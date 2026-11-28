# 웹 '이어가기' 를 엔진 이어하기로(WD-05) — 대화에 들인 MCP 심의만 · 세션 + CSRF · 엔진에 공유 비밀 + 그 사람의 신원 머리 셋 · 대화에 진행 카드 한 줄
"""docs/request-1125 WD-05 의 포털 몫(POST /agent/engine-delib/continue — app/agent/mcp_delib.py).

엔진 창구(HWAXAgentServer f955eff) POST /deliberate/continue 는 deliberate_continue 와 같은 함수이고 신원 머리(x-hwax-user)가 있어야 한다. 고정하는 것.
  · 계약 — 포털이 싣는 칸(previous_job_id · human_note · keep_seats · rounds)은 엔진 _CONT_FIELDS 안이다(모르는 칸은 422).
  · 엔진에 실리는 것 — 공유 비밀 · 그 사람의 이메일 · 지금 권한 키(feat:deliberation 등) · 원장 소속(게이트웨이가 MCP 호출에 싣는 것과 같은 셋).
  · 막는 것 — 그 대화에 들인 잡이 아니면 409 · CSRF 없으면 403 · 심의 권한 없으면 403 · 틀린 라운드 422, 모두 엔진을 부르지 않는다.
  · 엔진의 거절은 code · message 그대로, 옛 엔진(창구 없음)은 agent_outdated, 거절된 이어하기는 대화에 남기지 않는다.
"""
import ast
import json
from pathlib import Path

import httpx
import pytest
from tests.test_job_card import env, ingested, login  # noqa: F401  (env 는 픽스처)
from tests.test_mcp_delib import OUT, OWNER

_AGENT = Path(__file__).resolve().parents[3] / "HWAXAgentServer"


def test_포털이_싣는_칸은_엔진의_받는_칸이다():
    p = _AGENT / "app.py"
    if not p.exists():
        pytest.skip(f"형제 리포 없음: {p}")
    tree = ast.parse(p.read_text(encoding="utf-8"))
    fields = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                  and any(getattr(t, "id", "") == "_CONT_FIELDS" for t in n.targets))
    assert {"previous_job_id", "human_note", "keep_seats", "rounds"} <= set(fields)
    src = p.read_text(encoding="utf-8")
    assert '@app.post("/deliberate/continue")' in src and '"identity_required"' in src


def test_이어하기는_엔진에_그_사람의_신원으로_맡기고_대화에_진행_카드를_남긴다(env):
    cid, jid = ingested(env)
    h = login(env.c, OWNER)
    r = env.c.post("/agent/engine-delib/continue", json={"conversation_id": cid, "previous_job_id": jid, "human_note": "낙하 최우선",
                                                         "rounds": 4}, headers=h)
    assert r.status_code == 200, r.text
    (req,) = env.agent.seen
    assert str(req.url) == "http://agent.invalid/deliberate/continue"
    assert req.headers["authorization"] == "Bearer sekret" and req.headers["x-hwax-user"] == OWNER
    assert "feat:deliberation" in req.headers["x-hwax-groups"].split(","), "그 사람의 지금 권한 키"
    assert req.headers.get("x-hwax-affiliation") == "CAEG"
    assert json.loads(req.content) == {"previous_job_id": jid, "human_note": "낙하 최우선", "keep_seats": True, "rounds": 4}
    got = r.json()
    assert got["job_id"] == "diagnosis-20261128-090000-fff000"
    assert got["card"]["status_call"] == {"tool": "deliberate_status", "args": {"job_id": got["job_id"]}}
    assert got["card"]["phase"] == "run" and got["card"]["continued_from"] == jid
    last = env.c.get(f"/agent/conversations/{cid}", headers=h).json()["messages"][-1]
    assert last["role"] == "assistant" and last["meta"]["job_cards"] == [got["card"]] and "줄을 섰다" in last["content"]


def test_이어하기는_그_대화에_들인_잡만_세션_CSRF_로만(env):
    cid, jid = ingested(env)
    h = login(env.c, OWNER)
    body = {"conversation_id": cid, "previous_job_id": "default-20261128-010101-000000", "human_note": "x"}
    assert env.c.post("/agent/engine-delib/continue", json=body, headers=h).status_code == 409
    assert env.c.post("/agent/engine-delib/continue", json={**body, "previous_job_id": jid}).status_code == 403, "CSRF 없음"
    assert env.c.post("/agent/engine-delib/continue", json={**body, "previous_job_id": jid, "rounds": 1}, headers=h).status_code == 422
    env.c.cookies.clear()
    ho = login(env.c, OUT)
    r = env.c.post("/agent/engine-delib/continue", json={**body, "previous_job_id": jid}, headers=ho)
    assert r.status_code == 403, "심의 권한이 없다(소속 없음)"
    assert env.agent.seen == [], "엔진을 부르지 않았다"


def test_엔진의_거절은_code_그대로(env):
    cid, jid = ingested(env)
    h = login(env.c, OWNER)
    env.agent.answer = lambda req: httpx.Response(422, json={"code": "bad_request", "message": "이전 심의에 결정문이 없다(status=error)"})
    r = env.c.post("/agent/engine-delib/continue", json={"conversation_id": cid, "previous_job_id": jid, "human_note": "x"}, headers=h)
    assert r.status_code == 422 and r.json() == {"code": "bad_request", "message": "이전 심의에 결정문이 없다(status=error)"}
    env.agent.answer = lambda req: httpx.Response(404, json={"detail": "Not Found"})
    r = env.c.post("/agent/engine-delib/continue", json={"conversation_id": cid, "previous_job_id": jid, "human_note": "x"}, headers=h)
    assert r.status_code == 404 and r.json()["code"] == "agent_outdated"
    msgs = env.c.get(f"/agent/conversations/{cid}", headers=h).json()["messages"]
    assert not any((m.get("meta") or {}).get("job_cards") for m in msgs), "거절된 이어하기는 대화에 남기지 않는다"
