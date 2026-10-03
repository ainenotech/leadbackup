import pytest
import requests
import json
import base64
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

import os
# Force throwaway SQLite for tests
os.environ["DATABASE_URL"] = "sqlite:///./test_google_oauth.db"

from Backend.db import Base, SessionLocal, engine
from Backend.channels_models import OrgMailConnection, OAuthFlowState
from Backend.auth_models import Organization, OrganizationMember, User
from Email.channels.google_oauth_channel import GoogleOAuthChannel
from services.secret_store import encrypt_secret
from fastapi.testclient import TestClient
from Backend.api import app

client = TestClient(app)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestSessionLocal = sessionmaker(bind=test_engine)

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    db = TestSessionLocal()
    # Seed org
    org = Organization(id="test_org", name="Test Org", slug="test-org")
    user = User(id="test_user", email="admin@test.com")
    member = OrganizationMember(organization_id="test_org", user_id="test_user", role="owner", status="active")
    db.add(org)
    db.add(user)
    db.add(member)
    db.commit()
    yield
    db.close()
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def db_session():
    db = TestSessionLocal()
    yield db
    db.rollback()
    db.query(OAuthFlowState).delete()
    db.query(OrgMailConnection).delete()
    db.commit()
    db.close()

from Backend.db import get_db

def override_get_db():
    try:
        db = TestSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

def test_google_oauth_callback_success(db_session):
    # Setup state
    import hashlib
    state = "test_state"
    state_hash = hashlib.sha256(state.encode("utf-8")).hexdigest()
    
    flow = {
        "state": state,
        "code_verifier": "verifier",
        "redirect_uri": "http://localhost/callback"
    }
    
    flow_state = OAuthFlowState(
        state_hash=state_hash,
        provider="google",
        organization_id="test_org",
        user_id="test_user",
        expected_email="test@gmail.com",
        flow_data_encrypted=encrypt_secret(json.dumps(flow)),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15)
    )
    db_session.add(flow_state)
    db_session.commit()

    with patch('Backend.channels_endpoints.exchange_google_code') as mock_exchange, \
         patch('Backend.channels_endpoints.decode_google_id_token') as mock_decode:
        
        mock_exchange.return_value = {
            "access_token": "acc",
            "refresh_token": "ref",
            "id_token": "id",
            "scope": "gmail.send"
        }
        mock_decode.return_value = {"email": "test@gmail.com", "sub": "123"}
        
        resp = client.get("/api/channels/oauth/google/callback", params={"state": state, "code": "auth_code"})
        assert resp.status_code == 200
        assert "Connection Successful" in resp.text
        
        conn = db_session.query(OrgMailConnection).filter_by(email="test@gmail.com").first()
        assert conn is not None
        assert conn.channel == "google_oauth"
        assert conn.daily_cap == 500 # personal mailbox cap

def test_google_oauth_callback_mismatch(db_session):
    import hashlib
    state = "test_state_2"
    state_hash = hashlib.sha256(state.encode("utf-8")).hexdigest()
    
    flow = {
        "state": state,
        "code_verifier": "verifier",
        "redirect_uri": "http://localhost/callback"
    }
    
    flow_state = OAuthFlowState(
        state_hash=state_hash,
        provider="google",
        organization_id="test_org",
        user_id="test_user",
        expected_email="target@gmail.com",
        flow_data_encrypted=encrypt_secret(json.dumps(flow)),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15)
    )
    db_session.add(flow_state)
    db_session.commit()

    with patch('Backend.channels_endpoints.exchange_google_code') as mock_exchange, \
         patch('Backend.channels_endpoints.decode_google_id_token') as mock_decode:
        
        mock_exchange.return_value = {
            "access_token": "acc",
            "refresh_token": "ref",
            "id_token": "id",
            "scope": "gmail.send"
        }
        mock_decode.return_value = {"email": "wrong@gmail.com", "sub": "123"} # Mismatch!
        
        resp = client.get("/api/channels/oauth/google/callback", params={"state": state, "code": "auth_code"})
        assert resp.status_code == 200
        assert "Account Mismatch" in resp.text
        
        # Ensures no connection was saved
        conn = db_session.query(OrgMailConnection).filter_by(email="target@gmail.com").first()
        assert conn is None

def test_refresh_failure_sets_needs_reconnect(db_session):
    conn = OrgMailConnection(
        organization_id="test_org",
        email="refresh@gmail.com",
        domain="gmail.com",
        channel="google_oauth",
        status="active",
        encrypted_secret=encrypt_secret("bad_token"),
        daily_cap=500
    )
    db_session.add(conn)
    db_session.commit()
    
    channel = GoogleOAuthChannel()
    
    with patch('Email.channels.google_oauth_channel.refresh_google_token') as mock_refresh:
        import requests
        err_response = requests.Response()
        err_response.status_code = 400
        err_response._content = b'{"error":"invalid_grant"}'
        mock_refresh.side_effect = requests.exceptions.HTTPError("invalid_grant", response=err_response)
        
        with pytest.raises(ValueError):
            channel._refresh_access_token(db_session, conn)
            
        assert conn.status == "needs_reconnect"

def test_send_mime_unsubscribe(db_session):
    conn = OrgMailConnection(
        organization_id="test_org",
        email="send@gmail.com",
        domain="gmail.com",
        channel="google_oauth",
        status="active",
        encrypted_secret=encrypt_secret("token"),
        daily_cap=500
    )
    db_session.add(conn)
    db_session.commit()
    
    channel = GoogleOAuthChannel()
    
    with patch.object(channel, '_refresh_access_token', return_value="acc_token"), \
         patch('requests.post') as mock_post:
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "msg123"}
        mock_post.return_value = mock_resp
        
        channel.send_email(
            db=db_session,
            connection=conn,
            to_email="rcpt@test.com",
            subject="Test",
            body_html="<p>Test</p>",
            unsubscribe_link="http://unsub"
        )
        
        # Verify MIME contains unsubscribe
        call_kwargs = mock_post.call_args[1]
        raw_b64 = call_kwargs["json"]["raw"]
        raw_bytes = base64.urlsafe_b64decode(raw_b64)
        raw_str = raw_bytes.decode('utf-8')
        
        assert "List-Unsubscribe: <http://unsub>" in raw_str
        assert "List-Unsubscribe-Post: List-Unsubscribe=One-Click" in raw_str
        
def test_revoke_called_on_disconnect(db_session):
    conn = OrgMailConnection(
        organization_id="test_org",
        email="revoke@gmail.com",
        domain="gmail.com",
        channel="google_oauth",
        status="active",
        encrypted_secret=encrypt_secret("token"),
        daily_cap=500
    )
    db_session.add(conn)
    db_session.commit()
    
    channel = GoogleOAuthChannel()
    
    with patch('requests.post') as mock_post:
        channel.revoke_access(db_session, conn)
        mock_post.assert_called_with("https://oauth2.googleapis.com/revoke", data={"token": "token"}, timeout=5)
        
        assert conn.status == "needs_reconnect"
        # Secret should be wiped
        from services.secret_store import decrypt_secret
        assert decrypt_secret(conn.encrypted_secret) == ""
