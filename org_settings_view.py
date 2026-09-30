"""Organization Settings, Custom Branding & AI BYOK Configuration View.
"""

import streamlit as st
from Backend.db import SessionLocal
from Backend.auth_service import get_organization_by_id, update_organization_settings


def render_org_settings(organization_id: str):
    """Renders tenant organization settings panel."""
    db = SessionLocal()
    try:
        org = get_organization_by_id(db, organization_id)
        if not org:
            st.error("Organization not found.")
            return

        settings = org.settings or {}
        ai_cfg = settings.get("ai", {})
        sender_cfg = settings.get("sender", {})
        booking_cfg = settings.get("booking", {})

        col_hdr1, col_hdr2 = st.columns([3, 1])
        with col_hdr1:
            st.markdown(
                f"""
                <div style="margin-bottom: 20px;">
                    <h1 style="font-size: 28px; font-weight: 800; color: #0F172A; margin: 0 0 6px 0;">
                        ⚙️ Organization Settings: {org.name}
                    </h1>
                    <p style="font-size: 14px; color: #64748B; margin: 0;">
                        Manage your workspace branding, custom Bring-Your-Own-Key (BYOK) AI models, email senders, and calendar links.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_hdr2:
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            if st.button("👥 Manage Team Members", key="org_goto_team_view", use_container_width=True, help="Switch to Team Members view"):
                st.session_state.active_page = "team"
                st.query_params["page"] = "team"
                st.rerun()

        tab_branding, tab_ai, tab_sender, tab_booking, tab_team = st.tabs([
            "🎨 Branding & Identity",
            "🤖 AI & BYOK Intelligence",
            "✉️ Email Sender & Outbound",
            "📅 Calendar & Bookings",
            "👥 Team Members & RBAC",
        ])

        with tab_branding:
            st.markdown("### Workspace Branding & Identity")
            st.markdown("Customize your organization's display name, logo, and external presence across generated templates.")

            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Organization Legal Name", value=org.name or "", key="cfg_org_name")
                brand_name = st.text_input("Brand / Trade Name", value=org.brand_name or org.name or "", key="cfg_brand_name")
                website = st.text_input("Website URL", value=org.website or "", placeholder="https://example.com", key="cfg_website")

            with col2:
                logo_url = st.text_input("Logo Image URL (PNG/SVG/WebP)", value=org.logo_url or "", placeholder="https://...", key="cfg_logo_url")
                if logo_url:
                    st.image(logo_url, width=160, caption="Logo Preview")
                else:
                    st.info("💡 Provide a direct HTTPS link to your company logo for email banners.")

            if st.button("Save Branding Settings", type="primary", key="btn_save_branding"):
                update_organization_settings(
                    db=db,
                    org_id=organization_id,
                    name=name,
                    brand_name=brand_name,
                    logo_url=logo_url,
                    website=website,
                )
                st.session_state.current_org["name"] = name
                st.session_state.current_org["brand_name"] = brand_name
                st.session_state.current_org["logo_url"] = logo_url
                st.toast("Branding updated successfully!", icon="✅")
                st.rerun()

        with tab_ai:
            st.markdown("### Bring-Your-Own-Key (BYOK) & Custom AI Intelligence")
            st.markdown("Configure your own LLM API keys and model parameters, or use the platform default.")

            col_ai1, col_ai2 = st.columns(2)
            with col_ai1:
                provider_list = ["Google Gemini (Default)", "Anthropic Claude", "OpenAI", "Groq / OpenRouter"]
                prov_map = {
                    "Google Gemini (Default)": "gemini",
                    "Anthropic Claude": "claude",
                    "OpenAI": "openai",
                    "Groq / OpenRouter": "groq",
                }
                current_prov = ai_cfg.get("provider", "gemini")
                prov_idx = 0
                for idx, (lbl, val) in enumerate(prov_map.items()):
                    if val == current_prov:
                        prov_idx = idx
                        break

                selected_prov_label = st.selectbox("LLM Provider", provider_list, index=prov_idx, key="cfg_ai_prov")
                selected_provider = prov_map[selected_prov_label]

                model_options = {
                    "gemini": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-pro"],
                    "claude": ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"],
                    "openai": ["gpt-4o", "gpt-4o-mini", "o1-mini"],
                    "groq": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"],
                }
                curr_model = ai_cfg.get("model", model_options[selected_provider][0])
                model_idx = 0
                if curr_model in model_options[selected_provider]:
                    model_idx = model_options[selected_provider].index(curr_model)

                selected_model = st.selectbox("Primary Model", model_options[selected_provider], index=model_idx, key="cfg_ai_model")

                custom_api_key = st.text_input(
                    "Custom API Key (BYOK)",
                    value=ai_cfg.get("custom_api_key", ""),
                    type="password",
                    help="Leave blank to use platform-managed API keys.",
                    key="cfg_ai_key",
                )

            with col_ai2:
                tones = ["Professional & Executive", "Consultative & Analytical", "Direct & Concise", "Warm & Friendly", "Challenger / Value-Focused"]
                curr_tone = ai_cfg.get("tone", "Professional & Executive")
                tone_idx = tones.index(curr_tone) if curr_tone in tones else 0
                selected_tone = st.selectbox("Outreach Tone & Voice", tones, index=tone_idx, key="cfg_ai_tone")

                custom_prompt = st.text_area(
                    "Custom System Prompt Directives",
                    value=ai_cfg.get("custom_system_prompt", ""),
                    height=130,
                    placeholder="e.g. Always emphasize our 99.9% uptime SLA and SOC2 compliance. Never mention competitors.",
                    key="cfg_ai_prompt",
                )

            if st.button("Save AI & BYOK Configuration", type="primary", key="btn_save_ai"):
                update_organization_settings(
                    db=db,
                    org_id=organization_id,
                    ai_config={
                        "provider": selected_provider,
                        "model": selected_model,
                        "custom_api_key": custom_api_key,
                        "tone": selected_tone,
                        "custom_system_prompt": custom_prompt,
                    },
                )
                st.toast("AI settings saved successfully!", icon="🤖")
                st.rerun()

        with tab_sender:
            st.markdown("### Outbound Sender Configuration")
            st.markdown("Set up the sender email address and transmission channel for this organization.")

            col_s1, col_s2 = st.columns(2)
            with col_s1:
                send_provs = ["Microsoft Graph / Outlook 365 (Default)", "Custom SMTP Server", "SendGrid API"]
                s_map = {
                    "Microsoft Graph / Outlook 365 (Default)": "microsoft_graph",
                    "Custom SMTP Server": "smtp",
                    "SendGrid API": "sendgrid",
                }
                curr_s_prov = sender_cfg.get("provider", "microsoft_graph")
                s_idx = 0
                for idx, (lbl, val) in enumerate(s_map.items()):
                    if val == curr_s_prov:
                        s_idx = idx
                        break

                selected_s_label = st.selectbox("Email Delivery Engine", send_provs, index=s_idx, key="cfg_sender_prov")
                selected_s_provider = s_map[selected_s_label]

                sender_name = st.text_input("Sender Display Name", value=sender_cfg.get("sender_name", org.name or ""), key="cfg_sender_name")
                sender_email = st.text_input("Sender Email Address", value=sender_cfg.get("sender_email", org.email or ""), key="cfg_sender_email")

            with col_s2:
                if selected_s_provider == "smtp":
                    smtp_host = st.text_input("SMTP Host", value=sender_cfg.get("smtp_host", "smtp.office365.com"), key="cfg_smtp_host")
                    smtp_port = st.number_input("SMTP Port", value=sender_cfg.get("smtp_port", 587), key="cfg_smtp_port")
                    smtp_user = st.text_input("SMTP Username", value=sender_cfg.get("smtp_user", ""), key="cfg_smtp_user")
                    smtp_pwd = st.text_input("SMTP Password", value=sender_cfg.get("smtp_pwd", ""), type="password", key="cfg_smtp_pwd")
                elif selected_s_provider == "sendgrid":
                    sendgrid_key = st.text_input("SendGrid API Key", value=sender_cfg.get("sendgrid_key", ""), type="password", key="cfg_sendgrid_key")
                else:
                    st.info("⚡ **Microsoft Graph Integration**: Uses OAuth2 delegated application tokens to dispatch high-deliverability emails from your tenant's Outlook inbox.")

            if st.button("Save Sender Configuration", type="primary", key="btn_save_sender"):
                s_payload = {
                    "provider": selected_s_provider,
                    "sender_name": sender_name,
                    "sender_email": sender_email,
                }
                if selected_s_provider == "smtp":
                    s_payload.update({"smtp_host": smtp_host, "smtp_port": smtp_port, "smtp_user": smtp_user, "smtp_pwd": smtp_pwd})
                elif selected_s_provider == "sendgrid":
                    s_payload.update({"sendgrid_key": sendgrid_key})

                update_organization_settings(db=db, org_id=organization_id, sender_config=s_payload)
                st.toast("Sender settings saved!", icon="✉️")
                st.rerun()

        with tab_booking:
            st.markdown("### Calendar & Booking Integration")
            st.markdown("Configure appointment links that the AI agent dynamically proposes to qualified leads.")

            col_b1, col_b2 = st.columns(2)
            with col_b1:
                b_types = ["Microsoft Bookings", "Calendly", "Google Calendar / Meet", "Custom Scheduling Link"]
                curr_b_type = booking_cfg.get("type", "Microsoft Bookings")
                b_idx = b_types.index(curr_b_type) if curr_b_type in b_types else 0
                booking_type = st.selectbox("Calendar Engine", b_types, index=b_idx, key="cfg_booking_type")

                booking_url = st.text_input(
                    "Primary Booking URL",
                    value=booking_cfg.get("booking_link", "https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled"),
                    key="cfg_booking_link",
                )

            with col_b2:
                durations = [15, 30, 45, 60]
                curr_dur = booking_cfg.get("duration_minutes", 30)
                dur_idx = durations.index(curr_dur) if curr_dur in durations else 1
                duration = st.selectbox("Meeting Duration (Minutes)", durations, index=dur_idx, key="cfg_booking_dur")

            if st.button("Save Calendar Settings", type="primary", key="btn_save_booking"):
                update_organization_settings(
                    db=db,
                    org_id=organization_id,
                    booking_config={
                        "type": booking_type,
                        "booking_link": booking_url,
                        "duration_minutes": duration,
                    },
                )
                st.toast("Calendar configuration updated!", icon="📅")
                st.rerun()

        with tab_team:
            from team_view import render_team_view
            render_team_view(organization_id=organization_id, embedded=True)

    finally:
        db.close()
