# 포털이 챗·심의 요청마다 찍는 사용자 PAT 의 수명(CHAT_PAT_TTL_S) — 허용하는 가장 긴 심의보다 오래 사는지, 창 안에서는 여전히 같은 토큰인지
"""에이전트 서버는 심의를 시작할 때 포털이 준 사용자 PAT 로 도구를 받아 **그 실행 끝까지** 쓴다 — 라운드마다의 좌석
조회와 맨 끝의 Report Archive 저장까지. 이 토큰의 수명이 '30분 창의 시작 + 60분' 이어서 시작 시점에 30~60분만 남았다.
이 경로에서 가장 짧은 한도였고, 그보다 오래 돈 심의는 좌석 조회가 도구 오류로 돌아오고 마지막 저장이 실패했다.
어디에도 자격 만료라는 말은 없었다.

자격은 누적 시간 한도라 가장 바깥이어야 한다. 기본 24시간(CHAT_PAT_TTL_S) — 남는 수명은 최소 23.5시간이다.
30분 창은 그대로다: 같은 창에서는 토큰이 바이트 단위로 같아야 에이전트 서버의 캐시가 맞는다.
"""
import re
import time
import types
from pathlib import Path

import jwt
import pytest

from app import config
from app.agent.routes import _chat_user_pat
from app.auth.keystore import KeyStore
from app.config import Settings, startup_warnings

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


# ── 하한 — 발급 창(30분)보다 길지 않은 수명은 찍자마자 만료된 토큰이다 ─────────────────────────────────────
# 수명은 창의 **시작**에서 센다. 0 이면 어느 시점에 찍어도 이미 만료고, 900 이면 창의 앞 절반만 살고, 1800 이면 찍는 순간에는
# 살아 있어도 0~30분 뒤에 끝난다. 예시 파일에서 바로 위의 두 손잡이가 '0 = 끔' 이라 '만료 없음' 을 뜻하려고 0 을 넣기 쉽다 —
# 그러면 모든 챗·심의가 만료된 토큰을 받아 게이트웨이가 401 을 주고, 엔진은 조회와 보고서 저장을 서비스 계정으로 한다.
def _codes(**kw) -> list[str]:
    return [code for code, _ in startup_warnings(Settings(_env_file=None, **kw))]


@pytest.mark.parametrize("ttl", [0, -5, 900, 1800])
def test_창보다_길지_않은_수명은_쓰지_않고_기본값으로_찍는다(ks, ttl):
    s = Settings(_env_file=None, chat_pat_ttl_s=ttl)
    token = _chat_user_pat(ks, s, _WHO)
    # 게이트웨이가 하는 검증 그대로(서명·청중·필수 클레임·여유 30초) — 수명이 끝난 토큰이면 여기서 ExpiredSignatureError 다
    c = jwt.decode(token, ks.public_pem(ks.active_kid), algorithms=["RS256"], audience=s.pat_chat_audience,
                   options={"require": ["exp", "aud", "sub", "jti"]}, leeway=30)
    assert c["exp"] - time.time() > _LONGEST_RUN_S, "기본값(24시간)으로 찍어야 가장 긴 실행을 감싼다"
    assert "chat_pat_ttl" in _codes(chat_pat_ttl_s=ttl), "버린 값은 기동 로그(CRITICAL)와 /health/ready 의 temporary 에 실린다"


def test_가장_긴_실행보다_짧은_수명은_쓰되_기동_때_알린다(ks):
    """46800 밑으로는 내리지 않는다는 것이 주석뿐이었다 — 3600 을 적은 박스는 한 시간 넘은 심의가 도는 중에 자격을 잃는다."""
    c = _claims(_chat_user_pat(ks, Settings(_env_file=None, chat_pat_ttl_s=3600), _WHO))
    assert c["exp"] - c["iat"] == 3600, "창보다 길면 적은 값을 그대로 쓴다 — 기동을 막지도, 값을 바꾸지도 않는다"
    (text,) = [t for code, t in startup_warnings(Settings(_env_file=None, chat_pat_ttl_s=3600)) if code == "chat_pat_ttl"]
    assert "CHAT_PAT_TTL_S=3600" in text and "46800" in text
    assert "chat_pat_ttl" not in _codes(chat_pat_ttl_s=46800) and "chat_pat_ttl" not in _codes()


def test_하한이_아는_창이_토큰을_찍는_창과_같은_수다():
    """하한은 창의 길이에서 나온다 — 창을 바꾸면서 하한을 그대로 두면 '찍자마자 만료' 가 다시 열린다."""
    src = (Path(__file__).resolve().parents[1] / "app/agent/routes.py").read_text(encoding="utf-8")
    m = re.search(r"int\(now\.timestamp\(\)\) // (\d+) \* \1\b", src)
    assert m, "routes._chat_user_pat 에서 창의 길이를 못 읽었다 — 줄 모양이 바뀌었으면 이 식을 고쳐라"
    assert int(m.group(1)) == config.CHAT_PAT_WINDOW_S
    assert config.CHAT_PAT_TTL_MIN_S - config.CHAT_PAT_WINDOW_S > _LONGEST_RUN_S, (
        "알리는 문턱은 창 끝에서 찍힌 토큰도 가장 긴 실행(패널 벽시계 + 보고서 저장)을 감싸는 값이어야 한다")
