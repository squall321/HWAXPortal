# RA 사람별 위임 — 포털이 RA 전용 공유 비밀로 그 사람의 RA 토큰을 그 자리에서 받는다(ste 방식, docs/sso-delegation)
"""RA 위임 토큰 도우미.

  POST {ra_sso_url}  헤더 X-Heax-Gateway-Secret · X-Heax-User-Email · X-Heax-User-Name · X-Heax-Client
                     → 200 {success, data: {access_token, expires_in, …}}  · 404 꺼짐 · 401 비밀 불일치 · 403 계정 막힘

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
# 캐시 상한 — RA 위임 토큰은 12시간이다. 만료 직전 토큰을 쓰지 않게 expires_in 보다 2분 일찍 버리고, 그래도 11시간을 넘기지 않는다.
MAX_TTL_S = 11 * 3600
EARLY_S = 120

# {email: (token, 만료 monotonic)}. 프로세스 하나의 메모리다 — 재기동하면 비고 다시 받으면 된다.
_CACHE: dict[str, tuple[str, float]] = {}
# 404(RA 쪽 꺼짐)는 설정 상태라 매번 경고하면 소음이다 — 프로세스당 한 번만 남긴다.
_OFF_LOGGED = False


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
        return None

    if r.status_code == 404:
        # RA 쪽이 아직 위임을 안 켰다(HEAX_SSO_SECRET 없음) — 포털 설정만 앞선 상태다.
        if not _OFF_LOGGED:
            log.info("ra sso is off on the RA side (404) — falling back to registered tokens")
            _OFF_LOGGED = True
        return None
    if r.status_code != 200:
        # 401 = 비밀 불일치, 403 = 그 계정이 RA 에서 막힘. 본문은 싣지 않는다(무엇이 들었는지 모른다).
        log.warning("ra sso rejected for %s: HTTP %s", key, r.status_code)
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
    log.info("ra sso token issued for %s", key)
    return token
