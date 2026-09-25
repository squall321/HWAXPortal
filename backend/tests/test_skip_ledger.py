# "있는데 안 켠 기능" 장부 — 옵션·설정이 없어 건너뛴 단계가 조용히 지나가지 않고 요약에 전부 나오는지
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "infra/scripts/lib/skip-ledger.sh"
GATE = ROOT / "infra/scripts/lib/deploy-gate.sh"
UPDATE_ALL = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")
DEPLOY_STE = (ROOT / "infra/scripts/deploy-ste.sh").read_text(encoding="utf-8")
ENV_SYNC = (ROOT / "infra/scripts/env-sync.sh").read_text(encoding="utf-8")


def _bash(script: str, ledger: Path) -> str:
    env = {**os.environ, "HWAX_SKIP_LEDGER": str(ledger)}
    env.pop("HWAX_WITH", None); env.pop("STE_DEPLOY", None); env.pop("UPDATE_ALL_INTERACTIVE", None)
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL)
    return r.stdout + r.stderr


def test_ledger_prints_now_and_again_in_summary(tmp_path):
    ledger = tmp_path / "ledger"
    out = _bash(f'. "{LIB}"; hwax_skip ste "라우트 미설정" "routes.local.env 에 ste="; '
                f'hwax_skip "설정 TLS_CA_PATH" "값이 사람 몫" ".env 에서 정한다"; echo ---; hwax_skip_summary', ledger)
    assert out.count("켜려면: routes.local.env 에 ste=") == 2, "즉시 한 줄 + 요약에 다시"
    assert "있는데 안 켠 기능 1개 · 값 미정 설정 1개" in out and "실패가 아니다" in out
    assert out.index("---") < out.index("있는데 안 켠 기능")
    assert "값 미정 설정(주석으로만 들어감" in out and "TLS_CA_PATH" in out.split("값 미정 설정(")[1]


def test_summary_collapses_config_keys_and_dedupes(tmp_path):
    """실측: env-sync 가 넘긴 키 28개가 풀려 나와 기능 항목이 묻혔다. 키 이름만 한 줄, 중복 제거."""
    ledger = tmp_path / "ledger"
    lines = ["설정 A\t값 미정\t.env", "설정 B\t값 미정\t.env", "설정 A\t값 미정\t.env",
             "ste\t라우트 미설정\tste=", "ste\t라우트 미설정\tste="]
    ledger.write_text("\n".join(lines) + "\n")
    out = _bash(f'. "{LIB}"; hwax_skip_summary', ledger)
    assert "있는데 안 켠 기능 1개 · 값 미정 설정 2개" in out
    assert out.count("· ste — 라우트 미설정") == 1 and "A, B" in out


def test_summary_is_silent_when_nothing_was_skipped(tmp_path):
    out = _bash(f'. "{LIB}"; hwax_skip_summary; echo END', tmp_path / "ledger")
    assert out.strip() == "END"


def test_gate_records_option_and_precondition_skips_but_not_up_to_date(tmp_path):
    ledger = tmp_path / "ledger"
    # ① routine(터미널 아님·--with 없음) → 장부에 '--with-ste' 가 적힌다
    _bash(f'. "{GATE}"; hwax_gate ste --fresh "exit 0" --precond "true"; true', ledger)
    text = ledger.read_text(encoding="utf-8")
    assert "ste\t" in text and "--with-ste" in text and "STE_DEPLOY=1" in text
    # ② 사람이 불렀는데 전제조건 실패 → 전제를 세우라고 적힌다
    ledger.write_text("")
    _bash(f'. "{GATE}"; HWAX_WITH=ste hwax_gate ste --fresh "exit 0" --precond "false"; true', ledger)
    text = ledger.read_text(encoding="utf-8")
    assert "전제조건" in text and "--with-ste" in text
    # ③ 이미 최신(같음)은 '안 켠 것' 이 아니다 — 적지 않는다
    ledger.write_text("")
    _bash(f'. "{GATE}"; UPDATE_ALL_INTERACTIVE=1 hwax_gate ste --fresh "exit 1" --precond "true"; true', ledger)
    assert ledger.read_text(encoding="utf-8") == ""


def test_no_ledger_env_means_no_side_effect(tmp_path):
    r = subprocess.run(["bash", "-c", f'unset HWAX_SKIP_LEDGER; . "{LIB}"; hwax_skip_record a b c; hwax_skip a b c; hwax_skip_summary; echo rc=$?'],
                       capture_output=True, text=True, stdin=subprocess.DEVNULL)
    assert "rc=0" in r.stdout and "a — b" in r.stdout


def test_update_all_keeps_one_ledger_and_summarises_before_the_verdict():
    assert 'lib/skip-ledger.sh' in UPDATE_ALL and 'HWAX_SKIP_LEDGER="$(mktemp)"; export HWAX_SKIP_LEDGER' in UPDATE_ALL
    i_sum, i_fail = UPDATE_ALL.index("hwax_skip_summary"), UPDATE_ALL.index('if [ "$FAIL" = 1 ]; then')
    assert i_sum < i_fail, "요약은 성공·실패 어느 쪽 끝에서도 나와야 한다 — 판정 분기보다 앞"
    # 옵션·설정으로 건너뛰는 자리들이 ok/echo 가 아니라 장부를 쓴다
    for needle in ('hwax_skip "ste(SmartTwinExplorer)" "라우트 미설정',
                   'hwax_skip "ste 라우트 자동 기록" "HWAX_STE_AUTOROUTE=0',
                   'hwax_skip "agent-server .env 보정"', 'hwax_skip "AIDataHub 동기화"',
                   'hwax_skip ".env 옵션 동기화"', 'hwax_skip "ste 코드 최신화"'):
        assert needle in UPDATE_ALL, needle
    assert 'ok "ste 라우트 미설정 — 건너뜀"' not in UPDATE_ALL, "초록으로 지나가면 그 기능이 있는 줄도 모른다"


def test_deploy_ste_gate_block_exits_3_and_update_all_reads_it_as_skipped():
    assert "exit 3   # 게이트가 막았다" in DEPLOY_STE
    assert "3)   : ;;" in UPDATE_ALL and "124) bad" in UPDATE_ALL


def test_env_sync_records_keys_left_for_a_human():
    assert "lib/skip-ledger.sh" in ENV_SYNC
    assert ENV_SYNC.count('hwax_skip_record "설정 ${kv%%=*}"') == 2, "상한 초과 보고와 일반 보고 둘 다"
