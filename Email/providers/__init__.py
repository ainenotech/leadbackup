"""SES Sending Providers module."""

from .base import (
    CreateIdentityResult,
    DkimRecordData,
    IdentityStatusResult,
    MailFromRecordsData,
)
from .mock_provider import MockSESProvider
from .ses_provider import SESProvider, has_aws_credentials

def get_ses_provider():
    from services.domain_auth_service import _get_provider
    return _get_provider()


__all__ = [
    "CreateIdentityResult",
    "DkimRecordData",
    "IdentityStatusResult",
    "MailFromRecordsData",
    "MockSESProvider",
    "SESProvider",
    "has_aws_credentials",
    "get_ses_provider",
]

