"""Domain authentication service — orchestrates provider registration,
DNS verification, claim management, and status transitions.

Every public function requires organization_id from the VERIFIED token
and re-checks active membership and owner/admin role in the database.
"""

import logging
import os
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from Backend.auth_models import Organization, OrganizationMember, User
from Backend.domain_models import (
    OrgDomainCheckHistory,
    OrgDomainRecord,
    OrgDomainStats,
    OrgSendingDomain,
)

logger = logging.getLogger("domain_auth_service")

_PENDING_EXPIRY_DAYS = int(os.getenv("PENDING_DOMAIN_EXPIRY_DAYS", "14"))
_DEFAULT_DAILY_CAP = int(os.getenv("SENDING_DEFAULT_DAILY_CAP", "200"))
_BOUNCE_THRESHOLD = float(os.getenv("SES_BOUNCE_RATE_THRESHOLD", "5.0"))
_COMPLAINT_THRESHOLD = float(os.getenv("SES_COMPLAINT_RATE_THRESHOLD", "0.1"))


# ─────────────────────────────────────────────────────────────
# Auth helpers
# ─────────────────────────────────────────────────────────────

def _verify_org_admin(db: Session, user_id: str, organization_id: str) -> Organization:
    """Re-check caller's active membership and owner/admin role.
    Returns the Organization or raises ValueError.
    """
    org = db.query(Organization).filter(
        Organization.id == organization_id,
        Organization.status == "active",
    ).first()
    if not org:
        raise ValueError("Organization not found or inactive")

    # Platform super admins can manage sending domains for any org
    user = db.query(User).filter(User.id == user_id).first()
    if user and user.platform_role == "platform_super_admin":
        return org

    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == user_id,
        OrganizationMember.status == "active",
    ).first()
    if not member or member.role not in ("organization_owner", "organization_admin"):
        raise PermissionError("Only organization owners or admins can manage sending domains")

    return org


def _extract_domain(email_or_domain: str) -> str:
    """Extract and validate domain from an email address or bare domain."""
    value = email_or_domain.strip().lower()
    if "@" in value:
        parts = value.split("@")
        if len(parts) != 2 or not parts[1]:
            raise ValueError("Invalid email address")
        value = parts[1]

    # Basic domain validation
    if not re.match(r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$', value):
        raise ValueError(f"Invalid domain: {value}")

    return value


def is_mock_provider() -> bool:
    """Return True if running with simulated/mock SES provider."""
    from Email.providers.ses_provider import has_aws_credentials
    return os.getenv("MOCK_SES", "").lower() in ("true", "1") or not has_aws_credentials()


def _get_provider():
    """Return the configured SendingProvider instance."""
    if is_mock_provider():
        from Email.providers.mock_provider import MockSESProvider
        return MockSESProvider()
    from Email.providers.ses_provider import SESProvider
    return SESProvider()


def _config_set_name(org_id: str) -> str:
    """Generate a configuration set name for an organization."""
    short = org_id[:8] if len(org_id) >= 8 else org_id
    return f"org-{short}"


# ─────────────────────────────────────────────────────────────
# Domain registration
# ─────────────────────────────────────────────────────────────

def register_domain(
    db: Session,
    user_id: str,
    organization_id: str,
    email_address: str,
    from_name: Optional[str] = None,
    reply_to: Optional[str] = None,
) -> Dict[str, Any]:
    """Register a new sending domain extracted from the customer's email.

    1. Validate email, extract domain
    2. Check for existing claims
    3. Register with provider (SES)
    4. Store domain + DKIM records
    5. Run initial DNS check
    """
    org = _verify_org_admin(db, user_id, organization_id)
    domain = _extract_domain(email_address)
    local_part = email_address.split("@")[0] if "@" in email_address else "outreach"
    eff_reply_to = reply_to or (email_address.strip() if "@" in email_address else f"outreach@{domain}")

    # Check for existing claim
    existing = db.query(OrgSendingDomain).filter(
        OrgSendingDomain.domain == domain,
    ).first()

    if existing:
        if existing.organization_id == organization_id:
            raise ValueError(f"Domain {domain} is already registered for your organization")

        # Check if it's an expired pending claim
        if existing.status == "pending" and existing.claim_expires_at:
            claim_exp = existing.claim_expires_at
            if claim_exp.tzinfo is None:
                claim_exp = claim_exp.replace(tzinfo=timezone.utc)
            if claim_exp < datetime.now(timezone.utc):
                # Expired — clean up and allow re-claim
                _cleanup_expired_claim(db, existing)
            else:
                raise ValueError(
                    f"Domain {domain} is currently claimed by another organization. "
                    "The claim will expire if not verified."
                )
        elif existing.status in ("ready", "limited", "blocked"):
            raise ValueError(
                f"Domain {domain} is already verified by another organization"
            )
        else:
            raise ValueError(f"Domain {domain} is currently claimed by another organization")

    # Create configuration set for org (idempotent)
    provider = _get_provider()
    cs_name = _config_set_name(organization_id)
    try:
        provider.create_configuration_set(cs_name)
    except Exception as exc:
        logger.warning("Config set creation for org %s: %s", organization_id, exc)

    # Register domain with provider
    result = provider.create_identity(
        domain=domain,
        configuration_set_name=cs_name,
        mail_from_subdomain="mail",
    )

    # Create domain record
    sending_domain = OrgSendingDomain(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        domain=domain,
        provider="ses",
        provider_identity_ref=result.identity_ref,
        status="pending",
        from_local_part=local_part,
        from_name=from_name or org.brand_name or org.name,
        reply_to=eff_reply_to,
        mail_from_subdomain="mail",
        daily_cap=_DEFAULT_DAILY_CAP,
        claim_expires_at=datetime.now(timezone.utc) + timedelta(days=_PENDING_EXPIRY_DAYS),
    )
    db.add(sending_domain)
    db.flush()

    try:
        from services.master_db_service import log_audit
        log_audit(db, action="email_domain.created", entity_type="email_domain", entity_id=sending_domain.id, user=user_id)
        log_audit(db, action="email_domain.verification_started", entity_type="email_domain", entity_id=sending_domain.id, user=user_id)
    except Exception:
        pass

    # Store DKIM records
    for dkim in result.dkim_records:
        db.add(OrgDomainRecord(
            id=str(uuid.uuid4()),
            domain_id=sending_domain.id,
            record_type=dkim.record_type,
            host=dkim.host,
            value=dkim.value,
            purpose="dkim",
            required=True,
            status="pending",
        ))

    # Store MAIL FROM records
    if result.mail_from_records:
        mf = result.mail_from_records
        db.add(OrgDomainRecord(
            id=str(uuid.uuid4()),
            domain_id=sending_domain.id,
            record_type="MX",
            host=mf.mx_host,
            value=mf.mx_value,
            purpose="mail_from_mx",
            required=True,
            status="pending",
        ))
        db.add(OrgDomainRecord(
            id=str(uuid.uuid4()),
            domain_id=sending_domain.id,
            record_type="TXT",
            host=mf.spf_host,
            value=mf.spf_value,
            purpose="mail_from_spf",
            required=True,
            status="pending",
        ))

    db.commit()
    db.refresh(sending_domain)

    # Run initial DNS check
    dns_report = _run_dns_check(db, sending_domain, triggered_by="system")

    return _serialize_domain(db, sending_domain, dns_report)


def _cleanup_expired_claim(db: Session, domain_record: OrgSendingDomain):
    """Remove an expired pending claim and its provider identity."""
    try:
        provider = _get_provider()
        provider.delete_identity(domain_record.domain)
    except Exception as exc:
        logger.warning("Could not delete expired identity %s: %s", domain_record.domain, exc)

    # Delete associated records
    db.query(OrgDomainRecord).filter(OrgDomainRecord.domain_id == domain_record.id).delete()
    db.query(OrgDomainCheckHistory).filter(OrgDomainCheckHistory.domain_id == domain_record.id).delete()
    db.query(OrgDomainStats).filter(OrgDomainStats.domain_id == domain_record.id).delete()
    db.delete(domain_record)
    db.commit()


# ─────────────────────────────────────────────────────────────
# Verification
# ─────────────────────────────────────────────────────────────

def verify_domain(
    db: Session,
    user_id: str,
    organization_id: str,
    domain_id: str,
) -> Dict[str, Any]:
    """Re-run DNS lookups AND fetch provider verification status."""
    _verify_org_admin(db, user_id, organization_id)

    domain_rec = db.query(OrgSendingDomain).filter(
        OrgSendingDomain.id == domain_id,
        OrgSendingDomain.organization_id == organization_id,
    ).first()
    if not domain_rec:
        raise ValueError("Domain not found for this organization")

    dns_report = _run_dns_check(db, domain_rec, triggered_by="user")
    return _serialize_domain(db, domain_rec, dns_report)


def _run_dns_check(
    db: Session,
    domain_rec: OrgSendingDomain,
    triggered_by: str = "system",
) -> Dict:
    """Execute DNS lookups and provider status check. Update records and domain status."""
    from services.dns_health import (
        full_dns_check,
        verify_mail_from_mx,
        verify_mail_from_spf,
    )

    # Get stored records for DKIM check
    records = db.query(OrgDomainRecord).filter(
        OrgDomainRecord.domain_id == domain_rec.id,
    ).all()

    dkim_records = [
        {"host": r.host, "value": r.value}
        for r in records if r.purpose == "dkim"
    ]

    # Run DNS checks
    report = full_dns_check(domain_rec.domain, dkim_records)

    # Update DKIM record statuses
    now = datetime.now(timezone.utc)
    all_dkim_verified = True
    for rec in records:
        if rec.purpose == "dkim":
            matching = next(
                (d for d in report.dkim_checks if d.host == rec.host),
                None,
            )
            if matching:
                rec.status = "verified" if matching.verified else "pending"
                rec.last_result = matching.error or "Verified"
                rec.last_checked_at = now
                if not matching.verified:
                    all_dkim_verified = False
            else:
                all_dkim_verified = False

        elif rec.purpose == "mail_from_mx":
            mx_result = verify_mail_from_mx(rec.host, rec.value)
            rec.status = "verified" if mx_result.get("verified") else "pending"
            rec.last_result = mx_result.get("error", "Verified")
            rec.last_checked_at = now

        elif rec.purpose == "mail_from_spf":
            spf_result = verify_mail_from_spf(rec.host)
            rec.status = "verified" if spf_result.get("verified") else "pending"
            rec.last_result = spf_result.get("error", "Verified")
            rec.last_checked_at = now

    # Get provider verification status
    provider_result = None
    try:
        provider = _get_provider()
        provider_result = provider.get_identity_status(domain_rec.domain)
    except Exception as exc:
        logger.warning("Could not fetch provider status for %s: %s", domain_rec.domain, exc)

    # Determine domain-level status
    provider_dkim_verified = False
    if provider_result:
        provider_dkim_verified = provider_result.dkim_status in ("success",)

    # Domain verified when provider DKIM verified OR local DNS lookup verified
    if provider_dkim_verified or all_dkim_verified:
        if domain_rec.status in ("pending", "blocked"):
            domain_rec.status = "ready"
            domain_rec.verified_at = now
            domain_rec.claim_expires_at = None  # No longer expires
            try:
                from services.master_db_service import log_audit
                log_audit(db, action="email_domain.verification_succeeded", entity_type="email_domain", entity_id=domain_rec.id, user=triggered_by)
                log_audit(db, action="email_domain.sending_enabled", entity_type="email_domain", entity_id=domain_rec.id, user=triggered_by)
            except Exception:
                pass
    elif domain_rec.status == "pending":
        domain_rec.status = "pending"
        try:
            from services.master_db_service import log_audit
            log_audit(db, action="email_domain.verification_failed", entity_type="email_domain", entity_id=domain_rec.id, user=triggered_by)
        except Exception:
            pass

    domain_rec.last_checked_at = now

    # Save check history
    results_snapshot = {
        "dkim_checks": [
            {"host": d.host, "verified": d.verified, "error": d.error}
            for d in report.dkim_checks
        ],
        "spf": {
            "valid": report.spf.valid if report.spf else None,
            "has_ses_include": report.spf.has_ses_include if report.spf else None,
            "error": report.spf.error if report.spf else None,
        },
        "dmarc": {
            "policy": report.dmarc.policy if report.dmarc else None,
            "warning": report.dmarc.warning if report.dmarc else None,
        },
        "mx": {
            "provider": report.mx.detected_provider if report.mx else None,
        },
        "provider_dkim_status": provider_result.dkim_status if provider_result else None,
        "provider_verification": provider_result.verification_status if provider_result else None,
    }

    db.add(OrgDomainCheckHistory(
        id=str(uuid.uuid4()),
        domain_id=domain_rec.id,
        checked_at=now,
        results=results_snapshot,
        triggered_by=triggered_by,
    ))

    db.commit()
    return results_snapshot


# ─────────────────────────────────────────────────────────────
# CRUD operations
# ─────────────────────────────────────────────────────────────

def list_domains(
    db: Session,
    user_id: str,
    organization_id: str,
) -> List[Dict[str, Any]]:
    """List all sending domains for the org."""
    _verify_org_admin(db, user_id, organization_id)

    domains = db.query(OrgSendingDomain).filter(
        OrgSendingDomain.organization_id == organization_id,
    ).order_by(OrgSendingDomain.created_at.desc()).all()

    result = []
    for d in domains:
        records = db.query(OrgDomainRecord).filter(
            OrgDomainRecord.domain_id == d.id,
        ).all()
        result.append(_serialize_domain_brief(d, records))

    return result


def get_domain_detail(
    db: Session,
    user_id: str,
    organization_id: str,
    domain_id: str,
) -> Dict[str, Any]:
    """Get detailed domain info with records."""
    _verify_org_admin(db, user_id, organization_id)

    domain_rec = db.query(OrgSendingDomain).filter(
        OrgSendingDomain.id == domain_id,
        OrgSendingDomain.organization_id == organization_id,
    ).first()
    if not domain_rec:
        raise ValueError("Domain not found for this organization")

    return _serialize_domain(db, domain_rec)


def update_domain(
    db: Session,
    user_id: str,
    organization_id: str,
    domain_id: str,
    from_name: Optional[str] = None,
    reply_to: Optional[str] = None,
    daily_cap: Optional[int] = None,
) -> Dict[str, Any]:
    """Update editable fields of a sending domain."""
    _verify_org_admin(db, user_id, organization_id)

    domain_rec = db.query(OrgSendingDomain).filter(
        OrgSendingDomain.id == domain_id,
        OrgSendingDomain.organization_id == organization_id,
    ).first()
    if not domain_rec:
        raise ValueError("Domain not found for this organization")

    if from_name is not None:
        domain_rec.from_name = from_name
    if reply_to is not None:
        domain_rec.reply_to = reply_to
    if daily_cap is not None:
        domain_rec.daily_cap = max(0, daily_cap)

    db.commit()
    db.refresh(domain_rec)
    return _serialize_domain(db, domain_rec)


def pause_domain(
    db: Session,
    user_id: str,
    organization_id: str,
    domain_id: str,
    reason: str = "Manually paused by admin",
) -> Dict[str, Any]:
    """Pause a sending domain."""
    _verify_org_admin(db, user_id, organization_id)

    domain_rec = db.query(OrgSendingDomain).filter(
        OrgSendingDomain.id == domain_id,
        OrgSendingDomain.organization_id == organization_id,
    ).first()
    if not domain_rec:
        raise ValueError("Domain not found for this organization")

    domain_rec.status = "paused"
    domain_rec.paused_reason = reason
    db.commit()
    db.refresh(domain_rec)

    try:
        from services.master_db_service import log_audit
        log_audit(db, action="email_domain.sending_disabled", entity_type="email_domain", entity_id=domain_id, user=user_id)
    except Exception:
        pass

    return _serialize_domain(db, domain_rec)


def resume_domain(
    db: Session,
    user_id: str,
    organization_id: str,
    domain_id: str,
) -> Dict[str, Any]:
    """Resume a paused sending domain."""
    _verify_org_admin(db, user_id, organization_id)

    domain_rec = db.query(OrgSendingDomain).filter(
        OrgSendingDomain.id == domain_id,
        OrgSendingDomain.organization_id == organization_id,
    ).first()
    if not domain_rec:
        raise ValueError("Domain not found for this organization")

    if domain_rec.status != "paused":
        raise ValueError("Domain is not paused")

    domain_rec.status = "ready" if domain_rec.verified_at else "pending"
    domain_rec.paused_reason = None
    db.commit()
    db.refresh(domain_rec)

    try:
        from services.master_db_service import log_audit
        log_audit(db, action="email_domain.sending_enabled", entity_type="email_domain", entity_id=domain_id, user=user_id)
    except Exception:
        pass

    return _serialize_domain(db, domain_rec)


def delete_domain(
    db: Session,
    user_id: str,
    organization_id: str,
    domain_id: str,
) -> bool:
    """Delete a sending domain claim and its provider identity."""
    _verify_org_admin(db, user_id, organization_id)

    domain_rec = db.query(OrgSendingDomain).filter(
        OrgSendingDomain.id == domain_id,
        OrgSendingDomain.organization_id == organization_id,
    ).first()
    if not domain_rec:
        raise ValueError("Domain not found for this organization")

    # Delete from provider
    try:
        provider = _get_provider()
        provider.delete_identity(domain_rec.domain)
    except Exception as exc:
        logger.warning("Could not delete provider identity %s: %s", domain_rec.domain, exc)

    # Delete associated records
    db.query(OrgDomainRecord).filter(OrgDomainRecord.domain_id == domain_id).delete()
    db.query(OrgDomainCheckHistory).filter(OrgDomainCheckHistory.domain_id == domain_id).delete()
    db.query(OrgDomainStats).filter(OrgDomainStats.domain_id == domain_id).delete()
    db.delete(domain_rec)
    db.commit()

    try:
        from services.master_db_service import log_audit
        log_audit(db, action="email_domain.deleted", entity_type="email_domain", entity_id=domain_id, user=user_id)
    except Exception:
        pass

    return True


def get_check_history(
    db: Session,
    user_id: str,
    organization_id: str,
    domain_id: str,
) -> List[Dict]:
    """Get verification check history for a domain."""
    _verify_org_admin(db, user_id, organization_id)

    domain_rec = db.query(OrgSendingDomain).filter(
        OrgSendingDomain.id == domain_id,
        OrgSendingDomain.organization_id == organization_id,
    ).first()
    if not domain_rec:
        raise ValueError("Domain not found for this organization")

    history = db.query(OrgDomainCheckHistory).filter(
        OrgDomainCheckHistory.domain_id == domain_id,
    ).order_by(OrgDomainCheckHistory.checked_at.desc()).limit(50).all()

    return [
        {
            "id": h.id,
            "checked_at": h.checked_at.isoformat() if h.checked_at else None,
            "results": h.results,
            "triggered_by": h.triggered_by,
        }
        for h in history
    ]


def get_dns_instructions(
    db: Session,
    user_id: str,
    organization_id: str,
    domain_id: str,
) -> str:
    """Generate plain-language DNS instructions for IT admin."""
    _verify_org_admin(db, user_id, organization_id)

    domain_rec = db.query(OrgSendingDomain).filter(
        OrgSendingDomain.id == domain_id,
        OrgSendingDomain.organization_id == organization_id,
    ).first()
    if not domain_rec:
        raise ValueError("Domain not found for this organization")

    records = db.query(OrgDomainRecord).filter(
        OrgDomainRecord.domain_id == domain_id,
    ).all()

    lines = [
        f"DNS Records for {domain_rec.domain}",
        f"{'=' * 50}",
        "",
        "Please add the following DNS records to verify your sending domain.",
        "These records are required for email authentication (DKIM and SPF).",
        "",
    ]

    purpose_labels = {
        "dkim": "DKIM Authentication",
        "mail_from_mx": "Custom MAIL FROM (MX)",
        "mail_from_spf": "Custom MAIL FROM (SPF)",
    }

    for i, rec in enumerate(records, 1):
        lines.append(f"Record {i}: {purpose_labels.get(rec.purpose, rec.purpose)}")
        lines.append(f"  Type:    {rec.record_type}")
        lines.append(f"  Host:    {rec.host}")
        lines.append(f"  Value:   {rec.value}")
        lines.append(f"  Status:  {rec.status}")
        lines.append("")

    lines.extend([
        "Notes:",
        "- DKIM records may take up to 72 hours to propagate.",
        "- The MAIL FROM records are on a subdomain and do NOT affect",
        "  your existing email or domain configuration.",
        "- Do NOT modify your main domain's MX records.",
        "- After adding these records, click 'Verify' in the platform.",
    ])

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# Send-time enforcement
# ─────────────────────────────────────────────────────────────

class CapExceededError(Exception):
    """Raised when daily sending cap is exceeded."""
    pass


class DomainNotReadyError(Exception):
    """Raised when domain is not in a sendable state."""
    pass


def check_send_eligibility(
    db: Session,
    organization_id: str,
    from_domain: str,
) -> OrgSendingDomain:
    """Verify domain is eligible for sending. Returns the domain record
    or raises an appropriate error.
    """
    domain_rec = db.query(OrgSendingDomain).filter(
        OrgSendingDomain.organization_id == organization_id,
        OrgSendingDomain.domain == from_domain,
    ).first()

    if not domain_rec:
        raise DomainNotReadyError(f"No sending domain {from_domain} registered for this organization")

    if domain_rec.status == "paused":
        raise DomainNotReadyError(
            f"Sending domain {from_domain} is paused: {domain_rec.paused_reason or 'No reason given'}"
        )

    if domain_rec.status not in ("ready", "limited"):
        raise DomainNotReadyError(
            f"Sending domain {from_domain} is not verified (status: {domain_rec.status})"
        )

    # Check daily cap
    today = date.today()
    stats = db.query(OrgDomainStats).filter(
        OrgDomainStats.domain_id == domain_rec.id,
        OrgDomainStats.date == today,
    ).first()

    if stats and domain_rec.daily_cap > 0 and stats.sent >= domain_rec.daily_cap:
        raise CapExceededError(
            f"Daily sending cap ({domain_rec.daily_cap}) reached for {from_domain}. "
            f"Sent today: {stats.sent}"
        )

    return domain_rec


def record_send(db: Session, domain_id: str):
    """Increment the daily send counter for a domain."""
    today = date.today()
    stats = db.query(OrgDomainStats).filter(
        OrgDomainStats.domain_id == domain_id,
        OrgDomainStats.date == today,
    ).first()

    if stats:
        stats.sent = (stats.sent or 0) + 1
    else:
        stats = OrgDomainStats(
            id=str(uuid.uuid4()),
            domain_id=domain_id,
            date=today,
            sent=1,
        )
        db.add(stats)

    db.commit()


def record_bounce(db: Session, domain: str):
    """Increment bounce counter and check auto-pause threshold."""
    domain_rec = db.query(OrgSendingDomain).filter(
        OrgSendingDomain.domain == domain,
    ).first()
    if not domain_rec:
        return

    today = date.today()
    stats = db.query(OrgDomainStats).filter(
        OrgDomainStats.domain_id == domain_rec.id,
        OrgDomainStats.date == today,
    ).first()

    if stats:
        stats.bounced = (stats.bounced or 0) + 1
    else:
        stats = OrgDomainStats(
            id=str(uuid.uuid4()),
            domain_id=domain_rec.id,
            date=today,
            bounced=1,
        )
        db.add(stats)

    db.commit()

    # Check auto-pause threshold
    if stats and stats.sent and stats.sent > 0:
        bounce_rate = (stats.bounced / stats.sent) * 100
        if bounce_rate >= _BOUNCE_THRESHOLD:
            domain_rec.status = "paused"
            domain_rec.paused_reason = (
                f"Auto-paused: bounce rate {bounce_rate:.1f}% "
                f"exceeds threshold {_BOUNCE_THRESHOLD}%"
            )
            db.commit()
            logger.warning("Auto-paused domain %s: bounce rate %.1f%%", domain, bounce_rate)


def record_complaint(db: Session, domain: str):
    """Increment complaint counter and check auto-pause threshold."""
    domain_rec = db.query(OrgSendingDomain).filter(
        OrgSendingDomain.domain == domain,
    ).first()
    if not domain_rec:
        return

    today = date.today()
    stats = db.query(OrgDomainStats).filter(
        OrgDomainStats.domain_id == domain_rec.id,
        OrgDomainStats.date == today,
    ).first()

    if stats:
        stats.complained = (stats.complained or 0) + 1
    else:
        stats = OrgDomainStats(
            id=str(uuid.uuid4()),
            domain_id=domain_rec.id,
            date=today,
            complained=1,
        )
        db.add(stats)

    db.commit()

    # Check auto-pause threshold
    if stats and stats.sent and stats.sent > 0:
        complaint_rate = (stats.complained / stats.sent) * 100
        if complaint_rate >= _COMPLAINT_THRESHOLD:
            domain_rec.status = "paused"
            domain_rec.paused_reason = (
                f"Auto-paused: complaint rate {complaint_rate:.2f}% "
                f"exceeds threshold {_COMPLAINT_THRESHOLD}%"
            )
            db.commit()
            logger.warning("Auto-paused domain %s: complaint rate %.2f%%", domain, complaint_rate)


# ─────────────────────────────────────────────────────────────
# Serialization helpers
# ─────────────────────────────────────────────────────────────

def _serialize_domain(
    db: Session,
    domain: OrgSendingDomain,
    dns_report: Optional[Dict] = None,
) -> Dict[str, Any]:
    records = db.query(OrgDomainRecord).filter(
        OrgDomainRecord.domain_id == domain.id,
    ).all()

    # Get today's stats
    today = date.today()
    stats = db.query(OrgDomainStats).filter(
        OrgDomainStats.domain_id == domain.id,
        OrgDomainStats.date == today,
    ).first()

    v_status = "verified" if domain.status in ("ready", "limited") else ("disabled" if domain.status == "paused" else ("failed" if domain.status == "blocked" else "pending"))
    can_send = domain.status in ("ready", "limited")

    return {
        "id": domain.id,
        "organization_id": domain.organization_id,
        "domain": domain.domain,
        "provider": domain.provider,
        "status": domain.status,
        "verification_status": v_status,
        "can_send": can_send,
        "ses_identity_arn": domain.provider_identity_ref,
        "verification_method": "dns_dkim",
        "from_address": f"{domain.from_local_part}@{domain.domain}" if domain.from_local_part else f"noreply@{domain.domain}",
        "from_name": domain.from_name,
        "reply_to": domain.reply_to,
        "mail_from_subdomain": domain.mail_from_subdomain,
        "daily_cap": domain.daily_cap,
        "paused_reason": domain.paused_reason,
        "last_checked_at": domain.last_checked_at.isoformat() if domain.last_checked_at else None,
        "verified_at": domain.verified_at.isoformat() if domain.verified_at else None,
        "claim_expires_at": domain.claim_expires_at.isoformat() if domain.claim_expires_at else None,
        "created_at": domain.created_at.isoformat() if domain.created_at else None,
        "records": [
            {
                "id": r.id,
                "record_type": r.record_type,
                "host": r.host,
                "value": r.value,
                "purpose": r.purpose,
                "required": r.required,
                "status": r.status,
                "last_result": r.last_result,
                "last_checked_at": r.last_checked_at.isoformat() if r.last_checked_at else None,
            }
            for r in records
        ],
        "today_stats": {
            "sent": stats.sent if stats else 0,
            "bounced": stats.bounced if stats else 0,
            "complained": stats.complained if stats else 0,
        } if stats else None,
        "dns_report": dns_report,
    }


def _serialize_domain_brief(
    domain: OrgSendingDomain,
    records: List[OrgDomainRecord],
) -> Dict[str, Any]:
    return {
        "id": domain.id,
        "domain": domain.domain,
        "status": domain.status,
        "from_address": f"{domain.from_local_part}@{domain.domain}" if domain.from_local_part else f"noreply@{domain.domain}",
        "from_name": domain.from_name,
        "reply_to": domain.reply_to,
        "daily_cap": domain.daily_cap,
        "paused_reason": domain.paused_reason,
        "verified_at": domain.verified_at.isoformat() if domain.verified_at else None,
        "last_checked_at": domain.last_checked_at.isoformat() if domain.last_checked_at else None,
        "record_count": len(records),
        "verified_records": sum(1 for r in records if r.status == "verified"),
    }
