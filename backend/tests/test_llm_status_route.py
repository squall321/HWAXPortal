# 관리자 'LLM · GPU 현황' 창구 — 수집기를 대신 묻고(꺼짐 503 · 안 닿음 502) 관리자만 보는지 — CAEG(모든 기능 키)라도 관리자가 아니면 403(docs/ops-dashboard)
"""포털은 저장하지 않고 수집기의 /snapshot · /series 를 대신 부른다. 원장 · 토큰 저장소는 임시 폴더에, 수집기는 MockTransport 다. 응답 꼴은 수집기
`Collector.snapshot` · `series_view` 가 내는 그대로다(test_llm_status_collector 가 그 꼴을 잠근다). 주소는 지어낸 값이다.
"""
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.auth.routes import llm_status as ls
from app.auth.token_store import TokenStore
from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.main import app
from tests.test_infra_no_proxy import start_portal  # noqa: F401 — start.sh 의 기동 블록을 임시 리포에서 돌리는 대역

ROOT = Path(__file__).resolve().parents[2]

PW = "pw123456"
BASE = "/auth/admin/llm-status"
SNAP = {"collector": {"version": 1, "state": "ok", "interval_s": 15.0}, "targets": [
    {"id": "glm-1", "label": "GLM-1", "addr": "gpu-a.example:8000", "values": {
        "up": {"value": True, "at": 1.0, "source": "health", "error": None, "stale": False, "age_s": 3.0}}}],
    "agent": {"values": {}}, "router": None,
    "slurm": {"value": None, "at": None, "source": "slurm", "error": "모름 — …", "stale": False, "age_s": None, "rows": []},
    "gpu": {"value": None, "at": None, "source": "gpu", "error": "모름 — …", "stale": False, "age_s": None, "rows": []}}
SERIES = {"target": "glm-1", "metric": "running", "range": "24h", "step_s": 300, "source": "rollup:5m",
          "points": [[1800000000, 1.5, 3.0]], "at": 1800000000, "error": None, "approx": False}


@pytest.fixture()
def box(tmp_path, monkeypatch):
    """boss = 원장 관리자 · caeg = 소속 CAEG(모든 기능 · 플랫폼 키 — 관리자 아님). 수집기는 reply 로 답한다."""
    monkeypatch.delenv("PORTAL_ADMIN_EMAILS", raising=False)
    s = Settings(_env_file=None, user_store_path=str(tmp_path / "users.sqlite"),
                 token_store_path=str(tmp_path / "tokens.sqlite"), upload_staging_dir=str(tmp_path / "staging"),
                 local_bootstrap_admins="boss@corp.com", llm_status_url="http://collector.test:8760/")
    app.dependency_overrides[get_settings] = lambda: s
    from app.auth.routes.local import _rl
    _rl.clear()
    seen: list[httpx.Request] = []
    made: list[dict] = []
    col = {"reply": lambda req: httpx.Response(200, json=SNAP if req.url.path == "/snapshot" else SERIES)}

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return col["reply"](req)
    real = httpx.AsyncClient

    def client(**kw):
        made.append(kw)
        return real(transport=httpx.MockTransport(handler), **kw)
    monkeypatch.setattr(ls.httpx, "AsyncClient", client)
    with TestClient(app) as c:
        keep = (app.state.user_store, app.state.token_store)
        app.state.user_store, app.state.token_store = UserStore(s), TokenStore(s)
        for email in ("boss@corp.com", "caeg@corp.com"):
            c.post("/auth/local/signup", json={"email": email, "name": email.split("@")[0], "password": PW})
        assert app.state.user_store.approve("caeg@corp.com", by="boss@corp.com", groups=[])
        assert app.state.user_store.set_access("caeg@corp.com", affiliation="CAEG")
        yield c, s, col, seen, made
        app.state.user_store, app.state.token_store = keep
    app.dependency_overrides.pop(get_settings, None)


def _login(c, email) -> None:
    c.cookies.clear()
    assert c.post("/auth/local/login", json={"email": email, "password": PW}).status_code == 200


def test_CAEG_라도_관리자가_아니면_403_이고_수집기에_닿지_않는다(box):
    c, _s, _col, seen, _made = box
    _login(c, "caeg@corp.com")
    me = c.get("/auth/me").json()
    assert me["affiliation"] == "CAEG" and "feat:deliberation" in me["entitlements"], "모든 기능 키를 쥔 사람이다(OD-1 — feat: 로 막지 않는 까닭)"
    assert c.get(BASE).status_code == 403
    assert c.get(f"{BASE}/series", params={"target": "glm-1", "metric": "running"}).status_code == 403
    assert not seen, "관리자가 아닌 사람의 요청은 수집기에 닿지 않는다"
    c.cookies.clear()
    assert c.get(BASE).status_code == 401, "로그인하지 않으면 401"


def test_관리자에게_수집기의_스냅숏과_시계열을_그대로_넘긴다(box):
    c, _s, _col, seen, made = box
    _login(c, "boss@corp.com")
    made.clear()                     # 기동 때 앱이 만든 클라이언트는 빼고 이 요청의 것만 본다
    r = c.get(BASE)
    assert r.status_code == 200 and r.json() == SNAP
    assert seen[-1].method == "GET" and seen[-1].url.host == "collector.test" and seen[-1].url.path == "/snapshot"
    assert made and all(kw.get("trust_env") is False for kw in made), "루프백 — 셸의 프록시를 타지 않는다"
    r = c.get(f"{BASE}/series", params={"target": "glm-1", "metric": "running", "range": "24h"})
    assert r.status_code == 200 and r.json() == SERIES
    assert seen[-1].url.path == "/series" and dict(seen[-1].url.params) == {"target": "glm-1", "metric": "running", "range": "24h"}
    c.get(f"{BASE}/series", params={"target": "chat-18711", "metric": "ttft_p95"})
    assert dict(seen[-1].url.params)["range"] == "1h", "범위를 안 주면 1h"
    n = len(seen)
    for bad in ({"target": "a/b", "metric": "running"}, {"target": "glm-1", "metric": "Running"},
                {"target": "glm-1", "metric": "running", "range": "1y"}, {"metric": "running"}):
        assert c.get(f"{BASE}/series", params=bad).status_code == 422, bad
    assert len(seen) == n, "꼴이 틀린 조건은 수집기에 넘기지 않는다"


def test_주소가_없으면_503_꺼져_있다고_말하고_부르지_않는다(box):
    c, s, _col, seen, _made = box
    _login(c, "boss@corp.com")
    s.llm_status_url = ""
    r = c.get(BASE)
    assert r.status_code == 503 and "꺼져 있다" in r.json()["detail"] and "LLM_STATUS=1" in r.json()["detail"] and not seen


@pytest.mark.parametrize("reply, want, text", [
    (lambda req: (_ for _ in ()).throw(httpx.ConnectError("refused", request=req)), 502, "수집기가 답하지 않는다(ConnectError)"),
    (lambda req: (_ for _ in ()).throw(httpx.ReadTimeout("slow", request=req)), 502, "수집기가 답하지 않는다(ReadTimeout)"),
    (lambda req: httpx.Response(500, json={"error": "boom"}), 502, "수집기가 답하지 않는다(HTTP 500) — boom"),
    (lambda req: httpx.Response(503, json={"status": "stalled"}), 502, "수집기가 답하지 않는다(HTTP 503)"),
    (lambda req: httpx.Response(200, json={"hello": "other app"}), 502, "수집기 꼴이 아니다"),
    (lambda req: httpx.Response(200, text="<html>nginx</html>"), 502, "수집기 꼴이 아니다"),
])
def test_닿지_못하거나_답이_이상하면_502_수집기가_답하지_않는다(box, reply, want, text):
    c, _s, col, _seen, _made = box
    _login(c, "boss@corp.com")
    col["reply"] = reply
    r = c.get(BASE)
    assert r.status_code == want and text in r.json()["detail"], r.json()


def test_수집기의_400_404_는_까닭_그대로_넘긴다(box):
    c, _s, col, _seen, _made = box
    _login(c, "boss@corp.com")
    col["reply"] = lambda req: httpx.Response(404, json={"error": "모르는 대상이다 — 설정된 대상: agent, glm-1"})
    r = c.get(f"{BASE}/series", params={"target": "nope", "metric": "running"})
    assert r.status_code == 404 and "모르는 대상" in r.json()["detail"]
    col["reply"] = lambda req: httpx.Response(400, json={"error": "그 대상은 그 지표를 쌓지 않는다"})
    r = c.get(f"{BASE}/series", params={"target": "agent", "metric": "running"})
    assert r.status_code == 400 and "쌓지 않는다" in r.json()["detail"]
    col["reply"] = lambda req: httpx.Response(200, json={"nope": 1})
    assert c.get(f"{BASE}/series", params={"target": "glm-1", "metric": "running"}).status_code == 502, "시계열 꼴(points)이 아니면 502"


# ── 켜는 줄 하나(LLM_STATUS)로 화면도 켜진다 — start.sh 가 포털에 수집기 주소를 넘긴다 ──────────────────────────────────────
def test_포털_설정은_LLM_STATUS_URL_로_읽고_기본은_비어_있다(monkeypatch):
    assert Settings(_env_file=None).llm_status_url == "", "비면 꺼짐(화면 503)"
    monkeypatch.setenv("LLM_STATUS_URL", "http://127.0.0.1:18764")
    assert Settings(_env_file=None).llm_status_url == "http://127.0.0.1:18764"


def test_start_sh_는_LLM_STATUS_가_있을_때만_수집기_주소를_넘긴다(start_portal):  # noqa: F811
    assert "http://127.0.0.1:${LLM_STATUS_PORT:-8760}" in (ROOT / "infra/scripts/start.sh").read_text(encoding="utf-8"), "수집기와 같은 기본 포트"
    assert "LLM_STATUS_URL" not in start_portal(""), "꺼진 박스 — 넘기지 않는다(backend/.env 의 값을 덮지 않는다)"
    assert "LLM_STATUS_URL" not in start_portal("# LLM_STATUS=1   # 선택\n")
    assert start_portal("LLM_STATUS=1\n")["LLM_STATUS_URL"] == "http://127.0.0.1:8760"
    assert start_portal("LLM_STATUS=1\nLLM_STATUS_PORT=18765\n")["LLM_STATUS_URL"] == "http://127.0.0.1:18765"
    envs = start_portal("LLM_STATUS=1\nLLM_STATUS_PORT=87x0\n")
    assert "LLM_STATUS_URL" not in envs and "LLM_STATUS_PORT 가 포트 번호가 아니라" in start_portal.stdout
