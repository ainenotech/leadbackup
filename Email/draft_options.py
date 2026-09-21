import os
import re
from typing import Optional, Tuple


def _format_lead_name(name: Optional[str]) -> str:
    if not name or str(name).strip().lower() in ("nan", "none", ""):
        return "there"
    clean = str(name).strip()
    return clean.title() if clean.islower() else clean


def _format_company_name(company: Optional[str], fallback: str = "your team") -> str:
    if not company or str(company).strip().lower() in ("nan", "none", ""):
        return fallback
    return str(company).strip()


FONT_STACK = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
LOGO_URL = "https://res.cloudinary.com/dqreqsjas/image/upload/v1789542387/logo-dark.png"
LOGO_HEADER_HTML = f'<div style="margin:0 0 16px 0;padding:0 0 12px 0;border-bottom:1px solid #eef0f4;"><img src="{LOGO_URL}" alt="Nenotechnology" width="132" height="34" style="display:block;border:0;outline:none;text-decoration:none;-ms-interpolation-mode:bicubic;width:132px;height:34px;max-height:36px;pointer-events:none;"></div>'


def get_draft_template_option(
    option_id: int,
    name: Optional[str] = None,
    company: Optional[str] = None,
    cta_url: Optional[str] = None,
) -> Tuple[str, str]:
    """Generates (subject, html_body) for one of the 3 predefined high-converting draft options.
    Personalizes recipient name, company, and consultation CTA link.
    Embeds the real Nenotechnology logo (hosted on Cloudinary CDN).
    Excludes unsubscribe link per user specification.
    """
    cust_name = _format_lead_name(name)
    comp_name_for_body = _format_company_name(company, fallback="your team")
    has_company = bool(company and str(company).strip().lower() not in ("nan", "none", ""))
    company_clean = str(company).strip() if has_company else ""
    greeting = f"Dear {cust_name}," if cust_name != "there" else "Hi there,"

    default_booking = os.getenv(
        "BOOKING_FORM_URL",
        "https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled",
    )
    # Guarantee the consultation button uses the real Microsoft Bookings link
    if (
        not cta_url
        or str(cta_url).strip().lower() in ("nan", "none", "")
        or "localhost" in str(cta_url).lower()
        or "127.0.0.1" in str(cta_url)
        or "/form?token=" in str(cta_url)
    ):
        booking_url = default_booking
    else:
        booking_url = cta_url.strip()
    sender_email = os.getenv("MS_SENDER_EMAIL", "support@nenotechnology.com")
    contact_email = os.getenv("CONTACT_EMAIL", "sales@nenotechnology.com")
    contact_phone = os.getenv("CONTACT_PHONE", "7863852024")

    if option_id == 1:
        # Primary Template: Forward Deployed Engineers & Scalable Tech Talent
        if company_clean:
            subject = f"Smarter Systems for {company_clean} - AI & Automation by Nenotechnology"
        else:
            subject = "Smarter Systems, Less Overhead - AI Solutions by Nenotechnology"

        body = f"""<div style="font-family:{FONT_STACK};font-size:15px;line-height:1.6;color:#1E293B;max-width:100%;box-sizing:border-box;-webkit-font-smoothing:antialiased;">
  {LOGO_HEADER_HTML}
  <p style="margin:0 0 14px 0;padding:0;line-height:1.6;">{greeting}</p>
  <p style="margin:0 0 14px 0;padding:0;line-height:1.6;">I hope you and the team at {comp_name_for_body} are doing well.</p>
  <p style="margin:0 0 16px 0;padding:0;line-height:1.6;">I'm Tirth Patel, Founder &amp; CEO of <strong style="color:#0F172A;">Nenotechnology</strong> (Aineno Innovation Pvt. Ltd.), based in Ahmedabad, India. We help Australian agencies and businesses cut operational overhead and unlock new efficiency through purpose-built AI solutions - without the enterprise price tag.</p>
  <div style="margin:0 0 20px 0;padding:16px 20px;background-color:#F8FAFC;border-left:3px solid #0f62fe;border-radius:0 6px 6px 0;font-size:14.5px;line-height:1.6;color:#1E293B;">
    <strong style="color:#0F172A;">Would you be open to a 20-minute call</strong> to explore what would be most useful for {comp_name_for_body} right now? No pitch deck, no obligation - just a focused conversation about where AI and automation can save you real time.
  </div>
  <div style="margin:0 0 22px 0;padding:0;">
    <a href="{booking_url}" style="display:inline-block;background:#0f62fe;color:#ffffff;text-decoration:none;padding:12px 28px;border-radius:6px;font-weight:600;font-size:14px;text-align:center;line-height:1;letter-spacing:0.2px;">Book a Free Consultation</a>
  </div>
  <p style="margin:0 0 12px 0;padding:0;font-weight:700;color:#0F172A;font-size:16px;line-height:1.4;letter-spacing:-0.2px;">What you get</p>
  <p style="margin:0 0 14px 0;padding:0;font-size:14.5px;line-height:1.6;color:#1E293B;"><strong style="color:#0F172A;">Forward Deployed Engineers.</strong> One person who takes a requirement through build and deployment - using AI coding tools and agentic workflows to move at several times normal speed.</p>
  <p style="margin:0 0 14px 0;padding:0;font-size:14.5px;line-height:1.6;color:#1E293B;"><strong style="color:#0F172A;">AI and full-stack developers.</strong> AI agent developers, backend, full-stack and deployment engineers - already on our bench, not being recruited after you sign.</p>
  <p style="margin:0 0 14px 0;padding:0;font-size:14.5px;line-height:1.6;color:#1E293B;"><strong style="color:#0F172A;">Vetted before you meet them.</strong> Every engineer clears our five-stage screening. You interview the shortlist and pick who joins you.</p>
  <p style="margin:0 0 14px 0;padding:0;font-size:14.5px;line-height:1.6;color:#1E293B;"><strong style="color:#0F172A;">A fraction of local contract rates.</strong> Fixed monthly cost per developer. No payroll, no super, no desk, no notice period risk.</p>
  <p style="margin:0 0 16px 0;padding:0;line-height:1.6;">Our goal is simple: help businesses like yours reduce operational overhead while improving efficiency and customer experience - at a fraction of local agency costs.</p>
  <p style="margin:0 0 4px 0;padding:0;font-size:13.5px;line-height:1.5;color:#64748B;">Or simply reply to this email - it comes straight to me.</p>
  <div style="margin-top:20px;padding-top:14px;border-top:1px solid #eef0f4;font-size:13.5px;color:#475569;line-height:1.5;">
    Warm regards,<br>
    <strong style="color:#0F172A;">Tirth Patel</strong><br>
    Founder &amp; CEO, Nenotechnology (Aineno Innovation Pvt. Ltd.)<br>
    <span style="font-size:12.5px;color:#64748B;">TEDx Speaker &bull; 300,000+ Followers &bull; Co-founder, Gujarat AI Society &amp; Agentic Bharat</span><br>
    Ahmedabad, Gujarat, India<br>
    <a href="mailto:{contact_email}" style="color:#0f62fe;text-decoration:none;">{contact_email}</a> &nbsp;|&nbsp; <a href="tel:{contact_phone}" style="color:#0f62fe;text-decoration:none;">+91 {contact_phone}</a> &nbsp;|&nbsp; <a href="https://www.nenotechnology.com" style="color:#0f62fe;text-decoration:none;">www.nenotechnology.com</a> &nbsp;|&nbsp; <a href="https://www.linkedin.com/in/tirth-patel-nenotechnology/" style="color:#0f62fe;text-decoration:none;">LinkedIn</a>
  </div>
</div>"""
        return subject, body

    elif option_id == 2:
        # Returning Client Check-in & Free Consultation
        if company_clean:
            subject = f"Checking In - Complimentary Consultation for {company_clean}"
        else:
            subject = "Checking In - Complimentary Consultation from Nenotechnology"

        body = f"""<div style="font-family:{FONT_STACK};font-size:15px;line-height:1.6;color:#1E293B;max-width:100%;box-sizing:border-box;-webkit-font-smoothing:antialiased;">
  {LOGO_HEADER_HTML}
  <p style="margin:0 0 14px 0;padding:0;line-height:1.6;">{greeting}</p>
  <p style="margin:0 0 14px 0;padding:0;line-height:1.6;">I hope this message finds you well. As a returning client, the first consultation is on us.</p>
  <div style="margin:0 0 20px 0;padding:16px 20px;background-color:#F8FAFC;border-left:3px solid #0f62fe;border-radius:0 6px 6px 0;font-size:14.5px;line-height:1.6;color:#1E293B;">
    <strong style="color:#0F172A;">Would you be open to a 20-minute call</strong> to explore what would be most useful for {comp_name_for_body} right now? No pitch deck, no obligation - just a focused conversation.
  </div>
  <div style="margin:0 0 22px 0;padding:0;">
    <a href="{booking_url}" style="display:inline-block;background:#0f62fe;color:#ffffff;text-decoration:none;padding:12px 28px;border-radius:6px;font-weight:600;font-size:14px;text-align:center;line-height:1;letter-spacing:0.2px;">Schedule a Call</a>
  </div>
  <p style="margin:0 0 14px 0;padding:0;line-height:1.6;">It has been some time since our last interaction, and I wanted to check in personally rather than let the connection go quiet. Working with {comp_name_for_body} was a great experience for our team, and we would welcome the chance to support you again.</p>
  <p style="margin:0 0 14px 0;padding:0;line-height:1.6;">If you have any IT challenges on your plate at the moment - systems that need modernising, processes taking up too much manual time, or a new project in planning - I would be glad to talk it through, with no obligation on your side.</p>
  <p style="margin:0 0 14px 0;padding:0;line-height:1.6;">Simply click above or reply with a day and time that suits you, and I will arrange the rest.</p>
  <p style="margin:0 0 4px 0;padding:0;font-size:13.5px;line-height:1.5;color:#64748B;">Or simply reply to this email - it comes straight to me.</p>
  <div style="margin-top:20px;padding-top:14px;border-top:1px solid #eef0f4;font-size:13.5px;color:#475569;line-height:1.5;">
    Best regards,<br>
    <strong style="color:#0F172A;">Tirth Patel</strong><br>
    Founder &amp; CEO, Nenotechnology (Aineno Innovation Pvt. Ltd.)<br>
    <span style="font-size:12.5px;color:#64748B;">TEDx Speaker &bull; 300,000+ Followers &bull; Co-founder, Gujarat AI Society &amp; Agentic Bharat</span><br>
    Ahmedabad, Gujarat, India<br>
    <a href="mailto:{contact_email}" style="color:#0f62fe;text-decoration:none;">{contact_email}</a> &nbsp;|&nbsp; <a href="tel:{contact_phone}" style="color:#0f62fe;text-decoration:none;">+91 {contact_phone}</a> &nbsp;|&nbsp; <a href="https://www.nenotechnology.com" style="color:#0f62fe;text-decoration:none;">www.nenotechnology.com</a> &nbsp;|&nbsp; <a href="https://www.linkedin.com/in/tirth-patel-nenotechnology/" style="color:#0f62fe;text-decoration:none;">LinkedIn</a>
  </div>
</div>"""
        return subject, body

    elif option_id == 3:
        # Complimentary AI & IT Audit Offer
        if company_clean:
            subject = f"Complimentary AI & IT Systems Audit for {company_clean}"
        else:
            subject = "Complimentary AI & IT Systems Audit - Nenotechnology"

        body = f"""<div style="font-family:{FONT_STACK};font-size:15px;line-height:1.6;color:#1E293B;max-width:100%;box-sizing:border-box;-webkit-font-smoothing:antialiased;">
  {LOGO_HEADER_HTML}
  <p style="margin:0 0 14px 0;padding:0;line-height:1.6;">{greeting}</p>
  <p style="margin:0 0 14px 0;padding:0;line-height:1.6;">I hope you and the team at {comp_name_for_body} are doing well. Because you have worked with us before, I would like to offer {comp_name_for_body} a complimentary AI &amp; IT systems audit.</p>
  <div style="margin:0 0 20px 0;padding:16px 20px;background-color:#F8FAFC;border-left:3px solid #0f62fe;border-radius:0 6px 6px 0;font-size:14.5px;line-height:1.6;color:#1E293B;">
    <strong style="color:#0F172A;">Would you be open to a 20-minute call</strong> to explore what would be most useful for {comp_name_for_body} right now? No pitch deck, no obligation - just a focused session to identify your biggest automation wins.
  </div>
  <div style="margin:0 0 22px 0;padding:0;">
    <a href="{booking_url}" style="display:inline-block;background:#0f62fe;color:#ffffff;text-decoration:none;padding:12px 28px;border-radius:6px;font-weight:600;font-size:14px;text-align:center;line-height:1;letter-spacing:0.2px;">Claim Your Free Audit</a>
  </div>
  <p style="margin:0 0 12px 0;padding:0;font-weight:700;color:#0F172A;font-size:16px;line-height:1.4;letter-spacing:-0.2px;">What we'll cover in one session</p>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 16px 0;">
    <tr><td style="border-top:1px solid #E2E8F0;padding:12px 0;font-size:14.5px;line-height:1.6;color:#1E293B;"><strong style="color:#0F172A;">System Review.</strong> Walk through your current systems and pinpoint the manual bottlenecks draining your team's time.</td></tr>
    <tr><td style="border-top:1px solid #E2E8F0;padding:12px 0;font-size:14.5px;line-height:1.6;color:#1E293B;"><strong style="color:#0F172A;">Top 3 Automation Wins.</strong> Highlight the three processes with the highest return on automation investment.</td></tr>
    <tr><td style="border-top:1px solid #E2E8F0;border-bottom:1px solid #E2E8F0;padding:12px 0;font-size:14.5px;line-height:1.6;color:#1E293B;"><strong style="color:#0F172A;">Practical Roadmap.</strong> A clear, actionable plan with realistic timelines and costs - no vague promises.</td></tr>
  </table>
  <p style="margin:0 0 14px 0;padding:0;line-height:1.6;">There is zero cost and no commitment - if nothing makes sense for you right now, we will tell you that honestly.</p>
  <p style="margin:0 0 14px 0;padding:0;line-height:1.6;">Looking forward to speaking with you.</p>
  <p style="margin:0 0 4px 0;padding:0;font-size:13.5px;line-height:1.5;color:#64748B;">Or simply reply to this email - it comes straight to me.</p>
  <div style="margin-top:20px;padding-top:14px;border-top:1px solid #eef0f4;font-size:13.5px;color:#475569;line-height:1.5;">
    Warm regards,<br>
    <strong style="color:#0F172A;">Tirth Patel</strong><br>
    Founder &amp; CEO, Nenotechnology (Aineno Innovation Pvt. Ltd.)<br>
    <span style="font-size:12.5px;color:#64748B;">TEDx Speaker &bull; 300,000+ Followers &bull; Co-founder, Gujarat AI Society &amp; Agentic Bharat</span><br>
    Ahmedabad, Gujarat, India<br>
    <a href="mailto:{contact_email}" style="color:#0f62fe;text-decoration:none;">{contact_email}</a> &nbsp;|&nbsp; <a href="tel:{contact_phone}" style="color:#0f62fe;text-decoration:none;">+91 {contact_phone}</a> &nbsp;|&nbsp; <a href="https://www.nenotechnology.com" style="color:#0f62fe;text-decoration:none;">www.nenotechnology.com</a> &nbsp;|&nbsp; <a href="https://www.linkedin.com/in/tirth-patel-nenotechnology/" style="color:#0f62fe;text-decoration:none;">LinkedIn</a>
  </div>
</div>"""
        return subject, body

    else:
        raise ValueError(f"Unknown template option ID: {option_id}. Must be 1, 2, or 3.")


OPTIONS_METADATA = [
    {
        "id": 1,
        "title": "Primary Template (Forward-Deployed Engineers)",
        "short_title": "Primary Template",
        "cta_label": "Book a Free Consultation",
        "badge": "⭐ Primary / Recommended",
        "icon": "⭐",
        "desc": "Primary high-converting template: forward-deployed engineers, on-bench AI & full-stack developers, 5-stage vetting, and free consultation CTA.",
    },
    {
        "id": 2,
        "title": "Returning Client Check-in",
        "short_title": "Returning Client",
        "cta_label": "Schedule a Call",
        "badge": "Relationship Check-in",
        "icon": "🤝",
        "desc": "Personal outreach to returning clients offering a complimentary first consultation for current IT needs.",
    },
    {
        "id": 3,
        "title": "Complimentary AI & IT Audit",
        "short_title": "Free AI & IT Audit",
        "cta_label": "Claim Your Free Audit",
        "badge": "Free System Audit",
        "icon": "🔍",
        "desc": "Offers a complimentary AI & IT audit session to pinpoint bottlenecks and highest-ROI automation opportunities.",
    },
]
