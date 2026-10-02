"""Sending-Domain Authentication Models.

Four new tables for customer sending-domain registration, DNS record
tracking, verification history, and daily send/bounce/complaint stats.

These tables are additive and do NOT modify any existing table schemas.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey,
    Index, Integer, JSON, String, Text, UniqueConstraint,
)
from sqlalchemy.sql import func

from .db import Base


# ─────────────────────────────────────────────────────────────
# 1. ORG SENDING DOMAINS — one row per claimed sending domain
# ─────────────────────────────────────────────────────────────

class OrgSendingDomain(Base):
    """A customer-owned sending domain registered with an email provider
    (e.g. AWS SES).  A domain can be VERIFIED for exactly one organization
    at a time.  Pending/unverified claims expire after
    PENDING_DOMAIN_EXPIRY_DAYS.
    """
    __tablename__ = "org_sending_domains"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    domain = Column(String, nullable=False, unique=True)

    # Provider details
    provider = Column(String, nullable=False, default="ses")
    provider_identity_ref = Column(String, nullable=True)  # identity string at provider

    # Status: pending | blocked | limited | paused | ready
    status = Column(String, nullable=False, default="pending")

    # Sender identity
    from_local_part = Column(String, nullable=True)   # e.g. "john"
    from_name = Column(String, nullable=True)          # display name for From header
    reply_to = Column(String, nullable=False)          # where replies go

    # Custom MAIL FROM subdomain (e.g. "mail" → mail.customer.com)
    mail_from_subdomain = Column(String, nullable=True)

    # Daily sending cap
    daily_cap = Column(Integer, nullable=False, default=200)

    # Pause tracking
    paused_reason = Column(Text, nullable=True)

    # Verification timestamps
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    claim_expires_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


# ─────────────────────────────────────────────────────────────
# 2. ORG DOMAIN RECORDS — DNS records the customer must add
# ─────────────────────────────────────────────────────────────

class OrgDomainRecord(Base):
    """Individual DNS record that must be added by the customer for a
    sending domain to verify.  Records come from the provider response
    (e.g. DKIM CNAME tokens from SES) and from documentation (MAIL FROM
    MX and SPF).
    """
    __tablename__ = "org_domain_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    domain_id = Column(
        String,
        ForeignKey("org_sending_domains.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    record_type = Column(String, nullable=False)   # CNAME, TXT, MX
    host = Column(String, nullable=False)
    value = Column(String, nullable=False)
    purpose = Column(String, nullable=False)        # dkim, spf, mail_from_mx, mail_from_spf
    required = Column(Boolean, default=True)

    # Verification status: pending | verified | failed | warning
    status = Column(String, default="pending")
    last_result = Column(Text, nullable=True)       # human-readable result/error
    last_checked_at = Column(DateTime(timezone=True), nullable=True)


# ─────────────────────────────────────────────────────────────
# 3. ORG DOMAIN CHECK HISTORY — every verification attempt
# ─────────────────────────────────────────────────────────────

class OrgDomainCheckHistory(Base):
    """Audit log of every DNS verification check for a sending domain."""
    __tablename__ = "org_domain_check_history"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    domain_id = Column(
        String,
        ForeignKey("org_sending_domains.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    checked_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    results = Column(JSON, nullable=False)          # snapshot of all record statuses
    triggered_by = Column(String, nullable=True)    # 'user' | 'system' | 'webhook'


# ─────────────────────────────────────────────────────────────
# 4. ORG DOMAIN STATS — daily send/bounce/complaint counters
# ─────────────────────────────────────────────────────────────

class OrgDomainStats(Base):
    """Per-domain, per-day counters for sends, bounces, and complaints.
    Used for daily cap enforcement and auto-pause thresholds.
    """
    __tablename__ = "org_domain_stats"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    domain_id = Column(
        String,
        ForeignKey("org_sending_domains.id", ondelete="CASCADE"),
        nullable=False,
    )
    date = Column(Date, nullable=False)
    sent = Column(Integer, default=0)
    bounced = Column(Integer, default=0)
    complained = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("domain_id", "date", name="uq_domain_stats_day"),
        Index("ix_domain_stats_domain_date", "domain_id", "date"),
    )
