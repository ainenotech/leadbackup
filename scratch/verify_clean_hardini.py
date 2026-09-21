import pandas as pd
import sqlite3

df = pd.read_excel('customer_replies.xlsx')
print('customer_replies.xlsx rows:', len(df))
for idx, r in df.iterrows():
    print(f"=== Row {idx}: {r['email']} ({r['name']}) ===")
    print("Customer inquiry:", repr(str(r['customer_reply'])[:60]))
    print("AI reply sent starts:", repr(str(r['ai_response_sent'])[:100]))
    print("AI reply sent ends:", repr(str(r['ai_response_sent'])[-100:]))
    assert 'extras' not in str(r['ai_response_sent'])
    assert "[{'type" not in str(r['ai_response_sent'])

conn = sqlite3.connect('campaign.db')
c = conn.cursor()
c.execute("SELECT email, name, ai_reply_sent FROM campaign_log WHERE email LIKE '%hardini%'")
row = c.fetchone()
if row:
    print("\n=== DB campaign_log for Hardini ===")
    print("DB reply starts:", repr(str(row[2])[:100]))
    print("DB reply ends:", repr(str(row[2])[-100:]))
    assert 'extras' not in str(row[2])
    assert "[{'type" not in str(row[2])
conn.close()

print("\nALL RECORDS CLEAN AND PERFECT!")
