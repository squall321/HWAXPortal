# 공개 리포가 **쓸 수 있는 키**를 내주지 않게 막는다 — 세션 키 자리표시·폴백·기동 거부
#
# 사고(2026-09-16). dev 포털이 `SESSION_SECRET=change-me-infra-dev` 로 떠 있었다. 이 값은 공개 리포의
# `infra/.env.example` 에 있었고, 복사한 그대로인 `infra/.env` 가 그걸 썼다(0.0.0.0 바인드, oidc 로 실사용자).
# 세션 토큰은 HS256 에 `sub`·`groups` 를 싣는다 — 키를 알면 아무 사용자·관리자로 위조한다. 아무것도
# 거부하지 않았다. `start.sh` 도 비어 있으면 같은 공개값으로 **조용히** 채웠다.
#
# ⚠ 이 검사를 만들기 전, 추적 env 파일의 "실값 모양" 을 **정규식으로 짐작**했다가 `.env.real` 의
#   `REPLACE_WITH_openssl_rand_hex_32`(32자)·키트의 `@GENERATE_HEX32@`(16자)를 실제 비밀로 잘못 보고했다.
#   짐작은 틀린다. 그래서 여기는 **허용 목록**이다 — 비밀 이름의 키는 비었거나, 알려진 표식이어야 한다.
#   실패 메시지에는 값을 싣지 않는다(진짜 비밀이 들어왔다면 CI 로그로 또 샌다).
import re
import subprocess
from pathlib import Path

from app.config import PUBLIC_SESSION_SECRETS, SESSION_SECRET_MIN_LEN, Settings, startup_problems

ROOT = Path(__file__).resolve().parents[2]
START_SH = ROOT / "infra" / "scripts" / "start.sh"

_SECRET_KEY = re.compile(r"SECRET|TOKEN|PASSWORD|PASSWD|API_KEY|PRIVATE_KEY|CREDENTIAL", re.I)
# 이름에 TOKEN 이 들어도 경로·주소인 키(`TOKEN_STORE_PATH` 등)는 비밀이 아니다.
_NOT_SECRET = re.compile(r"_(PATH|DIR|FILE|URL)$", re.I)
# 비밀 칸에 허용하는 값 — 비었거나, 적용 시점에 채워지는 표식이거나, 포털이 **기동을 거부하는** 자리표시.
_ALLOWED = re.compile(r"^(|@GENERATE_HEX32@|@FROM_RA:[A-Z0-9_]+@|<[^<>]*>|REPLACE_WITH_[A-Za-z0-9_]+)$")
_ENV_FILE = re.compile(r"(^|/)\.env(\.[^/]+)?$|(^|/)env-kits/[^/]+\.env$")
_SECRET_FALLBACK = re.compile(r"\$\{[A-Z0-9_]*(SECRET|TOKEN|PASSWORD|PASSWD|API_KEY)[A-Z0-9_]*:-[^}]+\}")


def _tracked() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True)
    return [p for p in out.stdout.splitlines() if p]


def _settings(**kw) -> Settings:
    # `_env_file=None` — 이 박스의 backend/.env 가 검사를 오염시키지 않게. 인자는 환경변수보다 우선한다.
    return Settings(_env_file=None, **kw)


GOOD = "0123456789abcdef" * 4  # 64자 — 공개값 아님


# ── 기동 거부 ────────────────────────────────────────────────────────────────────────────
def test_공개된_세션_키로는_실사용자_구성이_기동하지_않는다():
    for secret in sorted(PUBLIC_SESSION_SECRETS):
        for env, provider in (("dev", "oidc"), ("prod", "oidc"), ("prod", "saml")):
            probs = startup_problems(_settings(app_env=env, auth_provider=provider, session_secret=secret))
            assert any("공개된 값" in p for p in probs), (env, provider, len(secret))


def test_짧은_키도_거부하고_제대로_된_키는_통과한다():
    short = "x" * (SESSION_SECRET_MIN_LEN - 1)
    assert any("자다" in p for p in startup_problems(
        _settings(app_env="prod", auth_provider="oidc", session_secret=short)))
    assert startup_problems(_settings(app_env="prod", auth_provider="oidc", session_secret=GOOD)) == []
    assert startup_problems(_settings(app_env="dev", auth_provider="saml", session_secret=GOOD)) == []


def test_로컬_개발_dev_mock_은_막지_않는다():
    """로컬에서 키 없이 띄우는 길은 남긴다 — 실사용자가 없는 구성이다."""
    assert startup_problems(_settings(app_env="dev", auth_provider="mock",
                                      session_secret="change-me-dev-only")) == []


def test_prod_의_mock_로그인은_좋은_키여도_거부한다():
    probs = startup_problems(_settings(app_env="prod", auth_provider="mock", session_secret=GOOD))
    assert any("AUTH_PROVIDER=mock" in p for p in probs), probs


# ── 짝 맞추기 — 같은 목록이 두 곳에 있다 ────────────────────────────────────────────────────
def test_start_sh_의_공개값_목록이_포털과_같다():
    """start.sh 가 모르는 공개값이면 교체하지 않고 넘기고, 포털은 그걸 거부해 **기동이 실패**한다."""
    m = re.search(r'case "\$_ss" in ([^)]+)\) _ss="" ;; esac', START_SH.read_text(encoding="utf-8"))
    assert m, "start.sh 의 공개값 case 줄을 못 찾았다 — 모양이 바뀌었으면 이 검사를 맞춰라"
    assert set(m.group(1).split("|")) == set(PUBLIC_SESSION_SECRETS)


def test_템플릿의_자리표시는_포털이_거부하는_값이다():
    """템플릿 자리표시를 바꾸면(예: 문구 수정) 포털 목록도 따라가야 한다 — 안 그러면 새 문구가
    32자 이상일 때 **그대로 기동한다**."""
    for rel in ("infra/.env.example", ".env.real"):
        p = ROOT / rel
        if not p.is_file():
            continue
        for ln in p.read_text(encoding="utf-8").splitlines():
            if ln.startswith("SESSION_SECRET="):
                v = ln.partition("=")[2].strip().strip('"').strip("'")
                assert v == "" or v in PUBLIC_SESSION_SECRETS, (rel, len(v))


# ── 추적 파일 ────────────────────────────────────────────────────────────────────────────
def test_셸_스크립트가_비밀_변수에_기본값을_주지_않는다():
    """`${SESSION_SECRET:-change-me-infra-dev}` 같은 폴백은 **비어 있으면 공개값으로 뜬다**는 뜻이다."""
    hits = []
    for rel in _tracked():
        if not rel.endswith(".sh"):
            continue
        for i, ln in enumerate((ROOT / rel).read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if _SECRET_FALLBACK.search(ln):
                hits.append(f"{rel}:{i}")
    assert not hits, f"비밀 변수에 기본값이 있다: {hits}"


def test_추적_env_파일의_비밀_칸은_비었거나_표식이다():
    files = [rel for rel in _tracked() if _ENV_FILE.search(rel)]
    assert len(files) >= 5, f"env 파일을 거의 못 찾았다({len(files)}) — 경로 규칙이 틀렸을 수 있다"
    bad, seen = [], 0
    for rel in files:
        for i, ln in enumerate((ROOT / rel).read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if "=" not in ln or ln.lstrip().startswith("#"):
                continue
            key, _, val = ln.partition("=")
            if not _SECRET_KEY.search(key) or _NOT_SECRET.search(key.strip()):
                continue
            seen += 1
            v = val.split(" #")[0].strip().strip('"').strip("'")
            # 포털이 기동을 거부하는 공개 자리표시(로컬 개발 기본값 등)는 둬도 된다 — 실사용자 구성에서 못 뜬다.
            if not (_ALLOWED.match(v) or v in PUBLIC_SESSION_SECRETS):
                bad.append(f"{rel}:{i} {key.strip()} (값 {len(v)}자)")   # 값은 싣지 않는다
    assert seen >= 5, f"비밀 칸을 거의 못 봤다({seen}) — 검사가 헛돌고 있을 수 있다"
    assert not bad, "추적 파일에 비밀 칸의 실값(또는 모르는 자리표시)이 있다: " + " · ".join(bad)


# ── 배선 — 검사 함수가 있어도 기동 경로가 안 부르면 소용없다 ─────────────────────────────────
def test_포털_기동이_공개_키를_실제로_거부한다(monkeypatch):
    """`startup_problems` 만 시험하면 main.py 에서 호출이 빠져도 초록이다. lifespan 을 실제로 태운다."""
    import pytest
    from fastapi.testclient import TestClient

    import app.main as main

    bad = _settings(app_env="prod", auth_provider="oidc", session_secret="change-me-infra-dev")
    monkeypatch.setattr(main, "settings", bad)
    with pytest.raises(RuntimeError, match="기동 거부"):
        with TestClient(main.app):
            pass
