"""Phase 3's matching engine: cross-references the lead's submitted slots,
the support mailbox's Microsoft 365 (Outlook) calendar free/busy, and the
office-hours window, and picks a slot — or, if nothing overlaps, computes a
fallback set of alternate slots. No API calls happen in this module; it's
pure logic over datetimes so it can be unit-tested without live Microsoft
Graph credentials.
"""

import json
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from zoneinfo import ZoneInfo

from .config import (
    AUTO_PROPOSE_LOOKAHEAD_DAYS,
    AUTO_PROPOSE_SLOT_COUNT,
    MEETING_DURATION_MINUTES,
    OFFICE_HOURS_DAYS,
    OFFICE_HOURS_END,
    OFFICE_HOURS_START,
    OFFICE_HOURS_TZ,
)

BusyBlock = Tuple[datetime, datetime]


def _tz() -> ZoneInfo:
    return ZoneInfo(OFFICE_HOURS_TZ)


def _office_hours_bounds(local_day: datetime) -> Tuple[datetime, datetime]:
    """Given any tz-aware datetime, returns that local day's office-hours
    start/end as tz-aware datetimes in OFFICE_HOURS_TZ."""
    sh, sm = (int(x) for x in OFFICE_HOURS_START.split(":"))
    eh, em = (int(x) for x in OFFICE_HOURS_END.split(":"))
    start = local_day.replace(hour=sh, minute=sm, second=0, microsecond=0)
    end = local_day.replace(hour=eh, minute=em, second=0, microsecond=0)
    return start, end


def _in_office_hours(slot_start: datetime, slot_end: datetime) -> bool:
    local_start = slot_start.astimezone(_tz())
    local_end = slot_end.astimezone(_tz())
    if local_start.weekday() not in OFFICE_HOURS_DAYS:
        return False
    day_start, day_end = _office_hours_bounds(local_start)
    return local_start >= day_start and local_end <= day_end


def _overlaps_busy(slot_start: datetime, slot_end: datetime, busy_blocks: List[BusyBlock]) -> bool:
    for b_start, b_end in busy_blocks:
        if b_start.tzinfo is None and slot_start.tzinfo is not None:
            b_start = b_start.replace(tzinfo=slot_start.tzinfo)
        if b_end.tzinfo is None and slot_end.tzinfo is not None:
            b_end = b_end.replace(tzinfo=slot_end.tzinfo)
        if slot_start < b_end and slot_end > b_start:
            return True
    return False


def parse_submitted_slots(submitted_availability_json: Optional[str]) -> List[datetime]:
    """Parses lead-submitted availability datetimes from JSON array strings,
    comma-separated strings, or single date-time strings. A naive (no-offset)
    datetime is assumed to be in OFFICE_HOURS_TZ.
    """
    if not submitted_availability_json:
        return []

    val = submitted_availability_json.strip()
    raw_items = []

    if val.startswith("[") and val.endswith("]"):
        try:
            parsed = json.loads(val)
            if isinstance(parsed, list):
                raw_items = [str(x) for x in parsed]
            else:
                raw_items = [str(parsed)]
        except Exception:
            raw_items = [x.strip() for x in val.strip("[]").split(",") if x.strip()]
    else:
        raw_items = [x.strip() for x in val.split(",") if x.strip()]

    slots = []
    for s in raw_items:
        s_clean = s.strip("'\"")
        dt = None
        for fmt in (
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
        ):
            try:
                dt = datetime.strptime(s_clean, fmt)
                break
            except ValueError:
                pass

        if dt is None:
            try:
                dt = datetime.fromisoformat(s_clean)
            except ValueError:
                continue

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=_tz())
        slots.append(dt)

    return slots


def find_confirmed_slot(
    submitted_slots: List[datetime], busy_blocks: List[BusyBlock]
) -> Optional[Tuple[datetime, datetime]]:
    """Returns the earliest lead-submitted slot that's inside office hours
    and free on the organizer's calendar, or None if none qualify."""
    duration = timedelta(minutes=MEETING_DURATION_MINUTES)
    for start in sorted(submitted_slots):
        end = start + duration
        if _in_office_hours(start, end) and not _overlaps_busy(start, end, busy_blocks):
            return start, end
    return None


def propose_alternate_slots(busy_blocks: List[BusyBlock], after: datetime) -> List[datetime]:
    """Fallback for SCHEDULING_FALLBACK=auto_propose: walks forward from
    `after` in MEETING_DURATION_MINUTES increments, within office hours,
    across AUTO_PROPOSE_LOOKAHEAD_DAYS days, returning up to
    AUTO_PROPOSE_SLOT_COUNT free slots.
    """
    duration = timedelta(minutes=MEETING_DURATION_MINUTES)
    found: List[datetime] = []

    local_after = after.astimezone(_tz())
    day_cursor = local_after

    for _ in range(AUTO_PROPOSE_LOOKAHEAD_DAYS):
        if day_cursor.weekday() in OFFICE_HOURS_DAYS:
            day_start, day_end = _office_hours_bounds(day_cursor)
            slot_cursor = max(day_start, local_after) if day_cursor.date() == local_after.date() else day_start

            while slot_cursor + duration <= day_end and len(found) < AUTO_PROPOSE_SLOT_COUNT:
                if not _overlaps_busy(slot_cursor, slot_cursor + duration, busy_blocks):
                    found.append(slot_cursor)
                slot_cursor += duration

        if len(found) >= AUTO_PROPOSE_SLOT_COUNT:
            break

        day_cursor = (day_cursor + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

    return found
