import utils.dns_patch  # Fast fallback DNS resolver for Microsoft Graph & login APIs
import base64
import html
import time
from datetime import datetime
import json as _json
import os
import re
from typing import Any, Dict, List, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from functools import lru_cache

@lru_cache(maxsize=16)
def get_image_base64(image_path: str) -> str:
    if os.path.exists(image_path):
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    return ""

load_dotenv(override=True)

import utils.microsoft_auth
import Email.outlook_mailer
import Email
import Backend.crud
import Email.draft_options

# Ensure in-memory module constants reflect the updated .env immediately across Streamlit reruns
_current_sender = os.getenv("MS_SENDER_EMAIL", "mohit@nenotechnology.us")
utils.microsoft_auth.MS_SENDER_EMAIL = _current_sender
Email.outlook_mailer.MS_SENDER_EMAIL = _current_sender
if hasattr(Email, "config"):
    Email.config.MS_SENDER_EMAIL = _current_sender

# Automatically sanitize any stale session state holding the legacy support address
if "active_workspace_sender" in st.session_state and st.session_state.active_workspace_sender == "support@nenotechnology.com":
    st.session_state.active_workspace_sender = _current_sender
if "active_sender_email" in st.session_state and st.session_state.active_sender_email == "support@nenotechnology.com":
    st.session_state.active_sender_email = _current_sender
if "current_org" in st.session_state and isinstance(st.session_state.current_org, dict):
    _s = st.session_state.current_org.get("settings", {})
    if _s and _s.get("sender_email") == "support@nenotechnology.com":
        _s["sender_email"] = _current_sender
        if "sender" in _s and isinstance(_s["sender"], dict):
            _s["sender"]["sender_email"] = _current_sender
            _s["sender"]["sender_name"] = "Mohit Patel"

# Module constants synchronized

from Agent.agents.composer import compose_email
from Backend.crud import (
    approve_and_send_entry,
    bulk_approve_and_send_entries,
    bulk_reject_entries,
    create_pending_entry,
    get_already_drafted_emails,
    get_already_sent_emails,
    is_email_already_sent,
    mark_form_filled,
    reject_entry,
    update_draft_content,
)
from Backend.db import Base, SessionLocal, engine, init_db
from Backend.models import CampaignLog
from sqlalchemy import func, or_
from Email import get_mailer
from Email.draft_options import get_draft_template_option, OPTIONS_METADATA

from leads import (
    DEFAULT_LEADS_FILE,
    append_or_update_leads_dataset,
    detect_lead_status_in_dataframe,
    update_lead_sheet_status,
)
from services.excel_logger import (
    DEFAULT_BOOKED_EXCEL,
    DEFAULT_REPLIES_EXCEL,
    log_form_submission_to_excel,
)
from utils.text_cleaner import extract_text_from_ai_message
from utils.token import generate_token
import services.analytics_service
import services.analytics_export
import reply_worker
from reply_worker import ReplyDaemonManager, check_and_reply_inbox
from services.rag import (
    get_knowledge_base_summary,
    ingest_file_content,
    delete_document,
    retrieve_relevant_chunks,
    list_documents,
)
from Agent.reply_agent import process_incoming_reply
import services.template_service
from services.template_service import load_all_templates, render_template

from analytics_view import render_analytics
from template_hub_view import render_template_hub
from knowledge_base_view import render_knowledge_base_hub
from master_db_view import render_master_db, _render_tab_leads_directory
from auth_view import render_auth_page, render_org_switcher
from org_settings_view import render_org_settings, render_email_channels_chooser
from team_view import render_team_view
from super_admin_view import render_super_admin_portal
from Backend.auth_models import Organization, User, OrganizationMember
from Backend.auth_service import authenticate_user
import utils.theme
from utils.theme import (
    get_current_theme,
    is_dark_mode,
    set_theme,
    apply_chart_theme,
    get_complete_theme_css,
)

@st.cache_resource(show_spinner=False)
def ensure_database_ready() -> bool:
    init_db()
    return True

st.set_page_config(
    page_title="AINeotechnology | Lead Outreach & Intelligence",
    layout="wide",
    page_icon="⚡",
    initial_sidebar_state="expanded",
)

ensure_database_ready()

# Permanent Light Mode enforced
set_theme("light")

# Starting the Outlook monitor during dashboard boot makes page loads wait on
# network-heavy work. Keep it opt-in; the Replies page still has a start button.
if os.getenv("AUTO_START_REPLY_DAEMON", "").lower() in {"1", "true", "yes"}:
    if not ReplyDaemonManager.is_running():
        ReplyDaemonManager.start(interval_seconds=30)

# Keep Render backend warm and awake while the dashboard is running
try:
    from Backend.keepalive import RenderKeepAliveDaemon
    if not RenderKeepAliveDaemon.is_running():
        RenderKeepAliveDaemon.start(interval_minutes=5)
except Exception:
    pass

# Auto-expand sidebar if it was collapsed from a previous session
if "sidebar_checked" not in st.session_state:
    st.session_state.sidebar_checked = True
    st.html(
        """
        <script>
        function expandIfCollapsed() {
            try {
                const doc = window.parent.document;
                if (!doc) return;
                const btn = doc.querySelector('[data-testid="stExpandSidebarButton"]');
                if (btn) {
                    btn.click();
                }
            } catch(e) {}
        }
        setTimeout(expandIfCollapsed, 200);
        setTimeout(expandIfCollapsed, 600);
        </script>
        """,
        unsafe_allow_javascript=True,
    )

# ─────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────
# MASTER DUAL THEME SYSTEM (Dark & Light Mode Dynamic CSS)
# ─────────────────────────────────────────────────────────────
st.markdown(get_complete_theme_css(is_dark_mode()), unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# MULTI-TENANT SAAS AUTHENTICATION & WORKSPACE STATE
# ─────────────────────────────────────────────────────────────
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.session_state.authenticated = False

    # Try restoring session from cookie
    session_token = st.context.cookies.get("session_token")
    if session_token:
        # Fast path: instant local token decode (zero network lag)
        try:
            from Backend.auth_service import decode_access_token
            payload = decode_access_token(session_token)
            if payload:
                user_id = payload.get("sub")
                org_id = payload.get("org_id")
                db_auth = SessionLocal()
                try:
                    user_obj = db_auth.query(User).filter(User.id == user_id).first()
                    if user_obj:
                        memberships = (
                            db_auth.query(OrganizationMember, Organization)
                            .join(Organization, OrganizationMember.organization_id == Organization.id)
                            .filter(OrganizationMember.user_id == user_obj.id, Organization.status == "active")
                            .all()
                        )
                        org_obj = None
                        active_role = payload.get("role", "regular_user")
                        for m, o in memberships:
                            if o.id == org_id:
                                org_obj = o
                                active_role = m.role
                                break
                        if not org_obj and memberships:
                            active_m, org_obj = memberships[0]
                            org_id = org_obj.id
                            active_role = active_m.role

                        if org_obj:
                            st.session_state.authenticated = True
                            st.session_state.user = {
                                "id": user_obj.id,
                                "email": user_obj.email,
                                "full_name": user_obj.full_name,
                                "platform_role": user_obj.platform_role,
                            }
                            st.session_state.current_org = {
                                "id": org_obj.id,
                                "name": org_obj.name,
                                "slug": org_obj.slug,
                                "role": active_role,
                                "logo_url": org_obj.logo_url,
                                "brand_name": org_obj.brand_name or org_obj.name,
                                "settings": org_obj.settings or {},
                            }
                            st.session_state.current_org_id = org_id
                            st.session_state.user_organizations = [
                                {
                                    "id": o.id,
                                    "name": o.name,
                                    "slug": o.slug,
                                    "role": m.role,
                                    "is_default": bool(m.is_default),
                                }
                                for m, o in memberships
                            ]
                            st.session_state.access_token = session_token
                            st.session_state.active_sender_email = user_obj.email
                finally:
                    db_auth.close()
        except Exception:
            pass

        # Network fallback if local decode didn't succeed
        if not st.session_state.get("authenticated"):
            import requests
            try:
                resp = requests.get(
                    "http://localhost:8000/api/auth/me",
                    headers={"Authorization": f"Bearer {session_token}"},
                    timeout=2,
                )
                if resp.status_code == 200:
                    res = resp.json()["data"]
                    st.session_state.authenticated = True
                    st.session_state.user = res["user"]
                    st.session_state.current_org = res.get("organization") or res.get("active_organization", {})
                    st.session_state.current_org_id = st.session_state.current_org.get("id")
                    st.session_state.user_organizations = res.get("organizations", [])
                    st.session_state.access_token = session_token
                    st.session_state.active_sender_email = res["user"]["email"]
            except Exception:
                pass

if not st.session_state.get("authenticated"):
    render_auth_page()
    st.stop()

if not st.session_state.get("onboarding_checked"):
    st.session_state.onboarding_checked = True
    st.session_state.show_onboarding = False

if st.session_state.get("show_onboarding", False):
    st.markdown("## Welcome to AINeotechnology!")
    st.markdown("Before you start sending outreach, let's configure your email channel.")
    render_email_channels_chooser(st.session_state.current_org_id, context="onboarding")
    if st.button("Continue to Dashboard", key="btn_skip_onboarding"):
        st.session_state.show_onboarding = False
        st.rerun()
    st.stop()


def sync_sender_env(sender_email: str):
    """Synchronizes in-memory and environment sender constants across all mail modules."""
    os.environ["MS_SENDER_EMAIL"] = sender_email
    utils.microsoft_auth.MS_SENDER_EMAIL = sender_email
    Email.outlook_mailer.MS_SENDER_EMAIL = sender_email
    if hasattr(Email, "config"):
        Email.config.MS_SENDER_EMAIL = sender_email


def get_active_outreach_sender() -> str:
    """Dynamically resolves outbound sender mailbox from workspace sender selection, current organization settings, or authenticated user."""
    curr_org = st.session_state.get("current_org", {})
    org_settings = curr_org.get("settings", {})
    org_sender = (
        org_settings.get("sender_email")
        or org_settings.get("sender", {}).get("sender_email")
    )
    ws_sender = st.session_state.get("active_workspace_sender")
    if ws_sender == "support@nenotechnology.com":
        ws_sender = org_sender or os.getenv("MS_SENDER_EMAIL", "mohit@nenotechnology.us")
        st.session_state.active_workspace_sender = ws_sender
        st.session_state.active_sender_email = ws_sender

    if ws_sender:
        sync_sender_env(ws_sender)
        return ws_sender

    user_email = st.session_state.get("user", {}).get("email")
    if user_email == "support@nenotechnology.com":
        user_email = "mohit@nenotechnology.us"

    sender = org_sender or user_email or os.getenv("MS_SENDER_EMAIL", "mohit@nenotechnology.us")
    sync_sender_env(sender)
    return sender


def render_sender_selector(campaign_name: str = "unknown") -> str:
    """Renders active outbound mailbox indicator / selector for outreach dialogs and returns active sender."""
    active_blast_sender = get_active_outreach_sender()
    curr_org = st.session_state.get("current_org", {})
    org_name = curr_org.get("name", "Organization") if isinstance(curr_org, dict) else "Organization"
    st.markdown(
        f"""
        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px 14px; margin-bottom: 12px; font-size: 13px; color: #334155;">
            ✉️ <strong>Campaign Outbound Mailbox:</strong> <code style="color: #2563EB; font-weight: 600;">{active_blast_sender}</code> ({org_name})
        </div>
        """,
        unsafe_allow_html=True,
    )
    return active_blast_sender



# ─────────────────────────────────────────────────────────────
# DATA LOADER
# ─────────────────────────────────────────────────────────────
CAMPAIGN_LOG_COLUMNS = [
    "id",
    "campaign",
    "lead_id",
    "email",
    "name",
    "company",
    "phone",
    "status",
    "subject",
    "body",
    "email_sent_at",
    "send_error",
    "opened",
    "open_count",
    "first_open_at",
    "last_open_at",
    "clicked_link",
    "click_count",
    "first_click_at",
    "last_click_at",
    "clicked_urls",
    "unsubscribed",
    "unsubscribed_at",
    "bounced",
    "bounce_reason",
    "engagement_score",
    "form_filled_at",
    "submitted_availability",
    "note",
    "reply_body",
    "reply_intent",
    "reply_received_at",
    "ai_reply_sent",
    "ai_reply_sent_at",
    "proposed_slot",
    "confirmed_slot",
    "meet_link",
    "booking_status",
    "token",
    "tracking_link",
    "template_id",
    "template_name",
    "created_at",
]


@st.cache_data(ttl=60, show_spinner=False)
def fetch_cached_kb_summary(organization_id: Optional[str] = None) -> dict:
    db = SessionLocal()
    try:
        return get_knowledge_base_summary(db, organization_id=organization_id)
    except Exception:
        return {"total_chunks": 0, "total_documents": 0, "documents": []}
    finally:
        db.close()


@st.cache_data(ttl=15, show_spinner=False)
def _load_cached_excel_file(file_path: str, mtime: float) -> pd.DataFrame:
    if os.path.exists(file_path):
        try:
            return pd.read_excel(file_path)
        except Exception:
            pass
    return pd.DataFrame()


def get_cached_excel_df(file_path: str) -> pd.DataFrame:
    """Fast in-memory cached Excel reader. Automatically invalidates when file mtime changes."""
    mtime = os.path.getmtime(file_path) if os.path.exists(file_path) else 0.0
    return _load_cached_excel_file(file_path, mtime)


@st.cache_data(ttl=60, show_spinner=False)
def load_campaign_logs(organization_id: Optional[str] = None) -> pd.DataFrame:
    db = SessionLocal()
    try:
        q = db.query(CampaignLog)
        if organization_id:
            q = q.filter(or_(CampaignLog.organization_id == organization_id, CampaignLog.organization_id.is_(None)))
        rows = q.order_by(CampaignLog.created_at.desc()).all()
        if not rows:
            return pd.DataFrame(columns=CAMPAIGN_LOG_COLUMNS)
        data = [
            {
                "id": r.id,
                "campaign": r.campaign_name,
                "lead_id": r.lead_id,
                "email": r.email,
                "name": r.name,
                "company": r.company,
                "phone": getattr(r, "phone", "") or "",
                "status": r.status or "pending",
                "subject": r.subject or "",
                "body": r.body or "",
                "email_sent_at": r.email_sent_at,
                "send_error": r.send_error or "",
                "opened": bool(getattr(r, "opened", False)),
                "open_count": getattr(r, "open_count", 0) or 0,
                "first_open_at": getattr(r, "first_open_at", None),
                "last_open_at": getattr(r, "last_open_at", None),
                "clicked_link": bool(getattr(r, "clicked_link", False)),
                "click_count": getattr(r, "click_count", 0) or 0,
                "first_click_at": getattr(r, "first_click_at", None),
                "last_click_at": getattr(r, "last_click_at", None),
                "clicked_urls": getattr(r, "clicked_urls", "") or "",
                "unsubscribed": bool(getattr(r, "unsubscribed", False)),
                "unsubscribed_at": getattr(r, "unsubscribed_at", None),
                "bounced": bool(getattr(r, "bounced", False)),
                "bounce_reason": getattr(r, "bounce_reason", "") or "",
                "engagement_score": getattr(r, "engagement_score", 0.0) or 0.0,
                "form_filled_at": r.form_filled_at,
                "submitted_availability": r.submitted_availability or "",
                "note": r.note or "",
                "reply_body": r.reply_body or "",
                "reply_intent": r.reply_intent or "",
                "reply_received_at": r.reply_received_at,
                "ai_reply_sent": r.ai_reply_sent or "",
                "ai_reply_sent_at": r.ai_reply_sent_at,
                "proposed_slot": r.proposed_slot or "",
                "confirmed_slot": r.confirmed_slot or "",
                "meet_link": r.meet_link or "",
                "booking_status": r.booking_status or "",
                "token": r.token or "",
                "tracking_link": r.tracking_link or "",
                "template_id": getattr(r, "template_id", "") or "",
                "template_name": getattr(r, "template_name", "") or "",
                "created_at": r.created_at,
            }
            for r in rows
        ]
        return pd.DataFrame(data, columns=CAMPAIGN_LOG_COLUMNS)
    finally:
        db.close()


@st.cache_data(ttl=120, show_spinner=False)
def sync_external_sources_once() -> dict:
    db = SessionLocal()
    try:
        from Backend.crud import sync_excel_and_outlook_to_db

        return sync_excel_and_outlook_to_db(db)
    except Exception as e:
        print(f"Sync note: {e}")
        return {"synced_bookings": 0, "synced_replies": 0}
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────
# SIDEBAR NAVIGATION
# ─────────────────────────────────────────────────────────────
# Core Campaign Pipeline Navigation
NAV_ITEMS = {
    "overview": {"icon": "📊", "label": "Pipeline Overview"},
    "master_db": {"icon": "🗄️", "label": "MasterDB"},
    "analytics": {"icon": "📈", "label": "Analytics"},
    "templates": {"icon": "📑", "label": "Template Review & Hub"},
    "upload": {"icon": "📤", "label": "Upload & Draft"},
    "leads": {"icon": "📋", "label": "Leads Directory"},
    "email": {"icon": "✉️", "label": "Email Review Studio"},
    "replies": {"icon": "💬", "label": "Replies & Bookings"},
    "knowledge_base": {"icon": "📚", "label": "Knowledge Base Hub"},
}

# Dedicated Workspace Management Pages (Integrated under Active Organization)
WORKSPACE_NAV_ITEMS = {
    "org_settings": {"icon": "⚙️", "label": "Workspace Settings"},
    "team": {"icon": "👥", "label": "Team Members"},
}

ALL_PAGES = set(NAV_ITEMS.keys()) | set(WORKSPACE_NAV_ITEMS.keys())
if st.session_state.get("user", {}).get("platform_role") == "platform_super_admin":
    ALL_PAGES.add("super_admin")

if "page" in st.query_params and st.query_params["page"] in ALL_PAGES:
    st.session_state.active_page = st.query_params["page"]

if "tab" in st.query_params:
    st.session_state.analytics_tab = st.query_params["tab"]

if "feature" in st.query_params:
    st.session_state.analytics_focused_feature = st.query_params["feature"]

if "active_page" not in st.session_state or st.session_state.active_page not in ALL_PAGES:
    st.session_state.active_page = "overview"


@st.dialog("⚠️ Confirm Complete Data Reset")
def confirm_reset_dialog():
    st.markdown(
        """
        <div style="background: #FEF2F2; border: 1px solid #FECACA; border-radius: 8px; padding: 12px 14px; margin-bottom: 14px;">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                <span style="font-size: 18px;">⚠️</span>
                <strong style="color: #991B1B; font-size: 14px;">Irreversible Action: Reset All Data to Zero</strong>
            </div>
            <p style="color: #7F1D1D; font-size: 12.5px; margin: 0; line-height: 1.45;">
                This will permanently erase all uploaded leads, generated email drafts, tracking logs, inbound replies, customer bookings, and analytics back to an empty slate (0 records).
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<p style='font-size: 13px; color: #334155; font-weight: 500;'>Are you sure you want to proceed with resetting all data to zero?</p>", unsafe_allow_html=True)

    col_confirm, col_cancel = st.columns(2)
    with col_confirm:
        if st.button("🔴 Yes, Reset All Data", type="primary", use_container_width=True, key="dlg_confirm_reset_action"):
            with st.spinner("Resetting PostgreSQL and clearing caches..."):
                from Backend.crud import reset_all_system_data
                reset_all_system_data()
                st.cache_data.clear()
                fetch_cached_kb_summary.clear()
                for k in list(st.session_state.keys()):
                    if k.startswith("_pdf_") or k.startswith("_excel_") or k == "campaign_data_version":
                        del st.session_state[k]
            st.toast("✅ All data has been successfully reset to zero in PostgreSQL and Excel!", icon="🗑️")
            st.rerun()
    with col_cancel:
        if st.button("Cancel", type="secondary", use_container_width=True, key="dlg_cancel_reset_action"):
            st.rerun()


with st.sidebar:
    curr_theme = "light"
    logo_name = "logo-dark.png"
    logo_file = os.path.join(os.path.dirname(__file__), logo_name)
    logo_b64 = get_image_base64(logo_file)

    curr_org = st.session_state.get("current_org", {})
    curr_org_name = curr_org.get("name", "Neno Technology")
    is_neno = "neno" in curr_org_name.lower()

    if is_neno and logo_b64:
        logo_img_tag = f'<img src="data:image/png;base64,{logo_b64}" alt="{curr_org_name}" class="sidebar-brand-logo-img" />'
    elif "super" in curr_org_name.lower() or "ai" in curr_org_name.lower():
        logo_img_tag = f'<div style="display:flex; align-items:center; gap:8px;"><span style="font-size:22px;">🤖</span><span style="color:#0F172A; font-weight:800; font-size:16px; letter-spacing:-0.02em;">{curr_org_name}</span></div>'
    else:
        logo_img_tag = f'<div style="display:flex; align-items:center; gap:8px;"><span style="font-size:20px;">🏢</span><span style="color:#0F172A; font-weight:800; font-size:16px; letter-spacing:-0.02em;">{curr_org_name}</span></div>'

    st.markdown(
        f"""
        <div class="sidebar-brand-card">
            <div class="sidebar-brand-logo-wrapper">
                {logo_img_tag}
            </div>
            <div class="sidebar-brand-subtitle">
                <span class="sidebar-brand-dot"></span>
                <span>Lead Intelligence &amp; Outreach</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Platform Super Admin Portal Link (Restricted to Super Admins) ──
    user_email = st.session_state.get("user", {}).get("email", "").lower().strip()
    is_platform_admin = (
        st.session_state.get("user", {}).get("platform_role") == "platform_super_admin"
        and user_email in ["support@nenotechnology.com", "mohit@nenotechnology.us"]
    )
    if is_platform_admin:
        is_admin_active = st.session_state.active_page == "super_admin"
        if st.button(
            "👑  Super Admin",
            key="top_admin_super_portal",
            type="primary" if is_admin_active else "secondary",
            use_container_width=True,
            help="Global SaaS Operations, Cross-Tenant Telemetry & Workspace Controls",
        ):
            st.session_state.active_page = "super_admin"
            st.query_params["page"] = "super_admin"
            if "tab" in st.query_params:
                del st.query_params["tab"]
            if "feature" in st.query_params:
                del st.query_params["feature"]
            st.rerun()
        st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)

    render_org_switcher()

    st.markdown("<hr style='border: none; border-top: 1px solid #E2E8F0; margin: 12px 0 10px 0;'>", unsafe_allow_html=True)
    st.markdown("<div style='font-family: \"JetBrains Mono\", monospace; font-size: 10.5px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.06em; margin: 4px 0 8px 6px;'>Pipeline Navigation</div>", unsafe_allow_html=True)

    for key, nav in NAV_ITEMS.items():
        btn_type = "primary" if st.session_state.active_page == key else "secondary"
        if st.button(
            f"{nav['icon']}  {nav['label']}",
            key=f"nav_{key}",
            type=btn_type,
            use_container_width=True,
        ):
            st.session_state.active_page = key
            st.query_params["page"] = key
            if key != "analytics":
                if "tab" in st.query_params:
                    del st.query_params["tab"]
                if "feature" in st.query_params:
                    del st.query_params["feature"]
            st.rerun()

    st.markdown("<hr style='border: none; border-top: 1px solid #E2E8F0; margin: 12px 0 10px 0;'>", unsafe_allow_html=True)
    st.markdown("""<div style='font-family: "JetBrains Mono", monospace; font-size: 10.5px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.06em; margin: 4px 0 8px 6px;'>Workspace Management</div>""", unsafe_allow_html=True)

    for key, nav in WORKSPACE_NAV_ITEMS.items():
        btn_type = "primary" if st.session_state.active_page == key else "secondary"
        if st.button(
            f"{nav['icon']}  {nav['label']}",
            key=f"nav_{key}",
            type=btn_type,
            use_container_width=True,
        ):
            st.session_state.active_page = key
            st.query_params["page"] = key
            if "tab" in st.query_params:
                del st.query_params["tab"]
            if "feature" in st.query_params:
                del st.query_params["feature"]
            st.rerun()

    st.markdown("<hr style='border: none; border-top: 1px solid #E2E8F0; margin: 16px 0 12px 0;'>", unsafe_allow_html=True)

    # ── Live System Health & Render Keep-Alive in Sidebar ──
    api_endpoint = os.getenv("API_BASE_URL", "http://localhost:8000").replace("https://", "").replace("http://", "").split("/")[0] or "localhost:8000"
    st.markdown(
        f"""
        <div class="sidebar-health-card">
            <div class="sidebar-health-title">
                <span>System Health</span>
                <span class="health-pill health-pill-green">● All Systems Go</span>
            </div>
            <div class="sidebar-health-row">
                <span>API Endpoint</span>
                <strong style="color: #2563EB; font-size: 11px;">{api_endpoint}</strong>
            </div>
            <div class="sidebar-health-row">
                <span>Render Keep-Alive</span>
                <span style="font-size: 11px; color: #059669; font-weight: 600;">● Active (24/7)</span>
            </div>
            <div class="sidebar-health-row">
                <span>AI Engine</span>
                <span style="font-size: 11px; color: #475569;">Gemini 2.5 Flash</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Real-Time Live Sync Controller ──
    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
    sync_cols = st.columns([6, 4])
    with sync_cols[0]:
        st.caption("⚡ **Live Sync Speed**")
    with sync_cols[1]:
        if st.button("🔄 Sync", key="sync_now_sidebar_btn", use_container_width=True, help="Force immediate data refresh"):
            load_campaign_logs.clear()
            st.rerun()

    live_intervals = [
        "⚡ Real-Time (5s)",
        "🚀 Fast (15s)",
        "⏱️ Standard (30s)",
        "🕐 1 Min",
        "⏸️ Paused",
    ]
    if "live_sync_choice" not in st.session_state:
        st.session_state.live_sync_choice = "⏱️ Standard (30s)"

    selected_sync = st.selectbox(
        "Live Sync Interval",
        options=live_intervals,
        index=live_intervals.index(st.session_state.live_sync_choice),
        key="sync_interval_select",
        label_visibility="collapsed",
    )
    if selected_sync != st.session_state.live_sync_choice:
        st.session_state.live_sync_choice = selected_sync
        st.rerun()

    with st.expander("📡 Render 24/7 Keep-Alive", expanded=False):
        st.caption("Pings your Render backend public URL to prevent 15-minute idle spin-down.")
        if st.button("⚡ Ping Render Now", use_container_width=True, key="ping_render_btn"):
            try:
                from Backend.keepalive import RenderKeepAliveDaemon
                res = RenderKeepAliveDaemon.ping_now()
                if res.get("success"):
                    st.success(f"Render awake! HTTP {res.get('status_code')} ({res.get('latency_ms')}ms)")
                else:
                    st.warning(f"Ping result: {res.get('error', 'Unknown')}")
            except Exception as pe:
                st.error(f"Keepalive error: {pe}")

    with st.expander("🗑️ Reset / Zero All Data", expanded=False):
        st.caption("Erase all uploaded leads, drafts, logs, replies, and bookings to test fresh with 0 records.")
        if st.button("⚠️ Reset All Data to Zero", type="secondary", use_container_width=True, key="reset_all_data_btn"):
            confirm_reset_dialog()

    # User Profile & Sign Out
    st.markdown("<hr style='border: none; border-top: 1px solid #E2E8F0; margin: 14px 0 10px 0;'>", unsafe_allow_html=True)
    user_info = st.session_state.get("user", {})
    user_role = st.session_state.get("current_org", {}).get("role", "regular_user")
    role_disp = {
        "organization_owner": "👑 Owner",
        "organization_admin": "🛡️ Admin",
        "campaign_manager": "🚀 Campaign Mgr",
        "sales_user": "💼 Sales User",
        "regular_user": "👤 Member",
        "viewer": "👁️ Viewer",
    }.get(user_role, "👤 Member")

    st.markdown(
        f"""
        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px 12px; margin-bottom: 8px;">
            <div style="font-weight: 700; font-size: 13px; color: #0F172A;">{user_info.get('full_name') or 'User'}</div>
            <div style="font-size: 11px; color: #64748B;">{user_info.get('email')}</div>
            <div style="margin-top: 4px;"><span style="background: #EDE9FE; color: #7C3AED; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px;">{role_disp}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("🚪 Sign Out", key="sb_btn_logout", type="secondary", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user = None
        st.session_state.current_org = None
        st.session_state.current_org_id = None
        st.rerun()



# ─────────────────────────────────────────────────────────────
# HELPER: TOP EXECUTIVE BANNER
# ─────────────────────────────────────────────────────────────
def render_top_banner(title: str, subtitle: str, badge_text: str = None):
    st.markdown(
        f"""
        <div class="top-header-banner">
            <div>
                <h1 class="top-header-title">
                    {title}
                    {f'<span class="badge badge-pending" style="font-size: 11px; font-weight: 600;">{badge_text}</span>' if badge_text else ''}
                </h1>
                <p class="top-header-desc">{subtitle}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_live_activity_stream(df: pd.DataFrame) -> None:
    """Renders a real-time chronological lead interaction activity stream."""
    if df.empty:
        return

    from datetime import timezone
    now = datetime.now(timezone.utc)

    def _relative_str(dt):
        if not dt or pd.isna(dt):
            return ""
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
            except Exception:
                return str(dt)[:16]
        if hasattr(dt, "tzinfo") and dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        try:
            secs = max(0, int((now - dt).total_seconds()))
            if secs < 60:
                return f"{secs}s ago"
            mins = secs // 60
            if mins < 60:
                return f"{mins}m ago"
            hours = mins // 60
            if hours < 24:
                return f"{hours}h ago"
            return f"{hours // 24}d ago"
        except Exception:
            return ""

    events = []
    # Fast vectorized pre-filter: only process rows with active telemetry events (< 20 rows instead of 1,130)
    has_activity = (
        (df["opened"] == True)
        | (df["clicked_link"] == True)
        | df["reply_received_at"].notna()
        | df["form_filled_at"].notna()
        | df["booking_status"].astype(str).str.lower().isin(["confirmed", "scheduled", "booked"])
    )
    active_df = df[has_activity] if not df.empty else df

    for _, r in active_df.iterrows():
        name = str(r.get("name") or "Lead")
        email = str(r.get("email") or "")
        company = str(r.get("company") or "")

        # Open event
        if r.get("opened") and pd.notna(r.get("last_open_at")):
            t = r.get("last_open_at")
            events.append({
                "badge": "👁️ Opened",
                "badge_style": "background: #E0F2FE; color: #0369A1; border: 1px solid #BAE6FD;",
                "name": name,
                "email": email,
                "company": company,
                "detail": f"Viewed email {int(r.get('open_count') or 1)}x",
                "time_obj": t,
                "relative_time": _relative_str(t),
            })
        # Click event
        if r.get("clicked_link") and pd.notna(r.get("last_click_at")):
            t = r.get("last_click_at")
            events.append({
                "badge": "🔗 Clicked Link",
                "badge_style": "background: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE;",
                "name": name,
                "email": email,
                "company": company,
                "detail": f"Clicked tracking link ({int(r.get('click_count') or 1)} clicks)",
                "time_obj": t,
                "relative_time": _relative_str(t),
            })
        # Reply event
        if pd.notna(r.get("reply_received_at")):
            t = r.get("reply_received_at")
            intent = str(r.get("reply_intent") or "Inquiry")
            events.append({
                "badge": "💬 Customer Reply",
                "badge_style": "background: #F3E8FF; color: #6D28D9; border: 1px solid #DDD6FE;",
                "name": name,
                "email": email,
                "company": company,
                "detail": f"Intent: {intent}",
                "time_obj": t,
                "relative_time": _relative_str(t),
            })
        # Booking event
        if pd.notna(r.get("form_filled_at")) or str(r.get("booking_status") or "").lower() in ("confirmed", "scheduled", "booked"):
            t = r.get("form_filled_at") or r.get("created_at")
            slot = str(r.get("confirmed_slot") or "Consultation Scheduled")
            events.append({
                "badge": "📅 Meeting Booked",
                "badge_style": "background: #ECFDF5; color: #047857; border: 1px solid #A7F3D0;",
                "name": name,
                "email": email,
                "company": company,
                "detail": slot[:40],
                "time_obj": t,
                "relative_time": _relative_str(t),
            })

    def _safe_sort_key(item):
        val = item.get("time_obj")
        if val is None or pd.isna(val):
            return ""
        return str(val)

    events.sort(key=_safe_sort_key, reverse=True)
    recent_events = events[:6]

    sync_choice = st.session_state.get("live_sync_choice", "⏱️ Standard (30s)")

    if recent_events:
        cards_html = ""
        for ev in recent_events:
            company_pill = f'<span style="background: #F1F5F9; color: #475569; font-size: 11px; padding: 2px 6px; border-radius: 4px; margin-left: 6px;">{html.escape(ev["company"])}</span>' if ev["company"] else ""
            cards_html += f"""
            <div style="background: white; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px 14px; margin-bottom: 8px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 1px 2px rgba(0,0,0,0.03);">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 9999px; {ev['badge_style']}">{ev['badge']}</span>
                    <strong style="font-size: 13px; color: #0F172A;">{html.escape(ev['name'])}</strong>
                    <span style="font-size: 12px; color: #64748B;">({html.escape(ev['email'])})</span>
                    {company_pill}
                </div>
                <div style="display: flex; align-items: center; gap: 12px;">
                    <span style="font-size: 12px; color: #475569; font-weight: 500;">{html.escape(ev['detail'])}</span>
                    <span style="font-size: 11px; color: #94A3B8; background: #F8FAFC; padding: 2px 6px; border-radius: 4px; border: 1px solid #E2E8F0;">⏱️ {ev['relative_time']}</span>
                </div>
            </div>
            """

        st.markdown(
            f"""
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px; padding: 16px; margin: 18px 0;">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #10B981; box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.2);"></span>
                        <strong style="font-size: 14px; color: #0F172A; font-weight: 700;">⚡ Real-Time Activity Feed</strong>
                        <span style="font-size: 11px; color: #64748B;">({len(events)} live telemetry events recorded)</span>
                    </div>
                    <div style="font-size: 11px; color: #059669; font-weight: 600; background: #ECFDF5; padding: 3px 8px; border-radius: 9999px; border: 1px solid #A7F3D0;">
                        ● Live Sync: {sync_choice}
                    </div>
                </div>
                {cards_html}
            </div>
            """,
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────
# PAGE 1: OVERVIEW
# ─────────────────────────────────────────────────────────────
def render_overview(df: pd.DataFrame) -> None:
    render_top_banner(
        "Executive Pipeline Overview",
        "Real-time visibility into lead outreach, email performance, customer replies, and consultation bookings.",
        "Live Campaign",
    )

    valid_df = df[~df["status"].astype(str).str.lower().isin(["rejected", "cancelled", "failed"])].copy() if not df.empty else pd.DataFrame()

    if valid_df.empty:
        total_leads = 0
        drafted_leads = 0
        sent_leads = 0
        replied_leads = 0
        forms_filled = 0
        scheduled_leads = 0
        draft_pct = 0
        sent_pct = 0
        reply_pct = 0
        form_pct = 0
        booked_pct = 0
    else:
        # Calculate funnel metrics by UNIQUE lead (email), ensuring multi-template touches to one user do not double count
        clean_email = valid_df["email"].astype(str).str.strip().str.lower()
        valid_df["clean_email"] = clean_email
        valid_has_email = valid_df[valid_df["clean_email"] != ""]

        total_leads = valid_has_email["clean_email"].nunique() if not valid_has_email.empty else len(valid_df)
        sent_leads = valid_has_email[valid_has_email["status"].isin(["sent", "replied", "bounced", "delivered", "meeting_scheduled"])]["clean_email"].nunique()
        drafted_leads = valid_has_email[valid_has_email["status"].isin(["drafted", "pending", "draft"])]["clean_email"].nunique()
        clean_rep_mask = valid_has_email["reply_received_at"].notna() & ~valid_has_email["reply_received_at"].astype(str).str.lower().isin(["nan", "none", "nat", ""])
        replied_leads = valid_has_email[(valid_has_email["status"] == "replied") | clean_rep_mask]["clean_email"].nunique()
        clean_form_mask = valid_has_email["form_filled_at"].notna() & ~valid_has_email["form_filled_at"].astype(str).str.lower().isin(["nan", "none", "nat", ""])
        forms_filled = valid_has_email[clean_form_mask]["clean_email"].nunique()
        scheduled_leads = valid_has_email[valid_has_email["booking_status"].isin(["scheduled", "meeting_scheduled", "confirmation_sent", "confirmed"])]["clean_email"].nunique()

        draft_pct = round((drafted_leads / total_leads * 100) if total_leads else 0)
        sent_pct = round((sent_leads / total_leads * 100) if total_leads else 0)
        reply_pct = round((replied_leads / sent_leads * 100) if sent_leads else 0, 1)
        form_pct = round((forms_filled / total_leads * 100) if total_leads else 0, 1)
        booked_pct = round((scheduled_leads / forms_filled * 100) if forms_filled else (round(scheduled_leads / total_leads * 100) if total_leads else 0), 1)

    # ── 6 Custom Rich KPI Cards (Unified Grid with Pixel-Perfect Gaps) ──
    st.markdown(
        f"""
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-top-bar kpi-bar-blue"></div>
                <div class="kpi-header">
                    <span class="kpi-label">Total Leads</span>
                    <div class="kpi-icon-box" style="background: #EFF6FF; color: #2563EB;">👥</div>
                </div>
                <div class="kpi-value">{total_leads}</div>
                <div class="kpi-micro">
                    <span class="kpi-pill kpi-pill-blue">100% active</span>
                    <span>in current campaign</span>
                </div>
            </div>
            <div class="kpi-card">
                <div class="kpi-top-bar kpi-bar-amber"></div>
                <div class="kpi-header">
                    <span class="kpi-label">Drafts (In Review)</span>
                    <div class="kpi-icon-box" style="background: #FFFBEB; color: #D97706;">✍️</div>
                </div>
                <div class="kpi-value">{drafted_leads}</div>
                <div class="kpi-micro">
                    <span class="kpi-pill kpi-pill-amber">{draft_pct}%</span>
                    <span>pending human approval</span>
                </div>
            </div>
            <div class="kpi-card">
                <div class="kpi-top-bar kpi-bar-teal"></div>
                <div class="kpi-header">
                    <span class="kpi-label">Emails Dispatched</span>
                    <div class="kpi-icon-box" style="background: #F0FDFA; color: #0D9488;">🚀</div>
                </div>
                <div class="kpi-value">{sent_leads}</div>
                <div class="kpi-micro">
                    <span class="kpi-pill kpi-pill-teal">{sent_pct}%</span>
                    <span>outreach delivered</span>
                </div>
            </div>
            <div class="kpi-card">
                <div class="kpi-top-bar kpi-bar-cyan"></div>
                <div class="kpi-header">
                    <span class="kpi-label">Customer Replies</span>
                    <div class="kpi-icon-box" style="background: #ECFEFF; color: #0891B2;">💬</div>
                </div>
                <div class="kpi-value">{replied_leads}</div>
                <div class="kpi-micro">
                    <span class="kpi-pill kpi-pill-cyan">{reply_pct}%</span>
                    <span>response rate</span>
                </div>
            </div>
            <div class="kpi-card">
                <div class="kpi-top-bar kpi-bar-purple"></div>
                <div class="kpi-header">
                    <span class="kpi-label">Forms Completed</span>
                    <div class="kpi-icon-box" style="background: #F5F3FF; color: #7C3AED;">📋</div>
                </div>
                <div class="kpi-value">{forms_filled}</div>
                <div class="kpi-micro">
                    <span class="kpi-pill kpi-pill-purple">{form_pct}%</span>
                    <span>converted from outreach</span>
                </div>
            </div>
            <div class="kpi-card">
                <div class="kpi-top-bar kpi-bar-rose"></div>
                <div class="kpi-header">
                    <span class="kpi-label">Meetings Booked</span>
                    <div class="kpi-icon-box" style="background: #FFF1F2; color: #E11D48;">🗓️</div>
                </div>
                <div class="kpi-value">{scheduled_leads}</div>
                <div class="kpi-micro">
                    <span class="kpi-pill kpi-pill-rose">{booked_pct}%</span>
                    <span>confirmed in calendar</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Visual Pipeline Conversion Funnel ──
    overall_win_rate = round(scheduled_leads / total_leads * 100 if total_leads else 0, 1)
    st.markdown(
        f"""
        <div class="funnel-container">
            <div class="funnel-header">
                <div class="funnel-title"><span>📈</span> Lead Outreach &amp; Conversion Funnel</div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span class="badge badge-pending">Live Progression</span>
                    <span class="badge badge-sent">Overall Win Rate: {overall_win_rate}%</span>
                </div>
            </div>
            <div class="funnel-stages">
                <div class="funnel-stage">
                    <div class="funnel-stage-name">1. Total Leads</div>
                    <div class="funnel-stage-val" style="color: #2563EB;">{total_leads}</div>
                    <div class="funnel-stage-sub">100% Base</div>
                </div>
                <div class="funnel-stage">
                    <div class="funnel-stage-name">2. Drafted</div>
                    <div class="funnel-stage-val" style="color: #D97706;">{drafted_leads}</div>
                    <div class="funnel-stage-sub">{draft_pct}% Pipeline</div>
                </div>
                <div class="funnel-stage">
                    <div class="funnel-stage-name">3. Sent</div>
                    <div class="funnel-stage-val" style="color: #0D9488;">{sent_leads}</div>
                    <div class="funnel-stage-sub">{sent_pct}% Dispatched</div>
                </div>
                <div class="funnel-stage">
                    <div class="funnel-stage-name">4. Replied</div>
                    <div class="funnel-stage-val" style="color: #0891B2;">{replied_leads}</div>
                    <div class="funnel-stage-sub">{reply_pct}% Replied</div>
                </div>
                <div class="funnel-stage">
                    <div class="funnel-stage-name">5. Form Filled</div>
                    <div class="funnel-stage-val" style="color: #7C3AED;">{forms_filled}</div>
                    <div class="funnel-stage-sub">{form_pct}% Converted</div>
                </div>
                <div class="funnel-stage">
                    <div class="funnel-stage-name">6. Confirmed</div>
                    <div class="funnel-stage-val" style="color: #E11D48;">{scheduled_leads}</div>
                    <div class="funnel-stage-sub">{booked_pct}% Booked</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if df.empty:
        st.info("💡 **Pipeline is clean with 0 records.** Real-time sync is active: any consultation bookings arriving in **Excel** (`booked_leads.xlsx` via your Bookings $\\to$ Excel $\\to$ Odoo CRM flow) and customer replies in **Outlook** will automatically populate the Dashboard & Analytics. You can also upload a lead spreadsheet in the **Upload & Draft** tab to start outreach.")
        return

    # ── Real-Time Live Activity Stream ──
    render_live_activity_stream(df)

    # ── Interactive Modern Charts Section ──
    col_c1, col_c2 = st.columns([7, 5], gap="large")

    with col_c1:
        with st.container(border=True):
            st.markdown(
                """
                <div class="chart-header">
                    <div class="chart-title-group">
                        <h3><span>📊</span> Conversion Velocity &amp; Stage Volume</h3>
                        <p>Interactive funnel tracking lead progression and drop-off rate</p>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            stages = ["1. Total Leads", "2. Drafted", "3. Sent", "4. Replied", "5. Form Filled", "6. Confirmed"]
            volumes = [total_leads, drafted_leads, sent_leads, replied_leads, forms_filled, scheduled_leads]
            conv_rates = ["100%", f"{draft_pct}%", f"{sent_pct}%", f"{reply_pct}%", f"{form_pct}%", f"{booked_pct}%"]
            colors = ["#2563EB", "#F59E0B", "#0D9488", "#0891B2", "#7C3AED", "#E11D48"]

            fig_funnel = go.Figure()
            fig_funnel.add_trace(
                go.Bar(
                    x=stages,
                    y=volumes,
                    name="Lead Volume",
                    marker_color=colors,
                    marker_line_width=0,
                    text=volumes,
                    textposition="outside",
                    textfont=dict(family="Inter", size=12, color="#18181B"),
                    customdata=conv_rates,
                    hovertemplate="<b>%{x}</b><br>Volume: <b>%{y} leads</b><br>Conversion: <b>%{customdata}</b><extra></extra>",
                )
            )
            fig_funnel.add_trace(
                go.Scatter(
                    x=stages,
                    y=volumes,
                    name="Funnel Trend",
                    mode="lines+markers",
                    line=dict(color="#0D9488", width=2.5, shape="spline"),
                    marker=dict(size=8, color="#FFFFFF", line=dict(color="#0D9488", width=2)),
                    hoverinfo="skip",
                )
            )

            fig_funnel.update_layout(
                template="plotly_white",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=10, r=10, t=25, b=25),
                height=300,
                showlegend=False,
                xaxis=dict(
                    showgrid=False,
                    tickfont=dict(family="Inter", size=11, color="#71717A"),
                ),
                yaxis=dict(
                    showgrid=True,
                    gridcolor="#F4F4F5",
                    tickfont=dict(family="JetBrains Mono", size=10.5, color="#71717A"),
                ),
            )
            apply_chart_theme(fig_funnel)
            st.plotly_chart(fig_funnel, use_container_width=True, config={"displayModeBar": False})

    with col_c2:
        with st.container(border=True):
            st.markdown(
                """
                <div class="chart-header">
                    <div class="chart-title-group">
                        <h3><span>🍩</span> Pipeline Engagement Breakdown</h3>
                        <p>Current distribution of active campaign contacts</p>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            donut_labels = ["Outreach Delivered", "Customer Replies", "Forms Completed", "Pending Review"]
            donut_vals = [max(0, sent_leads - replied_leads), replied_leads, forms_filled, drafted_leads]
            donut_colors = ["#0D9488", "#0891B2", "#7C3AED", "#F59E0B"]

            fig_donut = go.Figure(
                data=[
                    go.Pie(
                        labels=donut_labels,
                        values=donut_vals,
                        hole=0.68,
                        marker=dict(colors=donut_colors, line=dict(color="#FFFFFF", width=2)),
                        textinfo="percent",
                        textfont=dict(family="Inter", size=11, color="#FFFFFF"),
                        hovertemplate="<b>%{label}</b><br>Count: <b>%{value}</b><br>Share: <b>%{percent}</b><extra></extra>",
                    )
                ]
            )

            fig_donut.update_layout(
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.28,
                    xanchor="center",
                    x=0.5,
                    font=dict(family="Inter", size=11, color="#52525B"),
                ),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=10, r=10, t=10, b=30),
                height=300,
                annotations=[
                    dict(
                        text=f"<b>{total_leads}</b><br><span style='font-size:10px; color:#71717A; font-family:JetBrains Mono;'>TOTAL LEADS</span>",
                        x=0.5,
                        y=0.5,
                        font_size=24,
                        font_family="Inter",
                        showarrow=False,
                    )
                ],
            )
            apply_chart_theme(fig_donut)
            st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar": False})

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    # ── Two-Column Breakdown: Status Breakdown & Recent Activity ──
    col_status, col_activity = st.columns([5, 7], gap="large")

    with col_status:
        with st.container(border=True):
            st.markdown(
                """
                <div style="margin-bottom: 12px;">
                    <h4 style="font-family: 'Newsreader', Georgia, serif; font-size: 17px; margin: 0; color: #18181B;">📋 Pipeline Efficiency Metrics</h4>
                    <p style="font-family: 'Inter', sans-serif; font-size: 12px; color: #71717A; margin: 2px 0 0 0;">Conversion benchmarks and response velocities</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            status_counts = valid_df["status"].value_counts().reset_index()
            status_counts.columns = ["Status", "Count"]
            st.dataframe(
                status_counts,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Status": st.column_config.TextColumn("Lead Stage"),
                    "Count": st.column_config.ProgressColumn(
                        "Leads Volume",
                        format="%d",
                        min_value=0,
                        max_value=max(1, total_leads),
                    ),
                },
            )

    with col_activity:
        with st.container(border=True):
            st.markdown(
                """
                <div style="margin-bottom: 12px;">
                    <h4 style="font-family: 'Newsreader', Georgia, serif; font-size: 17px; margin: 0; color: #18181B;">⚡ Recent Campaign Activity</h4>
                    <p style="font-family: 'Inter', sans-serif; font-size: 12px; color: #71717A; margin: 2px 0 0 0;">Live timeline of contacts and outreach transactions</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            recent_cols = [c for c in ["email", "name", "company", "status", "created_at"] if c in df.columns]
            st.dataframe(
                df[recent_cols].head(8),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "email": "Recipient Email",
                    "name": "Contact Name",
                    "company": "Company",
                    "status": "Current Status",
                    "created_at": "Logged At",
                },
            )


# ─────────────────────────────────────────────────────────────
# PAGE 2: UPLOAD LEADS
# ─────────────────────────────────────────────────────────────
def render_upload() -> None:
    render_top_banner(
        "Upload Leads & Generate Drafts",
        "Import fresh lead spreadsheets, automatically skip already-contacted leads, and generate personalized drafts.",
        "Smart Deduplication",
    )

    uploaded_file = st.file_uploader(
        "Drag and drop your CSV or Excel lead sheet here",
        type=["csv", "xlsx"],
        help="Required column: 'email'. Optional columns: 'name', 'company', 'lead_id', 'last_activity_date', 'last_deal_stage'",
    )

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".csv"):
                raw_df = pd.read_csv(uploaded_file)
            else:
                raw_df = pd.read_excel(uploaded_file)

            st.success(f"File loaded successfully: **{uploaded_file.name}** ({len(raw_df)} rows discovered)")

            db = SessionLocal()
            try:
                sent_emails = get_already_sent_emails(db)
                drafted_emails = get_already_drafted_emails(db)
            finally:
                db.close()

            new_leads_df, skipped_sent_df, skipped_drafted_df = detect_lead_status_in_dataframe(
                raw_df, sent_emails=sent_emails, drafted_emails=drafted_emails
            )

            # Summary Metrics
            st.markdown("<br>", unsafe_allow_html=True)
            m1, m2, m3, m4 = st.columns(4, border=True)
            m1.metric("Total in Uploaded Sheet", len(raw_df))
            m2.metric("Skipped (Already Sent)", len(skipped_sent_df))
            m3.metric("Pending in Review", len(skipped_drafted_df))
            m4.metric("New Leads Ready for Outreach", len(new_leads_df))

            st.markdown("<br>", unsafe_allow_html=True)

            # ── Prominent Template Selector & Batch Drafting Station ──
            all_available_tpls = load_all_templates()
            tpl_map = {f"{t['name']} [{t.get('category', 'Outreach')}]": t for t in all_available_tpls}

            with st.container(border=True):
                st.markdown("##### 📑 Step 2: Choose Template & Generate Drafts for Email Review")
                col_tpl_sel, col_tpl_meta = st.columns([3, 2], vertical_alignment="bottom")
                with col_tpl_sel:
                    selected_tpl_label = st.selectbox(
                        "Choose outreach template to personalize for this sheet:",
                        options=list(tpl_map.keys()),
                        index=0,
                        key="upload_sheet_template_selector",
                        help="Assigns this specific template design to every lead in this sheet."
                    )
                    chosen_tpl_obj = tpl_map[selected_tpl_label]

                with col_tpl_meta:
                    tpl_subj = chosen_tpl_obj.get("subject") or chosen_tpl_obj.get("subject_pattern") or "Customized per lead"
                    st.caption(f"📧 **Subject:** `{tpl_subj}`")

                # Smart target selection: auto-prioritize new leads, else existing/uploaded leads
                if not new_leads_df.empty:
                    target_df = new_leads_df.copy()
                elif not skipped_drafted_df.empty:
                    target_df = skipped_drafted_df.copy()
                else:
                    target_df = raw_df.copy()

                target_count = len(target_df)

                btn_col1, btn_col2 = st.columns([1.6, 1.4])
                with btn_col1:
                    can_generate = target_count > 0
                    lead_word = "Lead" if target_count == 1 else "Leads"
                    btn_label = f"🚀 Generate AI Drafts & Open Email Review ({target_count} {lead_word})" if can_generate else "⚠️ No leads ready to draft"
                    start_draft_generation = st.button(
                        btn_label,
                        type="primary",
                        disabled=not can_generate,
                        key="gen_drafts_new",
                        help="Generate personalized outreach emails using the chosen template and transition immediately to Email Review Studio."
                    )
                with btn_col2:
                    active_drafts_count = len(drafted_emails) if 'drafted_emails' in locals() else 0
                    btn_rev_label = f"👉 Open Email Review Studio ({active_drafts_count} Drafts)" if active_drafts_count > 0 else "👉 Open Email Review Studio"
                    if st.button(btn_rev_label, key="goto_email_review", type="secondary"):
                        st.session_state.active_page = "email"
                        st.query_params["page"] = "email"
                        st.rerun()

            if start_draft_generation:
                    campaign_name = os.getenv("CAMPAIGN_NAME", "default_campaign")
                    progress_bar = st.progress(0.0, text=f"Generating personalized drafts with '{chosen_tpl_obj['name']}'...")
                    db = SessionLocal()
                    created_count = 0
                    failed_count = 0
                    failed_errors = []
                    successfully_drafted_rows = []

                    for idx, row in target_df.iterrows():
                        row_dict = {str(k).strip().lower(): v for k, v in row.items()}
                        email = str(row_dict.get("email", "")).strip().lower()
                        if not email or "@" not in email:
                            for candidate in ["email_address", "email address", "e-mail", "mail", "contact_email", "to"]:
                                val = row_dict.get(candidate)
                                if pd.notna(val) and "@" in str(val):
                                    email = str(val).strip().lower()
                                    break

                        name = None
                        for candidate in ["name", "full name", "contact name", "lead name", "first name", "firstname", "first_name", "full_name"]:
                            val = row_dict.get(candidate)
                            if pd.notna(val) and str(val).strip().lower() not in ("nan", "none", ""):
                                name = str(val).strip()
                                break

                        company = None
                        for candidate in ["company", "company name", "organization", "account", "business", "company_name", "org"]:
                            val = row_dict.get(candidate)
                            if pd.notna(val) and str(val).strip().lower() not in ("nan", "none", ""):
                                company = str(val).strip()
                                break

                        lead_id = str(row_dict.get("lead_id", f"lead_{idx}"))
                        last_activity = None if pd.isna(row_dict.get("last_activity_date")) else str(row_dict.get("last_activity_date"))
                        last_deal = None if pd.isna(row_dict.get("last_deal_stage")) else str(row_dict.get("last_deal_stage"))

                        progress_bar.progress(
                            (created_count + failed_count) / target_count,
                            text=f"Drafting email for {email} ({name or 'Lead'})...",
                        )

                        try:
                            token = generate_token()
                            booking_url = os.getenv(
                                "BOOKING_FORM_URL",
                                "https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled",
                            )
                            tracking_link = booking_url

                            lead_data = {
                                "name": name,
                                "company": company,
                                "email": email,
                                "last_activity_date": last_activity,
                                "last_deal_stage": last_deal,
                            }
                            subject, body = render_template(
                                chosen_tpl_obj,
                                lead_data=lead_data,
                                booking_url=tracking_link,
                            )

                            # Check if un-sent draft already exists in DB for this email
                            existing_draft = (
                                db.query(CampaignLog)
                                .filter(
                                    func.lower(CampaignLog.email) == email.lower(),
                                    CampaignLog.status.in_(["drafted", "pending", "draft", "rejected"]),
                                    CampaignLog.email_sent_at.is_(None),
                                )
                                .first()
                            )

                            if existing_draft:
                                update_draft_content(
                                    db,
                                    existing_draft.id,
                                    subject=subject,
                                    body=body,
                                    template_id=chosen_tpl_obj["id"],
                                    template_name=chosen_tpl_obj["name"],
                                )
                                existing_draft.status = "drafted"
                                db.commit()
                            else:
                                create_pending_entry(
                                    db,
                                    campaign_name=campaign_name,
                                    lead_id=lead_id,
                                    email=email,
                                    name=name,
                                    company=company,
                                    token=token,
                                    tracking_link=tracking_link,
                                    subject=subject,
                                    body=body,
                                    status="drafted",
                                    template_id=chosen_tpl_obj["id"],
                                    template_name=chosen_tpl_obj["name"],
                                    organization_id=st.session_state.get("current_org_id"),
                                )
                            created_count += 1
                            successfully_drafted_rows.append(row)
                        except Exception as err:
                            db.rollback()
                            failed_errors.append(f"{email}: {err}")
                            failed_count += 1

                    db.close()
                    progress_bar.progress(1.0, text="Draft generation completed!")

                    if successfully_drafted_rows:
                        try:
                            append_or_update_leads_dataset(pd.DataFrame(successfully_drafted_rows), default_status="drafted")
                        except Exception:
                            pass
                    st.cache_data.clear()
                    try:
                        load_campaign_logs.clear()
                    except Exception:
                        pass

                    if created_count > 0:
                        st.session_state["send_success_banner"] = f"🎉 Successfully generated {created_count} personalized outreach draft(s) with '{chosen_tpl_obj['name']}'! Ready for review below."
                        st.session_state["trigger_review_balloons"] = True
                        st.balloons()
                        st.session_state.active_page = "email"
                        st.query_params["page"] = "email"
                        time.sleep(0.3)
                        st.rerun()

                    if failed_errors:
                        for err_msg in failed_errors:
                            st.error(f"❌ Failed: {err_msg}")


            st.markdown("<br>", unsafe_allow_html=True)

            # ── Detailed Data Inspection Tabs ──
            tab_new, tab_skipped, tab_drafted = st.tabs([
                f"✨ New Leads Ready ({len(new_leads_df)})",
                f"🛡️ Skipped / Already Emailed ({len(skipped_sent_df)})",
                f"⏳ Awaiting Approval ({len(skipped_drafted_df)})",
            ])

            with tab_new:
                if not new_leads_df.empty:
                    st.markdown("##### New Leads to Draft Outreach For")
                    cols_to_show = [c for c in ["lead_id", "email", "name", "company", "last_activity_date"] if c in new_leads_df.columns]
                    if not cols_to_show:
                        cols_to_show = new_leads_df.columns.tolist()[:5]
                    st.dataframe(new_leads_df[cols_to_show], use_container_width=True, hide_index=True)
                else:
                    if not skipped_drafted_df.empty:
                        st.info(f"⏳ **{len(skipped_drafted_df)} lead(s)** from this sheet currently have active drafts awaiting your review in the Email Review Studio.")
                    else:
                        st.info("ℹ️ All leads in this sheet have already received emails. Click 'Generate AI Drafts' above to draft outreach with this template.")


            with tab_skipped:
                if not skipped_sent_df.empty:
                    st.warning(
                        "🛡️ **Zero-Duplicate Protection**: These leads have already received an email. "
                        "They are safely blocked to preserve sender reputation."
                    )
                    cols_to_show = [c for c in ["email", "name", "company", "skip_reason"] if c in skipped_sent_df.columns]
                    st.dataframe(skipped_sent_df[cols_to_show], use_container_width=True, hide_index=True)
                else:
                    st.success("No leads in this sheet were previously sent.")

            with tab_drafted:
                if not skipped_drafted_df.empty:
                    st.info("⏳ These leads already have drafts awaiting your review in the **Email Review Studio**.")
                    cols_to_show = [c for c in ["email", "name", "company", "skip_reason"] if c in skipped_drafted_df.columns]
                    st.dataframe(skipped_drafted_df[cols_to_show], use_container_width=True, hide_index=True)
                else:
                    st.write("No leads in this sheet are currently awaiting review.")

            st.markdown("---")
            st.markdown("##### 📁 Lead Sheet Synchronization")
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                if st.button("📥 Sync Unsaved Leads to leads.xlsx", key="append_all_leads"):
                    append_or_update_leads_dataset(raw_df)
                    st.success(f"Synchronized leads to {DEFAULT_LEADS_FILE}!")
                    st.cache_data.clear()

            with col_d2:
                if os.path.exists(DEFAULT_LEADS_FILE):
                    with open(DEFAULT_LEADS_FILE, "rb") as f:
                        st.download_button(
                            label="⬇️ Download Current leads.xlsx (with Statuses)",
                            data=f,
                            file_name="leads.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="dl_leads_xlsx",
                        )

        except Exception as e:
            st.error(f"Error processing lead sheet: {e}")


# ─────────────────────────────────────────────────────────────
# PAGE 3: LEADS DIRECTORY
# ─────────────────────────────────────────────────────────────
def render_leads(df: pd.DataFrame) -> None:
    _render_tab_leads_directory()
    return

    # Filter out un-sent rejected or cancelled drafts
    active_df = df[~df["status"].astype(str).str.lower().isin(["rejected", "cancelled", "failed"])].copy()
    if active_df.empty:
        active_df = df.copy()

    # Pre-aggregate by Unique Lead (email) to track multiple templates per lead
    unique_leads_data = []
    for email_key, group in active_df.groupby(active_df["email"].astype(str).str.strip().str.lower()):
        if not email_key or email_key in ["none", "nan", ""]:
            continue

        names = [str(n).strip() for n in group["name"].dropna() if str(n).strip().lower() not in ["none", "nan", ""]]
        best_name = names[0] if names else "Lead"
        companies = [str(c).strip() for c in group["company"].dropna() if str(c).strip().lower() not in ["none", "nan", ""]]
        best_company = companies[0] if companies else "N/A"

        # Collect unique templates sent or drafted for this lead
        tpl_names_sent = []
        for _, r in group.iterrows():
            t_name = str(r.get("template_name") or "").strip()
            if not t_name or t_name.lower() in ["none", "nan"]:
                subj = str(r.get("subject") or "").lower()
                if "velocity" in subj or "forward deployed" in subj:
                    t_name = "Template 1: Forward Deployed AI Engineers"
                elif "voice" in subj or "calling" in subj:
                    t_name = "Template 2: Autonomous Voice Agents"
                elif "agentic" in subj or "llm" in subj:
                    t_name = "Template 9: Custom Agentic Workflows (Mohit)" if ("mohit" in subj or "mohit" in str(r.get("body") or "").lower()) else "Template 3: Custom Agentic Workflows"
                elif "automation" in subj or "erp" in subj or "repetitive" in subj:
                    t_name = "Template 10: Business Process Automation (Mohit)" if ("mohit" in subj or "mohit" in str(r.get("body") or "").lower()) else "Template 4: Business Process Automation"
                elif "workbench" in subj or "offshore" in subj:
                    t_name = "Template 5: Dedicated Offshore AI Workbench"
                elif "modernization" in subj or "internal" in subj:
                    t_name = "Template 6: Legacy Modernization"
                elif "note" in subj or "manage recruiters" in subj or "founder-to-founder note" in subj:
                    t_name = "Template 8: A Founder-to-Founder Note"
                elif "strategy" in subj or "margin" in subj or "founder" in subj or "overhead" in subj:
                    t_name = "Template 11: Strategic AI Advisory (Mohit)" if ("mohit" in subj or "mohit" in str(r.get("body") or "").lower()) else "Template 7: Founder-to-Founder AI Strategy"
                else:
                    t_name = "Custom Template"
            if t_name and t_name not in tpl_names_sent:
                tpl_names_sent.append(t_name)

        templates_str = ", ".join(tpl_names_sent) if tpl_names_sent else "Standard Template"

        # Determine highest progression status
        stat_priority = ["confirmed", "meeting_scheduled", "scheduled", "form_filled", "replied", "sent", "drafted", "pending", "draft", "new"]
        lead_statuses = [str(s).lower() for s in group["status"].dropna()]
        highest_status = "new"
        for sp in stat_priority:
            if sp in lead_statuses:
                highest_status = sp
                break

        send_count = int((group["status"].isin(["sent", "meeting_scheduled"])).sum())
        total_touches = len(group)

        # Engagement aggregates
        has_opened = bool((group["opened"].fillna(False) == True).any()) if "opened" in group.columns else False
        has_clicked = bool((group["clicked_link"].fillna(False) == True).any()) if "clicked_link" in group.columns else False
        has_replied = bool(group["reply_received_at"].notna().any()) if "reply_received_at" in group.columns else False
        has_booked = bool(group["booking_status"].isin(["scheduled", "meeting_scheduled", "confirmation_sent", "confirmed"]).any()) if "booking_status" in group.columns else False

        last_contact = group["email_sent_at"].dropna().max() if not group["email_sent_at"].dropna().empty else group["created_at"].dropna().max()

        unique_leads_data.append({
            "email": email_key,
            "name": best_name,
            "company": best_company,
            "templates_used": templates_str,
            "template_count": len(tpl_names_sent),
            "send_count": send_count,
            "total_touches": total_touches,
            "status": highest_status,
            "has_opened": has_opened,
            "has_clicked": has_clicked,
            "has_replied": has_replied,
            "has_booked": has_booked,
            "last_contact": last_contact,
            "campaign": group["campaign"].iloc[0] if "campaign" in group.columns else "default",
            "lead_id": group["lead_id"].iloc[0] if "lead_id" in group.columns else "",
        })

    df_unique = pd.DataFrame(unique_leads_data)

    # ── Top KPI Bar ──
    total_unique_leads = len(df_unique)
    total_emails_sent = int((active_df["status"] == "sent").sum())
    multi_template_leads = int((df_unique["template_count"] > 1).sum()) if not df_unique.empty else 0
    avg_touches = round(total_emails_sent / max(1, total_unique_leads), 1)

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-top-bar kpi-bar-blue"></div>
                <div class="kpi-header"><span class="kpi-label">Unique Leads</span><span style="font-size: 18px;">👥</span></div>
                <div class="kpi-value">{total_unique_leads}</div>
                <div class="kpi-micro"><span class="kpi-pill kpi-pill-blue">100% Unique</span><span>in campaign database</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-top-bar kpi-bar-teal"></div>
                <div class="kpi-header"><span class="kpi-label">Dispatched Emails</span><span style="font-size: 18px;">🚀</span></div>
                <div class="kpi-value">{total_emails_sent}</div>
                <div class="kpi-micro"><span class="kpi-pill kpi-pill-teal">Sent</span><span>across all variants</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-top-bar kpi-bar-purple"></div>
                <div class="kpi-header"><span class="kpi-label">Multi-Template Contacts</span><span style="font-size: 18px;">📑</span></div>
                <div class="kpi-value">{multi_template_leads}</div>
                <div class="kpi-micro"><span class="kpi-pill" style="background: #F3E8FF; color: #7C3AED;">Multi-Touch</span><span>received 2+ variants</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-top-bar kpi-bar-amber"></div>
                <div class="kpi-header"><span class="kpi-label">Avg Touches / Lead</span><span style="font-size: 18px;">🎯</span></div>
                <div class="kpi-value">{avg_touches}x</div>
                <div class="kpi-micro"><span class="kpi-pill kpi-pill-amber">Outreach Depth</span><span>emails per lead</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

    # ── Filter Controls ──
    c_f1, c_f2, c_f3 = st.columns([1, 1, 1.6])
    with c_f1:
        stat_opts = ["All"] + sorted(df_unique["status"].unique().tolist()) if not df_unique.empty else ["All"]
        filter_status = st.selectbox("Filter by Status", stat_opts, key="leads_stat_filter")
    with c_f2:
        touch_opts = ["All Touchpoints", "Single Template (1)", "Multiple Templates (2+)"]
        filter_touch = st.selectbox("Outreach Depth", touch_opts, key="leads_touch_filter")
    with c_f3:
        search_query = st.text_input("🔍 Search Lead by Name, Email, Company or Template", placeholder="Type to search...", key="leads_search")

    filtered_unique = df_unique.copy()
    if filter_status != "All":
        filtered_unique = filtered_unique[filtered_unique["status"] == filter_status]
    if filter_touch == "Single Template (1)":
        filtered_unique = filtered_unique[filtered_unique["template_count"] <= 1]
    elif filter_touch == "Multiple Templates (2+)":
        filtered_unique = filtered_unique[filtered_unique["template_count"] > 1]
    if search_query:
        sq = search_query.strip().lower()
        filtered_unique = filtered_unique[
            filtered_unique["email"].str.lower().str.contains(sq)
            | filtered_unique["name"].str.lower().str.contains(sq)
            | filtered_unique["company"].str.lower().str.contains(sq)
            | filtered_unique["templates_used"].str.lower().str.contains(sq)
        ]

    # ── Tabs: Unique Leads vs All Logs ──
    tab_unique, tab_logs, tab_dispatch = st.tabs([
        f"👥 Unique Leads & Templates History ({len(filtered_unique)})",
        f"📨 All Outreach Records ({len(active_df)})",
        "📮 Dispatch Logs",
    ])

    with tab_unique:
        st.markdown(
            f"<p style='color: #64748B; font-size: 13px; font-weight: 500; margin-bottom: 8px;'>Showing <strong>{len(filtered_unique)}</strong> unique lead(s) with full template usage history.</p>",
            unsafe_allow_html=True,
        )

        display_cols = ["email", "name", "company", "templates_used", "send_count", "status", "last_contact"]
        st.dataframe(
            filtered_unique[display_cols],
            use_container_width=True,
            hide_index=True,
            column_config={
                "email": st.column_config.TextColumn("Recipient Email", width="medium"),
                "name": st.column_config.TextColumn("Contact Name", width="small"),
                "company": st.column_config.TextColumn("Company", width="medium"),
                "templates_used": st.column_config.TextColumn("Templates Used", width="large", help="All email template variants sent to this lead"),
                "send_count": st.column_config.NumberColumn("Emails Sent", width="small", format="%d"),
                "status": st.column_config.TextColumn("Outreach Status", width="small"),
                "last_contact": st.column_config.DatetimeColumn("Last Outreach", width="medium", format="YYYY-MM-DD HH:mm"),
            },
        )

        # Interactive Lead Outreach Inspector
        if not filtered_unique.empty:
            with st.expander("🔍 Inspect Full Template History for a Specific Lead", expanded=False):
                inspect_email = st.selectbox(
                    "Choose Lead to Inspect History:",
                    options=filtered_unique["email"].tolist(),
                    format_func=lambda em: f"{em} ({filtered_unique[filtered_unique['email'] == em]['name'].iloc[0]})",
                    key="sel_inspect_lead_history",
                )
                if inspect_email:
                    lead_entries = active_df[active_df["email"].astype(str).str.strip().str.lower() == inspect_email.lower()].sort_values(by="created_at", ascending=False)
                    st.markdown(f"##### Outreach Timeline for `{inspect_email}` ({len(lead_entries)} Event(s))")
                    for _, entry_row in lead_entries.iterrows():
                        t_lbl = entry_row.get("template_name") or "Template"
                        st.markdown(
                            f"""
                            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                                    <strong style="color: #0F172A; font-size: 14px;">📑 {t_lbl}</strong>
                                    <span class="badge badge-{'sent' if entry_row['status'] == 'sent' else 'drafted'}">{str(entry_row['status']).upper()}</span>
                                </div>
                                <div style="font-size: 12.5px; color: #475569; margin-bottom: 4px;">
                                    <strong>Subject:</strong> {entry_row.get('subject') or 'No subject'}
                                </div>
                                <div style="font-size: 11.5px; color: #64748B; display: flex; gap: 14px;">
                                    <span>Sent: {entry_row.get('email_sent_at') or 'Not yet dispatched'}</span>
                                    <span>Opened: {'✓ Yes' if entry_row.get('opened') else '✕ No'}</span>
                                    <span>Clicked: {'✓ Yes' if entry_row.get('clicked_link') else '✕ No'}</span>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

    with tab_logs:
        st.markdown(
            f"<p style='color: #64748B; font-size: 13px; font-weight: 500; margin-bottom: 8px;'>Raw chronological log of all {len(active_df)} outreach entries.</p>",
            unsafe_allow_html=True,
        )
        log_cols = [c for c in ["lead_id", "email", "name", "company", "template_name", "status", "subject", "email_sent_at"] if c in active_df.columns]
        st.dataframe(
            active_df[log_cols],
            use_container_width=True,
            hide_index=True,
            column_config={
                "lead_id": "Lead ID",
                "email": "Email Address",
                "name": "Full Name",
                "company": "Company",
                "template_name": "Template Used",
                "status": "Status",
                "subject": "Email Subject",
                "email_sent_at": "Sent At",
            },
        )
        
    with tab_dispatch:
        st.markdown(
            "<p style='color: #64748B; font-size: 13px; font-weight: 500; margin-bottom: 8px;'>Chronological dispatch logs from <b>send_attempts</b> for this campaign.</p>",
            unsafe_allow_html=True,
        )
        try:
            from Backend.db import SessionLocal
            from Backend.channels_models import SendAttempt
            db_dispatch = SessionLocal()
            try:
                # We need the current campaign string... It's active_campaign
                campaign_str = str(active_campaign) if active_campaign else "unknown"
                attempts = db_dispatch.query(SendAttempt).filter(
                    SendAttempt.organization_id == st.session_state.current_org_id,
                    SendAttempt.campaign_name == campaign_str
                ).order_by(SendAttempt.created_at.desc()).limit(500).all()
                
                if attempts:
                    attempts_data = [{
                        "time": a.created_at,
                        "lead_id": a.lead_id,
                        "status": "🟢 " + a.status if a.status == "sent" else ("🟡 " + a.status if a.status == "skipped" else "🔴 " + a.status),
                        "channel": a.channel,
                        "from_address": a.from_address,
                        "reason": a.reason or ""
                    } for a in attempts]
                    st.dataframe(attempts_data, use_container_width=True, hide_index=True)
                else:
                    st.info("No dispatch logs found for this campaign.")
            finally:
                db_dispatch.close()
        except Exception as e:
            st.error(f"Failed to load dispatch logs: {e}")



LOGO_URL = "https://res.cloudinary.com/dqreqsjas/image/upload/v1790076736/logo-light.png"
LOGO_HEADER_HTML = f'<div align="center" style="background-color:#071a2d;padding:18px 20px 16px 20px;text-align:center;border-top-left-radius:10px;border-top-right-radius:10px;border-bottom:3px solid #0f62fe;"><a href="https://www.nenotechnology.com/" target="_blank" style="text-decoration:none;display:inline-block;"><img src="{LOGO_URL}" alt="Neno Technology" width="160" height="41" style="display:block;margin:0 auto;border:0;outline:none;text-decoration:none;-ms-interpolation-mode:bicubic;width:160px;height:auto;max-height:42px;pointer-events:none;"></a></div>'


def clean_natural_email_body(html_text: str) -> str:
    if not html_text:
        return html_text
    cleaned = html_text
    # Replace old broken ngrok logos with the new reliable Cloudinary logo
    cleaned = re.sub(r'https?://[^\s"\'<>]*ngrok[^\s"\'<>]*/logo(?:-dark|-light)?\.png', LOGO_URL, cleaned, flags=re.IGNORECASE)
    # Remove artificial outer card boxes
    cleaned = re.sub(r'<div style="max-width:600px;margin:0 auto;background:#ffffff;color:#1a1a1a;border:1px solid #e3e6eb;border-radius:8px;overflow:hidden;font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.6;">\s*', '<div style="font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.45;color:#1a1a1a;">', cleaned)
    cleaned = re.sub(r'<div style="max-width:600px;margin:0 auto;background:#ffffff;color:#1e293b;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.6;">\s*', '<div style="font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.45;color:#1e293b;">', cleaned)
    cleaned = re.sub(r'<div style="padding:(?:24px|26px 24px);">\s*', '', cleaned)
    cleaned = re.sub(r'<div style="background:#f7f8fa;padding:14px 24px;font-size:11.5px;color:#(?:8b93a1|94a3b8);text-align:center;[^"]*">.*?</div>\s*</div>\s*$', '</div>', cleaned, flags=re.DOTALL)
    # Ensure Cloudinary logo header is present if missing
    if "logo-dark.png" not in cleaned and "logo-light.png" not in cleaned and "cloudinary" not in cleaned:
        if cleaned.startswith("<div"):
            cleaned = re.sub(r'(<div[^>]*>)', r'\1\n  ' + LOGO_HEADER_HTML, cleaned, count=1)
        else:
            cleaned = LOGO_HEADER_HTML + "\n" + cleaned
    # Consolidate legacy split sentences from Option 2
    cleaned = re.sub(
        r'<p style="margin:0 0 10px 0;padding:0;">I hope this message finds you well\.</p>\s*<p style="margin:0 0 10px 0;padding:0;">As a returning client, the first consultation is on us\.</p>',
        '<p style="margin:0 0 10px 0;margin-top:0;margin-bottom:10px;padding:0;line-height:1.45;">I hope this message finds you well. As a returning client, the first consultation is on us.</p>',
        cleaned,
    )
    # Tighten question & button margins
    cleaned = re.sub(
        r'<p style="margin:0 0 10px 0;padding:0;font-weight:600;color:#0f172a;">Would you be open to a 20-minute call to explore what would be most useful for you right now\?</p>',
        '<p style="margin:0 0 8px 0;margin-top:0;margin-bottom:8px;padding:0;font-weight:600;color:#0f172a;line-height:1.45;">Would you be open to a 20-minute call to explore what would be most useful for you right now?</p>',
        cleaned,
    )
    cleaned = re.sub(
        r'<div style="margin:(?:10px 0 14px 0|12px 0 16px 0);(?:padding:0;)?">',
        '<div style="margin:0 0 12px 0;margin-top:0;margin-bottom:12px;padding:0;">',
        cleaned,
    )

    # Clean any localhost or /form tracking URLs so recipients always get the real booking link
    target_booking = os.getenv(
        "BOOKING_FORM_URL",
        "https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled",
    )
    cleaned = re.sub(
        r'href=["\']https?://(?:localhost|127\.0\.0\.1)(?::\d+)?(?:/[^"\']*)?["\']',
        f'href="{target_booking}"',
        cleaned,
    )
    cleaned = re.sub(
        r'https?://[^/\"\'\s]+/form\?token=[^\s"\'<>]+',
        target_booking,
        cleaned,
    )

    return cleaned.strip()


# ─────────────────────────────────────────────────────────────
# DIALOGS: EMAIL DISPATCH CONFIRMATION
# ─────────────────────────────────────────────────────────────
@st.dialog("Confirm Email Dispatch")
def confirm_approve_send_dialog(entry_id: str, email: str, subject: str, body: str, sender_email: Optional[str] = None):
    st.markdown(
        f"""
        <div style="margin-bottom: 12px;">
            <p style="font-size: 15px; margin-bottom: 6px; color: #0F172A;">
                Are you sure you want to approve and send this email to <strong style="color: #2563EB;">{email}</strong>?
            </p>
            <p style="font-size: 13px; color: #64748B; margin: 0;">
                Subject: <strong>{subject}</strong>
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("👁️ Preview Message & Links", expanded=True):
        preview_modal = body if (body or "").strip().startswith(("<div", "<table", "<html", "<body")) else (body or "").replace(chr(10), '<br>')
        preview_modal = clean_natural_email_body(preview_modal)
        # Use st.iframe for pixel-perfect rendering of rich HTML email templates
        # (st.markdown strips most HTML tags/styles, causing broken preview with excessive whitespace)
        wrapped_preview = f"""
        <div style="background: #ffffff; border: 1px solid #E2E8F0; border-radius: 8px; padding: 16px; font-size: 14px; line-height: 1.6; color: #1E293B; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;">
            {preview_modal}
        </div>
        """
        st.iframe(wrapped_preview, height=480)

    active_single_sender = sender_email or get_active_outreach_sender()
    org_name = st.session_state.get("current_org", {}).get("name", "Organization")

    st.markdown(
        f"""
        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px 14px; margin-bottom: 12px; font-size: 13px; color: #334155;">
            ✉️ <strong>Company Sender:</strong> <code style="color: #2563EB; font-weight: 600;">{active_single_sender}</code> ({org_name})
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🚀 Confirm & Send Email", type="primary", use_container_width=True, key="dlg_confirm_send"):
            db = SessionLocal()
            try:
                update_draft_content(db, entry_id, subject, body)
                try:
                    approve_and_send_entry(db, entry_id, sender_email=active_single_sender)
                except TypeError as te:
                    if "sender_email" in str(te):
                        sync_sender_env(active_single_sender)
                        approve_and_send_entry(db, entry_id)
                    else:
                        raise
                st.session_state["send_success_banner"] = f"🎉 Email successfully dispatched to {email} from {active_single_sender}!"
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Send failed: {e}")
            finally:
                db.close()

    with c2:
        if st.button("Cancel", use_container_width=True, key="dlg_cancel_send"):
            st.rerun()


@st.dialog("Confirm Bulk Email Dispatch")
def confirm_approve_all_dialog(drafts_data, template_id: Optional[int] = None):
    count = len(drafts_data)
    
    # Identify unique templates among the pending drafts
    tpl_names = list({d.get("template_name") or "Reviewed Outreach Draft" for d in drafts_data if d.get("template_name")})
    tpl_summary_str = ", ".join(tpl_names[:2]) if tpl_names else "Reviewed Outreach Templates"
    if len(tpl_names) > 2:
        tpl_summary_str += f" (+{len(tpl_names)-2} more)"

    st.markdown(
        f"""
        <div style="margin-bottom: 12px;">
            <p style="font-size: 15px; margin-bottom: 6px; color: #0F172A;">
                Are you sure you want to approve and send all <strong style="color: #2563EB;">{count}</strong> pending email drafts?
            </p>
            <div style="background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 8px; padding: 10px 14px; margin-bottom: 12px; font-size: 13.5px; color: #1E40AF;">
                ✨ <strong>Reviewed Content Preserved:</strong> All {count} emails will be dispatched using the exact subject lines and personalized message bodies reviewed in Email Review Studio.
            </div>
            <p style="font-size: 13px; color: #64748B; margin: 0;">
                Dispatched reliably via Microsoft Graph with rate throttling and automatic retry protection.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    force_send = st.checkbox(
        "Bypass duplicate protection (force send to all leads, even if previously sent)",
        value=False,
        key="dlg_chk_force_resend",
        help="Check this if you are re-sending or testing leads that were already marked sent in previous campaigns.",
    )

    campaign_name_for_dialog = drafts_data[0].get("campaign_name", "unknown") if drafts_data else "unknown"
    active_blast_sender = render_sender_selector(campaign_name_for_dialog)


    with st.expander(f"📋 Review Recipients & Active Subjects ({count})", expanded=False):
        for d in drafts_data:
            s_clean = (d.get("subject") or "Outreach Invitation").replace("\ufffd", "-").replace("—", "-").strip()
            t_label = d.get("template_name") or "Draft"
            st.write(f"- **{d.get('email')}** ({d.get('name') or 'Lead'}, {d.get('company') or 'N/A'}) — *{s_clean}* `[{t_label}]`")

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button(f"🚀 Send All {count} Emails", type="primary", use_container_width=True, key="dlg_confirm_send_all"):
            progress_bar = st.progress(0.0)
            status_label = st.empty()
            status_label.markdown(f"⚡ **Preparing high-reliability dispatch for {count} recipients via `{active_blast_sender}`...**")

            def _update_progress(completed_cnt, total_cnt, email_str, status_type):
                pct = min(1.0, completed_cnt / max(1, total_cnt))
                progress_bar.progress(pct)
                if status_type == "sent":
                    status_label.markdown(f"🚀 **[{completed_cnt}/{total_cnt}]** Dispatched to `{email_str}` via `{active_blast_sender}`")
                elif status_type == "skipped":
                    status_label.markdown(f"🛡️ **[{completed_cnt}/{total_cnt}]** Duplicate skipped: `{email_str}`")
                else:
                    status_label.markdown(f"⚠️ **[{completed_cnt}/{total_cnt}]** Failed: `{email_str}`")

            try:
                try:
                    res = bulk_approve_and_send_entries(
                        entry_ids=[d["id"] for d in drafts_data],
                        template_id=template_id,
                        max_workers=2,
                        force_resend=force_send,
                        progress_callback=_update_progress,
                        sender_email=active_blast_sender,
                    )
                except TypeError as te:
                    if "sender_email" in str(te):
                        sync_sender_env(active_blast_sender)
                        res = bulk_approve_and_send_entries(
                            entry_ids=[d["id"] for d in drafts_data],
                            template_id=template_id,
                            max_workers=2,
                            force_resend=force_send,
                            progress_callback=_update_progress,
                        )
                    else:
                        raise

                approved_count = res.get("approved_count", 0)
                skipped_count = res.get("skipped_count", 0)
                error_details = res.get("error_details", [])

                progress_bar.progress(1.0)
                msg = f"🎉 Successfully dispatched {approved_count} of {count} emails from {active_blast_sender}!"
                if skipped_count > 0:
                    msg += f" (Skipped {skipped_count} duplicate/already sent. Enable 'Bypass duplicate protection' to force send.)"
                if error_details:
                    msg += f" (Encountered {len(error_details)} errors: {'; '.join(error_details[:2])})"
                st.session_state["send_success_banner"] = msg
                st.cache_data.clear()
                try:
                    load_campaign_logs.clear()
                except Exception:
                    pass
                st.rerun()
            except Exception as e:
                st.error(f"Dispatch error: {e}")

    with c2:
        if st.button("Cancel", use_container_width=True, key="dlg_cancel_all_btn"):
            st.rerun()


@st.dialog("Confirm Bulk Draft Rejection")
def confirm_reject_all_dialog(drafts_data):
    count = len(drafts_data)
    st.markdown(
        f"""
        <div style="margin-bottom: 12px;">
            <p style="font-size: 15px; margin-bottom: 6px; color: #0F172A;">
                Are you sure you want to reject all <strong style="color: #DC2626;">{count}</strong> pending email drafts?
            </p>
            <div style="background: #FEF2F2; border: 1px solid #FECACA; border-radius: 8px; padding: 12px 14px; margin-bottom: 12px; font-size: 13.5px; color: #991B1B;">
                🛑 <strong>Bulk Rejection:</strong> All {count} drafts will be marked as <strong>Rejected</strong> and removed from the review queue. No emails will be dispatched to these recipients.
            </div>
            <p style="font-size: 13px; color: #64748B; margin: 0;">
                You can re-import or re-draft these leads anytime from the Upload &amp; Draft tab.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander(f"📋 Review Leads to be Rejected ({count})", expanded=False):
        for d in drafts_data:
            st.write(f"- **{d['email']}** ({d.get('name') or 'Lead'}, {d.get('company') or 'N/A'})")

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button(f"✕ Reject All {count} Drafts", type="primary", use_container_width=True, key="dlg_confirm_reject_all_btn"):
            progress_bar = st.progress(0.0)
            status_label = st.empty()
            status_label.markdown(f"🛑 **Rejecting {count} drafts...**")
            db = SessionLocal()
            try:
                rejected_count = bulk_reject_entries(db, [d["id"] for d in drafts_data])
                progress_bar.progress(1.0)
                st.session_state["send_success_banner"] = f"✕ Successfully rejected {rejected_count} email drafts."
                st.cache_data.clear()
                try:
                    load_campaign_logs.clear()
                except Exception:
                    pass
                st.rerun()
            except Exception as ex:
                st.error(f"Rejection error: {ex}")
            finally:
                db.close()

    with c2:
        if st.button("Cancel", use_container_width=True, key="dlg_cancel_reject_all_btn"):
            st.rerun()




# ─────────────────────────────────────────────────────────────
# PAGE 4: EMAIL REVIEW & APPROVAL STUDIO
# ─────────────────────────────────────────────────────────────
def render_email_review(df: pd.DataFrame) -> None:
    render_top_banner(
        "Email Review Studio",
        "Inspect AI-generated drafts, customize messaging, review live previews, and dispatch via Microsoft Graph.",
        "Quality Control",
    )

    if "send_success_banner" in st.session_state:
        st.success(st.session_state.pop("send_success_banner"))

    if st.session_state.pop("trigger_review_balloons", False):
        st.balloons()

    # Ensure status matching covers all pending/drafted variations
    drafts = pd.DataFrame()
    if not df.empty and "status" in df.columns:
        drafts = df[df["status"].astype(str).str.lower().isin(["drafted", "pending", "draft"])].copy()

    # Fallback to direct DB query in case of cache lag or instant transition
    if drafts.empty:
        db_fb = SessionLocal()
        try:
            db_pending = (
                db_fb.query(CampaignLog)
                .filter(CampaignLog.status.in_(["drafted", "pending", "draft"]))
                .order_by(CampaignLog.created_at.desc())
                .all()
            )
            if db_pending:
                load_campaign_logs.clear()
                st.cache_data.clear()
                fresh_rows = load_campaign_logs(st.session_state.get("current_org_id"))
                df = fresh_rows if isinstance(fresh_rows, pd.DataFrame) else pd.DataFrame(fresh_rows, columns=CAMPAIGN_LOG_COLUMNS)
                drafts = df[df["status"].astype(str).str.lower().isin(["drafted", "pending", "draft"])].copy()
        finally:
            db_fb.close()

    if drafts.empty:
        st.info("No pending drafts awaiting review. Upload a lead sheet in 'Upload & Draft' or 'Template Review & Hub (Tab 3)' to generate new drafts.")
        if st.button("🔄 Check for New Drafts Now", key="btn_check_drafts_empty"):
            load_campaign_logs.clear()
            st.cache_data.clear()
            st.rerun()
        return

    st.markdown(
        f"""
        <div style="display: flex; justify-content: space-between; align-items: center; background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 10px; padding: 12px 18px; margin-bottom: 20px;">
            <div style="display: flex; align-items: center; gap: 8px; font-weight: 600; color: #92400E; font-size: 14px;">
                <span>📬</span> <strong>{len(drafts)}</strong> draft email(s) awaiting your approval
            </div>
            <div style="display: flex; align-items: center; gap: 10px;">
                <span class="badge badge-drafted">Human-in-the-Loop</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Individual Lead Draft Inspector & Fine-Tuning ──
    pending_count = len(drafts)
    booking_url = os.getenv(
        "BOOKING_FORM_URL",
        "https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled",
    )

    # Build unique option keys to avoid selectbox collision
    id_to_label = {}
    for _, d_row in drafts.iterrows():
        n = d_row['name'] or 'Lead'
        c = f" · {d_row['company']}" if d_row['company'] else ""
        id_to_label[d_row["id"]] = f"{d_row['email']} ({n}{c})"

    col_sel_draft, col_ref_draft = st.columns([4, 1])
    with col_sel_draft:
        selected_draft_id = st.selectbox(
            "Select Draft to Review",
            options=list(id_to_label.keys()),
            format_func=lambda did: id_to_label.get(did, did),
            key="approval_select_id",
        )
    with col_ref_draft:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button("🔄 Refresh", key="btn_refresh_draft_list", help="Reload latest drafts from database"):
            load_campaign_logs.clear()
            st.cache_data.clear()
            st.rerun()

    matched = drafts[drafts["id"] == selected_draft_id]
    if matched.empty:
        matched = drafts.iloc[:1]
    row = matched.iloc[0]

    # Multi-template detection: check what templates have already been sent to this recipient
    target_em = str(row["email"]).strip().lower()
    current_tpl_id = str(row.get("template_id") or "").strip().lower()
    current_tpl_name = str(row.get("template_name") or "Selected Template").strip()

    prev_sent_records = []
    already_sent_this_exact_template = False
    if not df.empty and "email" in df.columns and "status" in df.columns:
        matched_sent = df[
            (df["email"].astype(str).str.strip().str.lower() == target_em)
            & (df["status"].astype(str).str.lower() == "sent")
            & (df["id"] != row["id"])
        ]
        if not matched_sent.empty:
            for _, s_row in matched_sent.iterrows():
                prev_sent_records.append(str(s_row.get("template_name") or "Template"))
                if current_tpl_id and str(s_row.get("template_id") or "").strip().lower() == current_tpl_id:
                    already_sent_this_exact_template = True
                elif current_tpl_name.lower() in str(s_row.get("template_name") or "").lower():
                    already_sent_this_exact_template = True

    if already_sent_this_exact_template:
        st.warning(
            f"⚠️ **Duplicate Template Warning**: Template '{current_tpl_name}' was already sent to `{row['email']}`! "
            "Dispatching this draft will send another copy of the same template."
        )
    elif prev_sent_records:
        st.info(
            f"ℹ️ **Multi-Template Outreach**: This lead previously received: **{', '.join(set(prev_sent_records))}**. "
            f"You are now reviewing follow-up outreach with **'{current_tpl_name}'**."
        )

    # Lead Metadata Info Cards
    c1, c2 = st.columns(2)
    with c1:
        history_str = f"Received {len(prev_sent_records)} prior outreach ({', '.join(set(prev_sent_records))})" if prev_sent_records else "First outreach (fresh lead)"
        st.markdown(
            f"""
            <div class="premium-card">
                <div class="card-header-row">
                    <span class="card-title">Lead Profile</span>
                    <span class="badge badge-pending">Verified Contact</span>
                </div>
                <div class="card-text"><strong>Full Name:</strong> {row['name'] or 'N/A'}</div>
                <div class="card-text"><strong>Company:</strong> {row['company'] or 'N/A'}</div>
                <div class="card-text-light" style="margin-top: 5px; color: #4338CA;">
                    <strong>History:</strong> {history_str}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        custom_form_url = booking_url

        st.markdown(
            f"""
            <div class="premium-card">
                <div class="card-header-row">
                    <span class="card-title">Outreach Target</span>
                    <span class="badge badge-drafted">DRAFTED</span>
                </div>
                <div class="card-text"><strong>Recipient:</strong> <code>{row['email']}</code></div>
                <div class="card-text"><strong>Booking:</strong> <a href="{custom_form_url}" target="_blank" style="color: #2563EB; font-weight: 600; text-decoration: underline;">Microsoft Bookings ↗</a></div>
                <div class="card-text-light">Host: <code>bookings.cloud.microsoft</code></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Ensure custom meeting form CTA is included and reflects active URL
    current_body = row["body"] or ""
    current_subject = row["subject"] or ""
    current_subject = current_subject.replace("\ufffd", "-").replace("—", "-").strip()

    if row.get("token"):
        current_body = re.sub(
            r"https?://[^/\"'\s]+/form\?token=" + re.escape(row["token"]),
            custom_form_url,
            current_body,
        )

    if custom_form_url and custom_form_url not in current_body:
        if not current_body.strip().startswith(("<div", "<table", "<html", "<body")):
            link_html = f'<a href="{custom_form_url}" style="color: #2563EB; font-weight: 600; text-decoration: underline;">Schedule a Consultation Call</a>'
            current_body = current_body.rstrip() + f"\n\nSchedule your consultation here: {link_html}"
        else:
            current_body = re.sub(
                r'href="https://www\.nenotechnology\.com"',
                f'href="{custom_form_url}"',
                current_body,
                count=1,
            )

    # Clean any legacy logo tags, boxed wrappers, and consolidate split sentences
    current_body = clean_natural_email_body(current_body)
    if f"body_{row['id']}" in st.session_state:
        st.session_state[f"body_{row['id']}"] = clean_natural_email_body(st.session_state[f"body_{row['id']}"])

    # ── Quick Set Template Option: 7 High-Converting Templates with Batch Apply ──
    available_templates = load_all_templates()
    tpl_by_id = {t["id"]: t for t in available_templates}
    tpl_ids = list(tpl_by_id.keys())

    # Determine default template index from existing lead draft metadata
    current_tpl_id = row.get("template_id")
    default_idx = 0
    if current_tpl_id and current_tpl_id in tpl_ids:
        default_idx = tpl_ids.index(current_tpl_id)

    col_tpl, col_apply_single, col_apply_all = st.columns([3.0, 1.2, 1.6], vertical_alignment="bottom")

    with col_tpl:
        chosen_tpl_id = st.selectbox(
            f"🎯 Select Email Template ({len(tpl_ids)} Available)",
            options=tpl_ids,
            index=default_idx,
            format_func=lambda tid: tpl_by_id[tid]["name"],
            key=f"sel_tpl_{row['id']}",
            help=f"Choose any of the {len(tpl_ids)} high-converting executive outreach templates.",
        )
        chosen_tpl = tpl_by_id[chosen_tpl_id]

    with col_apply_single:
        if st.button(
            "✅ Apply to Lead",
            key=f"btn_apply_curr_{row['id']}",
            help=f"Apply '{chosen_tpl['name']}' to this lead ({row['email']})",
            use_container_width=True,
        ):
            opt_subj, opt_body = render_template(
                chosen_tpl_id,
                lead_name=row.get("name"),
                company=row.get("company"),
                booking_url=custom_form_url,
                tracking_link=custom_form_url,
            )
            opt_subj = opt_subj.replace("\ufffd", "-").replace("—", "-").strip()
            opt_body = clean_natural_email_body(opt_body)
            st.session_state[f"subj_{row['id']}"] = opt_subj
            st.session_state[f"body_{row['id']}"] = opt_body
            db = SessionLocal()
            try:
                update_draft_content(
                    db,
                    row["id"],
                    opt_subj,
                    opt_body,
                    template_id=chosen_tpl["id"],
                    template_name=chosen_tpl["name"],
                )
            finally:
                db.close()
            load_campaign_logs.clear()
            st.cache_data.clear()
            st.toast(f"✅ Applied '{chosen_tpl['name']}' to this lead!", icon="🎯")
            st.rerun()

    with col_apply_all:
        apply_all_label = f"👥 Confirm & Apply to All ({len(drafts)})" if len(drafts) > 1 else "👥 Confirm & Apply to All"
        if st.button(
            apply_all_label,
            key=f"btn_apply_all_{row['id']}",
            type="primary",
            help=f"Apply '{chosen_tpl['name']}' to all {len(drafts)} pending drafts awaiting review",
            use_container_width=True,
        ):
            with st.spinner(f"Applying '{chosen_tpl['name']}' to all {len(drafts)} drafts..."):
                db = SessionLocal()
                try:
                    for _, d_row in drafts.iterrows():
                        d_id = d_row["id"]
                        d_name = d_row.get("name")
                        d_comp = d_row.get("company")
                        t_subj, t_body = render_template(
                            chosen_tpl_id,
                            lead_name=d_name,
                            company=d_comp,
                            booking_url=custom_form_url,
                            tracking_link=custom_form_url,
                        )
                        t_subj = t_subj.replace("\ufffd", "-").replace("—", "-").strip()
                        t_body = clean_natural_email_body(t_body)

                        if d_id == row["id"]:
                            st.session_state[f"subj_{d_id}"] = t_subj
                            st.session_state[f"body_{d_id}"] = t_body
                            # sel_tpl_{row['id']} is already instantiated in this run with chosen_tpl_id
                        else:
                            st.session_state.pop(f"subj_{d_id}", None)
                            st.session_state.pop(f"body_{d_id}", None)
                            st.session_state.pop(f"sel_tpl_{d_id}", None)

                        update_draft_content(
                            db,
                            d_id,
                            t_subj,
                            t_body,
                            template_id=chosen_tpl["id"],
                            template_name=chosen_tpl["name"],
                        )
                    db.commit()
                finally:
                    db.close()
                load_campaign_logs.clear()
                st.cache_data.clear()
                st.toast(f"🚀 Successfully applied '{chosen_tpl['name']}' to all {len(drafts)} drafts!", icon="✅")
                st.rerun()

    accent_color = chosen_tpl.get("accent_color", "#2563EB")
    badge_text = chosen_tpl.get("badge") or chosen_tpl.get("category", "Template")
    st.markdown(
        f"""
        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-left: 4px solid {accent_color}; border-radius: 0 8px 8px 0; padding: 8px 12px; margin: 4px 0 14px 0; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px;">
            <div style="font-size: 12.5px; color: #334155; line-height: 1.45;">
                <strong style="color: #0F172A;">{chosen_tpl['name']}</strong> &nbsp;&bull;&nbsp;
                <span>{chosen_tpl.get('description', '')}</span>
            </div>
            <span style="font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 6px; background: #EFF6FF; color: {accent_color}; border: 1px solid #DBEAFE;">
                {badge_text}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    initial_subj = st.session_state.get(f"subj_{row['id']}", current_subject)
    initial_subj = initial_subj.replace("\ufffd", "-").replace("—", "-").strip()
    edit_subject = st.text_input("Subject Line", value=initial_subj, key=f"subj_{row['id']}")
    edit_body = st.text_area("Email Body (Markdown / HTML)", value=st.session_state.get(f"body_{row['id']}", current_body), height=260, key=f"body_{row['id']}")

    # ── Superhuman / Apple Mail Style Live Preview (Pixel-Perfect Without Extra Space) ──
    st.markdown("##### 👁️ Live Email Client Preview")
    sender_email = get_active_outreach_sender()

    # Outlook Client Header
    from_display_email = chosen_tpl.get("sender_email") or sender_email
    from_display_name = chosen_tpl.get("sender_name") or ("Mohit Patel" if "mohit" in from_display_email.lower() else "Neno Support")
    st.markdown(
        f"""
        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-top-left-radius: 10px; border-top-right-radius: 10px; padding: 12px 16px; border-bottom: 1px solid #CBD5E1;">
            <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 8px;">
                <span style="width: 10px; height: 10px; border-radius: 50%; background: #EF4444; display: inline-block;"></span>
                <span style="width: 10px; height: 10px; border-radius: 50%; background: #F59E0B; display: inline-block;"></span>
                <span style="width: 10px; height: 10px; border-radius: 50%; background: #10B981; display: inline-block;"></span>
                <span style="font-size: 11.5px; color: #64748B; margin-left: 8px; font-weight: 500;">Outlook / Webmail Client View</span>
            </div>
            <div style="font-size: 12.5px; color: #475569; display: flex; flex-direction: column; gap: 3px;">
                <div><strong style="color: #1E293B;">From:</strong> {from_display_name} &lt;{from_display_email}&gt;</div>
                <div><strong style="color: #1E293B;">To:</strong> {row['name'] or 'Lead'} &lt;{row['email']}&gt;</div>
                <div style="font-size: 14px; font-weight: 700; color: #0F172A; margin-top: 3px;">{edit_subject}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Isolated HTML rendering prevents Streamlit markdown parser from injecting paragraphs or extra vertical spacing
    is_html_email = (edit_body or "").strip().startswith(("<!DOCTYPE", "<html", "<table", "<body", "<div"))
    if is_html_email:
        preview_html_payload = edit_body
    else:
        paras = [f"<p style='margin: 0 0 11px 0; padding: 0;'>{p.replace(chr(10), '<br>')}</p>" for p in (edit_body or "").split("\n\n") if p.strip()]
        preview_html_payload = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ margin: 0; padding: 16px 20px; font-family: Arial, Helvetica, sans-serif; font-size: 15px; line-height: 1.45; color: #1a1a1a; background: #ffffff; }}
    p {{ margin: 0 0 11px 0; }}
    a {{ color: #0f62fe; text-decoration: underline; }}
  </style>
</head>
<body>
{''.join(paras)}
</body>
</html>"""

    st.iframe(preview_html_payload, height=650)

    st.markdown("<br>", unsafe_allow_html=True)

    btn1, btn_save, btn2, btn3 = st.columns([1.4, 1.1, 1.2, 1.0])

    with btn1:
        if st.button(
            "🚀 Approve & Send",
            type="primary",
            key=f"app_{row['id']}",
            disabled=already_sent_this_exact_template,
            use_container_width=True,
            help="⚠️ Duplicate: this template was already sent to this lead" if already_sent_this_exact_template else "Send email to this recipient via Microsoft Graph",
        ):
            from services.template_service import interpolate_lead_placeholders
            c_name = str(row.get("name", "")).strip() if row.get("name") and str(row.get("name")).strip().lower() not in ("nan", "none", "") else ""
            f_name = c_name.split()[0].title() if c_name else "there"
            c_comp = str(row.get("company", "")).strip() if row.get("company") and str(row.get("company")).strip().lower() not in ("nan", "none", "") else ""
            comp = c_comp if c_comp else "your team"
            subj_comp = comp if comp != "your team" else "Your Business"
            final_subj = interpolate_lead_placeholders(edit_subject, first_name=f_name, company_name=subj_comp)
            final_body = interpolate_lead_placeholders(edit_body, first_name=f_name, company_name=comp)
            confirm_approve_send_dialog(row["id"], row["email"], final_subj, final_body, sender_email=from_display_email)

    with btn_save:
        if st.button("💾 Save Draft", key=f"save_{row['id']}", use_container_width=True, help="Save changes to database without sending"):
            from services.template_service import interpolate_lead_placeholders
            c_name = str(row.get("name", "")).strip() if row.get("name") and str(row.get("name")).strip().lower() not in ("nan", "none", "") else ""
            f_name = c_name.split()[0].title() if c_name else "there"
            c_comp = str(row.get("company", "")).strip() if row.get("company") and str(row.get("company")).strip().lower() not in ("nan", "none", "") else ""
            comp = c_comp if c_comp else "your team"
            subj_comp = comp if comp != "your team" else "Your Business"
            final_subj = interpolate_lead_placeholders(edit_subject, first_name=f_name, company_name=subj_comp)
            final_body = interpolate_lead_placeholders(edit_body, first_name=f_name, company_name=comp)
            db = SessionLocal()
            update_draft_content(db, row["id"], final_subj, final_body)
            db.close()
            st.success("Draft saved successfully!")
            st.cache_data.clear()
            st.rerun()

    with btn2:
        if st.button("🪄 Regenerate Draft", key=f"regen_{row['id']}", use_container_width=True):
            try:
                new_subj, new_body = compose_email(
                    name=row["name"],
                    company=row["company"],
                    tracking_link=custom_form_url,
                )
                db = SessionLocal()
                update_draft_content(db, row["id"], new_subj, new_body)
                db.close()
                st.success("Draft regenerated successfully with Gemini AI!")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Regeneration failed: {e}")

    with btn3:
        if st.button("✕ Reject Draft", key=f"rej_{row['id']}", use_container_width=True):
            db = SessionLocal()
            reject_entry(db, row["id"])
            db.close()
            st.info("Draft rejected.")
            st.cache_data.clear()
            st.rerun()

    # ─────────────────────────────────────────────────────────────
    # BATCH OPERATIONS & BULK DISPATCH CENTER (PLACED AT BOTTOM)
    # ─────────────────────────────────────────────────────────────
    # BULK APPROVE & SEND (THREE BUTTONS ONLY)
    # ─────────────────────────────────────────────────────────────
    st.markdown("<hr style='border: 0; border-top: 1px solid #E2E8F0; margin: 32px 0 16px 0;'>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <div style="font-size: 15px; font-weight: 700; color: #0F172A; display: flex; align-items: center; gap: 8px;">
                <span>⚡</span> <span>Bulk Approve &amp; Send Remaining ({pending_count} Leads)</span>
            </div>
            <span class="badge badge-drafted" style="font-size: 11px; padding: 3px 10px; font-weight: 600;">{pending_count} Leads Ready</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    bulk_col1, bulk_col2 = st.columns([2.8, 1.4])
    with bulk_col1:
        if st.button(
            f"🚀 Bulk Approve & Send All ({pending_count} Leads)",
            key="bulk_send_opt1",
            type="primary",
            use_container_width=True,
            help="Approve and send all remaining drafts using their reviewed templates & customized messaging",
        ):
            confirm_approve_all_dialog(drafts.to_dict("records"))

    with bulk_col2:
        if st.button(
            f"✕ Reject All Drafts ({pending_count})",
            key="bulk_reject_all_opt",
            use_container_width=True,
            help="Reject and delete all remaining pending drafts without sending emails",
        ):
            confirm_reject_all_dialog(drafts.to_dict("records"))








# ─────────────────────────────────────────────────────────────
# PAGE 5: REPLIES & BOOKINGS
# ─────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────
# HELPERS FOR REPLIES & BOOKINGS
# ─────────────────────────────────────────────────────────────
def format_datetime_str(ts_val) -> str:
    if ts_val is None or pd.isna(ts_val):
        return "—"
    s = str(ts_val).strip()
    if not s or s.lower() in ("nan", "none", "nat", ""):
        return "—"
    try:
        dt = datetime.fromisoformat(s)
        return dt.strftime("%b %d, %Y · %I:%M %p")
    except Exception:
        pass
    for fmt in (
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(s.split("+")[0].strip(), fmt)
            return dt.strftime("%b %d, %Y · %I:%M %p")
        except Exception:
            pass
    return s


def format_booking_status(status_str) -> tuple[str, str]:
    raw = str(status_str or "pending").strip().lower()
    if raw in ("confirmation_sent", "confirmed", "meeting_scheduled", "scheduled"):
        return "Confirmed & Sent", "badge-sent"
    elif raw in ("pending", "form_submitted", "submitted"):
        return "Pending Review", "badge-pending"
    elif raw in ("reschedule", "rescheduled"):
        return "Reschedule Requested", "badge-drafted"
    elif raw in ("cancelled", "rejected", "failed"):
        return "Cancelled", "badge-rejected"
    return raw.replace("_", " ").title(), "badge-pending"


def get_lead_initials(name: str) -> str:
    if not name or pd.isna(name):
        return "LD"
    parts = str(name).strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    elif len(parts) == 1 and parts[0]:
        return parts[0][:2].upper()
    return "LD"


def parse_customer_reply_text(text: str) -> tuple[str, str]:
    if not text:
        return "", ""
    s = str(text).strip()
    match = re.search(r"(On\s+[A-Za-z]+,\s+[A-Za-z]+\s+\d+.*wrote\s*:.*)", s, flags=re.DOTALL | re.IGNORECASE)
    if match:
        main_reply = s[:match.start()].strip()
        quoted = match.group(1).strip()
        return main_reply or s, quoted
    return s, ""


def clean_html(html_str: str) -> str:
    if not html_str:
        return ""
    return "".join(line.strip() for line in str(html_str).strip().splitlines() if line.strip())


# ─────────────────────────────────────────────────────────────
# PAGE 5: REPLIES & BOOKINGS
# ─────────────────────────────────────────────────────────────
def format_reply_intent(intent_raw: str) -> tuple[str, str]:
    raw = (intent_raw or "positive_acknowledgement").lower().strip()
    if "positive" in raw or "ack" in raw or "courtesy" in raw:
        return "🤝 Positive Reply", "badge-sent"
    elif "interest" in raw and "not" not in raw:
        return "🎯 Interested", "badge-sent"
    elif "meeting" in raw:
        return "🗓️ Meeting Request", "badge-scheduled"
    elif "reschedule" in raw:
        return "⏱️ Reschedule", "badge-drafted"
    elif "not" in raw or "opt" in raw or "unsub" in raw:
        return "🛑 Opted Out", "badge-rejected"
    return "❓ Inquiry / Question", "badge-pending"


def render_replies(df: pd.DataFrame) -> None:
    import html
    render_top_banner(
        "Replies & Consultation Bookings",
        "AI Auto-Reply Agent, inbound email conversations, customer appointment submissions, and permanent Excel sheets.",
        "CRM & Intelligence",
    )

    # ── AI Auto-Reply Agent Control Center & Dynamic RAG Knowledge Status ──
    is_monitoring = ReplyDaemonManager.is_running()
    status_label = "Active & Monitoring Inbox (30s)" if is_monitoring else "Idle / On-Demand Mode"
    status_badge_cls = "badge-sent" if is_monitoring else "badge-pending"
    status_dot_color = "#10B981" if is_monitoring else "#94A3B8"

    kb_summary = fetch_cached_kb_summary()

    kb_chunks = kb_summary.get("total_chunks", 0)
    kb_docs_count = kb_summary.get("total_documents", 0)

    if kb_chunks > 0:
        kb_badge_html = f'<span class="badge badge-scheduled" style="font-size: 11px;">📚 Grounded in RAG Knowledge Base ({kb_docs_count} Docs · {kb_chunks} Chunks)</span>'
    else:
        kb_badge_html = '<span class="badge badge-pending" style="font-size: 11px;">⚠️ RAG Knowledge Empty (0 Chunks) · Attach Files in Tab Below</span>'

    agent_status_html = f"""
    <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 12px; padding: 18px 22px; margin-bottom: 18px; box-shadow: var(--shadow-sm); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px;">
        <div style="display: flex; align-items: center; gap: 14px;">
            <div style="width: 44px; height: 44px; border-radius: 12px; background: var(--brand-soft); color: var(--brand-primary); display: flex; align-items: center; justify-content: center; font-size: 22px; border: 1px solid var(--brand-border);">
                🤖
            </div>
            <div>
                <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                    <span style="font-size: 16px; font-weight: 700; color: var(--text-primary); font-family: 'Outfit', sans-serif;">AI Auto-Reply Agent</span>
                    <span class="badge {status_badge_cls}" style="font-size: 11px;">
                        <span style="display: inline-block; width: 7px; height: 7px; border-radius: 50%; background-color: {status_dot_color}; margin-right: 5px;"></span>
                        {status_label}
                    </span>
                    {kb_badge_html}
                </div>
                <div style="font-size: 13px; color: var(--text-muted); margin-top: 3px; font-family: 'Inter', sans-serif;">
                    Monitors <code>{os.getenv('MS_SENDER_EMAIL', 'mohit@nenotechnology.us')}</code> inbox · Auto-activates only on customer reply · Answers via RAG vector intelligence
                </div>
            </div>
        </div>
    </div>
    """
    st.markdown(agent_status_html, unsafe_allow_html=True)

    toolbar_col1, toolbar_col2, toolbar_col3 = st.columns([2.2, 2.2, 1.2])
    with toolbar_col1:
        if st.button("⚡ Check Inbox & Auto-Reply Now", type="primary", use_container_width=True, key="btn_check_inbox_now"):
            with st.spinner("Scanning Outlook inbox for unread customer replies (Strict Real-Data Mode)..."):
                summary = check_and_reply_inbox(sync_existing=False)
                st.cache_data.clear()
            if summary.get("message"):
                st.warning(f"ℹ️ {summary['message']}")
            elif summary["replied_count"] > 0:
                st.success(f"✅ Dispatched {summary['replied_count']} AI replies grounded in Neno Technology Knowledge Base (PDF)!")
            elif summary.get("bookings_synced", 0) > 0:
                st.success(f"📅 Synced {summary['bookings_synced']} Microsoft Bookings consultation appointments!")
            elif summary["processed_count"] == 0:
                st.info("No unread customer replies from outreach leads in inbox. System is up to date!")
            else:
                st.info(f"Processed {summary['processed_count']} messages ({summary['skipped_count']} skipped/non-campaign senders).")
            st.rerun()


    with toolbar_col2:
        if is_monitoring:
            if st.button("⏹️ Stop Background Monitor", key="btn_toggle_daemon", use_container_width=True):
                ReplyDaemonManager.stop()
                st.toast("Background auto-reply monitor stopped.", icon="⏹️")
                st.rerun()
        else:
            if st.button("▶️ Start Background Monitor", key="btn_toggle_daemon", use_container_width=True):
                ReplyDaemonManager.start(interval_seconds=30)
                st.toast("AI Auto-Reply Agent is now actively monitoring the inbox every 30s!", icon="🟢")
                st.rerun()

    with toolbar_col3:
        if st.button("🔄 Refresh Data", key="btn_refresh_replies", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # ── Reconcile Customer Replies from Excel and DB (Strict Real-Reply Filter) ──
    all_replies = []
    seen_emails = set()

    if os.path.exists(DEFAULT_REPLIES_EXCEL):
        try:
            excel_r_df = get_cached_excel_df(DEFAULT_REPLIES_EXCEL)
            for _, r in excel_r_df.iterrows():
                em = str(r.get("email") or "").strip().lower()
                cust_reply = str(r.get("customer_reply") or "").strip()
                ai_reply = extract_text_from_ai_message(str(r.get("ai_response_sent") or "")).strip()
                # Strict: must have an actual customer reply or AI reply text
                if em and (cust_reply or ai_reply) and em not in seen_emails and "microsoftexchange" not in em and "postmaster" not in em:
                    seen_emails.add(em)
                    all_replies.append({
                        "email": em,
                        "name": str(r.get("name") or "").strip() if pd.notna(r.get("name")) and str(r.get("name")).strip() else "Customer",
                        "company": str(r.get("company") or "").strip() if pd.notna(r.get("company")) and str(r.get("company")).strip() else "—",
                        "reply_intent": str(r.get("reply_intent") or "question").strip(),
                        "customer_reply": cust_reply,
                        "ai_response_sent": ai_reply,
                        "reply_received_at": str(r.get("reply_received_at") or "").strip() if pd.notna(r.get("reply_received_at")) else "",
                        "ai_reply_sent_at": str(r.get("ai_reply_sent_at") or "").strip() if pd.notna(r.get("ai_reply_sent_at")) else "",
                    })
        except Exception:
            pass

    if not df.empty:
        # Strict filter: Lead MUST have actual non-empty reply text or AI reply text or received reply timestamp with valid replied status!
        has_reply_body = df["reply_body"].fillna("").astype(str).str.strip().ne("")
        has_ai_reply = df["ai_reply_sent"].fillna("").astype(str).str.strip().ne("")
        has_valid_received = (
            df["reply_received_at"].notna()
            & df["reply_received_at"].astype(str).str.strip().ne("")
            & df["reply_received_at"].astype(str).str.strip().ne("None")
        )
        has_replied_status = df["status"].astype(str).str.strip().str.lower().isin(["replied", "form_submitted", "scheduled"])

        r_rows = df[(has_reply_body | has_ai_reply | (has_valid_received & has_replied_status))]
        for _, r in r_rows.iterrows():
            em = str(r.get("email") or "").strip().lower()
            cust_reply = str(r.get("reply_body") or "").strip()
            ai_reply = extract_text_from_ai_message(str(r.get("ai_reply_sent") or "")).strip()
            # Double safety guard: must have actual message content to show in Conversation Cards
            if not cust_reply and not ai_reply:
                continue
            if em and em not in seen_emails and "microsoftexchange" not in em and "postmaster" not in em:
                seen_emails.add(em)
                all_replies.append({
                    "email": em,
                    "name": str(r.get("name") or "").strip() if pd.notna(r.get("name")) and str(r.get("name")).strip() else "Customer",
                    "company": str(r.get("company") or "").strip() if pd.notna(r.get("company")) and str(r.get("company")).strip() else "—",
                    "reply_intent": str(r.get("reply_intent") or "question").strip(),
                    "customer_reply": cust_reply,
                    "ai_response_sent": ai_reply,
                    "reply_received_at": str(r.get("reply_received_at") or "").strip() if pd.notna(r.get("reply_received_at")) else "",
                    "ai_reply_sent_at": str(r.get("ai_reply_sent_at") or "").strip() if pd.notna(r.get("ai_reply_sent_at")) else "",
                })

    # ── Summary KPI Calculations ──
    booked_leads_count = 0
    if os.path.exists(DEFAULT_BOOKED_EXCEL):
        try:
            excel_df = get_cached_excel_df(DEFAULT_BOOKED_EXCEL)
            booked_leads_count = len(excel_df)
        except Exception:
            booked_leads_count = 0

    db_forms = int(df["form_filled_at"].notna().sum()) if not df.empty and "form_filled_at" in df.columns else 0
    forms_count = max(db_forms, booked_leads_count)
    db_meetings = int(df["booking_status"].isin(["scheduled", "meeting_scheduled", "confirmation_sent", "confirmed"]).sum()) if not df.empty and "booking_status" in df.columns else 0
    meetings_count = max(db_meetings, booked_leads_count)
    replies_count = len(all_replies)
    total_archive_records = booked_leads_count + replies_count

    # ── Executive 4-Card KPI Grid ──
    st.markdown(
        clean_html(
            f"""
            <div class="kpi-grid-4">
                <div class="kpi-card">
                    <div class="kpi-top-bar kpi-bar-teal"></div>
                    <div class="kpi-header">
                        <span class="kpi-label">Customer Replies</span>
                        <div class="kpi-icon-box" style="background: #F0FDFA; color: #0D9488;">💬</div>
                    </div>
                    <div class="kpi-value">{replies_count}</div>
                    <div class="kpi-micro">
                        <span class="kpi-pill kpi-pill-teal">AI Answered</span>
                        <span>Knowledge Grounded</span>
                    </div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-top-bar kpi-bar-purple"></div>
                    <div class="kpi-header">
                        <span class="kpi-label">Forms Completed</span>
                        <div class="kpi-icon-box" style="background: #F5F3FF; color: #7C3AED;">📋</div>
                    </div>
                    <div class="kpi-value">{forms_count}</div>
                    <div class="kpi-micro">
                        <span class="kpi-pill kpi-pill-purple">Verified Forms</span>
                        <span>Client submissions</span>
                    </div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-top-bar kpi-bar-rose"></div>
                    <div class="kpi-header">
                        <span class="kpi-label">Meetings Confirmed</span>
                        <div class="kpi-icon-box" style="background: #FFF1F2; color: #E11D48;">🗓️</div>
                    </div>
                    <div class="kpi-value">{meetings_count}</div>
                    <div class="kpi-micro">
                        <span class="kpi-pill kpi-pill-rose">Teams Ready</span>
                        <span>Dispatched invites</span>
                    </div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-top-bar kpi-bar-blue"></div>
                    <div class="kpi-header">
                        <span class="kpi-label">Permanent Archive</span>
                        <div class="kpi-icon-box" style="background: #EFF6FF; color: #2563EB;">📗</div>
                    </div>
                    <div class="kpi-value">{total_archive_records}</div>
                    <div class="kpi-micro">
                        <span class="kpi-pill kpi-pill-blue">Excel Synced</span>
                        <span>{replies_count} Replies · {booked_leads_count} Bookings</span>
                    </div>
                </div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )

    col_sync1, col_sync2 = st.columns([8, 4])
    with col_sync1:
        st.markdown(
            clean_html(
                """
                <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 8px 14px; margin-bottom: 8px; box-shadow: var(--shadow-sm);">
                    <div style="font-size: 12.5px; color: var(--text-secondary); font-family: 'Inter', sans-serif;">
                        <span style="font-weight: 600; color: var(--text-primary);">🔗 Live Data Pipeline:</span>
                        <span>Synchronizing <strong>Outlook</strong> (Replies) &amp; <strong>Excel</strong> (<code>booked_leads.xlsx</code> via Power Automate &rarr; Odoo CRM) into <strong>Dashboard &amp; Analytics</strong>.</span>
                    </div>
                </div>
                """
            ),
            unsafe_allow_html=True,
        )
    with col_sync2:
        if st.button("🔄 Sync Outlook & Excel Now", key="btn_sync_outlook_excel", use_container_width=True):
            with st.spinner("Syncing latest bookings and replies from Excel & Outlook..."):
                from Backend.crud import sync_excel_and_outlook_to_db
                db_sync = SessionLocal()
                s_res = sync_excel_and_outlook_to_db(db_sync)
                db_sync.close()
                st.cache_data.clear()
            st.toast(f"✅ Synced {s_res.get('synced_bookings', 0)} bookings and {s_res.get('synced_replies', 0)} replies!", icon="🔄")
            st.rerun()

    tab_replies_stream, tab_rag_hub, tab_bookings_stream, tab_excel_stream = st.tabs([
        f"💬 Customer Inquiries & AI Auto-Replies ({replies_count})",
        f"📚 RAG Knowledge Base & Attachments ({kb_chunks} Chunks)",
        f"📋 Customer Consultation Form Submissions ({forms_count})",
        f"📗 Permanent Excel Archives ({total_archive_records})",
    ])

    # ═══════════════════════════════════════════════════════════════
    # TAB 1: CUSTOMER INQUIRIES & AI AUTO-REPLIES
    # ═══════════════════════════════════════════════════════════════
    with tab_replies_stream:
        if not all_replies:
            st.markdown(
                clean_html(
                    f"""
                    <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 14px; padding: 36px 24px; text-align: center; margin-top: 14px; box-shadow: var(--shadow-sm);">
                        <div style="width: 52px; height: 52px; border-radius: 14px; background: var(--brand-soft); color: var(--brand-primary); font-size: 26px; display: flex; align-items: center; justify-content: center; margin: 0 auto 14px auto; border: 1px solid var(--brand-border);">
                            💬
                        </div>
                        <h3 style="margin: 0 0 6px 0; font-size: 18px; font-weight: 700; color: var(--text-primary); font-family: 'Outfit', sans-serif;">
                            No Customer Replies Recorded Yet
                        </h3>
                        <p style="margin: 0 auto 20px auto; max-width: 540px; font-size: 13.5px; color: var(--text-muted); line-height: 1.55; font-family: 'Inter', sans-serif;">
                            The AI Auto-Reply Agent is actively monitoring your outreach campaign inbox. Once a customer replies, their conversation thread and grounded corporate response will immediately appear here.
                        </p>
                    </div>
                    """
                ),
                unsafe_allow_html=True,
            )
            col_sb1, col_sb2, col_sb3 = st.columns([1.2, 2.2, 1.2])
            with col_sb2:
                if st.button("⚡ Scan Outlook Inbox for New Replies", key="btn_standby_check", type="primary", use_container_width=True):
                    with st.spinner("Checking Outlook inbox for customer replies..."):
                        check_and_reply_inbox(sync_existing=False)
                        st.cache_data.clear()
                    st.rerun()
        else:
            rc_col1, rc_col2 = st.columns([3, 1.3])
            with rc_col1:
                reply_search = st.text_input(
                    "Search Customer Replies",
                    placeholder="🔍 Search by customer name, email, company, or message content...",
                    label_visibility="collapsed",
                    key="reply_search_filter",
                )
            with rc_col2:
                intent_filter_opts = ["All Intents", "Positive Reply", "Interested", "Question / Inquiry", "Meeting Request", "Reschedule", "Opted Out"]
                intent_sel = st.selectbox(
                    "Filter by Intent",
                    intent_filter_opts,
                    label_visibility="collapsed",
                    key="reply_intent_sel",
                )

            filtered_replies = all_replies.copy()
            if reply_search:
                q_low = reply_search.strip().lower()
                filtered_replies = [
                    r for r in filtered_replies
                    if any(q_low in str(r.get(f, "")).lower() for f in ["email", "name", "company", "customer_reply", "ai_response_sent"])
                ]

            if intent_sel != "All Intents":
                intent_map = {
                    "Positive Reply": "positive_acknowledgement",
                    "Interested": "interested",
                    "Question / Inquiry": "question",
                    "Meeting Request": "meeting_request",
                    "Reschedule": "reschedule",
                    "Opted Out": "not_interested",
                }
                target_intent = intent_map.get(intent_sel, "")
                if target_intent:
                    filtered_replies = [r for r in filtered_replies if target_intent in r.get("reply_intent", "").lower()]

            st.caption(f"Showing **{len(filtered_replies)}** of **{len(all_replies)}** customer conversation threads:")

            tab_deck, tab_reply_table = st.tabs(["🎴 Executive Conversation Cards", "📊 Clean Data Grid"])

            with tab_deck:
                if not filtered_replies:
                    st.warning("No conversation records match your search filter.")
                else:
                    for item in filtered_replies:
                        initials = get_lead_initials(item["name"])
                        intent_label, badge_cls = format_reply_intent(item["reply_intent"])
                        fmt_received = format_datetime_str(item["reply_received_at"])
                        fmt_sent = format_datetime_str(item["ai_reply_sent_at"])

                        customer_msg_clean = item["customer_reply"] or "(No text preview)"
                        ai_reply_clean = extract_text_from_ai_message(item["ai_response_sent"]) or "(No AI reply recorded)"

                        st.markdown(
                            f"""
                            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px; padding: 22px 24px; margin-bottom: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.04);">
                                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; flex-wrap: wrap; gap: 10px;">
                                    <div style="display: flex; align-items: center; gap: 12px;">
                                        <div class="booking-avatar">{initials}</div>
                                        <div>
                                            <div style="font-size: 16px; font-weight: 700; color: #0F172A;">{item['name']}</div>
                                            <div style="font-size: 13px; color: #64748B;">🏢 {item['company']} &nbsp;·&nbsp; ✉️ <a href="mailto:{item['email']}" style="color: #2563EB; text-decoration: none;">{item['email']}</a></div>
                                        </div>
                                    </div>
                                    <div style="display: flex; align-items: center; gap: 8px;">
                                        <span class="badge {badge_cls}" style="font-size: 12px; padding: 4px 10px;">{intent_label}</span>
                                        <span class="badge badge-sent" style="font-size: 11px;">Auto-Replied via Outlook</span>
                                    </div>
                                </div>
                                <!-- Inbound customer message -->
                                <div class="chat-bubble-inbound">
                                    <div class="chat-bubble-sender">
                                        <span style="color: #475569; font-weight: 600;">🗨️ Customer Inquiry / Reply:</span>
                                        <span style="color: #94A3B8; font-family: 'JetBrains Mono', monospace; font-size: 11px;">Received {fmt_received}</span>
                                    </div>
                                    <div class="chat-bubble-text">{customer_msg_clean}</div>
                                </div>
                                <!-- Outbound AI knowledge-grounded response -->
                                <div class="chat-bubble-outbound">
                                    <div class="chat-bubble-sender">
                                        <span style="color: #0F766E; font-weight: 600;">🤖 AI Knowledge-Grounded Auto-Reply:</span>
                                        <span style="color: #0D9488; font-family: 'JetBrains Mono', monospace; font-size: 11px;">Sent {fmt_sent}</span>
                                    </div>
                                    <div class="chat-bubble-text">{ai_reply_clean}</div>
                                    <div style="margin-top: 12px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                                        <span class="badge badge-scheduled" style="font-size: 10.5px;">📚 Grounded in Attached RAG Knowledge Base ({kb_chunks} Chunks)</span>
                                        <span class="badge badge-sent" style="font-size: 10.5px;">✓ Dispatched via Microsoft Graph ({os.getenv('MS_SENDER_EMAIL', 'mohit@nenotechnology.us')})</span>
                                    </div>
                                    <div style="margin-top: 12px;">
                                        <a href="https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled" target="_blank"
                                           style="background: #2563EB; color: #FFFFFF; padding: 6px 14px; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: 600; display: inline-block;">
                                           📅 Microsoft Bookings: Schedule Consultation Call
                                        </a>
                                    </div>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        with st.expander(f"📧 View Outbound Email Thread with Quoted Primary Mail ({item['name']})", expanded=False):
                            st.markdown(
                                f"""
                                <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 18px; font-family: Arial, sans-serif; font-size: 13.5px; color: #1E293B;">
                                    <div style="margin-bottom: 12px; font-size: 13px; font-weight: 700; color: #0F172A;">
                                        Subject: Re: Consultation & Intelligence
                                    </div>
                                    <div style="white-space: pre-wrap; line-height: 1.6; margin-bottom: 14px;">{ai_reply_clean}</div>
                                    <div style="margin-top: 16px; padding-top: 12px; border-top: 1px solid #CBD5E1; font-size: 12px; color: #64748B; line-height: 1.5;">
                                        <b>From:</b> {item['name']} &lt;{item['email']}&gt;<br>
                                        <b>Sent:</b> {fmt_received}<br>
                                        <b>To:</b> Team &lt;{os.getenv('MS_SENDER_EMAIL', 'mohit@nenotechnology.us')}&gt;<br>
                                        <b>Subject:</b> Inquiry / Reply
                                    </div>
                                    <div style="border-left: 3px solid #CBD5E1; padding-left: 12px; margin-top: 8px; color: #475569; font-size: 13px; line-height: 1.5;">
                                        {customer_msg_clean}
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

            with tab_reply_table:
                r_table_df = pd.DataFrame(filtered_replies)
                if not r_table_df.empty:
                    display_cols = [c for c in ["email", "name", "company", "reply_intent", "customer_reply", "ai_response_sent", "reply_received_at", "ai_reply_sent_at"] if c in r_table_df.columns]
                    st.dataframe(
                        r_table_df[display_cols],
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "email": st.column_config.TextColumn("Customer Email", width="medium"),
                            "name": st.column_config.TextColumn("Name", width="small"),
                            "company": st.column_config.TextColumn("Company", width="small"),
                            "reply_intent": st.column_config.TextColumn("Detected Intent", width="small"),
                            "customer_reply": st.column_config.TextColumn("Customer Message", width="large"),
                            "ai_response_sent": st.column_config.TextColumn("AI Response Sent", width="large"),
                            "reply_received_at": st.column_config.TextColumn("Received At", width="medium"),
                            "ai_reply_sent_at": st.column_config.TextColumn("Sent At", width="medium"),
                        },
                    )

    # ═══════════════════════════════════════════════════════════════
    # TAB 2: RAG KNOWLEDGE BASE & ATTACHMENTS
    # ═══════════════════════════════════════════════════════════════
    with tab_rag_hub:
        st.markdown(
            clean_html(
                """
                <div style="margin-top: 6px; margin-bottom: 16px;">
                    <h3 style="margin: 0; font-size: 18px; font-weight: 600; display: flex; align-items: center; gap: 8px;">
                        <span>📚</span> RAG Knowledge Base & Document Attachments
                    </h3>
                    <p style="margin: 2px 0 0 0; font-size: 13px; color: var(--text-muted);">
                        Attach company PDFs, pitch decks, FAQs, or service guides. When a customer replies, the AI Auto-Reply Agent strictly retrieves relevant facts from these documents to answer with 100% accuracy.
                    </p>
                </div>
                """
            ),
            unsafe_allow_html=True,
        )

        # Knowledge Base KPI summary grid
        rag_kpi_html = f"""
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; margin-bottom: 20px;">
            <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 10px; padding: 16px; border-left: 4px solid #0D9488; box-shadow: var(--shadow-sm);">
                <div style="font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em;">Indexed Knowledge Chunks</div>
                <div style="font-size: 26px; font-weight: 800; color: var(--text-primary); margin: 4px 0; font-family: 'JetBrains Mono', monospace;">{kb_chunks}</div>
                <div style="font-size: 12px; color: var(--teal-primary); font-weight: 600;">Active in RAG Vector Memory</div>
            </div>
            <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 10px; padding: 16px; border-left: 4px solid var(--brand-primary); box-shadow: var(--shadow-sm);">
                <div style="font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em;">Source Documents</div>
                <div style="font-size: 26px; font-weight: 800; color: var(--text-primary); margin: 4px 0; font-family: 'JetBrains Mono', monospace;">{kb_docs_count}</div>
                <div style="font-size: 12px; color: var(--brand-primary); font-weight: 600;">Attached Files (PDF / MD / TXT)</div>
            </div>
            <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 10px; padding: 16px; border-left: 4px solid var(--purple-primary); box-shadow: var(--shadow-sm);">
                <div style="font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em;">Embedding Engine</div>
                <div style="font-size: 14px; font-weight: 700; color: var(--text-primary); margin: 8px 0 4px 0;">Gemini Embeddings</div>
                <div style="font-size: 12px; color: var(--text-muted);">Normalized Dense Vectors</div>
            </div>
            <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 10px; padding: 16px; border-left: 4px solid var(--amber-primary); box-shadow: var(--shadow-sm);">
                <div style="font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em;">Retrieval Algorithm</div>
                <div style="font-size: 14px; font-weight: 700; color: var(--text-primary); margin: 8px 0 4px 0;">Cosine Similarity</div>
                <div style="font-size: 12px; color: var(--text-muted);">Strict Min-Score 0.35 Filter</div>
            </div>
        </div>
        """
        st.markdown(rag_kpi_html, unsafe_allow_html=True)

        # Upload / Attach File Section
        st.markdown("#### 📤 Attach New Knowledge Base Document")
        up_col1, up_col2 = st.columns([3, 1.2])
        with up_col1:
            uploaded_rag_file = st.file_uploader(
                "Upload Document (.pdf, .md, .txt)",
                type=["pdf", "md", "txt"],
                key="rag_knowledge_uploader",
                help="Upload company sales decks, technical specifications, service outlines, or FAQs.",
            )
        with up_col2:
            custom_doc_title = st.text_input(
                "Document Title (Optional)",
                placeholder="e.g. Capabilities 2026",
                key="rag_doc_custom_title",
            )
            ingest_btn = st.button("📥 Ingest & Attach to RAG Memory", type="primary", use_container_width=True, disabled=(uploaded_rag_file is None), key="btn_ingest_rag_doc")

        if ingest_btn and uploaded_rag_file is not None:
            with st.spinner(f"Extracting text, chunking, and computing Gemini embeddings for '{uploaded_rag_file.name}'..."):
                kb_save_dir = os.path.join(os.path.dirname(__file__), "knowledge_base")
                os.makedirs(kb_save_dir, exist_ok=True)
                saved_path = os.path.join(kb_save_dir, uploaded_rag_file.name)
                file_bytes = uploaded_rag_file.getvalue()
                with open(saved_path, "wb") as f_out:
                    f_out.write(file_bytes)

                db_ingest = SessionLocal()
                try:
                    num_chunks = ingest_file_content(
                        db=db_ingest,
                        filename=uploaded_rag_file.name,
                        file_bytes_or_content=file_bytes,
                        title=custom_doc_title.strip() if custom_doc_title else None,
                    )
                finally:
                    db_ingest.close()
                st.cache_data.clear()
                fetch_cached_kb_summary.clear()
            st.success(f"✅ Successfully attached and indexed '{uploaded_rag_file.name}' into RAG memory ({num_chunks} vector chunks created)!")
            st.rerun()

        # Workspace Knowledge Sync & Management Button
        st.markdown("<hr style='margin: 18px 0; border: none; border-top: 1px solid var(--border-subtle);'>", unsafe_allow_html=True)
        sync_col1, sync_col2 = st.columns([3, 1.2])
        with sync_col1:
            if kb_chunks == 0:
                st.info("💡 **Clean State**: Vector memory is clean (0 Chunks). Upload your PDF, Markdown, or text documentation above to index knowledge for the AI reply agent.")
            else:
                st.caption(f"Knowledge base has **{kb_chunks}** active chunks across **{kb_docs_count}** document(s). You can index more files or manage them below.")
        with sync_col2:
            if kb_chunks > 0:
                if st.button("🗑️ Purge All RAG Documents", key="btn_purge_kb_docs", use_container_width=True, type="secondary"):
                    from services.rag import clear_all_knowledge_documents
                    db_p = SessionLocal()
                    try:
                        clear_all_knowledge_documents(db_p)
                    finally:
                        db_p.close()
                    st.cache_data.clear()
                    fetch_cached_kb_summary.clear()
                    st.toast("✅ All RAG documents cleared to 0 chunks!", icon="🗑️")
                    st.rerun()

        # Currently Attached Documents List
        st.markdown("#### 📑 Active Attached Knowledge Documents")
        docs_list = kb_summary.get("documents", [])
        if not docs_list:
            st.info("No documents indexed in vector memory yet. Upload your PDF or text document above to ground the AI assistant.")
        else:
            for doc in docs_list:
                d_title = doc.get("title", "Untitled")
                d_chunks = doc.get("chunks", 0)
                d_preview = doc.get("preview", "")
                d_cat = doc.get("category") or "Documentation"

                card_html = f"""
                <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 10px; padding: 14px 18px; margin-bottom: 10px; box-shadow: var(--shadow-sm); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                    <div>
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span style="font-size: 15px; font-weight: 700; color: var(--text-primary);">📄 {d_title}</span>
                            <span class="badge badge-scheduled" style="font-size: 11px;">{d_cat}</span>
                            <span class="badge badge-sent" style="font-size: 11px;">{d_chunks} Chunks Embedded</span>
                        </div>
                        <div style="font-size: 12.5px; color: var(--text-muted); margin-top: 4px; max-width: 750px;">
                            {html.escape(d_preview[:180])}...
                        </div>
                    </div>
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)

        # Interactive RAG Playground
        st.markdown("<hr style='margin: 22px 0; border: none; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)
        st.markdown("#### 🧪 Interactive RAG Grounding Playground")
        st.caption("Simulate a customer question to test which knowledge chunks are retrieved and how the agent composes a factual, grounded response.")

        q_col1, q_col2 = st.columns([3.5, 1.2])
        with q_col1:
            test_query = st.text_input(
                "Simulate Inbound Customer Question",
                value="Do you guys build custom web platforms and provide Forward-Deployed Engineering? How do we get started?",
                key="rag_test_query_input",
            )
        with q_col2:
            test_rag_btn = st.button("🔍 Test RAG Retrieval & AI Draft", type="primary", use_container_width=True, key="btn_run_rag_test")

        if test_rag_btn and test_query:
            with st.spinner("Embedding query and querying vector memory with cosine similarity..."):
                db_test = SessionLocal()
                try:
                    retrieved = retrieve_relevant_chunks(db_test, query=test_query, top_k=4, min_score=0.35)
                    test_agent_res = process_incoming_reply(
                        db=db_test,
                        from_email="inquiry@client.com",
                        from_name="Prospective Client",
                        company="Client Enterprise",
                        subject="Inquiry: Services & Engineering",
                        raw_body=test_query,
                    )
                finally:
                    db_test.close()

            t_res_col1, t_res_col2 = st.columns([1.2, 1.8])
            with t_res_col1:
                st.markdown(f"**Retrieved Knowledge Chunks ({len(retrieved)}):**")
                if not retrieved:
                    st.warning("No chunks cleared the relevance threshold (0.35). General Nenotechnology core capabilities will be used.")
                else:
                    for idx, c in enumerate(retrieved, 1):
                        score = c.get("score", 0)
                        score_pct = int(score * 100)
                        pill_cls = "badge-sent" if score >= 0.50 else "badge-pending"
                        st.markdown(
                            f"""
                            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px 12px; margin-bottom: 8px; font-size: 12px;">
                                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                    <span style="font-weight: 700; color: #1E293B;">Chunk #{idx} · {c.get('title', 'KB')}</span>
                                    <span class="badge {pill_cls}" style="font-size: 10px;">{score_pct}% Match</span>
                                </div>
                                <div style="color: #475569; font-size: 11.5px; line-height: 1.4;">{html.escape(c.get('content', '')[:160])}...</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

            with t_res_col2:
                st.markdown(f"**Grounded AI Draft Response (Intent: `{test_agent_res.get('intent', 'question')}`):**")
                draft_preview = test_agent_res.get("response_text", "")
                st.markdown(
                    f"""
                    <div style="background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 10px; padding: 16px; font-size: 13px; color: #0F172A; line-height: 1.6; white-space: pre-wrap; max-height: 380px; overflow-y: auto;">
                        {html.escape(draft_preview)}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # ═══════════════════════════════════════════════════════════════
    # TAB 3: CUSTOMER CONSULTATION FORM SUBMISSIONS
    # ═══════════════════════════════════════════════════════════════
    with tab_bookings_stream:
        st.markdown(
            clean_html(
                """
                <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-top: 6px; margin-bottom: 12px;">
                    <div>
                        <h3 style="margin: 0; font-size: 18px; font-weight: 600; display: flex; align-items: center; gap: 8px;">
                            <span>📋</span> Customer Consultation Form Submissions
                        </h3>
                        <p style="margin: 2px 0 0 0; font-size: 13px; color: var(--text-muted);">
                            Verified appointments submitted by clients with automated Microsoft Teams meeting links.
                        </p>
                    </div>
                </div>
                """
            ),
            unsafe_allow_html=True,
        )

        booked_df = df[df["form_filled_at"].notna()].copy() if not df.empty else pd.DataFrame()
        if os.path.exists(DEFAULT_BOOKED_EXCEL):
            try:
                excel_b_df = get_cached_excel_df(DEFAULT_BOOKED_EXCEL)
                if not excel_b_df.empty:
                    if booked_df.empty:
                        booked_df = excel_b_df
                    else:
                        existing_emails = set(booked_df["email"].astype(str).str.lower())
                        extra_rows = excel_b_df[~excel_b_df["email"].astype(str).str.lower().isin(existing_emails)]
                        if not extra_rows.empty:
                            booked_df = pd.concat([booked_df, extra_rows], ignore_index=True)
            except Exception:
                pass
        if not booked_df.empty and "form_filled_at" in booked_df.columns:
            booked_df = booked_df.sort_values(by="form_filled_at", ascending=False)

        if booked_df.empty:
            st.info("No consultation form submissions recorded yet. Submissions made via your permanent form link will appear here automatically.")
        else:
            # Search & Status Filter Controls
            f_col1, f_col2 = st.columns([3, 1.2])
            with f_col1:
                booking_search = st.text_input(
                    "Search Bookings",
                    placeholder="🔍 Search by lead name, company, email, or phone number...",
                    label_visibility="collapsed",
                    key="booking_search_term",
                )
            with f_col2:
                status_opts = ["All Statuses", "Confirmed & Sent", "Scheduled", "Pending"]
                status_sel = st.selectbox(
                    "Filter Status",
                    status_opts,
                    label_visibility="collapsed",
                    key="booking_status_sel",
                )

            # Apply search and filter
            filtered_booked = booked_df.copy()
            if booking_search:
                s_low = booking_search.lower().strip()
                filtered_booked = filtered_booked[
                    filtered_booked.apply(
                        lambda row: any(
                            s_low in str(row.get(col, "")).lower()
                            for col in ["email", "name", "company", "phone", "note"]
                        ),
                        axis=1,
                    )
                ]

            if status_sel != "All Statuses":
                if status_sel == "Confirmed & Sent":
                    filtered_booked = filtered_booked[
                        filtered_booked["booking_status"].isin(["confirmation_sent", "confirmed"])
                    ]
                elif status_sel == "Scheduled":
                    filtered_booked = filtered_booked[
                        filtered_booked["booking_status"].isin(["scheduled", "meeting_scheduled"])
                    ]
                elif status_sel == "Pending":
                    filtered_booked = filtered_booked[
                        filtered_booked["booking_status"].isin(["pending", "form_submitted", "submitted"])
                    ]

            st.caption(f"Showing **{len(filtered_booked)}** of **{len(booked_df)}** recorded consultation bookings:")

            tab_cards_view, tab_table_view = st.tabs(["🎴 Executive Booking Cards", "📊 Clean Data Grid"])

            with tab_cards_view:
                if filtered_booked.empty:
                    st.warning("No booking submissions match your search filter.")
                else:
                    card_rows = filtered_booked.to_dict("records")
                    for i in range(0, len(card_rows), 2):
                        col_left, col_right = st.columns(2, gap="medium")
                        pair = [card_rows[i]]
                        if i + 1 < len(card_rows):
                            pair.append(card_rows[i + 1])

                        for idx_card, r in enumerate(pair):
                            target_col = col_left if idx_card == 0 else col_right
                            with target_col:
                                b_name = r.get("name") or "Lead Contact"
                                b_company = r.get("company") or "Organization"
                                b_email = r.get("email") or "—"
                                b_phone = r.get("phone") or "—"
                                b_status_raw = r.get("booking_status") or "pending"
                                status_label, badge_cls = format_booking_status(b_status_raw)
                                initials = get_lead_initials(b_name)

                                fmt_requested = format_datetime_str(r.get("submitted_availability"))
                                fmt_confirmed = format_datetime_str(r.get("confirmed_slot"))
                                fmt_submitted = format_datetime_str(r.get("form_filled_at"))

                                meet_link = str(r.get("meet_link") or "").strip()
                                if meet_link.startswith("http"):
                                    teams_btn_html = f"""
                                    <a href="{meet_link}" target="_blank" class="teams-join-btn">
                                        📹 Join Microsoft Teams Meeting ↗
                                    </a>
                                    """
                                else:
                                    teams_btn_html = """
                                    <div style="text-align: center; font-size: 12px; color: #94A3B8; padding: 8px; background: #F8FAFC; border-radius: 6px; border: 1px dashed #E2E8F0;">
                                        ⏳ Meeting link will be generated upon confirmation
                                    </div>
                                    """

                                note_text = str(r.get("note") or "").strip()
                                note_html = ""
                                if note_text and note_text.lower() != "nan":
                                    note_html = f"""
                                    <div class="booking-note-box">
                                        <strong>Client Note:</strong> &ldquo;{note_text}&rdquo;
                                    </div>
                                    """

                                card_markup = f"""
                                <div class="booking-card">
                                    <div>
                                        <div class="booking-card-header">
                                            <div class="booking-lead-profile">
                                                <div class="booking-avatar">{initials}</div>
                                                <div>
                                                    <div class="booking-name-title">{b_name}</div>
                                                    <div class="booking-company-badge">🏢 {b_company}</div>
                                                </div>
                                            </div>
                                            <span class="badge {badge_cls}">{status_label}</span>
                                        </div>
                                        <div class="booking-info-grid">
                                            <div class="booking-info-item">
                                                <span class="booking-info-label">Customer Email</span>
                                                <span class="booking-info-val" title="{b_email}">✉️ {b_email}</span>
                                            </div>
                                            <div class="booking-info-item">
                                                <span class="booking-info-label">Phone Number</span>
                                                <span class="booking-info-val">📞 {b_phone}</span>
                                            </div>
                                            <div class="booking-info-item">
                                                <span class="booking-info-label">Requested Time</span>
                                                <span class="booking-info-val">⏱️ {fmt_requested}</span>
                                            </div>
                                            <div class="booking-info-item">
                                                <span class="booking-info-label">Submitted At</span>
                                                <span class="booking-info-val">📝 {fmt_submitted}</span>
                                            </div>
                                        </div>
                                        <div class="booking-slot-highlight">
                                            <span style="font-size: 18px;">🗓️</span>
                                            <div>
                                                <div style="font-size: 10.5px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #0F766E;">Confirmed Consultation Slot</div>
                                                <div class="booking-slot-text">{fmt_confirmed}</div>
                                            </div>
                                        </div>
                                        {note_html}
                                    </div>
                                    <div style="margin-top: 14px;">
                                        {teams_btn_html}
                                    </div>
                                </div>
                                """
                                st.markdown(clean_html(card_markup), unsafe_allow_html=True)

            with tab_table_view:
                display_grid_df = filtered_booked.copy()
                if "confirmed_slot" in display_grid_df.columns:
                    display_grid_df["formatted_confirmed"] = display_grid_df["confirmed_slot"].apply(format_datetime_str)
                else:
                    display_grid_df["formatted_confirmed"] = "—"

                if "submitted_availability" in display_grid_df.columns:
                    display_grid_df["formatted_requested"] = display_grid_df["submitted_availability"].apply(format_datetime_str)
                else:
                    display_grid_df["formatted_requested"] = "—"

                if "form_filled_at" in display_grid_df.columns:
                    display_grid_df["formatted_submitted"] = display_grid_df["form_filled_at"].apply(format_datetime_str)
                else:
                    display_grid_df["formatted_submitted"] = "—"

                if "booking_status" in display_grid_df.columns:
                    display_grid_df["clean_status"] = display_grid_df["booking_status"].apply(lambda s: format_booking_status(s)[0])
                else:
                    display_grid_df["clean_status"] = "Pending"

                table_cols = [
                    c for c in [
                        "email", "name", "company", "phone", "clean_status", 
                        "formatted_requested", "formatted_confirmed", "meet_link", 
                        "note", "formatted_submitted"
                    ] if c in display_grid_df.columns
                ]

                st.dataframe(
                    display_grid_df[table_cols],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "email": st.column_config.TextColumn("Customer Email", width="medium"),
                        "name": st.column_config.TextColumn("Full Name", width="small"),
                        "company": st.column_config.TextColumn("Company", width="small"),
                        "phone": st.column_config.TextColumn("Phone Number", width="small"),
                        "clean_status": st.column_config.TextColumn("Booking Status", width="small"),
                        "formatted_requested": st.column_config.TextColumn("Requested Slot", width="medium"),
                        "formatted_confirmed": st.column_config.TextColumn("Confirmed Slot", width="medium"),
                        "meet_link": st.column_config.LinkColumn("Teams Join Link", display_text="Join Teams Call ↗", width="medium"),
                        "note": st.column_config.TextColumn("Requirement Notes", width="large"),
                        "formatted_submitted": st.column_config.TextColumn("Submitted At", width="medium"),
                    },
                )

    # ═══════════════════════════════════════════════════════════════
    # TAB 3: PERMANENT EXCEL ARCHIVES
    # ═══════════════════════════════════════════════════════════════
    with tab_excel_stream:
        # Drawer 1: Customer Replies Workbook
        with st.expander(f"📗 Permanent Customer Replies Archive (`customer_replies.xlsx` · {replies_count} Records)", expanded=True):
            if os.path.exists(DEFAULT_REPLIES_EXCEL):
                try:
                    cr_export_df = get_cached_excel_df(DEFAULT_REPLIES_EXCEL)
                    d_col1, d_col2 = st.columns([3, 1])
                    with d_col1:
                        st.success(f"Verified `customer_replies.xlsx` on disk — contains **{len(cr_export_df)}** permanent customer reply records.")
                    with d_col2:
                        with open(DEFAULT_REPLIES_EXCEL, "rb") as f:
                            st.download_button(
                                label="⬇️ Export customer_replies.xlsx",
                                data=f,
                                file_name="customer_replies.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True,
                                key="dl_customer_replies_xlsx",
                            )
                    st.dataframe(cr_export_df, use_container_width=True, hide_index=True)
                except Exception as e:
                    st.error(f"Error reading customer_replies.xlsx: {e}")
            else:
                st.info("`customer_replies.xlsx` will be updated automatically when replies are processed.")

        st.markdown("<br>", unsafe_allow_html=True)

        # Drawer 2: Booked Leads Workbook
        with st.expander(f"📗 Permanent Consultation Bookings Archive (`booked_leads.xlsx` · {booked_leads_count} Records)", expanded=False):
            if os.path.exists(DEFAULT_BOOKED_EXCEL):
                try:
                    excel_df = get_cached_excel_df(DEFAULT_BOOKED_EXCEL)
                    meet_cols = [c for c in excel_df.columns if "google" in c.lower() and "meet" in c.lower()]
                    if meet_cols:
                        excel_df = excel_df.drop(columns=meet_cols)
                    dl_col1, dl_col2 = st.columns([3, 1])
                    with dl_col1:
                        st.success(f"Verified `booked_leads.xlsx` on disk — contains **{len(excel_df)}** permanent recorded submission(s).")
                    with dl_col2:
                        with open(DEFAULT_BOOKED_EXCEL, "rb") as f:
                            st.download_button(
                                label="⬇️ Export booked_leads.xlsx",
                                data=f,
                                file_name="booked_leads.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True,
                                key="dl_booked_leads_xlsx",
                            )
                    st.dataframe(excel_df, use_container_width=True, hide_index=True)
                except Exception as e:
                    st.error(f"Error reading booked_leads.xlsx: {e}")
            else:
                st.info("`booked_leads.xlsx` will be created automatically upon the first consultation form submission.")

# ─────────────────────────────────────────────────────────────
# MAIN ROUTER
# ─────────────────────────────────────────────────────────────
page = st.session_state.active_page

def get_campaign_logs_df() -> pd.DataFrame:
    org_id = st.session_state.get("current_org_id")
    res = load_campaign_logs(org_id)
    if isinstance(res, pd.DataFrame):
        return res
    return pd.DataFrame(res, columns=CAMPAIGN_LOG_COLUMNS) if res else pd.DataFrame(columns=CAMPAIGN_LOG_COLUMNS)

def render_main_view(page_name: str):
    org_id = st.session_state.get("current_org_id")
    if page_name == "overview":
        render_overview(get_campaign_logs_df())
    elif page_name == "master_db":
        render_master_db(get_campaign_logs_df(), organization_id=org_id)
    elif page_name == "analytics":
        render_analytics(get_campaign_logs_df())
    elif page_name == "replies":
        render_replies(get_campaign_logs_df())
    elif page_name == "leads":
        render_leads(get_campaign_logs_df())
    elif page_name == "templates":
        render_template_hub(get_campaign_logs_df())
    elif page_name == "email":
        render_email_review(get_campaign_logs_df())
    elif page_name == "upload":
        render_upload()
    elif page_name == "knowledge_base":
        render_knowledge_base_hub(organization_id=org_id)
    elif page_name == "org_settings":
        render_org_settings(organization_id=org_id)
    elif page_name == "team":
        render_team_view(organization_id=org_id)
    elif page_name == "super_admin":
        user_email = st.session_state.get("user", {}).get("email", "").lower().strip()
        if (
            st.session_state.get("user", {}).get("platform_role") == "platform_super_admin"
            and user_email in ["support@nenotechnology.com", "mohit@nenotechnology.us"]
        ):
            render_super_admin_portal()
        else:
            st.error("⛔ Access restricted: Only Platform Super Admin can access this portal.")
            st.session_state.active_page = "overview"
            render_overview(get_campaign_logs_df())

render_main_view(page)


