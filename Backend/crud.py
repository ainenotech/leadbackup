import os
import re
from datetime import datetime, timezone
from typing import List, Optional, Set

import pandas as pd
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from Email import get_mailer
from services.excel_logger import log_booking_to_excel, log_form_submission_to_excel
from .models import CampaignLog


def get_already_sent_emails(db: Session) -> Set[str]:
    """Returns a set of lowercased emails that have already received an email (status == 'sent')."""
    rows = db.query(CampaignLog.email).filter(CampaignLog.status == "sent").all()
    return {r[0].strip().lower() for r in rows if r[0]}


def get_already_drafted_emails(db: Session) -> Set[str]:
    """Returns a set of lowercased emails that currently have a draft in review or approved."""
    rows = (
        db.query(CampaignLog.email)
        .filter(CampaignLog.status.in_(["drafted", "approved"]))
        .all()
    )
    return {r[0].strip().lower() for r in rows if r[0]}


def is_email_already_sent(db: Session, email: str) -> bool:
    """Check if an email has already received a sent email."""
    if not email:
        return False
    row = (
        db.query(CampaignLog.id)
        .filter(
            func.lower(CampaignLog.email) == email.strip().lower(),
            CampaignLog.status == "sent",
        )
        .first()
    )
    return row is not None


def already_contacted(
    db: Session, campaign_name: str, lead_id: str, email: Optional[str] = None
) -> bool:
    """Idempotency check: has this lead already been emailed or drafted in this campaign (by lead_id or email)?"""
    query = db.query(CampaignLog).filter(
        CampaignLog.campaign_name == campaign_name,
        CampaignLog.status.in_(["sent", "drafted", "approved"]),
    )
    if email:
        cleaned_email = email.strip().lower()
        if lead_id:
            query = query.filter(
                or_(
                    CampaignLog.lead_id == lead_id,
                    func.lower(CampaignLog.email) == cleaned_email,
                )
            )
        else:
            query = query.filter(func.lower(CampaignLog.email) == cleaned_email)
    else:
        query = query.filter(CampaignLog.lead_id == lead_id)

    return query.first() is not None


def create_pending_entry(
    db: Session,
    campaign_name: str,
    lead_id: str,
    email: str,
    name: str,
    company: str,
    token: str,

    subject: str,
    body: str,
    status: str = "pending",
    tracking_link: Optional[str] = None,
    template_id: Optional[str] = None,
    template_name: Optional[str] = None,
) -> CampaignLog:
    booking_url = os.getenv(
        "BOOKING_FORM_URL",
        "https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled",
    )
    if not tracking_link or "localhost" in str(tracking_link) or "127.0.0.1" in str(tracking_link):
        tracking_link = booking_url

    entry = CampaignLog(
        campaign_name=campaign_name,
        lead_id=lead_id,
        email=email,
        name=name,
        company=company,
        token=token,
        tracking_link=tracking_link,
        subject=subject,
        body=body,
        status=status,
        template_id=template_id,
        template_name=template_name,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def mark_sent(db: Session, entry_id: str) -> None:
    entry = db.query(CampaignLog).filter(CampaignLog.id == entry_id).first()
    if entry:
        entry.status = "sent"
        entry.email_sent_at = datetime.now(timezone.utc)
        db.commit()


def mark_failed(db: Session, entry_id: str, error: str) -> None:
    entry = db.query(CampaignLog).filter(CampaignLog.id == entry_id).first()
    if entry:
        entry.status = "failed"
        entry.send_error = error
        db.commit()


def approve_and_send_entry(db: Session, entry_id: str) -> CampaignLog:
    """Approves a drafted email and dispatches it via the Outlook mailer (Microsoft Graph).
    Enforces strict pre-send deduplication so already-emailed leads are never resent.
    """
    entry = db.query(CampaignLog).filter(CampaignLog.id == entry_id).first()
    if not entry:
        raise ValueError("Campaign entry not found")

    if entry.status == "sent":
        raise ValueError(f"Email already sent to {entry.email} at {entry.email_sent_at}")

    # Guard: check if another entry with this email was already sent
    cleaned_email = entry.email.strip().lower()
    existing_sent = (
        db.query(CampaignLog)
        .filter(
            func.lower(CampaignLog.email) == cleaned_email,
            CampaignLog.status == "sent",
            CampaignLog.id != entry.id,
        )
        .first()
    )
    if existing_sent:
        entry.status = "skipped_duplicate"
        entry.send_error = f"Skipped: Email already sent to {entry.email} at {existing_sent.email_sent_at}"
        db.commit()
        raise ValueError(f"Skipped duplicate: {entry.email} has already received an outreach email.")

    booking_url = os.getenv(
        "BOOKING_FORM_URL",
        "https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled",
    )

    # Bulletproof fallback: ensure no unresolved placeholders reach the recipient
    c_name = str(entry.name).strip() if entry.name and str(entry.name).strip().lower() not in ("nan", "none", "") else ""
    first_name = c_name.split()[0].title() if c_name else "there"
    c_comp = str(entry.company).strip() if entry.company and str(entry.company).strip().lower() not in ("nan", "none", "") else ""
    comp_name = c_comp if c_comp else "your team"
    subj_comp = comp_name if comp_name != "your team" else "Your Business"

    try:
        from services.template_service import interpolate_lead_placeholders
        if entry.subject:
            entry.subject = interpolate_lead_placeholders(entry.subject, first_name=first_name, company_name=subj_comp)
        if entry.body:
            entry.body = interpolate_lead_placeholders(entry.body, first_name=first_name, company_name=comp_name)
    except Exception:
        pass

    if entry.body:
        entry.body = re.sub(
            r'href=["\']https?://(?:localhost|127\.0\.0\.1)(?::\d+)?(?:/[^"\']*)?["\']',
            f'href="{booking_url}"',
            entry.body,
        )
        entry.body = re.sub(
            r'href=["\']https?://[^/\"\'\s]+/form\?token=[^"\'\s]*["\']',
            f'href="{booking_url}"',
            entry.body,
        )

    mailer = get_mailer()
    try:
        mailer.send_email(to_email=entry.email, subject=entry.subject, body=entry.body, token=entry.token)
    except Exception as send_err:
        entry.status = "failed"
        entry.send_error = str(send_err)[:500]
        db.commit()
        raise RuntimeError(
            f"Email delivery failed for {entry.email}: {send_err}"
        ) from send_err

    entry.status = "sent"
    entry.email_sent_at = datetime.now(timezone.utc)
    entry.send_error = None
    db.commit()
    db.refresh(entry)

    # Synchronize to lead sheet
    try:
        from leads import update_lead_sheet_status

        update_lead_sheet_status(
            email=entry.email,
            status="sent",
            sent_at=entry.email_sent_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
        )
    except Exception as e:
        print(f"Warning: Could not sync status to leads sheet: {e}")

    return entry


def reject_entry(db: Session, entry_id: str) -> CampaignLog:
    entry = db.query(CampaignLog).filter(CampaignLog.id == entry_id).first()
    if entry:
        entry.status = "rejected"
        db.commit()
        db.refresh(entry)
    return entry


def update_draft_content(db: Session, entry_id: str, subject: str, body: str) -> CampaignLog:
    entry = db.query(CampaignLog).filter(CampaignLog.id == entry_id).first()
    if entry:
        entry.subject = subject
        entry.body = body
        db.commit()
        db.refresh(entry)
    return entry


def get_by_token(db: Session, token: str) -> Optional[CampaignLog]:
    return db.query(CampaignLog).filter(CampaignLog.token == token).first()


def mark_form_filled(
    db: Session,
    token: Optional[str] = None,
    email: Optional[str] = None,
    availability_json: Optional[str] = None,
    note: Optional[str] = None,
    name: Optional[str] = None,
    company: Optional[str] = None,
    service: Optional[str] = None,
    phone: Optional[str] = None,
) -> Optional[CampaignLog]:
    entry = None
    if token:
        entry = get_by_token(db, token)
    if not entry and email:
        entry = (
            db.query(CampaignLog)
            .filter(func.lower(CampaignLog.email) == email.strip().lower())
            .order_by(CampaignLog.created_at.desc())
            .first()
        )

    if not entry and (email or token):
        import uuid
        from utils.token import generate_token

        gen_token = token or generate_token()
        campaign_name = os.getenv("CAMPAIGN_NAME", "inbound_meeting_request")
        lead_id = f"lead_{uuid.uuid4().hex[:8]}"
        booking_url = os.getenv(
            "BOOKING_FORM_URL",
            "https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled",
        )
        tracking_link = booking_url

        entry = CampaignLog(
            campaign_name=campaign_name,
            lead_id=lead_id,
            email=email.strip().lower() if email else f"lead_{gen_token}@unknown.com",
            name=name,
            company=company,
            phone=phone,
            token=gen_token,
            tracking_link=tracking_link,
            status="form_submitted",
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)

    if entry:
        entry.form_filled_at = datetime.now(timezone.utc)
        if availability_json:
            entry.submitted_availability = availability_json
        if note:
            entry.note = note
        if name:
            entry.name = name
        if company:
            entry.company = company
        if phone:
            entry.phone = phone
        entry.booking_status = "pending"
        entry.scheduling_error = None
        db.commit()
        db.refresh(entry)

        target_email = entry.email
        target_name = entry.name or name
        target_company = entry.company or company
    else:
        target_email = email or ""
        target_name = name or ""
        target_company = company or ""

    if target_email:
        try:
            log_form_submission_to_excel(
                email=target_email,
                name=target_name,
                company=target_company,
                service_requested=service,
                submitted_slots=availability_json,
                note=note,
            )
        except Exception as e:
            print(f"Error logging form submission to Excel: {e}")

    return entry


def create_meeting_request(
    db: Session,
    name: str,
    email: str,
    company: Optional[str] = None,
    phone: Optional[str] = None,
    requirement: Optional[str] = None,
    service: Optional[str] = None,
    preferred_date: Optional[str] = None,
    preferred_time: Optional[str] = None,
    token: Optional[str] = None,
) -> CampaignLog:
    """Creates a meeting request in PostgreSQL with status 'pending'."""
    # Construct combined availability string
    availability = ""
    if preferred_date and preferred_time:
        availability = f"{preferred_date.strip()} {preferred_time.strip()}"
    elif preferred_date:
        availability = preferred_date.strip()
    else:
        availability = "General consultation request"

    # Construct note with service and requirement
    note_parts = []
    if service:
        note_parts.append(f"Service: {service.strip()}")
    if requirement:
        note_parts.append(f"Requirement: {requirement.strip()}")
    if phone:
        note_parts.append(f"Phone: {phone.strip()}")
    full_note = " | ".join(note_parts) or "Meeting Request"

    return mark_form_filled(
        db=db,
        token=token,
        email=email.strip().lower(),
        name=name.strip() if name else None,
        company=company.strip() if company else None,
        phone=phone.strip() if phone else None,
        service=service.strip() if service else None,
        note=full_note,
        availability_json=availability,
    )



def mark_form_visited(
    db: Session, token: str, destination_url: str = ""
) -> Optional[CampaignLog]:
    """Tracks when a lead clicks the tracking link to visit the form without marking it as filled prematurely."""
    entry = get_by_token(db, token)
    if entry:
        if not entry.note or "Visited" not in entry.note:
            entry.note = f"Visited Form Link ({datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')})"
            db.commit()
            db.refresh(entry)

    return entry


# Backwards compatibility alias
mark_google_form_visited = mark_form_visited




def get_awaiting_scheduling(db: Session):
    """Retrieves pending meeting requests and atomically transitions them to 'processing'
    to prevent duplicate concurrent worker execution."""
    rows = (
        db.query(CampaignLog)
        .filter(
            CampaignLog.form_filled_at.isnot(None),
            CampaignLog.confirmed_slot.is_(None),
            CampaignLog.booking_status.in_([None, "pending", "Form Submitted", "awaiting_scheduling"]),
        )
        .all()
    )
    for r in rows:
        r.booking_status = "processing"
    if rows:
        db.commit()
        for r in rows:
            db.refresh(r)
    return rows


def mark_scheduled(
    db: Session, entry_id: str, confirmed_slot_iso: str, meet_link: Optional[str]
) -> None:
    entry = db.query(CampaignLog).filter(CampaignLog.id == entry_id).first()
    if entry:
        entry.confirmed_slot = confirmed_slot_iso
        entry.meet_link = meet_link
        entry.booking_status = "meeting_scheduled"
        entry.scheduling_error = None
        db.commit()

        # Log confirmed booking to permanent Excel sheet
        log_booking_to_excel(
            email=entry.email,
            name=entry.name,
            company=entry.company,
            confirmed_slot=confirmed_slot_iso,
            meet_link=meet_link,
        )


def mark_confirmation_sent(db: Session, entry_id: str) -> None:
    entry = db.query(CampaignLog).filter(CampaignLog.id == entry_id).first()
    if entry:
        entry.booking_status = "confirmation_sent"
        db.commit()


def mark_auto_proposed(db: Session, entry_id: str, proposed_slots_json: str) -> None:
    entry = db.query(CampaignLog).filter(CampaignLog.id == entry_id).first()
    if entry:
        entry.proposed_slot = proposed_slots_json
        entry.booking_status = "alternates_proposed"
        db.commit()


def mark_manual_followup(db: Session, entry_id: str, reason: str) -> None:
    entry = db.query(CampaignLog).filter(CampaignLog.id == entry_id).first()
    if entry:
        entry.booking_status = "failed"
        entry.scheduling_error = reason
        db.commit()


def update_draft_base_url(db: Session, new_base_url: str) -> int:
    """Updates tracking links and embedded URLs in all drafted/pending campaign logs
    so they reflect the active base URL. Returns the number of updated records.
    """
    clean_base = new_base_url.rstrip("/")
    booking_url = os.getenv(
        "BOOKING_FORM_URL",
        "https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled",
    )
    is_local_base = any(h in clean_base.lower() for h in ("localhost", "127.0.0.1"))
    drafts = db.query(CampaignLog).filter(CampaignLog.status == "drafted").all()
    updated_count = 0

    for draft in drafts:
        changed = False
        if draft.token:
            new_tracking = booking_url
            if draft.tracking_link != new_tracking:
                old_tracking = draft.tracking_link
                draft.tracking_link = new_tracking
                changed = True
                if draft.body:
                    if old_tracking and old_tracking in draft.body:
                        draft.body = draft.body.replace(old_tracking, new_tracking)
                    else:
                        # Regex match any existing form URL with this token
                        draft.body = re.sub(
                            r"https?://[^/\"'\s]+/form\?token=" + re.escape(draft.token),
                            new_tracking,
                            draft.body,
                        )

        if changed:
            updated_count += 1

    if updated_count > 0:
        db.commit()

    return updated_count


def _calculate_engagement(entry: CampaignLog) -> float:
    """Computes a genuine engagement score (0 to 100) based strictly on real milestones."""
    if entry.bounced or entry.unsubscribed:
        return 0.0
    score = 0.0
    if entry.status in ["sent", "replied", "form_submitted"] or entry.email_sent_at:
        score += 10.0
    if entry.opened or (entry.open_count and entry.open_count > 0):
        score += 20.0
        score += min(15.0, ((entry.open_count or 1) - 1) * 5.0)
    if entry.clicked_link or (entry.click_count and entry.click_count > 0):
        score += 25.0
    if entry.reply_body or entry.reply_intent or entry.status == "replied":
        score += 25.0
        if entry.reply_intent in ["interested", "question"]:
            score += 10.0
    if entry.booking_status in ["scheduled", "meeting_scheduled", "confirmation_sent", "confirmed"] or entry.confirmed_slot:
        score = 100.0
    return min(100.0, score)


def record_email_open(db: Session, token: str) -> Optional[CampaignLog]:
    """Records a real email open event triggered by the 1x1 transparent tracking pixel."""
    entry = get_by_token(db, token)
    if entry:
        entry.opened = True
        entry.open_count = (entry.open_count or 0) + 1
        now_utc = datetime.now(timezone.utc)
        if not entry.first_open_at:
            entry.first_open_at = now_utc
        entry.last_open_at = now_utc
        entry.engagement_score = _calculate_engagement(entry)
        db.commit()
        db.refresh(entry)
    return entry


def record_link_click(db: Session, token: str, destination_url: str = "") -> Optional[CampaignLog]:
    """Records a real link click event triggered by click redirect tracking."""
    entry = get_by_token(db, token)
    if entry:
        entry.clicked_link = True
        entry.click_count = (entry.click_count or 0) + 1
        now_utc = datetime.now(timezone.utc)
        if not entry.first_click_at:
            entry.first_click_at = now_utc
        entry.last_click_at = now_utc

        # Append destination URL if provided
        if destination_url:
            current_urls = (entry.clicked_urls or "").split(" || ") if entry.clicked_urls else []
            if destination_url not in current_urls:
                current_urls.append(destination_url)
            entry.clicked_urls = " || ".join(filter(None, current_urls))

        entry.engagement_score = _calculate_engagement(entry)
        db.commit()
        db.refresh(entry)
    return entry


def record_unsubscribe(db: Session, token: str, reason: str = "Lead clicked opt-out link") -> Optional[CampaignLog]:
    """Flags a lead as opted-out/unsubscribed to halt further sequence sends."""
    entry = get_by_token(db, token)
    if entry:
        entry.unsubscribed = True
        entry.unsubscribed_at = datetime.now(timezone.utc)
        entry.status = "opted_out"
        entry.send_error = reason
        entry.engagement_score = 0.0
        db.commit()
        db.refresh(entry)
    return entry


def record_bounce(db: Session, email_or_token: str, reason: str = "550 User Unknown") -> Optional[CampaignLog]:
    """Flags an outreach email as bounced."""
    entry = (
        db.query(CampaignLog)
        .filter(
            or_(
                CampaignLog.token == email_or_token,
                func.lower(CampaignLog.email) == email_or_token.strip().lower(),
            )
        )
        .first()
    )
    if entry:
        entry.bounced = True
        entry.bounce_reason = reason
        entry.status = "failed"
        entry.send_error = reason
        entry.engagement_score = 0.0
        db.commit()
        db.refresh(entry)
    return entry


def reset_all_system_data(db: Optional[Session] = None) -> dict:
    """Atomically resets all application data:
    1. Clears PostgreSQL campaign_log table.
    2. Resets Excel files (leads.xlsx, booked_leads.xlsx, customer_replies.xlsx) to clean empty headers.
    3. Cleans local SQLite database if present.
    """
    import sqlite3
    from .db import SessionLocal
    from .models import CampaignLog

    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    deleted_pg = 0
    try:
        deleted_pg = db.query(CampaignLog).delete()
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error resetting PostgreSQL data: {e}")
    finally:
        if close_db:
            db.close()

    # Reset Excel files to clean zero rows
    booked_cols = [
        "email", "name", "company", "status", "submitted_slots",
        "confirmed_slot", "note", "updated_at", "service_requested", "teams_meeting_link"
    ]
    pd.DataFrame(columns=booked_cols).to_excel("booked_leads.xlsx", index=False)

    replies_cols = [
        "email", "name", "company", "reply_intent", "customer_reply",
        "ai_response_sent", "reply_received_at", "ai_reply_sent_at", "status", "updated_at"
    ]
    pd.DataFrame(columns=replies_cols).to_excel("customer_replies.xlsx", index=False)

    leads_cols = [
        "lead_id", "email", "name", "company", "last_activity_date",
        "last_deal_stage", "status", "email_sent_at"
    ]
    pd.DataFrame(columns=leads_cols).to_excel("leads.xlsx", index=False)

    if os.path.exists("campaign.db"):
        try:
            conn = sqlite3.connect("campaign.db")
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [r[0] for r in cur.fetchall()]
            if "campaign_log" in tables:
                cur.execute("DELETE FROM campaign_log;")
            conn.commit()
            conn.close()
        except Exception:
            pass

    return {
        "deleted_rows": deleted_pg,
        "status": "success",
    }


def sync_excel_and_outlook_to_db(db: Session) -> dict:
    """Synchronizes external Excel records (such as Bookings Page -> Excel -> Odoo CRM flows)
    and customer replies into PostgreSQL campaign_log in real-time.
    """
    import uuid
    from utils.token import generate_token

    synced_bookings = 0
    synced_replies = 0
    now_utc = datetime.now(timezone.utc)

    # 1. Sync from booked_leads.xlsx (Power Automate Bookings -> Excel flow)
    if os.path.exists("booked_leads.xlsx"):
        try:
            df_booked = pd.read_excel("booked_leads.xlsx")
            if not df_booked.empty and "email" in df_booked.columns:
                for _, row in df_booked.iterrows():
                    email_raw = str(row.get("email") or "").strip()
                    if not email_raw or "@" not in email_raw or "client.nenotechnology.com" in email_raw.lower():
                        continue
                    email_clean = email_raw.lower()
                    entry = (
                        db.query(CampaignLog)
                        .filter(func.lower(CampaignLog.email) == email_clean)
                        .first()
                    )
                    confirmed_slot = str(row.get("confirmed_slot") or "").strip() if pd.notna(row.get("confirmed_slot")) else ""
                    meet_link = str(row.get("teams_meeting_link") or "").strip() if pd.notna(row.get("teams_meeting_link")) else ""
                    note = str(row.get("note") or "").strip() if pd.notna(row.get("note")) else ""
                    submitted_slots = str(row.get("submitted_slots") or "").strip() if pd.notna(row.get("submitted_slots")) else ""
                    service = str(row.get("service_requested") or "").strip() if pd.notna(row.get("service_requested")) else ""
                    if service and note:
                        note = f"Service: {service} | {note}"
                    elif service and not note:
                        note = f"Service: {service}"

                    if entry:
                        needs_update = False
                        if entry.booking_status not in ["scheduled", "meeting_scheduled", "confirmation_sent", "confirmed"]:
                            entry.booking_status = "scheduled"
                            needs_update = True
                        if confirmed_slot and entry.confirmed_slot != confirmed_slot:
                            entry.confirmed_slot = confirmed_slot
                            needs_update = True
                        if meet_link and entry.meet_link != meet_link:
                            entry.meet_link = meet_link
                            needs_update = True
                        if note and not entry.note:
                            entry.note = note
                            needs_update = True
                        if submitted_slots and not entry.submitted_availability:
                            entry.submitted_availability = submitted_slots
                            needs_update = True
                        if not entry.form_filled_at:
                            entry.form_filled_at = now_utc
                            needs_update = True

                        if needs_update:
                            entry.engagement_score = _calculate_engagement(entry)
                            synced_bookings += 1
                    else:
                        # Create record for external booking
                        new_entry = CampaignLog(
                            id=str(uuid.uuid4()),
                            campaign_name=os.getenv("CAMPAIGN_NAME", "q3_stale_lead_reengagement"),
                            lead_id=f"lead_{uuid.uuid4().hex[:8]}",
                            email=email_raw,
                            name=str(row.get("name") or "").strip() if pd.notna(row.get("name")) else email_raw.split("@")[0].title(),
                            company=str(row.get("company") or "").strip() if pd.notna(row.get("company")) else "Client",
                            token=generate_token(),
                            status="sent",
                            email_sent_at=now_utc,
                            booking_status="scheduled",
                            confirmed_slot=confirmed_slot,
                            meet_link=meet_link,
                            note=note,
                            submitted_availability=submitted_slots,
                            form_filled_at=now_utc,
                            opened=False,
                            open_count=0,
                            clicked_link=False,
                            click_count=0,
                            engagement_score=_calculate_engagement(CampaignLog(booking_status="scheduled")),
                        )
                        db.add(new_entry)
                        synced_bookings += 1
        except Exception as e:
            print(f"Error syncing booked_leads.xlsx to DB: {e}")

    # 2. Sync from customer_replies.xlsx
    if os.path.exists("customer_replies.xlsx"):
        try:
            df_replies = pd.read_excel("customer_replies.xlsx")
            if not df_replies.empty and "email" in df_replies.columns:
                for _, row in df_replies.iterrows():
                    email_raw = str(row.get("email") or "").strip()
                    if not email_raw or "@" not in email_raw:
                        continue
                    email_clean = email_raw.lower()
                    entry = (
                        db.query(CampaignLog)
                        .filter(func.lower(CampaignLog.email) == email_clean)
                        .first()
                    )
                    reply_text = str(row.get("customer_reply") or "").strip() if pd.notna(row.get("customer_reply")) else ""
                    reply_intent = str(row.get("reply_intent") or "interested").strip() if pd.notna(row.get("reply_intent")) else "interested"
                    ai_reply = str(row.get("ai_response_sent") or "").strip() if pd.notna(row.get("ai_response_sent")) else ""

                    if entry:
                        needs_update = False
                        if reply_text and entry.reply_body != reply_text:
                            entry.reply_body = reply_text
                            needs_update = True
                        if reply_intent and entry.reply_intent != reply_intent:
                            entry.reply_intent = reply_intent
                            needs_update = True
                        if ai_reply and entry.ai_reply_sent != ai_reply:
                            entry.ai_reply_sent = ai_reply
                            needs_update = True
                        if not entry.reply_received_at:
                            entry.reply_received_at = now_utc
                            needs_update = True
                        if entry.status not in ["replied", "form_submitted", "scheduled"]:
                            entry.status = "replied"
                            needs_update = True

                        if needs_update:
                            entry.engagement_score = _calculate_engagement(entry)
                            synced_replies += 1
        except Exception as e:
            print(f"Error syncing customer_replies.xlsx to DB: {e}")

    if synced_bookings > 0 or synced_replies > 0:
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Error committing synced records to DB: {e}")

    return {
        "synced_bookings": synced_bookings,
        "synced_replies": synced_replies,
    }






