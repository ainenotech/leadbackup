"""Email Channels Models.

Tables for MX-based method chooser history and unified email connection registry.
"""
import uuid
from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
)
from sqlalchemy.sql import func

import Backend.auth_models
from .db import Base


class OrgDomainSnapshot(Base):
    """Stores the lookup result per domain (MX, SPF, DKIM, DMARC) for history."""
    __tablename__ = "org_domain_snapshots"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    domain = Column(String, nullable=False)
    checked_at = Column(DateTime(timezone=True), server_default=func.now())
    results = Column(JSON, nullable=False)


class OrgMailConnection(Base):
    """Unified email connection registry for an organization.
    
    Includes oauth tokens (encrypted), smtp passwords (encrypted), status, and daily caps.
    """
    __tablename__ = "org_mail_connections"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email = Column(String, nullable=False)
    domain = Column(String, nullable=False)
    
    # microsoft_oauth | google_oauth | smtp_imap | own_domain | customer_domain
    channel = Column(String, nullable=False)
    
    # active | needs_reconnect | paused | pending
    status = Column(String, nullable=False, default="pending")
    is_default = Column(Boolean, nullable=False, default=False)
    
    daily_cap = Column(Integer, nullable=False, default=200)
    sent_today = Column(Integer, nullable=False, default=0)
    sent_today_date = Column(Date, nullable=True)
    
    # Encrypted JSON payload for secrets
    encrypted_secret = Column(Text, nullable=True)
    
    # Non-secret config JSON (e.g. host, port, refresh_token_expiry)
    config = Column(JSON, nullable=True)
    
    last_error = Column(Text, nullable=True)
    last_polled_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "email", name="uq_org_mail_email"),
    )


class OAuthFlowState(Base):
    """Secure single-use state tracker for OAuth flows (PKCE)."""
    __tablename__ = "oauth_flow_states"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    state_hash = Column(String, unique=True, nullable=False, index=True)
    provider = Column(String, nullable=False)
    organization_id = Column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(String, nullable=False)
    expected_email = Column(String, nullable=False)
    
    # Encrypted JSON containing PKCE code_verifier, etc.
    flow_data_encrypted = Column(Text, nullable=False)
    
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())



class OrgSendSelection(Base):
    """Stores the explicitly selected channel per campaign for an organization."""
    __tablename__ = "org_send_selections"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    campaign_name = Column(String, nullable=False, index=True)
    channel_ref_id = Column(String, nullable=False)
    channel_type = Column(String, nullable=False)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "campaign_name", name="uq_org_campaign_selection"),
    )


class SendAttempt(Base):
    """Records every attempt to send an email via any channel."""
    __tablename__ = "send_attempts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lead_id = Column(String, nullable=False, index=True)
    campaign_name = Column(String, nullable=False)
    channel = Column(String, nullable=False)
    channel_ref_id = Column(String, nullable=True)
    channel_type = Column(String, nullable=True)
    from_address = Column(String, nullable=True)
    
    # sent | skipped | failed
    status = Column(String, nullable=False)
    reason = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
