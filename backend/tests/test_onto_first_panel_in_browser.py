# '온톨로지 먼저 보기' 칸(OntoFirstPanel)을 헤드리스 브라우저에 올려 켜짐 · 부르기 · 행 고르기 · 근거 꼴 · 못 부른 까닭을 본다 — 서버는 띄우지 않는다(가짜 fetch)
"""docs/ontology-first M4. 칸의 상태 동작(주제 과제가 없으면 꺼짐 · 열 때 그 과제와 의장 틀로 창구를 부름 · 고른 행만 호출 하나에 근거 한 항목 ·
빼면 근거에서 빠짐 · 이웃 행을 고르면 주제 과제 칸이 보이게 함께 골라지고 주제 과제를 빼면 이웃 행도 빠짐 · 부를 수 없을 때 까닭과 다시 보기 · 창구
실패를 '못 물어봄' 으로)은 타입 검사 · 린트로는 못 본다. 실제 부품을 esbuild 로 묶어 빈 문서 한 장에 올리고 fetch 만 가짜로 바꿔 사람처럼 눌러 본다
(test_subject_picker_in_browser 와 같은 꼴). 과제 이름 · id 는 지어낸 값이다.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FE = ROOT / "frontend"

pytestmark = pytest.mark.skipif(
    not shutil.which("node") or not (FE / "node_modules/@playwright/test").exists() or not (FE / "node_modules/vite").exists(),
    reason="node 또는 frontend node_modules(@playwright/test · vite) 가 없다 — 화면을 올려 볼 수 없다",
)

KEY = "알파 개발_C2"

_HARNESS = r"""
import { createRoot } from 'react-dom/client';
import { useState } from 'react';
import { OntoFirstPanel } from '__FE__/src/components/chat/OntoFirstPanel';
import { EMPTY_ONTO, ontoEvidence, type OntoChoice } from '__FE__/src/components/chat/ontoEvidence';

function Box({ spTask, chair }: { spTask: string; chair?: string }) {
  const [c, setC] = useState<OntoChoice>(EMPTY_ONTO);
  (window as unknown as { __choice: OntoChoice }).__choice = c;
  return <OntoFirstPanel spTask={spTask} chair={chair} onChange={setC} />;
}
const w = window as unknown as { __mount: (spTask: string, chair?: string) => void; __ontoEvidence: typeof ontoEvidence };
w.__ontoEvidence = ontoEvidence;
w.__mount = (spTask, chair) => {
  createRoot(document.getElementById('root')!).render(<Box spTask={spTask} chair={chair} />);
};
"""

_BUILD = r"""
const { createRequire } = require('module');
const path = require('path');
const [FE, OUT] = process.argv.slice(2);
const fe = createRequire(path.join(FE, 'package.json'));
const esbuild = createRequire(fe.resolve('vite/package.json'))('esbuild');
esbuild.buildSync({
  entryPoints: [path.join(OUT, 'harness.tsx')], bundle: true, format: 'iife', outfile: path.join(OUT, 'bundle.js'),
  jsx: 'automatic', nodePaths: [path.join(FE, 'node_modules')], logLevel: 'error',
  loader: { '.css': 'empty', '.svg': 'dataurl', '.png': 'dataurl', '.woff2': 'empty', '.woff': 'empty' },
  define: { 'import.meta.env': '{}', 'process.env.NODE_ENV': '"development"' },
});
"""

# 가짜 창구 — 받은 몸을 적고 sp_task 로 답을 고른다(포털 app.agent.onto_preview 의 답 꼴). '읽기' 는 읽기 미확인, '실패' 는 502(AuthError 의 detail 꼴).
_OK = {"state": "ok", "sp_task": KEY, "canonical": {"app": "rootdesigndatahub", "label": "자주검증 Datahub(rootdesign)"},
       "tools": {"resolve": "rootdesigndatahub_object_resolve", "neighbors": "rootdesigndatahub_graph_neighbors"},
       "calls": {"resolve": {"tool": "rootdesigndatahub_object_resolve", "args": {"type_slug": "plm_task", "name": KEY}},
                 "neighbors": {"tool": "rootdesigndatahub_graph_neighbors",
                               "args": {"object_id": "t-1", "depth": 1, "types": ["plm_model", "failure_mode"], "limit": 60}}},
       "anchor": {"id": "t-1", "key": KEY, "label": KEY, "type": "plm_task", "status": "active", "matched_by": "key",
                  "line": f"plm_task · {KEY} · {KEY} · 정본 허브 exact(key) · 상태 active"},
       "rows": [{"id": "n-1", "type": "failure_mode", "type_label": "고장모드", "key": "FM-0012", "label": "힌지 크랙", "rel": "이 과제 → 예측함(predicts)",
                 "line": "고장모드(failure_mode) · FM-0012 · 힌지 크랙 · 이 과제 → 예측함(predicts)"},
                {"id": "n-2", "type": "plm_model", "type_label": "개발모델", "key": "SM-A100", "label": "모델 A100", "rel": "이 과제 ← 과제의 모델(has_task)",
                 "line": "개발모델(plm_model) · SM-A100 · 모델 A100 · 이 과제 ← 과제의 모델(has_task)"}],
       "total": 5, "shown": 2, "hub_truncated": False, "note": "고른 행만 심의의 원천 근거로 들어간다."}

_STUB = r"""
(() => {
  window.__calls = [];
  const json = (body, status = 200) => Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }));
  window.fetch = (url, init = {}) => {
    const u = String(url), body = init.body ? JSON.parse(init.body) : {};
    window.__calls.push({ url: u, method: (init.method || 'GET').toUpperCase(), body });
    if (u === '/agent/deliberate/onto-preview') {
      if (body.sp_task === '읽기') return json({ state: 'unavailable', why: '이 박스에서 읽기로 확인되지 않았다 — rootdesigndatahub_object_resolve', note: 'n' });
      if (body.sp_task === '실패') return json({ detail: 'rootdesigndatahub_object_resolve: forbidden — 플랫폼 허가가 없다' }, 502);
      return json(__OK__);
    }
    return json({ detail: 'stub: no route ' + u }, 404);
  };
})();
""".replace("__OK__", json.dumps(_OK, ensure_ascii=False))

_DRIVE = r"""
const { createRequire } = require('module');
const path = require('path');
const [FE, OUT] = process.argv.slice(2);
const { chromium } = createRequire(path.join(FE, 'package.json'))('@playwright/test');

async function open(browser, spTask, chair) {
  const page = await browser.newPage({ viewport: { width: 1000, height: 900 } });
  page.setDefaultTimeout(10000);
  page.__errors = [];
  page.on('pageerror', (e) => page.__errors.push(String(e)));
  await page.route('http://harness.invalid/**', (r) =>
    r.fulfill({ contentType: 'text/html', body: '<!doctype html><html><body><div id="root"></div></body></html>' }));
  await page.goto('http://harness.invalid/');
  await page.addScriptTag({ path: path.join(OUT, 'stub.js') });
  await page.addScriptTag({ path: path.join(OUT, 'bundle.js') });
  await page.evaluate(([k, c]) => window.__mount(k, c), [spTask, chair]);
  await page.locator('.vf-open, .vf').first().waitFor();
  return page;
}
const choice = (page) => page.evaluate(() => window.__choice);
const calls = (page) => page.evaluate(() => window.__calls.map((c) => [c.method, c.url, c.body]));

const SCENARIOS = {
  async off(browser) {
    const page = await open(browser, '  ');
    const btn = page.locator('.vf-open');
    return { disabled: await btn.isDisabled(), text: await btn.textContent(), calls: await calls(page), errors: page.__errors };
  },
  async pick(browser) {
    const page = await open(browser, '__KEY__', 'diagnosis');
    const closedText = await page.locator('.vf-open').textContent();
    await page.locator('.vf-open').click();
    await page.getByText('힌지 크랙').waitFor();
    const before = await choice(page);
    const boxes = page.locator('.vf input[type=checkbox]');
    const n = await boxes.count();
    const ticks = async () => [await boxes.nth(0).isChecked(), await boxes.nth(1).isChecked(), await boxes.nth(2).isChecked()];
    // 부모에게 알리는 것은 효과(useEffect)라 그린 뒤에 온다 — 그 값이 설 때까지 기다린다
    const until = (rows, anchor) => page.waitForFunction(([r, a]) => window.__choice.rows === r && window.__choice.anchor === a, [rows, anchor]);
    await boxes.nth(2).check();                 // 둘째 이웃(개발모델)만 — 주제 과제 칸은 건드리지 않는다
    await until(1, true);                       // 주제 과제 칸이 보이게 함께 골라진다(관계 글 '이 과제' · object_id 가 그 과제다)
    const auto = { ticks: await ticks(), choice: await choice(page) };
    await boxes.nth(1).check();                 // 첫째 이웃(고장모드)
    await until(2, true);
    const all = await choice(page);
    await boxes.nth(1).uncheck();
    await until(1, true);
    const less = await choice(page);
    await boxes.nth(0).uncheck();               // 이웃을 고른 채 주제 과제를 뺀다 — 고른 이웃 행도 함께 빠진다
    await until(0, false);
    const cascade = { ticks: await ticks(), choice: await choice(page) };
    await boxes.nth(0).check();                 // 주제 과제만
    await until(0, true);
    const anchorOnly = await choice(page);
    await boxes.nth(0).uncheck();
    await until(0, false);
    const none = await choice(page);
    const hints = await page.locator('.vf-hint').allTextContents();
    return { closedText, n, before, auto, all, less, cascade, anchorOnly, none, hints, calls: await calls(page), errors: page.__errors };
  },
  async pure(browser) {
    // 근거 짓기만 — 주제 과제를 고르지 않은 채 이웃 행을 넘겨도 주제 과제의 key · 허브 id 를 싣지 않는다(반대 검토 11-02 재현을 뒤집음)
    const page = await open(browser, '  ');
    const ok = __OK__;
    const out = await page.evaluate((p) => ({
      neighborsOnly: window.__ontoEvidence(p, false, ['n-1']),
      both: window.__ontoEvidence(p, true, ['n-1']).map((e) => e.tool),
    }), ok);
    return { ...out, errors: page.__errors };
  },
  async unavailable(browser) {
    const page = await open(browser, '읽기');
    await page.locator('.vf-open').click();
    await page.locator('.vf-warn').waitFor();
    const warn = await page.locator('.vf-warn').textContent();
    const boxes = await page.locator('.vf input[type=checkbox]').count();
    await page.getByRole('button', { name: '다시 보기' }).click();
    await page.waitForFunction(() => window.__calls.length >= 2);
    return { warn, boxes, choice: await choice(page), n: (await calls(page)).length, errors: page.__errors };
  },
  async failed(browser) {
    const page = await open(browser, '실패');
    await page.locator('.vf-open').click();
    await page.locator('.vf-warn').waitFor();
    return { warn: await page.locator('.vf-warn').textContent(), choice: await choice(page), errors: page.__errors };
  },
};

(async () => {
  let browser;
  try { browser = await chromium.launch(); } catch (e) { process.stdout.write(JSON.stringify({ skip: String(e).slice(0, 300) })); return; }
  const out = {};
  try {
    for (const [name, run] of Object.entries(SCENARIOS)) {
      try { out[name] = await run(browser); } catch (e) { out[name] = { failed: String((e && e.stack) || e).slice(0, 1500) }; }
    }
  } finally { await browser.close(); }
  process.stdout.write(JSON.stringify(out));
})().catch((e) => { process.stderr.write(String((e && e.stack) || e)); process.exit(1); });
""".replace("__KEY__", KEY).replace("__OK__", json.dumps(_OK, ensure_ascii=False))


@pytest.fixture(scope="module")
def seen(tmp_path_factory):
    out = tmp_path_factory.mktemp("onto-panel")
    (out / "harness.tsx").write_text(_HARNESS.replace("__FE__", str(FE)), encoding="utf-8")
    for name, text in (("build.cjs", _BUILD), ("stub.js", _STUB), ("drive.cjs", _DRIVE)):
        (out / name).write_text(text, encoding="utf-8")
    r = subprocess.run(["node", "build.cjs", str(FE), str(out)], cwd=str(out), capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, "화면을 묶지 못했다:\n" + r.stdout + r.stderr
    r = subprocess.run(["node", "drive.cjs", str(FE), str(out)], cwd=str(out), capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
    got = json.loads(r.stdout)
    if "skip" in got:
        pytest.skip("헤드리스 브라우저를 띄우지 못했다(playwright 브라우저 미설치) — " + got["skip"])

    def scenario(name: str) -> dict:
        assert "failed" not in got[name], f"시나리오 {name} 이 끝까지 돌지 못했다:\n{got[name].get('failed')}"
        assert not got[name].get("errors"), f"화면이 예외를 던졌다: {got[name]['errors']}"
        return got[name]
    return scenario


def test_주제_과제가_없으면_꺼져_있고_부르지_않는다(seen):
    s = seen("off")
    assert s["disabled"] is True and "심의 주제에서 과제를 고르면 켜집니다" in s["text"] and s["calls"] == []


def test_열면_그_과제와_의장_틀로_부르고_고른_행만_호출_하나에_근거_한_항목이다(seen):
    s = seen("pick")
    assert KEY in s["closedText"]
    assert s["calls"] == [["POST", "/agent/deliberate/onto-preview", {"sp_task": KEY, "chair_template": "diagnosis"}]]
    assert s["n"] == 3, "주제 과제 한 칸 + 이웃 두 행"
    assert s["before"] == {"evidence": [], "rows": 0, "anchor": False}, "고르기 전에는 근거가 없다"
    # 이웃 행만 골라도 주제 과제의 key · 허브 id(object_id)가 근거에 실린다 — 말없이 나가지 않게 주제 과제 칸이 보이게 함께 골라진다(반대 검토 11-02 — OF-29)
    assert s["auto"]["ticks"] == [True, False, True], "이웃을 고르면 주제 과제 칸이 함께 골라져 보인다"
    auto = s["auto"]["choice"]
    assert auto["anchor"] is True and [e["tool"] for e in auto["evidence"]] == ["rootdesigndatahub_object_resolve", "rootdesigndatahub_graph_neighbors"]
    assert any("주제 과제" in h and "함께" in h for h in s["hints"]), ("함께 골라지는 까닭을 칸에 적는다", s["hints"])
    ev = s["all"]["evidence"]
    assert [e["tool"] for e in ev] == ["rootdesigndatahub_object_resolve", "rootdesigndatahub_graph_neighbors"], "호출 하나에 한 항목 — 행마다가 아니다"
    assert all(e["source"] == "온톨로지 먼저 · 자주검증 Datahub(rootdesign)" for e in ev)
    assert ev[0]["args"] == f"type_slug=plm_task · name={KEY}" and ev[0]["result"].startswith("[포털이 줄인 행 — 도구 원문이 아니다]")
    assert ev[1]["args"] == "object_id=t-1 · depth=1 · types=plm_model,failure_mode · limit=60"
    lines = ev[1]["result"].split("\n")
    assert "고른 2행(보인 2 · 전체 5)" in lines[0] and lines[1:] == [_OK["rows"][0]["line"], _OK["rows"][1]["line"]], "화면 차례대로"
    assert s["all"]["rows"] == 2 and s["all"]["anchor"] is True
    less = s["less"]["evidence"]
    assert [e["tool"] for e in less] == ["rootdesigndatahub_object_resolve", "rootdesigndatahub_graph_neighbors"]
    assert less[1]["result"].split("\n")[1:] == [_OK["rows"][1]["line"]], "뺀 행은 근거에서 빠진다"
    assert s["cascade"]["ticks"] == [False, False, False], "이웃을 고른 채 주제 과제를 빼면 이웃 행도 함께 빠진다(보인다)"
    assert s["cascade"]["choice"] == {"evidence": [], "rows": 0, "anchor": False}, "주제 과제 없이 이웃 행만 나가지 않는다"
    assert [e["tool"] for e in s["anchorOnly"]["evidence"]] == ["rootdesigndatahub_object_resolve"], "주제 과제만 — 풀이 항목 하나"
    assert s["none"] == {"evidence": [], "rows": 0, "anchor": False}
    assert any("전체 5행 가운데 2행만" in h for h in s["hints"]) and any("원천 근거" in h for h in s["hints"])


def test_주제_과제를_고르지_않으면_이웃_행을_넘겨도_주제_과제의_key_와_허브_id_를_싣지_않는다(seen):
    """근거 짓기(ontoEvidence)만 — 이웃 호출의 인자(object_id — 허브 id)와 머리(「key」)가 주제 과제를 가리킨다. 화면은 이웃을 고르면 주제 과제를 함께
    고르지만, 짓기도 고르지 않은 주제 과제를 싣지 않는다(반대 검토 11-02 재현을 뒤집음 — OF-29)."""
    s = seen("pure")
    assert s["neighborsOnly"] == [], s["neighborsOnly"]
    assert s["both"] == ["rootdesigndatahub_object_resolve", "rootdesigndatahub_graph_neighbors"]


def test_부를_수_없으면_까닭과_다시_보기만_있고_근거가_없다(seen):
    s = seen("unavailable")
    assert "이 박스에서 부를 수 없습니다" in s["warn"] and "읽기로 확인되지 않았다" in s["warn"]
    assert s["boxes"] == 0 and s["choice"]["evidence"] == [] and s["n"] == 2


def test_창구가_실패하면_없음이_아니라_못_물어봄으로_말한다(seen):
    s = seen("failed")
    assert "'없음' 이 아니라 '못 물어봄'" in s["warn"] and "forbidden" in s["warn"] and s["choice"]["evidence"] == []
