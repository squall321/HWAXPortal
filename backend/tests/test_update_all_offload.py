# update-all 3.5e — 서버 LLM 에 일 맡기기 A ~ D(토큰 절감 2판) 가운데 안 켠 것을 ○ 로, 그리고 env 킷의 주석 스위치(docs/token-saving/offload-v2.md)
"""스위치는 모두 기본 꺼짐이고 켜는 것은 사람이다 — 에이전트 서버 .env 의 DELEGATE_ENABLED · DRAFT_ENABLED · TRANSFORM_ENABLED · RESULT_ASK_ENABLED,
게이트웨이 provision.env 의 GATEWAY_RESULT_REFS. update-all 은 고쳐 쓰지 않고 안 켠 것을 ○ 로 남긴다(즉시 + 끝 요약 — 안 켠 기능도 로그에).
그 구획을 임시 박스에서 **실제로 돌린다**(실물 .env 는 읽지 않는다)."""
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
UA = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")
KIT = (ROOT / "infra/env-kits/agent-server.env").read_text(encoding="utf-8")
LEDGER_LIB = ROOT / "infra/scripts/lib/skip-ledger.sh"
NAMES = {"A": "서버 LLM 위임(A — delegate_start)", "B": "결과 손잡이 · 결과에 묻기(B — result_get · result_ask)",
         "C": "서버 긴 글 작성(C — draft_section)", "D": "서버 단순 변환(D — llm_transform)"}


def _fn(name: str) -> str:
    m = re.search(rf"(?ms)^{name}\(\) \{{[^\n]*\n.*?^\}}\n", UA)   # 첫 줄 꼬리에 주석이 붙는다
    assert m, name
    return m.group(0)


def _block() -> str:
    i = UA.index("# ── 3.5e) 서버 LLM 에 일 맡기기")
    return UA[i:UA.index("\n# ── 4) 챗 스택만", i)]


def _run(tmp_path: Path, agent: str | None, prov: str | None, *, gw: bool = True) -> tuple[str, list[str]]:
    a, g = tmp_path / "agent.env", tmp_path / "gw"
    g.mkdir(exist_ok=True)
    if agent is not None:
        a.write_text(agent, encoding="utf-8")
    if prov is not None:
        (g / "provision.env").write_text(prov, encoding="utf-8")
    led = tmp_path / "ledger"
    led.write_text("")
    script = (f"set -uo pipefail\n{_fn('_envfile_value')}. '{LEDGER_LIB}'\nHWAX_SKIP_LEDGER='{led}'\n"
              f"AGENT_ENV='{a}'\nGW_DIR='{g if gw else ''}'\n{_block()}\necho '-- 요약'\nhwax_skip_summary\n")
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout, [ln.split("\t")[0] for ln in led.read_text(encoding="utf-8").splitlines()]


def test_아무것도_안_켠_박스는_넷을_안_켠_줄로_남긴다(tmp_path):
    out, led = _run(tmp_path, "VLLM_BASE_URL=http://x/v1\n", "RAT_TOKEN=x\n")
    assert led == [NAMES[k] for k in "ABCD"], "A · B · C · D 차례로 하나씩"
    head, summary = out.split("-- 요약")
    for k in "ABCD":
        assert NAMES[k] in head and NAMES[k] in summary, "즉시 한 줄 + 끝 요약에 다시"
    assert head.count("켜려면:") == 4
    for knob in ("DELEGATE_ENABLED=1", "GATEWAY_RESULT_REFS=1", "RESULT_ASK_ENABLED=1", "DRAFT_ENABLED=1", "TRANSFORM_ENABLED=1"):
        assert knob in head, knob
    assert "docs/token-saving/offload-v2.md" in head


def test_파일이_없어도_꺼짐으로_읽는다(tmp_path):
    _, led = _run(tmp_path, None, None)
    assert led == [NAMES[k] for k in "ABCD"]


def test_다_켠_박스는_아무_말도_하지_않는다(tmp_path):
    # 켬 낱말 넷(대소문자 무시) · 줄 끝 설명 · 따옴표 · export — _envfile_value 의 읽기 규칙 그대로
    agent = ('DELEGATE_ENABLED=1   # 위임\nexport DRAFT_ENABLED="true"\nTRANSFORM_ENABLED=On\nRESULT_ASK_ENABLED=YES\n')
    out, led = _run(tmp_path, agent, "GATEWAY_RESULT_REFS='1'\n")
    assert led == [] and out.strip() == "-- 요약", out


@pytest.mark.parametrize("line", ["DELEGATE_ENABLED=0", "DELEGATE_ENABLED=", "# DELEGATE_ENABLED=1", "DELEGATE_ENABLED=2",
                                  "DELEGATE_ENABLED=1\nDELEGATE_ENABLED=0"])
def test_켬_낱말이_아니면_꺼짐이다(tmp_path, line):
    agent = f"{line}\nDRAFT_ENABLED=1\nTRANSFORM_ENABLED=1\nRESULT_ASK_ENABLED=1\n"
    _, led = _run(tmp_path, agent, "GATEWAY_RESULT_REFS=1\n")
    assert led == [NAMES["A"]], "마지막 활성 줄이 이긴다 · 주석 줄은 값이 아니다"


def test_결과_손잡이만_켜고_묻기_창구를_안_켜면_그_까닭으로_말한다(tmp_path):
    out, led = _run(tmp_path, "DELEGATE_ENABLED=1\nDRAFT_ENABLED=1\nTRANSFORM_ENABLED=1\n", "GATEWAY_RESULT_REFS=1\n")
    assert led == [NAMES["B"]]
    assert "RESULT_ASK_ENABLED=1 이 없다" in out and "result_ask" in out


def test_게이트웨이를_모르는_박스는_B_를_말하지_않는다(tmp_path):
    _, led = _run(tmp_path, "", None, gw=False)
    assert led == [NAMES[k] for k in "ACD"]


def test_고쳐_쓰지_않는다(tmp_path):
    _run(tmp_path, "DELEGATE_ENABLED=0\n", "RAT_TOKEN=x\n")
    assert (tmp_path / "agent.env").read_text(encoding="utf-8") == "DELEGATE_ENABLED=0\n"
    assert (tmp_path / "gw/provision.env").read_text(encoding="utf-8") == "RAT_TOKEN=x\n"


def test_구획은_3장5_뒤_그_갈래_밖에서_AGENT_ENV_가_있을_때만_돈다():
    """3.5 의 갈래 안(옛 심의 타임아웃 알림까지)은 다른 시험들이 떼어 가짜 함수로 돌린다 — 그 밖에 둔다."""
    blk = _block()
    i = UA.index(blk)
    end35 = UA.index('\nelse\n  hwax_skip "agent-server .env 보정"')
    assert UA.index('  AGENT_ENV="$AGENT_DIR/.env"') < end35 < i < UA.index('hr "4) update-sites'), "3.5 가 AGENT_ENV 를 정한 뒤 · §4 앞"
    assert UA.index("\nfi\n", end35) < i, "3.5 의 갈래 밖"
    assert 'if [ -n "${AGENT_ENV:-}" ]; then' in blk and blk.rstrip().endswith("fi")
    assert UA.index("_envfile_value() {") < i and UA.index('. "$SELF_REPO/infra/scripts/lib/skip-ledger.sh"') < i
    assert "_upsert_kv" not in blk and "sed -i" not in blk and ">>" not in blk, "읽기만 한다"


def test_에이전트_서버_리포가_없는_박스는_말하지_않는다(tmp_path):
    led = tmp_path / "ledger"
    led.write_text("")
    script = (f"set -uo pipefail\n{_fn('_envfile_value')}. '{LEDGER_LIB}'\nHWAX_SKIP_LEDGER='{led}'\nGW_DIR=''\n{_block()}\n")
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0 and r.stdout == "" and led.read_text() == "", r.stdout + r.stderr


# ── env 킷 — 넷은 주석(기본 꺼짐)으로만, 켜는 법과 계약 문서를 함께 ─────────────────────────────────────────────
def _kit_block() -> str:
    i = KIT.index("# --- 서버 LLM 에 일 맡기기")
    nxt = KIT.find("\n# --- ", i + 1)
    return KIT[i:] if nxt < 0 else KIT[i:nxt + 1]


def test_env_킷은_넷을_꺼진_주석으로만_적는다():
    blk = _kit_block()
    assert re.findall(r"^# ([A-Z_]+)=(\S*)$", blk, re.M) == [
        ("DELEGATE_ENABLED", "0"), ("DRAFT_ENABLED", "0"), ("TRANSFORM_ENABLED", "0"), ("RESULT_ASK_ENABLED", "0")]
    for k in ("DELEGATE_ENABLED", "DRAFT_ENABLED", "TRANSFORM_ENABLED", "RESULT_ASK_ENABLED"):
        assert not re.search(rf"^{k}=", KIT, re.M), "활성 줄로 두면 apply-envs 가 박스 .env 에 옮겨 적는다"
    assert "docs/token-saving/offload-v2.md" in blk and "GATEWAY_RESULT_REFS=1" in blk and "1 · true · yes · on" in blk
    assert "./start.sh -d" in blk, "켜는 법 — 재기동"
