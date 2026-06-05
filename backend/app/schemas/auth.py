"""API response models for the auth surface."""

from pydantic import BaseModel


class UserProfile(BaseModel):
    """What GET /auth/me returns — the current user as the SPA sees it."""

    subject: str
    email: str
    display_name: str | None = None
    groups: list[str] = []
