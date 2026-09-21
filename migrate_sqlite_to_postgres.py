"""Optional one-off script: copies existing rows from the old SQLite
campaign.db (used before this project switched to Postgres) into the
Postgres database configured via DATABASE_URL in .env.

Only needed if you have real campaign history in campaign.db you want to
keep. A fresh setup can skip this — Backend/db.py + Base.metadata.create_all
will create an empty campaign_log table in Postgres automatically the first
time any script/dashboard runs.

Usage:
    python migrate_sqlite_to_postgres.py [path/to/campaign.db]
"""

import sys
import sqlite3
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from Backend.db import Base, SessionLocal, engine
from Backend.models import CampaignLog

Base.metadata.create_all(bind=engine)

COLUMNS = [
    "id", "campaign_name", "lead_id", "email", "name", "company", "token",
    "tracking_link", "subject", "body", "status", "email_sent_at",
    "send_error", "form_filled_at", "submitted_availability", "note",
    "reply_body", "reply_intent", "reply_received_at", "ai_reply_sent",
    "ai_reply_sent_at", "proposed_slot", "confirmed_slot", "meet_link",
    "booking_status", "scheduling_error", "created_at", "updated_at",
]

DATETIME_COLUMNS = {
    "email_sent_at", "form_filled_at", "reply_received_at",
    "ai_reply_sent_at", "created_at", "updated_at",
}


def _parse_dt(value):
    if not value or not isinstance(value, str):
        return value
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        return None


def main():
    sqlite_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("campaign.db")
    if not sqlite_path.exists():
        print(f"No SQLite file found at {sqlite_path} — nothing to migrate.")
        return

    con = sqlite3.connect(str(sqlite_path))
    con.row_factory = sqlite3.Row
    rows = con.execute("SELECT * FROM campaign_log").fetchall()
    con.close()

    if not rows:
        print("campaign_log table in the SQLite file is empty — nothing to migrate.")
        return

    db = SessionLocal()
    migrated, skipped = 0, 0
    try:
        for row in rows:
            row_dict = dict(row)

            if db.query(CampaignLog).filter(CampaignLog.id == row_dict["id"]).first():
                skipped += 1
                continue

            entry = CampaignLog(
                **{
                    col: (_parse_dt(row_dict.get(col)) if col in DATETIME_COLUMNS else row_dict.get(col))
                    for col in COLUMNS
                    if col in row_dict
                }
            )
            db.add(entry)
            migrated += 1

        db.commit()
    finally:
        db.close()

    print(f"Migrated {migrated} row(s) from {sqlite_path} into Postgres. Skipped {skipped} already-present row(s).")


if __name__ == "__main__":
    main()
