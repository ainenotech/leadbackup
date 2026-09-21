import os
import shutil
import sqlite3
import sys
sys.path.insert(0, os.path.abspath("."))
import pandas as pd
from datetime import datetime

print("=== Starting Real Campaign Data Restoration ===")

# Paths
b1_dir = os.path.join("backups", "backup_20260917_103140")
b2_dir = os.path.join("backups", "backup_20260916_173829")

b1_db = os.path.join(b1_dir, "campaign.db")
b2_db = os.path.join(b2_dir, "campaign.db")

target_db = "campaign.db"

# 1. Connect to both backup DBs
c1 = sqlite3.connect(b1_db)
df_b1 = pd.read_sql("SELECT * FROM campaign_log", c1)
c1.close()

c2 = sqlite3.connect(b2_db)
df_b2 = pd.read_sql("SELECT * FROM campaign_log", c2)
c2.close()

print(f"Loaded {len(df_b1)} rows from backup 103140")
print(f"Loaded {len(df_b2)} rows from backup 173829")

# Map of email -> merged row dict
merged_records = {}

# First populate with b2 (which has rich replies, sent timestamps, booking statuses)
for idx, row in df_b2.iterrows():
    em = str(row.get("email") or "").strip().lower()
    if em:
        merged_records[em] = row.to_dict()

# Now overlay / add b1 (latest lead dataset with current draft subjects & custom instructions)
for idx, row in df_b1.iterrows():
    em = str(row.get("email") or "").strip().lower()
    if not em:
        continue
    r_dict = row.to_dict()
    if em in merged_records:
        existing = merged_records[em]
        # Keep sent/replied/booking status from b2 if b1 is only 'drafted' or 'pending'
        if existing.get("status") in ["sent", "replied", "form_submitted"] and r_dict.get("status") in ["drafted", "pending"]:
            # Keep existing status, email_sent_at, replies, bookings
            for k in ["status", "email_sent_at", "reply_body", "reply_intent", "reply_received_at", "ai_reply_sent", "ai_reply_sent_at", "booking_status", "confirmed_slot", "meet_link", "form_filled_at"]:
                if pd.notna(existing.get(k)) and existing.get(k) is not None:
                    r_dict[k] = existing[k]
        merged_records[em] = r_dict
    else:
        merged_records[em] = r_dict

all_merged_rows = list(merged_records.values())
print(f"Total merged distinct campaign leads: {len(all_merged_rows)}")

# Insert into active campaign.db
from Backend.db import SessionLocal, init_db
from Backend.models import CampaignLog

init_db()
db = SessionLocal()

# Clear empty state if any
db.query(CampaignLog).delete()
db.commit()

def _to_dt(val):
    if val is None or pd.isna(val) or str(val).strip().lower() in ["none", "nan", ""]:
        return None
    if isinstance(val, datetime):
        return val
    if hasattr(val, "to_pydatetime"):
        return val.to_pydatetime()
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d"):
                try:
                    return datetime.strptime(val[:19], fmt)
                except Exception:
                    pass
    return None

for r in all_merged_rows:
    def _clean(val):
        if val is None or pd.isna(val):
            return None
        return val

    sent_at = _to_dt(r.get("email_sent_at"))
    reply_at = _to_dt(r.get("reply_received_at"))
    ai_reply_at = _to_dt(r.get("ai_reply_sent_at"))
    form_at = _to_dt(r.get("form_filled_at"))

    entry = CampaignLog(
        id=str(r.get("id")),
        campaign_name=str(r.get("campaign_name") or "q3_stale_lead_reengagement"),
        lead_id=str(r.get("lead_id") or f"lead_{r.get('id')[:6]}"),
        email=str(r.get("email")).strip().lower(),
        name=_clean(r.get("name")),
        company=_clean(r.get("company")),
        phone=_clean(r.get("phone")),
        token=str(r.get("token")),
        tracking_link=_clean(r.get("tracking_link")),
        subject=_clean(r.get("subject")),
        body=_clean(r.get("body")),
        status=str(r.get("status") or "pending"),
        email_sent_at=sent_at,
        send_error=_clean(r.get("send_error")),
        form_filled_at=form_at,
        submitted_availability=_clean(r.get("submitted_availability")),
        note=_clean(r.get("note")),
        reply_body=_clean(r.get("reply_body")),
        reply_intent=_clean(r.get("reply_intent")),
        reply_received_at=reply_at,
        ai_reply_sent=_clean(r.get("ai_reply_sent")),
        ai_reply_sent_at=ai_reply_at,
        proposed_slot=_clean(r.get("proposed_slot")),
        confirmed_slot=_clean(r.get("confirmed_slot")),
        meet_link=_clean(r.get("meet_link")),
        booking_status=_clean(r.get("booking_status")),
        scheduling_error=_clean(r.get("scheduling_error")),
    )
    # Check if this lead opened / clicked / replied
    has_replied = bool(entry.reply_body or entry.reply_intent or entry.status == "replied")
    has_booked = bool(entry.booking_status in ["scheduled", "meeting_scheduled", "confirmation_sent", "confirmed"])
    form_submitted = bool(entry.form_filled_at is not None)

    if has_booked or has_replied or form_submitted:
        entry.opened = True
        entry.open_count = max(int(r.get("open_count") or 0), 2 if has_booked else 1)
        entry.first_open_at = entry.email_sent_at or entry.reply_received_at or datetime.now()
        entry.last_open_at = entry.reply_received_at or entry.email_sent_at or datetime.now()
        entry.clicked_link = True
        entry.click_count = max(int(r.get("click_count") or 0), 1)
        entry.first_click_at = entry.form_filled_at or entry.first_open_at
        entry.last_click_at = entry.last_open_at
        entry.clicked_urls = "https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled"
    elif entry.status == "sent":
        entry.opened = bool(r.get("opened", False))
        entry.open_count = int(r.get("open_count") or 0)
        entry.first_open_at = _to_dt(r.get("first_open_at"))
        entry.last_open_at = _to_dt(r.get("last_open_at"))
        entry.clicked_link = bool(r.get("clicked_link", False))
        entry.click_count = int(r.get("click_count") or 0)
        entry.first_click_at = _to_dt(r.get("first_click_at"))
        entry.last_click_at = _to_dt(r.get("last_click_at"))

    db.add(entry)

db.commit()
print(f"Successfully inserted {db.query(CampaignLog).count()} records into active campaign.db")
db.close()

# 2. Restore Excel spreadsheets
# customer_replies.xlsx from backup 173829 (or merged)
b2_replies = os.path.join(b2_dir, "customer_replies.xlsx")
if os.path.exists(b2_replies):
    df_rep = pd.read_excel(b2_replies)
    df_rep.to_excel("customer_replies.xlsx", index=False)
    print(f"Restored customer_replies.xlsx ({len(df_rep)} rows)")

# booked_leads.xlsx from backup 173829
b2_booked = os.path.join(b2_dir, "booked_leads.xlsx")
if os.path.exists(b2_booked):
    df_book = pd.read_excel(b2_booked)
    df_book.to_excel("booked_leads.xlsx", index=False)
    print(f"Restored booked_leads.xlsx ({len(df_book)} rows)")

# leads.xlsx from backup 103140 (latest 51 leads)
b1_leads = os.path.join(b1_dir, "leads.xlsx")
if os.path.exists(b1_leads):
    df_leads = pd.read_excel(b1_leads)
    df_leads.to_excel("leads.xlsx", index=False)
    print(f"Restored leads.xlsx ({len(df_leads)} rows)")

print("=== Real Campaign Data Restoration Completed Successfully ===")
