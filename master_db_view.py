"""Master Database & CRM Intelligence — Executive Streamlit View
Single source of truth for all leads, deduplication engine, intelligent chunking,
human-in-the-loop template assignment, and end-to-end outreach lifecycle tracking.
Designed with enterprise aesthetics: dark & light mode native, Outfit/Inter typography,
interactive Plotly charts, and modern micro-components.
"""

import io
import os
import re
import json
import base64
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from Backend.db import SessionLocal
from Backend.master_db_models import (
    MasterLead, LeadImport, LeadChunk, LeadChunkMember,
    OutreachHistory, LeadActivity, AuditLog,
)
from Backend.models import CampaignLog
from services.master_db_service import (
    generate_import_preview, confirm_import, normalize_email,
    get_dashboard_metrics, get_leads_paginated, get_lead_detail,
    get_all_chunks, get_chunk_leads, assign_template_to_chunk,
    transition_chunk_status, get_all_imports, get_import_detail,
    get_audit_log, get_templates_sent_to_lead, backfill_from_campaign_log,
    get_recent_activities, log_audit,
)
from services.template_service import load_all_templates
from utils.theme import apply_chart_theme, is_dark_mode


# ─────────────────────────────────────────────────────────────
# HIGH-PERFORMANCE IN-MEMORY CACHE (Eliminates Network Lag)
# ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=180, show_spinner=False)
def fetch_cached_dashboard_metrics() -> Dict:
    db = SessionLocal()
    try:
        return get_dashboard_metrics(db)
    finally:
        db.close()


@st.cache_data(ttl=180, show_spinner=False)
def fetch_cached_chunks() -> List[Dict]:
    db = SessionLocal()
    try:
        return get_all_chunks(db)
    finally:
        db.close()


@st.cache_data(ttl=180, show_spinner=False)
def fetch_cached_imports() -> List[Dict]:
    db = SessionLocal()
    try:
        return get_all_imports(db)
    finally:
        db.close()


@st.cache_data(ttl=120, show_spinner=False)
def fetch_cached_recent_activities(limit: int = 50) -> List[Dict]:
    db = SessionLocal()
    try:
        return get_recent_activities(db, limit=limit)
    finally:
        db.close()


@st.cache_data(ttl=120, show_spinner=False)
def fetch_cached_audit_log(limit: int = 200) -> List[Dict]:
    db = SessionLocal()
    try:
        return get_audit_log(db, limit=limit)
    finally:
        db.close()


@st.cache_data(ttl=300, show_spinner=False)
def fetch_cached_lead_detail(lead_id: str) -> Optional[Dict]:
    db = SessionLocal()
    try:
        return get_lead_detail(db, lead_id)
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────
# HTML CLEANING HELPER (Prevents raw code block leakage)
# ─────────────────────────────────────────────────────────────

def clean_html(html_str: str) -> str:
    """Strips leading/trailing whitespace from every line to prevent markdown
    parsers from mistakenly rendering HTML lines with 4+ spaces as <pre><code> blocks.
    """
    if not html_str:
        return ""
    return "".join(line.strip() for line in str(html_str).strip().splitlines() if line.strip())


# ─────────────────────────────────────────────────────────────
# STATUS BADGES & FORMATTING
# ─────────────────────────────────────────────────────────────

STATUS_CONFIG = {
    # Lead statuses
    "new": {"label": "New Ingested", "color": "#3B82F6", "bg_light": "#EFF6FF", "bg_dark": "rgba(59, 130, 246, 0.16)", "icon": "✨"},
    "active": {"label": "Active Pipeline", "color": "#2563EB", "bg_light": "#EFF6FF", "bg_dark": "rgba(37, 99, 235, 0.16)", "icon": "⚡"},
    "contacted": {"label": "Outreach Sent", "color": "#8B5CF6", "bg_light": "#F5F3FF", "bg_dark": "rgba(139, 92, 246, 0.16)", "icon": "📧"},
    "replied": {"label": "Replied / Engaged", "color": "#14B8A6", "bg_light": "#F0FDFA", "bg_dark": "rgba(20, 184, 166, 0.16)", "icon": "💬"},
    "booked": {"label": "Meeting Booked", "color": "#10B981", "bg_light": "#ECFDF5", "bg_dark": "rgba(16, 185, 129, 0.16)", "icon": "🎯"},
    "unsubscribed": {"label": "Unsubscribed", "color": "#EF4444", "bg_light": "#FEF2F2", "bg_dark": "rgba(239, 68, 68, 0.16)", "icon": "🚫"},
    "bounced": {"label": "Bounced / Invalid", "color": "#DC2626", "bg_light": "#FEF2F2", "bg_dark": "rgba(220, 38, 38, 0.16)", "icon": "⚠️"},
    # Chunk statuses
    "AWAITING_TEMPLATE": {"label": "Awaiting Template", "color": "#F59E0B", "bg_light": "#FFFBEB", "bg_dark": "rgba(245, 158, 11, 0.16)", "icon": "⏳"},
    "TEMPLATE_ASSIGNED": {"label": "Template Assigned", "color": "#3B82F6", "bg_light": "#EFF6FF", "bg_dark": "rgba(59, 130, 246, 0.16)", "icon": "🏷️"},
    "READY": {"label": "Ready to Send", "color": "#10B981", "bg_light": "#ECFDF5", "bg_dark": "rgba(16, 185, 129, 0.16)", "icon": "🚀"},
    "PROCESSING": {"label": "Processing Outreach", "color": "#8B5CF6", "bg_light": "#F5F3FF", "bg_dark": "rgba(139, 92, 246, 0.16)", "icon": "🔄"},
    "COMPLETED": {"label": "Completed", "color": "#059669", "bg_light": "#ECFDF5", "bg_dark": "rgba(5, 150, 105, 0.16)", "icon": "✅"},
    "PARTIALLY_COMPLETED": {"label": "Partial Complete", "color": "#D97706", "bg_light": "#FFFBEB", "bg_dark": "rgba(217, 119, 6, 0.16)", "icon": "⚠️"},
    "PAUSED": {"label": "Paused", "color": "#64748B", "bg_light": "#F8FAFC", "bg_dark": "rgba(100, 116, 139, 0.16)", "icon": "⏸️"},
    "FAILED": {"label": "Failed", "color": "#EF4444", "bg_light": "#FEF2F2", "bg_dark": "rgba(239, 68, 68, 0.16)", "icon": "❌"},
    "CANCELLED": {"label": "Cancelled", "color": "#475569", "bg_light": "#F1F5F9", "bg_dark": "rgba(71, 85, 105, 0.16)", "icon": "⏹️"},
}


def render_status_badge(status_key: str, custom_text: Optional[str] = None) -> str:
    """Renders a polished, theme-compatible inline status badge."""
    cfg = STATUS_CONFIG.get(status_key, {
        "label": status_key.replace("_", " ").title(),
        "color": "#64748B",
        "bg_light": "#F1F5F9",
        "bg_dark": "rgba(100, 116, 139, 0.16)",
        "icon": "•",
    })
    is_dark = is_dark_mode()
    bg = cfg["bg_dark"] if is_dark else cfg["bg_light"]
    color = cfg["color"]
    label = custom_text or cfg["label"]
    icon = cfg.get("icon", "")

    return f'<span class="mdb-badge" style="background:{bg};color:{color};border:1px solid {color}35;"><span style="font-size:10px;">{icon}</span><span>{label}</span></span>'


# ─────────────────────────────────────────────────────────────
# SCOPED STYLESHEET (Dark & Light Theme Harmony)
# ─────────────────────────────────────────────────────────────

def _inject_master_db_styles(is_dark: bool) -> None:
    """Injects bespoke CSS variables and component classes for the Master DB suite."""
    css = f"""
    <style>
    /* ── Master DB Executive Banner ── */
    .mdb-banner {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: var(--bg-surface);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-lg);
        padding: 22px 28px;
        margin-bottom: 22px;
        box-shadow: var(--shadow-sm);
        position: relative;
        overflow: hidden;
    }}
    .mdb-banner::before {{
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 4px;
        height: 100%;
        background: linear-gradient(180deg, #3B82F6 0%, #8B5CF6 100%);
    }}
    .mdb-banner-title {{
        font-family: 'Outfit', sans-serif !important;
        font-size: 24px !important;
        font-weight: 700 !important;
        color: var(--text-primary) !important;
        letter-spacing: -0.025em !important;
        margin: 0 !important;
        display: flex;
        align-items: center;
        gap: 12px;
    }}
    .mdb-banner-desc {{
        font-family: 'Inter', sans-serif !important;
        font-size: 13.5px !important;
        color: var(--text-muted) !important;
        margin: 6px 0 0 0 !important;
        line-height: 1.5 !important;
        max-width: 820px;
    }}
    .mdb-banner-chips {{
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin-top: 10px;
    }}
    .mdb-chip {{
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 3px 10px;
        border-radius: 6px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        font-weight: 600;
        background: {'rgba(59, 130, 246, 0.12)' if is_dark else '#EFF6FF'};
        color: {'#93C5FD' if is_dark else '#1D4ED8'};
        border: 1px solid {'rgba(59, 130, 246, 0.3)' if is_dark else '#BFDBFE'};
    }}

    /* ── Badge Pill ── */
    .mdb-badge {{
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 3px 10px;
        border-radius: 9999px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: -0.01em;
        white-space: nowrap;
    }}

    /* ── Executive Card Container ── */
    .mdb-card {{
        background: var(--bg-surface);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-lg);
        padding: 20px 22px;
        box-shadow: var(--shadow-sm);
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
    }}
    .mdb-card:hover {{
        border-color: var(--border-strong);
        box-shadow: var(--shadow-md);
    }}
    .mdb-card-title {{
        font-family: 'Outfit', sans-serif !important;
        font-size: 16px !important;
        font-weight: 700 !important;
        color: var(--text-primary) !important;
        margin: 0 0 14px 0 !important;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }}

    /* ── Workflow Stepper ── */
    .mdb-stepper {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 12px;
        margin-bottom: 24px;
    }}
    @media (max-width: 800px) {{
        .mdb-stepper {{ grid-template-columns: repeat(2, 1fr); }}
    }}
    .mdb-step-item {{
        background: var(--bg-surface);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-md);
        padding: 12px 14px;
        display: flex;
        align-items: center;
        gap: 10px;
        transition: all 0.2s ease;
    }}
    .mdb-step-num {{
        width: 26px;
        height: 26px;
        border-radius: 50%;
        background: {'rgba(59, 130, 246, 0.16)' if is_dark else '#EFF6FF'};
        color: {'#60A5FA' if is_dark else '#2563EB'};
        font-family: 'JetBrains Mono', monospace;
        font-weight: 700;
        font-size: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }}
    .mdb-step-title {{
        font-family: 'Outfit', sans-serif;
        font-weight: 600;
        font-size: 12.5px;
        color: var(--text-primary);
        line-height: 1.2;
    }}
    .mdb-step-sub {{
        font-family: 'Inter', sans-serif;
        font-size: 11px;
        color: var(--text-muted);
        margin-top: 2px;
    }}

    /* ── Lead Detail Profile Glass ── */
    .mdb-lead-header {{
        background: var(--bg-surface);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-lg);
        padding: 24px;
        margin-bottom: 18px;
        box-shadow: var(--shadow-sm);
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 16px;
    }}
    .mdb-avatar {{
        width: 54px;
        height: 54px;
        border-radius: 14px;
        background: linear-gradient(135deg, #2563EB 0%, #7C3AED 100%);
        color: #FFFFFF;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: 'Outfit', sans-serif;
        font-size: 22px;
        font-weight: 700;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25);
        flex-shrink: 0;
    }}

    /* ── Timeline List Stream ── */
    .mdb-timeline-wrap {{
        position: relative;
        padding-left: 28px;
        margin: 16px 0;
    }}
    .mdb-timeline-wrap::before {{
        content: '';
        position: absolute;
        top: 6px;
        bottom: 6px;
        left: 11px;
        width: 2px;
        background: var(--border-strong);
    }}
    .mdb-timeline-row {{
        position: relative;
        margin-bottom: 14px;
    }}
    .mdb-timeline-dot {{
        position: absolute;
        left: -28px;
        top: 2px;
        width: 24px;
        height: 24px;
        border-radius: 50%;
        background: var(--bg-surface);
        border: 2px solid #3B82F6;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 11px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.1);
    }}
    .mdb-timeline-box {{
        background: var(--bg-surface);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-md);
        padding: 10px 14px;
    }}

    /* ── Progress Bar ── */
    .mdb-progress-track {{
        width: 100%;
        height: 8px;
        background: {'#1F2937' if is_dark else '#E2E8F0'};
        border-radius: 4px;
        overflow: hidden;
        margin-top: 6px;
    }}
    .mdb-progress-fill {{
        height: 100%;
        border-radius: 4px;
        background: linear-gradient(90deg, #3B82F6, #10B981);
        transition: width 0.4s ease;
    }}
    </style>
    """
    st.markdown(clean_html(css), unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# MAIN VIEW CONTROLLER
# ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=600, show_spinner=False)
def _ensure_master_db_synced_once() -> bool:
    """Fast initial check to ensure Master DB has records."""
    db_chk = SessionLocal()
    try:
        m_cnt = db_chk.query(MasterLead).count()
        if m_cnt == 0:
            backfill_from_campaign_log(db_chk)
        return True
    except Exception as _ex:
        print(f"[Master DB sync notice] {_ex}")
        return False
    finally:
        db_chk.close()


def render_master_db(df_logs: pd.DataFrame = None):
    """Main entry point for Master Database & CRM Intelligence."""
    is_dark = is_dark_mode()
    _inject_master_db_styles(is_dark)

    # Automatic initial sync check: cached for 10 minutes so it doesn't run on every tab click
    _ensure_master_db_synced_once()

    # Top Executive Banner
    banner_html = f"""
    <div class="mdb-banner">
        <div>
            <h1 class="mdb-banner-title">
                <span>🗄️</span>
                <span>Master Leads Intelligence &amp; Ingestion Hub</span>
                <span class="mdb-badge" style="background:{'rgba(16, 185, 129, 0.16)' if is_dark else '#ECFDF5'};color:{'#34D399' if is_dark else '#047857'};border:1px solid {'rgba(16, 185, 129, 0.35)' if is_dark else '#A7F3D0'};">
                    ● Single Source of Truth
                </span>
            </h1>
            <p class="mdb-banner-desc">
                Centralized CRM repository: strict multi-touch deduplication, intelligent batch chunking, human-in-the-loop template assignment, and complete chronological lifecycle audit.
            </p>
            <div class="mdb-banner-chips">
                <span class="mdb-chip">🛡️ Deduplication Engine: ACTIVE</span>
                <span class="mdb-chip">📦 Smart Chunking: READY</span>
                <span class="mdb-chip">🏷️ Template Assignment: HUMAN-IN-THE-LOOP</span>
                <span class="mdb-chip">📜 Audit Logging: ENABLED</span>
            </div>
        </div>
    </div>
    """
    st.markdown(clean_html(banner_html), unsafe_allow_html=True)

    # Quick Live Sync Bar
    sync_c1, sync_c2 = st.columns([4.2, 1.2])
    with sync_c2:
        if st.button("⚡ Live Sync Real Data", key="btn_quick_live_sync", type="primary", use_container_width=True, help="Synchronize real data from campaigns, replies, and Excel sheets into Master DB"):
            db_sync = SessionLocal()
            try:
                with st.spinner("Syncing live telemetry & campaign records..."):
                    res = backfill_from_campaign_log(db_sync)
                st.cache_data.clear()
                st.toast(f"✅ Real data live synced! ({res['linked']} records verified)", icon="⚡")
                st.rerun()
            finally:
                db_sync.close()

    # Master DB Sub-navigation (Lazy Evaluation — executes ONLY the selected view)
    MDB_TAB_CHOICES = [
        ("overview", "📊 Command Center"),
        ("leads", "👥 Leads Directory"),
        ("ingestion", "📥 Ingestion & Deduplication"),
        ("chunks", "📦 Intelligent Chunks"),
        ("templates", "🏷️ Template Performance"),
        ("history", "📜 Batch History"),
        ("timeline", "🕐 Global Timeline"),
        ("audit", "📋 Regulatory Audit Log"),
    ]

    if "mdb_tab" in st.query_params and any(st.query_params["mdb_tab"] == k for k, _ in MDB_TAB_CHOICES):
        st.session_state.mdb_active_tab = st.query_params["mdb_tab"]
    elif "mdb_active_tab" not in st.session_state or st.session_state.mdb_active_tab not in [k for k, _ in MDB_TAB_CHOICES]:
        st.session_state.mdb_active_tab = "overview"

    # Sleek Tab Ribbon
    tab_cols = st.columns(len(MDB_TAB_CHOICES))
    for i, (t_key, t_label) in enumerate(MDB_TAB_CHOICES):
        with tab_cols[i]:
            is_cur = (st.session_state.mdb_active_tab == t_key)
            btn_type = "primary" if is_cur else "secondary"
            if st.button(
                t_label,
                key=f"btn_mdb_tab_{t_key}",
                type=btn_type,
                use_container_width=True,
            ):
                if st.session_state.mdb_active_tab != t_key:
                    st.session_state.mdb_active_tab = t_key
                    st.query_params["mdb_tab"] = t_key
                    st.rerun()

    cur_mdb_tab = st.session_state.mdb_active_tab

    if cur_mdb_tab == "overview":
        _render_tab_overview()
    elif cur_mdb_tab == "leads":
        _render_tab_leads_directory()
    elif cur_mdb_tab == "ingestion":
        _render_tab_ingestion()
    elif cur_mdb_tab == "chunks":
        _render_tab_chunks()
    elif cur_mdb_tab == "templates":
        _render_tab_templates()
    elif cur_mdb_tab == "history":
        _render_tab_import_history()
    elif cur_mdb_tab == "timeline":
        _render_tab_activity_timeline()
    elif cur_mdb_tab == "audit":
        _render_tab_audit_log()


# ─────────────────────────────────────────────────────────────
# TAB 1: 📊 COMMAND CENTER (Executive Overview)
# ─────────────────────────────────────────────────────────────

def _render_tab_overview():
    """Renders executive KPI metrics, interactive Plotly charts, and system status."""
    is_dark = is_dark_mode()
    metrics = fetch_cached_dashboard_metrics()

    total_leads = metrics.get("total_leads", 0)
    new_this_week = metrics.get("new_this_week", 0)
    duplicate_records = metrics.get("duplicate_records", 0)
    total_emails_sent = metrics.get("total_emails_sent", 0)
    total_replies = metrics.get("total_replies", 0)
    total_booked = metrics.get("total_booked", 0)

    # ── Executive 6-Card KPI Grid (matches analytics_view.py) ──
    reply_rate = round((total_replies / max(total_emails_sent, 1)) * 100, 1)
    book_rate = round((total_booked / max(total_replies, 1)) * 100, 1) if total_replies > 0 else 0.0

    kpi_markup = f"""
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-top-bar kpi-bar-blue"></div>
            <div class="kpi-header">
                <span class="kpi-label">Master Leads Stored</span>
                <div class="kpi-icon-box" style="background:{'rgba(59, 130, 246, 0.15)' if is_dark else '#EFF6FF'};color:#3B82F6;">👥</div>
            </div>
            <div class="kpi-value">{total_leads:,}</div>
            <div class="kpi-micro">
                <span class="kpi-pill kpi-pill-blue">+{new_this_week} this week</span>
                <span>Single Source of Truth</span>
            </div>
        </div>

        <div class="kpi-card">
            <div class="kpi-top-bar kpi-bar-amber"></div>
            <div class="kpi-header">
                <span class="kpi-label">Duplicates Filtered</span>
                <div class="kpi-icon-box" style="background:{'rgba(245, 158, 11, 0.15)' if is_dark else '#FFFBEB'};color:#F59E0B;">🛡️</div>
            </div>
            <div class="kpi-value">{duplicate_records:,}</div>
            <div class="kpi-micro">
                <span class="kpi-pill kpi-pill-amber">100% Blocked</span>
                <span>Zero Double-Sends</span>
            </div>
        </div>

        <div class="kpi-card">
            <div class="kpi-top-bar kpi-bar-teal"></div>
            <div class="kpi-header">
                <span class="kpi-label">Emails Dispatched</span>
                <div class="kpi-icon-box" style="background:{'rgba(20, 184, 166, 0.15)' if is_dark else '#F0FDFA'};color:#14B8A6;">📧</div>
            </div>
            <div class="kpi-value">{total_emails_sent:,}</div>
            <div class="kpi-micro">
                <span class="kpi-pill kpi-pill-teal">Outreach Live</span>
                <span>All Sequences</span>
            </div>
        </div>

        <div class="kpi-card">
            <div class="kpi-top-bar kpi-bar-purple"></div>
            <div class="kpi-header">
                <span class="kpi-label">Inbound Replies</span>
                <div class="kpi-icon-box" style="background:{'rgba(139, 92, 246, 0.15)' if is_dark else '#F5F3FF'};color:#8B5CF6;">💬</div>
            </div>
            <div class="kpi-value">{total_replies:,}</div>
            <div class="kpi-micro">
                <span class="kpi-pill kpi-pill-purple">{reply_rate}% Reply Rate</span>
                <span>AI Intent Parsed</span>
            </div>
        </div>

        <div class="kpi-card">
            <div class="kpi-top-bar kpi-bar-rose"></div>
            <div class="kpi-header">
                <span class="kpi-label">Consultations Booked</span>
                <div class="kpi-icon-box" style="background:{'rgba(244, 63, 94, 0.15)' if is_dark else '#FFF1F2'};color:#F43F5E;">📅</div>
            </div>
            <div class="kpi-value">{total_booked:,}</div>
            <div class="kpi-micro">
                <span class="kpi-pill kpi-pill-rose">{book_rate}% Conversion</span>
                <span>Booked Meetings</span>
            </div>
        </div>

        <div class="kpi-card">
            <div class="kpi-top-bar kpi-bar-cyan"></div>
            <div class="kpi-header">
                <span class="kpi-label">Batch Chunks Managed</span>
                <div class="kpi-icon-box" style="background:{'rgba(6, 182, 212, 0.15)' if is_dark else '#ECFEFF'};color:#06B6D4;">📦</div>
            </div>
            <div class="kpi-value">{sum(metrics.get('chunk_pipeline', {}).values()):,}</div>
            <div class="kpi-micro">
                <span class="kpi-pill kpi-pill-cyan">Structured Batches</span>
                <span>Deliverability Safe</span>
            </div>
        </div>
    </div>
    """
    st.markdown(clean_html(kpi_markup), unsafe_allow_html=True)
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # ── Interactive Plotly Charts Row ──
    c_chart1, c_chart2 = st.columns([1.1, 1.0])

    with c_chart1:
        st.markdown("""
        <div class="mdb-card">
            <div class="mdb-card-title">
                <span>📊 Lead Lifecycle Distribution</span>
                <span style="font-size:12px;font-weight:500;color:var(--text-muted);">Real-Time Master DB</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        sc = metrics.get("status_counts", {})
        if not sc or sum(sc.values()) == 0:
            sc = {"new": 1}

        labels = [STATUS_CONFIG.get(k, {}).get("label", k.title()) for k in sc.keys()]
        values = list(sc.values())
        colors = [STATUS_CONFIG.get(k, {}).get("color", "#64748B") for k in sc.keys()]

        fig_donut = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.62,
            marker=dict(colors=colors, line=dict(color="#111827" if is_dark else "#FFFFFF", width=2)),
            textinfo="percent+label",
            textposition="inside",
            insidetextorientation="radial",
            hovertemplate="<b>%{label}</b><br>Count: %{value:,}<br>Share: %{percent}<extra></extra>",
        )])
        fig_donut.update_layout(
            margin=dict(t=10, b=10, l=10, r=10),
            height=320,
            showlegend=False,
            annotations=[dict(
                text=f"<b>{total_leads:,}</b><br><span style='font-size:11px;color:#94A3B8;'>TOTAL LEADS</span>",
                x=0.5, y=0.5, font_size=18, font_family="JetBrains Mono", showarrow=False
            )]
        )
        apply_chart_theme(fig_donut, is_dark=is_dark)
        st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar": False})

    with c_chart2:
        st.markdown("""
        <div class="mdb-card">
            <div class="mdb-card-title">
                <span>⚙️ Chunk Execution Pipeline</span>
                <span style="font-size:12px;font-weight:500;color:var(--text-muted);">Batch Status Funnel</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        pipeline = metrics.get("chunk_pipeline", {})
        pipeline_order = ["AWAITING_TEMPLATE", "TEMPLATE_ASSIGNED", "READY", "PROCESSING", "COMPLETED"]
        p_names = [STATUS_CONFIG.get(k, {}).get("label", k.replace("_", " ").title()) for k in pipeline_order]
        p_vals = [pipeline.get(k, 0) for k in pipeline_order]
        p_colors = [STATUS_CONFIG.get(k, {}).get("color", "#3B82F6") for k in pipeline_order]

        fig_bar = go.Figure(data=[go.Bar(
            y=p_names,
            x=p_vals,
            orientation="h",
            marker=dict(color=p_colors, cornerradius=6),
            text=p_vals,
            textposition="auto",
            hovertemplate="<b>%{y}</b><br>Chunks: %{x}<extra></extra>",
        )])
        fig_bar.update_layout(
            margin=dict(t=10, b=10, l=10, r=20),
            height=320,
            xaxis=dict(showgrid=True, title="Number of Chunks"),
            yaxis=dict(autorange="reversed"),
        )
        apply_chart_theme(fig_bar, is_dark=is_dark)
        st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})

    # ── Database Synchronization & Legacy Backfill ──
    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    with st.expander("⚡ System Maintenance & Legacy Campaign Log Sync", expanded=False):
        st.markdown("""
        <div style="font-size: 13.5px; color: var(--text-secondary); margin-bottom: 12px; line-height: 1.6;">
            <strong>Backfill Engine:</strong> Scans existing <code>campaign_log</code> rows and automatically indexes them into the Master Database.
            Existing records are linked, deduplicated, and updated with timestamps, activity events, and outreach history without data loss.
        </div>
        """, unsafe_allow_html=True)

        b_col1, b_col2 = st.columns([1.5, 3.5])
        with b_col1:
            if st.button("🔄 Sync & Backfill Master DB", type="primary", use_container_width=True, key="btn_backfill_now"):
                db = SessionLocal()
                try:
                    with st.spinner("Indexing and synchronizing leads into Master DB..."):
                        res = backfill_from_campaign_log(db)
                    st.cache_data.clear()
                    st.success(f"✅ Sync Complete: **{res['created']}** leads created, **{res['updated']}** updated, **{res['linked']}** logs linked.")
                    st.rerun()
                except Exception as ex:
                    st.error(f"Error during backfill: {ex}")
                finally:
                    db.close()
        with b_col2:
            st.caption("Safe & idempotent operation. Run whenever external campaign files or background processes finish.")


# ─────────────────────────────────────────────────────────────
# TAB 2: 👥 LEADS DIRECTORY (CRM View)
# ─────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────
# TAB 2: 👥 LEADS DIRECTORY (CRM View: Hot / Warm / Cold Leads)
# ─────────────────────────────────────────────────────────────

def categorize_lead_temperature(row: Dict[str, Any]) -> Dict[str, Any]:
    """Analyzes real engagement telemetry and classifies lead into Hot, Warm, or Cold."""
    opens = int(row.get("opens") or row.get("open_count") or 0)
    clicks = int(row.get("clicks") or row.get("click_count") or 0)
    replies = int(row.get("replies") or row.get("total_replies") or 0)
    reply_body = str(row.get("reply_body") or "").strip()
    reply_intent = str(row.get("reply_intent") or "").strip().lower()
    booking_status = str(row.get("booking_status") or "").strip().lower()
    status_lower = str(row.get("status") or "").strip().lower()

    has_booked = booking_status in ["scheduled", "meeting_scheduled", "confirmation_sent", "confirmed", "booked"]
    has_replied = bool(
        replies > 0
        or (reply_body and reply_body.lower() not in ["none", "nan", "nat", "—", "-"])
        or status_lower == "replied"
    )

    score = 0.0
    signals = []

    # 1. Bookings & Consultations
    if has_booked:
        score = 98.0
        signals.append("📅 Meeting Booked")

    # 2. Customer Replies
    elif has_replied:
        score = max(score, 92.0)
        if reply_intent in ["interested", "positive_acknowledgement"]:
            signals.append("💬 Replied: High Interest")
        elif reply_intent == "reschedule":
            signals.append("💬 Replied: Reschedule Request")
        elif reply_intent == "question":
            signals.append("💬 Replied: Asked Details")
        elif reply_intent == "not_interested":
            score = 30.0
            signals.append("💬 Replied: Opt-out")
        else:
            signals.append("💬 Replied")

    # 3. Link Clicks (Strong buying interest)
    if clicks > 0:
        c_score = 70.0 + min(20.0, clicks * 4.0)
        score = max(score, c_score)
        signals.append(f"🖱️ Clicked Link {clicks}x")

    # 4. Email Opens
    if opens > 0:
        if score < 70.0:
            score = max(score, 25.0 + min(35.0, opens * 8.0))
        signals.append(f"👁️ Opened {opens}x")

    # Cold default
    if not signals:
        score = 10.0
        signals.append("Delivered • Unopened")

    score = min(100.0, max(0.0, score))

    # Accurate Tier Segmentation
    if has_booked or (has_replied and reply_intent != "not_interested") or (clicks >= 2 or (clicks > 0 and opens >= 2)) or score >= 70.0:
        tier = "HOT"
        tier_display = "🔥 Hot"
    elif opens > 0 or clicks > 0 or has_replied or score >= 25.0:
        tier = "WARM"
        tier_display = "⚡ Warm"
    else:
        tier = "COLD"
        tier_display = "❄️ Cold"

    activity_summary = " • ".join(signals)

    return {
        "tier": tier,
        "tier_display": tier_display,
        "score": int(round(score)),
        "activity_summary": activity_summary,
    }


@st.cache_data(ttl=600, show_spinner=False)
def _load_cached_leads_file_metadata(file_path: str = "leads.xlsx") -> Dict[str, Dict]:
    """Fast in-memory cache of leads spreadsheet metadata."""
    leads_meta = {}
    if os.path.exists(file_path):
        try:
            df_meta = pd.read_excel(file_path)
            for r in df_meta.to_dict("records"):
                em_raw = r.get("email") or r.get("Email ID") or r.get("emails")
                if pd.notna(em_raw):
                    em = str(em_raw).strip().lower()
                    if "@" in em and em not in leads_meta:
                        pos = r.get("Position") or r.get("job_title")
                        co = r.get("Company Name") or r.get("company")
                        fn = r.get("Full Name") or r.get("name")
                        leads_meta[em] = {
                            "job_title": str(pos).strip() if pd.notna(pos) and str(pos).strip().lower() not in ("nan", "none", "") else "",
                            "company": str(co).strip() if pd.notna(co) and str(co).strip().lower() not in ("nan", "none", "") else "",
                            "name": str(fn).strip() if pd.notna(fn) and str(fn).strip().lower() not in ("nan", "none", "") else "",
                        }
        except Exception:
            pass
    return leads_meta


@st.cache_data(ttl=300, show_spinner=False)
def load_enriched_master_data() -> pd.DataFrame:
    """Loads all Master Leads with full telemetry, template assignments, and Excel metadata."""
    from Backend.db import SessionLocal
    from Backend.master_db_models import MasterLead, OutreachHistory
    from Backend.models import CampaignLog

    db = SessionLocal()
    try:
        leads = db.query(MasterLead).all()
        oh_rows = db.query(OutreachHistory).order_by(OutreachHistory.created_at.desc()).all()
        oh_map = {}
        for oh in oh_rows:
            if oh.master_lead_id and oh.master_lead_id not in oh_map:
                oh_map[oh.master_lead_id] = oh

        cl_rows = db.query(CampaignLog).order_by(CampaignLog.created_at.desc()).all()
        cl_map = {}
        for cl in cl_rows:
            em = (cl.email or "").strip().lower()
            if em and em not in cl_map:
                cl_map[em] = cl

        # Load leads.xlsx metadata from fast in-memory cache
        leads_meta = _load_cached_leads_file_metadata("leads.xlsx")

        data = []
        for l in leads:
            em_norm = (l.email_normalized or l.email or "").strip().lower()
            oh = oh_map.get(l.id)
            cl = cl_map.get(em_norm)
            meta = leads_meta.get(em_norm, {})

            tpl_name = (oh.template_name if oh else None) or (cl.template_name if cl else None) or "Template 1: Forward Deployed AI Engineers"
            tpl_id = (oh.template_id if oh else None) or (cl.template_id if cl else None) or ""

            reply_b = (cl.reply_body if cl else None) or ""
            reply_int = (cl.reply_intent if cl else None) or (l.intent or "")
            booking_st = l.booking_status or (cl.booking_status if cl else "") or ""
            sent_time = l.last_contacted_at or (cl.email_sent_at if cl else None)

            full_n = meta.get("name") or l.full_name or ((l.first_name or "") + " " + (l.last_name or "")).strip() or (cl.name if cl else "") or "—"
            comp_n = meta.get("company") or l.company or (cl.company if cl else "") or "—"
            job_t = meta.get("job_title") or l.job_title or "—"

            row_dict = {
                "id": l.id,
                "email": l.email,
                "name": full_n,
                "company": comp_n,
                "job_title": job_t,
                "status": (l.current_status or "new").title(),
                "template_name": tpl_name,
                "template_id": tpl_id,
                "opens": int(l.total_opens or 0),
                "clicks": int(l.total_clicks or 0),
                "replies": int(l.total_replies or 0),
                "booking_status": booking_st,
                "reply_body": reply_b,
                "reply_intent": reply_int,
                "last_contacted_at": sent_time,
                "created_at": l.created_at,
            }
            temp_info = categorize_lead_temperature(row_dict)
            row_dict.update(temp_info)
            data.append(row_dict)
    finally:
        db.close()

    return pd.DataFrame(data) if data else pd.DataFrame()


@st.cache_data(show_spinner=False, ttl=600)
def generate_excel_export_bytes(df: pd.DataFrame, sheet_name: str = "Leads") -> bytes:
    """Generates an executive-formatted .xlsx Excel spreadsheet (cached in RAM)."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name[:31])
        worksheet = writer.sheets[sheet_name[:31]]
        for col in worksheet.columns:
            max_len = 0
            for cell in col:
                val_str = str(cell.value or "")
                if len(val_str) > max_len:
                    max_len = len(val_str)
            col_letter = col[0].column_letter
            worksheet.column_dimensions[col_letter].width = min(max(max_len + 3, 11), 50)
    return output.getvalue()


@st.cache_data(show_spinner=False, ttl=600)
def generate_csv_export_bytes(df: pd.DataFrame) -> bytes:
    """Fast in-memory cached CSV byte generator."""
    return df.to_csv(index=False).encode("utf-8")


def build_clean_dataframe(df_source: pd.DataFrame) -> pd.DataFrame:
    """Builds clean, structured dataframe formatted for display and export."""
    if df_source.empty:
        return pd.DataFrame()

    df_out = df_source.copy()

    df_out["opens"] = df_out["opens"].fillna(0).astype(int)
    df_out["clicks"] = df_out["clicks"].fillna(0).astype(int)

    df_out["reply_preview"] = df_out["reply_body"].apply(
        lambda x: (str(x)[:95] + "...") if pd.notna(x) and str(x).strip() and str(x).lower() not in ["none", "nan", "—", "-"] else "—"
    )

    df_out["template"] = df_out["template_name"].apply(
        lambda x: str(x).split(":")[0] if pd.notna(x) and ":" in str(x) else str(x)
    )

    def _clean_display(val, default="—"):
        if val is None or pd.isna(val):
            return default
        s = str(val).strip()
        if s.lower() in ("nan", "none", "nat", "", "—"):
            return default
        return s

    df_out["job_title"] = df_out["job_title"].apply(_clean_display)
    df_out["company"] = df_out["company"].apply(lambda x: _clean_display(x, "Unknown Company"))
    df_out["name"] = df_out["name"].apply(lambda x: _clean_display(x, "Lead Contact"))
    df_out["status"] = df_out["status"].apply(lambda x: _clean_display(x, "Sent").capitalize())

    cols_order = [
        c for c in [
            "tier_display",
            "score",
            "company",
            "name",
            "job_title",
            "email",
            "template",
            "opens",
            "clicks",
            "activity_summary",
            "reply_preview",
            "status",
        ] if c in df_out.columns
    ]
    return df_out[cols_order]


def _render_tab_leads_directory():
    """Renders template-wise lead segmentation into Hot, Warm, and Cold leads with Excel sheet export."""
    is_dark = is_dark_mode()
    templates = load_all_templates()

    # Load authentic enriched master lead records
    enriched_df = load_enriched_master_data()

    if enriched_df.empty:
        st.info("No leads found in the database. Ingest leads via the **Lead Ingestion & Deduplication** tab.")
        return

    # ── Top Filter Ribbon ──
    total_leads_in_db = len(enriched_df)
    template_choices = {"__all__": f"🌐 All Templates ({total_leads_in_db} leads)"}

    for tpl in templates:
        t_id = tpl.get("id")
        t_name = tpl.get("name", t_id)
        num_match = re.search(r"Template (\d+)", t_name) or re.search(r"(\d+)", t_id)
        t_num = num_match.group(1) if num_match else ""
        mask = (
            (enriched_df["template_id"] == t_id)
            | (enriched_df["template_name"] == t_name)
            | (enriched_df["template_name"].str.contains(t_id, na=False, case=False))
        )
        if t_num:
            mask = mask | (enriched_df["template_name"].str.contains(f"Template {t_num}", na=False, case=False))
        lead_count = int(mask.sum())
        template_choices[t_id] = f"{t_name} ({lead_count} leads)"

    col_tpl, col_search, col_score = st.columns([2.8, 2.0, 1.2])

    with col_tpl:
        default_tpl_id = st.query_params.get("template", "__all__")
        if default_tpl_id not in template_choices:
            default_tpl_id = "__all__"

        selected_tpl = st.selectbox(
            "Filter Outreach Template:",
            options=list(template_choices.keys()),
            format_func=lambda x: template_choices[x],
            index=list(template_choices.keys()).index(default_tpl_id),
            key="mdb_tpl_select",
        )
        if selected_tpl != st.query_params.get("template"):
            st.query_params["template"] = selected_tpl

    with col_search:
        search_kw = st.text_input(
            "Search Real Database:",
            placeholder="Search company, contact name, or email...",
            key="mdb_search_kw",
        ).strip().lower()

    with col_score:
        min_score = st.slider(
            "Min Lead Score:",
            min_value=0,
            max_value=100,
            value=0,
            step=5,
            key="mdb_score_slider",
        )

    # ── Instant Filtering ──
    filtered_df = enriched_df.copy()

    if selected_tpl != "__all__":
        t_obj = next((t for t in templates if t.get("id") == selected_tpl), {})
        t_name = t_obj.get("name", selected_tpl)
        num_match = re.search(r"(\d+)", selected_tpl) or re.search(r"Template (\d+)", t_name)
        t_num = num_match.group(1) if num_match else ""

        mask = (
            (filtered_df["template_id"] == selected_tpl)
            | (filtered_df["template_name"] == t_name)
            | (filtered_df["template_name"].str.contains(selected_tpl, na=False, case=False))
        )
        if t_num:
            mask = mask | (filtered_df["template_name"].str.contains(f"Template {t_num}", na=False, case=False))
        filtered_df = filtered_df[mask]

    if min_score > 0:
        filtered_df = filtered_df[filtered_df["score"] >= min_score]

    if search_kw:
        s_mask = (
            filtered_df["name"].astype(str).str.lower().str.contains(search_kw)
            | filtered_df["company"].astype(str).str.lower().str.contains(search_kw)
            | filtered_df["email"].astype(str).str.lower().str.contains(search_kw)
            | filtered_df["activity_summary"].astype(str).str.lower().str.contains(search_kw)
        )
        if "job_title" in filtered_df.columns:
            s_mask = s_mask | filtered_df["job_title"].astype(str).str.lower().str.contains(search_kw)
        filtered_df = filtered_df[s_mask]

    # Segmentation into Tiers
    hot_df = filtered_df[filtered_df["tier"] == "HOT"].copy()
    warm_df = filtered_df[filtered_df["tier"] == "WARM"].copy()
    cold_df = filtered_df[filtered_df["tier"] == "COLD"].copy()

    hot_count = len(hot_df)
    warm_count = len(warm_df)
    cold_count = len(cold_df)
    total_count = len(filtered_df)

    col_config = {
        "tier_display": st.column_config.TextColumn("Tier", width="small"),
        "score": st.column_config.ProgressColumn("Lead Score", min_value=0, max_value=100, format="%d", width="small"),
        "company": st.column_config.TextColumn("Company", width="medium"),
        "name": st.column_config.TextColumn("Contact Name", width="medium"),
        "job_title": st.column_config.TextColumn("Role / Title", width="medium"),
        "email": st.column_config.TextColumn("Email Address", width="medium"),
        "template": st.column_config.TextColumn("Template", width="small"),
        "opens": st.column_config.NumberColumn("Opens", width="small"),
        "clicks": st.column_config.NumberColumn("Clicks", width="small"),
        "activity_summary": st.column_config.TextColumn("Engagement Signals", width="large"),
        "reply_preview": st.column_config.TextColumn("Customer Reply Preview", width="large"),
        "status": st.column_config.TextColumn("Status", width="small"),
    }

    # ── Tabs: Hot Leads, Warm Leads, Cold Leads, All Leads ──
    tab_hot, tab_warm, tab_cold, tab_all = st.tabs([
        f"🔥 Hot Leads ({hot_count})",
        f"⚡ Warm Leads ({warm_count})",
        f"❄️ Cold Leads ({cold_count})",
        f"📋 All Leads ({total_count})",
    ])

    # 1. TAB: HOT LEADS
    with tab_hot:
        if hot_df.empty:
            st.info("No Hot leads found under the current selection.")
        else:
            h_df_sorted = hot_df.sort_values(by=["score", "opens"], ascending=False)
            h_clean = build_clean_dataframe(h_df_sorted)

            row_top_h1, row_top_h2, row_top_h3 = st.columns([3.0, 1.4, 0.9])
            with row_top_h1:
                st.caption(f"Showing **{len(h_clean)}** high-intent leads who replied to emails or clicked engagement links:")
            with row_top_h2:
                xlsx_h = generate_excel_export_bytes(h_clean, sheet_name="Hot Leads")
                st.download_button(
                    label="📥 Export Hot Leads (Excel)",
                    data=xlsx_h,
                    file_name="hot_leads.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_hot_clean_xlsx",
                    use_container_width=True,
                )
            with row_top_h3:
                csv_h = generate_csv_export_bytes(h_clean)
                st.download_button(
                    label="📄 CSV",
                    data=csv_h,
                    file_name="hot_leads.csv",
                    mime="text/csv",
                    key="dl_hot_clean_csv",
                    use_container_width=True,
                )

            st.dataframe(
                h_clean,
                use_container_width=True,
                hide_index=True,
                height=420,
                column_config=col_config,
            )

    # 2. TAB: WARM LEADS
    with tab_warm:
        if warm_df.empty:
            st.info("No Warm leads found under the current selection.")
        else:
            w_df_sorted = warm_df.sort_values(by=["score", "opens"], ascending=False)
            w_clean = build_clean_dataframe(w_df_sorted)

            row_top_w1, row_top_w2, row_top_w3 = st.columns([3.0, 1.4, 0.9])
            with row_top_w1:
                st.caption(f"Showing **{len(w_clean)}** active consideration leads who opened emails or clicked once:")
            with row_top_w2:
                xlsx_w = generate_excel_export_bytes(w_clean, sheet_name="Warm Leads")
                st.download_button(
                    label="📥 Export Warm Leads (Excel)",
                    data=xlsx_w,
                    file_name="warm_leads.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_warm_clean_xlsx",
                    use_container_width=True,
                )
            with row_top_w3:
                csv_w = generate_csv_export_bytes(w_clean)
                st.download_button(
                    label="📄 CSV",
                    data=csv_w,
                    file_name="warm_leads.csv",
                    mime="text/csv",
                    key="dl_warm_clean_csv",
                    use_container_width=True,
                )

            st.dataframe(
                w_clean,
                use_container_width=True,
                hide_index=True,
                height=420,
                column_config=col_config,
            )

    # 3. TAB: COLD LEADS
    with tab_cold:
        if cold_df.empty:
            st.info("No Cold leads found under the current selection.")
        else:
            c_clean = build_clean_dataframe(cold_df)

            row_top_c1, row_top_c2, row_top_c3 = st.columns([3.0, 1.4, 0.9])
            with row_top_c1:
                st.caption(f"Showing **{len(c_clean)}** leads awaiting first open or response:")
            with row_top_c2:
                xlsx_c = generate_excel_export_bytes(c_clean, sheet_name="Cold Leads")
                st.download_button(
                    label="📥 Export Cold Leads (Excel)",
                    data=xlsx_c,
                    file_name="cold_leads.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_cold_clean_xlsx",
                    use_container_width=True,
                )
            with row_top_c3:
                csv_c = generate_csv_export_bytes(c_clean)
                st.download_button(
                    label="📄 CSV",
                    data=csv_c,
                    file_name="cold_leads.csv",
                    mime="text/csv",
                    key="dl_cold_clean_csv",
                    use_container_width=True,
                )

            st.dataframe(
                c_clean,
                use_container_width=True,
                hide_index=True,
                height=420,
                column_config=col_config,
            )

    # 4. TAB: ALL LEADS
    with tab_all:
        if filtered_df.empty:
            st.info("No leads match the current filters.")
        else:
            all_clean = build_clean_dataframe(filtered_df)

            row_top_a1, row_top_a2, row_top_a3 = st.columns([3.0, 1.4, 0.9])
            with row_top_a1:
                st.caption(f"Showing all **{len(all_clean)}** real database records:")
            with row_top_a2:
                xlsx_all = generate_excel_export_bytes(all_clean, sheet_name="All Leads")
                st.download_button(
                    label="📥 Export All Leads (Excel)",
                    data=xlsx_all,
                    file_name="all_leads_master_db.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_all_clean_xlsx",
                    use_container_width=True,
                )
            with row_top_a3:
                csv_all = generate_csv_export_bytes(all_clean)
                st.download_button(
                    label="📄 CSV",
                    data=csv_all,
                    file_name="all_leads_master_db.csv",
                    mime="text/csv",
                    key="dl_all_clean_csv",
                    use_container_width=True,
                )

            st.dataframe(
                all_clean,
                use_container_width=True,
                hide_index=True,
                height=420,
                column_config=col_config,
            )

    # ── Sleek Lead Detail Viewer (CRM Profile Inspector) ──
    if not filtered_df.empty:
        st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
        st.markdown("""
        <div class="mdb-card-title">
            <span>🔎 Deep CRM Lead Inspection Profile</span>
            <span style="font-size:12px;font-weight:500;color:var(--text-muted);">Lifecycle, Chunk &amp; Activity Stream</span>
        </div>
        """, unsafe_allow_html=True)

        lead_records = filtered_df.to_dict(orient="records")
        lead_choices = [f"{l['email']}  ({l.get('company') or 'No Company'})" for l in lead_records]
        selected_lead_idx = st.selectbox(
            "Select lead to inspect",
            range(len(lead_choices)),
            format_func=lambda i: lead_choices[i],
            key="lead_detail_picker",
            label_visibility="collapsed",
        )

        if selected_lead_idx is not None:
            chosen_lead_id = lead_records[selected_lead_idx]["id"]
            _render_lead_profile_card(chosen_lead_id)


def _render_lead_profile_card(lead_id: str):
    """Renders an ultra-premium CRM profile card for a single lead."""
    is_dark = is_dark_mode()
    detail = fetch_cached_lead_detail(lead_id)

    if not detail:
        st.warning("Lead record not found.")
        return

    name = detail.get("full_name") or f"{detail.get('first_name', '') or ''} {detail.get('last_name', '') or ''}".strip() or "Unnamed Contact"
    email = detail["email"]
    company = detail.get("company") or "Independent"
    initial = (name[0] if name != "Unnamed Contact" else email[0]).upper()
    status_badge_html = render_status_badge(detail.get("current_status", "new"))

    # Top Profile Card
    header_html = f"""
    <div class="mdb-lead-header">
        <div style="display:flex;align-items:center;gap:18px;">
            <div class="mdb-avatar">{initial}</div>
            <div>
                <div style="display:flex;align-items:center;gap:10px;">
                    <span style="font-family:'Outfit',sans-serif;font-size:20px;font-weight:700;color:var(--text-primary);">{name}</span>
                    {status_badge_html}
                </div>
                <div style="font-size:13.5px;color:var(--text-muted);margin-top:2px;">
                    <strong>{email}</strong> &bull; {company}
                </div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--text-micro);margin-top:4px;">
                    UUID: {detail['id']}
                </div>
            </div>
        </div>
        <div style="display:flex;gap:12px;">
            <div style="text-align:right;">
                <div style="font-family:'JetBrains Mono';font-size:22px;font-weight:700;color:#3B82F6;">{detail.get('total_emails_sent', 0)}</div>
                <div style="font-size:11px;color:var(--text-muted);text-transform:uppercase;">Sent</div>
            </div>
            <div style="text-align:right;">
                <div style="font-family:'JetBrains Mono';font-size:22px;font-weight:700;color:#14B8A6;">{detail.get('total_replies', 0)}</div>
                <div style="font-size:11px;color:var(--text-muted);text-transform:uppercase;">Replies</div>
            </div>
            <div style="text-align:right;">
                <div style="font-family:'JetBrains Mono';font-size:22px;font-weight:700;color:#10B981;">{detail.get('total_opens', 0)}</div>
                <div style="font-size:11px;color:var(--text-muted);text-transform:uppercase;">Opens</div>
            </div>
        </div>
    </div>
    """
    st.markdown(clean_html(header_html), unsafe_allow_html=True)

    c_meta, c_outreach = st.columns([1.1, 1.4])

    with c_meta:
        linkedin = detail.get("linkedin_url")
        linkedin_link = f"<a href='{linkedin}' target='_blank' style='color:#3B82F6;'>View Profile ↗</a>" if linkedin else "—"
        website = detail.get("website")
        website_link = f"<a href='{website}' target='_blank' style='color:#3B82F6;'>{website} ↗</a>" if website else "—"

        meta_html = f"""
        <div class="mdb-card">
            <div class="mdb-card-title">
                <span>📋 Lead Attributes &amp; Telemetry</span>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;font-size:13px;">
                <div><span style="color:var(--text-muted);">Job Title:</span><br><strong>{detail.get('job_title') or '—'}</strong></div>
                <div><span style="color:var(--text-muted);">Industry:</span><br><strong>{detail.get('industry') or '—'}</strong></div>
                <div><span style="color:var(--text-muted);">Phone:</span><br><strong>{detail.get('phone') or '—'}</strong></div>
                <div><span style="color:var(--text-muted);">Location:</span><br><strong>{detail.get('location') or '—'}</strong></div>
                <div><span style="color:var(--text-muted);">Lead Source:</span><br><strong>{detail.get('lead_source') or 'Bulk Import'}</strong></div>
                <div><span style="color:var(--text-muted);">Booking Status:</span><br><strong>{detail.get('booking_status') or 'None'}</strong></div>
                <div><span style="color:var(--text-muted);">LinkedIn:</span><br>{linkedin_link}</div>
                <div><span style="color:var(--text-muted);">Website:</span><br>{website_link}</div>
            </div>
        </div>
        """
        st.markdown(clean_html(meta_html), unsafe_allow_html=True)

    with c_outreach:
        oh = detail.get("outreach_history", [])
        if oh:
            st.markdown("""
            <div class="mdb-card">
                <div class="mdb-card-title">
                    <span>📬 Outreach Campaign History</span>
                    <span style="font-size:12px;color:var(--text-muted);">Multi-Touch Touches</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            oh_list = []
            for item in oh:
                oh_list.append({
                    "Template": item.get("template_name") or item.get("template_id") or "Generic",
                    "Status": item.get("status", "sent").title(),
                    "Sent Date": item.get("sent_at")[:10] if item.get("sent_at") else "—",
                    "Opened": "👁️ Yes" if item.get("opened") else "—",
                    "Replied": "💬 Yes" if item.get("replied") else "—",
                    "Booked": "🎯 Yes" if item.get("booked") else "—",
                })
            st.dataframe(pd.DataFrame(oh_list), use_container_width=True, hide_index=True)
        else:
            st.markdown("""
            <div class="mdb-card" style="text-align:center;padding:32px 20px;">
                <div style="font-size:28px;margin-bottom:6px;">📭</div>
                <div style="font-size:14px;font-weight:600;color:var(--text-primary);">No Outreach Dispatched Yet</div>
                <div style="font-size:12px;color:var(--text-muted);margin-top:4px;">Lead is staged in master database. Assign a chunk to initiate sending.</div>
            </div>
            """, unsafe_allow_html=True)

    # Activity Timeline & Chunks
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    c_tl, c_chk = st.columns([1.5, 1.0])

    with c_tl:
        timeline = detail.get("timeline", [])
        if timeline:
            icon_map = {
                "lead_imported": "📥", "assigned_to_chunk": "📦", "template_assigned": "🏷️",
                "email_sent": "📧", "email_opened": "👁️", "link_clicked": "🔗",
                "reply_received": "💬", "meeting_booked": "🎯", "status_changed": "🔄",
            }
            ev_items = []
            for ev in timeline[:12]:
                ev_icon = icon_map.get(ev.get("type"), "•")
                ev_ts = ev.get("created_at")[:16].replace("T", " ") if ev.get("created_at") else ""
                desc = ev.get("description") or ev.get("type", "").replace("_", " ").title()
                ev_items.append(f"""
                <div class="mdb-timeline-row">
                    <div class="mdb-timeline-dot">{ev_icon}</div>
                    <div class="mdb-timeline-box">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <span style="font-size:12.5px;font-weight:600;color:var(--text-primary);">{desc}</span>
                            <span style="font-family:'JetBrains Mono';font-size:10.5px;color:var(--text-micro);">{ev_ts}</span>
                        </div>
                    </div>
                </div>
                """)
            tl_html = f"""
            <div class="mdb-card">
                <div class="mdb-card-title">
                    <span>🕐 Chronological Event Stream</span>
                </div>
                <div class="mdb-timeline-wrap">
                    {''.join(ev_items)}
                </div>
            </div>
            """
            st.markdown(clean_html(tl_html), unsafe_allow_html=True)

    with c_chk:
        chunks = detail.get("chunks", [])
        if chunks:
            chunk_items = []
            for ch in chunks:
                ch_status = render_status_badge(ch.get("status", "READY"))
                elig_txt = "<span style='color:#10B981;font-weight:600;'>● Eligible</span>" if ch.get("eligible") else "<span style='color:#EF4444;font-weight:600;'>● Excluded (Dup)</span>"
                chunk_items.append(f"""
                <div style="padding:10px 0;border-bottom:1px solid var(--border-subtle);font-size:12.5px;">
                    <div style="font-weight:700;color:var(--text-primary);">{ch.get('chunk_name')}</div>
                    <div style="font-size:11.5px;color:var(--text-muted);margin:3px 0;">Template: {ch.get('template_name') or 'Pending'}</div>
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-top:6px;">
                        {ch_status}
                        <span style="font-size:11px;">{elig_txt}</span>
                    </div>
                </div>
                """)
            chk_html = f"""
            <div class="mdb-card">
                <div class="mdb-card-title">
                    <span>📦 Chunk Memberships</span>
                </div>
                {''.join(chunk_items)}
            </div>
            """
            st.markdown(clean_html(chk_html), unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# TAB 3: 📥 LEAD INGESTION & DEDUPLICATION HUB
# ─────────────────────────────────────────────────────────────

def _render_tab_ingestion():
    """Renders a guided 4-step pipeline for uploading, deduplicating, previewing, and chunking leads."""
    is_dark = is_dark_mode()

    st.markdown("""
    <div style="margin-bottom:18px;">
        <h2 style="margin:0 0 4px 0;font-size:20px;font-weight:700;color:var(--text-primary);letter-spacing:-0.015em;">📥 Intelligent Lead Ingestion &amp; Deduplication Hub</h2>
        <p style="margin:0;font-size:13px;color:var(--text-muted);">Upload lead lists. The system performs pre-flight deduplication, detects template collisions, and creates delivery-optimized chunks.</p>
    </div>
    """, unsafe_allow_html=True)

    # Visual 4-Step Pipeline Header
    stepper_html = f"""
    <div class="mdb-stepper">
        <div class="mdb-step-item">
            <div class="mdb-step-num">1</div>
            <div>
                <div class="mdb-step-title">Upload List</div>
                <div class="mdb-step-sub">CSV or XLSX File</div>
            </div>
        </div>
        <div class="mdb-step-item">
            <div class="mdb-step-num">2</div>
            <div>
                <div class="mdb-step-title">Column Mapping</div>
                <div class="mdb-step-sub">Smart Auto-Detect</div>
            </div>
        </div>
        <div class="mdb-step-item">
            <div class="mdb-step-num">3</div>
            <div>
                <div class="mdb-step-title">Pre-Flight Check</div>
                <div class="mdb-step-sub">Deduplication Preview</div>
            </div>
        </div>
        <div class="mdb-step-item">
            <div class="mdb-step-num">4</div>
            <div>
                <div class="mdb-step-title">Chunk &amp; Commit</div>
                <div class="mdb-step-sub">Safe Staged Delivery</div>
            </div>
        </div>
    </div>
    """
    st.markdown(clean_html(stepper_html), unsafe_allow_html=True)

    # Step 1: Upload File
    uploaded_file = st.file_uploader(
        "Upload Lead Dataset",
        type=["csv", "xlsx", "xls"],
        key="uploader_master_db",
        help="Upload CSV or Excel files. Required column: Email. Supported: Full Name, Company, Job Title, Phone, Industry, Location, LinkedIn URL.",
    )

    if uploaded_file:
        try:
            if uploaded_file.name.lower().endswith(".csv"):
                df_raw = pd.read_csv(uploaded_file)
                file_type = "csv"
            else:
                df_raw = pd.read_excel(uploaded_file)
                file_type = "xlsx"
        except Exception as e:
            st.error(f"Error reading file: {e}")
            return

        st.success(f"📁 Parsed **{uploaded_file.name}** — **{len(df_raw)}** rows, **{len(df_raw.columns)}** columns detected.")

        # Ingestion Configuration
        c_conf1, c_conf2 = st.columns(2)
        with c_conf1:
            chunk_size = st.selectbox(
                "Chunk Batch Size",
                [10, 20, 25, 50, 100],
                index=2,
                help="Splits leads into manageable batches for staged outreach and deliverability protection.",
                key="cfg_chunk_size",
            )
        with c_conf2:
            all_tpls = load_all_templates()
            tpl_choices = [{"id": None, "name": "— Assign Later in Chunks Tab —"}]
            tpl_choices += [{"id": t["id"], "name": f"{t['name']}"} for t in all_tpls]
            selected_idx = st.selectbox(
                "Pre-Assign Template (Optional)",
                range(len(tpl_choices)),
                format_func=lambda i: tpl_choices[i]["name"],
                key="cfg_template_choice",
                help="Assigning a template now enables template-specific deduplication checks.",
            )
            pre_tpl_id = tpl_choices[selected_idx]["id"]
            pre_tpl_name = tpl_choices[selected_idx]["name"] if pre_tpl_id else None

        # Pre-Flight Preview Button
        if st.button("🔍 Run Deduplication & Pre-Flight Check", type="primary", use_container_width=True, key="btn_run_preview"):
            db = SessionLocal()
            try:
                with st.spinner("Analyzing emails, identifying duplicates, and checking collisions..."):
                    preview = generate_import_preview(db, df_raw, template_id=pre_tpl_id, filename=uploaded_file.name)
            finally:
                db.close()

            if "error" in preview:
                st.error(preview["error"])
                return

            st.session_state.mdb_active_preview = preview
            st.session_state.mdb_raw_df = df_raw
            st.session_state.mdb_file_name = uploaded_file.name
            st.session_state.mdb_file_type = file_type
            st.session_state.mdb_chosen_chunk_size = chunk_size
            st.session_state.mdb_chosen_tpl_id = pre_tpl_id
            st.session_state.mdb_chosen_tpl_name = pre_tpl_name

        # Render Ingestion Pre-Flight Inspection
        if "mdb_active_preview" in st.session_state and st.session_state.mdb_active_preview:
            preview = st.session_state.mdb_active_preview
            st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
            st.markdown("""
            <div class="mdb-card-title">
                <span>🛡️ Pre-Flight Deduplication &amp; Impact Analysis</span>
                <span class="mdb-badge" style="background:#EFF6FF;color:#2563EB;border:1px solid #BFDBFE;">Validation Complete</span>
            </div>
            """, unsafe_allow_html=True)

            # Analysis Grid
            m1, m2, m3, m4, m5, m6 = st.columns(6)
            with m1:
                st.metric("Total Records", f"{preview['total_records']:,}")
            with m2:
                st.metric("Net-New Leads", f"{preview['new_leads']:,}", delta="Ready to add")
            with m3:
                st.metric("Existing Leads", f"{preview['existing_leads']:,}", delta="Will enrich")
            with m4:
                st.metric("Duplicate Rows", f"{preview['duplicate_leads']:,}", delta="Skipped", delta_color="inverse")
            with m5:
                st.metric("Valid Emails", f"{preview['valid_emails']:,}")
            with m6:
                st.metric("Template Dups", f"{preview['duplicate_template_sends']:,}", delta="Collision", delta_color="inverse")

            # Explanation Callout
            st.markdown(f"""
            <div style="background:{'rgba(16, 185, 129, 0.12)' if is_dark else '#F0FDF4'};border:1px solid {'rgba(16, 185, 129, 0.3)' if is_dark else '#BBF7D0'};border-radius:10px;padding:16px 20px;margin:16px 0;font-size:13.5px;color:{'#A7F3D0' if is_dark else '#166534'};line-height:1.6;">
                <strong>✅ What will happen upon confirmation:</strong><br>
                &bull; <strong>{preview['new_leads']}</strong> net-new leads will be added to the Master Database.<br>
                &bull; <strong>{preview['existing_leads']}</strong> existing leads will be enriched without creating duplicates.<br>
                &bull; <strong>{preview['duplicate_leads']}</strong> duplicate rows inside the file will be safely skipped.<br>
                &bull; Leads will be split into <strong>{max(1, (preview['new_leads'] + preview['existing_leads']) // st.session_state.mdb_chosen_chunk_size + (1 if (preview['new_leads'] + preview['existing_leads']) % st.session_state.mdb_chosen_chunk_size else 0))}</strong> chunks of size <strong>{st.session_state.mdb_chosen_chunk_size}</strong>.
            </div>
            """, unsafe_allow_html=True)

            # Confirm Commit Action
            if st.button("🚀 Confirm Ingestion & Generate Chunks", type="primary", use_container_width=True, key="btn_confirm_ingest"):
                db = SessionLocal()
                try:
                    with st.spinner("Ingesting into Master Database and generating chunks..."):
                        res = confirm_import(
                            db,
                            st.session_state.mdb_raw_df,
                            filename=st.session_state.mdb_file_name,
                            file_type=st.session_state.mdb_file_type,
                            chunk_size=st.session_state.mdb_chosen_chunk_size,
                            template_id=st.session_state.mdb_chosen_tpl_id,
                            template_name=st.session_state.mdb_chosen_tpl_name,
                            column_mapping=preview.get("column_mapping"),
                        )
                finally:
                    db.close()

                if "error" in res:
                    st.error(res["error"])
                else:
                    st.success(f"""
                    🎉 **Import & Chunking Successfully Completed!**
                    - Import Code: **`{res['import_code']}`**
                    - Net-New Leads Added: **{res['new_leads']}**
                    - Existing Leads Enriched: **{res['existing_leads']}**
                    - Duplicates Suppressed: **{res['duplicates']}**
                    - Chunks Generated: **{res['chunks_created']}** (Size: {res['chunk_size']})
                    """)
                    st.balloons()
                    st.cache_data.clear()
                    for k in ["mdb_active_preview", "mdb_raw_df", "mdb_file_name", "mdb_file_type",
                              "mdb_chosen_chunk_size", "mdb_chosen_tpl_id", "mdb_chosen_tpl_name"]:
                        if k in st.session_state:
                            del st.session_state[k]


# ─────────────────────────────────────────────────────────────
# TAB 4: 📦 INTELLIGENT CHUNK MANAGEMENT
# ─────────────────────────────────────────────────────────────

def _render_tab_chunks():
    """Renders chunk queue, template assignments, and state transitions."""
    is_dark = is_dark_mode()

    st.markdown("""
    <div style="margin-bottom:14px;">
        <h2 style="margin:0 0 2px 0;font-size:20px;font-weight:700;color:var(--text-primary);letter-spacing:-0.015em;">📦 Intelligent Batch Chunk Management</h2>
        <p style="margin:0;font-size:13px;color:var(--text-muted);">Review chunk queues, perform human-in-the-loop template assignment, and control outreach progression.</p>
    </div>
    """, unsafe_allow_html=True)

    chunks = fetch_cached_chunks()

    if not chunks:
        st.info("No chunks created yet. Import leads via the **Lead Ingestion & Deduplication** tab to generate chunks automatically.")
        return

    # Chunks Summary Overview
    chunk_table = []
    for c in chunks:
        chunk_table.append({
            "Chunk": c["chunk_name"],
            "Leads": c["total_leads"],
            "Eligible": c["eligible_leads"],
            "Excluded (Dup)": c["duplicate_template_leads"],
            "Template": c["template_name"] or "— Needs Template —",
            "Status": c["processing_status"],
            "Sent": c["sent_count"],
            "Replies": c["reply_count"],
            "Created": c["created_at"][:10] if c["created_at"] else "—",
        })
    df_chunks = pd.DataFrame(chunk_table)

    st.dataframe(
        df_chunks,
        use_container_width=True,
        hide_index=True,
        height=320,
        column_config={
            "Leads": st.column_config.NumberColumn("Total Leads", format="%d"),
            "Eligible": st.column_config.NumberColumn("Eligible", format="%d"),
            "Excluded (Dup)": st.column_config.NumberColumn("Excluded", format="%d"),
        }
    )

    # ── Interactive Chunk Workstation ──
    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div class="mdb-card-title">
        <span>🔧 Human-in-the-Loop Chunk Workstation</span>
        <span style="font-size:12px;font-weight:500;color:var(--text-muted);">Assign Templates &amp; Transition State</span>
    </div>
    """, unsafe_allow_html=True)

    chunk_labels = [f"{c['chunk_name']} &bull; {c['total_leads']} leads &bull; [{c['processing_status']}]" for c in chunks]
    sel_chunk_idx = st.selectbox(
        "Select Chunk to Configure",
        range(len(chunk_labels)),
        format_func=lambda i: chunk_labels[i],
        key="station_chunk_select",
        label_visibility="collapsed",
    )

    if sel_chunk_idx is not None:
        chunk = chunks[sel_chunk_idx]
        chunk_id = chunk["id"]
        status_badge = render_status_badge(chunk["processing_status"])

        c_info, c_action = st.columns([1.2, 1.2])

        with c_info:
            sent = chunk.get("sent_count", 0)
            total = max(chunk.get("eligible_leads", 1), 1)
            pct = min(100, int((sent / total) * 100))

            card_html = f"""
            <div class="mdb-card">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                    <span style="font-family:'Outfit',sans-serif;font-size:18px;font-weight:700;color:var(--text-primary);">{chunk['chunk_name']}</span>
                    {status_badge}
                </div>
                <div style="font-size:13px;color:var(--text-secondary);line-height:1.8;">
                    <div>Assigned Template: <strong>{chunk.get('template_name') or 'Not Assigned Yet'}</strong></div>
                    <div>Total Leads: <strong>{chunk.get('total_leads', 0)}</strong> &bull; Eligible: <strong>{chunk.get('eligible_leads', 0)}</strong></div>
                    <div>Excluded (Template Collision): <strong>{chunk.get('duplicate_template_leads', 0)}</strong></div>
                    <div>Outreach Dispatched: <strong>{sent}</strong> / {total}</div>
                </div>
                <div class="mdb-progress-track">
                    <div class="mdb-progress-fill" style="width:{pct}%;"></div>
                </div>
                <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text-muted);margin-top:4px;">
                    <span>Outreach Progress</span>
                    <span>{pct}%</span>
                </div>
            </div>
            """
            st.markdown(clean_html(card_html), unsafe_allow_html=True)

        with c_action:
            st.markdown("""
            <div class="mdb-card">
                <div class="mdb-card-title">
                    <span>🏷️ Template &amp; Dispatch Controls</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            templates = load_all_templates()
            if templates:
                tpl_idx = st.selectbox(
                    "Assign Email Template",
                    range(len(templates)),
                    format_func=lambda i: templates[i]["name"],
                    key=f"sel_assign_tpl_{chunk_id}",
                )
                excl_dups = st.checkbox(
                    "Exclude leads who previously received this template",
                    value=True,
                    key=f"chk_excl_{chunk_id}",
                )

                if st.button("🏷️ Assign Template to Chunk", type="primary", use_container_width=True, key=f"btn_assign_tpl_{chunk_id}"):
                    db = SessionLocal()
                    try:
                        res = assign_template_to_chunk(
                            db,
                            chunk_id,
                            template_id=templates[tpl_idx]["id"],
                            template_name=templates[tpl_idx]["name"],
                            exclude_duplicates=excl_dups,
                        )
                    finally:
                        db.close()

                    if "error" in res:
                        st.error(res["error"])
                    else:
                        st.success(f"✅ Template assigned! {res['eligible_leads']} leads eligible, {res['duplicate_template_leads']} duplicates excluded.")
                        st.cache_data.clear()
                        st.rerun()

            # Lifecycle Transition Controls
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            t_col1, t_col2 = st.columns(2)
            with t_col1:
                if chunk["processing_status"] in ("TEMPLATE_ASSIGNED", "PAUSED"):
                    if st.button("🚀 Mark as READY", use_container_width=True, key=f"btn_ready_{chunk_id}"):
                        db = SessionLocal()
                        try:
                            transition_chunk_status(db, chunk_id, "READY")
                        finally:
                            db.close()
                        st.cache_data.clear()
                        st.rerun()

                elif chunk["processing_status"] == "READY":
                    if st.button("▶️ Start Outreach", type="primary", use_container_width=True, key=f"btn_start_{chunk_id}"):
                        db = SessionLocal()
                        try:
                            transition_chunk_status(db, chunk_id, "PROCESSING")
                        finally:
                            db.close()
                        st.cache_data.clear()
                        st.rerun()

            with t_col2:
                if chunk["processing_status"] == "PROCESSING":
                    if st.button("⏸️ Pause", use_container_width=True, key=f"btn_pause_{chunk_id}"):
                        db = SessionLocal()
                        try:
                            transition_chunk_status(db, chunk_id, "PAUSED")
                        finally:
                            db.close()
                        st.cache_data.clear()
                        st.rerun()
                    if st.button("✅ Mark Completed", use_container_width=True, key=f"btn_comp_{chunk_id}"):
                        db = SessionLocal()
                        try:
                            transition_chunk_status(db, chunk_id, "COMPLETED")
                        finally:
                            db.close()
                        st.cache_data.clear()
                        st.rerun()

        # Chunk Leads Inspection
        with st.expander(f"👥 Inspect All Leads in {chunk['chunk_name']}", expanded=False):
            db = SessionLocal()
            try:
                ch_leads = get_chunk_leads(db, chunk_id)
            finally:
                db.close()

            if ch_leads:
                ch_rows = []
                for cl in ch_leads:
                    ch_rows.append({
                        "Email": cl["email"],
                        "Name": cl.get("full_name") or "—",
                        "Company": cl.get("company") or "—",
                        "Status": cl.get("current_status", "new").title(),
                        "Eligible": "✅ Eligible" if cl.get("eligible") else "❌ Excluded",
                        "Duplicate": "⚠️ Collision" if cl.get("duplicate_template") else "Clean",
                    })
                st.dataframe(pd.DataFrame(ch_rows), use_container_width=True, hide_index=True)
            else:
                st.info("No leads mapped in this chunk.")


# ─────────────────────────────────────────────────────────────
# TAB 5: 🏷️ TEMPLATE PERFORMANCE & MATRIX
# ─────────────────────────────────────────────────────────────

def _render_tab_templates():
    """Renders cross-chunk template performance and conversion matrix."""
    is_dark = is_dark_mode()

    st.markdown("""
    <div style="margin-bottom:14px;">
        <h2 style="margin:0 0 2px 0;font-size:20px;font-weight:700;color:var(--text-primary);letter-spacing:-0.015em;">🏷️ Template Performance &amp; Assignment Matrix</h2>
        <p style="margin:0;font-size:13px;color:var(--text-muted);">Measure response and conversion rates by outreach template across all active chunks.</p>
    </div>
    """, unsafe_allow_html=True)

    chunks = fetch_cached_chunks()

    assigned_chunks = [c for c in chunks if c.get("template_name")]
    unassigned_chunks = [c for c in chunks if not c.get("template_name")]

    if unassigned_chunks:
        st.markdown(f"""
        <div style="background:{'rgba(245, 158, 11, 0.12)' if is_dark else '#FFFBEB'};border:1px solid {'rgba(245, 158, 11, 0.3)' if is_dark else '#FDE68A'};border-radius:10px;padding:14px 18px;margin-bottom:16px;font-size:13px;color:{'#FCD34D' if is_dark else '#92400E'};">
            ⚠️ <strong>{len(unassigned_chunks)} Chunk(s)</strong> awaiting template assignment. Switch to the <strong>Intelligent Chunks</strong> tab to configure.
        </div>
        """, unsafe_allow_html=True)

    if assigned_chunks:
        # Group metrics by template
        tpl_map = {}
        for c in assigned_chunks:
            tname = c["template_name"]
            if tname not in tpl_map:
                tpl_map[tname] = {"chunks": 0, "leads": 0, "sent": 0, "replies": 0, "opens": 0, "booked": 0}
            tpl_map[tname]["chunks"] += 1
            tpl_map[tname]["leads"] += c.get("total_leads", 0)
            tpl_map[tname]["sent"] += c.get("sent_count", 0)
            tpl_map[tname]["replies"] += c.get("reply_count", 0)
            tpl_map[tname]["opens"] += c.get("open_count", 0)
            tpl_map[tname]["booked"] += c.get("booking_count", 0)

        matrix_rows = []
        for tname, stats in tpl_map.items():
            sent = stats["sent"]
            replies = stats["replies"]
            rate = f"{round((replies / max(sent, 1)) * 100, 1)}%" if sent > 0 else "—"
            matrix_rows.append({
                "Template": tname,
                "Chunks": stats["chunks"],
                "Target Leads": stats["leads"],
                "Sent": sent,
                "Opens": stats["opens"],
                "Replies": replies,
                "Booked": stats["booked"],
                "Reply Rate": rate,
            })
        st.dataframe(pd.DataFrame(matrix_rows), use_container_width=True, hide_index=True)

        # Plotly Comparison Chart
        st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
        t_names = [r["Template"][:28] + "..." if len(r["Template"]) > 28 else r["Template"] for r in matrix_rows]
        t_sent = [r["Sent"] for r in matrix_rows]
        t_replies = [r["Replies"] for r in matrix_rows]
        t_booked = [r["Booked"] for r in matrix_rows]

        fig_bar = go.Figure(data=[
            go.Bar(name="Sent", x=t_names, y=t_sent, marker_color="#3B82F6"),
            go.Bar(name="Replies", x=t_names, y=t_replies, marker_color="#8B5CF6"),
            go.Bar(name="Bookings", x=t_names, y=t_booked, marker_color="#10B981"),
        ])
        fig_bar.update_layout(
            barmode="group",
            margin=dict(t=20, b=40, l=10, r=10),
            height=320,
            xaxis=dict(tickangle=-15),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        apply_chart_theme(fig_bar, is_dark=is_dark)
        st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})

    else:
        st.info("No templates have been assigned to chunks yet.")


# ─────────────────────────────────────────────────────────────
# TAB 6: 📜 BATCH IMPORT HISTORY
# ─────────────────────────────────────────────────────────────

def _render_tab_import_history():
    """Renders all past file uploads, stats, and row-level breakdown."""
    is_dark = is_dark_mode()

    st.markdown("""
    <div style="margin-bottom:14px;">
        <h2 style="margin:0 0 2px 0;font-size:20px;font-weight:700;color:var(--text-primary);letter-spacing:-0.015em;">📜 Batch Import History &amp; Receipts</h2>
        <p style="margin:0;font-size:13px;color:var(--text-muted);">Historical logs of every uploaded lead list, duplicates prevented, and chunks produced.</p>
    </div>
    """, unsafe_allow_html=True)

    imports = fetch_cached_imports()

    if not imports:
        st.info("No batch imports recorded yet.")
        return

    imp_table = []
    for i in imports:
        imp_table.append({
            "Import Code": i.get("import_code") or i["id"][:8],
            "Filename": i["filename"],
            "Uploaded By": i["uploaded_by"],
            "Total": i["total_records"],
            "New Leads": i["new_leads"],
            "Enriched": i["existing_leads"],
            "Duplicates Filtered": i["duplicates"],
            "Chunks": i["chunks_created"],
            "Status": i["status"].title(),
            "Date": i["created_at"][:10] if i["created_at"] else "—",
        })
    st.dataframe(pd.DataFrame(imp_table), use_container_width=True, hide_index=True)

    # Batch Inspector
    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
    imp_labels = [f"{i.get('import_code', i['id'][:8])} &bull; {i['filename']}" for i in imports]
    sel_imp_idx = st.selectbox(
        "Select batch to inspect row-level actions",
        range(len(imp_labels)),
        format_func=lambda i: imp_labels[i],
        key="batch_inspector_select",
    )

    if sel_imp_idx is not None:
        target_imp_id = imports[sel_imp_idx]["id"]
        db = SessionLocal()
        try:
            detail = get_import_detail(db, target_imp_id)
        finally:
            db.close()

        if detail and detail.get("records"):
            rec_rows = []
            action_map = {
                "created": "🟢 New Lead Created",
                "existing": "🟡 Existing Lead Updated",
                "duplicate_lead": "🛡️ File Duplicate Suppressed",
                "duplicate_template": "⚠️ Template Collision Excluded",
                "invalid_email": "❌ Invalid Email Excluded",
            }
            for r in detail["records"][:100]:
                rec_rows.append({
                    "Row #": r["row"],
                    "Email": r["email"],
                    "System Action": action_map.get(r["action"], r["action"]),
                    "Notes": r.get("error") or "—",
                })
            st.dataframe(pd.DataFrame(rec_rows), use_container_width=True, hide_index=True, height=300)


# ─────────────────────────────────────────────────────────────
# TAB 7: 🕐 GLOBAL ACTIVITY TIMELINE
# ─────────────────────────────────────────────────────────────

def _render_tab_activity_timeline():
    """Renders real-time chronological stream of lead events across the enterprise."""
    is_dark = is_dark_mode()

    st.markdown("""
    <div style="margin-bottom:14px;">
        <h2 style="margin:0 0 2px 0;font-size:20px;font-weight:700;color:var(--text-primary);letter-spacing:-0.015em;">🕐 Global Real-Time Activity Feed</h2>
        <p style="margin:0;font-size:13px;color:var(--text-muted);">Unified event stream across lead ingestion, chunking, email dispatches, and replies.</p>
    </div>
    """, unsafe_allow_html=True)

    act_rows = fetch_cached_recent_activities(limit=50)

    if not act_rows:
        st.info("No activity recorded yet.")
        return

    icon_map = {
        "lead_imported": "📥", "assigned_to_chunk": "📦", "template_assigned": "🏷️",
        "email_sent": "📧", "email_opened": "👁️", "link_clicked": "🔗",
        "reply_received": "💬", "meeting_booked": "🎯", "status_changed": "🔄",
    }

    for ev in act_rows[:50]:
        icon = icon_map.get(ev["type"], "•")
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:12px;padding:8px 12px;background:var(--bg-surface);border:1px solid var(--border-subtle);border-radius:8px;margin-bottom:6px;">
            <span style="font-size:16px;">{icon}</span>
            <div style="flex:1;">
                <div style="font-size:13px;font-weight:600;color:var(--text-primary);">
                    {ev['name']} <span style="font-weight:400;color:var(--text-muted);">({ev['email']})</span>
                </div>
                <div style="font-size:12px;color:var(--text-secondary);margin-top:2px;">{ev['desc'] or ev['type']}</div>
            </div>
            <span style="font-family:'JetBrains Mono';font-size:11px;color:var(--text-micro);white-space:nowrap;">{ev['ts']}</span>
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# TAB 8: 📋 REGULATORY AUDIT LOG
# ─────────────────────────────────────────────────────────────

def _render_tab_audit_log():
    """Renders administrative audit log for security, compliance, and traceability."""
    is_dark = is_dark_mode()

    st.markdown("""
    <div style="margin-bottom:14px;">
        <h2 style="margin:0 0 2px 0;font-size:20px;font-weight:700;color:var(--text-primary);letter-spacing:-0.015em;">📋 Enterprise Security &amp; Regulatory Audit Trail</h2>
        <p style="margin:0;font-size:13px;color:var(--text-muted);">Immutable record of administrative actions, chunk modifications, and template assignments.</p>
    </div>
    """, unsafe_allow_html=True)

    logs = fetch_cached_audit_log(limit=200)

    if not logs:
        st.info("No audit logs recorded yet.")
        return

    audit_table = []
    for l in logs:
        audit_table.append({
            "Timestamp": l["created_at"][:16].replace("T", " ") if l["created_at"] else "—",
            "Actor": l["user"],
            "Action": l["action"],
            "Entity": (l.get("entity_type") or "System").title(),
            "Entity ID": (l.get("entity_id") or "")[:8],
            "Details": str(l.get("new_value") or "")[:90],
        })
    st.dataframe(pd.DataFrame(audit_table), use_container_width=True, hide_index=True, height=450)
