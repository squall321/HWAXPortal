# update-all §3 — AIDataHub 병합이 3(열이 빠졌다)으로 끝나면 '병합함' 표식을 안 적어 다음 실행이 같은 덤프로 다시 병합하는가(10-17 cae00 리뷰 H1) · 조각 길 먼저(docs/aidh-parts-sync)
"""왜 — 10-17 cae00 에서 0032 가 잠금으로 늦은 채 병합이 돌아 m3 열이 ✓ 로 빠졌고, 다음 update-all 은 같은 덤프라 `.last-merged`
를 보고 병합을 건너뛰었다. 이제 merge-from-drive.sh 는 dev 에만 있는 열이 있으면 3 으로 끝나고, §3 은 그것을 실패와 갈라 말하되
표식은 0 일 때만 적는다.

조각 길(11-05) — 전체 덤프는 이름이 매일 바뀌어 바뀐 줄이 없어도 통째로 병합했다(한 시간 남짓). §3 은 fetch-parts.sh 를 먼저 불러 바뀐
조각만 병합하고(10 = 바뀐 것 없음이면 전체 길로 가지 않는다), 목록이 없거나(4) 받기 · 병합이 실패하면 전체 덤프 길로 간다.

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
        # 조각 길(AIDH_MERGE_PARTS=1)은 FAKE_PARTS_RC, 전체 덤프 길은 FAKE_RC 로 끝난다 — 한 실행에서 두 길을 갈라 본다.
        self.merge.write_text('#!/usr/bin/env bash\n'
                              'if [ "${AIDH_MERGE_PARTS:-}" = 1 ]; then echo "merge parts" >> "$MERGE_LOG"; exit "${FAKE_PARTS_RC:-0}"; fi\n'
                              'echo "merge dump=$AIDH_MERGE_DUMP" >> "$MERGE_LOG"\nexit "${FAKE_RC:-0}"\n')
        for f in (appt / "sync-from-drive.sh", self.merge):
            f.chmod(0o755)
        self.fetch = appt / "fetch-parts.sh"
        self.fetch_log = self.tmp / "fetch.log"
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
        full = {"PATH": os.environ["PATH"], "HOME": str(self.tmp), "LANG": "C.UTF-8", "MERGE_LOG": str(self.log),
                "FETCH_LOG": str(self.fetch_log), **env}
        r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=60, env=full)
        assert "END" in r.stdout and "unbound variable" not in r.stderr and "command not found" not in r.stderr, r.stdout + r.stderr
        return r.stdout

    def merges(self) -> int:
        return len(self.log.read_text().splitlines()) if self.log.exists() else 0

    def merge_kinds(self) -> list[str]:
        return [ln.split()[1].split("=")[0] for ln in self.log.read_text().splitlines()] if self.log.exists() else []

    def with_parts(self) -> "_Box":
        """AIDataHub 가 조각 길을 아는 판 — 받기는 FAKE_FETCH_RC, 적기(--commit)는 FAKE_COMMIT_RC 로 끝난다."""
        self.fetch.write_text('#!/usr/bin/env bash\n'
                              'if [ "${1:-}" = --commit ]; then echo commit >> "$FETCH_LOG"; exit "${FAKE_COMMIT_RC:-0}"; fi\n'
                              'echo fetch >> "$FETCH_LOG"; exit "${FAKE_FETCH_RC:-0}"\n')
        self.fetch.chmod(0o755)
        return self

    def fetches(self) -> list[str]:
        return self.fetch_log.read_text().split() if self.fetch_log.exists() else []


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


# ── 조각 길(docs/aidh-parts-sync) ─────────────────────────────────────────

def test_조각_변화가_없으면_어떤_병합도_하지_않는다(box):
    out = box.with_parts().run(FAKE_FETCH_RC="10")
    assert "OK:AIDH 조각 변화 없음 — merge 생략" in out and box.merges() == 0 and box.fetches() == ["fetch"], out
    assert not box.marker.exists(), "전체 덤프 표식은 조각 길이 적지 않는다"
    assert "페르소나" not in out, "병합이 돌지 않은 실행은 운영자 미리보기를 하지 않는다"


def test_조각을_받으면_조각_길로_병합하고_병합함을_적는다(box):
    out = box.with_parts().run()
    assert "OK:AIDH 조각 merge(" in out and box.merge_kinds() == ["parts"] and box.fetches() == ["fetch", "commit"], out
    assert "BAD:HE팀 운영자 페르소나 미리보기를 못 했다" in out, "조각 길로 병합한 실행도 운영자 미리보기를 한다(대역 박스엔 동기화 스크립트가 없다)"


def test_조각_병합이_3이면_병합함을_안_적고_전체_길로도_가지_않는다(box):
    out = box.with_parts().run(FAKE_PARTS_RC="3")
    line = next(ln for ln in out.splitlines() if ln.startswith("BAD:AIDH 조각"))
    assert "dev 에만 있는 열이 빠졌다" in line and "다시 병합한다" in line, line
    assert box.merge_kinds() == ["parts"] and box.fetches() == ["fetch"] and not box.marker.exists(), out


def test_조각_병합이_실패하면_전체_덤프_길로_다시_한다(box):
    out = box.with_parts().run(FAKE_PARTS_RC="1")
    assert "BAD:AIDH 조각 merge 실패(rc 1) — 아래 전체 덤프 길로" in out, out
    assert box.merge_kinds() == ["parts", "dump"] and box.fetches() == ["fetch"], out
    assert "OK:AIDH 데이터 merge(" in out and box.marker.read_text() == box.dump.name, out


@pytest.mark.parametrize("rc,word", [("4", "SKIP:AIDH 조각 동기화 Drive 에 조각 목록이 없다"), ("1", "BAD:AIDH 조각 받기 실패(rc 1)")])
def test_목록이_없거나_받기가_실패하면_전체_덤프_길(box, rc, word):
    out = box.with_parts().run(FAKE_FETCH_RC=rc)
    assert word in out and box.merge_kinds() == ["dump"] and box.marker.read_text() == box.dump.name, out


def test_AIDH_SYNC_MODE_full_이면_조각_길을_건너뛴다(box):
    out = box.with_parts().run(AIDH_SYNC_MODE="full")
    assert "SKIP:AIDH 조각 동기화 AIDH_SYNC_MODE=full" in out and box.fetches() == [] and box.merge_kinds() == ["dump"], out


def test_조각_길을_모르는_AIDataHub_면_말하고_전체_덤프_길(box):
    out = box.run()
    assert "SKIP:AIDH 조각 동기화 AIDataHub 에 fetch-parts.sh 가 없다" in out and box.merge_kinds() == ["dump"], out


def test_병합함을_못_적으면_알린다(box):
    out = box.with_parts().run(FAKE_COMMIT_RC="1")
    assert "BAD:AIDH 조각 merge 는 됐지만 '병합함' 을 못 적었다" in out and box.merge_kinds() == ["parts"], out

