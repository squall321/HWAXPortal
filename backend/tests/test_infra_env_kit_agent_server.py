# 에이전트 서버 env 킷(infra/env-kits/agent-server.env)의 심의 시간 한도 — 새 박스에 무엇이 심기고, 옛 값이 남은 박스가 어떻게 드러나는지
"""왜 — 킷은 박스가 값을 베껴 가는 원본이다. 여기 적힌 `DELIB_TIMEOUT_S=600` 이 운영 박스의 .env 에 심겼고, 좌석 20석 넘는
심의는 공유 LLM 의 큐 대기가 호출 시계에 들어가 그 600초에 좌석이 빠졌다. 값을 1800 으로 올려도 두 가지가 남는다.

  1. 킷은 **없는 키만** 더한다 — 600 이 이미 박힌 박스는 그대로다. 조용하면 한도를 올린 것이 그 박스에서만 안 먹는다.
     update-all 3.5 가 그런 박스를 알린다(고쳐 쓰지는 않는다).
  2. 킷의 주석 손잡이는 줄 끝에 설명을 달고 있는데, 에이전트 서버의 start.sh 는 `=` 뒤를 통째로 값으로 읽는다 — 설명째 옮기면
     숫자로 안 읽혀 기본값으로 돈다. 새로 적는 시간 한도는 값 줄에 설명을 붙이지 않고, 옮길 때의 주의를 킷에 적는다.

apply-envs.sh 와 update-all 의 그 구획을 임시 박스에서 **실제로 돌린다**(실물 .env 는 읽지 않는다).
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
KIT = (ROOT / "infra/env-kits/agent-server.env").read_text(encoding="utf-8")
UA = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")
ENGINE = ROOT.parent / "HWAXAgentServer"


def _time_block() -> str:
    """킷의 시간 한도 구획(주석 손잡이들) — 머리 줄부터 파일 끝까지."""
    return KIT[KIT.index("# --- 시간 한도(2026-10"):]


def _knobs() -> dict[str, str]:
    """시간 한도 구획의 값 줄 `# KEY=값` → {KEY: 값}, 그리고 킷이 실제로 심는 DELIB_TIMEOUT_S."""
    out = dict(re.findall(r"^# ([A-Z][A-Z0-9_]*)=(\S+)$", _time_block(), re.M))
    out["DELIB_TIMEOUT_S"] = re.search(r"^DELIB_TIMEOUT_S=(\S+)$", KIT, re.M).group(1)
    return out


# ── 새 박스 — 킷을 적용하면 무엇이 심기나 ─────────────────────────────────────────────────
def _apply(tmp_path: Path, existing: str | None = None) -> tuple[str, str]:
    """apply-envs.sh agent-server 를 임시 박스에서 돌린다 → (대상 .env 내용, 화면 출력)."""
    portal = tmp_path / "HWAXPortal"
    (portal / "infra/env-kits").mkdir(parents=True)
    for f in ("apply-envs.sh", "agent-server.env"):
        shutil.copy(ROOT / "infra/env-kits" / f, portal / "infra/env-kits" / f)
    agent = tmp_path / "HWAXAgentServer"; agent.mkdir()
    if existing is not None:
        (agent / ".env").write_text(existing, encoding="utf-8")
    r = subprocess.run(["bash", str(portal / "infra/env-kits/apply-envs.sh"), "agent-server"], capture_output=True, text=True,
                       timeout=60, env={"PATH": os.environ["PATH"], "HOME": str(tmp_path)})
    assert r.returncode == 0, r.stdout + r.stderr
    return (agent / ".env").read_text(encoding="utf-8"), r.stdout


def test_새_박스에는_1800초가_심긴다(tmp_path):
    """**이 시험이 이 파일의 이유다** — 종전에는 600 이 심겼다."""
    env, _ = _apply(tmp_path)
    assert re.findall(r"^DELIB_TIMEOUT_S=(.*)$", env, re.M) == ["1800"]


def test_주석으로_적어_둔_손잡이는_심기지_않는다(tmp_path):
    """시간 한도 구획은 '무엇이 있는지' 를 적어 둔 것이다 — 심으면 그 박스가 그 값에 묶여, 코드 기본값을 나중에 올려도 안 먹는다
    (이번에 600 으로 겪은 일이다)."""
    env, _ = _apply(tmp_path)
    seeded = set(re.findall(r"^([A-Z][A-Z0-9_]*)=", env, re.M))
    assert not seeded & (set(_knobs()) - {"DELIB_TIMEOUT_S"}), seeded


def test_이미_박힌_값은_킷이_건드리지_않는다(tmp_path):
    """'없는 키만 추가' 계약 그대로다 — 그래서 옛 값이 남은 박스는 아래 update-all 의 알림이 유일한 신호다."""
    env, _ = _apply(tmp_path, existing="DELIB_TIMEOUT_S=600\n")
    assert re.findall(r"^DELIB_TIMEOUT_S=(.*)$", env, re.M) == ["600"]


# ── 옛 값이 남은 박스 — update-all 3.5 가 알린다 ─────────────────────────────────────────────
def _stale_notice(tmp_path: Path, agent_env: str | None) -> str:
    i = UA.index("  # 옛 킷이 심은 심의 호출 타임아웃")
    block = UA[i:UA.index('\nelse\n  hwax_skip "agent-server .env 보정"', i)]
    env_file = tmp_path / "agent.env"
    if agent_env is not None:
        env_file.write_text(agent_env, encoding="utf-8")
    script = "\n".join(["set -uo pipefail", 'bad() { echo "BAD:$*"; }', f'SELF_REPO="{ROOT}"; AGENT_ENV="{env_file}"', block, "echo end"])
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=30, env={"PATH": "/usr/bin:/bin"})
    assert r.returncode == 0 and not r.stderr and r.stdout.rstrip().endswith("end"), r.stdout + r.stderr
    return r.stdout


@pytest.mark.parametrize("line", ["DELIB_TIMEOUT_S=600", 'DELIB_TIMEOUT_S="600"', "DELIB_TIMEOUT_S=600.0", "DELIB_TIMEOUT_S=180\r",
                                  "DELIB_TIMEOUT_S=3600\nDELIB_TIMEOUT_S=600", "DELIB_TIMEOUT_S=1799"])
def test_킷_값보다_짧게_박힌_박스를_알린다(tmp_path, line):
    """**킷 값을 올려도 그 박스는 600 이다** — 무엇을 지우면 되는지와 함께 한 줄로. 서버는 같은 키가 둘이면 뒤의 것을 쓴다."""
    out = _stale_notice(tmp_path, line + "\n")
    bads = [ln for ln in out.splitlines() if ln.startswith("BAD:")]
    assert len(bads) == 1, out
    assert "DELIB_TIMEOUT_S=" in bads[0] and "1800초" in bads[0] and "지우고" in bads[0] and "재기동" in bads[0]


@pytest.mark.parametrize("env", ["DELIB_TIMEOUT_S=1800\n", "DELIB_TIMEOUT_S=3600\n", "VLLM_MODEL=x\n", "# DELIB_TIMEOUT_S=600\n",
                                 "DELIB_TIMEOUT_S=600\nDELIB_TIMEOUT_S=3600\n", "DELIB_TIMEOUT_S=\n",
                                 "DELIB_TIMEOUT_S=600   # 여유값\n", None])
def test_넉넉하거나_없거나_못_읽는_값에는_조용하다(tmp_path, env):
    """넓히면 소음이 된다. 줄 끝 설명이 붙은 값은 서버가 숫자로 못 읽어 기본값으로 돈다 — 짧게 도는 것이 아니다."""
    assert "BAD:" not in _stale_notice(tmp_path, env)


def test_알림은_고쳐_쓰지_않는다(tmp_path):
    """박스가 일부러 정한 값일 수 있다 — update-all 이 .env 를 고치면 적은 값과 도는 값이 갈린다."""
    f = tmp_path / "agent.env"
    _stale_notice(tmp_path, "DELIB_TIMEOUT_S=600\n")
    assert f.read_text(encoding="utf-8") == "DELIB_TIMEOUT_S=600\n"


# ── 옮겨 적는 사람을 위한 모양 — 값 줄에 설명을 붙이지 않는다 ────────────────────────────────────
def test_시간_한도의_값_줄은_그대로_옮겨도_숫자다():
    """에이전트 서버의 start.sh 는 `=` 뒤를 통째로 값으로 읽는다(줄 끝 설명을 떼지 않는다). 구획 안에서 `# KEY=` 로 시작하는 줄은
    전부 `# KEY=숫자` 로 끝나야 한다 — 설명이 붙은 줄을 주석만 풀어 옮기면 그 손잡이가 기본값으로 돈다."""
    lines = [ln for ln in _time_block().splitlines() if re.match(r"^# [A-Z][A-Z0-9_]*=", ln)]
    assert len(lines) >= 12, lines
    for ln in lines:
        assert re.fullmatch(r"# [A-Z][A-Z0-9_]*=[0-9]+", ln), f"값 줄에 설명이 붙었다: {ln}"
    assert "# DELIB_SER_CLIP=700" in lines


def test_줄_끝_설명을_옮기지_말라는_말이_주석_손잡이_머리에_있다():
    """앞 구획의 주석 손잡이들은 줄 끝에 설명을 달고 있다(`# DELIB_JOB_MAX_RUNNING=2   # …`) — 그 줄을 옮기는 사람이 읽는 자리다."""
    i = KIT.index("# DELIB_JOB_MAX_RUNNING=")
    head = KIT[KIT.index("# --- 심의 잡·근거·좌석 상한"):i]
    assert "줄 끝의 설명" in head and "start.sh" in head and "기본값으로 돈다" in head


def test_옛_값이_남는다는_말이_값을_적는_자리에_있다():
    i = KIT.index("\nDELIB_TIMEOUT_S=")
    near = KIT[max(0, i - 900):i]
    assert "없는 키만" in near and "600" in near and "update-all" in near


# ── 엔진과의 계약 — 킷에 적은 이름·기본값이 엔진의 것과 같다 ──────────────────────────────────────
def _engine_default(knob: str) -> str | None:
    """엔진 소스가 그 손잡이에 주는 기본값(문자열). 손잡이를 모르면 None."""
    pats = (rf'_env_(?:int|float)\(\s*"{knob}"\s*,\s*([0-9.]+)\s*\)', rf'environ\.get\(\s*"{knob}"\s*,\s*"([0-9.]+)"\s*\)',
            rf'\$\{{{knob}:-([0-9.]+)\}}')
    for name in ("app.py", "deliberation.py", "thinking.py", "delib_jobs.py", "mcp_server.py", "start.sh"):
        f = ENGINE / name
        if not f.exists():
            continue
        src = f.read_text(encoding="utf-8")
        for pat in pats:
            m = re.search(pat, src)
            if m:
                return m.group(1)
    return None


@pytest.mark.parametrize("knob", sorted(_knobs()))
def test_킷의_값이_엔진_기본값과_같다(knob):
    """킷은 '아래 값이 코드 기본값이다' 라고 말한다. 엔진이 기본값을 바꾸면 킷을 보고 적은 박스만 옛 값으로 돈다 —
    형제 리포의 소스에서 읽어 맞댄다(그 리포의 의존성을 끌어오지 않게 import 하지 않는다)."""
    if not ENGINE.exists():
        pytest.skip(f"형제 리포 없음: {ENGINE}")
    got = _engine_default(knob)
    if got is None:
        pytest.skip(f"옆의 에이전트 서버가 아직 {knob} 를 모르는 판이다")
    assert float(got) == float(_knobs()[knob]), f"{knob}: 엔진 {got} · 킷 {_knobs()[knob]}"


def test_엔진이_시간_한도로_적은_손잡이가_킷에_빠짐없이_있다():
    """엔진 README 의 'Time limits' 표가 그 서버의 시간 한도 손잡이 목록이다. 엔진에 손잡이가 생겼는데 킷에 없으면, 킷을 보고 박스를
    맞추는 사람은 그 손잡이가 있는 줄 모른다 — 재기동 전에 심의 수를 묻는 한도(AGENT_HEALTH_PROBE_S)가 그렇게 빠져 있었다
    (킷을 적은 뒤에 엔진에 생겼다)."""
    readme = ENGINE / "README.md"
    if not readme.exists():
        pytest.skip(f"형제 리포 없음: {ENGINE}")
    text = readme.read_text(encoding="utf-8")
    assert "\n### Time limits\n" in text, "엔진 README 의 시간 한도 표를 못 찾았다 — 제목이 바뀌었으면 이 시험도 고쳐라"
    table = text[text.index("\n### Time limits\n"):]
    names = re.findall(r"^\| `([A-Z][A-Z0-9_]*)` \|", table[:table.index("\n## ")], re.M)
    assert len(names) >= 15, names
    kit = _knobs()
    for name in names:
        if name == "AGENT_RESTART_FORCE":
            # 박스의 .env 에 적는 값이 아니다(적으면 보호가 늘 꺼진다) — 이름과 그 말이 구획에 있으면 된다
            assert name in _time_block() and "이 파일에 적는 값이 아니다" in _time_block()
            continue
        assert name in kit, f"엔진의 시간 한도 손잡이 {name} 가 킷(infra/env-kits/agent-server.env)에 없다 — 기본값과 함께 적는다"


# ── 층 — 킷의 수치로 안쪽 < 바깥이 성립한다 ───────────────────────────────────────────────────
def test_킷의_수치로_안쪽_한도가_바깥보다_작다():
    """한 값만 고치면 순서가 뒤집힌다. 포털 릴레이의 침묵 한도는 heartbeat 가 꺼진(또는 없는 옛) 엔진에서도 LLM 논리 호출 1회의
    최악보다 커야 한다 — 요청 상한(DELIB_TIMEOUT_MAX_S)까지 청한 호출이어도."""
    from app.config import Settings

    k = {name: float(v) for name, v in _knobs().items()}
    assert k["LLM_CONNECT_TIMEOUT_S"] < k["DELIB_TIMEOUT_S"] <= k["DELIB_TIMEOUT_MAX_S"]
    attempts = k["DELIB_LLM_MAX_RETRIES"] + 1
    relay_idle = Settings.model_fields["agent_stream_idle_timeout_s"].default
    assert attempts * k["DELIB_TIMEOUT_S"] + 8 < relay_idle, "기본 한도의 논리 호출 1회가 릴레이 침묵 한도 안에 든다"
    assert attempts * k["DELIB_TIMEOUT_MAX_S"] + 8 < relay_idle, "요청 상한까지 청한 호출 1회도 그 안에 든다"
    assert k["DELIB_HEARTBEAT_S"] < k["DELIB_TIMEOUT_S"]
    assert k["KNOWLEDGE_TIMEOUT_S"] < k["MCP_CALL_TIMEOUT_S"], "지식카드 한도는 도구 호출 기한 안에서 먼저 걸려 폴백으로 넘어간다"
