# 챗 자기검증 표시를 헤드리스 브라우저에서 실제 ChatProvider · MessageList 로 본다 — 초안은 '생각' 칸, 본문은 고친 답, 고친 곳 · 검증 못 함은 답 아래(docs/chat-self-check)
"""왜 — 에이전트 서버는 초안을 reasoning 으로, 고친 답을 token 으로, 결과를 meta.self_check 로 낸다(HWAXAgentServer d8011e0). 화면이 그 셋을
제자리에 그리는지는 실제 화면으로만 안다.

  · 도는 동안 — 본문은 비어 있고 '생각 중' 칸에 초안이 쌓인다. 상태줄은 '답을 검증하는 중'.
  · 고쳤으면 — 본문은 고친 답, 답 아래에 '검증에서 N곳을 고쳤습니다'(펼치면 고친 점), 모델 표시 옆 배지는 없다.
  · 고칠 것 없음 · 생략 — 답 아래는 비고, 모델 표시 옆에 조용히('검증 ✓' · '검증 생략').
  · 검증 못 함(suspect 등) — 답 아래에 늘 '검증하지 못해 초안을 그대로 보였습니다' + 까닭 + 검토자가 짚은 곳(반영 안 함).
  · self_check 가 없는 옛 서버의 답 — 아무것도 더하지 않는다.
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

function Probe() {
  const { messages, sendMessage, streaming } = useChat();
  return (
    <>
      <button id="send" type="button" onClick={() => sendMessage('M3 나사 체결 토크는?')}>send</button>
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
        <ChatProvider storagePrefix="hwax.chat" serverKind="chat"><Probe /></ChatProvider>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
};
"""

# 가짜 백엔드 — 서버 대화 만들기 · 메시지 붙이기 · 챗 스트림(__push · __end)
_STUB = r"""
(() => {
  const enc = new TextEncoder();
  const json = (body, status = 200) =>
    Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }));
  window.fetch = (url, init = {}) => {
    const u = String(url);
    const method = (init.method || 'GET').toUpperCase();
    if (u === '/agent/conversations' && method === 'GET') return json({ conversations: [] });
    if (u === '/agent/conversations' && method === 'POST') return json({ id: 'srv-1' });
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

const DRAFT = 'M3 나사의 권장 체결 토크는 12.5 N·m 입니다.';
const FIXED = 'M3 나사의 권장 체결 토크는 12.5 N·m (근거 없음 — 추정) 입니다.';
const META = { models: { 'qwen3.8-flash-next': 2 }, chat_model: 'qwen3.8-flash-next', thinking: true, effort: 'xhigh', fallback_to: null };
const CHECKS = {
  fixed: { status: 'fixed', fixes: ['12.5 는 근거가 없어 추정으로 표시'], ms: 2300 },
  ok: { status: 'ok', ms: 1200 },
  skipped: { status: 'skipped', reason: '근거(조회 · 붙인 문서 · 그림)도 수치도 없는 짧은 답', ms: 0 },
  suspect: { status: 'suspect', reason: '고친 답이 초안의 그림 1개를 잃었다 — 초안을 그대로 냈다', fixes: ['그림 설명을 줄임'], ms: 4100 },
  none: null,
};

async function open(browser) {
  const page = await browser.newPage();
  page.setDefaultTimeout(10000);
  page.__errors = [];
  page.on('pageerror', (e) => page.__errors.push(String(e)));
  await page.route('http://harness.invalid/**', (r) =>
    r.fulfill({ contentType: 'text/html', body: '<!doctype html><html><body><div id="root"></div></body></html>' }));
  await page.goto('http://harness.invalid/');
  await page.addScriptTag({ path: path.join(OUT, 'stub.js') });
  await page.addScriptTag({ path: path.join(OUT, 'bundle.js') });
  await page.evaluate(() => window.__mount());
  return page;
}
const look = (page) => page.evaluate(() => {
  const bot = [...document.querySelectorAll('.msg.assistant')].pop();
  const q = (s) => (bot && bot.querySelector(s)) || null;
  const t = (s) => (q(s) ? q(s).textContent : null);
  return {
    body: t('.msg-content > .chat-text') ?? '',
    reasoning_summary: t('.msg-reasoning > summary'),
    reasoning: t('.msg-reasoning-body'),
    status: t('.msg-thinking'),
    check: t('.msg-check > summary'),
    check_warn: Boolean(q('.msg-check.warn')),
    check_open_text: q('.msg-check') ? q('.msg-check').textContent : null,
    actions: t('.msg-actions'),
  };
});

async function turn(browser, check) {
  const page = await open(browser);
  await page.click('#send');
  await page.waitForFunction(() => typeof window.__push === 'function');
  await page.evaluate((f) => window.__push(f), frame('reasoning', { delta: '생각: 나사 규격을 떠올린다' })
    + frame('reasoning', { delta: '\n\n— 초안(검증 전) —\n' }) + frame('reasoning', { delta: DRAFT })
    + frame('status', { step: '답을 검증하는 중 — 질문 · 근거 · 수치를 대조합니다', tool: null })
    + frame('reasoning', { delta: '\n\n— 검증 —\n[판정] 고침\n[고친 점]\n- 12.5 는 근거가 없어 추정으로 표시\n[바꿀 곳]\n[원문]\n12.5 N·m 입니다.\n'
      + '[새 글]\n12.5 N·m (근거 없음 — 추정) 입니다.' }));
  await page.waitForFunction(() => (document.querySelector('.msg-reasoning-body') || {}).textContent?.includes('— 검증 —'));
  const mid = await look(page);
  const final = check && check.status === 'suspect' ? DRAFT : check && check.status === 'fixed' ? FIXED : DRAFT;
  await page.evaluate((f) => { window.__push(f); window.__end(); }, frame('token', { delta: final })
    + frame('meta', check ? { ...META, self_check: check } : META) + frame('result', { type: 'text', content: final }) + frame('done', {}));
  await page.waitForFunction(() => document.getElementById('streaming').textContent === 'false');
  const end = await look(page);
  let opened = null;
  if (end.check) {
    await page.click('.msg-check > summary');
    opened = await page.evaluate(() => [...document.querySelectorAll('.msg-check li')].map((li) => li.textContent));
  }
  const errors = page.__errors;
  await page.close();
  return { mid, end, opened, errors };
}

(async () => {
  let browser;
  try { browser = await chromium.launch(); } catch (e) { process.stdout.write(JSON.stringify({ skip: String(e).slice(0, 300) })); return; }
  const out = {};
  try {
    for (const [name, check] of Object.entries(CHECKS)) {
      try { out[name] = await turn(browser, check); } catch (e) { out[name] = { failed: String((e && e.stack) || e).slice(0, 1500) }; }
    }
  } finally { await browser.close(); }
  process.stdout.write(JSON.stringify(out));
})().catch((e) => { process.stderr.write(String((e && e.stack) || e)); process.exit(1); });
"""


@pytest.fixture(scope="module")
def seen(tmp_path_factory):
    out = tmp_path_factory.mktemp("selfcheck")
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


DRAFT = "M3 나사의 권장 체결 토크는 12.5 N·m 입니다."
FIXED = "M3 나사의 권장 체결 토크는 12.5 N·m (근거 없음 — 추정) 입니다."


def test_도는_동안은_본문이_비고_초안은_생각_중_칸에_쌓인다(seen):
    mid = seen("fixed")["mid"]
    assert not (mid["body"] or "").strip(), f"검증 전에는 본문에 아무것도 없다 — {mid['body']!r}"
    assert mid["reasoning_summary"].startswith("생각 중"), mid
    assert "— 초안(검증 전) —\n" + DRAFT in mid["reasoning"] and "[판정] 고침" in mid["reasoning"]
    assert "답을 검증하는 중" in (mid["status"] or ""), mid


def test_고친_답이_본문이고_고친_곳은_답_아래에서_펼쳐_본다(seen):
    s = seen("fixed")
    end = s["end"]
    assert FIXED in end["body"] and end["body"].count("12.5") == 1, end["body"]
    assert end["reasoning_summary"].startswith("생각 ·"), "답이 나오면 '생각' 칸은 접힌 기록이 된다"
    assert end["check"] == "검증에서 1곳을 고쳤습니다 · 2.3초" and not end["check_warn"]
    assert s["opened"] == ["12.5 는 근거가 없어 추정으로 표시"]
    assert "고치기 전 초안은 위 ‘생각’ 칸에 있습니다" in end["check_open_text"]
    assert "검증 ✓" not in end["actions"] and "qwen3.8-flash-next" in end["actions"]


def test_고칠_것_없음과_생략은_모델_표시_옆에_조용히(seen):
    ok, skip = seen("ok")["end"], seen("skipped")["end"]
    assert ok["check"] is None and "검증 ✓ · 1.2초" in ok["actions"]
    assert skip["check"] is None and "검증 생략" in skip["actions"]


def test_검증_못_함은_답_아래에_늘_까닭과_짚은_곳(seen):
    s = seen("suspect")
    end = s["end"]
    assert DRAFT in end["body"] and end["check_warn"]
    assert end["check"] == "검증하지 못해 초안을 그대로 보였습니다 · 4.1초"
    assert "고친 답이 초안의 그림 1개를 잃었다" in end["check_open_text"] and "검토자가 짚은 곳(반영하지 않음)" in end["check_open_text"]
    assert s["opened"] == ["그림 설명을 줄임"]
    assert "검증" not in end["actions"]


def test_self_check_가_없는_옛_서버의_답은_그대로(seen):
    end = seen("none")["end"]
    assert end["check"] is None and "검증" not in end["actions"] and DRAFT in end["body"]
