from datetime import date
import os
import pandas as pd
import streamlit as st
from Backend.db import SessionLocal
from Backend.auth_service import get_organization_by_id, update_organization_settings
from Backend.auth_models import OrganizationMember, User

from Backend.channels_models import OrgMailConnection, OrgDomainSnapshot
from Backend.domain_models import (

    OrgSendingDomain,
    OrgDomainRecord,
    OrgDomainStats,
    OrgDomainCheckHistory,
)
from services.domain_auth_service import (
    register_domain,
    verify_domain,
    list_domains,
    get_domain_detail,
    update_domain,
    pause_domain,
    resume_domain,
    delete_domain,
    get_dns_instructions,
    get_check_history,
    is_mock_provider,
)



def render_email_channels_chooser(organization_id: str, context: str = "settings"):
    st.markdown("### 📬 Email Channels")
    st.markdown("Select or connect your preferred email delivery channel for outreach.")
    
    email = st.text_input("Enter your sender email address to detect the best connection method", key=f"detect_email_{context}")
    
    if st.button("Detect Method", key=f"btn_detect_{context}"):
        if not email or "@" not in email:
            st.error("Please enter a valid email address.")
            return
            
        try:
            from services.dns_health import full_dns_check
            
            domain = email.split("@")[1].lower()
            dns_report = full_dns_check(domain)
            mx_records = dns_report.mx.records if dns_report.mx else []
            spf_record = dns_report.spf.raw_records[0] if dns_report.spf and dns_report.spf.raw_records else None
            dmarc_record = dns_report.dmarc.raw_record if dns_report.dmarc else None
            
            recommendation = "unknown, choose manually"
            is_consumer = False
            
            if domain in ("gmail.com", "outlook.com", "hotmail.com", "yahoo.com"):
                is_consumer = True
                recommendation = "own_domain" if domain in ("yahoo.com",) else ("google_oauth" if domain == "gmail.com" else "microsoft_oauth")
            elif not mx_records:
                recommendation = "own_domain"
            else:
                mx_text = " ".join([mx.lower() for mx in mx_records])
                if "google.com" in mx_text or "googlemail.com" in mx_text:
                    recommendation = "google_oauth"
                elif "protection.outlook.com" in mx_text:
                    recommendation = "microsoft_oauth"
                elif "mimecast.com" in mx_text or "proofpoint.com" in mx_text or "messagelabs.com" in mx_text:
                    recommendation = "unknown, choose manually"
                else:
                    recommendation = "smtp_imap"

            db = SessionLocal()
            try:
                db.add(OrgDomainSnapshot(
                    organization_id=organization_id,
                    domain=domain,
                    results={
                        "mx": mx_records,
                        "spf": spf_record,
                        "dkim_detected": False,
                        "dmarc": dmarc_record,
                    }
                ))
                db.commit()
            except Exception:
                pass
            finally:
                db.close()
                
            st.session_state[f"detected_channel_{context}"] = recommendation
            st.session_state[f"detected_consumer_{context}"] = is_consumer
        except Exception as e:
            st.error(f"Detection failed: {e}")

    recommendation = st.session_state.get(f"detected_channel_{context}")
    if recommendation:
        st.success(f"Recommended Method: **{recommendation}**")
        if st.session_state.get(f"detected_consumer_{context}"):
            st.warning("This looks like a personal mailbox. Strict daily caps will apply to protect your reputation.")
            
        st.markdown("#### Connect a Channel")
        selected = st.radio(
            "Select Channel Method", 
            ["microsoft_oauth", "google_oauth", "smtp_imap", "own_domain", "customer_domain"],
            index=["microsoft_oauth", "google_oauth", "smtp_imap", "own_domain", "customer_domain"].index(recommendation) if recommendation in ["microsoft_oauth", "google_oauth", "smtp_imap", "own_domain", "customer_domain"] else 0,
            key=f"radio_{context}"
        )
        
        if selected == "microsoft_oauth":
            st.markdown("#### Microsoft 365 / Outlook Integration")
            st.markdown("We will request the following permissions from your Microsoft account:")
            st.markdown("- **Mail.Send**: To dispatch outreach emails from your mailbox.")
            st.markdown("- **Mail.Read**: To read replies specifically matching our campaigns.")
            st.markdown("- **User.Read**: To verify your identity.")
            
            if st.button("Generate Connection Link", key=f"btn_gen_{context}"):
                if not email or "@" not in email:
                    st.error("Please enter a valid sender email address above first.")
                else:
                    import requests
                    token = st.session_state.get("access_token")
                    if not token and st.session_state.get("user"):
                        from Backend.auth_service import create_access_token
                        u = st.session_state.get("user", {})
                        token = create_access_token(
                            user_id=u.get("id"),
                            org_id=organization_id,
                            role=st.session_state.get("current_org", {}).get("role", "organization_owner"),
                            email=u.get("email", ""),
                            platform_role=u.get("platform_role", "user"),
                        )
                        st.session_state.access_token = token
                    
                    base_url = (os.getenv("FORM_BASE_URL") or "http://localhost:8000").rstrip('/')
                    
                    try:
                        resp = requests.post(
                            f"{base_url}/api/channels/oauth/microsoft/start",
                            json={"email": email.strip()},
                            headers={"Authorization": f"Bearer {token}"} if token else {},
                            timeout=15
                        )
                        if resp.status_code == 200:
                            auth_url = resp.json().get("auth_url")
                            st.markdown(f'<a href="{auth_url}" target="_blank" style="display: inline-block; background-color: #0f172a; color: white; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: 500;">Connect with Microsoft</a>', unsafe_allow_html=True)
                            st.info("Click the button above to sign in. It will open in a new tab. Once you see the success message, click below to refresh.")
                            if st.button("Refresh Connection Status"):
                                st.rerun()
                        else:
                            st.error(f"Failed to start connection ({resp.status_code}): {resp.text}")
                    except Exception as e:
                        st.error(f"Could not reach API server: {e}")
        elif selected == "google_oauth":
            st.markdown("#### Google Workspace / Gmail Integration")
            st.markdown("We will request the following permissions from your Google account:")
            st.markdown("- **Send Emails**: To dispatch outreach emails from your mailbox (gmail.send).")
            st.markdown("- **Read Emails**: To read replies specifically matching our campaigns (gmail.readonly).")
            st.markdown("- **Basic Profile**: To verify your email identity.")
            
            if st.button("Generate Connection Link", key=f"btn_gen_{context}"):
                if not email or "@" not in email:
                    st.error("Please enter a valid sender email address above first.")
                else:
                    import requests
                    token = st.session_state.get("access_token")
                    if not token and st.session_state.get("user"):
                        from Backend.auth_service import create_access_token
                        u = st.session_state.get("user", {})
                        token = create_access_token(
                            user_id=u.get("id"),
                            org_id=organization_id,
                            role=st.session_state.get("current_org", {}).get("role", "organization_owner"),
                            email=u.get("email", ""),
                            platform_role=u.get("platform_role", "user"),
                        )
                        st.session_state.access_token = token

                    base_url = (os.getenv("FORM_BASE_URL") or "http://localhost:8000").rstrip('/')
                    
                    try:
                        resp = requests.post(
                            f"{base_url}/api/channels/oauth/google/start",
                            json={"email": email.strip()},
                            headers={"Authorization": f"Bearer {token}"} if token else {},
                            timeout=15
                        )
                        if resp.status_code == 200:
                            auth_url = resp.json().get("auth_url")
                            st.markdown(f'<a href="{auth_url}" target="_blank" style="display: inline-block; background-color: #0f172a; color: white; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: 500;">Connect with Google</a>', unsafe_allow_html=True)
                            st.info("Click the button above to sign in. It will open in a new tab. Once you see the success message, click below to refresh.")
                            if st.button("Refresh Connection Status"):
                                st.rerun()
                        else:
                            st.error(f"Failed to start connection ({resp.status_code}): {resp.text}")
                    except Exception as e:
                        st.error(f"Could not reach API server: {e}")
        else:
            if st.button("Connect Selected Channel", key=f"btn_connect_{context}"):
                st.info(f"The {selected} channel is registered but not yet available.")
            
    if context == "settings":
        db = SessionLocal()
        try:
            connections = db.query(OrgMailConnection).filter(OrgMailConnection.organization_id == organization_id).all()
            if connections:
                st.markdown("#### Configured Connections")
                for c in connections:
                    st.markdown(f"**{c.email}** ({c.channel})")
                    if c.status == "needs_reconnect":
                        st.error("Status: Needs Reconnect (Authentication expired or revoked)")
                    elif c.status == "active":
                        st.success(f"Status: Active (Sent today: {c.sent_today}/{c.daily_cap})")
                    else:
                        st.info(f"Status: {c.status}")
                        
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        if c.channel in ("microsoft_oauth", "google_oauth") and c.status == "active":
                            if st.button("Test Send", key=f"btn_test_{c.id}"):
                                from Email.channels import get_channel_handler
                                try:
                                    handler = get_channel_handler(c.channel)
                                    # Send to self
                                    res = handler.send_email(
                                        db=db, 
                                        connection=c, 
                                        to_email=c.email, 
                                        subject="Connection Test", 
                                        body_html="<p>This is a test email confirming your channel is connected.</p>",
                                        body_text="This is a test email confirming your channel is connected."
                                    )
                                    st.toast("Test email sent!", icon="✅")
                                except Exception as e:
                                    st.error(f"Test send failed: {e}")
                    with col_b:
                        new_cap = st.number_input("Daily Cap", value=c.daily_cap, min_value=1, key=f"cap_{c.id}")
                        if new_cap != c.daily_cap:
                            c.daily_cap = new_cap
                            db.commit()
                            st.toast("Daily cap updated", icon="💾")
                            st.rerun()
                    with col_c:
                        if st.button("Disconnect", key=f"btn_disc_{c.id}", help="Remove connection and secrets"):
                            db.delete(c)
                            db.commit()
                            st.toast("Connection removed.", icon="🗑️")
                            if c.channel == "microsoft_oauth":
                                st.info("To fully revoke access, visit https://myaccount.microsoft.com/permissions and remove this app.")
                            elif c.channel == "google_oauth":
                                st.info("To fully revoke access, visit https://myaccount.google.com/permissions and remove this app.")
                            st.rerun()
                    st.markdown("---")
            else:
                st.info("No connections configured.")
        finally:
            db.close()
            
        st.markdown("Looking for Enterprise Sending Domains? View the **🌐 Sending Domains** tab.")


def _render_sending_domains_tab(db, org, organization_id: str):
    """Renders the Sending Domains (AWS SES) management panel."""
    current_user = st.session_state.get("user", {})
    current_user_id = current_user.get("id")
    user_role = st.session_state.get("current_org", {}).get("role", "regular_user")
    is_admin_or_owner = (
        user_role in ("organization_owner", "organization_admin")
        or current_user.get("platform_role") == "platform_super_admin"
    )

    # Fallback to finding admin/owner if current_user_id is not set in session
    if not current_user_id:
        admin_member = db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.role.in_(["organization_owner", "organization_admin"]),
            OrganizationMember.status == "active",
        ).first()
        if admin_member:
            current_user_id = admin_member.user_id
            is_admin_or_owner = True

    st.markdown("### 🌐 Customer Sending Domains (AWS SES)")
    st.markdown(
        "Authenticate your custom company domains with AWS SES to dispatch high-deliverability cold outreach "
        "and follow-up campaigns directly from your domain (e.g. `john@customer.com`). "
        "Automated Easy DKIM (2048-bit key rotation) and custom MAIL FROM subdomains (`mail.customer.com`) "
        "ensure strict SPF & DKIM alignment without modifying your primary MX records."
    )

    if not is_admin_or_owner:
        st.info("ℹ️ You are viewing sending domains in read-only mode. Only organization owners and administrators can register or modify domains.")

    if is_mock_provider():
        st.info("💡 **Development / Simulation Mode**: Live AWS credentials (`AWS_ACCESS_KEY_ID` & `AWS_SECRET_ACCESS_KEY`) are not set in `.env`. A simulated SES provider is active so you can register domains, view DNS instructions, and test the full flow. To connect live Amazon SES, configure your AWS keys in `.env`.")

    # Fetch existing domains
    domains = db.query(OrgSendingDomain).filter(
        OrgSendingDomain.organization_id == organization_id
    ).order_by(OrgSendingDomain.created_at.desc()).all()

    status_labels = {
        "ready": ("🟢 Verified & Ready", "#10B981"),
        "limited": ("🟡 Verified (Cap Active)", "#F59E0B"),
        "pending": ("🟠 Pending DNS Verification", "#F97316"),
        "paused": ("🔴 Paused", "#EF4444"),
        "blocked": ("⛔ Blocked", "#6B7280"),
    }

    if domains:
        st.markdown(f"#### Active Sending Domains ({len(domains)})")
        for d in domains:
            label, color = status_labels.get(d.status, (d.status.title(), "#64748B"))
            today = date.today()
            stats = db.query(OrgDomainStats).filter(
                OrgDomainStats.domain_id == d.id,
                OrgDomainStats.date == today,
            ).first()
            sent_today = stats.sent if stats else 0
            bounced_today = stats.bounced if stats else 0
            complained_today = stats.complained if stats else 0

            with st.container():
                st.markdown(
                    f"""
                    <div style="border: 1px solid #E2E8F0; border-radius: 8px; padding: 16px; margin-bottom: 16px; background-color: #FFFFFF;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <div style="font-size: 18px; font-weight: 700; color: #0F172A;">
                                ✉️ {d.domain}
                            </div>
                            <span style="background-color: {color}20; color: {color}; font-weight: 600; font-size: 12px; padding: 4px 10px; border-radius: 9999px;">
                                {label}
                            </span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if d.status == "paused":
                    st.warning(f"⚠️ **Domain Sending Paused**: {d.paused_reason or 'Domain outbound traffic is currently suspended.'}")

                m1, m2, m3, m4 = st.columns(4)
                with m1:
                    sender_addr = f"{d.from_local_part}@{d.domain}" if d.from_local_part else f"noreply@{d.domain}"
                    st.metric("From Address", sender_addr)
                with m2:
                    st.metric("Reply-To", d.reply_to or "Not set")
                with m3:
                    st.metric("Daily Cap & Usage", f"{sent_today} / {d.daily_cap}")
                with m4:
                    st.metric("Bounces / Complaints", f"{bounced_today} / {complained_today}")

                # Action buttons
                if is_admin_or_owner and current_user_id:
                    btn_c1, btn_c2, btn_c3 = st.columns([2, 2, 2])
                    with btn_c1:
                        if st.button("🔄 Verify DNS Now", key=f"btn_verify_{d.id}", help="Run DNS lookups and check AWS SES status"):
                            with st.spinner("Verifying DNS records..."):
                                try:
                                    res = verify_domain(db, current_user_id, organization_id, d.id)
                                    st.toast(f"Verification complete: status is '{res['status']}'", icon="✅")
                                    st.rerun()
                                except Exception as exc:
                                    st.error(f"Verification check failed: {exc}")

                    with btn_c2:
                        if d.status == "paused":
                            if st.button("▶️ Resume Outbound", key=f"btn_resume_{d.id}"):
                                try:
                                    resume_domain(db, current_user_id, organization_id, d.id)
                                    st.toast("Domain outbound sending resumed.", icon="▶️")
                                    st.rerun()
                                except Exception as exc:
                                    st.error(f"Could not resume domain: {exc}")
                        else:
                            if st.button("⏸️ Pause Outbound", key=f"btn_pause_{d.id}"):
                                try:
                                    pause_domain(db, current_user_id, organization_id, d.id, reason="Manually paused from settings")
                                    st.toast("Domain outbound sending paused.", icon="⏸️")
                                    st.rerun()
                                except Exception as exc:
                                    st.error(f"Could not pause domain: {exc}")

                    with btn_c3:
                        with st.expander("🗑️ Delete Claim"):
                            st.write(f"Remove **{d.domain}** and its DNS identities?")
                            del_confirm = st.checkbox("I confirm permanent deletion", key=f"chk_del_{d.id}")
                            if st.button("Confirm Delete", type="primary", key=f"btn_del_conf_{d.id}", disabled=not del_confirm):
                                try:
                                    delete_domain(db, current_user_id, organization_id, d.id)
                                    st.toast("Domain claim removed.", icon="🗑️")
                                    st.rerun()
                                except Exception as exc:
                                    st.error(f"Could not delete domain: {exc}")

                # Display DNS Records Table
                records = db.query(OrgDomainRecord).filter(
                    OrgDomainRecord.domain_id == d.id
                ).all()

                if records:
                    st.markdown("##### 📋 Required DNS Configuration")
                    rec_rows = []
                    purpose_map = {
                        "dkim": "DKIM Key (CNAME)",
                        "mail_from_mx": "Custom MAIL FROM (MX)",
                        "mail_from_spf": "Custom MAIL FROM (SPF)",
                    }
                    status_icons = {
                        "verified": "✅ Verified",
                        "pending": "⏳ Pending",
                        "failed": "❌ Failed",
                        "warning": "⚠️ Warning",
                    }
                    for r in records:
                        rec_rows.append({
                            "Type": r.record_type,
                            "Host Name": r.host,
                            "Value / Target": r.value,
                            "Purpose": purpose_map.get(r.purpose, r.purpose),
                            "Status": status_icons.get(r.status, r.status),
                        })
                    st.dataframe(pd.DataFrame(rec_rows), use_container_width=True, hide_index=True)

                # Plain-Language IT Admin Guide
                with st.expander("📋 Copy Plain-Language IT Admin Instructions"):
                    try:
                        instructions = get_dns_instructions(db, current_user_id, organization_id, d.id)
                        st.code(instructions, language="text")
                    except Exception:
                        st.write("Instructions currently unavailable.")

                # Verification Check History
                with st.expander("📜 Verification Check History"):
                    try:
                        history = get_check_history(db, current_user_id, organization_id, d.id)
                        if history:
                            hist_rows = []
                            for h in history[:10]:
                                res = h.get("results") or {}
                                dkim_list = res.get("dkim_checks") or []
                                dkim_ver_count = sum(1 for dc in dkim_list if dc.get("verified"))
                                spf = res.get("spf") or {}
                                dmarc = res.get("dmarc") or {}
                                mx = res.get("mx") or {}
                                hist_rows.append({
                                    "Checked At": h.get("checked_at")[:19].replace("T", " ") if h.get("checked_at") else "N/A",
                                    "Trigger": h.get("triggered_by", "system"),
                                    "DKIM Records": f"{dkim_ver_count}/{len(dkim_list)} Verified",
                                    "Provider DKIM": res.get("provider_dkim_status", "N/A"),
                                    "SPF Valid": "Yes" if spf.get("valid") else "No",
                                    "DMARC Policy": dmarc.get("policy", "None"),
                                    "MX Provider": mx.get("provider", "Unknown"),
                                })
                            st.dataframe(pd.DataFrame(hist_rows), use_container_width=True, hide_index=True)
                        else:
                            st.info("No verification checks recorded yet.")
                    except Exception:
                        st.write("History unavailable.")

                # Edit Domain Settings
                if is_admin_or_owner and current_user_id:
                    with st.expander("⚙️ Edit Sender & Daily Cap"):
                        col_e1, col_e2, col_e3 = st.columns(3)
                        with col_e1:
                            new_from_name = st.text_input("Sender Display Name", value=d.from_name or "", key=f"edit_fn_{d.id}")
                        with col_e2:
                            new_reply_to = st.text_input("Reply-To Address", value=d.reply_to or "", key=f"edit_rt_{d.id}")
                        with col_e3:
                            new_cap = st.number_input("Daily Send Cap", min_value=0, max_value=50000, value=d.daily_cap, step=50, key=f"edit_cap_{d.id}")

                        if st.button("Save Domain Settings", key=f"btn_save_dom_{d.id}"):
                            try:
                                update_domain(
                                    db=db,
                                    user_id=current_user_id,
                                    organization_id=organization_id,
                                    domain_id=d.id,
                                    from_name=new_from_name,
                                    reply_to=new_reply_to,
                                    daily_cap=int(new_cap),
                                )
                                st.toast("Domain settings updated!", icon="⚙️")
                                st.rerun()
                            except Exception as exc:
                                st.error(f"Failed to update settings: {exc}")

                st.markdown("<hr style='margin: 20px 0; border: none; border-top: 1px solid #E2E8F0;'/>", unsafe_allow_html=True)
    else:
        st.info("No sending domains registered yet. Register your company domain below to enable SES-authenticated email campaigns.")

    # Register New Domain Section
    if is_admin_or_owner:
        with st.expander("➕ Register Sending Domain(s)", expanded=(len(domains) == 0)):
            st.markdown(
                "Authenticate your company domains to generate AWS SES DKIM tokens and MAIL FROM DNS records. "
                "You can register an individual domain or batch-register 4–5 domains simultaneously."
            )
            reg_mode = st.radio(
                "Registration Mode",
                ["Single Domain", "Batch Register (Multiple Domains)"],
                horizontal=True,
                key="dom_reg_mode"
            )

            if reg_mode == "Single Domain":
                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    reg_email = st.text_input(
                        "Sender Work Email Address*",
                        placeholder="outreach@customer.com",
                        key="reg_domain_email",
                        help="Email address used as default From sender (e.g. outreach@acme.com)",
                    )
                    reg_name = st.text_input(
                        "Default Sender Display Name",
                        value=org.brand_name or org.name or "",
                        placeholder="Acme Outreach Team",
                        key="reg_domain_name",
                    )
                with col_r2:
                    reg_reply = st.text_input(
                        "Default Reply-To Email",
                        value=org.email or "",
                        placeholder="replies@customer.com",
                        key="reg_domain_reply",
                    )
                    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                    if st.button("🚀 Register Domain with AWS SES", type="primary", key="btn_reg_domain_submit", use_container_width=True):
                        if not reg_email or "@" not in reg_email:
                            st.error("Please provide a valid sender work email address (e.g. outreach@customer.com).")
                        elif not current_user_id:
                            st.error("User context missing. Unable to authenticate request.")
                        else:
                            with st.spinner("Registering domain identity with AWS SES..."):
                                try:
                                    result = register_domain(
                                        db=db,
                                        user_id=current_user_id,
                                        organization_id=organization_id,
                                        email_address=reg_email,
                                        from_name=reg_name,
                                        reply_to=reg_reply or reg_email,
                                    )
                                    st.success(f"Domain '{result['domain']}' successfully registered! DNS records generated.")
                                    st.toast(f"Domain {result['domain']} registered!", icon="🌐")
                                    st.rerun()
                                except ValueError as ve:
                                    st.error(str(ve))
                                except PermissionError as pe:
                                    st.error(str(pe))
                                except Exception as exc:
                                    st.error(f"Domain registration failed: {exc}")
            else:
                st.markdown(
                    "Paste 4–5 sender emails or domains (one per line). The system will register each domain identity and generate all DNS records at once."
                )
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    batch_text = st.text_area(
                        "Sender Emails or Domains (one per line)*",
                        placeholder="outreach@superai-hq.com\nsales@superaimail.com\ncontact@getsuperai.com\nteam@superai-tech.com",
                        height=130,
                        key="reg_batch_domains_text",
                    )
                with col_b2:
                    batch_name = st.text_input(
                        "Default Sender Display Name",
                        value=org.brand_name or org.name or "",
                        placeholder="Acme Outreach Team",
                        key="reg_batch_domain_name",
                    )
                    batch_reply = st.text_input(
                        "Default Reply-To Email",
                        value=org.email or "",
                        placeholder="replies@customer.com",
                        key="reg_batch_domain_reply",
                    )
                    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
                    if st.button("🚀 Batch Register All Domains", type="primary", key="btn_reg_batch_submit", use_container_width=True):
                        lines = [l.strip() for l in batch_text.splitlines() if l.strip()]
                        if not lines:
                            st.error("Please enter at least one email address or domain.")
                        elif not current_user_id:
                            st.error("User context missing. Unable to authenticate request.")
                        else:
                            success_count = 0
                            with st.spinner(f"Registering {len(lines)} domains with AWS SES..."):
                                for line in lines:
                                    addr = line if "@" in line else f"outreach@{line}"
                                    try:
                                        res = register_domain(
                                            db=db,
                                            user_id=current_user_id,
                                            organization_id=organization_id,
                                            email_address=addr,
                                            from_name=batch_name,
                                            reply_to=batch_reply or addr,
                                        )
                                        success_count += 1
                                        st.toast(f"Registered {res['domain']}!", icon="🌐")
                                    except Exception as exc:
                                        st.warning(f"Could not register '{line}': {exc}")
                            if success_count > 0:
                                st.success(f"Successfully registered {success_count} domain(s)! DNS records generated below.")
                                st.rerun()

    # Deliverability & Policy Information
    with st.expander("🛡️ Deliverability Architecture & Acceptable Use Policy", expanded=False):
        st.markdown(
            """
            - **Easy DKIM (2048-bit CNAMEs)**: AWS SES manages and rotates cryptographic signing keys automatically. All outbound emails are DKIM-signed for maximum spam-filter trust.
            - **Custom MAIL FROM Subdomain (`mail.domain.com`)**: Dispatches email through an isolated subdomain. This ensures strict SPF alignment while **never altering** your root domain's MX records or exceeding the 10-lookup SPF limit.
            - **AWS SES Acceptable Use Policy**: SES is strictly designed for opt-in or professional B2B outreach with low bounce and complaint rates:
              - **Bounce Rate Limit**: If bounce rate exceeds **5.0%**, the domain is automatically paused to protect sender reputation.
              - **Complaint Rate Limit**: If complaint rate exceeds **0.1%**, outbound campaigns are automatically suspended.
              - **Daily Sending Cap**: We enforce a conservative per-tenant daily cap (default 200) to ensure high reputation and IP warming.
            """
        )


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

        tab_branding, tab_ai, tab_sender, tab_channels, tab_domains, tab_booking, tab_team = st.tabs([
            "🎨 Branding & Identity",
            "🤖 AI & BYOK Intelligence",
            "✉️ Email Sender & Outbound",
            "📬 Email Channels",
            "🌐 Sending Domains",
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

        with tab_channels:
            render_email_channels_chooser(organization_id, context="settings")

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

            st.info("💡 **Enterprise Sending Domains**: Looking to authenticate your custom domain (e.g. `john@customer.com`) via AWS SES with Easy DKIM & SPF alignment? Switch to the **🌐 Sending Domains** tab.")

        with tab_domains:
            _render_sending_domains_tab(db, org, organization_id)

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
