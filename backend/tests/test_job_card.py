# 진행 카드(WD-13) — 챗 중계가 SSE job_card 를 넘기고 서버 사본에 아는 칸만 남기며, 화면의 다시 묻기는 그 사람의 PAT 로 deliberate_status 를 부른다
"""docs/request-1125 WD-13 의 포털 몫(app/agent/mcp_delib.py card_pointer · gateway_read · GET /agent/engine-delib/status/{job_id}, 중계 routes.py).

에이전트 서버(3c6a54d)는 확인 카드로 승인한 호출이 '도는 중' 잡 하나를 걸면 SSE job_card {call, tool, app, kind, job_ids, phase, state, progress, detail, link,
status_call} 를 낸다. 고정하는 것.
  · 꼴 — 엔진 _confirm_job_card 가 내는 칸은 card_pointer 가 읽는 칸이다. 다시 묻기는 심의 잡의 deliberate_status 만(다른 도구를 화면이 부르게 하지
    않는다), 링크는 http(s) · 포털 안 경로만, 잡 id 가 없으면 남기지 않는다.
  · 중계 — 바이트는 그대로 흘리고 서버 사본의 답 meta.job_cards 에 걸러 남긴다(새로고침 · 다른 기기에서도 카드).
  · 다시 묻기 — 그 사람의 PAT 로 게이트웨이 deliberate_status(brief) · 쪽으로 나뉜 답은 엔진의 진짜 쪽 나누기(mcp_pages.paged)로 만들어 잇는다 · 끝난 잡이면
    그 사람의 대화에 들었는지(conversation_id) · 심의 권한이 있어야 한다.
"""
import ast
import importlib.util
import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from app.agent import mcp_delib as M
from app.agent import upload as U
from app.agent.audit import AuditLog
from app.agent.conv_store import ConversationStore
from app.auth.cookies import CSRF_COOKIE
from app.auth.token_store import TokenStore
from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.main import app
from tests.test_mcp_apps_panel import _Turn, _sse, kit  # noqa: F401  (kit 은 픽스처)
from tests.test_mcp_apps_panel import _login as _kit_login
from tests.test_mcp_delib import OUT, OWNER, PW, _engine_conv, _job

_AGENT = Path(__file__).resolve().parents[3] / "HWAXAgentServer"
JOB = "diagnosis-20261128-040000-abc123"
CARD = {"call": "c-1", "tool": "deliberate_start", "app": "hwax-deliberation", "kind": "deliberation", "job_ids": [JOB], "phase": "run",
        "state": "queued", "progress": None, "detail": "", "link": "/w/a/reports/7",
        "status_call": {"tool": "deliberate_status", "args": {"job_id": JOB}}}


def test_엔진이_내는_칸은_card_pointer_가_읽는_칸이다():
    p = _AGENT / "app.py"
    if not p.exists():
        pytest.skip(f"형제 리포 없음: {p}")
    tree = ast.parse(p.read_text(encoding="utf-8"))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_confirm_job_card")
    keys = {k.value for d in ast.walk(fn) if isinstance(d, ast.Dict) for k in d.keys if isinstance(k, ast.Constant) and isinstance(k.value, str)}
    keys |= {s.slice.value for s in ast.walk(fn) if isinstance(s, ast.Subscript) and isinstance(s.value, ast.Name) and s.value.id == "card"
             and isinstance(s.slice, ast.Constant)}
    read = {"call", "tool", "app", "kind", "job_ids", "phase", "state", "progress", "detail", "link", "status_call"}
    assert read <= keys | {"args", "job_id"} and {"call", "tool", "kind", "job_ids", "phase", "state", "link", "status_call"} <= keys, keys
    assert M.card_pointer(CARD) == {k: v for k, v in CARD.items() if k != "progress"} | {"progress": None}


@pytest.mark.parametrize(("patch", "want"), [
    ({"status_call": {"tool": "risk_job_action", "args": {"job_id": JOB}}}, {"status_call": None}),
    ({"status_call": {"tool": "deliberate_status", "args": {"job_id": "other-20261128-000000-000000"}}}, {"status_call": None}),
    ({"kind": "job"}, {"kind": "job", "status_call": None}),
    ({"link": "javascript:alert(1)"}, {"link": None}), ({"link": "//evil.example/x"}, {"link": None}),
    ({"link": "https://ra.example/w/a/reports/7"}, {"link": "https://ra.example/w/a/reports/7"}),
    ({"progress": 140}, {"progress": None}), ({"progress": 40}, {"progress": 40}), ({"phase": "weird"}, {"phase": "run"}),
])
def test_card_pointer_는_아는_칸만_걸러_남긴다(patch, want):
    got = M.card_pointer({**CARD, **patch})
    for k, v in want.items():
        assert got.get(k) == v, (k, got)


def test_잡_id_가_없으면_남기지_않는다():
    assert M.card_pointer({**CARD, "job_ids": []}) is None
    assert M.card_pointer({**CARD, "job_ids": ["../x"]}) is None
    assert M.card_pointer("x") is None


def test_중계는_사건을_넘기고_서버_사본의_답에_진행_카드를_남긴다(kit):
    c, _gw, _s = kit()
    h = _kit_login(c, "boss@corp.com")
    evil = {**CARD, "job_ids": ["x" * 3], "status_call": {"tool": "deliberate_cancel", "args": {"job_id": "xxx"}}, "link": "javascript:x"}

    def upstream(req):
        return httpx.Response(200, stream=_Turn([_sse("token", {"delta": "심의를 맡겼습니다"}), _sse("job_card", CARD), _sse("job_card", evil),
                                                 _sse("result", {"type": "text", "content": "심의를 맡겼습니다"}), _sse("done", {})]),
                              headers={"content-type": "text/event-stream"})
    real = app.state.agent_client
    app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(upstream))
    try:
        cid = c.post("/agent/conversations", json={"title": "t"}, headers=h).json()["id"]
        with c.stream("POST", "/agent/chat", json={"message": "실행", "conversation_id": cid}, headers=h) as r:
            text = "".join(r.iter_text())
        msgs = c.get(f"/agent/conversations/{cid}", headers=h).json()["messages"]
    finally:
        app.state.agent_client = real
    assert text.count("event: job_card") == 2, "중계는 바이트를 그대로 넘긴다(화면이 다시 거른다)"
    meta = [m for m in msgs if m["role"] == "assistant"][-1]["meta"]
    (one, two) = meta["job_cards"]
    assert one == M.card_pointer(CARD) and one["status_call"]["tool"] == "deliberate_status"
    assert "status_call" not in two and "link" not in two, "다른 도구 · 규칙 밖 링크는 남기지 않는다"


# ── 다시 묻기 창구 ─────────────────────────────────────────────────────────────────────────────────────────────
@pytest.fixture()
def paged():
    """엔진 mcp_pages 를 그대로 읽는다 — delib_jobs 에서 _env_int 하나만 쓰므로 그 자리만 대역을 둔다. 쪽 크기를 바닥(4,000자)으로."""
    p = _AGENT / "mcp_pages.py"
    if not p.exists():
        pytest.skip(f"형제 리포 없음: {p}")
    stub = types.ModuleType("delib_jobs")
    stub._env_int = lambda _name, default: default
    keep = sys.modules.get("delib_jobs")
    sys.modules["delib_jobs"] = stub
    try:
        spec = importlib.util.spec_from_file_location("_agent_mcp_pages_for_portal", p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        if keep is None:
            sys.modules.pop("delib_jobs", None)
        else:
            sys.modules["delib_jobs"] = keep
    mod.PAGE_CHARS = mod.PAGE_FLOOR
    return mod


def all_parts(mod, out: dict, ids=()) -> list[dict]:
    first = mod.paged(out, part=1, again={"job_id": "j"}, ids=ids)
    parts = (first.get("page") or {}).get("parts", 1)
    return [first] + [mod.paged(out, part=n, again={"job_id": "j"}, ids=ids) for n in range(2, parts + 1)]


def test_쪽으로_나뉜_답을_원래대로_잇는다(paged):
    out = {"job_id": JOB, "status": "done", "question": "질문 " * 300,
           "decision": "".join(f"{i:05d} 결정문 문단 — 근거 [e:{i % 7}]\n" for i in range(900))}
    pages = all_parts(paged, out, ids=("job_id", "status"))
    assert len(pages) > 3, "시험이 쪽 나누기를 타야 한다"
    assert M.join_pages(pages) == out
    lst = {"jobs": [{"job_id": f"default-20261128-0{i:05d}-abc{i:03d}", "question": f"화두 {i} " + "긴 변경 요지 " * (40 + i * 13),
                     "seats": [f"s{k}" for k in range(i)], "mine": True} for i in range(25)],
           "running": 1, "queued": 0, "filter": {"since": "2026-11-01"}}
    pages = all_parts(paged, lst, ids=("running", "queued", "filter"))
    assert len(pages) > 3
    assert M.join_pages(pages) == lst
    assert M.join_pages([out]) == out, "한 쪽 답은 그대로"
    with pytest.raises(M.PageJoinError):
        M.join_pages([pages[0], pages[2]])


def login(c: TestClient, email: str) -> dict:
    r = c.post("/auth/local/login", json={"email": email, "password": PW})
    assert r.status_code == 200, r.text
    return {"X-CSRF-Token": c.cookies.get(CSRF_COOKIE)}


class Agent:
    """에이전트 서버 대역(POST /deliberate/continue 등) — 받은 요청을 적고 answer(req) 로 답한다."""

    def __init__(self):
        self.seen: list[httpx.Request] = []
        self.answer = lambda req: httpx.Response(200, json={"job_id": "diagnosis-20261128-090000-fff000", "status": "queued", "step": "",
                                                            "continued_from": json.loads(req.content)["previous_job_id"],
                                                            "note": "줄을 섰다 — 앞에 1건"})

    def __call__(self, req):
        self.seen.append(req)
        return self.answer(req)


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """boss = 원장 관리자 · OWNER = CAEG(심의 권한) · OUT = 소속 없음. 게이트웨이 도구는 replies[도구](인자) 로 답한다. 원장은 임시 폴더."""
    monkeypatch.delenv("PORTAL_ADMIN_EMAILS", raising=False)
    s = Settings(_env_file=None, user_store_path=str(tmp_path / "users.sqlite"), agent_audit_log_path=str(tmp_path / "audit.sqlite"),
                 token_store_path=str(tmp_path / "tokens.sqlite"), conv_store_path=str(tmp_path / "conv.sqlite"),
                 conn_key_path=str(tmp_path / "conn.key"), local_bootstrap_admins="boss@example.com", gateway_shared_token="sekret",
                 agent_server_url="http://agent.invalid", delib_conv_sync_s=0)
    app.dependency_overrides[get_settings] = lambda: s
    from app.auth.routes.local import _rl
    _rl.clear()
    calls: list = []
    replies: dict = {}

    async def fake_mcp(url, pat, tool, args, timeout=90.0):
        calls.append((tool, dict(args), bool(pat)))
        return replies[tool](args)
    monkeypatch.setattr(U, "mcp_call", fake_mcp)
    with TestClient(app) as c:
        keep = (app.state.user_store, app.state.agent_audit, app.state.token_store, app.state.conv_store, app.state.agent_client)
        app.state.user_store, app.state.agent_audit, app.state.token_store = UserStore(s), AuditLog(s), TokenStore(s)
        app.state.conv_store = ConversationStore(s)
        agent = Agent()
        app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(agent))
        for email in ("boss@example.com", OWNER, OUT):
            assert c.post("/auth/local/signup", json={"email": email, "name": email.split("@")[0], "password": PW}).status_code < 300
        for email in (OWNER, OUT):
            assert app.state.user_store.approve(email, by="boss@example.com", groups=[])
        hb = login(c, "boss@example.com")
        assert c.patch(f"/auth/access/users/{OWNER}", json={"affiliation": "CAEG"}, headers=hb).status_code == 200
        c.cookies.clear()
        try:
            yield SimpleNamespace(c=c, agent=agent, calls=calls, replies=replies, store=app.state.conv_store, s=s)
        finally:
            app.state.user_store, app.state.agent_audit, app.state.token_store, app.state.conv_store, app.state.agent_client = keep
    app.dependency_overrides.pop(get_settings, None)


def ingested(e) -> tuple[str, str]:
    """OWNER 의 대화에 엔진 잡 하나를 들인다(로컬 계정의 sub 는 이메일이다) → (대화 id, 잡 id)."""
    conv_item, ledger = _engine_conv()
    j = _job(JOB)
    ledger[j["id"]] = j
    assert e.store.ingest_mcp_delib(owner_sub=OWNER, job_id=j["id"], root_job_id=j["id"], title="t", messages=M.messages_of(conv_item(j)),
                                    finished_at=j["finished_at"]) == "new"
    (conv,) = e.store.list_for_owner(OWNER)
    return conv["id"], j["id"]


def test_다시_묻기는_그_사람의_PAT_로_deliberate_status_를_부르고_들인_대화를_알려준다(env, paged):
    cid, jid = ingested(env)
    h = login(env.c, OWNER)
    env.replies["deliberate_status"] = lambda a: {"job_id": a["job_id"], "status": "done", "stage": "report", "round": 3, "total_rounds": 3,
                                                  "report_id": 12, "error": None}
    r = env.c.get(f"/agent/engine-delib/status/{jid}", headers=h)
    assert r.status_code == 200, r.text
    assert env.calls[-1] == ("deliberate_status", {"job_id": jid, "brief": True}, True)
    assert r.json()["phase"] == "end" and r.json()["report_id"] == 12 and r.json()["conversation_id"] == cid
    big = {"job_id": jid, "status": "running", "round": 1, "total_rounds": 3, "question": "긴 화두 " * 3000,
           "queue": {"position": 2, "ahead": 1, "length": 3, "x": 1}}
    env.replies["deliberate_status"] = lambda a: paged.paged(big, part=int(a.get("part") or 1), again={"job_id": jid, "brief": True},
                                                             ids=("job_id", "status"))
    got = env.c.get(f"/agent/engine-delib/status/{jid}", headers=h).json()
    assert [c[1].get("part") for c in env.calls[1:]][:2] == [None, 2], "쪽을 넘겨 받는다"
    assert got["phase"] == "run" and "conversation_id" not in got and got["queue"] == {"position": 2, "ahead": 1, "length": 3}
    assert env.c.get("/agent/engine-delib/status/..%2Fetc", headers=h).status_code in (404, 422)


def test_다시_묻기는_심의_권한이_있어야_한다(env):
    login(env.c, OUT)
    assert env.c.get(f"/agent/engine-delib/status/{JOB}").status_code == 403
