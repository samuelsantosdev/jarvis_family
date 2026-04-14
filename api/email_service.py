"""
Email sending service using aiosmtplib (async SMTP).
Falls back to a no-op/console log when SMTP credentials are not configured.
"""
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from api.config import (
    EMAILS_FROM_EMAIL,
    EMAILS_FROM_NAME,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USER,
)

logger = logging.getLogger(__name__)


async def _send_email(to_email: str, subject: str, html_body: str) -> None:
    """Send an HTML email.  Falls back to logging when SMTP is not configured."""
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning(
            "SMTP not configured – email to <%s> subject=%r would have been sent.",
            to_email,
            subject,
        )
        logger.info("Email body:\n%s", html_body)
        return

    try:
        import aiosmtplib  # imported lazily so the app starts without it when not needed

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{EMAILS_FROM_NAME} <{EMAILS_FROM_EMAIL}>"
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html"))

        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
            start_tls=True,
        )
        logger.info("Email sent to <%s>", to_email)
    except aiosmtplib.SMTPException as exc:
        logger.error("SMTP error sending email to <%s>: %s", to_email, exc)
    except Exception as exc:
        logger.error("Unexpected error sending email to <%s> (%s): %s", to_email, type(exc).__name__, exc)


async def send_confirmation_email(to_email: str, name: str, token: str, base_url: str) -> None:
    confirm_url = f"{base_url}/auth/confirm/{token}"
    subject = "Confirm your Jarvis Family account"
    html = f"""
    <html><body>
      <h2>Hello, {name}!</h2>
      <p>Thank you for registering with Jarvis Family.</p>
      <p>Please confirm your email address by clicking the link below:</p>
      <p><a href="{confirm_url}" style="background:#4CAF50;color:white;padding:10px 20px;
         text-decoration:none;border-radius:4px;">Confirm Email</a></p>
      <p>Or copy and paste this URL into your browser:</p>
      <p>{confirm_url}</p>
      <p>This link is valid for 24 hours.</p>
    </body></html>
    """
    await _send_email(to_email, subject, html)


async def send_welcome_email(to_email: str, name: str) -> None:
    subject = "Welcome to Jarvis Family!"
    html = f"""
    <html><body>
      <h2>Welcome, {name}! 🎉</h2>
      <p>Your email address has been confirmed and your Jarvis Family account is now active.</p>
      <p>You can now log in and start using the application.</p>
    </body></html>
    """
    await _send_email(to_email, subject, html)
