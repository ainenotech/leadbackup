"""DNS patch to ensure bulletproof domain resolution even if the host machine
has an unresponsive local or corporate DNS server (e.g. 10.x.x.x).
Falls back instantly to Google (8.8.8.8) and Cloudflare (1.1.1.1) public DNS.
"""

import socket
import logging
from typing import Dict, Any

logger = logging.getLogger("dns_patch")

_orig_getaddrinfo = socket.getaddrinfo
_dns_cache: Dict[str, str] = {}
_PUBLIC_DNS = ["8.8.8.8", "1.1.1.1"]

try:
    import dns.resolver
    _has_dnspython = True
    _resolver = dns.resolver.Resolver()
    _resolver.nameservers = _PUBLIC_DNS
    _resolver.timeout = 2.0
    _resolver.lifetime = 2.0
except ImportError:
    _has_dnspython = False
    _resolver = None


def _resolve_with_public_dns(host: str) -> str:
    if not _has_dnspython or not _resolver:
        return ""
    try:
        answers = _resolver.resolve(host, "A")
        if answers:
            return answers[0].to_text()
    except Exception:
        pass
    return ""


def patched_getaddrinfo(host: Any, port: Any, family: int = 0, type: int = 0, proto: int = 0, flags: int = 0) -> Any:
    if not host or not isinstance(host, str):
        return _orig_getaddrinfo(host, port, family, type, proto, flags)

    # Fast path for localhost, loopback, and raw IP addresses
    if host in ("localhost", "127.0.0.1", "::1", "0.0.0.0") or host.replace(".", "").isdigit():
        return _orig_getaddrinfo(host, port, family, type, proto, flags)

    # Check cache
    if host in _dns_cache:
        return _orig_getaddrinfo(_dns_cache[host], port, family, type, proto, flags)

    # Proactively resolve Microsoft Graph and login domains to avoid Windows DNS timeout
    if any(k in host.lower() for k in ("microsoft", "office", "graph", "windows.net", "azure")):
        ip = _resolve_with_public_dns(host)
        if ip:
            _dns_cache[host] = ip
            return _orig_getaddrinfo(ip, port, family, type, proto, flags)

    # Try standard system resolution
    try:
        return _orig_getaddrinfo(host, port, family, type, proto, flags)
    except (socket.gaierror, socket.herror, TimeoutError):
        # Fallback to public DNS on failure
        ip = _resolve_with_public_dns(host)
        if ip:
            _dns_cache[host] = ip
            return _orig_getaddrinfo(ip, port, family, type, proto, flags)
        raise


def apply_dns_patch() -> None:
    """Installs the DNS patch if not already applied."""
    if socket.getaddrinfo != patched_getaddrinfo:
        socket.getaddrinfo = patched_getaddrinfo


# Automatically apply on import
apply_dns_patch()
