# update-all 이 바뀌지 않은 서비스를 받지도 재기동하지도 않는지 — 기준은 '마지막으로 띄운 시점의 지문', 기록은 '모든 리스너가 새 프로세스로 답한 뒤에만'(docs/update-all-skip-unchanged, 2026-09-27~28)
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
FAST = {"HWAX_WAIT_DOWN_MAX": "3", "HWAX_WAIT_UP_MAX": "2"}   # 시험용 대기 상한(실물 20초/10초)


def _sh(script: str, **env) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", "-c", f'. "{LIB}"\n{script}'], capture_output=True, text=True, timeout=120,
                          env={"PATH": os.environ["PATH"], "HOME": os.environ.get("HOME", "/tmp"), **env})


def _git(*a, cwd):
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True, check=True,
                          env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x"})


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0)); return s.getsockname()[1]


# 실제 HTTP 리스너(python) — hwax_alive·hwax_wait_down/up·hwax_listener_ids 를 진짜 curl·ss 로 태운다.
# '같은 프로세스가 답한다' 를 재현하려면 pid 가 실제로 있어야 한다(/proc/<pid>/stat 을 읽는다). 백그라운드는 stdout 을 물면
# subprocess 가 끝나지 않으니 전부 /dev/null 로 돌린다.
SRV_TOOLS = r'''
_srv_start() {  # $1=port $2=pidfile — 루트(/)가 200 인 서버, 떠서 답할 때까지(최대 5초) 기다린다
  ( cd "$(dirname "$2")" && exec python3 -m http.server "$1" --bind 127.0.0.1 ) >/dev/null 2>&1 </dev/null &
  echo $! > "$2"; echo $! >> "$2.all"
  local i; for i in $(seq 1 50); do hwax_alive "http://127.0.0.1:$1/" && return 0; sleep 0.1; done; return 1
}
_srv_start_health() { _srv_start_code "$1" "$2" 200; }   # /health 만 200, 나머지는 404 (agent-server·signalforge 꼴)
_srv_start_code() {  # $1=port $2=pidfile $3=/health 가 낼 코드(401·406 등 MCP 루트가 실제로 내는 것)
  python3 - "$1" "$3" >/dev/null 2>&1 </dev/null <<'PY' &
import http.server, sys
CODE = int(sys.argv[2])
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(CODE if self.path == "/health" else 404); self.end_headers()
    def log_message(self, *a): pass
http.server.HTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
PY
  echo $! > "$2"; echo $! >> "$2.all"
  local i; for i in $(seq 1 50); do curl -s -o /dev/null -m 2 "http://127.0.0.1:$1/health" && return 0; sleep 0.1; done; return 1
}
_srv_start_late() {  # $1=port $2=pidfile $3=지연(초) — start 스크립트가 바인드 전에 돌아오는 꼴(SF 프론트 up.sh). 기다리지 않고 바로 반환
  ( cd "$(dirname "$2")" && sleep "$3" && exec python3 -m http.server "$1" --bind 127.0.0.1 ) >/dev/null 2>&1 </dev/null &
  echo $! > "$2"; echo $! >> "$2.all"; return 0
}
_srv_stop() {  # $1=pidfile
  local p i; p="$(cat "$1" 2>/dev/null)"; : > "$1"; [ -n "$p" ] || return 0
  kill "$p" 2>/dev/null; for i in $(seq 1 30); do kill -0 "$p" 2>/dev/null || return 0; sleep 0.1; done; kill -9 "$p" 2>/dev/null; return 0
}
'''


def _kill_all(pidfile: Path):
    for f in (Path(str(pidfile) + ".all"), pidfile):
        if f.exists():
            for tok in f.read_text().split():
                try: os.kill(int(tok), signal.SIGKILL)
                except (ProcessLookupError, ValueError, PermissionError): pass


@pytest.fixture
def srv(tmp_path):
    pf = tmp_path / "srv.pid"; port = _free_port()
    yield port, pf
    _kill_all(pf)


@pytest.fixture
def srv2(tmp_path):
    a = (_free_port(), tmp_path / "a.pid"); b = (_free_port(), tmp_path / "b.pid")
    yield a, b
    _kill_all(a[1]); _kill_all(b[1])


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


def test_alive_accepts_the_codes_mcp_roots_return(tmp_path, srv):
    """4라운드: 401·405·406 을 '살아 있다' 로 보는 규칙이 한 번도 검증되지 않았다. 줄이면 koorm :8701/mcp(406)·signalforge-mcp(401)·
    reportarchive-mcp(406) 가 매 회 '죽었다 → 기동' 이 되고, 사이클의 dead 갈래가 정상 기동을 ✗ rc 1 로 만든다(D-9 ③ 이 고친 결함의 재발)."""
    port, pf = srv
    for code, alive in ((200, True), (401, True), (405, True), (406, True), (404, False), (500, False)):
        r = _sh(f'{SRV_TOOLS}\n_srv_stop "{pf}"; _srv_start_code {port} "{pf}" {code} || exit 9\n'
                f'hwax_alive http://127.0.0.1:{port}/health; echo "code={code} rc=$?"')
        assert f"rc={0 if alive else 1}" in r.stdout, (code, r.stdout, r.stderr)
    _kill_all(pf)


def test_wait_up_returns_when_all_urls_answer(tmp_path, srv):
    port, pf = srv
    r = _sh(f'{SRV_TOOLS}\n_srv_start_late {port} "{pf}" 0.5; t0=$SECONDS; hwax_wait_up http://127.0.0.1:{port}/; echo "rc=$? dt=$((SECONDS-t0))"', HWAX_WAIT_UP_MAX="5")
    assert "rc=0" in r.stdout and int(r.stdout.split("dt=")[1]) <= 2, r.stdout
    r = _sh(f'hwax_wait_up http://127.0.0.1:{_free_port()}/; echo rc=$?', HWAX_WAIT_UP_MAX="1")
    assert "rc=1" in r.stdout, "아무도 안 들으면 상한 뒤 1"


# ── 재기동 사이클 — 모든 리스너가 새 프로세스로 답할 때만 기록한다 ─────────────────────────────────
def _cycle(tmp_path, srv, body: str, cur="f1", state=None, env=None, running=True, path="/", name="svc"):
    port, pf = srv
    st = tmp_path / "state"; st.mkdir(exist_ok=True)
    (st / name).unlink(missing_ok=True)
    if state is not None: (st / name).write_text(state + "\n")
    pre = f'_srv_stop "{pf}"' + (f'\n_srv_start {port} "{pf}" || exit 9' if running else "")
    t0 = time.time()
    r = _sh(f'{SRV_TOOLS}\nPORT={port}; PF="{pf}"; URL=http://127.0.0.1:{port}{path}\n{pre}\n{body}\n'
            f'hwax_restart_cycle {name} "{cur}" _stop _start "$URL"; echo "rc=$? R=$HWAX_RESTARTED"',
            HWAX_RESTART_STATE_DIR=str(st), **{**FAST, **(env or {})})
    recorded = (st / name).read_text().strip() if (st / name).exists() else None
    return r.stdout, r.stderr, recorded, time.time() - t0


def test_cycle_restarts_and_records_when_a_new_process_answers(tmp_path, srv):
    out, err, rec, _ = _cycle(tmp_path, srv, '_stop() { _srv_stop "$PF"; }; _start() { _srv_start "$PORT" "$PF"; }')
    assert "rc=0 R=1" in out and rec == "f1", (out, err)
    pids = Path(str(srv[1]) + ".all").read_text().split(); assert len(pids) == 2 and pids[0] != pids[1], "정말 새 프로세스로 갈렸다"


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


def test_cycle_start_failure_records_nothing_even_if_a_new_process_came_up(tmp_path, srv):
    """3라운드: start 가 새 프로세스를 띄우고도 rc≠0 이면(후속 단계 실패) 무기록·rc 1 — `"$startf" || return 1` 을 지우면 이 시험이 잡는다."""
    out, err, rec, _ = _cycle(tmp_path, srv, '_stop() { _srv_stop "$PF"; }; _start() { _srv_start "$PORT" "$PF"; return 1; }', cur="f2", state="f1")
    assert "rc=1" in out and rec == "f1" and "start 가 실패했다" in err, (out, err)


def test_cycle_waits_for_a_start_that_returns_before_binding(tmp_path, srv):
    """3라운드: SF 프론트 up.sh 는 instance start 뒤 배너만 찍고 돌아온다 — 유예 없이 한 번 보면 정상 기동을 '답하지 않는다' ✗ 로 오탐했다."""
    out, err, rec, dt = _cycle(tmp_path, srv, '_stop() { _srv_stop "$PF"; }; _start() { _srv_start_late "$PORT" "$PF" 0.7; }', cur="f2", state="f1", env={"HWAX_WAIT_UP_MAX": "5"})
    assert "rc=0 R=1" in out and rec == "f2" and "✗" not in err, (out, err)


def test_cycle_records_with_a_warning_when_the_new_process_is_not_healthy_yet(tmp_path, srv):
    """새 프로세스는 떴는데 health 가 아직 안 답한다(프록시는 살고 업스트림은 부팅 중 — heax caddy 502 꼴) → 기록은 하고 ⚠. 다음 실행의 생존 검사가 다시 띄운다.
    여기서 ✗ 로 막으면 늦게 뜨는 백엔드가 매 회 재기동된다(3라운드 반박 에이전트의 판정)."""
    out, err, rec, _ = _cycle(tmp_path, srv, '_stop() { _srv_stop "$PF"; }; _start() { _srv_start "$PORT" "$PF"; }', cur="f2", state="f1", path="/nope")
    assert "rc=0 R=1" in out and rec == "f2" and "아직 답하지 않는다" in err, (out, err)


def test_cycle_does_not_record_when_the_listener_answers_but_cannot_be_identified(tmp_path, srv):
    """4라운드: 이 갈래를 타는 시험이 하나도 없어 '?→⚠ 무기록' 을 되돌리는 변이가 스위트를 통과했다. ss 가 pid 를 못 보는 박스(다른 사용자 소유·ss 없음)에서
    이 규율이 풀리면 옛 프로세스 위에 새 지문이 적혀 영구 생략이 된다 — D-9 이 high 로 고친 결함의 재발이다."""
    port, pf = srv
    shim = tmp_path / "blind"; shim.mkdir()
    (shim / "ss").write_text('#!/usr/bin/env bash\necho "LISTEN 0 128 127.0.0.1:x 0.0.0.0:*"\nexit 0\n'); (shim / "ss").chmod(0o755)   # pid 를 안 보여 준다
    st = tmp_path / "state"; st.mkdir(exist_ok=True); (st / "svc").write_text("f1\n")
    r = _sh(f'{SRV_TOOLS}\nPORT={port}; PF="{pf}"\ncommand -v ss | grep -q "{shim}" || {{ echo "셈 미적용"; exit 9; }}\n'
            f'_srv_start {port} "{pf}" || exit 9\n_stop() {{ _srv_stop "$PF"; }}; _start() {{ _srv_start "$PORT" "$PF"; }}\n'
            f'hwax_restart_cycle svc f2 _stop _start http://127.0.0.1:{port}/; echo "rc=$? R=$HWAX_RESTARTED"',
            PATH=f"{shim}:" + __import__("os").environ["PATH"], HWAX_RESTART_STATE_DIR=str(st), **FAST)
    assert "rc=0 R=0" in r.stdout and "식별하지 못한다" in r.stderr and (st / "svc").read_text().strip() == "f1", (r.stdout, r.stderr)


def test_cycle_token_pairing_is_not_disturbed_by_files_in_the_cwd(tmp_path, srv2):
    """5라운드(low, latent): `$id0` 를 인용 없이 펼치면 `<포트>:?` 의 `?` 가 글롭이라 cwd 에 같은 이름의 파일이 여럿이면 토큰이
    늘어나 url↔토큰 짝이 밀린다. 그러면 죽은 url 이 '같은 프로세스' 로, 갈린 url 이 '안 갈렸다' 로 읽힌다."""
    (pa, pfa), (pb, pfb) = srv2
    st = tmp_path / "state"; st.mkdir(exist_ok=True); (st / "svc").write_text("f1\n")
    cwd = tmp_path / "cwd"; cwd.mkdir()
    for suffix in ("x", "y"):                      # `<죽은 포트>:?` 가 이 둘로 펼쳐지면 토큰이 밀린다
        (cwd / f"{pa}:{suffix}").write_text("")
    r = _sh(f'{SRV_TOOLS}\ncd "{cwd}"\n_srv_start {pb} "{pfb}" || exit 9\n'   # A 는 죽어 있고 B 만 산다
            f'_stop() {{ _srv_stop "{pfb}"; }}; _start() {{ _srv_start {pb} "{pfb}"; }}\n'
            f'hwax_restart_cycle svc f2 _stop _start http://127.0.0.1:{pa}/ http://127.0.0.1:{pb}/; echo "rc=$?"',
            HWAX_RESTART_STATE_DIR=str(st), **FAST)
    out = r.stdout + r.stderr
    assert "rc=1" in out and f"답하지 않는다(리스너 없음): http://127.0.0.1:{pa}/" in out, ("죽은 url 은 dead 로 읽혀야 한다", out)
    assert "같은 프로세스가 답한다" not in out, ("글롭으로 토큰이 밀리면 이 문구가 나온다", out)
    assert (st / "svc").read_text().strip() == "f1"


def _cycle2(tmp_path, srv2, stop_body: str, start_body: str, cur="f2", state="f1", env=None):
    (pa, pfa), (pb, pfb) = srv2
    st = tmp_path / "state"; st.mkdir(exist_ok=True); (st / "svc").unlink(missing_ok=True)
    if state is not None: (st / "svc").write_text(state + "\n")
    r = _sh(f'{SRV_TOOLS}\nPA={pa}; PFA="{pfa}"; PB={pb}; PFB="{pfb}"\n_srv_stop "$PFA"; _srv_stop "$PFB"; _srv_start $PA "$PFA" || exit 9; _srv_start $PB "$PFB" || exit 9\n'
            f'a0=$(cat "$PFA"); b0=$(cat "$PFB")\n_stop() {{ {stop_body}; }}\n_start() {{ {start_body}; }}\n'
            f'hwax_restart_cycle svc "{cur}" _stop _start http://127.0.0.1:$PA/ http://127.0.0.1:$PB/; echo "rc=$? R=$HWAX_RESTARTED a=$([ "$(cat "$PFA")" = "$a0" ] && echo same || echo new) b=$([ "$(cat "$PFB")" = "$b0" ] && echo same || echo new)"',
            HWAX_RESTART_STATE_DIR=str(st), **{**FAST, **(env or {})})
    return r.stdout, r.stderr, ((st / "svc").read_text().strip() if (st / "svc").exists() else None)


def test_cycle_with_two_listeners_records_only_when_both_are_replaced(tmp_path, srv2):
    """3라운드(high): 식별자 문자열 전체를 한 번에 비교해 둘 중 하나만 갈려도 기록됐다 — 정지에 실패한 인스턴스(포털 :8723/:8088, mxwp, sf, koorm)가
    옛 코드로 영구 생략될 판. url 마다 비교해 하나라도 같으면 ✗ 무기록."""
    (pa, _), (pb, _) = srv2
    out, err, rec = _cycle2(tmp_path, srv2, '_srv_stop "$PFB"', 'hwax_alive http://127.0.0.1:$PB/ || _srv_start $PB "$PFB"')   # A 는 못 내리고 B 만 갈린다
    assert "rc=1 R=0 a=same b=new" in out and rec == "f1" and f"같은 프로세스가 답한다: http://127.0.0.1:{pa}/" in err, (out, err)
    out, err, rec = _cycle2(tmp_path, srv2, '_srv_stop "$PFA"; _srv_stop "$PFB"', '_srv_start $PA "$PFA"; _srv_start $PB "$PFB"')
    assert "rc=0 R=1 a=new b=new" in out and rec == "f2", (out, err)
    out, err, rec = _cycle2(tmp_path, srv2, '_srv_stop "$PFB"', 'hwax_alive http://127.0.0.1:$PB/ || _srv_start $PB "$PFB"', env={"RESTART": "1"})
    assert "rc=0 R=0" in out and rec == "f1" and "NO_RESTART=1" in out, "NO_RESTART 는 · 무기록"


# ── deploy-all 포털 블록 — 실 git 리포 + 스텁으로 통째로 돈다 ─────────────────────────────
def _portal_block() -> str:
    end = 'skip "portal failed (see above)" ;; esac\n'
    i = DEPLOY_ALL.index('  _prc=0\n  ( cd "$PORTAL_DIR"\n    git_update'); j = DEPLOY_ALL.index(end, i) + len(end)
    return DEPLOY_ALL[i:j]


def _delib_hold_fn() -> str:
    """포털·nginx 구획이 내리기 전에 부르는 물음(도는 심의가 있으면 미룬다)과 그것이 쓰는 lib 둘 — 구획을 떼어 돌리는 하네스는 이것도
    함께 가져와야 한다. 여기 하네스들은 curl 이 대역이라 에이전트 서버의 답이 '모름' 이고, 모름은 미루지 않는다(종전 동작 그대로).
    미루는 쪽은 test_update_all_delib_restart_gate 가 본다."""
    i = DEPLOY_ALL.index("_delib_hold() {")
    return f'. "{LIB.parent}/skip-ledger.sh"\n. "{LIB.parent}/delib-busy.sh"\n' + DEPLOY_ALL[i:DEPLOY_ALL.index("\n}\n", i) + 3]


def _port_shims(shim: Path, lst: Path):
    """ss·curl 을 **포트별** 리스너 파일로 흉내 낸다 — 리스너는 진짜 프로세스(sleep) 의 pid. 포트를 무시하면 '둘 중 하나만 갈림' 을 원리적으로 못 본다(3라운드)."""
    shim.mkdir(exist_ok=True)
    (shim / "curl").write_text('#!/usr/bin/env bash\nu="${@: -1}"; p="$(printf %s "$u" | sed -n "s#.*://[^:/]*:\\([0-9]*\\).*#\\1#p")"; p="${p:-80}"\n'
                               f'f="{lst}.$p"; q="$(cat "$f" 2>/dev/null)"; if [ -n "$q" ] && kill -0 "$q" 2>/dev/null; then printf 200; else printf 000; fi\n'); (shim / "curl").chmod(0o755)
    (shim / "ss").write_text('#!/usr/bin/env bash\nlast="${@: -1}"; p="${last##*:}"\n'
                             f'q="$(cat "{lst}.$p" 2>/dev/null)"; [ -n "$q" ] && kill -0 "$q" 2>/dev/null && echo "LISTEN 0 128 127.0.0.1:$p 0.0.0.0:* users:((\\"x\\",pid=$q,fd=3))"; exit 0\n'); (shim / "ss").chmod(0o755)


def _listener_stub_lines(lst: Path, sleeps: Path, ports: tuple, stop_ports=None) -> tuple:
    start = "".join(f'q="$(cat "{lst}.{p}" 2>/dev/null)"; if [ -n "$q" ] && kill -0 "$q" 2>/dev/null; then echo "already running :{p}"; else '
                    f'sleep 300 >/dev/null 2>&1 </dev/null & echo $! > "{lst}.{p}"; echo $! >> "{sleeps}.all"; fi\n' for p in ports)   # 파이프를 물지 않게(안 그러면 하네스가 매달린다)
    stop = "".join(f'q="$(cat "{lst}.{p}" 2>/dev/null)"; [ -n "$q" ] && kill "$q" 2>/dev/null; : > "{lst}.{p}"\n' for p in (stop_ports if stop_ports is not None else ports))
    return start, stop


def _portal_harness(tmp_path):
    """블록의 url 은 :8723/:8088 로 박혀 있어(dev 에는 진짜 포털이 듣는다) ss·curl 을 포트별 셈으로 바꾼다. start.sh 스텁은 실물처럼 '이미 떠 있으면 새로 띄우지 않고 rc 0'.
    ⚠ 하네스의 모든 경로는 절대경로다 — 블록 안 `cd "$PORTAL_DIR"` 뒤 상대경로 셈이 풀려 실 apptainer 를 부른 사고가 있었다(3라운드 검토 에이전트, dev nginx 를 내렸다)."""
    origin = tmp_path / "origin"; origin.mkdir(); _git("init", "-q", "-b", "main", cwd=origin)
    (origin / "backend/app").mkdir(parents=True); (origin / "backend/app/main.py").write_text("VERSION=1\n")
    (origin / ".gitignore").write_text("infra/.env\nbackend/.env\nbackend/config/routes.local.env\ninfra/apptainer/\nfrontend/dist/\ninfra/.state/\n")
    _git("add", ".", cwd=origin); _git("commit", "-qm", "A", cwd=origin)
    repo = tmp_path / "portal"; _git("clone", "-q", str(origin), str(repo), cwd=tmp_path)
    (repo / "infra/scripts").mkdir(parents=True); (repo / "infra/apptainer").mkdir(); (repo / "frontend/dist").mkdir(parents=True); (repo / "backend/config").mkdir(parents=True)
    (repo / "infra/.env").write_text("HTTP_PORT=8088\n"); (repo / "backend/.env").write_text("RA_BASE_URL=http://127.0.0.1:3000\n"); (repo / "infra/apptainer/portal.sif").write_bytes(b"sif"); (repo / "frontend/dist/index.html").write_text("x")
    calls = tmp_path / "calls.log"; lst = tmp_path / "listener"; sleeps = tmp_path / "srv.pid"
    start_lines, stop_lines = _listener_stub_lines(lst, sleeps, (8723, 8088))
    stubs = {"images-from-drive.sh": f'echo images-from-drive.sh >> "{calls}"\n',
             "stop.sh": f'echo stop.sh >> "{calls}"\n{stop_lines}',
             "start.sh": f'echo start.sh >> "{calls}"\n{start_lines}'}
    def write_stubs(**override):
        for name, body in {**stubs, **override}.items():
            f = repo / "infra/scripts" / name; f.write_text("#!/usr/bin/env bash\n" + body); f.chmod(0o755)
    write_stubs()
    shim = tmp_path / "bin"; _port_shims(shim, lst)
    fp_git = DEPLOY_ALL[DEPLOY_ALL.index("_fp_git() {"):]; fp_git = fp_git[:fp_git.index("\n") + 1]
    _i = DEPLOY_ALL.index("_ngfp() {"); ngfp = _envv_fn() + DEPLOY_ALL[_i:DEPLOY_ALL.index("\n}\n", _i) + 3] + _delib_hold_fn()
    def run():
        script = (f'set -uo pipefail\nPORTAL_DIR="{repo}"; RESTART=0\n. "{LIB}"\nexport HWAX_RESTART_STATE_DIR="{tmp_path}/state" HWAX_RESTART_SKIPPED_FILE="{tmp_path}/skipped" HWAX_WAIT_DOWN_MAX=2 HWAX_WAIT_UP_MAX=2\n'
                  f'ok() {{ echo "OK:$*"; }}; skip() {{ echo "SKIP:$*"; }}; set_remote() {{ :; }}\n'
                  f'git_update() {{ git fetch -q origin main && git reset -q --hard origin/main; }}\n{fp_git}{ngfp}\n{_portal_block()}')
        calls.unlink(missing_ok=True)
        r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=90, env={"PATH": f"{shim}:{os.environ['PATH']}", "HOME": str(tmp_path)})
        return r.stdout + r.stderr, (calls.read_text().split() if calls.exists() else [])
    state = lambda: (tmp_path / "state/portal").read_text().strip() if (tmp_path / "state/portal").exists() else None  # noqa: E731
    return origin, repo, run, write_stubs, state, sleeps, (lst, stop_lines)


@pytest.fixture
def portal(tmp_path):
    h = _portal_harness(tmp_path)
    yield h
    _kill_all(h[5])
    for p in (8723, 8088): _kill_all(tmp_path / f"listener.{p}")


def test_portal_block_restarts_on_first_run_then_skips_then_restarts_on_code_env_or_artifact_change(portal):
    origin, repo, run, _, state, _, _ = portal
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
    (repo / "infra/apptainer/portal.sif").write_bytes(b"sif-v2")                   # images-from-drive 가 새 SIF 를 놓았다(§2 의 존재 이유 — 3라운드가 시험 공백으로 지적)
    out, calls = run(); assert "start.sh" in calls and "변경 있음" in out, "새 SIF 가 재기동을 일으킨다"
    (repo / "frontend/dist/index.html").write_text("y")
    out, calls = run(); assert "start.sh" in calls, "새 dist 가 재기동을 일으킨다"
    out, calls = run(); assert calls == ["images-from-drive.sh"]


def test_portal_block_does_not_record_a_start_that_failed(portal):
    _, repo, run, write_stubs, state, _, _ = portal
    write_stubs(**{"start.sh": 'echo start.sh >> "$(dirname "$0")/../../../calls.log"\nexit 1\n'})
    out, calls = run(); assert "SKIP:portal failed" in out and state() is None, "실패한 기동은 기준이 되지 않는다 — 다음 실행이 다시 시도한다"


def test_portal_block_does_not_record_an_already_running_old_process(portal):
    """2라운드(high): stop.sh 가 실패하면 start.sh 는 'already running' rc 0 — 옛 프로세스가 도는데 새 지문이 적혀 영구 생략됐다."""
    _, repo, run, write_stubs, state, _, _ = portal
    out, calls = run(); first = state(); assert first
    (repo / "backend/.env").write_text("K=2\n")
    write_stubs(**{"stop.sh": 'echo stop.sh >> "$(dirname "$0")/../../../calls.log"\nexit 1\n'})    # 정지가 안 된다
    out, calls = run()
    assert "SKIP:portal failed" in out and "재기동이 되지 않았다" in out and state() == first, ("옛 프로세스가 답하는데 기록하지 않는다", out)
    write_stubs()                                                                                     # 정지가 다시 된다
    out, calls = run(); assert "OK:portal up" in out and state() not in (None, first), "다음 정상 실행이 재기동하고 그때 기록한다"


def test_portal_block_does_not_record_when_only_one_of_two_instances_was_replaced(portal, tmp_path):
    """3라운드(high): stop.sh 가 hwax_nginx 만 못 내리면(instance list 파이프 거짓 음성 등) start.sh 는 포털만 새로 띄운다 — 8723 만 갈리고 8088 은 옛 nginx.
    종전엔 식별자 문자열이 달라져 기록됐고 nginx 기준 지문까지 적혔다."""
    _, repo, run, write_stubs, state, sleeps, (lst, _) = portal
    out, calls = run(); first = state(); assert first and (tmp_path / "state/nginx").exists()
    ng_first = (tmp_path / "state/nginx").read_text()
    (repo / "backend/.env").write_text("K=3\n")
    _, stop_only_portal = _listener_stub_lines(lst, sleeps, (8723, 8088), stop_ports=(8723,))
    write_stubs(**{"stop.sh": f'echo stop.sh >> "{tmp_path}/calls.log"\n{stop_only_portal}'})
    out, calls = run()
    assert "SKIP:portal failed" in out and "같은 프로세스가 답한다: http://127.0.0.1:8088/health" in out and state() == first, out
    assert (tmp_path / "state/nginx").read_text() == ng_first, "nginx 기준 지문도 그대로"
    write_stubs()
    out, calls = run(); assert "OK:portal up" in out and state() not in (None, first)


def test_portal_block_stops_at_a_failed_artifact_pull(portal):
    """`( … ) && ok || skip` 안은 set -e 가 꺼져 있다 — images-from-drive 가 실패해도 옛 SIF 로 기동하고 초록이었다."""
    _, repo, run, write_stubs, state, _, _ = portal
    write_stubs(**{"images-from-drive.sh": 'echo images-from-drive.sh >> "$(dirname "$0")/../../../calls.log"\nexit 1\n'})
    out, calls = run(); assert "SKIP:portal failed" in out and calls == ["images-from-drive.sh"] and state() is None


# ── deploy-all nginx 블록 — conf 재생성 → 지문 → 사이클, 실패는 skip 으로 집계 ─────────────────────────────
def _envv_fn() -> str:
    """deploy-all 의 .env 독자 — _ngfp·_hp·NG_PORT·SIF_DIR 넷이 같이 쓴다(5라운드). 블록 슬라이스 하네스는 이것도 함께 떼어 와야 한다."""
    i = DEPLOY_ALL.index("_envv() {"); return DEPLOY_ALL[i:DEPLOY_ALL.index("\n}\n", i) + 3]


def _nginx_block() -> str:
    i = DEPLOY_ALL.index('  NG_LOG="$(mktemp)"'); j = DEPLOY_ALL.index('  rm -f "$NG_LOG"\n', i) + len('  rm -f "$NG_LOG"\n')
    return DEPLOY_ALL[i:j]


def _nginx_harness(tmp_path):
    repo = tmp_path / "portal"; (repo / "infra/scripts").mkdir(parents=True); (repo / "infra/nginx").mkdir(); (repo / "infra/tls").mkdir()
    # HTTP_PORT 를 **인용해서** 적는다 — 포털 블록의 _hp 는 인용을 벗기는데 nginx 블록의 NG_PORT 는 안 벗겨 매 회 ✗ 였다(4라운드)
    (repo / "infra/.env").write_text('HTTP_PORT="8088"\n'); (repo / "infra/tls/hwax.crt").write_text("c"); (repo / "infra/tls/hwax.key").write_text("k")
    routes = tmp_path / "routes.txt"; routes.write_text("ste=a\n")
    calls = tmp_path / "calls.log"; lst = tmp_path / "listener"; sleeps = tmp_path / "srv.pid"
    start_lines, stop_lines = _listener_stub_lines(lst, sleeps, (8088,))
    # 실물 gen-nginx-conf 는 검증 실패 시 conf 를 **손대지 않고** exit 1 한다(쓰기는 검증 뒤다) — GEN_FAIL 이 그 모양이다
    for name, body in {"gen-nginx-conf.sh": f'echo gen >> "{calls}"\n[ "${{GEN_FAIL:-0}}" = 1 ] && {{ echo "✗ TLS 경로가 리포 밖이다"; exit 1; }}\ncp "{routes}" "{repo}/infra/nginx/hwax.conf"\n',
                       "start.sh": f'echo start.sh >> "{calls}"\n{start_lines}'}.items():
        f = repo / "infra/scripts" / name; f.write_text("#!/usr/bin/env bash\n" + body); f.chmod(0o755)
    shim = tmp_path / "bin"; _port_shims(shim, lst)
    # 블록은 PORTAL_DIR 안의 infra/apptainer/bin-* 가 없으면 PATH 의 apptainer 를 쓴다 — 여기서는 이 셈이다(절대경로).
    (shim / "apptainer").write_text(f'#!/usr/bin/env bash\necho "apptainer $*" >> "{calls}"\n[ "${{NGSTOP_NOOP:-0}}" = 1 ] && exit 0\n{stop_lines}'); (shim / "apptainer").chmod(0o755)
    _i = DEPLOY_ALL.index("_ngfp() {"); ngfp = _envv_fn() + DEPLOY_ALL[_i:DEPLOY_ALL.index("\n}\n", _i) + 3] + _delib_hold_fn()
    def run(env=None):
        script = (f'set -euo pipefail\nPORTAL_DIR="{repo}"\n. "{LIB}"\nexport HWAX_RESTART_STATE_DIR="{tmp_path}/state" HWAX_WAIT_DOWN_MAX=2 HWAX_WAIT_UP_MAX=2\n'
                  f'ok() {{ echo "OK:$*"; }}; skip() {{ echo "SKIP:$*"; }}\n{ngfp}\n{_nginx_block()}')
        calls.unlink(missing_ok=True)
        r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=90, env={"PATH": f"{shim}:{os.environ['PATH']}", "HOME": str(tmp_path), **(env or {})})
        return r.stdout + r.stderr, (calls.read_text().splitlines() if calls.exists() else []), r.returncode
    state = lambda: (tmp_path / "state/nginx").read_text().strip() if (tmp_path / "state/nginx").exists() else None  # noqa: E731
    return routes, run, state, sleeps


@pytest.fixture
def nginx(tmp_path):
    h = _nginx_harness(tmp_path)
    yield h
    _kill_all(h[3]); _kill_all(tmp_path / "listener.8088")


def test_nginx_block_bounces_on_conf_change_skips_otherwise_and_counts_a_failed_bounce(nginx):
    """3라운드(high): 사이클의 ✗(같은 프로세스가 답한다)를 `|| true` 로 삼키고 /health 200 만 보고 'reloaded' 초록 — 옛 conf 로 돌면서 exit 0 이었다."""
    routes, run, state, _ = nginx
    out, calls, rc = run(); assert rc == 0 and "OK:nginx reloaded" in out and state() and "start.sh" in calls, (out, calls)
    first = state()
    out, calls, rc = run(); assert "재기동 생략" in out and "OK:nginx reloaded" in out and not any(c.startswith("apptainer") for c in calls) and state() == first, "conf 그대로·살아 있음 → bounce 없음"
    routes.write_text("ste=b\n")                                                           # 라우트가 바뀌어 conf 가 달라진다
    out, calls, rc = run(); assert "변경 있음" in out and any("instance stop hwax_nginx" in c for c in calls) and "start.sh" in calls and state() not in (None, first), out
    second = state(); routes.write_text("ste=c\n")
    out, calls, rc = run(env={"NGSTOP_NOOP": "1"})                                         # 정지가 안 된다 → 같은 프로세스
    assert rc == 0 and "SKIP:nginx 재기동 실패" in out and "OK:nginx reloaded" not in out and state() == second, ("skip 으로 집계하고 기록하지 않는다", out)
    out, calls, rc = run(); assert "OK:nginx reloaded" in out and state() not in (None, second), "다음 정상 실행이 재기동하고 기록한다"
    third = state()
    # 4라운드: conf 생성이 실패하면 옛 conf 가 남고 그 지문은 '마지막 기동' 과 같아 사이클이 생략한다 — /health 200 만 보고 초록이었다.
    routes.write_text("ste=d\n")
    out, calls, rc = run(env={"GEN_FAIL": "1"})
    assert rc == 0 and "SKIP:nginx conf 생성 실패" in out and "TLS 경로가 리포 밖이다" in out and "OK:nginx reloaded" not in out and state() == third, ("생성 실패는 집계하고 사유를 보여 준다", out)
    assert not any("instance stop" in c for c in calls) and "start.sh" not in calls, "생성이 실패했으면 살아 있는 nginx 를 건드리지 않는다(5라운드)"
    assert "지금 /health → 200" in out, "단정하지 않고 실제로 잰 코드를 말한다"
    out, calls, rc = run(); assert "OK:nginx reloaded" in out and state() not in (None, third), "원인이 사라지면 다음 실행이 반영한다"


def test_deploy_all_wires_every_service_and_nginx_through_the_restart_cycle():
    for svc in ("portal", "mxwp", "heax", "signalforge", "kooremapper"):
        assert re.search(rf'hwax_restart_cycle {svc} "\$_cur" _stop _start [^\n]*\|\| exit 1', DEPLOY_ALL), f"{svc}: 사이클 실패는 블록을 끊어야 한다(|| exit 1)"
    assert re.search(r'hwax_restart_cycle aidh "\$_cur" : _start http://localhost:8001/ \|\| exit 1', DEPLOY_ALL), "AIDH 는 boot.sh --force 가 스스로 갈아 끼운다"
    assert 'hwax_restart_cycle nginx "$_ngcur" _stop _start' in DEPLOY_ALL and "_ngfp() {" in DEPLOY_ALL
    assert '_ngrc=0\n' in DEPLOY_ALL and ') || _ngrc=$?' in DEPLOY_ALL and 'skip "nginx 재기동 실패(rc=$_ngrc)' in DEPLOY_ALL, "nginx 사이클 rc 는 집계에 든다(3라운드)"
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


def test_deploy_all_env_reader_matches_the_canonical_rule(tmp_path):
    """4·5라운드: 한 파일 안에 .env 독자가 셋이라 `HTTP_PORT="8088"`·`'8088'`·인라인 주석에서 두 자리가 다른 값을 읽었다
    (nginx 판정이 매 회 ✗ → skip → exit 4). 일치 시험은 둘 다 틀리면 통과하므로 **정본**(update-all `_envfile_value`)을 오라클로 댄다."""
    canon = UPDATE_ALL[UPDATE_ALL.index("_envfile_value() {"):]
    canon = canon[:canon.index("\n}\n") + 3].replace("_envfile_value()", "_canon()", 1)
    cases = ['HTTP_PORT=8088', 'HTTP_PORT="8088"', "HTTP_PORT='8088'", 'HTTP_PORT=8088 # 포털', 'export HTTP_PORT=8088',
             '  HTTP_PORT= 8088 ', 'HTTP_PORT=', 'HTTP_PORT=   # 설명', 'HTTP_PORT=8088\r', '#HTTP_PORT=8088',
             'HTTP_PORT=1\nHTTP_PORT=2', 'export  HTTP_PORT="8088"  # c']
    for c in cases:
        f = tmp_path / "e.env"; f.write_text(c + "\n")
        r = subprocess.run(["bash", "-c", _envv_fn() + canon + f'printf "[%s]|[%s]" "$(_envv "{f}" HTTP_PORT)" "$(_canon "{f}" HTTP_PORT)"'],
                           capture_output=True, text=True, timeout=30)
        a, b = r.stdout.split("|")
        assert a == b, (c, a, b)
    assert DEPLOY_ALL.count("_envv ") >= 4 and "sed -n 's/^HTTP_PORT=//p'" not in DEPLOY_ALL, "네 자리(_hp·NG_PORT·_ngfp 둘·SIF_DIR)가 한 독자를 쓴다"


def test_images_from_drive_syncs_a_persistent_cache_and_fails_loudly():
    assert '"$RCLONE" sync --progress "$SRC/" "$STAGE/"' in IMAGES and 'STAGE="${HWAX_DRIVE_CACHE:-$APPT_DIR/.drive-cache}"' in IMAGES and "mktemp -d" not in IMAGES
    assert 'case $_rc in 0) echo "  ✓ staged $_f' in IMAGES and "설치 실패 — 위 사유\"; exit 1" in IMAGES
    assert '[ -f "$REPO_ROOT/frontend/dist/index.html" ] && [ -f "$APPT_DIR/.frontend-dist.applied.tar.gz" ]' in IMAGES, "dist 가 지워졌으면 같은 tar 라도 다시 푼다"


# ── services.py fp · port · health ────────────────────────────────────────────────
def _services_mod():
    spec = importlib.util.spec_from_file_location("hwax_services", ROOT / "infra/scripts/services.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def test_services_fp_tracks_head_env_and_identity_files_but_not_identity_dirs(tmp_path):
    origin = tmp_path / "origin"; origin.mkdir(); _git("init", "-q", "-b", "main", cwd=origin)
    (origin / "f").write_text("1\n"); _git("add", ".", cwd=origin); _git("commit", "-qm", "A", cwd=origin)
    work = tmp_path / "work"; _git("clone", "-q", str(origin), str(work), cwd=tmp_path)
    m = _services_mod(); svc = {"name": "x", "dir": str(work), "data": {"identity": ["gateway_config.json", "gateway_config.json.bak*", "var/integration_state"]}}
    a = m.service_fp(svc); assert len(a) == 16
    (work / ".env").write_text("K=1\n"); b = m.service_fp(svc); assert b != a
    (work / "gateway_config.json").write_text("{}"); c = m.service_fp(svc); assert c not in (a, b), "매니페스트 identity 파일(게이트웨이는 .env 가 없다 — 2라운드)"
    (work / "gateway_config.json.bak1").write_text("{}"); assert m.service_fp(svc) == c, "글롭 항목(백업)은 지문에 넣지 않는다"
    (work / "var/integration_state").mkdir(parents=True); (work / "var/integration_state/s.json").write_text("{}")
    assert m.service_fp(svc) == c, "identity 의 디렉터리(런타임 상태 — heax integration_state 는 45초마다 다시 쓴다)는 지문에 넣지 않는다(3라운드)"
    (work / "conf.d").mkdir(); (work / "conf.d/a.conf").write_text("a")
    d = m.service_fp({**svc, "fp": ["conf.d"]}); assert d != c, "재기동 판정용 fp: 의 디렉터리는 든다"
    (origin / "f").write_text("2\n"); _git("commit", "-qam", "B", cwd=origin); _git("fetch", "-q", "origin", cwd=work); _git("reset", "-q", "--hard", "origin/main", cwd=work)
    assert m.service_fp(svc) not in (a, b, c), "블록 밖에서 옮겨진 HEAD 도 지문에 든다"
    plain = tmp_path / "plain"; plain.mkdir(); assert len(m.service_fp({"name": "y", "dir": str(plain)})) == 16
    assert m.service_fp({"name": "z", "dir": str(tmp_path / "nope")}) == m.service_fp({"name": "z", "dir": str(tmp_path / "nope")})


def test_service_urls_lists_every_listener_and_expands_env_refs():
    """5라운드(high): 인스턴스가 둘인 서비스에서 한쪽만 갈려도 기록돼 영구 생략됐다. 매니페스트가 듣는 url 전부를 들고,
    박스마다 다른 값(포털 nginx 포트)은 `${KEY:-기본}` 으로 infra/.env 에서 푼다."""
    m = _services_mod()
    by = {s["name"]: s for s in m.load()}
    for name, n in (("portal", 2), ("mx-white-paper", 2), ("signalforge", 2), ("kooremapper", 2), ("agent-server", 1)):
        urls = m.service_urls(by[name])
        assert len(urls) == n, (name, urls)
        assert all(u and "${" not in u for u in urls), (name, urls)
    assert m.service_urls(by["kooremapper"])[1].endswith("/mcp"), "MCP 루트는 404 라 /mcp 를 본다"
    assert m.service_urls({"health": "http://h:1/a", "urls": ["http://h:${NO_SUCH_KEY_X:-9}/b", "http://h:1/a"]}) == \
        ["http://h:1/a", "http://h:9/b"], "기본값을 쓰고 중복은 하나로"


def test_services_port_and_health_print_from_the_real_manifest():
    py = ["python3", str(ROOT / "infra/scripts/services.py")]
    r = subprocess.run([*py, "port", "mcp-gateway"], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0 and r.stdout.strip() == "9110", r.stdout + r.stderr
    r = subprocess.run([*py, "port", "mcp-gateway", "agent-server"], capture_output=True, text=True, timeout=30)
    assert sorted(r.stdout.split()) == sorted(["mcp-gateway", "9110", "agent-server", "9009"]), r.stdout
    r = subprocess.run([*py, "health", "agent-server"], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0 and r.stdout.strip() == "http://localhost:9009/health", "생존·내려감 대기는 health 경로로(루트는 404 — 3라운드)"
    r = subprocess.run([*py, "health", "portal"], capture_output=True, text=True, timeout=30)
    assert r.stdout.split() == ["http://127.0.0.1:8723/health", "http://127.0.0.1:8088/health"], ("듣는 url 전부, 순서대로", r.stdout)
    r = subprocess.run([*py, "port", "portal"], capture_output=True, text=True, timeout=30)
    assert r.stdout.split() == ["8723", "8088"], ("포트도 같은 순서 — 어긋나면 url↔리스너 짝이 밀린다", r.stdout)
    assert subprocess.run([*py, "port", "no-such-service"], capture_output=True, text=True, timeout=30).returncode == 1


# ── update-sites — 마지막 기동 지문·살아 있음·강제 아님이면 down/up 생략, 기록은 새 프로세스가 답할 때만 ───────────
def _restart_svc_block() -> str:
    i = UPDATE_SITES.index('SKIPPED_RESTART=""'); j = UPDATE_SITES.index("# 1) 포털 먼저", i)
    return UPDATE_SITES[i:j]


def _sites_harness(tmp_path, srv):
    """리스너는 /health 만 200 인 진짜 서버(agent-server 꼴) — 포트 루트를 두드리면 살아 있어도 '죽었다' 로 읽히는 차이를 본다(3라운드)."""
    port, pf = srv
    log = tmp_path / "svc.log"; st = tmp_path / "state"; st.mkdir(exist_ok=True)
    svc = tmp_path / "svc.sh"
    svc.write_text(f'#!/usr/bin/env bash\n. "{LIB}"\n{SRV_TOOLS}\necho "$*" >> "{log}"\n'
                   f'case "$1" in update) printf "%b\\n" "$STUB_UPDATE";; fp) echo "$STUB_FP";; status) echo "  $STUB_STATUS x";;\n'
                   f'  port) [ "${{STUB_NO_HEALTH:-0}}" = 1 ] || echo {port};;\n'
                   f'  health) [ "${{STUB_NO_HEALTH:-0}}" = 1 ] || echo http://127.0.0.1:{port}/health;;\n'
                   f'  enabled) exit "${{STUB_ENABLED_RC:-0}}";;\n'
                   f'  down) [ "${{STUB_DOWN_NOOP:-0}}" = 1 ] || _srv_stop "{pf}";;\n'
                   f'  up) [ "${{STUB_UP_NOOP:-0}}" = 1 ] || hwax_alive http://127.0.0.1:{port}/health || _srv_start_health {port} "{pf}";; esac\nexit 0\n'); svc.chmod(0o755)
    def run(fp, status, update="  · x  updated: unchanged (abc1234)", env=None, running=True, name="x", show_cause=False):
        log.unlink(missing_ok=True)
        pre = f'{SRV_TOOLS}\n' + (f'hwax_alive http://127.0.0.1:{port}/health || _srv_start_health {port} "{pf}" || exit 9' if running else f'_srv_stop "{pf}"')
        sc = 'show_cause() { echo "CAUSE:$2"; }' if show_cause else 'show_cause() { :; }'
        script = f'SVC="{svc}"\n. "{LIB}"\nexport HWAX_RESTART_STATE_DIR="{st}" HWAX_WAIT_DOWN_MAX=2\n{pre}\n{sc}\n{_restart_svc_block()}\nrestart_svc "{name}"; echo "rc=$?"; echo "SKIPPED=[$SKIPPED_RESTART]"'
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
    assert calls == ["enabled x", "update x", "fp x", "health x", "down x", "up x"] and state == "f1", ("처음(기록 없음)은 재기동하고 기록한다", out, calls)
    out, calls, state = sites("f1", "✓ up")
    assert "재기동 생략" in out and calls == ["enabled x", "update x", "fp x", "status x"] and "SKIPPED=[ x]" in out and "rc=0" in out, (out, calls)
    out, calls, state = sites("f2", "✓ up")
    assert "down x" in calls and "up x" in calls and state == "f2" and "정지 뒤에도" not in out, "지문이 달라졌으면 재기동 — /health 로 내려감을 봐 진단 오탐이 없다"
    out, calls, state = sites("f2", "✗ down", running=False)
    assert calls == ["enabled x", "update x", "fp x", "status x", "health x", "down x", "up x"] and "rc=0" in out and state == "f2", ("죽어 있으면 띄운다", out)
    out, calls, _ = sites("f2", "✓ up", env={"HWAX_FORCE_RESTART": "agent-server x"})
    assert "down x" in calls and "up x" in calls, "강제 목록"
    out, calls, _ = sites("f2", "✓ up", env={"HWAX_RESTART_ALL": "1"})
    assert "down x" in calls and "up x" in calls, "HWAX_RESTART_ALL=1 은 종전 동작"
    out, calls, state = sites("", "✓ up")
    assert "down x" in calls and "up x" in calls and state == "f2", "지문을 못 구하면(빈 값) 모름 → 재기동, 기록은 안 한다"


def test_update_sites_pull_failure_raises_rc_but_does_not_bounce_an_unchanged_live_service(sites):
    """3라운드: GitHub 이 며칠 안 닿으면 update-all 마다 챗 스택 셋이 같은 옛 코드로 내려갔다 올라왔다(진행 중 SSE 절단). 실패는 rc 로만."""
    out, calls, state = sites("f1", "✓ up"); assert state == "f1"
    out, calls, state = sites("f1", "✓ up", update="  ✗ x  FAIL: pull")
    assert "rc=2" in out and "down x" not in calls and "up x" not in calls and "갱신(git pull) 은 실패했다" in out and "SKIPPED=[ x]" in out, (out, calls)
    out, calls, state = sites("f2", "✓ up", update="  ✗ x  FAIL: pull")
    assert "rc=2" in out and "down x" in calls and "up x" in calls and state == "f2", "지문이 다르면 재기동은 하되 rc 2(갱신만 실패) — 포털 게이트가 중단하지 않게(4라운드)"


def test_update_sites_does_not_record_when_down_failed_and_up_said_already_up(sites):
    """2라운드(high, C1/C6): down 이 안 됐는데 up 이 'already-up' rc 0 — 옛 프로세스가 도는데 새 지문이 적혀 영구 생략됐다.
    3라운드: 내려감 대기를 /health 로 하니 'down 실패' 진단도 이제 나온다(루트 404 서비스에서는 절대 안 나왔다)."""
    out, calls, state = sites("f1", "✓ up"); assert state == "f1"
    out, calls, state = sites("f2", "✓ up", env={"STUB_DOWN_NOOP": "1", "STUB_UP_NOOP": "1"})
    assert "rc=1" in out and "재기동이 되지 않았다" in out and "정지 뒤에도 답한다" in out and "/health" in out and state == "f1", (out, calls)
    out, calls, state = sites("f2", "✓ up")
    assert "rc=0" in out and state == "f2", "다음 정상 실행이 재기동하고 그때 기록한다"


def test_update_sites_fails_when_up_said_ok_but_nothing_answers(sites):
    """3라운드: `?` 갈래가 lib 와 달리 생존을 안 봐 up rc 0 뒤 아무도 안 들어도 '✓ 완료' rc 0 이었다."""
    out, calls, state = sites("f2", "✗ down", running=False, env={"STUB_UP_NOOP": "1"})
    assert "rc=1" in out and "답하지 않는다(리스너 없음)" in out and state is None, (out, calls)


def test_update_sites_refuses_a_name_that_is_not_in_the_manifest(sites):
    """4라운드: 없는 이름을 주면 update·up 이 조용히 아무것도 안 하고 fp 가 빈 값이라 검증 블록을 건너뛴 뒤 '✓ 완료' · exit 0 이었다."""
    out, calls, state = sites("", "✓ up", env={"STUB_ENABLED_RC": "2"})
    assert "rc=1" in out and "services.yaml 에 없는 서비스" in out and calls == ["enabled x"] and "완료" not in out and state is None, (out, calls)


def test_update_sites_does_not_fail_a_service_that_has_no_health_url(sites):
    """4라운드: health 없는 서비스(services.py 는 'started (no health url)' 로 정상 지원)를 포트 0 루트로 두드려 매 회 ✗ rc 1 이었다 → 판정 불가면 ⚠."""
    out, calls, state = sites("f1", "? no-health", env={"STUB_NO_HEALTH": "1"})
    assert "rc=0" in out and "health url 이 없어 재기동을 확인할 수 없다" in out and "답하지 않는다" not in out and state is None, (out, calls)


def test_update_sites_skips_a_service_this_box_does_not_own(sites):
    """5라운드: 이 박스 대상이 아닌 서비스(only_on)를 down/up 태우고 내려감 대기 20초를 쓴 뒤 '같은 프로세스가 답한다' 오탐 ✗ 로
    실행 전체를 실패로 만들었다. `?` 갈래는 이미 면제하고 있었는데 `*)` 갈래가 그 조건을 안 봤다(같은 파일 안의 규율 불일치)."""
    out, calls, state = sites("f1", "✓ up", env={"STUB_ENABLED_RC": "1"})
    assert "rc=0" in out and "이 박스 대상 아님" in out and calls == ["enabled x"] and state is None, (out, calls)


def test_update_sites_refuses_a_flag_as_a_service_name(sites):
    """5라운드(high→medium): services.py 는 `-` 로 시작하는 인자를 이름 목록에서 걸러 '이름 없음 = 전부' 로 읽는다. 그래서
    `update-sites.sh --force` 가 14개 서비스를 통째로 update·down·up 했다(제외 약속된 report-archive 포함)."""
    out, calls, state = sites("f1", "✓ up", name="--force")
    assert "rc=1" in out and "서비스명이 아니다" in out and calls == [], (out, calls)


def test_update_sites_rejects_an_unknown_flag_before_doing_anything():
    """같은 뿌리의 다른 쪽 — 인식 못 한 플래그가 `TARGETS="$*"` 로 들어가지 못하게 한다."""
    r = subprocess.run(["bash", str(ROOT / "infra/scripts/update-sites.sh"), "--force"], capture_output=True, text=True, timeout=60)
    assert r.returncode == 2 and "알 수 없는 옵션" in (r.stdout + r.stderr), (r.returncode, r.stdout + r.stderr)
    r = subprocess.run(["bash", str(ROOT / "infra/scripts/update-sites.sh"), "--help"], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0 and "사용법" in r.stdout, "--help 는 그대로 동작한다"


def test_update_sites_sees_a_pull_failure_that_is_not_on_the_last_line(sites):
    """5라운드: `tail -1` 만 봐서 여러 줄이 나오면 첫 줄의 ✗ 가 밀려 갱신 실패가 통째로 삼켜졌다."""
    out, calls, state = sites("f1", "✓ up", update="  ✗ x  FAIL: Could not resolve host\n  · y  updated: unchanged (abc)")
    assert "rc=2" in out and "갱신(git pull)" in out, ("마지막 줄이 아니어도 ✗ 를 본다", out, calls)


def test_update_sites_shows_the_pull_output_as_the_cause_of_a_pull_failure(sites):
    """5라운드: rc 2 갈래가 up 출력(성공 로그)을 '실패 원인' 으로 보여 줬다 — 같은 임시파일을 up 이 덮었다."""
    out, calls, state = sites("f2", "✓ up", update="  ✗ x  FAIL: Could not resolve host", show_cause=True)
    assert "CAUSE:" in out and "Could not resolve host" in out.split("CAUSE:", 1)[1], ("사유는 pull 출력이어야 한다", out)


def _sites2_harness(tmp_path, srv2):
    """리스너 둘인 서비스(mxwp api+web·sf api+front·koorm api+mcp 꼴) — `health` 가 url 두 줄을 낸다."""
    (pa, pfa), (pb, pfb) = srv2
    log = tmp_path / "svc2.log"; st = tmp_path / "state2"; st.mkdir(exist_ok=True)
    svc = tmp_path / "svc2.sh"
    svc.write_text(f'#!/usr/bin/env bash\n. "{LIB}"\n{SRV_TOOLS}\necho "$*" >> "{log}"\n'
                   f'case "$1" in update) echo "  · x  updated: unchanged (abc)";; fp) echo "$STUB_FP";; status) echo "  ✓ up  x";; enabled) exit 0;;\n'
                   f'  health) echo http://127.0.0.1:{pa}/; echo http://127.0.0.1:{pb}/;;\n'
                   f'  down) _srv_stop "{pfa}"; [ "${{STUB_KEEP_B:-0}}" = 1 ] || _srv_stop "{pfb}";;\n'
                   f'  up) hwax_alive http://127.0.0.1:{pa}/ || _srv_start {pa} "{pfa}"; hwax_alive http://127.0.0.1:{pb}/ || _srv_start {pb} "{pfb}";; esac\nexit 0\n'); svc.chmod(0o755)
    def run(fp, env=None):
        log.unlink(missing_ok=True)
        script = (f'SVC="{svc}"\n. "{LIB}"\nexport HWAX_RESTART_STATE_DIR="{st}" HWAX_WAIT_DOWN_MAX=2\n{SRV_TOOLS}\n'
                  f'hwax_alive http://127.0.0.1:{pa}/ || _srv_start {pa} "{pfa}" || exit 9\n'
                  f'hwax_alive http://127.0.0.1:{pb}/ || _srv_start {pb} "{pfb}" || exit 9\n'
                  f'b0=$(cat "{pfb}")\nshow_cause() {{ :; }}\n{_restart_svc_block()}\nrestart_svc x; echo "rc=$? b=$([ "$(cat "{pfb}")" = "$b0" ] && echo same || echo new)"')
        e = {"PATH": os.environ["PATH"], "HOME": str(tmp_path), "STUB_FP": fp, **(env or {})}
        r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=120, env=e)
        return r.stdout + r.stderr, ((st / "x").read_text().strip() if (st / "x").exists() else None)
    return run


def test_update_sites_with_two_listeners_records_only_when_both_are_replaced(tmp_path, srv2):
    """5라운드(high): 3라운드가 lib 를 url 별 비교로 고쳤는데 update-sites 는 그 규율을 손으로 다시 쓴 복사본이라 수정을 못 받았다.
    인스턴스 둘 중 하나가 옛 프로세스로 남아도 기준 지문이 적혀 **영구 생략**됐다(mxwp·signalforge·kooremapper·portal 전부 해당)."""
    pb = srv2[1][0]
    run = _sites2_harness(tmp_path, srv2)
    out, state = run("f1"); assert "rc=0" in out and state == "f1", ("처음엔 둘 다 갈리고 기록한다", out)
    out, state = run("f2", env={"STUB_KEEP_B": "1"})     # down 이 B 를 놓친다 → up 은 B 를 '이미 떠 있다' 로 본다
    assert "rc=1" in out and "b=same" in out and f"같은 프로세스가 답한다: http://127.0.0.1:{pb}/" in out and state == "f1", ("하나라도 옛 프로세스면 무기록", out)
    out, state = run("f2"); assert "rc=0" in out and state == "f2", "다음 정상 실행이 둘 다 갈고 기록한다"


def _sites_driver_block() -> str:
    """restart_svc + 포털 게이트 + 나머지 루프 + 요약 — 드라이버까지 포함해 '한 서비스의 rc 가 나머지 실행을 어떻게 가르는가' 를 본다."""
    i = UPDATE_SITES.index('SKIPPED_RESTART=""')
    return UPDATE_SITES[i:]


def test_update_sites_portal_pull_failure_does_not_abort_the_rest(tmp_path, srv):
    """4라운드(내가 4차에서 만든 회귀): 포털의 pull 실패가 '재기동 생략' 인데도 rc 1 이라 포털 게이트가 나머지 전부를 중단시켰다.
    GitHub 이 안 닿는 박스에서 무인자 update-sites 가 게이트웨이·에이전트서버까지 손도 못 댔고, 안내는 원인을 '포털 로그' 로 잘못 가리켰다."""
    port, pf = srv
    st = tmp_path / "state"; st.mkdir(); (st / "portal").write_text("f1\n"); (st / "gw").write_text("f1\n")
    log = tmp_path / "svc.log"
    svc = tmp_path / "svc.sh"
    svc.write_text(f'#!/usr/bin/env bash\necho "$*" >> "{log}"\n'
                   f'case "$1" in\n'
                   f'  update) if [ "$2" = portal ]; then echo "  ✗ portal  FAIL: Could not resolve host"; else echo "  · $2  updated: unchanged (abc)"; fi ;;\n'
                   f'  fp) echo f1 ;; status) echo "  ✓ up  $2" ;; port) echo {port} ;; health) echo http://127.0.0.1:{port}/health ;;\n'
                   f'  enabled) exit 0 ;; down|up) echo "TOUCHED:$1 $2" ;; esac\nexit 0\n'); svc.chmod(0o755)
    script = (f'SVC="{svc}"\n. "{LIB}"\nexport HWAX_RESTART_STATE_DIR="{st}"\n'
              f'HAS_PORTAL=1; PORTAL=portal; REST="gw"; TARGETS="portal gw"\nshow_cause() {{ :; }}\nnote() {{ echo "NOTE:$*"; }}\n'
              f'{_sites_driver_block()}')
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=90,
                       env={"PATH": os.environ["PATH"], "HOME": str(tmp_path)})
    out = r.stdout + r.stderr; calls = log.read_text().splitlines() if log.exists() else []
    assert "portal 갱신(git pull) 실패" in out and "건드리지 않고 중단" not in out, ("포털이 정상이면 중단하지 않는다", out)
    assert "update gw" in calls and "재기동 생략" in out, ("나머지 서비스가 계속 돈다", calls)
    assert "갱신(git pull) 실패: portal" in out and r.returncode == 1, ("끝에서 종료코드만 올린다", out, r.returncode)
    assert "TOUCHED" not in out, "둘 다 변경 없음·살아 있음이라 down/up 은 없다"


def test_update_sites_keeps_its_state_apart_from_deploy_all():
    """2라운드(C4): 인자 없는 update-sites 는 portal 도 대상 — §2 와 같은 상태 파일을 다른 형식의 지문으로 번갈아 덮으면 핑퐁 재기동."""
    assert 'HWAX_RESTART_STATE_DIR="${HWAX_RESTART_STATE_DIR:-$ROOT/infra/.state/restart-fp/sites}"' in UPDATE_SITES
    assert 'mapfile -t _urls < <("$SVC" health "$name"' in UPDATE_SITES and 'hwax_verify_restarted "$name" "$cur" "$id0" "$id1" "${_urls[@]}"' in UPDATE_SITES, "판정은 lib 정본을 쓴다(5라운드)"
    assert 'hwax_wait_down "${_urls[@]}"' in UPDATE_SITES


def test_the_per_url_verdict_lives_in_one_place():
    """5라운드(high): 3라운드가 lib 를 url 별 비교로 고쳤는데 update-sites 는 복사본이라 수정을 못 받았다 — 규율은 한 곳에만 있어야 한다."""
    lib = LIB.read_text(encoding="utf-8")
    assert "hwax_verify_restarted() {" in lib and lib.count("hwax_verify_restarted") >= 3, "정의·주석·사이클 호출"
    assert "hwax_verify_restarted" in UPDATE_SITES, "update-sites 도 같은 함수를 쓴다"
    for f in (UPDATE_SITES, DEPLOY_ALL):
        assert 'if [ "$id1" != "$id0" ]' not in f, "손으로 다시 쓴 판정이 남아 있으면 다음 수정이 한쪽에만 들어간다"


def test_update_all_no_longer_hand_wires_the_env_window():
    assert "_ae0" not in UPDATE_ALL and "_ae1" not in UPDATE_ALL, "§3.5 전/후 창은 §1c·운영자 편집을 못 봤다 — 상태 기준으로 대체"
