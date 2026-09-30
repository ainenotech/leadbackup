"""SaaS Authentication & Tenant Selection View for Streamlit.

Provides executive Sign In, Sign Up / Onboarding, and Organization Switcher.
"""

import streamlit as st
from Backend.db import SessionLocal
from Backend.auth_service import (
    authenticate_user,
    register_organization_and_user,
    switch_organization,
    get_organization_by_id,
)
from Backend.auth_models import Organization, User


def render_auth_page():
    """Renders the executive login/signup screen if user is not authenticated."""
    st.markdown(
        """
        <style>
        .auth-container {
            max-width: 480px;
            margin: 40px auto 20px auto;
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 16px;
            padding: 36px 32px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.03);
        }
        .auth-logo-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: #EEF2FF;
            color: #4F46E5;
            padding: 6px 14px;
            border-radius: 9999px;
            font-size: 13px;
            font-weight: 600;
            margin-bottom: 16px;
        }
        .auth-title {
            font-size: 26px;
            font-weight: 800;
            color: #0F172A;
            letter-spacing: -0.02em;
            margin-bottom: 6px;
        }
        .auth-subtitle {
            font-size: 14px;
            color: #64748B;
            margin-bottom: 24px;
            line-height: 1.5;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            """
            <div style="text-align: center; margin-top: 20px;">
                <div class="auth-logo-badge">⚡ Universal Multi-Tenant SaaS</div>
                <div class="auth-title">Lead Intelligence & Outreach</div>
                <div class="auth-subtitle">Sign in to your organization workspace or create a new tenant</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        tab_login, tab_signup = st.tabs(["🔑 Sign In", "🚀 Register Organization"])

        with tab_login:
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            login_email = st.text_input("Work Email", value="mohit@nenotechnology.us", key="auth_login_email")
            login_pwd = st.text_input("Password", type="password", value="Admin@12345", key="auth_login_pwd", help="Default initial admin password or your custom password.")

            col_btn, col_demo = st.columns([1, 1])
            with col_btn:
                if st.button("Sign In to Workspace", type="primary", use_container_width=True, key="btn_do_login"):
                    if not login_email or not login_pwd:
                        st.error("Please enter both email and password.")
                    else:
                        db = SessionLocal()
                        try:
                            res = authenticate_user(db, login_email, login_pwd)
                            st.session_state.authenticated = True
                            st.session_state.user = res["user"]
                            st.session_state.current_org = res["organization"]
                            st.session_state.current_org_id = res["organization"]["id"]
                            st.session_state.user_organizations = res["organizations"]
                            st.session_state.access_token = res["access_token"]
                            st.toast(f"Welcome back, {res['user'].get('full_name')}!", icon="👋")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Login failed: {str(e)}")
                        finally:
                            db.close()

            with col_demo:
                if st.button("⚡ Quick 1-Click Login", type="secondary", use_container_width=True, key="btn_quick_login", help="Logs in directly as Neno Technology Admin"):
                    db = SessionLocal()
                    try:
                        res = authenticate_user(db, "mohit@nenotechnology.us", "Admin@12345")
                        st.session_state.authenticated = True
                        st.session_state.user = res["user"]
                        st.session_state.current_org = res["organization"]
                        st.session_state.current_org_id = res["organization"]["id"]
                        st.session_state.user_organizations = res["organizations"]
                        st.session_state.access_token = res["access_token"]
                        st.toast("Authenticated as Neno Technology Owner", icon="⚡")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Quick login failed: {str(e)}")
                    finally:
                        db.close()

        with tab_signup:
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            new_org_name = st.text_input("Organization / Company Name*", placeholder="e.g. Acme Corporation", key="reg_org_name")
            new_email = st.text_input("Admin Work Email*", placeholder="admin@acme.com", key="reg_email")
            new_pwd = st.text_input("Password*", type="password", key="reg_pwd")
            new_name = st.text_input("Your Full Name", placeholder="Jane Doe", key="reg_name")
            col_ind, col_sz = st.columns(2)
            with col_ind:
                new_industry = st.selectbox("Industry", ["Technology / SaaS", "Marketing & Agency", "Financial Services", "Healthcare", "Consulting", "Real Estate", "Other"], key="reg_industry")
            with col_sz:
                new_size = st.selectbox("Company Size", ["1-10", "11-50", "51-200", "201-500", "500+"], key="reg_size")

            if st.button("Create Organization Workspace", type="primary", use_container_width=True, key="btn_do_register"):
                if not new_org_name or not new_email or not new_pwd:
                    st.error("Please fill in Organization Name, Email, and Password.")
                elif len(new_pwd) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    db = SessionLocal()
                    try:
                        res = register_organization_and_user(
                            db=db,
                            org_name=new_org_name,
                            admin_email=new_email,
                            password=new_pwd,
                            full_name=new_name,
                            industry=new_industry,
                            company_size=new_size,
                        )
                        st.session_state.authenticated = True
                        st.session_state.user = res["user"]
                        st.session_state.current_org = res["organization"]
                        st.session_state.current_org_id = res["organization"]["id"]
                        st.session_state.user_organizations = [
                            {
                                "id": res["organization"]["id"],
                                "name": res["organization"]["name"],
                                "slug": res["organization"]["slug"],
                                "role": "organization_owner",
                                "is_default": True,
                            }
                        ]
                        st.session_state.access_token = res["access_token"]
                        st.balloons()
                        st.toast(f"Workspace '{new_org_name}' created successfully!", icon="🎉")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Registration error: {str(e)}")
                    finally:
                        db.close()


def render_org_switcher():
    """Renders tenant organization dropdown in the sidebar with dedicated workspace settings and team management inside a clean container box."""
    if not st.session_state.get("authenticated"):
        return

    user_orgs = st.session_state.get("user_organizations", [])
    current_org_id = st.session_state.get("current_org_id")

    if not user_orgs:
        return

    org_names = {o["id"]: o["name"] for o in user_orgs}
    current_idx = 0
    current_org_obj = user_orgs[0]
    for idx, o in enumerate(user_orgs):
        if o["id"] == current_org_id:
            current_idx = idx
            current_org_obj = o
            break

    user_role = current_org_obj.get("role", "regular_user")
    role_badge = {
        "organization_owner": "👑 Owner",
        "organization_admin": "🛡️ Admin",
        "campaign_manager": "🚀 Mgr",
        "sales_user": "💼 Sales",
        "regular_user": "👤 Member",
        "viewer": "👁️ Viewer",
    }.get(user_role, "Workspace")

    with st.container(border=True):
        st.markdown(
            f"""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <span style="font-family: 'Inter', sans-serif; font-size: 11px; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.04em;">
                    🏢 Workspace
                </span>
                <span style="font-size: 9.5px; background: #EFF6FF; color: #1D4ED8; font-weight: 700; padding: 1.5px 6px; border-radius: 4px; border: 1px solid #BFDBFE;">
                    {role_badge}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        selected_org_id = st.selectbox(
            "Active Organization",
            options=[o["id"] for o in user_orgs],
            index=current_idx,
            format_func=lambda x: org_names.get(x, x),
            label_visibility="collapsed",
            key="sb_tenant_select",
        )

        if selected_org_id != current_org_id:
            db = SessionLocal()
            try:
                res = switch_organization(db, st.session_state.user["id"], selected_org_id)
                st.session_state.current_org = res["organization"]
                st.session_state.current_org_id = res["organization"]["id"]
                st.session_state.access_token = res["access_token"]
                st.toast(f"Switched to {res['organization']['name']}", icon="🏢")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to switch organization: {e}")
            finally:
                db.close()

        # Workspace Management Actions inside the box (Full-width buttons with complete labels)
        active_page = st.session_state.get("active_page", "overview")

        is_settings = active_page == "org_settings"
        if st.button(
            "⚙️  Workspace Settings",
            key="ws_box_settings_btn",
            type="primary" if is_settings else "secondary",
            use_container_width=True,
            help="Configure Workspace Settings, Branding & AI BYOK",
        ):
            st.session_state.active_page = "org_settings"
            st.query_params["page"] = "org_settings"
            if "tab" in st.query_params:
                del st.query_params["tab"]
            if "feature" in st.query_params:
                del st.query_params["feature"]
            st.rerun()

        is_team = active_page == "team"
        if st.button(
            "👥  Team Members",
            key="ws_box_team_btn",
            type="primary" if is_team else "secondary",
            use_container_width=True,
            help="Manage Team Members & Access Roles",
        ):
            st.session_state.active_page = "team"
            st.query_params["page"] = "team"
            if "tab" in st.query_params:
                del st.query_params["tab"]
            if "feature" in st.query_params:
                del st.query_params["feature"]
            st.rerun()

