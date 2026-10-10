"""Sender Account Service — business logic for Mail ID management.

Handles sender account CRUD, domain association, multi-dimensional
readiness checks (SES identity, mailbox connection, sending permissions,
reply monitoring), rate limiting, and campaign eligibility checks.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import or_

from Backend.auth_models import OrganizationMember, User
from Backend.channels_models import OrgMailConnection
from Backend.domain_models import OrgSendingDomain
from Backend.sender_models import SenderAccount

logger = logging.getLogger("sender_account_service")


def _verify_admin_access(db: Session, user_id: str, org_id: str) -> None:
    """Ensure the user is an owner, admin, or platform super admin."""
    user = db.query(User).filter(User.id == user_id).first()
    if user and user.platform_role == "platform_super_admin":
        return

    membership = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user_id,
            OrganizationMember.status == "active",
        )
        .first()
    )
    if not membership or membership.role not in (
        "owner",
        "admin",
        "organization_owner",
        "organization_admin",
    ):
        raise PermissionError("Admin access required for sender management")


def _reset_rate_limits_if_needed(sender: SenderAccount, now: datetime) -> bool:
    """Reset hourly and daily send counters if the reset window has passed.
    
    Returns True if changes were made to the record.
    """
    changed = False

    # Check hourly reset
    hour_reset = sender.hour_reset_at
    if hour_reset and hour_reset.tzinfo is None:
        hour_reset = hour_reset.replace(tzinfo=timezone.utc)
    if not hour_reset or now >= hour_reset:
        sender.sends_this_hour = 0
        sender.hour_reset_at = now + timedelta(hours=1)
        changed = True

    # Check daily reset (midnight UTC or 24h)
    day_reset = sender.day_reset_at
    if day_reset and day_reset.tzinfo is None:
        day_reset = day_reset.replace(tzinfo=timezone.utc)
    if not day_reset or now >= day_reset:
        sender.sends_today = 0
        sender.day_reset_at = now + timedelta(days=1)
        changed = True

    return changed


def _evaluate_readiness(
    sender: SenderAccount,
    domain: Optional[OrgSendingDomain],
    conn: Optional[OrgMailConnection],
) -> None:
    """Re-evaluate the four readiness dimensions and sending_status."""
    # 1. SES Identity Status
    if sender.provider == "ses_only":
        if domain:
            if domain.status in ("ready", "limited", "verified"):
                sender.ses_identity_status = "ready"
            elif domain.status in ("pending", "blocked"):
                sender.ses_identity_status = "pending"
            elif domain.status == "failed":
                sender.ses_identity_status = "failed"
            else:
                sender.ses_identity_status = domain.status or "not_started"
        else:
            sender.ses_identity_status = "not_started"
    else:
        sender.ses_identity_status = "not_required"

    # 2. Mailbox Connection Status
    if sender.provider == "ses_only":
        sender.mailbox_connection_status = "not_required"
        sender.reply_monitoring_status = "not_available"
    elif sender.provider in ("microsoft_365", "google_workspace", "smtp_imap"):
        if conn and conn.status == "active":
            sender.mailbox_connection_status = "connected"
            sender.provider_connection_id = conn.id
            sender.reply_monitoring_status = "active"
        elif conn and conn.status == "needs_reconnect":
            sender.mailbox_connection_status = "needs_reconnect"
            sender.reply_monitoring_status = "inactive"
        else:
            sender.mailbox_connection_status = "disconnected"
            sender.reply_monitoring_status = "not_configured"

    # 3. Sending Status
    if not sender.enabled:
        sender.sending_status = "disabled"
    elif domain and domain.status == "paused":
        sender.sending_status = "blocked"
    elif sender.provider == "ses_only" and sender.ses_identity_status != "ready":
        sender.sending_status = "blocked"
    elif sender.provider in ("microsoft_365", "google_workspace", "smtp_imap") and sender.mailbox_connection_status != "connected":
        sender.sending_status = "blocked"
    else:
        sends_hour = sender.sends_this_hour or 0
        sends_day = sender.sends_today or 0
        if (
            (sender.hourly_limit and sends_hour >= sender.hourly_limit)
            or (sender.daily_limit and sends_day >= sender.daily_limit)
        ):
            sender.sending_status = "rate_limited"
        else:
            sender.sending_status = "ready"


def create_sender_account(
    db: Session,
    user_id: str,
    org_id: str,
    email: str,
    display_name: Optional[str] = None,
    domain_id: Optional[str] = None,
    provider: str = "ses_only",
    hourly_limit: Optional[int] = 50,
    daily_limit: Optional[int] = 200,
    warmup_enabled: bool = False,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new sender email address under the given organization."""
    _verify_admin_access(db, user_id, org_id)

    email = email.strip().lower()
    if "@" not in email:
        raise ValueError(f"Invalid email address: {email}")

    domain_part = email.split("@")[1].strip().lower()

    is_common_webmail = domain_part in (
        "gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "live.com", "msn.com", "yahoo.com"
    ) or provider in ("google_workspace", "microsoft_365")

    # Find associated domain if provided or matching
    domain = None
    if domain_id:
        domain = (
            db.query(OrgSendingDomain)
            .filter(
                OrgSendingDomain.id == domain_id,
                OrgSendingDomain.organization_id == org_id,
            )
            .first()
        )
        if not domain:
            raise ValueError(f"Domain with ID '{domain_id}' not found in organization")
        if not is_common_webmail and domain.domain.lower() != domain_part:
            raise ValueError(
                f"Email domain '@{domain_part}' does not match specified domain '@{domain.domain}'"
            )
    else:
        domain = (
            db.query(OrgSendingDomain)
            .filter(
                OrgSendingDomain.domain == domain_part,
                OrgSendingDomain.organization_id == org_id,
            )
            .first()
        )
        if not domain and not is_common_webmail:
            raise ValueError(
                f"Domain '@{domain_part}' must be registered in organization before adding sender accounts"
            )

    # Check for duplicate
    existing = (
        db.query(SenderAccount)
        .filter(
            SenderAccount.organization_id == org_id,
            SenderAccount.email == email,
        )
        .first()
    )
    if existing:
        raise ValueError(f"Sender account '{email}' already exists in this organization")

    # Check if a mailbox connection already exists for this email
    conn = (
        db.query(OrgMailConnection)
        .filter(
            OrgMailConnection.organization_id == org_id,
            OrgMailConnection.email == email,
        )
        .first()
    )

    now = datetime.now(timezone.utc)
    sender = SenderAccount(
        organization_id=org_id,
        email=email,
        display_name=display_name or email.split("@")[0].replace(".", " ").title(),
        domain_id=domain.id if domain else None,
        domain_name=domain.domain if domain else domain_part,
        provider=provider,
        enabled=True,
        hourly_limit=hourly_limit,
        daily_limit=daily_limit,
        warmup_enabled=warmup_enabled,
        warmup_current_limit=warmup_enabled and 10 or None,
        warmup_started_at=now if warmup_enabled else None,
        notes=notes,
        hour_reset_at=now + timedelta(hours=1),
        day_reset_at=now + timedelta(days=1),
        sends_this_hour=0,
        sends_today=0,
        last_checked_at=now,
    )

    _evaluate_readiness(sender, domain, conn)

    db.add(sender)
    db.commit()
    db.refresh(sender)

    return sender_to_dict(sender)


def list_sender_accounts(
    db: Session,
    user_id: str,
    org_id: str,
    domain_id: Optional[str] = None,
    provider: Optional[str] = None,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List sender accounts for an organization with optional filters."""
    _verify_admin_access(db, user_id, org_id)

    query = db.query(SenderAccount).filter(SenderAccount.organization_id == org_id)

    if domain_id:
        query = query.filter(SenderAccount.domain_id == domain_id)
    if provider:
        query = query.filter(SenderAccount.provider == provider)
    if search:
        search_term = f"%{search.strip().lower()}%"
        query = query.filter(
            or_(
                SenderAccount.email.ilike(search_term),
                SenderAccount.display_name.ilike(search_term),
                SenderAccount.domain_name.ilike(search_term),
            )
        )

    senders = query.order_by(SenderAccount.created_at.desc()).all()
    now = datetime.now(timezone.utc)

    # Check rate resets and filter by overall_status if requested
    results = []
    for sender in senders:
        if _reset_rate_limits_if_needed(sender, now):
            db.commit()

        s_dict = sender_to_dict(sender)
        if status_filter:
            if status_filter.lower() != s_dict["overall_status"].lower():
                continue
        results.append(s_dict)

    return results


def get_sender_account(
    db: Session,
    user_id: str,
    org_id: str,
    sender_id: str,
) -> Dict[str, Any]:
    """Get single sender account details."""
    _verify_admin_access(db, user_id, org_id)

    sender = (
        db.query(SenderAccount)
        .filter(
            SenderAccount.id == sender_id,
            SenderAccount.organization_id == org_id,
        )
        .first()
    )
    if not sender:
        raise ValueError(f"Sender account '{sender_id}' not found")

    now = datetime.now(timezone.utc)
    if _reset_rate_limits_if_needed(sender, now):
        db.commit()

    return sender_to_dict(sender)


def update_sender_account(
    db: Session,
    user_id: str,
    org_id: str,
    sender_id: str,
    display_name: Optional[str] = None,
    hourly_limit: Optional[int] = None,
    daily_limit: Optional[int] = None,
    warmup_enabled: Optional[bool] = None,
    notes: Optional[str] = None,
    enabled: Optional[bool] = None,
    provider: Optional[str] = None,
) -> Dict[str, Any]:
    """Update sender settings."""
    _verify_admin_access(db, user_id, org_id)

    sender = (
        db.query(SenderAccount)
        .filter(
            SenderAccount.id == sender_id,
            SenderAccount.organization_id == org_id,
        )
        .first()
    )
    if not sender:
        raise ValueError(f"Sender account '{sender_id}' not found")

    if display_name is not None:
        sender.display_name = display_name
    if hourly_limit is not None:
        sender.hourly_limit = hourly_limit
    if daily_limit is not None:
        sender.daily_limit = daily_limit
    if notes is not None:
        sender.notes = notes
    if enabled is not None:
        sender.enabled = enabled
    if provider is not None:
        sender.provider = provider
    if warmup_enabled is not None:
        sender.warmup_enabled = warmup_enabled
        if warmup_enabled and not sender.warmup_started_at:
            sender.warmup_started_at = datetime.now(timezone.utc)
            sender.warmup_current_limit = 10

    domain = (
        db.query(OrgSendingDomain).filter(OrgSendingDomain.id == sender.domain_id).first()
        if sender.domain_id
        else None
    )
    conn = (
        db.query(OrgMailConnection)
        .filter(
            OrgMailConnection.organization_id == org_id,
            OrgMailConnection.email == sender.email,
        )
        .first()
    )

    _evaluate_readiness(sender, domain, conn)

    db.commit()
    db.refresh(sender)
    return sender_to_dict(sender)


def delete_sender_account(
    db: Session,
    user_id: str,
    org_id: str,
    sender_id: str,
) -> bool:
    """Delete a sender account."""
    _verify_admin_access(db, user_id, org_id)

    sender = (
        db.query(SenderAccount)
        .filter(
            SenderAccount.id == sender_id,
            SenderAccount.organization_id == org_id,
        )
        .first()
    )
    if not sender:
        raise ValueError(f"Sender account '{sender_id}' not found")

    db.delete(sender)
    db.commit()
    return True


def refresh_sender_readiness(
    db: Session,
    user_id: str,
    org_id: str,
    sender_id: str,
) -> Dict[str, Any]:
    """Perform a live check on domain SES status & mailbox connection and update sender."""
    _verify_admin_access(db, user_id, org_id)

    sender = (
        db.query(SenderAccount)
        .filter(
            SenderAccount.id == sender_id,
            SenderAccount.organization_id == org_id,
        )
        .first()
    )
    if not sender:
        raise ValueError(f"Sender account '{sender_id}' not found")

    domain = (
        db.query(OrgSendingDomain).filter(OrgSendingDomain.id == sender.domain_id).first()
        if sender.domain_id
        else None
    )
    conn = (
        db.query(OrgMailConnection)
        .filter(
            OrgMailConnection.organization_id == org_id,
            OrgMailConnection.email == sender.email,
        )
        .first()
    )

    now = datetime.now(timezone.utc)
    _reset_rate_limits_if_needed(sender, now)
    _evaluate_readiness(sender, domain, conn)

    sender.last_checked_at = now
    sender.last_error = None
    db.commit()
    db.refresh(sender)

    return sender_to_dict(sender)


def check_sender_eligibility(
    db: Session,
    org_id: str,
    sender_email_or_id: str,
) -> Dict[str, Any]:
    """Campaign worker helper: Checks if a sender is currently eligible to send email.
    
    Verifies domain verification, enabled flag, mailbox connection (if required),
    and rate limits. Returns:
      {"eligible": True/False, "reason": str, "sender": SenderAccount | None}
    """
    sender = (
        db.query(SenderAccount)
        .filter(
            SenderAccount.organization_id == org_id,
            or_(
                SenderAccount.id == sender_email_or_id,
                SenderAccount.email == sender_email_or_id.lower().strip(),
            ),
        )
        .first()
    )

    if not sender:
        return {
            "eligible": False,
            "reason": f"Sender account '{sender_email_or_id}' is not registered in organization",
            "sender": None,
        }

    now = datetime.now(timezone.utc)
    _reset_rate_limits_if_needed(sender, now)

    if not sender.enabled:
        return {"eligible": False, "reason": "Sender is disabled by admin", "sender": sender}

    # Verify domain only if provider is SES
    if sender.provider == "ses_only":
        domain = (
            db.query(OrgSendingDomain).filter(OrgSendingDomain.id == sender.domain_id).first()
            if sender.domain_id
            else None
        )
        if not domain:
            return {"eligible": False, "reason": "Sender domain is not registered in SES", "sender": sender}

        if domain.status not in ("ready", "limited", "verified"):
            return {
                "eligible": False,
                "reason": f"Sender domain '{domain.domain}' is not verified (status: {domain.status})",
                "sender": sender,
            }

        if domain.status == "paused":
            return {
                "eligible": False,
                "reason": f"Sending is paused for domain '{domain.domain}'",
                "sender": sender,
            }

    # Check mailbox connection if required
    if sender.provider in ("microsoft_365", "google_workspace", "smtp_imap"):
        conn = (
            db.query(OrgMailConnection)
            .filter(
                OrgMailConnection.organization_id == org_id,
                OrgMailConnection.email == sender.email,
            )
            .first()
        )
        if not conn or conn.status != "active":
            return {
                "eligible": False,
                "reason": f"Mailbox for '{sender.email}' ({sender.provider}) is not connected or requires reconnect",
                "sender": sender,
            }

    # Check rate limits
    if sender.hourly_limit and sender.sends_this_hour >= sender.hourly_limit:
        return {
            "eligible": False,
            "reason": f"Hourly limit reached ({sender.sends_this_hour}/{sender.hourly_limit})",
            "sender": sender,
        }

    effective_daily_limit = (
        sender.warmup_current_limit
        if (sender.warmup_enabled and sender.warmup_current_limit)
        else sender.daily_limit
    )
    if effective_daily_limit and sender.sends_today >= effective_daily_limit:
        return {
            "eligible": False,
            "reason": f"Daily limit reached ({sender.sends_today}/{effective_daily_limit})",
            "sender": sender,
        }

    return {"eligible": True, "reason": "Sender ready", "sender": sender}


def record_sender_send(db: Session, sender_id: str) -> None:
    """Record an email send against rate limits."""
    sender = db.query(SenderAccount).filter(SenderAccount.id == sender_id).first()
    if not sender:
        return

    now = datetime.now(timezone.utc)
    _reset_rate_limits_if_needed(sender, now)

    sender.sends_this_hour += 1
    sender.sends_today += 1
    sender.last_send_at = now
    db.commit()


def sender_to_dict(sender: SenderAccount) -> Dict[str, Any]:
    """Serialize a SenderAccount model to a clean dictionary."""
    return {
        "id": sender.id,
        "organization_id": sender.organization_id,
        "email": sender.email,
        "display_name": sender.display_name,
        "domain_id": sender.domain_id,
        "domain_name": sender.domain_name,
        "provider": sender.provider,
        "provider_connection_id": sender.provider_connection_id,
        "ses_identity_status": sender.ses_identity_status,
        "mailbox_connection_status": sender.mailbox_connection_status,
        "sending_status": sender.sending_status,
        "reply_monitoring_status": sender.reply_monitoring_status,
        "overall_status": sender.overall_status,
        "is_send_ready": sender.is_send_ready,
        "enabled": sender.enabled,
        "hourly_limit": sender.hourly_limit,
        "daily_limit": sender.daily_limit,
        "sends_this_hour": sender.sends_this_hour,
        "sends_today": sender.sends_today,
        "hour_reset_at": sender.hour_reset_at.isoformat() if sender.hour_reset_at else None,
        "day_reset_at": sender.day_reset_at.isoformat() if sender.day_reset_at else None,
        "warmup_enabled": sender.warmup_enabled,
        "warmup_daily_increment": sender.warmup_daily_increment,
        "warmup_current_limit": sender.warmup_current_limit,
        "last_checked_at": sender.last_checked_at.isoformat() if sender.last_checked_at else None,
        "last_send_at": sender.last_send_at.isoformat() if sender.last_send_at else None,
        "last_error": sender.last_error,
        "notes": sender.notes,
        "readiness_checklist": sender.readiness_checklist(),
        "created_at": sender.created_at.isoformat() if sender.created_at else None,
        "updated_at": sender.updated_at.isoformat() if sender.updated_at else None,
    }
