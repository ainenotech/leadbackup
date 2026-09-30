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
    """Renders platform-wide super admin control center."""
    user = st.session_state.get("user", {})
    if user.get("platform_role") != "platform_super_admin":
        st.error("⛔ Access Denied: You must be a Platform Super Administrator to view this portal.")
        return

    db = SessionLocal()
    try:
        overview = get_platform_admin_overview(db)
        metrics = overview.get("metrics", {})
        orgs = overview.get("organizations", [])

        st.markdown(
            """
            <div style="margin-bottom: 24px;">
                <div style="display: inline-block; background: #FEF3C7; color: #D97706; font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 9999px; text-transform: uppercase; margin-bottom: 8px;">
                    👑 Platform Super Admin
                </div>
                <h1 style="font-size: 28px; font-weight: 800; color: #0F172A; margin: 0 0 6px 0;">
                    Global SaaS Operations Center
                </h1>
                <p style="font-size: 14px; color: #64748B; margin: 0;">
                    Platform-wide telemetry, cross-tenant auditing, and organization workspace controls.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Global KPIs
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Organizations", metrics.get("total_organizations", 0))
        c2.metric("Active Workspaces", metrics.get("active_organizations", 0))
        c3.metric("Platform Users", metrics.get("total_users", 0))
        c4.metric("Total System Leads", metrics.get("total_leads", 0))
        c5.metric("Outreach Logs", metrics.get("total_campaign_logs", 0))
        c6.metric("RAG Documents", metrics.get("total_kb_docs", 0))

        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

        tab_list, tab_create = st.tabs(["🏢 All Organizations", "➕ Provision New Organization"])

        with tab_list:
            search_query = st.text_input("🔍 Search Organizations", placeholder="Filter by company name or slug...", key="sa_org_search")

            filtered_orgs = orgs
            if search_query:
                sq = search_query.strip().lower()
                filtered_orgs = [o for o in orgs if sq in o["name"].lower() or sq in o["slug"].lower()]

            st.markdown(f"**Showing {len(filtered_orgs)} Organizations**")

            for o in filtered_orgs:
                is_active = (o["status"] == "active")
                badge_bg = "#D1FAE5" if is_active else "#FEE2E2"
                badge_color = "#059669" if is_active else "#DC2626"
                badge_text = "● Active" if is_active else "● Suspended"

                col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 2])
                with col1:
                    st.markdown(
                        f"""
                        <div style="padding: 6px 0;">
                            <strong style="font-size: 15px; color: #0F172A;">{o['name']}</strong>
                            <div style="font-size: 11.5px; color: #64748B; font-family: monospace;">slug: {o['slug']}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with col2:
                    st.markdown(
                        f"""
                        <div style="padding: 10px 0;">
                            <span style="background: {badge_bg}; color: {badge_color}; font-weight: 700; font-size: 11.5px; padding: 3px 9px; border-radius: 9999px;">
                                {badge_text}
                            </span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with col3:
                    st.markdown(
                        f"""
                        <div style="font-size: 12.5px; color: #334155; padding: 10px 0;">
                            👥 <strong>{o['member_count']}</strong> members<br>
                            📋 <strong>{o['lead_count']}</strong> leads
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with col4:
                    st.markdown(
                        f"""
                        <div style="font-size: 12.5px; color: #334155; padding: 10px 0;">
                            ✉️ <strong>{o['campaign_count']}</strong> campaigns
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with col5:
                    if not o.get("is_platform_org"):
                        new_target_status = "suspended" if is_active else "active"
                        btn_label = "Suspend" if is_active else "Activate"
                        btn_t = "secondary" if is_active else "primary"
                        if st.button(btn_label, key=f"sa_btn_st_{o['id']}", type=btn_t):
                            set_organization_status(db, o["id"], new_target_status)
                            st.toast(f"Organization status changed to {new_target_status}", icon="🔄")
                            st.rerun()

                st.markdown("<hr style='border: none; border-top: 1px solid #F1F5F9; margin: 4px 0 10px 0;'>", unsafe_allow_html=True)

        with tab_create:
            st.markdown("### Provision New Organization")
            p_name = st.text_input("Company Name*", key="sa_new_org_name")
            p_email = st.text_input("Primary Admin Email*", key="sa_new_email")
            p_pwd = st.text_input("Temporary Password*", type="password", value="Welcome@2026!", key="sa_new_pwd")
            p_fullname = st.text_input("Admin Full Name", key="sa_new_admin_name")

            if st.button("Provision Organization Now", type="primary", key="sa_btn_provision"):
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
