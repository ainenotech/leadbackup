"""Centralized Microsoft Graph app-only (client credentials) auth helper,
shared by Email (OutlookMailer) and Calendar (OutlookCalendar). Uses MSAL's
confidential-client flow against a single Azure AD app registration with
Mail.Send, Mail.Read and Calendars.ReadWrite application permissions
granted (with admin consent) so the agent can act on the shared support
mailbox without any per-user interactive sign-in.
"""

import os
import time
from typing import Optional

import msal
from dotenv import load_dotenv

import utils.dns_patch  # Ensures reliable DNS resolution for Microsoft Graph and login

load_dotenv()

MS_TENANT_ID = os.getenv("MS_TENANT_ID", "")
MS_CLIENT_ID = os.getenv("MS_CLIENT_ID", "")
MS_CLIENT_SECRET = os.getenv("MS_CLIENT_SECRET", "")
MS_AUTHORITY = f"https://login.microsoftonline.com/{MS_TENANT_ID}" if MS_TENANT_ID else ""

# App-only Graph calls use the fixed .default scope; the actual permissions
# (Mail.Send, Mail.Read, Calendars.ReadWrite) are whatever was granted admin
# consent on the app registration in Azure AD.
GRAPH_SCOPE = ["https://graph.microsoft.com/.default"]

# The shared support mailbox that mail is sent from / read from and whose
# calendar is used for scheduling. Can be an email address or object id.
MS_SENDER_EMAIL = os.getenv("MS_SENDER_EMAIL", "support@nenotechnology.com")

_app: Optional["msal.ConfidentialClientApplication"] = None
_cached_token: Optional[str] = None
_cached_expiry: float = 0.0


def _get_app() -> "msal.ConfidentialClientApplication":
    global _app
    if _app is None:
        if not (MS_TENANT_ID and MS_CLIENT_ID and MS_CLIENT_SECRET):
            raise RuntimeError(
                "Microsoft Graph credentials are missing. Set MS_TENANT_ID, "
                "MS_CLIENT_ID and MS_CLIENT_SECRET in .env (see .env.example). "
                "These come from an Azure AD app registration with Mail.Send, "
                "Mail.Read and Calendars.ReadWrite application permissions, "
                "granted admin consent."
            )
        _app = msal.ConfidentialClientApplication(
            client_id=MS_CLIENT_ID,
            client_credential=MS_CLIENT_SECRET,
            authority=MS_AUTHORITY,
        )
    return _app


def get_graph_token() -> str:
    """Returns a valid app-only Microsoft Graph access token, caching it
    in-process until shortly before it expires."""
    global _cached_token, _cached_expiry

    if _cached_token and time.time() < _cached_expiry - 60:
        return _cached_token

    app = _get_app()
    result = app.acquire_token_silent(GRAPH_SCOPE, account=None)
    if not result:
        result = app.acquire_token_for_client(scopes=GRAPH_SCOPE)

    if not result or "access_token" not in result:
        error = (result or {}).get("error", "unknown_error")
        description = (result or {}).get("error_description", "no details returned")
        raise RuntimeError(f"Failed to acquire Microsoft Graph token: {error}: {description}")

    _cached_token = result["access_token"]
    _cached_expiry = time.time() + int(result.get("expires_in", 3600))
    return _cached_token


def get_graph_headers() -> dict:
    """Convenience helper: bearer-token headers ready to pass to `requests`."""
    return {
        "Authorization": f"Bearer {get_graph_token()}",
        "Content-Type": "application/json",
    }
