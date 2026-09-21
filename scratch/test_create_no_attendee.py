import sys, os
sys.path.insert(0, os.path.abspath('.'))
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests, re
from utils.microsoft_auth import MS_SENDER_EMAIL, get_graph_headers

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
tz = "Asia/Kolkata"
now = datetime.now(ZoneInfo(tz)) + timedelta(days=5)
start = now.replace(hour=14, minute=0, second=0, microsecond=0)
end = start + timedelta(minutes=30)

payload = {
    "subject": "Test Internal Meeting No Attendee",
    "body": {"contentType": "HTML", "content": "Testing teams link generation without attendees"},
    "start": {"dateTime": start.isoformat(), "timeZone": tz},
    "end": {"dateTime": end.isoformat(), "timeZone": tz},
    "attendees": [],
    "isOnlineMeeting": True,
    "onlineMeetingProvider": "teamsForBusiness",
}

resp = requests.post(
    f"{GRAPH_BASE}/users/{MS_SENDER_EMAIL}/events",
    headers=get_graph_headers(),
    json=payload,
    timeout=30,
)
print("Create status:", resp.status_code)
if resp.status_code < 300:
    ev = resp.json()
    content = ev.get("body", {}).get("content", "")
    meet_url = re.search(r'href=[\'"](https://teams\.microsoft\.com/meet/[^\'"]+)[\'"]', content)
    meet_id = re.search(r"Meeting ID:[\s\S]*?>([0-9 ]+)<", content)
    passcode = re.search(r"Passcode:[\s\S]*?>([^<]+)<", content)
    print("OnlineMeeting joinUrl:", (ev.get("onlineMeeting") or {}).get("joinUrl"))
    print("Parsed meet URL:", meet_url.group(1) if meet_url else None)
    print("Meeting ID:", meet_id.group(1).strip() if meet_id else None)
    print("Passcode:", passcode.group(1).strip() if passcode else None)

    # Clean up test event
    ev_id = ev.get("id")
    del_resp = requests.delete(f"{GRAPH_BASE}/users/{MS_SENDER_EMAIL}/events/{ev_id}", headers=get_graph_headers())
    print("Cleaned up test event:", del_resp.status_code)
