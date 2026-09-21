import sqlite3
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from Email.draft_options import get_draft_template_option


def update_draft(option_id: int = 1, token: str = "zrIvszi6TGbNLyNwZS66Ag"):
    conn = sqlite3.connect("campaign.db")
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, company, token FROM campaign_log WHERE token = ?", (token,))
    row = cursor.fetchone()
    if not row:
        print(f"No draft found with token: {token}")
        conn.close()
        return

    entry_id, name, company, token = row
    form_base_url = os.getenv("FORM_BASE_URL", "http://localhost:8000").rstrip("/")
    booking_url = f"{form_base_url}/form?token={token}"

    subject, body = get_draft_template_option(
        option_id=option_id,
        name=name,
        company=company,
        cta_url=booking_url,
    )

    cursor.execute(
        "UPDATE campaign_log SET subject = ?, body = ? WHERE token = ?",
        (subject, body, token),
    )
    conn.commit()
    print(f"Successfully updated draft to Option {option_id} (rows affected: {cursor.rowcount})")
    print(f"Recipient: {name} ({company})")
    print(f"Subject: {subject}")
    conn.close()


if __name__ == "__main__":
    option = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    update_draft(option_id=option)
