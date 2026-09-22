# `stc` 가 **클러스터 이름**으로 다시 쓰이지 못하게 — 한 글자 차이가 토폴로지를 바꾼다(2026-09-22)
"""왜 리포를 가로질러 보나 — 이건 한 파일의 오타가 아니라 **이름 하나의 오해**였고, 그
오해가 세 리포의 주석·설정·문서에 각자 퍼져 있었다.

무엇이 진실인가.
  · **ste**  = **24대** 클러스터(smart-twin-cluster-26, 헤드 icn401-0116-h01) **이자**
               그 위에 도는 SmartTwinExplorer 웹 서비스의 이름.
  · **stcx** = **356대** 클러스터. SmartTwinMCP 의 전각도·단일 낙하 대상이고,
               공개 호스트 `stcx.sec.samsung.net` 도 여기다.
  · 둘은 **다른 클러스터**다. 예전에 24대 쪽을 `stc` 라고 적어 두었던 것이 화근이었다.

무엇이 걸렸나(실제 피해). 2026-09-22 하루에 같은 오해를 **세 번** 했다. 한 번은 "둘이
같은 클러스터" 로 접어서 *파일을 어떻게 옮기나* 를 없는 문제로 만들었고, 한 번은 "완전히
단절된 둘" 로 접어서 **이미 있는 공유 경로**를 못 보고 없는 전송 계층을 지을 뻔했다.
이름이 틀리면 그 위에서 내린 설계 판단이 통째로 어긋난다. 그래서 규모(24 / 356)를
판별 기준으로 삼고, 그 이름을 기계로 지킨다.

⚠ **면제 셋** — 이것들은 위반이 아니다.
  ① `ssh stc` · `STMC_SLURM_SSH` · `~/.ssh/config` · `rsync -e` — **접속 별칭**이다.
     바꾸면 접속과 배포가 깨진다. 이름 정리가 접속을 깨는 것보다 중요한 적은 없다.
  ② `stc-` 로 시작하는 잡 ID 접두사 — 이미 발급된 식별자다.
  ③ 날짜가 박힌 **기록 파일**(context-notes·checklist·심의 예제) — 그때의 사실을 적은
     로그다. 다시 쓰면 기록을 위조하는 셈이라 손대지 않는다.
"""
import re
from pathlib import Path

import pytest

SIBLINGS = ("HWAXPortal", "SmartTwinExplorer", "SmartTwinMCP")
ROOT = Path(__file__).resolve().parents[3]          # ~/claude
EXTS = ("*.py", "*.sh", "*.md", "*.yaml", "*.yml", "*.ts", "*.tsx", "*.env", "*.example")
SKIP_DIRS = (".venv", "venv", "node_modules", "__pycache__", ".git", "build", "dist",
             "var", "backups", ".tools", "upstream")
# 기록 파일 — 위 ③. 파일 이름으로 뺀다(내용이 아니라 성격이 다르다).
# 이 가드 자신도 뺀다 — 규칙을 설명하려면 그 이름을 인용해야 한다.
SKIP_FILES = ("context-notes.md", "checklist.md", "test_cluster_naming.py")
SKIP_PARTS = ("deliberation-quality/examples",)

# 홀로 선 `stc` 만 본다 — `stcx`·`ste`·`stc-...` 는 걸리지 않는다.
BARE_STC = re.compile(r"(?<![A-Za-z0-9_./-])stc(?![A-Za-z0-9_./-])")
# 접속 별칭 문맥 — 같은 줄에 이것이 있으면 면제(위 ①).
# `stc:` 는 scp/rsync 의 **별칭:경로** 표기다 — 이것도 접속 별칭 용법이다.
ALIAS_CTX = re.compile(r"ssh\s+stc|STMC_SLURM_SSH|ssh[_ ]config|rsync|stc:|Host\s+stc|별칭")

# 남은 위반 — **줄어들기만 한다**(0 이면 비운 채로 둔다)
ALLOWED: dict[str, int] = {}


def _files():
    for repo in SIBLINGS:
        base = ROOT / repo
        if not base.is_dir():
            continue
        for ext in EXTS:
            for f in base.rglob(ext):
                if any(p in SKIP_DIRS for p in f.parts):
                    continue
                if f.name in SKIP_FILES:
                    continue
                rel = f.relative_to(base).as_posix()
                if any(part in rel for part in SKIP_PARTS):
                    continue
                yield repo, base, f


def _hits() -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for repo, base, f in _files():
        try:
            lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for n, line in enumerate(lines, 1):
            if not BARE_STC.search(line):
                continue
            if ALIAS_CTX.search(line):
                continue
            found.setdefault(repo, []).append(f"{f.relative_to(base)}:{n}: {line.strip()[:100]}")
    return found


def test_the_repos_are_actually_there():
    """형제 리포가 없으면 아래 시험은 **아무것도 안 보고 통과**한다 — 그 상태를 구분한다."""
    present = [r for r in SIBLINGS if (ROOT / r).is_dir()]
    if len(present) < 2:
        pytest.skip(f"형제 리포가 부족하다({present}) — 이 박스에서는 판정하지 않는다")
    assert sum(1 for _ in _files()) > 100, "스캔 대상이 너무 적다 — 경로 유도가 빗나갔다"


def test_stc_is_not_used_as_a_cluster_name():
    if len([r for r in SIBLINGS if (ROOT / r).is_dir()]) < 2:
        pytest.skip("형제 리포 부족")
    found = _hits()
    over = {r: v for r, v in found.items() if len(v) > ALLOWED.get(r, 0)}
    assert not over, (
        "`stc` 가 클러스터 이름으로 쓰였다 — 24대는 **ste**, 356대는 **stcx** 다.\n"
        "접속 별칭(`ssh stc`)이라면 그 문맥을 같은 줄에 적으면 면제된다.\n"
        + "\n".join(f"  [{r}]\n    " + "\n    ".join(v) for r, v in over.items()))


def test_the_allowance_only_shrinks():
    """위반이 줄었는데 ALLOWED 를 안 줄이면, 다음 한 건이 조용히 들어온다."""
    if len([r for r in SIBLINGS if (ROOT / r).is_dir()]) < 2:
        pytest.skip("형제 리포 부족")
    found = _hits()
    stale = {r: (n, len(found.get(r, []))) for r, n in ALLOWED.items() if len(found.get(r, [])) < n}
    assert not stale, f"허용치를 실제 개수로 줄여라: {stale}"


def test_the_exemptions_actually_exempt():
    """면제가 정말 걸리는지 — 안 걸리면 배포 스크립트를 고치라고 계속 고발한다."""
    for line in ("ssh stc 'sinfo'",
                 'HOST="${STMC_SLURM_SSH:-}"   # 비면 로컬, stc 면 원격',
                 "rsync -e ssh stc:/data/x .",
                 "# `ssh stc` 별칭으로 헤드노드에 붙는다"):
        assert BARE_STC.search(line) and ALIAS_CTX.search(line), line


def test_the_pattern_would_catch_a_real_violation():
    """좁게 잡다가 0건을 훑고 통과하는 상태를 구분한다."""
    bad = "# 운영 클러스터 stc 에서 돈다"
    assert BARE_STC.search(bad) and not ALIAS_CTX.search(bad)
    for ok in ("stcx 클러스터", "ste 헤드노드", "stc-01ABC 잡 ID", "smart-twin-cluster"):
        assert not BARE_STC.search(ok) or ALIAS_CTX.search(ok), ok
