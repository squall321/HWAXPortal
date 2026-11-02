# 심의 주제의 포털 몫 — DelibOpts.subject 의 꼴 · 중계가 에이전트의 확인 사건만 답 meta 에 남기기 · 허브 과제 찾기 창구(과제 인사이트 그래프 M1)
"""docs/project-insight-graph PLAN §4.1 · §4.3 · §9 M1.

  · 받는 칸은 넷(sp_task · round · text · artifacts)뿐이다 — 확인 상태 · 지문 · 차수 출처를 실어 오면 422 다(브라우저가 확인을 지어내지 못한다).
    상한은 에이전트 서버 delib_subject 와 같다(형제 리포의 원본을 읽어 견준다).
  · 중계는 delib_opts.subject 를 그대로 넘기고, 에이전트가 확인해 낸 delib 사건(kind=subject)만 답 meta.subject 로 남긴다 — 브라우저가 보낸 값은
    서버 사본 어디에도 남지 않는다. 주제가 없는 심의의 답 meta 에는 그 칸이 없다.
  · 허브 과제 찾기(POST /agent/deliberate/subject/search) — 그 사람의 PAT 로 에이전트와 같은 풀이 도구를 부르고 결과 행의 key 를 그대로 돌려준다.
    풀이의 가짜는 실제 StepForge 응답 꼴이다(형제 리포의 시험 자료를 읽는다 — 없으면 같은 꼴을 여기 둔다).
"""
import json
import re
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from app.agent import routes as R
from app.agent import subject as S
from app.agent.routes import ChatRequest, DelibOpts

_ROOT = Path(__file__).resolve().parents[2]
_AGENT = _ROOT.parent / "HWAXAgentServer"
KEY = "알파 개발_C2"

# 실제 StepForge find_plm_task 응답(StepForge 4253453 의 find_tasks 를 가짜 허브 거울에 대고 돌려 받아 적은 것 — 형제 리포
# tests/fixtures/subject/find_plm_task.json 과 같은 꼴). 형제 리포가 있으면 그 원본을 쓴다.
_REAL = {"query": KEY, "count": 2, "truncated": False, "omitted": 0, "tasks": [
    {"key": KEY, "label": KEY, "active": True, "task_status": "진행", "hub_status": "active",
     "project": {"key": "PJ-ALPHA", "label": "알파 프로젝트", "active": True},
     "models": [{"key": "SM-A100", "label": "모델 A100", "model_revision": "C2"}], "models_count": 1,
     "properties": {"aliases": ["알파"], "project": "PJ-ALPHA", "task_code": "TC-1001", "task_status": "진행"},
     "hub_updated_at": "2026-10-01T00:00:02.000000Z", "received_at": 1793590275.18, "matched_by": ["key", "label"]},
    {"key": f"{KEY} 보강", "label": f"{KEY} 보강", "active": True, "task_status": "진행", "hub_status": "active",
     "project": {"key": "PJ-ALPHA", "label": "알파 프로젝트", "active": True}, "models": [], "models_count": 0,
     "properties": {"project": "PJ-ALPHA", "task_code": "TC-1002", "task_status": "진행"},
     "hub_updated_at": "2026-10-01T00:00:03.000000Z", "received_at": 1793590275.18, "matched_by": ["key", "label"]}],
    "sync": {"configured": True}}


def _real() -> dict:
    p = _AGENT / "tests" / "fixtures" / "subject" / "find_plm_task.json"
    return json.loads(p.read_text(encoding="utf-8"))["exact_and_partial"]["body"] if p.exists() else _REAL


# ── 꼴 ─────────────────────────────────────────────────────────────────────────────────────
def test_받는_칸은_넷이고_그대로_중계된다():
    raw = {"sp_task": KEY, "round": "DV1", "text": "알파 1차", "artifacts": [{"kind": "mcad", "id": "019a2b3c4d5e6f7a8b9c0d1", "rev": "1a2b"}]}
    wire = ChatRequest(message="/심의 화두", delib_opts={"subject": raw}).delib_opts.model_dump(exclude_none=True)
    assert wire["subject"] == raw, "중계가 주제를 그대로 넘긴다(확인은 에이전트 서버가 한다)"
    assert "subject" not in ChatRequest(message="/심의 화두", delib_opts={}).delib_opts.model_dump(exclude_none=True)


@pytest.mark.parametrize("bad", [
    {"sp_task": KEY, "sp_state": "confirmed"}, {"sp_task": KEY, "sp_resolved_by": {"tool": "x"}}, {"round": "dv1", "round_by": "person"},
    {"sp_task": "가" * 201}, {"round": "d" * 41}, {"text": "가" * 501},
    {"artifacts": [{"kind": "pcb", "id": "x"}]}, {"artifacts": [{"kind": "mcad", "id": "x", "owner": "u"}]},
    {"artifacts": [{"kind": "mcad", "id": "0" * 23}] * 9}, {"artifacts": [{"kind": "mcad", "id": ""}]},
])
def test_서버가_적는_칸을_실어_오거나_상한을_넘으면_422_다(bad):
    with pytest.raises(ValidationError):
        DelibOpts(subject=bad)


def _agent_const(name: str) -> str | None:
    p = _AGENT / "delib_subject.py"
    if not p.exists():
        return None
    m = re.search(rf"^{name}\s*=\s*(.+)$", p.read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else None


def test_상한과_풀이_도구가_에이전트_서버와_같다():
    src = (_AGENT / "delib_subject.py")
    if not src.exists():
        pytest.skip(f"형제 리포 없음: {src}")
    text = src.read_text(encoding="utf-8")
    caps = re.search(r"^SP_TASK_MAX, ROUND_MAX, TEXT_MAX, REV_MAX, ARTIFACTS_MAX, WHY_MAX = (.+)$", text, re.M)
    assert caps, "에이전트 서버 delib_subject 의 상한 줄을 못 찾았다 — 모양이 바뀌었으면 이 시험도 고쳐라"
    sp, rnd, txt, rev, arts, _why = (int(x) for x in caps.group(1).split(","))
    f = DelibOpts.model_fields["subject"].annotation.__args__[0].model_fields
    ln = {k: next(m.max_length for m in f[k].metadata if hasattr(m, "max_length")) for k in ("sp_task", "round", "text", "artifacts")}
    assert ln == {"sp_task": sp, "round": rnd, "text": txt, "artifacts": arts}, ln
    a = R.DelibSubjectArtifact.model_fields
    assert next(m.max_length for m in a["rev"].metadata if hasattr(m, "max_length")) == rev
    app_, tool = re.search(r'^RESOLVER_APP, RESOLVER_TOOL = "([^"]+)", "([^"]+)"$', text, re.M).groups()
    assert S.RESOLVER_CALL == f"{app_.replace('-', '')}_{tool}", "고르기 화면의 후보와 서버의 확인은 같은 풀이에서 온다"


# ── 중계 ─────────────────────────────────────────────────────────────────────────────────────
def _sse(frames) -> bytes:
    return "".join(f"event: {ev}\ndata: {json.dumps(d, ensure_ascii=False)}\n\n" for ev, d in frames).encode()


class _Body(httpx.AsyncByteStream):
    def __init__(self, raw: bytes, step: int = 29) -> None:
        self.raw, self.step = raw, step

    async def __aiter__(self):
        for i in range(0, len(self.raw), self.step):
            yield self.raw[i:i + self.step]


@pytest.fixture()
def relay():
    """프레임을 에이전트 서버 자리에서 흘리고 (에이전트로 간 요청 본문, 저장된 서버 대화의 메시지)를 돌려준다."""
    from fastapi.testclient import TestClient

    from app.auth.provider import Principal
    from app.deps import principal_pat_or_session
    from app.main import app

    app.dependency_overrides[principal_pat_or_session] = lambda: Principal(
        subject="u1", email="u1@hwax.local", display_name="U", groups=["feat:chat", "feat:deliberation"])

    def go(body: dict, frames) -> tuple[dict, list[dict]]:
        sent = {}
        with TestClient(app) as c:
            real = app.state.agent_client
            raw = _sse(frames)

            def handler(req: httpx.Request) -> httpx.Response:
                sent.update(json.loads(req.content))
                return httpx.Response(200, stream=_Body(raw), headers={"content-type": "text/event-stream"})
            app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            try:
                cid = c.post("/agent/conversations", json={"title": "t", "kind": "deliberation"}).json()["id"]
                r = c.post("/agent/chat", json={**body, "conversation_id": cid})
                assert r.status_code == 200, r.text
                return sent, c.get(f"/agent/conversations/{cid}").json()["messages"]
            finally:
                app.state.agent_client = real

    try:
        yield go
    finally:
        app.dependency_overrides.pop(principal_pat_or_session, None)


CONFIRMED = {"sp_task": KEY, "sp_state": "confirmed", "sp_resolved_by": {"tool": S.RESOLVER_CALL, "app": "heax-step_forge", "at": 1.5,
                                                                          "sha256": "ab" * 32},
             "round": "dv1", "round_by": "person", "text": "알파 1차", "artifacts": [{"kind": "ecad", "id": "abcdef0123456789", "rev": "B"}]}


def test_중계는_에이전트가_확인한_주제만_답_meta_에_남기고_브라우저_값은_남기지_않는다(relay):
    asked = {"sp_task": KEY, "round": "dv1", "text": "알파 1차"}
    sent, msgs = relay({"message": "/심의 화두", "delib_opts": {"subject": asked}}, [
        ("delib", {"kind": "subject", "subject": CONFIRMED, "run_id": "r1"}),
        ("delib", {"kind": "decision", "text": "결정문"}),
        ("done", {})])
    assert sent["delib_opts"]["subject"] == asked, "에이전트 서버에 그대로 넘긴다"
    user, answer = msgs[0], [m for m in msgs if m["role"] == "assistant"][0]
    assert "subject" not in (user["meta"] or {}) and "subject" not in json.dumps(user["meta"] or {}, ensure_ascii=False), \
        "사람 발화의 meta 에 브라우저가 보낸 주제를 남기지 않는다"
    assert answer["meta"]["subject"] == CONFIRMED and answer["meta"]["delib_run"] == "r1"


def test_에이전트가_주제_사건을_내지_않으면_답에_주제가_없다(relay):
    """옛 에이전트 서버(주제를 모른다) · 리스크 심사 · 꼴이 틀린 주제 — 사건이 없으면 남길 것도 없다(브라우저 값으로 메우지 않는다)."""
    _sent, msgs = relay({"message": "/심의 화두", "delib_opts": {"subject": {"sp_task": KEY}}}, [
        ("delib", {"kind": "decision", "text": "결정문"}), ("done", {})])
    assert "subject" not in ([m for m in msgs if m["role"] == "assistant"][0]["meta"] or {})


@pytest.mark.parametrize("bad", [{"sp_task": KEY, "sp_state": "verified"}, "알파", None, {"sp_task": KEY}])
def test_꼴이_아닌_주제_사건은_남기지_않는다(relay, bad):
    _sent, msgs = relay({"message": "/심의 화두"}, [
        ("delib", {"kind": "subject", "subject": bad}), ("delib", {"kind": "decision", "text": "결정문"}), ("done", {})])
    assert "subject" not in ([m for m in msgs if m["role"] == "assistant"][0]["meta"] or {})


def test_남길_때는_알려진_칸만_상한_안에서():
    got = S.subject_of({**CONFIRMED, "extra": "x", "text": "가" * 900, "artifacts": [{"kind": "cae", "id": "0" * 26, "junk": 1}, {"kind": "zz"}]})
    assert "extra" not in got and len(got["text"]) == 600 and got["artifacts"] == [{"kind": "cae", "id": "0" * 26}]
    assert S.subject_of({"sp_state": "none", "sp_task": None, "round": None, "text": ""})["sp_task"] is None


# ── 허브 과제 찾기 ───────────────────────────────────────────────────────────────────────────
@pytest.fixture()
def search(monkeypatch):
    from fastapi.testclient import TestClient

    from app.auth.provider import Principal
    from app.deps import principal_pat_or_session
    from app.main import app

    seen = []
    state = {"groups": ["feat:chat", "feat:deliberation"], "reply": _real(), "raise": None}
    app.dependency_overrides[principal_pat_or_session] = lambda: Principal(
        subject="u1", email="u1@hwax.local", display_name="U", groups=state["groups"])

    async def mcp(url, pat, tool, args, timeout=90.0):
        seen.append({"pat": pat, "tool": tool, "args": args})
        if state["raise"]:
            raise state["raise"]
        return state["reply"]
    monkeypatch.setattr(R._upload, "mcp_call", mcp)
    monkeypatch.setattr(R, "_chat_user_pat", lambda *a, **k: "chat-pat")

    def go(query: str):
        with TestClient(app) as c:
            return c.post("/agent/deliberate/subject/search", json={"query": query})

    try:
        yield go, seen, state
    finally:
        app.dependency_overrides.pop(principal_pat_or_session, None)


def test_허브_과제_찾기는_그_사람의_PAT_로_같은_풀이를_부르고_결과_행의_key_를_그대로_준다(search):
    go, seen, _state = search
    r = go(f" {KEY} ")
    assert r.status_code == 200, r.text
    body = r.json()
    assert seen == [{"pat": "chat-pat", "tool": "heaxstep_forge_find_plm_task", "args": {"query": KEY, "limit": S.SEARCH_LIMIT, "full": True}}]
    assert [x["key"] for x in body["rows"]] == [KEY, f"{KEY} 보강"] and body["rows"][0]["task_code"] == "TC-1001"
    assert body["rows"][0]["project"] == "알파 프로젝트" and body["tool"] == S.RESOLVER_CALL and body["count"] == 2


def test_허브_과제_찾기의_0건은_까닭을_옮긴다(search):
    go, _seen, state = search
    state["reply"] = {"query": "없는 과제", "count": 0, "tasks": [], "why": {"cause": "no_match", "message": "맞는 것이 없다"}, "sync": {}}
    body = go("없는 과제").json()
    assert body["rows"] == [] and body["why"]["cause"] == "no_match"


def test_허브_과제_찾기는_심의_권한이_있어야_하고_도구_실패는_말한다(search):
    go, seen, state = search
    state["raise"] = R.AuthError("heaxstep_forge_find_plm_task: forbidden — 이 플랫폼 허가가 없다", status_code=502)
    r = go(KEY)
    assert r.status_code == 502 and "forbidden" in r.json()["detail"]
    state["groups"] = ["feat:chat"]
    n = len(seen)
    assert go(KEY).status_code == 403 and len(seen) == n, "심의 권한이 없으면 게이트웨이를 부르지 않는다"
    state["groups"] = ["feat:deliberation"]
    assert go("  ").status_code == 422 and len(seen) == n
