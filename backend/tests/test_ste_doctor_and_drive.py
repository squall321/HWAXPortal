# ste 진단 한 화면(ste-doctor)과 dev→Drive 스테이징 채널 — S2 의 마지막 두 조각을 못박는다
"""왜 — (1) cae00 에서 ste 가 죽어 있어도 초록으로 가려지던 자리가 넷이었고, §6 이 빨강을 내더라도 사람이
"지금 무엇이 문제인가" 를 한 번에 봐야 한다. (2) ste 스테이징은 dev 가 pack+push 를 **기억해야** Drive 에
갔고, 잊으면 cae00 은 낡은 코드를 배포하고도 초록이었다 — 실제로 2026-09-25 에 Drive 가 하루 전 판
(시크릿을 argv 로 넘기는 §8)이었다. build-all-to-drive 에 넣고 drive-drift 가 대조한다.
"""
import json
import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BUILD = (ROOT / "infra/scripts/build-all-to-drive.sh").read_text(encoding="utf-8")
DRIFT = (ROOT / "infra/scripts/drive-drift.sh").read_text(encoding="utf-8")
UA = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")
DOCTOR = ROOT / "infra/scripts/ste-doctor.sh"


def test_build_all_ships_ste_staging_by_default():
    assert re.search(r'WANT="\$\{\*:-[^"]*\bste\b', BUILD), "기본 대상에 ste 가 있어야 사람이 기억하지 않는다"
    assert "pack-staging.sh" in BUILD and "push-to-drive.sh --path SmartTwinExplorer/staging" in BUILD
    assert 'find_repo "${STE_DIR:-}" SmartTwinExplorer' in BUILD


def test_drive_drift_compares_the_staging_commit():
    assert re.search(r'WANT="\$\{\*:-[^"]*\bste\b', DRIFT)
    assert "SmartTwinExplorer/staging/ste-code.commit" in DRIFT
    assert "DRIFT=1" in DRIFT.split("if want ste; then", 1)[1].split("\nfi\n", 1)[0], "다르면 드리프트로 세야 한다"
    assert "build-all-to-drive.sh ste" in DRIFT                              # 올리는 명령을 안내


def test_update_all_points_at_the_doctor_when_ste_fails():
    assert "ste-doctor.sh" in UA


def test_doctor_report_is_machine_readable_on_this_box():
    """실물에 대고 --report 를 돌린다. 게이트웨이가 없으면 건너뛴다(시험이 박스 상태를 만들지 않는다)."""
    if subprocess.run(["curl", "-s", "-m", "3", "http://127.0.0.1:9110/health"], capture_output=True).returncode != 0:
        pytest.skip("게이트웨이 없음")
    p = subprocess.run(["bash", str(DOCTOR), "--report"], capture_output=True, text=True, timeout=90,
                       env={"PATH": os.environ["PATH"], "HOME": os.environ["HOME"]})
    if p.returncode == 2:
        pytest.skip("이 박스는 ste 를 안 쓴다")
    d = json.loads(p.stdout.strip().splitlines()[-1])
    assert isinstance(d["ok"], bool) and set(d["items"]) >= {"route", "web", "mcp", "sso-secret", "gateway-ste", "policy"}
    for k, v in d["items"].items():
        assert v["state"] in ("ok", "warn", "fail") and v["detail"], k        # 항목마다 어떻게 쟀는지 적는다
    assert (p.returncode == 0) == d["ok"]                                       # 종료코드와 JSON 이 같은 말을 한다


def test_doctor_is_read_only():
    src = DOCTOR.read_text(encoding="utf-8")
    body = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))
    body = re.sub(r"sudo -n journalctl ", "", body)     # 헤드 journal 읽기 — 읽기 전용이라 허용(mcp 가 죽은 이유를 보여 주는 자리)
    for forbidden in ("systemctl --user restart", "systemctl --user start", "rsync ", "sudo ", " > /opt", "sed -i"):
        assert forbidden not in body, f"진단 스크립트가 무엇을 바꾼다: {forbidden}"


def _doctor_tunnel_block() -> str:
    src = (ROOT / "infra/scripts/ste-doctor.sh").read_text(encoding="utf-8")
    i = src.index('  _tu="$HOME/.config/systemd/user/ste-tunnel.service"')
    return src[i:src.index("  # Teleport 세션", i)]


def test_doctor_judges_the_tunnel_unit_by_its_forwards_not_by_file_presence(tmp_path):
    """cae00 실측(2026-09-27): 헤드의 MCP 는 살아 15812 를 듣는데 cae00 의 15812 는 000 — 유닛 파일이 있다고 '리포 유닛' 으로 초록이었다.
    옛 손 유닛은 15810 만 연다. -L 목록으로 가른다."""
    unit = tmp_path / ".config/systemd/user/ste-tunnel.service"; unit.parent.mkdir(parents=True)
    stubs = 'ok() { echo "OK:$1 $2"; }; bad() { echo "BAD:$1 $2"; }; warn() { echo "WARN:$1 $2"; }; systemctl() { echo active; }; ss() { :; }; journalctl() { :; }\n'
    def run(unit_text, m):
        unit.write_text(unit_text)
        r = subprocess.run(["bash", "-c", f'HOME="{tmp_path}"; m="{m}"\n{stubs}{_doctor_tunnel_block()}'], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        return r.stdout
    old_hand = "ExecStart=/usr/bin/ssh -N -L 127.0.0.1:15810:127.0.0.1:15810 user@head\n"
    out = run(old_hand, "000")
    assert "BAD:tunnel-unit" in out and "15812 포워딩이 없다" in out and "install-ste-tunnel.sh" in out, out
    # 5차 이후: 개수가 아니라 **포트마다 누가 듣는지**를 보인다 — 개수만으로는 '유닛이 안 연다' 와 '헤드가 거부한다' 를 못 가른다.
    assert ":15810 리스너 없음" in out and ":15812 리스너 없음" in out, ("죽었으면 포트마다 리스너를 보인다", out)
    assert "유닛 MainPID" in out, "유닛이 active 인데 남이 포트를 쥔 상태를 가르려면 MainPID 가 필요하다"
    both = "ExecStart=/usr/bin/ssh -N -L 127.0.0.1:15810:127.0.0.1:15810 -L 127.0.0.1:15812:127.0.0.1:15812 user@head\n"
    out = run(both, "406")
    assert "OK:tunnel-unit" in out and "둘 다 있음" in out and "리스너 없음" not in out and "유닛 MainPID" not in out, out


def test_tunnel_installer_check_reads_the_unit_forwards_and_deploy_ste_waits_for_the_restarted_backend():
    inst = (ROOT / "infra/scripts/install-ste-tunnel.sh").read_text(encoding="utf-8")
    assert "grep -q -- '-L 127.0.0.1:15812:' \"$UNIT\"" in inst and "덮어쓰고 재기동" in inst
    dep = (ROOT / "infra/scripts/deploy-ste.sh").read_text(encoding="utf-8")
    assert "for _try in 1 2 3 4 5 6 7 8; do" in dep and "smart-twin-explorer' && break" in dep, "§8 재기동 직후의 502 를 실패로 읽지 않는다"

