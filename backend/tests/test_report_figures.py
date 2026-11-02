# 도구 그림을 그 사람 명의로 RA 보고서에 — 게이트웨이 계약 /agent/figures/to-report · 에이전트 서버용 /agent/figures/upload(docs/report-figures RF-1 ~ RF-8)
"""가짜 RA(httpx MockTransport — report_figures._TRANSPORT) + 진짜 포털 앱(TestClient)으로 끝에서 끝까지 본다. RA 의 요청 · 답 꼴은 ReportArchive
참고 원본(files/routes.py upload_file · reports/routes.py report_outline · update_ai_draft · shared/responses.py)에서 읽은 그대로다.
고정하는 것.
  · 그 사람의 RA 토큰으로만 부른다(서비스 계정 없음) — outline → /api/files → ai-draft PATCH, 그림 칸은 RA image 위젯 꼴(fig_<sha 16> · files[0]).
  · page 가 없으면 마지막 쪽, 넘는 쪽은 400 이고 올리지도 않는다.
  · 자격 — 진짜 의존성(principal_pat_or_session)으로 401 · 세션은 CSRF · 읽기 전용 PAT 403(게이트웨이 · 루틴 창구와 같은 판정) · 챗 PAT 는 쓴다 ·
    plat:reportarchive 없으면 403.
  · 꼴 — SVG 415(까닭) · 내용이 그림이 아니면 415 · 선언과 내용이 다르면 내용의 꼴로. 크기 413(길이 머리 · 읽기 둘 다) · 길이 머리 없으면 411.
    sha256 이 다르면 400.
  · RA 오류는 맞는 상태로(RF-8 표), RA 가 칸을 경고로 버리면 502, 같은 그림을 다시 넣으면 칸을 갈아 끼운다, 같은 보고서에 동시에 넣어도 칸이
    사라지지 않는다(보고서 잠금).
"""
import asyncio
import hashlib
import importlib.util
import json
import re
import secrets
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import jwt
import pytest
from fastapi.testclient import TestClient

from app.agent import report_figures as F
from app.agent import routes as R
from app.auth import ra_sso
from app.auth.cookies import CSRF_COOKIE, SESSION_COOKIE
from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.config import Settings, get_settings
from app.deps import principal_pat_or_session
from app.main import app

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 200
SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
KIM = Principal(subject="kim@corp.com", email="kim@corp.com", display_name="김철수", groups=["plat:reportarchive"])
_AGENT_RF = Path(__file__).resolve().parents[2].parent / "HWAXAgentServer" / "report_figures.py"


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


class _RA:
    """가짜 RA — 보고서 한 건(쪽마다 blocks_order). ai-draft PATCH 는 진짜처럼 읽고 · 합치고 · 쓴다(같은 id 는 교체, 새 id 는 끝에).
    dry_run PATCH 는 가드(권한 · 발행 · 편집 잠금)만 보고 바꾸지 않는다(RA _apply_ai_draft 와 같다). status 로 단계의 답을 바꾼다 —
    outline · files · patch(가드 — dry_run 과 진짜 PATCH 둘 다) · patch_real(진짜 PATCH 만 — 가드를 지난 뒤의 검증 거절). delay 는 PATCH 의
    읽기와 쓰기 사이를 벌린다(동시 호출 시험)."""

    def __init__(self, pages: int = 2, *, status: dict | None = None, drop: bool = False, delay: float = 0.0, rid: int = 41):
        self.rid, self.status, self.drop, self.delay = rid, status or {}, drop, delay
        self.pages = [{"blocks_order": ["background", "results"], "content": {}} for _ in range(pages)]
        self.calls: list[httpx.Request] = []
        self.files: list[dict] = []

    def _st(self, step: str, ok: int) -> int:
        return self.status.get(step, ok)

    async def __call__(self, req: httpx.Request) -> httpx.Response:
        self.calls.append(req)
        path = req.url.path
        if path == f"/api/reports/{self.rid}/outline" and req.method == "GET":
            st = self._st("outline", 200)
            if st >= 400:
                return httpx.Response(st, json={"success": False, "message": f"outline {st}"})
            return httpx.Response(200, json={"success": True, "data": {
                "report_id": self.rid, "title": "심의", "phase": "drafting", "page_count": len(self.pages),
                "pages": [{"page": i + 1, "blocks": [{"block_id": b} for b in p["blocks_order"]]} for i, p in enumerate(self.pages)],
                "issues": [], "mounted_to": []}})
        if path == "/api/files" and req.method == "POST":
            st = self._st("files", 201)
            if st >= 400:
                return httpx.Response(st, json={"success": False, "message": f"files {st}"})
            body = req.content
            head = body.split(b"\r\n\r\n", 1)[0].decode("utf-8", "replace")
            self.files.append({"filename": re.search(r'filename="([^"]*)"', head).group(1),
                               "mime": re.search(r"Content-Type: (\S+)", head).group(1),
                               "auth": req.headers.get("authorization")})
            return httpx.Response(201, json={"success": True, "message": "Created successfully",
                                             "data": {"id": f"f{len(self.files)}", "filename": "x", "mime_type": "image/png",
                                                      "size": 1, "is_image": True, "owner_user_id": 5, "workspace_slug": "personal-5",
                                                      "uploaded_at": "2026-11-02T00:00:00Z"}})
        if path == f"/api/reports/{self.rid}/ai-draft" and req.method == "PATCH":
            body = json.loads(req.content)
            st = self._st("patch", 200) if body.get("dry_run") else self._st("patch_real", self._st("patch", 200))
            if st >= 400:
                return httpx.Response(st, json={"success": False, "message": f"patch {st}"})
            if body.get("dry_run"):
                return httpx.Response(200, json={"success": True, "data": {"dry_run": True, "report_id": self.rid, "title": "심의",
                                                                         "page_diff": [], "metadata_changes": {}, "warnings": [],
                                                                         "mounted_to": [], "note": "적용하지 않았습니다."}})
            p = self.pages[body["page"] - 1]
            order = list(p["blocks_order"])                   # 읽기
            await asyncio.sleep(self.delay)
            warnings = []
            for b in body.get("extra_blocks") or []:
                if self.drop:
                    warnings.append(f"extra block '{b['id']}'(image): 내용 없음/형식 불일치 — 건너뜀")
                    continue
                if b["id"] not in order:
                    order.append(b["id"])
                p["content"][b["id"]] = b["content"]
            p["blocks_order"] = order                         # 쓰기
            return httpx.Response(200, json={"success": True, "data": {
                "report": {"id": self.rid, "pages": [{"template_id": "deliberation", "template_version": 1,
                                                      "blocks_order": q["blocks_order"], "content": q["content"]} for q in self.pages]},
                "warnings": warnings, "url": f"/w/personal-5/reports/{self.rid}", "mounted_to": []}})
        raise AssertionError(f"가짜 RA 가 모르는 요청 — {req.method} {path}")

    def paths(self) -> list[str]:
        return [f"{r.method} {r.url.path}" for r in self.calls]


def _settings(**kw) -> Settings:
    kw.setdefault("ra_base_url", "http://ra.test")
    kw.setdefault("ra_sso_secret", "")
    return Settings(_env_file=None, **kw)


class _Audit:
    def __init__(self):
        self.rows = []

    def record(self, **kw):
        self.rows.append(kw)


@pytest.fixture()
def portal(monkeypatch):
    """진짜 포털 앱 — 설정 · 감사 · RA 토큰 함수 · RA 전송을 바꿔 끼운다. principal 은 기본 KIM(시험이 바꿔 끼우거나 진짜 의존성으로 돌린다)."""
    s = _settings()
    ra = _RA()
    tok = {"value": ("rat_kim", False, {"workspace": ""})}

    async def fake_token(request, settings, principal):
        if isinstance(tok["value"], Exception):
            raise tok["value"]
        return tok["value"]

    F._LOCKS.clear()
    monkeypatch.setattr(R, "_ra_user_token", fake_token)
    monkeypatch.setattr(F, "_TRANSPORT", httpx.MockTransport(ra))
    app.dependency_overrides[get_settings] = lambda: s
    app.dependency_overrides[principal_pat_or_session] = lambda: KIM
    try:
        with TestClient(app, raise_server_exceptions=False) as c:
            keep = app.state.agent_audit
            app.state.agent_audit = _Audit()
            try:
                yield c, ra, s, tok
            finally:
                app.state.agent_audit = keep
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(principal_pat_or_session, None)
        F._LOCKS.clear()


def _meta(raw: bytes = PNG, **kw) -> dict:
    m = {"report_id": 41, "caption": "응력 분포 — 낙하 1.2 m", "tool": "dynaforge_plot", "mime": "image/png", "sha256": _sha(raw),
         "filename": "stress_plot.png", "ref": "gw:fig:1"}
    m.update(kw)
    return {k: v for k, v in m.items() if v is not None}


def _post(c, meta: dict, raw: bytes = PNG, *, path: str = "/agent/figures/to-report", headers: dict | None = None,
          name: str = "stress_plot.png", mime: str = "image/png") -> httpx.Response:
    return c.post(path, data={"meta": json.dumps(meta, ensure_ascii=False)}, files={"file": (name, raw, mime)}, headers=headers or {})


# ── 계약 — 고른 길 ──────────────────────────────────────────────────────────────────────────────────────────────
def test_그림을_그_사람_명의로_올리고_마지막_쪽_끝에_칸_하나를_붙인다(portal):
    c, ra, _s, _tok = portal
    r = _post(c, _meta())
    assert r.status_code == 200, r.text
    out = r.json()
    sid = f"fig_{_sha(PNG)[:16]}"
    assert out == {"ok": True, "report_id": 41, "file_id": "f1", "page": 2, "block_index": 2, "url": "/w/personal-5/reports/41",
                   "block_id": sid, "replaced": False}
    assert ra.paths() == ["GET /api/reports/41/outline", "PATCH /api/reports/41/ai-draft", "POST /api/files",
                          "PATCH /api/reports/41/ai-draft"]
    assert json.loads(ra.calls[1].content) == {"page": 2, "dry_run": True}, "올리기 전에 RA 가드를 dry_run 으로 묻는다"
    assert all(q.headers["authorization"] == "Bearer rat_kim" for q in ra.calls), "모든 RA 호출은 그 사람의 RA 토큰으로"
    assert ra.files == [{"filename": "stress_plot.png", "mime": "image/png", "auth": "Bearer rat_kim"}]
    patch = json.loads(ra.calls[-1].content)
    assert patch == {"page": 2, "extra_blocks": [{"id": sid, "type": "image", "props": {"max_count": 1}, "content": {
        "files": [{"file_id": "f1", "caption": "응력 분포 — 낙하 1.2 m", "alt": "응력 분포 — 낙하 1.2 m"}]}}]}
    assert re.fullmatch(r"[a-z][a-z0-9_]{0,63}", sid), "RA 블록 id 규칙(widgets/validation.py _BLOCK_ID_RE)"
    assert ra.pages[1]["blocks_order"][-1] == sid and ra.pages[0]["blocks_order"] == ["background", "results"]
    (row,) = app.state.agent_audit.rows
    assert row["event"] == "figure_to_report" and row["status"] == "ok" and row["principal"] == "kim@corp.com"
    assert row["meta"]["file_id"] == "f1" and row["meta"]["bytes"] == len(PNG)
    assert "응력" not in json.dumps(row, ensure_ascii=False), "감사에는 캡션 글을 남기지 않는다"


def test_page_를_주면_그_쪽이고_없는_쪽이면_올리지도_않고_400(portal):
    c, ra, _s, _tok = portal
    r = _post(c, _meta(page=1))
    assert r.status_code == 200 and r.json()["page"] == 1
    assert json.loads(ra.calls[-1].content)["page"] == 1
    n = len(ra.calls)
    r = _post(c, _meta(page=3))
    assert r.status_code == 400 and r.json()["error"] == "bad_page" and r.json()["ok"] is False
    assert ra.paths()[n:] == ["GET /api/reports/41/outline"], "없는 쪽이면 그림을 올리지 않는다(RA 에 고아 파일을 남기지 않는다)"


def test_같은_그림을_같은_쪽에_다시_넣으면_칸을_갈아_끼운다(portal):
    c, ra, _s, _tok = portal
    assert _post(c, _meta(caption="처음")).json()["replaced"] is False
    out = _post(c, _meta(caption="다시")).json()
    assert out["replaced"] is True and out["ok"] is True
    sid = f"fig_{_sha(PNG)[:16]}"
    assert ra.pages[1]["blocks_order"].count(sid) == 1, "다시 보내기가 칸을 늘리지 않는다"
    assert ra.pages[1]["content"][sid]["files"][0]["caption"] == "다시"


def test_upload_는_보고서를_건드리지_않고_file_id_만_준다(portal):
    c, ra, _s, _tok = portal
    m = _meta()
    del m["report_id"]
    r = _post(c, m, path="/agent/figures/upload")
    assert r.status_code == 200 and r.json() == {"ok": True, "file_id": "f1"}
    assert ra.paths() == ["POST /api/files"]


def test_캡션은_RA_상한_500자에서_줄인다(portal):
    c, ra, _s, _tok = portal
    _post(c, _meta(caption="가" * 900))
    f = json.loads(ra.calls[-1].content)["extra_blocks"][0]["content"]["files"][0]
    assert len(f["caption"]) == 500 and f["caption"].endswith("…") and len(f["alt"]) == 200


# ── 자격 — 진짜 의존성 ──────────────────────────────────────────────────────────────────────────────────────────
def _pat(s: Settings, scopes: list[str] | None, groups=("plat:reportarchive",)) -> str:
    ks = app.state.keystore
    now = datetime.now(tz=UTC)
    claims = {"iss": s.jwt_issuer, "sub": "kim@corp.com", "email": "kim@corp.com", "name": "김철수", "groups": list(groups),
              "aud": [s.pat_chat_audience], "scope": "api", "pat_name": "t", "iat": now, "nbf": now,
              "exp": now + timedelta(days=1), "jti": "t-" + secrets.token_urlsafe(8)}
    if scopes is not None:
        claims["scopes"] = scopes
    return jwt.encode(claims, ks.private_pem, algorithm="RS256", headers={"kid": ks.active_kid})


@pytest.fixture()
def real_auth(portal):
    """진짜 principal_pat_or_session — 권한 정책(app.state.access)은 비워 PAT 의 그룹을 그대로 쓴다(원장 · 정책은 이 시험의 관심이 아니다)."""
    app.dependency_overrides.pop(principal_pat_or_session, None)
    keep = getattr(app.state, "access", None)
    app.state.access = None
    try:
        yield portal
    finally:
        app.state.access = keep


def test_자격이_없거나_틀리면_401_이고_RA_를_부르지_않는다(real_auth):
    c, ra, _s, _tok = real_auth
    assert _post(c, _meta()).status_code == 401
    assert _post(c, _meta(), headers={"Authorization": "Bearer not-a-jwt"}).status_code == 401
    assert ra.calls == []


def test_세션은_CSRF_가_있어야_한다(real_auth):
    c, ra, _s, _tok = real_auth
    from app.auth.jwt_service import SESSION_AUDIENCE
    sess = app.state.jwt_service._encode({"sub": "kim@corp.com", "aud": SESSION_AUDIENCE, "email": "kim@corp.com", "name": "김철수",
                                          "groups": ["plat:reportarchive"]}, ttl=600, typ="session")
    c.cookies.set(SESSION_COOKIE, sess)
    c.cookies.set(CSRF_COOKIE, "t")
    try:
        assert _post(c, _meta()).status_code == 403, "세션 쿠키만으로 쓰지 못한다(CSRF)"
        assert ra.calls == []
        assert _post(c, _meta(), headers={"X-CSRF-Token": "t"}).status_code == 200
    finally:
        c.cookies.clear()


def test_읽기_전용_PAT_는_403_이고_쓰기_PAT_와_챗_PAT_는_넣는다(real_auth, monkeypatch):
    c, ra, s, _tok = real_auth
    r = _post(c, _meta(), headers={"Authorization": f"Bearer {_pat(s, ['read'])}"})
    assert r.status_code == 403 and r.json()["error"] == "read_only_token"
    assert ra.calls == [], "읽기 전용이면 RA 를 부르지도 않는다"
    assert _post(c, _meta(), headers={"Authorization": f"Bearer {_pat(s, ['read', 'write'])}"}).json()["ok"] is True
    assert _post(c, _meta(), headers={"Authorization": f"Bearer {_pat(s, None)}"}).json()["ok"] is True, "scopes 칸이 없는 옛 PAT"
    chat = R._chat_user_pat(app.state.keystore, s, KIM)
    assert jwt.decode(chat, options={"verify_signature": False})["scopes"] == ["chat"]
    # 챗 PAT 은 로그인 그룹만 싣는다 — 권한 키는 요청마다 원장으로 다시 계산한다(deps.entitled). 원장 대신 그 계산이 plat:reportarchive 를 준다고 둔다
    from app import deps
    monkeypatch.setattr(deps, "entitled", lambda request, p, admin_emails=frozenset(): p.model_copy(
        update={"groups": [*p.groups, "plat:reportarchive"]}))
    assert _post(c, _meta(), headers={"Authorization": f"Bearer {chat}"}).json()["ok"] is True, \
        "웹 챗 /보고서 의 에이전트 서버는 챗 PAT 로 부른다"


def test_plat_reportarchive_가_없으면_403(real_auth):
    c, ra, s, _tok = real_auth
    r = _post(c, _meta(), headers={"Authorization": f"Bearer {_pat(s, ['read', 'write'], groups=())}"})
    assert r.status_code == 403 and r.json()["error"] == "forbidden" and "plat:reportarchive" in r.json()["detail"]
    assert ra.calls == []


@pytest.mark.parametrize("scopes", [["read"], ["READ "], ["read", "write"], ["write"], ["chat"], ["mcp-app"], [], None, "read"])
def test_읽기_전용_판정은_루틴_창구와_같다(scopes):
    """같은 규칙이 두 자리에 있다(RF-2 — 루틴 창구는 절차 라우터라 import 하지 않았다). 어느 한쪽이 바뀌면 여기서 걸린다."""
    from types import SimpleNamespace

    from app.procedures.routine_routes import _read_only_pat as routine_rule
    claims = {"sub": "x"} if scopes is None else {"sub": "x", "scopes": scopes}
    tok = jwt.encode(claims, "k", algorithm="HS256")
    req = SimpleNamespace(headers={"authorization": f"Bearer {tok}"})
    assert F._read_only_pat(req) == routine_rule(tok)


# ── 그림 검사 ───────────────────────────────────────────────────────────────────────────────────────────────────
def test_SVG_는_415_와_까닭이고_RA_를_부르지_않는다(portal):
    c, ra, _s, _tok = portal
    r = _post(c, _meta(SVG, mime="image/svg+xml"), SVG, name="a.svg", mime="image/svg+xml")
    assert r.status_code == 415 and r.json()["error"] == "unsupported_media_type" and "SVG" in r.json()["detail"]
    r = _post(c, _meta(SVG, mime="image/png"), SVG)
    assert r.status_code == 415 and "그림이 아닙니다" in r.json()["detail"], "png 라고 해도 내용이 SVG 면 받지 않는다"
    r = _post(c, _meta(PNG, mime="application/pdf"))
    assert r.status_code == 415
    assert ra.calls == []


def test_선언과_내용이_다른_그림_꼴이면_내용의_꼴로_올린다(portal):
    c, ra, _s, _tok = portal
    r = _post(c, _meta(JPEG, mime="image/png", filename="plot.png"), JPEG)
    assert r.status_code == 200
    assert ra.files[-1]["mime"] == "image/jpeg" and ra.files[-1]["filename"] == "plot.jpg"
    _post(c, _meta(JPEG, mime="image/jpg", filename="../../etc/x y?.jpeg"), JPEG)
    assert ra.files[-1]["filename"] == "x_y.jpg", "경로 · 이상한 글자는 뗀다"


def test_크기_상한을_넘으면_413(portal):
    c, ra, s, _tok = portal
    s.docforge_ra_file_max_mb = 1
    big = PNG + b"\x00" * (2 * 1024 * 1024)
    r = _post(c, _meta(big), big)
    assert r.status_code == 413 and r.json()["error"] == "too_large", "길이 머리로 먼저 막는다"
    edge = PNG + b"\x00" * (1024 * 1024 - len(PNG) + 10)            # 길이 머리는 여유 안이고 그림은 상한 + 10 바이트
    r = _post(c, _meta(edge), edge)
    assert r.status_code == 413 and r.json()["error"] == "too_large", "읽을 때도 상한을 본다"
    assert ra.calls == []


def test_길이_머리가_없으면_411(portal):
    c, ra, _s, _tok = portal

    def body():
        yield b"--x\r\nContent-Disposition: form-data; name=\"meta\"\r\n\r\n{}\r\n--x--\r\n"
    r = c.post("/agent/figures/to-report", content=body(), headers={"content-type": "multipart/form-data; boundary=x"})
    assert r.status_code == 411 and r.json()["error"] == "length_required"
    assert ra.calls == []


@pytest.mark.parametrize("meta,err", [
    ({"sha256": "0" * 64}, "sha256_mismatch"),
    ({"sha256": "nothex"}, "bad_meta"),
    ({"report_id": None}, "bad_meta"),
    ({"report_id": True}, "bad_meta"),
    ({"page": 0}, "bad_meta"),
    ({"caption": 3}, "bad_meta"),
])
def test_meta_가_틀리면_400(portal, meta, err):
    c, ra, _s, _tok = portal
    m = _meta()
    m.update(meta)
    r = _post(c, {k: v for k, v in m.items() if v is not None})
    assert r.status_code == 400 and r.json()["error"] == err, r.text
    assert ra.calls == []


def test_meta_나_file_칸이_없으면_400(portal):
    c, ra, _s, _tok = portal
    r = c.post("/agent/figures/to-report", data={"meta": json.dumps(_meta())})
    assert r.status_code == 400 and r.json()["error"] == "bad_request"
    r = c.post("/agent/figures/to-report", files={"file": ("a.png", PNG, "image/png")})
    assert r.status_code == 400
    r = c.post("/agent/figures/to-report", data={"meta": "[1, 2]"}, files={"file": ("a.png", PNG, "image/png")})
    assert r.status_code == 400 and r.json()["error"] == "bad_meta"
    assert ra.calls == []


# ── RA 오류 ─────────────────────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("step,st,want,err", [
    ("outline", 404, 404, "report_not_found"),
    ("outline", 403, 403, "not_editable"),
    ("outline", 500, 502, "ra_error"),
    ("files", 403, 403, "forbidden_by_ra"),
    ("files", 413, 413, "too_large"),
    ("files", 401, 502, "ra_token_rejected"),
    ("files", 500, 502, "ra_error"),
    ("patch", 403, 403, "not_editable"),
    ("patch", 409, 409, "report_locked"),
    ("patch", 404, 404, "report_not_found"),
    ("patch_real", 400, 422, "ra_rejected"),
    ("patch_real", 409, 409, "report_locked"),
])
def test_RA_가_거절하면_맞는_상태와_까닭(portal, step, st, want, err):
    c, ra, _s, _tok = portal
    ra.status = {step: st}
    r = _post(c, _meta())
    assert r.status_code == want and r.json() == {"ok": False, "error": err, "detail": r.json()["detail"]}
    assert f"{step.split('_')[0]} {st}" in r.json()["detail"] or st == 401, "RA 가 밝힌 까닭을 붙인다"
    if step == "patch":
        assert "POST /api/files" not in ra.paths() and "남았습니다" not in r.json()["detail"], \
            "RA 가드(권한 · 발행 · 편집 잠금)가 거절할 보고서에는 그림 파일을 올리지 않는다 — RA 에 고아 파일을 남기지 않는다"
    if step == "patch_real":
        assert "f1" in r.json()["detail"] and "남았습니다" in r.json()["detail"], "가드 뒤에 거절되면 이미 올린 파일이 RA 에 남았다고 말한다"
    (row,) = app.state.agent_audit.rows
    assert row["status"] == "failed" and row["meta"]["error"] == err


@pytest.mark.parametrize("body", [["upstream"], "busy", 7])
def test_RA_오류의_본문이_객체가_아닌_JSON_이어도_계약대로_답한다(portal, monkeypatch, body):
    """반대 검토 F4 — 목록 · 글 · 수의 JSON 본문이 AttributeError 로 새어 포털 500(text/plain · 감사 없음)이 됐다."""
    c, _ra, _s, _tok = portal
    monkeypatch.setattr(F, "_TRANSPORT", httpx.MockTransport(lambda req: httpx.Response(503, json=body)))
    r = _post(c, _meta())
    assert r.status_code == 502 and r.json()["ok"] is False and r.json()["error"] == "ra_error"
    assert app.state.agent_audit.rows[-1]["status"] == "failed"


def test_mime_에_매개변수가_붙어도_꼴로_본다(portal):
    """반대 검토 F6 — 'image/png; charset=binary' 가 415 였다."""
    c, ra, _s, _tok = portal
    r = _post(c, _meta(mime="image/png; charset=binary"))
    assert r.status_code == 200 and r.json()["ok"] is True
    r = _post(c, _meta(SVG, mime="image/svg+xml; charset=utf-8"), SVG)
    assert r.status_code == 415 and "SVG" in r.json()["detail"]


def test_RA_에_닿지_못하면_502(portal, monkeypatch):
    c, _ra, _s, _tok = portal

    def down(req):
        raise httpx.ConnectError("refused")
    monkeypatch.setattr(F, "_TRANSPORT", httpx.MockTransport(down))
    r = _post(c, _meta())
    assert r.status_code == 502 and r.json()["error"] == "ra_unreachable"


def test_RA_가_칸을_경고로_버리면_502_이고_조용히_성공하지_않는다(portal):
    c, ra, _s, _tok = portal
    ra.drop = True
    r = _post(c, _meta())
    assert r.status_code == 502 and r.json()["error"] == "ra_dropped_block"
    assert "형식 불일치" in r.json()["detail"] and "f1" in r.json()["detail"]


def test_RA_연결이_없으면_그_까닭(portal):
    c, ra, _s, tok = portal
    tok["value"] = AuthError("Report Archive 연결이 없습니다 — 포털 '개인 토큰 › 외부 연결' 에서 RA 토큰을 먼저 등록하세요.", status_code=400)
    r = _post(c, _meta())
    assert r.status_code == 400 and r.json()["error"] == "no_ra_connection" and "외부 연결" in r.json()["detail"]
    assert ra.calls == []


def test_위임_토큰이_거절되면_한_번만_새로_받는다(portal, monkeypatch):
    c, ra, _s, tok = portal
    tok["value"] = ("stale", True, {"workspace": "team-a"})
    minted = []

    async def fresh(settings, *, email, name=""):
        minted.append(email)
        return "fresh"
    monkeypatch.setattr(ra_sso, "ra_user_token", fresh)
    seen = {"n": 0}
    real = ra.__call__

    async def first_401(req):
        seen["n"] += 1
        if seen["n"] == 1:
            ra.calls.append(req)
            return httpx.Response(401, json={"success": False, "message": "expired"})
        return await real(req)
    monkeypatch.setattr(F, "_TRANSPORT", httpx.MockTransport(first_401))
    r = _post(c, _meta())
    assert r.status_code == 200, r.text
    assert minted == ["kim@corp.com"]
    assert [q.headers["authorization"] for q in ra.calls] == ["Bearer stale"] + ["Bearer fresh"] * 4
    assert all(q.headers.get("x-workspace-slug") == "team-a" for q in ra.calls)


# ── 동시 호출 ───────────────────────────────────────────────────────────────────────────────────────────────────
def test_같은_보고서에_그림_둘을_한꺼번에_넣어도_칸이_사라지지_않는다(monkeypatch):
    """RA 의 PATCH 는 읽고 · 합치고 · 쓴다 — 줄 세우지 않으면 뒤 쓰기가 앞 칸을 덮는다(개인 Claude 의 병렬 도구 호출, RF-6)."""
    ra = _RA(delay=0.05)
    monkeypatch.setattr(F, "_TRANSPORT", httpx.MockTransport(ra))
    F._LOCKS.clear()
    raw2 = PNG + b"\x01"

    def fig(raw):
        return {"report_id": 41, "page": None, "sha256": _sha(raw), "mime": "image/png", "caption": "c", "alt": "c", "tool": "",
                "filename": "a.png", "ref": ""}

    async def both():
        mk = lambda: F._dfd.RaSession("http://ra.test", "rat_kim")   # noqa: E731
        return await asyncio.gather(F._to_report(mk(), fig(PNG), PNG), F._to_report(mk(), fig(raw2), raw2))
    a, b = asyncio.run(both())
    assert {f"fig_{_sha(PNG)[:16]}", f"fig_{_sha(raw2)[:16]}"} <= set(ra.pages[1]["blocks_order"]), "앞 칸이 덮였다"
    assert a["ok"] and b["ok"]
    F._LOCKS.clear()


# ── 에이전트 서버와의 계약 ─────────────────────────────────────────────────────────────────────────────────────
def test_에이전트_서버의_그림_올리기를_포털이_그대로_받고_같은_칸을_짓는다(real_auth, monkeypatch, tmp_path):
    """형제 리포 HWAXAgentServer 의 report_figures.attach 를 진짜 포털 앱(ASGI)에 물린다 — 칸 이름 · 자격 · 답의 꼴이 두 쪽에서 같아야 한다.
    한쪽만 바꾸면(meta 칸 이름 · file_id · 그림 칸의 꼴) 여기서 걸린다."""
    if not _AGENT_RF.is_file():
        pytest.skip("형제 리포 HWAXAgentServer 가 없다")
    spec = importlib.util.spec_from_file_location("agent_report_figures", _AGENT_RF)
    rf = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, rf)          # dataclass 가 지을 때 자기 모듈을 sys.modules 에서 찾는다
    spec.loader.exec_module(rf)
    c, ra, s, _tok = real_auth
    from app import deps
    monkeypatch.setattr(deps, "entitled", lambda request, p, admin_emails=frozenset(): p.model_copy(
        update={"groups": [*p.groups, "plat:reportarchive"]}))
    chat = R._chat_user_pat(app.state.keystore, s, KIM)
    name = _sha(PNG)[:20] + ".png"
    (tmp_path / name).write_bytes(PNG)
    monkeypatch.setattr(rf, "PORTAL_TRANSPORT", httpx.ASGITransport(app=app))
    monkeypatch.setattr(rf, "PORTAL_HTTP_BASE", "http://portal.test")
    out = asyncio.run(rf.attach({"results": [f"응력 ![응력](/agent/artifacts/{name})"]}, user_pat=chat, artifact_dir=str(tmp_path)))
    assert out.summary() == {"found": 1, "attached": 1, "failed": 0, "reasons": [], "failed_refs": []}, out.failed
    assert out.blocks["results"] == ["응력 [그림 1 — 응력]"]
    assert ra.paths() == ["POST /api/files"] and ra.files == [{"filename": name, "mime": "image/png", "auth": "Bearer rat_kim"}]
    assert out.extra_blocks == [F.block("f1", _sha(PNG), "그림 1 — 응력", "응력")], "그림 칸의 꼴은 포털 to-report 의 것과 같다"
    (row,) = app.state.agent_audit.rows
    assert row["event"] == "figure_upload" and row["principal"] == "kim@corp.com"
