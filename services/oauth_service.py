import os
from dotenv import load_dotenv
import msal
import logging
from typing import Dict, Any, Optional

load_dotenv()

logger = logging.getLogger(__name__)

def get_msal_app() -> msal.ConfidentialClientApplication:
    client_id = os.getenv("MS_OAUTH_CLIENT_ID")
    client_secret = os.getenv("MS_OAUTH_CLIENT_SECRET")
    authority = os.getenv("MS_OAUTH_AUTHORITY", "https://login.microsoftonline.com/common")
    
    if not client_id or not client_secret:
        raise ValueError("Microsoft OAuth credentials not configured.")
        
    return msal.ConfidentialClientApplication(
        client_id,
        authority=authority,
        client_credential=client_secret
    )

def build_auth_url_and_flow(scopes: list[str], redirect_uri: str) -> Dict[str, Any]:
    """Build the authorization URL and internal PKCE flow state."""
    app = get_msal_app()
    flow = app.initiate_auth_code_flow(scopes=scopes, redirect_uri=redirect_uri)
    if "error" in flow:
        raise ValueError(flow.get("error_description") or flow.get("error") or "Failed to initiate Microsoft OAuth flow")
    return flow

def acquire_token_by_auth_code_flow(flow: Dict[str, Any], query_params: Dict[str, Any]) -> Dict[str, Any]:
    """Exchange the authorization code for tokens using the saved PKCE flow state."""
    app = get_msal_app()
    result = app.acquire_token_by_auth_code_flow(flow, query_params)
    return result

def acquire_token_by_refresh_token(refresh_token: str, scopes: list[str]) -> Dict[str, Any]:
    """Get a new access token (and possibly a new refresh token) using the refresh token."""
    app = get_msal_app()
    result = app.acquire_token_by_refresh_token(refresh_token, scopes=scopes)
    return result


import secrets
import hashlib
import base64
import json
import requests
import urllib.parse

def build_google_auth_url_and_flow(scopes: list[str], redirect_uri: str) -> Dict[str, Any]:
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    if not client_id:
        raise ValueError("Google OAuth credentials not configured.")

    # Generate PKCE verifier and challenge
    code_verifier = secrets.token_urlsafe(64)
    hasher = hashlib.sha256()
    hasher.update(code_verifier.encode("utf-8"))
    code_challenge = base64.urlsafe_b64encode(hasher.digest()).decode("utf-8").rstrip("=")
    
    state = secrets.token_urlsafe(32)
    
    # Construct Google OAuth URL
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes),
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "access_type": "offline",
        "prompt": "consent"
    })
    
    flow = {
        "state": state,
        "code_verifier": code_verifier,
        "redirect_uri": redirect_uri,
        "auth_uri": auth_url
    }
    return flow

def exchange_google_code(code: str, code_verifier: str, redirect_uri: str) -> Dict[str, Any]:
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    
    res = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "code_verifier": code_verifier,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }, timeout=10)
    
    res.raise_for_status()
    return res.json()

def refresh_google_token(refresh_token: str) -> Dict[str, Any]:
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    
    res = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }, timeout=10)
    
    res.raise_for_status()
    return res.json()

def decode_google_id_token(id_token: str) -> Dict[str, Any]:
    parts = id_token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid id_token format")
    
    payload_part = parts[1]
    # Add padding if needed
    payload_part += "=" * ((4 - len(payload_part) % 4) % 4)
    payload_json = base64.urlsafe_b64decode(payload_part).decode("utf-8")
    return json.loads(payload_json)
