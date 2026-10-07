# 챗·심의 경로의 포털 시간 한도 넷(AGENT_STREAM_IDLE_TIMEOUT_S·AGENT_UNARY_TIMEOUT_S·CHAT_PAT_TTL_S·CONV_STORE_BUSY_TIMEOUT_S)이 infra/.env 에서 포털 컨테이너까지 닿는지
"""왜 — 한도를 손잡이로 내도 닿는 길이 없으면 **문서에는 늘려 놓았고 운영에서는 기본값으로 돈다.** 이 넷은 몇 시간짜리 심의가
걸리는 자리라(릴레이 침묵 · 도우미 대기 · 사용자 PAT 수명 · 대화 저장 잠금), 어긋난 것을 아는 때가 심의 하나를 잃은 뒤다.

닿는 길은 셋이 이어져야 한다(test_infra_identity_settings 와 같은 사슬) — ① 예시 파일(infra/.env.example)에 이름이 있다
(env-sync 가 기존 박스에 알린다) ② start.sh 가 컨테이너에 **명시해서** 넘긴다(상속에 기대지 않는다) ③ 포털 설정이 **그 이름으로**
읽는다. 셋 중 하나의 철자만 달라도 조용히 끊긴다(Settings 는 extra='ignore' 라 오타를 버린다).

기동 블록은 test_infra_no_proxy 의 대역(apptainer 자리에 선 스크립트가 받은 인자를 적는다)으로 원문 그대로 돌린다.
"""
import re
import subprocess
from pathlib import Path

import pytest

from app.config import Settings
from tests.test_infra_no_proxy import start_portal  # noqa: F401 — 기동 블록을 임시 리포에서 돌리는 대역

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = (ROOT / "infra/.env.example").read_text(encoding="utf-8")

# 설정 이름 → (infra/.env 에 적을 값, 코드 기본값). 적을 값은 기본값과 달라야 '넘어갔다' 를 가른다.
KNOBS = {
    "AGENT_STREAM_IDLE_TIMEOUT_S": ("60000", 46800),
    "AGENT_UNARY_TIMEOUT_S": ("900", 600),
    "CHAT_PAT_TTL_S": ("172800", 86400),
    "CONV_STORE_BUSY_TIMEOUT_S": ("45", 30),
}


def test_네_한도가_컨테이너까지_닿는다(start_portal):  # noqa: F811
    """**이 시험이 이 파일의 이유다** — infra/.env 에 늘려 적은 값이 `--env` 로 명시돼 나간다."""
    envs = start_portal("".join(f"{k}={v}   # 박스 사정\n" for k, (v, _) in KNOBS.items()))
    for key, (value, _) in KNOBS.items():
        assert envs.get(key) == value, f"{key} 가 컨테이너에 명시돼 넘어가지 않았다 — 상속이 끊기면 조용히 기본값으로 돈다"


@pytest.mark.parametrize("infra_env", ["", "".join(f"{k}=\n" for k in KNOBS), "".join(f"# {k}={d}\n" for k, (_, d) in KNOBS.items())])
def test_안_적었으면_빈_값을_명시하지_않는다(start_portal, infra_env):  # noqa: F811
    """`--env KEY=` 는 backend/.env 를 이긴다 — 빈 값을 명시하면 그 파일에 적어 둔 값을 덮고, 숫자 칸에 빈 문자열이 들어가
    포털이 기동을 거부한다. env-sync 가 넣는 주석 줄(`# KEY=기본값`)도 '안 적은 것' 이다. set -u 아래에서 죽지도 않아야 한다."""
    envs = start_portal(infra_env)
    assert not set(KNOBS) & set(envs), envs
    assert envs["AUTH_PROVIDER"] == "mock", "다른 --env 는 그대로다"


def test_운영자_셸에서_준_값도_간다(start_portal):  # noqa: F811
    envs = start_portal(CHAT_PAT_TTL_S="90000")
    assert envs["CHAT_PAT_TTL_S"] == "90000"


def _declared(text: str) -> dict[str, str]:
    """예시 파일이 선언한 키 → 값. 활성 줄과 주석 줄(`# KEY=`) 둘 다 선언이다(env-sync 와 같은 규칙)."""
    return dict(m.groups() for m in re.finditer(r"^[ \t]*#?[ \t]*([A-Z][A-Z0-9_]*)=(.*)$", text, re.M))


@pytest.mark.parametrize("key", sorted(KNOBS))
def test_예시_파일이_선언하고_포털이_그_이름으로_읽는다(key, monkeypatch):
    value, default = KNOBS[key]
    declared = _declared(EXAMPLE)
    assert key in declared, f"infra/.env.example 에 {key} 가 없다 — 기존 박스는 이 손잡이가 생긴 줄 모른다"
    assert key.lower() in Settings.model_fields, f"{key} 라는 설정 칸이 없다 — 예시 파일과 config.py 의 이름이 갈렸다"
    monkeypatch.setenv(key, value)
    assert float(getattr(Settings(_env_file=None), key.lower())) == float(value)
    # 예시 파일에 적힌 값은 코드 기본값과 같다 — 어긋나면 주석을 풀어 쓴 박스만 다른 한도로 돈다
    assert float(declared[key].split("#")[0].strip()) == float(default) == float(Settings.model_fields[key.lower()].default), key


@pytest.mark.parametrize("key", sorted(KNOBS))
def test_예시_파일에서는_주석_줄이다(key):
    """켜진 줄로 적혀 있으면 복사한 박스가 그 값에 묶인다 — 코드 기본값을 나중에 올려도 그 박스만 옛 값이다(이번에 겪은 일이다 —
    키트가 심은 DELIB_TIMEOUT_S=600 이 박스에 남는다). 설명은 값 줄에 붙이지 않는다(줄 끝 설명째 복사된다)."""
    line = next(ln for ln in EXAMPLE.splitlines() if re.match(rf"^[ \t]*#?[ \t]*{key}=", ln))
    assert line == f"# {key}={KNOBS[key][1]}", line


def test_env_sync_가_기존_박스의_env_에_주석으로_알린다(tmp_path):
    """이미 배포된 박스의 infra/.env 는 예시 파일을 다시 복사하지 않는다 — update-all 1c 의 env-sync 가 없는 키를 덧붙여 알린다.
    실제 예시 파일과 '이 변경 전' 모양의 .env 로 env-sync 를 **그대로 돌린다**. 전부 주석으로(꺼진 채) 들어가야 한다."""
    keys = [*KNOBS, "NGINX_AGENT_READ_TIMEOUT", "NGINX_MCP_READ_TIMEOUT"]
    box = tmp_path / "HWAXPortal" / "infra"
    box.mkdir(parents=True)
    (box / ".env.example").write_text(EXAMPLE, encoding="utf-8")
    old_env = "\n".join(ln for ln in EXAMPLE.splitlines() if not any(re.match(rf"^[ \t]*#?[ \t]*{k}=", ln) for k in keys)) + "\n"
    (box / ".env").write_text(old_env, encoding="utf-8")
    r = subprocess.run(["bash", str(ROOT / "infra/scripts/env-sync.sh"), str(box.parent)], capture_output=True, text=True,
                       timeout=60, env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)})
    assert r.returncode == 0, r.stdout + r.stderr
    added = (box / ".env").read_text(encoding="utf-8")[len(old_env):]
    for key in keys:
        assert re.search(rf"^# {key}=", added, re.M), f"{key} 가 기존 박스의 .env 에 알려지지 않았다\n{r.stdout}"
        assert not re.search(rf"^{key}=", added, re.M), f"{key} 가 켜진 줄로 들어갔다"
        assert key in r.stdout, "무엇이 새로 생겼는지 실행 출력에도 나온다"
    assert _declared(added).keys() == set(keys), "이 여섯 말고는 덧붙이지 않는다(구획의 설명 줄을 키로 읽지 않는다)"


def test_한도의_순서가_값을_적는_자리에_있다():
    """세 리포 세 손잡이라 한쪽만 바꾸면 순서가 뒤집힌다 — 값을 고치는 사람이 그 자리에서 읽어야 한다."""
    i = EXAMPLE.index("# AGENT_STREAM_IDLE_TIMEOUT_S=")
    near = EXAMPLE[max(0, i - 900):i]
    for want in ("NGINX_AGENT_READ_TIMEOUT", "50400", "HWAXRISK_ENGINE_READ_TIMEOUT_S", "54000", "46800"):
        assert want in EXAMPLE[max(0, i - 900):EXAMPLE.index("# NGINX_MCP_READ_TIMEOUT=")], want
    assert "<" in near, "어느 쪽이 작아야 하는지(순서)를 적는다"
