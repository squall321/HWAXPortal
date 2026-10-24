# 보내기 알림이 대화에 남는 순서를 헤드리스 브라우저에서 실제 ChatProvider 로 본다 — 서버는 띄우지 않는다(가짜 fetch · 가짜 시계, docs/chat-ppt PP-D3)
"""왜 — 보내기 결과를 대화에 남기는 일은 '언제 · 어느 서버 대화에' 가 전부다. 순수 함수 시험으로는 안 잡힌다.

  · 대화가 없으면(첫 화면) 새 대화를 만들고 서버 대화도 하나 만들어 알림을 붙인다. 다음 발화는 그 서버 대화로 가고(둘 만들지 않는다),
    이력에 알림의 근거가 kind=upload 로 실린다.
  · 답을 받는 중인 대화에 온 알림은 화면에는 곧바로(답 아래) 붙고, 서버 사본에는 그 스트림이 끝나고 잠시 뒤 붙는다 — 포털은 답을
    스트림 끝에 적으므로 먼저 적으면 다른 기기에서 알림이 답보다 앞에 선다.
  · 알림 바로 뒤에 보내면(서버 대화를 만드는 중) 발화가 그 줄을 기다린다 — 서버 대화는 하나, 알림이 발화보다 먼저 적힌다.
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
import { Composer } from '__FE__/src/components/chat/Composer';

const NOTICE = {
  title: 'a.pptx — AI 데이터 허브 변환',
  text: '「a.pptx」 을 AI 데이터 허브로 보내 변환했습니다',
  activity: [{ ts: 1, step: 'AI 데이터 허브로 보내 변환(사람이 올림)', tool: 'convert_file', detail: '{"file":"u-a.pptx"}',
               result_full: '{"record":1}', ok: true, origin: 'upload' as const }],
};
function Probe() {
  const { messages, sendMessage, streaming, addUploadNotice, activeConversation } = useChat();
  return (
    <>
      <button id="notice" type="button" onClick={() => addUploadNotice(NOTICE)}>notice</button>
      <button id="send" type="button" onClick={() => sendMessage('방금 변환한 것 검토해 줘')}>send</button>
      <span id="streaming">{String(streaming)}</span>
      <span id="roles">{messages.map((m) => m.role).join(',')}</span>
      <span id="last">{messages.length ? messages[messages.length - 1].text : ''}</span>
      <span id="sid">{activeConversation?.serverId ?? ''}</span>
    </>
  );
}
function Peek() {
  const { messages, activeConversation, attachedDocs, streaming } = useChat();
  return (
    <>
      <span id="roles">{messages.map((m) => m.role).join(',')}</span>
      <span id="sid">{activeConversation?.serverId ?? ''}</span>
      <span id="docs">{attachedDocs.map((d) => `${d.name}:${d.chars}`).join(',')}</span>
      <span id="streaming">{String(streaming)}</span>
    </>
  );
}
(window as unknown as { __mount: (what?: string) => void }).__mount = (what) => {
  const user = { subject: 'u1@corp.example', email: 'u1@corp.example', display_name: 'U', groups: [] };
  createRoot(document.getElementById('root')!).render(
    <AuthContext.Provider
      value={{ user, status: 'authenticated', login: () => undefined, logout: async () => undefined, refresh: async () => undefined }}
    >
      <MemoryRouter>
        <ChatProvider storagePrefix="hwax.chat" serverKind="chat" sendPrefix={what === 'delib' ? '/심의 ' : ''}>
          {what === 'composer' ? <><Composer /><Peek /></>
            : what === 'composer-page' ? <><Composer dropAnywhere /><Peek /><div id="thread" style={{ height: 300 }}>대화</div></>
            : <Probe />}
        </ChatProvider>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
};
"""

# 가짜 백엔드 — 서버 대화 만들기(__createDelay ms 뒤 답) · 메시지 붙이기 · 챗 스트림(__push · __end). 부른 차례를 __calls 에 적는다.
_STUB = r"""
(() => {
  window.__calls = [];
  window.__createDelay = 0;
  let made = 0;
  const enc = new TextEncoder();
  const json = (body, status = 200) =>
    Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }));
  window.fetch = (url, init = {}) => {
    const u = String(url);
    const method = (init.method || 'GET').toUpperCase();
    window.__calls.push({ url: u, method, body: typeof init.body === 'string' ? JSON.parse(init.body) : null });
    if (u === '/agent/upload' && method === 'POST') {
      const f = init.body.get('file');
      if (f.name.includes('broken')) return json({ detail: '스테이징 디스크가 찼습니다' }, 507);
      window.__staged = (window.__staged || 0) + 1;
      return json({ staging_id: 'st' + window.__staged, filename: f.name, size: f.size, ext: 'pptx', content_type: '',
                    destinations: window.__dests || [{ id: 'aidatahub', label: 'AI 데이터 허브 — 지식카드로 변환' },
                                                      { id: 'reportarchive', label: 'Report Archive — 보고서로' }] });
    }
    if (u === '/agent/upload/dispatch') return json(window.__dispatch);
    if (u.startsWith('/agent/upload/destinations/docforge/jobs/')) {      // 정밀 변환(DocForge) — 진행은 차례대로, 배달은 한 번
      if (u.endsWith('/deliver')) return json(window.__dfDeliver);
      if (u.endsWith('/cancel')) return json({ cancelled: true });
      return json(window.__dfStates.length > 1 ? window.__dfStates.shift() : window.__dfStates[0]);
    }
    if (u === '/agent/upload/pc-ticket' && method === 'POST')
      return json({ ticket: 'T'.repeat(43), expires_in_s: 600, helper_url: 'hwax-doc://extract?t=' + 'T'.repeat(43), protocol: 1 });
    if (u === '/agent/upload/pc-ticket/' + 'T'.repeat(43)) {
      const st = window.__pcStates.length > 1 ? window.__pcStates.shift() : window.__pcStates[0];
      return st === 'err' ? json({ detail: '잠깐 끊김' }, 502) : json(st);
    }
    if (u === '/agent/upload/pc-ticket/' + 'T'.repeat(43) + '/doc')
      return Promise.resolve(new Response(window.__pcDoc, { status: 200, headers: { 'Content-Type': 'text/markdown' } }));
    if (u === '/agent/upload/pc-ticket/' + 'T'.repeat(43) + '/slides/1') {
      const png = Uint8Array.from(atob('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=='),
                                  (ch) => ch.charCodeAt(0));
      return Promise.resolve(new Response(png, { status: 200, headers: { 'Content-Type': 'image/png' } }));
    }
    if (u === '/agent/conversations' && method === 'GET') return json({ conversations: [] });
    if (u === '/agent/conversations' && method === 'POST') {
      made += 1;
      const id = 'srv-' + made;
      return new Promise((res) => setTimeout(() => res(json({ id })), window.__createDelay));
    }
    if (/^\/agent\/conversations\/[^/]+\/messages$/.test(u)) return json({ ok: true });
    if (u.startsWith('/agent/conversations/')) return json({ detail: 'not found' }, 404);
    if (u.startsWith('/agent/chat')) {
      const body = new ReadableStream({ start(c) {
        window.__push = (text) => c.enqueue(enc.encode(text));
        window.__end = () => c.close();
      } });
      return Promise.resolve(new Response(body, { status: 200, headers: { 'Content-Type': 'text/event-stream' } }));
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
const frame = (event, data) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;

const AIDH = { stage: 'done', destination: 'aidatahub', inbox_name: 'u1-a.pptx', result: { status: 'converted', record: { t: 1 } } };
const MD = '---\nschema: hwax-doc/1\nsource: 설계검토.pptx\nkind: ppt\nunits: 1\n---\n\n## [s.1] 개요\n\n낙하 1.5 m\n';
const RECEIVED = { state: 'received', filename: 'drm.pptx', expires_in_s: 0,
  received: { doc_name: '설계검토.hwax.md', chars: MD.length, bytes: MD.length, slides: 1, doc_staging_id: 'd1' },
  staged: { staging_id: 'd1', filename: '설계검토.hwax.md', size: MD.length, ext: 'md', content_type: '',
            destinations: [{ id: 'aidatahub', label: 'AI 데이터 허브 — 지식카드로 변환' }] } };
const WAITING = { state: 'waiting', filename: 'drm.pptx', expires_in_s: 590 };

async function pick(page, name, head) {
  await page.locator('input[type=file]').setInputFiles({ name, mimeType: 'application/octet-stream',
    buffer: Buffer.concat([Buffer.from(head), Buffer.alloc(64)]) });
}

const PNG_B64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==';
const PK_B64 = Buffer.concat([Buffer.from([0x50, 0x4b, 0x03, 0x04]), Buffer.alloc(64)]).toString('base64');
// 파일을 끌어 와 놓는다 — 페이지 안에서 DataTransfer 를 만들어 dragover(놓을 자리 표시를 본다) → drop. files 가 없으면 글 끌기.
async function drag(page, selector, files, text) {
  const dt = await page.evaluateHandle(([fs, t]) => {
    const d = new DataTransfer();
    for (const f of fs) d.items.add(new File([Uint8Array.from(atob(f.b64), (c) => c.charCodeAt(0))], f.name, { type: f.mime }));
    if (t) d.setData('text/plain', t);
    return d;
  }, [files, text || '']);
  await page.dispatchEvent(selector, 'dragover', { dataTransfer: dt });
  const veil = await page.evaluate(() => Boolean(document.querySelector('.drop-veil')));
  const veil_text = await page.evaluate(() => (document.querySelector('.drop-veil b') || {}).textContent || '');
  const ring = await page.evaluate(() => Boolean(document.querySelector('form.composer-drop')));
  await page.dispatchEvent(selector, 'drop', { dataTransfer: dt });
  await page.waitForTimeout(80);
  return { veil, veil_text, ring, veil_after: await page.evaluate(() => Boolean(document.querySelector('.drop-veil'))) };
}
const err = (page) => page.evaluate(() => (document.querySelector('.composer .upl-err') || {}).textContent || '');
const chips = (page) => page.evaluate(() => document.querySelectorAll('.img-chip').length);

async function open(browser, what = '') {
  const page = await browser.newPage();
  page.setDefaultTimeout(10000);
  page.__errors = [];
  page.on('pageerror', (e) => page.__errors.push(String(e)));
  await page.route('http://harness.invalid/**', (r) =>
    r.fulfill({ contentType: 'text/html', body: '<!doctype html><html><body><div id="root"></div></body></html>' }));
  await page.clock.install({ time: new Date('2026-10-23T00:00:00Z') });
  await page.goto('http://harness.invalid/');
  await page.addScriptTag({ path: path.join(OUT, 'stub.js') });
  await page.addScriptTag({ path: path.join(OUT, 'bundle.js') });
  await page.evaluate((w) => window.__mount(w), what);
  return page;
}
const text = (page, id) => page.evaluate((i) => document.getElementById(i).textContent, id);
const calls = (page) => page.evaluate(() => window.__calls.filter((c) => c.url !== '/agent/conversations' || c.method !== 'GET')
  .map((c) => ({ url: c.url, method: c.method, body: c.body })));
async function forward(page, ms) { await page.clock.fastForward(ms); await page.waitForTimeout(60); }
async function finish(page) {
  await page.evaluate((f) => { window.__push(f); window.__end(); }, frame('result', { type: 'text', content: '답입니다' }) + frame('done', {}));
  await page.waitForFunction(() => document.getElementById('streaming').textContent === 'false');
}

const SCENARIOS = {
  // 입력창에서 파일 → AI 데이터 허브로 보내기 — 대화에 알림 · 입력창에 지시문(비어 있을 때만) · 새 파일이면 패널이 새로(A5)
  async composer_dispatch(browser) {
    const page = await open(browser, 'composer');
    await page.evaluate((r) => { window.__dispatch = r; }, AIDH);
    await pick(page, 'a.pptx', [0x50, 0x4b, 0x03, 0x04]);
    await page.getByText('어디로 보낼까요').waitFor();
    await page.getByRole('button', { name: /AI 데이터 허브/ }).click();
    await page.getByRole('button', { name: '변환하기' }).click();
    await page.getByText('변환했습니다').waitFor();
    await page.waitForFunction(() => window.__calls.some((c) => /\/messages$/.test(c.url)));
    const filled = await page.locator('textarea').inputValue();
    const roles = await text(page, 'roles');
    await pick(page, 'b.pptx', [0x50, 0x4b, 0x03, 0x04]);
    await page.getByText('어디로 보낼까요').waitFor();
    const reset = { done_gone: (await page.getByText('변환했습니다').count()) === 0, file: await page.locator('.upl-file').first().textContent() };
    return { filled, roles, reset, errors: page.__errors };
  },
  // 이 대화에서 분석 — 읽어 온 글이 문서 칩으로 붙고, 대화에 '보냈다' 알림은 남지 않는다(docs/chat-ppt PP-D17)
  async composer_chat(browser) {
    const page = await open(browser, 'composer');
    const md = '---\nschema: hwax-doc/1\nsource: a.pptx\nkind: ppt\nunits: 2\n---\n\n# a\n\n## [s.1] 개요\n\n낙하 1.5 m\n';
    await page.evaluate((m) => {
      window.__dests = [{ id: 'chat', label: '이 대화에서 분석 — 글·표·차트·노트를 읽어 입력창에(저장하지 않음)' },
                        { id: 'aidatahub', label: 'AI 데이터 허브 — 지식카드로 변환' }];
      window.__dispatch = { stage: 'done', destination: 'chat', doc: { name: 'a.hwax.md', text: m, chars: m.length } };
    }, md);
    await pick(page, 'a.pptx', [0x50, 0x4b, 0x03, 0x04]);
    await page.getByRole('button', { name: /이 대화에서 분석/ }).click();
    await page.getByRole('button', { name: '읽어서 붙이기' }).click();
    await page.getByText('입력창에 붙였습니다').waitFor();
    const sent = (await calls(page)).find((c) => c.url === '/agent/upload/dispatch');
    return { docs: await text(page, 'docs'), roles: await text(page, 'roles'), dispatch: sent && sent.body,
             appends: (await calls(page)).filter((c) => /\/messages$/.test(c.url)).length,
             chip_kind: await page.evaluate(() => (document.querySelector('.doc-chip em') || {}).textContent || ''),
             errors: page.__errors };
  },
  // 정밀 변환(DocForge) — 맡기면 진행을 1.5초마다 보고, 끝나면 배달(RA 엄격 생성)해 대화에 알림 · 입력창에 지시문(docs/doc-to-ra DF-D17)
  async composer_precise(browser) {
    const page = await open(browser, 'composer');
    await page.evaluate(() => {
      window.__dests = [{ id: 'reportarchive_precise', label: 'Report Archive — 정밀 변환(배치 유지 · 그림 판독)' }];
      window.__dispatch = { stage: 'dispatched', destination: 'reportarchive_precise', job_id: 'j_abc123' };
      window.__dfStates = [{ job_id: 'j_abc123', status: 'running', stage: 'S3 읽기', progress: 50 },
                           { job_id: 'j_abc123', status: 'done', stage: '끝', progress: 100 }];
      window.__dfDeliver = { stage: 'done', destination: 'reportarchive_precise', created: true, report_id: 41, title: '설계 검토',
        url: '/w/personal-5/reports/41', pages: 3, blocks: 12, dropped: 1, model_written: 2, unaccounted: 0, fidelity: 'full',
        warnings: [], conversion_warnings: ['u1.e3: 경고'] };
    });
    await pick(page, 'a.pptx', [0x50, 0x4b, 0x03, 0x04]);
    await page.getByRole('button', { name: /정밀 변환/ }).click();
    await page.getByRole('button', { name: '정밀 변환 맡기기' }).click();
    await page.getByText('정밀 변환 중').waitFor();
    await forward(page, 1600);
    const progress = await page.evaluate(() => (document.querySelector('.upl-panel [role=status]') || {}).textContent || '');
    await forward(page, 1600);
    await page.getByText('정밀 변환 보고서를 만들었습니다').waitFor();
    await page.waitForFunction(() => window.__calls.some((c) => /\/messages$/.test(c.url)));
    const all = await calls(page);
    const sent = all.find((c) => c.url === '/agent/upload/dispatch');
    return { progress, dispatch: sent && sent.body, roles: await text(page, 'roles'),
             df: all.filter((c) => c.url.includes('/docforge/')).map((c) => `${c.method} ${c.url}`),
             filled: await page.locator('textarea').inputValue(),
             link: await page.evaluate(() => { const a = document.querySelector('.upl-panel a'); return a ? a.getAttribute('href') : ''; }),
             model_note: (await page.getByText('원본과 맞는지 확인하세요').count()) > 0, errors: page.__errors };
  },
  // 사람이 쓰던 글이 있으면 저절로 덮지 않는다 — 단추로만
  async composer_typed(browser) {
    const page = await open(browser, 'composer');
    await page.evaluate((r) => { window.__dispatch = r; }, AIDH);
    await page.locator('textarea').fill('내가 쓰던 글');
    await pick(page, 'a.pptx', [0x50, 0x4b, 0x03, 0x04]);
    await page.getByRole('button', { name: /AI 데이터 허브/ }).click();
    await page.getByRole('button', { name: '변환하기' }).click();
    await page.getByText('변환했습니다').waitFor();
    const kept = await page.locator('textarea').inputValue();
    await page.getByRole('button', { name: '검토 지시문을 입력창에 넣기' }).click();
    return { kept, after_button: await page.locator('textarea').inputValue(), errors: page.__errors };
  },
  // 암호 파일 → PC 도우미 → 받은 글이 문서 칩으로 · 다음 단계(AI 데이터 허브)
  async pc_helper(browser) {
    const page = await open(browser, 'composer');
    // 한 번의 끊김(502)으로 멈추지 않는다 — 다시 묻는다
    await page.evaluate(([w, r, md]) => { window.__pcStates = ['err', w, { ...w, state: 'opened' }, r]; window.__pcDoc = md; }, [WAITING, RECEIVED, MD]);
    await pick(page, 'drm.pptx', [0xd0, 0xcf, 0x11, 0xe0]);
    await page.getByLabel('슬라이드 그림도(최대 12장)').check();
    await page.getByRole('button', { name: 'PC 의 PowerPoint 로 열어 가져오기' }).click();
    await page.getByText('PC 도우미를 기다리는 중…').waitFor();
    const ticket = (await calls(page)).find((c) => c.url === '/agent/upload/pc-ticket');
    await forward(page, 1600);
    const after_blip = (await page.getByText('받지 못했습니다').count()) + (await page.getByText('잠깐 끊김').count());
    await forward(page, 1600);
    await forward(page, 1600);
    const opened = (await page.getByText('PC 도우미가 열렸습니다').count()) > 0;
    await forward(page, 1600);
    await page.getByText('입력창에 붙였습니다').waitFor();
    const docs = await text(page, 'docs');
    await page.waitForFunction(() => document.querySelectorAll('.img-chip').length === 1);
    const imgs = await page.evaluate(() => document.querySelectorAll('.img-chip').length);
    await page.getByRole('button', { name: '이 글을 AI 데이터 허브로도 보내기' }).click();
    await page.getByText('어디로 보낼까요').waitFor();
    return { ticket: ticket && ticket.body, after_blip, opened, docs, imgs, next_file: await page.locator('.upl-file').first().textContent(), errors: page.__errors };
  },
  // 도우미가 안 열리면(설치 전) 15초 뒤 설치 안내
  async pc_helper_late(browser) {
    const page = await open(browser, 'composer');
    await page.evaluate((w) => { window.__pcStates = [w]; }, WAITING);
    await pick(page, 'drm.pptx', [0xd0, 0xcf, 0x11, 0xe0]);
    await page.getByRole('button', { name: 'PC 의 PowerPoint 로 열어 가져오기' }).click();
    await page.getByText('PC 도우미를 기다리는 중…').waitFor();
    const early = await page.getByRole('button', { name: '도우미 설치 배치 받기' }).count();
    for (let i = 0; i < 12; i += 1) await forward(page, 1600);
    return { early, late: await page.getByRole('button', { name: '도우미 설치 배치 받기' }).count(), errors: page.__errors };
  },
  // 대화창(화면 어디든)에 PPT 를 놓으면 '+' 와 같이 올라가 '어디로 보낼까요' 가 뜬다 · 그림 여럿은 다 붙는다
  async drop_page(browser) {
    const page = await open(browser, 'composer-page');
    const ppt = await drag(page, '#thread', [{ name: '설계검토.pptx', mime: 'application/vnd.ms-powerpoint', b64: PK_B64 }]);
    await page.getByText('어디로 보낼까요').waitFor();
    const staged = await page.locator('.upl-file').first().textContent();
    const uploads = (await calls(page)).filter((c) => c.url === '/agent/upload').length;
    const imgs = await drag(page, 'body', [{ name: 'a.png', mime: 'image/png', b64: PNG_B64 }, { name: 'b.png', mime: 'image/png', b64: PNG_B64 }]);
    await page.waitForFunction(() => document.querySelectorAll('.img-chip').length === 2);
    return { ppt, staged, uploads, imgs, chips: await chips(page), errors: page.__errors };
  },
  // 섞어 놓기 — 문서 하나 + 그림, 나머지 문서는 이름을 대고 · 받지 않는 형식은 올리지 않고 이름을 댄다
  async drop_mixed(browser) {
    const page = await open(browser, 'composer-page');
    await drag(page, '#thread', [{ name: 'a.pptx', mime: '', b64: PK_B64 }, { name: 'p.png', mime: 'image/png', b64: PNG_B64 },
                                 { name: 'b.pptx', mime: '', b64: PK_B64 }, { name: 'setup.exe', mime: '', b64: PK_B64 }]);
    await page.getByText('어디로 보낼까요').waitFor();
    await page.waitForFunction(() => document.querySelectorAll('.img-chip').length === 1);
    const mixed = { staged: await page.locator('.upl-file').first().textContent(), err: await err(page),
                    uploads: (await calls(page)).filter((c) => c.url === '/agent/upload').length };
    // 문서가 못 올라가도 그 까닭이 함께 놓은 그림 처리에 지워지지 않는다
    const page3 = await open(browser, 'composer-page');
    await drag(page3, '#thread', [{ name: 'broken.pptx', mime: '', b64: PK_B64 }, { name: 'p.png', mime: 'image/png', b64: PNG_B64 }]);
    await page3.waitForFunction(() => document.querySelectorAll('.img-chip').length === 1);
    const broken = { err: await err(page3) };
    const page2 = await open(browser, 'composer-page');
    await drag(page2, 'body', [{ name: 'setup.exe', mime: '', b64: PK_B64 }]);
    await page2.waitForTimeout(100);
    const odd = { err: await err(page2), uploads: (await calls(page2)).filter((c) => c.url === '/agent/upload').length };
    return { mixed, odd, broken, errors: [...page.__errors, ...page2.__errors, ...page3.__errors] };
  },
  // 독(입력창 위에 놓을 때만) — 바깥에 놓으면 받지 않고(다른 화면의 끌기를 가로채지 않는다), 입력창 위에 놓으면 받는다 · 글 끌기는 그대로
  async drop_dock(browser) {
    const page = await open(browser, 'composer');
    const outside = await drag(page, 'body', [{ name: 'a.png', mime: 'image/png', b64: PNG_B64 }]);
    const after_outside = await chips(page);
    const inside = await drag(page, 'form.composer', [{ name: 'a.png', mime: 'image/png', b64: PNG_B64 }]);
    await page.waitForFunction(() => document.querySelectorAll('.img-chip').length === 1);
    const page2 = await open(browser, 'composer-page');
    const text = await drag(page2, '#thread', [], '그냥 글');
    return { outside, after_outside, inside, text, errors: [...page.__errors, ...page2.__errors] };
  },
  // 답을 받는 중 — 놓아도 붙이지 않고 까닭을 말한다(+ 단추가 숨는 때와 같다)
  async drop_streaming(browser) {
    const page = await open(browser, 'composer-page');
    await page.locator('textarea').fill('질문');
    await page.locator('textarea').press('Enter');
    await page.waitForFunction(() => typeof window.__push === 'function');
    const d = await drag(page, '#thread', [{ name: 'a.png', mime: 'image/png', b64: PNG_B64 }]);
    await page.waitForTimeout(100);
    const during = { chips: await chips(page), err: await err(page), veil_text: d.veil_text };
    await finish(page);
    return { during, errors: page.__errors };
  },
  // 심의 화면 — 알림만 있는 대화의 첫 발화에도 트리거가 붙는다
  async delib_first_turn(browser) {
    const page = await open(browser, 'delib');
    await page.locator('#notice').click();
    await page.locator('#send').click();
    await page.waitForFunction(() => typeof window.__push === 'function');
    const chat = (await calls(page)).find((c) => c.url.startsWith('/agent/chat'));
    await finish(page);
    return { message: chat.body.message, errors: page.__errors };
  },
  // 첫 화면에서 보냈다 — 새 대화 · 서버 대화 하나 · 알림 붙이기, 다음 발화는 그 서버 대화로 · 이력에 업로드 근거
  async fresh(browser) {
    const page = await open(browser);
    await page.locator('#notice').click();
    await page.waitForFunction(() => window.__calls.some((c) => /\/messages$/.test(c.url)));
    const after_notice = { roles: await text(page, 'roles'), sid: await text(page, 'sid'), calls: await calls(page) };
    await page.locator('#send').click();
    await page.waitForFunction(() => typeof window.__push === 'function');
    const chat = (await calls(page)).find((c) => c.url.startsWith('/agent/chat'));
    await finish(page);
    return { after_notice, chat, all: await calls(page), roles: await text(page, 'roles'), errors: page.__errors };
  },
  // 답을 받는 중에 보냈다 — 화면에는 곧바로, 서버 사본에는 그 스트림이 끝나고 잠시 뒤
  async while_streaming(browser) {
    const page = await open(browser);
    await page.locator('#send').click();
    await page.waitForFunction(() => typeof window.__push === 'function');
    await page.locator('#notice').click();
    await forward(page, 3000);
    const during = { roles: await text(page, 'roles'), last: await text(page, 'last'), calls: await calls(page) };
    await finish(page);
    const right_after = await calls(page);
    await forward(page, 1000);
    await page.waitForFunction(() => window.__calls.some((c) => /\/messages$/.test(c.url)));
    return { during, right_after, all: await calls(page), roles: await text(page, 'roles'), errors: page.__errors };
  },
  // 알림 바로 뒤에 보냈다(서버 대화를 만드는 중) — 발화가 알림 줄을 기다린다
  async send_right_after(browser) {
    const page = await open(browser);
    await page.evaluate(() => { window.__createDelay = 500; });
    await page.locator('#notice').click();
    await page.locator('#send').click();
    await forward(page, 400);
    const before_create = await calls(page);
    await forward(page, 400);
    await page.waitForFunction(() => typeof window.__push === 'function');
    await finish(page);
    return { before_create, all: await calls(page), sid: await text(page, 'sid'), errors: page.__errors };
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
    out = tmp_path_factory.mktemp("chatppt")
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


def _kinds(calls: list[dict]) -> list[str]:
    out = []
    for c in calls:
        if c["url"] == "/agent/conversations" and c["method"] == "POST":
            out.append("create")
        elif c["url"].endswith("/messages"):
            out.append("append:" + c["url"].split("/")[3])
        elif c["url"].startswith("/agent/chat"):
            out.append("chat:" + str((c["body"] or {}).get("conversation_id")))
    return out


def test_첫_화면의_보내기는_새_대화를_만들고_다음_발화가_그_서버_대화로_간다(seen):
    s = seen("fresh")
    a = s["after_notice"]
    assert a["roles"] == "assistant" and a["sid"] == "srv-1"
    (create, append) = a["calls"]
    assert create["body"]["kind"] == "chat" and create["body"]["title"].startswith("a.pptx")
    assert append["url"] == "/agent/conversations/srv-1/messages"
    assert append["body"]["role"] == "assistant" and append["body"]["content"].startswith("「a.pptx」")
    assert append["body"]["meta"]["upload"] is True and append["body"]["meta"]["activity"][0]["origin"] == "upload"
    assert _kinds(s["all"]) == ["create", "append:srv-1", "chat:srv-1"], "서버 대화는 하나 — 발화가 알림이 만든 대화로 간다"
    (h,) = s["chat"]["body"]["history"]
    assert h["role"] == "assistant" and h["evidence"] == [
        {"tool": "convert_file", "args": '{"file":"u-a.pptx"}', "result": '{"record":1}', "kind": "upload"}]
    assert s["roles"] == "assistant,user,assistant"


def test_답을_받는_중의_보내기는_화면에_곧바로_서버_사본엔_답_뒤에(seen):
    s = seen("while_streaming")
    assert s["during"]["roles"] == "user,assistant,assistant" and s["during"]["last"].startswith("「a.pptx」"), \
        "화면에는 곧바로 — 받는 답 아래"
    assert _kinds(s["during"]["calls"]) == ["create", "chat:srv-1"], "받는 동안은 서버 사본에 붙이지 않는다"
    assert _kinds(s["right_after"]) == ["create", "chat:srv-1"], "스트림이 끝난 그 순간에도 아직 — 포털이 답을 적는 틈을 비켜 간다"
    assert _kinds(s["all"]) == ["create", "chat:srv-1", "append:srv-1"], "같은 서버 대화에 · 답 뒤에"


def test_알림_바로_뒤의_발화는_알림_줄을_기다린다(seen):
    s = seen("send_right_after")
    assert _kinds(s["before_create"]) == ["create"], "서버 대화를 만드는 동안 발화가 하나 더 만들지 않고 기다린다"
    assert _kinds(s["all"]) == ["create", "append:srv-1", "chat:srv-1"], "알림이 발화보다 먼저 적힌다"
    assert s["sid"] == "srv-1"


def test_입력창의_보내기는_대화에_알림을_남기고_빈_입력창에_지시문을_넣는다(seen):
    s = seen("composer_dispatch")
    assert s["filled"] == ("AI 데이터 허브 inbox 파일 `u1-a.pptx` 을 convert_file 로 변환한 초안을 검토하고, "
                           "모자란 항목은 import_record(dry_run=true)로 물어봐 줘")
    assert s["roles"] == "assistant", "대화에 알림 한 건"
    assert s["reset"] == {"done_gone": True, "file": "b.pptx"}, "새 파일이면 고른 목적지 · 완료 표시를 새로 시작한다(A5)"


def test_쓰던_글은_저절로_덮지_않고_단추로만_넣는다(seen):
    s = seen("composer_typed")
    assert s["kept"] == "내가 쓰던 글"
    assert s["after_button"].startswith("AI 데이터 허브 inbox 파일 `u1-a.pptx`")


def test_암호_파일은_PC_도우미로_가져와_문서_칩으로_붙이고_다음_단계를_준다(seen):
    s = seen("pc_helper")
    assert s["ticket"] == {"filename": "drm.pptx", "conversation_id": "", "slides": True}
    assert s["after_blip"] == 0, "상태 조회 한 번의 끊김으로 '실패' 를 굳히지 않는다"
    assert s["opened"], "도우미가 표를 읽으면 '열렸습니다' 로 바뀐다"
    assert s["docs"].startswith("설계검토.hwax.md:"), "손으로 .hwax.md 를 붙이던 것과 같은 칩"
    assert s["imgs"] == 1, "슬라이드 그림은 그림 칩으로(손으로 그림을 붙이던 길과 같다)"
    assert s["next_file"] == "설계검토.hwax.md", "다음 단계는 받은 글의 스테이징 상자로 '어디로 보낼까요'"


def test_도우미가_안_열리면_15초_뒤_설치_안내를_띄운다(seen):
    s = seen("pc_helper_late")
    assert s["early"] == 0 and s["late"] == 1


def test_알림만_있는_대화의_첫_발화에도_심의_트리거가_붙는다(seen):
    assert seen("delib_first_turn")["message"] == "/심의 방금 변환한 것 검토해 줘"


def test_대화창_어디에_놓아도_PPT_는_올라가고_그림은_여럿_붙는다(seen):
    s = seen("drop_page")
    assert s["ppt"] == {"veil": True, "veil_text": "여기에 놓으면 업로드됩니다", "ring": False, "veil_after": False}, \
        "끄는 동안 화면 전체에 놓을 자리 · 놓으면 거둔다"
    assert s["staged"] == "설계검토.pptx" and s["uploads"] == 1, "'+' 와 같은 길 — 올리고 '어디로 보낼까요'"
    assert s["imgs"]["veil"] and s["chips"] == 2, "그림은 여럿 붙는다"


def test_섞어_놓으면_문서_하나와_그림을_붙이고_나머지는_이름을_댄다(seen):
    s = seen("drop_mixed")
    m = s["mixed"]
    assert m["staged"] == "a.pptx" and m["uploads"] == 1
    assert "파일은 한 번에 하나씩 붙습니다 — b.pptx 은(는) 따로 붙이세요" in m["err"], m["err"]
    assert "붙이지 않는 형식입니다 — setup.exe" in m["err"], m["err"]
    assert s["odd"]["uploads"] == 0 and "붙이지 않는 형식입니다 — setup.exe" in s["odd"]["err"], "받지 않는 형식은 올리지도 않는다"
    assert "스테이징 디스크가 찼습니다" in s["broken"]["err"], "문서 업로드 실패가 함께 놓은 그림 처리에 지워지지 않는다"


def test_독은_입력창_위에_놓을_때만_받고_글_끌기는_건드리지_않는다(seen):
    s = seen("drop_dock")
    assert s["outside"] == {"veil": False, "veil_text": "", "ring": False, "veil_after": False} and s["after_outside"] == 0, \
        "독은 닫혀도 입력창이 붙어 있다 — 바깥 끌기를 가로채지 않는다"
    assert s["inside"]["ring"] is True and s["inside"]["veil"] is False, "입력창 위면 테두리로 알리고 받는다"
    assert s["text"]["veil"] is False, "파일이 아닌 끌기(글 · 링크)는 그대로"


def test_답을_받는_중에_놓으면_붙이지_않고_까닭을_말한다(seen):
    d = seen("drop_streaming")["during"]
    assert d["chips"] == 0 and "답을 받는 중에는 붙이지 않습니다" in d["err"], d
    assert d["veil_text"] == "답을 받는 중에는 붙이지 않습니다", "끄는 동안에도 미리 말한다"


def test_이_대화에서_분석은_읽어_온_글을_문서_칩으로_붙이고_보냈다는_알림을_남기지_않는다(seen):
    s = seen("composer_chat")
    assert s["dispatch"] == {"staging_id": "st1", "filename": "a.pptx", "destination": "chat"}
    assert s["docs"].startswith("a.hwax.md:"), "손 추출 · PC 도우미와 같은 문서 칩"
    assert s["chip_kind"].startswith("발표자료 · 2슬라이드"), "머리말(kind · units)을 칩이 읽는다"
    assert s["roles"] == "" and s["appends"] == 0, "보낸 것이 아니라 읽어 온 것 — 대화에 알림을 남기지 않는다"


def test_정밀_변환은_진행을_보이고_끝나면_넣어_대화에_알림과_지시문을_남긴다(seen):
    s = seen("composer_precise")
    assert s["dispatch"] == {"staging_id": "st1", "filename": "a.pptx", "destination": "reportarchive_precise"}
    assert "S3 읽기 · 50%" in s["progress"], s["progress"]
    job = "/agent/upload/destinations/docforge/jobs/j_abc123"
    assert s["df"] == [f"GET {job}", f"GET {job}", f"POST {job}/deliver"], "1.5초마다 보고 · 끝나면 한 번 넣는다"
    assert s["roles"] == "assistant", "대화에 알림 한 건"
    assert s["filled"] == "Report Archive 보고서 41(「설계 검토」)를 get_report_outline · get_report 로 읽고 검토해 줘"
    assert s["link"] == "/report-archive/w/personal-5/reports/41" and s["model_note"] is True
