# 이용 통계 화면의 셈 조각과 막대 그림을 node 로 실제로 돌려 본다 — 기록 전(null)은 그리지 않고 띠로 · 막대 폭 상한 · 해를 넘는 눈금(docs/ops-dashboard)
"""왜 — 화면 쪽 판정(null 을 0 막대로 그리는가, 그림 끝 날짜에 해가 붙는가, 기록 전 달을 접는가)은 타입 검사 · 린트로 안 잡힌다.
test_admin_screen_units 와 같은 길이다 — TypeScript 를 한 파일씩 옮겨 적어(transpile) node 로 부르고, 그림은 react-dom/server 로 글자로 그린다.
그림의 색은 클래스(토큰)로만 칠한다 — 마크업에 hex 가 끼면 래칫 밖에서 색이 생긴다.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FE = ROOT / "frontend"

pytestmark = pytest.mark.skipif(
    not (FE / "node_modules/typescript").exists() or not (FE / "node_modules/react-dom").exists() or not shutil.which("node"),
    reason="frontend node_modules(typescript · react-dom) 또는 node 가 없다 — 화면 조각을 돌려 볼 수 없다",
)

_DRIVER = r"""
const ts = require('typescript'); const fs = require('fs'); const path = require('path');
const SRC = process.argv[2];
for (const rel of ['lib/usageChart.ts', 'components/usage/UsageCharts.tsx']) {
  const js = ts.transpileModule(fs.readFileSync(path.join(SRC, rel), 'utf8'), { fileName: rel, compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2019, jsx: ts.JsxEmit.ReactJSX } });
  const dst = path.join(__dirname, rel.replace(/\.tsx?$/, '.js'));
  fs.mkdirSync(path.dirname(dst), { recursive: true }); fs.writeFileSync(dst, js.outputText);
}
const { renderToStaticMarkup } = require('react-dom/server'); const { createElement } = require('react');
const lib = require('./lib/usageChart.js');
const { ColumnChart, StatTile } = require('./components/usage/UsageCharts.js');
const req = JSON.parse(fs.readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify({
  niceMax: req.niceMax.map(lib.niceMax),
  compact: req.compact.map(lib.compact),
  columns: lib.columns(req.values, req.width, 100, lib.niceMax(lib.maxOf(req.values))),
  nullRuns: lib.nullRuns(req.values),
  edge: req.edges.map(lib.edgeLabels),
  fold: lib.foldLeading(req.months, (r) => r.accounts == null, (r) => r.month),
  perDay: lib.perDay(req.conv, req.axis),
  chart: renderToStaticMarkup(createElement(ColumnChart, { title: 'DAU', values: req.values, labels: req.labels, unit: '명' })),
  tile: renderToStaticMarkup(createElement(StatTile, { label: '챗 턴', value: 12900 })),
}));
"""

AXIS = [f"2026-10-{d:02d}" for d in range(20, 32)]          # 12일
VALUES = [None, None, None, 0, 3, 7, 0, 12, 5, None, 1, 2]       # 앞 셋은 기록 전, 가운데 하나는 빈 날(기록 틈)


@pytest.fixture(scope="module")
def screen(tmp_path_factory):
    out = tmp_path_factory.mktemp("usagescreen")
    (out / "drive.cjs").write_text(_DRIVER, encoding="utf-8")
    req = {"niceMax": [0, 1, 7, 12, 99, 101, 2400], "compact": [999, 1284, 12900, 250000, 3400000],
           "values": VALUES, "labels": AXIS, "width": 120,
           "edges": [["2026-10-04", "2026-11-02"], ["2025-09-29", "2026-11-02"], []],
           "months": [{"month": "2025-09", "accounts": None}, {"month": "2025-10", "accounts": None},
                      {"month": "2025-11", "accounts": 4}, {"month": "2025-12", "accounts": None}],
           "conv": [{"day": "2026-10-21", "n": 2}, {"day": "2026-10-21", "n": 3}, {"day": "2026-10-30", "n": 1}],
           "axis": AXIS}
    r = subprocess.run(["node", "drive.cjs", str(FE / "src")], cwd=str(out), capture_output=True, text=True, timeout=120,
                       input=json.dumps(req),
                       env={"PATH": "/usr/bin:/bin:" + str(Path(shutil.which("node")).parent), "NODE_PATH": str(FE / "node_modules")})
    assert r.returncode == 0, r.stdout + r.stderr
    return json.loads(r.stdout)


def test_눈금_꼭대기는_1_2_5_로_올리고_큰_수는_줄인다(screen):
    assert screen["niceMax"] == [1, 1, 10, 20, 100, 200, 5000]
    assert screen["compact"] == ["999", "1,284", "12.9K", "250K", "3.4M"]


def test_기록_전은_막대가_아니라_띠고_막대는_칸을_다_채우지_않는다(screen):
    cols = screen["columns"]["cols"]
    assert [c["h"] > 0 for c in cols] == [v is not None and v > 0 for v in VALUES], "null 과 0 은 막대가 없다 — 값만 막대다"
    assert all(c["w"] <= 24 for c in cols) and all(c["w"] < screen["columns"]["slot"] for c in cols), "막대 사이에 틈"
    assert screen["nullRuns"] == [{"start": 0, "end": 2}, {"start": 9, "end": 9}]


def test_그림은_null_칸을_기록_전_띠로_두고_색은_토큰_클래스로만_칠한다(screen):
    html = screen["chart"]
    assert html.count('class="uc-bar') == sum(1 for v in VALUES if v), "값이 있는 날만 막대"
    assert html.count('class="uc-gap"') == 2, "기록 전 구간 둘(앞 셋 · 가운데 하나)"
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", html), "마크업에 hex 색 — 래칫 밖에서 색이 생긴다"
    assert "<details" in html and "표로 보기" in html and html.count("<tr>") == len(AXIS), "모든 날을 표로도 읽을 수 있다"
    assert "기록 전" in html and "12명" in html


def test_그림_끝_날짜는_해를_넘으면_해까지_적고_기록_전_달은_한_줄로_접는다(screen):
    assert screen["edge"] == [["10-04", "11-02"], ["2025-09-29", "2026-11-02"], ["", ""]]
    fold = screen["fold"]
    assert fold["span"] == ["2025-09", "2025-10"] and [r["month"] for r in fold["rest"]] == ["2025-11", "2025-12"], \
        "앞쪽에 이어진 null 만 접는다 — 가운데 null 은 그대로 둔다"


def test_대화는_날마다_합치고_빠진_날은_0(screen):
    got = dict(zip(AXIS, screen["perDay"], strict=True))
    assert (got["2026-10-21"], got["2026-10-30"], got["2026-10-22"]) == (5, 1, 0)


def test_수_타일은_큰_수를_줄여_보인다(screen):
    assert "12.9K" in screen["tile"] and "챗 턴" in screen["tile"]
