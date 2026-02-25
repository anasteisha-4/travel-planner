"""
Email sending utility for password reset
Uses stdlib smtplib in a thread (avoids asyncio SSL timeout issues in Docker)
"""

import asyncio
import logging
import os
import smtplib
import ssl
from concurrent.futures import ThreadPoolExecutor
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from jinja2 import Environment, FileSystemLoader

from app.config import settings

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=2)

# Set up Jinja2 environment
template_dir = os.path.join(os.path.dirname(__file__), "templates")
jinja_env = Environment(loader=FileSystemLoader(template_dir))


def _build_mime_message(to_email: str, reset_link: str) -> MIMEMultipart:
    """Renders Jinja2 template and builds MIME message"""
    try:
        template = jinja_env.get_template("reset_password.html")
        html_content = template.render(reset_link=reset_link)
    except Exception as e:
        logger.error(f"Failed to render email template: {e}")
        # Fallback to simple text if template fails
        html_content = f"Сброс пароля: {reset_link}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Сброс пароля — Triply"
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_USER}>"
    msg["To"] = to_email

    msg.attach(MIMEText(html_content, "html", "utf-8"))
    return msg


def _send_email_sync(to_email: str, reset_link: str) -> bool:
    """Synchronous send — runs inside a thread executor"""
    if not settings.SMTP_HOST or not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning("SMTP not configured — email sending is disabled")
        return False

    msg = _build_mime_message(to_email, reset_link)

    # Try port 465 (SSL) first, then 587 (STARTTLS)
    attempts = [
        (settings.SMTP_PORT, settings.SMTP_USE_TLS),
        (587, False),
        (465, True),
    ]

    seen = set()
    unique_attempts = []
    for port, use_tls in attempts:
        key = (port, use_tls)
        if key not in seen:
            seen.add(key)
            unique_attempts.append((port, use_tls))

    last_error = None
    for port, use_tls in unique_attempts:
        try:
            if use_tls:
                ctx = ssl.create_default_context()
                with smtplib.SMTP_SSL(settings.SMTP_HOST, port, context=ctx, timeout=15) as server:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    server.sendmail(settings.SMTP_USER, to_email, msg.as_string())
            else:
                with smtplib.SMTP(settings.SMTP_HOST, port, timeout=15) as server:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    server.sendmail(settings.SMTP_USER, to_email, msg.as_string())
            logger.info(f"Password reset email sent to {to_email} via port {port}")
            return True
        except Exception as e:
            last_error = e
            logger.warning(f"SMTP attempt port {port} failed: {e}")

    logger.error(f"All SMTP attempts failed for {to_email}: {last_error}")
    return False


async def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    """
    Send password reset email. Runs smtplib in a thread to avoid
    asyncio SSL issues inside Docker on macOS.
    """
    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
    loop = asyncio.get_event_loop()
    try:
        return await loop.run_in_executor(_executor, _send_email_sync, to_email, reset_link)
    except Exception as e:
        logger.error(f"Unexpected error sending reset email to {to_email}: {e}")
        return False
