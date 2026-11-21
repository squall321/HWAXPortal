# '발표자료로' 를 헤드리스 브라우저에서 실제 ChatProvider · MessageList 로 본다 — 서버는 띄우지 않는다(가짜 fetch · 가짜 시계, docs/wda-deck)
"""왜 — 단추의 일은 '어느 자리에 서는가' 와 '끝난 알림이 어느 대화에 남는가' 다. 순수 함수 시험으로는 안 잡힌다.

  · 자리 — '/보고서' 저장 답(deliberation 템플릿)은 WDA 의 심의 꼴(delib-16x9)이 준비되지 않으면 숨고(사용자 결정 U-6), RA 보내기 알림(그 밖)은
    owner 만 있으면 선다. 권한 둘 중 하나가 없거나 스위치가 꺼졌으면 어디에도 없다.
  · 맡기기 — 출력 PPT · PDF 와 정식 보고서 꼴이 기본이고 단추를 누른 대화의 서버 id 가 간다.
  · 끝 — 진행을 보다가 끝나면 advance 한 번, 알림은 **단추를 누른 그 대화**에 남는다 — 다른 대화로 옮겨 가 단추 칸이 사라져도 입력창 위 줄이 잇는다.
  · 다시 묻기 — 줄이 목록을 한 번 못 읽어도 다음 차례에 다시 묻는다(멈추면 끝 알림이 남지 않는다).
"""
import json
import subprocess

import pytest

from tests.test_delib_stream_in_browser import _BUILD, FE, pytestmark  # noqa: F401 — 같은 도구가 없으면 같이 건너뛴다

_HARNESS = r"""
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { AuthContext } from '__FE__/src/auth/AuthContext';
import { ChatProvider, useChat } from '__FE__/src/state/ChatContext';
import { MessageList } from '__FE__/src/components/chat/MessageList';
import { DeckResume } from '__FE__/src/components/chat/DeckResume';

function Probe({ resume = true }: { resume?: boolean }) {
  const { messages, conversations, activeConversation, selectConversation } = useChat();
  return (
    <>
      <span id="active">{activeConversation?.serverId ?? ''}</span>
      <span id="counts">{conversations.map((c) => `${c.serverId}:${c.messages.length}`).join(',')}</span>
      <span id="lastA">{conversations.find((c) => c.serverId === 'srv-A')?.messages.slice(-1)[0]?.text ?? ''}</span>
      <span id="textsC">{JSON.stringify(conversations.find((c) => c.serverId === 'srv-C')?.messages.map((m) => m.text) ?? null)}</span>
      <button id="toA" type="button" onClick={() => selectConversation('cA')}>A</button>
      <button id="toB" type="button" onClick={() => selectConversation('cB')}>B</button>
      <button id="toC" type="button" onClick={() => selectConversation('srv-C')}>C</button>
      {resume && <DeckResume />}
      <MessageList messages={messages} />
    </>
  );
}
// nested — '/deliberate' 처럼 안쪽에 챗 제공자가 하나 더 있다(그 안의 줄이 알림을 받는다 — 바깥 제공자의 대화도 알아야 한다)
function Inner() {
  return <div id="inner"><DeckResume /></div>;
}
(window as unknown as { __mount: (ents?: string[] | null, serverKind?: 'chat', nested?: boolean) => void }).__mount = (ents, serverKind, nested) => {
  const user = { subject: 'u1@corp.example', email: 'u1@corp.example', display_name: 'U', groups: [],
                 entitlements: ents ?? ['feat:chat', 'plat:webdesign', 'plat:reportarchive'] };
  createRoot(document.getElementById('root')!).render(
    <AuthContext.Provider
      value={{ user, status: 'authenticated', login: () => undefined, logout: async () => undefined, refresh: async () => undefined }}
    >
      <MemoryRouter>
        <ChatProvider serverKind={serverKind}>
          <Probe resume={!nested} />
          {nested && (
            <ChatProvider storagePrefix="hwax.delib">
              <Inner />
            </ChatProvider>
          )}
        </ChatProvider>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
};
"""

_STUB = r"""
(() => {
  window.__calls = [];
  const json = (body, status = 200) =>
    Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }));
  window.fetch = (url, init = {}) => {
    const u = String(url);
    const method = (init.method || 'GET').toUpperCase();
    window.__calls.push({ url: u, method, body: typeof init.body === 'string' ? JSON.parse(init.body) : null });
    if (u === '/agent/deck/status') return json(window.__status);
    if (u === '/agent/conversations' && method === 'GET' && window.__convList) return json({ conversations: window.__convList });
    if (u.startsWith('/agent/conversations/') && method === 'GET' && window.__convDetail && window.__convDetail[u.slice(21)]) {
      return json(window.__convDetail[u.slice(21)]);
    }
    // 옛 심의 결과 카드의 RA 열기(docs/wda-deck WD-D78) — __raOpen401 번은 세션이 지난 401, __raOpenStatus 면 그 거절, 아니면 열 곳
    if (u.startsWith('/agent/ra/reports/')) {
      if (window.__raOpen401 > 0) { window.__raOpen401 -= 1; return json({ detail: 'session expired' }, 401); }
      if (window.__raOpenStatus) return json({ detail: 'denied' }, window.__raOpenStatus);
      return json({ url: window.__raOpenUrl || '/report-archive/' });
    }
    if (u === '/auth/refresh') return json({ ok: true });
    // 분석 루틴의 실행 원장(RoutineView 가 흐르지 않는 메시지를 다시 읽는다) — __runView 가 있을 때만
    if (u.startsWith('/routines-api/runs/')) return window.__runView ? json(window.__runView) : json({ detail: 'Not Found' }, 404);
    if (u === '/agent/deck/jobs' && method === 'POST') return json(window.__created);
    if (u === '/agent/deck/jobs' && method === 'GET') {
      if (window.__listOff) return json({ detail: 'Not Found' }, 404);
      if (window.__listFail > 0) { window.__listFail -= 1; return json({ detail: '잠시 답하지 않는다' }, 502); }
      return json({ jobs: window.__list || [], keep_days: 7 });
    }
    if (u.startsWith('/agent/deck/jobs/')) {
      if (u.endsWith('/advance')) {
        // __advQueue — 차례대로 줄 답(알림만 미룬 끝 등). 다 쓰면 __advanced. 아직 next 가 있는 답이면 목록에 남긴다
        const a = window.__advQueue && window.__advQueue.length ? window.__advQueue.shift() : window.__advanced;
        window.__list = a && a.next ? [a] : [];
        return json(a);
      }
      if (u.endsWith('/dismiss')) return json({ dismissed: true });
      // M2 — 다시 시도(새 잡을 돌려준다) · 지우기(지운 잡의 보기). 거절을 흉내 낼 때는 __retryStatus · __deleteStatus
      if (u.endsWith('/retry')) return window.__retryStatus ? json({ detail: '다시 시도할 수 없습니다' }, window.__retryStatus) : json(window.__retried);
      if (method === 'DELETE') return window.__deleteStatus ? json({ detail: 'WDA 가 아직 만드는 중이라 지우지 못했습니다' }, window.__deleteStatus) : json(window.__deletedJob);
      if (window.__jobOff) return json({ detail: 'Not Found' }, 404);
      return json(window.__states.length > 1 ? window.__states.shift() : window.__states[0]);
    }
    return json({ detail: 'stub: no route ' + u }, 404);
  };
})();
"""

_DRIVE = r"""
const { createRequire } = require('module');
const path = require('path');
const [FE, OUT] = process.argv.slice(2);
const { chromium } = createRequire(path.join(FE, 'package.json'))('@playwright/test');

const JOB = 'f'.repeat(32);
const NOTICE_TEXT = '보고서 41「설계 검토」로 발표자료를 만들었습니다 — PPT(글자를 고칠 수 있는 꼴) · PDF(정식 보고서 문서). 받기 — '
  + `[PPT 받기](/agent/deck/jobs/${JOB}/files/pptx) · [PDF 받기](/agent/deck/jobs/${JOB}/files/pdf).`;
const base = { job_id: JOB, report: { id: 41, title: '설계 검토' }, options: { targets: ['pptx', 'pdf'], doc_style: 'report', pptx_mode: 'hybrid' },
  conversation_id: 'srv-A', created_at: 1, elapsed_s: 3, step: '', progress: 0, error: null, late: false, next: null, skipped: [], files: [] };
const QUEUED = { ...base, state: 'queued', step: '줄 서는 중', created: true };
const RENDERING = { ...base, state: 'rendering', step: '만드는 중', progress: 80, elapsed_s: 4 };
const FINISH = { ...base, state: 'done', step: '끝', progress: 100, next: 'finish', elapsed_s: 6 };
const DONE = { ...base, state: 'done', step: '끝', progress: 100, next: null, elapsed_s: 6,
  files: [{ kind: 'pptx', bytes: 1228800, label: 'PPT', url: `/agent/deck/jobs/${JOB}/files/pptx` },
          { kind: 'pdf', bytes: 1972224, label: 'PDF', url: `/agent/deck/jobs/${JOB}/files/pdf` }],
  noticed: true, notice: { text: NOTICE_TEXT, deck: { job_id: JOB, state: 'done', report_id: 41, files: ['pptx', 'pdf'] },
    activity: [{ ts: 1, step: '발표자료 만들기(사람이 맡김)', tool: 'web_design_agents', detail: '{}', result_full: '{"report_id":41}', ok: true, origin: 'upload' }] } };
const STATUS = (deliberation) => ({ enabled: true, reason: null, formats: { deliberation }, targets: ['pptx', 'pdf', 'docx', 'html', 'video'],
  doc_styles: ['report', 'brief', 'memo'], defaults: { targets: ['pptx', 'pdf'], doc_style: 'report' }, keep_days: 7 });

// 대화 둘 — A 에 '/보고서' 저장 답(58, deliberation)과 RA 보내기 알림(41, 그 밖), B 에 일반 답
const SEED = JSON.stringify([
  { id: 'cA', serverId: 'srv-A', title: 'A', createdAt: 2, updatedAt: 2, messages: [
    { role: 'user', content: '/보고서', ts: 1 },
    { role: 'assistant', content: '📄 Report Archive 보고서 #58 로 저장했습니다 — 「심의 — 굽힘」', ts: 2, raReport: { id: 58, title: '심의 — 굽힘' } },
    { role: 'assistant', content: '「설계.pptx」 으로 Report Archive 보고서 초안을 만들었습니다 — 보고서 41', ts: 3,
      activity: [{ ts: 3, step: 'Report Archive 보고서 초안(사람이 올림)', tool: 'create_report_draft', detail: '{"file":"설계.pptx"}',
                   result_full: '{"report_id":41,"title":"설계 검토"}', ok: true, origin: 'upload' }] } ] },
  { id: 'cB', serverId: 'srv-B', title: 'B', createdAt: 1, updatedAt: 1, messages: [
    { role: 'user', content: '안녕', ts: 1 }, { role: 'assistant', content: '안녕하세요', ts: 2 } ] } ]);

async function open(browser, { status, ents, serverKind, before, nested } = {}) {
  const page = await browser.newPage();
  page.setDefaultTimeout(10000);
  page.__errors = [];
  page.on('pageerror', (e) => page.__errors.push(String(e)));
  await page.route('http://harness.invalid/**', (r) =>
    r.fulfill({ contentType: 'text/html', body: '<!doctype html><html><body><div id="root"></div></body></html>' }));
  await page.clock.install({ time: new Date('2026-11-01T00:00:00Z') });
  await page.goto('http://harness.invalid/');
  await page.addScriptTag({ path: path.join(OUT, 'stub.js') });
  await page.evaluate(([seed, st]) => {
    localStorage.setItem('hwax.chat.u1@corp.example.conversations', seed);
    localStorage.setItem('hwax.chat.u1@corp.example.activeId', 'cA');
    window.__status = st;
    window.__states = [];
  }, [SEED, status === undefined ? STATUS(false) : status]);
  if (before) await page.evaluate(before);
  await page.addScriptTag({ path: path.join(OUT, 'bundle.js') });
  await page.evaluate(([e, k, n]) => window.__mount(e, k, n), [ents || null, serverKind || null, Boolean(nested)]);
  await page.waitForTimeout(80);
  return page;
}
const text = (page, id) => page.evaluate((i) => document.getElementById(i).textContent, id);
const buttons = (page) => page.evaluate(() => document.querySelectorAll('.deck-go').length);
const calls = (page, prefix) => page.evaluate((p) => window.__calls.filter((c) => c.url.startsWith(p)), prefix);
async function forward(page, ms) { await page.clock.fastForward(ms); await page.waitForTimeout(60); }

async function makeJob(page) {
  await page.evaluate(([q, r, f, d]) => { window.__created = q; window.__states = [r, f]; window.__advanced = d; window.__list = [q]; },
                      [QUEUED, RENDERING, FINISH, DONE]);
  await page.locator('.deck-go').first().click();
  const opts = await page.evaluate(() => ({
    checked: Array.from(document.querySelectorAll('.deck-opts input')).map((i) => i.checked),
    style: (document.querySelector('.deck-style select') || {}).value || null }));
  await page.locator('.deck-panel .upl-go').click();
  await page.getByText('발표자료 만드는 중').first().waitFor();
  return opts;
}

const PREVIEW = `/agent/deck/jobs/${JOB}/preview`;
const DONE_PDF = { ...DONE, preview: PREVIEW, can_retry: false, deleted: false };
const FAILED = { ...base, state: 'failed', step: '장면 구성 에서 멈춤', error: "WDA 가 '장면 구성' 단계에서 실패했습니다.", progress: null, next: null,
  elapsed_s: 6, can_retry: true, deleted: false, preview: null, noticed: true, notice: null };
const GONE = { ...DONE, files: [], expired: true, deleted: true, preview: null, can_retry: false, notice: null };
const STATUS_DEL = { ...STATUS(false), delete: true };

const SCENARIOS = {
  // M2 — 끝난 잡의 칸에 PDF 미리보기(포털 경로 · 틀에 sandbox 속성 없음) · 사본 지우기. 지우면 링크 · 미리보기가 걷힌다
  async tools(browser) {
    const page = await open(browser, { status: STATUS_DEL });
    await page.evaluate(() => { window.confirm = (m) => { window.__confirmed = (window.__confirmed || []).concat(m); return true; }; });
    await page.evaluate(([q, r, f, d]) => { window.__created = q; window.__states = [r, f, d]; window.__advanced = d; window.__list = [q]; },
                        [QUEUED, RENDERING, FINISH, DONE_PDF]);
    await page.locator('.deck-go').first().click();
    await page.locator('.deck-panel .upl-go').click();
    await page.getByText('발표자료 만드는 중').first().waitFor();
    await forward(page, 3100);
    await forward(page, 3100);
    await page.getByText('발표자료를 만들었습니다').first().waitFor();
    const panel = page.locator('.deck-panel').first();
    const before = await page.evaluate(() => document.querySelectorAll('iframe.deck-preview').length);
    const g0 = (await calls(page, '/agent/deck/jobs/')).filter((c) => c.method === 'GET').length;
    await panel.getByRole('button', { name: 'PDF 미리보기' }).click();
    await page.locator('iframe.deck-preview').waitFor({ state: 'attached' });
    const frame = await page.evaluate(() => { const f = document.querySelector('iframe.deck-preview');
      return { src: f.getAttribute('src'), sandbox: f.hasAttribute('sandbox'), referrer: f.getAttribute('referrerpolicy') }; });
    const asked = (await calls(page, '/agent/deck/jobs/')).filter((c) => c.method === 'GET').length - g0;
    await panel.getByRole('button', { name: 'PDF 미리보기 닫기' }).click();
    const closed = await page.evaluate(() => document.querySelectorAll('iframe.deck-preview').length);
    await page.evaluate((g) => { window.__deletedJob = g; }, GONE);
    await panel.getByRole('button', { name: '사본 지우기' }).click();
    await panel.getByText('사본을 지웠습니다').waitFor();
    const del = (await calls(page, '/agent/deck/jobs/')).filter((c) => c.method === 'DELETE').map((c) => c.url);
    const after = await panel.evaluate((el) => ({ links: el.querySelectorAll('.deck-file').length, text: el.textContent,
      buttons: Array.from(el.querySelectorAll('button')).map((b) => b.textContent) }));
    return { before, frame, asked, closed, del, after, confirmed: await page.evaluate(() => window.__confirmed), errors: page.__errors };
  },
  // WDA 가 지우기를 모르는 판(status.delete 없음)이면 사본 지우기를 내지 않는다 · 지우기를 WDA 가 거절하면 까닭을 보이고 잡은 그대로다
  async toolsRefused(browser) {
    const noDel = await open(browser);
    await noDel.evaluate(([q, f, d]) => { window.__created = q; window.__states = [f, d]; window.__advanced = d; window.__list = [q]; }, [QUEUED, FINISH, DONE_PDF]);
    await noDel.locator('.deck-go').first().click();
    await noDel.locator('.deck-panel .upl-go').click();
    await forward(noDel, 3100);
    await noDel.getByText('발표자료를 만들었습니다').first().waitFor();
    const noDelButtons = await noDel.locator('.deck-panel').first().evaluate((el) => Array.from(el.querySelectorAll('button')).map((b) => b.textContent));
    const page = await open(browser, { status: STATUS_DEL });
    await page.evaluate(() => { window.confirm = () => true; window.__deleteStatus = 409; });
    await page.evaluate(([q, f, d]) => { window.__created = q; window.__states = [f, d]; window.__advanced = d; window.__list = [q]; }, [QUEUED, FINISH, DONE_PDF]);
    await page.locator('.deck-go').first().click();
    await page.locator('.deck-panel .upl-go').click();
    await forward(page, 3100);
    await page.getByText('발표자료를 만들었습니다').first().waitFor();
    await page.locator('.deck-panel').first().getByRole('button', { name: '사본 지우기' }).click();
    await page.locator('.deck-panel .upl-err').first().waitFor();
    const refused = await page.locator('.deck-panel').first().evaluate((el) => ({ err: el.querySelector('.upl-err').textContent,
      links: el.querySelectorAll('.deck-file').length }));
    return { noDelButtons, refused, errors: [...noDel.__errors, ...page.__errors] };
  },
  // 실패한 잡의 칸에 '다시 시도' — 새 잡을 받아 그 잡의 진행을 잇는다(다시 만들기와 다르다 — 만들기 창구를 부르지 않는다)
  async retry(browser) {
    const page = await open(browser);
    await page.evaluate(([q, f]) => { window.__created = q; window.__states = [{ ...f, next: 'finish' }]; window.__advanced = f; window.__list = [q]; },
                        [QUEUED, FAILED]);
    await page.locator('.deck-go').first().click();
    await page.locator('.deck-panel .upl-go').click();
    await forward(page, 3100);
    await page.getByText('발표자료를 만들지 못했습니다').first().waitFor();
    const panel = page.locator('.deck-panel').first();
    const buttons0 = await panel.evaluate((el) => Array.from(el.querySelectorAll('button')).map((b) => b.textContent));
    const NEW = 'e'.repeat(32);
    await page.evaluate(([q, r]) => { window.__retried = q; window.__states = [r]; },
                        [{ ...QUEUED, job_id: NEW, state: 'preparing', step: '다시 돌리는 중', created: true }, { ...RENDERING, job_id: NEW }]);
    const posts0 = (await calls(page, '/agent/deck/jobs')).filter((c) => c.method === 'POST' && c.url === '/agent/deck/jobs').length;
    await panel.getByRole('button', { name: '다시 시도' }).click();
    await page.getByText('발표자료 만드는 중').first().waitFor();
    await forward(page, 3100);
    const all = await calls(page, '/agent/deck/jobs');
    return { buttons0, retried: all.filter((c) => c.url.endsWith('/retry')).map((c) => c.url),
             creates: all.filter((c) => c.method === 'POST' && c.url === '/agent/deck/jobs').length - posts0,
             polled: all.some((c) => c.method === 'GET' && c.url === `/agent/deck/jobs/${NEW}`), errors: page.__errors };
  },
  // 대화에 남은 발표자료 알림 아래 '발표자료 관리' — 새로고침 뒤에도 미리보기 · 지우기 · 다시 시도에 닿는다. 누를 때만 잡을 읽는다
  async noticeTools(browser) {
    const seedNotice = () => {
      const k = 'hwax.chat.u1@corp.example.conversations';
      const convs = JSON.parse(localStorage.getItem(k));
      convs[0].messages.push({ role: 'assistant', content: '보고서 41「설계 검토」로 발표자료를 만들었습니다', ts: 9, deckJob: 'f'.repeat(32),
        activity: [{ ts: 9, step: '발표자료 만들기(사람이 맡김)', tool: 'web_design_agents', detail: '{}', result_full: '{"report_id":41}', ok: true, origin: 'upload' }] });
      localStorage.setItem(k, JSON.stringify(convs));
    };
    const off = await open(browser, { status: { ...STATUS(true), enabled: false, reason: 'off' }, before: seedNotice });
    const offButtons = await off.evaluate(() => document.querySelectorAll('.deck-notice-tools').length);
    const page = await open(browser, { status: STATUS_DEL, before: seedNotice });
    const early = (await calls(page, '/agent/deck/jobs/')).length;
    await page.evaluate((d) => { window.__states = [d]; }, DONE_PDF);
    await page.locator('.deck-notice-tools button').click();
    const panel = page.locator('.deck-notice-tools.deck-panel');
    await panel.waitFor();
    const buttons1 = await panel.evaluate((el) => Array.from(el.querySelectorAll('.deck-tools button')).map((b) => b.textContent));
    await panel.getByRole('button', { name: 'PDF 미리보기' }).click();
    await page.locator('iframe.deck-preview').waitFor({ state: 'attached' });
    const src = await page.evaluate(() => document.querySelector('iframe.deck-preview').getAttribute('src'));
    // 실패 알림 — 다시 시도를 맡기면 진행은 줄이 잇는다고 말한다
    const failedPage = await open(browser, { status: STATUS_DEL, before: seedNotice });
    await failedPage.evaluate(([f, q]) => { window.__states = [f]; window.__retried = q; window.__list = [q]; },
                              [FAILED, { ...QUEUED, job_id: 'e'.repeat(32) }]);
    await failedPage.locator('.deck-notice-tools button').click();
    const fpanel = failedPage.locator('.deck-notice-tools.deck-panel');
    await fpanel.getByRole('button', { name: '다시 시도' }).click();
    await fpanel.getByText('다시 시도를 맡겼습니다').waitFor();
    const strip = await failedPage.evaluate(() => !!document.querySelector('.deck-resume'));
    // 기록이 지워진 알림(7일) — 까닭을 말하고 묻기를 그친다
    const gonePage = await open(browser, { status: STATUS_DEL, before: seedNotice });
    await gonePage.evaluate(() => { window.__jobOff = true; });
    await gonePage.locator('.deck-notice-tools button').click();
    await gonePage.getByText('기록이 지워졌습니다').waitFor();
    return { offButtons, early, buttons1, src, strip,
             retried: (await calls(failedPage, '/agent/deck/jobs/')).filter((c) => c.url.endsWith('/retry')).length,
             errors: [...off.__errors, ...page.__errors, ...failedPage.__errors, ...gonePage.__errors] };
  },
  // 분석 루틴의 RA 초안(M2) — 심의 보고서와 같은 문(심의 꼴이 active 일 때만), 단추는 루틴 칸 안에 하나만. 초안 번호가 원장에만 있는
  // 메시지(끝에 묻는 루틴을 뒤에 올렸다 · 새로고침 뒤의 포인터)는 원장을 읽은 뒤 선다
  async routine(browser) {
    const seedRoutine = (routine) => {
      const k = 'hwax.chat.u1@corp.example.conversations';
      const convs = JSON.parse(localStorage.getItem(k));
      convs[0].messages.push({ role: 'assistant', content: '루틴 보고서 글', ts: 9, routine });
      localStorage.setItem(k, JSON.stringify(convs));
    };
    const WITH = { run_id: 'run-1', title: '굽힘 루틴', state: 'done', steps: [], report: { ra_upload: 'auto', ra_report_id: 91 } };
    const hidden = await open(browser, { before: `(${seedRoutine})(${JSON.stringify(WITH)})` });
    const without = await buttons(hidden);
    const page = await open(browser, { status: STATUS(true), before: `(${seedRoutine})(${JSON.stringify(WITH)})` });
    const total = await buttons(page);
    const inRoutine = await page.evaluate(() => document.querySelectorAll('.rv .deck-go').length);
    const inMsg = await page.evaluate(() => {
      const rv = document.querySelector('.rv');
      return rv ? rv.closest('.msg').querySelectorAll('.deck-go').length : -1;
    });
    await page.evaluate((q) => { window.__created = q; window.__states = [q]; window.__list = [q]; }, { ...QUEUED, report: { id: 91, title: '굽힘 루틴' } });
    await page.locator('.rv .deck-go').click();
    await page.locator('.deck-panel .upl-go').click();
    await page.getByText('발표자료 만드는 중').first().waitFor();
    const create = (await calls(page, '/agent/deck/jobs')).find((c) => c.method === 'POST' && c.url === '/agent/deck/jobs');
    // 원장에만 있는 초안 번호 — 메시지에는 실행 포인터뿐이다
    const VIEW = { run: { id: 'run-2', routine_id: 'r', version_no: 1, title: '원장 루틴', executor: 'chat', state: 'done', reason: null, calls: 0,
                          limits: { minutes: 1, calls: 1 }, limit_reached: null, report_ready: true, ra_report_id: 92, ra_error: null },
                   inputs: {}, purpose: '', steps: [], next_step: null, report: { title: '원장 루틴', sections: [], upload: 'ask' } };
    const POINTER = { run_id: 'run-2', title: '원장 루틴', state: 'done', steps: [] };
    const ledger = await open(browser, { status: STATUS(true), ents: ['feat:chat', 'feat:routines', 'plat:webdesign', 'plat:reportarchive'],
      before: `window.__runView = ${JSON.stringify(VIEW)}; (${seedRoutine})(${JSON.stringify(POINTER)})` });
    await ledger.waitForFunction(() => document.querySelectorAll('.rv .deck-go').length === 1);
    await ledger.evaluate((q) => { window.__created = q; window.__states = [q]; window.__list = [q]; }, { ...QUEUED, report: { id: 92, title: '원장 루틴' } });
    await ledger.locator('.rv .deck-go').click();
    await ledger.locator('.deck-panel .upl-go').click();
    await ledger.getByText('발표자료 만드는 중').first().waitFor();
    const create2 = (await calls(ledger, '/agent/deck/jobs')).find((c) => c.method === 'POST' && c.url === '/agent/deck/jobs');
    return { without, total, inRoutine, inMsg, create: create && create.body, create2: create2 && create2.body,
             errors: [...hidden.__errors, ...page.__errors, ...ledger.__errors] };
  },
  // 심의 꼴이 없는 WDA — '/보고서'(deliberation)는 숨고 RA 보내기 알림은 선다. 꼴이 서면 둘 다
  async spots(browser) {
    const page = await open(browser);
    const without = await buttons(page);
    const titles = await page.evaluate(() => Array.from(document.querySelectorAll('.deck-go')).map((b) =>
      b.closest('.msg').querySelector('.msg-content').textContent));
    const page2 = await open(browser, { status: STATUS(true) });
    const withFormat = await buttons(page2);
    return { without, titles, withFormat, errors: [...page.__errors, ...page2.__errors] };
  },
  // 권한 둘 중 하나가 없으면 묻지도 않는다 · 스위치가 꺼졌으면 어디에도 없다
  async hidden(browser) {
    const noPerm = await open(browser, { ents: ['feat:chat', 'plat:webdesign'] });
    const off = await open(browser, { status: { ...STATUS(true), enabled: false, reason: 'off' } });
    return { noPerm: await buttons(noPerm), noPermCalls: (await calls(noPerm, '/agent/deck')).length,
             off: await buttons(off), errors: [...noPerm.__errors, ...off.__errors] };
  },
  // 그 대화에 머문다 — 진행을 보다가 끝나면 advance 한 번 · 알림이 이 대화에 · 받기 링크는 포털 경로
  async stay(browser) {
    const page = await open(browser);
    const before = await text(page, 'counts');
    const opts = await makeJob(page);
    const create = (await calls(page, '/agent/deck/jobs')).find((c) => c.method === 'POST' && c.url === '/agent/deck/jobs');
    await forward(page, 3100);
    const mid = await page.evaluate(() => (document.querySelector('.deck-panel .upl-note') || {}).textContent || '');
    await forward(page, 3100);
    await page.getByText('발표자료를 만들었습니다').first().waitFor();
    const links = await page.evaluate(() => Array.from(document.querySelectorAll('.deck-file')).map((a) => a.getAttribute('href')));
    const advances = (await calls(page, '/agent/deck/jobs/')).filter((c) => c.url.endsWith('/advance')).length;
    // 대화에 남은 알림의 받기 링크도 눌리는 링크다(같은 오리진 절대경로 — md.ts)
    const noticeLinks = await page.evaluate(() => Array.from(document.querySelectorAll('.msg .md-link')).map((a) => a.getAttribute('href')));
    return { before, opts, create: create && create.body, mid, links, noticeLinks, advances, after: await text(page, 'counts'),
             last: await text(page, 'lastA'), errors: page.__errors };
  },
  // 다른 대화로 옮겨 간다 — 단추 칸이 사라져도 입력창 위 줄이 잇고, 알림은 단추를 누른 A 에 남는다(B 가 아니라)
  async away(browser) {
    const page = await open(browser);
    await makeJob(page);
    await page.locator('#toB').click();
    await page.waitForTimeout(60);
    await page.evaluate((f) => { window.__list = [f]; }, FINISH);      // 그 사이 WDA 가 끝냈다
    await forward(page, 10500);
    await page.waitForFunction(() => document.getElementById('lastA').textContent.includes('발표자료를 만들었습니다'));
    return { active: await text(page, 'active'), counts: await text(page, 'counts'),
             advances: (await calls(page, '/agent/deck/jobs/')).filter((c) => c.url.endsWith('/advance')).length, errors: page.__errors };
  },
  // 목록을 한 번 못 읽어도 줄이 다시 묻기를 멈추지 않는다 — 다음 차례에 끝을 보고 알림을 A 에
  async blip(browser) {
    const page = await open(browser);
    await makeJob(page);
    await page.locator('#toB').click();
    await page.waitForTimeout(60);
    await page.evaluate((f) => { window.__list = [f]; window.__listFail = 1; }, FINISH);
    await forward(page, 10500);                                         // 이 차례는 못 읽는다
    const mid = { last: await text(page, 'lastA'), strip: await page.evaluate(() => !!document.querySelector('.deck-resume')) };
    await forward(page, 10500);                                         // 다음 차례에 다시 묻는다
    await page.waitForFunction(() => document.getElementById('lastA').textContent.includes('발표자료를 만들었습니다'));
    return { mid, counts: await text(page, 'counts'),
             lists: (await calls(page, '/agent/deck/jobs')).filter((c) => c.method === 'GET' && c.url === '/agent/deck/jobs').length,
             errors: page.__errors };
  },
  // 끝난 잡에도 '다시 만들기'(again) · 지워진 파일은 링크 대신 다시 만들기 · 다른 대화의 잡을 받으면 알림이 갈 대화를 말한다(WD-D62)
  async regen(browser) {
    const page = await open(browser);
    await makeJob(page);
    await forward(page, 3100);
    await forward(page, 3100);
    await page.getByText('발표자료를 만들었습니다').first().waitFor();
    const againBtn = await page.locator('.deck-panel button', { hasText: '다시 만들기' }).count();
    await page.evaluate((q) => { window.__created = q; window.__states = [q]; }, { ...QUEUED, job_id: 'e'.repeat(32) });
    await page.locator('.deck-panel button', { hasText: '다시 만들기' }).click();
    await page.waitForTimeout(80);
    const create = (await calls(page, '/agent/deck/jobs')).filter((c) => c.method === 'POST' && c.url === '/agent/deck/jobs').pop();
    return { againBtn, againBody: create && create.body, errors: page.__errors };
  },
  async expired(browser) {
    const page = await open(browser);
    const GONE = { ...DONE, expired: true, files: [], notice: null, noticed: false };
    await page.evaluate(([g]) => { window.__created = { ...g, created: false }; window.__list = []; }, [GONE]);
    await page.locator('.deck-go').first().click();
    await page.locator('.deck-panel .upl-go').click();
    await page.waitForTimeout(120);
    return { text: await page.evaluate(() => document.querySelector('.deck-panel').textContent),
             links: await page.evaluate(() => document.querySelectorAll('.deck-panel .deck-file').length), errors: page.__errors };
  },
  async elsewhere(browser) {
    const page = await open(browser);
    await page.evaluate((q) => { window.__created = { ...q, created: false, conversation_id: 'srv-B' }; window.__states = [{ ...q, conversation_id: 'srv-B' }];
      window.__list = []; }, QUEUED);
    await page.locator('.deck-go').first().click();
    await page.locator('.deck-panel .upl-go').click();
    await page.waitForTimeout(120);
    return { text: await page.evaluate(() => (document.querySelector('.deck-panel .upl-note') || {}).textContent || ''), errors: page.__errors };
  },
  // 서버 목록에서 온 자리표시자 대화(C — 다른 기기에서 쓴 대화)에 알림이 오면 화면 사본에 붙이지 않는다 — 붙이면 열 때 서버 사본을 읽지 않아
  // 그 대화의 이력이 알림 하나로 가려졌다(적대 검토, WD-D63)
  async placeholder(browser) {
    const before = () => {
      window.__convList = [{ id: 'srv-A', title: 'A', kind: 'chat', source: 'web', created_at: 1, updated_at: 2 },
                           { id: 'srv-C', title: 'C', kind: 'chat', source: 'web', created_at: 1, updated_at: 1700000000 }];
      window.__convDetail = { 'srv-C': { id: 'srv-C', title: 'C', kind: 'chat', source: 'web', created_at: 1, updated_at: 1700000000, messages: [
        { role: 'user', persona: null, round: null, content: '/보고서', meta: null, ts: 1 },
        { role: 'assistant', persona: null, round: null, content: 'SAVED-ON-OTHER-DEVICE', meta: { ra_report: { id: 41, title: 't' } }, ts: 2 },
        { role: 'assistant', persona: null, round: null, content: 'NOTICE-FROM-SERVER', meta: { deck: { job_id: 'f'.repeat(32) } }, ts: 3 } ] } };
    };
    const page = await open(browser, { serverKind: 'chat', before });
    await page.evaluate(([f, d]) => { window.__list = [{ ...f, conversation_id: 'srv-C' }];
      window.__advanced = { ...d, conversation_id: 'srv-C' }; }, [FINISH, DONE]);
    await page.evaluate(() => window.dispatchEvent(new Event('hwax:deck-changed')));
    await page.waitForFunction(() => window.__calls.some((c) => c.url.endsWith('/advance')));
    await page.waitForTimeout(120);
    const beforeOpen = await text(page, 'textsC');
    await page.locator('#toC').click();
    await page.waitForFunction(() => (document.getElementById('textsC').textContent || '').includes('SAVED-ON-OTHER-DEVICE'));
    return { beforeOpen, afterOpen: await text(page, 'textsC'),
             detailGets: (await calls(page, '/agent/conversations/srv-C')).length, errors: page.__errors };
  },
  // 안쪽 챗 제공자('/deliberate')의 줄이 받은 알림을 바깥(앱 전체) 제공자의 대화도 받는다(적대 검토, WD-D64)
  async nested(browser) {
    const page = await open(browser, { nested: true });
    await page.evaluate(([f, d]) => { window.__list = [f]; window.__advanced = d; }, [FINISH, DONE]);
    await page.evaluate(() => window.dispatchEvent(new Event('hwax:deck-changed')));
    await page.waitForFunction(() => window.__calls.some((c) => c.url.endsWith('/advance')));
    await page.waitForTimeout(150);
    return { lastA: await text(page, 'lastA'), counts: await text(page, 'counts'), errors: page.__errors };
  },
  // 숨은 탭은 천천히 묻고(10배) 보이게 되면 곧 박자로 돌아온다 · 창구가 404(스위치 꺼짐)면 묻기를 멈춘다(WD-D65)
  async hiddenTab(browser) {
    const page = await open(browser);
    const RUN = { ...base, state: 'rendering', step: '만드는 중', progress: 80, elapsed_s: 4 };
    await page.evaluate((r) => { window.__list = [r];
      window.__vis = 'visible';
      Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => window.__vis }); }, RUN);
    await page.evaluate(() => window.dispatchEvent(new Event('hwax:deck-changed')));
    await page.waitForTimeout(80);
    const lists = async () => (await calls(page, '/agent/deck/jobs')).filter((c) => c.method === 'GET' && c.url === '/agent/deck/jobs').length;
    const n0 = await lists();
    await page.evaluate(() => { window.__vis = 'hidden'; document.dispatchEvent(new Event('visibilitychange')); });
    await forward(page, 30000);
    const hidden30 = (await lists()) - n0;
    await forward(page, 75000);
    const hidden105 = (await lists()) - n0;
    await page.evaluate(() => { window.__vis = 'visible'; document.dispatchEvent(new Event('visibilitychange')); });
    const n1 = await lists();
    await forward(page, 10500);
    const shown = (await lists()) - n1;
    return { hidden30, hidden105, shown, errors: page.__errors };
  },
  async stop404(browser) {
    const page = await open(browser);
    const RUN = { ...base, state: 'rendering', step: '만드는 중', progress: 80, elapsed_s: 4 };
    await page.evaluate((r) => { window.__list = [r]; }, RUN);
    await page.evaluate(() => window.dispatchEvent(new Event('hwax:deck-changed')));
    await page.waitForTimeout(80);
    await page.evaluate(() => { window.__listOff = true; });
    await forward(page, 10500);
    const lists = async () => (await calls(page, '/agent/deck/jobs')).filter((c) => c.method === 'GET' && c.url === '/agent/deck/jobs').length;
    const n0 = await lists();
    await forward(page, 60000);
    await page.evaluate(() => window.dispatchEvent(new Event('hwax:deck-changed')));   // 다른 칸이 맡겨도 — 다시 열 때까지 묻지 않는다
    await page.waitForTimeout(80);
    return { after: (await lists()) - n0, strip: await page.evaluate(() => !!document.querySelector('.deck-resume')), errors: page.__errors };
  },
  async spot404(browser) {
    const page = await open(browser);
    await makeJob(page);
    await page.evaluate(() => { window.__jobOff = true; });
    await forward(page, 3100);
    const gets = async () => (await calls(page, '/agent/deck/jobs/')).filter((c) => c.method === 'GET').length;
    const n0 = await gets();
    await forward(page, 3100);
    // 탭을 숨겼다 다시 보여도(박자가 바뀌어 효과가 다시 돈다) — 다시 열 때까지 묻지 않는다
    await page.evaluate(() => { window.__vis = 'hidden';
      Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => window.__vis });
      document.dispatchEvent(new Event('visibilitychange')); });
    await page.waitForTimeout(60);
    await page.evaluate(() => { window.__vis = 'visible'; document.dispatchEvent(new Event('visibilitychange')); });
    await page.waitForTimeout(60);
    await forward(page, 3100);
    return { after: (await gets()) - n0, note: await page.evaluate(() => (document.querySelector('.deck-panel .upl-err') || {}).textContent || ''),
             errors: page.__errors };
  },
  // 그 대화에 질문이 도는 동안 끝난 잡 — 끝(받기 링크)은 곧바로 보이고 칸은 묻기를 멈춘다. 대화 알림은 줄이 다음 차례들에 남긴다(WD-D75)
  async deferred(browser) {
    const page = await open(browser);
    const PENDING = { ...DONE, next: 'finish', notice: null, noticed: false, notice_pending: true, deferred: true };
    // 맡길 때 줄이 목록을 한 번 못 읽는다 — 줄은 쉬고 있다(끝나지 않은 잡을 본 적이 없다). 칸이 끝을 보고 알려야 줄이 넘겨받는다
    await page.evaluate(([q, r, f, p, d]) => { window.__created = q; window.__states = [r, f]; window.__advQueue = [p, p, p];
      window.__advanced = d; window.__list = [q]; window.__listFail = 1; }, [QUEUED, RENDERING, FINISH, PENDING, DONE]);
    await page.locator('.deck-go').first().click();
    await page.locator('.deck-panel .upl-go').click();
    await page.getByText('발표자료 만드는 중').first().waitFor();
    await forward(page, 3100);
    await forward(page, 3100);
    await page.getByText('발표자료를 만들었습니다').first().waitFor();
    const links = await page.evaluate(() => Array.from(document.querySelectorAll('.deck-panel .deck-file')).map((a) => a.getAttribute('href')));
    const gets = async () => (await calls(page, '/agent/deck/jobs/')).filter((c) => c.method === 'GET').length;
    const g0 = await gets();
    // 칸이 끝을 보면 줄에 알린다 — 줄이 곧바로 한 번 걷는다(아직 질문이 돈다)
    const mid = { counts: await text(page, 'counts') };
    await forward(page, 10500);                                          // 줄의 차례 — 아직 질문이 돈다(알림을 또 미룬다)
    mid.strip = await page.evaluate(() => !!document.querySelector('.deck-resume'));
    mid.counts2 = await text(page, 'counts');
    await forward(page, 10500);                                          // 다음 차례 — 질문이 끝났다(알림)
    await page.waitForFunction(() => document.getElementById('lastA').textContent.includes('발표자료를 만들었습니다'));
    return { links, mid, spotGets: (await gets()) - g0, counts: await text(page, 'counts'),
             advances: (await calls(page, '/agent/deck/jobs/')).filter((c) => c.url.endsWith('/advance')).length, errors: page.__errors };
  },
  // 심의 결과 카드의 RA 링크 — RA 가 준 주소면 그리로 바로, 없는(옛) 카드는 눌렀을 때 포털에 물어(세션을 되살려) 연다. 못 물으면 RA 첫 화면(WD-D78)
  async raCard(browser) {
    const before = () => {
      const k = 'hwax.chat.u1@corp.example.conversations';
      const convs = JSON.parse(localStorage.getItem(k));
      const d = (outcome) => ({ role: 'assistant', content: '결정문', ts: 5,
        delib: { turns: [{ round: 1, persona: 'mech', say: '말' }], decision: '결정문', outcome } });
      convs[0].messages.push(d({ report_id: 58, url: '/w/team-cae/reports/58', title: '새 카드' }), d({ report_id: 59, title: '옛 카드' }),
                             d({ report_id: 60, url: '/w/../reports/60', title: '틀린 주소' }),
                             d({ report_id: 61, url: '/w/team-cae/reports/62', title: '다른 번호' }));
      localStorage.setItem(k, JSON.stringify(convs));
      window.__opened = [];
      window.__replaced = [];
      window.open = (u, t, f) => {
        const w = { opener: 'me', location: { replace: (x) => window.__replaced.push(x) } };
        window.__opened.push({ u, t, f, w });
        return w;
      };
    };
    const page = await open(browser, { before });
    const hrefs = await page.evaluate(() => Array.from(document.querySelectorAll('.dv-card.report')).map((a) => a.getAttribute('href')));
    const early = (await calls(page, '/agent/ra/')).length;
    await page.evaluate(() => { window.__raOpen401 = 1; window.__raOpenUrl = '/report-archive/w/team-x/reports/59'; });
    await page.locator('.dv-card.report').nth(1).click();
    await page.waitForFunction(() => window.__replaced.length === 1);
    const first = await page.evaluate(() => ({ opened: window.__opened.map((o) => o.u), opener: window.__opened[0].w.opener,
                                               replaced: [...window.__replaced] }));
    const refreshed = (await calls(page, '/auth/refresh')).length;
    await page.evaluate(() => { window.__raOpenStatus = 403; });
    await page.locator('.dv-card.report').nth(1).click();
    await page.waitForFunction(() => window.__replaced.length === 2);
    await page.evaluate(() => { window.__raOpenStatus = 0; window.__raOpenUrl = 'https://evil.example/x'; });
    await page.locator('.dv-card.report').nth(1).click();
    await page.waitForFunction(() => window.__replaced.length === 3);
    return { hrefs, early, first, refreshed, denied: await page.evaluate(() => window.__replaced[1]),
             outside: await page.evaluate(() => window.__replaced[2]),
             asked: (await calls(page, '/agent/ra/reports/')).map((c) => c.url), errors: page.__errors };
  },
  // 팝업이 막힌 브라우저(window.open 이 null) — 옛 카드를 누르면 링크의 기본 이동(RA 첫 화면 · 새 탭)이 그대로 간다. 기다린 뒤의 window.open 은
  // 사용자 동작 밖이라 또 막힌다 — 종전엔 기본 이동을 막아 아무 일도 없었다(3차 적대 검토, WD-D84)
  async raCardBlocked(browser) {
    const before = () => {
      const k = 'hwax.chat.u1@corp.example.conversations';
      const convs = JSON.parse(localStorage.getItem(k));
      convs[0].messages.push({ role: 'assistant', content: '결정문', ts: 5,
        delib: { turns: [{ round: 1, persona: 'mech', say: '말' }], decision: '결정문', outcome: { report_id: 59, title: '옛 카드' } } });
      localStorage.setItem(k, JSON.stringify(convs));
      window.__opens = 0;
      window.open = () => { window.__opens += 1; return null; };
      // React 의 손잡이 뒤(bubble — window 가 마지막)에서 기본 이동이 막혔는지 적고, 시험은 실제 새 탭을 막는다
      window.addEventListener('click', (e) => {
        if (e.target && e.target.closest && e.target.closest('.dv-card.report')) { window.__prevented = e.defaultPrevented; e.preventDefault(); }
      });
    };
    const page = await open(browser, { before });
    const card = page.locator('.dv-card.report').first();
    const attrs = await card.evaluate((a) => ({ href: a.getAttribute('href'), target: a.getAttribute('target'), rel: a.getAttribute('rel') }));
    await card.click();
    await page.waitForTimeout(150);
    return { attrs, prevented: await page.evaluate(() => window.__prevented), opens: await page.evaluate(() => window.__opens),
             asked: (await calls(page, '/agent/ra/reports/')).length, errors: page.__errors };
  },
  // 숨긴 잡도 끝 알림을 남긴다 — 줄은 그 잡을 계속 한 걸음씩 가되 화면에는 보이지 않는다(WD-D59)
  async dismissedFinish(browser) {
    const page = await open(browser);
    await page.evaluate(([f, d]) => { window.__list = [{ ...f, dismissed: true }]; window.__advanced = d; }, [FINISH, DONE]);
    await page.evaluate(() => window.dispatchEvent(new Event('hwax:deck-changed')));
    await page.waitForFunction(() => document.getElementById('lastA').textContent.includes('발표자료를 만들었습니다'));
    return { strip: await page.evaluate(() => !!document.querySelector('.deck-resume')), counts: await text(page, 'counts'),
             advances: (await calls(page, '/agent/deck/jobs/')).filter((c) => c.url.endsWith('/advance')).length, errors: page.__errors };
  },
  // 숨긴 잡만 남아도 다시 묻기를 이어 간다 — 끝나면 그때 알림
  async dismissedLater(browser) {
    const page = await open(browser);
    const RUN = { ...base, state: 'rendering', step: '만드는 중', progress: 80, elapsed_s: 4, dismissed: true };
    await page.evaluate((r) => { window.__list = [r]; }, RUN);
    await page.evaluate(() => window.dispatchEvent(new Event('hwax:deck-changed')));
    await page.waitForTimeout(80);
    const stripWhileRunning = await page.evaluate(() => !!document.querySelector('.deck-resume'));
    await page.evaluate(([f, d]) => { window.__list = [{ ...f, dismissed: true }]; window.__advanced = d; }, [FINISH, DONE]);
    await forward(page, 10500);
    await page.waitForFunction(() => document.getElementById('lastA').textContent.includes('발표자료를 만들었습니다'));
    return { stripWhileRunning, counts: await text(page, 'counts'), errors: page.__errors };
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
    out = tmp_path_factory.mktemp("wdadeck")
    (out / "harness.tsx").write_text(_HARNESS.replace("__FE__", str(FE)), encoding="utf-8")
    for name, body in (("build.cjs", _BUILD), ("stub.js", _STUB), ("drive.cjs", _DRIVE)):
        (out / name).write_text(body, encoding="utf-8")
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


def test_심의_꼴이_없으면_보고서_저장_답은_숨고_RA_보내기_알림만_선다(seen):
    s = seen("spots")
    assert s["without"] == 1 and "보고서 초안을 만들었습니다" in s["titles"][0], "사용자 결정 U-6 — 심의 형식이 설 때까지 숨긴다"
    assert s["withFormat"] == 2


def test_분석_루틴의_RA_초안에도_단추가_서고_심의_보고서와_같은_문에_걸린다(seen):
    """M2(체크리스트 184행) — 루틴 RA 초안은 deliberation 템플릿이다. 심의 꼴이 active 가 아니면 숨고(U-6 · U-7), 서면 루틴 칸 안에 하나만.
    초안 번호가 원장에만 있어도(끝에 묻는 루틴 · 새로고침 뒤의 포인터) 원장을 읽은 뒤 선다."""
    s = seen("routine")
    assert s["without"] == 1, "심의 꼴이 없으면 루틴 초안의 단추도 숨는다(RA 보내기 알림만 선다)"
    assert s["total"] == 3 and s["inRoutine"] == 1 and s["inMsg"] == 1, "'/보고서' · RA 알림 · 루틴 — 루틴 메시지에는 단추가 하나뿐이다"
    assert s["create"] == {"report_id": 91, "conversation_id": "srv-A", "targets": ["pptx", "pdf"], "doc_style": "report"}
    assert s["create2"]["report_id"] == 92, "원장이 준 초안 번호로 맡긴다"


def test_끝난_잡의_칸에서_PDF_를_미리보고_사본을_지운다(seen):
    """M2(체크리스트 186행) — 미리보기는 포털 경로를 틀에 싣는다(WDA 주소가 아니다). 틀에는 sandbox 속성이 없다 — 속성이 있으면 Chromium 의
    PDF 보기가 서지 않고, 격리는 포털의 응답 머리(CSP sandbox)가 한다. 누른 뒤 포털에 한 번 물어(세션을 되살린다) 받은 주소만 싣는다."""
    s = seen("tools")
    assert s["before"] == 0, "누르기 전에는 틀이 없다(PDF 를 미리 받지 않는다)"
    assert s["frame"] == {"src": f"/agent/deck/jobs/{'f' * 32}/preview", "sandbox": False, "referrer": "no-referrer"}
    assert s["asked"] == 1 and s["closed"] == 0
    assert s["del"] == [f"/agent/deck/jobs/{'f' * 32}"] and len(s["confirmed"]) == 1 and "되돌릴 수 없" in s["confirmed"][0]
    assert s["after"]["links"] == 0 and "사본을 지웠습니다" in s["after"]["text"]
    assert "PDF 미리보기" not in s["after"]["buttons"] and "사본 지우기" not in s["after"]["buttons"] and "다시 만들기" in s["after"]["buttons"]


def test_지우기가_없는_WDA_면_단추가_없고_거절은_까닭을_보인다(seen):
    s = seen("toolsRefused")
    assert "사본 지우기" not in s["noDelButtons"] and "PDF 미리보기" in s["noDelButtons"]
    assert "만드는 중" in s["refused"]["err"] and s["refused"]["links"] == 2, "WDA 가 거절하면 잡은 그대로다"


def test_실패한_잡의_다시_시도는_새_잡의_진행을_잇는다(seen):
    s = seen("retry")
    assert "다시 시도" in s["buttons0"] and "다시 만들기" in s["buttons0"]
    assert s["retried"] == [f"/agent/deck/jobs/{'f' * 32}/retry"] and s["creates"] == 0, "다시 시도는 만들기 창구를 부르지 않는다"
    assert s["polled"] is True, "돌려받은 새 잡의 진행을 묻는다"


def test_대화에_남은_알림_아래에서도_미리보기_지우기_다시_시도에_닿는다(seen):
    s = seen("noticeTools")
    assert s["offButtons"] == 0, "스위치가 꺼진 박스에서는 알림 아래에 아무것도 서지 않는다"
    assert s["early"] == 0, "누르기 전에는 잡을 묻지 않는다(알림마다 묻지 않는다)"
    assert s["buttons1"] == ["PDF 미리보기", "사본 지우기"]
    assert s["src"] == f"/agent/deck/jobs/{'f' * 32}/preview"
    assert s["retried"] == 1 and s["strip"] is True, "다시 시도한 잡의 진행은 입력창 위 줄이 잇는다"


def test_권한이나_스위치가_없으면_단추가_없다(seen):
    s = seen("hidden")
    assert s["noPerm"] == 0 and s["noPermCalls"] == 0, "권한이 없으면 상태도 묻지 않는다"
    assert s["off"] == 0


def test_맡기면_진행을_보이고_끝나면_그_대화에_알림과_포털_받기_링크(seen):
    s = seen("stay")
    assert s["opts"] == {"checked": [True, True, False, False, False], "style": "report"}, "기본 PPT + PDF · 정식 보고서"
    assert s["create"] == {"report_id": 41, "conversation_id": "srv-A", "targets": ["pptx", "pdf"], "doc_style": "report"}
    assert "만드는 중" in s["mid"]
    assert s["links"] == [f"/agent/deck/jobs/{'f' * 32}/files/pptx", f"/agent/deck/jobs/{'f' * 32}/files/pdf"], "받기는 포털 경로 — WDA 주소가 아니다"
    assert s["advances"] == 1
    assert s["before"] == "srv-A:3,srv-B:2" and s["after"] == "srv-A:4,srv-B:2" and "발표자료를 만들었습니다" in s["last"]
    assert s["noticeLinks"] == s["links"], "대화에 남은 알림의 받기 링크도 눌린다"


def test_다른_대화로_옮겨_가도_알림은_단추를_누른_대화에(seen):
    s = seen("away")
    assert s["active"] == "srv-B"
    assert s["counts"] == "srv-A:4,srv-B:2", "알림은 A 에 — 지금 보는 B 가 아니다"
    assert s["advances"] == 1


def test_목록을_한_번_못_읽어도_줄이_다시_묻고_알림을_남긴다(seen):
    s = seen("blip")
    assert s["mid"]["strip"] is True and "발표자료를 만들었습니다" not in s["mid"]["last"], "못 읽은 차례에는 줄을 그대로 둔다"
    assert s["counts"] == "srv-A:4,srv-B:2", "다음 차례에 다시 물어 끝 알림을 A 에"
    assert s["lists"] >= 3


def test_질문이_도는_대화의_잡은_끝을_곧바로_보이고_알림은_줄이_나중에(seen):
    """2차 적대 검토 D — 미룸이 긴 턴 내내 잡을 열어 두었다(링크 없이 · 3초마다 · 상한을 먹으며). 끝은 곧바로 보이고 칸은 묻기를 멈추며,
    대화 알림은 줄이 다음 차례들에 남긴다(WD-D75)."""
    s = seen("deferred")
    assert s["links"] == [f"/agent/deck/jobs/{'f' * 32}/files/pptx", f"/agent/deck/jobs/{'f' * 32}/files/pdf"], "받기 링크는 곧바로"
    assert s["spotGets"] == 0, "끝을 적은 잡은 칸이 더 묻지 않는다"
    assert s["mid"]["counts"] == "srv-A:3,srv-B:2" and s["mid"]["counts2"] == "srv-A:3,srv-B:2", "알림은 아직 — 서버가 미뤘다"
    assert s["mid"]["strip"] is False, "끝을 적은 잡은 '만들고 있는 발표자료' 줄에 보이지 않는다"
    assert s["counts"] == "srv-A:4,srv-B:2" and s["advances"] == 4, "칸 한 번 · 줄이 넘겨받아 곧바로 한 번 · 차례마다 — 알림 한 건"


def test_심의_결과_카드는_RA_주소로_바로_열고_옛_카드는_포털에_물어_연다(seen):
    """2차 적대 검토 — 카드가 포털 길(/open)로 새 탭을 열어 15분 세션이 지나면 401 JSON, 권한이 없으면 403 JSON 이 떴다(WD-D78)."""
    s = seen("raCard")
    assert s["hrefs"] == ["/report-archive/w/team-cae/reports/58", "/report-archive/", "/report-archive/", "/report-archive/"], \
        "주소가 맞고 번호가 같으면 바로 · 아니면 RA 첫 화면"
    assert s["early"] == 0, "그리는 동안 포털에 묻지 않는다"
    assert s["first"]["opened"] == [""] and s["first"]["opener"] is None, "누른 순간 빈 탭을 열고(팝업 막기) 오프너를 끊는다"
    assert s["first"]["replaced"] == ["/report-archive/w/team-x/reports/59"] and s["refreshed"] == 1, "세션이 지났으면 되살려 다시 묻는다"
    assert s["denied"] == "/report-archive/", "못 물으면 JSON 대신 RA 첫 화면"
    assert s["outside"] == "/report-archive/", "포털의 RA 경로가 아닌 답은 따르지 않는다"
    assert s["asked"] == ["/agent/ra/reports/59/open"] * 4


def test_팝업이_막히면_옛_카드는_링크의_기본_이동으로_RA_첫_화면을_연다(seen):
    """3차 적대 검토(WD-D84) — 빈 탭을 못 열면(window.open 이 null) 기본 이동을 막지 않는다 · 포털에 묻지 않는다 · 옛 카드는 진짜 링크다."""
    s = seen("raCardBlocked")
    assert s["attrs"] == {"href": "/report-archive/", "target": "_blank", "rel": "noopener"}, s["attrs"]
    assert s["opens"] == 1 and s["prevented"] is False, "빈 탭을 못 열면 링크가 그대로 간다"
    assert s["asked"] == 0, "열 탭이 없으면 묻지 않는다"


def test_숨긴_잡도_끝_알림을_남기고_줄에는_보이지_않는다(seen):
    s = seen("dismissedFinish")
    assert s["strip"] is False and s["advances"] == 1 and s["counts"] == "srv-A:4,srv-B:2"


def test_숨긴_잡만_남아도_다시_묻기를_이어_간다(seen):
    s = seen("dismissedLater")
    assert s["stripWhileRunning"] is False, "숨긴 잡은 줄에 보이지 않는다"
    assert s["counts"] == "srv-A:4,srv-B:2", "그래도 다음 차례에 다시 물어 끝 알림을 남긴다"


def test_끝난_잡에도_다시_만들기가_있고_again_을_보낸다(seen):
    s = seen("regen")
    assert s["againBtn"] == 1 and s["againBody"]["again"] is True


def test_지워진_파일은_링크_대신_다시_만들기(seen):
    s = seen("expired")
    assert s["links"] == 0 and "지워졌습니다" in s["text"] and "다시 만들기" in s["text"]


def test_다른_대화의_잡을_받으면_알림이_갈_대화를_말한다(seen):
    s = seen("elsewhere")
    assert "「B」 대화에" in s["text"] and "그 대화에서 맡긴 같은 발표자료" in s["text"] and "이 대화에" not in s["text"]


def test_자리표시자_대화에는_알림을_붙이지_않고_열_때_서버_사본을_읽는다(seen):
    s = seen("placeholder")
    assert s["beforeOpen"] == "[]", "자리표시자에 화면 알림을 붙이지 않는다"
    assert s["detailGets"] >= 1 and "SAVED-ON-OTHER-DEVICE" in s["afterOpen"] and "NOTICE-FROM-SERVER" in s["afterOpen"]


def test_안쪽_챗_제공자가_받은_알림을_바깥_제공자의_대화도_받는다(seen):
    s = seen("nested")
    assert "발표자료를 만들었습니다" in s["lastA"] and s["counts"] == "srv-A:4,srv-B:2"


def test_숨은_탭은_천천히_묻고_보이면_곧_돌아온다(seen):
    s = seen("hiddenTab")
    assert s["hidden30"] == 0, "숨은 탭에서 10초 박자로 묻지 않는다"
    assert s["hidden105"] >= 1, "숨은 탭도 아주 멈추지는 않는다(10배 박자)"
    assert s["shown"] >= 1, "보이면 곧 박자로 돌아온다"


def test_창구가_404_면_줄이_묻기를_멈춘다(seen):
    s = seen("stop404")
    assert s["after"] == 0 and s["strip"] is False


def test_단추_칸도_404_면_묻기를_멈추고_까닭을_말한다(seen):
    s = seen("spot404")
    assert s["after"] == 0 and "멈춥니다" in s["note"]
