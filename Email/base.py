from abc import ABC, abstractmethod


class Mailer(ABC):
    @abstractmethod
    def send_email(self, to_email: str, subject: str, body: str) -> str:
        """Sends a plain-text email. Returns a provider message id."""
        raise NotImplementedError
