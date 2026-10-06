"""SES Multi-Tenant Sending Service.

Enforces strict tenant isolation, verified domain ownership, and daily caps
before dispatching outbound emails via AWS SES.
"""

from datetime import date, datetime, timezone
import logging
import os
import re
from typing import Any, Dict, Optional
import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from Backend.auth_models import Organization
from Backend.domain_models import OrgDomainStats, OrgSendingDomain
from services.domain_auth_service import _get_provider

logger = logging.getLogger("ses_send_service")


def validate_and_send_ses_email(
    db: Session,
    organization_id: str,
    from_email: str,
    to_email: str,
    subject: str,
    body: str,
    html_body: Optional[str] = None,
) -> Dict[str, Any]:
    """Strictly validates tenant ownership and verification status before sending via SES.

    Enforces the 6-step target architecture:
      1. Resolve current organization
      2. Resolve selected sending domain
      3. Confirm organization owns domain
      4. Confirm SES identity is verified
      5. Confirm sender address belongs to verified domain
      6. Send through SES
    """
    clean_from = from_email.strip().lower()
    clean_to = to_email.strip().lower()

    if not clean_from or "@" not in clean_from:
        raise ValueError(f"Invalid sender email address: '{from_email}'")
    if not clean_to or "@" not in clean_to:
        raise ValueError(f"Invalid recipient email address: '{to_email}'")

    # 1. Resolve current organization
    org = db.query(Organization).filter(
        Organization.id == organization_id,
        Organization.status == "active",
    ).first()
    if not org:
        raise ValueError(f"Organization '{organization_id}' not found or is inactive.")

    # 2. Resolve selected sending domain
    sender_domain = clean_from.split("@")[1].strip()

    # 3. Confirm organization owns domain
    domain_rec = db.query(OrgSendingDomain).filter(
        OrgSendingDomain.organization_id == organization_id,
        func.lower(OrgSendingDomain.domain) == sender_domain,
    ).first()

    if not domain_rec:
        # Check if another organization owns this domain to provide explicit cross-tenant rejection
        other_claim = db.query(OrgSendingDomain).filter(
            func.lower(OrgSendingDomain.domain) == sender_domain,
        ).first()
        if other_claim:
            raise PermissionError(
                f"Cross-organization domain rejected: '{sender_domain}' belongs to another organization."
            )
        raise ValueError(
            f"Domain '{sender_domain}' is not registered to organization '{org.name}'."
        )

    # 4. Confirm SES identity is verified
    if domain_rec.status not in ("ready", "limited"):
        raise ValueError(
            f"Cannot send email: domain '{sender_domain}' is not verified (status: {domain_rec.status}). "
            "DNS DKIM records must be verified before outbound sending is enabled."
        )

    if domain_rec.status == "paused":
        raise ValueError(
            f"Outbound sending is currently paused for domain '{sender_domain}': {domain_rec.paused_reason or 'Paused by administrator'}"
        )

    # 5. Confirm sender address belongs to verified domain
    if not clean_from.endswith(f"@{domain_rec.domain.lower()}"):
        raise ValueError(
            f"Sender address '{clean_from}' does not match verified domain '{domain_rec.domain}'."
        )

    # Check daily cap
    today = date.today()
    stats = db.query(OrgDomainStats).filter(
        OrgDomainStats.domain_id == domain_rec.id,
        OrgDomainStats.date == today,
    ).first()

    if stats and stats.sent >= domain_rec.daily_cap:
        raise ValueError(
            f"Daily sending cap ({domain_rec.daily_cap}) reached for domain '{sender_domain}' on {today}."
        )

    # 6. Send through SES provider
    provider = _get_provider()
    short_org = organization_id[:8] if len(organization_id) >= 8 else organization_id
    cs_name = f"org-{short_org}"

    send_result = provider.send_email(
        from_email=clean_from,
        to_email=clean_to,
        subject=subject,
        body=body,
        html_body=html_body,
        configuration_set_name=cs_name,
    )

    # Update daily send stats
    if not stats:
        stats = OrgDomainStats(
            id=str(uuid.uuid4()),
            domain_id=domain_rec.id,
            date=today,
            sent=1,
            bounced=0,
            complained=0,
        )
        db.add(stats)
    else:
        stats.sent += 1

    db.commit()

    logger.info("SES email dispatched from %s to %s for org %s", clean_from, clean_to, organization_id)
    return {
        "status": "sent",
        "domain": domain_rec.domain,
        "organization_id": organization_id,
        "provider_response": send_result,
        "success": True,
        "message_id": send_result.get("MessageId", str(uuid.uuid4())) if isinstance(send_result, dict) else str(uuid.uuid4()),
    }


# Export alias matching architectural spec
validate_and_send_via_ses = validate_and_send_ses_email

