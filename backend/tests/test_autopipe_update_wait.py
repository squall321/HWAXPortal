# update-all(deploy-all)이 포털을 내리기 직전에 자동 파이프라인 박자를 접는 _autopipe_quiesce 의 시험 — 지어낸 포털에 실제로 묻는다(AP-26)
"""고정하는 것.

  · 포털 구획의 _stop 이 stop.sh 앞에서 부른다(재기동이 정해진 뒤에만 — 지문이 같으면 묻지도 않는다).
  · 시크릿은 argv 가 아니라 curl -K - 로 싣고, 창구 주소는 포털 health 주소에서 짓는다(하네스가 health 주소 하나만 바꿔 끼운다).
  · 꺼진 박스 · 옛 포털(404)은 ○(장부), 못 기다림 · 비밀 없음 · 다른 답은 ⚠(장부 아님 · skip 아님) — 무엇이 와도 0 으로 끝나 포털은 내린다.
  · 떠 있지 않은 포털에는 묻지 않는다. 기다림 상한은 1800 에서 자르고 ttl 은 기다림 + 900(최대 3600)이다.
"""
from __future__ import annotations

import http.server
import json
import os
import re
import subprocess
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LIBDIR = ROOT / "infra/scripts/lib"
DEPLOY = (ROOT / "infra/scripts/deploy-all-from-drive.sh").read_text(encoding="utf-8")
TOKEN = "tok-for-quiesce-test"


def _fn(name: str) -> str:
    m = re.search(rf"(?ms)^{re.escape(name)}\(\) \{{[^\n]*\n.*?^\}}\n", DEPLOY)
    assert m, f"{name} 함수가 없다"
    return m.group(0)


@pytest.fixture()
def portal():
    """지어낸 포털 — /health 는 200, POST /internal/autopipe/quiesce 는 state 의 code · body 로 답하고 받은 것을 적는다."""
    state = {"code": 200, "body": {"enabled": True, "idle": True, "was_busy": False, "waited_s": 0.0}, "posts": []}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200 if self.path == "/health" else 404); self.end_headers()

        def do_POST(self):
            n = int(self.headers.get("content-length") or 0)
            state["posts"].append({"path": self.path, "auth": self.headers.get("authorization"),
                                   "body": json.loads(self.rfile.read(n) or b"{}")})
            if self.path != "/internal/autopipe/quiesce" or state["code"] == 404:
                self.send_response(404); self.end_headers(); return
            raw = json.dumps(state["body"]).encode()
            self.send_response(state["code"]); self.send_header("content-type", "application/json"); self.end_headers()
            self.wfile.write(raw)

        def log_message(self, *a):
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    state["health"] = f"http://127.0.0.1:{srv.server_address[1]}/health"
    yield state
    srv.shutdown(); srv.server_close()


def _quiesce(tmp_path: Path, health: str, *, token: str | None = TOKEN, **env) -> tuple[int, str, str]:
    repo = tmp_path / "portal"; (repo / "backend").mkdir(parents=True, exist_ok=True)
    (repo / "backend/.env").write_text(f"OTHER=1\nGATEWAY_SHARED_TOKEN={token}\n" if token else "OTHER=1\n")
    ledger = tmp_path / "ledger"; ledger.write_text("")
    script = (f'set -euo pipefail\n. "{LIBDIR}/change-detect.sh"\n. "{LIBDIR}/skip-ledger.sh"\nexport HWAX_SKIP_LEDGER="{ledger}"\n'
              f'{_fn("_envv")}{_fn("_autopipe_quiesce")}cd "{repo}"\n_autopipe_quiesce "{health}"\necho "END rc=$?"\n')
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=60,
                       env={"PATH": os.environ["PATH"], "HOME": os.environ.get("HOME", "/tmp"), **env})
    assert "END rc=0" in r.stdout, r.stdout + r.stderr
    return r.returncode, r.stdout + r.stderr, ledger.read_text()


def test_포털_구획은_내리기_직전에_묻는다():
    block = DEPLOY[DEPLOY.index("if want portal; then\n"):DEPLOY.index("# ── 2. MX White Paper")]
    stop = next(ln for ln in block.splitlines() if ln.strip().startswith("_stop()"))
    assert stop.index("_autopipe_quiesce http://127.0.0.1:8723/health") < stop.index("./infra/scripts/stop.sh"), stop
    fn = _fn("_autopipe_quiesce")
    assert "-K -" in fn and "Authorization: Bearer" in fn and "127.0.0.1:8723" not in fn, "시크릿은 argv 에 · 주소는 인자에서"
    ua = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")
    assert "HWAX_AUTOPIPE_WAIT_S=300" in ua.split("# 순서:", 1)[0], "update-all 머리의 손잡이 목록에 적는다"


def test_켜진_박스는_멈추고_기다린_뒤_간다(tmp_path, portal):
    _, out, ledger = _quiesce(tmp_path, portal["health"])
    (p,) = portal["posts"]
    assert p["path"] == "/internal/autopipe/quiesce" and p["auth"] == f"Bearer {TOKEN}"
    assert p["body"] == {"ttl_s": 1200, "wait_s": 300, "by": "update-all"}
    assert "새 박자를 멈췄다(도는 박자 없음)" in out and ledger == "" and "⚠" not in out
    assert TOKEN not in out, "비밀을 찍지 않는다"
    portal["body"] = {"enabled": True, "idle": True, "was_busy": True, "waited_s": 12.5}
    _, out, _ = _quiesce(tmp_path, portal["health"])
    assert "12.5초 기다렸다" in out


def test_기다림_상한은_1800_에서_자르고_ttl_은_3600_을_넘지_않는다(tmp_path, portal):
    _quiesce(tmp_path, portal["health"], HWAX_AUTOPIPE_WAIT_S="5000")
    _quiesce(tmp_path, portal["health"], HWAX_AUTOPIPE_WAIT_S="0")
    _quiesce(tmp_path, portal["health"], HWAX_AUTOPIPE_WAIT_S="abc")
    assert [p["body"]["wait_s"] for p in portal["posts"]] == [1800, 0, 300]
    assert [p["body"]["ttl_s"] for p in portal["posts"]] == [2700, 900, 1200]


@pytest.mark.parametrize("case", ["꺼진 박스", "옛 포털(404)"])
def test_안_켠_것은_동그라미로_장부에_남는다(tmp_path, portal, case):
    if case == "꺼진 박스":
        portal["body"] = {"enabled": False, "idle": True, "was_busy": False, "waited_s": 0}
    else:
        portal["code"] = 404
    _, out, ledger = _quiesce(tmp_path, portal["health"])
    assert "○" in out and "자동 파이프라인 박자 기다림" in ledger
    assert ("AUTO_PIPELINE_ENABLED=1" in out) if case == "꺼진 박스" else ("옛 판" in out)


@pytest.mark.parametrize("case", ["못 기다림", "비밀 없음", "403"])
def test_문제는_경고만_하고_그대로_간다(tmp_path, portal, case):
    if case == "못 기다림":
        portal["body"] = {"enabled": True, "idle": False, "was_busy": True, "waited_s": 300}
    elif case == "403":
        portal["code"] = 403
    _, out, ledger = _quiesce(tmp_path, portal["health"], token=None if case == "비밀 없음" else TOKEN)
    assert "⚠" in out and ledger == "" and "○" not in out
    if case == "비밀 없음":
        assert portal["posts"] == [], "비밀이 없으면 묻지 않는다"
    if case == "못 기다림":
        assert "HWAX_AUTOPIPE_WAIT_S" in out and "ra_outcome_unknown" in out
    if case == "403":
        assert "HTTP 403" in out and "GATEWAY_SHARED_TOKEN" in out


def test_떠_있지_않은_포털에는_묻지_않는다(tmp_path, portal):
    _, out, ledger = _quiesce(tmp_path, "http://127.0.0.1:9/health")
    assert portal["posts"] == [] and out.strip() == "END rc=0" and ledger == ""
