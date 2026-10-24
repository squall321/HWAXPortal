# Report Archive 정밀 변환(DocForge) — 맡기기 · 진행 · 배달(리소스 올리기 · res:// 바꾸기 · 엄격 생성) · 한 번만 · 주인 검사 · 경로 탈출(DF-D17)
"""가짜 게이트웨이 MCP(_upload.mcp_call 바꿔치기) + 가짜 RA(httpx MockTransport) + 디스크의 합성 패키지로 끝에서 끝까지 본다.
고정하는 것.
  · 맡기기는 스테이징의 **호스트 경로**를 docforge_convert 에 넘기고, 맡긴 사람을 기록한다(진행 · 배달은 그 사람만 — 남의 것은 '없다').
  · 배달은 report.json 이 가리키는 리소스만 POST /api/files → 'res://' 를 받은 id 로 → template 을 pages[0] 에서 올려 POST /api/reports.
  · RA 상한을 넘는 리소스는 올리지 않고 그 파일 칸을 빼고 경고로. 두 번 불러도 보고서는 하나. 패키지 위치가 데이터 루트 밖이면 거절.
"""
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from app.agent import docforge_delivery as D
from app.auth import ra_sso
from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.config import Settings

_REAL_CLIENT = httpx.AsyncClient
KIM = Principal(subject="kim@corp.com", email="kim@corp.com", display_name="김철수")
LEE = Principal(subject="lee@corp.com", email="lee@corp.com", display_name="이영희")


@pytest.fixture(autouse=True)
def _fresh():
    ra_sso._CACHE.clear()
    D._LOCKS.clear()
    yield
    ra_sso._CACHE.clear()


def _settings(tmp_path, **kw) -> Settings:
    kw.setdefault("ra_base_url", "http://ra.test")
    kw.setdefault("ra_sso_secret", "")
    return Settings(_env_file=None, upload_staging_dir=str(tmp_path / "staging"), upload_staging_host_dir="/host/staging",
                    docforge_package_root=str(tmp_path / "df"), **kw)


def _package(tmp_path, rel="jobs/j_abc123/package", big=0) -> str:
    """DocForge 패키지 꼴 — 그림 하나 · 첨부 하나(원본) · 안 쓰는 리소스 하나."""
    pkg = tmp_path / "df" / rel
    (pkg / "resources").mkdir(parents=True)
    (pkg / "resources" / "img_0001.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 10)
    (pkg / "resources" / "original.pptx").write_bytes(b"PK" + b"0" * big)
    (pkg / "resources" / "unused.png").write_bytes(b"x")
    page = {"template_id": "__import_blank__", "template_version": 1, "name": "설계 검토",
            "extra_blocks": [{"id": "df_1_1", "type": "heading", "props": {"level": 1}, "layout": {"row": 1, "col_span": 12}},
                             {"id": "df_1_2", "type": "image", "props": {"max_count": 1}, "layout": {"row": 2, "col_span": 12}},
                             {"id": "df_1_3", "type": "attachment", "props": {"max_count": 1}, "layout": {"row": 3, "col_span": 12}}],
            "content": {"df_1_1": {"text": "설계 검토", "level": 1},
                        "df_1_2": {"files": [{"file_id": "res://img_0001.png", "caption": "그림 1"}]},
                        "df_1_3": {"files": [{"file_id": "res://original.pptx", "filename": "a.pptx"}]}},
            "blocks_order": ["df_1_1", "df_1_2", "df_1_3"]}
    (pkg / "report.json").write_text(json.dumps({"_type": "report_archive_draft_v1", "title": "설계 검토", "tags": ["docforge"],
                                                 "pages": [page]}, ensure_ascii=False), encoding="utf-8")
    (pkg / "conversion.json").write_text(json.dumps({
        "fidelity": "full", "parser": "native python-pptx 1.0.2", "counts": {"units": 1, "blocks": 3},
        "accounting": {"unaccounted": []}, "dropped": [{"element_id": "u1.e9"}],
        "model_written": [{"block_id": "df_1_2"}], "warnings": ["u1.e3: 경고 하나"]}), encoding="utf-8")
    return rel


def _mock_ra(monkeypatch, *, reports_status=201, files_status=201, first_401=False):
    seen: list[httpx.Request] = []
    state = {"n": 0}

    def h(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        if first_401 and state["n"] == 0:
            state["n"] += 1
            return httpx.Response(401, json={"detail": "expired"})
        if req.url.path == "/api/auth/sso":
            return httpx.Response(200, json={"success": True, "data": {"access_token": "fresh-token", "expires_in": 43200}})
        if req.url.path == "/api/files":
            n = sum(1 for r in seen if r.url.path == "/api/files")
            return httpx.Response(files_status, json={"success": True, "data": {"id": f"f{n}"}})
        assert req.url.path == "/api/reports", req.url
        return httpx.Response(reports_status, json={"success": True, "data": {"id": 41, "workspace_slug": "personal-5",
                                                                            "title": "설계 검토"}}
                              if reports_status < 400 else {"success": False, "message": "template not found"})

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: _REAL_CLIENT(transport=httpx.MockTransport(h), **kw))
    return seen


class _Store:
    def __init__(self, conn=None):
        self.conn = conn

    def get_connection(self, *, email, service):
        return dict(self.conn) if self.conn else None


class _Audit:
    def __init__(self):
        self.rows = []

    def record(self, **kw):
        self.rows.append(kw)


def _wire(monkeypatch, tmp_path, mcp_replies: dict):
    from app.agent import routes as R
    f = tmp_path / "staging" / "kim" / "s1" / "a.pptx"
    f.parent.mkdir(parents=True)
    f.write_bytes(b"PK\x03\x04 fake")
    calls = []

    async def _mcp(url, pat, tool, args, timeout=90.0):
        calls.append((tool, args))
        return dict(mcp_replies[tool])

    monkeypatch.setattr(R._upload, "require_destination_group", lambda *a, **k: None)
    monkeypatch.setattr(R._upload, "staged_path", lambda *a, **k: f)
    monkeypatch.setattr(R._upload, "mcp_call", _mcp)
    monkeypatch.setattr(R, "_chat_user_pat", lambda *a, **k: "chat-pat")
    req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(user_store=_Store({"token": "rat_kim", "workspace": ""}),
                                                                    agent_audit=_Audit(), keystore=None)))
    return R, req, calls


@pytest.mark.anyio
async def test_맡기기는_호스트_경로를_넘기고_맡긴_사람을_기록한다(monkeypatch, tmp_path):
    s = _settings(tmp_path)
    R, req, calls = _wire(monkeypatch, tmp_path, {"docforge_convert": {"job_id": "j_abc123", "status": "queued"}})
    body = R.UploadDispatchReq(staging_id="s1", filename="a.pptx", destination="reportarchive_precise")
    out = await R._dispatch_inner(req, body, KIM, s)
    assert out["stage"] == "dispatched" and out["job_id"] == "j_abc123"
    ((tool, args),) = calls
    assert tool == "docforge_convert" and args == {"path": "/host/staging/kim/s1/a.pptx", "parser": "auto", "vlm": True}
    assert D.load_job(s, "j_abc123", KIM.subject)["filename"] == "a.pptx"
    with pytest.raises(D.DeliveryError) as e:
        D.load_job(s, "j_abc123", LEE.subject)
    assert e.value.status == 404, "남의 잡은 있는지도 알리지 않는다"
    assert req.app.state.agent_audit.rows[-1]["meta"]["job_id"] == "j_abc123"


@pytest.mark.anyio
async def test_DocForge_가_거절하면_실패로_말한다(monkeypatch, tmp_path):
    R, req, _ = _wire(monkeypatch, tmp_path, {"docforge_convert": {"ok": False, "error": "입력 뿌리 밖의 경로", "status": 403}})
    body = R.UploadDispatchReq(staging_id="s1", filename="a.pptx", destination="reportarchive_precise", vlm=False)
    out = await R._dispatch_inner(req, body, KIM, _settings(tmp_path))
    assert out["stage"] == "failed" and "입력 뿌리 밖의 경로" in out["error"]


@pytest.mark.anyio
async def test_배달은_리소스를_올리고_res_를_바꿔_엄격_생성한다_두_번이어도_하나(monkeypatch, tmp_path):
    s = _settings(tmp_path)
    rel = _package(tmp_path)
    R, req, calls = _wire(monkeypatch, tmp_path, {"docforge_package": {"job_id": "j_abc123", "package_rel": rel}})
    D.save_job(s, "j_abc123", owner_sub=KIM.subject, owner_email=KIM.email, filename="a.pptx")
    seen = _mock_ra(monkeypatch)
    out = await R.upload_docforge_deliver("j_abc123", req, KIM, s)
    assert out["stage"] == "done" and out["report_id"] == 41 and out["url"] == "/w/personal-5/reports/41"
    assert (out["pages"], out["blocks"], out["dropped"], out["model_written"], out["unaccounted"]) == (1, 3, 1, 1, 0)
    files = [r for r in seen if r.url.path == "/api/files"]
    assert len(files) == 2, "report.json 이 가리키는 것만(unused.png 는 올리지 않는다)"
    assert all(r.headers["Authorization"] == "Bearer rat_kim" for r in seen)
    (create,) = [r for r in seen if r.url.path == "/api/reports"]
    body = json.loads(create.content)
    assert (body["template_id"], body["template_version"], body["title"]) == ("__import_blank__", 1, "설계 검토")
    assert "_type" not in body
    content = body["pages"][0]["content"]
    assert {content["df_1_2"]["files"][0]["file_id"], content["df_1_3"]["files"][0]["file_id"]} == {"f1", "f2"}
    assert "res://" not in create.content.decode()
    again = await R.upload_docforge_deliver("j_abc123", req, KIM, s)
    assert again["report_id"] == 41 and again["created"] is False
    assert sum(1 for r in seen if r.url.path == "/api/reports") == 1, "두 번 불러도 보고서는 하나"
    st = await R.upload_docforge_status("j_abc123", req, KIM, s)
    assert st["delivered"]["report_id"] == 41


@pytest.mark.anyio
async def test_RA_상한을_넘는_리소스는_올리지_않고_칸을_빼고_알린다(monkeypatch, tmp_path):
    s = _settings(tmp_path, docforge_ra_file_max_mb=1)
    pkg = D.package_dir(s, _package(tmp_path, big=2 * 1024 * 1024))
    seen = _mock_ra(monkeypatch)
    got = await D.deliver(s, pkg, token="t")
    assert sum(1 for r in seen if r.url.path == "/api/files") == 1
    body = json.loads([r for r in seen if r.url.path == "/api/reports"][0].content)
    assert body["pages"][0]["content"]["df_1_3"]["files"] == []
    assert any("original.pptx" in w and "RA 상한" in w for w in got["warnings"])


@pytest.mark.anyio
async def test_위임_토큰이_거절되면_한_번만_새로_받는다(monkeypatch, tmp_path):
    s = _settings(tmp_path)
    pkg = D.package_dir(s, _package(tmp_path))
    seen = _mock_ra(monkeypatch, first_401=True)
    calls = []

    async def remint():
        calls.append(1)
        return "fresh-token"

    got = await D.deliver(s, pkg, token="stale", remint=remint)
    assert got["report_id"] == 41 and calls == [1]
    assert seen[0].headers["Authorization"] == "Bearer stale" and seen[1].headers["Authorization"] == "Bearer fresh-token"


@pytest.mark.anyio
async def test_RA_가_거절하면_까닭과_템플릿_안내(monkeypatch, tmp_path):
    s = _settings(tmp_path)
    pkg = D.package_dir(s, _package(tmp_path))
    _mock_ra(monkeypatch, reports_status=400)
    with pytest.raises(D.DeliveryError, match="__import_blank__"):
        await D.deliver(s, pkg, token="t")


def test_패키지_위치가_데이터_루트_밖이면_거절(tmp_path):
    s = _settings(tmp_path)
    _package(tmp_path)
    (tmp_path / "outside" / "package").mkdir(parents=True)
    for bad in ("../outside/package", "/etc", "", "jobs/none/package"):
        with pytest.raises(D.DeliveryError):
            D.package_dir(s, bad)
    (tmp_path / "df" / "link").symlink_to(tmp_path / "outside")
    with pytest.raises(D.DeliveryError, match="밖"):
        D.package_dir(s, "link/package")


@pytest.mark.anyio
async def test_남의_잡은_진행도_배달도_없다(monkeypatch, tmp_path):
    s = _settings(tmp_path)
    R, req, calls = _wire(monkeypatch, tmp_path, {"docforge_status": {"status": "running"}})
    D.save_job(s, "j_abc123", owner_sub=KIM.subject, owner_email=KIM.email, filename="a.pptx")
    for fn in (R.upload_docforge_status, R.upload_docforge_deliver, R.upload_docforge_cancel):
        with pytest.raises(AuthError) as e:
            await fn("j_abc123", req, LEE, s)
        assert e.value.status_code == 404
    with pytest.raises(AuthError):
        await R.upload_docforge_status("../../etc", req, KIM, s)
    assert calls == [], "주인이 아니면 DocForge 를 부르지도 않는다"
    st = await R.upload_docforge_status("j_abc123", req, KIM, s)
    assert st["status"] == "running"


def test_정밀_변환_목적지는_RA_와_DocForge_둘_다_있어야(tmp_path):
    from app.agent import upload as U
    s = _settings(tmp_path, upload_allowed_groups="")
    both = ["feat:upload", "plat:reportarchive", "plat:docforge"]
    assert any(d["id"] == "reportarchive_precise" for d in U.allowed_destinations(s, both, "pptx"))
    assert not any(d["id"] == "reportarchive_precise" for d in U.allowed_destinations(s, both[:2], "pptx"))
    assert any(d["id"] == "reportarchive_precise" for d in U.allowed_destinations(s, both, "xlsx"))


# ── PC 도우미 추출본(DRM 문서) — 글 + 슬라이드 그림을 zip 하나로(DF-D18) ─────────────────────────────────────────────
MD = "---\nschema: hwax-doc/1\nsource: 설계검토.pptx\nkind: ppt\n---\n\n# 설계검토\n## [s.1] 개요\n\n낙하 1.5 m\n"
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 20


def _wire_pc(monkeypatch, s):
    """staged_path 는 진짜로 — 받은 글 상자에서 글을 집는 것까지 본다. 가짜 게이트웨이는 넘겨받은 경로를 그 자리에서 열어 본다(뒤에 지워지므로)."""
    from app.agent import routes as R
    seen: dict = {"calls": 0}

    async def _mcp(url, pat, tool, args, timeout=90.0):
        seen["calls"] += 1
        local = Path(args["path"].replace("/host/staging", s.upload_staging_dir, 1))
        seen["path"] = local
        if local.suffix == ".zip":
            with zipfile.ZipFile(local) as zf:
                seen["names"] = sorted(zf.namelist())
        return {"job_id": "j_pc0001", "status": "queued"}

    monkeypatch.setattr(R._upload, "require_destination_group", lambda *a, **k: None)
    monkeypatch.setattr(R._upload, "mcp_call", _mcp)
    monkeypatch.setattr(R, "_chat_user_pat", lambda *a, **k: "chat-pat")
    req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(user_store=_Store(None), agent_audit=_Audit(), keystore=None)))
    return R, req, seen


@pytest.mark.anyio
async def test_PC_도우미_추출본은_글과_슬라이드_그림을_zip_하나로_넘기고_묶음_상자를_치운다(monkeypatch, tmp_path):
    from app.agent import pc_upload as P
    s = _settings(tmp_path)
    got = P.store(s, {"owner_sub": KIM.subject, "filename": "설계검토.pptx"}, MD, [PNG, PNG])
    R, req, seen = _wire_pc(monkeypatch, s)
    body = R.UploadDispatchReq(staging_id=got["doc_staging_id"], filename=got["doc_name"], destination="reportarchive_precise")
    out = await R._dispatch_inner(req, body, KIM, s)
    assert out["stage"] == "dispatched" and out["job_id"] == "j_pc0001"
    assert seen["names"] == ["slide-01.png", "slide-02.png", "설계검토.hwax.md"], "DocForge 는 zip 안의 *.hwax.md 와 slide-NN.png 를 읽는다"
    assert not seen["path"].parent.exists(), "DocForge 가 받아 간 뒤 묶음 상자는 지운다"
    assert R._upload.staged_path(s, KIM.subject, got["doc_staging_id"], got["doc_name"]).name == "설계검토.hwax.md", \
        "받은 글 상자에는 글 하나뿐 — 다른 목적지(AI 데이터 허브)로 보내도 글이 간다"
    assert req.app.state.agent_audit.rows[-1]["meta"]["slides"] == 2
    assert P.slides_of(s, LEE.subject, got["doc_staging_id"]) == [], "남의 글 상자의 그림은 찾지 않는다"


@pytest.mark.anyio
async def test_그림_없는_추출본은_글만_넘긴다(monkeypatch, tmp_path):
    from app.agent import pc_upload as P
    s = _settings(tmp_path)
    got = P.store(s, {"owner_sub": KIM.subject, "filename": "설계검토.pptx"}, MD, [])
    R, req, seen = _wire_pc(monkeypatch, s)
    body = R.UploadDispatchReq(staging_id=got["doc_staging_id"], filename=got["doc_name"], destination="reportarchive_precise")
    out = await R._dispatch_inner(req, body, KIM, s)
    assert out["stage"] == "dispatched" and seen["path"].name == "설계검토.hwax.md" and "names" not in seen


@pytest.mark.anyio
async def test_추출기가_만들지_않은_md_는_맡기지_않는다(monkeypatch, tmp_path):
    from app.agent import upload as U
    s = _settings(tmp_path)
    box = U._user_dir(s, KIM.subject) / ("a" * 32)
    box.mkdir(parents=True)
    (box / "note.md").write_text("# 그냥 메모\n", encoding="utf-8")
    R, req, seen = _wire_pc(monkeypatch, s)
    body = R.UploadDispatchReq(staging_id="a" * 32, filename="note.md", destination="reportarchive_precise")
    out = await R._dispatch_inner(req, body, KIM, s)
    assert out["stage"] == "failed" and "PC 도우미가 만든 .hwax.md 만" in out["error"] and seen["calls"] == 0


# ── 이 대화에서 분석 — DocForge 가 보이는 사람은 DocForge 로(DF-D19) ──────────────────────────────────────────────
KIM_DF = Principal(subject="kim@corp.com", email="kim@corp.com", display_name="김철수", groups=["feat:upload", "plat:aidatahub", "plat:docforge"])
RECORD = {"record": {"meta": {"source_format": "pptx", "title": "a"}, "sections": [{"title": "개요", "blocks": [{"type": "paragraph", "text": "글"}]}]}}


def _wire_chat(monkeypatch, tmp_path, replies: dict):
    """종전 길(AI 데이터 허브)도 돌 수 있게 inbox 를 시험 폴더로."""
    monkeypatch.setenv("AIDH_CONVERT_INBOX", str(tmp_path / "inbox"))
    R, req, calls = _wire(monkeypatch, tmp_path, {})

    async def _mcp(url, pat, tool, args, timeout=90.0):
        calls.append((tool, args))
        rep = replies[tool]
        if isinstance(rep, Exception):
            raise rep
        return dict(rep)

    monkeypatch.setattr(R._upload, "mcp_call", _mcp)
    return R, req, calls


@pytest.mark.anyio
async def test_DocForge_가_보이면_이_대화에서_분석은_DocForge_에_맡긴다_그림_판독은_끄고(monkeypatch, tmp_path):
    s = _settings(tmp_path)
    R, req, calls = _wire_chat(monkeypatch, tmp_path, {"docforge_convert": {"job_id": "j_chat01", "status": "queued"}})
    out = await R._dispatch_inner(req, R.UploadDispatchReq(staging_id="s1", filename="a.pptx", destination="chat"), KIM_DF, s)
    assert out == {"stage": "dispatched", "destination": "chat", "via": "docforge", "job_id": "j_chat01"}
    ((tool, args),) = calls
    assert tool == "docforge_convert" and args["vlm"] is False and args["path"] == "/host/staging/kim/s1/a.pptx"
    assert D.load_job(s, "j_chat01", KIM.subject)["purpose"] == "chat"


@pytest.mark.anyio
async def test_DocForge_가_안_보이거나_맡지_않으면_종전_길(monkeypatch, tmp_path):
    s = _settings(tmp_path)
    R, req, calls = _wire_chat(monkeypatch, tmp_path, {"docforge_convert": AuthError("docforge_convert: unknown tool", status_code=502),
                                                            "convert_file": RECORD})
    body = R.UploadDispatchReq(staging_id="s1", filename="a.pptx", destination="chat")
    out = await R._dispatch_inner(req, body, KIM, s)                 # plat:docforge 없음
    assert out["stage"] == "done" and [t for t, _ in calls] == ["convert_file"]
    calls.clear()
    out = await R._dispatch_inner(req, body, KIM_DF, s)              # 있지만 게이트웨이가 모른다
    assert out["stage"] == "done" and out["doc"]["name"] == "a.hwax.md" and [t for t, _ in calls] == ["docforge_convert", "convert_file"]


@pytest.mark.anyio
async def test_끝난_대화용_잡은_읽은_글을_주고_RA_에는_넣지_않는다(monkeypatch, tmp_path):
    s = _settings(tmp_path)
    rel = _package(tmp_path)
    md = "---\nschema: hwax-doc/1\nsource: a.pptx\nkind: ppt\nunits: 1\n---\n\n# 설계 검토\n\n## [s.1] 개요\n\n낙하 1.5 m\n"
    (tmp_path / "df" / rel / "document.md").write_text(md, encoding="utf-8")
    R, req, calls = _wire(monkeypatch, tmp_path, {"docforge_package": {"job_id": "j_chat01", "package_rel": rel}})
    D.save_job(s, "j_chat01", owner_sub=KIM.subject, owner_email=KIM.email, filename="설계 검토.pptx", purpose="chat")
    out = await R.upload_docforge_document("j_chat01", req, KIM, s)
    assert out["stage"] == "done" and out["doc"] == {"name": "설계 검토.hwax.md", "text": md, "chars": len(md)}
    row = req.app.state.agent_audit.rows[-1]
    assert row["event"] == "upload_document" and row["meta"]["chars"] == len(md) and "text" not in row["meta"], "문서 글은 감사에 싣지 않는다"
    with pytest.raises(AuthError) as e:
        await R.upload_docforge_deliver("j_chat01", req, KIM, s)
    assert e.value.status_code == 409 and [t for t, _ in calls] == ["docforge_package"]
    with pytest.raises(AuthError) as e:
        await R.upload_docforge_document("j_chat01", req, LEE, s)
    assert e.value.status_code == 404


@pytest.mark.anyio
async def test_글이_없는_낡은_패키지면_까닭을_말한다(monkeypatch, tmp_path):
    s = _settings(tmp_path)
    rel = _package(tmp_path)
    R, req, _ = _wire(monkeypatch, tmp_path, {"docforge_package": {"job_id": "j_chat01", "package_rel": rel}})
    D.save_job(s, "j_chat01", owner_sub=KIM.subject, owner_email=KIM.email, filename="a.pptx", purpose="chat")
    out = await R.upload_docforge_document("j_chat01", req, KIM, s)
    assert out["stage"] == "failed" and "document.md" in out["error"]
