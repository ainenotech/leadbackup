"""Multi-Tenant Foundation Models — organizations, users, memberships, roles.

These tables form the SaaS multi-tenancy backbone. They are additive and
do NOT modify any existing table schemas. Existing tables will gain an
`organization_id` column via a separate migration step.

Design principles:
  - One codebase, one database, organization-based data isolation.
  - organization_id is NEVER trusted from the client; it is always
    resolved from the authenticated user's session/JWT.
  - SSO-ready: identity_accounts table allows multiple auth providers
    per user without redesigning the users table.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Index, Integer,
    JSON, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .db import Base


# ─────────────────────────────────────────────────────────────
# 1. ORGANIZATIONS — top-level tenant entity
# ─────────────────────────────────────────────────────────────

class Organization(Base):
    """One row per tenant organization on the platform."""
    __tablename__ = "organizations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)                 # Display name
    slug = Column(String, nullable=False, unique=True)     # URL-safe identifier
    legal_name = Column(String, nullable=True)             # Registered legal name
    industry = Column(String, nullable=True)
    company_size = Column(String, nullable=True)           # e.g. "1-10", "11-50", "51-200"
    description = Column(Text, nullable=True)

    # Contact
    email = Column(String, nullable=True)                  # Primary org email
    support_email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    alt_phone = Column(String, nullable=True)

    # Address
    address_line1 = Column(String, nullable=True)
    address_line2 = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    country = Column(String, nullable=True)
    postal_code = Column(String, nullable=True)
    timezone = Column(String, nullable=True, default="UTC")

    # Web presence
    website = Column(String, nullable=True)

    # Social links (stored as JSON dict for flexibility)
    social_links = Column(JSON, nullable=True)
    # Expected format: {"linkedin": "...", "twitter": "...", "instagram": "...", "facebook": "...", "youtube": "..."}

    # Branding — URLs/keys to object storage, NEVER binary data
    logo_url = Column(String, nullable=True)
    profile_image_url = Column(String, nullable=True)
    brand_name = Column(String, nullable=True)
    brand_colors = Column(JSON, nullable=True)
    # Expected format: {"primary": "#1A5CFF", "secondary": "#0F172A", "accent": "#059669"}

    # Platform status
    # active | pending | suspended | deactivated
    status = Column(String, default="active", nullable=False)
    is_platform_org = Column(Boolean, default=False)       # True for the SaaS platform's own org

    # Onboarding progress (JSON tracking which steps are complete)
    onboarding_status = Column(JSON, nullable=True)
    onboarding_completed = Column(Boolean, default=False)

    # Settings (JSON blob for org-level config overrides)
    settings = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ─────────────────────────────────────────────────────────────
# 2. USERS — individual platform accounts
# ─────────────────────────────────────────────────────────────

class User(Base):
    """One row per registered user. Authentication credentials are
    stored separately (password_hash here, SSO in identity_accounts).
    Profile photo is stored in object storage; only the URL/key is here.
    """
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, nullable=False, unique=True, index=True)
    email_verified = Column(Boolean, default=False)

    # Password auth (Argon2id or bcrypt hash — NEVER plaintext)
    password_hash = Column(String, nullable=True)  # Null if SSO-only user

    # Profile
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    job_title = Column(String, nullable=True)
    phone = Column(String, nullable=True)

    # Profile photo — URL/key only, NOT binary
    profile_photo_url = Column(String, nullable=True)

    # Social links
    social_links = Column(JSON, nullable=True)
    # Expected: {"linkedin": "...", "twitter": "...", "instagram": "...", "facebook": "..."}

    # Platform-level role (separate from org-level roles)
    # platform_super_admin | user
    platform_role = Column(String, default="user", nullable=False)

    # Account status: active | pending_verification | suspended | deactivated
    status = Column(String, default="pending_verification", nullable=False)

    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ─────────────────────────────────────────────────────────────
# 3. ORGANIZATION MEMBERS — links users to organizations with roles
# ─────────────────────────────────────────────────────────────

class OrganizationMember(Base):
    """Associates a User with an Organization and assigns an org-level role.
    A user can belong to multiple organizations (future capability).
    """
    __tablename__ = "organization_members"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Org-level role:
    # organization_owner | organization_admin | campaign_manager | sales_user | regular_user | viewer
    role = Column(String, default="regular_user", nullable=False)

    # Whether this is the user's currently active/default organization
    is_default = Column(Boolean, default=True)

    # Member status: active | invited | suspended | removed
    status = Column(String, default="active", nullable=False)

    invited_by = Column(String, nullable=True)   # user_id of who invited them
    invited_at = Column(DateTime(timezone=True), nullable=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_org_member"),
        Index("ix_org_member_org_role", "organization_id", "role"),
    )


# ─────────────────────────────────────────────────────────────
# 4. IDENTITY ACCOUNTS — SSO / external auth providers
# ─────────────────────────────────────────────────────────────

class IdentityAccount(Base):
    """Links a User to external identity providers (Google, Microsoft, etc.).
    Allows multiple providers per user and new providers to be added
    without modifying the users table.
    """
    __tablename__ = "identity_accounts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Provider: google | microsoft | okta | auth0 | azure_ad | oidc | saml
    provider = Column(String, nullable=False)
    provider_user_id = Column(String, nullable=False)     # External user ID from provider
    provider_email = Column(String, nullable=True)

    # Metadata from the provider (profile data, etc.)
    provider_data = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_identity_provider_user"),
        Index("ix_identity_user_provider", "user_id", "provider"),
    )

    @property
    def provider_subject(self) -> str:
        return self.provider_user_id

    @provider_subject.setter
    def provider_subject(self, val: str):
        self.provider_user_id = val

    @property
    def email(self) -> Optional[str]:
        return self.provider_email

    @email.setter
    def email(self, val: Optional[str]):
        self.provider_email = val


# Aliases for architecture specifications
OAuthIdentity = IdentityAccount
OrganizationMembership = OrganizationMember


# ─────────────────────────────────────────────────────────────
# 5. SESSIONS — server-side session tracking
# ─────────────────────────────────────────────────────────────

class Session(Base):
    """Server-side session for authenticated users."""
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)

    # Session token (hashed) — the raw token is sent to client as a cookie
    token_hash = Column(String, nullable=False, unique=True, index=True)

    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_session_user_active", "user_id", "is_active"),
    )


# ─────────────────────────────────────────────────────────────
# 6. OTP CODES — email verification, password reset
# ─────────────────────────────────────────────────────────────

class OTPCode(Base):
    """One-time passcodes for email verification and password reset.
    Codes are hashed (never stored in plaintext if avoidable),
    expire after a set duration, are single-use, and have
    attempt limits to prevent brute-force.
    """
    __tablename__ = "otp_codes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    email = Column(String, nullable=False, index=True)

    # Purpose: email_verification | password_reset | login_otp
    purpose = Column(String, nullable=False)

    # The OTP code hash (bcrypt or SHA-256 of the 6-digit code)
    code_hash = Column(String, nullable=False)

    # Security controls
    attempts = Column(Integer, default=0)        # Failed verification attempts
    max_attempts = Column(Integer, default=5)    # Lock after this many failures
    is_used = Column(Boolean, default=False)

    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_otp_email_purpose", "email", "purpose"),
    )


# ─────────────────────────────────────────────────────────────
# 7. LOGIN TICKETS — short-lived session handoff tokens
# ─────────────────────────────────────────────────────────────

class LoginTicket(Base):
    """Short-lived, single-use ticket to securely handoff sessions from the OAuth callback to Streamlit."""
    __tablename__ = "login_tickets"

    ticket_hash = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

