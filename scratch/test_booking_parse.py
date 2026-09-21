import sys, os
sys.path.insert(0, os.path.abspath("."))
import requests
from utils.microsoft_auth import get_graph_headers, MS_SENDER_EMAIL

headers = get_graph_headers()
url = f"https://graph.microsoft.com/v1.0/users/{MS_SENDER_EMAIL}/mailFolders/inbox/messages?$filter=startswith(subject,'New booking:')&$top=3&$select=id,subject,from,body"
res = requests.get(url, headers=headers)
data = res.json().get("value", [])

for i, m in enumerate(data):
    subj = m.get("subject")
    content = m.get("body", {}).get("content", "")
    print(f"=== Booking {i+1}: {subj} ===")
    import re
    # Strip html
    text = re.sub(r"<[^>]+>", " ", content)
    text = re.sub(r"\s+", " ", text).strip()
    print(text[:400])
