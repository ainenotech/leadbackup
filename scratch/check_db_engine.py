import sys, os
sys.path.insert(0, os.path.abspath("."))
from Backend.db import engine, SessionLocal
from Backend.models import CampaignLog

print("Engine URL:", engine.url)
db = SessionLocal()
try:
    count = db.query(CampaignLog).count()
    print("CampaignLog count:", count)
    for r in db.query(CampaignLog).all():
        print(r.id, r.email, r.name, r.company, r.status, r.reply_intent)
finally:
    db.close()
