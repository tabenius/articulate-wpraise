"""Email service for sending transactional emails via Postfix SMTP."""

import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST", "postfix")
SMTP_PORT = int(os.getenv("SMTP_PORT", "25"))
MAIL_FROM = os.getenv("MAIL_FROM", "verify@ragbaz.xyz")
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "Articulate")
APP_URL = os.getenv("APP_URL", "https://app.ragbaz.xyz")


def _send(to: str, subject: str, html: str, text: str) -> bool:
    """Send an email via SMTP. Returns True on success."""
    msg = MIMEMultipart("alternative")
    msg["From"] = f"{MAIL_FROM_NAME} <{MAIL_FROM}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
            smtp.sendmail(MAIL_FROM, [to], msg.as_string())
        logger.info("Email sent to %s: %s", to, subject)
        return True
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to, e)
        return False


def send_verification_email(to: str, name: str, token: str) -> bool:
    """Send account verification email."""
    verify_url = f"{APP_URL}/auth/verify?token={token}"
    subject = "Verify your Articulate account"

    html = f"""
    <div style="font-family:system-ui,sans-serif;max-width:560px;margin:0 auto;padding:32px">
      <h2 style="margin:0 0 16px">Welcome to Articulate{', ' + name if name else ''}!</h2>
      <p style="color:#555;line-height:1.6">
        Please verify your email address to activate your account.
      </p>
      <p style="margin:24px 0">
        <a href="{verify_url}"
           style="background:#18181b;color:#fff;padding:12px 24px;border-radius:6px;
                  text-decoration:none;display:inline-block;font-weight:500">
          Verify Email Address
        </a>
      </p>
      <p style="color:#888;font-size:13px">
        Or copy this link: <a href="{verify_url}" style="color:#888">{verify_url}</a>
      </p>
      <p style="color:#888;font-size:13px">This link expires in 24 hours.</p>
      <hr style="border:none;border-top:1px solid #eee;margin:24px 0">
      <p style="color:#aaa;font-size:12px">Articulate &mdash; AI-powered WordPress management</p>
    </div>
    """

    text = (
        f"Welcome to Articulate{', ' + name if name else ''}!\n\n"
        f"Verify your email: {verify_url}\n\n"
        "This link expires in 24 hours."
    )

    return _send(to, subject, html, text)


def send_password_reset_email(to: str, name: str, token: str) -> bool:
    """Send password reset email."""
    reset_url = f"{APP_URL}/auth/reset?token={token}"
    subject = "Reset your Articulate password"

    html = f"""
    <div style="font-family:system-ui,sans-serif;max-width:560px;margin:0 auto;padding:32px">
      <h2 style="margin:0 0 16px">Password Reset</h2>
      <p style="color:#555;line-height:1.6">
        Hi{' ' + name if name else ''}, we received a request to reset your password.
      </p>
      <p style="margin:24px 0">
        <a href="{reset_url}"
           style="background:#18181b;color:#fff;padding:12px 24px;border-radius:6px;
                  text-decoration:none;display:inline-block;font-weight:500">
          Reset Password
        </a>
      </p>
      <p style="color:#888;font-size:13px">
        Or copy this link: <a href="{reset_url}" style="color:#888">{reset_url}</a>
      </p>
      <p style="color:#888;font-size:13px">This link expires in 1 hour. If you didn't request this, ignore this email.</p>
      <hr style="border:none;border-top:1px solid #eee;margin:24px 0">
      <p style="color:#aaa;font-size:12px">Articulate &mdash; AI-powered WordPress management</p>
    </div>
    """

    text = (
        f"Hi{' ' + name if name else ''},\n\n"
        f"Reset your password: {reset_url}\n\n"
        "This link expires in 1 hour. If you didn't request this, ignore this email."
    )

    return _send(to, subject, html, text)
