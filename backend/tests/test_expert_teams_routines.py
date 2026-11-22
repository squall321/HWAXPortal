# 분석 루틴의 전문가 팀 — 명세 team · 단계 team(덮어쓰기 · 빈 글 = 팀 없이) · 실행을 만들 때의 사본 · 못 풀면 null + 까닭 · 리스크 심사 계열 제외 · 준비도 줄(docs/expert-teams)
"""게이트웨이는 루틴 API 시험의 MockTransport 그대로다(tests/test_routines_api). 팀 저장소는 그 시험의 절차 저장소 연결을 같이 쓴다.
사람 — boss(원장 관리자 — 전부) · user(개별 허가 feat:routines · feat:expert-chat 만 — HE팀 운영자의 앱 권한이 없다)."""
import copy
import json

import pytest

# client 는 루틴 API 시험의 픽스처다
from tests.test_routines_api import PREFIX, RUN_SPEC, _create, _login, client  # noqa: F401

from app.agent.teams import TeamStore
from app.main import app

OP = "he-cad-stepforge"
TEAM = {"name": "힌지 낙하 검토팀", "lead": {"key": "mech-a", "name": "기구 강도 전문가"},
        "helpers": [{"key": "cae-b", "name": "구조 해석 전문가"}, {"key": OP, "name": "StepForge 운영자"}], "apps": ["step_forge"],
        "tools": ["section_atlas"]}
# 팀 전의 실행 보기 꼴 — 위 칸 차례 · 단계 칸(팀 칸을 안 쓰는 루틴은 이 그대로여야 한다)
VIEW_KEYS = ["contract", "run", "note", "inputs", "purpose", "steps", "next_step", "write_class", "report"]
STEP_KEYS = {"id", "title", "kind", "backends", "label", "allowed", "dropped_write", "goal", "uses", "expect", "budget", "blocked",
             "deliberation", "readiness", "state", "calls", "reason", "summary", "keys", "findings", "flags"}


@pytest.fixture()
def tc(client):  # noqa: F811 — 루틴 API 시험의 픽스처를 받아 팀 저장소를 더한다
    c, s = client
    keep = app.state.team_store
    app.state.team_store = TeamStore(app.state.procedures_store)
    hb = _login(c, "boss@corp.com")
    assert c.patch("/auth/access/users/user@corp.com", json={"grants": ["feat:routines", "feat:expert-chat"]},
                   headers=hb).status_code == 200
    yield c, s
    app.state.team_store = keep


def _team(c, h, **over) -> dict:
    r = c.post("/agent/teams", json={**TEAM, **over}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def _spec(team=None, steps: dict | None = None) -> dict:
    """RUN_SPEC 에 루틴 팀 · 단계 팀을 얹는다. 심의 단계(delib)는 그대로 — 리스크 심사 계열 단계는 따로 더한다."""
    sp = copy.deepcopy(RUN_SPEC)
    if team is not None:
        sp["team"] = team
    for s in sp["steps"]:
        if steps and s["id"] in steps:
            s["team"] = steps[s["id"]]
    return sp


def _run(c, h, spec) -> dict:
    rid = _create(c, h, spec)["id"]
    r = c.post(f"{PREFIX}/runs", json={"routine_id": rid, "inputs": {"model": "S26"}}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def _by(view) -> dict:
    return {s["id"]: s for s in view["steps"]}


def test_팀_칸을_안_쓰는_루틴은_스펙_실행_보기_준비도가_팀_전과_같다(tc):
    c, _ = tc
    h = _login(c, "boss@corp.com")
    rid = _create(c, h, RUN_SPEC)["id"]
    spec = c.get(f"{PREFIX}/routines/{rid}").json()["version"]["spec"]
    assert "team" not in spec and all("team" not in s for s in spec["steps"]), "저장한 스펙에 team: null 을 남기지 않는다"
    assert "team" not in c.get(f"{PREFIX}/routines/{rid}/export").text
    assert "teams" not in c.get(f"{PREFIX}/routines/{rid}/readiness").json()
    v = c.post(f"{PREFIX}/runs", json={"routine_id": rid, "inputs": {"model": "S26"}}, headers=h).json()
    assert list(v) == VIEW_KEYS, list(v)
    assert all(set(s) == STEP_KEYS for s in v["steps"]), [sorted(set(s) ^ STEP_KEYS) for s in v["steps"]]
    assert '"team' not in json.dumps(v, ensure_ascii=False)
    again = c.get(f"{PREFIX}/runs/{v['run']['id']}").json()
    assert json.dumps(again, ensure_ascii=False) == json.dumps(v, ensure_ascii=False), "다시 읽어도 같은 바이트"


def test_실행을_만들_때_사본을_원장에_남기고_단계는_덮거나_팀_없이(tc):
    c, _ = tc
    h = _login(c, "boss@corp.com")
    base = _team(c, h)
    other = _team(c, h, name="VOC 팀", lead={"key": "voc-a", "name": "VOC 분석가"}, helpers=[], apps=[], tools=[])
    v = _run(c, h, _spec(base["id"], {"ra": "", "ft": other["id"]}))
    assert list(v)[:4] == ["contract", "run", "note", "team"] and "team_why" not in v
    snap = v["team"]
    assert snap["id"] == base["id"] and snap["version"] == 1 and snap["name"] == TEAM["name"]
    assert snap["lead"] == TEAM["lead"] and snap["helpers"] == TEAM["helpers"] and snap["apps"] == ["step_forge"]
    by = _by(v)
    assert "team" not in by["voc"], "덮지 않은 단계는 칸이 없다 — 실행기는 step.team → view.team 차례로 읽는다"
    assert by["ra"]["team"] is False and "team_why" not in by["ra"], "빈 글 = 이 단계는 팀 없이"
    assert by["ft"]["team"]["id"] == other["id"] and by["ft"]["team"]["helpers"] == []
    assert "team" not in by["delib"], "보통 심의 단계는 루틴 팀을 그대로 받는다(좌석으로 넘기는 것은 실행기)"


def test_실행_도중_팀을_고쳐도_그_실행의_사본은_그대로다_이어서도(tc):
    c, _ = tc
    h = _login(c, "boss@corp.com")
    t = _team(c, h)
    v = _run(c, h, _spec(t["id"]))
    run_id = v["run"]["id"]
    r = c.patch(f"/agent/teams/{t['id']}", json={"expected_version": 1, "name": "바뀐 팀", "helpers": []}, headers=h)
    assert r.status_code == 200 and r.json()["version"] == 2
    got = c.get(f"{PREFIX}/runs/{run_id}").json()
    assert got["team"] == v["team"] and got["team"]["version"] == 1 and len(got["team"]["helpers"]) == 2
    assert c.post(f"{PREFIX}/runs/{run_id}/resume", headers=h).json()["team"] == v["team"], "이어서도 같은 사본"
    assert c.delete(f"/agent/teams/{t['id']}", headers=h).status_code == 200
    assert c.get(f"{PREFIX}/runs/{run_id}").json()["team"] == v["team"], "팀을 지워도 그 실행은 같은 사람들로"
    fresh = c.post(f"{PREFIX}/runs", json={"routine_id": v["run"]["routine_id"], "inputs": {"model": "S26"}}, headers=h).json()
    assert fresh["team"] is None and "찾을 수 없다" in fresh["team_why"], "지운 뒤 새 실행은 팀 없이 + 까닭"


def test_못_푼_팀은_null_과_까닭이고_못_푼_단계_팀은_루틴_팀으로_대신하지_않는다(tc):
    c, _ = tc
    h = _login(c, "boss@corp.com")
    base = _team(c, h)
    gone = _team(c, h, name="지울 팀")
    assert c.delete(f"/agent/teams/{gone['id']}", headers=h).status_code == 200
    v = _run(c, h, _spec(base["id"], {"voc": gone["id"]}))
    by = _by(v)
    assert v["team"]["id"] == base["id"]
    assert by["voc"]["team"] is False and "찾을 수 없다" in by["voc"]["team_why"], by["voc"]
    v = _run(c, h, _spec(gone["id"]))
    assert v["team"] is None and "찾을 수 없다" in v["team_why"] and all("team" not in s for s in v["steps"])


def test_남의_팀은_그_사람의_시야로_풀고_못_쓰는_보조는_빠진다(tc):
    c, _ = tc
    hb = _login(c, "boss@corp.com")
    mine = _team(c, hb)
    h = _login(c, "user@corp.com")
    v = _run(c, h, _spec(mine["id"]))
    assert v["team"] is None and "찾을 수 없다" in v["team_why"], "boss 의 나만 팀은 user 에게 없다"
    own = _team(c, h)
    v = _run(c, h, _spec(own["id"]))
    assert [x["key"] for x in v["team"]["helpers"]] == ["cae-b"] and OP in v["team_why"], v.get("team_why")
    rid = _create(c, h, _spec(own["id"]))["id"]
    lines = c.get(f"{PREFIX}/routines/{rid}/readiness").json()["teams"]
    assert lines == [{"where": "routine", "team_id": own["id"], "name": TEAM["name"], "state": "partial", "why": v["team_why"],
                      "hidden": [{"key": OP, "name": "StepForge 운영자"}]}], lines


def test_리스크_심사_계열_심의_단계에는_팀을_앉히지_않는다(tc):
    c, _ = tc
    h = _login(c, "boss@corp.com")
    t = _team(c, h)
    sp = _spec(t["id"])
    sp["steps"].append({"id": "rv", "title": "리스크 심사", "kind": "deliberation", "goal": "심사", "deliberation": {"job": "risk-review"}})
    sp["steps"].append({"id": "rs", "title": "봉인 심사", "kind": "deliberation", "goal": "심사",
                        "deliberation": {"job": "mechanism", "chair_template": "risk-review-sealed"}})
    v = _run(c, h, sp)
    by = _by(v)
    for sid in ("rv", "rs"):
        assert by[sid]["team"] is False and "D-18" in by[sid]["team_why"], by[sid]
    assert "team" not in by["delib"]
    rid = _create(c, h, sp)["id"]
    lines = {x["where"]: x for x in c.get(f"{PREFIX}/routines/{rid}/readiness").json()["teams"]}
    assert lines["rv"]["state"] == lines["rs"]["state"] == "off" and lines["routine"]["state"] == "ok"
    bad = copy.deepcopy(sp)
    bad["steps"][-2]["team"] = t["id"]
    r = c.post(f"{PREFIX}/routines", json={"spec": bad}, headers=h)
    assert r.status_code == 422 and "D-18" in r.json()["detail"], r.text
    bad["steps"][-2]["team"] = ""
    assert c.post(f"{PREFIX}/routines", json={"spec": bad}, headers=h).status_code == 201, "빈 글(팀 없이)은 된다"


def test_팀을_붙인_루틴은_전문가와_대화_권한도_있어야_저장하고_팀_칸_꼴을_본다(tc):
    c, _ = tc
    hb = _login(c, "boss@corp.com")
    t = _team(c, hb)
    assert c.patch("/auth/access/users/user@corp.com", json={"grants": ["feat:routines"]}, headers=hb).status_code == 200
    h = _login(c, "user@corp.com")
    r = c.post(f"{PREFIX}/routines", json={"spec": _spec(t["id"])}, headers=h)
    assert r.status_code == 403 and "feat:expert-chat" in r.json()["detail"], r.text
    assert c.post(f"{PREFIX}/routines", json={"spec": _spec(None, {"voc": ""})}, headers=h).status_code == 403, "빈 글도 팀 칸이다"
    assert c.post(f"{PREFIX}/routines", json={"spec": RUN_SPEC}, headers=h).status_code == 201
    yaml_text = f"title: 가져온 루틴\nteam: {t['id']}\nsteps:\n- id: a\n  title: a\n  backends: [signalforge]\n  goal: g\n"
    assert c.post(f"{PREFIX}/import", json={"yaml": yaml_text}, headers=h).status_code == 403
    hb = _login(c, "boss@corp.com")
    for bad in ({"team": ""}, {"team": "tm_x"}, {"team": 3}):
        r = c.post(f"{PREFIX}/routines", json={"spec": {**RUN_SPEC, **bad}}, headers=hb)
        assert r.status_code == 422 and "team" in r.json()["detail"], (bad, r.text)
    r = c.post(f"{PREFIX}/routines", json={"spec": _spec(None, {"voc": "tm_x"})}, headers=hb)
    assert r.status_code == 422 and "팀 칸" in r.json()["detail"]
