import sqlite3

def check_drafts():
    conn = sqlite3.connect("campaign.db")
    c = conn.cursor()
    c.execute("SELECT id, email, name, company, token, status, subject, body FROM campaign_log WHERE status='drafted'")
    rows = c.fetchall()
    print(f"Total drafted: {len(rows)}")
    for r in rows:
        email = r[1]
        name = r[2]
        subj = r[6]
        body = r[7] or ""
        has_logo = "logo-dark.png" in body or "logo.png" in body
        has_unsub = "unsubscribe" in body.lower()
        is_html = body.strip().startswith("<div")
        print(f"- {email} ({name}): HTML={is_html}, HasLogo={has_logo}, HasUnsub={has_unsub}, Subj={subj}")
        print("  HEADER:", repr(body[:250]))
    conn.close()

if __name__ == "__main__":
    check_drafts()
