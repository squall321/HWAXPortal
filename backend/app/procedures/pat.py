"""절차용 단명 PAT — **단계 호출마다** 찍고 실행에 저장하지 않는다.

`agent/routes.py:_chat_user_pat` 과 **같은 체계**를 쓴다(새 공유비밀을 만들지 않는다).
게이트웨이는 이 토큰을 포털 JWKS 로 검증하므로 위조가 불가능하고, 도구 인가도 서비스
계정이 아니라 이 사람의 groups 로 이뤄진다.

다른 점 셋이 의도다.

1. **창(window) 결정성을 안 쓴다.** 그것은 agent-server 의 에이전트 캐시가 첫 토큰을 물고
   재사용하기 때문에 필요했다. 절차 기능은 agent-server 를 안 쓰고 게이트웨이는 요청마다
   검증하므로 요건이 아니다(따라도 무해하지만, 안 따르는 편이 수명이 길다).
2. **수명이 짧다.** 찍자마자 그 호출에만 쓴다. `_chat_user_pat` 은 창 시작+60분이라 잔여
   수명이 30~60분인데, 실행에 저장했다가 `gate: human` 뒤에 재개하면 401 이 난다(실측).
3. **`pat_name`·`jti` 로 챗과 구분한다.** 게이트웨이 감사는 이 클레임을 안 남기므로
   구분은 절차 자기 실행 기록이 맡지만(context-notes W-17), 토큰 자체에도 적어 둔다 —
   나중에 게이트웨이가 남기게 되면 그대로 갈린다.
"""

import logging
from datetime import UTC, datetime, timedelta

import jwt

logger = logging.getLogger(__name__)

LIFETIME_MIN = 15   # 한 호출에만 쓴다. 길 이유가 없다.
SKEW_SEC = 60       # 게이트웨이와 시계가 어긋나도 nbf 에 걸리지 않게.


def mint(keystore, settings, principal, run_id: str, step_ix: int) -> str | None:
    """`None` 이면 **실행하지 않는다** — 서비스 계정으로 대신 돌지 않는다.

    챗은 발급에 실패해도 GW_TOKEN 으로 도는 길이 있지만(대화가 끊기지 않게), 절차 기능은
    그러면 안 된다. 실행 기록의 명의가 실제 호출자와 달라지면 그 기록은 감사 정본이 못 된다.
    """
    try:
        now = datetime.now(tz=UTC)
        claims = {
            "iss": settings.jwt_issuer,
            "sub": principal.subject,
            "email": principal.email,
            "name": getattr(principal, "display_name", None),
            "groups": list(principal.groups or []),
            "aud": [settings.pat_chat_audience],
            "scope": "api",
            "scopes": ["chat"],
            "pat_name": "procedures",
            "iat": now,
            "nbf": now - timedelta(seconds=SKEW_SEC),
            "exp": now + timedelta(minutes=LIFETIME_MIN),
            # 실행·단계에 묶인다. 폐기 목록에 넣으면 그 호출만 막힌다.
            "jti": f"wb-{run_id}-{step_ix}",
        }
        return jwt.encode(claims, keystore.private_pem, algorithm="RS256",
                          headers={"kid": keystore.active_kid})
    except Exception:  # noqa: BLE001
        logger.warning("절차 PAT 발급 실패 run=%s step=%s — 실행을 세운다",
                       run_id, step_ix, exc_info=True)
        return None
