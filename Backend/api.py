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

# Initialize DB schema & migrations
init_db()

app = FastAPI(title="AINeotechnology — Lead Outreach & Analytics API")


@app.on_event("startup")
def start_background_daemon():
    try:
        from reply_worker import ReplyDaemonManager
        if not ReplyDaemonManager.is_running():
            ReplyDaemonManager.start(interval_seconds=15)
    except Exception as e:
        print(f"[API Startup Warning] Could not start ReplyDaemonManager: {e}")


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
    }


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


