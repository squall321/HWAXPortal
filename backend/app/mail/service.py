"""Selects the active mail backend from config (MAIL_BACKEND). Swap = env only."""

from app.config import Settings
from app.mail.base import MailBackend


def build_mail_backend(settings: Settings) -> MailBackend:
    if settings.mail_backend == "console":
        from app.mail.console import ConsoleMailBackend

        return ConsoleMailBackend(settings)
    if settings.mail_backend == "smtp":
        from app.mail.smtp import SmtpMailBackend

        return SmtpMailBackend(settings)
    if settings.mail_backend == "graph":
        from app.mail.graph import GraphMailBackend

        return GraphMailBackend(settings)
    raise ValueError(f"unknown MAIL_BACKEND: {settings.mail_backend}")
