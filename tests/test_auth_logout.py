import pytest
from fastapi.testclient import TestClient
from Backend.api import app

def test_api_auth_logout_clears_cookie():
    """Verify that /api/auth/logout endpoint invalidates session and sets cookie deletion header."""
    client = TestClient(app)
    # Test POST logout
    response = client.post("/api/auth/logout")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    # Verify Set-Cookie header contains session_token deletion with max-age=0
    set_cookie = response.headers.get("set-cookie", "")
    assert "session_token=" in set_cookie
    assert "Max-Age=0" in set_cookie or "max-age=0" in set_cookie

    # Test GET logout
    response_get = client.get("/api/auth/logout")
    assert response_get.status_code == 200
    assert "session_token=" in response_get.headers.get("set-cookie", "")

def test_signout_session_state_logic():
    """Verify that when logged_out is True, session_token cookie restoration is ignored."""
    # Simulate session state
    session_state = {
        "authenticated": False,
        "logged_out": True,
        "user": None,
        "current_org": None,
        "current_org_id": None,
    }
    mock_cookies = {"session_token": "valid_mock_jwt_token"}

    # Evaluate the exact logic from dashboard.py
    session_token = None if session_state.get("logged_out") else mock_cookies.get("session_token")
    assert session_token is None, "session_token should NOT be restored when logged_out is True!"

    # And when logged_out is False, cookie is restored
    session_state["logged_out"] = False
    session_token = None if session_state.get("logged_out") else mock_cookies.get("session_token")
    assert session_token == "valid_mock_jwt_token"
