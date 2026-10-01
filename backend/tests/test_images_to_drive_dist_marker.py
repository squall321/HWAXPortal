# images-to-drive 가 출처 모를 dist 를 올리지 않는다 — 표식이 없거나 HEAD 와 다르면 멈춘다(5차 요청 §3)
"""예전엔 표식이 없으면 업로드 때 **지금 HEAD** 표식을 찍었다. 표식 없는 옛 dist 를 새 체크아웃에서 올리면 받는 쪽 게이트
(update-all 의 dist 대 HEAD:frontend 대조)가 옛 화면을 '지금 소스' 로 읽어 거짓 초록이 된다. dist 블록을 원문 그대로 떼어
임시 git 리포 위에서 돌린다(rclone·Drive 는 안 건드린다)."""
import subprocess
from pathlib import Path

SRC = (Path(__file__).resolve().parents[2] / "infra" / "scripts" / "images-to-drive.sh").read_text(encoding="utf-8")


def _block() -> str:
    i = SRC.index('if [ -f "$REPO_ROOT/frontend/dist/index.html" ]; then')
    return SRC[i:SRC.index("\n# SearxNG", i)]


def _repo(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "repo"
    (root / "frontend" / "src").mkdir(parents=True)
    (root / "frontend" / "src" / "a.ts").write_text("x\n")
    git = ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run([*git, "add", "-A"], check=True)
    subprocess.run([*git, "commit", "-qm", "i"], check=True)
    (root / "frontend" / "dist").mkdir()
    (root / "frontend" / "dist" / "index.html").write_text("<html>")
    head = subprocess.run([*git, "rev-parse", "HEAD:frontend"], capture_output=True, text=True, check=True).stdout.strip()
    return root, head


def _run(root: Path, stage: Path) -> subprocess.CompletedProcess:
    stage.mkdir(exist_ok=True)
    script = f"set -euo pipefail\nREPO_ROOT='{root}'\nSTAGE='{stage}'\n{_block()}\necho DONE"
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True)


def test_표식이_없으면_멈추고_찍지도_않는다(tmp_path):
    root, _ = _repo(tmp_path)
    p = _run(root, tmp_path / "stage")
    assert p.returncode == 1 and "DONE" not in p.stdout, p.stdout + p.stderr
    assert not (tmp_path / "stage" / "frontend-dist.tar.gz").exists()
    assert not (root / "frontend" / "dist" / ".build-src").exists(), "옛 dist 에 지금 HEAD 표식을 찍으면 안 된다"


def test_표식이_HEAD_와_다르면_멈춘다(tmp_path):
    root, _ = _repo(tmp_path)
    (root / "frontend" / "dist" / ".build-src").write_text("0" * 40 + "\n")
    p = _run(root, tmp_path / "stage")
    assert p.returncode == 1 and "pnpm build" in p.stderr, p.stderr
    assert not (tmp_path / "stage" / "frontend-dist.tar.gz").exists()


def test_지금_소스로_빌드된_dist_는_올라간다(tmp_path):
    root, head = _repo(tmp_path)
    (root / "frontend" / "dist" / ".build-src").write_text(head + "\n")   # postbuild 가 쓰는 꼴(개행 포함)
    p = _run(root, tmp_path / "stage")
    assert p.returncode == 0 and "DONE" in p.stdout, p.stderr
    assert (tmp_path / "stage" / "frontend-dist.tar.gz").is_file()
