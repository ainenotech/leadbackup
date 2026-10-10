import os
import json
import base64
import time
import email
from email.message import EmailMessage
import requests
from requests.exceptions import HTTPError
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from .base import SendChannel
from Backend.channels_models import OrgMailConnection
from services.secret_store import decrypt_secret, encrypt_secret
from services.oauth_service import refresh_google_token

class GoogleOAuthChannel(SendChannel):
    """Implementation of the Google OAuth channel for sending via Gmail API and reading replies."""
    
    def _refresh_access_token(self, db: Session, connection: OrgMailConnection) -> str:
        """Helper to get a fresh access token from the refresh token."""
        refresh_token = decrypt_secret(connection.encrypted_secret)
        if not refresh_token:
            raise ValueError("No refresh token available.")
            
        try:
            result = refresh_google_token(refresh_token)
            access_token = result.get("access_token")
            new_refresh_token = result.get("refresh_token")
            
            # If Google rotated the refresh token, save it securely
            if new_refresh_token:
                connection.encrypted_secret = encrypt_secret(new_refresh_token)
                db.commit()
                
            return access_token
        except HTTPError as e:
            if e.response.status_code == 400 and "invalid_grant" in e.response.text:
                connection.status = "needs_reconnect"
                db.commit()
                raise ValueError("Refresh token expired or revoked. Needs reconnect.")
            raise

    def get_status(self, db: Session, connection: OrgMailConnection) -> str:
        if connection.status == "needs_reconnect":
            return "needs_reconnect"
        try:
            self._refresh_access_token(db, connection)
            return "active"
        except Exception:
            return connection.status

    def revoke_access(self, db: Session, connection: OrgMailConnection) -> bool:
        refresh_token = decrypt_secret(connection.encrypted_secret)
        if refresh_token:
            try:
                # Fire and forget revocation
                requests.post("https://oauth2.googleapis.com/revoke", data={"token": refresh_token}, timeout=5)
            except Exception:
                pass
        
        connection.status = "needs_reconnect"
        connection.encrypted_secret = encrypt_secret("")
        db.commit()
        return True

    def send_email(
        self, 
        db: Session, 
        connection: OrgMailConnection, 
        to_email: str, 
        subject: str, 
        body_html: str,
        body_text: str = None,
        reply_to: str = None,
        unsubscribe_link: str = None,
        headers: dict = None
    ) -> dict:
        access_token = self._refresh_access_token(db, connection)
        
        # Build MIME message
        msg = EmailMessage()
        msg["To"] = to_email
        msg["From"] = connection.email
        msg["Subject"] = subject
        
        if reply_to:
            msg["Reply-To"] = reply_to
            
        if unsubscribe_link:
            msg["List-Unsubscribe"] = f"<{unsubscribe_link}>"
            msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
            
        if headers:
            for k, v in headers.items():
                msg[k] = v
                
        if body_text and body_html:
            msg.set_content(body_text)
            msg.add_alternative(body_html, subtype='html')
        elif body_html:
            msg.set_content(body_html, subtype='html')
        else:
            msg.set_content(body_text or "")
            
        # Base64url encode the entire MIME message
        raw_string = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
        
        # Send via Gmail API
        url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
        
        max_retries = 3
        backoff = 2
        
        for attempt in range(max_retries):
            resp = requests.post(
                url,
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                json={"raw": raw_string},
                timeout=15
            )
            
            if resp.status_code == 429:
                if attempt < max_retries - 1:
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                raise Exception("Rate limit exceeded (429) after retries.")
            
            if resp.status_code == 403:
                err_text = resp.text.lower()
                if "rate_limit_exceeded" in err_text or "user ratelimit" in err_text:
                    if attempt < max_retries - 1:
                        time.sleep(backoff)
                        backoff *= 2
                        continue
                raise Exception(f"Gmail API 403 Forbidden: {resp.text}")
                
            if resp.status_code >= 400:
                raise Exception(f"Gmail API error ({resp.status_code}): {resp.text}")

            data = resp.json()
            return {"provider_message_id": data.get("id"), "status": "sent"}
            
        raise Exception("Failed to send email after max retries")

    def fetch_replies(self, db: Session, connection: OrgMailConnection, since_timestamp: datetime) -> list:
        access_token = self._refresh_access_token(db, connection)
        
        # Format for Gmail 'q' parameter: epoch timestamp
        epoch = int(since_timestamp.timestamp())
        query = f"after:{epoch}"
        
        url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
        
        replies = []
        page_token = None
        
        while True:
            params = {"q": query, "maxResults": 100}
            if page_token:
                params["pageToken"] = page_token
                
            resp = requests.get(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
                params=params,
                timeout=15
            )
            
            if resp.status_code in (401, 403):
                raise Exception(f"Failed to list messages: HTTP {resp.status_code}")
                
            resp.raise_for_status()
            data = resp.json()
            
            messages = data.get("messages", [])
            for msg_meta in messages:
                msg_id = msg_meta["id"]
                # Fetch full message
                msg_resp = requests.get(
                    f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={"format": "full"},
                    timeout=10
                )
                if msg_resp.status_code == 200:
                    full_msg = msg_resp.json()
                    parsed = self._parse_gmail_message(full_msg)
                    if parsed:
                        replies.append(parsed)
                        
            page_token = data.get("nextPageToken")
            if not page_token:
                break
                
        return replies
        
    def _parse_gmail_message(self, full_msg: dict) -> dict:
        """Parses the Gmail API message payload into our standard reply format."""
        headers = {h["name"].lower(): h["value"] for h in full_msg["payload"].get("headers", [])}
        
        sender = headers.get("from", "")
        subject = headers.get("subject", "")
        date_str = headers.get("date", "")
        message_id = headers.get("message-id", "")
        in_reply_to = headers.get("in-reply-to", "")
        
        body_text = ""
        body_html = ""
        
        def _extract_parts(parts):
            nonlocal body_text, body_html
            for part in parts:
                mime_type = part.get("mimeType")
                if mime_type == "text/plain" and "data" in part.get("body", {}):
                    body_text += base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                elif mime_type == "text/html" and "data" in part.get("body", {}):
                    body_html += base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                elif "parts" in part:
                    _extract_parts(part["parts"])
                    
        if "parts" in full_msg["payload"]:
            _extract_parts(full_msg["payload"]["parts"])
        else:
            mime_type = full_msg["payload"].get("mimeType")
            if "data" in full_msg["payload"].get("body", {}):
                data = base64.urlsafe_b64decode(full_msg["payload"]["body"]["data"]).decode("utf-8")
                if mime_type == "text/plain":
                    body_text = data
                else:
                    body_html = data
                    
        return {
            "id": message_id,
            "sender": sender,
            "subject": subject,
            "body_text": body_text,
            "body_html": body_html,
            "date": date_str,
            "in_reply_to": in_reply_to
        }

    def check_health(self) -> bool:
        return True
        
    def describe_requirements(self) -> dict:
        return {"description": "Google OAuth connection."}
