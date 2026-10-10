"""Service module for recording form submissions and booked meeting details
into an Excel workbook (booked_leads.xlsx and leads.xlsx) for permanent record keeping.
"""

import os
from datetime import datetime, timezone
import pandas as pd
from utils.text_cleaner import clean_email_text

DEFAULT_BOOKED_EXCEL = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "booked_leads.xlsx"
)

_data_replies_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "customer_replies.xlsx")
_root_replies_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "customer_replies.xlsx")
DEFAULT_REPLIES_EXCEL = _data_replies_path if os.path.exists(_data_replies_path) else _root_replies_path



def log_form_submission_to_excel(
    email: str,
    name: str = None,
    company: str = None,
    service_requested: str = None,
    submitted_slots: str = None,
    note: str = None,
    excel_path: str = DEFAULT_BOOKED_EXCEL,
) -> str:
    """Appends or updates a record in booked_leads.xlsx when a lead fills out the consultation form."""
    os.makedirs(os.path.dirname(excel_path) or ".", exist_ok=True)

    if os.path.exists(excel_path):
        try:
            df = pd.read_excel(excel_path)
            df = df.astype(object)
            meet_cols = [c for c in df.columns if "google" in c.lower() and "meet" in c.lower()]
            if meet_cols:
                df = df.drop(columns=meet_cols)
        except Exception:
            df = pd.DataFrame()
    else:
        df = pd.DataFrame()

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    new_row = {
        "email": email,
        "name": name or "",
        "company": company or "",
        "service_requested": service_requested or "",
        "status": "Form Submitted",
        "submitted_slots": submitted_slots or "",
        "confirmed_slot": "",
        "teams_meeting_link": "",
        "note": note or "",
        "updated_at": timestamp,
    }

    if not df.empty and "email" in df.columns and email in df["email"].values:
        idx = df[df["email"] == email].index[0]
        df.at[idx, "status"] = "Form Submitted"
        if name:
            df.at[idx, "name"] = name
        if company:
            df.at[idx, "company"] = company
        if service_requested:
            df.at[idx, "service_requested"] = service_requested
        df.at[idx, "submitted_slots"] = submitted_slots or ""
        df.at[idx, "note"] = note or ""
        df.at[idx, "updated_at"] = timestamp
    else:
        # Ensure column structure matches
        if "service_requested" not in df.columns and not df.empty:
            df["service_requested"] = ""
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    df.to_excel(excel_path, index=False)
    return excel_path



def log_booking_to_excel(
    email: str,
    name: str = None,
    company: str = None,
    confirmed_slot: str = None,
    meet_link: str = None,
    excel_path: str = DEFAULT_BOOKED_EXCEL,
) -> str:
    """Appends or updates a record in booked_leads.xlsx when a Microsoft Teams meeting is booked."""
    os.makedirs(os.path.dirname(excel_path) or ".", exist_ok=True)

    if os.path.exists(excel_path):
        try:
            df = pd.read_excel(excel_path)
            df = df.astype(object)
            meet_cols = [c for c in df.columns if "google" in c.lower() and "meet" in c.lower()]
            if meet_cols:
                df = df.drop(columns=meet_cols)
        except Exception:
            df = pd.DataFrame()
    else:
        df = pd.DataFrame()

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    if not df.empty and "email" in df.columns and email in df["email"].values:
        idx = df[df["email"] == email].index[0]
        df.at[idx, "status"] = "Meeting Scheduled"
        df.at[idx, "confirmed_slot"] = str(confirmed_slot or "")
        df.at[idx, "teams_meeting_link"] = str(meet_link or "")
        df.at[idx, "updated_at"] = timestamp
    else:
        new_row = {
            "email": email,
            "name": name or "",
            "company": company or "",
            "status": "Meeting Scheduled",
            "submitted_slots": "",
            "confirmed_slot": confirmed_slot or "",
            "teams_meeting_link": meet_link or "",
            "note": "",
            "updated_at": timestamp,
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    df.to_excel(excel_path, index=False)
    return excel_path


def log_reply_to_excel(
    email: str,
    name: str = None,
    company: str = None,
    reply_intent: str = None,
    customer_reply: str = None,
    ai_response_sent: str = None,
    reply_received_at: str = None,
    ai_reply_sent_at: str = None,
    excel_path: str = DEFAULT_REPLIES_EXCEL,
) -> str:
    """Appends or updates a customer reply record in customer_replies.xlsx."""
    os.makedirs(os.path.dirname(excel_path) or ".", exist_ok=True)

    if os.path.exists(excel_path):
        try:
            df = pd.read_excel(excel_path)
            df = df.astype(object)
        except Exception:
            df = pd.DataFrame()
    else:
        df = pd.DataFrame()

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    clean_email = email.strip().lower() if email else ""
    clean_ai_sent = clean_email_text(ai_response_sent) if ai_response_sent else ""

    new_row = {
        "email": clean_email,
        "name": name or "",
        "company": company or "",
        "reply_intent": reply_intent or "interested",
        "customer_reply": customer_reply or "",
        "ai_response_sent": clean_ai_sent,
        "reply_received_at": str(reply_received_at or timestamp),
        "ai_reply_sent_at": str(ai_reply_sent_at or timestamp),
        "status": "Replied",
        "updated_at": timestamp,
    }

    if not df.empty and "email" in df.columns and clean_email in df["email"].astype(str).str.lower().values:
        idx = df[df["email"].astype(str).str.lower() == clean_email].index[0]
        df.at[idx, "status"] = "Replied"
        if name:
            df.at[idx, "name"] = name
        if company:
            df.at[idx, "company"] = company
        if reply_intent:
            df.at[idx, "reply_intent"] = reply_intent
        if customer_reply:
            df.at[idx, "customer_reply"] = customer_reply
        if ai_response_sent:
            df.at[idx, "ai_response_sent"] = clean_ai_sent
        if reply_received_at:
            df.at[idx, "reply_received_at"] = str(reply_received_at)

        if ai_reply_sent_at:
            df.at[idx, "ai_reply_sent_at"] = str(ai_reply_sent_at)
        df.at[idx, "updated_at"] = timestamp
    else:
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    df.to_excel(excel_path, index=False)
    return excel_path


def sync_all_replies_to_excel(db_session, excel_path: str = DEFAULT_REPLIES_EXCEL) -> pd.DataFrame:
    """Extracts all customer reply interactions from the database and writes/refreshes customer_replies.xlsx."""
    from Backend.models import CampaignLog

    os.makedirs(os.path.dirname(excel_path) or ".", exist_ok=True)

    rows = (
        db_session.query(CampaignLog)
        .filter(
            (CampaignLog.reply_body.isnot(None)) | (CampaignLog.ai_reply_sent.isnot(None))
        )
        .order_by(CampaignLog.reply_received_at.desc(), CampaignLog.updated_at.desc())
        .all()
    )

    data = []
    for r in rows:
        data.append({
            "email": (r.email or "").strip().lower(),
            "name": r.name or "",
            "company": r.company or "",
            "reply_intent": r.reply_intent or "interested",
            "customer_reply": r.reply_body or "",
            "ai_response_sent": r.ai_reply_sent or "",
            "reply_received_at": str(r.reply_received_at or ""),
            "ai_reply_sent_at": str(r.ai_reply_sent_at or ""),
            "status": "Replied",
            "updated_at": str(r.updated_at or r.reply_received_at or ""),
        })

    df = pd.DataFrame(data)
    df.to_excel(excel_path, index=False)
    return df
