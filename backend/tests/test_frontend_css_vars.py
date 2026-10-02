# 프론트가 쓰는 CSS 변수가 전부 정의돼 있는지 — 없으면 폴백(라이트 테마 값)으로 조용히 떨어져 흰 패널이 생긴다(docs/ui-refresh 단계 1)
"""빌드(`pnpm build`)도 같은 검사를 먼저 돌리지만, 백엔드 시험만 도는 자리에서도 잡히게 여기서 한 번 더 부른다."""
import shutil
import subprocess
from pathlib import Path

import pytest

FE = Path(__file__).resolve().parents[2] / "frontend"


@pytest.mark.skipif(shutil.which("node") is None, reason="node 가 없다")
def test_쓰는_CSS_변수는_전부_정의돼_있다():
    r = subprocess.run(["node", "scripts/check-css-vars.mjs"], cwd=FE, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node 가 없다")
def test_검사기는_빠진_변수를_실제로_잡는다(tmp_path):
    """검사기가 늘 통과하면 시험이 아니다 — 정의 없는 변수를 쓰는 사본에서 실패해야 한다."""
    shutil.copytree(FE / "src", tmp_path / "src")
    shutil.copytree(FE / "scripts", tmp_path / "scripts")
    (tmp_path / "src" / "styles" / "zz-probe.css").write_text(".x { color: var(--no-such-token, #fff); }\n")
    r = subprocess.run(["node", "scripts/check-css-vars.mjs"], cwd=tmp_path, capture_output=True, text=True, timeout=60)
    assert r.returncode == 1 and "--no-such-token" in r.stderr, (r.returncode, r.stderr)
