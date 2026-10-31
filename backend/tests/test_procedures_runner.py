# 실행기 — invoke_tool 경유·isError 보존·save 체인·게이트·취소·시간(docs/procedures/PLAN.md §5-6·§5-10)
#
# 게이트웨이는 httpx.MockTransport 로 세운다(tests/test_access_control.py:134 선례).
# 프로토콜은 실물 그대로 — initialize → mcp-session-id → notifications/initialized →
# tools/call, 응답은 SSE `data:` 줄.
import asyncio
import gzip
import hashlib
import json
import sqlite3
import time
import types

import httpx
import pytest

from app.config import Settings
from app.procedures.models import ProcedureSpec, Step, Var, schema_fingerprint
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
# 되돌리기 어려운 도구 일반의 게이트다. 게시(publish_report)는 게이트 **전에** 미리보기를 부르는 따로 길이 있다 —
# 아래 '게시 2단 확인' 절(남은 일 B3).
def test_gate_stops_before_calling_and_holds_no_slot(kit):
    async def go(store, build):
        g = Gate(tools={"reportarchive_trash_report": {}})
        r = build(g)
        spec = _spec([{"backend": "reportarchive", "tool": "trash_report",
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
        g = Gate(tools={"reportarchive_trash_report": {}},
                 replies={"reportarchive_trash_report": ok({"trashed": True})})
        r = build(g)
        spec = _spec([{"backend": "reportarchive", "tool": "trash_report",
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


# ── 게시 2단 확인(RA preview_publish → publish_report — PLAN §5-4 · 남은 일 B3) ──────────────────────
# 가짜 RA 는 실물 꼴이다 — `mounts/routes.py` preview_mount 의 data 를 MCP `_unwrap` 이 벗기고 FastMCP 가 들여쓴 JSON 글
# 하나로 낸다(mcp 1.28 은 `-> dict` 에 outputSchema 가 없어 structuredContent 도 없다). 실패도 isError=false 의 `{error}`
# 봉투다. 토큰은 미리보기마다 새로 나오고 (사용자, 보고서, 게시판 집합)에 묶인다(`mounts/confirm.py` — `<만료초>.<서명>`).
# 막힌 게시판이 하나라도 있으면 실물 게시는 커밋 없이 통째로 거절된다(`services.mount_report`) — 가짜도 그렇다.
RA_PREVIEW_SCHEMA = {"properties": {"report_id": {"title": "Report Id", "type": "integer"},
                                    "boards": {"items": {}, "title": "Boards", "type": "array"}},
                     "required": ["report_id", "boards"], "title": "preview_publishArguments", "type": "object"}
BOARDS = {"dept-a": {"name": "가 부서", "parent_slug": "div-x", "audience": 12},
          "dept-b": {"name": "나 부서", "parent_slug": "div-x", "audience": 30, "descendant_boards": 2}}
BLOCKED = "이 게시판에 게시할 권한이 없습니다."


def _ra(obj) -> dict:
    """RA MCP 의 도구 결과 꼴 — 들여쓴 JSON 글 하나, isError 는 false."""
    return {"content": [{"type": "text", "text": json.dumps(obj, ensure_ascii=False, indent=2)}], "isError": False}


class FakeRA:
    """RA 의 게시 두 도구. 미리보기 · 게시를 따로 센다."""

    def __init__(self, boards: dict, title: str = "낙하 해석 보고서"):
        self.boards = boards
        self.title = title
        self.issued: list[tuple] = []      # (토큰, 보고서, 게시판 집합)
        self.previews: list[dict] = []
        self.published: list[dict] = []

    def gate(self) -> "Gate":
        from tests.test_procedures_contract import RA_PUBLISH_SCHEMA
        return Gate(tools={"reportarchive_preview_publish": {"inputSchema": RA_PREVIEW_SCHEMA},
                           "reportarchive_publish_report": {"inputSchema": RA_PUBLISH_SCHEMA}},
                    replies={"reportarchive_preview_publish": self.preview,
                             "reportarchive_publish_report": self.publish})

    def preview(self, a: dict) -> dict:
        self.previews.append(dict(a))
        targets = []
        for slug in a["boards"]:
            b = self.boards.get(slug)
            if b is None:
                targets.append({"slug": slug, "error": "게시판을 찾을 수 없습니다."})
                continue
            targets.append({"slug": slug, "name": b["name"], "parent_slug": b.get("parent_slug"),
                            "audience": b["audience"], "descendant_boards": b.get("descendant_boards", 0),
                            "already_mounted": b.get("already_mounted", False), "blocked": b.get("blocked")})
        token = None
        if any(not t.get("blocked") and not t.get("error") for t in targets):
            exp = 1793406421 + len(self.issued)
            raw = f"7:{a['report_id']}:{','.join(sorted(a['boards']))}:{exp}"
            token = f"{exp}.{hashlib.sha256(raw.encode()).hexdigest()[:43]}"
            self.issued.append((token, a["report_id"], tuple(sorted(a["boards"]))))
        return _ra({"report_id": a["report_id"], "title": self.title, "targets": targets, "confirm_token": token,
                    "note": "실제로 게시되지 않았습니다. 사용자에게 대상 게시판을 확인받은 뒤 confirm_token 과 함께 게시하세요."})

    def publish(self, a: dict) -> dict:
        tok = a.get("confirm_token")
        if not tok or "." not in tok:
            return _ra({"error": "게시 전에 미리보기가 필요합니다 — POST /api/mounts/preview 로 어디에 게시되는지 "
                                 "확인한 뒤 받은 confirm_token 을 함께 보내세요."})
        if (tok, a["report_id"], tuple(sorted(a["boards"]))) not in self.issued:
            return _ra({"error": "확인 토큰이 이 요청과 맞지 않습니다(보고서·게시판이 미리보기와 다름). "
                                 "게시할 대상 그대로 미리보기를 다시 받으세요."})
        new = [s for s in a["boards"] if not self.boards.get(s, {}).get("already_mounted")]
        bad = [s for s in new if s not in self.boards or self.boards[s].get("blocked")]
        if bad:
            return _ra({"error": f"{BLOCKED[:-1]}: {bad[0]}"})
        self.published.append(dict(a))
        return _ra({"items": [{"report_id": a["report_id"], "workspace_slug": s, "edit_policy": "default",
                               "mounted_by_user_id": 7, "via": "mcp", "mounted_at": "2026-10-31T09:00:00",
                               "note": a.get("note", ""), "can_unmount": None, "takedown_pending": None,
                               "folder_ids": [], "folder_id": None, "workspace_name": None, "folder_name": None,
                               "folder_names": []} for s in new]})


def _publish_spec(boards=("dept-a", "dept-b")) -> ProcedureSpec:
    return ProcedureSpec(title="게시", vars=[Var(key="report_id", label="보고서", type="number")], steps=[
        Step(backend="reportarchive", tool="publish_report", gate="human",
             args={"report_id": "{{report_id}}", "boards": list(boards), "note": "절차가 올린다"})])


def _inner(g: "Gate", alias: str) -> list[dict]:
    """그 도구로 나간 인자들(invoke_tool 안쪽)."""
    return [c["arguments"]["arguments"] for c in g.calls if c["arguments"].get("name") == alias]


def _ledger_cells(path: str) -> list[str]:
    """원장 sqlite 의 모든 표 · 모든 칸을 글로(gzip 결과는 풀어서)."""
    con = sqlite3.connect(path)
    try:
        out = []
        for (table,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
            for row in con.execute(f'SELECT * FROM "{table}"'):
                for v in row:
                    if isinstance(v, bytes):
                        try:
                            v = gzip.decompress(v).decode("utf-8")
                        except OSError:
                            v = v.decode("utf-8", "replace")
                    if v is not None:
                        out.append(str(v))
        return out
    finally:
        con.close()


async def _gated_then_acked(store, r, spec, inputs=None) -> tuple[str, dict]:
    """게이트까지 돌리고 사람이 그 카드를 승인한다 — 승인은 화면이 보낸 그 행의 지문이다."""
    rid = _run(store, spec, inputs=inputs or {"report_id": 41})
    out = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
    assert out["state"] == "gated", out
    assert out["args_sha256"] == store.list_steps(rid)[0]["args_sha256"]
    store.ack_gate(rid, 0, by="u1", args_sha256=out["args_sha256"])
    return rid, out


def test_게시_단계는_게이트_전에_미리보기를_카드에_싣는다(kit):
    """① 대상 · 볼 사람 수 · 못 올리는 사유(RA 미리보기 그대로)를 게이트 카드에 — 게시는 부르지 않는다."""
    async def go(store, build):
        ra = FakeRA({**BOARDS, "dept-b": {**BOARDS["dept-b"], "blocked": BLOCKED}})
        g = ra.gate()
        r = build(g)
        spec = _publish_spec()
        rid = _run(store, spec, inputs={"report_id": 41})
        out = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        assert out["state"] == "gated" and out["stopped_at"] == 0, out
        assert _inner(g, "reportarchive_preview_publish") == [{"report_id": 41, "boards": ["dept-a", "dept-b"]}]
        assert _inner(g, "reportarchive_publish_report") == [] and ra.published == []
        st = store.list_steps(rid)[0]
        assert (st["state"], st["stage"]) == ("pending", "gate")
        assert st["args"] == {"report_id": 41, "boards": ["dept-a", "dept-b"], "note": "절차가 올린다"}
        pv = st["notes"]["publish_preview"]
        assert (pv["report_id"], pv["title"]) == (41, "낙하 해석 보고서")
        assert [(t["slug"], t["name"], t["audience"], t["descendant_boards"], t["blocked"]) for t in pv["targets"]] == [
            ("dept-a", "가 부서", 12, 0, None), ("dept-b", "나 부서", 30, 2, BLOCKED)]
        assert st["notes"]["publish_blocked"] == [f"dept-b: {BLOCKED}"]
        assert ra.issued[0][0] not in json.dumps(st, ensure_ascii=False), "카드 · 지문에 토큰이 실렸다"
        assert store.get_run(rid)["state"] == "gated"
        assert r.sem._value == int(r.settings.procedures_concurrency)   # 슬롯을 놓았다
    asyncio.run(go(*kit))


def test_승인_뒤_미리보기가_달라지면_게시하지_않고_차이를_보이며_다시_멈춘다(kit):
    """② 다르면 게시 0회 — 사람이 본 대상과 지금의 대상이 다르다. 새 미리보기를 승인하면 그때 간다."""
    async def go(store, build):
        ra = FakeRA(dict(BOARDS))
        g = ra.gate()
        r = build(g)
        spec = _publish_spec()
        rid, out = await _gated_then_acked(store, r, spec)

        ra.boards["dept-b"] = {**BOARDS["dept-b"], "audience": 340}    # 승인 뒤 볼 사람이 늘었다(상위 조직이 붙었다)
        out2 = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        assert out2["state"] == "gated" and out2["stopped_at"] == 0, out2
        assert _inner(g, "reportarchive_publish_report") == [] and ra.published == []
        st = store.list_steps(rid)[0]
        assert (st["state"], st["stage"]) == ("pending", "gate")
        assert st["notes"]["publish_changed"] == ["dept-b 볼 수 있는 사람: 30 → 340"]
        assert st["notes"]["publish_preview"]["targets"][1]["audience"] == 340
        assert st["args_sha256"] != out["args_sha256"], "옛 승인이 새 미리보기에 통한다"

        store.ack_gate(rid, 0, by="u1", args_sha256=st["args_sha256"])   # 새 카드를 승인하면 그때 간다
        out3 = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        assert out3["state"] == "done", out3
        assert len(ra.published) == 1 and len(ra.previews) == 3
    asyncio.run(go(*kit))


def test_승인_뒤_미리보기가_같으면_그때_받은_토큰으로_한_번_게시한다(kit):
    """② 같으면 1회 — 두 번째 미리보기의 토큰으로 곧바로(사람 대기가 사이에 없어 토큰 수명 600초에 안 걸린다)."""
    async def go(store, build):
        ra = FakeRA(dict(BOARDS))
        g = ra.gate()
        r = build(g)
        spec = _publish_spec()
        rid, _ = await _gated_then_acked(store, r, spec)
        out2 = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        assert out2["state"] == "done", out2
        assert [c["arguments"]["name"] for c in g.calls] == [
            "reportarchive_preview_publish", "reportarchive_preview_publish", "reportarchive_publish_report"]
        assert _inner(g, "reportarchive_publish_report") == [
            {"report_id": 41, "boards": ["dept-a", "dept-b"], "note": "절차가 올린다",
             "confirm_token": ra.issued[1][0]}], "두 번째 미리보기의 토큰이 아니다"
        assert len(ra.published) == 1
        st = store.list_steps(rid)[0]
        assert (st["state"], st["ok"]) == ("done", 1)
        assert st["args"] == {"report_id": 41, "boards": ["dept-a", "dept-b"], "note": "절차가 올린다"}
        assert [t["slug"] for t in st["notes"]["publish_preview"]["targets"]] == ["dept-a", "dept-b"]
        assert [m["workspace_slug"] for m in json.loads(store.step_result(rid, 0))["items"]] == ["dept-a", "dept-b"]
    asyncio.run(go(*kit))


def test_원장_어디에도_확인_토큰이_남지_않는다(kit):
    """③ 실행 입력 · 단계 인자 · 노트 · 결과 · 승인 지문 — sqlite 의 모든 칸을 글로 풀어 본다."""
    async def go(store, build):
        ra = FakeRA(dict(BOARDS))
        r = build(ra.gate())
        spec = _publish_spec()
        rid, out = await _gated_then_acked(store, r, spec)
        assert (await r.run(run_id=rid, spec=spec, principal=PRINCIPAL))["state"] == "done"
        await r.aclose()
        toks = [t for t, _, _ in ra.issued]
        assert len(toks) == 2 and len(ra.published) == 1
        cells = _ledger_cells(store.health()["path"])
        assert any("dept-a" in c for c in cells), "원장을 못 읽었다"
        assert [c for c in cells for t in toks if t in c or t.split(".")[1] in c] == []
        # 승인 지문은 토큰과 무관하다 — 미리보기마다 토큰이 바뀌어도 같은 대상이면 같은 지문이다
        assert store.gate_ack(rid, 0)["args_sha256"] == out["args_sha256"] == store.list_steps(rid)[0]["args_sha256"]
    asyncio.run(go(*kit))


def test_게시_응답에_되비친_토큰도_원장에_남지_않는다(kit):
    """pydantic 의 '칸 없음' 오류는 받은 인자를 통째로 되비친다(input_value={…}) — 결과 · 오류 글에서 가린다."""
    async def go(store, build):
        ra = FakeRA(dict(BOARDS))
        g = ra.gate()
        g.replies["reportarchive_publish_report"] = lambda a: err(
            "Error executing tool publish_report: 1 validation error for publish_reportArguments\n"
            f"boards\n  Field required [type=missing, input_value={a!r}, input_type=dict]")
        r = build(g)
        spec = _publish_spec()
        rid, _ = await _gated_then_acked(store, r, spec)
        out2 = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        assert out2["state"] == "failed", out2
        tok = ra.issued[1][0]
        assert _inner(g, "reportarchive_publish_report")[0]["confirm_token"] == tok     # 나가기는 했다
        assert [c for c in _ledger_cells(store.health()["path"]) if tok in c] == []
        assert "[가림:confirm_token]" in store.step_result(rid, 0)
    asyncio.run(go(*kit))


def test_막힌_대상이_그대로면_승인해도_게시하지_않는다(kit):
    """막힌 게시판이 하나라도 있으면 RA 는 게시 전체를 거절한다 — 알면서 부르지 않고 사유를 남긴다."""
    async def go(store, build):
        ra = FakeRA({**BOARDS, "dept-b": {**BOARDS["dept-b"], "blocked": BLOCKED}})
        g = ra.gate()
        r = build(g)
        spec = _publish_spec()
        rid, _ = await _gated_then_acked(store, r, spec)
        out2 = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        assert out2["state"] == "failed" and out2["stopped_at"] == 0, out2
        assert _inner(g, "reportarchive_publish_report") == []
        st = store.list_steps(rid)[0]
        assert (st["state"], st["stage"]) == ("failed", "publish:blocked")
        assert f"dept-b: {BLOCKED}" in st["error"]
        assert st["notes"]["publish_preview"]["targets"][1]["blocked"] == BLOCKED
        assert store.get_run(rid)["state"] == "failed"
    asyncio.run(go(*kit))


def test_미리보기가_실패하면_게이트_없이_그_단계에서_멈춘다(kit):
    """RA 가 `{error}` 봉투로 답하면(isError=false — PLAN §5-6 ④) 사람에게 보일 대상이 없다."""
    async def go(store, build):
        ra = FakeRA(dict(BOARDS))
        g = ra.gate()
        g.replies["reportarchive_preview_publish"] = lambda a: _ra({"error": "보고서를 찾을 수 없습니다: 41"})
        r = build(g)
        spec = _publish_spec()
        rid = _run(store, spec, inputs={"report_id": 41})
        out = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        assert out["state"] == "failed" and out["stopped_at"] == 0, out
        assert _inner(g, "reportarchive_publish_report") == []
        st = store.list_steps(rid)[0]
        assert st["stage"] == "preview" and "보고서를 찾을 수 없습니다" in st["error"]
        assert store.get_run(rid)["state"] == "failed"
    asyncio.run(go(*kit))


def test_옛_판본이_인자에_적은_확인_토큰은_버리고_미리보기의_것을_쓴다(kit):
    """저장 검증이 이제 거절하지만 판본은 불변이다 — 적힌 값이 단계 인자 · 지문에 들어가지 않게 실행기가 뗀다."""
    async def go(store, build):
        ra = FakeRA(dict(BOARDS))
        g = ra.gate()
        r = build(g)
        spec = ProcedureSpec(title="옛 게시", steps=[Step(
            backend="reportarchive", tool="publish_report", gate="human",
            args={"report_id": 41, "boards": ["dept-a"], "confirm_token": "{{tok}}"})])
        # 계획 모드도 실제로 나갈 것을 보인다
        plan = store.create_run(owner_sub="u1", mode="plan", inputs={"tok": "1793400000.stale"})
        out_p = await r.run(run_id=plan, spec=spec, principal=PRINCIPAL)
        assert out_p["calls"][0]["args"] == {"report_id": 41, "boards": ["dept-a"]}
        assert "confirm_token" not in store.list_steps(plan)[0]["args"]

        rid, _ = await _gated_then_acked(store, r, spec, inputs={"tok": "1793400000.stale"})
        assert "confirm_token" not in store.list_steps(rid)[0]["args"]
        assert (await r.run(run_id=rid, spec=spec, principal=PRINCIPAL))["state"] == "done"
        await r.aclose()
        assert _inner(g, "reportarchive_publish_report")[0]["confirm_token"] == ra.issued[1][0]
        assert "1793400000.stale" not in json.dumps(store.list_steps(rid), ensure_ascii=False)
    asyncio.run(go(*kit))


def test_옛_판본의_토큰_변수는_실행_입력에_없어도_돈다(kit):
    """옛 판본이 토큰을 받던 변수는 이제 입력이 아니다(coerce_inputs 가 받지도 남기지도 않는다) — 그 칸을 치환 전에 떼야 돈다."""
    async def go(store, build):
        ra = FakeRA(dict(BOARDS))
        g = ra.gate()
        r = build(g)
        spec = ProcedureSpec(title="옛 게시", vars=[Var(key="tok", label="확인 토큰")], steps=[Step(
            backend="reportarchive", tool="publish_report", gate="human",
            args={"report_id": 41, "boards": ["dept-a"], "confirm_token": "{{tok}}"})])
        plan = store.create_run(owner_sub="u1", mode="plan", inputs={})
        out_p = await r.run(run_id=plan, spec=spec, principal=PRINCIPAL)
        assert out_p["calls"][0]["args"] == {"report_id": 41, "boards": ["dept-a"]}
        assert out_p["unverified"] == [], "토큰 변수가 비었다고 계획이 '확인 못 함' 으로 남는다"

        rid, _ = await _gated_then_acked(store, r, spec, inputs={})
        assert (await r.run(run_id=rid, spec=spec, principal=PRINCIPAL))["state"] == "done"
        await r.aclose()
        assert _inner(g, "reportarchive_publish_report")[0]["confirm_token"] == ra.issued[1][0]
    asyncio.run(go(*kit))


def _preview_then_publish_spec() -> ProcedureSpec:
    """챗 기록을 편 초안(derive)에서 저장 거절 셋(save 토큰 · 게이트 · confirm_token)만 고친 꼴 — 미리보기 단계가 남는다."""
    return ProcedureSpec(title="챗에서 온 게시", vars=[Var(key="report_id", label="보고서", type="number")], steps=[
        Step(backend="reportarchive", tool="preview_publish", args={"report_id": "{{report_id}}", "boards": ["dept-a"]}),
        Step(backend="reportarchive", tool="publish_report", gate="human",
             args={"report_id": "{{report_id}}", "boards": ["dept-a"]})])


def test_따로_둔_미리보기_단계의_결과도_확인_토큰을_가려_남긴다(kit):
    """그 단계의 결과 원문에는 600초짜리 토큰이 들어 있다 — 원장에 넣기 전에 가린다. 나머지(대상 · 볼 사람 수)는 그대로다."""
    async def go(store, build):
        ra = FakeRA(dict(BOARDS))
        r = build(ra.gate())
        spec = _preview_then_publish_spec()
        rid = _run(store, spec, inputs={"report_id": 41})
        out = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        assert out["state"] == "gated" and out["stopped_at"] == 1, out
        store.ack_gate(rid, 1, by="u1", args_sha256=out["args_sha256"])
        assert (await r.run(run_id=rid, spec=spec, principal=PRINCIPAL, start_at=1))["state"] == "done"
        await r.aclose()
        toks = [t for t, _, _ in ra.issued]
        assert len(toks) == 3 and len(ra.published) == 1
        cells = _ledger_cells(store.health()["path"])
        assert [c[:80] for c in cells for t in toks if t in c or t.split(".")[1] in c] == []
        first = json.loads(store.step_result(rid, 0))
        assert first["confirm_token"] == "[가림:confirm_token]"
        assert [(t["slug"], t["audience"]) for t in first["targets"]] == [("dept-a", 12)]
    asyncio.run(go(*kit))


def test_한_단계씩_돌린_미리보기도_확인_토큰을_원장에_남기지_않는다(kit):
    """빈 실행에 한 단계씩 붙이는 길(절차 기능의 진입점)도 같은 `_one` 을 탄다."""
    async def go(store, build):
        ra = FakeRA(dict(BOARDS))
        r = build(ra.gate())
        rid = store.create_run(owner_sub="u1", mode="live", inputs={})
        got = await r.step_once(run_id=rid, principal=PRINCIPAL, step=Step(
            backend="reportarchive", tool="preview_publish", args={"report_id": 41, "boards": ["dept-a"]}))
        await r.aclose()
        assert got["ok"] is True, got
        tok = ra.issued[0][0]
        assert [c[:80] for c in _ledger_cells(store.health()["path"]) if tok in c] == []
        assert json.loads(store.step_result(rid, 0))["confirm_token"] == "[가림:confirm_token]"
    asyncio.run(go(*kit))


def test_승인_뒤_미리보기가_한_번_실패해도_다음_카드는_승인한_것과의_차이를_보인다(kit):
    """실패 행이 승인 지문과 승인한 미리보기를 지운 동안, 재개한 카드는 '바뀐 줄' 없이 처음 보는 카드처럼 떴다."""
    async def go(store, build):
        ra = FakeRA(dict(BOARDS))
        g = ra.gate()
        r = build(g)
        spec = _publish_spec()
        rid, _ = await _gated_then_acked(store, r, spec)          # 사람이 이 미리보기를 보고 승인했다
        keep = g.replies["reportarchive_preview_publish"]
        g.replies["reportarchive_preview_publish"] = lambda a: _ra({"error": "잠깐 불통"})
        assert (await r.run(run_id=rid, spec=spec, principal=PRINCIPAL))["state"] == "failed"
        st = store.list_steps(rid)[0]
        assert (st["state"], st["stage"]) == ("failed", "preview") and "잠깐 불통" in st["error"]
        g.replies["reportarchive_preview_publish"] = keep
        ra.boards["dept-b"] = {**BOARDS["dept-b"], "audience": 340}  # 그사이 볼 사람이 늘었다
        out3 = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)  # 재개
        await r.aclose()
        assert out3["state"] == "gated" and ra.published == [], out3
        assert out3["changed"] == ["dept-b 볼 수 있는 사람: 30 → 340"]
        assert store.list_steps(rid)[0]["notes"]["publish_changed"] == ["dept-b 볼 수 있는 사람: 30 → 340"]
    asyncio.run(go(*kit))


def test_승인_뒤_미리보기를_기다리는_사이_중단하면_게시하지_않는다(kit):
    """중단은 단계 경계에서만 봤다 — 두 번째 미리보기(네트워크)를 기다린 뒤 되돌릴 수 없는 게시를 그대로 보냈다."""
    async def go(store, build):
        ra = FakeRA(dict(BOARDS))
        g = ra.gate()
        r = build(g)
        spec = _publish_spec()
        rid, _ = await _gated_then_acked(store, r, spec)
        orig = g.replies["reportarchive_preview_publish"]

        def preview_then_cancel(a):
            got = orig(a)
            store.cancel_run(rid, "u1")   # 미리보기 응답이 오기 전에 사람이 '중단' 을 눌렀다
            return got

        g.replies["reportarchive_preview_publish"] = preview_then_cancel
        out = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        assert out == {"state": "cancelled", "stopped_at": 0}, out
        assert _inner(g, "reportarchive_publish_report") == [] and ra.published == []
        assert store.get_run(rid)["state"] == "cancelled"
    asyncio.run(go(*kit))


def test_게이트_전_미리보기를_기다리는_사이_중단하면_확인_대기로_덮지_않는다(kit):
    """덮이면 중단한 실행이 확인 대기 맨 위로 돌아온다 — 승인하면 게시까지 간다."""
    async def go(store, build):
        ra = FakeRA(dict(BOARDS))
        g = ra.gate()
        r = build(g)
        spec = _publish_spec()
        rid = _run(store, spec, inputs={"report_id": 41})
        orig = g.replies["reportarchive_preview_publish"]

        def preview_then_cancel(a):
            got = orig(a)
            store.cancel_run(rid, "u1")
            return got

        g.replies["reportarchive_preview_publish"] = preview_then_cancel
        out = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        assert out == {"state": "cancelled", "stopped_at": 0}, out
        assert store.get_run(rid)["state"] == "cancelled"
        assert store.list_steps(rid) == [], "중단한 뒤 게이트 카드를 썼다"
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


async def _pinging_gateway(tool_s: float, ping_s: float):
    """게이트웨이처럼 답하는 **진짜 소켓** — tools/call 응답에 `: ping` 을 ping_s 마다 싣고 tool_s 뒤에 결과를 낸다(chunked).
    MockTransport 는 시간 한도를 적용하지 않아, 한도가 실제로 걸리는지는 소켓으로만 본다."""
    async def handle(reader, writer):
        head = await reader.readuntil(b"\r\n\r\n")
        n = next((int(ln.split(b":")[1]) for ln in head.split(b"\r\n") if ln.lower().startswith(b"content-length")), 0)
        body = json.loads(await reader.readexactly(n)) if n else {}
        m = body.get("method")

        def plain(payload: dict, extra: bytes = b"") -> None:
            raw = json.dumps(payload).encode()
            writer.write(b"HTTP/1.1 200 OK\r\ncontent-type: application/json\r\nconnection: close\r\n" + extra
                         + b"content-length: %d\r\n\r\n" % len(raw) + raw)

        try:
            if m == "tools/call":
                writer.write(b"HTTP/1.1 200 OK\r\ncontent-type: text/event-stream\r\nconnection: close\r\n"
                             b"transfer-encoding: chunked\r\n\r\n")
                t0 = time.monotonic()
                while time.monotonic() - t0 < tool_s:
                    await asyncio.sleep(ping_s)
                    writer.write(b"%x\r\n%s\r\n" % (len(b": ping\r\n\r\n"), b": ping\r\n\r\n"))
                    await writer.drain()
                last = ("event: message\r\ndata: " + json.dumps({"jsonrpc": "2.0", "id": 2, "result": ok({"made": 1})})
                        + "\r\n\r\n").encode()
                writer.write(b"%x\r\n%s\r\n0\r\n\r\n" % (len(last), last))
            elif m == "tools/list":
                plain({"jsonrpc": "2.0", "id": 3, "result": {"tools": [
                    {"name": "b_create_thing", "description": "", "inputSchema": {}}]}})
            elif m == "initialize":
                plain({"jsonrpc": "2.0", "id": 1, "result": {}}, b"mcp-session-id: s1\r\n")
            else:
                plain({})
            await writer.drain()
            writer.close()
        except (ConnectionError, OSError):      # 실행기가 기한에 먼저 끊었다 — 이 시험이 보려는 바로 그 일이다
            pass
    return await asyncio.start_server(handle, "127.0.0.1", 0)


def test_ping_이_흐르는_응답에도_단계_상한은_벽시계로_걸린다(tmp_path, monkeypatch):
    """게이트웨이는 응답에 15초마다 ping 을 싣는다. httpx 한도는 바이트 사이 간격이라 ping 이 올 때마다 되감긴다 — 단계 상한이
    그 한도뿐이면 살아 있는 게이트웨이 앞에서는 한 번도 안 걸린다. 그러면 '빠름(30초)' 으로 적은 단계가 게이트웨이 상한(600초)까지
    기다리고, 게이트웨이가 끊은 쓰기는 `unknown` 이 아니라 `failed` 로 남아 재개가 **확인 없이** 다시 보낸다.
    같은 비율로 줄여 본다 — 상한 0.3초 · ping 0.1초 · 도구 1.5초. 고치기 전에는 1.5초 뒤 done 이었다."""
    from app.procedures import runner as R

    monkeypatch.setitem(R.EXPECT_TIMEOUT, "fast", 0.3)

    async def go():
        srv = await _pinging_gateway(tool_s=1.5, ping_s=0.1)
        port = srv.sockets[0].getsockname()[1]
        s = Settings(procedures_store_path=str(tmp_path / "wb.sqlite"), mcp_gateway_url=f"http://127.0.0.1:{port}")
        store = ProceduresStore(s)
        r = ProceduresRunner(settings=s, store=store, mint_pat=lambda p, run, ix: "pat")
        spec = _spec([{"backend": "b", "tool": "create_thing"}])
        rid = _run(store, spec)
        t0 = time.perf_counter()
        try:
            await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
            took = time.perf_counter() - t0
            st = store.list_steps(rid)[0]
        finally:
            await r.aclose()
            store.close()
            srv.close()
            await srv.wait_closed()
        assert (st["state"], st["stage"]) == ("unknown", "timeout"), (st["state"], st["stage"], f"{took:.2f}초")
        assert "실행 여부를 모른다" in st["error"]
        assert took < 1.0, f"단계 상한 0.3초가 {took:.2f}초에야 걸렸다 — 도구가 끝나기를 기다렸다"
    asyncio.run(go())


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


def test_워밍업_호출은_단계_상한이_아니라_워밍업_한도로_나간다(kit):
    """워밍업 한도는 게이트웨이가 스스로 포기할 때까지 기다리는 값이다(게이트웨이 상한 600 + 바깥 기한 60 + 여유).
    단계 상한(110초)으로 나가면 콜드스타트를 흡수하기 전에 우리가 먼저 끊는다."""
    from app.procedures.runner import EXPECT_TIMEOUT, WARMUP_TIMEOUT

    async def go(store, build):
        g = Gate(tools={"b_search_catalog_property": {}, "b_use_it": {}},
                 replies={"b_search_catalog_property": ok({}), "b_use_it": ok({"found": 1})})
        r = build(g)
        seen: dict[str, float] = {}
        inner = r._client._transport.handler

        async def spy(req: httpx.Request) -> httpx.Response:
            body = json.loads(req.content) if req.content else {}
            if body.get("method") == "tools/call":
                seen[body["params"]["arguments"]["name"]] = req.extensions["timeout"]["read"]
            return await inner(req)

        r._client._transport.handler = spy
        spec = _spec([{"backend": "b", "tool": "search_catalog_property", "warmup": True},
                      {"backend": "b", "tool": "use_it", "expect": "slow"}])
        rid = _run(store, spec)
        out = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        assert out["state"] == "done"
        assert seen == {"b_search_catalog_property": WARMUP_TIMEOUT, "b_use_it": EXPECT_TIMEOUT["slow"]}
        assert WARMUP_TIMEOUT == 690.0 and EXPECT_TIMEOUT["slow"] == 110.0
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
        # ⚠ **원장에도 이유가 남아야 한다.** 예전엔 stage 가 `schema_drift` 한 낱말뿐이라, 화면에서
        # 어느 단계의 어떤 도구가 문제인지 알 길이 없었다(2026-09-17 cae00 점검).
        row = store.get_run(rid)
        assert row["stage"].startswith("schema_drift: ") and "1단계 a" in row["stage"], row["stage"]
    asyncio.run(go(*kit))


def test_게이트웨이에_없는_도구도_어느_단계인지_원장에_남는다(kit):
    """cae00 에서 앱이 안 붙어 있거나 권한 밖이면 이 경로로 선다 — 이유가 없으면 사람이 못 고친다."""
    async def go(store, build):
        g = Gate(tools={}, replies={})
        r = build(g)
        spec = _spec([{"backend": "b", "tool": "a"}])
        rid = _run(store, spec)
        out = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        assert out["state"] == "failed" and out["stage"] == "schema_drift"
        row = store.get_run(rid)
        assert "게이트웨이에 없다" in row["stage"] and "1단계 a" in row["stage"], row["stage"]
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


# ── 값 단언 — 성공한 응답이 **기대한 대상의 것**인가 ─────────────────────────────────────────
def test_값_단언이_어긋나면_그_단계에서_멈춘다(kit):
    """판정기는 '도구가 실패했나' 만 본다. 전각도 회수 절차가 impact 리포트를 받아도 판독은 전부
    성공하고 보고서만 다른 해석 위에서 나온다 — 그 자리를 절차가 선언으로 막는다."""
    async def go(store, build):
        g = Gate(tools={"b_a": {"description": "d", "inputSchema": {}},
                        "b_b": {"description": "d", "inputSchema": {}}},
                 replies={"b_a": ok({"kind": "impact"}), "b_b": ok({})})
        r = build(g)
        spec = _spec([{"backend": "b", "tool": "a",
                       "assert": [{"path": "kind", "equals": "sphere", "why": "전각도 리포트여야 한다"}]},
                      {"backend": "b", "tool": "b"}])
        rid = _run(store, spec)
        out = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        assert out["state"] == "failed" and out["kind"] == "assert_failed", out
        assert "sphere" in out["error"] and "전각도 리포트여야" in out["error"], out["error"]
        assert [c["arguments"]["name"] for c in g.calls] == ["b_a"], "어긋난 뒤 단계는 부르지 않는다"
    asyncio.run(go(*kit))


def test_값_단언이_맞으면_그대로_간다(kit):
    async def go(store, build):
        g = Gate(tools={"b_a": {"description": "d", "inputSchema": {}}},
                 replies={"b_a": ok({"kind": "sphere", "parts": [{"part_id": 3}]})})
        r = build(g)
        spec = _spec([{"backend": "b", "tool": "a",
                       "assert": [{"path": "kind", "in": ["sphere", "deep"]},
                                  {"path": "parts[0].part_id", "not_empty": True}],
                       "save": {"kind": "kind"}}])
        rid = _run(store, spec)
        out = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        assert out["state"] == "done", out
        assert store.get_run(rid)["inputs"]["kind"] == "sphere"
    asyncio.run(go(*kit))


def test_단언_경로가_안_풀리면_그것도_멈춘다(kit):
    """'없는 칸' 을 '기대와 같다' 로 보면, 단언이 붙은 단계가 전부 무사통과한다."""
    async def go(store, build):
        g = Gate(tools={"b_a": {"description": "d", "inputSchema": {}}}, replies={"b_a": ok({"other": 1})})
        r = build(g)
        spec = _spec([{"backend": "b", "tool": "a", "assert": [{"path": "kind", "equals": "sphere"}]}])
        rid = _run(store, spec)
        out = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        assert out["state"] == "failed" and out["kind"] == "assert_missing", out
    asyncio.run(go(*kit))


# ── 인자를 못 풀면 실행이 running 인 채 남았다(2026-09-17 재현) ─────────────
def test_앞_단계가_건너뛰면_뒤_단계는_실행을_세우고_끝난다(kit):
    """`TemplateError` 가 `_loop` 밖으로 나가면 실행은 **`running` 인 채 영원히** 남는다.

    화면에는 도는 것으로 보이고, 끝나지 않으니 재개도 취소도 아니다. `select on_none: skip`
    이 그 입구다 — 앞 단계가 건너뛰면 뒤 단계가 쓸 변수가 없다.
    """
    async def go(store, build):
        g = Gate(tools={"b_find": {}, "b_use": {}},
                 replies={"b_find": ok({"items": []}), "b_use": ok({"done": 1})})
        r = build(g)
        spec = _spec([{"backend": "b", "tool": "find",
                       "select": {"from": "items", "save": "id", "as": "ids", "on_none": "skip"}},
                      {"backend": "b", "tool": "use", "args": {"ids": "{{ids}}"}}])
        rid = _run(store, spec)
        out = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        assert out["state"] == "failed" and out["kind"] == "args_missing", out
        run = store.get_run(rid)
        assert run["state"] == "failed", "running 인 채 남으면 사람이 손댈 수 없다"
        assert [(s["ix"], s["state"], s["stage"]) for s in run["steps"]] == [
            (0, "skipped", "select:none"), (1, "failed", "args")]
        assert "ids" in run["steps"][1]["error"], run["steps"][1]["error"]
        assert [c["arguments"]["name"] for c in g.calls] == ["b_find"], "못 푼 인자로 부르지 않는다"
    asyncio.run(go(*kit))


def test_게이트_단계도_같은_자리에서_선다(kit):
    """게이트는 치환을 **따로** 했다 — 거기서 터지면 승인 화면도 못 뜬 채 running 이었다."""
    async def go(store, build):
        g = Gate(tools={"b_find": {}, "b_use": {}},
                 replies={"b_find": ok({"items": []}), "b_use": ok({"done": 1})})
        r = build(g)
        spec = _spec([{"backend": "b", "tool": "find",
                       "select": {"from": "items", "save": "id", "as": "ids", "on_none": "skip"}},
                      {"backend": "b", "tool": "use", "gate": "human", "args": {"ids": "{{ids}}"}}])
        rid = _run(store, spec)
        out = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        assert out["state"] == "failed" and out["kind"] == "args_missing", out
        assert store.get_run(rid)["state"] == "failed"
    asyncio.run(go(*kit))


def test_승인한_인자_그대로_나간다(kit):
    """게이트와 호출이 **각각** 치환했다 — 둘 사이에 범위가 바뀌면 승인한 것과 다른 것이 나간다."""
    async def go(store, build):
        g = Gate(tools={"b_w": {}}, replies={"b_w": ok({"done": 1})})
        r = build(g)
        spec = _spec([{"backend": "b", "tool": "w", "gate": "human",
                       "args": {"who": "{{me.email}}", "n": 1}}])
        rid = _run(store, spec)
        out = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        assert out["state"] == "gated", out
        store.ack_gate(rid, 0, by="u1", args_sha256=out["args_sha256"])
        out2 = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL, start_at=0)
        await r.aclose()
        assert out2["state"] == "done", out2
        sent = [c for c in g.calls if c["arguments"].get("name") == "b_w"]
        assert sent and sent[0]["arguments"]["arguments"] == {"who": "u1@x.io", "n": 1}
    asyncio.run(go(*kit))


# ── 비운 선택 변수(W-102) ─────────────────────────────────────────────────
def _opt_spec(args, gate=None):
    st = {"backend": "b", "tool": "w", "args": args, **({"gate": gate} if gate else {})}
    return ProcedureSpec(title="t", vars=[Var(key="p", label="p", required=False)], steps=[Step(**st)])


def test_비운_선택_변수는_도구에_칸_없이_간다(kit):
    """비운 선택 변수를 쓰는 단계가 '변수 없음' 으로 멈췄다 — 제출 뒤의 후처리 예약이면 제출만 나가고 예약은 안 걸린다."""
    async def go(store, build):
        g = Gate(tools={"b_w": {}}, replies={"b_w": ok({"done": 1})})
        r = build(g)
        spec = _opt_spec({"p": "{{p}}", "n": 1})
        rid = _run(store, spec)
        assert (await r.run(run_id=rid, spec=spec, principal=PRINCIPAL))["state"] == "done"
        rid2 = _run(store, spec, inputs={"p": "DEMO"})
        assert (await r.run(run_id=rid2, spec=spec, principal=PRINCIPAL))["state"] == "done"
        await r.aclose()
        assert [c["arguments"]["arguments"] for c in g.calls] == [{"n": 1}, {"p": "DEMO", "n": 1}]
        assert "p" not in (store.get_run(rid)["inputs"] or {}), "자리표는 원장에 안 남는다"
    asyncio.run(go(*kit))


def test_비운_선택_변수를_문자열_안에_쓰면_그_단계에서_멈춘다(kit):
    async def go(store, build):
        g = Gate(tools={"b_w": {}}, replies={"b_w": ok({})})
        r = build(g)
        spec = _opt_spec({"title": "과제 {{p}}"})
        rid = _run(store, spec)
        out = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        assert out["state"] == "failed" and out["kind"] == "args_missing", out
        assert g.calls == [], "못 푼 인자로 부르지 않는다"
        err = store.get_run(rid)["steps"][0]["error"]
        assert "선택 변수가 비었다: p" in err and "앞 단계가" not in err, "앞 단계 탓이 아니다 — 채우거나 통째 자리로"
    asyncio.run(go(*kit))


def test_비운_선택_변수가_목록_원소면_그_이름을_대고_멈춘다(kit):
    async def go(store, build):
        g = Gate(tools={"b_w": {}}, replies={"b_w": ok({})})
        r = build(g)
        spec = _opt_spec({"tags": ["{{p}}", "x"]})
        rid = _run(store, spec)
        out = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        assert out["state"] == "failed" and out["kind"] == "args_missing", out
        err = store.get_run(rid)["steps"][0]["error"]
        assert "선택 변수가 비었다: p" in err and "앞 단계가" not in err
        assert g.calls == []
    asyncio.run(go(*kit))


def test_비운_선택_변수도_게이트_지문이_재개_뒤에_같다(kit):
    """자리표는 원장에 없고 실행마다 다시 채운다 — 재개 때 지문이 달라지면 승인이 영영 안 맞는다."""
    async def go(store, build):
        g = Gate(tools={"b_w": {}}, replies={"b_w": ok({"done": 1})})
        r = build(g)
        spec = _opt_spec({"p": "{{p}}", "who": "{{me.email}}"}, gate="human")
        rid = _run(store, spec)
        out = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        assert out["state"] == "gated", out
        store.ack_gate(rid, 0, by="u1", args_sha256=out["args_sha256"])
        out2 = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL, start_at=0)
        await r.aclose()
        assert out2["state"] == "done", out2
        assert g.calls[-1]["arguments"]["arguments"] == {"who": "u1@x.io"}
    asyncio.run(go(*kit))


def test_계획_모드도_빠진_칸으로_보인다(kit):
    async def go(store, build):
        r = build(Gate())
        spec = _opt_spec({"p": "{{p}}", "n": 1})
        rid = store.create_run(owner_sub="u1", mode="plan", inputs={})
        out = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        assert out["calls"][0]["args"] == {"n": 1} and out["calls"][0]["unverified"] is False, out
    asyncio.run(go(*kit))


# ── 사람 자리는 실행 시점에도 선다(W-100) ──────────────────────────────────
def test_즉석_단계_실행기도_사람_자리를_거절한다(kit):
    """라우트가 먼저 거르지만, 다른 호출부가 생겨도 뚫리지 않게 실행기가 한 번 더 막는다."""
    async def go(store, build):
        g = Gate(tools={"reportarchive_trash_report": {}},
                 replies={"reportarchive_trash_report": ok({"trashed": 1})})
        r = build(g)
        rid = _run(store, None)
        for st in (Step(backend="reportarchive", tool="trash_report", gate="human"),
                   Step(backend="reportarchive", tool="trash_report")):
            with pytest.raises(RunnerError, match="즉석으로 돌리지 않는다"):
                await r.step_once(run_id=rid, step=st, principal=PRINCIPAL)
        await r.aclose()
        assert g.calls == [], f"게이트웨이까지 갔다: {g.calls}"
    asyncio.run(go(*kit))


def test_옛_판본의_MUST_GATE_단계도_실행_시점에_멈춘다(kit):
    """판본은 불변이라 저장 검증을 다시 안 탄다. `publish_report_to_datahub` 는 09-15 에야 MUST_GATE 에
    들었다 — 그 전에 `gate` 없이 저장된 단계가 오늘 확인 없이 지나가면 안 된다."""
    async def go(store, build):
        g = Gate(tools={"b_read": {}, "reportarchive_publish_report_to_datahub": {}},
                 replies={"b_read": ok({"id": 7}),
                          "reportarchive_publish_report_to_datahub": ok({"published": 1})})
        r = build(g)
        # validate_spec 을 거치지 않은 판본 — 저장 당시엔 MUST_GATE 가 아니었다
        spec = ProcedureSpec(title="old", steps=[
            Step(backend="b", tool="read", save={"rid": "id"}),
            Step(backend="reportarchive", tool="publish_report_to_datahub", args={"id": "{{rid}}"})])
        rid = _run(store, spec)
        out = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        assert out["state"] == "gated" and out["stopped_at"] == 1, out
        assert [c["arguments"]["name"] for c in g.calls] == ["b_read"], "승인 전에 나갔다"

        store.ack_gate(rid, 1, by="u1", args_sha256=out["args_sha256"])
        out2 = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL, start_at=1)
        await r.aclose()
        assert out2["state"] == "done", out2
        assert [c["arguments"]["name"] for c in g.calls][-1] == "reportarchive_publish_report_to_datahub"
    asyncio.run(go(*kit))


def test_계획_모드는_실제로_멈출_자리를_보인다(kit):
    """선언이 없어도 멈추는 단계를 계획에서 `gate: None` 으로 보이면 사람은 '확인 없이 간다' 로 읽는다."""
    async def go(store, build):
        r = build(Gate())
        spec = ProcedureSpec(title="p", steps=[Step(backend="reportarchive", tool="trash_report")])
        rid = store.create_run(owner_sub="u1", mode="plan", inputs={})
        out = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        calls = out.get("calls") or []
        assert calls and calls[0]["gate"] == "human", out
    asyncio.run(go(*kit))


# ── 도구 설명에만 있는 경고(합성 데이터 모델 — W-7 ③) ─────────────────────────
# 게이트웨이 실물 설명(ai-data-hub `pcb_warpage_surrogate`, 10-17) — 응답에는 이 경고가 없다.
SURROGATE_DESC = ("적 휨(µm)을 즉시 예측하는 회귀 대리모델. 홀드아웃 R²=0.971. 예측값과 함께 민감도 곡선 PNG를 반환한다. "
                  "경고: 이 모델은 합성(synthetic) 데이터로 학습한 데모다. 실제 공정·측정 데이터가 아니며 계수는 어떤 "
                  "실측으로도 교정되지 않았다. 절대값을 판정·양산 의사결정 근거로 쓰지 마라 (경향 비교와 민감도 확인 용도).")


def test_합성_데이터_경고는_설명에서_읽어_단계_경고에_남긴다(kit):
    async def go(store, build):
        g = Gate(tools={"b_surrogate": {"description": SURROGATE_DESC}, "b_plain": {"description": "평범한 도구"}},
                 replies={"b_surrogate": ok({"pred_um": 41.2}), "b_plain": ok({})})
        r = build(g)
        spec = _spec([{"backend": "b", "tool": "surrogate"}, {"backend": "b", "tool": "plain"}])
        rid = _run(store, spec)
        out = await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        assert out["state"] == "done", out
        s0, s1 = store.list_steps(rid)
        w = s0["notes"]["warnings"]
        assert len(w) == 1 and w[0].startswith("합성 데이터 모델(도구 설명) — 이 모델은 합성(synthetic) 데이터로")
        assert "판정·양산 의사결정 근거로 쓰지 마라" in w[0]
        assert "warnings" not in s1["notes"], "경고 없는 도구에 경고를 달았다"
    asyncio.run(go(*kit))


def test_결과가_준_경고는_그대로_두고_덧붙인다(kit):
    async def go(store, build):
        g = Gate(tools={"b_surrogate": {"description": SURROGATE_DESC}},
                 replies={"b_surrogate": ok({"pred_um": 1, "warnings": ["W120: ply 제외"]})})
        r = build(g)
        spec = _spec([{"backend": "b", "tool": "surrogate"}])
        rid = _run(store, spec)
        await r.run(run_id=rid, spec=spec, principal=PRINCIPAL)
        await r.aclose()
        w = store.list_steps(rid)[0]["notes"]["warnings"]
        assert w[0] == "W120: ply 제외" and w[1].startswith("합성 데이터 모델(도구 설명)"), w
    asyncio.run(go(*kit))


def test_한_단계씩_돌려도_합성_데이터_경고가_남는다(kit):
    """`step_once` 가 절차 기능의 진입점이다 — 여기서 빠지면 사람이 한 단계씩 돌린 기록에 없다."""
    async def go(store, build):
        g = Gate(tools={"b_surrogate": {"description": SURROGATE_DESC}}, replies={"b_surrogate": ok({"pred_um": 1})})
        r = build(g)
        rid = store.create_run(owner_sub="u1", mode="live")
        out = await r.step_once(run_id=rid, principal=PRINCIPAL, step=Step(backend="b", tool="surrogate"))
        await r.aclose()
        assert out["ok"] is True
        assert store.list_steps(rid)[0]["notes"]["warnings"][0].startswith("합성 데이터 모델(도구 설명)")
    asyncio.run(go(*kit))


@pytest.mark.parametrize("desc", [
    "CLT 는 모든 층이 **완전합성**으로 함께 굽는다고 가정한다",                       # 복합재 — 다른 뜻
    "새 파트의 경로는 `<과제>/shape_ops/<이름>`(합성 경로 — 원본 트리가 아니다)",       # 경로 — 다른 뜻
    "서버 설정 DELIB_KNOWLEDGE_SYNTHETIC_SEATS 에 그 키를 적어야 조회한다",            # 환경 변수 이름
    "실선=실측, 점선=합성 근사이므로 반드시 구분해 해석하라",                           # 결과 안의 표시 — 도구가 이미 가른다
    "", None])
def test_합성_한_낱말로는_경고를_달지_않는다(desc):
    from app.procedures.judge import description_caveat
    assert description_caveat(desc) is None


@pytest.mark.parametrize("desc, want", [
    ("합성(synthetic) 데이터로 학습했다. 경향만 보라.", "합성(synthetic) 데이터로 학습했다. 경향만 보라."),   # 첫 문장부터 — 앞 글자를 자르지 않는다
    ("대리모델.\n⚠ 경고: synthetic data 로 맞췄다.\n\n사용법: x", "synthetic data 로 맞췄다."),          # 줄 경계 · ⚠ · '경고:' 를 떼고 문단에서 멈춘다
])
def test_합성_데이터_경고는_그_문장부터_문단_끝까지다(desc, want):
    from app.procedures.judge import description_caveat
    assert description_caveat(desc) == f"합성 데이터 모델(도구 설명) — {want}"
