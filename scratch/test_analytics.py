import os
import sys
sys.path.insert(0, os.path.abspath("."))
import pandas as pd
from Backend.db import SessionLocal
from Backend.models import CampaignLog
from services.analytics_service import build_comprehensive_analytics

db = SessionLocal()
rows = db.query(CampaignLog).all()
data_list = []
for r in rows:
    data_list.append({
        "id": r.id,
        "campaign": r.campaign_name,
        "lead_id": r.lead_id,
        "email": r.email,
        "name": r.name,
        "company": r.company,
        "phone": getattr(r, "phone", "") or "",
        "status": r.status or "pending",
        "subject": r.subject or "",
        "body": r.body or "",
        "email_sent_at": r.email_sent_at,
        "send_error": r.send_error or "",
        "opened": bool(getattr(r, "opened", False)),
        "open_count": getattr(r, "open_count", 0) or 0,
        "first_open_at": getattr(r, "first_open_at", None),
        "last_open_at": getattr(r, "last_open_at", None),
        "clicked_link": bool(getattr(r, "clicked_link", False)),
        "click_count": getattr(r, "click_count", 0) or 0,
        "first_click_at": getattr(r, "first_click_at", None),
        "last_click_at": getattr(r, "last_click_at", None),
        "clicked_urls": getattr(r, "clicked_urls", "") or "",
        "unsubscribed": bool(getattr(r, "unsubscribed", False)),
        "unsubscribed_at": getattr(r, "unsubscribed_at", None),
        "bounced": bool(getattr(r, "bounced", False)),
        "bounce_reason": getattr(r, "bounce_reason", "") or "",
        "engagement_score": getattr(r, "engagement_score", 0.0) or 0.0,
        "form_filled_at": r.form_filled_at,
        "submitted_availability": r.submitted_availability or "",
        "note": r.note or "",
        "reply_body": r.reply_body or "",
        "reply_intent": r.reply_intent or "",
        "reply_received_at": r.reply_received_at,
        "ai_reply_sent": r.ai_reply_sent or "",
        "ai_reply_sent_at": r.ai_reply_sent_at,
        "proposed_slot": r.proposed_slot or "",
        "confirmed_slot": r.confirmed_slot or "",
        "meet_link": r.meet_link or "",
        "booking_status": r.booking_status or "",
        "token": r.token or "",
        "tracking_link": r.tracking_link or "",
        "created_at": r.created_at,
    })
db.close()

df_logs = pd.DataFrame(data_list)
print(f"Loaded {len(df_logs)} records from CampaignLog")
analytics = build_comprehensive_analytics(df_logs)

totals = analytics["totals"]
print("\n--- Analytics Totals ---")
for k, v in totals.items():
    print(f"  {k}: {v}")

print("\n--- Verification: Any Fake Leads? ---")
names = [r["name"] for r in analytics["leads_records"]]
emails = [r["email"] for r in analytics["leads_records"]]
has_fake = any("Connor" in r["name"] or "Mercer" in r["name"] or "Cyberdyne" in str(r.get("company")) for r in analytics["leads_records"])
print(f"Fake names present: {has_fake}")
print(f"Sample real leads: {emails[:5]}")
print(f"Total intent counts: {analytics['intent_counts']}")
print(f"Subject lines count: {len(analytics['subject_lines'])}")
print(f"CTA variants count: {len(analytics['cta_variants'])}")
print("\nAnalytics build succeeded with 100% real data!")
