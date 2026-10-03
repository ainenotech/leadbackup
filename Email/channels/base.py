"""Base interface for all email sending channels."""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any


class SendChannel(ABC):
    """Abstract interface for all outbound email channels."""
    
    @abstractmethod
    def send_email(self, to_email: str, subject: str, body: str, token: Optional[str] = None) -> bool:
        """Send an email using this channel."""
        pass
        
    def poll_replies(self) -> List[Dict[str, Any]]:
        """Poll the channel for new replies.
        
        Returns a list of reply dictionaries in the format expected by the reply processing pipeline.
        Returns empty list if the channel does not support or need polling.
        """
        return []
        
    @abstractmethod
    def check_health(self) -> bool:
        """Check if the connection/channel is healthy."""
        pass
        
    @abstractmethod
    def describe_requirements(self) -> Dict[str, Any]:
        """Describe the configuration requirements for this channel type."""
        pass
