# 심의 주제 고르기(SubjectPicker)를 헤드리스 브라우저에 실제로 올려 고르기 · 찾기 · 보낼 꼴을 본다 — 서버는 띄우지 않는다(가짜 fetch)
"""docs/project-insight-graph M1. 고르기의 상태 동작(과제를 골라야 차수 · 글 · 설계 자료 칸이 열리는가 · '과제 대상이 아님' 이 주제를 비우는가 ·
찾기 결과가 후보에 붙는가 · 찾기 실패를 말하는가 · 이 대화에서 온 key 를 허브 찾기로 다시 보는가 · 비활성 과제는 못 고르는가 · 차수의 원천 값은
고른 해석 리포트에서만 오는가 · 설계 자료 상한)은 타입 검사 · 린트 · node 단위 시험(test_subject_front)으로는 못 본다. 실제 부품을 esbuild 로
묶어 빈 문서 한 장에 올리고 fetch 만 가짜로 바꿔 사람처럼 눌러 본다(test_admin_pages_in_browser 와 같은 꼴). 주소 · 과제 이름은 지어낸 값이다.
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
import { SubjectPicker } from '__FE__/src/components/chat/SubjectPicker';
import { EMPTY_SUBJECT, subjectWire, type SubjectCandidates, type SubjectDraft } from '__FE__/src/components/chat/subject';

function Box({ cands, slot }: { cands: SubjectCandidates; slot: number }) {
  const [v, setV] = useState<SubjectDraft>(EMPTY_SUBJECT);
  (window as unknown as { __wire: Record<number, unknown> }).__wire[slot] = subjectWire(v);
  return <SubjectPicker candidates={cands} value={v} onChange={setV} />;
}
const w = window as unknown as { __wire: Record<number, unknown>; __mount: (c: SubjectCandidates, n: number) => void };
w.__wire = {};
w.__mount = (cands, n) => {
  createRoot(document.getElementById('root')!).render(
    <>{Array.from({ length: n }, (_, i) => <div key={i} className={`slot-${i}`}><Box cands={cands} slot={i} /></div>)}</>);
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

# 가짜 찾기 창구 — 받은 질의를 적고, '실패' 를 담은 질의는 502 로 답한다(포털 AuthError 의 {"detail": …} 꼴). 이 대화의 후보를 다시 보는 질의
# (key 그대로)는 허브 거울처럼 답한다 — '감마 개발' 은 부분 일치 행만(글자 그대로인 행이 없다), '델타 개발' 은 비활성, '느린 과제' 는 늦게 답한다.
_STUB = r"""
(() => {
  window.__calls = [];
  const json = (body, status = 200, delay = 0) =>
    new Promise((ok) => setTimeout(() => ok(new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })), delay));
  const rows = (query, list, delay = 0) => json({ query, tool: 'heaxstep_forge_find_plm_task', count: list.length, rows: list }, 200, delay);
  window.fetch = (url, init = {}) => {
    const u = String(url), body = init.body ? JSON.parse(init.body) : {};
    window.__calls.push({ url: u, method: (init.method || 'GET').toUpperCase(), body });
    if (u === '/agent/deliberate/subject/search') {
      const q = body.query;
      if (q.includes('실패')) return json({ detail: 'heaxstep_forge_find_plm_task: forbidden — 플랫폼 허가가 없다' }, 502);
      if (q.includes('없는')) return json({ query: q, tool: 'x', rows: [], count: 0, why: { cause: 'no_match', message: '맞는 것이 없다' } });
      if (q === '__KEY__') return rows(q, [{ key: '__KEY__', label: '__KEY__', task_code: 'TC-1001', project: '알파 프로젝트', active: true }]);
      if (q === '감마 개발') return rows(q, [{ key: '감마 개발 보강', label: '감마 개발 보강', active: true }]);
      if (q === '델타 개발') return rows(q, [{ key: '델타 개발', label: '델타 개발', active: false }]);
      if (q === '느린 과제') return rows(q, [], 400);
      return rows(q, [{ key: '베타 개발_C1', label: '베타 개발_C1', task_code: 'TC-2001', project: '베타 프로젝트', active: true }]);
    }
    return json({ detail: 'stub: no route ' + u }, 404);
  };
})();
""".replace("__KEY__", KEY)

_DRIVE = r"""
const { createRequire } = require('module');
const path = require('path');
const [FE, OUT, CANDS] = process.argv.slice(2);
const { chromium } = createRequire(path.join(FE, 'package.json'))('@playwright/test');
const cands = JSON.parse(CANDS);

async function open(browser, n = 1) {
  const page = await browser.newPage({ viewport: { width: 1100, height: 900 } });
  page.setDefaultTimeout(10000);
  page.__errors = [];
  page.on('pageerror', (e) => page.__errors.push(String(e)));
  await page.route('http://harness.invalid/**', (r) =>
    r.fulfill({ contentType: 'text/html', body: '<!doctype html><html><body><div id="root"></div></body></html>' }));
  await page.goto('http://harness.invalid/');
  await page.addScriptTag({ path: path.join(OUT, 'stub.js') });
  await page.addScriptTag({ path: path.join(OUT, 'bundle.js') });
  await page.evaluate(([c, k]) => window.__mount(c, k), [cands, n]);
  await page.locator('.cx-subj').first().waitFor();
  return page;
}
const wire = (page, slot = 0) => page.evaluate((s) => window.__wire[s], slot);
const radios = (page) => page.evaluate(() => Array.from(document.querySelectorAll('.slot-0 input[type=radio]')).map((r) => ({
  label: r.closest('label').querySelector('.cx-brief-seat-name').textContent, checked: r.checked, disabled: r.disabled })));
const searched = (page) => page.evaluate(() => window.__calls.filter((c) => c.url === '/agent/deliberate/subject/search').map((c) => c.body.query));
const check = (page) => page.evaluate(() => (document.querySelector('.cx-subj-check') || {}).textContent || '');
const pickRow = (page, name) => page.locator('.slot-0 label', { has: page.locator('.cx-brief-seat-name', { hasText: new RegExp('^' + name + '$') }) })
  .locator('input[type=radio]');

const SCENARIOS = {
  async pick(browser) {
    const page = await open(browser);
    const before = { radios: await radios(page), wire: await wire(page), round_shown: await page.locator('.cx-subj-more').count() };
    await pickRow(page, '__KEY__').check();
    const picked = await wire(page);
    await page.waitForFunction(() => window.__calls.length >= 1);
    await page.waitForTimeout(50);
    const rechecked = { queries: await searched(page), note: await check(page) };
    const options = await page.locator('.cx-subj-more select option').allTextContents();
    await page.locator('.cx-subj-more label', { hasText: '알파 낙하' }).locator('input[type=checkbox]').check();
    const optionsWithReport = await page.locator('.cx-subj-more select option').allTextContents();
    await page.locator('.cx-subj-more label', { hasText: '알파 낙하' }).locator('input[type=checkbox]').uncheck();
    await page.locator('.cx-subj-more select').selectOption('dv1');
    await page.locator('.cx-subj-more input.cx-brief-seatsearch').fill('  1차 메모  ');
    await page.locator('.cx-subj-more input[type=checkbox]').first().check();
    const full = await wire(page);
    await page.locator('label', { hasText: '과제 대상이 아님' }).locator('input[type=radio]').check();
    return { before, picked, rechecked, options, optionsWithReport, full, cleared: await wire(page),
             round_shown_after: await page.locator('.cx-subj-more').count(), errors: page.__errors };
  },
  async recheck(browser) {
    const page = await open(browser);
    await pickRow(page, '감마 개발').check();
    await page.waitForFunction(() => (document.querySelector('.cx-subj-check') || {}).textContent?.includes('글자 그대로 없다'));
    const gamma = { note: await check(page), wire: await wire(page) };
    await pickRow(page, '델타 개발').check();
    await page.waitForFunction(() => (document.querySelector('.cx-subj-check') || {}).textContent?.includes('비활성'));
    const delta = await check(page);
    await pickRow(page, '느린 과제').check();
    await pickRow(page, '__KEY__').check();         // 늦은 답이 오기 전에 다른 것을 골랐다
    await page.waitForTimeout(700);
    const stale = { note: await check(page), wire: await wire(page) };
    const box = page.locator('.cx-subj-search input');
    await box.fill('베타');
    await page.locator('.cx-subj-go').click();
    await page.getByText('베타 개발_C1').waitFor();
    const n = (await searched(page)).length;
    await pickRow(page, '베타 개발_C1').check();
    await page.waitForTimeout(100);
    return { gamma, delta, stale, queries: await searched(page), afterSearchPick: (await searched(page)).length - n, note: await check(page),
             errors: page.__errors };
  },
  async cap(browser) {
    const page = await open(browser);
    await pickRow(page, '__KEY__').check();
    const boxes = page.locator('.cx-subj-more input[type=checkbox]');
    const total = await boxes.count();
    for (let i = 0; i < total; i += 1) {
      if (!(await boxes.nth(i).isDisabled())) await boxes.nth(i).check();
    }
    const states = await page.evaluate(() => Array.from(document.querySelectorAll('.cx-subj-more input[type=checkbox]')).map((b) => [b.checked, b.disabled]));
    const label = await page.locator('.cx-subj-more .cx-subj-field > span').last().textContent();
    return { total, states, label, wire: await wire(page), errors: page.__errors };
  },
  async search(browser) {
    const page = await open(browser);
    const box = page.locator('.cx-subj-search input');
    await box.fill('베타');
    await page.locator('.cx-subj-go').click();
    await page.getByText('베타 개발_C1').waitFor();
    const calls = await page.evaluate(() => window.__calls.map((c) => [c.method, c.url, c.body]));
    const rows = await radios(page);
    await page.locator('label', { hasText: '베타 개발_C1' }).locator('input[type=radio]').check();
    const picked = await wire(page);
    await box.fill('실패하는 과제');
    await box.press('Enter');
    await page.getByText('허브 과제를 찾지 못했다').waitFor();
    const failure = await page.locator('.cx-subj .cx-brief-empty').textContent();
    await box.fill('없는 과제');
    await page.locator('.cx-subj-go').click();
    await page.getByText('맞는 과제가 없다').waitFor();
    return { calls, rows, picked, failure, none: await page.locator('.cx-subj .cx-brief-empty').textContent(), errors: page.__errors };
  },
  async two(browser) {
    const page = await open(browser, 2);
    const names = await page.evaluate(() => [0, 1].map((i) =>
      Array.from(new Set(Array.from(document.querySelectorAll(`.slot-${i} input[type=radio]`)).map((r) => r.name)))));
    await page.locator('.slot-0 label', { hasText: '__KEY__' }).first().locator('input[type=radio]').check();
    return { names, w0: await wire(page, 0), w1: await wire(page, 1), errors: page.__errors };
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
""".replace("__KEY__", KEY)

_CANDS = {"sp": [{"key": KEY, "label": KEY, "taskCode": "TC-1001", "project": "알파 프로젝트", "active": True,
                  "from": "이 대화의 find_plm_task"},
                 {"key": f"{KEY} 보강", "active": False, "from": "이 대화의 find_plm_task"},
                 {"key": "감마 개발", "active": True, "from": "이 대화의 find_plm_task"},
                 {"key": "델타 개발", "active": True, "from": "이 대화의 find_plm_task"},
                 {"key": "느린 과제", "active": True, "from": "이 대화의 find_plm_task"}],
          "artifacts": [{"kind": "mcad", "id": "019a2b3c4d5e6f7a8b9c0d1", "rev": "1a2b3c4d5e6f7a8b", "label": "알파 힌지 CAD",
                         "from": "이 대화의 get_project_meta"},
                        {"kind": "cae", "id": "01HZX3K5Q9V8N7M6P5R4S3T2W1", "rev": "dv2", "label": "알파 낙하", "from": "이 대화의 list_reports"},
                        *({"kind": "ecad", "id": f"abcdef01234567{i:02x}", "rev": "B", "label": f"보드 {i}", "from": "이 대화의 find_job"}
                          for i in range(8))]}


@pytest.fixture(scope="module")
def seen(tmp_path_factory):
    out = tmp_path_factory.mktemp("subject-picker")
    (out / "harness.tsx").write_text(_HARNESS.replace("__FE__", str(FE)), encoding="utf-8")
    for name, text in (("build.cjs", _BUILD), ("stub.js", _STUB), ("drive.cjs", _DRIVE)):
        (out / name).write_text(text, encoding="utf-8")
    r = subprocess.run(["node", "build.cjs", str(FE), str(out)], cwd=str(out), capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, "화면을 묶지 못했다:\n" + r.stdout + r.stderr
    r = subprocess.run(["node", "drive.cjs", str(FE), str(out), json.dumps(_CANDS, ensure_ascii=False)], cwd=str(out),
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
    got = json.loads(r.stdout)
    if "skip" in got:
        pytest.skip("헤드리스 브라우저를 띄우지 못했다(playwright 브라우저 미설치) — " + got["skip"])

    def scenario(name: str) -> dict:
        assert "failed" not in got[name], f"시나리오 {name} 이 끝까지 돌지 못했다:\n{got[name].get('failed')}"
        assert not got[name].get("errors"), f"화면이 예외를 던졌다: {got[name]['errors']}"
        return got[name]
    return scenario


def test_과제를_골라야_차수_글_설계_자료가_열리고_과제_대상이_아님은_주제를_비운다(seen):
    s = seen("pick")
    assert s["before"]["wire"] is None and s["before"]["round_shown"] == 0, "처음에는 주제가 없다(과제 대상이 아닌 질문이 기본)"
    assert [r["checked"] for r in s["before"]["radios"]] == [True, False, False, False, False, False]
    assert [r["label"] for r in s["before"]["radios"]] == ["과제 대상이 아님", KEY, f"{KEY} 보강", "감마 개발", "델타 개발", "느린 과제"], \
        "후보는 받은 행 그대로"
    assert [r["disabled"] for r in s["before"]["radios"]] == [False, False, True, False, False, False], \
        "허브에서 비활성인 과제는 고를 수 없다(서버가 확인하지 않는다 — 반대 검토 11-02)"
    assert s["picked"] == {"sp_task": KEY}, "고른 결과 행의 key 를 그대로 싣는다"
    assert s["rechecked"] == {"queries": [KEY], "note": ""}, "이 대화에서 온 key 는 허브 찾기로 다시 보고, 글자 그대로 있으면 말이 없다"
    assert s["options"][0].startswith("차수 모름") and [o for o in s["options"] if " — " in o] == [s["options"][0]], \
        "리포트를 고르기 전에는 원천 값이 없다"
    assert s["optionsWithReport"][1].startswith("dv2 — 고른 해석 리포트 알파 낙하"), "고른 해석 리포트의 개발 단계가 정본 꼴 목록보다 먼저다"
    assert [o for o in s["options"] if " — " not in o] == ["pre", "dv1", "dv2", "dv3", "dvr", "pv1", "pv2", "pv3", "pvr", "pra", "mp"]
    assert s["full"] == {"sp_task": KEY, "round": "dv1", "text": "1차 메모",
                         "artifacts": [{"kind": "mcad", "id": "019a2b3c4d5e6f7a8b9c0d1", "rev": "1a2b3c4d5e6f7a8b"}]}
    assert s["cleared"] is None and s["round_shown_after"] == 0, "'과제 대상이 아님' 을 고르면 차수 · 글 · 설계 자료도 함께 비운다"


def test_허브_과제_찾기는_그_사람의_찾기_창구로_가고_결과를_후보로_붙이며_실패를_말한다(seen):
    s = seen("search")
    assert s["calls"][0] == ["POST", "/agent/deliberate/subject/search", {"query": "베타"}]
    assert [r["label"] for r in s["rows"]] == ["과제 대상이 아님", KEY, f"{KEY} 보강", "감마 개발", "델타 개발", "느린 과제", "베타 개발_C1"], \
        "찾은 행은 이 대화의 후보 뒤에 붙는다"
    assert s["picked"] == {"sp_task": "베타 개발_C1"}
    assert "허브 과제를 찾지 못했다" in s["failure"] and "forbidden" in s["failure"], "권한 · 도구 실패의 까닭을 그대로 보인다"
    assert "맞는 과제가 없다" in s["none"] and "맞는 것이 없다" in s["none"]


def test_한_화면에_고르기가_둘이어도_라디오가_섞이지_않는다(seen):
    s = seen("two")
    assert len(s["names"][0]) == 1 and len(s["names"][1]) == 1 and s["names"][0] != s["names"][1]
    assert s["w0"] == {"sp_task": KEY} and s["w1"] is None


def test_이_대화에서_온_key_는_고를_때_허브_찾기로_다시_본다(seen):
    """도구 결과의 미리보기는 겹친 공백을 하나로 줄여 적어 그 key 가 허브의 key 와 다를 수 있다(반대 검토 11-02) — 고를 때 허브 찾기로 글자 그대로
    있는지 보고, 없거나 비활성이면 말한다. 늦게 온 답은 그사이 다른 것을 골랐으면 버린다. 찾기에서 온 행은 다시 보지 않는다."""
    s = seen("recheck")
    assert "글자 그대로 없다" in s["gamma"]["note"] and "이름 일부로 찾아" in s["gamma"]["note"]
    assert s["gamma"]["wire"] == {"sp_task": "감마 개발"}, "고른 것은 그대로 둔다 — 서버가 시작 때 다시 확인한다(말만 한다)"
    assert "비활성" in s["delta"]
    assert s["stale"] == {"note": "", "wire": {"sp_task": KEY}}, "늦게 온 '느린 과제' 의 답이 지금 고른 것의 말을 덮지 않는다"
    assert s["queries"][:4] == ["감마 개발", "델타 개발", "느린 과제", KEY] and s["afterSearchPick"] == 0 and s["note"] == ""


def test_설계_자료는_상한까지만_고르고_넘으면_막는다(seen):
    """상한(8건)을 넘는 고르기는 보낼 때 말없이 잘렸다(반대 검토 11-02) — 상한에 닿으면 나머지 칸을 막고 수를 보인다."""
    s = seen("cap")
    assert s["total"] == 10 and [c for c, _d in s["states"]].count(True) == 8
    assert [d for c, d in s["states"] if not c] == [True, True], "고르지 않은 칸은 막힌다"
    assert "8/8" in s["label"] and "8건까지" in s["label"] and len(s["wire"]["artifacts"]) == 8
