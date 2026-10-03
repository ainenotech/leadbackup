import os
import logging
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import requests
import urllib.parse
from urllib.parse import urlparse

from sqlalchemy.orm import Session
from Backend.channels_models import OrgMailConnection
from services.secret_store import encrypt_secret, decrypt_secret
from services.oauth_service import acquire_token_by_refresh_token
from Email.channels.base import SendChannel
from Email.tracking import rewrite_links_for_tracking, attach_pixel_and_unsub

logger = logging.getLogger(__name__)

class MicrosoftOAuthChannel(SendChannel):
    """Channel adapter for Microsoft 365 OAuth."""

    def _get_access_token(self, db: Session, connection: OrgMailConnection) -> str:
        """Retrieves access token, refreshing if necessary and storing the new refresh token."""
        try:
            refresh_token = decrypt_secret(connection.encrypted_secret)
        except Exception as e:
            connection.status = "needs_reconnect"
            connection.last_error = f"Failed to decrypt refresh token: {str(e)}"
            db.commit()
            raise ValueError("Token decryption failed. Needs reconnect.")

        # In a real app we'd cache the access token in memory with an expiry.
        # For simplicity and correctness in this demo, we acquire it on demand.
        result = acquire_token_by_refresh_token(refresh_token, scopes=connection.config.get("scopes", []))
        
        if "error" in result:
            connection.status = "needs_reconnect"
            connection.last_error = f"OAuth error: {result.get('error_description', result.get('error'))}"
            db.commit()
            raise ValueError(f"Failed to acquire token: {connection.last_error}")

        # Handle token rotation
        new_refresh = result.get("refresh_token")
        if new_refresh and new_refresh != refresh_token:
            connection.encrypted_secret = encrypt_secret(new_refresh)
            db.commit()

        return result["access_token"]


    def send_email(
        self,
        db: Session,
        connection: OrgMailConnection,
        to_email: str,
        subject: str,
        body_html: str,
        body_text: str,
        campaign_id: Optional[str] = None,
        lead_id: Optional[str] = None,
        reply_to: Optional[str] = None,
    ) -> Dict:
        """Send email using Microsoft Graph API."""
        
        # Enforce daily cap (already enforced in get_mailer_for_org, but double check)
        today = datetime.now(timezone.utc).date()
        if connection.sent_today_date != today:
            connection.sent_today = 0
            connection.sent_today_date = today
            db.commit()
            
        if connection.sent_today >= connection.daily_cap:
            raise ValueError(f"Daily cap of {connection.daily_cap} reached for {connection.email}")

        access_token = self._get_access_token(db, connection)
        
        # Apply tracking and unsubscribe footer
        if campaign_id and lead_id:
            body_html, body_text = rewrite_links_for_tracking(body_html, body_text, campaign_id, lead_id)
            body_html, body_text = attach_pixel_and_unsub(body_html, body_text, campaign_id, lead_id)
            
        message = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "HTML",
                    "content": body_html
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": to_email
                        }
                    }
                ],
                "internetMessageHeaders": []
            },
            "saveToSentItems": "true"
        }
        
        if reply_to:
            message["message"]["replyTo"] = [{"emailAddress": {"address": reply_to}}]
            
        if campaign_id and lead_id:
            # We can use internetMessageHeaders to add List-Unsubscribe
            base_url = os.getenv("FORM_BASE_URL", "http://localhost:8000").rstrip('/')
            domain = urlparse(base_url).netloc
            unsub_url = f"{base_url}/api/track/unsubscribe?c={campaign_id}&l={lead_id}"
            
            message["message"]["internetMessageHeaders"].append({
                "name": "List-Unsubscribe",
                "value": f"<{unsub_url}>"
            })
            # Also add a custom header for campaign tracking in bounces/replies
            message["message"]["internetMessageHeaders"].append({
                "name": "X-Campaign-ID",
                "value": campaign_id
            })
            message["message"]["internetMessageHeaders"].append({
                "name": "X-Lead-ID",
                "value": lead_id
            })

        endpoint = "https://graph.microsoft.com/v1.0/me/sendMail"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Send with retry for 429
        max_retries = 3
        for attempt in range(max_retries):
            resp = requests.post(endpoint, headers=headers, json=message, timeout=15)
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", "5"))
                if attempt < max_retries - 1:
                    time.sleep(retry_after)
                    continue
            
            if resp.status_code in (202, 200):
                connection.sent_today += 1
                db.commit()
                # Apply spacing
                spacing = int(os.getenv("SENDING_MINIMUM_SPACING_SECONDS", "5"))
                if spacing > 0:
                    time.sleep(spacing)
                    
                return {"status": "sent", "channel": "microsoft_oauth"}
                
            raise ValueError(f"Graph API Error: {resp.status_code} {resp.text}")
            
        raise ValueError("Exceeded max retries on 429 Too Many Requests")


    def poll_replies(self, db: Session, connection: OrgMailConnection) -> List[Dict]:
        """Poll the inbox for replies since last_polled_at using Microsoft Graph."""
        access_token = self._get_access_token(db, connection)
        
        last_polled = connection.last_polled_at
        if not last_polled:
            # If never polled, look back 7 days
            last_polled = datetime.now(timezone.utc) - timedelta(days=7)
            
        # Graph API requires ISO 8601 strings in UTC like 2023-10-01T12:00:00Z
        filter_date = last_polled.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        endpoint = f"https://graph.microsoft.com/v1.0/me/messages"
        # We only need inbox messages, not sent items
        params = {
            "$filter": f"receivedDateTime ge {filter_date}",
            "$select": "id,subject,bodyPreview,body,from,receivedDateTime,internetMessageHeaders",
            "$orderby": "receivedDateTime asc",
            "$top": 50
        }
        
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        resp = requests.get(endpoint, headers=headers, params=params, timeout=15)
        if resp.status_code != 200:
            if resp.status_code == 401:
                connection.status = "needs_reconnect"
                connection.last_error = "Unauthorized to read messages"
                db.commit()
            return []
            
        data = resp.json()
        messages = data.get("value", [])
        
        results = []
        highest_date = last_polled
        
        for msg in messages:
            # Check privacy constraints: We ONLY care if the message matches our campaigns.
            # The reply worker pipeline handles the deduplication and matching (via internetMessageHeaders or subject/email)
            # So we pass it up in the format it expects.
            
            # Format the output so the reply_worker pipeline can process it natively
            # The existing pipeline expects a generic dict
            
            headers = msg.get("internetMessageHeaders", [])
            header_dict = {h["name"].lower(): h["value"] for h in headers}
            
            # For privacy, if the worker rejects it, it will be discarded.
            results.append({
                "message_id": msg.get("id"),
                "subject": msg.get("subject", ""),
                "sender_email": msg.get("from", {}).get("emailAddress", {}).get("address", ""),
                "body": msg.get("body", {}).get("content", ""),
                "received_at": msg.get("receivedDateTime"),
                "headers": header_dict
            })
            
            # Track highest date
            try:
                msg_date = datetime.strptime(msg.get("receivedDateTime")[:19], "%Y-%m-%dT%H:%M:%S")
                msg_date = msg_date.replace(tzinfo=timezone.utc)
                if msg_date > highest_date:
                    highest_date = msg_date
            except Exception:
                pass
                
        # Update last_polled_at
        connection.last_polled_at = highest_date
        db.commit()
        
        return results
