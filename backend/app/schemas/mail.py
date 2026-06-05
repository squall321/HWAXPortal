from pydantic import BaseModel, EmailStr, Field


class SendMailRequest(BaseModel):
    to: list[EmailStr] = Field(min_length=1)
    subject: str = Field(min_length=1)
    body_html: str = Field(min_length=1)
    body_text: str | None = None
    cc: list[EmailStr] = []
