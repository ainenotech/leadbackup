"""Endpoints for the Email Channels Foundation."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from Backend.db import get_db
from Backend.auth_endpoints import get_current_user_and_tenant
from Backend.channels_models import OrgDomainSnapshot
from services.dns_health import full_dns_check
from pydantic import BaseModel, EmailStr
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import Request
from Backend.auth_models import User, Organization, OrganizationMember, IdentityAccount, LoginTicket
from Backend.auth_service import register_organization_and_user
from datetime import datetime, timezone, timedelta
import json
import urllib.parse
import requests
import os
import hashlib
from services.oauth_service import (
    build_auth_url_and_flow, acquire_token_by_auth_code_flow,
    build_google_auth_url_and_flow, exchange_google_code, decode_google_id_token
)
from Backend.channels_models import OAuthFlowState, OrgMailConnection
from services.secret_store import encrypt_secret

router = APIRouter(prefix="/api/channels", tags=["Email Channels"])


class DetectRequest(BaseModel):
    email: EmailStr


class DetectResponse(BaseModel):
    email: str
    domain: str
    recommendation: str
    is_consumer_mailbox: bool
    dns_health: dict


@router.post("/detect", response_model=DetectResponse)
def detect_channel(
    req: DetectRequest,
    db: Session = Depends(get_db),
    user_data: dict = Depends(get_current_user_and_tenant)
):
    """Detect the recommended channel based on MX records."""
    org_id = user_data.get("org_id")
    if not org_id:
        raise HTTPException(status_code=403, detail="Organization context required")

    # Re-check active membership and owner/admin role in the database.
    from Backend.auth_models import OrganizationMember, User
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org_id,
        OrganizationMember.user_id == user_data["user_id"]
    ).first()
    
    if not membership or membership.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Admin access required")

    domain = req.email.split("@")[1].lower()
    
    # 1. Run DNS health check
    try:
        dns_report = full_dns_check(domain)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resolve DNS for domain {domain}: {str(e)}")

    mx_records = dns_report.mx.records if dns_report.mx else []
    spf_record = dns_report.spf.raw_records[0] if dns_report.spf and dns_report.spf.raw_records else None
    dmarc_record = dns_report.dmarc.raw_record if dns_report.dmarc else None

    
    # 2. Determine recommendation
    recommendation = "unknown, choose manually"
    is_consumer = False
    
    # Check consumer domains
    if domain in ("gmail.com", "outlook.com", "hotmail.com", "yahoo.com"):
        is_consumer = True
        recommendation = "own_domain" if domain in ("yahoo.com",) else ("google_oauth" if domain == "gmail.com" else "microsoft_oauth")
    elif not mx_records:
        recommendation = "own_domain"
    else:
        # Check MX hostnames
        mx_text = " ".join([mx.lower() for mx in mx_records])
        if "google.com" in mx_text or "googlemail.com" in mx_text:
            recommendation = "google_oauth"
        elif "protection.outlook.com" in mx_text:
            recommendation = "microsoft_oauth"
        elif "mimecast.com" in mx_text or "proofpoint.com" in mx_text or "messagelabs.com" in mx_text:
            recommendation = "unknown, choose manually"
        else:
            # any other MX: smtp_imap
            recommendation = "smtp_imap"

    # 3. Save snapshot
    snapshot = OrgDomainSnapshot(
        organization_id=org_id,
        domain=domain,
        results={
            "mx": mx_records,
            "spf": spf_record,
            "dkim_detected": False,
            "dmarc": dmarc_record,
        }
    )
    db.add(snapshot)
    db.commit()

    return DetectResponse(
        email=req.email,
        domain=domain,
        recommendation=recommendation,
        is_consumer_mailbox=is_consumer,
        dns_health={
            "mx": mx_records,
            "spf": spf_record,
            "dmarc": dmarc_record
        }
    )


class StartOAuthRequest(BaseModel):
    email: EmailStr

class StartOAuthResponse(BaseModel):
    auth_url: str

@router.post("/oauth/microsoft/start", response_model=StartOAuthResponse)
def start_microsoft_oauth(
    req: StartOAuthRequest,
    db: Session = Depends(get_db),
    user_data: dict = Depends(get_current_user_and_tenant)
):
    org_id = user_data.get("org_id")
    if not org_id:
        raise HTTPException(status_code=403, detail="Organization context required")

    from Backend.auth_models import OrganizationMember
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org_id,
        OrganizationMember.user_id == user_data["user_id"],
        OrganizationMember.status == "active"
    ).first()
    
    is_super_admin = user_data.get("platform_role") == "platform_super_admin"
    if not is_super_admin and (not membership or membership.role not in ("owner", "admin", "organization_owner", "organization_admin")):
        raise HTTPException(status_code=403, detail="Admin access required")

    scopes = ["User.Read", "Mail.Send", "Mail.Read"]
    redirect_uri = os.getenv("MS_OAUTH_REDIRECT_URI", "http://localhost:8000/api/channels/oauth/microsoft/callback")
    
    try:
        flow = build_auth_url_and_flow(scopes=scopes, redirect_uri=redirect_uri)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to initiate Microsoft OAuth: {exc}")
    
    # MSAL generates a state parameter
    raw_state = flow.get("state")
    if not raw_state:
        raise HTTPException(status_code=500, detail="Failed to generate OAuth state")
        
    state_hash = hashlib.sha256(raw_state.encode("utf-8")).hexdigest()
    
    flow_state = OAuthFlowState(
        state_hash=state_hash,
        provider="microsoft",
        organization_id=org_id,
        user_id=user_data["user_id"],
        expected_email=req.email.lower().strip(),
        flow_data_encrypted=encrypt_secret(flow),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15)
    )
    db.add(flow_state)
    db.commit()
    
    return StartOAuthResponse(auth_url=flow["auth_uri"])



@router.post("/oauth/google/start", response_model=StartOAuthResponse)
def start_google_oauth(
    req: StartOAuthRequest,
    db: Session = Depends(get_db),
    user_data: dict = Depends(get_current_user_and_tenant)
):
    org_id = user_data.get("org_id")
    if not org_id:
        raise HTTPException(status_code=403, detail="Organization context required")

    from Backend.auth_models import OrganizationMember
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org_id,
        OrganizationMember.user_id == user_data["user_id"],
        OrganizationMember.status == "active"
    ).first()
    
    is_super_admin = user_data.get("platform_role") == "platform_super_admin"
    if not is_super_admin and (not membership or membership.role not in ("owner", "admin", "organization_owner", "organization_admin")):
        raise HTTPException(status_code=403, detail="Admin access required")

    scopes = ["openid", "email", "profile", "https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/gmail.readonly"]
    redirect_uri = os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:8000/api/channels/oauth/google/callback")
    
    try:
        flow = build_google_auth_url_and_flow(scopes=scopes, redirect_uri=redirect_uri)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to initiate Google OAuth: {exc}")
    
    raw_state = flow.get("state")
    if not raw_state:
        raise HTTPException(status_code=500, detail="Failed to generate OAuth state")
        
    state_hash = hashlib.sha256(raw_state.encode("utf-8")).hexdigest()
    
    flow_state = OAuthFlowState(
        state_hash=state_hash,
        provider="google",
        organization_id=org_id,
        user_id=user_data["user_id"],
        expected_email=req.email.lower().strip(),
        flow_data_encrypted=encrypt_secret(flow),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15)
    )
    db.add(flow_state)
    db.commit()
    
    return StartOAuthResponse(auth_url=flow["auth_uri"])

def _render_oauth_result(title: str, message: str, is_error: bool = False, admin_consent_url: str = None) -> HTMLResponse:
    import html
    color = "#dc2626" if is_error else "#16a34a"
    title_escaped = html.escape(title)
    msg_escaped = html.escape(message)
    
    admin_html = ""
    if admin_consent_url:
        admin_url_escaped = html.escape(admin_consent_url)
        admin_html = f'''
        <div style="margin-top: 20px; padding: 15px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; text-align: left;">
            <p style="font-size: 14px; font-weight: bold; margin-top: 0;">Send this link to your IT Administrator:</p>
            <textarea readonly style="width: 100%; height: 60px; font-family: monospace; font-size: 12px; padding: 8px; border: 1px solid #cbd5e1; border-radius: 4px;" onclick="this.select()">{admin_url_escaped}</textarea>
        </div>
        '''
        
    html_content = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title_escaped}</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #f1f5f9; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
            .card {{ background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); max-width: 450px; width: 100%; text-align: center; }}
            h2 {{ color: {color}; margin-top: 0; }}
            p {{ color: #475569; font-size: 16px; line-height: 1.5; }}
            .close-btn {{ background-color: #0f172a; color: white; border: none; padding: 10px 20px; border-radius: 6px; font-size: 16px; font-weight: 500; cursor: pointer; margin-top: 20px; }}
            .close-btn:hover {{ background-color: #1e293b; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h2>{title_escaped}</h2>
            <p>{msg_escaped}</p>
            {admin_html}
            <button class="close-btn" onclick="window.close()">Close Tab</button>
        </div>
    </body>
    </html>
    '''
    return HTMLResponse(content=html_content, headers={"Cache-Control": "no-store"})

def _handle_oauth_auth(provider: str, purpose: str, email: str, config: dict, current_user_id: str, db: Session):
    clean_email = email.lower()
    
    if provider == "microsoft":
        oid = config.get("oid")
        tid = config.get("tenant_id")
        if not oid or not tid:
            return _render_oauth_result("Invalid Token", "Microsoft did not return an immutable ID.", True)
        immutable_id = f"{oid}_{tid}"
        email_verified = False
        is_consumer = (tid == "9188040d-6c67-4c5b-b112-36a304b66dad")
    elif provider == "google":
        sub = config.get("sub")
        if not sub:
            return _render_oauth_result("Invalid Token", "Google did not return an immutable ID.", True)
        immutable_id = sub
        email_verified = config.get("email_verified", False)
        is_consumer = not config.get("hd")
    else:
        return _render_oauth_result("Unsupported", "Unsupported provider.", True)
        
    identity = db.query(IdentityAccount).filter(
        IdentityAccount.provider == provider,
        IdentityAccount.provider_user_id == immutable_id
    ).first()
    
    app_url = os.getenv("APP_URL", "http://localhost:8501")
    allow_consumer = os.getenv("AUTH_ALLOW_CONSUMER_ACCOUNTS", "false").lower() == "true"
    
    if purpose == "link":
        if not current_user_id or current_user_id == "login":
            return _render_oauth_result("Not logged in", "You must be logged in to link an account.", True)
            
        user = db.query(User).filter(User.id == current_user_id).first()
        if not user:
            return _render_oauth_result("User Not Found", "Your account could not be found.", True)
            
        if identity:
            if identity.user_id != user.id:
                return _render_oauth_result("Already Linked", f"This {provider.capitalize()} account is already linked to another user.", True)
        else:
            identity = IdentityAccount(
                id=str(uuid.uuid4()),
                user_id=user.id,
                provider=provider,
                provider_user_id=immutable_id,
                provider_email=clean_email
            )
            db.add(identity)
            
        user.last_login_at = datetime.now(timezone.utc)
        db.commit()
        return RedirectResponse(url=f"{app_url}/?linked=true")
        
    elif purpose == "login":
        if identity:
            user = db.query(User).filter(User.id == identity.user_id).first()
            if not user:
                return _render_oauth_result("User Not Found", "Your account could not be found.", True)
        else:
            user = db.query(User).filter(User.email == clean_email).first()
            if user:
                if not user.email_verified and email_verified:
                    pass
                else:
                    return _render_oauth_result("Account Exists", "We couldn't sign you in. If you already have an account, sign in the usual way and link your Microsoft or Google account inside the app.", True)
            else:
                if is_consumer and not allow_consumer:
                    return _render_oauth_result("Work Account Required", f"Personal {provider.capitalize()} accounts are not supported. Please use a work or school account.", True)
                    
                dummy_password = os.urandom(16).hex()
                org_name = clean_email.split("@")[1].split(".")[0].capitalize()
                try:
                    register_organization_and_user(
                        db=db,
                        org_name=f"{org_name} Workspace",
                        admin_email=clean_email,
                        password=dummy_password,
                        full_name=None,
                        industry=None,
                        company_size=None,
                        phone=None,
                        website=None
                    )
                    user = db.query(User).filter(User.email == clean_email).first()
                except Exception as e:
                    db.rollback()
                    return _render_oauth_result("Sign Up Failed", str(e), True)
                    
            if not identity:
                identity = IdentityAccount(
                    id=str(uuid.uuid4()),
                    user_id=user.id,
                    provider=provider,
                    provider_user_id=immutable_id,
                    provider_email=clean_email
                )
                db.add(identity)
                
        ticket_hash = hashlib.sha256(os.urandom(32)).hexdigest()
        ticket = LoginTicket(
            ticket_hash=ticket_hash,
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5)
        )
        db.add(ticket)
        db.commit()
        
        return RedirectResponse(url=f"{app_url}/?login_ticket={ticket_hash}")


@router.get("/oauth/{provider}/callback")
def oauth_callback(provider: str, req: Request, db: Session = Depends(get_db)):
    # Look up state
    raw_state = req.query_params.get("state")
    if not raw_state:
        return _render_oauth_result("Invalid Request", "Missing state parameter in callback.", is_error=True)
        
    state_hash = hashlib.sha256(raw_state.encode("utf-8")).hexdigest()
    
    flow_state = db.query(OAuthFlowState).filter(OAuthFlowState.state_hash == state_hash).first()
    if not flow_state:
        return _render_oauth_result("Invalid Request", "State parameter not found or already used. Please restart the connection process.", is_error=True)
        
    exp = flow_state.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if flow_state.used_at or exp < datetime.now(timezone.utc):
        return _render_oauth_result("Link Expired", "This connection attempt has expired or was already used. Please restart.", is_error=True)
        
    # Mark as used immediately to prevent replay
    flow_state.used_at = datetime.now(timezone.utc)
    db.commit()
    
    purpose = flow_state.expected_email
    
    if purpose not in ("login", "link"):
        # Re-verify user membership is still active owner/admin (allow platform_super_admin)
        from Backend.auth_models import OrganizationMember, User
        user = db.query(User).filter(User.id == flow_state.user_id).first()
        is_super = bool(user and user.platform_role == "platform_super_admin")
        if not is_super:
            membership = db.query(OrganizationMember).filter(
                OrganizationMember.organization_id == flow_state.organization_id,
                OrganizationMember.user_id == flow_state.user_id,
                OrganizationMember.status == "active"
            ).first()
            
            if not membership or membership.role not in ("owner", "admin", "organization_owner", "organization_admin"):
                return _render_oauth_result("Unauthorized", "You are no longer an active administrator for this organization.", is_error=True)

    # Check for OAuth error in callback
    error = req.query_params.get("error")
    error_desc = req.query_params.get("error_description", "").lower()
    
    if error:
        if error == "access_denied" and "cancel" in error_desc:
            return _render_oauth_result("Connection Cancelled", "You cancelled the consent screen. No changes were made.", is_error=True)
        if error == "access_denied" and "admin_consent" in error_desc:
            client_id = os.getenv("MS_OAUTH_CLIENT_ID")
            redirect_uri = os.getenv("MS_OAUTH_REDIRECT_URI", "http://localhost:8000/api/channels/oauth/microsoft/callback")
            admin_url = f"https://login.microsoftonline.com/common/adminconsent?client_id={client_id}&redirect_uri={urllib.parse.quote(redirect_uri)}"
            return _render_oauth_result("Admin Approval Required", "Your organization requires an IT administrator to approve this app before you can connect your mailbox.", is_error=True, admin_consent_url=admin_url)
            
        return _render_oauth_result("Connection Failed", f"{provider.capitalize()} returned an error: {error_desc or error}", is_error=True)

    from services.secret_store import decrypt_secret
    try:
        dec = decrypt_secret(flow_state.flow_data_encrypted)
        if isinstance(dec, dict):
            flow_data = dec
        elif isinstance(dec, str):
            flow_data = json.loads(dec)
        else:
            flow_data = {}
    except Exception as exc:
        return _render_oauth_result("Internal Error", f"Failed to decrypt OAuth flow state: {exc}", is_error=True)
        
    access_token = None
    refresh_token = None
    actual_mail = ""
    config = {}
    
    if provider == "microsoft":
        result = acquire_token_by_auth_code_flow(flow_data, dict(req.query_params))
        if "error" in result:
            err_msg = result.get("error_description") or result.get("error") or "Unknown error"
            return _render_oauth_result("Token Exchange Failed", f"Could not acquire tokens: {err_msg}", is_error=True)
        access_token = result.get("access_token")
        refresh_token = result.get("refresh_token")
        if not access_token or not refresh_token:
            return _render_oauth_result("Token Missing", "Microsoft did not return the expected tokens. Please try again.", is_error=True)
            
        try:
            me_resp = requests.get("https://graph.microsoft.com/v1.0/me", headers={"Authorization": f"Bearer {access_token}"}, timeout=10)
            if me_resp.status_code == 200:
                me_data = me_resp.json()
                actual_mail = me_data.get("mail") or me_data.get("userPrincipalName") or ""
            else:
                actual_mail = result.get("id_token_claims", {}).get("preferred_username", "")
        except Exception:
            actual_mail = result.get("id_token_claims", {}).get("preferred_username", "")
            
        config = {
            "tenant_id": result.get("id_token_claims", {}).get("tid"),
            "scopes": result.get("scope"),
            "oid": result.get("id_token_claims", {}).get("oid")
        }
        
    elif provider == "google":
        code = req.query_params.get("code")
        if not code:
            return _render_oauth_result("Invalid Request", "Google did not return an authorization code.", is_error=True)
            
        try:
            result = exchange_google_code(code, flow_data.get("code_verifier", ""), flow_data.get("redirect_uri", ""))
        except Exception as e:
            return _render_oauth_result("Token Exchange Failed", f"Could not acquire tokens from Google: {str(e)}", is_error=True)
            
        access_token = result.get("access_token")
        refresh_token = result.get("refresh_token")
        id_token = result.get("id_token")
        if not refresh_token:
            return _render_oauth_result("Refresh Token Missing", "Google did not return a refresh token. Please revoke access at https://myaccount.google.com/permissions and retry so Google issues an offline token.", is_error=True)
            
        try:
            id_data = decode_google_id_token(id_token) if id_token else {}
            actual_mail = id_data.get("email", "")
        except Exception:
            actual_mail = ""
            
        config = {
            "scopes": result.get("scope"),
            "sub": id_data.get("sub") if id_token else None
        }
    else:
        return _render_oauth_result("Unsupported Provider", f"Provider {provider} is not supported.", is_error=True)

    if purpose in ("login", "link"):
        return _handle_oauth_auth(provider, purpose, actual_mail, config, flow_state.user_id, db)
        
    actual_clean = (actual_mail or "").strip().lower()
    expected_clean = (flow_state.expected_email or "").strip().lower()
    if actual_clean and expected_clean and actual_clean != expected_clean:
        return _render_oauth_result("Account Mismatch", f"You entered {expected_clean} but signed into {provider.capitalize()} as {actual_clean}. Please sign in with the matching account.", is_error=True)
        
    # Save connection
    existing_conn = db.query(OrgMailConnection).filter(
        OrgMailConnection.organization_id == flow_state.organization_id,
        OrgMailConnection.email == expected_clean
    ).first()
    
    channel_name = f"{provider}_oauth"
    domain = expected_clean.split("@")[1].lower() if "@" in expected_clean else "unknown.com"
    is_personal = domain in ("gmail.com", "outlook.com", "hotmail.com")
    
    if provider == "google":
        daily_cap = 500 if is_personal else 2000
    else:
        daily_cap = int(os.getenv("SENDING_PERSONAL_DAILY_CAP", "50"))
    
    if existing_conn:
        existing_conn.channel = channel_name
        existing_conn.status = "active"
        existing_conn.encrypted_secret = encrypt_secret(refresh_token)
        existing_conn.config = config
    else:
        new_conn = OrgMailConnection(
            organization_id=flow_state.organization_id,
            email=expected_clean,
            domain=domain,
            channel=channel_name,
            status="active",
            encrypted_secret=encrypt_secret(refresh_token),
            config=config,
            daily_cap=daily_cap
        )
        db.add(new_conn)
        
    db.commit()
    
    return _render_oauth_result("Connection Successful", f"Your mailbox ({flow_state.expected_email}) has been securely connected. You can now close this tab and return to the application.")
