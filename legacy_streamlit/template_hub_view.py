from utils.theme import apply_chart_theme, is_dark_mode
import html
import os
import textwrap
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
    delete_custom_template,
    is_template_customized,
    interpolate_lead_placeholders,
    render_template,
    compute_template_analytics,
)
from Backend.db import SessionLocal
from Backend.crud import create_pending_entry
from utils.token import generate_token


def render_template_hub(df_logs: pd.DataFrame) -> None:
    """Renders the executive Email Template Studio & Performance Hub."""
    templates = load_all_templates()
    stats = compute_template_analytics(df_logs)

    # Scoped Premium CSS for Template Studio
    st.markdown(
        """
        <style>
        .top-tpl-banner {
            background: var(--bg-surface);
            border: 1px solid var(--border-subtle);
            border-radius: 12px;
            padding: 20px 24px;
            margin-bottom: 22px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
        }
        .top-tpl-title {
            font-size: 22px;
            font-weight: 700;
            color: var(--text-primary);
            margin: 0;
            display: flex;
            align-items: center;
            gap: 10px;
            letter-spacing: -0.02em;
        }
        .top-tpl-desc {
            font-size: 13.5px;
            color: var(--text-muted);
            margin: 4px 0 0 0;
            line-height: 1.45;
        }
        .tpl-badge-pill {
            font-size: 11px;
            font-weight: 600;
            padding: 4px 10px;
            border-radius: 9999px;
            letter-spacing: 0.02em;
            display: inline-flex;
            align-items: center;
            gap: 5px;
        }
        .tpl-card-box {
            background: var(--bg-surface);
            border: 1px solid var(--border-subtle);
            border-radius: 10px;
            padding: 14px 16px;
            margin-bottom: 10px;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .tpl-card-box:hover {
            border-color: var(--border-strong);
            box-shadow: 0 4px 12px rgba(0,0,0,0.04);
        }
        .tpl-card-box.is-active {
            background: var(--bg-elevated);
            border: 1.5px solid #2563EB;
            border-left: 4px solid #2563EB;
            box-shadow: 0 4px 14px -2px rgba(37, 99, 235, 0.12);
        }
        .tpl-meta-tag {
            font-size: 10.5px;
            font-weight: 600;
            color: var(--text-secondary);
            background: var(--bg-nested);
            padding: 2px 7px;
            border-radius: 6px;
        }
        .email-window-header {
            background: var(--bg-elevated);
            border: 1px solid var(--border-subtle);
            border-bottom: 1px solid #E2E8F0;
            border-radius: 10px 10px 0 0;
            padding: 10px 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .email-dot-group {
            display: flex;
            gap: 5px;
            align-items: center;
        }
        .email-dot {
            width: 9px;
            height: 9px;
            border-radius: 50%;
            display: inline-block;
        }
        .email-subject-box {
            background: var(--bg-surface);
            border: 1px solid var(--border-subtle);
            border-top: none;
            padding: 14px 18px;
            margin-bottom: 14px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.02);
        }
        .email-preview-frame {
            background: var(--bg-nested);
            border: 1px solid var(--border-subtle);
            border-radius: 10px;
            padding: 14px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.03);
        }
        /* Step Cards for Batch Outreach */
        .batch-step-card {
            background: var(--bg-surface);
            border: 1px solid var(--border-subtle);
            border-radius: 12px;
            padding: 20px 22px;
            margin-bottom: 16px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.03);
            transition: all 0.2s ease;
        }
        .batch-step-card:hover {
            border-color: var(--border-strong);
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        }
        .batch-step-num {
            font-size: 10px;
            font-weight: 700;
            background: #EFF6FF;
            color: #1D4ED8;
            padding: 3px 8px;
            border-radius: 6px;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            border: 1px solid #DBEAFE;
            display: inline-block;
        }
        .batch-step-title {
            font-size: 15px;
            font-weight: 700;
            color: var(--text-primary);
            margin-top: 6px;
            margin-bottom: 3px;
        }
        .batch-step-desc {
            font-size: 12.5px;
            color: var(--text-muted);
            line-height: 1.4;
            margin-bottom: 12px;
        }
        .batch-stat-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: var(--bg-elevated);
            border: 1px solid var(--border-subtle);
            padding: 5px 12px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            color: var(--text-secondary);
        }
        .analytics-subbanner {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--bg-surface);
            border: 1px solid var(--border-subtle);
            border-radius: 10px;
            padding: 16px 20px;
            margin-bottom: 18px;
            flex-wrap: wrap;
            gap: 12px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Top Executive Banner with clean metrics
    st.markdown(
        f"""
        <div class="top-tpl-banner">
            <div>
                <h1 class="top-tpl-title">
                    ✉️ Email Template Studio
                </h1>
                <p class="top-tpl-desc">
                    Review and customize responsive executive HTML templates with real-time lead simulation, copy outreach copy, and pair batch outreach cohorts.
                </p>
            </div>
            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                <span class="tpl-badge-pill" style="background: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE;">
                    ⚡ {len(templates)} Templates Ready
                </span>
                <span class="tpl-badge-pill" style="background: #ECFDF5; color: #047857; border: 1px solid #A7F3D0;">
                    ✓ Responsive HTML
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_gallery, tab_analytics, tab_batch = st.tabs([
        f"🎨 Template Studio & Live Preview ({len(templates)})",
        "📈 Performance Analytics & Daily Trends",
        "📤 Sheet-to-Template Batch Outreach (20–25 Leads)",
    ])

    # ═══════════════════════════════════════════════════════════════
    # TAB 1: TEMPLATE STUDIO & LIVE PREVIEW
    # ═══════════════════════════════════════════════════════════════
    with tab_gallery:
        if "gallery_tpl_select" not in st.session_state:
            st.session_state["gallery_tpl_select"] = templates[0]["id"]

        selected_id = st.session_state["gallery_tpl_select"]
        current_tpl = get_template_by_id(selected_id) or templates[0]

        # Master-Detail Layout: Left Directory (38%), Right Studio (62%)
        col_left, col_right = st.columns([1.1, 1.9], gap="large")

        # ── LEFT COLUMN: Clean Template Directory ──
        with col_left:
            st.markdown(
                """
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div style="font-size: 15px; font-weight: 700; color: #0F172A;">📑 Template Directory</div>
                    <span style="font-size: 11.5px; color: #64748B; font-weight: 500;">Click to preview</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Quick search & category filter in one sleek row
            f_col1, f_col2 = st.columns([1.3, 1.1])
            with f_col1:
                search_kw = st.text_input(
                    "Search",
                    placeholder="🔍 Filter templates...",
                    key="tpl_search_box",
                    label_visibility="collapsed",
                ).strip().lower()
            with f_col2:
                all_cats = ["All Categories"] + sorted(list(set(t.get("category", "General") for t in templates)))
                cat_filter = st.selectbox(
                    "Filter Category",
                    options=all_cats,
                    key="tpl_cat_filter_box",
                    label_visibility="collapsed",
                )

            # Filter templates list
            filtered_templates = []
            for t in templates:
                matches_cat = (cat_filter == "All Categories") or (t.get("category") == cat_filter)
                matches_kw = (
                    not search_kw
                    or search_kw in t.get("name", "").lower()
                    or search_kw in t.get("description", "").lower()
                    or search_kw in t.get("subject", "").lower()
                    or search_kw in t.get("category", "").lower()
                )
                if matches_cat and matches_kw:
                    filtered_templates.append(t)

            if not filtered_templates:
                st.info("No templates match your filter criteria.")
            else:
                for idx, t in enumerate(filtered_templates, start=1):
                    is_active = (t["id"] == selected_id)
                    accent = t.get("accent_color", "#2563EB")
                    cat_name = t.get("category", "General")
                    subj_snippet = t.get("subject", "")

                    is_custom = is_template_customized(t["id"])
                    custom_tag = '<span style="background: #FEF3C7; color: #92400E; font-size: 10px; font-weight: 600; padding: 1px 6px; border-radius: 4px; border: 1px solid #FDE68A;">Customized</span>' if is_custom else ''

                    esc_name = html.escape(t["name"])
                    esc_cat = html.escape(cat_name)
                    esc_desc = html.escape(t.get("description", ""))

                    if is_active:
                        # Active Card: Prominent, highlighted, clean, no redundant button needed
                        active_html = (
                            f'<div class="tpl-card-box is-active" style="border-left-color: {accent};">'
                            f'<div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">'
                            f'<div style="font-weight: 700; font-size: 14px; color: #0F172A; line-height: 1.3;">{esc_name}</div>'
                            f'<div style="display: flex; gap: 4px; align-items: center;">'
                            f'{custom_tag}'
                            f'<span style="background: {accent}; color: #FFFFFF; font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 9999px; letter-spacing: 0.04em; white-space: nowrap;">● ACTIVE</span>'
                            f'</div>'
                            f'</div>'
                            f'<div style="margin-bottom: 6px;"><span class="tpl-meta-tag">{esc_cat}</span></div>'
                            f'<div style="font-size: 12px; color: #475569; line-height: 1.45; margin-bottom: 8px;">{esc_desc}</div>'
                            f'<div style="font-size: 11px; background: #FFFFFF; border: 1px solid #E2E8F0; padding: 5px 8px; border-radius: 6px; color: #334155; word-break: break-all;">'
                            f'<strong style="color: #64748B;">Subject:</strong> <code>{html.escape(subj_snippet)}</code>'
                            f'</div>'
                            f'</div>'
                        )
                        st.markdown(active_html, unsafe_allow_html=True)
                    else:
                        # Inactive Card: Clean card with a single integrated action button
                        inactive_html = (
                            f'<div class="tpl-card-box">'
                            f'<div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">'
                            f'<div style="font-weight: 600; font-size: 13.5px; color: #1E293B; line-height: 1.3;">{esc_name}</div>'
                            f'{custom_tag}'
                            f'</div>'
                            f'<div style="margin-bottom: 6px;"><span class="tpl-meta-tag">{esc_cat}</span></div>'
                            f'<div style="font-size: 12px; color: #64748B; line-height: 1.4; margin-bottom: 8px;">{esc_desc}</div>'
                            f'<div style="font-size: 11px; background: #F8FAFC; border: 1px solid #E2E8F0; padding: 4px 7px; border-radius: 6px; color: #475569; word-break: break-all; margin-bottom: 8px;">'
                            f'<strong style="color: #64748B;">Subject:</strong> <code>{html.escape(subj_snippet)}</code>'
                            f'</div>'
                            f'</div>'
                        )
                        st.markdown(inactive_html, unsafe_allow_html=True)
                        # Single clean action button below card
                        if st.button(
                            f"Preview {t['name'].split(':')[0]} →",
                            key=f"select_tpl_{t['id']}",
                            use_container_width=True,
                        ):
                            st.session_state["gallery_tpl_select"] = t["id"]
                            st.rerun()

                    st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)

            # Add Custom Template Expander
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            with st.expander("➕ Create New Custom Template", expanded=False):
                with st.form("form_add_custom_template"):
                    st.markdown("##### New Outreach Template")
                    new_id = st.text_input("Unique ID", value=f"tpl_custom_{uuid.uuid4().hex[:6]}")
                    new_name = st.text_input("Template Name", placeholder="e.g. Template 8: Executive Video Audit")
                    new_cat = st.selectbox(
                        "Category",
                        ["Executive & Velocity", "Voice & Inbound AI", "Technical Capabilities", "Operational Automation", "Team Augmentation", "Software Modernization", "Founder & Advisory", "Custom"],
                    )
                    new_subj = st.text_input("Subject Line Pattern", value="Quick question for {{Company}}")
                    new_desc = st.text_area("Description / Value Proposition", value="Custom tailored outreach template for specialized lead batches.", height=80)
                    new_html = st.text_area("HTML Email Code", height=200, placeholder="Paste inline-styled HTML code here...")
                    
                    submitted = st.form_submit_button("💾 Save Template to Library", type="primary", use_container_width=True)
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
                                st.session_state["gallery_tpl_select"] = new_id.strip()
                                st.toast(f"✅ Template '{new_name}' saved to library!", icon="💾")
                                st.rerun()
                            else:
                                st.error("Could not save template to disk.")
                        else:
                            st.warning("Please fill in ID, Name, and HTML content.")

        # ── RIGHT COLUMN: Live Inspector & Email Preview ──
        with col_right:
            sim_name = "Alex"
            sim_company = "Acme Health"
            sim_pain = "manual operational overhead"

            # Render Interpolated HTML
            booking_url = os.getenv(
                "BOOKING_FORM_URL",
                "https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled",
            )
            interp_subject, interp_html = render_template(
                selected_id,
                lead_name=sim_name,
                company=sim_company,
                pain_point=sim_pain,
                booking_url=booking_url,
            )

            is_cur_custom = is_template_customized(current_tpl["id"])
            custom_pill = '<span style="background: #FEF3C7; color: #92400E; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px; border: 1px solid #FDE68A;">Customized</span>' if is_cur_custom else ''

            # Simulated Email Client Window Chrome with Proper Subject Line Card
            st.markdown(
                textwrap.dedent(f"""
                <div class="email-window-header">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <div class="email-dot-group">
                            <span class="email-dot" style="background: #FF5F56;"></span>
                            <span class="email-dot" style="background: #FFBD2E;"></span>
                            <span class="email-dot" style="background: #27C93F;"></span>
                        </div>
                        <span style="font-size: 13px; font-weight: 600; color: #1E293B;">
                            Live Preview: {current_tpl['name']}
                        </span>
                    </div>
                    <div style="display: flex; gap: 6px; align-items: center;">
                        {custom_pill}
                        <span class="tpl-meta-tag">{current_tpl.get('category', 'General')}</span>
                    </div>
                </div>
                <div class="email-subject-box">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                        <div style="font-size: 11px; text-transform: uppercase; font-weight: 700; color: #64748B; letter-spacing: 0.05em;">
                            Subject Line
                        </div>
                        <div style="font-size: 11px; color: #64748B;">
                            Pattern: <code style="color: #0284C7; background: #F0F9FF; padding: 2px 6px; border-radius: 4px; font-size: 11px; border: 1px solid #BAE6FD;">{html.escape(current_tpl.get('subject', ''))}</code>
                        </div>
                    </div>
                    <div style="font-size: 16px; font-weight: 700; color: #0F172A; margin-bottom: 10px;">
                        {html.escape(interp_subject)}
                    </div>
                    <div style="display: flex; gap: 20px; font-size: 12.5px; color: #475569; border-top: 1px solid #F1F5F9; padding-top: 8px; flex-wrap: wrap;">
                        <div><strong style="color: #334155;">From:</strong> Tirth Patel &lt;support@nenotechnology.com&gt;</div>
                        <div><strong style="color: #334155;">To:</strong> Alex &lt;contact@acmehealth.com.au&gt;</div>
                    </div>
                </div>
                """).strip(),
                unsafe_allow_html=True,
            )

            # ── SUBJECT LINE & TITLE CRUD CONTROLS ──
            with st.expander("✏️ Edit Subject Line & Template Title (Dynamic Placeholder CRUD)", expanded=False):
                st.markdown(
                    """
                    <div style="font-size: 13px; color: #475569; margin-bottom: 10px; line-height: 1.45;">
                        Customize this template's <strong>Title</strong> and <strong>Subject Line</strong>. Change the words or phrasing as you wish, while keeping dynamic tags like <code>{{Company}}</code> so lead and business names carry over automatically into every personalized email.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                crud_col_title, crud_col_subj = st.columns([1, 1.2])
                with crud_col_title:
                    edit_name_val = st.text_input(
                        "Template Title / Name",
                        value=current_tpl.get("name", ""),
                        key=f"crud_name_input_{current_tpl['id']}",
                        help="Display name in the sidebar, logs, and batch dispatch.",
                    )
                with crud_col_subj:
                    edit_subj_val = st.text_input(
                        "Subject Line Pattern",
                        value=current_tpl.get("subject", "Quick idea for {{Company}}"),
                        key=f"crud_subj_input_{current_tpl['id']}",
                        help="Dynamic pattern using {{Company}} or {{FirstName}}.",
                    )

                # Visual guide for automatic names
                st.markdown(
                    """
                    <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 9px 13px; margin: 4px 0 10px 0; font-size: 12px; color: #334155; line-height: 1.5;">
                        <strong style="color: #0F172A;">💡 How Automatic Names Carry Over:</strong><br>
                        • <code>{{Company}}</code> &rarr; Automatically inserts each prospect's company name (e.g., <em>Acme Health</em>)<br>
                        • <code>{{FirstName}}</code> &rarr; Automatically inserts each prospect's first name (e.g., <em>Alex</em>)<br>
                        • <code>{{Pain}}</code> &rarr; Automatically inserts the prospect's operational pain point
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Real-time preview of the updated subject line
                live_rendered_subject = interpolate_lead_placeholders(
                    edit_subj_val,
                    first_name=sim_name,
                    company_name=sim_company,
                    pain_text=sim_pain,
                )
                st.markdown(
                    f"""
                    <div style="background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 8px; padding: 10px 14px; margin-bottom: 12px;">
                        <div style="font-size: 11px; text-transform: uppercase; font-weight: 700; color: #1D4ED8; letter-spacing: 0.04em; margin-bottom: 2px;">
                            Live Render Preview for {sim_company}:
                        </div>
                        <div style="font-size: 14.5px; font-weight: 700; color: #1E3A8A;">
                            "{html.escape(live_rendered_subject)}"
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # CRUD Action Buttons
                c_btn1, c_btn2, c_btn3 = st.columns([1.8, 1.6, 1.6])
                with c_btn1:
                    if st.button("💾 Save Subject & Title", type="primary", key=f"btn_save_crud_{current_tpl['id']}", use_container_width=True):
                        if not edit_name_val.strip():
                            st.warning("Please provide a Template Title.")
                        elif not edit_subj_val.strip():
                            st.warning("Please provide a Subject Line pattern.")
                        else:
                            updated_tpl = dict(current_tpl)
                            updated_tpl["name"] = edit_name_val.strip()
                            updated_tpl["subject"] = edit_subj_val.strip()
                            save_custom_template(updated_tpl)
                            st.toast(f"✅ Saved! Subject updated to: '{edit_subj_val.strip()}'", icon="💾")
                            st.rerun()

                with c_btn2:
                    if is_cur_custom:
                        if st.button("↺ Reset to Built-in", key=f"btn_reset_crud_{current_tpl['id']}", use_container_width=True):
                            delete_custom_template(current_tpl["id"])
                            st.toast("↺ Template reset to built-in default.", icon="↺")
                            st.rerun()

                with c_btn3:
                    if current_tpl.get("badge") == "Custom Added":
                        if st.button("🗑️ Delete Template", key=f"btn_del_crud_{current_tpl['id']}", use_container_width=True):
                            delete_custom_template(current_tpl["id"])
                            st.session_state["gallery_tpl_select"] = templates[0]["id"]
                            st.toast("🗑️ Template permanently deleted.", icon="🗑️")
                            st.rerun()

            # Quick Copy Subject Line bar
            with st.expander("📋 Copy Subject Line or HTML Source", expanded=False):
                st.caption("Copy this ready-to-send personalized subject line:")
                st.code(interp_subject, language="")

            # Responsive Email Preview Frame
            st.markdown('<div class="email-preview-frame">', unsafe_allow_html=True)
            components.html(interp_html, height=740, scrolling=True)
            st.markdown("</div>", unsafe_allow_html=True)

            # Inspect & Edit HTML Code Drawer
            with st.expander("🛠️ Inspect & Customize Template HTML Code", expanded=False):
                st.markdown(
                    "<p style='font-size: 13px; color: #64748B; margin-bottom: 8px;'>Modify the template layout, copy, or placeholders (<code>{{FirstName}}</code>, <code>{{Company}}</code>, <code>{{Pain}}</code>, <code>LOGO_URL</code>, <code>BOOKING_LINK</code>). Changes are saved to disk.</p>",
                    unsafe_allow_html=True,
                )
                raw_code = current_tpl.get("html_content", interp_html)
                edited_html = st.text_area(
                    "HTML Template Source Code",
                    value=raw_code,
                    height=320,
                    key=f"edit_raw_html_{current_tpl['id']}",
                    label_visibility="collapsed",
                )
                btn_save_col1, btn_save_col2 = st.columns([1.8, 1.8])
                with btn_save_col1:
                    if st.button("💾 Save HTML Changes", type="primary", key=f"btn_save_raw_{current_tpl['id']}", use_container_width=True):
                        updated_tpl = dict(current_tpl)
                        updated_tpl["html_content"] = edited_html
                        save_custom_template(updated_tpl)
                        st.toast(f"✅ Template '{current_tpl['name']}' saved successfully!", icon="💾")
                        st.rerun()
                with btn_save_col2:
                    if is_cur_custom:
                        if st.button("↺ Reset HTML to Default", key=f"btn_reset_raw_{current_tpl['id']}", use_container_width=True):
                            delete_custom_template(current_tpl["id"])
                            st.toast("↺ Template HTML reset to default.", icon="↺")
                            st.rerun()

    # ═══════════════════════════════════════════════════════════════
    # TAB 2: TEMPLATE-WISE ANALYTICS & DAILY TRENDS
    # ═══════════════════════════════════════════════════════════════
    with tab_analytics:
        st.markdown(
            """
            <div class="analytics-subbanner">
                <div>
                    <div style="font-size: 17px; font-weight: 700; color: #0F172A; display: flex; align-items: center; gap: 8px;">
                        📊 Template Conversion & Telemetry Intelligence
                    </div>
                    <p style="font-size: 13px; color: #64748B; margin: 3px 0 0 0;">
                        Track open rates, click-through rates, reply frequency, and consultation bookings across email variants.
                    </p>
                </div>
                <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                    <span class="tpl-badge-pill" style="background: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE;">
                        ● Real-Time Telemetry
                    </span>
                    <span class="tpl-badge-pill" style="background: #F0FDF4; color: #166534; border: 1px solid #BBF7D0;">
                        4 Funnel Metrics
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 4 Trophy KPI Cards
        best_open = stats.get("best_open_rate")
        best_click = stats.get("best_click_rate")
        best_book = stats.get("best_booking_rate")

        kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
        with kpi_col1:
            val_open = f"{best_open['open_rate']}%" if best_open else "—"
            tpl_open = best_open['template_name'].split(':')[0] if best_open else "No sends yet"
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
            active_count = stats.get('total_templates_active', 0)
            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-top-bar" style="background: #8B5CF6;"></div>
                    <div class="kpi-header"><span class="kpi-label">Active Variants</span><span style="font-size: 18px;">📑</span></div>
                    <div class="kpi-value">{len(templates)}</div>
                    <div class="kpi-micro"><span class="kpi-pill" style="background: #F3E8FF; color: #7C3AED;">Ready</span><span>{active_count} cohorts active</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

        # ── Day-by-Day Trend Analysis Chart with Template Selector Dropdown ──
        st.markdown(
            """
            <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 8px;">
                <div>
                    <div style="font-size: 16px; font-weight: 700; color: #0F172A;">📈 Multi-Variant Daily Progression Curves</div>
                    <p style="font-size: 12.5px; color: #64748B; margin: 2px 0 0 0;">Track daily conversion trajectories over time for all cohorts or isolate a single template variant.</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        tpl_filter_options = ["All Templates (Comparative)"] + [t["name"] for t in templates]
        c_filter1, c_filter2 = st.columns([1.5, 1.5], gap="medium")
        with c_filter1:
            chosen_tpl_filter = st.selectbox(
                "Focus Variant",
                options=tpl_filter_options,
                index=0,
                key="tab2_tpl_filter_select",
                help="Inspect daily conversion curve for one template or compare all side-by-side.",
            )
        with c_filter2:
            metric_choice = st.radio(
                "Metric Trajectory to Plot",
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
            chart_title = f"Daily {metric_choice} Progression: {chosen_tpl_filter}"
            
            # Focused single template KPI metrics ribbon
            single_stat = next((s for s in stats.get("template_stats", []) if s["template_name"] == chosen_tpl_filter), None)
            if single_stat:
                st.markdown(
                    f"""
                    <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 14px 20px; margin: 10px 0 16px 0; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px;">
                        <div>
                            <span style="font-size: 10.5px; text-transform: uppercase; font-weight: 700; color: #64748B; letter-spacing: 0.05em;">Variant Focus</span>
                            <div style="font-size: 15.5px; font-weight: 700; color: #0F172A;">{single_stat['template_name']}</div>
                            <span class="tpl-meta-tag">{single_stat['category']}</span>
                        </div>
                        <div style="display: flex; gap: 24px; align-items: center; flex-wrap: wrap;">
                            <div style="text-align: center;">
                                <div style="font-size: 10.5px; color: #64748B; font-weight: 600;">ASSIGNED</div>
                                <div style="font-size: 17px; font-weight: 700; color: #0F172A;">{single_stat['total_leads']}</div>
                            </div>
                            <div style="text-align: center;">
                                <div style="font-size: 10.5px; color: #64748B; font-weight: 600;">SENT</div>
                                <div style="font-size: 17px; font-weight: 700; color: #0F172A;">{single_stat['total_sent']}</div>
                            </div>
                            <div style="text-align: center;">
                                <div style="font-size: 10.5px; color: #2563EB; font-weight: 600;">OPEN RATE</div>
                                <div style="font-size: 17px; font-weight: 700; color: #2563EB;">{single_stat['open_rate']}%</div>
                                <span style="font-size: 11px; color: #64748B;">({single_stat['opened_count']} opens)</span>
                            </div>
                            <div style="text-align: center;">
                                <div style="font-size: 10.5px; color: #0D9488; font-weight: 600;">CLICK RATE</div>
                                <div style="font-size: 17px; font-weight: 700; color: #0D9488;">{single_stat['click_rate']}%</div>
                                <span style="font-size: 11px; color: #64748B;">({single_stat['clicked_count']} clicks)</span>
                            </div>
                            <div style="text-align: center;">
                                <div style="font-size: 10.5px; color: #7C3AED; font-weight: 600;">BOOKING RATE</div>
                                <div style="font-size: 17px; font-weight: 700; color: #7C3AED;">{single_stat['booking_rate']}%</div>
                                <span style="font-size: 11px; color: #64748B;">({single_stat['booked_count']} booked)</span>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            plot_df = daily_df
            chart_title = f"Day-by-Day {metric_choice} Across All Cohorts"

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
                font_color="#334155",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                yaxis=dict(ticksuffix="%", range=[0, 105], gridcolor="#F1F5F9"),
                xaxis=dict(gridcolor="#F1F5F9"),
                margin=dict(l=20, r=20, t=40, b=20),
            )
            apply_chart_theme(fig)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            if chosen_tpl_filter != "All Templates (Comparative)":
                st.info(f"💡 No daily outreach telemetry recorded yet for **{chosen_tpl_filter}**. As emails are sent for this cohort, its daily {metric_choice} trajectory will appear here.")
            else:
                st.info(
                    "💡 **Day-by-day trend chart will populate automatically** as outreach emails are sent to your leads and telemetry (opens, clicks, bookings) is recorded."
                )

        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

        # ── Template Comparison Leaderboard ──
        st.markdown(
            """
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <div>
                    <div style="font-size: 16px; font-weight: 700; color: #0F172A;">🏆 Multi-Variant Performance Leaderboard</div>
                    <p style="font-size: 12.5px; color: #64748B; margin: 2px 0 0 0;">Comprehensive conversion funnel breakdown by template variant.</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        stats_list = stats.get("template_stats", [])
        if stats_list:
            leaderboard_rows = []
            for s in stats_list:
                leaderboard_rows.append({
                    "Template": s["template_name"],
                    "Category": s["category"],
                    "Assigned": s["total_leads"],
                    "Sent": s["total_sent"],
                    "Opens": s["opened_count"],
                    "Open Rate": s["open_rate"],
                    "Clicks": s["clicked_count"],
                    "Click Rate": s["click_rate"],
                    "Replies": s["replied_count"],
                    "Reply Rate": s["reply_rate"],
                    "Bookings": s["booked_count"],
                    "Booking Rate": s["booking_rate"],
                })
            df_board = pd.DataFrame(leaderboard_rows)
            
            st.dataframe(
                df_board,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Template": st.column_config.TextColumn("Template Variant", width="large"),
                    "Category": st.column_config.TextColumn("Category", width="medium"),
                    "Assigned": st.column_config.NumberColumn("Assigned", format="%d"),
                    "Sent": st.column_config.NumberColumn("Sent", format="%d"),
                    "Opens": st.column_config.NumberColumn("Opens", format="%d"),
                    "Open Rate": st.column_config.ProgressColumn("Open Rate", min_value=0, max_value=100, format="%.1f%%"),
                    "Clicks": st.column_config.NumberColumn("Clicks", format="%d"),
                    "Click Rate": st.column_config.ProgressColumn("Click Rate", min_value=0, max_value=100, format="%.1f%%"),
                    "Replies": st.column_config.NumberColumn("Replies", format="%d"),
                    "Reply Rate": st.column_config.ProgressColumn("Reply Rate", min_value=0, max_value=100, format="%.1f%%"),
                    "Bookings": st.column_config.NumberColumn("Bookings", format="%d"),
                    "Booking Rate": st.column_config.ProgressColumn("Booking Rate", min_value=0, max_value=100, format="%.1f%%"),
                },
            )

            # Visual Bar Comparison
            st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
            st.markdown("##### 📊 Visual Conversion Funnel by Template")
            chart_data = []
            for s in stats_list:
                if s["total_sent"] > 0:
                    t_short = s["template_name"].split(":")[0]
                    chart_data.append({"Template": t_short, "Metric": "Open Rate %", "Value": s["open_rate"]})
                    chart_data.append({"Template": t_short, "Metric": "Click Rate %", "Value": s["click_rate"]})
                    chart_data.append({"Template": t_short, "Metric": "Booking Rate %", "Value": s["booking_rate"]})
            if chart_data:
                df_bar = pd.DataFrame(chart_data)
                fig_bar = px.bar(
                    df_bar,
                    x="Template",
                    y="Value",
                    color="Metric",
                    barmode="group",
                    text_auto=".1f",
                    labels={"Value": "Percentage (%)"},
                    color_discrete_map={
                        "Open Rate %": "#2563EB",
                        "Click Rate %": "#0D9488",
                        "Booking Rate %": "#D97706",
                    },
                )
                fig_bar.update_layout(
                    yaxis=dict(ticksuffix="%", gridcolor="#F1F5F9"),
                    xaxis=dict(gridcolor="#F1F5F9"),
                    plot_bgcolor="#FFFFFF",
                    paper_bgcolor="#FFFFFF",
                    font_family="Inter, -apple-system, sans-serif",
                    font_color="#334155",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    margin=dict(l=20, r=20, t=30, b=20),
                )
                apply_chart_theme(fig_bar)
                st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})

    # ═══════════════════════════════════════════════════════════════
    # TAB 3: SHEET-TO-TEMPLATE BATCH OUTREACH (20–25 LEADS)
    # ═══════════════════════════════════════════════════════════════
    with tab_batch:
        st.markdown(
            """
            <div class="analytics-subbanner">
                <div>
                    <div style="font-size: 17px; font-weight: 700; color: #0F172A; display: flex; align-items: center; gap: 8px;">
                        📤 Batch Outreach (Sheet-to-Template)
                    </div>
                    <p style="font-size: 13px; color: #64748B; margin: 3px 0 0 0;">
                        Upload a lead spreadsheet (20–25 leads), select your template variant, and generate personalized drafts.
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        b_col1, b_col2 = st.columns([1.2, 1.1], gap="large")

        with b_col1:
            st.markdown(
                """
                <div class="batch-step-card">
                    <div class="batch-step-title">1. Upload Lead Spreadsheet</div>
                    <div class="batch-step-desc">Upload your CSV or Excel file containing columns: <code>email</code>, <code>name</code>, <code>company</code>.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            batch_file = st.file_uploader(
                "Upload Spreadsheet",
                type=["xlsx", "xls", "csv"],
                key="batch_sheet_uploader",
                label_visibility="collapsed",
            )

            batch_df = pd.DataFrame()
            if batch_file:
                try:
                    if batch_file.name.endswith(".csv"):
                        batch_df = pd.read_csv(batch_file)
                    else:
                        batch_df = pd.read_excel(batch_file)
                    
                    lead_count = len(batch_df)
                    st.success(f"✓ **{batch_file.name}** loaded with **{lead_count} leads**")
                except Exception as e:
                    st.error(f"Error reading file: {e}")

        with b_col2:
            st.markdown(
                """
                <div class="batch-step-card">
                    <div class="batch-step-title">2. Select Template</div>
                    <div class="batch-step-desc">Choose the email template variant to pair with this batch of leads.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            tpl_choices = {t["id"]: f"{t['name']}" for t in templates}
            batch_tpl_id = st.selectbox(
                "Select Template",
                options=list(tpl_choices.keys()),
                format_func=lambda tid: tpl_choices[tid],
                key="batch_template_picker",
                label_visibility="collapsed",
            )
            batch_tpl = get_template_by_id(batch_tpl_id) or templates[0]

            accent = batch_tpl.get("accent_color", "#2563EB")
            cat_label = batch_tpl.get("category", "General")
            st.markdown(
                f"""
                <div style="background: #F8FAFC; border: 1.5px solid #CBD5E1; border-left: 4px solid {accent}; border-radius: 10px; padding: 14px 16px; margin-top: 4px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                        <span style="font-size: 13.5px; font-weight: 700; color: #0F172A;">{batch_tpl['name']}</span>
                        <span class="tpl-meta-tag">{cat_label}</span>
                    </div>
                    <div style="font-size: 11.5px; background: #FFFFFF; border: 1px solid #E2E8F0; padding: 5px 8px; border-radius: 6px; color: #334155;">
                        <strong style="color: #64748B;">Subject Pattern:</strong> <code>{html.escape(batch_tpl.get('subject', ''))}</code>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # ── Review Leads & Generate Button ──
        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

        if not batch_df.empty:
            st.markdown(
                f"""
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div style="font-size: 15px; font-weight: 700; color: #0F172A;">Review Leads ({len(batch_df)} records)</div>
                    <span style="font-size: 12px; color: #059669; font-weight: 600;">● Ready to Generate</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
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


