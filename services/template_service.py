import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

TEMPLATES_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
TEMPLATES_JSON_PATH = os.path.join(TEMPLATES_DATA_DIR, "templates.json")

DEFAULT_LOGO_URL = "https://res.cloudinary.com/dqreqsjas/image/upload/v1789542387/logo-dark.png"
DEFAULT_LINKEDIN_URL = "https://www.linkedin.com/in/tirthpatel-ai/"
DEFAULT_BOOKING_URL = os.getenv(
    "BOOKING_FORM_URL",
    "https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled",
)

# ─────────────────────────────────────────────────────────────
# 4 USER-PROVIDED HIGH-CONVERTING HTML TEMPLATES
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
) -> str:
    """Generates a pixel-perfect, fully responsive HTML email template
    matching the user's executive design with Cloudinary CDN logo,
    callout question box, bullets, and complete Tirth Patel signature.
    """
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>{title}</title>
<style>
  body {{
    margin: 0;
    padding: 0;
    background-color: #f1f5f9;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
  }}
  table {{
    border-collapse: collapse;
  }}
  @media only screen and (max-width: 620px) {{
    .outer-table {{ padding: 12px 6px !important; }}
    .email-container {{ width: 100% !important; border-radius: 8px !important; }}
    .content-cell {{ padding: 22px 18px !important; }}
    .cta-btn {{ display: block !important; width: 100% !important; text-align: center !important; box-sizing: border-box !important; }}
  }}
</style>
</head>
<body style="margin:0;padding:0;background-color:#f1f5f9;">

<div style="display:none;max-height:0;overflow:hidden;opacity:0;font-size:1px;line-height:1px;color:#f1f5f9;">
  {preheader}
</div>

<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="outer-table" style="background-color:#f1f5f9;padding:28px 12px;">
<tr>
  <td align="center">
    <!-- Main Card Container -->
    <table role="presentation" width="620" cellpadding="0" cellspacing="0" border="0" class="email-container" style="width:620px;max-width:100%;background-color:#ffffff;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;box-shadow:0 4px 6px -1px rgba(0,0,0,0.05);">
      <tr>
        <td class="content-cell" style="padding:32px 36px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;font-size:15px;line-height:1.6;color:#1e293b;text-align:left;">
          
          <!-- Logo -->
          <div style="margin-bottom:24px;">
            <img src="LOGO_URL" alt="Neno Technology" style="height:38px;max-height:42px;max-width:180px;display:block;border:0;outline:none;" />
          </div>

          <!-- Greeting & Intro -->
          <p style="margin:0 0 14px 0;font-size:15px;line-height:1.6;color:#1e293b;">Dear {{FirstName}},</p>
          <p style="margin:0 0 14px 0;font-size:15px;line-height:1.6;color:#1e293b;">I hope you and the team at {{Company}} are doing well.</p>
          <p style="margin:0 0 18px 0;font-size:15px;line-height:1.6;color:#1e293b;">
            {intro_html}
          </p>

          <!-- Callout Question Box -->
          <div style="border-left:3px solid {accent_color};background-color:#f8fafc;padding:14px 18px;margin:20px 0;border-radius:0 8px 8px 0;font-size:14.5px;line-height:1.55;color:#0f172a;font-weight:500;">
            {callout_html}
          </div>

          <!-- CTA Button -->
          <div style="margin:22px 0 26px 0;">
            <a href="BOOKING_LINK" target="_blank" class="cta-btn" style="display:inline-block;background-color:{accent_color};color:#ffffff;padding:12px 24px;border-radius:6px;font-weight:600;font-size:14.5px;text-decoration:none;letter-spacing:0.01em;">
              {cta_text}
            </a>
          </div>

          <!-- Section Heading -->
          <div style="font-size:16px;font-weight:700;color:#0f172a;margin:24px 0 14px 0;line-height:1.3;">
            {section_heading}
          </div>

          <!-- Bullets -->
          <div style="font-size:14.5px;line-height:1.65;color:#334155;">
            {bullets_html}
          </div>

          <!-- Closing pitch -->
          <p style="margin:20px 0 12px 0;font-size:14.5px;line-height:1.6;color:#1e293b;">
            {closing_html}
          </p>
          <p style="margin:0 0 24px 0;font-size:13px;line-height:1.5;color:#64748b;">
            Or simply reply to this email - it comes straight to me.
          </p>

          <!-- Warm Regards / Signature (Exact screenshot match) -->
          <div style="margin-top:26px;padding-top:20px;border-top:1px solid #e2e8f0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
            <div style="font-size:14px;color:#475569;margin-bottom:3px;">Warm regards,</div>
            <div style="font-size:16.5px;font-weight:700;color:#0f172a;line-height:1.3;">Tirth Patel</div>
            <div style="font-size:13px;color:#334155;margin-top:2px;">Founder &amp; CEO, Nenotechnology (Aineno Innovation Pvt. Ltd.)</div>
            <div style="font-size:12px;color:#64748b;margin-top:3px;">TEDx Speaker &bull; 300,000+ Followers &bull; Co-founder, Gujarat AI Society &amp; Agentic Bharat</div>
            <div style="font-size:12px;color:#64748b;margin-top:2px;">Ahmedabad, Gujarat, India</div>
            <div style="font-size:12px;color:#2563eb;margin-top:6px;">
              <a href="mailto:support@nenotechnology.com" style="color:#2563eb;text-decoration:none;">support@nenotechnology.com</a> &nbsp;|&nbsp;
              <a href="tel:+917863852024" style="color:#2563eb;text-decoration:none;">+91 7863852024</a> &nbsp;|&nbsp;
              <a href="https://www.nenotechnology.com" target="_blank" style="color:#2563eb;text-decoration:none;">www.nenotechnology.com</a> &nbsp;|&nbsp;
              <a href="LINKEDIN_URL" target="_blank" style="color:#2563eb;text-decoration:none;">LinkedIn</a>
            </div>
          </div>

        </td>
      </tr>
    </table>

    <!-- Footer / Unsubscribe -->
    <table role="presentation" width="620" cellpadding="0" cellspacing="0" border="0" style="width:620px;max-width:100%;margin-top:14px;">
      <tr>
        <td style="font-size:11.5px;line-height:1.5;color:#94a3b8;text-align:center;padding:8px 12px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
          Aineno Innovation Pvt. Ltd. &middot; Ahmedabad, Gujarat, India<br>
          Prefer not to hear from us? <a href="UNSUBSCRIBE_LINK" style="color:#94a3b8;text-decoration:underline;">Unsubscribe</a>
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
    bullets_html="""<p style="margin:0 0 10px 0;"><strong style="color:#0f172a;">Forward Deployed Engineers.</strong> One person who takes a requirement through build and deployment &mdash; using AI coding tools and agentic workflows to move at several times normal speed.</p>
<p style="margin:0 0 10px 0;"><strong style="color:#0f172a;">AI and full-stack developers.</strong> AI agent developers, backend, full-stack and deployment engineers &mdash; already on our bench, not being recruited after you sign.</p>
<p style="margin:0 0 10px 0;"><strong style="color:#0f172a;">Vetted before you meet them.</strong> Every engineer clears our five-stage screening. You interview the shortlist and pick who joins you.</p>
<p style="margin:0;"><strong style="color:#0f172a;">A fraction of local contract rates.</strong> Fixed monthly cost per developer. No payroll, no super, no desk, no notice period risk.</p>""",
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
    bullets_html="""<p style="margin:0 0 10px 0;"><strong style="color:#0f172a;">Sub-Second Voice Latency.</strong> Natural, human-like voice agents that navigate multi-turn conversations, answer service questions, and overcome objections flawlessly.</p>
<p style="margin:0 0 10px 0;"><strong style="color:#0f172a;">24/7 Lead Capture.</strong> Never lose after-hours, holiday, or weekend leads again. Every call is answered, qualified, and scheduled on your calendar instantly.</p>
<p style="margin:0 0 10px 0;"><strong style="color:#0f172a;">Instant CRM &amp; Calendar Sync.</strong> Real-time call transcription, structured notes, and confirmed bookings pushed automatically to HubSpot, Salesforce, or Google Calendar.</p>
<p style="margin:0;"><strong style="color:#0f172a;">Unlimited Concurrent Capacity.</strong> Handle 100 simultaneous calls during marketing spikes without hiring extra call center staff or paying per-minute agency fees.</p>""",
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
    bullets_html="""<p style="margin:0 0 10px 0;"><strong style="color:#0f172a;">Autonomous Agentic Workflows.</strong> Multi-agent systems built with LangGraph, LlamaIndex, and custom tool integrations that execute complex multi-step reasoning autonomously.</p>
<p style="margin:0 0 10px 0;"><strong style="color:#0f172a;">Enterprise RAG &amp; Hybrid Search.</strong> Highly accurate knowledge retrieval pipelines with semantic re-ranking, token-cost optimization, and strict anti-hallucination guardrails.</p>
<p style="margin:0 0 10px 0;"><strong style="color:#0f172a;">Bench Ready Next Week.</strong> Senior Python, TypeScript, FastAPI, and Next.js engineers who connect to your GitHub repo and Jira on day one &mdash; no recruiting lag.</p>
<p style="margin:0;"><strong style="color:#0f172a;">Predictable Monthly Sprints.</strong> Fixed monthly pricing per engineer with transparent weekly deliverables and zero long-term vendor lock-in.</p>""",
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
    bullets_html="""<p style="margin:0 0 10px 0;"><strong style="color:#0f172a;">Cross-Platform Pipeline Sync.</strong> Connect your CRM, email inboxes, WhatsApp Business API, accounting platforms, and databases into zero-touch automated workflows.</p>
<p style="margin:0 0 10px 0;"><strong style="color:#0f172a;">Automated Document &amp; Invoice Parsing.</strong> Extract structured data from supplier invoices, client contracts, and receipts automatically with 99.8% precision.</p>
<p style="margin:0 0 10px 0;"><strong style="color:#0f172a;">Zero Manual Entry Errors.</strong> Replace fragile human data copying with automated schema validation, webhook alerts, and error failover logging.</p>
<p style="margin:0;"><strong style="color:#0f172a;">Fast 7-14 Day Turnaround.</strong> Most operational bottlenecks can be fully automated within 1 to 2 weeks without disrupting your day-to-day business.</p>""",
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
    bullets_html="""<p style="margin:0 0 10px 0;"><strong style="color:#0f172a;">Direct Team Integration.</strong> Engineers work exclusively for {{Company}}, attend your daily standups, communicate in your Slack, and follow your coding standards.</p>
<p style="margin:0 0 10px 0;"><strong style="color:#0f172a;">Top 1% Indian Tech Talent.</strong> Every engineer clears our rigorous 5-stage technical screening, live system architecture rounds, and fluent English communication tests.</p>
<p style="margin:0 0 10px 0;"><strong style="color:#0f172a;">Guaranteed Time-Zone Alignment.</strong> Daily working hours synchronized with Australian Eastern Standard Time (AEST) and Western time zones for real-time collaboration.</p>
<p style="margin:0;"><strong style="color:#0f172a;">Zero Office or HR Overhead.</strong> We take care of state-of-the-art office facilities, high-speed fiber, compliance, laptops, and payroll &mdash; you simply assign tasks.</p>""",
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
    bullets_html="""<p style="margin:0 0 10px 0;"><strong style="color:#0f172a;">Modern High-Performance Stack.</strong> Fast Next.js, React, Node, Python, and cloud-native serverless backends replacing slow legacy systems.</p>
<p style="margin:0 0 10px 0;"><strong style="color:#0f172a;">AI-Assisted Dashboards.</strong> Real-time operational dashboards with natural-language AI query assistants so any team member can ask questions about company data.</p>
<p style="margin:0 0 10px 0;"><strong style="color:#0f172a;">Fast Prototype to Production.</strong> Interactive clickable prototypes delivered within 5 days, production deployment within 3-4 weeks.</p>
<p style="margin:0;"><strong style="color:#0f172a;">Transparent Fixed Milestones.</strong> Clear milestone deliverables with no surprise hourly charges or scope creep.</p>""",
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
    bullets_html="""<p style="margin:0 0 10px 0;"><strong style="color:#0f172a;">Unvarnished Strategic Advice.</strong> Direct guidance from Tirth Patel on what AI can realistically solve today versus what is just marketing hype.</p>
<p style="margin:0 0 10px 0;"><strong style="color:#0f172a;">Tailored ROI Roadmap.</strong> Identify the specific 20% of repetitive workflows that will generate 80% of your operational savings.</p>
<p style="margin:0 0 10px 0;"><strong style="color:#0f172a;">Hands-On Implementation Squad.</strong> If there's a mutual fit, we provide the exact engineering team to execute the roadmap end-to-end.</p>
<p style="margin:0;"><strong style="color:#0f172a;">Strict Confidentiality &amp; Full IP Ownership.</strong> 100% of all intellectual property, custom models, code, and automations belong entirely to {{Company}}.</p>""",
    closing_html="I only take 3 advisory calls a week to ensure high impact. If you want a straight, honest perspective on AI for {{Company}}, let's connect.",
    accent_color="#DC2626",
)


# Built-in Core Template Catalog (7 Distinct Templates)
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
        "style": "crimson_direct",
        "accent_color": "#DC2626",
        "badge": "Executive Direct",
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
    l_url = (logo_url or DEFAULT_LOGO_URL).strip()
    li_url = (linkedin_url or DEFAULT_LINKEDIN_URL).strip()
    unsub_link = f"mailto:support@nenotechnology.com?subject=Unsubscribe%20{company_name}"

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
    html = html.replace("UNSUBSCRIBE_LINK", unsub_link)

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

    df_copy = df.copy()

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
            t_str = str(tid).strip()
            legacy_map = {
                "tpl_exec_navy": "tpl_fde_velocity",
                "tpl_calling_agents": "tpl_voice_calling",
                "tpl_blue_gradient": "tpl_agentic_workflows",
                "tpl_workflow_automation": "tpl_business_automation",
                "tpl_standard_fde": "tpl_fde_velocity",
                "tpl_teal_grid": "tpl_internal_dashboards",
                "tpl_editorial_letter": "tpl_founder_strategy",
            }
            return legacy_map.get(t_str, t_str)
        # Infer from subject
        subj = str(row.get("subject") or "").lower()
        if "quick idea" in subj or "velocity" in subj or "forward deployed" in subj:
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
        total_leads = len(t_df)
        sent_mask = (
            t_df["email_sent_at"].notna()
            | t_df["status"].isin([
                "sent", "meeting_scheduled", "replied", "opted_out", "delivered",
                "scheduled", "meeting_booked", "booked", "form_submitted", "opened", "clicked"
            ])
        )
        total_sent = int(sent_mask.sum())
        
        opened_count = int(t_df["opened"].sum()) if "opened" in t_df.columns else 0
        clicked_count = int(t_df["clicked_link"].sum()) if "clicked_link" in t_df.columns else 0
        
        replied_count = 0
        if "reply_received_at" in t_df.columns:
            replied_count = int(t_df["reply_received_at"].notna().sum())
        if "status" in t_df.columns:
            replied_count = max(replied_count, int((t_df["status"] == "replied").sum()))
        if "reply_body" in t_df.columns:
            has_body = (
                t_df["reply_body"].notna()
                & (~t_df["reply_body"].astype(str).str.strip().str.lower().isin(["", "none", "-", "—"]))
            )
            replied_count = max(replied_count, int(has_body.sum()))

        booked_count = 0
        if "booking_status" in t_df.columns:
            booked_count = int(t_df["booking_status"].isin(["scheduled", "meeting_scheduled", "confirmation_sent", "confirmed"]).sum())
        if "status" in t_df.columns:
            booked_count = max(booked_count, int(t_df["status"].isin(["scheduled", "meeting_scheduled", "meeting_booked", "booked"]).sum()))

        if total_sent == 0 and (opened_count > 0 or clicked_count > 0 or replied_count > 0 or booked_count > 0):
            total_sent = max(total_leads, opened_count, clicked_count, replied_count, booked_count)

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
            "sent": total_sent,
            "opened": opened_count,
            "opened_count": opened_count,
            "clicked": clicked_count,
            "clicked_count": clicked_count,
            "replied": replied_count,
            "replied_count": replied_count,
            "booked": booked_count,
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
