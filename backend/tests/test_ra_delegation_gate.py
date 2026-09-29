# RA 사용자 위임 배선 — update-all §6 점검(공유 시크릿 짝)과 wire 스크립트(값이 다르면 갈아 끼움)
#
# 2026-09-29 사고: 게이트웨이 config 의 portal.api_base 가 --force 로 사라져 게이트웨이가 포털에 묻지도 않았고,
# 연결을 등록한 사람의 RA 글이 서비스 토큰 주인 명의로 올라갔다. 게이트웨이는 이제 못 물으면 RA 쓰기를 거부하므로,
# 배포가 그 조회 경로(게이트웨이 GW_TOKEN = 포털 GATEWAY_SHARED_TOKEN)를 직접 확인해야 한다.
import http.server
import json
import os
import shutil
import subprocess
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
UA = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")
WIRE = ROOT / "infra/scripts/wire-gateway-shared-token.sh"


def _fn(name: str) -> str:
    s = UA[UA.index(f"{name}() {{"):]
    return s[:s.index("\n}\n") + 3]


def _gate_block() -> str:
    i = UA.index("  # ── RA 사용자 위임 — 게이트웨이가 포털에")
    return UA[i:UA.index("  # ste 관련 빨강이 하나라도 있으면", i)]


def _verdict(code: str) -> tuple[str, str]:
    r = subprocess.run(["bash", "-c", f'{_fn("_ra_conn_verdict")}\n_ra_conn_verdict "{code}"'],
                       capture_output=True, text=True)
    lvl, _, msg = r.stdout.rstrip("\n").partition("\t")
    return lvl, msg


def test_판정표는_포털_라우트의_세_코드를_가른다():
    assert _verdict("404")[0] == "ok"
    lvl, msg = _verdict("403")
    assert lvl == "fail" and "GATEWAY_SHARED_TOKEN" in msg and "wire-gateway-shared-token.sh" in msg
    lvl, msg = _verdict("503")
    assert lvl == "fail" and "없다" in msg and "wire-gateway-shared-token.sh" in msg
    for c in ("000", "200", "500"):
        assert _verdict(c)[0] == "fail", c                  # 모르는 응답을 통과로 읽지 않는다


def test_점검은_시크릿을_argv_에_싣지_않고_헬스게이트_안에서_돈다():
    blk = _gate_block()
    assert "-K -" in blk and "Bearer $" not in blk and "-H " not in blk
    assert UA.index('hr "6) 헬스게이트"') < UA.index("  # ── RA 사용자 위임 — 게이트웨이가 포털에")
    assert "hwax_skip" in blk, "RA 백엔드가 없는 박스는 건너뜀으로 적는다(안 켠 기능도 로그에)"


class _Portal(http.server.BaseHTTPRequestHandler):
    code = 404
    seen: list = []

    def do_GET(self):  # noqa: N802
        _Portal.seen.append((self.path, self.headers.get("Authorization")))
        self.send_response(_Portal.code); self.end_headers()

    def log_message(self, *a): pass


@pytest.fixture()
def portal():
    srv = http.server.HTTPServer(("127.0.0.1", 0), _Portal)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    _Portal.seen = []
    yield srv.server_address[1]
    srv.shutdown()


NEW_GW = "class _ConnLookupError(Exception):\n    pass\n"     # 새 판 게이트웨이의 표식(게이트웨이 b9cc6e7)


def _run_gate(tmp_path, port: int, cfg: dict | None, gateway_py: str = NEW_GW) -> str:
    gw = tmp_path / "HWAXMcpGateway"; gw.mkdir(exist_ok=True)
    (gw / "gateway.py").write_text(gateway_py)
    if cfg is not None:
        cfg = {"portal": {"jwks_url": f"http://127.0.0.1:{port}/.well-known/jwks.json"}, **cfg}
        (gw / "gateway_config.json").write_text(json.dumps(cfg))
    # 주소는 게이트웨이 config 에서 온다(jwks_url 을 시험 포털로) — 기본값 문자열이 쓰이면 진짜 :8723 에 닿으니 막는다
    blk = _gate_block().replace("http://127.0.0.1:8723", "http://127.0.0.1:1")
    script = ("ok(){ echo \"OK $*\"; }\nfail(){ echo \"FAIL $*\"; }\n"
              "hwax_skip(){ echo \"SKIP $1\"; }\n"
              f"{_fn('_ra_conn_verdict')}\nGW_DIR={gw}\n{blk}")
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return r.stdout + r.stderr


@pytest.mark.parametrize("code,want", [(404, "OK"), (403, "FAIL"), (503, "FAIL")])
def test_점검이_실제로_포털에_게이트웨이_토큰으로_묻는다(tmp_path, portal, code, want):
    _Portal.code = code
    out = _run_gate(tmp_path, portal, {"_gateway": {"token": "gw-tok-123"}, "reportarchive": {"url": "http://x/mcp"}})
    assert out.startswith(want), out
    path, auth = _Portal.seen[0]
    assert path == "/internal/connections/reportarchive?email=hwax-probe%40invalid"
    assert auth == "Bearer gw-tok-123", "curl 설정 줄이 깨지면 헤더가 안 간다 — 그러면 매번 503/403 이다"


def test_RA_백엔드가_없으면_묻지_않고_건너뜀으로_적는다(tmp_path, portal):
    out = _run_gate(tmp_path, portal, {"_gateway": {"token": "t"}})
    assert out.startswith("SKIP RA 사용자 위임 점검") and _Portal.seen == []
    (tmp_path / "none").mkdir()
    assert _run_gate(tmp_path / "none", portal, None).startswith("SKIP")    # 게이트웨이 config 자체가 없다
    assert _Portal.seen == []


# ── wire 스크립트: '있기만 하면' 건너뛰던 것 → 값이 다르면 갈아 끼운다 ──────────────────────────
def _wire_tree(tmp_path, env_text: str | None) -> Path:
    portal = tmp_path / "HWAXPortal"
    (portal / "infra/scripts").mkdir(parents=True); (portal / "backend").mkdir()
    shutil.copy2(WIRE, portal / "infra/scripts/wire-gateway-shared-token.sh")
    gw = tmp_path / "HWAXMcpGateway"; gw.mkdir()
    (gw / "gateway_config.json").write_text(json.dumps({"_gateway": {"token": "NEW"}, "portal": {}}))
    if env_text is not None:
        (portal / "backend/.env").write_text(env_text)
    return portal


def _wire(portal: Path, tmp_path) -> str:
    r = subprocess.run(["bash", str(portal / "infra/scripts/wire-gateway-shared-token.sh")],
                       capture_output=True, text=True, env={**os.environ, "HOME": str(tmp_path / "home")})
    assert r.returncode == 0, r.stderr
    return r.stdout


def test_wire_는_다른_값을_갈아_끼우고_나머지_줄은_그대로_둔다(tmp_path):
    p = _wire_tree(tmp_path, "A=1\n# GATEWAY_SHARED_TOKEN=commented\nGATEWAY_SHARED_TOKEN=OLD\nB=2\n")
    out = _wire(p, tmp_path)
    assert "갈아 끼웠다" in out
    assert (p / "backend/.env").read_text() == "A=1\n# GATEWAY_SHARED_TOKEN=commented\nGATEWAY_SHARED_TOKEN=NEW\nB=2\n"
    assert "이미 배선됨" in _wire(p, tmp_path)                     # 두 번째는 같다 — 멱등
    cfg = json.loads((tmp_path / "HWAXMcpGateway/gateway_config.json").read_text())
    assert cfg["portal"]["api_base"] == "http://127.0.0.1:8723"


def test_wire_는_마지막_활성_줄과_export_형태를_본다(tmp_path):
    p = _wire_tree(tmp_path, "GATEWAY_SHARED_TOKEN=NEW\nexport GATEWAY_SHARED_TOKEN='OLD'\n")
    assert "갈아 끼웠다" in _wire(p, tmp_path)                      # 마지막 줄이 이기므로 그것이 달랐다
    assert (p / "backend/.env").read_text() == "GATEWAY_SHARED_TOKEN=NEW\nexport GATEWAY_SHARED_TOKEN=NEW\n"
    p2 = _wire_tree(tmp_path / "q", "export GATEWAY_SHARED_TOKEN=\"NEW\"\n")
    assert "이미 배선됨" in _wire(p2, tmp_path)


def test_wire_는_없으면_덧붙인다(tmp_path):
    p = _wire_tree(tmp_path, "A=1")
    _wire(p, tmp_path)
    assert (p / "backend/.env").read_text().endswith("\nGATEWAY_SHARED_TOKEN=NEW\n")


def test_점검은_게이트웨이와_같은_규칙으로_주소를_정한다(tmp_path, portal):
    """api_base 가 있으면 그것, 없으면 jwks_url 의 origin — gateway.py _portal_api_base() 와 같다."""
    _Portal.code = 404
    out = _run_gate(tmp_path, portal, {"_gateway": {"token": "t"}, "reportarchive": {"url": "x"},
                                       "portal": {"api_base": f"http://127.0.0.1:{portal}/"}})
    assert out.startswith("OK") and _Portal.seen[0][0].startswith("/internal/connections/reportarchive")
    _Portal.seen = []
    out = _run_gate(tmp_path, portal, {"_gateway": {"token": "t"}, "reportarchive": {"url": "x"},
                                       "portal": {"api_base": "http://127.0.0.1:1",
                                                  "jwks_url": f"http://127.0.0.1:{portal}/.well-known/jwks.json"}})
    assert out.startswith("FAIL") and _Portal.seen == [], "api_base 가 jwks 보다 먼저다(게이트웨이도 그렇다)"


def test_짝이_맞아도_게이트웨이가_옛_판이면_통과가_아니다(tmp_path, portal):
    """§4 가 게이트웨이 갱신에 실패해도 살아 있으면 재기동을 생략한다 — 옛 판은 못 물으면 공용 토큰으로 폴백한다."""
    _Portal.code = 404
    out = _run_gate(tmp_path, portal, {"_gateway": {"token": "t"}, "reportarchive": {"url": "x"}},
                    gateway_py="async def _portal_connection(): ...\n")
    assert out.startswith("FAIL") and "옛 판" in out


def test_wire_는_포털처럼_등호_주변_공백과_줄끝_주석을_읽는다(tmp_path):
    p = _wire_tree(tmp_path, "GATEWAY_SHARED_TOKEN=OLD1\nGATEWAY_SHARED_TOKEN = OLD2\n")
    assert "갈아 끼웠다" in _wire(p, tmp_path)
    assert (p / "backend/.env").read_text() == "GATEWAY_SHARED_TOKEN=OLD1\nGATEWAY_SHARED_TOKEN = NEW\n", \
        "포털(dotenv)은 마지막 줄을 읽는다 — 그 줄을 갈아야 한다"
    p2 = _wire_tree(tmp_path / "c", "GATEWAY_SHARED_TOKEN=NEW  # 게이트웨이 GW_TOKEN\n")
    assert "이미 배선됨" in _wire(p2, tmp_path), "줄끝 주석을 값으로 읽어 헛된 재기동을 시켰다"
