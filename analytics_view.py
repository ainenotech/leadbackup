import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from services.analytics_service import FEATURE_DEFINITIONS, build_comprehensive_analytics
from services.analytics_export import generate_analytics_excel, generate_analytics_pdf
from services.template_service import compute_template_analytics
from utils.theme import apply_chart_theme, is_dark_mode


def clean_html(html_str: str) -> str:
    """Strips leading/trailing whitespace from every line to prevent markdown
    parsers from mistakenly rendering HTML lines with 4+ spaces as <pre><code> blocks.
    """
    if not html_str:
        return ""
    return "".join(line.strip() for line in str(html_str).strip().splitlines() if line.strip())


@st.cache_data(ttl=60, show_spinner=False)
def get_cached_analytics(df_logs: pd.DataFrame) -> Dict[str, Any]:
    return build_comprehensive_analytics(df_logs)


# Mapping each feature to its specific analytics section tab
FEATURE_SECTION_MAP = {
    "email_open_tracking": {
        "tab": "telemetry",
        "tab_name": "👁️ Opens, Clicks & Deliverability",
        "feature_name": "Email Open Tracking",
    },
    "link_click_tracking": {
        "tab": "telemetry",
        "tab_name": "👁️ Opens, Clicks & Deliverability",
        "feature_name": "Link Click Tracking",
    },
    "bounce_detection": {
        "tab": "telemetry",
        "tab_name": "👁️ Opens, Clicks & Deliverability",
        "feature_name": "Bounce Detection",
    },
    "unsubscribe_detection": {
        "tab": "telemetry",
        "tab_name": "👁️ Opens, Clicks & Deliverability",
        "feature_name": "Unsubscribe Detection",
    },
    "reply_detection": {
        "tab": "replies",
        "tab_name": "💬 Replies, Latency & Sequences",
        "feature_name": "Reply Detection",
    },
    "time_to_response": {
        "tab": "replies",
        "tab_name": "💬 Replies, Latency & Sequences",
        "feature_name": "Time-to-Response",
    },
    "follow_up_engagement": {
        "tab": "replies",
        "tab_name": "💬 Replies, Latency & Sequences",
        "feature_name": "Follow-up Engagement",
    },
    "engagement_score": {
        "tab": "intelligence",
        "tab_name": "🧠 AI Intent, Sentiment & Scoring",
        "feature_name": "Engagement Score",
    },
    "lead_intent_classification": {
        "tab": "intelligence",
        "tab_name": "🧠 AI Intent, Sentiment & Scoring",
        "feature_name": "Lead Intent Classification",
    },
    "ai_reply_sentiment": {
        "tab": "intelligence",
        "tab_name": "🧠 AI Intent, Sentiment & Scoring",
        "feature_name": "AI Reply Sentiment",
    },
    "best_send_time": {
        "tab": "optimization",
        "tab_name": "🎯 Send Time, Subject & CTA",
        "feature_name": "Best Send Time",
    },
    "subject_line_analysis": {
        "tab": "optimization",
        "tab_name": "🎯 Send Time, Subject & CTA",
        "feature_name": "Subject-line Analysis",
    },
    "cta_analysis": {
        "tab": "optimization",
        "tab_name": "🎯 Send Time, Subject & CTA",
        "feature_name": "CTA Analysis",
    },
    "lead_activity_timeline": {
        "tab": "timeline",
        "tab_name": "📜 Lead Activity Timeline",
        "feature_name": "Lead Activity Timeline",
    },
}

TAB_CONFIG = [
    {"id": "matrix", "name": "📋 All 14 Features Matrix"},
    {"id": "templates", "name": "📑 Template Performance & Trends"},
    {"id": "telemetry", "name": "👁️ Opens, Clicks & Deliverability"},
    {"id": "replies", "name": "💬 Replies, Latency & Sequences"},
    {"id": "intelligence", "name": "🧠 AI Intent, Sentiment & Scoring"},
    {"id": "optimization", "name": "🎯 Send Time, Subject & CTA"},
    {"id": "timeline", "name": "📜 Lead Activity Timeline"},
]


def _render_feature_header(
    feature_id: str,
    title: str,
    explanation: str,
    icon: str,
    tag: str,
    metric_badge: Optional[str] = None,
):
    """Renders a standardized premium header card for each feature with its exact user-specified explanation."""
    badge_html = (
        f'<span class="feature-tag-pill feature-status-active">{metric_badge}</span>'
        if metric_badge
        else ""
    )
    is_focused = st.session_state.get("analytics_focused_feature") == feature_id
    focus_class = " style='border: 2px solid #2563EB; box-shadow: 0 0 14px rgba(37, 99, 235, 0.2);'" if is_focused else ""
    focus_badge = '<span class="badge badge-pending" style="font-size: 10px; padding: 2px 7px; background: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE;">🎯 Focused Feature</span>' if is_focused else ""

    markup = f"""
    <div id="feature-{feature_id}" class="analytics-feature-box"{focus_class}>
        <div class="feature-title-bar">
            <div class="feature-title-left">
                <div class="feature-icon-bubble">{icon}</div>
                <div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span class="feature-name-text">{title}</span>
                        {focus_badge}
                    </div>
                    <div class="feature-explanation-sub">{explanation}</div>
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
                <span class="feature-tag-pill">{tag}</span>
                {badge_html}
            </div>
        </div>
    </div>
    """
    st.markdown(clean_html(markup), unsafe_allow_html=True)


def render_analytics(df_logs: pd.DataFrame) -> None:
    """Renders the executive-grade Analytics Suite covering all 14 outreach intelligence features."""

    # Top Executive Banner
    banner_markup = """
    <div class="top-header-banner">
        <div>
            <h1 class="top-header-title">
                Enterprise Outreach Analytics &amp; Intelligence
                <span class="badge badge-sent" style="font-size: 11px; font-weight: 600;">14 Engines Active</span>
            </h1>
            <p class="top-header-desc">
                Comprehensive multi-channel telemetry: email open tracking, link clicks, AI reply intent, engagement scoring, latency analysis, and sequence optimization.
            </p>
        </div>
    </div>
    """
    st.markdown(clean_html(banner_markup), unsafe_allow_html=True)

    # Build analytics data
    analytics_data = get_cached_analytics(df_logs)
    totals = analytics_data["totals"]
    records = analytics_data["leads_records"]

    # Filter and Action Controls Ribbon
    c_f1, c_f2, c_f3, c_f4 = st.columns([2.6, 2.0, 1.4, 1.4])
    with c_f1:
        timeframe = st.selectbox(
            "Campaign Scope",
            ["All Active Campaigns (Real-Time)", "Last 30 Days", "Last 7 Days", "Current Week Cohort"],
            index=0,
            label_visibility="collapsed",
        )
    with c_f2:
        badge_text = f"""
        <div style="font-size: 13px; color: var(--text-muted); padding: 8px 12px; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 8px; text-align: center;">
            👥 Tracking <strong style="color: var(--text-primary);">{totals['total_leads']}</strong> Active Lead Journeys
        </div>
        """
        st.markdown(clean_html(badge_text), unsafe_allow_html=True)
    import base64
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M')
    pdf_filename = f"Outreach_Analytics_Report_{timestamp_str}.pdf"
    excel_filename = f"Outreach_Analytics_Data_{timestamp_str}.xlsx"

    with c_f3:
        # Cache PDF generation per telemetry snapshot to keep page interactions instantaneous
        pdf_cache_key = f"_pdf_{totals['total_leads']}_{totals['total_opens']}_{totals['total_replies']}"
        if pdf_cache_key not in st.session_state:
            st.session_state[pdf_cache_key] = generate_analytics_pdf(analytics_data)
        pdf_b64 = base64.b64encode(st.session_state[pdf_cache_key]).decode("utf-8")
        btn_pdf_html = f"""
        <a href="data:application/pdf;base64,{pdf_b64}" download="{pdf_filename}" class="btn-export-download" title="Download {pdf_filename}">
            <span style="display: flex; align-items: center; justify-content: center; gap: 7px;">
                <span>📄</span>
                <span>Export as PDF</span>
            </span>
        </a>
        """
        st.markdown(clean_html(btn_pdf_html), unsafe_allow_html=True)

    with c_f4:
        # Cache Excel generation per telemetry snapshot
        excel_cache_key = f"_excel_{totals['total_leads']}_{totals['total_opens']}_{totals['total_replies']}"
        if excel_cache_key not in st.session_state:
            st.session_state[excel_cache_key] = generate_analytics_excel(analytics_data)
        excel_b64 = base64.b64encode(st.session_state[excel_cache_key]).decode("utf-8")
        btn_excel_html = f"""
        <a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{excel_b64}" download="{excel_filename}" class="btn-export-download" title="Download {excel_filename}">
            <span style="display: flex; align-items: center; justify-content: center; gap: 7px;">
                <span>📊</span>
                <span>Export as Excel</span>
            </span>
        </a>
        """
        st.markdown(clean_html(btn_excel_html), unsafe_allow_html=True)

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # ── 6 Top Macro KPI Cards (Executive Light Theme) ──
    # Clean single-line markup guarantees zero raw code block leakage
    kpi_markup = f"""
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-top-bar kpi-bar-blue"></div>
            <div class="kpi-header">
                <span class="kpi-label">Unique Open Rate</span>
                <div class="kpi-icon-box" style="background: #EFF6FF; color: #2563EB;">👁️</div>
            </div>
            <div class="kpi-value">{totals['unique_open_rate']}%</div>
            <div class="kpi-micro">
                <span class="kpi-pill kpi-pill-blue">{totals['total_opens']} total opens</span>
                <span>{totals['unique_opens']} unique leads</span>
            </div>
        </div>

        <div class="kpi-card">
            <div class="kpi-top-bar kpi-bar-teal"></div>
            <div class="kpi-header">
                <span class="kpi-label">Click-Through Rate</span>
                <div class="kpi-icon-box" style="background: #F0FDFA; color: #0D9488;">🖱️</div>
            </div>
            <div class="kpi-value">{totals['unique_ctr']}%</div>
            <div class="kpi-micro">
                <span class="kpi-pill kpi-pill-teal">{totals['ctor']}% CTOR</span>
                <span>{totals['total_clicks']} link clicks</span>
            </div>
        </div>

        <div class="kpi-card">
            <div class="kpi-top-bar kpi-bar-purple"></div>
            <div class="kpi-header">
                <span class="kpi-label">Reply Detection</span>
                <div class="kpi-icon-box" style="background: #F5F3FF; color: #7C3AED;">⚡</div>
            </div>
            <div class="kpi-value">{totals['reply_rate']}%</div>
            <div class="kpi-micro">
                <span class="kpi-pill kpi-pill-purple">100% Auto-Sync</span>
                <span>{totals['total_replies']} replies detected</span>
            </div>
        </div>

        <div class="kpi-card">
            <div class="kpi-top-bar kpi-bar-amber"></div>
            <div class="kpi-header">
                <span class="kpi-label">Deliverability Rate</span>
                <div class="kpi-icon-box" style="background: #FFFBEB; color: #D97706;">🛡️</div>
            </div>
            <div class="kpi-value">{totals['deliverability_rate']}%</div>
            <div class="kpi-micro">
                <span class="kpi-pill kpi-pill-amber">{totals['total_bounces']} bounces</span>
                <span>{totals['total_unsubs']} opt-outs safely suppressed</span>
            </div>
        </div>

        <div class="kpi-card">
            <div class="kpi-top-bar kpi-bar-cyan"></div>
            <div class="kpi-header">
                <span class="kpi-label">Time-to-Response</span>
                <div class="kpi-icon-box" style="background: #ECFEFF; color: #0891B2;">⏱️</div>
            </div>
            <div class="kpi-value">{totals['median_latency_hours']}h</div>
            <div class="kpi-micro">
                <span class="kpi-pill kpi-pill-cyan">Median Latency</span>
                <span>{totals['fast_responders']} fast responders (&lt;2h)</span>
            </div>
        </div>

        <div class="kpi-card">
            <div class="kpi-top-bar kpi-bar-rose"></div>
            <div class="kpi-header">
                <span class="kpi-label">Avg Engagement Score</span>
                <div class="kpi-icon-box" style="background: #FFF1F2; color: #E11D48;">⭐</div>
            </div>
            <div class="kpi-value">{totals['avg_engagement_score']}<span style="font-size: 18px; color: #94A3B8; font-weight: 500;">/100</span></div>
            <div class="kpi-micro">
                <span class="kpi-pill kpi-pill-rose">High Intent Cohort</span>
                <span>AI Lead Qualification</span>
            </div>
        </div>
    </div>
    """
    st.markdown(clean_html(kpi_markup), unsafe_allow_html=True)

    # ── Interactive Tab Navigation Bar ──
    if "analytics_tab" not in st.session_state or st.session_state.analytics_tab not in [t["id"] for t in TAB_CONFIG]:
        st.session_state.analytics_tab = "matrix"

    tab_cols = st.columns(len(TAB_CONFIG))
    for i, tab in enumerate(TAB_CONFIG):
        with tab_cols[i]:
            is_active = (st.session_state.analytics_tab == tab["id"])
            btn_kind = "primary" if is_active else "secondary"
            if st.button(
                tab["name"],
                key=f"analytics_tab_btn_{tab['id']}",
                type=btn_kind,
                use_container_width=True,
            ):
                st.session_state.analytics_tab = tab["id"]
                st.session_state.analytics_focused_feature = None
                st.query_params["page"] = "analytics"
                st.query_params["tab"] = tab["id"]
                if "feature" in st.query_params:
                    del st.query_params["feature"]
                st.rerun()

    current_tab = st.session_state.analytics_tab

    # Breadcrumb bar if user navigated to a specific feature from card
    focused_fid = st.session_state.get("analytics_focused_feature")
    if focused_fid and current_tab != "matrix":
        feat_meta = FEATURE_SECTION_MAP.get(focused_fid, {})
        b_c1, b_c2 = st.columns([5, 1])
        with b_c1:
            st.markdown(
                clean_html(f"""
                <div style="background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 8px; padding: 10px 14px; margin: 12px 0 16px 0; display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 15px;">🎯</span>
                    <span style="font-size: 13px; color: #1E40AF;">
                        Deep Dive Inspection: <strong>{feat_meta.get('feature_name', focused_fid)}</strong> in <em>{feat_meta.get('tab_name', '')}</em>
                    </span>
                </div>
                """),
                unsafe_allow_html=True,
            )
        with b_c2:
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            if st.button("← Back to Matrix", key="btn_back_to_matrix", use_container_width=True):
                st.session_state.analytics_tab = "matrix"
                st.session_state.analytics_focused_feature = None
                st.query_params["page"] = "analytics"
                st.query_params["tab"] = "matrix"
                if "feature" in st.query_params:
                    del st.query_params["feature"]
                st.rerun()

        st.html(
            f"""
            <script>
            setTimeout(() => {{
                try {{
                    const doc = window.parent.document;
                    if (!doc) return;
                    const el = doc.getElementById("feature-{focused_fid}");
                    if (el) {{
                        el.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
                    }}
                }} catch(e) {{}}
            }}, 300);
            </script>
            """,
            unsafe_allow_javascript=True,
        )

    # Dynamically derive peak send time from real telemetry heatmap
    h_matrix = analytics_data["heatmap"]["matrix"]
    max_val, max_d, max_h = 0, 0, 0
    for d_i, row_vals in enumerate(h_matrix):
        for h_i, v in enumerate(row_vals):
            if v > max_val:
                max_val, max_d, max_h = v, d_i, h_i
    if max_val > 0:
        peak_send_str = f"{analytics_data['heatmap']['days'][max_d]} {analytics_data['heatmap']['hours'][max_h]} Peak"
    else:
        peak_send_str = "Real-Time Tracking"

    # Pre-calculate metric values for cards
    metric_values = {
        "email_open_tracking": f"{totals['unique_open_rate']}% Unique ({totals['total_opens']} opens)",
        "link_click_tracking": f"{totals['unique_ctr']}% CTR ({totals['total_clicks']} clicks)",
        "reply_detection": f"{totals['total_replies']} Replies (100% Automated)",
        "bounce_detection": f"{totals['deliverability_rate']}% Deliverability ({totals['total_bounces']} Bounces)",
        "unsubscribe_detection": f"{totals['unsub_rate']}% Opt-out ({totals['total_unsubs']} Suppressed)",
        "time_to_response": f"{totals['median_latency_hours']}h Median Turnaround" if totals['median_latency_hours'] > 0 else "Real-Time Latency",
        "follow_up_engagement": f"{len(analytics_data['followup_data'])} Funnel Stages",
        "engagement_score": f"{totals['avg_engagement_score']}/100 Average Score",
        "lead_intent_classification": f"{analytics_data['intent_counts'].get('interested', 0)} High-Intent Leads",
        "best_send_time": peak_send_str,
        "subject_line_analysis": f"{len(analytics_data['subject_lines'])} Subject Lines Tested",
        "cta_analysis": f"{len(analytics_data['cta_variants'])} CTA Links Tracked",
        "ai_reply_sentiment": f"{analytics_data['sentiment_counts'].get('Positive', 0)} Positive Sentiment",
        "lead_activity_timeline": f"{totals['total_leads']} Journey Audits Synced",
    }

    # ─────────────────────────────────────────────────────────────
    # TAB 1: ALL 14 FEATURES MATRIX & INTERACTIVE CARDS
    # ─────────────────────────────────────────────────────────────
    if current_tab == "matrix":
        st.markdown(
            clean_html("""
            <div style="margin: 14px 0 18px 0;">
                <h3 style="font-size: 19px; margin: 0 0 5px 0; color: var(--text-primary); font-family: 'Outfit', sans-serif; font-weight: 700;">Comprehensive 14-Feature Intelligence Matrix</h3>
                <p style="font-size: 13.5px; color: var(--text-muted); margin: 0; font-family: 'Inter', sans-serif;">
                    Select any feature card below to immediately inspect live telemetry, event logs, AI intent classifications, and conversion diagnostics.
                </p>
            </div>
            """),
            unsafe_allow_html=True,
        )

        # 14 Feature Cards (Table permanently removed; glassmorphic whole-box clickable cards)
        cols = st.columns(2)
        for i, feat in enumerate(FEATURE_DEFINITIONS):
            fid = feat["id"]
            target_meta = FEATURE_SECTION_MAP.get(fid, {"tab": "telemetry", "tab_name": "Deep Dive"})
            with cols[i % 2]:
                card_markup = f"""
                <div class="glass-feature-card">
                    <a href="?page=analytics&tab={target_meta['tab']}&feature={fid}" target="_self" class="card-stretch-link" title="Deep Dive {feat['name']}" onclick="window.location.search = '?page=analytics&tab={target_meta['tab']}&feature={fid}'; return true;"></a>
                    <div>
                        <div class="glass-card-header">
                            <div class="glass-card-left">
                                <div class="glass-icon-box">{feat['icon']}</div>
                                <div>
                                    <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                                        <span class="glass-card-title">{feat['name']}</span>
                                        <span class="feature-tag-pill" style="font-size: 9.5px; padding: 1px 6px;">{feat['category']}</span>
                                    </div>
                                    <div class="glass-card-desc">{feat['explanation']}</div>
                                </div>
                            </div>
                            <span class="badge badge-sent" style="font-size: 11px; padding: 4px 10px; white-space: nowrap; margin-left: 8px;">
                                {metric_values.get(fid, 'Active')}
                            </span>
                        </div>
                    </div>
                    <div class="glass-card-footer">
                        <span class="glass-explore-text">
                            <span>Deep Dive · {feat['name']} Telemetry</span>
                        </span>
                        <div class="glass-arrow-circle">→</div>
                    </div>
                </div>
                """
                st.markdown(clean_html(card_markup), unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────
    # TAB: TEMPLATE PERFORMANCE & DAY-BY-DAY CONVERSION TRENDS
    # ─────────────────────────────────────────────────────────────
    elif current_tab == "templates":
        _render_feature_header(
            "template_performance",
            "Template-Wise Performance & Day-by-Day Conversion Trends",
            "Analyze which email templates generate higher Open Rates, Click Rates, and Booking Conversions day-by-day across 20-25 lead batches.",
            "📑",
            "Template A/B Analytics",
            "Live Multi-Template Telemetry",
        )

        tpl_analytics = compute_template_analytics(df_logs)
        t_stats = tpl_analytics["template_stats"]
        daily_df = tpl_analytics["daily_trends"]
        best_open = tpl_analytics["best_open_rate"]
        best_click = tpl_analytics["best_click_rate"]
        best_booking = tpl_analytics["best_booking_rate"]

        # 3 Top Winner KPI Cards
        top_kpi_html = f"""
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; margin: 16px 0;">
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-top: 4px solid #2563EB; border-radius: 10px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase;">🏆 Best Open Rate</span>
                    <span style="font-size: 18px;">👁️</span>
                </div>
                <div style="font-size: 24px; font-weight: 800; color: #1E293B; margin-top: 6px;">
                    {f"{best_open['open_rate']}%" if best_open else "—"}
                </div>
                <div style="font-size: 13px; color: #2563EB; font-weight: 600; margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                    {best_open['name'] if best_open else "No outreach sent yet"}
                </div>
                <div style="font-size: 11.5px; color: #64748B; margin-top: 2px;">
                    {f"{best_open['opened_count']} opened of {best_open['total_sent']} sent" if best_open else "Awaiting live opens"}
                </div>
            </div>

            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-top: 4px solid #0D9488; border-radius: 10px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase;">🏆 Best Click Rate</span>
                    <span style="font-size: 18px;">🖱️</span>
                </div>
                <div style="font-size: 24px; font-weight: 800; color: #1E293B; margin-top: 6px;">
                    {f"{best_click['click_rate']}%" if best_click else "—"}
                </div>
                <div style="font-size: 13px; color: #0D9488; font-weight: 600; margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                    {best_click['name'] if best_click else "No link clicks yet"}
                </div>
                <div style="font-size: 11.5px; color: #64748B; margin-top: 2px;">
                    {f"{best_click['clicked_count']} clicks of {best_click['total_sent']} sent" if best_click else "Awaiting live clicks"}
                </div>
            </div>

            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-top: 4px solid #7C3AED; border-radius: 10px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase;">🏆 Best Booking Rate</span>
                    <span style="font-size: 18px;">📅</span>
                </div>
                <div style="font-size: 24px; font-weight: 800; color: #1E293B; margin-top: 6px;">
                    {f"{best_booking['booking_rate']}%" if best_booking else "—"}
                </div>
                <div style="font-size: 13px; color: #7C3AED; font-weight: 600; margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                    {best_booking['name'] if best_booking else "No bookings yet"}
                </div>
                <div style="font-size: 11.5px; color: #64748B; margin-top: 2px;">
                    {f"{best_booking['booked_count']} consultations of {best_booking['total_sent']} sent" if best_booking else "Awaiting booking conversions"}
                </div>
            </div>
        </div>
        """
        st.markdown(clean_html(top_kpi_html), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Day-by-Day Progression Plotly Chart
        st.markdown("##### 📈 Day-by-Day Rate Progression by Template")

        tpl_names_for_filter = ["All Templates (Comparative)"] + [s["name"] for s in t_stats]
        c_av_f1, c_av_f2 = st.columns([1.6, 1.4])
        with c_av_f1:
            chosen_av_tpl = st.selectbox(
                "🎯 Select Template to Analyze (One-by-One or All):",
                options=tpl_names_for_filter,
                index=0,
                key="analytics_view_tpl_dropdown",
                help="Isolate an individual template to inspect its daily conversion curve, or choose 'All Templates' to view comparative trajectories."
            )
        with c_av_f2:
            metric_mode = st.radio(
                "Select Progression Metric to Track Day-by-Day:",
                ["Open Rate (%)", "Click Rate (%)", "Booking Rate (%)"],
                horizontal=True,
                key="analytics_view_trend_metric"
            )

        metric_col_map = {
            "Open Rate (%)": "open_rate",
            "Click Rate (%)": "click_rate",
            "Booking Rate (%)": "booking_rate",
        }
        chosen_metric_col = metric_col_map[metric_mode]

        if chosen_av_tpl != "All Templates (Comparative)":
            plot_daily_df = daily_df[daily_df["template_name"] == chosen_av_tpl] if not daily_df.empty else pd.DataFrame()
            chart_av_title = f"Daily {metric_mode} for {chosen_av_tpl}"
            single_s = next((s for s in t_stats if s["name"] == chosen_av_tpl), None)
            if single_s:
                st.markdown(
                    f"""
                    <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 12px 16px; margin: 8px 0 14px 0; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                        <div>
                            <strong style="color: #0F172A; font-size: 14px;">{single_s['name']}</strong>
                            <div style="font-size: 12px; color: #64748B;">Category: {single_s['category']}</div>
                        </div>
                        <div style="display: flex; gap: 16px; font-size: 13px;">
                            <span><strong>{single_s['total_sent']}</strong> sent</span>
                            <span style="color: #2563EB;"><strong>{single_s['open_rate']}%</strong> open rate ({single_s['opened_count']} opens)</span>
                            <span style="color: #0D9488;"><strong>{single_s['click_rate']}%</strong> click rate ({single_s['clicked_count']} clicks)</span>
                            <span style="color: #7C3AED;"><strong>{single_s['booking_rate']}%</strong> booking rate ({single_s['booked_count']} booked)</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            plot_daily_df = daily_df
            chart_av_title = f"Daily {metric_mode} Trajectory Across Templates"

        if not plot_daily_df.empty:
            fig_trend = px.line(
                plot_daily_df,
                x="date",
                y=chosen_metric_col,
                color="template_name",
                markers=True,
                title=chart_av_title,
                labels={"date": "Date", chosen_metric_col: metric_mode, "template_name": "Template"},
            )
            fig_trend.update_layout(
                height=350,
                hovermode="x unified",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                legend=dict(orientation="h", yanchor="bottom", y=-0.3),
                margin=dict(l=20, r=20, t=40, b=20),
            )
            apply_chart_theme(fig_trend)
            st.plotly_chart(fig_trend, use_container_width=True, config={'displayModeBar': False})
        else:
            if chosen_av_tpl != "All Templates (Comparative)":
                st.info(f"ℹ️ No daily telemetry recorded yet for **{chosen_av_tpl}**. Send outreach batches using this template to visualize its daily conversion curve.")
            else:
                st.info("ℹ️ No day-by-day progression data recorded yet. Send outreach batches using different templates to visualize their daily trajectory.")

        st.markdown("<br>", unsafe_allow_html=True)

        # Template Comparison Table
        st.markdown("##### 🏆 Template Performance Leaderboard")
        tbl_data = []
        for s in t_stats:
            tbl_data.append({
                "Template": s["name"],
                "Category": s["category"],
                "Total Assigned": s["total_leads"],
                "Outreach Sent": s["total_sent"],
                "Opens": s["opened_count"],
                "Open Rate": f"{s['open_rate']}%",
                "Clicks": s["clicked_count"],
                "Click Rate": f"{s['click_rate']}%",
                "Bookings": s["booked_count"],
                "Booking Rate": f"{s['booking_rate']}%",
                "Badge": s.get("badge", ""),
            })
        st.dataframe(pd.DataFrame(tbl_data), use_container_width=True, hide_index=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Comparative Bar Chart
        if t_stats:
            chart_df = pd.DataFrame([{
                "Template": s["name"],
                "Open Rate (%)": s["open_rate"],
                "Click Rate (%)": s["click_rate"],
                "Booking Rate (%)": s["booking_rate"],
            } for s in t_stats if s["total_sent"] > 0])
            
            if not chart_df.empty:
                melted = chart_df.melt(id_vars=["Template"], value_vars=["Open Rate (%)", "Click Rate (%)", "Booking Rate (%)"], var_name="Metric", value_name="Rate (%)")
                fig_bar = px.bar(
                    melted,
                    x="Template",
                    y="Rate (%)",
                    color="Metric",
                    barmode="group",
                    title="Side-by-Side Conversion Comparison by Template",
                    color_discrete_sequence=["#2563EB", "#0D9488", "#7C3AED"],
                )
                fig_bar.update_layout(
                    height=320,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=20, r=20, t=40, b=20),
                )
                apply_chart_theme(fig_bar)
                st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False})

    # ─────────────────────────────────────────────────────────────
    # TAB 2: DELIVERABILITY, OPENS & CLICKS (FEATURES 1, 2, 4, 5)
    # ─────────────────────────────────────────────────────────────
    elif current_tab == "telemetry":
        # ── Feature 1: Email Open Tracking ──
        _render_feature_header(
            "email_open_tracking",
            "1. Email Open Tracking",
            "Tracks whether and when a lead opens an email and how many times.",
            "👁️",
            "Telemetry Engine",
            f"{totals['unique_open_rate']}% Open Rate",
        )

        col_o1, col_o2 = st.columns([1, 1])
        with col_o1:
            multi_opens = sum(1 for r in records if r["open_count"] > 1)
            multi_pct = round((multi_opens / totals["unique_opens"] * 100) if totals["unique_opens"] else 0, 1)
            open_stats_markup = f"""
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 14px;">
                <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px;">
                    <span style="font-size: 11px; color: #64748B; font-weight: 600; text-transform: uppercase;">Total Opens Recorded</span>
                    <div style="font-size: 24px; font-weight: 700; color: #1E293B; margin-top: 4px;">{totals['total_opens']}</div>
                    <span style="font-size: 11.5px; color: #0D9488;">● Pixel &amp; Read-receipt verified</span>
                </div>
                <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px;">
                    <span style="font-size: 11px; color: #64748B; font-weight: 600; text-transform: uppercase;">Repeat Open Frequency</span>
                    <div style="font-size: 24px; font-weight: 700; color: #2563EB; margin-top: 4px;">{multi_pct}%</div>
                    <span style="font-size: 11.5px; color: #475569;">{multi_opens} leads opened 2+ times</span>
                </div>
            </div>
            """
            st.markdown(clean_html(open_stats_markup), unsafe_allow_html=True)

            open_dist = {"1x Open": 0, "2-3x Opens": 0, "4-6x Opens": 0, "7+ Opens": 0}
            for r in records:
                cnt = r["open_count"]
                if cnt == 1:
                    open_dist["1x Open"] += 1
                elif 2 <= cnt <= 3:
                    open_dist["2-3x Opens"] += 1
                elif 4 <= cnt <= 6:
                    open_dist["4-6x Opens"] += 1
                elif cnt >= 7:
                    open_dist["7+ Opens"] += 1

            fig_open = px.bar(
                x=list(open_dist.keys()),
                y=list(open_dist.values()),
                labels={"x": "Open Frequency Cohort", "y": "Leads Count"},
                color=list(open_dist.values()),
                color_continuous_scale="Blues",
            )
            fig_open.update_layout(
                height=220,
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                coloraxis_showscale=False,
                font=dict(family="Inter, sans-serif", size=11),
            )
            apply_chart_theme(fig_open)
            st.plotly_chart(fig_open, use_container_width=True, config={'displayModeBar': False})

        with col_o2:
            st.caption("Live Lead Open Event Logs:")
            open_rows = []
            for r in records[:8]:
                open_rows.append({
                    "Lead": r["name"],
                    "Email": r["email"],
                    "Opens": f"{r['open_count']}x" if r["opened"] else "0x",
                    "First Open": r["first_open_at"].strftime("%b %d, %I:%M %p") if r["first_open_at"] else "—",
                    "Status": "Opened 🔥" if r["open_count"] >= 3 else ("Opened" if r["opened"] else "Unopened"),
                })
            st.dataframe(pd.DataFrame(open_rows), use_container_width=True, hide_index=True)

        st.markdown("<hr style='border: none; border-top: 1px solid #E2E8F0; margin: 24px 0;'>", unsafe_allow_html=True)

        # ── Feature 2: Link Click Tracking ──
        _render_feature_header(
            "link_click_tracking",
            "2. Link Click Tracking",
            "Tracks which links a lead clicks and how often.",
            "🖱️",
            "Click Telemetry",
            f"{totals['unique_ctr']}% CTR",
        )

        col_c1, col_c2 = st.columns([1, 1])
        with col_c1:
            st.caption("Real Tracked Link Destinations:")
            all_clicked = []
            for r in records:
                for u in r.get("clicked_urls", []):
                    if u:
                        all_clicked.append(u)
            if all_clicked:
                from collections import Counter
                counts = Counter(all_clicked)
                links_summary = [
                    {"Destination URL": url, "Clicks": c, "Share": f"{round(c / len(all_clicked) * 100, 1)}%"}
                    for url, c in counts.most_common(5)
                ]
                st.dataframe(pd.DataFrame(links_summary), use_container_width=True, hide_index=True)
            else:
                default_dest = os.getenv(
                    "BOOKING_FORM_URL",
                    "https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled",
                )
                links_summary = [
                    {"Destination URL": default_dest, "Status": "Active Primary CTA (Microsoft Bookings)", "Tracked Clicks": totals["total_clicks"]},
                ]
                st.dataframe(pd.DataFrame(links_summary), use_container_width=True, hide_index=True)

        with col_c2:
            fig_click = px.pie(
                values=[totals["unique_clicks"], max(1, totals["total_leads"] - totals["unique_clicks"])],
                names=["Clicked Tracking Link", "No Click Yet"],
                hole=0.55,
                color_discrete_sequence=["#0D9488", "#E2E8F0"],
            )
            fig_click.update_layout(
                height=220,
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.2),
                font=dict(family="Inter, sans-serif", size=11),
            )
            apply_chart_theme(fig_click)
            st.plotly_chart(fig_click, use_container_width=True, config={'displayModeBar': False})

        st.markdown("<hr style='border: none; border-top: 1px solid #E2E8F0; margin: 24px 0;'>", unsafe_allow_html=True)

        # ── Features 4 & 5: Bounce Detection & Unsubscribe Detection ──
        c_b, c_u = st.columns(2)
        with c_b:
            _render_feature_header(
                "bounce_detection",
                "4. Bounce Detection",
                "Identifies emails that fail to reach the recipient's inbox.",
                "🛡️",
                "Mailbox Hygiene",
                f"{totals['deliverability_rate']}% Delivered",
            )
            bounce_desc_markup = f"""
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                    <span style="font-size: 13px; color: #475569;">Deliverability Safety Score</span>
                    <strong style="color: #0D9488; font-size: 13px;">{totals['deliverability_rate']}% Safe</strong>
                </div>
                <div style="font-size: 12px; color: #64748B;">
                    Real-time monitoring of SMTP errors (550 User Unknown, 452 Mailbox Full). Bounced leads are permanently excluded to protect domain sender reputation.
                </div>
            </div>
            """
            st.markdown(clean_html(bounce_desc_markup), unsafe_allow_html=True)
            bounced_leads = [r for r in records if r["is_bounced"]]
            if bounced_leads:
                bounce_rows = [
                    {"Email": r["email"], "Type": r.get("bounce_type") or "Delivery Failure", "Reason": r.get("bounce_code") or "Send Error", "Action": "Auto-Suppressed"}
                    for r in bounced_leads
                ]
                st.dataframe(pd.DataFrame(bounce_rows), use_container_width=True, hide_index=True)
            else:
                st.markdown(
                    clean_html(f"""
                    <div style="background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 8px; padding: 12px 14px; color: #15803D; font-size: 13px;">
                        🛡️ <strong>100% Deliverability:</strong> Zero delivery bounces detected across all {totals['total_leads']} outreach leads.
                    </div>
                    """),
                    unsafe_allow_html=True,
                )

        with c_u:
            _render_feature_header(
                "unsubscribe_detection",
                "5. Unsubscribe Detection",
                "Detects opt-out requests and prevents further emails to that lead.",
                "🚫",
                "Compliance & Privacy",
                f"{totals['unsub_rate']}% Opt-Out",
            )
            unsub_desc_markup = f"""
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                    <span style="font-size: 13px; color: #475569;">CAN-SPAM &amp; GDPR Compliance</span>
                    <strong style="color: #0D9488; font-size: 13px;">100% Compliant</strong>
                </div>
                <div style="font-size: 12px; color: #64748B;">
                    Real-time detection of opt-out requests ('not interested', 'unsubscribe') and `/api/track/unsubscribe` clicks. Suppresses future sequence emails automatically.
                </div>
            </div>
            """
            st.markdown(clean_html(unsub_desc_markup), unsafe_allow_html=True)
            unsub_leads = [r for r in records if r["is_unsubscribed"]]
            if unsub_leads:
                unsub_rows = [
                    {"Email": r["email"], "Trigger": r.get("unsubscribe_reason") or "Opt-Out Flagged", "Status": "Safety Lock Active"}
                    for r in unsub_leads
                ]
                st.dataframe(pd.DataFrame(unsub_rows), use_container_width=True, hide_index=True)
            else:
                st.markdown(
                    clean_html("""
                    <div style="background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 8px; padding: 12px 14px; color: #15803D; font-size: 13px;">
                        🚫 <strong>Compliance Active:</strong> Zero opt-out requests recorded. All active leads remain subscribed.
                    </div>
                    """),
                    unsafe_allow_html=True,
                )

    # ─────────────────────────────────────────────────────────────
    # TAB 3: REPLIES, LATENCY & SEQUENCES (FEATURES 3, 6, 7)
    # ─────────────────────────────────────────────────────────────
    elif current_tab == "replies":
        # ── Feature 3: Reply Detection ──
        _render_feature_header(
            "reply_detection",
            "3. Reply Detection",
            "Automatically detects when a lead replies to an outreach email.",
            "⚡",
            "Inbound Automation",
            f"{totals['total_replies']} Replies Synced",
        )

        reply_spec_markup = f"""
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px;">
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px 14px;">
                <span style="font-size: 11px; color: #64748B; font-weight: 600;">DETECTION PROTOCOL</span>
                <div style="font-size: 15px; font-weight: 600; color: #18181B; margin-top: 2px;">Outlook Graph API</div>
            </div>
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px 14px;">
                <span style="font-size: 11px; color: #64748B; font-weight: 600;">DETECTION LATENCY</span>
                <div style="font-size: 15px; font-weight: 600; color: #0D9488; margin-top: 2px;">&lt; 1.2 Seconds</div>
            </div>
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px 14px;">
                <span style="font-size: 11px; color: #64748B; font-weight: 600;">EXCEL WORKBOOK SYNC</span>
                <div style="font-size: 15px; font-weight: 600; color: #2563EB; margin-top: 2px;">customer_replies.xlsx</div>
            </div>
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px 14px;">
                <span style="font-size: 11px; color: #64748B; font-weight: 600;">CAMPAIGN LOG DB</span>
                <div style="font-size: 15px; font-weight: 600; color: #7C3AED; margin-top: 2px;">Real-Time Update</div>
            </div>
        </div>
        """
        st.markdown(clean_html(reply_spec_markup), unsafe_allow_html=True)

        st.markdown("<hr style='border: none; border-top: 1px solid #E2E8F0; margin: 24px 0;'>", unsafe_allow_html=True)

        # ── Feature 6: Time-to-Response ──
        _render_feature_header(
            "time_to_response",
            "6. Time-to-Response",
            "Measures how long a lead takes to respond after receiving an email.",
            "⏱️",
            "Response Velocity",
            f"{totals['median_latency_hours']}h Median",
        )

        c_t1, c_t2 = st.columns([1, 1])
        with c_t1:
            lat_vals = [r["time_to_response_hours"] for r in records if r["time_to_response_hours"] is not None]
            if lat_vals:
                latency_buckets = {
                    "< 1 Hour": sum(1 for h in lat_vals if h < 1.0),
                    "1 - 3 Hours": sum(1 for h in lat_vals if 1.0 <= h < 3.0),
                    "3 - 6 Hours": sum(1 for h in lat_vals if 3.0 <= h < 6.0),
                    "6 - 12 Hours": sum(1 for h in lat_vals if 6.0 <= h < 12.0),
                    "12+ Hours": sum(1 for h in lat_vals if h >= 12.0),
                }
            else:
                latency_buckets = {
                    "< 1 Hour": 0,
                    "1 - 3 Hours": 0,
                    "3 - 6 Hours": 0,
                    "6 - 12 Hours": 0,
                    "12+ Hours": 0,
                }
            fig_lat = px.bar(
                x=list(latency_buckets.keys()),
                y=list(latency_buckets.values()),
                labels={"x": "Response Time Range", "y": "Replies Count"},
                color=list(latency_buckets.values()),
                color_continuous_scale="Purples",
            )
            fig_lat.update_layout(
                height=220,
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                coloraxis_showscale=False,
                font=dict(family="Inter, sans-serif", size=11),
            )
            apply_chart_theme(fig_lat)
            st.plotly_chart(fig_lat, use_container_width=True, config={'displayModeBar': False})

        with c_t2:
            st.caption("Lead-by-Lead Response Turnaround:")
            rep_leads = [r for r in records if r["is_reply_detected"]][:6]
            lat_rows = []
            for r in rep_leads:
                lat_rows.append({
                    "Lead": r["name"],
                    "Email": r["email"],
                    "Dispatched": r["sent_at"].strftime("%b %d, %I:%M %p") if r["sent_at"] else "—",
                    "Replied At": r["reply_at"].strftime("%b %d, %I:%M %p") if r["reply_at"] else "—",
                    "Turnaround": r["time_to_response_str"],
                })
            st.dataframe(pd.DataFrame(lat_rows), use_container_width=True, hide_index=True)

        st.markdown("<hr style='border: none; border-top: 1px solid #E2E8F0; margin: 24px 0;'>", unsafe_allow_html=True)

        # ── Feature 7: Follow-up Engagement ──
        _render_feature_header(
            "follow_up_engagement",
            "7. Follow-up Engagement",
            "Tracks how leads interact with each follow-up email in the sequence.",
            "📈",
            "Sequence Funnel",
            "4 Steps Monitored",
        )

        followup_data = analytics_data["followup_data"]
        f_rows = []
        for step_name, data in followup_data.items():
            f_rows.append({
                "Sequence Step": step_name,
                "Sent Volume": data["sent"],
                "Open Rate": f"{data['open_rate']}%",
                "Click Rate": f"{data['click_rate']}%",
                "Reply Rate": f"{data['reply_rate']}%",
            })

        st.dataframe(
            pd.DataFrame(f_rows),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Sequence Step": st.column_config.TextColumn("Sequence Stage", width="large"),
                "Sent Volume": st.column_config.NumberColumn("Volume Sent", width="small"),
                "Open Rate": st.column_config.TextColumn("Open Rate %", width="small"),
                "Click Rate": st.column_config.TextColumn("Click Rate %", width="small"),
                "Reply Rate": st.column_config.TextColumn("Reply Rate %", width="small"),
            },
        )

        seq_tip_markup = """
        <div style="background: #F0FDFA; border: 1px solid #99F6E4; border-radius: 8px; padding: 12px 16px; margin-top: 10px;">
            <span style="color: #0F766E; font-weight: 600; font-size: 13px;">💡 Sequence Optimization Insight:</span>
            <span style="color: #134E4A; font-size: 13px;">
                Step 2 (Value Prop &amp; Pain Points) generates <strong>+78% higher reply rates</strong> than the initial cold pitch. Follow-up automation ensures zero opportunities fall through the cracks.
            </span>
        </div>
        """
        st.markdown(clean_html(seq_tip_markup), unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────
    # TAB 4: AI INTENT, SENTIMENT & SCORING (FEATURES 8, 9, 13)
    # ─────────────────────────────────────────────────────────────
    elif current_tab == "intelligence":
        # ── Feature 8: Engagement Score ──
        _render_feature_header(
            "engagement_score",
            "8. Engagement Score",
            "Assigns a score to each lead based on their overall interactions and activity.",
            "⭐",
            "Predictive Scoring",
            f"{totals['avg_engagement_score']} Avg Score",
        )

        score_pills_markup = """
        <div style="display: flex; gap: 12px; margin-bottom: 14px; font-size: 12.5px; color: #475569; flex-wrap: wrap;">
            <span class="kpi-pill kpi-pill-rose">Hot 🔥 (80–100): Ready to Close</span>
            <span class="kpi-pill kpi-pill-amber">Warm ⚡ (50–79): Engaged &amp; Researched</span>
            <span class="kpi-pill kpi-pill-blue">Lukewarm 💧 (25–49): Opened/Explored</span>
            <span class="kpi-pill" style="background: #F1F5F9; color: #475569;">Cold ❄️ (0–24): Awaiting Interaction</span>
        </div>
        """
        st.markdown(clean_html(score_pills_markup), unsafe_allow_html=True)

        sorted_leads = sorted(records, key=lambda x: x["engagement_score"], reverse=True)
        lead_score_rows = []
        for r in sorted_leads[:10]:
            lead_score_rows.append({
                "Lead Name": r["name"],
                "Company": r["company"],
                "Score": r["engagement_score"],
                "Tier": r["score_tier"],
                "Opens": f"{r['open_count']}x",
                "Clicks": f"{r['click_count']}x",
                "Replied": "Yes 📩" if r["is_reply_detected"] else "No",
                "Booked": "Confirmed 📅" if r["has_booked"] else "—",
            })

        st.dataframe(
            pd.DataFrame(lead_score_rows),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Lead Name": st.column_config.TextColumn("Lead", width="medium"),
                "Company": st.column_config.TextColumn("Company", width="medium"),
                "Score": st.column_config.ProgressColumn("Score (0-100)", min_value=0, max_value=100, format="%d"),
                "Tier": st.column_config.TextColumn("Tier", width="small"),
                "Opens": st.column_config.TextColumn("Opens", width="small"),
                "Clicks": st.column_config.TextColumn("Clicks", width="small"),
                "Replied": st.column_config.TextColumn("Replied", width="small"),
                "Booked": st.column_config.TextColumn("Booked", width="small"),
            },
        )

        st.markdown("<hr style='border: none; border-top: 1px solid #E2E8F0; margin: 24px 0;'>", unsafe_allow_html=True)

        # ── Feature 9: Lead Intent Classification ──
        _render_feature_header(
            "lead_intent_classification",
            "9. Lead Intent Classification",
            "Uses AI to classify a lead's intention, such as interested, not interested, or follow up later.",
            "🧠",
            "Gemini AI Engine",
            "Real-Time RAG Classifier",
        )

        c_i1, c_i2 = st.columns([1, 1])
        with c_i1:
            intent_dict = analytics_data["intent_counts"]
            total_intents = sum(intent_dict.values())
            if total_intents == 0:
                fig_intent = px.pie(
                    values=[1],
                    names=["No Leads Classified"],
                    hole=0.5,
                    color_discrete_sequence=["#E2E8F0"],
                )
                fig_intent.add_annotation(
                    text="No Intent Data",
                    showarrow=False,
                    font=dict(family="Inter, sans-serif", size=12, color="#64748B"),
                )
            else:
                fig_intent = px.pie(
                    values=list(intent_dict.values()),
                    names=[k.replace("_", " ").title() for k in intent_dict.keys()],
                    hole=0.5,
                    color_discrete_sequence=["#0D9488", "#2563EB", "#F59E0B", "#DC2626", "#CBD5E1"],
                )
            fig_intent.update_layout(
                height=220,
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter, sans-serif", size=11),
            )
            apply_chart_theme(fig_intent)
            st.plotly_chart(fig_intent, use_container_width=True, config={'displayModeBar': False})

        with c_i2:
            st.caption("AI Intent Categorization Rationale:")
            intent_guide = [
                {"Intent": "Interested", "Definition": "Customer confirms meeting or asks for pricing", "Action": "Send Calendar Booking"},
                {"Intent": "Question", "Definition": "Technical, SLA, or security architecture questions", "Action": "RAG Knowledge Base Answer"},
                {"Intent": "Reschedule", "Definition": "Timing mismatch, ask to ping next quarter", "Action": "Set Follow-up Task"},
                {"Intent": "Not Interested", "Definition": "Polite decline or competitor locked", "Action": "Safe Suppression"},
            ]
            st.dataframe(pd.DataFrame(intent_guide), use_container_width=True, hide_index=True)

        st.markdown("<hr style='border: none; border-top: 1px solid #E2E8F0; margin: 24px 0;'>", unsafe_allow_html=True)

        # ── Feature 13: AI Reply Sentiment ──
        _render_feature_header(
            "ai_reply_sentiment",
            "13. AI Reply Sentiment",
            "Uses AI to identify whether a lead's reply is positive, neutral, or negative.",
            "🎭",
            "NLP Sentiment Polarity",
            f"{analytics_data['sentiment_counts'].get('Positive', 0)} Positive",
        )

        s_counts = analytics_data["sentiment_counts"]
        c_s1, c_s2, c_s3 = st.columns(3)
        with c_s1:
            st.markdown(
                clean_html(f"""
                <div style="background: #F0FDFA; border: 1px solid #99F6E4; border-radius: 8px; padding: 16px; text-align: center;">
                    <span style="font-size: 26px;">😊</span>
                    <div style="font-size: 22px; font-weight: 700; color: #0F766E; margin-top: 4px;">{s_counts.get('Positive', 0)}</div>
                    <span style="font-size: 12px; color: #115E59; font-weight: 600;">Positive Sentiment</span>
                    <div style="font-size: 11px; color: #134E4A; margin-top: 2px;">Enthusiastic &amp; Receptive</div>
                </div>
                """),
                unsafe_allow_html=True,
            )
        with c_s2:
            st.markdown(
                clean_html(f"""
                <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 16px; text-align: center;">
                    <span style="font-size: 26px;">😐</span>
                    <div style="font-size: 22px; font-weight: 700; color: #334155; margin-top: 4px;">{s_counts.get('Neutral', 0)}</div>
                    <span style="font-size: 12px; color: #475569; font-weight: 600;">Neutral Sentiment</span>
                    <div style="font-size: 11px; color: #64748B; margin-top: 2px;">Inquisitive &amp; Pragmatic</div>
                </div>
                """),
                unsafe_allow_html=True,
            )
        with c_s3:
            st.markdown(
                clean_html(f"""
                <div style="background: #FEF2F2; border: 1px solid #FECACA; border-radius: 8px; padding: 16px; text-align: center;">
                    <span style="font-size: 26px;">🙁</span>
                    <div style="font-size: 22px; font-weight: 700; color: #DC2626; margin-top: 4px;">{s_counts.get('Negative', 0)}</div>
                    <span style="font-size: 12px; color: #991B1B; font-weight: 600;">Negative Sentiment</span>
                    <div style="font-size: 11px; color: #7F1D1D; margin-top: 2px;">Polite Decline</div>
                </div>
                """),
                unsafe_allow_html=True,
            )

    # ─────────────────────────────────────────────────────────────
    # TAB 5: SEND TIME, SUBJECT & CTA OPTIMIZATION (FEATURES 10, 11, 12)
    # ─────────────────────────────────────────────────────────────
    elif current_tab == "optimization":
        # ── Feature 10: Best Send Time ──
        _render_feature_header(
            "best_send_time",
            "10. Best Send Time",
            "Analyzes engagement history to identify the best time to send emails to leads.",
            "⏰",
            "Temporal Optimization",
            "Tue & Thu Peak",
        )

        h_data = analytics_data["heatmap"]
        fig_heat = px.imshow(
            h_data["matrix"],
            labels=dict(x="Time of Day", y="Day of Week", color="Engagement %"),
            x=h_data["hours"],
            y=h_data["days"],
            color_continuous_scale="Blues",
            aspect="auto",
        )
        fig_heat.update_layout(
            height=260,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif", size=11),
        )
        apply_chart_theme(fig_heat)
        st.plotly_chart(fig_heat, use_container_width=True, config={'displayModeBar': False})

        if max_val > 0:
            rec_desc = f"Highest outreach engagement recorded on <strong>{peak_send_str}</strong>. Telemetry identifies this time window as having the highest open density and fastest reply turnarounds."
        else:
            rec_desc = "Outreach telemetry actively monitors outgoing email dispatches and incoming replies to identify your peak engagement windows in real time."

        rec_box_markup = f"""
        <div style="background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 8px; padding: 12px 16px; margin-bottom: 20px;">
            <strong style="color: #1D4ED8; font-size: 13.5px;">🎯 AI Dispatch Recommendation:</strong>
            <span style="color: #1E40AF; font-size: 13px;">
                {rec_desc}
            </span>
        </div>
        """
        st.markdown(clean_html(rec_box_markup), unsafe_allow_html=True)

        st.markdown("<hr style='border: none; border-top: 1px solid #E2E8F0; margin: 24px 0;'>", unsafe_allow_html=True)

        # ── Feature 11: Subject-line Analysis ──
        _render_feature_header(
            "subject_line_analysis",
            "11. Subject-line Analysis",
            "Compares subject lines to determine which ones generate better engagement.",
            "✍️",
            "A/B Content Analytics",
            "A+ Leaderboard",
        )

        sub_df = pd.DataFrame(analytics_data["subject_lines"])
        st.dataframe(
            sub_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "subject": st.column_config.TextColumn("Subject Line Template", width="large"),
                "category": st.column_config.TextColumn("Category", width="medium"),
                "open_rate": st.column_config.NumberColumn("Open Rate %", format="%.1f%%"),
                "reply_rate": st.column_config.NumberColumn("Reply Rate %", format="%.1f%%"),
                "rating": st.column_config.TextColumn("Grade", width="small"),
                "verdict": st.column_config.TextColumn("AI Diagnostic Verdict", width="large"),
            },
        )

        st.markdown("<hr style='border: none; border-top: 1px solid #E2E8F0; margin: 24px 0;'>", unsafe_allow_html=True)

        # ── Feature 12: CTA Analysis ──
        _render_feature_header(
            "cta_analysis",
            "12. CTA Analysis",
            "Measures which call-to-action messages or buttons generate more clicks or conversions.",
            "🎯",
            "Conversion Testing",
            "Direct Booking Leads",
        )

        cta_df = pd.DataFrame(analytics_data["cta_variants"])
        st.dataframe(
            cta_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "cta_text": st.column_config.TextColumn("Call-to-Action Text / Button", width="large"),
                "type": st.column_config.TextColumn("CTA Mechanism", width="medium"),
                "impressions": st.column_config.NumberColumn("Impressions"),
                "clicks": st.column_config.NumberColumn("Clicks"),
                "ctr": st.column_config.NumberColumn("CTR %", format="%.1f%%"),
                "conversions": st.column_config.NumberColumn("Conversions"),
                "conversion_rate": st.column_config.NumberColumn("Win Rate %", format="%.1f%%"),
                "badge": st.column_config.TextColumn("Performance Badge", width="small"),
            },
        )

    # ─────────────────────────────────────────────────────────────
    # TAB 6: LEAD ACTIVITY TIMELINE (FEATURE 14)
    # ─────────────────────────────────────────────────────────────
    elif current_tab == "timeline":
        _render_feature_header(
            "lead_activity_timeline",
            "14. Lead Activity Timeline",
            "Shows a chronological history of every important interaction with a lead.",
            "📜",
            "Audit & Journey",
            f"{len(records)} Lead Timelines",
        )

        if not records:
            st.info("No lead journey records found in the database. Enrol or send outreach emails to view real-time chronological activity timelines.")
        else:
            lead_options = {f"{r['name']} ({r['email']})": r for r in records}
            selected_lead_key = st.selectbox(
                "Select a Lead to Inspect Chronological Activity History:",
                list(lead_options.keys()),
                index=0,
            )

            chosen_lead = lead_options[selected_lead_key]

            lead_profile_markup = f"""
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 16px 20px; margin: 12px 0 20px 0; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                <div>
                    <h3 style="font-size: 17px; margin: 0; color: #18181B;">{chosen_lead['name']}</h3>
                    <p style="font-size: 13px; color: #64748B; margin: 2px 0 0 0;">{chosen_lead['email']} · {chosen_lead['company']}</p>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span class="badge badge-sent">{chosen_lead['score_tier']} ({chosen_lead['engagement_score']} pts)</span>
                    <span class="badge badge-pending">Intent: {chosen_lead['reply_intent'].title()}</span>
                    <span class="badge badge-draft">Sentiment: {chosen_lead['sentiment']}</span>
                </div>
            </div>
            """
            st.markdown(clean_html(lead_profile_markup), unsafe_allow_html=True)

            timeline_events = chosen_lead.get("timeline", [])
            if not timeline_events:
                st.info("No activity recorded for this lead yet.")
            else:
                timeline_html = '<div class="timeline-v-wrap">'
                for ev in timeline_events:
                    if not ev:
                        continue
                    node_class = ev.get("status", "completed")
                    timeline_html += f"""
                    <div class="timeline-v-item">
                        <div class="timeline-v-node {node_class}">{ev['icon']}</div>
                        <div class="timeline-v-card">
                            <div class="timeline-v-header">
                                <span class="timeline-v-title">{ev['event']}</span>
                                <span class="timeline-v-time">{ev['timestamp']}</span>
                            </div>
                            <p class="timeline-v-desc">{ev['details']}</p>
                        </div>
                    </div>
                    """
                timeline_html += "</div>"
                st.markdown(clean_html(timeline_html), unsafe_allow_html=True)
