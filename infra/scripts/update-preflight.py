#!/usr/bin/env python3
# update-all 전에 박스(cae00)에서 돌리는 읽기 전용 사전 점검 — 끊길 일 · 사라질 데이터 · 빠진 설정 · Drive 의 판을 본다(docs/cae00-deploy-guide '2026-10-25 반영분')
"""update-all 을 돌리기 **전에** 이 박스에서 무엇이 끊기고 무엇이 사라질 수 있는지, 새 기능이 서려면 무엇이 빠졌는지를 한 번에 본다.

이 파일이 아직 박스에 없을 때(받기 전) — 작업 트리를 건드리지 않고 원격 판을 그대로 돌린다(포털 리포 루트에서).

    cd ~/Projects/HWAXPortal && git fetch -q origin main && git show origin/main:infra/scripts/update-preflight.py | python3 -

받은 뒤에는 `python3 infra/scripts/update-preflight.py`. `--no-fetch` 를 주면 원격을 묻지 않는다(마지막으로 받은 원격 ref 로 본다).
종료코드 0 = ✗ 없음(⚠ 는 읽고 판단한다), 1 = ✗ 있음(update-all 전에 그 줄의 할 일을 한다).

읽기만 한다 — 서비스를 내리거나 파일을 고치지 않는다. 바꾸는 것은 `git fetch` 의 원격 ref 뿐이다(update-all 도 맨 처음 같은 일을 한다).
비밀은 찍지 않는다 — 두 곳의 비밀이 같은지는 해시 앞자리로만 견준다. DB 는 읽기로만 연다(sqlite mode=ro · psql 의 SELECT).
리포 자리는 이 리포 옆 → ~/Projects → ~/claude 순서다(update-all find_repo 와 같다). 표준 라이브러리만 쓴다.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path


def _root() -> Path:
    """이 파일의 리포 — `python3 -`(원격 판을 표준입력으로)이면 지금 자리가 포털 리포 루트여야 한다."""
    f = globals().get("__file__")
    if f and Path(f).is_file():
        return Path(f).resolve().parents[2]
    c = Path.cwd()
    if (c / "infra/scripts/update-all.sh").is_file():
        return c
    sys.exit("포털 리포 루트에서 돌린다 — cd ~/Projects/HWAXPortal 뒤 다시")


ROOT = _root()
HOME = Path.home()
FETCH = "--no-fetch" not in sys.argv[1:]
RESULTS: list[tuple[str, str]] = []
TRUE = ("1", "true", "yes", "on")
_LOOP = urllib.request.build_opener(urllib.request.ProxyHandler({}))   # 루프백은 프록시를 타지 않는다
_WIKI: dict = {}                                                      # MX 백서 위키 /health 답(한 번만 묻는다)
AGENT = os.environ.get("HWAX_PREFLIGHT_AGENT", "http://127.0.0.1:9009")   # 시험이 실서비스에 닿지 않게 바꾸는 자리 — 박스에선 손대지 않는다
MXWP_API = os.environ.get("HWAX_PREFLIGHT_MXWP", "http://127.0.0.1:8800")

# update-all §1(포털) · deploy-all(나머지)이 `git stash push -u` 뒤 `reset --hard origin/<branch>` 하는 리포 → 그 리포의 설정 파일들.
# 설정이 가리키는 파일이 git 이 모르는 채 있으면 stash 가 작업 트리에서 치운다(그 서비스가 그 파일을 잃는다).
RESET = {"HWAXPortal": ("backend/.env", "infra/.env"), "MXWhitePaper": (".env",), "HEAXHub": (".env",),
         "SignalForge": (".env",), "AIDataHub": ("deploy/apptainer/.env", "api_server/.env"), "KooRemapper": ("platform/.env",)}
# update-sites(§4)가 `git pull --ff-only` 하는 리포 — 지우지는 않지만, 겹치는 수정 · 로컬 커밋이 있으면 갱신이 막혀 옛 코드로 남는다.
PULL = ("HWAXAgentServer", "HWAXMcpGateway")
MIGRATIONS = {"MXWhitePaper": "apps/api/alembic/versions", "HEAXHub": "backend/alembic/versions",
              "KooRemapper": "platform/backend/alembic/versions", "SignalForge": "backend/alembic/versions",
              "AIDataHub": "api_server/alembic/versions"}


def say(kind: str, msg: str) -> None:
    RESULTS.append((kind, msg))
    print(f"  {kind} {msg}")


def head(title: str) -> None:
    print(f"\n── {title}")


def find_repo(name: str) -> Path | None:
    for base in (ROOT.parent, HOME / "Projects", HOME / "claude"):
        if (base / name).is_dir():
            return base / name
    return None


def envv(path: Path | None, key: str) -> str:
    """.env 값 하나 — update-all `_envfile_value` 와 같은 규칙(export 허용 · 공백 뒤 # 제거 · 따옴표 제거 · 마지막 줄)."""
    vals = env_all(path)
    return vals.get(key, "")


def env_all(path: Path | None) -> dict[str, str]:
    out: dict[str, str] = {}
    if path is None or not path.is_file():
        return out
    for ln in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$", ln)
        if m:
            out[m.group(1)] = re.sub(r"\s+#.*$", "", m.group(2)).strip().replace('"', "").replace("'", "").replace("\r", "")
    return out


def h8(v: str) -> str:
    return hashlib.sha256(v.encode()).hexdigest()[:8] if v else ""


def run(cmd: list[str], *, cwd: Path | None = None, env: dict | None = None, timeout: int = 60) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env={**os.environ, **(env or {})})
        return r.returncode, r.stdout
    except (OSError, subprocess.TimeoutExpired) as e:
        return 127, str(e)


def get_json(url: str, *, timeout: float = 5.0, headers: dict | None = None, loopback: bool = True):
    """(상태, JSON) — 못 닿으면 (None, None). 루프백은 프록시 없이, 그 밖(LLM 서버)은 이 셸의 프록시 설정 그대로(에이전트와 같게)."""
    try:
        req = urllib.request.Request(url, headers=headers or {})
        opener = _LOOP if loopback else urllib.request.build_opener()
        with opener.open(req, timeout=timeout) as r:      # noqa: S310 — 박스 설정에 적힌 주소만
            return r.status, json.loads(r.read(4_000_000).decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:  # noqa: BLE001 — 못 닿음은 '모름' 이다
        return None, None


def ro_sqlite(path: Path, sql: str):
    """읽기로만 연다 — 떠 있는 앱의 DB 를 잠그지 않는다. 못 열면 None."""
    try:
        c = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2)
        try:
            return c.execute(sql).fetchall()
        finally:
            c.close()
    except sqlite3.Error:
        return None


def appt() -> str:
    """apptainer — 포털 리포에 푼 판(D-Bus 없이 도는 것)이 있으면 그것, 없으면 시스템 판(deploy-all 의 MX 백서 · KooRemapper 구역과 같은 순서)."""
    for c in sorted((ROOT / "infra/apptainer").glob("bin-*/usr/bin/apptainer")):
        if os.access(c, os.X_OK):
            return str(c)
    return shutil.which("apptainer") or "apptainer"


def wiki_health() -> dict:
    if "v" not in _WIKI:
        st, w = get_json(MXWP_API + "/api/v1/wiki/health")
        _WIKI["v"] = (w.get("data") or {}) if st == 200 and isinstance(w, dict) else {}
    return _WIKI["v"]


def upstream_file(repo: Path, rel: str) -> str | None:
    """받을 판(@{u})의 파일 내용 — 없으면 None."""
    code, out = run(["git", "show", f"@{{u}}:{rel}"], cwd=repo)
    return out if code == 0 else None


# ── 1. 지금 도는 일 — update-all 이 내리면 끊긴다 ─────────────────────────────────────────────────
def check_running() -> None:
    head("1. 지금 도는 일(update-all 이 다시 띄우면 끊긴다)")
    st, h = get_json(AGENT + "/health")
    if not isinstance(h, dict):
        say("?", "에이전트 서버 /health 가 답하지 않는다 — 도는 심의를 셀 수 없다")
    else:
        active, queued = int(h.get("delib_active") or 0), int(h.get("delib_queued") or 0)
        if active or queued:
            # 10-22 전 엔진은 '새 심의 멈춤' 을 모른다 — update-all 이 에이전트 재기동을 **미룬다**(○). 그러면 이번 실행은 에이전트를 안 바꾼다.
            durable = "" if h.get("delib_queue_durable") else " · 이 엔진은 줄 선 심의가 재기동을 넘기지 못한다(옛 판이면 재기동을 미룬다 — 한 번 더 돌린다)"
            say("⚠", f"도는 심의 {active} · 줄 선 심의 {queued} — update-all 이 새 심의를 멈추고 끝나기를 기다린다(HWAX_DELIB_WAIT_S){durable}")
        else:
            say("✓", "도는 · 줄 선 심의 없음")
        if int(h.get("review_active") or 0):
            say("·", f"리스크 카드 대조 {h['review_active']}건이 돈다 — update-all 이 새 대조를 멈추고 최대 300초 기다린다(HWAX_DRAIN_WAIT_S). "
                     "그 뒤 끊긴 호출은 리스크 앱이 차감 없이 다시 돌린다")
    koor = find_repo("KooRemapper")
    if koor and (koor / "platform/infra/scripts/_common.sh").is_file():
        n = _koorm_running(koor)
        if n is None:
            say("?", "DynaForge 도는 로컬 작업을 셀 수 없다(인스턴스 · DB 를 못 물었다)")
        elif n:
            say("⚠", f"DynaForge 로컬 작업 {n}건이 돈다 — update-all 이 DynaForge 재기동만 미룬다(○ — §1 이 포털을 받은 뒤 새 판으로 다시 돌아 첫 실행부터 걸린다). "
                     "끝난 뒤 한 번 더 돌린다(지금 내리려면 KOORM_RESTART_FORCE=1 — 끊긴 작업은 실패로 적힌다)")
        else:
            say("✓", "DynaForge 도는 로컬 작업 없음")
    hub = find_repo("HEAXHub")
    if hub:
        # 허브가 다시 뜨면(코드 · SIF 가 바뀌면) 도는 허브 앱 작업은 끊긴다 — 막는 장치가 없다. 끝난 뒤 돌린다.
        for app, db in (("StepForge", "step_forge/stepforge.db"), ("DocForge", "doc_forge/docforge.db")):
            p = hub / "var/app_data" / db
            if not p.exists():
                continue
            rows = ro_sqlite(p, "SELECT count(*) FROM jobs WHERE status = 'running'")
            if rows is None:
                say("?", f"{app} 작업 DB 를 못 읽었다({p})")
            elif rows[0][0]:
                say("⚠", f"{app} 작업 {rows[0][0]}건이 돈다 — 허브가 다시 뜨면 끊긴다(끝난 뒤 update-all)")
            else:
                say("✓", f"{app} 도는 작업 없음")
    w = wiki_health()
    if w:
        running = int((w.get("jobs") or {}).get("running") or 0)
        say("·" if running else "✓", f"MX 백서 위키 작업 {running}건이 돈다 — 끊기면 lease 가 지난 뒤 다시 집는다(시도 1회 소모)"
            if running else "MX 백서 위키 도는 작업 없음")


def _koorm_running(repo: Path) -> int | None:
    """portal lib/koorm-busy.sh 와 같은 길 — 그 리포의 _common.sh 가 세운 APPTAINER · INST_POSTGRES · POSTGRES_* 로 psql."""
    code, out = run(["bash", "-c", ". platform/infra/scripts/_common.sh >/dev/null 2>&1 || exit 9; "
                     '"$APPTAINER" exec instance://"$INST_POSTGRES" psql -U "$POSTGRES_USER" -p "$POSTGRES_PORT" "$POSTGRES_DB" -tAc '
                     "\"SELECT count(*) FROM jobs WHERE status = 'running' AND external_kind IS NULL\""], cwd=repo, timeout=30)
    s = out.strip()
    return int(s) if code == 0 and s.isdigit() else None


# ── 2. 데이터 안전 ──────────────────────────────────────────────────────────────────────────────
def check_data() -> None:
    head("2. 데이터 안전(update-all 이 지우거나 치우는 것)")
    # AIDataHub 병합은 Drive 덤프(11GB 남짓, gz)를 mktemp -d(/tmp)에 받는다(그 리포 merge-from-drive.sh). 배포 전 백업은 /data/backups.
    for path, need, why in (("/tmp", 12, "AIDataHub 병합이 Drive 덤프를 /tmp 에 받는다"),
                            ("/data", 20, "배포 전 백업(/data/backups) · 병합"), (str(HOME), 10, "SIF · 배포물 받기")):
        if os.path.isdir(path):
            free = shutil.disk_usage(path).free / 2**30
            say("⚠" if free < need else "✓", f"{path} 남은 {free:,.0f}GiB" + (f" — {need}GiB 아래다({why})" if free < need else ""))
    for name, envs in RESET.items():
        repo = find_repo(name)
        if repo is not None and (repo / ".git").exists():
            _reset_repo(name, repo, envs)
    for name in PULL:
        repo = find_repo(name)
        if repo is not None and (repo / ".git").exists():
            _pull_repo(name, repo)
    for name, mdir in MIGRATIONS.items():
        repo = find_repo(name)
        if repo is None or not (repo / ".git").exists():
            continue
        code, out = run(["git", "diff", "--name-only", "--diff-filter=A", "HEAD", "@{u}", "--", mdir], cwd=repo)
        new = sorted(Path(p).name for p in out.split() if p.endswith(".py")) if code == 0 else []
        if new:
            say("·", f"{name}: 들어올 DB 이관 {len(new)} — {', '.join(new[:8])}{' …' if len(new) > 8 else ''}")
    _mxwp_orphans()
    _risk_version()


def _status(repo: Path) -> tuple[list[str], list[str], int]:
    """(고친 추적 파일, git 이 모르는 파일, origin 에 없는 로컬 커밋 수). 원격 ref 는 여기서 받는다(--no-fetch 면 묻지 않는다)."""
    if FETCH:
        run(["git", "fetch", "--quiet"], cwd=repo, timeout=120)
    code, out = run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=repo)
    lines = [ln for ln in out.splitlines() if ln.strip()] if code == 0 else []
    mod = [ln[3:] for ln in lines if not ln.startswith("??")]
    unt = [ln[3:] for ln in lines if ln.startswith("??")]
    code, n = run(["git", "rev-list", "--count", "@{u}..HEAD"], cwd=repo)
    return mod, unt, int(n.strip()) if code == 0 and n.strip().isdigit() else 0


def _env_refs(repo: Path, envs: tuple[str, ...]) -> set[Path]:
    """설정 파일들의 값 가운데 이 리포 안의 경로 — 그 자리(파일이나 폴더). 리포 루트 자체는 뺀다."""
    refs: set[Path] = set()
    root = repo.resolve()
    for rel in envs:
        ef = repo / rel
        for v in env_all(ef).values():
            if "://" in v:
                continue
            for part in re.split(r"[,;\s]+", v):
                if not part or not ("/" in part or re.search(r"\.(ya?ml|json|env|sqlite|db|key|pem|crt|toml)$", part)):
                    continue
                part = os.path.expanduser(part)
                cands = [Path(part)] if part.startswith("/") else [ef.parent / part, repo / part]
                for c in cands:
                    c = c.resolve()
                    if c != root and root in c.parents:
                        refs.add(c)
    return refs


def _reset_repo(name: str, repo: Path, envs: tuple[str, ...]) -> None:
    mod, unt, ahead = _status(repo)
    if ahead:
        say("✗", f"{name}: origin 에 없는 로컬 커밋 {ahead}개 — update-all 의 reset --hard 가 버린다(reflog 에만 남는다). "
                 f"먼저 push 하거나 cd {repo} && git branch keep-before-update 로 남긴다")
    refs = _env_refs(repo, envs)
    hit = [p for p in unt if any(r == (repo / p).resolve() or r in (repo / p).resolve().parents for r in refs)]
    if hit:
        excl = repo / ".git/info/exclude"
        say("✗", f"{name}: 설정(.env)이 가리키는 파일 {len(hit)}개를 git 이 모른다 — update-all 이 맨 처음 stash 로 치워 그 서비스가 잃는다"
                 f"({', '.join(hit[:5])}). update-all 전에: " + " ; ".join(f"echo '{p}' >> {excl}" for p in hit[:5]))
    rest = [p for p in mod + unt if p not in hit]
    if not (mod or unt):
        say("✓", f"{name}: 작업 트리 깨끗함")
    elif rest:
        secret = [p for p in rest if re.search(r"(^|/)\.env|\.env([._-]|$)|secret|\.key$|\.pem$", p)]
        say("⚠", f"{name}: 고친 파일 {len([p for p in mod if p not in hit])} · git 이 모르는 파일 {len([p for p in unt if p not in hit])} — update-all 이 "
                 f"stash 로 옮기고 origin 판으로 되돌린다(되찾기: cd {repo} && git stash list)"
                 + (f" · 비밀로 보이는 것 {len(secret)}({', '.join(secret[:4])}) — stash 에 들어가면 git 객체로 남는다, 리포 밖으로 옮긴다" if secret else "")
                 + f" — {_group(rest)}")


def _group(paths: list[str]) -> str:
    """맨 윗 폴더별 개수(많은 순) — 수백 개를 이름으로 늘어놓으면 무엇이 치워지는지 읽히지 않는다."""
    c: dict[str, int] = {}
    for p in paths:
        k = p.split("/", 1)[0] + ("/" if "/" in p else "")
        c[k] = c.get(k, 0) + 1
    top = sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))
    return " · ".join(f"{k} {n}" if k.endswith("/") else k for k, n in top[:10]) + (f" · 그 밖 {len(top) - 10}곳" if len(top) > 10 else "")


def _pull_repo(name: str, repo: Path) -> None:
    mod, unt, ahead = _status(repo)
    code, out = run(["git", "diff", "--name-only", "HEAD", "@{u}"], cwd=repo)
    incoming = set(out.split()) if code == 0 else set()
    clash = [p for p in mod + unt if p in incoming]
    if ahead:
        say("✗", f"{name}: origin 에 없는 로컬 커밋 {ahead}개 — git pull --ff-only 가 막혀 이 서비스가 옛 코드로 남는다(push 하거나 되돌린다)")
    if clash:
        say("✗", f"{name}: 들어올 변경과 겹치는 로컬 파일 {len(clash)}개 — git pull --ff-only 가 막혀 옛 코드로 남는다({', '.join(clash[:5])})")
    elif mod or unt:
        say("·", f"{name}: 고친 · git 이 모르는 파일 {len(mod) + len(unt)}개 — 들어올 변경과 겹치지 않아 그대로 남는다")
    elif not ahead:
        say("✓", f"{name}: 작업 트리 깨끗함")


def _mxwp_orphans() -> None:
    """MX 백서 이관 0056 은 주어 slug 의 문서가 없는 doc_triples 를 **되돌릴 수 없게** 지운다. 아직 안 탄 박스면 몇 줄인지 센다."""
    mx = find_repo("MXWhitePaper")
    if mx is None or not (mx / ".env").is_file():
        return
    e = env_all(mx / ".env")
    user, db, port = e.get("POSTGRES_USER") or "mxwp", e.get("POSTGRES_DB") or "mxwp", e.get("POSTGRES_PORT") or "5432"
    base = [appt(), "exec", "instance://mxwp_postgres", "psql", "-h", "127.0.0.1", "-p", port, "-U", user, "-d", db, "-tAc"]
    pw = {"PGPASSWORD": e.get("POSTGRES_PASSWORD", "")}                 # 비밀은 환경으로(명령줄에 나오지 않게)
    code, ver = run(base + ["SELECT version_num FROM alembic_version"], env=pw, timeout=30)
    m = re.match(r"(\d+)", ver.strip()) if code == 0 else None
    if not m:
        say("?", "MX 백서 DB 판을 못 물었다(mxwp_postgres) — 이관 0056 이 지울 줄 수를 모른다")
        return
    if int(m.group(1)) >= 56:
        say("✓", f"MX 백서 DB 는 이미 {ver.strip()} — 0056 의 지우기는 지난 일이다")
        return
    code, n = run(base + ["SELECT count(*) FROM doc_triples t WHERE NOT EXISTS (SELECT 1 FROM documents d WHERE d.slug = t.subject_slug)"],
                  env=pw, timeout=60)
    n = n.strip()
    if code == 0 and n.isdigit():
        say("⚠" if int(n) else "✓", f"MX 백서 이관 0056 이 지울 짝 없는 doc_triples {n}줄 — 되돌릴 수 없다(update-all §1b 의 배포 전 백업에 남는다)"
            if int(n) else "MX 백서 이관 0056 이 지울 짝 없는 doc_triples 없음")


def _risk_version() -> None:
    """리스크 앱 DB 판(PRAGMA user_version). v5 아래면 첫 기동이 한 방향으로 올린다 — 이관 전 사본을 두므로 DB 크기만큼의 자리가 더 든다."""
    hub = find_repo("HEAXHub")
    p = hub / "var/app_data/hwax_risk/risk_review.db" if hub else None
    if p is None or not p.exists():
        return
    rows = ro_sqlite(p, "PRAGMA user_version")
    if rows is None:
        say("?", "리스크 앱 DB 판을 못 읽었다")
        return
    v, size = rows[0][0], p.stat().st_size / 2**20
    free = shutil.disk_usage(p.resolve().parent).free / 2**20
    if v < 5:
        say("⚠" if free < size * 1.2 else "·", f"리스크 앱 DB v{v}({size:,.0f}MiB) — 첫 기동이 v5 로 올린다(되돌리려면 이관 전 사본). 남은 자리 {free:,.0f}MiB")
    else:
        say("✓", f"리스크 앱 DB v{v}")


# ── 3. 설정 — 새 기능이 서려면 ─────────────────────────────────────────────────────────────────
def check_config() -> None:
    head("3. 설정(새 기능이 서려면 — 사람이 넣는 것)")
    agent = find_repo("HWAXAgentServer")
    aenv = agent / ".env" if agent else None
    sc = envv(aenv, "CHAT_SELF_CHECK")
    # 챗 자기검증(10-23) — 기본 켜짐. 모든 챗 답에 검토 호출이 하나 더 붙어 답이 늦어진다(실모델에서 잰 적 없다).
    say("·", f"챗 자기검증 CHAT_SELF_CHECK={sc or '(없음 — 기본 켜짐)'} — 끄려면 에이전트 .env 에 CHAT_SELF_CHECK=0")
    _context_cap(aenv)
    gw = find_repo("HWAXMcpGateway")
    penv = gw / "provision.env" if gw else None
    if penv and penv.is_file():
        if envv(penv, "HEAX_MCP_TOKEN"):
            say("✓", "게이트웨이 HEAX_MCP_TOKEN 고정됨")
        else:
            say("⚠", "게이트웨이 provision.env 에 HEAX_MCP_TOKEN 이 없다 — 재프로비저닝마다 허브에서 새로 발급한다(10-25 판부터 실패하면 앞 토큰으로 잇는다). 고정을 권한다")
        _mxwp_delegation(penv)
    _mxwp_env()
    _docforge()
    _portal()
    _mxwp_mcp_sdk()


def _context_cap(aenv: Path | None) -> None:
    """LLM_CONTEXT_TOKENS 는 10-22 전엔 '서버에 못 물을 때의 값' 이었고 그 뒤로는 **상한**이다 — 서버 창보다 작게 적혀 있으면 창이 그만큼 준다."""
    cap = envv(aenv, "LLM_CONTEXT_TOKENS")
    if not cap:
        say("✓", "LLM_CONTEXT_TOKENS 없음 — 서버가 답한 창을 그대로 쓴다")
        return
    srv = None
    st, h = get_json(AGENT + "/health")
    ctx = (h or {}).get("context") if isinstance(h, dict) else None
    if isinstance(ctx, dict):
        srv = ctx.get("server") or (ctx.get("tokens") if ctx.get("source") == "server" else None)
    if not srv:   # 에이전트와 같은 길 — VLLM_BASE_URL/models 의 그 모델(하나뿐이면 그것)의 max_model_len, 세 번 물어 작은 쪽
        e = env_all(aenv)
        base, key, model = (e.get("VLLM_BASE_URL") or "http://127.0.0.1:8000/v1").rstrip("/"), e.get("VLLM_API_KEY") or "EMPTY", e.get("VLLM_MODEL", "")
        got = []
        for _ in range(3):
            st, m = get_json(base + "/models", headers={"Authorization": f"Bearer {key}"}, loopback=False)
            data = [d for d in ((m or {}).get("data") or []) if isinstance(d, dict)] if isinstance(m, dict) else []
            pick = next((d for d in data if d.get("id") == model), data[0] if len(data) == 1 else None)
            if pick and (pick.get("max_model_len") or pick.get("context_length")):
                got.append(int(pick.get("max_model_len") or pick.get("context_length")))
        srv = min(got) if got else None
    if srv and cap.isdigit() and int(cap) < int(srv):
        say("⚠", f"LLM_CONTEXT_TOKENS={cap} 이 서버 창 {srv} 보다 작다 — 새 엔진에선 상한이라 심의 · 챗 창이 {cap} 으로 준다(섞인 풀의 작은 쪽이 아니면 지운다)")
    else:
        say("·", f"LLM_CONTEXT_TOKENS={cap}(서버 창 {srv or '모름'}) — 새 엔진에선 상한이다")


def _mxwp_delegation(penv: Path) -> None:
    """MX 백서 사람 명의 위임 — 게이트웨이 · MX 백서 두 곳의 비밀이 같아야 한다. 어긋나면 신원 있는 MX 백서 호출이 실패한다(서비스 계정으로 내려가지 않는다)."""
    mx = find_repo("MXWhitePaper")
    mxs = envv(mx / ".env", "MXWP_SSO_SECRET") if mx else ""
    on = "mx-white-paper:MXWP" in envv(penv, "PER_USER_SSO_APPS")
    gws = envv(penv, "MXWP_SSO_SECRET")
    if not on:
        say("·", "MX 백서 사람 명의 위임 꺼짐" + (" — MX 백서 .env 에는 비밀이 있다. 게이트웨이 PER_USER_SSO_APPS 에 mx-white-paper:MXWP 를 더하면 켜진다" if mxs
                                         else " — 켜는 법은 docs/mxwp-wiki PLAN"))
        return
    if not gws:
        say("✗", "PER_USER_SSO_APPS 에 mx-white-paper 가 있는데 provision.env 에 MXWP_SSO_SECRET 이 없다")
    elif not mxs:
        say("✗", "게이트웨이는 MX 백서 위임을 켰는데 MX 백서 .env 에 MXWP_SSO_SECRET 이 없다 — 신원 있는 MX 백서 호출이 전부 실패한다(MX 백서 쪽부터)")
    elif h8(gws) != h8(mxs):
        say("✗", f"MXWP_SSO_SECRET 이 두 곳에서 다르다(해시 앞자리 {h8(gws)} ≠ {h8(mxs)}) — 신원 있는 호출이 전부 실패한다")
    else:
        say("✓", "MX 백서 위임 비밀이 두 곳에서 같다")
        if not envv(penv, "MXWP_SSO_URL"):
            say("✗", "provision.env 에 MXWP_SSO_URL 이 없다(같은 박스면 http://127.0.0.1:8800/api/v1/auth/sso)")
        if envv(penv, "MXWP_SEND_PLAT") != "1":
            say("⚠", "MXWP_SEND_PLAT=1 이 아니다 — plat: 범위 위키 문서가 위임 호출에서 안 보인다")


def _mxwp_env() -> None:
    mx = find_repo("MXWhitePaper")
    if mx is None:
        return
    e = env_all(mx / ".env")
    if e.get("WIKI_ENABLED", "").lower() in TRUE:
        if not (e.get("WIKI_LLM_BASE_URL") and e.get("WIKI_LLM_MODEL")):
            q = (wiki_health().get("jobs") or {})
            say("✗", "MX 백서 WIKI_ENABLED=true 인데 WIKI_LLM_BASE_URL · WIKI_LLM_MODEL 이 없다 — 들이기 · 점검 작업이 줄에서 영영 기다린다"
                     + (f"(지금 {q.get('queued', 0)}건, 가장 오래 {int(q.get('oldest_queued_s') or 0) // 60}분)" if q else ""))
        else:
            llm = wiki_health().get("llm")
            say("✓" if llm in (None, "ok") else "⚠", f"MX 백서 위키 켜짐 · 위키 LLM 설정 있음" + (f" — 지금 LLM 상태 '{llm}'" if llm not in (None, "ok") else ""))
    else:
        say("·", "MX 백서 위키 꺼짐(WIKI_ENABLED) — 심의의 '위키에 남기기' 는 켤 때까지 실패한다(켜는 순서: docs/mxwp-wiki)")
    if e.get("MXWP_SSO_ONLY", "").lower() in TRUE and not e.get("MXWP_LOCAL_LOGIN_ALLOW"):
        say("⚠", "MXWP_SSO_ONLY 인데 MXWP_LOCAL_LOGIN_ALLOW 가 비었다 — 포털 SSO 가 고장 나면 관리자도 못 들어온다")


def _docforge() -> None:
    """DocForge — 받을 판의 등록 사본이 draft 면 게이트웨이에 안 실려 포털이 목적지를 숨긴다(그때 설정은 미리 넣어 둘 것으로만 알린다)."""
    hub = find_repo("HEAXHub")
    if hub is None:
        return
    man = upstream_file(hub, "integrations/doc-forge/.portal/manifest.yaml")
    if man is None:
        return
    m = re.search(r"^status:\s*(\S+)", man, re.M)
    live = bool(m and m.group(1) != "draft")
    kind = "⚠" if live else "·"
    if not live:
        say("·", "DocForge 등록이 draft — 게이트웨이에 안 실려 포털 「정밀 변환」 은 목적지에 안 뜬다(10-25 판부터). 아래는 베타가 오기 전에 넣어 둘 것")
    if not envv(hub / ".env", "APPTAINERENV_DOCFORGE_INPUT_ROOTS"):
        say(kind, "HEAXHub .env 에 APPTAINERENV_DOCFORGE_INPUT_ROOTS 가 없다 — DocForge 가 모든 변환을 거절한다(docs/doc-to-ra/server-setup §1)")
    models = hub / "var/app_data/doc_forge/models"
    if not (models.is_dir() and any(models.iterdir())):
        say(kind, "DocForge 모델(Docling)이 없다 — PDF 변환이 실패한다. 한 번: cd HEAXHub && HEAX_MODEL_APPS=\"doc_forge\" bash deploy/apptainer/models-from-drive.sh")


def _portal() -> None:
    benv = ROOT / "backend/.env"
    cat = envv(benv, "CATALOG_PATH")
    p = (Path(cat) if cat.startswith("/") else ROOT / "backend" / cat) if cat else ROOT / "backend/config/systems.yaml"
    txt = p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""
    if cat and not p.is_file():
        say("✗", f"포털 CATALOG_PATH 의 파일이 없다({p}) — 포털이 카탈로그를 읽지 못해 뜨지 못한다")
    mm = re.search(r"^(\s*)-\s+id:\s*mx-white-paper\s*$", txt, re.M)
    if mm:
        rest = txt[mm.end():]
        nxt = re.search(r"^\s*-\s+id:", rest, re.M)
        if not re.search(r"^\s*claims_affiliation:\s*true\b", rest[:nxt.start()] if nxt else rest, re.M):
            say("⚠", f"{p.name} 의 mx-white-paper 에 claims_affiliation: true 가 없다 — 타일 진입이 MX 백서에 소속을 싣지 않는다(위키 소속 범위)")
    us = envv(ROOT / "infra/.env", "USER_STORE_PATH") or envv(benv, "USER_STORE_PATH")
    q = Path(us) if us.startswith("/") else ROOT / "backend" / (us or "data/users.sqlite")
    if q.exists() and q.stat().st_mode & 0o077:
        say("⚠", f"계정 원장 {q} 를 다른 계정도 읽을 수 있다({oct(q.stat().st_mode & 0o777)}) — 외부 연결 토큰이 평문으로 든다. chmod 600 을 권한다")


def _mxwp_mcp_sdk() -> None:
    """MX 백서 MCP(mxwp_api 안 python3 -m mcp)는 그 안의 mcp SDK 를 쓴다 — FastMCP.tool 이 annotations 를 못 받으면 위키 읽기 표지만 빠진다(서버는 뜬다)."""
    probe = ('cd / && python3 -c "import inspect, importlib.metadata as m; from mcp.server.fastmcp import FastMCP; '
             'print(m.version(\'mcp\'), \'annotations\' in inspect.signature(FastMCP.tool).parameters)"')
    code, out = run([appt(), "exec", "instance://mxwp_api", "bash", "-lc", probe], timeout=60)
    parts = out.split()
    if code != 0 or len(parts) < 2:
        say("?", "MX 백서 MCP 의 mcp SDK 를 못 물었다(mxwp_api)")
    elif parts[-1] == "True":
        say("✓", f"MX 백서 MCP SDK {parts[-2]} — 읽기 표지를 단다")
    else:
        say("⚠", f"MX 백서 MCP SDK {parts[-2]} — 읽기 표지를 못 단다(읽기 전용 토큰으로 위키 읽기 도구가 막힌다)")


# ── 4. Drive — 이 박스가 받을 판 ────────────────────────────────────────────────────────────────
def check_drive() -> None:
    head("4. Drive(이 박스가 받을 판)")
    if not shutil.which("rclone"):
        say("?", "rclone 이 없다 — Drive 를 못 본다")
        return
    # 포털 화면 — Drive 의 dist 가 받을 소스의 frontend 트리로 지은 것인가. 다르면 update-all §6 이 'SPA dist 가 지금 소스와 다르다' 로 실패한다.
    r = envv(ROOT / "infra/.env", "HWAX_DRIVE_REMOTE").rstrip("/")
    if r:
        code, up = run(["git", "rev-parse", "@{u}:frontend"], cwd=ROOT)
        _, built = run(["bash", "-c", 'rclone cat "$1/latest/frontend-dist.tar.gz" 2>/dev/null | tar -xzO dist/.build-src 2>/dev/null', "_", r], timeout=300)
        built, up = built.strip(), up.strip()
        if not built:
            say("?", "Drive 포털 화면의 빌드 표지(.build-src)를 못 읽었다")
        elif code == 0 and up and built != up:
            say("✗", f"Drive 포털 화면이 받을 소스와 다르다(빌드 {built[:10]} ≠ 소스 {up[:10]}) — dev 에서 build-all-to-drive.sh portal 이 먼저다")
        else:
            say("✓", "Drive 포털 화면이 받을 소스와 같다")
    mx = find_repo("MXWhitePaper")
    rm = envv(mx / ".env", "MXWP_IMAGES_REMOTE").rstrip("/") if mx else ""
    if rm:
        code, out = run(["rclone", "lsl", f"{rm}/latest/"], timeout=120)
        have = {ln.split()[-1]: " ".join(ln.split()[1:3])[:16] for ln in out.splitlines() if len(ln.split()) >= 4}
        wiki_on = envv(mx / ".env", "WIKI_ENABLED").lower() in TRUE
        for b in ("web.sif", "api.sif", "wiki.sif"):
            if b in have:
                say("·", f"MX 백서 Drive {b} — {have[b]}")
            elif b == "wiki.sif" and not wiki_on:
                say("·", "MX 백서 Drive latest/ 에 wiki.sif 가 없다 — 위키를 켜기 전엔 필요 없다")
            else:
                say("⚠", f"MX 백서 Drive latest/ 에 {b} 가 없다" + (" — 위키 워커가 뜨지 못한다(API · 웹은 뜬다)" if b == "wiki.sif" else ""))
    hub = find_repo("HEAXHub")
    rh = envv(hub / ".env", "HEAX_DRIVE_REMOTE").rstrip("/") if hub else ""
    if rh:
        # 허브 받기(dist-from-drive)는 latest/ 를 받아 `sha256sum -c SHA256SUMS` — 목록의 파일이 하나라도 없거나 다르면 허브 배치 전체가
        # 'checksum failed' 로 멈춘다. 목록 밖 SIF 는 대조 없이 깔린다. Drive 의 서버 쪽 해시로 미리 견준다(내려받지 않는다).
        code, sums = run(["rclone", "cat", f"{rh}/latest/SHA256SUMS"], timeout=120)
        listed = {}
        for ln in sums.splitlines():
            f = ln.split()
            if len(f) >= 2:
                listed[f[-1].removeprefix("./")] = f[0].lower()
        hc, hs = run(["rclone", "hashsum", "sha256", f"{rh}/latest/"], timeout=300)
        drive = {ln.split()[-1]: ln.split()[0].lower() for ln in hs.splitlines() if len(ln.split()) >= 2} if hc == 0 else {}
        if code != 0 or not listed:
            say("?", "허브 Drive latest/ 의 SHA256SUMS 를 못 읽었다 — 받는 쪽은 대조 없이 받는다")
        elif not drive:
            say("?", "허브 Drive 의 서버 쪽 해시를 못 받았다(rclone 판?) — 대조 목록을 미리 견주지 못했다")
        else:
            gone = [n for n in listed if n not in drive]
            diff = [n for n, h in listed.items() if n in drive and drive[n] and drive[n] != h]
            loose = [n for n in drive if n.endswith(".sif") and n not in listed]
            if gone or diff:
                say("✗", f"허브 Drive 대조 목록이 latest/ 와 어긋난다(없음 {len(gone)} · 다름 {len(diff)}: {', '.join((gone + diff)[:6])}) — 이 박스의 허브 받기가 "
                         "'checksum failed' 로 멈춰 허브 앱이 하나도 안 바뀐다. dev 에서 목록을 다시 올린다(drive-push-sif.sh 가 합쳐 올린다)")
            else:
                say("✓", f"허브 Drive 대조 목록 {len(listed)}줄이 latest/ 와 맞는다")
            if loose:
                say("·", f"허브 Drive latest/ 의 SIF {len(loose)}개는 대조 목록 밖이다 — 내용 대조 없이 깔린다(.sif.hash 는 커밋 표지다). "
                         "rclone 이 받을 때 해시로 확인해 위험은 낮다")


def main() -> int:
    print(f"update-all 사전 점검 — {ROOT}{'' if FETCH else ' (원격 안 묻기)'}")
    for f in (check_running, check_data, check_config, check_drive):
        try:
            f()
        except Exception as e:  # noqa: BLE001 — 한 구역이 터져도 나머지는 본다
            say("?", f"{f.__name__} 를 끝까지 못 봤다 — {type(e).__name__}: {e}")
    bad = [m for k, m in RESULTS if k == "✗"]
    print(f"\n요약 — ✗ {len(bad)} · ⚠ {sum(1 for k, _ in RESULTS if k == '⚠')} · ? {sum(1 for k, _ in RESULTS if k == '?')}")
    if bad:
        print("✗ 가 있다 — update-all 전에 그 줄의 할 일을 한다.")
        for m in bad:
            print(f"  ✗ {m}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
