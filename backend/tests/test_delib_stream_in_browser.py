# 심의·챗 스트림 화면을 헤드리스 브라우저에 실제로 올려, 오래 걸리는 실행이 어떻게 보이는지 본다 — 서버는 띄우지 않는다(가짜 fetch · 가짜 시계)
"""왜 — 긴 심의에서 화면이 하는 일은 대부분 '시간이 흐르는 동안' 일어난다. 신호가 15초마다 오는 동안 무엇을 보이는가,
45초 끊기면 무엇으로 바뀌는가, 몇 시간이 지나도 스트림을 스스로 끊지 않는가. 타입 검사·린트로는 안 잡히고, 순수 함수 시험
(test_stream_liveness_units)은 판정까지만 본다 — 그 판정이 실제 화면에 붙어 있는지는 여기서 본다.

실제 컴포넌트(ChatProvider · MessageList · ActivityPanel)를 esbuild 로 한 파일로 묶어 빈 문서에 올리고, fetch 는 시험이
한 프레임씩 밀어 넣는 스트림으로, 시계는 playwright 의 가짜 시계로 바꾼다(test_admin_pages_in_browser 와 같은 길).
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

# 심의 페이지의 뼈대만 — 보내기·중지 버튼과 실제 메시지 목록·활동 패널. `__FE__` 는 이 리포의 frontend 절대경로로 바꿔 쓴다.
_HARNESS = r"""
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { AuthContext } from '__FE__/src/auth/AuthContext';
import { ChatProvider, useChat } from '__FE__/src/state/ChatContext';
import { MessageList } from '__FE__/src/components/chat/MessageList';
import { ActivityPanel } from '__FE__/src/components/chat/ActivityPanel';
import { HandoffBrief } from '__FE__/src/components/chat/HandoffBrief';

function Probe() {
  const { messages, sendMessage, streaming, stop } = useChat();
  return (
    <>
      <button id="send" type="button" onClick={() => sendMessage('힌지 파손 원인')}>send</button>
      <button id="stop" type="button" onClick={stop}>stop</button>
      <span id="streaming">{String(streaming)}</span>
      <MessageList messages={messages} />
      <ActivityPanel messages={messages} />
    </>
  );
}
// 챗 → 심의 브리프(핸드오프) — 열리자마자 화두 제안과 좌석 발굴 도우미를 부른다
const CONV = {
  id: 'c1', title: 't', createdAt: 0, updatedAt: 0,
  messages: [{ id: 'm1', role: 'user' as const, text: '힌지가 왜 깨지나' }, { id: 'm2', role: 'assistant' as const, text: '응력 집중입니다' }],
};
(window as unknown as { __mount: (what?: string) => void }).__mount = (what) => {
  const user = { subject: 'u1@corp.example', email: 'u1@corp.example', display_name: 'U', groups: [] };
  createRoot(document.getElementById('root')!).render(
    <AuthContext.Provider
      value={{ user, status: 'authenticated', login: () => undefined, logout: async () => undefined, refresh: async () => undefined }}
    >
      <MemoryRouter>
        <ChatProvider storagePrefix="hwax.delib" sendPrefix="/심의 ">
          {what === 'brief' ? <HandoffBrief conv={CONV} onClose={() => undefined} /> : <Probe />}
        </ChatProvider>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
};
"""

# esbuild 는 vite 의 의존성이라 최상위 node_modules 에 없다(pnpm) — vite 자리에서 찾는다. CSS·글꼴은 비운다(동작만 본다).
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

# 가짜 백엔드 — /agent/chat 은 시험이 __push 로 한 프레임씩 밀어 넣는 스트림을 준다. __chat 으로 다른 응답(422 등)을 줄 수 있다.
_STUB = r"""
(() => {
  window.__calls = [];
  window.__aborted = false;
  window.__chat = null;
  const enc = new TextEncoder();
  const json = (body, status = 200) =>
    Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }));
  window.fetch = (url, init = {}) => {
    const u = String(url);
    window.__calls.push({ url: u, body: init.body ? JSON.parse(init.body) : null });
    if (u.startsWith('/agent/chat')) {
      if (window.__chat) return window.__chat();
      if (init.signal) init.signal.addEventListener('abort', () => { window.__aborted = true; });
      const body = new ReadableStream({ start(c) {
        window.__push = (text) => c.enqueue(enc.encode(text));
        window.__end = () => c.close();
        window.__break = (msg) => c.error(new TypeError(msg));
      } });
      return Promise.resolve(new Response(body, { status: 200, headers: { 'Content-Type': 'text/event-stream' } }));
    }
    // 도우미 경로 — __helpers[이름] 이 'hang' 이면 답하지 않고 매달린다(중단 신호에만 풀린다). 객체면 그 답을 준다.
    const helper = (u.match(/^\/agent\/deliberate\/(experts|topic|clarify|voc)/) || [])[1];
    if (helper && window.__helpers && window.__helpers[helper] === 'hang')
      return new Promise((_, rej) => init.signal && init.signal.addEventListener('abort', () =>
        rej(new DOMException('aborted', 'AbortError'))));
    if (helper && window.__helpers && window.__helpers[helper]) return json(window.__helpers[helper]);
    if (helper === 'topic') return json({ topic: '', why: '', options: [] });
    if (helper === 'clarify') return json({ applicable: false, slots: [], ask: [] });
    if (u.startsWith('/agent/deliberate/experts')) return json({ recommended: [], pool: [] });
    return json({ detail: 'stub: no route ' + u }, 404);
  };
})();
"""

# 시나리오 구동기 — 묶은 화면을 빈 문서에 올리고 프레임을 밀어 넣으며 시계를 돌린다. 시나리오마다 새 탭이다.
_DRIVE = r"""
const { createRequire } = require('module');
const path = require('path');
const [FE, OUT] = process.argv.slice(2);
const { chromium } = createRequire(path.join(FE, 'package.json'))('@playwright/test');

const frame = (event, data) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
const PING = frame('ping', { idle_s: 15, ts: 1 });

async function open(browser, { seed = '', what = '' } = {}) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  page.setDefaultTimeout(10000);
  page.__errors = [];
  page.on('pageerror', (e) => page.__errors.push(String(e)));
  // 가로챈 주소로 빈 문서를 준다 — about:blank 에서는 document.cookie 가 막혀 apiFetch 의 CSRF 읽기가 던진다(서버는 여전히 없다)
  await page.route('http://harness.invalid/**', (r) =>
    r.fulfill({ contentType: 'text/html', body: '<!doctype html><html><body><div id="root"></div></body></html>' }));
  await page.clock.install({ time: new Date('2026-10-08T00:00:00Z') });
  await page.goto('http://harness.invalid/');
  await page.addScriptTag({ path: path.join(OUT, 'stub.js') });
  if (seed) await page.evaluate(seed);
  await page.addScriptTag({ path: path.join(OUT, 'bundle.js') });
  await page.evaluate((w) => window.__mount(w), what);
  return page;
}
const push = (page, text) => page.evaluate((t) => window.__push(t), text);
// 화면 아래(메시지)와 활동 패널의 생존 표시 — [{ state, text }]
const pulse = (page) => page.evaluate(() =>
  Array.from(document.querySelectorAll('[data-live]')).map((el) => ({ state: el.dataset.live, text: el.textContent })));
const state = (page) => page.evaluate(() => ({ streaming: document.getElementById('streaming').textContent, aborted: window.__aborted }));
async function start(page) {
  await page.locator('#send').click();
  await page.waitForFunction(() => typeof window.__push === 'function');
  await push(page, frame('status', { step: '1라운드 발언 대기', tool: null }));
  await page.getByText('1라운드 발언 대기').first().waitFor();
}
// 시계를 돌린 뒤 화면이 따라올 틈을 준다(가짜 시계라 실제로는 수 밀리초다)
async function forward(page, ms) { await page.clock.fastForward(ms); await page.waitForTimeout(60); }

const SCENARIOS = {
  // heartbeat 가 오는 서버 — 오는 동안, 끊겼을 때, 다시 왔을 때, 끝났을 때
  async heartbeat(browser) {
    const page = await open(browser);
    await start(page);
    const just_started = await pulse(page);
    await forward(page, 14000); await push(page, PING);
    await forward(page, 15000); await push(page, PING);
    await forward(page, 3000);
    const alive = await pulse(page);
    await forward(page, 50000);                       // ping 세 번이 빠졌다
    const silent = await pulse(page);
    const while_silent = await state(page);
    await push(page, PING); await forward(page, 2000);
    const back = await pulse(page);
    await push(page, frame('delib', { kind: 'turn', round: 1, persona: 'mech-a', say: '초기 입장' }));
    await forward(page, 2000);
    const after_progress = await pulse(page);
    await push(page, frame('done', {})); await page.evaluate(() => window.__end());
    await page.waitForFunction(() => document.getElementById('streaming').textContent === 'false');
    return { just_started, alive, silent, while_silent, back, after_progress, done: await pulse(page), errors: page.__errors };
  },
  // heartbeat 가 없는 옛 서버 — LLM 호출 한 번이 통째로 조용하다. 침묵을 끊김으로 읽으면 건강한 심의를 죽었다고 말한다.
  async old_server(browser) {
    const page = await open(browser);
    await start(page);
    await forward(page, 10 * 60000);
    return { ten_min: await pulse(page), st: await state(page), errors: page.__errors };
  },
  // 몇 시간이 지나도 브라우저가 스스로 끊지 않는다 — heartbeat 가 오든, 끊겼든
  async never_cuts(browser) {
    const page = await open(browser);
    await start(page);
    await push(page, PING);
    for (let h = 0; h < 6; h++) { await forward(page, 3600000); }
    const six_hours_silent = { st: await state(page), pulse: await pulse(page) };
    await push(page, frame('delib', { kind: 'stage', stage: 'decide' }));
    await push(page, frame('delib', { kind: 'decision', text: '여섯 시간 뒤의 결정문' }));
    await push(page, frame('done', {})); await page.evaluate(() => window.__end());
    await page.getByText('여섯 시간 뒤의 결정문').first().waitFor();
    const chat_calls = await page.evaluate(() => window.__calls.filter((c) => c.url.startsWith('/agent/chat')).length);
    return { six_hours_silent, st: await state(page), chat_calls, errors: page.__errors };
  },
  // 한도가 걸렸을 때 화면이 하는 말 — 응답 도중 절단, 포털 릴레이의 침묵 한도, 엔진의 LLM 호출 한도, 범위를 넘은 값(422)
  async errors(browser) {
    const out = { errors: [] };
    const box = (page) => page.evaluate(() => {
      const el = document.querySelector('.chat-error');
      return el && { title: el.querySelector('.chat-error-title').textContent.replace(/^⚠\s*/, ''),
                     hint: (el.querySelector('.chat-error-hint') || {}).textContent || '',
                     retry: Boolean(el.querySelector('.chat-error-retry')),
                     kept: document.body.textContent.includes('초기 입장'),
                     streaming: document.getElementById('streaming').textContent };
    });
    const turn = frame('delib', { kind: 'turn', round: 1, persona: 'mech-a', say: '초기 입장' });
    for (const [name, finish] of [
      ['cut', (page) => page.evaluate(() => window.__break('network error'))],
      ['idle', async (page) => { await push(page, frame('error', { code: 'agent_stream_idle', message: IDLE })); await push(page, frame('done', {})); await page.evaluate(() => window.__end()); }],
      ['llm', async (page) => { await push(page, frame('error', { code: 'deliberation_error', message: '심의 처리 중 오류: Request timed out.' })); await push(page, frame('done', {})); await page.evaluate(() => window.__end()); }],
    ]) {
      const page = await open(browser);
      await start(page);
      await push(page, frame('delib', { kind: 'stage', stage: 'r1', n: 2 }));
      await push(page, turn);
      await page.getByText('초기 입장').first().waitFor();
      await finish(page);
      await page.locator('.chat-error').waitFor();
      out[name] = await box(page);
      out.errors.push(...page.__errors);
    }
    const page = await open(browser, { seed: `window.__chat = () => Promise.resolve(new Response(JSON.stringify({ detail: [
      { loc: ['body', 'delib_opts', 'timeout_s'], msg: 'Input should be less than or equal to 14400', type: 'less_than_equal' }] }),
      { status: 422, headers: { 'Content-Type': 'application/json' } }))` });
    await page.locator('#send').click();
    await page.locator('.chat-error').waitFor();
    out.rejected = await box(page);
    out.errors.push(...page.__errors);
    return out;
  },
  // 근거 카드의 딱지 — 포함된 근거 · 좌석에 주지 않은 근거 · 근거가 아닌 알림(엔진 notice=true)
  async evidence(browser) {
    const page = await open(browser);
    await start(page);
    await push(page, frame('delib', { kind: 'stage', stage: 'r1', n: 2 }));
    const card = (source, extra) => frame('delib', { kind: 'evidence', source, text: source + ' 본문', ...extra });
    await push(page, card('SignalForge 환기', { included: true }));
    await push(page, card('사전 근거 예산 초과', { included: false }));
    await push(page, card('의장 전사 상한 초과', { included: false, notice: true }));
    await push(page, card('좌석 유실', { included: false, notice: true }));
    await page.getByText('좌석 유실').first().waitFor();
    const flags = await page.evaluate(() => Array.from(document.querySelectorAll('.dv-evidence summary')).map((el) =>
      [el.childNodes[1].textContent, el.querySelector('.dv-ev-flag').textContent]));
    return { flags, errors: page.__errors };
  },
  // 심의 브리프의 도우미(화두 제안·좌석 발굴)가 오래 걸릴 때 — 몇 초째인지 보이고, 기다리지 않고 넘길 수 있다
  async brief(browser) {
    const look = (page) => page.evaluate(() => ({
      topic_busy: (document.querySelector('.cx-brief-note') || {}).textContent || '',
      seat_label: document.querySelector('.cx-brief-seatlabel').textContent,
      skips: Array.from(document.querySelectorAll('.cq-skip')).map((b) => b.textContent),
      topic: document.querySelector('.cx-brief textarea').value,
      empty: (document.querySelector('.cx-brief-empty') || {}).textContent || '',
      notice: Array.from(document.querySelectorAll('.cx-brief-lowconf')).map((el) => el.textContent),
      can_start: !document.querySelector('.cx-brief-go').disabled,
    }));
    const page = await open(browser, { what: 'brief', seed: `window.__helpers = { topic: 'hang', experts: 'hang' }` });
    await page.locator('.cx-brief-seatlabel').waitFor();
    await forward(page, 600);                          // 좌석 발굴은 500ms 뒤에 나간다(입력 디바운스)
    await forward(page, 90000);
    const waiting = await look(page);
    await page.locator('.cx-brief-note .cq-skip').click();
    await page.waitForFunction(() => !document.querySelector('.cx-brief-note'));
    const topic_skipped = await look(page);
    await page.locator('.cx-brief-seatlabel .cq-skip').click();
    await page.waitForFunction(() => !document.querySelector('.cq-skip'));
    const seats_skipped = await look(page);
    // 포털 한도가 걸려 폴백으로 온 경우 — 사유를 말한다
    const msg = '도우미 응답이 600초 안에 오지 않아 기본값으로 진행한다(AGENT_UNARY_TIMEOUT_S)';
    const late = await open(browser, { what: 'brief', seed: `window.__helpers = {
      topic: { topic: '힌지가 왜 깨지나', why: '', options: [], error: 'agent_timeout', message: '${msg}' },
      experts: { recommended: [], pool: [], error: 'agent_timeout', message: '${msg}' } }` });
    await late.locator('.cx-brief-seatlabel').waitFor();
    await forward(late, 700);
    await late.waitForFunction(() => !document.querySelector('.cq-skip'));
    return { waiting, topic_skipped, seats_skipped, timed_out: await look(late), errors: [...page.__errors, ...late.__errors] };
  },
};

const IDLE = '에이전트 서버가 46800초 동안 아무 신호도 보내지 않아 구독을 끊었다(AGENT_STREAM_IDLE_TIMEOUT_S). ' +
  '심의는 서버에서 계속 돌 수 있다 — 다시 시작하기 전에 Report Archive 와 대화 목록을 확인하라';

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
    out = tmp_path_factory.mktemp("stream")
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


def test_신호가_오는_동안은_살아_있다고_끊기면_신호_없음이라고_보인다(seen):
    """깜박이는 점과 마지막 상태줄뿐이던 자리다 — 한 시간 전에 죽은 스트림과 생각 중인 좌석이 똑같이 보였다.
    표시는 두 곳에 같이 뜬다(도는 턴 아래 · 활동 패널 머리)."""
    s = seen("heartbeat")
    assert s["just_started"] == [], "진행이 방금 있었으면 말하지 않는다"
    assert [p["state"] for p in s["alive"]] == ["alive", "alive"], s["alive"]
    assert all(p["text"] == "서버 살아 있음 · 마지막 진행 32초 전" for p in s["alive"]), s["alive"]
    assert [p["state"] for p in s["silent"]] == ["silent", "silent"], "ping 세 번(45초)이 빠지면 바뀐다"
    assert all(p["text"].startswith("신호 없음 53초 — 연결이 끊겼을 수") for p in s["silent"]), s["silent"]
    assert s["while_silent"] == {"streaming": "true", "aborted": False}, "신호가 끊겨도 스트림을 끊지 않는다 — 표시만 한다"
    assert [p["state"] for p in s["back"]] == ["alive", "alive"], "신호가 다시 오면 돌아온다"
    assert s["after_progress"] == [] and s["done"] == [], "진행이 다시 흐르거나 끝나면 표시는 사라진다"


def test_heartbeat_가_없는_옛_서버의_침묵을_끊김으로_읽지_않는다(seen):
    """재기동을 건너뛴 박스에서는 옛 엔진이 새 화면과 섞여 돈다. 거기서는 LLM 호출 한 번이 통째로 조용하다."""
    s = seen("old_server")
    assert s["ten_min"] == [{"state": "unknown", "text": "마지막 진행 10분 전"}] * 2, s["ten_min"]
    assert s["st"] == {"streaming": "true", "aborted": False}


def test_몇_시간이_지나도_화면이_스트림을_스스로_끊지_않는다(seen):
    """브라우저에는 타임아웃도 자동 중단도 없다 — 끊을지는 중지 버튼을 쥔 사람이 정한다. 여섯 시간 조용한 뒤에 온 결정문도 받는다."""
    s = seen("never_cuts")
    assert s["six_hours_silent"]["st"] == {"streaming": "true", "aborted": False}
    assert [p["state"] for p in s["six_hours_silent"]["pulse"]] == ["silent", "silent"]
    assert "신호 없음 6시간" in s["six_hours_silent"]["pulse"][0]["text"]
    assert s["st"] == {"streaming": "false", "aborted": False}, "끝까지 받고 정상으로 닫힌다"
    assert s["chat_calls"] == 1, "다시 보내지 않는다 — 재시도는 두 번째 심의를 나란히 돌린다"


def test_한도가_걸리면_화면이_무엇이_걸렸고_어디를_볼지_말한다(seen):
    """종전 — 절단은 원문 'TypeError: network error', LLM 한도는 '라운드 수를 줄이거나 무거운 옵션을 끄라', 422 는
    'Request failed (422)'. 셋 다 손잡이를 말하지 않았고, 어느 경우든 '다시 시도' 가 심의 전체를 새로 돌렸다."""
    s = seen("errors")
    cut = s["cut"]
    assert cut["title"] == "스트림이 끊겼습니다" and cut["kept"] and cut["streaming"] == "false", cut
    assert "NGINX_AGENT_READ_TIMEOUT" in cut["hint"] and "서버에서 계속 돌 수" in cut["hint"] and "두 번째 심의" in cut["hint"]
    assert "TypeError" not in cut["title"], "원문이 제목으로 뜨던 자리다"

    idle = s["idle"]
    assert idle["title"] == "에이전트 서버의 신호가 끊겨 구독을 닫았습니다" and idle["kept"]
    assert "46800초" in idle["hint"] and "AGENT_STREAM_IDLE_TIMEOUT_S" in idle["hint"], "포털이 준 문구를 그대로 보인다"

    llm = s["llm"]
    assert llm["title"] == "LLM 호출이 제한 시간에 걸렸습니다", llm
    assert "timeout_s" in llm["hint"] and "DELIB_TIMEOUT_S" in llm["hint"] and "14400초" in llm["hint"]
    assert "줄이거나" not in llm["hint"] and "끄고" not in llm["hint"], "줄이라고 권하지 않는다"

    rej = s["rejected"]
    assert rej["title"] == "요청 값이 허용 범위를 벗어났습니다" and rej["streaming"] == "false", rej
    assert "delib_opts.timeout_s: Input should be less than or equal to 14400" in rej["hint"]
    assert rej["retry"] is False, "같은 값으로 다시 보내면 같은 거절이다"
    assert cut["retry"] and idle["retry"] and llm["retry"]


def test_브리프의_도우미가_오래_걸리면_몇_초째인지_보이고_건너뛸_수_있다(seen):
    """화두 제안과 좌석 발굴은 도는 패널 뒤에 줄을 서면 몇 분이 걸린다. 종전에는 '뽑는 중…' · '(발굴 중…)' 이 경과 표시도
    넘어갈 길도 없이 돌았다. 브라우저 타임아웃은 여전히 없다 — 한도는 포털 한 곳(AGENT_UNARY_TIMEOUT_S)이다."""
    s = seen("brief")
    w = s["waiting"]
    assert "뽑는 중… 90초" in w["topic_busy"] and "(발굴 중… 90초)" in w["seat_label"], w
    assert w["skips"] == ["건너뛰기", "건너뛰기"] and w["can_start"], "기다리는 동안에도 심의는 시작할 수 있다"
    t = s["topic_skipped"]
    assert t["topic_busy"] == "" and t["topic"] == "힌지가 왜 깨지나", "넘기면 서버가 실패했을 때와 같은 폴백 — 첫 발화 그대로"
    assert t["skips"] == ["건너뛰기"] and "발굴 중" in t["seat_label"], "화두만 넘겼다 — 좌석 발굴은 계속 돈다"
    z = s["seats_skipped"]
    assert z["skips"] == [] and "추천 좌석 없음 — 심의가 자동 발굴합니다" in z["empty"] and z["can_start"]
    late = s["timed_out"]
    assert len(late["notice"]) == 1 and "600초" in late["notice"][0] and "AGENT_UNARY_TIMEOUT_S" in late["notice"][0]
    assert "첫 발화 그대로" in late["notice"][0]
    assert "AGENT_UNARY_TIMEOUT_S" in late["empty"] and "심의가 자동 발굴합니다" in late["empty"], late


def test_근거가_아닌_알림_카드는_알림이라고_뜬다(seen):
    """엔진은 알림(의장 전사를 줄였다 · 좌석이 유실됐다)도 included=false 근거 카드로 보낸다. 그 카드에 '좌석에 주지 않음' 이
    붙으면 '의장 입력을 줄였다' 가 '좌석이 못 받았다' 로 읽힌다 — 좌석은 전부 받았다. 엔진이 notice=true 로 가른다."""
    assert seen("evidence")["flags"] == [
        ["SignalForge 환기", "심의에 포함"],
        ["사전 근거 예산 초과", "좌석에 주지 않음"],
        ["의장 전사 상한 초과", "알림"],
        ["좌석 유실", "알림"],
    ]
