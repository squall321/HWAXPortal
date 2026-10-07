# update-all 이 도는·줄 선 심의가 있을 때 에이전트 서버를 재기동하지 않는지(§4 update-sites · §5 재프로비저닝), 그 사실이 ○ 로 남는지
"""왜 — 좌석 20석 넘는 심의는 몇 시간 돈다. 에이전트 서버의 재기동은 2초 유예 뒤 강제 종료라, 코드나 설정이 바뀐 update-all
한 번이 도는 심의와 줄 선 심의를 말없이 지운다(재개가 없다). 한도를 아무리 넉넉히 잡아도 배포 한 번이 가장 흔한 절단이 된다.
유예를 늘려서는 몇 시간짜리를 못 살린다 — 무인 경로는 끊지 않고 건너뛴 사실을 남긴다(강행은 AGENT_RESTART_FORCE=1).

짝 — 에이전트 서버 /health 가 delib_active·delib_queued 를 싣는다(HWAXAgentServer). 여기서는 그 응답을 지어낸 서버로 대신하고
lib·update-sites·update-all 의 그 구획을 **원문 그대로 떼어 돌린다**(실물 서비스는 건드리지 않는다).
"""
import http.server
import json
import os
import subprocess
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LIBDIR = ROOT / "infra/scripts/lib"
BUSY_LIB = LIBDIR / "delib-busy.sh"
UPDATE_SITES = (ROOT / "infra/scripts/update-sites.sh").read_text(encoding="utf-8")
UA = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")
LIBS = f'. "{LIBDIR}/change-detect.sh"\n. "{LIBDIR}/skip-ledger.sh"\n. "{BUSY_LIB}"\n'


@pytest.fixture()
def health():
    """지어낸 에이전트 서버 /health — state['body'] 를 그대로 답하고(문자열이면 그대로, None 이면 404) 요청 수를 센다."""
    state = {"body": {"status": "ok"}, "hits": 0}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            state["hits"] += 1
            body = state["body"]
            if body is None or self.path != "/health":
                self.send_response(404); self.end_headers(); return
            raw = (body if isinstance(body, str) else json.dumps(body)).encode()
            self.send_response(200); self.send_header("content-type", "application/json"); self.end_headers(); self.wfile.write(raw)

        def log_message(self, *a):
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    state["url"] = f"http://127.0.0.1:{srv.server_address[1]}/health"
    yield state
    srv.shutdown(); srv.server_close()


def _sh(script: str, **env) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=90,
                          env={"PATH": os.environ["PATH"], "HOME": os.environ.get("HOME", "/tmp"), **env})


# ── lib — 묻는 함수 ────────────────────────────────────────────────────────────────────────
def _busy(url: str, **env) -> tuple[int, str]:
    r = _sh(f'set -uo pipefail\n. "{BUSY_LIB}"\nout="$(hwax_delib_busy "{url}")"; echo "rc=$? out=[$out]"', **env)
    assert not r.stderr, r.stderr
    rc, out = r.stdout.strip().split(" ", 1)
    return int(rc[3:]), out[5:-1]


@pytest.mark.parametrize("body,want", [
    ({"status": "ok", "delib_active": 1, "delib_queued": 0}, (0, "1 0")),
    ({"status": "ok", "delib_active": 0, "delib_queued": 3}, (0, "0 3")),     # 줄 선 것도 재기동하면 사라진다(메모리에만 있다)
    ({"status": "ok", "delib_active": 2, "delib_queued": 5}, (0, "2 5")),
    ({"status": "ok", "delib_active": 0, "delib_queued": 0}, (1, "")),
    ({"status": "ok", "delib_active": 4}, (0, "4 0")),                        # 하나만 실은 판 — 없는 쪽은 0 으로 읽는다
])
def test_도는_심의와_줄_선_심의를_센다(health, body, want):
    health["body"] = body
    assert _busy(health["url"]) == want


@pytest.mark.parametrize("body", [{"status": "ok"}, "<html>502</html>", "", None, {"delib_active": "많음", "delib_queued": 0},
                                  {"delib_active": True, "delib_queued": 0}, {"delib_active": -1, "delib_queued": 0}, [1, 2]])
def test_알_수_없으면_2다_건너뛰는_값이_아니다(health, body):
    """필드가 없는 옛 판, JSON 이 아닌 응답, 수가 아닌 값 — **모른다**. 모르는데 건너뛰면 옛 판을 영영 못 올린다."""
    health["body"] = body
    assert _busy(health["url"]) == (2, "")


def test_답하지_않는_서버는_2다():
    """내려가 있으면 끊을 심의가 없다 — 그대로 띄워야 한다."""
    assert _busy("http://127.0.0.1:9/health") == (2, "")


def test_강행하면_묻지도_않는다(health):
    health["body"] = {"delib_active": 3, "delib_queued": 1}
    assert _busy(health["url"], AGENT_RESTART_FORCE="1") == (1, "")
    assert health["hits"] == 0
    assert _busy(health["url"], AGENT_RESTART_FORCE="0") == (0, "3 1"), "1 만 강행이다"


def test_운영자_셸의_프록시를_타지_않는다(health):
    """로컬 health 를 사내 프록시로 부르면 프록시가 이 박스의 루프백에 못 닿아 '모름' 이 되고, 모름은 재기동이다 —
    프록시 변수가 있는 셸에서 돌린 update-sites 만 도는 심의를 끊는다."""
    health["body"] = {"delib_active": 1, "delib_queued": 0}
    dead = "http://127.0.0.1:9"
    assert _busy(health["url"], http_proxy=dead, HTTP_PROXY=dead, no_proxy="", NO_PROXY="") == (0, "1 0")


# ── §4 update-sites — 에이전트 서버를 내리기 전에 묻는다 ────────────────────────────────────────
def _restart_svc_block() -> str:
    i = UPDATE_SITES.index('SKIPPED_RESTART=""')
    return UPDATE_SITES[i:UPDATE_SITES.index("# 1) 포털 먼저", i)]


def _restart(tmp_path: Path, url: str, name: str = "agent-server", update: str = "  · x  updated: abc → def", **env):
    """restart_svc 를 대역 services.sh 로 돌린다 → (화면, services.sh 가 받은 호출, 기록된 지문, 장부)."""
    log = tmp_path / "svc.log"; st = tmp_path / "state"; st.mkdir(exist_ok=True); ledger = tmp_path / "ledger"
    log.unlink(missing_ok=True); ledger.write_text("")
    svc = tmp_path / "svc.sh"
    svc.write_text(f'#!/usr/bin/env bash\necho "$*" >> "{log}"\n'
                   f'case "$1" in update) printf "%b\\n" "$STUB_UPDATE";; fp) echo f-new;; status) echo "  ✓ up x";;\n'
                   f'  health) echo {url};; enabled) exit 0;; esac\nexit 0\n')
    svc.chmod(0o755)
    script = (f'set -uo pipefail\nSVC="{svc}"\n{LIBS}export HWAX_RESTART_STATE_DIR="{st}" HWAX_WAIT_DOWN_MAX=1 HWAX_WAIT_UP_MAX=1 '
              f'HWAX_SKIP_LEDGER="{ledger}"\nshow_cause() {{ :; }}\n{_restart_svc_block()}\n'
              f'restart_svc "{name}"; echo "rc=$?"; echo "DEFERRED=[$DEFERRED_RESTART]"')
    r = _sh(script, STUB_UPDATE=update, **env)
    state = (st / name).read_text().strip() if (st / name).exists() else None
    return r.stdout + r.stderr, (log.read_text().splitlines() if log.exists() else []), state, ledger.read_text()


def test_심의가_돌면_에이전트_서버를_내리지_않는다(tmp_path, health):
    """**이 시험이 이 파일의 이유다** — down·up 이 불리지 않고, 지문도 적지 않는다(다음 실행이 다시 본다)."""
    health["body"] = {"status": "ok", "delib_active": 2, "delib_queued": 1}
    out, calls, state, ledger = _restart(tmp_path, health["url"])
    assert "down agent-server" not in calls and "up agent-server" not in calls, calls
    assert state is None, "미룬 재기동의 지문을 적으면 새 코드가 영영 안 올라간다"
    assert "rc=0" in out and "DEFERRED=[ agent-server]" in out, out
    line = next(ln for ln in out.splitlines() if "○" in ln)
    assert "agent-server 재기동 건너뜀" in line and "심의 2건 진행 중, 1건 대기" in line
    assert "AGENT_RESTART_FORCE=1" in out and "./start.sh -d" in out, "끝난 뒤 무엇을 하는지와 강행하는 법"
    assert "agent-server 재기동 건너뜀" in ledger and "AGENT_RESTART_FORCE=1" in ledger, "update-all 의 마지막 요약에도 다시 나온다"


def test_줄만_서_있어도_내리지_않는다(tmp_path, health):
    health["body"] = {"delib_active": 0, "delib_queued": 4}
    out, calls, state, _ = _restart(tmp_path, health["url"])
    assert "down agent-server" not in calls and "심의 0건 진행 중, 4건 대기" in out and state is None


@pytest.mark.parametrize("body", [{"status": "ok", "delib_active": 0, "delib_queued": 0}, {"status": "ok"}])
def test_심의가_없거나_옛_판이면_종전대로_재기동한다(tmp_path, health, body):
    health["body"] = body
    out, calls, _, ledger = _restart(tmp_path, health["url"])
    assert "down agent-server" in calls and "up agent-server" in calls, (calls, out)
    assert "건너뜀" not in out and ledger == ""
    said_old = "묻지 못하고 재기동한다" in out
    assert said_old is ("delib_active" not in body), "수를 싣지 않는 옛 판이면 묻지 못했다고 말한다 — 조용하면 물은 줄 안다"


def test_강행하면_심의가_돌아도_재기동한다(tmp_path, health):
    health["body"] = {"delib_active": 2, "delib_queued": 1}
    out, calls, _, ledger = _restart(tmp_path, health["url"], AGENT_RESTART_FORCE="1")
    assert "down agent-server" in calls and "up agent-server" in calls and "건너뜀" not in out and ledger == ""


def test_다른_서비스는_묻지_않는다(tmp_path, health):
    """게이트웨이·signalforge-mcp 의 재기동은 심의를 지우지 않는다(도구 호출이 한 번 실패할 뿐이다) — 넓히면 배포가 안 된다."""
    health["body"] = {"delib_active": 2, "delib_queued": 1}
    out, calls, _, _ = _restart(tmp_path, health["url"], name="mcp-gateway")
    assert "down mcp-gateway" in calls and "up mcp-gateway" in calls and "건너뜀" not in out


def test_미룬_실행에서_갱신이_실패했으면_종료코드는_올린다(tmp_path, health):
    health["body"] = {"delib_active": 1, "delib_queued": 0}
    out, calls, _, _ = _restart(tmp_path, health["url"], update="  ✗ agent-server  FAIL: pull")
    assert "rc=2" in out and "down agent-server" not in calls, out


def _driver(tmp_path: Path, url: str, rest: str = "agent-server", **env) -> subprocess.CompletedProcess:
    """restart_svc + 나머지 루프 + 요약까지 — update-sites 의 종료코드를 본다."""
    st = tmp_path / "state"; st.mkdir(exist_ok=True); ledger = tmp_path / "ledger"; ledger.write_text("")
    svc = tmp_path / "svc.sh"
    svc.write_text('#!/usr/bin/env bash\ncase "$1" in update) echo "  · $2  updated: a → b";; fp) echo f-new;; status) echo "  ✓ up  $2";;\n'
                   f'  health) echo {url};; enabled) exit 0;; esac\nexit 0\n')
    svc.chmod(0o755)
    i = UPDATE_SITES.index('SKIPPED_RESTART=""')
    script = (f'set -uo pipefail\nSVC="{svc}"\n{LIBS}export HWAX_RESTART_STATE_DIR="{st}" HWAX_WAIT_DOWN_MAX=1 HWAX_WAIT_UP_MAX=1 '
              f'HWAX_SKIP_LEDGER="{ledger}"\nHAS_PORTAL=0; PORTAL=portal; REST="{rest}"; TARGETS="{rest}"\nshow_cause() {{ :; }}\n'
              f'{UPDATE_SITES[i:]}')
    return _sh(script, **env)


def test_미루기만_한_실행은_3으로_끝난다(tmp_path, health):
    """0 이면 '전부 재기동됐다' 와 구별이 안 된다 — deploy-ste 의 게이트와 같은 약속이다(3 = 안 했다, 실패는 아니다)."""
    health["body"] = {"delib_active": 1, "delib_queued": 2}
    r = _driver(tmp_path, health["url"])
    assert r.returncode == 3, r.stdout + r.stderr
    assert "재기동 미룸" in r.stdout and "agent-server" in r.stdout and "전부 최신화·재기동" not in r.stdout
    idle = tmp_path / "idle"; idle.mkdir()
    health["body"] = {"delib_active": 0, "delib_queued": 0}
    assert _driver(idle, health["url"]).returncode != 3, "심의가 없으면 미룬 것이 없다"


# ── update-all §4 — update-sites 의 3 은 실패가 아니다 ─────────────────────────────────────────
@pytest.mark.parametrize("rc,failed", [(0, False), (3, False), (1, True), (2, True)])
def test_update_all_은_미룬_재기동을_실패로_세지_않는다(tmp_path, rc, failed):
    i = UA.index('"$SELF_REPO/infra/scripts/update-sites.sh" signalforge-mcp mcp-gateway agent-server; _us_rc=$?')
    block = UA[i:UA.index("esac\n", i) + 5]
    stub = tmp_path / "infra/scripts/update-sites.sh"; stub.parent.mkdir(parents=True)
    stub.write_text(f'#!/usr/bin/env bash\necho "ARGS:$*"\nexit {rc}\n'); stub.chmod(0o755)
    r = _sh(f'set -uo pipefail\nSELF_REPO="{tmp_path}"\nfail() {{ echo "FAIL:$*"; }}\n{block}\necho end')
    assert r.returncode == 0 and not r.stderr and "end" in r.stdout, r.stderr
    assert "ARGS:signalforge-mcp mcp-gateway agent-server" in r.stdout, "백엔드 → 게이트웨이 → 소비자 순서 그대로"
    assert ("FAIL:" in r.stdout) is failed, r.stdout


# ── update-all §5 — 재프로비저닝은 게이트웨이·에이전트서버 재기동을 끌고 온다 ─────────────────────────
def _section5_gate() -> str:
    i = UA.index('  _reprov_deferred=""')
    return UA[i:UA.index('  if [ -n "$MISSING" ]; then\n    echo "  · config에 없거나', i)]


def _gate(health_url: str, missing: str, **env) -> str:
    gate = _section5_gate().replace("http://127.0.0.1:9009/health", health_url)
    assert health_url in gate, "§5 가 묻는 주소는 에이전트 서버의 health 다"
    r = _sh(f'set -uo pipefail\n{LIBS}MISSING="{missing}"\n{gate}\nprintf "MISSING=[%s] DEFERRED=[%s]\\n" "$MISSING" "$_reprov_deferred"', **env)
    assert r.returncode == 0 and not r.stderr, r.stderr
    return r.stdout


def test_심의가_돌면_재프로비저닝을_이번_실행에서_하지_않는다(health):
    """재프로비저닝이 성공하면 곧바로 `down mcp-gateway agent-server` 다 — 묻는 자리는 그 앞이어야 한다. config 만 고치고 재기동을
    빼면 떠 있는 프로세스와 파일이 갈리므로 통째로 미룬다."""
    health["body"] = {"delib_active": 1, "delib_queued": 2}
    out = _gate(health["url"], "arp testscope_sso")
    assert "MISSING=[] DEFERRED=[arp testscope_sso]" in out, out
    line = next(ln for ln in out.splitlines() if "○" in ln)
    assert "재프로비저닝 건너뜀" in line and "심의 1건 진행 중, 2건 대기" in line and "arp testscope_sso" in line
    assert "AGENT_RESTART_FORCE=1" in out
    assert UA.index('  _reprov_deferred=""') < UA.index('if ( cd "$GW_DIR" && export PER_USER_SSO_APPS '), "provision 보다 먼저 묻는다"


@pytest.mark.parametrize("body", [{"delib_active": 0, "delib_queued": 0}, {"status": "ok"}, None])
def test_심의가_없거나_모르면_종전대로_재프로비저닝한다(health, body):
    health["body"] = body
    out = _gate(health["url"], "arp")
    assert "MISSING=[arp] DEFERRED=[]" in out and "○" not in out, out


def test_고칠_것이_없으면_묻지도_않는다(health):
    health["body"] = {"delib_active": 9, "delib_queued": 9}
    out = _gate(health["url"], "")
    assert "MISSING=[] DEFERRED=[]" in out and "○" not in out and health["hits"] == 0


def test_강행하면_심의가_돌아도_재프로비저닝한다(health):
    health["body"] = {"delib_active": 1, "delib_queued": 0}
    assert "MISSING=[arp] DEFERRED=[]" in _gate(health["url"], "arp", AGENT_RESTART_FORCE="1")


@pytest.mark.parametrize("deferred,shown", [("arp", False), ("", True)])
def test_미룬_실행을_정합이라고_말하지_않는다(deferred, shown):
    """○ 바로 아래에 '✓ config 정합(빠진 백엔드 없음)' 이 찍히면 로그가 스스로 어긋난다."""
    i = UA.index('ok "config 정합 (빠진 백엔드 없음)"')
    line = UA[UA.rindex("\n", 0, i) + 1:UA.index("\n", i)]
    r = _sh(f'set -uo pipefail; ok() {{ echo "OK:$*"; }}; KNOX_MISSING=0; _reprov_deferred="{deferred}"\n{line}\necho end')
    assert r.returncode == 0 and not r.stderr and "end" in r.stdout, r.stderr
    assert ("OK:config 정합" in r.stdout) is shown


# ── 손잡이는 이웃들이 적힌 자리에 적는다 ──────────────────────────────────────────────────────
def test_강행_손잡이가_사용법에_적혀_있다():
    """건너뛴 줄(○)을 본 사람이 다음에 찾는 곳이 사용법이다 — update-all 은 머리의 실행 예, update-sites 는 --help."""
    r = subprocess.run(["bash", str(ROOT / "infra/scripts/update-sites.sh"), "--help"], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0 and "AGENT_RESTART_FORCE=1" in r.stdout and "종료코드 3" in r.stdout, r.stdout
    head = UA[:UA.index("set -uo pipefail")]
    assert "AGENT_RESTART_FORCE=1 ./infra/scripts/update-all.sh" in head and "○" in head
