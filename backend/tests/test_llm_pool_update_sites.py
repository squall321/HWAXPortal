# update-sites 가 LLM 요청이 라우터를 지나는 동안 llm-router 를 재기동하지 않는지 — 확실히 바쁠 때만 미루고 ○ 로 남기는지
"""왜 — 라우터를 내리면 그 순간 라우터를 지나던 스트림(챗·심의 좌석·카드 대조)이 전부 끊기고 라우터는 다시 보내지 않는다(docs/llm-pool
LP-D3). 에이전트 서버의 심의 미룸과 같은 규율로 막는다(PLAN §4) — /health 의 inflight 가 **확실한** 양의 정수일 때만 미루고, 지문을 적지
않고, ○ 로 남기고, 실행은 3 으로 끝난다. 모르면(내려가 있다·옛 판·답이 이상하다) 그대로 재기동한다 — 죽은 라우터를 다시 띄워야 한다.

restart_svc 구획을 **원문 그대로** 떼어 대역 services.sh 로 돌린다(실물 서비스는 건드리지 않는다). 라우터 /health 는 지어낸 서버다.
"""
import http.server
import json
import os
import re
import socket
import subprocess
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LIBDIR = ROOT / "infra/scripts/lib"
UPDATE_SITES = (ROOT / "infra/scripts/update-sites.sh").read_text(encoding="utf-8")
LIBS = "".join(f'. "{LIBDIR}/{n}"\n' for n in ("change-detect.sh", "skip-ledger.sh", "delib-busy.sh", "llm-pool.sh"))


@pytest.fixture()
def router():
    state = {"body": {"status": "ok", "upstreams_total": 2, "upstreams_up": 2, "inflight": 0,
                      "models": {"match": True}, "config_mtime": 1.0}, "hits": 0}

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


def _dead_url() -> str:
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close()
    return f"http://127.0.0.1:{p}/health"


def _sh(script: str, **env) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=90,
                          env={"PATH": os.environ["PATH"], "HOME": os.environ.get("HOME", "/tmp"), **env})


def _restart_svc_block() -> str:
    i = UPDATE_SITES.index('SKIPPED_RESTART=""')
    return UPDATE_SITES[i:UPDATE_SITES.index("# 1) 포털 먼저", i)]


def _svc_stub(tmp_path: Path, url: str, log: Path) -> Path:
    svc = tmp_path / "svc.sh"
    svc.write_text(f'#!/usr/bin/env bash\necho "$*" >> "{log}"\n'
                   'case "$1" in update) echo "  · $2  skip (update:false)";; fp) echo f-new;; status) echo "  ✓ up $2";;\n'
                   f'  health) echo {url};; enabled) exit 0;; esac\nexit 0\n')
    svc.chmod(0o755)
    return svc


def _restart(tmp_path: Path, url: str, name: str = "llm-router", **env):
    """restart_svc 를 대역 services.sh 로 돌린다 → (화면, services.sh 가 받은 호출, 기록된 지문, 장부)."""
    log = tmp_path / "svc.log"; st = tmp_path / "state"; st.mkdir(exist_ok=True); ledger = tmp_path / "ledger"
    log.unlink(missing_ok=True); ledger.write_text("")
    svc = _svc_stub(tmp_path, url, log)
    script = (f'set -uo pipefail\nSVC="{svc}"\n{LIBS}export HWAX_RESTART_STATE_DIR="{st}" HWAX_WAIT_DOWN_MAX=1 HWAX_WAIT_UP_MAX=1 '
              f'HWAX_SKIP_LEDGER="{ledger}"\nshow_cause() {{ :; }}\n{_restart_svc_block()}\n'
              f'restart_svc "{name}"; echo "rc=$?"; echo "DEFERRED=[$DEFERRED_RESTART] LLM=[$DEFERRED_LLM]"')
    r = _sh(script, **env)
    state = (st / name).read_text().strip() if (st / name).exists() else None
    return r.stdout + r.stderr, (log.read_text().splitlines() if log.exists() else []), state, ledger.read_text()


def test_요청이_지나는_동안은_라우터를_내리지_않는다(tmp_path, router):
    """**이 시험이 이 파일의 이유다** — down·up 이 불리지 않고, 지문도 적지 않는다(다음 실행이 다시 본다)."""
    router["body"]["inflight"] = 3
    out, calls, state, ledger = _restart(tmp_path, router["url"])
    assert "down llm-router" not in calls and "up llm-router" not in calls, calls
    assert state is None, "미룬 재기동의 지문을 적으면 새 라우터 코드가 영영 안 올라간다"
    assert "rc=0" in out and "LLM=[ llm-router]" in out and "DEFERRED=[]" in out, out
    line = next(ln for ln in out.splitlines() if "○" in ln)
    assert "llm-router 재기동 미룸" in line and "LLM 요청 3건" in line
    assert "LLM_ROUTER_RESTART_FORCE=1" in out
    name = ledger.split("\t")[0]
    assert name == "llm-router 재기동 미룸", ledger
    assert not re.search(r"(재기동|재프로비저닝) 건너뜀$", name), \
        "update-all 1h 끝맺음이 이 이름을 심의 때문에 미룬 재기동으로 읽으면 새 패널을 멈춘 채 둔다(이 미룸은 심의와 무관하다)"


@pytest.mark.parametrize("body", [
    {"status": "ok", "upstreams_total": 2, "upstreams_up": 2, "inflight": 0},       # 비었다
    {"status": "ok", "upstreams_total": 2, "upstreams_up": 2},                       # 옛 판(수를 싣지 않는다)
    {"status": "ok", "upstreams_total": 2, "inflight": "많음"},
    {"status": "ok", "upstreams_total": 2, "inflight": True},
    {"status": "ok", "service": "다른 앱", "inflight": 5},                           # 라우터의 답이 아니다
    "<html>502</html>", None,
])
def test_비었거나_모르면_종전대로_재기동한다(tmp_path, router, body):
    router["body"] = body
    out, calls, _, ledger = _restart(tmp_path, router["url"])
    assert "down llm-router" in calls and "up llm-router" in calls, (calls, out)
    assert "미룸" not in out and ledger == ""


def test_내려간_라우터는_띄운다(tmp_path):
    out, calls, _, ledger = _restart(tmp_path, _dead_url())
    assert "down llm-router" in calls and "up llm-router" in calls and ledger == "", (calls, out)


def test_강행하면_요청이_지나도_재기동한다(tmp_path, router):
    router["body"]["inflight"] = 4
    out, calls, _, ledger = _restart(tmp_path, router["url"], LLM_ROUTER_RESTART_FORCE="1")
    assert "down llm-router" in calls and "up llm-router" in calls and ledger == "" and "미룸" not in out, (calls, out)


def test_다른_서비스는_라우터를_묻지_않는다(tmp_path, router):
    """게이트웨이·에이전트 서버의 재기동 판단에 라우터의 도는 요청이 끼면 배포가 안 된다 — 묻는 것은 llm-router 뿐이다."""
    router["body"]["inflight"] = 9
    out, calls, _, _ = _restart(tmp_path, router["url"], name="mcp-gateway")
    assert "down mcp-gateway" in calls and "up mcp-gateway" in calls and "미룸" not in out


def _driver(tmp_path: Path, url: str, rest: str = "llm-router", **env) -> subprocess.CompletedProcess:
    """restart_svc + 나머지 루프 + 요약까지 — update-sites 의 종료코드를 본다."""
    st = tmp_path / "state"; st.mkdir(exist_ok=True); ledger = tmp_path / "ledger"; ledger.write_text("")
    svc = _svc_stub(tmp_path, url, tmp_path / "svc.log")
    i = UPDATE_SITES.index('SKIPPED_RESTART=""')
    script = (f'set -uo pipefail\nSVC="{svc}"\n{LIBS}export HWAX_RESTART_STATE_DIR="{st}" HWAX_WAIT_DOWN_MAX=1 HWAX_WAIT_UP_MAX=1 '
              f'HWAX_SKIP_LEDGER="{ledger}"\nHAS_PORTAL=0; PORTAL=portal; REST="{rest}"; TARGETS="{rest}"\nshow_cause() {{ :; }}\n'
              f'{UPDATE_SITES[i:]}')
    return _sh(script, **env)


def test_미루기만_한_실행은_3으로_끝나고_사유를_다시_말한다(tmp_path, router):
    """0 이면 '전부 재기동됐다' 와 구별이 안 된다 — update-all 1i 는 3 을 미룸으로 읽는다(실패로 세지 않는다)."""
    router["body"]["inflight"] = 2
    r = _driver(tmp_path, router["url"])
    assert r.returncode == 3, r.stdout + r.stderr
    summary = [ln for ln in r.stdout.splitlines() if ln.startswith("▶ ○")]
    assert len(summary) == 1 and "LLM 요청이 라우터를 지나고 있다" in summary[0] and "LLM_ROUTER_RESTART_FORCE=1" in summary[0], summary
    assert "심의가 돌거나" not in r.stdout, "에이전트 서버의 요약(심의·AGENT_RESTART_FORCE)으로 말하지 않는다"
    idle = tmp_path / "idle"; idle.mkdir()
    router["body"]["inflight"] = 0
    assert _driver(idle, router["url"]).returncode != 3, "비었으면 미룬 것이 없다"


def test_물려받은_라우터_포트를_services_sh_에_넘기지_않는다(tmp_path):
    """**2라운드 LOW 6 회귀** — services.py down 은 부른 쪽의 환경을 llm-router.sh stop 에 넘기고, stop 은 환경의 LLM_ROUTER_PORT 가 먼저다.
    운영자 셸에 옛 포트가 export 돼 있으면 update-sites llm-router 가 옛 포트의 라우터(미룬 서비스가 아직 쓸 수 있다)를 내리고 지금 포트의
    라우터는 못 내렸다. update-sites 머리가 그 값을 버린다 — services.sh 가 받는 환경에 없다.
    update-sites.sh 를 **임시 포털에 복사해** 통째로 돌린다 — services.sh·services.py·매니페스트는 그 포털의 대역이다(실물 서비스를 건드리지 않게
    — 스크립트가 서비스 경로를 자기 자리에서 유도하는지 먼저 본다)."""
    src = UPDATE_SITES
    for line in ('ROOT="$(cd "$(dirname "$0")/../.." && pwd)"', 'SVC="$ROOT/infra/scripts/services.sh"',
                 'SVCPY="$ROOT/infra/scripts/services.py"', 'MANIFEST="$ROOT/infra/services.yaml"'):
        assert line in src, f"update-sites 가 서비스 경로를 자기 자리에서 유도하지 않는다 — 복사본이 실물을 부를 수 있다: {line}"
    portal = tmp_path / "HWAXPortal"; scripts = portal / "infra/scripts"; (scripts / "lib").mkdir(parents=True)
    (scripts / "update-sites.sh").write_text(src, encoding="utf-8")
    for n in ("change-detect.sh", "skip-ledger.sh", "delib-busy.sh", "llm-pool.sh"):
        (scripts / "lib" / n).write_text((LIBDIR / n).read_text(encoding="utf-8"), encoding="utf-8")
    log = tmp_path / "svc.log"
    (scripts / "services.sh").write_text(
        f'#!/usr/bin/env bash\necho "$* port=${{LLM_ROUTER_PORT-없음}}" >> "{log}"\n'
        'case "$1" in update) echo "  · $2  (대역) skip";; fp) echo f-new;; status) echo "  ✓ up $2";;\n'
        f'  health) echo {_dead_url()};; enabled) exit 0;; esac\nexit 0\n')
    (scripts / "services.sh").chmod(0o755)
    (scripts / "services.py").write_text("from pathlib import Path\nPARENT = Path('/nonexistent')\n\ndef resolve_dir(s):\n    return None\n")
    (portal / "infra/services.yaml").write_text("services:\n  - name: llm-router\n")
    ledger = tmp_path / "ledger"; ledger.write_text("")
    r = subprocess.run(["bash", str(scripts / "update-sites.sh"), "llm-router"], capture_output=True, text=True, timeout=120,
                       env={"PATH": os.environ["PATH"], "HOME": str(tmp_path), "LLM_ROUTER_PORT": "9555",
                            "HWAX_RESTART_STATE_DIR": str(tmp_path / "state"), "HWAX_WAIT_DOWN_MAX": "1", "HWAX_WAIT_UP_MAX": "1",
                            "HWAX_SKIP_LEDGER": str(ledger)})
    calls = log.read_text().splitlines() if log.exists() else []
    assert calls and all(c.endswith(" port=없음") for c in calls), (calls, r.stdout + r.stderr)
    assert "down llm-router port=없음" in calls, (calls, r.stdout + r.stderr)


def test_사용법이_라우터_보호를_말한다():
    head = UPDATE_SITES[:UPDATE_SITES.index("# ── 대상 산출")]
    assert "LLM_ROUTER_RESTART_FORCE=1" in head and "llm-router" in head
    assert '. "$ROOT/infra/scripts/lib/llm-pool.sh"' in UPDATE_SITES
