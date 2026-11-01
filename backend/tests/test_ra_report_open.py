# RA 보고서를 그 보고서의 공간 주소로 여는 포털 길(/agent/ra/reports/{id}/open) — 심의 결과 카드가 공간 이름 'dev' 를 박았다(docs/wda-deck WD-D67)
"""왜 — RA 화면에는 공간 없는 보고서 주소가 없다(/w/<공간>/reports/<번호> 뿐 — ReportArchive frontend App.jsx). 심의 결과 카드는
`/report-archive/w/dev/reports/<번호>` 를 박아 dev 가 아닌 박스 · 다른 공간의 보고서가 열리지 않았다. 포털이 그 사람 명의로 보고서를 읽어
workspace_slug 를 받아 옮긴다 — 못 읽으면 그 사람의 RA 연결에 묶인 공간, 그것도 없으면 RA 첫 화면.
"""
import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.agent import routes as R
from app.auth.provider import Principal
from app.config import Settings, get_settings
from app.deps import principal_pat_or_session
from app.main import app

KIM = Principal(subject="kim@corp.com", email="kim@corp.com", display_name="김", groups=["plat:reportarchive"])


@pytest.fixture()
def ra(monkeypatch, tmp_path):
    s = Settings(_env_file=None, ra_base_url="http://ra.test", ra_sso_secret="", upload_staging_dir=str(tmp_path / "st"))
    who = {"p": KIM}
    reports: dict[int, httpx.Response] = {}
    seen: list[dict] = []
    app.dependency_overrides[get_settings] = lambda: s
    app.dependency_overrides[principal_pat_or_session] = lambda: who["p"]

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append({"auth": req.headers.get("authorization"), "ws": req.headers.get("x-workspace-slug")})
        rid = int(req.url.path.rsplit("/", 1)[1])
        return reports.get(rid) or httpx.Response(404, json={"success": False, "message": "Report not found"})

    real = httpx.AsyncClient
    monkeypatch.setattr(R.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    with TestClient(app, follow_redirects=False) as c:
        yield {"c": c, "who": who, "reports": reports, "seen": seen}
    app.dependency_overrides.pop(get_settings, None)
    app.dependency_overrides.pop(principal_pat_or_session, None)


def _report(slug: str) -> httpx.Response:
    return httpx.Response(200, content=json.dumps({"success": True, "data": {"id": 58, "workspace_slug": slug, "title": "t"}}).encode())


def test_그_보고서의_공간으로_옮긴다_그_사람_토큰으로(ra):
    app.state.user_store.set_connection(email="kim@corp.com", service="reportarchive", token="rat_kim", workspace="personal-5")
    ra["reports"][58] = _report("team-cae")
    r = ra["c"].get("/agent/ra/reports/58/open")
    assert r.status_code == 302 and r.headers["location"] == "/report-archive/w/team-cae/reports/58"
    assert ra["seen"] == [{"auth": "Bearer rat_kim", "ws": "personal-5"}], "그 사람의 RA 토큰으로(서비스 계정 없음)"


def test_못_읽으면_연결의_공간_그것도_없으면_RA_첫_화면(ra):
    app.state.user_store.set_connection(email="kim@corp.com", service="reportarchive", token="rat_kim", workspace="personal-5")
    r = ra["c"].get("/agent/ra/reports/58/open")                         # RA 404
    assert r.status_code == 302 and r.headers["location"] == "/report-archive/w/personal-5/reports/58"
    app.state.user_store.set_connection(email="kim@corp.com", service="reportarchive", token="rat_kim", workspace="")
    assert ra["c"].get("/agent/ra/reports/58/open").headers["location"] == "/report-archive/"


def test_RA_연결이_없으면_RA_첫_화면(ra):
    # 다른 시험이 남긴 연결과 섞이지 않게 이 시험에만 쓰는 사람
    ra["who"]["p"] = Principal(subject="no-ra-link@corp.com", email="no-ra-link@corp.com", display_name="연결 없음",
                               groups=["plat:reportarchive"])
    r = ra["c"].get("/agent/ra/reports/58/open")
    assert r.status_code == 302 and r.headers["location"] == "/report-archive/" and ra["seen"] == []


@pytest.mark.parametrize("slug", ["../admin", "a/b", "", "x" * 121, "w?x=1"])
def test_공간_이름이_주소를_바꿀_꼴이면_쓰지_않는다(ra, slug):
    app.state.user_store.set_connection(email="kim@corp.com", service="reportarchive", token="rat_kim", workspace="")
    ra["reports"][58] = _report(slug)
    assert ra["c"].get("/agent/ra/reports/58/open").headers["location"] == "/report-archive/"


def test_권한이_없으면_403_이고_번호는_양의_정수만(ra):
    assert ra["c"].get("/agent/ra/reports/0/open").status_code == 422
    ra["who"]["p"] = Principal(subject="kim@corp.com", email="kim@corp.com", display_name="김", groups=[])
    assert ra["c"].get("/agent/ra/reports/58/open").status_code == 403


def test_심의_결과_카드는_공간을_박지_않고_포털_길로_연다():
    src = (Path(__file__).resolve().parents[2] / "frontend" / "src" / "components" / "chat" / "DelibView.tsx").read_text(encoding="utf-8")
    assert "/report-archive/w/dev/" not in src and "/agent/ra/reports/${o.report_id}/open" in src
