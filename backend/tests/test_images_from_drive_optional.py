# images-from-drive — 꺼진 선택 서비스(상시 상태판 · 호출 추적)의 이미지는 받지 않는다(10-17 cae00 리뷰 P8)
#
# 원문 스크립트를 임시 포털 리포에 복사해 돌린다. rclone · services.py · bootstrap-rclone 만 대역이다(Drive 와 실 박스는 건드리지 않는다).
import hashlib
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "infra" / "scripts"

FAKE_RCLONE = r'''#!/usr/bin/env bash
# 대역 rclone — version · lsf · sync 만. sync 는 원격 대역 디렉터리에서 --exclude 를 빼고 복사하고 받은 인자를 적는다.
case "$1" in
  version) exit 0 ;;
  lsf) ls -1 "$FAKE_REMOTE" ; exit 0 ;;
  sync)
    shift; excl=()
    while [ $# -gt 2 ]; do case "$1" in --exclude) excl+=("$2"); shift 2 ;; *) shift ;; esac; done
    echo "sync excl=${excl[*]:-}" >> "$RCLONE_LOG"
    dst="$2"; mkdir -p "$dst"
    for f in "$FAKE_REMOTE"/*; do
      b="$(basename "$f")"; skip=0; for e in "${excl[@]:-}"; do [ "$b" = "$e" ] && skip=1; done
      [ "$skip" = 1 ] || cp -p "$f" "$dst/$b"
    done ;;
  *) echo "unexpected rclone $*" >&2; exit 9 ;;
esac
'''

FAKE_SERVICES = '''import os, sys
# 대역 services.py — enabled <이름> 만. FAKE_ENABLED(쉼표)에 있으면 0, FAKE_ERR 이면 2, 아니면 1
if sys.argv[1:2] != ["enabled"]:
    sys.exit(9)
if os.environ.get("FAKE_ERR"):
    sys.exit(2)
sys.exit(0 if sys.argv[2] in os.environ.get("FAKE_ENABLED", "").split(",") else 1)
'''


@pytest.fixture()
def box(tmp_path):
    repo = tmp_path / "portal"
    (repo / "infra/scripts/lib").mkdir(parents=True)
    (repo / "infra/bin").mkdir()
    (repo / "infra/apptainer").mkdir()
    (repo / "frontend").mkdir()
    for rel in ("images-from-drive.sh", "_common.sh", "lib/change-detect.sh"):
        shutil.copy2(SCRIPTS / rel, repo / "infra/scripts" / rel)
    (repo / "infra/scripts/bootstrap-rclone.sh").write_text("#!/usr/bin/env bash\nexit 0\n")
    (repo / "infra/scripts/services.py").write_text(FAKE_SERVICES)
    for name in ("bootstrap-rclone.sh", "images-from-drive.sh"):
        (repo / "infra/scripts" / name).chmod(0o755)
    (repo / "infra/bin/rclone").write_text(FAKE_RCLONE)
    (repo / "infra/bin/rclone").chmod(0o755)
    (repo / "infra/.env").write_text("HWAX_DRIVE_REMOTE=Fake:HWAXPortal/images\n")
    remote = tmp_path / "remote"
    remote.mkdir()
    sums = []
    for name in ("portal.sif", "nginx.sif", "gatus.sif", "phoenix.sif"):
        body = f"{name}-v2".encode()
        (remote / name).write_bytes(body)
        sums.append(f"{hashlib.sha256(body).hexdigest()}  {name}")
    (remote / "SHA256SUMS").write_text("\n".join(sums) + "\n")
    log = tmp_path / "rclone.log"

    def run(**env):
        full = {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "FAKE_REMOTE": str(remote), "RCLONE_LOG": str(log), **env}
        r = subprocess.run(["bash", str(repo / "infra/scripts/images-from-drive.sh")], capture_output=True, text=True,
                           timeout=120, env=full, cwd=tmp_path)
        return r, (log.read_text() if log.exists() else "")
    return repo, run


def test_꺼진_상태판_호출추적_이미지는_받지_않는다(box):
    repo, run = box
    r, log = run()
    assert r.returncode == 0, r.stdout + r.stderr
    assert "sync excl=gatus.sif phoenix.sif" in log, log
    stage = repo / "infra/apptainer/.drive-cache"
    assert not (stage / "gatus.sif").exists() and not (stage / "phoenix.sif").exists()
    assert (repo / "infra/apptainer/portal.sif").exists(), "필수 이미지는 그대로 받는다"
    assert "gatus.sif 받지 않음 — status-board 꺼짐" in r.stdout and "phoenix.sif 받지 않음 — call-trace 꺼짐" in r.stdout


def test_켠_서비스의_이미지는_받는다(box):
    repo, run = box
    r, log = run(FAKE_ENABLED="status-board")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "sync excl=phoenix.sif" in log, log
    assert (repo / "infra/apptainer/gatus.sif").exists()


def test_켜짐_판정이_실패하면_예전처럼_받는다(box):
    repo, run = box
    r, log = run(FAKE_ERR="1")
    assert r.returncode == 0 and "sync excl=\n" in log, log
    assert (repo / "infra/apptainer/phoenix.sif").exists()


def test_캐시의_옛_사본은_치워_검증이_업데이트를_끊지_않는다(box):
    """제외한 이미지의 옛 사본이 캐시에 남으면 Drive 의 새 SHA256SUMS 와 어긋나 검증이 업데이트 전체를 끊는다."""
    repo, run = box
    stage = repo / "infra/apptainer/.drive-cache"
    stage.mkdir(parents=True)
    (stage / "phoenix.sif").write_bytes(b"phoenix.sif-v1")       # 예전에 받아 둔 옛 판
    r, _ = run()
    assert r.returncode == 0, r.stdout + r.stderr
    assert not (stage / "phoenix.sif").exists() and "checksum verification failed" not in r.stdout
