"""AWS SES implementation of the SendingProvider interface.

Uses boto3 SESv2 client. AWS credentials are resolved exclusively from
the standard credential chain (IAM role, instance profile, environment
variables). Credentials are NEVER read from application config, .env
files, or database.
"""

import logging
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional

from .base import (
    DkimRecord,
    IdentityResult,
    MailFromRecord,
    SendingProvider,
)

logger = logging.getLogger("ses_provider")

_DEFAULT_REGION = "us-east-1"
_DEFAULT_MAIL_FROM_SUB = "mail"


def _get_region() -> str:
    return os.getenv("AWS_SES_REGION", _DEFAULT_REGION)


def has_aws_credentials() -> bool:
    """Check if AWS credentials are available in environment or boto3 chain."""
    if os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"):
        return True
    try:
        import boto3
        session = boto3.Session(region_name=_get_region())
        credentials = session.get_credentials()
        return credentials is not None and credentials.access_key is not None
    except Exception:
        return False


def _get_client():
    """Lazy-import boto3 and create a SESv2 client.
    Supports AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY from .env or standard AWS chain.
    """
    import boto3  # noqa: local import — boto3 is optional until actually used

    region = _get_region()
    kwargs = {"region_name": region}
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    if aws_access_key and aws_secret_key:
        kwargs["aws_access_key_id"] = aws_access_key
        kwargs["aws_secret_access_key"] = aws_secret_key
    aws_session_token = os.getenv("AWS_SESSION_TOKEN")
    if aws_session_token:
        kwargs["aws_session_token"] = aws_session_token

    return boto3.client("sesv2", **kwargs)


class SESProvider(SendingProvider):
    """Amazon SES (v2 API) implementation."""

    # ── Identity management ──────────────────────────────────

    def create_identity(
        self,
        domain: str,
        configuration_set_name: Optional[str] = None,
        mail_from_subdomain: Optional[str] = None,
    ) -> IdentityResult:
        client = _get_client()
        region = _get_region()

        kwargs: Dict = {
            "EmailIdentity": domain,
            "DkimSigningAttributes": {
                "DomainSigningAttributesOrigin": "AWS_SES",
            },
        }
        if configuration_set_name:
            kwargs["ConfigurationSetName"] = configuration_set_name

        resp = client.create_email_identity(**kwargs)

        # Extract DKIM tokens
        dkim_attrs = resp.get("DkimAttributes", {})
        tokens = dkim_attrs.get("Tokens", [])
        dkim_records = [
            DkimRecord(
                record_type="CNAME",
                host=f"{token}._domainkey.{domain}",
                value=f"{token}.dkim.amazonses.com",
            )
            for token in tokens
        ]

        # Set up custom MAIL FROM subdomain
        mf_sub = mail_from_subdomain or _DEFAULT_MAIL_FROM_SUB
        mail_from_domain = f"{mf_sub}.{domain}"
        mail_from_records = None
        try:
            client.put_email_identity_mail_from_attributes(
                EmailIdentity=domain,
                MailFromDomain=mail_from_domain,
                BehaviorOnMxFailure="USE_DEFAULT_VALUE",
            )
            mail_from_records = MailFromRecord(
                mx_host=mail_from_domain,
                mx_value=f"10 feedback-smtp.{region}.amazonses.com",
                spf_host=mail_from_domain,
                spf_value='"v=spf1 include:amazonses.com ~all"',
            )
        except Exception as exc:
            logger.warning("Could not set custom MAIL FROM for %s: %s", domain, exc)

        return IdentityResult(
            identity_ref=domain,
            dkim_records=dkim_records,
            mail_from_records=mail_from_records,
            dkim_status=dkim_attrs.get("Status", "PENDING").lower(),
            verification_status="pending",
            verified_for_sending=resp.get("VerifiedForSendingStatus", False),
            mail_from_status="pending",
            configuration_set=configuration_set_name,
        )

    def get_identity_status(self, domain: str) -> IdentityResult:
        client = _get_client()
        region = _get_region()

        resp = client.get_email_identity(EmailIdentity=domain)

        dkim_attrs = resp.get("DkimAttributes", {})
        tokens = dkim_attrs.get("Tokens", [])
        dkim_records = [
            DkimRecord(
                record_type="CNAME",
                host=f"{token}._domainkey.{domain}",
                value=f"{token}.dkim.amazonses.com",
            )
            for token in tokens
        ]

        mf_attrs = resp.get("MailFromAttributes", {})
        mf_domain = mf_attrs.get("MailFromDomain", "")
        mail_from_records = None
        if mf_domain:
            mail_from_records = MailFromRecord(
                mx_host=mf_domain,
                mx_value=f"10 feedback-smtp.{region}.amazonses.com",
                spf_host=mf_domain,
                spf_value='"v=spf1 include:amazonses.com ~all"',
            )

        return IdentityResult(
            identity_ref=domain,
            dkim_records=dkim_records,
            mail_from_records=mail_from_records,
            dkim_status=dkim_attrs.get("Status", "NOT_STARTED").lower(),
            verification_status=resp.get("VerificationStatus", "NOT_STARTED").lower(),
            verified_for_sending=resp.get("VerifiedForSendingStatus", False),
            mail_from_status=mf_attrs.get("MailFromDomainStatus", "NOT_STARTED").lower(),
            configuration_set=resp.get("ConfigurationSetName"),
        )

    def delete_identity(self, domain: str) -> bool:
        client = _get_client()
        try:
            client.delete_email_identity(EmailIdentity=domain)
            return True
        except Exception as exc:
            logger.error("Failed to delete SES identity %s: %s", domain, exc)
            return False

    # ── Send ─────────────────────────────────────────────────

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
        client = _get_client()

        # Build raw MIME message so we can set custom headers
        # (List-Unsubscribe, List-Unsubscribe-Post, Reply-To)
        msg = MIMEMultipart("alternative")
        msg["From"] = from_address
        msg["To"] = to_address
        msg["Subject"] = subject

        if reply_to:
            msg["Reply-To"] = reply_to

        # Inject custom headers (List-Unsubscribe, etc.)
        if headers:
            for hdr_name, hdr_value in headers.items():
                msg[hdr_name] = hdr_value

        html_part = MIMEText(html_body, "html", "utf-8")
        msg.attach(html_part)

        kwargs: Dict = {
            "Content": {
                "Raw": {
                    "Data": msg.as_bytes(),
                },
            },
        }
        if configuration_set:
            kwargs["ConfigurationSetName"] = configuration_set

        resp = client.send_email(**kwargs)
        return resp.get("MessageId", "")

    # ── Configuration sets ───────────────────────────────────

    def create_configuration_set(self, name: str) -> bool:
        client = _get_client()
        try:
            client.create_configuration_set(ConfigurationSetName=name)
            return True
        except client.exceptions.AlreadyExistsException:
            logger.info("Configuration set %s already exists", name)
            return False
        except Exception as exc:
            logger.error("Failed to create configuration set %s: %s", name, exc)
            raise

    def delete_configuration_set(self, name: str) -> bool:
        client = _get_client()
        try:
            client.delete_configuration_set(ConfigurationSetName=name)
            return True
        except Exception as exc:
            logger.error("Failed to delete configuration set %s: %s", name, exc)
            return False
