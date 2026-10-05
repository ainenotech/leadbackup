"""FastAPI endpoints for sending-domain authentication.

All domain management endpoints require authentication and verify the
caller's org membership and owner/admin role in the database (via the
service layer).  The webhook endpoint is public but validates SNS
message signatures cryptographically.
"""

import base64
import hashlib
import json
import logging
import re
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from .auth_endpoints import get_current_user_and_tenant
from .db import SessionLocal

logger = logging.getLogger("domain_endpoints")

router = APIRouter(prefix="/api", tags=["Sending Domain Authentication"])


# ─────────────────────────────────────────────────────────────
# PYDANTIC SCHEMAS
# ─────────────────────────────────────────────────────────────

class RegisterDomainRequest(BaseModel):
    email_address: str
    from_name: Optional[str] = None
    reply_to: Optional[str] = None


class UpdateDomainRequest(BaseModel):
    from_name: Optional[str] = None
    reply_to: Optional[str] = None
    daily_cap: Optional[int] = None


class PauseDomainRequest(BaseModel):
    reason: str = "Manually paused by admin"


# ─────────────────────────────────────────────────────────────
# DOMAIN MANAGEMENT ROUTES (authenticated)
# ─────────────────────────────────────────────────────────────

@router.post("/domains/register")
def register_domain_endpoint(
    req: RegisterDomainRequest,
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    """Register a new sending domain extracted from the given email address."""
    from services.domain_auth_service import register_domain

    db = SessionLocal()
    try:
        result = register_domain(
            db=db,
            user_id=context["user_id"],
            organization_id=context["org_id"],
            email_address=req.email_address,
            from_name=req.from_name,
            reply_to=req.reply_to,
        )
        return {"status": "success", "data": result}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Domain registration failed: %s", e)
        raise HTTPException(status_code=500, detail="Domain registration failed")
    finally:
        db.close()


@router.get("/domains")
def list_domains_endpoint(
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    """List all sending domains for the current organization."""
    from services.domain_auth_service import list_domains

    db = SessionLocal()
    try:
        result = list_domains(
            db=db,
            user_id=context["user_id"],
            organization_id=context["org_id"],
        )
        return {"status": "success", "data": result}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error("Failed to list domains: %s", e)
        raise HTTPException(status_code=500, detail="Failed to list domains")
    finally:
        db.close()


@router.get("/domains/{domain_id}")
def get_domain_endpoint(
    domain_id: str,
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    """Get detailed information about a sending domain."""
    from services.domain_auth_service import get_domain_detail

    db = SessionLocal()
    try:
        result = get_domain_detail(
            db=db,
            user_id=context["user_id"],
            organization_id=context["org_id"],
            domain_id=domain_id,
        )
        return {"status": "success", "data": result}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to get domain: %s", e)
        raise HTTPException(status_code=500, detail="Failed to get domain details")
    finally:
        db.close()


@router.post("/domains/{domain_id}/verify")
def verify_domain_endpoint(
    domain_id: str,
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    """Re-run DNS lookups and fetch provider verification status."""
    from services.domain_auth_service import verify_domain

    db = SessionLocal()
    try:
        result = verify_domain(
            db=db,
            user_id=context["user_id"],
            organization_id=context["org_id"],
            domain_id=domain_id,
        )
        return {"status": "success", "data": result}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Domain verification failed: %s", e)
        raise HTTPException(status_code=500, detail="Verification failed")
    finally:
        db.close()


@router.put("/domains/{domain_id}")
def update_domain_endpoint(
    domain_id: str,
    req: UpdateDomainRequest,
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    """Update editable fields of a sending domain."""
    from services.domain_auth_service import update_domain

    db = SessionLocal()
    try:
        result = update_domain(
            db=db,
            user_id=context["user_id"],
            organization_id=context["org_id"],
            domain_id=domain_id,
            from_name=req.from_name,
            reply_to=req.reply_to,
            daily_cap=req.daily_cap,
        )
        return {"status": "success", "data": result}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.post("/domains/{domain_id}/pause")
def pause_domain_endpoint(
    domain_id: str,
    req: PauseDomainRequest,
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    """Manually pause a sending domain."""
    from services.domain_auth_service import pause_domain

    db = SessionLocal()
    try:
        result = pause_domain(
            db=db,
            user_id=context["user_id"],
            organization_id=context["org_id"],
            domain_id=domain_id,
            reason=req.reason,
        )
        return {"status": "success", "data": result}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.post("/domains/{domain_id}/resume")
def resume_domain_endpoint(
    domain_id: str,
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    """Resume a paused sending domain."""
    from services.domain_auth_service import resume_domain

    db = SessionLocal()
    try:
        result = resume_domain(
            db=db,
            user_id=context["user_id"],
            organization_id=context["org_id"],
            domain_id=domain_id,
        )
        return {"status": "success", "data": result}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.delete("/domains/{domain_id}")
def delete_domain_endpoint(
    domain_id: str,
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    """Delete a sending domain claim and its provider identity."""
    from services.domain_auth_service import delete_domain

    db = SessionLocal()
    try:
        delete_domain(
            db=db,
            user_id=context["user_id"],
            organization_id=context["org_id"],
            domain_id=domain_id,
        )
        return {"status": "success", "message": "Domain deleted successfully"}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.get("/domains/{domain_id}/history")
def get_history_endpoint(
    domain_id: str,
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    """Get verification check history for a domain."""
    from services.domain_auth_service import get_check_history

    db = SessionLocal()
    try:
        result = get_check_history(
            db=db,
            user_id=context["user_id"],
            organization_id=context["org_id"],
            domain_id=domain_id,
        )
        return {"status": "success", "data": result}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        db.close()


@router.get("/domains/{domain_id}/dns-instructions")
def get_instructions_endpoint(
    domain_id: str,
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    """Generate plain-language DNS instructions for IT admin."""
    from services.domain_auth_service import get_dns_instructions

    db = SessionLocal()
    try:
        result = get_dns_instructions(
            db=db,
            user_id=context["user_id"],
            organization_id=context["org_id"],
            domain_id=domain_id,
        )
        return {"status": "success", "data": result}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────
# PUBLIC WEBHOOK (SNS → SES bounce/complaint events)
# ─────────────────────────────────────────────────────────────

def _validate_sns_cert_url(url: str) -> bool:
    """Validate that SigningCertURL belongs to an official AWS SNS domain."""
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return False
    host = parsed.hostname or ""
    # Must match sns.{region}.amazonaws.com
    if not re.match(r'^sns\.[a-z0-9-]+\.amazonaws\.com$', host):
        return False
    if not parsed.path.endswith(".pem"):
        return False
    return True


def _verify_sns_signature(message: Dict) -> bool:
    """Cryptographically verify an SNS message signature.
    Uses the certificate from SigningCertURL (validated above).
    """
    try:
        from cryptography.x509 import load_pem_x509_certificate
        from cryptography.hazmat.primitives.hashes import SHA1, SHA256
        from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
        import requests

        cert_url = message.get("SigningCertURL", "")
        if not _validate_sns_cert_url(cert_url):
            logger.warning("Invalid SigningCertURL: %s", cert_url)
            return False

        # Download certificate (production should cache this)
        resp = requests.get(cert_url, timeout=10)
        if resp.status_code != 200:
            return False

        cert = load_pem_x509_certificate(resp.content)
        public_key = cert.public_key()

        # Build string to sign based on message type
        msg_type = message.get("Type", "")
        if msg_type == "Notification":
            fields = ["Message", "MessageId", "Subject", "Timestamp", "TopicArn", "Type"]
        elif msg_type in ("SubscriptionConfirmation", "UnsubscribeConfirmation"):
            fields = ["Message", "MessageId", "SubscribeURL", "Timestamp", "Token", "TopicArn", "Type"]
        else:
            return False

        string_to_sign = ""
        for field in fields:
            if field in message:
                string_to_sign += f"{field}\n{message[field]}\n"

        signature = base64.b64decode(message.get("Signature", ""))
        sig_version = message.get("SignatureVersion", "1")
        hash_algo = SHA256() if sig_version == "2" else SHA1()

        public_key.verify(
            signature,
            string_to_sign.encode("utf-8"),
            PKCS1v15(),
            hash_algo,
        )
        return True

    except Exception as exc:
        logger.warning("SNS signature verification failed: %s", exc)
        return False


@router.post("/webhooks/ses-events")
async def ses_event_webhook(request: Request):
    """Public webhook for SES bounce/complaint events via SNS.

    Security: Validates SNS message signature and certificate source.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Handle SNS subscription confirmation
    msg_type = body.get("Type", "")

    if msg_type == "SubscriptionConfirmation":
        if not _verify_sns_signature(body):
            raise HTTPException(status_code=403, detail="Invalid signature")
        # Auto-confirm by visiting the SubscribeURL
        subscribe_url = body.get("SubscribeURL", "")
        if subscribe_url:
            try:
                import requests
                requests.get(subscribe_url, timeout=10)
                logger.info("Confirmed SNS subscription: %s", body.get("TopicArn", ""))
            except Exception as exc:
                logger.error("Failed to confirm SNS subscription: %s", exc)
        return {"status": "ok", "message": "Subscription confirmed"}

    if msg_type != "Notification":
        return {"status": "ignored"}

    # Verify signature
    if not _verify_sns_signature(body):
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Parse the SES event from the SNS message
    try:
        ses_message = json.loads(body.get("Message", "{}"))
    except (json.JSONDecodeError, TypeError):
        return {"status": "ignored", "reason": "Invalid message format"}

    event_type = ses_message.get("eventType", "")
    mail_data = ses_message.get("mail", {})

    # Extract the sending domain from the source address
    source = mail_data.get("source", "")
    if "@" in source:
        sending_domain = source.split("@")[1].lower()
    else:
        return {"status": "ignored", "reason": "No source domain"}

    db = SessionLocal()
    try:
        from services.domain_auth_service import record_bounce, record_complaint

        if event_type == "Bounce":
            record_bounce(db, sending_domain)
            logger.info("Recorded bounce for domain %s", sending_domain)
        elif event_type == "Complaint":
            record_complaint(db, sending_domain)
            logger.info("Recorded complaint for domain %s", sending_domain)
        else:
            return {"status": "ignored", "reason": f"Unhandled event type: {event_type}"}

        return {"status": "processed", "event_type": event_type, "domain": sending_domain}
    finally:
        db.close()
