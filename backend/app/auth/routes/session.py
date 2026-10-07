"""Session routes: login init, IdP callback, current-user, refresh, logout.

These are IdP-independent: they delegate the only IdP-specific steps (redirect to IdP,
process the IdP response) to the active AuthProvider, then run the same session machinery
for mock and SAML alike.
"""

import contextlib
import logging
import secrets
from urllib.parse import quote

import jwt
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.access.policy import first_sso_affiliation, is_synthetic
from app.auth import access_log, cookies
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
log = logging.getLogger("hwax.auth")


def login_failed(settings: Settings, exc: AuthError, *, reason: str = "") -> RedirectResponse:
    """브라우저 SSO 콜백 실패를 로그인 화면으로 보낸다 — 종전엔 흰 바탕에 JSON 원문 한 줄로 끝났다(docs/ui-refresh 단계 4).

    원인은 버리지 않는다: 서버 로그(WARNING — 포털은 INFO 를 버린다)와 로그인 화면의 '자세히' 둘 다에 남긴다. 운영 SSO 를
    열 때 요청자가 바로 이 원문(InvalidNameIDPolicy 등)으로 원인을 찾았다(D-11). 원문은 검증 사유뿐이라 비밀이 없다.
    길이는 1000자에서 자른다 — 300자로 자르면 '받은 Claim 이름 목록' 이 잘려 진단 단서가 사라졌다(시험이 잡았다).

    reason — **일부러 거절한** 경우의 사유 코드(지금은 `disabled` 하나). 화면은 프로토콜 실패에 "잠시 뒤 다시 시도하세요" 와
    '다시 로그인' 을 보이는데, 정지로 거절된 사람도 같은 화면을 받아 일시 장애로 읽고 다시 눌렀다(누를 때마다 접속 이력에
    login_fail 이 쌓였다). 화면은 이 코드로 문장을 고른다 — detail 의 글을 머리로 올리지 않는다(URL 로 누구나 바꿔 넣을 수 있다).
    `error=sso` 는 그대로 둔다: 옛 dist 가 떠 있는 동안에도 종전 화면으로는 보인다(값을 바꾸면 그동안 아무 안내도 안 뜬다).
    """
    log.warning("SSO 콜백 실패(HTTP %s): %s", exc.status_code, exc.message)
    detail = quote(exc.message[:1000], safe="")
    why = f"&reason={quote(reason, safe='')}" if reason else ""
    return RedirectResponse(f"{settings.frontend_url}/login?error=sso{why}&detail={detail}", status_code=302)


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
    request: Request | None = None,
) -> RedirectResponse:
    """Issue the portal session and bounce the browser back to where it wanted to go.

    Shared by the mock callback and the SAML ACS — everything from a verified Principal
    onward is IdP-independent.
    """
    # ── 정지를 사번으로도 본다(10차 요청 §6) ─────────────────────────────────────────────────────
    # 정지 검사는 이메일 행 하나만 봤다(deps.entitled). 정지된 사람이 다른 Mail Claim 으로 들어오면 원장에 없는 이메일이라 아래
    # note_sso_login 이 active 새 행을 만들고 그대로 로그인됐다. 같은 사번의 정지된 행이 있으면 여기서 끝낸다 — 새 행을 만들기 전,
    # 세션을 내기 전이다. 사번 Claim 을 안 받는 박스(SAML_ATTR_SABUN 빈 값)와 사번이 없는 로그인은 이 판정을 지나지 않는다.
    # ⚠ 이 판정은 아래의 '원장은 부기록이라 실패해도 로그인은 막지 않는다' 갈래(except·suppress) **밖**에 둔다. 그 안에서 거절하면
    #   삼켜져 그대로 로그인된다. 판정을 **못 해도** 들여보내지 않는다 — 원장이 고장 난 동안 정지가 통째로 풀리면 안 된다.
    # ⚠ 요청마다 보는 검사(deps.entitled)는 여전히 이메일 행만 본다 — 정지 전에 다른 Mail 로 이미 만든 행의 세션·PAT 는 그 행을
    #   따로 정지해야 끊긴다. 여기서 막는 것은 **새로 들어오는 길**이다.
    who = getattr(principal, "email", "") or getattr(principal, "subject", "")
    sabun_vals = ((getattr(principal, "attributes", None) or {}).get(settings.saml_attr_sabun)
                  if settings.saml_attr_sabun else None)
    sabun = str((sabun_vals or [""])[0] or "").strip()
    if user_store is not None and sabun:
        try:
            suspended = user_store.disabled_by_sabun(sabun)
            # 제 이메일의 행이 정지된 사람과, 다른 Mail 로 온 사람을 접속 원장에서 가른다 — 뒤쪽이 관리자가 알아야 할 줄이다.
            own = suspended and bool(who) and (user_store.get(who) or {}).get("status") == "disabled"
        except Exception:  # noqa: BLE001 — 못 읽은 것을 '정지 아님' 으로 읽지 않는다
            log.warning("SSO 로그인 거절(%s) — 정지 여부(사번)를 원장에서 확인하지 못했다", who, exc_info=True)
            return login_failed(settings, AuthError("정지 여부를 확인하지 못해 로그인을 중단했습니다 — 관리자에게 문의하세요",
                                                    status_code=503))
        if suspended:
            # 사번 값은 어디에도 남기지 않는다(개인 식별자다).
            log.warning("SSO 로그인 거절(%s) — %s", who,
                        "정지된 계정이다" if own else "같은 사번의 정지된 계정이 있다(다른 Mail 로 들어왔다)")
            if request is not None:
                access_log.note(request, email=who, event="login_fail", service="portal",
                                detail="sso:disabled" if own else "sso:disabled:sabun")
            return login_failed(settings, AuthError("이 계정은 정지되었습니다 — 관리자에게 문의하세요", status_code=403),
                                reason="disabled")

    # SSO 연동 훅 — 같은 이메일의 로컬 계정이 있으면 연결(auth_source 갱신), 없으면 원장에
    # 생성. 계정 행은 SSO 전환 후에도 남는다(로컬 계정 브리지의 승계 보장). 실패해도
    # 로그인은 막지 않는다 — 원장은 부기록이다.
    sso_detail = "sso"     # 접속 원장의 로그인 줄 — 새 행에 소속을 넣었으면 그 출처가 붙는다(sso:aff:map|default:<소속>)
    if user_store is not None and getattr(principal, "email", None):
        # 부서는 여기서 수확해 원장에 적어야 한다 — 원시 Claim(principal.attributes)은 세션 JWT 에 안 실려 콜백을 벗어나면
        # 사라진다(6차 요청 §4-B-2). 이름은 적지 않아도 읽을 때 대체한다(deps.entitled) — 원장 이름이 비었을 때만 채운다.
        attrs = getattr(principal, "attributes", None) or {}
        dept_vals = attrs.get(settings.saml_attr_department) if settings.saml_attr_department else None
        # 부서 코드(DeptId)는 부서명과 다른 칸으로 — 같은 칸에 받으면 사람이 적은 부서명이 코드로 덮인다(10차 요청 §7).
        dept_id_vals = attrs.get(settings.saml_attr_dept_id) if settings.saml_attr_dept_id else None
        # 소속 — **처음 생기는 행에만** 넣는다(10차 요청 §2). Claim → 소속 표가 먼저, 안 맞으면 기본 소속이고 둘 다 권한 표에 있는
        # 소속만 나온다. 입력은 셋뿐이다: IdP 가 서명한 Assertion 의 Claim, 박스 파일의 표, 박스 env 의 기본값 — 요청(본문·쿼리·
        # 헤더·쿠키)에서 오는 값은 없다. 권한 표를 못 읽으면 넣지 않는다(검증 못 한 소속을 원장에 쓰지 않는다).
        # 이미 있는 사람은 계산도 하지 않는다 — 어차피 쓰지 않고, 계산이 남기는 경고('적용하지 않았다')가 로그인마다 쌓인다.
        aff, aff_src, aff_why = "", "", ""
        access = getattr(request.app.state, "access", None) if request is not None else None
        if access is not None:
            with contextlib.suppress(Exception):
                if user_store.get(principal.email) is None:
                    aff, aff_src, aff_why = first_sso_affiliation(access.get(), attrs, settings.sso_default_affiliation)
        created = False
        try:
            created = user_store.note_sso_login(email=principal.email, name=principal.display_name,
                                                department=(dept_vals or [None])[0],
                                                dept_id=(dept_id_vals or [None])[0], affiliation=aff,
                                                sabun=sabun)
        except Exception:  # noqa: BLE001 — 원장은 부기록이라 로그인은 막지 않는다
            # 다만 조용히 삼키지 않는다. 종전엔 흔적이 없었다 — 새 사람은 행 없이(소속도 없이) 들어와 관리자 목록에도 안 보인다.
            # 원장의 칸 추가가 기동 때 실패한 박스에서 이 쓰기가 로그인마다 실패한다(칸 추가는 실패를 삼킨다 — user_store).
            log.warning("SSO 원장 기록 실패(%s) — 로그인은 계속한다", principal.email, exc_info=True)
        if created and aff:
            # 사람이 정하지 않은 소속이다 — 누가 넣었는지 남긴다. 서버 로그(WARNING — INFO 는 버려진다)와 아래 접속 원장 둘 다.
            log.warning("SSO 신규 계정 %s — 소속 %s 를 넣었다(%s)", principal.email, aff, aff_why)
            sso_detail = f"sso:aff:{aff_src}:{aff}"
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
    # 접속 원장 + 로그인 연결 ID(docs/access-history). 요청이 없으면(옛 호출부) 둘 다 건너뛴다.
    if request is not None:
        uid = access_log.new_uid()
        cookies.set_uid_cookie(response, settings, uid=uid)
        # 정지된 계정도 IdP 는 통과시키고 세션도 받지만 모든 요청이 403 이다(deps) — 로컬 경로처럼 실패로 적는다(검토 1차).
        disabled = False
        if user_store is not None and who:
            with contextlib.suppress(Exception):
                disabled = (user_store.get(who) or {}).get("status") == "disabled"
        access_log.note(request, email=who, event="login_fail" if disabled else "login", service="portal",
                        detail="sso:disabled" if disabled else sso_detail, uid=uid)
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
    try:
        principal = await provider.handle_callback(request, expected_state=expected_state)
    except AuthError as exc:
        return login_failed(settings, exc)
    return complete_login(
        principal=principal,
        expected_state=expected_state,
        settings=settings,
        jwt_service=jwt_service,
        user_store=getattr(request.app.state, "user_store", None),
        request=request,
    )


@router.get("/me", response_model=UserProfile)
def me(request: Request, principal=Depends(get_current_principal)) -> UserProfile:
    # 부서는 세션 JWT 가 아니라 users 원장에서 — 갱신(RA 연결 자동 채움)이 즉시 보인다.
    department = ""
    store = getattr(request.app.state, "user_store", None)
    if store is not None:
        u = store.get(principal.email)
        department = (u or {}).get("department") or ""
    # 권한(feat:·plat:)은 로그인 그룹과 나눠 준다 — 화면은 entitlements 로 메뉴·입구를 숨긴다.
    ents = getattr(request.state, "entitlements", None)
    return UserProfile(
        subject=principal.subject,
        email=principal.email,
        display_name=principal.display_name,
        groups=[g for g in principal.groups if not is_synthetic(g)],
        department=department,
        affiliation=ents.affiliation if ents else "",
        entitlements=sorted(g for g in principal.groups if is_synthetic(g)),
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
        routed = request.app.state.catalog.routed_prefixes()
        for sysm in request.app.state.catalog.all():
            u = getattr(sysm, "url", "") or ""
            if "/portal-callback" not in u:
                continue
            # 이 박스에 라우트가 없는 타일은 뺀다 — nginx 에 /<접두어>/ location 이 없으면 그 POST 는 포털 자신이 받아 405 로
            # 확정 실패한다(아래의 '늘 울리는 경보'). aireadyportal 은 콜백 url 이 추적 파일에 있고 라우트는 박스 파일에 손으로
            # 적는 첫 핸드오프 타일이라, 라우트가 없는 박스(dev·새 박스)에서 매 로그아웃마다 그랬다. 타일 id 가 아니라 콜백의
            # 첫 경로 마디로 본다 — 리스크 심사 타일은 /heax-hub/ 의 콜백을 쓰고, 화면과 API 가 갈린 서비스의 키는 `<id>/api` 다.
            if u.startswith("/") and u.split("/")[1] not in routed:
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
            # ⚠ aireadyportal 의 /api/auth/logout 은 있는지 확인된 적이 없다(요청서는 /api/auth/me 와 portal-callback 만 말한다).
            # 라우트가 있는 박스에서는 그래도 친다 — 빼면 '확실히 못 끊고 조용하다' 가 된다. 그 박스에서 재 본 뒤 없으면
            # ai-data-hub 처럼 사유와 함께 뺀다.
            _out = base + ("/logout-session" if "/heax-hub/" in u else "/logout")
            if _out not in outs:      # 리스크 심사 타일이 heax-hub 의 콜백을 같이 쓴다 — 같은 주소를 두 번 치지 않는다
                outs.append(_out)
    except Exception:  # noqa: BLE001 — 목록을 못 읽어도 포털 로그아웃 자체는 되어야 한다
        outs = []
    response = JSONResponse({"status": "logged_out", "downstream_logout": outs})
    cookies.clear_session_cookies(response, settings)
    return response
