"""Session routes: login init, IdP callback, current-user, refresh, logout.

These are IdP-independent: they delegate the only IdP-specific steps (redirect to IdP,
process the IdP response) to the active AuthProvider, then run the same session machinery
for mock and SAML alike.
"""

import contextlib
import secrets

import jwt
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.auth import cookies
from app.auth.errors import AuthError
from app.auth.jwt_service import JWTService
from app.auth.provider import AuthProvider
from app.config import Settings, get_settings
from app.deps import (
    get_auth_provider,
    get_current_principal,
    get_jwt_service,
    require_csrf,
)
from app.schemas.auth import UserProfile

router = APIRouter(prefix="/auth", tags=["auth"])


def _safe_return_to(raw: str | None) -> str:
    """Only allow same-site relative paths — blocks open-redirect via return_to."""
    if not raw or not raw.startswith("/") or raw.startswith("//"):
        return "/"
    return raw


def complete_login(
    *,
    principal,
    expected_state: str | None,
    settings: Settings,
    jwt_service: JWTService,
    user_store=None,
) -> RedirectResponse:
    """Issue the portal session and bounce the browser back to where it wanted to go.

    Shared by the mock callback and the SAML ACS — everything from a verified Principal
    onward is IdP-independent.
    """
    # SSO 연동 훅 — 같은 이메일의 로컬 계정이 있으면 연결(auth_source 갱신), 없으면 원장에
    # 생성. 계정 행은 SSO 전환 후에도 남는다(로컬 계정 브리지의 승계 보장). 실패해도
    # 로그인은 막지 않는다 — 원장은 부기록이다.
    if user_store is not None and getattr(principal, "email", None):
        with contextlib.suppress(Exception):
            user_store.note_sso_login(email=principal.email, name=principal.display_name)
    return_to = "/"
    if expected_state:
        try:
            return_to = _safe_return_to(jwt_service.verify_state(expected_state).get("return_to"))
        except jwt.PyJWTError:
            return_to = "/"

    response = RedirectResponse(f"{settings.frontend_url}{return_to}", status_code=302)
    cookies.set_session_cookies(
        response,
        settings,
        session=jwt_service.issue_session(principal),
        refresh=jwt_service.issue_refresh(principal),
    )
    cookies.set_csrf_cookie(response, settings, token=secrets.token_urlsafe(24))
    cookies.clear_state_cookie(response, settings)
    return response


@router.get("/login")
def login(
    request: Request,
    return_to: str = "/",
    settings: Settings = Depends(get_settings),
    provider: AuthProvider = Depends(get_auth_provider),
    jwt_service: JWTService = Depends(get_jwt_service),
) -> RedirectResponse:
    state = jwt_service.issue_state(return_to=_safe_return_to(return_to))
    response = provider.login_redirect(state=state)
    cookies.set_state_cookie(response, settings, token=state)
    return response


# GET(response_mode=query) + POST(response_mode=form_post) 둘 다 — 사내 IdP 는 대개 form_post
# 로 POST 콜백을 보내는데, GET 전용이면 여기서 405 Method Not Allowed 로 로그인이 깨진다.
@router.api_route("/callback", methods=["GET", "POST"])
async def callback(
    request: Request,
    settings: Settings = Depends(get_settings),
    provider: AuthProvider = Depends(get_auth_provider),
    jwt_service: JWTService = Depends(get_jwt_service),
) -> RedirectResponse:
    expected_state = request.cookies.get(cookies.STATE_COOKIE)
    principal = await provider.handle_callback(request, expected_state=expected_state)
    return complete_login(
        principal=principal,
        expected_state=expected_state,
        settings=settings,
        jwt_service=jwt_service,
        user_store=getattr(request.app.state, "user_store", None),
    )


@router.get("/me", response_model=UserProfile)
def me(request: Request, principal=Depends(get_current_principal)) -> UserProfile:
    # 부서는 세션 JWT 가 아니라 users 원장에서 — 갱신(RA 연결 자동 채움)이 즉시 보인다.
    department = ""
    store = getattr(request.app.state, "user_store", None)
    if store is not None:
        u = store.get(principal.email)
        department = (u or {}).get("department") or ""
    return UserProfile(
        subject=principal.subject,
        email=principal.email,
        display_name=principal.display_name,
        groups=principal.groups,
        department=department,
    )


@router.post("/refresh")
def refresh(
    request: Request,
    settings: Settings = Depends(get_settings),
    jwt_service: JWTService = Depends(get_jwt_service),
    _: None = Depends(require_csrf),
) -> JSONResponse:
    token = request.cookies.get(cookies.REFRESH_COOKIE)
    if not token:
        raise AuthError("no refresh token", status_code=401)
    try:
        claims = jwt_service.verify_refresh(token)
    except jwt.PyJWTError as exc:
        raise AuthError("invalid or expired refresh token", status_code=401) from exc

    principal = jwt_service.principal_from_claims(claims)
    response = JSONResponse({"status": "refreshed"})
    cookies.set_session_cookie(response, settings, session=jwt_service.issue_session(principal))
    return response


@router.post("/logout")
def logout(
    request: Request,
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_csrf),
) -> JSONResponse:
    # 하위 서비스 세션도 같이 끊어야 한다. 그 쿠키들은 같은 호스트의 '경로 스코프' 라
    # 서버가 대신 지울 수 없다(포털은 /heax-hub/ 경로 쿠키를 못 건드린다) — 브라우저가
    # 각 서비스의 로그아웃을 쳐야 한다. 안 그러면 포털에서 로그아웃해도 /apps/<slug>/ 가
    # 그 서비스의 토큰 수명(최대 1시간) 동안 직전 사용자 신원으로 열려 있다.
    # 여기서는 '어디를 쳐야 하는지' 만 알려주고, 실제 호출은 SPA 가 한다.
    # ⚠ 목록은 세션이 있는 사람에게만 준다. require_csrf 는 double-submit 이라 호출자가
    # 쿠키·헤더를 같은 값으로 맞추면 스스로 통과시킬 수 있어 인증이 아니다 — 그대로 두면
    # 미인증 호출자가 하위 서비스 인증 엔드포인트 목록을 그냥 받아 간다.
    # 로그아웃 동작(쿠키 삭제)은 세션 유무와 무관하게 그대로 수행한다.
    # ⚠ 쿠키 '존재' 로 판정하면 두 가지가 동시에 틀린다.
    #   (1) 서명 검증이 없어 아무 값이나 넣으면 통과한다 — 막았다던 미인증 노출이 그대로다.
    #   (2) hwax_session 은 900초라 15분만 놀아도 사라진다. SPA 에 주기 갱신이 없고 이
    #       라우트는 401 을 안 내므로 refresh-on-401 도 안 탄다 → 정상 사용자가 하위
    #       서비스를 하나도 못 끊는다(로그아웃이 무력화된다).
    # 그래서 세션 또는 refresh 토큰 중 하나라도 '검증에 성공' 해야 목록을 준다.
    _has_session = False
    try:
        _svc = request.app.state.jwt_service
        _tok = request.cookies.get(cookies.SESSION_COOKIE)
        if _tok:
            _svc.verify_session(_tok)
            _has_session = True
    except Exception:  # noqa: BLE001 — 만료·위조는 아래 refresh 로 한 번 더 본다
        _has_session = False
    if not _has_session:
        try:
            _rt = request.cookies.get(cookies.REFRESH_COOKIE)
            if _rt:
                request.app.state.jwt_service.verify_refresh(_rt)
                _has_session = True
        except Exception:  # noqa: BLE001 — 둘 다 실패면 목록을 주지 않는다
            _has_session = False
    outs = []
    try:
        if not _has_session:
            raise RuntimeError("no session — 목록 비공개")
        for sysm in request.app.state.catalog.all():
            u = getattr(sysm, "url", "") or ""
            if "/portal-callback" not in u:
                continue
            base = u.rsplit("/", 1)[0]
            # ⚠ 경로를 유도만 하고 존재를 확인하지 않으면 안 된다 — 실측으로 4개 중
            # 3개가 404 이거나(엔드포인트 없음) 401/422 였다(헤더·본문 요구). 그런데도
            # 화면은 '로그아웃됨' 으로 끝났다. 서비스별로 '쿠키만 지우는' 경로를 쓴다.
            #   heax-hub : /logout 은 Bearer+본문 필수 → 쿠키 전용 /logout-session 을 쓴다
            #   그 외    : /logout (없으면 SPA 가 그 사실을 사용자에게 알린다)
            # ⚠ 없는 엔드포인트를 목록에 넣지 않는다. ai-data-hub 는 로그아웃 경로가
            # 아예 없다. 넣어 두면 매 로그아웃마다 404 가 확정적으로 발생해 "실패를
            # 알린다" 는 장치가 늘 울리는 경보가 된다 — 그러면 진짜 실패를 아무도 안 본다.
            #
            # ⚠ 다만 이건 '지웠다'가 아니라 '알리지 않는다'다. AIDataHub 의 자격증명은
            # localStorage 의 X-API-Key 인데 그건 사본일 뿐이고, 정본은 서버의 ApiKey
            # 행이다(portal_sso.py 가 name="sso:{email}" 로 발급, TTL 은
            # portal_sso_key_ttl_days 기본 30일). 브라우저에서 지워도 그 행은 살아 있어
            # 키 사본을 가진 쪽은 최대 30일간 그대로 들어간다. 포털 로그아웃은
            # AIDataHub 접근을 회수하지 못한다 — 회수하려면 AIDataHub 에 그 행을
            # revoke 하는 경로가 필요하다(재로그인 때는 portal_sso 가 이전 키를 폐기한다).
            if "/ai-data-hub/" in u:
                continue
            outs.append(base + ("/logout-session" if "/heax-hub/" in u else "/logout"))
    except Exception:  # noqa: BLE001 — 목록을 못 읽어도 포털 로그아웃 자체는 되어야 한다
        outs = []
    response = JSONResponse({"status": "logged_out", "downstream_logout": outs})
    cookies.clear_session_cookies(response, settings)
    return response
