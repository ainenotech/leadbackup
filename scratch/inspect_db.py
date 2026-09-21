import os
import sqlite3
import pandas as pd

print("--- Checking campaign.db ---")
if os.path.exists("campaign.db"):
    print("campaign.db size:", os.path.getsize("campaign.db"))
    conn = sqlite3.connect("campaign.db")
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cur.fetchall()
    print("Tables:", tables)
    for (tname,) in tables:
        cur.execute(f'SELECT count(*) FROM "{tname}"')
        cnt = cur.fetchone()[0]
        print(f"Table {tname}: {cnt} rows")
    conn.close()
else:
    print("campaign.db does not exist")

print("\n--- Checking Excel files ---")
for f in ["leads.xlsx", "booked_leads.xlsx", "customer_replies.xlsx"]:
    if os.path.exists(f):
        try:
            df = pd.read_excel(f)
            print(f"{f}: {len(df)} rows, columns: {list(df.columns)}")
            if len(df) > 0:
                print(df.head(2))
        except Exception as e:
            print(f"{f} error: {e}")
    else:
        print(f"{f} not found")
