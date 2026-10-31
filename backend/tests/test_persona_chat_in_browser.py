# 전문가 페르소나 화면을 헤드리스 브라우저에 실제 컴포넌트로 올려 본다 — 같은 사람이 화면마다 같은 색인지(서버는 띄우지 않는다, 가짜 fetch)
"""왜 — 색은 '같은 사람' 을 눈으로 잇는 유일한 단서다. 챗 말풍선 · 고르기 화면 · 입력창 알약은 이름으로, 회의록 · 관계도 · 띵킹은
키로 색을 뽑아 같은 사람이 대개 다른 색이었다(docs/leftovers-1017/triage-1031.md B12). 소스 시험(test_persona_color_key)은 인자가
키인지까지만 본다 — 실제 화면의 계산된 색이 하나인지는 여기서 본다.

test_delib_stream_in_browser 와 같은 길 — 실제 컴포넌트(ChatProvider · MessageList · ExpertToggle)를 esbuild 로 한 파일로 묶어 빈 문서에
올리고 fetch 를 가짜로 바꾼다. 도구는 프론트가 이미 가진 것만 쓴다. 없으면 건너뛴다(운영 박스).
"""
import json
import subprocess

import pytest

from tests.test_delib_stream_in_browser import _BUILD, FE, pytestmark  # noqa: F401 — 같은 도구가 없으면 같이 건너뛴다

# 같은 전문가 한 명 — 이름과 키가 옛 해시로 서로 다른 색이 되는 짝이다(키 #3f7d80 · 원래 이름 #7a5aa6). 같은 색이 나오는 짝이면
# 이름으로 칠해도 이 시험이 통과해 버린다.
_HARNESS = r"""
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { AuthContext } from '__FE__/src/auth/AuthContext';
import { ChatProvider, useChat } from '__FE__/src/state/ChatContext';
import { MessageList } from '__FE__/src/components/chat/MessageList';
import { ExpertToggle } from '__FE__/src/components/chat/ExpertToggle';
import type { Message } from '__FE__/src/types/chat';

const KEY = 'mech-a';
const NAME = '기구 강도 전문가 (Mechanical Strength Expert)';
// 한 사람이 네 화면에 — 챗 말풍선(지정 전문가의 답) · 심의 회의록(소개 · 발언) · 띵킹 좌석. 발언에는 엔진처럼 키만 싣는다.
const SHOWN: Message[] = [
  { id: 'u1', role: 'user', text: '힌지 강도 봐 줘' },
  { id: 'a1', role: 'assistant', text: '응력 집중입니다', persona: { key: KEY, name: NAME } },
  { id: 'd1', role: 'assistant', text: '', delib: {
      stages: ['r1'], stage: 'r1', totalRounds: 1, personas: [{ key: KEY }, { key: 'cae-b' }],
      turns: [{ round: 1, persona: KEY, say: '초기 입장', ts: 0 }, { round: 1, persona: 'cae-b', say: '다른 입장', ts: 0 }] } },
  { id: 't1', role: 'assistant', text: '', think: { seats: [{ key: KEY, name: NAME, verdict: 'answer', answer: '좌석 답' }] } },
];
function Colours() {
  const { setPinnedAgent } = useChat();
  return (
    <>
      <button id="pin" type="button" onClick={() => setPinnedAgent(KEY, NAME)}>pin</button>
      <ExpertToggle />
      <MessageList messages={SHOWN} />
    </>
  );
}
// 챗 화면 — 전문가를 고르고 보내 답을 받는다. 같은 대화를 서버 사본으로 다시 여는 단추도 둔다. 슬래시 트리거로 보내는 단추 둘은
// 고른 전문가 대신 띵킹 · 심의가 답하는 발화다(에이전트 서버가 트리거로 가른다).
function Chat() {
  const { messages, sendMessage, setPinnedAgent, selectConversation, streaming } = useChat();
  return (
    <>
      <button id="pin" type="button" onClick={() => setPinnedAgent(KEY, NAME)}>pin</button>
      <button id="send" type="button" onClick={() => sendMessage('힌지 강도 봐 줘')}>send</button>
      <button id="send-think" type="button" onClick={() => sendMessage('/띵킹 힌지 강도 봐 줘')}>think</button>
      <button id="send-delib" type="button" onClick={() => sendMessage('/심의 힌지 파손 원인')}>delib</button>
      <button id="open" type="button" onClick={() => selectConversation('srv-1')}>open</button>
      <span id="streaming">{String(streaming)}</span>
      <MessageList messages={messages} />
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
        <ChatProvider storagePrefix="hwax.chat" serverKind="chat">
          {what === 'chat' ? <Chat /> : <Colours />}
        </ChatProvider>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
};
"""

# 가짜 백엔드 — 전문가 명부(회의록이 키를 이름으로 바꾸고 고르기 화면이 찾는다), 서버 대화(만들기 · 목록 __convs · 사본 __conv),
# 챗 스트림(__push · __end). 부른 차례를 __calls 에 적는다.
_STUB = r"""
(() => {
  window.__calls = [];
  window.__convs = [];
  window.__conv = null;
  const enc = new TextEncoder();
  const json = (body, status = 200) =>
    Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }));
  window.fetch = (url, init = {}) => {
    const u = String(url);
    const method = (init.method || 'GET').toUpperCase();
    window.__calls.push({ url: u, method, body: typeof init.body === 'string' ? JSON.parse(init.body) : null });
    if (u.startsWith('/agent/deliberate/experts')) return json({ recommended: [], pool: [
      { key: 'mech-a', name: '기구 강도 전문가 (Mechanical Strength Expert)', tags: [] },
      { key: 'cae-b', name: '구조 해석 전문가 (Structural Analysis Expert)', tags: [] }] });
    if (u === '/agent/conversations' && method === 'GET') return json({ conversations: window.__convs });
    if (u === '/agent/conversations' && method === 'POST') return json({ id: 'srv-1' });
    if (u === '/agent/conversations/srv-1' && method === 'GET')
      return window.__conv ? json(window.__conv) : json({ detail: 'not found' }, 404);
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

// ctx 를 넘기면 그 브라우저 문맥(같은 localStorage)에 새 탭을 연다 — 새로고침 · 다시 열기. 없으면 새 문맥(다른 기기)이다.
async function open(browser, what = '', { ctx = null, before = null } = {}) {
  const page = ctx ? await ctx.newPage() : await browser.newPage({ viewport: { width: 1280, height: 900 } });
  page.setDefaultTimeout(10000);
  page.__errors = [];
  page.on('pageerror', (e) => page.__errors.push(String(e)));
  await page.route('http://harness.invalid/**', (r) =>
    r.fulfill({ contentType: 'text/html', body: '<!doctype html><html><body><div id="root"></div></body></html>' }));
  await page.goto('http://harness.invalid/');
  await page.addScriptTag({ path: path.join(OUT, 'stub.js') });
  await page.addScriptTag({ path: path.join(OUT, 'bundle.js') });
  if (before) await page.evaluate(before);                 // 띄우기 전에 가짜 서버 값을 둔다(띄우자마자 목록을 읽는다)
  await page.evaluate((w) => window.__mount(w), what);
  return page;
}
const frame = (event, data) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
// 지정 전문가의 말풍선 — 이름 · 키 · 아바타 색 · 테두리 색 · 본문
const bubble = (page) => page.evaluate(() => {
  const el = document.querySelector('.msg.is-persona');
  return el && {
    name: el.querySelector('.msg-who-name').textContent,
    key: el.querySelector('.msg-who-key').textContent,
    av: getComputedStyle(el.querySelector('.msg-av')).backgroundColor,
    edge: getComputedStyle(el.querySelector('.msg-content')).borderLeftColor,
    text: el.querySelector('.msg-content').textContent,
  };
});
// 포털이 서버 대화에 남기는 꼴 그대로 — 사람 발화의 meta 에 고른 전문가(routes.py `_pin`), 답은 본문만(agent/routes.py 의 _save)
const SERVER_COPY = (ts) => ({
  id: 'srv-1', title: '힌지 강도 봐 줘', kind: 'chat', source: 'web', created_at: ts, updated_at: ts,
  messages: [
    { role: 'user', persona: null, round: null, content: '힌지 강도 봐 줘', ts,
      meta: { pinned_agent: 'mech-a', pinned_agent_name: '기구 강도 전문가 (Mechanical Strength Expert)' } },
    { role: 'assistant', persona: null, round: null, content: '힌지 브래킷 R 이 작아 응력이 몰립니다.', ts: ts + 5, meta: null },
  ],
});

const SCENARIOS = {
  // 같은 사람(mech-a)이 그려지는 자리마다 계산된 색 — 아바타는 배경, 버블은 왼쪽 테두리
  async colours(browser) {
    const page = await open(browser);
    await page.getByText('기구 강도 전문가', { exact: true }).first().waitFor();     // 회의록이 명부로 이름을 찾았다
    await page.locator('#pin').click();
    await page.locator('.tool-av').waitFor();
    await page.locator('.tool-pill').click();                                        // 입력창 알약 → 고르기 화면
    await page.locator('.pp-search').fill('기구');
    await page.locator('.pp-av').first().waitFor();
    const seen = await page.evaluate(() => {
      const bg = (el) => (el ? getComputedStyle(el).backgroundColor : null);
      const edge = (el) => (el ? getComputedStyle(el).borderLeftColor : null);
      const persona = document.querySelector('.msg.is-persona');
      return {
        chat_name: persona && persona.querySelector('.msg-who-name').textContent,
        chat_key: persona && persona.querySelector('.msg-who-key').textContent,
        chat_av: bg(persona && persona.querySelector('.msg-av')),
        chat_edge: edge(persona && persona.querySelector('.msg-content')),
        intro: Array.from(document.querySelectorAll('.dv-intro-item')).map((li) =>
          [li.querySelector('.dv-intro-key').getAttribute('title'), bg(li.querySelector('.dv-intro-avatar'))]),
        turns: Array.from(document.querySelectorAll('.dv-turn')).map((t) =>
          [t.querySelector('.dv-who').getAttribute('title'), bg(t.querySelector('.dv-av')), edge(t.querySelector('.dv-bub'))]),
        think_av: bg(document.querySelector('.tv-avatar')),
        pill_av: bg(document.querySelector('.tool-av')),
        picker: Array.from(document.querySelectorAll('.pp-row')).map((r) =>
          [r.querySelector('.pp-row-sub').textContent, bg(r.querySelector('.pp-av'))]),
      };
    });
    return { ...seen, errors: page.__errors };
  },
  // 전문가를 지정해 보내고 답을 받는다 → 말풍선. 같은 브라우저로 다시 열면(새로고침) · 다른 기기에서 서버 사본으로 열면 말풍선이 남는가
  async pinned(browser) {
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const page = await open(browser, 'chat', { ctx });
    await page.locator('#pin').click();
    await page.locator('#send').click();
    await page.waitForFunction(() => typeof window.__push === 'function');
    await page.evaluate((f) => { window.__push(f); window.__end(); },
      frame('token', { delta: '힌지 브래킷 R 이 작아 ' }) + frame('result', { type: 'text', content: '힌지 브래킷 R 이 작아 응력이 몰립니다.' }) +
      frame('done', {}));
    await page.waitForFunction(() => document.getElementById('streaming').textContent === 'false');
    const live = await bubble(page);
    const chat = (await page.evaluate(() => window.__calls)).find((c) => c.url.startsWith('/agent/chat'));
    // 새로고침 — 같은 브라우저(localStorage 사본)로 다시 띄운다. 서버 목록에는 그 대화가 그 사이 갱신된 것으로 온다(포털이 답을 스트림
    // 끝에 적는다 — 사본이 더 새로우면 화면은 서버 사본으로 바꾼다)
    const later = Math.floor(Date.now() / 1000) + 60;
    const again = await open(browser, 'chat', { ctx, before: `window.__convs = [${JSON.stringify(SERVER_COPY(later))}].map(
      ({ messages, ...m }) => m); window.__conv = ${JSON.stringify(SERVER_COPY(later))};` });
    // 고르지 않는다 — 브라우저 사본이 마지막에 연 대화(activeId)를 되살린다
    await again.getByText('응력이 몰립니다').first().waitFor();
    await again.waitForFunction(() => window.__calls.some((c) => c.url === '/agent/conversations/srv-1'));
    await again.waitForTimeout(300);
    const reloaded = await bubble(again);
    const reload_gets = (await again.evaluate(() => window.__calls)).filter((c) => c.url === '/agent/conversations/srv-1').length;
    // 다른 기기 — 빈 브라우저에서 서버 목록 · 사본만으로 연다
    const other = await open(browser, 'chat', { before: `window.__convs = [${JSON.stringify(SERVER_COPY(later))}].map(
      ({ messages, ...m }) => m); window.__conv = ${JSON.stringify(SERVER_COPY(later))};` });
    await other.locator('#open').click();
    await other.getByText('응력이 몰립니다').first().waitFor();
    await other.waitForTimeout(300);
    const elsewhere = await bubble(other);
    await ctx.close();
    return { live, chat: chat && chat.body, reloaded, reload_gets, elsewhere,
             errors: [...page.__errors, ...again.__errors, ...other.__errors] };
  },
  // 전문가를 고른 채 '/띵킹 …' · '/심의 …' 를 보낸다 — 답은 고른 전문가가 아니라 띵킹 · 심의다. 라이브는 띵킹 · 심의 화면이고 말풍선이
  // 없다. 새로고침 · 다른 기기에서 서버 사본으로 열어도 말풍선이 없어야 한다. 서버 사본은 시험(파이썬)이 같은 프레임을 포털 중계
  // (agent/routes.py)에 흘려 남긴 그대로다(routed.json) — 손으로 옮겨 적은 사본이면 포털이 적는 꼴과 어긋나도 모른다.
  async routed(browser) {
    const routed = JSON.parse(require('fs').readFileSync(path.join(OUT, 'routed.json'), 'utf8'));
    const look = (page) => page.evaluate(() => ({
      bubble: Boolean(document.querySelector('.msg.is-persona')),
      think: Boolean(document.querySelector('.msg .tv')),
      delib: Boolean(document.querySelector('.msg .dv-root')),
      text: Array.from(document.querySelectorAll('.msg.assistant')).map((el) => el.textContent).join(' | '),
    }));
    const out = {};
    for (const [name, { button, frames, copy, text }] of Object.entries(routed)) {
      const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
      const page = await open(browser, 'chat', { ctx });
      await page.locator('#pin').click();
      await page.locator(button).click();
      await page.waitForFunction(() => typeof window.__push === 'function');
      await page.evaluate((f) => { window.__push(f); window.__end(); }, frames);
      await page.waitForFunction(() => document.getElementById('streaming').textContent === 'false');
      const live = await look(page);
      const sent = (await page.evaluate(() => window.__calls)).find((c) => c.url.startsWith('/agent/chat'));
      const later = Math.floor(Date.now() / 1000) + 60;
      const conv = { id: 'srv-1', title: name, kind: 'chat', source: 'web', created_at: later, updated_at: later,
                     messages: copy.map((m) => ({ ...m, ts: later })) };
      const before = `window.__convs = [${JSON.stringify(conv)}].map(({ messages, ...m }) => m); window.__conv = ${JSON.stringify(conv)};`;
      const again = await open(browser, 'chat', { ctx, before });           // 새로고침 — 서버 사본이 더 새로워 사본으로 바뀐다
      await again.getByText(text).first().waitFor();
      await again.waitForFunction(() => window.__calls.some((c) => c.url === '/agent/conversations/srv-1'));
      await again.waitForTimeout(300);
      const reloaded = await look(again);
      const other = await open(browser, 'chat', { before });                 // 다른 기기 — 서버 사본만으로 연다
      await other.locator('#open').click();
      await other.getByText(text).first().waitFor();
      await other.waitForTimeout(300);
      const elsewhere = await look(other);
      await ctx.close();
      out[name] = { live, sent: sent && sent.body, reloaded, elsewhere, errors: [...page.__errors, ...again.__errors, ...other.__errors] };
    }
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
    out = tmp_path_factory.mktemp("persona")
    (out / "harness.tsx").write_text(_HARNESS.replace("__FE__", str(FE)), encoding="utf-8")
    for name, body in (("build.cjs", _BUILD), ("stub.js", _STUB), ("drive.cjs", _DRIVE)):
        (out / name).write_text(body, encoding="utf-8")
    # 띵킹 · 심의가 답한 턴의 서버 사본 — 화면이 라이브로 받을 프레임을 포털 중계에 그대로 흘려 남긴다(routed 시나리오)
    from tests.test_pinned_agent_persist import DELIB_HEAD, DELIB_NO_TURNS, THINK_SUMMARY, THINK_TURN, relay_turn

    pin = {"pinned_agent": "mech-a", "pinned_agent_name": "기구 강도 전문가 (Mechanical Strength Expert)"}
    routed = {
        "think": {"button": "#send-think", "frames": THINK_TURN, "text": THINK_SUMMARY,
                  "copy": relay_turn(THINK_TURN, message="/띵킹 힌지 강도 봐 줘", **pin)},
        "delib": {"button": "#send-delib", "frames": DELIB_NO_TURNS, "text": DELIB_HEAD,
                  "copy": relay_turn(DELIB_NO_TURNS, message="/심의 힌지 파손 원인", **pin)},
    }
    (out / "routed.json").write_text(json.dumps(routed, ensure_ascii=False), encoding="utf-8")
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


def test_같은_전문가는_챗_말풍선과_회의록_띵킹_알약_고르기_화면에서_같은_색이다(seen):
    """챗 말풍선의 아바타 · 테두리와 회의록 아바타(소개 · 발언) · 발언 버블 테두리 · 띵킹 좌석 · 입력창 알약 · 고르기 화면 행이
    한 색이어야 한 사람으로 읽힌다. 종전엔 말풍선 · 알약 · 고르기 화면이 이름으로, 회의록 · 띵킹이 키로 칠해 두 색이었다."""
    s = seen("colours")
    assert s["chat_name"] == "기구 강도 전문가" and s["chat_key"] == "mech-a", "말풍선은 축약 이름 · 키를 보인다"
    intro = dict(s["intro"])
    turns = {who: (av, edge) for who, av, edge in s["turns"]}
    picker = [bg for sub, bg in s["picker"] if sub.endswith("mech-a")]
    assert set(intro) == {"mech-a", "cae-b"} and set(turns) == {"mech-a", "cae-b"}, (s["intro"], s["turns"])
    assert len(picker) == 1, s["picker"]
    one = s["chat_av"]
    assert one and one.startswith("rgb("), s
    assert {
        "말풍선 테두리": s["chat_edge"], "회의록 소개": intro["mech-a"], "회의록 발언": turns["mech-a"][0],
        "발언 버블 테두리": turns["mech-a"][1], "띵킹 좌석": s["think_av"], "입력창 알약": s["pill_av"], "고르기 화면": picker[0],
    } == dict.fromkeys(("말풍선 테두리", "회의록 소개", "회의록 발언", "발언 버블 테두리", "띵킹 좌석", "입력창 알약", "고르기 화면"), one), \
        f"같은 사람(mech-a)이 화면마다 다른 색이다 — 말풍선 아바타 {one}: {s}"


def test_전문가를_지정해_보낸_답은_말풍선이고_새로고침해도_다른_기기에서_열어도_남는다(seen):
    """지정 전문가의 답이면 말풍선(이름 · 키 · 색)으로 '누가 답했는지' 를 세운다(docs/persona-chat D-3). 누가 답했는지는 보낼 때 찍고
    서버에는 사람 발화의 meta(pinned_agent · pinned_agent_name)로 남는다. 서버 사본으로 화면을 바꾸는 길(사본이 더 새로운 새로고침 ·
    다른 기기 · 숨은 탭에서 돌아옴)에서 말풍선이 사라지면 같은 답이 일반 어시스턴트의 것으로 읽힌다."""
    s = seen("pinned")
    assert s["chat"]["pinned_agent"] == "mech-a" and s["chat"]["pinned_agent_name"].startswith("기구 강도 전문가"), s["chat"]
    live = s["live"]
    assert live and live["name"] == "기구 강도 전문가" and live["key"] == "mech-a", live
    assert live["edge"] == live["av"] and live["av"].startswith("rgb("), "테두리와 아바타가 한 색이다"
    assert "응력이 몰립니다" in live["text"]
    assert s["reload_gets"] >= 1, "전제 — 서버 사본이 더 새로워 화면이 사본으로 바뀌는 길을 탔다"
    for where in ("reloaded", "elsewhere"):
        got = s[where]
        assert got == {**live, "text": got and got["text"]}, f"{where}: 서버 사본으로 연 대화에서 말풍선이 사라졌다 — {got}"
        assert "응력이 몰립니다" in got["text"]


@pytest.mark.parametrize("name, view", [("think", "think"), ("delib", "delib")])
def test_전문가를_고른_채_띵킹_심의로_보낸_답은_다시_열어도_말풍선이_아니다(seen, name, view):
    """'/띵킹' · '/심의' 는 고른 전문가 대신 띵킹 · 심의가 답한다(에이전트 서버가 트리거로 먼저 가른다 — 요청의 thinking 은 거짓이다).
    라이브는 띵킹 · 심의 화면이고 말풍선이 없다. 서버 사본으로 다시 열 때 고른 전문가의 말풍선이 되면 여러 전문가의 요약 · 심의의 앞글이
    그 사람의 답으로 읽힌다(docs/leftovers-1017 B11 반대 검토). 발언 없이 끝난 심의도 같다 — 결정문이 아니라 일반 답처럼 생겼다."""
    s = seen("routed")[name]
    assert not s["errors"], s["errors"]
    assert s["sent"]["pinned_agent"] == "mech-a" and "thinking" not in s["sent"], f"전제 — 전문가를 고르고 Thinking 은 끈 채 보냈다: {s['sent']}"
    assert s["live"]["bubble"] is False and s["live"][view] is True, f"라이브: {s['live']}"
    for where in ("reloaded", "elsewhere"):
        assert s[where]["bubble"] is False, f"{where}: 서버 사본으로 연 {name} 의 답이 고른 전문가의 말풍선이 됐다 — {s[where]}"
