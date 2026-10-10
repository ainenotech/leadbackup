import os

from dotenv import load_dotenv

load_dotenv()

from Agent.graph import build_graph
from Backend.crud import already_contacted, create_pending_entry, mark_failed, mark_sent
from Backend.db import SessionLocal, init_db
from Email import get_mailer
from leads import load_stale_leads
from utils.token import generate_token

init_db()

composer_graph = build_graph()
mailer = get_mailer()


def run_campaign():
    campaign_name = os.getenv("CAMPAIGN_NAME", "default_campaign")
    stale_after_days = int(os.getenv("STALE_AFTER_DAYS", "90"))
    require_approval = os.getenv("REQUIRE_HUMAN_APPROVAL", "true").lower() in ["true", "1", "yes"]

    leads = load_stale_leads(stale_after_days)
    print(f"Found {len(leads)} stale leads")

    db = SessionLocal()
    sent_count = 0
    drafted_count = 0
    skipped_count = 0
    failed_count = 0

    for lead in leads:
        if already_contacted(db, campaign_name, lead.lead_id, email=lead.email):
            skipped_count += 1
            continue

        token = generate_token()

        try:
            result = composer_graph.invoke(
                {
                    "lead_id": lead.lead_id,
                    "email": lead.email,
                    "name": lead.name,
                    "company": lead.company,
                    "last_activity_date": lead.last_activity_date,
                    "last_deal_stage": lead.last_deal_stage,
                }
            )
        except Exception as e:
            print(f"Composer failed for lead {lead.lead_id}: {e}")
            failed_count += 1
            continue

        initial_status = "drafted" if require_approval else "pending"

        entry = create_pending_entry(
            db,
            campaign_name=campaign_name,
            lead_id=lead.lead_id,
            email=lead.email,
            name=lead.name,
            company=lead.company,
            token=token,
            subject=result["subject"],
            body=result["body"],
            status=initial_status,
        )

        # Never send to bounced or unsubscribed leads
        if entry.bounced or entry.unsubscribed:
            print(
                f"Skipping {lead.email}: "
                f"{'unsubscribed' if entry.unsubscribed else 'bounced'}"
            )
            continue

        if require_approval:
            drafted_count += 1
            print(f"Drafted email for {lead.email} (Awaiting approval in dashboard)")
        else:
            sender_email = os.getenv("SENDER_EMAIL")
            sender_account_id = None
            if not sender_email:
                try:
                    from Backend.auth_models import Organization
                    org = db.query(Organization).filter(Organization.status == "active").first()
                    if org and org.settings:
                        sender_email = org.settings.get("sender", {}).get("sender_email") or org.settings.get("sender_email")
                except Exception:
                    pass

            if not sender_email:
                try:
                    from Backend.sender_models import SenderAccount
                    first_ready = db.query(SenderAccount).filter(SenderAccount.enabled == True).first()
                    if first_ready:
                        sender_email = first_ready.email
                except Exception:
                    pass

            if sender_email:
                try:
                    from services.sender_account_service import check_sender_eligibility, record_sender_send
                    from Backend.sender_models import SenderAccount
                    sender_rec = db.query(SenderAccount).filter(SenderAccount.email == sender_email.lower().strip()).first()
                    if sender_rec:
                        eligibility = check_sender_eligibility(db, sender_rec.organization_id, sender_rec.id)
                        if not eligibility.get("eligible"):
                            print(f"Skipping {lead.email}: Sender '{sender_email}' not eligible: {eligibility.get('reason')}")
                            mark_failed(db, entry.id, f"Sender not eligible: {eligibility.get('reason')}")
                            failed_count += 1
                            continue
                        sender_account_id = sender_rec.id
                except Exception as se:
                    print(f"Sender eligibility check warning: {se}")

            try:
                mailer.send_email(
                    to_email=lead.email,
                    subject=result["subject"],
                    body=result["body"],
                    token=token,
                    from_email=sender_email,
                )
                mark_sent(db, entry.id)
                if sender_account_id:
                    try:
                        record_sender_send(db, sender_account_id)
                    except Exception:
                        pass
                sent_count += 1
                try:
                    from leads import update_lead_sheet_status
                    from datetime import datetime, timezone
                    update_lead_sheet_status(
                        email=lead.email,
                        status="sent",
                        sent_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                    )
                except Exception:
                    pass
                print(f"Sent email to {lead.email}")
            except Exception as e:
                mark_failed(db, entry.id, str(e))
                failed_count += 1
                print(f"Send failed for {lead.email}: {e}")

    db.close()
    print(
        f"\nDone. drafted={drafted_count} sent={sent_count} skipped(already contacted/drafted)={skipped_count} failed={failed_count}"
    )


if __name__ == "__main__":
    run_campaign()
