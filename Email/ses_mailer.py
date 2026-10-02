"""SES-backed Mailer implementation.

Sends emails through AWS SES using the provider interface, with
tracking pixel, click rewriting, unsubscribe headers, and Reply-To.
"""

import os
from typing import Optional

from .base import Mailer
from .tracking import get_unsubscribe_url, prepare_tracked_body


class SESMailer(Mailer):
    """Mailer that sends through AWS SES with custom headers."""

    def __init__(
        self,
        from_address: str,
        from_name: str,
        reply_to: str,
        configuration_set: Optional[str] = None,
        domain_id: Optional[str] = None,
    ):
        self._from_address = from_address
        self._from_name = from_name
        self._reply_to = reply_to
        self._configuration_set = configuration_set
        self._domain_id = domain_id

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        token: Optional[str] = None,
        sender_email: Optional[str] = None,
    ) -> str:
        from Email.providers.ses_provider import SESProvider

        # Prepare tracked HTML body
        api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
        html_body = prepare_tracked_body(
            body=body,
            token=token,
            api_base_url=api_base_url,
            sender_email=self._from_address,
            from_name=self._from_name,
        )

        # Build From header with display name
        if self._from_name:
            from_header = f"{self._from_name} <{self._from_address}>"
        else:
            from_header = self._from_address

        # Build custom headers
        headers = {}
        unsub_url = get_unsubscribe_url(token, api_base_url)
        if unsub_url:
            headers["List-Unsubscribe"] = f"<{unsub_url}>"
            headers["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"

        # Send via SES provider
        provider = SESProvider()
        message_id = provider.send_message(
            from_address=from_header,
            to_address=to_email,
            subject=subject,
            html_body=html_body,
            reply_to=self._reply_to,
            configuration_set=self._configuration_set,
            headers=headers if headers else None,
        )

        # Record send in stats
        if self._domain_id:
            try:
                from Backend.db import SessionLocal
                from services.domain_auth_service import record_send

                db = SessionLocal()
                try:
                    record_send(db, self._domain_id)
                finally:
                    db.close()
            except Exception:
                pass  # Don't fail the send if stats recording fails

        return message_id or f"ses-{to_email}"
