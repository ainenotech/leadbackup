from datetime import datetime
from typing import List, Tuple

import requests

from utils.microsoft_auth import MS_SENDER_EMAIL, get_graph_headers

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class OutlookCalendar:
    """Wraps the Microsoft Graph calendar calls needed for checking
    free/busy blocks and creating events with an attached Microsoft Teams
    meeting, on the shared support mailbox's calendar. Uses app-only
    (client credentials) auth from utils.microsoft_auth, mirroring the same
    interface the app previously used against Google Calendar.
    """

    def get_busy_blocks(
        self, start: datetime, end: datetime, tz: str
    ) -> List[Tuple[datetime, datetime]]:
        """Queries Microsoft Graph's /calendar/getSchedule for the support
        mailbox over [start, end]. Returns a list of (start, end) datetimes
        for every busy/tentative/out-of-office block.
        """
        payload = {
            "schedules": [MS_SENDER_EMAIL],
            "startTime": {"dateTime": start.isoformat(), "timeZone": tz},
            "endTime": {"dateTime": end.isoformat(), "timeZone": tz},
            "availabilityViewInterval": 30,
        }

        resp = requests.post(
            f"{GRAPH_BASE}/users/{MS_SENDER_EMAIL}/calendar/getSchedule",
            headers=get_graph_headers(),
            json=payload,
            timeout=30,
        )
        if resp.status_code >= 300:
            raise RuntimeError(
                f"Microsoft Graph getSchedule failed ({resp.status_code}): {resp.text}"
            )

        schedules = resp.json().get("value", [])
        busy_blocks: List[Tuple[datetime, datetime]] = []
        if schedules:
            from zoneinfo import ZoneInfo
            tz_obj = ZoneInfo(tz)
            for item in schedules[0].get("scheduleItems", []):
                if item.get("status") in ("busy", "tentative", "oof"):
                    busy_start = datetime.fromisoformat(item["start"]["dateTime"])
                    busy_end = datetime.fromisoformat(item["end"]["dateTime"])
                    if busy_start.tzinfo is None:
                        busy_start = busy_start.replace(tzinfo=tz_obj)
                    if busy_end.tzinfo is None:
                        busy_end = busy_end.replace(tzinfo=tz_obj)
                    busy_blocks.append((busy_start, busy_end))

        return busy_blocks

    def create_event_with_meet(
        self,
        subject: str,
        body_html: str,
        start: datetime,
        end: datetime,
        tz: str,
        attendee_email: str,
    ) -> dict:
        """Creates an event on the support mailbox's calendar with the lead
        as an attendee and an automatically generated Microsoft Teams
        meeting link (isOnlineMeeting + teamsForBusiness provider).
        """
        payload = {
            "subject": subject,
            "body": {"contentType": "HTML", "content": body_html},
            "start": {"dateTime": start.isoformat(), "timeZone": tz},
            "end": {"dateTime": end.isoformat(), "timeZone": tz},
            "attendees": [
                {"emailAddress": {"address": attendee_email}, "type": "required"}
            ],
            "isOnlineMeeting": True,
            "onlineMeetingProvider": "teamsForBusiness",
        }

        resp = requests.post(
            f"{GRAPH_BASE}/users/{MS_SENDER_EMAIL}/events",
            headers=get_graph_headers(),
            json=payload,
            timeout=30,
        )
        if resp.status_code >= 300:
            raise RuntimeError(
                f"Microsoft Graph create event failed ({resp.status_code}): {resp.text}"
            )

        event = resp.json()
        meet_link = (event.get("onlineMeeting") or {}).get("joinUrl", "")

        return {
            "event_id": event.get("id"),
            "meet_link": meet_link or "",
        }
