import sys, os
sys.path.insert(0, os.path.abspath('.'))
import requests
import re
from utils.microsoft_auth import MS_SENDER_EMAIL, get_graph_headers

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
headers = get_graph_headers()
resp = requests.get(f"{GRAPH_BASE}/users/{MS_SENDER_EMAIL}/events?$top=10", headers=headers)
events = resp.json().get("value", [])
print(f"Total events checked: {len(events)}")
for i, ev in enumerate(events):
    content = ev.get("body", {}).get("content", "")
    meet_url = re.search(r'href=[\'"](https://teams\.microsoft\.com/meet/[^\'"]+)[\'"]', content)
    meet_id = re.search(r"Meeting ID:[\s\S]*?>([0-9 ]+)<", content)
    passcode = re.search(r"Passcode:[\s\S]*?>([^<]+)<", content)
    print(f"Event {i+1}: {ev.get('subject')}")
    print(f"  Meet URL: {meet_url.group(1) if meet_url else None}")
    print(f"  Meeting ID: {meet_id.group(1).strip() if meet_id else None}")
    print(f"  Passcode: {passcode.group(1).strip() if passcode else None}")
