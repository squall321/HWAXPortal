# 포털 챗 MCP Apps 패널 호스트 창구(docs/request-1027 HP-42 · 설계 B5.4 · B6 P3) — 손잡이 · 세션+CSRF · feat:panels · ui:// · 크기 · mime · 허용 도구 · 첫 쓰기 확인 · 누적 · 남의 panel_id · 서버 사본 · 감사
"""받아들이는 기준(design-ha09-ha20.md B6 P3). 게이트웨이 자리는 MCP JSON-RPC 를 흉내 내는 가짜(httpx.MockTransport)다 — 진짜 게이트웨이의 패널 PAT
판별은 게이트웨이 리포의 두 리포 계약 시험이 이 리포의 발급기(app/agent/panel_pat.py)를 그대로 읽어 본다. 여기서는 포털이 무엇을 보내는지
(패널 PAT 의 꼴 · 서명 · 부르는 도구)를 가짜가 받은 그대로 판정한다.
"""
import ast
import json
import os
import sqlite3
from pathlib import Path

import httpx
import jwt
import pytest
from fastapi.testclient import TestClient

from app.agent import panel as P
from app.agent import panel_pat
from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.main import app

_URI = "ui://simflow/workflow"
_HTML = "<!doctype html><html><head><title>w</title></head><body>panel</body></html>"
_SECRET_ARG = "ARG-BODY-7c1e"            # 인자 본문 — 포털 감사에 실리면 안 된다


class _FakeGW:
    """게이트웨이 대역 — /tools-map 과 /mcp(JSON-RPC: initialize · tools/list · resources/read · tools/call · DELETE). 받은 요청을 남긴다.
    tools/list 는 진짜 게이트웨이의 패널 PAT 범위를 흉내 내지 않고 일부러 앱 밖 · 막음 도구를 섞는다 — 포털의 거르기를 따로 본다."""

    def __init__(self, *, mime="text/html;profile=mcp-app", html=_HTML, read=("list_runs", "open_workflow_panel"), csp=None, missing=False,
                 old_key=False):
        self.mime, self.html, self.read, self.csp, self.missing = mime, html, read, csp, missing
        self.old_key = old_key             # 패널 도구가 옛 키("ui/resourceUri")만 단다 — 다른 판의 앱(B7 사양 판 어긋남)
        self.reqs: list[dict] = []
        self.sids: set[str] = set()
        self.deleted: list[str] = []
        self.n = 0

    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/tools-map":
            return httpx.Response(200, json={
                "map": {"open_workflow_panel": "simflow", "list_runs": "simflow", "submit_run": "simflow", "model_only": "simflow",
                        "trash_report": "simflow", "arp_list": "arp", "invoke_tool": "_gateway"},
                "routine_read": list(self.read) if self.read is not None else None,
                "apps": [{"app": "simflow", "label": "SimFlow"}, {"app": "arp", "label": "ARP"}]})
        assert request.url.path == "/mcp", request.url
        sid = request.headers.get("mcp-session-id", "")
        if request.method == "DELETE":
            self.deleted.append(sid)
            self.sids.discard(sid)
            return httpx.Response(200)
        body = json.loads(request.content)
        m = body.get("method")
        self.reqs.append({"method": m, "auth": request.headers.get("authorization", ""), "sid": sid,
                          "corr": request.headers.get("x-hwax-corr", ""), "params": body.get("params")})
        if m == "initialize":
            self.n += 1
            new = f"sid-{self.n}"
            self.sids.add(new)
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": body["id"], "result": {"protocolVersion": "2025-06-18",
                                  "capabilities": {}, "serverInfo": {"name": "gw", "version": "1"}}}, headers={"mcp-session-id": new})
        if m == "notifications/initialized":
            return httpx.Response(202)
        if sid not in self.sids:
            self.reqs.pop()                                # 실행되지 않은 요청 — 받은 호출로 세지 않는다
            return httpx.Response(404, json={"error": "session not found"})
        if m == "tools/list":
            tools = [{"name": n, "inputSchema": {"type": "object"}} for n in ("list_runs", "submit_run", "trash_report", "arp_list",
                                                                                  "invoke_tool")]
            tools.append({"name": "open_workflow_panel", "inputSchema": {"type": "object"},
                          "_meta": {"ui/resourceUri": _URI} if self.old_key else {"ui": {"resourceUri": _URI}}})
            tools.append({"name": "model_only", "inputSchema": {"type": "object"}, "_meta": {"ui": {"visibility": ["model"]}}})
            return self._sse(body["id"], {"tools": tools})
        if m == "resources/read":
            if body["params"]["uri"] != _URI or self.missing:
                return httpx.Response(200, json={"jsonrpc": "2.0", "id": body["id"], "error": {"code": -32002, "message": "Resource not found"}})
            meta = {"ui": {"prefersBorder": False, **({"csp": self.csp} if self.csp else {})}}
            return self._sse(body["id"], {"contents": [{"uri": _URI, "mimeType": self.mime, "text": self.html, "_meta": meta}]})
        if m == "tools/call":
            p = body["params"]
            return self._sse(body["id"], {"content": [{"type": "text", "text": f"ok {p['name']}"}], "structuredContent": {"n": 1},
                                          "_meta": {"viewer": "v"}, "isError": False})
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": body.get("id"), "error": {"code": -32601, "message": "nope"}})

    @staticmethod
    def _sse(rid, result) -> httpx.Response:
        # 진짜 서버처럼 알림 한 줄 뒤에 결과 — 포털은 id 가 맞는 줄을 골라야 한다
        text = (f"event: message\ndata: {json.dumps({'jsonrpc': '2.0', 'method': 'notifications/message', 'params': {}})}\n\n"
                f"event: message\ndata: {json.dumps({'jsonrpc': '2.0', 'id': rid, 'result': result})}\n\n")
        return httpx.Response(200, text=text, headers={"content-type": "text/event-stream"})

    def calls(self, method="tools/call") -> list[dict]:
        return [r for r in self.reqs if r["method"] == method]


@pytest.fixture()
def kit(tmp_path, monkeypatch):
    made: list = []

    def _make(*, on=True, fake: _FakeGW | None = None, **over):
        s = Settings(user_store_path=str(tmp_path / f"u{len(made)}.sqlite"), local_bootstrap_admins="boss@corp.com",
                     mcp_apps_host=on, mcp_gateway_url="http://gw.test", **over)
        app.dependency_overrides[get_settings] = lambda: s
        from app.auth.routes.local import _rl
        _rl.clear()
        gw = fake or _FakeGW()
        transport = httpx.MockTransport(gw.handler)
        monkeypatch.setattr(P, "_client_factory", lambda timeout: httpx.AsyncClient(timeout=timeout, transport=transport))
        monkeypatch.setattr(P, "_GW_MAP", {"at": float("-inf"), "map": None, "read": None, "labels": {}})
        monkeypatch.setattr(P, "_TABLE", {})
        c = TestClient(app)
        c.__enter__()
        app.state.user_store = UserStore(s)
        made.append(c)
        return c, gw, s

    yield _make
    for c in made:
        c.__exit__(None, None, None)
    app.dependency_overrides.pop(get_settings, None)


def _login(c, email, *, boss=None, grants=None):
    c.post("/auth/local/signup", json={"email": email, "name": email, "password": "pw123456"})
    if boss is not None:
        assert c.post(f"/auth/local/users/{email}/approve", json={"groups": []}, headers=boss).status_code == 200
        c.post("/auth/local/logout", headers=boss)
    if grants is not None:
        app.state.user_store.set_access(email, grants=grants)
    assert c.post("/auth/local/login", json={"email": email, "password": "pw123456"}).status_code == 200
    return {"X-CSRF-Token": c.cookies.get("hwax_csrf")}


def _open(c, h, **body):
    return c.post("/agent/panel/open", json={"uri": _URI, "tool": "open_workflow_panel", "call": "run-1", **body}, headers=h)


# ── 손잡이 · 세션 + CSRF · 권한 ─────────────────────────────────────────────────────────────────────────────────────

def test_P3_손잡이가_끄면_다섯_창구가_다_404(kit):
    c, gw, _ = kit(on=False)
    h = _login(c, "boss@corp.com")
    for path, body in (("open", {"uri": _URI, "tool": "open_workflow_panel"}), ("call", {"panel_id": "x" * 10, "name": "list_runs"}),
                       ("read", {"panel_id": "x" * 10, "uri": _URI}), ("confirm", {"panel_id": "x" * 10, "token": "t" * 10}),
                       ("close", {"panel_id": "x" * 10})):
        assert c.post(f"/agent/panel/{path}", json=body, headers=h).status_code == 404, path
    assert gw.reqs == [], "꺼진 박스는 게이트웨이를 부르지 않는다"


def test_P3_세션과_CSRF_로만_받는다_PAT_는_받지_않는다(kit):
    c, gw, _ = kit()
    h = _login(c, "boss@corp.com")
    assert _open(c, {}).status_code == 403, "CSRF 머리 없이"
    assert _open(c, {"X-CSRF-Token": "forged"}).status_code == 403
    pat = c.post("/auth/pat", json={"name": "t", "ttl_days": 1}, headers=h).json()["token"]
    c.post("/auth/local/logout", headers=h)
    c.cookies.clear()
    r = c.post("/agent/panel/open", json={"uri": _URI, "tool": "open_workflow_panel"}, headers={"Authorization": f"Bearer {pat}"})
    assert r.status_code == 401, "패널은 브라우저 탭에서만 산다 — 개인 PAT 로는 못 연다"
    assert gw.calls("resources/read") == []


def test_P3_feat_panels_가_없으면_403(kit):
    c, gw, _ = kit()
    boss = _login(c, "boss@corp.com")
    h = _login(c, "plain@corp.com", boss=boss)
    r = _open(c, h)
    assert r.status_code == 403 and "feat:panels" in r.text and gw.reqs == []


def test_P3_ui_주소만_받는다(kit):
    c, gw, _ = kit()
    h = _login(c, "boss@corp.com")
    for bad in ("https://evil.example/x.html", "file:///etc/passwd", "javascript:alert(1)"):
        assert _open(c, h, uri=bad).status_code == 422, bad
    assert _open(c, h, tool="no_such_tool").status_code == 404, "지도에 없는 도구"
    assert _open(c, h, tool="invoke_tool").status_code == 404, "게이트웨이 자체 도구는 패널을 내지 않는다"
    assert gw.calls("resources/read") == []


# ── 열기 — 패널 PAT · mime · 크기 · CSP ────────────────────────────────────────────────────────────────────────────

def test_P3_열면_패널_PAT_로_게이트웨이를_부르고_HTML_과_허용_도구를_준다(kit):
    c, gw, s = kit()
    h = _login(c, "boss@corp.com")
    r = _open(c, h)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["html"] == _HTML and j["app"] == "simflow" and j["app_label"] == "SimFlow" and j["uri"] == _URI
    assert j["prefers_border"] is False and j["csp"] == {"connectDomains": [], "resourceDomains": []}
    assert j["tools"] == ["list_runs", "open_workflow_panel", "submit_run"], "앱 밖 · 막음 · 모델 전용 도구는 뺀다"
    auths = {x["auth"] for x in gw.reqs}
    assert len(auths) == 1
    tok = auths.pop().removeprefix("Bearer ")
    pub = app.state.keystore.public_pem(app.state.keystore.active_kid)
    claims = jwt.decode(tok, pub, algorithms=["RS256"], audience=s.panel_pat_audience)
    assert (claims["purpose"], claims["panel"], claims["aud"], claims["scope"]) == (
        panel_pat.PANEL_PURPOSE, {"app": "simflow", "uri": _URI}, [panel_pat.PANEL_AUDIENCE], "api")
    assert claims["jti"].startswith(panel_pat.PANEL_JTI_PREFIX) and claims["exp"] - claims["iat"] == 900
    assert claims["email"] == "boss@corp.com" and not any(g.startswith(("feat:", "plat:")) for g in claims["groups"])
    with pytest.raises(jwt.InvalidAudienceError):
        jwt.decode(tok, pub, algorithms=["RS256"], audience=s.pat_chat_audience)    # 챗 · MCP 청중으로는 통하지 않는다
    assert all(x["corr"].startswith("panel:") for x in gw.reqs if x["method"] in ("tools/list", "resources/read"))
    assert gw.calls() == [], "열기(기록의 '다시 열기' 포함)는 도구를 부르지 않는다 — 목록 · 리소스 읽기뿐이다(B7 두 번 실행)"


def test_P3_옛_키_ui_resourceUri_만_단_패널_도구도_연다(kit):
    """B7 사양 판 어긋남 — 앱이 옛 키("ui/resourceUri")를 내면 게이트웨이가 그대로 옮긴다(HG-07). 포털이 새 키만 보면 그 패널은 늘 404 다."""
    c, gw, _ = kit(fake=_FakeGW(old_key=True))
    h = _login(c, "boss@corp.com")
    r = _open(c, h)
    assert r.status_code == 200 and r.json()["html"] == _HTML, r.text
    assert _open(c, h, uri="ui://simflow/other").json()["detail"]["code"] == "panel_uri_mismatch", "옛 키도 그 도구가 단 주소만 연다"


@pytest.mark.parametrize("mime,html,code,status", [
    ("text/plain", _HTML, "panel_bad_mime", 502),
    ("application/javascript", _HTML, "panel_bad_mime", 502),
    ("text/html;profile=mcp-app", "가" * 2_000_000, "panel_html_too_large", 413),
])
def test_P3_mime_와_크기가_틀리면_열지_않고_게이트웨이_세션을_닫는다(kit, mime, html, code, status):
    c, gw, _ = kit(fake=_FakeGW(mime=mime, html=html))
    h = _login(c, "boss@corp.com")
    r = _open(c, h)
    assert r.status_code == status and r.json()["detail"]["code"] == code, r.text
    assert gw.deleted == ["sid-1"] and P._TABLE == {}


def test_P3_게이트웨이가_없는_주소라고_하면_404_이고_세션을_닫는다(kit):
    c, gw, _ = kit(fake=_FakeGW(missing=True))
    h = _login(c, "boss@corp.com")
    r = _open(c, h)
    assert r.status_code == 404 and r.json()["detail"]["code"] == "panel_resource_unavailable" and gw.deleted == ["sid-1"]


def test_P3_없는_리소스는_404_이고_CSP_는_박스_허용과의_교집합만(kit):
    c, gw, _ = kit(fake=_FakeGW(csp={"connectDomains": ["https://api.simflow.example", "https://evil.example", "x;script-src *"],
                                     "resourceDomains": ["https://cdn.simflow.example"], "frameDomains": ["https://f.example"]}),
                   panel_allowed_origins="https://api.simflow.example, https://other.example")
    h = _login(c, "boss@corp.com")
    assert _open(c, h, uri="ui://simflow/none").status_code == 404, "그 도구가 단 주소가 아니다"
    r = _open(c, h, uri="ui://simflow/status", tool="list_runs")
    assert r.status_code == 404 and r.json()["detail"]["code"] == "panel_uri_mismatch", "패널 도구가 아닌 도구로 같은 앱의 다른 주소를 열지 않는다"
    assert gw.calls("resources/read") == []
    j = _open(c, h).json()
    assert j["csp"] == {"connectDomains": ["https://api.simflow.example"], "resourceDomains": []}, "청한 것 ∩ 박스 허용 · 꼴이 틀리면 버린다"


# ── 부르기 — 허용 도구 · 크기 · 누적 · 첫 쓰기 확인 · 남의 panel_id ────────────────────────────────────────────────────

def test_P3_허용_도구만_부르고_결과는_그대로_돌려준다(kit):
    c, gw, _ = kit()
    h = _login(c, "boss@corp.com")
    pid = _open(c, h).json()["panel_id"]
    r = c.post("/agent/panel/call", json={"panel_id": pid, "name": "list_runs", "arguments": {"q": _SECRET_ARG}}, headers=h)
    assert r.status_code == 200 and r.json() == {"result": {"content": [{"type": "text", "text": "ok list_runs"}],
                                                            "structuredContent": {"n": 1}, "_meta": {"viewer": "v"}, "isError": False}}
    for name in ("arp_list", "invoke_tool", "trash_report", "model_only", "rest_call"):
        rr = c.post("/agent/panel/call", json={"panel_id": pid, "name": name, "arguments": {}}, headers=h)
        assert rr.status_code == 403 and rr.json()["detail"]["code"] == "tool_not_allowed", name
    assert [x["params"]["name"] for x in gw.calls()] == ["list_runs"]
    assert len({x["sid"] for x in gw.reqs if x["method"] != "initialize"}) == 1, "패널마다 MCP 세션 하나를 열어 둔다"


def test_P3_인자_크기와_세션_누적_상한(kit):
    c, gw, _ = kit(panel_call_max_bytes=1000, panel_session_max_mb=1)
    h = _login(c, "boss@corp.com")
    pid = _open(c, h).json()["panel_id"]
    big = c.post("/agent/panel/call", json={"panel_id": pid, "name": "list_runs", "arguments": {"b": "x" * 2000}}, headers=h)
    assert big.status_code == 413 and big.json()["detail"]["code"] == "call_too_large" and "파일 올리기" in big.text
    P._TABLE[pid].used = 1024 * 1024 - 10
    cap = c.post("/agent/panel/call", json={"panel_id": pid, "name": "list_runs", "arguments": {"b": "x" * 100}}, headers=h)
    assert cap.status_code == 413 and cap.json()["detail"]["code"] == "session_cap"
    assert gw.calls() == []


def test_P3_첫_쓰기는_확인을_묻고_확인_뒤에는_묻지_않는다(kit):
    c, gw, _ = kit()
    h = _login(c, "boss@corp.com")
    pid = _open(c, h).json()["panel_id"]
    r = c.post("/agent/panel/call", json={"panel_id": pid, "name": "submit_run", "arguments": {"case": "A"}}, headers=h)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "confirm_required" and gw.calls() == [], "확인 전에는 보내지 않는다"
    tok = r.json()["detail"]["token"]
    assert c.post("/agent/panel/confirm", json={"panel_id": pid, "token": "wrong-token-xx"}, headers=h).status_code == 409
    assert c.post("/agent/panel/confirm", json={"panel_id": pid, "token": tok}, headers={}).status_code == 403, "CSRF"
    assert c.post("/agent/panel/confirm", json={"panel_id": pid, "token": tok}, headers=h).json() == {"ok": True}
    assert c.post("/agent/panel/confirm", json={"panel_id": pid, "token": tok}, headers=h).status_code == 409, "한 번만"
    for _ in range(2):
        assert c.post("/agent/panel/call", json={"panel_id": pid, "name": "submit_run", "arguments": {}}, headers=h).status_code == 200
    assert len(gw.calls()) == 2
    # 읽기 목록을 모르는 게이트웨이(옛 판)면 읽기 도구도 쓰기로 본다(모르면 묻는다)
    c2, gw2, _ = kit(fake=_FakeGW(read=None))
    h2 = _login(c2, "boss@corp.com")
    pid2 = _open(c2, h2).json()["panel_id"]
    assert c2.post("/agent/panel/call", json={"panel_id": pid2, "name": "list_runs", "arguments": {}}, headers=h2).status_code == 409


def test_P3_한꺼번에_온_쓰기_둘은_확인_하나로_풀린다(kit):
    c, gw, _ = kit()
    h = _login(c, "boss@corp.com")
    pid = _open(c, h).json()["panel_id"]
    t1, t2 = (c.post("/agent/panel/call", json={"panel_id": pid, "name": "submit_run", "arguments": {"i": i}}, headers=h).json()["detail"]["token"]
              for i in (1, 2))
    assert t1 != t2 and gw.calls() == []
    assert c.post("/agent/panel/confirm", json={"panel_id": pid, "token": t1}, headers=h).json() == {"ok": True}
    r = c.post("/agent/panel/confirm", json={"panel_id": pid, "token": t2}, headers=h)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "no_pending_confirm", "확인은 세션마다 한 번 — 남은 토큰은 지웠다"
    assert c.post("/agent/panel/call", json={"panel_id": pid, "name": "submit_run", "arguments": {}}, headers=h).status_code == 200


def test_P3_남의_panel_id_는_없는_것과_같다(kit):
    c, gw, _ = kit()
    boss = _login(c, "boss@corp.com")
    pid = _open(c, boss).json()["panel_id"]
    h = _login(c, "other@corp.com", boss=boss, grants=["feat:panels"])
    for path, body in (("call", {"panel_id": pid, "name": "list_runs", "arguments": {}}), ("read", {"panel_id": pid, "uri": _URI}),
                       ("confirm", {"panel_id": pid, "token": "t" * 12})):
        r = c.post(f"/agent/panel/{path}", json=body, headers=h)
        assert r.status_code == 404 and r.json()["detail"]["code"] == "panel_not_found", path
    assert c.post("/agent/panel/close", json={"panel_id": pid}, headers=h).json() == {"ok": True}
    assert pid in P._TABLE, "남이 닫지 못한다"
    assert gw.calls() == []


def test_P3_닫으면_게이트웨이_세션도_닫고_끝난_세션은_404(kit):
    c, gw, s = kit()
    h = _login(c, "boss@corp.com")
    pid = _open(c, h).json()["panel_id"]
    assert c.post("/agent/panel/close", json={"panel_id": pid}, headers=h).json() == {"ok": True}
    assert gw.deleted == ["sid-1"] and pid not in P._TABLE
    assert c.post("/agent/panel/call", json={"panel_id": pid, "name": "list_runs", "arguments": {}}, headers=h).status_code == 404
    pid2 = _open(c, h).json()["panel_id"]
    P._TABLE[pid2].last -= s.panel_idle_s + 1
    assert c.post("/agent/panel/call", json={"panel_id": pid2, "name": "list_runs", "arguments": {}}, headers=h).status_code == 404


def test_P3_게이트웨이를_재기동해_세션을_잃으면_한_번_다시_연다(kit):
    c, gw, _ = kit()
    h = _login(c, "boss@corp.com")
    pid = _open(c, h).json()["panel_id"]
    gw.sids.clear()                                        # 게이트웨이가 다시 떴다 — 옛 세션 id 는 404
    r = c.post("/agent/panel/call", json={"panel_id": pid, "name": "list_runs", "arguments": {}}, headers=h)
    assert r.status_code == 200 and len(gw.calls()) == 1 and gw.n == 2


def test_P3_패널의_리소스_읽기는_ui_주소만(kit):
    c, gw, _ = kit()
    h = _login(c, "boss@corp.com")
    pid = _open(c, h).json()["panel_id"]
    assert c.post("/agent/panel/read", json={"panel_id": pid, "uri": "https://x.example/a"}, headers=h).status_code == 422
    assert c.post("/agent/panel/read", json={"panel_id": pid, "uri": _URI}, headers=h).json()["result"]["contents"][0]["text"] == _HTML
    assert c.post("/agent/panel/read", json={"panel_id": pid, "uri": "ui://arp/board"}, headers=h).json()["error"]["code"] == -32002


# ── 감사 · 서버 사본 ──────────────────────────────────────────────────────────────────────────────────────────────

def _audit_rows(event_prefix="panel_"):
    path = get_settings().resolve(get_settings().agent_audit_log_path)
    with sqlite3.connect(path) as db:
        return [dict(zip(("event", "tool", "status", "meta"), r)) for r in db.execute(
            "SELECT event, tool, status, meta FROM agent_audit WHERE event LIKE ? ORDER BY id", (event_prefix + "%",))]


def test_P3_감사는_앱_도구_주소_크기_성패를_남기고_인자_본문은_남기지_않는다(kit):
    before = len(_audit_rows())
    c, gw, _ = kit()
    h = _login(c, "boss@corp.com")
    pid = _open(c, h).json()["panel_id"]
    c.post("/agent/panel/call", json={"panel_id": pid, "name": "list_runs", "arguments": {"q": _SECRET_ARG}}, headers=h)
    tok = c.post("/agent/panel/call", json={"panel_id": pid, "name": "submit_run", "arguments": {}}, headers=h).json()["detail"]["token"]
    c.post("/agent/panel/confirm", json={"panel_id": pid, "token": tok}, headers=h)
    rows = _audit_rows()[before:]
    assert [(r["event"], r["status"]) for r in rows] == [("panel_open", "ok"), ("panel_call", "ok"), ("panel_call", "confirm_required"),
                                                         ("panel_confirm", "ok")]
    m = json.loads(rows[1]["meta"])
    assert rows[1]["tool"] == "list_runs" and m["app"] == "simflow" and m["uri"] == _URI and m["ok"] is True
    assert m["bytes"] > 0 and isinstance(m["ms"], int) and m["corr"].startswith("panel:")
    assert m["corr"] in {x["corr"] for x in gw.calls()}, "게이트웨이 감사와 같은 호출 id 로 잇는다"
    assert not any(_SECRET_ARG in (r["meta"] or "") for r in rows), "인자 본문은 감사에 없다"


class _Turn(httpx.AsyncByteStream):
    """에이전트 서버 대역 — 패널 도구 상태줄 · ui_resource · 답."""

    def __init__(self, frames):
        self.frames = frames

    async def __aiter__(self):
        for f in self.frames:
            yield f

    async def aclose(self):
        pass


def _sse(evt, data):
    return f"event: {evt}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode()


def _chat_turn(c, app_, h, *, ui_host="mcp-apps/1", auth=None):
    sent = {}
    ev = {"call": "run-1", "tool": "open_workflow_panel", "app": "simflow", "uri": _URI, "input": {"case": _SECRET_ARG},
          "result": {"content": [{"type": "text", "text": "t"}], "structuredContent": {"x": _SECRET_ARG}, "_meta": {"m": _SECRET_ARG}}}

    def upstream(req):
        sent["payload"] = json.loads(req.content)
        return httpx.Response(200, stream=_Turn([_sse("status", {"step": "도구 완료: open_workflow_panel", "tool": "open_workflow_panel",
                                                                     "call": "run-1", "ok": True}),
                                                 _sse("ui_resource", ev), _sse("token", {"delta": "열었습니다"}),
                                                 _sse("result", {"type": "text", "content": "열었습니다"}), _sse("done", {})]),
                              headers={"content-type": "text/event-stream"})
    real = app_.state.agent_client
    app_.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(upstream))
    try:
        cid = c.post("/agent/conversations", json={"title": "t"}, headers=h).json()["id"]
        body = {"message": "패널 열어줘", "conversation_id": cid, **({"ui_host": ui_host} if ui_host else {})}
        hdrs = {**h, **({"Authorization": auth} if auth else {})}
        with c.stream("POST", "/agent/chat", json=body, headers=hdrs) as r:
            text = "".join(r.iter_text())
        msgs = c.get(f"/agent/conversations/{cid}", headers=h).json()["messages"]
    finally:
        app_.state.agent_client = real
    return sent["payload"], text, msgs


def test_P3_서버_사본에는_패널_포인터만_남고_표지는_조건이_다_맞을_때만_싣는다(kit):
    c, gw, _ = kit()
    h = _login(c, "boss@corp.com")
    _open(c, h)                                           # 앱 라벨을 붙잡아 둔다(포인터의 제목)
    payload, text, msgs = _chat_turn(c, app, h)
    assert payload["ui_host"] == "mcp-apps/1"
    assert "ui_resource" in text, "중계는 사건을 그대로 넘긴다(화면이 결과를 쓴다)"
    meta = [m for m in msgs if m["role"] == "assistant"][-1]["meta"]
    assert meta["panels"] == [{"app": "simflow", "tool": "open_workflow_panel", "uri": _URI, "call": "run-1", "title": "SimFlow"}]
    assert _SECRET_ARG not in json.dumps(msgs, ensure_ascii=False), "결과 · 입력 · _meta 는 서버 사본에 없다(B-4 · B-6)"
    for ui_host in (None, "mcp-apps/2"):
        p2, _t, m2 = _chat_turn(c, app, h, ui_host=ui_host)
        assert "ui_host" not in p2 and "panels" not in ([m for m in m2 if m["role"] == "assistant"][-1]["meta"] or {}), ui_host


def test_P3_PAT_로_온_챗은_표지를_싣지_않는다(kit):
    """스크립트 · 개인 Claude 의 챗에는 패널을 그릴 화면이 없다(패널 창구도 세션만 받는다)."""
    c, gw, _ = kit()
    h = _login(c, "boss@corp.com")
    pat = c.post("/auth/pat", json={"name": "t", "ttl_days": 1}, headers=h).json()["token"]
    p, _t, _m = _chat_turn(c, app, h, auth=f"Bearer {pat}")
    assert "ui_host" not in p, p


def test_P3_손잡이가_끄거나_권한이_없으면_표지를_싣지_않는다(kit):
    c, gw, _ = kit(on=False)
    h = _login(c, "boss@corp.com")
    p, _t, msgs = _chat_turn(c, app, h)
    assert "ui_host" not in p and "panels" not in ([m for m in msgs if m["role"] == "assistant"][-1]["meta"] or {})
    c2, _gw2, _ = kit()
    boss = _login(c2, "boss@corp.com")
    h2 = _login(c2, "plain@corp.com", boss=boss)
    p2, _t2, _m2 = _chat_turn(c2, app, h2)
    assert "ui_host" not in p2, "feat:panels 없음"


# ── 두 리포 계약(형제 리포가 이 박스에 있을 때 — 워크트리는 HWAX_GATEWAY_REPO · HWAX_AGENT_REPO 로 가리킨다) ────────────────────────────

_ROOT = Path(__file__).resolve().parents[2]


def _sibling(env: str, name: str) -> Path:
    return Path(os.environ.get(env) or _ROOT.parent / name)


def _module_literals(path: Path) -> dict:
    out: dict = {}
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    v = node.value
                    if isinstance(v, ast.Call) and getattr(v.func, "attr", "") == "get" and len(v.args) == 2:
                        v = v.args[1]                                  # PORTAL.get("panel_audience", "<기본값>") — 기본값을 읽는다
                    try:
                        out[t.id] = ast.literal_eval(v)
                    except ValueError:
                        pass
    return out


def test_P3_게이트웨이_판별_글자가_포털_발급기와_같다():
    gw = _sibling("HWAX_GATEWAY_REPO", "HWAXMcpGateway") / "gateway.py"
    if not gw.exists():
        pytest.skip(f"형제 게이트웨이 리포 없음: {gw}")
    lit = _module_literals(gw)
    if "PANEL_PURPOSE" not in lit:
        pytest.skip("형제 게이트웨이가 아직 패널 PAT 를 모른다 — 패널 PAT 는 그 청중을 몰라 401 로 닫힌다(새지 않는다)")
    assert (lit["PANEL_PURPOSE"], lit["PANEL_JTI_PREFIX"], lit["PANEL_AUDIENCE"]) == (
        panel_pat.PANEL_PURPOSE, panel_pat.PANEL_JTI_PREFIX, panel_pat.PANEL_AUDIENCE)
    assert panel_pat.PANEL_TTL_S <= lit["PANEL_MAX_TTL_S"]
    assert Settings().panel_pat_audience == panel_pat.PANEL_AUDIENCE


def test_P3_에이전트_서버_표지_글자와_요청_칸이_같다():
    ag = _sibling("HWAX_AGENT_REPO", "HWAXAgentServer")
    if not (ag / "ui_panels.py").exists():
        pytest.skip(f"형제 에이전트 서버에 패널 표지가 없다({ag}) — 표지를 실어도 그쪽 ChatRequest 가 버린다(HA-05 그대로)")
    assert _module_literals(ag / "ui_panels.py")["HOST_TOKEN"] == P.UI_HOST_TOKEN
    tree = ast.parse((ag / "app.py").read_text(encoding="utf-8"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ChatRequest")
    assert "ui_host" in {s.target.id for s in cls.body if isinstance(s, ast.AnnAssign) and isinstance(s.target, ast.Name)}
