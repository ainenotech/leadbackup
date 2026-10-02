from .base import Mailer
from .outlook_mailer import OutlookMailer


def get_mailer() -> OutlookMailer:
    """Returns the Outlook (Microsoft Graph) mailer instance."""
    return OutlookMailer()


def get_mailer_for_org(
    organization_id: str = None,
    from_address: str = None,
) -> Mailer:
    """Returns the appropriate mailer for an organization.

    If the organization has a verified, active sending domain matching
    from_address, returns an SESMailer.  Otherwise returns OutlookMailer
    (existing behavior preserved).

    Args:
        organization_id: The organization's UUID (from verified token).
        from_address: The intended sender email address.

    Returns:
        A Mailer instance ready to send.
    """
    if not organization_id:
        return OutlookMailer()

    try:
        from Backend.db import SessionLocal
        from Backend.domain_models import OrgSendingDomain
        from services.domain_auth_service import CapExceededError, DomainNotReadyError

        # Extract domain from from_address
        if from_address and "@" in from_address:
            from_domain = from_address.split("@")[1].lower()
        else:
            from_domain = None

        db = SessionLocal()
        try:
            # Look for a verified sending domain for this org
            query = db.query(OrgSendingDomain).filter(
                OrgSendingDomain.organization_id == organization_id,
            )

            if from_domain:
                query = query.filter(OrgSendingDomain.domain == from_domain)

            domain_rec = query.first()

            if not domain_rec:
                return OutlookMailer()

            if domain_rec.status == "paused":
                raise DomainNotReadyError(
                    f"Sending domain {domain_rec.domain} is paused: "
                    f"{domain_rec.paused_reason or 'No reason given'}"
                )

            if domain_rec.status not in ("ready", "limited"):
                # Not verified yet — fall back to OutlookMailer
                return OutlookMailer()

            # Check daily cap
            from services.domain_auth_service import check_send_eligibility
            try:
                check_send_eligibility(db, organization_id, domain_rec.domain)
            except CapExceededError:
                raise  # Let caller handle cap exceeded
            except DomainNotReadyError:
                return OutlookMailer()

            # Build the configuration set name
            cs_name = f"org-{organization_id[:8]}" if len(organization_id) >= 8 else f"org-{organization_id}"

            # Determine from address
            effective_from = from_address or f"{domain_rec.from_local_part}@{domain_rec.domain}"

            from .ses_mailer import SESMailer
            return SESMailer(
                from_address=effective_from,
                from_name=domain_rec.from_name or "",
                reply_to=domain_rec.reply_to,
                configuration_set=cs_name,
                domain_id=domain_rec.id,
            )

        finally:
            db.close()

    except ImportError:
        return OutlookMailer()
    except Exception as exc:
        # If it's a known domain error, re-raise
        from services.domain_auth_service import CapExceededError, DomainNotReadyError
        if isinstance(exc, (CapExceededError, DomainNotReadyError)):
            raise
        # For any unexpected error, fall back safely
        return OutlookMailer()


__all__ = ["Mailer", "get_mailer", "get_mailer_for_org", "OutlookMailer"]

