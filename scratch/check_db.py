import sqlite3
import os
import pandas as pd

conn = sqlite3.connect("campaign.db")
c = conn.cursor()
tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("SQLite tables and counts:")
for t in tables:
    count = c.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
    print(f"  {t}: {count}")

conn.close()

excel_files = ["customer_replies.xlsx", "booked_leads.xlsx", "leads.xlsx"]
print("\nExcel files:")
for f in excel_files:
    if os.path.exists(f):
        df = pd.read_excel(f)
        print(f"  {f}: {len(df)} rows")
    else:
        print(f"  {f}: not found")
