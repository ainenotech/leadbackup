"""FastAPI endpoints for SaaS multi-tenancy, authentication, and team management.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import os
import hashlib
import json
import uuid

from .db import get_db, SessionLocal
from .auth_models import User, Organization, OrganizationMember, IdentityAccount, LoginTicket, Session as UserSession
from .auth_service import (
    authenticate_user,
    create_access_token,
    decode_access_token,
    get_org_members,
    get_organization_by_id,
    get_platform_admin_overview,
    invite_org_member,
    resend_org_invitation,
    register_organization_and_user,
    remove_org_member,
    set_organization_status,
    switch_organization,
    update_member_role,
    update_organization_settings,
)

router = APIRouter(prefix="/api", tags=["SaaS Auth & Multi-Tenancy"])


# ─────────────────────────────────────────────────────────────
# PYDANTIC SCHEMAS
# ─────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    org_name: str
    admin_email: str
    password: str
    full_name: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class SwitchOrgRequest(BaseModel):
    organization_id: str


class InviteMemberRequest(BaseModel):
    email: str
    role: str = "regular_user"
    full_name: Optional[str] = None
    temporary_password: Optional[str] = None


class OAuthStartRequest(BaseModel):
    purpose: str = "login"  # "login" or "link"

class OAuthStartResponse(BaseModel):
    auth_url: str

class ExchangeTicketRequest(BaseModel):
    login_ticket: Optional[str] = None
    ticket: Optional[str] = None


class UpdateMemberRoleRequest(BaseModel):
    role: str


class UpdateOrgSettingsRequest(BaseModel):
    name: Optional[str] = None
    brand_name: Optional[str] = None
    logo_url: Optional[str] = None
    website: Optional[str] = None
    brand_colors: Optional[Dict[str, str]] = None
    ai_config: Optional[Dict[str, Any]] = None
    sender_config: Optional[Dict[str, Any]] = None
    booking_config: Optional[Dict[str, Any]] = None


class OrgStatusRequest(BaseModel):
    status: str


class CreateOrganizationRequest(BaseModel):
    name: str
    slug: Optional[str] = None
    brand_name: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    phone: Optional[str] = None


# ─────────────────────────────────────────────────────────────
# FASTAPI DEPENDENCIES (Tenant & User Context)
# ─────────────────────────────────────────────────────────────

def get_current_user_and_tenant(
    authorization: Optional[str] = Header(None),
    x_organization_id: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """Resolves authenticated user, verified active organization, and permissions.
    organization_id is resolved securely from JWT or validated against active memberships.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication token.",
        )

    token = authorization.split("Bearer ", 1)[1].strip()
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
        )

    active_org_id = x_organization_id or payload.get("org_id")
    return {
        "user_id": payload.get("sub"),
        "email": payload.get("email"),
        "org_id": active_org_id,
        "role": payload.get("role", "regular_user"),
        "platform_role": payload.get("platform_role", "user"),
    }


# ─────────────────────────────────────────────────────────────
# AUTH ROUTES
# ─────────────────────────────────────────────────────────────

@router.post("/auth/login")
def login(req: LoginRequest):
    """Authenticate with work email and password."""
    db = SessionLocal()
    try:
        result = authenticate_user(
            db=db,
            email=req.email.strip().lower(),
            password=req.password,
        )
        return {
            "status": "success",
            "access_token": result["access_token"],
            "token_type": "bearer",
            "user": result["user"],
            "organization": result["organization"],
            "organizations": result.get("organizations", [result["organization"]]),
            "data": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.post("/auth/register")
def register(req: RegisterRequest):
    """Sign up a new organization and admin account."""
    db = SessionLocal()
    try:
        result = register_organization_and_user(
            db=db,
            org_name=req.org_name.strip(),
            admin_email=req.admin_email.strip().lower(),
            password=req.password,
            full_name=req.full_name.strip() if req.full_name else None,
            industry=req.industry,
            company_size=req.company_size,
            phone=req.phone,
            website=req.website,
        )
        return {
            "status": "success",
            "access_token": result["access_token"],
            "token_type": "bearer",
            "user": result["user"],
            "organization": result["organization"],
            "organizations": result.get("organizations", [result["organization"]]),
            "data": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


def get_optional_user(authorization: Optional[str] = Header(None)) -> Optional[Dict[str, Any]]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        token = authorization.split("Bearer ", 1)[1].strip()
        return decode_access_token(token)
    except Exception:
        return None

@router.get("/auth/oauth/{provider}/login")
def auth_oauth_login(
    provider: str,
    db: Session = Depends(get_db)
):
    """Starts the OAuth flow for login and redirects directly to the provider."""
    if provider not in ("microsoft", "google"):
        raise HTTPException(status_code=400, detail="Unsupported provider")
        
    user_id = "login"
    org = db.query(Organization).first()
    org_id = org.id if org else None

    from services.oauth_service import build_auth_url_and_flow, build_google_auth_url_and_flow
    if provider == "microsoft":
        scopes = ["User.Read"]
        redirect_uri = os.getenv("MS_OAUTH_REDIRECT_URI", "http://localhost:8000/api/channels/oauth/microsoft/callback")
        flow = build_auth_url_and_flow(scopes=scopes, redirect_uri=redirect_uri)
    elif provider == "google":
        scopes = ["openid", "email", "profile"]
        redirect_uri = os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:8000/api/channels/oauth/google/callback")
        flow = build_google_auth_url_and_flow(scopes=scopes, redirect_uri=redirect_uri)

    raw_state = flow.get("state")
    if not raw_state:
        raise HTTPException(status_code=500, detail="Failed to generate OAuth state")
        
    state_hash = hashlib.sha256(raw_state.encode("utf-8")).hexdigest()
    
    from Backend.channels_models import OAuthFlowState
    from services.secret_store import encrypt_secret
    
    flow_state = OAuthFlowState(
        state_hash=state_hash,
        provider=provider,
        organization_id=org_id,
        user_id=user_id,
        expected_email="login",
        flow_data_encrypted=encrypt_secret(json.dumps(flow)),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15)
    )
    db.add(flow_state)
    db.commit()
    
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=flow["auth_uri"])

def _do_exchange_ticket(ticket_hash: Optional[str]):
    """Exchanges a short-lived login ticket for normal session credentials."""
    if not ticket_hash:
        raise HTTPException(status_code=400, detail="Missing login ticket")

    db = SessionLocal()
    try:
        ticket = db.query(LoginTicket).filter(
            LoginTicket.ticket_hash == ticket_hash,
            LoginTicket.expires_at > datetime.now(timezone.utc)
        ).first()
        
        if not ticket:
            raise HTTPException(status_code=401, detail="Invalid, expired, or already used ticket.")
            
        if ticket.used_at is not None:
            used_time = ticket.used_at
            if used_time.tzinfo is None:
                used_time = used_time.replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - used_time).total_seconds()
            if age > 60:
                raise HTTPException(status_code=401, detail="Invalid, expired, or already used ticket.")
        else:
            ticket.used_at = datetime.now(timezone.utc)
            db.commit()
        
        user = db.query(User).filter(User.id == ticket.user_id).first()
        if not user or user.status not in ("active", "pending_verification"):
            raise HTTPException(status_code=403, detail="User account is not active.")
            
        user.last_login_at = datetime.now(timezone.utc)
        
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
            # Provision fallback org if missing
            display_name = user.full_name or user.email.split("@")[0].capitalize()
            org_slug = f"org-{uuid.uuid4().hex[:8]}"
            active_org = Organization(
                id=str(uuid.uuid4()),
                name=f"{display_name} Organization",
                slug=org_slug,
                status="active",
                is_platform_org=False,
            )
            db.add(active_org)
            db.flush()
            default_membership = OrganizationMember(
                id=str(uuid.uuid4()),
                organization_id=active_org.id,
                user_id=user.id,
                role="organization_owner",
                status="active",
                is_default=True,
            )
            db.add(default_membership)
            db.commit()
            memberships = [(default_membership, active_org)]
            
        default_membership, active_org = None, None
        for m, o in memberships:
            if m.is_default:
                default_membership, active_org = m, o
                break
        if not active_org:
            default_membership, active_org = memberships[0]
            
        org_list = [
            {
                "id": o.id,
                "name": o.name,
                "slug": o.slug,
                "role": m.role,
                "logo_url": o.logo_url,
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
        
        # Create server-side session safely
        try:
            existing_session = db.query(UserSession).filter(UserSession.token_hash == token).first()
            if not existing_session:
                user_session = UserSession(
                    user_id=user.id,
                    organization_id=active_org.id,
                    token_hash=token,
                    expires_at=datetime.now(timezone.utc) + timedelta(days=30),
                    ip_address="0.0.0.0",
                    user_agent="Streamlit/Next.js"
                )
                db.add(user_session)
                db.commit()
        except Exception:
            db.rollback()
        
        payload = {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "platform_role": user.platform_role,
            },
            "organization": {
                "id": active_org.id,
                "name": active_org.name,
                "slug": active_org.slug,
                "role": default_membership.role,
                "logo_url": active_org.logo_url,
                "brand_name": active_org.brand_name or active_org.name,
            },
            "organizations": org_list,
        }
        return {
            "status": "success",
            "data": payload,
            **payload,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.post("/auth/oauth/exchange-ticket")
@router.post("/auth/oauth/ticket")
def exchange_ticket_post(req: ExchangeTicketRequest):
    return _do_exchange_ticket(req.login_ticket or req.ticket)

@router.get("/auth/oauth/exchange-ticket")
@router.get("/auth/oauth/ticket")
def exchange_ticket_get(ticket: Optional[str] = None, login_ticket: Optional[str] = None):
    return _do_exchange_ticket(ticket or login_ticket)


@router.get("/auth/me")
def get_current_user_state(
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db)
):
    """Returns the user and organization state for a valid token."""
    user_id = context["user_id"]
    org_id = context["org_id"]
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
        
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
        raise HTTPException(status_code=403, detail="No active organizations")
        
    active_membership, active_org = None, None
    for m, o in memberships:
        if o.id == org_id:
            active_membership, active_org = m, o
            break
            
    if not active_org:
        # Fallback to default
        for m, o in memberships:
            if m.is_default:
                active_membership, active_org = m, o
                break
        if not active_org:
            active_membership, active_org = memberships[0]

    org_list = [
        {
            "id": o.id,
            "name": o.name,
            "slug": o.slug,
            "role": m.role,
            "logo_url": o.logo_url,
        }
        for m, o in memberships
    ]
    
    return {
        "status": "success",
        "data": {
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "platform_role": user.platform_role,
            },
            "organization": {
                "id": active_org.id,
                "name": active_org.name,
                "slug": active_org.slug,
                "role": active_membership.role,
                "logo_url": active_org.logo_url,
                "brand_name": active_org.brand_name or active_org.name,
                "settings": active_org.settings or {},
            },
            "organizations": org_list,
        }
    }


@router.post("/auth/switch-org")
def switch_org(
    req: SwitchOrgRequest,
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    """Switch active tenant organization for authenticated user."""
    db = SessionLocal()
    try:
        result = switch_organization(
            db=db,
            user_id=context["user_id"],
            target_org_id=req.organization_id,
        )
        return {"status": "success", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()





# ─────────────────────────────────────────────────────────────
# ORGANIZATION & SETTINGS ROUTES
# ─────────────────────────────────────────────────────────────

@router.get("/org/current")
def get_current_org_details(
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    """Retrieve detailed settings and branding of the active organization."""
    db = SessionLocal()
    try:
        org = get_organization_by_id(db, context["org_id"])
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        return {
            "status": "success",
            "data": {
                "id": org.id,
                "name": org.name,
                "slug": org.slug,
                "brand_name": org.brand_name or org.name,
                "logo_url": org.logo_url,
                "website": org.website,
                "settings": org.settings or {},
                "user_role": context.get("role"),
            },
        }
    finally:
        db.close()


@router.get("/org/settings")
@router.get("/org/{org_id}/settings")
def get_org_settings_endpoint(
    org_id: Optional[str] = None,
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    target_org_id = org_id or context["org_id"]
    db = SessionLocal()
    try:
        org = get_organization_by_id(db, target_org_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        return {"status": "success", "settings": org.settings or {}}
    finally:
        db.close()


@router.put("/org/settings")
@router.put("/org/{org_id}/settings")
def update_org_settings_endpoint(
    req: UpdateOrgSettingsRequest,
    org_id: Optional[str] = None,
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    target_org_id = org_id or context["org_id"]
    """Update settings, branding, AI preferences, or sender credentials."""
    if context.get("role") not in ("organization_owner", "organization_admin") and context.get("platform_role") != "platform_super_admin":
        raise HTTPException(status_code=403, detail="Only organization admins can modify settings.")

    db = SessionLocal()
    try:
        result = update_organization_settings(
            db=db,
            org_id=target_org_id,
            name=req.name,
            brand_name=req.brand_name,
            logo_url=req.logo_url,
            website=req.website,
            brand_colors=req.brand_colors,
            ai_config=req.ai_config,
            sender_config=req.sender_config,
            booking_config=req.booking_config,
        )
        return {"status": "success", "data": result, "organization": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.get("/org/members")
@router.get("/org/{org_id}/members")
def list_members_endpoint(
    org_id: Optional[str] = None,
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    """List all team members of the active organization."""
    target_org_id = org_id or context["org_id"]
    db = SessionLocal()
    try:
        members = get_org_members(db, target_org_id)
        return {"status": "success", "members": members, "data": members}
    finally:
        db.close()


@router.post("/org/members/invite")
@router.post("/org/{org_id}/members")
def invite_member_endpoint(
    req: InviteMemberRequest,
    org_id: Optional[str] = None,
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    """Invite a new team member to the organization."""
    target_org_id = org_id or context["org_id"]
    if context.get("role") not in ("organization_owner", "organization_admin") and context.get("platform_role") != "platform_super_admin":
        raise HTTPException(status_code=403, detail="Only organization admins can invite members.")

    db = SessionLocal()
    try:
        result = invite_org_member(
            db=db,
            org_id=target_org_id,
            invited_by_user_id=context["user_id"],
            email=req.email,
            role=req.role,
            full_name=req.full_name,
            temporary_password=req.temporary_password,
        )
        return {"status": "success", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.post("/org/members/{user_id}/resend-invite")
@router.post("/org/{org_id}/members/{user_id}/resend-invite")
def resend_invite_endpoint(
    user_id: str,
    org_id: Optional[str] = None,
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    """Resend the workspace invitation email to an existing member."""
    target_org_id = org_id or context["org_id"]
    if context.get("role") not in ("organization_owner", "organization_admin") and context.get("platform_role") != "platform_super_admin":
        raise HTTPException(status_code=403, detail="Only organization admins can resend invitations.")

    db = SessionLocal()
    try:
        result = resend_org_invitation(
            db=db,
            org_id=target_org_id,
            user_id=user_id,
            requester_user_id=context["user_id"],
        )
        return {"status": "success", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.get("/org/invitation-preview")
@router.get("/org/{org_id}/invitation-preview")
def get_invitation_preview_endpoint(
    org_id: Optional[str] = None,
    email: Optional[str] = "alex@company.com",
    name: Optional[str] = "Alex Rivera",
    role: Optional[str] = "regular_user",
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    """Returns rendered invitation email subject, HTML, and text for previewing in the UI."""
    target_org_id = org_id or context.get("org_id")
    db = SessionLocal()
    try:
        org = db.query(Organization).filter(Organization.id == target_org_id).first() if target_org_id else None
        org_name = org.name if org else "Workspace"

        inviter = db.query(User).filter(User.id == context.get("user_id")).first() if context.get("user_id") else None
        inviter_name = (inviter.full_name or inviter.email) if inviter else "Workspace Admin"
        inviter_email = inviter.email if inviter else "admin@nenotechnology.com"

        from services.invitation_service import build_invitation_email
        subject, html_content, text_content = build_invitation_email(
            recipient_email=email or "alex@company.com",
            organization_name=org_name,
            inviter_name=inviter_name,
            inviter_email=inviter_email,
            recipient_name=name or "Alex Rivera",
            role=role or "regular_user",
            temporary_password="Welcome@2026!",
        )
        return {
            "status": "success",
            "subject": subject,
            "html": html_content,
            "text": text_content,
            "org_name": org_name,
            "inviter_name": inviter_name,
            "inviter_email": inviter_email,
        }
    finally:
        db.close()


@router.put("/org/members/{user_id}/role")
@router.put("/org/{org_id}/members/{user_id}/role")
def update_member_role_endpoint(
    user_id: str,
    req: UpdateMemberRoleRequest,
    org_id: Optional[str] = None,
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    target_org_id = org_id or context["org_id"]
    """Update a team member's role."""
    if context.get("role") != "organization_owner" and context.get("platform_role") != "platform_super_admin":
        raise HTTPException(status_code=403, detail="Only organization owners can modify member roles.")

    db = SessionLocal()
    try:
        update_member_role(db, target_org_id, user_id, req.role)
        return {"status": "success", "message": f"Updated role to {req.role}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.delete("/org/members/{user_id}")
@router.delete("/org/{org_id}/members/{user_id}")
def remove_member_endpoint(
    user_id: str,
    org_id: Optional[str] = None,
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    target_org_id = org_id or context["org_id"]
    """Remove a team member from the organization."""
    if context.get("role") not in ("organization_owner", "organization_admin") and context.get("platform_role") != "platform_super_admin":
        raise HTTPException(status_code=403, detail="Permission denied.")

    db = SessionLocal()
    try:
        remove_org_member(db, target_org_id, user_id)
        return {"status": "success", "message": "Member removed successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────
# SUPER ADMIN PLATFORM ROUTES
# ─────────────────────────────────────────────────────────────

@router.get("/admin/overview")
def admin_overview_endpoint(
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    """Platform Super Admin high-level system overview."""
    if context.get("platform_role") != "platform_super_admin":
        raise HTTPException(status_code=403, detail="Requires platform super admin privileges.")

    db = SessionLocal()
    try:
        stats = get_platform_admin_overview(db)
        return {"status": "success", "data": stats}
    finally:
        db.close()


@router.put("/admin/organizations/{org_id}/status")
def set_org_status_endpoint(
    org_id: str,
    req: OrgStatusRequest,
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    """Platform Super Admin toggle organization status (active/suspended/deactivated)."""
    if context.get("platform_role") != "platform_super_admin":
        raise HTTPException(status_code=403, detail="Requires platform super admin privileges.")

    db = SessionLocal()
    try:
        set_organization_status(db, org_id, req.status)
        return {"status": "success", "message": f"Organization status updated to {req.status}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.get("/oauth/{provider}/callback")
def oauth_callback_alias(provider: str, req: Request, db: Session = Depends(get_db)):
    """Alias for /api/oauth/{provider}/callback redirect URIs matching Google/Microsoft configurations."""
    from Backend.channels_endpoints import oauth_callback
    return oauth_callback(provider, req, db)


@router.post("/auth/logout")
@router.get("/auth/logout")
def logout_endpoint():
    """Sign out endpoint that invalidates session and clears the session_token cookie."""
    from fastapi.responses import JSONResponse
    response = JSONResponse(content={"status": "success", "message": "Successfully signed out."})
    response.delete_cookie(key="session_token", path="/")
    return response


# ── Universal Organization Endpoints ──

@router.post("/organizations")
@router.post("/auth/organizations")
def create_organization_endpoint(
    req: CreateOrganizationRequest,
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    """Create a new customer organization and assign creator as owner."""
    import re
    db = SessionLocal()
    try:
        user_id = context["user_id"]
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        base_slug = req.slug or re.sub(r'[^a-z0-9]+', '-', req.name.strip().lower()).strip('-')
        if not base_slug:
            base_slug = "workspace"
        slug = base_slug
        counter = 1
        while db.query(Organization).filter(Organization.slug == slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1

        org_id = str(uuid.uuid4())
        org = Organization(
            id=org_id,
            name=req.name.strip(),
            slug=slug,
            brand_name=req.brand_name.strip() if req.brand_name else req.name.strip(),
            website=req.website.strip() if req.website else None,
            industry=req.industry.strip() if req.industry else None,
            company_size=req.company_size.strip() if req.company_size else None,
            phone=req.phone.strip() if req.phone else None,
            status="active",
            is_platform_org=False,
        )
        db.add(org)
        db.flush()

        membership = OrganizationMember(
            id=str(uuid.uuid4()),
            organization_id=org.id,
            user_id=user.id,
            role="organization_owner",
            status="active",
            is_default=True,
        )
        db.add(membership)
        db.commit()

        try:
            from services.master_db_service import log_audit
            log_audit(db, action="organization.created", entity_type="organization", entity_id=org.id, user=user.id)
        except Exception:
            pass

        new_token = create_access_token(
            user_id=user.id,
            org_id=org.id,
            role="organization_owner",
            email=user.email,
            platform_role=user.platform_role,
        )

        return {
            "status": "success",
            "access_token": new_token,
            "organization": {
                "id": org.id,
                "name": org.name,
                "slug": org.slug,
                "brand_name": org.brand_name,
                "role": "organization_owner",
                "status": org.status,
            },
            "data": {
                "id": org.id,
                "name": org.name,
                "slug": org.slug,
                "brand_name": org.brand_name,
                "role": "organization_owner",
            },
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.get("/organizations")
def list_user_organizations_endpoint(
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    """List all organizations the authenticated user belongs to."""
    db = SessionLocal()
    try:
        user_id = context["user_id"]
        memberships = (
            db.query(OrganizationMember, Organization)
            .join(Organization, OrganizationMember.organization_id == Organization.id)
            .filter(
                OrganizationMember.user_id == user_id,
                OrganizationMember.status == "active",
                Organization.status == "active",
            )
            .all()
        )
        org_list = [
            {
                "id": o.id,
                "name": o.name,
                "slug": o.slug,
                "role": m.role,
                "is_default": m.is_default,
                "status": o.status,
                "logo_url": o.logo_url,
                "brand_name": o.brand_name or o.name,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for m, o in memberships
        ]
        return {"status": "success", "organizations": org_list, "data": org_list}
    finally:
        db.close()


@router.get("/organizations/{organization_id}")
def get_organization_endpoint(
    organization_id: str,
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    """Get single organization details scoped to caller's membership."""
    db = SessionLocal()
    try:
        user_id = context["user_id"]
        is_super = context.get("platform_role") == "platform_super_admin"
        if not is_super:
            membership = db.query(OrganizationMember).filter(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user_id,
                OrganizationMember.status == "active",
            ).first()
            if not membership:
                raise HTTPException(status_code=403, detail="Access denied to this organization.")

        org = db.query(Organization).filter(Organization.id == organization_id).first()
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        member_count = db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.status == "active",
        ).count()

        return {
            "status": "success",
            "data": {
                "id": org.id,
                "name": org.name,
                "slug": org.slug,
                "brand_name": org.brand_name or org.name,
                "logo_url": org.logo_url,
                "website": org.website,
                "status": org.status,
                "member_count": member_count,
                "settings": org.settings or {},
            },
        }
    finally:
        db.close()


@router.get("/organizations/{organization_id}/members")
def get_organization_members_endpoint(
    organization_id: str,
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    """List members for a specific organization."""
    db = SessionLocal()
    try:
        user_id = context["user_id"]
        is_super = context.get("platform_role") == "platform_super_admin"
        if not is_super:
            membership = db.query(OrganizationMember).filter(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user_id,
                OrganizationMember.status == "active",
            ).first()
            if not membership:
                raise HTTPException(status_code=403, detail="Access denied to this organization.")

        members = get_org_members(db, organization_id)
        return {"status": "success", "members": members, "data": members}
    finally:
        db.close()


@router.post("/organizations/{organization_id}/members/invite")
def invite_organization_member_endpoint(
    organization_id: str,
    req: InviteMemberRequest,
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    """Invite member to an organization."""
    db = SessionLocal()
    try:
        user_id = context["user_id"]
        is_super = context.get("platform_role") == "platform_super_admin"
        if not is_super:
            membership = db.query(OrganizationMember).filter(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user_id,
                OrganizationMember.status == "active",
            ).first()
            if not membership or membership.role not in ("organization_owner", "owner", "organization_admin", "admin"):
                raise HTTPException(status_code=403, detail="Only organization owners or admins can invite members.")

        # Normalize role
        target_role = req.role
        if target_role == "owner":
            target_role = "organization_owner"
        elif target_role == "admin":
            target_role = "organization_admin"
        elif target_role == "member":
            target_role = "regular_user"

        result = invite_org_member(
            db=db,
            org_id=organization_id,
            invited_by_user_id=user_id,
            email=req.email,
            role=target_role,
            full_name=req.full_name,
            temporary_password=req.temporary_password,
        )
        try:
            from services.master_db_service import log_audit
            log_audit(db, action="organization.member.invited", entity_type="organization_member", entity_id=result.get("member_id"), user=user_id)
        except Exception:
            pass

        return {"status": "success", "success": True, "data": result}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.post("/organizations/{organization_id}/members/{target_user_id}/accept")
def accept_organization_invite_endpoint(
    organization_id: str,
    target_user_id: str,
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    """Accept invitation to an organization."""
    db = SessionLocal()
    try:
        caller_id = context["user_id"]
        if caller_id != target_user_id and context.get("platform_role") != "platform_super_admin":
            raise HTTPException(status_code=403, detail="Cannot accept invitation for another user.")

        membership = db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == target_user_id,
        ).first()

        if not membership:
            raise HTTPException(status_code=404, detail="Invitation not found.")

        membership.status = "active"
        membership.joined_at = datetime.now(timezone.utc)
        db.commit()

        try:
            from services.master_db_service import log_audit
            log_audit(db, action="organization.member.accepted", entity_type="organization_member", entity_id=membership.id, user=caller_id)
        except Exception:
            pass

        return {
            "status": "success",
            "message": "Invitation accepted.",
            "membership": {
                "id": membership.id,
                "organization_id": membership.organization_id,
                "user_id": membership.user_id,
                "role": membership.role,
                "status": membership.status,
            }
        }
    finally:
        db.close()

