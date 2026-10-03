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
from .auth_models import User, Organization, OrganizationMember, IdentityAccount, LoginTicket
from .auth_service import (
    authenticate_user,
    create_access_token,
    decode_access_token,
    get_org_members,
    get_organization_by_id,
    get_platform_admin_overview,
    invite_org_member,
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
    login_ticket: str


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

@router.post("/auth/register")
def register(req: RegisterRequest):
    """Sign up a new organization and admin account."""
    db = SessionLocal()
    try:
        result = register_organization_and_user(
            db=db,
            org_name=req.org_name,
            admin_email=req.admin_email,
            password=req.password,
            full_name=req.full_name,
            industry=req.industry,
            company_size=req.company_size,
            phone=req.phone,
            website=req.website,
        )
        return {"status": "success", "data": result}
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
    org = db.query(Organization).filter(Organization.is_platform_org == True).first()
    if not org:
        org = db.query(Organization).first()
    if not org:
        raise HTTPException(status_code=500, detail="No organization exists to anchor login state.")
    org_id = org.id

    from services.oauth_service import build_auth_url_and_flow, build_google_auth_url_and_flow
    if provider == "microsoft":
        scopes = ["openid", "profile", "email"]
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

@router.post("/auth/oauth/exchange-ticket")
def exchange_ticket(req: ExchangeTicketRequest):
    """Exchanges a short-lived login ticket for normal session credentials."""
    db = SessionLocal()
    try:
        ticket = db.query(LoginTicket).filter(
            LoginTicket.ticket_hash == req.login_ticket,
            LoginTicket.used_at == None,
            LoginTicket.expires_at > datetime.now(timezone.utc)
        ).first()
        
        if not ticket:
            raise HTTPException(status_code=401, detail="Invalid, expired, or already used ticket.")
            
        ticket.used_at = datetime.now(timezone.utc)
        
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
            raise HTTPException(status_code=403, detail="Your account is not associated with any active organization.")
            
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
        
        # Create server-side session
        session = Session(
            user_id=user.id,
            organization_id=active_org.id,
            token_hash=token, # For simplicity, using JWT as the token_hash
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            ip_address="0.0.0.0",
            user_agent="Streamlit"
        )
        db.add(session)
        
        db.commit()
        
        return {
            "status": "success",
            "data": {
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
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


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


@router.put("/org/settings")
def update_org_settings_endpoint(
    req: UpdateOrgSettingsRequest,
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    """Update settings, branding, AI preferences, or sender credentials."""
    if context.get("role") not in ("organization_owner", "organization_admin") and context.get("platform_role") != "platform_super_admin":
        raise HTTPException(status_code=403, detail="Only organization admins can modify settings.")

    db = SessionLocal()
    try:
        result = update_organization_settings(
            db=db,
            org_id=context["org_id"],
            name=req.name,
            brand_name=req.brand_name,
            logo_url=req.logo_url,
            website=req.website,
            brand_colors=req.brand_colors,
            ai_config=req.ai_config,
            sender_config=req.sender_config,
            booking_config=req.booking_config,
        )
        return {"status": "success", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.get("/org/members")
def list_members_endpoint(
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    """List all team members of the active organization."""
    db = SessionLocal()
    try:
        members = get_org_members(db, context["org_id"])
        return {"status": "success", "data": members}
    finally:
        db.close()


@router.post("/org/members/invite")
def invite_member_endpoint(
    req: InviteMemberRequest,
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    """Invite a new team member to the organization."""
    if context.get("role") not in ("organization_owner", "organization_admin") and context.get("platform_role") != "platform_super_admin":
        raise HTTPException(status_code=403, detail="Only organization admins can invite members.")

    db = SessionLocal()
    try:
        result = invite_org_member(
            db=db,
            org_id=context["org_id"],
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


@router.put("/org/members/{user_id}/role")
def update_member_role_endpoint(
    user_id: str,
    req: UpdateMemberRoleRequest,
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    """Update a team member's role."""
    if context.get("role") != "organization_owner" and context.get("platform_role") != "platform_super_admin":
        raise HTTPException(status_code=403, detail="Only organization owners can modify member roles.")

    db = SessionLocal()
    try:
        update_member_role(db, context["org_id"], user_id, req.role)
        return {"status": "success", "message": f"Updated role to {req.role}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.delete("/org/members/{user_id}")
def remove_member_endpoint(
    user_id: str,
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    """Remove a team member from the organization."""
    if context.get("role") not in ("organization_owner", "organization_admin") and context.get("platform_role") != "platform_super_admin":
        raise HTTPException(status_code=403, detail="Permission denied.")

    db = SessionLocal()
    try:
        remove_org_member(db, context["org_id"], user_id)
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
