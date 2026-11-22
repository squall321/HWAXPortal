# 절차의 전문가 팀 — 명세 team(선택) · 「심의로 넘기기」 미리보기의 팀 사본 · 「챗으로 가져가기」 의 대화 지정값 · 저장 권한(docs/expert-teams PLAN 2-3)
"""절차 라우트 시험의 오프라인 실행기 · 사람 둘(boss 관리자 · user 개별 허가)을 그대로 쓴다. 팀 저장소는 그 시험의 절차 저장소 연결을 같이 쓴다."""
import pytest
from tests.test_procedures_routes import (  # noqa: F401 — client 는 픽스처
    PREFIX,
    _finished_run,
    _login,
    _users,
    client,
)

from app.agent.teams import TeamStore
from app.main import app

TEAM = {"name": "열충격 검토팀", "lead": {"key": "rel-thermal", "name": "열충격 신뢰성 전문가"},
        "helpers": [{"key": "cae-b", "name": "구조 해석 전문가"}], "apps": ["odb-hub"], "tools": ["odb_list_components"]}
SPEC = {"title": "열충격 SED 판정", "steps": [{"backend": "ra", "tool": "find_reports", "args": {"q": "x"}}]}


@pytest.fixture()
def tu(client):  # noqa: F811 — 절차 라우트 시험의 픽스처에 팀 저장소를 더한다
    keep = app.state.team_store
    app.state.team_store = TeamStore(app.state.procedures_store)
    _users(client, grants=["feat:procedures", "feat:expert-chat", "feat:deliberation"])
    yield client, _login(client, "user@corp.com")
    app.state.team_store = keep


def _team(c, h, **over) -> dict:
    r = c.post("/agent/teams", json={**TEAM, **over}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def _run_of(c, h, team_id=None) -> str:
    """팀(있으면)을 단 절차 판본에서 나온 끝난 실행 — 단계 기록은 절차 라우트 시험의 것 그대로."""
    st = c.app.state.procedures_store
    me = c.get("/auth/me", headers=h).json()["subject"]
    got = st.create_procedure(owner_sub=me, spec={**SPEC, **({"team": team_id} if team_id else {})}, title=SPEC["title"],
                              visibility="private")
    rid = _finished_run(c, h)
    st._conn().execute("UPDATE runs SET procedure_version_id=? WHERE id=?", (got["version_id"], rid))
    st._conn().commit()
    return rid


def test_팀이_없는_절차의_넘기기와_챗은_팀_전과_같다(tu):
    c, h = tu
    rid = _run_of(c, h)
    d = c.get(f"{PREFIX}/runs/{rid}/handoff", headers=h).json()
    assert "team" not in d and "team_why" not in d
    r = c.post(f"{PREFIX}/runs/{rid}/chat", headers=h).json()
    assert set(r) == {"conversation_id", "title"}
    conv = c.get(f"/agent/conversations/{r['conversation_id']}", headers=h).json()
    assert conv["messages"][0]["meta"] is None


def test_심의로_넘기기는_팀_사본을_좌석으로_미리_채울_수_있게_싣는다(tu):
    c, h = tu
    t = _team(c, h)
    rid = _run_of(c, h, t["id"])
    d = c.get(f"{PREFIX}/runs/{rid}/handoff", headers=h).json()
    assert d["team"]["id"] == t["id"] and d["team"]["lead"] == TEAM["lead"] and d["team"]["helpers"] == TEAM["helpers"]
    assert d["team_why"] == "" and d["evidence_count"] == 2, "근거는 그대로 — 팀은 도구 단계를 바꾸지 않는다"
    assert c.delete(f"/agent/teams/{t['id']}", headers=h).status_code == 200
    d = c.get(f"{PREFIX}/runs/{rid}/handoff", headers=h).json()
    assert d["team"] is None and "찾을 수 없다" in d["team_why"], "지운 팀은 null + 까닭 — 심의 화면은 추천으로 채운다"


def test_챗으로_가져가면_팀이_대화_지정값이_된다(tu):
    c, h = tu
    t = _team(c, h)
    rid = _run_of(c, h, t["id"])
    r = c.post(f"{PREFIX}/runs/{rid}/chat", headers=h)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["team"]["id"] == t["id"] and body["team"]["apps"] == ["odb-hub"] and body["team"]["tools"] == ["odb_list_components"]
    conv = c.get(f"/agent/conversations/{body['conversation_id']}", headers=h).json()
    assert conv["messages"][0]["meta"] == {"pinned_agent": "rel-thermal", "pinned_agent_name": "열충격 신뢰성 전문가",
                                           "pinned_agents": ["rel-thermal", "cae-b"]}, "챗 중계가 적는 꼴 그대로 — 다른 기기에서 열어도 전문가가 산다"
    # 나중에 팀을 고쳐도 이미 연 대화는 그대로(ET-3)
    assert c.patch(f"/agent/teams/{t['id']}", json={"expected_version": 1, "lead": {"key": "other"}}, headers=h).status_code == 200
    conv = c.get(f"/agent/conversations/{body['conversation_id']}", headers=h).json()
    assert conv["messages"][0]["meta"]["pinned_agent"] == "rel-thermal"


def test_보조가_없는_팀은_pinned_agents_를_싣지_않는다(tu):
    c, h = tu
    t = _team(c, h, helpers=[])
    rid = _run_of(c, h, t["id"])
    cid = c.post(f"{PREFIX}/runs/{rid}/chat", headers=h).json()["conversation_id"]
    meta = c.get(f"/agent/conversations/{cid}", headers=h).json()["messages"][0]["meta"]
    assert meta == {"pinned_agent": "rel-thermal", "pinned_agent_name": "열충격 신뢰성 전문가"}


def test_팀을_붙인_절차는_전문가와_대화_권한도_있어야_저장하고_팀_칸_꼴을_본다(tu):
    c, h = tu
    t = _team(c, h)
    r = c.post(f"{PREFIX}/procedures", json={"title": "t", "spec": {**SPEC, "team": t["id"]}}, headers=h)
    assert r.status_code == 201, r.text
    got = c.get(f"{PREFIX}/procedures/{r.json()['id']}", headers=h).json()
    assert got["spec"]["team"] == t["id"] and got["mine"] is True
    plain = c.post(f"{PREFIX}/procedures", json={"title": "t", "spec": SPEC}, headers=h).json()
    assert "team" not in c.get(f"{PREFIX}/procedures/{plain['id']}", headers=h).json()["spec"], "안 적으면 정규 모양에 칸이 없다"
    bad = c.post(f"{PREFIX}/procedures", json={"title": "t", "spec": {**SPEC, "team": "tm_x"}}, headers=h)
    assert bad.status_code == 422 and "팀" in bad.json()["detail"]
    hb = _login(c, "boss@corp.com")
    assert c.get(f"{PREFIX}/procedures/{r.json()['id']}", headers=hb).json()["mine"] is False, "공개 절차를 남이 읽으면 mine 이 거짓"
    assert c.patch("/auth/access/users/user@corp.com", json={"grants": ["feat:procedures"]}, headers=hb).status_code == 200
    h = _login(c, "user@corp.com")
    r = c.post(f"{PREFIX}/procedures", json={"title": "t", "spec": {**SPEC, "team": t["id"]}}, headers=h)
    assert r.status_code == 403 and "feat:expert-chat" in r.json()["detail"]
