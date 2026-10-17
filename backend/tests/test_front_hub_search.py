# 앱 검색이 HEAX 허브 앱도 찾는지 — 허브 앱만 · 쓸 수 있는 것만 · 이미 타일인 앱은 빼고 · 이름 · 설명 · id 로(수정 제안서 F4, 10-18)
"""왜 — 포털 「앱」 검색은 포털 타일(이름 · 소개 · 분류)만 봤다. MaterialTwin · StepForge 같은 허브 앱은 'HEAX Hub' 타일 안에 있어 검색에
걸리지 않았고, 10-18 사용자가 「MaterialTwin 이 연결 해제되었나」로 물었다. 화면 코드를 node 로 돌린다(test_front_window_payload._node)."""
import shutil
from pathlib import Path

import pytest

from tests.test_front_window_payload import _FE, _node

pytestmark = pytest.mark.skipif(
    not (_FE / "node_modules/typescript").exists() or not shutil.which("node"),
    reason="frontend node_modules(typescript) 또는 node 가 없다 — 화면 조각을 돌려 볼 수 없다",
)
_PAGE = Path(__file__).resolve().parents[2] / "frontend" / "src" / "pages" / "PortalHomePage.tsx"


def _app(app, label, desc="", allowed=True, absent=False):
    return {"app": app, "label": label, "description": desc, "tool_count": 3, "reachable": True, "allowed": allowed,
            "muted": False, **({"absent": True} if absent else {})}


def _hits(apps, tiles, q):
    return _node(["components/catalog/hubSearch.ts"],
                 "const { hubMatches } = require('./components/catalog/hubSearch.js');"
                 " out(hubMatches(input.apps, new Set(input.tiles), input.q).map(a => a.slug));",
                 {"apps": apps, "tiles": tiles, "q": q})


def test_허브_앱을_이름_설명_id_로_찾는다():
    apps = [_app("heax-materialtwin_web", "MaterialTwin Web", "물성 카탈로그"), _app("heax-step_forge", "StepForge", "STEP 해석"),
            _app("signalforge", "SignalForge VOC")]
    assert _hits(apps, [], "materialtwin") == ["materialtwin_web"]
    assert _hits(apps, [], "물성") == ["materialtwin_web"], "설명으로도"
    assert _hits(apps, [], "step_") == ["step_forge"], "id 로도"
    assert _hits(apps, [], "signal") == [], "허브 앱(heax-)이 아닌 게이트웨이 앱은 타일 쪽 일이다"
    assert _hits(apps, [], "  ") == [], "검색어가 없으면 싣지 않는다"


def test_쓸_수_없거나_없는_앱_이미_타일인_앱은_뺀다():
    apps = [_app("heax-hwax_risk", "HWAX Risk Review"), _app("heax-thermal_shock_mcp", "Thermal Shock", allowed=False),
            _app("heax-paper_ingest", "Paper Ingest", absent=True)]
    assert _hits(apps, ["hwax-risk"], "risk") == [], "포털 타일(hwax-risk)로 이미 있다"
    assert _hits(apps, [], "thermal") == [] and _hits(apps, [], "paper") == []


def test_고르면_허브의_그_앱_화면을_연다():
    src = _PAGE.read_text(encoding="utf-8")
    assert "window.open(`/heax-hub/apps/${encodeURIComponent(slug)}`, '_blank', 'noopener')" in src
    assert "if (!q || hubApps !== null || hubErr) return;" in src, "검색어를 칠 때 한 번만 부른다"
