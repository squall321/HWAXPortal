# Linked services — how each tile connects (proxy vs external-url, strip vs pass)

The portal federates 6 platforms. Each tile is either a **proxy** (served under the portal domain
at `/<id>/` via nginx) or an **external-url** (the tile links directly to the service's own address).
Set per platform in `backend/config/systems.yaml` (`integration_type`); proxy destinations live in
`backend/config/routes.env`.

## The two proxy sub-modes (the subtle part)

`gen-nginx-conf.sh` uses the routes.env URL **verbatim**, so the trailing slash decides whether the
`/<id>/` prefix is **passed through** or **stripped** — pick the one that matches how the service
serves its assets:

| Service | routes.env | nginx | Why |
|---|---|---|---|
| mx-white-paper | `http://localhost:5173` (no slash) | **pass** `/mx-white-paper/` through | `vite preview` serves the built dist **under** the base `/mx-white-paper/` |
| heax-hub | `http://localhost:4180/` (slash) | **strip** prefix → `/` | Caddy serves at root; dist built with base `/heax-hub/` so HTML URLs carry the prefix |
| ai-data-hub | `http://localhost:8001/` (slash) | **strip** prefix → `/` | FastAPI serves `/dashboard`,`/api`,`/static` at root; dashboard derives its own prefix |
| report-archive | `http://127.0.0.1:3000/` (slash) | **strip** prefix → `/` | Combined FastAPI serves SPA+`/api` at root; dist built with base `/report-archive/` so HTML URLs carry the prefix |

Rule of thumb:
- Service serves **under** the sub-path (e.g. `vite preview` with `base`) → **no trailing slash** (pass).
- Service serves at its **root** (Caddy/nginx/FastAPI at `/`) but its built assets carry the prefix
  → **trailing slash** (strip).

Either way the service must be **built/configured for the sub-path** so its asset/router/api URLs
carry `/<id>/`. Each linked repo documents that in its own `docs/HWAX-PORTAL-INTEGRATION.md`:
- MX White Paper: `MXWP_BASE_PATH=/mx-white-paper/` → build + `vite preview`.
- HEAX Hub: `HEAX_BASE_PATH=/heax-hub/` → `pnpm build`; Caddy unchanged.
- AI Data Hub: `AIDH_ROOT_PATH=/ai-data-hub` → uvicorn `--root-path`; dashboard derives the prefix.
- Report Archive: `vite build --base=/report-archive/` + React Router `basename` 1-line; combined FastAPI serves dist. See its repo `SSO_SETUP.local.md §A` (+ portal `docs/REPORTARCHIVE-FEATURE-SUMMARY.md`).

## external-url tiles (no proxy)

Services with their own reachable address link directly (new tab) — set `integration_type:
external-url` + `url:` in systems.yaml, NOT in routes.env:
- smart-twin-cluster → `https://stcx.sec.samsung.net`
- spdm → `https://spdm.sec.samsung.net`
<!-- report-archive moved to the proxy table above — sub-path support added (vite base + router basename), now proxied at /report-archive/. -->

## Frontend behaviour

`PortalHomePage.onOpen` (frontend): `proxy` tiles open `/<id>/` (same origin); `external-url` tiles
open their `url`; `jwt/saml-handoff` go through `/launch/<id>`. The backend `_to_read` only exposes
`url` for external-url tiles, so internal proxy targets never reach the browser.
