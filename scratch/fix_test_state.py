import os
import sys
sys.path.insert(0, os.path.abspath("."))
import pandas as pd
from datetime import datetime, timezone
from Backend.db import SessionLocal
from Backend.models import CampaignLog
from sqlalchemy import text

# 1. Reset customer_replies.xlsx
replies_cols = ['email', 'name', 'company', 'reply_intent', 'customer_reply', 'ai_response_sent', 'reply_received_at', 'ai_reply_sent_at', 'status', 'updated_at']
pd.DataFrame(columns=replies_cols).to_excel('customer_replies.xlsx', index=False)
print("customer_replies.xlsx cleaned")

# 2. Update processed_replies in PostgreSQL
db = SessionLocal()
db.execute(text("UPDATE processed_replies SET status = 'historical_before_send_skipped' WHERE LOWER(sender_email) LIKE '%man@%' OR LOWER(sender_email) LIKE '%nenotechnology%'"))
db.commit()
print("processed_replies updated")

# 3. Clean Man in campaign_log
man = db.query(CampaignLog).filter(CampaignLog.email.ilike('%man@nenotechnology.com%')).first()
if man:
    man.status = 'sent'
    man.email_sent_at = datetime(2026, 9, 19, 14, 24, 37, tzinfo=timezone.utc)
    man.reply_body = None
    man.reply_intent = None
    man.reply_received_at = None
    man.ai_reply_sent = None
    man.ai_reply_sent_at = None
    man.opened = False
    man.open_count = 0
    man.first_open_at = None
    man.last_open_at = None
    man.clicked_link = False
    man.click_count = 0
    man.engagement_score = 15.0
    db.commit()
    print("Man updated to sent, 0 opens, 0 replies")

db.close()
