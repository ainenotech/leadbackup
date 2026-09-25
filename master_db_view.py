"""Master Database & CRM Intelligence — Executive Streamlit View
Single source of truth for all leads, deduplication engine, intelligent chunking,
human-in-the-loop template assignment, and end-to-end outreach lifecycle tracking.
Designed with enterprise aesthetics: dark & light mode native, Outfit/Inter typography,
interactive Plotly charts, and modern micro-components.
"""

import io
import os
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
from services.master_db_service import (
    generate_import_preview, confirm_import, normalize_email,
    get_dashboard_metrics, get_leads_paginated, get_lead_detail,
    get_all_chunks, get_chunk_leads, assign_template_to_chunk,
    transition_chunk_status, get_all_imports, get_import_detail,
    get_audit_log, get_templates_sent_to_lead, backfill_from_campaign_log,
    log_audit,
)
from services.template_service import load_all_templates
from utils.theme import apply_chart_theme, is_dark_mode


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

    return f"""
    <span class="mdb-badge" style="background:{bg};color:{color};border:1px solid {color}35;">
        <span style="font-size:10px;">{icon}</span>
        <span>{label}</span>
    </span>
    """


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

def render_master_db(df_logs: pd.DataFrame = None):
    """Main entry point for Master Database & CRM Intelligence."""
    is_dark = is_dark_mode()
    _inject_master_db_styles(is_dark)

    # Automatic initial sync check: ensure Master DB is populated with campaign logs & chunks
    if "mdb_initial_sync_done" not in st.session_state:
        db_chk = SessionLocal()
        try:
            m_cnt = db_chk.query(MasterLead).count()
            c_cnt = db_chk.query(LeadChunk).count()
            if m_cnt == 0 or c_cnt == 0:
                backfill_from_campaign_log(db_chk)
            st.session_state.mdb_initial_sync_done = True
        except Exception as _ex:
            print(f"[Master DB sync notice] {_ex}")
        finally:
            db_chk.close()

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

    # Master DB Sub-navigation
    tabs = st.tabs([
        "📊 Command Center",
        "👥 Leads Directory",
        "📥 Lead Ingestion & Deduplication",
        "📦 Intelligent Chunks",
        "🏷️ Template Performance",
        "📜 Batch History",
        "🕐 Global Timeline",
        "📋 Regulatory Audit Log",
    ])

    with tabs[0]:
        _render_tab_overview()

    with tabs[1]:
        _render_tab_leads_directory()

    with tabs[2]:
        _render_tab_ingestion()

    with tabs[3]:
        _render_tab_chunks()

    with tabs[4]:
        _render_tab_templates()

    with tabs[5]:
        _render_tab_import_history()

    with tabs[6]:
        _render_tab_activity_timeline()

    with tabs[7]:
        _render_tab_audit_log()


# ─────────────────────────────────────────────────────────────
# TAB 1: 📊 COMMAND CENTER (Executive Overview)
# ─────────────────────────────────────────────────────────────

def _render_tab_overview():
    """Renders executive KPI metrics, interactive Plotly charts, and system status."""
    is_dark = is_dark_mode()
    db = SessionLocal()
    try:
        metrics = get_dashboard_metrics(db)
    finally:
        db.close()

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

def _render_tab_leads_directory():
    """Renders search, filters, paginated table, and rich CRM profile inspector."""
    is_dark = is_dark_mode()

    st.markdown("""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
        <div>
            <h2 style="margin:0 0 2px 0;font-size:19px;font-weight:700;color:var(--text-primary);letter-spacing:-0.015em;">👥 Enterprise Leads Directory</h2>
            <p style="margin:0;font-size:13px;color:var(--text-muted);">Search, filter, and inspect leads across the unified master database.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Search and Filter Ribbon
    f_col1, f_col2, f_col3, f_col4 = st.columns([3.2, 1.4, 1.2, 1.0])
    with f_col1:
        search_query = st.text_input(
            "Search",
            placeholder="🔍 Search by email, name, company, or job title...",
            key="mdb_search_input",
            label_visibility="collapsed",
        )
    with f_col2:
        status_opts = ["all", "new", "active", "contacted", "replied", "booked", "unsubscribed", "bounced"]
        status_filter = st.selectbox(
            "Status",
            status_opts,
            format_func=lambda s: "All Statuses" if s == "all" else STATUS_CONFIG.get(s, {}).get("label", s.title()),
            key="mdb_status_select",
            label_visibility="collapsed",
        )
    with f_col3:
        page_size = st.selectbox(
            "Page Size",
            [25, 50, 100],
            index=1,
            key="mdb_pagesize_select",
            label_visibility="collapsed",
        )

    def _reset_mdb_filters():
        st.session_state.mdb_search_input = ""
        st.session_state.mdb_status_select = "all"
        st.session_state.mdb_page = 1

    with f_col4:
        st.button("Reset", use_container_width=True, key="mdb_reset_filters", on_click=_reset_mdb_filters)

    if "mdb_page" not in st.session_state:
        st.session_state.mdb_page = 1

    db = SessionLocal()
    try:
        result = get_leads_paginated(
            db,
            page=st.session_state.mdb_page,
            page_size=page_size,
            search=search_query if search_query.strip() else None,
            status_filter=status_filter if status_filter != "all" else None,
        )
    finally:
        db.close()

    leads = result["leads"]
    total_count = result["total"]
    total_pages = result["total_pages"]

    # Table Header Metrics
    st.markdown(f"""
    <div style="display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid var(--border-subtle);margin-bottom:10px;">
        <span style="font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--text-muted);">
            Showing <strong style="color:var(--text-primary);">{len(leads)}</strong> of <strong style="color:var(--text-primary);">{total_count:,}</strong> records
        </span>
        <span style="font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--text-muted);">
            Page <strong>{st.session_state.mdb_page}</strong> of <strong>{total_pages}</strong>
        </span>
    </div>
    """, unsafe_allow_html=True)

    if leads:
        table_rows = []
        for l in leads:
            name_val = l.get("full_name") or f"{l.get('first_name', '') or ''} {l.get('last_name', '') or ''}".strip() or "—"
            table_rows.append({
                "ID": l["id"][:8],
                "Name": name_val,
                "Email": l["email"],
                "Company": l.get("company") or "—",
                "Job Title": l.get("job_title") or "—",
                "Status": l.get("current_status", "new").title(),
                "Sent": l.get("total_emails_sent", 0),
                "Replies": l.get("total_replies", 0),
                "Score": round(float(l.get("engagement_score") or 0.0), 1),
                "Booking": l.get("booking_status") or "—",
                "Ingested": l.get("created_at")[:10] if l.get("created_at") else "—",
            })
        df_view = pd.DataFrame(table_rows)

        st.dataframe(
            df_view,
            use_container_width=True,
            hide_index=True,
            height=400,
            column_config={
                "ID": st.column_config.TextColumn("ID", width="small"),
                "Score": st.column_config.ProgressColumn("Engagement", min_value=0, max_value=100, format="%.0f"),
                "Sent": st.column_config.NumberColumn("Sent", format="%d"),
                "Replies": st.column_config.NumberColumn("Replies", format="%d"),
            }
        )

        # Pagination Bar
        p_prev, p_info, p_next = st.columns([1.2, 2.6, 1.2])
        with p_prev:
            if st.button("← Previous", disabled=st.session_state.mdb_page <= 1, use_container_width=True, key="btn_pg_prev"):
                st.session_state.mdb_page -= 1
                st.rerun()
        with p_info:
            st.markdown(f"<div style='text-align:center;padding-top:6px;font-size:12px;color:var(--text-muted);font-family:\"JetBrains Mono\";'>Viewing batch {st.session_state.mdb_page} / {total_pages}</div>", unsafe_allow_html=True)
        with p_next:
            if st.button("Next →", disabled=st.session_state.mdb_page >= total_pages, use_container_width=True, key="btn_pg_next"):
                st.session_state.mdb_page += 1
                st.rerun()

        # ── Sleek Lead Detail Viewer (CRM Profile Inspector) ──
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        st.markdown("""
        <div class="mdb-card-title">
            <span>🔎 Deep CRM Lead Inspection Profile</span>
            <span style="font-size:12px;font-weight:500;color:var(--text-muted);">Lifecycle, Chunk &amp; Activity Stream</span>
        </div>
        """, unsafe_allow_html=True)

        lead_choices = [f"{l['email']}  ({l.get('company') or 'No Company'})" for l in leads]
        selected_lead_idx = st.selectbox(
            "Select lead to inspect",
            range(len(lead_choices)),
            format_func=lambda i: lead_choices[i],
            key="lead_detail_picker",
            label_visibility="collapsed",
        )

        if selected_lead_idx is not None:
            chosen_lead_id = leads[selected_lead_idx]["id"]
            _render_lead_profile_card(chosen_lead_id)

    else:
        st.info("No leads match your search criteria. Try a different query or upload leads via the **Lead Ingestion & Deduplication** tab.")


def _render_lead_profile_card(lead_id: str):
    """Renders an ultra-premium CRM profile card for a single lead."""
    is_dark = is_dark_mode()
    db = SessionLocal()
    try:
        detail = get_lead_detail(db, lead_id)
    finally:
        db.close()

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
            st.markdown("""
            <div class="mdb-card">
                <div class="mdb-card-title">
                    <span>🕐 Chronological Event Stream</span>
                </div>
                <div class="mdb-timeline-wrap">
            """, unsafe_allow_html=True)
            icon_map = {
                "lead_imported": "📥", "assigned_to_chunk": "📦", "template_assigned": "🏷️",
                "email_sent": "📧", "email_opened": "👁️", "link_clicked": "🔗",
                "reply_received": "💬", "meeting_booked": "🎯", "status_changed": "🔄",
            }
            for ev in timeline[:12]:
                ev_icon = icon_map.get(ev.get("type"), "•")
                ev_ts = ev.get("created_at")[:16].replace("T", " ") if ev.get("created_at") else ""
                desc = ev.get("description") or ev.get("type", "").replace("_", " ").title()
                st.markdown(f"""
                <div class="mdb-timeline-row">
                    <div class="mdb-timeline-dot">{ev_icon}</div>
                    <div class="mdb-timeline-box">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <span style="font-size:12.5px;font-weight:600;color:var(--text-primary);">{desc}</span>
                            <span style="font-family:'JetBrains Mono';font-size:10.5px;color:var(--text-micro);">{ev_ts}</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown("</div></div>", unsafe_allow_html=True)

    with c_chk:
        chunks = detail.get("chunks", [])
        if chunks:
            st.markdown("""
            <div class="mdb-card">
                <div class="mdb-card-title">
                    <span>📦 Chunk Memberships</span>
                </div>
            """, unsafe_allow_html=True)
            for ch in chunks:
                ch_status = render_status_badge(ch.get("status", "READY"))
                elig_txt = "<span style='color:#10B981;'>● Eligible</span>" if ch.get("eligible") else "<span style='color:#EF4444;'>● Excluded (Dup)</span>"
                st.markdown(f"""
                <div style="padding:10px 0;border-bottom:1px solid var(--border-subtle);font-size:12.5px;">
                    <div style="font-weight:700;color:var(--text-primary);">{ch.get('chunk_name')}</div>
                    <div style="font-size:11.5px;color:var(--text-muted);margin:3px 0;">Template: {ch.get('template_name') or 'Pending'}</div>
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-top:4px;">
                        {ch_status}
                        <span style="font-size:11px;">{elig_txt}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)


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

    db = SessionLocal()
    try:
        chunks = get_all_chunks(db)
    finally:
        db.close()

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
                        st.rerun()

                elif chunk["processing_status"] == "READY":
                    if st.button("▶️ Start Outreach", type="primary", use_container_width=True, key=f"btn_start_{chunk_id}"):
                        db = SessionLocal()
                        try:
                            transition_chunk_status(db, chunk_id, "PROCESSING")
                        finally:
                            db.close()
                        st.rerun()

            with t_col2:
                if chunk["processing_status"] == "PROCESSING":
                    if st.button("⏸️ Pause", use_container_width=True, key=f"btn_pause_{chunk_id}"):
                        db = SessionLocal()
                        try:
                            transition_chunk_status(db, chunk_id, "PAUSED")
                        finally:
                            db.close()
                        st.rerun()
                    if st.button("✅ Mark Completed", use_container_width=True, key=f"btn_comp_{chunk_id}"):
                        db = SessionLocal()
                        try:
                            transition_chunk_status(db, chunk_id, "COMPLETED")
                        finally:
                            db.close()
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

    db = SessionLocal()
    try:
        chunks = get_all_chunks(db)
    finally:
        db.close()

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

    db = SessionLocal()
    try:
        imports = get_all_imports(db)
    finally:
        db.close()

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

    db = SessionLocal()
    try:
        activities = db.query(LeadActivity).order_by(LeadActivity.created_at.desc()).limit(150).all()
        act_rows = []
        for a in activities:
            lead = db.query(MasterLead).filter(MasterLead.id == a.master_lead_id).first()
            act_rows.append({
                "type": a.activity_type,
                "desc": a.description,
                "email": lead.email if lead else "—",
                "name": lead.full_name if lead else "—",
                "ts": a.created_at.strftime("%Y-%m-%d %H:%M") if a.created_at else "",
            })
    finally:
        db.close()

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

    db = SessionLocal()
    try:
        logs = get_audit_log(db, limit=200)
    finally:
        db.close()

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
