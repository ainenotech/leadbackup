import ast
import re
import sqlite3

conn = sqlite3.connect("campaign.db")
c = conn.cursor()
c.execute("SELECT ai_reply_sent FROM campaign_log WHERE email LIKE '%hardini%'")
raw = c.fetchone()[0]
conn.close()

def extract_clean_text(content):
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                text_val = block.get("text", "")
                if text_val:
                    parts.append(text_val)
            elif hasattr(block, "text"):
                text_val = getattr(block, "text", "")
                if text_val:
                    parts.append(text_val)
            else:
                parts.append(str(block))
        return "\n".join(parts).strip()
    elif isinstance(content, str):
        s = content.strip()
        if (s.startswith("[{") and ("'text'" in s or '"text"' in s)):
            try:
                parsed = ast.literal_eval(s)
                if isinstance(parsed, list):
                    return extract_clean_text(parsed)
            except Exception:
                pass
            try:
                import json
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    return extract_clean_text(parsed)
            except Exception:
                pass
            m = re.search(r"['\"]text['\"]\s*:\s*(['\"])(.*?)\1(?:,\s*['\"]extras|\}\])", s, re.DOTALL)
            if m:
                try:
                    return m.group(2).encode().decode("unicode-escape").strip()
                except Exception:
                    return m.group(2).strip()
        return s
    return str(content).strip()

cleaned = extract_clean_text(raw)
print("CLEANED LENGTH:", len(cleaned))
print("STARTS WITH:\n", cleaned[:150])
print("\nENDS WITH:\n", cleaned[-150:])
assert "extras" not in cleaned
assert "[{'type" not in cleaned
print("\nTEST PASSED 100%!")
