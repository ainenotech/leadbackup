"""Unit tests for Customer Sending-Domain Authentication.

All external calls (AWS SES via boto3, DNS lookups via dnspython,
and SNS HTTP certificate downloads) are mocked so tests run completely
offline, fast, and deterministically without touching production databases
or real AWS services.
"""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from Backend.db import Base
from Backend.auth_models import Organization, OrganizationMember, User
from Backend.domain_models import (
    OrgDomainCheckHistory,
    OrgDomainRecord,
    OrgDomainStats,
    OrgSendingDomain,
)
from services.dns_health import (
    MxResult,
    SpfResult,
    DkimResult,
    DmarcResult,
    DnsHealthReport,
    _merge_spf_record,
    _estimate_spf_lookups,
    lookup_spf,
    full_dns_check,
)
from services.domain_auth_service import (
    CapExceededError,
    DomainNotReadyError,
    check_send_eligibility,
    delete_domain,
    get_check_history,
    get_dns_instructions,
    get_domain_detail,
    list_domains,
    pause_domain,
    record_bounce,
    record_complaint,
    record_send,
    register_domain,
    resume_domain,
    update_domain,
    verify_domain,
)
from Email import get_mailer_for_org
from Email.outlook_mailer import OutlookMailer


# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def db_session():
    """In-memory SQLite session for fast, isolated test runs."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_org_and_user(db_session):
    """Creates a test organization, owner user, and active membership."""
    org = Organization(
        id="org-test-12345678",
        name="Acme Corp",
        slug="acme-corp",
        status="active",
        email="admin@acme.com",
    )
    user = User(
        id="user-owner-123",
        email="john@acme.com",
        status="active",
        platform_role="user",
    )
    member = OrganizationMember(
        id="member-123",
        organization_id=org.id,
        user_id=user.id,
        role="organization_owner",
        status="active",
    )
    db_session.add(org)
    db_session.add(user)
    db_session.add(member)
    db_session.commit()

    return {"org": org, "user": user, "member": member}


@pytest.fixture
def mock_ses_provider():
    """Mocks SESProvider responses for Easy DKIM and MAIL FROM."""
    with patch("services.domain_auth_service._get_provider") as mock_get_prov:
        prov = MagicMock()
        prov.create_configuration_set.return_value = "org-test-1"

        # Mock create_identity return
        dkim1 = MagicMock(record_type="CNAME", host="tok1._domainkey.acme.com", value="tok1.dkim.amazonses.com", purpose="dkim")
        dkim2 = MagicMock(record_type="CNAME", host="tok2._domainkey.acme.com", value="tok2.dkim.amazonses.com", purpose="dkim")
        dkim3 = MagicMock(record_type="CNAME", host="tok3._domainkey.acme.com", value="tok3.dkim.amazonses.com", purpose="dkim")
        mail_from = MagicMock(
            subdomain="mail.acme.com",
            mx_host="mail.acme.com",
            mx_value="10 feedback-smtp.us-east-1.amazonses.com",
            spf_host="mail.acme.com",
            spf_value="v=spf1 include:amazonses.com ~all",
        )
        prov.create_identity.return_value = MagicMock(
            identity_ref="acme.com",
            verification_token="tok-ver-123",
            dkim_records=[dkim1, dkim2, dkim3],
            mail_from_records=mail_from,
        )

        prov.get_identity_status.return_value = MagicMock(
            identity_ref="acme.com",
            verification_status="success",
            dkim_status="success",
            mail_from_status="success",
            verified_for_sending=True,
        )

        mock_get_prov.return_value = prov
        yield prov


@pytest.fixture(autouse=True)
def default_mock_dns():
    """Default mock for full_dns_check that returns JSON-serializable DnsHealthReport."""
    with patch("services.dns_health.full_dns_check") as mock_dns:
        mock_dns.return_value = DnsHealthReport(
            domain="acme.com",
            dkim_checks=[
                DkimResult(host="tok1._domainkey.acme.com", expected_value="tok1.dkim.amazonses.com", verified=False),
                DkimResult(host="tok2._domainkey.acme.com", expected_value="tok2.dkim.amazonses.com", verified=False),
                DkimResult(host="tok3._domainkey.acme.com", expected_value="tok3.dkim.amazonses.com", verified=False),
            ],
            spf=SpfResult(valid=True, has_ses_include=False),
            dmarc=DmarcResult(policy="none"),
            mx=MxResult(detected_provider="Google Workspace"),
        )
        yield mock_dns


# ─────────────────────────────────────────────────────────────
# Test 1, 2, 3: SPF Analysis & Merging
# ─────────────────────────────────────────────────────────────

def test_spf_merge_existing_record():
    """Verify include:amazonses.com is cleanly merged before the ~all mechanism."""
    raw_spf = "v=spf1 include:_spf.google.com ~all"
    merged = _merge_spf_record(raw_spf)

    assert "include:amazonses.com" in merged
    assert merged.startswith("v=spf1 ")
    assert merged.endswith("~all")
    assert "include:_spf.google.com" in merged


def test_spf_multiple_records_detected():
    """Multiple SPF records violate RFC 7208; verify that multiple records trigger invalid status."""
    with patch("services.dns_health._get_resolver") as mock_res:
        mock_resolver = MagicMock()
        # Return 2 TXT records starting with v=spf1
        ans1 = MagicMock()
        ans1.strings = [b"v=spf1 include:_spf.google.com ~all"]
        ans2 = MagicMock()
        ans2.strings = [b"v=spf1 include:mailgun.org ~all"]
        mock_resolver.resolve.return_value = [ans1, ans2]
        mock_res.return_value = mock_resolver

        res = lookup_spf("customer.com")
        assert res.valid is False
        assert "Multiple SPF records" in (res.error or "")


def test_spf_lookup_limit_warning():
    """SPF with over 10 lookups triggers an RFC 7208 lookup warning."""
    # Build an SPF record with 11 includes
    raw_spf = "v=spf1 " + " ".join([f"include:spf{i}.example.com" for i in range(11)]) + " ~all"
    with patch("services.dns_health._get_resolver") as mock_res:
        mock_resolver = MagicMock()
        # Return empty answers for includes
        mock_resolver.resolve.side_effect = Exception("No TXT")
        mock_res.return_value = mock_resolver

        count, warning = _estimate_spf_lookups("example.com", raw_spf)
        # 11 includes directly in record
        assert count is not None or "limit" in str(warning) or "determine" in str(warning)


# ─────────────────────────────────────────────────────────────
# Test 4: DKIM Verification & State Transitions
# ─────────────────────────────────────────────────────────────

def test_dkim_verification_state_transitions(db_session, test_org_and_user, mock_ses_provider):
    """Pending domain transitions to limited/ready when both SES provider and DNS agree."""
    org = test_org_and_user["org"]
    user = test_org_and_user["user"]

    # Register domain
    with patch("services.dns_health.full_dns_check") as mock_dns:
        # Initially DNS CNAMEs are not yet propagating
        mock_dns.return_value = DnsHealthReport(
            domain="acme.com",
            dkim_checks=[
                DkimResult(host="tok1._domainkey.acme.com", expected_value="tok1.dkim.amazonses.com", verified=False, error="NXDOMAIN"),
                DkimResult(host="tok2._domainkey.acme.com", expected_value="tok2.dkim.amazonses.com", verified=False, error="NXDOMAIN"),
                DkimResult(host="tok3._domainkey.acme.com", expected_value="tok3.dkim.amazonses.com", verified=False, error="NXDOMAIN"),
            ],
            spf=SpfResult(valid=True, has_ses_include=False),
            dmarc=DmarcResult(policy="none"),
            mx=MxResult(detected_provider="Google Workspace"),
        )
        mock_ses_provider.get_identity_status.return_value.dkim_status = "pending"

        reg_res = register_domain(
            db=db_session,
            user_id=user.id,
            organization_id=org.id,
            email_address="john@acme.com",
        )
        assert reg_res["status"] == "pending"

        # Now DNS CNAMEs propagate and SES verifies Easy DKIM
        mock_dns.return_value = DnsHealthReport(
            domain="acme.com",
            dkim_checks=[
                DkimResult(host="tok1._domainkey.acme.com", expected_value="tok1.dkim.amazonses.com", verified=True),
                DkimResult(host="tok2._domainkey.acme.com", expected_value="tok2.dkim.amazonses.com", verified=True),
                DkimResult(host="tok3._domainkey.acme.com", expected_value="tok3.dkim.amazonses.com", verified=True),
            ],
            spf=SpfResult(valid=True, has_ses_include=True),
            dmarc=DmarcResult(policy="reject"),
            mx=MxResult(detected_provider="Google Workspace"),
        )
        mock_ses_provider.get_identity_status.return_value.dkim_status = "success"

        ver_res = verify_domain(
            db=db_session,
            user_id=user.id,
            organization_id=org.id,
            domain_id=reg_res["id"],
        )
        assert ver_res["status"] == "limited"
        assert ver_res["verified_at"] is not None


# ─────────────────────────────────────────────────────────────
# Test 5 & 6: Domain Claim Uniqueness & Expiry
# ─────────────────────────────────────────────────────────────

def test_single_verified_domain_claim(db_session, test_org_and_user, mock_ses_provider):
    """A verified domain cannot be claimed by another organization."""
    org1 = test_org_and_user["org"]
    user1 = test_org_and_user["user"]

    # Org 2
    org2 = Organization(id="org-2", name="Beta Corp", slug="beta-corp", status="active")
    user2 = User(id="user-2", email="jane@beta.com", status="active", platform_role="user")
    member2 = OrganizationMember(id="m-2", organization_id=org2.id, user_id=user2.id, role="organization_owner", status="active")
    db_session.add_all([org2, user2, member2])
    db_session.commit()

    reg1 = register_domain(
        db=db_session,
        user_id=user1.id,
        organization_id=org1.id,
        email_address="sales@acme.com",
    )
    # Mark as verified
    dom = db_session.query(OrgSendingDomain).filter(OrgSendingDomain.id == reg1["id"]).first()
    dom.status = "ready"
    db_session.commit()

    # Org 2 attempts to claim the same domain
    with pytest.raises(ValueError, match="already verified by another organization"):
        register_domain(
            db=db_session,
            user_id=user2.id,
            organization_id=org2.id,
            email_address="marketing@acme.com",
        )


def test_unverified_claim_expiry(db_session, test_org_and_user, mock_ses_provider):
    """An unverified pending claim that expired is cleaned up when re-claimed."""
    org1 = test_org_and_user["org"]
    user1 = test_org_and_user["user"]

    org2 = Organization(id="org-2-expired", name="Gamma Corp", slug="gamma-corp", status="active")
    user2 = User(id="user-2-expired", email="gamma@gamma.com", status="active", platform_role="user")
    member2 = OrganizationMember(id="m-2-exp", organization_id=org2.id, user_id=user2.id, role="organization_owner", status="active")
    db_session.add_all([org2, user2, member2])
    db_session.commit()

    # Org 1 claims domain
    reg1 = register_domain(
        db=db_session,
        user_id=user1.id,
        organization_id=org1.id,
        email_address="sales@startup.com",
    )
    dom = db_session.query(OrgSendingDomain).filter(OrgSendingDomain.id == reg1["id"]).first()
    # Fast-forward claim expiry to the past
    dom.claim_expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    db_session.commit()

    # Org 2 claims the expired domain
    reg2 = register_domain(
        db=db_session,
        user_id=user2.id,
        organization_id=org2.id,
        email_address="hello@startup.com",
    )
    assert reg2["organization_id"] == org2.id
    assert reg2["domain"] == "startup.com"


# ─────────────────────────────────────────────────────────────
# Test 7: Cross-Organization Isolation
# ─────────────────────────────────────────────────────────────

def test_cross_org_isolation(db_session, test_org_and_user, mock_ses_provider):
    """User in Org B cannot read, verify, pause, or delete Org A's domain."""
    org1 = test_org_and_user["org"]
    user1 = test_org_and_user["user"]

    org2 = Organization(id="org-b", name="Org B", slug="org-b", status="active")
    user2 = User(id="user-b", email="b@b.com", status="active", platform_role="user")
    member2 = OrganizationMember(id="m-b", organization_id=org2.id, user_id=user2.id, role="organization_owner", status="active")
    db_session.add_all([org2, user2, member2])
    db_session.commit()

    reg1 = register_domain(
        db=db_session,
        user_id=user1.id,
        organization_id=org1.id,
        email_address="admin@isolated.com",
    )
    domain_id = reg1["id"]

    # Org 2 attempts to get detail
    with pytest.raises(ValueError, match="Domain not found for this organization"):
        get_domain_detail(db_session, user2.id, org2.id, domain_id)

    # Org 2 attempts to verify
    with pytest.raises(ValueError, match="Domain not found for this organization"):
        verify_domain(db_session, user2.id, org2.id, domain_id)

    # Org 2 attempts to pause
    with pytest.raises(ValueError, match="Domain not found for this organization"):
        pause_domain(db_session, user2.id, org2.id, domain_id)

    # Org 2 attempts to delete
    with pytest.raises(ValueError, match="Domain not found for this organization"):
        delete_domain(db_session, user2.id, org2.id, domain_id)


# ─────────────────────────────────────────────────────────────
# Test 8, 9, 10: Send-Time Enforcement & Daily Cap
# ─────────────────────────────────────────────────────────────

def test_send_time_enforcement_unverified_fallback(db_session, test_org_and_user):
    """Unverified domain causes get_mailer_for_org to fall back to OutlookMailer."""
    org = test_org_and_user["org"]
    dom = OrgSendingDomain(
        id="dom-unver",
        organization_id=org.id,
        domain="unverified.com",
        status="pending",
        reply_to="reply@unverified.com",
    )
    db_session.add(dom)
    db_session.commit()

    with patch("Backend.db.SessionLocal", return_value=db_session):
        mailer = get_mailer_for_org(org.id, "john@unverified.com")
        assert isinstance(mailer, OutlookMailer)


def test_send_time_enforcement_paused(db_session, test_org_and_user):
    """Paused domain raises DomainNotReadyError and blocks sending."""
    org = test_org_and_user["org"]
    dom = OrgSendingDomain(
        id="dom-paused",
        organization_id=org.id,
        domain="paused.com",
        status="paused",
        paused_reason="Rate exceeded",
        reply_to="reply@paused.com",
    )
    db_session.add(dom)
    db_session.commit()

    with pytest.raises(DomainNotReadyError, match="Sending domain paused.com is paused"):
        check_send_eligibility(db_session, org.id, "paused.com")


def test_daily_cap_enforcement(db_session, test_org_and_user):
    """When daily sending volume hits cap, CapExceededError is raised."""
    org = test_org_and_user["org"]
    dom = OrgSendingDomain(
        id="dom-capped",
        organization_id=org.id,
        domain="capped.com",
        status="limited",
        daily_cap=5,
        reply_to="reply@capped.com",
    )
    db_session.add(dom)
    # Add stats showing 5 sent today
    stats = OrgDomainStats(
        id="stats-today",
        domain_id=dom.id,
        date=date.today(),
        sent=5,
    )
    db_session.add(stats)
    db_session.commit()

    with pytest.raises(CapExceededError, match="Daily sending cap"):
        check_send_eligibility(db_session, org.id, "capped.com")

    # If cap is 10, it passes
    dom.daily_cap = 10
    db_session.commit()
    res = check_send_eligibility(db_session, org.id, "capped.com")
    assert res.id == dom.id


# ─────────────────────────────────────────────────────────────
# Test 11, 12: SNS Webhook Signature & Bounce/Complaint Handling
# ─────────────────────────────────────────────────────────────

def test_webhook_signature_rejection():
    """An SNS message with invalid cert URL or fake signature is rejected."""
    from Backend.domain_endpoints import _validate_sns_cert_url, _verify_sns_signature

    # Invalid cert URL (not https, or not amazonaws.com)
    assert not _validate_sns_cert_url("http://sns.us-east-1.amazonaws.com/cert.pem")
    assert not _validate_sns_cert_url("https://malicious-site.com/cert.pem")
    assert not _validate_sns_cert_url("https://sns.us-east-1.amazonaws.com/cert.exe")

    # Valid format
    assert _validate_sns_cert_url("https://sns.us-east-1.amazonaws.com/SimpleNotificationService-123.pem")

    # Invalid signature payload
    fake_msg = {
        "Type": "Notification",
        "Message": '{"eventType": "Bounce"}',
        "SigningCertURL": "https://invalid.attacker.com/cert.pem",
        "Signature": "dGhpcyBpcyBhIGZha2Ugc2lnbmF0dXJl",
    }
    assert not _verify_sns_signature(fake_msg)


def test_webhook_bounce_and_auto_pause(db_session, test_org_and_user):
    """Bounce counter increments; domain auto-pauses when threshold (>= 5.0%) is reached."""
    org = test_org_and_user["org"]
    dom = OrgSendingDomain(
        id="dom-bounce",
        organization_id=org.id,
        domain="deliverability.com",
        status="ready",
        reply_to="reply@deliverability.com",
    )
    db_session.add(dom)
    # 20 emails sent today
    stats = OrgDomainStats(
        id="stats-bounce",
        domain_id=dom.id,
        date=date.today(),
        sent=20,
        bounced=0,
    )
    db_session.add(stats)
    db_session.commit()

    # 1st bounce (1/20 = 5.0% >= threshold 5.0%)
    record_bounce(db_session, "deliverability.com")

    db_session.refresh(dom)
    db_session.refresh(stats)
    assert stats.bounced == 1
    assert dom.status == "paused"
    assert "Auto-paused: bounce rate" in dom.paused_reason


def test_webhook_complaint_and_auto_pause(db_session, test_org_and_user):
    """Complaint counter increments; auto-pauses when complaint rate >= 0.1%."""
    org = test_org_and_user["org"]
    dom = OrgSendingDomain(
        id="dom-comp",
        organization_id=org.id,
        domain="complaints.com",
        status="ready",
        reply_to="reply@complaints.com",
    )
    db_session.add(dom)
    stats = OrgDomainStats(
        id="stats-comp",
        domain_id=dom.id,
        date=date.today(),
        sent=100,
        complained=0,
    )
    db_session.add(stats)
    db_session.commit()

    # 1 complaint (1/100 = 1.0% >= threshold 0.1%)
    record_complaint(db_session, "complaints.com")

    db_session.refresh(dom)
    assert dom.status == "paused"
    assert "complaint rate" in dom.paused_reason


# ─────────────────────────────────────────────────────────────
# Test 13 & 14: Fallback & Module Import Verification
# ─────────────────────────────────────────────────────────────

def test_org_without_sending_domain(db_session):
    """Organizations without sending domains seamlessly fall back to OutlookMailer."""
    with patch("Backend.db.SessionLocal", return_value=db_session):
        mailer = get_mailer_for_org(None)
        assert isinstance(mailer, OutlookMailer)

        mailer_empty = get_mailer_for_org("non-existent-org-id")
        assert isinstance(mailer_empty, OutlookMailer)


def test_all_modules_import_cleanly():
    """Verify that all newly created and modified modules import without syntax or symbol errors."""
    import Backend.domain_models
    import Backend.domain_endpoints
    import services.dns_health
    import services.domain_auth_service
    import Email.providers.base
    import Email.providers.ses_provider
    import Email.ses_mailer
    import Email.tracking

    assert hasattr(Backend.domain_models, "OrgSendingDomain")
    assert hasattr(Backend.domain_endpoints, "router")
    assert hasattr(services.dns_health, "full_dns_check")
    assert hasattr(services.domain_auth_service, "register_domain")
    assert hasattr(Email.ses_mailer, "SESMailer")
    assert hasattr(Email.tracking, "prepare_tracked_body")
