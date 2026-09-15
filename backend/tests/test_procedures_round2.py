# **고친 것이 남긴 것** — 2026-09-15 2차 감사가 짚은 자리들
#
# 이 파일은 특이하다. 여기 담긴 결함은 전부 **같은 날 앞선 수정이 만들거나 드러낸 것**이다.
# 고친 자리 옆에서 새 결함이 나는 것은 흔한 일이고, 그래서 고친 뒤에 다시 본다.
import asyncio
import json

import httpx
import pytest

from app.config import Settings
from app.procedures.models import ProcedureSpec
from app.procedures.runner import ProceduresRunner
from app.procedures.store import ProceduresStore


class _P:
    subject, email, groups = "u1", "u1@corp.com", ["feat:procedures"]


@pytest.fixture()
def store(tmp_path):
    return ProceduresStore(Settings(procedures_store_path=str(tmp_path / "w.sqlite")))


def _runner(store, reply_by_tool: dict, seen: list | None = None):
    def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content or b"{}") if req.content else {}
        if body.get("method") == "initialize":
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": {}},
                                  headers={"mcp-session-id": "t"})
        if body.get("method") == "tools/list":
            tools = [{"name": n, "description": "", "inputSchema": {}}
                     for n in reply_by_tool]
            out = {"jsonrpc": "2.0", "id": 2, "result": {"tools": tools}}
            return httpx.Response(200, text=f"data: {json.dumps(out)}\n\n",
                                  headers={"content-type": "text/event-stream"})
        args = (body.get("params") or {}).get("arguments") or {}
        if seen is not None:
            seen.append(args)
        payload = reply_by_tool.get(args.get("name"), {})
        out = {"jsonrpc": "2.0", "id": 3, "result": {"isError": False, "content": [
            {"type": "text", "text": json.dumps(payload)}]}}
        return httpx.Response(200, text=f"data: {json.dumps(out)}\n\n",
                              headers={"content-type": "text/event-stream"})

    return ProceduresRunner(
        settings=Settings(gateway_shared_token="t"), store=store,
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=5.0),
        mint_pat=lambda p, run, ix: "pat")


# ── ① 노트를 더하는 것과 마감하는 것은 다른 일이다 ────────────────────────
def test_노트를_더해도_성패가_안_지워진다(store):
    """`finish_step` 은 `state·ok·error·stage` 를 **항상** 쓴다. 노트만 주려고 그걸
    다시 부르면 앞서 적은 실패 사유가 지워지고 `ok` 가 기본값으로 돌아간다 —
    챗 원장의 절단 표식이 정확히 그러고 있었고, 바로 전 커밋을 경계 한 칸에서 되돌렸다."""
    rid = store.create_run(owner_sub="u1", mode="live")
    store.begin_step(rid, 0, backend="", tool="t", args={})
    store.finish_step(rid, 0, ok=False, state="unknown", stage="no_outcome",
                      result_text="본문", error="성패를 못 받았다")
    store.annotate_step(rid, 0, {"truncated": 10})

    s = store.get_run(rid)["steps"][0]
    assert s["state"] == "unknown" and s["ok"] == 0
    assert s["error"] == "성패를 못 받았다" and s["stage"] == "no_outcome"
    assert s["notes"]["truncated"] == 10
    assert store.step_result(rid, 0) == "본문"


# ── ② 2^53 위에서 서로 다른 id 를 같다고 하던 것 ──────────────────────────
def test_큰_정수_둘을_한_변수로_합치지_않는다():
    """`str(int(float(n)))` 은 2^53 위에서 **다른 수**다. 앞 라운드가 `"0012" == 12` 를
    막으면서 이 끝은 그대로 뒀다 — 막으려던 사고가 위쪽에 남아 있었다."""
    from app.procedures import derive

    assert derive._same("9007199254740992", 9007199254740993) is False
    assert derive._same(9007199254740993, 9007199254740992) is False
    assert derive._vkey(9007199254740993) != derive._vkey(9007199254740992)
    assert str(10 ** 30) in derive._num_text(10 ** 30)
    # 같은 값은 여전히 같다 — 너무 조이면 진짜 체인을 놓친다
    assert derive._vkey(10) == derive._vkey(10.0) == derive._vkey("10")
    assert derive._same("12", 12) and derive._same(10, 10.0)

    got = derive.draft([
        {"tool": "get_record", "args": {"record_id": 9007199254740993}, "result": {}},
        {"tool": "get_record", "args": {"record_id": 9007199254740992}, "result": {}},
    ], tool_backend={"get_record": "a"},
        asked="레코드 9007199254740993 와 9007199254740992 를 비교해줘")
    names = {s["args"]["record_id"] for s in got["spec"]["steps"]}
    assert len(names) == 2, f"서로 다른 id 가 한 변수로 합쳐졌다: {names}"


# ── ③ 큰 save 값이 원장을 부풀리던 것 ─────────────────────────────────────
def test_큰_save_값은_원장에_안_넣고_말한다(store):
    """`inputs_json` 은 통째로 다시 쓰는 한 덩이라, 큰 값을 넣으면 단계마다 그만큼을
    다시 쓴다(실측 2.5MB × 10단계 = 25MB · 2.7초, 전부 이벤트 루프 위)."""
    big = {"rows": [{"id": f"R{i}", "v": "x" * 100} for i in range(4000)]}
    spec = ProcedureSpec.model_validate({"title": "t", "vars": [], "steps": [
        {"backend": "ra", "tool": "big", "args": {}, "save": {"rows": "rows"}},
        {"backend": "ra", "tool": "small", "args": {}, "save": {"rid": "id"}},
    ]})
    r = _runner(store, {"ra_big": big, "ra_small": {"id": "R-1"}})
    rid = store.create_run(owner_sub="u1", inputs={}, mode="live")
    assert asyncio.run(r.run(run_id=rid, spec=spec, principal=_P()))["state"] == "done"

    run = store.get_run(rid)
    assert "rows" not in run["inputs"], "큰 값이 원장에 들어갔다"
    assert run["inputs"]["rid"] == "R-1", "작은 값까지 막으면 안 된다"
    note = run["steps"][0]["notes"]
    assert note["save_not_persisted"] == ["rows"], note
    assert "재개" in note["why"], "재개가 안 된다는 것을 말해야 한다"
    # 결과 자체는 그대로 있다 — 못 남긴 것은 **입력 사본**이지 결과가 아니다
    assert store.step_result(rid, 0)
