# 리스크 심사 종합 보고서 판을 그 사람 명의로 Report Archive 초안으로 — 포털 창구 POST /agent/risk-report/ra-draft(docs/risk-review-redesign RA 초안 문)
"""사용자 결정 2026-11-22(docs/leftovers-1121 L21-17 ④) — RA 에 쓰는 것은 포털이다(그 사람의 RA 연결로). 리스크 앱은 재료를 내주고 원장만 적는다.

가짜 셋 + 진짜 포털 앱(TestClient)으로 끝에서 끝까지 본다.
  · 가짜 게이트웨이(httpx MockTransport — upload._TRANSPORT) — streamable-http 한 왕복(initialize → notifications/initialized → tools/call →
    DELETE)과 진짜 게이트웨이의 꼴: 모르는 도구는 isError + 'unknown tool: <이름>', 백엔드 도구의 답은 text 블록 하나(FastMCP 의 들여쓰기 2 JSON),
    결과의 메일은 가린다([가림:메일]). 사람은 Bearer PAT 의 email 로 본다(사람별 위임).
  · 가짜 리스크 앱 — 두 창구(risk_report_ra_material · risk_report_ra_record)의 계약을 그 꼴 그대로(HWAXRisk docs/ra-report-draft.md ·
    app/report_ra.py). 도구 이름 · 인자 · 오류 낱말이 진짜와 같은지는 맨 아래 계약 시험이 형제 리포 소스와 견준다.
  · 가짜 RA(httpx MockTransport — risk_report._TRANSPORT) — `POST /api/reports/ai-draft`(dry_run · 만들기 201) · `PATCH /api/reports/{id}/ai-draft`
    (page = 쪽 수 + 1 이면 붙이고 있는 쪽이면 준 블록만 덮는다). 요청 · 답 꼴은 ReportArchive v0.186.3 reports/routes.py create_ai_draft ·
    _apply_ai_draft · shared/responses.py 에서 읽은 그대로다.
고정하는 것.
  · 차례 — 재료 → 1쪽 dry_run(경고가 있으면 만들지 않는다) → 만들기 → 번호를 먼저 적는다 → 2쪽부터 붙인다 → 다 실렸다고 적는다.
  · 자격 — RA 는 그 사람의 RA 토큰으로만, 게이트웨이는 그 사람의 PAT 로만. 서비스 계정 · 박스 토큰으로 내려가는 길이 없다. RA 연결이 없으면
    리스크 앱도 부르지 않는다(「보내는 중」 을 잡지 않는다).
  · 싣는 것 — template_id · template_version · title · blocks · tags(+ dry_run) 뿐. 게시(publish · boards) · 객체(entity_ids)는 부르지도 싣지도 않는다.
  · 세션 + CSRF 로만(사람이 누른 호출) · plat:risk 와 plat:reportarchive 둘 다.
  · 실패 — 확실한 거절은 풀고, 만드는 호출의 결과를 모르면 「보내는 중」 으로 남기고, 붙이다 멈추면 partial 로 적는다. 리스크 앱 · 게이트웨이의
    거절은 정해진 글로 옮긴다(상대의 글을 그대로 내지 않는다).
"""
import ast
import asyncio
import json
import re
from pathlib import Path

import httpx
import jwt
import pytest
from fastapi.testclient import TestClient

from app.agent import risk_report as M
from app.agent import routes as R
from app.agent import upload as U
from app.auth.cookies import CSRF_COOKIE, SESSION_COOKIE
from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.config import Settings, get_settings
from app.deps import get_current_principal, require_csrf
from app.main import app

KIM = Principal(subject="kim@corp.com", email="kim@corp.com", display_name="김철수", groups=["plat:risk", "plat:reportarchive"])
TARGET = "snap:" + "a" * 32
UID = "rp-0123456789abcdef"
TITLE = f"심의 — [리스크심사 S26U {TARGET}] 종합 보고서 v4 [C2 · 잔여 1]"
TAGS = ["리스크심사", "종합보고서", f"hwax:target:{TARGET}"]
MATERIAL = "heaxhwax_risk_risk_report_ra_material"
RECORD = "heaxhwax_risk_risk_report_ra_record"
_RISK_REPO = Path(__file__).resolve().parents[2].parent / "HWAXRisk" / "backend" / "app"
_EMAIL = re.compile(r"[A-Za-z0-9_.%+-]+@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}")


def _pages(n: int) -> list[dict]:
    return [{"background": [f"# 리스크 심사 보고서 v4 — {i}쪽"], "results": [f"- {i}쪽의 행", "- 담당 hong@corp.com"]}
            for i in range(1, n + 1)]


class _Risk:
    """가짜 리스크 앱 — 두 창구의 계약. 오류는 앱이 MCP 로 눕히는 봉투 {error, message, detail}(HWAXRisk mcp_server._guarded)."""

    STALE_S = 900

    def __init__(self, n_pages: int = 3):
        self.pages = _pages(n_pages)
        self.template = {"id": "deliberation", "version": 1}
        self.ledger: dict = dict.fromkeys(("state", "report_id", "url", "pages_sent", "pages_total", "template", "by", "at", "error"))
        self.editors = {"kim@corp.com"}
        self.refuse: dict[str, tuple[str, str]] = {}     # 도구 → (오류 낱말, 글) — 그 창구가 통째로 거절한다
        self.now, self.delegating, self.audits = 1000, True, 0

    def _ra(self) -> dict | None:
        return None if all(v is None for v in self.ledger.values()) else dict(self.ledger)

    @staticmethod
    def _err(code: str, message: str, **detail) -> dict:
        return {"error": code, "message": message, **({"detail": detail} if detail else {})}

    def _gate(self, tool: str, who: str | None, target_key: str) -> dict | None:
        if not self.delegating or not who:
            return self._err("delegation_required", "게이트웨이 위임으로 확인된 사람만 쓴다.", fix="per_user_sso")
        if target_key != TARGET or who not in self.editors:
            return self._err("E404", f"타깃({target_key}) 을 찾을 수 없습니다.")
        if tool in self.refuse:
            return self._err(*self.refuse[tool])
        return None

    def material(self, who: str | None, *, target_key: str, version: int | None = None) -> dict:
        bad = self._gate("material", who, target_key)
        if bad:
            return bad
        if version is not None and version != 4:
            return self._err("report_version_moved", f"보고서 판이 {version} 에서 4 로 바뀌었다 — 처음 쪽부터 다시 받는다.", version=4)
        out = {"target_key": TARGET, "report_uid": UID, "version": 4}
        led = self.ledger
        if led["state"] == "sent":
            return {**out, "already": True, "ra": self._ra()}
        if led["report_id"] is not None and led["by"] != who:
            return self._err("ra_report_other_author", f"이 판의 RA 초안(#{led['report_id']})은 {led['by']} 이 만들다 멈췄다.", by=led["by"])
        if led["state"] == "sending" and (led["at"] or 0) > self.now - self.STALE_S:
            return self._err("ra_report_in_progress", f"이 판은 지금 RA 로 보내는 중이다({led['by']}).", by=led["by"])
        orphan = led["state"] == "sending" and led["report_id"] is None
        led.update(state="sending", by=who, at=self.now, error=None, pages_total=len(self.pages),
                   template=f"{self.template['id']}@{self.template['version']}")
        got = {**out, "already": False, "title": TITLE, "tags": list(TAGS), "template": dict(self.template),
               "pages": [dict(p) for p in self.pages], "pages_total": len(self.pages), "ra": self._ra()}
        return {**got, "orphan_possible": True} if orphan else got

    def record(self, who: str | None, *, target_key: str, report_uid: str, report_id: int | None = None, url: str | None = None,
               pages_sent: int | None = None, error_reason: str | None = None, error_text: str | None = None,
               outcome_unknown: bool = False) -> dict:
        bad = self._gate("record", who, target_key)
        if bad:
            return bad
        led = self.ledger
        if report_uid != UID:
            return self._err("report_absent", f"이 대상에 그 보고서 판이 없다 — {report_uid}.")
        if led["state"] != "sending" or led["by"] != who:
            if (led["state"] == "sent" and led["by"] == who and not (error_reason or error_text) and report_id in (None, led["report_id"])
                    and pages_sent in (None, led["pages_sent"])):
                return {"target_key": TARGET, "report_uid": UID, "version": 4, "created": False, "ra": self._ra()}   # 같은 사실을 다시
            return self._err("ra_report_not_claimed", "이 판의 재료를 받아 간(보내는 중인) 사람만 결과를 적는다.", by=led["by"])
        if led["report_id"] is not None and report_id not in (None, led["report_id"]):
            return self._err("ra_report_id_conflict", f"이 판에는 이미 RA 초안 #{led['report_id']} 가 적혀 있다.")
        known = led["report_id"] if led["report_id"] is not None else report_id
        had = led["pages_sent"] or 0
        sent = had if pages_sent is None else pages_sent
        if sent < had or sent > led["pages_total"] or (sent and known is None):
            return self._err("E100", f"pages_sent 는 {had} 이상 {led['pages_total']} 이하다 — {sent}.")
        created = led["report_id"] is None and known is not None
        led["report_id"] = known
        if known is not None:
            led["pages_sent"] = sent
            self.audits += int(sent > had)
        hit = re.fullmatch(r"/w/[^/\s]+/reports/(\d+)", url) if isinstance(url, str) else None
        if hit and known is not None and int(hit.group(1)) == known:
            led["url"] = url
        if error_reason or error_text:
            led["error"] = f"{error_reason or 'failed'}: {error_text or ''}"[:300]
            if known is not None:
                led["state"] = "partial"
            elif not outcome_unknown:
                led["state"] = None
        else:
            led.update(state="sent" if known is not None and sent == led["pages_total"] else "sending", error=None, at=self.now)
        return {"target_key": TARGET, "report_uid": UID, "version": 4, "created": created, "ra": self._ra()}


def _sse(msg: dict) -> str:
    return f"event: message\ndata: {json.dumps(msg, ensure_ascii=False)}\n\n"


class _Gateway:
    """가짜 게이트웨이 — 리스크 앱이 문을 켰으면(on) 두 도구가 목록에 있고, 껐으면 'unknown tool:' 이다. down 에 든 도구는 불통이다."""

    def __init__(self, risk: _Risk):
        self.risk, self.on = risk, True
        self.calls: list[tuple[str, dict]] = []
        self.tokens: list[str] = []
        self.open = 0
        self.down: set[str] = set()
        self.forbid: set[str] = set()

    async def __call__(self, req: httpx.Request) -> httpx.Response:
        assert req.url.path == "/mcp"
        self.tokens.append(req.headers.get("authorization", ""))
        if req.method == "DELETE":
            self.open -= 1
            return httpx.Response(200)
        msg = json.loads(req.content)
        if msg["method"] == "initialize":
            self.open += 1
            return httpx.Response(200, headers={"mcp-session-id": f"s{len(self.tokens)}", "content-type": "text/event-stream"},
                                  text=_sse({"jsonrpc": "2.0", "id": msg["id"], "result": {"protocolVersion": "2024-11-05",
                                                                                           "capabilities": {}, "serverInfo": {}}}))
        if msg["method"] == "notifications/initialized":
            return httpx.Response(202)
        assert msg["method"] == "tools/call"
        name, args = msg["params"]["name"], msg["params"]["arguments"]
        self.calls.append((name, args))
        if name in self.down:
            raise httpx.ConnectError("gateway down", request=req)
        who = jwt.decode(self.tokens[-1].removeprefix("Bearer "), options={"verify_signature": False}).get("email")

        def answer(text: str, *, is_error: bool = False) -> httpx.Response:
            return httpx.Response(200, headers={"content-type": "text/event-stream"}, text=_sse({
                "jsonrpc": "2.0", "id": msg["id"], "result": {"content": [{"type": "text", "text": text}], "isError": is_error}}))

        if name in self.forbid:
            return answer(f"forbidden: {name} 은 plat:risk 권한이 있어야 한다", is_error=True)
        if not self.on or name not in (MATERIAL, RECORD):
            return answer(f"unknown tool: {name}", is_error=True)
        out = self.risk.material(who, **args) if name == MATERIAL else self.risk.record(who, **args)
        return answer(_EMAIL.sub("[가림:메일]", json.dumps(out, ensure_ascii=False, indent=2)))

    def names(self) -> list[str]:
        return [n.removeprefix("heaxhwax_risk_risk_report_ra_") for n, _a in self.calls]


class _RA:
    """가짜 RA — 초안은 작성자 개인 공간(/w/personal-5/reports/<번호>)에 선다. fail[단계] = HTTP 상태 · boom[단계] = 전송 예외 ·
    lose 에 든 단계는 반영한 뒤 답을 잃는다(시간 초과). 단계 — preview(dry_run) · create · page<n>(n쪽 PATCH)."""

    BLOCKS = ("background", "results", "recommendation", "minutes")

    def __init__(self):
        self.calls: list[httpx.Request] = []
        self.reports: dict[int, dict] = {}
        self.next_id = 58
        self.templates = {("deliberation", 1)}
        self.fail: dict[str, int] = {}
        self.boom: dict[str, type] = {}
        self.lose: set[str] = set()
        self.unauthorized = 0                       # 앞의 몇 요청을 401 로(위임 토큰 다시 받기)
        self.hold: asyncio.Event | None = None      # 붙이기를 붙잡는다(요청이 끊겨도 끝까지 가는지)

    def _page(self, blocks: dict) -> tuple[dict, list[str]]:
        warnings = [f"템플릿에 없는 block_id '{b}' — 건너뜀" for b in blocks if b not in self.BLOCKS]
        return {b: v for b, v in blocks.items() if b in self.BLOCKS}, warnings

    async def __call__(self, req: httpx.Request) -> httpx.Response:
        self.calls.append(req)
        if self.unauthorized:
            self.unauthorized -= 1
            return httpx.Response(401, json={"detail": "Invalid or expired token"})
        body = json.loads(req.content)
        path = req.url.path
        hit = re.fullmatch(r"/api/reports/(\d+)/ai-draft", path)
        if path == "/api/reports/ai-draft" and req.method == "POST":
            step = "preview" if body.get("dry_run") else "create"
        elif hit and req.method == "PATCH":
            step = f"page{body['page']}"
        else:
            raise AssertionError(f"가짜 RA 가 모르는 요청 — {req.method} {path}")
        if step in self.boom:
            raise self.boom[step]("가짜 RA 불통", request=req)
        if step in self.fail:
            return httpx.Response(self.fail[step], json={"success": False, "message": f"{step} {self.fail[step]}"})
        if step in ("preview", "create"):
            if (body["template_id"], body["template_version"]) not in self.templates:
                return httpx.Response(404, json={"success": False, "message": "Template not found or not visible to this account: "
                                                                             f"{body['template_id']}@{body['template_version']}"})
            content, warnings = self._page(body.get("blocks") or {})
            if step == "preview":
                return httpx.Response(200, json={"success": True, "data": {
                    "dry_run": True, "title": body["title"], "page_count": 1, "pages": [{"page": 1, "blocks": sorted(content)}],
                    "warnings": warnings, "note": "만들지 않았습니다. 그대로 생성하려면 dry_run 없이 다시 호출하세요."}})
            rid, self.next_id = self.next_id, self.next_id + 1
            self.reports[rid] = {"title": body["title"], "tags": body.get("tags") or [], "pages": [content],
                                 "template": (body["template_id"], body["template_version"]), "auth": req.headers["authorization"]}
            if step in self.lose:
                raise httpx.ReadTimeout("가짜 RA 가 답을 잃었다", request=req)
            return httpx.Response(201, json={"success": True, "message": "Created successfully", "data": {
                "report_id": rid, "title": body["title"], "page_count": 1, "phase": "drafting", "warnings": warnings,
                "url": f"/w/personal-5/reports/{rid}"}})
        rid = int(hit.group(1))
        report = self.reports.get(rid)
        if report is None:
            return httpx.Response(404, json={"success": False, "message": f"Report not found: {rid}"})
        if self.hold is not None:
            await self.hold.wait()
        n = body["page"]
        if n - 1 > len(report["pages"]):
            return httpx.Response(400, json={"success": False, "message": f"page {n}: 이 보고서엔 {len(report['pages'])}쪽뿐입니다 "
                                                                         f"(이어서 추가하려면 page={len(report['pages']) + 1})."})
        content, warnings = self._page(body.get("blocks") or {})
        if n - 1 == len(report["pages"]):
            report["pages"].append(content)
        else:
            report["pages"][n - 1].update(content)
        if step in self.lose:
            raise httpx.ReadTimeout("가짜 RA 가 답을 잃었다", request=req)
        return httpx.Response(200, json={"success": True, "data": {
            "report": {"id": rid, "pages": [{"template_id": "deliberation", "template_version": 1, "content": p} for p in report["pages"]]},
            "warnings": warnings, "url": f"/w/personal-5/reports/{rid}", "mounted_to": []}})

    def steps(self) -> list[str]:
        out = []
        for r in self.calls:
            body = json.loads(r.content)
            out.append(("preview" if body.get("dry_run") else "create") if r.method == "POST" else f"page{body['page']}")
        return out


def _settings(**kw) -> Settings:
    kw.setdefault("ra_base_url", "http://ra.test")
    kw.setdefault("ra_sso_secret", "")
    kw.setdefault("mcp_gateway_url", "http://gw.test")
    return Settings(_env_file=None, **kw)


class _Audit:
    def __init__(self):
        self.rows = []

    def record(self, **kw):
        self.rows.append(kw)


class _Box:
    def __init__(self, c, risk, gw, ra, s, tok):
        self.c, self.risk, self.gw, self.ra, self.s, self.tok = c, risk, gw, ra, s, tok

    def post(self, body: dict | None = None, **kw) -> httpx.Response:
        return self.c.post("/agent/risk-report/ra-draft", json={"target_key": TARGET} if body is None else body, **kw)


@pytest.fixture()
def box(monkeypatch):
    """진짜 포털 앱 — 설정 · 감사 · RA 토큰 함수 · 두 전송(게이트웨이 · RA)을 바꿔 끼운다. 사람은 기본 KIM(세션 + CSRF 를 지난 것으로 둔다)."""
    s = _settings()
    risk = _Risk()
    gw, ra = _Gateway(risk), _RA()
    tok = {"value": ("rat_kim", False, {"workspace": ""})}

    async def fake_token(request, settings, principal):
        if isinstance(tok["value"], Exception):
            raise tok["value"]
        return tok["value"]

    monkeypatch.setattr(R, "_ra_user_token", fake_token)
    monkeypatch.setattr(M, "_TRANSPORT", httpx.MockTransport(ra))
    monkeypatch.setattr(U, "_TRANSPORT", httpx.MockTransport(gw))
    app.dependency_overrides[get_settings] = lambda: s
    app.dependency_overrides[get_current_principal] = lambda: KIM
    app.dependency_overrides[require_csrf] = lambda: None
    try:
        with TestClient(app, raise_server_exceptions=False) as c:
            keep = app.state.agent_audit
            app.state.agent_audit = _Audit()
            try:
                yield _Box(c, risk, gw, ra, s, tok)
            finally:
                app.state.agent_audit = keep
    finally:
        for dep in (get_settings, get_current_principal, require_csrf):
            app.dependency_overrides.pop(dep, None)


# ── 고른 길 ─────────────────────────────────────────────────────────────────────────────────────────────────────
def test_재료를_받아_그_사람_명의로_초안을_만들고_쪽을_붙이고_원장에_적는다(box):
    r = box.post()
    assert r.status_code == 200, r.text
    assert r.json() == {"ok": True, "target_key": TARGET, "report_uid": UID, "version": 4, "state": "sent", "already": False,
                        "created": True, "report_id": 58, "url": "/w/personal-5/reports/58", "pages_sent": 3, "pages_total": 3,
                        "warnings": [], "orphan_possible": False}
    assert box.ra.steps() == ["preview", "create", "page2", "page3"], "1쪽 dry_run → 만들기 → 2쪽부터 차례로"
    draft = {"template_id": "deliberation", "template_version": 1, "title": TITLE, "blocks": box.risk.pages[0], "tags": TAGS}
    sent = [json.loads(q.content) for q in box.ra.calls]
    masked = json.loads(_EMAIL.sub("[가림:메일]", json.dumps(draft, ensure_ascii=False)))     # 게이트웨이를 지난 재료 — 메일이 가려져 온다
    assert sent[0] == {**masked, "dry_run": True} and sent[1] == masked, "제목 · 태그 · 템플릿은 재료 그대로"
    assert [q.url.path for q in box.ra.calls[2:]] == ["/api/reports/58/ai-draft"] * 2
    assert sent[2] == {"page": 2, "blocks": {"background": ["# 리스크 심사 보고서 v4 — 2쪽"], "results": ["- 2쪽의 행", "- 담당 [가림:메일]"]}}
    assert all(q.headers["authorization"] == "Bearer rat_kim" for q in box.ra.calls), "모든 RA 호출은 그 사람의 RA 토큰으로"
    assert box.ra.reports[58]["title"] == TITLE and box.ra.reports[58]["tags"] == TAGS and len(box.ra.reports[58]["pages"]) == 3
    # 리스크 앱 — 재료 한 번, 번호를 먼저 적고(1쪽), 쪽마다 진행을, 끝에 다 실렸다고 적는다
    assert box.gw.names() == ["material", "record", "record", "record"]
    assert box.gw.calls[0][1] == {"target_key": TARGET}
    assert [a for _n, a in box.gw.calls[1:]] == [
        {"target_key": TARGET, "report_uid": UID, "report_id": 58, "url": "/w/personal-5/reports/58", "pages_sent": 1},
        {"target_key": TARGET, "report_uid": UID, "pages_sent": 2}, {"target_key": TARGET, "report_uid": UID, "pages_sent": 3}]
    assert box.risk.ledger["state"] == "sent" and box.risk.ledger["report_id"] == 58 and box.risk.ledger["by"] == "kim@corp.com"
    assert box.gw.open == 0, "게이트웨이 세션을 닫는다"
    # 게이트웨이에는 그 사람의 PAT 로만 — 서비스 토큰이 없다
    claims = [jwt.decode(t.removeprefix("Bearer "), options={"verify_signature": False}) for t in set(box.gw.tokens)]
    assert [(c["email"], c["scopes"], c["aud"]) for c in claims] == [("kim@corp.com", ["chat"], [box.s.pat_chat_audience])]
    (row,) = app.state.agent_audit.rows
    assert row["event"] == "risk_report_ra_draft" and row["status"] == "ok" and row["principal"] == "kim@corp.com"
    assert row["meta"] == {"target_key": TARGET, "report_uid": UID, "version": 4, "report_id": 58, "pages_sent": 3, "pages_total": 3,
                           "created": True}
    assert "리스크 심사 보고서" not in json.dumps(row, ensure_ascii=False), "감사에는 보고서 글을 남기지 않는다"


def test_RA_에는_초안_만들기와_쪽_붙이기만_부르고_게시_객체_칸은_싣지_않는다(box):
    assert box.post().status_code == 200
    allowed = {"template_id", "template_version", "title", "blocks", "tags", "dry_run", "page"}
    for q in box.ra.calls:
        assert (q.method, bool(re.fullmatch(r"/api/reports(/\d+)?/ai-draft", q.url.path))) in (("POST", True), ("PATCH", True))
        assert set(json.loads(q.content)) <= allowed
    # 소스(주석 · 설명 글 포함)에도 그 낱말이 없다 — 게시 · 게시판 · 객체 태그 · 폴더 · 유형 · 추가 블록, 서비스 자격 이름
    src = Path(M.__file__).read_text(encoding="utf-8")
    for word in ("publish", "boards", "entity_ids", "folder_ids", "report_type_id", "mount", "extra_blocks", "gw_token", "GW_TOKEN",
                 "service_token", "admin"):
        assert word not in src, word


def test_한_쪽짜리_판은_만들고_곧바로_다_실렸다고_적는다(box):
    box.risk.pages = _pages(1)
    out = box.post().json()
    assert (out["ok"], out["state"], out["pages_sent"], out["pages_total"]) == (True, "sent", 1, 1)
    assert box.ra.steps() == ["preview", "create"] and box.gw.names() == ["material", "record"]
    assert box.gw.calls[1][1] == {"target_key": TARGET, "report_uid": UID, "report_id": 58, "url": "/w/personal-5/reports/58",
                                  "pages_sent": 1}


def test_이미_다_실린_판은_RA_를_부르지_않고_그_초안을_돌려준다(box):
    assert box.post().json()["created"] is True
    n_ra, n_gw = len(box.ra.calls), len(box.gw.calls)
    r = box.post()
    assert r.status_code == 200
    assert r.json() == {"ok": True, "target_key": TARGET, "report_uid": UID, "version": 4, "state": "sent", "already": True,
                        "created": False, "report_id": 58, "url": "/w/personal-5/reports/58", "pages_sent": 3, "pages_total": 3,
                        "warnings": [], "orphan_possible": False}
    assert len(box.ra.calls) == n_ra and box.gw.names()[n_gw:] == ["material"], "한 판에 초안 하나 — 다시 만들지도 적지도 않는다"
    assert len(box.ra.reports) == 1


def test_판을_주면_그대로_넘기고_판이_바뀌었으면_409(box):
    r = box.post({"target_key": TARGET, "version": 3})
    assert r.status_code == 409 and r.json()["error"] == "report_version_moved" and box.ra.calls == []
    assert box.gw.calls == [(MATERIAL, {"target_key": TARGET, "version": 3})]
    assert box.post({"target_key": TARGET, "version": 4}).json()["ok"] is True
    for bad in ({}, {"target_key": ""}, {"target_key": TARGET, "version": 0}, {"target_key": "x" * 201}):
        assert box.post(bad).status_code == 422


# ── 끊김 — 이어 보내기 · 결과를 모를 때 ─────────────────────────────────────────────────────────────────────────
def test_붙이다_멈추면_실린_데까지_적고_다시_누르면_그_다음_쪽부터_잇는다(box):
    box.risk.pages = _pages(4)
    box.ra.fail["page3"] = 502
    r = box.post()
    assert r.status_code == 502
    out = r.json()
    assert (out["ok"], out["error"], out["report_id"], out["pages_sent"], out["pages_total"], out["created"]) == (
        False, "ra_error", 58, 2, 4, True)
    assert out["url"] == "/w/personal-5/reports/58" and "다시" in out["detail"]
    assert box.ra.steps() == ["preview", "create", "page2", "page3"]
    assert (box.risk.ledger["state"], box.risk.ledger["pages_sent"], box.risk.ledger["error"]) == (
        "partial", 2, "transient: HTTP 502 page3 502")
    assert box.gw.calls[-1][1] == {"target_key": TARGET, "report_uid": UID, "pages_sent": 2, "error_reason": "transient",
                                   "error_text": "HTTP 502 page3 502"}
    (row,) = app.state.agent_audit.rows
    assert row["status"] == "failed" and row["meta"]["error"] == "ra_error" and row["meta"]["report_id"] == 58

    box.ra.fail.clear()
    n = len(box.ra.calls)
    again = box.post().json()
    assert (again["ok"], again["state"], again["created"], again["report_id"], again["pages_sent"]) == (True, "sent", False, 58, 4)
    assert box.ra.steps()[n:] == ["page3", "page4"], "초안을 다시 만들지 않는다 — 원장의 다음 쪽부터"
    assert len(box.ra.reports) == 1 and len(box.ra.reports[58]["pages"]) == 4 and box.risk.ledger["state"] == "sent"


def test_붙이기가_불통이어도_partial_이고_편집_잠금은_409(box):
    box.ra.boom["page2"] = httpx.ConnectError
    r = box.post()
    assert r.status_code == 502 and r.json()["error"] == "ra_unreachable" and r.json()["pages_sent"] == 1
    assert (box.risk.ledger["state"], box.risk.ledger["error"]) == ("partial", "transient: ConnectError")
    box.ra.boom.clear()
    box.ra.fail["page2"] = 409
    r = box.post()
    assert r.status_code == 409 and r.json()["error"] == "report_locked" and "편집 화면" in r.json()["detail"]
    assert box.risk.ledger["error"] == "locked: HTTP 409 page2 409"
    # RA 에서 그 초안이 사라졌다(사람이 지웠다) — 그 판은 이어 보내지 못한다
    box.ra.fail.clear()
    box.ra.reports.clear()
    r = box.post()
    assert r.status_code == 409 and r.json()["error"] == "ra_draft_gone" and box.risk.ledger["state"] == "partial"


def test_RA_의_답이_아닌_2xx_3xx_는_성공으로_치지_않는다(box, monkeypatch):
    """중간 장비가 로그인 쪽을 200 으로 주거나 주소가 넘겨질(302) 때 — 「경고 없음」 · 「쪽이 실렸다」 로 읽으면 실패가 성공과 같은 꼴이 된다."""
    real = _RA.__call__
    mode = {"step": "preview", "resp": lambda: httpx.Response(200, text="<html>login</html>")}

    async def odd(self, req):
        body = json.loads(req.content)
        step = ("preview" if body.get("dry_run") else "create") if req.method == "POST" else f"page{body['page']}"
        if step == mode["step"]:
            self.calls.append(req)
            return mode["resp"]()
        return await real(self, req)

    monkeypatch.setattr(_RA, "__call__", odd)
    r = box.post()
    assert r.status_code == 502 and r.json()["error"] == "ra_error"
    assert box.ra.steps() == ["preview"] and box.ra.reports == {} and box.risk.ledger["state"] is None, "미리보기를 못 읽었으면 만들지 않는다"
    mode["resp"] = lambda: httpx.Response(302, headers={"location": "https://ra.test/login"})
    assert box.post().json()["error"] == "ra_error" and box.ra.reports == {}
    for resp in (lambda: httpx.Response(200, text="<html>login</html>"), lambda: httpx.Response(302, headers={"location": "/login"}),
                 lambda: httpx.Response(200, json={"success": True, "data": {"report": {"id": 58, "pages": [{}]}, "warnings": []}})):
        mode.update(step="page2", resp=resp)
        out = box.post().json()
        assert (out["ok"], out["error"], out["pages_sent"], out["report_id"]) == (False, "ra_error", 1, 58)
        assert (box.risk.ledger["state"], box.risk.ledger["pages_sent"]) == ("partial", 1), "실리지 않은 쪽을 실렸다고 적지 않는다"
    mode["step"] = "none"
    assert box.post().json()["state"] == "sent" and len(box.ra.reports[58]["pages"]) == 3


def test_쪽을_붙인_답을_잃어도_같은_쪽을_다시_보내_쪽이_겹치지_않는다(box):
    box.ra.lose.add("page2")
    assert box.post().json()["error"] == "ra_unreachable"
    assert len(box.ra.reports[58]["pages"]) == 2 and box.risk.ledger["pages_sent"] == 1, "RA 에는 실렸는데 원장은 모른다"
    box.ra.lose.clear()
    assert box.post().json()["state"] == "sent"
    assert [p["background"][0][-2:] for p in box.ra.reports[58]["pages"]] == ["1쪽", "2쪽", "3쪽"], "2쪽을 다시 보내도 덮을 뿐이다"


def test_미리보기에_경고가_있으면_만들지_않고_잡은_것을_푼다(box):
    box.risk.pages[0]["appendix"] = ["템플릿에 없는 블록"]
    r = box.post()
    assert r.status_code == 409
    out = r.json()
    assert (out["ok"], out["error"]) == (False, "ra_template_mismatch") and "HWAXRISK_RA_REPORT_TEMPLATE" in out["detail"]
    assert out["warnings"] == ["템플릿에 없는 block_id 'appendix' — 건너뜀"] and out["template"] == "deliberation@1"
    assert box.ra.steps() == ["preview"] and box.ra.reports == {}, "RA 는 형식이 틀린 블록을 경고만 내고 버린다 — 만들지 않는다"
    assert box.gw.calls[-1][1] == {"target_key": TARGET, "report_uid": UID, "error_reason": "template_mismatch",
                                   "error_text": "템플릿에 없는 block_id 'appendix' — 건너뜀"}
    assert box.risk.ledger["state"] is None, "보낸 적 없는 상태 — 곧바로 다시 누를 수 있다"


def test_템플릿이_없거나_RA_가_거절하면_만들지_않고_푼다(box):
    box.risk.template = {"id": "sys.hwax.deliberation", "version": 2}
    r = box.post()
    assert r.status_code == 409 and r.json()["error"] == "ra_template_not_found" and r.json()["template"] == "sys.hwax.deliberation@2"
    assert box.ra.steps() == ["preview"] and box.risk.ledger["state"] is None
    assert box.risk.ledger["error"].startswith("rejected: HTTP 404 Template not found")
    box.risk.template = {"id": "deliberation", "version": 1}
    for status, error, http in ((403, "ra_forbidden", 403), (400, "ra_rejected", 422), (401, "ra_token_rejected", 502)):
        box.ra.calls.clear()
        box.ra.fail["create"] = status
        r = box.post()
        assert (r.status_code, r.json()["error"]) == (http, error), status
        assert box.ra.steps() == ["preview", "create"] and box.ra.reports == {} and box.risk.ledger["state"] is None, status
    # 미리보기가 불통이어도 만들어진 것이 없다 — 푼다
    box.ra.fail.clear()
    box.ra.boom["preview"] = httpx.ConnectTimeout
    r = box.post()
    assert r.status_code == 502 and r.json()["error"] == "ra_unreachable" and box.risk.ledger["state"] is None


def test_템플릿은_리스크_앱의_박스_설정을_그대로_쓴다(box):
    """템플릿 id · 판의 정본은 리스크 앱의 박스 설정 한 곳이다(재료에 실려 온다) — 포털은 고르지 않는다."""
    box.risk.template = {"id": "sys.hwax.deliberation", "version": 2}
    box.ra.templates.add(("sys.hwax.deliberation", 2))
    assert box.post().json()["ok"] is True
    assert box.ra.reports[58]["template"] == ("sys.hwax.deliberation", 2)
    assert [(b["template_id"], b["template_version"]) for b in map(json.loads, (q.content for q in box.ra.calls[:2]))] == [
        ("sys.hwax.deliberation", 2)] * 2


def test_만드는_호출의_결과를_모르면_보내는_중으로_남기고_곧바로_다시_만들지_않는다(box):
    """RA 가 초안을 만들고 답을 잃었다(시간 초과) — 곧바로 다시 만들면 초안이 둘이 된다. 원장은 「보내는 중」 으로 남고(앱이 15분 뒤에 다시
    잡게 한다) 둘째 누름은 409 다. 낡은 뒤 다시 잡으면 앞 시도의 초안이 남았을 수 있다고 알린다(orphan_possible)."""
    box.ra.lose.add("create")
    r = box.post()
    assert r.status_code == 502 and r.json()["error"] == "ra_outcome_unknown" and "내 공간" in r.json()["detail"]
    assert len(box.ra.reports) == 1 and box.ra.steps() == ["preview", "create"]
    assert box.gw.calls[-1][1] == {"target_key": TARGET, "report_uid": UID, "error_reason": "transient", "error_text": "ReadTimeout",
                                   "outcome_unknown": True}
    assert (box.risk.ledger["state"], box.risk.ledger["report_id"]) == ("sending", None)
    box.ra.lose.clear()
    r = box.post()
    assert r.status_code == 409 and r.json()["error"] == "ra_report_in_progress" and len(box.ra.reports) == 1
    box.risk.now += _Risk.STALE_S + 1
    out = box.post().json()
    assert (out["ok"], out["orphan_possible"], out["report_id"]) == (True, True, 59) and len(box.ra.reports) == 2
    # 5xx 도 결과를 모르는 쪽이다
    box.risk.ledger.update(dict.fromkeys(box.risk.ledger))
    box.ra.fail["create"] = 502
    assert box.post().json()["error"] == "ra_outcome_unknown" and box.risk.ledger["state"] == "sending"


def test_만든_초안의_번호를_읽지_못해도_결과를_모르는_쪽이다(box, monkeypatch):
    real = _RA.__call__

    async def no_id(self, req):
        resp = await real(self, req)
        if req.method == "POST" and not json.loads(req.content).get("dry_run"):
            return httpx.Response(201, json={"success": True, "data": {"title": "x", "url": "/w/personal-5/reports/58"}})
        return resp

    monkeypatch.setattr(_RA, "__call__", no_id)
    r = box.post()
    assert r.status_code == 502 and r.json()["error"] == "ra_outcome_unknown"
    assert box.risk.ledger["state"] == "sending" and box.gw.calls[-1][1]["outcome_unknown"] is True


def test_RA_가_준_주소는_꼴이_맞고_그_번호일_때만_싣는다(box, monkeypatch):
    real = _RA.__call__

    async def odd_url(self, req):
        resp = await real(self, req)
        if req.method == "POST" and not json.loads(req.content).get("dry_run"):
            data = resp.json()["data"]
            return httpx.Response(201, json={"success": True, "data": {**data, "url": "https://evil.example/w/x/reports/58"}})
        return resp

    monkeypatch.setattr(_RA, "__call__", odd_url)
    out = box.post().json()
    assert (out["ok"], out["report_id"], out["url"]) == (True, 58, None), "꼴이 다른 글을 링크로 내지 않는다"
    assert box.gw.calls[1][1] == {"target_key": TARGET, "report_uid": UID, "report_id": 58, "pages_sent": 1}
    assert box.risk.ledger["url"] is None


def test_초안은_만들었는데_원장에_적지_못하면_번호를_돌려주고_멈춘다(box):
    box.gw.down.add(RECORD)
    r = box.post()
    assert r.status_code == 502
    out = r.json()
    assert (out["ok"], out["error"], out["report_id"], out["url"]) == (False, "ledger_unrecorded", 58, "/w/personal-5/reports/58")
    assert "58" in out["detail"]
    assert box.ra.steps() == ["preview", "create"], "번호를 적지 못했으면 더 붙이지 않는다"
    (row,) = app.state.agent_audit.rows
    assert row["status"] == "failed" and row["meta"]["report_id"] == 58


def test_진행을_적지_못해도_보내기는_잇고_끝에_다시_적는다(box):
    real = box.risk.record
    seen = {"n": 0}

    def flaky(who, **args):
        seen["n"] += 1
        if seen["n"] == 2:                                        # 2쪽의 진행 적기만 실패한다
            return _Risk._err("internal_error", "내부 오류 — 서버 로그를 확인하세요.")
        return real(who, **args)

    box.risk.record = flaky
    out = box.post().json()
    assert (out["ok"], out["state"], out["pages_sent"]) == (True, "sent", 3) and box.ra.steps() == ["preview", "create", "page2", "page3"]


def test_RA_가_쪽을_붙이며_낸_경고는_답에_싣는다(box):
    box.risk.pages[1]["appendix"] = ["2쪽에만 있는 모르는 블록"]
    out = box.post().json()
    assert out["ok"] is True and out["warnings"] == ["2쪽: 템플릿에 없는 block_id 'appendix' — 건너뜀"]


def test_위임_토큰이_거절되면_한_번_다시_받아_잇는다(box, monkeypatch):
    from app.auth import ra_sso

    box.tok["value"] = ("rat_old", True, {"workspace": "stale-dept"})
    forgot = []

    async def fresh(settings, *, email, name):
        return "rat_fresh"

    monkeypatch.setattr(ra_sso, "forget", lambda email: forgot.append(email))
    monkeypatch.setattr(ra_sso, "ra_user_token", fresh)
    box.ra.unauthorized = 1
    assert box.post().json()["ok"] is True
    assert forgot == ["kim@corp.com"]
    assert [q.headers["authorization"] for q in box.ra.calls[:2]] == ["Bearer rat_old", "Bearer rat_fresh"]
    assert all("x-workspace-slug" not in q.headers for q in box.ra.calls), "위임 토큰이면 부서 머리를 싣지 않는다(_ra_workspace)"


# ── 자격 — 서비스 계정으로 내려가는 길이 없다 ───────────────────────────────────────────────────────────────────
def test_RA_연결이_없으면_만들지_않고_리스크_앱도_부르지_않는다(box):
    box.tok["value"] = AuthError("Report Archive 연결이 없습니다 — 포털 '개인 토큰 › 외부 연결'(/tokens?tab=connect)에서 RA 토큰을 먼저 "
                                 "등록하세요.", status_code=400)
    r = box.post()
    assert r.status_code == 400
    assert r.json()["ok"] is False and r.json()["error"] == "no_ra_connection" and "외부 연결" in r.json()["detail"]
    assert box.gw.calls == [] and box.ra.calls == [], "「보내는 중」 을 잡지 않는다 · 다른 자격으로 내려가지 않는다"
    assert box.risk.ledger["state"] is None


def test_사람_PAT_를_만들지_못하면_아무것도_부르지_않는다(box, monkeypatch):
    monkeypatch.setattr(R, "_chat_user_pat", lambda *a, **k: None)
    r = box.post()
    assert r.status_code == 502 and r.json()["error"] == "no_person_token"
    assert box.gw.calls == [] and box.ra.calls == []


def test_권한_둘이_다_있어야_한다(box):
    for groups in (["plat:risk"], ["plat:reportarchive"], []):
        app.dependency_overrides[get_current_principal] = lambda g=groups: KIM.model_copy(update={"groups": g})
        assert box.post().status_code == 403, groups
    assert box.gw.calls == [] and box.ra.calls == []


def test_세션과_CSRF_로만_받는다(box):
    """사람이 화면에서 누른 호출만 — PAT(개인 Claude · 스크립트)로는 부르지 못한다."""
    app.dependency_overrides.pop(get_current_principal, None)
    app.dependency_overrides.pop(require_csrf, None)
    keep = getattr(app.state, "access", None)
    app.state.access = None
    try:
        assert box.post().status_code == 401
        chat = R._chat_user_pat(app.state.keystore, box.s, KIM)
        assert box.post(headers={"Authorization": f"Bearer {chat}"}).status_code == 401, "PAT 는 받지 않는다"
        from app.auth.jwt_service import SESSION_AUDIENCE
        sess = app.state.jwt_service._encode({"sub": "kim@corp.com", "aud": SESSION_AUDIENCE, "email": "kim@corp.com", "name": "김철수",
                                              "groups": list(KIM.groups)}, ttl=600, typ="session")
        box.c.cookies.set(SESSION_COOKIE, sess)
        box.c.cookies.set(CSRF_COOKIE, "t")
        assert box.post().status_code == 403, "세션 쿠키만으로는 못 쓴다(CSRF)"
        assert box.gw.calls == [] and box.ra.calls == []
        assert box.post(headers={"X-CSRF-Token": "t"}).json()["ok"] is True
    finally:
        box.c.cookies.clear()
        app.state.access = keep


# ── 리스크 앱 · 게이트웨이의 거절 — 정해진 글로 ──────────────────────────────────────────────────────────────────
def test_리스크_앱의_문이_꺼져_있으면_꺼져_있다고_답한다(box):
    """문이 꺼진 박스(기본값)는 두 도구를 등록하지 않는다 — 게이트웨이가 'unknown tool:' 로 답한다. 포털에 둘째 스위치는 없다."""
    box.gw.on = False
    r = box.post()
    assert r.status_code == 409
    assert r.json()["error"] == "risk_ra_draft_off" and "꺼져" in r.json()["detail"] and "HWAXRISK_RA_REPORT_DRAFT" in r.json()["detail"]
    assert box.ra.calls == []
    box.gw.on = True
    box.risk.refuse["material"] = ("ra_report_off", "종합 보고서를 RA 초안으로 보내는 문이 이 박스에서 꺼져 있다(기본값).")
    assert box.post().json()["error"] == "risk_ra_draft_off"


@pytest.mark.parametrize("code,status,error", [
    ("role_insufficient", 403, "not_editor"), ("E404", 404, "target_not_found"), ("report_absent", 404, "report_absent"),
    ("project_purged", 409, "project_purged"), ("ra_report_withheld", 409, "ra_report_withheld"),
    ("ra_report_empty", 409, "ra_report_empty"), ("ra_report_in_progress", 409, "ra_report_in_progress"),
    ("ra_report_other_author", 409, "ra_report_other_author"), ("delegation_required", 502, "risk_not_delegated"),
    ("internal_error", 502, "risk_refused"), ("brand_new_code", 502, "risk_refused"),
    ("<script>alert(1)</script>", 502, "risk_refused"), ("낱말이 아닌 긴 글 " * 5, 502, "risk_refused")])
def test_리스크_앱의_거절은_정해진_글로_옮긴다(box, code, status, error):
    secret = "상대가 지은 글 hong@corp.com <script>"
    box.risk.refuse["material"] = (code, secret)
    r = box.post()
    assert (r.status_code, r.json()["error"], r.json()["ok"]) == (status, error, False)
    assert "상대가 지은 글" not in r.text and "script" not in r.text and "낱말이 아닌" not in r.text, "상대의 글을 그대로 내지 않는다"
    shown = code if re.fullmatch(r"[A-Za-z0-9_]{1,40}", code) else "unknown"      # 낱말 꼴이 아닌 오류 칸은 싣지 않는다
    assert r.json()["detail"] == M.REFUSALS[error][1].format(code=shown)
    assert box.ra.calls == [] and box.gw.names() == ["material"]
    (row,) = app.state.agent_audit.rows
    assert row["status"] == "failed" and row["meta"] == {"target_key": TARGET, "error": error}


def test_위임이_안_된_게이트웨이면_누구인지_확인하지_못했다고_답한다(box):
    box.risk.delegating = False
    r = box.post()
    assert r.status_code == 502 and r.json()["error"] == "risk_not_delegated" and "위임" in r.json()["detail"]
    assert box.ra.calls == []


def test_게이트웨이의_권한_거절과_불통(box):
    box.gw.forbid.add(MATERIAL)
    r = box.post()
    assert r.status_code == 403 and r.json()["error"] == "risk_forbidden" and box.ra.calls == []
    box.gw.forbid.clear()
    box.gw.down.add(MATERIAL)
    r = box.post()
    assert r.status_code == 502 and r.json()["error"] == "gateway_unreachable" and box.ra.calls == []


def test_재료의_꼴이_틀리면_RA_를_부르지_않고_푼다(box):
    real = box.risk.material
    for spoil in ({"pages": "글"}, {"pages": []}, {"pages": [{"background": "글 하나"}]}, {"title": ""}, {"title": "가" * 256},
                  {"template": {"id": "deliberation"}}, {"pages_total": 9}, {"tags": "태그"}):
        box.risk.ledger.update(dict.fromkeys(box.risk.ledger))
        box.risk.material = lambda who, _s=spoil, **args: {**real(who, **args), **_s}
        r = box.post()
        assert r.status_code == 502 and r.json()["error"] == "risk_bad_material", spoil
        assert box.ra.calls == [] and box.risk.ledger["state"] is None, spoil


def test_낡은_보내는_중을_다시_잡았으면_남은_초안이_있을_수_있다고_알린다(box):
    box.risk.ledger.update(state="sending", by="kim@corp.com", at=box.risk.now - _Risk.STALE_S - 1, pages_total=3)
    out = box.post().json()
    assert out["ok"] is True and out["orphan_possible"] is True


# ── 끊겨도 끝까지 ───────────────────────────────────────────────────────────────────────────────────────────────
def test_요청이_끊겨도_보내기와_원장_적기는_끝난다(monkeypatch):
    """브라우저가 떠나 요청이 취소돼도 도는 보내기는 끝까지 간다 — 안 그러면 그 판이 15분 동안 「보내는 중」 으로 잡힌다."""
    from app.agent import docforge_delivery as dfd

    risk = _Risk()
    gw, ra = _Gateway(risk), _RA()
    monkeypatch.setattr(M, "_TRANSPORT", httpx.MockTransport(ra))
    monkeypatch.setattr(U, "_TRANSPORT", httpx.MockTransport(gw))
    s = _settings()
    pat = jwt.encode({"email": "kim@corp.com", "scopes": ["chat"]}, "k" * 32, algorithm="HS256")   # 가짜 게이트웨이는 서명을 보지 않는다

    async def scenario() -> tuple[dict, list[str]]:
        ra.hold = asyncio.Event()
        audit = _Audit()
        job = M._job(audit, s, KIM, pat, dfd.RaSession(s.ra_base_url, "rat_kim"), TARGET, None)
        outer = asyncio.ensure_future(M._detached(job))
        while "page2" not in ra.steps():
            await asyncio.sleep(0.01)
        outer.cancel()
        with pytest.raises(asyncio.CancelledError):
            await outer
        assert risk.ledger["state"] == "sending" and M._TASKS, "보내기는 아직 돈다"
        ra.hold.set()
        await asyncio.gather(*list(M._TASKS))
        assert not M._TASKS
        assert [r["status"] for r in audit.rows] == ["ok"]
        return risk.ledger, ra.steps()

    ledger, steps = asyncio.run(scenario())
    assert ledger["state"] == "sent" and ledger["pages_sent"] == 3 and steps == ["preview", "create", "page2", "page3"]


# ── 계약 — 형제 리포(리스크 앱) 소스와 견준다 ────────────────────────────────────────────────────────────────────
def _risk_src(name: str) -> str:
    path = _RISK_REPO / name
    if not path.is_file():
        pytest.skip(f"형제 리포 HWAXRisk 가 곁에 없다({path.parent}) — 계약은 그 리포가 있는 박스에서만 견준다")
    return path.read_text(encoding="utf-8")


def test_계약_두_창구의_이름과_인자가_리스크_앱과_같다():
    """포털이 부르는 도구 이름 · 싣는 인자가 리스크 앱의 스위치 뒤 도구 둘과 같다 — 가짜(_Risk)의 인자도 같다. 리스크 앱이 아직 두 창구를 싣지
    않은 판이면 붉다(그 리포를 먼저 올린다)."""
    tree = ast.parse(_risk_src("mcp_server.py"))
    tools = {n.name: [a.arg for a in n.args.args] for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef)
             and n.name.startswith("risk_report_ra_")}
    assert set(tools) == {"risk_report_ra_material", "risk_report_ra_record"}
    prefix = "heaxhwax_risk_"
    assert (M.TOOL_MATERIAL, M.TOOL_RECORD) == (MATERIAL, RECORD) == (prefix + "risk_report_ra_material", prefix + "risk_report_ra_record")
    assert tools["risk_report_ra_material"] == ["target_key", "version"]
    assert tools["risk_report_ra_record"] == ["target_key", "report_uid", "report_id", "url", "pages_sent", "error_reason", "error_text",
                                               "outcome_unknown"]
    import inspect
    assert list(inspect.signature(_Risk.material).parameters)[2:] == tools["risk_report_ra_material"]
    assert list(inspect.signature(_Risk.record).parameters)[2:] == tools["risk_report_ra_record"]
    switched = re.search(r"SWITCHED_TOOLS[^=]*=\s*\((.*?)\n\)", _risk_src("mcp_server.py"), re.S).group(1)
    assert switched.count("config.ra_report_draft_enabled") == 2, "두 창구는 리스크 앱의 스위치 뒤에 있다(포털에 둘째 스위치가 없다)"


def test_계약_포털이_옮기는_오류_낱말이_리스크_앱에_있다():
    src = _risk_src("routes.py") + _risk_src("report_ra.py") + _risk_src("entry.py")
    for code in M.RISK_CODES:
        assert f'"{code}"' in src, code
    # 리스크 앱이 두 창구에서 내는 낱말 가운데 포털이 모르는 것이 없다(적기 쪽의 낱말은 포털이 원장 적기 실패로 묶는다)
    raised = set(re.findall(r'AppError\("(ra_report_[a-z_]+)"', src))
    assert raised <= set(M.RISK_CODES) | {"ra_report_not_claimed", "ra_report_id_conflict"}, raised - set(M.RISK_CODES)


def test_계약_RA_호출_하나의_기한이_리스크_앱의_낡음_기한보다_짧다():
    """리스크 앱은 「보내는 중」 이 CLAIM_STALE_S 보다 낡으면 죽은 시도로 보고 다시 잡는다 — 포털이 RA 호출 하나를 기다리는 기한은 그보다 짧아야
    한다(도는 보내기를 죽었다고 읽지 않게). 가짜(_Risk.STALE_S)도 같은 값이다."""
    stale = int(re.search(r"^CLAIM_STALE_S = (\d+)", _risk_src("report_ra.py"), re.M).group(1))
    assert stale == _Risk.STALE_S
    assert M._RA_TIMEOUT.read < stale and M._RA_TIMEOUT.connect < stale
    assert M.MATERIAL_TIMEOUT_S < stale and M.RECORD_TIMEOUT_S < stale


def test_계약_두_창구는_게이트웨이의_응답_캐시에_담기지_않는다():
    """게이트웨이는 이름 접두(list_ · get_ · report_ …)로 읽기 도구의 답을 300초 담는다. 재료 내주기가 담기면 다시 누른 호출이 옛 원장(초안 번호
    없음)을 받아 초안을 또 만든다 — 두 창구의 원래 이름은 그 접두에 걸리지 않아야 한다."""
    gw = Path(__file__).resolve().parents[2].parent / "HWAXMcpGateway" / "gateway.py"
    if not gw.is_file():
        pytest.skip(f"형제 리포 HWAXMcpGateway 가 곁에 없다({gw.parent})")
    tree = ast.parse(gw.read_text(encoding="utf-8"))
    (cacheable,) = [ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == "_CACHEABLE" for t in n.targets)]
    assert "report_" in cacheable, "가짜가 아니라 진짜 목록을 읽었다"
    for tool in (M.TOOL_MATERIAL, M.TOOL_RECORD):
        original = tool.removeprefix("heaxhwax_risk_")
        assert original.startswith("risk_report_ra_") and not original.startswith(tuple(cacheable)), original
