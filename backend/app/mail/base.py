"""Mail abstraction. Backends (console/smtp/graph) implement `MailBackend.send`."""

from abc import ABC, abstractmethod

from pydantic import BaseModel, EmailStr, Field


class Message(BaseModel):
    to: list[EmailStr] = Field(min_length=1)
    subject: str
    body_html: str
    body_text: str | None = None
    cc: list[EmailStr] = []


class MailBackend(ABC):
    name: str

    @abstractmethod
    async def send(self, message: Message) -> None: ...
