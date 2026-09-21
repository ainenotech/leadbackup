import html
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from services.template_service import (
    load_all_templates,
    get_template_by_id,
    save_custom_template,
    render_template,
    compute_template_analytics,
)
from Backend.db import SessionLocal
from Backend.crud import create_pending_entry
from utils.token import generate_token


def render_template_hub(df_logs: pd.DataFrame) -> None:
    """Renders the comprehensive Template Review & Hub page."""
    templates = load_all_templates()
    stats = compute_template_analytics(df_logs)

    # Top Executive Banner
    st.markdown(
        """
        <div class="top-header-banner" style="margin-bottom: 20px;">
            <div>
                <h1 class="top-header-title">
                    📑 Email Template Review &amp; A/B Performance Hub
                    <span class="badge badge-pending" style="font-size: 11px; font-weight: 600;">10–15 Template Ready</span>
                </h1>
                <p class="top-header-desc">
                    Review and preview your responsive HTML email templates, pair 20–25 lead sheets with designated templates, and analyze daily open, click, and booking rates.
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_gallery, tab_analytics, tab_batch = st.tabs([
        f"👁️ Template Gallery & Live Inspector ({len(templates)})",
        "📈 Template-Wise Analytics & Daily Trends",
        "📤 Sheet-to-Template Batch Outreach (20–25 Leads)",
    ])

    # ═══════════════════════════════════════════════════════════════
    # TAB 1: TEMPLATE GALLERY & LIVE INSPECTOR
    # ═══════════════════════════════════════════════════════════════
    with tab_gallery:
        col_left, col_right = st.columns([1.1, 1.9], gap="large")

        with col_left:
            st.markdown("### 🎨 Select & Configure Template")
            
            tpl_options = {t["id"]: f"{t['name']}" for t in templates}
            selected_id = st.selectbox(
                "Choose Template to Review",
                options=list(tpl_options.keys()),
                format_func=lambda tid: tpl_options[tid],
                key="gallery_tpl_select",
            )
            current_tpl = get_template_by_id(selected_id) or templates[0]

            # Template Details Card
            badge_html = f'<span class="badge badge-info" style="font-size: 11px;">{current_tpl.get("badge", "Active")}</span>' if current_tpl.get("badge") else ""
            st.markdown(
                f"""
                <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 16px; margin: 12px 0;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <strong style="color: #0F172A; font-size: 15px;">{current_tpl['name']}</strong>
                        {badge_html}
                    </div>
                    <div style="font-size: 12px; color: #64748B; margin-bottom: 6px;">
                        <strong>Category:</strong> {current_tpl.get('category', 'Outreach')}
                    </div>
                    <div style="font-size: 13px; color: #334155; line-height: 1.5;">
                        {current_tpl.get('description', 'High-converting responsive HTML email template.')}
                    </div>
                    <div style="margin-top: 10px; padding: 8px 10px; background: #FFFFFF; border: 1px dashed #CBD5E1; border-radius: 6px; font-size: 12px; color: #475569;">
                        <strong>Subject Pattern:</strong><br>
                        <code>{current_tpl.get('subject', '')}</code>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Add Custom Template Expander
            with st.expander("➕ Add New Custom Template (Expand to 10-15+)", expanded=False):
                with st.form("form_add_custom_template"):
                    st.markdown("##### Create a Custom Outreach Template")
                    new_id = st.text_input("Template Unique ID", value=f"tpl_custom_{uuid.uuid4().hex[:6]}")
                    new_name = st.text_input("Template Name", placeholder="e.g. Template 8: Short Founder Video Intro")
                    new_cat = st.selectbox("Category", ["Executive & Founder", "Technical & Architecture", "Case Study & Results", "Quick Check-in", "Custom"])
                    new_subj = st.text_input("Subject Line Pattern", value="Quick question for {{Company}}")
                    new_desc = st.text_area("Description / Use Case", value="Custom tailored outreach template for specialized lead batches.")
                    new_html = st.text_area("HTML Email Template Code", height=250, placeholder="Paste inline-styled HTML code here...")
                    
                    submitted = st.form_submit_button("💾 Save Template to Library", type="primary")
                    if submitted:
                        if new_id and new_name and new_html:
                            saved = save_custom_template({
                                "id": new_id.strip(),
                                "name": new_name.strip(),
                                "subject": new_subj.strip(),
                                "category": new_cat,
                                "description": new_desc.strip(),
                                "html_content": new_html.strip(),
                                "badge": "Custom Added",
                                "accent_color": "#2563EB",
                            })
                            if saved:
                                st.success(f"Template '{new_name}' successfully added to your library!")
                                st.rerun()
                            else:
                                st.error("Could not save template to disk.")
                        else:
                            st.warning("Please fill in Template ID, Name, and HTML content.")

        with col_right:
            # Render Interpolated HTML
            booking_url = os.getenv(
                "BOOKING_FORM_URL",
                "https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled",
            )
            interp_subject, interp_html = render_template(
                selected_id,
                lead_name="there",
                company="Your Company",
                pain_point="manual operational overhead",
                booking_url=booking_url,
            )

            st.markdown(
                f"""
                <div style="background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 8px; padding: 12px 16px; margin-bottom: 12px;">
                    <div style="font-size: 11px; text-transform: uppercase; font-weight: 700; color: #64748B; letter-spacing: 0.05em;">Subject Preview</div>
                    <div style="font-size: 16px; font-weight: 600; color: #0F172A; margin-top: 2px;">{html.escape(interp_subject)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Frame simulation wrapper (Standard Desktop Card 620px)
            st.markdown(
                """
                <div style="display: flex; justify-content: center; background: #F1F5F9; border-radius: 12px; padding: 16px; border: 1px solid #E2E8F0;">
                    <div style="width: 620px; max-width: 100%; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1); border-radius: 12px; overflow: hidden; background: #FFFFFF;">
                """,
                unsafe_allow_html=True,
            )
            components.html(interp_html, height=750, scrolling=True)
            st.markdown("</div></div>", unsafe_allow_html=True)

            with st.expander("📄 Inspect & Edit Raw Template HTML Code", expanded=False):
                st.markdown("<p style='font-size: 13px; color: #64748B; margin-bottom: 8px;'>Review and edit the HTML source code for this template below. Click <strong>Save Template Changes</strong> to apply and persist your edits.</p>", unsafe_allow_html=True)
                raw_code = current_tpl.get("html_content", interp_html)
                edited_html = st.text_area(
                    "HTML Template Source Code",
                    value=raw_code,
                    height=360,
                    key=f"edit_raw_html_{current_tpl['id']}",
                    help="Modify HTML structure, styling, or placeholders ({{FirstName}}, {{Company}}, {{Pain}}, LOGO_URL, BOOKING_LINK).",
                )
                btn_save_col1, btn_save_col2 = st.columns([1.5, 4])
                with btn_save_col1:
                    if st.button("💾 Save Template Changes", type="primary", key=f"btn_save_raw_{current_tpl['id']}"):
                        updated_tpl = dict(current_tpl)
                        updated_tpl["html_content"] = edited_html
                        save_custom_template(updated_tpl)
                        st.toast(f"✅ Template '{current_tpl['name']}' saved successfully!", icon="💾")
                        st.rerun()

    # ═══════════════════════════════════════════════════════════════
    # TAB 2: TEMPLATE-WISE ANALYTICS & DAILY TRENDS
    # ═══════════════════════════════════════════════════════════════
    with tab_analytics:
        st.markdown("### 📊 Performance Analytics by Email Template")
        st.markdown(
            "Track and analyze open rates, click rates, reply rates, and consultation booking rates across your different templates."
        )

        # 4 Trophy KPI Cards
        best_open = stats.get("best_open_rate")
        best_click = stats.get("best_click_rate")
        best_book = stats.get("best_booking_rate")

        kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
        with kpi_col1:
            val_open = f"{best_open['open_rate']}%" if best_open else "—"
            tpl_open = best_open['template_name'].split(':')[0] if best_open else "No sent emails yet"
            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-top-bar kpi-bar-blue"></div>
                    <div class="kpi-header"><span class="kpi-label">🏆 Top Open Rate</span><span style="font-size: 18px;">👁️</span></div>
                    <div class="kpi-value">{val_open}</div>
                    <div class="kpi-micro"><span class="kpi-pill kpi-pill-blue">Highest</span><span>{tpl_open}</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with kpi_col2:
            val_click = f"{best_click['click_rate']}%" if best_click else "—"
            tpl_click = best_click['template_name'].split(':')[0] if best_click else "No clicks yet"
            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-top-bar kpi-bar-teal"></div>
                    <div class="kpi-header"><span class="kpi-label">🏆 Top Click Rate</span><span style="font-size: 18px;">🖱️</span></div>
                    <div class="kpi-value">{val_click}</div>
                    <div class="kpi-micro"><span class="kpi-pill kpi-pill-teal">Highest</span><span>{tpl_click}</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with kpi_col3:
            val_book = f"{best_book['booking_rate']}%" if best_book else "—"
            tpl_book = best_book['template_name'].split(':')[0] if best_book else "No bookings yet"
            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-top-bar kpi-bar-amber"></div>
                    <div class="kpi-header"><span class="kpi-label">🏆 Top Booking Rate</span><span style="font-size: 18px;">📅</span></div>
                    <div class="kpi-value">{val_book}</div>
                    <div class="kpi-micro"><span class="kpi-pill kpi-pill-amber">Highest</span><span>{tpl_book}</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with kpi_col4:
            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-top-bar" style="background: #8B5CF6;"></div>
                    <div class="kpi-header"><span class="kpi-label">Active Templates</span><span style="font-size: 18px;">📑</span></div>
                    <div class="kpi-value">{len(templates)}</div>
                    <div class="kpi-micro"><span class="kpi-pill" style="background: #F3E8FF; color: #7C3AED;">Ready</span><span>{stats.get('total_templates_active', 0)} in active use</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Day-by-Day Trend Analysis Chart with Template Selector Dropdown ──
        st.markdown("#### 📈 Day-by-Day Metric Progression (Increasing vs Decreasing)")
        
        tpl_filter_options = ["All Templates (Comparative)"] + [t["name"] for t in templates]
        c_filter1, c_filter2 = st.columns([1.6, 1.4])
        with c_filter1:
            chosen_tpl_filter = st.selectbox(
                "🎯 Select Template to Analyze (One-by-One or All):",
                options=tpl_filter_options,
                index=0,
                key="tab2_tpl_filter_select",
                help="Choose a specific template to inspect its daily conversion curve one by one, or select 'All Templates' to compare side-by-side.",
            )
        with c_filter2:
            metric_choice = st.radio(
                "Select Trend Metric to Plot",
                ["Open Rate (%)", "Click Rate (%)", "Booking Rate (%)"],
                horizontal=True,
                key="chart_metric_choice",
            )

        daily_df = stats.get("daily_trends", pd.DataFrame())
        col_map = {
            "Open Rate (%)": "open_rate",
            "Click Rate (%)": "click_rate",
            "Booking Rate (%)": "booking_rate",
        }
        target_metric = col_map[metric_choice]

        if chosen_tpl_filter != "All Templates (Comparative)":
            plot_df = daily_df[daily_df["template_name"] == chosen_tpl_filter] if not daily_df.empty else pd.DataFrame()
            chart_title = f"Day-by-Day {metric_choice} for {chosen_tpl_filter}"
            
            # Focused single template KPI metrics ribbon
            single_stat = next((s for s in stats.get("template_stats", []) if s["template_name"] == chosen_tpl_filter), None)
            if single_stat:
                st.markdown(
                    f"""
                    <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 14px 18px; margin: 10px 0 16px 0; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                        <div>
                            <span style="font-size: 11px; text-transform: uppercase; font-weight: 700; color: #64748B;">Focused Template</span>
                            <div style="font-size: 16px; font-weight: 700; color: #0F172A;">{single_stat['template_name']}</div>
                            <span style="font-size: 12px; color: #475569;">Category: {single_stat['category']}</span>
                        </div>
                        <div style="display: flex; gap: 24px; align-items: center;">
                            <div style="text-align: center;">
                                <div style="font-size: 11px; color: #64748B; font-weight: 600;">ASSIGNED</div>
                                <div style="font-size: 18px; font-weight: 700; color: #0F172A;">{single_stat['total_leads']}</div>
                            </div>
                            <div style="text-align: center;">
                                <div style="font-size: 11px; color: #64748B; font-weight: 600;">SENT</div>
                                <div style="font-size: 18px; font-weight: 700; color: #0F172A;">{single_stat['total_sent']}</div>
                            </div>
                            <div style="text-align: center;">
                                <div style="font-size: 11px; color: #2563EB; font-weight: 600;">OPEN RATE</div>
                                <div style="font-size: 18px; font-weight: 700; color: #2563EB;">{single_stat['open_rate']}%</div>
                                <span style="font-size: 11px; color: #64748B;">({single_stat['opened_count']} opens)</span>
                            </div>
                            <div style="text-align: center;">
                                <div style="font-size: 11px; color: #0D9488; font-weight: 600;">CLICK RATE</div>
                                <div style="font-size: 18px; font-weight: 700; color: #0D9488;">{single_stat['click_rate']}%</div>
                                <span style="font-size: 11px; color: #64748B;">({single_stat['clicked_count']} clicks)</span>
                            </div>
                            <div style="text-align: center;">
                                <div style="font-size: 11px; color: #7C3AED; font-weight: 600;">BOOKING RATE</div>
                                <div style="font-size: 18px; font-weight: 700; color: #7C3AED;">{single_stat['booking_rate']}%</div>
                                <span style="font-size: 11px; color: #64748B;">({single_stat['booked_count']} booked)</span>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            plot_df = daily_df
            chart_title = f"Day-by-Day {metric_choice} Across All Templates"

        if not plot_df.empty:
            fig = px.line(
                plot_df,
                x="date",
                y=target_metric,
                color="template_name",
                markers=True,
                title=chart_title,
                labels={"date": "Date", target_metric: metric_choice, "template_name": "Template"},
            )
            fig.update_layout(
                hovermode="x unified",
                plot_bgcolor="#FFFFFF",
                paper_bgcolor="#FFFFFF",
                font_family="Inter, -apple-system, sans-serif",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                yaxis=dict(ticksuffix="%", range=[0, 105]),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            if chosen_tpl_filter != "All Templates (Comparative)":
                st.info(f"💡 No daily outreach telemetry recorded yet for **{chosen_tpl_filter}**. As emails are sent for this cohort, its daily {metric_choice} trajectory will appear here.")
            else:
                st.info(
                    "💡 **Day-by-day trend chart will populate automatically** as outreach emails are sent to your leads and telemetry (opens, clicks, bookings) is recorded."
                )

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Template Comparison Leaderboard ──
        st.markdown("#### 📋 Template Comparison Leaderboard")
        stats_list = stats.get("template_stats", [])
        if stats_list:
            leaderboard_rows = []
            for s in stats_list:
                leaderboard_rows.append({
                    "Template": s["template_name"],
                    "Category": s["category"],
                    "Total Leads": s["total_leads"],
                    "Sent": s["total_sent"],
                    "Opens": s["opened_count"],
                    "Open Rate": f"{s['open_rate']}%",
                    "Clicks": s["clicked_count"],
                    "Click Rate": f"{s['click_rate']}%",
                    "Replies": s["replied_count"],
                    "Reply Rate": f"{s['reply_rate']}%",
                    "Bookings": s["booked_count"],
                    "Booking Rate": f"{s['booking_rate']}%",
                })
            df_board = pd.DataFrame(leaderboard_rows)
            st.dataframe(df_board, use_container_width=True, hide_index=True)

            # Visual Bar Comparison
            st.markdown("##### Visual Metric Comparison Across Templates")
            chart_data = []
            for s in stats_list:
                if s["total_sent"] > 0:
                    chart_data.append({"Template": s["template_name"].split(":")[0], "Metric": "Open Rate %", "Value": s["open_rate"]})
                    chart_data.append({"Template": s["template_name"].split(":")[0], "Metric": "Click Rate %", "Value": s["click_rate"]})
                    chart_data.append({"Template": s["template_name"].split(":")[0], "Metric": "Booking Rate %", "Value": s["booking_rate"]})
            if chart_data:
                df_bar = pd.DataFrame(chart_data)
                fig_bar = px.bar(
                    df_bar,
                    x="Template",
                    y="Value",
                    color="Metric",
                    barmode="group",
                    text_auto=True,
                    labels={"Value": "Percentage (%)"},
                    color_discrete_map={
                        "Open Rate %": "#2563EB",
                        "Click Rate %": "#0D9488",
                        "Booking Rate %": "#D97706",
                    },
                )
                fig_bar.update_layout(yaxis=dict(ticksuffix="%"))
                st.plotly_chart(fig_bar, use_container_width=True)

    # ═══════════════════════════════════════════════════════════════
    # TAB 3: SHEET-TO-TEMPLATE BATCH OUTREACH (20–25 LEADS)
    # ═══════════════════════════════════════════════════════════════
    with tab_batch:
        st.markdown("### 📤 Sheet-to-Template Batch Outreach (20–25 Leads per Sheet)")
        st.markdown(
            """
            Upload a spreadsheet containing **20 to 25 leads** and pair it directly with your chosen template.
            Each sheet will execute with its designated template so you can cleanly analyze A/B performance across batches.
            """
        )

        b_col1, b_col2 = st.columns([1.2, 1], gap="large")

        with b_col1:
            st.markdown("#### 1. Upload Lead Sheet (20–25 Records)")
            batch_file = st.file_uploader(
                "Upload Excel or CSV Sheet",
                type=["xlsx", "xls", "csv"],
                key="batch_sheet_uploader",
                help="Recommended: 20 to 25 rows with columns: email, name, company",
            )

            batch_df = pd.DataFrame()
            if batch_file:
                try:
                    if batch_file.name.endswith(".csv"):
                        batch_df = pd.read_csv(batch_file)
                    else:
                        batch_df = pd.read_excel(batch_file)
                    st.success(f"Loaded **{batch_file.name}** with **{len(batch_df)}** leads!")
                    if len(batch_df) < 15 or len(batch_df) > 35:
                        st.caption(f"ℹ️ Note: Sheet contains {len(batch_df)} leads (your target batch size is 20–25 leads).")
                except Exception as e:
                    st.error(f"Error reading sheet: {e}")

        with b_col2:
            st.markdown("#### 2. Select Assigned Template")
            tpl_choices = {t["id"]: f"{t['name']} ({t.get('category', 'General')})" for t in templates}
            batch_tpl_id = st.selectbox(
                "Template for this Sheet Batch",
                options=list(tpl_choices.keys()),
                format_func=lambda tid: tpl_choices[tid],
                key="batch_template_picker",
            )
            batch_tpl = get_template_by_id(batch_tpl_id) or templates[0]

            st.markdown(
                f"""
                <div style="background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 8px; padding: 12px; font-size: 13px; color: #1E40AF;">
                    <strong>Assigned:</strong> {batch_tpl['name']}<br>
                    <strong>Subject Pattern:</strong> {batch_tpl.get('subject', '')}
                </div>
                """,
                unsafe_allow_html=True,
            )

        if not batch_df.empty:
            st.markdown("#### 3. Review Leads in this Sheet")
            cols_preview = [c for c in ["lead_id", "email", "name", "company"] if c in batch_df.columns]
            if not cols_preview:
                cols_preview = batch_df.columns[:4]
            st.dataframe(batch_df[cols_preview], use_container_width=True, hide_index=True)

            if st.button(
                f"🚀 Generate {len(batch_df)} Personalized Drafts with '{batch_tpl['name']}'",
                type="primary",
                key="btn_generate_batch_drafts",
                use_container_width=True,
            ):
                campaign_name = os.getenv("CAMPAIGN_NAME", "default_campaign")
                booking_url = os.getenv(
                    "BOOKING_FORM_URL",
                    "https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled",
                )
                progress = st.progress(0.0, text="Generating template-linked outreach drafts...")
                db = SessionLocal()
                created = 0
                failed = 0
                total_rows = len(batch_df)

                for idx, row in batch_df.iterrows():
                    email = str(row.get("email", "")).strip()
                    if not email or "@" not in email:
                        failed += 1
                        continue
                    name = None if pd.isna(row.get("name")) else str(row.get("name"))
                    company = None if pd.isna(row.get("company")) else str(row.get("company"))
                    lead_id = str(row.get("lead_id", f"lead_{idx}_{uuid.uuid4().hex[:4]}"))

                    progress.progress(
                        (created + failed) / total_rows,
                        text=f"Drafting for {email} ({name or 'Lead'})...",
                    )

                    try:
                        token = generate_token()
                        tracking_link = booking_url

                        subj, body_html = render_template(
                            batch_tpl_id,
                            lead_name=name,
                            company=company,
                            tracking_link=tracking_link,
                            booking_url=booking_url,
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
                            subject=subj,
                            body=body_html,
                            status="drafted",
                            template_id=batch_tpl_id,
                            template_name=batch_tpl["name"],
                        )
                        created += 1
                    except Exception as err:
                        failed += 1

                db.close()
                progress.progress(1.0, text="Completed!")
                st.balloons()
                st.success(
                    f"✅ Successfully created **{created} drafts** linked to **{batch_tpl['name']}**! "
                    "You can now review and approve them in the **Email Review Studio**."
                )
