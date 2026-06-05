"""SMTP mail backend (aiosmtplib). Fallback for hwax@samsung.com if Graph is delayed."""

from email.message import EmailMessage

import aiosmtplib

from app.mail.base import MailBackend, Message


class SmtpMailBackend(MailBackend):
    name = "smtp"

    def __init__(self, settings) -> None:
        self._s = settings
        if not settings.smtp_host:
            raise RuntimeError("MAIL_BACKEND=smtp requires SMTP_HOST")

    async def send(self, message: Message) -> None:
        msg = EmailMessage()
        msg["From"] = self._s.mail_from
        msg["To"] = ", ".join(message.to)
        if message.cc:
            msg["Cc"] = ", ".join(message.cc)
        msg["Subject"] = message.subject
        msg.set_content(message.body_text or "")
        msg.add_alternative(message.body_html, subtype="html")

        await aiosmtplib.send(
            msg,
            hostname=self._s.smtp_host,
            port=self._s.smtp_port,
            start_tls=self._s.smtp_starttls,
            username=self._s.smtp_username,
            password=self._s.smtp_password,
        )
