# RA 연결의 조직(워크스페이스) 선택 — 후보 정렬·기본값·검증·슬러그만 변경
import pytest

from app.auth.errors import AuthError
from app.auth.routes.connections import (
    _pick_default_workspace,
    _validate_workspace,
    _workspace_options,
)
from app.auth.user_store import UserStore
from app.config import Settings


# RA /api/me 실응답 모양(2026-09-09 실측, dev@hwax.local).
_ME = {
    "home_workspace_slug": "dev",
    "memberships": [
        {"workspace_slug": "personal-2", "workspace_kind": "personal",
         "workspace_name": "Dev Admin (개인)", "role": "manager"},
        {"workspace_slug": "dev", "workspace_kind": "org",
         "workspace_name": "Dev (개발)", "role": "manager"},
    ],
}


# ── 후보 목록 ────────────────────────────────────────────────────────────────
def test_options_put_org_first_and_flag_personal():
    opts = _workspace_options(_ME)
    assert [w["slug"] for w in opts] == ["dev", "personal-2"]   # 조직이 앞
    assert opts[0]["personal"] is False and opts[1]["personal"] is True
    assert opts[0]["name"] == "Dev (개발)"


def test_options_treat_personal_prefix_as_personal_even_without_kind():
    me = {"memberships": [{"workspace_slug": "personal-9", "workspace_name": "개인"}]}
    assert _workspace_options(me)[0]["personal"] is True


def test_options_skip_rows_without_slug():
    me = {"memberships": [{"workspace_name": "이름만"}, {"workspace_slug": "  "}]}
    assert _workspace_options(me) == []


# ── 기본값 ───────────────────────────────────────────────────────────────────
def test_default_prefers_org_even_when_home_is_personal():
    """⚠ 회귀 방지 — 예전엔 home_workspace_slug 를 그대로 썼다. home 이 개인이면
    개인 워크스페이스가 박히고 화면에 바꿀 방법이 없어 보고서가 개인함에 계속 쌓였다."""
    me = {**_ME, "home_workspace_slug": "personal-2"}
    assert _pick_default_workspace(me, _workspace_options(me)) == "dev"


def test_default_respects_home_when_home_is_an_org():
    me = {
        "home_workspace_slug": "mx",
        "memberships": [
            {"workspace_slug": "dev", "workspace_kind": "org", "workspace_name": "D"},
            {"workspace_slug": "mx", "workspace_kind": "org", "workspace_name": "M"},
        ],
    }
    assert _pick_default_workspace(me, _workspace_options(me)) == "mx"


def test_default_falls_back_to_personal_only_when_no_org_exists():
    me = {"home_workspace_slug": "personal-2",
          "memberships": [{"workspace_slug": "personal-2", "workspace_kind": "personal"}]}
    assert _pick_default_workspace(me, _workspace_options(me)) == "personal-2"


def test_default_is_empty_when_there_is_nothing_to_pick():
    assert _pick_default_workspace({}, []) == ""


# ── 검증 ─────────────────────────────────────────────────────────────────────
def test_validate_accepts_a_real_membership():
    assert _validate_workspace("dev", _workspace_options(_ME)) == "dev"


def test_validate_rejects_a_slug_the_account_is_not_in():
    """오타를 저장하면 등록은 성공한 것처럼 끝나는데 보고서는 어디에도 안 보인다 —
    실패가 성공과 똑같이 생기는 그 부류다. 여기서 막는다."""
    with pytest.raises(AuthError) as e:
        _validate_workspace("dev-typo", _workspace_options(_ME))
    assert "dev" in str(e.value.detail if hasattr(e.value, "detail") else e.value)


def test_validate_allows_empty_as_unset():
    # 빈 값은 '지정 안 함' 이다 — 게이트웨이가 헤더를 지워 RA 기본 워크스페이스로 간다.
    assert _validate_workspace("", _workspace_options(_ME)) == ""
    assert _validate_workspace("   ", _workspace_options(_ME)) == ""


def test_validate_allows_personal_when_explicitly_chosen():
    # 기본값은 안 되지만, 알고 고르는 것은 사용자의 선택이다.
    assert _validate_workspace("personal-2", _workspace_options(_ME)) == "personal-2"


# ── 저장소 ───────────────────────────────────────────────────────────────────
def _store(tmp_path) -> UserStore:
    return UserStore(Settings(user_store_path=str(tmp_path / "users.sqlite")))


def test_workspace_can_change_without_touching_the_token(tmp_path):
    st = _store(tmp_path)
    st.set_connection(email="A@x.com", service="reportarchive", token="rat_secret", workspace="dev")
    assert st.set_connection_workspace(email="a@x.com", service="reportarchive", workspace="mx")
    conn = st.get_connection(email="a@x.com", service="reportarchive")
    assert conn == {"token": "rat_secret", "workspace": "mx"}   # 토큰 그대로


def test_workspace_update_on_missing_connection_reports_false(tmp_path):
    st = _store(tmp_path)
    assert not st.set_connection_workspace(email="none@x.com", service="reportarchive",
                                           workspace="dev")


def test_connection_meta_never_exposes_the_token(tmp_path):
    st = _store(tmp_path)
    st.set_connection(email="a@x.com", service="reportarchive", token="rat_verysecret",
                      workspace="dev")
    meta = st.connection_meta(email="a@x.com", service="reportarchive")
    assert meta["tail"] == "cret" and "token" not in meta
    assert meta["workspace"] == "dev"


# ── 게이트웨이 캐시 무효화 — 실패해도 설정 변경을 막지 않는다 ─────────────────
def test_invalidate_is_skipped_when_gateway_is_not_configured():
    """공유 토큰이나 주소가 없으면 조용히 건너뛴다(예외로 설정 변경을 죽이지 않는다)."""
    import asyncio

    from app.auth.routes.connections import _invalidate_gateway_cache

    asyncio.run(_invalidate_gateway_cache(Settings(gateway_shared_token=""), "a@x.com"))


def test_invalidate_swallows_transport_errors(monkeypatch):
    """게이트웨이가 죽어 있어도 조직 변경은 성공해야 한다 — TTL 지나면 어차피 반영된다."""
    import asyncio

    import httpx

    from app.auth.routes import connections as C

    class _Boom:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, *a, **kw):
            raise httpx.ConnectError("refused")

    monkeypatch.setattr(C.httpx, "AsyncClient", lambda **kw: _Boom())
    asyncio.run(C._invalidate_gateway_cache(
        Settings(gateway_shared_token="t", mcp_gateway_url="http://127.0.0.1:9"), "a@x.com"))


def test_invalidate_targets_the_changed_user_only(monkeypatch):
    import asyncio

    from app.auth.routes import connections as C

    seen: dict = {}

    class _Cli:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, params=None, headers=None):
            seen["url"], seen["params"], seen["headers"] = url, params, headers

            class _R:
                status_code = 200
            return _R()

    monkeypatch.setattr(C.httpx, "AsyncClient", lambda **kw: _Cli())
    asyncio.run(C._invalidate_gateway_cache(
        Settings(gateway_shared_token="gw-tok", mcp_gateway_url="http://gw:9110/"), "a@x.com"))
    assert seen["url"] == "http://gw:9110/conn-invalidate"
    assert seen["params"] == {"email": "a@x.com"}      # 남의 캐시까지 날리지 않는다
    assert seen["headers"]["Authorization"] == "Bearer gw-tok"
