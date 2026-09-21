import os
import sys
sys.path.insert(0, os.path.abspath("."))
from Backend.db import SessionLocal
from Backend.models import CampaignLog
from Backend.crud import record_email_open, record_link_click

db = SessionLocal()
lead = db.query(CampaignLog).first()
if not lead:
    print("No lead found to test!")
    sys.exit(1)

test_token = lead.token
initial_opens = lead.open_count or 0
initial_clicks = lead.click_count or 0
print(f"Testing lead: {lead.email} (token: {test_token})")
print(f"Initial opens: {initial_opens}, initial clicks: {initial_clicks}")

# Simulate open tracking
record_email_open(db, test_token)
db.refresh(lead)
print(f"After open tracking -> opened: {lead.opened}, open_count: {lead.open_count}, first_open: {lead.first_open_at}")
assert lead.opened == True
assert lead.open_count == initial_opens + 1

# Simulate click tracking
record_link_click(db, test_token, "https://example.com/test-cta")
db.refresh(lead)
print(f"After click tracking -> clicked_link: {lead.clicked_link}, click_count: {lead.click_count}, clicked_urls: {lead.clicked_urls}")
assert lead.clicked_link == True
assert lead.click_count == initial_clicks + 1
assert "https://example.com/test-cta" in lead.clicked_urls

db.close()
print("All live telemetry tracking verified successfully!")
