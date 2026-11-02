# 과제 인사이트 원장(M2) — 들이기 셋 · 읽을 때 거름 · 주인의 확인과 쓰기 · 형제 리포와 맞대는 규칙(docs/project-insight-graph contracts)
"""고정하는 것.
  · 카드는 확인된 주제만(draft), 주장은 주인의 기다림 줄(waiting), 주제가 없거나 none 이면 들이지 않는다. 리스크 심사 계열은 어느 길로도 안 든다.
  · 초안은 주인만, 주인이 포털에서 확인하면 [aff:<지금 소속>] + 근거 앱의 plat 토큰 — MCP 잡이 실은 소속(자칭)은 쓰지 않는다. 사람 손 없이 넓어지지 않는다.
  · 읽을 때 거른다 — 남의 초안이 안 보이고, 소속이 바뀌면 시야도 바뀌고, 거둔 카드는 아무에게도 안 보인다(관리자도). 관리자의 범위 밖 읽기는 감사에.
  · 쓰기는 세션 + CSRF 만(PAT 로는 못 쓴다). 차수가 다르면 다른 칸 · 차수 모름은 따로.
  · 에이전트 서버 · 게이트웨이 · 리스크 앱과 같은 규칙(차수 정규화 · 주장 뽑기 · 창구 판 · 별칭)은 형제 리포의 원본과 맞댄다.
계정은 example.com 시험 신원만 쓴다 — 이 리포는 GitHub 에 있다.
"""
import ast
import asyncio
import importlib.util
import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.agent import routes as R
from app.agent.audit import AuditLog
from app.auth.cookies import CSRF_COOKIE
from app.auth.token_store import TokenStore
from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.insights import cards as C
from app.insights import intake as I
from app.insights import routes as IR
from app.insights.store import InsightStore
from app.main import app
from app.procedures.store import ProceduresStore

_ROOT = Path(__file__).resolve().parents[2]
_AGENT = _ROOT.parent / "HWAXAgentServer"
_GATEWAY = _ROOT.parent / "HWAXMcpGateway"
_RISK = _ROOT.parent / "HWAXRisk"
PW = "pw123456"
KEY = "알파 개발_C2"
CONFIRMED = {"sp_task": KEY, "sp_state": "confirmed", "sp_resolved_by": {"tool": "heaxstep_forge_find_plm_task", "app": "heax-step_forge",
                                                                          "at": 1.5, "sha256": "ab" * 32},
             "round": "dv1", "round_by": "person", "text": "알파 1차", "artifacts": [{"kind": "ecad", "id": "abcdef0123456789"}]}
CLAIMED = {**CONFIRMED, "sp_state": "claimed", "sp_resolved_by": None, "sp_why": "결과 행에 같은 key 가 없다", "sp_task": "알파"}
SUMMARY = "- 리브를 1.2 mm 로 보강한다\n- 근거: 응력 412 MPa"
CARD = {"stage": "default", "claim": SUMMARY, "claim_from": "summary", "tally": {"agree": 2, "conditional": 0, "oppose": 1, "abstain": 0},
        "report_id": 7, "report_url": "/w/a/reports/7", "model": "glm", "calls": [], "tools": [], "apps": [], "apps_unknown": [],
        "refs": ["rpt:7"]}


# ── 형제 리포와 같은 규칙 ─────────────────────────────────────────────────────────────────────────────────
def _load(path: Path, name: str):
    if not path.exists():
        pytest.skip(f"형제 리포 없음: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_차수_정규화_리스크_심사_계열은_에이전트_서버와_같다():
    a = _load(_AGENT / "delib_subject.py", "_agent_delib_subject_for_insights")
    assert C.STAGES == a.STAGES and C._SPACE_RE.pattern == a._SPACE_RE.pattern and C.ROUND_UNKNOWN == a.ROUND_UNKNOWN
    for v in ("DV1", " dv 1 ", "ｄｖ１", "dv-1", "2차", "C2", "양산", "pre1", "dv", "PVR", "　mp ", "dv⁠1", None, 3):
        assert C.norm_round(v) == a.norm_round(v), v
    for chair, by in (("risk-review", None), ("risk-review-sealed", None), ("Risk-Review", ""), ("default", "app"), ("default", "human"),
                      (None, None), ("diagnosis", "APP ")):
        assert C.risk_family(chair, by) == a.risk_family(chair, by), (chair, by)


def _agent_claim_fn():
    """에이전트 deliberation.py 의 insight_claim 과 그 도우미 · 상수만 AST 로 떼어 실행한다(엔진 모듈 전체를 읽지 않는다)."""
    p = _AGENT / "deliberation.py"
    if not p.exists():
        pytest.skip(f"형제 리포 없음: {p}")
    tree = ast.parse(p.read_text(encoding="utf-8"))
    want_fn = {"_insight_clip", "_insight_summary_of", "_insight_plain_one", "insight_claim"}
    want_var = {"_INSIGHT_CLAIM_MAX", "_INSIGHT_SUMMARY_HEAD", "_INSIGHT_PLAIN_HEAD", "_INSIGHT_PLAIN_ONE", "_BULLET_RE"}
    body = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name in want_fn)
            or (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in want_var for t in n.targets))]
    assert len(body) == len(want_fn) + len(want_var), "엔진의 주장 뽑기 모양이 바뀌었다 — 이 시험도 고쳐라"
    ns: dict = {"re": re}
    exec(compile(ast.Module(body=body, type_ignores=[]), str(p), "exec"), ns)  # noqa: S102 — 형제 리포의 우리 코드다
    return ns["insight_claim"]


@pytest.mark.parametrize("dec", [
    f"■ 핵심 요약\n{SUMMARY}\n\n결정 — 보강한다.",
    f"■ 봉인 실행 — 봉인\n\n■ 기준일 — 2026-10-01\n\n■ 핵심 요약\n{SUMMARY}\n\n결정",
    "결정 — 보강한다.\n\n---\n\n■ 쉬운 설명\n### 한마디로\n리브를 보강하라는 결정이다\n### 왜 그런가\n- 응력",
    "결정\n\n---\n\n■ 쉬운 설명 (결정문 일부 기준 — 전문 900자 중 앞뒤 발췌)\n### 한마디로\n\n(리브를 보강한다)\n",
    "결정 ■ 핵심 요약\n- 가운데", "", "### 한마디로 없이 결정만",
    "■ 핵심 요약\n" + "\n".join(f"- 근거 {i} " + "가" * 40 for i in range(30)),
])
def test_주장_뽑기는_엔진과_같다(dec):
    assert C.claim_of(dec) == _agent_claim_fn()(dec)


def test_창구_판_상한_별칭이_형제_리포와_같다():
    jobs = (_AGENT / "delib_jobs.py")
    if not jobs.exists():
        pytest.skip(f"형제 리포 없음: {jobs}")
    assert re.search(rf'^INSIGHT_CONTRACT = "{re.escape(I.AGENT_CONTRACT)}"$', jobs.read_text(encoding="utf-8"), re.M)
    gw = _GATEWAY / "gateway.py"
    if gw.exists():
        src = gw.read_text(encoding="utf-8")
        assert re.search(rf"^CONV_SUBJECT_MAX_CHARS = {R._CONV_SUBJECT_MAX_CHARS}\b", src, re.M)
        assert f're.compile(r"{R._CONV_CHAIR_RE.pattern}")' in src
        assert '"/insights-api", "GET", "/find"' in src and '"/insights-api", "GET", f"/cards/' in src, "게이트웨이 도구가 부르는 창구"
    assert IR.RISK_TOOL == "heaxhwax_risk_" + "risk_find_projects_by_subject", "게이트웨이 별칭 꼴 — <백엔드 키에서 - 뺀 것>_<원래 이름>"
    mcp = _RISK / "backend" / "app" / "mcp_server.py"
    if mcp.exists() and "risk_find_projects_by_subject" in mcp.read_text(encoding="utf-8"):
        assert re.search(r"def risk_find_projects_by_subject\(", mcp.read_text(encoding="utf-8"))


# ── 원장 · 시야(단위) ─────────────────────────────────────────────────────────────────────────────────────
@pytest.fixture()
def store(tmp_path):
    s = Settings(_env_file=None, procedures_store_path=str(tmp_path / "procedures.sqlite"))
    ps = ProceduresStore(s)
    yield InsightStore(ps)
    ps.close()


def _relay(st, *, owner="me@example.com", subject=CONFIRMED, cards=(CARD,), chair=None, started_by=None, cid="c1", run="r1"):
    return I.from_relay(st, owner_email=owner, owner_sub="sub-" + owner, cid=cid, run_key=run, subject=subject, cards=list(cards),
                        chair_template=chair, started_by=started_by)


def test_웹_들이기는_확인된_주제만_초안이고_주장은_기다림_줄이고_없음은_없다(store):
    assert _relay(store) == ["ins:web:c1:r1:default"]
    r = store.get("ins:web:c1:r1:default")
    assert (r["status"], r["sp_task"], r["round"], r["scope"], r["path"]) == ("draft", KEY, "dv1", ["user:me@example.com"], "web")
    assert r["claim"] == SUMMARY and r["card"]["report_id"] == 7
    assert _relay(store) == [], "같은 원천은 하나다"
    assert _relay(store, subject=CLAIMED, cid="c2") == ["ins:web:c2:r1:default"]
    w = store.get("ins:web:c2:r1:default")
    assert w["status"] == "waiting" and w["sp_task"] is None and w["subject"]["sp_task"] == "알파"
    assert _relay(store, subject={**CONFIRMED, "sp_state": "none", "sp_task": None}, cid="c3") == []
    assert _relay(store, subject=None, cid="c4") == [] and _relay(store, run="", cid="c5") == []


@pytest.mark.parametrize("kw", [{"chair": "risk-review"}, {"chair": "risk-review-sealed"}, {"started_by": "app"},
                                {"cards": ({**CARD, "stage": "risk-review"},)}])
def test_리스크_심사가_낳은_웹_심의는_들이지_않는다(store, kw):
    assert _relay(store, **kw) == []


def test_다단_심의는_단마다_한_장이고_같은_단을_다시_내면_뒤엣것이다(store):
    got = _relay(store, cards=({**CARD, "stage": "mechanism", "claim": "앞"}, {**CARD, "stage": "sim-plan"},
                               {**CARD, "stage": "mechanism", "claim": "다시"}))
    assert sorted(got) == ["ins:web:c1:r1:mechanism", "ins:web:c1:r1:sim-plan"]
    assert store.get("ins:web:c1:r1:mechanism")["claim"] == "다시"


def test_거둔_카드는_묘비로_남고_다시_들여도_되살지_않는다(store):
    _relay(store)
    assert store.withdraw("ins:web:c1:r1:default", by="me@example.com")
    t = store.get("ins:web:c1:r1:default")
    assert (t["status"], t["claim"], t["card"], t["subject"], t["withdrawn_by"]) == ("withdrawn", "", {}, {}, "me@example.com")
    assert _relay(store) == [] and store.get("ins:web:c1:r1:default")["status"] == "withdrawn"
    assert store.rows() == []


def _v(email, aff="", groups=(), admin=False):
    return C.Viewer(email=email, sub=email, aff=aff, groups=frozenset(groups), admin=admin)


def test_시야_규칙():
    row = {"owner_email": "me@example.com", "status": "draft", "scope": ["user:me@example.com"]}
    assert C.visible(row, _v("ME@example.com"))[0] is False, "읽는 사람 메일은 소문자로 온다(_viewer) — 여기는 그 전제"
    assert C.visible(row, _v("me@example.com")) == (True, False)
    assert C.visible(row, _v("peer@example.com", "CAEG")) == (False, False), "남의 초안"
    assert C.visible(row, _v("boss@example.com", admin=True)) == (True, True), "관리자는 보되 범위 밖이라고 표시"
    shared = {**row, "status": "confirmed", "scope": ["aff:CAEG", "plat:risk"]}
    assert C.visible(shared, _v("peer@example.com", "CAEG", {"plat:risk"})) == (True, False)
    assert C.visible(shared, _v("peer@example.com", "CAEG")) == (False, False), "근거 플랫폼 권한이 없다"
    assert C.visible(shared, _v("out@example.com", "", {"plat:risk"})) == (False, False), "다른(없는) 소속"
    assert C.visible({**shared, "status": "waiting"}, _v("peer@example.com", "CAEG", {"plat:risk"}))[0] is False
    assert C.visible({**shared, "status": "withdrawn"}, _v("me@example.com"))[0] is False
    assert C.visible({**shared, "status": "withdrawn"}, _v("boss@example.com", admin=True))[0] is False, "거둔 것은 관리자도 못 본다"
    assert C.visible(shared, _v(""))[0] is False, "신원 없는 호출"
    assert C.scope_ok(["org"], _v("x@example.com")) and not C.scope_ok([], _v("x@example.com"))
    assert not C.scope_ok(["aff:CAEG", "team:x"], _v("p@example.com", "CAEG")), "모르는 토큰은 닫힌다"


def test_근거_앱은_권한표로_plat_토큰이_된다():
    from app.access.policy import AccessPolicy
    pol = AccessPolicy(Settings(_env_file=None)).get()
    assert C.plat_tokens(["heax-hwax_risk", "ai-data-hub", "_gateway", "모르는-앱", "hwax-deliberation"], pol) == \
        ["plat:aidatahub", "plat:risk"], "feat: 키 · 게이트웨이 자체 · 표에 없는 백엔드는 토큰이 없다"


# ── MCP 잡 당기기 ─────────────────────────────────────────────────────────────────────────────────────────
def _item(jid="default-1", **kw):
    return {"job_id": jid, "job": "default", "user": "me%40example.com", "owner_aff": "자칭", "chair_template": "default",
            "started_by": "human", "status": "done", "finished_at": 1000.0, "continues": None, "subject": CONFIRMED, "cards": [CARD], **kw}


def test_잡_항목은_주인_퍼센트를_풀고_자칭_소속을_쓰지_않고_리스크_심사는_뺀다(store):
    items = [_item(), _item("anon", user=""), _item("risk", chair_template="risk-review"), _item("app", started_by="app"),
             _item("riskcard", cards=[{**CARD, "stage": "risk-review"}]), _item("none", subject={**CONFIRMED, "sp_state": "none"}),
             _item("claimed", subject=CLAIMED), _item("next", continues="default-1"), _item("next2", continues="gone-job")]
    assert I.ingest_jobs(store, items) == 4
    r = store.get("ins:delib:default-1:default")
    assert (r["owner_email"], r["owner_sub"], r["path"], r["scope"], r["status"]) == (
        "me@example.com", None, "mcp-job", ["user:me@example.com"], "draft")
    assert r["card"]["refs"][0] == "delib:default-1"
    assert store.get("ins:delib:claimed:default")["status"] == "waiting"
    assert store.get("ins:delib:next:default")["continues"] == "ins:delib:default-1:default"
    assert store.get("ins:delib:next2:default")["continues"] == "delib:gone-job", "앞 카드가 없으면 앞 잡을 가리킨다"
    for jid in ("anon", "risk", "app", "riskcard", "none"):
        assert store.get(f"ins:delib:{jid}:default") is None, jid


def _sync_app(store, handler, **kw):
    from types import SimpleNamespace
    s = Settings(_env_file=None, insight_sync_s=kw.pop("every", 60), gateway_shared_token=kw.pop("tok", "gw-secret"),
                 agent_server_url="http://agent.test")
    real = httpx.AsyncClient
    return SimpleNamespace(state=SimpleNamespace(insight_store=store)), s, (lambda **k: real(transport=httpx.MockTransport(handler), **k))


def test_당기기는_공유_비밀로_쪽을_넘기며_커서보다_앞부터_읽는다(store, monkeypatch):
    seen = []
    pages = {0: {"items": [_item("a", finished_at=10.0)], "next_since": 10.0, "complete": False},
             10: {"items": [_item("b", finished_at=20.0)], "next_since": 20.0, "complete": True}}

    def handler(req):
        seen.append((req.headers.get("authorization"), float(req.url.params["since"])))
        return httpx.Response(200, json={"contract": I.AGENT_CONTRACT, **pages[int(float(req.url.params["since"]))]})
    app_, s, cli = _sync_app(store, handler)
    monkeypatch.setattr(I.httpx, "AsyncClient", cli)
    monkeypatch.setattr(I, "_SYNC", {"at": 0.0, "lock": None, "loop": None, "last": None})
    out = asyncio.run(I.sync_jobs(app_, s))
    assert out == {"ingested": 2, "since": 20.0} and seen == [("Bearer gw-secret", 0.0), ("Bearer gw-secret", 10.0)]
    assert store.meta_get("jobs_since") == "20.0"
    assert asyncio.run(I.sync_jobs(app_, s)) == {"skipped": "recent"}
    seen.clear()
    pages[0] = pages[10]                                   # 다음엔 커서(20)보다 600초 앞(0으로 바닥)부터 다시 읽는다
    out = asyncio.run(I.sync_jobs(app_, s, force=True))
    assert seen[0][1] == 0.0 and out["ingested"] == 0, "같은 id 는 다시 들이지 않는다"


def test_당기기는_꺼져_있거나_비밀이_없거나_답이_다르면_읽기를_막지_않고_까닭만(store, monkeypatch):
    monkeypatch.setattr(I, "_SYNC", {"at": 0.0, "lock": None, "loop": None, "last": None})
    app_, s, cli = _sync_app(store, lambda req: httpx.Response(200, json={"contract": "다른 판"}), every=0)
    assert asyncio.run(I.sync_jobs(app_, s)) == {"skipped": "off"}
    app_, s, cli = _sync_app(store, lambda req: httpx.Response(200, json={"contract": "다른 판"}), tok="")
    assert "공유 비밀" in asyncio.run(I.sync_jobs(app_, s))["error"]
    app_, s, cli = _sync_app(store, lambda req: httpx.Response(401, json={"error": "unauthorized"}))
    monkeypatch.setattr(I.httpx, "AsyncClient", cli)
    monkeypatch.setattr(I, "_SYNC", {"at": 0.0, "lock": None, "loop": None, "last": None})
    assert "답이 다르다" in asyncio.run(I.sync_jobs(app_, s))["error"]


# ── API — 실제 로그인 세 사람 ──────────────────────────────────────────────────────────────────────────────
def _login(c, email) -> dict:
    c.cookies.clear()
    assert c.post("/auth/local/login", json={"email": email, "password": PW}).status_code == 200
    return {"X-CSRF-Token": c.cookies.get(CSRF_COOKIE)}


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """boss = 원장 관리자 · me · peer = CAEG · out = 소속 없음 + 개별 허가 feat:insights. 원장은 임시 폴더."""
    monkeypatch.delenv("PORTAL_ADMIN_EMAILS", raising=False)
    s = Settings(_env_file=None, user_store_path=str(tmp_path / "users.sqlite"), agent_audit_log_path=str(tmp_path / "audit.sqlite"),
                 token_store_path=str(tmp_path / "tokens.sqlite"), conv_store_path=str(tmp_path / "conv.sqlite"),
                 procedures_store_path=str(tmp_path / "procedures.sqlite"), conn_key_path=str(tmp_path / "conn.key"),
                 local_bootstrap_admins="boss@example.com", insight_sync_s=0)
    app.dependency_overrides[get_settings] = lambda: s
    from app.auth.routes.local import _rl
    _rl.clear()
    with TestClient(app) as c:
        keep = (app.state.user_store, app.state.agent_audit, app.state.token_store, app.state.insight_store)
        ps = ProceduresStore(s)
        app.state.user_store, app.state.agent_audit, app.state.token_store = UserStore(s), AuditLog(s), TokenStore(s)
        app.state.insight_store = InsightStore(ps)
        for email in ("boss@example.com", "me@example.com", "peer@example.com", "out@example.com"):
            assert c.post("/auth/local/signup", json={"email": email, "name": email.split("@")[0], "password": PW}).status_code < 300
        for email in ("me@example.com", "peer@example.com", "out@example.com"):
            assert app.state.user_store.approve(email, by="boss@example.com", groups=[])
        hb = _login(c, "boss@example.com")
        for email in ("me@example.com", "peer@example.com"):
            assert c.patch(f"/auth/access/users/{email}", json={"affiliation": "CAEG"}, headers=hb).status_code == 200
        assert c.patch("/auth/access/users/out@example.com", json={"grants": ["feat:insights"]}, headers=hb).status_code == 200
        c.cookies.clear()
        yield c, app.state.insight_store, s
        app.state.user_store, app.state.agent_audit, app.state.token_store, app.state.insight_store = keep
        ps.close()
    app.dependency_overrides.pop(get_settings, None)


def _ids(r) -> list:
    assert r.status_code == 200, r.text
    return [x["id"] for x in r.json()["items"]]


def test_초안은_주인만_보고_확인하면_같은_소속에_열린다(env):
    c, st, _s = env
    _relay(st)
    cid = "ins:web:c1:r1:default"
    _login(c, "me@example.com")
    assert _ids(c.get("/insights-api/find", params={"sp_task": KEY})) == [cid]
    mine = c.get("/insights-api/mine").json()
    assert [x["id"] for x in mine["draft"]] == [cid] and mine["draft"][0]["mine"] is True
    for who in ("peer@example.com", "out@example.com"):
        _login(c, who)
        assert _ids(c.get("/insights-api/find", params={"sp_task": KEY})) == []
        assert c.get(f"/insights-api/cards/{cid}").status_code == 404, "남의 초안은 없는 것과 같다"
    h = _login(c, "me@example.com")
    r = c.post(f"/insights-api/cards/{cid}/confirm", headers=h)
    assert r.status_code == 200 and r.json()["status"] == "confirmed" and r.json()["scope"] == ["aff:CAEG"], r.text
    _login(c, "peer@example.com")
    assert _ids(c.get("/insights-api/find", params={"sp_task": KEY, "round": "dv1"})) == [cid]
    body = c.get("/insights-api/project", params={"sp_task": KEY}).json()
    assert [(cell["round"], [x["id"] for x in cell["cards"]]) for cell in body["rounds"]] == [("dv1", [cid])]
    assert "calls" not in body["rounds"][0]["cards"][0] and c.get(f"/insights-api/cards/{cid}").json()["calls"] == []
    _login(c, "out@example.com")
    assert _ids(c.get("/insights-api/find", params={"sp_task": KEY})) == [], "다른(없는) 소속은 못 본다"


def test_소속이_바뀌면_시야도_바뀐다(env):
    c, st, _s = env
    _relay(st)
    cid = "ins:web:c1:r1:default"
    h = _login(c, "me@example.com")
    assert c.post(f"/insights-api/cards/{cid}/confirm", headers=h).status_code == 200
    hb = _login(c, "boss@example.com")
    assert c.patch("/auth/access/users/peer@example.com", json={"affiliation": "", "grants": ["feat:insights"]},
                   headers=hb).status_code == 200
    _login(c, "peer@example.com")
    assert _ids(c.get("/insights-api/find")) == []


def test_MCP_잡_주인의_자칭_소속으로는_넓히지_않는다(env):
    c, st, _s = env
    I.ingest_jobs(st, [_item(owner_aff="OTHER-TEAM")])
    cid = "ins:delib:default-1:default"
    _login(c, "peer@example.com")
    assert c.get(f"/insights-api/cards/{cid}").status_code == 404, "MCP 잡 카드도 주인 확인 전에는 주인만"
    h = _login(c, "me@example.com")
    r = c.post(f"/insights-api/cards/{cid}/confirm", headers=h).json()
    assert r["scope"] == ["aff:CAEG"] and r["owner"] == "me@example.com", "넓힐 때의 소속은 포털 원장의 지금 값이다"
    assert st.get(cid)["owner_sub"], "주인이 처음 손댈 때 포털 subject 를 단다"


def test_앞_카드는_읽는_사람이_볼_수_있을_때만_잇는다(env):
    c, st, _s = env
    I.ingest_jobs(st, [_item("prev"), _item("next", continues="prev", finished_at=1001.0)])
    h = _login(c, "me@example.com")
    assert c.post("/insights-api/cards/ins:delib:next:default/confirm", headers=h).status_code == 200
    mine = {x["id"]: x["continues"] for x in c.get("/insights-api/find").json()["items"]}
    assert mine["ins:delib:next:default"] == "ins:delib:prev:default", "주인은 자기 앞 카드를 본다"
    _login(c, "peer@example.com")
    rows = c.get("/insights-api/find").json()["items"]
    assert [x["id"] for x in rows] == ["ins:delib:next:default"] and rows[0]["continues"] is None, "초안인 앞 카드는 있다는 것도 말하지 않는다"
    assert c.get("/insights-api/cards/ins:delib:next:default").json()["continues"] is None
    cell = c.get("/insights-api/project", params={"sp_task": KEY}).json()["rounds"][0]["cards"]
    assert cell[0]["continues"] is None


def test_관리자는_다_보되_범위_밖_읽기를_감사에_남기고_거둔_것은_못_본다(env):
    c, st, s = env
    _relay(st)
    cid = "ins:web:c1:r1:default"
    _login(c, "boss@example.com")
    assert c.get(f"/insights-api/cards/{cid}").status_code == 200
    with closing(sqlite3.connect(s.agent_audit_log_path)) as db:
        rows = db.execute("SELECT event, meta FROM agent_audit WHERE event='insight_admin_read'").fetchall()
    assert rows and json.loads(rows[-1][1])["ids"] == [cid]
    h = _login(c, "me@example.com")
    assert c.post(f"/insights-api/cards/{cid}/withdraw", headers=h).json() == {"id": cid, "status": "withdrawn"}
    for who in ("me@example.com", "boss@example.com"):
        _login(c, who)
        assert c.get(f"/insights-api/cards/{cid}").status_code == 404 and _ids(c.get("/insights-api/find")) == []


def test_기다림_줄은_과제_보기에_없고_주제를_확인하면_초안이_선다(env, monkeypatch):
    c, st, _s = env
    _relay(st, subject=CLAIMED)
    cid = "ins:web:c1:r1:default"
    h = _login(c, "me@example.com")
    assert _ids(c.get("/insights-api/find")) == [] and c.get("/insights-api/projects").json()["projects"] == []
    assert [x["id"] for x in c.get("/insights-api/mine").json()["waiting"]] == [cid]
    assert c.post(f"/insights-api/cards/{cid}/confirm", headers=h).status_code == 409, "주제부터"
    asked = {}

    async def fake_confirm(settings, *, subject, principal, pat, chair_template):
        asked.update(subject=subject, email=principal.email, chair=chair_template, pat=bool(pat))
        return ({**CONFIRMED, "sp_task": subject["sp_task"]} if subject["sp_task"] == KEY else {**CLAIMED, "sp_task": subject["sp_task"]}), ""
    monkeypatch.setattr(I, "confirm_async", fake_confirm)
    r = c.post(f"/insights-api/cards/{cid}/subject", json={"sp_task": "틀린 key"}, headers=h).json()
    assert r["confirmed"] is False and r["status"] == "waiting"
    r = c.post(f"/insights-api/cards/{cid}/subject", json={"sp_task": KEY}, headers=h).json()
    assert r["confirmed"] is True and r["status"] == "draft" and st.get(cid)["sp_task"] == KEY
    assert asked == {"subject": {"sp_task": KEY, "round": "dv1", "text": "알파 1차", "artifacts": [{"kind": "ecad", "id": "abcdef0123456789"}]},
                     "email": "me@example.com", "chair": "default", "pat": True}, "글 · 설계 자료는 처음 주제 그대로, 확인은 에이전트 서버가"
    assert c.post(f"/insights-api/cards/{cid}/subject", json={"sp_task": KEY, "sp_state": "confirmed"}, headers=h).status_code == 422


def test_차수가_다르면_다른_칸이고_차수_모름은_따로다(env):
    c, st, _s = env
    _relay(st, cid="a")
    _relay(st, cid="b", subject={**CONFIRMED, "round": None, "round_by": None})
    _relay(st, cid="d", subject={**CONFIRMED, "round": "pv1"})
    h = _login(c, "me@example.com")
    body = c.get("/insights-api/project", params={"sp_task": KEY}).json()
    assert [(cell["round"], len(cell["cards"])) for cell in body["rounds"]] == [("dv1", 1), ("pv1", 1), (None, 1)]
    assert _ids(c.get("/insights-api/find", params={"round": "unknown"})) == ["ins:web:b:r1:default"]
    assert c.get("/insights-api/find", params={"round": "2차"}).status_code == 422, "꼴이 아닌 차수는 거름이 아니다"
    assert c.post("/insights-api/cards/ins:web:b:r1:default/round", json={"round": "DV2"}, headers=h).json()["subject"]["round"] == "dv2"
    assert c.post("/insights-api/cards/ins:web:b:r1:default/round", json={"round": "C2"}, headers=h).status_code == 422
    r = c.post("/insights-api/cards/ins:web:b:r1:default/round", json={"round": "unknown"}, headers=h).json()
    assert r["subject"]["round"] is None and r["subject"]["round_by"] == "person", "사람이 고른 '차수 모름' 도 사람이 단 차수다"
    projects = c.get("/insights-api/projects").json()["projects"]
    assert projects == [{"sp_task": KEY, "rounds": {"dv1": 1, "pv1": 1, "unknown": 1}, "total": 3, "latest_at": projects[0]["latest_at"],
                         "risk": 0}]


def test_쓰기는_세션과_CSRF_만이고_주인만_한다(env):
    c, st, s = env
    _relay(st)
    cid = "ins:web:c1:r1:default"
    _login(c, "me@example.com")
    assert c.post(f"/insights-api/cards/{cid}/confirm").status_code == 403, "CSRF 없이"
    pat = R._chat_user_pat(app.state.keystore, s, _principal("me@example.com"))
    c.cookies.clear()
    auth = {"Authorization": f"Bearer {pat}"}
    assert _ids(c.get("/insights-api/find", headers=auth)) == [cid], "PAT 로 읽는다(게이트웨이 insight_find 의 길)"
    assert c.post(f"/insights-api/cards/{cid}/confirm", headers=auth).status_code == 401, "PAT 로는 쓰지 못한다"
    _relay(st, owner="peer@example.com", cid="p1")
    h = _login(c, "peer@example.com")
    assert c.post(f"/insights-api/cards/{cid}/withdraw", headers=h).status_code == 404, "남의 초안은 없는 것과 같다"
    hm = _login(c, "me@example.com")
    assert c.post(f"/insights-api/cards/{cid}/confirm", headers=hm).status_code == 200
    h = _login(c, "peer@example.com")
    assert c.post(f"/insights-api/cards/{cid}/claim", json={"claim": "고침"}, headers=h).status_code == 403, "보이지만 주인이 아니다"


def _principal(email):
    from app.auth.provider import Principal
    return Principal(subject=email, email=email, display_name=email, groups=[])


def test_주장_고치기_반박_조직_공개(env):
    c, st, _s = env
    _relay(st, cid="a")
    _relay(st, cid="b", cards=({**CARD, "tools": ["find_part"], "apps": ["heax-step_forge"]},))
    a, b = "ins:web:a:r1:default", "ins:web:b:r1:default"
    h = _login(c, "me@example.com")
    r = c.post(f"/insights-api/cards/{a}/claim", json={"claim": "  사람이 고친 결론  "}, headers=h).json()
    assert r["claim"] == "사람이 고친 결론" and r["claim_from"] == "person" and r["claim_edited_by"] == "me@example.com"
    assert c.post(f"/insights-api/cards/{a}/claim", json={"claim": "가" * 501}, headers=h).status_code == 422
    assert c.post(f"/insights-api/cards/{a}/widen", json={"to": "org"}, headers=h).status_code == 409, "확인 전"
    for cid in (a, b):
        assert c.post(f"/insights-api/cards/{cid}/confirm", headers=h).status_code == 200
    r = c.post(f"/insights-api/cards/{a}/widen", json={"to": "org"}, headers=h)
    assert r.status_code == 200 and r.json()["scope"] == ["org"], "근거가 없는 카드는 근거 범위를 다 안다"
    r = c.post(f"/insights-api/cards/{b}/widen", json={"to": "org"}, headers=h)
    assert r.status_code == 409 and "근거 범위" in r.json()["detail"]
    _login(c, "out@example.com")
    assert _ids(c.get("/insights-api/find")) == [a], "조직 공개는 다른 소속도 본다"
    h = _login(c, "me@example.com")
    r = c.post(f"/insights-api/cards/{b}/dispute", json={"by_card": a, "note": "뒤 심의가 틀렸다고"}, headers=h).json()
    assert r["status"] == "disputed"
    full = c.get(f"/insights-api/cards/{b}").json()
    assert full["disputed_by"] == [{"by": a, "note": "뒤 심의가 틀렸다고", "at": full["disputed_by"][0]["at"]}]
    assert c.get(f"/insights-api/cards/{a}").json()["disputes"] == [b]
    _login(c, "out@example.com")
    assert c.get(f"/insights-api/cards/{a}").json()["disputes"] == [], "보이지 않는 카드로의 잇기는 말하지 않는다"


def test_확인할_때_근거_앱은_plat_토큰이_되고_앱을_모르면_그렇다고_단다(env):
    c, st, _s = env
    _relay(st, cards=({**CARD, "tools": ["risk_get_diff", "x_tool"], "apps": ["heax-hwax_risk"], "apps_unknown": ["x_tool"]},))
    h = _login(c, "me@example.com")
    r = c.post("/insights-api/cards/ins:web:c1:r1:default/confirm", headers=h).json()
    assert r["scope"] == ["aff:CAEG", "plat:risk"] and "앱을 몰라" in r["scope_note"]


def test_리스크_행은_읽는_사람의_PAT_로_리스크_앱에서_같은_칸에_싣는다(env, monkeypatch):
    c, st, _s = env
    _relay(st)
    calls = []

    async def fake_mcp(url, pat, tool, args, timeout=0):
        calls.append((tool, args, bool(pat)))
        return {"caller": "user", "projects": [{"project_id": "p1", "sp_task": KEY, "stage": "dv1", "round": "dv1", "targets": []},
                                               {"project_id": "p2", "sp_task": KEY, "stage": "dv", "round": None, "targets": []},
                                               {"project_id": "p3", "sp_task": "다른 과제", "stage": "pv1", "round": "pv1"}]}
    from app.agent import upload as _upload
    monkeypatch.setattr(_upload, "mcp_call", fake_mcp)
    _login(c, "me@example.com")
    body = c.get("/insights-api/project", params={"sp_task": KEY}).json()
    assert [(cell["round"], len(cell["cards"]), [p["project_id"] for p in cell["risk"]]) for cell in body["rounds"]] == [
        ("dv1", 1, ["p1"]), (None, 0, ["p2"])], "꼴이 아닌 stage(dv)는 차수 모름 칸 · 다른 과제는 싣지 않는다"
    assert calls[0] == (IR.RISK_TOOL, {"sp_task": KEY, "limit": 50}, True)
    projects = {p["sp_task"]: p for p in c.get("/insights-api/projects").json()["projects"]}
    assert projects[KEY]["risk"] == 2 and projects["다른 과제"]["total"] == 0 and projects["다른 과제"]["risk"] == 1

    async def broken(*_a, **_k):
        raise httpx.ConnectError("x")
    monkeypatch.setattr(_upload, "mcp_call", broken)
    body = c.get("/insights-api/project", params={"sp_task": KEY}).json()
    assert "리스크 앱을 읽지 못했다" in body["risk_error"] and body["rounds"][0]["cards"], "일반 심의 카드는 그대로 보인다"


def test_리스크_앱_답이_남으면_다음_쪽을_이어_받고_상한에서_멈추면_말한다(env, monkeypatch):
    """리스크 앱은 결과 상한(약 2만 5천 자)에서 과제 수를 줄이고 truncated · next_offset 으로 나눈다 — 첫 쪽만 싣고 조용히 끝내지 않는다."""
    c, st, _s = env
    calls = []

    def pager(nxt_of):
        async def fake_mcp(url, pat, tool, args, timeout=0):
            calls.append(dict(args))
            off = int(args.get("offset") or 0)
            nxt = nxt_of(off)
            return {"caller": "user", "projects": [{"project_id": f"p{off}", "sp_task": f"과제 {off}", "stage": "dv1"}],
                    "total": 9, "truncated": nxt is not None, **({} if nxt is None else {"next_offset": nxt})}
        return fake_mcp
    from app.agent import upload as _upload
    _login(c, "me@example.com")
    monkeypatch.setattr(_upload, "mcp_call", pager(lambda off: off + 1 if off < 2 else None))
    body = c.get("/insights-api/projects").json()
    assert [a.get("offset") for a in calls] == [None, 1, 2] and "risk_error" not in body
    assert sorted(p["sp_task"] for p in body["projects"]) == ["과제 0", "과제 1", "과제 2"]
    calls.clear()
    monkeypatch.setattr(_upload, "mcp_call", pager(lambda off: off + 1))
    body = c.get("/insights-api/projects").json()
    assert len(calls) == IR.RISK_PAGES_MAX and f"앞 {IR.RISK_PAGES_MAX}개만" in body["risk_error"]
    calls.clear()
    monkeypatch.setattr(_upload, "mcp_call", pager(lambda off: off))
    body = c.get("/insights-api/projects").json()
    assert len(calls) == 1 and "다음 쪽이 없어 앞 1개" in body["risk_error"], "제자리 next_offset 은 돌지 않고 말한다"


# ── Claude 워크플로 — 대화 저장 뒤 ─────────────────────────────────────────────────────────────────────────
WF_DEC = "결정 — 보강한다.\n\n---\n\n■ 쉬운 설명\n### 한마디로\n리브를 보강하라는 결정이다\n### 왜 그런가\n- 응력"


def test_워크플로_대화는_저장한_뒤_다시_풀어_한_장으로_들이고_저장은_막지_않는다(env, monkeypatch):
    c, st, s = env
    seen = []

    def fake_confirm(settings, *, subject, principal, pat, chair_template):
        seen.append((subject, principal.email, chair_template, bool(pat)))
        if subject.get("sp_task") == "없는 과제":
            return {**CLAIMED, "sp_task": "없는 과제"}, ""
        if subject.get("sp_task") is None:
            return None, "과제가 없는 주제다 — 잇지 않는다"
        return CONFIRMED, ""
    monkeypatch.setattr(I, "confirm_sync", fake_confirm)
    _login(c, "me@example.com")
    pat = R._chat_user_pat(app.state.keystore, s, _principal("me@example.com"))
    c.cookies.clear()
    auth = {"Authorization": f"Bearer {pat}"}
    msgs = [{"role": "user", "content": "q"}, {"role": "persona", "persona": "a", "content": "발언"},
            {"role": "assistant", "content": "(결정문 1/2)\n" + WF_DEC[:20]}, {"role": "assistant", "content": "(결정문 2/2)\n" + WF_DEC[20:]}]
    r = c.post("/agent/conversations", json={"title": "심의 — 알파", "kind": "deliberation", "source": "mcp", "messages": msgs,
                                             "subject": {"sp_task": KEY, "round": "dv1"}, "chair_template": "sim-plan"}, headers=auth).json()
    cid = r["id"]
    assert r["insight"] == {"id": f"ins:wf:{cid}", "status": "draft"}
    row = st.get(f"ins:wf:{cid}")
    assert (row["path"], row["stage"], row["claim"], row["claim_from"], row["card"]["apps_unknown"]) == (
        "mcp-workflow", "sim-plan", "리브를 보강하라는 결정이다", "plain", ["(workflow)"])
    assert seen[0] == ({"sp_task": KEY, "round": "dv1"}, "me@example.com", "sim-plan", True)
    for extra, want in (({"chair_template": "risk-review"}, "리스크 심사"), ({"kind": "risk-review"}, "리스크 심사"),
                        ({"source": "web"}, "source=mcp"), ({"subject": {"sp_task": "없는 과제"}}, None)):
        body = {"title": "t", "kind": "deliberation", "source": "mcp", "messages": msgs, "subject": {"sp_task": KEY}, **extra}
        out = c.post("/agent/conversations", json=body, headers=auth).json()
        assert out["id"] and ((want in out["insight"]["skipped"]) if want else out["insight"]["status"] == "waiting"), out
    out = c.post("/agent/conversations", json={"title": "t", "kind": "deliberation", "source": "mcp", "messages": msgs,
                                               "subject": "문자열", "chair_template": "Bad Name"}, headers=auth).json()
    assert set(out) == {"id"}, "꼴이 아닌 주제는 없는 것과 같다 — 저장은 그대로"


def test_큰_워크플로는_덧붙인_결정문으로_주장을_다시_뽑는다(env, monkeypatch):
    c, st, s = env
    monkeypatch.setattr(I, "confirm_sync", lambda settings, **kw: (CONFIRMED, ""))
    _login(c, "me@example.com")
    pat = R._chat_user_pat(app.state.keystore, s, _principal("me@example.com"))
    c.cookies.clear()
    auth = {"Authorization": f"Bearer {pat}"}
    cid = c.post("/agent/conversations", json={"title": "t", "kind": "deliberation", "source": "mcp", "subject": {"sp_task": KEY},
                                               "messages": [{"role": "user", "content": "q"}]}, headers=auth).json()["id"]
    assert st.get(f"ins:wf:{cid}")["claim"] == ""
    for part in ("(결정문 1/2)\n" + WF_DEC[:25], "(결정문 2/2)\n" + WF_DEC[25:]):
        assert c.post(f"/agent/conversations/{cid}/messages", json={"role": "assistant", "content": part}, headers=auth).status_code == 200
    assert st.get(f"ins:wf:{cid}")["claim"] == "리브를 보강하라는 결정이다"
    st.update(f"ins:wf:{cid}", claim="사람 글", claim_edited_by="me@example.com")
    c.post(f"/agent/conversations/{cid}/messages", json={"role": "assistant", "content": "추가"}, headers=auth)
    assert st.get(f"ins:wf:{cid}")["claim"] == "사람 글", "사람이 고친 주장은 건드리지 않는다"


# ── 웹 중계 끝까지 ─────────────────────────────────────────────────────────────────────────────────────────
def _sse(frames) -> bytes:
    return "".join(f"event: {ev}\ndata: {json.dumps(d, ensure_ascii=False)}\n\n" for ev, d in frames).encode()


class _Body(httpx.AsyncByteStream):
    """에이전트 서버 자리의 SSE — 프레임 경계와 안 맞는 조각으로 흘린다(중계가 완결 프레임만 읽는지도 함께 본다)."""

    def __init__(self, raw: bytes, step: int = 29) -> None:
        self.raw, self.step = raw, step

    async def __aiter__(self):
        for i in range(0, len(self.raw), self.step):
            yield self.raw[i:i + self.step]


@pytest.mark.parametrize("opts,want", [({}, 1), ({"chair_template": "risk-review"}, 0), ({"started_by": "app"}, 0)])
def test_중계는_에이전트가_낸_카드_거리를_답을_남길_때_들인다(env, opts, want):
    c, st, _s = env
    raw = _sse([("delib", {"kind": "subject", "subject": CONFIRMED, "run_id": "r9"}), ("delib", {"kind": "decision", "text": "결정"}),
                ("delib", {"kind": "insight", **CARD}), ("result", {"type": "text", "content": "결정"}), ("done", {})])
    real = app.state.agent_client
    app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(
        lambda req: httpx.Response(200, stream=_Body(raw), headers={"content-type": "text/event-stream"})))
    try:
        h = _login(c, "me@example.com")
        cid = c.post("/agent/conversations", json={"title": "t", "kind": "deliberation"}, headers=h).json()["id"]
        r = c.post("/agent/chat", json={"message": "/심의 화두", "conversation_id": cid, "delib_opts": opts}, headers=h)
        assert r.status_code == 200, r.text
    finally:
        app.state.agent_client = real
    rows = st.rows(owner_email="me@example.com")
    assert len(rows) == want
    if want:
        assert rows[0]["id"] == f"ins:web:{cid}:r9:default" and rows[0]["status"] == "draft"


# ── 반대 검토 11-02 — 재현해 고친 것(context-notes PG-35) ───────────────────────────────────────────────────────────
def test_남의_초안이_많아도_보이는_카드가_목록에서_밀려나지_않는다(env, monkeypatch):
    """읽기 창(최근 N장)이 남의 초안까지 세면 보이는 확인 카드가 목록 · 과제에서 사라졌다(반대 검토 6). 창은 읽는 사람의 것과 공유 상태만 센다."""
    from app.insights import store as S
    c, st, _s = env
    monkeypatch.setattr(S, "ROWS_MAX", 20)
    _relay(st, cid="old")
    old = "ins:web:old:r1:default"
    h = _login(c, "me@example.com")
    assert c.post(f"/insights-api/cards/{old}/confirm", headers=h).status_code == 200
    for i in range(30):
        _relay(st, owner="out@example.com", cid=f"z{i:03d}")
    with st._conn() as con:
        con.execute("UPDATE insight_cards SET created_at = created_at - 100 WHERE id=?", (old,))
    _login(c, "peer@example.com")
    assert _ids(c.get("/insights-api/find")) == [old]
    assert [p["sp_task"] for p in c.get("/insights-api/projects").json()["projects"]] == [KEY]
    _login(c, "boss@example.com")
    body = c.get("/insights-api/projects").json()
    assert body.get("truncated") is True and "최근" in body["note_rows"], "관리자 창은 남의 초안도 세고, 넘치면 말한다"


def test_당기기는_커서_창이_빽빽해도_따라잡는다(store, monkeypatch):
    """커서보다 600초 앞부터 다시 읽는데 그 창에 쪽 상한(5×200)보다 많은 항목이 있으면 커서가 영영 못 넘어갔다(반대 검토 7). 상한에서 멈춘 다음
    당기기는 겹침 없이 커서부터 잇는다."""
    items = [_item(f"j{i:05d}", finished_at=1000.0 + i * 0.05) for i in range(1300)]

    def handler(req):
        since, lim = float(req.url.params["since"]), int(req.url.params["limit"])
        hit = [it for it in items if it["finished_at"] >= since]
        page = hit[:lim]
        return httpx.Response(200, json={"contract": I.AGENT_CONTRACT, "items": page,
                                         "next_since": max((it["finished_at"] for it in page), default=since),
                                         "complete": len(hit) <= lim})
    app_, s, cli = _sync_app(store, handler)
    monkeypatch.setattr(I.httpx, "AsyncClient", cli)

    def pull(times: int) -> int:
        for _ in range(times):
            monkeypatch.setattr(I, "_SYNC", {"at": 0.0, "lock": None, "loop": None, "last": None})
            asyncio.run(I.sync_jobs(app_, s, force=True))
        with store._conn() as con:
            return con.execute("SELECT COUNT(*) FROM insight_cards").fetchone()[0]
    assert pull(2) == len(items), "상한에서 멈춘 다음 당기기가 커서부터 잇는다"
    assert store.meta_get("jobs_partial") == "0"
    items.extend(_item(f"k{i}", finished_at=2000.0 + i) for i in range(5))
    assert pull(2) == len(items), "겹쳐 읽는 창이 빽빽해도(상한에서 멈춰도) 그다음 당기기가 새 항목을 들인다"


def test_관리자가_잇기로_본_남의_초안_id_도_감사에_남는다(env):
    c, st, s = env
    I.ingest_jobs(st, [_item("prev", user="peer%40example.com"),
                       _item("next", user="boss%40example.com", continues="prev", finished_at=1001.0)])
    _login(c, "boss@example.com")
    body = c.get("/insights-api/cards/ins:delib:next:default").json()
    assert body["continues"] == "ins:delib:prev:default"
    with closing(sqlite3.connect(s.agent_audit_log_path)) as db:
        metas = [json.loads(m) for (m,) in db.execute("SELECT meta FROM agent_audit WHERE event='insight_admin_read'").fetchall()]
    assert any("ins:delib:prev:default" in m["ids"] for m in metas), metas
    c.get("/insights-api/mine")
    with closing(sqlite3.connect(s.agent_audit_log_path)) as db:
        n = db.execute("SELECT COUNT(*) FROM agent_audit WHERE event='insight_admin_read'").fetchone()[0]
    assert n == 2, "내 카드 목록이 잇는 남의 초안도 감사에 남는다"


def test_보이지_않는_카드가_반박하면_반박_줄은_누가인지만_가린다(env):
    """반박한 카드가 읽는 사람에게 안 보이면 상태만 '반박' 이고 줄은 비어, 숨은 카드가 있다는 것만 드러났다(반대 검토 9). 줄은 남기고 반박한
    카드만 가린다 — 카드 없이 단 반박과 같은 꼴이다."""
    c, st, _s = env
    _relay(st, cid="a")
    _relay(st, cid="b")
    a, b = "ins:web:a:r1:default", "ins:web:b:r1:default"
    h = _login(c, "me@example.com")
    assert c.post(f"/insights-api/cards/{a}/confirm", headers=h).status_code == 200
    assert c.post(f"/insights-api/cards/{a}/dispute", json={"by_card": b, "note": "시험 뒤 다시"}, headers=h).status_code == 200
    _login(c, "peer@example.com")
    full = c.get(f"/insights-api/cards/{a}").json()
    assert full["status"] == "disputed" and [(d["by"], d["note"]) for d in full["disputed_by"]] == [(None, "시험 뒤 다시")]
    listed = c.get("/insights-api/project", params={"sp_task": KEY}).json()["rounds"][0]["cards"][0]
    assert [(d["by"], d["note"]) for d in listed["disputed_by"]] == [(None, "시험 뒤 다시")]


def test_주제_확인은_사람이_단_차수를_지킨다(env, monkeypatch):
    """기다림 줄 카드에 사람이 단 차수(모름 포함)를 주제 확인이 옛 주제의 차수로 되돌렸다(반대 검토 10)."""
    c, st, _s = env
    asked = []

    async def fake_confirm(settings, *, subject, principal, pat, chair_template):
        asked.append(dict(subject))
        return {**CONFIRMED, "sp_task": subject["sp_task"], "round": subject.get("round") or "dv2",
                "round_by": "person" if subject.get("round") else "spec"}, ""
    monkeypatch.setattr(I, "confirm_async", fake_confirm)
    _relay(st, subject=CLAIMED)
    cid = "ins:web:c1:r1:default"
    h = _login(c, "me@example.com")
    assert c.post(f"/insights-api/cards/{cid}/round", json={"round": "pv1"}, headers=h).status_code == 200
    r = c.post(f"/insights-api/cards/{cid}/subject", json={"sp_task": KEY}, headers=h).json()
    assert asked[-1]["round"] == "pv1" and (r["subject"]["round"], r["subject"]["round_by"]) == ("pv1", "person")
    _relay(st, subject=CLAIMED, cid="c2")
    cid2 = "ins:web:c2:r1:default"
    assert c.post(f"/insights-api/cards/{cid2}/round", json={"round": "unknown"}, headers=h).status_code == 200
    r = c.post(f"/insights-api/cards/{cid2}/subject", json={"sp_task": KEY}, headers=h).json()
    assert "round" not in asked[-1] and (r["subject"]["round"], r["subject"]["round_by"]) == (None, "person"), "고른 '모름' 도 지킨다"

