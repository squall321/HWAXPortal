# 챗 첫 화면의 '내 부서' — 그 사람의 RA 홈 부서와 그 위 사슬을 읽는 포털 길(/agent/ra/home — docs/ra-chat RC-2 ~ RC-6)
"""왜 — 첫 화면에 나의 Report Archive 조직(파트 · 그룹)을 표기하고 「내 부서 최근 이슈」 제시어를 처음부터 낸다(사용자 요청 2026-11-26).
소속의 정본은 RA 의 홈 부서(`/api/me` home_workspace_slug)이고, 위계는 `/api/workspaces` 의 parent_slug 사슬이다. 못 받으면 카드 없이
그대로 뜬다 — 오류를 띄우지 않고 {"home": null, "reason"} 을 200 으로 준다.
"""
import httpx
import pytest
from fastapi.testclient import TestClient

from app.agent import routes as R
from app.auth.provider import Principal
from app.config import Settings, get_settings
from app.deps import principal_pat_or_session
from app.main import app

LEE = Principal(subject="lee-home@corp.com", email="lee-home@corp.com", display_name="이", groups=["plat:reportarchive"])

TREE = [
    {"slug": "div-mx", "name": "MX사업부", "parent_slug": None, "kind": "virtual"},
    {"slug": "grp-cae", "name": "CAE그룹", "parent_slug": "div-mx", "kind": "org"},
    {"slug": "part-drop", "name": "낙하파트", "parent_slug": "grp-cae", "kind": "org"},
    {"slug": "personal-7", "name": "이 (개인)", "parent_slug": None, "kind": "personal"},
]


@pytest.fixture()
def ra(monkeypatch, tmp_path):
    s = Settings(_env_file=None, ra_base_url="http://ra.test", ra_sso_secret="", upload_staging_dir=str(tmp_path / "st"))
    who = {"p": LEE}
    st = {"me": httpx.Response(200, json={"success": True, "data": {"home_workspace_slug": "part-drop"}}),
          "ws": httpx.Response(200, json={"success": True, "data": TREE}), "seen": []}
    app.dependency_overrides[get_settings] = lambda: s
    app.dependency_overrides[principal_pat_or_session] = lambda: who["p"]

    def handler(req: httpx.Request) -> httpx.Response:
        st["seen"].append({"path": req.url.path, "auth": req.headers.get("authorization"), "ws": req.headers.get("x-workspace-slug")})
        r = st["me"] if req.url.path == "/api/me" else st["ws"] if req.url.path == "/api/workspaces" else None
        if isinstance(r, Exception):
            raise r
        return r or httpx.Response(404, json={"success": False})

    real = httpx.AsyncClient
    monkeypatch.setattr(R.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    with TestClient(app, follow_redirects=False) as c:
        # 원장은 기동 뒤에 생긴다 — 연결은 그 안에서 단다
        app.state.user_store.set_connection(email=LEE.email, service="reportarchive", token="rat_lee", workspace="personal-7")
        yield {"c": c, "who": who, **{"st": st}}
    app.dependency_overrides.pop(get_settings, None)
    app.dependency_overrides.pop(principal_pat_or_session, None)


def _get(ra) -> dict:
    r = ra["c"].get("/agent/ra/home")
    assert r.status_code == 200, r.text
    return r.json()


def test_홈_부서와_위_사슬을_위에서_아래로_그_사람_토큰으로(ra):
    j = _get(ra)
    assert j["home"] == {"slug": "part-drop", "name": "낙하파트", "kind": "org"}
    assert [n["name"] for n in j["chain"]] == ["MX사업부", "CAE그룹", "낙하파트"]
    assert [s["path"] for s in ra["st"]["seen"]] == ["/api/me", "/api/workspaces"]
    assert all(s["auth"] == "Bearer rat_lee" for s in ra["st"]["seen"]), "그 사람의 RA 토큰으로(서비스 계정 없음)"
    assert all(s["ws"] is None for s in ra["st"]["seen"]), "두 창구 모두 부서 머리 없이 — 연결에 묶인 개인 공간을 싣지 않는다"


def test_RA_연결이_없으면_카드_없이(ra):
    ra["who"]["p"] = Principal(subject="no-ra-home@corp.com", email="no-ra-home@corp.com", display_name="없음",
                               groups=["plat:reportarchive"])
    assert _get(ra) == {"home": None, "reason": "no_connection"} and ra["st"]["seen"] == []


@pytest.mark.parametrize("home", [None, "", "../admin", "a/b", "x" * 121, "ghost-ws"])
def test_홈_부서가_없거나_꼴이_틀리거나_보이지_않으면_카드_없이(ra, home):
    ra["st"]["me"] = httpx.Response(200, json={"success": True, "data": {"home_workspace_slug": home}})
    assert _get(ra) == {"home": None, "reason": "no_home"}


def test_홈이_개인_공간이면_카드_없이(ra):
    ra["st"]["me"] = httpx.Response(200, json={"success": True, "data": {"home_workspace_slug": "personal-7"}})
    assert _get(ra) == {"home": None, "reason": "no_home"}


@pytest.mark.parametrize("which", ["me", "ws"])
@pytest.mark.parametrize("bad", [httpx.Response(500, text="boom"), httpx.Response(200, text="not json"),
                                 httpx.Response(200, json=["list"]), httpx.ConnectError("down")])
def test_RA_가_실패하면_카드_없이_오류를_띄우지_않는다(ra, which, bad):
    ra["st"][which] = bad
    assert _get(ra) == {"home": None, "reason": "ra_error"}


def test_순환과_빠진_노드에서_멈춘다(ra):
    ra["st"]["ws"] = httpx.Response(200, json={"success": True, "data": [
        {"slug": "a", "name": "A", "parent_slug": "b", "kind": "org"},
        {"slug": "b", "name": "B", "parent_slug": "a", "kind": "org"},
        {"slug": "c", "name": "C", "parent_slug": "gone", "kind": "org"},
    ]})
    ra["st"]["me"] = httpx.Response(200, json={"success": True, "data": {"home_workspace_slug": "a"}})
    assert [n["slug"] for n in _get(ra)["chain"]] == ["b", "a"]
    ra["st"]["me"] = httpx.Response(200, json={"success": True, "data": {"home_workspace_slug": "c"}})
    assert [n["slug"] for n in _get(ra)["chain"]] == ["c"]


def test_깊은_나무는_상한에서_멈추고_꼴이_틀린_위_노드는_넣지_않는다(ra):
    rows = [{"slug": f"n{i}", "name": f"N{i}", "parent_slug": f"n{i + 1}", "kind": "org"} for i in range(20)]
    rows.append({"slug": "p1", "name": "P1", "parent_slug": "../x", "kind": "org"})
    rows.append({"slug": "../x", "name": "X", "parent_slug": None, "kind": "org"})
    ra["st"]["ws"] = httpx.Response(200, json={"success": True, "data": rows})
    ra["st"]["me"] = httpx.Response(200, json={"success": True, "data": {"home_workspace_slug": "n0"}})
    chain = _get(ra)["chain"]
    assert len(chain) == R._RA_HOME_DEPTH and chain[-1]["slug"] == "n0"
    ra["st"]["me"] = httpx.Response(200, json={"success": True, "data": {"home_workspace_slug": "p1"}})
    assert [n["slug"] for n in _get(ra)["chain"]] == ["p1"]


def test_items_로_감싼_목록도_받는다(ra):
    ra["st"]["ws"] = httpx.Response(200, json={"success": True, "data": {"items": TREE}})
    assert _get(ra)["home"]["slug"] == "part-drop"


def test_RA_권한이_없으면_막는다(ra):
    ra["who"]["p"] = Principal(subject="lee-home@corp.com", email="lee-home@corp.com", display_name="이", groups=[])
    assert ra["c"].get("/agent/ra/home").status_code == 403 and ra["st"]["seen"] == []
