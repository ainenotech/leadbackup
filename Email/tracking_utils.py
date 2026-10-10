import os
import re
import hashlib
import hmac
import urllib.parse
from typing import Optional, Tuple


def sign_tracking_url(token: str, destination_url: str) -> str:
    secret = os.getenv("TRACKING_SIGNING_SECRET")
    if not secret:
        secret = "_fFR_zjTPVkx4IATEAI1kvVieW7WkvgFmwG5s2JxlYs"

    message = f"{token}|{destination_url}".encode("utf-8")
    return hmac.new(
        secret.encode("utf-8"),
        message,
        hashlib.sha256,
    ).hexdigest()


def prepare_tracked_email_bodies(
    body: str,
    token: Optional[str] = None,
    sender_email: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Enriches email body (HTML or plain text) with:
    1. Booking URL redirects.
    2. Rewritten click tracking links (via TRACKING_API_URL).
    3. An invisible 1x1 open tracking pixel.
    4. An unsubscribe link.
    Returns (html_body, text_body).
    """
    clean_body = (body or "").strip()
    api_base_url = os.getenv("TRACKING_API_URL", "https://tracking.nenotechnology.com").rstrip("/")
    target_booking = os.getenv(
        "BOOKING_FORM_URL",
        "https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled",
    )
    sender = sender_email or os.getenv("SES_FROM_EMAIL", "support@nenotechnology.com")

    # 1. Clean localhost URLs to point to booking URL
    clean_body = re.sub(
        r'href=["\']https?://(?:localhost|127\.0\.0\.1)(?::\d+)?(?:/[^"\']*)?["\']',
        f'href="{target_booking}"',
        clean_body,
    )
    clean_body = re.sub(
        r'href=["\']https?://[^/\"\'\s]+/form\?token=[^"\'\s]*["\']',
        f'href="{target_booking}"',
        clean_body,
    )

    has_public_tracking = (
        bool(api_base_url)
        and api_base_url.lower().startswith("https://")
        and not any(h in api_base_url.lower() for h in ("localhost", "127.0.0.1", "0.0.0.0", "::1"))
    )

    # 2. Rewrite links for click tracking if token and public tracking API are available
    if token and has_public_tracking:
        def _rewrite_link(m):
            orig_url = m.group(1)
            if "track/click" in orig_url or "track/unsubscribe" in orig_url or orig_url.startswith("mailto:"):
                return f'href="{orig_url}"'
            encoded = urllib.parse.quote(orig_url, safe="")
            sig = sign_tracking_url(token, orig_url)
            return f'href="{api_base_url}/api/track/click/{token}?url={encoded}&sig={sig}"'

        clean_body = re.sub(r'href=["\'](https?://[^"\']+)["\']', _rewrite_link, clean_body)

    # 3. Tracking pixel & unsubscribe footer
    pixel_img = ""
    if token and api_base_url:
        pixel_url = f"{api_base_url}/api/track/open/{token}"
        pixel_img = f'<img src="{pixel_url}" width="1" height="1" alt="" style="display:none;max-height:0px;max-width:0px;opacity:0;border:none;overflow:hidden;" />'

    if token and has_public_tracking:
        unsub_url = f"{api_base_url}/api/track/unsubscribe/{token}"
        unsub_link = f'<a href="{unsub_url}" style="color: #64748B; text-decoration: underline;">unsubscribe safely here</a>'
    else:
        unsub_mailto = f"mailto:{sender}?subject=Unsubscribe%20Request"
        unsub_link = f'<a href="{unsub_mailto}" style="color: #64748B; text-decoration: underline;">unsubscribe safely here</a>'

    telemetry_html = f"""
    <div style="margin-top: 24px; padding-top: 14px; border-top: 1px solid #E2E8F0; font-size: 11px; color: #94A3B8;">
        If you no longer wish to receive updates from Nenotechnology, you can {unsub_link}.
    </div>
    {pixel_img}
    """

    looks_like_html = clean_body.startswith(("<div", "<table", "<html", "<!DOCTYPE", "<body")) or "<p>" in clean_body or "<br" in clean_body

    if looks_like_html:
        if "<body" in clean_body.lower() and "</body>" in clean_body.lower():
            html_content = re.sub(r'(</body>)', f'{telemetry_html}\\1', clean_body, flags=re.IGNORECASE)
        elif "<html" in clean_body.lower() and "</html>" in clean_body.lower():
            html_content = re.sub(r'(</html>)', f'{telemetry_html}\\1', clean_body, flags=re.IGNORECASE)
        else:
            html_content = f"{clean_body}\n{telemetry_html}"
        text_content = re.sub(r'<[^>]+>', ' ', clean_body).strip()
    else:
        escaped = clean_body.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        html_content = f"<html><body><div style='font-family:Arial,sans-serif;font-size:14px;line-height:1.5;'>{escaped}</div>{telemetry_html}</body></html>"
        text_content = clean_body

    return html_content, text_content
