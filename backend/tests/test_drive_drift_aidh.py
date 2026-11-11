# drive-drift.sh aidh — Drive 의 조각 목록이 전체 덤프보다 하루 넘게 낡으면 드리프트인가(cae00 요청 HP-63) — 가짜 rclone · 가짜 리포로 실제로 돌린다
"""왜 — dev 의 하루 한 번 조각 내기(parts-to-drive.sh)가 걸리지 않아 11-08 뒤 조각 목록이 끊겼고, cae00 update-all §3 이 낡음 검사로 전체 덤프 길(11 GB ·
약 1시간 30분)로 갔다. 이 검사는 같은 낡음을 cae00 이 돌리기 전에 dev 에서 먼저 본다(라운드 길의 드리프트 0 확인)."""
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DRIFT = ROOT / "infra/scripts/drive-drift.sh"


def _box(tmp: Path, *, dumps: list[str], manifests: list[str], parts_remote: str = "") -> tuple[Path, dict, Path]:
    portal = tmp / "HWAXPortal"
    (portal / "infra/scripts").mkdir(parents=True)
    shutil.copy(DRIFT, portal / "infra/scripts/drive-drift.sh")
    aidh = tmp / "AIDataHub/deploy/apptainer"
    aidh.mkdir(parents=True)
    env_lines = "AIDH_DRIVE_REMOTE=fake:AIDataHub/db\n" + (f"AIDH_PARTS_REMOTE={parts_remote}\n" if parts_remote else "")
    (aidh / ".env").write_text(env_lines)
    stub = tmp / "stub"
    stub.mkdir()
    (tmp / "dumps").write_text("".join(f"{n}\n" for n in dumps))
    (tmp / "mans").write_text("".join(f"{n}\n" for n in manifests))
    calls = tmp / "rclone-called"
    rc = stub / "rclone"
    rc.write_text(
        "#!/usr/bin/env bash\n"
        f'echo "$@" >> {calls}\n'
        '[ "$1" = lsf ] || exit 0\n'
        f'case "$2" in *db-parts/|*parts-elsewhere/) cat {tmp}/mans ;; fake:AIDataHub/db/) cat {tmp}/dumps ;; *) exit 3 ;; esac\n')
    rc.chmod(0o755)
    env = {**os.environ, "PATH": f"{stub}:{os.environ.get('PATH', '')}", "HOME": str(tmp)}
    return portal, env, calls


def _run(portal: Path, env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(portal / "infra/scripts/drive-drift.sh"), "aidh"],
                          capture_output=True, text=True, env=env, timeout=60)


def test_하루_안이면_일치(tmp_path):
    portal, env, calls = _box(tmp_path, dumps=["aidh-db-20261110-044502Z.sql.gz", "aidh-db-20261111-044502Z.sql.gz"],
                              manifests=["manifest-20261110-050000Z.json", "manifest-20261111-051500Z.json"])
    out = _run(portal, env)
    assert out.returncode == 0 and "✓ 일치(manifest-20261111-051500Z.json)" in out.stdout, out.stdout + out.stderr
    assert "lsf fake:AIDataHub/db/" in calls.read_text() and "lsf fake:AIDataHub/db-parts/" in calls.read_text(), "가짜 rclone 이 불렸다"


def test_하루_넘게_낡으면_드리프트(tmp_path):
    portal, env, _ = _box(tmp_path, dumps=["aidh-db-20261111-044502Z.sql.gz"], manifests=["manifest-20261108-003457Z.json"])
    out = _run(portal, env)
    assert out.returncode == 1, out.stdout
    assert "manifest-20261108-003457Z.json 이 전체 덤프 aidh-db-20261111-044502Z.sql.gz 보다 76시간 낡았다" in out.stdout, out.stdout
    assert "parts-to-drive.sh" in out.stdout and "docs/aidh-parts-sync/checklist.md" in out.stdout, "다시 올리는 법을 알린다"


def test_조각_목록이_없으면_드리프트(tmp_path):
    portal, env, _ = _box(tmp_path, dumps=["aidh-db-20261111-044502Z.sql.gz"], manifests=[])
    out = _run(portal, env)
    assert out.returncode == 1 and "조각 목록이 하나도 없다" in out.stdout, out.stdout


def test_덤프를_못_읽으면_확인_불가_드리프트_아님(tmp_path):
    portal, env, _ = _box(tmp_path, dumps=[], manifests=["manifest-20261111-051500Z.json"])
    out = _run(portal, env)
    assert out.returncode == 0 and "확인 불가" in out.stdout, out.stdout


def test_AIDH_PARTS_REMOTE_가_있으면_그_자리를_본다(tmp_path):
    portal, env, calls = _box(tmp_path, dumps=["aidh-db-20261111-044502Z.sql.gz"], manifests=["manifest-20261111-051500Z.json"],
                              parts_remote="fake:AIDataHub/parts-elsewhere")
    out = _run(portal, env)
    assert out.returncode == 0 and "lsf fake:AIDataHub/parts-elsewhere/" in calls.read_text(), out.stdout


def test_기본_목록에_aidh_가_든다():
    src = DRIFT.read_text(encoding="utf-8")
    assert 'WANT="${*:-portal heax koorm mxwp ste aidh}"' in src
