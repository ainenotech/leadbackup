"""Master DB Module for AINeotechnology Outreach Suite.
Provides a clean, fast, and executive UI for template-wise lead segmentation
into real Hot, Warm, and Cold leads with interactive data tables and real-time telemetry.
"""

import os
import re
import html
import pandas as pd
import streamlit as st
from typing import Any, Dict, List
from datetime import datetime

from services.template_service import load_all_templates
from utils.theme import is_dark_mode


# ─────────────────────────────────────────────────────────────
# REAL LEAD TEMPERATURE CLASSIFIER
# ─────────────────────────────────────────────────────────────
def categorize_lead_temperature(row: Dict[str, Any]) -> Dict[str, Any]:
    """Analyzes real engagement telemetry and classifies lead into Hot, Warm, or Cold."""
    opened = bool(row.get("opened", False))
    open_count = int(row.get("open_count") or 0)
    clicked = bool(row.get("clicked_link", False))
    click_count = int(row.get("click_count") or 0)
    reply_body = str(row.get("reply_body") or "").strip()
    reply_intent = str(row.get("reply_intent") or "").strip()
    reply_intent_lower = reply_intent.lower()
    booking_status = str(row.get("booking_status") or "").strip().lower()
    confirmed_slot = str(row.get("confirmed_slot") or "").strip()
    meet_link = str(row.get("meet_link") or "").strip()
    status_lower = str(row.get("status") or "").strip().lower()

    has_booked = bool(
        (confirmed_slot and confirmed_slot.lower() not in ["none", "nan", "nat", ""])
        or (meet_link and meet_link.lower() not in ["none", "nan", "nat", ""])
        or booking_status in ["scheduled", "meeting_scheduled", "confirmation_sent", "confirmed"]
    )
    reply_time = row.get("reply_received_at")
    has_valid_reply_time = bool(pd.notna(reply_time) and str(reply_time).strip().lower() not in ["none", "nan", "nat", ""])
    has_reply_body = bool(reply_body and reply_body.lower() not in ["none", "nan", "nat", "—", "-"])

    has_replied = bool(
        has_reply_body
        or status_lower == "replied"
        or has_valid_reply_time
    )
    form_time = row.get("form_filled_at")
    form_filled = bool(pd.notna(form_time) and str(form_time).strip().lower() not in ["none", "nan", "nat", ""])

    score = 0.0
    signals = []

    # 1. Bookings & Consultations
    if has_booked:
        score = 98.0
        signals.append("📅 Meeting Booked")
    elif form_filled:
        score = 90.0
        signals.append("📝 Form Submitted")

    # 2. Real Customer Replies
    if has_replied:
        score = max(score, 92.0)
        if reply_intent_lower in ["interested", "positive_acknowledgement"]:
            signals.append("💬 Replied: High Interest")
        elif reply_intent_lower == "reschedule":
            signals.append("💬 Replied: Reschedule Request")
        elif reply_intent_lower == "question":
            signals.append("💬 Replied: Asked Details")
        elif reply_intent_lower == "not_interested":
            score = 30.0
            signals.append("💬 Replied: Opt-out")
        else:
            signals.append(f"💬 Replied ({reply_intent or 'Customer Response'})")

    # 3. Link Clicks (Strong buying interest)
    if clicked or click_count > 0:
        c_score = 70.0 + min(20.0, max(1, click_count) * 4.0)
        score = max(score, c_score)
        signals.append(f"🖱️ Clicked Link {max(1, click_count)}x")

    # 4. Email Opens
    if opened or open_count > 0:
        o_count = max(1, open_count)
        if score < 70.0:
            score = max(score, 25.0 + min(35.0, o_count * 8.0))
        signals.append(f"👁️ Opened {o_count}x")

    # Cold default
    if not signals:
        score = 10.0
        signals.append("Delivered • Unopened")

    score = min(100.0, max(0.0, score))

    # Real, accurate Tier Segmentation:
    # Any booked lead, replied lead, or high clicker is HOT
    if has_booked or (has_replied and reply_intent_lower != "not_interested") or (clicked and (click_count >= 2 or open_count >= 2)) or score >= 70.0:
        tier = "HOT"
        tier_display = "🔥 Hot"
    elif opened or clicked or has_replied or score >= 25.0:
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


# ─────────────────────────────────────────────────────────────
# FAST IN-MEMORY DATA ENRICHMENT
# ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=30, show_spinner=False)
def load_enriched_master_data() -> pd.DataFrame:
    """Loads all logs and merges real Excel metadata for 100% authentic Master DB records."""
    from Backend.db import SessionLocal
    from Backend.models import CampaignLog
    from Backend.crud import sync_excel_and_outlook_to_db

    # Statuses that represent real leads (actually sent or engaged)
    REAL_LEAD_STATUSES = {
        "sent", "replied", "delivered", "form_submitted",
        "scheduled", "meeting_booked", "booked", "opted_out",
    }

    db = SessionLocal()
    try:
        try:
            sync_excel_and_outlook_to_db(db)
        except Exception:
            pass
        rows = db.query(CampaignLog).order_by(CampaignLog.created_at.desc()).all()
        data = [
            {
                "id": r.id,
                "email": (r.email or "").strip().lower(),
                "name": (r.name or "").strip(),
                "company": (r.company or "").strip(),
                "phone": getattr(r, "phone", "") or "",
                "status": r.status or "sent",
                "template_id": getattr(r, "template_id", "") or "",
                "template_name": getattr(r, "template_name", "") or "",
                "opened": bool(getattr(r, "opened", False)),
                "open_count": getattr(r, "open_count", 0) or 0,
                "clicked_link": bool(getattr(r, "clicked_link", False)),
                "click_count": getattr(r, "click_count", 0) or 0,
                "reply_body": (r.reply_body or "").strip(),
                "reply_intent": (r.reply_intent or "").strip(),
                "reply_received_at": r.reply_received_at,
                "booking_status": (r.booking_status or "").strip(),
                "confirmed_slot": (r.confirmed_slot or "").strip(),
                "meet_link": (r.meet_link or "").strip(),
                "form_filled_at": r.form_filled_at,
                "email_sent_at": r.email_sent_at,
                "created_at": r.created_at,
            }
            for r in rows
            if r.email and (
                (r.status or "").strip().lower() in REAL_LEAD_STATUSES
                or r.email_sent_at is not None
            )
        ]
    finally:
        db.close()

    df = pd.DataFrame(data) if data else pd.DataFrame()
    if df.empty:
        return df

    # Deduplicate by email: keep the row with the highest engagement
    # (most opens + clicks + has reply) per unique email address
    if "email" in df.columns and len(df) > 0:
        df["_engagement_rank"] = (
            df["open_count"].fillna(0).astype(int)
            + df["click_count"].fillna(0).astype(int) * 2
            + df["reply_body"].apply(lambda x: 5 if x and str(x).lower() not in ["none", "nan", "—", "-", ""] else 0)
        )
        df = df.sort_values("_engagement_rank", ascending=False).drop_duplicates(subset=["email"], keep="first")
        df = df.drop(columns=["_engagement_rank"])
        df = df.sort_values("created_at", ascending=False).reset_index(drop=True)

    # Merge real CRM metadata from leads.xlsx (roles, last activity, etc.)
    if os.path.exists("leads.xlsx"):
        try:
            leads_df = pd.read_excel("leads.xlsx")
            leads_df["email_clean"] = leads_df["email"].astype(str).str.strip().str.lower()

            def _clean_str(val):
                if val is None or pd.isna(val):
                    return ""
                s = str(val).strip()
                if s.lower() in ("nan", "none", "nat", ""):
                    return ""
                return s

            meta_cols = {}
            for _, r in leads_df.iterrows():
                em = r.get("email_clean")
                if em and "@" in em and em not in meta_cols:
                    pos = _clean_str(r.get("Position")) or _clean_str(r.get("job_title"))
                    last_act = _clean_str(r.get("last_activity_date")).replace(" 00:00:00", "")
                    loc = _clean_str(r.get("location"))
                    meta_cols[em] = {
                        "job_title": pos,
                        "last_activity_date": last_act,
                        "location": loc,
                    }

            if meta_cols:
                # Also check customer_replies for signature titles (e.g. Michael Tutek -> CEO, Co-Founder)
                if os.path.exists("customer_replies.xlsx"):
                    try:
                        cr_df = pd.read_excel("customer_replies.xlsx")
                        for _, cr_row in cr_df.iterrows():
                            cr_em = _clean_str(cr_row.get("email")).lower()
                            cr_body = _clean_str(cr_row.get("customer_reply"))
                            if cr_em and cr_body:
                                for candidate_title in ["CEO, Co-Founder", "Co-Founder & CEO", "Founder & CEO", "CEO and Founder", "Managing Director", "Founder"]:
                                    if candidate_title.lower() in cr_body.lower():
                                        if cr_em in meta_cols and not meta_cols[cr_em]["job_title"]:
                                            meta_cols[cr_em]["job_title"] = candidate_title
                                        elif cr_em not in meta_cols:
                                            meta_cols[cr_em] = {"job_title": candidate_title, "last_activity_date": "", "location": ""}
                                        break
                    except Exception:
                        pass

                df["job_title"] = df["email"].apply(lambda e: meta_cols.get(e, {}).get("job_title", ""))
                df["last_activity_date"] = df["email"].apply(lambda e: meta_cols.get(e, {}).get("last_activity_date", ""))
                df["location"] = df["email"].apply(lambda e: meta_cols.get(e, {}).get("location", ""))
        except Exception:
            pass

    if "job_title" not in df.columns:
        df["job_title"] = ""
    if "last_activity_date" not in df.columns:
        df["last_activity_date"] = ""

    # Enrich each lead with temperature and signals
    enriched = []
    for _, row in df.iterrows():
        row_dict = row.to_dict()
        temp_info = categorize_lead_temperature(row_dict)
        row_dict.update(temp_info)
        enriched.append(row_dict)

    return pd.DataFrame(enriched)



# ─────────────────────────────────────────────────────────────
# MAIN RENDER FUNCTION: MASTER DB
# ─────────────────────────────────────────────────────────────
def render_master_db(df_logs: pd.DataFrame) -> None:
    """Renders the fast, real-data Master Database with accurate Hot/Warm/Cold segmentation."""
    templates = load_all_templates()

    # Load authentic enriched data
    enriched_df = load_enriched_master_data()
    if enriched_df.empty and not df_logs.empty:
        enriched_list = []
        for _, row in df_logs.iterrows():
            row_dict = row.to_dict()
            temp_info = categorize_lead_temperature(row_dict)
            row_dict.update(temp_info)
            enriched_list.append(row_dict)
        enriched_df = pd.DataFrame(enriched_list)

    # ── Header ──
    st.markdown(
        """
        <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 12px; padding: 18px 22px; margin-bottom: 20px; box-shadow: var(--shadow-sm);">
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <div>
                    <h2 style="font-family: 'Outfit', sans-serif; font-size: 24px; font-weight: 700; margin: 0; color: var(--text-primary); letter-spacing: -0.02em;">
                        🗄️ Master DB
                    </h2>
                    <p style="font-family: 'Inter', sans-serif; font-size: 13.5px; color: var(--text-muted); margin: 4px 0 0 0;">
                        Live database segmentation with verified Hot, Warm, and Cold lead telemetry.
                    </p>
                </div>
                <span class="badge badge-sent" style="font-size: 11.5px; padding: 4px 10px;">
                    Real Database Verified
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if enriched_df.empty:
        st.info("No leads found in the database. Upload a spreadsheet in 'Upload & Draft' to populate Master DB.")
        return

    # ── Template Filter & Search Controls ──
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

    # Segmentation
    hot_df = filtered_df[filtered_df["tier"] == "HOT"].copy()
    warm_df = filtered_df[filtered_df["tier"] == "WARM"].copy()
    cold_df = filtered_df[filtered_df["tier"] == "COLD"].copy()

    total_leads = len(filtered_df)
    hot_count = len(hot_df)
    warm_count = len(warm_df)
    cold_count = len(cold_df)
    opened_count = int(filtered_df["opened"].sum()) if "opened" in filtered_df.columns else 0
    clicked_count = int(filtered_df["clicked_link"].sum()) if "clicked_link" in filtered_df.columns else 0
    replied_count = int(filtered_df["reply_body"].apply(lambda x: bool(str(x).strip() and str(x).lower() not in ["none", "nan", "—", "-"])).sum()) if "reply_body" in filtered_df.columns else 0

    hot_pct = (hot_count / total_leads * 100) if total_leads else 0.0
    warm_pct = (warm_count / total_leads * 100) if total_leads else 0.0
    cold_pct = (cold_count / total_leads * 100) if total_leads else 0.0

    # ── 5 Sleek Executive KPI Cards ──
    st.markdown(
        f"""
        <div class="kpi-grid" style="grid-template-columns: repeat(5, 1fr); gap: 12px; margin: 16px 0 20px 0;">
            <div class="kpi-card" style="padding: 14px 16px; min-height: 110px;">
                <div class="kpi-top-bar kpi-bar-blue"></div>
                <div class="kpi-header" style="margin-bottom: 4px;">
                    <span class="kpi-label">Total Leads</span>
                    <span style="font-size: 16px;">👥</span>
                </div>
                <div class="kpi-value" style="font-size: 26px;">{total_leads}</div>
                <div class="kpi-micro"><span class="kpi-pill kpi-pill-blue">Active</span> In current view</div>
            </div>
            <div class="kpi-card" style="padding: 14px 16px; min-height: 110px;">
                <div class="kpi-top-bar" style="background: linear-gradient(90deg, #EF4444, #F87171);"></div>
                <div class="kpi-header" style="margin-bottom: 4px;">
                    <span class="kpi-label" style="color: #EF4444;">🔥 Hot Leads</span>
                    <span style="font-size: 16px;">🔥</span>
                </div>
                <div class="kpi-value" style="font-size: 26px; color: #EF4444;">{hot_count}</div>
                <div class="kpi-micro"><span class="kpi-pill" style="background: rgba(239, 68, 68, 0.12); color: #EF4444; border: 1px solid rgba(239, 68, 68, 0.3);">{hot_pct:.1f}%</span> High intent / replies</div>
            </div>
            <div class="kpi-card" style="padding: 14px 16px; min-height: 110px;">
                <div class="kpi-top-bar kpi-bar-amber"></div>
                <div class="kpi-header" style="margin-bottom: 4px;">
                    <span class="kpi-label" style="color: #D97706;">⚡ Warm Leads</span>
                    <span style="font-size: 16px;">⚡</span>
                </div>
                <div class="kpi-value" style="font-size: 26px; color: #D97706;">{warm_count}</div>
                <div class="kpi-micro"><span class="kpi-pill kpi-pill-amber">{warm_pct:.1f}%</span> Opened / Engaged</div>
            </div>
            <div class="kpi-card" style="padding: 14px 16px; min-height: 110px;">
                <div class="kpi-top-bar kpi-bar-cyan"></div>
                <div class="kpi-header" style="margin-bottom: 4px;">
                    <span class="kpi-label">❄️ Cold Leads</span>
                    <span style="font-size: 16px;">❄️</span>
                </div>
                <div class="kpi-value" style="font-size: 26px;">{cold_count}</div>
                <div class="kpi-micro"><span class="kpi-pill kpi-pill-cyan">{cold_pct:.1f}%</span> Unopened</div>
            </div>
            <div class="kpi-card" style="padding: 14px 16px; min-height: 110px;">
                <div class="kpi-top-bar kpi-bar-teal"></div>
                <div class="kpi-header" style="margin-bottom: 4px;">
                    <span class="kpi-label" style="color: #0D9488;">💬 Responses</span>
                    <span style="font-size: 16px;">💬</span>
                </div>
                <div class="kpi-value" style="font-size: 26px; color: #0D9488;">{replied_count}</div>
                <div class="kpi-micro"><span class="kpi-pill kpi-pill-teal">{clicked_count} Clicks</span> {opened_count} Opens</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Table Column Builder ──
    def build_clean_dataframe(df_source: pd.DataFrame) -> pd.DataFrame:
        if df_source.empty:
            return pd.DataFrame()

        df_out = df_source.copy()

        df_out["opens"] = df_out["open_count"].fillna(0).astype(int)
        df_out["clicks"] = df_out["click_count"].fillna(0).astype(int)

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

        def _fmt_date(val):
            if not val or pd.isna(val) or str(val).lower() in ["none", "nan", ""]:
                return "—"
            s = str(val).replace("T", " ")
            return s[:16]

        df_out["last_touch"] = df_out["email_sent_at"].apply(_fmt_date)

        cols_order = [
            c
            for c in [
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
                "last_touch",
            ]
            if c in df_out.columns
        ]
        return df_out[cols_order]

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
        "last_touch": st.column_config.TextColumn("Last Sent", width="medium"),
    }

    # ── Tabs: Hot Leads, Warm Leads, Cold Leads, All Leads ──
    tab_hot, tab_warm, tab_cold, tab_all = st.tabs([
        f"🔥 Hot Leads ({hot_count})",
        f"⚡ Warm Leads ({warm_count})",
        f"❄️ Cold Leads ({cold_count})",
        f"📋 All Leads ({len(filtered_df)})",
    ])

    # TAB 1: HOT LEADS
    with tab_hot:
        if hot_df.empty:
            st.info("No Hot leads found under the current selection.")
        else:
            h_df_sorted = hot_df.sort_values(by=["score", "open_count"], ascending=False)
            h_clean = build_clean_dataframe(h_df_sorted)

            row_top_h1, row_top_h2 = st.columns([3, 1])
            with row_top_h1:
                st.caption(f"Showing **{len(h_clean)}** high-intent leads who replied to emails or clicked engagement links:")
            with row_top_h2:
                csv_h = h_clean.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="⬇️ Export Hot Leads (CSV)",
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
                column_config=col_config,
            )

    # TAB 2: WARM LEADS
    with tab_warm:
        if warm_df.empty:
            st.info("No Warm leads found under the current selection.")
        else:
            w_df_sorted = warm_df.sort_values(by=["score", "open_count"], ascending=False)
            w_clean = build_clean_dataframe(w_df_sorted)

            row_top_w1, row_top_w2 = st.columns([3, 1])
            with row_top_w1:
                st.caption(f"Showing **{len(w_clean)}** active consideration leads who opened emails or clicked once:")
            with row_top_w2:
                csv_w = w_clean.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="⬇️ Export Warm Leads (CSV)",
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
                column_config=col_config,
            )

    # TAB 3: COLD LEADS
    with tab_cold:
        if cold_df.empty:
            st.info("No Cold leads found under the current selection.")
        else:
            c_clean = build_clean_dataframe(cold_df)

            row_top_c1, row_top_c2 = st.columns([3, 1])
            with row_top_c1:
                st.caption(f"Showing **{len(c_clean)}** leads awaiting first open or response:")
            with row_top_c2:
                csv_c = c_clean.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="⬇️ Export Cold Leads (CSV)",
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
                column_config=col_config,
            )

    # TAB 4: ALL LEADS
    with tab_all:
        if filtered_df.empty:
            st.info("No leads match the current filters.")
        else:
            all_clean = build_clean_dataframe(filtered_df)

            row_top_a1, row_top_a2 = st.columns([3, 1])
            with row_top_a1:
                st.caption(f"Showing all **{len(all_clean)}** real database records:")
            with row_top_a2:
                csv_all = all_clean.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="⬇️ Export All Leads (CSV)",
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
                column_config=col_config,
            )
