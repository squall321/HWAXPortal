# update-all 끝의 박스 훅(docs/core-link SRC-12) — lib 동작 · 바쁨 판정 · update-all 배선 · 무시 규칙을 본다
"""요청서 완료 기준 둘 — 빈 훅 폴더에서 동작이 지금과 같다(○ 한 줄만 더해진다 — 사용자 지시 '안 켠 기능도 로그에') · 실패하는 시험 훅
하나로 종료코드 0 과 요약 줄이 함께 나온다. 바쁨 판정은 가짜 /health 로만 본다 — 떠 있는 에이전트 서버를 두드리지 않는다."""
import json
import os
import socket
import sqlite3
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "infra/scripts"
LIB = SCRIPTS / "lib/post-update-hooks.sh"
LEDGER_LIB = SCRIPTS / "lib/skip-ledger.sh"
UA = (SCRIPTS / "update-all.sh").read_text(encoding="utf-8")
TAIL_START = '[ "${HWAX_UPDATE_ALL_STOP:-0}" = 1 ] && echo "  · 종료 요청이 있었지만'


class _Agent:
    """가짜 에이전트 서버 /health — review_active · drain · delib_active · delib_queued 만 낸다."""

    def __init__(self, ra=0, da=0, dq=0):
        body = json.dumps({"review_active": ra, "drain": {"on": False}, "draining": False,
                           "delib_active": da, "delib_queued": dq}).encode()

        class H(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                self.send_response(200 if self.path == "/health" else 404)
                self.send_header("content-type", "application/json")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass

        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def close(self):
        self.srv.shutdown()


def _closed_url() -> str:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return f"http://127.0.0.1:{port}"


@pytest.fixture
def lay(tmp_path):
    """<tmp>/work/HWAXPortal(포털 루트) · 빈 HOME — find_repo 의 ~/Projects · ~/claude 가 실물 리포를 찾지 않게."""
    root = tmp_path / "work/HWAXPortal"
    (root / "infra/hooks/post-update.d").mkdir(parents=True)
    home = tmp_path / "home"
    home.mkdir()
    return root, home, tmp_path


def _hook(root: Path, name: str, body: str) -> Path:
    p = root / "infra/hooks/post-update.d" / name
    p.write_text(body, encoding="utf-8")
    return p


def _run(lay, body: str, *, timeout=60, **env):
    root, home, tmp = lay
    ledger = tmp / "ledger"
    ledger.write_text("")
    script = (f'set -uo pipefail\n. "{LEDGER_LIB}"\nHWAX_SKIP_LEDGER="{ledger}"\n. "{LIB}"\n'
              f'cd "{tmp}"\n{body}\n')
    base = {"PATH": os.environ["PATH"], "HOME": str(home), "LANG": "C.UTF-8", "LOG": str(tmp / "ran"),
            # 바쁨 판정이 기본 주소(떠 있는 에이전트 서버)로 가지 않게 늘 닫힌 주소를 기본으로 둔다.
            "HWAX_AGENT_URL": env.pop("HWAX_AGENT_URL", None) or _closed_url()}
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=timeout, env={**base, **env})
    # update-all 끝은 장부를 지운다(rm -f "$HWAX_SKIP_LEDGER") — 끝을 돌린 시험에는 장부가 없다.
    return (r, (tmp / "ran").read_text().split() if (tmp / "ran").exists() else [],
            ledger.read_text() if ledger.exists() else "")


def _call(lay):
    return f'hwax_post_update_hooks "{lay[0]}"; echo "rc=$?"; printf "NOTE=[%s]\\n" "$HWAX_HOOKS_NOTE"'


# ── lib — 훅 돌리기 ───────────────────────────────────────────────────────────────────────────────────
def test_훅이_없으면_안_켠_줄_하나이고_아무것도_돌지_않는다(lay):
    r, ran, ledger = _run(lay, _call(lay))
    assert "rc=0" in r.stdout and "NOTE=[]" in r.stdout, r.stdout + r.stderr
    assert "○" in r.stdout and "박스 훅(update-all 끝)" in r.stdout and "켜려면" in r.stdout
    assert "박스 훅(update-all 끝)" in ledger, "끝 요약에도 다시 나오게 장부에 적는다"
    assert ran == [] and r.stderr == "", r.stderr


def test_C_차례로_돌고_실패는_요약_줄_하나로_반환은_0(lay):
    root = lay[0]
    _hook(root, "20-b.local.sh", 'echo 20-b >> "$LOG"; exit 3\n')
    _hook(root, "10-a.local.sh", 'echo 10-a >> "$LOG"\n')
    _hook(root, "05-z.local.sh", 'echo 05-z >> "$LOG"\n')
    r, ran, ledger = _run(lay, _call(lay))
    assert ran == ["05-z", "10-a", "20-b"], ran
    assert "rc=0" in r.stdout, r.stdout + r.stderr
    note = r.stdout.split("NOTE=[", 1)[1]
    assert "박스 훅 3개 중 1개 실패" in note and "20-b.local.sh(rc 3)" in note and "종료코드에는 넣지 않는다" in note, note
    assert "▶ 박스 훅 05-z.local.sh" in r.stdout and ledger == "", "실패는 ○ 장부에 들지 않는다"


def test_모두_끝나면_모두_끝났다_줄(lay):
    root = lay[0]
    _hook(root, "10-a.local.sh", "true\n")
    _hook(root, "20-b.local.sh", "true\n")
    r, _, _ = _run(lay, _call(lay))
    assert "NOTE=[  · 박스 훅 2개 — 모두 끝났다: 10-a.local.sh · 20-b.local.sh" in r.stdout, r.stdout


def test_훅은_포털_루트에서_입력_없이_돌고_HWAX_UPDATE_FAIL_을_받는다(lay):
    root, _, tmp = lay
    _hook(root, "10-env.local.sh", f'pwd > "{tmp}/pwd"; cat > "{tmp}/stdin"; echo "$HWAX_UPDATE_FAIL" > "{tmp}/fail"\n')
    r, _, _ = _run(lay, "FAIL=1\n" + _call(lay), timeout=30)
    assert "모두 끝났다" in r.stdout, r.stdout + r.stderr
    assert (tmp / "pwd").read_text().strip() == str(root.resolve())
    assert (tmp / "stdin").read_text() == "", "표준 입력은 비어 있다(훅이 입력을 기다리며 멈추지 않는다)"
    assert (tmp / "fail").read_text().strip() == "1"


def test_이름이_local_sh_가_아닌_sh_는_돌리지_않고_짚는다(lay):
    root = lay[0]
    _hook(root, "30-c.sh", 'echo 30-c >> "$LOG"\n')
    _hook(root, "10-a.local.sh", 'echo 10-a >> "$LOG"\n')
    (root / "infra/hooks/post-update.d/README.md").write_text("설명\n")
    r, ran, _ = _run(lay, _call(lay))
    assert ran == ["10-a"], ran
    assert "돌리지 않는 파일: 30-c.sh" in r.stdout and "README" not in r.stdout, r.stdout


def test_이름이_틀린_훅만_있으면_짚고_안_켠_줄(lay):
    _hook(lay[0], "50-core-link.sh", "true\n")
    r, ran, ledger = _run(lay, _call(lay))
    assert "돌리지 않는 파일: 50-core-link.sh" in r.stdout and "○" in r.stdout and ran == []
    assert "박스 훅(update-all 끝)" in ledger


def test_상한을_넘긴_훅은_실패로_세고_다음_훅은_돈다(lay):
    root = lay[0]
    _hook(root, "10-slow.local.sh", "exec sleep 30\n")
    _hook(root, "20-next.local.sh", 'echo 20-next >> "$LOG"\n')
    t0 = time.monotonic()
    r, ran, _ = _run(lay, _call(lay), timeout=60, HWAX_HOOK_TIMEOUT_S="1")
    assert time.monotonic() - t0 < 20, "상한이 훅을 끊어야 한다"
    assert ran == ["20-next"] and "10-slow.local.sh(상한 1초)" in r.stdout and "rc=0" in r.stdout, r.stdout + r.stderr


def test_상한_값을_못_읽으면_말하고_기본으로_돈다(lay):
    _hook(lay[0], "10-a.local.sh", 'echo 10-a >> "$LOG"\n')
    r, ran, _ = _run(lay, _call(lay), HWAX_HOOK_TIMEOUT_S="abc")
    assert ran == ["10-a"] and "HWAX_HOOK_TIMEOUT_S=abc 을 읽지 못했다" in r.stdout, r.stdout


def test_종료_요청이_있으면_건너뛴다(lay):
    _hook(lay[0], "10-a.local.sh", 'echo 10-a >> "$LOG"\n')
    r, ran, ledger = _run(lay, _call(lay), HWAX_UPDATE_ALL_STOP="1")
    assert ran == [] and "종료 요청이 있어 돌리지 않았다" in r.stdout and "박스 훅 1개" in ledger, r.stdout


# ── --hooks-when-idle — 바쁨 판정 ────────────────────────────────────────────────────────────────────
def test_when_idle_심의가_돌면_건너뛴다(lay):
    _hook(lay[0], "10-a.local.sh", 'echo 10-a >> "$LOG"\n')
    a = _Agent(da=1, dq=2)
    try:
        r, ran, ledger = _run(lay, _call(lay), HWAX_HOOKS_WHEN_IDLE="1", HWAX_AGENT_URL=a.url)
    finally:
        a.close()
    assert ran == [] and "일이 있다(심의 1 · 줄 2 · 카드 대조 0)" in r.stdout, r.stdout + r.stderr
    assert "박스 훅 1개" in ledger


def test_when_idle_에이전트를_못_물으면_모름이라_건너뛴다(lay):
    _hook(lay[0], "10-a.local.sh", 'echo 10-a >> "$LOG"\n')
    r, ran, _ = _run(lay, _call(lay), HWAX_HOOKS_WHEN_IDLE="1")
    assert ran == [] and "셀 수 없다" in r.stdout and "에이전트 서버 /health" in r.stdout, r.stdout + r.stderr


def test_when_idle_일이_없으면_돈다(lay):
    _hook(lay[0], "10-a.local.sh", 'echo 10-a >> "$LOG"\n')
    a = _Agent()
    try:
        r, ran, _ = _run(lay, _call(lay), HWAX_HOOKS_WHEN_IDLE="1", HWAX_AGENT_URL=a.url)
    finally:
        a.close()
    assert ran == ["10-a"] and "일이 없다(심의 0 · 줄 0 · 카드 대조 0)" in r.stdout, r.stdout + r.stderr


def _jobs_db(tmp: Path, rel: str, rows):
    db = tmp / "work/HEAXHub/var/app_data" / rel
    db.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE jobs (id INTEGER PRIMARY KEY, status TEXT)")
    c.executemany("INSERT INTO jobs(status) VALUES (?)", [(s,) for s in rows])
    c.commit()
    c.close()
    return db


def test_when_idle_StepForge_대기_작업도_일이다(lay):
    root, _, tmp = lay
    _hook(root, "10-a.local.sh", 'echo 10-a >> "$LOG"\n')
    _jobs_db(tmp, "step_forge/stepforge.db", ["done", "pending", "failed"])
    _jobs_db(tmp, "doc_forge/docforge.db", ["done"])
    a = _Agent()
    try:
        r, ran, _ = _run(lay, _call(lay), HWAX_HOOKS_WHEN_IDLE="1", HWAX_AGENT_URL=a.url)
    finally:
        a.close()
    assert ran == [] and "StepForge 1 · DocForge 0" in r.stdout, r.stdout + r.stderr


def test_when_idle_작업_DB_를_못_읽으면_모름(lay):
    root, _, tmp = lay
    _hook(root, "10-a.local.sh", 'echo 10-a >> "$LOG"\n')
    bad = tmp / "work/HEAXHub/var/app_data/doc_forge/docforge.db"
    bad.parent.mkdir(parents=True)
    bad.write_bytes(b"not a sqlite file")
    a = _Agent()
    try:
        r, ran, _ = _run(lay, _call(lay), HWAX_HOOKS_WHEN_IDLE="1", HWAX_AGENT_URL=a.url)
    finally:
        a.close()
    assert ran == [] and "셀 수 없음: DocForge 작업 DB" in r.stdout, r.stdout + r.stderr


def test_when_idle_DynaForge_를_못_세면_모름(lay):
    root, _, tmp = lay
    _hook(root, "10-a.local.sh", 'echo 10-a >> "$LOG"\n')
    common = tmp / "work/KooRemapper/platform/infra/scripts/_common.sh"
    common.parent.mkdir(parents=True)
    common.write_text("exit 1\n")              # 인스턴스 · DB 를 못 물은 꼴 — 수 대신 빈 값
    a = _Agent()
    try:
        r, ran, _ = _run(lay, _call(lay), HWAX_HOOKS_WHEN_IDLE="1", HWAX_AGENT_URL=a.url)
    finally:
        a.close()
    assert ran == [] and "셀 수 없음: DynaForge 작업" in r.stdout, r.stdout + r.stderr


# ── update-all 배선 ─────────────────────────────────────────────────────────────────────────────────
def test_update_all_은_인자와_lib_와_끝_자리를_잇는다():
    assert '    --hooks-when-idle) HWAX_HOOKS_WHEN_IDLE=1 ;;\n' in UA
    lib_at = UA.index('. "$SELF_REPO/infra/scripts/lib/post-update-hooks.sh"')
    assert lib_at < UA.index('hr "1) 포털 레포 최신화"'), "lib 는 첫 § 머리 전에 적재한다"
    tail = UA[UA.index(TAIL_START):]
    assert (tail.index("_hwax_board_resume") < tail.index('hwax_post_update_hooks "$SELF_REPO"')
            < tail.index('hwax_skip_summary\nrm -f "$HWAX_SKIP_LEDGER"')), "끝맺음 뒤 · ○ 요약 앞"
    assert (tail.index("_inbox_mark\n") < tail.index('printf \'%s\' "$HWAX_HOOKS_NOTE"')
            < tail.index("# ⚠ 경고 요약")), "따로 줄은 받은 편지함 뒤 · 경고 요약 앞"
    assert 'hr "' not in tail, "끝에서는 § 머리를 부르지 않는다(비우기 깃발 — CK-6)"
    assert "--hooks-when-idle" in UA[:UA.index("set -uo pipefail")], "손잡이는 머리 안내에 적는다"


def _ua_tail(lay, *, fail=0):
    root = lay[0]
    stubs = ('ok() { printf "  ✓ %s\\n" "$*"; }\n_hwax_drain_finish() { :; }\n_hwax_delib_pause_finish() { :; }\n'
             '_hwax_board_resume() { :; }\n_inbox_mark() { :; }\n')
    body = f'SELF_REPO="{root}"\n{stubs}FAIL={fail}\n{UA[UA.index(TAIL_START):]}'
    return _run(lay, body)


def test_update_all_끝_요약은_실패_훅_줄을_내고_종료코드는_0(lay):
    _hook(lay[0], "50-core-link.local.sh", "echo 하는 중; exit 4\n")
    r, _, _ = _ua_tail(lay)
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.count("박스 훅 1개 중 1개 실패 — 50-core-link.local.sh(rc 4)") == 2, "제자리에서 한 번, 끝 요약에서 한 번"
    assert "경고 " not in r.stdout, "경고 수에 들지 않는다"
    assert r.stdout.rstrip().endswith("전체 최신화 완료 — 운영 준비 상태"), r.stdout


def test_update_all_끝_요약은_빈_폴더면_안_켠_줄_하나만_더한다(lay):
    r, _, _ = _ua_tail(lay)
    assert r.returncode == 0 and "있는데 안 켠 것 — 기능 1" in r.stdout and "박스 훅(update-all 끝)" in r.stdout, r.stdout + r.stderr
    assert "박스 훅 " not in r.stdout.replace("박스 훅(update-all 끝)", ""), "돌린 훅이 없으면 따로 줄도 없다"


def test_update_all_이_실패한_실행도_훅을_돌리고_종료코드는_그대로(lay):
    root, _, tmp = lay
    _hook(root, "10-a.local.sh", f'echo "$HWAX_UPDATE_FAIL" > "{tmp}/fail"\n')
    r, _, _ = _ua_tail(lay, fail=1)
    assert r.returncode == 1 and (tmp / "fail").read_text().strip() == "1", r.stdout + r.stderr
    assert "박스 훅 1개 — 모두 끝났다" in r.stdout


# ── 무시 규칙 ───────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("rel, ignored", [
    ("infra/hooks/post-update.d/50-core-link.local.sh", True),
    ("infra/hooks/post-update.d/README.md", False),
    ("infra/hooks/post-update.d/30-c.sh", False),          # 그래서 lib 가 이 이름을 짚는다(stash 가 치운다)
])
def test_gitignore_가_박스_훅을_지킨다(rel, ignored):
    r = subprocess.run(["git", "-C", str(ROOT), "check-ignore", "-q", "--no-index", rel])
    assert (r.returncode == 0) is ignored, rel


def test_README_는_추적한다():
    assert (ROOT / "infra/hooks/post-update.d/README.md").is_file()
