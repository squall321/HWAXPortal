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


# ── ④ 예약 이름이 save·select 로는 뚫려 있었다 ────────────────────────────
def test_예약_이름은_save_로도_못_만든다():
    """`Var._key` 는 `run_id`·`me.*` 를 막는데 save·select 는 안 봤다. 실행기가 범위에
    신원을 **덮어쓰므로**, 같은 `{{run_id}}` 가 한 `_loop` 안에서는 save 값이고 재개
    뒤에는 진짜 실행 id 가 된다 — 때에 따라 다른 것을 가리킨다."""
    from app.procedures.models import validate_spec

    def _hard(step):
        spec = ProcedureSpec.model_validate({"title": "t", "vars": [],
                                             "steps": [{"backend": "b", "tool": "t", **step}]})
        return [e for e in validate_spec(spec) if not e.startswith("warn:")]

    assert any("예약어" in e for e in _hard({"save": {"run_id": "x"}}))
    assert any("예약어" in e for e in
               _hard({"select": {"from": "p", "save": "n", "as": "run_id"}}))
    # 평범한 이름은 그대로 통과한다
    assert _hard({"save": {"rid": "x"}}) == []


def test_사람_말_경계는_한국어에서도_돈다():
    """경계를 "뒤에 글자가 오면 다른 이름" 으로 두면 한국어 문장에서 거의 다 놓친다 —
    조사를 값에 붙여 쓰기 때문이다. ASCII 기준으로 본다."""
    from app.procedures.derive import _in_prose

    assert _in_prose("BRKT", "BRKT부품 을 골라") is True
    assert _in_prose("PANEL_1", "PANEL_1을 분석") is True
    assert _in_prose("12.5", "두께 12.5mm") is True
    # 더 긴 식별자의 일부는 그 값이 아니다
    assert _in_prose("12", "12_ASSY") is False
    assert _in_prose("BRKT", "BRKT_1_ASSY") is False
    assert _in_prose("12.5", "2012.5월") is False


def test_같은_경고가_줄줄이_나오지_않는다():
    """**99%에서 울리는 검출기는 검출기가 아니다.** `{"path": [파일 50개]}` 면 같은 말이
    50줄 나오고, 진짜 오류가 그 아래 묻힌다."""
    from app.procedures.models import _collapse, _scan_args

    many = _collapse(_scan_args({"path": [f"/d/f{i}" for i in range(50)]}, "1단계"))
    assert len(many) == 1 and "50곳" in many[0], many
    # 몇 개 안 되면 그대로 보인다 — 뭉치는 것이 정보를 지우면 안 된다
    few = _collapse(_scan_args({"path": ["/a", "/b"]}, "1단계"))
    assert len(few) == 2, few
    # 딱딱한 오류도 같이 뭉치되 **딱딱한 채로** 남는다
    hard = _collapse(_scan_args(
        {"headers": {"Authorization": [f"Bearer sk-{i}" for i in range(5)]}}, "1단계"))
    assert len(hard) == 1 and not hard[0].startswith("warn:"), hard


# ── ⑤ 한 단계에 save 와 select 를 같이 쓰면 select 가 깨졌다(3차 감사) ─────
def test_save_와_select_를_같이_써도_돈다(store):
    """`SAVE_PERSIST_MAX` 를 넣으면서 루프 변수를 `v` 로 둬 **바로 위의 판정을 덮었다.**
    `_pick` 이 `v.parsed` 를 읽다 `AttributeError` 를 내고, 그 넓은 except 가 그것을
    "후보 없음" 으로 바꾼다 — 후보가 둘 있는데 "룰이 아무것도 못 골랐다" 가 된다.

    가장 나쁜 모양은 `on_none: skip` 이다. 그러면 **전부 초록인 채로** 뒤 단계가 헛돈다 —
    context-notes 가 "조용히 건너뛰면 뒤 단계가 전부 헛도는데 화면은 정상으로 보인다"
    고 적은 그 상태를 코드가 만들어 냈다.
    """
    spec = ProcedureSpec.model_validate({"title": "t", "vars": [], "steps": [
        {"backend": "ra", "tool": "find_parts", "args": {},
         "save": {"total": "count"},
         "select": {"from": "rows", "save": "pid", "as": "pid", "on_many": "first"}},
        {"backend": "ra", "tool": "get_part", "args": {"id": "{{pid}}"}},
    ]})
    seen: list = []
    r = _runner(store, {"ra_find_parts": {"count": 2, "rows": [{"pid": "P-1"},
                                                               {"pid": "P-2"}]},
                        "ra_get_part": {"ok": True}}, seen)
    rid = store.create_run(owner_sub="u1", inputs={}, mode="live")
    got = asyncio.run(r.run(run_id=rid, spec=spec, principal=_P()))

    assert got["state"] == "done", got
    run = store.get_run(rid)
    assert run["inputs"]["pid"] == "P-1", f"select 가 못 골랐다: {run['inputs']}"
    assert run["inputs"]["total"] == 2, "save 도 함께 돌아야 한다"
    calls = [a for a in seen if isinstance(a, dict) and "arguments" in a]
    assert calls[-1]["arguments"] == {"id": "P-1"}, calls[-1]


def test_상한은_글자가_아니라_바이트로_센다(store):
    """한국어는 UTF-8 로 글자당 3바이트다 — 글자 수로 세면 상한의 3배까지 통과해,
    상한이 막으려던 병이 그대로 난다."""
    from app.procedures.runner import SAVE_PERSIST_MAX

    ko = "가" * (SAVE_PERSIST_MAX // 2)          # 글자로는 절반, 바이트로는 1.5배
    assert len(ko) < SAVE_PERSIST_MAX < len(ko.encode("utf-8"))
    spec = ProcedureSpec.model_validate({"title": "t", "vars": [], "steps": [
        {"backend": "ra", "tool": "big", "args": {}, "save": {"txt": "text"}}]})
    rid = store.create_run(owner_sub="u1", inputs={}, mode="live")
    r = _runner(store, {"ra_big": {"text": ko}})
    assert asyncio.run(r.run(run_id=rid, spec=spec, principal=_P()))["state"] == "done"
    assert "txt" not in store.get_run(rid)["inputs"], "한국어가 상한을 빠져나갔다"
