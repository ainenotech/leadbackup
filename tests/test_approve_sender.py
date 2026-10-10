import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from Backend.db import Base
from Backend.models import CampaignLog
from Backend.crud import approve_and_send_entry

@pytest.fixture
def mock_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    entry = CampaignLog(
        id="test-draft-123",
        campaign_name="Test Campaign",
        lead_id="lead-001",
        token="token-123",
        email="lead@example.com",
        name="Lead Name",
        company="Lead Co",
        status="drafted",
        subject="Hello {{name}}",
        body="Pitching to {{company}}",
    )
    session.add(entry)
    session.commit()
    yield session
    session.close()

def test_approve_and_send_entry_with_sender_email(mock_db):
    mock_mailer = MagicMock()
    mock_mailer.send_email.return_value = "msg-123"

    with patch("Backend.crud.get_mailer", return_value=mock_mailer):
        entry = approve_and_send_entry(mock_db, "test-draft-123", sender_email="hardini@nenotechnology.com")

        assert entry.status == "sent"
        assert entry.email_sent_at is not None
        mock_mailer.send_email.assert_called_once()
        _, kwargs = mock_mailer.send_email.call_args
        assert kwargs.get("from_email") == "hardini@nenotechnology.com"


def test_api_approve_and_send_all():
    from fastapi.testclient import TestClient
    from Backend.api import app

    client = TestClient(app)

    # Test send-all with batch_size & sender_email
    with patch("Backend.routes.approve_and_send_entry") as mock_approve:
        resp = client.post(
            "/api/drafts/send-all",
            json={"sender_email": "support@nenotechnology.com", "batch_size": 2},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "sent_count" in data
        assert data["sender_email"] == "support@nenotechnology.com"


def test_create_sender_account_gmail_with_any_verified_domain():
    from services.sender_account_service import create_sender_account
    from Backend.auth_models import Organization, User, OrganizationMembership
    from Backend.domain_models import OrgSendingDomain
    import uuid

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    org = Organization(id=str(uuid.uuid4()), name="Test Org", slug="test-org")
    user = User(id=str(uuid.uuid4()), email="admin@test.com", password_hash="hash")
    membership = OrganizationMembership(organization_id=org.id, user_id=user.id, role="admin")
    domain = OrgSendingDomain(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        domain="nenotechnology.com",
        status="verified",
    )
    session.add_all([org, user, membership, domain])
    session.commit()

    # 1. Adding a Gmail account with verified corporate domain
    gmail_sender = create_sender_account(
        db=session,
        user_id=user.id,
        org_id=org.id,
        email="panchalnand4@gmail.com",
        display_name="Nand Panchal",
        domain_id=domain.id,
        provider="ses_only",
    )
    assert gmail_sender["email"] == "panchalnand4@gmail.com"
    assert gmail_sender["display_name"] == "Nand Panchal"
    assert gmail_sender["domain_name"] == "nenotechnology.com"
    assert gmail_sender["is_send_ready"] is True

    # 2. Adding an Outlook account without any custom domain
    outlook_sender = create_sender_account(
        db=session,
        user_id=user.id,
        org_id=org.id,
        email="outreach@outlook.com",
        display_name="Outreach Outlook",
        provider="microsoft_365",
    )
    assert outlook_sender["email"] == "outreach@outlook.com"
    assert outlook_sender["domain_name"] == "outlook.com"
    session.close()


