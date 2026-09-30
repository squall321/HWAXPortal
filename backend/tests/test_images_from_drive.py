# images-from-drive.sh 를 끝까지 태운다 — Drive 의 SIF 가 안 바뀐 날 set -e 로 조용히 끝나 portal 이 'failed' 였던 사고(2026-09-30)
#
# 진짜 스크립트를 임시 사본에서 돌린다. Drive 는 가짜 rclone(PATH 맨 앞 셈)이 로컬 폴더로 흉내 낸다 — 실제 전송·실제
# infra/apptainer 는 건드리지 않는다. 셈이 정말 쓰이는지 `command -v` 로 먼저 단언한다(상대경로 하네스가 실도구를 부른 사고 이후).
import gzip
import hashlib
import io
import os
import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

_FAKE_RCLONE = r'''#!/usr/bin/env bash
# 가짜 rclone — fake:images/<x> 를 $FAKE_REMOTE/<x> 로 바꿔 로컬 파일로 흉내 낸다(version·lsf·sync 만)
map() { local p="${1#fake:images}"; printf '%s%s' "$FAKE_REMOTE" "${p%/}"; }
case "$1" in
  version) echo "rclone v0-fake" ;;
  lsf) if [ "$2" = "--dirs-only" ]; then ls -1p "$(map "$3")" | grep '/$' || true; else ls -1 "$(map "$2")"; fi ;;
  sync) shift; [ "$1" = "--progress" ] && shift; src="$(map "$1")"; dst="${2%/}"; mkdir -p "$dst"
        find "$dst" -mindepth 1 -maxdepth 1 -exec rm -rf {} +; cp -p "$src"/* "$dst"/ ;;
  *) echo "fake rclone: 모르는 명령 $*" >&2; exit 9 ;;
esac
'''


def _dist_tar(marker: str) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        data = f"<html>{marker}</html>".encode()
        ti = tarfile.TarInfo("dist/index.html"); ti.size = len(data)
        t.addfile(ti, io.BytesIO(data))
    return buf.getvalue()


def _publish(remote: Path, *, sif: str, dist: str) -> None:
    latest = remote / "latest"
    latest.mkdir(parents=True, exist_ok=True)
    (latest / "portal.sif").write_text(f"portal-{sif}")
    (latest / "nginx.sif").write_text(f"nginx-{sif}")
    (latest / "frontend-dist.tar.gz").write_bytes(_dist_tar(dist))
    sums = "".join(f"{hashlib.sha256((latest / n).read_bytes()).hexdigest()}  {n}\n"
                   for n in ("portal.sif", "nginx.sif", "frontend-dist.tar.gz"))
    (latest / "SHA256SUMS").write_text(sums)


@pytest.fixture()
def box(tmp_path):
    repo = tmp_path / "repo"
    shutil.copytree(ROOT / "infra/scripts", repo / "infra/scripts")
    (repo / "infra/apptainer").mkdir(parents=True)
    (repo / "frontend").mkdir()
    (repo / "infra/.env").write_text("HWAX_DRIVE_REMOTE=fake:images\n")
    shim = tmp_path / "bin"; shim.mkdir()
    (shim / "rclone").write_text(_FAKE_RCLONE); (shim / "rclone").chmod(0o755)
    remote = tmp_path / "remote"
    env = {"PATH": f"{shim}:/usr/bin:/bin", "HOME": str(tmp_path), "FAKE_REMOTE": str(remote)}
    who = subprocess.run(["bash", "-c", "command -v rclone"], env=env, capture_output=True, text=True).stdout.strip()
    assert who == str(shim / "rclone"), f"가짜 rclone 이 아니라 {who} 가 불린다 — 실제 Drive 로 나간다"

    def run():
        return subprocess.run([str(repo / "infra/scripts/images-from-drive.sh")], cwd=repo, env=env,
                              capture_output=True, text=True, timeout=120)
    return repo, remote, run


def test_SIF_가_안_바뀐_날에도_끝까지_가고_dist_를_푼다(box):
    """실사고: 두 번째 실행부터 'checksums OK' 뒤에 아무 말 없이 rc 1 — portal 단계가 사유 없는 'portal failed' 였고
    frontend/dist 도 풀리지 않아 화면이 옛 판으로 남았다(set -e 아래에서 '같음'(1)을 맨 문장으로 받았다)."""
    repo, remote, run = box
    _publish(remote, sif="v1", dist="first")
    r1 = run()
    assert r1.returncode == 0, r1.stdout + r1.stderr
    assert "✓ staged portal.sif" in r1.stdout and "✓ extracted frontend/dist" in r1.stdout

    _publish(remote, sif="v1", dist="second")            # SIF 는 그대로, 화면만 새 판
    r2 = run()
    assert r2.returncode == 0, r2.stdout + r2.stderr
    assert "· portal.sif 같음" in r2.stdout and "· nginx.sif 같음" in r2.stdout
    assert "✓ extracted frontend/dist" in r2.stdout and "✓ images ready" in r2.stdout
    assert "second" in (repo / "frontend/dist/index.html").read_text(), "SIF 가 같아도 새 화면은 풀려야 한다"

    r3 = run()                                            # 전부 같을 때
    assert r3.returncode == 0 and "· frontend/dist 같음" in r3.stdout, r3.stdout + r3.stderr


def test_설치에_실패하면_사유를_찍고_멈춘다(box):
    """'같음' 을 통과시키면서 진짜 실패(쓰기 불가)는 여전히 멈춰야 한다."""
    repo, remote, run = box
    _publish(remote, sif="v1", dist="first")
    assert run().returncode == 0
    _publish(remote, sif="v2", dist="first")
    (repo / "infra/apptainer/portal.sif").chmod(0o444)
    (repo / "infra/apptainer").chmod(0o555)
    try:
        r = run()
    finally:
        (repo / "infra/apptainer").chmod(0o755)
    if os.geteuid() == 0:
        pytest.skip("root 는 권한 없이도 쓴다")
    assert r.returncode != 0 and "설치 실패" in (r.stdout + r.stderr)
