import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

TEMPLATES_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
TEMPLATES_JSON_PATH = os.path.join(TEMPLATES_DATA_DIR, "templates.json")

DEFAULT_LOGO_URL = "https://res.cloudinary.com/dqreqsjas/image/upload/v1789542387/logo-dark.png"
DEFAULT_LINKEDIN_URL = "https://www.linkedin.com/in/tirthpatel-ai/"
DEFAULT_BOOKING_URL = os.getenv(
    "BOOKING_FORM_URL",
    "https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled",
)

# ─────────────────────────────────────────────────────────────
# 4 USER-PROVIDED HIGH-CONVERTING HTML TEMPLATES
# ─────────────────────────────────────────────────────────────

RAW_TEMPLATE_1 = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>Quick idea for {{Company}}</title>
</head>
<body style="margin:0;padding:0;background:#eef1f6;">

<div style="display:none;max-height:0;overflow:hidden;opacity:0;font-size:1px;line-height:1px;color:#eef1f6;">
  A senior AI engineer, already vetted and ready to start, at a fixed monthly cost. 20 minutes to see if it fits {{Company}}.
</div>

<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#eef1f6;">
<tr><td align="center" style="padding:32px 12px;">

  <!-- Card -->
  <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:600px;max-width:100%;background:#ffffff;border-radius:14px;overflow:hidden;border:1px solid #dfe4ee;">

    <!-- Header band -->
    <tr>
      <td style="background:#0b1533;padding:26px 36px;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr>
            <td align="left" style="vertical-align:middle;">
              <img src="LOGO_URL" alt="Neno Technology" width="150" style="display:block;border:0;height:auto;max-width:150px;font-family:Arial,Helvetica,sans-serif;font-size:18px;font-weight:bold;color:#ffffff;">
            </td>
            <td align="right" style="vertical-align:middle;font-family:Arial,Helvetica,sans-serif;font-size:12px;color:#9fb0d6;">
              AI &amp; engineering team, on demand
            </td>
          </tr>
        </table>
      </td>
    </tr>
    <tr><td style="height:4px;line-height:4px;font-size:4px;background:#1a5cff;">&nbsp;</td></tr>

    <!-- Intro -->
    <tr>
      <td style="padding:38px 36px 8px 36px;font-family:Arial,Helvetica,sans-serif;color:#1c2333;">
        <p style="margin:0 0 20px 0;font-size:24px;line-height:32px;font-weight:bold;color:#0b1533;">
          Hi {{FirstName}}, what if {{Company}} had a senior AI engineer starting next week?
        </p>
        <p style="margin:0 0 16px 0;font-size:16px;line-height:26px;color:#3a4358;">
          I'm Tirth, Founder &amp; CEO of <strong style="color:#0b1533;">Nenotechnology</strong> in Ahmedabad, India. We help Australian agencies and businesses cut operational overhead with purpose-built AI solutions, without the enterprise price tag.
        </p>
        <p style="margin:0;font-size:16px;line-height:26px;color:#3a4358;">
          Here is exactly what working with us looks like:
        </p>
      </td>
    </tr>

    <!-- Benefits -->
    <tr>
      <td style="padding:20px 36px 8px 36px;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="font-family:Arial,Helvetica,sans-serif;">

          <tr>
            <td width="44" valign="top" style="padding:0 0 22px 0;">
              <div style="width:34px;height:34px;line-height:34px;text-align:center;border-radius:8px;background:#e8efff;color:#1a5cff;font-size:17px;font-weight:bold;">&#9889;</div>
            </td>
            <td valign="top" style="padding:0 0 22px 0;">
              <div style="font-size:16px;line-height:22px;font-weight:bold;color:#0b1533;">Forward Deployed Engineers</div>
              <div style="font-size:15px;line-height:23px;color:#4a5468;padding-top:3px;">One person takes a requirement from build to deployment, using AI coding tools and agentic workflows to move several times faster than usual.</div>
            </td>
          </tr>

          <tr>
            <td width="44" valign="top" style="padding:0 0 22px 0;">
              <div style="width:34px;height:34px;line-height:34px;text-align:center;border-radius:8px;background:#e8efff;color:#1a5cff;font-size:17px;font-weight:bold;">&#128187;</div>
            </td>
            <td valign="top" style="padding:0 0 22px 0;">
              <div style="font-size:16px;line-height:22px;font-weight:bold;color:#0b1533;">A bench that is already built</div>
              <div style="font-size:15px;line-height:23px;color:#4a5468;padding-top:3px;">AI agent, backend, full-stack and deployment engineers are ready now. No recruiting after you sign.</div>
            </td>
          </tr>

          <tr>
            <td width="44" valign="top" style="padding:0 0 22px 0;">
              <div style="width:34px;height:34px;line-height:34px;text-align:center;border-radius:8px;background:#e8efff;color:#1a5cff;font-size:17px;font-weight:bold;">&#10003;</div>
            </td>
            <td valign="top" style="padding:0 0 22px 0;">
              <div style="font-size:16px;line-height:22px;font-weight:bold;color:#0b1533;">You choose who joins</div>
              <div style="font-size:15px;line-height:23px;color:#4a5468;padding-top:3px;">Every engineer clears our five-stage screening first. You interview the shortlist and pick.</div>
            </td>
          </tr>

          <tr>
            <td width="44" valign="top" style="padding:0 0 8px 0;">
              <div style="width:34px;height:34px;line-height:34px;text-align:center;border-radius:8px;background:#e8efff;color:#1a5cff;font-size:17px;font-weight:bold;">$</div>
            </td>
            <td valign="top" style="padding:0 0 8px 0;">
              <div style="font-size:16px;line-height:22px;font-weight:bold;color:#0b1533;">A fraction of local contract rates</div>
              <div style="font-size:15px;line-height:23px;color:#4a5468;padding-top:3px;">One fixed monthly cost per developer. No payroll, no super, no desk, no notice-period risk.</div>
            </td>
          </tr>

        </table>
      </td>
    </tr>

    <!-- CTA block -->
    <tr>
      <td style="padding:24px 36px 8px 36px;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f3f6fd;border-radius:12px;border-left:4px solid #1a5cff;">
          <tr>
            <td style="padding:26px 28px;font-family:Arial,Helvetica,sans-serif;">
              <div style="font-size:19px;line-height:26px;font-weight:bold;color:#0b1533;">Worth a 20-minute call?</div>
              <div style="font-size:15px;line-height:24px;color:#4a5468;padding:6px 0 20px 0;">
                We will look at where AI and automation could save {{Company}} real time. No pitch deck, no obligation.
              </div>
              <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td align="center" bgcolor="#1a5cff" style="border-radius:8px;">
                    <a href="BOOKING_LINK" target="_blank" style="display:inline-block;padding:14px 30px;font-family:Arial,Helvetica,sans-serif;font-size:16px;font-weight:bold;color:#ffffff;text-decoration:none;border-radius:8px;">Book a free 20-minute call</a>
                  </td>
                </tr>
              </table>
              <div style="font-size:13px;line-height:20px;color:#7a8499;padding-top:14px;">
                Prefer email? Just reply to this message. It comes straight to me.
              </div>
            </td>
          </tr>
        </table>
      </td>
    </tr>

    <!-- P.S. -->
    <tr>
      <td style="padding:22px 36px 6px 36px;font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:24px;color:#4a5468;">
        <strong style="color:#0b1533;">P.S.</strong> Not the right time? Reply "later" and I will check back in a few months. If a different person handles this at {{Company}}, I would be grateful if you pointed me their way.
      </td>
    </tr>

    <!-- Signature -->
    <tr>
      <td style="padding:26px 36px 34px 36px;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-top:1px solid #e3e8f1;">
          <tr>
            <td style="padding-top:22px;font-family:Arial,Helvetica,sans-serif;">
              <div style="font-size:14px;line-height:20px;color:#4a5468;">Warm regards,</div>
              <div style="font-size:17px;line-height:26px;font-weight:bold;color:#0b1533;padding-top:2px;">Tirth Patel</div>
              <div style="font-size:14px;line-height:21px;color:#4a5468;">Founder &amp; CEO, Nenotechnology (Aineno Innovation Pvt. Ltd.)</div>
              <div style="font-size:13px;line-height:20px;color:#7a8499;padding-top:4px;">TEDx Speaker &bull; 300,000+ followers &bull; Co-founder, Gujarat AI Society &amp; Agentic Bharat</div>
              <div style="font-size:13px;line-height:22px;padding-top:8px;color:#7a8499;">
                <a href="mailto:sales@nenotechnology.com" style="color:#1a5cff;text-decoration:none;">sales@nenotechnology.com</a> &nbsp;|&nbsp;
                <a href="tel:+917863852024" style="color:#1a5cff;text-decoration:none;">+91 78638 52024</a> &nbsp;|&nbsp;
                <a href="https://www.nenotechnology.com" style="color:#1a5cff;text-decoration:none;">nenotechnology.com</a> &nbsp;|&nbsp;
                <a href="LINKEDIN_URL" style="color:#1a5cff;text-decoration:none;">LinkedIn</a>
              </div>
            </td>
          </tr>
        </table>
      </td>
    </tr>

  </table>

  <!-- Footer -->
  <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:600px;max-width:100%;">
    <tr>
      <td align="center" style="padding:18px 20px 0 20px;font-family:Arial,Helvetica,sans-serif;font-size:12px;line-height:18px;color:#8b95a9;">
        Aineno Innovation Pvt. Ltd. &middot; Ahmedabad, Gujarat, India<br>
        You are receiving this because we think {{Company}} could benefit from our work.
        <a href="UNSUBSCRIBE_LINK" style="color:#8b95a9;text-decoration:underline;">Unsubscribe</a>
      </td>
    </tr>
  </table>

</td></tr>
</table>

</body>
</html>"""


RAW_TEMPLATE_2 = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>Engineers for {{Company}}, without the hiring wait</title>
</head>
<body style="margin:0;padding:0;background:#f5f6fa;">

<div style="display:none;max-height:0;overflow:hidden;opacity:0;font-size:1px;line-height:1px;color:#f5f6fa;">
  Vetted AI and full-stack engineers, fixed monthly cost, no payroll or notice-period risk.
</div>

<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#f5f6fa">
<tr><td align="center" style="padding:28px 12px;">

  <table role="presentation" width="620" cellpadding="0" cellspacing="0" border="0" style="width:620px;max-width:100%;background:#ffffff;border-radius:16px;overflow:hidden;">

    <!-- HERO -->
    <tr>
      <td bgcolor="#1440d6" style="background:#1440d6;background-image:linear-gradient(135deg,#0d2a9c 0%,#1a5cff 100%);padding:34px 40px 40px 40px;">
        <img src="LOGO_URL" alt="Neno Technology" width="140" style="display:block;border:0;height:auto;max-width:140px;font-family:Arial,Helvetica,sans-serif;font-size:18px;font-weight:bold;color:#ffffff;">
        <div style="font-family:Georgia,'Times New Roman',serif;font-size:32px;line-height:40px;font-weight:bold;color:#ffffff;padding-top:30px;">
          Ship AI projects faster, without the hiring wait.
        </div>
        <div style="font-family:Arial,Helvetica,sans-serif;font-size:16px;line-height:26px;color:#d6e2ff;padding-top:14px;">
          Vetted AI and full-stack engineers for Australian agencies and businesses. Fixed monthly cost, ready to start.
        </div>
      </td>
    </tr>

    <!-- GREETING -->
    <tr>
      <td style="padding:36px 40px 6px 40px;font-family:Arial,Helvetica,sans-serif;color:#2b3448;">
        <p style="margin:0 0 16px 0;font-size:16px;line-height:26px;">Hi {{FirstName}},</p>
        <p style="margin:0 0 16px 0;font-size:16px;line-height:26px;color:#3f4960;">
          I'm Tirth, Founder &amp; CEO of <strong style="color:#0b1533;">Nenotechnology</strong> (Aineno Innovation Pvt. Ltd.) in Ahmedabad. We help teams like {{Company}} cut operational overhead with purpose-built AI, without the enterprise price tag.
        </p>
        <p style="margin:0;font-size:16px;line-height:26px;color:#3f4960;">
          The simplest way to see the difference is to compare it with hiring locally:
        </p>
      </td>
    </tr>

    <!-- COMPARISON -->
    <tr>
      <td style="padding:22px 40px 8px 40px;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border:1px solid #e2e7f2;border-radius:12px;border-collapse:separate;overflow:hidden;font-family:Arial,Helvetica,sans-serif;">
          <tr>
            <td width="34%" bgcolor="#f5f7fc" style="padding:13px 16px;font-size:13px;font-weight:bold;color:#6a7590;border-bottom:1px solid #e2e7f2;">&nbsp;</td>
            <td width="33%" bgcolor="#f5f7fc" style="padding:13px 16px;font-size:13px;font-weight:bold;color:#6a7590;border-bottom:1px solid #e2e7f2;">Local hire</td>
            <td width="33%" bgcolor="#e8efff" style="padding:13px 16px;font-size:13px;font-weight:bold;color:#1440d6;border-bottom:1px solid #d3dfff;">With Neno</td>
          </tr>
          <tr>
            <td style="padding:13px 16px;font-size:14px;font-weight:bold;color:#0b1533;border-bottom:1px solid #eef1f8;">Time to start</td>
            <td style="padding:13px 16px;font-size:14px;color:#4a5468;border-bottom:1px solid #eef1f8;">Recruit, then wait</td>
            <td bgcolor="#f6f9ff" style="padding:13px 16px;font-size:14px;color:#0b1533;font-weight:bold;border-bottom:1px solid #eef1f8;">Bench ready now</td>
          </tr>
          <tr>
            <td style="padding:13px 16px;font-size:14px;font-weight:bold;color:#0b1533;border-bottom:1px solid #eef1f8;">Cost</td>
            <td style="padding:13px 16px;font-size:14px;color:#4a5468;border-bottom:1px solid #eef1f8;">Local contract rates</td>
            <td bgcolor="#f6f9ff" style="padding:13px 16px;font-size:14px;color:#0b1533;font-weight:bold;border-bottom:1px solid #eef1f8;">A fraction, fixed monthly</td>
          </tr>
          <tr>
            <td style="padding:13px 16px;font-size:14px;font-weight:bold;color:#0b1533;border-bottom:1px solid #eef1f8;">Overheads</td>
            <td style="padding:13px 16px;font-size:14px;color:#4a5468;border-bottom:1px solid #eef1f8;">Payroll, super, desk</td>
            <td bgcolor="#f6f9ff" style="padding:13px 16px;font-size:14px;color:#0b1533;font-weight:bold;border-bottom:1px solid #eef1f8;">None</td>
          </tr>
          <tr>
            <td style="padding:13px 16px;font-size:14px;font-weight:bold;color:#0b1533;">Who you get</td>
            <td style="padding:13px 16px;font-size:14px;color:#4a5468;">Whoever applies</td>
            <td bgcolor="#f6f9ff" style="padding:13px 16px;font-size:14px;color:#0b1533;font-weight:bold;">Five-stage vetted, you pick</td>
          </tr>
        </table>
      </td>
    </tr>

    <!-- FDE HIGHLIGHT -->
    <tr>
      <td style="padding:22px 40px 6px 40px;font-family:Arial,Helvetica,sans-serif;">
        <div style="font-size:16px;line-height:26px;color:#3f4960;">
          Our <strong style="color:#0b1533;">Forward Deployed Engineers</strong> take a requirement from build to deployment on their own, using AI coding tools and agentic workflows to move several times faster than usual. We also have AI agent, backend, full-stack and deployment engineers on the bench.
        </div>
      </td>
    </tr>

    <!-- HOW IT WORKS -->
    <tr>
      <td style="padding:26px 40px 6px 40px;font-family:Arial,Helvetica,sans-serif;">
        <div style="font-size:18px;line-height:24px;font-weight:bold;color:#0b1533;padding-bottom:14px;">How it works</div>
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr>
            <td width="34" valign="top" style="padding:0 0 16px 0;">
              <div style="width:26px;height:26px;line-height:26px;text-align:center;border-radius:13px;background:#1a5cff;color:#ffffff;font-size:13px;font-weight:bold;">1</div>
            </td>
            <td valign="top" style="padding:2px 0 16px 0;font-size:15px;line-height:23px;color:#3f4960;"><strong style="color:#0b1533;">20-minute call.</strong> You tell us where time is being lost.</td>
          </tr>
          <tr>
            <td width="34" valign="top" style="padding:0 0 16px 0;">
              <div style="width:26px;height:26px;line-height:26px;text-align:center;border-radius:13px;background:#1a5cff;color:#ffffff;font-size:13px;font-weight:bold;">2</div>
            </td>
            <td valign="top" style="padding:2px 0 16px 0;font-size:15px;line-height:23px;color:#3f4960;"><strong style="color:#0b1533;">Shortlist.</strong> You interview vetted engineers and choose.</td>
          </tr>
          <tr>
            <td width="34" valign="top" style="padding:0 0 4px 0;">
              <div style="width:26px;height:26px;line-height:26px;text-align:center;border-radius:13px;background:#1a5cff;color:#ffffff;font-size:13px;font-weight:bold;">3</div>
            </td>
            <td valign="top" style="padding:2px 0 4px 0;font-size:15px;line-height:23px;color:#3f4960;"><strong style="color:#0b1533;">Start building.</strong> Fixed monthly cost, no notice-period risk.</td>
          </tr>
        </table>
      </td>
    </tr>

    <!-- CTA -->
    <tr>
      <td align="center" style="padding:26px 40px 10px 40px;font-family:Arial,Helvetica,sans-serif;">
        <table role="presentation" cellpadding="0" cellspacing="0" border="0">
          <tr>
            <td align="center" bgcolor="#1a5cff" style="border-radius:10px;">
              <a href="BOOKING_LINK" target="_blank" style="display:inline-block;padding:16px 38px;font-family:Arial,Helvetica,sans-serif;font-size:17px;font-weight:bold;color:#ffffff;text-decoration:none;border-radius:10px;">Book a free 20-minute call</a>
            </td>
          </tr>
        </table>
        <div style="font-size:13px;line-height:20px;color:#7a8499;padding-top:14px;">
          No pitch deck, no obligation. Or just reply to this email, it comes straight to me.
        </div>
      </td>
    </tr>

    <!-- SIGNATURE -->
    <tr>
      <td style="padding:30px 40px 34px 40px;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-top:1px solid #e6eaf3;">
          <tr>
            <td style="padding-top:22px;font-family:Arial,Helvetica,sans-serif;">
              <div style="font-size:14px;line-height:20px;color:#4a5468;">Warm regards,</div>
              <div style="font-size:17px;line-height:26px;font-weight:bold;color:#0b1533;">Tirth Patel</div>
              <div style="font-size:14px;line-height:21px;color:#4a5468;">Founder &amp; CEO, Nenotechnology (Aineno Innovation Pvt. Ltd.)</div>
              <div style="font-size:13px;line-height:20px;color:#7a8499;padding-top:3px;">TEDx Speaker &bull; 300,000+ followers &bull; Co-founder, Gujarat AI Society &amp; Agentic Bharat</div>
              <div style="font-size:13px;line-height:22px;padding-top:8px;">
                <a href="mailto:sales@nenotechnology.com" style="color:#1a5cff;text-decoration:none;">sales@nenotechnology.com</a> &nbsp;|&nbsp;
                <a href="tel:+917863852024" style="color:#1a5cff;text-decoration:none;">+91 78638 52024</a> &nbsp;|&nbsp;
                <a href="https://www.nenotechnology.com" style="color:#1a5cff;text-decoration:none;">nenotechnology.com</a> &nbsp;|&nbsp;
                <a href="LINKEDIN_URL" style="color:#1a5cff;text-decoration:none;">LinkedIn</a>
              </div>
            </td>
          </tr>
        </table>
      </td>
    </tr>

  </table>

  <table role="presentation" width="620" cellpadding="0" cellspacing="0" border="0" style="width:620px;max-width:100%;">
    <tr>
      <td align="center" style="padding:18px 20px 0 20px;font-family:Arial,Helvetica,sans-serif;font-size:12px;line-height:18px;color:#8b95a9;">
        Aineno Innovation Pvt. Ltd. &middot; Ahmedabad, Gujarat, India<br>
        Not relevant for {{Company}}? <a href="UNSUBSCRIBE_LINK" style="color:#8b95a9;text-decoration:underline;">Unsubscribe</a>
      </td>
    </tr>
  </table>

</td></tr>
</table>

</body>
</html>"""


RAW_TEMPLATE_3 = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>Where AI could save {{Company}} time first</title>
<style>
  @media only screen and (max-width:620px) {
    .stack { display:block !important; width:100% !important; }
    .pad { padding-left:22px !important; padding-right:22px !important; }
    .h1 { font-size:26px !important; line-height:34px !important; }
  }
</style>
</head>
<body style="margin:0;padding:0;background:#e9eef0;">

<div style="display:none;max-height:0;overflow:hidden;opacity:0;font-size:1px;line-height:1px;color:#e9eef0;">
  Four places AI usually pays back first, and three ways to work with our engineers.
</div>

<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#e9eef0">
<tr><td align="center" style="padding:28px 12px;">

  <table role="presentation" width="620" cellpadding="0" cellspacing="0" border="0" style="width:620px;max-width:100%;background:#ffffff;border-radius:14px;overflow:hidden;">

    <!-- Top bar -->
    <tr>
      <td class="pad" style="padding:24px 40px;border-bottom:1px solid #e6ebee;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr>
            <td align="left"><img src="LOGO_URL" alt="Neno Technology" width="130" style="display:block;border:0;height:auto;max-width:130px;font-family:Arial,Helvetica,sans-serif;font-size:17px;font-weight:bold;color:#0f2a2e;"></td>
            <td align="right" style="font-family:Arial,Helvetica,sans-serif;font-size:12px;color:#0f766e;font-weight:bold;">Ahmedabad &rarr; Australia</td>
          </tr>
        </table>
      </td>
    </tr>

    <!-- Opening -->
    <tr>
      <td class="pad" style="padding:38px 40px 6px 40px;font-family:Arial,Helvetica,sans-serif;">
        <div class="h1" style="font-family:Georgia,'Times New Roman',serif;font-size:30px;line-height:38px;font-weight:bold;color:#0f2a2e;">
          {{FirstName}}, where is {{Company}} losing the most hours?
        </div>
        <p style="margin:20px 0 14px 0;font-size:16px;line-height:26px;color:#3b4a4d;">
          I'm Tirth Patel, founder of Nenotechnology. We build AI solutions and provide vetted engineers for Australian agencies and businesses, at a fraction of local costs.
        </p>
        <p style="margin:0;font-size:16px;line-height:26px;color:#3b4a4d;">
          In most teams, AI pays back first in one of these four places:
        </p>
      </td>
    </tr>

    <!-- Use cases 2x2 -->
    <tr>
      <td class="pad" style="padding:20px 40px 4px 40px;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr>
            <td class="stack" width="50%" valign="top" style="padding:0 6px 12px 0;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#f0f7f6" style="background:#f0f7f6;border-radius:10px;">
                <tr><td style="padding:18px 18px;font-family:Arial,Helvetica,sans-serif;">
                  <div style="font-size:15px;line-height:21px;font-weight:bold;color:#0f2a2e;">Lead follow-up</div>
                  <div style="font-size:14px;line-height:21px;color:#4a5a5d;padding-top:5px;">AI agents that qualify, reply and book meetings while your team sleeps.</div>
                </td></tr>
              </table>
            </td>
            <td class="stack" width="50%" valign="top" style="padding:0 0 12px 6px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#f0f7f6" style="background:#f0f7f6;border-radius:10px;">
                <tr><td style="padding:18px 18px;font-family:Arial,Helvetica,sans-serif;">
                  <div style="font-size:15px;line-height:21px;font-weight:bold;color:#0f2a2e;">Customer support</div>
                  <div style="font-size:14px;line-height:21px;color:#4a5a5d;padding-top:5px;">First-line answers and ticket triage, with humans handling the hard cases.</div>
                </td></tr>
              </table>
            </td>
          </tr>
          <tr>
            <td class="stack" width="50%" valign="top" style="padding:0 6px 12px 0;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#f0f7f6" style="background:#f0f7f6;border-radius:10px;">
                <tr><td style="padding:18px 18px;font-family:Arial,Helvetica,sans-serif;">
                  <div style="font-size:15px;line-height:21px;font-weight:bold;color:#0f2a2e;">Reporting and admin</div>
                  <div style="font-size:14px;line-height:21px;color:#4a5a5d;padding-top:5px;">Weekly reports, data entry and document handling that run themselves.</div>
                </td></tr>
              </table>
            </td>
            <td class="stack" width="50%" valign="top" style="padding:0 0 12px 6px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#f0f7f6" style="background:#f0f7f6;border-radius:10px;">
                <tr><td style="padding:18px 18px;font-family:Arial,Helvetica,sans-serif;">
                  <div style="font-size:15px;line-height:21px;font-weight:bold;color:#0f2a2e;">Custom internal tools</div>
                  <div style="font-size:14px;line-height:21px;color:#4a5a5d;padding-top:5px;">Dashboards and workflow apps built around how you actually work.</div>
                </td></tr>
              </table>
            </td>
          </tr>
        </table>
      </td>
    </tr>

    <!-- Engagement options -->
    <tr>
      <td class="pad" style="padding:22px 40px 4px 40px;font-family:Arial,Helvetica,sans-serif;">
        <div style="font-size:18px;line-height:24px;font-weight:bold;color:#0f2a2e;padding-bottom:6px;">Three ways to work with us</div>

        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr>
            <td style="padding:14px 0;border-bottom:1px solid #e6ebee;font-size:15px;line-height:23px;color:#3b4a4d;">
              <strong style="color:#0f2a2e;">One dedicated engineer.</strong> A Forward Deployed Engineer who takes a requirement from build to deployment, using AI coding tools to move fast.
            </td>
          </tr>
          <tr>
            <td style="padding:14px 0;border-bottom:1px solid #e6ebee;font-size:15px;line-height:23px;color:#3b4a4d;">
              <strong style="color:#0f2a2e;">A small squad.</strong> AI agent, backend, full-stack and deployment engineers working as one team on your roadmap.
            </td>
          </tr>
          <tr>
            <td style="padding:14px 0;font-size:15px;line-height:23px;color:#3b4a4d;">
              <strong style="color:#0f2a2e;">A defined project.</strong> Tell us the outcome and we build and hand it over.
            </td>
          </tr>
        </table>

        <p style="margin:14px 0 0 0;font-size:14px;line-height:22px;color:#5b6a6d;">
          Every engineer clears a five-stage screening before you meet them, and you choose who joins. One fixed monthly cost per developer, with no payroll, super or notice-period risk.
        </p>
      </td>
    </tr>

    <!-- CTA -->
    <tr>
      <td class="pad" style="padding:26px 40px 8px 40px;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#0f2a2e" style="background:#0f2a2e;border-radius:12px;">
          <tr>
            <td align="center" style="padding:30px 26px;font-family:Arial,Helvetica,sans-serif;">
              <div style="font-size:20px;line-height:28px;font-weight:bold;color:#ffffff;">Tell us your biggest bottleneck.</div>
              <div style="font-size:15px;line-height:23px;color:#b7cbcd;padding:8px 0 20px 0;">
                In 20 minutes we will point out where AI could help {{Company}} most. No pitch deck, no obligation.
              </div>
              <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td align="center" bgcolor="#2dd4bf" style="border-radius:8px;">
                    <a href="BOOKING_LINK" target="_blank" style="display:inline-block;padding:14px 32px;font-family:Arial,Helvetica,sans-serif;font-size:16px;font-weight:bold;color:#06302b;text-decoration:none;border-radius:8px;">Pick a time that suits you</a>
                  </td>
                </tr>
              </table>
              <div style="font-size:13px;line-height:20px;color:#8fa9ac;padding-top:14px;">
                Or reply with one line about the bottleneck and I will come back with ideas.
              </div>
            </td>
          </tr>
        </table>
      </td>
    </tr>

    <!-- Signature -->
    <tr>
      <td class="pad" style="padding:28px 40px 34px 40px;font-family:Arial,Helvetica,sans-serif;">
        <div style="font-size:14px;line-height:20px;color:#4a5a5d;">Warm regards,</div>
        <div style="font-size:17px;line-height:26px;font-weight:bold;color:#0f2a2e;">Tirth Patel</div>
        <div style="font-size:14px;line-height:21px;color:#4a5a5d;">Founder &amp; CEO, Nenotechnology (Aineno Innovation Pvt. Ltd.)</div>
        <div style="font-size:13px;line-height:20px;color:#7a898c;padding-top:3px;">TEDx Speaker &bull; 300,000+ followers &bull; Co-founder, Gujarat AI Society &amp; Agentic Bharat</div>
        <div style="font-size:13px;line-height:22px;padding-top:8px;">
          <a href="mailto:sales@nenotechnology.com" style="color:#0f766e;text-decoration:none;">sales@nenotechnology.com</a> &nbsp;|&nbsp;
          <a href="tel:+917863852024" style="color:#0f766e;text-decoration:none;">+91 78638 52024</a> &nbsp;|&nbsp;
          <a href="https://www.nenotechnology.com" style="color:#0f766e;text-decoration:none;">nenotechnology.com</a> &nbsp;|&nbsp;
          <a href="LINKEDIN_URL" style="color:#0f766e;text-decoration:none;">LinkedIn</a>
        </div>
      </td>
    </tr>

  </table>

  <table role="presentation" width="620" cellpadding="0" cellspacing="0" border="0" style="width:620px;max-width:100%;">
    <tr>
      <td align="center" style="padding:18px 20px 0 20px;font-family:Arial,Helvetica,sans-serif;font-size:12px;line-height:18px;color:#7a898c;">
        Aineno Innovation Pvt. Ltd. &middot; Ahmedabad, Gujarat, India<br>
        Prefer not to hear from us? <a href="UNSUBSCRIBE_LINK" style="color:#7a898c;text-decoration:underline;">Unsubscribe</a>
      </td>
    </tr>
  </table>

</td></tr>
</table>

</body>
</html>"""


RAW_TEMPLATE_4 = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>Your next engineer doesn't need a job ad</title>
<style>
  @media only screen and (max-width:620px) {
    .card { border-radius:0 !important; }
    .pad { padding-left:22px !important; padding-right:22px !important; }
    .h1 { font-size:32px !important; line-height:38px !important; }
  }
</style>
</head>
<body style="margin:0;padding:0;background:#f2f2f0;">

<div style="display:none;max-height:0;overflow:hidden;opacity:0;font-size:1px;line-height:1px;color:#f2f2f0;">
  Picture an AI engineer already working on {{Company}}'s biggest time-drain. Here is how that happens.
</div>

<div style="padding:28px 12px;background:#f2f2f0;">
  <div class="card" style="max-width:600px;margin:0 auto;background:#ffffff;border-radius:6px;overflow:hidden;font-family:Arial,Helvetica,sans-serif;color:#1a1a1a;">

    <!-- Logo -->
    <div class="pad" style="padding:30px 44px 0 44px;">
      <img src="LOGO_URL" alt="Neno Technology" width="120" style="display:block;border:0;height:auto;max-width:120px;font-size:17px;font-weight:bold;color:#1a1a1a;">
    </div>

    <!-- Headline -->
    <div class="pad" style="padding:34px 44px 0 44px;">
      <div class="h1" style="font-family:Georgia,'Times New Roman',serif;font-size:38px;line-height:44px;font-weight:bold;color:#111111;letter-spacing:-0.5px;">
        Your next engineer doesn't need a job ad.
      </div>
      <div style="width:56px;height:5px;background:#ff5a1f;margin-top:22px;font-size:0;line-height:0;">&nbsp;</div>
    </div>

    <!-- Letter -->
    <div class="pad" style="padding:28px 44px 0 44px;font-size:17px;line-height:29px;color:#3a3a3a;">
      <p style="margin:0 0 18px 0;">Hi {{FirstName}},</p>
      <p style="margin:0 0 18px 0;">
        Every business has a task that quietly eats hours: chasing leads, writing the same reports, answering the same questions, moving data between tools. Everyone knows it should be automated. Nobody has the spare engineer to do it.
      </p>
      <p style="margin:0;">
        I'm Tirth, and that gap is what <strong style="color:#111111;">Nenotechnology</strong> exists to close. We place vetted AI and full-stack engineers with Australian agencies and businesses, so the work starts without a hiring process.
      </p>
    </div>

    <!-- Picture this -->
    <div class="pad" style="padding:34px 44px 0 44px;">
      <div style="font-size:20px;line-height:26px;font-weight:bold;color:#111111;">Picture this at {{Company}}</div>

      <div style="margin-top:18px;padding-left:18px;border-left:3px solid #ff5a1f;font-size:16px;line-height:26px;color:#3a3a3a;">
        A lead fills in your website form at 11pm. By the time your team logs on, an AI agent has already replied, asked the right questions and put a meeting in the calendar.
      </div>
      <div style="margin-top:16px;padding-left:18px;border-left:3px solid #ff5a1f;font-size:16px;line-height:26px;color:#3a3a3a;">
        The weekly client report that used to take someone half a day now lands in the inbox, drafted and checked, before Monday's first coffee.
      </div>
      <div style="margin-top:16px;padding-left:18px;border-left:3px solid #ff5a1f;font-size:16px;line-height:26px;color:#3a3a3a;">
        A simple question from a customer gets a correct answer in seconds. Only the tricky ones reach a person.
      </div>
      <div style="margin-top:16px;font-size:14px;line-height:22px;color:#7a7a7a;">
        These are examples of what we build. Yours will be shaped around how you actually work.
      </div>
    </div>

    <!-- What you get -->
    <div class="pad" style="padding:34px 44px 0 44px;">
      <div style="font-size:20px;line-height:26px;font-weight:bold;color:#111111;">Why it is easy to say yes</div>
      <div style="margin-top:14px;font-size:16px;line-height:27px;color:#3a3a3a;">
        <div style="padding-bottom:10px;"><strong style="color:#111111;">You choose.</strong> Every engineer clears a five-stage screening first. You interview the shortlist and pick who joins.</div>
        <div style="padding-bottom:10px;"><strong style="color:#111111;">They finish things.</strong> Our Forward Deployed Engineers take a requirement from build to deployment, using AI coding tools and agentic workflows to move much faster.</div>
        <div><strong style="color:#111111;">One flat price.</strong> A fixed monthly cost per developer, well below local contract rates. No payroll, no super, no desk, no notice period.</div>
      </div>
    </div>

    <!-- Fit / not fit -->
    <div class="pad" style="padding:34px 44px 0 44px;">
      <div style="background:#f6f6f4;border-radius:8px;padding:24px 26px;">
        <div style="font-size:16px;line-height:24px;font-weight:bold;color:#111111;">A fair warning: we are not for everyone.</div>
        <div style="font-size:15px;line-height:25px;color:#3a3a3a;padding-top:8px;">
          We are a good match if you have real work to automate or build and want to start soon. We are probably not the right call if you only want a one-off quote for a tiny task, or you need someone sitting in your office.
        </div>
      </div>
    </div>

    <!-- CTA -->
    <div class="pad" style="padding:38px 44px 0 44px;text-align:left;">
      <div style="font-family:Georgia,'Times New Roman',serif;font-size:26px;line-height:33px;font-weight:bold;color:#111111;">Curious? Let's talk for 20 minutes.</div>
      <div style="font-size:16px;line-height:26px;color:#3a3a3a;padding-top:8px;">
        I will ask where your team loses time, and tell you honestly whether we can help. No slides, no pressure.
      </div>
      <div style="padding-top:22px;">
        <a href="BOOKING_LINK" target="_blank" style="display:inline-block;background:#ff5a1f;color:#ffffff;font-size:17px;font-weight:bold;text-decoration:none;padding:16px 34px;border-radius:6px;">Choose a time</a>
      </div>
      <div style="font-size:14px;line-height:22px;color:#7a7a7a;padding-top:14px;">
        Rather write it out? Reply with the task you would most like gone. It comes straight to me.
      </div>
    </div>

    <!-- Signature -->
    <div class="pad" style="padding:38px 44px 40px 44px;">
      <div style="border-top:1px solid #e6e6e2;padding-top:24px;">
        <div style="font-size:14px;line-height:20px;color:#5a5a5a;">Warm regards,</div>
        <div style="font-size:18px;line-height:27px;font-weight:bold;color:#111111;">Tirth Patel</div>
        <div style="font-size:14px;line-height:21px;color:#5a5a5a;">Founder &amp; CEO, Nenotechnology (Aineno Innovation Pvt. Ltd.)</div>
        <div style="font-size:13px;line-height:20px;color:#8a8a8a;padding-top:3px;">TEDx Speaker &bull; 300,000+ followers &bull; Co-founder, Gujarat AI Society &amp; Agentic Bharat</div>
        <div style="font-size:13px;line-height:23px;padding-top:8px;">
          <a href="mailto:sales@nenotechnology.com" style="color:#d9430f;text-decoration:none;">sales@nenotechnology.com</a> &nbsp;|&nbsp;
          <a href="tel:+917863852024" style="color:#d9430f;text-decoration:none;">+91 78638 52024</a> &nbsp;|&nbsp;
          <a href="https://www.nenotechnology.com" style="color:#d9430f;text-decoration:none;">nenotechnology.com</a> &nbsp;|&nbsp;
          <a href="LINKEDIN_URL" style="color:#d9430f;text-decoration:none;">LinkedIn</a>
        </div>
      </div>
    </div>

  </div>

  <!-- Footer -->
  <div style="max-width:600px;margin:0 auto;padding:18px 20px 0 20px;text-align:center;font-family:Arial,Helvetica,sans-serif;font-size:12px;line-height:18px;color:#8a8a8a;">
    Aineno Innovation Pvt. Ltd. &middot; Ahmedabad, Gujarat, India<br>
    Not relevant to {{Company}}? <a href="UNSUBSCRIBE_LINK" style="color:#8a8a8a;text-decoration:underline;">Unsubscribe</a>
  </div>
</div>

</body>
</html>"""


# Built-in Core Template Catalog
BUILTIN_TEMPLATES: List[Dict[str, Any]] = [
    {
        "id": "tpl_exec_navy",
        "name": "Template 1: Executive Dark Navy",
        "subject": "Quick idea for {{Company}}",
        "category": "Enterprise & Agencies",
        "description": "Premium dark navy header (#0b1533) with blue accent line, 4 feature bullet points (FDE, Pre-built Bench, 5-Stage Vetting, Low Overhead), and high-contrast consultation CTA.",
        "html_content": RAW_TEMPLATE_1,
        "style": "executive",
        "accent_color": "#1A5CFF",
        "badge": "Top Recommended",
    },
    {
        "id": "tpl_blue_gradient",
        "name": "Template 2: Blue Gradient Hero & Comparison",
        "subject": "Engineers for {{Company}}, without the hiring wait",
        "category": "Direct Pitch & Comparison",
        "description": "Vibrant gradient hero banner with full side-by-side comparison table (Local Hire vs With Neno) and clear 1-2-3 onboarding timeline.",
        "html_content": RAW_TEMPLATE_2,
        "style": "modern_gradient",
        "accent_color": "#1440D6",
        "badge": "High Conversion",
    },
    {
        "id": "tpl_teal_grid",
        "name": "Template 3: Modern Teal Use-Case Grid",
        "subject": "Where AI could save {{Company}} time first",
        "category": "Problem-Solution & Use Cases",
        "description": "Refined emerald/teal theme with 2x2 use-case grid (Lead Follow-up, Support, Admin/Reporting, Internal Tools) and dark contrasting consultation box.",
        "html_content": RAW_TEMPLATE_3,
        "style": "teal_grid",
        "accent_color": "#0F766E",
        "badge": "High Engagement",
    },
    {
        "id": "tpl_editorial_letter",
        "name": "Template 4: Editorial Personal Letter",
        "subject": "Your next engineer doesn't need a job ad",
        "category": "Personal Letter & Story",
        "description": "Warm personal editorial layout with high readability, energetic orange accent bar (#FF5A1F), 'Picture this at {{Company}}', and candid fit/not-fit filter.",
        "html_content": RAW_TEMPLATE_4,
        "style": "editorial_letter",
        "accent_color": "#FF5A1F",
        "badge": "Executive Personal",
    },
    {
        "id": "tpl_standard_fde",
        "name": "Template 5: Forward Deployed Engineers (Clean)",
        "subject": "Smarter Systems for {{Company}} - AI & Automation by Nenotechnology",
        "category": "Technical Capabilities",
        "description": "Clean, minimal white card with Cloudinary CDN header logo, focusing on forward-deployed engineer velocity and fixed monthly cost.",
        "html_content": """<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;font-size:15px;line-height:1.6;color:#1E293B;max-width:600px;margin:0 auto;background:#ffffff;padding:24px;border:1px solid #E2E8F0;border-radius:12px;">
  <div style="margin-bottom:18px;border-bottom:1px solid #EEF0F4;padding-bottom:12px;"><img src="LOGO_URL" alt="Nenotechnology" width="132" style="display:block;max-width:132px;"></div>
  <p>Dear {{FirstName}},</p>
  <p>I hope you and the team at {{Company}} are doing well.</p>
  <p>I'm Tirth Patel, Founder &amp; CEO of <strong>Nenotechnology</strong> in Ahmedabad. We help forward-thinking teams cut operational overhead with purpose-built AI solutions &mdash; without the enterprise price tag.</p>
  <p>Our <strong>Forward Deployed Engineers</strong> take requirements from design to production using cutting-edge agentic workflows, moving 3-5x faster than conventional developers.</p>
  <div style="margin:22px 0;text-align:center;">
    <a href="BOOKING_LINK" target="_blank" style="display:inline-block;background:#2563EB;color:#FFFFFF;padding:12px 28px;text-decoration:none;border-radius:8px;font-weight:600;font-size:15px;">Schedule a 20-Min AI Discovery Call</a>
  </div>
  <p style="font-size:14px;color:#64748B;">Warm regards,<br><strong style="color:#0F172A;">Tirth Patel</strong><br>Founder &amp; CEO, Nenotechnology</p>
</div>""",
        "style": "standard_minimal",
        "accent_color": "#2563EB",
        "badge": "Standard",
    },
    {
        "id": "tpl_calling_agents",
        "name": "Template 6: Autonomous AI Voice & Calling Agents",
        "subject": "Zero Missed Opportunities for {{Company}} - Autonomous AI Calling Agents",
        "category": "Calling & Voice AI",
        "description": "Specialized B2B outreach highlighting autonomous inbound/outbound voice calling agents that qualify leads 24/7.",
        "html_content": """<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;font-size:15px;line-height:1.6;color:#1E293B;max-width:600px;margin:0 auto;background:#ffffff;padding:24px;border:1px solid #E2E8F0;border-radius:12px;">
  <div style="margin-bottom:18px;border-bottom:1px solid #EEF0F4;padding-bottom:12px;"><img src="LOGO_URL" alt="Nenotechnology" width="132" style="display:block;max-width:132px;"></div>
  <p>Hi {{FirstName}},</p>
  <p>What if {{Company}} could instantly qualify every inbound lead within 60 seconds &mdash; 24/7?</p>
  <p>At <strong>Nenotechnology</strong>, our autonomous AI voice agents handle natural two-way customer calls, answer complex service inquiries, and schedule confirmed appointments directly onto your calendar.</p>
  <div style="background:#F8FAFC;border-left:4px solid #7C3AED;padding:14px 18px;margin:18px 0;border-radius:6px;">
    <strong>Proven Impact:</strong> Up to 70% reduction in lead follow-up latency with zero extra staff hiring.
  </div>
  <div style="margin:22px 0;text-align:center;">
    <a href="BOOKING_LINK" target="_blank" style="display:inline-block;background:#7C3AED;color:#FFFFFF;padding:12px 28px;text-decoration:none;border-radius:8px;font-weight:600;font-size:15px;">Experience an AI Calling Demo</a>
  </div>
  <p style="font-size:14px;color:#64748B;">Best regards,<br><strong style="color:#0F172A;">Tirth Patel</strong><br>Founder &amp; CEO, Nenotechnology</p>
</div>""",
        "style": "purple_modern",
        "accent_color": "#7C3AED",
        "badge": "Voice AI",
    },
    {
        "id": "tpl_workflow_automation",
        "name": "Template 7: Business Automation & ERP/CRM Integration",
        "subject": "Automating Time-Consuming Operations at {{Company}}",
        "category": "Enterprise Automation",
        "description": "Operational efficiency pitch demonstrating automatic sync between WhatsApp, Email, CRM, and internal databases.",
        "html_content": """<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;font-size:15px;line-height:1.6;color:#1E293B;max-width:600px;margin:0 auto;background:#ffffff;padding:24px;border:1px solid #E2E8F0;border-radius:12px;">
  <div style="margin-bottom:18px;border-bottom:1px solid #EEF0F4;padding-bottom:12px;"><img src="LOGO_URL" alt="Nenotechnology" width="132" style="display:block;max-width:132px;"></div>
  <p>Dear {{FirstName}},</p>
  <p>Most growing businesses spend 15-20 hours every week manually copying data between email, spreadsheets, and CRM tools.</p>
  <p>At <strong>Nenotechnology</strong>, we build seamless, unified automation pipelines connecting your outreach, customer replies, and database in real-time so your core team can focus on closing deals.</p>
  <div style="margin:22px 0;text-align:center;">
    <a href="BOOKING_LINK" target="_blank" style="display:inline-block;background:#059669;color:#FFFFFF;padding:12px 28px;text-decoration:none;border-radius:8px;font-weight:600;font-size:15px;">Review Automation Opportunities for {{Company}}</a>
  </div>
  <p style="font-size:14px;color:#64748B;">Warm regards,<br><strong style="color:#0F172A;">Tirth Patel</strong><br>Founder &amp; CEO, Nenotechnology</p>
</div>""",
        "style": "emerald_enterprise",
        "accent_color": "#059669",
        "badge": "Automation",
    },
]


def load_all_templates() -> List[Dict[str, Any]]:
    """Loads all templates: built-ins combined with any user-created or edited templates."""
    tpl_dict = {t["id"]: dict(t) for t in BUILTIN_TEMPLATES}
    if os.path.exists(TEMPLATES_JSON_PATH):
        try:
            with open(TEMPLATES_JSON_PATH, "r", encoding="utf-8") as f:
                custom_tpls = json.load(f)
                if isinstance(custom_tpls, list):
                    for c in custom_tpls:
                        if c.get("id"):
                            tpl_dict[c["id"]] = c
        except Exception:
            pass
    return list(tpl_dict.values())


def get_template_by_id(template_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a single template definition by its unique identifier."""
    for tpl in load_all_templates():
        if tpl.get("id") == template_id:
            return tpl
    return None


def save_custom_template(template_dict: Dict[str, Any]) -> bool:
    """Saves or updates a custom template in data/templates.json."""
    os.makedirs(TEMPLATES_DATA_DIR, exist_ok=True)
    custom_list = []
    if os.path.exists(TEMPLATES_JSON_PATH):
        try:
            with open(TEMPLATES_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    custom_list = data
        except Exception:
            custom_list = []

    # Update if exists, else append
    idx = next((i for i, item in enumerate(custom_list) if item.get("id") == template_dict.get("id")), -1)
    if idx >= 0:
        custom_list[idx] = template_dict
    else:
        custom_list.append(template_dict)

    try:
        with open(TEMPLATES_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(custom_list, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def render_template(
    template_or_id: Any,
    lead_name: Optional[Any] = None,
    company: Optional[str] = None,
    pain_point: Optional[str] = None,
    tracking_link: Optional[str] = None,
    booking_url: Optional[str] = None,
    logo_url: Optional[str] = None,
    linkedin_url: Optional[str] = None,
    lead_data: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> Tuple[str, str]:
    """Interpolates lead data, tracking links, and assets into the requested template.
    Accepts either template ID string or template dictionary, and either individual fields or a lead_data dict.
    Returns (interpolated_subject, interpolated_html_body).
    """
    if isinstance(template_or_id, dict):
        tpl = template_or_id
    else:
        tpl = get_template_by_id(str(template_or_id))
        if not tpl:
            tpl = BUILTIN_TEMPLATES[0]

    # If lead_name argument is passed as a dict, treat as lead_data
    if isinstance(lead_name, dict):
        lead_data = lead_name
        lead_name = None

    if lead_data and isinstance(lead_data, dict):
        if not lead_name:
            lead_name = lead_data.get("name") or lead_data.get("first_name") or lead_data.get("full_name")
        if not company:
            company = lead_data.get("company") or lead_data.get("company_name")
        if not pain_point:
            pain_point = lead_data.get("pain_point") or lead_data.get("pain")
        if not tracking_link:
            tracking_link = lead_data.get("tracking_link")
        if not booking_url:
            booking_url = lead_data.get("booking_url")

    # Clean Name & Company
    c_name = str(lead_name).strip() if lead_name and str(lead_name).strip().lower() not in ("nan", "none", "") else ""
    first_name = c_name.split()[0].title() if c_name else "there"
    
    c_comp = str(company).strip() if company and str(company).strip().lower() not in ("nan", "none", "") else ""
    company_name = c_comp if c_comp else "your team"

    pain_text = str(pain_point).strip() if pain_point and str(pain_point).strip().lower() not in ("nan", "none", "") else "manual operational overhead"

    b_link = (booking_url or tracking_link or DEFAULT_BOOKING_URL).strip()
    l_url = (logo_url or DEFAULT_LOGO_URL).strip()
    li_url = (linkedin_url or DEFAULT_LINKEDIN_URL).strip()
    unsub_link = f"mailto:sales@nenotechnology.com?subject=Unsubscribe%20{company_name}"

    # Subject Interpolation
    subj = tpl.get("subject", "Quick idea for {{Company}}")
    subj = subj.replace("{{FirstName}}", first_name)
    subj = subj.replace("{{Company}}", company_name if company_name != "your team" else "Your Business")
    subj = subj.replace("{{Pain}}", pain_text)

    # Body Interpolation
    html = tpl.get("html_content", "")
    html = html.replace("{{FirstName}}", first_name)
    html = html.replace("{{Company}}", company_name)
    html = html.replace("{{Pain}}", pain_text)
    html = html.replace("LOGO_URL", l_url)
    html = html.replace("BOOKING_LINK", b_link)
    html = html.replace("LINKEDIN_URL", li_url)
    html = html.replace("UNSUBSCRIBE_LINK", unsub_link)

    return subj, html


# ─────────────────────────────────────────────────────────────
# TEMPLATE-WISE ANALYTICS & DAILY TREND COMPUTATION
# ─────────────────────────────────────────────────────────────

def compute_template_analytics(df: pd.DataFrame) -> Dict[str, Any]:
    """Calculates granular performance metrics and day-by-day trends
    for each template across opens, clicks, replies, and consultation bookings.
    """
    templates = load_all_templates()
    tpl_lookup = {t["id"]: t for t in templates}

    if df.empty:
        return {
            "template_stats": [],
            "daily_trends": pd.DataFrame(),
            "best_open_rate": None,
            "best_click_rate": None,
            "best_booking_rate": None,
            "total_templates_active": 0,
        }

    df_copy = df.copy()

    # Normalize template_id
    if "template_id" not in df_copy.columns:
        df_copy["template_id"] = None
    if "template_name" not in df_copy.columns:
        df_copy["template_name"] = None

    # Fallback to map option / pattern if template_id is missing
    def _infer_template(row):
        tid = row.get("template_id")
        if pd.notna(tid) and str(tid).strip() and str(tid).strip().lower() != "nan":
            return str(tid).strip()
        # Infer from subject
        subj = str(row.get("subject") or "").lower()
        if "quick idea" in subj:
            return "tpl_exec_navy"
        elif "without the hiring wait" in subj or "faster" in subj:
            return "tpl_blue_gradient"
        elif "where ai could save" in subj:
            return "tpl_teal_grid"
        elif "doesn't need a job ad" in subj or "job ad" in subj:
            return "tpl_editorial_letter"
        elif "voice" in subj or "calling" in subj:
            return "tpl_calling_agents"
        elif "automating" in subj or "erp" in subj:
            return "tpl_workflow_automation"
        return "tpl_standard_fde"

    df_copy["resolved_template_id"] = df_copy.apply(_infer_template, axis=1)

    template_stats = []
    daily_records = []

    # Calculate metrics for each template
    for tpl in templates:
        tid = tpl["id"]
        tname = tpl["name"]
        color = tpl.get("accent_color", "#2563EB")
        
        t_df = df_copy[df_copy["resolved_template_id"] == tid]
        total_leads = len(t_df)
        sent_df = t_df[t_df["status"].isin(["sent", "meeting_scheduled"])]
        total_sent = len(sent_df)
        
        opened_count = int(t_df["opened"].sum()) if "opened" in t_df.columns else 0
        clicked_count = int(t_df["clicked_link"].sum()) if "clicked_link" in t_df.columns else 0
        replied_count = int(t_df["reply_received_at"].notna().sum()) if "reply_received_at" in t_df.columns else 0
        booked_count = int(t_df["booking_status"].isin(["scheduled", "meeting_scheduled", "confirmation_sent", "confirmed"]).sum()) if "booking_status" in t_df.columns else 0

        open_rate = round((opened_count / total_sent * 100), 1) if total_sent > 0 else 0.0
        click_rate = round((clicked_count / total_sent * 100), 1) if total_sent > 0 else 0.0
        reply_rate = round((replied_count / total_sent * 100), 1) if total_sent > 0 else 0.0
        booking_rate = round((booked_count / total_sent * 100), 1) if total_sent > 0 else 0.0

        stat_item = {
            "template_id": tid,
            "id": tid,
            "template_name": tname,
            "name": tname,
            "category": tpl.get("category", "General"),
            "badge": tpl.get("badge", ""),
            "accent_color": color,
            "total_leads": total_leads,
            "total_sent": total_sent,
            "opened_count": opened_count,
            "clicked_count": clicked_count,
            "replied_count": replied_count,
            "booked_count": booked_count,
            "open_rate": open_rate,
            "click_rate": click_rate,
            "reply_rate": reply_rate,
            "booking_rate": booking_rate,
        }
        template_stats.append(stat_item)

        # Day-by-Day Progression
        if not t_df.empty and "created_at" in t_df.columns:
            # Group by day
            t_df_dated = t_df.copy()
            # Use email_sent_at or created_at
            t_df_dated["date_dt"] = pd.to_datetime(t_df_dated["email_sent_at"].fillna(t_df_dated["created_at"]), errors="coerce")
            t_df_dated = t_df_dated[t_df_dated["date_dt"].notna()]
            if not t_df_dated.empty:
                t_df_dated["date_str"] = t_df_dated["date_dt"].dt.strftime("%Y-%m-%d")
                for d_str, g in t_df_dated.groupby("date_str"):
                    g_sent = len(g[g["status"].isin(["sent", "meeting_scheduled"])])
                    g_open = int(g["opened"].sum()) if "opened" in g.columns else 0
                    g_click = int(g["clicked_link"].sum()) if "clicked_link" in g.columns else 0
                    g_book = int(g["booking_status"].isin(["scheduled", "meeting_scheduled", "confirmation_sent", "confirmed"]).sum()) if "booking_status" in g.columns else 0

                    daily_records.append({
                        "date": d_str,
                        "template_id": tid,
                        "template_name": tname,
                        "sent": g_sent,
                        "opens": g_open,
                        "clicks": g_click,
                        "bookings": g_book,
                        "open_rate": round(g_open / g_sent * 100, 1) if g_sent else 0.0,
                        "click_rate": round(g_click / g_sent * 100, 1) if g_sent else 0.0,
                        "booking_rate": round(g_book / g_sent * 100, 1) if g_sent else 0.0,
                    })

    daily_df = pd.DataFrame(daily_records)
    if not daily_df.empty:
        daily_df = daily_df.sort_values(by="date")

    # Winner identifications (min 1 sent to qualify)
    qual_sent = [s for s in template_stats if s["total_sent"] > 0]
    best_open = max(qual_sent, key=lambda x: x["open_rate"]) if qual_sent else None
    best_click = max(qual_sent, key=lambda x: x["click_rate"]) if qual_sent else None
    best_booking = max(qual_sent, key=lambda x: x["booking_rate"]) if qual_sent else None

    return {
        "template_stats": template_stats,
        "daily_trends": daily_df,
        "best_open_rate": best_open,
        "best_click_rate": best_click,
        "best_booking_rate": best_booking,
        "total_templates_active": len([s for s in template_stats if s["total_leads"] > 0]),
    }
