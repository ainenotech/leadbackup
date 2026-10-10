"""Sender Account (Mail ID) Models.

One row per configured sender email address. Each sender is associated
with exactly one sending domain and optionally connected to a real
mailbox via OAuth or SMTP.

These tables are additive and do NOT modify any existing table schemas.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Index, Integer, JSON, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .db import Base


# ─────────────────────────────────────────────────────────────
# 1. SENDER ACCOUNTS — one row per configured sender email
# ─────────────────────────────────────────────────────────────

class SenderAccount(Base):
    """A sender email address associated with a verified sending domain.

    Tracks four independent readiness dimensions:
      - ses_identity_status: Is the SES domain/email identity verified?
      - mailbox_connection_status: Is a real mailbox (OAuth/SMTP) connected?
      - sending_status: Is the sender permitted to send?
      - reply_monitoring_status: Can replies be monitored?

    A sender is only Active when ALL required prerequisites pass.
    """
    __tablename__ = "sender_accounts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email = Column(String, nullable=False)
    display_name = Column(String, nullable=True)

    # FK to the sending domain
    domain_id = Column(
        String,
        ForeignKey("org_sending_domains.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    domain_name = Column(String, nullable=False)  # denormalized for convenience

    # Provider: microsoft_365 | google_workspace | ses_only | smtp_imap
    provider = Column(String, nullable=False, default="ses_only")

    # Link to OrgMailConnection if a mailbox is connected
    provider_connection_id = Column(String, nullable=True)

    # Four independent readiness statuses
    # ses_identity_status: ready | pending | failed | not_started | error
    ses_identity_status = Column(String, nullable=False, default="not_started")

    # mailbox_connection_status: connected | disconnected | not_required | error | needs_reconnect
    mailbox_connection_status = Column(String, nullable=False, default="disconnected")

    # sending_status: ready | blocked | rate_limited | disabled
    sending_status = Column(String, nullable=False, default="blocked")

    # reply_monitoring_status: active | inactive | not_configured | not_available
    reply_monitoring_status = Column(String, nullable=False, default="not_configured")

    # Overall enabled flag (admin toggle)
    enabled = Column(Boolean, nullable=False, default=False)

    # Rate limits
    hourly_limit = Column(Integer, nullable=True, default=50)
    daily_limit = Column(Integer, nullable=True, default=200)
    sends_this_hour = Column(Integer, nullable=False, default=0)
    sends_today = Column(Integer, nullable=False, default=0)
    hour_reset_at = Column(DateTime(timezone=True), nullable=True)
    day_reset_at = Column(DateTime(timezone=True), nullable=True)

    # Warm-up
    warmup_enabled = Column(Boolean, nullable=False, default=False)
    warmup_daily_increment = Column(Integer, nullable=True, default=10)
    warmup_current_limit = Column(Integer, nullable=True)
    warmup_started_at = Column(DateTime(timezone=True), nullable=True)

    # Diagnostics
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    last_send_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)  # sanitized, no secrets

    # Notes
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "email", name="uq_sender_org_email"),
        Index("ix_sender_domain_id", "domain_id"),
        Index("ix_sender_org_enabled", "organization_id", "enabled"),
    )

    @property
    def overall_status(self) -> str:
        """Compute overall sender status from the four readiness dimensions."""
        if not self.enabled:
            return "disabled"

        if self.provider == "ses_only" and self.ses_identity_status != "ready":
            return "ses_pending"

        if self.provider in ("microsoft_365", "google_workspace", "smtp_imap"):
            if self.mailbox_connection_status not in ("connected", "not_required"):
                return "mailbox_disconnected"

        if self.sending_status == "rate_limited":
            return "rate_limited"
        if self.sending_status != "ready":
            return "blocked"

        return "active"

    @property
    def is_send_ready(self) -> bool:
        """True only when ALL required prerequisites pass."""
        if not self.enabled:
            return False
        if self.provider == "ses_only" and self.ses_identity_status != "ready":
            return False
        if self.sending_status != "ready":
            return False
        if self.provider in ("microsoft_365", "google_workspace", "smtp_imap"):
            if self.mailbox_connection_status not in ("connected", "not_required"):
                return False
        return True

    def readiness_checklist(self) -> list:
        """Return a list of check dicts for UI display."""
        checks = [
            {
                "label": "Email & domain relationship valid",
                "passed": bool(self.domain_id and self.domain_name),
                "detail": f"{self.email} → {self.domain_name}" if self.domain_name else "No domain assigned",
            },
            {
                "label": "SES identity ready",
                "passed": self.ses_identity_status == "ready",
                "detail": f"Status: {self.ses_identity_status}",
            },
        ]

        if self.provider in ("microsoft_365", "google_workspace", "smtp_imap"):
            checks.append({
                "label": "Mailbox connected",
                "passed": self.mailbox_connection_status == "connected",
                "detail": f"Provider: {self.provider}, Status: {self.mailbox_connection_status}",
            })

        checks.extend([
            {
                "label": "Sending permission ready",
                "passed": self.sending_status == "ready",
                "detail": f"Status: {self.sending_status}",
            },
            {
                "label": "Reply monitoring configured",
                "passed": self.reply_monitoring_status in ("active", "not_available"),
                "detail": f"Status: {self.reply_monitoring_status}",
            },
            {
                "label": "Sender enabled",
                "passed": self.enabled,
                "detail": "Enabled" if self.enabled else "Disabled by admin",
            },
        ])

        return checks
