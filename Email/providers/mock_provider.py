"""Mock Sending Provider for local development and testing without AWS credentials.

Simulates AWS SES identity creation, Easy-DKIM CNAME token generation,
and custom MAIL FROM subdomain configuration.
"""

import hashlib
import logging
import uuid
from typing import Dict, List, Optional

from .base import (
    DkimRecord,
    IdentityResult,
    MailFromRecord,
    SendingProvider,
)

logger = logging.getLogger("mock_provider")


class MockSESProvider(SendingProvider):
    """Simulated AWS SES Provider for local environments."""

    def create_identity(
        self,
        domain: str,
        configuration_set_name: Optional[str] = None,
        mail_from_subdomain: Optional[str] = None,
    ) -> IdentityResult:
        logger.info("[MockSES] Creating simulated identity for domain: %s", domain)
        mf_sub = mail_from_subdomain or "mail"
        mail_from_domain = f"{mf_sub}.{domain}"

        # Generate 3 deterministic mock DKIM tokens based on domain
        tokens = [
            hashlib.md5(f"{domain}-ses-token-{i}".encode()).hexdigest()[:16]
            for i in range(1, 4)
        ]
        dkim_records = [
            DkimRecord(
                record_type="CNAME",
                host=f"{token}._domainkey.{domain}",
                value=f"{token}.dkim.amazonses.com",
            )
            for token in tokens
        ]
        mail_from_records = MailFromRecord(
            mx_host=mail_from_domain,
            mx_value="10 feedback-smtp.us-east-1.amazonses.com",
            spf_host=mail_from_domain,
            spf_value='"v=spf1 include:amazonses.com ~all"',
        )

        return IdentityResult(
            identity_ref=domain,
            dkim_records=dkim_records,
            mail_from_records=mail_from_records,
            dkim_status="pending",
            verification_status="pending",
            verified_for_sending=False,
            mail_from_status="pending",
            configuration_set=configuration_set_name,
        )

    def get_identity_status(self, domain: str) -> IdentityResult:
        logger.info("[MockSES] Getting status for domain: %s", domain)
        tokens = [
            hashlib.md5(f"{domain}-ses-token-{i}".encode()).hexdigest()[:16]
            for i in range(1, 4)
        ]
        dkim_records = [
            DkimRecord(
                record_type="CNAME",
                host=f"{token}._domainkey.{domain}",
                value=f"{token}.dkim.amazonses.com",
            )
            for token in tokens
        ]
        return IdentityResult(
            identity_ref=domain,
            dkim_records=dkim_records,
            dkim_status="pending",
            verification_status="pending",
            verified_for_sending=False,
            mail_from_status="pending",
        )

    def delete_identity(self, domain: str) -> bool:
        logger.info("[MockSES] Deleted simulated identity: %s", domain)
        return True

    def send_message(
        self,
        from_address: str,
        to_address: str,
        subject: str,
        html_body: str,
        reply_to: Optional[str] = None,
        configuration_set: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> str:
        mock_id = f"mock-msg-{uuid.uuid4()}"
        logger.info("[MockSES] Simulated send from %s to %s (id=%s)", from_address, to_address, mock_id)
        return mock_id

    def create_configuration_set(self, name: str) -> bool:
        logger.info("[MockSES] Created simulated config set: %s", name)
        return True

    def delete_configuration_set(self, name: str) -> bool:
        logger.info("[MockSES] Deleted simulated config set: %s", name)
        return True
