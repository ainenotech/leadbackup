"""FastAPI endpoints for Sender Accounts (Mail IDs) management.

Provides CRUD endpoints, readiness verification, and test send facilities
for configured sender email addresses.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from .auth_endpoints import get_current_user_and_tenant
from .db import SessionLocal

logger = logging.getLogger("sender_endpoints")

router = APIRouter(prefix="/api/senders", tags=["Sender Accounts / Mail IDs"])


# ─────────────────────────────────────────────────────────────
# PYDANTIC SCHEMAS
# ─────────────────────────────────────────────────────────────

class CreateSenderRequest(BaseModel):
    email: EmailStr
    display_name: Optional[str] = None
    domain_id: Optional[str] = None
    provider: str = "ses_only"  # ses_only | microsoft_365 | google_workspace | smtp_imap
    hourly_limit: Optional[int] = 50
    daily_limit: Optional[int] = 200
    warmup_enabled: bool = False
    notes: Optional[str] = None


class UpdateSenderRequest(BaseModel):
    display_name: Optional[str] = None
    hourly_limit: Optional[int] = None
    daily_limit: Optional[int] = None
    warmup_enabled: Optional[bool] = None
    notes: Optional[str] = None
    enabled: Optional[bool] = None
    provider: Optional[str] = None


class TestSendRequest(BaseModel):
    to_email: EmailStr


# ─────────────────────────────────────────────────────────────
# SENDER ACCOUNT ROUTES
# ─────────────────────────────────────────────────────────────

@router.post("", status_code=status.HTTP_201_CREATED)
def create_sender_endpoint(
    req: CreateSenderRequest,
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    """Create a new sender email account associated with a domain."""
    from services.sender_account_service import create_sender_account

    db = SessionLocal()
    try:
        sender = create_sender_account(
            db=db,
            user_id=context["user_id"],
            org_id=context["org_id"],
            email=str(req.email),
            display_name=req.display_name,
            domain_id=req.domain_id,
            provider=req.provider,
            hourly_limit=req.hourly_limit,
            daily_limit=req.daily_limit,
            warmup_enabled=req.warmup_enabled,
            notes=req.notes,
        )
        return {"status": "success", "data": sender}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error("Error creating sender account: %s", e)
        raise HTTPException(status_code=500, detail="Failed to create sender account")
    finally:
        db.close()


@router.get("")
def list_senders_endpoint(
    domain_id: Optional[str] = None,
    provider: Optional[str] = None,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    """List all sender accounts for the organization with optional filtering."""
    from services.sender_account_service import list_sender_accounts

    db = SessionLocal()
    try:
        senders = list_sender_accounts(
            db=db,
            user_id=context["user_id"],
            org_id=context["org_id"],
            domain_id=domain_id,
            provider=provider,
            status_filter=status_filter,
            search=search,
        )
        return {"status": "success", "data": senders}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        logger.error("Error listing sender accounts: %s", e)
        raise HTTPException(status_code=500, detail="Failed to list sender accounts")
    finally:
        db.close()


@router.get("/{sender_id}")
def get_sender_endpoint(
    sender_id: str,
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    """Get single sender account details and readiness checklist."""
    from services.sender_account_service import get_sender_account

    db = SessionLocal()
    try:
        sender = get_sender_account(
            db=db,
            user_id=context["user_id"],
            org_id=context["org_id"],
            sender_id=sender_id,
        )
        return {"status": "success", "data": sender}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error("Error retrieving sender account: %s", e)
        raise HTTPException(status_code=500, detail="Failed to get sender account")
    finally:
        db.close()


@router.patch("/{sender_id}")
def update_sender_endpoint(
    sender_id: str,
    req: UpdateSenderRequest,
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    """Update sender account configuration, rate limits, or enabled state."""
    from services.sender_account_service import update_sender_account

    db = SessionLocal()
    try:
        sender = update_sender_account(
            db=db,
            user_id=context["user_id"],
            org_id=context["org_id"],
            sender_id=sender_id,
            display_name=req.display_name,
            hourly_limit=req.hourly_limit,
            daily_limit=req.daily_limit,
            warmup_enabled=req.warmup_enabled,
            notes=req.notes,
            enabled=req.enabled,
            provider=req.provider,
        )
        return {"status": "success", "data": sender}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error("Error updating sender account: %s", e)
        raise HTTPException(status_code=500, detail="Failed to update sender account")
    finally:
        db.close()


@router.delete("/{sender_id}")
def delete_sender_endpoint(
    sender_id: str,
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    """Delete a sender account."""
    from services.sender_account_service import delete_sender_account

    db = SessionLocal()
    try:
        delete_sender_account(
            db=db,
            user_id=context["user_id"],
            org_id=context["org_id"],
            sender_id=sender_id,
        )
        return {"status": "success", "message": "Sender account deleted successfully"}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error("Error deleting sender account: %s", e)
        raise HTTPException(status_code=500, detail="Failed to delete sender account")
    finally:
        db.close()


@router.post("/{sender_id}/refresh")
def refresh_sender_endpoint(
    sender_id: str,
    context: Dict[str, Any] = Depends(get_current_user_and_tenant),
):
    """Trigger a live refresh of domain SES readiness and mailbox connection."""
    from services.sender_account_service import refresh_sender_readiness

    db = SessionLocal()
    try:
        result = refresh_sender_readiness(
            db=db,
            user_id=context["user_id"],
            org_id=context["org_id"],
            sender_id=sender_id,
        )
        return {"status": "success", "data": result}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error("Error refreshing sender readiness: %s", e)
        raise HTTPException(status_code=500, detail="Failed to refresh sender status")
    finally:
        db.close()
