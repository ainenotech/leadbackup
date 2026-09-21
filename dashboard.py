import base64
from datetime import datetime
import json as _json
import os
import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

@st.cache_data
def get_image_base64(image_path: str) -> str:
    if os.path.exists(image_path):
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    return ""

load_dotenv(override=True)

import importlib
import Email.outlook_mailer
importlib.reload(Email.outlook_mailer)
import Email
importlib.reload(Email)
import Backend.crud
importlib.reload(Backend.crud)
import Email.draft_options
importlib.reload(Email.draft_options)

from Agent.agents.composer import compose_email
from Backend.crud import (
    approve_and_send_entry,
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
import importlib
import services.analytics_service
import services.analytics_export
import analytics_view
try:
    importlib.reload(services.analytics_service)
    importlib.reload(services.analytics_export)
    importlib.reload(analytics_view)
except Exception:
    pass

import reply_worker
try:
    importlib.reload(reply_worker)
except Exception:
    pass
from reply_worker import ReplyDaemonManager, check_and_reply_inbox
from analytics_view import render_analytics

init_db()

# Auto-start continuous real-time background sync (Outlook replies & Bookings Excel)
if not ReplyDaemonManager.is_running():
    ReplyDaemonManager.start(interval_seconds=15)

st.set_page_config(
    page_title="AINeotechnology | Lead Outreach & Intelligence",
    layout="wide",
    page_icon="⚡",
    initial_sidebar_state="expanded",
)

# Auto-expand sidebar if it was collapsed from a previous session
if "sidebar_checked" not in st.session_state:
    st.session_state.sidebar_checked = True
    components.html(
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
        height=0,
        width=0,
    )

# ─────────────────────────────────────────────────────────────
# EXECUTIVE LIGHT THEME CSS — 100% Light Mode, Zero Dark Content
# ─────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
/* ── Perplexity AI Typography (Newsreader + Inter + JetBrains Mono) ── */
@import url('https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400..700;1,6..72,400..700&family=Inter:ital,wght@0,300..700;1,300..700&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* ── Perplexity AI Design Tokens ── */
:root {
    --bg-canvas: #FAFAF9;
    --bg-surface: #FFFFFF;
    --bg-elevated: #FFFFFF;
    --border-subtle: #E4E4E7;
    --border-strong: #D4D4D8;
    --text-primary: #18181B;
    --text-secondary: #3F3F46;
    --text-muted: #71717A;
    --text-micro: #A1A1AA;
    --brand-primary: #2563EB;
    --brand-hover: #1D4ED8;
    --brand-soft: #EFF6FF;
    --brand-border: #BFDBFE;
    --perplexity-teal: #0D9488;
    --perplexity-teal-soft: #F0FDFA;
    --perplexity-teal-border: #99F6E4;
    --success-primary: #0D9488;
    --success-soft: #F0FDFA;
    --success-border: #99F6E4;
    --warning-primary: #D97706;
    --warning-soft: #FFFBEB;
    --warning-border: #FDE68A;
    --danger-primary: #DC2626;
    --danger-soft: #FEF2F2;
    --danger-border: #FECACA;
    --ai-primary: #0D9488;
    --ai-soft: #F0FDFA;
    --ai-border: #99F6E4;
    --radius-lg: 12px;
    --radius-md: 8px;
    --radius-sm: 6px;
    --shadow-sm: 0 1px 3px 0 rgba(0, 0, 0, 0.04), 0 1px 2px -1px rgba(0, 0, 0, 0.02);
    --shadow-md: 0 4px 12px -2px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
    --shadow-lg: 0 10px 25px -5px rgba(0, 0, 0, 0.08), 0 8px 10px -6px rgba(0, 0, 0, 0.04);
}

/* ── Global Canvas & Resets ── */
html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    color: var(--text-primary) !important;
    background-color: var(--bg-canvas) !important;
    -webkit-font-smoothing: antialiased !important;
    -moz-osx-font-smoothing: grayscale !important;
    letter-spacing: -0.011em !important;
    line-height: 1.6 !important;
}

/* ── Perplexity Editorial Headings ── */
h1, h2, [data-testid="stMarkdownContainer"] h1, [data-testid="stMarkdownContainer"] h2 {
    font-family: 'Newsreader', Georgia, 'Source Serif 4', serif !important;
    font-weight: 600 !important;
    letter-spacing: -0.025em !important;
    color: var(--text-primary) !important;
    line-height: 1.25 !important;
}

h3, h4, h5, h6, [data-testid="stMarkdownContainer"] h3, [data-testid="stMarkdownContainer"] h4 {
    font-family: 'Inter', -apple-system, sans-serif !important;
    font-weight: 600 !important;
    letter-spacing: -0.015em !important;
    color: var(--text-secondary) !important;
}

p, [data-testid="stMarkdownContainer"] p {
    font-family: 'Inter', -apple-system, sans-serif !important;
    letter-spacing: -0.01em !important;
    line-height: 1.6 !important;
}

/* ── Monospace Citations, Chips & Codes ── */
code, pre, .mono-text {
    font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace !important;
    font-feature-settings: "zero", "tnum" !important;
}

[data-testid="stHeader"] {
    background: transparent !important;
}

/* Hide deploy & developer toolbar buttons on top-right */
[data-testid="stToolbarActions"],
[data-testid="stStatusWidget"],
[data-testid="stAppDeployButton"],
.stDeployButton,
#MainMenu, footer {
    display: none !important;
}

/* ── Sidebar Expand & Collapse Button Styling ── */
[data-testid="stExpandSidebarButton"] {
    display: inline-flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    background: #FFFFFF !important;
    border: 1px solid var(--border-strong) !important;
    border-radius: var(--radius-sm) !important;
    box-shadow: var(--shadow-sm) !important;
    padding: 6px 10px !important;
    margin: 10px 0 0 12px !important;
    transition: all 0.2s ease !important;
}
[data-testid="stExpandSidebarButton"]:hover {
    background: var(--brand-soft) !important;
    border-color: var(--brand-primary) !important;
}

[data-testid="stSidebarCollapseButton"] {
    background: #F8FAFC !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-sm) !important;
    padding: 4px 6px !important;
    transition: all 0.2s ease !important;
}
[data-testid="stSidebarCollapseButton"]:hover {
    background: var(--brand-soft) !important;
    color: var(--brand-primary) !important;
}

/* ── Sidebar Navigation ── */
section[data-testid="stSidebar"] {
    background-color: #FFFFFF !important;
    border-right: 1px solid var(--border-subtle) !important;
    box-shadow: 2px 0 12px rgba(15, 23, 42, 0.02) !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    padding-top: 1rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
}

.sidebar-brand-card {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    padding: 14px 16px;
    background: linear-gradient(135deg, #0B1120 0%, #0F172A 60%, #1E293B 100%);
    border: 1px solid #1E293B;
    border-radius: var(--radius-md);
    margin-bottom: 18px;
    box-shadow: 0 4px 14px -2px rgba(15, 23, 42, 0.12), inset 0 1px 0 rgba(255, 255, 255, 0.05);
    transition: all 0.2s ease;
}
.sidebar-brand-card:hover {
    border-color: rgba(59, 130, 246, 0.35);
    box-shadow: 0 6px 20px -2px rgba(37, 99, 235, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.08);
}
.sidebar-brand-logo-wrapper {
    width: 100%;
    display: flex;
    align-items: center;
}
.sidebar-brand-logo-img {
    height: 32px;
    max-width: 100%;
    width: auto;
    object-fit: contain;
    display: block;
}
.sidebar-brand-subtitle {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 10px !important;
    font-weight: 600 !important;
    color: #94A3B8 !important;
    margin: 8px 0 0 0 !important;
    letter-spacing: 0.05em !important;
    text-transform: uppercase !important;
    display: flex !important;
    align-items: center !important;
    gap: 6px !important;
}
.sidebar-brand-dot {
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background-color: #10B981;
    box-shadow: 0 0 6px rgba(16, 185, 129, 0.6);
}

/* Sidebar Nav Buttons */
section[data-testid="stSidebar"] .stButton > button {
    font-family: 'Inter', -apple-system, sans-serif !important;
    width: 100%;
    background: #FFFFFF !important;
    border: 1px solid transparent !important;
    color: var(--text-secondary) !important;
    text-align: left !important;
    padding: 10px 14px !important;
    border-radius: var(--radius-sm) !important;
    font-size: 13.5px !important;
    font-weight: 500 !important;
    letter-spacing: -0.01em !important;
    transition: all 0.15s ease !important;
    justify-content: flex-start !important;
    margin-bottom: 3px !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: #F4F4F5 !important;
    color: var(--text-primary) !important;
    border-color: var(--border-subtle) !important;
}
section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: var(--brand-soft) !important;
    color: var(--brand-primary) !important;
    font-weight: 600 !important;
    border: 1px solid var(--brand-border) !important;
    border-left: 4px solid var(--brand-primary) !important;
    box-shadow: var(--shadow-sm) !important;
}

/* Sidebar System Health Card */
.sidebar-health-card {
    background: #FFFFFF;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
    padding: 12px 14px;
    margin-top: 14px;
    box-shadow: var(--shadow-sm);
}
.sidebar-health-title {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 10.5px !important;
    font-weight: 600 !important;
    color: var(--text-muted) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.sidebar-health-row {
    font-family: 'Inter', sans-serif !important;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 12px;
    color: var(--text-secondary);
    padding: 3px 0;
    letter-spacing: -0.01em;
}
.health-pill {
    font-family: 'JetBrains Mono', monospace !important;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 7px;
    border-radius: 6px;
    font-size: 10.5px;
    font-weight: 600;
}
.health-pill-green {
    background: #F0FDFA;
    color: #0F766E;
    border: 1px solid #99F6E4;
}

/* ── Top Executive Header Banner ── */
.top-header-banner {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #FFFFFF;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 22px 28px;
    margin-bottom: 24px;
    box-shadow: var(--shadow-sm);
}
.top-header-title {
    font-family: 'Newsreader', Georgia, 'Source Serif 4', serif !important;
    font-size: 28px !important;
    font-weight: 600 !important;
    color: var(--text-primary) !important;
    letter-spacing: -0.025em !important;
    line-height: 1.25 !important;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 12px;
}
.top-header-desc {
    font-family: 'Inter', sans-serif !important;
    font-size: 13.5px !important;
    color: var(--text-muted) !important;
    margin: 6px 0 0 0;
    line-height: 1.55 !important;
    letter-spacing: -0.01em !important;
}
.top-header-badges {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
}

/* ── Modern KPI Grid with Pixel-Perfect Gaps ── */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
    margin-top: 4px;
    margin-bottom: 28px;
    width: 100%;
}
@media (max-width: 1100px) {
    .kpi-grid {
        grid-template-columns: repeat(2, 1fr);
        gap: 16px;
    }
}
@media (max-width: 680px) {
    .kpi-grid {
        grid-template-columns: 1fr;
    }
}

.kpi-card {
    background: #FFFFFF;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 22px 24px 20px 24px;
    box-shadow: var(--shadow-sm);
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    min-height: 148px;
}
.kpi-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.02);
    border-color: #CBD5E1;
}
.kpi-top-bar {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
}
.kpi-bar-blue   { background: linear-gradient(90deg, #2563EB, #60A5FA); }
.kpi-bar-amber  { background: linear-gradient(90deg, #F59E0B, #FCD34D); }
.kpi-bar-teal   { background: linear-gradient(90deg, #0D9488, #2DD4BF); }
.kpi-bar-cyan   { background: linear-gradient(90deg, #06B6D4, #67E8F9); }
.kpi-bar-purple { background: linear-gradient(90deg, #8B5CF6, #C4B5FD); }
.kpi-bar-rose   { background: linear-gradient(90deg, #F43F5E, #FDA4AF); }

.kpi-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
}
.kpi-label {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    color: var(--text-muted) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}
.kpi-icon-box {
    width: 36px;
    height: 36px;
    border-radius: 9px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 17px;
    flex-shrink: 0;
}
.kpi-value {
    font-family: 'Inter', -apple-system, sans-serif !important;
    font-feature-settings: "tnum", "cv02", "cv03", "cv04", "cv11" !important;
    font-size: 34px !important;
    font-weight: 700 !important;
    color: var(--text-primary) !important;
    line-height: 1.1 !important;
    letter-spacing: -0.035em !important;
    margin-bottom: 10px;
}
.kpi-micro {
    font-family: 'Inter', sans-serif !important;
    font-size: 12.5px !important;
    font-weight: 500 !important;
    color: var(--text-muted) !important;
    display: flex;
    align-items: center;
    gap: 6px;
    letter-spacing: -0.01em !important;
}
.kpi-pill {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    padding: 2.5px 7px;
    border-radius: 5px;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 11px !important;
    font-weight: 600;
    line-height: 1.2;
}
.kpi-pill-blue   { background: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE; }
.kpi-pill-amber  { background: #FFFBEB; color: #B45309; border: 1px solid #FDE68A; }
.kpi-pill-teal   { background: #F0FDFA; color: #0F766E; border: 1px solid #99F6E4; }
.kpi-pill-cyan   { background: #ECFEFF; color: #0E7490; border: 1px solid #A5F3FC; }
.kpi-pill-purple { background: #F5F3FF; color: #6D28D9; border: 1px solid #DDD6FE; }
.kpi-pill-rose   { background: #FFF1F2; color: #BE123C; border: 1px solid #FECDD3; }

/* ── Visual Conversion Funnel Card ── */
.funnel-container {
    background: #FFFFFF;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 22px 26px 20px 26px;
    margin-bottom: 28px;
    box-shadow: var(--shadow-sm);
}
.funnel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 18px;
}
.funnel-title {
    font-family: 'Newsreader', Georgia, serif !important;
    font-size: 19px !important;
    font-weight: 600 !important;
    color: var(--text-primary) !important;
    letter-spacing: -0.02em !important;
    display: flex;
    align-items: center;
    gap: 10px;
}
.funnel-stages {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 12px;
}
@media (max-width: 1024px) {
    .funnel-stages {
        grid-template-columns: repeat(3, 1fr);
    }
}
.funnel-stage {
    background: #FAFAF9;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 14px 12px;
    text-align: center;
    position: relative;
    transition: all 0.2s ease;
}
.funnel-stage:hover {
    background: #FFFFFF;
    border-color: #CBD5E1;
    transform: translateY(-2px);
    box-shadow: var(--shadow-sm);
}
.funnel-stage-name {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 10.5px !important;
    font-weight: 600 !important;
    color: var(--text-muted) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    margin-bottom: 5px;
}
.funnel-stage-val {
    font-family: 'Inter', sans-serif !important;
    font-feature-settings: "tnum" !important;
    font-size: 22px !important;
    font-weight: 700 !important;
    color: var(--text-primary) !important;
    letter-spacing: -0.02em !important;
    margin-bottom: 4px;
}
.funnel-stage-sub {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 10.5px !important;
    font-weight: 600 !important;
    color: var(--text-muted) !important;
}

/* ── Modern Premium Chart Containers ── */
.chart-box {
    background: #FFFFFF;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 22px 24px 18px 24px;
    box-shadow: var(--shadow-sm);
    margin-bottom: 24px;
    transition: all 0.2s ease;
}
.chart-box:hover {
    border-color: #CBD5E1;
    box-shadow: var(--shadow-md);
}
.chart-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 12px;
}
.chart-title-group h3 {
    font-family: 'Newsreader', Georgia, serif !important;
    font-size: 18px !important;
    font-weight: 600 !important;
    color: var(--text-primary) !important;
    margin: 0 !important;
    letter-spacing: -0.015em !important;
    display: flex;
    align-items: center;
    gap: 8px;
}
.chart-title-group p {
    font-family: 'Inter', sans-serif !important;
    font-size: 12.5px !important;
    color: var(--text-muted) !important;
    margin: 3px 0 0 0 !important;
}

/* ── Native Streamlit Bordered Containers Styled as Premium Cards ── */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: #FFFFFF !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-lg) !important;
    box-shadow: var(--shadow-sm) !important;
    padding: 20px 22px !important;
    transition: all 0.2s ease !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: #CBD5E1 !important;
    box-shadow: var(--shadow-md) !important;
}

/* ── Modern Premium Cards ── */
.premium-card {
    background: #FFFFFF;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 22px 24px;
    margin-bottom: 20px;
    box-shadow: var(--shadow-sm);
}
.card-header-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 14px;
}
.card-title {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    color: var(--text-muted) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}
.card-text {
    font-family: 'Inter', sans-serif !important;
    font-size: 14px;
    color: var(--text-primary);
    margin: 4px 0;
    line-height: 1.55;
    letter-spacing: -0.01em;
}
.card-text-light {
    font-family: 'Inter', sans-serif !important;
    font-size: 13px;
    color: var(--text-muted);
    margin: 2px 0;
    letter-spacing: -0.01em;
}

/* ── Badges / Pills (Perplexity Citation Chip Style) ── */
.badge {
    font-family: 'JetBrains Mono', monospace !important;
    display: inline-flex;
    align-items: center;
    padding: 2.5px 8px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 500;
    line-height: 1.3;
    letter-spacing: 0.02em;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
}
.badge-sent      { background: #F0FDFA; color: #0F766E; border: 1px solid #99F6E4; }
.badge-drafted   { background: #FFFBEB; color: #92400E; border: 1px solid #FDE68A; }
.badge-pending   { background: #F4F4F5; color: #27272A; border: 1px solid #E4E4E7; }
.badge-rejected  { background: #FEF2F2; color: #991B1B; border: 1px solid #FECACA; }
.badge-failed    { background: #FEF2F2; color: #991B1B; border: 1px solid #FECACA; }
.badge-replied   { background: #F0FDFA; color: #0F766E; border: 1px solid #99F6E4; }
.badge-scheduled { background: #F5F3FF; color: #5B21B6; border: 1px solid #DDD6FE; }

/* ── Form Inputs, Textarea, Select ── */
label, [data-testid="stWidgetLabel"] label, [data-testid="stWidgetLabel"] p {
    color: #0F172A !important;
    font-size: 13.5px !important;
    font-weight: 600 !important;
    margin-bottom: 5px !important;
}
div[data-baseweb="input"],
div[data-baseweb="textarea"],
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    background-color: #FFFFFF !important;
    color: #0F172A !important;
    -webkit-text-fill-color: #0F172A !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: var(--radius-sm) !important;
    font-size: 14px !important;
    box-shadow: var(--shadow-sm) !important;
}
div[data-baseweb="input"]:focus-within,
div[data-baseweb="textarea"]:focus-within {
    border-color: var(--brand-primary) !important;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15) !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"] {
    background: #FFFFFF !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: var(--radius-sm) !important;
    color: #0F172A !important;
}

/* ── Buttons ── */
.stButton > button {
    border-radius: var(--radius-sm) !important;
    font-weight: 600 !important;
    font-size: 13.5px !important;
    padding: 8px 16px !important;
    transition: all 0.15s ease !important;
    box-shadow: var(--shadow-sm) !important;
}
.stButton > button[kind="primary"] {
    background: var(--brand-primary) !important;
    border: 1px solid var(--brand-primary) !important;
    color: #FFFFFF !important;
}
.stButton > button[kind="primary"]:hover {
    background: var(--brand-hover) !important;
    border-color: var(--brand-hover) !important;
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25) !important;
}

/* ── Superhuman Email Client Preview Card ── */
.email-preview-window {
    background: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-md);
    overflow: hidden;
    margin: 16px 0;
}
.email-preview-mac-header {
    background: #F1F5F9;
    padding: 10px 16px;
    border-bottom: 1px solid #E2E8F0;
    display: flex;
    align-items: center;
    gap: 6px;
}
.mac-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
}
.dot-red   { background: #FF5F56; }
.dot-amber { background: #FFBD2E; }
.dot-green { background: #27C93F; }

.email-preview-meta {
    padding: 16px 20px;
    border-bottom: 1px solid #F1F5F9;
    background: #FAFAFA;
}
.email-preview-meta-row {
    display: flex;
    align-items: center;
    font-size: 13px;
    color: #475569;
    margin-bottom: 4px;
}
.email-preview-meta-label {
    width: 60px;
    font-weight: 600;
    color: #64748B;
}
.email-preview-subject {
    font-size: 15px;
    font-weight: 700;
    color: #0F172A;
    margin-top: 6px;
}
.email-preview-body {
    padding: 20px 24px;
    font-size: 14.5px;
    line-height: 1.5;
    color: #1E293B;
    background: #FFFFFF;
    word-break: break-word;
}
.email-preview-body p {
    margin: 0 0 10px 0 !important;
    padding: 0 !important;
    line-height: 1.5 !important;
}
.email-preview-body ul {
    margin: 4px 0 12px 0 !important;
    padding-left: 18px !important;
}
.email-preview-body li {
    margin-bottom: 4px !important;
    line-height: 1.45 !important;
}

/* ── Clean Data Tables ── */
[data-testid="stDataFrame"] {
    border-radius: var(--radius-md) !important;
    border: 1px solid var(--border-subtle) !important;
    background: #FFFFFF !important;
    box-shadow: var(--shadow-sm);
    overflow: hidden;
}

/* ── Light Alert / Status Containers ── */
[data-testid="stAlert"] {
    border-radius: var(--radius-md) !important;
    box-shadow: var(--shadow-sm) !important;
}

/* ── 4-Column Modern KPI Grid ── */
.kpi-grid-4 {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin-top: 4px;
    margin-bottom: 24px;
    width: 100%;
}
@media (max-width: 1200px) {
    .kpi-grid-4 {
        grid-template-columns: repeat(2, 1fr);
        gap: 14px;
    }
}
@media (max-width: 640px) {
    .kpi-grid-4 {
        grid-template-columns: 1fr;
    }
}

/* ── Executive Action Toolbar Card ── */
.action-toolbar-card {
    background: #FFFFFF;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 16px 22px;
    margin-bottom: 18px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: var(--shadow-sm);
    gap: 16px;
    flex-wrap: wrap;
}
.action-toolbar-status {
    display: flex;
    align-items: center;
    gap: 12px;
}
.action-toolbar-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: #10B981;
    box-shadow: 0 0 6px rgba(16, 185, 129, 0.6);
    display: inline-block;
}

/* ── Executive Consultation Booking Cards ── */
.booking-card {
    background: #FFFFFF;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 20px 22px;
    box-shadow: var(--shadow-sm);
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    margin-bottom: 16px;
    height: 100%;
}
.booking-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px -4px rgba(15, 23, 42, 0.08);
    border-color: #CBD5E1;
}
.booking-card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 14px;
}
.booking-lead-profile {
    display: flex;
    align-items: center;
    gap: 12px;
}
.booking-avatar {
    width: 44px;
    height: 44px;
    border-radius: 12px;
    background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%);
    color: #1D4ED8;
    font-weight: 700;
    font-size: 15px;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px solid #BFDBFE;
    flex-shrink: 0;
}
.booking-name-title {
    font-size: 15.5px;
    font-weight: 600;
    color: var(--text-primary);
    line-height: 1.3;
}
.booking-company-badge {
    font-size: 12.5px;
    color: var(--text-muted);
    display: flex;
    align-items: center;
    gap: 4px;
    margin-top: 2px;
}
.booking-info-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
    padding: 12px 14px;
    background: #FAFAFA;
    border: 1px solid #F1F5F9;
    border-radius: var(--radius-md);
    margin: 12px 0;
}
.booking-info-item {
    display: flex;
    flex-direction: column;
}
.booking-info-label {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 10px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
.booking-info-val {
    font-size: 12.5px;
    font-weight: 500;
    color: var(--text-secondary);
    margin-top: 2px;
    word-break: break-all;
}
.booking-slot-highlight {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    background: #F0FDFA;
    border: 1px solid #99F6E4;
    border-radius: var(--radius-md);
    margin: 10px 0 14px 0;
}
.booking-slot-text {
    font-size: 13px;
    font-weight: 600;
    color: #0F766E;
}
.booking-note-box {
    font-size: 12.5px;
    color: #475569;
    background: #F8FAFC;
    border-left: 3px solid #94A3B8;
    padding: 8px 12px;
    border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
    margin-bottom: 14px;
    font-style: italic;
}
.teams-join-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    width: 100%;
    padding: 10px 16px;
    background: linear-gradient(135deg, #4338CA 0%, #4F46E5 100%);
    color: #FFFFFF !important;
    font-weight: 600;
    font-size: 13px;
    border-radius: var(--radius-sm);
    text-decoration: none !important;
    box-shadow: 0 2px 6px rgba(79, 70, 229, 0.25);
    transition: all 0.2s ease;
}
.teams-join-btn:hover {
    background: linear-gradient(135deg, #3730A3 0%, #4338CA 100%);
    box-shadow: 0 4px 12px rgba(79, 70, 229, 0.35);
    transform: translateY(-1px);
    color: #FFFFFF !important;
}

/* ── Live Reply & Conversation Thread Feed ── */
.chat-thread-card {
    background: #FFFFFF;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 20px 22px;
    margin-bottom: 18px;
    box-shadow: var(--shadow-sm);
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
.chat-thread-card:hover {
    box-shadow: var(--shadow-md);
    border-color: #CBD5E1;
}
.chat-thread-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 12px;
    margin-bottom: 14px;
    border-bottom: 1px solid #F1F5F9;
    flex-wrap: wrap;
    gap: 10px;
}
.chat-lead-profile {
    display: flex;
    align-items: center;
    gap: 10px;
}
.chat-bubble-inbound {
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 12px 12px 12px 2px;
    padding: 14px 16px;
    margin-bottom: 12px;
}
.chat-bubble-outbound {
    background: #F0FDFA;
    border: 1px solid #CCFBF1;
    border-radius: 12px 12px 2px 12px;
    padding: 14px 16px;
}
.chat-bubble-sender {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 12px;
    font-weight: 600;
    margin-bottom: 6px;
}
.chat-bubble-text {
    font-size: 13.5px;
    color: #1E293B;
    line-height: 1.6;
    white-space: pre-wrap;
}

/* ── Executive Analytics Suite Styles ── */
.analytics-feature-box {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 18px 22px;
    margin-bottom: 18px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
    transition: all 0.2s ease;
}
.analytics-feature-box:hover {
    border-color: #CBD5E1;
    box-shadow: 0 4px 12px -2px rgba(15, 23, 42, 0.06);
}
.feature-title-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.feature-title-left {
    display: flex;
    align-items: center;
    gap: 12px;
}
.feature-icon-bubble {
    width: 38px;
    height: 38px;
    border-radius: 10px;
    background: #EFF6FF;
    color: #2563EB;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    flex-shrink: 0;
}
.feature-name-text {
    font-size: 15.5px;
    font-weight: 600;
    color: #18181B;
    letter-spacing: -0.015em;
    margin: 0;
}
.feature-explanation-sub {
    font-size: 13px;
    color: #64748B;
    margin: 2px 0 0 0;
}
.feature-tag-pill {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10.5px;
    font-weight: 600;
    padding: 3px 8px;
    border-radius: 6px;
    background: #F8FAFC;
    color: #475569;
    border: 1px solid #E2E8F0;
}
.feature-status-active {
    background: #F0FDFA;
    color: #0F766E;
    border: 1px solid #99F6E4;
}

/* ── Vertical Connected Lead Timeline ── */
.timeline-v-wrap {
    position: relative;
    padding-left: 32px;
    margin: 16px 0;
}
.timeline-v-wrap::before {
    content: '';
    position: absolute;
    top: 10px;
    bottom: 10px;
    left: 13px;
    width: 2px;
    background: #E2E8F0;
}
.timeline-v-item {
    position: relative;
    margin-bottom: 20px;
}
.timeline-v-node {
    position: absolute;
    left: -32px;
    top: 2px;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: #FFFFFF;
    border: 2px solid #2563EB;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    box-shadow: 0 0 0 3px #EFF6FF;
    z-index: 2;
}
.timeline-v-node.completed {
    border-color: #0D9488;
    box-shadow: 0 0 0 3px #F0FDFA;
}
.timeline-v-node.suppressed {
    border-color: #DC2626;
    box-shadow: 0 0 0 3px #FEF2F2;
}
.timeline-v-card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 12px 16px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}
.timeline-v-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 4px;
}
.timeline-v-title {
    font-size: 13.5px;
    font-weight: 600;
    color: #1E293B;
}
.timeline-v-time {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: #94A3B8;
}
.timeline-v-desc {
    font-size: 12.5px;
    color: #475569;
    margin: 0;
}

/* ── Luxury Glassmorphic Feature Cards (Whole Box Clickable) ── */
.glass-feature-card {
    display: flex !important;
    flex-direction: column !important;
    justify-content: space-between !important;
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.88) 0%, rgba(248, 250, 252, 0.68) 100%) !important;
    backdrop-filter: blur(16px) saturate(180%) !important;
    -webkit-backdrop-filter: blur(16px) saturate(180%) !important;
    border: 1px solid rgba(226, 232, 240, 0.85) !important;
    border-radius: 16px !important;
    padding: 22px 24px !important;
    margin-bottom: 18px !important;
    text-decoration: none !important;
    color: inherit !important;
    cursor: pointer !important;
    box-shadow: 0 4px 20px -2px rgba(15, 23, 42, 0.04), inset 0 1px 1px 0 rgba(255, 255, 255, 0.95) !important;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    position: relative !important;
    overflow: hidden !important;
    min-height: 148px !important;
}
.glass-feature-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3.5px;
    background: linear-gradient(90deg, #2563EB 0%, #0D9488 50%, #7C3AED 100%);
    opacity: 0;
    transition: opacity 0.25s ease;
}
.glass-feature-card:hover {
    transform: translateY(-4px) !important;
    border-color: rgba(59, 130, 246, 0.45) !important;
    box-shadow: 0 16px 36px -4px rgba(37, 99, 235, 0.12), inset 0 1px 2px 0 rgba(255, 255, 255, 1) !important;
    text-decoration: none !important;
}
.glass-feature-card:hover::before {
    opacity: 1;
}
.glass-feature-card:hover .glass-card-title {
    color: #2563EB !important;
}
.glass-feature-card:hover .glass-arrow-circle {
    background: #2563EB !important;
    color: #FFFFFF !important;
    transform: translateX(4px) !important;
    border-color: #2563EB !important;
}
.glass-card-header {
    display: flex !important;
    justify-content: space-between !important;
    align-items: flex-start !important;
    margin-bottom: 10px !important;
}
.glass-card-left {
    display: flex !important;
    align-items: flex-start !important;
    gap: 14px !important;
}
.glass-icon-box {
    width: 44px !important;
    height: 44px !important;
    border-radius: 12px !important;
    background: linear-gradient(135deg, rgba(239, 246, 255, 0.9) 0%, rgba(219, 234, 254, 0.7) 100%) !important;
    border: 1px solid rgba(191, 219, 254, 0.8) !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: 22px !important;
    flex-shrink: 0 !important;
    box-shadow: 0 2px 8px rgba(37, 99, 235, 0.08) !important;
}
.glass-card-title {
    font-size: 16px !important;
    font-weight: 700 !important;
    color: #18181B !important;
    letter-spacing: -0.015em !important;
    margin: 0 !important;
    transition: color 0.2s ease !important;
}
.glass-card-desc {
    font-size: 13px !important;
    color: #64748B !important;
    margin: 4px 0 0 0 !important;
    line-height: 1.5 !important;
}
.glass-card-footer {
    display: flex !important;
    justify-content: space-between !important;
    align-items: center !important;
    margin-top: 14px !important;
    padding-top: 10px !important;
    border-top: 1px solid rgba(226, 232, 240, 0.6) !important;
}
.glass-explore-text {
    font-size: 11.5px !important;
    font-weight: 600 !important;
    color: #475569 !important;
    letter-spacing: -0.01em !important;
    display: flex !important;
    align-items: center !important;
    gap: 4px !important;
}
.glass-arrow-circle {
    width: 26px !important;
    height: 26px !important;
    border-radius: 50% !important;
    background: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    color: #475569 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: 12px !important;
    font-weight: 700 !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04) !important;
}
.card-stretch-link {
    position: absolute !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    bottom: 0 !important;
    width: 100% !important;
    height: 100% !important;
    z-index: 15 !important;
    cursor: pointer !important;
    background: transparent !important;
    text-decoration: none !important;
    display: block !important;
    border: none !important;
    outline: none !important;
}
.btn-export-download {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-weight: 500 !important;
    padding: 0.45rem 0.85rem !important;
    border-radius: 8px !important;
    min-height: 38px !important;
    margin: 0px !important;
    line-height: 1.5 !important;
    color: #1E293B !important;
    width: 100% !important;
    user-select: none !important;
    background: #FFFFFF !important;
    border: 1px solid #CBD5E1 !important;
    text-decoration: none !important;
    font-size: 13.5px !important;
    cursor: pointer !important;
    transition: all 0.15s ease !important;
    box-sizing: border-box !important;
    text-align: center !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
}
.btn-export-download:hover {
    border-color: #2563EB !important;
    color: #2563EB !important;
    background-color: #F8FAFC !important;
    text-decoration: none !important;
    box-shadow: 0 2px 4px rgba(37, 99, 235, 0.12) !important;
}
.btn-export-download:active {
    background-color: #EFF6FF !important;
    transform: translateY(1px) !important;
}
</style>
""",
    unsafe_allow_html=True,
)


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
    "created_at",
]


def load_campaign_logs():
    db = SessionLocal()
    try:
        try:
            from Backend.crud import sync_excel_and_outlook_to_db
            sync_excel_and_outlook_to_db(db)
        except Exception as e:
            print(f"Sync note: {e}")
        rows = db.query(CampaignLog).order_by(CampaignLog.created_at.desc()).all()
    finally:
        db.close()
    return [
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
            "created_at": r.created_at,
        }
        for r in rows
    ]


# ─────────────────────────────────────────────────────────────
# SIDEBAR NAVIGATION
# ─────────────────────────────────────────────────────────────
NAV_ITEMS = {
    "overview": {"icon": "📊", "label": "Pipeline Overview"},
    "analytics": {"icon": "📈", "label": "Analytics"},
    "upload": {"icon": "📤", "label": "Upload & Draft"},
    "leads": {"icon": "📋", "label": "Leads Directory"},
    "email": {"icon": "✉️", "label": "Email Review Studio"},
    "replies": {"icon": "💬", "label": "Replies & Bookings"},
}

if "page" in st.query_params and st.query_params["page"] in NAV_ITEMS:
    st.session_state.active_page = st.query_params["page"]

if "tab" in st.query_params:
    st.session_state.analytics_tab = st.query_params["tab"]

if "feature" in st.query_params:
    st.session_state.analytics_focused_feature = st.query_params["feature"]

if "active_page" not in st.session_state or st.session_state.active_page not in NAV_ITEMS:
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
                for k in list(st.session_state.keys()):
                    if k.startswith("_pdf_") or k.startswith("_excel_") or k == "campaign_data_version":
                        del st.session_state[k]
            st.toast("✅ All data has been successfully reset to zero in PostgreSQL and Excel!", icon="🗑️")
            st.rerun()
    with col_cancel:
        if st.button("Cancel", type="secondary", use_container_width=True, key="dlg_cancel_reset_action"):
            st.rerun()


with st.sidebar:
    logo_file = os.path.join(os.path.dirname(__file__), "logo-light.png")
    logo_b64 = get_image_base64(logo_file)
    if logo_b64:
        logo_img_tag = f'<img src="data:image/png;base64,{logo_b64}" alt="Neno Technology" class="sidebar-brand-logo-img" />'
    else:
        logo_img_tag = '<span style="color: #FFFFFF; font-weight: 700; font-size: 15px;">⚡ Neno Technology</span>'

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

    st.markdown("<div style='font-family: \"JetBrains Mono\", monospace; font-size: 10.5px; font-weight: 600; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.06em; margin: 4px 0 8px 6px;'>Navigation</div>", unsafe_allow_html=True)

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

    st.markdown("<hr style='border: none; border-top: 1px solid #E2E8F0; margin: 16px 0 12px 0;'>", unsafe_allow_html=True)

    # ── Live System Health in Sidebar ──
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
                <span>Outreach Sender</span>
                <span style="font-size: 11px; color: #475569;">support@nenotech...</span>
            </div>
            <div class="sidebar-health-row">
                <span>AI Engine</span>
                <span style="font-size: 11px; color: #475569;">Gemini 2.5 Flash</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("🗑️ Reset / Zero All Data", expanded=False):
        st.caption("Erase all uploaded leads, drafts, logs, replies, and bookings to test fresh with 0 records.")
        if st.button("⚠️ Reset All Data to Zero", type="secondary", use_container_width=True, key="reset_all_data_btn"):
            confirm_reset_dialog()



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


# ─────────────────────────────────────────────────────────────
# PAGE 1: OVERVIEW
# ─────────────────────────────────────────────────────────────
def render_overview(df: pd.DataFrame) -> None:
    render_top_banner(
        "Executive Pipeline Overview",
        "Real-time visibility into lead outreach, email performance, customer replies, and consultation bookings.",
        "Live Campaign",
    )

    if df.empty:
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
        total_leads = len(df)
        drafted_leads = int((df["status"] == "drafted").sum())
        sent_leads = int((df["status"] == "sent").sum())
        replied_leads = int(df["reply_received_at"].notna().sum())
        forms_filled = int(df["form_filled_at"].notna().sum())
        scheduled_leads = int(df["booking_status"].isin(["scheduled", "meeting_scheduled", "confirmation_sent"]).sum())

        draft_pct = round((drafted_leads / total_leads * 100) if total_leads else 0)
        sent_pct = round((sent_leads / total_leads * 100) if total_leads else 0)
        reply_pct = round((replied_leads / sent_leads * 100) if sent_leads else 0)
        form_pct = round((forms_filled / total_leads * 100) if total_leads else 0)
        booked_pct = round((scheduled_leads / forms_filled * 100) if forms_filled else (round(scheduled_leads / total_leads * 100) if total_leads else 0))

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
            st.plotly_chart(fig_funnel, use_container_width=True)

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
            st.plotly_chart(fig_donut, use_container_width=True)

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
            status_counts = df["status"].value_counts().reset_index()
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
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total in Uploaded Sheet", len(raw_df))
            m2.metric("Skipped (Already Sent)", len(skipped_sent_df))
            m3.metric("Pending in Review", len(skipped_drafted_df))
            m4.metric("New Leads Ready for Outreach", len(new_leads_df))

            st.markdown("<br>", unsafe_allow_html=True)

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

                    st.markdown("<br>", unsafe_allow_html=True)
                    btn_col1, btn_col2 = st.columns([1, 1])

                    with btn_col1:
                        if st.button(
                            f"🚀 Generate AI Drafts for {len(new_leads_df)} New Lead(s)",
                            type="primary",
                            key="gen_drafts_new",
                        ):
                            campaign_name = os.getenv("CAMPAIGN_NAME", "default_campaign")
                            progress_bar = st.progress(0.0, text="Generating personalized drafts with Gemini AI...")
                            db = SessionLocal()
                            created_count = 0
                            failed_count = 0
                            failed_errors = []
                            successfully_drafted_rows = []
                            total_new = len(new_leads_df)

                            for idx, row in new_leads_df.iterrows():
                                email = str(row.get("email", "")).strip()
                                name = None if pd.isna(row.get("name")) else str(row.get("name"))
                                company = None if pd.isna(row.get("company")) else str(row.get("company"))
                                lead_id = str(row.get("lead_id", f"lead_{idx}"))
                                last_activity = None if pd.isna(row.get("last_activity_date")) else str(row.get("last_activity_date"))
                                last_deal = None if pd.isna(row.get("last_deal_stage")) else str(row.get("last_deal_stage"))

                                progress_bar.progress(
                                    (created_count + failed_count) / total_new,
                                    text=f"Drafting email for {email} ({name or 'Lead'})...",
                                )

                                try:
                                    token = generate_token()
                                    booking_url = os.getenv(
                                        "BOOKING_FORM_URL",
                                        "https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled",
                                    )
                                    tracking_link = booking_url

                                    # Primary Email Template: Option 1 (Forward-Deployed Engineers & Tech Solutions)
                                    subject, body = Email.draft_options.get_draft_template_option(
                                        1,
                                        name=name,
                                        company=company,
                                        cta_url=tracking_link,
                                    )

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
                                    )
                                    created_count += 1
                                    successfully_drafted_rows.append(row)
                                except Exception as err:
                                    failed_errors.append(f"{email}: {err}")
                                    failed_count += 1

                            db.close()
                            progress_bar.progress(1.0, text="Draft generation completed!")

                            if successfully_drafted_rows:
                                append_or_update_leads_dataset(pd.DataFrame(successfully_drafted_rows), default_status="drafted")
                            st.cache_data.clear()

                            if created_count > 0:
                                st.success(f"🎉 Generated {created_count} personalized outreach drafts! Ready for review.")
                            if failed_errors:
                                for err_msg in failed_errors:
                                    st.error(f"❌ Failed: {err_msg}")

                    with btn_col2:
                        if st.button("👉 Open Email Review Studio", key="goto_email_review", type="secondary"):
                            st.session_state.active_page = "email"
                            st.rerun()

                else:
                    st.info("✅ All leads in this sheet have already received emails or currently have active drafts. No duplicates generated!")

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
    render_top_banner(
        "Campaign Leads Directory",
        "Browse, filter, and inspect leads recorded in your database.",
        "Master Directory",
    )

    if df.empty:
        st.info("No leads found. Upload a dataset in 'Upload & Draft' to get started.")
        return

    col1, col2, col3 = st.columns([1, 1, 1.5])
    with col1:
        campaign_filter = st.selectbox(
            "Filter by Campaign",
            ["All"] + sorted(df["campaign"].unique().tolist()),
            key="leads_camp_filter",
        )
    with col2:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All"] + sorted(df["status"].unique().tolist()),
            key="leads_stat_filter",
        )
    with col3:
        search_query = st.text_input("Search by Name, Email or Company", placeholder="Type to search...", key="leads_search")

    filtered = df.copy()
    if campaign_filter != "All":
        filtered = filtered[filtered["campaign"] == campaign_filter]
    if status_filter != "All":
        filtered = filtered[filtered["status"] == status_filter]
    if search_query:
        sq = search_query.lower()
        filtered = filtered[
            filtered["email"].str.lower().str.contains(sq)
            | filtered["name"].fillna("").str.lower().str.contains(sq)
            | filtered["company"].fillna("").str.lower().str.contains(sq)
        ]

    st.markdown(f"<p style='color: #64748B; font-size: 13.5px; font-weight: 500;'>Displaying <strong>{len(filtered)}</strong> matching lead(s)</p>", unsafe_allow_html=True)
    
    display_cols = [c for c in ["lead_id", "email", "name", "company", "status", "subject", "booking_status", "created_at"] if c in filtered.columns]
    st.dataframe(
        filtered[display_cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "lead_id": "Lead ID",
            "email": "Email Address",
            "name": "Full Name",
            "company": "Company",
            "status": "Outreach Status",
            "subject": "Email Subject",
            "booking_status": "Booking Status",
            "created_at": "Created",
        },
    )


LOGO_URL = "https://res.cloudinary.com/dqreqsjas/image/upload/v1789542387/logo-dark.png"
LOGO_HEADER_HTML = f'<div style="margin:0 0 16px 0;padding:0 0 12px 0;border-bottom:1px solid #eef0f4;"><img src="{LOGO_URL}" alt="Nenotechnology" width="132" height="34" style="display:block;border:0;outline:none;text-decoration:none;-ms-interpolation-mode:bicubic;width:132px;height:34px;max-height:36px;pointer-events:none;"></div>'


def clean_natural_email_body(html_text: str) -> str:
    if not html_text:
        return html_text
    cleaned = html_text
    # Replace old broken ngrok logos with the new reliable Cloudinary logo
    cleaned = re.sub(r'https?://[^\s"\'<>]*ngrok[^\s"\'<>]*/logo(?:-dark)?\.png', LOGO_URL, cleaned, flags=re.IGNORECASE)
    # Remove any <a> link wrappers around the logo so it is purely an unclickable image
    cleaned = re.sub(r'<a\s+[^>]*href=["\'][^"\']*nenotechnology\.com[^"\']*["\'][^>]*>\s*(<img[^>]*logo(?:-dark)?\.png[^>]*>)\s*</a>', r'\1', cleaned, flags=re.IGNORECASE)
    # Remove artificial outer card boxes
    cleaned = re.sub(r'<div style="max-width:600px;margin:0 auto;background:#ffffff;color:#1a1a1a;border:1px solid #e3e6eb;border-radius:8px;overflow:hidden;font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.6;">\s*', '<div style="font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.45;color:#1a1a1a;">', cleaned)
    cleaned = re.sub(r'<div style="max-width:600px;margin:0 auto;background:#ffffff;color:#1e293b;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.6;">\s*', '<div style="font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.45;color:#1e293b;">', cleaned)
    cleaned = re.sub(r'<div style="padding:(?:24px|26px 24px);">\s*', '', cleaned)
    cleaned = re.sub(r'<div style="background:#f7f8fa;padding:14px 24px;font-size:11.5px;color:#(?:8b93a1|94a3b8);text-align:center;[^"]*">.*?</div>\s*</div>\s*$', '</div>', cleaned, flags=re.DOTALL)
    # Ensure Cloudinary logo header is present if missing
    if "logo-dark.png" not in cleaned and "cloudinary" not in cleaned:
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
def confirm_approve_send_dialog(entry_id: str, email: str, subject: str, body: str):
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
        st.markdown(
            f"""
            <div style="background: #ffffff; border: 1px solid #E2E8F0; border-radius: 8px; padding: 20px; font-size: 14px; line-height: 1.6; color: #1E293B;">
                {preview_modal}
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
                approve_and_send_entry(db, entry_id)
                st.session_state["send_success_banner"] = f"🎉 Email successfully approved and dispatched to {email}!"
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
def confirm_approve_all_dialog(drafts_data, template_id: int = 1):
    count = len(drafts_data)
    template_info = {
        1: ("Primary Template", "⭐", "Forward-Deployed Engineers & Tech Solutions"),
        2: ("Option 2 (Returning Client)", "🤝", "Personal Check-in & Complimentary Consultation"),
        3: ("Option 3 (Free AI & IT Audit)", "🔍", "Complimentary AI & IT Diagnostic Roadmap"),
    }
    t_name, t_icon, t_desc = template_info.get(template_id, ("Primary Template", "⭐", "Forward-Deployed Engineers"))

    st.markdown(
        f"""
        <div style="margin-bottom: 12px;">
            <p style="font-size: 15px; margin-bottom: 6px; color: #0F172A;">
                Are you sure you want to approve and send all <strong style="color: #2563EB;">{count}</strong> pending email drafts with <strong>{t_name}</strong>?
            </p>
            <div style="background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 8px; padding: 10px 14px; margin-bottom: 12px; font-size: 13.5px; color: #1E40AF;">
                {t_icon} <strong>{t_name} Applied:</strong> All {count} emails will be formatted with <strong>{t_desc}</strong>, personalized with each recipient's name, company, and Microsoft Bookings consultation link.
            </div>
            <p style="font-size: 13px; color: #64748B; margin: 0;">
                Dispatched securely via Microsoft Graph. Duplicate leads are safely skipped to protect sender reputation.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander(f"📋 Review Recipients & Active Subjects ({count})", expanded=True):
        booking_url = os.getenv(
            "BOOKING_FORM_URL",
            "https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled",
        )
        for d in drafts_data:
            s, _ = get_draft_template_option(template_id, d.get("name"), d.get("company"), booking_url)
            s_clean = s.replace("\ufffd", "-").replace("—", "-").strip()
            st.write(f"- **{d['email']}** ({d.get('name') or 'Lead'}, {d.get('company') or 'N/A'}) — *{s_clean}*")

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button(f"🚀 Send All {count} Emails ({t_name})", type="primary", use_container_width=True, key="dlg_confirm_send_all"):
            db = SessionLocal()
            approved_count = 0
            skipped_count = 0
            error_details = []
            booking_url = os.getenv(
                "BOOKING_FORM_URL",
                "https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled",
            )
            for d in drafts_data:
                try:
                    curr_s, curr_b = get_draft_template_option(
                        template_id, d.get("name"), d.get("company"), booking_url
                    )
                    curr_s = curr_s.replace("\ufffd", "-").replace("—", "-").strip()
                    update_draft_content(db, d["id"], curr_s, curr_b)
                    approve_and_send_entry(db, d["id"])
                    approved_count += 1
                except ValueError as ve:
                    skipped_count += 1
                except Exception as ex:
                    error_details.append(f"{d.get('email')}: {str(ex)}")
            db.close()
            msg = f"🎉 Approved & sent {approved_count} emails with {t_name} successfully!"
            if skipped_count > 0:
                msg += f" (Skipped {skipped_count} duplicate/already sent)"
            if error_details:
                msg += f" (Encountered {len(error_details)} errors: {'; '.join(error_details[:2])})"
            st.session_state["send_success_banner"] = msg
            st.cache_data.clear()
            st.rerun()

    with c2:
        if st.button("Cancel", use_container_width=True, key="dlg_cancel_all_btn"):
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

    if df.empty or "status" not in df.columns:
        st.info("No pending drafts awaiting review. Upload a lead sheet in 'Upload & Draft' to generate new drafts.")
        return

    drafts = df[df["status"] == "drafted"].copy()

    if drafts.empty:
        st.info("No pending drafts awaiting review. Upload a lead sheet in 'Upload & Draft' to generate new drafts.")
        return

    st.markdown(
        f"""
        <div style="display: flex; justify-content: space-between; align-items: center; background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 10px; padding: 12px 18px; margin-bottom: 20px;">
            <div style="display: flex; align-items: center; gap: 8px; font-weight: 600; color: #92400E; font-size: 14px;">
                <span>📬</span> <strong>{len(drafts)}</strong> draft email(s) awaiting your approval
            </div>
            <span class="badge badge-drafted">Human-in-the-Loop</span>
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

    selected_email = st.selectbox(
        "Select Draft to Review",
        drafts["email"].tolist(),
        key="approval_select",
    )
    row = drafts[drafts["email"] == selected_email].iloc[0]

    db_check = SessionLocal()
    is_already_sent = is_email_already_sent(db_check, row["email"])
    db_check.close()

    if is_already_sent:
        st.error(
            f"⚠️ **Duplicate Protection Alert**: An outreach email was already sent to `{row['email']}`! "
            "Dispatch is blocked to safeguard sender reputation."
        )

    # Lead Metadata Info Cards
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            f"""
            <div class="premium-card">
                <div class="card-header-row">
                    <span class="card-title">Lead Profile</span>
                    <span class="badge badge-pending">Verified Contact</span>
                </div>
                <div class="card-text"><strong>Full Name:</strong> {row['name'] or 'N/A'}</div>
                <div class="card-text"><strong>Company:</strong> {row['company'] or 'N/A'}</div>
                <div class="card-text-light">Lead Identifier: <code>{row['lead_id']}</code></div>
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

    # ── Quick Set Template Option Buttons ──
    st.markdown(
        """
        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px 16px; margin: 12px 0 10px 0;">
            <div style="font-size: 13.5px; font-weight: 700; color: #1E293B; display: flex; align-items: center; justify-content: space-between;">
                <span>🎯 Select Email Draft Template:</span>
                <span class="badge badge-pending" style="font-size: 10.5px; padding: 2px 8px;">3 Natural Executive Templates</span>
            </div>
            <div style="font-size: 12px; color: #64748B; margin-top: 2px;">
                Click any button below to instantly format this lead's draft with the chosen executive template:
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    t_col1, t_col2, t_col3 = st.columns(3)
    with t_col1:
        if st.button("⭐ Primary Template", key=f"btn_opt1_{row['id']}", use_container_width=True, help="Primary template: Forward-Deployed Engineers, Vetted bench & consultation call"):
            importlib.reload(Email.draft_options)
            opt_subj, opt_body = Email.draft_options.get_draft_template_option(1, row["name"], row["company"], custom_form_url)
            opt_subj = opt_subj.replace("\ufffd", "-").replace("—", "-").strip()
            st.session_state[f"subj_{row['id']}"] = opt_subj
            st.session_state[f"body_{row['id']}"] = opt_body
            db = SessionLocal()
            update_draft_content(db, row["id"], opt_subj, opt_body)
            db.close()
            st.cache_data.clear()
            st.toast("✅ Applied Primary Template!", icon="⭐")
            st.rerun()

    with t_col2:
        if st.button("🤝 Returning Client", key=f"btn_opt2_{row['id']}", use_container_width=True, help="Personal check-in with returning client and free consultation call"):
            importlib.reload(Email.draft_options)
            opt_subj, opt_body = Email.draft_options.get_draft_template_option(2, row["name"], row["company"], custom_form_url)
            opt_subj = opt_subj.replace("\ufffd", "-").replace("—", "-").strip()
            st.session_state[f"subj_{row['id']}"] = opt_subj
            st.session_state[f"body_{row['id']}"] = opt_body
            db = SessionLocal()
            update_draft_content(db, row["id"], opt_subj, opt_body)
            db.close()
            st.cache_data.clear()
            st.toast("✅ Applied Returning Client Template!", icon="🤝")
            st.rerun()

    with t_col3:
        if st.button("🔍 Free AI & IT Audit", key=f"btn_opt3_{row['id']}", use_container_width=True, help="Complimentary AI & IT audit offer with practical roadmap"):
            importlib.reload(Email.draft_options)
            opt_subj, opt_body = Email.draft_options.get_draft_template_option(3, row["name"], row["company"], custom_form_url)
            opt_subj = opt_subj.replace("\ufffd", "-").replace("—", "-").strip()
            st.session_state[f"subj_{row['id']}"] = opt_subj
            st.session_state[f"body_{row['id']}"] = opt_body
            db = SessionLocal()
            update_draft_content(db, row["id"], opt_subj, opt_body)
            db.close()
            st.cache_data.clear()
            st.toast("✅ Applied Free AI & IT Audit Template!", icon="🔍")
            st.rerun()

    initial_subj = st.session_state.get(f"subj_{row['id']}", current_subject)
    initial_subj = initial_subj.replace("\ufffd", "-").replace("—", "-").strip()
    edit_subject = st.text_input("Subject Line", value=initial_subj, key=f"subj_{row['id']}")
    edit_body = st.text_area("Email Body (Markdown / HTML)", value=st.session_state.get(f"body_{row['id']}", current_body), height=260, key=f"body_{row['id']}")

    # ── Superhuman / Apple Mail Style Live Preview ──
    st.markdown("##### 👁️ Live Email Client Preview")
    sender_email = os.getenv("MS_SENDER_EMAIL", "support@nenotechnology.com")
    preview_rendered = edit_body if (edit_body or "").strip().startswith(("<div", "<table", "<html", "<body")) else (edit_body or "").replace(chr(10), '<br>')
    preview_rendered = clean_natural_email_body(preview_rendered)
    st.markdown(
        f"""
        <div class="email-preview-window">
            <div class="email-preview-mac-header">
                <div class="mac-dot dot-red"></div>
                <div class="mac-dot dot-amber"></div>
                <div class="mac-dot dot-green"></div>
                <span style="font-size: 11.5px; color: #64748B; margin-left: 10px; font-weight: 500;">Outlook / Webmail Client View</span>
            </div>
            <div class="email-preview-meta">
                <div class="email-preview-meta-row">
                    <span class="email-preview-meta-label">From:</span>
                    <span>AINeotechnology Team &lt;{sender_email}&gt;</span>
                </div>
                <div class="email-preview-meta-row">
                    <span class="email-preview-meta-label">To:</span>
                    <span>{row['name'] or 'Lead'} &lt;{row['email']}&gt;</span>
                </div>
                <div class="email-preview-subject">{edit_subject}</div>
            </div>
            <div class="email-preview-body">
                {preview_rendered}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    btn1, btn_save, btn2, btn3 = st.columns([1.4, 1.1, 1.2, 1.0])

    with btn1:
        if st.button(
            "🚀 Approve & Send",
            type="primary",
            key=f"app_{row['id']}",
            disabled=is_already_sent,
            use_container_width=True,
            help="Send email to this recipient via Microsoft Graph",
        ):
            confirm_approve_send_dialog(row["id"], row["email"], edit_subject, edit_body)

    with btn_save:
        if st.button("💾 Save Draft", key=f"save_{row['id']}", use_container_width=True, help="Save changes to database without sending"):
            db = SessionLocal()
            update_draft_content(db, row["id"], edit_subject, edit_body)
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

    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button(
            f"⭐ Approve All & Send Primary ({pending_count})",
            key="bulk_send_opt1",
            type="primary",
            use_container_width=True,
            help="Approve and send all remaining drafts formatted with Primary Template",
        ):
            confirm_approve_all_dialog(drafts.to_dict("records"), template_id=1)

    with b2:
        if st.button(
            f"🤝 Approve All & Send Option 2 ({pending_count})",
            key="bulk_send_opt2",
            use_container_width=True,
            help="Approve and send all remaining drafts formatted with Option 2 (Returning Client)",
        ):
            confirm_approve_all_dialog(drafts.to_dict("records"), template_id=2)

    with b3:
        if st.button(
            f"🔍 Approve All & Send Option 3 ({pending_count})",
            key="bulk_send_opt3",
            use_container_width=True,
            help="Approve and send all remaining drafts formatted with Option 3 (Free AI & IT Audit)",
        ):
            confirm_approve_all_dialog(drafts.to_dict("records"), template_id=3)





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
    raw = (intent_raw or "question").lower().strip()
    if "interest" in raw and "not" not in raw:
        return "🎯 Interested", "badge-sent"
    elif "meeting" in raw:
        return "🗓️ Meeting Request", "badge-scheduled"
    elif "reschedule" in raw:
        return "⏱️ Reschedule", "badge-drafted"
    elif "not" in raw or "opt" in raw or "unsub" in raw:
        return "🛑 Opted Out", "badge-rejected"
    return "❓ Inquiry / Question", "badge-pending"


def render_replies(df: pd.DataFrame) -> None:
    render_top_banner(
        "Replies & Consultation Bookings",
        "AI Auto-Reply Agent, inbound email conversations, customer appointment submissions, and permanent Excel sheets.",
        "CRM & Intelligence",
    )

    # ── AI Auto-Reply Agent Control Center ──
    is_monitoring = ReplyDaemonManager.is_running()
    status_label = "Active & Monitoring Inbox (30s)" if is_monitoring else "Idle / On-Demand Mode"
    status_badge_cls = "badge-sent" if is_monitoring else "badge-pending"
    status_dot_color = "#10B981" if is_monitoring else "#94A3B8"

    agent_status_html = f"""
    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px;">
        <div style="display: flex; align-items: center; gap: 14px;">
            <div style="width: 44px; height: 44px; border-radius: 12px; background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%); color: #2563EB; display: flex; align-items: center; justify-content: center; font-size: 22px; border: 1px solid #BFDBFE;">
                🤖
            </div>
            <div>
                <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                    <span style="font-size: 16px; font-weight: 700; color: #0F172A;">AI Auto-Reply Agent</span>
                    <span class="badge {status_badge_cls}" style="font-size: 11px;">
                        <span style="display: inline-block; width: 7px; height: 7px; border-radius: 50%; background-color: {status_dot_color}; margin-right: 5px;"></span>
                        {status_label}
                    </span>
                    <span class="badge badge-scheduled" style="font-size: 11px;">📚 Grounded in Neno Technology Knowledge Base (PDF · 70 Chunks)</span>
                </div>
                <div style="font-size: 13px; color: #64748B; margin-top: 3px;">
                    Monitors <code>support@nenotechnology.com</code> inbox · Analyzes customer questions · Answers with verified company intelligence
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

    # ── Reconcile Customer Replies from Excel and DB ──
    all_replies = []
    seen_emails = set()

    if os.path.exists(DEFAULT_REPLIES_EXCEL):
        try:
            excel_r_df = pd.read_excel(DEFAULT_REPLIES_EXCEL)
            for _, r in excel_r_df.iterrows():
                em = str(r.get("email") or "").strip().lower()
                if em and em not in seen_emails and "microsoftexchange" not in em and "postmaster" not in em:
                    seen_emails.add(em)
                    all_replies.append({
                        "email": em,
                        "name": str(r.get("name") or "").strip() if pd.notna(r.get("name")) and str(r.get("name")).strip() else "Customer",
                        "company": str(r.get("company") or "").strip() if pd.notna(r.get("company")) and str(r.get("company")).strip() else "—",
                        "reply_intent": str(r.get("reply_intent") or "question").strip(),
                        "customer_reply": str(r.get("customer_reply") or "").strip() if pd.notna(r.get("customer_reply")) else "",
                        "ai_response_sent": extract_text_from_ai_message(str(r.get("ai_response_sent") or "")),
                        "reply_received_at": str(r.get("reply_received_at") or "").strip() if pd.notna(r.get("reply_received_at")) else "",
                        "ai_reply_sent_at": str(r.get("ai_reply_sent_at") or "").strip() if pd.notna(r.get("ai_reply_sent_at")) else "",
                    })
        except Exception:
            pass

    if not df.empty:
        r_rows = df[df["reply_received_at"].notna() | df["reply_body"].notna() | df["ai_reply_sent"].notna()]
        for _, r in r_rows.iterrows():
            em = str(r.get("email") or "").strip().lower()
            if em and em not in seen_emails and "microsoftexchange" not in em and "postmaster" not in em:
                seen_emails.add(em)
                all_replies.append({
                    "email": em,
                    "name": str(r.get("name") or "").strip() if pd.notna(r.get("name")) and str(r.get("name")).strip() else "Customer",
                    "company": str(r.get("company") or "").strip() if pd.notna(r.get("company")) and str(r.get("company")).strip() else "—",
                    "reply_intent": str(r.get("reply_intent") or "question").strip(),
                    "customer_reply": str(r.get("reply_body") or "").strip() if pd.notna(r.get("reply_body")) else "",
                    "ai_response_sent": extract_text_from_ai_message(str(r.get("ai_reply_sent") or "")),
                    "reply_received_at": str(r.get("reply_received_at") or "").strip() if pd.notna(r.get("reply_received_at")) else "",
                    "ai_reply_sent_at": str(r.get("ai_reply_sent_at") or "").strip() if pd.notna(r.get("ai_reply_sent_at")) else "",
                })

    # ── Summary KPI Calculations ──
    booked_leads_count = 0
    if os.path.exists(DEFAULT_BOOKED_EXCEL):
        try:
            excel_df = pd.read_excel(DEFAULT_BOOKED_EXCEL)
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
                <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 7px 12px; margin-bottom: 8px;">
                    <div style="font-size: 12.5px; color: #334155;">
                        <span style="font-weight: 600; color: #0F172A;">🔗 Live Data Pipeline:</span>
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

    tab_replies_stream, tab_bookings_stream, tab_excel_stream = st.tabs([
        f"💬 Customer Inquiries & AI Auto-Replies ({replies_count})",
        f"📋 Customer Consultation Form Submissions ({forms_count})",
        f"📗 Permanent Excel Archives ({total_archive_records})",
    ])

    # ═══════════════════════════════════════════════════════════════
    # TAB 1: CUSTOMER INQUIRIES & AI AUTO-REPLIES
    # ═══════════════════════════════════════════════════════════════
    with tab_replies_stream:
        if not all_replies:
            st.info("No customer replies recorded yet. Click '⚡ Check Inbox & Auto-Reply Now' or start the background monitor to process incoming messages.")
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
                intent_filter_opts = ["All Intents", "Interested", "Question / Inquiry", "Meeting Request", "Reschedule", "Opted Out"]
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
                                        <span class="badge badge-scheduled" style="font-size: 10.5px;">📚 Grounded in Neno Technology Knowledge Base (PDF)</span>
                                        <span class="badge badge-sent" style="font-size: 10.5px;">✓ Dispatched via Microsoft Graph (support@nenotechnology.com)</span>
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
                                        <b>To:</b> Support &lt;support@nenotechnology.com&gt;<br>
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
    # TAB 2: CUSTOMER CONSULTATION FORM SUBMISSIONS
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
                excel_b_df = pd.read_excel(DEFAULT_BOOKED_EXCEL)
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
                    cr_export_df = pd.read_excel(DEFAULT_REPLIES_EXCEL)
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
                    excel_df = pd.read_excel(DEFAULT_BOOKED_EXCEL)
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
# MAIN ROUTER (Real-Time Live Sync Engine)
# ─────────────────────────────────────────────────────────────
page = st.session_state.active_page

@st.fragment(run_every="5s")
def render_live_telemetry_view(page_name: str):
    rows = load_campaign_logs()
    df_logs = pd.DataFrame(rows, columns=CAMPAIGN_LOG_COLUMNS) if rows else pd.DataFrame(columns=CAMPAIGN_LOG_COLUMNS)
    if page_name == "overview":
        render_overview(df_logs)
    elif page_name == "analytics":
        render_analytics(df_logs)
    elif page_name == "replies":
        render_replies(df_logs)

if page in ["overview", "analytics", "replies"]:
    render_live_telemetry_view(page)
elif page == "upload":
    render_upload()
elif page == "leads":
    rows = load_campaign_logs()
    df_logs = pd.DataFrame(rows, columns=CAMPAIGN_LOG_COLUMNS) if rows else pd.DataFrame(columns=CAMPAIGN_LOG_COLUMNS)
    render_leads(df_logs)
elif page == "email":
    rows = load_campaign_logs()
    df_logs = pd.DataFrame(rows, columns=CAMPAIGN_LOG_COLUMNS) if rows else pd.DataFrame(columns=CAMPAIGN_LOG_COLUMNS)
    render_email_review(df_logs)

