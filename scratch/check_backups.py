import os
import sqlite3
import pandas as pd

backups_dir = "backups"
for b in sorted(os.listdir(backups_dir)):
    bpath = os.path.join(backups_dir, b)
    if os.path.isdir(bpath):
        print(f"=== {b} ===")
        cdb = os.path.join(bpath, "campaign.db")
        if os.path.exists(cdb):
            try:
                conn = sqlite3.connect(cdb)
                cur = conn.cursor()
                cur.execute("SELECT count(*) FROM campaign_log")
                print("  campaign_log count:", cur.fetchone()[0])
                cur.execute("SELECT email, status, email_sent_at, reply_intent, booking_status FROM campaign_log LIMIT 5")
                print("  Sample rows:", cur.fetchall())
                conn.close()
            except Exception as e:
                print("  db error:", e)
        for xf in ["leads.xlsx", "customer_replies.xlsx", "booked_leads.xlsx"]:
            xp = os.path.join(bpath, xf)
            if os.path.exists(xp):
                try:
                    df = pd.read_excel(xp)
                    print(f"  {xf}: {len(df)} rows")
                except Exception as e:
                    print(f"  {xf} error:", e)
