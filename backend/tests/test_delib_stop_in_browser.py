# 심의 화면의 '멈춤' 단추를 헤드리스 브라우저에 실제로 올려 누른다 — 받는 동안 잠기고 그 심의의 실행 id 로 멈추며, 마무리 중에는 거두고, 끊긴 심의를 멈추면 새로고침 뒤에도 멈춤으로 남는다(가짜 fetch)
"""docs/leftovers-1017 triage A24 (나) — 도는 웹 심의를 서버에서 그치는 '멈춤'(포털 POST /agent/deliberate/cancel). 입력창의 ■ 는 받기만 끊고
심의는 서버에서 끝까지 돈다 — 그치는 길은 심의 칸의 이 단추다. 타입 검사로는 '누르는 동안 잠기는가', '무엇을 보내는가', '결과를 어떻게
말하는가', '받기가 끊긴 심의에도 남는가' 를 못 본다. A24 검토로 더한 것 — 실행 id(첫 심의 사건의 run_id)를 싣는다 · 실행 id 가 없으면 단추가
없다 · 의장이 결정문을 낸 뒤의 마무리(finishing)에는 단추를 거둔다 · 끊긴 심의를 멈추면(200) 칸에 멈춤을 적어 새로고침 뒤에도 남는다. 10-31 화면 틈 —
다단 심의(/시뮬심의)가 1단 결정문 뒤 2단 도중에 끊기면 단추가 남는다(한 단 심의는 결정문 뒤에 없다). test_delib_stream_in_browser 와 같은 길이다 — 실제 ChatProvider · MessageList(심의 칸
DelibView)를 esbuild 로 묶어 빈 문서에 올리고, fetch 는 시험이 한 프레임씩 밀어 넣는 스트림과 손으로 답하는 멈춤 창구로 바꾼다.
도구는 프론트가 이미 가진 것만 쓴다. 없으면 건너뛴다(운영 박스).
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

# 심의 페이지의 뼈대 — 서버 대화 사본을 쓰는 ChatProvider(serverKind) · 보내기 · ■ · 실제 메시지 목록. `__FE__` 는 이 리포의 frontend 절대경로.
_HARNESS = r"""
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { AuthContext } from '__FE__/src/auth/AuthContext';
import { ChatProvider, useChat } from '__FE__/src/state/ChatContext';
import { MessageList } from '__FE__/src/components/chat/MessageList';

function Probe() {
  const { messages, sendMessage, streaming, stop } = useChat();
  return (
    <>
      <button id="send" type="button" onClick={() => sendMessage('힌지 파손 원인')}>send</button>
      <button id="stop" type="button" onClick={stop}>stop</button>
      <span id="streaming">{String(streaming)}</span>
      <MessageList messages={messages} />
    </>
  );
}
(window as unknown as { __mount: () => void }).__mount = () => {
  const user = { subject: 'u1@corp.example', email: 'u1@corp.example', display_name: 'U', groups: [] };
  createRoot(document.getElementById('root')!).render(
    <AuthContext.Provider
      value={{ user, status: 'authenticated', login: () => undefined, logout: async () => undefined, refresh: async () => undefined }}
    >
      <MemoryRouter>
        <ChatProvider storagePrefix="hwax.delib" sendPrefix="/심의 " serverKind="deliberation">
          <Probe />
        </ChatProvider>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
};
"""

STOP_MSG = "사람이 멈췄다 — 의장이 결정문을 내기 전에 멈춰 이 단의 결정문 · 보고서는 없다"

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

# 가짜 백엔드 — 서버 대화를 하나 만들어 주고(srv-1), /agent/chat 은 시험이 __push 로 밀어 넣는 스트림, 멈춤 창구는 시험이 __answer 로 답할
# 때까지 매달린다(누른 동안 단추가 잠기는지 본다). 받은 요청은 __calls 에 적는다.
_STUB = r"""
(() => {
  window.__calls = [];
  const enc = new TextEncoder();
  const json = (body, status = 200) =>
    Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }));
  window.fetch = (url, init = {}) => {
    const u = String(url);
    const method = (init.method || 'GET').toUpperCase();
    window.__calls.push({ url: u, method, body: init.body ? JSON.parse(init.body) : null,
                          csrf: new Headers(init.headers || {}).get('X-CSRF-Token') });
    if (u === '/agent/conversations' && method === 'POST') return json({ id: 'srv-1' });
    if (u === '/agent/conversations') return json({ conversations: [] });
    if (u.startsWith('/agent/conversations/')) return json({ detail: 'conversation not found' }, 404);
    if (u.startsWith('/agent/chat')) {
      const body = new ReadableStream({ start(c) {
        window.__push = (text) => c.enqueue(enc.encode(text));
        window.__end = () => c.close();
        window.__break = (msg) => c.error(new TypeError(msg));
      } });
      return Promise.resolve(new Response(body, { status: 200, headers: { 'Content-Type': 'text/event-stream' } }));
    }
    if (u === '/agent/deliberate/cancel')
      return new Promise((res) => { window.__answer = (status, body) => res(new Response(JSON.stringify(body),
        { status, headers: { 'Content-Type': 'application/json' } })); });
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
const STOP_MSG = '사람이 멈췄다 — 의장이 결정문을 내기 전에 멈춰 이 단의 결정문 · 보고서는 없다';

// where — 브라우저(새 저장소) 또는 같은 저장소의 컨텍스트(새로고침 흉내)
async function open(where, { confirm = true } = {}) {
  const page = await where.newPage({ viewport: { width: 1280, height: 800 } });
  page.setDefaultTimeout(10000);
  page.__errors = [];
  page.__dialogs = [];
  page.on('pageerror', (e) => page.__errors.push(String(e)));
  page.on('dialog', (d) => { page.__dialogs.push(d.message()); return confirm ? d.accept() : d.dismiss(); });
  // 가로챈 주소로 빈 문서를 준다 — about:blank 에서는 document.cookie 가 막혀 CSRF 쿠키를 둘 수 없다(서버는 여전히 없다)
  await page.route('http://harness.invalid/**', (r) =>
    r.fulfill({ contentType: 'text/html', body: '<!doctype html><html><body><div id="root"></div></body></html>' }));
  await page.goto('http://harness.invalid/');
  await page.evaluate(() => { document.cookie = 'hwax_csrf=csrf-1; path=/'; });
  await page.addScriptTag({ path: path.join(OUT, 'stub.js') });
  await page.addScriptTag({ path: path.join(OUT, 'bundle.js') });
  await page.evaluate(() => window.__mount());
  return page;
}
const push = (page, text) => page.evaluate((t) => window.__push(t), text);
const RUN = 'run-1';
// 심의를 열고 1라운드 발언 하나까지 흘린다 — 받는 중인 심의 칸이다. 에이전트는 첫 심의 사건에 실행 id 를 싣는다(runId 가 null 이면 옛 에이전트)
async function start(page, runId = RUN) {
  await page.locator('#send').click();
  await page.waitForFunction(() => typeof window.__push === 'function');
  await push(page, frame('delib', { kind: 'stage', stage: 'discover', ...(runId ? { run_id: runId } : {}) }));
  await push(page, frame('delib', { kind: 'personas', personas: [{ key: 'mech-a', role: '기구' }], totalRounds: 2 }));
  await push(page, frame('delib', { kind: 'stage', stage: 'r1', n: 1 }));
  await push(page, frame('delib', { kind: 'turn', round: 1, persona: 'mech-a', say: '초기 입장' }));
  await page.getByText('초기 입장').first().waitFor();
}
// 다단 심의(/시뮬심의)의 1단 끝 — 에이전트가 실제로 내는 차례다. 의결 → 마무리 표지 → 결정문 · 결과 · 글 → 1단의 done(엔진의 단 하나가 done 으로
// 끝나고 시뮬 래퍼가 그대로 흘린다 — 화면은 여기서 받기를 마친 것으로 본다) → 단 경계 표지(checkpoint) → 좌석 전환(도구 호출 — 몇 초 걸린다) →
// 2단 라운드. stage2=false 면 좌석 전환에서 멈춘다(2단의 심의 사건이 아직 없다)
async function stage1Done(page, { stage2 = true } = {}) {
  await push(page, frame('delib', { kind: 'stage', stage: 'decide' }));
  await push(page, frame('delib', { kind: 'finishing' }));
  await push(page, frame('delib', { kind: 'decision', text: '1단 결정문' }));
  await push(page, frame('delib', { kind: 'outcome', report_id: 41, title: 't' }));
  await push(page, frame('token', { delta: '1단 결정문' }));
  await push(page, frame('result', { type: 'text', content: '1단 결정문' }));
  await push(page, frame('done', {}));
  await push(page, frame('delib', { kind: 'checkpoint', stage: 'sim-1', decision_a: '1단 결정문' }));
  await push(page, frame('status', { step: '좌석 전환 — CAE 전문가 발굴', tool: 'recommend_agents' }));
  if (!stage2) {
    await page.getByText('좌석 전환 — CAE 전문가 발굴').first().waitFor();
    return;
  }
  await push(page, frame('status', { step: '2단 — 해석 설계 심의', tool: null }));
  await push(page, frame('delib', { kind: 'stage', stage: 'discover' }));
  await push(page, frame('delib', { kind: 'stage', stage: 'r1', n: 1 }));
  await push(page, frame('delib', { kind: 'turn', round: 1, persona: 'cae-b', say: '2단 입장' }));
  await page.getByText('2단 입장').first().waitFor();
}
const look = (page) => page.evaluate(() => {
  const btn = document.querySelector('.dv-stop-btn');
  return {
    btn: btn && { text: btn.textContent, disabled: btn.disabled, busy: btn.getAttribute('aria-busy') },
    said: (document.querySelector('.dv-stop-said') || {}).textContent || '',
    note: (document.querySelector('.dv-stop-note') || {}).textContent || '',
    stopped: (document.querySelector('.dv-stopped') || {}).textContent || '',
    plain: (document.querySelector('.dv-plain') || {}).textContent || '',
    decision: (document.querySelector('.dv-decision') || {}).textContent || '',
    error: Boolean(document.querySelector('.chat-error')),
    streaming: document.getElementById('streaming').textContent,
  };
});
const cancels = (page) => page.evaluate(() => window.__calls.filter((c) => c.url === '/agent/deliberate/cancel'));

const SCENARIOS = {
  // 받는 중에 멈춘다 — 누른 동안 잠기고, 창구의 답을 적고, 멈춤 사건이 오면 단추 자리에 '멈춤' 알림이 남는다
  async live(browser) {
    const page = await open(browser);
    await start(page);
    const before = await look(page);
    await page.locator('.dv-stop-btn').click();
    await page.waitForFunction(() => typeof window.__answer === 'function');
    const in_flight = await look(page);
    await page.locator('.dv-stop-btn').click({ force: true, timeout: 1000 }).catch(() => undefined);   // 잠긴 단추를 다시 눌러 본다
    const sent = await cancels(page);
    await page.evaluate(() => window.__answer(200, { conversation_id: 'srv-1', status: 'cancelling', runs: 1, message: '멈춤을 요청했다' }));
    await page.locator('.dv-stop-said').waitFor();
    const answered = await look(page);
    await push(page, frame('delib', { kind: 'cancelled', by: 'u1@corp.example', message: STOP_MSG, run_id: 'run-1' }));
    await push(page, frame('done', {}));
    await page.evaluate(() => window.__end());
    await page.waitForFunction(() => document.getElementById('streaming').textContent === 'false');
    await page.locator('.dv-stopped').waitFor();
    return { before, in_flight, sent, answered, after: await look(page), dialogs: page.__dialogs, errors: page.__errors };
  },
  // 받기가 끊긴 심의 — 결정문 없이 멈춰 보여도 서버에서 아직 돌 수 있다. 단추가 남고, 서버가 '찾지 못했다' 고 하면 그렇게 적는다
  async cut(browser) {
    const page = await open(browser);
    await start(page);
    await page.evaluate(() => window.__break('network error'));
    await page.locator('.chat-error').waitFor();
    const halted = await look(page);
    await page.locator('.dv-stop-btn').click();
    await page.waitForFunction(() => typeof window.__answer === 'function');
    await page.evaluate(() => window.__answer(404, { code: 'delib_not_found', message: '이 대화에서 도는 웹 심의가 없다' }));
    await page.locator('.dv-stop-said').waitFor();
    return { halted, answered: await look(page), dialogs: page.__dialogs, sent: await cancels(page), errors: page.__errors };
  },
  // 받기가 끊긴 심의를 멈춘다(200) — 멈춤 사건이 오지 않는다. 칸에 멈춤(포털이 대화에 남긴 글)을 적고, 같은 저장소로 다시 열어도 멈춤으로 남는다
  async cut_stopped(browser) {
    const ctx = await browser.newContext();
    const page = await open(ctx);
    await start(page);
    await page.evaluate(() => window.__break('network error'));
    await page.locator('.chat-error').waitFor();
    await page.locator('.dv-stop-btn').click();
    await page.waitForFunction(() => typeof window.__answer === 'function');
    await page.evaluate(() => window.__answer(200, { conversation_id: 'srv-1', run_id: 'run-1', status: 'cancelling', runs: 1,
      message: '멈춤을 요청했다', stop_note: '사람이 멈췄다(받기가 끊긴 뒤) — 끊긴 뒤 서버에서 나온 발언은 남지 않았다(포털)' }));
    await page.locator('.dv-stopped').waitFor();
    const answered = await look(page);
    await page.waitForTimeout(800);                 // 브라우저 사본 저장(250ms 디바운스) 뒤
    const again = await open(ctx);                  // 새로고침 — 같은 저장소
    await again.getByText('초기 입장').first().waitFor();
    const reloaded = await look(again);
    const errors = [...page.__errors, ...again.__errors];
    await ctx.close();
    return { answered, reloaded, dialogs: page.__dialogs, errors };
  },
  // 의장이 결정문을 냈다(finishing) — 마무리(쉬운 설명 · 보고서 저장) 동안 에이전트는 멈추지 않는다. 단추를 거두고, 결정문이 오면 끝난 심의다
  async finishing(browser) {
    const page = await open(browser);
    await start(page);
    const before = await look(page);
    await push(page, frame('delib', { kind: 'stage', stage: 'decide' }));
    await push(page, frame('delib', { kind: 'finishing' }));
    await push(page, frame('delib', { kind: 'stage', stage: 'explain' }));
    await push(page, frame('delib', { kind: 'plain', text: '### 한마디로\n간극을 되돌린다' }));
    await push(page, frame('delib', { kind: 'stage', stage: 'report' }));
    await page.locator('.dv-plain').waitFor();
    const tail = await look(page);
    return { before, tail, sent: await cancels(page), errors: page.__errors };
  },
  // 다단 심의 — 1단 결정문 뒤 2단 라운드에서는 다시 멈출 수 있고, 2단 도중에 받기가 끊겨도 멈춤이 남는다(단 사이 done · 표지가 없는 차례)
  async next_stage(browser) {
    const page = await open(browser);
    await start(page);
    await push(page, frame('delib', { kind: 'finishing' }));
    const tail = await look(page);
    await push(page, frame('delib', { kind: 'decision', text: '1단 결정문' }));
    await push(page, frame('delib', { kind: 'stage', stage: 'r1', n: 1 }));
    await push(page, frame('delib', { kind: 'turn', round: 1, persona: 'mech-a', say: '2단 입장' }));
    await page.getByText('2단 입장').first().waitFor();
    const stage2 = await look(page);
    await page.evaluate(() => window.__break('network error'));
    await page.locator('.chat-error').waitFor();
    return { tail, stage2, cut2: await look(page), errors: page.__errors };
  },
  // 다단 심의의 실제 차례(1단의 done · 단 경계 표지) — 2단 도중에 받기가 끊겼다. 보이는 결정문은 1단의 것이고 2단은 서버에서 아직 돈다. 멈춤이
  // 남고, 같은 저장소로 다시 열어도 남으며, 그 심의의 실행 id 로 멈춘다
  async stage2_cut(browser) {
    const ctx = await browser.newContext();
    const page = await open(ctx);
    await start(page);
    await stage1Done(page);
    await page.evaluate(() => window.__break('network error'));
    await page.locator('.chat-error').waitFor();
    const halted = await look(page);
    await page.waitForTimeout(800);                 // 브라우저 사본 저장(250ms 디바운스) 뒤
    const again = await open(ctx);                  // 새로고침 — 같은 저장소
    await again.getByText('2단 입장').first().waitFor();
    const reloaded = await look(again);
    if (reloaded.btn) {                             // 단추가 없으면(종전) 누르지 않고 본 것을 돌려준다 — 시험이 단추 없음으로 붉어진다
      await again.locator('.dv-stop-btn').click();
      await again.waitForFunction(() => typeof window.__answer === 'function');
    }
    const sent = await cancels(again);
    const errors = [...page.__errors, ...again.__errors];
    await ctx.close();
    return { halted, reloaded, sent, dialogs: again.__dialogs, errors };
  },
  // 단 경계 표지 뒤 좌석 전환 중에 끊겼다 — 2단의 심의 사건은 아직 없지만 엔진은 다음 단을 잇는다고 알렸다
  async seat_change_cut(browser) {
    const page = await open(browser);
    await start(page);
    await stage1Done(page, { stage2: false });
    await page.evaluate(() => window.__break('network error'));
    await page.locator('.chat-error').waitFor();
    return { halted: await look(page), errors: page.__errors };
  },
  // 결정문을 받은 뒤 끊겼다 — 한 단 심의는 결정문이 끝이라 멈춤이 없다(종전 그대로). 다단 심의도 마지막 단의 결정문 뒤에는 없다
  async decided_cut(browser) {
    const one = await open(browser);
    await start(one);
    await push(one, frame('delib', { kind: 'stage', stage: 'decide' }));
    await push(one, frame('delib', { kind: 'finishing' }));
    await push(one, frame('delib', { kind: 'decision', text: '결정문 — 보강한다' }));
    await one.getByText('결정문 — 보강한다').first().waitFor();
    await one.evaluate(() => window.__break('network error'));
    await one.locator('.chat-error').waitFor();
    const multi = await open(browser);
    await start(multi);
    await stage1Done(multi);
    await push(multi, frame('delib', { kind: 'finishing' }));
    await push(multi, frame('delib', { kind: 'decision', text: '2단 결정문' }));
    await multi.getByText('2단 결정문').first().waitFor();
    await multi.evaluate(() => window.__break('network error'));
    await multi.locator('.chat-error').waitFor();
    return { single: await look(one), multi: await look(multi), errors: [...one.__errors, ...multi.__errors] };
  },
  // 실행 id 를 싣지 않는 옛 에이전트 — 멈출 열쇠가 없다(대화 id 만으로는 보내지 않는다)
  async no_run(browser) {
    const page = await open(browser);
    await start(page, null);
    const live = await look(page);
    await page.evaluate(() => window.__break('network error'));
    await page.locator('.chat-error').waitFor();
    return { live, halted: await look(page), errors: page.__errors };
  },
  // 이미 끝난 심의(409) · 확인 창에서 '취소' — 보내지 않는다
  async finished(browser) {
    const page = await open(browser);
    await start(page);
    await page.locator('.dv-stop-btn').click();
    await page.waitForFunction(() => typeof window.__answer === 'function');
    await page.evaluate(() => window.__answer(409, { code: 'already_finished', status: 'done', message: '이미 끝난 심의다' }));
    await page.locator('.dv-stop-said').waitFor();
    const answered = await look(page);
    const nope = await open(browser, { confirm: false });
    await start(nope);
    await nope.locator('.dv-stop-btn').click();
    await nope.waitForTimeout(200);
    return { answered, dismissed: { look: await look(nope), sent: await cancels(nope) }, errors: [...page.__errors, ...nope.__errors] };
  },
  // 결정문까지 받은 심의에는 단추가 없다
  async decided(browser) {
    const page = await open(browser);
    await start(page);
    await push(page, frame('delib', { kind: 'decision', text: '결정문 — 보강한다' }));
    await push(page, frame('delib', { kind: 'outcome', report_id: null, title: 't' }));
    await push(page, frame('done', {}));
    await page.evaluate(() => window.__end());
    await page.waitForFunction(() => document.getElementById('streaming').textContent === 'false');
    await page.getByText('결정문 — 보강한다').first().waitFor();
    return { after: await look(page), errors: page.__errors };
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
    out = tmp_path_factory.mktemp("stop")
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


def test_받는_중에_멈추면_누른_동안_잠기고_결과를_적고_멈춤_사건이_오면_알림으로_바뀐다(seen):
    s = seen("live")
    assert s["before"]["btn"] == {"text": "멈춤", "disabled": False, "busy": "false"}, s["before"]
    assert s["in_flight"]["btn"] == {"text": "멈추는 중…", "disabled": True, "busy": "true"}, "요청이 도는 동안 잠긴다"
    assert len(s["sent"]) == 1, "잠긴 단추를 다시 눌러도 두 번 보내지 않는다"
    (call,) = s["sent"]
    assert call["method"] == "POST" and call["body"] == {"conversation_id": "srv-1", "run_id": "run-1"}, "서버 대화 id 와 그 심의의 실행 id 로 멈춘다"
    assert call["csrf"] == "csrf-1", "상태를 바꾸는 요청은 CSRF 를 싣는다"
    (asked,) = s["dialogs"]
    assert asked.startswith("이 심의를 서버에서 멈출까요? 지금까지 받은 발언은 남고") and "Report Archive 에 저장된 초안은 그대로" in asked, asked
    assert "결정문과 보고서는 만들지 않습니다" not in asked, "앞 단 · 앞 회차가 낸 결정문 · 보고서까지 없다고 단정했다"
    assert s["answered"]["said"].startswith("멈춤을 요청했습니다") and s["answered"]["btn"] is None, s["answered"]
    after = s["after"]
    assert after["stopped"] == f"멈춤 — {STOP_MSG}", after
    assert after["btn"] is None and after["said"] == "" and not after["error"], "멈춤은 실패가 아니다 — 오류 상자가 없다"


def test_받기가_끊긴_심의에도_단추가_남고_서버가_찾지_못했다고_하면_그렇게_적는다(seen):
    s = seen("cut")
    h = s["halted"]
    assert h["btn"] == {"text": "멈춤", "disabled": False, "busy": "false"} and h["error"], h
    assert h["note"] == "받기가 끊겼습니다 — 심의는 서버에서 아직 돌 수 있습니다."
    a = s["answered"]
    assert a["said"] == "서버에서 도는 이 심의를 찾지 못했습니다 — 이미 끝났거나 서버가 다시 떴습니다.", a
    assert a["btn"] == {"text": "멈춤", "disabled": False, "busy": "false"}, "멈추지 못했으면 다시 누를 수 있다"
    assert [c["body"] for c in s["sent"]] == [{"conversation_id": "srv-1", "run_id": "run-1"}]
    (asked,) = s["dialogs"]
    assert "받기가 끊긴 뒤 서버에서 나온 발언은 남지 않고" in asked and "지금까지 받은 발언은 남고" not in asked, asked


def test_끊긴_심의를_멈추면_칸에_멈춤을_적고_새로고침_뒤에도_멈춤으로_남는다(seen):
    """A24 검토 — 종전엔 멈춘 사실이 단추 칸의 상태에만 있어, 같은 저장소로 다시 열면 '아직 돌 수 있다' 와 '멈춤' 이 다시 보였다."""
    s = seen("cut_stopped")
    note = "사람이 멈췄다(받기가 끊긴 뒤) — 끊긴 뒤 서버에서 나온 발언은 남지 않았다(포털)"
    for look in (s["answered"], s["reloaded"]):
        assert look["stopped"] == f"멈춤 — {note}", look
        assert look["btn"] is None and look["note"] == "", look


def test_의장이_결정문을_낸_뒤의_마무리에는_멈춤을_거둔다(seen):
    """A24 검토 — 보고 단계(Report Archive 저장)에서 누르면 다 만든 결정문이 버려졌다. 에이전트도 그때는 409 finishing 이다."""
    s = seen("finishing")
    assert s["before"]["btn"] == {"text": "멈춤", "disabled": False, "busy": "false"}, s["before"]
    assert s["tail"]["btn"] is None and s["tail"]["plain"], s["tail"]
    assert s["sent"] == []


def test_다단_심의는_앞_단의_결정문_뒤_다음_단에서_다시_멈출_수_있다(seen):
    s = seen("next_stage")
    assert s["tail"]["btn"] is None
    assert s["stage2"]["btn"] == {"text": "멈춤", "disabled": False, "busy": "false"}, s["stage2"]
    # 2단 도중에 받기가 끊겼다 — 1단 결정문이 보여도 2단은 서버에서 아직 돈다(종전엔 결정문이 있으면 끊긴 칸으로 보지 않아 단추가 사라졌다)
    cut2 = s["cut2"]
    assert cut2["btn"] == {"text": "멈춤", "disabled": False, "busy": "false"} and cut2["error"], cut2
    assert cut2["note"] == "받기가 끊겼습니다 — 심의는 서버에서 아직 돌 수 있습니다." and "1단 결정문" in cut2["decision"], cut2


def test_다단_심의의_실제_차례에서_2단_도중에_끊기면_멈춤이_남고_새로고침_뒤에도_그_실행으로_멈춘다(seen):
    """/시뮬심의 는 단마다 done 을 내고(1단의 done 에서 화면은 받기를 마친다) 단 경계 표지(checkpoint) 뒤 2단을 돈다. 2단 도중에 받기가 끊기면
    보이는 결정문은 1단의 것이고 2단은 서버에서 아직 돈다 — 멈춤이 남아야 한다(10-31 A24 검토가 남긴 화면 틈 1)."""
    s = seen("stage2_cut")
    for look in (s["halted"], s["reloaded"]):
        assert look["btn"] == {"text": "멈춤", "disabled": False, "busy": "false"}, look
        assert look["note"] == "받기가 끊겼습니다 — 심의는 서버에서 아직 돌 수 있습니다." and look["error"], look
        assert "1단 결정문" in look["decision"] and look["stopped"] == "", look
    assert [c["body"] for c in s["sent"]] == [{"conversation_id": "srv-1", "run_id": "run-1"}], "그 심의의 실행 id 로 멈춘다"
    (asked,) = s["dialogs"]
    assert "받기가 끊긴 뒤 서버에서 나온 발언은 남지 않고" in asked, asked


def test_단_경계_표지_뒤_좌석_전환_중에_끊겨도_멈춤이_남는다(seen):
    """엔진은 1단 결정문 뒤 단 경계 표지(checkpoint)를 내고 좌석 전환(도구 호출)을 한 뒤 2단을 연다 — 그사이에 끊겨도 다음 단은 서버에서 돈다."""
    h = seen("seat_change_cut")["halted"]
    assert h["btn"] == {"text": "멈춤", "disabled": False, "busy": "false"} and h["error"] and "1단 결정문" in h["decision"], h


def test_결정문을_받은_뒤_끊긴_한_단_심의와_마지막_단을_마친_다단_심의에는_멈춤이_없다(seen):
    """한 단 심의는 결정문이 끝이다(종전 규칙 그대로) — 다단 심의도 마지막 단의 결정문 뒤에는 다음 단이 없다."""
    s = seen("decided_cut")
    for look in (s["single"], s["multi"]):
        assert look["btn"] is None and look["note"] == "" and look["error"], look
    assert "2단 결정문" in s["multi"]["decision"]


def test_실행_id_가_없으면_멈춤_단추가_없다(seen):
    """옛 에이전트(실행 id 를 싣지 않는다) — 대화 id 만으로 보내면 같은 대화의 다른 심의를 접을 수 있다. 단추를 내지 않는다."""
    s = seen("no_run")
    assert s["live"]["btn"] is None and s["halted"]["btn"] is None and s["halted"]["error"], s


def test_이미_끝난_심의는_그렇게_적고_확인_창에서_물리면_보내지_않는다(seen):
    s = seen("finished")
    assert s["answered"]["said"] == "이미 끝난 심의입니다 — 멈출 것이 없습니다.", s["answered"]
    assert s["dismissed"]["sent"] == [] and s["dismissed"]["look"]["said"] == ""


def test_결정문까지_받은_심의에는_멈춤이_없다(seen):
    s = seen("decided")
    assert s["after"]["btn"] is None and s["after"]["note"] == "" and s["after"]["stopped"] == ""
