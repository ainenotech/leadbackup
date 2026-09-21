import os
import re
from typing import Optional
from langchain_core.messages import HumanMessage, SystemMessage

from Agent.llm import get_llm

DEFAULT_SYSTEM_PROMPT = """You are drafting warm, high-converting, professional B2B re-engagement emails on behalf of:
Sender: Tirth Patel, Founder & CEO
Company: Nenotechnology (Aineno Innovation Pvt. Ltd.), Ahmedabad, Gujarat (www.nenotechnology.com)

Company Capabilities & Services:
- Custom AI solutions tailored to specific business workflows
- Autonomous AI calling agents for customer support and sales outreach
- AI-powered CRM and ERP systems for streamlined operations
- Business process automation to reduce manual workload
- Email and WhatsApp automation for faster customer engagement

Rules:
1. STRICTLY NO PLACEHOLDERS: NEVER include square brackets or template placeholders like "[Customer Name]", "[Your Name]", "[mention their past interest...]", "[Insert Company]", etc.
2. Greeting: Address the lead by their real name (e.g., "Dear Alex," or "Hi Alex,"). If no name is provided, use "Hi there,". Never write "[Name]".
3. Tone: Warm, executive, professional, and no-pressure.
4. Content:
   - Mention it has been a while since connecting and reconnecting to share Nenotechnology's expanded AI/automation capabilities.
   - Reference their company name if provided.
   - If past interest is provided, reference it naturally. If NOT provided, seamlessly highlight how our AI & automation solutions reduce operational overhead and improve efficiency.
5. Call to Action: Invite them to schedule a short consultation call or reply directly to the email. (Note: A dedicated booking link will be inserted automatically, do NOT invent or write fake URLs).
6. Sign-off:
   Warm regards,
   Tirth Patel
   Founder & CEO,
   Nenotechnology (Aineno Innovation Pvt. Ltd.)
   Ahmedabad, Gujarat
   sales@nenotechnology.com | +91 7863852024
   www.nenotechnology.com

Output format must strictly begin with line 1 as "SUBJECT: <subject line>", followed by the email body.
"""


def compose_email(
    name: Optional[str],
    company: Optional[str],
    last_activity_date: Optional[str] = None,
    last_deal_stage: Optional[str] = None,
    previous_interest: Optional[str] = None,
    custom_instructions: Optional[str] = None,
    tracking_link: Optional[str] = None,
) -> tuple[str, str]:
    """Generates a personalized (subject, body) outreach email tailored to lead details.
    The email CTA links to the consultation booking form.
    """
    llm = get_llm()

    lead_name = name.strip() if name and name.strip().lower() not in ("nan", "none", "") else None
    company_name = company.strip() if company and company.strip().lower() not in ("nan", "none", "") else None

    context_lines = []
    if lead_name:
        context_lines.append(f"Lead Name: {lead_name}")
    if company_name:
        context_lines.append(f"Lead Company: {company_name}")
    if last_activity_date and str(last_activity_date).strip().lower() not in ("nan", "none", ""):
        context_lines.append(f"Last Interaction Date: {last_activity_date}")
    if last_deal_stage and str(last_deal_stage).strip().lower() not in ("nan", "none", ""):
        context_lines.append(f"Last Deal Stage: {last_deal_stage}")
    if previous_interest and str(previous_interest).strip().lower() not in ("nan", "none", ""):
        context_lines.append(f"Previous Interest: {previous_interest}")
    if custom_instructions:
        context_lines.append(f"Custom Messaging Angle: {custom_instructions}")

    user_prompt = (
        ("\n".join(context_lines) + "\n\n" if context_lines else "")
        + "Draft the re-engagement email now adhering strictly to the system instructions. Do not include any square bracket placeholders."
    )

    response = llm.invoke(
        [SystemMessage(content=DEFAULT_SYSTEM_PROMPT), HumanMessage(content=user_prompt)]
    )

    content = response.content
    if isinstance(content, str):
        text = content.strip()
    else:
        text_parts = []
        for block in content:
            if isinstance(block, dict):
                block_text = block.get("text")
            else:
                block_text = getattr(block, "text", None)
            if block_text:
                text_parts.append(block_text)
        text = "\n".join(text_parts).strip()

    if not text:
        raise ValueError("The AI composer returned an empty response")

    lines = text.split("\n", 1)

    if lines[0].upper().startswith("SUBJECT:"):
        subject = lines[0].split(":", 1)[1].strip()
        body = lines[1].strip() if len(lines) > 1 else ""
    else:
        company_info = f" — {company_name}" if company_name else ""
        subject = f"Let's Reconnect — New AI & IT Solutions at Nenotechnology{company_info}"
        body = text

    # Cleanup any inadvertent bracket placeholders LLM might still produce
    if lead_name:
        body = re.sub(r"\[(?:Customer\s+Name|Lead\s+Name|Name|Client\s+Name)\]", lead_name.title(), body, flags=re.IGNORECASE)
    else:
        body = re.sub(r"\[(?:Customer\s+Name|Lead\s+Name|Name|Client\s+Name)\]", "there", body, flags=re.IGNORECASE)

    if company_name:
        body = re.sub(r"\[(?:Company\s+Name|Company)\]", company_name, body, flags=re.IGNORECASE)

    body = re.sub(r"\[mention[^\]]*\]", "AI integration and workflow automation", body, flags=re.IGNORECASE)
    body = re.sub(r"\[Your\s+Name\]", "Tirth Patel", body, flags=re.IGNORECASE)

    # Standard sign-off block
    contact_email = os.getenv("CONTACT_EMAIL", "sales@nenotechnology.com")
    contact_phone = os.getenv("CONTACT_PHONE", "7863852024")
    signature_block = (
        "Warm regards,\n"
        "Tirth Patel\n"
        "Founder & CEO, \n"
        "Nenotechnology (Aineno Innovation Pvt. Ltd.)\n"
        "Ahmedabad, Gujarat\n"
        f"{contact_email} | +91 {contact_phone}\n"
        "www.nenotechnology.com"
    )

    # Prepare consultation booking CTA link
    booking_url = os.getenv(
        "BOOKING_FORM_URL",
        "https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled",
    )
    cta_link = tracking_link if tracking_link and "bookings.cloud.microsoft" in tracking_link else booking_url
    link_html = f'<a href="{cta_link}" style="color: #2563EB; font-weight: 600; text-decoration: underline;">Schedule a Consultation Call</a>'
    cta_sentence = f"Schedule your consultation here: {link_html}"

    if cta_link not in body:
        # If signature exists in body, insert CTA right before signature
        sig_match = re.search(r"(Warm regards|Best regards|Kind regards|Regards),?", body, flags=re.IGNORECASE)
        if sig_match:
            idx = sig_match.start()
            prefix = body[:idx].rstrip()
            suffix = body[idx:].strip()
            body = f"{prefix}\n\n{cta_sentence}\n\n{suffix}"
        else:
            body = body.rstrip() + f"\n\n{cta_sentence}\n\n{signature_block}"
    elif "Tirth Patel" not in body:
        body = body.rstrip() + f"\n\n{signature_block}"

    return subject, body




