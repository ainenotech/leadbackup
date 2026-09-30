"""Team Management & Multi-Tenant RBAC View.
"""

import streamlit as st
from Backend.db import SessionLocal
from Backend.auth_service import (
    get_org_members,
    invite_org_member,
    update_member_role,
    remove_org_member,
)


def render_team_view(organization_id: str, embedded: bool = False):
    """Renders the organization team members and RBAC controls."""
    db = SessionLocal()
    try:
        members = get_org_members(db, organization_id)
        current_user_id = st.session_state.get("user", {}).get("id")
        user_role = st.session_state.get("current_org", {}).get("role", "regular_user")
        is_admin_or_owner = user_role in ("organization_owner", "organization_admin") or st.session_state.get("user", {}).get("platform_role") == "platform_super_admin"

        if not embedded:
            col_hdr1, col_hdr2 = st.columns([3, 1])
            with col_hdr1:
                st.markdown(
                    f"""
                    <div style="margin-bottom: 20px;">
                        <h1 style="font-size: 28px; font-weight: 800; color: #0F172A; margin: 0 0 6px 0;">
                            👥 Team Members &amp; Access Controls
                        </h1>
                        <p style="font-size: 14px; color: #64748B; margin: 0;">
                            Manage team permissions, role-based access control (RBAC), and invite colleagues to this workspace.
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with col_hdr2:
                st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
                if st.button("⚙️ Workspace Settings", key="team_goto_ws_settings", use_container_width=True, help="Switch to Workspace Settings"):
                    st.session_state.active_page = "org_settings"
                    st.query_params["page"] = "org_settings"
                    st.rerun()

        col_top1, col_top2 = st.columns([3, 1])
        with col_top1:
            st.markdown(f"**Total Workspace Members:** `{len(members)}`")
        with col_top2:
            pass

        # Invite Member Section
        if is_admin_or_owner:
            with st.expander("➕ Invite New Team Member", expanded=False):
                col_i1, col_i2, col_i3 = st.columns([2, 2, 2])
                with col_i1:
                    inv_email = st.text_input("Colleague Work Email*", placeholder="alex@company.com", key="inv_email")
                with col_i2:
                    inv_name = st.text_input("Full Name", placeholder="Alex Rivera", key="inv_name")
                with col_i3:
                    inv_role = st.selectbox(
                        "Workspace Role*",
                        [
                            "regular_user",
                            "campaign_manager",
                            "sales_user",
                            "organization_admin",
                            "viewer",
                        ],
                        format_func=lambda x: {
                            "regular_user": "Regular User",
                            "campaign_manager": "Campaign Manager",
                            "sales_user": "Sales User",
                            "organization_admin": "Organization Admin",
                            "viewer": "Viewer (Read Only)",
                        }.get(x, x),
                        key="inv_role",
                    )

                inv_pwd = st.text_input("Initial Password (Optional)", type="password", placeholder="Welcome@2026!", key="inv_pwd")

                if st.button("Send Workspace Invitation", type="primary", key="btn_send_inv"):
                    if not inv_email:
                        st.error("Please enter a valid work email.")
                    else:
                        try:
                            res = invite_org_member(
                                db=db,
                                org_id=organization_id,
                                invited_by_user_id=current_user_id,
                                email=inv_email,
                                role=inv_role,
                                full_name=inv_name,
                                temporary_password=inv_pwd if inv_pwd else None,
                            )
                            st.toast(f"Successfully added {inv_email} as {inv_role}!", icon="🎉")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to invite: {e}")

        # Member list table
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        st.markdown("### Active Workspace Members")

        ROLE_BADGES = {
            "organization_owner": ("👑 Owner", "#7C3AED", "#EDE9FE"),
            "organization_admin": ("🛡️ Admin", "#2563EB", "#DBEAFE"),
            "campaign_manager": ("🚀 Campaign Mgr", "#059669", "#D1FAE5"),
            "sales_user": ("💼 Sales User", "#D97706", "#FEF3C7"),
            "regular_user": ("👤 Member", "#475569", "#F1F5F9"),
            "viewer": ("👁️ Viewer", "#64748B", "#F8FAFC"),
        }

        for m in members:
            b_label, b_color, b_bg = ROLE_BADGES.get(m["role"], ("Member", "#475569", "#F1F5F9"))
            is_me = (m["user_id"] == current_user_id)
            me_tag = " <span style='font-size: 11px; color: #2563EB; font-weight: 600;'>(You)</span>" if is_me else ""

            col_m1, col_m2, col_m3 = st.columns([4, 2, 2])
            with col_m1:
                st.markdown(
                    f"""
                    <div style="padding: 10px 0;">
                        <strong style="font-size: 15px; color: #0F172A;">{m['full_name']}</strong>{me_tag}
                        <div style="font-size: 12.5px; color: #64748B;">{m['email']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with col_m2:
                st.markdown(
                    f"""
                    <div style="padding: 12px 0;">
                        <span style="background: {b_bg}; color: {b_color}; font-weight: 700; font-size: 12px; padding: 4px 10px; border-radius: 9999px;">
                            {b_label}
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with col_m3:
                if is_admin_or_owner and not is_me:
                    col_act1, col_act2 = st.columns(2)
                    with col_act1:
                        pass
                    with col_act2:
                        if st.button("Remove", key=f"btn_rem_{m['user_id']}", type="secondary", help="Remove member from this organization"):
                            try:
                                remove_org_member(db, organization_id, m["user_id"])
                                st.toast(f"Removed {m['full_name']}", icon="🗑️")
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))
                else:
                    st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)

            st.markdown("<hr style='border: none; border-top: 1px solid #F1F5F9; margin: 4px 0 10px 0;'>", unsafe_allow_html=True)

    finally:
        db.close()
