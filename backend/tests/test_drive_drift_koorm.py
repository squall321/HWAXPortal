# drive-drift.sh 의 KooRemapper 대조가 게시 직후 '올려야 한다' 를 잘못 띄우지 않는가 — 가짜 rclone · 가짜 리포로 실제로 돌린다
"""왜 — KooRemapper 의 dist-to-drive.sh 는 BUILD_INFO.txt 를 tar 에서 빼고(--exclude=bin/BUILD_INFO.txt) tar 를 만든 뒤 게시한
박스의 bin/ 에 내려놓는다. 대조가 bin/ 의 가장 새 파일 시각을 Drive tar 시각과 견주면 그 파일 때문에 게시 직후마다 ✗ 가 뜬다
(2026-10-16 build-all-to-drive heax 끝의 publish 확인). 늘 뜨는 경고는 진짜 드리프트도 가린다.

  · BUILD_INFO.txt 만 tar 보다 새것이면 일치다.
  · 바이너리가 tar 보다 새것이면 여전히 드리프트다.
"""
import os
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DRIFT = ROOT / "infra/scripts/drive-drift.sh"
T_TAR = time.time() - 3600                      # Drive 의 koorm-bin.tar.gz 시각


def _box(tmp: Path, *, binary_age: float, info_age: float) -> tuple[Path, dict]:
    """tmp/HWAXPortal/infra/scripts/drive-drift.sh 와 형제 tmp/KooRemapper, 그리고 PATH 앞의 가짜 rclone."""
    portal = tmp / "HWAXPortal"
    (portal / "infra/scripts").mkdir(parents=True)
    shutil.copy(DRIFT, portal / "infra/scripts/drive-drift.sh")
    koorm = tmp / "KooRemapper"
    (koorm / "platform/backend/bin").mkdir(parents=True)
    (koorm / "platform/frontend/dist").mkdir(parents=True)
    (koorm / "platform/.env").write_text("KOORM_DRIVE_REMOTE=fake:KooRemapper/dist\n")
    files = {koorm / "platform/backend/bin/KooRemapper": T_TAR + binary_age,
             koorm / "platform/backend/bin/BUILD_INFO.txt": T_TAR + info_age,
             koorm / "platform/frontend/dist/index.html": T_TAR - 60}
    for p, t in files.items():
        p.write_text("x")
        os.utime(p, (t, t))
    stub = tmp / "stub"
    stub.mkdir()
    stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(T_TAR)) + ".735000000"
    marker = tmp / "rclone-called"
    rc = stub / "rclone"
    rc.write_text(f'#!/usr/bin/env bash\necho "$@" >> {marker}\n'
                  f'[ "$1" = lsl ] && echo "  36395364 {stamp} $(basename "$2")"\nexit 0\n')
    rc.chmod(0o755)
    env = {**os.environ, "PATH": f"{stub}:{os.environ.get('PATH', '')}", "HOME": str(tmp)}
    return portal, env


def _run(portal: Path, env: dict) -> subprocess.CompletedProcess:
    out = subprocess.run(["bash", str(portal / "infra/scripts/drive-drift.sh"), "koorm"],
                         capture_output=True, text=True, env=env, timeout=60)
    called = (portal.parent / "rclone-called").read_text()
    assert "lsl fake:KooRemapper/dist/latest/koorm-bin.tar.gz" in called, "가짜 rclone 이 불렸다(실 Drive 를 보지 않았다)"
    return out


def test_게시_직후_BUILD_INFO_만_새것이면_일치다(tmp_path):
    portal, env = _box(tmp_path, binary_age=-300, info_age=+5)   # 바이너리는 tar 전, BUILD_INFO 는 tar 뒤(실측 0.37초 — 초 경계를 넘으면 ✗)
    out = _run(portal, env)
    assert out.returncode == 0, out.stdout + out.stderr
    assert "✓ 일치" in out.stdout and "✗" not in out.stdout


def test_바이너리가_tar_보다_새것이면_드리프트다(tmp_path):
    portal, env = _box(tmp_path, binary_age=+120, info_age=+5)
    out = _run(portal, env)
    assert out.returncode == 1, out.stdout + out.stderr
    assert "✗ platform/backend/bin" in out.stdout
