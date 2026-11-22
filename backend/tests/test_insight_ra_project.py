# 과제 인사이트의 RA 투영(M5) 시험 — 조직에 연 확인 카드의 RA 보고서에 SP 과제 객체를 그 사람의 RA 연결로 단다 · 스위치 기본 꺼짐 · 거두면 표지만
"""docs/project-insight-graph M5 · contracts §11 · 사용자 결정 2026-11-21(docs/leftovers-1121 L21-6 ③).

RA 대역은 Report Archive v0.186.3(`b552f09`)의 진짜 꼴이다 — 답은 `{success, data}` 봉투(shared/responses.py), 거절은 `{success: false, message}`
(shared/errors.py — HTTPException 도 이 꼴), 객체 검색은 `POST /api/entities/search` → `{items: EntityRead[], total}`(entities/routes.py ·
schemas.py), 태그 더하기는 `POST /api/reports/{id}/entities/add` → `{report_id, entity_ids, added}`(reports/routes.py). 마지막 시험이 그 소스와
견준다(형제 리포가 없으면 건너뛴다).
"""
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from app.agent import routes as R
from app.insights import ra_project as RA
from app.insights import routes as IR
from app.main import app

from test_insights import CARD, CONFIRMED, KEY, _login, _principal, _relay, env  # noqa: F401 — env 는 픽스처다

_RA_SRC = Path(__file__).resolve().parents[3] / "ReportArchive" / "backend" / "app"
EID, OTHER = 4412, 4413


def _entity(eid: int, code: str | None, value: str, *, type_slug: str = "project", status: str = "active") -> dict:
    """RA EntityRead 의 JSON 꼴(jsonable_encoder — 날짜는 ISO 글, status 는 낱말)."""
    return {"id": eid, "type_id": 3, "type_slug": type_slug, "value": value, "code": code, "description": "", "status": status,
            "valid_from_year": None, "valid_to_year": None, "created_by_user_id": 1, "created_at": "2026-11-20T01:02:03",
            "updated_at": "2026-11-20T01:02:03", "properties": {}, "usage_count": None}


def _ok(data, status: int = 200) -> httpx.Response:
    return httpx.Response(status, json={"success": True, "data": data})


def _no(message: str, status: int) -> httpx.Response:
    return httpx.Response(status, json={"success": False, "message": message})


@pytest.fixture()
def ra(env, monkeypatch):  # noqa: F811
    """RA 대역 · 스위치 · 카드 만들기. 기본 — 과제 key 로 찾으면 code 가 같은 객체 하나와 글자만 겹친 객체 하나가 오고, 태그 더하기는 받는다."""
    c, st, s = env
    monkeypatch.setattr(s, "insight_ra_project", False)      # 기본은 꺼짐 — 셸 환경에 켜는 줄이 있어도 시험은 꺼진 데서 시작한다
    seen: list[httpx.Request] = []
    state = SimpleNamespace(search=lambda body: _ok({"items": [_entity(EID, KEY, "알파 개발"), _entity(OTHER, KEY + "-old", "알파 개발 옛")],
                                                     "total": 2}),
                            add=lambda rid, body: _ok({"report_id": rid, "entity_ids": [11, *body["entity_ids"]], "added": 1}))

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        body = json.loads(req.content or b"{}")
        if req.method == "POST" and req.url.path == "/api/entities/search":
            return state.search(body)
        if req.method == "POST" and req.url.path.startswith("/api/reports/") and req.url.path.endswith("/entities/add"):
            return state.add(int(req.url.path.split("/")[3]), body)
        return _no("Not Found", 404)
    monkeypatch.setattr(RA, "_TRANSPORT", httpx.MockTransport(handler))

    def on(flag: bool = True) -> None:
        monkeypatch.setattr(s, "insight_ra_project", flag)

    def login(who: str) -> dict:
        from app.auth.routes.local import _rl
        _rl.clear()
        return _login(c, who)

    def card(cid: str = "a", *, who: str = "me@example.com", widen: bool = True, **kw) -> str:
        _relay(st, owner=who, cid=cid, **kw)
        iid = f"ins:web:{cid}:r1:default"
        h = login(who)
        assert c.post(f"/insights-api/cards/{iid}/confirm", headers=h).status_code == 200
        if widen:
            assert c.post(f"/insights-api/cards/{iid}/widen", json={"to": "org"}, headers=h).status_code == 200
        return iid

    def connect(who: str = "me@example.com", workspace: str = "") -> None:
        app.state.user_store.set_connection(email=who, service="reportarchive", token="rat_test", workspace=workspace)

    def go(iid: str, who: str = "me@example.com"):
        return c.post(f"/insights-api/cards/{iid}/ra", headers=login(who))

    return SimpleNamespace(c=c, st=st, s=s, seen=seen, state=state, on=on, login=login, card=card, connect=connect, go=go)


def _ra_keys(st) -> list[str]:
    with closing(st._conn().execute("SELECT k FROM insight_meta WHERE k LIKE 'ra:%'")) as cur:
        return [r[0] for r in cur.fetchall()]


def _audits(s, event: str = "insight_ra_projected") -> list[tuple[str, dict]]:
    with closing(sqlite3.connect(s.agent_audit_log_path)) as db:
        return [(st, json.loads(m)) for st, m in db.execute("SELECT status, meta FROM agent_audit WHERE event=?", (event,)).fetchall()]


# ── 꺼짐(기본) ─────────────────────────────────────────────────────────────────────────────────────
def test_꺼져_있으면_창구가_없는_것과_같고_읽기와_거두기의_답이_바이트까지_같다(ra, monkeypatch):
    iid = ra.card("a")
    ra.connect()
    h = ra.login("me@example.com")
    nothing = ra.c.post(f"/insights-api/cards/{iid}/zz-none", headers=h)
    got = ra.c.post(f"/insights-api/cards/{iid}/ra", headers=h)
    assert (got.status_code, got.content) == (nothing.status_code, nothing.content) and got.status_code == 404, \
        "꺼져 있으면 없는 창구와 같은 답이다"
    paths = ("/insights-api/mine", f"/insights-api/project?sp_task={KEY}", "/insights-api/review", f"/insights-api/cards/{iid}")
    off = {p: ra.c.get(p).content for p in paths}
    keep = IR._with_ra
    monkeypatch.setattr(IR, "_with_ra", lambda request, settings, views: views)
    assert {p: ra.c.get(p).content for p in paths} == off, "꺼져 있으면 ra 칸을 다는 자리가 아무것도 바꾸지 않는다"
    monkeypatch.setattr(IR, "_with_ra", keep)
    assert all(b'"ra"' not in b for b in off.values())
    # 켜기 전에 RA 에 단 줄이 남아 있어도(스위치를 껐다) 거두기 답은 종전 그대로다 — 원장 표지만 맞춘다
    ra.st.meta_set(f"ra:{iid}", json.dumps({"state": RA.PROJECTED, "report_id": 7, "entity_id": EID}))
    out = ra.c.post(f"/insights-api/cards/{iid}/withdraw", headers=h)
    assert out.status_code == 200 and out.json() == {"id": iid, "status": "withdrawn"}
    assert RA.record(ra.st, iid)["state"] == RA.WITHDRAWN
    assert ra.seen == [], "꺼져 있으면 RA 를 부르지 않는다"


# ── 켬 — 다는 길 ─────────────────────────────────────────────────────────────────────────────────────
def test_조직에_연_확인_카드는_그_사람의_RA_연결로_보고서에_과제_객체를_단다(ra):
    ra.on()
    iid = ra.card("a")
    ra.connect(workspace="dept-a")
    r = ra.go(iid)
    assert r.status_code == 200, r.text
    got = r.json()
    assert got["already"] is False and got["ra"]["state"] == "projected" and got["ra"]["report_id"] == CARD["report_id"]
    assert (got["ra"]["entity_id"], got["ra"]["type_slug"], got["ra"]["value"], got["ra"]["added"], got["ra"]["by"]) == (
        EID, "project", "알파 개발", True, "me@example.com")
    assert "태그를 달았다" in got["note"] and "떼지 않는다" in got["note"]
    search, add = ra.seen
    assert (search.method, search.url.path, json.loads(search.content)) == ("POST", "/api/entities/search", {"q": KEY, "limit": 200})
    assert (add.url.path, json.loads(add.content)) == ("/api/reports/7/entities/add", {"entity_ids": [EID]}), "code 가 글자 그대로 같은 객체만"
    for req in ra.seen:
        assert req.headers["authorization"] == "Bearer rat_test" and req.headers["x-workspace-slug"] == "dept-a", \
            "등록한 토큰과 그 사람이 고른 부서로 — 서비스 자격으로 내려가지 않는다"
    assert _audits(ra.s) == [("ok", {"id": iid, "report_id": 7, "entity_id": EID, "added": True})]
    # 한 카드는 한 번만 — 원장에 줄이 있으면 RA 를 부르지 않는다
    again = ra.go(iid)
    assert again.status_code == 200 and again.json()["already"] is True and again.json()["ra"] == got["ra"] and len(ra.seen) == 2
    # 화면의 읽기에는 카드마다 ra 칸(단 줄 · 아직이면 null)이 선다
    other = ra.card("b")
    ra.login("me@example.com")
    mine = {x["id"]: x for x in ra.c.get("/insights-api/mine").json()["shared"]}
    assert mine[iid]["ra"] == got["ra"] and mine[other]["ra"] is None
    cells = ra.c.get("/insights-api/project", params={"sp_task": KEY}).json()["rounds"]
    assert {x["id"]: x["ra"] for cell in cells for x in cell["cards"]} == {iid: got["ra"], other: None}
    assert ra.c.get(f"/insights-api/cards/{iid}").json()["ra"] == got["ra"]
    ra.login("peer@example.com")
    assert ra.c.get(f"/insights-api/cards/{iid}").json()["ra"] == got["ra"], "카드를 볼 수 있는 사람은 그 카드가 RA 에 달렸다는 것도 본다"


def test_RA_가_이미_그_태그를_가졌으면_added_는_거짓이고_원장에는_한_번_적는다(ra):
    ra.on()
    iid = ra.card("a")
    ra.connect()
    ra.state.add = lambda rid, body: _ok({"report_id": rid, "entity_ids": [EID], "added": 0})
    r = ra.go(iid)
    assert r.status_code == 200 and r.json()["ra"]["added"] is False and _ra_keys(ra.st) == [f"ra:{iid}"]


def test_위임_박스는_그_사람의_위임_토큰으로_부르고_부서_머리를_싣지_않는다(ra, monkeypatch):
    ra.on()
    iid = ra.card("a")
    ra.connect(workspace="tf-x")                     # 등록 토큰 시절에 고른 부서 — 위임 길에서는 싣지 않는다(L21-6 ②)
    monkeypatch.setattr(ra.s, "ra_sso_secret", "sso-secret")
    asked = []

    async def fake_sso(settings, *, email, name):
        asked.append(email)
        return "rat_from_sso"
    monkeypatch.setattr(R.ra_sso, "ra_user_token", fake_sso)
    assert ra.go(iid).status_code == 200
    assert asked and set(asked) == {"me@example.com"}
    assert all(q.headers["authorization"] == "Bearer rat_from_sso" and "x-workspace-slug" not in q.headers for q in ra.seen)


# ── 켬 — 달지 않는 때 ─────────────────────────────────────────────────────────────────────────────────
def _plat(ra) -> str:
    """조직에 열었지만 plat 토큰이 남은 카드(widen 은 plat 토큰을 지키고 org 를 더한다 — routes.widen)."""
    iid = ra.card("plat", widen=False)
    assert ra.st.update(iid, scope=["org", "plat:risk"])
    return iid


def test_조직에_연_확인_카드가_아니면_RA_를_부르지_않고_까닭을_준다(ra):
    ra.on()
    ra.connect()
    cases = {
        ra.card("draft-like", widen=False): "조직에 연 카드만",                                    # 확인했지만 같은 소속까지
        _plat(ra): "플랫폼 권한",
        ra.card("norep", cards=({**CARD, "report_id": None},)): "RA 보고서 번호가 없다",
        ra.card("badrep", cards=({**CARD, "report_id": "7a"},)): "RA 보고서 번호가 없다",
        ra.card("long", subject={**CONFIRMED, "sp_task": "가" * 65}): "64자를 넘어",
    }
    _relay(ra.st, owner="me@example.com", cid="d")                                                  # 초안
    cases["ins:web:d:r1:default"] = "확인한 카드만"
    dp = ra.card("dp")
    assert ra.c.post(f"/insights-api/cards/{dp}/dispute", json={"note": "틀렸다"}, headers=ra.login("me@example.com")).status_code == 200
    cases[dp] = "확인한 카드만"
    for iid, want in cases.items():
        r = ra.go(iid)
        assert r.status_code == 409 and want in r.json()["detail"], (iid, r.text)
    assert ra.seen == [] and _ra_keys(ra.st) == [] and _audits(ra.s) == []


def test_주인이_아니거나_권한이_없거나_PAT_면_달지_않는다(ra, monkeypatch):
    ra.on()
    iid = ra.card("a")
    for who in ("peer@example.com", "boss@example.com", "me@example.com"):
        ra.connect(who)
    assert ra.go(iid, "peer@example.com").status_code == 403, "같은 소속은 카드를 보지만 주인이 아니다"
    assert ra.go(iid, "boss@example.com").status_code in (403, 404), "관리자도 남의 카드를 그 사람의 RA 보고서에 달지 않는다"
    pat = R._chat_user_pat(app.state.keystore, ra.s, _principal("me@example.com"))
    ra.c.cookies.clear()
    r = ra.c.post(f"/insights-api/cards/{iid}/ra", headers={"Authorization": f"Bearer {pat}"})
    assert r.status_code in (401, 403), "쓰기는 세션 + CSRF 만 — 사람이 화면에서 누른다"
    ra.login("me@example.com")
    assert ra.c.post(f"/insights-api/cards/{iid}/ra").status_code == 403, "CSRF 머리 없이는 받지 않는다"
    real = IR.ensure

    def no_ra(principal, *keys, any_of=False):
        if "plat:reportarchive" in keys:
            from app.auth.errors import AuthError
            raise AuthError("권한이 없습니다(plat:reportarchive)", status_code=403)
        return real(principal, *keys, any_of=any_of)
    monkeypatch.setattr(IR, "ensure", no_ra)
    r = ra.go(iid)
    assert r.status_code == 403 and "plat:reportarchive" in r.text
    assert ra.seen == [] and _ra_keys(ra.st) == []


def test_RA_연결이_없으면_RA_를_부르지_않고_무엇을_고칠지_말한다(ra):
    ra.on()
    iid = ra.card("a")
    r = ra.go(iid)
    assert r.status_code == 400 and "외부 연결" in r.json()["detail"] and ra.seen == [] and _ra_keys(ra.st) == []
    assert _audits(ra.s) == [("failed", {"id": iid, "error": "no_ra_connection"})]


@pytest.mark.parametrize("found, why", [
    ({"items": [_entity(OTHER, KEY + "-old", "알파 개발 옛")], "total": 1}, "객체가 없다"),                    # 글자만 겹친다
    ({"items": [_entity(OTHER, KEY.upper() + "X", "x")], "total": 1}, "객체가 없다"),
    ({"items": [_entity(OTHER, None, KEY)], "total": 1}, "객체가 없다"),                                       # 이름이 key 인 객체는 SP 객체가 아니다
    ({"items": [], "total": 0}, "객체가 없다"),
    ({"items": [_entity(EID, KEY, "알파"), _entity(OTHER, KEY, "알파 사본", type_slug="model")], "total": 2}, "2개"),
    ({"items": [_entity(EID, KEY, "알파")], "total": 201}, "다 보지 못했다"),
    ({"items": [_entity(EID, KEY, "알파")]}, "다 보지 못했다"),                                                # total 이 없다 — 모른다
    ({"items": [_entity(EID, KEY, "알파", status="deprecated")], "total": 1}, "객체가 없다"),                  # SP 에서 지워진 객체
])
def test_RA_과제_객체가_하나로_서지_않으면_달지_않는다(ra, found, why):
    ra.on()
    iid = ra.card("a")
    ra.connect()
    ra.state.search = lambda body: _ok(found)
    r = ra.go(iid)
    assert r.status_code == 409 and why in r.json()["detail"], r.text
    assert [q.url.path for q in ra.seen] == ["/api/entities/search"] and _ra_keys(ra.st) == []


@pytest.mark.parametrize("step, reply, status, why", [
    ("search", _no("유효하지 않은 토큰입니다.", 401), 502, "RA 토큰을 받지 않았습니다"),
    ("search", _no("Internal server error", 500), 502, "답하지 못했습니다"),
    ("add", _no("이 보고서를 편집할 권한이 없습니다.", 403), 403, "주인 · 편집자만"),
    ("add", _no("Out of workspace scope", 403), 403, "Out of workspace scope"),
    ("add", _no("Report not found: 7", 404), 404, "보고서가 Report Archive 에 없습니다"),
    ("add", _no("Validation failed", 422), 422, "받지 않았습니다"),
    ("add", _ok({"report_id": 7, "entity_ids": [11], "added": 0}), 502, "달렸는지 모릅니다"),
    ("add", httpx.Response(200, text="<html>"), 502, "달렸는지 모릅니다"),
])
def test_RA_가_거절하면_까닭을_옮기고_원장에_적지_않는다(ra, step, reply, status, why):
    ra.on()
    iid = ra.card("a")
    ra.connect()
    if step == "search":
        ra.state.search = lambda body: reply
    else:
        ra.state.add = lambda rid, body: reply
    r = ra.go(iid)
    assert r.status_code == status and why in r.json()["detail"], r.text
    assert _ra_keys(ra.st) == [] and _audits(ra.s)[-1][0] == "failed"
    ra.state.search = lambda body: _ok({"items": [_entity(EID, KEY, "알파")], "total": 1})
    ra.state.add = lambda rid, body: _ok({"report_id": rid, "entity_ids": body["entity_ids"], "added": 1})
    assert ra.go(iid).status_code == 200, "원장에 적지 않았으니 다시 누르면 단다"


def test_RA_에_닿지_못하면_502_이고_원장에_적지_않는다(ra):
    ra.on()
    iid = ra.card("a")
    ra.connect()

    def down(body):
        raise httpx.ConnectError("refused")
    ra.state.search = down
    r = ra.go(iid)
    assert r.status_code == 502 and "닿지 못했습니다(ConnectError)" in r.json()["detail"] and _ra_keys(ra.st) == []


# ── 거두기 ───────────────────────────────────────────────────────────────────────────────────────────
def test_거두면_RA_는_부르지_않고_원장_표지만_바꾸고_태그가_남는다고_알린다(ra):
    ra.on()
    iid = ra.card("a")
    ra.connect()
    assert ra.go(iid).status_code == 200
    n = len(ra.seen)
    out = ra.c.post(f"/insights-api/cards/{iid}/withdraw", headers=ra.login("me@example.com"))
    assert out.status_code == 200 and len(ra.seen) == n, "거두기는 RA 를 부르지 않는다(사람 권한으로 태그 하나만 떼는 길이 없다)"
    body = out.json()
    assert body["status"] == "withdrawn" and body["ra"]["state"] == "withdrawn" and body["ra"]["report_id"] == 7
    assert "RA 에 남는다" in body["ra"]["note"] and "손으로 뗀다" in body["ra"]["note"]
    rec = RA.record(ra.st, iid)
    assert rec["state"] == "withdrawn" and rec["withdrawn_by"] == "me@example.com" and rec["entity_id"] == EID
    assert ra.go(iid).status_code == 404, "거둔 카드는 없는 것과 같다 — 다시 달지 않는다"
    # 투영하지 않은 카드를 거두면 답은 종전 그대로다
    b = ra.card("b")
    assert ra.c.post(f"/insights-api/cards/{b}/withdraw", headers=ra.login("me@example.com")).json() == {"id": b, "status": "withdrawn"}
    assert RA.record(ra.st, b) is None


def test_사람_PAT_의_읽기에는_ra_칸이_없다(ra):
    ra.on()
    iid = ra.card("a")
    ra.connect()
    assert ra.go(iid).status_code == 200
    pat = R._chat_user_pat(app.state.keystore, ra.s, _principal("me@example.com"))
    ra.c.cookies.clear()
    auth = {"Authorization": f"Bearer {pat}"}
    for path in (f"/insights-api/cards/{iid}", "/insights-api/mine", f"/insights-api/project?sp_task={KEY}", "/insights-api/review",
                 f"/insights-api/find?sp_task={KEY}"):
        r = ra.c.get(path, headers=auth)
        assert r.status_code == 200 and b'"ra"' not in r.content, path


# ── 단위 ─────────────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("rid, want", [(7, 7), ("7", 7), (0, None), (-1, None), (True, None), ("7a", None), ("٧", None), (None, None),
                                       (7.0, None)])
def test_보고서_번호는_양의_정수만(rid, want):
    assert RA.report_id_of({"card": {"report_id": rid}}) == want


def test_원장_줄의_꼴이_틀리면_없는_것으로_읽는다(ra):
    for raw in ("[1]", "글", "{", "null"):
        ra.st.meta_set("ra:x", raw)
        assert RA.record(ra.st, "x") is None
    assert RA.public({"state": "withdrawn", "report_id": 7}) is None and RA.public(None) is None
    assert RA.mark_withdrawn(ra.st, "없는 카드", "me@example.com") is None


def test_보내는_곳과_칸이_RA_소스와_맞는다():
    """RA v0.186.3 소스와 견준다 — 객체 검색 · 태그 더하기의 길 · 칸, SP 받기의 code 규칙, 객체 쓰기가 관리자 전용이라는 것."""
    if not _RA_SRC.exists():
        pytest.skip(f"형제 리포 없음: {_RA_SRC}")
    ent_routes = (_RA_SRC / "modules" / "entities" / "routes.py").read_text(encoding="utf-8")
    ent_schemas = (_RA_SRC / "modules" / "entities" / "schemas.py").read_text(encoding="utf-8")
    rep_routes = (_RA_SRC / "modules" / "reports" / "routes.py").read_text(encoding="utf-8")
    rep_schemas = (_RA_SRC / "modules" / "reports" / "schemas.py").read_text(encoding="utf-8")
    mounts = (_RA_SRC / "modules" / "__init__.py").read_text(encoding="utf-8")
    sp_pull = (_RA_SRC / "modules" / "connectors" / "sp_pull.py").read_text(encoding="utf-8")
    mcp = (_RA_SRC.parents[1] / "mcp_server" / "server.py").read_text(encoding="utf-8")
    assert 'prefix="/api/entities"' in mounts and 'prefix="/api/reports"' in mounts
    search = ent_routes.split('@entities_router.post("/search")', 1)[1].split("@entities_router", 1)[0]
    assert "Depends(entity_actor)" in search and "_require_admin" not in search, "객체 검색은 로그인만으로 된다"
    assert f"limit: int = Field(default=50, ge=1, le={RA.SEARCH_LIMIT})" in ent_schemas.split("class EntitySearchRequest", 1)[1][:800]
    read = ent_schemas.split("class EntityRead(BaseModel)", 1)[1][:1200]
    assert "code: Optional[str]" in read and "status: EntityStatus" in read and "type_slug: str" in read
    assert f"code: Optional[str] = Field(default=None, max_length={RA.CODE_MAX})" in ent_schemas
    assert f"code=key if len(key) <= {RA.CODE_MAX} else None" in sp_pull, "SP 받기는 code = SP 키(64자까지)"
    add = rep_routes.split('@router.post("/{report_id}/entities/add")', 1)[1].split("@router", 1)[0]
    assert "_require_admin" not in add and "can_edit(" in add and '"entity_ids": after' in add and '"added":' in add
    assert "entity_ids: list[int]" in rep_schemas.split("class ReportEntitiesAdd", 1)[1][:600]
    for tool in ("create_object", "update_object", "link_objects", "add_object_alias"):
        body = mcp.split(f"async def {tool}(", 1)[1][:600]
        assert "[시스템 관리자 전용]" in body, tool
    mine = Path(RA.__file__).read_text(encoding="utf-8").split('"""', 2)[2]
    assert not any(w in mine for w in ("/api/ai/ontology/write", "create_object", "update_object", "link_objects", "/relations")), \
        "객체 쓰기(관리자 몫)는 부르지 않는다"
