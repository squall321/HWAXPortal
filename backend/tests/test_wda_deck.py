# 발표자료로 — 그 사람 명의 RA 읽기 · 허브 Caddy 경유 WDA · 주인만 · 한 번만 알림 · 상태 낱말 하나 · 받기 중계(docs/wda-deck)
"""가짜 RA 와 가짜 '허브 게이트 + WDA'(httpx MockTransport)로 포털 창구를 끝에서 끝까지 본다.

가짜 WDA 는 **요청서(docs/wda-deck/wda-request.md)의 계약**을 그대로 따른다 — WDA 에는 아직 없다(11-01 답 Q1). 봉투 {success, data, message, code} ·
상태 낱말(파이프라인 queued/running/done/failed · 단계 pending/running/done/failed · 렌더 queued/rendering/done/failed) · 남과 신원 없음에 404 ·
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

    def __init__(self, keystore, *, features=("owner",), chain=True):
        self.keystore, self.features, self.chain = keystore, set(features), chain
        # WDA 의 꼴 등록부(꼴 id → 상태) — features 에 format:<id> 가 저절로 실린다. 심의 꼴(delib-16x9)은 시험이 넣는다
        self.formats = {"wide-16x9": "active", "short-9x16": "active", "print-a4": "draft"}
        self.version = "0.1.0"                         # 패키지 판(허브 매니페스트 판과 같다 — WDA 11-01)
        self.runs: dict[str, dict] = {}
        self.reports = {41: IMPORT, 42: EMPTY, 58: DELIB}
        self.calls: list[tuple[str, str]] = []          # (메서드, 경로)
        self.created: list[dict] = []                  # 받은 만들기 본문
        self.client_identity: list[str] = []           # 클라이언트가 보낸 X-Heax-User-Email(있으면 안 된다)
        self.pats: list[dict] = []
        self.ra_auth: list[str] = []
        self.no_hub_account: set[str] = set()
        self.reject_all = False                        # 허브 게이트가 모든 자격을 거절한다(portal_auth 앱의 익명 · 깨진 토큰 — HEAXHub 385783f)
        self.health_down = False
        self.slow = 0.0
        self.max_bytes = 16 * 1024 * 1024
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
        body = {"success": status < 400, "data": data, "message": message}
        if code:
            body["code"] = code
        return httpx.Response(status, json=body)

    async def handler(self, req: httpx.Request) -> httpx.Response:
        if self.slow:
            await asyncio.sleep(self.slow)
        if req.url.host == "ra.test":
            return self.ra(req)
        assert req.url.host == "hub.test", req.url
        self.calls.append((req.method, req.url.path))
        if "x-heax-user-email" in req.headers:
            self.client_identity.append(req.headers["x-heax-user-email"])
        auth = req.headers.get("authorization", "")
        if self.reject_all or not auth.startswith("Bearer "):
            return httpx.Response(401, json={"detail": "로그인이 필요하다"})   # portal_auth: true — 익명은 health 까지 401
        try:
            claims = jwt.decode(auth[7:], self.keystore.public_pem(self.keystore.active_kid), algorithms=["RS256"], audience="heax-hub",
                                options={"require": ["exp", "jti", "sub"]})
        except jwt.PyJWTError:
            return httpx.Response(401, json={"detail": "포털 토큰이 거절됐다"})
        assert claims["scope"] == "api"
        self.pats.append(claims)
        email = str(claims.get("email") or "").lower()
        if email in self.no_hub_account:
            return httpx.Response(403, json={"detail": "허브 계정이 없다 — 포털에서 HEAX Hub 타일을 한 번 눌러 허브에 로그인한 뒤 다시 시도한다"})
        path = req.url.path.removeprefix("/apps/web_design_agents")
        return self.wda(req, path, email)

    def ra(self, req: httpx.Request) -> httpx.Response:
        self.ra_auth.append(req.headers.get("authorization", ""))
        rid = int(req.url.path.rsplit("/", 1)[1])
        if req.headers.get("authorization") not in ("Bearer rat_kim", "Bearer rat_lee"):
            return httpx.Response(401, json={"detail": "unauthorized"})
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
            if len(req.content) > self.max_bytes:
                return self.env(413, message="본문이 크다", code="TOO_LARGE")
            body = json.loads(req.content)
            self.created.append(body)
            fmt = body.get("format", "wide-16x9")
            if fmt not in self.formats:
                return self.env(400, message=f"모르는 format '{fmt}' — 쓸 수 있는 꼴: {', '.join(sorted(self.formats))}", code="INVALID")
            n, t = self._text_blocks(body["report_json"], fmt)
            if not t:
                return self.env(422, message=f"ValueError: 텍스트를 가진 블록이 없다 (블록 {n}개, 텍스트 0개)", code="INVALID")
            rid = f"wr-{uuid.uuid4().hex}"
            self.runs[rid] = {"run_id": rid, "owner": email, "status": "queued", "error": None, "render": None,
                              "format": fmt, "render_opts": body.get("render"),
                              "stages": [{"stage": s, "status": "pending", "error": None} for s in ("ingest", "fragmentize", "scenario", "build")]}
            return self.env(202, {"run_id": rid, "slug": body["slug"], "owner": email})
        parts = path.split("/")          # ['', 'api', 'runs', id, ...]
        if len(parts) >= 4 and parts[1:3] == ["api", "runs"]:
            run = self._mine(parts[3], email)
            if run is None:
                return self.env(404, message="실행을 찾을 수 없습니다", code="NOT_FOUND")
            rest = parts[4:]
            if not rest and req.method == "GET":
                return self.env(200, {k: v for k, v in run.items() if k != "render_opts"})
            if rest == ["render"] and req.method == "POST":
                if run["status"] != "done":
                    return self.env(409, message="빌드 전", code="NOT_BUILT")
                if run["render"] and run["render"]["status"] in ("queued", "rendering"):
                    return self.env(409, message="이미 렌더 중", code="BUSY")
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
                k = rest[1]
                outs = {{"video": "mp4"}.get(t, t) for t in ((run["render"] or {}).get("outputs") or {})}
                if k not in outs:
                    return self.env(404, message="산출물이 아직 없습니다", code="NOT_FOUND")
                return httpx.Response(200, content=self.files[k], headers={"content-type": "application/octet-stream",
                                                                          "content-disposition": f'attachment; filename="{parts[3]}-{k}"'})
        return self.env(404, message="경로 없음", code="NOT_FOUND")


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


def test_글이_없는_보고서는_WDA_의_까닭을_그대로_보이고_잡을_남기지_않는다(box):
    r = _make(box, report_id=42)
    assert r.status_code == 502 and "텍스트를 가진 블록이 없다 (블록 2개, 텍스트 0개)" in r.json()["detail"]
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
    """탐침(60초 붙잡음) 뒤 WDA 가 그 꼴을 잃었다(옛 판으로 되돌림) — 만들기가 곧바로 400 INVALID(쓸 수 있는 꼴을 message 에)."""
    fake = box["fake"]
    fake.formats["delib-16x9"] = "active"
    assert box["c"].get("/agent/deck/status").json()["formats"] == {"deliberation": True}
    del fake.formats["delib-16x9"]
    r = _make(box, report_id=58)
    detail = r.json()["detail"]
    assert r.status_code == 502 and "(HTTP 400 · INVALID)" in detail and "쓸 수 있는 꼴: print-a4, short-9x16, wide-16x9" in detail
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


def test_RA_가_거절하거나_없거나_보고서가_크면_WDA_를_부르지_않는다(box):
    assert _make(box, report_id=403).status_code == 403
    assert _make(box, report_id=999).status_code == 404
    box["s"].wda_deck_report_max_mb = 0
    r = _make(box)
    assert r.status_code == 413 and "MB" in r.json()["detail"]
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
    assert r.status_code == 403 and "허브 계정이 없다" in r.json()["detail"]
    assert r.json()["detail"].startswith("허브가 만들기 요청을 막았습니다(HTTP 403)")


def test_허브가_탐침을_401_로_막으면_모름으로_숨기고_붙잡지_않는다(box):
    """portal_auth: true(HEAXHub 385783f)부터 익명은 /api/health 도 401 이다 — 탐침은 그 사람의 PAT 를 싣고, 막히면 '모름' 으로 숨긴다(오류 되풀이 없음)."""
    box["fake"].reject_all = True
    st = box["c"].get("/agent/deck/status")
    assert st.status_code == 200 and st.json()["enabled"] is False and st.json()["reason"] == "unknown"
    assert _make(box).status_code == 503 and box["fake"].created == []
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
    a = box["c"].post(f"/agent/deck/jobs/{job}/advance").json()
    assert "만들지 못했습니다" in a["notice"]["text"] and "시나리오 검증 실패" in a["notice"]["text"]
    assert a["notice"]["activity"][0]["ok"] is False and len(_messages(box)) == 1
    job2 = _make(box, again=True).json()["job_id"]
    box["fake"].runs.clear()
    st = box["c"].get(f"/agent/deck/jobs/{job2}").json()
    assert st["state"] == "failed" and "모릅니다" in st["error"]


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
    assert box["c"].get("/agent/deck/jobs").json()["jobs"] == []


def test_없는_잡이나_남의_잡을_숨겨도_잠금이_쌓이지_않는다(box):
    job = _make(box).json()["job_id"]
    n = len(W._LOCKS)
    for jid in [uuid.uuid4().hex for _ in range(5)] + ["../x", "z" * 32]:
        assert box["c"].post(f"/agent/deck/jobs/{jid}/dismiss").status_code == 404
    box["who"]["p"] = LEE
    assert box["c"].post(f"/agent/deck/jobs/{job}/dismiss").status_code == 404
    assert len(W._LOCKS) == n, "꼴이 틀리거나 없거나 남의 잡이면 잠금을 만들지 않는다"


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
