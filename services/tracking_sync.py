import json
import os
import time
import urllib.parse
import urllib.request
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

from Backend.db import SessionLocal
from Backend.crud import (
    record_email_open,
    record_link_click,
    record_unsubscribe,
)
from Backend.models import CampaignLog


load_dotenv()

TRACKING_API_URL = os.getenv(
    "TRACKING_API_URL",
    "https://tracking.nenotechnology.com",
).rstrip("/")

TRACKING_API_KEY = os.getenv("TRACKING_API_KEY")

POLL_INTERVAL_SECONDS = int(
    os.getenv("TRACKING_SYNC_INTERVAL", "15")
)

CURSOR_FILE = Path(
    os.getenv(
        "TRACKING_SYNC_CURSOR_FILE",
        ".tracking_sync_cursor",
    )
)


def load_cursor() -> int:
    """Read the last AWS event ID successfully processed."""
    try:
        return int(CURSOR_FILE.read_text(encoding="utf-8").strip())
    except (FileNotFoundError, ValueError):
        return 0


def save_cursor(event_id: int) -> None:
    """Atomically save the last processed AWS event ID."""
    temp_file = CURSOR_FILE.with_suffix(".tmp")
    temp_file.write_text(str(event_id), encoding="utf-8")
    temp_file.replace(CURSOR_FILE)


def fetch_events(after_id: int) -> list[dict]:
    if not TRACKING_API_KEY:
        raise RuntimeError(
            "TRACKING_API_KEY environment variable is not configured."
        )

    params = urllib.parse.urlencode({
        "after_id": after_id,
        "limit": 500,
    })

    url = f"{TRACKING_API_URL}/api/events?{params}"

    request = urllib.request.Request(
        url,
        headers={
            "X-Tracking-Key": TRACKING_API_KEY,
            "Accept": "application/json",
        },
        method="GET",
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_event_time(value: str | None):
    if not value:
        return datetime.now(timezone.utc)

    dt = datetime.fromisoformat(value)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt


def process_event(event: dict) -> bool:
    """
    Apply one AWS tracking event to the existing local CampaignLog.

    Returns True if the event was handled.
    Returns False when the token does not exist locally.
    """

    event_id = event["id"]
    token = event["token"]
    event_type = event["event_type"]
    target_url = event.get("target_url")
    created_at = parse_event_time(event.get("created_at"))

    db = SessionLocal()

    try:
        campaign = (
            db.query(CampaignLog)
            .filter(CampaignLog.token == token)
            .first()
        )

        if campaign is None:
            print(
                f"[tracking-sync] Event {event_id}: "
                f"token {token!r} does not exist locally. "
                f"Skipping."
            )
            return False

        print(
            f"[tracking-sync] Event {event_id}: "
            f"{event_type} for token {token}"
        )

        # Use the application's existing tracking logic.
        #
        # These functions already update:
        #   opened/open_count/timestamps
        #   clicked_link/click_count/clicked_urls/timestamps
        #   unsubscribe state
        #   engagement score
        #
        if event_type == "open":
            record_email_open(db, token, event_time=created_at)

        elif event_type == "click":
            record_link_click(
                db,
                token,
                target_url,
                event_time=created_at,
            )

        elif event_type == "unsubscribe":
            record_unsubscribe(db, token)

        else:
            print(
                f"[tracking-sync] Event {event_id}: "
                f"unknown event type {event_type!r}. Skipping."
            )
            return False

        return True

    except Exception as exc:
        db.rollback()
        raise

    finally:
        db.close()


def sync_once() -> int:
    """
    Fetch and process all AWS events newer than the saved cursor.

    Returns the number of events processed.
    """

    cursor = load_cursor()

    print(
        f"[tracking-sync] Fetching events after ID {cursor}..."
    )

    events = fetch_events(cursor)

    if not events:
        print("[tracking-sync] No new events.")
        return 0

    processed = 0

    for event in events:
        event_id = int(event["id"])

        # Safety against an unexpected duplicate response.
        if event_id <= cursor:
            continue

        handled = process_event(event)

        # Advance the cursor even when the token isn't present locally.
        #
        # Otherwise an unrelated/old test token would be fetched
        # forever.
        save_cursor(event_id)
        cursor = event_id

        if handled:
            processed += 1

    print(
        f"[tracking-sync] Processed {processed} event(s). "
        f"Cursor is now {cursor}."
    )

    return processed


import threading
from typing import Optional


class TrackingSyncDaemon:
    """Thread-safe background daemon to sync AWS tracking events continuously."""
    _thread: Optional[threading.Thread] = None
    _stop_event: threading.Event = threading.Event()
    _is_running: bool = False

    @classmethod
    def is_running(cls) -> bool:
        return cls._is_running and cls._thread is not None and cls._thread.is_alive()

    @classmethod
    def start(cls, interval_seconds: int = 15):
        if cls.is_running():
            return
        cls._stop_event.clear()
        cls._is_running = True

        def _loop():
            print(f"[TrackingSyncDaemon] Continuous sync daemon started (every {interval_seconds}s from {TRACKING_API_URL}).")
            while not cls._stop_event.is_set():
                try:
                    sync_once()
                except Exception as e:
                    print(f"[TrackingSyncDaemon] Sync error: {e}")
                cls._stop_event.wait(interval_seconds)
            cls._is_running = False
            print("[TrackingSyncDaemon] Stopped.")

        cls._thread = threading.Thread(target=_loop, name="TrackingSyncDaemon", daemon=True)
        cls._thread.start()

    @classmethod
    def stop(cls):
        cls._stop_event.set()
        cls._is_running = False


def main():
    print("[tracking-sync] Starting.")
    print(f"[tracking-sync] API: {TRACKING_API_URL}")
    print(f"[tracking-sync] Poll interval: {POLL_INTERVAL_SECONDS}s")

    while True:
        try:
            sync_once()

        except KeyboardInterrupt:
            print("\n[tracking-sync] Stopped.")
            break

        except Exception as exc:
            print(
                f"[tracking-sync] ERROR: {type(exc).__name__}: {exc}"
            )

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()