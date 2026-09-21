import sys, os
sys.path.insert(0, os.path.abspath("."))
import requests
from utils.microsoft_auth import get_graph_headers, MS_SENDER_EMAIL

headers = get_graph_headers()
url = f"https://graph.microsoft.com/v1.0/users/{MS_SENDER_EMAIL}/mailFolders/inbox/messages?$top=40&$select=id,subject,from,receivedDateTime,isRead,bodyPreview"
res = requests.get(url, headers=headers)
msgs = res.json().get("value", [])

print(f"Total inbox messages fetched: {len(msgs)}")
for m in msgs:
    addr = m.get("from", {}).get("emailAddress", {}).get("address", "")
    name = m.get("from", {}).get("emailAddress", {}).get("name", "")
    subj = m.get("subject", "")
    is_read = m.get("isRead")
    dt = m.get("receivedDateTime", "")
    preview = m.get("bodyPreview", "")[:70]
    if not addr.lower().startswith("microsoftexchange") and not addr.lower().startswith("postmaster"):
        print(f"[{is_read}] {addr} ({name}): '{subj}' | {dt} | {preview}")
