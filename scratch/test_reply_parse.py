import sys, os
sys.path.insert(0, os.path.abspath("."))
import requests
from utils.microsoft_auth import get_graph_headers, MS_SENDER_EMAIL

headers = get_graph_headers()
url = f"https://graph.microsoft.com/v1.0/users/{MS_SENDER_EMAIL}/mailFolders/inbox/messages?$top=20&$select=id,subject,from,receivedDateTime,body"
res = requests.get(url, headers=headers)
data = res.json().get("value", [])

for m in data:
    addr = m.get("from", {}).get("emailAddress", {}).get("address", "")
    subj = m.get("subject", "")
    if addr.lower() in ["man@nenotechnology.com", "hetsuthar2157@gmail.com", "ajay1@nenotechnology.com"]:
        print(f"=== SENDER: {addr} | SUBJ: {subj} ===")
        content = m.get("body", {}).get("content", "")
        import re
        text = re.sub(r"<[^>]+>", "\n", content)
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        print("\n".join(lines[:12]))
        print("---------------------------------------")
