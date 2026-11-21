# RA 사람별 위임 — 포털이 RA 전용 공유 비밀로 그 사람의 RA 토큰을 그 자리에서 받는다(ste 방식, docs/sso-delegation)
"""RA 위임 토큰 도우미.

  POST {ra_sso_url}  헤더 X-Heax-Gateway-Secret · X-Heax-User-Email · X-Heax-User-Name · X-Heax-Client
                     → 200 {success, data: {access_token, expires_in, …}}  · 404 꺼짐 · 401 비밀 불일치 또는 메일 꼴 아님
                       · 403 허용 IP 밖(HEAX_SSO_ALLOWED_IPS) 또는 계정 비활성
  POST {ra_sso_url}/revoke  같은 헤더(이름 빼고) → 200 {ok, revoked} — 그 사람 · 그 client 의 위임 토큰을 지운다(RA v0.170.0)

**왜 포털도 받나.** Claude·챗·심의의 RA 호출은 게이트웨이가 같은 계약으로 받는다(`per_user_sso.reportarchive`).
포털이 RA 를 직접 부르는 곳(챗의 PPT 가져오기)만 남는데, 거기서 사람이 붙여 넣은 토큰을 찾으면 ste 방식으로
바꾼 뜻이 없다 — `/ste/credential` 과 같은 선례로 포털이 그 자리에서 받는다.

**토큰은 메모리에만 짧게 둔다.** 포털 DB 에 쌓지 않는다(ste 방식의 요점이다). 캐시는 RA 가 발급마다 접속 이력에
'포털 로그인' 한 줄을 남기기 때문이다 — PPT 를 연달아 올릴 때마다 받으면 그 사람의 RA 로그인이 그만큼 부푼다.

**실패는 None 이다.** 부르는 쪽이 등록 토큰으로 내려가거나 사람에게 이유를 말한다. 비밀·토큰은 로그에 안 남긴다.
"""

from __future__ import annotations

import logging
import time

import httpx

# 이름 헤더 인코딩은 ste 중계와 한 규칙이다 — 따로 두면 한쪽만 고쳐져 한글 이름에서 갈린다.
from app.auth.routes.ste_credential import _header_name
from app.config import Settings

log = logging.getLogger("hwax.ra_sso")

# ste 중계와 같은 시한 — 계정 확인 + JWT 서명뿐이라 원래 수십 ms 다.
TIMEOUT_S = 15.0
# 캐시 상한 — RA 위임 토큰은 `rat_` 개인 토큰이고 수명은 2일이다(RA v0.170.0 — expires_in 172800. 요청서를 쓸 때는 12시간 JWT 로 알았다).
# 만료 직전 토큰을 쓰지 않게 expires_in 보다 2분 일찍 버리고, 그래도 11시간을 넘기지 않는다(메모리에 오래 두지 않는다).
MAX_TTL_S = 11 * 3600
EARLY_S = 120

# {email: (token, 만료 monotonic)}. 프로세스 하나의 메모리다 — 재기동하면 비고 다시 받으면 된다.
_CACHE: dict[str, tuple[str, float]] = {}
# 404(RA 쪽 꺼짐)는 설정 상태라 매번 경고하면 소음이다 — 프로세스당 한 번만 남긴다.
_OFF_LOGGED = False
# {email: 마지막으로 못 받은 까닭} — 사람에게 내는 안내가 고칠 곳을 짚게 한다(why_failed). 받으면 지운다. 상한을 넘으면 통째로 비운다.
_WHY: dict[str, str] = {}
_WHY_MAX = 2000
# RA `sso/gateway_token.py` 의 `_gate` · `issue` 가 내는 상태 그대로다(v0.171.1).
_WHY_BY_STATUS = {
    401: "RA 가 포털의 위임 비밀을 받지 않았거나(RA 의 HEAX_SSO_SECRET 과 포털의 RA_SSO_SECRET 이 다르다) 계정 이름이 메일 주소 꼴이 아닙니다",
    403: "포털 서버의 주소가 RA 의 허용 목록(HEAX_SSO_ALLOWED_IPS)에 없거나, 그 RA 계정이 비활성이거나 자동 생성이 꺼져 있습니다",
}


def why_failed(email: str) -> str:
    """그 사람의 위임 토큰을 마지막으로 못 받은 까닭 한 줄(없으면 빈 글). 비밀 · 토큰 · 응답 본문은 들어 있지 않다."""
    return _WHY.get((email or "").strip().lower(), "")


def _note_why(key: str, why: str) -> None:
    if len(_WHY) >= _WHY_MAX:
        _WHY.clear()
    _WHY[key] = why


def sso_url(settings: Settings) -> str:
    return settings.ra_sso_url or (settings.ra_base_url.rstrip("/") + "/api/auth/sso")


def _find(o):
    """응답 안 어딘가의 (토큰, 그 옆 expires_in) — RA 는 `{success, data: {…}}` 봉투라 게이트웨이(`_mint_user_pat`)와
    같은 규칙으로 깊이 찾는다. expires_in 은 토큰과 **같은 객체**에서 읽는다(따로 찾으면 남의 수명을 집을 수 있다)."""
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ("access_token", "token") and isinstance(v, str) and v.strip():
                return v.strip(), o.get("expires_in")
            got = _find(v)
            if got:
                return got
    return None


def forget(email: str) -> None:
    """캐시해 둔 토큰을 RA 가 거절했을 때(401) — 다음 호출이 새로 받게 한다."""
    _CACHE.pop((email or "").strip().lower(), None)


async def ra_user_token(settings: Settings, *, email: str, name: str = "") -> str | None:
    """그 사람의 RA 토큰. 꺼져 있거나(비밀 없음·RA 404) 받지 못하면 None."""
    global _OFF_LOGGED
    secret = (settings.ra_sso_secret or "").strip()
    key = (email or "").strip().lower()
    if not secret or not key:
        return None
    hit = _CACHE.get(key)
    if hit and hit[1] > time.monotonic():
        return hit[0]

    headers = {
        "X-Heax-Gateway-Secret": secret,
        "X-Heax-User-Email": key,
        "X-Heax-User-Name": _header_name(name or ""),
        # 게이트웨이(gateway)와 다른 이름 — 발급이 서로를 회수하지 않게 가른다.
        "X-Heax-Client": "hwax-portal",
    }
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
            r = await client.post(sso_url(settings), headers=headers)
    # UnicodeEncodeError 는 httpx.HTTPError 의 하위가 아니다 — ste 중계에서 한글 값으로 500 이 났던 그 자리다.
    except (httpx.HTTPError, UnicodeEncodeError) as exc:
        log.warning("ra sso call failed: %s", type(exc).__name__)
        _note_why(key, f"RA 의 위임 창구에 닿지 못했습니다({type(exc).__name__})")
        return None

    if r.status_code == 404:
        # RA 쪽이 아직 위임을 안 켰다(HEAX_SSO_SECRET 없음) — 포털 설정만 앞선 상태다.
        if not _OFF_LOGGED:
            log.info("ra sso is off on the RA side (404) — falling back to registered tokens")
            _OFF_LOGGED = True
        return None
    if r.status_code != 200:
        # 401 = 비밀 불일치 또는 메일 꼴 아님, 403 = 허용 IP 밖 또는 그 계정이 RA 에서 막힘. 본문은 싣지 않는다(무엇이 들었는지 모른다).
        log.warning("ra sso rejected for %s: HTTP %s", key, r.status_code)
        _note_why(key, _WHY_BY_STATUS.get(r.status_code, f"RA 의 위임 창구가 HTTP {r.status_code} 로 답했습니다"))
        return None
    try:
        body = r.json()
    except ValueError:
        log.warning("ra sso returned non-JSON (HTTP 200)")
        return None
    got = _find(body)
    if not got:
        log.warning("ra sso returned no token")
        return None
    token, exp = got
    # 값이 없거나 이상하면(bool·문자열·0 이하) 캐시 상한만 쓴다 — 게이트웨이 `_user_pat` 과 같은 규칙.
    ttl = MAX_TTL_S
    if isinstance(exp, (int, float)) and not isinstance(exp, bool) and exp > 0:
        ttl = min(MAX_TTL_S, exp - EARLY_S)
    if ttl > 0:
        _CACHE[key] = (token, time.monotonic() + ttl)
    _WHY.pop(key, None)
    log.info("ra sso token issued for %s", key)
    return token


async def revoke_for(settings: Settings, email: str, *, clients: tuple[str, ...] = ("hwax-portal",)) -> bool | None:
    """RA 에서 그 사람의 위임 토큰을 지운다(RA v0.170.0 `POST /api/auth/sso/revoke`) — 계정 정지(auth/routes/local.py)가 쓴다.

    RA 는 발급도 회수도 client 별이다. 기본은 포털이 받은 것(hwax-portal)만이고, 정지처럼 그 사람의 길을 다 끊을 때는 게이트웨이가
    받은 것(gateway)도 함께 넘긴다 — RA 위임 토큰은 2일을 살아 메모리에서 잊는 것만으로는 그동안 유효하다.
    돌려주는 것: True(모든 client 가 200) · False(닿지 못했거나 하나라도 거절) · None(이 박스에 RA 위임이 꺼져 있거나 RA 쪽이 404 —
    위임을 안 켰거나 회수 창구가 없는 옛 판이라 지울 토큰도 없다). 메모리의 토큰은 어느 경우든 먼저 잊는다."""
    forget(email)
    secret = (settings.ra_sso_secret or "").strip()
    key = (email or "").strip().lower()
    if not secret or not key:
        return None
    url = sso_url(settings).rstrip("/") + "/revoke"
    ok, off = True, 0
    for client_name in clients:
        headers = {"X-Heax-Gateway-Secret": secret, "X-Heax-User-Email": key, "X-Heax-Client": client_name}
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
                r = await client.post(url, headers=headers)
        except (httpx.HTTPError, UnicodeEncodeError) as exc:
            log.warning("ra sso revoke failed: %s", type(exc).__name__)
            ok = False
            continue
        if r.status_code == 404:
            off += 1
        elif r.status_code != 200:
            log.warning("ra sso revoke rejected for %s (%s): HTTP %s", key, client_name, r.status_code)
            ok = False
    if off == len(clients):
        return None
    return ok
