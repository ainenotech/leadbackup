import os
import re
import hashlib
import hmac
from typing import Optional

import requests

import utils.dns_patch
from utils.microsoft_auth import MS_SENDER_EMAIL, get_graph_headers
from .base import Mailer

GRAPH_BASE = "https://graph.microsoft.com/v1.0"

def sign_tracking_url(token: str, destination_url: str) -> str:
    secret = os.getenv("TRACKING_SIGNING_SECRET")

    if not secret:
        raise RuntimeError("TRACKING_SIGNING_SECRET is not configured")

    message = f"{token}|{destination_url}".encode("utf-8")

    return hmac.new(
        secret.encode("utf-8"),
        message,
        hashlib.sha256,
    ).hexdigest()


class OutlookMailer(Mailer):
    """Mailer implementation using Microsoft Graph's /sendMail endpoint,
    sending on behalf of the shared support mailbox (MS_SENDER_EMAIL, e.g.
    support@nenotechnology.com) via app-only Graph credentials.
    """

    def send_email(self, to_email: str, subject: str, body: str, token: Optional[str] = None) -> str:
        # Resolve token for live open and click tracking
        clean_body = (body or "").strip()
        api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")

        if not token:
            try:
                from Backend.db import SessionLocal
                from Backend.models import CampaignLog
                from sqlalchemy import func

                _s = SessionLocal()
                _row = (
                    _s.query(CampaignLog.token)
                    .filter(func.lower(CampaignLog.email) == to_email.strip().lower())
                    .first()
                )
                if _row and _row[0]:
                    token = _row[0]
                _s.close()
            except Exception:
                token = None

        # Target Microsoft Bookings consultation URL
        target_booking = os.getenv(
            "BOOKING_FORM_URL",
            "https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled",
        )

        # 1. Clean any existing localhost hrefs in the email body
        clean_body = re.sub(
            r'href=["\']https?://(?:localhost|127\.0\.0\.1)(?::\d+)?(?:/[^"\']*)?["\']',
            f'href="{target_booking}"',
            clean_body,
        )
        # 2. Clean any /form?token= links to point directly to the booking form
        clean_body = re.sub(
            r'href=["\']https?://[^/\"\'\s]+/form\?token=[^"\'\s]*["\']',
            f'href="{target_booking}"',
            clean_body,
        )

        # Check if api_base_url is a real public HTTPS URL (e.g. custom domain or public host)
        has_public_tunnel = (
            bool(api_base_url)
            and api_base_url.lower().startswith("https://")
            and not any(h in api_base_url.lower() for h in ("localhost", "127.0.0.1", "0.0.0.0", "::1"))
        )

        # Rewrite links to route through click tracking ONLY if a public HTTPS host is configured
        # Otherwise, keep Microsoft Bookings links 100% direct and reliable for all recipients!
        if token and has_public_tunnel:
            def _rewrite_link(m):
                orig_url = m.group(1)
                if "track/click" in orig_url or "track/unsubscribe" in orig_url or orig_url.startswith("mailto:"):
                    return f'href="{orig_url}"'
                import urllib.parse
                encoded = urllib.parse.quote(orig_url, safe="")
                signature = sign_tracking_url(token, orig_url)

                return (
                    f'href="{api_base_url}/api/track/click/'
                    f'{token}?url={encoded}&sig={signature}"'
                )

            clean_body = re.sub(r'href=["\'](https?://[^"\']+)["\']', _rewrite_link, clean_body)

        # Prepare tracking pixel & unsubscribe footer
        sender_email = os.getenv("MS_SENDER_EMAIL", "support@nenotechnology.com")
        pixel_img = ""
        if token and api_base_url:
            pixel_url = f"{api_base_url}/api/track/open/{token}"
            pixel_img = f'<img src="{pixel_url}" width="1" height="1" alt="" style="display:none;max-height:0px;max-width:0px;opacity:0;border:none;overflow:hidden;" />'

        if token and has_public_tunnel:
            unsub_url = f"{api_base_url}/api/track/unsubscribe/{token}"
            unsub_link = f'<a href="{unsub_url}" style="color: #64748B; text-decoration: underline;">unsubscribe safely here</a>'
        else:
            unsub_mailto = f"mailto:{sender_email}?subject=Unsubscribe%20Request"
            unsub_link = f'<a href="{unsub_mailto}" style="color: #64748B; text-decoration: underline;">unsubscribe safely here</a>'

        telemetry_html = f"""
        <div style="margin-top: 24px; padding-top: 14px; border-top: 1px solid #E2E8F0; font-size: 11px; color: #94A3B8;">
            If you no longer wish to receive updates from Nenotechnology, you can {unsub_link}.
        </div>
        {pixel_img}
        """

        # Construct an HTML body so hyperlinks and rich email templates render perfectly.
        if clean_body.startswith(("<div", "<table", "<html", "<!DOCTYPE", "<body")):
            if "<html" in clean_body.lower():
                html_content = clean_body.replace("</body>", f"{telemetry_html}</body>")
            else:
                html_content = f"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <!--[if mso]>
  <style type="text/css">
    body, table, td, p, div, a, li, blockquote {{
      font-family: Arial, Helvetica, sans-serif !important;
      mso-line-height-rule: exactly !important;
    }}
    p, div {{
      margin: 0 0 11pt 0 !important;
      margin-top: 0 !important;
      mso-margin-top-alt: 0pt !important;
      mso-margin-bottom-alt: 11pt !important;
      padding: 0 !important;
    }}
  </style>
  <![endif]-->
  <style type="text/css">
    html, body {{ margin: 0 !important; padding: 0 !important; }}
    p {{ margin: 0 0 11px 0 !important; line-height: 1.45 !important; }}
    a {{ color: #0f62fe; }}
  </style>
</head>
<body style="margin: 0; padding: 0; background-color: #ffffff; font-family: Arial, Helvetica, sans-serif; font-size: 15px; line-height: 1.45; color: #1a1a1a;">
{clean_body}
{telemetry_html}
</body>
</html>"""
        else:
            has_html = "<a " in clean_body or "<br" in clean_body or "<p>" in clean_body
            paragraphs = clean_body.replace("\r\n", "\n").split("\n\n")
            html_paragraphs = []
            for p in paragraphs:
                p_clean = p.strip()
                if p_clean:
                    p_html = p_clean.replace("\n", "<br>")
                    if not has_html:
                        p_html = re.sub(
                            r'\[([^\]]+)\]\((https?://[^\s\)]+)\)',
                            r'<a href="\2" style="color: #0f62fe; text-decoration: underline; font-weight: 600;">\1</a>',
                            p_html,
                        )
                    html_paragraphs.append(f"<p style='margin: 0 0 11px 0; margin-top: 0; margin-bottom: 11px; padding: 0; line-height: 1.45;'>{p_html}</p>")

            html_content = f"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style type="text/css">
    p {{ margin: 0 0 11px 0 !important; line-height: 1.45 !important; }}
  </style>
</head>
<body style="margin: 0; padding: 0; background-color: #ffffff; font-family: Arial, Helvetica, sans-serif; font-size: 15px; line-height: 1.45; color: #1a1a1a;">
{"".join(html_paragraphs)}
{telemetry_html}
</body>
</html>"""

        payload = {
            "message": {
                "subject": subject,
                "body": {"contentType": "HTML", "content": html_content},
                "toRecipients": [{"emailAddress": {"address": to_email}}],
            },
            "saveToSentItems": "true",
        }

        resp = requests.post(
            f"{GRAPH_BASE}/users/{MS_SENDER_EMAIL}/sendMail",
            headers=get_graph_headers(),
            json=payload,
            timeout=30,
        )
        if resp.status_code >= 300:
            raise RuntimeError(
                f"Microsoft Graph sendMail failed ({resp.status_code}): {resp.text}"
            )

        # Graph's /sendMail returns 202 Accepted with an empty body (no
        # message id), unlike Gmail's send call — return a synthetic id so
        # any caller that logs "message id" still gets a stable value.
        return f"graph-sendmail-{to_email}"


def get_mailer() -> OutlookMailer:
    """Factory function returning the OutlookMailer instance."""
    return OutlookMailer()

