# 포털 PAT(장기 scope=api RS256 JWT) 발급·목록·폐기 + 게이트웨이용 공개 폐기목록 라우터
"""Portal PAT (Personal Access Token) endpoints.

A PAT shares the launch-token trust root (portal keystore → JWKS) but is longer-lived,
multi-audience, and `scope="api"`. The HWAX REST API gateway verifies it via
`/.well-known/jwks.json` and forwards to sub-site REST APIs with each site's own service
token — the sub-sites are never changed. Revocation = the token_store jti denylist,
published (non-expired revoked jtis) at `/auth/pat/revoked.json` for the gateway to poll.

토큰 교환(`/auth/pat/exchange`)은 원 PAT 로 같은 사람의 더 좁은 PAT 을 내고, 소비자는 새것을
받아들인 뒤 옛것을 `/auth/pat/revoke-self` 로 폐기한다(docs/risk-credentials C-11).
"""

import logging
import re
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.access.policy import login_groups
from app.auth.errors import AuthError
from app.auth.pat_verify import pat_principal, verify_pat_claims
from app.auth.provider import Principal
from app.auth.token_store import MAX_LIVE_CHILDREN
from app.config import Settings, get_settings
from app.deps import ensure, entitled, get_current_principal, require_csrf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/pat", tags=["pat"])

# 범위 이름 — 소문자로 시작하는 영소문자·숫자·`_`·`-`, 32자 이하(SEC-2). `fullmatch` 여야 한다 —
# `re.match` 의 `$` 는 끝 줄바꿈 앞에서도 맞아 "read\n" 을 통과시킨다.
_SCOPE_RE = re.compile(r"[a-z][a-z0-9_-]{0,31}")
_SCOPE_RULE = "소문자로 시작하는 영소문자·숫자·_·- 32자 이하"


def _bad_scopes(scopes: list[str]) -> int:
    return sum(1 for s in scopes if not _SCOPE_RE.fullmatch(s))


class PatCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    audiences: list[str] = Field(default_factory=list)  # sites this PAT may reach; empty → config default
    scopes: list[str] = Field(default_factory=lambda: ["read", "write"])
    # 0 = 무기한(만료로는 안 죽고 폐기로만 죽는다). None 이면 서버 기본값.
    ttl_days: int | None = Field(default=None, ge=0, le=36500)


class PatExchange(BaseModel):
    """토큰 교환 본문 — `/auth/pat` 과 달리 전부 필수다. 빈 칸을 기본값으로 채우면 그 기본값이
    원 PAT 보다 넓을 수 있다."""
    name: str = Field(min_length=1, max_length=80)
    audiences: list[str]
    scopes: list[str]
    ttl_days: int
    # 새 PAT 이 적어도 이만큼(초) 살아야 한다 — 원이 곧 만료되면 낸 PAT 도 곧 죽으므로 내지 않고
    # 거절한다(source_expiring). 소비자가 받자마자 다시 바라는 되풀이를 막는다.
    min_remaining_s: int = Field(default=0, ge=0)


class PatMeta(BaseModel):
    jti: str
    name: str
    audiences: list[str]
    scopes: list[str]
    created: int
    exp: int
    revoked: bool
    # 교환으로 받은 PAT 이면 원 PAT 의 jti — 토큰 화면이 '교환으로 생김' 을 표시한다(D3).
    parent_jti: str | None = None


class PatCreated(PatMeta):
    token: str  # the JWT — shown ONCE, never stored server-side


def _mint_pat(request: Request, settings: Settings, principal: Principal, *,
              name: str, audiences: list[str], scopes: list[str], ttl_days: int,
              not_after: int | None = None, parent_jti: str | None = None):
    """`not_after`(epoch 초)를 주면 만료가 그보다 늦지 않다 — 교환 PAT 은 원보다 오래 못 산다.

    `parent_jti` 를 주면 클레임 `par` 로 싣는다 — 받는 쪽(게이트웨이)이 교환 PAT(자식)과 사람이
    낸 PAT(원)을 원장 없이 가른다(D5)."""
    keystore = request.app.state.keystore
    now = datetime.now(tz=UTC)
    exp = now + timedelta(days=ttl_days)
    if not_after is not None:
        exp = min(exp, datetime.fromtimestamp(not_after, tz=UTC))
    jti = secrets.token_urlsafe(24)
    claims = {
        "iss": settings.jwt_issuer,
        "sub": principal.subject,
        "email": principal.email,
        "name": principal.display_name,
        # 로그인 그룹만 박는다 — 관리자 표지·권한 키는 쓰는 쪽(포털·게이트웨이)이 호출마다 원장으로 다시 정한다.
        # 박아 두면 무기한 PAT 가 발급 때의 `portal-admin` 을 100년 들고 다닌다(10차 요청 §4).
        "groups": login_groups(principal.groups),
        "aud": audiences,        # array — the gateway checks the target site is a member
        "scope": "api",          # distinguishes a PAT from a 90s "launch" token
        "scopes": scopes,
        "pat_name": name,
        "iat": now, "nbf": now, "exp": exp,
        "jti": jti,
    }
    if parent_jti:
        claims["par"] = parent_jti
    token = jwt.encode(claims, keystore.private_pem, algorithm="RS256",
                       headers={"kid": keystore.active_kid})
    return token, jti, int(now.timestamp()), int(exp.timestamp())


@router.post("", response_model=PatCreated)
def create_pat(
    body: PatCreate,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    _csrf: None = Depends(require_csrf),
    settings: Settings = Depends(get_settings),
) -> PatCreated:
    # API 토큰은 게이트웨이 도구를 포털 밖(Claude·스크립트)에서 쓰는 열쇠다 — 허가가 있어야
    # 발급한다.
    ensure(principal, "feat:api-token")
    if n := _bad_scopes(body.scopes):
        raise AuthError(f"bad_scope — scopes 가운데 {n}개의 형식이 틀렸다({_SCOPE_RULE})",
                        status_code=400)
    # ttl_days=0 은 '무기한' 이다. `or` 로 기본값을 채우면 0 이 falsy 라 90일로 둔갑하므로
    # None 과 0 을 반드시 구분한다.
    never = body.ttl_days == 0
    ttl = settings.pat_never_ttl_days if never else (body.ttl_days or settings.pat_ttl_days)
    if not never and (ttl < 1 or ttl > settings.pat_max_ttl_days):
        raise AuthError(f"ttl_days must be 0(무기한) or 1..{settings.pat_max_ttl_days}",
                        status_code=400)
    auds = body.audiences or settings.pat_default_audience_list
    allowed = set(settings.pat_default_audience_list)  # least privilege: only known sites
    bad = [a for a in auds if a not in allowed]
    if bad:
        raise AuthError(f"unknown audience(s): {', '.join(bad)}", status_code=400)
    token, jti, created, exp = _mint_pat(
        request, settings, principal,
        name=body.name, audiences=auds, scopes=body.scopes, ttl_days=ttl,
    )
    request.app.state.token_store.record_pat(
        jti=jti, sub=principal.subject, email=principal.email, name=body.name,
        aud=auds, scopes=body.scopes, created=created, exp=exp,
    )
    # 발급을 남긴다 — 특히 무기한은 만료로 안 죽으므로 "누가 언제 냈나" 가 사후 유일한
    # 단서다. token_store 행 하나만으로는 조회 경로가 관리자 목록뿐이라 부족하다.
    # name 은 사람이 고른 글이다 — %r 로 남겨 줄바꿈으로 기록 줄을 위조하지 못하게 한다(SEC-4).
    logger.warning("PAT issued: sub=%s name=%r aud=%s ttl=%s%s",
                   principal.subject, body.name, auds,
                   "무기한" if never else f"{ttl}d",
                   " ⚠NEVER-EXPIRES" if never else "")
    return PatCreated(jti=jti, name=body.name, audiences=auds, scopes=body.scopes,
                      created=created, exp=exp, revoked=False, token=token)


def _too_many_children() -> AuthError:
    return AuthError(f"이 원 PAT 로 바꿔 받은 살아 있는 PAT 이 이미 {MAX_LIVE_CHILDREN}개다 — "
                     "안 쓰는 것을 폐기(revoke-self·토큰 화면)한 뒤 다시 바꿔라",
                     status_code=409, code="too_many_children")


@router.post("/exchange", response_model=PatCreated)
def exchange_pat(
    body: PatExchange,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> PatCreated:
    """원 PAT 하나를 증거로 **같은 사람의 더 좁은 PAT** 을 낸다. 넓히는 일은 하지 않는다.

    게이트웨이가 Claude 로 온 호출자 본인의 PAT 을 그대로 들고 부른다(docs/risk-credentials
    PLAN §4.1). 그래서 인증은 `Authorization: Bearer` 하나다 — 세션 쿠키는 보지 않는다(웹은
    `/auth/pat` 이 있다). 쿠키를 안 보므로 CSRF 도 걸 자리가 없다. 거절은 전부
    `{"detail": {"code", "message"}}` 다 — 게이트웨이가 code 로 갈라 감사에 남긴다.
    """
    auth = request.headers.get("authorization", "")
    if auth[:7].lower() != "bearer ":
        raise AuthError("Authorization: Bearer <원 PAT> 만 받는다 — 브라우저는 /auth/pat 를 쓴다",
                        status_code=401, code="invalid_source")
    ts = request.app.state.token_store
    try:
        src = verify_pat_claims(auth[7:].strip(), keystore=request.app.state.keystore,
                                revoked_jtis=ts.revoked_jtis(),
                                audience=settings.pat_chat_audience)
    except Exception as exc:  # noqa: BLE001 — 어떤 검증 실패든 401(principal_pat_or_session 과 같다)
        raise AuthError("원 PAT 이 유효하지 않다(서명·청중·만료·폐기)", status_code=401,
                        code="invalid_source") from exc
    try:
        principal = entitled(request, pat_principal(src), settings.portal_admin_email_set)
    except AuthError as exc:
        raise AuthError(exc.message, status_code=exc.status_code,
                        code="account_disabled") from exc
    try:
        ensure(principal, "feat:api-token")
    except AuthError as exc:
        raise AuthError(exc.message, status_code=exc.status_code,
                        code="permission_denied") from exc
    # 사람이 토큰 화면에서 낸 PAT 만 원이 된다. 챗·절차 PAT 은 기록되지 않고 절차 PAT 은
    # `purpose` 를 단다 — 24시간짜리 챗 PAT 로 90일짜리를 받는 수명 늘리기를 막는다.
    if src.get("purpose") or not ts.pat_is_exchangeable(src["jti"], src["sub"]):
        raise AuthError("토큰 화면에서 발급한 PAT 만 바꿀 수 있다 — 챗·절차용 PAT 과 "
                        "교환으로 받은 PAT 은 원이 될 수 없다",
                        status_code=403, code="source_not_exchangeable")
    src_aud = src["aud"] if isinstance(src["aud"], list) else [src["aud"]]
    # 빈 청중도 거절한다 — `/auth/pat` 에서 빈 청중은 '기본 전체' 라 좁히기가 아니다.
    # 거절 글에 받은 값을 되싣지 않는다(SEC-2) — 게이트웨이가 감사에 남기는 글이라 줄바꿈 등으로
    # 줄을 위조할 수 있다. 원 PAT 의 값도 옛 발급(형식 검사 전)이면 사람이 고른 글이라 수만 센다.
    if not body.audiences or not set(body.audiences) <= set(src_aud):
        raise AuthError(f"audiences 는 원 PAT 청중({len(src_aud)}개)의 비지 않은 부분집합이어야 "
                        f"한다 — 원에 없는 것 {len(set(body.audiences) - set(src_aud))}개",
                        status_code=400, code="widen_audience")
    if n := _bad_scopes(body.scopes):
        raise AuthError(f"scopes 가운데 {n}개의 형식이 틀렸다({_SCOPE_RULE})",
                        status_code=400, code="bad_scope")
    src_scopes = src.get("scopes", ["read", "write"])  # 칸이 없던 옛 PAT 은 /auth/pat 기본값
    if not set(body.scopes) <= set(src_scopes):
        raise AuthError(f"scopes 는 원 PAT 범위({len(src_scopes)}개)의 부분집합이어야 한다 — "
                        f"원에 없는 것 {len(set(body.scopes) - set(src_scopes))}개",
                        status_code=400, code="widen_scopes")
    if not 1 <= body.ttl_days <= settings.pat_max_ttl_days:
        raise AuthError(f"ttl_days 는 1..{settings.pat_max_ttl_days} 다(무기한 없음)",
                        status_code=400, code="bad_ttl")
    now = int(datetime.now(tz=UTC).timestamp())
    src_left = int(src["exp"]) - now
    life = min(body.ttl_days * 86400, src_left)  # = min(지금 + ttl, 원의 만료) - 지금
    if life < body.min_remaining_s:
        why = (f"원 PAT 자체가 곧 만료된다(남은 {src_left}초) — 토큰 화면에서 새 PAT 을 발급해 "
               "다시 넣어야 한다" if src_left < body.min_remaining_s else
               f"ttl_days({body.ttl_days}일)가 min_remaining_s 보다 짧다")
        raise AuthError(f"새 PAT 이 {life}초만 살 수 있어 요구한 {body.min_remaining_s}초에 "
                        f"못 미친다 — {why}", status_code=400, code="source_expiring")
    if ts.live_children(src["jti"]) >= MAX_LIVE_CHILDREN:
        raise _too_many_children()
    token, jti, created, exp = _mint_pat(
        request, settings, principal, name=body.name, audiences=body.audiences,
        scopes=body.scopes, ttl_days=body.ttl_days, not_after=int(src["exp"]),
        parent_jti=src["jti"],
    )
    # 같은 이름의 앞선 교환 PAT 은 여기서 폐기하지 않는다(C-11) — 소비자가 새것을 받아들인 뒤
    # `/auth/pat/revoke-self` 로 옛것을 스스로 폐기한다.
    refused = ts.record_exchanged_pat(
        parent_jti=src["jti"], jti=jti, sub=principal.subject, email=principal.email,
        name=body.name, aud=body.audiences, scopes=body.scopes, created=created, exp=exp,
    )
    if refused == "source_revoked":  # 검사 뒤 기록 전에 원이 폐기됐다 — 낸 토큰은 버린다
        raise AuthError("원 PAT 이 방금 폐기됐다", status_code=403, code="source_not_exchangeable")
    if refused == "too_many_children":  # 동시 교환이 위 검사를 함께 지났다 — 낸 토큰은 버린다
        raise _too_many_children()
    logger.warning("PAT exchanged: sub=%s name=%r parent=%s aud=%s exp=%s",  # name 은 %r(SEC-4)
                   principal.subject, body.name, src["jti"], body.audiences, exp)
    return PatCreated(jti=jti, name=body.name, audiences=body.audiences, scopes=body.scopes,
                      created=created, exp=exp, revoked=False, parent_jti=src["jti"], token=token)


@router.post("/revoke-self")
def revoke_self(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> dict:
    """Bearer 로 낸 PAT **그 자신**을 폐기한다(그 자식은 연쇄로 함께). 다른 jti 는 받지도 않는다.

    교환 PAT 을 쥔 소비자(리스크 앱)가 새것을 받아들인 뒤 옛것을 죽이는 길이다(C-11). 인증은
    `Authorization: Bearer` 하나이고, 폐기 대상은 그 토큰의 jti 뿐이다 — 본문·경로에 jti 를 받지
    않으므로 남의 토큰을 고를 길이 없다.

    폐기 목록은 보지 않는다(서명·청중·`scope=api`·만료는 본다). 이미 폐기된 토큰도 200 이다 —
    응답을 잃은 재시도가 실패처럼 보이면 안 되고, 폐기된 토큰으로 할 수 있는 일은 이미 폐기된
    자기 자신(과 연쇄로 이미 폐기된 자식)을 다시 폐기하는 것뿐이다. 계정 정지·`feat:api-token`
    도 보지 않는다 — 힘을 줄이는 일이다. 만료된 토큰은 401 이다(이미 죽었고, 원장 행도 지워진다).
    """
    auth = request.headers.get("authorization", "")
    if auth[:7].lower() != "bearer ":
        raise AuthError("Authorization: Bearer <폐기할 PAT> 만 받는다", status_code=401,
                        code="invalid_token")
    try:
        claims = verify_pat_claims(auth[7:].strip(), keystore=request.app.state.keystore,
                                   revoked_jtis=(), audience=settings.pat_chat_audience)
    except Exception as exc:  # noqa: BLE001 — 어떤 검증 실패든 401
        raise AuthError("PAT 이 유효하지 않다(서명·청중·만료)", status_code=401,
                        code="invalid_token") from exc
    if not request.app.state.token_store.revoke_pat(claims["jti"], claims["sub"]):
        raise AuthError("토큰 원장에 없는 PAT 이다 — 챗·절차용 PAT 은 기록되지 않아 여기서 "
                        "폐기할 수 없다(만료로 죽는다)", status_code=404, code="not_recorded")
    logger.warning("PAT self-revoked: sub=%s jti=%s", claims["sub"], claims["jti"])
    return {"revoked": claims["jti"]}


@router.get("", response_model=list[PatMeta])
def list_pat(
    request: Request,
    principal: Principal = Depends(get_current_principal),
) -> list[PatMeta]:
    return [PatMeta(**r) for r in request.app.state.token_store.list_pats(principal.subject)]


@router.get("/all")
def list_all_pats(
    request: Request,
    principal: Principal = Depends(get_current_principal),
) -> dict:
    """전체 PAT 메타 — 관리자 전용. 토큰 자체는 어디에도 실리지 않는다.

    무기한 토큰은 폐기가 유일한 통제인데, 남의 토큰을 찾을 방법이 없으면 그 폐기를
    실행할 수 없다. 목록 없이 '폐기하면 된다' 고만 적어 두는 것은 통제가 아니다.
    """
    if "portal-admin" not in principal.groups:
        raise AuthError("admin only", status_code=403)
    # 잘린 사실을 숨기지 않는다 — 목록이 전부인 줄 알면 없는 토큰을 없다고 믿는다.
    ts = request.app.state.token_store
    rows = ts.all_pats()
    total = ts.count_pats()
    return {"pats": rows, "shown": len(rows), "total": total,
            "truncated": total > len(rows),
            "note": ("만료가 먼 것(오래 사는 토큰)부터 보인다 — 폐기가 필요한 쪽이 먼저다."
                     if total > len(rows) else "")}


@router.delete("/{jti}")
def revoke_pat(
    jti: str,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    _csrf: None = Depends(require_csrf),
) -> dict:
    is_admin = "portal-admin" in principal.groups
    ok = request.app.state.token_store.revoke_pat(jti, None if is_admin else principal.subject)
    if not ok:
        raise AuthError("token not found", status_code=404)
    return {"revoked": jti}


@router.get("/revoked.json")
def revoked_list(request: Request) -> JSONResponse:
    """PUBLIC denylist (opaque jtis) the REST gateway polls to enforce pre-expiry revocation."""
    return JSONResponse(
        {"revoked": request.app.state.token_store.revoked_jtis()},
        headers={"Cache-Control": "public, max-age=60"},
    )
