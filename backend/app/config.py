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
    auth_provider: Literal["mock", "saml", "oidc"] = "mock"
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

    # ── OIDC RP (used when AUTH_PROVIDER=oidc) — portal logs users in via an OIDC IdP ──
    # GO-LIVE: set oidc_issuer (+ client id/secret) to the corp IdP — no code edits. The
    # redirect_uri to register at the IdP is DERIVED from public_base_url (see property below).
    # Leave oidc_issuer empty in dev to use the built-in mock OP (oidc_mock_idp_enabled).
    oidc_issuer: str = ""               # IdP issuer URL (its discovery base)
    oidc_discovery_url: str = ""        # override {issuer}/.well-known/openid-configuration
    oidc_client_id: str = "hwax-portal"
    oidc_client_secret: str = ""        # confidential-client secret (provision via env/secret in prod)
    oidc_scopes: str = "openid email profile groups"  # space-separated (OIDC convention)
    oidc_claim_email: str = "email"
    oidc_claim_name: str = "name"
    oidc_claim_groups: str = "groups"
    oidc_claim_subject: str = "sub"

    # ── Dev-only mock OIDC OP (a real RS256-signing OP fixture that exercises the RP) ──
    oidc_mock_idp_enabled: bool = True

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

    # ── Portal PAT (long-lived, scope="api" RS256 JWT; the REST API gateway verifies via JWKS) ──
    # SAME keystore/JWKS as launch tokens — a PAT is just longer-lived, multi-audience, scope="api".
    # Revocation = token_store jti denylist, published at /auth/pat/revoked.json for the gateway.
    pat_ttl_days: int = 90            # default PAT lifetime (days)
    pat_max_ttl_days: int = 365       # cap on a requested ttl
    # comma-separated allowlist. "mcp-gateway" = the AI surface (LLM chat + MCP tools): a PAT with
    # this audience can drive /agent/chat AND connect a personal Claude to the MCP gateway.
    pat_default_audiences: str = "mx-white-paper,heax-hub,ai-data-hub,signalforge,mcp-gateway"
    pat_chat_audience: str = "mcp-gateway"   # audience a PAT must carry to use the chat / MCP surface

    # ── MCP chat (Phase 1: agent proxy + MCP registry; echo mode needs no remote) ──
    # The portal is a thin proxy + auth gate: real LLM/LangGraph/MCP fan-out lives in the
    # remote Agent Server (URL below). dev/prod swap the URL via routes.env (vLLM split).
    agent_server_url: str = "http://127.0.0.1:9009"  # Agent Server (SSE /chat); 9000 is MinIO here
    mcp_gateway_url: str = "http://127.0.0.1:9110"    # MCP Gateway (HWAXMcpGateway; aggregates the 3 MCPs). :9100 was node_exporter.
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

    # Derived OIDC URLs — single source of truth = public_base_url.
    @property
    def oidc_redirect_uri(self) -> str:
        # Register THIS at the IdP. The generic /auth/callback handles the OIDC code+state.
        return f"{self.public_base_url}/auth/callback"

    @property
    def oidc_mock_issuer(self) -> str:
        return f"{self.public_base_url}/auth/oidc-mock"

    @property
    def oidc_discovery(self) -> str:
        """Where the RP fetches the IdP's OpenID configuration (explicit > issuer > dev mock)."""
        if self.oidc_discovery_url:
            return self.oidc_discovery_url
        if self.oidc_issuer:
            return f"{self.oidc_issuer.rstrip('/')}/.well-known/openid-configuration"
        return f"{self.oidc_mock_issuer}/.well-known/openid-configuration"

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

    @property
    def pat_default_audience_list(self) -> list[str]:
        return [a.strip() for a in self.pat_default_audiences.split(",") if a.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
