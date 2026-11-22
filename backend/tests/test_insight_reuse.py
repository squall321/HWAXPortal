# 과제 인사이트 다시 쓰기(M3) — 웹 일반 심의 시작에 같은 (과제, 차수)의 앞선 인사이트를 근거로 깔기 · 범위 이어받기(docs/project-insight-graph PLAN §7.1)
"""고정하는 것.
  · 깔기는 확인된 주제 · 같은 (과제, 차수) 칸 · 산출물 범위 안(시작한 사람의 소속 · 조직 — plat 이 붙은 것 · 주인만 보는 것은 아니다)의 카드만이다.
    다른 차수 · 차수 모름은 그 사람의 화면에 수만 알린다(근거에 싣지 않는다). RA 작업 공간의 범위를 모르면 조직에 연 카드만 깐다.
  · 주제가 없거나 · 확인되지 않았거나 · 볼 수 있는 카드가 없으면 에이전트 서버로 가는 요청이 종전과 **바이트까지** 같다. 깔기가 터져도 같다.
  · 리스크 심사 계열(의장 risk-review* · 앱이 띄운 패널)에는 깔지 않는다(D-18) — 확인도 부르지 않는다.
  · 누설 — 남의 초안 · 다른 소속의 카드 · 관리자의 범위 밖 읽기는 깔리지도 세어지지도 않는다. 과제 인사이트 권한이 없으면 깔지 않는다.
  · 앞선 인사이트를 근거로 쓴 카드의 확인 범위는 읽은 카드들의 범위를 다 담는다(PLAN §6.2 최소 범위) — 모르면 주인만 본다.
  · 엔진과 같은 수 · 같은 이름 규칙은 형제 리포의 원본과 맞댄다.
계정은 example.com 시험 신원만 쓴다."""
import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from app.agent import routes as R
from app.agent import upload as U
from app.auth.errors import AuthError
from app.insights import cards as C
from app.insights import intake as I
from app.insights import lineage as L
from app.insights import reuse as X
from app.main import app

from test_insights import CARD, CONFIRMED, KEY, _login, _relay, env  # noqa: F401 — env 는 픽스처다

_ROOT = Path(__file__).resolve().parents[2]
_AGENT = _ROOT.parent / "HWAXAgentServer"
MSG = "/심의 힌지 크랙의 원인을 규명한다"
ASK = {"sp_task": KEY, "round": "dv1", "text": "알파 1차"}
FRAMES = [("delib", {"kind": "decision", "text": "결정문"}), ("done", {})]


def _v(email="me@example.com", aff="CAEG", groups=("feat:insights",), admin=False):
    return C.Viewer(email=email, sub=email, aff=aff, groups=frozenset(groups), admin=admin)


def _row(i, *, owner="peer@example.com", status="confirmed", scope=("aff:CAEG",), rnd="dv1", at=100, claim="리브를 보강한다", **kw):
    return {"id": f"ins:web:c{i}:r:default", "path": "web", "source_id": f"c{i}", "stage": "default", "owner_email": owner, "status": status,
            "scope": list(scope), "round": rnd, "sp_task": KEY, "created_at": at, "claim": claim,
            "subject": {"sp_task": KEY, "round": rnd, "artifacts": []}, "card": dict(CARD), **kw}


# ── 고르기(단위) ─────────────────────────────────────────────────────────────────────────────────────────
def test_같은_칸의_공유_카드만_깔고_나머지는_센다():
    rows = [_row(1, at=5), _row(2, rnd="pv1"), _row(3, rnd=None), _row(4, scope=("aff:CAEG", "plat:risk")),
            _row(5, owner="me@example.com", status="draft", scope=("user:me@example.com",)), _row(6, scope=("org",), at=9),
            _row(7, scope=("aff:OTHER",)), _row(8, status="draft", scope=("user:peer@example.com",)),
            _row(9, owner="me@example.com", status="waiting", scope=("user:me@example.com",))]
    got, n = X.pick(rows, viewer=_v(), round_code="dv1", audience="aff")
    assert [r["id"] for r in got] == ["ins:web:c6:r:default", "ins:web:c1:r:default"], "최근 것부터 — 소속 · 조직 범위의 확인 카드"
    assert n == {"laid": 2, "other_round": 1, "unknown_round": 1, "no_round": 0, "out_of_scope": 1, "over": 0}, \
        "플랫폼 범위(4)는 그 권한이 없어 보이지도 않는다 · 내 초안(5)만 범위 밖 · 다른 소속(7) · 남의 초안(8) · 기다림(9)은 세지 않는다"
    got, n = X.pick(rows, viewer=_v(groups=("feat:insights", "plat:risk")), round_code="dv1", audience="aff")
    assert len(got) == 2 and n["out_of_scope"] == 2, "플랫폼 권한이 있어 보여도 plat 이 붙은 카드는 깔지 않는다 — 산출물의 독자는 그 권한으로 걸러지지 않는다"
    odd = [_row(10, owner="me@example.com", status="draft", scope=("org",))]
    got, n = X.pick(odd, viewer=_v(), round_code="dv1", audience="aff")
    assert got == [] and n["out_of_scope"] == 1, "범위 토큰이 어떻든 확인 · 반박 상태가 아닌 카드는 깔지 않는다"


def test_이_대화의_앞_회차가_낳은_카드는_깔지도_세지도_않는다():
    """이어하기는 앞 회차의 결정문을 요약으로 이미 넘긴다 — 같은 대화의 카드를 '앞선 인사이트' 로 또 깔면 제 결론을 독립 근거처럼 되읽는다."""
    rows = [_row(1), _row(2, source_id="conv-now"), _row(3, source_id="conv-now", path="mcp-job")]
    got, n = X.pick(rows, viewer=_v(), round_code="dv1", audience="aff", skip_source="conv-now")
    assert [r["id"] for r in got] == ["ins:web:c1:r:default", "ins:web:c3:r:default"] and n["laid"] == 2 and sum(n.values()) == 2, \
        "웹 길의 같은 대화 카드만 뺀다(다른 길의 source_id 는 잡 · 워크플로 대화의 id 다)"


def test_RA_작업_공간의_범위를_모르면_조직에_연_카드만_깐다():
    rows = [_row(1), _row(2, scope=("org",))]
    got, n = X.pick(rows, viewer=_v(), round_code="dv1", audience="org")
    assert [r["id"] for r in got] == ["ins:web:c2:r:default"] and n["out_of_scope"] == 1
    got, _n = X.pick(rows, viewer=_v(aff=""), round_code="dv1", audience="aff")
    assert [r["id"] for r in got] == ["ins:web:c2:r:default"], "소속이 없는 사람에게는 조직에 연 카드뿐이다"


def test_이_심의의_차수를_모르면_아무것도_깔지_않고_수만_센다():
    got, n = X.pick([_row(1), _row(2, rnd=None), _row(3, rnd="pv1")], viewer=_v(), round_code=None, audience="aff")
    assert got == [] and n["no_round"] == 3 and n["laid"] == 0


def test_관리자의_범위_밖_읽기로는_깔지도_세지도_않는다():
    rows = [_row(1, scope=("aff:OTHER",)), _row(2, status="draft", scope=("user:peer@example.com",))]
    got, n = X.pick(rows, viewer=_v("boss@example.com", admin=True), round_code="dv1", audience="aff")
    assert got == [] and not any(n.values())


def test_상한을_넘는_카드는_수만_센다():
    rows = [_row(i, at=i) for i in range(X.LAY_MAX + 3)]
    got, n = X.pick(rows, viewer=_v(), round_code="dv1", audience="aff")
    assert len(got) == X.LAY_MAX and n["over"] == 3 and got[0]["created_at"] == X.LAY_MAX + 2
    got, n = X.pick(rows, viewer=_v(), round_code="dv1", audience="aff", room=0)
    assert got == [] and n["over"] == X.LAY_MAX + 3, "호출자 근거가 이미 상한이면 하나도 깔지 않는다"


@pytest.mark.parametrize("kw, want", [
    ({"save_report": 0, "append_to_report_id": None, "ra_sso": False, "ra_workspace": "dept-a"}, "aff"),
    ({"save_report": None, "append_to_report_id": None, "ra_sso": False, "ra_workspace": "personal-7"}, "aff"),
    ({"save_report": 1, "append_to_report_id": None, "ra_sso": False, "ra_workspace": "dept-a"}, "org"),
    ({"save_report": None, "append_to_report_id": None, "ra_sso": False, "ra_workspace": ""}, "org"),
    ({"save_report": None, "append_to_report_id": None, "ra_sso": False, "ra_workspace": None}, "org"),
    ({"save_report": None, "append_to_report_id": 12, "ra_sso": False, "ra_workspace": "personal-7"}, "org"),
    ({"save_report": None, "append_to_report_id": None, "ra_sso": True, "ra_workspace": "personal-7"}, "org"),
])
def test_산출물의_독자는_보고서가_어디_저장되는지로_정한다(kw, want):
    assert X.output_audience(**kw) == want


@pytest.mark.parametrize("viewer, pat, opts, want", [
    (_v(), "pat", {"subject": {"sp_task": f" {KEY} "}}, KEY),
    (_v(), "pat", {"subject": {"sp_task": KEY}, "chair_template": "diagnosis", "started_by": "human"}, KEY),
    (_v(groups=("feat:deliberation",)), "pat", {"subject": {"sp_task": KEY}}, ""),          # 과제 인사이트 권한이 없다
    (_v(), "", {"subject": {"sp_task": KEY}}, ""),                                           # 사람 자격이 없다
    (_v(), None, {"subject": {"sp_task": KEY}}, ""),
    (_v(email=""), "pat", {"subject": {"sp_task": KEY}}, ""),
    (None, "pat", {"subject": {"sp_task": KEY}}, ""),
    (_v(), "pat", {"subject": {"text": "과제 없이 글만"}}, ""),
    (_v(), "pat", {"subject": {"sp_task": "  "}}, ""),
    (_v(), "pat", {}, ""),
    (_v(), "pat", {"subject": {"sp_task": KEY}, "chair_template": "risk-review"}, ""),       # D-18
    (_v(), "pat", {"subject": {"sp_task": KEY}, "chair_template": "risk-review-sealed"}, ""),
    (_v(), "pat", {"subject": {"sp_task": KEY}, "started_by": "app"}, ""),
])
def test_깔기의_대상은_과제를_단_일반_심의이고_권한과_사람_자격이_있을_때뿐이다(viewer, pat, opts, want):
    assert X.subject_key(viewer, pat, opts) == want


def test_근거_항목은_표지_출처_상태_판을_달고_도구_칸에_카드_id_를_싣는다():
    row = _row(1, owner="peer@example.com", at=1_795_000_000, status="disputed", claim_edited_by="peer@example.com",
               subject={"sp_task": KEY, "round": "dv1", "artifacts": [{"kind": "mcad", "id": "0" * 23, "rev": "aa11"},
                                                                       {"kind": "ecad", "id": "abcdef0123456789", "rev": "B"},
                                                                       {"kind": "cae", "id": "R1"}]})
    now = {"artifacts": [{"kind": "mcad", "id": "0" * 23, "rev": "bb22"}, {"kind": "ecad", "id": "abcdef0123456789", "rev": "B"}]}
    it = X.evidence_item(row, 3, now_subject=now, stale={"say": "낡았을 수 있다 — 기구 CAD: 뒤 판이 있다"}, dispute_notes=["응력 근거가 틀렸다"])
    assert it["tool"] == "insight_get" and json.loads(it["args"]) == {"id": row["id"]} and it["key"] == "ins-3"
    assert it["source"] == X.SOURCE == "앞선 인사이트 — 검증 대상, 독립 근거 아님"
    body = it["result"]
    assert body.startswith("[앞선 인사이트 — 검증 대상, 독립 근거 아님]\n출처: peer@example.com · ")
    for want in ("웹 심의", "단 default", "RA 보고서 #7", f"카드 {row['id']}", "상태: 반박 있음 · 주장은 사람이 고쳤다", "반박 메모: 응력 근거가 틀렸다",
                 "이 심의의 판(bb22)과 다르다", "이 심의와 같은 판", "이 심의의 주제에 없는 설계 자료", "낡았을 수 있다", "표결: 동의 2 · 조건부 0 · 반대 1",
                 "주장:\n리브를 보강한다"):
        assert want in body, want
    mark = {"tool": it["tool"], "args": it["args"], "ok": True}        # 엔진이 근거 표지에 적는 꼴(_insight_calls — ok 는 결과 글의 성패다)
    assert C.insight_sources({"card": {"calls": [mark]}}) == ([row["id"]], ""), "깐 항목이 낳는 근거 표지에서 읽은 카드 id 를 되찾는다"
    for bad in ({**mark, "ok": False}, {"tool": it["tool"], "args": it["args"]}, {**mark, "ok": 1}):
        assert C.insight_sources({"card": {"calls": [mark, bad]}})[0] is None, "실패했거나 성패를 모르는 표지는 그 카드를 읽었다는 증거가 아니다(L2)"


def test_근거_항목의_꼴과_상한은_엔진과_맞는다():
    eng = _AGENT / "deliberation.py"
    if not eng.exists():
        pytest.skip(f"형제 리포 없음: {eng}")
    src = eng.read_text(encoding="utf-8")
    assert re.search(rf'^_EVID_ITEMS = _env_int\("DELIB_EVID_ITEMS", {X.EVID_ITEMS}\)', src, re.M)
    assert R.DelibOpts.model_fields["evidence"].metadata[0].max_length == X.EVID_ITEMS
    assert re.search(rf"^_INSIGHT_CALLS_MAX = {C.CALLS_MAX}\b", src, re.M)
    assert f'_INSIGHT_TOOL_HEAD = "{C.INSIGHT_TOOL_HEAD}"' in src and X.TOOL.startswith(C.INSIGHT_TOOL_HEAD)
    m = re.search(r'^_INSIGHT_EV_TOOL_RE = re\.compile\(r"([^"]+)" \+ _INSIGHT_TOOL_HEAD, re\.I \| re\.A\)$', src, re.M)
    assert m and m.group(1) + C.INSIGHT_TOOL_HEAD == C._INSIGHT_NAME_RE.pattern, "리스크 심사의 받침과 같은 이름 규칙"
    assert C._INSIGHT_NAME_RE.flags & re.I and C._INSIGHT_NAME_RE.flags & re.A, "같은 깃발(같은 입력에 같은 답은 test_insight_workflows 가 맞댄다)"
    key_max = int(re.search(r"^_EVID_KEY_MAX = (\d+)$", src, re.M).group(1))
    assert len(f"ins-{X.LAY_MAX}") <= key_max and re.fullmatch(r"[A-Za-z0-9_.-]+", f"ins-{X.LAY_MAX}")
    args_max = int(re.search(r'^_EVID_ARGS_MAX = _env_int\("DELIB_EVID_ARGS_MAX", (\d+)\)', src, re.M).group(1))
    assert len(json.dumps({"id": "ins:web:" + "c" * 64 + ":" + "r" * 64 + ":" + "s" * 40})) <= args_max, "카드 id 가 인자 표기 상한에서 잘리지 않는다"


# ── 중계 — 실제 로그인 · 에이전트 서버 자리의 대역 ────────────────────────────────────────────────────────────
def _sse(frames) -> bytes:
    return "".join(f"event: {ev}\ndata: {json.dumps(d, ensure_ascii=False)}\n\n" for ev, d in frames).encode()


class _Body(httpx.AsyncByteStream):
    def __init__(self, raw: bytes) -> None:
        self.raw = raw

    async def __aiter__(self):
        yield self.raw


@pytest.fixture()
def web(env, monkeypatch):  # noqa: F811
    """/agent/chat 를 세션으로 부르고 에이전트 서버로 간 요청 본문(바이트)과 브라우저가 받은 글을 본다. 주제 확인(에이전트 서버) · 게이트웨이 도구는
    대역이다 — 부른 것을 적는다. 기본은 '받은 주제를 그대로 확인' 이고 게이트웨이 도구는 없다(unknown tool)."""
    c, st, s = env
    sent, confirms, calls = [], [], []
    state = SimpleNamespace(confirm=lambda subj: {**CONFIRMED, "sp_task": subj["sp_task"], "round": C.norm_round(subj.get("round") or ""),
                                                  "round_by": "person" if C.norm_round(subj.get("round") or "") else None,
                                                  "artifacts": subj.get("artifacts") or []}, gateway={})

    def handler(req: httpx.Request) -> httpx.Response:
        sent.append(req.content)
        return httpx.Response(200, stream=_Body(_sse(FRAMES)), headers={"content-type": "text/event-stream"})

    async def fake_confirm(settings, *, subject, principal, pat, chair_template):
        confirms.append({"subject": subject, "email": principal.email, "pat": bool(pat), "chair": chair_template})
        rec = state.confirm(subject)
        return (rec, "") if rec is not None else (None, "주제를 다시 풀지 못했다")

    async def fake_mcp(url, pat, tool, args, timeout=90.0):
        calls.append((tool, args))
        if tool not in state.gateway:
            raise AuthError(f"{tool}: unknown tool: {tool}", status_code=502)
        return state.gateway[tool](args)

    monkeypatch.setattr(I, "confirm_async", fake_confirm)
    monkeypatch.setattr(U, "mcp_call", fake_mcp)
    real = app.state.agent_client
    app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    def login(who: str) -> dict:
        from app.auth.routes.local import _rl
        _rl.clear()                      # 한 시험이 여러 번 갈아 로그인한다 — 로그인 횟수 제한은 이 시험이 보는 것이 아니다
        return _login(c, who)

    def go(who: str, body: dict) -> tuple[bytes, str]:
        r = c.post("/agent/chat", json=body, headers=login(who))
        assert r.status_code == 200, r.text
        return sent[-1], r.text

    def confirmed(who: str, cid: str, **kw) -> str:
        """그 사람의 확인한 카드 하나(소속 범위) — 웹 길로 들이고 화면의 확인을 누른다."""
        _relay(st, owner=who, cid=cid, **kw)
        iid = f"ins:web:{cid}:r1:default"
        assert c.post(f"/insights-api/cards/{iid}/confirm", headers=login(who)).status_code == 200
        return iid

    try:
        yield SimpleNamespace(c=c, st=st, s=s, go=go, login=login, confirmed=confirmed, sent=sent, confirms=confirms, calls=calls, state=state)
    finally:
        app.state.agent_client = real


def _personal(email="me@example.com"):
    app.state.user_store.set_connection(email=email, service="reportarchive", token="rat_test", workspace="personal-7")


def _body(**opts):
    return {"message": MSG, "delib_opts": {"subject": dict(ASK), **opts}}


def _ev(payload: bytes) -> list:
    return (json.loads(payload).get("delib_opts") or {}).get("evidence") or []


def test_같은_과제_차수의_확인된_카드를_근거로_깔고_그_사람에게_알린다(web):
    a = web.confirmed("peer@example.com", "a")
    web.confirmed("peer@example.com", "b", subject={**CONFIRMED, "round": "pv1"})
    web.confirmed("peer@example.com", "d", subject={**CONFIRMED, "round": None, "round_by": None})
    _relay(web.st, owner="me@example.com", cid="mine")              # 내 초안 — 같은 칸이지만 깔지 않는다
    _personal()
    mine = {"source": "StepForge", "tool": "find_part", "args": "{}", "result": "힌지 2종"}
    payload, text = web.go("me@example.com", _body(evidence=[mine]))
    ev = _ev(payload)
    assert ev[0] == mine and len(ev) == 2, "그 사람이 고른 근거가 앞이고 깐 것이 뒤다"
    assert ev[1]["tool"] == "insight_get" and json.loads(ev[1]["args"]) == {"id": a} and ev[1]["source"] == X.SOURCE
    assert "출처: peer@example.com" in ev[1]["result"] and "상태: 확인" in ev[1]["result"]
    assert json.loads(payload)["delib_opts"]["subject"] == ASK, "주제는 그대로 넘긴다(에이전트 서버가 다시 확인한다)"
    assert "앞선 인사이트 1건을 근거로 실었다" in text and "다른 차수 1건" in text and "차수 모름 1건" in text and "범위 밖 1건" in text
    assert "pv1" not in json.dumps(ev, ensure_ascii=False), "다른 차수의 카드는 근거에 없다"
    assert "다른 차수" not in json.dumps(ev, ensure_ascii=False), "수는 화면에만 알린다 — 근거(산출물)에 싣지 않는다"
    assert web.confirms == [{"subject": ASK, "email": "me@example.com", "pat": True, "chair": None}]
    with closing(sqlite3.connect(web.s.agent_audit_log_path)) as db:
        meta = json.loads(db.execute("SELECT meta FROM agent_audit WHERE event='insight_laid'").fetchall()[-1][0])
    assert meta["ids"] == [a] and meta["laid"] == 1 and meta["sp_task"] == KEY


def test_이어하는_심의에는_그_대화의_앞_카드를_깔지_않는다(web):
    web.login("me@example.com")
    conv = web.c.post("/agent/conversations", json={"title": "t", "kind": "deliberation"}, headers=web.login("me@example.com")).json()["id"]
    mine = web.confirmed("me@example.com", conv)            # 이 대화의 앞 회차가 낳은 카드(웹 길의 source_id 는 대화 id 다)
    other = web.confirmed("peer@example.com", "a")
    _personal()
    got, text = web.go("me@example.com", {**_body(), "conversation_id": conv})
    assert [json.loads(e["args"])["id"] for e in _ev(got)] == [other] and mine not in got.decode() and "1건을 근거로 실었다" in text
    got, _t = web.go("me@example.com", _body())             # 다른(새) 대화에서는 그 카드도 앞선 인사이트다
    assert sorted(json.loads(e["args"])["id"] for e in _ev(got)) == sorted([mine, other])


def test_RA_작업_공간의_범위를_모르면_조직에_연_카드만_깔린다(web):
    a = web.confirmed("peer@example.com", "a")
    b = web.confirmed("peer@example.com", "b")
    assert web.c.post(f"/insights-api/cards/{b}/widen", json={"to": "org"}, headers=web.login("peer@example.com")).status_code == 200
    payload, text = web.go("me@example.com", _body())                 # RA 연결이 없다 — 작업 공간의 범위를 모른다
    assert [json.loads(e["args"])["id"] for e in _ev(payload)] == [b]
    assert "범위 밖 1건" in text and "작업 공간의 범위를 몰라" in text
    payload, _t = web.go("me@example.com", _body(save_report=0))       # 보고서를 저장하지 않으면 소속 범위도 깐다
    assert sorted(json.loads(e["args"])["id"] for e in _ev(payload)) == sorted([a, b])


def _baseline(web, who: str, body: dict) -> bytes:
    """깔기를 통째로 뺀 중계가 보내는 요청 — '종전' 이다."""
    keep = R._insight_ctx
    R._insight_ctx = lambda *_a, **_k: None
    try:
        return web.go(who, body)[0]
    finally:
        R._insight_ctx = keep


def test_주제가_없거나_확인되지_않았으면_요청이_종전과_바이트까지_같다(web):
    web.confirmed("peer@example.com", "a")
    _personal()
    plain = {"message": MSG, "delib_opts": {"rounds": 3, "evidence": [{"source": "메모", "result": "글"}]}}
    for body in (plain, {"message": MSG}, {"message": "힌지 크랙이 뭐야", "delib_opts": {"subject": dict(ASK)}},
                 {"message": MSG, "delib_opts": {"subject": {"text": "과제 없이 글만"}}}):
        base = _baseline(web, "me@example.com", body)
        n = len(web.confirms)
        got, text = web.go("me@example.com", body)
        assert got == base, body
        assert len(web.confirms) == n and "앞선 인사이트" not in text, "주제가 없으면 확인도 부르지 않고 알림도 없다"
    # 주제를 줬지만 서버가 확인하지 못했다(주장) · 다른 key 로 확인됐다 · 확인 창구에 닿지 못했다
    for rec in (lambda s: {**CONFIRMED, "sp_state": "claimed", "sp_task": s["sp_task"]}, lambda s: {**CONFIRMED, "sp_task": "다른 과제"},
                lambda s: None):
        web.state.confirm = rec
        body = _body(rounds=3)
        got, text = web.go("me@example.com", body)
        assert got == _baseline(web, "me@example.com", body) and "근거로 실었다" not in text


def test_볼_수_있는_카드가_없으면_확인도_부르지_않고_요청이_같다(web):
    _relay(web.st, owner="peer@example.com", cid="a")                 # 남의 초안뿐 — 나에게는 없는 것과 같다
    _personal()
    got, text = web.go("me@example.com", _body())
    assert got == _baseline(web, "me@example.com", _body()) and web.confirms == [] and web.calls == [] and "앞선 인사이트" not in text
    web.confirmed("peer@example.com", "b", subject={**CONFIRMED, "sp_task": "다른 과제"})
    got, _t = web.go("me@example.com", _body())
    assert got == _baseline(web, "me@example.com", _body()) and web.confirms == [], "다른 과제의 카드만 있으면 확인하지 않는다"


def test_같은_칸에_깔_것이_없어도_확인된_주제면_수만_알리고_요청은_같다(web):
    web.confirmed("peer@example.com", "b", subject={**CONFIRMED, "round": "pv1"})
    _personal()
    got, text = web.go("me@example.com", _body())
    assert got == _baseline(web, "me@example.com", _body()), "깐 것이 없으면 근거 칸을 만들지 않는다"
    assert "앞선 인사이트를 근거로 싣지 않았다" in text and "다른 차수 1건" in text


@pytest.mark.parametrize("opts", [{"chair_template": "risk-review"}, {"chair_template": "risk-review-sealed"}, {"started_by": "app"}])
def test_리스크_심사_계열에는_깔지_않고_확인도_부르지_않는다(web, opts):
    web.confirmed("peer@example.com", "a")
    _personal()
    got, text = web.go("me@example.com", _body(**opts))
    assert got == _baseline(web, "me@example.com", _body(**opts)) and web.confirms == [] and web.calls == []
    assert "insight_get" not in got.decode() and "앞선 인사이트" not in text


def test_다른_소속_과제_인사이트_권한이_없는_사람에게는_깔리지_않는다(web):
    web.confirmed("peer@example.com", "a")
    grants = ["feat:chat", "feat:deliberation"]
    assert web.c.patch("/auth/access/users/out@example.com", json={"grants": grants}, headers=web.login("boss@example.com")).status_code == 200
    body = _body(save_report=0)
    got, text = web.go("out@example.com", body)
    assert got == _baseline(web, "out@example.com", body) and web.confirms == [], "과제 인사이트 권한이 없다"
    assert web.c.patch("/auth/access/users/out@example.com", json={"grants": [*grants, "feat:insights"]},
                       headers=web.login("boss@example.com")).status_code == 200
    got, text = web.go("out@example.com", body)
    assert got == _baseline(web, "out@example.com", body) and web.confirms == [] and "앞선 인사이트" not in text, \
        "권한이 있어도 다른(없는) 소속에게 CAEG 범위의 카드는 없는 것과 같다 — 수도 알리지 않는다"
    got, _t = web.go("boss@example.com", body)
    assert _ev(got) == [], "관리자도 제 소속 밖의 카드는 깔리지 않는다(범위 밖 읽기는 화면에서만 · 감사에 남는다)"


def test_깔기가_터지거나_늦어도_심의는_종전_요청_그대로_열린다(web, monkeypatch):
    web.confirmed("peer@example.com", "a")
    _personal()
    base = _baseline(web, "me@example.com", _body())

    async def boom(**_k):
        raise RuntimeError("원장이 잠겼다")
    monkeypatch.setattr(X, "lay", boom)
    got, text = web.go("me@example.com", _body())
    assert got == base and "결정문" in text

    async def slow(**_k):
        import asyncio
        await asyncio.sleep(5)
    monkeypatch.setattr(X, "lay", slow)
    monkeypatch.setattr(X, "LAY_TIMEOUT_S", 0.05)
    got, text = web.go("me@example.com", _body())
    assert got == base and "결정문" in text


def test_호출자_근거가_상한이면_깔지_않고_수만_알린다(web):
    web.confirmed("peer@example.com", "a")
    _personal()
    full = [{"source": f"E{i}", "result": "글"} for i in range(X.EVID_ITEMS)]
    got, text = web.go("me@example.com", _body(evidence=full))
    assert len(_ev(got)) == X.EVID_ITEMS and "상한 밖 1건" in text


def test_옛_key_로_남은_카드도_지금_과제의_같은_칸으로_깐다(web):
    old = web.confirmed("peer@example.com", "a", subject={**CONFIRMED, "sp_task": "알파 개발_C1"})
    web.confirmed("peer@example.com", "b", subject={**CONFIRMED, "sp_task": "재사용된 옛 이름"})
    _personal()
    web.state.gateway[L.STEPFORGE_OBJECT] = lambda a: {"node": a["focus"], "type": "plm_task", "key": KEY,
                                                       "keys": {"previous_keys": ["알파 개발_C1", "재사용된 옛 이름"], "merged_from": []}}
    # 풀이 — '재사용된 옛 이름' 은 지금 다른 산 과제의 key 다(글자 그대로 같은 활성 행 하나). '알파 개발_C1' 은 풀이에 없다.
    web.state.gateway[L._subject.RESOLVER_CALL] = lambda a: {"query": a["query"], "tasks": (
        [{"key": a["query"], "label": a["query"], "active": True}] if a["query"] == "재사용된 옛 이름" else [])}
    got, text = web.go("me@example.com", _body())
    assert [json.loads(e["args"])["id"] for e in _ev(got)] == [old] and "1건을 근거로 실었다" in text
    assert (L.STEPFORGE_OBJECT, {"focus": f"plm_task:{KEY}", "history": False}) in web.calls


# ── 범위 이어받기 — 앞선 인사이트를 근거로 쓴 카드의 확인 ─────────────────────────────────────────────────────────
def _derived(ids, *, tool="insight_get", extra_calls=(), args=None):
    calls = [{"ref": f"call:{i:016x}", "tool": tool, "app": "_gateway", "args": args or json.dumps({"id": x}), "sha256": "0" * 64, "ok": True}
             for i, x in enumerate(ids)]
    return {**CARD, "calls": [*calls, *extra_calls], "tools": sorted({tool, *(c["tool"] for c in extra_calls)}), "apps": ["_gateway"]}


def test_읽은_카드를_다_알_때만_id_를_낸다():
    assert C.insight_sources({"card": _derived(["ins:web:a:r1:default", "ins:delib:j:default"])})[0] == ["ins:web:a:r1:default", "ins:delib:j:default"]
    assert C.insight_sources({"card": _derived(["ins:wf:z"], tool="mcp__hwax__insight_get", args="{'id': 'ins:wf:z'}")})[0] == ["ins:wf:z"], \
        "엔진이 사전 인자를 글로 옮긴 꼴도 읽는다"
    for card in (_derived(["x"], tool="insight_find", args='{"sp_task": "알파"}'), _derived(["x"], args='{"id": "남의 글"}'),
                 _derived(["x"], tool="insight_find", args='{"id": "ins:web:a:r1:default"}'),     # 찾기 도구에 id 를 적어도 카드 하나가 아니다
                 _derived(["x"], args='{"id": "ins:web:a:r1:default", "also": 1}'), {**CARD, "tools": ["insight_get"], "calls": []},
                 _derived(["ins:wf:z"], extra_calls=[{"tool": "find_part", "args": "{}"}] * (C.CALLS_MAX - 1))):
        ids, why = C.insight_sources({"card": card})
        assert ids is None and why, card["tools"]
    assert C.insight_derived({"card": {"tools": ["mcp__hwax__insight_find"]}}) and not C.insight_derived({"card": {"tools": ["getinsight_x"]}})
    assert C.insight_derived({"card": {"tools": ["get_insight_x"]}}), "낱말 경계 — 앞이 영숫자가 아니면 인사이트 도구로 본다(닫힌 쪽)"


def test_이름만_있는_인사이트_도구가_섞이면_읽은_카드를_다_안다고_하지_않는다():
    """반대 검토 11-22 L1 — 근거 표지(calls)는 카드 하나를 읽은 것뿐인데 도구 이름(tools)에 표지 없는 인사이트 도구가 더 있으면(같은 심의의 앞 단이
    찾기 결과를 넘겼다) 그 도구가 무엇을 읽었는지 모른다. 계약 §10.3 — 이름만 있으면 모른다(주인만)."""
    one = _derived(["ins:web:a:r1:default"])
    assert C.insight_sources({"card": one})[0] == ["ins:web:a:r1:default"]
    for more in (["insight_find"], ["mcp__hwax__insight_find"], ["mcp__hwax__insight_get"], ["hwax-insight_get"]):
        ids, why = C.insight_sources({"card": {**one, "tools": [*one["tools"], *more]}})
        assert ids is None and "도구 이름만" in why, more
    assert C.insight_sources({"card": {**one, "tools": [*one["tools"], "find_part", "risk_get_diff"]}})[0] == ["ins:web:a:r1:default"], \
        "인사이트 도구가 아닌 이름은 따지지 않는다"
    assert C.insight_sources({"card": {**one, "tools": []}})[0] == ["ins:web:a:r1:default"], "도구 이름 칸이 비면 표지만 본다"


def test_범용_실행기로_부른_표지는_앞선_인사이트를_쓴_것으로_치되_읽은_카드는_모른다():
    """반대 검토 11-22 M3 — invoke_tool 껍데기에 든 insight_get 도 앞선 인사이트를 근거로 쓴 것이다(확인이 주인만으로 닫힌다). 엔진은 껍데기를 벗겨
    안쪽 이름 · 인자로 표지를 적으므로(deliberation._ev_unwrap) 껍데기째 남은 표지는 풀지 못한 것이다 — 읽은 카드를 안다고 하지 않는다."""
    wrapped = {**CARD, "tools": ["mcp__hwax__invoke_tool"], "apps": ["_gateway"],
               "calls": [{"ref": "call:1", "tool": "mcp__hwax__invoke_tool", "ok": True, "sha256": "0" * 64,
                          "args": '{"name": "insight_get", "arguments": {"id": "ins:web:a:r1:default"}}'}]}
    assert C.insight_derived({"card": wrapped}) and C.insight_sources({"card": wrapped})[0] is None
    other = {**wrapped, "calls": [{**wrapped["calls"][0], "args": '{"name": "find_part", "arguments": {"q": "insight_get"}}'}]}
    assert not C.insight_derived({"card": other}), "껍데기 안의 도구가 인사이트가 아니면 아니다"


@pytest.mark.parametrize("base, sources, want", [
    (["aff:CAEG"], [{"status": "confirmed", "scope": ["aff:CAEG"]}], ["aff:CAEG"]),
    (["aff:CAEG", "plat:stepforge"], [{"status": "disputed", "scope": ["org", "plat:risk"]}], ["aff:CAEG", "plat:risk", "plat:stepforge"]),
    (["aff:CAEG"], [{"status": "confirmed", "scope": ["org"]}, {"status": "confirmed", "scope": ["aff:CAEG"]}], ["aff:CAEG"]),
    (["aff:CAEG"], [{"status": "confirmed", "scope": ["aff:OTHER"]}], None),          # 서로 다른 소속 — 함께 볼 사람이 없다
    (["aff:CAEG"], [{"status": "confirmed", "scope": ["user:peer@example.com"]}], None),
    (["aff:CAEG"], [{"status": "draft", "scope": ["user:peer@example.com"]}], None),   # 아직 주인만 보는 카드
    (["aff:CAEG"], [{"status": "withdrawn", "scope": []}], None),
    (["aff:CAEG"], [{"status": "draft", "scope": ["aff:CAEG"]}], None),                # 범위 토큰이 어떻든 공유 상태가 아니면 이어받지 않는다
    (["aff:CAEG"], [None], None),                                                       # 원장에 없는 id
    (["aff:CAEG"], [{"status": "confirmed", "scope": []}], None),
    (["user:me@example.com"], [{"status": "confirmed", "scope": ["org"]}], None),       # 제 범위부터 주인만(소속 없음)
])
def test_확인_범위는_읽은_카드들의_범위를_다_담고_못_담으면_주인만이다(base, sources, want):
    scope, why = C.inherit_scope(base, sources, "me@example.com")
    assert scope == (want or ["user:me@example.com"])
    assert bool(why) == (want is None and base != ["user:me@example.com"])


def test_앞선_인사이트를_근거로_쓴_카드는_확인하면_읽은_카드의_범위를_이어받는다(web):
    c, st = web.c, web.st
    a = web.confirmed("peer@example.com", "a")                                         # [aff:CAEG]
    _relay(st, owner="me@example.com", cid="n1", cards=({**_derived([a])},))
    h = web.login("me@example.com")
    r = c.post("/insights-api/cards/ins:web:n1:r1:default/confirm", headers=h).json()
    assert r["status"] == "confirmed" and r["scope"] == ["aff:CAEG"] and not r["scope_note"], r
    # 읽은 카드가 플랫폼 범위면 그 권한까지 담는다(MCP 호출자가 넘긴 경우)
    _relay(st, owner="peer@example.com", cid="p", cards=({**CARD, "tools": ["risk_get_diff"], "apps": ["heax-hwax_risk"]},))
    assert c.post("/insights-api/cards/ins:web:p:r1:default/confirm", headers=web.login("peer@example.com")).json()["scope"] == \
        ["aff:CAEG", "plat:risk"]
    _relay(st, owner="me@example.com", cid="n2", cards=({**_derived([a, "ins:web:p:r1:default"])},))
    r = c.post("/insights-api/cards/ins:web:n2:r1:default/confirm", headers=web.login("me@example.com")).json()
    assert r["scope"] == ["aff:CAEG", "plat:risk"], "읽은 카드의 플랫폼 권한을 이어받는다 — 그 권한 없는 같은 소속에 열리지 않는다"
    # 읽은 카드를 모르거나(찾기 묶음) · 거뒀거나 · 초안이면 주인만
    _relay(st, owner="me@example.com", cid="n3", cards=({**_derived(["x"], tool="insight_find", args='{"sp_task": "알파"}')},))
    _relay(st, owner="peer@example.com", cid="dr")
    _relay(st, owner="me@example.com", cid="n4", cards=({**_derived(["ins:web:dr:r1:default"])},))
    _relay(st, owner="me@example.com", cid="n5", cards=({**_derived(["ins:web:gone:r1:default"])},))
    for cid in ("n3", "n4", "n5"):
        r = c.post(f"/insights-api/cards/ins:web:{cid}:r1:default/confirm", headers=web.login("me@example.com")).json()
        assert r["status"] == "confirmed" and r["scope"] == ["user:me@example.com"] and r["scope_note"], cid
    web.login("peer@example.com")
    assert c.get("/insights-api/cards/ins:web:n1:r1:default").status_code == 200
    assert c.get("/insights-api/cards/ins:web:n3:r1:default").status_code == 404
    assert c.post("/insights-api/cards/ins:web:n1:r1:default/widen", json={"to": "org"}, headers=web.login("me@example.com")).status_code == 409, \
        "앞선 인사이트에 기댄 카드는 조직에 열지 않는다(근거 범위를 다 알지 못한다)"
