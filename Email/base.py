from abc import ABC, abstractmethod
from typing import Optional


class Mailer(ABC):
    @abstractmethod
    def send_email(
        self, to_email: str, subject: str, body: str, token: Optional[str] = None
    ) -> str:
        """Sends an email. Returns a provider message id."""
        raise NotImplementedError

