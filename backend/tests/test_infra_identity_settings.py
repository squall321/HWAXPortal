# 새 신원·권한 설정 넷(PORTAL_ADMIN_EMAILS·SSO_DEFAULT_AFFILIATION·SAML_ATTR_DEPT_ID·SAML_ATTR_SABUN)이 infra/.env 에서 포털 컨테이너까지 닿는지(8·9·10차 요청 #1·#5·#15·#16)
"""왜 — 설정은 코드(config.py)에 생겼는데 닿는 길이 없으면 **문서에는 켜져 있고 운영에서는 죽어 있다.** start.sh 는 포털을
`--env` 로 띄우고(backend/.env 를 덮는다), 같은 파일이 SAML 에 대해 「호스트 env 상속에만 기대면 조용히 되돌아간다」고 적어 둔
그대로다. `SAML_` 로 시작하는 둘은 그 순회가 넘기지만 나머지 둘은 접두가 달라 걸리지 않았다 — 상속이 끊기는 순간 고정 관리자가
일반 사용자가 되고 기본 소속이 꺼지는데, infra/.env 에는 값이 적혀 있어 아무도 의심하지 않는다.

닿는 길은 셋이 이어져야 한다 — ① 예시 파일(infra/.env.example)에 이름이 있다(env-sync 가 기존 박스에 알린다) ② start.sh 가
컨테이너에 넘긴다 ③ 포털 설정이 **그 이름으로** 읽는다. 셋 중 하나의 철자만 달라도 조용히 끊긴다.

기동 블록은 test_infra_no_proxy 의 대역(apptainer 자리에 선 스크립트가 받은 인자를 적는다)으로 원문 그대로 돌린다.
주소·코드는 지어낸 값이다(문서용 도메인 · C999 · D12345 꼴).
"""
import re
from pathlib import Path

import pytest

from app.config import Settings
from tests.test_infra_no_proxy import start_portal  # noqa: F401 — 기동 블록을 임시 리포에서 돌리는 대역

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = (ROOT / "infra/.env.example").read_text(encoding="utf-8")

ADMINS = "kim.admin@corp.example,lee.admin@sub.corp.example"
DEPT_URI = "http://schemas.corp.example/ws/2008/06/identity/claims/DeptId"
SABUN_URI = "http://schemas.corp.example/ws/2008/06/identity/claims/Sabun"
# 설정 이름 → infra/.env 에 적을 값
VALUES = {
    "PORTAL_ADMIN_EMAILS": ADMINS,
    "SSO_DEFAULT_AFFILIATION": "PARTNER",
    "SAML_ATTR_DEPT_ID": DEPT_URI,
    "SAML_ATTR_SABUN": SABUN_URI,
}


def test_네_설정이_컨테이너까지_닿는다(start_portal):  # noqa: F811
    """**이 시험이 이 파일의 이유다** — infra/.env 에 적은 값이 `--env` 로 명시돼 나간다(상속에 기대지 않는다)."""
    envs = start_portal("".join(f"{k}={v}\n" for k, v in VALUES.items()))
    for key, value in VALUES.items():
        assert envs.get(key) == value, f"{key} 가 컨테이너에 명시돼 넘어가지 않았다 — 상속이 끊기면 조용히 꺼진다"


def test_콤마_목록과_따옴표_값도_글자_그대로_간다(start_portal):  # noqa: F811
    """관리자 목록은 콤마로 잇는다 — 공백을 섞어 적으면 따옴표가 필요하고, bash 가 벗긴 값이 그대로 가야 한다."""
    envs = start_portal('PORTAL_ADMIN_EMAILS="kim.admin@corp.example, lee.admin@sub.corp.example"   # 주소가 둘인 사람은 둘 다\n')
    assert envs["PORTAL_ADMIN_EMAILS"] == "kim.admin@corp.example, lee.admin@sub.corp.example"


@pytest.mark.parametrize("infra_env", ["", "PORTAL_ADMIN_EMAILS=\nSSO_DEFAULT_AFFILIATION=\n",
                                       "# PORTAL_ADMIN_EMAILS=   # ⚠ 값을 운영자가 정해야 한다\n# SSO_DEFAULT_AFFILIATION=\n"])
def test_비어_있으면_빈_값을_명시하지_않는다(start_portal, infra_env):  # noqa: F811
    """`--env KEY=` 는 backend/.env 를 이긴다 — 빈 값을 명시하면 그 파일에 적어 둔 고정 관리자를 덮어 끈다.
    set -u 아래에서 미정의 변수를 읽어 기동이 죽지도 않아야 한다."""
    envs = start_portal(infra_env)
    assert "PORTAL_ADMIN_EMAILS" not in envs and "SSO_DEFAULT_AFFILIATION" not in envs
    assert envs["AUTH_PROVIDER"] == "mock", "다른 --env 는 그대로다"


def test_운영자_셸에서_준_값도_간다(start_portal):  # noqa: F811
    """infra/.env 가 아니라 띄우는 셸에 export 해 둔 박스도 같다(_common.sh 는 infra/.env 를 그 위에 소싱한다)."""
    envs = start_portal(PORTAL_ADMIN_EMAILS="kim.admin@corp.example")
    assert envs["PORTAL_ADMIN_EMAILS"] == "kim.admin@corp.example"


# ── ① 예시 파일 — 이름이 있어야 env-sync 가 기존 박스의 .env 에 '이런 설정이 생겼다' 고 알린다 ─────────────────
def _declared(text: str) -> dict[str, str]:
    """예시 파일이 선언한 키 → 값. 활성 줄과 주석 줄(`# KEY=`) 둘 다 선언이다(env-sync 와 같은 규칙)."""
    return dict(m.groups() for m in re.finditer(r"^[ \t]*#?[ \t]*([A-Z][A-Z0-9_]*)=(.*)$", text, re.M))


@pytest.mark.parametrize("key", sorted(VALUES))
def test_예시_파일이_선언하고_포털이_그_이름으로_읽는다(key, monkeypatch):
    declared = _declared(EXAMPLE)
    assert key in declared, f"infra/.env.example 에 {key} 가 없다 — 기존 박스는 이 설정이 생긴 줄 모른다"
    # ③ 철자 — 예시 파일의 이름이 설정 클래스의 칸과 글자까지 같아야 읽힌다(extra='ignore' 라 오타는 조용히 버려진다)
    assert key.lower() in Settings.model_fields, f"{key} 라는 설정 칸이 없다 — 예시 파일과 config.py 의 이름이 갈렸다"
    monkeypatch.setenv(key, VALUES[key])
    assert getattr(Settings(_env_file=None), key.lower()) == VALUES[key]


@pytest.mark.parametrize("key", sorted(VALUES))
def test_예시_파일의_기본은_꺼짐이고_실제_값을_싣지_않는다(key):
    """네 설정 모두 비우면 꺼진다. 예시 값이 켜진 채 복사되면 '그럴듯하게 틀린 설정' 이 되고, 관리자·소속은 그것이 곧 권한이다."""
    line = next(ln for ln in EXAMPLE.splitlines() if re.match(rf"^[ \t]*#?[ \t]*{key}=", ln))
    assert line.lstrip().startswith("#"), f"{key} 가 예시 파일에서 켜져 있다"
    value = _declared(EXAMPLE)[key].split("#")[0].strip()
    assert value == "" or re.fullmatch(r"<[^<>]+>", value), f"{key} 의 예시 값은 비우거나 <자리표시> 여야 한다 — 받은 값 {value!r}"


def test_env_sync_가_기존_박스의_env_에_네_설정을_주석으로_알린다(tmp_path):
    """이미 배포된 박스의 infra/.env 는 예시 파일을 다시 복사하지 않는다 — update-all 1c 의 env-sync 가 없는 키를 덧붙여 알린다.
    실제 예시 파일과 '이 변경 전' 모양의 .env 로 env-sync 를 **그대로 돌린다**. 넷 다 주석으로(꺼진 채) 들어가야 한다 —
    활성 줄로 들어가면 빈 값이 export 되어 backend/.env 에 적어 둔 값을 덮는다."""
    import subprocess

    box = tmp_path / "HWAXPortal" / "infra"
    box.mkdir(parents=True)
    (box / ".env.example").write_text(EXAMPLE, encoding="utf-8")
    # 이 변경 전의 박스 — 예시 파일에서 네 설정의 줄만 뺀 것을 그 박스의 .env 로 삼는다
    old_env = "\n".join(ln for ln in EXAMPLE.splitlines() if not any(re.match(rf"^[ \t]*#?[ \t]*{k}=", ln) for k in VALUES)) + "\n"
    (box / ".env").write_text(old_env, encoding="utf-8")
    r = subprocess.run(["bash", str(ROOT / "infra/scripts/env-sync.sh"), str(box.parent)], capture_output=True, text=True,
                       timeout=60, env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)})
    assert r.returncode == 0, r.stdout + r.stderr
    added = (box / ".env").read_text(encoding="utf-8")[len(old_env):]
    for key in VALUES:
        assert re.search(rf"^# {key}=", added, re.M), f"{key} 가 기존 박스의 .env 에 알려지지 않았다\n{r.stdout}"
        assert not re.search(rf"^{key}=", added, re.M), f"{key} 가 켜진 줄로 들어갔다"
        assert key in r.stdout, "무엇이 새로 생겼는지 실행 출력에도 나온다"
    assert _declared(added).keys() == set(VALUES), "이 넷 말고는 덧붙이지 않는다(예시 파일의 다른 줄은 이미 있다)"


def test_전권_소속_경고가_기본_소속_옆에_있다():
    """기본 소속에 전권 소속(grants '*')을 적으면 IdP 를 통과한 누구나 전권이다 — 값을 적는 자리에서 읽혀야 한다."""
    i = EXAMPLE.index("SSO_DEFAULT_AFFILIATION=")
    near = EXAMPLE[max(0, i - 900):i]
    assert "전권" in near and "sso_affiliation_map" in near
