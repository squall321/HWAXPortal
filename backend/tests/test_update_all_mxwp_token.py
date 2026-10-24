# update-all 이 게이트웨이의 죽은 MX 백서 서비스 토큰을 알아보고 재프로비저닝하는지(docs/mxwp-wiki MW-D14)
"""키(mx-white-paper)는 config 에 있고 토큰만 죽은 경우는 calc_missing 이 못 본다 — MXWP 시험이 api_tokens 를 비우자(2026-10-24 dev)
도구는 뜨고 신원 없는 호출만 401 인 채 남았다. `_mxwp_token_drift` 가 그 토큰으로 MXWP `/api/v1/me` 를 물어 401 · 403 이면 방아쇠를 당긴다.
MXWP 가 안 닿으면 방아쇠로 삼지 않는다 — 그러면 내려가 있는 동안 매 실행 재프로비저닝이 헛돈다."""
import http.server
import json
import subprocess
import threading
from pathlib import Path

import pytest

UA_PATH = Path(__file__).resolve().parents[2] / "infra" / "scripts" / "update-all.sh"
UA = UA_PATH.read_text(encoding="utf-8")


def _fn(name: str) -> str:
    s = UA[UA.index(f"{name}() {{"):]
    return s[:s.index("\n}\n") + 3]


@pytest.fixture()
def mxwp():
    """토큰을 보고 200 · 401 을 답하는 가짜 MXWP — `Bearer mxwp_alive` 만 산 토큰이다."""
    seen = []

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            seen.append((self.path, self.headers.get("Authorization")))
            ok = self.path == "/api/v1/me" and self.headers.get("Authorization") == "Bearer mxwp_alive"
            self.send_response(200 if ok else 401)
            self.end_headers()

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}", seen
    srv.shutdown()


def _drift(tmp_path: Path, cfg: dict) -> int:
    f = tmp_path / "gateway_config.json"
    f.write_text(json.dumps(cfg), encoding="utf-8")
    r = subprocess.run(["bash", "-c", f'{_fn("_mxwp_token_drift")}\n_mxwp_token_drift "{f}"; echo "rc=$?"'],
                       capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
    assert not r.stderr, r.stderr
    return int(r.stdout.strip().rsplit("rc=", 1)[1])


def _cfg(base: str, mcp: str | None, rest_inject: str | None = None) -> dict:
    d: dict = {"rest": {"mx-white-paper": {"base": base}}}
    if mcp is not None:
        d["mx-white-paper"] = {"url": "http://127.0.0.1:8765/mcp", "headers": {"Authorization": f"Bearer {mcp}"}}
    if rest_inject is not None:
        d["rest"]["mx-white-paper"]["inject"] = {"header": "Authorization", "value": f"Bearer {rest_inject}"}
    return d


def test_죽은_서비스_토큰이면_방아쇠다(tmp_path, mxwp):
    base, seen = mxwp
    assert _drift(tmp_path, _cfg(base, "mxwp_dead")) == 0
    assert _drift(tmp_path, _cfg(base, "mxwp_alive", rest_inject="mxwp_dead")) == 0, "REST 주입 토큰만 죽어도 어긋남"
    assert ("/api/v1/me", "Bearer mxwp_dead") in seen


def test_산_토큰이거나_판정할_수_없으면_조용하다(tmp_path, mxwp):
    base, _ = mxwp
    assert _drift(tmp_path, _cfg(base, "mxwp_alive")) == 1
    assert _drift(tmp_path, _cfg(base, "mxwp_alive", rest_inject="mxwp_alive")) == 1
    assert _drift(tmp_path, {"rest": {}}) == 1, "항목이 없으면 calc_missing 몫이다"
    assert _drift(tmp_path, _cfg("http://127.0.0.1:9", "mxwp_dead")) == 1, \
        "MXWP 가 안 닿으면 방아쇠가 아니다 — 내려가 있는 동안 매 실행 재프로비저닝이 헛돈다"


def test_방아쇠는_MXWP_가_떠_있을_때만_당기고_재프로비저닝_뒤에도_다시_본다():
    pre = UA[UA.index("# MX 백서 서비스 토큰 — 키는 있고 토큰만 죽은 경우"):]
    pre = pre[:pre.index("\n  fi\n") + 6]
    assert '[ "${MXWP_UP:-0}" = 1 ]' in pre and '_mxwp_token_drift "$GW_DIR/gateway_config.json"' in pre
    assert 'MISSING="${MISSING:+$MISSING }mx-white-paper"' in pre
    assert 'STILL="${STILL:+$STILL }mx-white-paper(서비스 토큰이 여전히 401' in UA, "재프로비저닝 뒤에도 죽어 있으면 말한다"
    fn = _fn("_mxwp_token_drift")
    assert "sys.argv" in fn and "$ARP" not in fn and "Bearer" in fn
    assert "curl" not in fn, "토큰을 argv 에 싣지 않는다 — 파이썬이 config 에서 읽어 헤더로만 쓴다"
