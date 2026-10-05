"""Secret store for encrypting and decrypting sensitive email credentials."""

import os
import json
import base64
import hashlib
from dotenv import load_dotenv
from cryptography.fernet import Fernet, MultiFernet

load_dotenv()


_cached_multi_fernet = None


def _get_multi_fernet() -> MultiFernet:
    """Initialize MultiFernet from MAIL_CREDENTIAL_KEY in environment with singleton caching."""
    global _cached_multi_fernet
    if _cached_multi_fernet is not None:
        return _cached_multi_fernet

    keys_str = os.getenv("MAIL_CREDENTIAL_KEY")
    if not keys_str:
        load_dotenv()
        keys_str = os.getenv("MAIL_CREDENTIAL_KEY")

    if not keys_str:
        # Fallback to a deterministic default key for local dev if missing
        seed = os.getenv("SECRET_KEY", "default-saas-mail-credential-secret-key-32b")
        key = base64.urlsafe_b64encode(hashlib.sha256(seed.encode()).digest())
        keys_str = key.decode("utf-8")

    # Support comma-separated keys for rotation
    keys = [k.strip() for k in keys_str.split(",") if k.strip()]
    if not keys:
        seed = os.getenv("SECRET_KEY", "default-saas-mail-credential-secret-key-32b")
        key = base64.urlsafe_b64encode(hashlib.sha256(seed.encode()).digest())
        keys = [key.decode("utf-8")]

    fernets = [Fernet(k) for k in keys]
    _cached_multi_fernet = MultiFernet(fernets)
    return _cached_multi_fernet


def encrypt_secret(data) -> str:
    """Encrypt a dictionary or string of secrets into a token string."""
    if data is None:
        return ""
    f = _get_multi_fernet()
    if isinstance(data, (dict, list)):
        payload_bytes = json.dumps(data).encode("utf-8")
    elif isinstance(data, str):
        payload_bytes = data.encode("utf-8")
    else:
        payload_bytes = str(data).encode("utf-8")
    token = f.encrypt(payload_bytes)
    return token.decode("utf-8")


def decrypt_secret(token: str):
    """Decrypt a token string back into its original payload (dict or str). Safe against invalid tokens."""
    if not token:
        return ""

    try:
        f = _get_multi_fernet()
        token_bytes = token.encode("utf-8")
        decrypted_bytes = f.decrypt(token_bytes)
        decrypted_str = decrypted_bytes.decode("utf-8")
        try:
            return json.loads(decrypted_str)
        except Exception:
            return decrypted_str
    except Exception:
        return ""
