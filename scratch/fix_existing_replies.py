import os
import sys
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, os.path.abspath("."))
import ast
import re
import sqlite3
import pandas as pd
from Agent.reply_agent import extract_text_from_ai_message


print("Cleaning campaign.db...")
conn = sqlite3.connect("campaign.db")
c = conn.cursor()
c.execute("SELECT id, email, ai_reply_sent FROM campaign_log")
rows = c.fetchall()
for row_id, em, raw in rows:
    if raw and ("[{'type'" in raw or '"extras"' in raw or "'extras'" in raw):
        cleaned = extract_text_from_ai_message(raw)
        c.execute("UPDATE campaign_log SET ai_reply_sent = ? WHERE id = ?", (cleaned, row_id))
        print(f"Cleaned DB row {row_id} for {em}: new length {len(cleaned)}")
conn.commit()
conn.close()

print("Cleaning customer_replies.xlsx...")
if os.path.exists("customer_replies.xlsx"):
    df = pd.read_excel("customer_replies.xlsx")
    if not df.empty and "ai_response_sent" in df.columns:
        for idx, val in df["ai_response_sent"].items():
            if pd.notna(val) and ("[{'type'" in str(val) or "extras" in str(val)):
                cleaned = extract_text_from_ai_message(str(val))
                df.at[idx, "ai_response_sent"] = cleaned
                print(f"Cleaned Excel row {idx}: new length {len(cleaned)}")
        df.to_excel("customer_replies.xlsx", index=False)
        print("Saved clean customer_replies.xlsx!")

print("Done cleaning existing reply records!")
