"""Continuous / On-Demand Inbound Reply Worker for Nenotechnology.

Monitors the Microsoft Graph / Outlook inbox (support@nenotechnology.com) for
incoming customer emails and replies. For each customer message:
1. Cleans the incoming message and retrieves company knowledge base context
   strictly grounded in neno_technology_knowledge_base.pdf.
2. Generates an AI answer grounded in the verified PDF knowledge base.
3. Automatically dispatches the email reply via Microsoft Graph using the
   executive corporate reply format (AI answer + Microsoft Bookings button/link
   + signature + quoted primary mail headers and body).
4. Marks the message as read in Outlook to avoid duplicates.
5. Ingests Microsoft Bookings consultation notifications into booked_leads.xlsx.
6. Updates CampaignLog in SQLite/Postgres and customer_replies.xlsx.

Usage:
    python reply_worker.py          # Runs continuous monitoring loop (polls every 30s)
    python reply_worker.py --once   # Runs a single scan & reply pass then exits
    python reply_worker.py --sync   # Runs full inbox sync & backfill
"""

import argparse
import html
import os
import re
import sys
import time

import utils.dns_patch
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        pass

import requests
from dotenv import load_dotenv

load_dotenv()

from Agent.reply_agent import (
    build_threaded_reply_html,
    build_threaded_reply_plain,
    process_incoming_reply,
)
from Backend.db import SessionLocal, init_db
from Backend.models import CampaignLog
from Email import get_mailer
from services.excel_logger import log_booking_to_excel, log_reply_to_excel
from utils.microsoft_auth import MS_SENDER_EMAIL, get_graph_headers

init_db()

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
SYSTEM_SENDERS = [
    "copy@nenotechnology.com",
    "support@nenotechnology.com",
    "no-reply@microsoft.com",
    "noreply@microsoft.com",
    "mailer-daemon@googlemail.com",
]

BOOKING_URL = os.getenv(
    "BOOKING_FORM_URL",
    "https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled",
)


import threading


class ReplyDaemonManager:
    """Thread-safe background daemon manager to monitor the Outlook inbox
    continuously while the application / dashboard is running.
    """
    _thread: Optional[threading.Thread] = None
    _stop_event: threading.Event = threading.Event()
    _is_running: bool = False
    _last_run: Optional[datetime] = None
    _last_summary: Optional[Dict[str, Any]] = None

    @classmethod
    def is_running(cls) -> bool:
        return cls._is_running and cls._thread is not None and cls._thread.is_alive()

    @classmethod
    def start(cls, interval_seconds: int = 15):
        if cls.is_running():
            return
        cls._stop_event.clear()
        cls._is_running = True

        def _loop():
            from Backend.db import SessionLocal
            from Backend.crud import sync_excel_and_outlook_to_db

            print(f"[Daemon] Continuous real-time background sync started (every {interval_seconds}s).")
            _network_offline_logged = False
            while not cls._stop_event.is_set():
                try:
                    summary = check_and_reply_inbox()
                    cls._last_run = datetime.now()
                    cls._last_summary = summary
                    if summary and summary.get("error") == "network_unavailable":
                        if not _network_offline_logged:
                            print("[Daemon Outlook] ⚠️ Internet/DNS connection to Microsoft Graph is temporarily offline. Waiting for network reconnection...")
                            _network_offline_logged = True
                    else:
                        if _network_offline_logged:
                            print("[Daemon Outlook] ✅ Microsoft Graph internet connection restored.")
                            _network_offline_logged = False
                except Exception as e:
                    err_text = str(e)
                    if any(k in err_text for k in ("getaddrinfo failed", "NameResolutionError", "Max retries exceeded", "ConnectionError")):
                        if not _network_offline_logged:
                            print("[Daemon Outlook] ⚠️ Temporary network/DNS connection hiccup to Microsoft Graph. Retrying automatically...")
                            _network_offline_logged = True
                    else:
                        print(f"[Daemon Outlook Error]: {e}")

                try:
                    _db = SessionLocal()
                    sync_excel_and_outlook_to_db(_db)
                    _db.close()
                except Exception as e:
                    err_text = str(e)
                    if not any(k in err_text for k in ("getaddrinfo failed", "NameResolutionError", "Max retries exceeded")):
                        print(f"[Daemon Sync Error]: {e}")

                for _ in range(interval_seconds):
                    if cls._stop_event.is_set():
                        break
                    time.sleep(1)
            cls._is_running = False

        cls._thread = threading.Thread(target=_loop, daemon=True, name="ReplyDaemonThread")
        cls._thread.start()

    @classmethod
    def stop(cls):
        cls._stop_event.set()
        cls._is_running = False

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        return {
            "running": cls.is_running(),
            "last_run": cls._last_run,
            "last_summary": cls._last_summary,
        }


def _format_reply_subject(original_subject: Optional[str]) -> str:
    subj = (original_subject or "Inquiry").strip()
    if not subj.lower().startswith("re:"):
        return f"Re: {subj}"
    return subj


def _send_graph_reply(
    message_id: str,
    to_email: str,
    subject: str,
    body_html: str,
    body_text: Optional[str] = None,
) -> bool:
    """Dispatches the reply email using Microsoft Graph.
    Attempts thread reply first, then falls back to sendMail via OutlookMailer.
    Guarantees the email includes the AI response, the official Microsoft Bookings URL,
    and the quoted primary message.
    """
    headers = get_graph_headers()

    # 1. Attempt Graph direct thread reply
    reply_url = f"{GRAPH_BASE}/users/{MS_SENDER_EMAIL}/messages/{message_id}/reply"
    payload = {"comment": body_html}

    try:
        resp = requests.post(reply_url, headers=headers, json=payload, timeout=25)
        if resp.status_code in [200, 202]:
            return True
        print(f"[Notice] Direct thread reply returned {resp.status_code}: {resp.text[:120]}. Falling back to send_email.")
    except Exception as e:
        print(f"[Notice] Thread reply request exception: {e}. Falling back to send_email.")

    # 2. Fallback to standard outbound dispatch (sends full HTML MIME with quoted thread)
    try:
        mailer = get_mailer()
        mailer.send_email(
            to_email=to_email,
            subject=_format_reply_subject(subject),
            body=body_html,
        )
        return True
    except Exception as e:
        print(f"[Error] send_email fallback failed for {to_email}: {e}")
        return False


def is_message_already_processed(db, message_id: str, sender_email: str = "") -> bool:
    """Checks local database to see if this message_id has already been processed or dismissed."""
    if not message_id or db is None:
        return False
    try:
        from sqlalchemy import text
        row = db.execute(text("SELECT status FROM processed_replies WHERE message_id = :mid LIMIT 1"), {"mid": message_id}).fetchone()
        if not row:
            return False
        st = str(row[0] or "").strip()
        if st in [
            "historical_before_send_skipped",
            "no_outreach_sent_skipped",
            "old_booking_suppressed",
            "old_historical_suppressed",
            "processed",
            "ndr_skipped",
            "system_notice_skipped",
        ]:
            return True
        # If it was previously skipped as internal staff/non-campaign, only re-evaluate if lead has actually been sent an outreach email
        if st in ["internal_staff_skipped", "non_campaign_skipped"]:
            if not sender_email:
                return True
            from Backend.models import CampaignLog
            sent_lead = (
                db.query(CampaignLog)
                .filter(CampaignLog.email.ilike(sender_email.strip()), CampaignLog.email_sent_at.isnot(None))
                .first()
            )
            if sent_lead:
                return False
            return True
        return True
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return False


def record_message_processed(db, message_id: str, sender_email: str = "", subject: str = "", status: str = "processed"):
    """Persists message_id locally into processed_replies so it is never re-processed even if Graph PATCH is forbidden."""
    if not message_id or db is None:
        return
    try:
        import uuid
        from sqlalchemy import text
        db.execute(
            text(
                "INSERT INTO processed_replies (id, message_id, sender_email, subject, status) "
                "VALUES (:id, :mid, :sender, :subj, :status) "
                "ON CONFLICT (message_id) DO UPDATE SET status = :status"
            ),
            {
                "id": f"pr_{uuid.uuid4().hex[:12]}",
                "mid": message_id,
                "sender": sender_email or "",
                "subj": subject or "",
                "status": status,
            }
        )
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass


def _mark_message_read(message_id: str, db=None, sender_email: str = "", subject: str = "", status: str = "processed") -> bool:
    """Marks message as processed locally in DB and attempts Graph PATCH."""
    if db is not None:
        record_message_processed(db, message_id, sender_email, subject, status)
    headers = get_graph_headers()
    url = f"{GRAPH_BASE}/users/{MS_SENDER_EMAIL}/messages/{message_id}"
    try:
        resp = requests.patch(url, headers=headers, json={"isRead": True}, timeout=15)
        return resp.status_code in [200, 204]
    except Exception as e:
        return False



def parse_microsoft_booking_notification(subject: str, body_content: str) -> Optional[Dict[str, Any]]:
    """Parses automated Microsoft Bookings confirmation emails sent to support@nenotechnology.com
    (e.g., 'New booking: for support', 'New booking: for 15-min meeting', etc.)
    and extracts client appointment details.
    """
    if not any(term in subject.lower() for term in ["new booking:", "booking confirmation"]):
        return None

    # Strip HTML tags
    clean_text = html.unescape(body_content).replace("\r\n", "\n")
    clean_text = re.sub(r"<[^>]+>", "\n", clean_text)
    lines = [l.strip() for l in clean_text.split("\n") if l.strip()]

    name = ""
    service = "Consultation / Support"
    slot = ""

    for i, l in enumerate(lines):
        if "new booking from" in l.lower() and i + 1 < len(lines):
            name = lines[i + 1].strip()
        if "with support" in l.lower():
            svc_line = lines[i].replace("with Support", "").replace("with support", "").strip()
            if not svc_line and i > 0:
                svc_line = lines[i - 1].strip()
            if svc_line and "new booking from" not in svc_line.lower():
                service = svc_line
        if any(day in l for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]):
            time_part = lines[i + 1] if i + 1 < len(lines) and ("AM" in lines[i + 1] or "PM" in lines[i + 1]) else ""
            slot = f"{l} {time_part}".strip()

    if not name or len(name) < 2:
        match = re.search(r"New booking from\s+([A-Za-z0-9\s]+?)(?:with Support|support|\n)", clean_text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()

    if not name:
        return None

    return {
        "name": name,
        "service": service,
        "slot": slot or "Confirmed Booking Slot",
        "subject": subject,
    }


def check_and_reply_inbox(db=None, sync_existing: bool = False) -> Dict[str, Any]:
    """Scans the inbox for customer replies, retrieves knowledge base facts from the PDF,
    and dispatches automated responses with the primary mail quoted. Also syncs Microsoft Bookings.
    Returns a summary dict of actions taken.
    """
    close_db_at_end = False
    if db is None:
        db = SessionLocal()
        close_db_at_end = True

    results = {
        "processed_count": 0,
        "replied_count": 0,
        "bookings_synced": 0,
        "skipped_count": 0,
        "failed_count": 0,
        "details": [],
    }

    try:
        # ── Zero-Data Safety Guard ──
        total_campaign_leads = db.query(CampaignLog).count()
        leads_sheet_count = 0
        try:
            leads_path = os.getenv("LEADS_FILE", "leads.xlsx")
            if os.path.exists(leads_path):
                import pandas as pd
                leads_sheet_count = len(pd.read_excel(leads_path))
        except Exception:
            pass

        if total_campaign_leads == 0 and leads_sheet_count == 0:
            print("[Notice] Zero campaign leads in database/sheet (system has zero data). Auto-reply paused until real leads are imported.")
            results["message"] = "Zero campaign leads in system. Auto-reply paused."
            return results

        # Fetch recent inbox messages sorted by newest first (read and unread).
        # We rely on is_message_already_processed() and DB reply state to skip old emails,
        # ensuring customer replies are never missed even if viewed in Outlook!
        top_limit = 40 if sync_existing else 30
        inbox_url = (
            f"{GRAPH_BASE}/users/{MS_SENDER_EMAIL}/mailFolders/inbox/messages"
            f"?$orderby=receivedDateTime desc&$top={top_limit}"
        )

        try:
            headers = get_graph_headers()
            resp = requests.get(inbox_url, headers=headers, timeout=15)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as net_err:
            results["error"] = "network_unavailable"
            results["message"] = f"Network or DNS connection offline ({net_err.__class__.__name__})."
            return results
        except Exception as ex:
            err_str = str(ex)
            if any(k in err_str for k in ("getaddrinfo failed", "NameResolutionError", "Max retries exceeded")):
                results["error"] = "network_unavailable"
                results["message"] = "DNS resolution for graph.microsoft.com failed."
                return results
            results["error"] = "graph_error"
            results["message"] = err_str
            return results

        if resp.status_code != 200:
            print(f"[Error] Failed to read inbox from Microsoft Graph ({resp.status_code}): {resp.text}")
            return results

        messages = resp.json().get("value", [])
        if not messages:
            return results

        # Track emails processed in this pass
        processed_emails_this_run = set()
        OLD_SUPPRESSED_BOOKINGS = {
            "dhruv mali", "mit patel", "het suthar", "patel", "mit dharmeshbhai patel",
            "hardini dalwadi", "hardini", "ajay", "ajay patel"
        }

        for msg in messages:
            msg_id = msg.get("id")
            subject = msg.get("subject") or ""
            from_dict = msg.get("from", {}).get("emailAddress", {})
            sender_addr = (from_dict.get("address") or "").strip().lower()
            sender_name = from_dict.get("name") or ""

            if is_message_already_processed(db, msg_id, sender_email=sender_addr):
                continue

            body_dict = msg.get("body", {})
            body_content = body_dict.get("content") or msg.get("bodyPreview") or ""
            recv_time = msg.get("receivedDateTime") or ""

            # Ignore NDR bounces
            is_ndr = (
                sender_addr.startswith("microsoftexchange")
                or sender_addr.startswith("postmaster@")
                or sender_addr.startswith("mailer-daemon@")
                or subject.lower().startswith("undeliverable:")
                or "delivery status notification" in subject.lower()
            )
            if is_ndr:
                results["skipped_count"] += 1
                _mark_message_read(msg_id, db=db, sender_email=sender_addr, subject=subject, status="ndr_skipped")
                continue

            # ── Check for Microsoft Bookings notification emails ──
            booking_info = parse_microsoft_booking_notification(subject, body_content)
            if booking_info:
                client_name = booking_info["name"].strip()

                # Look up if this booking belongs to an existing campaign lead
                b_lead = (
                    db.query(CampaignLog)
                    .filter(CampaignLog.name.ilike(client_name))
                    .first()
                )
                if not b_lead:
                    for word in client_name.split():
                        if len(word) > 2:
                            b_lead = (
                                db.query(CampaignLog)
                                .filter(CampaignLog.name.ilike(f"%{word}%"))
                                .first()
                            )
                            if b_lead:
                                break

                # Never invent synthetic IDs. If not an existing campaign lead, or suppressed, skip it.
                if (
                    client_name.lower() in OLD_SUPPRESSED_BOOKINGS
                    or msg.get("isRead", False)
                    or not b_lead
                    or "client.nenotechnology.com" in getattr(b_lead, "email", "").lower()
                ):
                    results["skipped_count"] += 1
                    _mark_message_read(msg_id, db=db, sender_email=sender_addr, subject=subject, status="old_booking_suppressed")
                    continue

                client_service = booking_info["service"]
                client_slot = booking_info["slot"]

                try:
                    b_lead.booking_status = "meeting_scheduled"
                    b_lead.status = "meeting_scheduled"
                    b_lead.confirmed_slot = client_slot
                    b_lead.form_filled_at = datetime.now(timezone.utc)
                    db.commit()

                    log_booking_to_excel(
                        email=b_lead.email,
                        name=b_lead.name or client_name,
                        company=b_lead.company or "Client",
                        confirmed_slot=client_slot,
                        meet_link=BOOKING_URL,
                    )
                    results["bookings_synced"] += 1
                    _mark_message_read(msg_id, db=db, sender_email=b_lead.email, subject=subject, status="booking_synced")
                    print(f"[Bookings] Synced appointment for verified campaign lead '{b_lead.name}' <{b_lead.email}> ({client_slot}).")
                except Exception as ex:
                    print(f"[Warning] Error logging booking for {client_name}: {ex}")

                continue

            # Skip internal system notifications & internal staff emails from @nenotechnology.com
            if any(term in subject.lower() for term in ["added you as a staff member", "declined:", "accepted:"]):
                results["skipped_count"] += 1
                _mark_message_read(msg_id, db=db, sender_email=sender_addr, subject=subject, status="system_notice_skipped")
                continue

            # Check if this sender is a registered outreach campaign lead
            is_campaign_lead = (
                db.query(CampaignLog).filter(CampaignLog.email.ilike(sender_addr)).first() is not None
            )
            if not is_campaign_lead:
                try:
                    leads_path = os.getenv("LEADS_FILE", "leads.xlsx")
                    if os.path.exists(leads_path):
                        import pandas as pd
                        ldf = pd.read_excel(leads_path)
                        if "email" in ldf.columns:
                            is_campaign_lead = not ldf[ldf["email"].astype(str).str.strip().str.lower() == sender_addr].empty
                except Exception:
                    pass

            if (
                not sender_addr
                or sender_addr in SYSTEM_SENDERS
                or sender_addr == MS_SENDER_EMAIL.lower()
                or (sender_addr.endswith("@nenotechnology.com") and not is_campaign_lead)
            ):
                results["skipped_count"] += 1
                _mark_message_read(msg_id, db=db, sender_email=sender_addr, subject=subject, status="internal_staff_skipped")
                continue

            # Avoid double replying in the same batch run
            if sender_addr in processed_emails_this_run:
                continue

            is_msg_read = bool(msg.get("isRead", False))

            # ── Strict Real-Data Verification ──
            # Look up existing outreach lead in DB
            lead = (
                db.query(CampaignLog)
                .filter(CampaignLog.email.ilike(sender_addr))
                .order_by(CampaignLog.created_at.desc())
                .first()
            )

            lead_from_sheet = None
            if lead is None:
                try:
                    leads_path = os.getenv("LEADS_FILE", "leads.xlsx")
                    if os.path.exists(leads_path):
                        import pandas as pd
                        ldf = pd.read_excel(leads_path)
                        if "email" in ldf.columns:
                            match = ldf[ldf["email"].astype(str).str.strip().str.lower() == sender_addr]
                            if not match.empty:
                                lead_from_sheet = match.iloc[0]
                except Exception:
                    pass

            # If sender is not an outreach campaign lead, strictly skip to prevent dummy leads & hallucinations
            if lead is None and lead_from_sheet is None:
                results["skipped_count"] += 1
                _mark_message_read(msg_id, db=db, sender_email=sender_addr, subject=subject, status="non_campaign_skipped")
                print(f"[Inbox] Skipped sender '{sender_addr}': Not an outreach campaign lead (Strict Real-Data Mode).")
                continue

            # ── Strict Sent-Verification: Message can ONLY be a campaign reply if outreach was actually sent! ──
            lead_sent_at = lead.email_sent_at if lead else None
            if not lead_sent_at and lead_from_sheet is not None:
                sheet_sent = lead_from_sheet.get("email_sent_at")
                if pd.notna(sheet_sent) and str(sheet_sent).strip():
                    try:
                        lead_sent_at = datetime.fromisoformat(str(sheet_sent).replace("Z", "+00:00"))
                    except Exception:
                        pass

            if not lead_sent_at:
                results["skipped_count"] += 1
                _mark_message_read(msg_id, db=db, sender_email=sender_addr, subject=subject, status="no_outreach_sent_skipped")
                print(f"[Inbox] Skipped message from '{sender_addr}': No outreach email was ever sent to this lead.")
                continue

            # Incoming message can ONLY be a reply if received strictly AFTER email_sent_at!
            if recv_time:
                try:
                    msg_dt = datetime.fromisoformat(recv_time.replace("Z", "+00:00"))
                    sent_dt = lead_sent_at
                    if sent_dt.tzinfo is None:
                        sent_dt = sent_dt.replace(tzinfo=timezone.utc)
                    if msg_dt <= sent_dt:
                        results["skipped_count"] += 1
                        _mark_message_read(msg_id, db=db, sender_email=sender_addr, subject=subject, status="historical_before_send_skipped")
                        print(f"[Inbox] Skipped historical message from '{sender_addr}' (received {msg_dt} before/at outreach sent at {sent_dt}).")
                        continue
                except Exception as e:
                    print(f"[Warning] Timestamp comparison error: {e}")

            # Check if an AI reply was already recorded for this lead
            already_replied = bool(lead and lead.ai_reply_sent and lead.status == "replied")

            # If this lead was already replied to, skip re-sending
            if already_replied and not sync_existing:
                results["skipped_count"] += 1
                continue

            results["processed_count"] += 1
            processed_emails_this_run.add(sender_addr)
            print(f"[Agent Activated] Inbound customer reply detected from {sender_name} <{sender_addr}>: '{subject}'. Activating RAG grounded auto-reply...")

            # Extract real verified name and company
            if lead:
                company_name = lead.company if lead.company and lead.company.strip().lower() not in ["inbound lead", "none", "nan", "—", "-"] else None
                effective_name = lead.name if lead.name and "@" not in lead.name and lead.name.strip().lower() not in ["none", "nan", "customer"] else None
            elif lead_from_sheet is not None:
                sheet_company = str(lead_from_sheet.get("company") or "").strip()
                sheet_name = str(lead_from_sheet.get("name") or "").strip()
                company_name = sheet_company if sheet_company and sheet_company.lower() not in ["none", "nan", "—", "-"] else None
                effective_name = sheet_name if sheet_name and "@" not in sheet_name and sheet_name.lower() not in ["none", "nan", "customer"] else None
            else:
                company_name = None
                effective_name = None

            if not effective_name and sender_name and "@" not in sender_name and not sender_name.lower().startswith("test"):
                effective_name = sender_name.strip()

            # Format received datetime
            fmt_received_date = recv_time
            if recv_time:
                try:
                    dt = datetime.fromisoformat(recv_time.replace("Z", "+00:00"))
                    fmt_received_date = dt.strftime("%A, %B %d, %Y %I:%M %p UTC")
                except Exception:
                    fmt_received_date = recv_time

            # Process with AI Reply Agent grounded in neno_technology_knowledge_base.pdf
            try:
                agent_res = process_incoming_reply(
                    db=db,
                    from_email=sender_addr,
                    from_name=effective_name,
                    company=company_name,
                    subject=subject,
                    raw_body=body_content,
                )
            except Exception as e:
                print(f"[Error] AI reply agent failed for {sender_addr}: {e}")
                results["failed_count"] += 1
                continue

            reply_text = agent_res.get("response_text", "")
            intent = agent_res.get("intent", "question")
            cleaned_msg = agent_res.get("cleaned_message", "")
            chunks_used = agent_res.get("context_chunks", [])
            primary_mail_body = agent_res.get("original_body") or cleaned_msg or body_content

            # Build the complete threaded email HTML & plain text with quoted primary mail
            full_reply_html = build_threaded_reply_html(
                ai_response_text=reply_text,
                sender_name=effective_name,
                sender_email=sender_addr,
                subject=subject,
                received_time=fmt_received_date,
                original_body=primary_mail_body,
                booking_url=BOOKING_URL,
            )
            full_reply_text = build_threaded_reply_plain(
                ai_response_text=reply_text,
                sender_name=effective_name,
                sender_email=sender_addr,
                subject=subject,
                received_time=fmt_received_date,
                original_body=primary_mail_body,
                booking_url=BOOKING_URL,
            )

            # If not yet replied, send the AI response email via Microsoft Graph
            sent_ok = False
            if not already_replied:
                sent_ok = _send_graph_reply(
                    message_id=msg_id,
                    to_email=sender_addr,
                    subject=subject,
                    body_html=full_reply_html,
                    body_text=full_reply_text,
                )
            else:
                sent_ok = True  # Already dispatched previously

            if sent_ok:
                results["replied_count"] += 1
                now_utc = datetime.now(timezone.utc)

                # Mark read in Graph & record in local processed list
                _mark_message_read(msg_id, db=db, sender_email=sender_addr, subject=subject, status="processed")

                # Persist in DB
                if lead:
                    lead.reply_body = cleaned_msg or body_content
                    lead.reply_intent = intent
                    if not lead.reply_received_at:
                        lead.reply_received_at = now_utc
                    lead.ai_reply_sent = reply_text
                    lead.ai_reply_sent_at = now_utc
                    lead.status = "replied"
                    from Backend.crud import _calculate_engagement
                    lead.engagement_score = _calculate_engagement(lead)
                    db.commit()
                    db.refresh(lead)
                elif lead_from_sheet is not None:
                    import uuid
                    from utils.token import generate_token
                    new_entry = CampaignLog(
                        campaign_name=os.getenv("CAMPAIGN_NAME", "campaign"),
                        lead_id=str(lead_from_sheet.get("lead_id") or f"lead_{uuid.uuid4().hex[:8]}"),
                        email=sender_addr,
                        name=effective_name or "",
                        company=company_name or "",
                        token=generate_token(),
                        tracking_link=BOOKING_URL,
                        subject=subject,
                        reply_body=cleaned_msg or body_content,
                        reply_intent=intent,
                        reply_received_at=now_utc,
                        ai_reply_sent=reply_text,
                        ai_reply_sent_at=now_utc,
                        status="replied",
                    )
                    db.add(new_entry)
                    db.commit()

                # Sync to customer_replies.xlsx
                try:
                    log_reply_to_excel(
                        email=sender_addr,
                        name=effective_name or "Lead",
                        company=company_name or "",
                        reply_intent=intent,
                        customer_reply=cleaned_msg or body_content,
                        ai_response_sent=reply_text,
                        reply_received_at=fmt_received_date or now_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
                        ai_reply_sent_at=now_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    )
                except Exception as ex:
                    print(f"[Warning] Could not log reply to customer_replies.xlsx: {ex}")

                results["details"].append({
                    "email": sender_addr,
                    "name": effective_name,
                    "subject": subject,
                    "intent": intent,
                    "chunks_count": len(chunks_used),
                })
                print(f"[Success] Grounded AI reply for verified lead {sender_addr} ({intent}, {len(chunks_used)} KB chunks used).")
            else:
                results["failed_count"] += 1
                print(f"[Failed] Could not dispatch reply to {sender_addr}")

    finally:
        if close_db_at_end:
            db.close()

    return results


def run_monitoring_loop(interval_seconds: int = 30):
    """Runs a continuous background polling loop."""
    print(f"[Agent] AI Auto-Reply Agent active for mailbox: {MS_SENDER_EMAIL}")
    print(f"[Knowledge] Grounded in: neno_technology_knowledge_base.pdf (70 Chunks)")
    print(f"[Consultation] Microsoft Bookings Portal: {BOOKING_URL}")
    print(f"[Status] Polling interval: every {interval_seconds}s (Press Ctrl+C to stop)\n")

    try:
        while True:
            try:
                res = check_and_reply_inbox()
                if res["processed_count"] > 0 or res.get("bookings_synced", 0) > 0:
                    print(
                        f"[{datetime.now().strftime('%H:%M:%S')}] Cycle: {res['replied_count']} replied, "
                        f"{res.get('bookings_synced', 0)} bookings synced, {res['failed_count']} failed."
                    )
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Polling error: {e}")

            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("\n[Agent] AI Auto-Reply Agent stopped gracefully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Auto-Reply Agent for Nenotechnology Outlook Inbox")
    parser.add_argument("--once", action="store_true", help="Run a single scan & reply pass, then exit")
    parser.add_argument("--sync", action="store_true", help="Run full inbox sync & backfill on existing messages")
    parser.add_argument("--interval", type=int, default=30, help="Polling interval in seconds (default: 30)")
    args = parser.parse_args()

    if args.sync:
        print(f"[Sync] Running full inbox sync & backfill on mailbox {MS_SENDER_EMAIL}...")
        summary = check_and_reply_inbox(sync_existing=True)
        print(f"\nDone. Processed={summary['processed_count']} Replied={summary['replied_count']} BookingsSynced={summary.get('bookings_synced', 0)} Skipped={summary['skipped_count']} Failed={summary['failed_count']}")
    elif args.once:
        print(f"[Scan] Running single scan on mailbox {MS_SENDER_EMAIL}...")
        summary = check_and_reply_inbox()
        print(f"\nDone. Processed={summary['processed_count']} Replied={summary['replied_count']} BookingsSynced={summary.get('bookings_synced', 0)} Skipped={summary['skipped_count']} Failed={summary['failed_count']}")
    else:
        run_monitoring_loop(interval_seconds=args.interval)
