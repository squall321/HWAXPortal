# ste 사용자 위임 점검(ste-gateway-check.py)과 update-all §5 드리프트 — 점검이 초록인데 ste 도구가 실패하던 자리(docs/ste-cae00 D-30)
#
# 주소는 문서용 예약 대역(TEST-NET)·루프백만 쓴다 — 이 리포는 GitHub 에 있다.
import http.server
import importlib.util
import json
import os
import socket
import subprocess
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "infra/scripts/ste-gateway-check.py"
UA = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")
_spec = importlib.util.spec_from_file_location("ste_gateway_check", SCRIPT)
chk = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(chk)


# ── 실패 문구 가르기 — 게이트웨이와 ste MCP 가 **실제로 내는** 모양 ─────────────────────────
@pytest.mark.parametrize("text,err,want", [
    ('{"items": []}', False, "ok"),
    ("ste: u@x.io 자격증명으로 호출하지 못했습니다 (RuntimeError('SSO 401: {\"detail\":\"시크릿이 맞지 않는다\"}')). "
     "이 앱은 사용자별 데이터라 서비스 계정 결과로 대체하지 않습니다.", True, "mint"),
    ('Error executing tool list_jobs: GET /api/jobs → HTTP 401: {"detail":"인증이 필요하다"} — 신원이 없거나 토큰이 죽었다.',
     True, "token"),
    ("backend ste unavailable: RuntimeError('backend session down')", True, "session"),
    ("forbidden: cluster_info — 이 계정에는 권한이 없다", True, "forbidden"),
    ("unknown tool: cluster_info", True, "missing"),
    ('Error executing tool cluster_info: GET /api/cluster → HTTP 503: {"detail":"클러스터 조회 실패: scontrol 없음"}',
     True, "slurm"),
    ("Error executing tool cluster_info: 알 수 없는 오류", True, "other"),
])
def test_실패_문구를_원인별로_가른다(text, err, want):
    assert chk.classify(text, err)[0] == want


def test_가르는_문구가_게이트웨이_소스에_실제로_있다():
    """문구가 바뀌면 판정이 조용히 'other' 로 떨어진다 — 형제 리포의 원문을 붙잡는다."""
    gw = ROOT.parent / "HWAXMcpGateway/gateway.py"
    if not gw.exists():
        pytest.skip("형제 HWAXMcpGateway 리포가 없다")
    src = gw.read_text(encoding="utf-8")
    assert "자격증명으로 호출하지 못했습니다" in src
    assert 'f"backend {backend_key} unavailable: ' in src
    ste = ROOT.parent / "SmartTwinExplorer/backend/mcp_server/server.py"
    if ste.exists():
        assert 'f"{what} → HTTP {r.status_code}: ' in ste.read_text(encoding="utf-8")


def test_도구_이름은_박스마다_다르다_ste_백엔드_것만_찾는다():
    tmap = {"ste_list_jobs": "ste", "list_jobs": "heax-kooremapper_mcp", "cluster_info": "ste"}
    assert chk.resolve(tmap, "list_jobs") == "ste_list_jobs", "같은 이름이 다른 앱에 있으면 접두어가 붙는다"
    assert chk.resolve({"list_jobs": "ste"}, "list_jobs") == "list_jobs", "충돌이 없는 박스는 그대로다"
    assert chk.resolve(tmap, "cluster_info") == "cluster_info"
    assert chk.resolve({"cluster_info": "smart-twin-mcp"}, "cluster_info") is None


# ── deleg — 게이트웨이 config 의 위임과 그 시크릿 ──────────────────────────────────────
class _Verify(http.server.BaseHTTPRequestHandler):
    mode = "204"

    def do_POST(self):  # noqa: N802
        want = self.headers.get("X-Heax-Gateway-Secret")
        if self.mode == "old":
            self.send_response(401); self.send_header("WWW-Authenticate", "Bearer"); self.end_headers(); return
        if self.mode == "404":
            self.send_response(404); self.end_headers(); return
        self.send_response(204 if want == "right" else 401); self.end_headers()

    def log_message(self, *a):
        pass


@pytest.fixture()
def verify_server():
    srv = http.server.HTTPServer(("127.0.0.1", 0), _Verify)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield srv
    srv.shutdown()


def _cfg(tmp_path, ste: dict | None, has_backend=True) -> Path:
    g = {"_gateway": {"token": "t"}}
    if has_backend:
        g["ste"] = {"url": "http://127.0.0.1:15812/mcp"}
    if ste is not None:
        g["heax_registry"] = {"per_user_sso": {"ste": ste}}
    p = tmp_path / "gateway_config.json"
    p.write_text(json.dumps(g))
    return p


def test_위임이_없으면_빨강이고_토큰_없이_부른다고_말한다(tmp_path):
    r = chk.deleg(_cfg(tmp_path, None), "right")
    assert r["state"] == "missing" and chk.deleg_rc(r) == 1 and "토큰 없이" in r["detail"]


def test_게이트웨이_시크릿이_infra_env_와_다르면_빨강(tmp_path, verify_server):
    url = f"http://127.0.0.1:{verify_server.server_port}/api/auth/sso"
    r = chk.deleg(_cfg(tmp_path, {"sso_url": url, "secret": "old-copy"}), "right")
    assert r["state"] == "stale" and r["verify"] == "401" and chk.deleg_rc(r) == 1
    assert "old-copy" not in json.dumps(r) and "right" not in json.dumps(r), "시크릿 값은 어디에도 찍지 않는다"


def test_헤드가_게이트웨이의_시크릿을_받으면_초록(tmp_path, verify_server):
    url = f"http://127.0.0.1:{verify_server.server_port}/api/auth/sso"
    r = chk.deleg(_cfg(tmp_path, {"sso_url": url, "secret": "right"}), "right")
    assert (r["state"], r["verify"], chk.deleg_rc(r)) == ("ok", "204", 0)


@pytest.mark.parametrize("mode,want", [("old", "old"), ("404", "404")])
def test_헤드_옛_판과_verify_모름을_가른다(tmp_path, verify_server, mode, want):
    _Verify.mode = mode
    try:
        url = f"http://127.0.0.1:{verify_server.server_port}/api/auth/sso"
        r = chk.deleg(_cfg(tmp_path, {"sso_url": url, "secret": "right"}), "right")
        assert r["verify"] == want and chk.deleg_rc(r) == 1
    finally:
        _Verify.mode = "204"


def test_헤드에_닿지_않으면_터널부터_보라고_한다(tmp_path):
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()   # 닫힌 포트
    r = chk.deleg(_cfg(tmp_path, {"sso_url": f"http://127.0.0.1:{port}/api/auth/sso", "secret": "right"}), "right")
    assert r["verify"] == "unreachable" and "터널" in r["detail"] and chk.deleg_rc(r) == 1


def test_ste_를_안_쓰는_박스와_config_없음은_판정_불가(tmp_path):
    assert chk.deleg_rc(chk.deleg(_cfg(tmp_path, None, has_backend=False), "x")) == 2
    assert chk.deleg_rc(chk.deleg(tmp_path / "nope.json", "x")) == 2


def test_설정만_볼_때는_헤드에_묻지_않는다(tmp_path):
    r = chk.deleg(_cfg(tmp_path, {"sso_url": "http://127.0.0.1:9/api/auth/sso", "secret": "right"}), "right",
                  do_verify=False)
    assert (r["state"], r["verify"], chk.deleg_rc(r)) == ("ok", "skipped", 0)


def test_env_값은_bash_와_같게_읽는다(tmp_path):
    f = tmp_path / ".env"
    f.write_text('STE_SSO_SECRET=first\nexport STE_SSO_SECRET="second"   # 주석\r\n')
    assert chk.env_value("STE_SSO_SECRET", f) == "second"
    assert chk.env_value("NOPE", f) == ""


# ── update-all §5 — 위임이 없거나 낡았으면 재프로비저닝 대상에 넣는다 ──────────────────────
def _drift_block() -> str:
    i = UA.index("  # ste 사용자 위임 — 게이트웨이 config 에 없거나 시크릿이 infra/.env 와 다르면 재프로비저닝")
    return UA[i:UA.index('  if [ -n "$MISSING" ]; then', i)]


@pytest.mark.parametrize("ste,expect", [
    (None, True),                                                       # 위임 없음
    ({"sso_url": "http://127.0.0.1:15810/api/auth/sso", "secret": "old"}, True),    # 시크릿 낡음
    ({"sso_url": "http://127.0.0.1:15810/api/auth/sso", "secret": "right"}, False),  # 정상
])
def test_update_all_5_는_ste_위임_드리프트를_재프로비저닝한다(tmp_path, ste, expect):
    gw = tmp_path / "gw"; gw.mkdir()
    _cfg(gw, ste)
    script = 'MISSING=""\n' + _drift_block() + 'printf "MISSING=[%s]\\n" "$MISSING"\n'
    env = {"PATH": os.environ["PATH"], "STE_ROUTED": "1", "GW_DIR": str(gw), "STE_SSO_SECRET": "right",
           "SELF_REPO": str(ROOT)}
    r = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    assert ("MISSING=[ste]" in r.stdout) is expect, r.stdout
    assert "right" not in r.stdout and "old" not in r.stdout.replace("MISSING", ""), "시크릿을 찍지 않는다"
