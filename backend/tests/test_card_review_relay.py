# 카드 대조 중계(/agent/card-review/*) — 신원 덮어쓰기·본문 그대로·크기 경계·권한 문·감사·오류 어휘·전용 풀·끊김 전파를 본다
"""리스크 심사 재설계 M2 · WP3a P1. 리스크 앱 러너 → 포털 /agent/card-review/{limits|pack|plan|run} → 에이전트 서버 /card-review/*.

포털은 본문을 통째로 넘기고 신원 칸 넷(groups·user_email·user_pat·entitlements)만 검증된 주체로 덮어쓴다. 에이전트 서버는
httpx.MockTransport 로 흉내 낸다 — 엔진(HWAXAgentServer card_review)이 떠 있지 않아도 계약(docs/risk-review-redesign/M2.md
4.3·4.4)으로 본다. WP5b C7 포털 단언 ①~⑤, P-14(챗과 연결·퍼밋을 다투지 않는다), M2 나갈 기준 3(대화를 만들지 않는다)을 같이
고정한다. 끊김 전파는 TestClient 가 아니라 ASGI 를 직접 불러 본다 — TestClient 는 응답을 끝까지 모은 뒤 돌려주므로 앱 쪽이 도중에
떠나는 일을 만들지 못한다.
"""
import asyncio
import contextlib
import hashlib
import json

import httpx
import jwt
import pytest
from fastapi.testclient import TestClient

from app.agent.routes import _WINDOW_CHARS
from app.auth.provider import Principal
from app.config import Settings, get_settings
from app.deps import principal_pat_or_session
from app.main import _agent_timeout, app

_WHO = Principal(subject="u1", email="u1@hwax.local", display_name="U",
                 groups=["eng-team", "feat:deliberation", "plat:aidatahub"])
_IDENT = ("groups", "user_email", "user_pat", "entitlements")
_CANARY = "CANARY-7f3a19c2"
_JSON = {"content-type": "application/json"}

# run 요청(M2.md 4.3) — 선언하지 않은 칸(future_field)과 호출자가 자칭한 신원 넷을 같이 싣는다.
_RUN = {
    "kind": "verdict", "variant": "fwd", "target_key": "T-1",
    "expert": {"key": "mech-a", "name": "기구 A", "domain": "mech", "role": "힌지 «원문» 담당"},
    "cards": [{"alias": "K01", "record_id": "DOC-1", "text": f"유효 접착폭은 0.8 mm 를 하한으로 — {_CANARY}"}],
    "digest": [],
    "unit": {"unit_id": "U-03", "kind": "change", "title": "힌지", "summary": "",
             "lines": [{"ref": "c:ab12", "text": "두께 0.5→0.4 mm"}], "context": [], "evidence": [],
             "notes": "", "missing": []},
    "manifest": [], "extra": {"domains": [], "mechanisms": [], "known": []},
    "expect": {"prompt_rev": "cr-verdict-1", "limits_rev": "a1b2c3d4"},
    "future_field": {"nested": [1, 2.5, None, True, "한글"]},
    "groups": ["portal-admin"], "entitlements": ["feat:deliberation", "feat:admin"],
    "user_email": "boss@hwax.local", "user_pat": "forged-token",
}
_BODY = {"pack": {**_RUN, "agent_key": "mech-a"}, "plan": _RUN, "run": _RUN}

# 엔진 run 의 SSE — 청크 경계를 프레임·한글 글자 가운데에 둔다(릴레이가 실제로 받는 모양).
_SSE = ('event: status\ndata: {"step": "attempt", "n": 1}\n\n'
        'event: ping\ndata: {"idle_s": 15, "ts": 1}\n\n'
        'event: result\ndata: {"kind": "verdict", "rows": [{"k": "K01", "why": "접착폭 하한 미달"}]}\n\n'
        'event: done\ndata: {}\n\n').encode()


class _Audit:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def record(self, **kw) -> None:
        self.rows.append(kw)


class _Stream(httpx.AsyncByteStream):
    """상류 SSE 본문 — 조각을 내고, 주면 끝에 예외를 던진다. 닫혔는지 적는다."""

    def __init__(self, parts: list[bytes], then: Exception | None = None) -> None:
        self.parts, self.then, self.closed = parts, then, False

    async def __aiter__(self):
        for p in self.parts:
            yield p
        if self.then is not None:
            raise self.then

    async def aclose(self) -> None:
        self.closed = True


class _Agent:
    """에이전트 서버 대역 — 받은 요청을 적고 답한다."""

    def __init__(self, answer) -> None:
        self.seen: list[httpx.Request] = []
        self.answer = answer

    def __call__(self, req: httpx.Request) -> httpx.Response:
        self.seen.append(req)
        return self.answer(req)


def _sse_ok(req: httpx.Request | None = None) -> httpx.Response:
    return httpx.Response(200, headers={"content-type": "text/event-stream"},
                          stream=_Stream([_SSE[:7], _SSE[7:90], _SSE[90:131], _SSE[131:]]))


def _ok(req: httpx.Request) -> httpx.Response:
    return _sse_ok() if req.url.path.endswith("/run") else httpx.Response(200, json={"ok": True, "path": req.url.path})


def _wire(answer=_ok, *, read: float = 46800.0) -> _Agent:
    agent = _Agent(answer)
    app.state.card_review_client = httpx.AsyncClient(transport=httpx.MockTransport(agent),
                                                     timeout=httpx.Timeout(30.0, read=read))
    return agent


def _call(c: TestClient, route: str, body: dict | bytes | None = None) -> httpx.Response:
    if route == "limits":
        return c.get("/agent/card-review/limits")
    raw = body if isinstance(body, bytes) else json.dumps(_BODY[route] if body is None else body,
                                                          ensure_ascii=False).encode()
    return c.post(f"/agent/card-review/{route}", content=raw, headers=_JSON)


def _frames(raw: bytes) -> list[tuple[str, dict]]:
    out = []
    for blk in raw.decode(errors="replace").split("\n\n"):
        ev = [ln[6:].strip() for ln in blk.split("\n") if ln.startswith("event:")]
        data = [ln[5:].strip() for ln in blk.split("\n") if ln.startswith("data:")]
        if ev and data:
            try:
                out.append((ev[0], json.loads(data[0])))
            except ValueError:
                out.append((ev[0], {"_broken": data[0]}))
    return out


def _strip(d: dict) -> dict:
    return {k: v for k, v in d.items() if k not in _IDENT}


@pytest.fixture
def portal():
    app.dependency_overrides[principal_pat_or_session] = lambda: _WHO
    try:
        with TestClient(app) as c:
            keep = ("card_review_client", "card_review_semaphore", "agent_client", "agent_semaphore", "agent_audit")
            saved = {k: getattr(app.state, k) for k in keep}
            app.state.agent_audit = _Audit()
            try:
                yield c
            finally:
                for k, v in saved.items():
                    setattr(app.state, k, v)
    finally:
        app.dependency_overrides.pop(principal_pat_or_session, None)
        app.dependency_overrides.pop(get_settings, None)


def _rows() -> list[dict]:
    return app.state.agent_audit.rows


# ── ①② 본문은 그대로, 신원 칸 넷만 포털의 것 ─────────────────────────────────────────────


@pytest.mark.parametrize("route", ["pack", "plan", "run"])
def test_나간_본문은_받은_본문과_신원_칸_넷만_다르고_자칭_신원은_버려진다(portal, route):
    agent = _wire()
    r = _call(portal, route)
    assert r.status_code == 200
    (req,) = agent.seen
    assert (req.method, req.url.path) == ("POST", f"/card-review/{route}")
    sent = json.loads(req.content)
    assert _strip(sent) == _strip(_BODY[route]), "신원 칸 말고는 한 칸도 바뀌거나 빠지면 안 된다(선언하지 않은 칸 포함)"
    # 권한 상승 시험 — 호출자가 실어 보낸 portal-admin·feat:admin·남의 이메일·위조 토큰이 하나도 가지 않는다.
    assert sent["groups"] == _WHO.groups
    assert sent["user_email"] == "u1@hwax.local"
    assert sent["entitlements"] == ["feat:deliberation", "plat:aidatahub"], "합성 그룹만, 정렬해서"
    assert sent["user_pat"] != "forged-token"
    claims = jwt.decode(sent["user_pat"], app.state.keystore.public_pem(app.state.keystore.active_kid),
                        algorithms=["RS256"], audience=get_settings().pat_chat_audience)
    assert claims["sub"] == "u1" and claims["scopes"] == ["chat"], "이 사람 이름의 챗 PAT 이다(서비스 계정이 아니다)"


def test_자칭_신원이_없어도_신원_칸_넷이_붙는다(portal):
    agent = _wire()
    body = _strip(_RUN)
    assert _call(portal, "run", body).status_code == 200
    sent = json.loads(agent.seen[0].content)
    assert set(_IDENT) <= set(sent) and _strip(sent) == body


def test_limits_는_GET_이고_본문을_싣지_않는다(portal):
    agent = _wire()
    r = _call(portal, "limits")
    assert r.status_code == 200 and r.json() == {"ok": True, "path": "/card-review/limits"}
    (req,) = agent.seen
    assert (req.method, req.url.path, req.content) == ("GET", "/card-review/limits", b"")


def test_run_은_바이트를_그대로_흘린다(portal):
    _wire()
    r = _call(portal, "run")
    assert r.status_code == 200
    assert r.content == _SSE, "프레임을 만들지도 삼키지도 않는다(ping 도 엔진 것 그대로) — 한글 글자 가운데의 청크 경계도 그대로"
    assert r.headers["content-type"].startswith("text/event-stream") and r.headers["x-accel-buffering"] == "no"


# ── ③ 크기 경계 — 창 하나(_WINDOW_CHARS 바이트) ───────────────────────────────────────────


def _sized(n: int) -> bytes:
    """정확히 n 바이트인 JSON 객체."""
    head, tail = b'{"kind":"sweep","pad":"', b'"}'
    return head + b"x" * (n - len(head) - len(tail)) + tail


@pytest.mark.parametrize("route", ["pack", "plan", "run"])
def test_본문_상한은_창_하나다_상한은_통과하고_하나_넘으면_413(portal, route):
    agent = _wire()
    assert _WINDOW_CHARS == 4_194_304, "설계서의 600,000자 상한이 아니라 1M 토큰 창 하나다(D-21)"
    assert _call(portal, route, _sized(_WINDOW_CHARS)).status_code == 200
    assert len(agent.seen) == 1
    r = _call(portal, route, _sized(_WINDOW_CHARS + 1))
    assert r.status_code == 413
    assert r.json()["code"] == "body_too_large" and r.json()["max_bytes"] == _WINDOW_CHARS
    assert len(agent.seen) == 1, "넘는 본문은 에이전트 서버로 가지 않는다"
    assert _rows()[-1]["event"] == f"card_review_{route}_error" and _rows()[-1]["status"] == "rejected"


def test_길이를_밝히지_않은_본문도_상한에서_멈춘다(portal):
    """Content-Length 없이(청크 전송) 오는 본문은 읽으면서 잰다 — 앞단 nginx 는 2GB 까지 받는다."""
    agent = _wire()
    raw = _sized(_WINDOW_CHARS + 1)
    r = portal.post("/agent/card-review/run", content=iter([raw[i:i + (1 << 20)] for i in range(0, len(raw), 1 << 20)]),
                    headers=_JSON)
    assert r.status_code == 413 and agent.seen == []


@pytest.mark.parametrize("raw", [b"", b"not json", b"[1, 2]", b'"x"', b"[" * 100_000])
def test_JSON_객체가_아니면_422_bad_request(portal, raw):
    agent = _wire()
    r = _call(portal, "run", raw)
    assert r.status_code == 422 and r.json()["code"] == "bad_request" and agent.seen == []


# ── ④ 권한 문 ──────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("route", ["limits", "pack", "plan", "run"])
def test_feat_deliberation_이_없으면_403_이고_아무것도_안_나간다(portal, route):
    app.dependency_overrides[principal_pat_or_session] = lambda: Principal(
        subject="u2", email="u2@hwax.local", groups=["eng-team", "feat:chat"])
    agent = _wire()
    r = _call(portal, route)      # 본문은 entitlements 에 feat:deliberation 을 자칭한다 — 그래도 막힌다
    assert r.status_code == 403
    assert agent.seen == [], "권한 없는 요청은 에이전트 서버로 한 바이트도 안 나간다(pack 은 카드 원문을 돌려준다)"


# ── ⑤ 감사 ─────────────────────────────────────────────────────────────────────────


def test_감사_행에는_식별자와_크기_해시_상류_상태만_있고_본문은_없다(portal):
    agent = _wire()
    raw = json.dumps(_RUN, ensure_ascii=False).encode()
    pack_raw = json.dumps(_BODY["pack"], ensure_ascii=False).encode()
    assert _call(portal, "run", raw).status_code == 200
    assert _call(portal, "pack", pack_raw).status_code == 200
    assert _call(portal, "limits").status_code == 200
    rows = _rows()
    assert [(r["event"], r.get("status")) for r in rows] == [
        ("card_review_run_start", None), ("card_review_run_done", "ok"),
        ("card_review_pack_done", "ok"), ("card_review_limits_done", "ok")]
    start = {"kind": "verdict", "agent": "mech-a", "unit": "U-03", "bytes": len(raw),
             "sha256": hashlib.sha256(raw).hexdigest()}
    assert rows[0]["meta"] == start, "sha256 은 받은 원 본문의 것이다 — 앱이 보낸 바이트와 맞춰 볼 수 있다"
    assert rows[1]["meta"] == {**start, "upstream": 200}
    assert rows[2]["meta"]["agent"] == "mech-a" and rows[2]["meta"]["sha256"] == hashlib.sha256(pack_raw).hexdigest()
    assert rows[3]["meta"] == {"upstream": 200}
    assert all(r["principal"] == "u1" for r in rows)
    dumped = json.dumps(rows, ensure_ascii=False)
    minted = json.loads(agent.seen[0].content)["user_pat"]
    for leak in (_CANARY, "두께", "forged-token", minted, "portal-admin"):
        assert leak not in dumped, f"감사에 본문·신원이 새었다: {leak[:20]}"


def test_감사의_식별자_칸으로_본문을_흘리지_못한다(portal):
    _wire()
    body = {**_RUN, "kind": "verdict" + "가" * 5000, "expert": {"key": _CANARY * 500}}
    assert _call(portal, "run", body).status_code == 200
    for r in _rows():
        assert len(r["meta"]["kind"]) <= 200 and len(r["meta"]["agent"]) <= 200


# ── 오류 어휘(M2.md 4.4) ────────────────────────────────────────────────────────────


@pytest.mark.parametrize("status,body,headers", [
    (422, {"code": "over_budget", "message": "창 초과", "need": 1_200_000, "have": 1_008_000, "part": "cards"}, {}),
    (422, {"detail": {"code": "unknown_fields", "fields": ["zzz"]}}, {}),
    (409, {"code": "rev_mismatch", "prompt_rev": "cr-verdict-2", "limits_rev": "ffff0000"}, {}),
    (429, {"code": "review_busy", "retry_after_s": 30}, {"Retry-After": "30"}),
    (403, {"code": "denied", "message": "feat:deliberation 없음"}, {}),
    (404, {"code": "agent_not_found", "message": "agent not found: x"}, {}),
    # 엔진이 code 를 실은 5xx — 앱이 팩 재시도로 가르는 어휘다. 502 agent_5xx 로 덮으면 구분이 사라진다.
    (503, {"code": "tools_unavailable", "missing": ["get_record"]}, {}),
    (502, {"code": "card_fetch_failed", "failed": ["DOC-9"]}, {}),
])
@pytest.mark.parametrize("route", ["limits", "pack", "plan", "run"])
def test_에이전트_서버가_code_를_실은_오류는_상태와_본문_그대로_간다(portal, route, status, body, headers):
    agent = _wire(lambda req: httpx.Response(status, json=body, headers=headers))
    r = _call(portal, route)
    code = body.get("code") or body["detail"]["code"]
    assert r.status_code == status and r.json() == body, "앱이 code·need·have 를 읽는다 — 상태와 본문을 바꾸지 않는다"
    if headers:
        assert r.headers["retry-after"] == "30"
    assert len(agent.seen) == 1
    last = _rows()[-1]
    assert last["event"] == f"card_review_{route}_error" and last["status"] == "error"
    assert last["meta"]["upstream"] == status and last["meta"]["code"] == code


@pytest.mark.parametrize("route", ["limits", "pack", "plan", "run"])
def test_code_없는_404_는_옛_에이전트_서버다(portal, route):
    _wire(lambda req: httpx.Response(404, json={"detail": "Not Found"}))
    r = _call(portal, route)
    assert r.status_code == 404 and r.json()["code"] == "agent_outdated"
    assert _rows()[-1]["meta"]["code"] == "agent_outdated" and _rows()[-1]["meta"]["upstream"] == 404


def _raise(exc_type):
    def answer(req: httpx.Request) -> httpx.Response:
        raise exc_type("boom", request=req)
    return answer


@pytest.mark.parametrize("route", ["limits", "pack", "plan", "run"])
def test_상류_실패는_어휘의_상태와_code_로_나간다(portal, route):
    _wire(lambda req: httpx.Response(500, text=f"Traceback … {_CANARY}"))
    r = _call(portal, route)
    assert (r.status_code, r.json()["code"], r.json()["upstream"]) == (502, "agent_5xx", 500)
    assert _CANARY not in r.text, "상류 오류 본문은 되싣지 않는다"
    _wire(_raise(httpx.ConnectError))
    r = _call(portal, route)
    assert (r.status_code, r.json()["code"]) == (502, "agent_unreachable")
    _wire(_raise(httpx.PoolTimeout))
    r = _call(portal, route)
    assert (r.status_code, r.json()["code"], r.json()["retry_after_s"]) == (429, "engine_busy", 30), \
        "전용 풀이 찼다 — 엔진에 닿지도 않았으니 기다림 부류다"
    assert r.headers["retry-after"] == "30"


@pytest.mark.parametrize("route", ["limits", "pack", "plan"])
def test_단발_시간_초과는_504_agent_timeout_이고_기본값으로_진행하지_않는다(portal, route):
    _wire(_raise(httpx.ReadTimeout))
    r = _call(portal, route)
    got = r.json()
    assert r.status_code == 504 and got["code"] == "agent_timeout"
    assert got["knob"] == "AGENT_UNARY_TIMEOUT_S" and got["timeout_s"] == 600.0 and "600초" in got["message"]
    assert "기본값" not in got["message"], "도우미의 폴백 규칙(기본값으로 진행)을 따르지 않는다"
    assert _rows()[-1]["status"] == "error" and _rows()[-1]["meta"]["code"] == "agent_timeout"


def test_run_의_헤더_전_시간_초과도_504_다(portal):
    _wire(_raise(httpx.ReadTimeout), read=46800.0)
    r = _call(portal, "run")
    assert r.status_code == 504 and r.json()["knob"] == "AGENT_STREAM_IDLE_TIMEOUT_S"


def test_단발은_요청마다_AGENT_UNARY_TIMEOUT_S_이고_run_은_침묵_한도다(portal):
    seen: dict[str, dict] = {}

    def answer(req: httpx.Request) -> httpx.Response:
        seen[req.url.path] = req.extensions["timeout"]
        return _ok(req)

    _wire(answer, read=46800.0)
    for route in ("limits", "pack", "plan", "run"):
        assert _call(portal, route).status_code == 200
    for route in ("limits", "pack", "plan"):
        assert seen[f"/card-review/{route}"]["read"] == 600.0, route
    assert seen["/card-review/run"]["read"] == 46800.0, "run 은 바이트 사이 침묵 한도(13시간) — 엔진 ping 15초"


# ── run 스트림 — 침묵 한도·도중 끊김·엔진 오류 프레임 ─────────────────────────────────────


def _stream_answer(stream: _Stream):
    return lambda req: httpx.Response(200, headers={"content-type": "text/event-stream"}, stream=stream)


def test_침묵_한도에_걸리면_반쯤_온_프레임을_닫고_error_agent_stream_idle_과_done(portal):
    head = b'event: status\ndata: {"step": "attempt", "n": 1}\n\n'
    half = b'event: ping\ndata: {"idle_s": 1'                      # 반쯤 온 프레임에서 멈춘다
    stream = _Stream([head, half], then=httpx.ReadTimeout("idle"))
    _wire(_stream_answer(stream), read=0.4)
    r = _call(portal, "run")
    assert r.status_code == 200 and r.content.startswith(head + half + b"\n\n")
    frames = _frames(r.content)
    assert [e for e, _ in frames] == ["status", "ping", "error", "done"], "반쯤 온 조각이 중계의 error 프레임과 붙지 않는다"
    err = frames[2][1]
    assert err["code"] == "agent_stream_idle" and err["infra"] is True and err["retryable"] is True
    assert err["knob"] == "AGENT_STREAM_IDLE_TIMEOUT_S" and err["idle_s"] == 0.4
    assert stream.closed, "멈춘 엔진과의 연결을 닫는다 — 엔진이 LLM 을 거둔다"
    last = _rows()[-1]
    assert (last["event"], last["status"], last["meta"]["code"]) == ("card_review_run_error", "error", "agent_stream_idle")


def test_도중에_끊기면_error_agent_unreachable_과_done(portal):
    stream = _Stream([b'event: status\ndata: {"step": "attempt", "n": 1}\n\n'],
                     then=httpx.RemoteProtocolError("peer closed connection"))
    _wire(_stream_answer(stream))
    frames = _frames(_call(portal, "run").content)
    assert [e for e, _ in frames] == ["status", "error", "done"]
    assert frames[1][1]["code"] == "agent_unreachable" and frames[1][1]["infra"] is True
    assert stream.closed and _rows()[-1]["meta"]["code"] == "agent_unreachable"


def test_done_뒤에_끊기면_아무것도_덧붙이지_않는다(portal):
    stream = _Stream([_SSE], then=httpx.RemoteProtocolError("peer closed connection"))
    _wire(_stream_answer(stream))
    r = _call(portal, "run")
    assert r.content == _SSE
    assert _rows()[-1]["event"] == "card_review_run_done"


def test_엔진의_error_프레임은_그대로_가고_감사에_그_code_가_남는다(portal):
    body = (b'event: error\ndata: {"code": "review_busy", "message": "\xec\x9e\x90\xeb\xa6\xac \xec\x97\x86\xec\x9d\x8c", '
            b'"infra": false, "retryable": true, "retry_after_s": 30}\n\nevent: done\ndata: {}\n\n')
    _wire(_stream_answer(_Stream([body[:20], body[20:]])))
    r = _call(portal, "run")
    assert r.content == body
    last = _rows()[-1]
    assert (last["event"], last["meta"]["code"], last["meta"]["upstream"]) == ("card_review_run_error", "review_busy", 200)


def test_끝_프레임_없이_끝난_스트림은_감사에_끊김으로_남고_중계가_프레임을_지어내지_않는다(portal):
    head = b'event: status\ndata: {"step": "attempt", "n": 1}\n\n'
    _wire(_stream_answer(_Stream([head])))
    r = _call(portal, "run")
    assert r.content == head, "끊김을 알아보는 것은 앱이다(engine_stream_cut) — 중계는 done 을 지어내지 않는다"
    assert _rows()[-1]["meta"]["code"] == "engine_stream_cut"


# ── 자리 — 전용 세마포어·전용 풀(P-14)·퍼밋 반환 ─────────────────────────────────────────


def test_자리가_없으면_429_engine_busy_이고_아무것도_안_나간다(portal):
    agent = _wire()
    app.state.card_review_semaphore = asyncio.Semaphore(0)
    r = _call(portal, "run")
    assert r.status_code == 429
    got = r.json()
    assert got["code"] == "engine_busy" and got["retry_after_s"] == 30 and r.headers["retry-after"] == "30"
    assert "CARD_REVIEW_MAX_STREAMS" in got["message"]
    assert agent.seen == []
    last = _rows()[-1]
    assert (last["event"], last["status"], last["meta"]["code"]) == ("card_review_run_error", "rejected", "engine_busy")


def test_어느_끝에서든_퍼밋이_돌아온다(portal):
    """자리 하나로 끝 모양마다 두 번씩 부른다 — 하나라도 새면 둘째가 429 다."""
    answers = [_ok, lambda req: httpx.Response(422, json={"code": "over_budget"}),
               lambda req: httpx.Response(404, json={"detail": "Not Found"}),
               lambda req: httpx.Response(500), _raise(httpx.ConnectError),
               _stream_answer(_Stream([b"event: status\ndata: {}\n\n"], then=httpx.ReadTimeout("idle"))),
               _stream_answer(_Stream([b"event: status\ndata: {}\n\n"], then=httpx.RemoteProtocolError("cut")))]
    app.state.card_review_semaphore = asyncio.Semaphore(1)
    for answer in answers:
        _wire(answer)
        for _ in range(2):
            assert _call(portal, "run").status_code != 429


def test_챗이_꽉_차도_카드_대조는_제_풀로_가고_대화를_만들지_않는다(portal):
    """P-14 — 공유 클라이언트(max_concurrent_chats)를 같이 쓰면 챗이 차면 카드 대조가 연결을 못 얻는다. M2 나갈 기준 3 —
    카드 대조는 /agent/chat 을 타지 않으므로 포털 대화 목록에 새 대화가 생기지 않는다."""
    store = app.state.conv_store
    before = store.count_for_owner("u1")
    chat_calls: list[httpx.Request] = []
    app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(
        lambda req: chat_calls.append(req) or httpx.Response(500)))
    app.state.agent_semaphore = asyncio.Semaphore(0)                     # 챗 자리가 다 찼다
    assert portal.post("/agent/chat", json={"message": "x"}).status_code == 429
    agent = _wire()
    for route in ("limits", "pack", "plan", "run"):
        assert _call(portal, route).status_code == 200, route
    assert len(agent.seen) == 4 and chat_calls == [], "카드 대조는 챗 클라이언트를 한 번도 쓰지 않는다"
    assert store.count_for_owner("u1") == before, "카드 대조가 포털 대화를 만들었다"


def test_기동이_전용_클라이언트와_세마포어를_만든다():
    assert Settings(_env_file=None).card_review_max_streams == 12
    with TestClient(app):
        s = get_settings()
        client = app.state.card_review_client
        assert client is not app.state.agent_client
        assert client.timeout == _agent_timeout(s), "read 는 침묵 한도 — 단발 셋은 요청마다 600초를 따로 준다"
        assert client._transport._pool._max_connections == s.card_review_max_streams + 4, "run 몫 + limits·pack·plan 몫 4"
        assert app.state.card_review_semaphore._value == s.card_review_max_streams


# ── 앱 쪽이 떠나면 에이전트 쪽 연결도 닫힌다(실제 Starlette 끊김 경로 — uvicorn 은 ASGI spec 2.3) ──────────────


class _Endless(httpx.AsyncByteStream):
    """LLM 이 도는 중 — 첫 프레임 뒤로 아무것도 안 낸다. 닫혔는지 적는다."""

    def __init__(self) -> None:
        self.closed = False

    async def __aiter__(self):
        yield b'event: status\ndata: {"step": "attempt", "n": 1}\n\n'
        while True:
            await asyncio.sleep(0.02)

    async def aclose(self) -> None:
        self.closed = True


async def _drive_disconnect(body: bytes) -> list[dict]:
    """ASGI 를 직접 부른다 — 첫 본문 조각을 받은 뒤 앱 쪽이 떠난다(http.disconnect)."""
    sent: list[dict] = []
    got_first = asyncio.Event()
    asked = 0

    async def receive() -> dict:
        nonlocal asked
        asked += 1
        if asked == 1:
            return {"type": "http.request", "body": body, "more_body": False}
        await got_first.wait()
        return {"type": "http.disconnect"}

    async def send(msg: dict) -> None:
        sent.append(msg)
        if msg["type"] == "http.response.body" and msg.get("body"):
            got_first.set()

    await asyncio.wait_for(app(_scope(body, "2.3"), receive, send), timeout=10)
    return sent


def _scope(body: bytes, spec: str) -> dict:
    return {"type": "http", "asgi": {"version": "3.0", "spec_version": spec}, "http_version": "1.1",
            "method": "POST", "scheme": "http", "path": "/agent/card-review/run", "raw_path": b"/agent/card-review/run",
            "root_path": "", "query_string": b"", "client": ("127.0.0.1", 50000), "server": ("testserver", 80),
            "headers": [(b"host", b"testserver"), (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode())]}


def test_앱_쪽이_끊으면_에이전트_쪽_연결이_닫히고_퍼밋이_돌아온다(portal):
    stream = _Endless()

    async def go():
        app.state.card_review_semaphore = asyncio.Semaphore(1)
        _wire(_stream_answer(stream))
        sent = await _drive_disconnect(json.dumps(_RUN).encode())
        return sent, app.state.card_review_semaphore.locked()

    sent, locked = asyncio.run(go())
    assert sent[0]["type"] == "http.response.start" and sent[0]["status"] == 200
    assert sent[1]["body"].startswith(b"event: status"), "끊기 전에 받은 것은 그대로 넘어간다"
    assert stream.closed, "앱 쪽이 떠났는데 에이전트 쪽 연결이 열려 있다 — 엔진이 듣는 이 없는 LLM 호출을 끝까지 돈다"
    assert not locked, "끊긴 run 의 퍼밋이 돌아오지 않았다"
    last = _rows()[-1]
    assert (last["event"], last["status"], last["meta"]["code"]) == ("card_review_run_error", "cancelled", "client_closed")


def test_헤더를_보내다_끊겨도_에이전트_쪽_연결이_닫히고_퍼밋이_돌아온다(portal):
    """생성기가 한 번도 돌지 않는 끊김(ASGI spec 2.4 — 헤더를 보내다 OSError). 생성기의 finally 는 돌지 않으므로 응답
    (_CrStream)이 닫는다. 이 길이 없으면 퍼밋이 영구히 새고 엔진은 듣는 이 없는 LLM 호출을 끝까지 돈다."""
    stream = _Endless()
    body = json.dumps(_RUN).encode()

    async def go():
        app.state.card_review_semaphore = asyncio.Semaphore(1)
        _wire(_stream_answer(stream))
        given = False

        async def receive() -> dict:
            nonlocal given
            if not given:
                given = True
                return {"type": "http.request", "body": body, "more_body": False}
            await asyncio.sleep(3600)

        async def send(msg: dict) -> None:
            raise OSError("client gone")

        with contextlib.suppress(Exception):   # 끊긴 연결의 ASGI 호출은 예외로 끝난다(ClientDisconnect 등)
            await asyncio.wait_for(app(_scope(body, "2.4"), receive, send), timeout=10)
        return app.state.card_review_semaphore.locked()

    locked = asyncio.run(go())
    assert stream.closed, "헤더를 보내다 끊긴 run 의 에이전트 쪽 연결이 열려 있다"
    assert not locked, "헤더를 보내다 끊긴 run 의 퍼밋이 돌아오지 않았다"
    assert _rows()[-1]["meta"]["code"] == "client_closed"
