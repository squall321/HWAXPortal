# '위키에 남기기' · '해결됨' — 저장된 턴으로 MX 백서 원천 봉투를 짓고 그 사람 PAT 로 게이트웨이 wiki_submit_source 를 부른다(docs/mxwp-wiki P6 · P7)
"""고정하는 것.
  · 봉투는 **저장된 턴**으로 — 화면이 보낸 본문은 짝을 찾는 열쇠일 뿐이고, 저장된 답과 글자가 다르면 보내지 않는다(MW-D5).
  · MX 백서 계약의 칸만(모르는 칸은 거부된다) · 근거는 끝난 도구 호출 · 질문자 이름은 본문에 없다.
  · 범위는 그 사람의 소속 — 소속이 없으면 바로 남기기는 막고, 후보는 plat:mxwhitepaper 를 제안으로.
  · 권한(plat:mxwhitepaper) · 대화 주인 · 실패해도 감사 한 줄.
"""
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.access.policy import AccessPolicy
from app.agent import wiki_send as W
from app.agent.conv_store import ConversationStore
from app.auth.errors import AuthError
from app.auth.user_store import UserStore
from app.catalog.registry import CatalogRegistry
from app.config import Settings, get_settings
from app.main import app

_CONFIG = Path(__file__).resolve().parents[1] / "config"
NOW = datetime(2026, 10, 24, 9, 0, tzinfo=UTC)
ACT = [
    {"step": "부품 찾기", "tool": "find_part", "call": "c1", "ts": 1, "detail": "{\"q\": \"힌지\"}"},           # 시작 줄 — 결과 없음
    {"step": "부품 찾기", "tool": "find_part", "call": "c1", "ts": 2, "ok": True, "result_preview": "힌지 브래킷 · 412 MPa"},
    {"step": "부품 찾기", "tool": "find_part", "call": "c1", "ts": 3, "ok": True, "result_preview": "힌지 브래킷 · 412 MPa"},
    {"step": "올림", "tool": "convert_file", "ok": True, "origin": "upload", "detail": "{\"file\": \"검토.pptx\"}",
     "result_preview": "x" * 900},
]
MSGS = [
    {"role": "user", "content": "힌지 브래킷 응력은?", "meta": None, "ts": "2026-10-24T08:00:00+00:00"},
    {"role": "assistant", "content": "412 MPa 입니다.", "meta": {"activity": ACT}, "ts": "2026-10-24T08:00:05+00:00"},
    {"role": "assistant", "content": "올렸습니다", "meta": {"activity": [], "upload": True}, "ts": 1761292810},
]


# ── 순수 함수 ────────────────────────────────────────────────────────────────────────────────────
def test_짝은_저장된_답과_글자_그대로_같을_때만이고_앞의_질문과_함께다():
    assert W.pick_turn(MSGS, " 412 MPa 입니다. ") == (1, "힌지 브래킷 응력은?", MSGS[1])
    assert W.pick_turn(MSGS, "412 MPa 입니다 — 고친 말") is None, "화면이 고친 본문은 저장된 것이 아니다"
    assert W.pick_turn(MSGS, "올렸습니다") is None, "업로드 알림은 답이 아니다"
    assert W.pick_turn([MSGS[1]], "412 MPa 입니다.") is None, "앞에 질문이 없으면 문답이 아니다"
    twice = MSGS[:2] + [{"role": "user", "content": "다시"}, {"role": "assistant", "content": "412 MPa 입니다.", "meta": None}]
    assert W.pick_turn(twice, "412 MPa 입니다.")[:2] == (3, "다시"), "같은 본문이 여럿이면 가장 최근 것"


def test_봉투는_계약의_칸만이고_근거는_끝난_호출이다():
    env = W.qa_envelope(cid="c-1", index=1, question="힌지 브래킷 응력은?", message=MSGS[1], owner_email="u@corp.com",
                        audience=["aff:CAEG"], mode="button", outcome="solved", model=None, now=NOW)
    assert set(env) == {"schema", "kind", "origin", "title", "captured_at", "owner", "audience", "sensitivity", "consent", "body"}
    assert env["schema"] == "mxwp-source/1" and env["kind"] == "qa"
    assert env["origin"] == {"system": "hwax-portal", "ref": "conv:c-1:1"}
    assert env["consent"] == {"by": "u@corp.com", "at": NOW.isoformat(), "mode": "button"}
    assert env["captured_at"] == "2026-10-24T08:00:05+00:00"
    body = env["body"]
    assert set(body) == {"question", "answer", "evidence", "model", "outcome"} and body["model"] == "포털 챗"
    assert body["evidence"] == [
        {"kind": "tool", "ref": "find_part", "excerpt": "힌지 브래킷 · 412 MPa"},
        {"kind": "doc", "ref": "검토.pptx", "excerpt": "x" * W.EXCERPT_MAX}], "시작 줄 · 같은 결과 거듭은 빼고, 올린 문서는 doc"
    assert "u@corp.com" not in body["question"] + body["answer"]


def test_범위는_소속이고_소속이_없으면_후보만_제안_범위로():
    assert W.audience_for("CAEG", "button") == ["aff:CAEG"] == W.audience_for("CAEG", "candidate")
    assert W.audience_for("", "candidate") == [W.PLAT_KEY]
    with pytest.raises(AuthError) as e:
        W.audience_for("", "button")
    assert e.value.status_code == 409 and "해결됨" in str(e.value)


def test_시각은_시간대가_있는_ISO_로():
    assert W._iso(1761292810, NOW).endswith("+00:00") and W._iso(1761292810000, NOW) == W._iso(1761292810, NOW)
    assert W._iso("2026-10-24T08:00:00", NOW) == "2026-10-24T08:00:00+00:00"
    assert W._iso("모름", NOW) == NOW.isoformat() == W._iso(None, NOW)


def test_원천_번호가_없으면_성공으로_치지_않는다():
    assert W.result_of({"result": {"id": "u1", "short": "src_u1", "dedup": False}})["short"] == "src_u1"
    with pytest.raises(AuthError):
        W.result_of({"result": {"error": "x"}})


# ── 라우트 끝에서 끝(가짜 게이트웨이) ──────────────────────────────────────────────────────────────────
@pytest.fixture()
def portal(tmp_path, monkeypatch):
    for name in ("systems.yaml", "access.yaml"):
        shutil.copy(_CONFIG / name, tmp_path / name)
    (tmp_path / "routes.env").write_text("\n")
    s = Settings(_env_file=None, user_store_path=str(tmp_path / "users.sqlite"), local_bootstrap_admins="boss@corp.com",
                 catalog_path=str(tmp_path / "systems.yaml"), routes_path=str(tmp_path / "routes.env"),
                 access_path=str(tmp_path / "access.yaml"), conv_store_path=str(tmp_path / "conv.db"))
    app.dependency_overrides[get_settings] = lambda: s
    from app.auth.routes.local import _rl
    _rl.clear()
    calls = []

    async def fake_mcp(url, pat, tool, args, timeout=90.0):
        calls.append({"tool": tool, "args": args, "pat": bool(pat)})
        return {"result": {"id": "11111111-2222", "short": "src_11111111", "dedup": False, "doc_slug": "src-11111111",
                           "ingest_state": "queued"}}
    monkeypatch.setattr("app.agent.upload.mcp_call", fake_mcp)
    with TestClient(app) as c:
        keep = (app.state.user_store, app.state.access, app.state.catalog, app.state.conv_store)
        # 컨텍스트 진입 후 교체 — 실제 사용자 원장 · 대화 저장소를 건드리지 않는다
        app.state.user_store, app.state.access, app.state.catalog = UserStore(s), AccessPolicy(s), CatalogRegistry(s)
        app.state.conv_store = ConversationStore(s)
        for email in ("boss@corp.com", "user@corp.com"):
            c.post("/auth/local/signup", json={"email": email, "name": email.split("@")[0], "password": "pw123456"})
        h = _login(c, "boss@corp.com")
        assert c.post("/auth/local/users/user@corp.com/approve", json={"groups": []}, headers=h).status_code == 200
        yield c, calls
        app.state.user_store, app.state.access, app.state.catalog, app.state.conv_store = keep
    app.dependency_overrides.pop(get_settings, None)


def _login(c, email):
    r = c.post("/auth/local/login", json={"email": email, "password": "pw123456"})
    assert r.status_code == 200, r.text
    return {"X-CSRF-Token": c.cookies.get("hwax_csrf")}


def _conv(c, h) -> str:
    msgs = [{"role": m["role"], "content": m["content"], "meta": m["meta"]} for m in MSGS[:2]]
    r = c.post("/agent/conversations", json={"title": "응력", "messages": msgs}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_소속이_있는_사람은_바로_남기고_봉투는_저장된_턴이다(portal):
    c, calls = portal
    ha = _login(c, "boss@corp.com")
    assert c.patch("/auth/access/users/user@corp.com", json={"affiliation": "CAEG", "grants": []}, headers=ha).status_code == 200
    h = _login(c, "user@corp.com")
    cid = _conv(c, h)
    r = c.post(f"/agent/conversations/{cid}/wiki", json={"text": "412 MPa 입니다.", "model": "qwen-2.5"}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["short"] == "src_11111111" and r.json()["audience"] == ["aff:CAEG"]
    (call,) = calls
    assert call["tool"] == "wiki_submit_source" and call["pat"] and call["args"]["ingest"] is True
    env = call["args"]["envelope"]
    assert env["owner"] == {"email": "user@corp.com"} and env["consent"]["mode"] == "button"
    assert env["body"]["question"] == "힌지 브래킷 응력은?" and env["body"]["model"] == "qwen-2.5"
    assert env["body"]["evidence"][0]["ref"] == "find_part"

    calls.clear()
    r = c.post(f"/agent/conversations/{cid}/wiki", json={"text": "지어낸 답"}, headers=h)
    assert r.status_code == 409 and calls == [], "저장된 답과 다르면 게이트웨이를 부르지 않는다"


def test_소속이_없으면_후보만_되고_권한이_없으면_막힌다(portal):
    c, calls = portal
    ha = _login(c, "boss@corp.com")
    assert c.patch("/auth/access/users/user@corp.com", json={"grants": ["plat:mxwhitepaper"]}, headers=ha).status_code == 200
    h = _login(c, "user@corp.com")
    cid = _conv(c, h)
    assert c.post(f"/agent/conversations/{cid}/wiki", json={"text": "412 MPa 입니다."}, headers=h).status_code == 409
    r = c.post(f"/agent/conversations/{cid}/wiki", json={"text": "412 MPa 입니다.", "mode": "candidate"}, headers=h)
    assert r.status_code == 200 and r.json()["audience"] == [W.PLAT_KEY]
    assert calls[-1]["args"]["envelope"]["consent"]["mode"] == "candidate"

    ha = _login(c, "boss@corp.com")      # 한 클라이언트라 사용자로 들어간 뒤의 관리자 헤더는 낡았다 — 다시 들어간다
    assert c.patch("/auth/access/users/user@corp.com", json={"grants": []}, headers=ha).status_code == 200
    h = _login(c, "user@corp.com")
    n = len(calls)
    assert c.post(f"/agent/conversations/{cid}/wiki", json={"text": "412 MPa 입니다."}, headers=h).status_code == 403
    assert len(calls) == n


def test_남의_대화는_없는_것과_같다(portal):
    c, calls = portal
    ha = _login(c, "boss@corp.com")
    assert c.patch("/auth/access/users/user@corp.com", json={"affiliation": "CAEG", "grants": []}, headers=ha).status_code == 200
    hb = _login(c, "boss@corp.com")
    cid = _conv(c, hb)
    h = _login(c, "user@corp.com")
    assert c.post(f"/agent/conversations/{cid}/wiki", json={"text": "412 MPa 입니다."}, headers=h).status_code == 404
    assert calls == []
