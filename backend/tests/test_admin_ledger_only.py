# 관리자는 원장만 — 세션·refresh·PAT 에 박힌 portal-admin 은 판정에도 그룹에도 쓰지 않는다(10차 요청 §4)
"""관리자 여부를 '토큰이 들고 온 그룹 **또는** 원장' 으로 인정했었다. 그러면 관리자를 해제해도 그 사람이 이미 들고 있는
세션(8시간)·PAT(최대 36,500일)이 계속 관리자다 — mock 시절 공용 계정 PAT 가 2026-10-06 에도 쓰였다.

여기서 고정하는 것.
  · 판정 — 토큰의 `portal-admin` 은 원장 행에 그 그룹이 없으면(행이 아예 없어도) 관리자가 아니다. 원장 관리자는 그대로다.
  · 그룹 — 그 표지는 요청의 그룹에서도 빠진다(`require_role` 은 그룹을 본다 — 판정만 고치면 문이 그대로 열린다).
  · 발급 — 새로 내는 세션·refresh·PAT 에는 표지도 합성 그룹(feat:·plat:)도 박지 않는다.
  · 게이트웨이 — `/internal/access/entitlements` 가 `is_admin` 을 불리언으로 준다(게이트웨이가 이 이름으로 읽는다).

원장·토큰 저장소·업로드 폴더는 전부 임시 폴더에 만든다.
"""
import re
import secrets
import types
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient

from app.access.policy import ADMIN_GROUP, AccessPolicy, compute, with_entitlements
from app.agent.routes import _chat_user_pat
from app.auth.cookies import CSRF_COOKIE, REFRESH_COOKIE, SESSION_COOKIE
from app.auth.jwt_service import SESSION_AUDIENCE
from app.auth.mock_provider import MockProvider
from app.auth.provider import Principal
from app.auth.token_store import TokenStore
from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.main import app
from app.procedures.pat import mint as mint_procedure_pat

GW = {"Authorization": "Bearer gw-test-secret"}
PW = "pw123456"


@pytest.fixture()
def box(tmp_path, monkeypatch):
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
        c.post("/auth/local/signup", json={"email": "boss@corp.com", "name": "Boss", "password": PW})   # 부트스트랩 = 원장 관리자
        c.post("/auth/local/signup", json={"email": "user@corp.com", "name": "User", "password": PW})
        assert app.state.user_store.approve("user@corp.com", by="boss@corp.com", groups=[])
        yield c, s
        app.state.user_store, app.state.token_store, app.state.auth_provider = keep
    app.dependency_overrides.pop(get_settings, None)


def _login(c, email) -> dict:
    assert c.post("/auth/local/login", json={"email": email, "password": PW}).status_code == 200
    return {"X-CSRF-Token": c.cookies.get(CSRF_COOKIE)}


def _old_token(email: str, groups: list[str], typ: str = "session") -> str:
    """이 변경 **전**의 포털이 내던 세션·refresh — groups 를 그대로 박았다. 지금의 발급은 표지를 빼므로 같은 키로 직접 서명한다."""
    return app.state.jwt_service._encode(
        {"sub": email, "aud": SESSION_AUDIENCE, "email": email, "name": None, "groups": groups}, ttl=600, typ=typ)


def _old_pat(s: Settings, email: str, groups: list[str]) -> str:
    """관리자이던 때(또는 mock 시절) 받은 PAT — 포털 키로 서명됐고 폐기되지 않았다."""
    ks = app.state.keystore
    now = datetime.now(tz=UTC)
    return jwt.encode({"iss": s.jwt_issuer, "sub": email, "email": email, "name": None, "groups": groups,
                       "aud": [s.pat_chat_audience], "scope": "api", "scopes": ["read", "write"], "pat_name": "old",
                       "iat": now, "nbf": now, "exp": now + timedelta(days=30), "jti": "old-" + secrets.token_urlsafe(8)},
                      ks.private_pem, algorithm="RS256", headers={"kid": ks.active_kid})


def _wear(c, session: str) -> dict:
    """그 토큰을 든 브라우저가 된다. CSRF 는 double-submit 이라 같은 값을 쿠키·헤더에 실으면 된다."""
    c.cookies.clear()
    c.cookies.set(SESSION_COOKIE, session)
    c.cookies.set(CSRF_COOKIE, "t")
    return {"X-CSRF-Token": "t"}


def _admin_routes() -> list[tuple[str, str]]:
    """`require_role` 이 걸린 라우트 전부(메서드, 경로) — 목록을 적어 두지 않는다. 새 관리자 라우트가 생기면 저절로 따라온다."""
    def gated(dep) -> bool:
        return (getattr(dep.call, "__qualname__", "").startswith("require_role.")
                or any(gated(d) for d in dep.dependencies))

    out = []
    for r in app.routes:
        dep = getattr(r, "dependant", None)
        if dep is not None and gated(dep):
            out += [(m, re.sub(r"\{[^}]+\}", "1", r.path)) for m in sorted(r.methods - {"HEAD", "OPTIONS"})]
    return out


def _claims(token: str) -> dict:
    return jwt.decode(token, options={"verify_signature": False})


# ── 판정 ─────────────────────────────────────────────────────────────────────
def test_토큰의_관리자_표지는_원장에_없으면_관리자가_아니다():
    pol = AccessPolicy(Settings(_env_file=None)).get()
    for row in (None, {"groups": [], "grants": []}, {"groups": ["mes-user"], "status": "active"}):
        e = compute(pol, groups=[ADMIN_GROUP], row=row)
        assert e.is_admin is False, f"토큰이 들고 온 표지를 믿었다(row={row})"
        assert e.keys == {"feat:chat"}, "관리자가 아니면 기본 권한뿐이다"
        got = with_entitlements([ADMIN_GROUP, "mes-user", "feat:deliberation"], e)
        assert ADMIN_GROUP not in got, "판정만 고치고 그룹에 남기면 require_role 이 그대로 통과한다"
        assert "mes-user" in got and "feat:deliberation" not in got, "로그인 그룹은 남고 들어온 합성 그룹은 버린다"
    led = compute(pol, groups=[], row={"groups": [ADMIN_GROUP]})
    assert led.is_admin is True and with_entitlements([], led).count(ADMIN_GROUP) == 1, "원장 관리자는 그대로다"
    assert with_entitlements([ADMIN_GROUP], led).count(ADMIN_GROUP) == 1, "표지는 한 번만 붙는다"


# ── 들고 있던 세션·refresh ───────────────────────────────────────────────────
def test_옛_세션에_박힌_표지로는_어느_관리자_라우트도_못_연다(box):
    c, _s = box
    routes = _admin_routes()
    assert ("GET", "/auth/local/users") in routes and ("PATCH", "/auth/access/users/1") in routes and len(routes) >= 10, routes
    h = _wear(c, _old_token("user@corp.com", [ADMIN_GROUP]))
    for method, path in routes:
        r = c.request(method, path, headers=h, json={})
        assert r.status_code == 403 and "requires role" in r.text, f"{method} {path} → {r.status_code} {r.text[:120]}"
    # require_role 을 안 쓰고 그룹을 직접 보는 자리들도 같다
    assert c.get("/auth/pat/all").status_code == 403
    assert c.get("/setup/requests").json() == {"items": [], "pending": 0}
    me = c.get("/auth/me").json()
    assert ADMIN_GROUP not in me["groups"] and me["entitlements"] == ["feat:chat"], me
    assert c.get("/auth/access").json()["is_admin"] is False


def test_원장에_행이_없는_신원도_표지만으로는_관리자가_아니다(box):
    """mock 시절 공용 계정처럼 원장에 없는 신원 — 원장에 없는 것은 정지가 아니라 로그인은 되지만, 관리자는 아니다."""
    c, _s = box
    _wear(c, _old_token("ghost@corp.com", [ADMIN_GROUP, "mes-user"]))
    me = c.get("/auth/me")
    assert me.status_code == 200 and me.json()["groups"] == ["mes-user"], me.text
    assert c.get("/auth/local/users").status_code == 403


def test_옛_refresh_로_새_세션을_받아도_관리자가_아니다(box):
    """refresh 는 원장을 다시 보지 않고 제 그룹을 새 세션에 옮겨 적었다 — 8시간 동안 표지가 되살아나는 길이었다."""
    c, _s = box
    c.cookies.clear()
    c.cookies.set(CSRF_COOKIE, "t")
    c.cookies.set(REFRESH_COOKIE, _old_token("user@corp.com", [ADMIN_GROUP, "mes-user"], typ="refresh"))
    r = c.post("/auth/refresh", headers={"X-CSRF-Token": "t"})
    assert r.status_code == 200, r.text
    new = app.state.jwt_service.verify_session(r.cookies.get(SESSION_COOKIE))
    assert new["groups"] == ["mes-user"], "새 세션에 표지를 다시 박았다"
    assert c.get("/auth/local/users").status_code == 403


def test_원장_관리자는_그대로_관리자다(box):
    c, _s = box
    _login(c, "boss@corp.com")
    assert c.get("/auth/local/users").status_code == 200
    assert ADMIN_GROUP in c.get("/auth/me").json()["groups"]
    # 표지가 박히지 않은 세션이어도 원장만으로 관리자다 — 정본이 원장이라는 것의 다른 면
    _wear(c, _old_token("boss@corp.com", []))
    assert c.get("/auth/local/users").status_code == 200
    # 원장에서 떼면 들고 있던 세션도 그 순간부터 아니다
    app.state.user_store.set_groups("boss@corp.com", [])
    assert c.get("/auth/local/users").status_code == 403


# ── 들고 있던 PAT ────────────────────────────────────────────────────────────
def test_옛_PAT_에_박힌_표지로는_관리자_그룹_문을_못_지난다(box):
    """업로드 수신은 PAT 를 받고 기본 설정이 관리자 그룹(UPLOAD_ALLOWED_GROUPS=portal-admin)에게 연다 — 표지가 박힌 옛 PAT 가
    해제 뒤에도 이 문을 지났다. 포털의 PAT 검증은 폐기 목록만 보므로 폐기하지 않은 토큰은 서명이 살아 있다."""
    c, s = box
    c.cookies.clear()
    files = {"file": ("t.csv", b"a,b\n1,2\n", "text/csv")}
    old = {"Authorization": "Bearer " + _old_pat(s, "user@corp.com", [ADMIN_GROUP, "feat:upload", "plat:materialtwin"])}
    r = c.post("/agent/upload", files=files, headers=old)
    assert r.status_code == 403, f"{r.status_code} {r.text[:160]}"
    # 대조군 — 원장 관리자의 PAT 는 표지가 안 박혀 있어도 같은 문을 지난다
    ok = c.post("/agent/upload", files=files, headers={"Authorization": "Bearer " + _old_pat(s, "boss@corp.com", [])})
    assert ok.status_code == 200, ok.text


# ── 발급 ─────────────────────────────────────────────────────────────────────
def test_새로_내는_세션과_refresh_에는_표지를_박지_않는다(box):
    c, _s = box
    _login(c, "boss@corp.com")
    svc = app.state.jwt_service
    assert svc.verify_session(c.cookies.get(SESSION_COOKIE))["groups"] == []
    refresh = next(k.value for k in c.cookies.jar if k.name == REFRESH_COOKIE)
    assert svc.verify_refresh(refresh)["groups"] == []
    p = Principal(subject="a@x.com", email="a@x.com", groups=["mes-user", ADMIN_GROUP, "feat:chat", "plat:ste"])
    assert svc.verify_session(svc.issue_session(p))["groups"] == ["mes-user"]
    assert svc.verify_refresh(svc.issue_refresh(p))["groups"] == ["mes-user"]


def test_새로_내는_PAT_에는_표지도_합성_그룹도_박지_않는다(box):
    c, s = box
    h = _login(c, "boss@corp.com")           # 관리자 — 요청의 그룹에는 portal-admin 과 모든 feat:·plat: 키가 얹혀 있다
    r = c.post("/auth/pat", json={"name": "claude", "ttl_days": 30}, headers=h)
    assert r.status_code == 200, r.text
    assert _claims(r.json()["token"])["groups"] == [], "관리자이던 때 받은 PAT 가 해제 뒤에도 표지를 들고 다닌다"
    p = types.SimpleNamespace(subject="u1", email="u1@x.io", display_name="U",
                              groups=["mes-user", ADMIN_GROUP, "feat:procedures", "plat:ste"])
    assert _claims(mint_procedure_pat(app.state.keystore, s, p, "run-1", 0))["groups"] == ["mes-user"]
    assert _claims(_chat_user_pat(app.state.keystore, s, p))["groups"] == ["mes-user"]


# ── 게이트웨이가 읽는 응답 ───────────────────────────────────────────────────
def test_게이트웨이_조회가_is_admin_을_원장만으로_준다(box):
    c, _s = box
    url = "/internal/access/entitlements"

    def ask(email, groups=""):
        return c.get(url, params={"email": email, "groups": groups}, headers=GW).json()

    assert ask("boss@corp.com")["is_admin"] is True
    assert ask("user@corp.com")["is_admin"] is False
    # 게이트웨이는 PAT 의 로그인 그룹을 그대로 넘긴다 — 그 값으로 관리자가 되면 안 된다
    forged = ask("user@corp.com", ADMIN_GROUP)
    assert forged["is_admin"] is False and forged["keys"] == ["feat:chat"], forged
    ghost = ask("ghost@corp.com", ADMIN_GROUP)
    assert ghost["is_admin"] is False and ghost["keys"] == ["feat:chat"], ghost
    app.state.user_store.set_status("boss@corp.com", "disabled")
    off = ask("boss@corp.com", ADMIN_GROUP)
    assert off["is_admin"] is False and off["keys"] == [], "정지가 관리자보다 먼저다"


def test_게이트웨이가_읽는_식으로_봐도_관리자는_원장만이다(box):
    """게이트웨이는 포털 응답의 `is_admin` 이 **불리언 참**일 때만 하위로 넘기는 그룹에 portal-admin 을 붙인다(게이트웨이 3f6bb28).
    그 판정식을 게이트웨이 원문에서 꺼내 포털의 **실제 응답**에 돌린다 — 칸 이름이나 값의 꼴이 한쪽에서만 바뀌면 관리자 표지가
    하위로 가지 않거나(이름이 갈렸다) 문자열 'false' 가 참이 된다(꼴이 갈렸다). 두 리포는 같은 배포로 나간다."""
    from pathlib import Path

    gw = Path(__file__).resolve().parents[3] / "HWAXMcpGateway" / "gateway.py"
    if not gw.exists():
        pytest.skip("게이트웨이 리포가 옆에 없다")
    m = re.search(r"^\s*if _ent is not None and (_ent\.get\(\"is_admin\"\)[^:\n]*):\s*$", gw.read_text(encoding="utf-8"), re.M)
    if m is None:
        pytest.skip("옆의 게이트웨이가 아직 포털의 is_admin 을 읽지 않는 판이다")

    def gateway_says(ent: dict) -> bool:
        return bool(eval(m.group(1), {"__builtins__": {}}, {"_ent": ent}))  # noqa: S307 — 옆 리포의 추적 파일에서 꺼낸 판정식

    c, _s = box
    url = "/internal/access/entitlements"

    def ask(email, groups=""):
        return c.get(url, params={"email": email, "groups": groups}, headers=GW).json()

    assert gateway_says(ask("boss@corp.com")) is True, "원장 관리자 — 표지가 하위로 간다"
    assert gateway_says(ask("user@corp.com", ADMIN_GROUP)) is False, "토큰에 박힌 표지 — 포털이 보증하지 않는다"
    assert gateway_says(ask("ghost@corp.com", ADMIN_GROUP)) is False, "원장에 없는 신원"
    app.state.user_store.set_status("boss@corp.com", "disabled")
    assert gateway_says(ask("boss@corp.com", ADMIN_GROUP)) is False, "정지된 관리자"
    # 값의 꼴 — 게이트웨이는 참 같은 값(문자열·숫자)을 받지 않는다. 포털이 불리언을 내는 동안만 맞물린다.
    assert gateway_says({"is_admin": "true"}) is False and gateway_says({"is_admin": 1}) is False and gateway_says({}) is False


# ── 개발 박스(mock IdP) ──────────────────────────────────────────────────────
def test_mock_IdP_가_준_관리자_그룹은_원장에_없으면_관리자가_아니다(box):
    """mock·oidc-mock 박스는 관리자를 IdP 그룹(MOCK_USER_GROUPS)으로 받아 왔다 — 이제 원장에 적어야 한다.
    원장에 적으면 재로그인 없이 곧바로 관리자다."""
    c, s = box
    assert ADMIN_GROUP in s.mock_user_group_list, "기본 mock 그룹이 바뀌었다 — 이 시험의 전제를 다시 볼 것"
    app.state.auth_provider = MockProvider(s)
    c.cookies.clear()
    r = c.get("/auth/login", follow_redirects=False)
    assert c.get(r.headers["location"], follow_redirects=False).status_code == 302
    me = c.get("/auth/me").json()
    assert me["email"] == s.mock_user_email and me["groups"] == ["mes-user"], me
    assert c.get("/auth/local/users").status_code == 403
    assert app.state.user_store.set_groups(s.mock_user_email, [ADMIN_GROUP]), "첫 로그인이 원장 행을 만든다"
    assert c.get("/auth/local/users").status_code == 200
