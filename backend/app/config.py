"""Application settings, loaded from environment / backend/.env.

Fields are added per build phase to keep the surface honest (Simplicity First).
Phase 0: app identity + CORS only.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/  (parent of the app package) — anchor .env here so it loads regardless of CWD.
BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",  # tolerate not-yet-wired env vars from .env.example
    )

    # Dev ports are deliberately uncommon (8723 / 5283) to avoid collisions on shared boxes.
    # public_base_url = the origin BROWSERS reach the portal at. In dev that is the Vite
    # proxy (5283), not the uvicorn bind port (8723) — so cookies and SAML Destination URLs
    # all live on one origin. In prod the SPA + API are same-origin (the real host).
    app_env: Literal["dev", "prod"] = "dev"
    public_base_url: str = "http://localhost:5283"
    frontend_url: str = "http://localhost:5283"

    # Single-origin deploy: let the backend serve the built SPA (dist/) so the whole portal
    # is one uvicorn process at the real domain — no separate web server / proxy needed.
    serve_frontend: bool = False
    frontend_dist: str = "../frontend/dist"

    # ── Session cookie / CSRF ────────────────────────────────────────────────
    session_secret: str = "change-me-dev-only"  # HS256 key for portal session/state tokens
    cookie_secure: bool = False                  # prod MUST be true (https)
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    # ── Auth provider (the go-live switch) ───────────────────────────────────
    auth_provider: Literal["mock", "saml"] = "mock"
    mock_user_email: str = "hong.gildong@samsung.com"
    mock_user_name: str = "Hong Gil Dong"
    mock_user_groups: str = "portal-admin,mes-user"  # comma-separated

    # ── Session token TTLs (HS256; downstream RS256 launch tokens land in Phase 4) ──
    jwt_issuer: str = "https://hwax.sec.samsung.net"
    jwt_session_ttl: int = 900       # access token (s)
    jwt_refresh_ttl: int = 28800     # refresh token (s) = 8h
    jwt_state_ttl: int = 300         # login-flow state token (s)

    # ── SAML SP (used when AUTH_PROVIDER=saml). Paths are relative to backend/. ──
    # GO-LIVE: only the IdP metadata file/URL + attribute map below change — no code edits.
    # ACS/SLS URLs are DERIVED from public_base_url (see properties) so dev/prod differ by
    # one env var, and entityId is a stable logical id (need not be a reachable URL).
    saml_sp_entity_id: str = "https://hwax.sec.samsung.net/sp"
    saml_sp_cert_path: str = "config/saml/sp.crt"
    saml_sp_key_path: str = "secrets/saml/sp.key"
    saml_idp_metadata_path: str = "config/saml/dev/mock_idp_metadata.xml"  # DEV: mock IdP
    saml_idp_metadata_url: str | None = None  # PROD: real Samsung AD metadata URL (overrides path)
    # Attribute mapping: which SAML assertion attribute fills which Principal field.
    # GO-LIVE: set these to the names Samsung AD actually emits.
    saml_attr_email: str = "email"
    saml_attr_name: str = "displayName"
    saml_attr_groups: str = "memberOf"

    # ── Dev-only mock SAML IdP (a real, signing IdP fixture that exercises the SP) ──
    saml_mock_idp_enabled: bool = True
    saml_idp_cert_path: str = "config/saml/dev/idp.crt"
    saml_idp_key_path: str = "secrets/saml/idp.key"

    # ── Catalog ──────────────────────────────────────────────────────────────
    catalog_path: str = "config/systems.yaml"
    # Routing destinations. A simple `system-id=URL` file: set a system's URL here and that
    # tile becomes clickable (opens the URL); omit it and the tile stays "coming_soon".
    # systems.yaml holds the metadata (name/logo/description); routes.env holds the ports.
    # Per-env: point ROUTES_PATH at routes.dev.env (localhost ports) vs routes.prod.env.
    # A real env var SYS_<ID>_URL (id upper-cased, '-'→'_') overrides the file (docker/prod).
    routes_path: str = "config/routes.env"

    # ── Downstream launch tokens (RS256; downstream verifies via JWKS) ──────────
    # SEPARATE from the HS256 session: external systems must verify with a PUBLIC key,
    # so a shared secret is unacceptable. Keys auto-generate in dev if missing.
    jwt_keys_dir: str = "secrets/jwt"
    jwt_active_kid: str = "dev-1"
    jwt_launch_ttl: int = 90  # downstream launch token (s) — short to shrink replay window
    token_store_path: str = "secrets/token_store.sqlite"
    # Auto-generate the JWT keypair if absent. dev always does; set true to allow it in a
    # single-instance prod/mock-demo deploy too. Real multi-instance prod provisions keys.
    jwt_autogen_keys: bool = False

    # ── MCP chat (Phase 1: agent proxy + MCP registry; echo mode needs no remote) ──
    # The portal is a thin proxy + auth gate: real LLM/LangGraph/MCP fan-out lives in the
    # remote Agent Server (URL below). dev/prod swap the URL via routes.env (vLLM split).
    agent_server_url: str = "http://127.0.0.1:9000"  # remote Agent Server (SSE /chat)
    mcp_gateway_url: str = "http://127.0.0.1:9100"    # MCP Gateway (tools/list, tools/call)
    mcp_servers_path: str = "config/mcp_servers.yaml"  # MCP registry (PR-managed; admin reload)
    agent_token_audience: str = "agent-server"         # aud for the RS256 handoff token
    agent_request_timeout: float = 30.0                # per-call timeout to remote services (s)
    max_concurrent_chats: int = 64                     # SSE connections hold a worker → cap + 429
    agent_audit_log_path: str = "secrets/agent_audit.sqlite"  # who/when/which tool (Phase 1)

    # ── Mail (automated send from hwax@samsung.com) ────────────────────────────
    mail_backend: Literal["console", "smtp", "graph"] = "console"  # dev default = console
    mail_from: str = "hwax@samsung.com"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_starttls: bool = True
    graph_tenant_id: str | None = None
    graph_client_id: str | None = None
    graph_client_secret: str | None = None

    # Derived SAML URLs — single source of truth = public_base_url.
    @property
    def saml_acs_url(self) -> str:
        return f"{self.public_base_url}/auth/saml/acs"

    @property
    def saml_sls_url(self) -> str:
        return f"{self.public_base_url}/auth/saml/sls"

    @property
    def saml_mock_idp_entity_id(self) -> str:
        return f"{self.public_base_url}/auth/mock-idp"

    @property
    def saml_mock_idp_sso_url(self) -> str:
        return f"{self.public_base_url}/auth/mock-idp/sso"

    def resolve(self, rel: str) -> str:
        """Resolve a backend-relative config/secret path to an absolute path."""
        from pathlib import Path

        p = Path(rel)
        return str(p if p.is_absolute() else BACKEND_DIR / p)

    @property
    def cors_origins(self) -> list[str]:
        # Same-origin in prod (SPA served behind the portal host); dev allows the Vite origin.
        return [self.frontend_url]

    @property
    def mock_user_group_list(self) -> list[str]:
        return [g.strip() for g in self.mock_user_groups.split(",") if g.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
