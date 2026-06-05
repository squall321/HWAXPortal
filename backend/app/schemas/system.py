"""Linked-system catalog models.

A LinkedSystem describes one tile on the portal home. `integration_type` drives how the
launch (Phase 4) behaves:
  - external-url : a plain bookmark; the SPA opens `url` directly, no identity propagated.
  - jwt-handoff  : portal mints a short-lived audience-scoped JWT and hands it off.
  - saml-handoff : portal issues a SAML assertion (downstream SAML-IdP; deferred).
"""

from typing import Literal

from pydantic import BaseModel, Field

IntegrationType = Literal["external-url", "jwt-handoff", "saml-handoff"]
HandoffMode = Literal["redirect", "auto_post"]
Status = Literal["available", "coming_soon"]
# Signature gradient theme per platform (frontend maps these to colors).
Accent = Literal["violet", "cyan", "amber", "emerald", "sky", "rose", "indigo"]


class LinkedSystem(BaseModel):
    id: str
    name: str
    description: str | None = None  # the rich paragraph shown on the card
    tagline: str | None = None  # short punchy line under the name
    icon: str | None = None  # emoji fallback; the SPA draws a custom SVG logo by id
    accent: Accent = "indigo"  # signature gradient theme
    category: str | None = None
    status: Status = "available"  # "coming_soon" → tile renders but does not launch yet
    url: str | None = None  # base/launch URL (absent until the link is wired)
    integration_type: IntegrationType = "external-url"
    audience: str | None = None  # token `aud` for jwt/saml handoff
    handoff_mode: HandoffMode = "auto_post"
    handoff_param: str = "token"  # form field / query param the downstream expects
    required_role: str | None = None  # gate: hide tile unless user has this group/role
    enabled: bool = True
    sort_order: int = 100


class CatalogFile(BaseModel):
    """Top-level shape of config/systems.yaml — validated on load (fail fast on typos)."""

    systems: list[LinkedSystem] = Field(default_factory=list)


class SystemRead(BaseModel):
    """Tile as the SPA sees it (no internal handoff secrets beyond what it needs)."""

    id: str
    name: str
    description: str | None = None
    tagline: str | None = None
    icon: str | None = None
    accent: Accent = "indigo"
    category: str | None = None
    status: Status = "available"
    integration_type: IntegrationType
    # For external-url the SPA opens this directly; for handoffs it calls /systems/{id}/launch.
    url: str | None = None
