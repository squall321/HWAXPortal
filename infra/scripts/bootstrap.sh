#!/usr/bin/env bash
# Ensure apptainer is available — WITHOUT sudo — by extracting the .deb to a local path.
#   ./infra/scripts/bootstrap.sh            auto: use cached .deb if present, else download
#   ./infra/scripts/bootstrap.sh --offline  cached .deb only (air-gapped); fail if absent
#   ./infra/scripts/bootstrap.sh --online   force download of the .deb
#
# Result: infra/apptainer/bin-<ver>/usr/bin/apptainer  (picked up automatically by _common.sh).
# Caveat: the extracted (non-setuid) apptainer runs via unprivileged user namespaces
# (Ubuntu 24.04 default = enabled). If the host disables them, install the same cached .deb with
# sudo instead:  sudo dpkg -i infra/packages/deb/apptainer_*.deb
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APPT_DIR="$REPO_ROOT/infra/apptainer"
DEB_DIR="$REPO_ROOT/infra/packages/deb"
# optional overrides from infra/.env (proxy fallback, pinned version)
[ -f "$REPO_ROOT/infra/.env" ] && { set -a; . "$REPO_ROOT/infra/.env"; set +a; }

APPTAINER_VER="${HWAX_APPTAINER_VER:-1.3.6}"
ARCH="$(dpkg --print-architecture 2>/dev/null || echo amd64)"
FALLBACK_PROXY="${HWAX_FALLBACK_PROXY:-}"

MODE=auto
for a in "$@"; do
  case "$a" in
    --online) MODE=online ;;
    --offline) MODE=offline ;;
    -h|--help) sed -n '2,12p' "$0" | sed 's/^# \?//'; exit 0 ;;
    *) echo "unknown arg: $a (try --help)"; exit 1 ;;
  esac
done

# Turn off the systemd cgroup manager in a (user-owned) extracted conf — see note at extraction.
disable_cgroups() {
  local conf="$1/etc/apptainer/apptainer.conf"
  if [ -f "$conf" ] && grep -qiE '^systemd cgroups = yes' "$conf"; then
    sed -i 's/^systemd cgroups = yes/systemd cgroups = no/' "$conf"
    echo "  · set 'systemd cgroups = no' in $(basename "$1") (no D-Bus needed for instance start)"
  fi
}

# 0. Already have OUR pinned, extracted apptainer? Ensure cgroups off, then use it.
existing=""
for c in "$APPT_DIR"/bin-*/usr/bin/apptainer; do [ -x "$c" ] && existing="$c"; done
if [ -n "$existing" ] && "$existing" --version >/dev/null 2>&1; then
  disable_cgroups "$(dirname "$(dirname "$(dirname "$existing")")")"
  echo "✓ apptainer (pinned, no-sudo): $existing ($("$existing" --version 2>&1 | head -1))"
  exit 0
fi
# We PIN our own apptainer for reproducibility — a newer system apptainer (e.g. 1.5.0) enforces
# rootless cgroups/D-Bus and its root-owned conf can't be relaxed without sudo, which breaks
# `instance start` on hosts without a user D-Bus session. Only defer to the system one if asked.
if [ "${HWAX_USE_SYSTEM_APPTAINER:-0}" = "1" ] || printf '%s\n' "$@" | grep -qx -- '--use-system'; then
  sys="$(command -v apptainer 2>/dev/null || true)"
  if [ -n "$sys" ] && "$sys" --version >/dev/null 2>&1; then
    echo "✓ using system apptainer (--use-system): $sys ($("$sys" --version 2>&1 | head -1))"
    exit 0
  fi
fi

# 1. Locate a cached .deb (offline) or download one (online).
find_cached_deb() {
  local d f
  for d in "$DEB_DIR" "$APPT_DIR" "$REPO_ROOT/infra/packages" "$REPO_ROOT"; do
    for f in "$d"/apptainer_*.deb "$d"/apptainer_*_"${ARCH}".deb; do
      [ -e "$f" ] || continue
      [ "$(stat -c%s "$f" 2>/dev/null || echo 0)" -ge 1000000 ] && { printf '%s' "$f"; return 0; }
    done
  done
  return 1
}

deb="$(find_cached_deb || true)"
if [ -n "$deb" ]; then
  echo "→ using cached .deb: $deb"
elif [ "$MODE" = offline ]; then
  echo "✗ --offline but no apptainer_*.deb cached in $DEB_DIR/"
  echo "  Build the bundle on an online machine: ./infra/scripts/download-packages.sh"
  exit 1
else
  deb="$DEB_DIR/apptainer_${APPTAINER_VER}_${ARCH}.deb"
  url="https://github.com/apptainer/apptainer/releases/download/v${APPTAINER_VER}/apptainer_${APPTAINER_VER}_${ARCH}.deb"
  mkdir -p "$DEB_DIR"
  echo "→ downloading apptainer ${APPTAINER_VER} (${ARCH})…"
  if ! curl -fL --retry 2 --connect-timeout 15 -o "$deb" "$url"; then
    if [ -n "$FALLBACK_PROXY" ]; then
      echo "  ↻ retry via fallback proxy $FALLBACK_PROXY"
      HTTPS_PROXY="$FALLBACK_PROXY" HTTP_PROXY="$FALLBACK_PROXY" \
        curl -fL --retry 2 -o "$deb" "$url" \
        || { echo "✗ download failed (direct + proxy)"; exit 1; }
    else
      echo "✗ download failed. Pre-stage the .deb in $DEB_DIR/ and re-run --offline."; exit 1
    fi
  fi
fi

# 2. Extract — NO SUDO.
ver="$(basename "$deb" | sed -E 's/^apptainer_([^_]+)_.*/\1/')"
target="$APPT_DIR/bin-${ver}"
bin="$target/usr/bin/apptainer"
if [ ! -x "$bin" ]; then
  echo "→ extracting → $target (no sudo)"
  rm -rf "$target"; mkdir -p "$target"
  dpkg-deb -x "$deb" "$target"
  # The .deb installs to /usr + /etc + /var separately, but the relocated binary derives its
  # prefix as <target>/usr and looks for sysconfdir/localstatedir UNDER that prefix. Link them
  # so apptainer finds usr/etc/apptainer/apptainer.conf and usr/var/apptainer.
  [ -d "$target/etc" ] && [ ! -e "$target/usr/etc" ] && ln -s ../etc "$target/usr/etc"
  [ -d "$target/var" ] && [ ! -e "$target/usr/var" ] && ln -s ../var "$target/usr/var"
fi
[ -x "$bin" ] || { echo "✗ extraction failed: $bin not found"; exit 1; }
disable_cgroups "$target"   # no D-Bus needed for rootless instance start

# 3. Verify it runs.
if ! "$bin" --version >/dev/null 2>&1; then
  echo "✗ extracted apptainer won't run: $bin"; exit 1
fi
echo "✓ apptainer ready (no sudo): $bin ($("$bin" --version 2>&1 | head -1))"

# 4. user-namespace probe (a real container run needs it when non-setuid).
probe_sif=""
for s in "$APPT_DIR/nginx.sif" "$APPT_DIR/portal.sif"; do [ -f "$s" ] && probe_sif="$s" && break; done
if [ -n "$probe_sif" ]; then
  if "$bin" exec "$probe_sif" true >/dev/null 2>&1; then
    echo "✓ user namespaces OK (rootless container run works)"
  else
    echo "  ⚠ container run failed — this host may have unprivileged user namespaces disabled."
    echo "    Fallback (one command, needs sudo once):  sudo dpkg -i $deb"
  fi
else
  echo "  ℹ no .sif yet to probe userns. If 'start.sh' later fails to run a container, either"
  echo "    enable unprivileged userns, or:  sudo dpkg -i $deb"
fi
