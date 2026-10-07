# 언제나 관리자(PORTAL_ADMIN_EMAILS)와 관리자 지정·해제 화면 — 관리자가 원장 값 하나로만 유지되고 바꿀 길도 없었다(10차 요청 §3)
"""관리자 근거가 원장 `groups` 의 `portal-admin` 하나였고, 활성 사용자의 그 값을 바꾸는 라우트가 없었다(`set_groups` 호출부 0).
그 값이 지워지면 화면으로는 되돌릴 수 없다.

여기서 고정하는 것.
  · 고정 목록 — 원장 행의 이메일이 목록에 **글자 그대로** 있으면 요청마다 관리자다. 정지가 먼저고, 원장에 행이 없는 신원은
    목록에 있어도 아니다. 별칭 도메인은 같은 사람으로 보지 않는다(같은 로컬파트의 다른 사람이 관리자가 된다).
  · 지정·해제 — 관리자만. 해제하면 그 사람의 토큰을 폐기한다. 자기 자신과 마지막 관리자는 해제하지 못한다.
    고정 관리자는 화면에서 해제하지 못한다(박스 설정이다) — 됐다고 답하고 그대로 관리자인 응답을 내지 않는다.

원장·토큰 저장소는 전부 임시 폴더에 만든다. 주소는 지어낸 값이다.
"""
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient

from app.access import routes as access_routes
from app.access.policy import ADMIN_GROUP, AccessPolicy, compute
from app.auth.cookies import CSRF_COOKIE, SESSION_COOKIE
from app.auth.mock_provider import MockProvider
from app.auth.provider import Principal
from app.auth.token_store import TokenStore
from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.deps import get_current_principal
from app.main import app

GW = {"Authorization": "Bearer gw-test-secret"}
PW = "pw123456"
USERS = "/auth/local/users"            # require_role(portal-admin) — 관리자인지 재는 문


@pytest.fixture()
def box(tmp_path, monkeypatch):
    """boss = 원장 관리자 · user·pin = 활성 일반 사용자 · wait = 승인 대기."""
    monkeypatch.delenv("PORTAL_ADMIN_EMAILS", raising=False)
    s = Settings(_env_file=None, user_store_path=str(tmp_path / "users.sqlite"),
                 token_store_path=str(tmp_path / "tokens.sqlite"), upload_staging_dir=str(tmp_path / "staging"),
                 local_bootstrap_admins="boss@corp.com", gateway_shared_token="gw-test-secret")
    app.dependency_overrides[get_settings] = lambda: s
    from app.auth.routes.local import _rl
    _rl.clear()
    with TestClient(app) as c:
        keep = (app.state.user_store, app.state.token_store, app.state.auth_provider)
        app.state.user_store, app.state.token_store = UserStore(s), TokenStore(s)   # 기동 뒤 교체 — 실 저장소를 안 쓴다
        for email in ("boss@corp.com", "user@corp.com", "pin@corp.com", "wait@corp.com"):
            c.post("/auth/local/signup", json={"email": email, "name": email.split("@")[0], "password": PW})
        for email in ("user@corp.com", "pin@corp.com"):
            assert app.state.user_store.approve(email, by="boss@corp.com", groups=[])
        yield c, s
        app.state.user_store, app.state.token_store, app.state.auth_provider = keep
    app.dependency_overrides.pop(get_settings, None)
    app.dependency_overrides.pop(get_current_principal, None)


def _pin(s: Settings, *emails: str) -> None:
    s.portal_admin_emails = ",".join(emails)


def _login(c, email) -> dict:
    c.cookies.clear()
    assert c.post("/auth/local/login", json={"email": email, "password": PW}).status_code == 200
    return {"X-CSRF-Token": c.cookies.get(CSRF_COOKIE)}


def _wear(c, email: str) -> dict:
    """SSO 로 들어온 그 사람의 브라우저가 된다(비밀번호 로그인이 안 되는 행 — 원장에 없거나 승인 대기 — 도 IdP 는 통과한다)."""
    c.cookies.clear()
    c.cookies.set(SESSION_COOKIE, app.state.jwt_service.issue_session(Principal(subject=email, email=email)))
    c.cookies.set(CSRF_COOKIE, "t")
    return {"X-CSRF-Token": "t"}


def _groups(email: str) -> list[str]:
    return app.state.user_store.get(email)["groups"]


def _set_admin(c, h, email: str, on: bool):
    return c.patch(f"/auth/access/users/{email}", json={"admin": on}, headers=h)


def _ent(c, email: str) -> dict:
    return c.get("/internal/access/entitlements", params={"email": email}, headers=GW).json()


# ── 설정 ─────────────────────────────────────────────────────────────────────
def test_목록은_콤마로_나누고_소문자로_맞춘다(monkeypatch):
    monkeypatch.delenv("PORTAL_ADMIN_EMAILS", raising=False)
    assert Settings(_env_file=None).portal_admin_email_set == frozenset(), "기본은 꺼짐"
    s = Settings(_env_file=None, portal_admin_emails=" Pin@Corp.com ,, other@corp.com ,")
    assert s.portal_admin_email_set == {"pin@corp.com", "other@corp.com"}
    monkeypatch.setenv("PORTAL_ADMIN_EMAILS", "env@corp.com")
    assert Settings(_env_file=None).portal_admin_email_set == {"env@corp.com"}


# ── 판정 ─────────────────────────────────────────────────────────────────────
def test_고정_목록은_원장_행의_이메일로만_견준다():
    pol = AccessPolicy(Settings(_env_file=None)).get()
    pinned = frozenset({"pin@corp.com"})
    on = compute(pol, groups=[], row={"email": "pin@corp.com", "groups": [], "status": "active"}, admin_emails=pinned)
    assert on.is_admin is True and on.keys == set(pol.keys) and set(on.reasons.values()) == {"admin"}
    # 목록을 안 넘긴 호출부는 관리자로 보지 않는다(잊으면 닫히는 쪽)
    assert compute(pol, groups=[], row={"email": "pin@corp.com", "groups": []}).is_admin is False
    # 원장에 행이 없으면 목록에 있어도 아니다 — 토큰이 무엇을 들고 와도
    assert compute(pol, groups=[ADMIN_GROUP], row=None, admin_emails=pinned).is_admin is False
    # 정지가 먼저다
    off = compute(pol, groups=[], row={"email": "pin@corp.com", "groups": [], "status": "disabled"}, admin_emails=pinned)
    assert off.is_admin is False and off.keys == set()
    # 별칭 도메인·비슷한 주소는 다른 사람이다
    for other in ("pin@ax.corp.com", "pin@corp.com.evil.example", "xpin@corp.com", "pin", ""):
        row = {"email": other, "groups": [], "status": "active"}
        assert compute(pol, groups=[], row=row, admin_emails=pinned).is_admin is False, other


# ── 요청마다 ─────────────────────────────────────────────────────────────────
def test_고정_관리자는_원장을_고치지_않고_요청마다_관리자다(box):
    c, s = box
    _login(c, "pin@corp.com")
    assert c.get(USERS).status_code == 403, "대조군 — 목록에 넣기 전에는 일반 사용자다"
    _pin(s, "other@corp.com", "Pin@Corp.com")
    assert c.get(USERS).status_code == 200, "재로그인 없이 다음 요청부터"
    assert ADMIN_GROUP in c.get("/auth/me").json()["groups"]
    assert c.get("/auth/access").json()["is_admin"] is True
    got = _ent(c, "pin@corp.com")
    assert got["is_admin"] is True and "plat:stepforge" in got["keys"], "게이트웨이도 같은 답을 받는다"
    assert _groups("pin@corp.com") == [], "원장에 적지 않는다 — 목록에서 빼면 그 순간 끝나야 한다"
    _pin(s)
    assert c.get(USERS).status_code == 403
    assert _ent(c, "pin@corp.com")["is_admin"] is False


def test_고정_관리자는_PAT_로_와도_관리자다(box):
    """PAT 를 받는 문은 세션과 다른 자리에서 권한을 계산한다 — 거기서 목록을 빼먹으면 화면에서는 관리자인데 토큰으로는 아니다.
    업로드 수신은 기본 설정이 관리자 그룹(UPLOAD_ALLOWED_GROUPS=portal-admin)에게 연다."""
    c, s = box
    ks = app.state.keystore
    now = datetime.now(tz=UTC)
    pat = jwt.encode({"iss": s.jwt_issuer, "sub": "pin@corp.com", "email": "pin@corp.com", "groups": [],
                      "aud": [s.pat_chat_audience], "scope": "api", "iat": now, "nbf": now,
                      "exp": now + timedelta(days=1), "jti": "pin-upload"},
                     ks.private_pem, algorithm="RS256", headers={"kid": ks.active_kid})
    files = {"file": ("t.csv", b"a,b\n1,2\n", "text/csv")}
    c.cookies.clear()
    bearer = {"Authorization": f"Bearer {pat}"}
    assert c.post("/agent/upload", files=files, headers=bearer).status_code == 403, "대조군 — 목록에 넣기 전"
    _pin(s, "pin@corp.com")
    assert c.post("/agent/upload", files=files, headers=bearer).status_code == 200
    # 같은 문을 세션 쿠키로 — PAT 가 없을 때의 갈래도 목록을 넘긴다
    h = _login(c, "pin@corp.com")
    assert c.post("/agent/upload", files=files, headers=h).status_code == 200


def test_원장에_행이_없는_신원은_목록에_있어도_관리자가_아니다(box):
    c, s = box
    _pin(s, "ghost@corp.com")
    _wear(c, "ghost@corp.com")
    assert c.get("/auth/me").status_code == 200, "원장에 없는 것은 정지가 아니다 — 로그인은 된다"
    assert c.get(USERS).status_code == 403
    assert _ent(c, "ghost@corp.com")["is_admin"] is False


def test_mock_박스는_고정_목록으로_관리자를_잇는다(box):
    """관리자를 IdP 그룹으로 받던 개발 박스(mock·oidc-mock)의 길 — 화면 점검(frontend/scripts/ui-check.sh)의 관리자 층도 이 길이다.
    첫 로그인이 원장 행을 만들고, 그 행의 이메일이 목록에 있으니 바로 다음 요청부터 관리자다."""
    c, s = box
    _pin(s, s.mock_user_email)
    assert app.state.user_store.get(s.mock_user_email) is None, "전제 — 처음 들어오는 사람"
    app.state.auth_provider = MockProvider(s)
    c.cookies.clear()
    r = c.get("/auth/login", follow_redirects=False)
    assert c.get(r.headers["location"], follow_redirects=False).status_code == 302
    assert c.get(USERS).status_code == 200
    assert ADMIN_GROUP in c.get("/auth/me").json()["groups"]


def test_정지가_고정_목록보다_먼저다(box):
    c, s = box
    _pin(s, "pin@corp.com")
    _login(c, "pin@corp.com")
    sess = c.cookies.get(SESSION_COOKIE)
    hb = _login(c, "boss@corp.com")
    assert c.post(f"{USERS}/pin@corp.com/status", json={"status": "disabled"}, headers=hb).status_code == 200
    c.cookies.clear()
    c.cookies.set(SESSION_COOKIE, sess)
    r = c.get(USERS)
    assert r.status_code == 403 and "정지" in r.text, r.text
    got = _ent(c, "pin@corp.com")
    assert got["is_admin"] is False and got["keys"] == []


def test_별칭_도메인의_같은_로컬파트는_다른_사람이다(box):
    c, s = box
    _pin(s, "user@ax.corp.com")
    _login(c, "user@corp.com")
    assert c.get(USERS).status_code == 403
    assert _ent(c, "user@corp.com")["is_admin"] is False


def test_권한을_다시_계산하는_자리도_목록을_본다(box, monkeypatch):
    """요청의 권한은 보통 한 번 계산해 둔 값(request.state)을 쓰지만, 그 값이 없을 때 '내 권한'·'허브에 보일 앱' 이 스스로
    다시 계산한다. 그 셋이 목록을 빼먹으면 같은 사람이 화면마다 다른 권한으로 보인다."""
    c, s = box
    _pin(s, "pin@corp.com")
    apps = [{"app": "ai-data-hub", "label": "AI 데이터 허브", "tool_count": 3, "reachable": True}]

    async def fake_apps(_settings):
        return apps

    async def no_invalidate(_settings, _email):
        return None

    monkeypatch.setattr(access_routes, "_gateway_apps", fake_apps)
    monkeypatch.setattr(access_routes, "_invalidate_gateway_cache", no_invalidate)
    # entitled 를 지나지 않은 신원 — request.state 에 계산값이 없다
    app.dependency_overrides[get_current_principal] = lambda: Principal(subject="pin@corp.com", email="pin@corp.com")
    c.cookies.set(CSRF_COOKIE, "t")
    h = {"X-CSRF-Token": "t"}

    def seen() -> tuple:
        return (c.get("/auth/access").json()["is_admin"],
                c.get("/auth/access/apps").json()["apps"][0]["allowed"],
                c.put("/auth/access/apps/ai-data-hub", json={"muted": False}, headers=h).json()["apps"][0]["allowed"])

    assert seen() == (True, True, True)
    _pin(s)
    assert seen() == (False, False, False), "대조군 — 목록에서 빼면 셋 다 일반 사용자다"


# ── 지정·해제 ────────────────────────────────────────────────────────────────
def test_지정과_해제는_곧바로_먹고_해제하면_그_사람의_토큰을_폐기한다(box):
    c, _s = box
    store, ts = app.state.user_store, app.state.token_store
    store.set_groups("user@corp.com", ["mes-user"])
    store.set_access("user@corp.com", grants=["feat:api-token"])
    hu = _login(c, "user@corp.com")
    sess = c.cookies.get(SESSION_COOKIE)
    jti = c.post("/auth/pat", json={"name": "t", "ttl_days": 30}, headers=hu).json()["jti"]

    hb = _login(c, "boss@corp.com")
    r = _set_admin(c, hb, "user@corp.com", True)
    assert r.status_code == 200 and r.json()["admin"] is True and r.json()["pats_revoked"] == 0, r.text
    assert _groups("user@corp.com") == ["mes-user", ADMIN_GROUP], "다른 그룹은 그대로 둔다"
    assert _set_admin(c, hb, "user@corp.com", True).status_code == 200
    assert _groups("user@corp.com") == ["mes-user", ADMIN_GROUP], "두 번 눌러도 한 번만 붙는다"
    assert jti not in ts.revoked_jtis(), "지정은 토큰을 건드리지 않는다"
    c.cookies.clear()
    c.cookies.set(SESSION_COOKIE, sess)
    assert c.get(USERS).status_code == 200, "들고 있던 세션이 재로그인 없이 관리자다"

    hb = _login(c, "boss@corp.com")
    r = _set_admin(c, hb, "user@corp.com", False)
    assert r.status_code == 200 and r.json()["admin"] is False and r.json()["pats_revoked"] == 1, r.text
    assert _groups("user@corp.com") == ["mes-user"]
    assert jti in ts.revoked_jtis(), "해제했는데 관리자이던 때의 PAT 가 살아 있다"
    c.cookies.clear()
    c.cookies.set(SESSION_COOKIE, sess)
    assert c.get(USERS).status_code == 403, "들고 있던 세션도 그 순간부터 아니다"

    # 이미 아닌 사람을 다시 해제 — 아무것도 안 한다(멀쩡한 토큰을 폐기하지 않는다)
    hu = _login(c, "user@corp.com")
    jti2 = c.post("/auth/pat", json={"name": "t2", "ttl_days": 30}, headers=hu).json()["jti"]
    hb = _login(c, "boss@corp.com")
    r = _set_admin(c, hb, "user@corp.com", False)
    assert r.status_code == 200 and r.json()["pats_revoked"] == 0 and jti2 not in ts.revoked_jtis()


def test_소속과_허가만_고치면_관리자_표지는_건드리지_않는다(box):
    c, _s = box
    hb = _login(c, "boss@corp.com")
    r = c.patch("/auth/access/users/boss@corp.com", json={"affiliation": "CAEG"}, headers=hb)
    assert r.status_code == 200 and r.json()["admin"] is True and _groups("boss@corp.com") == [ADMIN_GROUP]
    r = c.patch("/auth/access/users/user@corp.com", json={"grants": ["feat:deliberation"]}, headers=hb)
    assert r.status_code == 200 and r.json()["admin"] is False and _groups("user@corp.com") == []


def test_자기_자신의_관리자_권한은_해제하지_못한다(box):
    c, _s = box
    app.state.user_store.set_groups("user@corp.com", [ADMIN_GROUP])       # 관리자가 둘 — '마지막 관리자' 규칙이 아니다
    hb = _login(c, "boss@corp.com")
    r = _set_admin(c, hb, "Boss@Corp.com", False)
    assert r.status_code == 409 and "자기 자신" in r.json()["detail"], r.text
    assert _groups("boss@corp.com") == [ADMIN_GROUP] and c.get(USERS).status_code == 200


def test_마지막_관리자는_해제하지_못한다(box):
    """남는 관리자로 세는 것은 **활성 원장 행이 있는** 관리자다(원장 표지든 고정 목록이든). 목록에만 있고 승인되지 않은 계정은
    세지 않는다 — 비밀번호로는 들어오지 못하고, 그 주소가 맞는지도 확인된 적이 없다."""
    c, s = box
    store = app.state.user_store
    _pin(s, "wait@corp.com", "typo@corp.com")            # wait = 승인 대기 행, typo = 원장에 없는 주소
    h = _wear(c, "wait@corp.com")
    assert c.get(USERS).status_code == 200, "전제 — 목록에 있고 원장에 행이 있으면(정지가 아니면) 관리자다"
    r = _set_admin(c, h, "boss@corp.com", False)
    assert r.status_code == 409 and "마지막" in r.json()["detail"], r.text
    assert _groups("boss@corp.com") == [ADMIN_GROUP]
    # 저장소도 같은 판정을 잠금 안에서 한다 — 두 관리자가 서로를 동시에 해제해도 한 명은 남는다
    assert store.set_admin("boss@corp.com", False, pinned=s.portal_admin_email_set) == "last"
    assert store.set_admin("boss@corp.com", False) == "last"
    # 승인되어 활성이 되면 그 사람이 남는 관리자다
    assert store.approve("wait@corp.com", by="boss@corp.com")
    r = _set_admin(c, h, "boss@corp.com", False)
    assert r.status_code == 200 and _groups("boss@corp.com") == [], r.text
    # 정지된 고정 관리자는 남는 관리자가 아니다
    store.set_groups("boss@corp.com", [ADMIN_GROUP])
    store.set_status("wait@corp.com", "disabled")
    assert store.set_admin("boss@corp.com", False, pinned=s.portal_admin_email_set) == "last"


def test_고정_관리자는_화면에서_해제하지_못한다(box):
    """됐다고 답하고 그대로 관리자인 응답을 내지 않는다 — 어디서 바꾸는지 말한다."""
    c, s = box
    _pin(s, "pin@corp.com")
    store, ts = app.state.user_store, app.state.token_store
    ts.record_pat(jti="pin-pat", sub="pin@corp.com", email="pin@corp.com", name="t", aud=["mcp-gateway"],
                  scopes=["read"], created=1, exp=4102444800)
    hb = _login(c, "boss@corp.com")
    for ledger in ([], [ADMIN_GROUP]):                    # 원장에 표지가 있든 없든
        store.set_groups("pin@corp.com", ledger)
        r = _set_admin(c, hb, "pin@corp.com", False)
        assert r.status_code == 409 and "PORTAL_ADMIN_EMAILS" in r.json()["detail"], r.text
        assert _groups("pin@corp.com") == ledger and "pin-pat" not in ts.revoked_jtis()
    _pin(s)                                               # 목록에서 빼면 보통 관리자처럼 해제된다
    assert _set_admin(c, hb, "pin@corp.com", False).status_code == 200 and _groups("pin@corp.com") == []


def test_관리자가_아니면_지정도_해제도_못_한다(box):
    c, _s = box
    hu = _login(c, "user@corp.com")
    assert _set_admin(c, hu, "user@corp.com", True).status_code == 403, "스스로 관리자가 될 수 없다"
    assert _set_admin(c, hu, "boss@corp.com", False).status_code == 403
    assert _groups("user@corp.com") == [] and _groups("boss@corp.com") == [ADMIN_GROUP]


def test_지정은_활성_계정에만_하고_해제는_어느_상태든_된다(box):
    c, _s = box
    store = app.state.user_store
    hb = _login(c, "boss@corp.com")
    assert _set_admin(c, hb, "nobody@corp.com", True).status_code == 404
    r = _set_admin(c, hb, "wait@corp.com", True)
    assert r.status_code == 409 and _groups("wait@corp.com") == [], "승인 대기는 '관리자로 승인' 으로 간다"
    store.set_status("user@corp.com", "disabled")
    assert _set_admin(c, hb, "user@corp.com", True).status_code == 409 and _groups("user@corp.com") == []
    store.set_groups("user@corp.com", [ADMIN_GROUP])      # 정지된 채 표지가 남은 사람 — 떼는 것은 된다
    assert _set_admin(c, hb, "user@corp.com", False).status_code == 200 and _groups("user@corp.com") == []


def test_사용자_목록이_고정_관리자인지_알려_준다(box):
    c, s = box
    _pin(s, "PIN@corp.com", "user@ax.corp.com", "nobody@corp.com")
    _login(c, "boss@corp.com")
    rows = {u["email"]: u["admin_pinned"] for u in c.get(USERS).json()}
    assert rows == {"boss@corp.com": False, "user@corp.com": False, "pin@corp.com": True, "wait@corp.com": False}


# ── 정지 — 관리자 해제와 같은 구멍의 다른 문 ──────────────────────────────────────────────────────────
# 해제는 본인·마지막 관리자를 거절한다. 그런데 **정지**는 거절하지 않았다(화면만 본인 줄의 버튼을 숨겼다) — 정지된 관리자는 권한이
# 0 이라, 마지막 관리자가 자기를 정지하는 요청 한 번이면 관리자 화면을 열 사람이 없어지고 되돌리는 길은 박스의 셸뿐이다.
def _suspend(c, h, email: str):
    return c.post(f"{USERS}/{email}/status", json={"status": "disabled"}, headers=h)


def _status(email: str) -> str:
    return app.state.user_store.get(email)["status"]


def test_자기_자신은_정지할_수_없다(box):
    c, _s = box
    hb = _login(c, "boss@corp.com")
    r = _suspend(c, hb, "boss@corp.com")
    assert r.status_code == 409 and "자기 자신" in r.json()["detail"], r.text
    assert _status("boss@corp.com") == "active" and c.get(USERS).status_code == 200, "여전히 관리자다"
    assert _suspend(c, hb, "BOSS@corp.com").status_code == 409, "대소문자만 바꾼 주소도 본인이다"


def test_다른_관리자는_정지할_수_있고_정지는_토큰까지_죽인다(box):
    """막는 것은 본인과 마지막 관리자뿐이다 — 관리자 한 명을 정지하는 평소의 일은 그대로 된다."""
    c, _s = box
    app.state.user_store.set_groups("user@corp.com", [ADMIN_GROUP])
    hb = _login(c, "boss@corp.com")
    r = _suspend(c, hb, "user@corp.com")
    assert r.status_code == 200 and _status("user@corp.com") == "disabled", r.text
    assert _suspend(c, hb, "nobody@corp.com").status_code == 404
    assert c.post(f"{USERS}/user@corp.com/status", json={"status": "active"}, headers=hb).status_code == 200
    assert _status("user@corp.com") == "active", "다시 활성화는 종전대로"


def test_저장소는_마지막_활성_관리자의_정지를_잠금_안에서_거절한다(box):
    """라우트는 본인만 막으면 된다고 볼 수 있다 — 부른 사람이 남으니까. 두 관리자가 **서로를 동시에** 정지하면 각자 '상대가 남는다'
    로 보고 둘 다 통과한다. 판정과 쓰기를 저장소의 잠금 안에서 한 번에 한다(관리자 해제의 set_admin 과 같은 셈법)."""
    _c, _s = box
    store = app.state.user_store
    assert store.suspend("boss@corp.com") == "last" and _status("boss@corp.com") == "active"
    assert store.suspend("user@corp.com") == "set", "관리자가 아닌 사람은 언제나 정지된다"
    assert store.suspend("nobody@corp.com") == "missing"
    # 고정 목록의 활성 관리자가 남으면 원장 관리자를 정지할 수 있다 — 목록에만 있고 승인 대기인 주소는 세지 않는다
    assert store.suspend("boss@corp.com", pinned=frozenset({"wait@corp.com", "ghost@corp.com"})) == "last"
    assert store.suspend("boss@corp.com", pinned=frozenset({"pin@corp.com"})) == "set"
    # 이제 pin 이 마지막 활성 관리자다(고정 목록) — 정지는 고정보다 먼저라 정지하면 관리자가 0 이다
    assert store.suspend("pin@corp.com", pinned=frozenset({"pin@corp.com"})) == "last" and _status("pin@corp.com") == "active"
    assert store.suspend("pin@corp.com") == "set", "목록에서 빠진 사람은 관리자가 아니다 — 그냥 정지된다"


def test_마지막_관리자_정지_거절이_화면에_사유로_간다(box, monkeypatch):
    c, _s = box
    app.state.user_store.set_groups("user@corp.com", [ADMIN_GROUP])
    hb = _login(c, "boss@corp.com")
    monkeypatch.setattr(app.state.user_store, "suspend", lambda *a, **k: "last")      # 경합에서만 나는 갈래 — 저장소가 그렇게 답했다 치고
    r = _suspend(c, hb, "user@corp.com")
    assert r.status_code == 409 and "마지막 관리자" in r.json()["detail"], r.text

