# HWAX Portal

SSO hub for **`hwax.sec.samsung.net`** — federates multiple internal/external systems.
A user signs in via **AD account SSO**, lands on a catalog of linked systems, and launches
into a chosen system with their identity propagated.

The portal is a **SAML broker**:

- **SP** toward upstream Samsung AD (dev uses a mock IdP; real AD is a config swap, no code change).
- **Identity issuer** toward downstream systems — primarily short-lived **RS256 JWT** (verified via JWKS),
  with SAML assertions reserved for systems that need them (deferred until a real consumer exists).

It also sends automated mail from `hwax@samsung.com`.

## Stack

| Layer | Tech |
|---|---|
| Frontend | React + TypeScript + Vite |
| Backend | FastAPI (Python 3.13, min 3.12) |
| Upstream auth | `python3-saml` SP, config/metadata-driven |
| Token issuance | `PyJWT` RS256 + JWKS endpoint |
| Catalog | YAML registry (git = audit + CRUD) |
| Mail | pluggable: console (dev) / SMTP / MS Graph |

## Quickstart

Prereqs: Python **3.13** (or 3.12), Node 20+, pnpm.

```bash
# 1. backend venv + deps
python3.13 -m venv backend/.venv
backend/.venv/bin/python -m pip install -e "backend[dev]"

# 2. frontend deps + root orchestrator
pnpm --dir frontend install
npm install            # root: installs `concurrently`

# 3. config (dev defaults run the full mock-SSO loop with no external deps)
cp .env.example backend/.env

# 4. run both servers
pnpm dev
```

Restart cleanly anytime (kills stragglers on the ports, then relaunches):

```bash
./restart.sh        # stop + start (foreground)   ·   pnpm restart
./restart.sh --bg   # start in background → restart.log
./restart.sh stop   # stop both   ·   pnpm stop
```

- Frontend (Vite): http://localhost:5283
- Backend (FastAPI): http://localhost:8723  (docs at `/docs`)

> Dev ports (**8723** / **5283**) are deliberately uncommon to avoid collisions on shared boxes.
> The Vite dev server proxies `/auth`, `/systems`, `/mail`, `/health`, `/.well-known` to the
> backend, so the SPA is **same-origin** with the API (httpOnly session cookies + the SAML
> redirect chain behave exactly like production).

## Deploy to the real domain (`hwax.sec.samsung.net`)

The portal can run at the real domain on **mock login today**, before SSO is approved. The
backend serves the built SPA itself, so it's one process at one origin (no nginx needed).

```bash
# Option A — Docker (single image: builds SPA + serves it)
cp .env.real .env.real.filled       # then edit: set SESSION_SECRET ($ openssl rand -hex 32)
docker compose up -d                # uses .env.real via env_file

# Option B — native
pnpm --dir frontend install && pnpm --dir frontend build
python3.13 -m venv backend/.venv && backend/.venv/bin/pip install -e backend
cp .env.real backend/.env           # edit SESSION_SECRET first
backend/.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8723
```

See [`.env.real`](.env.real) for every knob and [`docs/GO-LIVE.md`](docs/GO-LIVE.md) for the
mock→real-AD switch (drop in the AD metadata, flip one env var).

## Run as Apptainer instances (shared servers / prod)

For the team's standard rootless setup — the portal + an nginx that **path-routes one domain**
to the portal and to each linked service — use `infra/` (mirrors the MXWhitePaper pattern):

```bash
cp infra/.env.example infra/.env     # set HTTP_PORT, PUBLIC_BASE_URL, SESSION_SECRET, AUTH_PROVIDER…
./infra/scripts/start.sh             # build images → build SPA → gen nginx conf → start hwax_portal + hwax_nginx
./infra/scripts/status.sh            # instances + healthchecks + active routes
./infra/scripts/restart.sh           # after editing routes.env / infra/.env
./infra/scripts/stop.sh
```

- Two rootless Apptainer instances: **`hwax_portal`** (single uvicorn: SPA + API) and **`hwax_nginx`**.
  Instance names are `hwax_*`, so they coexist with other services (`mxwp_*`, …) on one host.
- **Path routing**: `hwax.sec.samsung.net/` → portal; `…/<system-id>/` → that system. nginx upstreams
  are **generated from `backend/config/routes.env`** — a destination URL may be `localhost`, another
  server's **IP**, or a domain, so services spread across machines all route through the one origin.
- nginx listens on `HTTP_PORT` (default 8088 — rootless can't bind <1024); front it with the server's
  real `:80/:443` (corp LB / system reverse proxy). The linked services start independently (their own projects).

`restart.sh` at the repo root is the **native dev** loop (venv + pnpm); `infra/scripts/*` is the
**Apptainer** path. See `docs/architecture.md` and `docs/GO-LIVE.md`.

## Wiring a linked system (routing)

Each platform tile's **destination** is set in a dead-simple file —
[`backend/config/routes.env`](backend/config/routes.env) — one line per system:

```ini
# <system-id>=<URL>   (set it → the tile becomes clickable and opens that URL; omit → "coming_soon")
heax-hub=http://localhost:9301
ai-data-hub=http://localhost:9302
```

The names/logos/descriptions live in `backend/config/systems.yaml`; **only the port/URL is in
`routes.env`**. Edit it, then restart or `POST /systems/reload` (admin). Per-environment: dev
points at `routes.env` (localhost ports), prod at `routes.prod.env` via `ROUTES_PATH`. Any line
can be overridden by an env var `SYS_<ID>_URL` (id upper-cased, `-`→`_`) for Docker/prod.

## Auth model — the go-live switch

Everything below `handle_callback() -> Principal` is IdP-independent and written once.
Going live against real Samsung AD is a **config swap**, not a code change:

```
AUTH_PROVIDER=mock   →   AUTH_PROVIDER=saml
+ drop in the real IdP metadata / SP cert / attribute mapping (config only)
```

## Layout

```
frontend/   React + TS SPA (Vite)
backend/    FastAPI app
  app/        config, routers, auth core, catalog, mail
  config/     systems.yaml catalog + SAML metadata (non-secret)
  secrets/    keys/certs/token store (gitignored)
```

See `docs/architecture.md` for the broker pattern and launch flow (added in later phases).

## Deferred (interfaces are in place — additive later)

- Downstream **SAML IdP** (issuing assertions) — behind `DownstreamTokenIssuer`.
- **Redis** token store (multi-instance prod) — behind `TokenStore`; pilot uses SQLite.
- **OIDC** upstream (if AD moves to Azure/Entra) — behind `AuthProvider`.
