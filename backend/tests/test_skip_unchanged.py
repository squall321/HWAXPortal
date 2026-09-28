# update-all 이 바뀌지 않은 서비스를 받지도 재기동하지도 않는지 — 기준은 '마지막으로 띄운 시점의 지문', 기록은 '새 프로세스가 답한 뒤에만'(docs/update-all-skip-unchanged, 2026-09-27)
import importlib.util
import os
import re
import signal
import socket
import subprocess
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "infra/scripts/lib/change-detect.sh"
DEPLOY_ALL = (ROOT / "infra/scripts/deploy-all-from-drive.sh").read_text(encoding="utf-8")
UPDATE_SITES = (ROOT / "infra/scripts/update-sites.sh").read_text(encoding="utf-8")
UPDATE_ALL = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")
IMAGES = (ROOT / "infra/scripts/images-from-drive.sh").read_text(encoding="utf-8")
NOT_ROOT = pytest.mark.skipif(os.geteuid() == 0, reason="root 는 권한을 무시한다")


def _sh(script: str, **env) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", "-c", f'. "{LIB}"\n{script}'], capture_output=True, text=True, timeout=120,
                          env={"PATH": os.environ["PATH"], "HOME": os.environ.get("HOME", "/tmp"), **env})


def _git(*a, cwd):
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True, check=True,
                          env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x"})


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0)); return s.getsockname()[1]


# 실제 HTTP 리스너(python http.server) — hwax_alive·hwax_wait_down·hwax_listener_ids 를 진짜 curl·ss 로 태운다.
# 살아 있는 프로세스로 '같은 프로세스가 답한다' 를 재현하려면 pid 가 실제로 있어야 한다(/proc/<pid>/stat 을 읽는다).
SRV_TOOLS = r'''
_srv_start() {  # $1=port $2=pidfile — 떠서 답할 때까지(최대 5초) 기다린다
  ( cd "$(dirname "$2")" && exec python3 -m http.server "$1" --bind 127.0.0.1 ) >/dev/null 2>&1 &
  echo $! > "$2"; echo $! >> "$2.all"
  local i; for i in $(seq 1 50); do hwax_alive "http://127.0.0.1:$1/" && return 0; sleep 0.1; done; return 1
}
_srv_stop() {  # $1=pidfile
  local p i; p="$(cat "$1" 2>/dev/null)"; : > "$1"; [ -n "$p" ] || return 0
  kill "$p" 2>/dev/null; for i in $(seq 1 30); do kill -0 "$p" 2>/dev/null || return 0; sleep 0.1; done; kill -9 "$p" 2>/dev/null; return 0
}
'''


def _kill_all(pidfile: Path):
    for f in (pidfile.with_suffix(pidfile.suffix + ".all"), pidfile):
        if f.exists():
            for tok in f.read_text().split():
                try: os.kill(int(tok), signal.SIGKILL)
                except (ProcessLookupError, ValueError, PermissionError): pass


@pytest.fixture
def srv(tmp_path):
    pf = tmp_path / "srv.pid"; port = _free_port()
    yield port, pf
    _kill_all(pf)


# ── 지문 ──────────────────────────────────────────────────────────────────────
def test_fp_changes_on_size_or_mtime_and_is_stable_otherwise(tmp_path):
    d = tmp_path / "art"; d.mkdir(); (d / "a.sif").write_bytes(b"x" * 100); os.utime(d / "a.sif", (1_700_000_000, 1_700_000_000))
    env = tmp_path / ".env"; env.write_text("A=1\n")
    a = _sh(f'hwax_fp "{d}" "{env}"').stdout.strip(); b = _sh(f'hwax_fp "{d}" "{env}"').stdout.strip()
    assert a == b and len(a) == 12
    os.utime(d / "a.sif", (1_700_000_100, 1_700_000_100))
    assert _sh(f'hwax_fp "{d}" "{env}"').stdout.strip() != a
    os.utime(d / "a.sif", (1_700_000_000, 1_700_000_000)); env.write_text("A=2\n")
    assert _sh(f'hwax_fp "{d}" "{env}"').stdout.strip() != a, "작은 파일은 내용"
    env.write_text("A=1\n"); assert _sh(f'hwax_fp "{d}" "{env}"').stdout.strip() == a
    m1 = _sh(f'hwax_fp "{d}" "{tmp_path}/nope"').stdout.strip(); m2 = _sh(f'hwax_fp "{d}" "{tmp_path}/nope"').stdout.strip()
    assert m1 != a and m1 == m2, "없는 경로는 'missing' 으로 지문에 들어가고 안정적이다"


def test_fp_uses_size_and_mtime_not_content_for_big_files(tmp_path):
    big = tmp_path / "big.sif"
    with open(big, "wb") as f: f.truncate(40 * 1024 * 1024)
    os.utime(big, (1_700_000_000, 1_700_000_000))
    t0 = time.time(); a = _sh(f'hwax_fp "{big}"').stdout.strip(); dt = time.time() - t0
    assert dt < 1.0, f"큰 파일 지문이 {dt:.2f}s — 내용을 읽고 있다"
    with open(big, "r+b") as f: f.seek(0); f.write(b"changed")
    os.utime(big, (1_700_000_000, 1_700_000_000))
    assert _sh(f'hwax_fp "{big}"').stdout.strip() == a, "같은 크기·mtime 이면 같다(의도된 한계 — 설치가 cp -p·cmp 라 실제론 안 생긴다)"
    os.utime(big, (1_700_000_001, 1_700_000_001))
    assert _sh(f'hwax_fp "{big}"').stdout.strip() != a


def test_install_if_changed_returns_installed_same_or_failed(tmp_path):
    src = tmp_path / "cache/x.sif"; src.parent.mkdir(); src.write_bytes(b"abc"); os.utime(src, (1_600_000_000, 1_600_000_000))
    dst = tmp_path / "live/x.sif"; dst.parent.mkdir()
    assert "rc=0" in _sh(f'hwax_install_if_changed "{src}" "{dst}"; echo rc=$?').stdout and int(dst.stat().st_mtime) == 1_600_000_000
    ino = dst.stat().st_ino; os.utime(dst, (1_650_000_000, 1_650_000_000))
    assert "rc=1" in _sh(f'hwax_install_if_changed "{src}" "{dst}"; echo rc=$?').stdout and dst.stat().st_ino == ino, "같은 내용은 손대지 않는다"
    src.write_bytes(b"abcd"); assert "rc=0" in _sh(f'hwax_install_if_changed "{src}" "{dst}"; echo rc=$?').stdout and dst.read_bytes() == b"abcd"


@NOT_ROOT
def test_install_if_changed_reports_a_failed_copy_loudly(tmp_path):
    """검토: cp 실패가 '같음 — 그대로' 로 찍히고 rc 0 이었다 — 옛 SIF 가 조용히 남는다."""
    src = tmp_path / "x.sif"; src.write_bytes(b"new"); dst = tmp_path / "x-live.sif"; dst.write_bytes(b"old"); dst.chmod(0o444)   # 쓸 수 없는 대상(다른 소유자와 같다)
    try:
        r = _sh(f'hwax_install_if_changed "{src}" "{dst}"; echo rc=$?')
        assert "rc=2" in r.stdout and "설치 실패" in r.stderr and dst.read_bytes() == b"old", r.stdout + r.stderr
    finally:
        dst.chmod(0o644)


# ── 판정 — 마지막 기동 지문 기준 ────────────────────────────────────────────────────
def _decide(tmp_path, cur, alive=(True,), env=None, state=None):
    urls = " ".join(f"http://127.0.0.1:{i}/h" for i in range(len(alive)))
    curl = "curl() { case \"$*\" in " + " ".join(f'*127.0.0.1:{i}/*) printf {"200" if a else "000"};;' for i, a in enumerate(alive)) + " esac; }"
    st = tmp_path / "state"; st.mkdir(exist_ok=True)
    if state is not None: (st / "svc").write_text(state + "\n")
    e = {"HWAX_RESTART_STATE_DIR": str(st), "HWAX_RESTART_SKIPPED_FILE": str(tmp_path / "skipped"), **(env or {})}
    r = _sh(f'{curl}\nif hwax_restart_needed svc "{cur}" {urls}; then echo NEED; else echo SKIP; fi', **e)
    return r.stdout


def test_restart_needed_compares_with_the_last_start_not_with_block_entry(tmp_path):
    """검토(1라운드, high): '블록 전/후' 기준은 §1 의 git reset·§1c/1d/1e 의 .env·routes 기록·운영자 편집이 전부 블록 밖이라 안 보여
    백엔드 커밋과 설정 변경이 재기동을 영원히 못 일으켰다. 기준은 마지막으로 띄운 시점의 지문이다."""
    assert "NEED" in _decide(tmp_path, "aaa") and "기록이 없다" in _decide(tmp_path, "aaa"), "기록이 없으면 재기동"
    out = _decide(tmp_path, "aaa", state="aaa"); assert "SKIP" in out and "재기동 생략" in out and (tmp_path / "skipped").read_text().strip() == "svc"
    out = _decide(tmp_path, "bbb", state="aaa"); assert "NEED" in out and "마지막 기동 뒤 변경 있음" in out, "블록 안에서 전후가 같아도 마지막 기동과 다르면 재기동"
    out = _decide(tmp_path, "aaa", alive=(False,), state="aaa"); assert "NEED" in out and "답하지 않는다" in out
    out = _decide(tmp_path, "aaa", alive=(True, False), state="aaa"); assert "NEED" in out, "인스턴스가 여럿이면 하나라도 죽었으면 띄운다"
    out = _decide(tmp_path, "aaa", state="aaa", env={"HWAX_RESTART_ALL": "1"}); assert "NEED" in out and "HWAX_RESTART_ALL=1" in out


def test_mark_started_writes_the_state_file(tmp_path):
    st = tmp_path / "s"
    r = _sh('hwax_mark_started portal "abc|def"; hwax_last_fp portal', HWAX_RESTART_STATE_DIR=str(st))
    assert r.stdout.strip() == "abc|def" and (st / "portal").read_text() == "abc|def\n"


@NOT_ROOT
def test_mark_started_failure_is_loud_but_not_fatal(tmp_path):
    """상태 디렉터리에 못 쓰면(sudo 로 한 번 돌려 root 소유 등) ⚠ 를 내고 0 — 재기동은 이미 됐고 다음 실행이 한 번 더 재기동할 뿐이다."""
    st = tmp_path / "s"; st.mkdir(); st.chmod(0o555)
    try:
        r = _sh('hwax_mark_started portal abc; echo rc=$?', HWAX_RESTART_STATE_DIR=str(st))
        assert "rc=0" in r.stdout and "기록하지 못했다" in r.stderr and not (st / "portal").exists()
    finally:
        st.chmod(0o755)


# ── 리스너 식별 — 실제 ss·/proc ────────────────────────────────────────────────────
def test_port_of_url():
    r = _sh('hwax_port_of_url http://127.0.0.1:8701/mcp; echo; hwax_port_of_url http://localhost:4180/health; echo; hwax_port_of_url http://localhost/x; echo')
    assert r.stdout.split() == ["8701", "4180", "80"]


def test_listener_ids_identify_the_process_on_the_port_and_change_when_it_is_replaced(tmp_path, srv):
    port, pf = srv
    r = _sh(f'{SRV_TOOLS}\n_srv_start {port} "{pf}" || exit 9; a="$(hwax_listener_ids http://127.0.0.1:{port}/)"; _srv_stop "{pf}"'
            f'\nb="$(hwax_listener_ids http://127.0.0.1:{port}/)"; _srv_start {port} "{pf}" || exit 9; c="$(hwax_listener_ids http://127.0.0.1:{port}/)"; echo "$a|$b|$c"')
    assert r.returncode == 0, r.stderr
    a, b, c = r.stdout.strip().split("|")
    assert re.fullmatch(rf"{port}:\d+:\d+", a), a
    assert b == f"{port}:?", "아무도 안 들으면 포트:?"
    assert re.fullmatch(rf"{port}:\d+:\d+", c) and c != a, "다른 프로세스가 물려받으면 식별자가 바뀐다"


# ── 재기동 사이클 — 새 프로세스가 답할 때만 기록한다 ────────────────────────────────────────
def _cycle(tmp_path, srv, body: str, cur="f1", state=None, env=None, running=True):
    port, pf = srv
    st = tmp_path / "state"; st.mkdir(exist_ok=True)
    (st / "svc").unlink(missing_ok=True)
    if state is not None: (st / "svc").write_text(state + "\n")
    pre = f'_srv_stop "{pf}"' + (f'\n_srv_start {port} "{pf}" || exit 9' if running else "")
    t0 = time.time()
    r = _sh(f'{SRV_TOOLS}\nPORT={port}; PF="{pf}"; URL=http://127.0.0.1:{port}/\n{pre}\n{body}\n'
            f'hwax_restart_cycle svc "{cur}" _stop _start "$URL"; echo "rc=$? R=$HWAX_RESTARTED"',
            HWAX_RESTART_STATE_DIR=str(st), HWAX_WAIT_DOWN_MAX="3", **(env or {}))
    recorded = (st / "svc").read_text().strip() if (st / "svc").exists() else None
    return r.stdout, r.stderr, recorded, time.time() - t0


def test_cycle_restarts_and_records_when_a_new_process_answers(tmp_path, srv):
    out, err, rec, _ = _cycle(tmp_path, srv, '_stop() { _srv_stop "$PF"; }; _start() { _srv_start "$PORT" "$PF"; }')
    assert "rc=0 R=1" in out and rec == "f1", (out, err)
    pids = (srv[1].with_suffix(".pid.all")).read_text().split(); assert len(pids) == 2 and pids[0] != pids[1], "정말 새 프로세스로 갈렸다"


def test_cycle_refuses_to_record_when_the_same_process_still_answers(tmp_path, srv):
    """2라운드(high): stop 이 실패하면 start 는 'already running' 으로 rc 0 을 낸다 — 그 rc 만 믿고 새 지문을 적으면 옛 프로세스가 영구 생략된다."""
    out, err, rec, _ = _cycle(tmp_path, srv, '_stop() { return 1; }; _start() { :; }', cur="f2", state="f1")
    assert "rc=1 R=0" in out and rec == "f1" and "재기동이 되지 않았다" in err and "정지 뒤에도 답한다" in err, (out, err)


def test_cycle_no_restart_mode_starts_only_and_records_nothing(tmp_path, srv):
    out, err, rec, _ = _cycle(tmp_path, srv, '_stop() { echo STOP-CALLED; }; _start() { :; }', cur="f2", state="f1", env={"RESTART": "1"})
    assert "rc=0 R=0" in out and rec == "f1" and "NO_RESTART=1" in out and "STOP-CALLED" not in out, (out, err)


def test_cycle_colon_stop_means_start_replaces_the_process_itself(tmp_path, srv):
    """AIDH boot.sh --force 류 — 정지 함수가 ':' 면 내려감을 기다리지 않는다(기다리면 살아 있는 서비스 앞에서 20초를 헛되이 센다)."""
    port, pf = srv
    st = tmp_path / "state"; st.mkdir(exist_ok=True)
    t0 = time.time()
    r = _sh(f'{SRV_TOOLS}\nPORT={port}; PF="{pf}"; _srv_start {port} "{pf}" || exit 9\n_start() {{ _srv_stop "$PF"; _srv_start "$PORT" "$PF"; }}\n'
            f'hwax_restart_cycle aidh f1 : _start http://127.0.0.1:{port}/; echo "rc=$? R=$HWAX_RESTARTED"', HWAX_RESTART_STATE_DIR=str(st), HWAX_WAIT_DOWN_MAX="20")
    assert "rc=0 R=1" in r.stdout and (st / "aidh").read_text().strip() == "f1", (r.stdout, r.stderr)
    assert time.time() - t0 < 12, "내려감 대기(20초)를 건너뛰었다"


def test_cycle_fails_when_start_claims_success_but_nothing_listens(tmp_path, srv):
    out, err, rec, _ = _cycle(tmp_path, srv, '_stop() { :; }; _start() { :; }', running=False)
    assert "rc=1" in out and rec is None and "답하지 않는다(리스너 없음)" in err, (out, err)


def test_cycle_skips_without_touching_stop_or_start_when_unchanged_and_alive(tmp_path, srv):
    out, err, rec, _ = _cycle(tmp_path, srv, '_stop() { echo STOP-CALLED; }; _start() { echo START-CALLED; }', cur="f1", state="f1")
    assert "rc=0 R=0" in out and "재기동 생략" in out and "CALLED" not in out and rec == "f1"


def test_cycle_start_failure_records_nothing(tmp_path, srv):
    out, err, rec, _ = _cycle(tmp_path, srv, '_stop() { _srv_stop "$PF"; }; _start() { return 1; }', cur="f2", state="f1")
    assert "rc=1" in out and rec == "f1"


# ── deploy-all 포털 블록 — 실 git 리포 + 스텁으로 통째로 돈다 ─────────────────────────────
def _portal_block() -> str:
    i = DEPLOY_ALL.index('  ( cd "$PORTAL_DIR"\n    git_update'); j = DEPLOY_ALL.index('skip "portal failed (see above)"', i) + len('skip "portal failed (see above)"')
    return DEPLOY_ALL[i:j]


def _portal_harness(tmp_path):
    """블록의 url 은 :8723/:8088 로 박혀 있어(dev 에는 진짜 포털이 듣는다) ss·curl 을 셈으로 바꾼다 — 리스너는 진짜 프로세스(sleep) 의 pid 로 흉내 낸다.
    start.sh 스텁은 실물처럼 '이미 떠 있으면 새로 띄우지 않고 rc 0'."""
    origin = tmp_path / "origin"; origin.mkdir(); _git("init", "-q", "-b", "main", cwd=origin)
    (origin / "backend/app").mkdir(parents=True); (origin / "backend/app/main.py").write_text("VERSION=1\n")
    (origin / ".gitignore").write_text("infra/.env\nbackend/.env\nbackend/config/routes.local.env\ninfra/apptainer/\nfrontend/dist/\ninfra/.state/\n")
    _git("add", ".", cwd=origin); _git("commit", "-qm", "A", cwd=origin)
    repo = tmp_path / "portal"; _git("clone", "-q", str(origin), str(repo), cwd=tmp_path)
    (repo / "infra/scripts").mkdir(parents=True); (repo / "infra/apptainer").mkdir(); (repo / "frontend/dist").mkdir(parents=True); (repo / "backend/config").mkdir(parents=True)
    (repo / "infra/.env").write_text("HTTP_PORT=8088\n"); (repo / "backend/.env").write_text("RA_BASE_URL=http://127.0.0.1:3000\n"); (repo / "infra/apptainer/portal.sif").write_bytes(b"sif"); (repo / "frontend/dist/index.html").write_text("x")
    calls = tmp_path / "calls.log"; listener = tmp_path / "listener"; sleeps = tmp_path / "srv.pid"   # srv.pid.all 에 전부 적어 정리한다
    stubs = {
        "images-from-drive.sh": f'echo images-from-drive.sh >> "{calls}"\n',
        "stop.sh": f'echo stop.sh >> "{calls}"\np="$(cat "{listener}" 2>/dev/null)"; [ -n "$p" ] && kill "$p" 2>/dev/null; : > "{listener}"\n',
        "start.sh": f'echo start.sh >> "{calls}"\np="$(cat "{listener}" 2>/dev/null)"; if [ -n "$p" ] && kill -0 "$p" 2>/dev/null; then echo "already running"; exit 0; fi\n'
                    f'sleep 300 >/dev/null 2>&1 </dev/null & echo $! > "{listener}"; echo $! >> "{sleeps}.all"\n',   # 파이프를 물지 않게(안 그러면 하네스가 sleep 이 끝날 때까지 매달린다)
    }
    def write_stubs(**override):
        for name, body in {**stubs, **override}.items():
            f = repo / "infra/scripts" / name; f.write_text("#!/usr/bin/env bash\n" + body); f.chmod(0o755)
    write_stubs()
    shim = tmp_path / "bin"; shim.mkdir()
    (shim / "curl").write_text(f'#!/usr/bin/env bash\np="$(cat "{listener}" 2>/dev/null)"; if [ -n "$p" ] && kill -0 "$p" 2>/dev/null; then printf 200; else printf 000; fi\n'); (shim / "curl").chmod(0o755)
    (shim / "ss").write_text(f'#!/usr/bin/env bash\np="$(cat "{listener}" 2>/dev/null)"; [ -n "$p" ] && echo "LISTEN 0 128 127.0.0.1:x 0.0.0.0:* users:((\\"x\\",pid=$p,fd=3))"; exit 0\n'); (shim / "ss").chmod(0o755)
    fp_git = DEPLOY_ALL[DEPLOY_ALL.index("_fp_git() {"):]; fp_git = fp_git[:fp_git.index("\n") + 1]
    ngfp = DEPLOY_ALL[DEPLOY_ALL.index("_ngfp() {"):]; ngfp = ngfp[:ngfp.index("\n}\n") + 3]
    def run():
        script = (f'set -uo pipefail\nPORTAL_DIR="{repo}"; RESTART=0\n. "{LIB}"\nexport HWAX_RESTART_STATE_DIR="{tmp_path}/state" HWAX_RESTART_SKIPPED_FILE="{tmp_path}/skipped" HWAX_WAIT_DOWN_MAX=2\n'
                  f'ok() {{ echo "OK:$*"; }}; skip() {{ echo "SKIP:$*"; }}; set_remote() {{ :; }}\n'
                  f'git_update() {{ git fetch -q origin main && git reset -q --hard origin/main; }}\n{fp_git}{ngfp}\n{_portal_block()}')
        calls.unlink(missing_ok=True)
        r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=90, env={"PATH": f"{shim}:{os.environ['PATH']}", "HOME": str(tmp_path)})
        return r.stdout + r.stderr, (calls.read_text().split() if calls.exists() else [])
    state = lambda: (tmp_path / "state/portal").read_text().strip() if (tmp_path / "state/portal").exists() else None  # noqa: E731
    return origin, repo, run, write_stubs, state, sleeps


@pytest.fixture
def portal(tmp_path):
    h = _portal_harness(tmp_path)
    yield h
    _kill_all(h[5]); _kill_all(tmp_path / "listener")


def test_portal_block_restarts_on_first_run_then_skips_then_restarts_on_code_or_env_change(portal):
    origin, repo, run, _, state, _ = portal
    out, calls = run(); assert calls == ["images-from-drive.sh", "stop.sh", "start.sh"] and "기록이 없다" in out and "OK:portal up" in out and state(), (out, calls)
    out, calls = run(); assert calls == ["images-from-drive.sh"] and "재기동 생략" in out, "두 번째: 받기만 하고 재기동은 생략"
    # §1 이 먼저 당긴 것처럼 — 블록 밖에서 리포가 새 커밋으로 옮겨진다
    (origin / "backend/app/main.py").write_text("VERSION=2\n"); _git("commit", "-qam", "B", cwd=origin)
    _git("fetch", "-q", "origin", cwd=repo); _git("reset", "-q", "--hard", "origin/main", cwd=repo)
    out, calls = run(); assert "stop.sh" in calls and "start.sh" in calls and "변경 있음" in out, "백엔드 커밋(§1 이 이미 당김)이 재기동을 일으킨다"
    out, calls = run(); assert calls == ["images-from-drive.sh"], "다시 안정"
    (repo / "backend/.env").write_text("RA_BASE_URL=http://ra.example:3000\n")     # §1e 가 블록 전에 적은 것과 같다
    out, calls = run(); assert "start.sh" in calls, ".env 변경(블록 밖)이 재기동을 일으킨다"
    (repo / "backend/config/routes.local.env").write_text("ste=http://127.0.0.1:15810/\n")   # §1d
    out, calls = run(); assert "start.sh" in calls, "routes.local.env 변경이 재기동을 일으킨다"
    out, calls = run(); assert calls == ["images-from-drive.sh"]


def test_portal_block_does_not_record_a_start_that_failed(portal):
    _, repo, run, write_stubs, state, _ = portal
    write_stubs(**{"start.sh": 'echo start.sh >> "$(dirname "$0")/../../../calls.log"\nexit 1\n'})
    out, calls = run(); assert "SKIP:portal failed" in out and state() is None, "실패한 기동은 기준이 되지 않는다 — 다음 실행이 다시 시도한다"


def test_portal_block_does_not_record_an_already_running_old_process(portal):
    """2라운드(high): stop.sh 가 실패하면 start.sh 는 'already running' rc 0 — 옛 프로세스가 도는데 새 지문이 적혀 영구 생략됐다."""
    _, repo, run, write_stubs, state, _ = portal
    out, calls = run(); first = state(); assert first
    (repo / "backend/.env").write_text("K=2\n")
    write_stubs(**{"stop.sh": 'echo stop.sh >> "$(dirname "$0")/../../../calls.log"\nexit 1\n'})    # 정지가 안 된다
    out, calls = run()
    assert "SKIP:portal failed" in out and "재기동이 되지 않았다" in out and state() == first, ("옛 프로세스가 답하는데 기록하지 않는다", out)
    write_stubs()                                                                                     # 정지가 다시 된다
    out, calls = run(); assert "OK:portal up" in out and state() not in (None, first), "다음 정상 실행이 재기동하고 그때 기록한다"


def test_portal_block_stops_at_a_failed_artifact_pull(portal):
    """`( … ) && ok || skip` 안은 set -e 가 꺼져 있다 — images-from-drive 가 실패해도 옛 SIF 로 기동하고 초록이었다."""
    _, repo, run, write_stubs, state, _ = portal
    write_stubs(**{"images-from-drive.sh": 'echo images-from-drive.sh >> "$(dirname "$0")/../../../calls.log"\nexit 1\n'})
    out, calls = run(); assert "SKIP:portal failed" in out and calls == ["images-from-drive.sh"] and state() is None


def test_deploy_all_wires_every_service_and_nginx_through_the_restart_cycle():
    for svc in ("portal", "mxwp", "heax", "signalforge", "kooremapper"):
        assert f'hwax_restart_cycle {svc} "$_cur" _stop _start' in DEPLOY_ALL, svc
    assert 'hwax_restart_cycle aidh "$_cur" : _start http://localhost:8001/' in DEPLOY_ALL, "AIDH 는 boot.sh --force 가 스스로 갈아 끼운다"
    assert 'hwax_restart_cycle nginx "$_ngcur" _stop _start' in DEPLOY_ALL and "_ngfp() {" in DEPLOY_ALL
    assert "hwax_restart_needed" not in DEPLOY_ALL and DEPLOY_ALL.count("hwax_mark_started") == 1, "기록은 사이클 안에서만(nginx 는 포털 start.sh 가 함께 띄운 것을 적는다)"
    assert '[ "${HWAX_RESTARTED:-0}" = 1 ] && hwax_mark_started nginx "$(_ngfp)"' in DEPLOY_ALL
    assert 'HWAX_RESTART_STATE_DIR="${HWAX_RESTART_STATE_DIR:-$PORTAL_DIR/infra/.state/restart-fp}"' in DEPLOY_ALL
    assert '"$HWAX_RESTART_SKIPPED_FILE"\' EXIT' in DEPLOY_ALL, "끊긴 실행이 장부 파일을 /tmp 에 남기지 않는다"
    for two in ("http://127.0.0.1:8800/api/v1/healthz http://127.0.0.1:5173/", "http://127.0.0.1:18000/health http://127.0.0.1:17370/", "http://127.0.0.1:8700/api/health http://127.0.0.1:8701/mcp"):
        assert two in DEPLOY_ALL, "인스턴스가 여럿인 서비스는 둘 다 답해야 생략"
    assert "http://127.0.0.1:8701/ " not in DEPLOY_ALL and "http://127.0.0.1:8701/'" not in DEPLOY_ALL, "MCP 루트는 404 라 매 회 '죽었다' 였다(2라운드)"
    assert DEPLOY_ALL.count("./infra/scripts/images-from-drive.sh || exit 1") == 2 and "./deploy/apptainer/dist-from-drive.sh || exit 1" in DEPLOY_ALL and "./scripts/sync-from-drive.sh || exit 1" in DEPLOY_ALL, "받기 실패는 블록을 끊는다"
    assert "hwax_fp deploy/apptainer/.env" in DEPLOY_ALL and "hwax_fp .env api_server/.env" not in DEPLOY_ALL, "AIDH 의 실제 설정 파일(2라운드) — api_server/.env 는 boot.sh 가 기동 때 다시 쓴다"
    assert "_fp0" not in DEPLOY_ALL, "블록 진입 시점 기준은 버렸다"
    assert "infra/.state/" in (ROOT / ".gitignore").read_text(encoding="utf-8")


def test_images_from_drive_syncs_a_persistent_cache_and_fails_loudly():
    assert '"$RCLONE" sync --progress "$SRC/" "$STAGE/"' in IMAGES and 'STAGE="${HWAX_DRIVE_CACHE:-$APPT_DIR/.drive-cache}"' in IMAGES and "mktemp -d" not in IMAGES
    assert 'case $_rc in 0) echo "  ✓ staged $_f' in IMAGES and "설치 실패 — 위 사유\"; exit 1" in IMAGES
    assert '[ -f "$REPO_ROOT/frontend/dist/index.html" ] && [ -f "$APPT_DIR/.frontend-dist.applied.tar.gz" ]' in IMAGES, "dist 가 지워졌으면 같은 tar 라도 다시 푼다"


# ── services.py fp · port ────────────────────────────────────────────────────────
def _services_mod():
    spec = importlib.util.spec_from_file_location("hwax_services", ROOT / "infra/scripts/services.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def test_services_fp_tracks_head_env_and_identity_files_and_does_not_break_on_non_git(tmp_path):
    origin = tmp_path / "origin"; origin.mkdir(); _git("init", "-q", "-b", "main", cwd=origin)
    (origin / "f").write_text("1\n"); _git("add", ".", cwd=origin); _git("commit", "-qm", "A", cwd=origin)
    work = tmp_path / "work"; _git("clone", "-q", str(origin), str(work), cwd=tmp_path)
    m = _services_mod(); svc = {"name": "x", "dir": str(work), "data": {"identity": ["gateway_config.json", "gateway_config.json.bak*"]}}
    a = m.service_fp(svc); assert len(a) == 16
    (work / ".env").write_text("K=1\n"); b = m.service_fp(svc); assert b != a
    (work / "gateway_config.json").write_text("{}"); c = m.service_fp(svc); assert c not in (a, b), "매니페스트 identity 파일(게이트웨이는 .env 가 없다 — 2라운드)"
    (work / "gateway_config.json.bak1").write_text("{}"); assert m.service_fp(svc) == c, "글롭 항목(백업)은 지문에 넣지 않는다"
    (origin / "f").write_text("2\n"); _git("commit", "-qam", "B", cwd=origin); _git("fetch", "-q", "origin", cwd=work); _git("reset", "-q", "--hard", "origin/main", cwd=work)
    assert m.service_fp(svc) not in (a, b, c), "블록 밖에서 옮겨진 HEAD 도 지문에 든다"
    plain = tmp_path / "plain"; plain.mkdir(); assert len(m.service_fp({"name": "y", "dir": str(plain)})) == 16
    assert m.service_fp({"name": "z", "dir": str(tmp_path / "nope")}) == m.service_fp({"name": "z", "dir": str(tmp_path / "nope")})


def test_services_port_prints_the_health_port_from_the_real_manifest():
    r = subprocess.run(["python3", str(ROOT / "infra/scripts/services.py"), "port", "mcp-gateway"], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0 and r.stdout.strip() == "9110", r.stdout + r.stderr
    r = subprocess.run(["python3", str(ROOT / "infra/scripts/services.py"), "port", "mcp-gateway", "agent-server"], capture_output=True, text=True, timeout=30)
    assert sorted(r.stdout.split()) == sorted(["mcp-gateway", "9110", "agent-server", "9009"]), r.stdout
    assert subprocess.run(["python3", str(ROOT / "infra/scripts/services.py"), "port", "no-such-service"], capture_output=True, text=True, timeout=30).returncode == 1


# ── update-sites — 마지막 기동 지문·살아 있음·강제 아님이면 down/up 생략, 기록은 새 프로세스가 답할 때만 ───────────
def _restart_svc_block() -> str:
    i = UPDATE_SITES.index('SKIPPED_RESTART=""'); j = UPDATE_SITES.index("# 1) 포털 먼저", i)
    return UPDATE_SITES[i:j]


def _sites_harness(tmp_path, srv):
    port, pf = srv
    log = tmp_path / "svc.log"; st = tmp_path / "state"; st.mkdir(exist_ok=True)
    svc = tmp_path / "svc.sh"
    svc.write_text(f'#!/usr/bin/env bash\n. "{LIB}"\n{SRV_TOOLS}\necho "$*" >> "{log}"\n'
                   f'case "$1" in update) echo "$STUB_UPDATE";; fp) echo "$STUB_FP";; status) echo "  $STUB_STATUS x";; port) echo {port};;\n'
                   f'  down) [ "${{STUB_DOWN_NOOP:-0}}" = 1 ] || _srv_stop "{pf}";;\n'
                   f'  up) [ "${{STUB_UP_NOOP:-0}}" = 1 ] || hwax_alive http://127.0.0.1:{port}/ || _srv_start {port} "{pf}";; esac\nexit 0\n'); svc.chmod(0o755)
    def run(fp, status, update="  · x  updated: unchanged (abc1234)", env=None, running=True):
        log.unlink(missing_ok=True)
        pre = f'{SRV_TOOLS}\n' + (f'hwax_alive http://127.0.0.1:{port}/ || _srv_start {port} "{pf}" || exit 9' if running else f'_srv_stop "{pf}"')
        script = f'SVC="{svc}"\n. "{LIB}"\nexport HWAX_RESTART_STATE_DIR="{st}" HWAX_WAIT_DOWN_MAX=3\n{pre}\nshow_cause() {{ :; }}\n{_restart_svc_block()}\nrestart_svc x; echo "rc=$?"; echo "SKIPPED=[$SKIPPED_RESTART]"'
        e = {"PATH": os.environ["PATH"], "HOME": str(tmp_path), "STUB_FP": fp, "STUB_STATUS": status, "STUB_UPDATE": update, **(env or {})}
        r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=90, env=e)
        return r.stdout + r.stderr, (log.read_text().splitlines() if log.exists() else []), ((st / "x").read_text().strip() if (st / "x").exists() else None)
    return run


@pytest.fixture
def sites(tmp_path, srv):
    yield _sites_harness(tmp_path, srv)
    _kill_all(srv[1])


def test_update_sites_uses_the_last_start_fingerprint_and_records_only_a_real_restart(sites):
    out, calls, state = sites("f1", "✓ up")
    assert calls == ["update x", "fp x", "port x", "down x", "up x"] and state == "f1", ("처음(기록 없음)은 재기동하고 기록한다", out, calls)
    out, calls, state = sites("f1", "✓ up")
    assert "재기동 생략" in out and calls == ["update x", "fp x", "status x"] and "SKIPPED=[ x]" in out, (out, calls)
    out, calls, state = sites("f2", "✓ up")
    assert calls == ["update x", "fp x", "port x", "down x", "up x"] and state == "f2", "지문이 달라졌으면(코드·.env — §2 가 미리 당겼어도) 재기동"
    out, calls, state = sites("f2", "✗ down", running=False)
    assert calls == ["update x", "fp x", "status x", "port x", "down x", "up x"] and "rc=0" in out and state == "f2", ("죽어 있으면 띄운다", out)
    out, calls, _ = sites("f2", "✓ up", env={"HWAX_FORCE_RESTART": "agent-server x"})
    assert calls == ["update x", "fp x", "port x", "down x", "up x"], "강제 목록"
    out, calls, _ = sites("f2", "✓ up", env={"HWAX_RESTART_ALL": "1"})
    assert calls == ["update x", "fp x", "port x", "down x", "up x"], "HWAX_RESTART_ALL=1 은 종전 동작"
    out, calls, _ = sites("f2", "✓ up", update="  ✗ x  FAIL: pull")
    assert "rc=1" in out and "down x" in calls and "up x" in calls, "갱신 실패는 종료코드로 올리되 기동은 한다"
    out, calls, state = sites("", "✓ up")
    assert "down x" in calls and "up x" in calls and state == "f2", "지문을 못 구하면(빈 값) 모름 → 재기동, 기록은 안 한다"


def test_update_sites_does_not_record_when_down_failed_and_up_said_already_up(sites):
    """2라운드(high, C1/C6): down 이 안 됐는데 up 이 'already-up' rc 0 — 옛 프로세스가 도는데 새 지문이 적혀 영구 생략됐다."""
    out, calls, state = sites("f1", "✓ up"); assert state == "f1"
    out, calls, state = sites("f2", "✓ up", env={"STUB_DOWN_NOOP": "1", "STUB_UP_NOOP": "1"})
    assert "rc=1" in out and "재기동이 되지 않았다" in out and state == "f1", (out, calls)
    out, calls, state = sites("f2", "✓ up")
    assert "rc=0" in out and state == "f2", "다음 정상 실행이 재기동하고 그때 기록한다"


def test_update_sites_keeps_its_state_apart_from_deploy_all():
    """2라운드(C4): 인자 없는 update-sites 는 portal 도 대상 — §2 와 같은 상태 파일을 다른 형식의 지문으로 번갈아 덮으면 핑퐁 재기동."""
    assert 'HWAX_RESTART_STATE_DIR="${HWAX_RESTART_STATE_DIR:-$ROOT/infra/.state/restart-fp/sites}"' in UPDATE_SITES
    assert '"$SVC" port "$name"' in UPDATE_SITES and "hwax_listener_ids" in UPDATE_SITES and "hwax_wait_down" in UPDATE_SITES


def test_update_all_no_longer_hand_wires_the_env_window():
    assert "_ae0" not in UPDATE_ALL and "_ae1" not in UPDATE_ALL, "§3.5 전/후 창은 §1c·운영자 편집을 못 봤다 — 상태 기준으로 대체"
