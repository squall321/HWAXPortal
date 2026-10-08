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
import time
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
    """지어낸 에이전트 서버 /health — state['body'] 를 그대로 답하고(문자열이면 그대로, None 이면 404) 요청 수를 센다.
    state['delay'] 에 초를 적으면 요청마다 앞에서부터 하나씩 꺼내 그만큼 늦게 답한다(이벤트 루프가 막힌 순간의 서버)."""
    state = {"body": {"status": "ok"}, "hits": 0, "delay": []}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            state["hits"] += 1
            if state["delay"]:
                time.sleep(state["delay"].pop(0))
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


# ── 늦게 답한 서버는 '모름' 이 아니다 — 거절과 시간 초과를 가른다 ────────────────────────────────────
# 에이전트 서버의 이벤트 루프는 동기 조회로 몇 초씩 막힌다(게이트웨이가 매달린 순간의 /tools-map 5초 · LLM 서버가 매달린 순간의
# /models 5초). 그 순간에 한 번 물어 4초를 넘기면 종전에는 '모름' 이었고 모름은 재기동이다 — 살아서 10시간짜리 패널을 돌리는
# 서버가 죽은 서버와 같은 취급을 받았다. 탐침 4초는 그대로 두고(죽은 상대를 재는 값이다) 시간 초과만 연속으로 세어 본다.
LATE = 5        # 탐침 한도(4초)를 넘기는 응답 지연


def test_한_번_늦게_답한_서버를_모름으로_읽지_않는다(health):
    health["body"] = {"status": "ok", "delib_active": 2, "delib_queued": 1}
    health["delay"] = [LATE]
    assert _busy(health["url"], HWAX_DELIB_PROBE_GAP_S="0") == (0, "2 1")
    assert health["hits"] == 2, "시간 초과면 다시 묻는다 — 답을 받았으면 더 묻지 않는다"


def test_내려간_서버는_다시_묻지_않는다():
    """거절(curl 7)은 내려가 있다는 뜻이다 — 다시 묻거나 쉬면 죽은 서버를 띄우는 일만 늦어진다."""
    t0 = time.monotonic()
    assert _busy("http://127.0.0.1:9/health", HWAX_DELIB_PROBE_GAP_S="5") == (2, "")
    assert time.monotonic() - t0 < 3, "거절에 재시도·대기를 썼다"


def test_연속으로_시간_초과면_매달린_것이다(health):
    """듣고는 있는데 내리 답이 없다 — 4. 2(내려갔다·옛 판)와 갈라야 부르는 쪽이 사유를 사실대로 적는다. 건너뛰는 값은 아니다
    (매달린 서버를 무인 경로가 다시 띄울 수 있어야 한다)."""
    health["body"] = {"status": "ok", "delib_active": 2, "delib_queued": 1}
    health["delay"] = [LATE, LATE]
    assert _busy(health["url"], HWAX_DELIB_PROBE_STRIKES="2", HWAX_DELIB_PROBE_GAP_S="0") == (4, "")
    assert health["hits"] == 2


@pytest.mark.parametrize("strikes", ["0", "-1", "많이", ""])
def test_횟수를_잘못_적어도_묻기는_한다(health, strikes):
    """0 은 '묻지 않는다' 가 아니다 — 한 번도 안 묻고 '매달렸다' 로 읽으면 도는 심의가 있어도 재기동한다. 기본값으로 읽는다."""
    health["body"] = {"status": "ok", "delib_active": 1, "delib_queued": 0}
    assert _busy(health["url"], HWAX_DELIB_PROBE_STRIKES=strikes) == (0, "1 0")


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


def test_늦게_답한_순간에도_에이전트_서버를_내리지_않는다(tmp_path, health):
    health["body"] = {"status": "ok", "delib_active": 2, "delib_queued": 1}
    health["delay"] = [LATE]
    out, calls, state, ledger = _restart(tmp_path, health["url"], HWAX_DELIB_PROBE_GAP_S="0")
    assert "down agent-server" not in calls and "up agent-server" not in calls, (calls, out)
    assert "DEFERRED=[ agent-server]" in out and "agent-server 재기동 건너뜀" in ledger and state is None
    assert "옛 판" not in out, "늦게 답한 새 판을 옛 판이라고 말하지 않는다"


def test_매달린_서버는_재기동하되_옛_판이라고_말하지_않는다(tmp_path, health):
    """종전에는 이 갈래가 '/health 가 도는 심의 수를 싣지 않는다(옛 판)' 로 찍혔다 — 수를 싣는 새 판이 늦게 답했을 뿐인데."""
    health["body"] = {"status": "ok", "delib_active": 2, "delib_queued": 1}
    health["delay"] = [LATE]
    out, calls, _, ledger = _restart(tmp_path, health["url"], HWAX_DELIB_PROBE_STRIKES="1", HWAX_DELIB_PROBE_GAP_S="0")
    assert "down agent-server" in calls and "up agent-server" in calls, (calls, out)
    assert "옛 판" not in out and "연속" in out and "답하지 않았다" in out, out
    assert "건너뜀" not in out and ledger == ""


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


# ── §2 deploy-all-from-drive — 포털·nginx 를 내리기 전에도 묻는다 ─────────────────────────────────
# 웹 심의도 리스크 패널도 nginx → 포털 릴레이를 거쳐 에이전트 서버의 스트림을 구독한다. 에이전트 서버만 보호하던 동안에는
# 포털 커밋이 하나라도 있는 update-all 이 §2 에서 포털·nginx 를 내려 구독을 전부 끊었다 — 리스크 잡은 engine_stream_cut 으로 멈춰
# 사람이 재개해야 하고, 엔진이 끝까지 돌린 심의의 결과는 원장에 못 들어가 패널을 처음부터 다시 돌린다. 그런 뒤 §4 는 구독자를
# 이미 잃은 심의를 보고 '재기동하면 전부 끊긴다' 며 에이전트 서버를 건너뛰었다.
#
# 구획을 **원문 그대로** 임시 포털 리포에서 돌린다. stop·start·images-from-drive·gen-nginx-conf 와 apptainer 는 부른 사실만 적는
# 대역이다. ⚠ 실물을 건드리면 안 된다(상대경로 하네스가 실 apptainer 로 dev nginx 를 내린 사고가 있었다 — 2026-09-28).
#   · 하네스는 임시 디렉터리에서 돌고(cd 가 실패해도 상대경로가 실 리포로 가지 않는다) 경로는 전부 절대경로다.
#   · apptainer 가 대역으로 잡히는지 구획을 돌리기 **전에** 확인하고, 아니면 97 로 멈춘다.
#   · 포털·nginx·에이전트 서버의 주소(8723·8088·9009)는 지어낸 서버로 바꾼다 — 안 바뀌면 시험이 그 자리에서 실패한다.
DEPLOY = (ROOT / "infra/scripts/deploy-all-from-drive.sh").read_text(encoding="utf-8")
_PORTAL_HEALTH, _AGENT_HEALTH = "http://127.0.0.1:8723/health", "http://127.0.0.1:9009/health"
DEAD = "http://127.0.0.1:9/health"


def _deploy_common() -> str:
    """지문·설정 읽기·묻는 함수 — lib 소싱 줄 바로 아래부터 포털 구획 앞까지(lib 는 하네스가 절대경로로 소싱한다)."""
    i = DEPLOY.index('HWAX_RESTART_STATE_DIR="${HWAX_RESTART_STATE_DIR:-')
    return DEPLOY[i:DEPLOY.index("# ── 1. Portal (the hub)", i)]


def _portal_block() -> str:
    i = DEPLOY.index("if want portal; then\n")
    return DEPLOY[i:DEPLOY.index("# ── 2. MX White Paper", i)]


def _nginx_block() -> str:
    i = DEPLOY.index('if [ "${NO_NGINX_REFRESH:-0}" != "1" ] && [ -d "$PORTAL_DIR" ]; then\n')
    return DEPLOY[i:DEPLOY.index("# ── Health summary", i)]


def _deploy(tmp_path: Path, block: str, agent_url: str, portal_url: str, nginx_port: int, last_fp: dict[str, str], **env):
    """deploy-all 의 한 구획을 임시 포털 리포에서 돌린다 → (화면, 대역이 받은 호출, 남은 기준 지문, 장부, skip 으로 센 줄)."""
    repo = tmp_path / "portal"; scripts = repo / "infra/scripts"; scripts.mkdir(parents=True, exist_ok=True)
    (repo / "infra/nginx").mkdir(exist_ok=True)
    log = tmp_path / "calls.log"; log.write_text("")
    ledger = tmp_path / "ledger"; ledger.write_text("")
    failed = tmp_path / "failed"; failed.write_text("")
    st = tmp_path / "state"; st.mkdir(exist_ok=True)
    for name, fp in last_fp.items():
        (st / name).write_text(fp + "\n")
    (repo / "infra/.env").write_text(f"HTTP_PORT={nginx_port}\n")
    for name in ("images-from-drive.sh", "stop.sh", "start.sh"):
        (scripts / name).write_text(f'#!/usr/bin/env bash\necho "{name}" >> "{log}"\nexit 0\n'); (scripts / name).chmod(0o755)
    # conf 생성기 대역 — 새 conf 를 쓴다. NG_SAME=1 이면 '마지막으로 띄운 뒤 conf 가 그대로' 인 박스를 만든다(그 지문을 기준으로 적는다)
    (scripts / "gen-nginx-conf.sh").write_text(
        f'#!/usr/bin/env bash\necho "gen-nginx-conf.sh" >> "{log}"\necho "conf $RANDOM" > "{repo}/infra/nginx/hwax.conf"\n'
        f'if [ "${{NG_SAME:-0}}" = 1 ]; then . "{LIBDIR}/change-detect.sh"\n'
        f'  hwax_fp "{repo}/infra/nginx/hwax.conf" "{repo}/infra/tls/hwax.crt" "{repo}/infra/tls/hwax.key" > "{st}/nginx"; fi\n')
    (scripts / "gen-nginx-conf.sh").chmod(0o755)
    stubbin = tmp_path / "bin"; stubbin.mkdir(exist_ok=True)
    (stubbin / "apptainer").write_text(f'#!/usr/bin/env bash\necho "apptainer $*" >> "{log}"\nexit 0\n'); (stubbin / "apptainer").chmod(0o755)
    body = (_deploy_common() + 'RESTART="${NO_RESTART:-0}"\n' + block)
    assert _AGENT_HEALTH in body, "심의 수를 묻는 주소는 에이전트 서버의 health 다"
    body = body.replace(_AGENT_HEALTH, agent_url).replace(_PORTAL_HEALTH, portal_url)
    assert "127.0.0.1:8723" not in body and "127.0.0.1:9009" not in body, "실물 주소가 남았다 — 하네스가 떠 있는 서비스를 두드린다"
    script = (f'set -euo pipefail\ncd "{tmp_path}"\n'
              f'[ "$(command -v apptainer)" = "{stubbin}/apptainer" ] || {{ echo "HARNESS: apptainer 가 대역이 아니다" >&2; exit 97; }}\n'
              f'PORTAL_DIR="{repo}"; DEPLOY_FAILED_FILE="{failed}"\n'
              f'[ "$(cd "$PORTAL_DIR" && pwd)" = "{repo}" ] || {{ echo "HARNESS: 임시 리포로 못 들어간다" >&2; exit 97; }}\n'
              f'[ "$(sed -n "s/^HTTP_PORT=//p" "$PORTAL_DIR/infra/.env")" = "{nginx_port}" ] || exit 97\n'
              'want() { true; }; hr() { echo "── $*"; }; ok() { echo "OK:$*"; }\n'
              'skip() { echo "SKIP:$*"; printf "%s\\n" "$*" >> "$DEPLOY_FAILED_FILE"; }\n'
              'git_update() { echo "  · git: aaa → bbb (reset to origin/main)"; }; set_remote() { :; }\n'
              f'{LIBS}export HWAX_RESTART_STATE_DIR="{st}" HWAX_SKIP_LEDGER="{ledger}" HWAX_WAIT_DOWN_MAX=1 HWAX_WAIT_UP_MAX=1\n'
              f'{body}\necho "END"\n')
    r = _sh(script, PATH=f'{stubbin}:{os.environ["PATH"]}', **env)
    assert r.returncode != 97, r.stderr
    assert "END" in r.stdout, r.stdout + r.stderr
    state = {f.name: f.read_text().strip() for f in st.iterdir()}
    return r.stdout + r.stderr, log.read_text().splitlines(), state, ledger.read_text(), failed.read_text()


def _port(url: str) -> int:
    return int(url.split(":")[2].split("/")[0])


def test_심의가_돌면_포털과_nginx_를_내리지_않는다(tmp_path, health):
    """**이 시험이 이 구획의 이유다** — 지문이 바뀌었어도(포털 커밋) stop·start 가 불리지 않는다. 이미지도 받지 않는다 —
    받으면 떠 있는 인스턴스 밑의 SIF 가 제자리에서 덮이고 옛 백엔드가 새 SPA 를 낸다. 지문은 그대로라 다음 실행이 다시 본다."""
    health["body"] = {"status": "ok", "delib_active": 1, "delib_queued": 2}
    out, calls, state, ledger, failed = _deploy(tmp_path, _portal_block(), health["url"], health["url"], _port(health["url"]),
                                                {"portal": "old-fp"})
    assert calls == [], f"대역이 불렸다 — {calls}"
    line = next(ln for ln in out.splitlines() if "○" in ln)
    assert "포털·nginx 재기동 건너뜀" in line and "심의 1건 진행 중, 2건 대기" in line and "engine_stream_cut" in line
    assert "AGENT_RESTART_FORCE=1" in out
    assert "포털·nginx 재기동 건너뜀" in ledger, "update-all 의 마지막 요약에도 다시 나온다"
    assert state == {"portal": "old-fp"}, "미룬 재기동의 지문을 적으면 새 코드가 영영 안 올라간다"
    assert "OK:portal up" not in out, "올라왔다고 말하지 않는다"
    assert "SKIP:" not in out and failed == "", "실패가 아니다 — skip 으로 세면 deploy-all 이 4 로 끝나고 update-all 이 실패로 적는다"


@pytest.mark.parametrize("case", ["심의 없음", "옛 판(수를 싣지 않는다)", "강행", "포털이 내려가 있다", "내리지 않고 띄우기만(NO_RESTART=1)"])
def test_심의가_없거나_모르거나_강행하면_포털을_종전대로_재기동한다(tmp_path, health, case):
    health["body"] = {"심의 없음": {"status": "ok", "delib_active": 0, "delib_queued": 0},
                      "옛 판(수를 싣지 않는다)": {"status": "ok"}}.get(case, {"delib_active": 2, "delib_queued": 1})
    env = {"강행": {"AGENT_RESTART_FORCE": "1"}, "내리지 않고 띄우기만(NO_RESTART=1)": {"NO_RESTART": "1"}}.get(case, {})
    portal = DEAD if case == "포털이 내려가 있다" else health["url"]      # 내려가 있으면 끊을 구독이 없다 — 띄워야 한다
    out, calls, _, ledger, _ = _deploy(tmp_path, _portal_block(), health["url"], portal, _port(health["url"]), {"portal": "old-fp"}, **env)
    want = ["images-from-drive.sh", "start.sh"] if case.startswith("내리지 않고") else ["images-from-drive.sh", "stop.sh", "start.sh"]
    assert calls == want, (calls, out)
    assert "○" not in out and ledger == "", out


def test_심의가_돌면_conf_가_바뀌어도_nginx_를_내리지_않는다(tmp_path, health):
    """리스크 앱은 nginx 를 거쳐 포털에 붙는다 — 포털 구획이 안 도는 실행(`deploy-all-from-drive.sh <다른 서비스>`)에서도
    끝의 라우팅 갱신이 nginx 를 내린다. conf 는 만들어 두고(nginx 는 뜰 때만 읽는다) 내리는 것만 미룬다."""
    health["body"] = {"delib_active": 1, "delib_queued": 0}
    out, calls, state, ledger, failed = _deploy(tmp_path, _nginx_block(), health["url"], health["url"], _port(health["url"]),
                                                {"nginx": "old-fp"})
    assert calls == ["gen-nginx-conf.sh"], f"conf 는 만들고 nginx 는 건드리지 않는다 — {calls}"
    line = next(ln for ln in out.splitlines() if "○" in ln)
    assert "nginx 재기동 건너뜀" in line and "심의 1건 진행 중, 0건 대기" in line and "nginx 재기동 건너뜀" in ledger
    assert state == {"nginx": "old-fp"} and "reloaded" not in out and "SKIP:" not in out and failed == ""


@pytest.mark.parametrize("body,env", [({"delib_active": 0, "delib_queued": 0}, {}), ({"status": "ok"}, {}),
                                      ({"delib_active": 1, "delib_queued": 0}, {"AGENT_RESTART_FORCE": "1"})])
def test_심의가_없거나_모르거나_강행하면_nginx_를_종전대로_내렸다_올린다(tmp_path, health, body, env):
    health["body"] = body
    out, calls, _, ledger, _ = _deploy(tmp_path, _nginx_block(), health["url"], health["url"], _port(health["url"]),
                                       {"nginx": "old-fp"}, **env)
    assert calls == ["gen-nginx-conf.sh", "apptainer instance stop hwax_nginx", "start.sh"], (calls, out)
    assert "○" not in out and ledger == ""


def test_conf_가_그대로면_심의가_돌아도_미뤘다고_말하지_않는다(tmp_path, health):
    """갈아 끼울 것이 없으면 사이클이 스스로 생략한다 — 그때까지 ○ 를 찍으면 심의가 도는 동안의 모든 실행이 '미뤘다' 고 말한다."""
    health["body"] = {"delib_active": 3, "delib_queued": 0}
    out, calls, _, ledger, failed = _deploy(tmp_path, _nginx_block(), health["url"], health["url"], _port(health["url"]),
                                            {}, NG_SAME="1")
    assert calls == ["gen-nginx-conf.sh"] and "○" not in out and ledger == "" and failed == "", (calls, out)
    assert "재기동 생략" in out


def test_deploy_all_의_포털과_nginx_재기동은_전부_심의를_묻고_난_뒤다():
    """재기동 자리가 둘이다(포털 구획 · 끝의 nginx 갱신) — 한 곳만 묻으면 다른 길에서 같은 절단이 난다. 셋째 자리가 생기면 여기서 걸린다."""
    import re

    sites = [m.start() for m in re.finditer(r"hwax_restart_cycle (?:portal|nginx) ", DEPLOY)]
    assert len(sites) == 2, "포털·nginx 를 내리는 자리가 늘었다 — 그 자리도 _delib_hold 를 지나게 하고 이 수를 고친다"
    for block, name in ((_portal_block(), "portal"), (_nginx_block(), "nginx")):
        assert block.index("_delib_hold ") < block.index(f"hwax_restart_cycle {name} "), f"{name}: 내리기 전에 묻지 않는다"
    pb = _portal_block()
    assert pb.index("_delib_hold ") < pb.index("./infra/scripts/images-from-drive.sh"), (
        "묻는 자리는 이미지를 받기 전이어야 한다 — 받은 뒤에 미루면 떠 있는 인스턴스 밑의 SIF 가 이미 덮였다")
    assert DEPLOY.index("lib/delib-busy.sh") < DEPLOY.index("_delib_hold() {") and DEPLOY.index("lib/skip-ledger.sh") < DEPLOY.index("_delib_hold() {")


def test_deploy_all_의_강행_손잡이가_사용법에_적혀_있다():
    head = DEPLOY[:DEPLOY.index("set -euo pipefail")]
    assert "AGENT_RESTART_FORCE=1 ./infra/scripts/deploy-all-from-drive.sh" in head and "○" in head
    ua_head = UA[:UA.index("set -uo pipefail")]
    assert "§2" in ua_head and "포털·nginx" in ua_head, "update-all 의 사용법이 §2 도 건너뛴다는 것을 말한다"


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


# ── update-forges — 에이전트 서버의 start.sh 가 스스로 건너뛴 것(3)을 실패로 세지 않는다 ─────────────────────
FORGES = (ROOT / "infra/scripts/update-forges.sh").read_text(encoding="utf-8")


@pytest.mark.parametrize("rc,failed,said", [(0, "0", ""), (3, "0", "○"), (1, "1", "✗"), (127, "1", "✗")])
def test_update_forges_는_건너뛴_재기동을_실패로_세지_않는다(tmp_path, rc, failed, said):
    """짝 — HWAXAgentServer 의 start.sh 는 도는·줄 선 심의가 있으면 인스턴스를 내리지 않고 3 으로 나간다. update-forges(chat ·
    restart)는 그 스크립트를 직접 부른다 — 3 을 실패로 세면 '○ 재기동 건너뜀' 바로 아래에 '✗ 재기동 실패' 가 찍히고 실행이 실패로 끝난다."""
    i = FORGES.index("restart_agent() {")
    fn = FORGES[i:FORGES.index("\n}\n", i) + 3]
    agent = tmp_path / "HWAXAgentServer"; agent.mkdir()
    (agent / "start.sh").write_text(f'#!/usr/bin/env bash\necho "ARG:$1" > "{tmp_path}/called"\nexit {rc}\n'); (agent / "start.sh").chmod(0o755)
    r = _sh(f'set -uo pipefail\nFAIL=0\n{fn}\nrestart_agent "{agent}"\necho "FAIL=$FAIL"')
    assert r.returncode == 0 and not r.stderr, r.stderr
    assert (tmp_path / "called").read_text().strip() == "ARG:-d", "백그라운드로 띄운다(종전 그대로)"
    assert f"FAIL={failed}" in r.stdout, r.stdout
    assert (said in r.stdout) if said else (r.stdout.strip() == "FAIL=0"), r.stdout
    if rc == 3:
        assert "✗" not in r.stdout and "그대로 둔다" in r.stdout


def test_update_forges_의_에이전트_재기동은_전부_그_함수를_지난다():
    """재기동 자리가 둘이다(chat · restart) — 한 곳만 고치면 다른 길에서 같은 거짓 실패가 난다."""
    assert FORGES.count('restart_agent "$aserver"') == 2
    assert FORGES.count("./start.sh -d") == 1, "start.sh 를 직접 부르는 곳은 그 함수 하나다"
