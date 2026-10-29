# 분석 루틴 API(/routines-api, R1) — 권한 전수 403 · 주인과 공개 · 판 · 보관 · 검증 · YAML · 준비도 · 고를 수 있는 플랫폼(docs/analysis-routines)
"""저장소 · 원장은 임시 폴더, 게이트웨이는 MockTransport 다(tools/list · /tools-map 을 실제 꼴로 — 노출 이름은 원래 이름이거나
'<백엔드에서 하이픈 뺀 것>_<원래 이름>'). 공유 서비스를 부르지 않는다(절차 라우트 시험과 같은 까닭)."""
import copy
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.main import app
from app.procedures.routine_store import RoutineStore
from app.procedures.store import ProceduresStore

PREFIX = "/routines-api"
PW = "pw123456"
SPEC = {
    "title": "VOC → 심의",
    "purpose": "{{model}} 의 불량",
    "vars": [{"key": "model", "label": "모델"}],
    "steps": [
        {"id": "voc", "title": "VOC", "backends": ["signalforge"], "goal": "{{model}} VOC 를 본다",
         "tools": ["search_voc", "defect_profile"], "expect": {"keys": ["product_code"]}},
        {"id": "ra", "title": "기존 보고서", "kind": "cite", "backends": ["reportarchive"], "goal": "보고서를 찾는다"},
        {"id": "ft", "title": "FailureTrace", "backends": ["failuretrace"], "goal": "불량 기록"},
        {"id": "risk", "title": "리스크", "backends": ["heax-hwax_risk"], "goal": "리스크"},
        {"id": "delib", "title": "메커니즘", "kind": "deliberation", "goal": "메커니즘", "uses": ["voc"]},
    ],
}
# 이 사람의 tools/list(권한 필터의 정본) — signalforge 둘(하나는 별칭 꼴) · RA 하나 · 심의 · 게이트웨이 자체
TOOLS = [{"name": "search_voc", "description": "VOC 검색\n둘째 줄"}, {"name": "signalforge_defect_profile", "description": "불량 분포"},
         {"name": "submit_job", "description": "쓰기"}, {"name": "search_reports", "description": "RA"},
         {"name": "deliberate_start", "description": "심의"}, {"name": "search_tools", "description": "게이트웨이"}]
TMAP = {"map": {"search_voc": "signalforge", "signalforge_defect_profile": "signalforge", "submit_job": "signalforge",
                "search_reports": "reportarchive", "deliberate_start": "hwax-deliberation", "search_tools": "_gateway",
                "risk_list": "heax-hwax_risk"},
        "apps": [{"app": "signalforge", "label": "SignalForge VOC"}, {"app": "reportarchive", "label": "Report Archive"},
                 {"app": "hwax-deliberation", "label": "심의"}, {"app": "heax-hwax_risk", "label": "HWAX Risk"},
                 {"app": "_gateway", "label": "게이트웨이"}]}


def _gateway(tools=TOOLS):
    def handler(req: httpx.Request) -> httpx.Response:
        if req.method == "GET" and req.url.path.endswith("/tools-map"):
            return httpx.Response(200, json=TMAP)
        body = json.loads(req.content or b"{}") if req.content else {}
        if body.get("method") == "initialize":
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": {}}, headers={"mcp-session-id": "s"})
        if body.get("method") == "tools/list":
            payload = {"jsonrpc": "2.0", "id": 3, "result": {"tools": tools}}
            return httpx.Response(200, text=f"data: {json.dumps(payload)}\n\n", headers={"content-type": "text/event-stream"})
        return httpx.Response(200)
    return handler


@pytest.fixture()
def client(tmp_path):
    s = Settings(_env_file=None, user_store_path=str(tmp_path / "users.sqlite"), token_store_path=str(tmp_path / "tok.sqlite"),
                 procedures_store_path=str(tmp_path / "wb.sqlite"), jwt_keys_dir=str(tmp_path / "keys"),
                 upload_staging_dir=str(tmp_path / "stage"),
                 local_bootstrap_admins="boss@corp.com", gateway_shared_token="gw-test-secret")
    app.dependency_overrides[get_settings] = lambda: s
    from app.auth.routes.local import _rl
    from app.procedures.runner import ProceduresRunner
    _rl.clear()
    with TestClient(app) as c:
        app.state.user_store = UserStore(s)
        app.state.procedures_store = ProceduresStore(s)
        app.state.routine_store = RoutineStore(app.state.procedures_store)
        app.state.procedures_runner = ProceduresRunner(
            settings=s, store=app.state.procedures_store, mint_pat=lambda p, run, ix: "pat-test",
            client=httpx.AsyncClient(transport=httpx.MockTransport(_gateway()), timeout=5.0))
        for email in ("boss@corp.com", "peer@corp.com", "user@corp.com"):
            c.post("/auth/local/signup", json={"email": email, "name": email.split("@")[0], "password": PW})
        assert app.state.user_store.approve("user@corp.com", by="boss@corp.com", groups=[])
        assert app.state.user_store.approve("peer@corp.com", by="boss@corp.com", groups=["portal-admin"])   # 부트스트랩은 첫 가입자 하나뿐
        yield c, s
        app.state.procedures_runner = None
    app.dependency_overrides.pop(get_settings, None)


def _login(c, email) -> dict:
    c.cookies.clear()
    assert c.post("/auth/local/login", json={"email": email, "password": PW}).status_code == 200
    return {"X-CSRF-Token": c.cookies.get("hwax_csrf")}


def _routes():
    out = []
    for r in app.routes:
        path = getattr(r, "path", "")
        if path.startswith(PREFIX):
            out += [(m, path) for m in sorted(getattr(r, "methods", set()) - {"HEAD", "OPTIONS"})]
    return sorted(out)


def _create(c, h, spec=None) -> dict:
    r = c.post(f"{PREFIX}/routines", json={"spec": spec or SPEC}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def test_권한_없는_사람은_모든_루틴_라우트에서_403_이고_health_만_열려_있다(client):
    c, _ = client
    routes = _routes()
    assert len(routes) >= 10, routes
    h = _login(c, "user@corp.com")               # 승인된 일반 사용자 — feat:chat 뿐
    for m, path in routes:
        url = path.replace("{routine_id}", "r1")
        body = {"spec": SPEC} if m == "POST" and not path.endswith("/import") else {"yaml": "title: x"}
        r = c.request(m, url, headers=h, json=body if m in ("POST", "PUT", "PATCH") else None)
        if path == f"{PREFIX}/health":
            assert r.status_code == 200 and r.json() == {"ok": True, "contract": 1}, r.text
        else:
            assert r.status_code == 403, (m, path, r.status_code, r.text[:200])


def test_짜기_판_공개_보관은_주인만_고치고_없는_것과_못_보는_것은_같은_404(client):
    c, _ = client
    hb = _login(c, "boss@corp.com")
    made = _create(c, hb)
    assert made["version_no"] == 1
    rid = made["id"]
    got = c.get(f"{PREFIX}/routines/{rid}").json()
    assert got["mine"] and got["version"]["spec"]["visibility"] == "private" and got["version"]["spec"]["report"]["ra"]["upload"] == "auto"
    assert [v["version_no"] for v in got["versions"]] == [1]
    assert c.post(f"{PREFIX}/routines", json={"spec": SPEC}).status_code == 403, "CSRF 없이 쓰지 않는다"
    hp = _login(c, "peer@corp.com")
    assert c.get(f"{PREFIX}/routines/{rid}").status_code == 404, "비공개는 주인만"
    assert c.get(f"{PREFIX}/routines/nope").status_code == 404
    assert c.get(f"{PREFIX}/routines").json()["count"] == 0
    hb = _login(c, "boss@corp.com")
    r = c.post(f"{PREFIX}/routines/{rid}/versions", json={"spec": {**SPEC, "visibility": "all", "title": "VOC → 심의 v2"}}, headers=hb)
    assert r.status_code == 201 and r.json()["version_no"] == 2
    hp = _login(c, "peer@corp.com")
    rows = c.get(f"{PREFIX}/routines", params={"q": "v2"}).json()["routines"]
    assert [x["title"] for x in rows] == ["VOC → 심의 v2"] and rows[0]["mine"] is False
    assert [s["id"] for s in rows[0]["steps"]] == ["voc", "ra", "ft", "risk", "delib"] and rows[0]["vars"][0]["key"] == "model"
    assert c.get(f"{PREFIX}/routines/{rid}", params={"version": 1}).json()["version"]["spec"]["title"] == "VOC → 심의"
    r = c.post(f"{PREFIX}/routines/{rid}/versions", json={"spec": SPEC}, headers=hp)
    assert r.status_code == 404 and "주인만" in r.json()["detail"], "공개는 '남도 본다' 이지 '남도 고친다' 가 아니다"
    assert c.delete(f"{PREFIX}/routines/{rid}", headers=hp).status_code == 404
    text = c.get(f"{PREFIX}/routines/{rid}/export").text
    assert "title: VOC → 심의 v2" in text and "upload: auto" in text
    mine = c.post(f"{PREFIX}/import", json={"yaml": text}, headers=hp)
    assert mine.status_code == 201 and mine.json()["id"] != rid, "남의 루틴은 가져오기로 내 것을 만든다"
    hb = _login(c, "boss@corp.com")
    assert c.delete(f"{PREFIX}/routines/{rid}", headers=hb).json() == {"ok": True, "archived": True}
    assert c.get(f"{PREFIX}/routines/{rid}").status_code == 200, "보관해도 주인은 읽는다(실행 원장이 그 판을 가리킨다)"
    _login(c, "peer@corp.com")
    assert c.get(f"{PREFIX}/routines/{rid}").status_code == 404 and rid not in json.dumps(c.get(f"{PREFIX}/routines").json())


def test_틀린_스펙은_422_와_까닭이고_검증만_하는_길이_있다(client):
    c, _ = client
    h = _login(c, "boss@corp.com")
    bad = copy.deepcopy(SPEC)
    bad["steps"][0]["tools"] = ["publish_report"]
    r = c.post(f"{PREFIX}/routines", json={"spec": bad}, headers=h)
    assert r.status_code == 422 and "쓰기 도구" in r.json()["detail"], r.text
    r = c.post(f"{PREFIX}/validate", json={"spec": SPEC}, headers=h)
    assert r.status_code == 200 and r.json()["spec"]["report"]["sections"] == ["voc", "ra", "ft", "risk", "delib", "insight"]
    assert c.get(f"{PREFIX}/routines").json()["count"] == 0, "검증은 저장하지 않는다"
    r = c.post(f"{PREFIX}/import", json={"yaml": "title: [깨진"}, headers=h)
    assert r.status_code == 422 and "YAML" in r.json()["detail"]


def test_준비도는_단계마다_권한_토큰_박스를_말하고_막지_않는다(client):
    c, _ = client
    h = _login(c, "boss@corp.com")
    spec = copy.deepcopy(SPEC)
    spec["steps"][0]["tools"] = ["search_voc", "defect_profile", "nope_tool"]
    rid = _create(c, h, spec)["id"]
    r = c.get(f"{PREFIX}/routines/{rid}/readiness")
    assert r.status_code == 200, r.text
    by = {s["step"]: s for s in r.json()["steps"]}
    assert by["voc"]["state"] == "allowed" and by["voc"]["missing_tools"] == ["nope_tool"], "별칭 꼴(signalforge_defect_profile)도 원래 이름으로 센다"
    assert by["ra"]["state"] == "not_connected" and "/tokens?tab=connect" in by["ra"]["reason"], "RA 토큰이 없다 — 서비스 계정으로 떨어지지 않는다"
    assert by["ft"]["state"] == "unavailable" and "이 박스" in by["ft"]["reason"]
    assert by["risk"]["state"] == "denied", "이 박스에 있지만 내 도구 목록에 없다"
    assert by["delib"]["state"] == "allowed"


def test_고를_수_있는_플랫폼은_내_도구를_백엔드로_묶는다(client):
    c, _ = client
    _login(c, "boss@corp.com")
    d = c.get(f"{PREFIX}/platforms").json()
    sf = next(p for p in d["platforms"] if p["backend"] == "signalforge")
    assert sf["label"] == "SignalForge VOC"
    assert {t["name"]: t["write"] for t in sf["tools"]} == {"defect_profile": False, "search_voc": False, "submit_job": True}
    assert next(t for t in sf["tools"] if t["name"] == "search_voc")["description"] == "VOC 검색", "설명은 첫 줄만"
    assert {p["backend"] for p in d["platforms"]} == {"signalforge", "reportarchive"}, "심의 · 게이트웨이 자체는 플랫폼 목록 밖"
    assert d["deliberation"] is True
    assert d["not_permitted"] == [{"backend": "heax-hwax_risk", "label": "HWAX Risk"}]


def test_게이트웨이가_넘긴_PAT_로도_읽는다(client):
    c, _ = client
    h = _login(c, "boss@corp.com")
    rid = _create(c, h)["id"]
    tok = c.post("/auth/pat", json={"name": "claude"}, headers=h).json()["token"]
    c.cookies.clear()
    auth = {"Authorization": f"Bearer {tok}"}
    assert c.get(f"{PREFIX}/routines", headers=auth).json()["count"] == 1
    assert c.get(f"{PREFIX}/routines/{rid}", headers=auth).status_code == 200
    assert c.post(f"{PREFIX}/routines", json={"spec": SPEC}, headers=auth).status_code in (401, 403), "짜기는 화면(세션 + CSRF)만"
