# `instance list | … | grep -q` 가 다시 들어오지 못하게 — 떠 있는 것을 "없다"로 읽던 패턴(2026-09-19~20)
"""왜 리포를 가로질러 보나 — 이 결함은 **한 리포의 버그가 아니라 관용구**였다. 같은 줄이
KooRemapper(감독자) · HEAXHub(워치독·start·stop·boot·heal) · 게이트웨이(프로비저닝) ·
SignalForge(드라이브 동기화) · 포털(update-all·백업)에 **각자** 복사돼 있었고, 한 곳을 고쳐도
나머지는 그대로였다. 그래서 '고쳤다'가 아니라 '다시 들어오면 깨진다'로 못 박는다.

기구 — `grep -q` 는 첫 매칭에서 끝난다. `pipefail` 아래서는 아직 쓰고 있던 `apptainer` 가
SIGPIPE(141)로 죽어 **파이프라인 전체가 실패**하고, 호출부는 그것을 "인스턴스 없음" 으로 읽는다.
실측(dev, 2026-09-19): 유휴 400회 중 0회지만 `instance list` 를 6개 동시에 돌리는 경합에서
**600회 중 88회(14.7%)**. 그 오판으로 멀쩡한 API 가 하루 168회 재기동됐고, `boot.sh` 는 떠 있는
인스턴스의 상태 파일을 지울 뻔했으며, `stop.sh` 는 "내렸다" 고 말하고 안 내렸다.

고침은 **출력을 먼저 받는 것**이다(파이프가 없으면 조기 종료도 없다). 되돌리기 어려운 일을 시키는
자리는 한 걸음 더 간다 — 조회 실패(2)와 부재(1)를 가른다(HEAXHub `_common.sh:instance_running`).

⚠ 이 가드는 **`instance list` 계열만** 본다. `ss -tln | grep -q` 같은 표시용 자리는 같은 꼴이지만
판정을 바꾸지 않아 일부러 뺐다(넓히면 소음이 되고, 소음이 나면 아무도 안 본다).
"""
import re
from pathlib import Path

import pytest

SIBLINGS = ("HWAXPortal", "HWAXMcpGateway", "HEAXHub", "SignalForge", "StepForge", "KooRemapper")
ROOT = Path(__file__).resolve().parents[3]          # ~/claude
PATTERN = re.compile(r"instance\s+list.*\|.*(grep\s+-q|head\s)")
# 소스만 본다 — 배포 번들·런타임 산출물에는 **옛 사본**이 들어 있고(예: dist-bundle/…/watchdog.sh),
# 그것을 세면 고칠 수 없는 것을 계속 고발한다(다음 번들을 만들면 사라진다).
SKIP_DIRS = (".venv", "node_modules", ".tools", "upstream", "koorm-work", ".git",
             "dist-bundle", "var", "backups")

# 남은 위반 — **줄어들기만 한다**(0 이면 이 사전을 비운 채로 둔다)
ALLOWED: dict[str, int] = {}


def _hits() -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for repo in SIBLINGS:
        base = ROOT / repo
        if not base.is_dir():
            continue
        for f in base.rglob("*.sh"):
            if any(part in SKIP_DIRS for part in f.parts):
                continue
            try:
                lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for n, line in enumerate(lines, 1):
                if line.lstrip().startswith("#"):
                    continue                      # 주석은 설명이다(이 파일도 그 문구를 인용한다)
                if PATTERN.search(line):
                    found.setdefault(repo, []).append(f"{f.relative_to(base)}:{n}: {line.strip()[:90]}")
    return found


def test_the_repos_are_actually_there():
    """형제 리포가 하나도 없으면 아래 시험은 **아무것도 안 보고 통과**한다 — 그 상태를 구분한다."""
    present = [r for r in SIBLINGS if (ROOT / r).is_dir()]
    if len(present) < 2:
        pytest.skip(f"형제 리포가 {present} 뿐이라 가로지르는 검사가 무의미하다")
    assert present


def test_no_instance_list_decision_pipe_comes_back():
    found = _hits()
    over = {r: v for r, v in found.items() if len(v) > ALLOWED.get(r, 0)}
    assert not over, "떠 있는 인스턴스를 '없다'로 읽는 패턴이 다시 들어왔다 —\n" + "\n".join(
        f"  [{r}] 허용 {ALLOWED.get(r, 0)} / 발견 {len(v)}\n    " + "\n    ".join(v[:5])
        for r, v in over.items())


def test_the_allowance_only_shrinks():
    """허용치가 실제보다 크면 '빚' 이 조용히 남는다 — 고쳤으면 수를 내려야 한다."""
    found = {r: len(v) for r, v in _hits().items()}
    stale = {r: (n, found.get(r, 0)) for r, n in ALLOWED.items() if found.get(r, 0) < n}
    assert not stale, f"허용치가 낡았다(실제보다 크다) — 내려라: {stale}"
