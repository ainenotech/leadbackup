"""Team & Organization Invitation Email Service.

Provides responsive, executive-designed invitation emails with bulletproof HTML,
credential provisioning details, and direct workspace join links.
"""

import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

LOGO_URL = "https://res.cloudinary.com/dqreqsjas/image/upload/v1789542387/logo-dark.png"

ROLE_CONFIG: Dict[str, Dict[str, str]] = {
    "organization_owner": {
        "label": "Organization Owner",
        "desc": "Full administrative ownership, billing, member access, and workspace controls",
        "icon": "👑",
        "color": "#7C3AED",
        "bg": "#EDE9FE",
        "border": "#DDD6FE",
    },
    "organization_admin": {
        "label": "Organization Admin",
        "desc": "Manage workspace members, channels, outreach campaigns, and integrations",
        "icon": "🛡️",
        "color": "#2563EB",
        "bg": "#EFF6FF",
        "border": "#BFDBFE",
    },
    "campaign_manager": {
        "label": "Campaign Manager",
        "desc": "Create, edit, review, and schedule AI email outreach campaigns",
        "icon": "🚀",
        "color": "#059669",
        "bg": "#ECFDF5",
        "border": "#A7F3D0",
    },
    "sales_user": {
        "label": "Sales User",
        "desc": "Engage with warm leads, follow up on customer replies, and book consultations",
        "icon": "💼",
        "color": "#D97706",
        "bg": "#FFFBEB",
        "border": "#FDE68A",
    },
    "regular_user": {
        "label": "Regular Member",
        "desc": "Standard pipeline access, lead directory review, and campaign telemetry",
        "icon": "👤",
        "color": "#475569",
        "bg": "#F8FAFC",
        "border": "#E2E8F0",
    },
    "viewer": {
        "label": "Viewer (Read Only)",
        "desc": "Read-only access across workspace telemetry, reporting, and lead records",
        "icon": "👁️",
        "color": "#64748B",
        "bg": "#F1F5F9",
        "border": "#CBD5E1",
    },
}


def _clean_display_name(name: Optional[str], email: str) -> str:
    """Format a clean display name."""
    if name and str(name).strip().lower() not in ("nan", "none", ""):
        return name.strip()
    prefix = email.split("@")[0].replace(".", " ").replace("_", " ")
    return prefix.title()


def build_invitation_email(
    recipient_email: str,
    organization_name: str,
    inviter_name: str,
    inviter_email: str,
    recipient_name: Optional[str] = None,
    role: str = "regular_user",
    temporary_password: Optional[str] = None,
    app_url: Optional[str] = None,
) -> Tuple[str, str, str]:
    """Builds a pixel-perfect, cross-client HTML & text invitation email.

    Returns:
        (subject, html_content, text_content)
    """
    clean_email = recipient_email.strip().lower()
    clean_name = _clean_display_name(recipient_name, clean_email)
    clean_inviter = inviter_name.strip() if inviter_name else "A workspace administrator"
    clean_org = organization_name.strip() if organization_name else "Workspace"

    role_meta = ROLE_CONFIG.get(role, ROLE_CONFIG["regular_user"])
    base_app_url = (app_url or os.getenv("APP_URL", "http://localhost:3000")).rstrip("/")
    login_url = f"{base_app_url}?email={clean_email}"

    subject = f"You're invited to join {clean_org} on Nenotechnology"
    preheader = f"{clean_inviter} has invited you to join the {clean_org} workspace on Nenotechnology."

    # Credentials row HTML
    if temporary_password:
        credentials_html = f"""
        <tr>
          <td style="padding: 9px 0; border-top: 1px solid #E2E8F0; font-size: 13.5px; color: #64748B; width: 140px; vertical-align: top;">
            🔑 <strong>Initial Password:</strong>
          </td>
          <td style="padding: 9px 0; border-top: 1px solid #E2E8F0; vertical-align: top;">
            <div style="display: inline-block; background: #FFFFFF; border: 1px dashed #94A3B8; padding: 4px 12px; border-radius: 6px; font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; font-size: 13.5px; font-weight: 700; color: #0F172A; letter-spacing: 0.05em;">
              {temporary_password}
            </div>
            <div style="font-size: 11.5px; color: #64748B; margin-top: 4px;">
              Please sign in and set your personal password under Settings.
            </div>
          </td>
        </tr>
        """
    else:
        credentials_html = f"""
        <tr>
          <td style="padding: 9px 0; border-top: 1px solid #E2E8F0; font-size: 13.5px; color: #64748B; width: 140px; vertical-align: top;">
            🔑 <strong>Access:</strong>
          </td>
          <td style="padding: 9px 0; border-top: 1px solid #E2E8F0; font-size: 13.5px; color: #0F172A; vertical-align: top;">
            Sign in with your existing account password
          </td>
        </tr>
        """

    html_content = f"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta name="color-scheme" content="light">
  <title>{subject}</title>
  <!--[if mso]>
  <style type="text/css">
    body, table, td, p, div, a {{ font-family: Arial, Helvetica, sans-serif !important; }}
  </style>
  <![endif]-->
  <style type="text/css">
    body {{
      margin: 0 !important;
      padding: 0 !important;
      background-color: #F1F5F9;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      -webkit-font-smoothing: antialiased;
    }}
    table {{ border-collapse: collapse; }}
    @media only screen and (max-width: 620px) {{
      .outer-wrap {{ padding: 12px 6px !important; }}
      .main-card {{ width: 100% !important; border-radius: 10px !important; }}
      .card-body {{ padding: 24px 20px !important; }}
      .cta-btn {{ display: block !important; width: 100% !important; text-align: center !important; box-sizing: border-box !important; }}
      .details-table td {{ display: block !important; width: 100% !important; padding: 4px 0 !important; }}
    }}
  </style>
</head>
<body style="margin: 0; padding: 0; background-color: #F1F5F9;">

  <!-- Preheader text (hidden preview in mail clients) -->
  <div style="display: none; max-height: 0; overflow: hidden; opacity: 0; font-size: 1px; line-height: 1px; color: #F1F5F9;">
    {preheader}&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;
  </div>

  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="outer-wrap" style="background-color: #F1F5F9; padding: 36px 12px;">
    <tr>
      <td align="center">
        <!-- Main Container Card -->
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" class="main-card" style="width: 600px; max-width: 100%; background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.05), 0 8px 10px -6px rgba(15, 23, 42, 0.04);">
          
          <!-- Top Accent Banner -->
          <tr>
            <td style="height: 6px; background: #2563EB; background: linear-gradient(90deg, #1A5CFF 0%, #3B82F6 50%, #6366F1 100%);"></td>
          </tr>

          <!-- Card Content -->
          <tr>
            <td class="card-body" style="padding: 36px 40px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; text-align: left;">
              
              <!-- Header Bar (Logo + Badge) -->
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 24px;">
                <tr>
                  <td align="left" style="vertical-align: middle;">
                    <img src="{LOGO_URL}" alt="Nenotechnology" style="height: 36px; max-height: 38px; max-width: 170px; display: block; border: 0; outline: none;" />
                  </td>
                  <td align="right" style="vertical-align: middle;">
                    <span style="display: inline-block; background-color: #EFF6FF; color: #2563EB; border: 1px solid #BFDBFE; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; padding: 4px 10px; border-radius: 9999px;">
                      ✨ Workspace Invitation
                    </span>
                  </td>
                </tr>
              </table>

              <div style="height: 1px; background-color: #F1F5F9; margin-bottom: 24px;"></div>

              <!-- Main Greeting & Headline -->
              <h1 style="margin: 0 0 12px 0; font-size: 23px; font-weight: 800; color: #0F172A; line-height: 1.3; letter-spacing: -0.02em;">
                You've been invited to join <span style="color: #2563EB;">{clean_org}</span>
              </h1>

              <p style="margin: 0 0 14px 0; font-size: 15px; line-height: 1.6; color: #334155;">
                Hello <strong>{clean_name}</strong>,
              </p>

              <p style="margin: 0 0 22px 0; font-size: 15px; line-height: 1.6; color: #334155;">
                <strong>{clean_inviter}</strong> (<a href="mailto:{inviter_email}" style="color: #2563EB; text-decoration: none; font-weight: 600;">{inviter_email}</a>) has invited you to collaborate on the <strong>{clean_org}</strong> workspace on the Nenotechnology outreach &amp; lead re-engagement platform.
              </p>

              <!-- Workspace Details Card -->
              <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px; padding: 20px 22px; margin-bottom: 26px;">
                <div style="font-size: 11px; font-weight: 800; color: #64748B; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 12px;">
                  📋 Invitation Details
                </div>
                
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="details-table">
                  <tr>
                    <td style="padding: 6px 0; font-size: 13.5px; color: #64748B; width: 140px; vertical-align: top;">
                      🏢 <strong>Workspace:</strong>
                    </td>
                    <td style="padding: 6px 0; font-size: 14px; font-weight: 700; color: #0F172A; vertical-align: top;">
                      {clean_org}
                    </td>
                  </tr>

                  <tr>
                    <td style="padding: 9px 0; border-top: 1px solid #E2E8F0; font-size: 13.5px; color: #64748B; vertical-align: top;">
                      🛡️ <strong>Assigned Role:</strong>
                    </td>
                    <td style="padding: 9px 0; border-top: 1px solid #E2E8F0; vertical-align: top;">
                      <span style="display: inline-block; background-color: {role_meta['bg']}; color: {role_meta['color']}; border: 1px solid {role_meta['border']}; font-weight: 700; font-size: 12px; padding: 3px 10px; border-radius: 9999px;">
                        {role_meta['icon']} {role_meta['label']}
                      </span>
                      <div style="font-size: 12px; color: #64748B; margin-top: 4px; line-height: 1.4;">
                        {role_meta['desc']}
                      </div>
                    </td>
                  </tr>

                  <tr>
                    <td style="padding: 9px 0; border-top: 1px solid #E2E8F0; font-size: 13.5px; color: #64748B; vertical-align: top;">
                      ✉️ <strong>Login Email:</strong>
                    </td>
                    <td style="padding: 9px 0; border-top: 1px solid #E2E8F0; font-size: 13.5px; font-weight: 600; color: #0F172A; vertical-align: top;">
                      {clean_email}
                    </td>
                  </tr>

                  {credentials_html}
                </table>
              </div>

              <!-- CTA Join Button -->
              <div style="margin: 28px 0 24px 0; text-align: center;">
                <a href="{login_url}" target="_blank" class="cta-btn" style="display: inline-block; background: #2563EB; background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%); color: #FFFFFF; font-weight: 700; font-size: 15px; text-decoration: none; padding: 14px 34px; border-radius: 10px; letter-spacing: 0.01em; box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35);">
                  Accept Invitation &amp; Join Workspace &rarr;
                </a>
                <p style="margin: 12px 0 0 0; font-size: 12.5px; color: #64748B;">
                  Direct link: <a href="{login_url}" style="color: #2563EB; text-decoration: underline; word-break: break-all;">{login_url}</a>
                </p>
              </div>

              <!-- Workspace Capabilities Section -->
              <div style="margin-top: 32px; padding-top: 24px; border-top: 1px solid #E2E8F0;">
                <div style="font-size: 13px; font-weight: 800; color: #0F172A; margin-bottom: 14px;">
                  What you can do in this workspace:
                </div>

                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                  <tr>
                    <td style="padding: 6px 0; font-size: 13.5px; color: #334155; line-height: 1.5; vertical-align: top;">
                      <span style="color: #2563EB; font-weight: 700;">🚀 AI Outreach Engine:</span> Review personalized campaigns and automate multi-channel follow-ups.
                    </td>
                  </tr>
                  <tr>
                    <td style="padding: 6px 0; font-size: 13.5px; color: #334155; line-height: 1.5; vertical-align: top;">
                      <span style="color: #2563EB; font-weight: 700;">📊 Live Telemetry:</span> Track opens, clicks, customer replies, and conversion rates in real time.
                    </td>
                  </tr>
                  <tr>
                    <td style="padding: 6px 0; font-size: 13.5px; color: #2563EB; line-height: 1.5; vertical-align: top;">
                      <span style="color: #2563EB; font-weight: 700;">📅 Calendar Synchronization:</span> Automatic consultation booking with Microsoft Teams &amp; Bookings.
                    </td>
                  </tr>
                </table>
              </div>

              <!-- Security Notice Callout -->
              <div style="background-color: #FEF3C7; border-left: 4px solid #F59E0B; border-radius: 6px; padding: 12px 16px; margin: 26px 0 20px 0;">
                <p style="margin: 0; font-size: 12px; color: #92400E; line-height: 1.5;">
                  🔒 <strong>Security Notice:</strong> This invitation was specifically generated for <strong>{clean_email}</strong>. If you did not expect this invitation, you can safely ignore this email.
                </p>
              </div>

              <!-- Signature & Footer -->
              <div style="margin-top: 28px; padding-top: 20px; border-top: 1px solid #E2E8F0; font-size: 12.5px; color: #64748B; line-height: 1.6;">
                <p style="margin: 0 0 4px 0; font-weight: 700; color: #0F172A;">
                  Nenotechnology Team
                </p>
                <p style="margin: 0 0 8px 0; color: #64748B;">
                  Aineno Innovation Pvt. Ltd. &bull; Ahmedabad, Gujarat, India
                </p>
                <p style="margin: 0; font-size: 11.5px; color: #94A3B8;">
                  <a href="https://www.nenotechnology.com" style="color: #2563EB; text-decoration: none;">www.nenotechnology.com</a> &nbsp;|&nbsp;
                  <a href="mailto:support@nenotechnology.com" style="color: #2563EB; text-decoration: none;">support@nenotechnology.com</a> &nbsp;|&nbsp;
                  Outreach &amp; Lead AI Platform
                </p>
              </div>

            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>

</body>
</html>"""

    # Plain text fallback
    text_pwd_line = f"\n- Initial Password: {temporary_password} (Please change upon initial login)" if temporary_password else "\n- Access: Use your existing account password"
    text_content = f"""You've been invited to join {clean_org} on Nenotechnology!

Hello {clean_name},

{clean_inviter} ({inviter_email}) has invited you to collaborate on the {clean_org} workspace on the Nenotechnology outreach platform.

Invitation Details:
- Workspace: {clean_org}
- Role: {role_meta['label']} ({role_meta['desc']})
- Email: {clean_email}{text_pwd_line}

Accept your invitation and join here:
{login_url}

If you were not expecting this invitation, you can safely ignore this message.

Warm regards,
Nenotechnology Team
Aineno Innovation Pvt. Ltd.
https://www.nenotechnology.com
"""

    return subject, html_content, text_content


def send_invitation_email(
    recipient_email: str,
    organization_name: str,
    inviter_name: str,
    inviter_email: str,
    recipient_name: Optional[str] = None,
    role: str = "regular_user",
    temporary_password: Optional[str] = None,
    app_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Generates and delivers the workspace invitation email via the configured mailer."""
    clean_email = recipient_email.strip().lower()
    subject, html_content, text_content = build_invitation_email(
        recipient_email=clean_email,
        organization_name=organization_name,
        inviter_name=inviter_name,
        inviter_email=inviter_email,
        recipient_name=recipient_name,
        role=role,
        temporary_password=temporary_password,
        app_url=app_url,
    )

    try:
        from Email.factory import get_mailer

        mailer = get_mailer()
        msg_id = mailer.send_email(
            to_email=clean_email,
            subject=subject,
            body=html_content,
            is_transactional=True,
        )

        return {
            "success": True,
            "status": "sent",
            "recipient": clean_email,
            "subject": subject,
            "message_id": msg_id,
        }
    except Exception as e:
        print(f"[Invitation Service] Error sending invitation email to {clean_email}: {e}")
        return {
            "success": False,
            "status": "failed",
            "recipient": clean_email,
            "error": str(e),
        }
