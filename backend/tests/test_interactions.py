# 상호작용 기록(docs/interaction-data) — 가림 벡터 · 원장 · 수집기 원천 넷 · 상태 코드 · 창구(공유 · 내 기록 · 지우기 · 분석가) · 꺼짐 404
"""계약(contract.md)을 그대로 단언한다 — 가림 부록 벡터 다섯 · UNIQUE(source, source_ref) · 같은 세션 덮어쓰기 · 50 MB 상한 · grant_only 분석가 ·
원문 열기마다 감사 한 줄. 원장 · 원천은 모두 임시 폴더이고 게이트웨이는 HTTP 대역(MockTransport)이다 — 떠 있는 서비스를 부르지 않는다."""
import gzip
import json
import time
import types

import httpx
import pytest
from fastapi.testclient import TestClient

from app.agent.conv_store import ConversationStore
from app.auth.cookies import CSRF_COOKIE
from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.interactions import collector
from app.interactions import transcript as tx
from app.interactions.redact import redact, redact_text
from app.interactions.store import InteractionStore, ulid
from app.main import app
from app.procedures.routine_store import RoutineStore
from app.procedures.store import ProceduresStore

# contract.md 부록 — 두 리포 시험이 그대로 쓴다
VECTORS = [
    ('{"Authorization": "Bearer abc.def"}', '{"Authorization": "<가림:authorization>"}'),
    ('{"args": {"api_key": "k-123", "q": "응력"}}', '{"args": {"api_key": "<가림:api_key>", "q": "응력"}}'),
    ("curl -H 'Authorization: Bearer x1y2z3'", "curl -H 'Authorization: Bearer <가림:bearer>'"),
    ("토큰 eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ4In0.c2ln 끝", "토큰 <가림:jwt> 끝"),
    ('{"user_password": "p@ss", "count": 3}', '{"user_password": "<가림:user_password>", "count": 3}'),
]


@pytest.fixture()
def s(tmp_path):
    return Settings(_env_file=None, interactions_enabled=True, interactions_store_path=str(tmp_path / "ix.sqlite"),
                    conv_store_path=str(tmp_path / "conv.sqlite"), procedures_store_path=str(tmp_path / "proc.sqlite"),
                    mcp_gateway_url="http://gw.test", gateway_shared_token="sek", interactions_ingest_s=60)


@pytest.fixture()
def st(s):
    store = InteractionStore(s)
    yield store
    store.close()


def _app():
    return types.SimpleNamespace(state=types.SimpleNamespace())


# ── 가림(contract §4) ──────────────────────────────────────────────────────────
@pytest.mark.parametrize(("got", "want"), VECTORS)
def test_가림_벡터를_글로도_구조로도_그대로_낸다(got, want):
    assert redact_text(got) == want
    assert redact_text(want) == want, "두 번 걸어도 같다 — 게이트웨이가 가린 것을 포털이 다시 건다"
    try:
        obj = json.loads(got)
    except ValueError:
        return
    assert json.dumps(redact(obj), ensure_ascii=False) == want


def test_가림_PEM_덩어리와_잘린_PEM_과_칸_이름_끝말():
    assert redact_text("앞 -----BEGIN RSA PRIVATE KEY-----\nMIIabc\n-----END RSA PRIVATE KEY----- 뒤") == "앞 <가림:pem> 뒤"
    assert redact_text("-----BEGIN PRIVATE KEY-----\nMIIabc 잘림") == "<가림:pem>", "끝 표지가 없으면 글 끝까지"
    assert redact_text("Bearer -----BEGIN EC PRIVATE KEY-----\nAAA\n-----END EC PRIVATE KEY-----") == "Bearer <가림:pem>", "PEM 이 먼저(게이트웨이와 같은 차례)"
    assert redact_text("Bearer\tab.c") == "Bearer <가림:bearer>" and redact_text("Bearer\nnext") == "Bearer\nnext", "Bearer 뒤 구분은 빈칸 · 탭만"
    got = redact({"max_tokens": 5, "session_id": "s1", "X-Api-Key": "z", "Cookie": "a=b", "nested": [{"refresh_token": "r"}], "token": None})
    assert got == {"max_tokens": 5, "session_id": "s1", "X-Api-Key": "<가림:x-api-key>", "Cookie": "<가림:cookie>",
                   "nested": [{"refresh_token": "<가림:refresh_token>"}], "token": None}


# ── 원장 ──────────────────────────────────────────────────────────────────────
def test_원장_한_번만_넣고_상한을_넘는_글은_앞부분_크기_sha_를_남긴다(s, tmp_path):
    s2 = s.model_copy(update={"interactions_output_max_bytes": 2000})
    st = InteractionStore(s2)
    big = "가" * 3000                                   # 9000 바이트
    ev = {"ts": 100, "surface": "web_chat", "actor": "Me@X.com", "output": big, "input": {"api_key": "k"},
          "source": "conversations", "source_ref": "m1"}
    assert st.put_events([ev, dict(ev)]) == 1, "같은 (source, source_ref) 는 한 번만"
    assert st.put_events([ev]) == 0
    got = st.search(actor="me@x.com")["items"]
    assert len(got) == 1 and got[0]["actor"] == "me@x.com", "주인은 소문자"
    full = st.get(got[0]["id"])
    assert len(full["output"].encode()) <= 2000 and full["output_chars"] == 3000 and full["meta"]["output_clipped"]
    import hashlib
    assert full["output_sha256"] == hashlib.sha256(big.encode()).hexdigest(), "sha 는 원문 전체의 것"
    assert full["input"] == '{"api_key": "<가림:api_key>"}', "넣기 전에 가린다"
    st.close()


def test_원장_ULID_차례가_시각_차례이고_before_로_넘긴다(st):
    assert ulid(1000) < ulid(2000) and len(ulid()) == 26
    st.put_events([{"ts": t, "surface": "web_chat", "actor": "a@x", "input": f"q{t}", "source": "t", "source_ref": str(t)}
                   for t in (10, 20, 30)])
    p1 = st.search(actor="a@x", limit=2)
    assert [i["input_preview"] for i in p1["items"]] == ["q30", "q20"] and p1["more"]
    p2 = st.search(actor="a@x", limit=2, before=p1["next_before"])
    assert [i["input_preview"] for i in p2["items"]] == ["q10"] and not p2["more"]


def test_지우기는_그_사람_것만_지우고_표지_앞선_줄은_다시_들어오지_않는다(st):
    mk = lambda who, t, ref: {"ts": t, "surface": "mcp_call", "actor": who, "output": "r", "source": "gateway", "source_ref": ref}  # noqa: E731
    st.put_events([mk("a@x", 10, "1"), mk("b@x", 10, "2")])
    st.put_shared(owner="a@x", session_id="s", title="t", client="c", messages=[{"role": "user", "content": "x"}], kind="tool",
                  raw=None, event={"input": "t", "output": "x"})
    got = st.erase("A@X")
    assert got["events"] == 2 and got["shared"] == 1
    assert st.search(actor="b@x")["items"], "남의 것은 그대로"
    assert st.put_events([mk("a@x", 10, "3"), mk("a@x", got["upto"], "4")]) == 0, "지우기 시각 전(같음 포함)의 줄은 되살아나지 않는다"
    assert st.put_events([mk("a@x", got["upto"] + 5, "5")]) == 1, "그 뒤의 일은 다시 쌓인다(수집 사실은 알린다)"


# ── 수집기 — 대화 저장소(S1 · S2) ──────────────────────────────────────────────
def test_대화_저장소를_증분으로_옮기고_겉면과_턴_메타를_싣는다(s, st):
    conv = ConversationStore(s)
    c1 = conv.create(owner_sub="Me@x.com", title="힌지", kind="chat")
    conv.append(conversation_id=c1, owner_sub="Me@x.com", role="user", content="힌지 강도 봐 줘 Bearer secret123")
    conv.append(conversation_id=c1, owner_sub="Me@x.com", role="assistant", content="답",
                meta={"activity": [{"tool": "get_material", "ok": True, "detail_full": "x"}],
                      "turn": {"chat_model": "qwen", "self_check": {"status": "fixed"}, "confirm": [{"tool": "submit"}]}})
    conv.append(conversation_id=c1, owner_sub="Me@x.com", role="assistant", content="요약", meta={"answered_by": "think"})
    c2 = conv.create(owner_sub="Me@x.com", title="심의", kind="deliberation", source="mcp")
    conv.append(conversation_id=c2, owner_sub="Me@x.com", role="persona", content="좌석 발언", persona="cae-b", round=1)
    aff = lambda e: "CAEG"  # noqa: E731
    assert collector._ingest_conversations(s, st, aff) == 4
    assert collector._ingest_conversations(s, st, aff) == 0, "다시 돌아도 둘이 되지 않는다"
    items = {i["input_preview"] or i["output_preview"]: i for i in st.search(actor="me@x.com")["items"]}
    assert items["힌지 강도 봐 줘 Bearer <가림:bearer>"]["surface"] == "web_chat"
    ans = st.get(items["답"]["id"])
    assert ans["model"] == "qwen" and ans["meta"]["tools"] == ["get_material"] and ans["meta"]["turn"]["self_check"]["status"] == "fixed"
    assert ans["meta"]["turn"]["confirm"] == [{"tool": "submit"}] and ans["affiliation"] == "CAEG" and ans["conv_id"] == c1
    assert items["요약"]["surface"] == "think"
    seat = st.get(items["좌석 발언"]["id"])
    assert seat["surface"] == "web_delib" and seat["client"] == "MCP 워크플로" and seat["meta"]["persona"] == "cae-b"
    conv.append(conversation_id=c1, owner_sub="Me@x.com", role="user", content="다음 질문")
    assert collector._ingest_conversations(s, st, aff) == 1


def test_대화_저장소_끝_줄이_지워진_뒤_다시_쓰인_rowid_도_놓치지_않는다(s, st):
    conv = ConversationStore(s)
    c1 = conv.create(owner_sub="a@x", title="t")
    for i in range(3):
        conv.append(conversation_id=c1, owner_sub="a@x", role="user", content=f"m{i}")
    c2 = conv.create(owner_sub="a@x", title="곧 지울 것")
    conv.append(conversation_id=c2, owner_sub="a@x", role="user", content="지울 글")
    collector._ingest_conversations(s, st, lambda e: None)
    conv.delete(c2, "a@x")                       # 끝 rowid 가 빠진다 — 다음 넣기가 같은 rowid 를 쓴다
    c3 = conv.create(owner_sub="a@x", title="새 대화")
    conv.append(conversation_id=c3, owner_sub="a@x", role="user", content="새 글")
    assert collector._ingest_conversations(s, st, lambda e: None) == 1
    assert any(i["input_preview"] == "새 글" for i in st.search(actor="a@x")["items"])


# ── 수집기 — 절차 · 루틴(S6) ─────────────────────────────────────────────────
def test_끝난_절차_단계와_루틴_호출_보고서를_옮긴다(s, st):
    ps = ProceduresStore(s)
    RoutineStore(ps)
    with ps._conn() as c:
        c.execute("INSERT INTO runs (id, owner_sub, run_by, title, state, started_at, ended_at) VALUES ('r1','o@x','o@x','검토','done',100,110)")
        c.execute("INSERT INTO runs (id, owner_sub, run_by, title, state, started_at) VALUES ('r2','o@x','o@x','도는 중','running',100)")
        for ix, ok in ((0, 1), (1, 0)):
            c.execute("INSERT INTO run_steps (run_id, ix, backend, tool, args_json, args_sha256, result_gz, result_sha256, state, ok, "
                      "started_at, duration_ms) VALUES ('r1', ?, 'step-forge', 'section', '{\"token\":\"t\"}', 'h', ?, 'sha', 'done', ?, 101, 5)",
                      (ix, gzip.compress(f"결과{ix}".encode()), ok))
        c.execute("INSERT INTO routine_runs (id, owner_sub, routine_id, version_id, version_no, title, inputs_json, plan_json, executor, "
                  "conversation_id, state, started_at, deadline, ended_at, report_md) VALUES ('rr1','o@x','rt','v',1,'루틴','{}','{}','qwen',"
                  "'cv1','done',100,999,120,'# 보고서')")
        c.execute("INSERT INTO routine_calls (run_id, call_id, step_id, n, backend, tool, args_json, args_sha256, ok, ms, result_gz, "
                  "result_chars, created_at) VALUES ('rr1','c1','s1',1,'ai-data-hub','search','{}','h',1,7,?,3,115)", (gzip.compress(b"abc"),))
    assert collector._ingest_procedures(s, st, lambda e: None) == 4, "끝난 실행만 — 단계 둘 · 루틴 보고서 하나 · 호출 하나"
    assert collector._ingest_procedures(s, st, lambda e: None) == 0
    rows = {(i["surface"], i["tool"], i["status"]) for i in st.search(actor="o@x")["items"]}
    assert rows == {("procedure", "section", "ok"), ("procedure", "section", "error"), ("routine", None, "ok"), ("routine", "search", "ok")}
    step = next(i for i in st.search(actor="o@x", surface="procedure")["items"] if i["status"] == "ok")
    full = st.get(step["id"])
    assert full["output"] == "결과0" and full["via"] == "procedure" and full["input"] == '{"token":"<가림:token>"}'
    ps.close()


# ── 수집기 — 게이트웨이 창고(S3)와 도구 검색 질의(S4) ──────────────────────────────
def _gw(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _spool_event(i, **over):
    # 게이트웨이 작업자가 확정한 꼴 — ts 는 소수 셋째 초 · client 는 '이름/판' 글 · via 는 게이트웨이 낱말(pat · chat · procedure · mcp-app · gw-token · service)
    return {"ts": 1000.123 + i, "corr": "c-1", "rid": f"r{i}", "actor": "Me@x.com", "via": "pat", "client": "claude-code/2.1",
            "tool": "search_tools", "backend": "gateway", "orig": "search_tools", "args": {"query": "응력", "password": "pw"},
            "result": f"결과 {i} Bearer abc", "result_chars": 50, "result_sha256": f"h{i}", "is_error": False, "ms": 12, **over}


def test_게이트웨이_창고를_쪽마다_넣고_자리를_쓴_뒤_ack_한다(s, st):
    seen = []

    def handler(req: httpx.Request):
        seen.append((req.method, req.url.path, dict(req.url.params), req.headers.get("authorization")))
        if req.url.path == "/internal/interactions":
            if "cursor" not in req.url.params:
                return httpx.Response(200, json={"events": [_spool_event(1), _spool_event(2, via="chat"),
                                                            _spool_event(9, tool="share_conversation", orig="_gateway", args={"messages": []})],
                                                 "next_cursor": "c1", "more": True})
            return httpx.Response(200, json={"events": [_spool_event(3, is_error=True, args="앞부분 글 password=x", args_chars=2_000_000)],
                                             "next_cursor": "c2", "more": False})
        if req.url.path == "/internal/interactions/ack":
            return httpx.Response(200, json={"ok": True})
        return httpx.Response(404)

    async def go():
        async with _gw(handler) as cli:
            return await collector._ingest_gateway(s, st, cli, lambda e: "CAEG", collector.AckState())
    import asyncio
    assert asyncio.run(go()) == 3, "share_conversation 호출 줄은 건너뛴다 — 같은 대화가 공유 창구로 shared_sessions 에 든다"
    assert [(m, p) for m, p, _, _ in seen] == [("GET", "/internal/interactions"), ("POST", "/internal/interactions/ack"),
                                              ("GET", "/internal/interactions"), ("POST", "/internal/interactions/ack")]
    assert all(a == "Bearer sek" for *_, a in seen), "서비스 자격(GATEWAY_SHARED_TOKEN = 게이트웨이 GW_TOKEN)"
    assert seen[2][2]["cursor"] == "c1" and st.cursor("gateway") == "c2"
    items = st.search(actor="me@x.com", surface="mcp_call")["items"]
    assert {i["via"] for i in items} == {"pat", "chat"}, "via 는 게이트웨이 낱말 그대로 — 개인 Claude 와 포털이 대신 부른 것을 가른다"
    assert not [i for i in items if i["tool"] == "share_conversation"]
    full = st.get(next(i["id"] for i in items if i["status"] == "error"))
    assert full["client"] == "claude-code/2.1" and full["corr"] == "c-1" and full["output_chars"] == 50 and full["output_sha256"] == "h3"
    assert full["ts"] == 1003 and full["input"] == "앞부분 글 password=x" and full["meta"]["args_chars"] == 2_000_000, "1 MB 넘는 args 는 글로 온다"
    assert "Bearer <가림:bearer>" in full["output"], "포털이 넣기 전에 한 번 더 가린다"
    one = st.get(next(i["id"] for i in items if i["via"] == "pat" and i["status"] == "ok"))
    assert '"password": "<가림:password>"' in one["input"]
    assert asyncio.run(go()) == 0, "자리부터 다시 읽어도(같은 줄이 또 와도) 둘이 되지 않는다"


@pytest.mark.parametrize(("resp", "capture", "kind"), [(httpx.Response(404), True, "pending"), (httpx.Response(405), True, "pending"),
                                                       (httpx.Response(401), False, "pending"), (httpx.Response(403), False, "pending"),
                                                       (httpx.Response(401), True, "error"), (httpx.Response(200, json=[1]), True, "error")])
def test_게이트웨이_창구가_없거나_캡처가_꺼졌으면_기다리고_켰는데_자격이_틀리면_실패다(s, st, resp, capture, kind):
    """게이트웨이는 캡처가 꺼졌으면 내부 창구를 일반 인증으로 보내 401 이다 — 공유 비밀이 틀린 것과 같은 꼴이라 /health 의 enabled 로 가른다."""
    import asyncio

    async def go():
        async with _gw(lambda req: resp) as cli:
            await collector._ingest_gateway(s, st, cli, lambda e: None, collector.AckState(), capture)
    exc = collector.Pending if kind == "pending" else collector.IngestError
    with pytest.raises(exc):
        asyncio.run(go())


def test_게이트웨이가_모르는_ack_자리는_되풀이해_보내지_않는다(s, st):
    import asyncio
    acks = []

    def handler(req):
        if req.url.path == "/internal/interactions/ack":
            acks.append(json.loads(req.content)["cursor"])
            return httpx.Response(400, json={"error": "unknown cursor"})
        return httpx.Response(200, json={"events": [], "next_cursor": "c9", "more": False})
    ack = collector.AckState()

    async def go():
        async with _gw(handler) as cli:
            await collector._ingest_gateway(s, st, cli, lambda e: None, ack)
    asyncio.run(go())
    asyncio.run(go())
    assert acks == ["c9"] and ack.cursor == "c9"


def test_게이트웨이가_내려가_있으면_기다리고_공유_비밀이_없으면_실패다(s, st):
    import asyncio

    def down(req):
        raise httpx.ConnectError("refused", request=req)

    async def go(settings, handler):
        async with _gw(handler) as cli:
            await collector._ingest_gateway(settings, st, cli, lambda e: None, collector.AckState())
    with pytest.raises(collector.Pending):
        asyncio.run(go(s, down))
    with pytest.raises(collector.IngestError, match="GATEWAY_SHARED_TOKEN"):
        asyncio.run(go(s.model_copy(update={"gateway_shared_token": ""}), down))


def test_도구_검색_질의는_뒤이은_호출이_붙으면_바꿔_쓰고_같으면_쓰지_않는다(s, st):
    import asyncio
    rows = [{"id": "q1", "ts": 1000, "d": "2026-11-24", "q": "응력 해석", "mode": "kw", "top": ["a:b", "c:d"]}]
    params = []

    def handler(req):
        params.append(dict(req.url.params))
        return httpx.Response(200, json={"searches": rows})

    async def go():
        async with _gw(handler) as cli:
            return await collector._ingest_tool_search(s, st, cli, {})
    assert asyncio.run(go()) == 1 and params[0]["days"] == "30", "처음은 30일 전부"
    assert asyncio.run(go()) == 0, "같으면 쓰지 않는다"
    rows[0]["outcomes"] = [{"t": "a:b", "r": 1, "ok": True}]
    assert asyncio.run(go()) == 1
    ev = st.get(st.search(surface="tool_search")["items"][0]["id"])
    assert ev["input"] == "응력 해석" and ev["output"] == "a:b\nc:d" and ev["meta"]["outcomes"][0]["ok"] is True and ev["actor"] is None


def test_도구_검색_질의가_한도만큼_오면_놓쳤을_수_있다고_남긴다(s, st):
    import asyncio
    rows = [{"id": f"q{i}", "ts": 1000 + i, "q": "x"} for i in range(collector.SEARCH_LIMIT)]
    notes: dict = {}

    async def go():
        async with _gw(lambda req: httpx.Response(200, json={"searches": rows})) as cli:
            return await collector._ingest_tool_search(s, st, cli, notes)
    asyncio.run(go())
    assert "게이트웨이에 청할 것" in notes["tool_search"]


# ── 한 주기 · 상태 코드(IX-9) ─────────────────────────────────────────────────
def test_한_주기는_원천_하나의_실패가_다른_원천을_막지_않고_상태를_남긴다(s, st):
    import asyncio
    a = _app()

    def handler(req):
        if req.url.path == "/health":
            return httpx.Response(200, json={"interactions": {"enabled": True, "dropped": 0, "spool_bytes": 1}})
        if req.url.path == "/search-log":
            return httpx.Response(401)
        return httpx.Response(404)

    async def go():
        async with _gw(handler) as cli:
            return await collector.run_once(a, s, st, client=cli)
    out = asyncio.run(go())
    assert out["gateway"]["pending"] and out["tool_search"]["error"] and out["conversations"] == 0 and out["procedures"] == 0
    stt = a.state.interactions_status
    assert stt["gateway"]["pending"] and stt["tool_search"]["fails"] == 1 and stt["conversations"]["last_ok"]
    a.state.interactions_task = types.SimpleNamespace(done=lambda: False)
    a.state.interactions_started = time.time()
    for _ in range(2):
        asyncio.run(go())
    assert collector.problems(a, s) == ["failing:tool_search"]
    ok, body = collector.health(a, s)
    assert not ok and body["sources"]["gateway"]["state"] == "pending" and body["sources"]["conversations"]["state"] == "ok"
    assert "sek" not in json.dumps(body) and "gw.test" not in json.dumps(body), "무인증 본문에 비밀 · 주소가 없다"


def test_상태_코드_멈춤_넘침_꺼짐_죽음(s):
    a = _app()
    now = time.time()
    a.state.interactions_task = types.SimpleNamespace(done=lambda: False)
    a.state.interactions_started = now - 10_000
    a.state.interactions_status = collector._new_status()
    for src in collector.SOURCES:
        a.state.interactions_status[src]["last_ok"] = now
    assert collector.problems(a, s, now=now) == []
    a.state.interactions_status["procedures"]["last_ok"] = now - 10_000
    a.state.interactions_status["gateway"].update(last_ok=None, pending="캡처 꺼짐")
    assert collector.problems(a, s, now=now) == ["stalled:procedures"], "기다림(pending)은 멈춤이 아니다"
    a.state.interactions_spool = {"dropped": 3, "errors": 1, "oldest_ts": now - 7200}
    assert {"spool_dropped", "spool_errors", "spool_old"} <= set(collector.problems(a, s, now=now))
    a.state.interactions_task = types.SimpleNamespace(done=lambda: True)
    assert "collector_dead" in collector.problems(a, s, now=now)
    assert collector.problems(a, s.model_copy(update={"interactions_ingest_s": 0}), now=now) == ["collector_off"]


# ── 기록 파일 풀이(M2) ─────────────────────────────────────────────────────────
TRANSCRIPT = "\n".join([
    json.dumps({"type": "summary", "summary": "힌지 강도 검토"}),
    json.dumps({"type": "user", "sessionId": "sess-1", "version": "2.1.300", "timestamp": "2026-11-24T01:00:00Z",
                "message": {"role": "user", "content": "힌지 응력 봐 줘. Bearer abcdef123"}}, ensure_ascii=False),
    json.dumps({"type": "assistant", "sessionId": "sess-1", "message": {"role": "assistant", "content": [
        {"type": "text", "text": "조회합니다"},
        {"type": "tool_use", "id": "t1", "name": "mcp__hwax__search_tools", "input": {"query": "응력", "api_key": "k-1"}}]}}, ensure_ascii=False),
    json.dumps({"type": "user", "sessionId": "sess-1", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "t1", "content": [{"type": "text", "text": "결과 eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ4In0.c2ln"}]}]}},
               ensure_ascii=False),
    "이건 JSON 이 아니다 password=hunter2 Bearer zzz999",
    json.dumps({"type": "system", "content": "x"}),
]) + "\n"


def test_기록_파일에서_글과_도구_호출을_꺼내고_원문은_가린_채_둔다():
    p = tx.parse(TRANSCRIPT)
    assert [m["role"] for m in p["messages"]] == ["user", "assistant", "tool"]
    assert p["messages"][1]["tools"] == ["mcp__hwax__search_tools"] and "[도구 호출 mcp__hwax__search_tools]" in p["messages"][1]["content"]
    assert p["session_id"] == "sess-1" and p["title"] == "힌지 강도 검토" and p["client"] == "Claude Code 2.1.300"
    assert p["lines"] == 6 and p["skipped"] == 2, "모르는 줄은 세기만 한다(원문에는 남는다)"
    for secret in ("abcdef123", "k-1", "eyJhbGci", "zzz999"):
        assert secret not in p["raw"] and secret not in json.dumps(p["messages"], ensure_ascii=False), secret
    assert len(p["raw"].splitlines()) == 6 and "<가림:api_key>" in p["raw"]


# ── 창구(contract §5 · §6) ─────────────────────────────────────────────────────
PW = "pw123456"
ROUTES = [("GET", "/interactions/status"), ("POST", "/interactions/share"), ("GET", "/interactions/me"),
          ("DELETE", "/interactions/me"), ("GET", "/interactions/me/x"), ("GET", "/interactions/admin/search"),
          ("GET", "/interactions/admin/x"), ("GET", "/health/interactions")]


def _login(c, email) -> dict:
    c.cookies.clear()
    assert c.post("/auth/local/login", json={"email": email, "password": PW}).status_code == 200
    return {"X-CSRF-Token": c.cookies.get(CSRF_COOKIE)}


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.delenv("PORTAL_ADMIN_EMAILS", raising=False)
    cfg = Settings(_env_file=None, user_store_path=str(tmp_path / "users.sqlite"), token_store_path=str(tmp_path / "tokens.sqlite"),
                   conv_store_path=str(tmp_path / "conv.sqlite"), procedures_store_path=str(tmp_path / "procedures.sqlite"),
                   conn_key_path=str(tmp_path / "conn.key"), local_bootstrap_admins="boss@example.com",
                   interactions_enabled=True, interactions_store_path=str(tmp_path / "ix.sqlite"), interactions_share_max_mb=1,
                   mcp_gateway_url="http://127.0.0.1:9")
    box = {"s": cfg}
    app.dependency_overrides[get_settings] = lambda: box["s"]
    from app.auth.routes.local import _rl
    _rl.clear()
    with TestClient(app) as c:
        keep = app.state.user_store
        app.state.user_store = UserStore(cfg)
        for email in ("boss@example.com", "me@example.com", "peer@example.com"):
            assert c.post("/auth/local/signup", json={"email": email, "name": email.split("@")[0], "password": PW}).status_code < 300
        for email in ("me@example.com", "peer@example.com"):
            assert app.state.user_store.approve(email, by="boss@example.com", groups=[])
        hb = _login(c, "boss@example.com")
        for email in ("me@example.com", "peer@example.com"):
            assert c.patch(f"/auth/access/users/{email}", json={"affiliation": "CAEG"}, headers=hb).status_code == 200
        c.cookies.clear()
        yield c, box
        if app.state.interaction_store is not None:
            app.state.interaction_store.close()
            app.state.interaction_store = None
        app.state.user_store = keep
    app.dependency_overrides.pop(get_settings, None)


def test_꺼진_박스는_모든_창구가_404_이고_ready_답이_그대로다(env):
    c, box = env
    box["s"] = box["s"].model_copy(update={"interactions_enabled": False})
    h = _login(c, "me@example.com")
    for method, path in ROUTES:
        r = c.request(method, path, headers=h, json={})
        assert r.status_code == 404, (method, path, r.status_code)
    assert "interactions" not in c.get("/health/ready").json(), "꺼진 박스의 ready 답에 새 칸이 없다"
    assert c.get("/auth/pat/share").json() == {"portal": False, "capture": None}
    assert app.state.interaction_store is None, "꺼진 박스는 원장 파일을 열지 않는다"


def test_공유는_세션이면_CSRF_가_있어야_하고_같은_세션은_덮어쓴다(env):
    c, _ = env
    h = _login(c, "me@example.com")
    body = {"session_id": "s1", "title": "힌지", "messages": [{"role": "user", "content": "질문 Bearer tok123"},
                                                             {"role": "assistant", "content": "답"}]}
    assert c.post("/interactions/share", json=body).status_code == 403, "세션은 CSRF 없이 쓰지 못한다"
    r = c.post("/interactions/share", json=body, headers=h)
    assert r.status_code == 200 and r.json()["created"] and r.json()["kind"] == "tool" and r.json()["messages"] == 2, r.text
    r2 = c.post("/interactions/share", json={**body, "messages": body["messages"][:1]}, headers=h)
    assert r2.json()["id"] == r.json()["id"] and not r2.json()["created"] and r2.json()["messages"] == 1, "같은 session_id 는 덮어쓴다"
    mine = c.get("/interactions/me", params={"surface": "shared_claude"}).json()["items"]
    assert len(mine) == 1 and mine[0]["client"] == "share_conversation"
    full = c.get(f"/interactions/me/{mine[0]['id']}").json()
    assert full["shared"]["messages"] == [{"role": "user", "content": "질문 Bearer <가림:bearer>"}]
    for bad in ({}, {"messages": body["messages"], "transcript": "x"}, {"messages": [{"role": "system", "content": "x"}]}):
        assert c.post("/interactions/share", json=bad, headers=h).status_code == 422, bad


def test_공유는_PAT_로_받고_기록_파일_원문도_가린_채_둔다(env):
    c, _ = env
    h = _login(c, "me@example.com")
    pat = c.post("/auth/pat", json={"name": "t"}, headers=h).json()["token"]
    c.cookies.clear()
    r = c.post("/interactions/share", json={"transcript": TRANSCRIPT}, headers={"Authorization": f"Bearer {pat}"})
    assert r.status_code == 200, r.text
    got = r.json()
    assert got["session_id"] == "sess-1" and got["kind"] == "transcript" and got["messages"] == 3 and got["skipped"] == 2
    auth = {"Authorization": f"Bearer {pat}"}
    eid = c.get("/interactions/me", headers=auth).json()["items"][0]["id"]
    raw = c.get(f"/interactions/me/{eid}", params={"raw": 1}, headers=auth)
    assert raw.status_code == 200 and "<가림:api_key>" in raw.text and "k-1" not in raw.text


def test_공유_본문이_상한을_넘으면_413(env):
    c, _ = env
    h = _login(c, "me@example.com")
    big = json.dumps({"transcript": "x" * (1024 * 1024 + 10)})
    r = c.post("/interactions/share", content=big, headers={**h, "content-type": "application/json"})
    assert r.status_code == 413


def test_내_기록은_내_것만_보이고_지우기는_확인_글이_있어야_한다(env):
    c, box = env
    from app.interactions.routes import store_of
    st = store_of(app, box["s"])
    st.put_events([{"ts": 10, "surface": "mcp_call", "actor": "peer@example.com", "output": "남의 것", "source": "gateway", "source_ref": "p1"},
                   {"ts": 11, "surface": "mcp_call", "actor": "me@example.com", "output": "내 것", "source": "gateway", "source_ref": "m1"}])
    h = _login(c, "me@example.com")
    items = c.get("/interactions/me").json()["items"]
    assert [i["output_preview"] for i in items] == ["내 것"]
    other = st.search(actor="peer@example.com")["items"][0]["id"]
    assert c.get(f"/interactions/me/{other}").status_code == 404, "남의 기록은 없는 것과 같다"
    assert c.request("DELETE", "/interactions/me", json={}, headers=h).status_code == 422
    r = c.request("DELETE", "/interactions/me", json={"confirm": "전부 지웁니다"}, headers=h)
    assert r.status_code == 200 and r.json()["events"] == 1
    assert c.get("/interactions/me").json()["items"] == [] and st.search(actor="peer@example.com")["items"]


def test_분석가는_grant_only_이고_검색_원문_열기마다_감사_한_줄(env):
    c, box = env
    from app.interactions.routes import store_of
    st = store_of(app, box["s"])
    st.put_events([{"ts": 10, "surface": "mcp_call", "actor": "peer@example.com", "output": "남의 원문", "source": "gateway", "source_ref": "p1"}])
    hb = _login(c, "boss@example.com")
    assert c.get("/interactions/admin/search").status_code == 403, "관리자 전권에 딸려 오지 않는다"
    assert c.get("/interactions/status").json()["analyst"] is False
    assert c.patch("/auth/access/users/boss@example.com", json={"grants": ["feat:interaction-analyst"]}, headers=hb).status_code == 200
    _login(c, "boss@example.com")
    r = c.get("/interactions/admin/search", params={"actor": "peer@example.com"})
    assert r.status_code == 200 and r.json()["items"][0]["output_preview"] == "남의 원문"
    eid = r.json()["items"][0]["id"]
    assert c.get(f"/interactions/admin/{eid}").json()["output"] == "남의 원문"
    rows = st.audit_rows()
    assert [(x["action"], x["viewer"], x["owner"]) for x in rows] == [("open", "boss@example.com", "peer@example.com"),
                                                                      ("search", "boss@example.com", "peer@example.com")]
    assert rows[0]["event_id"] == eid
    me = _login(c, "me@example.com")
    assert me and c.get("/interactions/admin/search").status_code == 403, "CAEG(전부)여도 분석가가 아니다"
    assert c.get("/interactions/status").json()["analyst"] is False


def test_켜진_박스의_상태_답과_ready_와_상태판_줄(env):
    c, _ = env
    _login(c, "me@example.com")
    got = c.get("/interactions/status").json()
    assert got["enabled"] and "지정 분석가만" in got["notice"] and got["share_max_mb"] == 1 and "health" not in got
    assert "health" not in c.get("/interactions/status", params={"detail": 1}).json(), "분석가 · 관리자가 아니면 수집 상태를 싣지 않는다"
    _login(c, "boss@example.com")
    assert "health" not in c.get("/interactions/status").json(), "헤더가 화면마다 묻는 답에는 싣지 않는다(수 세기는 표를 훑는다)"
    got = c.get("/interactions/status", params={"detail": 1}).json()
    assert got["health"]["problems"] == ["collector_off"] and got["counts"] == {"events": 0, "shared": 0}
    r = c.get("/health/interactions")
    assert r.status_code == 503 and r.json()["problems"] == ["collector_off"], "켰는데 수집기 주기가 0(conftest) — 아무것도 안 쌓이니 붉다"
    assert c.get("/health/ready").json()["interactions"] == {"ok": False, "problems": ["collector_off"]}


# ── 중계가 턴 메타를 남긴다(S2) — 켠 박스에서만 ──────────────────────────────────
def test_중계는_켠_박스에서만_답_meta_turn_에_모델_자기검증_확인_카드를_남긴다():
    from tests.test_pinned_agent_persist import relay_turn, sse
    turn = (sse("meta", {"models": {"qwen": 2}, "chat_model": "qwen", "self_check": {"status": "ok"}, "junk": 1})
            + sse("confirm", {"tool": "submit_job", "args": {"x": 1}}) + sse("result", {"type": "text", "content": "답"}) + sse("done", {}))
    off = relay_turn(turn)
    assert off[1]["meta"] is None, "꺼진 박스의 서버 사본은 종전 그대로"
    s_on = get_settings().model_copy(update={"interactions_enabled": True})
    app.dependency_overrides[get_settings] = lambda: s_on
    try:
        on = relay_turn(turn)
    finally:
        app.dependency_overrides.pop(get_settings, None)
    assert on[1]["meta"] == {"turn": {"models": {"qwen": 2}, "chat_model": "qwen", "self_check": {"status": "ok"},
                                      "confirm": [{"tool": "submit_job", "args": {"x": 1}}]}}
