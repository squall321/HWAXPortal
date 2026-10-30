# 챗의 켜 둔 분석 루틴을 헤드리스 브라우저에서 실제 ChatProvider · 입력창 · 고르기 창 · 툴바 버튼으로 돌려 본다 — 서버는 띄우지 않는다(가짜 fetch, docs/analysis-routines R3)
"""왜 — 켜 둔 루틴은 화면 상태다. 보내는 꼴(덧붙인 말 · 이어서 · RA 올리기), 실패한 뒤 값이 살아남는지, 창을 닫는 손짓, 툴바의 한 번 누름,
계정이 바뀔 때가 모두 '누르고 보내는' 차례 안에서 갈린다. 글 맞대기로는 차례를 못 본다 — 실제 컴포넌트를 묶어 빈 문서에 올리고 눌러 본다
(test_chat_ppt_in_browser · test_delib_stream_in_browser 와 같은 길). 고르기 창의 '배경을 눌러 닫기' 는 자리(카드 밖 · 안)가 판정이라 실제
CSS(tokens · globals · chat · ui)를 함께 싣는다.

  · 덧붙인 말(R3 C3) — 루틴을 켜 두고 사람이 쓴 글이 routine.note 로 간다. 글 없이 보낼 때 싣는 '루틴: <제목>' 은 덧붙인 말이 아니다
    (실행기가 그 글을 '사용자가 덧붙인 말' 로 단계 · 인사이트 프롬프트에 실었다).
  · 이어서는 run_id 만, 끝난 실행의 'RA 초안 올리기' 는 upload_ra 를 더한다(R3 C4).
  · 실행을 만들기 전의 거절(포털 _coerce 422 · 중계 422 · 동시 상한)은 보낸 값을 다시 켜 두고 까닭을 칸 옆에 보인다. '다시 시도' 는 고친 값과
    처음 덧붙인 말로 보낸다(반대 검토 #14 — 거절 하나에 적은 값이 다 사라졌고 다시 시도는 같은 거절을 되풀이했다). 실행이 생긴 뒤 · 받던 중에
    끊긴 것(실행이 생겼는지 모른다)은 되살리지 않는다.
  · 칸 안에서 끌어 고르다 카드 밖에서 떼도 창이 닫히지 않는다(#33).
  · 툴바(ChatActionBar)의 한 번 누름 보내기는 켜 둔 루틴을 싣지도 쓰지도 않는다(#35).
  · 계정이 바뀌면(로그아웃 · 다른 사람의 로그인) 켜 둔 루틴과 입력을 버린다 — 보낸 뒤 바뀐 턴의 실패도 되살리지 않는다(#36).
  · 덧붙인 말은 선에서 2,000자(코드 포인트)로 자른다 — 중계 RoutineReq.note 상한을 넘으면 보내기 전체가 422 였다. 사람 글(message)은 그대로다.
  · 실행 id 를 받기 전에 ■ 로 끊었거나 받던 중에 끊겼거나 실행이 생겼을 수 있는 오류(게이트웨이 · 실행기 · 침묵 한도)로 끝난 루틴 턴의 '다시
    시도' 는 내 실행 목록에서 같은 루틴 · 이 대화의 실행 가운데 이 대화의 메시지가 아직 가리키지 않는 가장 새것을 찾아 잇는다(실행은 서버에서
    돈다 — 다시 보내면 둘이다). 시각으로 가르지 않는다 — 서버와 이 PC 의 시계가 어긋나면 그 턴의 실행을 놓치거나 앞 턴의 실행에 붙었다(2차 #6 ·
    #13 · #11). 못 찾거나 목록을 못 읽으면 보낸 요청을 다시 보낸다.
  · 루틴 턴이 흐르는 동안 ■ 힌트는 '화면 연결만 끊고 루틴은 서버에서 계속 돈다(그치려면 ‘멈춤’)' 를 말한다. 실행이 이미 끝난 턴(RA 초안
    올리기 · 끝난 계획)은 '멈춤' 을 가리키지 않는다(2차 #16).
  · 받는 중에는 누른 때의 함수로 부른 잇기도 둘째 스트림을 열지 않는다(2차 #12). 켜 둔 루틴과 붙인 그림 · 문서는 함께 보내지 않고 까닭을
    말하며, 루틴 턴은 붙인 것을 싣지도 비우지도 않는다(2차 #14). 고르기 창은 고른 뒤 포커스를 옮기고 무엇을 열었는지 들린다(2차 #17).
"""
import json
import subprocess

import pytest

from tests.test_delib_stream_in_browser import FE, pytestmark  # noqa: F401 — 같은 도구가 없으면 같이 건너뛴다

# 화면 뼈대 — 실제 입력창(루틴 알약 포함) · 툴바 버튼 · 챗 상태. 사용자는 window.__setUser 로 바꾼다(이메일 로그인처럼 페이지를 다시 읽지 않는다).
_HARNESS = r"""
import { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import '__FE__/src/styles/tokens.css';
import '__FE__/src/styles/globals.css';
import '__FE__/src/styles/chat.css';
import { AuthContext } from '__FE__/src/auth/AuthContext';
import type { User } from '__FE__/src/auth/types';
import { ChatProvider, useChat } from '__FE__/src/state/ChatContext';
import { Composer } from '__FE__/src/components/chat/Composer';
import { ChatActionBar } from '__FE__/src/components/chat/ChatActionBar';

// serverKind — 서버 대화를 만드는 화면(챗 페이지와 같다 — 루틴 턴에 conversation_id 가 실린다). hint — 입력창 힌트 줄(챗 페이지와 같다).
type Opts = { serverKind?: 'chat'; hint?: boolean };
type W = { __ctx?: unknown; __setUser?: (who: string) => void; __mount?: (o?: Opts) => void };
const w = window as unknown as W;

function Probe() {
  const chat = useChat();
  w.__ctx = { resumeRoutine: chat.resumeRoutine, setAttachedImages: chat.setAttachedImages, setAttachedDocs: chat.setAttachedDocs };
  return (
    <div id="probe">
      <span id="streaming">{String(chat.streaming)}</span>
      <span id="rtstream">{String(chat.routineStreaming)}</span>
      <span id="armed">{chat.armedRoutine ? JSON.stringify(chat.armedRoutine) : ''}</span>
      <ol id="msgs">
        {chat.messages.map((m) => (
          <li key={m.id} data-role={m.role} data-live={m.streaming ? '1' : ''} data-error={m.error ?? ''}
              data-run={m.routine?.run_id ?? ''}>{m.text}</li>
        ))}
      </ol>
      <button id="retry" type="button" onClick={chat.retryLast}>retry</button>
    </div>
  );
}

const USERS: Record<string, User> = {
  a: { subject: 'alice@corp.example', email: 'alice@corp.example', display_name: 'A', groups: [], entitlements: ['feat:routines'] },
  b: { subject: 'bob@corp.example', email: 'bob@corp.example', display_name: 'B', groups: [], entitlements: ['feat:routines'] },
};

function Root({ serverKind, hint }: Opts) {
  const [who, setWho] = useState('a');
  w.__setUser = setWho;
  const user = USERS[who] ?? null;
  return (
    <AuthContext.Provider
      value={{ user, status: user ? 'authenticated' : 'unauthenticated', login: () => undefined,
               logout: async () => undefined, refresh: async () => undefined }}
    >
      <MemoryRouter>
        <ChatProvider storagePrefix="hwax.chat" serverKind={serverKind}>
          {user && (
            <>
              <div id="bar"><ChatActionBar /></div>
              <Composer showRoutine showHint={hint} />
            </>
          )}
          <Probe />
        </ChatProvider>
      </MemoryRouter>
    </AuthContext.Provider>
  );
}
w.__mount = (o = {}) => createRoot(document.getElementById('root')!).render(<Root {...o} />);
"""

# CSS 도 묶는다(bundle.css) — 고르기 창의 배경 · 카드 자리가 실제와 같아야 '카드 밖에서 뗐다' 가 뜻이 있다.
_BUILD = r"""
const { createRequire } = require('module');
const path = require('path');
const [FE, OUT] = process.argv.slice(2);
const fe = createRequire(path.join(FE, 'package.json'));
const esbuild = createRequire(fe.resolve('vite/package.json'))('esbuild');
esbuild.buildSync({
  entryPoints: [path.join(OUT, 'harness.tsx')], bundle: true, format: 'iife', outfile: path.join(OUT, 'bundle.js'),
  jsx: 'automatic', nodePaths: [path.join(FE, 'node_modules')], logLevel: 'error',
  // 글꼴(KaTeX 등)은 비운다 — 자리만 본다
  loader: { '.svg': 'dataurl', '.png': 'dataurl', '.woff2': 'empty', '.woff': 'empty', '.ttf': 'empty', '.eot': 'empty' },
  define: { 'import.meta.env': '{}', 'process.env.NODE_ENV': '"development"' },
});
"""

# 가짜 백엔드 — 루틴 목록 · 보기 · 준비도, 툴바 매니페스트(knox-bridge), 챗 스트림(__chatQueue 의 차례대로: 프레임 · 상태 코드 · 붙잡기),
# 서버 대화(만들면 conv-srv-1), 내 실행 목록(__runs 를 routine_id 로 거른다 · __runsStatus 면 그 상태로 거절 · __runsHold 면 __runsRelease 까지 붙잡는다).
_STUB = r"""
(() => {
  window.__calls = [];
  window.__chatQueue = [];
  const enc = new TextEncoder();
  const json = (body, status = 200) =>
    Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }));
  const sse = (start) =>
    Promise.resolve(new Response(new ReadableStream({ start }), { status: 200, headers: { 'Content-Type': 'text/event-stream' } }));
  const STEP = { id: 'anchor', title: '기준 키', kind: 'platform', backends: ['rootdesigndatahub'], goal: '기준 키를 찾는다',
                 tools: [], uses: [], expect: { keys: [] }, budget: { calls: 4, seconds: 60 },
                 blocked: { empty: 'continue', denied: 'skip', unavailable: 'skip' } };
  const ROW = { id: 'rt-swelling', owner_sub: 'alice@corp.example', title: '시장불량 원인 분석', visibility: 'all', latest_version: 3,
                updated_at: 1, mine: true, steps: [{ id: 'anchor', title: '기준 키', kind: 'platform', backends: ['rootdesigndatahub'] }],
                vars: [{ key: 'model', label: '모델' }] };
  const DETAIL = {
    routine: { id: 'rt-swelling', owner_sub: 'alice@corp.example', title: '시장불량 원인 분석', visibility: 'all', latest_version: 3, archived: 0 },
    version: { version_id: 'v3', version_no: 3, author_sub: 'alice@corp.example', created_at: 1, spec: {
      title: '시장불량 원인 분석', purpose: 'S26 의 스웰링 시장불량', visibility: 'all',
      vars: [{ key: 'model', label: '모델', type: 'string', required: true },
             { key: 'strict', label: '엄격', type: 'boolean', required: true },
             { key: 'limit', label: '건수', type: 'number', required: false },
             { key: 'laminate', label: '적층', type: 'json', required: false }],
      steps: [STEP], report: { title: '보고서', sections: ['anchor', 'insight'], ra: { upload: 'ask' } },
      limits: { minutes: 30, calls: 40 } } },
    versions: [], mine: true };
  const READY = { version_no: 3, steps: [{ step: 'anchor', state: 'allowed', backends: [], missing_tools: [], reason: '' }] };
  window.fetch = (url, init = {}) => {
    const u = String(url);
    const method = (init.method || 'GET').toUpperCase();
    let body = null;
    try { body = typeof init.body === 'string' ? JSON.parse(init.body) : null; } catch (e) { body = String(init.body); }
    window.__calls.push({ url: u, method, body });
    if (u.startsWith('/routines-api/routines?')) return json({ count: 1, routines: [ROW] });
    if (u.startsWith('/routines-api/routines/rt-swelling/readiness')) return json(READY);
    if (u.startsWith('/routines-api/routines/rt-swelling')) return json(DETAIL);
    if (u === '/systems') return json([{ id: 'knox-bridge', name: 'Knox', status: 'available', integration_type: 'proxy' }]);
    if (u === '/knox-bridge/ui/actions.json')
      return json({ schema: 'hwax.chat-actions/1', actions: [
        { id: 'mail', label: '메일 초안', kind: 'prompt', prompt: '이 답을 메일 초안으로 만들어 줘', mode: 'send' }] });
    if (u === '/agent/conversations') return json(method === 'POST' ? { id: 'conv-srv-1' } : { conversations: [] });
    if (u.startsWith('/routines-api/runs?')) {
      if (window.__runsStatus) return json({ detail: 'stub: 실행 목록을 못 읽었다' }, window.__runsStatus);
      const rid = new URLSearchParams(u.split('?')[1]).get('routine_id');
      const rows = (window.__runs || []).filter((r) => r.routine_id === rid);
      if (window.__runsHold) return new Promise((res) => { window.__runsRelease = () => res(json({ count: rows.length, runs: rows })); });
      return json({ count: rows.length, runs: rows });
    }
    if (u.startsWith('/agent/chat')) {
      const spec = window.__chatQueue.shift() || { frames: ['event: token\ndata: {"delta":"답"}\n\n', 'event: done\ndata: {}\n\n'] };
      if (spec.status) return json(spec.json || {}, spec.status);
      if (spec.hold)
        return sse((c) => {
          window.__push = (t) => c.enqueue(enc.encode(t));
          window.__end = () => c.close();
          window.__break = (m) => c.error(new TypeError(m));   // 받던 중의 끊김(프록시 · 재기동) — chat.api 가 stream_cut 으로 적는다
        });
      return sse((c) => { for (const f of spec.frames) c.enqueue(enc.encode(f)); c.close(); });
    }
    return json({ detail: 'stub: no route ' + u }, 404);
  };
})();
"""

# 시나리오 구동기 — 시나리오마다 새 탭이다. 실패는 그 시나리오에 적고 다음으로 간다.
_DRIVE = r"""
const { createRequire } = require('module');
const path = require('path');
const [FE, OUT] = process.argv.slice(2);
const { chromium } = createRequire(path.join(FE, 'package.json'))('@playwright/test');

const frame = (event, data) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
const DONE = frame('done', {});
const TITLE = '시장불량 원인 분석';
const LONG = '{"laminae": [{"mat": "CFRP", "t": 0.125, "angle": 0}, {"mat": "CFRP", "t": 0.125, "angle": 45}], "unit_system": "SI_mm"}';
const PLAN = { kind: 'plan', run_id: 'R9', routine_id: 'rt-swelling', version_no: 3, title: TITLE, purpose: '', state: 'running',
               resumed: false, steps: [], report: { title: '보고서', sections: [], upload: 'ask' } };
// 덧붙인 말 상한(2,000자)을 넘는 글 — 2,000번째 글자가 그림 글자라 UTF-16 으로 자르면 짝 없는 대리 글자가 남는다
const LONG_NOTE = '가'.repeat(1999) + '😀' + '나'.repeat(600);
// 실행 목록 한 줄 — 포털 routine_store.list_runs 가 고르는 칸 그대로에 conversation_id(withConv 가 거짓이면 뺀다 — 그 칸을 싣지 않는 포털)
const runRow = (id, conv, startedAt, withConv = true) => ({
  id, routine_id: 'rt-swelling', version_no: 3, title: TITLE, executor: 'chat', state: 'running', reason: null, calls: 0,
  started_at: startedAt, ended_at: null, ra_report_id: null, ...(withConv ? { conversation_id: conv } : {}) });

async function open(browser, opts = {}) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  page.setDefaultTimeout(10000);
  page.__errors = [];
  page.on('pageerror', (e) => page.__errors.push(String(e)));
  // 가로챈 주소로 빈 문서를 준다 — about:blank 에서는 document.cookie 가 막혀 apiFetch 의 CSRF 읽기가 던진다
  await page.route('http://harness.invalid/**', (r) =>
    r.fulfill({ contentType: 'text/html', body: '<!doctype html><html><body><div id="root"></div></body></html>' }));
  await page.goto('http://harness.invalid/');
  await page.addStyleTag({ path: path.join(OUT, 'bundle.css') });
  await page.addScriptTag({ path: path.join(OUT, 'stub.js') });
  await page.addScriptTag({ path: path.join(OUT, 'bundle.js') });
  await page.evaluate((o) => window.__mount(o), opts);
  await page.locator('textarea[aria-label="메시지 입력"]').waitFor();
  return page;
}
const box = (page) => page.locator('textarea[aria-label="메시지 입력"]');
const armed = (page) => page.evaluate(() => {
  const t = document.getElementById('armed').textContent;
  return t ? JSON.parse(t) : null;
});
const chats = (page) => page.evaluate(() => window.__calls.filter((c) => c.url.startsWith('/agent/chat')).map((c) => c.body));
const msgs = (page) => page.evaluate(() => Array.from(document.querySelectorAll('#msgs li')).map((li) =>
  ({ role: li.dataset.role, text: li.textContent, error: li.dataset.error, run: li.dataset.run })));
// 턴 k 개가 끝났다 — 챗 호출 k 번 · 메시지가 그려졌고(사람 + 답) 흐르는 답이 없다
async function turns(page, k, lis = 2 * k) {
  await page.waitForFunction(([k2, n]) => {
    const calls = window.__calls.filter((c) => c.url.startsWith('/agent/chat')).length;
    const items = Array.from(document.querySelectorAll('#msgs li'));
    return calls >= k2 && items.length >= n && items.every((li) => li.dataset.live !== '1')
      && document.getElementById('streaming').textContent === 'false';
  }, [k, lis]);
}
const settle = (page) => page.waitForTimeout(250);
const field = (page, key) => page.locator('.rp-field')
  .filter({ has: page.locator('code', { hasText: new RegExp('^' + key + '$') }) })
  .locator('input, select, textarea').first();
// 고르기 창을 열어 입력 칸까지 — 켜 둔 것이 있으면 바로 그 칸이고, 없으면 목록에서 루틴을 고른다
async function openForm(page) {
  await page.locator('.tool-routine .tool-pill').click();
  await page.locator('.rp-row, .rp-fields').first().waitFor();
  if (!(await page.locator('.rp-fields').count())) await page.locator('.rp-row').first().click();
  await page.locator('.rp-fields').waitFor();
}
async function arm(page, vals) {
  await openForm(page);
  for (const [k, v] of Object.entries(vals)) {
    const el = field(page, k);
    if ((await el.evaluate((x) => x.tagName)) === 'SELECT') await el.selectOption(v);
    else await el.fill(v);
  }
  await page.locator('.rp-on').click();
  await page.locator('.rp-card').waitFor({ state: 'detached' });
}
const form = (page) => page.evaluate(() => Object.fromEntries(Array.from(document.querySelectorAll('.rp-field')).map((f) => {
  const c = f.querySelector('input, select, textarea');
  return [f.querySelector('code').textContent, {
    tag: c.tagName, type: c.getAttribute('type') || '', value: c.value, invalid: c.getAttribute('aria-invalid') || '',
    options: c.tagName === 'SELECT' ? Array.from(c.options).map((o) => o.value) : null,
    err: (f.querySelector('.rp-err') || {}).textContent || '' }];
})));
const pill = (page) => page.evaluate(() => {
  const b = document.querySelector('.tool-routine .tool-pill');
  return { cls: b.className, title: b.title, text: b.textContent };
});
const queue = (page, spec) => page.evaluate((s) => window.__chatQueue.push(s), spec);
async function send(page, text) {
  await box(page).fill(text);
  await box(page).press('Enter');
}
// 입력창 힌트 줄과 ■ 단추 풀이(없으면 '')
const hint = (page) => page.evaluate(() => ({
  hint: (document.querySelector('.composer-hint') || {}).textContent || '',
  stop: (document.querySelector('button[aria-label="응답 중지"]') || {}).title || '',
  routine: document.getElementById('rtstream').textContent,
}));
const runsAsked = (page) => page.evaluate(() => window.__calls.filter((c) => c.url.startsWith('/routines-api/runs')).map((c) => c.url));
// 입력창의 알림 줄(.upl-err) · 붙인 그림 칩 수 · 지금 포커스가 있는 요소
const alerts = (page) => page.evaluate(() => Array.from(document.querySelectorAll('.upl-err')).map((e) => e.textContent));
const chips = (page) => page.locator('.img-chip').count();
const focused = (page) => page.evaluate(() => {
  const a = document.activeElement;
  return { tag: a ? a.tagName : '', cls: (a && a.className) || '', text: ((a && a.textContent) || '').trim().slice(0, 40) };
});
// 1×1 PNG — 붙인 그림 칩이 그릴 수 있는 작은 그림
const PNG = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==';
const IMG = { name: 'crack.png', mime: 'image/png', dataUrl: PNG, width: 1, height: 1, bytes: 68 };
const DOC = { name: '시험성적서.md', text: '스웰링 3mm', chars: 9, truncated: false };
// 루틴 프레임만 보내고 도는 채로 끝나는 이어서 스트림(그 턴의 답이 그 실행을 가리킨다)
const resumed = (id) => ({ frames: [frame('routine', { ...PLAN, run_id: id, resumed: true }),
                                    frame('routine', { kind: 'done', run_id: id, state: 'running' }), DONE] });
// 켜 둔 값으로 붙잡힌 스트림을 보내고 첫 routine 프레임 전에 ■ — 보낸 때(이 PC 시계, 초)를 돌려준다
async function stopArmed(page, vals, text) {
  await arm(page, vals);
  await page.evaluate(() => { window.__push = undefined; });
  await queue(page, { hold: true });
  await send(page, text);
  await page.waitForFunction(() => typeof window.__push === 'function');
  const at = await page.evaluate(() => Date.now());
  await page.locator('button[aria-label="응답 중지"]').click();
  await page.waitForFunction(() => document.getElementById('streaming').textContent === 'false');
  return Math.floor(at / 1000);
}
// 루틴을 켜 두고 붙잡힌 스트림으로 보낸 뒤 첫 routine 프레임 전에 ■ — 보낸 때(이 PC 시계, 초)를 돌려준다
async function stopBeforeRun(page, text) {
  await arm(page, { model: 'S26', strict: 'true' });
  await page.evaluate(() => { window.__push = undefined; });
  await queue(page, { hold: true });
  await send(page, text);
  await page.waitForFunction(() => typeof window.__push === 'function');
  const at = await page.evaluate(() => Date.now());
  await page.locator('button[aria-label="응답 중지"]').click();
  await page.waitForFunction(() => document.getElementById('streaming').textContent === 'false');
  return Math.floor(at / 1000);
}

const SCENARIOS = {
  // 덧붙인 말 — 사람이 쓴 글은 note 로, 글 없이 보낸 '루틴: <제목>' 은 note 가 아니다. 칸의 형도 여기서 본다.
  async note(browser) {
    const page = await open(browser);
    await openForm(page);
    const fields = await form(page);
    await page.locator('.rp-x').click();
    await arm(page, { model: 'S26', strict: 'true', limit: '9007199254740993' });
    const armed1 = await armed(page);
    await send(page, '북미 모델만, 3분기 이후');
    await turns(page, 1);
    const after1 = await armed(page);
    await arm(page, { model: 'S26', strict: 'false' });
    await page.locator('button[aria-label="전송"]').click();
    await turns(page, 2);
    return { fields, armed1, after1, chats: await chats(page), msgs: await msgs(page), errors: page.__errors };
  },
  // 이어서 · RA 초안 올리기 — 화면(RoutineView)이 부르는 resumeRoutine 그대로
  async resume(browser) {
    const page = await open(browser);
    await page.evaluate((t) => window.__ctx.resumeRoutine('R-77', t), TITLE);
    await turns(page, 1);
    await page.evaluate((t) => window.__ctx.resumeRoutine('R-77', t, { uploadRa: true }), TITLE);
    await turns(page, 2);
    return { chats: await chats(page), msgs: await msgs(page), armed: await armed(page), errors: page.__errors };
  },
  // 실행을 만들기 전의 거절(포털 _coerce 가 게이트웨이를 거쳐 routine_gateway 로) — 값이 살고 까닭이 칸 옆에, 고쳐서 다시 시도
  async reject(browser) {
    const page = await open(browser);
    await arm(page, { model: 'S26', strict: 'false', limit: '1000', laminate: '{"a": 1}' });
    const reason = "입력 엄격(strict) — strict: 참·거짓이 아니다 — 'false'";
    await queue(page, { frames: [frame('error', { code: 'routine_gateway', message: reason }), DONE] });
    await send(page, '북미만');
    await turns(page, 1);
    await settle(page);
    const rearmed = await armed(page);
    const pill1 = await pill(page);
    if (!rearmed) return { rearmed, pill1, errors: page.__errors };   // 되살리지 않았다 — 고칠 것이 없다(시험이 까닭을 말한다)
    await openForm(page);
    const reopened = await form(page);
    const top_err = await page.evaluate(() =>
      Array.from(document.querySelectorAll('.rp-body > .rp-err')).map((e) => e.textContent));
    await field(page, 'strict').selectOption('true');
    await page.locator('.rp-on').click();
    await page.locator('.rp-card').waitFor({ state: 'detached' });
    const fixed = await armed(page);
    const pill2 = await pill(page);
    await page.locator('#retry').click();
    await turns(page, 2);
    await settle(page);
    return { rearmed, pill1, reopened, top_err, fixed, pill2, after_retry: await armed(page), chats: await chats(page),
             msgs: await msgs(page), errors: page.__errors };
  },
  // 그 밖의 거절 · 실패 — 중계 422(검증 거절), 손대지 않고 다시 시도, 실행이 생긴 뒤의 오류, RA 올리기 턴의 다시 시도
  async reject_more(browser) {
    const page = await open(browser);
    await arm(page, { model: 'S26', strict: 'true' });
    await queue(page, { status: 422, json: { detail: [{ loc: ['body', 'routine', 'note'],
      msg: 'String should have at most 2000 characters', type: 'string_too_long' }] } });
    await send(page, '긴 말');
    await turns(page, 1);
    await settle(page);
    const relay = await armed(page);
    // 고르기 창을 열지 않고 다시 시도 — 같은 값 · 같은 덧붙인 말로 보낸다(되살린 루틴을 쓰고 끈다)
    await queue(page, { frames: [frame('error', { code: 'routine_busy', message: '루틴이 이미 2개 돈다 — 잠시 뒤', retryable: true }), DONE] });
    await page.locator('#retry').click();
    await turns(page, 2);
    await settle(page);
    const busy = await armed(page);
    // 실행이 생긴 뒤(plan 프레임)의 오류 — 되살리지 않는다(다시 보내면 실행이 둘)
    await queue(page, { frames: [frame('routine', PLAN), frame('error', { code: 'routine_internal', message: '실행기 오류' }),
                                 frame('routine', { kind: 'done', run_id: 'R9', state: 'running' }), DONE] });
    await send(page, '세 번째');
    await turns(page, 3);
    await settle(page);
    const after_run = await armed(page);
    // 그 턴의 다시 시도는 같은 실행을 잇는다
    await page.locator('#retry').click();
    await turns(page, 4);
    // RA 초안 올리기 턴이 실행 프레임 뒤에 실패했다 — 다시 시도는 올리기를 다시 한다
    await queue(page, { frames: [frame('routine', { kind: 'report', run_id: 'R9', ra_upload: 'ask', ra_error: 'RA 연결 실패',
                                                    coverage: { counts: {}, not_ok: [] }, warnings: [] }),
                                 frame('error', { code: 'routine_gateway', message: 'RA 에 닿지 못했다' }), DONE] });
    await page.evaluate((t) => window.__ctx.resumeRoutine('R9', t, { uploadRa: true }), TITLE);
    await turns(page, 5);
    await page.locator('#retry').click();
    await turns(page, 6);
    await settle(page);
    return { relay, busy, after_run, after_upload: await armed(page), chats: await chats(page), msgs: await msgs(page),
             errors: page.__errors };
  },
  // 받던 중에 끊겼다(첫 routine 프레임 전) — 실행이 서버에 생겼는지 모른다. 되살리지 않고, 다시 시도는 보낸 요청 그대로다.
  async cut(browser) {
    const page = await open(browser);
    await arm(page, { model: 'S26', strict: 'true' });
    await queue(page, { hold: true });
    await send(page, '끊길 말');
    await page.waitForFunction(() => typeof window.__break === 'function');
    await page.evaluate(() => window.__break('network error'));
    await turns(page, 1);
    await settle(page);
    const after_cut = await armed(page);
    const cut_msgs = await msgs(page);
    await page.locator('#retry').click();
    await turns(page, 2);
    return { after_cut, cut_msgs, chats: await chats(page), errors: page.__errors };
  },
  // 칸 안에서 끌어 고르다 카드 밖에서 뗐다 · 배경에서 눌러 카드 안에서 뗐다 — 닫지 않는다. 배경을 그냥 누르면 닫는다.
  async drag(browser) {
    const page = await open(browser);
    await openForm(page);
    await field(page, 'model').fill('S26 Ultra');
    await field(page, 'laminate').fill(LONG);
    const before = await form(page);
    const out = {};
    const cases = [
      ['textarea_right', 'laminate', (c, b) => [c.x + c.width + 6, b.y + 12]],
      ['textarea_below', 'laminate', (c, b) => [b.x + 40, c.y + c.height + 15]],
      ['input_right', 'model', (c, b) => [c.x + c.width + 6, b.y + 10]],
    ];
    for (const [name, key, target] of cases) {
      // 앞 끌기가 남긴 선택을 접는다 — 선택 위에서 누르면 브라우저가 글 고르기가 아니라 끌어 놓기를 시작한다
      await field(page, key).press('End');
      const b = await field(page, key).boundingBox();
      const card = await page.locator('.rp-card').boundingBox();
      const [x, y] = target(card, b);
      await page.mouse.move(b.x + 12, b.y + 10);
      await page.mouse.down();
      await page.mouse.move(x, y, { steps: 8 });
      await page.mouse.up();
      await settle(page);
      out[name] = (await page.locator('.rp-card').count()) === 1;
      if (!out[name]) break;
    }
    if (Object.values(out).every(Boolean)) {
      const card = await page.locator('.rp-card').boundingBox();
      await page.mouse.move(5, 5);
      await page.mouse.down();
      await page.mouse.move(card.x + 30, card.y + 30, { steps: 5 });
      await page.mouse.up();
      await settle(page);
      out.into_card = (await page.locator('.rp-card').count()) === 1;
    }
    const after = (await page.locator('.rp-card').count()) ? await form(page) : null;
    await page.mouse.click(5, 5);
    await settle(page);
    const plain_click_closed = (await page.locator('.rp-card').count()) === 0;
    return { before, after, kept: out, plain_click_closed, errors: page.__errors };
  },
  // 툴바의 바로 보내기 — 켜 둔 루틴을 싣지도 쓰지도 않는다
  async action(browser) {
    const page = await open(browser);
    await send(page, '안녕');
    await turns(page, 1);
    await page.locator('[data-hwax-action="mail"]:not([disabled])').waitFor();
    await arm(page, { model: 'S26', strict: 'true' });
    await page.locator('[data-hwax-action="mail"]').click();
    await turns(page, 2);
    return { chats: await chats(page), armed: await armed(page), pill: await pill(page), errors: page.__errors };
  },
  // 계정이 바뀐다 — 다른 사람의 로그인 · 로그아웃 뒤 다시 로그인
  async account(browser) {
    const page = await open(browser);
    await arm(page, { model: 'A-secret-project-42', strict: 'true' });
    const as_a = await armed(page);
    await page.evaluate(() => window.__setUser('b'));
    await settle(page);
    const as_b = await armed(page);
    const pill_b = await pill(page);
    await arm(page, { model: 'B-project', strict: 'false' });
    await page.evaluate(() => window.__setUser(''));
    await settle(page);
    const logged_out = await armed(page);
    await page.evaluate(() => window.__setUser('b'));
    await page.locator('textarea[aria-label="메시지 입력"]').waitFor();
    await settle(page);
    const back_b = await armed(page);
    await send(page, '그냥 질문');
    await turns(page, 1);
    return { as_a, as_b, pill_b, logged_out, back_b, chats: await chats(page), errors: page.__errors };
  },
  // 보낸 뒤 계정이 바뀌었고 그 턴이 실행 전에 실패했다 — 앞 사람의 루틴을 다음 사람에게 되살리지 않는다
  async switch_in_flight(browser) {
    const page = await open(browser);
    await arm(page, { model: 'A-secret-project-42', strict: 'true' });
    await queue(page, { hold: true });
    await send(page, '앨리스의 말');
    await page.waitForFunction(() => typeof window.__push === 'function');
    await page.evaluate(() => window.__setUser('b'));
    await settle(page);
    await page.evaluate((t) => { window.__push(t); window.__end(); },
      frame('error', { code: 'routine_busy', message: '루틴이 이미 2개 돈다' }) + DONE);
    await settle(page);
    await page.waitForFunction(() => document.getElementById('streaming').textContent === 'false');
    return { armed: await armed(page), pill: await pill(page), errors: page.__errors };
  },
  // 덧붙인 말이 상한(2,000자)을 넘는다 — 선의 note 만 자르고 사람 글(message)은 그대로 보낸다
  async note_clip(browser) {
    const page = await open(browser);
    await arm(page, { model: 'S26', strict: 'true' });
    await send(page, LONG_NOTE);
    await turns(page, 1);
    return { chats: await chats(page), msgs: await msgs(page), errors: page.__errors };
  },
  // 루틴 아닌 턴 · 루틴 턴의 ■ 힌트, 그리고 첫 routine 프레임 전에 ■ 로 끊은 루틴 턴의 다시 시도 — 내 실행 목록에서 그 실행을 찾아 잇는다
  async stop_found(browser) {
    const page = await open(browser, { serverKind: 'chat', hint: true });
    await queue(page, { hold: true });
    await send(page, '그냥 질문');
    await page.waitForFunction(() => typeof window.__push === 'function');
    const plain = await hint(page);
    await page.evaluate((t) => { window.__push(t); window.__end(); }, frame('token', { delta: '답' }) + DONE);
    await turns(page, 1);
    await arm(page, { model: 'S26', strict: 'true' });
    await page.evaluate(() => { window.__push = undefined; });
    await queue(page, { hold: true });
    await send(page, '멈출 말');
    await page.waitForFunction(() => typeof window.__push === 'function');
    const routine = await hint(page);
    const sec = Math.floor((await page.evaluate(() => Date.now())) / 1000);
    await page.locator('button[aria-label="응답 중지"]').click();
    await turns(page, 2);
    const idle = await hint(page);
    // 목록은 최근 시작부터(포털 ORDER BY started_at DESC) — 다른 대화의 더 새 실행 · 이 대화의 실행(서버 시계가 20초 늦다) · 이 대화의 10분 전 실행
    // (이 대화의 메시지가 가리키지 않는 것 가운데 가장 새것이 그 턴의 실행이다)
    await page.evaluate((rows) => { window.__runs = rows; },
      [runRow('R-ELSE', 'conv-other', sec + 1), runRow('R-MINE', 'conv-srv-1', sec - 20), runRow('R-OLD', 'conv-srv-1', sec - 600)]);
    await queue(page, { frames: [frame('routine', { ...PLAN, run_id: 'R-MINE', resumed: true }),
                                 frame('routine', { kind: 'done', run_id: 'R-MINE', state: 'running' }), DONE] });
    await page.locator('#retry').click();
    await turns(page, 3);
    return { plain, routine, idle, chats: await chats(page), runs: await runsAsked(page), msgs: await msgs(page),
             errors: page.__errors };
  },
  // 첫 routine 프레임 전에 ■ — 목록을 못 읽었다(500) · 맞는 실행이 없다(conversation_id 를 싣지 않는 줄 · 이 대화의 앞 턴 답이 가리키는 실행).
  // 둘 다 보낸 요청을 다시 보낸다
  async stop_fallback(browser) {
    const page = await open(browser, { serverKind: 'chat' });
    await stopBeforeRun(page, '첫 말');
    await turns(page, 1);
    await page.evaluate(() => { window.__runsStatus = 500; });
    // 다시 보낸 요청이 실행 R-OLD 를 만들었다 — 그 답이 R-OLD 를 가리킨다
    await queue(page, { frames: [frame('routine', { ...PLAN, run_id: 'R-OLD' }),
                                 frame('routine', { kind: 'done', run_id: 'R-OLD', state: 'running' }), DONE] });
    await page.locator('#retry').click();
    await turns(page, 2);
    const sec = await stopBeforeRun(page, '둘째 말');
    await turns(page, 3);
    await page.evaluate((rows) => { window.__runsStatus = 0; window.__runs = rows; },
      [runRow('R-NOCONV', 'conv-srv-1', sec + 1, false), runRow('R-OLD', 'conv-srv-1', sec - 600)]);
    await page.locator('#retry').click();
    await turns(page, 4);
    return { chats: await chats(page), runs: await runsAsked(page), msgs: await msgs(page), errors: page.__errors };
  },
  // 다시 시도가 실행 목록을 기다리는 사이에 계정이 바뀌었다 — 앞 사람의 요청을 다음 사람의 이름으로 보내지 않는다(#36)
  async switch_during_lookup(browser) {
    const page = await open(browser, { serverKind: 'chat' });
    await stopBeforeRun(page, '앨리스의 말');
    await turns(page, 1);
    await page.evaluate(() => { window.__runsHold = true; });
    await page.locator('#retry').click();
    await page.waitForFunction(() => typeof window.__runsRelease === 'function');
    await page.evaluate(() => window.__setUser('b'));
    await settle(page);
    await page.evaluate(() => window.__runsRelease());
    await settle(page);
    await settle(page);
    return { chats: await chats(page), runs: await runsAsked(page), errors: page.__errors };
  },
  // 받던 중에 끊긴 루틴 턴(첫 routine 프레임 전)의 다시 시도도 그 실행을 찾아 잇는다
  async cut_found(browser) {
    const page = await open(browser, { serverKind: 'chat' });
    await arm(page, { model: 'S26', strict: 'true' });
    await queue(page, { hold: true });
    await send(page, '끊길 말');
    await page.waitForFunction(() => typeof window.__break === 'function');
    const sec = Math.floor((await page.evaluate(() => Date.now())) / 1000);
    await page.evaluate(() => window.__break('network error'));
    await turns(page, 1);
    await page.evaluate((rows) => { window.__runs = rows; }, [runRow('R-CUT', 'conv-srv-1', sec + 2)]);
    await page.locator('#retry').click();
    await turns(page, 2);
    return { chats: await chats(page), runs: await runsAsked(page), msgs: await msgs(page), errors: page.__errors };
  },
  // 서버 시계가 이 PC 보다 90초 · 180초 늦다 — 시작 시각으로 가르면 그 턴의 실행을 놓쳐 실행이 둘이 된다. 둘째 턴은 첫 턴이 이은 실행(메시지가
  // 가리킨다)을 건너뛰고 그 턴의 실행을 잇는다
  async stop_clock(browser) {
    const page = await open(browser, { serverKind: 'chat' });
    const sec1 = await stopArmed(page, { model: 'S26', strict: 'true' }, '첫 말');
    await turns(page, 1);
    await page.evaluate((rows) => { window.__runs = rows; }, [runRow('R-90', 'conv-srv-1', sec1 - 90)]);
    await queue(page, resumed('R-90'));
    await page.locator('#retry').click();
    await turns(page, 2);
    const sec2 = await stopArmed(page, { model: 'S26', strict: 'false' }, '둘째 말');
    await turns(page, 3);
    await page.evaluate((rows) => { window.__runs = rows; },
      [runRow('R-90', 'conv-srv-1', sec1 - 90), runRow('R-180', 'conv-srv-1', sec2 - 180)]);
    await queue(page, resumed('R-180'));
    await page.locator('#retry').click();
    await turns(page, 4);
    return { chats: await chats(page), runs: await runsAsked(page), msgs: await msgs(page), errors: page.__errors };
  },
  // 앞 턴(모델 A)의 답이 가리키는 실행 R0 — 같은 루틴 · 이 대화 · 20초 전이라도 다음 턴(모델 B)의 것이 아니다. 그 턴의 실행이 아직 목록에 없으면
  // 다시 시도는 모델 B 요청을 다시 보내고, 있으면(R2) 그것을 잇는다
  async stop_prior(browser) {
    const page = await open(browser, { serverKind: 'chat' });
    await arm(page, { model: 'A', strict: 'true' });
    await queue(page, { frames: [frame('routine', { ...PLAN, run_id: 'R0' }),
                                 frame('routine', { kind: 'done', run_id: 'R0', state: 'running' }), DONE] });
    await send(page, '모델 A');
    await turns(page, 1);
    const sec1 = await stopArmed(page, { model: 'B', strict: 'true' }, '모델 B');
    await turns(page, 2);
    await page.evaluate((rows) => { window.__runs = rows; }, [runRow('R0', 'conv-srv-1', sec1 - 20)]);
    await page.locator('#retry').click();
    await turns(page, 3);
    const sec2 = await stopArmed(page, { model: 'C', strict: 'true' }, '모델 C');
    await turns(page, 4);
    await page.evaluate((rows) => { window.__runs = rows; },
      [runRow('R2', 'conv-srv-1', sec2 + 1), runRow('R0', 'conv-srv-1', sec1 - 20)]);
    await queue(page, resumed('R2'));
    await page.locator('#retry').click();
    await turns(page, 5);
    return { chats: await chats(page), runs: await runsAsked(page), msgs: await msgs(page), errors: page.__errors };
  },
  // 실행 id 전에 게이트웨이 오류(포털이 늦었다) · 중계의 침묵 한도 · 실행기 오류로 끝난 턴 — 실행이 생겼을 수 있다. 다시 시도는 먼저 찾아 잇고(오류가
  // 되살린 같은 루틴은 끈다), 이 대화의 메시지가 가리키지 않는 실행이 없으면 보낸 요청을 다시 보낸다
  async maybe_started(browser) {
    const page = await open(browser, { serverKind: 'chat' });
    const sec = Math.floor((await page.evaluate(() => Date.now())) / 1000);
    await arm(page, { model: 'S26', strict: 'true' });
    await queue(page, { frames: [frame('error', { code: 'routine_gateway', message: '포털에 닿지 못했다(ReadTimeout)' }), DONE] });
    await send(page, '게이트웨이가 늦은 말');
    await turns(page, 1);
    await settle(page);
    const gw_armed = await armed(page);
    await page.evaluate((rows) => { window.__runs = rows; }, [runRow('R-GW', 'conv-srv-1', sec + 1)]);
    await queue(page, resumed('R-GW'));
    await page.locator('#retry').click();
    await turns(page, 2);
    await settle(page);
    const gw_after = await armed(page);
    await arm(page, { model: 'S26', strict: 'false' });
    await queue(page, { frames: [frame('error', { code: 'agent_stream_idle',
      message: '에이전트 서버가 900초 동안 아무 신호도 보내지 않아 구독을 끊었다(AGENT_STREAM_IDLE_TIMEOUT_S). 루틴은 서버에서 계속 돌 수 있다' }), DONE] });
    await send(page, '조용해진 말');
    await turns(page, 3);
    await settle(page);
    const idle_armed = await armed(page);
    await page.evaluate((rows) => { window.__runs = rows; },
      [runRow('R-IDLE', 'conv-srv-1', sec + 5), runRow('R-GW', 'conv-srv-1', sec + 1)]);
    await queue(page, resumed('R-IDLE'));
    await page.locator('#retry').click();
    await turns(page, 4);
    await settle(page);
    await arm(page, { model: 'S27', strict: 'true' });
    await queue(page, { frames: [frame('error', { code: 'routine_internal', message: '실행기 오류 — RuntimeError: x' }), DONE] });
    await send(page, '실행기 오류 말');
    await turns(page, 5);
    await settle(page);
    await page.locator('#retry').click();
    await turns(page, 6);
    await settle(page);
    return { gw_armed, gw_after, idle_armed, internal_after: await armed(page), chats: await chats(page),
             runs: await runsAsked(page), msgs: await msgs(page), errors: page.__errors };
  },
  // 누른 때의 함수로 부른 잇기(고르기를 기다린 뒤 잇던 길) — 다른 답을 받는 중이면 둘째 스트림을 열지 않는다
  async stale_resume(browser) {
    const page = await open(browser);
    await page.evaluate(() => { window.__stale = window.__ctx.resumeRoutine; });
    await queue(page, { hold: true });
    await send(page, '다른 질문');
    await page.waitForFunction(() => typeof window.__push === 'function');
    await page.evaluate((t) => window.__stale('R1', t), TITLE);
    await settle(page);
    const during = await chats(page);
    await page.evaluate((t) => { window.__push(t); window.__end(); }, frame('token', { delta: '답' }) + DONE);
    await turns(page, 1);
    await settle(page);
    return { during, chats: await chats(page), msgs: await msgs(page), errors: page.__errors };
  },
  // 루틴을 켜 두고 그림 · 문서를 붙여 보내면 보내지 않고 까닭을 말한다(붙인 것 · 쓴 글 · 켜 둔 루틴은 그대로). 이어서 같은 루틴 턴은 붙인 것을
  // 싣지도 비우지도 않고, 다음 일반 턴이 싣는다
  async attach(browser) {
    const page = await open(browser);
    await page.evaluate((im) => window.__ctx.setAttachedImages([im]), IMG);
    await arm(page, { model: 'S26', strict: 'true' });
    await send(page, '이 균열 사진을 근거로');
    await settle(page);
    const img_try = { chats: (await chats(page)).length, alerts: await alerts(page), chips: await chips(page),
                      armed: await armed(page), box: await box(page).inputValue() };
    await page.locator('.img-chip button').click();
    await settle(page);
    const removed = await alerts(page);
    await page.evaluate((d) => window.__ctx.setAttachedDocs([d]), DOC);
    await box(page).press('Enter');
    await settle(page);
    const doc_try = { chats: (await chats(page)).length, alerts: await alerts(page), docs: await page.locator('.doc-chip').count() };
    await page.locator('.doc-chip button').click();
    await box(page).press('Enter');
    await turns(page, 1);
    await page.evaluate((im) => window.__ctx.setAttachedImages([im]), IMG);
    await page.evaluate((t) => window.__ctx.resumeRoutine('R-77', t), TITLE);
    await turns(page, 2);
    const after_resume = await chips(page);
    await send(page, '그냥 질문');
    await turns(page, 3);
    return { img_try, removed, doc_try, after_resume, after_plain: await chips(page), chats: await chats(page),
             errors: page.__errors };
  },
  // ■ 힌트 — 실행이 이미 끝난 턴(RA 초안 올리기 · 끝난 계획을 받은 이어서)은 '멈춤' 을 가리키지 않는다. 도는 실행을 이으면 그대로고, 그 턴을 ■ 로
  // 끊으면 오류는 '취소됨' 이다(실행 id 를 안다)
  async closed_hint(browser) {
    const page = await open(browser, { hint: true });
    const held = async (args) => {
      await page.evaluate(() => { window.__push = undefined; });
      await queue(page, { hold: true });
      await page.evaluate((a) => window.__ctx.resumeRoutine(...a), args);
      await page.waitForFunction(() => typeof window.__push === 'function');
    };
    await held(['R-8', TITLE, { uploadRa: true }]);
    const upload = await hint(page);
    await page.evaluate((t) => { window.__push(t); window.__end(); },
      frame('routine', { ...PLAN, run_id: 'R-8', state: 'done', resumed: true }) + DONE);
    await turns(page, 1);
    await held(['R-9', TITLE]);
    const closed_before = await hint(page);
    await page.evaluate((t) => window.__push(t), frame('routine', { ...PLAN, run_id: 'R-9', state: 'done', resumed: true }));
    await settle(page);
    const closed_after = await hint(page);
    await page.evaluate((t) => { window.__push(t); window.__end(); }, frame('routine', { kind: 'done', run_id: 'R-9', state: 'done' }) + DONE);
    await turns(page, 2);
    await held(['R-10', TITLE]);
    await page.evaluate((t) => window.__push(t), frame('routine', { ...PLAN, run_id: 'R-10', state: 'running', resumed: true }));
    await settle(page);
    const live = await hint(page);
    await page.locator('button[aria-label="응답 중지"]').click();
    await turns(page, 3);
    return { upload, closed_before, closed_after, live, idle: await hint(page), msgs: await msgs(page), errors: page.__errors };
  },
  // 고르기 창 — 키보드로 루틴을 고르면 다 불러온 뒤 '← 목록' 이 포커스를 받고 무엇을 열었는지 들린다. 목록으로 돌아오면 그 루틴의 줄이 받는다
  async picker_focus(browser) {
    const page = await open(browser);
    await page.locator('.tool-routine .tool-pill').click();
    await page.locator('.rp-row').first().waitFor();
    await page.locator('.rp-row').first().focus();
    await page.keyboard.press('Enter');
    await page.locator('.rp-fields').waitFor();
    await settle(page);
    const opened = await focused(page);
    const said = await page.evaluate(() => Array.from(document.querySelectorAll('.rp-card [role="status"]')).map((e) => e.textContent));
    const out = { opened, said };
    if (opened.cls.includes('rp-back')) {
      await page.keyboard.press('Enter');
      await page.locator('.rp-row').first().waitFor();
      await settle(page);
      out.back = await focused(page);
    }
    out.errors = page.__errors;
    return out;
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
    """화면을 한 번 묶고 시나리오를 한 번에 돌려, 시나리오 이름 → 본 것을 돌려준다(브라우저를 시험마다 띄우지 않는다)."""
    out = tmp_path_factory.mktemp("routinectx")
    (out / "harness.tsx").write_text(_HARNESS.replace("__FE__", str(FE)), encoding="utf-8")
    for name, body in (("build.cjs", _BUILD), ("stub.js", _STUB), ("drive.cjs", _DRIVE)):
        (out / name).write_text(body, encoding="utf-8")
    r = subprocess.run(["node", "build.cjs", str(FE), str(out)], cwd=str(out), capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, "화면을 묶지 못했다:\n" + (r.stdout + r.stderr)[-4000:]
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


TITLE = "시장불량 원인 분석"
REASON = "입력 엄격(strict) — strict: 참·거짓이 아니다 — 'false'"
# 실행 id 를 받기 전에 ■ 로 끊은 새 루틴 턴의 오류 글(lib/chatErrors ROUTINE_STOPPED_BEFORE_RUN)
STOPPED_BEFORE_RUN = "취소됨 — 루틴 실행 id 를 받기 전"
ATTACH_BLOCK = "켜 둔 루틴은 붙인 그림 · 문서를 쓰지 않습니다"


def _routine(body: dict) -> dict | None:
    return body.get("routine")


# ── 덧붙인 말(R3 C3) ─────────────────────────────────────────────────────────────────────────────────
def test_사람이_쓴_글은_덧붙인_말로_가고_빈_글의_제목_글은_덧붙인_말이_아니다(seen):
    """실행기는 routine.note 를 원장에 남겨 '사용자가 덧붙인 말' 로 쓴다(이어서에도). 글 없이 보낼 때 싣는 '루틴: <제목>' 이 note 로 가면
    단계 · 인사이트 프롬프트가 제목을 사람의 조건으로 읽는다."""
    s = seen("note")
    first, second = s["chats"]
    assert first["message"] == "북미 모델만, 3분기 이후"
    assert _routine(first).get("note") == "북미 모델만, 3분기 이후", "사람이 쓴 글이 덧붙인 말(note)로 가지 않는다"
    assert _routine(first) == {"id": "rt-swelling", "version": 3, "note": "북미 모델만, 3분기 이후",
                               "inputs": {"model": "S26", "strict": "true", "limit": "9007199254740993"}}, \
        "큰 정수 id 는 적은 글 그대로 가야 한다(형은 포털이 맞춘다)"
    assert s["after1"] is None, "켜 둔 루틴은 한 번 쓰고 꺼진다"
    assert second["message"] == f"루틴: {TITLE}"
    assert _routine(second) == {"id": "rt-swelling", "version": 3, "inputs": {"model": "S26", "strict": "false"}}, \
        "글 없이 보낸 턴에 note 가 실렸다 — '루틴: <제목>' 은 덧붙인 말이 아니다"
    assert [m["text"] for m in s["msgs"] if m["role"] == "user"] == ["북미 모델만, 3분기 이후", f"루틴: {TITLE}"], \
        "화면의 사람 말풍선은 보낸 글 그대로다"


def test_이어서는_run_id_만이고_RA_초안_올리기는_upload_ra_를_더한다(seen):
    """R3 C4 — 끝난 실행의 'RA 초안 올리기'(ra.upload ask)는 {run_id, upload_ra: true}. 이어서는 덧붙인 말을 다시 보내지 않는다(실행기가 원장
    note 를 쓴다). 포털 RoutineReq.upload_ra 는 참거짓만 받는다(StrictBool) — 글 'true' 가 가면 422 다."""
    s = seen("resume")
    resume, upload = s["chats"]
    assert resume["message"] == f"루틴 이어서: {TITLE}" and _routine(resume) == {"run_id": "R-77"}
    assert upload["message"] == f"RA 초안 올리기: {TITLE}" and _routine(upload) == {"run_id": "R-77", "upload_ra": True}
    assert s["armed"] is None


# ── 고르기 창의 칸(#14) ────────────────────────────────────────────────────────────────────────────
def test_고르기_창은_참거짓을_고르게_하고_수치는_수_칸이다(seen):
    """포털 Var.coerce 는 참거짓으로 'true' · 'false' 만 받는다 — 글 칸에 '예' · '참' 을 적으면 실행을 만들기 전에 거절됐다."""
    f = seen("note")["fields"]
    assert (f["strict"]["tag"], f["strict"]["options"]) == ("SELECT", ["", "true", "false"])
    assert (f["limit"]["tag"], f["limit"]["type"]) == ("INPUT", "number")
    assert (f["model"]["tag"], f["model"]["type"]) == ("INPUT", "")
    assert f["laminate"]["tag"] == "TEXTAREA"


# ── 실행 전의 거절(#14) ────────────────────────────────────────────────────────────────────────────
def test_실행_전에_거절되면_보낸_값을_다시_켜_두고_까닭을_그_칸_옆에_보인다(seen):
    s = seen("reject")
    assert s["rearmed"] == {"id": "rt-swelling", "version": 3, "title": TITLE, "reason": REASON,
                            "inputs": {"model": "S26", "strict": "false", "limit": "1000", "laminate": '{"a": 1}'}}, \
        "거절 하나에 적은 값이 다 사라졌다 — 다시 켜 두어야 한다"
    assert "is-warn" in s["pill1"]["cls"] and REASON in s["pill1"]["title"], "알약이 거절을 말하지 않는다"
    got = s["reopened"]
    assert {k: v["value"] for k, v in got.items()} == {"model": "S26", "strict": "false", "limit": "1000", "laminate": '{"a": 1}'}
    assert REASON in got["strict"]["err"] and got["strict"]["invalid"] == "true", "까닭이 그 칸 옆에 없다"
    assert not any(v["err"] for k, v in got.items() if k != "strict") and s["top_err"] == [], "까닭을 엉뚱한 자리에도 보인다"


def test_다시_시도는_고친_값과_처음_덧붙인_말로_보내고_켜_둔_것을_쓴다(seen):
    s = seen("reject")
    assert s.get("fixed"), "실패한 턴이 값을 되살리지 않아 고쳐서 다시 켤 것이 없다"
    assert "reason" not in s["fixed"] and s["fixed"]["inputs"]["strict"] == "true", "다시 켜면 까닭이 지워져야 한다"
    assert "is-warn" not in s["pill2"]["cls"]
    first, again = s["chats"]
    assert again["message"] == first["message"] == "북미만"
    assert _routine(again) == {"id": "rt-swelling", "version": 3, "note": "북미만",
                               "inputs": {"model": "S26", "strict": "true", "limit": "1000", "laminate": '{"a": 1}'}}, \
        "다시 시도가 옛 값(같은 거절)을 다시 보냈거나 덧붙인 말을 잃었다"
    assert s["after_retry"] is None, "다시 시도가 켜 둔 루틴을 쓰지 않아 다음 발화에 또 실린다"


def test_중계_거절과_동시_상한도_값을_살리고_손대지_않은_다시_시도는_같은_값을_보낸다(seen):
    s = seen("reject_more")
    assert s["relay"], "중계의 검증 거절(422) 뒤에 보낸 값을 되살리지 않았다"
    assert s["relay"]["inputs"] == {"model": "S26", "strict": "true"} and "(422)" in s["relay"]["reason"]
    relay, busy = s["chats"][:2]
    assert _routine(busy) == _routine(relay) == {"id": "rt-swelling", "version": 3, "note": "긴 말",
                                                 "inputs": {"model": "S26", "strict": "true"}}
    assert busy["message"] == "긴 말"
    assert s["busy"] is not None and s["busy"]["reason"].startswith("루틴이 이미 2개"), "동시 상한 뒤에도 값이 살아야 한다"


def test_실행이_생긴_뒤의_오류는_되살리지_않고_다시_시도는_그_실행을_잇는다(seen):
    s = seen("reject_more")
    third, retry = s["chats"][2:4]
    assert (_routine(third) or {}).get("id") == "rt-swelling" and third["message"] == "세 번째", \
        "시험의 전제 — 셋째 턴은 되살린 루틴을 싣고 간다"
    assert s["after_run"] is None, "plan 프레임 뒤의 오류에 루틴을 되살렸다 — 다시 보내면 실행이 둘이다"
    assert _routine(retry) == {"run_id": "R9"} and retry["message"] == f"루틴 이어서: {TITLE}"


def test_받던_중에_끊긴_턴은_되살리지_않고_다시_시도는_보낸_요청_그대로다(seen):
    """끊김(stream_cut)은 실행 전의 거절이 아니다 — 응답이 흐르기 시작했으니 실행이 서버에 생겼을 수 있다. 되살리면 다시 보내라고 이끈다."""
    s = seen("cut")
    assert s["cut_msgs"][1]["error"].startswith("스트림이 끊겼습니다"), "시험의 전제 — 받던 중의 끊김이다"
    assert s["after_cut"] is None, "받던 중에 끊긴 턴의 루틴을 되살렸다 — 실행이 이미 있으면 다시 보내 둘이 된다"
    first, again = s["chats"]
    assert _routine(again) == _routine(first) == {"id": "rt-swelling", "version": 3, "note": "끊길 말",
                                                  "inputs": {"model": "S26", "strict": "true"}}, \
        "다시 시도가 보낸 값 · 덧붙인 말을 잃었다"


def test_RA_초안_올리기_턴의_다시_시도는_올리기를_다시_한다(seen):
    s = seen("reject_more")
    upload, retry = s["chats"][4:6]
    assert _routine(upload) == _routine(retry) == {"run_id": "R9", "upload_ra": True}, \
        "그냥 이어서로 가면 끝난 실행이라 '이미 끝났다' 로 끝난다"
    assert s["after_upload"] is None


# ── 창 닫기 손짓(#33) ────────────────────────────────────────────────────────────────────────────
def test_칸_안에서_끌다_카드_밖에서_떼도_고르기_창이_닫히지_않고_값이_남는다(seen):
    s = seen("drag")
    assert s["kept"] == {"textarea_right": True, "textarea_below": True, "input_right": True, "into_card": True}, \
        "누름과 뗌이 둘 다 배경이 아닌데 닫혔다"
    assert s["after"] is not None and s["after"]["laminate"]["value"] == s["before"]["laminate"]["value"]
    assert s["after"]["model"]["value"] == "S26 Ultra"
    assert s["plain_click_closed"], "배경을 그냥 누르면 닫혀야 한다"


# ── 툴바의 한 번 누름(#35) ──────────────────────────────────────────────────────────────────────────
def test_툴바의_바로_보내기는_켜_둔_루틴을_싣지도_쓰지도_않는다(seen):
    s = seen("action")
    sent = s["chats"][1]
    assert sent["message"] == "이 답을 메일 초안으로 만들어 줘"
    assert "routine" not in sent, "툴바 요청이 루틴의 덧붙인 말이 되어 루틴이 돌고 메일 초안은 안 된다"
    assert s["armed"] is not None and s["armed"]["id"] == "rt-swelling", "툴바 누름이 켜 둔 루틴을 써 버렸다"
    assert "is-on" in s["pill"]["cls"]


# ── 계정이 바뀔 때(#36) ─────────────────────────────────────────────────────────────────────────────
def test_계정이_바뀌면_켜_둔_루틴과_입력을_버린다(seen):
    s = seen("account")
    assert s["as_a"]["inputs"]["model"] == "A-secret-project-42"
    assert s["as_b"] is None, "앞 사람이 켜 둔 루틴과 입력이 다음 사람에게 남았다"
    assert s["pill_b"]["text"] == "루틴" and "is-on" not in s["pill_b"]["cls"]
    assert s["logged_out"] is None and s["back_b"] is None, "로그아웃해도 켜 둔 루틴이 메모리에 남았다"
    assert "routine" not in s["chats"][0], "다음 사람의 발화에 앞 사람의 루틴이 실렸다"


def test_보낸_뒤_계정이_바뀐_턴이_실패해도_앞_사람의_루틴을_되살리지_않는다(seen):
    s = seen("switch_in_flight")
    assert s["armed"] is None, "실패한 턴이 앞 사람의 값을 다음 사람의 입력창에 켜 두었다"
    assert s["pill"]["text"] == "루틴"


# ── 덧붙인 말 상한 ──────────────────────────────────────────────────────────────────────────────────
def test_덧붙인_말은_선에서_2000자로_자르고_사람_글은_자르지_않는다(seen):
    """중계 RoutineReq.note 는 2,000자(파이썬 글자 수)까지다 — 넘으면 보내기 전체가 422 라 루틴이 시작조차 못 했다. 잘라도 그림 글자를 반으로
    가르면(UTF-16 자르기) 짝 없는 대리 글자가 가 또 422(string_unicode)다."""
    s = seen("note_clip")
    (sent,) = s["chats"]
    text = "가" * 1999 + "😀" + "나" * 600
    assert sent["message"] == text, "사람이 쓴 글(message)까지 잘랐다"
    assert [m["text"] for m in s["msgs"] if m["role"] == "user"] == [text], "화면의 사람 말풍선은 쓴 글 그대로다"
    note = _routine(sent).get("note", "")
    assert len(note) <= 2000, f"덧붙인 말 {len(note)}자가 중계 상한 2,000자를 넘어 보내기 전체가 422 다"
    assert note == "가" * 1999 + "😀", "앞 2,000자(코드 포인트)를 그대로 보내야 한다 — 그림 글자를 반으로 갈랐거나 더 잘랐다"


# ── 실행 id 를 받기 전에 끊긴 루틴 턴의 다시 시도 ────────────────────────────────────────────────────────
def test_실행_id_전에_멈춘_루틴_턴의_다시_시도는_이_대화에서_그_뒤에_시작한_실행을_잇는다(seen):
    """■ 는 화면 받기만 끊는다 — 중계는 상류를 끝까지 읽고 실행기는 구독이 끊겨도 돈다. 같은 요청을 다시 보내면 실행이 둘이다."""
    s = seen("stop_found")
    plain, stopped, retry = s["chats"]
    assert stopped["conversation_id"] == "conv-srv-1" and (_routine(stopped) or {}).get("id") == "rt-swelling", \
        "시험의 전제 — 멈춘 턴은 이 대화의 새 실행 요청이다"
    assert s["msgs"][3]["error"] == STOPPED_BEFORE_RUN and not s["msgs"][3]["run"], "시험의 전제 — 실행 id 를 받기 전에 ■ 로 끊었다"
    assert s["runs"] == ["/routines-api/runs?routine_id=rt-swelling"], "다시 시도가 내 실행 목록을 찾아보지 않았다"
    assert retry["message"] == f"루틴 이어서: {TITLE}" and _routine(retry) == {"run_id": "R-MINE"}, \
        "그 턴의 실행을 두고 새 실행을 또 만들었거나 다른 대화의 실행 · 앞 턴의 실행을 이었다"
    assert s["msgs"][5]["run"] == "R-MINE"


def test_실행_id_전에_멈춘_턴은_실행을_못_찾으면_보낸_요청을_다시_보낸다(seen):
    """목록을 못 읽었으면 예전처럼 다시 보낸다. 목록이 conversation_id 를 싣지 않는 포털이면 그 실행이 이 대화의 것인지 모른다 — 다른 탭 · 다른
    입력으로 연 실행을 잇지 않고 다시 보낸다(닫힌 쪽). 이 대화의 실행이라도 이 대화의 메시지가 이미 가리키는 것은 앞 턴의 실행이다."""
    s = seen("stop_fallback")
    first, again, second, again2 = s["chats"]
    assert len(s["runs"]) == 2, "다시 시도가 실행 목록을 찾아보지 않았다"
    assert _routine(again) == _routine(first) == {"id": "rt-swelling", "version": 3, "note": "첫 말",
                                                  "inputs": {"model": "S26", "strict": "true"}}, \
        "목록을 못 읽었을 때 보낸 요청을 그대로 다시 보내야 한다"
    assert s["msgs"][3]["run"] == "R-OLD", "시험의 전제 — 앞 턴의 답이 R-OLD 를 가리킨다"
    assert _routine(again2) == _routine(second) and _routine(second)["note"] == "둘째 말", \
        "conversation_id 없는 줄을 이 대화의 실행으로 보았거나 앞 턴의 답이 가리키는 실행을 이었다"


def test_실행을_찾는_사이에_계정이_바뀌면_앞_사람의_요청을_보내지_않는다(seen):
    s = seen("switch_during_lookup")
    assert len(s["runs"]) == 1, "시험의 전제 — 다시 시도가 실행 목록을 기다리는 중에 계정이 바뀌었다"
    assert len(s["chats"]) == 1, f"앞 사람의 루틴 요청을 다음 사람의 이름으로 보냈다: {s['chats'][1:]}"


def test_받던_중에_끊긴_루틴_턴의_다시_시도도_그_실행을_찾아_잇는다(seen):
    s = seen("cut_found")
    first, retry = s["chats"]
    assert s["msgs"][1]["error"].startswith("스트림이 끊겼습니다") and (_routine(first) or {}).get("id") == "rt-swelling", \
        "시험의 전제 — 첫 routine 프레임 전에 받던 중 끊긴 새 실행 요청이다"
    assert s["runs"] == ["/routines-api/runs?routine_id=rt-swelling"]
    assert _routine(retry) == {"run_id": "R-CUT"} and retry["message"] == f"루틴 이어서: {TITLE}", \
        "끊긴 턴의 실행을 두고 새 실행을 또 만들었다"


# ── ■ 힌트 ───────────────────────────────────────────────────────────────────────────────────────────
def test_루틴_턴이_흐르는_동안_중지_힌트는_루틴이_서버에서_계속_돈다고_말한다(seen):
    s = seen("stop_found")
    assert s["plain"] == {"hint": "응답 생성 중… 중지하려면 ■ 버튼", "stop": "응답 중지", "routine": "false"}, \
        "루틴 아닌 턴의 힌트가 바뀌었다"
    h = s["routine"]["hint"]
    assert "연결만 끊" in h and "서버에서 계속" in h and "‘멈춤’" in h, \
        f"루틴 턴(실행 id 전에도)의 힌트가 ■ 를 루틴 중지로 읽히게 둔다: {h!r}"
    assert s["routine"]["stop"] == h, "힌트 줄이 없는 입력창(독)에서는 ■ 단추 풀이가 같은 말을 해야 한다"
    assert s["routine"]["routine"] == "true"
    assert s["idle"] == {"hint": "Enter 전송 · Shift+Enter 줄바꿈 · 그림은 붙여넣기(Ctrl+V)", "stop": "", "routine": "false"}, \
        "멈춘 뒤에도 루틴 턴 표시가 남았다"


def test_실행이_이미_끝난_루틴_턴의_중지_힌트는_멈춤을_가리키지_않는다(seen):
    """RA 초안 올리기 턴 · 끝난 계획을 받은 이어서는 그칠 실행이 없다 — '멈춤' 은 어디에도 없는데 힌트가 그것을 가리켰다(2차 #16). 중계는 그
    턴도 끝까지 읽으므로 '연결만 끊는다' 는 그대로 말한다. 도는 실행을 이으면 종전 힌트이고, 그 턴을 ■ 로 끊으면 오류는 그냥 '취소됨' 이다."""
    s = seen("closed_hint")
    for name in ("upload", "closed_after"):
        h = s[name]
        assert "연결만 끊" in h["hint"] and "멈춤" not in h["hint"], f"{name} — 끝난 실행의 턴이 '멈춤' 을 가리킨다: {h['hint']!r}"
        assert h["stop"] == h["hint"] and h["routine"] == "true", f"{name} — ■ 단추 풀이가 힌트 줄과 다르다"
    assert "올리기" in s["upload"]["hint"]
    assert "‘멈춤’" in s["closed_before"]["hint"], "계획을 받기 전(끝났는지 모른다)에는 종전 힌트다"
    assert "‘멈춤’" in s["live"]["hint"] and "서버에서 계속" in s["live"]["hint"], "도는 실행을 이은 턴의 힌트가 바뀌었다"
    assert s["msgs"][5]["error"] == "취소됨", "실행 id 를 아는 턴의 ■ 는 그냥 '취소됨' 이다"
    assert s["idle"]["routine"] == "false"


def test_실행_id_전에_멈춘_루틴_턴의_오류는_루틴의_말로_적힌다(seen):
    """루틴 칸이 아직 없어 '중단되었습니다' 만 보였다 — 실행은 서버에서 돌고 있는데 멈춘 것으로 읽혔다(2차 #16). 루틴 칸이 있는 턴(실행 id 를
    안다)은 종전대로 '취소됨' 이다(위 시험)."""
    s = seen("stop_found")
    assert s["msgs"][3]["error"] == STOPPED_BEFORE_RUN


def test_서버_시계가_어긋나도_실행_id_전에_멈춘_턴의_실행을_찾는다(seen):
    """포털 started_at 은 서버 시계이고 보낸 때는 이 PC 의 시계다 — 60초 여유로 가르면 서버가 그보다 늦은 박스에서 그 턴의 실행을 놓쳐 새 실행을
    또 만들었다(2차 #6). 이 대화의 메시지가 아직 가리키지 않는 가장 새 실행이 그 턴의 것이다."""
    s = seen("stop_clock")
    first, retry1, second, retry2 = s["chats"]
    assert (_routine(first) or {}).get("id") == "rt-swelling" and first["conversation_id"] == "conv-srv-1", "시험의 전제"
    assert _routine(retry1) == {"run_id": "R-90"}, f"서버 시계가 90초 늦은 실행을 놓쳤다 — {retry1}"
    assert s["msgs"][3]["run"] == "R-90"
    assert _routine(retry2) == {"run_id": "R-180"}, \
        f"서버 시계가 180초 늦은 실행을 놓쳤거나 앞 턴이 이은 R-90 에 다시 붙었다 — {retry2}"
    assert len(s["runs"]) == 2


def test_앞_턴의_답이_가리키는_실행에는_다시_시도가_붙지_않는다(seen):
    """모델 A 턴의 답이 R0 을 보인 뒤 모델 B 턴을 실행 id 전에 끊었다 — 그 턴의 실행이 아직 목록에 없을 때 다시 시도가 20초 전의 R0 을 이으면
    사람의 모델 B 요청이 말없이 모델 A 실행으로 바뀐다(2차 #13). 다시 보내고, 그 턴의 실행(R2)이 목록에 있으면 그것을 잇는다."""
    s = seen("stop_prior")
    t0, t1, retry1, t2, retry2 = s["chats"]
    assert (_routine(t0) or {}).get("inputs", {}).get("model") == "A" and s["msgs"][1]["run"] == "R0", "시험의 전제 — 앞 턴의 답이 R0 이다"
    assert _routine(retry1) == _routine(t1) == {"id": "rt-swelling", "version": 3, "note": "모델 B",
                                                "inputs": {"model": "B", "strict": "true"}}, \
        f"다시 시도가 앞 턴의 실행 R0 에 붙었거나 모델 B 요청을 잃었다 — {retry1}"
    assert _routine(retry2) == {"run_id": "R2"}, f"그 턴의 실행 R2 를 두고 다시 보냈거나 R0 에 붙었다 — {retry2}"


def test_게이트웨이_실행기_오류_침묵_한도로_끝난_턴의_다시_시도는_실행을_먼저_찾는다(seen):
    """게이트웨이가 포털을 기다리다 끊겼거나(ReadTimeout) 보낸 뒤 답을 잃으면 원장에는 실행이 남는다 — 거절로만 보아 같은 요청을 다시 보내면 실행이
    둘이고 앞 것은 아무도 돌리지 않는 running 으로 남았다(2차 #11). 다시 시도는 먼저 찾아 잇고, 그 오류가 되살려 켜 둔 같은 루틴은 끈다(남기면
    다음 발화가 또 시작한다). 침묵 한도는 받던 중의 끊김처럼 되살리지 않는다. 찾을 실행이 없으면(목록의 것은 메시지가 가리킨다) 보낸 요청이다."""
    s = seen("maybe_started")
    assert s["gw_armed"] and s["gw_armed"]["reason"] == "포털에 닿지 못했다(ReadTimeout)", "시험의 전제 — 게이트웨이 오류는 값을 되살린다"
    gw, retry_gw, idle, retry_idle, internal, retry_internal = s["chats"]
    assert (_routine(gw) or {}).get("id") == "rt-swelling"
    assert _routine(retry_gw) == {"run_id": "R-GW"}, f"게이트웨이 오류 뒤 실행을 찾지 않고 다시 보냈다 — {retry_gw}"
    assert s["gw_after"] is None, "실행을 찾아 이었는데 되살린 루틴이 켜져 있다 — 다음 발화가 실행을 또 만든다"
    assert s["idle_armed"] is None, "침묵 한도(실행이 서버에서 돈다) 뒤 루틴을 되살렸다 — 다시 보내게 이끈다"
    assert _routine(retry_idle) == {"run_id": "R-IDLE"}, f"침묵 한도 뒤 실행을 찾지 않았다 — {retry_idle}"
    assert _routine(retry_internal) == _routine(internal) == {"id": "rt-swelling", "version": 3, "note": "실행기 오류 말",
                                                              "inputs": {"model": "S27", "strict": "true"}}, \
        f"찾을 실행이 없는데 메시지가 가리키는 실행에 붙었다 — {retry_internal}"
    assert s["internal_after"] is None and len(s["runs"]) == 3


def test_받는_중에는_누른_때의_함수로_부른_잇기도_둘째_스트림을_열지_않는다(seen):
    """고르기는 원장에 고른 뒤 잇는다 — 그 사이 다른 답이 흐르기 시작해도 누른 때의 함수는 받는 중이 아니라고 믿어 둘째 스트림을 열었고, 먼저
    끝난 쪽이 다른 쪽의 ■ 를 지웠다(2차 #12)."""
    s = seen("stale_resume")
    assert len(s["during"]) == 1, f"받는 중에 둘째 스트림이 열렸다 — {[c.get('message') for c in s['during']]}"
    assert [c["message"] for c in s["chats"]] == ["다른 질문"]


def test_켜_둔_루틴과_붙인_그림_문서는_함께_보내지_않고_까닭을_말한다(seen):
    """실행기는 붙인 그림 · 문서를 읽지 않는다 — 보내면 그림은 저장되지 않은 채 칩에서만 사라졌다(2차 #14). 보내지 않고 입력창에 까닭을 말하며
    붙인 것 · 쓴 글 · 켜 둔 루틴은 그대로 둔다. 떼면 말이 거둬지고, 다 떼면 루틴만 간다."""
    s = seen("attach")
    t = s["img_try"]
    assert t["chats"] == 0, "켜 둔 루틴과 붙인 그림을 함께 보냈다"
    assert any(ATTACH_BLOCK in a for a in t["alerts"]), f"보내지 않은 까닭을 말하지 않는다 — {t['alerts']}"
    assert t["chips"] == 1 and t["armed"] and t["box"] == "이 균열 사진을 근거로", "붙인 그림 · 켜 둔 루틴 · 쓴 글을 잃었다"
    assert not any(ATTACH_BLOCK in a for a in s["removed"]), "그림을 떼었는데 막는 말이 남았다"
    d = s["doc_try"]
    assert d["chats"] == 0 and d["docs"] == 1 and any(ATTACH_BLOCK in a for a in d["alerts"]), f"붙인 문서도 막아야 한다 — {d}"
    sent = s["chats"][0]
    assert _routine(sent) == {"id": "rt-swelling", "version": 3, "note": "이 균열 사진을 근거로", "inputs": {"model": "S26", "strict": "true"}}
    assert "images" not in sent and "documents" not in sent


def test_루틴_턴은_붙여_둔_그림을_싣지도_비우지도_않고_다음_일반_턴이_싣는다(seen):
    """이어서 · 고른 뒤 잇기 · RA 초안 올리기 · 다시 시도는 사람이 고른 보내기가 아니다 — 붙여 둔 그림을 그 턴이 가져가 버렸다(2차 #14)."""
    s = seen("attach")
    resume, plain = s["chats"][1:3]
    assert _routine(resume) == {"run_id": "R-77"} and "images" not in resume, "이어서 턴이 붙여 둔 그림을 실었다"
    assert s["after_resume"] == 1, "이어서 턴이 붙여 둔 그림을 비웠다"
    assert "routine" not in plain and len(plain.get("images") or []) == 1, "다음 일반 턴이 그림을 싣지 않았다"
    assert s["after_plain"] == 0


def test_고르기_창에서_루틴을_고르면_포커스를_옮기고_무엇을_열었는지_들린다(seen):
    """고른 줄은 목록과 함께 사라져 포커스가 문서(body)로 떨어지고 아무것도 들리지 않았다(2차 #17). 다 불러오면 '← 목록' 이 포커스를 받고, 돌아오면
    방금 본 루틴의 줄이 받는다."""
    s = seen("picker_focus")
    assert "rp-back" in s["opened"]["cls"], f"루틴을 고른 뒤 포커스가 '← 목록' 에 없다 — {s['opened']}"
    assert any(f"「{TITLE}」 을(를) 열었습니다" in x for x in s["said"]), f"무엇을 열었는지 들리지 않는다 — {s['said']}"
    assert "rp-row" in s.get("back", {}).get("cls", "") and TITLE in s["back"]["text"], \
        f"목록으로 돌아온 뒤 포커스가 그 루틴의 줄에 없다 — {s.get('back')}"
