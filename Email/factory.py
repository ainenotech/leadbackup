
from Email.config import EMAIL_PROVIDER


def get_mailer():
    """Return the configured email provider."""
    if EMAIL_PROVIDER == "outlook":
        from Email.outlook_mailer import OutlookMailer
        return OutlookMailer()

    if EMAIL_PROVIDER == "ses":
        from Email.ses import SESMailer
        return SESMailer()

    raise ValueError(
        f"Unsupported EMAIL_PROVIDER: {EMAIL_PROVIDER!r}. "
        "Use 'outlook' or 'ses'."
    )
