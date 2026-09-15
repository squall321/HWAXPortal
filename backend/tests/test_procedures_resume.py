# 게이트에서 멈췄다 다시 이어갈 때 — **앞에서 뽑아 둔 값이 살아남는가**(2026-09-15 감사)
#
# 무엇이 깨져 있었나. `save` 는 `scope` 에만 들어갔다. `scope` 는 `run()` 호출 안에서만
# 살고, 재개는 새 `run()` 이라 `run["inputs"]` 에서 scope 를 다시 만든다. 거기 없으니
# 그 값을 쓰는 단계가 `TemplateError` 로 죽고, 그 예외는 `_loop` 밖이라 아무도 안 받아
# 실행이 **`running` 인 채 영원히** 남았다. 화면은 계속 '도는 중' 이다.
#
# 하필 이 모양이 가장 흔하다 — 앞에서 대상을 뽑고, 되돌리기 어려운 다음 단계를 게이트로
# 막는 것. 그게 통째로 재개가 안 됐다.
import asyncio
import json

import httpx
import pytest

from app.config import Settings
from app.procedures.models import ProcedureSpec
from app.procedures.runner import ProceduresRunner
from app.procedures.store import ProceduresStore

SPEC = ProcedureSpec.model_validate({
    "title": "뽑고 → 게이트 → 쓴다",
    "vars": [],
    "steps": [
        {"backend": "ra", "tool": "find_reports", "args": {"q": "x"},
         "save": {"rid": "reports[0].id"}},
        {"backend": "ra", "tool": "add_report_tags", "gate": "human",
         "args": {"report_id": "{{rid}}"}},
    ],
})


class _P:
    subject, email, groups = "u1", "u1@corp.com", ["feat:procedures"]


def _runner(store, seen: list):
    """게이트웨이를 MockTransport 로 — 1단계는 보고서 하나, 2단계는 기록만 한다."""
    def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content or b"{}") if req.content else {}
        if body.get("method") == "initialize":
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": {}},
                                  headers={"mcp-session-id": "t"})
        if body.get("method") == "tools/list":
            tools = [{"name": n, "description": "", "inputSchema": {}}
                     for n in ("ra_find_reports", "ra_add_report_tags")]
            out = {"jsonrpc": "2.0", "id": 2, "result": {"tools": tools}}
            return httpx.Response(200, text=f"data: {json.dumps(out)}\n\n",
                                  headers={"content-type": "text/event-stream"})
        args = (body.get("params") or {}).get("arguments") or {}
        seen.append(args)
        payload = ({"reports": [{"id": "R-77"}]}
                   if args.get("name") == "ra_find_reports" else {"tagged": True})
        out = {"jsonrpc": "2.0", "id": 3, "result": {"isError": False, "content": [
            {"type": "text", "text": json.dumps(payload)}]}}
        return httpx.Response(200, text=f"data: {json.dumps(out)}\n\n",
                              headers={"content-type": "text/event-stream"})

    return ProceduresRunner(
        settings=Settings(gateway_shared_token="t"), store=store,
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=5.0),
        mint_pat=lambda p, run, ix: "pat")


@pytest.fixture()
def store(tmp_path):
    return ProceduresStore(Settings(procedures_store_path=str(tmp_path / "wb.sqlite")))


def test_게이트_앞에서_뽑은_값이_재개까지_살아남는다(store):
    seen: list = []
    r = _runner(store, seen)
    rid = store.create_run(owner_sub="u1", inputs={}, mode="live")

    got = asyncio.run(r.run(run_id=rid, spec=SPEC, principal=_P()))
    assert got["state"] == "gated" and got["stopped_at"] == 1, got
    # ⚠ **여기가 요점이다.** scope 가 아니라 원장에 남아야 재개가 읽는다.
    assert store.get_run(rid)["inputs"].get("rid") == "R-77", \
        "뽑은 값이 원장에 없다 — 재개하면 TemplateError 로 죽고 실행이 running 에 남는다"

    # 게이트 카드에 실제 대상이 찍혀야 사람이 무엇을 승인하는지 안다
    assert store.get_run(rid)["steps"][1]["args"] == {"report_id": "R-77"}


def test_재개가_실제로_끝까지_간다(store):
    """위 검사의 짝 — 값이 남아 있기만 하고 재개가 안 되면 소용없다."""
    seen: list = []
    r = _runner(store, seen)
    rid = store.create_run(owner_sub="u1", inputs={}, mode="live")
    assert asyncio.run(r.run(run_id=rid, spec=SPEC, principal=_P()))["state"] == "gated"

    # 승인 — 인자 지문에 묶인 1회용이다
    from app.procedures.runner import _sha

    store.ack_gate(rid, 1, by="u1", args_sha256=_sha(store.get_run(rid)["steps"][1]["args"]))
    got = asyncio.run(r.run(run_id=rid, spec=SPEC, principal=_P(), start_at=1))
    assert got["state"] == "done", got
    calls = [a for a in seen if isinstance(a, dict) and "arguments" in a]
    assert calls[-1]["arguments"] == {"report_id": "R-77"}, \
        f"재개 단계가 받은 인자: {calls[-1]}"
