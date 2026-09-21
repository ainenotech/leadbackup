import sqlite3
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from Email.draft_options import get_draft_template_option


def clean_drafts():
    db_path = "campaign.db"
    if not os.path.exists(db_path):
        print("campaign.db not found")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE campaign_log SET status = 'drafted' WHERE id = '5b789060-02bd-4a49-b32d-2e76674b7fe4'")
    cursor.execute("SELECT id, name, company, token, subject, status FROM campaign_log WHERE status IN ('drafted', 'pending', 'approved')")
    rows = cursor.fetchall()
    print(f"Checking {len(rows)} active draft rows in campaign.db...")

    updated = 0
    form_base_url = os.getenv("FORM_BASE_URL", "http://localhost:8000").rstrip("/")

    for rid, name, company, token, subj, status in rows:
        booking_url = f"{form_base_url}/form?token={token}" if token else "https://www.nenotechnology.com"
        if subj and "checking in" in str(subj).lower():
            opt = 2
        elif subj and "audit" in str(subj).lower():
            opt = 3
        else:
            opt = 1

        new_subj, new_body = get_draft_template_option(opt, name, company, booking_url)
        cursor.execute("UPDATE campaign_log SET subject = ?, body = ? WHERE id = ?", (new_subj, new_body, rid))
        print(f"Updated row {rid} ({name} @ {company}) -> Option {opt}")
        updated += 1

    conn.commit()
    conn.close()
    print(f"Successfully updated {updated} drafts with tight, natural email spacing!")


if __name__ == "__main__":
    clean_drafts()
