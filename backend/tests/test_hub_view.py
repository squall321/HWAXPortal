# 개인 Claude 보기 — 포털 사람 설정 저장 · 검증 · 게이트웨이 전달(docs/request-1029 E-4 · design-e2-e4.md E4-3)
#
# 게이트웨이는 HTTP 전송 계층만 가짜로 둔다(test_hub_apps.py 와 같다) — `/tools-map` 을 읽는 코드와 `/conn-invalidate` 를 부르는 코드는 진짜로 돈다.
import ast
import json
import os
import sqlite3
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.access.hub_view import AREA_RE, HEADER_NAME, HEADER_PORTAL, MODES, format_view, parse_view
from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.main import app

REPO = Path(__file__).resolve().parents[2]
# 게이트웨이 /tools-map 의 꼴(map · areas · apps[].role · area_meta) — 형제 허브(role sibling)와 허브 자체 도구(_gateway)는 묶음 수에 들지 않는다
TOOLS_MAP = {
    "map": {"step_x": "heax-step_forge", "step_y": "heax-step_forge", "mesh_q": "heax-step_forge", "voc_q": "signalforge",
            "loose": "signalforge", "run_drop": "smart-twin-mcp", "rootdesigndatahub_object_get": "rootdesigndatahub",
            "failuretrace_object_get": "failuretrace", "search_tools": "_gateway"},
    "areas": {"step_x": "cad", "step_y": "cad", "mesh_q": "mesh", "voc_q": "voc", "loose": "", "run_drop": "sim",
              "rootdesigndatahub_object_get": "knowledge", "failuretrace_object_get": "knowledge", "search_tools": "system"},
    "apps": [{"app": "_gateway", "label": "허브", "tool_count": 1, "reachable": True},
             {"app": "heax-step_forge", "label": "StepForge", "tool_count": 3, "reachable": True},
             {"app": "signalforge", "label": "SignalForge", "tool_count": 2, "reachable": True},
             {"app": "smart-twin-mcp", "label": "SmartTwin", "tool_count": 1, "reachable": True},
             {"app": "rootdesigndatahub", "label": "자주검증 Datahub", "tool_count": 1, "reachable": True, "role": "canonical"},
             {"app": "failuretrace", "label": "FailureTrace", "tool_count": 1, "reachable": True, "role": "sibling"}],
    "area_meta": [{"area": a, "label": a.upper(), "description": f"{a} 영역"} for a in ("cad", "mesh", "voc", "sim", "knowledge", "system")],
    # 게이트웨이가 아는 보기 — 없으면(보기 이전 판) 포털은 저장하되 '아직 전체로 돈다' 고 알린다(검토 10-31)
    "views": ["full", "bundle", "light"],
}
# 목적 보기(docs/mcp-modernize M3)를 아는 게이트웨이 — `/tools-map` 의 views 에 purpose, purposes.items(목적 표). 트리거 · 질의 예 · 단계 차례는 화면에
# 내리지 않는다(list_tool_apps(by='purpose') 의 37K 자를 피하는 길 — 화면에 쓸 칸만)
PURPOSE_MAP = {
    **TOOLS_MAP, "views": ["full", "bundle", "light", "purpose"],
    "purposes": {"fingerprint": "fp1", "app_entries": {}, "items": [
        {"key": "drop-prep", "title": "낙하 해석 준비", "summary": "형상에서 낙하 해석 입력까지", "kind": "multi",
         "apps": ["heax-step_forge", "smart-twin-mcp"], "entry": {"backend": "heax-step_forge", "tool": "x", "name": "step_x"}, "live": True,
         "steps": [{"backend": "heax-step_forge", "tool": "x", "name": "step_x", "why": "형상"},
                   {"backend": "heax-step_forge", "tool": "m", "name": "mesh_q", "why": "메시"},
                   {"backend": "smart-twin-mcp", "tool": "r", "name": "run_drop", "why": "제출"},
                   {"backend": "box-only", "tool": "z", "name": None, "why": "이 박스에 없다"},
                   {"backend": "_gateway", "tool": "search_tools", "name": "search_tools", "why": "찾기"}],
         "triggers": ["낙하 준비"], "samples": ["낙하 해석 준비해줘"]},
        {"key": "voc-scan", "title": "VOC 훑기", "summary": "시장 신호", "kind": "app", "apps": ["signalforge"],
         "entry": {"backend": "signalforge", "tool": "q", "name": "voc_q"}, "live": True,
         "steps": [{"backend": "signalforge", "tool": "q", "name": "voc_q", "why": "검색"}], "triggers": [], "samples": []},
        {"key": "knowledge", "title": "정본 지식 찾기", "summary": "정본 허브", "kind": "app", "apps": ["rootdesigndatahub", "failuretrace"],
         "entry": {"backend": "rootdesigndatahub", "tool": "g", "name": "rootdesigndatahub_object_get"}, "live": True,
         "steps": [{"backend": "rootdesigndatahub", "tool": "g", "name": "rootdesigndatahub_object_get", "why": "정본"},
                   {"backend": "failuretrace", "tool": "g", "name": "failuretrace_object_get", "why": "형제"}], "triggers": [], "samples": []},
        {"key": "box-only", "title": "다른 박스 전용", "summary": "이 박스에 앱이 없다", "kind": "app", "apps": ["box-only"],
         "entry": {"backend": "box-only", "tool": "z", "name": None}, "live": False,
         "steps": [{"backend": "box-only", "tool": "z", "name": None, "why": "없음"}], "triggers": [], "samples": []},
    ]},
}


class _Gateway:
    def __init__(self):
        self.calls: list[tuple[str, str, dict]] = []
        self.down = False
        self.tools_map = TOOLS_MAP

    def handle(self, req: httpx.Request) -> httpx.Response:
        self.calls.append((req.method, req.url.path, dict(req.url.params)))
        if self.down:
            raise httpx.ConnectError("gateway down")
        if req.url.path.endswith("/tools-map"):
            return httpx.Response(200, json=self.tools_map)
        if req.url.path.endswith("/conn-invalidate"):
            return httpx.Response(200, json={"ok": True})
        return httpx.Response(404)


@pytest.fixture()
def env(tmp_path, monkeypatch):
    s = Settings(user_store_path=str(tmp_path / "users.sqlite"), local_bootstrap_admins="boss@corp.com",
                 gateway_shared_token="gw-test-secret")
    app.dependency_overrides[get_settings] = lambda: s
    from app.auth.routes.local import _rl

    _rl.clear()
    gw = _Gateway()
    real = httpx.AsyncClient

    class _Client(real):
        def __init__(self, *a, **k):
            k["transport"] = httpx.MockTransport(gw.handle)
            super().__init__(*a, **k)

    with TestClient(app) as c:
        app.state.user_store = UserStore(s)          # 컨텍스트 진입 후 교체(실DB 오염 방지)
        monkeypatch.setattr(httpx, "AsyncClient", _Client)
        c.post("/auth/local/signup", json={"email": "boss@corp.com", "name": "Boss", "password": "pw123456"})
        c.post("/auth/local/signup", json={"email": "user@corp.com", "name": "User", "password": "pw123456"})
        h = _login(c, "boss@corp.com")
        assert c.post("/auth/local/users/user@corp.com/approve", json={"groups": []}, headers=h).status_code == 200
        yield c, gw
    app.dependency_overrides.pop(get_settings, None)


def _login(c, email):
    r = c.post("/auth/local/login", json={"email": email, "password": "pw123456"})
    assert r.status_code == 200, r.text
    return {"X-CSRF-Token": c.cookies.get("hwax_csrf")}


def _ent(c, email):
    return c.get("/internal/access/entitlements", params={"email": email},
                 headers={"Authorization": "Bearer gw-test-secret"}).json()


def _put(c, h, mode, areas=()):
    return c.put("/auth/access/view", json={"mode": mode, "areas": list(areas)}, headers=h)


def test_보기는_기본이_전체이고_권한_응답에_실린다(env):
    """끄기와 같은 길 — 권한 응답(게이트웨이가 60초 캐시로 받는다)의 view 칸. 새 사용자는 전체다(지금과 같다 — 결정 Q-9)."""
    c, _ = env
    _login(c, "user@corp.com")
    body = c.get("/auth/access/view").json()
    assert (body["mode"], body["areas"], body["unknown_areas"], body["view_supported"]) == ("full", [], [], True)
    assert "재연결" in body["note"] and "invoke_tool" in body["note"]
    assert f"{HEADER_NAME}: {HEADER_PORTAL}" in body["note"] and "서버" in body["note"], \
        "보기는 청한 연결(포털 배치 · 등록 명령)에만 먹는다 — 내 토큰으로 서버에서 도는 앱 · 스크립트는 늘 전체다(검토 10-31)"
    assert _ent(c, "user@corp.com")["view"] == "full"


def test_보기를_모르는_옛_게이트웨이면_저장하되_아직_전체로_돈다고_알린다(env):
    """보기 이전 게이트웨이는 권한 응답의 view 를 읽지 않는다 — 종전 화면은 '저장했습니다' 만 말하고 목록은 그대로 전체였다(실패가 성공처럼 보였다, 검토
    10-31). 게이트웨이 `/tools-map` 의 views 로 안다고 말할 때만 view_supported 다. 저장은 한다 — 게이트웨이를 새 판으로 올리면 그때부터 먹는다."""
    c, gw = env
    gw.tools_map = {k: v for k, v in TOOLS_MAP.items() if k != "views"}
    h = _login(c, "user@corp.com")
    assert c.get("/auth/access/view").json()["view_supported"] is False
    r = _put(c, h, "light")
    assert r.status_code == 200 and r.json()["view_supported"] is False and r.json()["mode"] == "light", r.text
    assert _ent(c, "user@corp.com")["view"] == "light"
    gw.tools_map = {**TOOLS_MAP, "views": ["full"]}
    assert c.get("/auth/access/view").json()["view_supported"] is False, "보기 셋을 다 알아야 한다"
    gw.tools_map = TOOLS_MAP
    assert c.get("/auth/access/view").json()["view_supported"] is True


def test_묶음을_고르면_저장되고_게이트웨이_캐시를_깨고_권한_응답에_실린다(env):
    c, gw = env
    h = _login(c, "user@corp.com")
    r = _put(c, h, "bundle", ["voc", "cad", "voc"])
    assert r.status_code == 200, r.text
    assert (r.json()["mode"], r.json()["areas"]) == ("bundle", ["voc", "cad"]), "고른 차례 그대로, 겹치면 하나"
    assert ("POST", "/conn-invalidate", {"email": "user@corp.com"}) in gw.calls, "안 깨면 최대 60초 늦게 먹는다"
    assert _ent(c, "user@corp.com")["view"] == "bundle:voc,cad"
    assert _ent(c, "boss@corp.com")["view"] == "full", "남의 설정에 섞이지 않는다"
    assert c.get("/auth/access/view").json()["areas"] == ["voc", "cad"]
    assert _put(c, h, "light", ["cad"]).status_code == 200
    assert _ent(c, "user@corp.com")["view"] == "light", "가벼운 · 전체는 영역을 버린다"
    assert _put(c, h, "FULL").status_code == 200 and _ent(c, "user@corp.com")["view"] == "full"


def test_영역_수는_내_권한_안이고_끈_앱_형제_허브_허브_자체는_세지_않는다(env):
    """화면이 영역마다 '내 권한 안의 도구 수' 를 보인다 — 묶음 보기가 실제로 싣는 것과 같은 셈이다(권한 없는 앱 · 끈 앱은 어느 보기에도 없고, 형제 허브
    사본은 묶음에 없으며, 허브 자체 도구는 늘 실린다). 미분류는 어느 묶음에도 들지 않는다(찾기로 닿는다)."""
    c, _ = env
    h = _login(c, "boss@corp.com")                    # 관리자 — 다 열린다
    counts = {o["area"]: o["tool_count"] for o in c.get("/auth/access/view").json()["area_options"]}
    assert counts == {"cad": 2, "mesh": 1, "voc": 1, "sim": 1, "knowledge": 1, "system": 0}, counts
    assert c.get("/auth/access/view").json()["unclassified"] == 1
    assert c.put("/auth/access/apps/heax-step_forge", json={"muted": True}, headers=h).status_code == 200
    counts = {o["area"]: o["tool_count"] for o in c.get("/auth/access/view").json()["area_options"]}
    assert counts["cad"] == 0 and counts["mesh"] == 0 and counts["voc"] == 1
    _login(c, "user@corp.com")                         # 기본 사용자 — StepForge · SignalForge · SmartTwin 권한이 없다
    body = c.get("/auth/access/view").json()
    counts = {o["area"]: o["tool_count"] for o in body["area_options"]}
    assert counts == {"cad": 0, "mesh": 0, "voc": 0, "sim": 0, "knowledge": 1, "system": 0} and body["unclassified"] == 0, counts
    assert [o["label"] for o in body["area_options"]][:2] == ["CAD", "MESH"], "라벨 · 차례는 게이트웨이 area_meta 그대로"


@pytest.mark.parametrize("mode,areas,why", [("everything", [], "모르는 보기"), ("bundle", [], "하나 이상"), ("bundle", ["nosuch"], "모르는 영역"),
                                            ("bundle", ["cad", "CAD!"], "모르는 영역"), ("bundle", ["x" * 40], "모르는 영역")])
def test_틀린_보기와_모르는_영역은_받지_않는다(env, mode, areas, why):
    c, _ = env
    h = _login(c, "user@corp.com")
    assert _put(c, h, "bundle", ["cad"]).status_code == 200
    r = _put(c, h, mode, areas)
    assert r.status_code == 400 and why in r.json()["detail"], r.text
    assert _ent(c, "user@corp.com")["view"] == "bundle:cad", "거절하면 그대로다"


def test_CSRF_없이는_못_바꾼다(env):
    c, _ = env
    _login(c, "user@corp.com")
    assert c.put("/auth/access/view", json={"mode": "light", "areas": []}).status_code == 403
    assert _ent(c, "user@corp.com")["view"] == "full"


def test_게이트웨이에_못_닿으면_모름이다(env):
    c, gw = env
    h = _login(c, "user@corp.com")
    gw.down = True
    assert c.get("/auth/access/view").status_code == 502
    assert _put(c, h, "light").status_code == 502, "영역을 확인할 수 없으면 바꾸지 않는다(끄기와 같다)"
    assert _ent(c, "user@corp.com")["view"] == "full"


def test_옛_DB_에도_칸이_생긴다(tmp_path):
    db = tmp_path / "users.sqlite"
    con = sqlite3.connect(str(db))
    con.execute("CREATE TABLE users (email TEXT PRIMARY KEY, name TEXT NOT NULL, pw_hash TEXT, "
                "groups TEXT NOT NULL DEFAULT '[]', status TEXT NOT NULL DEFAULT 'pending', "
                "auth_source TEXT NOT NULL DEFAULT 'local', created_at INTEGER NOT NULL, approved_at INTEGER, "
                "approved_by TEXT, last_login_at INTEGER, failed_count INTEGER NOT NULL DEFAULT 0, "
                "locked_until INTEGER NOT NULL DEFAULT 0)")
    con.execute("INSERT INTO users(email, name, created_at) VALUES('old@corp.com', 'Old', 0)")
    con.commit()
    con.close()
    st = UserStore(Settings(user_store_path=str(db)))
    assert st.get("old@corp.com")["hub_view"] == ""
    assert st.set_hub_view("old@corp.com", "bundle:cad") == "bundle:cad"
    assert st.get("old@corp.com")["hub_view"] == "bundle:cad"
    assert st.set_hub_view("nobody@corp.com", "light") is None


def test_보기_글의_꼴():
    """게이트웨이 _parse_view 와 같은 규칙이다(그쪽 시험이 이 모듈을 읽어 맞댄다) — 칸 이름 · 꼴이 갈리면 사람 설정이 조용히 전체로 떨어진다."""
    assert MODES == ("full", "bundle", "light", "purpose"), "앞 셋(E-4)의 차례는 그대로 — 목적(M3)은 뒤에 붙인다"
    assert parse_view(" PURPOSE:drop-prep,report-write,drop-prep ") == ("purpose", ["drop-prep", "report-write"])
    assert parse_view("purpose:") is None and parse_view("purpose:Drop!") is None
    assert format_view("purpose", ["drop-prep", "voc-scan", "drop-prep"]) == "purpose:drop-prep,voc-scan"
    for raw, want in (("full", ("full", [])), (" LIGHT ", ("light", [])), ("bundle:cad", ("bundle", ["cad"])),
                      ("bundle:cad, mesh,cad", ("bundle", ["cad", "mesh"])), ("bundle:", None), ("bundle:CAD!", None),
                      ("bundle:" + ",".join(f"a{i}" for i in range(33)), None), ("all", None), ("", None), (None, None)):
        assert parse_view(raw) == want, raw
    assert format_view("bundle", ["cad", "mesh", "cad"]) == "bundle:cad,mesh" and format_view("light", ["cad"]) == "light"
    assert parse_view(HEADER_PORTAL) is None, "연결 머리의 portal 은 보기 글이 아니다 — '포털 설정을 따른다' 는 표지라 저장하지 않는다"


def test_리포_mcp_json_은_보기_머리로_늘_전체를_청한다():
    """리포 파이프라인(infra/pipeline/*.js)은 리포 .mcp.json(개인 PAT)으로 돈다 — 사람 설정이 가벼운이어도 심의 · 리스크 워크플로의 목록이 줄지 않게
    연결 머리가 늘 full 을 청한다(design-e2-e4 E4-5 · mcp-app-toggle D-7). 환경변수로만 바꾼다."""
    srv = json.loads((REPO / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]["hwax"]
    assert srv["headers"]["X-HWAX-View"] == "${HWAX_GATEWAY_VIEW:-full}"
    assert parse_view("full") == ("full", [])


def _gateway_literal(name: str):
    """형제 게이트웨이 gateway.py 의 모듈 수준 상수(문자열 · re.compile 의 패턴) — import 하지 않고 AST 로 읽는다(test_gateway_parity 와 같다).
    작업 가지에서는 HWAX_GATEWAY_ROOT 로 그 자리를 준다. 형제가 없거나 보기 이전 판이면 건너뛴다."""
    root = Path(os.environ.get("HWAX_GATEWAY_ROOT") or REPO.parent / "HWAXMcpGateway")
    src = root / "gateway.py"
    if not src.exists():
        pytest.skip("형제 리포 HWAXMcpGateway 가 이 박스에 없다")
    text = src.read_text(encoding="utf-8")
    if "x-hwax-view" not in text:
        pytest.skip("형제 게이트웨이가 보기 이전 판이다(x-hwax-view 를 모른다)")
    for node in ast.parse(text).body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == name for t in node.targets):
            v = node.value
            return v.args[0].value if isinstance(v, ast.Call) else ast.literal_eval(v)
    raise AssertionError(f"게이트웨이에서 {name} 를 못 찾았다(이름이 바뀌었나)")


def test_게이트웨이와_머리_이름_영역_꼴이_같다():
    assert _gateway_literal("VIEW_HEADER") == "x-hwax-view" == HEADER_NAME.lower()
    assert _gateway_literal("_VIEW_AREA_RE") == AREA_RE.pattern
    # 포털 등록 배치(setupBat.ts)가 다는 표지 — 게이트웨이가 이 값의 머리로 청한 연결에만 포털 보기를 얹는다(어긋나면 배치로 붙인 Claude 가 늘 전체다)
    assert _gateway_literal("VIEW_PORTAL") == HEADER_PORTAL


# ── 목적 보기(docs/mcp-modernize M3) ──────────────────────────────────────────────────────────────────────
def test_목적_고르기는_화면에_쓸_칸만_내리고_내_권한_안의_단계_도구를_센다(env):
    """목적마다 제목 · 요약 · 관련 앱(라벨) · 이 박스에 있나 · 내 권한 안의 단계 도구 수. 트리거 · 질의 예 · 단계 차례는 내리지 않는다 — 목적 표
    전체를 글로 펴는 list_tool_apps(by='purpose')(37K 자) 대신 `/tools-map` 의 purposes 에서 고른 칸만이다. 허브 자체 도구는 늘 실려 세지 않는다."""
    c, gw = env
    gw.tools_map = PURPOSE_MAP
    _login(c, "boss@corp.com")
    body = c.get("/auth/access/view").json()
    assert body["purpose_supported"] is True and body["view_supported"] is True
    rows = {o["key"]: o for o in body["purpose_options"]}
    assert list(rows) == ["drop-prep", "voc-scan", "knowledge", "box-only"], "차례는 게이트웨이 표 그대로"
    d = rows["drop-prep"]
    assert set(d) == {"key", "title", "summary", "kind", "apps", "live", "tool_count", "step_count"}, "트리거 · 질의 예 · 단계는 내리지 않는다"
    assert (d["title"], d["live"], d["tool_count"], d["step_count"]) == ("낙하 해석 준비", True, 3, 5), d
    assert d["apps"] == [{"app": "heax-step_forge", "label": "StepForge"}, {"app": "smart-twin-mcp", "label": "SmartTwin"}]
    assert rows["knowledge"]["tool_count"] == 2, "목적 보기는 단계에 있으면 형제 허브 사본도 싣는다(묶음과 다르다)"
    assert rows["box-only"]["live"] is False and rows["box-only"]["tool_count"] == 0
    assert len(json.dumps(body["purpose_options"], ensure_ascii=False)) < 2000
    _login(c, "user@corp.com")                         # 기본 사용자 — StepForge · SignalForge · SmartTwin 권한이 없다
    rows = {o["key"]: o for o in c.get("/auth/access/view").json()["purpose_options"]}
    assert rows["drop-prep"]["tool_count"] == 0 and rows["voc-scan"]["tool_count"] == 0 and rows["knowledge"]["tool_count"] == 2


def test_목적을_고르면_저장되고_게이트웨이_캐시를_깨고_권한_응답에_실린다(env):
    c, gw = env
    gw.tools_map = PURPOSE_MAP
    h = _login(c, "user@corp.com")
    r = c.put("/auth/access/view", json={"mode": "purpose", "purposes": ["voc-scan", "drop-prep", "voc-scan"]}, headers=h)
    assert r.status_code == 200, r.text
    assert (r.json()["mode"], r.json()["purposes"], r.json()["areas"]) == ("purpose", ["voc-scan", "drop-prep"], [])
    assert ("POST", "/conn-invalidate", {"email": "user@corp.com"}) in gw.calls
    assert _ent(c, "user@corp.com")["view"] == "purpose:voc-scan,drop-prep", "게이트웨이 _parse_view 가 읽는 글 그대로"
    assert _put(c, h, "bundle", ["cad"]).status_code == 200 and _ent(c, "user@corp.com")["view"] == "bundle:cad", "묶음으로 돌아가면 목적은 버린다"


@pytest.mark.parametrize("purposes,why", [([], "하나 이상"), (["nosuch"], "모르는 목적"), (["box-only"], "단계가 하나도 없는 목적"),
                                          (["Drop!"], "모르는 목적")])
def test_모르는_목적과_이_박스에_없는_목적은_받지_않는다(env, purposes, why):
    c, gw = env
    gw.tools_map = PURPOSE_MAP
    h = _login(c, "user@corp.com")
    r = c.put("/auth/access/view", json={"mode": "purpose", "purposes": purposes}, headers=h)
    assert r.status_code == 400 and why in r.json()["detail"], r.text
    assert _ent(c, "user@corp.com")["view"] == "full", "거절하면 그대로다"


@pytest.mark.parametrize("tm", [TOOLS_MAP, {**PURPOSE_MAP, "views": ["full", "bundle", "light"]}, {**PURPOSE_MAP, "purposes": {"items": []}}])
def test_목적_보기를_모르는_게이트웨이면_목적은_저장하지_않는다(env, tm):
    """묶음 · 가벼운은 옛 게이트웨이에도 저장하고 '아직 전체로 돈다' 고 알리지만, 목적 글은 손잡이를 끈 게이트웨이가 틀린 꼴(전체)로 읽는다 — 저장하면
    '저장했다' 와 '전체로 돈다' 가 갈린다. 앞 셋은 그대로 안다(view_supported)."""
    c, gw = env
    gw.tools_map = tm
    h = _login(c, "user@corp.com")
    body = c.get("/auth/access/view").json()
    assert body["purpose_supported"] is False and body["view_supported"] is True
    r = c.put("/auth/access/view", json={"mode": "purpose", "purposes": ["drop-prep"]}, headers=h)
    assert r.status_code == 400 and "목적 보기를 모릅니다" in r.json()["detail"], r.text
    assert _ent(c, "user@corp.com")["view"] == "full"


def test_저장해_둔_목적이_표에서_사라지면_알린다(env):
    c, gw = env
    gw.tools_map = PURPOSE_MAP
    h = _login(c, "user@corp.com")
    assert c.put("/auth/access/view", json={"mode": "purpose", "purposes": ["drop-prep", "voc-scan"]}, headers=h).status_code == 200
    gw.tools_map = {**PURPOSE_MAP, "purposes": {**PURPOSE_MAP["purposes"], "items": PURPOSE_MAP["purposes"]["items"][1:]}}
    body = c.get("/auth/access/view").json()
    assert (body["mode"], body["purposes"], body["unknown_purposes"]) == ("purpose", ["drop-prep", "voc-scan"], ["drop-prep"])
