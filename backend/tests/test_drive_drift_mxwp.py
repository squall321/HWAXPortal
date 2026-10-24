# drive-drift.sh 의 MX 백서 구역 — 그쪽이 짓는 SIF(web · api · wiki)가 Drive latest/ 에 같은 크기로 있는가를 가짜 rclone · 가짜 리포로 실제로 돌려 본다
"""왜 — MX 백서는 이미지를 그 리포의 images-to-drive.sh 로 따로 올리고, 이 검사는 그 구역을 안 봤다. 10-25 에 처음 견주자 web.sif 는
Drive 와 달랐고 api.sif · wiki.sif 는 latest/ 에 없었다 — cae00 은 위키 워커를 띄울 이미지를 받을 수 없었다. 올리기가 latest/ 를 그때
올린 묶음으로 sync 해서, 안 올린 이미지는 latest/ 에서 빠진다(있어야 할 것이 없는 것도 드리프트다).

  · 세 SIF 가 같은 크기로 있으면 일치다.
  · 크기가 다르거나 latest/ 에 없으면 드리프트다(종료코드 1).
  · 이 박스에서 굽지 않은 SIF(위키 W3 전 판의 wiki.sif)는 견주지 않는다.
"""
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DRIFT = ROOT / "infra/scripts/drive-drift.sh"


def _box(tmp: Path, *, local: dict[str, int], drive: dict[str, int]) -> tuple[Path, dict]:
    """tmp/HWAXPortal 의 drive-drift.sh · 형제 tmp/MXWhitePaper(로컬 SIF) · PATH 앞의 가짜 rclone(latest/ 목록)."""
    portal = tmp / "HWAXPortal"
    (portal / "infra/scripts").mkdir(parents=True)
    shutil.copy(DRIFT, portal / "infra/scripts/drive-drift.sh")
    mx = tmp / "MXWhitePaper"
    (mx / "infra/apptainer").mkdir(parents=True)
    (mx / ".env").write_text("MXWP_IMAGES_REMOTE=fake:MXWhitePaper/images\n")
    for name, size in local.items():
        (mx / "infra/apptainer" / name).write_bytes(b"x" * size)
    stub = tmp / "stub"
    stub.mkdir()
    marker = tmp / "rclone-called"
    listing = "".join(f'echo "  {size} 2026-10-25 07:00:00.000000000 {name}"\n' for name, size in drive.items())
    rc = stub / "rclone"
    rc.write_text(f'#!/usr/bin/env bash\necho "$@" >> {marker}\n[ "$1" = lsl ] && {{\n{listing}}}\nexit 0\n')
    rc.chmod(0o755)
    env = {**os.environ, "PATH": f"{stub}:{os.environ.get('PATH', '')}", "HOME": str(tmp)}
    return portal, env


def _run(portal: Path, env: dict) -> subprocess.CompletedProcess:
    out = subprocess.run(["bash", str(portal / "infra/scripts/drive-drift.sh"), "mxwp"],
                         capture_output=True, text=True, env=env, timeout=60)
    called = (portal.parent / "rclone-called").read_text()
    assert "lsl fake:MXWhitePaper/images/latest/" in called, "가짜 rclone 이 불렸다(실 Drive 를 보지 않았다)"
    return out


def test_짓는_SIF_셋이_같은_크기로_있으면_일치다(tmp_path):
    same = {"web.sif": 30, "api.sif": 20, "wiki.sif": 10}
    portal, env = _box(tmp_path, local=same, drive=same)
    out = _run(portal, env)
    assert out.returncode == 0, out.stdout + out.stderr
    assert "── MX 백서 이미지" in out.stdout and "✓ 일치" in out.stdout and "✗" not in out.stdout


def test_크기가_다르거나_latest_에_없으면_드리프트다(tmp_path):
    portal, env = _box(tmp_path, local={"web.sif": 31, "api.sif": 20, "wiki.sif": 10}, drive={"web.sif": 30})
    out = _run(portal, env)
    assert out.returncode == 1, out.stdout + out.stderr
    assert "✗ web.sif — 로컬 31 ≠ Drive 30" in out.stdout
    assert "✗ api.sif — Drive latest/ 에 없다" in out.stdout and "✗ wiki.sif — Drive latest/ 에 없다" in out.stdout
    assert "images-to-drive.sh" in out.stdout, "올리는 길을 알려 준다"


def test_이_박스에서_굽지_않은_SIF_는_견주지_않는다(tmp_path):
    portal, env = _box(tmp_path, local={"web.sif": 30}, drive={"web.sif": 30})
    out = _run(portal, env)
    assert out.returncode == 0 and "wiki.sif" not in out.stdout, out.stdout + out.stderr
