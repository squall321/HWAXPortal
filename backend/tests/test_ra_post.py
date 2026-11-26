# 심의 보고서 RA 제출 표준 — 박스 파일의 심의 형식 · 시스템 공간 게시판, 사람이 확인한 뒤의 게시, 리스크 보고서 형식 통일(docs/ra-delib-standard)
"""왜 — 심의 보고서를 RA 에 저장하는 길이 다섯이고 형식을 고르는 장치가 셋으로 갈려 있었다. 다섯 모두 개인 초안으로만 남아 게시까지 가는 길이 없었다.
사용자 결정(11-26): 심의 형식 하나(박스 파일 한 곳) · RA 시스템 공간에 사람이 확인한 뒤 게시. 게시판은 박스 파일에서만 오고, 게시는 그 사람 명의다.
"""
import importlib.util
import json
import os
import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.agent import ra_post as P
from app.agent import risk_report as RR
from app.agent import routes as R
from app.auth.provider import Principal
from app.config import Settings, get_settings
from app.deps import principal_pat_or_session, require_csrf
from app.main import app

ROOT = Path(__file__).resolve().parents[2]
AGENT = ROOT.parent / "HWAXAgentServer" / "ra_formats.py"
PARK = Principal(subject="park-post@corp.com", email="park-post@corp.com", display_name="박", groups=["plat:reportarchive"])


@pytest.fixture()
def box(monkeypatch, tmp_path):
    """박스 파일 자리를 시험 폴더로 — 쓰면 그 내용, 안 쓰면 파일 없음."""
    path = tmp_path / "ra-formats.local.json"
    monkeypatch.setattr(P, "PATH", path)
    monkeypatch.setitem(P._STATE, "key", "시험")

    def write(doc):
        path.write_text(json.dumps(doc) if not isinstance(doc, str) else doc, encoding="utf-8")
        st = path.stat()
        os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000))    # 같은 크기로 다시 써도 다시 읽게
    return write


ROW = {"template_id": "sys.hwax.deliberation", "template_version": 2, "board": "sys-hwax"}


# ── 박스 파일 읽기 ─────────────────────────────────────────────────────────────────────────────────────────
def test_파일이_없으면_기본_형식이고_게시하지_않는다(box):
    assert P.deliberation_template() == ("deliberation", 1) and P.box_template() is None and P.deliberation_board() is None
    assert P.status() == {"board": None, "template_id": "deliberation", "template_version": 1, "source": "default", "error": None}


def test_줄이_맞으면_그_형식과_게시판(box):
    box({"_doc": "메모", "deliberation": ROW})
    assert P.deliberation_template() == ("sys.hwax.deliberation", 2) and P.deliberation_board() == "sys-hwax"
    assert P.status()["source"] == "box"


def test_board_가_없으면_형식만_바꾸고_게시하지_않는다(box):
    box({"deliberation": {"template_id": "sys.hwax.deliberation", "template_version": 1}})
    assert P.box_template() == ("sys.hwax.deliberation", 1) and P.deliberation_board() is None and P.status()["error"] is None


@pytest.mark.parametrize("board", ["../x", "a/b", "", ".", "..", "x" * 65, 3, ["sys-hwax"]])
def test_board_꼴이_틀리면_게시하지_않고_까닭을_남긴다(box, board):
    box({"deliberation": {**ROW, "board": board}})
    assert P.box_template() == ("sys.hwax.deliberation", 2) and P.deliberation_board() is None and P.status()["error"]


@pytest.mark.parametrize("row", [{"template_id": "../x", "template_version": 1, "board": "sys-hwax"},
                                 {"template_id": "sys.hwax.deliberation", "template_version": True, "board": "sys-hwax"},
                                 {"template_id": "sys.hwax.deliberation", "template_version": 0, "board": "sys-hwax"},
                                 "sys.hwax.deliberation"])
def test_형식_줄이_틀리면_기본으로_돌고_게시판도_쓰지_않는다(box, row):
    box({"deliberation": row})
    assert P.deliberation_template() == ("deliberation", 1) and P.deliberation_board() is None and P.status()["error"]


def test_깨진_파일은_기본으로(box):
    box("{ 깨진")
    assert P.deliberation_template() == ("deliberation", 1) and P.deliberation_board() is None and "못 읽음" in P.status()["error"]


def test_바뀌면_재기동_없이_다시_읽는다(box):
    box({"deliberation": ROW})
    assert P.deliberation_board() == "sys-hwax"
    box({"deliberation": {**ROW, "board": "sys-cae"}})
    assert P.deliberation_board() == "sys-cae"


def test_에이전트_서버는_board_칸이_있어도_같은_형식을_읽는다(tmp_path, monkeypatch):
    """두 리더(에이전트 서버 · 게이트웨이)는 줄의 template_id · template_version 만 읽는다 — board 를 더해도 그쪽 동작이 같다(RS-4)."""
    if not AGENT.is_file():
        pytest.skip("형제 리포 HWAXAgentServer 가 이 박스에 없다")
    path = tmp_path / "ra-formats.local.json"
    path.write_text(json.dumps({"deliberation": ROW}), encoding="utf-8")
    monkeypatch.setenv("RA_FORMATS_PATH", str(path))
    spec = importlib.util.spec_from_file_location("ra_formats_under_test", AGENT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.template("deliberation") == ("sys.hwax.deliberation", 2) and mod._load()["error"] is None
    sys.modules.pop("ra_formats_under_test", None)


def test_게이트웨이_리더도_줄의_두_칸만_읽는다():
    gw = ROOT.parent / "HWAXMcpGateway" / "gateway.py"
    if not gw.is_file():
        pytest.skip("형제 리포 HWAXMcpGateway 가 이 박스에 없다")
    src = gw.read_text(encoding="utf-8")
    body = src[src.index("def _ra_formats_load"):src.index("def _ra_format_args")]
    assert 'row.get("template_id")' in body and 'row.get("template_version")' in body and "board" not in body


# ── 리스크 종합 보고서의 형식 통일(RS-5) ────────────────────────────────────────────────────────────────────
def _mat(tid="deliberation", ver=1):
    return {"template": {"id": tid, "version": ver}, "title": "리스크 종합", "tags": ["리스크"], "pages_total": 1,
            "pages": [{"background": ["b"]}], "ra": {}}


def test_리스크_보고서는_박스_파일이_없으면_앱_값_그대로(box):
    assert (lambda m: (m["template_id"], m["template_version"]))(RR._material(_mat(ver=3))) == ("deliberation", 3)


def test_리스크_보고서가_기본_틀이면_박스의_심의_형식으로(box):
    box({"deliberation": ROW})
    m = RR._material(_mat(ver=3))
    assert (m["template_id"], m["template_version"]) == ("sys.hwax.deliberation", 2)


def test_리스크_앱이_일부러_고른_틀은_덮지_않는다(box):
    box({"deliberation": ROW})
    m = RR._material(_mat(tid="risk.custom", ver=4))
    assert (m["template_id"], m["template_version"]) == ("risk.custom", 4)


# ── 창구 — 게시판 · 미리보기 · 게시 ──────────────────────────────────────────────────────────────────────────
def _preview(board="sys-hwax", *, audience=42, already=False, blocked=None, token="tok-1"):
    return httpx.Response(200, json={"success": True, "data": {
        "report_id": 7, "targets": [{"slug": board, "name": "HWAX 심의", "parent_slug": None, "audience": audience,
                                     "descendant_boards": 0, "already_mounted": already, "blocked": blocked}],
        "confirm_token": None if blocked else token}})


@pytest.fixture()
def ra(monkeypatch, tmp_path, box):
    s = Settings(_env_file=None, ra_base_url="http://ra.test", ra_sso_secret="", upload_staging_dir=str(tmp_path / "st"))
    who = {"p": PARK}
    st = {"preview": _preview(), "mount": httpx.Response(200, json={"success": True, "data": {"items": []}}), "seen": []}
    app.dependency_overrides[get_settings] = lambda: s
    app.dependency_overrides[principal_pat_or_session] = lambda: who["p"]
    app.dependency_overrides[require_csrf] = lambda: None

    def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content or b"{}")
        st["seen"].append({"path": req.url.path, "body": body, "auth": req.headers.get("authorization"),
                           "ws": req.headers.get("x-workspace-slug"), "client": req.headers.get("x-client")})
        r = st["preview"] if req.url.path == "/api/mounts/preview" else st["mount"] if req.url.path == "/api/mounts" else None
        if isinstance(r, Exception):
            raise r
        return r or httpx.Response(404, json={"success": False})

    real = httpx.AsyncClient
    monkeypatch.setattr(R.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    with TestClient(app, follow_redirects=False) as c:
        app.state.user_store.set_connection(email=PARK.email, service="reportarchive", token="rat_park", workspace="team-cae")
        yield {"c": c, "who": who, "st": st, "box": box}
    for dep in (get_settings, principal_pat_or_session, require_csrf):
        app.dependency_overrides.pop(dep, None)


def test_게시판을_정하지_않은_박스는_단추도_게시도_없다(ra):
    assert ra["c"].get("/agent/ra/post-target").json() == {"board": None}
    for r in (ra["c"].get("/agent/ra/reports/7/post-preview"), ra["c"].post("/agent/ra/reports/7/post")):
        assert r.status_code == 409 and r.json()["code"] == "no_board"
    assert ra["st"]["seen"] == []


def test_미리보기는_게시판_이름과_볼_사람_수만_내고_토큰은_내지_않는다(ra):
    ra["box"]({"deliberation": ROW})
    assert ra["c"].get("/agent/ra/post-target").json() == {"board": "sys-hwax"}
    j = ra["c"].get("/agent/ra/reports/7/post-preview").json()
    assert j == {"board": "sys-hwax", "ok": True, "targets": [
        {"slug": "sys-hwax", "name": "HWAX 심의", "audience": 42, "already_mounted": False, "blocked": None}]}
    assert "tok-1" not in json.dumps(j)
    assert ra["st"]["seen"] == [{"path": "/api/mounts/preview", "body": {"report_id": 7, "workspace_slugs": ["sys-hwax"]},
                                 "auth": "Bearer rat_park", "ws": "team-cae", "client": None}], "그 사람 토큰 · 박스의 게시판으로만"


def test_게시는_미리보기를_다시_받아_그_토큰과_함께_박스의_게시판에만(ra):
    ra["box"]({"deliberation": ROW})
    r = ra["c"].post("/agent/ra/reports/7/post", json={"board": "top-division"})     # 화면이 보낸 게시판은 쓰지 않는다
    assert r.status_code == 200 and r.json() == {"board": "sys-hwax", "name": "HWAX 심의", "mounted": True, "already": False}
    paths = [s["path"] for s in ra["st"]["seen"]]
    assert paths == ["/api/mounts/preview", "/api/mounts"]
    mount = ra["st"]["seen"][1]["body"]
    assert mount["workspace_slugs"] == ["sys-hwax"] and mount["confirm_token"] == "tok-1" and mount["report_id"] == 7


def test_이미_게시됐으면_다시_게시하지_않는다(ra):
    ra["box"]({"deliberation": ROW})
    ra["st"]["preview"] = _preview(already=True)
    assert ra["c"].post("/agent/ra/reports/7/post").json()["already"] is True
    assert [s["path"] for s in ra["st"]["seen"]] == ["/api/mounts/preview"]


def test_못_올리는_게시판이면_게시하지_않고_까닭을(ra):
    ra["box"]({"deliberation": ROW})
    ra["st"]["preview"] = _preview(blocked="이 게시판에 게시 권한이 없습니다")
    r = ra["c"].post("/agent/ra/reports/7/post")
    assert r.status_code == 409 and "권한이 없습니다" in r.json()["detail"]
    assert [s["path"] for s in ra["st"]["seen"]] == ["/api/mounts/preview"]
    assert ra["c"].get("/agent/ra/reports/7/post-preview").json()["ok"] is False


@pytest.mark.parametrize("st,code", [(401, "ra_token_rejected"), (403, "forbidden_by_ra"), (404, "not_found"), (422, "ra_rejected"),
                                     (500, "ra_error")])
def test_RA_의_거절은_정해진_낱말로(ra, st, code):
    ra["box"]({"deliberation": ROW})
    ra["st"]["mount"] = httpx.Response(st, json={"success": False, "message": "거절"})
    r = ra["c"].post("/agent/ra/reports/7/post")
    assert r.json()["code"] == code


def test_게시_답을_잃으면_게시됐는지_모른다고_말한다(ra):
    ra["box"]({"deliberation": ROW})
    ra["st"]["mount"] = httpx.ReadTimeout("느림")
    r = ra["c"].post("/agent/ra/reports/7/post")
    assert r.status_code == 502 and r.json()["code"] == "ra_outcome_unknown"


def test_RA_연결이_없으면_RA_를_부르지_않는다(ra):
    ra["box"]({"deliberation": ROW})
    ra["who"]["p"] = Principal(subject="no-ra-post@corp.com", email="no-ra-post@corp.com", display_name="없음", groups=["plat:reportarchive"])
    r = ra["c"].post("/agent/ra/reports/7/post")
    assert r.json()["code"] == "no_ra_connection" and ra["st"]["seen"] == []


def test_RA_권한이_없으면_막는다(ra):
    ra["box"]({"deliberation": ROW})
    ra["who"]["p"] = Principal(subject="park-post@corp.com", email="park-post@corp.com", display_name="박", groups=[])
    for r in (ra["c"].get("/agent/ra/post-target"), ra["c"].get("/agent/ra/reports/7/post-preview"), ra["c"].post("/agent/ra/reports/7/post")):
        assert r.status_code == 403
    assert ra["st"]["seen"] == []


def test_게시는_CSRF_를_요구한다(ra):
    ra["box"]({"deliberation": ROW})
    app.dependency_overrides.pop(require_csrf, None)
    assert ra["c"].post("/agent/ra/reports/7/post").status_code == 403 and ra["st"]["seen"] == []


# ── Claude 워크플로(RS-6) ─────────────────────────────────────────────────────────────────────────────────
def test_워크플로는_형식을_박지_않고_게이트웨이에_묻고_게시는_안내만_한다():
    js = (ROOT / "infra" / "pipeline" / "hwax-deliberate.js").read_text(encoding="utf-8")
    # create_report_draft 인자에 형식을 글자로 박으면 박스 파일을 따라가지 않는 자리가 남는다(도구가 없을 때 돌아갈 기본값 안내는 괜찮다)
    assert '인자: template_id="deliberation"' not in js and js.count('인자: template_id="${FMT.template_id}"') == 2
    assert 'ra_report_format(kind="deliberation")' in js and "FMT.template_id" in js
    assert "raPost," in js and "publish_report(" in js and "확인 없이 게시하지 않는다" in js
    assert "publish_report(report_id" not in js.split("how:")[0], "워크플로가 스스로 게시하지 않는다 — 안내(how)에만 있다"
    assert "/^" + P._BOARD_RE.pattern + "$/" in js, "게시판 꼴이 포털 · 게이트웨이와 같다"
