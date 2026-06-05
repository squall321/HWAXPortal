"""Dev mail backend — logs the rendered message to stdout. Lets the team build and test
notification flows with zero credentials. Default in dev."""

import logging

from app.mail.base import MailBackend, Message

logger = logging.getLogger("hwax.mail")


class ConsoleMailBackend(MailBackend):
    name = "console"

    def __init__(self, settings) -> None:
        self._from = settings.mail_from

    async def send(self, message: Message) -> None:
        logger.info(
            "[MAIL:console] from=%s to=%s cc=%s subject=%r\n%s",
            self._from,
            ", ".join(message.to),
            ", ".join(message.cc),
            message.subject,
            message.body_text or message.body_html,
        )
