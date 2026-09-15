# 2단 도구 — 역량이 도구 하나 뒤에 숨은 자리를 절차가 단계로 쓰는가(PLAN §9-4·§9-5)
#
# 왜 이게 필요했나. 게이트웨이 도구 지도 466개를 훑고 "DynaForge 에는 물성을 갱신하는
# 도구가 없다" 고 판단했다 — **틀렸다.** `list_operations` 를 부르니 연산 47개가 있었고
# 그중 `matdb`·`matswap` 이 물성 교체였다. 도구가 아니라 `run_operation` 뒤에 있어서
# `search_tools` 로도 안 나오고 카탈로그에도 1로 세어진다.
#
# 아래 고정물은 **실물 응답 모양**이다(2026-09-14 게이트웨이 실호출에서 줄인 것).
import asyncio
import json
from pathlib import Path

import pytest

from app.procedures import dispatch
from app.procedures.models import ProcedureSpec, check_against_schemas

ROOT = Path(__file__).resolve().parents[2]

# ── 실물 응답 모양 ───────────────────────────────────────────────────────
DESCRIBE_MATDB = {
    "name": "matdb", "category": "material",
    "summary": "Replace *MAT cards from a JSON material database …",
    "args_schema": {
        "type": "object",
        "properties": {
            "model": {"type": "string", "x-kind": "session_file"},
            "output": {"type": "string"},
            "database": {"type": "string", "x-kind": "session_file"},
            "mat_type": {"type": "string", "default": "MAT_ELASTIC"},
            "thermal": {"type": "boolean", "default": False},
            "materials": {"type": "array"},
        },
        "required": ["model", "output"],
        "additionalProperties": False,
    },
}
GUIDE_MESH = {   # StepForge job_params_guide(kind="mesh") — 형식이 다르다
    "jobs": {"mesh": {
        "rebuild": {"type": "bool", "default": False, "설명": "메시 캐시를 무시하고 다시 굽는다"},
        "parts": {"type": "list", "default": None, "설명": "이 파트만 다시 굽는다"},
        "max_fail_rate": {"type": "float", "default": 0.05, "설명": "실패율 경고 임계"},
    }},
    "공차를_받는_잡": ["detect", "mesh", "pipeline"],
}


@pytest.fixture(scope="module")
def reg():
    return dispatch.load()


# ── 등록부 ───────────────────────────────────────────────────────────────
def test_등록부가_리포와_함께_온다(reg):
    """없으면 2단 지원이 없을 뿐이지만, 있는 것을 확인해 둔다."""
    assert (ROOT / "docs" / "procedures" / "dispatchers.yaml").is_file()
    for key in (("heax-kooremapper_mcp", "run_operation"),
                ("heax-step_forge", "run_job"),
                ("smart-twin-mcp", "catalog_run")):
        assert key in reg, key


def test_후보는_확인한_것만_등재한다():
    """⚠ **확인 못 한 것과 없는 것은 다르다.** 이 박스에 프리셋이 0건이라고 그 앱에
    2단이 없는 게 아니다 — 후보로 두고 `checked` 에 무엇을 봤는지 적는다."""
    import yaml as _y

    raw = _y.safe_load((ROOT / "docs" / "procedures" / "dispatchers.yaml")
                       .read_text(encoding="utf-8"))
    for c in raw.get("candidates") or []:
        assert c.get("checked"), f"확인 기록 없는 후보: {c}"
    # 확정된 것은 전부 describe 를 갖는다 — 그게 2단의 조건이다
    for d in raw["dispatchers"]:
        assert d.get("describe") and d.get("schema_kind")


def test_같은_도구를_두_번_등재하면_거절한다(tmp_path):
    """두 번 적히면 어느 계약을 쓰는지가 파일 순서로 정해진다 — 조용한 오답이다."""
    p = tmp_path / "d.yaml"
    one = {"backend": "a", "tool": "run_x", "selector": "s", "payload": "p",
           "describe": "describe_x"}
    p.write_text(json.dumps({"dispatchers": [one, dict(one)]}), encoding="utf-8")
    with pytest.raises(ValueError, match="두 번"):
        dispatch.load(p)


def test_등록부가_없으면_조용히_비어_있다(tmp_path):
    assert dispatch.load(tmp_path / "없다.yaml") == {}


# ── 두 번째 단의 형식 흡수 ───────────────────────────────────────────────
def test_JSON_스키마는_그대로_쓴다(reg):
    d = reg[("heax-kooremapper_mcp", "run_operation")]
    sch = dispatch.to_json_schema(DESCRIBE_MATDB, d, item="matdb")
    assert sch["required"] == ["model", "output"]
    assert sch["additionalProperties"] is False
    assert "mat_type" in sch["properties"]


def test_다른_형식은_어댑터가_옮긴다(reg):
    """StepForge 는 `{type, default, 설명}` 모양이다 — 앱마다 두 번째 단이 다르다."""
    d = reg[("heax-step_forge", "run_job")]
    sch = dispatch.to_json_schema(GUIDE_MESH, d, item="mesh")
    assert sch["properties"]["rebuild"]["type"] == "boolean", "bool → boolean 으로 옮겨야 한다"
    assert sch["properties"]["parts"]["type"] == "array"
    assert sch["properties"]["max_fail_rate"]["type"] == "number"
    assert "캐시" in sch["properties"]["rebuild"]["description"]
    # ⚠ **닫으면 안 된다.** 앱이 받는 키가 이 표보다 넓다 — 공차는 `jobs` 밖 칸에 있고
    # `pipeline` 은 중첩 블록도 받는다. 실측으로 `mesh` + `clearance_gap` 은 앱이
    # 통과시키는데, 닫아 두면 우리가 저장 시점에 거절한다(모르는 것을 틀렸다고 말한 것).
    assert "additionalProperties" not in sch


def test_모르는_키를_우리가_먼저_거절하지_않는다(reg):
    """실측 회귀 — StepForge 가 받는 공차 키를 우리가 막고 있었다(2026-09-15).

    `clearance_gap` 은 `job_params_guide` 의 `jobs.mesh` 에 **없다**(딴 칸에 있다).
    그런데 `check_job_params("mesh", {"clearance_gap": …})` 는 통과한다 — 실물로 확인.
    """
    d = reg[("heax-step_forge", "run_job")]
    sch = dispatch.to_json_schema(GUIDE_MESH, d, item="mesh")
    assert "clearance_gap" not in sch["properties"], "고정물 전제가 바뀌었다"
    spec = ProcedureSpec.model_validate({
        "title": "t", "vars": [],
        "steps": [{"backend": "heax-step_forge", "tool": "run_job",
                   "args": {"kind": "mesh", "params": {"clearance_gap": 0.05}}}]})
    errs = check_against_schemas(
        spec, {"heaxstep_forge_run_job": {"properties": {"kind": {"type": "string"},
                                                         "params": {"type": "object"}}}},
        {("heax-step_forge", "run_job", "mesh"): sch})
    assert errs == [], f"앱이 받는 인자를 우리가 거절했다: {errs}"


def test_못_옮기면_지어내지_않는다(reg):
    d = reg[("heax-kooremapper_mcp", "run_operation")]
    assert dispatch.to_json_schema({"summary": "스키마가 없다"}, d, item="matdb") is None
    assert dispatch.to_json_schema("문자열", d, item="matdb") is None
    g = reg[("heax-step_forge", "run_job")]
    assert dispatch.to_json_schema(GUIDE_MESH, g, item="없는종류") is None


# ── 저장 시점 검증이 속 인자까지 본다 ─────────────────────────────────────
GW = {"heaxkooremapper_mcp_run_operation": {
    "properties": {"operation": {"type": "string"}, "args": {"type": "object"},
                   "session_id": {"type": "string"}},
    "required": ["operation"]}}


def _spec(args: dict) -> ProcedureSpec:
    return ProcedureSpec.model_validate({
        "title": "물성 교체",
        "steps": [{"backend": "heax-kooremapper_mcp", "tool": "run_operation", "args": args}],
    })


def test_속_인자_오타가_저장에서_걸린다():
    """**이것이 요점이다.** 게이트웨이 스키마상 `args` 는 속성 없는 object 라 그냥 통과한다.
    그러면 `outut` 오타가 실행 시점에야 터지고, 그때는 앞 단계가 이미 돌아 있다."""
    spec = _spec({"operation": "matdb", "args": {"model": "a.k", "outut": "b"}})
    second = {("heax-kooremapper_mcp", "run_operation", "matdb"): DESCRIBE_MATDB["args_schema"]}

    assert check_against_schemas(spec, GW) == [], "1단만 보면 통과한다(그게 문제였다)"
    errs = check_against_schemas(spec, GW, second)
    assert any("outut" in e for e in errs), errs
    assert any("output" in e and "빠졌다" in e for e in errs), errs


def test_제대로_적으면_통과한다():
    spec = _spec({"operation": "matdb", "args": {"model": "a.k", "output": "b",
                                                 "mat_type": "MAT_024"}})
    second = {("heax-kooremapper_mcp", "run_operation", "matdb"): DESCRIBE_MATDB["args_schema"]}
    assert check_against_schemas(spec, GW, second) == []


def test_무엇을_부를지_변수면_검사하지_않는다():
    """저장 시점엔 어느 연산인지 모른다 — 모르는 것을 틀렸다고 하지 않는다."""
    spec = _spec({"operation": "{{op}}", "args": {"아무거나": 1}})
    second = {("heax-kooremapper_mcp", "run_operation", "matdb"): DESCRIBE_MATDB["args_schema"]}
    assert check_against_schemas(spec, GW, second) == []


def test_두_번째_단을_못_받았으면_검사하지_않는다():
    """describe 를 못 불렀을 때 **모른다**와 **틀렸다**를 섞으면 안 된다."""
    spec = _spec({"operation": "matdb", "args": {"outut": "b"}})
    assert check_against_schemas(spec, GW, None) == []
    assert check_against_schemas(spec, GW, {}) == []


def test_등록부에_없는_도구는_건드리지_않는다():
    spec = ProcedureSpec.model_validate({
        "title": "t", "steps": [{"backend": "heax-step_forge", "tool": "list_parts",
                                 "args": {"project_id": "p"}}]})
    gw = {"heaxstep_forge_list_parts": {"properties": {"project_id": {"type": "string"}}}}
    assert check_against_schemas(spec, gw, {("x", "y", "z"): {}}) == []


# ── 후보 검출 — 밀 뿐 등재하지 않는다 ────────────────────────────────────
def test_후보는_이름이_아니라_스키마_모양으로_민다():
    """이름 분류는 466개 중 113개를 못 갈랐다(§9-7). 신호는 **자유 페이로드 + 고르는 인자**다."""
    catalog = {
        "run_operation": {"inputSchema": {"properties": {
            "operation": {"type": "string"}, "args": {"type": "object"},
            "session_id": {"type": "string"}}}},
        "describe_operation": {"inputSchema": {"properties": {"operation": {"type": "string"}}}},
        "list_operations": {"inputSchema": {"properties": {}}},
        # 자유 페이로드가 없다 — 후보가 아니다
        "list_parts": {"inputSchema": {"properties": {"project_id": {"type": "string"},
                                                      "limit": {"type": "integer"}}}},
        # 짝(describe)이 없다 — 후보가 아니다
        "run_lonely": {"inputSchema": {"properties": {"kind": {"type": "string"},
                                                      "params": {"type": "object"}}}},
    }
    got = dispatch.detect_candidates(catalog)
    assert [c["tool"] for c in got] == ["run_operation"], got
    c = got[0]
    assert c["selector"] == "operation" and c["payload"] == "args"
    assert c["describe"] == "describe_operation" and c["list"] == "list_operations"


def test_속성_있는_object_는_자유_페이로드가_아니다():
    """`laminate` 처럼 속성이 적힌 object 를 자유 페이로드로 보면 엉뚱한 것을 2단으로 만든다."""
    catalog = {
        "run_thing": {"inputSchema": {"properties": {
            "kind": {"type": "string"},
            "cfg": {"type": "object", "properties": {"a": {"type": "string"}}}}}},
        "describe_thing": {"inputSchema": {"properties": {}}},
    }
    assert dispatch.detect_candidates(catalog) == []


# ── 목록 응답 모양이 앱마다 다르다 ───────────────────────────────────────
def test_앱마다_다른_목록_모양에서_이름을_골라_낸다():
    """DynaForge 는 `{name, category, summary}` 의 연속, SmartTwinMCP 는 `{hits: […]}`.
    모양을 하나로 가정하면 한쪽이 **조용히 빈 목록**이 된다."""
    from app.procedures.runner import _names_of

    dyna = [{"name": "matdb", "category": "material", "summary": "*MAT 카드를 갈아 끼운다"},
            {"name": "matswap", "category": "material", "summary": "물성 묶음 교체"}]
    assert [r["name"] for r in _names_of(dyna)] == ["matdb", "matswap"]
    assert _names_of(dyna)[0]["category"] == "material"

    stmc = {"total_tools": 44, "hits": [{"name": "echo", "summary": "Echo the message"}]}
    assert [r["name"] for r in _names_of(stmc)] == ["echo"]


def test_모르는_모양이면_빈_목록이다():
    """⚠ 지어내지 않는다 — 이름이 없는 것은 항목이 아니다."""
    from app.procedures.runner import _names_of

    assert _names_of("텍스트 한 덩이") == []
    assert _names_of({"뭔가": "다른 모양"}) == []
    assert _names_of([{"summary": "이름이 없다"}]) == []


def test_라우트가_부르는_실행기_메서드가_실제로_있다():
    """정적 계약 가드 — 이름 하나가 없으면 라우트를 안 쳐도 잡힌다(W-30 재발 방지)."""
    import re
    from pathlib import Path

    from app.procedures.runner import ProceduresRunner

    src = (Path(__file__).resolve().parents[1] / "app" / "procedures" / "routes.py"
           ).read_text(encoding="utf-8")
    called = sorted(set(re.findall(r"runner\.(\w+)\(", src)))
    assert {"dispatcher_items", "second_stage_one"} <= set(called), called
    missing = [c for c in called if not hasattr(ProceduresRunner, c)]
    assert not missing, f"라우트가 없는 메서드를 부른다: {missing}"


def test_이름이_run_으로_시작하지_않는_2단도_찾는다():
    """⚠ **점검에서 잡힌 구멍이다.** 접두만 보면 확정 등재된 `catalog_run` 을 못 찾는다 —
    검출기가 이미 아는 것도 못 미는 셈이다."""
    cat = {
        "catalog_run": {"inputSchema": {"properties": {
            "name": {"type": "string"}, "args": {"type": "object"}}}},
        "catalog_describe": {"inputSchema": {"properties": {"name": {"type": "string"}}}},
        "catalog_search": {"inputSchema": {"properties": {"query": {"type": "string"}}}},
    }
    got = dispatch.detect_candidates(cat)
    assert [c["tool"] for c in got] == ["catalog_run"], got
    assert got[0]["describe"] == "catalog_describe" and got[0]["list"] == "catalog_search"


def test_등록부에_확정된_것은_검출기도_밀_수_있어야_한다():
    """검출기가 **이미 확정된 것조차 못 밀면** 새 후보는 더 못 민다.
    ⚠ 어간이 다른 짝(`slurm_submit_job`↔`slurm_list_templates`)은 여전히 못 잡는다 —
    이름 규칙의 한계이고, 그래서 등재는 사람이 한다."""
    reg = dispatch.load()
    fake = {}
    for d in reg.values():
        fake[d.tool] = {"inputSchema": {"properties": {
            d.selector: {"type": "string"}, d.payload: {"type": "object"}}}}
        fake[d.describe] = {"inputSchema": {"properties": {}}}
        if d.list_tool:
            fake[d.list_tool] = {"inputSchema": {"properties": {}}}
    found = {c["tool"] for c in dispatch.detect_candidates(fake)}
    # 못 미는 것은 등록부에 `detector_finds: false` 로 **적혀 있어야** 한다.
    # 규칙을 늘려 전부 맞추는 대신, 못 민다는 사실을 데이터로 남기고 사람이 등재한다.
    should = {d.tool for d in reg.values() if d.detector_finds}
    known_miss = {d.tool for d in reg.values() if not d.detector_finds}
    assert not (should - found), f"민다고 적혀 있는데 못 민다: {sorted(should - found)}"
    assert not (known_miss & found), (
        f"못 민다고 적혀 있는데 민다: {sorted(known_miss & found)} — 등록부를 고쳐라")


# ── 실제로 돌려 본다 ──────────────────────────────────────────────────────
# ⚠ 여태 이 파일은 **메서드 이름이 있는지만** 봤다. 그 사이 `second_stage`·
# `second_stage_one`·`dispatcher_items` 셋 다 늘 빈 값을 냈다 — `GatewaySession.call`
# 이 튜플 `(isError, content[])` 인데 객체인 줄 알고 `getattr(res,"content")` 로
# 읽었기 때문이다. 없는 것과 못 받은 것이 같은 모양이라 아무도 몰랐다(2026-09-15).
def _runner_with(reply: dict):
    """게이트웨이를 MockTransport 로 세운 실행기 — `tools/call` 에 `reply` 를 준다."""
    import httpx

    from app.config import Settings
    from app.procedures.runner import ProceduresRunner

    def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content or b"{}") if req.content else {}
        if body.get("method") == "initialize":
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": {}},
                                  headers={"mcp-session-id": "t"})
        out = {"jsonrpc": "2.0", "id": 2, "result": {"isError": False, "content": [
            {"type": "text", "text": json.dumps(reply, ensure_ascii=False)}]}}
        return httpx.Response(200, text=f"data: {json.dumps(out)}\n\n",
                              headers={"content-type": "text/event-stream"})

    return ProceduresRunner(
        settings=Settings(gateway_shared_token="t"), store=None,
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=5.0),
        mint_pat=lambda p, run, ix: "pat")


class _P:
    subject, email, groups = "u1", "u1@corp.com", ["feat:procedures"]


def test_2단_계약을_실제로_받아_온다():
    spec = ProcedureSpec.model_validate({
        "title": "t", "vars": [],
        "steps": [{"backend": "heax-step_forge", "tool": "run_job",
                   "args": {"kind": "mesh", "params": {}}}]})
    got = asyncio.run(_runner_with(GUIDE_MESH).second_stage(_P(), spec))
    assert got, "계약을 못 받았다 — 빈 값은 '검사할 게 없다' 로 읽혀 검사가 통째로 꺼진다"
    sch = got[("heax-step_forge", "run_job", "mesh")]
    assert sch["properties"]["rebuild"]["type"] == "boolean"


def test_한_항목_계약과_목록도_실제로_받아_온다(reg):
    one = asyncio.run(_runner_with(GUIDE_MESH).second_stage_one(
        _P(), reg[("heax-step_forge", "run_job")], "mesh"))
    assert one and one["properties"]["rebuild"]["type"] == "boolean", \
        "None 이면 라우트가 '이름이 틀렸거나 앱이 안 붙어 있다' 는 **오진**을 낸다"

    items = asyncio.run(
        _runner_with({"operations": [{"name": "matdb", "summary": "물성 교체"}]})
        .dispatcher_items(_P(), reg[("heax-kooremapper_mcp", "run_operation")]))
    assert [i["name"] for i in items] == ["matdb"], "목록이 비면 '뒤에 아무것도 없다' 로 보인다"
