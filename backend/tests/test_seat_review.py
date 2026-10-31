# 관리자 '전문가 고르기 검토' — 관리자 · CSRF · 표시자 이름 · 누설 없는 화면 답 · 꺼져 있으면 안 읽는 모으기 · 이름 · 메일 · 대화 id 떼기(docs/request-1029 E-5 · E5-2)
"""포털은 저장하지 않고 에이전트 서버 창구(seat-questions/1 — docs/request-1029/e5-seat-review-contract.md)를 공유 비밀로 부른다. 원장 · 대화
저장소는 임시 폴더에, 에이전트 서버는 MockTransport 다. 가짜 답은 에이전트 서버 seat_questions.view · label · ingest 가 내는 꼴 그대로이고, 형제
리포에 그 모듈이 있으면 맨 끝 시험이 **진짜 모듈**로 같은 길을 한 번 더 돈다. 질문 글은 모두 지어낸 것이다(실사용 질문을 추적 파일에 두지 않는다 — D-E5-8).
"""
import importlib
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.agent import seat_review_harvest as hv
from app.agent.conv_store import ConversationStore
from app.auth.cookies import CSRF_COOKIE
from app.auth.provider import Principal
from app.auth.routes import seat_review as sr
from app.auth.token_store import TokenStore
from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.main import app

PW = "pw123456"
BASE = "/auth/admin/seat-review"
SECRET = "gw-test-secret"
# 화면에 닿으면 안 되는 칸 — 추천 순위 · 점수 · 신호 · 지금 좌석 · 사람이 고른 전문가 · 사람 · 대화(design-e5 2.1 L6) · 표본 질문(L1)
LEAKY = {"rank", "score", "scores", "desc_match", "matched_tags", "matched_name", "low_confidence", "why", "seats", "seat",
         "answered", "picked", "recommended", "candidates", "ranked", "user", "email", "conversation_id", "message_id", "ts",
         "sample_queries", "samples", "tags", "records", "records_total", "prompt", "labelers"}
MINE = {"primary": ["disp-foldable-stackup"], "also": [], "none": None, "unsure": False,
        "via": {"disp-foldable-stackup": "tree"}, "memo": "", "t": 1793260800}
# 에이전트 서버 seat_questions.view 의 꼴
VIEW = {"collect": True, "days": 60, "total": 2, "counts": {"persona": 1, "thinking": 1, "delib": 0, "expert_cmd": 0},
        "filtered": {"short": 0, "not_standalone": 1, "near_dup": 0}, "labeled": {"mine": 1, "any": 1},
        "labelers": ["boss@corp.com", "second@corp.com"],
        "items": [{"qid": "H-aaaaaaaaaaaa", "d": "2026-10-30", "src": "thinking", "text": "OCA 점탄성 물성을 어디서 구하나",
                   "mine": MINE, "others": 0},
                  {"qid": "H-bbbbbbbbbbbb", "d": "2026-10-29", "src": "persona", "text": "낙하 시 보드 변형률을 어떻게 재나요",
                   "mine": None, "others": 1}]}
POOL = {"recommended": [], "candidates": [], "light": True, "low_confidence": False, "axes": [],
        "tools": {"recommended": [], "expert_tools": [], "pipeline": [], "all": [], "apps": [], "areas": []},
        "pool": [{"key": "rel-drop-impact", "name": "낙하 시험", "tags": []}, {"key": "he-sim-smarttwin", "name": "운영자", "tags": []},
                 {"key": "cam-lens-molding", "name": "렌즈", "tags": ["렌즈"]}]}
DETAIL = {"key": "rel-drop-impact", "name": "낙하 시험", "role": "낙하 · 충격 시험의 조건 설계" + "가" * 900, "prompt": "역할 문서",
          "tags": ["낙하"], "samples": ["낙하 시험 조건은?"], "records": [{"id": "r1", "title": "카드", "data_type": "x"}],
          "records_total": 120, "operator": False, "apps": []}


def _route(req: httpx.Request) -> httpx.Response:
    """에이전트 서버 대역 — 경로마다 그쪽 꼴의 답."""
    p = req.url.path
    if p == "/seat-questions":
        return httpx.Response(200, json=VIEW)
    if p == "/seat-questions/label":
        b = json.loads(req.content)
        return httpx.Response(200, json={"ok": True, "qid": b["qid"], "by": b["by"], "removed": bool(b.get("remove"))})
    if p == "/seat-questions/ingest":
        return httpx.Response(200, json={"added": len(json.loads(req.content)["items"]), "dup": 0, "old": 0, "short": 0})
    if p == "/deliberate/experts":
        return httpx.Response(200, json=POOL)
    if p == "/catalog/agent":
        return httpx.Response(200, json=DETAIL)
    return httpx.Response(404, json={"detail": "Not Found"})


@pytest.fixture()
def box(tmp_path, monkeypatch):
    """boss · second · third = 원장 관리자 · user = 일반 사용자(이름 홍길동). 에이전트 서버는 agent['reply'] 로 답한다."""
    monkeypatch.delenv("PORTAL_ADMIN_EMAILS", raising=False)
    s = Settings(_env_file=None, user_store_path=str(tmp_path / "users.sqlite"),
                 token_store_path=str(tmp_path / "tokens.sqlite"), conv_store_path=str(tmp_path / "conv.sqlite"),
                 upload_staging_dir=str(tmp_path / "staging"), local_bootstrap_admins="boss@corp.com",
                 gateway_shared_token=SECRET, agent_server_url="http://agent.test/")
    app.dependency_overrides[get_settings] = lambda: s
    from app.auth.routes.local import _rl
    _rl.clear()
    seen: list[httpx.Request] = []
    agent = {"reply": _route}

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return agent["reply"](req)
    real = httpx.AsyncClient
    monkeypatch.setattr(sr.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    with TestClient(app) as c:
        keep = (app.state.user_store, app.state.token_store)
        app.state.user_store, app.state.token_store = UserStore(s), TokenStore(s)
        for email, name in (("boss@corp.com", "보스"), ("Second@corp.com", "둘째"), ("third@corp.com", "셋째"),
                            ("user@corp.com", "홍길동")):
            c.post("/auth/local/signup", json={"email": email, "name": name, "password": PW})
        for email in ("second@corp.com", "third@corp.com"):
            assert app.state.user_store.approve(email, by="boss@corp.com", groups=["portal-admin"])
        assert app.state.user_store.approve("user@corp.com", by="boss@corp.com", groups=[])
        yield c, s, agent, seen
        app.state.user_store, app.state.token_store = keep
    app.dependency_overrides.pop(get_settings, None)


def _login(c, email) -> dict:
    c.cookies.clear()
    assert c.post("/auth/local/login", json={"email": email, "password": PW}).status_code == 200
    return {"X-CSRF-Token": c.cookies.get(CSRF_COOKIE)}


def _keys_deep(v) -> set[str]:
    if isinstance(v, dict):
        return set(v) | {k for x in v.values() for k in _keys_deep(x)}
    if isinstance(v, list):
        return {k for x in v for k in _keys_deep(x)}
    return set()


LABEL = {"qid": "H-aaaaaaaaaaaa", "primary": ["disp-foldable-stackup"], "also": ["mech-psa-bonding"],
         "via": {"disp-foldable-stackup": "tree", "mech-psa-bonding": "search"}, "memo": "OCA 는 적층 담당"}


def test_관리자만_보고_에이전트_서버에_공유_비밀과_조건을_넘긴다(box):
    c, _s, _agent, seen = box
    h = _login(c, "user@corp.com")
    for method, path in (("GET", "/items"), ("GET", "/catalog"), ("GET", "/expert?key=rel-drop-impact"),
                         ("POST", "/label"), ("POST", "/collect")):
        assert c.request(method, BASE + path, json=LABEL, headers=h).status_code == 403, path
    assert not seen, "일반 사용자의 요청은 에이전트 서버에 닿지 않는다"
    _login(c, "second@corp.com")
    r = c.get(f"{BASE}/items", params={"src": "thinking", "limit": 50, "offset": 100})
    assert r.status_code == 200, r.text
    [req] = seen
    assert req.method == "GET" and req.url.host == "agent.test" and req.url.path == "/seat-questions"
    assert dict(req.url.params) == {"src": "thinking", "by": "second@corp.com", "limit": "50", "offset": "100"}, \
        "표시자 이름은 메일(소문자)이다 — 박스의 SEAT_QUESTIONS_LABELERS 와 글자 그대로 견준다"
    assert req.headers["authorization"] == f"Bearer {SECRET}" and req.headers["x-seat-contract"] == "seat-questions/1"
    d = r.json()
    assert d["contract"] == "seat-review/1" and d["me"] == {"by": "second@corp.com", "can_label": True}
    assert d["collect"] == {"on": True, "days": 60} and d["labelers_set"] is True
    assert [i["qid"] for i in d["items"]] == ["H-aaaaaaaaaaaa", "H-bbbbbbbbbbbb"], "차례는 그쪽 그대로(출처 번갈아 · 해시 — 점수가 아니다)"
    assert d["items"][0]["mine"] == MINE and d["items"][1]["others"] == 1
    _login(c, "third@corp.com")
    assert c.get(f"{BASE}/items").json()["me"] == {"by": "third@corp.com", "can_label": False}, \
        "SEAT_QUESTIONS_LABELERS 에 없는 관리자는 보기만 한다(그쪽 label 이 같은 규칙으로 거절한다)"
    assert c.get(f"{BASE}/items", params={"src": "rank"}).status_code == 422


def test_화면_답에는_순위_점수_지금_좌석이_없다(box):
    """누설 규칙 L6 — 에이전트 서버가 칸을 더 실어 보내도(옛 판 · 실수) 허용 목록이 걸러 화면에 닿지 않는다."""
    c, _s, agent, _seen = box
    leaky_item = {"qid": "H-cccccccccccc", "d": "2026-10-31", "src": "persona", "text": "카메라 모듈 낙하 손상 기준",
                  "rank": 1, "score": 0.91, "desc_match": 0.4, "matched_tags": ["낙하"], "low_confidence": False, "why": "표본 일치",
                  "seats": ["cam-module-reliability"], "picked": ["rel-drop-impact"], "answered": ["sim-drop-impact"],
                  "user": "user@corp.com", "conversation_id": "c0ffee", "ts": 1793260800, "others": 2,
                  "mine": {**MINE, "score": 0.5, "rank": 2, "seats": ["x-y"], "picked": ["rel-drop-impact"]}}
    agent["reply"] = lambda req: (httpx.Response(200, json={**VIEW, "items": [leaky_item], "ranked": ["a-b"],
                                                           "recommended": [{"key": "a-b", "score": 1}]})
                                  if req.url.path == "/seat-questions" else _route(req))
    _login(c, "boss@corp.com")
    d = c.get(f"{BASE}/items").json()
    assert not (_keys_deep(d) & LEAKY), _keys_deep(d) & LEAKY
    assert set(d) == {"contract", "total", "counts", "filtered", "labeled", "collect", "labelers_set", "me", "items"}
    assert set(d["items"][0]) == {"qid", "d", "src", "text", "mine", "others"}
    assert set(d["items"][0]["mine"]) == {"primary", "also", "none", "unsure", "via", "memo", "t"}
    txt = json.dumps(d, ensure_ascii=False)
    for v in ("rel-drop-impact", "sim-drop-impact", "cam-module-reliability", "c0ffee", "user@corp.com", "0.91",
              "second@corp.com"):
        assert v not in txt, f"{v} 가 화면 답에 실렸다"
    cat = c.get(f"{BASE}/catalog").json()
    assert cat == {"contract": "seat-review/1",
                   "experts": [{"key": "cam-lens-molding", "name": "렌즈"}, {"key": "rel-drop-impact", "name": "낙하 시험"}]}, \
        "운영자를 빼고 키 순 · 태그는 버린다"
    card = c.get(f"{BASE}/expert", params={"key": "rel-drop-impact"}).json()
    assert set(card) == {"contract", "key", "name", "desc", "error"} and len(card["desc"]) == 400 and card["error"] is None
    assert "낙하 시험 조건은?" not in json.dumps(card, ensure_ascii=False), "표본 질문은 카드에 싣지 않는다(L1)"


def test_카드는_명부_light_와_상세를_부르고_운영자는_부르지_않는다(box):
    c, _s, agent, seen = box
    _login(c, "boss@corp.com")
    c.get(f"{BASE}/catalog")
    sent = json.loads(seen[-1].content)
    assert seen[-1].url.path == "/deliberate/experts" and sent["light"] is True and "portal-admin" in sent["groups"], \
        "명부는 light(추천을 돌리지 않는다) — 화두 질의 순위가 생기지 않는다"
    c.get(f"{BASE}/expert", params={"key": "rel-drop-impact"})
    assert seen[-1].url.path == "/catalog/agent" and json.loads(seen[-1].content)["key"] == "rel-drop-impact"
    n = len(seen)
    assert c.get(f"{BASE}/expert", params={"key": "he-sim-smarttwin"}).status_code == 422 and len(seen) == n
    agent["reply"] = lambda req: httpx.Response(200, json={**DETAIL, "error": "session_failed"})
    assert c.get(f"{BASE}/expert", params={"key": "rel-drop-impact"}).json()["error"] == "detail_failed"


@pytest.mark.parametrize("payload", [{**VIEW, "contract": "seat-questions/2"}, {k: v for k, v in VIEW.items() if k != "items"}])
def test_꼴이나_판이_다르면_옮기지_않는다(box, payload):
    c, _s, agent, _seen = box
    agent["reply"] = lambda req: httpx.Response(200, json=payload)
    _login(c, "boss@corp.com")
    r = c.get(f"{BASE}/items")
    assert r.status_code == 502 and "꼴 · 판이 다르다" in r.json()["detail"], r.json()


@pytest.mark.parametrize("status, payload, want, text", [
    (401, {"error": "unauthorized"}, 502, "공유 비밀"),
    (503, {"error": "공유 비밀이 없다 — MCP_CONFIG 의 게이트웨이 연결에 Authorization(Bearer <GW_TOKEN>)이 없다"}, 502, "MCP_CONFIG"),
    (404, {"detail": "Not Found"}, 502, "낡았다"),
    (405, None, 502, "낡았다"),
    (404, {"error": "그 질문이 박스에 없다(지난 날짜 파일이 지워졌거나 qid 가 틀렸다)"}, 404, "그 질문이 박스에 없다"),
    (409, {"error": "모으기가 꺼져 있다 — 박스의 SEAT_QUESTIONS_COLLECT=1 뒤 재기동"}, 409, "SEAT_QUESTIONS_COLLECT"),
    (422, {"error": "표시자 'x' 는 이 박스의 SEAT_QUESTIONS_LABELERS 에 없다"}, 422, "SEAT_QUESTIONS_LABELERS"),
    (500, {"error": "터졌다"}, 502, "에이전트 서버 500 — 터졌다"),
])
def test_에이전트_서버_답을_포털_답으로_옮긴다(box, status, payload, want, text):
    c, _s, agent, _seen = box
    agent["reply"] = lambda req: httpx.Response(status, json=payload) if payload is not None else httpx.Response(status, text="no")
    _login(c, "boss@corp.com")
    r = c.get(f"{BASE}/items")
    assert r.status_code == want and text in r.json()["detail"], r.json()


def test_닿지_못하거나_공유_비밀이_없으면_까닭을_말한다(box):
    c, s, agent, seen = box
    _login(c, "boss@corp.com")

    def down(req):
        raise httpx.ConnectError("refused", request=req)
    agent["reply"] = down
    r = c.get(f"{BASE}/items")
    assert r.status_code == 502 and "닿지 못했다" in r.json()["detail"]
    s.gateway_shared_token = ""
    n = len(seen)
    r = c.get(f"{BASE}/items")
    assert r.status_code == 503 and "GATEWAY_SHARED_TOKEN" in r.json()["detail"] and len(seen) == n, "비밀이 없으면 부르지 않는다"


def test_표시는_CSRF_를_요구하고_표시자_이름을_붙여_넘긴다(box):
    c, _s, _agent, seen = box
    h = _login(c, "boss@corp.com")
    assert c.post(f"{BASE}/label", json=LABEL).status_code == 403, "CSRF 머리가 없다"
    assert not seen
    r = c.post(f"{BASE}/label", json=LABEL, headers=h)
    assert r.status_code == 200 and r.json() == {"contract": "seat-review/1", "ok": True, "qid": LABEL["qid"], "removed": False}
    sent = json.loads(seen[-1].content)
    assert seen[-1].url.path == "/seat-questions/label"
    assert sent == {"by": "boss@corp.com", "none": None, "unsure": False, **LABEL}, "그쪽 check_label 이 받는 칸만 — 모르는 칸은 422 다"
    r = c.post(f"{BASE}/label", json={"qid": "H-aaaaaaaaaaaa", "remove": True, "memo": "남지 않는다"}, headers=h)
    assert r.json()["removed"] is True and json.loads(seen[-1].content) == {"qid": "H-aaaaaaaaaaaa", "by": "boss@corp.com", "remove": True}
    c.post(f"{BASE}/label", json={"qid": "H-aaaaaaaaaaaa", "none": "core_data"}, headers=h)
    assert json.loads(seen[-1].content)["none"] == "core_data"


def test_표시자_이름은_그쪽이_받는_꼴로():
    def p(email):
        return Principal(subject=email, email=email)
    assert sr.by_of(p("Koo.Park@Corp.com")) == "koo.park@corp.com"
    assert sr.by_of(p("a" * 30 + "@long-domain.example.com")) == "a" * 30, "40자를 넘으면 메일 앞부분"
    assert sr.by_of(p("a+b@corp.com")) == "", "받지 않는 글자(+)가 들면 달 수 없다(빈 값 — 409)"


@pytest.mark.parametrize("body", [
    {"primary": []},
    {"primary": ["a-1", "a-2", "a-3", "a-4"]},
    {"primary": ["a-1"], "also": [f"b-{i}" for i in range(6)]},
    {"primary": ["a-1"], "also": ["a-1"]},
    {"primary": ["he-sim-smarttwin"]},
    {"primary": ["A-Upper"]},
    {"primary": ["a-1"], "via": {"a-1": "guess"}},
    {"primary": ["a-1"], "via": {"b-2": "tree"}},
    {"primary": ["a-1"], "none": "core_data"},
    {"none": "maybe"},
    {"unsure": True, "none": "out_of_pool"},
    {"also": ["a-1"], "unsure": True},
    {"qid": "H-../../etc", "unsure": True},
])
def test_표시_꼴은_포털에서도_막는다(box, body):
    c, _s, _agent, seen = box
    h = _login(c, "boss@corp.com")
    r = c.post(f"{BASE}/label", json={"qid": "H-aaaaaaaaaaaa", **body}, headers=h)
    assert r.status_code == 422 and not seen, r.text


def _seed(s: Settings, now: int) -> None:
    """지어낸 대화 — 출처 셋 · 넣지 않는 것 넷 · 창 밖 하나. 사람 이름(홍길동) · 메일이 글에 든다."""
    st = ConversationStore(s)
    rows: list[tuple[str, int]] = []

    def conv(msgs, ts=None):
        cid = st.create(owner_sub="user@corp.com", title="t")
        for role, content, meta in msgs:
            st.append(conversation_id=cid, owner_sub="user@corp.com", role=role, content=content, meta=meta)
        rows.append((cid, ts if ts is not None else now - 3600 + len(rows)))
    pin = {"pinned_agent": "rel-drop-impact", "pinned_agent_name": "낙하 시험", "pinned_agents": ["rel-drop-impact", "mech-drop-impact"]}
    conv([("user", "홍길동입니다. user@corp.com 으로 회신 주세요 — 낙하 시험에서 보드 크랙 판정은 어떻게 하나요?", pin),
          ("assistant", "답", None), ("user", "두 번째 발화는 첫 발화가 아니다", pin)])
    conv([("user", "일반 챗으로 먼저 물었다", None), ("user", "그다음에 전문가를 골랐다 — 앞선 사람 발화가 있어 넣지 않는다", pin)])
    conv([("user", "/띵킹 AP 패키지 열충격 SED 를 해석 없이 가늠하려면?", None),
          ("assistant", "## Thinking — 2명 답변 · 3명 기권\n…", None)])
    conv([("user", "/전문가 폴더블 힌지 토크", None), ("user", "/전문가", None), ("user", "/agents   battery swelling", None)])
    conv([("user", "/심의 낙하 크랙 원인", {"pinned_agent": "sim-drop-impact"})])
    conv([("user", "SmartTwin 낙하 잡을 제출해 줘", {"pinned_agent": "he-sim-smarttwin"})])
    conv([("user", "아주 오래전의 띵킹 질문은 창 밖이다", None), ("assistant", "## Thinking — 1명 답변", None)], ts=now - 90 * 86400)
    con = sqlite3.connect(s.resolve(s.conv_store_path))
    for cid, ts in rows:
        con.execute("UPDATE messages SET ts = ? WHERE conversation_id = ?", (ts, cid))
    con.commit()
    con.close()


def test_그쪽_모으기가_꺼져_있으면_대화_저장소를_읽지도_않는다(box, monkeypatch):
    c, _s, agent, seen = box
    monkeypatch.setattr(sr, "harvest", lambda *a, **k: pytest.fail("꺼져 있는데 대화 저장소를 읽었다"))
    agent["reply"] = lambda req: httpx.Response(200, json={**VIEW, "collect": False, "items": []})
    h = _login(c, "boss@corp.com")
    assert c.post(f"{BASE}/collect").status_code == 403, "CSRF 머리가 없다"
    r = c.post(f"{BASE}/collect", headers=h)
    assert r.status_code == 409 and "SEAT_QUESTIONS_COLLECT=1" in r.json()["detail"]
    assert [q.url.path for q in seen] == ["/seat-questions"], "스위치만 묻고 밀지 않는다"


def test_모으기는_이름_메일_대화_id_를_떼고_출처_셋을_나눠_민다(box, monkeypatch):
    c, s, _agent, seen = box
    now = int(time.time())
    _seed(s, now)
    monkeypatch.setattr(sr, "INGEST_MAX", 3)
    h = _login(c, "boss@corp.com")
    r = c.post(f"{BASE}/collect", headers=h)
    assert r.status_code == 200, r.text
    pushes = [q for q in seen if q.url.path == "/seat-questions/ingest"]
    assert len(pushes) == 2 and all(q.headers["authorization"] == f"Bearer {SECRET}" for q in pushes), "1,000건씩(여기서는 3) 나눠 민다"
    bodies = [json.loads(q.content) for q in pushes]
    assert all(set(b) == {"items"} for b in bodies), "그쪽 ingest 는 {items} 만 받는다"
    items = [i for b in bodies for i in b["items"]]
    got = [(i["src"], i["text"]) for i in items]
    assert got == [
        ("persona", "[이름]입니다. [메일] 으로 회신 주세요 — 낙하 시험에서 보드 크랙 판정은 어떻게 하나요?"),
        ("thinking", "AP 패키지 열충격 SED 를 해석 없이 가늠하려면?"),
        ("expert_cmd", "폴더블 힌지 토크"),
        ("expert_cmd", "battery swelling"),
        ("persona", "SmartTwin 낙하 잡을 제출해 줘"),
    ], got
    assert all(set(i) <= {"src", "text", "ts", "picked"} for i in items), "대화 · 메시지 id · 사람을 싣지 않는다"
    assert all(now - 7200 < i["ts"] <= now for i in items), "시각은 그쪽이 날짜 · 창 밖 거름에만 쓴다"
    picked = {i["text"].split()[0]: i.get("picked") for i in items if i["src"] == "persona"}
    assert picked == {"[이름]입니다.": ["rel-drop-impact", "mech-drop-impact"], "SmartTwin": ["he-sim-smarttwin"]}, \
        "사람이 고른 전문가는 박스 파일에만 간다(화면에는 안 싣는다) — 운영자를 고른 대화도 그쪽 실시간 모으기처럼 넣는다"
    raw = b"".join(q.content for q in pushes).decode()
    for v in ("user@corp.com", "홍길동", "두 번째 발화", "그다음에 전문가", "/심의", "창 밖"):
        assert v not in raw, f"{v} 가 밀렸다"
    con = sqlite3.connect(s.resolve(s.conv_store_path))
    for (cid,) in con.execute("SELECT id FROM conversations"):
        assert cid not in raw, "대화 id 가 밀렸다"
    con.close()
    d = r.json()
    assert d["harvest"] == {"days": 60, "seen": {"expert_cmd": 3, "thinking": 1, "persona": 3}, "sent": 5,
                            "skipped": {"slash": 1, "empty": 1}, "scrubbed": 1}
    assert d["agent"] == {"added": 5, "dup": 0, "old": 0, "short": 0}, "에이전트 서버 답에서 수만 더해 옮긴다"


def test_떼어_내기_조각들():
    nre = hv.name_re(["홍길동", "A", " 김 철수 ", "박구현(CAE그룹)", "Jo"], ["koo.park", "ab", "user"])
    assert hv.scrub("홍길동님 · 김 철수 책임 · 박구현 프로 · KOO.PARK 와 koo.parker · ab 팀 · user 경험 · Job · x@y.co 로", nre) == \
        "[이름]님 · [이름] 책임 · [이름] 프로 · [이름] 와 koo.parker · ab 팀 · user 경험 · Job · [메일] 로", \
        "1자 이름 · 2자 영문 이름 · 낱말 꼴 메일 앞부분은 가리지 않는다(질문 글을 지운다)"
    assert hv.scrub("메일 a.b@c.example 만", None) == "메일 [메일] 만"
    assert hv.strip_agent_trigger("/agents  x y") == "x y" and hv.strip_agent_trigger("/agent: z") == ": z"
    assert hv.strip_agent_trigger("/전문가") == "" and hv.strip_agent_trigger("전문가 추천") is None
    assert hv.strip_thinking_trigger("/Thinking 낙하") == "낙하" and hv.strip_thinking_trigger("/띵킹") == "/띵킹"
    assert hv._pinned('{"pinned_agent": "a-1", "pinned_agents": ["b-2", "a-1"]}') == ["b-2", "a-1"], "목록이 있으면 목록(그쪽 _persona_keys)"
    assert hv._pinned('{"pinned_agent": "a-1"}') == ["a-1"] and hv._pinned("not json") == [] and hv._pinned(None) == []


# ── 진짜 모듈로 — 형제 리포의 에이전트 서버 seat_questions(없으면 건너뛴다) ─────────────────────────────
# 에이전트 서버 리포를 다른 자리(아직 합치지 않은 작업 트리)에서 보려면 HWAX_AGENT_SERVER_ROOT 로 준다.
AGENT_DIR = Path(os.environ.get("HWAX_AGENT_SERVER_ROOT") or Path(__file__).resolve().parents[3] / "HWAXAgentServer")


def test_진짜_에이전트_서버_모듈과_한_바퀴(box, tmp_path, monkeypatch):
    """포털이 미는 꼴을 그쪽 ingest 가 받고 · 그쪽 view 를 포털이 걸러 화면에 내고 · 포털 표시를 그쪽 label 이 받는다(계약 seat-questions/1)."""
    if not (AGENT_DIR / "seat_questions.py").exists():
        pytest.skip(f"형제 리포에 seat_questions.py 가 없다: {AGENT_DIR}")
    c, s, agent, _seen = box
    monkeypatch.setenv("SEAT_EVAL_DIR", str(tmp_path / "seat-eval"))
    monkeypatch.setenv("SEAT_QUESTIONS_COLLECT", "1")
    monkeypatch.setenv("SEAT_QUESTIONS_LABELERS", "boss@corp.com")
    monkeypatch.syspath_prepend(str(AGENT_DIR))
    monkeypatch.setattr(sys, "dont_write_bytecode", True)     # 형제 리포에 이 venv 의 .pyc 를 남기지 않는다
    for m in ("seat_questions", "seat_probe"):
        sys.modules.pop(m, None)
    sq = importlib.import_module("seat_questions")
    try:
        def real(req: httpx.Request) -> httpx.Response:
            if req.headers.get("authorization") != f"Bearer {SECRET}":
                return httpx.Response(401, json={"error": "unauthorized"})
            p = req.url.path
            if p == "/seat-questions":
                q = req.url.params
                return httpx.Response(200, json=sq.view(q.get("src") or None, q.get("by") or None,
                                                         limit=int(q.get("limit") or 100), offset=int(q.get("offset") or 0)))
            if p in ("/seat-questions/label", "/seat-questions/ingest"):
                body = json.loads(req.content)
                if p.endswith("ingest"):
                    assert isinstance(body, dict) and set(body) == {"items"}, body    # 그쪽 창구가 거르는 본문 꼴
                    st, out = sq.ingest(body["items"])
                else:
                    st, out = sq.label(body)
                return httpx.Response(st, json=out)
            return _route(req)
        agent["reply"] = real
        _seed(s, int(time.time()))
        h = _login(c, "boss@corp.com")
        r = c.post(f"{BASE}/collect", headers=h)
        assert r.status_code == 200, r.text
        assert r.json()["agent"]["added"] >= 4, r.json()
        d = c.get(f"{BASE}/items").json()
        assert d["collect"]["on"] is True and d["me"] == {"by": "boss@corp.com", "can_label": True}
        assert not (_keys_deep(d) & LEAKY), _keys_deep(d) & LEAKY
        txt = json.dumps(d, ensure_ascii=False)
        assert "홍길동" not in txt and "user@corp.com" not in txt and "rel-drop-impact" not in txt, "고른 전문가 · 사람이 화면에 없다"
        q = next(i for i in d["items"] if i["src"] == "thinking")
        r = c.post(f"{BASE}/label", json={"qid": q["qid"], "primary": ["sim-thermal-sed"], "via": {"sim-thermal-sed": "search"}},
                   headers=h)
        assert r.status_code == 200 and r.json()["ok"] is True, r.text
        mine = next(i for i in c.get(f"{BASE}/items").json()["items"] if i["qid"] == q["qid"])["mine"]
        assert mine["primary"] == ["sim-thermal-sed"] and mine["via"] == {"sim-thermal-sed": "search"}
        h2 = _login(c, "second@corp.com")
        r = c.post(f"{BASE}/label", json={"qid": q["qid"], "unsure": True}, headers=h2)
        assert r.status_code == 422 and "SEAT_QUESTIONS_LABELERS" in r.json()["detail"], "다는 사람은 그쪽 설정이 정한다"
    finally:
        for m in ("seat_questions", "seat_probe"):
            sys.modules.pop(m, None)
