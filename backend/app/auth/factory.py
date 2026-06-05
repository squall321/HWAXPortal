"""Selects the active AuthProvider from config. The go-live switch lives here."""

from app.auth.provider import AuthProvider
from app.config import Settings


def build_auth_provider(settings: Settings) -> AuthProvider:
    if settings.auth_provider == "mock":
        from app.auth.mock_provider import MockProvider

        return MockProvider(settings)
    if settings.auth_provider == "saml":
        # Implemented in Phase 2 (python3-saml SP). Same interface, config-driven.
        from app.auth.saml_provider import SamlProvider

        return SamlProvider(settings)
    raise ValueError(f"unknown AUTH_PROVIDER: {settings.auth_provider}")
