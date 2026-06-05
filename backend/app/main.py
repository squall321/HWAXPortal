"""HWAX Portal backend — application assembly.

Routers are wired in as each build phase lands.
Phase 0: health.  Phase 1: auth session + AuthProvider/JWTService on app.state.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import routes_health
from app.auth.downstream import JwtDownstreamIssuer
from app.auth.errors import AuthError
from app.auth.keystore import KeyStore
from app.auth.routes import jwks as auth_jwks
from app.auth.routes import launch as auth_launch
from app.auth.routes import saml as auth_saml
from app.auth.routes import session as auth_session
from app.auth.token_store import TokenStore
from app.catalog import routes as catalog_routes
from app.catalog.registry import CatalogRegistry
from app.config import get_settings
from app.deps import build_services
from app.mail import routes as mail_routes
from app.mail.service import build_mail_backend

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Build the active auth provider + session token service + catalog once, from config.
    app.state.auth_provider, app.state.jwt_service = build_services(settings)
    app.state.catalog = CatalogRegistry(settings)
    # Downstream propagation: RS256 keystore (auto-gen in dev), launch-token issuer, jti store.
    app.state.keystore = KeyStore(settings)
    app.state.downstream_issuer = JwtDownstreamIssuer(settings, app.state.keystore)
    app.state.token_store = TokenStore(settings)
    # Mail backend (console in dev; smtp/graph via MAIL_BACKEND env).
    app.state.mail_backend = build_mail_backend(settings)
    yield


app = FastAPI(
    title="HWAX Portal API",
    version="0.1.0",
    description="SSO broker + system catalog + mail for hwax.sec.samsung.net",
    lifespan=lifespan,
)

# Same-origin in prod; dev permits the Vite origin so the SPA can call the API with cookies.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,  # required for httpOnly session cookie
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AuthError)
async def _auth_error_handler(_request: Request, exc: AuthError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


app.include_router(routes_health.router)
app.include_router(auth_session.router)
app.include_router(auth_saml.router)
app.include_router(auth_jwks.router)
app.include_router(catalog_routes.router)
app.include_router(auth_launch.router)
app.include_router(mail_routes.router)

# Dev-only mock SAML IdP — a real signing IdP fixture to exercise the SP path.
if settings.app_env == "dev" and settings.saml_mock_idp_enabled:
    from app.auth.routes import mock_idp

    app.include_router(mock_idp.router)

# Dev-only fake downstream — proves the launch token verifies via JWKS + replay defense.
if settings.app_env == "dev":
    from app.auth.routes import dev_downstream

    app.include_router(dev_downstream.router)


# Single-origin deploy: serve the built SPA from the backend so the portal is one process
# at the real domain. Registered LAST so all API routes match first; unknown paths fall back
# to index.html (client-side routing).
if settings.serve_frontend:
    from pathlib import Path

    from fastapi import Request
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    from app.config import BACKEND_DIR

    dist = Path(settings.frontend_dist)
    if not dist.is_absolute():
        dist = (BACKEND_DIR / dist).resolve()
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str, request: Request) -> FileResponse:
        # API routers are registered above and match first; this catches SPA routes only.
        candidate = (dist / full_path).resolve()
        if full_path and candidate.is_file() and dist in candidate.parents:
            return FileResponse(candidate)  # real static file (favicon, etc.)
        return FileResponse(dist / "index.html")  # SPA route → let the client router handle it
