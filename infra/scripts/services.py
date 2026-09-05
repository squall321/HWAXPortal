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

import os
import re
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

# ── 데이터 경로 레지스트리(docs/data-migration/PLAN.md §5) ──────────────────────────
# services.yaml 의 서비스별 `data:` 블록을 기동 env 로 해석한다. HWAX_DATA_ROOT 가 없으면 {} 를
# 돌려 기동 명령줄이 종전과 바이트 하나 안 달라진다(원칙 D1 — 켜지 않으면 무영향).
# infra/.env 는 여기서만, HWAX_* 키만 읽고 **os.environ 에 넣지 않는다**. 유닛 EnvironmentFile 로
# 파일 전체를 실으면 APP_ENV·SESSION_SECRET 이 모든 자식 서비스에 상속되는데, heax Settings 가
# APP_ENV=dev 를 거부하며 죽은 것이 2026-09-04 실사고다(사전점검 NO-GO).
_INFRA_ENV_RE = re.compile(r"^\s*(?:export\s+)?(HWAX_(?:DATA_ROOT|BOX|BOX_ROLE|DATA_[A-Z0-9_]+))=(.*)$")


def _infra_env() -> dict[str, str]:
    p = PORTAL_ROOT / "infra" / ".env"
    out: dict[str, str] = {}
    if not p.exists():
        return out
    for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
        m = _INFRA_ENV_RE.match(ln)
        if not m:
            continue
        try:
            toks = shlex.split(m.group(2), comments=True)  # 인라인 주석·따옴표 처리, $VAR 는 확장 안 함
        except ValueError:
            continue
        if toks and toks[0].strip():  # 빈 값(.env.example 의 `KEY=`)은 미설정과 같다
            out[m.group(1)] = toks[0]
    return out


def _hwax_setting(key: str) -> str | None:
    """우선순위 os.environ > infra/.env, 빈 값 = 미설정. backup-local.sh 의 폴백과 같은 순서여야
    두 도구가 같은 박스 이름·경로를 본다."""
    v = os.environ.get(key)
    if v is None or not v.strip():
        v = _infra_env().get(key)
    return v.strip() if v and v.strip() else None


def box_name() -> str:
    import socket
    return _hwax_setting("HWAX_BOX") or socket.gethostname().split(".")[0]


def class_paths(svc: dict, cname: str, c: dict, root: str | None, box: str) -> tuple[Path | None, Path | None]:
    """클래스의 (현행 경로, 목표 경로). 목표는 HWAX_DATA_ROOT 있을 때만, HWAX_DATA_<SVC>_<CLASS> 오버레이 우선."""
    sdir = None if svc.get("_data_only") else resolve_dir(svc)
    curp: Path | None = None
    cur = c.get("current")
    if cur and "#" not in str(cur):  # ".env#KEY" 같은 키 참조는 경로가 아니다
        curp = Path(os.path.expandvars(str(cur))).expanduser()
        if not curp.is_absolute():
            curp = (sdir / curp) if sdir else None
    tgt: Path | None = None
    if root and c.get("path") and c.get("enabled") is not False:
        key = svc["name"].upper().replace("-", "_")
        override = _hwax_setting(f"HWAX_DATA_{key}_{cname.upper()}")
        tgt = Path(override) if override else Path(f"{root}/{c['path']}".replace("{box}", box))
    return curp, tgt


def resolve_data(svc: dict) -> dict[str, str]:
    """`data:` 블록 → 주입할 env. HWAX_DATA_ROOT 없으면 {}.

    ⚠ **이동이 끝난 클래스만 주입한다**(상태 same·only-target). 아직 현행 경로에 있는 클래스에 새 경로 env 를
    주면 앱이 그 자리에 빈 DB 를 새로 만든다 — 포털은 users/token_store 가 비고 JWT 키를 새로 민팅한다.
    이동은 data-migrate.sh 가 하고, 그 뒤 재기동에서야 이 env 가 붙는다(브리지 심링크가 있어 안 붙어도 동작한다)."""
    root = _hwax_setting("HWAX_DATA_ROOT")
    data = svc.get("data") or {}
    if not root or not data:
        return {}
    box = box_name()
    env: dict[str, str] = {}
    # root_env 는 주입하지 않는다 — 4 리포 모두 DATA_DIR 이 리포 상대로 고정돼 읽는 코드가 없고, 클래스가
    # /data/pg 와 /data/svc 로 갈리므로 한 루트로 가리킬 수도 없다. 브리지 심링크(D2)가 경로를 잇는다.
    for cname, c in (data.get("classes") or {}).items():
        if not isinstance(c, dict) or c.get("enabled") is False or not c.get("env") or not c.get("path"):
            continue
        curp, tgt = class_paths(svc, cname, c, root, box)
        if tgt is None or _data_status(curp, tgt) not in ("same", "only-target"):
            continue
        env[c["env"]] = str(tgt)
    return env


def _data_status(cur: Path | None, tgt: Path | None) -> str:
    """same(같은 inode·브리지 완료) / divergent(둘 다 있고 다름 — 위험) / only-current / only-target / absent"""
    ce = cur is not None and (cur.exists() or cur.is_symlink())
    te = tgt is not None and tgt.exists()
    if not ce and not te:
        return "absent"
    if ce and not te:
        return "only-current"
    if te and not ce:
        return "only-target"
    try:
        if os.path.samefile(str(cur), str(tgt)):
            return "same"
    except OSError:
        pass
    return "divergent"


def cmd_data(names: list[str], check: bool = False) -> int:
    """data [svc] [--check] — 레지스트리 해석 결과(현행 → 목표·상태). --check 는 이동 대상 종류에 divergent·only-target 이 있으면 1.
    HWAX_DATA_ROOT 미설정이면 목표가 없으므로 상태는 only-current/absent 만 나온다."""
    root = _hwax_setting("HWAX_DATA_ROOT")
    box = box_name()
    print(f"  HWAX_DATA_ROOT={root or '(미설정 — 주입 없음, 현행 경로)'}  box={box}  role={_hwax_setting('HWAX_BOX_ROLE') or '-'}")
    raw = yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) or {}
    items: list[dict] = [s for s in load() if s.get("data") and (not names or s["name"] in names)]
    for dname, d in (raw.get("data_only") or {}).items():  # 기동 대상이 아닌 데이터만 등록된 것(슬럼 헤드 등)
        if not names or dname in names:
            items.append({"name": dname, "data": d, "_data_only": True})
    bad = 0
    for s in items:
        data = s["data"]
        sdir = None if s.get("_data_only") else resolve_dir(s)
        print(f"── {s['name']}{'  (data_only)' if s.get('_data_only') else ''}")
        for cname, c in (data.get("classes") or {}).items():
            if not isinstance(c, dict):
                continue
            curp, tgt = class_paths(s, cname, c, root, box)
            if c.get("kind") == "identity" or c.get("enabled") is False or (not c.get("path") and curp is None):
                st = "n/a"
            elif tgt is None:
                st = "only-current" if (curp is not None and (curp.exists() or curp.is_symlink())) else "absent"
            else:
                st = _data_status(curp, tgt)
            if st in ("divergent", "only-target") and c.get("kind") not in ("backup", "log", "cache"):   # 옮기지 않는 종류는 참고만
                bad = 1
            print(f"  {st:<13} {cname:<16} {str(c.get('kind', '-')):<9} {str(curp) if curp else '-'}  →  {str(tgt) if tgt else '-'}")
    return bad if check else 0


def load() -> list[dict]:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) or {}
    svcs = data.get("services", [])
    return sorted(svcs, key=lambda s: s.get("tier", 10))


def enabled_here(svc: dict) -> bool:
    """`only_on: <hostname|[hostnames]>` — 그 박스에서만 다루는 서비스(예: dev 전용 로컬 vLLM).
    다른 박스에선 up/down/update 가 조용히 skip 한다(공유 manifest 하나로 박스별 차이 표현)."""
    only = svc.get("only_on")
    if not only:
        return True
    hosts = [only] if isinstance(only, str) else list(only)
    import socket
    return socket.gethostname() in hosts


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


def health_ok(url: str, timeout: float = 2.0, expect: object = None) -> bool:
    """Any HTTP response (even 4xx) means the port is serving → up.

    expect 가 주어지면 상태코드까지 본다. 프록시 뒤에 있는 서비스는 '응답이 왔다'만으로는
    판정이 안 되기 때문이다 — heax-hub 는 Caddy(:4180)가 앞에 있어서 백엔드(:4040)가 죽어도
    정적 SPA 를 200 으로 돌려주고, 죽은 upstream 이면 502 가 오는데 그것도 '응답'이라 up 이
    됐다. 그래서 '앱이 죽었는데 초록' 이 구조적으로 가능했다.
    expect 가 없으면 종전 그대로다 — 406 을 up 으로 봐야 하는 항목들이 있어 전역 강제는 못 한다.
    """
    allowed = None
    if expect is not None:
        allowed = {int(c) for c in (expect if isinstance(expect, (list, tuple, set)) else [expect])}
    try:
        r = urllib.request.urlopen(url, timeout=timeout)  # noqa: S310 (trusted local/own URLs)
        return allowed is None or r.getcode() in allowed
    except urllib.error.HTTPError as e:
        return allowed is None or e.code in allowed  # 404/406 etc — it answered, so it's up
    except Exception:
        return False


def wait_health(url: str, tries: int = 60, gap: float = 2.0, tick=None, expect=None) -> bool:
    import time
    for i in range(tries):
        if health_ok(url, expect=expect):
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
    if url and health_ok(url, expect=svc.get("expect")):
        return "already-up"

    host = svc.get("host", "local")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log = LOG_DIR / f"{name}.log"
    # 레지스트리 env(HWAX_DATA_ROOT 있을 때만) 위에 명시 env: 가 덮는다. 미설정이면 종전과 동일.
    inner = f"{env_prefix({**resolve_data(svc), **(svc.get('env') or {})})}{svc['start']}"

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
    gap = 2.0
    tries = max(1, int(int(os.environ.get("HWAX_HEALTH_WAIT") or 120) / gap))   # 초. 이관기는 300 — HEAX 전체 재기동이 120s 를 넘긴다
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

    return "up" if wait_health(url, tries, gap, _tick, expect=svc.get("expect")) else \
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
        if not enabled_here(s):
            print(f"  · {s['name']:<16} skip (only_on={s.get('only_on')})")
            continue
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
        if not enabled_here(s):
            print(f"  · {s['name']:<16} skip (only_on={s.get('only_on')} — 이 박스 대상 아님)", flush=True)
            continue
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
        if not enabled_here(s):
            print(f"  {'· skip':<12} {s['name']:<16} only_on={s.get('only_on')}")
            continue
        url = s.get("health", "")
        up = health_ok(url, expect=s.get("expect")) if url else None
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
        if not enabled_here(s):
            print(f"  · {name}: skip (only_on={s.get('only_on')})")
            continue
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
    if len(sys.argv) < 2 or sys.argv[1] not in ("up", "down", "status", "update", "data"):
        print(__doc__)
        return 2
    action = sys.argv[1]
    args = sys.argv[2:]
    do_update = "--update" in args
    names = [a for a in args if not a.startswith("-")]
    if action == "up":
        return cmd_up(names, do_update=do_update)
    if action == "data":  # 데이터 경로 레지스트리 조회·검증(docs/data-migration)
        return cmd_data(names, check="--check" in args)
    return {"status": cmd_status, "down": cmd_down, "update": cmd_update}[action](names)


if __name__ == "__main__":
    raise SystemExit(main())
