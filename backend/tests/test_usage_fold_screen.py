# 이용 통계 M2 화면 — 접어 둔 표의 카드를 백엔드가 실제로 낸 한 판으로 node 에서 그려 본다(칸 이름이 어긋나면 undefined · NaN 이 글자로 보인다, docs/ops-dashboard)
"""왜 — 화면의 칸 이름 · 꼴은 타입 선언(usage.api.ts)을 믿는데, 그 선언이 백엔드의 실제 답과 맞는지는 타입 검사가 모른다. test_usage_screen_units 와 같은
길로(TypeScript 를 한 파일씩 옮겨 적어 react-dom/server 로 글자로 그린다) 접기 시험의 장면을 그대로 그려 본다 — 수 · 라벨이 보이는지, 접은 적이 없을 때 ·
접지 못한 원천이 있을 때 무엇을 말하는지, 사람의 이메일이 화면 글자에 없는지.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from tests.test_usage_fold import NOW, _at, _box, _fold
from tests.test_usage_fold_sections import D19, A, B, C, scene  # noqa: F401 — 장면 고정물

ROOT = Path(__file__).resolve().parents[2]
FE = ROOT / "frontend"

pytestmark = pytest.mark.skipif(
    not (FE / "node_modules/typescript").exists() or not (FE / "node_modules/react-dom").exists() or not shutil.which("node"),
    reason="frontend node_modules(typescript · react-dom) 또는 node 가 없다 — 화면 조각을 돌려 볼 수 없다",
)

_DRIVER = r"""
const ts = require('typescript'); const fs = require('fs'); const path = require('path');
const SRC = process.argv[2];
for (const rel of ['lib/usageChart.ts', 'components/usage/UsageCharts.tsx', 'components/usage/UsageBlocks.tsx',
                   'components/usage/UsageFoldCards.tsx']) {
  const js = ts.transpileModule(fs.readFileSync(path.join(SRC, rel), 'utf8'), { fileName: rel, compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2019, jsx: ts.JsxEmit.ReactJSX } });
  const dst = path.join(__dirname, rel.replace(/\.tsx?$/, '.js'));
  fs.mkdirSync(path.dirname(dst), { recursive: true }); fs.writeFileSync(dst, js.outputText);
}
const { renderToStaticMarkup } = require('react-dom/server'); const { createElement } = require('react');
const lib = require('./lib/usageChart.js');
const { FoldCards, FoldStatusCard, FoldErrors } = require('./components/usage/UsageFoldCards.js');
const req = JSON.parse(fs.readFileSync(0, 'utf8'));
const out = { ms: req.ms.map(lib.msText), span: req.span.map(([a, b]) => lib.spanText(a, b)), months: lib.monthlyRows(req.months), pages: {} };
for (const [name, rep] of Object.entries(req.reports)) {
  const s = rep.sections;
  out.pages[name] = {
    cards: renderToStaticMarkup(createElement(FoldCards, { s, axis: rep.range.axis })),
    status: renderToStaticMarkup(createElement(FoldStatusCard, { s })),
    errors: renderToStaticMarkup(createElement(FoldErrors, { s })),
  };
}
process.stdout.write(JSON.stringify(out));
"""


def _render(tmp_path_factory, reports: dict) -> dict:
    out = tmp_path_factory.mktemp("usagefoldscreen")
    (out / "drive.cjs").write_text(_DRIVER, encoding="utf-8")
    req = {"reports": reports, "ms": [None, 0, 340.4, 1234, 45000, 150000], "span": [["2026-11-17", "2026-11-20"], ["2026-11-20", "2026-11-20"], [None, None]],
           "months": [{"month": "2026-10", "accounts": None, "partial": False}, {"month": "2026-11", "accounts": 3, "partial": True}]}
    r = subprocess.run(["node", "drive.cjs", str(FE / "src")], cwd=str(out), capture_output=True, text=True, timeout=120, input=json.dumps(req),
                       env={"PATH": "/usr/bin:/bin:" + str(Path(shutil.which("node")).parent), "NODE_PATH": str(FE / "node_modules")})
    assert r.returncode == 0, r.stdout + r.stderr
    return json.loads(r.stdout)


def _text(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


@pytest.fixture()
def screen(scene, tmp_path, tmp_path_factory):  # noqa: F811
    box, rem = scene
    folded = box.build(days=7, now=NOW, labels={"service": {"heax-hub": "HEAX 허브"}})
    rem.status["gateway.test"] = 404
    _fold(box, NOW + 3600, rem)
    failed = box.build(days=7, now=NOW)
    empty = _box(tmp_path / "empty")
    empty.access((int(_at(D19, 9)), A, "login", "portal", "local"))
    return _render(tmp_path_factory, {"folded": folded, "failed": failed, "pending": empty.build(days=7, now=NOW)})


def test_셈_조각은_어림_표지와_범위를_글자로_낸다(screen):
    assert screen["ms"] == ["—", "≈ 0ms", "≈ 340ms", "≈ 1.2초", "≈ 45초", "≈ 2.5분"]
    assert screen["span"] == ["2026-11-17 ~ 2026-11-20", "2026-11-20", "—"]
    assert screen["months"] == [["2026-10", "기록 전"], ["2026-11 (일부만)", 3]]


def test_접어_둔_표의_카드는_백엔드의_답을_그대로_그린다(screen):
    page = screen["pages"]["folded"]
    text = _text(page["cards"])
    for want in ("쓴 사람(원천을 가로질러)", "MCP 도구", "MCP 심의 · RA 초안", "정문 요청(허브 앱 열기)",
                 "개인 PAT(개인 Claude) (pat)", "에이전트 서버(심의 엔진) (gw-token)", "수명이 끝난 토큰",
                 "ai-data-hub · search_cards", "hwax-deliberation · deliberate_status (상태 묻기)", "≈ 38ms", "≈ 900ms",
                 "apps/step_forge", "끝남 1", "오류 1", "30분", "자격 — 포털 챗", "기록 전", "17%"):
        assert want in text, want
    assert "undefined" not in text and "NaN" not in text and "[object" not in text, "칸 이름 · 꼴이 백엔드의 답과 어긋났다"
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", page["cards"]) and "style=" not in page["cards"], "색 · 치수는 토큰 클래스로만"
    for leak in (A, B, C):
        assert leak not in page["cards"] + page["status"], "화면에는 서로 다른 계정의 수만 낸다"
    assert page["errors"] == "", "접지 못한 원천이 없으면 아무것도 그리지 않는다"
    status = _text(page["status"])
    assert "게이트웨이(MCP 도구 호출)" in status and "2026-11-18 ~ 2026-11-20 (3일)" in status and "undefined" not in status


def test_접지_못한_원천이_있으면_까닭을_위에_보이고_앞서_접은_수는_그대로_그린다(screen):
    page = screen["pages"]["failed"]
    assert "날마다 접지 못한 원천이 있다" in page["errors"] and "게이트웨이(MCP 도구 호출): 그쪽 판이 낡았다" in _text(page["errors"])
    assert "판이 낡았다" in _text(page["status"]) and "ai-data-hub · search_cards" in _text(page["cards"])


def test_접은_적이_없으면_카드마다_그렇다고_말하고_빈_그림을_그리지_않는다(screen):
    page = screen["pages"]["pending"]
    text = _text(page["cards"])
    assert text.count("아직 접은 적이 없다") >= 10 and "<svg" not in page["cards"] and "<table" not in page["cards"]
    assert "아직 접은 적이 없다" in _text(page["status"]) and page["errors"] == "" and "undefined" not in text
