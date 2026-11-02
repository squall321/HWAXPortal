# 심의 전 '온톨로지 먼저 보기' 창구 — 주제 과제 확인 · 읽기 확인 · exact 일 때만 이웃 · 어휘표 타입만 · 리스크 심사 거절(docs/ontology-first M4)
"""docs/ontology-first PLAN §5.2 · OF-8 · OF-14 ③.

  · 닻은 심의 주제(M1)의 과제 key 다 — 브라우저 값은 근거가 아니라, M1 과 같은 풀이(heaxstep_forge_find_plm_task)를 그 사람의 PAT 로 불러 key 가 글자
    그대로 같은 활성 행이 하나일 때만 확인이다(에이전트 서버 delib_subject.confirm 과 같은 판정 — 형제 리포 원문으로 견준다). 아니면 허브를 부르지 않는다.
  · 두 허브 도구(rootdesigndatahub_object_resolve · _graph_neighbors)가 게이트웨이 /tools-map 의 정본 백엔드 것이고 routine_read 에 있어야 부른다.
  · object_resolve 가 exact 이고 그 객체의 key 가 닻과 같을 때만 graph_neighbors(depth 1 · 어휘표 types 의 값에서 plm_task 를 뺀 타입 · limit 60)를 부른다.
    candidates · none · 다른 key 의 exact 는 그대로 보이고 아무것도 고르지 않는다.
  · 이웃은 닻과 바로 이어진 어휘표 타입만, 줄마다 '타입 · key · 이름 · 관계(방향)' 로 4,000자 안. 리스크 심사 계열 의장이면 422 이고 아무것도 부르지 않는다.
  · 가짜 허브 답은 StandardPlatform 의 실제 응답 꼴이다(ResolveOut · ResolveHit · NeighborhoodOut · NodeOut · EdgeOut — 형제 리포 원본의 칸과 견준다).
"""
import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import httpx
import pytest

from app.agent import onto_preview as O
from app.agent import routes as R
from app.agent import subject as S
from tests.test_subject_m1 import KEY, _real

_ROOT = Path(__file__).resolve().parents[2]
_AGENT = _ROOT.parent / "HWAXAgentServer"
_SP = _ROOT.parent / "StepForge" / "external" / "StandardPlatform" / "backend" / "app" / "modules"
RES, NB = "rootdesigndatahub_object_resolve", "rootdesigndatahub_graph_neighbors"
TASK_ID = "0195f3c2-6a1e-7c11-9a10-1b2c3d4e5f60"
OTHER_ID = "0195f3c2-6a1e-7c11-9a10-1b2c3d4e5f61"


def _hit(oid=TASK_ID, key=KEY, label=KEY, matched_by="key", type_slug="plm_task") -> dict:
    """SP ResolveHit(objects/schemas.py) — id · key · label · aliases · status · matched_by · hint · type_slug."""
    return {"id": oid, "key": key, "label": label, "aliases": ["알파"], "status": "active", "matched_by": matched_by, "hint": "",
            "type_slug": type_slug}


def _resolve(match="exact", obj=None, cands=()) -> dict:
    """SP ResolveOut — match · object · candidates · hint · truncated."""
    return {"match": match, "object": obj if match == "exact" else None, "candidates": list(cands), "hint": "", "truncated": False}


def _node(nid, label, key, type_slug, type_label) -> dict:
    """SP NodeOut(graph/schemas.py) — id · label · key · type_slug · type_label · status · owner_workspace_slug · degree · truncated."""
    return {"id": nid, "label": label, "key": key, "type_slug": type_slug, "type_label": type_label, "status": "active",
            "owner_workspace_slug": None, "degree": 3, "truncated": False}


def _edge(eid, relation, label, inverse, src, dst) -> dict:
    """SP EdgeOut — id · relation · label · inverse_label · directed · src · dst."""
    return {"id": eid, "relation": relation, "label": label, "inverse_label": inverse, "directed": True, "src": src, "dst": dst}


_N = {"fm": "0195f3c2-0000-7000-8000-000000000001", "model": "0195f3c2-0000-7000-8000-000000000002",
      "risk": "0195f3c2-0000-7000-8000-000000000003", "far": "0195f3c2-0000-7000-8000-000000000004",
      "prev": "0195f3c2-0000-7000-8000-000000000005"}


def _neighbors(*, truncated=False) -> dict:
    """SP NeighborhoodOut — focus · nodes · edges · depth · fanout · node_limit · truncated · log_counts. 시작점 노드가 늘 든다. 어휘표에 없는 타입
    (risk_finding)과 닻과 바로 잇지 않은 노드(far — 이웃의 이웃)는 행이 되지 않는다."""
    return {"focus": TASK_ID, "depth": 1, "fanout": 30, "node_limit": 60, "truncated": truncated,
            "log_counts": [{"type_slug": "test_log", "type_label": "시험 기록", "key": "task", "label": "과제", "inverse_label": "", "count": 12}],
            "nodes": [_node(TASK_ID, KEY, KEY, "plm_task", "PLM 과제"),
                      _node(_N["fm"], "힌지 크랙", "FM-0012", "failure_mode", "고장모드"),
                      _node(_N["model"], "모델 A100", "SM-A100", "plm_model", "개발모델"),
                      _node(_N["risk"], "앞 판정", "R-1", "risk_finding", "리스크 판정"),
                      _node(_N["far"], "먼 기준", "CR-9", "criterion", "관리 기준"),
                      _node(_N["prev"], "알파 개발_C1", "알파 개발_C1", "plm_task", "PLM 과제")],
            "edges": [_edge("e1", "predicts", "예측함", "예측됨", TASK_ID, _N["fm"]),
                      _edge("e2", "has_task", "과제를 가짐", "과제의 모델", _N["model"], TASK_ID),
                      _edge("e3", "judges", "판정함", "판정됨", _N["risk"], TASK_ID),
                      _edge("e4", "guards_against", "막음", "막힘", _N["far"], _N["fm"]),
                      _edge("e5", "succeeds", "뒤를 잇는다", "앞선다", TASK_ID, _N["prev"])]}


def _tools_map(read=(RES, NB), *, routine=True) -> dict:
    m = {RES: "rootdesigndatahub", NB: "rootdesigndatahub", "find_plm_task": "heax-step_forge", "list_parts": "heax-step_forge"}
    return {"map": m, **({"routine_read": sorted(set(read) | {"find_plm_task"})} if routine else {})}


@pytest.fixture()
def onto(monkeypatch, tmp_path):
    """창구를 그 사람 PAT · 가짜 게이트웨이 · 가짜 도구 지도로 부른다. 어휘표는 이 리포의 정본(박스 덧씌우기 없이)."""
    from fastapi.testclient import TestClient

    from app.access import routes as access_routes
    from app.auth.provider import Principal
    from app.deps import principal_pat_or_session
    from app.main import app

    monkeypatch.setattr(O, "VOCAB_LOCAL_PATH", tmp_path / "core_vocab.local.json")
    monkeypatch.setattr(O, "_V", {"key": None, "v": None})
    state = {"groups": ["feat:chat", "feat:deliberation"], "find": _real(), "resolve": _resolve("exact", _hit()),
             "neighbors": _neighbors(), "tools_map": _tools_map(), "raise": {}}
    seen: list = []
    app.dependency_overrides[principal_pat_or_session] = lambda: Principal(
        subject="u1", email="u1@hwax.local", display_name="U", groups=state["groups"])

    async def mcp(url, pat, tool, args, timeout=90.0):
        seen.append({"pat": pat, "tool": tool, "args": args, "timeout": timeout})
        if tool in state["raise"]:
            raise state["raise"][tool]
        return {S.RESOLVER_CALL: state["find"], RES: state["resolve"], NB: state["neighbors"]}[tool]

    async def tmap(_settings):
        return state["tools_map"]
    monkeypatch.setattr(R._upload, "mcp_call", mcp)
    monkeypatch.setattr(R, "_chat_user_pat", lambda *a, **k: "chat-pat")
    monkeypatch.setattr(access_routes, "_gateway_tools_map", tmap)

    def go(body: dict):
        with TestClient(app) as c:
            return c.post("/agent/deliberate/onto-preview", json=body)

    try:
        yield go, seen, state
    finally:
        app.dependency_overrides.pop(principal_pat_or_session, None)


def _tools(seen) -> list:
    return [c["tool"] for c in seen]


# ── 바른 길 ───────────────────────────────────────────────────────────────────────────────
def test_확인된_주제_과제가_exact_면_한_걸음_이웃을_어휘표_타입으로_줄여_준다(onto):
    go, seen, _state = onto
    r = go({"sp_task": f" {KEY} ", "chair_template": "diagnosis"})
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["state"] == "ok", b
    assert _tools(seen) == [S.RESOLVER_CALL, RES, NB], "확인 → 풀이 → 이웃 차례"
    assert all(c["pat"] == "chat-pat" and c["timeout"] == O.CALL_TIMEOUT_S for c in seen), "그 사람의 PAT · 호출마다 30초"
    assert seen[0]["args"] == {"query": KEY, "limit": S.CONFIRM_LIMIT, "full": True}, "M1 과 같은 풀이 · 같은 행 수"
    assert seen[1]["args"] == {"type_slug": "plm_task", "name": KEY}
    vocab = json.loads(O.VOCAB_PATH.read_text(encoding="utf-8"))
    want_types = [t for t in dict.fromkeys(vocab["types"].values()) if t != "plm_task"]
    assert seen[2]["args"] == {"object_id": TASK_ID, "depth": 1, "types": want_types, "limit": 60}, seen[2]["args"]
    rows = {x["key"]: x for x in b["rows"]}
    assert set(rows) == {"FM-0012", "SM-A100", "알파 개발_C1"}, "어휘표 타입 · 닻과 바로 이은 것만(판정 · 이웃의 이웃은 아니다)"
    assert rows["FM-0012"]["line"] == "고장모드(failure_mode) · FM-0012 · 힌지 크랙 · 이 과제 → 예측함(predicts)"
    assert rows["SM-A100"]["rel"] == "이 과제 ← 과제의 모델(has_task)", "들어오는 관계는 거꿀말로"
    assert b["total"] == b["shown"] == 3 and b["hub_truncated"] is False
    assert b["anchor"]["key"] == KEY and b["anchor"]["id"] == TASK_ID and "exact(key)" in b["anchor"]["line"]
    assert b["calls"] == {"resolve": {"tool": RES, "args": seen[1]["args"]}, "neighbors": {"tool": NB, "args": seen[2]["args"]}}
    assert "결정문 · Report Archive 보고서의 근거에 남는다" in b["note"] and "도구 원문이 아니다" in b["note"]


def test_줄인_글은_chars_안에서_끊고_전체와_보인_수를_말한다(onto, monkeypatch):
    go, _seen, state = onto
    nb = _neighbors(truncated=True)
    for i in range(80):
        nid = f"0195f3c2-1111-7000-8000-{i:012d}"
        nb["nodes"].append(_node(nid, "아주 긴 이름 " * 8, f"FM-{i:04d}", "failure_mode", "고장모드"))
        nb["edges"].append(_edge(f"x{i}", "predicts", "예측함", "예측됨", TASK_ID, nid))
    state["neighbors"] = nb
    b = go({"sp_task": KEY}).json()
    assert b["state"] == "ok" and b["total"] == 83 and 0 < b["shown"] < 83 and b["hub_truncated"] is True
    assert sum(len(x["line"]) + 1 for x in b["rows"]) <= 4000


# ── 고르지 않는 길 ───────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("match", ("candidates", "none"))
def test_후보_여럿이나_없음이면_이웃을_부르지_않고_고르지_않는다(onto, match):
    go, seen, state = onto
    state["resolve"] = _resolve(match, cands=[_hit(), _hit(OTHER_ID, f"{KEY} 보강", f"{KEY} 보강", "contains")] if match == "candidates" else ())
    b = go({"sp_task": KEY}).json()
    assert b["state"] == match and _tools(seen) == [S.RESOLVER_CALL, RES], b
    assert "rows" not in b and "anchor" not in b
    if match == "candidates":
        assert [c["key"] for c in b["candidates"]] == [KEY, f"{KEY} 보강"] and "고르지 않는다" in b["why"]


def test_exact_가_다른_key_를_가리키면_고르지_않는다(onto):
    """별칭 · 이름으로 맞은 다른 객체 — 정본 허브의 exact 가 주제 과제와 같은 객체라고 볼 수 없다(틀린 대상)."""
    go, seen, state = onto
    state["resolve"] = _resolve("exact", _hit(OTHER_ID, "알파 개발_C2 옛판", "알파 개발_C2 옛판", "alias"))
    b = go({"sp_task": KEY}).json()
    assert b["state"] == "mismatch" and _tools(seen) == [S.RESOLVER_CALL, RES] and "alias" in b["why"], b


@pytest.mark.parametrize("find", (
    {"query": KEY, "count": 0, "tasks": [], "why": {"cause": "no_match"}},
    {"query": KEY, "count": 1, "tasks": [{"key": f"{KEY} 보강", "label": "x", "active": True}]},
    {"query": KEY, "count": 1, "tasks": [{"key": KEY, "label": KEY, "active": False, "gone_reason": "merged"}]},
    {"query": KEY, "count": 2, "tasks": [{"key": KEY, "active": True}, {"key": KEY, "active": True}]},
), ids=("없음", "부분일치만", "비활성", "둘"))
def test_주제_과제를_확인하지_못하면_허브를_부르지_않는다(onto, find):
    go, seen, state = onto
    state["find"] = find
    b = go({"sp_task": KEY}).json()
    assert b["state"] == "unconfirmed" and _tools(seen) == [S.RESOLVER_CALL] and b["why"].startswith("주제 과제를 확인하지 못했다"), b


@pytest.mark.parametrize("tm,why", (
    (None, "도구 지도"),
    (_tools_map(read=(NB,)), RES),
    (_tools_map(routine=False), "routine_read"),
    ({"map": {"find_plm_task": "heax-step_forge"}, "routine_read": []}, "정본 허브(rootdesigndatahub) 도구가 없다"),
), ids=("지도불통", "풀이_읽기미확인", "옛게이트웨이", "dev_허브없음"))
def test_읽기로_확인되지_않으면_아무것도_부르지_않고_까닭을_말한다(onto, tm, why):
    go, seen, state = onto
    state["tools_map"] = tm
    b = go({"sp_task": KEY}).json()
    assert b["state"] == "unavailable" and seen == [] and why in b["why"], b
    if tm and tm.get("routine_read") is not None and RES not in tm["routine_read"] and RES in tm["map"]:
        assert "read_tools.local.json" in b["why"] and "rootdesigndatahub:object_resolve" in b["why"], "박스에서 여는 길을 말한다(M-R)"


@pytest.mark.parametrize("where", (RES, NB, S.RESOLVER_CALL))
@pytest.mark.parametrize("exc", (httpx.ConnectError("게이트웨이가 없다"), R.AuthError("x: forbidden — 플랫폼 허가가 없다", status_code=502)),
                         ids=("불통", "거절"))
def test_호출이_실패하면_그_단계의_까닭을_말하고_다음을_부르지_않는다(onto, where, exc):
    go, seen, state = onto
    state["raise"] = {where: exc}
    b = go({"sp_task": KEY}).json()
    want = {S.RESOLVER_CALL: "unconfirmed", RES: "error", NB: "error"}[where]
    assert b["state"] == want and _tools(seen)[-1] == where, b
    assert ("ConnectError" in b["why"]) if isinstance(exc, httpx.ConnectError) else ("forbidden" in b["why"]), b["why"]
    if where == NB:
        assert b["anchor"]["key"] == KEY and b["rows"] == [], "닻은 보이되 이웃은 못 물어봤다고 말한다"


# ── 막는 길 ─────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("chair", ("risk-review", "risk-review-sealed", " Risk-Review "))
def test_리스크_심사_계열에는_쓰지_않는다(onto, chair):
    go, seen, _state = onto
    r = go({"sp_task": KEY, "chair_template": chair})
    assert r.status_code == 422 and "D-18" in r.json()["detail"] and seen == [], r.text


def test_심의_권한이_없거나_꼴이_틀리면_부르지_않는다(onto):
    go, seen, state = onto
    state["groups"] = ["feat:chat"]
    assert go({"sp_task": KEY}).status_code == 403
    state["groups"] = ["feat:deliberation"]
    assert go({"sp_task": "   "}).status_code == 422
    assert go({"sp_task": KEY, "sp_state": "confirmed"}).status_code == 422, "확인 상태를 실어 오지 못한다"
    assert go({"sp_task": "가" * 201}).status_code == 422
    assert seen == []


def test_박스_덧씌우기의_facts_가_틀리면_기본값으로_돌고_말한다(onto, tmp_path):
    go, seen, _state = onto
    (tmp_path / "core_vocab.local.json").write_text(json.dumps({"ontology": {"facts": {"depth": 3, "limit": 9999}}}), encoding="utf-8")
    b = go({"sp_task": KEY}).json()
    assert b["state"] == "ok" and seen[2]["args"]["limit"] == 60 and seen[2]["args"]["depth"] == 1
    assert any("facts" in n for n in b["notes"]), b.get("notes")
    (tmp_path / "core_vocab.local.json").write_text(json.dumps({"ontology": {"facts": {"limit": 20, "chars": 1500}}}), encoding="utf-8")
    seen.clear()
    b = go({"sp_task": KEY}).json()
    assert seen[2]["args"]["limit"] == 20 and "notes" not in b, "맞는 덧씌우기는 받아들인다"


# ── 계약 — 에이전트 서버의 확인 판정 · SP 응답 꼴 ─────────────────────────────────────────────────────────
_CONFIRM = (
    "import asyncio, json, sys\n"
    "import delib_subject as ds\n"
    "cases = json.load(sys.stdin)\n"
    "out = []\n"
    "for body in cases:\n"
    "    async def fake(*_a, _b=body, **_k):\n"
    "        return False, json.dumps(_b, ensure_ascii=False)\n"
    "    ds.call_resolver = fake\n"
    "    rec = asyncio.run(ds.confirm(None, ds.parse({'sp_task': body['_key']}), groups=[], user='u'))\n"
    "    out.append(rec['sp_state'])\n"
    "print(json.dumps(out))\n"
)


def test_닻_확인_판정이_에이전트_서버의_주제_확인과_같다():
    """심의를 열 때 에이전트 서버가 같은 풀이로 주제를 다시 확인한다 — 미리보기가 확인한 과제가 심의에서 '주장' 으로 떨어지면 고른 근거와 주제가 갈린다."""
    if not (_AGENT / "delib_subject.py").exists():
        pytest.skip(f"형제 리포 없음: {_AGENT}")
    cases = [{**_real(), "_key": KEY}, {"tasks": [], "_key": KEY}, {"tasks": [{"key": KEY, "active": False}], "_key": KEY},
             {"tasks": [{"key": KEY}, {"key": KEY}], "_key": KEY}, {"tasks": [{"key": KEY.lower(), "active": True}], "_key": KEY},
             {"tasks": [{"key": KEY, "active": True}, {"key": "다른 과제", "active": True}], "_key": KEY}, {"result": [], "_key": KEY}]
    r = subprocess.run([sys.executable, "-c", _CONFIRM], input=json.dumps(cases, ensure_ascii=False), cwd=_AGENT,
                       env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, f"에이전트 서버 delib_subject.confirm 을 부르지 못했다 — {r.stderr.strip()[-600:]}"
    agent = json.loads(r.stdout)
    portal = ["confirmed" if S.confirm_rows({k: v for k, v in c.items() if k != "_key"}, c["_key"])[0] else "claimed" for c in cases]
    assert portal == agent, (portal, agent)
    assert agent[0] == "confirmed" and agent.count("confirmed") == 2


def _fields(path: Path, cls: str) -> set:
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.ClassDef) and node.name == cls:
            return {s.target.id for s in node.body if isinstance(s, ast.AnnAssign) and isinstance(s.target, ast.Name)}
    raise AssertionError(f"{path.name} 에서 {cls} 를 못 찾았다 — 응답 꼴이 바뀌었으면 가짜도 고친다")


def test_가짜_허브_답은_StandardPlatform_의_실제_응답_꼴이다():
    """가짜가 진짜 꼴과 다르면 판정 결함을 숨긴다(시험 가짜 · 진짜 꼴). 형제 리포(StepForge 의 SP 사본)의 스키마 칸과 견준다(README 의 SP 778db2f)."""
    objs, graph = _SP / "objects" / "schemas.py", _SP / "graph" / "schemas.py"
    if not objs.exists() or not graph.exists():
        pytest.skip(f"형제 리포의 StandardPlatform 사본이 없다: {_SP}")
    assert set(_resolve("exact", _hit())) == _fields(objs, "ResolveOut")
    assert set(_hit()) == _fields(objs, "ResolveHit")
    nb = _neighbors()
    assert set(nb) == _fields(graph, "NeighborhoodOut")
    assert set(nb["nodes"][0]) == _fields(graph, "NodeOut") and set(nb["edges"][0]) == _fields(graph, "EdgeOut")
    assert set(nb["log_counts"][0]) == _fields(objs, "LogCountOut")
