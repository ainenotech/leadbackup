"""Email channels registry."""

from .base import SendChannel


class NotImplementedChannel(SendChannel):
    def __init__(self, channel_name: str):
        self.channel_name = channel_name
        
    def send_email(self, to_email: str, subject: str, body: str, token=None) -> bool:
        raise NotImplementedError(f"Channel {self.channel_name} is not yet available.")
        
    def check_health(self) -> bool:
        return False
        
    def describe_requirements(self) -> dict:
        return {"description": f"{self.channel_name} not yet implemented."}


class CustomerDomainAdapter(SendChannel):
    def __init__(self, ses_mailer):
        self.mailer = ses_mailer
        
    def send_email(self, to_email: str, subject: str, body: str, token=None) -> bool:
        return self.mailer.send_email(to_email=to_email, subject=subject, body=body, token=token)
        
    def check_health(self) -> bool:
        return True
        
    def describe_requirements(self) -> dict:
        return {"description": "Customer custom domain via Amazon SES."}


def get_channel_handler(channel_name: str, config: dict = None) -> SendChannel:
    """Returns a handler for the given channel name."""
    if channel_name == "microsoft_oauth":
        from .microsoft_oauth import MicrosoftOAuthChannel
        return MicrosoftOAuthChannel()
    elif channel_name == "google_oauth":
        from .google_oauth_channel import GoogleOAuthChannel
        return GoogleOAuthChannel()
    elif channel_name == "customer_domain":
        from services.domain_auth_service import _get_provider
        return CustomerDomainAdapter(ses_mailer=_get_provider())
    elif channel_name in ("smtp_imap", "own_domain"):
        return NotImplementedChannel(channel_name)
    raise ValueError(f"Unknown channel: {channel_name}")
