# repo-bundle-to-drive.sh — 원격 없는 지식 리포를 git 묶음 + 커밋 안 된 변경 사본으로 올리고, 안 바뀌면 건너뛰며, 최근 N벌만 남기는지(10-17 결정 3)
"""왜 작업 사본까지 — git 묶음은 커밋만 담는다. ExpertGrounding 은 커밋이 8월의 1개뿐이고 뒤 작업이 전부 작업 트리에 있었다.

원문 스크립트를 임시 포털에 복사해 돌린다. 형제 리포는 임시 git 이고, Drive 는 가짜 rclone(로컬 폴더)이다.
"""
import os
import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

_FAKE_RCLONE = r'''#!/usr/bin/env bash
echo "$*" >> "$RCLONE_LOG"
p() { printf '%s/%s' "$FAKE_DRIVE" "${1#*:}"; }
case "$1" in
  copy) mkdir -p "$(p "$3")"; cp "$2" "$(p "$3")/" ;;
  lsf) d="$(p "${@: -1}")"; [ -d "$d" ] && ls -1 "$d" ;;
  deletefile) rm -f "$(p "$2")" ;;
  *) echo "fake rclone: 모르는 명령 $*" >&2; exit 9 ;;
esac
'''

_GIT = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True,
                          env={**os.environ, **_GIT}).stdout.strip()


@pytest.fixture()
def box(tmp_path):
    portal = tmp_path / "HWAXPortal"
    (portal / "infra/scripts").mkdir(parents=True)
    shutil.copy(ROOT / "infra/scripts/repo-bundle-to-drive.sh", portal / "infra/scripts/")
    (portal / "infra/.env").write_text("HWAX_DRIVE_REMOTE=Fake:HWAXPortal/images\n", encoding="utf-8")
    repo = tmp_path / "ExpertAgents"
    (repo / "knowledge").mkdir(parents=True)
    _git(repo, "init", "-q")
    (repo / "knowledge/a.md").write_text("v1\n")
    (repo / ".gitignore").write_text("cache/\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "first")
    (repo / "knowledge/a.md").write_text("v2 — 아직 커밋 안 함\n")      # 커밋 안 된 수정
    (repo / "knowledge/new.md").write_text("새 카드\n")                 # 추적 안 된 파일
    (repo / ".env.local").write_text("TOKEN=x\n")
    (repo / "secret.key").write_text("k\n")
    (repo / "qdrant.sif").write_bytes(b"\0" * 64)
    (repo / "cache").mkdir()
    (repo / "cache/tmp.bin").write_bytes(b"ignored")
    shim = tmp_path / "bin"
    shim.mkdir()
    (shim / "rclone").write_text(_FAKE_RCLONE)
    (shim / "rclone").chmod(0o755)
    drive, log = tmp_path / "drive", tmp_path / "rclone.log"

    def run(*args, **env):
        full = {"PATH": f"{shim}:/usr/bin:/bin", "HOME": str(tmp_path), "FAKE_DRIVE": str(drive), "RCLONE_LOG": str(log),
                "HWAX_BOX": "devbox", "HWAX_BUNDLE_STATE": str(tmp_path / "state"), **env}
        return subprocess.run(["bash", str(portal / "infra/scripts/repo-bundle-to-drive.sh"), *args], capture_output=True,
                              text=True, timeout=120, env=full)
    return run, repo, drive / "HWAXPortal/repo-bundles/ExpertAgents"


def test_묶음과_커밋_안_된_변경을_올리고_비밀_꼴과_이미지는_뺀다(box, tmp_path):
    run, repo, dest = box
    r = run()
    assert r.returncode == 0, r.stdout + r.stderr
    assert "○ ExpertGrounding: 리포 없음" in r.stdout
    tars = sorted(dest.glob("ExpertAgents-devbox-*.tar"))
    assert len(tars) == 1, r.stdout
    out = tmp_path / "x"
    with tarfile.open(tars[0]) as t:
        t.extractall(out, filter="data")
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", "-q", str(out / "ExpertAgents.bundle"), str(clone)], check=True)
    assert _git(clone, "rev-parse", "HEAD") == _git(repo, "rev-parse", "HEAD"), "묶음이 이력을 담지 않았다"
    with tarfile.open(out / "worktree-changes.tar.gz") as t:
        names = set(t.getnames())
    assert {"knowledge/a.md", "knowledge/new.md"} <= names, names
    assert not names & {".env.local", "secret.key", "qdrant.sif", "cache/tmp.bin"}, names
    assert "changes=2" in (out / "MANIFEST.txt").read_text()


def test_안_바뀌면_올리지_않고_바뀌면_다시_올린다(box):
    run, repo, dest = box
    run()
    r = run()
    assert r.returncode == 0 and "○ ExpertAgents: 바뀐 것 없음" in r.stdout, r.stdout + r.stderr
    assert len(list(dest.glob("*.tar"))) == 1
    (repo / "knowledge/new.md").write_text("새 카드 — 고쳤다\n")
    os.utime(repo / "knowledge/new.md", (2_000_000_000, 2_000_000_000))
    r = run()
    assert r.returncode == 0 and "✓ ExpertAgents" in r.stdout, r.stdout + r.stderr


def test_최근_N벌만_남긴다(box):
    """다 커밋해 바뀐 파일이 없는 날에도 돈다 — 예전 판은 grep -v 가 1 로 끝나 말없이 죽었다."""
    run, repo, dest = box
    for i in range(3):
        (repo / f"knowledge/c{i}.md").write_text(f"{i}\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", f"c{i}")
        r = run("ExpertAgents", HWAX_BUNDLE_RETAIN="2")
        assert r.returncode == 0, r.stdout + r.stderr
        import time
        time.sleep(1.1)                                         # 파일 이름의 초가 달라지게
    assert len(list(dest.glob("ExpertAgents-devbox-*.tar"))) == 2


def test_Drive_자리가_없으면_멈춘다(box, tmp_path):
    run, _, _ = box
    (tmp_path / "HWAXPortal/infra/.env").write_text("OTHER=1\n")
    r = run()
    assert r.returncode == 1 and "HWAX_DRIVE_REMOTE" in r.stdout
