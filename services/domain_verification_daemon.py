"""Domain Verification Daemon — background SES verification polling.

Periodically checks AWS SES for domain identity and DKIM verification
status. Updates local PostgreSQL records so the dashboard reflects
real-time verification progress without repeated manual clicks.

Runs as a background thread started from the FastAPI startup event.
"""

import logging
import os
import threading
import time
from datetime import datetime, timezone

logger = logging.getLogger("domain_verification_daemon")

_CHECK_INTERVAL = int(os.getenv("DOMAIN_CHECK_INTERVAL_SECONDS", "300"))  # 5 minutes default


class DomainVerificationDaemon:
    """Singleton background thread that polls SES for pending domain verifications."""

    _thread: threading.Thread | None = None
    _stop_event = threading.Event()
    _last_run: datetime | None = None
    _lock = threading.Lock()

    @classmethod
    def is_running(cls) -> bool:
        return cls._thread is not None and cls._thread.is_alive()

    @classmethod
    def start(cls, interval_seconds: int | None = None):
        """Start the verification daemon if not already running."""
        if cls.is_running():
            return

        interval = interval_seconds or _CHECK_INTERVAL
        cls._stop_event.clear()

        def _run():
            logger.info(
                "[DomainVerificationDaemon] Started — checking every %d seconds", interval
            )
            while not cls._stop_event.is_set():
                try:
                    cls._check_pending_domains()
                    cls._last_run = datetime.now(timezone.utc)
                except Exception as exc:
                    logger.error("[DomainVerificationDaemon] Check cycle error: %s", exc)

                cls._stop_event.wait(timeout=interval)

            logger.info("[DomainVerificationDaemon] Stopped")

        cls._thread = threading.Thread(target=_run, daemon=True, name="domain-verify-daemon")
        cls._thread.start()

    @classmethod
    def stop(cls):
        """Signal the daemon to stop."""
        cls._stop_event.set()
        if cls._thread:
            cls._thread.join(timeout=10)
            cls._thread = None

    @classmethod
    def get_stats(cls) -> dict:
        return {
            "running": cls.is_running(),
            "last_run": cls._last_run.isoformat() if cls._last_run else None,
            "interval_seconds": _CHECK_INTERVAL,
        }

    @classmethod
    def _check_pending_domains(cls):
        """Load domains that need verification and check SES status."""
        from Backend.db import SessionLocal
        from Backend.domain_models import OrgSendingDomain, OrgDomainRecord, OrgDomainCheckHistory
        from Backend.sender_models import SenderAccount

        db = SessionLocal()
        try:
            # Find domains in pending/blocked status (exclude paused — admin disabled)
            pending_domains = db.query(OrgSendingDomain).filter(
                OrgSendingDomain.status.in_(["pending", "blocked"]),
            ).all()

            if not pending_domains:
                return

            logger.info(
                "[DomainVerificationDaemon] Checking %d pending domain(s)", len(pending_domains)
            )

            from services.domain_auth_service import is_mock_provider, _get_provider
            from services.dns_health import full_dns_check, verify_mail_from_mx, verify_mail_from_spf
            import uuid

            provider = _get_provider()
            now = datetime.now(timezone.utc)

            for domain_rec in pending_domains:
                try:
                    # 1. Query SES for current status
                    provider_result = provider.get_identity_status(domain_rec.domain)

                    # 2. Check DKIM status from SES
                    provider_dkim_verified = provider_result.dkim_status in ("success",)

                    # 3. Run local DNS checks on stored records
                    records = db.query(OrgDomainRecord).filter(
                        OrgDomainRecord.domain_id == domain_rec.id,
                    ).all()

                    dkim_records = [
                        {"host": r.host, "value": r.value}
                        for r in records if r.purpose == "dkim"
                    ]

                    dns_report = None
                    all_dkim_verified = True
                    try:
                        dns_report = full_dns_check(domain_rec.domain, dkim_records)

                        for rec in records:
                            if rec.purpose == "dkim":
                                matching = next(
                                    (d for d in dns_report.dkim_checks if d.host == rec.host),
                                    None,
                                )
                                if matching:
                                    rec.status = "verified" if matching.verified else "pending"
                                    rec.last_result = matching.error or "Verified"
                                    rec.last_checked_at = now
                                    if not matching.verified:
                                        all_dkim_verified = False
                                else:
                                    all_dkim_verified = False

                            elif rec.purpose == "mail_from_mx":
                                mx_result = verify_mail_from_mx(rec.host, rec.value)
                                rec.status = "verified" if mx_result.get("verified") else "pending"
                                rec.last_result = mx_result.get("error", "Verified")
                                rec.last_checked_at = now

                            elif rec.purpose == "mail_from_spf":
                                spf_result = verify_mail_from_spf(rec.host)
                                rec.status = "verified" if spf_result.get("verified") else "pending"
                                rec.last_result = spf_result.get("error", "Verified")
                                rec.last_checked_at = now

                    except Exception as dns_exc:
                        logger.warning(
                            "[DomainVerificationDaemon] DNS check error for %s: %s",
                            domain_rec.domain, dns_exc
                        )
                        all_dkim_verified = False

                    # 4. Update domain status
                    old_status = domain_rec.status
                    if provider_dkim_verified or all_dkim_verified:
                        domain_rec.status = "ready"
                        domain_rec.verified_at = now
                        domain_rec.claim_expires_at = None
                        domain_rec.last_error = None

                        # Also update sender accounts for this domain
                        senders = db.query(SenderAccount).filter(
                            SenderAccount.domain_id == domain_rec.id,
                        ).all()
                        for sender in senders:
                            sender.ses_identity_status = "ready"
                            # If sending was blocked only due to SES, update it
                            if sender.sending_status == "blocked" and sender.enabled:
                                if sender.provider == "ses_only" or sender.mailbox_connection_status == "connected":
                                    sender.sending_status = "ready"

                        if old_status != "ready":
                            logger.info(
                                "[DomainVerificationDaemon] ✓ Domain %s VERIFIED (was %s)",
                                domain_rec.domain, old_status
                            )
                    else:
                        # Still pending — record the error for display
                        error_parts = []
                        if not provider_dkim_verified:
                            error_parts.append(f"SES DKIM: {provider_result.dkim_status}")
                        if not all_dkim_verified:
                            error_parts.append("DNS DKIM records not yet detected")
                        domain_rec.last_error = "; ".join(error_parts)

                    domain_rec.last_checked_at = now

                    # 5. Save check history
                    results_snapshot = {
                        "provider_dkim_status": provider_result.dkim_status,
                        "provider_verification": provider_result.verification_status,
                        "provider_mail_from": provider_result.mail_from_status,
                        "dns_dkim_all_verified": all_dkim_verified,
                        "auto_check": True,
                    }
                    db.add(OrgDomainCheckHistory(
                        id=str(uuid.uuid4()),
                        domain_id=domain_rec.id,
                        checked_at=now,
                        results=results_snapshot,
                        triggered_by="system_daemon",
                    ))

                    db.commit()

                except Exception as exc:
                    db.rollback()
                    logger.error(
                        "[DomainVerificationDaemon] Error checking domain %s: %s",
                        domain_rec.domain, exc
                    )

        except Exception as exc:
            logger.error("[DomainVerificationDaemon] Session error: %s", exc)
        finally:
            db.close()
