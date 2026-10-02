"""Provider-agnostic interface for email sending domain management.

Every concrete provider (SES, SendGrid, Postmark, etc.) implements this
interface so the domain-auth service and mailer are decoupled from any
single vendor.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class DkimRecord:
    """A DKIM DNS record the customer must publish."""
    record_type: str       # "CNAME" for SES Easy DKIM
    host: str              # e.g. "{token}._domainkey.customer.com"
    value: str             # e.g. "{token}.dkim.amazonses.com"


@dataclass
class MailFromRecord:
    """DNS records for custom MAIL FROM subdomain."""
    mx_host: str           # e.g. "mail.customer.com"
    mx_value: str          # e.g. "10 feedback-smtp.us-east-1.amazonses.com"
    spf_host: str          # e.g. "mail.customer.com"
    spf_value: str         # e.g. '"v=spf1 include:amazonses.com ~all"'


@dataclass
class IdentityResult:
    """Result of creating or querying a provider identity."""
    identity_ref: str                        # provider's reference for this identity
    dkim_records: List[DkimRecord] = field(default_factory=list)
    mail_from_records: Optional[MailFromRecord] = None
    dkim_status: str = "pending"             # pending | success | failed
    verification_status: str = "pending"     # pending | success | failed
    verified_for_sending: bool = False
    mail_from_status: str = "pending"        # pending | success | failed
    configuration_set: Optional[str] = None
    raw_response: Optional[Dict] = None      # full provider response (never logged)


class SendingProvider(ABC):
    """Abstract interface for an email sending provider."""

    @abstractmethod
    def create_identity(
        self,
        domain: str,
        configuration_set_name: Optional[str] = None,
        mail_from_subdomain: Optional[str] = None,
    ) -> IdentityResult:
        """Register a domain identity with the provider.

        Returns DKIM records the customer must publish and (optionally)
        MAIL FROM records.
        """
        ...

    @abstractmethod
    def get_identity_status(self, domain: str) -> IdentityResult:
        """Query current verification status of a domain identity."""
        ...

    @abstractmethod
    def delete_identity(self, domain: str) -> bool:
        """Remove a domain identity from the provider. Returns True on success."""
        ...

    @abstractmethod
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
        """Send an email through the provider. Returns a provider message ID."""
        ...

    @abstractmethod
    def create_configuration_set(self, name: str) -> bool:
        """Create an isolated configuration set (for per-org reputation).
        Returns True on success, False if it already exists.
        """
        ...

    @abstractmethod
    def delete_configuration_set(self, name: str) -> bool:
        """Delete a configuration set. Returns True on success."""
        ...
