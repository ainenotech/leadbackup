"""Shared tracking utilities for email body preparation.

Extracts the tracking-pixel, click-rewrite, and unsubscribe footer logic
into a reusable function that both OutlookMailer and SESMailer can use.
OutlookMailer continues to use its own inline logic unchanged — this
module is used ONLY by SESMailer.
"""

import os
import re
from typing import Optional


def prepare_tracked_body(
    body: str,
    token: Optional[str] = None,
    api_base_url: Optional[str] = None,
    sender_email: str = "",
    from_name: str = "",
) -> str:
    """Prepare an HTML email body with tracking pixel, click rewriting,
    and unsubscribe footer.  Mirrors the logic in OutlookMailer.send_email
    without modifying that class.
    """
    if not api_base_url:
        api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")

    clean_body = (body or "").strip()

    # Target booking URL
    target_booking = os.getenv(
        "BOOKING_FORM_URL",
        "https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled",
    )

    # Clean localhost hrefs
    clean_body = re.sub(
        r'href=["\']https?://(?:localhost|127\.0\.0\.1)(?::\d+)?(?:/[^"\']*)?["\']',
        f'href="{target_booking}"',
        clean_body,
    )
    # Clean /form?token= links
    clean_body = re.sub(
        r'href=["\']https?://[^/"\'\\s]+/form\?token=[^"\'\\s]*["\']',
        f'href="{target_booking}"',
        clean_body,
    )

    # Check if api_base_url is a real public HTTPS URL
    has_public_tunnel = (
        bool(api_base_url)
        and api_base_url.lower().startswith("https://")
        and not any(h in api_base_url.lower() for h in ("localhost", "127.0.0.1", "0.0.0.0", "::1"))
    )

    # Rewrite links for click tracking
    if token and has_public_tunnel:
        def _rewrite_link(m):
            orig_url = m.group(1)
            if "track/click" in orig_url or "track/unsubscribe" in orig_url or orig_url.startswith("mailto:"):
                return f'href="{orig_url}"'
            import urllib.parse
            encoded = urllib.parse.quote(orig_url, safe="")
            return f'href="{api_base_url}/api/track/click/{token}?url={encoded}"'

        clean_body = re.sub(r'href=["\'](https?://[^"\']+)["\']', _rewrite_link, clean_body)

    # Tracking pixel
    pixel_img = ""
    if token and api_base_url:
        pixel_url = f"{api_base_url}/api/track/open/{token}"
        pixel_img = (
            f'<img src="{pixel_url}" width="1" height="1" alt="" '
            f'style="display:none;max-height:0px;max-width:0px;opacity:0;'
            f'border:none;overflow:hidden;" />'
        )

    # Unsubscribe link
    if token and has_public_tunnel:
        unsub_url = f"{api_base_url}/api/track/unsubscribe/{token}"
        unsub_link = (
            f'<a href="{unsub_url}" style="color: #64748B; text-decoration: underline;">'
            f'unsubscribe safely here</a>'
        )
    else:
        unsub_mailto = f"mailto:{sender_email}?subject=Unsubscribe%20Request"
        unsub_link = (
            f'<a href="{unsub_mailto}" style="color: #64748B; text-decoration: underline;">'
            f'unsubscribe safely here</a>'
        )

    company_display = from_name or "Nenotechnology"
    telemetry_html = f"""
    <div style="margin-top: 24px; padding-top: 14px; border-top: 1px solid #E2E8F0; font-size: 11px; color: #94A3B8;">
        If you no longer wish to receive updates from {company_display}, you can {unsub_link}.
    </div>
    {pixel_img}
    """

    # Wrap in full HTML document
    if clean_body.startswith(("<div", "<table", "<html", "<!DOCTYPE", "<body")):
        if "<html" in clean_body.lower():
            footer_to_append = pixel_img if ("aineno innovation" in clean_body.lower() or "subscribe" in clean_body.lower()) else telemetry_html
            html_content = clean_body.replace("</body>", f"{footer_to_append}</body>")
        else:
            html_content = f"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
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
                html_paragraphs.append(
                    f"<p style='margin: 0 0 11px 0; margin-top: 0; margin-bottom: 11px; "
                    f"padding: 0; line-height: 1.45;'>{p_html}</p>"
                )

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

    return html_content


def get_unsubscribe_url(token: Optional[str], api_base_url: Optional[str] = None) -> Optional[str]:
    """Return the unsubscribe URL for a given token, or None."""
    if not token:
        return None
    if not api_base_url:
        api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
    return f"{api_base_url}/api/track/unsubscribe/{token}"
