"""Super Admin Platform Portal View.
"""

import streamlit as st
from Backend.db import SessionLocal
from Backend.auth_service import (
    get_platform_admin_overview,
    set_organization_status,
    register_organization_and_user,
)


def render_super_admin_portal():
    """Renders platform-wide super admin control center with crisp, executive box UI."""
    user = st.session_state.get("user", {})
    user_email = user.get("email", "").lower().strip()
    if user.get("platform_role") != "platform_super_admin" or user_email not in ["support@nenotechnology.com", "mohit@nenotechnology.us"]:
        st.error("⛔ Access Denied: You must be the Platform Super Administrator to view this portal.")
        return

    db = SessionLocal()
    try:
        overview = get_platform_admin_overview(db)
        metrics = overview.get("metrics", {})
        orgs = overview.get("organizations", [])

        # Executive Header Banner
        st.markdown(
            '<div style="margin-bottom: 22px;">'
            '<div style="display: inline-flex; align-items: center; gap: 6px; background: #FEF3C7; color: #92400E; font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 9999px; text-transform: uppercase; border: 1px solid #FDE68A; margin-bottom: 10px; letter-spacing: 0.04em;">'
            '<span>👑</span> Platform Super Admin'
            '</div>'
            '<h1 style="font-size: 28px; font-weight: 800; color: #0F172A; margin: 0 0 6px 0; letter-spacing: -0.025em; font-family: Outfit, sans-serif;">'
            'Global SaaS Operations Center'
            '</h1>'
            '<p style="font-size: 14px; color: #64748B; margin: 0; line-height: 1.5;">'
            'Platform-wide telemetry, cross-tenant auditing, and organization workspace controls.'
            '</p>'
            '</div>',
            unsafe_allow_html=True,
        )

        # Global KPIs in Crisp Modern Box Cards
        kpi_items = [
            ("Organizations", metrics.get("total_organizations", 0), "🏢"),
            ("Active Workspaces", metrics.get("active_organizations", 0), "⚡"),
            ("Platform Users", metrics.get("total_users", 0), "👥"),
            ("Total System Leads", metrics.get("total_leads", 0), "📋"),
            ("Outreach Logs", metrics.get("total_campaign_logs", 0), "✉️"),
            ("RAG Documents", metrics.get("total_kb_docs", 0), "📚"),
        ]
        kpi_cols = st.columns(6)
        for idx, (label, val, icon) in enumerate(kpi_items):
            with kpi_cols[idx]:
                with st.container(border=True):
                    st.markdown(
                        f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">'
                        f'<span style="font-family: monospace; font-size: 10px; font-weight: 600; color: #64748B; text-transform: uppercase; letter-spacing: 0.04em;">{label}</span>'
                        f'<span style="font-size: 14px;">{icon}</span>'
                        f'</div>'
                        f'<div style="font-family: monospace; font-size: 26px; font-weight: 700; color: #0F172A; line-height: 1.1;">{val}</div>',
                        unsafe_allow_html=True,
                    )

        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

        tab_list, tab_create = st.tabs(["🏢 All Organizations", "➕ Provision New Organization"])

        with tab_list:
            col_search, col_count = st.columns([5, 1], vertical_alignment="center")
            with col_search:
                search_query = st.text_input(
                    "Search Organizations",
                    placeholder="Filter by company name or slug...",
                    key="sa_org_search",
                    label_visibility="collapsed",
                )
            with col_count:
                pass

            filtered_orgs = orgs
            if search_query:
                sq = search_query.strip().lower()
                filtered_orgs = [o for o in orgs if sq in o["name"].lower() or sq in o["slug"].lower()]

            st.markdown(
                f"<div style='font-size: 13.5px; font-weight: 600; color: #334155; margin: 10px 0 12px 2px;'>Showing {len(filtered_orgs)} Organizations</div>",
                unsafe_allow_html=True,
            )

            if not filtered_orgs:
                st.info("No organizations matched your search filter.")

            for o in filtered_orgs:
                is_active = (o["status"] == "active")
                badge_bg = "#ECFDF5" if is_active else "#FEF2F2"
                badge_border = "#A7F3D0" if is_active else "#FECACA"
                badge_color = "#047857" if is_active else "#DC2626"
                badge_text = "● Active" if is_active else "● Suspended"

                with st.container(border=True):
                    col_info, col_status, col_stats, col_action = st.columns([3.8, 1.4, 3.4, 1.4], vertical_alignment="center")
                    with col_info:
                        root_tag = ""
                        if o.get("is_platform_org"):
                            root_tag = '<span style="font-size: 9.5px; background: #FEF3C7; color: #92400E; font-weight: 700; padding: 2px 6px; border-radius: 4px; border: 1px solid #FDE68A; margin-left: 6px;">ROOT</span>'
                        st.markdown(
                            f'<div style="display: flex; align-items: center; gap: 10px;">'
                            f'<div style="width: 38px; height: 38px; border-radius: 8px; background: #EFF6FF; border: 1px solid #DBEAFE; display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0;">🏢</div>'
                            f'<div>'
                            f'<div style="display: flex; align-items: center;"><span style="font-size: 15px; font-weight: 700; color: #0F172A; font-family: Outfit, sans-serif;">{o["name"]}</span>{root_tag}</div>'
                            f'<div style="font-size: 11.5px; color: #64748B; font-family: monospace; margin-top: 1px;">slug: <span style="color: #2563EB;">{o["slug"]}</span></div>'
                            f'</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                    with col_status:
                        st.markdown(
                            f'<div><span style="background: {badge_bg}; color: {badge_color}; border: 1px solid {badge_border}; font-weight: 700; font-size: 11px; padding: 3px 10px; border-radius: 9999px; display: inline-flex; align-items: center; gap: 4px; font-family: monospace; white-space: nowrap;">{badge_text}</span></div>',
                            unsafe_allow_html=True,
                        )
                    with col_stats:
                        st.markdown(
                            f'<div style="display: flex; gap: 14px; align-items: center; font-size: 12px; color: #334155; white-space: nowrap;">'
                            f'<div style="display: flex; align-items: center; gap: 4px;"><span style="color: #64748B;">👥</span> <strong>{o["member_count"]}</strong> <span style="color: #64748B; font-size: 11px;">members</span></div>'
                            f'<div style="display: flex; align-items: center; gap: 4px;"><span style="color: #64748B;">📋</span> <strong>{o["lead_count"]}</strong> <span style="color: #64748B; font-size: 11px;">leads</span></div>'
                            f'<div style="display: flex; align-items: center; gap: 4px;"><span style="color: #64748B;">✉️</span> <strong>{o["campaign_count"]}</strong> <span style="color: #64748B; font-size: 11px;">campaigns</span></div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                    with col_action:
                        if not o.get("is_platform_org"):
                            new_target_status = "suspended" if is_active else "active"
                            btn_label = "Suspend" if is_active else "Activate"
                            btn_t = "secondary" if is_active else "primary"
                            if st.button(btn_label, key=f"sa_btn_st_{o['id']}", type=btn_t, use_container_width=True):
                                set_organization_status(db, o["id"], new_target_status)
                                st.toast(f"Organization status changed to {new_target_status}", icon="🔄")
                                st.rerun()
                        else:
                            st.markdown(
                                '<div style="text-align: center; font-size: 11px; color: #94A3B8; font-weight: 600; padding: 6px 0;">Protected</div>',
                                unsafe_allow_html=True,
                            )

        with tab_create:
            with st.container(border=True):
                st.markdown(
                    '<div style="margin-bottom: 16px;">'
                    '<h3 style="font-size: 18px; font-weight: 700; color: #0F172A; margin: 0 0 4px 0; font-family: Outfit, sans-serif;">➕ Provision New Organization Workspace</h3>'
                    '<p style="font-size: 13px; color: #64748B; margin: 0;">Deploy an isolated multi-tenant organization with its own dedicated database scope, credentials, and owner account.</p>'
                    '</div>',
                    unsafe_allow_html=True,
                )

                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    p_name = st.text_input("Company Name*", key="sa_new_org_name", placeholder="e.g. Acme Corporation")
                    p_email = st.text_input("Primary Admin Email*", key="sa_new_email", placeholder="admin@acme.com")
                with col_f2:
                    p_fullname = st.text_input("Admin Full Name", key="sa_new_admin_name", placeholder="Jane Doe")
                    p_pwd = st.text_input("Temporary Password*", type="password", value="Welcome@2026!", key="sa_new_pwd")

                st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
                if st.button("🚀 Provision Organization Now", type="primary", key="sa_btn_provision"):
                    if not p_name or not p_email or not p_pwd:
                        st.error("Please fill in Company Name, Admin Email, and Password.")
                    else:
                        try:
                            res = register_organization_and_user(
                                db=db,
                                org_name=p_name,
                                admin_email=p_email,
                                password=p_pwd,
                                full_name=p_fullname,
                            )
                            st.toast(f"Successfully provisioned workspace '{p_name}'!", icon="🎉")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

    finally:
        db.close()

