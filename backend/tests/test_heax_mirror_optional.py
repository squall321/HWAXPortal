# HEAXHub pip·npm 미러가 Drive 에 없을 때 — deploy-all 이 부르면 ○ 와 3(건너뜀), 단독 실행은 ✗ 와 1(10-17 cae00 리뷰 P9)
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MIRROR = ROOT.parent / "HEAXHub" / "deploy" / "apptainer" / "mirror-from-drive.sh"
DEPLOY_ALL = (ROOT / "infra" / "scripts" / "deploy-all-from-drive.sh").read_text(encoding="utf-8")

pytestmark = pytest.mark.skipif(not MIRROR.is_file(), reason="형제 리포 HEAXHub 가 없다")


def _run(tmp_path, **env):
    shim = tmp_path / "bin"
    shim.mkdir(exist_ok=True)
    (shim / "rclone").write_text("#!/usr/bin/env bash\nexit 0\n")      # Drive 가 비었다 — lsf 가 아무것도 안 낸다
    (shim / "rclone").chmod(0o755)
    full = {"PATH": f"{shim}:/usr/bin:/bin", "HOME": str(tmp_path), "HEAX_DRIVE_REMOTE": "Fake:HEAXHub/dist", **env}
    return subprocess.run(["bash", str(MIRROR)], capture_output=True, text=True, timeout=60, env=full)


def test_deploy_all_이_부르면_미러_없음은_건너뜀이다(tmp_path):
    r = _run(tmp_path, HEAX_MIRROR_OPTIONAL="1")
    assert r.returncode == 3, (r.returncode, r.stdout, r.stderr)
    assert "○ Drive 에 pip·npm 미러가 없다" in r.stdout and "✗" not in r.stdout + r.stderr, r.stdout


def test_단독_실행은_그대로_실패다(tmp_path):
    """소스로 SIF 를 빌드하려는 박스에서는 미러가 빌드의 전제다 — 조용히 넘어가면 안 된다."""
    r = _run(tmp_path)
    assert r.returncode == 1 and "✗ Drive 에 pip·npm 미러가 하나도 없음" in r.stdout, (r.returncode, r.stdout)


def test_deploy_all_은_선택으로_부르고_3_을_장부에만_적는다():
    i = DEPLOY_ALL.index("HEAX_MIRROR_OPTIONAL=1 bash deploy/apptainer/mirror-from-drive.sh")
    block = DEPLOY_ALL[i - 400:i + 400]
    assert "|| _mrc=$?" in block and '[ "$_mrc" = 3 ] && hwax_skip_record "HEAX pip·npm 미러"' in block, block
    assert "|| true" not in DEPLOY_ALL[i:i + 120], "실패를 버리면 3 과 1 을 못 가른다"
