# HWAX Portal — single-origin production image.
# Builds the SPA, then runs the FastAPI backend which serves that SPA itself
# (SERVE_FRONTEND=true) → one process answering at the real domain.

# ── Stage 1: build the React/Vite SPA ────────────────────────────────────────
FROM node:20-slim AS web
WORKDIR /app/frontend
RUN corepack enable
COPY frontend/package.json frontend/pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile || pnpm install
COPY frontend/ ./
RUN pnpm build   # → /app/frontend/dist

# ── Stage 2: Python backend that serves the API + the built SPA ──────────────
FROM python:3.13-slim AS app
# Runtime libs for python3-saml/xmlsec/lxml (self-contained wheels usually suffice;
# these are a cheap safety net for the manylinux wheels' shared deps).
RUN apt-get update && apt-get install -y --no-install-recommends \
        libxml2 libxmlsec1-openssl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend
COPY backend/pyproject.toml ./
COPY backend/app ./app
RUN pip install --no-cache-dir -e .

# Bring in the built SPA (served at "/" by the backend).
COPY --from=web /app/frontend/dist /app/frontend/dist
COPY backend/config ./config

ENV APP_ENV=prod \
    SERVE_FRONTEND=true \
    JWT_AUTOGEN_KEYS=true \
    FRONTEND_DIST=../frontend/dist
# Provide the rest at runtime (PUBLIC_BASE_URL, SESSION_SECRET, AUTH_PROVIDER, ...) via
# --env-file .env.real or -e flags. NEVER bake SESSION_SECRET into the image.

EXPOSE 8723
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8723"]
