"""Microsoft Graph mail backend — recommended for prod (M365).

Sends as the shared mailbox via client-credentials OAuth, avoiding stored mailbox passwords
and SMTP-AUTH (which Microsoft is deprecating). The portal already speaks OAuth/AD for SSO,
so the credential model is consistent. The app registration needs Mail.Send application
permission for hwax@samsung.com.
"""

import time

import httpx

from app.mail.base import MailBackend, Message


class GraphMailBackend(MailBackend):
    name = "graph"

    def __init__(self, settings) -> None:
        self._s = settings
        if not (
            settings.graph_tenant_id
            and settings.graph_client_id
            and settings.graph_client_secret
        ):
            raise RuntimeError(
                "MAIL_BACKEND=graph requires GRAPH_TENANT_ID/CLIENT_ID/CLIENT_SECRET"
            )
        self._token: str | None = None
        self._token_exp: float = 0.0

    async def _access_token(self) -> str:
        if self._token and time.time() < self._token_exp - 60:
            return self._token
        url = f"https://login.microsoftonline.com/{self._s.graph_tenant_id}/oauth2/v2.0/token"
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                url,
                data={
                    "client_id": self._s.graph_client_id,
                    "client_secret": self._s.graph_client_secret,
                    "scope": "https://graph.microsoft.com/.default",
                    "grant_type": "client_credentials",
                },
            )
            r.raise_for_status()
            data = r.json()
        self._token = data["access_token"]
        self._token_exp = time.time() + int(data.get("expires_in", 3600))
        return self._token

    async def send(self, message: Message) -> None:
        token = await self._access_token()
        payload = {
            "message": {
                "subject": message.subject,
                "body": {"contentType": "HTML", "content": message.body_html},
                "toRecipients": [{"emailAddress": {"address": a}} for a in message.to],
                "ccRecipients": [{"emailAddress": {"address": a}} for a in message.cc],
            },
            "saveToSentItems": True,
        }
        url = f"https://graph.microsoft.com/v1.0/users/{self._s.mail_from}/sendMail"
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(url, json=payload, headers={"Authorization": f"Bearer {token}"})
            r.raise_for_status()
