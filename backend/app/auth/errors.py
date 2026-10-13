"""Auth error types, mapped to HTTP responses at the router layer."""


class AuthError(Exception):
    """Authentication/authorization failure. Carries an HTTP status + safe message.

    `code` 를 주면 응답이 `{"detail": {"code", "message"}}` 가 된다 — 기계가 갈라 읽는
    끝점(토큰 교환)용이다. 안 주면 종전대로 `{"detail": "<message>"}` 다."""

    def __init__(self, message: str, *, status_code: int = 401, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
