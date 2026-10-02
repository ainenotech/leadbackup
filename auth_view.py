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
                        st.session_state.active_sender_email = res["user"]["email"]
                        st.toast(f"Welcome back, {res['user'].get('full_name')}!", icon="👋")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Login failed: {str(e)}")
                    finally:
                        db.close()

            st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
            col_demo1, col_demo2, col_demo3 = st.columns(3)
            with col_demo1:
                if st.button("👑 Neno: Mohit Patel", type="secondary", use_container_width=True, key="btn_quick_mohit", help="Sign in as Neno Technology Owner (mohit@nenotechnology.us)"):
                    db = SessionLocal()
                    try:
                        res = authenticate_user(db, "mohit@nenotechnology.us", "Admin@12345")
                        st.session_state.authenticated = True
                        st.session_state.user = res["user"]
                        st.session_state.current_org = res["organization"]
                        st.session_state.current_org_id = res["organization"]["id"]
                        st.session_state.user_organizations = res["organizations"]
                        st.session_state.access_token = res["access_token"]
                        st.session_state.active_workspace_sender = "mohit@nenotechnology.us"
                        st.session_state.active_sender_email = "mohit@nenotechnology.us"
                        st.toast("Authenticated as Mohit Patel (👑 Owner)", icon="🏢")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Quick login failed: {str(e)}")
                    finally:
                        db.close()

            with col_demo2:
                if st.button("🛡️ Neno: Mit Patel", type="secondary", use_container_width=True, key="btn_quick_mitpatel", help="Sign in as Neno Technology Admin (mitpatel@nenotechnology.com)"):
                    db = SessionLocal()
                    try:
                        res = authenticate_user(db, "mitpatel@nenotechnology.com", "Admin@12345")
                        st.session_state.authenticated = True
                        st.session_state.user = res["user"]
                        st.session_state.current_org = res["organization"]
                        st.session_state.current_org_id = res["organization"]["id"]
                        st.session_state.user_organizations = res["organizations"]
                        st.session_state.access_token = res["access_token"]
                        st.session_state.active_workspace_sender = "mitpatel@nenotechnology.com"
                        st.session_state.active_sender_email = "mitpatel@nenotechnology.com"
                        st.toast("Authenticated as Mit Patel (🛡️ Admin)", icon="🛡️")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Quick login failed: {str(e)}")
                    finally:
                        db.close()

            with col_demo3:
                if st.button("🤖 Super AI: Mann", type="secondary", use_container_width=True, key="btn_quick_superai", help="Sign in as Super AI Owner (man@nenotechnology.com)"):
                    db = SessionLocal()
                    try:
                        res = authenticate_user(db, "man@nenotechnology.com", "Admin@12345")
                        st.session_state.authenticated = True
                        st.session_state.user = res["user"]
                        st.session_state.current_org = res["organization"]
                        st.session_state.current_org_id = res["organization"]["id"]
                        st.session_state.user_organizations = res["organizations"]
                        st.session_state.access_token = res["access_token"]
                        st.session_state.active_workspace_sender = "man@nenotechnology.com"
                        st.session_state.active_sender_email = "man@nenotechnology.com"
                        st.toast("Authenticated into Super AI (Owner: Mann)", icon="🤖")
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


@st.cache_data(ttl=60, show_spinner=False)
def get_workspace_senders(organization_id: str):
    """Retrieves all active sending identities for the given workspace, sorted by role priority."""
    if not organization_id:
        return []
    db = SessionLocal()
    try:
        from Backend.auth_models import Organization, OrganizationMember, User
        org = db.query(Organization).filter(Organization.id == organization_id).first()
        preferred_email = ""
        if org and org.settings:
            preferred_email = (
                org.settings.get("sender_email")
                or org.settings.get("sender", {}).get("sender_email")
                or ""
            ).lower().strip()
        if not preferred_email:
            preferred_email = os.getenv("MS_SENDER_EMAIL", "mohit@nenotechnology.us").lower().strip()

        members = (
            db.query(OrganizationMember, User)
            .join(User, OrganizationMember.user_id == User.id)
            .filter(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.status == "active",
                User.status == "active",
            )
            .all()
        )

        def _sender_priority(item):
            m, u = item
            u_email = (u.email or "").lower().strip()
            is_preferred = 0 if u_email == preferred_email or ("mohit" in u_email and "mohit" in preferred_email) else 1
            is_def = 0 if m.is_default else 1
            role_prio = 0 if m.role == "organization_owner" else (1 if m.role == "organization_admin" else 2)
            return (is_preferred, is_def, role_prio)

        sorted_members = sorted(members, key=_sender_priority)
        senders = []
        for m, u in sorted_members:
            if m.role in ("organization_owner", "organization_admin", "campaign_manager"):
                senders.append({
                    "email": u.email,
                    "name": u.full_name or u.email.split("@")[0],
                    "role": m.role,
                })
        return senders
    except Exception:
        return []
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

        if len(user_orgs) > 1:
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
                    if "active_workspace_sender" in st.session_state:
                        del st.session_state["active_workspace_sender"]
                    st.toast(f"Switched to {res['organization']['name']}", icon="🏢")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to switch organization: {e}")
                finally:
                    db.close()
        else:
            st.markdown(
                f"""
                <div style="font-size: 13.5px; font-weight: 700; color: #0F172A; padding: 2px 0 6px 0;">
                    {current_org_obj.get('name')}
                </div>
                """,
                unsafe_allow_html=True,
            )

        # ── Workspace Sender Setup (Silently Initialized) ──
        ws_senders = get_workspace_senders(current_org_id)
        if ws_senders:
            curr_active_ws = st.session_state.get("active_workspace_sender")
            if not curr_active_ws or curr_active_ws == "support@nenotechnology.com":
                st.session_state.active_workspace_sender = ws_senders[0]["email"]
                st.session_state.active_sender_email = ws_senders[0]["email"]

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

