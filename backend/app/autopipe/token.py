# 자동 파이프라인 호출마다 찍는 15분짜리 서비스 토큰 — 클레임은 core-link 서비스 PAT 꼴(service_claims) 그대로, jti 만 svc-ap-<실행>-<단계>(AP-8)
"""길게 사는 서비스 PAT 를 저장하지 않고 호출마다 찍는다(portal-api §7 · context-notes AP-8). 저장할 비밀 · 만료 관리 · 유출 표면이 없다.

- 클레임은 `app/auth/service_pat.service_claims` 가 짓는다 — 게이트웨이 `_service_scope` 와 두 리포 계약 시험으로 묶인 꼴이다. 여기서는 수명(15분) ·
  nbf(시계 어긋남 60초) · jti 셋만 바꾼다. jti 는 게이트웨이가 `svc-` 머리를 요구한다 — `svc-ap-<실행 앞 12자>-<단계 id>`.
- 토큰 원장(`record_pat`)에 적지 않는다 — 호출마다 한 줄씩 원장이 끝없이 자란다. 관리자 서비스 토큰 목록은 사람이 발급한 길게 사는 토큰을 보는
  화면이고, 이 토큰은 15분 뒤 저절로 죽는다. 무엇을 불렀는지는 원장 auto_events 와 게이트웨이 감사(caller system:auto-pipeline · note svc:ap-…)가 남긴다.
- 막는 길은 둘이다 — 게이트웨이 허용 목록에서 작업을 빼거나, 포털 스위치(AUTO_PIPELINE_ENABLED)를 끈다. jti 를 폐기 목록에 넣으면 그 단계만 막힌다.
"""
from __future__ import annotations

import logging
import re
from datetime import UTC, datetime

import jwt

from app.auth.service_pat import SERVICE_JTI_PREFIX, service_claims
from app.autopipe import JOB

logger = logging.getLogger(__name__)

LIFETIME_S = 900          # 한 호출에만 쓴다 — 절차 PAT 와 같은 15분
SKEW_S = 60               # 게이트웨이와 시계가 어긋나도 nbf 에 걸리지 않게(절차 PAT 와 같다)
_TAG_RE = re.compile(r"[^a-z0-9_-]")


def jti_for(run: str, step: str) -> str:
    """svc-ap-<실행 앞 12자>-<단계> — 실행 · 단계에 묶인다. 원천 감지는 run='src' · 단계=원천 키, 앱 목록은 run='prof'."""
    tag = lambda s: _TAG_RE.sub("", str(s).lower())[:40] or "x"       # noqa: E731
    return f"{SERVICE_JTI_PREFIX}ap-{tag(run)[:12]}-{tag(step)}"


def claims(iss: str, run: str, step: str, now: int | None = None) -> dict:
    now = int(datetime.now(tz=UTC).timestamp()) if now is None else int(now)
    c = service_claims(iss=iss, job=JOB, now=now, days=1)
    c.update(exp=now + LIFETIME_S, nbf=now - SKEW_S, jti=jti_for(run, step))
    return c


def mint(keystore, settings, run: str, step: str) -> str | None:
    """None 이면 그 호출을 하지 않는다(다른 신원으로 대신 돌지 않는다 — 절차 PAT 와 같은 자세)."""
    try:
        return jwt.encode(claims(settings.jwt_issuer, run, step), keystore.private_pem, algorithm="RS256",
                          headers={"kid": keystore.active_kid})
    except Exception:  # noqa: BLE001
        logger.warning("자동 파이프라인 서비스 토큰 발급 실패 run=%s step=%s — 그 호출을 세운다", run, step, exc_info=True)
        return None
