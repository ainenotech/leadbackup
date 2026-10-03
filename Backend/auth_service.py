"""Multi-Tenant Authentication & Organization Management Service.

Provides complete SaaS authentication, user lifecycle, multi-tenant RBAC,
organization switcher, team invitations, and org-level configuration.
"""

import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import bcrypt
import jwt
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from .auth_models import Organization, OrganizationMember, User, Session as UserSession
from .models import CampaignLog, KnowledgeDocument
from .master_db_models import MasterLead, LeadImport

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "neno-saas-universal-secret-key-prod-2026")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 72


# ─────────────────────────────────────────────────────────────
# 1. PASSWORD SECURITY (bcrypt)
# ─────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Generate a secure bcrypt hash for a plaintext password."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: Optional[str]) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    if not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────
# 2. JWT TOKEN ENGINE
# ─────────────────────────────────────────────────────────────

def create_access_token(
    user_id: str,
    org_id: Optional[str] = None,
    role: str = "regular_user",
    email: str = "",
    platform_role: str = "user",
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token containing tenant context."""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    payload = {
        "sub": user_id,
        "email": email,
        "org_id": org_id,
        "role": role,
        "platform_role": platform_role,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────
# 3. SLUG UTILITY
# ─────────────────────────────────────────────────────────────

def generate_org_slug(name: str, db: Session) -> str:
    """Generate a clean, unique URL slug for an organization."""
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not base:
        base = "org"
    slug = base
    counter = 1
    while db.query(Organization).filter(Organization.slug == slug).first():
        slug = f"{base}-{counter}"
        counter += 1
    return slug


# ─────────────────────────────────────────────────────────────
# 4. REGISTRATION & ONBOARDING
# ─────────────────────────────────────────────────────────────

def register_organization_and_user(
    db: Session,
    org_name: str,
    admin_email: str,
    password: str,
    full_name: Optional[str] = None,
    industry: Optional[str] = None,
    company_size: Optional[str] = None,
    phone: Optional[str] = None,
    website: Optional[str] = None,
) -> Dict[str, Any]:
    """Complete SaaS signup flow:
    1. Creates Organization
    2. Creates User
    3. Creates OrganizationMember with role='organization_owner'
    4. Generates initial JWT token
    """
    clean_email = admin_email.strip().lower()

    # Check if user already exists
    existing_user = db.query(User).filter(User.email == clean_email).first()
    if existing_user and existing_user.password_hash:
        raise ValueError(f"An account with email '{clean_email}' already exists. Please log in.")

    # Create Organization
    slug = generate_org_slug(org_name, db)
    org = Organization(
        id=str(uuid.uuid4()),
        name=org_name.strip(),
        slug=slug,
        industry=industry,
        company_size=company_size,
        email=clean_email,
        phone=phone,
        website=website,
        status="active",
        onboarding_completed=True,
        brand_name=org_name.strip(),
        settings={
            "ai": {
                "provider": "openai",
                "model": "gpt-4o",
                "custom_api_key": "",
                "custom_system_prompt": "",
                "tone": "professional",
            },
            "sender": {
                "provider": "microsoft_graph",
                "sender_email": clean_email,
                "sender_name": full_name or org_name,
            },
            "booking": {
                "type": "teams",
                "booking_link": "",
                "duration_minutes": 30,
            },
        },
    )
    db.add(org)
    db.flush()

    # Create or update User
    if existing_user:
        user = existing_user
        user.password_hash = hash_password(password)
        if full_name:
            user.full_name = full_name.strip()
        user.status = "active"
    else:
        user = User(
            id=str(uuid.uuid4()),
            email=clean_email,
            password_hash=hash_password(password),
            full_name=full_name.strip() if full_name else clean_email.split("@")[0].capitalize(),
            phone=phone,
            status="active",
            email_verified=True,
            platform_role="user",
        )
        db.add(user)
        db.flush()

    # Create Organization Membership
    membership = OrganizationMember(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        user_id=user.id,
        role="organization_owner",
        is_default=True,
        status="active",
    )
    db.add(membership)
    db.commit()

    token = create_access_token(
        user_id=user.id,
        org_id=org.id,
        role="organization_owner",
        email=user.email,
        platform_role=user.platform_role,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "platform_role": user.platform_role,
        },
        "organization": {
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
            "role": "organization_owner",
            "logo_url": org.logo_url,
            "brand_name": org.brand_name or org.name,
        },
    }


# ─────────────────────────────────────────────────────────────
# 5. AUTHENTICATION & LOGIN
# ─────────────────────────────────────────────────────────────

def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> Dict[str, Any]:
    """Authenticate user with email and password.
    Returns user, active organization, available organizations, and access token.
    Supports auto-initializing initial admin password if none set.
    """
    clean_email = email.strip().lower()
    user = db.query(User).filter(User.email == clean_email).first()

    if not user:
        raise ValueError("Invalid email or password.")

    # Check password
    if not user.password_hash:
        # Default seed user fallback: if user has no password set yet, set it to provided password
        user.password_hash = hash_password(password)
        db.commit()
    elif not verify_password(password, user.password_hash):
        raise ValueError("Invalid email or password.")

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    # Find organizations user belongs to
    memberships = (
        db.query(OrganizationMember, Organization)
        .join(Organization, OrganizationMember.organization_id == Organization.id)
        .filter(
            OrganizationMember.user_id == user.id,
            OrganizationMember.status == "active",
            Organization.status == "active",
        )
        .all()
    )

    if not memberships:
        # If platform_super_admin has no org, check if any org exists to attach to
        first_org = db.query(Organization).filter(Organization.status == "active").first()
        if first_org:
            m = OrganizationMember(
                id=str(uuid.uuid4()),
                organization_id=first_org.id,
                user_id=user.id,
                role="organization_owner" if user.platform_role == "platform_super_admin" else "regular_user",
                is_default=True,
                status="active",
            )
            db.add(m)
            db.commit()
            memberships = [(m, first_org)]
        else:
            raise ValueError("Your account is not associated with any active organization.")

    # Determine default or active org
    default_membership, active_org = None, None
    for m, o in memberships:
        if m.is_default:
            default_membership, active_org = m, o
            break

    if not active_org:
        default_membership, active_org = memberships[0]

    if user.platform_role == "platform_super_admin":
        all_active_orgs = db.query(Organization).filter(Organization.status == "active").all()
        user_roles = {m.organization_id: m.role for m, _ in memberships}
        org_list = [
            {
                "id": o.id,
                "name": o.name,
                "slug": o.slug,
                "role": user_roles.get(o.id, "organization_owner"),
                "is_default": (o.id == active_org.id),
                "logo_url": o.logo_url,
                "brand_name": o.brand_name or o.name,
            }
            for o in all_active_orgs
        ]
    else:
        org_list = [
            {
                "id": o.id,
                "name": o.name,
                "slug": o.slug,
                "role": m.role,
                "is_default": bool(m.is_default),
                "logo_url": o.logo_url,
                "brand_name": o.brand_name or o.name,
            }
            for m, o in memberships
        ]

    token = create_access_token(
        user_id=user.id,
        org_id=active_org.id,
        role=default_membership.role,
        email=user.email,
        platform_role=user.platform_role,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "job_title": user.job_title,
            "platform_role": user.platform_role,
        },
        "organization": {
            "id": active_org.id,
            "name": active_org.name,
            "slug": active_org.slug,
            "role": default_membership.role,
            "logo_url": active_org.logo_url,
            "brand_name": active_org.brand_name or active_org.name,
            "settings": active_org.settings or {},
        },
        "organizations": org_list,
    }


def switch_organization(
    db: Session,
    user_id: str,
    target_org_id: str,
) -> Dict[str, Any]:
    """Switch active organization for a user and return a new JWT token."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("User not found.")

    membership = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.user_id == user_id,
            OrganizationMember.organization_id == target_org_id,
            OrganizationMember.status == "active",
        )
        .first()
    )

    if not membership:
        if user.platform_role == "platform_super_admin":
            membership = OrganizationMember(
                id=str(uuid.uuid4()),
                organization_id=target_org_id,
                user_id=user_id,
                role="organization_owner",
                is_default=True,
                status="active",
            )
            db.add(membership)
            db.commit()
        else:
            raise ValueError("User does not have access to this organization.")

    org = db.query(Organization).filter(Organization.id == target_org_id).first()
    if not org or org.status != "active":
        raise ValueError("Target organization is inactive or not found.")

    # Update is_default flags
    db.query(OrganizationMember).filter(OrganizationMember.user_id == user_id).update({"is_default": False})
    membership.is_default = True
    db.commit()

    token = create_access_token(
        user_id=user.id,
        org_id=org.id,
        role=membership.role,
        email=user.email,
        platform_role=user.platform_role,
    )

    return {
        "access_token": token,
        "organization": {
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
            "role": membership.role,
            "logo_url": org.logo_url,
            "brand_name": org.brand_name or org.name,
            "settings": org.settings or {},
        },
    }


# ─────────────────────────────────────────────────────────────
# 6. TEAM MEMBERSHIP & RBAC
# ─────────────────────────────────────────────────────────────

def get_org_members(db: Session, org_id: str) -> List[Dict[str, Any]]:
    """Get all members of an organization with profile and role details."""
    members = (
        db.query(OrganizationMember, User)
        .join(User, OrganizationMember.user_id == User.id)
        .filter(OrganizationMember.organization_id == org_id)
        .order_by(OrganizationMember.created_at.asc())
        .all()
    )

    return [
        {
            "membership_id": m.id,
            "user_id": u.id,
            "email": u.email,
            "full_name": u.full_name or u.email.split("@")[0],
            "role": m.role,
            "status": m.status,
            "joined_at": m.joined_at.isoformat() if m.joined_at else None,
            "invited_by": m.invited_by,
        }
        for m, u in members
    ]


def invite_org_member(
    db: Session,
    org_id: str,
    invited_by_user_id: str,
    email: str,
    role: str = "regular_user",
    full_name: Optional[str] = None,
    temporary_password: Optional[str] = None,
) -> Dict[str, Any]:
    """Invite or add a user to an organization."""
    clean_email = email.strip().lower()

    # Check if user already exists
    user = db.query(User).filter(User.email == clean_email).first()
    if not user:
        # Create user with initial password or random
        default_pwd = temporary_password or "Welcome@2026!"
        user = User(
            id=str(uuid.uuid4()),
            email=clean_email,
            password_hash=hash_password(default_pwd),
            full_name=full_name.strip() if full_name else clean_email.split("@")[0].capitalize(),
            status="active",
            email_verified=True,
            platform_role="user",
        )
        db.add(user)
        db.flush()

    # Check if already member
    existing_member = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user.id,
        )
        .first()
    )

    if existing_member:
        if existing_member.status == "active":
            raise ValueError(f"User '{clean_email}' is already an active member of this organization.")
        else:
            existing_member.status = "active"
            existing_member.role = role
            db.commit()
            return {"status": "reactivated", "member_id": existing_member.id}

    member = OrganizationMember(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        user_id=user.id,
        role=role,
        is_default=False,
        status="active",
        invited_by=invited_by_user_id,
        invited_at=datetime.now(timezone.utc),
    )
    db.add(member)
    db.commit()

    return {
        "status": "invited",
        "member_id": member.id,
        "email": user.email,
        "role": role,
    }


def update_member_role(
    db: Session,
    org_id: str,
    member_user_id: str,
    new_role: str,
) -> bool:
    """Update role for a member in an organization."""
    valid_roles = {"organization_owner", "organization_admin", "campaign_manager", "sales_user", "regular_user", "viewer"}
    if new_role not in valid_roles:
        raise ValueError(f"Invalid role '{new_role}'. Must be one of {valid_roles}")

    member = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == member_user_id,
        )
        .first()
    )
    if not member:
        raise ValueError("Member not found.")

    member.role = new_role
    db.commit()
    return True


def remove_org_member(
    db: Session,
    org_id: str,
    member_user_id: str,
) -> bool:
    """Remove a member from an organization."""
    member = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == member_user_id,
        )
        .first()
    )
    if not member:
        raise ValueError("Member not found.")

    if member.role == "organization_owner":
        # Check if there is at least one other owner
        owner_count = (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.role == "organization_owner",
                OrganizationMember.status == "active",
            )
            .count()
        )
        if owner_count <= 1:
            raise ValueError("Cannot remove the sole Organization Owner. Transfer ownership first.")

    db.delete(member)
    db.commit()
    return True


# ─────────────────────────────────────────────────────────────
# 7. ORGANIZATION SETTINGS & CONFIGURATION
# ─────────────────────────────────────────────────────────────

def get_organization_by_id(db: Session, org_id: str) -> Optional[Organization]:
    """Retrieve organization entity by ID."""
    return db.query(Organization).filter(Organization.id == org_id).first()


def update_organization_settings(
    db: Session,
    org_id: str,
    name: Optional[str] = None,
    brand_name: Optional[str] = None,
    logo_url: Optional[str] = None,
    website: Optional[str] = None,
    brand_colors: Optional[Dict[str, str]] = None,
    ai_config: Optional[Dict[str, Any]] = None,
    sender_config: Optional[Dict[str, Any]] = None,
    booking_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Update organization branding, AI preferences, sender credentials, or booking configuration."""
    org = get_organization_by_id(db, org_id)
    if not org:
        raise ValueError("Organization not found.")

    if name:
        org.name = name.strip()
    if brand_name:
        org.brand_name = brand_name.strip()
    if logo_url is not None:
        org.logo_url = logo_url
    if website is not None:
        org.website = website
    if brand_colors:
        org.brand_colors = brand_colors

    # Update nested settings dictionary cleanly
    current_settings = dict(org.settings or {})

    if ai_config:
        current_ai = current_settings.get("ai", {})
        current_ai.update(ai_config)
        current_settings["ai"] = current_ai

    if sender_config:
        current_sender = current_settings.get("sender", {})
        current_sender.update(sender_config)
        current_settings["sender"] = current_sender

    if booking_config:
        current_booking = current_settings.get("booking", {})
        current_booking.update(booking_config)
        current_settings["booking"] = current_booking

    from sqlalchemy.orm.attributes import flag_modified
    import copy

    org.settings = copy.deepcopy(current_settings)
    flag_modified(org, "settings")
    db.commit()
    db.refresh(org)

    return {
        "id": org.id,
        "name": org.name,
        "brand_name": org.brand_name,
        "logo_url": org.logo_url,
        "website": org.website,
        "settings": org.settings,
    }


# ─────────────────────────────────────────────────────────────
# 8. SUPER ADMIN PLATFORM AUDIT & METRICS
# ─────────────────────────────────────────────────────────────

def get_platform_admin_overview(db: Session) -> Dict[str, Any]:
    """Super Admin high-level system telemetry across all organizations."""
    total_orgs = db.query(Organization).count()
    active_orgs = db.query(Organization).filter(Organization.status == "active").count()
    total_users = db.query(User).count()
    total_leads = db.query(MasterLead).count()
    total_campaign_logs = db.query(CampaignLog).count()
    total_kb_docs = db.query(KnowledgeDocument).count()

    orgs = db.query(Organization).order_by(Organization.created_at.desc()).all()
    org_summaries = []
    for o in orgs:
        lead_count = db.query(MasterLead).filter(MasterLead.organization_id == o.id).count()
        member_count = db.query(OrganizationMember).filter(OrganizationMember.organization_id == o.id).count()
        campaign_count = db.query(CampaignLog).filter(CampaignLog.organization_id == o.id).count()
        org_summaries.append({
            "id": o.id,
            "name": o.name,
            "slug": o.slug,
            "status": o.status,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "member_count": member_count,
            "lead_count": lead_count,
            "campaign_count": campaign_count,
            "is_platform_org": o.is_platform_org,
        })

    return {
        "metrics": {
            "total_organizations": total_orgs,
            "active_organizations": active_orgs,
            "total_users": total_users,
            "total_leads": total_leads,
            "total_campaign_logs": total_campaign_logs,
            "total_kb_docs": total_kb_docs,
        },
        "organizations": org_summaries,
    }


def set_organization_status(db: Session, org_id: str, new_status: str) -> bool:
    """Activate, suspend, or deactivate an organization."""
    valid_statuses = {"active", "suspended", "deactivated"}
    if new_status not in valid_statuses:
        raise ValueError(f"Invalid status '{new_status}'")

    org = get_organization_by_id(db, org_id)
    if not org:
        raise ValueError("Organization not found.")

    org.status = new_status
    db.commit()
    return True
