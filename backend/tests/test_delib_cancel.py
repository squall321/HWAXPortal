# 도는 웹 심의 멈춤(POST /agent/deliberate/cancel) — 세션 + CSRF · 대화 주인만 · 에이전트 서버의 답을 그대로 넘기고, 중계는 멈춤 사건을 대화에 남긴다
"""docs/leftovers-1017 triage A24 (나) — 사용자 결정 10-31.

웹 심의는 에이전트 서버의 분리 태스크라 화면이 떠나도 서버에서 끝까지 돌았고 멈출 길이 없었다(docs/change-request-8-10/server-setup §6).
포털 창구가 대화 주인을 확인하고 에이전트 서버 POST /deliberate/cancel 을 부른다. 고정하는 것.
  · 주인은 멈춘다 — 에이전트에 대화 id · 누가(by) · 그 사람(user_email)을 싣는다(에이전트는 그 사람의 심의만 접는다).
  · 남의 대화는 403 not_owner — 관리자도 같다(MCP deliberate_cancel 의 규칙). 없는 대화는 404 conversation_not_found. 둘 다 에이전트를 부르지 않는다.
  · CSRF 가 없거나 어긋나면 403, 세션이 없으면 401(PAT 는 받지 않는다).
  · 에이전트의 답(200 · 404 delib_not_found · 409 already_finished)은 상태 · 본문 그대로. code 없는 404 는 agent_outdated, 닿지 못하면 502,
    늦으면 504, code 없는 5xx 는 502 agent_5xx.
  · 중계가 멈춤 사건(delib kind=cancelled)을 받으면 받은 발언과 멈춤을 서버 대화에 남긴다(결정문으로 남기지 않는다).
에이전트 서버는 httpx.MockTransport 로 흉내 낸다. 에이전트 쪽 실제 프로세스 시험은 HWAXAgentServer tests/test_web_delib_cancel_e2e.py 다.
"""
import json
import shutil
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.access.policy import AccessPolicy
from app.agent.conv_store import ConversationStore
from app.auth.user_store import UserStore
from app.catalog.registry import CatalogRegistry
from app.config import Settings, get_settings
from app.main import app

_CONFIG = Path(__file__).resolve().parents[1] / "config"
OWNER, OTHER, ADMIN = "user@corp.com", "other@corp.com", "boss@corp.com"
_OK = {"conversation_id": "", "status": "cancelling", "runs": 1, "message": "멈춤을 요청했다"}


class _Agent:
    """에이전트 서버 대역 — 받은 요청을 적고, answer(req) 로 답한다(기본은 200 cancelling)."""

    def __init__(self) -> None:
        self.seen: list[httpx.Request] = []
        self.answer = lambda req: httpx.Response(200, json={**_OK, "conversation_id": json.loads(req.content)["conversation_id"]})

    def __call__(self, req: httpx.Request) -> httpx.Response:
        self.seen.append(req)
        return self.answer(req)


@pytest.fixture()
def portal(tmp_path):
    for name in ("systems.yaml", "access.yaml"):
        shutil.copy(_CONFIG / name, tmp_path / name)
    (tmp_path / "routes.env").write_text("\n")
    s = Settings(_env_file=None, user_store_path=str(tmp_path / "users.sqlite"), local_bootstrap_admins=ADMIN,
                 catalog_path=str(tmp_path / "systems.yaml"), routes_path=str(tmp_path / "routes.env"),
                 access_path=str(tmp_path / "access.yaml"), conv_store_path=str(tmp_path / "conv.db"),
                 agent_server_url="http://agent.invalid")
    app.dependency_overrides[get_settings] = lambda: s
    from app.auth.routes.local import _rl
    _rl.clear()
    with TestClient(app) as c:
        # 기동 뒤 바꿔 끼운다 — 실 계정 원장 · 대화 저장소 · 에이전트 서버를 건드리지 않는다
        keep = (app.state.user_store, app.state.access, app.state.catalog, app.state.conv_store, app.state.agent_client)
        app.state.user_store, app.state.access, app.state.catalog = UserStore(s), AccessPolicy(s), CatalogRegistry(s)
        app.state.conv_store = ConversationStore(s)
        agent = _Agent()
        app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(agent))
        for email in (ADMIN, OWNER, OTHER):
            c.post("/auth/local/signup", json={"email": email, "name": email.split("@")[0], "password": "pw123456"})
        h = _login(c, ADMIN)
        for email in (OWNER, OTHER):
            assert c.post(f"/auth/local/users/{email}/approve", json={"groups": []}, headers=h).status_code == 200
        try:
            yield c, agent
        finally:
            app.state.user_store, app.state.access, app.state.catalog, app.state.conv_store, app.state.agent_client = keep
    app.dependency_overrides.pop(get_settings, None)


def _login(c: TestClient, email: str) -> dict:
    r = c.post("/auth/local/login", json={"email": email, "password": "pw123456"})
    assert r.status_code == 200, r.text
    return {"X-CSRF-Token": c.cookies.get("hwax_csrf")}


def _conv(c: TestClient, h: dict) -> str:
    r = c.post("/agent/conversations", json={"title": "심의", "kind": "deliberation"}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _cancel(c: TestClient, cid: str, h: dict | None):
    return c.post("/agent/deliberate/cancel", json={"conversation_id": cid}, headers=h or {})


def _audit_rows() -> list[dict]:
    rows = app.state.agent_audit._conn.execute(
        "SELECT event, status, meta FROM agent_audit WHERE event = 'delib_cancel' ORDER BY id").fetchall()
    return [{"event": e, "status": st, "meta": json.loads(m) if m else None} for e, st, m in rows]


# ── 주인 ─────────────────────────────────────────────────────────────────────────────────────────
def test_주인은_멈추고_에이전트에_대화_id_와_그_사람을_싣는다(portal):
    c, agent = portal
    h = _login(c, OWNER)
    cid = _conv(c, h)
    n = len(_audit_rows())
    r = _cancel(c, cid, h)
    assert r.status_code == 200, r.text
    assert r.json() == {**_OK, "conversation_id": cid}, "에이전트의 답이 그대로 온다"
    (req,) = agent.seen
    assert (req.method, req.url.path) == ("POST", "/deliberate/cancel")
    assert json.loads(req.content) == {"conversation_id": cid, "by": OWNER, "user_email": OWNER}
    row = _audit_rows()[n:]
    assert row == [{"event": "delib_cancel", "status": "ok", "meta": {"conversation": cid, "upstream": 200}}], row


# ── 남 · 없는 대화 · 관리자 ──────────────────────────────────────────────────────────────────────────
def test_남의_대화는_403_not_owner_이고_에이전트를_부르지_않는다(portal):
    c, agent = portal
    cid = _conv(c, _login(c, OWNER))
    r = _cancel(c, cid, _login(c, OTHER))
    assert r.status_code == 403 and r.json()["code"] == "not_owner", r.text
    assert agent.seen == []
    assert _audit_rows()[-1] == {"event": "delib_cancel", "status": "rejected", "meta": {"conversation": cid, "code": "not_owner"}}


def test_관리자도_남의_심의는_멈추지_못한다(portal):
    """MCP deliberate_cancel(에이전트 delib_jobs.cancel 의 _foreign)과 같은 규칙 — 관리자는 볼 수 있어도 접지는 못한다."""
    c, agent = portal
    cid = _conv(c, _login(c, OWNER))
    r = _cancel(c, cid, _login(c, ADMIN))
    assert r.status_code == 403 and r.json()["code"] == "not_owner", r.text
    assert agent.seen == []


def test_없는_대화는_404_conversation_not_found_이고_에이전트를_부르지_않는다(portal):
    c, agent = portal
    r = _cancel(c, "0" * 32, _login(c, OWNER))
    assert r.status_code == 404 and r.json()["code"] == "conversation_not_found", r.text
    assert agent.seen == []


# ── 인증 · CSRF · 본문 ───────────────────────────────────────────────────────────────────────────────
def test_CSRF_가_없거나_어긋나면_403_이고_에이전트를_부르지_않는다(portal):
    c, agent = portal
    h = _login(c, OWNER)
    cid = _conv(c, h)
    for bad in (None, {"X-CSRF-Token": "forged"}):
        r = _cancel(c, cid, bad)
        assert r.status_code == 403 and "CSRF" in r.json()["detail"], r.text
    assert agent.seen == []


def test_세션이_없으면_401_이고_PAT_는_받지_않는다(portal):
    c, agent = portal
    cid = _conv(c, _login(c, OWNER))
    c.cookies.clear()
    assert _cancel(c, cid, None).status_code == 401
    assert _cancel(c, cid, {"Authorization": "Bearer anything"}).status_code == 401
    assert agent.seen == []


def test_본문의_모르는_칸은_422_다(portal):
    c, agent = portal
    h = _login(c, OWNER)
    cid = _conv(c, h)
    r = c.post("/agent/deliberate/cancel", json={"conversation_id": cid, "user_email": ADMIN}, headers=h)
    assert r.status_code == 422, "호출자가 실은 신원 칸은 받지 않는다 — 에이전트에 가는 신원은 세션의 것뿐이다"
    assert agent.seen == []


# ── 에이전트의 답 ─────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("status, body", [
    (404, {"code": "delib_not_found", "conversation_id": "X", "message": "이 대화에서 도는 웹 심의가 없다"}),
    (409, {"code": "already_finished", "conversation_id": "X", "status": "done", "message": "이미 끝난 심의다"}),
    (200, {"conversation_id": "X", "status": "cancelled", "runs": 0, "already": True, "message": "이미 멈춘 심의다"}),
], ids=["404", "409", "already"])
def test_에이전트의_답은_상태와_본문_그대로_온다(portal, status, body):
    c, agent = portal
    h = _login(c, OWNER)
    cid = _conv(c, h)
    agent.answer = lambda req: httpx.Response(status, json=body)
    r = _cancel(c, cid, h)
    assert (r.status_code, r.json()) == (status, body)
    assert _audit_rows()[-1]["meta"] == {"conversation": cid, "upstream": status,
                                         **({"code": body["code"]} if "code" in body else {})}


@pytest.mark.parametrize("answer, status, code", [
    (lambda req: httpx.Response(404, json={"detail": "Not Found"}), 404, "agent_outdated"),
    (lambda req: httpx.Response(500, text="boom"), 502, "agent_5xx"),
], ids=["옛-에이전트", "5xx"])
def test_code_없는_404_는_옛_에이전트_code_없는_5xx_는_502(portal, answer, status, code):
    c, agent = portal
    h = _login(c, OWNER)
    agent.answer = answer
    r = _cancel(c, _conv(c, h), h)
    assert (r.status_code, r.json()["code"]) == (status, code), r.text


@pytest.mark.parametrize("exc, status, code", [
    (httpx.ConnectError("refused"), 502, "agent_unreachable"),
    (httpx.ReadTimeout("slow"), 504, "agent_timeout"),
], ids=["닿지-못함", "늦음"])
def test_에이전트에_닿지_못하거나_늦으면_502_504(portal, exc, status, code):
    c, agent = portal
    h = _login(c, OWNER)

    def boom(req):
        raise exc

    agent.answer = boom
    r = _cancel(c, _conv(c, h), h)
    assert (r.status_code, r.json()["code"]) == (status, code), r.text
    assert _audit_rows()[-1]["status"] == "error"


# ── 중계가 멈춤 사건을 대화에 남긴다 ─────────────────────────────────────────────────────────────────────
_STOP = "사람이 멈췄다 — 지금까지의 발언은 남고, 결정문 · 보고서는 만들지 않았다"


class _Body(httpx.AsyncByteStream):
    """상류 SSE 본문 — 청크를 프레임 경계와 어긋나게 쪼갠다(중계는 완결 프레임만 읽는다)."""

    def __init__(self, raw: bytes, step: int = 37) -> None:
        self.raw, self.step = raw, step

    async def __aiter__(self):
        for i in range(0, len(self.raw), self.step):
            yield self.raw[i:i + self.step]


def test_중계가_멈춤_사건을_받으면_발언과_멈춤을_대화에_남기고_결정문으로_남기지_않는다(portal):
    c, _agent = portal
    h = _login(c, OWNER)
    cid = _conv(c, h)
    frames = [("delib", {"kind": "stage", "stage": "r1"}),
              ("delib", {"kind": "turn", "round": 1, "persona": "mech-a", "say": "초기 입장"}),
              ("delib", {"kind": "cancelled", "by": OWNER, "message": _STOP}), ("done", {})]
    raw = "".join(f"event: {ev}\ndata: {json.dumps(d, ensure_ascii=False)}\n\n" for ev, d in frames).encode()
    app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(
        lambda req: httpx.Response(200, stream=_Body(raw), headers={"content-type": "text/event-stream"})))
    r = c.post("/agent/chat", json={"message": "/심의 힌지", "conversation_id": cid}, headers=h)
    assert r.status_code == 200 and '"cancelled"' in r.text
    msgs = c.get(f"/agent/conversations/{cid}", headers=h).json()["messages"]
    assert [m["role"] for m in msgs] == ["user", "persona", "assistant"], msgs
    assert msgs[1]["content"] == "초기 입장"
    assert msgs[2]["content"] == _STOP and msgs[2]["meta"]["delib_cancelled"] == {"message": _STOP, "by": OWNER}
    # 다른 기기 · 새로고침이 되살린 심의 — 멈춤은 멈춤으로, 결정문으로 그리지 않는다(conversations.api.ts serverMessagesToLocal)
    local = _restore(msgs)
    assert local[-1]["delib"].get("cancelled") == {"message": _STOP} and "decision" not in local[-1]["delib"], local[-1]
    assert [t["say"] for t in local[-1]["delib"]["turns"]] == ["초기 입장"]


def test_결정문_뒤에_멈춘_심의는_결정문과_멈춤을_함께_되살린다():
    """다단 심의(/시뮬심의)는 1단 결정문을 낸 뒤 2단에서 멈출 수 있다 — 답의 글은 1단 결정문이고 meta 가 멈춤을 말한다."""
    local = _restore([{"role": "persona", "persona": "mech-a", "round": 1, "content": "발언", "meta": None, "ts": 1},
                      {"role": "assistant", "persona": None, "round": None, "content": "1단 결정문",
                       "meta": {"delib_cancelled": {"message": _STOP, "by": OWNER}}, "ts": 2}])
    assert local[-1]["delib"]["decision"] == "1단 결정문" and local[-1]["delib"]["cancelled"] == {"message": _STOP}


# 프론트에는 단위 시험 러너가 없어 그 파일을 typescript 로 옮겨 적어 node 로 부른다(test_conv_save_full 과 같은 길).
_FE = Path(__file__).resolve().parents[2] / "frontend"


def _restore(server_messages: list[dict]) -> list[dict]:
    import subprocess
    import tempfile

    if not (_FE / "node_modules/typescript").exists() or not shutil.which("node"):
        pytest.skip("frontend node_modules(typescript) 또는 node 가 없다")
    out = Path(tempfile.mkdtemp(prefix="delib-cancel-restore-"))
    try:
        (out / "api").mkdir()
        (out / "state").mkdir()
        (out / "api" / "client.js").write_text("exports.apiFetch = async () => { throw new Error('시험에서 부르지 않는다'); };\n")
        (out / "in.json").write_text(json.dumps(server_messages, ensure_ascii=False), encoding="utf-8")
        (out / "build.cjs").write_text(
            "const ts = require('typescript'); const fs = require('fs');\n"
            f"const src = {json.dumps(str(_FE / 'src'))};\n"
            "for (const [from, to] of [['api/conversations.api.ts', 'api/conversations.api.js'], ['state/chatStore.ts', 'state/chatStore.js']]) {\n"
            "  const js = ts.transpileModule(fs.readFileSync(src + '/' + from, 'utf8'),\n"
            "    { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } });\n"
            "  fs.writeFileSync(__dirname + '/' + to, js.outputText);\n"
            "}\n"
            "const { serverMessagesToLocal } = require('./api/conversations.api.js');\n"
            "const msgs = JSON.parse(fs.readFileSync(__dirname + '/in.json', 'utf8'));\n"
            "process.stdout.write(JSON.stringify(serverMessagesToLocal(msgs)));\n", encoding="utf-8")
        r = subprocess.run(["node", "build.cjs"], cwd=str(out), capture_output=True, text=True, timeout=120,
                           env={"PATH": "/usr/bin:/bin:" + str(Path(shutil.which("node")).parent),
                                "NODE_PATH": str(_FE / "node_modules")})
    finally:
        shutil.rmtree(out, ignore_errors=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return json.loads(r.stdout)
