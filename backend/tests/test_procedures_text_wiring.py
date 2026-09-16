# 평문(raw) 단계의 실패가 **실행 전체를 멈추는가** — 판정기 함수가 아니라 실행기 배선을 본다
#
# judge 에 평문 실패 머리·성공 표식(ok_text)을 넣어도, 실행기가 ok_text 를 안 넘기면 그대로 샌다.
# test_procedures_resume.py 와 같은 틀 — 진짜 ProceduresRunner 에 MockTransport 게이트웨이를 붙인다.
# 평문은 KooSlurm 실측·소스(tests/fixtures/procedures/smarttwin_text_responses.json).
import asyncio
import json
from pathlib import Path

import httpx
import pytest

from app.config import Settings
from app.procedures.models import ProcedureSpec
from app.procedures.runner import ProceduresRunner
from app.procedures.store import ProceduresStore

_SMT = json.loads((Path(__file__).parent / "fixtures" / "procedures"
                   / "smarttwin_text_responses.json").read_text(encoding="utf-8"))


class _P:
    subject, email, groups = "u1", "u1@corp.com", ["feat:procedures"]


def _spec(ok_text: str | None) -> ProcedureSpec:
    step = {"backend": "smart-twin-cluster", "tool": "smarttwin_scenario_options",
            "args": {"sim_type": "fullangle_drop"}, "raw": True}
    if ok_text:
        step["ok_text"] = ok_text
    return ProcedureSpec.model_validate({"title": "평문 단계", "vars": [], "steps": [step]})


def _runner(store, text: str):
    def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content or b"{}") if req.content else {}
        if body.get("method") == "initialize":
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": {}},
                                  headers={"mcp-session-id": "t"})
        if body.get("method") == "tools/list":
            out = {"jsonrpc": "2.0", "id": 2, "result": {"tools": [
                {"name": "smarttwincluster_smarttwin_scenario_options", "description": "", "inputSchema": {}}]}}
            return httpx.Response(200, text=f"data: {json.dumps(out)}\n\n",
                                  headers={"content-type": "text/event-stream"})
        out = {"jsonrpc": "2.0", "id": 3, "result": {"isError": False, "content": [
            {"type": "text", "text": text}]}}
        return httpx.Response(200, text=f"data: {json.dumps(out)}\n\n",
                              headers={"content-type": "text/event-stream"})

    return ProceduresRunner(
        settings=Settings(gateway_shared_token="t"), store=store,
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=5.0),
        mint_pat=lambda p, run, ix: "pat")


@pytest.fixture()
def store(tmp_path):
    return ProceduresStore(Settings(procedures_store_path=str(tmp_path / "wb.sqlite")))


def _run(store, text: str, ok_text: str | None) -> dict:
    rid = store.create_run(owner_sub="u1", inputs={}, mode="live")
    return asyncio.run(_runner(store, text).run(run_id=rid, spec=_spec(ok_text), principal=_P()))


def test_평문_error_머리가_오면_실행이_실패로_멈춘다(store):
    got = _run(store, _SMT["submit_http_fail"], None)
    assert got["state"] == "failed" and got.get("kind") == "text_error", got


def test_ok_text_를_실행기가_실제로_넘긴다(store):
    """머리 없는 실패 문구 — ok_text 가 배선돼 있어야만 멈춘다."""
    got = _run(store, _SMT["submit_parse_fail"], r"(\[DRY-RUN\]|✅ 제출 완료)")
    assert got["state"] == "failed" and got.get("kind") == "text_unexpected", got


def test_정상_평문은_끝까지_간다(store):
    got = _run(store, _SMT["dry_run_fullangle"], r"(\[DRY-RUN\]|✅ 제출 완료)")
    assert got["state"] != "failed", got
