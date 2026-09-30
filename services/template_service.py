import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

TEMPLATES_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
TEMPLATES_JSON_PATH = os.path.join(TEMPLATES_DATA_DIR, "templates.json")

DEFAULT_LOGO_URL = "https://res.cloudinary.com/dqreqsjas/image/upload/v1790076736/logo-light.png"
DEFAULT_LOGO_DARK_URL = "https://res.cloudinary.com/dqreqsjas/image/upload/v1790076736/logo-dark.png"
DEFAULT_LINKEDIN_URL = "https://www.linkedin.com/in/tirth-patel-nenotechnology/"
DEFAULT_MOHIT_LINKEDIN_URL = os.getenv("MOHIT_LINKEDIN_URL", "https://www.linkedin.com/company/nenotechnology/")
DEFAULT_PORTFOLIO_URL = os.getenv("PORTFOLIO_URL", "https://www.nenotechnology.com/")
DEFAULT_MOHIT_PORTFOLIO_URL = os.getenv("MOHIT_PORTFOLIO_URL", "https://www.nenotechnology.us/")
DEFAULT_TWITTER_URL = os.getenv("TWITTER_URL", "https://x.com/nenotechnology")
DEFAULT_INSTAGRAM_URL = os.getenv("INSTAGRAM_URL", "https://www.instagram.com/nenotechnology")
DEFAULT_FACEBOOK_URL = os.getenv("FACEBOOK_URL", "https://www.facebook.com/nenotechnology")
DEFAULT_BOOKING_URL = os.getenv(
    "BOOKING_FORM_URL",
    "https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled",
)
DEFAULT_MOHIT_PHONE = os.getenv("MOHIT_PHONE", "+14239003550")

# ─────────────────────────────────────────────────────────────
# 8 USER-PROVIDED HIGH-CONVERTING HTML TEMPLATES
# ─────────────────────────────────────────────────────────────

def _build_responsive_template_html(
    title: str,
    preheader: str,
    intro_html: str,
    callout_html: str,
    cta_text: str,
    section_heading: str,
    bullets_html: str,
    closing_html: str,
    accent_color: str = "#1A5CFF",
    website_callout_html: str = "",
    signature_html: str = "",
    footer_address_html: str = "",
    website_url: str = "https://www.nenotechnology.com/",
) -> str:
    """Generates a pixel-perfect, fully responsive HTML email template
    featuring an executive dark navy top header banner with centered light logo,
    callout question box, bullets, dedicated website visit section, and customizable signature.
    """
    if not footer_address_html:
        footer_address_html = "Aineno Innovation Pvt. Ltd. &middot; Ahmedabad, Gujarat, India"
    if not website_callout_html:
        website_callout_html = f"""<div style="margin:18px 0 16px 0;padding:12px 18px;background-color:#f8fafc;border:1px solid #e2e8f0;border-left:3px solid {accent_color};border-radius:0 8px 8px 0;font-size:13.5px;line-height:1.5;color:#334155;">
            🌐 <strong>Explore our work:</strong> Please visit our website at <a href="https://www.nenotechnology.com/" target="_blank" style="color:{accent_color};font-weight:600;text-decoration:underline;">Nenotechnology</a> to explore our complete suite of AI solutions, client case studies, and live production demos.
          </div>"""

    if not signature_html:
        signature_html = f"""<div style="margin-top:18px;padding-top:14px;border-top:1px solid #e2e8f0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
            <div style="font-size:13px;color:#64748b;margin-bottom:2px;">Warm regards,</div>
            <div style="font-size:15px;font-weight:700;color:#0f172a;line-height:1.3;">Tirth Patel</div>
            <div style="font-size:12.5px;color:#334155;margin-top:1px;">Founder &amp; CEO, Nenotechnology (Aineno Innovation Pvt. Ltd.)</div>
            <div style="font-size:11.5px;color:#94a3b8;margin-top:2px;">TEDx Speaker &bull; 300,000+ Followers &bull; Co-founder, Gujarat AI Society &amp; Agentic Bharat</div>
            <div style="font-size:11.5px;color:#94a3b8;margin-top:1px;">Ahmedabad, Gujarat, India</div>
            <div class="sig-links" style="font-size:12px;margin-top:6px;">
              <a href="mailto:sales@nenotechnology.com" style="color:{accent_color};text-decoration:none;">sales@nenotechnology.com</a> &nbsp;|&nbsp;
              <a href="tel:+917863852024" style="color:{accent_color};text-decoration:none;">+91 7863852024</a> &nbsp;|&nbsp;
              <a href="https://www.nenotechnology.com" target="_blank" style="color:{accent_color};text-decoration:none;">www.nenotechnology.com</a> &nbsp;|&nbsp;
              <a href="LINKEDIN_URL" target="_blank" style="color:{accent_color};text-decoration:none;">LinkedIn</a>
            </div>
          </div>"""

    return f"""<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<meta name="supported-color-schemes" content="light">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<title>{title}</title>
<!--[if mso]>
<xml>
<o:OfficeDocumentSettings>
<o:AllowPNG/>
<o:PixelsPerInch>96</o:PixelsPerInch>
</o:OfficeDocumentSettings>
</xml>
<![endif]-->
<style>
  body {{
    margin: 0;
    padding: 0;
    background-color: #f0f4f8;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }}
  table {{
    border-collapse: collapse;
    mso-table-lspace: 0pt;
    mso-table-rspace: 0pt;
  }}
  img {{
    -ms-interpolation-mode: bicubic;
    border: 0;
    outline: none;
    text-decoration: none;
  }}
  @media only screen and (max-width: 620px) {{
    .outer-table {{ padding: 10px 4px !important; }}
    .email-container {{ width: 100% !important; border-radius: 10px !important; }}
    .content-cell {{ padding: 24px 20px !important; }}
    .cta-btn {{ display: block !important; width: 100% !important; text-align: center !important; box-sizing: border-box !important; padding: 14px 20px !important; }}
    .sig-links {{ font-size: 11px !important; }}
  }}
</style>
</head>
<body style="margin:0;padding:0;background-color:#f0f4f8;">

<div style="display:none;max-height:0;overflow:hidden;opacity:0;font-size:1px;line-height:1px;color:#f0f4f8;">
  {preheader}
</div>

<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="outer-table" style="background-color:#f0f4f8;padding:24px 10px;">
<tr>
  <td align="center">

    <!-- Main Card Container with Dark Navy Top Header -->
    <table role="presentation" width="620" cellpadding="0" cellspacing="0" border="0" class="email-container" style="width:620px;max-width:100%;background-color:#ffffff;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px -2px rgba(0,0,0,0.08),0 1px 3px rgba(0,0,0,0.04);">
      
      <!-- Top Header Banner (Dark Navy #071a2d with Centered Light Logo) -->
      <tr>
        <td align="center" style="background-color:#071a2d;padding:20px 24px 18px 24px;text-align:center;border-top-left-radius:12px;border-top-right-radius:12px;border-bottom:3px solid {accent_color};">
          <a href="{website_url}" target="_blank" style="text-decoration:none;display:inline-block;">
            <img src="LOGO_URL" alt="Neno Technology" width="168" height="43" style="display:block;margin:0 auto;border:0;outline:none;text-decoration:none;-ms-interpolation-mode:bicubic;width:168px;height:auto;max-height:45px;" />
          </a>
        </td>
      </tr>

      <!-- Card Body -->
      <tr>
        <td class="content-cell" style="padding:28px 32px 24px 32px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;font-size:15px;line-height:1.55;color:#1e293b;text-align:left;">

          <!-- Greeting & Intro -->
          <p style="margin:0 0 8px 0;font-size:15px;line-height:1.55;color:#1e293b;">Dear {{FirstName}},</p>
          <p style="margin:0 0 8px 0;font-size:15px;line-height:1.55;color:#1e293b;">I hope you and the team at {{Company}} are doing well.</p>
          <p style="margin:0 0 12px 0;font-size:15px;line-height:1.55;color:#1e293b;">
            {intro_html}
          </p>

          <!-- Callout Question Box -->
          <div style="border-left:3px solid {accent_color};background-color:#f8fafc;padding:12px 16px;margin:12px 0 14px 0;border-radius:0 6px 6px 0;font-size:14.5px;line-height:1.5;color:#0f172a;font-weight:500;">
            {callout_html}
          </div>

          <!-- CTA Button -->
          <div style="margin:14px 0 18px 0;">
            <a href="BOOKING_LINK" target="_blank" class="cta-btn" style="display:inline-block;background-color:{accent_color};color:#ffffff;padding:11px 26px;border-radius:6px;font-weight:600;font-size:14px;text-decoration:none;letter-spacing:0.01em;box-shadow:0 2px 4px rgba(0,0,0,0.12);mso-padding-alt:11px 26px;">
              {cta_text} &rarr;
            </a>
          </div>

          <!-- Section Heading -->
          <div style="font-size:15px;font-weight:700;color:#0f172a;margin:16px 0 10px 0;line-height:1.3;">
            {section_heading}
          </div>

          <!-- Bullets -->
          <div style="font-size:14px;line-height:1.55;color:#334155;">
            {bullets_html}
          </div>

          <!-- Website Content Section -->
          {website_callout_html}

          <!-- Closing pitch -->
          <p style="margin:14px 0 8px 0;font-size:14px;line-height:1.55;color:#1e293b;">
            {closing_html}
          </p>
          <p style="margin:0 0 0 0;font-size:12.5px;line-height:1.45;color:#94a3b8;">
            Or simply reply to this email &mdash; it comes straight to me.
          </p>

          <!-- Signature -->
          {signature_html}

        </td>
      </tr>
    </table>

    <!-- Footer -->
    <table role="presentation" width="620" cellpadding="0" cellspacing="0" border="0" style="width:620px;max-width:100%;margin-top:10px;">
      <tr>
        <td style="font-size:11px;line-height:1.45;color:#94a3b8;text-align:center;padding:6px 12px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
          {footer_address_html}<br>
          Stay updated with our latest AI insights &amp; research &middot; <a href="SUBSCRIBE_LINK" style="color:#94a3b8;text-decoration:underline;">Subscribe</a>
        </td>
      </tr>
    </table>

  </td>
</tr>
</table>

</body>
</html>"""


# ─────────────────────────────────────────────────────────────
# 7 DISTINCT, HIGH-CONVERTING RESPONSIVE HTML TEMPLATES
# ─────────────────────────────────────────────────────────────

RAW_TEMPLATE_1 = _build_responsive_template_html(
    title="Quick idea for {{Company}}",
    preheader="A senior AI engineer starting next week at a fixed monthly cost. 20 minutes to see if it fits {{Company}}.",
    intro_html="I'm Tirth Patel, Founder &amp; CEO of <strong>Nenotechnology</strong> (Aineno Innovation Pvt. Ltd.), based in Ahmedabad, India. We help Australian agencies and businesses cut operational overhead and unlock new efficiency through purpose-built AI solutions &mdash; without the enterprise price tag.",
    callout_html="Would you be open to a 20-minute call to explore what would be most useful for {{Company}} right now? No pitch deck, no obligation &mdash; just a focused conversation about where AI and automation can save you real time.",
    cta_text="Book a Free Consultation",
    section_heading="What you get",
    bullets_html="""<p style="margin:0 0 6px 0;"><strong style="color:#0f172a;">Forward Deployed Engineers.</strong> One person who takes a requirement through build and deployment &mdash; using AI coding tools and agentic workflows to move at several times normal speed.</p>
<p style="margin:0 0 6px 0;"><strong style="color:#0f172a;">AI and full-stack developers.</strong> AI agent developers, backend, full-stack and deployment engineers &mdash; already on our bench, not being recruited after you sign.</p>
<p style="margin:0 0 6px 0;"><strong style="color:#0f172a;">Vetted before you meet them.</strong> Every engineer clears our five-stage screening. You interview the shortlist and pick who joins you.</p>
<p style="margin:0;"><strong style="color:#0f172a;">A fraction of local contract rates.</strong> Fixed monthly cost per developer. No payroll, no super, no desk, no notice period risk.</p>""",
    website_callout_html="""<div style="margin:18px 0 16px 0;padding:12px 18px;background-color:#f8fafc;border:1px solid #e2e8f0;border-left:3px solid #1A5CFF;border-radius:0 8px 8px 0;font-size:13.5px;line-height:1.5;color:#334155;">
            🌐 <strong>Explore our engineering capabilities:</strong> Please visit our website at <a href="https://www.nenotechnology.com/" target="_blank" style="color:#1A5CFF;font-weight:600;text-decoration:underline;">Nenotechnology</a> to see our full tech stack, developer screening benchmarks, and client case studies.
          </div>""",
    closing_html="Our goal is simple: help businesses like yours reduce operational overhead while improving efficiency and customer experience &mdash; at a fraction of local agency costs.",
    accent_color="#1A5CFF",
)

RAW_TEMPLATE_2 = _build_responsive_template_html(
    title="Zero Missed Inbound Leads for {{Company}} - AI Calling Agents",
    preheader="What if {{Company}} could qualify every inbound customer call in under 60 seconds, 24/7?",
    intro_html="I'm Tirth Patel, Founder &amp; CEO of <strong>Nenotechnology</strong> (Aineno Innovation Pvt. Ltd.) in Ahmedabad. We build human-sounding, autonomous AI voice agents that pick up, qualify, and book inbound inquiries for Australian businesses within 60 seconds.",
    callout_html="Could {{Company}} benefit from an AI voice agent answering customer calls in under 60 seconds 24/7? Let's take 15 minutes to run a live demonstration over the phone.",
    cta_text="Experience a Live Voice AI Demo",
    section_heading="How Autonomous Voice Agents Transform Your Pipeline",
    bullets_html="""<p style="margin:0 0 6px 0;"><strong style="color:#0f172a;">Sub-Second Voice Latency.</strong> Natural, human-like voice agents that navigate multi-turn conversations, answer service questions, and overcome objections flawlessly.</p>
<p style="margin:0 0 6px 0;"><strong style="color:#0f172a;">24/7 Lead Capture.</strong> Never lose after-hours, holiday, or weekend leads again. Every call is answered, qualified, and scheduled on your calendar instantly.</p>
<p style="margin:0 0 6px 0;"><strong style="color:#0f172a;">Instant CRM &amp; Calendar Sync.</strong> Real-time call transcription, structured notes, and confirmed bookings pushed automatically to HubSpot, Salesforce, or Google Calendar.</p>
<p style="margin:0;"><strong style="color:#0f172a;">Unlimited Concurrent Capacity.</strong> Handle 100 simultaneous calls during marketing spikes without hiring extra call center staff or paying per-minute agency fees.</p>""",
    website_callout_html="""<div style="margin:18px 0 16px 0;padding:12px 18px;background-color:#f8fafc;border:1px solid #e2e8f0;border-left:3px solid #7C3AED;border-radius:0 8px 8px 0;font-size:13.5px;line-height:1.5;color:#334155;">
            🌐 <strong>Listen to live voice demos:</strong> Please visit our website at <a href="https://www.nenotechnology.com/" target="_blank" style="color:#7C3AED;font-weight:600;text-decoration:underline;">Nenotechnology</a> to hear sample voice AI recordings, explore inbound call flows, and view client ROI metrics.
          </div>""",
    closing_html="Our voice agents eliminate missed opportunities, slash response latency from hours to seconds, and book meetings directly into your team's calendar.",
    accent_color="#7C3AED",
)

RAW_TEMPLATE_3 = _build_responsive_template_html(
    title="Ship AI projects faster at {{Company}}, without the hiring wait",
    preheader="Senior AI and LLM engineers ready on bench to build your agentic workflows and custom features.",
    intro_html="I'm Tirth Patel, Founder &amp; CEO of <strong>Nenotechnology</strong> (Aineno Innovation Pvt. Ltd.) in Ahmedabad. We provide vetted AI &amp; LLM engineering squads who help tech teams build and ship production agentic workflows, RAG systems, and custom AI features in weeks.",
    callout_html="Have an AI feature, RAG pipeline, or custom agent backlog waiting to be built at {{Company}}? Let's spend 20 minutes reviewing the technical architecture and delivery timeline.",
    cta_text="Schedule an AI Architecture Call",
    section_heading="Engineering Capabilities on Demand",
    bullets_html="""<p style="margin:0 0 6px 0;"><strong style="color:#0f172a;">Autonomous Agentic Workflows.</strong> Multi-agent systems built with LangGraph, LlamaIndex, and custom tool integrations that execute complex multi-step reasoning autonomously.</p>
<p style="margin:0 0 6px 0;"><strong style="color:#0f172a;">Enterprise RAG &amp; Hybrid Search.</strong> Highly accurate knowledge retrieval pipelines with semantic re-ranking, token-cost optimization, and strict anti-hallucination guardrails.</p>
<p style="margin:0 0 6px 0;"><strong style="color:#0f172a;">Bench Ready Next Week.</strong> Senior Python, TypeScript, FastAPI, and Next.js engineers who connect to your GitHub repo and Jira on day one &mdash; no recruiting lag.</p>
<p style="margin:0;"><strong style="color:#0f172a;">Predictable Monthly Sprints.</strong> Fixed monthly pricing per engineer with transparent weekly deliverables and zero long-term vendor lock-in.</p>""",
    website_callout_html="""<div style="margin:18px 0 16px 0;padding:12px 18px;background-color:#f8fafc;border:1px solid #e2e8f0;border-left:3px solid #0284C7;border-radius:0 8px 8px 0;font-size:13.5px;line-height:1.5;color:#334155;">
            🌐 <strong>Explore our AI architectures:</strong> Please visit our website at <a href="https://www.nenotechnology.com/" target="_blank" style="color:#0284C7;font-weight:600;text-decoration:underline;">Nenotechnology</a> to see our LangGraph multi-agent builds, enterprise RAG pipelines, and technical blueprints.
          </div>""",
    closing_html="Whether you need an end-to-end AI product built from scratch or an extra engineer to clear your backlog, our squad delivers fast, production-grade code.",
    accent_color="#0284C7",
)

RAW_TEMPLATE_4 = _build_responsive_template_html(
    title="Automating repetitive manual operations at {{Company}}",
    preheader="Stop spending 15-20 hours every week manually copying data between email, spreadsheets, and CRM tools.",
    intro_html="I'm Tirth Patel, Founder &amp; CEO of <strong>Nenotechnology</strong> (Aineno Innovation Pvt. Ltd.) in Ahmedabad. We build unified automation pipelines that eliminate 15 to 20 hours every week of manual data transfer between emails, spreadsheets, WhatsApp, and CRMs.",
    callout_html="Where is {{Company}} losing the most hours each week to repetitive copy-paste work? Let's take 20 minutes to pinpoint high-impact automation quick wins.",
    cta_text="Review Automation Opportunities",
    section_heading="What We Automate For Your Business",
    bullets_html="""<p style="margin:0 0 6px 0;"><strong style="color:#0f172a;">Cross-Platform Pipeline Sync.</strong> Connect your CRM, email inboxes, WhatsApp Business API, accounting platforms, and databases into zero-touch automated workflows.</p>
<p style="margin:0 0 6px 0;"><strong style="color:#0f172a;">Automated Document &amp; Invoice Parsing.</strong> Extract structured data from supplier invoices, client contracts, and receipts automatically with 99.8% precision.</p>
<p style="margin:0 0 6px 0;"><strong style="color:#0f172a;">Zero Manual Entry Errors.</strong> Replace fragile human data copying with automated schema validation, webhook alerts, and error failover logging.</p>
<p style="margin:0;"><strong style="color:#0f172a;">Fast 7-14 Day Turnaround.</strong> Most operational bottlenecks can be fully automated within 1 to 2 weeks without disrupting your day-to-day business.</p>""",
    website_callout_html="""<div style="margin:18px 0 16px 0;padding:12px 18px;background-color:#f8fafc;border:1px solid #e2e8f0;border-left:3px solid #059669;border-radius:0 8px 8px 0;font-size:13.5px;line-height:1.5;color:#334155;">
            🌐 <strong>Explore our automation workflows:</strong> Please visit our website at <a href="https://www.nenotechnology.com/" target="_blank" style="color:#059669;font-weight:600;text-decoration:underline;">Nenotechnology</a> to review how we automate ERP, CRM, invoice parsing, and cross-platform business operations.
          </div>""",
    closing_html="We free your top talent from low-value repetitive tasks so they can spend their energy speaking to clients and driving revenue.",
    accent_color="#059669",
)

RAW_TEMPLATE_5 = _build_responsive_template_html(
    title="Extending {{Company}}'s dev team with dedicated senior engineers",
    preheader="Dedicated offshore AI engineering workbench in Ahmedabad, India &mdash; 60-70% lower overhead with full time-zone alignment.",
    intro_html="I'm Tirth Patel, Founder &amp; CEO of <strong>Nenotechnology</strong> (Aineno Innovation Pvt. Ltd.) in Ahmedabad, India. We build dedicated offshore engineering squads for Australian and global tech companies, delivering senior AI and full-stack developers at 60-70% lower overhead.",
    callout_html="Considering scaling your development capacity this quarter? Let's do a quick 20-minute discussion on how our dedicated workbench model fits {{Company}}.",
    cta_text="Explore Dedicated Workbench",
    section_heading="How Our Dedicated Workbench Works",
    bullets_html="""<p style="margin:0 0 6px 0;"><strong style="color:#0f172a;">Direct Team Integration.</strong> Engineers work exclusively for {{Company}}, attend your daily standups, communicate in your Slack, and follow your coding standards.</p>
<p style="margin:0 0 6px 0;"><strong style="color:#0f172a;">Top 1% Indian Tech Talent.</strong> Every engineer clears our rigorous 5-stage technical screening, live system architecture rounds, and fluent English communication tests.</p>
<p style="margin:0 0 6px 0;"><strong style="color:#0f172a;">Guaranteed Time-Zone Alignment.</strong> Daily working hours synchronized with Australian Eastern Standard Time (AEST) and Western time zones for real-time collaboration.</p>
<p style="margin:0;"><strong style="color:#0f172a;">Zero Office or HR Overhead.</strong> We take care of state-of-the-art office facilities, high-speed fiber, compliance, laptops, and payroll &mdash; you simply assign tasks.</p>""",
    website_callout_html="""<div style="margin:18px 0 16px 0;padding:12px 18px;background-color:#f8fafc;border:1px solid #e2e8f0;border-left:3px solid #D97706;border-radius:0 8px 8px 0;font-size:13.5px;line-height:1.5;color:#334155;">
            🌐 <strong>Discover our offshore workbench model:</strong> Please visit our website at <a href="https://www.nenotechnology.com/" target="_blank" style="color:#D97706;font-weight:600;text-decoration:underline;">Nenotechnology</a> to see how our dedicated Indian engineering squads deliver seamless Australian time-zone alignment.
          </div>""",
    closing_html="Get the engineering velocity and senior talent of a dedicated development team without the local hiring costs, recruiting agency fees, or long-term liability.",
    accent_color="#D97706",
)

RAW_TEMPLATE_6 = _build_responsive_template_html(
    title="Modernizing legacy systems & internal portals for {{Company}}",
    preheader="Replace clunky spreadsheets and outdated legacy tools with slick, modern web applications powered by AI intelligence.",
    intro_html="I'm Tirth Patel, Founder &amp; CEO of <strong>Nenotechnology</strong> (Aineno Innovation Pvt. Ltd.) in Ahmedabad. We replace brittle spreadsheets, outdated legacy software, and fragmented internal tools with slick, modern web applications powered by AI intelligence.",
    callout_html="Are clunky internal tools slowing down {{Company}}'s daily operations? Let's connect for 20 minutes to see how a streamlined custom portal could accelerate your team.",
    cta_text="Discuss System Modernization",
    section_heading="Modern Portal &amp; Internal Tool Capabilities",
    bullets_html="""<p style="margin:0 0 6px 0;"><strong style="color:#0f172a;">Modern High-Performance Stack.</strong> Fast Next.js, React, Node, Python, and cloud-native serverless backends replacing slow legacy systems.</p>
<p style="margin:0 0 6px 0;"><strong style="color:#0f172a;">AI-Assisted Dashboards.</strong> Real-time operational dashboards with natural-language AI query assistants so any team member can ask questions about company data.</p>
<p style="margin:0 0 6px 0;"><strong style="color:#0f172a;">Fast Prototype to Production.</strong> Interactive clickable prototypes delivered within 5 days, production deployment within 3-4 weeks.</p>
<p style="margin:0;"><strong style="color:#0f172a;">Transparent Fixed Milestones.</strong> Clear milestone deliverables with no surprise hourly charges or scope creep.</p>""",
    website_callout_html="""<div style="margin:18px 0 16px 0;padding:12px 18px;background-color:#f8fafc;border:1px solid #e2e8f0;border-left:3px solid #4F46E5;border-radius:0 8px 8px 0;font-size:13.5px;line-height:1.5;color:#334155;">
            🌐 <strong>View modernized portal prototypes:</strong> Please visit our website at <a href="https://www.nenotechnology.com/" target="_blank" style="color:#4F46E5;font-weight:600;text-decoration:underline;">Nenotechnology</a> to see interactive prototypes, legacy migration case studies, and modern web application builds.
          </div>""",
    closing_html="Give your staff and clients a fast, modern digital interface that eliminates friction and unlocks real-time operational visibility.",
    accent_color="#4F46E5",
)

RAW_TEMPLATE_7 = _build_responsive_template_html(
    title="Founder-to-founder: Cutting overhead at {{Company}} with AI",
    preheader="Strategic, founder-to-founder advisory on pinpointing high-ROI AI opportunities and scaling margins.",
    intro_html="I'm Tirth Patel, Founder &amp; CEO of <strong>Nenotechnology</strong> (Aineno Innovation Pvt. Ltd.) in Ahmedabad. As a founder who has scaled AI systems for hundreds of thousands of users, I offer candid, practical advice to business owners on where AI creates real profit.",
    callout_html="No sales pitch, no slides &mdash; just founder-to-founder. Would you be open to a 20-minute chat about the top 2 bottlenecks holding back {{Company}}'s margins?",
    cta_text="Book a Founder Strategy Call",
    section_heading="What We Focus on During Our Call",
    bullets_html="""<p style="margin:0 0 6px 0;"><strong style="color:#0f172a;">Unvarnished Strategic Advice.</strong> Direct guidance from Tirth Patel on what AI can realistically solve today versus what is just marketing hype.</p>
<p style="margin:0 0 6px 0;"><strong style="color:#0f172a;">Tailored ROI Roadmap.</strong> Identify the specific 20% of repetitive workflows that will generate 80% of your operational savings.</p>
<p style="margin:0 0 6px 0;"><strong style="color:#0f172a;">Hands-On Implementation Squad.</strong> If there's a mutual fit, we provide the exact engineering team to execute the roadmap end-to-end.</p>
<p style="margin:0;"><strong style="color:#0f172a;">Strict Confidentiality &amp; Full IP Ownership.</strong> 100% of all intellectual property, custom models, code, and automations belong entirely to {{Company}}.</p>""",
    website_callout_html="""<div style="margin:18px 0 16px 0;padding:12px 18px;background-color:#f8fafc;border:1px solid #e2e8f0;border-left:3px solid #0D9488;border-radius:0 8px 8px 0;font-size:13.5px;line-height:1.5;color:#334155;">
            🌐 <strong>Learn more about Nenotechnology:</strong> Please visit our website at <a href="https://www.nenotechnology.com/" target="_blank" style="color:#0D9488;font-weight:600;text-decoration:underline;">Nenotechnology</a> to review our founder story, AI advisory frameworks, and real-world client deployments.
          </div>""",
    closing_html="I only take 3 advisory calls a week to ensure high impact. If you want a straight, honest perspective on AI for {{Company}}, let's connect.",
    accent_color="#0D9488",
)

RAW_TEMPLATE_8 = """<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<meta name="supported-color-schemes" content="light">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<title>A founder-to-founder note for {{Company}}</title>
<!--[if mso]>
<xml><o:OfficeDocumentSettings><o:AllowPNG/><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml>
<![endif]-->
<style>
  body { margin:0; padding:0; background-color:#f4f1ea; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif; -webkit-font-smoothing:antialiased; }
  table { border-collapse:collapse; mso-table-lspace:0pt; mso-table-rspace:0pt; }
  img { -ms-interpolation-mode:bicubic; border:0; outline:none; text-decoration:none; }
  @media only screen and (max-width:620px) {
    .outer-table { padding:10px 4px !important; }
    .email-container { width:100% !important; }
    .content-cell { padding:26px 22px !important; }
    .cta-btn { display:block !important; width:100% !important; text-align:center !important; box-sizing:border-box !important; }
    .hero-text { font-size:26px !important; line-height:33px !important; }
  }
</style>
</head>
<body style="margin:0;padding:0;background-color:#f4f1ea;">

<div style="display:none;max-height:0;overflow:hidden;opacity:0;font-size:1px;line-height:1px;color:#f4f1ea;">
  Founder to founder: how {{Company}} could get a senior AI engineer this month, not this quarter.
</div>

<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="outer-table" style="background-color:#f4f1ea;padding:26px 10px;">
<tr><td align="center">

  <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" class="email-container" style="width:600px;max-width:100%;background-color:#ffffff;border-radius:10px;overflow:hidden;border:1px solid #e6e0d3;">

    <!-- Header: logo + founder tag with dark header banner to display logo clearly -->
    <tr>
      <td style="background-color:#1c1a15;padding:22px 36px 20px 36px;border-top-left-radius:9px;border-top-right-radius:9px;border-bottom:2px solid #a08a5c;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr>
            <td align="left" valign="middle">
              <a href="https://www.nenotechnology.com/" target="_blank" style="text-decoration:none;display:inline-block;">
                <img src="LOGO_URL" alt="Neno Technology" width="145" style="display:block;border:0;width:145px;max-width:145px;height:auto;" />
              </a>
            </td>
            <td align="right" valign="middle" style="font-size:11px;letter-spacing:0.8px;color:#d4c29a;font-weight:700;">FOUNDER TO FOUNDER</td>
          </tr>
        </table>
      </td>
    </tr>

    <!-- Hero line -->
    <tr>
      <td class="content-cell" style="padding:22px 36px 0 36px;">
        <div class="hero-text" style="font-family:Georgia,'Times New Roman',serif;font-size:30px;line-height:38px;font-weight:bold;color:#1c1a15;">
          You didn't start {{Company}} to manage recruiters.
        </div>
      </td>
    </tr>

    <!-- Body -->
    <tr>
      <td class="content-cell" style="padding:20px 36px 0 36px;font-size:15.5px;line-height:1.65;color:#3b3629;">
        <p style="margin:0 0 14px 0;">Hi {{FirstName}},</p>
        <p style="margin:0 0 14px 0;">
          I'm Tirth Patel, Founder &amp; CEO of <strong style="color:#1c1a15;">Nenotechnology</strong> in Ahmedabad. I built this company for the same reason you probably built {{Company}}: I was tired of watching good ideas sit in a backlog because there was no one free to build them.
        </p>
        <p style="margin:0;">
          So we did the unglamorous part first. We built a bench of vetted AI and full-stack engineers, ready before you need them, so a "we should automate that" conversation on Monday can be a working prototype by Friday.
        </p>
      </td>
    </tr>

    <!-- Founder-specific reasons box -->
    <tr>
      <td class="content-cell" style="padding:26px 36px 0 36px;">
        <div style="font-size:16px;font-weight:700;color:#1c1a15;margin:0 0 12px 0;">Why founders choose to work with us</div>

        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr>
            <td style="padding:0 0 14px 0;border-bottom:1px solid #f0ebe0;">
              <div style="font-size:14.5px;line-height:1.55;color:#3b3629;padding-bottom:12px;">
                <strong style="color:#1c1a15;">Runway matters more than headcount.</strong> A fixed monthly cost per developer, well under local contract rates, with no payroll, super or desk to carry.
              </div>
            </td>
          </tr>
          <tr>
            <td style="padding:14px 0 14px 0;border-bottom:1px solid #f0ebe0;">
              <div style="font-size:14.5px;line-height:1.55;color:#3b3629;">
                <strong style="color:#1c1a15;">You don't have three months to hire.</strong> Our engineers are already vetted and on the bench. You interview a shortlist and pick, without running a search.
              </div>
            </td>
          </tr>
          <tr>
            <td style="padding:14px 0 0 0;">
              <div style="font-size:14.5px;line-height:1.55;color:#3b3629;">
                <strong style="color:#1c1a15;">You need someone who finishes, not just codes.</strong> Our Forward Deployed Engineers own a requirement from build to deployment, using AI coding tools to move several times faster than usual.
              </div>
            </td>
          </tr>
        </table>
      </td>
    </tr>

    <!-- CTA -->
    <tr>
      <td class="content-cell" style="padding:30px 36px 0 36px;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#fbf6ea;border-radius:10px;border:1px solid #ecdfb8;">
          <tr>
            <td style="padding:24px 26px;">
              <div style="font-size:17px;line-height:24px;font-weight:700;color:#1c1a15;">One honest 20-minute call.</div>
              <div style="font-size:14.5px;line-height:1.6;color:#5c5540;padding:8px 0 18px 0;">
                Tell me what's slow at {{Company}} right now. I'll tell you plainly whether we're the right fit, no pitch deck, no pressure.
              </div>
              <a href="BOOKING_LINK" target="_blank" class="cta-btn" style="display:inline-block;background-color:#1c1a15;color:#ffffff;padding:13px 28px;border-radius:7px;font-weight:700;font-size:14.5px;text-decoration:none;mso-padding-alt:13px 28px;">
                Book a time with me &rarr;
              </a>
              <div style="font-size:12.5px;line-height:1.5;color:#8a8368;padding-top:14px;">
                Or just reply. Founder to founder, it comes straight to me, not a sales queue.
              </div>
            </td>
          </tr>
        </table>
      </td>
    </tr>

    <!-- Signature -->
    <tr>
      <td class="content-cell" style="padding:30px 36px 30px 36px;">
        <div style="border-top:1px solid #f0ebe0;padding-top:20px;">
          <div style="font-size:13px;color:#8a8368;">Talk soon,</div>
          <div style="font-size:16px;font-weight:700;color:#1c1a15;">Tirth Patel</div>
          <div style="font-size:13px;color:#5c5540;">Founder &amp; CEO, Nenotechnology (Aineno Innovation Pvt. Ltd.)</div>
          <div style="font-size:12px;color:#a08a5c;margin-top:3px;">TEDx Speaker &bull; 300,000+ Followers &bull; Co-founder, Gujarat AI Society &amp; Agentic Bharat</div>
          <div style="font-size:12px;margin-top:8px;">
            <a href="mailto:sales@nenotechnology.com" style="color:#a08a5c;text-decoration:none;">sales@nenotechnology.com</a> &nbsp;|&nbsp;
            <a href="tel:+917863852024" style="color:#a08a5c;text-decoration:none;">+91 7863852024</a> &nbsp;|&nbsp;
            <a href="https://www.nenotechnology.com" target="_blank" style="color:#a08a5c;text-decoration:none;">www.nenotechnology.com</a> &nbsp;|&nbsp;
            <a href="LINKEDIN_URL" target="_blank" style="color:#a08a5c;text-decoration:none;">LinkedIn</a>
          </div>
        </div>
      </td>
    </tr>

  </table>

  <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:600px;max-width:100%;margin-top:10px;">
    <tr>
      <td style="font-size:11px;line-height:1.5;color:#a39d89;text-align:center;padding:6px 12px;">
        Aineno Innovation Pvt. Ltd. &middot; Ahmedabad, Gujarat, India<br>
        Stay updated with our latest AI insights &amp; research &middot; <a href="SUBSCRIBE_LINK" style="color:#a39d89;text-decoration:underline;">Subscribe</a>
      </td>
    </tr>
  </table>

</td></tr>
</table>

</body>
</html>"""


def _build_mohit_signature_html(
    accent_color: str = "#0284C7",
    website_url: str = "https://www.nenotechnology.us/",
    phone_number: str = DEFAULT_MOHIT_PHONE,
) -> str:
    """Builds clean executive signature block for Mohit Patel (Neno Technology) with email, phone, and website."""
    return f"""<div style="margin-top:18px;padding-top:14px;border-top:1px solid #e2e8f0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
            <div style="font-size:13px;color:#64748b;margin-bottom:2px;">Warm regards,</div>
            <div style="font-size:15px;font-weight:700;color:#0f172a;line-height:1.3;">Mohit Patel</div>
            <div style="font-size:12.5px;color:#334155;margin-top:2px;">Neno Technology</div>
            <div class="sig-links" style="font-size:12px;margin-top:4px;">
              <a href="mailto:mohit@nenotechnology.us" style="color:{accent_color};text-decoration:none;font-weight:500;">mohit@nenotechnology.us</a> &nbsp;|&nbsp;
              <a href="tel:{phone_number}" style="color:{accent_color};text-decoration:none;">{phone_number}</a> &nbsp;|&nbsp;
              <a href="{website_url}" target="_blank" style="color:{accent_color};text-decoration:none;">{website_url}</a>
            </div>
            <div style="font-size:12px;color:#64748b;margin-top:3px;">3838 Andrew Johnson Hwy, Limestone, TN 37681</div>
          </div>"""


# ─────────────────────────────────────────────────────────────
# MOHIT OUTREACH TEMPLATES (TEMPLATES 9, 10, 11)
# Derived from Tirth Patel Templates 3, 4, 7 for Mohit (mohit@nenotechnology.us)
# ─────────────────────────────────────────────────────────────

RAW_TEMPLATE_9 = _build_responsive_template_html(
    title="Ship AI projects faster at {{Company}}, without the hiring wait",
    preheader="Senior AI and LLM engineers ready on bench to build your agentic workflows and custom features.",
    intro_html="I'm Mohit Patel from <strong>Neno Technology</strong>. We provide vetted AI &amp; LLM engineering squads who help tech teams build and ship production agentic workflows, RAG systems, and custom AI features in weeks.",
    callout_html="Have an AI feature, RAG pipeline, or custom agent backlog waiting to be built at {{Company}}? Let's spend 20 minutes reviewing the technical architecture and delivery timeline.",
    cta_text="Schedule an AI Architecture Call",
    section_heading="Engineering Capabilities on Demand",
    bullets_html="""<p style="margin:0 0 6px 0;"><strong style="color:#0f172a;">Autonomous Agentic Workflows.</strong> Multi-agent systems built with LangGraph, LlamaIndex, and custom tool integrations that execute complex multi-step reasoning autonomously.</p>
<p style="margin:0 0 6px 0;"><strong style="color:#0f172a;">Enterprise RAG &amp; Hybrid Search.</strong> Highly accurate knowledge retrieval pipelines with semantic re-ranking, token-cost optimization, and strict anti-hallucination guardrails.</p>
<p style="margin:0 0 6px 0;"><strong style="color:#0f172a;">Bench Ready Next Week.</strong> Senior Python, TypeScript, FastAPI, and Next.js engineers who connect to your GitHub repo and Jira on day one &mdash; no recruiting lag.</p>
<p style="margin:0;"><strong style="color:#0f172a;">Predictable Monthly Sprints.</strong> Fixed monthly pricing per engineer with transparent weekly deliverables and zero long-term vendor lock-in.</p>""",
    website_callout_html="""<div style="margin:18px 0 16px 0;padding:12px 18px;background-color:#f8fafc;border:1px solid #e2e8f0;border-left:3px solid #0284C7;border-radius:0 8px 8px 0;font-size:13.5px;line-height:1.5;color:#334155;">
            🌐 <strong>Explore our AI architectures:</strong> Please visit our website at <a href="https://www.nenotechnology.us/" target="_blank" style="color:#0284C7;font-weight:600;text-decoration:underline;">Neno Technology</a> to see our LangGraph multi-agent builds, enterprise RAG pipelines, and technical blueprints.
          </div>""",
    closing_html="Whether you need an end-to-end AI product built from scratch or an extra engineer to clear your backlog, our squad delivers fast, production-grade code.",
    accent_color="#0284C7",
    website_url="https://www.nenotechnology.us/",
    signature_html=_build_mohit_signature_html("#0284C7", "https://www.nenotechnology.us/"),
    footer_address_html="Neno Technology &middot; 3838 Andrew Johnson Hwy, Limestone, TN 37681",
)

RAW_TEMPLATE_10 = _build_responsive_template_html(
    title="Automating repetitive manual operations at {{Company}}",
    preheader="Stop spending 15-20 hours every week manually copying data between email, spreadsheets, and CRM tools.",
    intro_html="I'm Mohit Patel from <strong>Neno Technology</strong>. We build unified automation pipelines that eliminate 15 to 20 hours every week of manual data transfer between emails, spreadsheets, WhatsApp, and CRMs.",
    callout_html="Where is {{Company}} losing the most hours each week to repetitive copy-paste work? Let's take 20 minutes to pinpoint high-impact automation quick wins.",
    cta_text="Review Automation Opportunities",
    section_heading="What We Automate For Your Business",
    bullets_html="""<p style="margin:0 0 6px 0;"><strong style="color:#0f172a;">Cross-Platform Pipeline Sync.</strong> Connect your CRM, email inboxes, WhatsApp Business API, accounting platforms, and databases into zero-touch automated workflows.</p>
<p style="margin:0 0 6px 0;"><strong style="color:#0f172a;">Automated Document &amp; Invoice Parsing.</strong> Extract structured data from supplier invoices, client contracts, and receipts automatically with 99.8% precision.</p>
<p style="margin:0 0 6px 0;"><strong style="color:#0f172a;">Zero Manual Entry Errors.</strong> Replace fragile human data copying with automated schema validation, webhook alerts, and error failover logging.</p>
<p style="margin:0;"><strong style="color:#0f172a;">Fast 7-14 Day Turnaround.</strong> Most operational bottlenecks can be fully automated within 1 to 2 weeks without disrupting your day-to-day business.</p>""",
    website_callout_html="""<div style="margin:18px 0 16px 0;padding:12px 18px;background-color:#f8fafc;border:1px solid #e2e8f0;border-left:3px solid #059669;border-radius:0 8px 8px 0;font-size:13.5px;line-height:1.5;color:#334155;">
            🌐 <strong>Explore our automation workflows:</strong> Please visit our website at <a href="https://www.nenotechnology.us/" target="_blank" style="color:#059669;font-weight:600;text-decoration:underline;">Neno Technology</a> to review how we automate ERP, CRM, invoice parsing, and cross-platform business operations.
          </div>""",
    closing_html="We free your top talent from low-value repetitive tasks so they can spend their energy speaking to clients and driving revenue.",
    accent_color="#059669",
    website_url="https://www.nenotechnology.us/",
    signature_html=_build_mohit_signature_html("#059669", "https://www.nenotechnology.us/"),
    footer_address_html="Neno Technology &middot; 3838 Andrew Johnson Hwy, Limestone, TN 37681",
)

RAW_TEMPLATE_11 = _build_responsive_template_html(
    title="Cutting overhead at {{Company}} with AI - Strategic consultation",
    preheader="Strategic advisory on pinpointing high-ROI AI opportunities and scaling margins.",
    intro_html="I'm Mohit Patel from <strong>Neno Technology</strong>. We help business owners and leadership teams cut operational overhead and unlock new efficiency through purpose-built AI solutions &mdash; offering candid, practical advice on where AI creates real profit.",
    callout_html="No sales pitch, no slides. Would you be open to a 20-minute chat about the top 2 bottlenecks holding back {{Company}}'s margins?",
    cta_text="Book a Strategy Consultation",
    section_heading="What We Focus on During Our Call",
    bullets_html="""<p style="margin:0 0 6px 0;"><strong style="color:#0f172a;">Unvarnished Strategic Advice.</strong> Direct guidance from our senior AI &amp; engineering leadership on what AI can realistically solve today versus what is just marketing hype.</p>
<p style="margin:0 0 6px 0;"><strong style="color:#0f172a;">Tailored ROI Roadmap.</strong> Identify the specific 20% of repetitive workflows that will generate 80% of your operational savings.</p>
<p style="margin:0 0 6px 0;"><strong style="color:#0f172a;">Hands-On Implementation Squad.</strong> If there's a mutual fit, we provide the exact engineering team to execute the roadmap end-to-end.</p>
<p style="margin:0;"><strong style="color:#0f172a;">Strict Confidentiality &amp; Full IP Ownership.</strong> 100% of all intellectual property, custom models, code, and automations belong entirely to {{Company}}.</p>""",
    website_callout_html="""<div style="margin:18px 0 16px 0;padding:12px 18px;background-color:#f8fafc;border:1px solid #e2e8f0;border-left:3px solid #0D9488;border-radius:0 8px 8px 0;font-size:13.5px;line-height:1.5;color:#334155;">
            🌐 <strong>Learn more about Neno Technology:</strong> Please visit our website at <a href="https://www.nenotechnology.us/" target="_blank" style="color:#0D9488;font-weight:600;text-decoration:underline;">Neno Technology</a> to review our company story, AI advisory frameworks, and real-world client deployments.
          </div>""",
    closing_html="If you want a straight, honest perspective on AI for {{Company}}, let's connect.",
    accent_color="#0D9488",
    website_url="https://www.nenotechnology.us/",
    signature_html=_build_mohit_signature_html("#0D9488", "https://www.nenotechnology.us/"),
    footer_address_html="Neno Technology &middot; 3838 Andrew Johnson Hwy, Limestone, TN 37681",
)


# Built-in Core Template Catalog (8 Distinct Templates)
BUILTIN_TEMPLATES: List[Dict[str, Any]] = [
    {
        "id": "tpl_fde_velocity",
        "name": "Template 1: Forward Deployed AI Engineers",
        "subject": "Quick idea for {{Company}}",
        "category": "Executive & Engineering Velocity",
        "description": "Executive pitch emphasizing Forward Deployed Engineers moving 3-5x faster with agentic coding, pre-built bench, and zero payroll risk.",
        "html_content": RAW_TEMPLATE_1,
        "style": "executive",
        "accent_color": "#1A5CFF",
        "badge": "Top Recommended",
    },
    {
        "id": "tpl_voice_calling",
        "name": "Template 2: Autonomous AI Voice & Calling Agents",
        "subject": "Zero Missed Inbound Leads for {{Company}} - AI Calling Agents",
        "category": "Voice & Inbound Lead Capture",
        "description": "Specialized outreach highlighting autonomous 24/7 AI voice calling agents that qualify prospects in 60 seconds and sync with CRM.",
        "html_content": RAW_TEMPLATE_2,
        "style": "purple_modern",
        "accent_color": "#7C3AED",
        "badge": "Voice AI",
    },
    {
        "id": "tpl_agentic_workflows",
        "name": "Template 3: Custom Agentic Workflows & LLM Engineering",
        "subject": "Ship AI projects faster at {{Company}}, without the hiring wait",
        "category": "Technical Capabilities & LLMs",
        "description": "Pitch for tech companies and agencies needing senior Python/TypeScript squads to build custom LangGraph/RAG pipelines without recruitment lag.",
        "html_content": RAW_TEMPLATE_3,
        "style": "sky_technical",
        "accent_color": "#0284C7",
        "badge": "High Conversion",
    },
    {
        "id": "tpl_business_automation",
        "name": "Template 4: Business Process & ERP/CRM Automation",
        "subject": "Automating repetitive manual operations at {{Company}}",
        "category": "Operational Automation",
        "description": "Operational pitch aimed at businesses losing 15-20 hrs/week on manual copy-paste across emails, WhatsApp, Sheets, and CRMs.",
        "html_content": RAW_TEMPLATE_4,
        "style": "emerald_enterprise",
        "accent_color": "#059669",
        "badge": "Automation",
    },
    {
        "id": "tpl_dedicated_workbench",
        "name": "Template 5: Dedicated Offshore AI Tech Workbench",
        "subject": "Extending {{Company}}'s dev team with dedicated senior engineers",
        "category": "Team Augmentation",
        "description": "Dedicated offshore tech extension model in Ahmedabad, India with guaranteed Australian time-zone alignment and 60-70% lower overhead.",
        "html_content": RAW_TEMPLATE_5,
        "style": "amber_workbench",
        "accent_color": "#D97706",
        "badge": "High Engagement",
    },
    {
        "id": "tpl_internal_dashboards",
        "name": "Template 6: Legacy Modernization & Custom Internal Tools",
        "subject": "Modernizing legacy systems & internal portals for {{Company}}",
        "category": "Software Modernization",
        "description": "Modernization outreach replacing slow legacy tools and brittle spreadsheets with slick Next.js web applications and AI dashboards.",
        "html_content": RAW_TEMPLATE_6,
        "style": "indigo_modern",
        "accent_color": "#4F46E5",
        "badge": "Modernization",
    },
    {
        "id": "tpl_founder_strategy",
        "name": "Template 7: Founder-to-Founder AI Strategy Audit",
        "subject": "Founder-to-founder: Cutting overhead at {{Company}} with AI",
        "category": "Founder & Advisory",
        "description": "Candid founder-to-founder advisory consultation focusing on margin expansion, ROI roadmaps, and cutting operational fat.",
        "html_content": RAW_TEMPLATE_7,
        "style": "teal_executive",
        "accent_color": "#0D9488",
        "badge": "Executive Direct",
    },
    {
        "id": "tpl_founder_note",
        "name": "Template 8: A Founder-to-Founder Note",
        "subject": "A founder-to-founder note for {{Company}}",
        "category": "Founder & Advisory",
        "description": "Warm editorial founder-to-founder note focusing on senior AI engineer talent without recruiter friction, fixed runway costs, and Friday prototype speed.",
        "html_content": RAW_TEMPLATE_8,
        "style": "warm_editorial",
        "accent_color": "#A08A5C",
        "badge": "Warm Editorial",
        "logo_url": DEFAULT_LOGO_URL,
    },
    {
        "id": "tpl_mohit_agentic_workflows",
        "name": "Template 9: Custom Agentic Workflows & LLM Engineering (Mohit)",
        "subject": "Ship AI projects faster at {{Company}}, without the hiring wait",
        "category": "Mohit Outreach",
        "description": "On behalf of Mohit Patel (mohit@nenotechnology.us): Pitch for tech companies & agencies needing senior squads for LangGraph/RAG pipelines.",
        "html_content": RAW_TEMPLATE_9,
        "style": "sky_technical",
        "accent_color": "#0284C7",
        "badge": "Mohit Outreach",
        "sender_name": "Mohit Patel",
        "sender_email": "mohit@nenotechnology.us",
        "sender_phone": DEFAULT_MOHIT_PHONE,
        "portfolio_url": "https://www.nenotechnology.us/",
        "website_url": "https://www.nenotechnology.us/",
    },
    {
        "id": "tpl_mohit_business_automation",
        "name": "Template 10: Business Process & ERP/CRM Automation (Mohit)",
        "subject": "Automating repetitive manual operations at {{Company}}",
        "category": "Mohit Outreach",
        "description": "On behalf of Mohit Patel (mohit@nenotechnology.us): Operational pitch aimed at businesses losing 15-20 hrs/week on manual copy-paste.",
        "html_content": RAW_TEMPLATE_10,
        "style": "emerald_enterprise",
        "accent_color": "#059669",
        "badge": "Mohit Outreach",
        "sender_name": "Mohit Patel",
        "sender_email": "mohit@nenotechnology.us",
        "sender_phone": DEFAULT_MOHIT_PHONE,
        "portfolio_url": "https://www.nenotechnology.us/",
        "website_url": "https://www.nenotechnology.us/",
    },
    {
        "id": "tpl_mohit_strategic_advisory",
        "name": "Template 11: Strategic AI Advisory & Overhead Reduction (Mohit)",
        "subject": "Cutting overhead at {{Company}} with AI - Strategic consultation",
        "category": "Mohit Outreach",
        "description": "On behalf of Mohit Patel (mohit@nenotechnology.us): Advisory consultation focusing on margin expansion, ROI roadmaps, and cutting operational fat.",
        "html_content": RAW_TEMPLATE_11,
        "style": "teal_executive",
        "accent_color": "#0D9488",
        "badge": "Mohit Outreach",
        "sender_name": "Mohit Patel",
        "sender_email": "mohit@nenotechnology.us",
        "sender_phone": DEFAULT_MOHIT_PHONE,
        "portfolio_url": "https://www.nenotechnology.us/",
        "website_url": "https://www.nenotechnology.us/",
    },
]


def load_all_templates() -> List[Dict[str, Any]]:
    """Loads all templates: built-ins combined with any user-created or edited templates."""
    tpl_dict = {t["id"]: dict(t) for t in BUILTIN_TEMPLATES}
    if os.path.exists(TEMPLATES_JSON_PATH):
        try:
            with open(TEMPLATES_JSON_PATH, "r", encoding="utf-8") as f:
                custom_tpls = json.load(f)
                if isinstance(custom_tpls, list):
                    for c in custom_tpls:
                        if c.get("id"):
                            tpl_dict[c["id"]] = c
        except Exception:
            pass
    return list(tpl_dict.values())


def get_template_by_id(template_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a single template definition by its unique identifier."""
    for tpl in load_all_templates():
        if tpl.get("id") == template_id:
            return tpl
    return None


def save_custom_template(template_dict: Dict[str, Any]) -> bool:
    """Saves or updates a custom template in data/templates.json."""
    os.makedirs(TEMPLATES_DATA_DIR, exist_ok=True)
    custom_list = []
    if os.path.exists(TEMPLATES_JSON_PATH):
        try:
            with open(TEMPLATES_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    custom_list = data
        except Exception:
            custom_list = []

    # Update if exists, else append
    idx = next((i for i, item in enumerate(custom_list) if item.get("id") == template_dict.get("id")), -1)
    if idx >= 0:
        custom_list[idx] = template_dict
    else:
        custom_list.append(template_dict)

    try:
        with open(TEMPLATES_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(custom_list, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def delete_custom_template(template_id: str) -> bool:
    """Removes a template from data/templates.json.
    If it's an edited built-in template, removing it restores the original built-in code.
    If it's a user-created template, it deletes it entirely.
    """
    if not os.path.exists(TEMPLATES_JSON_PATH):
        return True
    try:
        with open(TEMPLATES_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            new_data = [t for t in data if t.get("id") != template_id]
            with open(TEMPLATES_JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(new_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def is_template_customized(template_id: str) -> bool:
    """Returns True if this template has custom overrides in data/templates.json."""
    if not os.path.exists(TEMPLATES_JSON_PATH):
        return False
    try:
        with open(TEMPLATES_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return any(t.get("id") == template_id for t in data)
    except Exception:
        pass
    return False



def interpolate_lead_placeholders(
    text: str,
    first_name: str,
    company_name: str,
    pain_text: str = "manual operational overhead",
) -> str:
    """Bulletproof interpolation for all casing and brace variations of lead placeholders:
    {FirstName}, {{FirstName}}, {name}, {{name}}, {company}, {{company}}, {pain}, etc.
    """
    if not text:
        return ""
    # Name / First Name variants
    text = re.sub(
        r'\{\{?\s*(?:first_?name|lead_?name|name|recipient_?name)\s*\}?\}',
        first_name,
        text,
        flags=re.IGNORECASE,
    )
    # Company variants
    text = re.sub(
        r'\{\{?\s*(?:company_?name|company|client|business)\s*\}?\}',
        company_name,
        text,
        flags=re.IGNORECASE,
    )
    # Pain point variants
    text = re.sub(
        r'\{\{?\s*(?:pain_?point|pain|challenge)\s*\}?\}',
        pain_text,
        text,
        flags=re.IGNORECASE,
    )
    return text


def render_template(
    template_or_id: Any,
    lead_name: Optional[Any] = None,
    company: Optional[str] = None,
    pain_point: Optional[str] = None,
    tracking_link: Optional[str] = None,
    booking_url: Optional[str] = None,
    logo_url: Optional[str] = None,
    linkedin_url: Optional[str] = None,
    portfolio_url: Optional[str] = None,
    twitter_url: Optional[str] = None,
    instagram_url: Optional[str] = None,
    facebook_url: Optional[str] = None,
    lead_data: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> Tuple[str, str]:
    """Interpolates lead data, tracking links, and assets into the requested template.
    Accepts either template ID string or template dictionary, and either individual fields or a lead_data dict.
    Returns (interpolated_subject, interpolated_html_body).
    """
    if isinstance(template_or_id, dict):
        tpl = template_or_id
    else:
        tpl = get_template_by_id(str(template_or_id))
        if not tpl:
            tpl = BUILTIN_TEMPLATES[0]

    # If lead_name argument is passed as a dict, treat as lead_data
    if isinstance(lead_name, dict):
        lead_data = lead_name
        lead_name = None

    if lead_data and isinstance(lead_data, dict):
        if not lead_name:
            lead_name = lead_data.get("name") or lead_data.get("first_name") or lead_data.get("full_name")
        if not company:
            company = lead_data.get("company") or lead_data.get("company_name")
        if not pain_point:
            pain_point = lead_data.get("pain_point") or lead_data.get("pain")
        if not tracking_link:
            tracking_link = lead_data.get("tracking_link")
        if not booking_url:
            booking_url = lead_data.get("booking_url")

    # Clean Name & Company
    c_name = str(lead_name).strip() if lead_name and str(lead_name).strip().lower() not in ("nan", "none", "") else ""
    first_name = c_name.split()[0].title() if c_name else "there"
    
    c_comp = str(company).strip() if company and str(company).strip().lower() not in ("nan", "none", "") else ""
    company_name = c_comp if c_comp else "your team"

    pain_text = str(pain_point).strip() if pain_point and str(pain_point).strip().lower() not in ("nan", "none", "") else "manual operational overhead"

    b_link = (booking_url or tracking_link or DEFAULT_BOOKING_URL).strip()
    l_url = (logo_url or tpl.get("logo_url") or DEFAULT_LOGO_URL).strip()
    li_url = (linkedin_url or tpl.get("linkedin_url") or DEFAULT_LINKEDIN_URL).strip()
    sender_mail = tpl.get("sender_email") or "sales@nenotechnology.com"
    is_mohit = "mohit" in str(tpl.get("id", "")).lower() or "mohit" in sender_mail.lower()
    default_port = DEFAULT_MOHIT_PORTFOLIO_URL if is_mohit else DEFAULT_PORTFOLIO_URL
    port_url = (portfolio_url or tpl.get("portfolio_url") or default_port).strip()
    tw_url = (twitter_url or tpl.get("twitter_url") or DEFAULT_TWITTER_URL).strip()
    ig_url = (instagram_url or tpl.get("instagram_url") or DEFAULT_INSTAGRAM_URL).strip()
    fb_url = (facebook_url or tpl.get("facebook_url") or DEFAULT_FACEBOOK_URL).strip()

    sender_mail = tpl.get("sender_email") or "sales@nenotechnology.com"
    sub_link = f"mailto:{sender_mail}?subject=Subscribe%20to%20AI%20Updates%20-%20{company_name}"

    # Subject Interpolation
    raw_subj = tpl.get("subject", "Quick idea for {{Company}}")
    subj_company = company_name if company_name != "your team" else "Your Business"
    subj = interpolate_lead_placeholders(raw_subj, first_name=first_name, company_name=subj_company, pain_text=pain_text)

    # Body Interpolation
    raw_html = tpl.get("html_content", "")
    html = interpolate_lead_placeholders(raw_html, first_name=first_name, company_name=company_name, pain_text=pain_text)
    html = html.replace("LOGO_URL", l_url)
    html = html.replace("BOOKING_LINK", b_link)
    html = html.replace("LINKEDIN_URL", li_url)
    html = html.replace("PORTFOLIO_URL", port_url)
    html = html.replace("TWITTER_URL", tw_url)
    html = html.replace("INSTAGRAM_URL", ig_url)
    html = html.replace("FACEBOOK_URL", fb_url)
    html = html.replace("SUBSCRIBE_LINK", sub_link)
    html = html.replace("UNSUBSCRIBE_LINK", sub_link)

    return subj, html


# ─────────────────────────────────────────────────────────────
# TEMPLATE-WISE ANALYTICS & DAILY TREND COMPUTATION
# ─────────────────────────────────────────────────────────────

def compute_template_analytics(df: pd.DataFrame) -> Dict[str, Any]:
    """Calculates granular performance metrics and day-by-day trends
    for each template across opens, clicks, replies, and consultation bookings.
    """
    templates = load_all_templates()
    tpl_lookup = {t["id"]: t for t in templates}

    if df.empty:
        return {
            "template_stats": [],
            "daily_trends": pd.DataFrame(),
            "best_open_rate": None,
            "best_click_rate": None,
            "best_booking_rate": None,
            "total_templates_active": 0,
        }

    df_copy = df[~df["status"].astype(str).str.lower().isin(["rejected", "cancelled", "failed"])].copy()

    # Normalize template_id
    if "template_id" not in df_copy.columns:
        df_copy["template_id"] = None
    if "template_name" not in df_copy.columns:
        df_copy["template_name"] = None

    # Fallback to map option / pattern if template_id is missing
    def _infer_template(row):
        tid = row.get("template_id")
        if pd.notna(tid) and str(tid).strip() and str(tid).strip().lower() != "nan":
            # Map legacy IDs to new canonical IDs if needed
            t_str = str(tid).strip().lower()
            legacy_map = {
                "template_1": "tpl_fde_velocity",
                "template 1": "tpl_fde_velocity",
                "template-1": "tpl_fde_velocity",
                "tpl_1": "tpl_fde_velocity",
                "tpl_exec_navy": "tpl_fde_velocity",
                "tpl_standard_fde": "tpl_fde_velocity",
                "template_2": "tpl_voice_calling",
                "template 2": "tpl_voice_calling",
                "tpl_2": "tpl_voice_calling",
                "tpl_calling_agents": "tpl_voice_calling",
                "template_3": "tpl_agentic_workflows",
                "template 3": "tpl_agentic_workflows",
                "tpl_3": "tpl_agentic_workflows",
                "tpl_blue_gradient": "tpl_agentic_workflows",
                "template_4": "tpl_business_automation",
                "template 4": "tpl_business_automation",
                "tpl_4": "tpl_business_automation",
                "tpl_workflow_automation": "tpl_business_automation",
                "template_5": "tpl_dedicated_workbench",
                "template 5": "tpl_dedicated_workbench",
                "tpl_5": "tpl_dedicated_workbench",
                "template_6": "tpl_internal_dashboards",
                "template 6": "tpl_internal_dashboards",
                "tpl_6": "tpl_internal_dashboards",
                "tpl_teal_grid": "tpl_internal_dashboards",
                "template_7": "tpl_founder_strategy",
                "template 7": "tpl_founder_strategy",
                "tpl_7": "tpl_founder_strategy",
                "tpl_editorial_letter": "tpl_founder_strategy",
                "template_8": "tpl_founder_note",
                "template 8": "tpl_founder_note",
                "tpl_8": "tpl_founder_note",
                "template_9": "tpl_mohit_agentic_workflows",
                "template 9": "tpl_mohit_agentic_workflows",
                "tpl_9": "tpl_mohit_agentic_workflows",
                "template_10": "tpl_mohit_business_automation",
                "template 10": "tpl_mohit_business_automation",
                "tpl_10": "tpl_mohit_business_automation",
                "template_11": "tpl_mohit_strategic_advisory",
                "template 11": "tpl_mohit_strategic_advisory",
                "tpl_11": "tpl_mohit_strategic_advisory",
            }
            if t_str in legacy_map:
                return legacy_map[t_str]
            if str(tid).strip() in tpl_lookup:
                return str(tid).strip()

        # Infer from template_id if it's Mohit
        t_id_str = str(tid or "").lower()
        if "mohit" in t_id_str or "tpl_mohit" in t_id_str:
            if "agentic" in t_id_str or "9" in t_id_str:
                return "tpl_mohit_agentic_workflows"
            elif "automation" in t_id_str or "10" in t_id_str:
                return "tpl_mohit_business_automation"
            elif "advisory" in t_id_str or "overhead" in t_id_str or "strategic" in t_id_str or "11" in t_id_str:
                return "tpl_mohit_strategic_advisory"

        # Infer from subject
        subj = str(row.get("subject") or "").lower()
        row_body = str(row.get("body") or "").lower()
        is_mohit = "mohit" in subj or "mohit" in row_body or "mohit@nenotechnology.us" in row_body

        if is_mohit:
            if "agentic" in subj or "hiring wait" in subj or "llm" in subj:
                return "tpl_mohit_agentic_workflows"
            elif "automating" in subj or "operations" in subj or "erp" in subj or "repetitive" in subj:
                return "tpl_mohit_business_automation"
            elif "overhead" in subj or "strategic" in subj or "consultation" in subj:
                return "tpl_mohit_strategic_advisory"

        if "quick idea" in subj or "velocity" in subj or "forward deployed" in subj or "transformation" in subj or "engineering partnership" in subj:
            return "tpl_fde_velocity"
        elif "voice" in subj or "calling" in subj or "inbound" in subj:
            return "tpl_voice_calling"
        elif "agentic" in subj or "hiring wait" in subj or "llm" in subj:
            return "tpl_agentic_workflows"
        elif "automating" in subj or "erp" in subj or "repetitive" in subj or "operations" in subj:
            return "tpl_business_automation"
        elif "workbench" in subj or "offshore" in subj or "extending" in subj:
            return "tpl_dedicated_workbench"
        elif "modernizing" in subj or "internal" in subj or "portal" in subj or "legacy" in subj:
            return "tpl_internal_dashboards"
        elif "note" in subj or "manage recruiters" in subj or "founder-to-founder note" in subj:
            return "tpl_founder_note"
        elif "founder" in subj or "strategy" in subj or "margin" in subj:
            return "tpl_founder_strategy"
        return "tpl_fde_velocity"

    df_copy["resolved_template_id"] = df_copy.apply(_infer_template, axis=1)

    template_stats = []
    daily_records = []

    # Calculate metrics for each template
    for tpl in templates:
        tid = tpl["id"]
        tname = tpl["name"]
        color = tpl.get("accent_color", "#2563EB")
        
        t_df = df_copy[df_copy["resolved_template_id"] == tid]
        total_leads = t_df["email"].astype(str).str.strip().str.lower().nunique() if not t_df.empty else 0
        sent_df = t_df[t_df["status"].isin(["sent", "meeting_scheduled"])]
        total_sent = sent_df["email"].astype(str).str.strip().str.lower().nunique() if not sent_df.empty else 0
        
        opened_count = int(t_df["opened"].sum()) if "opened" in t_df.columns else 0
        clicked_count = int(t_df["clicked_link"].sum()) if "clicked_link" in t_df.columns else 0
        replied_count = int(t_df["reply_received_at"].notna().sum()) if "reply_received_at" in t_df.columns else 0
        booked_count = int(t_df["booking_status"].isin(["scheduled", "meeting_scheduled", "confirmation_sent", "confirmed"]).sum()) if "booking_status" in t_df.columns else 0

        open_rate = round((opened_count / total_sent * 100), 1) if total_sent > 0 else 0.0
        click_rate = round((clicked_count / total_sent * 100), 1) if total_sent > 0 else 0.0
        reply_rate = round((replied_count / total_sent * 100), 1) if total_sent > 0 else 0.0
        booking_rate = round((booked_count / total_sent * 100), 1) if total_sent > 0 else 0.0

        stat_item = {
            "template_id": tid,
            "id": tid,
            "template_name": tname,
            "name": tname,
            "category": tpl.get("category", "General"),
            "badge": tpl.get("badge", ""),
            "accent_color": color,
            "total_leads": total_leads,
            "total_sent": total_sent,
            "opened_count": opened_count,
            "clicked_count": clicked_count,
            "replied_count": replied_count,
            "booked_count": booked_count,
            "open_rate": open_rate,
            "click_rate": click_rate,
            "reply_rate": reply_rate,
            "booking_rate": booking_rate,
        }
        template_stats.append(stat_item)

        # Day-by-Day Progression
        if not t_df.empty and "created_at" in t_df.columns:
            # Group by day
            t_df_dated = t_df.copy()
            # Use email_sent_at or created_at
            t_df_dated["date_dt"] = pd.to_datetime(t_df_dated["email_sent_at"].fillna(t_df_dated["created_at"]), errors="coerce")
            t_df_dated = t_df_dated[t_df_dated["date_dt"].notna()]
            if not t_df_dated.empty:
                t_df_dated["date_str"] = t_df_dated["date_dt"].dt.strftime("%Y-%m-%d")
                for d_str, g in t_df_dated.groupby("date_str"):
                    g_sent = len(g[g["status"].isin(["sent", "meeting_scheduled"])])
                    g_open = int(g["opened"].sum()) if "opened" in g.columns else 0
                    g_click = int(g["clicked_link"].sum()) if "clicked_link" in g.columns else 0
                    g_book = int(g["booking_status"].isin(["scheduled", "meeting_scheduled", "confirmation_sent", "confirmed"]).sum()) if "booking_status" in g.columns else 0

                    daily_records.append({
                        "date": d_str,
                        "template_id": tid,
                        "template_name": tname,
                        "sent": g_sent,
                        "opens": g_open,
                        "clicks": g_click,
                        "bookings": g_book,
                        "open_rate": round(g_open / g_sent * 100, 1) if g_sent else 0.0,
                        "click_rate": round(g_click / g_sent * 100, 1) if g_sent else 0.0,
                        "booking_rate": round(g_book / g_sent * 100, 1) if g_sent else 0.0,
                    })

    daily_df = pd.DataFrame(daily_records)
    if not daily_df.empty:
        daily_df = daily_df.sort_values(by="date")

    # Winner identifications (min 1 sent to qualify)
    qual_sent = [s for s in template_stats if s["total_sent"] > 0]
    best_open = max(qual_sent, key=lambda x: x["open_rate"]) if qual_sent else None
    best_click = max(qual_sent, key=lambda x: x["click_rate"]) if qual_sent else None
    best_booking = max(qual_sent, key=lambda x: x["booking_rate"]) if qual_sent else None

    return {
        "template_stats": template_stats,
        "daily_trends": daily_df,
        "best_open_rate": best_open,
        "best_click_rate": best_click,
        "best_booking_rate": best_booking,
        "total_templates_active": len([s for s in template_stats if s["total_leads"] > 0]),
    }
