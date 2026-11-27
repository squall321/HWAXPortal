# 절차 페이지의 「자동」 탭(자동 파이프라인)을 헤드리스 브라우저에 실제로 올려 — 권한 · 꺼짐 안내 · 검증 오류 · 자동 켜기 확인 · 승인 · 취소 · 판정 글자 · 대체됨을 본다(docs/auto-pipeline)
"""왜 — 이 화면의 위험은 사람이 누르는 두 단추다. 「켜기」(stage auto)와 「제출 승인」은 클러스터 해석을 저절로 · 곧바로 낸다. 확인을 거치지 않고 POST 가
나가거나, 승인 단추가 승인 대기가 아닌 실행에 뜨면 타입 검사 · 린트로는 안 잡힌다. 그래서 실제 ProceduresPage 를 esbuild 로 묶어 빈 문서에 올리고 fetch 만
가짜 창구(portal-api.md §6 꼴)로 바꿔 사람처럼 눌러 본다(test_admin_pages_in_browser 와 같은 길). 서버도 네트워크도 없다.

창구 문서는 목록의 봉투 · 상세의 묶음을 정하지 않았다. 가짜는 일부러 두 꼴을 섞는다 — 규칙 목록은 {rules: [...]}, 단계 원장 칸은 check_json(글) · result(객체),
현황판은 열(columns)을 주지 않는다(화면이 규칙 스펙에서 열을 짓는다). 주소 · 과제 key 는 지어낸 값이다.
"""
import json
import subprocess

import pytest
from tests.test_admin_pages_in_browser import _BUILD, FE, pytestmark  # noqa: F401 — 같은 도구가 없으면 같이 건너뛴다

_HARNESS = r"""
import { createRoot } from 'react-dom/client';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { AuthContext } from '__FE__/src/auth/AuthContext';
import { ProceduresProvider } from '__FE__/src/state/ProceduresContext';
import ProceduresPage from '__FE__/src/pages/procedures/ProceduresPage';

function Loc() {
  const l = useLocation();
  return <pre id="loc">{l.pathname + l.search}</pre>;
}

(window as unknown as { __mount: (url: string, ents: string[]) => void }).__mount = (url, ents) => {
  const user = { subject: 'u1@corp.example', email: 'u1@corp.example', display_name: 'U', groups: [], entitlements: ents };
  createRoot(document.getElementById('root')!).render(
    <AuthContext.Provider
      value={{ user, status: 'authenticated', login: () => undefined, logout: async () => undefined, refresh: async () => undefined }}
    >
      <MemoryRouter initialEntries={[url]}>
        <Loc />
        <Routes>
          <Route path="/procedures/*" element={<ProceduresProvider><ProceduresPage /></ProceduresProvider>} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
};
"""

# 가짜 창구 — __health · __validate 는 시나리오가 심는다. __calls 는 받은 요청(쓰기 판정은 여기서 본다).
_STUB = r"""
(() => {
  window.__calls = [];
  window.__health = { enabled: true, how_to_enable: null, engine: { running: true, last_tick: 1764200000, last_error: null },
    sources: [{ app: 'step_forge', cursor_at: '2026-11-27T01:02:03Z', last_error: null }], ra: { configured: true, board: 'sys-autopipe' },
    counts: { rules: 3, subjects: 4 } };
  window.__validate = { ok: true, errors: [], warnings: [] };
  const STEPS = [{ id: 'thermal', kind: 'analysis', app: 'thermal_shock', profile: 'default' },
    { id: 'drop', kind: 'analysis', app: 'kooremapper', profile: 'fullangle-26' },
    { id: 'summary', kind: 'report', report: 'summary', needs: ['thermal', 'drop'] }];
  const spec = (title, stage) => ({ title, stage, scope: { all_projects: true, exclude: [] }, trigger: { ready_when: ['step_forge.parsed'], quiet_s: 1800 },
    steps: STEPS, limits: { max_concurrent: 2 } });
  window.__rules = {
    'r-auto': { id: 'r-auto', title: '자동 규칙', enabled: false, latest_version: 2, spec: spec('자동 규칙', 'auto') },
    'r-shadow': { id: 'r-shadow', title: '그림자 규칙', enabled: false, latest_version: 1, spec: spec('그림자 규칙', 'shadow') },
    'r-live': { id: 'r-live', title: '켜진 그림자 규칙', enabled: true, latest_version: 1, spec: spec('켜진 그림자 규칙', 'shadow') },
  };
  const row = (r) => ({ id: r.id, title: r.title, enabled: r.enabled, latest_version: r.latest_version, stage: r.spec.stage });
  const BOARD = { rows: [
    { project: 'P-100', revision: 'EVT2', run_id: 'run-done', run_state: 'done', superseded_by: null,
      steps: { thermal: { state: 'done', verdict: 'pass' }, drop: { state: 'done', verdict: 'fail' }, summary: { state: 'done', verdict: null } } },
    { project: 'P-100', revision: 'EVT1', run_id: 'run-sup', run_state: 'superseded', superseded_by: 'run-done',
      steps: { thermal: { state: 'done', verdict: 'marginal' }, drop: { state: 'cancelled' }, summary: { state: 'cancelled' } } },
    { project: 'P-300', revision: 'PVT', run_id: 'run-run', run_state: 'running', superseded_by: null,
      steps: { thermal: { state: 'done', verdict: 'unknown' }, drop: { state: 'blocked' } } },
  ] };
  const run = (id, state, stage, extra = {}) => ({ id, rule_id: 'r-auto', rule_title: '자동 규칙', version_no: 2, project: 'P-100', revision: 'EVT2',
    fingerprint: 'ab'.repeat(32), stage, state, superseded_by: null, reason: null, created_at: 1764200000, ended_at: null, ...extra });
  window.__runs = {
    'run-done': { run: run('run-done', 'done', 'auto', { ended_at: '2026-11-27T01:02:03Z' }), events: [
        { id: 1, at: 1764200000, kind: 'run_created', detail_json: JSON.stringify({ by: 'engine' }) },
        { id: 2, at: 1764200050, kind: 'step_done', detail: { step: 'drop' } }],
      steps: [
        { step_id: 'thermal', kind: 'analysis', state: 'done', run_ref: 'ts-1', started_at: 1764200100, ended_at: 1764203600, verdict: 'pass',
          check_json: JSON.stringify({ ready: true, missing: [], inputs: [{ kind: 'ecad_board', ref: 'b-1', sha256: 'f'.repeat(64) }] }),
          result_json: JSON.stringify({ verdict: 'pass', profile: 'default', app_version: 'abcd1234',
            metrics: [{ name: 'solder_sed_max', label: '솔더 SED 최대', unit: 'MJ/m3', value: 0.82, limit: 1.0, limit_source: '사내 기준 A', verdict: 'pass' },
                      { name: 'warpage_max', unit: 'mm', value: 0.31, limit: null, verdict: 'unknown' }],
            figures: [{ ref: 'fig-1', caption: 'SED 분포 — 코너 볼' }], artifacts: [{ kind: 'd3plot', location: '/data/run/x' }],
            notes: ['기준이 없는 항목은 모름으로 둔다'] }) },
        // 동기 앱 — 제출 응답에서 곧바로 끝났다(시작 시각 · 도는 중을 거치지 않음)
        { step_id: 'drop', kind: 'analysis', state: 'done', run_ref: 'kr-9', verdict: 'fail',
          result: { verdict: 'fail', metrics: [{ name: 'g_peak', label: '최대 가속도', unit: 'g', value: 1500, limit: 1200, verdict: 'fail' }] } },
        { step_id: 'summary', kind: 'report', state: 'done' }] },
    'run-await': { run: run('run-await', 'awaiting_approval', 'approve', { project: 'P-200', revision: 'DV' }), events: [],
      spec: spec('자동 규칙', 'approve'),
      steps: [{ step_id: 'thermal', kind: 'analysis', state: 'ready', check: { ready: true, missing: [], inputs: [] } },
              { step_id: 'drop', kind: 'analysis', state: 'ready', check: { ready: true, missing: [], inputs: [] } },
              { step_id: 'summary', kind: 'report', state: 'pending' }] },
    'run-run': { run: run('run-run', 'running', 'auto', { project: 'P-300', revision: 'PVT' }), events: [],
      steps: [{ step_id: 'thermal', kind: 'analysis', state: 'done', verdict: 'unknown' },
              { step_id: 'drop', kind: 'analysis', state: 'blocked', check: { ready: false, missing: [
                  { kind: 'human_input', why: '패키지 종류를 고르세요' }, { kind: 'revision' }, { kind: 'infra', why: 'stcx 공유 볼륨 없음' },
                  { kind: 'ecad_board', why: '보드 파일 없음' }] } },
              { step_id: 'summary', kind: 'report', state: 'pending' }] },
    'run-sup': { run: run('run-sup', 'superseded', 'auto', { revision: 'EVT1', superseded_by: 'run-done' }), events: [],
      steps: [{ step_id: 'thermal', kind: 'analysis', state: 'done', verdict: 'marginal' }, { step_id: 'drop', kind: 'analysis', state: 'cancelled' }] },
    'run-planned': { run: run('run-planned', 'planned', 'shadow'), events: [], steps: [{ step_id: 'thermal', kind: 'analysis', state: 'ready' }] },
  };
  const SUBJECTS = { subjects: [
    { project: 'P-100', revision: 'EVT2', state: 'ready', block_reason: null, last_change: 1764200000 },
    { project: null, revision: 'EVT1', state: 'blocked', block_reason: 'project_key', last_change: 1764200000 },
    { project: 'P-400', revision: 'DV', state: 'blocked', block_reason: 'human_input: 패키지 종류', last_change: 1764200000 },
    { project: 'P-500', revision: null, state: 'blocked', block_reason: 'revision', last_change: 1764200000 },
    { project: 'P-600', revision: 'EVT1', state: 'blocked', block_reason: 'weird_word', last_change: 1764200000 },
    { project: 'P-700', revision: 'EVT1', state: 'waiting_quiet', block_reason: null, last_change: 1764200000 }] };
  const json = (body, status = 200) =>
    Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }));
  window.fetch = (url, init = {}) => {
    const u = decodeURIComponent(String(url)), method = (init.method || 'GET').toUpperCase();
    const body = init.body ? JSON.parse(init.body) : null;
    window.__calls.push({ key: `${method} ${u}`, body });
    let m;
    if (u === '/autopipe-api/health') return json(window.__health);
    if (u === '/autopipe-api/rules' && method === 'GET') return json({ rules: Object.values(window.__rules).map(row) });
    if (u === '/autopipe-api/rules' && method === 'POST') return json({ id: 'r-new', version_no: 1 }, 201);
    if (u === '/autopipe-api/validate') return json(window.__validate);
    if ((m = u.match(/^\/autopipe-api\/rules\/([^/]+)$/))) {
      const r = window.__rules[m[1]];
      if (!r) return json({ detail: '규칙이 없다' }, 404);
      return json({ rule: row(r), version: { version_no: r.latest_version, spec: r.spec, author: 'u1@corp.example', created_at: 1764200000 },
                    versions: [{ version_no: r.latest_version, spec: r.spec, author: 'u1@corp.example', created_at: 1764200000 }] });
    }
    if ((m = u.match(/^\/autopipe-api\/rules\/([^/]+)\/enabled$/))) { window.__rules[m[1]].enabled = body.enabled; return json({ ok: true }); }
    if ((m = u.match(/^\/autopipe-api\/rules\/([^/]+)\/versions$/))) {
      const r = window.__rules[m[1]]; r.latest_version += 1; r.spec = body.spec; return json({ id: r.id, version_no: r.latest_version }, 201);
    }
    if (u.startsWith('/autopipe-api/board?')) return json(BOARD);
    if (u.startsWith('/autopipe-api/subjects?')) return json(SUBJECTS);
    if ((m = u.match(/^\/autopipe-api\/runs\/([^/?]+)\/report\?step=(.+)$/)))
      return json({ markdown: '## 종합 판정\n\n| 해석 | 판정 |\n|---|---|\n| thermal | 합 |\n| drop | 부 |\n\n낙하가 **기준을 넘었다**.' });
    if ((m = u.match(/^\/autopipe-api\/runs\/([^/]+)\/approve$/))) { window.__runs[m[1]].run.state = 'running'; return json({ ok: true }); }
    if ((m = u.match(/^\/autopipe-api\/runs\/([^/]+)\/cancel$/))) {
      window.__runs[m[1]].run.state = 'cancelled';
      return json({ ok: true, message: '도는 단계 1개는 앱에 취소가 없어 끝까지 둡니다.' });
    }
    if ((m = u.match(/^\/autopipe-api\/runs\/([^/]+)$/))) return window.__runs[m[1]] ? json(window.__runs[m[1]]) : json({ detail: '실행이 없다' }, 404);
    if (u.startsWith('/routines-api/routines')) return json({ count: 0, routines: [] });
    return json({ detail: 'stub: no route ' + u }, 404);
  };
})();
"""

_DRIVE = r"""
const { createRequire } = require('module');
const path = require('path');
const [FE, OUT] = process.argv.slice(2);
const { chromium } = createRequire(path.join(FE, 'package.json'))('@playwright/test');

async function open(browser, url, { ents = ['feat:auto-pipeline'], seed = '', dialog = 'accept' } = {}) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  page.setDefaultTimeout(10000);
  page.__dialogs = [];
  page.on('dialog', (d) => { page.__dialogs.push(d.message()); return dialog === 'accept' ? d.accept() : d.dismiss(); });
  page.__errors = [];
  page.on('pageerror', (e) => page.__errors.push(String(e)));
  // 가로챈 주소로 빈 문서를 준다 — about:blank 에서는 document.cookie 가 막혀 apiFetch 의 CSRF 읽기가 던진다
  await page.route('http://harness.invalid/**', (r) =>
    r.fulfill({ contentType: 'text/html', body: '<!doctype html><html><body><div id="root"></div></body></html>' }));
  await page.goto('http://harness.invalid/');
  await page.addScriptTag({ path: path.join(OUT, 'stub.js') });
  if (seed) await page.evaluate(seed);
  await page.addScriptTag({ path: path.join(OUT, 'bundle.js') });
  await page.evaluate(([u, e]) => window.__mount(u, e), [url, ents]);
  return page;
}
const posts = (page, tail) => page.evaluate((t) => window.__calls.filter((c) => c.key.startsWith('POST ') && c.key.endsWith(t)).map((c) => c.body), tail);
const loc = (page) => page.evaluate(() => document.getElementById('loc').textContent);
const tabs = (page) => page.evaluate(() => Array.from(document.querySelectorAll('.pr-tab')).map((a) => a.textContent));
const buttons = (page) => page.evaluate(() => Array.from(document.querySelectorAll('#root button')).map((b) => b.textContent.trim()));
const health = (page) => page.evaluate(() => document.querySelector('[aria-label="자동 파이프라인 상태"]').innerText);

const SCENARIOS = {
  // 탭은 feat:auto-pipeline 이 있는 사람에게만 — 그 키만 있으면 절차 첫 화면이 자동 탭으로 간다
  async tabs(browser) {
    const out = { errors: [] };
    const routinesOnly = await open(browser, '/procedures/routines', { ents: ['feat:routines'] });
    await routinesOnly.locator('.pr-tab').first().waitFor();
    await routinesOnly.waitForTimeout(150);
    out.routines_only = { tabs: await tabs(routinesOnly), autopipe_calls: await routinesOnly.evaluate(() => window.__calls.filter((c) => c.key.includes('/autopipe-api')).length) };
    const autoOnly = await open(browser, '/procedures', { ents: ['feat:auto-pipeline'] });
    await autoOnly.locator('[aria-label="자동 파이프라인 상태"]').waitFor();
    out.auto_only = { tabs: await tabs(autoOnly), loc: await loc(autoOnly) };
    const both = await open(browser, '/procedures/auto', { ents: ['feat:procedures', 'feat:routines', 'feat:auto-pipeline'] });
    await both.locator('[aria-label="자동 파이프라인 상태"]').waitFor();
    out.both = { tabs: await tabs(both) };
    // 탭 없는 사람이 주소로 들어와도 화면이 서지 않는다(백엔드도 막는다)
    const direct = await open(browser, '/procedures/auto', { ents: ['feat:routines'] });
    await direct.locator('.pr-tab').first().waitFor();
    await direct.waitForTimeout(150);
    out.direct = { health: await direct.locator('[aria-label="자동 파이프라인 상태"]').count() };
    out.errors.push(...routinesOnly.__errors, ...autoOnly.__errors, ...both.__errors, ...direct.__errors);
    return out;
  },
  async off(browser) {
    const page = await open(browser, '/procedures/auto', { seed: `window.__health = { enabled: false,
      how_to_enable: 'infra/.env 에 AUTO_PIPELINE_ENABLED=1 을 적고 포털을 다시 띄운다', engine: { running: false, last_tick: null, last_error: null },
      sources: [{ app: 'step_forge', cursor_at: null, last_error: 'auto_changes 가 없다' }], ra: { configured: false, board: null }, counts: {} }` });
    await page.getByText('꺼져 있습니다').waitFor();
    const off = await health(page);
    const on = await open(browser, '/procedures/auto');
    await on.locator('[aria-label="자동 파이프라인 상태"]').waitFor();
    return { off, on: await health(on), errors: [...page.__errors, ...on.__errors] };
  },
  async validate(browser) {
    const page = await open(browser, '/procedures/auto/rules/new', { seed: `window.__validate = { ok: false,
      errors: [{ path: 'steps[1].id', msg: 'id 가 겹친다 — thermal' }, '순환이 있다 — summary → drop → summary'],
      warnings: ['night_only 가 비었다'] }` });
    await page.getByRole('button', { name: '검증' }).click();
    await page.locator('[aria-label="검증 결과"]').waitFor();
    const seen = await page.evaluate(() => {
      const box = document.querySelector('[aria-label="검증 결과"]');
      return { role: box.getAttribute('role'), text: box.innerText,
               errors: Array.from(box.querySelectorAll('.ap-errors li')).map((li) => li.textContent),
               warnings: Array.from(box.querySelectorAll('.ap-warnings li')).map((li) => li.textContent) };
    });
    const sent = await posts(page, '/validate');
    await page.locator('textarea[aria-label="규칙 스펙 JSON"]').fill('{ "title": "깨진", ');
    await page.getByRole('button', { name: '검증' }).click();
    await page.getByText('JSON 꼴이 아닙니다').waitFor();
    return { seen, sent, after_bad_json: (await posts(page, '/validate')).length, errors: page.__errors };
  },
  // stage auto 규칙 켜기는 확인 한 번 — 취소하면 POST 가 나가지 않는다. 그림자 규칙은 묻지 않는다.
  async enable(browser) {
    const out = { errors: [] };
    for (const [name, rule, dialog] of [['auto_dismiss', 'r-auto', 'dismiss'], ['auto_accept', 'r-auto', 'accept'], ['shadow', 'r-shadow', 'accept']]) {
      const page = await open(browser, `/procedures/auto/rules/${rule}`, { dialog });
      await page.getByRole('button', { name: '켜기' }).click();
      if (dialog === 'accept') await page.getByRole('button', { name: '끄기' }).waitFor();
      else await page.waitForTimeout(200);
      out[name] = { asked: [...page.__dialogs], sent: await posts(page, '/enabled'),
                    chip: await page.evaluate(() => document.querySelector('[aria-label="규칙 정보"] .ap-chip').textContent) };
      out.errors.push(...page.__errors);
    }
    // 켜진 규칙을 「자동 제출」로 올리는 저장도 같은 확인을 거친다
    for (const [name, dialog] of [['save_auto_dismiss', 'dismiss'], ['save_auto_accept', 'accept']]) {
      const page = await open(browser, '/procedures/auto/rules/r-live', { dialog });
      const box = page.locator('textarea[aria-label="규칙 스펙 JSON"]');
      await box.waitFor();
      await box.fill((await box.inputValue()).replace('"stage": "shadow"', '"stage": "auto"'));
      await page.getByRole('button', { name: '새 판으로 저장' }).click();
      if (dialog === 'accept') await page.getByText('판 2 으로 저장했습니다').waitFor();
      else await page.waitForTimeout(200);
      out[name] = { asked: [...page.__dialogs], sent: (await posts(page, '/versions')).map((b) => b.spec.stage) };
      out.errors.push(...page.__errors);
    }
    return out;
  },
  async board(browser) {
    const page = await open(browser, '/procedures/auto?rule=r-auto');
    await page.locator('.ap-board tbody tr').first().waitFor();
    const seen = await page.evaluate(() => ({
      heads: Array.from(document.querySelectorAll('.ap-board thead th')).map((th) => th.childNodes[0].textContent),
      rows: Array.from(document.querySelectorAll('.ap-board tbody tr')).map((tr) => ({
        superseded: tr.classList.contains('ap-superseded'), cells: Array.from(tr.querySelectorAll('td')).map((td) => td.innerText.replace(/\s+/g, ' ').trim()) })),
      subjects: Array.from(document.querySelectorAll('.ap-subjects tbody tr')).map((tr) => Array.from(tr.querySelectorAll('td')).map((td) => td.innerText.trim())),
      rules: Array.from(document.querySelectorAll('.ap-rule')).map((li) => li.innerText.replace(/\s+/g, ' ').trim()),
    }));
    await page.locator('.ap-board tbody tr').first().locator('td').nth(1).click();
    await page.locator('[aria-label="실행"]').waitFor();
    return { ...seen, after_click: await loc(page), errors: page.__errors };
  },
  // 승인 단추는 awaiting_approval 에만, 취소 단추는 끝나지 않은 실행에만 — 둘 다 확인 뒤에만 POST
  async approve_cancel(browser) {
    const out = { errors: [], buttons: {} };
    for (const id of ['run-await', 'run-run', 'run-done', 'run-sup', 'run-planned']) {
      const page = await open(browser, `/procedures/auto/runs/${id}`);
      await page.locator('[aria-label="실행"]').waitFor();
      out.buttons[id] = await buttons(page);
      out.errors.push(...page.__errors);
    }
    for (const [name, dialog] of [['approve_dismiss', 'dismiss'], ['approve_accept', 'accept']]) {
      const page = await open(browser, '/procedures/auto/runs/run-await', { dialog });
      await page.getByRole('button', { name: '제출 승인' }).click();
      if (dialog === 'accept') await page.getByText('승인했습니다').waitFor();
      else await page.waitForTimeout(200);
      out[name] = { asked: [...page.__dialogs], sent: (await posts(page, '/approve')).length, buttons: await buttons(page) };
      out.errors.push(...page.__errors);
    }
    for (const [name, dialog] of [['cancel_dismiss', 'dismiss'], ['cancel_accept', 'accept']]) {
      const page = await open(browser, '/procedures/auto/runs/run-run', { dialog });
      await page.getByRole('button', { name: '취소' }).click();
      if (dialog === 'accept') await page.getByText('끝까지 둡니다').waitFor();
      else await page.waitForTimeout(200);
      out[name] = { asked: [...page.__dialogs], sent: (await posts(page, '/cancel')).length,
                    status: await page.evaluate(() => Array.from(document.querySelectorAll('[role=status]')).map((s) => s.textContent).join(' | ')) };
      out.errors.push(...page.__errors);
    }
    return out;
  },
  async detail(browser) {
    const page = await open(browser, '/procedures/auto/runs/run-done');
    await page.locator('[data-step="thermal"]').waitFor();
    const step = (id) => page.evaluate((s) => document.querySelector(`[data-step="${s}"]`).innerText, id);
    const metrics = await page.evaluate(() => Array.from(document.querySelectorAll('[data-step="thermal"] .ap-metrics tbody tr'))
      .map((tr) => Array.from(tr.querySelectorAll('td')).map((td) => td.innerText.trim())));
    const thermal = await step('thermal');
    const drop = await step('drop');
    const events = await page.evaluate(() => document.querySelector('.ap-events').innerText);
    await page.getByRole('button', { name: '보고서 보기' }).click();
    await page.locator('.ap-report table').waitFor();
    const report = await page.evaluate(() => {
      const r = document.querySelector('.ap-report');
      const h = r.querySelector('.md-h');  // TextBlock 은 제목을 챗 버블 크기의 div.md-h 로 그린다
      return { text: r.innerText, heading: h ? h.textContent : null, rows: r.querySelectorAll('tbody tr').length };
    });
    const reportCall = await page.evaluate(() => window.__calls.filter((c) => c.key.includes('/report?')).map((c) => c.key));
    const blocked = await open(browser, '/procedures/auto/runs/run-run');
    await blocked.locator('[data-step="drop"] .ap-missing').waitFor();
    const missing = await blocked.evaluate(() => Array.from(document.querySelectorAll('[data-step="drop"] .ap-missing li')).map((li) => li.textContent));
    const sup = await open(browser, '/procedures/auto/runs/run-sup');
    await sup.locator('.ap-superseded-note').waitFor();
    const supNote = await sup.evaluate(() => document.querySelector('.ap-superseded-note').innerText);
    return { metrics, thermal, drop, events, report, reportCall, missing, supNote,
             errors: [...page.__errors, ...blocked.__errors, ...sup.__errors] };
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
"""


@pytest.fixture(scope="module")
def seen(tmp_path_factory):
    """화면을 한 번 묶고 시나리오를 한 번에 돌려, 시나리오 이름 → 본 것을 돌려준다."""
    out = tmp_path_factory.mktemp("autopipe")
    (out / "harness.tsx").write_text(_HARNESS.replace("__FE__", str(FE)), encoding="utf-8")
    for name, text in (("build.cjs", _BUILD), ("stub.js", _STUB), ("drive.cjs", _DRIVE)):
        (out / name).write_text(text, encoding="utf-8")
    r = subprocess.run(["node", "build.cjs", str(FE), str(out)], cwd=str(out), capture_output=True, text=True, timeout=180)
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


def test_자동_탭은_feat_auto_pipeline_이_있는_사람에게만_보이고_그_키만으로도_들어온다(seen):
    s = seen("tabs")
    assert "자동" not in s["routines_only"]["tabs"] and s["routines_only"]["autopipe_calls"] == 0, s["routines_only"]
    assert s["auto_only"]["tabs"] == ["자동"], "절차 · 루틴 권한 없이 이 키만 있으면 자동 탭 하나"
    assert s["auto_only"]["loc"] == "/procedures/auto", "절차 첫 화면(만들기)이 없으면 자동 탭으로 간다"
    assert s["both"]["tabs"] == ["만들기", "절차", "실행 이력", "루틴", "자동"]
    assert s["direct"]["health"] == 0, "탭이 없는 사람이 주소로 들어와도 자동 화면이 서지 않는다"


def test_App_의_절차_라우트는_자동_파이프라인_키만_있어도_연다():
    """RequireEntitlement 는 목록 가운데 하나만 있어도 연다 — 이 키가 목록에 없으면 위 탭에 닿기 전에 '내 권한' 으로 튕긴다."""
    src = (FE / "src/App.tsx").read_text(encoding="utf-8")
    assert "need={['feat:procedures', 'feat:routines', 'feat:auto-pipeline']}" in src
    head = (FE / "src/components/layout/AppHeader.tsx").read_text(encoding="utf-8")
    assert "can('feat:auto-pipeline') ? [{ to: '/procedures', label: '절차' }]" in head, "머리 메뉴의 '절차' 도 이 키로 보인다"


def test_꺼짐이면_켜는_법을_말하고_켜짐이면_말하지_않는다(seen):
    s = seen("off")
    assert "꺼짐" in s["off"] and "꺼져 있습니다" in s["off"], s["off"]
    assert "AUTO_PIPELINE_ENABLED=1" in s["off"], "how_to_enable 글을 그대로 보인다"
    assert "엔진 멈춤" in s["off"] and "RA 게시 — 미설정" in s["off"], s["off"]
    assert "step_forge" in s["off"] and "auto_changes 가 없다" in s["off"], "원천별 오류"
    assert "켜짐" in s["on"] and "꺼져 있습니다" not in s["on"], s["on"]
    assert "설정됨(게시판 sys-autopipe)" in s["on"] and "엔진 도는 중" in s["on"], s["on"]


def test_검증_오류와_경고를_줄마다_보이고_JSON_이_깨지면_창구를_부르지_않는다(seen):
    s = seen("validate")
    v = s["seen"]
    assert v["role"] == "alert" and "오류 2건" in v["text"], v
    assert v["errors"] == ["steps[1].id — id 가 겹친다 — thermal", "순환이 있다 — summary → drop → summary"], v["errors"]
    assert v["warnings"] == ["night_only 가 비었다"]
    assert len(s["sent"]) == 1 and s["sent"][0]["spec"]["stage"] == "shadow", "글상자의 JSON 을 spec 으로 보낸다(새 규칙 틀은 그림자)"
    assert s["after_bad_json"] == 1, "JSON 이 깨졌으면 창구를 부르지 않고 그 자리에서 알린다"


def test_자동_제출_규칙을_켜는_것은_확인_한_번_뒤에만_나간다(seen):
    s = seen("enable")
    d = s["auto_dismiss"]
    assert len(d["asked"]) == 1 and d["sent"] == [] and d["chip"] == "꺼짐", d
    assert "자동 제출" in d["asked"][0] and "클러스터 해석 제출" in d["asked"][0] and "저절로" in d["asked"][0], d["asked"][0]
    a = s["auto_accept"]
    assert len(a["asked"]) == 1 and a["sent"] == [{"enabled": True}] and a["chip"] == "켜짐", a
    sh = s["shadow"]
    assert sh["asked"] == [] and sh["sent"] == [{"enabled": True}], "그림자 규칙은 묻지 않는다"
    # 켜진 규칙을 자동 제출로 올리는 저장도 켜기와 같은 일이다
    assert len(s["save_auto_dismiss"]["asked"]) == 1 and s["save_auto_dismiss"]["sent"] == [], s["save_auto_dismiss"]
    assert s["save_auto_accept"]["sent"] == ["auto"], s["save_auto_accept"]


def test_현황판은_판정을_글자로도_보이고_대체된_줄을_흐리게_대체됨으로_보인다(seen):
    s = seen("board")
    assert s["heads"] == ["과제 · 차수", "실행", "thermal", "drop", "summary"], "열 = 규칙 단계(현황판이 열을 안 줘도 스펙 순서로)"
    done, sup, running = s["rows"]
    assert done["cells"][:2] == ["P-100 · EVT2", "끝"] and done["cells"][2:] == ["끝 ✓ 합", "끝 ✗ 부", "끝"], done
    assert sup["superseded"] and not done["superseded"], "대체된 줄만 흐리다"
    assert sup["cells"][1] == "대체됨" and sup["cells"][2] == "끝 △ 경계", sup
    assert running["cells"][2:] == ["끝 ? 모름", "막힘", "—"], "칸이 없는 단계는 줄표"
    assert s["after_click"] == "/procedures/auto/runs/run-done", "줄을 누르면 실행 상세"
    assert s["rules"][0].startswith("자동 규칙") and "꺼짐" in s["rules"][0] and "판 2" in s["rules"][0] and "자동 제출" in s["rules"][0], s["rules"]


def test_감지_목록은_막힌_까닭을_사람_말로_모르는_낱말은_그대로(seen):
    rows = {(r[0], r[1]): r for r in seen("board")["subjects"]}
    assert rows[("P-100", "EVT2")][2:4] == ["준비됨", "—"]
    assert rows[("과제 key 없음", "EVT1")][2:4] == ["막힘", "과제 key 를 못 풂"]
    assert rows[("P-400", "DV")][3] == "사람이 줄 값이 필요함 — 패키지 종류"
    assert rows[("P-500", "차수 모름")][3] == "개발 단계(차수)를 모름"
    assert rows[("P-600", "EVT1")][3] == "weird_word"
    assert rows[("P-700", "EVT1")][2] == "조용해지기를 기다림"


def test_승인_단추는_승인_대기에만_승인_취소는_확인_뒤에만_나간다(seen):
    s = seen("approve_cancel")
    b = s["buttons"]
    assert "제출 승인" in b["run-await"] and "취소" in b["run-await"]
    for rid in ("run-run", "run-done", "run-sup", "run-planned"):
        assert "제출 승인" not in b[rid], (rid, b[rid])
    assert "취소" in b["run-run"]
    for rid in ("run-done", "run-sup", "run-planned"):
        assert "취소" not in b[rid], f"끝난 실행({rid})에는 취소가 없다"
    d = s["approve_dismiss"]
    assert len(d["asked"]) == 1 and d["sent"] == 0, d
    said = d["asked"][0]
    assert "해석 2개" in said and "thermal — thermal_shock · default" in said and "drop — kooremapper · fullangle-26" in said, said
    a = s["approve_accept"]
    assert a["sent"] == 1 and "제출 승인" not in a["buttons"], "승인 뒤 다시 읽어 단추가 사라진다"
    assert s["cancel_dismiss"]["sent"] == 0 and len(s["cancel_dismiss"]["asked"]) == 1
    assert "끝까지" in s["cancel_dismiss"]["asked"][0], "도는 해석은 끝까지 돈다는 것을 묻기 전에 말한다"
    c = s["cancel_accept"]
    assert c["sent"] == 1 and "도는 단계 1개는 앱에 취소가 없어 끝까지 둡니다." in c["status"], c


def test_실행_상세는_결과_봉투_수치표_입력_확인_보고서를_보인다(seen):
    s = seen("detail")
    assert s["metrics"][0] == ["솔더 SED 최대", "0.82", "MJ/m3", "1 (사내 기준 A)", "✓ 합"], s["metrics"]
    assert s["metrics"][1] == ["warpage_max", "0.31", "mm", "—", "? 모름"], "label 이 없으면 name, 기준이 없으면 줄표"
    t = s["thermal"]
    assert "입력 확인 — 갖춤" in t and "SED 분포 — 코너 볼" in t and "기준이 없는 항목은 모름으로 둔다" in t and "프로파일 default" in t, t
    # 동기 앱 — 시작 시각 · 도는 중 없이 곧바로 끝난 단계도 끝으로 보인다
    assert "끝" in s["drop"] and "✗ 부" in s["drop"] and "최대 가속도" in s["drop"] and "시작" not in s["drop"], s["drop"]
    assert "run_created" in s["events"] and "engine" in s["events"], "detail_json 글도 편다"
    assert s["reportCall"] == ["GET /autopipe-api/runs/run-done/report?step=summary"]
    assert s["report"]["heading"] == "종합 판정" and s["report"]["rows"] == 2 and "**" not in s["report"]["text"], s["report"]
    assert s["missing"] == ["사람이 줄 값이 필요함 — 패키지 종류를 고르세요", "개발 단계(차수)를 모름",
                            "박스 문제(클러스터 · 저장소 등) — stcx 공유 볼륨 없음", "ecad_board — 보드 파일 없음"], s["missing"]
    assert "대체됨" in s["supNote"] and "뒤 실행 보기" in s["supNote"], s["supNote"]
