import os
import hashlib
import hmac
from fastapi import FastAPI, Request, Depends, HTTPException, Header
from fastapi.responses import Response, RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from urllib.parse import urlparse

from .database import Base, engine, get_db
from .models import TrackingEvent


app = FastAPI(
    title="Neno Tracking Service",
    version="1.0.0",
)


# Create database tables when the service starts.
Base.metadata.create_all(bind=engine)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "neno-tracking-service",
    }


def record_event(
    db: Session,
    token: str,
    event_type: str,
    request: Request,
    target_url: str | None = None,
):
    from datetime import datetime, timezone, timedelta

    # Debounce rapid duplicate events (e.g. link scanners, prefetch, or double click within 4s)
    threshold = datetime.now(timezone.utc) - timedelta(seconds=4)
    recent = (
        db.query(TrackingEvent)
        .filter(
            TrackingEvent.token == token,
            TrackingEvent.event_type == event_type,
            TrackingEvent.created_at >= threshold,
        )
        .first()
    )
    if recent:
        return recent

    event = TrackingEvent(
        token=token,
        event_type=event_type,
        target_url=target_url,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    db.add(event)
    db.commit()

    return event


@app.get("/api/track/open/{token}")
def track_open(
    token: str,
    request: Request,
    db: Session = Depends(get_db),
):
    record_event(
        db=db,
        token=token,
        event_type="open",
        request=request,
    )

    # Transparent 1x1 GIF.
    transparent_gif = (
        b"GIF89a"
        b"\x01\x00\x01\x00"
        b"\x80\x00\x00"
        b"\x00\x00\x00"
        b"\xff\xff\xff"
        b"!\xf9\x04\x01"
        b"\x00\x00\x00\x00"
        b",\x00\x00\x00\x00"
        b"\x01\x00\x01\x00"
        b"\x00\x02\x02"
        b"\x44\x01"
        b"\x00;"
    )

    return Response(
        content=transparent_gif,
        media_type="image/gif",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.get("/api/track/click/{token}")
def track_click(
    token: str,
    request: Request,
    url: str,
    sig: str,
    db: Session = Depends(get_db),
):
    signing_secret = os.getenv("TRACKING_SIGNING_SECRET")

    if not signing_secret:
        raise HTTPException(
            status_code=500,
            detail="TRACKING_SIGNING_SECRET is not configured",
        )

    message = f"{token}|{url}".encode("utf-8")

    expected_sig = hmac.new(
        signing_secret.encode("utf-8"),
        message,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(sig, expected_sig):
        raise HTTPException(
            status_code=403,
            detail="Invalid tracking signature",
        )

    parsed = urlparse(url)

    # Only allow normal HTTPS/HTTP destinations.
    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(
            status_code=400,
            detail="Invalid destination URL",
        )

    record_event(
        db=db,
        token=token,
        event_type="click",
        request=request,
        target_url=url,
    )

    return RedirectResponse(
        url=url,
        status_code=302,
    )


@app.get("/api/track/unsubscribe/{token}")
def track_unsubscribe(
    token: str,
    request: Request,
    db: Session = Depends(get_db),
):
    record_event(
        db=db,
        token=token,
        event_type="unsubscribe",
        request=request,
    )

    return HTMLResponse(
        """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Unsubscribed</title>
        </head>
        <body>
            <h2>You have been unsubscribed.</h2>
            <p>You will no longer receive these emails.</p>
        </body>
        </html>
        """
    )


@app.get("/api/events")
def get_events(
    after_id: int = 0,
    limit: int = 100,
    x_tracking_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    expected_key = os.getenv("TRACKING_API_KEY")

    if not expected_key:
        raise HTTPException(
            status_code=500,
            detail="TRACKING_API_KEY is not configured",
        )

    if x_tracking_key != expected_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid tracking API key",
        )

    limit = min(max(limit, 1), 500)

    events = (
        db.query(TrackingEvent)
        .filter(TrackingEvent.id > after_id)
        .order_by(TrackingEvent.id.asc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": event.id,
            "token": event.token,
            "event_type": event.event_type,
            "target_url": event.target_url,
            "ip_address": event.ip_address,
            "user_agent": event.user_agent,
            "created_at": event.created_at.isoformat(),
        }
        for event in events
    ]