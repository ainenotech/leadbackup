import os
import sys
import uuid
import sqlite3
import pandas as pd
import requests

from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, os.path.abspath("."))

from utils.microsoft_auth import MS_SENDER_EMAIL, get_graph_headers

conn = sqlite3.connect("campaign.db")
c = conn.cursor()

# 1. Fetch all current messages in Outlook inbox (with pagination) and register their IDs in processed_replies
try:
    headers = get_graph_headers()
    url = f"https://graph.microsoft.com/v1.0/users/{MS_SENDER_EMAIL}/mailFolders/inbox/messages?$top=50"
    total_registered = 0
    
    while url:
        resp = requests.get(url, headers=headers, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            msgs = data.get("value", [])
            for m in msgs:
                mid = m.get("id")
                snd = m.get("from", {}).get("emailAddress", {}).get("address", "")
                sbj = m.get("subject", "")
                c.execute(
                    "INSERT OR IGNORE INTO processed_replies (id, message_id, sender_email, subject, status) VALUES (?, ?, ?, ?, ?)",
                    (f"pr_{uuid.uuid4().hex[:12]}", mid, snd, sbj, "old_historical_suppressed")
                )
                total_registered += 1
            conn.commit()
            url = data.get("@odata.nextLink")
        else:
            print(f"Graph API returned status {resp.status_code}: {resp.text}")
            break
            
    print(f"Registered {total_registered} inbox messages into processed_replies as suppressed!")
except Exception as e:
    print(f"Warning registering inbox messages: {e}")

# 2. Completely empty campaign_log
c.execute("DELETE FROM campaign_log")
conn.commit()
c.execute("SELECT COUNT(*) FROM campaign_log")
print("campaign_log rows:", c.fetchone()[0])
conn.close()

# 3. Reset customer_replies.xlsx to 0 rows
replies_cols = ['email', 'name', 'company', 'reply_intent', 'customer_reply', 'ai_response_sent', 'reply_received_at', 'ai_reply_sent_at', 'status', 'updated_at']
pd.DataFrame(columns=replies_cols).to_excel('customer_replies.xlsx', index=False)
print("customer_replies.xlsx rows:", len(pd.read_excel('customer_replies.xlsx')))

# 4. Reset booked_leads.xlsx to 0 rows
booked_cols = ['email', 'name', 'company', 'status', 'submitted_slots', 'confirmed_slot', 'note', 'updated_at', 'service_requested', 'teams_meeting_link']
pd.DataFrame(columns=booked_cols).to_excel('booked_leads.xlsx', index=False)
print("booked_leads.xlsx rows:", len(pd.read_excel('booked_leads.xlsx')))

# 5. Reset leads.xlsx to 0 rows
leads_cols = ['lead_id', 'email', 'name', 'company', 'last_activity_date', 'last_deal_stage', 'status', 'email_sent_at']
pd.DataFrame(columns=leads_cols).to_excel('leads.xlsx', index=False)
print("leads.xlsx rows:", len(pd.read_excel('leads.xlsx')))

print("\n=== VERIFICATION ===")
assert len(pd.read_excel('customer_replies.xlsx')) == 0
assert len(pd.read_excel('booked_leads.xlsx')) == 0
assert len(pd.read_excel('leads.xlsx')) == 0

conn = sqlite3.connect("campaign.db")
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM campaign_log")
campaign_count = c.fetchone()[0]
assert campaign_count == 0
c.execute("SELECT COUNT(*) FROM processed_replies")
pr_count = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM knowledge_documents")
kd_count = c.fetchone()[0]
print(f"campaign_log count: {campaign_count}")
print(f"customer_replies.xlsx count: 0")
print(f"booked_leads.xlsx count: 0")
print(f"leads.xlsx count: 0")
print(f"processed_replies count: {pr_count} (prevents re-ingestion of historical emails)")
print(f"knowledge_documents count: {kd_count} (PDF knowledge preserved)")
conn.close()

print("\nSUCCESS: ALL DATA IS 100% ZERO LIKE BRAND NEW!")
