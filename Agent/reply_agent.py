"""Inbound Customer Reply Agent for Nenotechnology.

Processes incoming customer replies from the support mailbox, strips quoted email history,
classifies the customer's intent, retrieves relevant company intelligence from the
Postgres/SQLite knowledge base (neno_technology_knowledge_base.md), and drafts a
polished, factual, knowledge-grounded response.
"""

import os
import re
from typing import Any, Dict, List, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.orm import Session

from Agent.llm import get_llm
from services.rag import retrieve_relevant_chunks

def extract_text_from_ai_message(content: Any) -> str:
    """Safely extracts clean human string text from LLM response content across all providers
    (string, list of dicts, Anthropic/Claude/Gemini content blocks, or stringified repr),
    guaranteeing no raw Python dicts, extras, or base64 signatures are ever returned.
    """
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                text_val = block.get("text", "")
                if text_val:
                    parts.append(text_val)
            elif hasattr(block, "text"):
                text_val = getattr(block, "text", "")
                if text_val:
                    parts.append(text_val)
            else:
                parts.append(str(block))
        result = "\n".join(parts).strip()
    elif isinstance(content, str):
        s = content.strip()
        # Check if the string is a stringified list of dicts: "[{'type': 'text', 'text': ..."
        if (s.startswith("[{") and ("'text'" in s or '"text"' in s)):
            try:
                import ast
                parsed = ast.literal_eval(s)
                if isinstance(parsed, list):
                    return extract_text_from_ai_message(parsed)
            except Exception:
                pass
            try:
                import json
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    return extract_text_from_ai_message(parsed)
            except Exception:
                pass
            import re
            m = re.search(r"['\"]text['\"]\s*:\s*(['\"])(.*?)\1(?:,\s*['\"]extras|\}\])", s, re.DOTALL)
            if m:
                try:
                    return m.group(2).encode().decode("unicode-escape").strip()
                except Exception:
                    return m.group(2).strip()
        result = s
    else:
        result = str(content).strip()

    # Safety: strip any stray 'extras': {'signature': ...} if present
    if "'extras':" in result:
        idx = result.find("'extras':")
        result = result[:idx].rstrip(", '\"{")
    if '"extras":' in result:
        idx = result.find('"extras":')
        result = result[:idx].rstrip(', \'"{')

    return result.strip()



REPLY_SYSTEM_PROMPT = """You are an AI Communications Executive representing:
Sender: Tirth Patel, Founder & CEO
Company: Nenotechnology (Aineno Innovation Pvt. Ltd.), Ahmedabad, Gujarat (www.nenotechnology.com)

Your job is to craft a warm, professional, high-converting, and accurate email reply to a customer or lead who replied to our outreach.

CRITICAL GROUNDING & STRICT REAL-DATA RULES:
1. STRICT REAL DATA ONLY: NEVER invent, assume, or hallucinate dummy names, placeholder companies, or fictional teams (such as 'ABCD', 'ABCD Team', 'Acme', 'XYZ Corp', etc.).
2. PERSONALIZATION:
   - If the lead's verified real name is provided (e.g. 'Mann' or 'Alex'), address them as 'Hi Mann,' or 'Hi Alex,'.
   - If the lead's name is not provided or unknown, use 'Hi there,' or 'Hello,'.
   - NEVER use an email address as a person's name (e.g. NEVER say 'Hi user@domain.com,').
   - NEVER fabricate or assume a company name if one is not verified.
3. GROUND IN KNOWLEDGE BASE (PDF): Use ONLY verified facts from the Neno Technology Knowledge Base (extracted directly from neno_technology_knowledge_base.pdf) to answer their questions accurately. 
   - If they ask about custom websites, portfolio sites, web platforms, or UI/UX: explain our full-stack engineering capabilities, clean modular frontend/backend architectures, high performance, responsive design, and bespoke showcase experiences.
   - If they ask about Forward-Deployed Engineering (FDE), explain how our engineers embed directly with their team, build production-grade agentic AI/systems, and accelerate time-to-market.
   - If they ask about voice agents, custom AI, CRM/ERP, or enterprise automation, provide the specific capabilities detailed in the knowledge base.
   - Do NOT invent fake pricing, fake certifications, or make unrealistic promises outside the knowledge base.
4. STRICTLY NO PLACEHOLDERS: NEVER include square brackets like "[Customer Name]", "[insert details]", "[Your Name]", etc.
5. TONE: Warm, responsive, consultative, and executive. Avoid robotic language or generic fluff.
6. CALL TO ACTION:
   - Encourage them to schedule a short consultation call to discuss their exact project requirements.
   - Direct them to our official Microsoft Bookings consultation portal:
     <a href="{booking_url}" style="color: #2563EB; font-weight: 600; text-decoration: underline;">Schedule a Consultation Call</a>
7. SIGN-OFF BLOCK:
   End with the exact executive sign-off:
   Warm regards,
   Tirth Patel
   Founder & CEO,
   Nenotechnology (Aineno Innovation Pvt. Ltd.)
   Ahmedabad, Gujarat
   sales@nenotechnology.com | +91 7863852024
   www.nenotechnology.com

SPECIAL CASES:
- If the customer says "not interested", "unsubscribe", or asks to be removed, reply politely acknowledging their request, assure them they are removed from future outreach, wish them success, and DO NOT push any meeting or sales pitch.
"""


CLASSIFIER_PROMPT = """Analyze the incoming customer email and classify the intent into exactly one category:
- question (the customer is asking about capabilities, services, tech stack, FDE, voice AI, pricing, process, or company details)
- interested (the customer expresses general interest in connecting, learning more, or discussing their project)
- meeting_request (the customer explicitly wants to book a call, meet, or see a demo)
- reschedule (the customer wants to reschedule an existing appointment or proposed time)
- not_interested (the customer declines, asks to unsubscribe, says no, or requests to be removed)

Respond with ONLY the category keyword (question, interested, meeting_request, reschedule, or not_interested). Do not include any other text."""


import html

def clean_inbound_message(raw_body: str) -> str:
    """Strips out quoted email headers, disclaimer footers, and historical thread trails
    so the AI analyzes only what the customer actually typed.
    """
    if not raw_body:
        return ""

    # Unescape HTML entities first (&lt; -> <, &gt; -> >, &nbsp; -> space)
    text = html.unescape(raw_body).replace("\r\n", "\n")

    # Replace block-level HTML tags with newlines before stripping
    text = re.sub(r"<(?:br|p|div|tr)[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)

    # Comprehensive thread cut patterns (Outlook, Gmail, Apple Mail)
    cut_patterns = [
        r"_{5,}",  # Outlook separator line: _____
        r"-{4,}\s*Original Message\s*-{4,}",
        r"-{4,}\s*Forwarded message\s*-{4,}",
        r"\bFrom:\s+.*",
        r"\bDe:\s+.*",
        r"\bVon:\s+.*",
        r"On\s+[A-Za-z]+,\s+[A-Za-z]+\s+\d+.*wrote:",
        r"On\s+.*,\s+.*wrote:",
        r"Sent from my (?:iPhone|Android|Galaxy|iPad)",
        r"Get Outlook for (?:iOS|Android)",
        r"If you no longer wish to receive updates",
    ]

    for pat in cut_patterns:
        match = re.search(pat, text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            text = text[:match.start()]

    # Collapse consecutive whitespace & empty lines
    lines = [line.strip() for line in text.split("\n")]
    cleaned = "\n".join(line for line in lines if line)
    return cleaned.strip()


def classify_reply_intent(customer_text: str) -> str:
    """Classifies the customer's reply into one of the known intent categories."""
    if not customer_text or len(customer_text.strip()) == 0:
        return "question"

    lower = customer_text.lower().strip()
    # Fast regex heuristics for immediate opt-out detection (ONLY on customer's actual text)
    if any(phrase in lower for phrase in ["unsubscribe", "remove me", "stop emailing", "not interested", "no thanks", "take me off", "leave me alone"]):
        return "not_interested"

    if any(phrase in lower for phrase in ["schedule a call", "book a call", "book a meeting", "let's meet", "calendar", "free at", "available at"]):
        return "meeting_request"

    if any(phrase in lower for phrase in ["reschedule", "change time", "another time", "postpone"]):
        return "reschedule"

    try:
        llm = get_llm()
        resp = llm.invoke([
            SystemMessage(content=CLASSIFIER_PROMPT),
            HumanMessage(content=f"Customer email:\n\"\"\"{customer_text}\"\"\"")
        ])
        content = resp.content.strip().lower() if isinstance(resp.content, str) else "question"
        for candidate in ["not_interested", "meeting_request", "reschedule", "interested", "question"]:
            if candidate in content:
                return candidate
    except Exception as e:
        print(f"[Notice] Fallback classifier used: {e}")

    return "question"


def process_incoming_reply(
    db: Session,
    from_email: str,
    from_name: Optional[str] = None,
    company: Optional[str] = None,
    subject: Optional[str] = None,
    raw_body: Optional[str] = None,
    custom_instructions: Optional[str] = None,
) -> Dict[str, Any]:
    """Main orchestration function:
    1. Cleans the customer's message body.
    2. Classifies intent.
    3. Retrieves top relevant knowledge base chunks from neno_technology_knowledge_base.md.
    4. Composes an AI answer grounded in the retrieved context.
    """
    cleaned_body = clean_inbound_message(raw_body or "")
    if not cleaned_body and raw_body:
        cleaned_body = raw_body.strip()[:500]

    intent = classify_reply_intent(cleaned_body)

    booking_url = os.getenv(
        "BOOKING_FORM_URL",
        "https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled",
    )

    # If opt-out, provide an immediate polite de-escalation response
    if intent == "not_interested":
        polite_optout = (
            f"Hi {from_name or 'there'},\n\n"
            f"Thank you for letting us know. I have updated our records, and you will not receive any further emails from us regarding this sequence.\n\n"
            f"We appreciate your time and wish you and your team continued success.\n\n"
            f"Warm regards,\n"
            f"Tirth Patel\n"
            f"Founder & CEO,\n"
            f"Nenotechnology (Aineno Innovation Pvt. Ltd.)\n"
            f"Ahmedabad, Gujarat\n"
            f"sales@nenotechnology.com | +91 7863852024\n"
            f"www.nenotechnology.com"
        )
        return {
            "intent": "not_interested",
            "response_text": polite_optout,
            "context_chunks": [],
            "cleaned_message": cleaned_body,
        }

    # Query knowledge base for relevant context
    query_text = f"{subject or ''} {cleaned_body}".strip()
    context_chunks = []
    try:
        context_chunks = retrieve_relevant_chunks(db, query=query_text, top_k=4, min_score=0.40)
    except Exception as e:
        print(f"[Warning] RAG retrieval error: {e}")

    # Build context string
    formatted_chunks = []
    for i, c in enumerate(context_chunks, 1):
        formatted_chunks.append(f"--- Context Chunk {i} [{c.get('title', 'KB')}] (Relevance: {c.get('score', 0)}) ---\n{c.get('content', '')}")

    context_str = "\n\n".join(formatted_chunks) if formatted_chunks else "No specific knowledge chunks retrieved. Answer based on core Nenotechnology capabilities (production AI, voice agents, autonomous software systems, enterprise automation)."

    system_prompt = REPLY_SYSTEM_PROMPT.format(booking_url=booking_url)

    # Sanitize lead name and company to strictly avoid dummy entities, placeholders, or email greetings
    clean_name = (from_name or "").strip()
    if "@" in clean_name or clean_name.lower().startswith("test") or clean_name.lower() in ["customer", "inbound lead", "lead", "none", "nan", "unknown"]:
        clean_name = ""

    clean_company = (company or "").strip()
    if clean_company.lower() in ["inbound lead", "not specified", "unknown", "lead", "none", "nan", "—", "-"]:
        clean_company = ""

    user_prompt_lines = [
        f"Customer Email: {from_email}",
        f"Customer Name: {clean_name or 'Unknown (Address as: Hi there, or Hello,)'}",
        f"Customer Company: {clean_company or 'Not specified (DO NOT invent a fake company name)'}",
        f"Incoming Subject: {subject or 'Inquiry'}",
        f"Customer's Inbound Message:\n\"\"\"\n{cleaned_body}\n\"\"\"",
        f"Detected Intent: {intent}",
        f"\n=== RETRIEVED KNOWLEDGE BASE CONTEXT (VERIFIED PDF FACTS) ===\n{context_str}\n==========================================",
    ]

    if custom_instructions:
        user_prompt_lines.append(f"Additional Instructions: {custom_instructions}")

    user_prompt_lines.append(
        "\nDraft the email response now. Address their query thoroughly using the verified knowledge base facts above. NEVER invent placeholder company names (e.g. 'ABCD', 'Acme'). Include the consultation link and executive sign-off."
    )

    user_prompt = "\n".join(user_prompt_lines)

    llm = get_llm()
    resp = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ])

    response_text = extract_text_from_ai_message(resp.content)


    # Ensure booking link is present if not already embedded
    if "bookings.cloud.microsoft" not in response_text and intent != "not_interested":
        cta_html = f'<p style="margin: 16px 0;"><a href="{booking_url}" style="color: #2563EB; font-weight: 600; text-decoration: underline;">Schedule a Consultation Call Here</a></p>'
        sig_match = re.search(r"(Warm regards|Best regards|Kind regards|Regards),?", response_text, flags=re.IGNORECASE)
        if sig_match:
            idx = sig_match.start()
            response_text = f"{response_text[:idx].rstrip()}\n\n{cta_html}\n\n{response_text[idx:].strip()}"
        else:
            response_text = f"{response_text.rstrip()}\n\n{cta_html}"

    # Build standard corporate threaded email with primary mail body quoted
    formatted_html = build_threaded_reply_html(
        ai_response_text=response_text,
        sender_name=from_name,
        sender_email=from_email,
        subject=subject,
        received_time=None,
        original_body=cleaned_body or raw_body,
        booking_url=booking_url,
    )
    formatted_text = build_threaded_reply_plain(
        ai_response_text=response_text,
        sender_name=from_name,
        sender_email=from_email,
        subject=subject,
        received_time=None,
        original_body=cleaned_body or raw_body,
        booking_url=booking_url,
    )

    return {
        "intent": intent,
        "response_text": response_text,
        "formatted_email_html": formatted_html,
        "formatted_email_text": formatted_text,
        "context_chunks": context_chunks,
        "cleaned_message": cleaned_body,
        "original_body": raw_body or cleaned_body,
    }


def build_threaded_reply_html(
    ai_response_text: str,
    sender_name: Optional[str],
    sender_email: str,
    subject: Optional[str],
    received_time: Optional[str] = None,
    original_body: Optional[str] = None,
    booking_url: str = "https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled",
) -> str:
    """Builds a complete, executive corporate reply email in standard Outlook/enterprise format:
    1. AI response grounded in the Neno Technology Knowledge Base PDF.
    2. Consultation Call button & direct link to Microsoft Bookings.
    3. Executive sign-off block from Tirth Patel (Founder & CEO).
    4. Clean Outlook separator line (<hr>).
    5. Standard quoted header (From, Sent, To, Subject).
    6. Quoted primary incoming message body (copied verbatim from primary mail).
    """
    clean_name = (sender_name or "").strip() or "Customer"
    subj = (subject or "Inquiry").strip()
    from_date = (received_time or "Recent").strip()

    # Convert AI response text into clean HTML paragraphs
    paragraphs = [p.strip() for p in ai_response_text.replace("\r\n", "\n").split("\n\n") if p.strip()]
    ai_html_parts = []
    for p in paragraphs:
        # Avoid double wrapping if already contains HTML tags like <a> or <p>
        if p.startswith(("<p", "<div", "<table", "<ul", "<ol", "<blockquote")):
            ai_html_parts.append(p)
        else:
            p_formatted = p.replace("\n", "<br>")
            ai_html_parts.append(
                f'<p style="margin: 0 0 13px 0; font-family: Arial, Helvetica, sans-serif; font-size: 14.5px; line-height: 1.6; color: #1E293B;">{p_formatted}</p>'
            )
    ai_html_body = "\n".join(ai_html_parts)

    # Prepare consultation call CTA button if not already in text
    cta_block = ""
    if booking_url and booking_url not in ai_response_text and "unsubscribe" not in ai_response_text.lower():
        cta_block = f"""
        <div style="margin: 20px 0;">
            <table cellpadding="0" cellspacing="0" border="0" style="border-collapse: separate;">
                <tr>
                    <td style="background-color: #2563EB; border-radius: 6px; text-align: center;">
                        <a href="{booking_url}" target="_blank"
                           style="display: inline-block; padding: 12px 24px; color: #FFFFFF; font-family: Arial, sans-serif; font-size: 14px; font-weight: bold; text-decoration: none; border-radius: 6px;">
                           📅 Schedule a Consultation Call
                        </a>
                    </td>
                </tr>
            </table>
            <div style="margin-top: 8px; font-size: 12.5px; color: #64748B; font-family: Arial, sans-serif;">
                Direct booking URL: <a href="{booking_url}" style="color: #2563EB; text-decoration: underline;">{booking_url}</a>
            </div>
        </div>
        """

    # Quoted primary incoming message section
    quoted_section = ""
    if original_body and original_body.strip():
        # Clean incoming text
        raw_clean = original_body.strip()
        if not raw_clean.startswith("<"):
            orig_html = raw_clean.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        else:
            orig_html = raw_clean

        quoted_section = f"""
        <div style="margin-top: 28px; padding-top: 4px;">
            <hr style="border: none; border-top: 1px solid #CBD5E1; margin: 0 0 16px 0;" />
            <div style="font-family: Arial, Helvetica, sans-serif; font-size: 12.5px; color: #475569; line-height: 1.5; margin-bottom: 12px;">
                <b>From:</b> {clean_name} &lt;<a href="mailto:{sender_email}" style="color: #2563EB; text-decoration: none;">{sender_email}</a>&gt;<br>
                <b>Sent:</b> {from_date}<br>
                <b>To:</b> Support &lt;<a href="mailto:support@nenotechnology.com" style="color: #2563EB; text-decoration: none;">support@nenotechnology.com</a>&gt;<br>
                <b>Subject:</b> {subj}
            </div>
            <div style="border-left: 3px solid #CBD5E1; padding-left: 14px; margin-left: 2px; font-family: Arial, Helvetica, sans-serif; font-size: 13.5px; color: #334155; line-height: 1.55;">
                {orig_html}
            </div>
        </div>
        """

    full_html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 12px; font-family: Arial, Helvetica, sans-serif; background-color: #FFFFFF;">
  <div style="max-width: 650px; margin: 0 auto; color: #1E293B;">
    {ai_html_body}
    {cta_block}
    {quoted_section}
  </div>
</body>
</html>"""
    return full_html.strip()


def build_threaded_reply_plain(
    ai_response_text: str,
    sender_name: Optional[str],
    sender_email: str,
    subject: Optional[str],
    received_time: Optional[str] = None,
    original_body: Optional[str] = None,
    booking_url: str = "https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled",
) -> str:
    """Builds a plaintext corporate reply with quoted primary incoming message."""
    clean_name = (sender_name or "").strip() or "Customer"
    subj = (subject or "Inquiry").strip()
    from_date = (received_time or "Recent").strip()

    parts = [ai_response_text.strip()]

    if booking_url and booking_url not in ai_response_text and "unsubscribe" not in ai_response_text.lower():
        parts.append(f"\nSchedule a Consultation Call:\n{booking_url}")

    if original_body and original_body.strip():
        # Strip HTML if present for plaintext quote
        clean_orig = re.sub(r"<[^>]+>", " ", original_body)
        clean_orig = "\n".join(l.strip() for l in clean_orig.split("\n") if l.strip())
        parts.append(
            f"\n\n-----Original Message-----\n"
            f"From: {clean_name} <{sender_email}>\n"
            f"Sent: {from_date}\n"
            f"To: Support <support@nenotechnology.com>\n"
            f"Subject: {subj}\n\n"
            f"{clean_orig.strip()}"
        )

    return "\n".join(parts)
