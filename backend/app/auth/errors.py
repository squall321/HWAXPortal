"""Auth error types, mapped to HTTP responses at the router layer."""


class AuthError(Exception):
    """Authentication/authorization failure. Carries an HTTP status + safe message."""

    def __init__(self, message: str, *, status_code: int = 401) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
