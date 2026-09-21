import os

from dotenv import load_dotenv

load_dotenv()

# --- Office hours / timezone ---
# Two open items from the proposal that Phase 3 needs a real value for.
# Defaulted here (not hardcoded into the logic) so they're a one-line .env
# change, not a code change, once you decide differently.
OFFICE_HOURS_TZ = os.getenv("OFFICE_HOURS_TZ", "Asia/Kolkata")
OFFICE_HOURS_START = os.getenv("OFFICE_HOURS_START", "09:00")  # 24h, local to OFFICE_HOURS_TZ
OFFICE_HOURS_END = os.getenv("OFFICE_HOURS_END", "18:00")  # 9 AM to 6 PM
# Weekday numbers, Monday=0 .. Sunday=6. Default Mon-Fri.
OFFICE_HOURS_DAYS = [int(d) for d in os.getenv("OFFICE_HOURS_DAYS", "0,1,2,3,4").split(",") if d != ""]

MEETING_DURATION_MINUTES = int(os.getenv("MEETING_DURATION_MINUTES", "30"))

# How far ahead to pull the support mailbox's free/busy (via Microsoft
# Graph's getSchedule) when checking a lead's submitted slots against the
# calendar.
AVAILABILITY_LOOKAHEAD_DAYS = int(os.getenv("AVAILABILITY_LOOKAHEAD_DAYS", "14"))

# The other open item: what to do when none of the lead's submitted slots
# are both in office hours and free.
#   "auto_propose" (default) — find the next free office-hours slots on the
#     organizer's calendar and email the lead a fresh pick-a-time link.
#   "manual_flag" — leave the row for a human to schedule by hand; no
#     automatic email is sent.
SCHEDULING_FALLBACK = os.getenv("SCHEDULING_FALLBACK", "auto_propose").lower()

AUTO_PROPOSE_LOOKAHEAD_DAYS = int(os.getenv("AUTO_PROPOSE_LOOKAHEAD_DAYS", "7"))
AUTO_PROPOSE_SLOT_COUNT = int(os.getenv("AUTO_PROPOSE_SLOT_COUNT", "3"))
