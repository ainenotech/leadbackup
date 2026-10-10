"""AWS SES v2 Provider — production domain verification and outbound delivery."""

import logging
import os
from typing import Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

from .base import (
    CreateIdentityResult,
    DkimRecordData,
    IdentityStatusResult,
    MailFromRecordsData,
)

logger = logging.getLogger("ses_provider")



def has_aws_credentials() -> bool:
    """Return True if the configured AWS credentials can be resolved."""
    if os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"):
        return True

    try:
        profile = os.getenv("AWS_PROFILE")
        session = (
            boto3.Session(profile_name=profile)
            if profile
            else boto3.Session()
        )
        return session.get_credentials() is not None
    except Exception:
        logger.exception("Could not resolve AWS credentials")
        return False



class SESProvider:
    """Production AWS SESv2 client for multi-tenant domain verification and sending."""

    def __init__(self, region_name: Optional[str] = None):
        self.region_name = region_name or os.getenv("AWS_REGION", "us-east-1")
        self._client = None

        profile = os.getenv("AWS_PROFILE")
        if profile:
            self._session = boto3.Session(
            profile_name=profile,
            region_name=self.region_name,
            )
        else:
            self._session = boto3.Session(region_name=self.region_name)

    @property
    def client(self):
        if self._client is None:
            self._client = boto3.client("sesv2", region_name=self.region_name)
        return self._client

    def create_configuration_set(self, name: str) -> bool:
        """Create an AWS SES configuration set if it does not already exist."""
        try:
            self.client.create_configuration_set(ConfigurationSetName=name)
            logger.info("Created SES configuration set: %s", name)
            return True
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("AlreadyExistsException", "ConfigurationSetAlreadyExistsException"):
                return True
            logger.warning("Error creating configuration set %s: %s", name, e)
            return False
        except Exception as e:
            logger.warning("Unexpected error creating config set %s: %s", name, e)
            return False

    def create_identity(
        self,
        domain: str,
        configuration_set_name: Optional[str] = None,
        mail_from_subdomain: Optional[str] = "mail",
    ) -> CreateIdentityResult:
        """Registers a domain identity in AWS SESv2 and requests Easy DKIM (RSA 2048)."""
        clean_domain = domain.strip().lower()

        kwargs = {
            "EmailIdentity": clean_domain,
            "DkimSigningAttributes": {
                "NextSigningKeyLength": "RSA_2048_BIT",
            },
        }
        if configuration_set_name:
            kwargs["ConfigurationSetName"] = configuration_set_name

        try:
            resp = self.client.create_email_identity(**kwargs)
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code == "AlreadyExistsException":
                # Fetch existing identity attributes
                resp = self.client.get_email_identity(EmailIdentity=clean_domain)
            else:
                logger.error("AWS SES create_email_identity failed for %s: %s", clean_domain, e)
                raise RuntimeError("Domain verification is currently unavailable. Please try again later.") from e

        identity_arn = resp.get("IdentityArn") or f"arn:aws:ses:{self.region_name}:identity/{clean_domain}"
        dkim_attrs = resp.get("DkimAttributes", {})
        tokens = dkim_attrs.get("Tokens", [])

        signing_zone = dkim_attrs.get(
            "SigningHostedZone",
            "dkim.amazonses.com",
        ).rstrip(".")

        dkim_records = [
            DkimRecordData(
                record_type="CNAME",
                host=f"{token}._domainkey.{clean_domain}",
                value=f"{token}.{signing_zone}",
            )
            for token in tokens
        ]

        # Configure Custom MAIL FROM domain if specified
        mail_from_records = None
        if mail_from_subdomain:
            sub = mail_from_subdomain.strip().lower()
            mf_domain = f"{sub}.{clean_domain}"
            try:
                self.client.put_email_identity_mail_from_attributes(
                    EmailIdentity=clean_domain,
                    MailFromDomain=mf_domain,
                    BehaviorOnMxFailure="USE_DEFAULT_VALUE",
                )
            except Exception as e:
                logger.warning("Could not set MAIL FROM domain for %s: %s", clean_domain, e)

            mail_from_records = MailFromRecordsData(
                mx_host=mf_domain,
                mx_value=f"feedback-smtp.{self.region_name}.amazonses.com",
                spf_host=mf_domain,
                spf_value="v=spf1 include:amazonses.com ~all",
            )

        return CreateIdentityResult(
            identity_ref=identity_arn,
            dkim_records=dkim_records,
            mail_from_records=mail_from_records,
        )

    def get_identity_status(self, domain: str) -> IdentityStatusResult:
        """Queries AWS SESv2 for current DKIM and identity verification status."""
        clean_domain = domain.strip().lower()
        try:
            resp = self.client.get_email_identity(EmailIdentity=clean_domain)
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code == "NotFoundException":
                return IdentityStatusResult(
                    domain=clean_domain,
                    verification_status="not_started",
                    dkim_status="not_started",
                )
            logger.error("AWS SES get_email_identity failed for %s: %s", clean_domain, e)
            raise RuntimeError("Domain verification is currently unavailable. Please try again later.") from e

        dkim_attrs = resp.get("DkimAttributes", {})
        dkim_status_raw = dkim_attrs.get("Status", "PENDING").lower()  # SUCCESS, PENDING, FAILED, TEMPORARY_FAILURE
        verif_status_raw = resp.get("VerificationStatus", "PENDING").lower()
        mail_from_attrs = resp.get("MailFromAttributes", {})
        mail_from_status_raw = mail_from_attrs.get("MailFromDomainStatus", "PENDING").lower()

        # Map AWS statuses to standard status names
        status_map = {
            "success": "success",
            "pending": "pending",
            "failed": "failed",
            "temporary_failure": "pending",
            "not_started": "not_started",
        }

        return IdentityStatusResult(
            domain=clean_domain,
            verification_status=status_map.get(verif_status_raw, "pending"),
            dkim_status=status_map.get(dkim_status_raw, "pending"),
            mail_from_status=status_map.get(mail_from_status_raw, "pending"),
        )

    def delete_identity(self, domain: str) -> bool:
        """Deletes an identity from AWS SES."""
        clean_domain = domain.strip().lower()
        try:
            self.client.delete_email_identity(EmailIdentity=clean_domain)
            return True
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code == "NotFoundException":
                return True
            logger.error("AWS SES delete_email_identity failed for %s: %s", clean_domain, e)
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
        """Dispatches an email via AWS SESv2."""
        content = {
            "Simple": {
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Text": {"Data": body, "Charset": "UTF-8"},
                },
            }
        }
        if html_body:
            content["Simple"]["Body"]["Html"] = {"Data": html_body, "Charset": "UTF-8"}

        kwargs = {
            "FromEmailAddress": from_email,
            "Destination": {
                "ToAddresses": [to_email],
            },
            "Content": content,
        }
        if configuration_set_name:
            kwargs["ConfigurationSetName"] = configuration_set_name

        try:
            resp = self.client.send_email(**kwargs)
            return resp
        except ClientError as e:
            logger.error("AWS SES send_email failed for %s -> %s: %s", from_email, to_email, e)
            raise RuntimeError(f"Email delivery failed: {e.response.get('Error', {}).get('Message', 'SES send error')}") from e
