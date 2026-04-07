"""Email service for Voxclar — branded HTML emails via Zoho SMTP."""
import asyncio
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

from src.config import get_settings

settings = get_settings()

DISCORD_URL = "https://discord.gg/eXu9mfDh"
WEBSITE_URL = "https://voxclar.com"
SUPPORT_EMAIL = "service@voxclar.com"

# ── Base HTML template ───────────────────────────────────────────

LOGO_URL = f"{WEBSITE_URL}/images/logo.png"

def _base_template(title: str, body_html: str) -> str:
    year = datetime.now().year
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
</head>
<body style="margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',sans-serif;-webkit-font-smoothing:antialiased;" bgcolor="#000000">
<table width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#000000" style="background-color:#000000;">
<tr><td align="center" style="padding:40px 16px;">

<table width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;width:100%;">

<!-- Logo Row -->
<tr><td style="padding:0 0 28px;" align="left">
  <table cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td style="padding-right:12px;vertical-align:middle;">
      <img src="{LOGO_URL}" alt="Voxclar" width="40" height="40" style="display:block;border:0;border-radius:8px;" />
    </td>
    <td style="vertical-align:middle;">
      <span style="font-size:26px;font-weight:700;letter-spacing:-0.5px;">
        <span style="color:#ffdd02;">Vox</span><span style="color:#ffffff;">clar</span>
      </span>
    </td>
  </tr>
  </table>
</td></tr>

<!-- Card -->
<tr><td>
  <table width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#1a1a1a" style="background-color:#1a1a1a;border-radius:16px;border:1px solid #2a2a2a;">
  <tr><td style="padding:40px 36px;">
    {body_html}
  </td></tr>
  </table>
</td></tr>

<!-- Footer -->
<tr><td style="padding:32px 0 0;" align="center">
  <p style="margin:0 0 14px;font-size:13px;">
    <a href="{WEBSITE_URL}" style="color:#ffdd02;text-decoration:none;font-weight:500;">Website</a>
    <span style="color:#555555;">&nbsp;&nbsp;&#8226;&nbsp;&nbsp;</span>
    <a href="{DISCORD_URL}" style="color:#ffdd02;text-decoration:none;font-weight:500;">Discord</a>
    <span style="color:#555555;">&nbsp;&nbsp;&#8226;&nbsp;&nbsp;</span>
    <a href="{WEBSITE_URL}/docs" style="color:#ffdd02;text-decoration:none;font-weight:500;">API Docs</a>
  </p>
  <p style="margin:0 0 8px;font-size:11px;color:#666666;">
    &copy; {year} Voxclar. All rights reserved.
  </p>
  <p style="margin:0;font-size:11px;color:#555555;">
    Questions? Reply to this email or contact <a href="mailto:{SUPPORT_EMAIL}" style="color:#888888;text-decoration:underline;">{SUPPORT_EMAIL}</a>
  </p>
</td></tr>

</table>

</td></tr>
</table>
</body>
</html>"""


# ── Send email (sync via thread to avoid blocking) ───────────────

def _send_sync(to_email: str, subject: str, html_body: str):
    msg = MIMEMultipart("alternative")
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_USER}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=ctx) as server:
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)


async def send_email(to_email: str, subject: str, html_body: str):
    """Send email asynchronously (runs SMTP in thread pool)."""
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _send_sync, to_email, subject, html_body)
    except Exception as e:
        # Never let email failure crash the main flow
        print(f"[EMAIL ERROR] Failed to send to {to_email}: {e}")


# ── Email builders ───────────────────────────────────────────────

def _heading(text: str) -> str:
    return f'<h1 style="margin:0 0 16px;font-size:24px;font-weight:700;color:#ffffff;">{text}</h1>'

def _text(text: str) -> str:
    return f'<p style="margin:0 0 16px;font-size:14px;line-height:1.7;color:#b0b0b0;">{text}</p>'

def _gold_text(text: str) -> str:
    return f'<span style="color:#ffdd02;font-weight:600;">{text}</span>'

def _button(url: str, label: str, color: str = "#ffdd02", text_color: str = "#000000") -> str:
    return f'''\
<table cellpadding="0" cellspacing="0" border="0" style="margin:24px 0;">
<tr><td bgcolor="{color}" style="background-color:{color};border-radius:8px;padding:14px 32px;text-align:center;">
  <a href="{url}" style="color:{text_color};text-decoration:none;font-size:14px;font-weight:700;display:inline-block;">{label}</a>
</td></tr>
</table>'''

def _info_row(label: str, value: str) -> str:
    return f'''\
<tr>
  <td style="padding:10px 0;font-size:13px;color:#777777;width:140px;border-bottom:1px solid #2a2a2a;">{label}</td>
  <td style="padding:10px 0;font-size:13px;color:#e0e0e0;font-weight:500;border-bottom:1px solid #2a2a2a;">{value}</td>
</tr>'''

def _info_table(rows: list[tuple[str, str]]) -> str:
    inner = "".join(_info_row(label, val) for label, val in rows)
    return f'<table cellpadding="0" cellspacing="0" border="0" style="margin:16px 0;width:100%;">{inner}</table>'

def _divider() -> str:
    return '<hr style="border:none;border-top:1px solid #333333;margin:24px 0;">'

def _discord_block() -> str:
    return f'''\
{_divider()}
<p style="margin:0;font-size:13px;color:#999999;">
  Join our community on <a href="{DISCORD_URL}" style="color:#ffdd02;text-decoration:none;font-weight:600;">Discord</a> for tips, support, and updates.
</p>'''


# ── Verification code ───────────────────────────────────────────

async def send_verification_code(email: str, code: str):
    body = (
        _heading("Verify Your Email")
        + _text("Enter this code in the app to complete your registration:")
        + '<div style="margin:24px 0;text-align:center;">'
        + f'<span style="font-size:36px;font-weight:700;letter-spacing:12px;color:#ffdd02;font-family:monospace;background:#2a2500;padding:16px 32px;border-radius:12px;border:2px solid #3d3600;display:inline-block;">{code}</span>'
        + '</div>'
        + _text("This code expires in <strong style=\"color:#e0e0e0;\">10 minutes</strong>. If you didn't request this, ignore this email.")
    )
    html = _base_template("Verify Your Email", body)
    await send_email(email, "Voxclar — Email Verification Code", html)


# ── Welcome (registration) ──────────────────────────────────────

async def send_welcome_email(email: str, username: str):
    body = (
        _heading(f"Welcome to Voxclar, {username}!")
        + _text("Your account has been created successfully. You're ready to start using AI-powered meeting assistance.")
        + _info_table([
            ("Account", email),
            ("Plan", "Free (10 min)"),
        ])
        + _text("Get started by downloading the app and starting your first meeting. Upgrade anytime for more minutes and premium features.")
        + _button(WEBSITE_URL, "Get Started")
        + _discord_block()
    )
    html = _base_template("Welcome to Voxclar", body)
    await send_email(email, "Welcome to Voxclar — Your AI Meeting Assistant", html)


# ── Subscription activated ──────────────────────────────────────

async def send_subscription_email(email: str, username: str, plan: str, minutes: int, price: float):
    plan_display = plan.capitalize()
    body = (
        _heading("Subscription Activated!")
        + _text(f"Hi {username}, your {_gold_text(plan_display)} plan is now active. Thank you for your purchase!")
        + _info_table([
            ("Plan", plan_display),
            ("Minutes", f"{minutes} min/month"),
            ("Price", f"${price:.2f}/mo"),
            ("Billing", "Auto-renew monthly"),
        ])
        + _text("Your minutes have been credited to your account. Cloud data sync and premium AI models are now available.")
        + _button(WEBSITE_URL, "Open Voxclar")
        + _discord_block()
    )
    html = _base_template(f"Subscription: {plan_display}", body)
    await send_email(email, f"Voxclar {plan_display} Plan — Subscription Confirmed", html)


# ── Lifetime license ────────────────────────────────────────────

async def send_lifetime_email(email: str, username: str, license_key: str):
    body = (
        _heading("Lifetime License Activated!")
        + _text(f"Hi {username}, congratulations! Your lifetime license is now active. You have unlimited access to Voxclar — forever.")
        + _info_table([
            ("License Key", f'<code style="color:#ffdd02;background:#2a2500;padding:2px 8px;border-radius:4px;">{license_key}</code>'),
            ("Plan", "Lifetime — Unlimited"),
            ("ASR", "Local (faster-whisper)"),
            ("AI Models", "Bring your own API keys"),
        ])
        + _text("Your license is device-locked. Set up your AI API keys in Settings to start using AI-powered answers.")
        + _button(WEBSITE_URL, "Open Voxclar")
        + _divider()
        + _text('<span style="font-size:12px;color:#777777;">Save this email — your license key is shown above. You can also view it in the app.</span>')
        + _discord_block()
    )
    html = _base_template("Lifetime License", body)
    await send_email(email, "Voxclar Lifetime License — Welcome!", html)


# ── Subscription renewal ────────────────────────────────────────

async def send_renewal_email(email: str, username: str, plan: str, minutes: int, price: float):
    plan_display = plan.capitalize()
    body = (
        _heading("Subscription Renewed")
        + _text(f"Hi {username}, your {_gold_text(plan_display)} subscription has been renewed successfully.")
        + _info_table([
            ("Plan", plan_display),
            ("Minutes Credited", f"{minutes} min"),
            ("Amount Charged", f"${price:.2f}"),
        ])
        + _text("Your minutes have been reset for this billing cycle. Keep having great meetings!")
        + _discord_block()
    )
    html = _base_template("Subscription Renewed", body)
    await send_email(email, f"Voxclar — {plan_display} Subscription Renewed", html)


# ── Subscription cancelled ──────────────────────────────────────

async def send_cancellation_email(email: str, username: str, plan: str):
    plan_display = plan.capitalize()
    body = (
        _heading("Subscription Cancelled")
        + _text(f"Hi {username}, your {_gold_text(plan_display)} subscription has been cancelled.")
        + _text("You'll continue to have access until the end of your current billing period. After that, your account will revert to the Free plan.")
        + _text("If this was a mistake, you can resubscribe anytime from the Subscription page in the app.")
        + _button(WEBSITE_URL, "Resubscribe", "#ffdd02", "#000")
        + _divider()
        + _text('<span style="font-size:12px;color:#777777;">We\'d love to know why you cancelled. Reply to this email and let us know — your feedback helps us improve.</span>')
        + _discord_block()
    )
    html = _base_template("Subscription Cancelled", body)
    await send_email(email, "Voxclar — Subscription Cancelled", html)


# ── Time Boost purchase ─────────────────────────────────────────

async def send_topup_email(email: str, username: str, minutes: int, price: float):
    body = (
        _heading("Time Boost Added!")
        + _text(f"Hi {username}, your Time Boost has been applied to your account.")
        + _info_table([
            ("Minutes Added", f"+{minutes} min"),
            ("Amount", f"${price:.2f}"),
            ("Expiration", "Never expires"),
        ])
        + _text("Boost minutes are used after your subscription minutes run out.")
        + _discord_block()
    )
    html = _base_template("Time Boost", body)
    await send_email(email, "Voxclar — Time Boost Confirmed", html)


# ── ASR Minutes purchase ────────────────────────────────────────

async def send_asr_topup_email(email: str, username: str, minutes: int, price: float, api_key: str | None = None):
    api_section = ""
    if api_key:
        api_section = (
            _divider()
            + _text('Your API key has been generated:')
            + f'<p style="margin:8px 0 16px;font-family:monospace;font-size:13px;color:#ffdd02;background:#2a2500;padding:12px 16px;border-radius:8px;border:1px solid #3d3600;word-break:break-all;">{api_key}</p>'
            + _text('API Endpoint: <code style="color:#aaaaaa;">https://api.voxclar.com/v1/listen</code>')
            + _button(f"{WEBSITE_URL}/docs", "View API Docs", "#9333ea", "#ffffff")
        )

    body = (
        _heading("ASR Minutes Added!")
        + _text(f"Hi {username}, your Voxclar Cloud ASR minutes have been credited.")
        + _info_table([
            ("Minutes Added", f"+{minutes} min"),
            ("Amount", f"${price:.2f}"),
            ("Usage", 'Select "Voxclar Cloud ASR" in Settings'),
        ])
        + api_section
        + _discord_block()
    )
    html = _base_template("ASR Minutes", body)
    await send_email(email, "Voxclar — Cloud ASR Minutes Confirmed", html)


# ── API Key generated ───────────────────────────────────────────

async def send_api_key_email(email: str, username: str, api_key: str):
    body = (
        _heading("API Key Generated")
        + _text(f"Hi {username}, your Voxclar Cloud ASR API key is ready.")
        + f'<p style="margin:16px 0;font-family:monospace;font-size:13px;color:#ffdd02;background:#2a2500;padding:14px 16px;border-radius:8px;border:1px solid #3d3600;word-break:break-all;">{api_key}</p>'
        + _text("Use this key to access the Voxclar Cloud ASR API programmatically. Keep it secret — do not share it publicly.")
        + _info_table([
            ("Endpoint", '<code style="color:#aaaaaa;">https://api.voxclar.com/v1/listen</code>'),
            ("Docs", f'<a href="{WEBSITE_URL}/docs" style="color:#ffdd02;">{WEBSITE_URL}/docs</a>'),
        ])
        + _button(f"{WEBSITE_URL}/docs", "View API Documentation", "#9333ea", "#ffffff")
        + _discord_block()
    )
    html = _base_template("API Key", body)
    await send_email(email, "Voxclar — Your API Key", html)


# ── Product update / newsletter ─────────────────────────────────

async def send_update_email(email: str, username: str, subject: str, update_title: str, update_body: str, cta_url: str | None = None, cta_label: str = "Learn More"):
    body = (
        _heading(update_title)
        + _text(f"Hi {username},")
        + update_body
    )
    if cta_url:
        body += _button(cta_url, cta_label)
    body += _discord_block()
    html = _base_template(update_title, body)
    await send_email(email, subject, html)
