# update-all §3 — AIDataHub 병합이 3(열이 빠졌다)으로 끝나면 '병합함' 표식을 안 적어 다음 실행이 같은 덤프로 다시 병합하는가(10-17 cae00 리뷰 H1)
"""왜 — 10-17 cae00 에서 0032 가 잠금으로 늦은 채 병합이 돌아 m3 열이 ✓ 로 빠졌고, 다음 update-all 은 같은 덤프라 `.last-merged`
를 보고 병합을 건너뛰었다. 이제 merge-from-drive.sh 는 dev 에만 있는 열이 있으면 3 으로 끝나고, §3 은 그것을 실패와 갈라 말하되
표식은 0 일 때만 적는다.

update-all 원문의 §3 구획을 그대로 임시 박스에서 돌린다. AIDataHub 의 두 스크립트만 대역이다.
"""
import os
import subprocess
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "infra" / "scripts"
UA = (SCRIPTS / "update-all.sh").read_text(encoding="utf-8")
_START = 'hr "3) AIDataHub 데이터(에이전트·레코드) 동기화"'
_END = "# ── 2c) ste(SmartTwinExplorer)"


def _section() -> str:
    assert _START in UA and _END in UA
    i = UA.index(_START)
    return UA[i:UA.index(_END, i)]


class _Box:
    def __init__(self, tmp: Path):
        self.tmp = tmp.resolve()
        self.aidh = self.tmp / "AIDataHub"
        appt = self.aidh / "deploy/apptainer"
        (appt / "backups").mkdir(parents=True)
        (appt / ".env").write_text("AIDH_DRIVE_REMOTE=Fake:AIDataHub/db-dumps\n", encoding="utf-8")
        (appt / "sync-from-drive.sh").write_text("#!/usr/bin/env bash\nexit 0\n")
        self.merge = appt / "merge-from-drive.sh"
        self.merge.write_text('#!/usr/bin/env bash\necho "merge dump=$AIDH_MERGE_DUMP" >> "$MERGE_LOG"\nexit "${FAKE_RC:-0}"\n')
        for f in (appt / "sync-from-drive.sh", self.merge):
            f.chmod(0o755)
        self.dump = appt / "backups/aidh-db-20261016-193902Z.sql.gz"
        self.dump.write_bytes(b"")
        (appt / "backups/latest.sql.gz").symlink_to(self.dump.name)
        self.marker = appt / "backups/.last-merged"
        self.log = self.tmp / "merge.log"

    def run(self, **env) -> str:
        body = _section()
        assert "/home/" not in body, "구획에 실물 경로가 박혀 있다"
        script = "\n".join([
            "set -uo pipefail", f'cd "{self.tmp}"', f'AIDH_DIR="{self.aidh}"', f'SELF_REPO="{self.tmp}/HWAXPortal"',
            'hr() { echo "HR:$*"; }; ok() { echo "OK:$*"; }; bad() { echo "BAD:$*"; }; fail() { echo "FAIL:$*"; FAIL=1; }',
            'hwax_skip() { echo "SKIP:$*"; }', body, "echo END",
        ])
        full = {"PATH": os.environ["PATH"], "HOME": str(self.tmp), "LANG": "C.UTF-8", "MERGE_LOG": str(self.log), **env}
        r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=60, env=full)
        assert "END" in r.stdout and "unbound variable" not in r.stderr and "command not found" not in r.stderr, r.stdout + r.stderr
        return r.stdout

    def merges(self) -> int:
        return len(self.log.read_text().splitlines()) if self.log.exists() else 0


@pytest.fixture()
def box(tmp_path):
    return _Box(tmp_path)


def test_병합이_되면_표식을_적고_같은_덤프는_다음에_건너뛴다(box):
    out = box.run()
    assert "OK:AIDH 데이터 merge(" in out and box.marker.read_text() == box.dump.name, out
    assert f"merge dump={box.dump}" in box.log.read_text(), "병합은 받은 덤프 그 파일로 돈다"
    out = box.run()
    assert "merge 생략" in out and box.merges() == 1, out


def test_열이_빠져_3이면_실패와_갈라_말하고_표식을_안_적어_다음에_다시_병합한다(box):
    out = box.run(FAKE_RC="3")
    assert not box.marker.exists(), "3 인데 표식을 적으면 다음 update-all 이 같은 덤프라 건너뛴다(10-17 cae00)"
    line = next(ln for ln in out.splitlines() if ln.startswith("BAD:"))
    assert "dev 에만 있는 열이 빠졌다" in line and "다시 병합한다" in line and "merge 실패" not in line, line
    out = box.run(FAKE_RC="0")
    assert box.merges() == 2 and box.marker.read_text() == box.dump.name, out


def test_실패는_종료코드를_적어_알리고_표식을_안_적는다(box):
    out = box.run(FAKE_RC="1")
    assert "BAD:AIDH 데이터 merge 실패(rc 1)" in out and not box.marker.exists(), out


def test_병합_스크립트가_없으면_없다고_말한다(box):
    box.merge.unlink()
    out = box.run()
    assert "merge-from-drive.sh 없음" in out and box.merges() == 0 and not box.marker.exists(), out
