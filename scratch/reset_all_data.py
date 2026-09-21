import os
import sys
sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import shutil
import sqlite3
import datetime
import pandas as pd

timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup_dir = os.path.join("backups", f"backup_{timestamp}")
os.makedirs(backup_dir, exist_ok=True)
print(f"Created backup directory: {backup_dir}")

# 1. Backup existing files
files_to_backup = [
    "campaign.db",
    "leads.xlsx",
    "booked_leads.xlsx",
    "customer_replies.xlsx"
]

for fname in files_to_backup:
    if os.path.exists(fname):
        dest = os.path.join(backup_dir, fname)
        shutil.copy2(fname, dest)
        print(f"Backed up: {fname} -> {dest}")

# 2. Reset campaign.db (SQLite)
if os.path.exists("campaign.db"):
    conn = sqlite3.connect("campaign.db")
    cur = conn.cursor()
    
    # Check tables
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cur.fetchall()]
    
    if "campaign_log" in tables:
        cur.execute("DELETE FROM campaign_log;")
        print("campaign_log: deleted all rows.")
    if "processed_replies" in tables:
        cur.execute("DELETE FROM processed_replies;")
        print("processed_replies: deleted all rows.")
    if "document_sync_state" in tables:
        cur.execute("DELETE FROM document_sync_state;")
        print("document_sync_state: deleted all rows.")
        
    conn.commit()
    cur.execute("VACUUM;")
    conn.close()
    print("campaign.db cleaned and vacuumed successfully.")

# 3. Check and reset PostgreSQL if accessible
try:
    from Backend.db import engine, SessionLocal
    from Backend.models import CampaignLog
    from sqlalchemy import text

    session = SessionLocal()
    # If using postgres or sqlite
    print("Attempting to clean PostgreSQL tables...")
    session.query(CampaignLog).delete()
    session.commit()
    print("PostgreSQL campaign_log table cleared.")
    session.close()
except Exception as e:
    print(f"PostgreSQL cleanup notice: {e}")

# 4. Reset booked_leads.xlsx to 0 rows (headers preserved)
booked_cols = [
    'email', 'name', 'company', 'status', 'submitted_slots',
    'confirmed_slot', 'note', 'updated_at', 'service_requested', 'teams_meeting_link'
]
empty_booked_df = pd.DataFrame(columns=booked_cols)
empty_booked_df.to_excel("booked_leads.xlsx", index=False)
print(f"booked_leads.xlsx: reset to 0 rows. Columns: {booked_cols}")

# 5. Reset customer_replies.xlsx to 0 rows (headers preserved)
replies_cols = [
    'email', 'name', 'company', 'reply_intent', 'customer_reply',
    'ai_response_sent', 'reply_received_at', 'ai_reply_sent_at', 'status', 'updated_at'
]
empty_replies_df = pd.DataFrame(columns=replies_cols)
empty_replies_df.to_excel("customer_replies.xlsx", index=False)
print(f"customer_replies.xlsx: reset to 0 rows. Columns: {replies_cols}")

# 6. Reset leads.xlsx to 0 rows (headers preserved)
leads_cols = [
    'lead_id', 'email', 'name', 'company', 'last_activity_date',
    'last_deal_stage', 'status', 'email_sent_at'
]
empty_leads_df = pd.DataFrame(columns=leads_cols)
empty_leads_df.to_excel("leads.xlsx", index=False)
print(f"leads.xlsx: reset to 0 rows. Columns: {leads_cols}")

print("\n--- Verification Summary ---")
# Verify SQLite
if os.path.exists("campaign.db"):
    conn = sqlite3.connect("campaign.db")
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    existing_tables = [r[0] for r in cur.fetchall()]
    for t in ['campaign_log', 'processed_replies', 'knowledge_documents']:
        if t in existing_tables:
            cur.execute(f'SELECT COUNT(*) FROM "{t}"')
            cnt = cur.fetchone()[0]
            print(f"SQLite table '{t}' count: {cnt}")
    conn.close()

# Verify Excels
for fname in ["leads.xlsx", "booked_leads.xlsx", "customer_replies.xlsx"]:
    df = pd.read_excel(fname)
    print(f"{fname} count: {len(df)} rows, columns: {list(df.columns)}")

print("\nAll campaign, lead, booking, and reply data successfully reset to 0!")
