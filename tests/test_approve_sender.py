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

