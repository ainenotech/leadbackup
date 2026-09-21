import sqlite3
import re
import os

def upgrade_draft_headers():
    conn = sqlite3.connect("campaign.db")
    cursor = conn.cursor()

    form_base_url = os.getenv("FORM_BASE_URL", "http://localhost:8000").rstrip("/")
    logo_img_tag = f'<img src="{form_base_url}/logo-dark.png" alt="Nenotechnology" style="height:36px;max-height:40px;width:auto;display:block;border:0;">'

    cursor.execute("SELECT id, email, token, body FROM campaign_log WHERE status='drafted'")
    rows = cursor.fetchall()
    updated = 0

    for entry_id, email, token, body in rows:
        if not body:
            continue

        new_body = body
        # Pattern 1: stylized div text header
        new_body = re.sub(
            r'<div style="font-size:18px;font-weight:800;letter-spacing:0\.5px;color:#0f62fe;">NENOTECHNOLOGY\s*<span[^>]*>Aineno Innovation Pvt\. Ltd\.</span></div>',
            logo_img_tag,
            new_body,
            flags=re.IGNORECASE
        )
        # Pattern 2: raw div small text header
        new_body = re.sub(
            r'<div>NENOTECHNOLOGY\s*<small[^>]*>Aineno Innovation Pvt\. Ltd\.</small></div>',
            logo_img_tag,
            new_body,
            flags=re.IGNORECASE
        )

        if new_body != body:
            cursor.execute("UPDATE campaign_log SET body = ? WHERE id = ?", (new_body, entry_id))
            updated += 1
            print(f"Updated logo header for: {email}")

    conn.commit()
    print(f"Total drafts updated with real logo: {updated}")
    conn.close()

if __name__ == "__main__":
    upgrade_draft_headers()
