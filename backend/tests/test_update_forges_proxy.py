# update-forges.sh stepforge 가 박스 덮어쓰기로 프록시가 된 step_forge 를 다시 지으려다 exit 2 로 멈추지 않는가(docs/request-1125 HP-69)
"""왜 — cae00 의 전환은 step_forge 덮어쓰기(manifest.local.yaml)가 source 를 비우고 launch.mode: proxy 로 둔다. 그 박스에서 update-forges.sh stepforge 는
redeploy-app.sh --rebuild 의 'manifest.source 없음' exit 2 로 멈췄다. 덮어쓰기가 프록시면 건너뛰고 '운영 노드 판은 그쪽 묶음 올리기로' 를 알린다.

임시 HWAXPortal · HEAXHub 를 만들고 redeploy-app.sh 를 부른 기록만 남기는 가짜로 바꿔 스크립트를 그대로 돌린다(게이트웨이 확인은 닿지 않는 포트).
"""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _run(tmp_path: Path, local: str | None) -> tuple[subprocess.CompletedProcess, Path]:
    portal = tmp_path / "HWAXPortal/infra/scripts"
    portal.mkdir(parents=True)
    src = (ROOT / "infra/scripts/update-forges.sh").read_text(encoding="utf-8").replace("127.0.0.1:9110", "127.0.0.1:9")
    (portal / "update-forges.sh").write_text(src, encoding="utf-8")
    heax = tmp_path / "HEAXHub"
    (heax / "deploy/apptainer").mkdir(parents=True)
    (heax / "integrations/step_forge/.portal").mkdir(parents=True)
    log = tmp_path / "calls"
    (heax / "deploy/apptainer/redeploy-app.sh").write_text(f'echo "$*" >> {log}\n[ "$2" = "--rebuild" ] && exit 2\nexit 0\n')
    if local is not None:
        (heax / "integrations/step_forge/.portal/manifest.local.yaml").write_text(local, encoding="utf-8")
    r = subprocess.run(["bash", str(portal / "update-forges.sh"), "stepforge"], capture_output=True, text=True,
                       env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)})
    return r, log


@pytest.mark.parametrize("local", ["launch:\n  mode: proxy\n  upstream: http://node:9999\nsource: null\n",
                                   "source: null\n", "launch:\n  mode: proxy\n"])
def test_프록시_덮어쓰기면_리빌드하지_않고_건너뛴다(tmp_path, local):
    r, log = _run(tmp_path, local)
    assert r.returncode == 0, r.stdout + r.stderr
    assert not log.exists(), "프록시 앱을 다시 지으려 했다"
    assert "○ step_forge 건너뜀" in r.stdout and "운영 노드 판은 그쪽 묶음 올리기로" in r.stdout, r.stdout


@pytest.mark.parametrize("local", [None, "launch:\n  env:\n    X: '1'\n"])
def test_덮어쓰기가_없거나_프록시가_아니면_종전대로_리빌드한다(tmp_path, local):
    r, log = _run(tmp_path, local)
    assert log.read_text().strip() == "step_forge --rebuild", r.stdout
    assert "✗ step_forge 재배포 실패" in r.stdout and r.returncode == 1
