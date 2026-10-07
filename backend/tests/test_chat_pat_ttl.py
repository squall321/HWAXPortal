# 포털이 챗·심의 요청마다 찍는 사용자 PAT 의 수명(CHAT_PAT_TTL_S) — 허용하는 가장 긴 심의보다 오래 사는지, 창 안에서는 여전히 같은 토큰인지
"""에이전트 서버는 심의를 시작할 때 포털이 준 사용자 PAT 로 도구를 받아 **그 실행 끝까지** 쓴다 — 라운드마다의 좌석
조회와 맨 끝의 Report Archive 저장까지. 이 토큰의 수명이 '30분 창의 시작 + 60분' 이어서 시작 시점에 30~60분만 남았다.
이 경로에서 가장 짧은 한도였고, 그보다 오래 돈 심의는 좌석 조회가 도구 오류로 돌아오고 마지막 저장이 실패했다.
어디에도 자격 만료라는 말은 없었다.

자격은 누적 시간 한도라 가장 바깥이어야 한다. 기본 24시간(CHAT_PAT_TTL_S) — 남는 수명은 최소 23.5시간이다.
30분 창은 그대로다: 같은 창에서는 토큰이 바이트 단위로 같아야 에이전트 서버의 캐시가 맞는다.
"""
import time
import types

import jwt
import pytest

from app.agent.routes import _chat_user_pat
from app.auth.keystore import KeyStore
from app.config import Settings

_WHO = types.SimpleNamespace(subject="u1", email="u1@x.io", display_name="U", groups=["feat:deliberation"])

# 리스크 패널 벽시계(HWAXRISK_PANEL_TIMEOUT_S 기본값)와 그 뒤의 Report Archive 저장 — 다른 리포의 값이라 여기 숫자로 적는다.
# 그쪽을 올리면 이 수와 CHAT_PAT_TTL_S 를 같이 본다(결정표의 자격 사슬).
_LONGEST_RUN_S = 43200 + 660


def _claims(token: str) -> dict:
    return jwt.decode(token, options={"verify_signature": False}, algorithms=["RS256"])


@pytest.fixture()
def ks(tmp_path):
    return KeyStore(Settings(_env_file=None, jwt_keys_dir=str(tmp_path / "keys")))


def test_시작_시점에_남는_수명이_가장_긴_심의보다_길다(ks):
    s = Settings(_env_file=None)
    c = _claims(_chat_user_pat(ks, s, _WHO))
    assert c["exp"] - c["iat"] == 86400 == s.chat_pat_ttl_s
    assert c["iat"] % 1800 == 0, "수명은 30분 창의 시작에서 센다"
    left = c["exp"] - time.time()
    assert left >= 86400 - 1800, f"남은 수명 {left:.0f}초 — 창 끝에서 찍혀도 (수명 − 30분)은 남아야 한다"
    assert s.chat_pat_ttl_s - 1800 > _LONGEST_RUN_S, (
        "기본값이 허용하는 가장 긴 실행(리스크 패널 벽시계 + RA 저장)보다 짧다 — 긴 심의가 끝에서 보고서를 잃는다")


def test_손잡이로_수명을_바꾼다(ks):
    c = _claims(_chat_user_pat(ks, Settings(_env_file=None, chat_pat_ttl_s=46800), _WHO))
    assert c["exp"] - c["iat"] == 46800


def test_같은_창에서는_토큰이_바이트_단위로_같다(ks):
    """수명을 늘려도 이 성질은 그대로여야 한다 — 요청마다 다른 토큰이면 에이전트 서버 캐시가 첫 토큰을 물고 나머지를 버린다."""
    s = Settings(_env_file=None)
    for _ in range(3):                    # 두 번 찍는 사이에 창이 넘어가면 다시 한다(30분에 한 번 있는 경계)
        a, b = _chat_user_pat(ks, s, _WHO), _chat_user_pat(ks, s, _WHO)
        if _claims(a)["iat"] == _claims(b)["iat"]:
            break
    assert a == b
    c = _claims(a)
    assert c["jti"] == f"chat-u1-{c['iat']}", "창별 jti — 폐기 목록에 넣으면 그 창이 막힌다"
    assert c["scopes"] == ["chat"] and c["pat_name"] == "chat-session"
