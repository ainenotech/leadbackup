"""Phase 3's transactional emails. Kept as plain deterministic
templates rather than routed through the LLM composer — these confirm
facts (a time, a link) rather than persuade, so a template that can never
misstate the booked time is worth more here than composer variety.
"""

import os
from datetime import datetime
from typing import List, Optional
from zoneinfo import ZoneInfo


FONT_STACK = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
LOGO_URL = "https://res.cloudinary.com/dqreqsjas/image/upload/v1789542387/logo-dark.png"
LOGO_HEADER_HTML = f'<div style="margin:0 0 14px 0;padding:0 0 12px 0;border-bottom:1px solid #eef0f4;"><img src="{LOGO_URL}" alt="Nenotechnology" width="140" height="36" style="display:block;border:0;outline:none;text-decoration:none;-ms-interpolation-mode:bicubic;width:140px;height:36px;max-height:40px;pointer-events:none;"></div>'


def _clean_name(name: Optional[str]) -> str:
    if not name or str(name).strip().lower() in ("nan", "none", ""):
        return "there"
    clean = str(name).strip()
    return clean.title() if clean.islower() else clean


def _wrap_transactional_card(inner_html: str, accent_color: str = "#2563eb") -> str:
    """Wraps transactional email body in a professional bordered card container."""
    return f"""<div style="background-color:#f0f4f8;padding:20px 8px;margin:0;font-family:{FONT_STACK};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f0f4f8;">
<tr><td align="center">

  <!-- Accent Top Bar -->
  <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:600px;max-width:100%;">
    <tr><td style="height:4px;background:linear-gradient(90deg,{accent_color},#6366f1);border-radius:10px 10px 0 0;font-size:0;line-height:0;" height="4">&nbsp;</td></tr>
  </table>

  <!-- Card Body -->
  <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:600px;max-width:100%;background-color:#ffffff;border-left:1px solid #e2e8f0;border-right:1px solid #e2e8f0;border-bottom:1px solid #e2e8f0;border-radius:0 0 10px 10px;box-shadow:0 2px 8px -2px rgba(0,0,0,0.08),0 1px 3px rgba(0,0,0,0.04);">
    <tr>
      <td style="padding:26px 30px 22px 30px;font-family:{FONT_STACK};font-size:15px;line-height:1.5;color:#1e293b;text-align:left;">
{inner_html}
      </td>
    </tr>
  </table>

  <!-- Footer -->
  <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:600px;max-width:100%;margin-top:8px;">
    <tr>
      <td style="font-size:11px;line-height:1.4;color:#94a3b8;text-align:center;padding:4px 12px;font-family:{FONT_STACK};">
        Aineno Innovation Pvt. Ltd. &middot; Ahmedabad, Gujarat, India
      </td>
    </tr>
  </table>

</td></tr>
</table>
</div>"""


def build_confirmation_email(
    name: Optional[str],
    company: Optional[str],
    start: datetime,
    tz_name: str,
    meet_link: str,
    service: Optional[str] = None,
) -> tuple[str, str]:
    """Builds a confirmation email for a successfully booked meeting at
    the customer's requested time slot, with the Nenotechnology branded HTML layout,
    logo, formatted IST date & time, topic, and Teams join button."""
    local = start.astimezone(ZoneInfo(tz_name))
    tz_label = local.tzname() or "IST"
    date_time_str = f"{local.strftime('%A, %B %d, %Y at %I:%M %p')} {tz_label}"
    cust_name = _clean_name(name)
    company_line = f" for {company.strip()}" if company and str(company).strip().lower() not in ("nan", "none", "") else ""
    
    topic = (service or "AI & IT Solutions Consultation").strip()
    if company and str(company).strip().lower() not in ("nan", "none", "") and company not in topic:
        topic = f"{topic} ({company.strip()})"

    sender_email = os.getenv("MS_SENDER_EMAIL", "support@nenotechnology.com")
    contact_email = os.getenv("CONTACT_EMAIL", "sales@nenotechnology.com")
    contact_phone = os.getenv("CONTACT_PHONE", "7863852024")
    accent = "#2563eb"
    subject = f"Confirmed: Consultation Call with Nenotechnology{company_line} — {local.strftime('%b %d, %I:%M %p')}"

    inner = f"""{LOGO_HEADER_HTML}
  <p style="margin:0 0 8px 0;padding:0;line-height:1.5;">Hi <strong>{cust_name}</strong>,</p>
  <p style="margin:0 0 10px 0;padding:0;line-height:1.5;">Thank you for reaching out to Nenotechnology. Your consultation call has been confirmed and added to our calendar.</p>
  <div style="background:#f8fafc;border-left:4px solid {accent};border-radius:6px;padding:10px 14px;margin:10px 0;">
    <p style="margin:0 0 5px 0;padding:0;line-height:1.4;">📅 <strong>Date &amp; Time:</strong> {date_time_str}</p>
    <p style="margin:0 0 5px 0;padding:0;line-height:1.4;">🎯 <strong>Discussion Topic:</strong> {topic}</p>
    <p style="margin:0;padding:0;line-height:1.4;">💻 <strong>Platform:</strong> Microsoft Teams</p>
  </div>
  <div style="margin:12px 0 14px 0;padding:0;">
    <a href="{meet_link}" style="display:inline-block;background:{accent};color:#ffffff;text-decoration:none;padding:11px 24px;border-radius:6px;font-weight:600;font-size:14px;text-align:center;line-height:1;box-shadow:0 2px 4px rgba(0,0,0,0.12);">Join Microsoft Teams Meeting &rarr;</a>
  </div>
  <p style="margin:0 0 0 0;padding:0;line-height:1.5;">We look forward to speaking with you.</p>
  <div style="margin-top:14px;padding-top:10px;border-top:1px solid #e2e8f0;font-size:13px;color:#64748b;line-height:1.45;">
    Warm regards,<br>
    <strong style="color:#0f172a;">Tirth Patel</strong><br>
    Founder &amp; CEO, Nenotechnology (Aineno Innovation Pvt. Ltd.)<br>
    <span style="font-size:11.5px;color:#94a3b8;">Ahmedabad, Gujarat, India</span><br>
    <span style="font-size:12px;"><a href="mailto:{contact_email}" style="color:{accent};text-decoration:none;">{contact_email}</a> &nbsp;|&nbsp; <a href="tel:{contact_phone}" style="color:{accent};text-decoration:none;">+91 {contact_phone}</a> &nbsp;|&nbsp; <a href="https://www.nenotechnology.com" style="color:{accent};text-decoration:none;">www.nenotechnology.com</a></span>
  </div>"""
    body = _wrap_transactional_card(inner, accent)
    return subject, body


def build_rescheduled_email(
    name: Optional[str],
    company: Optional[str],
    start: datetime,
    tz_name: str,
    meet_link: str,
    service: Optional[str] = None,
) -> tuple[str, str]:
    """Builds a rescheduling email when the customer's requested slot was
    busy. The agent has auto-booked the earliest available free slot and
    this email notifies them of the new time + Teams link in the same natural
    Nenotechnology email format."""
    local = start.astimezone(ZoneInfo(tz_name))
    tz_label = local.tzname() or "IST"
    date_time_str = f"{local.strftime('%A, %B %d, %Y at %I:%M %p')} {tz_label}"
    cust_name = _clean_name(name)
    company_line = f" for {company.strip()}" if company and str(company).strip().lower() not in ("nan", "none", "") else ""
    
    topic = (service or "AI & IT Solutions Consultation").strip()
    if company and str(company).strip().lower() not in ("nan", "none", "") and company not in topic:
        topic = f"{topic} ({company.strip()})"

    sender_email = os.getenv("MS_SENDER_EMAIL", "support@nenotechnology.com")
    contact_email = os.getenv("CONTACT_EMAIL", "sales@nenotechnology.com")
    contact_phone = os.getenv("CONTACT_PHONE", "7863852024")
    accent = "#f59e0b"
    subject = f"Rescheduled: Consultation Call with Nenotechnology{company_line} — {local.strftime('%b %d, %I:%M %p')}"

    inner = f"""{LOGO_HEADER_HTML}
  <p style="margin:0 0 8px 0;padding:0;line-height:1.5;">Hi <strong>{cust_name}</strong>,</p>
  <p style="margin:0 0 10px 0;padding:0;line-height:1.5;">Thank you for reaching out to Nenotechnology. Your requested time slot was not available on our calendar, so we have automatically reserved the <strong>earliest available slot</strong> for you.</p>
  <div style="background:#fffbeb;border-left:4px solid {accent};border-radius:6px;padding:10px 14px;margin:10px 0;">
    <p style="margin:0 0 5px 0;padding:0;line-height:1.4;">📅 <strong>Rescheduled Date &amp; Time:</strong> {date_time_str}</p>
    <p style="margin:0 0 5px 0;padding:0;line-height:1.4;">🎯 <strong>Discussion Topic:</strong> {topic}</p>
    <p style="margin:0;padding:0;line-height:1.4;">💻 <strong>Platform:</strong> Microsoft Teams</p>
  </div>
  <div style="margin:12px 0 14px 0;padding:0;">
    <a href="{meet_link}" style="display:inline-block;background:#0f62fe;color:#ffffff;text-decoration:none;padding:11px 24px;border-radius:6px;font-weight:600;font-size:14px;text-align:center;line-height:1;box-shadow:0 2px 4px rgba(0,0,0,0.12);">Join Microsoft Teams Meeting &rarr;</a>
  </div>
  <p style="margin:0 0 0 0;font-size:13.5px;color:#475569;padding:0;line-height:1.5;">A calendar invite has also been sent to your email. If this time doesn't work for you, simply reply to this email and we'll gladly arrange another slot.</p>
  <div style="margin-top:14px;padding-top:10px;border-top:1px solid #e2e8f0;font-size:13px;color:#64748b;line-height:1.45;">
    Warm regards,<br>
    <strong style="color:#0f172a;">Tirth Patel</strong><br>
    Founder &amp; CEO, Nenotechnology (Aineno Innovation Pvt. Ltd.)<br>
    <span style="font-size:11.5px;color:#94a3b8;">Ahmedabad, Gujarat, India</span><br>
    <span style="font-size:12px;"><a href="mailto:{contact_email}" style="color:#0f62fe;text-decoration:none;">{contact_email}</a> &nbsp;|&nbsp; <a href="tel:{contact_phone}" style="color:#0f62fe;text-decoration:none;">+91 {contact_phone}</a> &nbsp;|&nbsp; <a href="https://www.nenotechnology.com" style="color:#0f62fe;text-decoration:none;">www.nenotechnology.com</a></span>
  </div>"""
    body = _wrap_transactional_card(inner, "#0f62fe")
    return subject, body


def build_alternate_times_email(
    name: Optional[str], company: Optional[str], alternates: List[datetime]
) -> tuple[str, str]:
    """Legacy fallback: proposes alternate times without auto-booking.
    Retained for edge cases where no free slot can be auto-booked."""
    greeting = _clean_name(name)
    company_line = f" with {company}" if company else ""

    subject = "None of those times work on our end — pick another"
    lines = "\n".join(f"- {dt.strftime('%A, %B %d at %I:%M %p %Z')}" for dt in alternates)
    body = (
        f"Hi {greeting},\n\n"
        f"Thanks for sharing your availability{company_line} — none of those "
        f"times are free on our calendar, but here's what is open:\n\n"
        f"{lines}\n\n"
        f"Just reply to this email to confirm one of these times.\n\n"
        f"Thanks!"
    )
    return subject, body
