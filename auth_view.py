"""SaaS Authentication & Tenant Selection View for Streamlit.

Provides executive Sign In, Sign Up / Organization Registration, and Organization Switcher.
Engineered specifically for pristine light-theme visibility, high contrast, and responsive centered card design.
"""

import os
import streamlit as st
import requests
from Backend.db import SessionLocal
from Backend.auth_service import (
    authenticate_user,
    register_organization_and_user,
    switch_organization,
    get_organization_by_id,
)
from Backend.auth_models import Organization, User


def render_auth_page():
    """Renders the executive, high-contrast, centered login & register card in pristine light theme."""
    # ── 1. Handle OAuth SSO Ticket Exchange (if returning from Microsoft / Google) ──
    ticket = st.query_params.get("login_ticket")
    if ticket:
        if "login_ticket" in st.query_params:
            del st.query_params["login_ticket"]
        with st.spinner("Completing secure sign in..."):
            try:
                resp = requests.post(
                    "http://localhost:8000/api/auth/oauth/exchange-ticket",
                    json={"login_ticket": ticket},
                    timeout=5,
                )
                if resp.status_code == 200:
                    res = resp.json()["data"]
                    st.session_state.authenticated = True
                    st.session_state.user = res["user"]
                    st.session_state.current_org = res["organization"]
                    st.session_state.current_org_id = res["organization"]["id"]
                    st.session_state.user_organizations = res.get("organizations", [res["organization"]])
                    st.session_state.access_token = res["access_token"]
                    st.session_state.active_sender_email = res["user"]["email"]
                    st.session_state.active_workspace_sender = res["user"]["email"]
                    st.session_state.show_onboarding = False
                    st.toast(f"Welcome back, {res['user'].get('full_name')}!", icon="👋")

                    import streamlit.components.v1 as components
                    components.html(
                        f"<script>document.cookie = 'session_token={res['access_token']}; path=/; max-age=2592000'; window.parent.location.href='/';</script>",
                        height=0,
                    )
                    st.rerun()
                else:
                    st.error(f"Sign in failed: {resp.json().get('detail', 'Unknown error')}")
            except Exception as e:
                st.error(f"Failed to communicate with authentication server: {str(e)}")

    # ── 2. Master Executive Light-Theme CSS ──
    st.markdown(
        """
        <style>
        /* Hide sidebar and Streamlit headers during login */
        [data-testid="stSidebar"] { display: none !important; }
        [data-testid="stSidebarNav"] { display: none !important; }
        [data-testid="stExpandSidebarButton"] { display: none !important; }
        #MainMenu { visibility: hidden !important; }
        header { visibility: hidden !important; }
        footer { visibility: hidden !important; }

        /* Canvas Backdrop with subtle ambient depth */
        .stApp {
            background: radial-gradient(at 0% 0%, #EEF2FF 0px, transparent 50%),
                        radial-gradient(at 100% 0%, #F5F3FF 0px, transparent 50%),
                        radial-gradient(at 50% 100%, #E2E8F0 0px, transparent 60%),
                        #F8FAFC !important;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        }

        /* Center Card Box Constraints */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: #FFFFFF !important;
            border: 1.5px solid #E2E8F0 !important;
            border-radius: 22px !important;
            padding: 34px 34px 30px 34px !important;
            box-shadow: 0 20px 35px -10px rgba(15, 23, 42, 0.08),
                        0 1px 3px 0 rgba(0, 0, 0, 0.04),
                        0 0 0 1px rgba(226, 232, 240, 0.8) !important;
            max-width: 470px !important;
            margin: 20px auto 40px auto !important;
        }

        /* Segmented / Pill-Style Tabs */
        div[data-testid="stTabs"] {
            margin-bottom: 16px !important;
        }

        div[data-testid="stTabs"] [role="tablist"] {
            background: #F1F5F9 !important;
            padding: 4px !important;
            border-radius: 12px !important;
            border: 1px solid #E2E8F0 !important;
            gap: 4px !important;
            justify-content: center !important;
        }

        div[data-testid="stTabs"] button[role="tab"] {
            flex: 1 !important;
            text-align: center !important;
            border-radius: 9px !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 13.5px !important;
            font-weight: 600 !important;
            color: #64748B !important;
            padding: 8px 16px !important;
            border: none !important;
            background: transparent !important;
            transition: all 0.15s ease !important;
        }

        div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
            background: #FFFFFF !important;
            color: #0F172A !important;
            font-weight: 700 !important;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08), 0 1px 2px rgba(0, 0, 0, 0.04) !important;
        }

        div[data-testid="stTabs"] button[role="tab"]:hover {
            color: #0F172A !important;
        }

        /* High-Definition Input Labels */
        div[data-testid="stTextInput"] label p {
            font-family: 'Inter', sans-serif !important;
            font-size: 13.5px !important;
            font-weight: 700 !important;
            color: #0F172A !important;
            margin-bottom: 5px !important;
            letter-spacing: -0.01em !important;
        }

        /* High-Visibility Crisp Inputs */
        div[data-testid="stTextInput"] input {
            background-color: #FFFFFF !important;
            border: 1.5px solid #CBD5E1 !important;
            border-radius: 10px !important;
            color: #0F172A !important;
            font-size: 14.5px !important;
            font-weight: 500 !important;
            padding: 11px 14px !important;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04) !important;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        }

        div[data-testid="stTextInput"] input:focus {
            background-color: #FFFFFF !important;
            border-color: #2563EB !important;
            box-shadow: 0 0 0 3.5px rgba(37, 99, 235, 0.16) !important;
            outline: none !important;
        }

        div[data-testid="stTextInput"] input::placeholder {
            color: #94A3B8 !important;
            font-size: 13.5px !important;
        }

        /* Primary High-Impact CTA Button */
        button[kind="primary"] {
            background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
            color: #FFFFFF !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 14.5px !important;
            font-weight: 700 !important;
            padding: 12px 20px !important;
            border-radius: 10px !important;
            border: none !important;
            box-shadow: 0 4px 14px rgba(37, 99, 235, 0.28) !important;
            letter-spacing: -0.01em !important;
            margin-top: 6px !important;
            transition: all 0.2s ease !important;
        }

        button[kind="primary"]:hover {
            background: linear-gradient(135deg, #1D4ED8 0%, #1E40AF 100%) !important;
            box-shadow: 0 6px 18px rgba(37, 99, 235, 0.38) !important;
            transform: translateY(-1px) !important;
        }

        /* SSO Links */
        .stLinkButton > a {
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            background: #FFFFFF !important;
            color: #1E293B !important;
            border: 1.5px solid #E2E8F0 !important;
            border-radius: 10px !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 12.5px !important;
            font-weight: 600 !important;
            padding: 9px 12px !important;
            text-decoration: none !important;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03) !important;
            transition: all 0.2s ease !important;
        }

        .stLinkButton > a:hover {
            background: #F8FAFC !important;
            border-color: #CBD5E1 !important;
            color: #0F172A !important;
            transform: translateY(-1px) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ── 3. Centered Layout Column ──
    col_l, col_center, col_r = st.columns([1, 1.4, 1])

    with col_center:
        with st.container(border=True):
            # Brand Header inside Center Box
            st.markdown(
                """
                <div style="text-align: center; margin-bottom: 4px;">
                    <div style="display: inline-flex; align-items: center; gap: 6px; background: #EFF6FF; border: 1px solid #BFDBFE; color: #1D4ED8; font-size: 11px; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase; padding: 4px 12px; border-radius: 9999px; margin-bottom: 12px;">
                        ⚡ AINeotechnology Enterprise
                    </div>
                    <div style="font-size: 26px; font-weight: 800; color: #0F172A; letter-spacing: -0.03em; margin-bottom: 4px; line-height: 1.25;">
                        Welcome to <span style="background: linear-gradient(135deg, #2563EB 0%, #7C3AED 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">AINeo</span>
                    </div>
                    <div style="font-size: 13.5px; color: #64748B; margin-bottom: 18px; line-height: 1.5;">
                        Autonomous lead intelligence and high-deliverability outreach suite.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Navigation Tabs: Sign In vs Register
            tab_signin, tab_register = st.tabs(["🔑 Sign In", "🚀 Register Workspace"])

            # ─────────────────────────────────────────────────────────────
            # TAB 1: SIGN IN (Standard Credentials)
            # ─────────────────────────────────────────────────────────────
            with tab_signin:
                st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)

                # Organization Context Badge
                st.markdown(
                    """
                    <div style="background: #F8FAFC; border: 1.5px solid #E2E8F0; border-radius: 10px; padding: 10px 14px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span style="font-size: 16px;">🏢</span>
                            <div>
                                <div style="font-size: 13px; font-weight: 700; color: #0F172A;">Neno Technology</div>
                                <div style="font-size: 11px; color: #64748B;">Workspace: nenotechnology</div>
                            </div>
                        </div>
                        <span style="background: #EFF6FF; color: #1D4ED8; font-size: 10.5px; font-weight: 700; padding: 4px 10px; border-radius: 6px; border: 1px solid #BFDBFE; white-space: nowrap; display: inline-flex; align-items: center; gap: 4px;">
                            👑 Owner Active
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                login_email = st.text_input(
                    "Work Email Address",
                    value="mohit@nenotechnology.us",
                    placeholder="name@company.com",
                    key="auth_signin_email",
                )

                login_pwd = st.text_input(
                    "Password",
                    type="password",
                    value="Admin@12345",
                    placeholder="••••••••••••",
                    key="auth_signin_pwd",
                    help="Enter your workspace password (Default: Admin@12345)",
                )

                if st.button("Sign In to Workspace  →", type="primary", use_container_width=True, key="btn_signin_submit"):
                    if not login_email or not login_pwd:
                        st.error("Please enter both work email and password.")
                    else:
                        db = SessionLocal()
                        try:
                            res = authenticate_user(db, login_email.strip(), login_pwd)
                            st.session_state.authenticated = True
                            st.session_state.user = res["user"]
                            st.session_state.current_org = res["organization"]
                            st.session_state.current_org_id = res["organization"]["id"]
                            st.session_state.user_organizations = res.get("organizations", [res["organization"]])
                            st.session_state.access_token = res["access_token"]
                            st.session_state.active_sender_email = res["user"]["email"]
                            st.session_state.active_workspace_sender = res["user"]["email"]
                            st.session_state.show_onboarding = False
                            st.toast(f"Welcome back, {res['user'].get('full_name')}!", icon="👋")

                            import streamlit.components.v1 as components
                            components.html(
                                f"<script>document.cookie = 'session_token={res['access_token']}; path=/; max-age=2592000'; window.parent.location.href='/';</script>",
                                height=0,
                            )
                            st.rerun()
                        except Exception as e:
                            st.error(f"Sign in failed: {str(e)}")
                        finally:
                            db.close()

                # SSO Divider & Buttons
                st.markdown(
                    """
                    <div style="display: flex; align-items: center; text-align: center; margin: 20px 0 12px 0; color: #94A3B8; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">
                        <span style="flex: 1; border-bottom: 1px solid #E2E8F0;"></span>
                        <span style="padding: 0 10px;">or continue with SSO</span>
                        <span style="flex: 1; border-bottom: 1px solid #E2E8F0;"></span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                col_sso1, col_sso2 = st.columns(2)
                with col_sso1:
                    st.link_button("Microsoft 365", "http://localhost:8000/api/auth/oauth/microsoft/login", use_container_width=True)
                with col_sso2:
                    st.link_button("Google Workspace", "http://localhost:8000/api/auth/oauth/google/login", use_container_width=True)

            # ─────────────────────────────────────────────────────────────
            # TAB 2: REGISTER (Create New Workspace)
            # ─────────────────────────────────────────────────────────────
            with tab_register:
                st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)

                reg_name = st.text_input("Your Full Name *", placeholder="Mohit Patel", key="reg_full_name")
                reg_email = st.text_input("Work Email Address *", placeholder="mohit@nenotechnology.us", key="reg_email")
                reg_org_name = st.text_input("Company or Organization Name *", placeholder="Neno Technology", key="reg_org_name")

                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    reg_pwd = st.text_input("Password *", type="password", placeholder="Min 6 chars", key="reg_pwd")
                with col_p2:
                    reg_pwd_confirm = st.text_input("Confirm Password *", type="password", placeholder="Re-enter password", key="reg_pwd_confirm")

                if st.button("Create Account & Launch Workspace  →", type="primary", use_container_width=True, key="btn_register_submit"):
                    if not reg_name or not reg_email or not reg_org_name or not reg_pwd:
                        st.error("Please fill in all required fields marked with *.")
                    elif len(reg_pwd) < 6:
                        st.error("Password must be at least 6 characters long.")
                    elif reg_pwd != reg_pwd_confirm:
                        st.error("Passwords do not match. Please re-check.")
                    else:
                        db = SessionLocal()
                        try:
                            res = register_organization_and_user(
                                db=db,
                                org_name=reg_org_name.strip(),
                                admin_email=reg_email.strip().lower(),
                                password=reg_pwd,
                                full_name=reg_name.strip(),
                            )
                            st.session_state.authenticated = True
                            st.session_state.user = res["user"]
                            st.session_state.current_org = res["organization"]
                            st.session_state.current_org_id = res["organization"]["id"]
                            st.session_state.user_organizations = [res["organization"]]
                            st.session_state.access_token = res["access_token"]
                            st.session_state.active_sender_email = res["user"]["email"]
                            st.session_state.active_workspace_sender = res["user"]["email"]
                            st.session_state.show_onboarding = False

                            st.toast(f"Workspace '{reg_org_name}' created successfully!", icon="🎉")
                            import streamlit.components.v1 as components
                            components.html(
                                f"<script>document.cookie = 'session_token={res['access_token']}; path=/; max-age=2592000'; window.parent.location.href='/';</script>",
                                height=0,
                            )
                            st.rerun()
                        except Exception as e:
                            st.error(f"Registration failed: {str(e)}")
                        finally:
                            db.close()

            # Enterprise Security Guarantee
            st.markdown(
                """
                <div style="text-align: center; margin-top: 22px; padding-top: 14px; border-top: 1px solid #F1F5F9; font-size: 11.5px; color: #94A3B8; line-height: 1.5;">
                    🔒 <strong>Enterprise Multi-Tenant Security</strong> · AES-256 Workspace Isolation<br>
                    Protected by AINeotechnology Autonomous Infrastructure
                </div>
                """,
                unsafe_allow_html=True,
            )


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

        # Workspace Management Actions inside the box
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
