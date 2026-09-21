import ast
import sqlite3
import pandas as pd

conn = sqlite3.connect('campaign.db')
c = conn.cursor()
c.execute("SELECT email, name, ai_reply_sent FROM campaign_log WHERE email LIKE '%hardini%'")
row = c.fetchone()
if row:
    email, name, raw = row
    print("Email:", email)
    print("Name:", name)
    print("Raw start:", raw[:120])
    print("Raw end:", raw[-120:])
    try:
        parsed = ast.literal_eval(raw)
        if isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], dict):
            clean_text = parsed[0].get('text', '')
            print("\n=== CLEAN TEXT EXTRACTED ===")
            print(clean_text[:300])
    except Exception as e:
        print("Error:", e)
conn.close()
