# drive-drift.sh 의 허브 app-data 검사 — 심링크를 따라가고, 레지스트리가 dev → 박스로 보내는 앱(sync: publish-*)의 DB 만 tar 시각과 견준다
"""왜 — 10-25 cae00 업데이트 점검에서 이 검사가 늘 통과였던 것을 찾았다. var/app_data 는 /data 이관 뒤 심링크(dev · cae00)라 `find` 가
DB 를 하나도 못 찾았다. -L 로 따라가자 이번엔 박스 고유 DB(stepforge · docforge · voicerecorder · risk — 레지스트리 sync: mirror)가
dev 에서 늘 새것이라 매번 '✗ app-data' 가 떠서 진짜 어긋남을 가렸다. 그래서 레지스트리의 publish-* 앱만 본다.

  · 링크 너머의 publish 앱 DB 가 tar 보다 새것이면 드리프트다.
  · mirror 앱 DB 만 새것이면 일치다.
  · 레지스트리를 못 읽으면 링크(시작점)를 따라 전부 본다(조용히 통과하지 않는다 — -L 이 갈리는 곳이 여기다).
  · 드리프트 안내는 구역마다 따로 올리는 길이다 — 전체 build-all-to-drive.sh 를 권하지 않는다.
"""
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DRIFT = ROOT / "infra/scripts/drive-drift.sh"
TAR_T = "2026-10-25 07:00:00"


def _box(tmp: Path, dbs: dict[str, float], *, registry: str | None = None) -> tuple[Path, dict]:
    """tmp/HWAXPortal(drive-drift · 레지스트리 · dev 처럼 backend/.venv 의 python) · tmp/HEAXHub(var/app_data → tmp/data/appdata 링크)
    · PATH 앞의 가짜 rclone(app-data tar 시각만 답한다). dbs 는 {'<앱>/<파일>': mtime}."""
    portal = tmp / "HWAXPortal"
    (portal / "infra/scripts").mkdir(parents=True)
    shutil.copy(DRIFT, portal / "infra/scripts/drive-drift.sh")
    if registry is None:
        shutil.copy(ROOT / "infra/services.yaml", portal / "infra/services.yaml")
    else:
        (portal / "infra/services.yaml").write_text(registry)
    (portal / "backend/.venv/bin").mkdir(parents=True)
    os.symlink(sys.executable, portal / "backend/.venv/bin/python")
    hub = tmp / "HEAXHub"
    (hub / "var").mkdir(parents=True)
    (hub / ".env").write_text("HEAX_DRIVE_REMOTE=fake:HEAX/dist\n")
    data = tmp / "data" / "appdata"
    data.mkdir(parents=True)
    os.symlink(data, hub / "var/app_data")
    for rel, mtime in dbs.items():
        p = data / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"")
        os.utime(p, (mtime, mtime))
    stub = tmp / "stub"
    stub.mkdir()
    rc = stub / "rclone"
    rc.write_text('#!/usr/bin/env bash\necho "$@" >> "' + str(tmp / "rclone-called") + '"\n'
                  'case "$*" in "lsl fake:HEAX/app-data/latest/app-data.tar.gz") echo "  9 ' + TAR_T + '.000000000 app-data.tar.gz" ;; esac\n'
                  'exit 0\n')
    rc.chmod(0o755)
    return portal, {**os.environ, "PATH": f"{stub}:{os.environ.get('PATH', '')}", "HOME": str(tmp)}


def _run(portal: Path, env: dict) -> subprocess.CompletedProcess:
    out = subprocess.run(["bash", str(portal / "infra/scripts/drive-drift.sh"), "heax"],
                         capture_output=True, text=True, env=env, timeout=60)
    assert "lsl fake:HEAX/app-data/latest/app-data.tar.gz" in (portal.parent / "rclone-called").read_text(), "가짜 rclone 이 불렸다"
    return out


def _epoch(s: str) -> float:
    return time.mktime(time.strptime(s, "%Y-%m-%d %H:%M:%S"))


OLD, NEW = _epoch("2026-10-24 07:00:00"), _epoch("2026-10-25 08:00:00")


def test_링크_너머의_publish_앱_DB_가_tar_보다_새것이면_드리프트다(tmp_path):
    portal, env = _box(tmp_path, {"materialtwin_web/materialtwin.db": NEW})
    out = _run(portal, env)
    assert out.returncode == 1 and "✗ app-data — DB 가 Drive tar(" in out.stdout, out.stdout + out.stderr


def test_박스_고유_mirror_앱_DB_만_새것이면_일치다(tmp_path):
    portal, env = _box(tmp_path, {"materialtwin_web/materialtwin.db": OLD, "step_forge/stepforge.db": NEW,
                                  "doc_forge/docforge.db": NEW, "voice_recorder/voicerecorder.db": NEW})
    out = _run(portal, env)
    assert out.returncode == 0 and "✓ 일치" in out.stdout and "app-data" not in out.stdout, out.stdout + out.stderr


def test_레지스트리를_못_읽으면_링크를_따라_전부_본다(tmp_path):
    portal, env = _box(tmp_path, {"materialtwin_web/materialtwin.db": OLD, "step_forge/stepforge.db": NEW}, registry="services: [깨진")
    out = _run(portal, env)
    assert out.returncode == 1 and "✗ app-data" in out.stdout, "조용히 통과하지 않는다 — " + out.stdout


def test_드리프트_안내는_구역마다_따로_올리는_길이다(tmp_path):
    portal, env = _box(tmp_path, {"materialtwin_web/materialtwin.db": NEW})
    out = _run(portal, env).stdout
    assert "build-all-to-drive.sh portal" in out and "drive-push-sif.sh --dry-run" in out
    assert "# 전체(빌드+업로드)" not in out and "bash deploy/apptainer/dist-to-drive.sh" not in out, "허브 통째 올리기는 되돌림 판 · 대조 목록을 깎는다"
    assert 'HEAX_BACKUP_EXCLUDE="doc_forge step_forge voice_recorder"' in out
