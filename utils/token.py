import secrets


def generate_token(identifier: str = None) -> str:
    return secrets.token_urlsafe(16)
