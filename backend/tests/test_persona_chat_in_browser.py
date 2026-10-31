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
(window as unknown as { __mount: (what?: string) => void }).__mount = () => {
  const user = { subject: 'u1@corp.example', email: 'u1@corp.example', display_name: 'U', groups: [] };
  createRoot(document.getElementById('root')!).render(
    <AuthContext.Provider
      value={{ user, status: 'authenticated', login: () => undefined, logout: async () => undefined, refresh: async () => undefined }}
    >
      <MemoryRouter>
        <ChatProvider storagePrefix="hwax.chat" serverKind="chat">
          <Colours />
        </ChatProvider>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
};
"""

# 가짜 백엔드 — 전문가 명부(회의록이 키를 이름으로 바꾸고 고르기 화면이 찾는다)와 빈 서버 대화 목록만 준다.
_STUB = r"""
(() => {
  window.__calls = [];
  const json = (body, status = 200) =>
    Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }));
  window.fetch = (url, init = {}) => {
    const u = String(url);
    const method = (init.method || 'GET').toUpperCase();
    window.__calls.push({ url: u, method });
    if (u.startsWith('/agent/deliberate/experts')) return json({ recommended: [], pool: [
      { key: 'mech-a', name: '기구 강도 전문가 (Mechanical Strength Expert)', tags: [] },
      { key: 'cae-b', name: '구조 해석 전문가 (Structural Analysis Expert)', tags: [] }] });
    if (u === '/agent/conversations' && method === 'GET') return json({ conversations: [] });
    return json({ detail: 'stub: no route ' + u }, 404);
  };
})();
"""

_DRIVE = r"""
const { createRequire } = require('module');
const path = require('path');
const [FE, OUT] = process.argv.slice(2);
const { chromium } = createRequire(path.join(FE, 'package.json'))('@playwright/test');

async function open(browser, what = '') {
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  page.setDefaultTimeout(10000);
  page.__errors = [];
  page.on('pageerror', (e) => page.__errors.push(String(e)));
  await page.route('http://harness.invalid/**', (r) =>
    r.fulfill({ contentType: 'text/html', body: '<!doctype html><html><body><div id="root"></div></body></html>' }));
  await page.goto('http://harness.invalid/');
  await page.addScriptTag({ path: path.join(OUT, 'stub.js') });
  await page.addScriptTag({ path: path.join(OUT, 'bundle.js') });
  await page.evaluate((w) => window.__mount(w), what);
  return page;
}

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
