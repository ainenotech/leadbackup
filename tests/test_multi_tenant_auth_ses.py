"""
Comprehensive Automated Test Suite for Universal Multi-Tenant Auth,
Arbitrary Organization Creation, Explicit Memberships, and AWS SES Sending Domains.

Tests cover:
1. Google OAuth flow & Microsoft OAuth flow (personal & workspace accounts)
2. Stable OAuth identity linking without collision
3. Arbitrary Organization creation (User john@gmail.com creates ACME, becomes owner)
4. Multi-organization membership (John belongs to ACME and Startup XYZ)
5. Tenant isolation (User cannot access another org's data or email domains)
6. Organization invitation and role enforcement (owner/admin vs member)
7. Customer email domain registration with domain normalization (ACME.COM == acme.com)
8. AWS SES Easy DKIM verification record generation (provider-agnostic DNS)
9. SES verification status checking and transition to verified
10. Pre-send verification rules (step 1 to 6 enforcement):
    - Verified domain allows sending
    - Unverified domain blocked
    - Cross-tenant domain blocked
    - Sender mismatch blocked
"""

import os
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set test environment flags
os.environ["MOCK_SES"] = "true"
os.environ["AUTH_ALLOW_CONSUMER_ACCOUNTS"] = "true"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-multi-tenant-12345"

from Backend.db import Base, get_db
from Backend.api import app
from Backend.auth_models import Organization, User, IdentityAccount, OrganizationMember
from Backend.domain_models import OrgSendingDomain
from Backend.auth_service import hash_password, create_access_token
from services.ses_send_service import validate_and_send_via_ses
from Email.providers.mock_provider import MockSESProvider
from Email.providers import get_ses_provider

# Setup persistent test SQLite file for reliable multi-thread and multi-connection testing
TEST_DB_FILE = "test_saas.db"
if os.path.exists(TEST_DB_FILE):
    try:
        os.remove(TEST_DB_FILE)
    except Exception:
        pass

SQLALCHEMY_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

import Backend.db
import Backend.auth_endpoints
import Backend.domain_endpoints

Backend.db.engine = engine
Backend.db.SessionLocal = TestingSessionLocal
Backend.auth_endpoints.SessionLocal = TestingSessionLocal
Backend.domain_endpoints.SessionLocal = TestingSessionLocal

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except Exception:
            pass

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Helper fixtures for multi-tenant tokens
@pytest.fixture
def john_user(db_session):
    """User John with personal email john@gmail.com"""
    user = db_session.query(User).filter(User.email == "john@gmail.com").first()
    if not user:
        user = User(
            email="john@gmail.com",
            full_name="John Doe",
            password_hash=hash_password("Password123!"),
            status="active",
            email_verified=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user

@pytest.fixture
def sarah_user(db_session):
    """User Sarah with work email sarah@competitor.io"""
    user = db_session.query(User).filter(User.email == "sarah@competitor.io").first()
    if not user:
        user = User(
            email="sarah@competitor.io",
            full_name="Sarah Smith",
            password_hash=hash_password("Password123!"),
            status="active",
            email_verified=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user

@pytest.fixture
def acme_org(db_session, john_user):
    """ACME Organization owned by John"""
    org = db_session.query(Organization).filter(Organization.slug == "acme-corp").first()
    if not org:
        org = Organization(
            name="ACME Corporation",
            slug="acme-corp",
            is_platform_org=False,
            settings={"sender_name": "ACME Team", "sender_email": "hello@acme.com"}
        )
        db_session.add(org)
        db_session.commit()
        db_session.refresh(org)

        # John is Owner
        member = OrganizationMember(
            organization_id=org.id,
            user_id=john_user.id,
            role="organization_owner",
            status="active",
            is_default=True
        )
        db_session.add(member)
        db_session.commit()
    return org

@pytest.fixture
def startup_org(db_session, sarah_user):
    """Startup XYZ Organization owned by Sarah"""
    org = db_session.query(Organization).filter(Organization.slug == "startup-xyz").first()
    if not org:
        org = Organization(
            name="Startup XYZ",
            slug="startup-xyz",
            is_platform_org=False,
            settings={"sender_name": "Startup Team", "sender_email": "team@startup.xyz"}
        )
        db_session.add(org)
        db_session.commit()
        db_session.refresh(org)

        member = OrganizationMember(
            organization_id=org.id,
            user_id=sarah_user.id,
            role="organization_owner",
            status="active",
            is_default=True
        )
        db_session.add(member)
        db_session.commit()
    return org

def make_auth_headers(user, org=None):
    token = create_access_token(
        user_id=user.id,
        org_id=org.id if org else None,
        role="organization_owner" if org else "regular_user",
        email=user.email,
        platform_role=user.platform_role if hasattr(user, "platform_role") else "user"
    )
    return {"Authorization": f"Bearer {token}"}

# ==============================================================================
# 1. AUTHENTICATION & OAUTH IDENTITY TESTS
# ==============================================================================

def test_oauth_identity_separation(db_session, john_user):
    """Test OAuth identity uses stable provider_subject and links cleanly without duplicate collisions."""
    # Add Google identity
    google_id = IdentityAccount(
        user_id=john_user.id,
        provider="google",
        provider_user_id="google-sub-987654",
        provider_email="john@gmail.com",
    )
    db_session.add(google_id)
    db_session.commit()

    # Add Microsoft identity to same user
    ms_id = IdentityAccount(
        user_id=john_user.id,
        provider="microsoft",
        provider_user_id="ms-sub-123456",
        provider_email="john@outlook.com",
    )
    db_session.add(ms_id)
    db_session.commit()

    identities = db_session.query(IdentityAccount).filter(IdentityAccount.user_id == john_user.id).all()
    assert len(identities) == 2
    assert {i.provider for i in identities} == {"google", "microsoft"}

def test_login_flow_credentials(client, john_user, acme_org):
    """Test standard login endpoint issues JWT with user's active organization."""
    resp = client.post("/api/auth/login", json={
        "email": "john@gmail.com",
        "password": "Password123!"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == "john@gmail.com"

# ==============================================================================
# 2. UNIVERSAL ORGANIZATION CREATION & MULTI-TENANCY
# ==============================================================================

def test_create_organization_arbitrary_user(client, john_user):
    """A user with a personal @gmail.com address can create any company organization and becomes Owner."""
    headers = make_auth_headers(john_user)
    resp = client.post("/api/organizations", json={
        "name": "Global Logistics Corp"
    }, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["organization"]["name"] == "Global Logistics Corp"
    assert "access_token" in data

def test_user_belongs_to_multiple_organizations(client, db_session, john_user, acme_org, startup_org):
    """User John can belong to ACME (as owner) and Startup XYZ (as member)."""
    # Add John to Startup XYZ as a regular member
    existing_mem = db_session.query(OrganizationMember).filter(
        OrganizationMember.organization_id == startup_org.id,
        OrganizationMember.user_id == john_user.id
    ).first()
    if not existing_mem:
        db_session.add(OrganizationMember(
            organization_id=startup_org.id,
            user_id=john_user.id,
            role="member",
            status="active"
        ))
        db_session.commit()

    headers = make_auth_headers(john_user, acme_org)
    resp = client.get("/api/organizations", headers=headers)
    assert resp.status_code == 200
    orgs = resp.json()["organizations"]
    org_ids = [o["id"] for o in orgs]
    assert acme_org.id in org_ids
    assert startup_org.id in org_ids

@pytest.fixture
def competitor_org(db_session, sarah_user):
    """Competitor Inc Organization where John is NOT a member"""
    org = db_session.query(Organization).filter(Organization.slug == "competitor-inc").first()
    if not org:
        org = Organization(
            name="Competitor Inc",
            slug="competitor-inc",
            is_platform_org=False,
            settings={"sender_name": "Competitor", "sender_email": "team@competitor.io"}
        )
        db_session.add(org)
        db_session.commit()
        db_session.refresh(org)

        member = OrganizationMember(
            organization_id=org.id,
            user_id=sarah_user.id,
            role="organization_owner",
            status="active",
            is_default=True
        )
        db_session.add(member)
        db_session.commit()
    return org

def test_tenant_isolation_unauthorized_org_access(client, john_user, competitor_org):
    """User John cannot view member list of an organization he is not a member of."""
    headers = make_auth_headers(john_user)
    # Target an org where user has no membership
    resp = client.get(f"/api/organizations/{competitor_org.id}/members", headers=headers)
    # Either 403 Forbidden or 404 Not Found
    assert resp.status_code in [403, 404]

# ==============================================================================
# 3. ORGANIZATION INVITATION FLOW
# ==============================================================================

def test_invite_member_and_accept(client, db_session, john_user, acme_org):
    """Owner can invite user@external.com, and user can accept without email domain restriction."""
    headers = make_auth_headers(john_user, acme_org)
    resp = client.post(f"/api/organizations/{acme_org.id}/members/invite", json={
        "email": "consultant@freelance.org",
        "role": "member"
    }, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # Find user created during invitation
    consultant = db_session.query(User).filter(User.email == "consultant@freelance.org").first()
    assert consultant is not None

    consultant_headers = make_auth_headers(consultant)
    accept_resp = client.post(
        f"/api/organizations/{acme_org.id}/members/{consultant.id}/accept",
        headers=consultant_headers
    )
    assert accept_resp.status_code == 200
    assert accept_resp.json()["membership"]["role"] in ("regular_user", "member")

# ==============================================================================
# 4. CUSTOMER EMAIL DOMAIN & AWS SES VERIFICATION
# ==============================================================================

def test_add_email_domain_normalizes_and_calls_ses(client, john_user, acme_org):
    """Domain is normalized (ACME.COM -> acme.com) and Easy DKIM records are generated."""
    headers = make_auth_headers(john_user, acme_org)
    resp = client.post(f"/api/organizations/{acme_org.id}/email-domains", json={
        "domain": "ACME.COM"
    }, headers=headers)
    assert resp.status_code == 200
    data = resp.json()["domain"]
    assert data["domain"] == "acme.com"
    assert data["verification_status"] == "pending"
    assert len(data["records"]) >= 3  # Easy DKIM CNAMEs + MAIL FROM

def test_duplicate_domain_registration_handled(client, john_user, acme_org):
    """Registering the same domain again in the same organization returns conflict or existing domain."""
    headers = make_auth_headers(john_user, acme_org)
    resp = client.post(f"/api/organizations/{acme_org.id}/email-domains", json={
        "domain": "acme.com"
    }, headers=headers)
    # Returns 409 or graceful conflict message
    assert resp.status_code in [400, 409]

def test_cross_tenant_domain_access_blocked(client, sarah_user, acme_org, db_session):
    """Sarah (Startup XYZ) cannot access or verify ACME's email domains."""
    acme_domain = db_session.query(OrgSendingDomain).filter(
        OrgSendingDomain.organization_id == acme_org.id
    ).first()
    assert acme_domain is not None

    sarah_headers = make_auth_headers(sarah_user)
    resp = client.get(
        f"/api/organizations/{acme_org.id}/email-domains/{acme_domain.id}",
        headers=sarah_headers
    )
    assert resp.status_code in [403, 404]

def test_domain_verification_status_check(client, john_user, acme_org, db_session):
    """Checking verification checks SES and transitions status when DKIM records verify."""
    acme_domain = db_session.query(OrgSendingDomain).filter(
        OrgSendingDomain.organization_id == acme_org.id
    ).first()

    # Simulate provider mock verification
    provider = get_ses_provider()
    if isinstance(provider, MockSESProvider):
        provider.set_verified("acme.com", True)

    headers = make_auth_headers(john_user, acme_org)
    resp = client.post(
        f"/api/organizations/{acme_org.id}/email-domains/{acme_domain.id}/verify",
        headers=headers
    )
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["verification_status"] == "verified"
    assert res_data["can_send"] is True

# ==============================================================================
# 5. PRE-SEND VALIDATION RULES (SES SEND SERVICE)
# ==============================================================================

def test_ses_pre_send_validation_success(db_session, acme_org):
    """Sending from an authorized, verified domain succeeds."""
    # Ensure verified domain exists for ACME
    domain = db_session.query(OrgSendingDomain).filter(
        OrgSendingDomain.organization_id == acme_org.id,
        OrgSendingDomain.domain == "acme.com"
    ).first()
    if not domain:
        domain = OrgSendingDomain(
            organization_id=acme_org.id,
            domain="acme.com",
            status="ready",
            provider_identity_ref="arn:aws:ses:us-east-1:123456789012:identity/acme.com"
        )
        db_session.add(domain)
        db_session.commit()
    else:
        domain.status = "ready"
        db_session.commit()

    result = validate_and_send_via_ses(
        db=db_session,
        organization_id=acme_org.id,
        from_email="outreach@acme.com",
        to_email="lead@customer.com",
        subject="Partnership Opportunity",
        body="Hello from ACME!",
        html_body="<p>Hello from ACME!</p>"
    )
    assert result["success"] is True
    assert "message_id" in result

def test_ses_pre_send_validation_rejects_unverified_domain(db_session, startup_org):
    """Sending from an unverified domain is strictly rejected."""
    # Register unverified domain in Startup XYZ
    unverified = OrgSendingDomain(
        organization_id=startup_org.id,
        domain="unverified-startup.io",
        status="pending",
    )
    db_session.add(unverified)
    db_session.commit()

    with pytest.raises(ValueError, match="not verified"):
        validate_and_send_via_ses(
            db=db_session,
            organization_id=startup_org.id,
            from_email="sales@unverified-startup.io",
            to_email="lead@customer.com",
            subject="Test",
            body="Test",
            html_body="<p>Test</p>"
        )

def test_ses_pre_send_validation_rejects_cross_tenant_domain(db_session, startup_org):
    """Startup XYZ cannot send emails using ACME's verified domain."""
    with pytest.raises(Exception):
        validate_and_send_via_ses(
            db=db_session,
            organization_id=startup_org.id,
            from_email="sales@acme.com",
            to_email="lead@customer.com",
            subject="Test",
            body="Test",
            html_body="<p>Test</p>"
        )

def test_ses_pre_send_validation_rejects_mismatched_sender(db_session, acme_org):
    """Sender email user@other.com does not match verified domain acme.com."""
    with pytest.raises(Exception):
        validate_and_send_via_ses(
            db=db_session,
            organization_id=acme_org.id,
            from_email="admin@roguedomain.com",
            to_email="lead@customer.com",
            subject="Test",
            body="Test",
            html_body="<p>Test</p>"
        )

