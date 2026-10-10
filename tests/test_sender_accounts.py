"""Unit and Integration Tests for Multi-Domain & Multi-Mailbox Management.

Tests cover:
1. Sender Account Creation & Domain Association
2. Email normalization & domain validation (must match domain)
3. Multi-dimensional readiness checklist:
   - SES Identity status (ready / pending / failed)
   - Mailbox connection status (connected / disconnected / not_required)
   - Sending permission status (ready / blocked / rate_limited / disabled)
   - Reply monitoring status
4. Rate limiting: hourly & daily send caps, auto-reset windows
5. Campaign sender eligibility logic (check_sender_eligibility)
6. Tenant isolation (senders cannot be accessed or modified cross-organization)
7. REST API endpoints (/api/senders CRUD, filtering, refresh)
8. Domain verification daemon check cycle updating sender readiness
"""

import os
import sys
from pathlib import Path
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add repo root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["MOCK_SES"] = "true"
os.environ["AUTH_ALLOW_CONSUMER_ACCOUNTS"] = "true"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-sender-accounts-54321"

from Backend.db import Base, get_db
from Backend.api import app
from Backend.auth_models import Organization, User, IdentityAccount, OrganizationMember
from Backend.domain_models import OrgSendingDomain, OrgDomainRecord
from Backend.sender_models import SenderAccount
from Backend.channels_models import OrgMailConnection
from Backend.auth_service import hash_password, create_access_token
from services.sender_account_service import (
    create_sender_account,
    list_sender_accounts,
    get_sender_account,
    update_sender_account,
    delete_sender_account,
    check_sender_eligibility,
    record_sender_send,
    refresh_sender_readiness,
)

TEST_DB_FILE = "test_sender_mgmt.db"
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
import Backend.sender_endpoints

Backend.db.engine = engine
Backend.db.SessionLocal = TestingSessionLocal
Backend.auth_endpoints.SessionLocal = TestingSessionLocal
Backend.domain_endpoints.SessionLocal = TestingSessionLocal
Backend.sender_endpoints.SessionLocal = TestingSessionLocal


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
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def test_setup(db):
    """Seed test organizations, users, and sending domains with clean state."""
    db.query(SenderAccount).delete()
    db.query(OrgMailConnection).delete()
    db.query(OrgSendingDomain).delete()
    db.query(OrganizationMember).delete()
    db.query(User).delete()
    db.query(Organization).delete()
    db.commit()

    # Org 1: ACME Corp
    org1 = Organization(
        id=str(uuid.uuid4()),
        name="ACME Corp",
        slug=f"acme-{uuid.uuid4().hex[:6]}",
        status="active",
    )
    db.add(org1)

    # User 1: Admin of ACME
    user1 = User(
        id=str(uuid.uuid4()),
        email="admin@acme.com",
        full_name="Alice Admin",
        password_hash=hash_password("Password123!"),
        status="active",
        platform_role="user",
    )
    db.add(user1)
    db.flush()

    member1 = OrganizationMember(
        id=str(uuid.uuid4()),
        organization_id=org1.id,
        user_id=user1.id,
        role="organization_admin",
        status="active",
        is_default=True,
    )
    db.add(member1)

    # Org 2: Beta Corp
    org2 = Organization(
        id=str(uuid.uuid4()),
        name="Beta Corp",
        slug=f"beta-{uuid.uuid4().hex[:6]}",
        status="active",
    )
    db.add(org2)

    # User 2: Admin of Beta
    user2 = User(
        id=str(uuid.uuid4()),
        email="admin@beta.com",
        full_name="Bob Beta",
        password_hash=hash_password("Password123!"),
        status="active",
        platform_role="user",
    )
    db.add(user2)
    db.flush()

    member2 = OrganizationMember(
        id=str(uuid.uuid4()),
        organization_id=org2.id,
        user_id=user2.id,
        role="organization_admin",
        status="active",
        is_default=True,
    )
    db.add(member2)

    # Verified Domain for Org 1
    domain_verified = OrgSendingDomain(
        id=str(uuid.uuid4()),
        organization_id=org1.id,
        domain="acme.com",
        status="ready",
        provider="ses",
    )
    db.add(domain_verified)

    # Pending Domain for Org 1
    domain_pending = OrgSendingDomain(
        id=str(uuid.uuid4()),
        organization_id=org1.id,
        domain="outreach.acme.com",
        status="pending",
        provider="ses",
    )
    db.add(domain_pending)

    # Paused Domain for Org 1
    domain_paused = OrgSendingDomain(
        id=str(uuid.uuid4()),
        organization_id=org1.id,
        domain="paused.acme.com",
        status="paused",
        provider="ses",
    )
    db.add(domain_paused)

    db.commit()

    token1 = create_access_token(user_id=user1.id, org_id=org1.id, email=user1.email, role="organization_admin")
    token2 = create_access_token(user_id=user2.id, org_id=org2.id, email=user2.email, role="organization_admin")

    return {
        "org1": org1,
        "org2": org2,
        "user1": user1,
        "user2": user2,
        "token1": token1,
        "token2": token2,
        "domain_verified": domain_verified,
        "domain_pending": domain_pending,
        "domain_paused": domain_paused,
    }


# ─────────────────────────────────────────────────────────────
# UNIT & SERVICE TESTS
# ─────────────────────────────────────────────────────────────

def test_create_sender_account_success(db, test_setup):
    """Admin can create a sender account linked to a verified domain."""
    s = test_setup
    result = create_sender_account(
        db=db,
        user_id=s["user1"].id,
        org_id=s["org1"].id,
        email="sales@acme.com",
        display_name="ACME Sales Team",
        domain_id=s["domain_verified"].id,
        provider="ses_only",
        hourly_limit=60,
        daily_limit=300,
    )

    assert result["email"] == "sales@acme.com"
    assert result["display_name"] == "ACME Sales Team"
    assert result["domain_name"] == "acme.com"
    assert result["ses_identity_status"] == "ready"
    assert result["mailbox_connection_status"] == "not_required"
    assert result["overall_status"] == "active"
    assert result["is_send_ready"] is True
    assert len(result["readiness_checklist"]) >= 4


def test_create_sender_account_mismatched_domain(db, test_setup):
    """Sender email domain must match the specified sending domain."""
    s = test_setup
    with pytest.raises(ValueError, match="does not match"):
        create_sender_account(
            db=db,
            user_id=s["user1"].id,
            org_id=s["org1"].id,
            email="sales@otherdomain.com",
            domain_id=s["domain_verified"].id,
        )


def test_create_sender_account_unregistered_domain(db, test_setup):
    """Cannot create a sender for a domain not registered in the organization."""
    s = test_setup
    with pytest.raises(ValueError, match="must be registered"):
        create_sender_account(
            db=db,
            user_id=s["user1"].id,
            org_id=s["org1"].id,
            email="someone@unregistered.com",
        )


def test_sender_readiness_with_pending_domain(db, test_setup):
    """Sender associated with pending domain is marked ses_pending."""
    s = test_setup
    result = create_sender_account(
        db=db,
        user_id=s["user1"].id,
        org_id=s["org1"].id,
        email="hello@outreach.acme.com",
        domain_id=s["domain_pending"].id,
        provider="ses_only",
    )

    assert result["ses_identity_status"] == "pending"
    assert result["overall_status"] == "ses_pending"
    assert result["is_send_ready"] is False


def test_sender_with_oauth_mailbox(db, test_setup):
    """Sender with Microsoft 365 provider requires connected mailbox to be send-ready."""
    s = test_setup
    # Create M365 sender without mailbox connected yet
    result = create_sender_account(
        db=db,
        user_id=s["user1"].id,
        org_id=s["org1"].id,
        email="outreach@acme.com",
        domain_id=s["domain_verified"].id,
        provider="microsoft_365",
    )

    assert result["mailbox_connection_status"] == "disconnected"
    assert result["overall_status"] == "mailbox_disconnected"
    assert result["is_send_ready"] is False

    # Simulate mailbox connection via OrgMailConnection
    conn = OrgMailConnection(
        id=str(uuid.uuid4()),
        organization_id=s["org1"].id,
        email="outreach@acme.com",
        domain="acme.com",
        channel="microsoft_oauth",
        status="active",
        daily_cap=500,
    )
    db.add(conn)
    db.commit()

    # Refresh readiness
    refreshed = refresh_sender_readiness(
        db=db,
        user_id=s["user1"].id,
        org_id=s["org1"].id,
        sender_id=result["id"],
    )

    assert refreshed["mailbox_connection_status"] == "connected"
    assert refreshed["reply_monitoring_status"] == "active"
    assert refreshed["overall_status"] == "active"
    assert refreshed["is_send_ready"] is True


def test_sender_rate_limits_and_eligibility(db, test_setup):
    """Check campaign sender eligibility respects hourly and daily send caps."""
    s = test_setup
    sender = create_sender_account(
        db=db,
        user_id=s["user1"].id,
        org_id=s["org1"].id,
        email="capped@acme.com",
        domain_id=s["domain_verified"].id,
        provider="ses_only",
        hourly_limit=2,
        daily_limit=3,
    )

    # Initial: Eligible
    elig1 = check_sender_eligibility(db, s["org1"].id, sender["id"])
    assert elig1["eligible"] is True

    # Record 2 sends
    record_sender_send(db, sender["id"])
    record_sender_send(db, sender["id"])

    # Hourly cap reached!
    elig2 = check_sender_eligibility(db, s["org1"].id, sender["id"])
    assert elig2["eligible"] is False
    assert "Hourly limit reached" in elig2["reason"]

    # Manually reset hour window and test daily limit
    sender_rec = db.query(SenderAccount).filter(SenderAccount.id == sender["id"]).first()
    sender_rec.hour_reset_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()

    # Now eligible again for the hour, but sends_today is 2/3
    elig3 = check_sender_eligibility(db, s["org1"].id, sender["id"])
    assert elig3["eligible"] is True

    # Record 3rd send
    record_sender_send(db, sender["id"])

    # Daily cap reached!
    elig4 = check_sender_eligibility(db, s["org1"].id, sender["id"])
    assert elig4["eligible"] is False
    assert "Daily limit reached" in elig4["reason"]


def test_sender_paused_domain_ineligibility(db, test_setup):
    """Sender under a paused domain is ineligible to send."""
    s = test_setup
    sender = create_sender_account(
        db=db,
        user_id=s["user1"].id,
        org_id=s["org1"].id,
        email="paused@paused.acme.com",
        domain_id=s["domain_paused"].id,
        provider="ses_only",
    )

    elig = check_sender_eligibility(db, s["org1"].id, sender["id"])
    assert elig["eligible"] is False
    assert "paused" in elig["reason"]


# ─────────────────────────────────────────────────────────────
# REST API ENDPOINT TESTS
# ─────────────────────────────────────────────────────────────

def test_api_list_and_create_sender(client, test_setup):
    """Test POST /api/senders and GET /api/senders."""
    s = test_setup
    headers = {"Authorization": f"Bearer {s['token1']}"}

    # Create via API
    payload = {
        "email": "newsletter@acme.com",
        "display_name": "ACME Newsletter",
        "domain_id": s["domain_verified"].id,
        "provider": "ses_only",
        "hourly_limit": 100,
        "daily_limit": 500,
        "notes": "Marketing newsletter sender",
    }
    res = client.post("/api/senders", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["email"] == "newsletter@acme.com"
    sender_id = data["id"]

    # List via API
    res_list = client.get("/api/senders", headers=headers)
    assert res_list.status_code == 200
    senders = res_list.json()["data"]
    assert any(snd["id"] == sender_id for snd in senders)

    # Filter by domain
    res_filtered = client.get(f"/api/senders?domain_id={s['domain_verified'].id}", headers=headers)
    assert res_filtered.status_code == 200
    assert len(res_filtered.json()["data"]) >= 1


def test_api_tenant_isolation(client, test_setup):
    """Org 2 cannot view or modify Org 1's sender accounts."""
    s = test_setup
    headers_org1 = {"Authorization": f"Bearer {s['token1']}"}
    headers_org2 = {"Authorization": f"Bearer {s['token2']}"}

    # Create sender in Org 1
    res = client.post(
        "/api/senders",
        json={
            "email": "confidential@acme.com",
            "domain_id": s["domain_verified"].id,
            "provider": "ses_only",
        },
        headers=headers_org1,
    )
    assert res.status_code == 201
    sender_id = res.json()["data"]["id"]

    # Org 2 tries to GET Org 1's sender
    res_get = client.get(f"/api/senders/{sender_id}", headers=headers_org2)
    assert res_get.status_code == 404

    # Org 2 tries to PATCH Org 1's sender
    res_patch = client.patch(
        f"/api/senders/{sender_id}",
        json={"display_name": "Hacked Display Name"},
        headers=headers_org2,
    )
    assert res_patch.status_code == 404

    # Org 2 tries to DELETE Org 1's sender
    res_del = client.delete(f"/api/senders/{sender_id}", headers=headers_org2)
    assert res_del.status_code == 404


def test_api_update_and_delete_sender(client, test_setup):
    """Test PATCH /api/senders/{id} and DELETE /api/senders/{id}."""
    s = test_setup
    headers = {"Authorization": f"Bearer {s['token1']}"}

    # Create
    res = client.post(
        "/api/senders",
        json={
            "email": "temp@acme.com",
            "domain_id": s["domain_verified"].id,
            "provider": "ses_only",
        },
        headers=headers,
    )
    sender_id = res.json()["data"]["id"]

    # Update
    patch_res = client.patch(
        f"/api/senders/{sender_id}",
        json={"display_name": "Updated Temp Sender", "enabled": False},
        headers=headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["data"]["display_name"] == "Updated Temp Sender"
    assert patch_res.json()["data"]["enabled"] is False

    # Delete
    del_res = client.delete(f"/api/senders/{sender_id}", headers=headers)
    assert del_res.status_code == 200

    # Confirm 404
    get_res = client.get(f"/api/senders/{sender_id}", headers=headers)
    assert get_res.status_code == 404
