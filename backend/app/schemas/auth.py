"""API response models for the auth surface."""

from pydantic import BaseModel


class UserProfile(BaseModel):
    """What GET /auth/me returns — the current user as the SPA sees it."""

    subject: str
    email: str
    display_name: str | None = None
    groups: list[str] = []
    department: str = ""  # users 원장(가입 입력 또는 RA 연결 자동 채움) — 세션 JWT 에는 없음
