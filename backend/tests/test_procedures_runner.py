# 실행기 — invoke_tool 경유·isError 보존·save 체인·게이트·취소·시간(docs/procedures/PLAN.md §5-6·§5-10)
#
# 게이트웨이는 httpx.MockTransport 로 세운다(tests/test_access_control.py:134 선례).
# 프로토콜은 실물 그대로 — initialize → mcp-session-id → notifications/initialized →
# tools/call, 응답은 SSE `data:` 줄.
import asyncio
import json
import types

import httpx
import pytest

from app.config import Settings
from app.procedures.models import ProcedureSpec, Step, schema_fingerprint
from app.procedures.runner import ProceduresRunner, RunnerError
from app.procedures.store import ProceduresStore

PRINCIPAL = types.SimpleNamespace(subject="u1", email="u1@x.io", display_name="U",
                                  groups=["feat:procedures"])


def _sse(payload: dict) -> httpx.Response:
    """게이트웨이는 event-stream 으로 답한다 — 마지막 data: 줄이 정본이다."""
    body = f"event: message\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
    return httpx.Response(200, text=body,
                          headers={"content-type": "text/event-stream"})


class Gate:
    """가짜 게이트웨이. 부른 것을 전부 기록한다."""

    def __init__(self, tools=None, replies=None, fp=None):
        self.calls: list[dict] = []
        self.sessions: list[str] = []
        self.deleted: list[str] = []
        self.tools = tools or {}
        self.replies = replies or {}
        self.fp = fp or {}

    def transport(self) -> httpx.MockTransport:
        async def handler(req: httpx.Request) -> httpx.Response:
            if req.method == "DELETE":
                self.deleted.append(req.headers.get("mcp-session-id", ""))
                return httpx.Response(200)
            body = json.loads(req.content)
            m = body.get("method")
            if m == "initialize":
                sid = f"s{len(self.sessions) + 1}"
                self.sessions.append(sid)
                return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": {}},
                                      headers={"mcp-session-id": sid})
            if m == "notifications/initialized":
                return httpx.Response(200)
            if m == "tools/list":
                return _sse({"jsonrpc": "2.0", "id": 3, "result": {"tools": [
                    {"name": n, "description": d.get("description", ""),
                     "inputSchema": d.get("inputSchema", {})}
                    for n, d in self.tools.items()]}})
            if m == "tools/call":
                p = body["params"]
                self.calls.append({"name": p["name"], "arguments": p["arguments"],
                                   "pat": req.headers.get("authorization", ""),
                                   "sid": req.headers.get("mcp-session-id", "")})
                inner = p["arguments"].get("name") if p["name"] == "invoke_tool" else p["name"]
                r = self.replies.get(inner)
                if callable(r):
                    r = r(p["arguments"].get("arguments") or {})
                if isinstance(r, Exception):
                    raise r
                if r is None:
                    r = {"content": [{"type": "text", "text": "{}"}], "isError": False}
                return _sse({"jsonrpc": "2.0", "id": 2, "result": r})
            return httpx.Response(400)

        return httpx.MockTransport(handler)


def ok(obj) -> dict:
    return {"content": [{"type": "text", "text": json.dumps(obj, ensure_ascii=False)}],
            "isError": False}


def err(text: str) -> dict:
    return {"content": [{"type": "text", "text": text}], "isError": True}


@pytest.fixture
def kit(tmp_path):
    s = Settings(procedures_store_path=str(tmp_path / "wb.sqlite"))
    store = ProceduresStore(s)

    def build(gate: Gate, **kw):
        client = httpx.AsyncClient(transport=gate.transport(), timeout=5.0)
        return ProceduresRunner(settings=s, store=store, client=client,
                               mint_pat=lambda p, run, ix: f"pat-{run}-{ix}", **kw)

    yield store, build
    store.close()


def _spec(steps, title="t"):
    return ProcedureSpec(title=title, steps=[Step(**x) for x in steps])


def _run(store, spec, mode="live", inputs=None):
    return store.create_run(owner_sub="u1", mode=mode, inputs=inputs or {})


# ── invoke_tool 경유 ─────────────────────────────────────────────────────
def test_calls_go_through_invoke_tool_with_the_alias(kit):
    """직접 tools/call 하면 게이트웨이의 파괴 도구 관문을 **지나지 않는다**."""
    async def go(store, build):
        g = Gate(tools={"heaxstep_forge_list_parts": {}},
                 replies={"heaxstep_forge_list_parts": ok({"parts": [1]})})
        r = build(g)
        spec = _spec([{"backend": "heax-step_forge", "tool": "list_parts",
                       "args": {"project_id": "p"}}])
        rid = _run(store, spec)
        out = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        assert out["state"] == "done"
        c = g.calls[0]
        assert c["name"] == "invoke_tool"
        assert c["arguments"] == {"name": "heaxstep_forge_list_parts",
                                  "arguments": {"project_id": "p"}}
    asyncio.run(go(*kit))


def test_one_session_per_run_and_it_is_closed(kit):
    """mcp_call 은 호출마다 세션을 만들고 안 닫는다 — 챗과 공유하는 게이트웨이에 쌓인다."""
    async def go(store, build):
        g = Gate(tools={"b_a": {}, "b_c": {}}, replies={"b_a": ok({}), "b_c": ok({})})
        r = build(g)
        spec = _spec([{"backend": "b", "tool": "a"}, {"backend": "b", "tool": "c"}])
        rid = _run(store, spec)
        await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        assert len(g.sessions) == 1                  # 실행당 하나
        assert {c["sid"] for c in g.calls} == {"s1"}  # 두 단계가 같은 세션
        assert g.deleted == ["s1"]                    # finally 에서 닫힌다
    asyncio.run(go(*kit))


def test_pat_is_minted_per_step_not_once(kit):
    """exp 가 창 시작+60분이라 오래 멈춘 실행이 저장된 토큰으로 재개하면 401 이다."""
    async def go(store, build):
        g = Gate(tools={"b_a": {}, "b_c": {}}, replies={"b_a": ok({}), "b_c": ok({})})
        r = build(g)
        spec = _spec([{"backend": "b", "tool": "a"}, {"backend": "b", "tool": "c"}])
        rid = _run(store, spec)
        await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        pats = [c["pat"] for c in g.calls]
        assert pats[0] != pats[1]
        assert pats[0].endswith("-0") and pats[1].endswith("-1")
    asyncio.run(go(*kit))


# ── 판정이 실행기에 걸려 있나 ──────────────────────────────────────────
def test_is_error_stops_the_run_and_save_does_not_happen(kit):
    async def go(store, build):
        g = Gate(tools={"b_a": {}, "b_c": {}},
                 replies={"b_a": err("unknown tool: a"), "b_c": ok({})})
        r = build(g)
        spec = _spec([{"backend": "b", "tool": "a", "save": {"x": "v"}},
                      {"backend": "b", "tool": "c", "args": {"x": "{{x}}"}}])
        rid = _run(store, spec)
        out = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        assert out["state"] == "failed" and out["kind"] == "unknown_tool"
        assert len(g.calls) == 1                       # 두 번째 단계는 안 돈다
        steps = store.list_steps(rid)
        assert steps[0]["state"] == "failed" and steps[0]["ok"] == 0
        assert "unknown tool" in steps[0]["error"]
    asyncio.run(go(*kit))


def test_app_envelope_failure_stops_even_though_is_error_is_false(kit):
    """실측 — predict_sed 에 미지 키가 섞이면 E100 봉투가 isError=false 로 온다."""
    async def go(store, build):
        env = {"content": [{"type": "text", "text": json.dumps(
            {"ok": False, "data": None,
             "errors": [{"code": "E100", "field": "sample",
                         "message": "extra fields not permitted: layer"}]})}],
            "isError": False}
        g = Gate(tools={"heaxthermal_shock_mcp_predict_sed": {}},
                 replies={"heaxthermal_shock_mcp_predict_sed": env})
        r = build(g)
        spec = _spec([{"backend": "heax-thermal_shock_mcp", "tool": "predict_sed",
                       "save": {"sed": "data.sed_pred"}}])
        rid = _run(store, spec)
        out = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        assert out["state"] == "failed" and out["kind"] == "app_envelope"
        assert "E100" in store.list_steps(rid)[0]["error"]
    asyncio.run(go(*kit))


def test_empty_save_value_stops_the_chain(kit):
    """RA 는 0행 표를 오류 없이 만든다 — 빈 값을 다음 단계에 넘기지 않는다."""
    async def go(store, build):
        g = Gate(tools={"b_a": {}, "b_c": {}},
                 replies={"b_a": ok({"parts": []}), "b_c": ok({})})
        r = build(g)
        spec = _spec([{"backend": "b", "tool": "a", "save": {"parts": "parts"}},
                      {"backend": "b", "tool": "c", "args": {"rows": "{{parts}}"}}])
        rid = _run(store, spec)
        out = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        assert out["state"] == "failed" and out["kind"] == "save_empty"
        assert len(g.calls) == 1
    asyncio.run(go(*kit))


def test_save_feeds_next_step_with_type_preserved(kit):
    """R1 의 체인 그 자체 — equivalent_loads 를 형 그대로 넘긴다."""
    async def go(store, build):
        loads = {"N": [1.0, 0, 0], "M": [2.5, 0, 0]}
        g = Gate(tools={"heaxlaminate_analyzer_mcp_solve_prescribed_curvature": {},
                        "heaxlaminate_analyzer_mcp_recover_ply_stresses": {}},
                 replies={"heaxlaminate_analyzer_mcp_solve_prescribed_curvature":
                          ok({"equivalent_loads": loads}),
                          "heaxlaminate_analyzer_mcp_recover_ply_stresses":
                          ok({"min_tsai_wu_R": 1.8})})
        r = build(g)
        spec = _spec([
            {"backend": "heax-laminate_analyzer_mcp", "tool": "solve_prescribed_curvature",
             "args": {"bend_radius": "{{r_min}}"}, "save": {"loads": "equivalent_loads"}},
            {"backend": "heax-laminate_analyzer_mcp", "tool": "recover_ply_stresses",
             "args": {"loads": "{{loads}}"}}])
        rid = _run(store, spec, inputs={"r_min": 50.0})
        out = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        assert out["state"] == "done"
        assert g.calls[0]["arguments"]["arguments"] == {"bend_radius": 50.0}
        assert g.calls[1]["arguments"]["arguments"] == {"loads": loads}  # dict 그대로
    asyncio.run(go(*kit))


def test_all_content_blocks_are_recorded(kit):
    async def go(store, build):
        many = {"content": [{"type": "text", "text": json.dumps({"i": i})}
                            for i in range(3)], "isError": False}
        g = Gate(tools={"b_a": {}}, replies={"b_a": many})
        r = build(g)
        spec = _spec([{"backend": "b", "tool": "a", "raw": True}])
        rid = _run(store, spec)
        await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        assert store.step_result(rid, 0).count("\n") == 2
    asyncio.run(go(*kit))


def test_warnings_reach_notes(kit):
    async def go(store, build):
        g = Gate(tools={"b_a": {}},
                 replies={"b_a": ok({"life_cycles": 1, "warnings": ["W120: ply 3 제외"]})})
        r = build(g)
        spec = _spec([{"backend": "b", "tool": "a"}])
        rid = _run(store, spec)
        await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        n = store.list_steps(rid)[0]["notes"]
        assert "W120" in n["warnings"][0]
        assert n["judge"] == {"layer": "envelope", "kind": "ok", "retriable": False}
    asyncio.run(go(*kit))


# ── 게이트 ───────────────────────────────────────────────────────────────
def test_gate_stops_before_calling_and_holds_no_slot(kit):
    async def go(store, build):
        g = Gate(tools={"reportarchive_publish_report": {}})
        r = build(g)
        spec = _spec([{"backend": "reportarchive", "tool": "publish_report",
                       "gate": "human", "args": {"id": 1}}])
        rid = _run(store, spec)
        out = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        assert out["state"] == "gated" and out["stopped_at"] == 0
        assert g.calls == []                                   # 부르지 않았다
        assert store.get_run(rid)["state"] == "gated"
        assert r.sem._value == int(r.settings.procedures_concurrency)  # 슬롯을 놓았다
    asyncio.run(go(*kit))


def test_gate_ack_lets_it_through_and_stale_ack_does_not(kit):
    """승인은 (run, step, 치환된 인자 sha256) 에 묶인 1회용이다."""
    async def go(store, build):
        g = Gate(tools={"reportarchive_publish_report": {}},
                 replies={"reportarchive_publish_report": ok({"published": True})})
        r = build(g)
        spec = _spec([{"backend": "reportarchive", "tool": "publish_report",
                       "gate": "human", "args": {"id": "{{rid}}"}}])
        rid = _run(store, spec, inputs={"rid": "R-1"})
        out = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        assert out["state"] == "gated"

        # 다른 인자로 받은 승인은 안 통한다
        store.ack_gate(rid, 0, by="u1", args_sha256="deadbeef")
        assert (await r.run(run_id=rid, spec=spec, principal=PRINCIPAL))["state"] == "gated"
        assert g.calls == []

        store.ack_gate(rid, 0, by="u1", args_sha256=out["args_sha256"])
        out2 = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        assert out2["state"] == "done" and len(g.calls) == 1
    asyncio.run(go(*kit))


# ── 취소·소유자 ──────────────────────────────────────────────────────────
def test_cancel_is_seen_at_the_step_boundary(kit):
    async def go(store, build):
        seen = []

        def slow(args):
            seen.append(1)
            return ok({"n": len(seen)})

        g = Gate(tools={"b_a": {}, "b_c": {}}, replies={"b_a": slow, "b_c": slow})
        r = build(g)
        spec = _spec([{"backend": "b", "tool": "a"}, {"backend": "b", "tool": "c"}])
        rid = _run(store, spec)

        real = store.get_run

        def patched(run_id, **kw):          # 1단계 뒤에 사람이 취소를 눌렀다
            d = real(run_id, **kw)
            if d and len(seen) == 1 and d["state"] == "running":
                store.cancel_run(run_id, "u1")
                return real(run_id, **kw)
            return d

        store.get_run = patched
        out = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        store.get_run = real
        await r.aclose()
        assert out["state"] == "cancelled" and len(g.calls) == 1
        assert real(rid)["cancelled_by"] == "u1"
    asyncio.run(go(*kit))


def test_inactive_owner_stops_before_minting_a_pat(kit):
    async def go(store, build):
        g = Gate(tools={"b_a": {}}, replies={"b_a": ok({})})
        r = build(g, is_active=lambda _e: False)
        spec = _spec([{"backend": "b", "tool": "a"}])
        rid = _run(store, spec)
        out = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        assert out["state"] == "failed" and out["stage"] == "owner_inactive"
        assert g.calls == []
    asyncio.run(go(*kit))


# ── 시간 ─────────────────────────────────────────────────────────────────
def test_timeout_is_unknown_not_failed(kit):
    """쓰기가 뒤늦게 완료됐을 수 있다 — 재실행 전에 사람이 본다."""
    async def go(store, build):
        g = Gate(tools={"b_create_thing": {}},
                 replies={"b_create_thing": httpx.ReadTimeout("느리다")})
        r = build(g)
        spec = _spec([{"backend": "b", "tool": "create_thing"}])
        rid = _run(store, spec)
        out = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        assert out["state"] == "failed"          # 실행은 멈춘다
        st = store.list_steps(rid)[0]
        assert st["state"] == "unknown" and st["stage"] == "timeout"   # 단계는 unknown
        assert "실행 여부를 모른다" in st["error"]
    asyncio.run(go(*kit))


def test_warmup_discards_result_and_survives_timeout(kit):
    """카탈로그 검색은 세션 첫 호출에 120.3초다 — 한 번 버리는 호출이 그걸 흡수한다."""
    async def go(store, build):
        g = Gate(tools={"b_search_catalog_property": {}, "b_use_it": {}},
                 replies={"b_search_catalog_property": httpx.ReadTimeout("콜드스타트"),
                          "b_use_it": ok({"found": 1})})
        r = build(g)
        spec = _spec([{"backend": "b", "tool": "search_catalog_property", "warmup": True},
                      {"backend": "b", "tool": "use_it"}])
        rid = _run(store, spec)
        out = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        assert out["state"] == "done"                  # 워밍업 타임아웃은 실패가 아니다
        assert [s["ix"] for s in store.list_steps(rid)] == [1]  # 기록도 안 남긴다
    asyncio.run(go(*kit))


def test_slow_steps_serialise_per_backend(kit):
    """느린 단계 중 같은 백엔드를 또 치면 재연결이 다른 실행까지 끊는다."""
    async def go(store, build):
        g = Gate(tools={"b_a": {}}, replies={"b_a": ok({})})
        r = build(g)
        assert r._blk("b") is r._blk("b") and r._blk("b") is not r._blk("c")
        await r.aclose()
    asyncio.run(go(*kit))


# ── 계획 모드 ────────────────────────────────────────────────────────────
def test_plan_mode_never_touches_the_gateway(kit):
    async def go(store, build):
        g = Gate()
        r = build(g)
        spec = _spec([{"backend": "b", "tool": "a", "args": {"x": "{{v}}"},
                       "save": {"y": "out"}},
                      {"backend": "b", "tool": "c", "args": {"z": "{{y}}"}}])
        rid = _run(store, spec, mode="plan", inputs={"v": 7})
        out = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        assert g.calls == [] and g.sessions == []
        assert out["state"] == "done" and out["stage"] == "plan"
        assert out["calls"][0]["args"] == {"x": 7}
        # 앞 단계 save 에 기대는 인자는 '미검증' 으로 표시한다
        assert out["calls"][1]["unverified"] is True
    asyncio.run(go(*kit))


# ── 스키마 드리프트 ──────────────────────────────────────────────────────
def test_schema_drift_stops_before_any_step(kit):
    """도구에 판본이 없으니 변화를 잡아 멈추는 것까지가 할 수 있는 전부다."""
    async def go(store, build):
        g = Gate(tools={"b_a": {"description": "새 설명", "inputSchema": {"x": 1}}},
                 replies={"b_a": ok({})})
        r = build(g)
        spec = _spec([{"backend": "b", "tool": "a",
                       "schema_fp": schema_fingerprint("옛 설명", {"x": 1})}])
        rid = _run(store, spec)
        out = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        assert out["state"] == "failed" and out["stage"] == "schema_drift"
        assert "스키마가 바뀌었다" in out["detail"][0]
        assert g.calls == []
    asyncio.run(go(*kit))


def test_matching_fingerprint_proceeds(kit):
    async def go(store, build):
        desc, sch = "설명", {"properties": {"x": {}}}
        g = Gate(tools={"b_a": {"description": desc, "inputSchema": sch}},
                 replies={"b_a": ok({})})
        r = build(g)
        spec = _spec([{"backend": "b", "tool": "a",
                       "schema_fp": schema_fingerprint(desc, sch)}])
        rid = _run(store, spec)
        out = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        assert out["state"] == "done"
    asyncio.run(go(*kit))


def test_missing_tool_is_caught_up_front(kit):
    async def go(store, build):
        g = Gate(tools={})
        r = build(g)
        spec = _spec([{"backend": "odb-hub", "tool": "odb_list_components"}])
        rid = _run(store, spec)
        out = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        assert out["state"] == "failed" and "게이트웨이에 없다" in out["detail"][0]
    asyncio.run(go(*kit))


# ── 재개 ─────────────────────────────────────────────────────────────────
def test_resume_starts_after_the_done_steps(kit):
    """done 은 절대 재실행하지 않는다 — 비멱등 쓰기가 두 번 난다."""
    async def go(store, build):
        g = Gate(tools={"b_a": {}, "b_c": {}}, replies={"b_a": ok({}), "b_c": ok({})})
        r = build(g)
        spec = _spec([{"backend": "b", "tool": "a"}, {"backend": "b", "tool": "c"}])
        rid = _run(store, spec)
        out = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL, start_at=1)
        await r.aclose()
        assert out["state"] == "done"
        assert [c["arguments"]["name"] for c in g.calls] == ["b_c"]
    asyncio.run(go(*kit))




# ── 빈 실행에 단계 하나(진입점) ─────────────────────────────────────────
def test_step_once_appends_and_feeds_the_next_step(kit):
    """뽑은 값이 실행 입력에 합쳐져 **다음 단계가 {{key}} 로 쓴다** — 진입점의 핵심."""
    async def go(store, build):
        g = Gate(tools={"b_first": {}, "b_second": {}},
                 replies={"b_first": ok({"project": {"id": "P-1"}}),
                          "b_second": ok({"done": True})})
        r = build(g)
        rid = store.create_run(owner_sub="u1", mode="live")

        out = await r.step_once(run_id=rid, principal=PRINCIPAL,
                                step=Step(backend="b", tool="first",
                                          save={"pid": "project.id"}))
        assert out["ok"] is True and out["ix"] == 0 and out["saved"] == {"pid": "P-1"}
        assert store.get_run(rid)["inputs"]["pid"] == "P-1", "다음 단계가 못 쓴다"

        out2 = await r.step_once(run_id=rid, principal=PRINCIPAL,
                                 step=Step(backend="b", tool="second",
                                           args={"project_id": "{{pid}}"}))
        await r.aclose()
        assert out2["ok"] is True and out2["ix"] == 1
        assert g.calls[1]["arguments"]["arguments"] == {"project_id": "P-1"}
    asyncio.run(go(*kit))


def test_step_once_opens_and_closes_its_own_session(kit):
    async def go(store, build):
        g = Gate(tools={"b_a": {}}, replies={"b_a": ok({})})
        r = build(g)
        rid = store.create_run(owner_sub="u1", mode="live")
        await r.step_once(run_id=rid, principal=PRINCIPAL, step=Step(backend="b", tool="a"))
        await r.aclose()
        assert len(g.sessions) == 1 and g.deleted == ["s1"]
    asyncio.run(go(*kit))


def test_step_once_refuses_while_another_step_runs(kit):
    """같은 단계 재실행 방지 — 라우트의 409 와 같은 판정을 실행기도 한다."""
    async def go(store, build):
        g = Gate(tools={"b_a": {}}, replies={"b_a": ok({})})
        r = build(g)
        rid = store.create_run(owner_sub="u1", mode="live")
        store.begin_step(rid, 0, backend="b", tool="a", args={})
        with pytest.raises(RunnerError):
            await r.step_once(run_id=rid, principal=PRINCIPAL, step=Step(backend="b", tool="a"))
        await r.aclose()
        assert g.calls == []
    asyncio.run(go(*kit))


def test_step_once_failure_marks_the_run(kit):
    async def go(store, build):
        g = Gate(tools={"b_a": {}}, replies={"b_a": err("unknown tool: a")})
        r = build(g)
        rid = store.create_run(owner_sub="u1", mode="live")
        out = await r.step_once(run_id=rid, principal=PRINCIPAL, step=Step(backend="b", tool="a"))
        await r.aclose()
        assert out["ok"] is False and out["kind"] == "unknown_tool"
        assert store.get_run(rid)["state"] == "failed"
    asyncio.run(go(*kit))


def test_catalog_lists_tools_and_closes_the_session(kit):
    """화면이 처음 부르는 것 — 권한 필터는 tools/list 쪽이 정본이다."""
    async def go(store, build):
        g = Gate(tools={"b_a": {"description": "설명", "inputSchema": {"x": 1}}})
        r = build(g)
        cat = await r.catalog(PRINCIPAL)
        await r.aclose()
        assert set(cat) == {"b_a"} and cat["b_a"]["description"] == "설명"
        assert g.deleted == ["s1"], "카탈로그 조회도 세션을 닫아야 한다"
    asyncio.run(go(*kit))
