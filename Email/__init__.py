from .base import Mailer
from .outlook_mailer import OutlookMailer


def get_mailer() -> OutlookMailer:
    """Returns the Outlook (Microsoft Graph) mailer instance."""
    return OutlookMailer()


__all__ = ["Mailer", "get_mailer", "OutlookMailer"]
