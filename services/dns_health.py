"""Read-only DNS health checks for customer sending domains.

Performs MX, SPF, DKIM, and DMARC lookups.  Generates merged SPF
recommendations.  Estimates DNS lookup count.  NEVER writes DNS.

All resolver calls use timeouts and graceful fallbacks so a single
lookup failure does not crash the entire check.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("dns_health")

# Maximum depth for resolving SPF includes (bounded to prevent runaway)
_SPF_RESOLVE_MAX_DEPTH = 3
_SPF_RESOLVE_TIMEOUT = 4.0  # seconds per query
_SES_SPF_INCLUDE = "amazonses.com"


def _get_resolver():
    """Return a dnspython Resolver with public DNS and timeouts."""
    import dns.resolver

    resolver = dns.resolver.Resolver()
    resolver.nameservers = ["8.8.8.8", "1.1.1.1"]
    resolver.timeout = _SPF_RESOLVE_TIMEOUT
    resolver.lifetime = _SPF_RESOLVE_TIMEOUT * 2
    return resolver


# ─────────────────────────────────────────────────────────────
# Data classes for results
# ─────────────────────────────────────────────────────────────

@dataclass
class MxResult:
    records: List[str] = field(default_factory=list)
    detected_provider: str = "unknown"
    error: Optional[str] = None


@dataclass
class SpfResult:
    raw_records: List[str] = field(default_factory=list)
    valid: bool = True
    includes: List[str] = field(default_factory=list)
    estimated_lookups: Optional[int] = None
    lookup_warning: Optional[str] = None
    merged_recommendation: Optional[str] = None
    has_ses_include: bool = False
    error: Optional[str] = None


@dataclass
class DkimResult:
    """Result of checking a specific DKIM CNAME."""
    host: str = ""
    expected_value: str = ""
    actual_value: Optional[str] = None
    verified: bool = False
    error: Optional[str] = None


@dataclass
class DmarcResult:
    raw_record: Optional[str] = None
    policy: Optional[str] = None       # none | quarantine | reject
    warning: Optional[str] = None
    error: Optional[str] = None


@dataclass
class DnsHealthReport:
    domain: str = ""
    mx: Optional[MxResult] = None
    spf: Optional[SpfResult] = None
    dkim_checks: List[DkimResult] = field(default_factory=list)
    dmarc: Optional[DmarcResult] = None


# ─────────────────────────────────────────────────────────────
# MX lookup + provider detection
# ─────────────────────────────────────────────────────────────

_PROVIDER_PATTERNS = {
    "Microsoft 365": ["outlook.com", "microsoft.com", "office365"],
    "Google Workspace": ["google.com", "googlemail.com", "googleapis.com"],
    "Amazon SES": ["amazonses.com", "amazonaws.com"],
    "Zoho": ["zoho.com", "zoho.eu", "zoho.in"],
    "ProtonMail": ["protonmail.ch", "proton.me"],
    "GoDaddy": ["secureserver.net"],
    "Rackspace": ["emailsrvr.com"],
}


def lookup_mx(domain: str) -> MxResult:
    """Read-only MX lookup for provider detection."""
    try:
        resolver = _get_resolver()
        import dns.resolver

        try:
            answers = resolver.resolve(domain, "MX")
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
            return MxResult(error="No MX records found")
        except dns.resolver.NoNameservers:
            return MxResult(error="DNS servers unreachable")

        records = []
        for rdata in answers:
            exchange = str(rdata.exchange).rstrip(".")
            records.append(f"{rdata.preference} {exchange}")

        # Detect provider
        provider = "unknown"
        all_exchanges = " ".join(records).lower()
        for prov_name, patterns in _PROVIDER_PATTERNS.items():
            if any(p in all_exchanges for p in patterns):
                provider = prov_name
                break

        return MxResult(records=records, detected_provider=provider)

    except ImportError:
        return MxResult(error="dnspython not installed")
    except Exception as exc:
        return MxResult(error=str(exc))


# ─────────────────────────────────────────────────────────────
# SPF lookup, analysis, and merge
# ─────────────────────────────────────────────────────────────

def lookup_spf(domain: str) -> SpfResult:
    """Read and analyse SPF records for a domain."""
    try:
        resolver = _get_resolver()
        import dns.resolver

        try:
            answers = resolver.resolve(domain, "TXT")
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
            return SpfResult(error="No TXT records found")
        except dns.resolver.NoNameservers:
            return SpfResult(error="DNS servers unreachable")

        spf_records = []
        for rdata in answers:
            txt = "".join(s.decode("utf-8", errors="replace") if isinstance(s, bytes) else s for s in rdata.strings)
            if txt.strip().lower().startswith("v=spf1"):
                spf_records.append(txt.strip())

        if not spf_records:
            return SpfResult(
                raw_records=[],
                valid=True,
                merged_recommendation=f'v=spf1 include:{_SES_SPF_INCLUDE} ~all',
                error="No SPF record found — one will need to be created",
            )

        if len(spf_records) > 1:
            return SpfResult(
                raw_records=spf_records,
                valid=False,
                error="Multiple SPF records detected (RFC 7208 violation). "
                      "Merge them into a single record before proceeding.",
            )

        record = spf_records[0]
        includes = re.findall(r'include:(\S+)', record)
        has_ses = _SES_SPF_INCLUDE in [i.lower() for i in includes]

        # Estimate lookup count
        estimated, lookup_warning = _estimate_spf_lookups(domain, record)

        # Generate merged recommendation
        merged = None
        if not has_ses:
            merged = _merge_spf_record(record)

        return SpfResult(
            raw_records=spf_records,
            valid=True,
            includes=includes,
            estimated_lookups=estimated,
            lookup_warning=lookup_warning,
            merged_recommendation=merged,
            has_ses_include=has_ses,
        )

    except ImportError:
        return SpfResult(error="dnspython not installed")
    except Exception as exc:
        return SpfResult(error=str(exc))


def _merge_spf_record(existing: str) -> str:
    """Insert our include before the terminating all mechanism.
    Never creates a second record.
    """
    # Find the terminating mechanism
    all_match = re.search(r'([~+?-]all)\s*$', existing.strip())
    if all_match:
        before_all = existing[:all_match.start()].rstrip()
        all_mechanism = all_match.group(1)
        return f"{before_all} include:{_SES_SPF_INCLUDE} {all_mechanism}"
    else:
        # No all mechanism found — append include at the end
        return f"{existing.rstrip()} include:{_SES_SPF_INCLUDE} ~all"


def _estimate_spf_lookups(
    domain: str,
    record: str,
    depth: int = 0,
) -> Tuple[Optional[int], Optional[str]]:
    """Estimate total DNS lookups from an SPF record by resolving includes.
    Returns (count, warning_message).
    """
    if depth > _SPF_RESOLVE_MAX_DEPTH:
        return None, "Could not determine — resolve depth exceeded"

    count = 0

    # Count mechanisms that cause lookups: include, a, mx, ptr, exists, redirect
    includes = re.findall(r'include:(\S+)', record)
    a_count = len(re.findall(r'\ba[:/\s]', record)) + len(re.findall(r'\ba$', record))
    mx_count = len(re.findall(r'\bmx[:/\s]', record)) + len(re.findall(r'\bmx$', record))
    ptr_count = len(re.findall(r'\bptr[:/\s]', record))
    exists_count = len(re.findall(r'exists:', record))
    redirect_count = len(re.findall(r'redirect=', record))

    count += len(includes) + a_count + mx_count + ptr_count + exists_count + redirect_count

    # Recurse into includes (bounded)
    try:
        resolver = _get_resolver()
        import dns.resolver

        for inc_domain in includes:
            try:
                answers = resolver.resolve(inc_domain, "TXT")
                for rdata in answers:
                    txt = "".join(
                        s.decode("utf-8", errors="replace") if isinstance(s, bytes) else s
                        for s in rdata.strings
                    )
                    if txt.strip().lower().startswith("v=spf1"):
                        sub_count, _ = _estimate_spf_lookups(inc_domain, txt.strip(), depth + 1)
                        if sub_count is not None:
                            count += sub_count
                        else:
                            return None, f"Could not determine — unable to resolve {inc_domain}"
                        break
            except Exception:
                return None, f"Could not determine — unable to resolve {inc_domain}"
    except ImportError:
        return None, "Could not determine — dnspython not installed"

    warning = None
    if count > 10:
        warning = (
            f"Estimated {count} DNS lookups (RFC 7208 limit is 10). "
            "Adding another include may cause SPF validation failures."
        )
    elif count == 10:
        warning = (
            "Estimated 10 DNS lookups (at the RFC 7208 limit). "
            "Adding another include will exceed the limit."
        )

    return count, warning


# ─────────────────────────────────────────────────────────────
# DKIM CNAME verification
# ─────────────────────────────────────────────────────────────

def verify_dkim_cname(host: str, expected_value: str) -> DkimResult:
    """Check if a DKIM CNAME record exists and points to the expected value."""
    try:
        resolver = _get_resolver()
        import dns.resolver

        try:
            answers = resolver.resolve(host, "CNAME")
            for rdata in answers:
                actual = str(rdata.target).rstrip(".")
                if actual.lower() == expected_value.lower().rstrip("."):
                    return DkimResult(
                        host=host,
                        expected_value=expected_value,
                        actual_value=actual,
                        verified=True,
                    )
            # Found CNAME but wrong value
            actual_values = [str(r.target).rstrip(".") for r in answers]
            return DkimResult(
                host=host,
                expected_value=expected_value,
                actual_value=", ".join(actual_values),
                verified=False,
                error=f"CNAME exists but points to {', '.join(actual_values)} instead of {expected_value}",
            )
        except dns.resolver.NXDOMAIN:
            return DkimResult(
                host=host,
                expected_value=expected_value,
                verified=False,
                error="Record not found (NXDOMAIN)",
            )
        except dns.resolver.NoAnswer:
            return DkimResult(
                host=host,
                expected_value=expected_value,
                verified=False,
                error="No CNAME record at this host",
            )
        except dns.resolver.NoNameservers:
            return DkimResult(
                host=host,
                expected_value=expected_value,
                verified=False,
                error="DNS servers unreachable",
            )
    except ImportError:
        return DkimResult(host=host, expected_value=expected_value, error="dnspython not installed")
    except Exception as exc:
        return DkimResult(host=host, expected_value=expected_value, error=str(exc))


# ─────────────────────────────────────────────────────────────
# DMARC lookup
# ─────────────────────────────────────────────────────────────

def lookup_dmarc(domain: str) -> DmarcResult:
    """Read DMARC record for a domain. Warn if policy is reject/quarantine."""
    try:
        resolver = _get_resolver()
        import dns.resolver

        dmarc_domain = f"_dmarc.{domain}"
        try:
            answers = resolver.resolve(dmarc_domain, "TXT")
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
            return DmarcResult(error="No DMARC record found")
        except dns.resolver.NoNameservers:
            return DmarcResult(error="DNS servers unreachable")

        for rdata in answers:
            txt = "".join(
                s.decode("utf-8", errors="replace") if isinstance(s, bytes) else s
                for s in rdata.strings
            )
            if txt.strip().lower().startswith("v=dmarc1"):
                policy_match = re.search(r'p=(\w+)', txt, re.IGNORECASE)
                policy = policy_match.group(1).lower() if policy_match else None

                warning = None
                if policy in ("reject", "quarantine"):
                    warning = (
                        f"DMARC policy is '{policy}'. Emails may be rejected or "
                        "quarantined by recipients until DKIM is verified and aligned. "
                        "Do NOT change your DMARC policy — verify DKIM first."
                    )

                return DmarcResult(
                    raw_record=txt.strip(),
                    policy=policy,
                    warning=warning,
                )

        return DmarcResult(error="No DMARC record found")

    except ImportError:
        return DmarcResult(error="dnspython not installed")
    except Exception as exc:
        return DmarcResult(error=str(exc))


# ─────────────────────────────────────────────────────────────
# Verify MAIL FROM records (MX + SPF on the subdomain)
# ─────────────────────────────────────────────────────────────

def verify_mail_from_mx(subdomain: str, expected_mx: str) -> Dict:
    """Check MX record on the MAIL FROM subdomain."""
    try:
        resolver = _get_resolver()
        import dns.resolver

        try:
            answers = resolver.resolve(subdomain, "MX")
            for rdata in answers:
                exchange = str(rdata.exchange).rstrip(".")
                # expected_mx is like "10 feedback-smtp.us-east-1.amazonses.com"
                expected_exchange = expected_mx.split(" ", 1)[-1] if " " in expected_mx else expected_mx
                if exchange.lower() == expected_exchange.lower():
                    return {"verified": True, "actual": f"{rdata.preference} {exchange}"}
            actuals = [f"{r.preference} {str(r.exchange).rstrip('.')}" for r in answers]
            return {"verified": False, "actual": ", ".join(actuals), "error": "MX exists but points elsewhere"}
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
            return {"verified": False, "error": "No MX record found"}
    except ImportError:
        return {"verified": False, "error": "dnspython not installed"}
    except Exception as exc:
        return {"verified": False, "error": str(exc)}


def verify_mail_from_spf(subdomain: str) -> Dict:
    """Check SPF TXT record on the MAIL FROM subdomain includes amazonses.com."""
    try:
        resolver = _get_resolver()
        import dns.resolver

        try:
            answers = resolver.resolve(subdomain, "TXT")
            for rdata in answers:
                txt = "".join(
                    s.decode("utf-8", errors="replace") if isinstance(s, bytes) else s
                    for s in rdata.strings
                )
                if "v=spf1" in txt.lower() and "amazonses.com" in txt.lower():
                    return {"verified": True, "actual": txt.strip()}
            return {"verified": False, "error": "SPF record found but does not include amazonses.com"}
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
            return {"verified": False, "error": "No TXT record found"}
    except ImportError:
        return {"verified": False, "error": "dnspython not installed"}
    except Exception as exc:
        return {"verified": False, "error": str(exc)}


# ─────────────────────────────────────────────────────────────
# Full health check
# ─────────────────────────────────────────────────────────────

def full_dns_check(
    domain: str,
    dkim_records: Optional[List[Dict]] = None,
) -> DnsHealthReport:
    """Run all DNS checks for a domain. dkim_records is a list of
    dicts with 'host' and 'value' keys (from the provider response).
    """
    report = DnsHealthReport(domain=domain)

    report.mx = lookup_mx(domain)
    report.spf = lookup_spf(domain)
    report.dmarc = lookup_dmarc(domain)

    if dkim_records:
        for rec in dkim_records:
            result = verify_dkim_cname(rec["host"], rec["value"])
            report.dkim_checks.append(result)

    return report
