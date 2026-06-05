"""Mail endpoint.

  POST /mail/send  — send an email from hwax@samsung.com via the active backend.
                     Admin-only + CSRF-guarded (sending mail is a powerful capability).
"""

from fastapi import APIRouter, Depends, Request

from app.auth.provider import Principal
from app.deps import require_csrf, require_role
from app.mail.base import Message
from app.schemas.mail import SendMailRequest

router = APIRouter(prefix="/mail", tags=["mail"])


@router.post("/send")
async def send_mail(
    body: SendMailRequest,
    request: Request,
    _admin: Principal = Depends(require_role("portal-admin")),
    _csrf: None = Depends(require_csrf),
) -> dict[str, str]:
    backend = request.app.state.mail_backend
    await backend.send(
        Message(
            to=body.to,
            subject=body.subject,
            body_html=body.body_html,
            body_text=body.body_text,
            cc=body.cc,
        )
    )
    return {"status": "sent", "backend": backend.name}
