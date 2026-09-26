import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import pandas as pd
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from Email import get_mailer
from services.excel_logger import log_booking_to_excel, log_form_submission_to_excel
from .models import CampaignLog, KnowledgeDocument, ProcessedReply


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

    # Check and link master lead if already known
    m_id = None
    try:
        from Backend.master_db_models import MasterLead
        from services.master_db_service import normalize_email
        norm_em = normalize_email(email)
        m_lead = db.query(MasterLead).filter(MasterLead.email_normalized == norm_em).first()
        if m_lead:
            m_id = m_lead.id
    except Exception:
        pass

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
        master_lead_id=m_id,
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

    # Guard: check if this exact template was already sent to this email (allows multi-template outreach to the same lead)
    cleaned_email = entry.email.strip().lower()
    current_tid = str(getattr(entry, "template_id", "") or "").strip().lower()
    current_tname = str(getattr(entry, "template_name", "") or "").strip().lower()

    existing_sent_query = db.query(CampaignLog).filter(
        func.lower(CampaignLog.email) == cleaned_email,
        CampaignLog.status == "sent",
        CampaignLog.id != entry.id,
    )
    if current_tid or current_tname:
        conds = []
        if current_tid:
            conds.append(func.lower(CampaignLog.template_id) == current_tid)
        if current_tname:
            conds.append(func.lower(CampaignLog.template_name) == current_tname)
        existing_sent_query = existing_sent_query.filter(or_(*conds))

    existing_sent_same_tpl = existing_sent_query.first()
    if existing_sent_same_tpl:
        entry.status = "skipped_duplicate"
        entry.send_error = f"Skipped: Template '{entry.template_name or current_tid}' already sent to {entry.email} at {existing_sent_same_tpl.email_sent_at}"
        db.commit()
        raise ValueError(f"Skipped duplicate: {entry.email} has already received this template.")

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
        mailer.send_email(
            to_email=str(entry.email),
            subject=str(entry.subject or ""),
            body=str(entry.body or ""),
            token=str(entry.token) if entry.token else None,
        )
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

    # Synchronize to Master DB
    try:
        from services.master_db_service import sync_campaign_entry_to_master_db
        sync_campaign_entry_to_master_db(db, entry)
    except Exception as e:
        print(f"Warning: Could not sync to Master DB: {e}")

    return entry


def reject_entry(db: Session, entry_id: str) -> bool:
    """Discards an un-sent draft entry from CampaignLog so it does not inflate pipeline or template metrics."""
    entry = db.query(CampaignLog).filter(CampaignLog.id == entry_id).first()
    if not entry:
        return False
    email = entry.email.strip().lower() if entry.email else None
    
    # If it was never dispatched, completely remove it from the campaign log
    if entry.email_sent_at is None:
        db.delete(entry)
        db.commit()
    else:
        entry.status = "rejected"
        db.commit()

    if email:
        try:
            from leads import update_lead_sheet_status
            already_sent = is_email_already_sent(db, email)
            new_status = "sent" if already_sent else "new"
            update_lead_sheet_status(email=email, status=new_status)
        except Exception as e:
            print(f"Warning: Could not sync status to leads sheet: {e}")
    return True


def bulk_reject_entries(db: Session, entry_ids: List[str]) -> int:
    """Rejects/discards multiple un-sent draft entries from CampaignLog in a single transaction
    so they do not pollute Total Leads or Template Assigned metrics, and syncs lead sheet status.
    """
    if not entry_ids:
        return 0

    entries = db.query(CampaignLog).filter(CampaignLog.id.in_(entry_ids)).all()
    if not entries:
        return 0

    emails = []
    deleted_count = 0
    for entry in entries:
        if entry.email:
            emails.append(entry.email.strip().lower())
        if entry.email_sent_at is None:
            db.delete(entry)
            deleted_count += 1
        else:
            entry.status = "rejected"

    db.commit()

    if emails:
        try:
            from leads import bulk_update_lead_sheet_status
            sent_emails = get_already_sent_emails(db)
            bulk_updates = {}
            for em in emails:
                bulk_updates[em] = {"status": "sent" if em in sent_emails else "new"}
            bulk_update_lead_sheet_status(bulk_updates)
        except Exception as e:
            print(f"Warning: Could not sync bulk status to leads sheet: {e}")

    return len(entries)


def purge_orphan_rejected_drafts(db: Session) -> int:
    """Removes historical un-sent records with status 'rejected' to clean up pipeline and template metrics."""
    orphans = (
        db.query(CampaignLog)
        .filter(CampaignLog.status == "rejected", CampaignLog.email_sent_at.is_(None))
        .all()
    )
    count = len(orphans)
    if count > 0:
        for entry in orphans:
            db.delete(entry)
        db.commit()
    return count


def bulk_approve_and_send_entries(
    entry_ids: List[str],
    template_id: Optional[int] = None,
    max_workers: int = 2,
    force_resend: bool = False,
    progress_callback: Optional[Callable[[int, int, str, str], None]] = None,
) -> dict:
    """Dispatches multiple drafts concurrently with connection-pooled Microsoft Graph calls,
    isolated main-thread database updates, and single-pass lead sheet synchronization.
    Preserves reviewed draft subjects and bodies rather than forcefully overwriting them.
    """
    if not entry_ids:
        return {"approved_count": 0, "skipped_count": 0, "failed_count": 0, "error_details": []}

    booking_url = os.getenv(
        "BOOKING_FORM_URL",
        "https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled",
    )

    import time
    from Backend.db import SessionLocal
    from Email.draft_options import get_draft_template_option
    from services.template_service import interpolate_lead_placeholders

    # Phase 1: Pre-flight check & draft preparation on Main Thread (Thread-safe)
    db = SessionLocal()
    tasks_to_send = []
    skipped_count = 0
    error_details = []
    lead_sheet_updates = {}
    completed_counter = 0
    total_count = len(entry_ids)

    try:
        entries = db.query(CampaignLog).filter(CampaignLog.id.in_(entry_ids)).all()
        if not entries:
            return {"approved_count": 0, "skipped_count": 0, "failed_count": 0, "error_details": ["No matching entries found."]}

        entry_map = {e.id: e for e in entries}

        # Query emails and templates that have already been sent to prevent sending the same template twice (unless force_resend is True)
        all_emails = [e.email.strip().lower() for e in entries if e.email]
        sent_template_set = set()
        if not force_resend:
            already_sent_rows = (
                db.query(CampaignLog.email, CampaignLog.template_id, CampaignLog.template_name)
                .filter(
                    func.lower(CampaignLog.email).in_(all_emails),
                    CampaignLog.status == "sent",
                )
                .all()
            )
            for r in already_sent_rows:
                em = r[0].strip().lower()
                if r[1]:
                    sent_template_set.add((em, str(r[1]).strip().lower()))
                if r[2]:
                    sent_template_set.add((em, str(r[2]).strip().lower()))

        seen_in_batch = set()
        for eid in entry_ids:
            entry = entry_map.get(eid)
            if not entry or not entry.email:
                continue

            cleaned_email = entry.email.strip().lower()
            tid_key = str(entry.template_id or entry.template_name or "").strip().lower()
            batch_key = (cleaned_email, tid_key)

            # Check if this exact template was already sent to this email or duplicated in current batch
            if not force_resend and ((cleaned_email, tid_key) in sent_template_set or (tid_key and batch_key in seen_in_batch)):
                entry.status = "skipped_duplicate"
                entry.send_error = f"Skipped: Template '{entry.template_name or tid_key or 'outreach'}' already sent to {entry.email}"
                skipped_count += 1
                lead_sheet_updates[cleaned_email] = {"status": "skipped_duplicate"}
                completed_counter += 1
                if progress_callback:
                    try:
                        progress_callback(completed_counter, total_count, entry.email, "skipped")
                    except Exception:
                        pass
                continue

            if tid_key:
                seen_in_batch.add(batch_key)

            # PRESERVE DRAFT CONTENT: Use reviewed draft subject and body if available!
            has_existing_content = bool(entry.subject and entry.subject.strip() and entry.body and entry.body.strip())
            if has_existing_content:
                curr_s = entry.subject.strip()
                curr_b = entry.body.strip()
            else:
                # Fallback only when draft subject or body is completely empty
                fallback_opt = template_id if template_id in (1, 2, 3) else 1
                curr_s, curr_b = get_draft_template_option(
                    fallback_opt, entry.name, entry.company, booking_url
                )

            curr_s = curr_s.replace("\ufffd", "-").replace("—", "-").strip()

            c_name = str(entry.name).strip() if entry.name and str(entry.name).strip().lower() not in ("nan", "none", "") else ""
            first_name = c_name.split()[0].title() if c_name else "there"
            c_comp = str(entry.company).strip() if entry.company and str(entry.company).strip().lower() not in ("nan", "none", "") else ""
            comp_name = c_comp if c_comp else "your team"
            subj_comp = comp_name if comp_name != "your team" else "Your Business"

            try:
                if curr_s and ("{first_name}" in curr_s or "{company_name}" in curr_s):
                    curr_s = interpolate_lead_placeholders(curr_s, first_name=first_name, company_name=subj_comp)
                if curr_b and ("{first_name}" in curr_b or "{company_name}" in curr_b):
                    curr_b = interpolate_lead_placeholders(curr_b, first_name=first_name, company_name=comp_name)
            except Exception:
                pass

            if curr_b:
                curr_b = re.sub(
                    r'href=["\']https?://(?:localhost|127\.0\.0\.1)(?::\d+)?(?:/[^"\']*)?["\']',
                    f'href="{booking_url}"',
                    curr_b,
                )
                curr_b = re.sub(
                    r'href=["\']https?://[^/\"\'\s]+/form\?token=[^"\'\s]*["\']',
                    f'href="{booking_url}"',
                    curr_b,
                )

            entry.subject = curr_s
            entry.body = curr_b
            tasks_to_send.append({
                "id": entry.id,
                "email": str(entry.email or ""),
                "subject": curr_s,
                "body": curr_b,
                "token": str(entry.token) if entry.token else None,
            })

        db.commit()
    finally:
        db.close()

    if not tasks_to_send:
        if lead_sheet_updates:
            try:
                from leads import bulk_update_lead_sheet_status
                bulk_update_lead_sheet_status(lead_sheet_updates)
            except Exception:
                pass
        return {"approved_count": 0, "skipped_count": skipped_count, "failed_count": 0, "error_details": error_details}

    # Phase 2: Controlled Worker Dispatch (Only Microsoft Graph Network calls!)
    mailer = get_mailer()

    def _worker_send(task: Dict[str, Any]) -> Tuple[Any, Any, bool, Optional[str]]:
        try:
            # Space out requests slightly (300ms) to respect Exchange Online burst rates
            time.sleep(0.3)
            mailer.send_email(
                to_email=str(task.get("email") or ""),
                subject=str(task.get("subject") or ""),
                body=str(task.get("body") or ""),
                token=task.get("token"),
            )
            return (task["id"], task["email"], True, None)
        except Exception as e:
            return (task["id"], task["email"], False, str(e))

    send_results = []
    # Maximum 3 concurrent workers to respect Exchange Online single-mailbox connection limits
    worker_limit = max(1, min(max_workers, len(tasks_to_send), 3))
    with ThreadPoolExecutor(max_workers=worker_limit) as executor:
        future_map = {executor.submit(_worker_send, t): t for t in tasks_to_send}
        for future in as_completed(future_map):
            res = future.result()
            send_results.append(res)
            completed_counter += 1
            entry_id, email, success, err = res
            status_label = "sent" if success else "failed"
            if progress_callback:
                try:
                    progress_callback(completed_counter, total_count, email, status_label)
                except Exception:
                    pass

    # Phase 3: Main Thread Batch DB Persistence
    approved_count = 0
    now_utc = datetime.now(timezone.utc)
    now_str = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")

    db = SessionLocal()
    try:
        entries = db.query(CampaignLog).filter(CampaignLog.id.in_([r[0] for r in send_results])).all()
        emap = {e.id: e for e in entries}

        for entry_id, email, success, err in send_results:
            ent = emap.get(entry_id)
            if not ent:
                continue

            clean_em = email.strip().lower()
            if success:
                ent.status = "sent"
                ent.email_sent_at = now_utc
                ent.send_error = None
                approved_count += 1
                lead_sheet_updates[clean_em] = {"status": "sent", "sent_at": now_str}
            else:
                ent.status = "failed"
                ent.send_error = (err or "Unknown dispatch error")[:500]
                error_details.append(f"{email}: {err}")
                lead_sheet_updates[clean_em] = {"status": "failed"}

        db.commit()

        # Synchronize successfully sent entries to Master DB
        try:
            from services.master_db_service import sync_campaign_entry_to_master_db
            for entry_id, email, success, err in send_results:
                if success:
                    ent = emap.get(entry_id)
                    if ent:
                        sync_campaign_entry_to_master_db(db, ent)
        except Exception as _sync_err:
            print(f"[bulk dispatch notice] Master DB sync note: {_sync_err}")
    finally:
        db.close()

    # Phase 4: Single-pass Lead Sheet Synchronization
    if lead_sheet_updates:
        try:
            from leads import bulk_update_lead_sheet_status
            bulk_update_lead_sheet_status(lead_sheet_updates)
        except Exception as e:
            print(f"Warning: Could not sync batch to leads sheet: {e}")

    return {
        "approved_count": approved_count,
        "skipped_count": skipped_count,
        "failed_count": len(error_details),
        "error_details": error_details,
    }


def update_draft_content(
    db: Session,
    entry_id: str,
    subject: str,
    body: str,
    template_id: Optional[str] = None,
    template_name: Optional[str] = None,
) -> CampaignLog:
    entry = db.query(CampaignLog).filter(CampaignLog.id == entry_id).first()
    if entry:
        entry.subject = subject
        entry.body = body
        if template_id:
            entry.template_id = template_id
        if template_name:
            entry.template_name = template_name
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

        try:
            from services.master_db_service import sync_campaign_entry_to_master_db
            sync_campaign_entry_to_master_db(db, entry)
        except Exception:
            pass


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
        try:
            from services.master_db_service import sync_campaign_entry_to_master_db
            sync_campaign_entry_to_master_db(db, entry)
        except Exception:
            pass
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
        try:
            from services.master_db_service import sync_campaign_entry_to_master_db
            sync_campaign_entry_to_master_db(db, entry)
        except Exception:
            pass
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
        try:
            from services.master_db_service import sync_campaign_entry_to_master_db
            sync_campaign_entry_to_master_db(db, entry)
        except Exception:
            pass
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
        try:
            from services.master_db_service import sync_campaign_entry_to_master_db
            sync_campaign_entry_to_master_db(db, entry)
        except Exception:
            pass
    return entry


def reset_all_system_data(db: Optional[Session] = None) -> dict:
    """Atomically resets all application data:
    1. Clears PostgreSQL campaign_log, knowledge_documents, and processed_replies tables.
    2. Resets Excel files (leads.xlsx, booked_leads.xlsx, customer_replies.xlsx) to clean empty headers.
    3. Cleans local SQLite database tables if present.
    """
    import sqlite3
    from .db import SessionLocal
    from .models import CampaignLog, KnowledgeDocument, ProcessedReply

    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    deleted_pg = 0
    deleted_kb = 0
    deleted_pr = 0
    try:
        deleted_pg = db.query(CampaignLog).delete()
        deleted_kb = db.query(KnowledgeDocument).delete()
        deleted_pr = db.query(ProcessedReply).delete()
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
            for tbl in ["campaign_log", "knowledge_documents", "processed_replies"]:
                if tbl in tables:
                    cur.execute(f"DELETE FROM {tbl};")
            conn.commit()
            conn.close()
        except Exception:
            pass

    return {
        "deleted_campaign_logs": deleted_pg,
        "deleted_knowledge_docs": deleted_kb,
        "deleted_processed_replies": deleted_pr,
        "status": "success",
    }


_LAST_SYNC_BOOKED_MTIME = 0.0
_LAST_SYNC_REPLIES_MTIME = 0.0


def sync_excel_and_outlook_to_db(db: Session, force: bool = False) -> dict:
    """Synchronizes external Excel records (such as Bookings Page -> Excel -> Odoo CRM flows)
    and customer replies into PostgreSQL campaign_log in real-time with high-performance batching.
    """
    global _LAST_SYNC_BOOKED_MTIME, _LAST_SYNC_REPLIES_MTIME
    import uuid
    from utils.token import generate_token

    synced_bookings = 0
    synced_replies = 0
    now_utc = datetime.now(timezone.utc)

    booked_path = "booked_leads.xlsx"
    replies_path = "customer_replies.xlsx"

    booked_mtime = os.path.getmtime(booked_path) if os.path.exists(booked_path) else 0.0
    replies_mtime = os.path.getmtime(replies_path) if os.path.exists(replies_path) else 0.0

    # Short-circuit if files have not changed on disk and not forced
    if not force and booked_mtime == _LAST_SYNC_BOOKED_MTIME and replies_mtime == _LAST_SYNC_REPLIES_MTIME:
        return {"synced_bookings": 0, "synced_replies": 0}

    # 1. Sync from booked_leads.xlsx (Power Automate Bookings -> Excel flow)
    if os.path.exists(booked_path) and (force or booked_mtime != _LAST_SYNC_BOOKED_MTIME):
        try:
            df_booked = pd.read_excel(booked_path)
            if not df_booked.empty and "email" in df_booked.columns:
                valid_rows = []
                valid_emails = set()
                for _, row in df_booked.iterrows():
                    email_raw = str(row.get("email") or "").strip()
                    if not email_raw or "@" not in email_raw or "client.nenotechnology.com" in email_raw.lower():
                        continue
                    clean_em = email_raw.lower()
                    valid_rows.append((clean_em, email_raw, row))
                    valid_emails.add(clean_em)

                # Batch query existing entries in 1 network call
                existing_map = {}
                if valid_emails:
                    found = db.query(CampaignLog).filter(func.lower(CampaignLog.email).in_(list(valid_emails))).all()
                    for f in found:
                        if f.email:
                            existing_map[f.email.strip().lower()] = f

                for email_clean, email_raw, row in valid_rows:
                    entry = existing_map.get(email_clean)
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
                        existing_map[email_clean] = new_entry
                        synced_bookings += 1
            _LAST_SYNC_BOOKED_MTIME = booked_mtime
        except Exception as e:
            print(f"Error syncing booked_leads.xlsx to DB: {e}")

    # 2. Sync from customer_replies.xlsx
    if os.path.exists(replies_path) and (force or replies_mtime != _LAST_SYNC_REPLIES_MTIME):
        try:
            df_replies = pd.read_excel(replies_path)
            if not df_replies.empty and "email" in df_replies.columns:
                valid_reply_rows = []
                valid_reply_emails = set()
                for _, row in df_replies.iterrows():
                    email_raw = str(row.get("email") or "").strip()
                    if not email_raw or "@" not in email_raw:
                        continue
                    clean_em = email_raw.lower()
                    valid_reply_rows.append((clean_em, email_raw, row))
                    valid_reply_emails.add(clean_em)

                # Batch query existing entries in 1 network call
                existing_reply_map = {}
                if valid_reply_emails:
                    found = db.query(CampaignLog).filter(func.lower(CampaignLog.email).in_(list(valid_reply_emails))).all()
                    for f in found:
                        if f.email:
                            existing_reply_map[f.email.strip().lower()] = f

                for email_clean, email_raw, row in valid_reply_rows:
                    entry = existing_reply_map.get(email_clean)
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
            _LAST_SYNC_REPLIES_MTIME = replies_mtime
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






