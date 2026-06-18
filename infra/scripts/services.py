#!/usr/bin/env python3
"""HWAX stack orchestrator — bring the federated services + chat stack up/down/status.

Reads infra/services.yaml. Local services start in a detached session (survives this
process); remote services start over SSH (KEY auth — no passwords anywhere). Each service
is polled at its health URL. Idempotent: a service that's already answering is skipped.

  services.py up [name ...]      start all (or named) services, tier by tier, wait healthy
  services.py status [name ...]  show which are up (health probe only)
  services.py down [name ...]    stop (uses `stop:` if given, else best-effort by port)

NO SECRETS: remote = ssh <ssh_user>@<host> with key auth. sudo on a remote = that host's
NOPASSWD sudoers, never a password here.
"""

import shlex
import subprocess
import sys
import urllib.request
from pathlib import Path

import yaml

PORTAL_ROOT = Path(__file__).resolve().parent.parent.parent  # infra/scripts → repo root
PARENT = PORTAL_ROOT.parent
MANIFEST = PORTAL_ROOT / "infra" / "services.yaml"
LOG_DIR = Path("/tmp/hwax-services")


def load() -> list[dict]:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) or {}
    svcs = data.get("services", [])
    return sorted(svcs, key=lambda s: s.get("tier", 10))


def resolve_dir(svc: dict) -> Path | None:
    """Explicit dir wins; else auto-discover the repo by name in the usual roots."""
    if svc.get("dir"):
        d = Path(svc["dir"]).expanduser()
        return (PORTAL_ROOT / d).resolve() if not d.is_absolute() else d
    name = svc.get("discover")
    if not name:
        return None
    for root in (PARENT, Path.home() / "Projects", Path.home() / "claude"):
        cand = root / name
        if cand.is_dir():
            return cand
    return None


def health_ok(url: str, timeout: float = 2.0) -> bool:
    """Any HTTP response (even 4xx) means the port is serving → up."""
    try:
        urllib.request.urlopen(url, timeout=timeout)  # noqa: S310 (trusted local/own URLs)
        return True
    except urllib.error.HTTPError:
        return True  # 404/406 etc — it answered, so it's up
    except Exception:
        return False


def wait_health(url: str, tries: int = 60, gap: float = 2.0) -> bool:
    import time
    for _ in range(tries):
        if health_ok(url):
            return True
        time.sleep(gap)
    return False


def env_prefix(env: dict | None) -> str:
    if not env:
        return ""
    return " ".join(f"{k}={shlex.quote(str(v))}" for k, v in env.items()) + " "


def start_one(svc: dict) -> str:
    name = svc["name"]
    url = svc.get("health", "")
    if url and health_ok(url):
        return "already-up"

    host = svc.get("host", "local")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log = LOG_DIR / f"{name}.log"
    inner = f"{env_prefix(svc.get('env'))}{svc['start']}"

    if host == "local":
        wd = resolve_dir(svc)
        if not wd or not wd.is_dir():
            return f"FAIL: dir not found (discover={svc.get('discover')}, dir={svc.get('dir')})"
        # Detached session: survives this orchestrator; foreground servers keep running.
        with open(log, "wb") as lf, open("/dev/null", "rb") as devnull:
            subprocess.Popen(  # noqa: S602 — commands come from our own manifest
                ["bash", "-c", inner], cwd=str(wd),
                stdout=lf, stderr=subprocess.STDOUT, stdin=devnull,
                start_new_session=True,
            )
    else:
        user = svc.get("ssh_user")
        if not user:
            return "FAIL: remote service needs ssh_user (key auth)"
        wd = svc.get("dir") or f"~/claude/{svc.get('discover', '')}"
        remote = f"cd {shlex.quote(wd)} && setsid bash -c {shlex.quote(inner)} " \
                 f"> /tmp/{name}.log 2>&1 < /dev/null &"
        subprocess.Popen(  # noqa: S603 — ssh with key auth, no password
            ["ssh", "-o", "BatchMode=yes", f"{user}@{host}", remote],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    if not url:
        return "started (no health url)"
    return "up" if wait_health(url) else f"FAIL: no health after start (see {log})"


def cmd_up(names: list[str]) -> int:
    svcs = [s for s in load() if not names or s["name"] in names]
    rc = 0
    cur_tier = None
    for s in svcs:
        if s.get("tier") != cur_tier:
            cur_tier = s.get("tier")
            print(f"── tier {cur_tier} ──")
        r = start_one(s)
        mark = "✓" if r in ("up", "already-up", "started (no health url)") else "✗"
        if mark == "✗":
            rc = 1
        print(f"  {mark} {s['name']:<16} {r}")
    return rc


def cmd_status(names: list[str]) -> int:
    svcs = [s for s in load() if not names or s["name"] in names]
    any_down = 0
    for s in svcs:
        url = s.get("health", "")
        up = health_ok(url) if url else None
        mark = "✓ up" if up else ("? no-health" if up is None else "✗ down")
        if up is False:
            any_down = 1
        host = s.get("host", "local")
        print(f"  {mark:<12} {s['name']:<16} {host:<14} {url}")
    return any_down


def cmd_down(names: list[str]) -> int:
    # Reverse tier order. Use an explicit `stop:` if the manifest gives one; otherwise
    # best-effort kill by the health port (local only). Remote down is left to `stop:`.
    svcs = [s for s in load() if not names or s["name"] in names]
    for s in reversed(svcs):
        name = s["name"]
        if s.get("stop"):
            wd = resolve_dir(s)
            subprocess.run(["bash", "-c", s["stop"]], cwd=str(wd) if wd else None, check=False)
            print(f"  • {name}: ran stop")
            continue
        url = s.get("health", "")
        port = url.rsplit(":", 1)[-1].split("/")[0] if ":" in url else ""
        if s.get("host", "local") == "local" and port.isdigit():
            subprocess.run(  # noqa: S607
                ["bash", "-c", f"fuser -k {port}/tcp 2>/dev/null || true"], check=False
            )
            print(f"  • {name}: killed :{port}")
        else:
            print(f"  • {name}: no stop defined (remote/unknown) — skip")
    return 0


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in ("up", "down", "status"):
        print(__doc__)
        return 2
    action, names = sys.argv[1], sys.argv[2:]
    return {"up": cmd_up, "status": cmd_status, "down": cmd_down}[action](names)


if __name__ == "__main__":
    raise SystemExit(main())
