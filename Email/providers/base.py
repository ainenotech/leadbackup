"""Base data structures and interface for SES sending providers."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DkimRecordData:
    record_type: str
    host: str
    value: str


@dataclass
class MailFromRecordsData:
    mx_host: str
    mx_value: str
    spf_host: str
    spf_value: str


@dataclass
class CreateIdentityResult:
    identity_ref: str
    dkim_records: List[DkimRecordData] = field(default_factory=list)
    mail_from_records: Optional[MailFromRecordsData] = None


@dataclass
class IdentityStatusResult:
    domain: str
    verification_status: str  # "success" | "pending" | "failed" | "not_started"
    dkim_status: str          # "success" | "pending" | "failed" | "not_started"
    mail_from_status: str = "pending"
    signing_attributes_origin: str = "AWS_SES"
