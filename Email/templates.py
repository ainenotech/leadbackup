"""Phase 3's transactional emails. Kept as plain deterministic
templates rather than routed through the LLM composer — these confirm
facts (a time, a link) rather than persuade, so a template that can never
misstate the booked time is worth more here than composer variety.
"""

import os
from datetime import datetime
from typing import List, Optional
from zoneinfo import ZoneInfo





LOGO_URL = "https://res.cloudinary.com/dqreqsjas/image/upload/v1789542387/logo-dark.png"
LOGO_HEADER_HTML = f'<div style="margin:0 0 16px 0;padding:0 0 12px 0;border-bottom:1px solid #eef0f4;"><img src="{LOGO_URL}" alt="Nenotechnology" width="132" height="34" style="display:block;border:0;outline:none;text-decoration:none;-ms-interpolation-mode:bicubic;width:132px;height:34px;max-height:36px;pointer-events:none;"></div>'


def _clean_name(name: Optional[str]) -> str:
    if not name or str(name).strip().lower() in ("nan", "none", ""):
        return "there"
    clean = str(name).strip()
    return clean.title() if clean.islower() else clean


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
    subject = f"Confirmed: Consultation Call with Nenotechnology{company_line} — {local.strftime('%b %d, %I:%M %p')}"

    body = f"""<div style="font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.45;color:#1e293b;max-width:100%;box-sizing:border-box;">
  {LOGO_HEADER_HTML}
  <p style="margin:0 0 10px 0;margin-top:0;margin-bottom:10px;padding:0;line-height:1.45;">Hi <strong>{cust_name}</strong>,</p>
  <p style="margin:0 0 10px 0;margin-top:0;margin-bottom:10px;padding:0;line-height:1.45;">Thank you for reaching out to Nenotechnology. Your consultation call has been confirmed and added to our calendar.</p>
  <div style="background:#f8fafc;border-left:4px solid #2563eb;border-radius:6px;padding:12px 16px;margin:12px 0;">
    <p style="margin:0 0 6px 0;margin-top:0;margin-bottom:6px;padding:0;line-height:1.4;">📅 <strong>Date &amp; Time:</strong> {date_time_str}</p>
    <p style="margin:0 0 6px 0;margin-top:0;margin-bottom:6px;padding:0;line-height:1.4;">🎯 <strong>Discussion Topic:</strong> {topic}</p>
    <p style="margin:0;margin-top:0;padding:0;line-height:1.4;">💻 <strong>Platform:</strong> Microsoft Teams</p>
  </div>
  <div style="margin:0 0 14px 0;margin-top:0;margin-bottom:14px;padding:0;">
    <a href="{meet_link}" style="display:inline-block;background:#2563eb;color:#ffffff;text-decoration:none;padding:10px 22px;border-radius:6px;font-weight:600;font-size:14px;text-align:center;line-height:1;">Join Microsoft Teams Meeting</a>
  </div>
  <p style="margin:0 0 12px 0;margin-top:0;margin-bottom:12px;padding:0;line-height:1.45;">We look forward to speaking with you.</p>
  <div style="margin-top:16px;padding-top:12px;border-top:1px solid #e2e8f0;font-size:13px;color:#64748b;line-height:1.45;">
    Warm regards,<br>
    <strong style="color:#0f172a;">Tirth Patel</strong><br>
    Founder &amp; CEO, Nenotechnology (Aineno Innovation Pvt. Ltd.)<br>
    Ahmedabad, Gujarat, India<br>
    <a href="mailto:{contact_email}" style="color:#2563eb;text-decoration:none;">{contact_email}</a> &nbsp;|&nbsp; <a href="tel:{contact_phone}" style="color:#2563eb;text-decoration:none;">+91 {contact_phone}</a> &nbsp;|&nbsp; <a href="https://www.nenotechnology.com" style="color:#2563eb;text-decoration:none;">www.nenotechnology.com</a>
  </div>
</div>"""
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
    subject = f"Rescheduled: Consultation Call with Nenotechnology{company_line} — {local.strftime('%b %d, %I:%M %p')}"

    body = f"""<div style="font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.45;color:#1e293b;max-width:100%;box-sizing:border-box;">
  {LOGO_HEADER_HTML}
  <p style="margin:0 0 10px 0;margin-top:0;margin-bottom:10px;padding:0;line-height:1.45;">Hi <strong>{cust_name}</strong>,</p>
  <p style="margin:0 0 10px 0;margin-top:0;margin-bottom:10px;padding:0;line-height:1.45;">Thank you for reaching out to Nenotechnology. Your requested time slot was not available on our calendar, so we have automatically reserved the <strong>earliest available slot</strong> for you.</p>
  <div style="background:#fffbeb;border-left:4px solid #f59e0b;border-radius:6px;padding:12px 16px;margin:12px 0;">
    <p style="margin:0 0 6px 0;margin-top:0;margin-bottom:6px;padding:0;line-height:1.4;">📅 <strong>Rescheduled Date &amp; Time:</strong> {date_time_str}</p>
    <p style="margin:0 0 6px 0;margin-top:0;margin-bottom:6px;padding:0;line-height:1.4;">🎯 <strong>Discussion Topic:</strong> {topic}</p>
    <p style="margin:0;margin-top:0;padding:0;line-height:1.4;">💻 <strong>Platform:</strong> Microsoft Teams</p>
  </div>
  <div style="margin:0 0 14px 0;margin-top:0;margin-bottom:14px;padding:0;">
    <a href="{meet_link}" style="display:inline-block;background:#0f62fe;color:#ffffff;text-decoration:none;padding:10px 22px;border-radius:6px;font-weight:600;font-size:14px;text-align:center;line-height:1;">Join Microsoft Teams Meeting</a>
  </div>
  <p style="margin:0 0 10px 0;margin-top:0;margin-bottom:10px;font-size:14px;color:#475569;padding:0;line-height:1.45;">A calendar invite has also been sent to your email. If this time doesn't work for you, simply reply to this email and we'll gladly arrange another slot.</p>
  <div style="margin-top:16px;padding-top:12px;border-top:1px solid #e2e8f0;font-size:13px;color:#64748b;line-height:1.45;">
    Warm regards,<br>
    <strong style="color:#0f172a;">Tirth Patel</strong><br>
    Founder &amp; CEO, Nenotechnology (Aineno Innovation Pvt. Ltd.)<br>
    Ahmedabad, Gujarat, India<br>
    <a href="mailto:{contact_email}" style="color:#0f62fe;text-decoration:none;">{contact_email}</a> &nbsp;|&nbsp; <a href="tel:{contact_phone}" style="color:#0f62fe;text-decoration:none;">+91 {contact_phone}</a> &nbsp;|&nbsp; <a href="https://www.nenotechnology.com" style="color:#0f62fe;text-decoration:none;">www.nenotechnology.com</a>
  </div>
</div>"""
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
