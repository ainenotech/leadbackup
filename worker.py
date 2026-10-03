import os

from dotenv import load_dotenv

load_dotenv()

from Agent.graph import build_graph
from Backend.crud import already_contacted, create_pending_entry, mark_failed, mark_sent
from Backend.db import SessionLocal, init_db
from Email import get_mailer, get_mailer_for_org
from leads import load_stale_leads
from utils.token import generate_token
import itertools
from Backend.channels_models import OrgMailConnection
from Backend.domain_models import OrgSendingDomain

init_db()

composer_graph = build_graph()
default_mailer = get_mailer()


def run_campaign():
    campaign_name = os.getenv("CAMPAIGN_NAME", "default_campaign")
    stale_after_days = int(os.getenv("STALE_AFTER_DAYS", "90"))
    require_approval = os.getenv("REQUIRE_HUMAN_APPROVAL", "true").lower() in ["true", "1", "yes"]

    leads = load_stale_leads(stale_after_days)
    print(f"Found {len(leads)} stale leads")

    db = SessionLocal()
    
    org_id = os.getenv("ORG_ID")
    if not org_id:
        print("WARNING: ORG_ID not set. Autonomous multi-tenant dispatch will fail.")
        
    active_senders = []
    if org_id:
        conns = db.query(OrgMailConnection).filter(
            OrgMailConnection.organization_id == org_id,
            OrgMailConnection.status == "active"
        ).all()
        for c in conns:
            active_senders.append(c.email)
            
        doms = db.query(OrgSendingDomain).filter(
            OrgSendingDomain.organization_id == org_id,
            OrgSendingDomain.status.in_(["ready", "limited"])
        ).all()
        for d in doms:
            active_senders.append(f"{d.from_local_part or 'hello'}@{d.domain}")
            
    if active_senders:
        print(f"Found {len(active_senders)} active sending channels/domains for round-robin.")
    else:
        print("WARNING: No active senders found for this org. Will fallback to default.")
        
    sender_cycle = itertools.cycle(active_senders) if active_senders else None

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
            organization_id=org_id,
        )

        if require_approval:
            drafted_count += 1
            print(f"Drafted email for {lead.email} (Awaiting approval in dashboard)")
        else:
            try:
                entry_org_id = getattr(entry, 'organization_id', None) if entry else None
                from Email import dispatch_outreach_email
                
                if entry_org_id:
                    sender_to_use = next(sender_cycle) if sender_cycle else None
                    success = dispatch_outreach_email(
                        db=db,
                        organization_id=entry_org_id,
                        campaign_name=campaign_name,
                        lead_id=lead.lead_id,
                        to_email=lead.email,
                        subject=result["subject"],
                        body_html=result["body"],
                        requested_sender=sender_to_use
                    )
                else:
                    success = False
                    raise Exception("No organization_id available for autonomous send")
                
                if success:
                    mark_sent(db, entry.id)
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
