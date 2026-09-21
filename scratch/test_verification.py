import os
import sys
import pandas as pd
import sqlite3

sys.path.insert(0, os.path.abspath("."))

print("=== 1. Checking Data Files for 0 Dummy Data ===")
for f in ["leads.xlsx", "customer_replies.xlsx", "booked_leads.xlsx"]:
    if os.path.exists(f):
        df = pd.read_excel(f)
        print(f"File {f}: {len(df)} rows. Columns: {list(df.columns)}")
        assert len(df) == 0, f"Expected 0 rows in {f}, got {len(df)}"
    else:
        print(f"File {f}: Not found")

conn = sqlite3.connect("campaign.db")
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM campaign_log")
camp_count = c.fetchone()[0]
print(f"campaign_log table in campaign.db: {camp_count} rows")
assert camp_count == 0, f"Expected 0 rows in campaign_log, got {camp_count}"

c.execute("SELECT COUNT(*) FROM knowledge_documents")
kb_count = c.fetchone()[0]
print(f"knowledge_documents in campaign.db: {kb_count} rows (Verified PDF knowledge preserved)")
assert kb_count > 0, "Expected knowledge_documents to be preserved"
conn.close()

print("\n=== 2. Testing extract_text_from_ai_message ===")
from Agent.reply_agent import extract_text_from_ai_message

# Test case 1: Raw content block list (Anthropic/Gemini)
blocks = [{'type': 'text', 'text': 'Hello Alex,\n\nThank you for reaching out.'}]
extracted = extract_text_from_ai_message(blocks)
print("Extracted from blocks:", repr(extracted))
assert extracted == "Hello Alex,\n\nThank you for reaching out."
assert "[{'type'" not in extracted

# Test case 2: Plain string
assert extract_text_from_ai_message("Simple string") == "Simple string"
print("extract_text_from_ai_message passed all tests!")

print("\n=== 3. Testing Zero-Data Guard in reply_worker ===")
from reply_worker import check_and_reply_inbox
res = check_and_reply_inbox()
print("check_and_reply_inbox() result with 0 leads:", res)
assert res["processed_count"] == 0
assert res["replied_count"] == 0
assert "Zero campaign leads" in res.get("message", "")
print("Zero-Data Guard verified successfully! Agent does not reply when data is zero.")

print("\n=== 4. Verifying customer_replies.xlsx is still 0 ===")
df_replies = pd.read_excel("customer_replies.xlsx")
assert len(df_replies) == 0, f"Expected 0 rows in customer_replies.xlsx, got {len(df_replies)}"
print("customer_replies.xlsx remains clean at 0 rows.")

print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")
