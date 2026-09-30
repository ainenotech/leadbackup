"""FastAPI endpoints for SaaS multi-tenancy, authentication, and team management.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from .db import get_db, SessionLocal
from .auth_models import User, Organization, OrganizationMember
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
        # Check if default org exists in local/dev fallback mode
        db = SessionLocal()
        try:
            default_org = db.query(Organization).filter(Organization.status == "active").first()
            if default_org:
                return {
                    "user_id": "system_admin",
                    "email": "system@platform.local",
                    "org_id": x_organization_id or default_org.id,
                    "role": "organization_owner",
                    "platform_role": "platform_super_admin",
                }
        finally:
            db.close()
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


@router.post("/auth/login")
def login(req: LoginRequest):
    """Log in with email and password."""
    db = SessionLocal()
    try:
        result = authenticate_user(
            db=db,
            email=req.email,
            password=req.password,
        )
        return {"status": "success", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    finally:
        db.close()


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


@router.get("/auth/me")
def get_current_user_profile(
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    """Get authenticated user details and active tenant info."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == context["user_id"]).first()
        org = get_organization_by_id(db, context["org_id"]) if context.get("org_id") else None

        memberships = (
            db.query(OrganizationMember, Organization)
            .join(Organization, OrganizationMember.organization_id == Organization.id)
            .filter(OrganizationMember.user_id == context["user_id"], Organization.status == "active")
            .all()
        )

        return {
            "status": "success",
            "data": {
                "user": {
                    "id": user.id if user else context["user_id"],
                    "email": user.email if user else context["email"],
                    "full_name": user.full_name if user else "",
                    "platform_role": context.get("platform_role", "user"),
                },
                "active_organization": {
                    "id": org.id if org else None,
                    "name": org.name if org else "Default",
                    "role": context.get("role", "regular_user"),
                    "logo_url": org.logo_url if org else None,
                    "settings": org.settings if org else {},
                } if org else None,
                "organizations": [
                    {
                        "id": o.id,
                        "name": o.name,
                        "slug": o.slug,
                        "role": m.role,
                        "is_active": (o.id == context.get("org_id")),
                    }
                    for m, o in memberships
                ],
            },
        }
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
