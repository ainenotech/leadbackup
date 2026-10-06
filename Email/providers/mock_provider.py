"""Mock SES provider for unit testing, offline development, and sandbox verification."""

import hashlib
import logging
import os
from typing import Dict, List, Optional
from datetime import datetime, timezone

from .base import (
    CreateIdentityResult,
    DkimRecordData,
    IdentityStatusResult,
    MailFromRecordsData,
)

logger = logging.getLogger("mock_ses_provider")


class MockSESProvider:
    """Simulates AWS SESv2 API operations entirely in-memory."""

    _identities: Dict[str, Dict] = {}
    _config_sets: set = set()
    _sent_messages: List[Dict] = []

    @classmethod
    def reset(cls):
        """Reset mock state between tests."""
        cls._identities.clear()
        cls._config_sets.clear()
        cls._sent_messages.clear()

    def create_configuration_set(self, name: str) -> bool:
        self._config_sets.add(name)
        return True

    def create_identity(
        self,
        domain: str,
        configuration_set_name: Optional[str] = None,
        mail_from_subdomain: Optional[str] = "mail",
    ) -> CreateIdentityResult:
        clean_domain = domain.strip().lower()
        region = os.getenv("AWS_REGION", "us-east-1")

        # Generate 3 deterministic mock DKIM tokens based on domain
        tokens = [
            hashlib.md5(f"{clean_domain}-dkim-token-{i}".encode("utf-8")).hexdigest()[:16]
            for i in range(1, 4)
        ]

        dkim_records = [
            DkimRecordData(
                record_type="CNAME",
                host=f"{token}._domainkey.{clean_domain}",
                value=f"{token}.dkim.amazonses.com",
            )
            for token in tokens
        ]

        mail_from_records = None
        if mail_from_subdomain:
            sub = mail_from_subdomain.strip().lower()
            mail_from_records = MailFromRecordsData(
                mx_host=f"{sub}.{clean_domain}",
                mx_value=f"feedback-smtp.{region}.amazonses.com",
                spf_host=f"{sub}.{clean_domain}",
                spf_value="v=spf1 include:amazonses.com ~all",
            )

        identity_arn = f"arn:aws:ses:{region}:123456789012:identity/{clean_domain}"

        self._identities[clean_domain] = {
            "domain": clean_domain,
            "arn": identity_arn,
            "dkim_tokens": tokens,
            "dkim_status": "pending",
            "verification_status": "pending",
            "mail_from_status": "pending",
            "mail_from_subdomain": mail_from_subdomain,
            "created_at": datetime.now(timezone.utc),
        }

        return CreateIdentityResult(
            identity_ref=identity_arn,
            dkim_records=dkim_records,
            mail_from_records=mail_from_records,
        )

    def get_identity_status(self, domain: str) -> IdentityStatusResult:
        clean_domain = domain.strip().lower()
        id_data = self._identities.get(clean_domain)

        if not id_data:
            return IdentityStatusResult(
                domain=clean_domain,
                verification_status="not_started",
                dkim_status="not_started",
            )

        return IdentityStatusResult(
            domain=clean_domain,
            verification_status=id_data.get("verification_status", "pending"),
            dkim_status=id_data.get("dkim_status", "pending"),
            mail_from_status=id_data.get("mail_from_status", "pending"),
        )

    def set_verified(self, domain: str, verified: bool = True):
        """Helper to simulate SES verification in tests or local dev."""
        clean_domain = domain.strip().lower()
        if clean_domain in self._identities:
            status = "success" if verified else "pending"
            self._identities[clean_domain]["dkim_status"] = status
            self._identities[clean_domain]["verification_status"] = status
            self._identities[clean_domain]["mail_from_status"] = status

    def delete_identity(self, domain: str) -> bool:
        clean_domain = domain.strip().lower()
        if clean_domain in self._identities:
            del self._identities[clean_domain]
            return True
        return False

    def send_email(
        self,
        from_email: str,
        to_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        configuration_set_name: Optional[str] = None,
    ) -> Dict:
        """Simulate SES sending."""
        msg_id = f"mock-ses-{hashlib.md5(f'{from_email}{to_email}{datetime.now(timezone.utc)}'.encode()).hexdigest()[:20]}"
        record = {
            "message_id": msg_id,
            "from_email": from_email,
            "to_email": to_email,
            "subject": subject,
            "body": body,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }
        self._sent_messages.append(record)
        logger.info("[MockSES] Email dispatched from %s to %s (id: %s)", from_email, to_email, msg_id)
        return {"MessageId": msg_id, "status": "sent"}
