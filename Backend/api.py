import os
import re
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from .db import Base, SessionLocal, engine, init_db
from .models import CampaignLog

load_dotenv()

SERVER_START_TIME = datetime.now(timezone.utc)

# Initialize DB schema & migrations
init_db()

app = FastAPI(title="AINeotechnology — Lead Outreach & Analytics API")


@app.on_event("startup")
def start_background_services():
    # 1. Start continuous inbound reply monitoring daemon
    try:
        from reply_worker import ReplyDaemonManager
        if not ReplyDaemonManager.is_running():
            ReplyDaemonManager.start(interval_seconds=15)
    except Exception as e:
        print(f"[API Startup Warning] Could not start ReplyDaemonManager: {e}")

    # 2. Start Render Keep-Alive Daemon to prevent 15-minute idle spin-down
    try:
        from .keepalive import RenderKeepAliveDaemon
        if not RenderKeepAliveDaemon.is_running():
            RenderKeepAliveDaemon.start(interval_minutes=9)
    except Exception as e:
        print(f"[API Startup Warning] Could not start RenderKeepAliveDaemon: {e}")


@app.get("/logo-dark.png")
@app.get("/logo.png")
@app.get("/static/logo-dark.png")
@app.get("/static/logo.png")
def get_logo_image():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logo_path = os.path.join(root_dir, "logo-dark.png")
    if os.path.exists(logo_path):
        return FileResponse(logo_path, media_type="image/png")
    raise HTTPException(status_code=404, detail="Logo not found")


@app.get("/")
def home():
    return {
        "status": "online",
        "service": "Lead Outreach & Analytics API",
        "health_check": "/api/health",
        "realtime_summary": "/api/realtime/summary",
        "realtime_feed": "/api/realtime/feed",
    }


@app.get("/health")
@app.get("/api/health")
@app.head("/health")
@app.head("/api/health")
def health_check():
    """Comprehensive health probe for uptime monitors, Render keep-alive, and system telemetry."""
    import time
    from sqlalchemy import text

    now_utc = datetime.now(timezone.utc)
    uptime_seconds = round((now_utc - SERVER_START_TIME).total_seconds(), 1)

    # 1. Database Connectivity & Latency Probe
    db_status = {"connected": False, "latency_ms": 0.0, "dialect": str(engine.dialect.name)}
    try:
        t0 = time.time()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status["connected"] = True
        db_status["latency_ms"] = round((time.time() - t0) * 1000, 2)
    except Exception as e:
        db_status["error"] = str(e)

    # 2. Reply Daemon status
    reply_daemon_status = {"running": False, "last_run": None}
    try:
        from reply_worker import ReplyDaemonManager
        reply_daemon_status["running"] = ReplyDaemonManager.is_running()
        if ReplyDaemonManager._last_run:
            reply_daemon_status["last_run"] = ReplyDaemonManager._last_run.isoformat()
    except Exception:
        pass

    # 3. Render Keep-Alive Daemon metrics
    keepalive_stats = {}
    try:
        from .keepalive import RenderKeepAliveDaemon
        keepalive_stats = RenderKeepAliveDaemon.get_stats()
    except Exception:
        pass

    return {
        "status": "healthy" if db_status["connected"] else "degraded",
        "service": "Lead Outreach & Analytics API",
        "uptime_seconds": uptime_seconds,
        "server_time_utc": now_utc.isoformat(),
        "database": db_status,
        "reply_daemon": reply_daemon_status,
        "keepalive": keepalive_stats,
        "render_environment": {
            "is_render": bool(os.getenv("RENDER")),
            "service_id": os.getenv("RENDER_SERVICE_ID", ""),
            "instance_id": os.getenv("RENDER_INSTANCE_ID", ""),
            "external_url": os.getenv("RENDER_EXTERNAL_URL", ""),
        },
    }


@app.get("/api/keepalive/ping")
@app.post("/api/keepalive/ping")
def trigger_keepalive_ping():
    """Manual trigger to immediately test or execute a Render keep-alive ping."""
    from .keepalive import RenderKeepAliveDaemon
    result = RenderKeepAliveDaemon.ping_now()
    return result


@app.get("/api/realtime/summary")
def get_realtime_summary():
    """Returns aggregated real-time outreach, engagement, and reply metrics."""
    db = SessionLocal()
    try:
        rows = db.query(CampaignLog).all()
        total_leads = len(rows)
        sent_rows = [r for r in rows if r.status in ("sent", "delivered", "replied", "meeting_booked", "booked")]
        sent_count = len(sent_rows)
        opened_rows = [r for r in rows if getattr(r, "opened", False)]
        opened_count = len(opened_rows)
        total_opens = sum(getattr(r, "open_count", 0) or 0 for r in opened_rows)
        clicked_rows = [r for r in rows if getattr(r, "clicked_link", False)]
        clicked_count = len(clicked_rows)
        total_clicks = sum(getattr(r, "click_count", 0) or 0 for r in clicked_rows)
        replied_rows = [r for r in rows if getattr(r, "reply_received_at", None) or (r.reply_body and r.reply_body.strip())]
        replied_count = len(replied_rows)
        booked_rows = [r for r in rows if getattr(r, "booking_status", "") in ("confirmed", "scheduled", "booked") or getattr(r, "form_filled_at", None)]
        booked_count = len(booked_rows)
        unsubscribed_count = len([r for r in rows if getattr(r, "unsubscribed", False)])
        bounced_count = len([r for r in rows if getattr(r, "bounced", False)])

        def _max_ts(attr):
            valid = [getattr(r, attr) for r in rows if getattr(r, attr, None)]
            return max(valid).isoformat() if valid else None

        latest_open = _max_ts("last_open_at") or _max_ts("first_open_at")
        latest_click = _max_ts("last_click_at") or _max_ts("first_click_at")
        latest_reply = _max_ts("reply_received_at")
        latest_booking = _max_ts("form_filled_at")

        open_rate = round((opened_count / sent_count * 100), 1) if sent_count else 0.0
        click_rate = round((clicked_count / sent_count * 100), 1) if sent_count else 0.0
        reply_rate = round((replied_count / sent_count * 100), 1) if sent_count else 0.0

        return {
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": {
                "total_leads": total_leads,
                "sent": sent_count,
                "opened": opened_count,
                "total_opens": total_opens,
                "clicked": clicked_count,
                "total_clicks": total_clicks,
                "replied": replied_count,
                "booked": booked_count,
                "unsubscribed": unsubscribed_count,
                "bounced": bounced_count,
                "open_rate_pct": open_rate,
                "click_rate_pct": click_rate,
                "reply_rate_pct": reply_rate,
            },
            "latest_events": {
                "latest_open_at": latest_open,
                "latest_click_at": latest_click,
                "latest_reply_at": latest_reply,
                "latest_booking_at": latest_booking,
            },
        }
    finally:
        db.close()


@app.get("/api/realtime/feed")
def get_realtime_feed(limit: int = 25):
    """Returns chronological real-time event feed for live activity streaming."""
    db = SessionLocal()
    events = []
    try:
        rows = db.query(CampaignLog).all()
        now = datetime.now(timezone.utc)

        def _format_relative(dt):
            if not dt:
                return ""
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            secs = max(0, int((now - dt).total_seconds()))
            if secs < 60:
                return f"{secs}s ago"
            mins = secs // 60
            if mins < 60:
                return f"{mins}m ago"
            hours = mins // 60
            if hours < 24:
                return f"{hours}h ago"
            return f"{hours // 24}d ago"

        for r in rows:
            # Open events
            if getattr(r, "opened", False) and getattr(r, "last_open_at", None):
                events.append({
                    "id": f"open_{r.id}",
                    "lead_id": r.lead_id or "",
                    "name": r.name,
                    "email": r.email,
                    "company": r.company or "",
                    "event_type": "email_opened",
                    "badge": "👁️ Opened",
                    "badge_color": "#0284C7",
                    "timestamp": r.last_open_at.isoformat() if hasattr(r.last_open_at, "isoformat") else str(r.last_open_at),
                    "relative_time": _format_relative(r.last_open_at),
                    "details": f"Opened {getattr(r, 'open_count', 1)} times",
                })
            # Click events
            if getattr(r, "clicked_link", False) and getattr(r, "last_click_at", None):
                events.append({
                    "id": f"click_{r.id}",
                    "lead_id": r.lead_id or "",
                    "name": r.name,
                    "email": r.email,
                    "company": r.company or "",
                    "event_type": "link_clicked",
                    "badge": "🔗 Clicked Link",
                    "badge_color": "#2563EB",
                    "timestamp": r.last_click_at.isoformat() if hasattr(r.last_click_at, "isoformat") else str(r.last_click_at),
                    "relative_time": _format_relative(r.last_click_at),
                    "details": f"Clicked {getattr(r, 'click_count', 1)} times",
                })
            # Reply events
            if getattr(r, "reply_received_at", None):
                intent = getattr(r, "reply_intent", "") or "Inquiry"
                events.append({
                    "id": f"reply_{r.id}",
                    "lead_id": r.lead_id or "",
                    "name": r.name,
                    "email": r.email,
                    "company": r.company or "",
                    "event_type": "reply_received",
                    "badge": "💬 Customer Reply",
                    "badge_color": "#7C3AED",
                    "timestamp": r.reply_received_at.isoformat() if hasattr(r.reply_received_at, "isoformat") else str(r.reply_received_at),
                    "relative_time": _format_relative(r.reply_received_at),
                    "details": f"Intent: {intent}",
                })
            # Booking events
            if getattr(r, "form_filled_at", None) or getattr(r, "booking_status", "") in ("confirmed", "scheduled"):
                b_time = getattr(r, "form_filled_at", None) or getattr(r, "created_at", None)
                events.append({
                    "id": f"booking_{r.id}",
                    "lead_id": r.lead_id or "",
                    "name": r.name,
                    "email": r.email,
                    "company": r.company or "",
                    "event_type": "meeting_booked",
                    "badge": "📅 Meeting Booked",
                    "badge_color": "#059669",
                    "timestamp": b_time.isoformat() if hasattr(b_time, "isoformat") else str(b_time),
                    "relative_time": _format_relative(b_time),
                    "details": f"Slot: {getattr(r, 'confirmed_slot', '') or 'Consultation Scheduled'}",
                })

        events.sort(key=lambda x: str(x.get("timestamp") or ""), reverse=True)

        return {
            "status": "success",
            "total_events": len(events),
            "events": events[:limit],
        }
    finally:
        db.close()


# 1x1 Transparent GIF Byte stream for open tracking pixel
TRANSPARENT_GIF_BYTES = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)


@app.get("/api/track/open/{token}")
@app.get("/track/open/{token}")
def track_email_open(token: str):
    """Logs real-time email open and returns invisible 1x1 transparent GIF pixel."""
    from .crud import record_email_open
    from fastapi.responses import Response

    db = SessionLocal()
    try:
        record_email_open(db, token)
    except Exception as e:
        print(f"Error logging email open: {e}")
    finally:
        db.close()

    return Response(
        content=TRANSPARENT_GIF_BYTES,
        media_type="image/gif",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
            "Access-Control-Allow-Origin": "*",
        },
    )


@app.get("/api/track/click/{token}")
@app.get("/track/click/{token}")
def track_link_click(token: str, url: Optional[str] = None):
    """Logs real-time link click event and redirects lead to their destination URL."""
    from .crud import record_link_click
    from fastapi.responses import RedirectResponse

    dest_url = url or os.getenv(
        "BOOKING_FORM_URL",
        "https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled",
    )

    db = SessionLocal()
    try:
        record_link_click(db, token, dest_url)
    except Exception as e:
        print(f"Error logging link click: {e}")
    finally:
        db.close()

    return RedirectResponse(url=dest_url, status_code=302)


@app.get("/api/track/unsubscribe/{token}")
@app.get("/track/unsubscribe/{token}")
def track_unsubscribe(token: str):
    """Logs opt-out request in real-time and renders a clean confirmation page."""
    from .crud import record_unsubscribe
    from fastapi.responses import HTMLResponse

    db = SessionLocal()
    try:
        record_unsubscribe(db, token, reason="Direct link opt-out")
    except Exception as e:
        print(f"Error logging unsubscribe: {e}")
    finally:
        db.close()

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Unsubscribe Confirmed | Nenotechnology</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #F8FAFC; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
            .card { background: white; padding: 40px; border-radius: 12px; border: 1px solid #E2E8F0; box-shadow: 0 4px 12px rgba(0,0,0,0.05); max-width: 460px; text-align: center; }
            h2 { color: #0F172A; margin-bottom: 8px; font-size: 22px; }
            p { color: #64748B; font-size: 14.5px; line-height: 1.5; }
            .badge { display: inline-block; background: #ECFDF5; color: #059669; font-weight: 600; font-size: 12px; padding: 4px 10px; border-radius: 9999px; margin-bottom: 12px; }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="badge">Preferences Updated</div>
            <h2>You Have Been Safely Unsubscribed</h2>
            <p>Your email has been permanently excluded from future outreach sequences from Nenotechnology. Thank you for your time.</p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html, status_code=200)


@app.get("/form")
def consultation_form(token: Optional[str] = None):
    """Logs form visit click and redirects to the consultation scheduling interface."""
    from .crud import record_link_click
    from fastapi.responses import RedirectResponse

    booking_url = os.getenv(
        "BOOKING_FORM_URL",
        "https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled",
    )
    if token:
        db = SessionLocal()
        try:
            record_link_click(db, token, booking_url)
        except Exception as e:
            print(f"Error recording form click: {e}")
        finally:
            db.close()

    return RedirectResponse(url=booking_url, status_code=302)


@app.get("/api/analytics/export/pdf")
def api_export_analytics_pdf():
    """Generates and serves a publication-grade PDF report for all 14 analytics features."""
    import pandas as pd
    from fastapi.responses import Response
    from services.analytics_service import build_comprehensive_analytics
    from services.analytics_export import generate_analytics_pdf

    db = SessionLocal()
    try:
        rows = db.query(CampaignLog).all()
        data_list = [
            {
                "id": r.id,
                "lead_id": r.lead_id or "",
                "name": r.name,
                "email": r.email,
                "company": r.company or "",
                "status": r.status or "drafted",
                "opened": r.opened or False,
                "open_count": r.open_count or 0,
                "first_open_at": r.first_open_at,
                "last_open_at": r.last_open_at,
                "clicked_link": r.clicked_link or False,
                "click_count": r.click_count or 0,
                "clicked_urls": r.clicked_urls or "",
                "sent_at": r.sent_at,
                "reply_received_at": r.reply_received_at,
                "reply_body": r.reply_body or "",
                "reply_intent": r.reply_intent or "",
                "sentiment": r.sentiment or "",
                "engagement_score": r.engagement_score or 0.0,
            }
            for r in rows
        ]
        df_logs = pd.DataFrame(data_list)
    finally:
        db.close()

    analytics_data = build_comprehensive_analytics(df_logs)
    pdf_bytes = generate_analytics_pdf(analytics_data)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"Outreach_Analytics_Report_{timestamp}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Allow-Origin": "*",
        },
    )


@app.get("/api/analytics/export/excel")
def api_export_analytics_excel():
    """Generates and serves a 15-sheet styled Excel workbook for all 14 analytics features."""
    import pandas as pd
    from fastapi.responses import Response
    from services.analytics_service import build_comprehensive_analytics
    from services.analytics_export import generate_analytics_excel

    db = SessionLocal()
    try:
        rows = db.query(CampaignLog).all()
        data_list = [
            {
                "id": r.id,
                "lead_id": r.lead_id or "",
                "name": r.name,
                "email": r.email,
                "company": r.company or "",
                "status": r.status or "drafted",
                "opened": r.opened or False,
                "open_count": r.open_count or 0,
                "first_open_at": r.first_open_at,
                "last_open_at": r.last_open_at,
                "clicked_link": r.clicked_link or False,
                "click_count": r.click_count or 0,
                "clicked_urls": r.clicked_urls or "",
                "sent_at": r.sent_at,
                "reply_received_at": r.reply_received_at,
                "reply_body": r.reply_body or "",
                "reply_intent": r.reply_intent or "",
                "sentiment": r.sentiment or "",
                "engagement_score": r.engagement_score or 0.0,
            }
            for r in rows
        ]
        df_logs = pd.DataFrame(data_list)
    finally:
        db.close()

    analytics_data = build_comprehensive_analytics(df_logs)
    excel_bytes = generate_analytics_excel(analytics_data)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"Outreach_Analytics_Data_{timestamp}.xlsx"

    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Allow-Origin": "*",
        },
    )


