import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def send_verification_email(to_email: str, first_name: str, token: str) -> None:
    settings = get_settings()
    link = f"{settings.public_base_url}/auth/verify-email?token={token}"
    logger.info(f"[email] Verification link for {to_email}: {link}")

    if (
        settings.smtp_host
        and settings.smtp_port
        and settings.smtp_user
        and settings.smtp_password
        and settings.smtp_from
    ):
        try:
            msg = EmailMessage()
            msg["Subject"] = "Verify your Dayflow HRMS Account"
            msg["From"] = settings.smtp_from
            msg["To"] = to_email
            msg.set_content(
                f"Hello {first_name},\n\n"
                f"Thank you for registering on Dayflow HRMS.\n"
                f"Please verify your email address by clicking the link below:\n\n"
                f"{link}\n\n"
                f"If you did not request this account, please ignore this email."
            )
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                server.starttls()
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
        except Exception as exc:
            logger.error(f"[email] Failed to send email via SMTP to {to_email}: {exc}")
