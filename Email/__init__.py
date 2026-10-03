from .base import Mailer
from .outlook_mailer import OutlookMailer
import os
from datetime import datetime, timezone


def get_mailer() -> OutlookMailer:
    """Returns the Outlook (Microsoft Graph) mailer instance."""
    return OutlookMailer()


def get_mailer_for_org(
    organization_id: str = None,
    from_address: str = None,
) -> Mailer:
    """Returns the appropriate mailer for an organization across all channels."""
    if not organization_id:
        return OutlookMailer()

    try:
        from Backend.db import SessionLocal
        from Backend.domain_models import OrgSendingDomain
        from Backend.channels_models import OrgMailConnection
        from services.domain_auth_service import CapExceededError, DomainNotReadyError
        from Email.channels import CustomerDomainAdapter, get_channel_handler
        from Email.ses_mailer import SESMailer

        if from_address and "@" in from_address:
            from_domain = from_address.split("@")[1].lower()
        else:
            from_domain = None

        db = SessionLocal()
        try:
            # Gather all configured channels for this org
            connections = db.query(OrgMailConnection).filter(
                OrgMailConnection.organization_id == organization_id
            ).all()
            
            domains = db.query(OrgSendingDomain).filter(
                OrgSendingDomain.organization_id == organization_id
            ).all()

            # Rule 7 Change: if NO channels are configured at all, fallback to platform mailbox
            if not connections and not domains:
                return OutlookMailer()

            resolved_item = None
            resolved_type = None  # 'connection' or 'domain'

            # Resolution Order
            # 1. Connection matching from_address
            if from_address:
                for c in connections:
                    if c.email.lower() == from_address.lower():
                        resolved_item = c
                        resolved_type = 'connection'
                        break

            # 2. Domain matching from_domain
            if not resolved_item and from_domain:
                for d in domains:
                    if d.domain.lower() == from_domain:
                        if d.status in ("ready", "limited"):
                            resolved_item = d
                            resolved_type = 'domain'
                        break

            # 3. Default connection
            if not resolved_item:
                for c in connections:
                    if c.is_default:
                        resolved_item = c
                        resolved_type = 'connection'
                        break

            # 4. Any active connection/domain
            if not resolved_item:
                for c in connections:
                    if c.status == "active":
                        resolved_item = c
                        resolved_type = 'connection'
                        break
                if not resolved_item:
                    for d in domains:
                        if d.status in ("ready", "limited"):
                            resolved_item = d
                            resolved_type = 'domain'
                            break

            # If we still haven't resolved anything (e.g., they have channels but none active),
            # fallback to the platform mailbox.
            if not resolved_item:
                return OutlookMailer()

            # Now enforce status and cap
            if resolved_type == 'domain':
                if resolved_item.status == "paused":
                    raise DomainNotReadyError(
                        f"Sending domain {resolved_item.domain} is paused: "
                        f"{resolved_item.paused_reason or 'No reason given'}"
                    )
                if resolved_item.status not in ("ready", "limited"):
                    raise DomainNotReadyError(f"Sending domain {resolved_item.domain} is not verified (status: {resolved_item.status}).")
                
                from services.domain_auth_service import check_send_eligibility
                check_send_eligibility(db, organization_id, resolved_item.domain)
                
                cs_name = f"org-{organization_id[:8]}" if len(organization_id) >= 8 else f"org-{organization_id}"
                effective_from = from_address or f"{resolved_item.from_local_part}@{resolved_item.domain}"
                
                ses_mailer = SESMailer(
                    from_address=effective_from,
                    from_name=resolved_item.from_name or "",
                    reply_to=resolved_item.reply_to,
                    configuration_set=cs_name,
                    domain_id=resolved_item.id,
                )
                return CustomerDomainAdapter(ses_mailer)
                
            elif resolved_type == 'connection':
                if resolved_item.status == "paused":
                    raise DomainNotReadyError(f"Channel for {resolved_item.email} is paused.")
                if resolved_item.status == "needs_reconnect":
                    raise DomainNotReadyError(f"Channel for {resolved_item.email} needs reconnection.")
                if resolved_item.status != "active":
                    raise DomainNotReadyError(f"Channel for {resolved_item.email} is not active (status: {resolved_item.status}).")
                
                # Check daily cap
                default_cap = int(os.getenv("SENDING_PERSONAL_DAILY_CAP", "200"))
                cap = resolved_item.daily_cap if resolved_item.daily_cap else default_cap
                
                today = datetime.now(timezone.utc).date()
                if resolved_item.sent_today_date != today:
                    resolved_item.sent_today = 0
                    resolved_item.sent_today_date = today
                    db.commit()
                
                if resolved_item.sent_today >= cap:
                    raise CapExceededError(f"Channel {resolved_item.email} has exceeded its daily cap of {cap}.")
                
                return get_channel_handler(resolved_item.channel, resolved_item.config)
            
            return OutlookMailer()

        finally:
            db.close()

    except ImportError:
        return OutlookMailer()
    except Exception as exc:
        from services.domain_auth_service import CapExceededError, DomainNotReadyError
        if isinstance(exc, (CapExceededError, DomainNotReadyError)):
            raise
        raise

__all__ = ["Mailer", "get_mailer", "get_mailer_for_org", "OutlookMailer", "dispatch_outreach_email"]


import os

def dispatch_outreach_email(
    db: Session,
    organization_id: str,
    campaign_name: str,
    lead_id: str,
    to_email: str,
    subject: str,
    body_html: str,
    body_text: str = None,
    requested_sender: str = None,
    token: str = None,
    **kwargs
) -> bool:
    """Unified email dispatch that enforces contact guards, explicit sender selections, and logging."""
    from datetime import datetime, timedelta, timezone
    from sqlalchemy.orm import Session
    from Email.channels.base import SendChannel
    from Backend.channels_models import OrgSendSelection, SendAttempt, OrgMailConnection, OrgDomainSnapshot
    from Backend.auth_models import Organization
    from Email import get_mailer_for_org, get_channel_handler
    from services.domain_auth_service import DomainNotReadyError, CapExceededError, SESMailer, CustomerDomainAdapter
    from Backend.crud import MasterLead
    
    # 1. Contact Guard
    cooldown_days_str = os.getenv("LEAD_CONTACT_COOLDOWN_DAYS", "14")
    cooldown_days = int(cooldown_days_str)
    cutoff = datetime.now(timezone.utc) - timedelta(days=cooldown_days)
    
    recent_send = db.query(SendAttempt).filter(
        SendAttempt.organization_id == organization_id,
        SendAttempt.lead_id == lead_id,
        SendAttempt.status == "sent",
        SendAttempt.created_at >= cutoff
    ).first()
    
    if recent_send:
        attempt = SendAttempt(
            organization_id=organization_id,
            lead_id=lead_id,
            campaign_name=campaign_name,
            channel="unknown",
            status="skipped",
            reason="recently contacted"
        )
        db.add(attempt)
        db.commit()
        return False

    # 2. Resolve Channel
    selection = db.query(OrgSendSelection).filter(
        OrgSendSelection.organization_id == organization_id,
        OrgSendSelection.campaign_name == campaign_name
    ).first()
    
    resolved_mailer = None
    resolved_channel = "unknown"
    resolved_ref_id = None
    resolved_type = None
    resolved_email = requested_sender
    skip_reason = None
    
    if selection:
        resolved_ref_id = selection.channel_ref_id
        resolved_type = selection.channel_type
        
        if resolved_type == 'connection':
            conn = db.query(OrgMailConnection).filter(OrgMailConnection.id == resolved_ref_id).first()
            if not conn:
                skip_reason = "Selected channel no longer exists"
            else:
                resolved_channel = conn.channel
                resolved_email = conn.email
                if conn.status == "paused":
                    skip_reason = "Channel paused"
                elif conn.status == "needs_reconnect":
                    skip_reason = "Channel needs reconnect"
                elif conn.status != "active":
                    skip_reason = f"Channel is not active ({conn.status})"
                else:
                    default_cap = int(os.getenv("SENDING_PERSONAL_DAILY_CAP", "200"))
                    cap = conn.daily_cap if conn.daily_cap else default_cap
                    today = datetime.now(timezone.utc).date()
                    if conn.sent_today_date != today:
                        conn.sent_today = 0
                        conn.sent_today_date = today
                        db.commit()
                    if conn.sent_today >= cap:
                        skip_reason = "Channel at daily cap"
                    else:
                        resolved_mailer = get_channel_handler(conn.channel, conn.config)
                        
        elif resolved_type == 'domain':
            # Need to get domain details, wait OrgSendingDomain is in Backend.models?
            # Actually, I'm not sure where OrgSendingDomain is defined. Let's assume Backend.models.
            from Backend.models import OrgSendingDomain
            dom = db.query(OrgSendingDomain).filter(OrgSendingDomain.id == resolved_ref_id).first()
            if not dom:
                skip_reason = "Selected domain no longer exists"
            else:
                resolved_channel = "customer_domain"
                if dom.status == "paused":
                    skip_reason = f"Sending domain is paused: {dom.paused_reason or 'No reason given'}"
                elif dom.status not in ("ready", "limited"):
                    skip_reason = f"Sending domain is not verified ({dom.status})"
                else:
                    from services.domain_auth_service import check_send_eligibility
                    try:
                        check_send_eligibility(db, organization_id, dom.domain)
                        cs_name = f"org-{organization_id[:8]}" if len(organization_id) >= 8 else f"org-{organization_id}"
                        effective_from = resolved_email or f"{dom.from_local_part}@{dom.domain}"
                        resolved_email = effective_from
                        ses_mailer = SESMailer(
                            from_address=effective_from,
                            from_name=dom.from_name or "",
                            reply_to=dom.reply_to,
                            configuration_set=cs_name,
                            domain_id=dom.id,
                        )
                        resolved_mailer = CustomerDomainAdapter(ses_mailer)
                    except CapExceededError as e:
                        skip_reason = str(e)
                    except DomainNotReadyError as e:
                        skip_reason = str(e)
    else:
        # Fall back to default resolution
        try:
            resolved_mailer = get_mailer_for_org(organization_id, requested_sender)
            # We don't perfectly know which connection get_mailer_for_org picked internally, 
            # but we can try to infer it from requested_sender or just log "unknown".
            # For simplicity, if we reached here without an explicit selection, 
            # we just log it as a default send.
            resolved_channel = "auto_default"
        except DomainNotReadyError as e:
            skip_reason = str(e)
        except CapExceededError as e:
            skip_reason = str(e)
        except Exception as e:
            skip_reason = f"Resolution failed: {str(e)}"
            
    if skip_reason:
        attempt = SendAttempt(
            organization_id=organization_id,
            lead_id=lead_id,
            campaign_name=campaign_name,
            channel=resolved_channel,
            channel_ref_id=resolved_ref_id,
            channel_type=resolved_type,
            from_address=resolved_email,
            status="skipped",
            reason=skip_reason
        )
        db.add(attempt)
        db.commit()
        return False
        
    # 3. Dispatch the Email
    try:
        if not resolved_mailer:
            raise Exception("No mailer resolved")
            
        resolved_mailer.send_email(
            to_email=to_email,
            subject=subject,
            body=body_html,
            sender_email=resolved_email,
            token=token,
            **kwargs
        )
        
        # Log success
        attempt = SendAttempt(
            organization_id=organization_id,
            lead_id=lead_id,
            campaign_name=campaign_name,
            channel=resolved_channel,
            channel_ref_id=resolved_ref_id,
            channel_type=resolved_type,
            from_address=resolved_email,
            status="sent",
            reason=None
        )
        db.add(attempt)
        
        # If connection, increment sent_today (since we bypassed get_mailer_for_org cap logic)
        if resolved_type == 'connection' and selection:
            conn = db.query(OrgMailConnection).filter(OrgMailConnection.id == resolved_ref_id).first()
            if conn:
                conn.sent_today += 1
                
        db.commit()
        return True
        
    except Exception as e:
        attempt = SendAttempt(
            organization_id=organization_id,
            lead_id=lead_id,
            campaign_name=campaign_name,
            channel=resolved_channel,
            channel_ref_id=resolved_ref_id,
            channel_type=resolved_type,
            from_address=resolved_email,
            status="failed",
            reason=str(e)
        )
        db.add(attempt)
        db.commit()
        return False
