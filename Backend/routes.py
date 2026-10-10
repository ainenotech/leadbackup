import os
import re
import json
import base64
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

import pandas as pd
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query, Response
from fastapi.responses import FileResponse, JSONResponse

from .db import SessionLocal
from .models import CampaignLog, KnowledgeDocument
from .crud import (
    approve_and_send_entry,
    create_pending_entry,
    get_already_drafted_emails,
    get_already_sent_emails,
    is_email_already_sent,
    mark_form_filled,
    reject_entry,
    update_draft_content,
    reset_all_system_data,
    sync_excel_and_outlook_to_db,
)
from services.analytics_service import build_comprehensive_analytics, FEATURE_DEFINITIONS
from services.template_service import (
    load_all_templates,
    get_template_by_id,
    render_template,
    interpolate_lead_placeholders,
    compute_template_analytics,
)
from services.rag import (
    get_knowledge_base_summary,
    ingest_file_content,
    delete_document,
    list_documents,
    retrieve_relevant_chunks,
)
from reply_worker import ReplyDaemonManager, check_and_reply_inbox
from leads import detect_lead_status_in_dataframe
from services.excel_logger import DEFAULT_BOOKED_EXCEL, DEFAULT_REPLIES_EXCEL
from utils.text_cleaner import extract_text_from_ai_message
from utils.token import generate_token

router = APIRouter(prefix="/api")


# ── Helper: Safe Serialization of Logs ──
def _serialize_log(r: CampaignLog) -> dict:
    return {
        "id": r.id,
        "campaign": r.campaign_name or "",
        "lead_id": r.lead_id or "",
        "email": r.email or "",
        "name": r.name or "",
        "company": r.company or "",
        "phone": getattr(r, "phone", "") or "",
        "status": r.status or "pending",
        "subject": r.subject or "",
        "body": r.body or "",
        "email_sent_at": r.email_sent_at.isoformat() if r.email_sent_at else None,
        "send_error": r.send_error or "",
        "opened": bool(getattr(r, "opened", False)),
        "open_count": getattr(r, "open_count", 0) or 0,
        "first_open_at": r.first_open_at.isoformat() if getattr(r, "first_open_at", None) else None,
        "last_open_at": r.last_open_at.isoformat() if getattr(r, "last_open_at", None) else None,
        "clicked_link": bool(getattr(r, "clicked_link", False)),
        "click_count": getattr(r, "click_count", 0) or 0,
        "first_click_at": r.first_click_at.isoformat() if getattr(r, "first_click_at", None) else None,
        "last_click_at": r.last_click_at.isoformat() if getattr(r, "last_click_at", None) else None,
        "clicked_urls": getattr(r, "clicked_urls", "") or "",
        "unsubscribed": bool(getattr(r, "unsubscribed", False)),
        "unsubscribed_at": r.unsubscribed_at.isoformat() if getattr(r, "unsubscribed_at", None) else None,
        "bounced": bool(getattr(r, "bounced", False)),
        "bounce_reason": getattr(r, "bounce_reason", "") or "",
        "engagement_score": float(getattr(r, "engagement_score", 0.0) or 0.0),
        "form_filled_at": r.form_filled_at.isoformat() if r.form_filled_at else None,
        "submitted_availability": r.submitted_availability or "",
        "note": r.note or "",
        "reply_body": r.reply_body or "",
        "reply_intent": r.reply_intent or "",
        "reply_received_at": r.reply_received_at.isoformat() if r.reply_received_at else None,
        "ai_reply_sent": r.ai_reply_sent or "",
        "ai_reply_sent_at": r.ai_reply_sent_at.isoformat() if r.ai_reply_sent_at else None,
        "proposed_slot": r.proposed_slot or "",
        "confirmed_slot": r.confirmed_slot or "",
        "meet_link": r.meet_link or "",
        "booking_status": r.booking_status or "",
        "token": r.token or "",
        "tracking_link": r.tracking_link or "",
        "template_id": getattr(r, "template_id", "") or "",
        "template_name": getattr(r, "template_name", "") or "",
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def _get_logs_dataframe(db) -> pd.DataFrame:
    rows = db.query(CampaignLog).order_by(CampaignLog.created_at.desc()).all()
    data = []
    for r in rows:
        data.append({
            "id": r.id,
            "campaign": r.campaign_name or "",
            "lead_id": r.lead_id or "",
            "email": r.email or "",
            "name": r.name or "",
            "company": r.company or "",
            "phone": getattr(r, "phone", "") or "",
            "status": r.status or "pending",
            "subject": r.subject or "",
            "body": r.body or "",
            "email_sent_at": r.email_sent_at,
            "send_error": r.send_error or "",
            "opened": bool(getattr(r, "opened", False)),
            "open_count": int(getattr(r, "open_count", 0) or 0),
            "first_open_at": getattr(r, "first_open_at", None),
            "last_open_at": getattr(r, "last_open_at", None),
            "clicked_link": bool(getattr(r, "clicked_link", False)),
            "click_count": int(getattr(r, "click_count", 0) or 0),
            "first_click_at": getattr(r, "first_click_at", None),
            "last_click_at": getattr(r, "last_click_at", None),
            "clicked_urls": getattr(r, "clicked_urls", "") or "",
            "unsubscribed": bool(getattr(r, "unsubscribed", False)),
            "unsubscribed_at": getattr(r, "unsubscribed_at", None),
            "bounced": bool(getattr(r, "bounced", False)),
            "bounce_reason": getattr(r, "bounce_reason", "") or "",
            "engagement_score": float(getattr(r, "engagement_score", 0.0) or 0.0),
            "form_filled_at": r.form_filled_at,
            "submitted_availability": r.submitted_availability or "",
            "note": r.note or "",
            "reply_body": r.reply_body or "",
            "reply_intent": r.reply_intent or "",
            "sentiment": r.reply_intent or "",
            "reply_received_at": r.reply_received_at,
            "ai_reply_sent": r.ai_reply_sent or "",
            "ai_reply_sent_at": r.ai_reply_sent_at,
            "proposed_slot": r.proposed_slot or "",
            "confirmed_slot": r.confirmed_slot or "",
            "meet_link": r.meet_link or "",
            "booking_status": r.booking_status or "",
            "token": r.token or "",
            "tracking_link": r.tracking_link or "",
            "template_id": getattr(r, "template_id", "") or "",
            "template_name": getattr(r, "template_name", "") or "",
            "created_at": r.created_at,
        })
    return pd.DataFrame(data) if data else pd.DataFrame()


# ── 1. Pipeline Overview Stats ──
@router.get("/overview/stats")
def get_overview_stats():
    db = SessionLocal()
    try:
        df = _get_logs_dataframe(db)
        if df.empty:
            return {
                "total_leads": 0,
                "drafted_leads": 0,
                "sent_leads": 0,
                "replied_leads": 0,
                "forms_filled": 0,
                "scheduled_leads": 0,
                "draft_pct": 0,
                "sent_pct": 0,
                "reply_pct": 0,
                "form_pct": 0,
                "booked_pct": 0,
            }
        
        total_leads = len(df)
        drafted_leads = int((df["status"] == "drafted").sum())
        sent_leads = int((df["status"] == "sent").sum())
        replied_leads = int(df["reply_received_at"].notna().sum())
        forms_filled = int(df["form_filled_at"].notna().sum())
        scheduled_leads = int(df["booking_status"].isin(["scheduled", "meeting_scheduled", "confirmation_sent", "confirmed"]).sum())

        draft_pct = round((drafted_leads / total_leads * 100) if total_leads else 0)
        sent_pct = round((sent_leads / total_leads * 100) if total_leads else 0)
        reply_pct = round((replied_leads / sent_leads * 100) if sent_leads else 0)
        form_pct = round((forms_filled / total_leads * 100) if total_leads else 0)
        booked_pct = round((scheduled_leads / forms_filled * 100) if forms_filled else (round(scheduled_leads / total_leads * 100) if total_leads else 0))

        return {
            "total_leads": total_leads,
            "drafted_leads": drafted_leads,
            "sent_leads": sent_leads,
            "replied_leads": replied_leads,
            "forms_filled": forms_filled,
            "scheduled_leads": scheduled_leads,
            "draft_pct": draft_pct,
            "sent_pct": sent_pct,
            "reply_pct": reply_pct,
            "form_pct": form_pct,
            "booked_pct": booked_pct,
        }
    finally:
        db.close()



# ── System Mailbox Configuration ──
@router.get("/system/mailbox")
def get_system_mailbox():
    sender_email = None
    db = SessionLocal()
    try:
        from Backend.auth_models import Organization
        org = db.query(Organization).filter(Organization.status == "active").first()
        if org and org.settings:
            sender_email = org.settings.get("sender", {}).get("sender_email") or org.settings.get("sender_email")
    except Exception:
        pass
    finally:
        db.close()

    if not sender_email:
        sender_email = os.getenv("MS_SENDER_EMAIL", "mohit@nenotechnology.us")

    contact_email = os.getenv("CONTACT_EMAIL", "sales@nenotechnology.com")
    booking_url = os.getenv(
        "BOOKING_FORM_URL",
        "https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled",
    )
    api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
    return {
        "status": "success",
        "sender_email": sender_email,
        "contact_email": contact_email,
        "booking_url": booking_url,
        "api_base_url": api_base_url,
    }


# ── 2. All Campaign Logs with Filter/Search ──
@router.get("/logs")
def get_campaign_logs(
    status: Optional[str] = None,
    campaign: Optional[str] = None,
    search: Optional[str] = None,
    limit: Optional[int] = 1000,
):
    db = SessionLocal()
    try:
        query = db.query(CampaignLog).order_by(CampaignLog.created_at.desc())
        if status and status != "All":
            query = query.filter(CampaignLog.status == status)
        if campaign and campaign != "All":
            query = query.filter(CampaignLog.campaign_name == campaign)
        
        rows = query.all()
        result = []
        s_lower = search.lower().strip() if search else None

        for r in rows:
            if s_lower:
                match = (
                    (r.name and s_lower in r.name.lower())
                    or (r.email and s_lower in r.email.lower())
                    or (r.company and s_lower in r.company.lower())
                )
                if not match:
                    continue
            result.append(_serialize_log(r))
            if limit and len(result) >= limit:
                break

        return {"total": len(result), "logs": result}
    finally:
        db.close()


# ── 3. Full 14-Feature Analytics Suite ──
@router.get("/analytics/full")
def get_full_analytics():
    db = SessionLocal()
    try:
        df = _get_logs_dataframe(db)
        analytics = build_comprehensive_analytics(df)

        # Convert leads_records to JSON-safe structure
        records_safe = []
        for rec in analytics.get("leads_records", []):
            clean_rec = dict(rec)
            for k, v in clean_rec.items():
                if isinstance(v, (datetime, pd.Timestamp)):
                    clean_rec[k] = v.isoformat()
                elif isinstance(v, (list, tuple, dict)):
                    clean_rec[k] = v
                elif pd.isna(v):
                    clean_rec[k] = None
            records_safe.append(clean_rec)
        analytics["leads_records"] = records_safe

        return {
            "status": "success",
            "features": FEATURE_DEFINITIONS,
            "data": analytics,
        }
    finally:
        db.close()


# ── 4. Master Database (with HOT/WARM/COLD Enriched Tiers) ──
def _categorize_lead_temperature(row: dict) -> dict:
    clicked = bool(row.get("clicked_link"))
    click_count = int(row.get("click_count") or 0)
    opened = bool(row.get("opened"))
    open_count = int(row.get("open_count") or 0)
    reply_body = str(row.get("reply_body") or "").strip()
    reply_intent = str(row.get("reply_intent") or "").strip()
    reply_intent_lower = reply_intent.lower()
    booking_status = str(row.get("booking_status") or "").strip().lower()
    confirmed_slot = str(row.get("confirmed_slot") or "").strip()
    meet_link = str(row.get("meet_link") or "").strip()
    status_lower = str(row.get("status") or "").strip().lower()

    has_booked = bool(
        (confirmed_slot and confirmed_slot.lower() not in ["none", "nan", "nat", ""])
        or (meet_link and meet_link.lower() not in ["none", "nan", "nat", ""])
        or booking_status in ["scheduled", "meeting_scheduled", "confirmation_sent", "confirmed"]
    )
    reply_time = row.get("reply_received_at")
    has_valid_reply_time = bool(reply_time and str(reply_time).strip().lower() not in ["none", "nan", "nat", ""])
    has_reply_body = bool(reply_body and reply_body.lower() not in ["none", "nan", "nat", "—", "-"])

    has_replied = bool(has_reply_body or status_lower == "replied" or has_valid_reply_time)
    form_time = row.get("form_filled_at")
    form_filled = bool(form_time and str(form_time).strip().lower() not in ["none", "nan", "nat", ""])

    score = 0.0
    signals = []

    if has_booked:
        score = 98.0
        signals.append("📅 Meeting Booked")
    elif form_filled:
        score = 90.0
        signals.append("📝 Form Submitted")

    if has_replied:
        score = max(score, 92.0)
        if reply_intent_lower in ["interested", "positive_acknowledgement"]:
            signals.append("💬 Replied: High Interest")
        elif reply_intent_lower == "reschedule":
            signals.append("💬 Replied: Reschedule Request")
        elif reply_intent_lower == "question":
            signals.append("💬 Replied: Asked Details")
        elif reply_intent_lower == "not_interested":
            score = 30.0
            signals.append("💬 Replied: Opt-out")
        else:
            signals.append(f"💬 Replied ({reply_intent or 'Customer Response'})")

    if clicked or click_count > 0:
        c_score = 70.0 + min(20.0, max(1, click_count) * 4.0)
        score = max(score, c_score)
        signals.append(f"🖱️ Clicked Link {max(1, click_count)}x")

    if opened or open_count > 0:
        o_count = max(1, open_count)
        if score < 70.0:
            score = max(score, 25.0 + min(35.0, o_count * 8.0))
        signals.append(f"👁️ Opened {o_count}x")

    if not signals:
        score = 10.0
        signals.append("Delivered • Unopened")

    score = min(100.0, max(0.0, score))

    if has_booked or (has_replied and reply_intent_lower != "not_interested") or (clicked and (click_count >= 2 or open_count >= 2)) or score >= 70.0:
        tier = "HOT"
        tier_display = "🔥 Hot"
    elif opened or clicked or has_replied or score >= 25.0:
        tier = "WARM"
        tier_display = "⚡ Warm"
    else:
        tier = "COLD"
        tier_display = "❄️ Cold"

    return {
        "tier": tier,
        "tier_display": tier_display,
        "score": int(round(score)),
        "activity_summary": " • ".join(signals),
    }


@router.get("/master-db")
def get_master_db():
    db = SessionLocal()
    try:
        try:
            sync_excel_and_outlook_to_db(db)
        except Exception:
            pass

        REAL_LEAD_STATUSES = {
            "sent", "replied", "delivered", "form_submitted",
            "scheduled", "meeting_booked", "booked", "opted_out",
        }

        rows = db.query(CampaignLog).order_by(CampaignLog.created_at.desc()).all()
        leads_data = []

        # Load real CRM metadata from leads.xlsx if present
        meta_cols = {}
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        leads_xlsx_path = os.path.join(root_dir, "leads.xlsx")
        if os.path.exists(leads_xlsx_path):
            try:
                leads_df = pd.read_excel(leads_xlsx_path)
                leads_df["email_clean"] = leads_df["email"].astype(str).str.strip().str.lower()
                for _, r in leads_df.iterrows():
                    em = r.get("email_clean")
                    if em and "@" in em and em not in meta_cols:
                        pos = str(r.get("Position") or r.get("job_title") or "").strip()
                        if pos.lower() in ("nan", "none", ""): pos = ""
                        last_act = str(r.get("last_activity_date") or "").replace(" 00:00:00", "").strip()
                        if last_act.lower() in ("nan", "none", ""): last_act = ""
                        loc = str(r.get("location") or "").strip()
                        if loc.lower() in ("nan", "none", ""): loc = ""
                        meta_cols[em] = {"job_title": pos, "last_activity_date": last_act, "location": loc}
            except Exception:
                pass

        seen_emails = {}
        for r in rows:
            em = (r.email or "").strip().lower()
            if not em:
                continue
            st_val = (r.status or "").strip().lower()
            if st_val not in REAL_LEAD_STATUSES and r.email_sent_at is None:
                continue

            open_c = getattr(r, "open_count", 0) or 0
            click_c = getattr(r, "click_count", 0) or 0
            has_rep = 5 if (r.reply_body and r.reply_body.strip() not in ["none", "—", "-"]) else 0
            rank = open_c + click_c * 2 + has_rep

            if em in seen_emails and seen_emails[em]["rank"] >= rank:
                continue

            row_dict = {
                "id": r.id,
                "email": em,
                "name": (r.name or "").strip(),
                "company": (r.company or "").strip(),
                "phone": getattr(r, "phone", "") or "",
                "status": r.status or "sent",
                "template_id": getattr(r, "template_id", "") or "",
                "template_name": getattr(r, "template_name", "") or "",
                "opened": bool(getattr(r, "opened", False)),
                "open_count": open_c,
                "clicked_link": bool(getattr(r, "clicked_link", False)),
                "click_count": click_c,
                "reply_body": (r.reply_body or "").strip(),
                "reply_intent": (r.reply_intent or "").strip(),
                "reply_received_at": r.reply_received_at.isoformat() if r.reply_received_at else None,
                "booking_status": (r.booking_status or "").strip(),
                "confirmed_slot": (r.confirmed_slot or "").strip(),
                "meet_link": (r.meet_link or "").strip(),
                "form_filled_at": r.form_filled_at.isoformat() if r.form_filled_at else None,
                "email_sent_at": r.email_sent_at.isoformat() if r.email_sent_at else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "job_title": meta_cols.get(em, {}).get("job_title", ""),
                "last_activity_date": meta_cols.get(em, {}).get("last_activity_date", ""),
                "location": meta_cols.get(em, {}).get("location", ""),
            }

            temp_info = _categorize_lead_temperature(row_dict)
            row_dict.update(temp_info)
            row_dict["rank"] = rank
            seen_emails[em] = row_dict

        result_leads = list(seen_emails.values())
        result_leads.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)

        return {
            "total": len(result_leads),
            "leads": result_leads,
            "counts": {
                "hot": len([l for l in result_leads if l["tier"] == "HOT"]),
                "warm": len([l for l in result_leads if l["tier"] == "WARM"]),
                "cold": len([l for l in result_leads if l["tier"] == "COLD"]),
            }
        }
    finally:
        db.close()


# ── 5. Template Hub & Review ──
@router.get("/templates")
def get_all_templates():
    db = SessionLocal()
    try:
        df = _get_logs_dataframe(db)
        templates = load_all_templates()
        analytics_result = compute_template_analytics(df)

        stats_list = analytics_result.get("template_stats", [])
        stats_map = {item["id"]: item for item in stats_list}

        enriched_templates = []
        for tpl in templates:
            t_id = tpl["id"]
            t_stats = stats_map.get(t_id, {
                "sent": 0, "opened": 0, "clicked": 0, "replied": 0, "booked": 0,
                "open_rate": 0.0, "click_rate": 0.0, "reply_rate": 0.0, "booking_rate": 0.0,
                "total_leads": 0, "total_sent": 0,
            })
            enriched_templates.append({
                **tpl,
                "stats": t_stats,
            })

        return {
            "templates": enriched_templates,
            "total": len(enriched_templates),
            "summary": {
                "best_open_rate": analytics_result.get("best_open_rate"),
                "best_click_rate": analytics_result.get("best_click_rate"),
                "best_booking_rate": analytics_result.get("best_booking_rate"),
            }
        }
    finally:
        db.close()


@router.get("/templates/{template_id}")
def get_template_detail(template_id: str):
    tpl = get_template_by_id(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    
    sample_lead = {
        "name": "Sarah Connor",
        "company": "Cyberdyne Systems",
        "email": "s.connor@cyberdyne.io",
        "phone": "+1 (555) 234-5678",
    }
    rendered_subject, rendered_body = render_template(
        tpl,
        lead_name=sample_lead["name"],
        company=sample_lead["company"],
    )

    return {
        "template": tpl,
        "sample_preview": {
            "subject": rendered_subject,
            "body": rendered_body,
        }
    }


@router.post("/templates/render")
def render_template_preview(payload: Dict[str, Any]):
    template_id = payload.get("template_id")
    lead_name = payload.get("lead_name", "Sarah Connor")
    company = payload.get("company", "Cyberdyne Systems")
    pain_point = payload.get("pain_point", "manual operational overhead")
    booking_url = payload.get("booking_url") or os.getenv(
        "BOOKING_FORM_URL",
        "https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled",
    )

    subj, body = render_template(
        template_id or "tpl_fde_velocity",
        lead_name=lead_name,
        company=company,
        pain_point=pain_point,
        booking_url=booking_url,
    )
    return {"subject": subj, "body": body}


# ── 6. Upload Leads & AI Draft Generation ──
@router.post("/leads/upload")
async def upload_leads_file(file: UploadFile = File(...)):
    contents = await file.read()
    try:
        if file.filename.endswith(".csv"):
            import io
            df = pd.read_csv(io.BytesIO(contents))
        else:
            import io
            df = pd.read_excel(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse spreadsheet: {str(e)}")

    db = SessionLocal()
    try:
        sent_emails = get_already_sent_emails(db)
        drafted_emails = get_already_drafted_emails(db)
    finally:
        db.close()

    new_leads_df, skipped_sent_df, skipped_drafted_df = detect_lead_status_in_dataframe(
        df, sent_emails=sent_emails, drafted_emails=drafted_emails
    )

    def _clean_records(d):
        recs = d.to_dict(orient="records")
        for r in recs:
            for k, v in r.items():
                if pd.isna(v): r[k] = None
        return recs

    return {
        "filename": file.filename,
        "total_rows": len(df),
        "new_leads_count": len(new_leads_df),
        "skipped_sent_count": len(skipped_sent_df),
        "skipped_drafted_count": len(skipped_drafted_df),
        "new_leads": _clean_records(new_leads_df),
        "skipped_sent": _clean_records(skipped_sent_df),
        "skipped_drafted": _clean_records(skipped_drafted_df),
    }


@router.post("/drafts/generate")
def generate_drafts(payload: Dict[str, Any]):
    leads = payload.get("leads", [])
    template_id = payload.get("template_id")
    campaign_name = payload.get("campaign_name") or os.getenv("CAMPAIGN_NAME", "default_campaign")

    if not leads:
        raise HTTPException(status_code=400, detail="No leads provided for drafting.")

    tpl = get_template_by_id(template_id) if template_id else None
    all_tpls = load_all_templates()
    if not tpl and all_tpls:
        tpl = all_tpls[0]

    db = SessionLocal()
    created_count = 0
    errors = []

    try:
        booking_url = os.getenv("BOOKING_FORM_URL", "https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled")

        for lead in leads:
            try:
                email = str(lead.get("email") or "").strip()
                if not email or "@" not in email:
                    continue

                if is_email_already_sent(db, email):
                    continue

                name = str(lead.get("name") or lead.get("Full Name") or lead.get("Contact Name") or "").strip()
                if not name or name.lower() in ("nan", "none", "-", "—"):
                    from leads import infer_name_from_email
                    name = infer_name_from_email(email) or "Valued Partner"

                company = str(lead.get("company") or lead.get("Company Name") or "").strip()
                if not company or company.lower() in ("nan", "none", "-", "—"):
                    from leads import infer_company_from_email
                    company = infer_company_from_email(email) or "Your Enterprise"

                lead_id = str(lead.get("lead_id") or email)

                token = generate_token(email)
                tracking_link = f"/track/click/{token}?url={booking_url}"

                subject, body = render_template(
                    tpl,
                    lead_name=name,
                    company=company,
                    tracking_link=tracking_link,
                    booking_url=booking_url,
                )

                create_pending_entry(
                    db=db,
                    campaign_name=campaign_name,
                    lead_id=lead_id,
                    email=email,
                    name=name,
                    company=company,
                    token=token,
                    subject=subject,
                    body=body,
                    status="drafted",
                    tracking_link=tracking_link,
                    template_id=tpl.get("id") if tpl else None,
                    template_name=tpl.get("name") if tpl else None,
                )
                created_count += 1
            except Exception as e:
                errors.append(f"{lead.get('email', 'unknown')}: {str(e)}")

        return {
            "success": True,
            "created_count": created_count,
            "errors": errors,
        }
    finally:
        db.close()


# ── 7. Email Review Studio Actions ──
@router.get("/drafts")
def get_pending_drafts():
    db = SessionLocal()
    try:
        rows = db.query(CampaignLog).filter(CampaignLog.status == "drafted").order_by(CampaignLog.created_at.desc()).all()
        return {
            "total": len(rows),
            "drafts": [_serialize_log(r) for r in rows],
        }
    finally:
        db.close()


@router.put("/drafts/{log_id}")
def update_draft(log_id: str, payload: Dict[str, str]):
    subject = payload.get("subject", "")
    body = payload.get("body", "")
    db = SessionLocal()
    try:
        updated = update_draft_content(db, log_id, subject, body)
        return {"success": True, "draft": _serialize_log(updated)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


class ApproveDraftPayload(BaseModel):
    sender_email: Optional[str] = None


@router.post("/drafts/{log_id}/approve")
def approve_and_send(log_id: str, payload: Optional[ApproveDraftPayload] = None):
    db = SessionLocal()
    try:
        sender_email = payload.sender_email if payload else None
        sent_entry = approve_and_send_entry(db, log_id, sender_email=sender_email)
        return {"success": True, "entry": _serialize_log(sent_entry)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to dispatch email: {str(e)}")
    finally:
        db.close()


@router.post("/drafts/{log_id}/reject")
def reject_draft(log_id: str):
    db = SessionLocal()
    try:
        rejected = reject_entry(db, log_id)
        if not rejected:
            return {"success": True, "message": "Draft already rejected or not found", "entry": None}
        return {"success": True, "entry": _serialize_log(rejected)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.post("/drafts/{log_id}/apply-template")
def apply_template_to_draft(log_id: str, payload: Dict[str, str]):
    template_id = payload.get("template_id")
    if not template_id:
        raise HTTPException(status_code=400, detail="template_id required")
    
    db = SessionLocal()
    try:
        r = db.query(CampaignLog).filter(CampaignLog.id == log_id).first()
        if not r:
            raise HTTPException(status_code=404, detail="Draft not found")
        
        tpl = get_template_by_id(template_id)
        if not tpl:
            raise HTTPException(status_code=404, detail="Template not found")
            
        booking_url = os.getenv("BOOKING_FORM_URL", "https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled")
        token = r.token or generate_token(r.email)
        tracking_link = f"/track/click/{token}?url={booking_url}"
        
        subj, body = render_template(
            tpl,
            lead_name=r.name,
            company=r.company,
            tracking_link=tracking_link,
            booking_url=booking_url,
        )
        r.subject = subj
        r.body = body
        r.template_id = tpl.get("id")
        r.template_name = tpl.get("name")
        db.commit()
        db.refresh(r)
        return {"success": True, "draft": _serialize_log(r)}
    finally:
        db.close()


@router.post("/drafts/apply-template-all")
def apply_template_all(payload: Dict[str, str]):
    template_id = payload.get("template_id")
    if not template_id:
        raise HTTPException(status_code=400, detail="template_id required")
    
    db = SessionLocal()
    try:
        tpl = get_template_by_id(template_id)
        if not tpl:
            raise HTTPException(status_code=404, detail="Template not found")
            
        rows = db.query(CampaignLog).filter(CampaignLog.status == "drafted").all()
        booking_url = os.getenv("BOOKING_FORM_URL", "https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled")
        
        updated_count = 0
        for r in rows:
            token = r.token or generate_token(r.email)
            tracking_link = f"/track/click/{token}?url={booking_url}"
            subj, body = render_template(
                tpl,
                lead_name=r.name,
                company=r.company,
                tracking_link=tracking_link,
                booking_url=booking_url,
            )
            r.subject = subj
            r.body = body
            r.template_id = tpl.get("id")
            r.template_name = tpl.get("name")
            updated_count += 1
            
        db.commit()
        return {"success": True, "updated_count": updated_count}
    finally:
        db.close()


@router.post("/drafts/reject-all")
def reject_all_drafts():
    db = SessionLocal()
    try:
        rows = db.query(CampaignLog).filter(CampaignLog.status == "drafted").all()
        count = 0
        for r in rows:
            r.status = "rejected"
            count += 1
        db.commit()
        return {"success": True, "rejected_count": count}
    finally:
        db.close()


class BatchSendDraftsPayload(BaseModel):
    sender_email: Optional[str] = None
    batch_size: Optional[int] = None
    draft_ids: Optional[List[str]] = None


@router.post("/drafts/send-all")
def send_all_drafts(payload: Optional[BatchSendDraftsPayload] = None):
    db = SessionLocal()
    try:
        sender_email = payload.sender_email if payload else None
        batch_size = payload.batch_size if payload else None
        draft_ids = payload.draft_ids if payload else None

        query = db.query(CampaignLog).filter(CampaignLog.status == "drafted")
        if draft_ids:
            query = query.filter(CampaignLog.id.in_(draft_ids))
        if batch_size and batch_size > 0:
            query = query.limit(batch_size)

        rows = query.all()
        sent_count = 0
        failed_count = 0
        errors = []

        for r in rows:
            try:
                approve_and_send_entry(db, r.id, sender_email=sender_email)
                sent_count += 1
            except Exception as e:
                failed_count += 1
                errors.append(f"{r.email}: {str(e)}")

        return {
            "sent_count": sent_count,
            "failed_count": failed_count,
            "errors": errors,
            "sender_email": sender_email,
        }
    finally:
        db.close()


# ── 8. Replies & Consultations ──
@router.get("/replies")
def get_customer_replies():
    db = SessionLocal()
    all_replies = []
    seen_emails = set()

    try:
        # Load from Excel if present
        if os.path.exists(DEFAULT_REPLIES_EXCEL):
            try:
                excel_r_df = pd.read_excel(DEFAULT_REPLIES_EXCEL)
                for _, r in excel_r_df.iterrows():
                    em = str(r.get("email") or "").strip().lower()
                    cust_reply = str(r.get("customer_reply") or "").strip()
                    ai_reply = extract_text_from_ai_message(str(r.get("ai_response_sent") or "")).strip()
                    if em and (cust_reply or ai_reply) and em not in seen_emails and "postmaster" not in em:
                        seen_emails.add(em)
                        all_replies.append({
                            "email": em,
                            "name": str(r.get("name") or "").strip() or "Customer",
                            "company": str(r.get("company") or "").strip() or "—",
                            "reply_intent": str(r.get("reply_intent") or "question").strip(),
                            "customer_reply": cust_reply,
                            "ai_response_sent": ai_reply,
                            "reply_received_at": str(r.get("reply_received_at") or "").strip(),
                            "ai_reply_sent_at": str(r.get("ai_reply_sent_at") or "").strip(),
                        })
            except Exception:
                pass

        # Load from DB
        rows = db.query(CampaignLog).all()
        for r in rows:
            em = str(r.email or "").strip().lower()
            cust_reply = str(r.reply_body or "").strip()
            ai_reply = extract_text_from_ai_message(str(r.ai_reply_sent or "")).strip()
            if not cust_reply and not ai_reply:
                continue
            if em and em not in seen_emails and "postmaster" not in em:
                seen_emails.add(em)
                all_replies.append({
                    "email": em,
                    "name": r.name or "Customer",
                    "company": r.company or "—",
                    "reply_intent": r.reply_intent or "question",
                    "customer_reply": cust_reply,
                    "ai_response_sent": ai_reply,
                    "reply_received_at": r.reply_received_at.isoformat() if r.reply_received_at else "",
                    "ai_reply_sent_at": r.ai_reply_sent_at.isoformat() if r.ai_reply_sent_at else "",
                })

        return {
            "total": len(all_replies),
            "replies": all_replies,
        }
    finally:
        db.close()


@router.get("/bookings")
def get_booked_consultations():
    db = SessionLocal()
    try:
        bookings = []
        if os.path.exists(DEFAULT_BOOKED_EXCEL):
            try:
                b_df = pd.read_excel(DEFAULT_BOOKED_EXCEL)
                for _, r in b_df.iterrows():
                    bookings.append({
                        "email": str(r.get("email") or "").strip(),
                        "name": str(r.get("name") or "").strip(),
                        "company": str(r.get("company") or "").strip(),
                        "confirmed_slot": str(r.get("confirmed_slot") or r.get("submitted_slots") or "").strip(),
                        "service": str(r.get("service") or r.get("service_requested") or "").strip(),
                        "note": str(r.get("note") or "").strip(),
                    })
            except Exception:
                pass

        # Merge DB confirmed bookings
        rows = db.query(CampaignLog).filter(
            CampaignLog.booking_status.in_(["scheduled", "meeting_scheduled", "confirmation_sent", "confirmed"])
            | CampaignLog.form_filled_at.isnot(None)
        ).all()
        for r in rows:
            em = str(r.email or "").strip().lower()
            if not any(b["email"].lower() == em for b in bookings):
                bookings.append({
                    "email": r.email,
                    "name": r.name,
                    "company": r.company,
                    "confirmed_slot": r.confirmed_slot or "Consultation Scheduled",
                    "service": getattr(r, "service_requested", "") or "General Inquiry",
                    "note": r.note or "",
                })

        return {
            "total": len(bookings),
            "bookings": bookings,
        }
    finally:
        db.close()


@router.post("/replies/check-inbox")
def trigger_inbox_check():
    try:
        summary = check_and_reply_inbox(sync_existing=False)
        return {"status": "success", "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daemon/status")
def get_daemon_status():
    return {
        "running": ReplyDaemonManager.is_running(),
        "last_run": ReplyDaemonManager._last_run.isoformat() if ReplyDaemonManager._last_run else None,
    }


@router.post("/daemon/start")
def start_daemon():
    ReplyDaemonManager.start(interval_seconds=30)
    return {"status": "started", "running": True}


@router.post("/daemon/stop")
def stop_daemon():
    ReplyDaemonManager.stop()
    return {"status": "stopped", "running": False}


# ── 9. Knowledge Base & RAG ──
@router.get("/kb/summary")
def get_kb_summary():
    db = SessionLocal()
    try:
        summary = get_knowledge_base_summary(db)
        return summary
    finally:
        db.close()


@router.get("/kb/documents")
def get_kb_documents():
    db = SessionLocal()
    try:
        docs = list_documents(db)
        return {"documents": docs}
    finally:
        db.close()


@router.post("/kb/upload")
async def upload_kb_document(file: UploadFile = File(...), category: Optional[str] = Form(None)):
    contents = await file.read()
    text = contents.decode("utf-8", errors="replace")
    db = SessionLocal()
    try:
        result = ingest_file_content(db, file.filename, text, title=f"Knowledge Base ({file.filename})", category=category)
        return {"success": True, "result": result}
    finally:
        db.close()


@router.delete("/kb/documents")
def delete_kb_document(title: str = Query(...)):
    db = SessionLocal()
    try:
        deleted = delete_document(db, title)
        return {"success": True, "deleted_chunks": deleted}
    finally:
        db.close()


@router.post("/kb/search")
def search_kb_chunks(payload: Dict[str, Any]):
    query = payload.get("query", "")
    top_k = payload.get("top_k", 4)
    db = SessionLocal()
    try:
        chunks = retrieve_relevant_chunks(db, query=query, top_k=top_k)
        return {"query": query, "chunks": chunks}
    except Exception as e:
        return {"query": query, "chunks": [], "error": str(e)}
    finally:
        db.close()


@router.post("/kb/clear")
def clear_kb():
    db = SessionLocal()
    try:
        from services.rag import clear_all_knowledge_documents
        cleared = clear_all_knowledge_documents(db)
        return {"success": True, "cleared_chunks": cleared}
    except Exception as e:
        # Fallback delete all
        db.query(KnowledgeDocument).delete()
        db.commit()
        return {"success": True, "cleared_chunks": 0}
    finally:
        db.close()


# ── 10. Direct Excel Exports ──
@router.get("/excel/customer-replies")
def download_customer_replies_excel():
    if os.path.exists(DEFAULT_REPLIES_EXCEL):
        return FileResponse(
            DEFAULT_REPLIES_EXCEL,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename="customer_replies.xlsx"
        )
    raise HTTPException(status_code=404, detail="customer_replies.xlsx not generated yet")


@router.get("/excel/booked-leads")
def download_booked_leads_excel():
    if os.path.exists(DEFAULT_BOOKED_EXCEL):
        return FileResponse(
            DEFAULT_BOOKED_EXCEL,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename="booked_leads.xlsx"
        )
    raise HTTPException(status_code=404, detail="booked_leads.xlsx not generated yet")


# ── 11. System Operations ──
@router.post("/system/sync")
def trigger_system_sync():
    db = SessionLocal()
    try:
        res = sync_excel_and_outlook_to_db(db)
        return {"status": "success", "result": res}
    finally:
        db.close()


@router.post("/system/reset-all")
def trigger_system_reset():
    db = SessionLocal()
    try:
        res = reset_all_system_data(db)
        return {"status": "success", "result": res}
    finally:
        db.close()
