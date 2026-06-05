#!/usr/bin/env bash
# Run on an ONLINE machine to assemble the offline bundle, so an air-gapped server can run
# HWAX with no internet and no sudo.  Output → infra/packages/{deb,sif} + frontend/dist.
#
# HWAX needs far less than a full stack: the SPA is pre-built (dist) and every Python dep is
# baked into portal.sif — so there is NO host node/pnpm/pip to bundle. Just apptainer + images.
#
#   ./infra/scripts/download-packages.sh            # apptainer .deb + .sif + dist
#   ./infra/scripts/download-packages.sh --skip-sif # only the apptainer .deb
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"
[ -f infra/.env ] && { set -a; . infra/.env; set +a; }

PKG="$REPO_ROOT/infra/packages"
DEB_DIR="$PKG/deb"
SIF_DIR="$PKG/sif"
APPTAINER_VER="${HWAX_APPTAINER_VER:-1.3.6}"
ARCH="$(dpkg --print-architecture 2>/dev/null || echo amd64)"
FALLBACK_PROXY="${HWAX_FALLBACK_PROXY:-}"

SKIP_SIF=0
[ "${1:-}" = "--skip-sif" ] && SKIP_SIF=1
mkdir -p "$DEB_DIR" "$SIF_DIR"

echo "▶ apptainer .deb (${APPTAINER_VER}, ${ARCH})"
deb="$DEB_DIR/apptainer_${APPTAINER_VER}_${ARCH}.deb"
url="https://github.com/apptainer/apptainer/releases/download/v${APPTAINER_VER}/apptainer_${APPTAINER_VER}_${ARCH}.deb"
if [ -f "$deb" ] && [ "$(stat -c%s "$deb" 2>/dev/null || echo 0)" -ge 1000000 ]; then
  echo "  ✓ already cached: $deb"
else
  if ! curl -fL --retry 2 --connect-timeout 15 -o "$deb" "$url"; then
    [ -n "$FALLBACK_PROXY" ] && HTTPS_PROXY="$FALLBACK_PROXY" curl -fL --retry 2 -o "$deb" "$url"
  fi
  echo "  ✓ $(basename "$deb")"
fi

if [ "$SKIP_SIF" -eq 0 ]; then
  echo "▶ pre-built images (.sif)"
  if ls infra/apptainer/*.sif >/dev/null 2>&1; then
    cp -f infra/apptainer/portal.sif infra/apptainer/nginx.sif "$SIF_DIR/" 2>/dev/null || true
    echo "  ✓ $(ls "$SIF_DIR"/*.sif 2>/dev/null | wc -l) image(s) → $SIF_DIR"
  else
    echo "  ! no .sif found — run ./infra/scripts/build.sh first, then re-run."
  fi

  echo "▶ SPA (frontend/dist)"
  if [ -f frontend/dist/index.html ]; then
    echo "  ✓ frontend/dist present (it ships in the bundle as-is)"
  else
    echo "  ! frontend/dist missing — run: pnpm --dir frontend build"
  fi
fi

echo
echo "✓ offline bundle staged. Total: $(du -ch "$PKG" frontend/dist 2>/dev/null | tail -1 | cut -f1)"
cat <<EOF

Pack & transport (online machine):
  tar -czf hwax-offline-bundle.tar.gz infra/packages frontend/dist

On the air-gapped 24.04 server (no internet, no sudo):
  tar -xzf hwax-offline-bundle.tar.gz -C <repo>
  cd <repo>
  ./infra/scripts/bootstrap.sh --offline          # extract apptainer locally (no sudo)
  cp infra/packages/sif/*.sif infra/apptainer/     # stage the pre-built images
  cp infra/.env.example infra/.env                 # set ports / PUBLIC_BASE_URL / SESSION_SECRET
  ./infra/scripts/start.sh                         # build + SPA both skip → boots
EOF
