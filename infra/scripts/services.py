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


def wait_health(url: str, tries: int = 60, gap: float = 2.0, tick=None) -> bool:
    import time
    for i in range(tries):
        if health_ok(url):
            return True
        if tick:
            tick(i + 1, tries)  # 실패한 폴 직후 진행 알림(어디서 멈추는지 가시화)
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
    tries, gap = 60, 2.0
    print(f"      ▸ {name}: health 대기 {url} (최대 {int(tries * gap)}s) …", flush=True)

    def _tick(i: int, n: int) -> None:
        if i != 1 and i % 5 != 0:      # ~10초마다(1회차 + 5의 배수)만 출력
            return
        last = ""
        try:  # 서비스 자기 로그 꼬리를 함께 보여 heal.sh/기동 진행을 노출
            with open(log, encoding="utf-8", errors="replace") as lf:
                ls = [ln for ln in lf if ln.strip()]
            last = ls[-1].rstrip()[:90] if ls else ""
        except OSError:
            pass
        print(f"        · 대기 {int(i * gap)}s/{int(n * gap)}s"
              + (f"  | log꼬리: {last}" if last else "  | (로그 아직 없음)"), flush=True)

    return "up" if wait_health(url, tries, gap, _tick) else \
        f"FAIL: no health after start (see {log})"


def update_one(svc: dict) -> str:
    """Pull latest code (git ff-only by default; `update:` in the manifest overrides),
    streaming output live to the terminal AND the service log so a slow build / hang is
    visible where it happens. Remote/none-update services are skipped."""
    if svc.get("host", "local") != "local":
        return "skip (remote)"
    cmd = svc.get("update")
    if cmd is None:  # default: a safe fast-forward pull if it's a git repo
        cmd = "git rev-parse --git-dir >/dev/null 2>&1 && git pull --ff-only || echo 'no-git'"
    if cmd is False or cmd == "":  # explicit opt-out (e.g. vllm: stateless)
        return "skip"
    wd = resolve_dir(svc)
    if not wd or not wd.is_dir():
        return "FAIL: dir not found"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logp = LOG_DIR / f"{svc['name']}.log"
    lines: list[str] = []
    with open(logp, "a", encoding="utf-8") as lf:
        lf.write(f"\n=== update START: {cmd}\n")
        lf.flush()
        proc = subprocess.Popen(  # noqa: S602 — manifest-owned cmd
            ["bash", "-c", cmd], cwd=str(wd),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        for line in proc.stdout:  # 라인 도착 즉시 화면+로그로 흘려 진행(빌드/pull)을 가시화
            lines.append(line)
            lf.write(line)
            lf.flush()
            print(f"        · {line.rstrip()}", flush=True)
        rc = proc.wait()
        if rc != 0:
            lf.write(f"=== update FAILED (rc={rc})\n")
    tail = lines[-1].strip() if lines else ""
    return ("updated" if rc == 0 else "FAIL") + (f": {tail[:60]}" if tail else "")


def cmd_update(names: list[str]) -> int:
    svcs = [s for s in load() if not names or s["name"] in names]
    rc = 0
    for s in svcs:
        r = update_one(s)
        if r.startswith("FAIL"):
            rc = 1
        print(f"  {'✗' if r.startswith('FAIL') else '·'} {s['name']:<16} {r}")
    return rc


def cmd_up(names: list[str], do_update: bool = False) -> int:
    svcs = [s for s in load() if not names or s["name"] in names]
    rc = 0
    cur_tier = None
    for s in svcs:
        if s.get("tier") != cur_tier:
            cur_tier = s.get("tier")
            print(f"── tier {cur_tier} ──", flush=True)
        if do_update:
            print(f"  ↻ {s['name']:<16} update …", flush=True)
            print(f"  ↻ {s['name']:<16} {update_one(s)}", flush=True)
        print(f"  ▷ {s['name']:<16} start + health …", flush=True)
        r = start_one(s)
        mark = "✓" if r in ("up", "already-up", "started (no health url)") else "✗"
        if mark == "✗":
            rc = 1
        print(f"  {mark} {s['name']:<16} {r}", flush=True)
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
    if len(sys.argv) < 2 or sys.argv[1] not in ("up", "down", "status", "update"):
        print(__doc__)
        return 2
    action = sys.argv[1]
    args = sys.argv[2:]
    do_update = "--update" in args
    names = [a for a in args if not a.startswith("-")]
    if action == "up":
        return cmd_up(names, do_update=do_update)
    return {"status": cmd_status, "down": cmd_down, "update": cmd_update}[action](names)


if __name__ == "__main__":
    raise SystemExit(main())
