# 발표자료로 — 그 사람 명의 RA 읽기 · 허브 Caddy 경유 WDA · 주인만 · 한 번만 알림 · 상태 낱말 하나 · 받기 중계(docs/wda-deck)
"""가짜 RA 와 가짜 '허브 게이트 + WDA'(httpx MockTransport)로 포털 창구를 끝에서 끝까지 본다.

가짜 WDA 는 **요청서(docs/wda-deck/wda-request.md)의 계약**을 따르되, 오류는 **지금 WDA 의 꼴**이다(적대 검토 11-01, WD-D48) — 4xx 는
`{"detail"}` 이고 code 가 없으며(W-10 전), 글은 진짜 WDA 처럼 `f"{type(exc).__name__}: {exc}"` 다(경로 · run_id 가 실릴 수 있다). 모르는 꼴의 400 만
봉투 `{success, data, message}` 다(11-01 저녁 판). `error_codes=True` 면 요청서 W-10 의 봉투 + code 로 답한다. 허브 게이트도 진짜 꼴 — 익명 401 은 몸이
비고, 거절된 포털 토큰 401 · 허브 계정 없음 403 · JWKS 를 못 읽음 503 은 `{"detail"}`, 앱을 볼 수 없음 403 은 몸이 비며, 읽기 전용 포털 토큰의 GET 밖은
403 이다(HEAXHub authz.py · portal_sso.py). 상태 낱말(파이프라인 queued/running/done/failed · 단계 pending/running/done/failed · 렌더 queued/rendering/
done/failed) · 남과 신원 없음에 404 ·
features(owner · 꼴마다 format:<id>) · formats(꼴마다 상태 draft · active — WDA 의 꼴 등록부, 11-01 답) · 만들기의 format 칸(없으면 wide-16x9 ·
모르는 꼴이면 곧바로 400 INVALID 와 쓸 수 있는 꼴). 허브 게이트는 포털 PAT 의 서명 · 청중 · scope 를 보고 그 이메일을 X-Heax-User-Email 로 싣는
Caddy 를 흉내 낸다. 만들기 본문은 WDA 가 알려 준 블록 글자 규칙으로 센다 — rich_text 는 content.markdown, heading 은 content.text, props.default_text 는
대신 쓰지 않고, content 에 없는 블록은 글자 0, 모두 0 이면 거절.
"""
import asyncio
import copy
import json
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import httpx
import jwt
import pytest
from fastapi.testclient import TestClient

from app.agent import wda_deck as W
from app.auth.provider import Principal
from app.config import Settings, get_settings
from app.deps import principal_pat_or_session
from app.main import app

NEEDS = ["plat:webdesign", "plat:reportarchive"]
KIM = Principal(subject="kim@corp.com", email="kim@corp.com", display_name="김", groups=NEEDS)
LEE = Principal(subject="lee@corp.com", email="lee@corp.com", display_name="이", groups=NEEDS)
BASE = "http://hub.test/apps/web_design_agents"

IMPORT = {"id": 41, "workspace_slug": "personal-5", "template_id": "__import_blank__", "template_version": 1, "title": "설계 검토",
          "tags": ["docforge"], "content": {}, "pages": [{
              "template_id": "__import_blank__", "template_version": 1, "name": "1쪽",
              "extra_blocks": [{"id": "b001", "type": "heading", "props": {"level": 1}},
                               {"id": "b002", "type": "rich_text", "props": {}},
                               {"id": "b003", "type": "image", "props": {"max_count": 1}}],
              "content": {"b001": {"text": "설계 검토", "level": 1}, "b002": {"markdown": "결론 — 두께 12um 는 위험하다."},
                          "b003": {"files": [{"file_id": 77, "caption": "그림 1"}]}},
              "blocks_order": ["b001", "b002", "b003"]}]}
# 글이 하나도 없는 보고서 — heading 의 props.default_text 는 대신 쓰지 않고, content 에 없는 블록은 글자 0(WDA 11-01)
EMPTY = {**IMPORT, "id": 42, "title": "빈 보고서", "pages": [{
    "template_id": "__import_blank__", "template_version": 1,
    "extra_blocks": [{"id": "b001", "type": "heading", "props": {"default_text": "제목"}}, {"id": "b002", "type": "rich_text", "props": {}}],
    "content": {}}]}
# 심의 템플릿 보고서 — 블록 정의가 보고서에 없다(템플릿 블록은 content 키만, 에이전트 서버 create_report_draft template deliberation)
DELIB = {"id": 58, "workspace_slug": "personal-5", "template_id": "deliberation", "template_version": 1, "title": "심의 — 굽힘",
         "tags": ["심의"], "content": {}, "pages": [{
             "template_id": "deliberation", "template_version": 1, "extra_blocks": [],
             "content": {"background": {"markdown": "심의 주제: 굽힘"}, "recommendation": {"markdown": "결정 — 12um 는 쓰지 않는다"}}}]}


class FakeHubWDA:
    """허브 게이트(포털 PAT 검증 → X-Heax-User-Email) + 요청서 계약의 WDA + RA."""

    def __init__(self, keystore, *, features=("owner",), chain=True, error_codes=False):
        self.keystore, self.features, self.chain, self.error_codes = keystore, set(features), chain, error_codes
        # WDA 의 꼴 등록부(꼴 id → 상태) — features 에 format:<id> 가 저절로 실린다. 심의 꼴(delib-16x9)은 시험이 넣는다
        self.formats = {"wide-16x9": "active", "short-9x16": "active", "print-a4": "draft"}
        self.version = "0.1.0"                         # 패키지 판(허브 매니페스트 판과 같다 — WDA 11-01)
        self.run_formats: dict[str, str] | None = None  # 만들기가 받는 꼴 — None 이면 formats 와 같다(health 와 어긋나는 판을 흉내 낼 때만)
        self.idem: dict[str, str] = {}                 # Idempotency-Key → run_id(요청서 W-15 — 같은 키의 두 번째 만들기는 같은 run)
        self.lose_create_response = 0                  # 만들기를 받아 실행을 만든 뒤 답을 잃는다(읽기 시간 초과) — 남은 횟수
        self.refuse_connect = 0                        # 만들기에 연결 자체를 거절한다 — 남은 횟수
        self.runs: dict[str, dict] = {}
        self.reports = {41: IMPORT, 42: EMPTY, 58: DELIB}
        self.calls: list[tuple[str, str]] = []          # (메서드, 경로)
        self.created: list[dict] = []                  # 받은 만들기 본문
        self.client_identity: list[str] = []           # 클라이언트가 보낸 X-Heax-User-Email(있으면 안 된다)
        self.pats: list[dict] = []
        self.pat_calls: list[tuple[str, str, str]] = []     # (메서드, WDA 경로, 그 부르기에 실린 PAT 의 jti)
        self.ra_delay: dict[str, float] = {}           # RA 토큰 → 늦추는 초(그 사람의 RA 만 느리다)
        self.ra_auth: list[str] = []
        self.no_hub_account: set[str] = set()
        self.not_viewable: set[str] = set()            # 허브 계정은 있으나 이 앱을 볼 수 없다(can_view_app 거절 — 몸 없는 403)
        self.jwks_down = False                         # 허브가 포털 JWKS 를 못 읽는다(503)
        self.reject_all = False                        # 허브 게이트가 모든 포털 토큰을 거절한다(서명 · 만료 · 청중 — 401 detail)
        self.health_down = False
        self.slow = 0.0
        self.max_bytes = 16 * 1024 * 1024
        self.chunks_sent = 0                           # 흘려 보낸 덩어리 수(RA 큰 보고서 · 받기 실패의 큰 몸) — 받는 쪽이 어디서 멈췄나
        self.download_fails_big = False                # 받기가 500 과 끝없는 몸을 준다
        self.files = {"pptx": b"PK\x03\x04pptx-bytes", "pdf": b"%PDF-1.7 deck", "docx": b"PK\x03\x04docx", "html": b"<html>x</html>",
                      "mp4": b"\x00\x00\x00\x18ftypmp4"}

    # ── 가짜를 움직이는 손 ──
    def set_run(self, run_id: str, **kw):
        self.runs[run_id].update(kw)

    def stage(self, run_id: str, stage: str):
        run = self.runs[run_id]
        seen = True
        for s in run["stages"]:
            if s["stage"] == stage:
                s["status"], seen = "running", False
            else:
                s["status"] = "done" if seen else "pending"
        run["status"] = "running"

    def built(self, run_id: str):
        run = self.runs[run_id]
        for s in run["stages"]:
            s["status"] = "done"
        run["status"] = "done"
        if self.chain and run["render_opts"]:
            run["render"] = {"status": "queued", "targets": run["render_opts"]["targets"], "requested": run["render_opts"]["targets"],
                             "outputs": {}, "skipped": [], "error": None}

    def rendered(self, run_id: str, *, skip: dict | None = None):
        run = self.runs[run_id]
        req = run["render"]["requested"]
        skip = skip or {}
        run["render"].update(status="done", outputs={t: f"/data/renders/x/{t}" for t in req if t not in skip},
                             skipped=[{"target": t, "reason": r} for t, r in skip.items()])

    # ── 처리 ──
    def env(self, status: int, data=None, message: str = "", code: str | None = None):
        if status >= 400 and not self.error_codes:
            return httpx.Response(status, json={"detail": message})       # 지금 WDA 의 4xx — detail 하나, code 없음
        body = {"success": status < 400, "data": data, "message": message}
        if code and self.error_codes:
            body["code"] = code
        return httpx.Response(status, json=body)

    async def handler(self, req: httpx.Request) -> httpx.Response:
        if self.slow:
            await asyncio.sleep(self.slow)
        if req.url.host == "ra.test":
            if d := self.ra_delay.get(req.headers.get("authorization", "").removeprefix("Bearer ")):
                await asyncio.sleep(d)
            return self.ra(req)
        assert req.url.host == "hub.test", req.url
        self.calls.append((req.method, req.url.path))
        if "x-heax-user-email" in req.headers:
            self.client_identity.append(req.headers["x-heax-user-email"])
        auth = req.headers.get("authorization", "")
        if not auth.startswith("Bearer "):
            return httpx.Response(401)                                        # portal_auth: true — 익명은 health 까지 몸 없는 401
        if self.jwks_down:
            return httpx.Response(503, json={"detail": "포털 공개키(JWKS)를 못 읽었다 — 잠시 뒤 다시"})
        try:
            if self.reject_all:
                raise jwt.InvalidTokenError("거절")
            claims = jwt.decode(auth[7:], self.keystore.public_pem(self.keystore.active_kid), algorithms=["RS256"], audience="heax-hub",
                                options={"require": ["exp", "jti", "sub"]})
        except jwt.PyJWTError:
            return httpx.Response(401, json={"detail": "포털 토큰이 거절됐다(서명 · 만료 · 청중 heax-hub)"})
        assert claims["scope"] == "api"
        self.pats.append(claims)
        self.pat_calls.append((req.method, req.url.path.removeprefix("/apps/web_design_agents"), claims["jti"]))
        email = str(claims.get("email") or "").lower()
        if email in self.no_hub_account:
            return httpx.Response(403, json={"detail": "허브 계정이 없다 — 포털에서 HEAX Hub 타일을 한 번 눌러 허브에 로그인한 뒤 다시 시도한다"})
        if email in self.not_viewable:
            return httpx.Response(403)                                        # can_view_app 거절 — 몸 없음
        scopes = {str(x).lower() for x in claims.get("scopes") or []}
        if "read" in scopes and "write" not in scopes and req.method not in ("GET", "HEAD"):
            return httpx.Response(403, json={"detail": "읽기 전용 포털 토큰 — GET · HEAD 만 연다"})
        path = req.url.path.removeprefix("/apps/web_design_agents")
        return self.wda(req, path, email)

    async def _stream(self, n: int, size: int = 64 * 1024):
        for _ in range(n):
            self.chunks_sent += 1
            yield b"x" * size

    def ra(self, req: httpx.Request) -> httpx.Response:
        self.ra_auth.append(req.headers.get("authorization", ""))
        rid = int(req.url.path.rsplit("/", 1)[1])
        if req.headers.get("authorization") not in ("Bearer rat_kim", "Bearer rat_lee"):
            return httpx.Response(401, json={"detail": "unauthorized"})
        if rid == 777:                                  # 4 MB 를 길이 머리 없이 흘린다
            return httpx.Response(200, content=self._stream(64))
        if rid == 403:
            return httpx.Response(403, json={"detail": "Out of workspace scope"})
        if rid not in self.reports:
            return httpx.Response(404, json={"success": False, "message": "Report not found"})
        return httpx.Response(200, json={"success": True, "data": copy.deepcopy(self.reports[rid])})

    def _text_blocks(self, report: dict, fmt: str) -> tuple[int, int]:
        """WDA 의 블록 글자 규칙(11-01) — (블록 수, 글자 있는 블록 수)."""
        n = t = 0
        for p in report.get("pages") or []:
            content = p.get("content") or {}
            defs = list(p.get("extra_blocks") or [])
            if p.get("template_id") == "deliberation" and fmt == "delib-16x9":
                defs += [{"id": k, "type": "rich_text"} for k in content]      # 심의 꼴로 맡긴 실행은 템플릿 블록을 안다(W-21)
            for b in defs:
                n += 1
                c = content.get(b["id"], b.get("content"))
                if not isinstance(c, dict):
                    continue
                txt = c.get("markdown") if b["type"] == "rich_text" else c.get("text") if b["type"] == "heading" else None
                if txt and str(txt).strip():
                    t += 1
        return n, t

    def _mine(self, run_id: str, email: str):
        run = self.runs.get(run_id)
        if run is None or not run["owner"] or run["owner"] != email:
            return None
        return run

    def wda(self, req: httpx.Request, path: str, email: str) -> httpx.Response:
        if path == "/api/health":
            if self.health_down:
                return httpx.Response(503)
            return httpx.Response(200, json={"status": "ok", **({"version": self.version} if self.version else {}),
                                             "features": sorted(self.features | {f"format:{k}" for k in self.formats}),
                                             "formats": dict(self.formats)})
        if path == "/api/runs" and req.method == "POST":
            if self.refuse_connect:
                self.refuse_connect -= 1
                raise httpx.ConnectError("연결 거절", request=req)
            key = req.headers.get("idempotency-key")
            if key and key in self.idem:
                rid = self.idem[key]
                return self.env(202, {"run_id": rid, "slug": json.loads(req.content)["slug"], "owner": self.runs[rid]["owner"]})
            if len(req.content) > self.max_bytes:
                return self.env(413, message="PayloadTooLarge: 본문이 크다", code="TOO_LARGE")
            body = json.loads(req.content)
            self.created.append(body)
            fmt = body.get("format", "wide-16x9")
            if fmt not in (self.formats if self.run_formats is None else self.run_formats):
                # 11-01 저녁 판 — 모르는 꼴은 곧바로 400 이고 봉투(code 없음)에 쓸 수 있는 꼴을 싣는다
                return httpx.Response(400, json={"success": False, "data": None,
                                                 "message": f"ValueError: 모르는 format '{fmt}' — 쓸 수 있는 꼴: {', '.join(sorted(self.formats))}",
                                                 **({"code": "INVALID"} if self.error_codes else {})})
            n, t = self._text_blocks(body["report_json"], fmt)
            if not t:
                return self.env(422, message=f"ValueError: 텍스트를 가진 블록이 없다 (블록 {n}개, 텍스트 0개)", code="INVALID")
            rid = f"wr-{uuid.uuid4().hex}"
            self.runs[rid] = {"run_id": rid, "owner": email, "status": "queued", "error": None, "render": None,
                              "format": fmt, "render_opts": body.get("render"),
                              "stages": [{"stage": s, "status": "pending", "error": None} for s in ("ingest", "fragmentize", "scenario", "build")]}
            if key:
                self.idem[key] = rid
            if self.lose_create_response:
                self.lose_create_response -= 1
                raise httpx.ReadTimeout("답을 잃었다", request=req)
            return self.env(202, {"run_id": rid, "slug": body["slug"], "owner": email})
        parts = path.split("/")          # ['', 'api', 'runs', id, ...]
        if len(parts) >= 4 and parts[1:3] == ["api", "runs"]:
            run = self._mine(parts[3], email)
            if run is None:
                return self.env(404, message=f"FileNotFoundError: /data/wda/pipeline/{parts[3]}/run.json", code="NOT_FOUND")
            rest = parts[4:]
            if not rest and req.method == "GET":
                return self.env(200, {k: v for k, v in run.items() if k != "render_opts"})
            if rest == ["render"] and req.method == "POST":
                if run["status"] != "done":
                    return self.env(409, message="RuntimeError: 빌드 전", code="NOT_BUILT")
                if run["render"] and run["render"]["status"] in ("queued", "rendering"):
                    return self.env(409, message=f"RuntimeError: 이미 렌더 중 — {parts[3]}", code="BUSY")
                b = json.loads(req.content)
                run["render"] = {"status": "queued", "targets": b["targets"], "requested": b["targets"], "outputs": {}, "skipped": [], "error": None}
                return self.env(202, {"run_id": run["run_id"]})
            if rest == ["artifacts"]:
                outs = (run["render"] or {}).get("outputs") or {}
                wk = {"video": "mp4"}
                arts = {k: {"exists": False, "size": None} for k in ("mp4", "pptx", "html", "pdf", "docx", "qa", "scenario")}
                for t in outs:
                    k = wk.get(t, t)
                    arts[k] = {"exists": True, "size": len(self.files[k])}
                return self.env(200, arts)
            if len(rest) == 2 and rest[0] == "download":
                if self.download_fails_big:
                    return httpx.Response(500, content=self._stream(64))
                k = rest[1]
                outs = {{"video": "mp4"}.get(t, t) for t in ((run["render"] or {}).get("outputs") or {})}
                if k not in outs:
                    return self.env(404, message=f"FileNotFoundError: /data/wda/renders/{parts[3]}/{k}", code="NOT_FOUND")
                return httpx.Response(200, content=self.files[k], headers={"content-type": "application/octet-stream",
                                                                          "content-disposition": f'attachment; filename="{parts[3]}-{k}"'})
        return self.env(404, message="Not Found", code="NOT_FOUND")


@pytest.fixture()
def box(tmp_path, monkeypatch):
    s = Settings(_env_file=None, upload_staging_dir=str(tmp_path / "staging"), ra_base_url="http://ra.test", ra_sso_secret="",
                 wda_deck_enabled=True, wda_base_url=BASE)
    who = {"p": KIM}
    app.dependency_overrides[get_settings] = lambda: s
    app.dependency_overrides[principal_pat_or_session] = lambda: who["p"]
    W._CAPS.update(at=0.0, features=None)
    W._LOCKS.clear()
    with TestClient(app) as c:
        fake = FakeHubWDA(app.state.keystore)
        real = httpx.AsyncClient
        monkeypatch.setattr(W, "_http", lambda timeout: real(transport=httpx.MockTransport(fake.handler), timeout=timeout))
        app.state.user_store.set_connection(email="kim@corp.com", service="reportarchive", token="rat_kim")
        app.state.user_store.set_connection(email="lee@corp.com", service="reportarchive", token="rat_lee")
        conv = {}
        for p in (KIM, LEE):
            who["p"] = p
            conv[p.subject] = c.post("/agent/conversations", json={"title": "t", "kind": "chat"}).json()["id"]
        who["p"] = KIM
        yield {"c": c, "s": s, "fake": fake, "who": who, "conv": conv}
    app.dependency_overrides.pop(get_settings, None)
    app.dependency_overrides.pop(principal_pat_or_session, None)
    W._CAPS.update(at=0.0, features=None)


def _make(b, report_id=41, **kw):
    body = {"report_id": report_id, "conversation_id": b["conv"][b["who"]["p"].subject], **kw}
    return b["c"].post("/agent/deck/jobs", json=body)


def _run_id(b) -> str:
    (rid,) = b["fake"].runs
    return rid


def _messages(b, who=KIM) -> list[dict]:
    b["who"]["p"] = who
    return b["c"].get(f"/agent/conversations/{b['conv'][who.subject]}").json()["messages"]


# ── 만들기 ─────────────────────────────────────────────────────────────────────────────────────
def test_만들기는_그_사람_RA_토큰으로_읽고_ReportRead_를_바꾸지_않고_허브를_거쳐_넘긴다(box):
    r = _make(box)
    assert r.status_code == 200, r.text
    j = r.json()
    fake = box["fake"]
    assert fake.ra_auth == ["Bearer rat_kim"], "RA 는 그 사람의 토큰으로만 읽는다"
    (sent,) = fake.created
    assert sent["report_json"] == IMPORT, "RA 의 ReportRead 를 바꾸지 않고 넘긴다(WDA 가 받는 꼴)"
    assert "format" not in sent, "심의 밖의 템플릿은 format 칸을 싣지 않는다(WDA 기본 wide-16x9)"
    assert sent["render"] == {"targets": ["pptx", "pdf"], "doc_style": "report", "pptx_mode": "hybrid", "narration": False}
    assert sent["slug"] == "ra-41" and sent["source"]["report_id"] == 41
    assert fake.client_identity == [], "X-Heax-User-Email 은 Caddy 가 싣는다 — 포털은 싣지 않는다"
    pat = fake.pats[-1]
    assert pat["email"] == "kim@corp.com" and pat["aud"] == ["heax-hub"] and pat["exp"] - pat["iat"] <= 600
    assert fake.runs[_run_id(box)]["owner"] == "kim@corp.com"
    assert j["created"] is True and W._JOB_RE.fullmatch(j["job_id"]) and j["state"] == "queued"
    assert _run_id(box) not in r.text and "hub.test" not in r.text, "브라우저는 WDA 의 run_id · 주소를 보지 않는다"
    rec = W.load(box["s"], j["job_id"], "kim@corp.com")
    assert rec["images_not_sent"] == 1 and rec["report"] == {"id": 41, "title": "설계 검토"}
    assert rec["wda"]["version"] == "0.1.0" and "0.1.0" not in r.text, "만들 때 본 WDA 판을 기록에만 남긴다(진단용)"
    assert oct(os.stat(W._path(box["s"], j["job_id"])).st_mode & 0o777) == "0o600"


@pytest.mark.parametrize("rid", [".", "..", "a/b", "", "x" * 129])
def test_WDA_가_준_실행_번호가_경로를_바꿀_꼴이면_받지_않는다(box, rid):
    """적대 검토 R9 — '..' 를 받으면 다음 부르기의 /api/runs/../download/pptx 가 /api/download/pptx 로 정규화된다."""
    orig = box["fake"].wda

    def odd(req, path, email):
        resp = orig(req, path, email)
        if path == "/api/runs" and req.method == "POST" and resp.status_code == 202:
            j = json.loads(resp.content)
            j["data"]["run_id"] = rid
            return httpx.Response(202, json=j)
        return resp

    box["fake"].wda = odd
    r = _make(box)
    assert r.status_code == 502 and "실행 번호" in r.json()["detail"] and W.records(box["s"]) == []
    assert W._RUN_RE.fullmatch("wr-20261101-0a1b.c_d")


def test_글이_없는_보고서는_정해진_글로_말하고_잡을_남기지_않는다(box):
    r = _make(box, report_id=42)
    detail = r.json()["detail"]
    assert r.status_code == 422 and "WDA 가 이 보고서를 다루지 못했습니다" in detail
    assert "ValueError" not in detail and "텍스트를 가진 블록" not in detail, "WDA 의 예외 글은 사람에게 보이지 않는다(WD-D49)"
    assert W.records(box["s"]) == []


def test_고른_출력과_문서_꼴이_간다_순서는_정해진_차례로(box):
    r = _make(box, targets=["video", "docx", "pptx"], doc_style="memo")
    assert r.status_code == 200
    assert box["fake"].created[-1]["render"]["targets"] == ["pptx", "docx", "video"]
    assert box["fake"].created[-1]["render"]["doc_style"] == "memo"
    for bad in ({"targets": []}, {"targets": ["gif"]}, {"doc_style": "slides"}, {"report_id": True}, {"report_id": 0}, {"extra": 1}):
        assert _make(box, **bad).status_code == 422, bad


def test_남의_대화에는_만들지_않는다(box):
    r = box["c"].post("/agent/deck/jobs", json={"report_id": 41, "conversation_id": box["conv"]["lee@corp.com"]})
    assert r.status_code == 404 and box["fake"].created == []


# ── 문 — 권한 · 스위치 · 능력 · 템플릿 ───────────────────────────────────────────────────────────────
def test_권한_둘_중_하나라도_없으면_403_이고_status_는_permission(box):
    for groups in (["plat:webdesign"], ["plat:reportarchive"], []):
        box["who"]["p"] = Principal(subject="kim@corp.com", email="kim@corp.com", display_name="김", groups=groups)
        assert _make(box).status_code == 403
        st = box["c"].get("/agent/deck/status").json()
        assert st["enabled"] is False and st["reason"] == "permission"
    assert box["fake"].created == []


def test_권한을_거두면_목록_진행_advance_받기_숨기기도_403_이고_허브_토큰을_찍지_않는다(box):
    """적대 검토 R4 — 만들기만 ensure 했다. 거둔 권한으로 받기 · 진행 · advance 가 이어지고 허브 토큰이 찍혔다(WD-D50)."""
    c, fake = box["c"], box["fake"]
    done = _make(box, targets=["pptx"]).json()["job_id"]
    rid = _run_id(box)
    fake.built(rid)
    fake.rendered(rid)
    c.post(f"/agent/deck/jobs/{done}/advance")
    running = _make(box, doc_style="memo").json()["job_id"]
    n_pats = len(fake.pats)
    for groups in ([], ["plat:webdesign"], ["plat:reportarchive"]):
        box["who"]["p"] = Principal(subject="kim@corp.com", email="kim@corp.com", display_name="김", groups=groups)
        for r in (c.get(f"/agent/deck/jobs/{done}/files/pptx"), c.get(f"/agent/deck/jobs/{running}"), c.get("/agent/deck/jobs"),
                  c.post(f"/agent/deck/jobs/{running}/advance"), c.post(f"/agent/deck/jobs/{running}/dismiss")):
            assert r.status_code == 403, (groups, r.request.url, r.status_code)
    assert len(fake.pats) == n_pats, "권한이 없는 사람 이름으로 허브 토큰을 찍지 않는다"


# ── 진짜 인증 길 — 위 시험은 principal_pat_or_session 을 덮는다. 이 둘은 덮지 않는다(적대 검토 R7, WD-D51) ──────────────
def _real_auth(box, monkeypatch):
    import app.deps as deps
    app.dependency_overrides.pop(principal_pat_or_session, None)
    # 권한 원장은 박스마다 다르다 — 로그인 그룹에서 권한 키를 셈하는 자리(entitled)만 두 권한으로 고정한다
    monkeypatch.setattr(deps, "entitled", lambda request, p, admin=frozenset(): p.model_copy(update={"groups": list(NEEDS)}))
    box["c"].cookies.clear()


def _pat(box, scopes):
    from datetime import UTC, datetime, timedelta
    ks = app.state.keystore
    now = datetime.now(tz=UTC)
    claims = {"iss": box["s"].jwt_issuer, "sub": "kim@corp.com", "email": "kim@corp.com", "name": "김", "groups": [],
              "aud": [box["s"].pat_chat_audience], "scope": "api", "jti": f"t-{time.time_ns()}", "iat": now, "exp": now + timedelta(days=1)}
    if scopes is not None:
        claims["scopes"] = list(scopes)
    return jwt.encode(claims, ks.private_pem, algorithm="RS256", headers={"kid": ks.active_kid})


def test_세션_길은_CSRF_가_있어야_맡긴다(box, monkeypatch):
    _real_auth(box, monkeypatch)
    c = box["c"]
    c.cookies.set("hwax_session", app.state.jwt_service.issue_session(KIM))
    c.cookies.set("hwax_csrf", "csrf-1")
    body = {"report_id": 41, "conversation_id": box["conv"]["kim@corp.com"]}
    assert c.post("/agent/deck/jobs", json=body).status_code == 403, "CSRF 머리 없는 쿠키 POST"
    assert box["fake"].created == []
    r = c.post("/agent/deck/jobs", json=body, headers={"X-CSRF-Token": "csrf-1"})
    assert r.status_code == 200 and r.json()["created"] is True
    job = r.json()["job_id"]
    assert c.get(f"/agent/deck/jobs/{job}").status_code == 200, "읽기(GET)는 세션만으로"
    assert c.post(f"/agent/deck/jobs/{job}/advance").status_code == 403
    assert c.post(f"/agent/deck/jobs/{job}/advance", headers={"X-CSRF-Token": "csrf-1"}).status_code == 200
    c.cookies.clear()


@pytest.mark.parametrize("scopes,writes", [(["read"], False), (["chat"], False), (["read", "write"], True), (None, True)])
def test_PAT_길은_write_범위가_있어야_맡기고_바꾼다(box, monkeypatch, scopes, writes):
    _real_auth(box, monkeypatch)
    c = box["c"]
    h = {"Authorization": f"Bearer {_pat(box, scopes)}"}
    body = {"report_id": 41, "conversation_id": box["conv"]["kim@corp.com"]}
    r = c.post("/agent/deck/jobs", json=body, headers=h)
    assert c.get("/agent/deck/jobs", headers=h).status_code == 200, "읽기는 어느 범위든"
    if not writes:
        assert r.status_code == 403 and "쓰기 범위" in r.json()["detail"]
        assert box["fake"].created == [] and not any(m == "POST" for m, _ in box["fake"].calls), "허브에 쓰기가 나가지 않는다"
        jid = "a" * 32
        assert c.post(f"/agent/deck/jobs/{jid}/advance", headers=h).status_code == 403
        assert c.post(f"/agent/deck/jobs/{jid}/dismiss", headers=h).status_code == 403
    else:
        assert r.status_code == 200 and r.json()["created"] is True


def test_스위치가_꺼지면_창구는_없고_status_는_off(box):
    box["s"].wda_deck_enabled = False
    assert _make(box).status_code == 404
    assert box["c"].get("/agent/deck/jobs").status_code == 404
    st = box["c"].get("/agent/deck/status").json()
    assert st == {**st, "enabled": False, "reason": "off"}
    assert box["fake"].calls == [], "꺼진 박스는 WDA 를 부르지 않는다"


def test_WDA_판을_모르면_기록에_비워_두고_막지_않는다(box):
    box["fake"].version = None
    j = _make(box).json()
    assert j["created"] is True and W.load(box["s"], j["job_id"], "kim@corp.com")["wda"]["version"] is None


def test_WDA_에_주인_기능이_없거나_상태를_모르면_만들지_않는다(box):
    box["fake"].features = set()
    assert _make(box).status_code == 409
    assert box["c"].get("/agent/deck/status").json()["reason"] == "no_owner"
    W._CAPS.update(at=0.0, features=None)
    box["fake"].health_down = True
    assert _make(box).status_code == 503
    assert box["c"].get("/agent/deck/status").json()["reason"] == "unknown"
    assert box["fake"].created == [] and box["fake"].ra_auth == [], "주인 기능을 모르는 WDA 에는 보고서를 읽지도 넘기지도 않는다"


@pytest.mark.parametrize("state,shown", [(None, False), ("draft", False), ("active", True)])
def test_심의_보고서는_delib_16x9_가_active_일_때만_서고_그_꼴을_실어_만든다(box, state, shown):
    """사용자 결정(11-01, WD-D42) — 없음 · draft 는 숨기고(만들기 409 · WDA 에 넘기지 않는다) active 일 때만 연다. draft 를 여는 손잡이는 없다."""
    fake = box["fake"]
    if state:
        fake.formats["delib-16x9"] = state
    st = box["c"].get("/agent/deck/status").json()
    assert st["enabled"] is True and st["formats"] == {"deliberation": shown}
    r = _make(box, report_id=58)
    if not shown:
        assert r.status_code == 409 and f"delib-16x9 — {state or '없음'}" in r.json()["detail"]
        assert fake.created == [] and W.records(box["s"]) == [], "준비되지 않은 꼴로는 심의 보고서를 넘기지 않는다(사용자 결정 11-01 U-6 · U-7)"
        return
    assert r.status_code == 200
    (sent,) = fake.created
    assert sent["format"] == "delib-16x9" and sent["report_json"] == DELIB, "그 꼴을 싣고 ReportRead 는 그대로"
    assert fake.runs[_run_id(box)]["format"] == "delib-16x9"


def test_WDA_가_모르는_꼴이면_400_의_까닭을_보이고_기본_꼴로_다시_보내지_않는다(box):
    """만들기는 탐침을 늘 새로 하므로(WD-D57) 꼴을 잃은 WDA 에는 409 로 멈춘다. 그래도 health 와 만들기가 어긋나는 WDA(탐침과 만들기 사이에
    되돌림)는 만들기가 곧바로 400 이다 — 그 까닭을 정해진 글로 말하고 기본 꼴로 다시 보내지 않는다."""
    fake = box["fake"]
    fake.formats["delib-16x9"] = "active"
    assert box["c"].get("/agent/deck/status").json()["formats"] == {"deliberation": True}
    fake.run_formats = {k: v for k, v in fake.formats.items() if k != "delib-16x9"}
    r = _make(box, report_id=58)
    detail = r.json()["detail"]
    assert r.status_code == 502 and "WDA 가 만들기 요청의 꼴을 받지 않았습니다" in detail
    assert "ValueError" not in detail and "print-a4" not in detail, "WDA 의 글은 서버 로그에만(WD-D49)"
    assert [c.get("format") for c in fake.created] == ["delib-16x9"], "기본 꼴(wide-16x9)로 다시 보내지 않는다"
    assert fake.runs == {} and W.records(box["s"]) == []


@pytest.mark.parametrize("features,formats,want", [
    ({"format:delib-16x9"}, {"delib-16x9": "active"}, True),
    ({"format:delib-16x9"}, {"delib-16x9": "draft"}, False),
    ({"format:delib-16x9"}, {}, False),
    (set(), {"delib-16x9": "active"}, False),
])
def test_꼴_정책은_하나다_features_와_active_가_둘_다(features, formats, want):
    assert W.format_ready(W.Caps(frozenset(features), formats), "delib-16x9") is want


# ── 만들기의 답을 잃으면 '결과를 모른다' — 다시 누르면 같은 잡 id 로(WD-D58) ─────────────────────────────────────────────
def test_만들기의_답을_잃으면_결과를_모른다고_말하고_다시_누르면_같은_키로_묻는다(box):
    c, fake, s = box["c"], box["fake"], box["s"]
    fake.lose_create_response = 1
    r = _make(box)
    assert r.status_code == 504 and "만들어졌는지 모릅니다" in r.json()["detail"] and "연결하지 못했" not in r.json()["detail"]
    (rec,) = W.records(s)
    assert W.reserving(rec) and rec["wda"]["create_unknown"] and W.inflight(rec, s, time.time()), "자리는 그대로(WDA 에서 돌 수 있다)"
    (j,) = c.get("/agent/deck/jobs").json()["jobs"]
    assert (j["state"], j["step"]) == ("failed", "결과 모름")
    keys = [k for k in fake.idem]
    r2 = _make(box)
    assert r2.status_code == 200 and r2.json()["job_id"] == rec["job_id"], "같은 잡을 잇는다"
    assert list(fake.idem) == keys == [rec["job_id"]] and len(fake.runs) == 1, "같은 Idempotency-Key — 실행이 둘이 되지 않는다"
    assert W.load(s, rec["job_id"], "kim@corp.com")["wda"]["run_id"] in fake.runs


def test_연결조차_못_했으면_연결하지_못했다고_말하고_예약을_놓는다(box):
    box["fake"].refuse_connect = 1
    r = _make(box)
    assert r.status_code == 502 and "연결하지 못했습니다" in r.json()["detail"] and W.records(box["s"]) == []
    assert _make(box).status_code == 200


# ── 만들기는 탐침을 새로 하고 202 의 주인을 본다(적대 검토 R5, WD-D57) ─────────────────────────────────────────────────────
def test_되돌린_WDA_에는_60초_안에도_본문을_넘기지_않는다(box):
    c, fake = box["c"], box["fake"]
    assert c.get("/agent/deck/status").json()["enabled"] is True        # 탐침이 60초 붙잡힌다(화면용)
    fake.features = set()                                               # 옛 SIF 로 되돌림 — owner 없음
    r = _make(box)
    assert r.status_code == 409 and fake.created == [], "만들기는 붙잡은 능력을 쓰지 않는다"


def _owner_in_202(fake, owner):
    orig = fake.wda

    def w(req, path, email):
        resp = orig(req, path, email)
        if path == "/api/runs" and req.method == "POST" and resp.status_code == 202:
            j = json.loads(resp.content)
            if owner is None:
                j["data"].pop("owner", None)
            else:
                j["data"]["owner"] = owner
            return httpx.Response(202, json=j)
        return resp

    fake.wda = w


@pytest.mark.parametrize("owner", [None, "", "admin@hub.local", "lee@corp.com"])
def test_202_의_주인이_맡긴_사람이_아니면_따라가지_않고_실패로_남긴다(box, owner):
    fake, s = box["fake"], box["s"]
    _owner_in_202(fake, owner)
    r = _make(box)
    assert r.status_code == 502 and "주인을 맡긴 사람으로 확인해 주지 않았습니다" in r.json()["detail"]
    (rec,) = W.records(s)
    assert rec["finished"]["state"] == "failed" and rec["wda"]["run_id"] in fake.runs, "WDA 의 run_id 는 진단용으로 남긴다"
    assert not W.inflight(rec, s, time.time()), "따라가지 않는다 — 상한을 먹지 않는다"
    rows = app.state.agent_audit._conn.execute(
        "SELECT status, meta FROM agent_audit WHERE event = 'deck_create' ORDER BY rowid DESC LIMIT 1").fetchone()
    assert rows[0] == "failed" and "owner_mismatch" in rows[1]


def test_202_의_주인은_대소문자를_가리지_않는다(box):
    _owner_in_202(box["fake"], "KIM@Corp.COM")
    assert _make(box).status_code == 200


@pytest.mark.parametrize("how,status,said", [("not_viewable", 403, "허브가 막았습니다"), ("jwks_down", 503, "HTTP 503"),
                                             ("no_hub_account", 403, "허브 계정이 없거나")])
def test_만들기의_탐침_거절은_정해진_글로(box, how, status, said):
    fake = box["fake"]
    if how == "jwks_down":
        fake.jwks_down = True
    else:
        getattr(fake, how).add("kim@corp.com")
    r = _make(box)
    assert r.status_code == status and said in r.json()["detail"] and fake.created == []


def test_RA_가_거절하거나_없거나_보고서가_크면_WDA_를_부르지_않는다(box):
    assert _make(box, report_id=403).status_code == 403
    assert _make(box, report_id=999).status_code == 404
    box["s"].wda_deck_report_max_mb = 0
    r = _make(box)
    assert r.status_code == 413 and "MB" in r.json()["detail"]
    assert box["fake"].created == []


def test_RA_본문은_흘려_받으며_상한에서_멈춘다(box):
    """적대 검토 — 본문을 다 받은 뒤 재면 상한이 메모리를 지키지 못한다(WD-D53)."""
    box["s"].wda_deck_report_max_mb = 1
    r = _make(box, report_id=777)
    assert r.status_code == 413 and "상한 1 MB" in r.json()["detail"]
    assert box["fake"].chunks_sent < 32, f"다 받기 전에 멈춘다(보낸 덩어리 {box['fake'].chunks_sent}/64)"
    assert box["fake"].created == []


def test_RA_연결이_없으면_고칠_곳을_말한다(box):
    box["who"]["p"] = Principal(subject="park@corp.com", email="park@corp.com", display_name="박", groups=NEEDS)
    pid = box["c"].post("/agent/conversations", json={"title": "t", "kind": "chat"}).json()["id"]
    r = box["c"].post("/agent/deck/jobs", json={"report_id": 41, "conversation_id": pid})
    assert r.status_code == 400 and "외부 연결" in r.json()["detail"]


def test_허브가_계정_없음으로_막으면_그_까닭을_그대로(box):
    box["fake"].health_down = False
    box["c"].get("/agent/deck/status")                       # 김의 성공한 탐침이 60초 붙잡힌다 — 이의 실패와 섞이지 않게
    box["fake"].no_hub_account.add("lee@corp.com")
    box["who"]["p"] = LEE
    r = _make(box)
    assert r.status_code == 403 and r.json()["detail"].startswith("허브가 막았습니다 — 허브 계정이 없거나")
    assert "HEAX Hub 타일" in r.json()["detail"], "고칠 곳을 말한다(허브가 준 글이 아니라 포털의 정해진 글로)"


def test_허브가_탐침을_401_로_막으면_모름으로_숨기고_붙잡지_않는다(box):
    """portal_auth: true(HEAXHub 385783f)부터 익명은 /api/health 도 401 이다 — 탐침은 그 사람의 PAT 를 싣고, 막히면 '모름' 으로 숨긴다(오류 되풀이 없음)."""
    box["fake"].reject_all = True
    st = box["c"].get("/agent/deck/status")
    assert st.status_code == 200 and st.json()["enabled"] is False and st.json()["reason"] == "unknown"
    r = _make(box)
    assert r.status_code == 403 and "허브가 포털 토큰을 받지 않았습니다" in r.json()["detail"] and box["fake"].created == []
    box["fake"].reject_all = False
    assert box["c"].get("/agent/deck/status").json()["enabled"] is True, "실패는 붙잡지 않는다 — 풀리면 곧바로 선다"
    assert box["fake"].pats and all(p["email"] == "kim@corp.com" for p in box["fake"].pats), "탐침도 그 사람의 PAT 로"


# ── 진행 · 끝 · 알림 ─────────────────────────────────────────────────────────────────────────────
def test_진행을_보고_끝나면_단추를_누른_대화에_알림_한_건(box):
    job = _make(box).json()["job_id"]
    c, fake = box["c"], box["fake"]
    rid = _run_id(box)
    assert c.get(f"/agent/deck/jobs/{job}").json()["state"] == "queued"
    fake.stage(rid, "scenario")
    st = c.get(f"/agent/deck/jobs/{job}").json()
    assert (st["state"], st["step"], st["progress"], st["next"]) == ("preparing", "장면 구성", 40, None)
    fake.built(rid)
    st = c.get(f"/agent/deck/jobs/{job}").json()
    assert (st["state"], st["step"]) == ("rendering", "차례 기다림")
    fake.rendered(rid)
    st = c.get(f"/agent/deck/jobs/{job}").json()
    assert (st["state"], st["next"]) == ("done", "finish")
    assert len(_messages(box)) == 0, "GET 은 부작용이 없다 — 알림은 advance 만"
    a = c.post(f"/agent/deck/jobs/{job}/advance").json()
    assert a["state"] == "done" and a["noticed"] is True and [f["kind"] for f in a["files"]] == ["pptx", "pdf"]
    (m,) = _messages(box)
    assert m["role"] == "assistant" and m["content"] == a["notice"]["text"]
    assert f"(/agent/deck/jobs/{job}/files/pptx)" in m["content"] and "PDF(정식 보고서 문서)" in m["content"]
    assert "그림 · 첨부 1개는 이번에 싣지 않았습니다" in m["content"]
    (act,) = m["meta"]["activity"]
    assert act["origin"] == "upload" and act["tool"] == "web_design_agents" and m["meta"]["upload"] is True
    assert m["meta"]["deck"]["job_id"] == job and rid not in json.dumps(m, ensure_ascii=False), "알림에 WDA 번호가 없다"
    again = c.post(f"/agent/deck/jobs/{job}/advance").json()
    assert again["notice"] == a["notice"] and len(_messages(box)) == 1, "두 번 불러도 알림은 하나"
    assert c.get(f"/agent/deck/jobs/{job}").json()["files"][0]["url"] == f"/agent/deck/jobs/{job}/files/pptx"


def test_advance_를_동시에_불러도_알림은_하나(box):
    job = _make(box).json()["job_id"]
    rid = _run_id(box)
    box["fake"].built(rid)
    box["fake"].rendered(rid)
    box["fake"].slow = 0.15
    with ThreadPoolExecutor(3) as ex:
        outs = list(ex.map(lambda _: box["c"].post(f"/agent/deck/jobs/{job}/advance").json(), range(3)))
    assert {o["state"] for o in outs} == {"done"} and len(_messages(box)) == 1


def test_알림을_덧붙인_뒤_기록이_실패해도_다시_오면_알림은_하나(box, monkeypatch):
    """적대 검토 R6 — 알림을 덧붙인 뒤 잡 기록(finished) 저장이 실패하면, 다음 advance 가 알림을 한 번 더 썼다(WD-D54)."""
    c, fake = box["c"], box["fake"]
    job = _make(box).json()["job_id"]
    rid = _run_id(box)
    fake.built(rid)
    fake.rendered(rid)
    real = W.save
    hit = {"n": 0}

    def flaky(settings, rec):
        if rec.get("finished") and not hit["n"]:
            hit["n"] = 1
            raise OSError(28, "No space left on device")
        return real(settings, rec)

    monkeypatch.setattr(W, "save", flaky)
    with pytest.raises(OSError):
        c.post(f"/agent/deck/jobs/{job}/advance")
    a = c.post(f"/agent/deck/jobs/{job}/advance")
    assert a.status_code == 200 and a.json()["state"] == "done"
    assert len(_messages(box)) == 1, "같은 잡의 알림은 하나"


def test_대화_저장소의_한_번만_덧붙이기(box):
    store = app.state.conv_store
    cid = box["conv"]["kim@corp.com"]
    for _ in range(3):
        assert store.append(conversation_id=cid, owner_sub="kim@corp.com", role="assistant", content="x", msg_id="deck-" + "b" * 32)
    assert store.append(conversation_id=cid, owner_sub="lee@corp.com", role="assistant", content="x", msg_id="deck-" + "c" * 32) is False
    assert [m["content"] for m in _messages(box)] == ["x"]


def test_렌더를_이어서_하지_않는_판이면_advance_가_한_번_맡긴다(box):
    box["fake"].chain = False
    job = _make(box).json()["job_id"]
    rid = _run_id(box)
    box["fake"].built(rid)
    st = box["c"].get(f"/agent/deck/jobs/{job}").json()
    assert (st["state"], st["next"]) == ("preparing", "render")
    a = box["c"].post(f"/agent/deck/jobs/{job}/advance").json()
    assert a["state"] == "rendering"
    box["c"].post(f"/agent/deck/jobs/{job}/advance")
    assert box["fake"].calls.count(("POST", f"/apps/web_design_agents/api/runs/{rid}/render")) == 1
    assert box["fake"].runs[rid]["render"]["requested"] == ["pptx", "pdf"]


def test_요청한_출력이_빠지면_알림에_이름과_까닭(box):
    job = _make(box, targets=["pptx", "pdf", "video"]).json()["job_id"]
    rid = _run_id(box)
    box["fake"].built(rid)
    box["fake"].rendered(rid, skip={"video": "이 장면 꼴은 영상을 내지 않는다"})
    a = box["c"].post(f"/agent/deck/jobs/{job}/advance").json()
    assert a["state"] == "done" and [f["kind"] for f in a["files"]] == ["pptx", "pdf"]
    assert "만들지 않은 것 — 영상(이 장면 꼴은 영상을 내지 않는다)" in a["notice"]["text"]


def test_실패와_WDA_가_모르는_실행은_실패_알림_한_건(box):
    job = _make(box).json()["job_id"]
    rid = _run_id(box)
    box["fake"].set_run(rid, status="failed")
    box["fake"].runs[rid]["stages"][2].update(status="failed", error="ValueError: 시나리오 검증 실패")
    st = box["c"].get(f"/agent/deck/jobs/{job}").json()
    assert (st["state"], st["step"], st["next"]) == ("failed", "장면 구성 에서 멈춤", "finish")
    assert st["error"] == "WDA 가 '장면 구성' 단계에서 실패했습니다."
    a = box["c"].post(f"/agent/deck/jobs/{job}/advance").json()
    assert "만들지 못했습니다" in a["notice"]["text"] and "'장면 구성' 단계에서 실패" in a["notice"]["text"]
    assert "ValueError" not in a["notice"]["text"]
    assert a["notice"]["activity"][0]["ok"] is False and len(_messages(box)) == 1
    job2 = _make(box, again=True).json()["job_id"]
    box["fake"].runs.clear()
    st = box["c"].get(f"/agent/deck/jobs/{job2}").json()
    assert st["state"] == "failed" and "모릅니다" in st["error"]


# ── 사람 · WDA 의 글이 알림 · LLM 근거에서 마크다운이 되지 않는다(적대 검토 R3 · R3b, WD-D49) ─────────────────────────
PAYLOAD = ("분기 실적」\n\n> [!WARNING] 보안 점검 중입니다 — 받기 전에 [포털 다시 로그인](https://evil.example/login) 하세요"
           " ![](https://evil.example/t.png?u=1)\n\n「")


def _md_tokens(text: str) -> list[str]:
    """알림 글에서 링크 · 그림이 될 자리 — 포털이 박은 받기 링크([PPT 받기](/agent/deck/…))만 있어야 한다."""
    import re
    return re.findall(r"!?\[[^\]\n]*\]\([^)\s]*\)", text)


def test_RA_제목은_알림에서_링크_그림_콜아웃이_되지_않는다(box):
    c, fake = box["c"], box["fake"]
    fake.reports[41] = {**IMPORT, "title": PAYLOAD}
    job = _make(box).json()["job_id"]
    rid = _run_id(box)
    fake.built(rid)
    fake.rendered(rid)
    c.post(f"/agent/deck/jobs/{job}/advance")
    (m,) = _messages(box)
    assert "\n" not in m["content"] and "evil.example/login)" not in m["content"]
    assert all(t.startswith("[") and "](/agent/deck/jobs/" in t for t in _md_tokens(m["content"])), _md_tokens(m["content"])
    full = json.loads(m["meta"]["activity"][0]["result_full"])
    assert "[" not in full["title"] and "](" not in full["title"] and "\n" not in full["title"], "LLM 이력의 근거에도 그대로 가지 않는다"


def test_WDA_의_실패_글은_경로_run_id_링크_없이_정해진_글로(box, caplog):
    c, fake = box["c"], box["fake"]
    job = _make(box).json()["job_id"]
    rid = _run_id(box)
    err = (f"FileNotFoundError: [Errno 2] No such file or directory: '/data/wda/pipeline/{rid}/scenario.json'"
           " ![](/agent/deck/jobs) [다시 시도](https://evil.example/r)")
    fake.set_run(rid, status="failed")
    fake.runs[rid]["stages"][2].update(status="failed", error=err)
    st = c.get(f"/agent/deck/jobs/{job}")
    assert rid not in st.text and "/data/wda" not in st.text and "evil.example" not in st.text, "브라우저에 WDA run_id · 경로가 없다(WD-D7)"
    with caplog.at_level("WARNING", logger="hwax.wda_deck"):
        c.post(f"/agent/deck/jobs/{job}/advance")
    (m,) = _messages(box)
    assert rid not in m["content"] and "evil.example" not in m["content"] and "FileNotFoundError" not in m["content"]
    assert _md_tokens(m["content"]) == []
    assert any("FileNotFoundError" in r.getMessage() for r in caplog.records), "까닭은 서버 로그에 남는다"


def test_렌더_실패_글도_정해진_글로(box):
    job = _make(box).json()["job_id"]
    rid = _run_id(box)
    box["fake"].built(rid)
    box["fake"].runs[rid]["render"].update(status="failed", error=f"RuntimeError: chromium 이 /data/wda/renders/{rid} 에서 죽었다")
    st = box["c"].get(f"/agent/deck/jobs/{job}")
    assert st.json()["error"] == "WDA 가 파일을 만들다 실패했습니다." and rid not in st.text
    a = box["c"].post(f"/agent/deck/jobs/{job}/advance").json()
    assert "RuntimeError" not in a["notice"]["text"] and rid not in a["notice"]["text"]


def test_뺀_출력의_까닭도_마크다운이_되지_않는다(box):
    job = _make(box, targets=["pptx", "video"]).json()["job_id"]
    rid = _run_id(box)
    box["fake"].built(rid)
    box["fake"].rendered(rid, skip={"video": "[여기](https://evil.example/x) 를 보라\n# 제목"})
    a = box["c"].post(f"/agent/deck/jobs/{job}/advance").json()
    assert "evil.example/x)" not in a["notice"]["text"] and "\n" not in a["notice"]["text"]
    assert all("](/agent/deck/jobs/" in t for t in _md_tokens(a["notice"]["text"]))


@pytest.mark.parametrize("raw", ["[a](https://e.x/y)", "![](/x.png)", "> [!NOTE] 콜아웃", "# 제목", "```\n코드", "a | b | c",
                                 "**굵게** _기울임_", "$x$", "\\(x\\)", "줄\n바꿈", "방향\u202e바꿈", "<b>꺾쇠</b>"])
def test_md_plain_은_마크다운_구문이_되는_글자를_전각으로(raw):
    out = W.md_plain(raw)
    for ch in "[]()!*_\\`#>|$~<\n\u202e":
        assert ch not in out, (raw, out)


@pytest.mark.parametrize("how", ["no_hub_account", "jwks_down", "wda_502"])
def test_WDA_에_묻지_못해도_6시간_그물은_끝을_적는다(box, how):
    """적대 검토(묻지 못한 잡이 영영) — 허브가 그 사람을 막거나(계정 · JWKS) WDA 가 답하지 않으면 6시간 그물이 걸리지 않아 줄이 잡을 영영 열어 뒀다(WD-D55)."""
    c, fake, s = box["c"], box["fake"], box["s"]
    job = _make(box).json()["job_id"]
    rec = W.load(s, job, "kim@corp.com")
    rec["created_at"] -= s.wda_deck_give_up_s + 3600
    W.save(s, rec)
    if how == "no_hub_account":
        fake.no_hub_account.add("kim@corp.com")
    elif how == "jwks_down":
        fake.jwks_down = True
    else:
        orig = fake.wda
        fake.wda = lambda req, path, email: httpx.Response(502) if path.startswith("/api/runs/") else orig(req, path, email)
    (j,) = c.get("/agent/deck/jobs").json()["jobs"]
    assert (j["state"], j["step"], j["next"]) == ("failed", "시간 초과", "finish")
    one = c.get(f"/agent/deck/jobs/{job}")
    assert one.status_code == 200 and one.json()["state"] == "failed"
    a = c.post(f"/agent/deck/jobs/{job}/advance")
    assert a.status_code == 200 and a.json()["state"] == "failed" and "6시간" in a.json()["notice"]["text"]
    assert len(_messages(box)) == 1
    (j,) = c.get("/agent/deck/jobs").json()["jobs"]
    assert j["next"] is None, "끝을 적었다 — 줄이 더 묻지 않는다"


# ── 주인 · 받기 ─────────────────────────────────────────────────────────────────────────────────
def _finished(box) -> str:
    job = _make(box, targets=["pptx", "pdf", "html"]).json()["job_id"]
    rid = _run_id(box)
    box["fake"].built(rid)
    box["fake"].rendered(rid)
    box["c"].post(f"/agent/deck/jobs/{job}/advance")
    return job


def test_남의_잡은_상태도_advance_도_파일도_숨기기도_없다(box):
    job = _finished(box)
    box["who"]["p"] = LEE
    c = box["c"]
    for r in (c.get(f"/agent/deck/jobs/{job}"), c.post(f"/agent/deck/jobs/{job}/advance"),
              c.get(f"/agent/deck/jobs/{job}/files/pptx"), c.post(f"/agent/deck/jobs/{job}/dismiss")):
        assert r.status_code == 404, r.text
    assert c.get("/agent/deck/jobs").json()["jobs"] == []
    assert c.get("/agent/deck/jobs/../../etc").status_code == 404


def test_파일은_주인에게만_흘리고_머리를_단다(box):
    job = _finished(box)
    c = box["c"]
    r = c.get(f"/agent/deck/jobs/{job}/files/pptx")
    assert r.status_code == 200 and r.content == box["fake"].files["pptx"]
    cd = r.headers["content-disposition"]
    assert cd.startswith("attachment;") and "filename*=UTF-8''%EC%84%A4%EA%B3%84%20%EA%B2%80%ED%86%A0.pptx" in cd
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["cache-control"] == "private, no-store"
    assert r.headers["content-type"].startswith("application/vnd.openxmlformats-officedocument.presentationml")
    assert "content-security-policy" not in r.headers
    h = c.get(f"/agent/deck/jobs/{job}/files/html")
    assert h.status_code == 200 and h.headers["content-security-policy"] == "sandbox" and h.headers["content-disposition"].startswith("attachment;")
    assert c.get(f"/agent/deck/jobs/{job}/files/docx").status_code == 404, "만들지 않은 파일"
    assert c.get(f"/agent/deck/jobs/{job}/files/exe").status_code == 404
    box["fake"].runs.clear()
    gone = c.get(f"/agent/deck/jobs/{job}/files/pdf")
    assert gone.status_code == 404 and "지워졌습니다" in gone.json()["detail"]


def test_받기가_실패하면_몸을_상한까지만_읽는다(box):
    job = _finished(box)
    box["fake"].download_fails_big = True
    box["fake"].chunks_sent = 0
    r = box["c"].get(f"/agent/deck/jobs/{job}/files/pptx")
    assert r.status_code == 503 and "HTTP 500" in r.json()["detail"]
    assert box["fake"].chunks_sent <= 3, f"거절 응답의 몸을 다 읽지 않는다(보낸 덩어리 {box['fake'].chunks_sent}/64)"


# ── 한 번만 · 상한 · 목록 ───────────────────────────────────────────────────────────────────────────
def test_같은_보고서_같은_옵션은_하나로_again_은_새로(box):
    a = _make(box).json()
    b = _make(box).json()
    assert b["job_id"] == a["job_id"] and b["created"] is False and len(box["fake"].created) == 1
    other = _make(box, doc_style="brief").json()
    assert other["job_id"] != a["job_id"]
    rid = next(k for k, v in box["fake"].runs.items() if v["render_opts"]["doc_style"] == "report")
    box["fake"].built(rid)
    box["fake"].rendered(rid)
    box["c"].post(f"/agent/deck/jobs/{a['job_id']}/advance")
    assert _make(box).json()["job_id"] == a["job_id"], "끝난 같은 잡은 그것을 준다"
    assert _make(box, again=True).json()["created"] is True


# ── 만들기의 잠금은 기록만 — RA · WDA 왕복은 잠금 밖, 자리는 예약으로(적대 검토 R2, WD-D56) ───────────────────────────────
def _by_header(box):
    from fastapi import Request
    users = {"kim": KIM, "lee": LEE}

    def who(request: Request) -> Principal:
        return users[request.headers.get("x-u", "kim")]

    app.dependency_overrides[principal_pat_or_session] = who


def test_한_사람의_느린_RA_읽기가_다른_사람의_만들기를_세우지_않는다(box):
    c, fake = box["c"], box["fake"]
    _by_header(box)
    c.get("/agent/deck/status", headers={"x-u": "kim"})
    fake.ra_delay["rat_kim"] = 2.5
    kim = {"report_id": 41, "conversation_id": box["conv"]["kim@corp.com"]}
    lee = {"report_id": 41, "conversation_id": box["conv"]["lee@corp.com"]}

    def lee_after():
        time.sleep(0.5)
        t = time.monotonic()
        r = c.post("/agent/deck/jobs", json=lee, headers={"x-u": "lee"})
        return r.status_code, time.monotonic() - t

    with ThreadPoolExecutor(2) as ex:
        fk = ex.submit(lambda: c.post("/agent/deck/jobs", json=kim, headers={"x-u": "kim"}).status_code)
        fl = ex.submit(lee_after)
        code, waited = fl.result()
        assert fk.result() == 200
    assert code == 200 and waited < 1.5, f"이의 만들기가 김의 RA 읽기를 기다렸다({waited:.2f}초)"


def test_예약은_RA_를_읽는_동안에도_상한에_세고_실패하면_놓는다(box):
    c, fake, s = box["c"], box["fake"], box["s"]
    s.wda_deck_inflight_max = 1
    c.get("/agent/deck/status")
    fake.ra_delay["rat_kim"] = 1.5

    def second():
        time.sleep(0.4)
        return _make(box, doc_style="memo")

    with ThreadPoolExecutor(2) as ex:
        first = ex.submit(lambda: _make(box))
        r2 = ex.submit(second).result()
        assert first.result().status_code == 200
    assert r2.status_code == 429, "첫 잡이 아직 RA 를 읽는 동안에도 자리를 센다"
    fake.ra_delay.clear()
    for rec in W.records(s):
        rec["finished"] = {"state": "done", "files": [], "skipped": []}
        W.save(s, rec)
    assert _make(box, report_id=999).status_code == 404
    assert [r for r in W.records(s) if not r.get("finished")] == [], "실패한 만들기는 예약을 놓는다"
    assert _make(box, doc_style="brief").status_code == 200, "놓은 자리는 다음 만들기가 쓴다"


def test_허브_토큰은_쓰기_바로_앞에서_새로_찍는다(box):
    """RA 읽기(길 수 있다)를 사이에 두고 탐침 때 찍은 토큰을 들고 있다가 WDA 만들기에 쓰지 않는다(WD-D56 · D47)."""
    fake = box["fake"]
    assert _make(box).status_code == 200
    jtis = {path: jti for _, path, jti in fake.pat_calls}
    assert jtis["/api/health"] != jtis["/api/runs"]


def test_끊긴_예약은_상한에_세지_않고_실패로_보인다(box):
    c, s = box["c"], box["s"]
    s.wda_deck_inflight_max = 1
    stale = {"job_id": "e" * 32, "owner_sub": "kim@corp.com", "owner_email": "kim@corp.com", "conversation_id": box["conv"]["kim@corp.com"],
             "report": {"id": 43, "title": ""}, "options": {"targets": ["pptx"], "doc_style": "report", "pptx_mode": "hybrid"},
             "wda": {"run_id": None}, "state": "queued", "created_at": time.time() - W.RESERVE_TTL_S - 1, "render_submitted_at": None,
             "images_not_sent": 0, "finished": None, "dismissed": None}
    W.save(s, stale)
    fresh = {**stale, "job_id": "d" * 32, "created_at": time.time()}
    W.save(s, fresh)
    listed = {j["job_id"]: (j["state"], j["step"]) for j in c.get("/agent/deck/jobs").json()["jobs"]}
    assert listed == {stale["job_id"]: ("failed", "맡기다 끊김"), fresh["job_id"]: ("queued", "맡기는 중")}, "예약은 WDA 에 묻지 않는다"
    assert c.post(f"/agent/deck/jobs/{fresh['job_id']}/advance").json()["step"] == "맡기는 중"
    j = c.get(f"/agent/deck/jobs/{stale['job_id']}").json()
    assert (j["state"], j["step"]) == ("failed", "맡기다 끊김")
    W._path(s, fresh["job_id"]).unlink()
    assert _make(box).status_code == 200, "끊긴 예약은 자리를 먹지 않는다"


# ── 아무도 advance 하지 않는 잡이 자리를 먹지 않는다(적대 검토 R1, WD-D59) ─────────────────────────────────────────────────
def test_숨기거나_버려진_잡이_WDA_에서_끝났으면_만들기_앞에서_끝을_적고_자리를_놓는다(box):
    c, fake, s = box["c"], box["fake"], box["s"]
    fake.reports[43] = {**IMPORT, "id": 43, "title": "다른 보고서"}
    a = _make(box).json()["job_id"]
    b = _make(box, doc_style="memo").json()["job_id"]
    for rid in list(fake.runs):            # WDA 는 둘 다 몇 초 만에 끝냈다
        fake.built(rid)
        fake.rendered(rid)
    for j in (a, b):                       # 입력창 위 줄의 '숨기기' — 그 뒤 아무도 advance 하지 않는다(창을 닫았다)
        assert c.post(f"/agent/deck/jobs/{j}/dismiss").status_code == 200
    r = _make(box, report_id=43)
    assert r.status_code == 200, r.text
    assert len(_messages(box)) == 2, "끝난 두 잡의 알림이 남았다(숨겨도 알림은 남긴다)"
    # 박스 전체 — 이도 둘을 맡기고 떠났다(PAT 스크립트 · 닫은 창). 셋째 사람의 만들기가 그 둘을 이의 이름으로 정리한다
    box["who"]["p"] = LEE
    la = _make(box).json()["job_id"]
    lb = _make(box, doc_style="memo").json()["job_id"]
    for rid, run in list(fake.runs.items()):
        if run["status"] != "done":
            fake.built(rid)
            fake.rendered(rid)
    app.state.user_store.set_connection(email="park@corp.com", service="reportarchive", token="rat_lee")
    s.wda_deck_inflight_box_max = 3
    park = Principal(subject="park@corp.com", email="park@corp.com", display_name="박", groups=NEEDS)
    box["who"]["p"] = park
    pconv = c.post("/agent/conversations", json={"title": "t", "kind": "chat"}).json()["id"]
    n0 = len(fake.pat_calls)
    r = c.post("/agent/deck/jobs", json={"report_id": 41, "conversation_id": pconv})
    assert r.status_code == 200, r.text
    lee_runs = {W.load(s, j, "lee@corp.com")["wda"]["run_id"] for j in (la, lb)}
    asked = {(path.rsplit("/", 1)[-1], next(p["email"] for p in fake.pats if p["jti"] == jti))
             for m, path, jti in fake.pat_calls[n0:] if m == "GET" and path.startswith("/api/runs/") and path.count("/") == 3}
    assert {(rid, "lee@corp.com") for rid in lee_runs} <= asked, "남의 잡은 그 주인의 이름으로 묻는다(WDA 의 주인 검사를 지난다)"
    assert all(W.load(s, j, "lee@corp.com")["finished"]["state"] == "done" for j in (la, lb))
    assert len(_messages(box, LEE)) == 2, "이의 대화에 이의 알림이 남는다"


def test_사람당_박스_전체_동시_상한(box):
    box["s"].wda_deck_inflight_max = 1
    assert _make(box).status_code == 200
    r = _make(box, doc_style="memo")
    assert r.status_code == 429 and "1건" in r.json()["detail"]
    box["s"].wda_deck_inflight_max = 5
    box["s"].wda_deck_inflight_box_max = 2
    box["who"]["p"] = LEE
    assert _make(box).status_code == 200
    r = _make(box, doc_style="memo")
    assert r.status_code == 429 and "많습니다" in r.json()["detail"]
    for rec in W.records(box["s"]):                        # 6시간이 지난 끊긴 잡은 상한을 먹지 않는다
        rec["created_at"] -= box["s"].wda_deck_give_up_s + 1
        W.save(box["s"], rec)
    assert _make(box, doc_style="memo").status_code == 200


def test_내_목록은_끝나지_않은_잡의_지금_상태와_숨기기(box):
    job = _make(box).json()["job_id"]
    box["fake"].stage(_run_id(box), "build")
    (j,) = box["c"].get("/agent/deck/jobs").json()["jobs"]
    assert (j["job_id"], j["state"], j["step"]) == (job, "preparing", "화면 굽기")
    box["fake"].reject_all = True                            # WDA 를 못 묻는 동안에도 목록이 그 잡을 잃지 않는다(줄이 다시 묻기를 멈추지 않게)
    (j,) = box["c"].get("/agent/deck/jobs").json()["jobs"]
    assert (j["job_id"], j["state"], j["next"]) == (job, "preparing", None) and "묻지 못했습니다" in j["step"]
    box["fake"].reject_all = False
    assert box["c"].post(f"/agent/deck/jobs/{job}/dismiss").json() == {"job_id": job, "dismissed": True}
    (j,) = box["c"].get("/agent/deck/jobs").json()["jobs"]
    assert j["dismissed"] is True, "숨긴 잡도 끝나지 않았으면 싣는다 — 줄이 계속 한 걸음씩(화면에는 숨긴다, WD-D59)"
    box["fake"].built(_run_id(box))
    box["fake"].rendered(_run_id(box))
    assert box["c"].post(f"/agent/deck/jobs/{job}/advance").json()["noticed"] is True, "숨긴 잡도 끝 알림을 남긴다"
    assert box["c"].get("/agent/deck/jobs").json()["jobs"] == [], "숨겼고 끝난 잡은 목록에서 빠진다"


def test_없는_잡이나_남의_잡을_숨겨도_잠금이_쌓이지_않는다(box):
    job = _make(box).json()["job_id"]
    n = len(W._LOCKS)
    for jid in [uuid.uuid4().hex for _ in range(5)] + ["../x", "z" * 32]:
        assert box["c"].post(f"/agent/deck/jobs/{jid}/dismiss").status_code == 404
    box["who"]["p"] = LEE
    assert box["c"].post(f"/agent/deck/jobs/{job}/dismiss").status_code == 404
    assert len(W._LOCKS) == n, "꼴이 틀리거나 없거나 남의 잡이면 잠금을 만들지 않는다"


def test_쓴_잠금은_남지_않는다(box):
    """잡 id 마다 만든 잠금이 메모리에 쌓였다(적대 검토, WD-D60) — 쓰고 나면 지운다."""
    job = _finished(box)
    box["c"].post(f"/agent/deck/jobs/{job}/advance")
    box["c"].post(f"/agent/deck/jobs/{job}/dismiss")
    box["c"].get("/agent/deck/jobs")
    assert W._LOCKS == {}


def test_잡_기록은_스테이징_청소에서_빠지고_기한_뒤에_지운다(box):
    from app.agent.upload import sweep_expired
    s = box["s"]
    job = _make(box).json()["job_id"]
    p = W._path(s, job)
    old = time.time() - s.upload_staging_ttl_hours * 3600 - 60
    os.utime(p, (old, old))
    sweep_expired(s)
    assert p.exists(), "6시간 청소는 발표자료 기록을 지우지 않는다"
    gone = time.time() - s.wda_deck_job_days * 86400 - 60
    os.utime(p, (gone, gone))
    sweep_expired(s)
    assert not p.exists()


def test_감사에는_보고서_본문이_없다(box):
    job = _finished(box)
    box["c"].get(f"/agent/deck/jobs/{job}/files/pptx")
    rows = app.state.agent_audit._conn.execute(
        "SELECT event, status, meta FROM agent_audit WHERE event LIKE 'deck_%' ORDER BY rowid DESC LIMIT 10").fetchall()
    events = {r[0] for r in rows}
    assert {"deck_create", "deck_finish", "deck_download"} <= events
    assert all("두께 12um" not in (r[2] or "") for r in rows)


# ── 상태 접기(순수) ─────────────────────────────────────────────────────────────────────────────
def _rec(created=None, targets=("pptx", "pdf"), **kw):
    return {"job_id": "a" * 32, "created_at": time.time() if created is None else created,
            "options": {"targets": list(targets), "doc_style": "report"}, **kw}


def _run(status, stage=None, render=None):
    stages = []
    for s in ("ingest", "fragmentize", "scenario", "build"):
        stages.append({"stage": s, "status": "running" if s == stage else "pending"})
    return {"status": status, "stages": stages, "render": render}


@pytest.mark.parametrize("run,want", [
    (_run("queued"), ("queued", "줄 서는 중", 0, None)),
    (_run("running", "ingest"), ("preparing", "보고서 읽기", 10, None)),
    (_run("running", "fragmentize"), ("preparing", "조각 나누기", 25, None)),
    (_run("running", "build"), ("preparing", "화면 굽기", 55, None)),
    (_run("done"), ("preparing", "렌더 맡기기", 60, "render")),
    (_run("done", render={"status": "queued"}), ("rendering", "차례 기다림", 65, None)),
    (_run("done", render={"status": "building"}), ("rendering", "준비", 70, None)),
    (_run("done", render={"status": "rendering"}), ("rendering", "만드는 중", 80, None)),
    (_run("done", render={"status": "done", "outputs": {"pptx": "x"}}), ("done", "끝", 100, "finish")),
    (_run("done", render={"status": "failed", "error": "chromium 죽음"}), ("failed", "파일 만들기에서 멈춤", 0, "finish")),
    (None, ("failed", "WDA 가 이 실행을 모릅니다(지웠거나 다른 박스)", 0, "finish")),
])
def test_상태_낱말_하나로_접는다(run, want):
    f = W.fold(run, rec=_rec(), now=time.time(), settings=Settings(_env_file=None))
    assert (f["state"], f["step"], f["progress"], f["next"]) == want


def test_렌더를_맡긴_뒤에는_다시_맡기지_않는다():
    f = W.fold(_run("done"), rec=_rec(render_submitted_at=time.time()), now=time.time(), settings=Settings(_env_file=None))
    assert (f["state"], f["next"]) == ("rendering", None)


def test_늦음과_시간_초과():
    s = Settings(_env_file=None)
    now = time.time()
    assert W.fold(_run("running", "scenario"), rec=_rec(now - s.wda_deck_late_prepare_s - 1), now=now, settings=s)["late"] is True
    assert W.fold(_run("running", "scenario"), rec=_rec(now - 10), now=now, settings=s)["late"] is False
    rend = _run("done", render={"status": "rendering"})
    assert W.fold(rend, rec=_rec(now - s.wda_deck_late_render_s - 1), now=now, settings=s)["late"] is True
    assert W.fold(rend, rec=_rec(now - s.wda_deck_late_render_s - 1, targets=("pptx", "video")), now=now, settings=s)["late"] is False
    out = W.fold(rend, rec=_rec(now - s.wda_deck_give_up_s - 1), now=now, settings=s)
    assert out["state"] == "failed" and out["next"] == "finish" and "6시간" in out["error"]
    done = W.fold(rend, rec=_rec(now, finished={"state": "done"}), now=now, settings=s)
    assert done["next"] is None


def test_허브_PAT_은_짧고_청중은_허브_하나():
    from app.auth.keystore import KeyStore
    s = Settings(_env_file=None)
    ks = KeyStore(s)
    tok = W.hub_pat(ks, s, KIM)
    claims = jwt.decode(tok, ks.public_pem(ks.active_kid), algorithms=["RS256"], audience="heax-hub")
    assert claims["aud"] == ["heax-hub"] and claims["scope"] == "api" and claims["exp"] - claims["iat"] == 600
    assert claims["jti"] != jwt.decode(W.hub_pat(ks, s, KIM), ks.public_pem(ks.active_kid), algorithms=["RS256"], audience="heax-hub")["jti"]
    assert "plat:webdesign" not in claims["groups"], "권한 키는 허브에 싣지 않는다(로그인 그룹만)"


def test_WDA_주소는_설정이_이기고_없으면_routes_env_의_apps():
    class Cat:
        def route(self, key):
            return {"apps": "http://localhost:4180/apps/"}.get(key)
    s = Settings(_env_file=None)
    assert W.wda_base(s, Cat()) == "http://localhost:4180/apps/web_design_agents"
    s.wda_base_url = "http://h/apps/web_design_agents/"
    assert W.wda_base(s, Cat()) == "http://h/apps/web_design_agents"
    s.wda_base_url = ""
    assert W.wda_base(s, None) == ""
