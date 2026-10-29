# 숨은 탭이 다시 보일 때 받는 중인 대화를 서버 사본과 맞추는지 헤드리스 브라우저에서 실제 ChatProvider 로 본다(docs/request-1029 P-1 ②)
"""포털 중계는 브라우저가 읽지 않아도 상류를 끝까지 읽어 서버 사본에 답을 저장한다(P-1 ①). 화면이 다시 보일 때 받는 중인 대화가 20초 넘게
조용했으면 서버 사본을 묻고, 마지막이 이 턴의 사람 발화 뒤의 답이면 받는 중 표시를 끝내고 서버 사본으로 바꾼다. 답이 아직 없거나 조용한 시간이
짧으면 아무것도 하지 않는다. 숨김 · 보임은 document.visibilityState 를 바꾸고 visibilitychange 를 쏴서 흉내 낸다.
"""
import json
import subprocess

import pytest

from tests.test_chat_self_check_in_browser import _HARNESS
from tests.test_delib_stream_in_browser import _BUILD, FE, pytestmark  # noqa: F401 — 같은 도구가 없으면 같이 건너뛴다

# 가짜 백엔드 — 서버 대화 만들기 · 붙이기 · 상세(window.__server 가 답한다, 부른 수를 센다) · 챗 스트림(__push · __end)
_STUB = r"""
(() => {
  const enc = new TextEncoder();
  window.__server = null;
  window.__gets = 0;
  const json = (body, status = 200) =>
    Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }));
  window.fetch = (url, init = {}) => {
    const u = String(url);
    const method = (init.method || 'GET').toUpperCase();
    if (u === '/agent/conversations' && method === 'GET') return json({ conversations: [] });
    if (u === '/agent/conversations' && method === 'POST') return json({ id: 'srv-1' });
    if (/^\/agent\/conversations\/[^/]+\/messages$/.test(u)) return json({ ok: true });
    if (u === '/agent/conversations/srv-1' && method === 'GET') {
      window.__gets += 1;
      return window.__server ? json(window.__server) : json({ detail: 'not found' }, 404);
    }
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
const ASKED = 'M3 나사 체결 토크는?';
// 서버 시각은 화면 시계(가짜 — 아래 clock.install)와 같은 때다. 진짜 서버도 그렇다 — 1970 년 값을 주면 '서버가 더 새롭다' 판정이 엇나간다.
const T0 = Date.parse('2026-10-29T00:00:00Z') / 1000;
const conv = (messages) => ({ id: 'srv-1', title: 't', kind: 'chat', source: 'web', created_at: T0, updated_at: T0 + 20,
  messages: messages.map(([role, content]) => ({ role, persona: null, round: null, content, meta: null, ts: T0 + 20 })) });

async function open(browser) {
  const page = await browser.newPage();
  page.setDefaultTimeout(10000);
  page.__errors = [];
  page.on('pageerror', (e) => page.__errors.push(String(e)));
  await page.route('http://harness.invalid/**', (r) =>
    r.fulfill({ contentType: 'text/html', body: '<!doctype html><html><body><div id="root"></div></body></html>' }));
  await page.clock.install({ time: new Date('2026-10-29T00:00:00Z') });
  await page.goto('http://harness.invalid/');
  await page.addScriptTag({ path: path.join(OUT, 'stub.js') });
  await page.addScriptTag({ path: path.join(OUT, 'bundle.js') });
  await page.evaluate(() => window.__mount());
  return page;
}
// 숨겼다가 다시 보인다 — 그 사이 quietMs 동안 아무 프레임도 오지 않았다
async function hideAndShow(page, quietMs) {
  await page.evaluate(() => { Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'hidden' });
                              document.dispatchEvent(new Event('visibilitychange')); });
  await page.clock.fastForward(quietMs);
  await page.evaluate(() => { Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'visible' });
                              document.dispatchEvent(new Event('visibilitychange')); });
  await page.waitForTimeout(300);
}
const state = (page) => page.evaluate(() => ({ streaming: document.getElementById('streaming').textContent,
  gets: window.__gets, text: [...document.querySelectorAll('.msg.assistant')].map((el) => el.textContent).join(' | ') }));

async function scenario(browser, server, quietMs) {
  const page = await open(browser);
  await page.click('#send');
  await page.waitForFunction(() => typeof window.__push === 'function');
  await page.evaluate((f) => window.__push(f), frame('status', { step: '조회 중', tool: null }));
  await page.waitForTimeout(100);
  await page.evaluate((s) => { window.__server = s; }, server);
  await hideAndShow(page, quietMs);
  const out = { ...(await state(page)), errors: page.__errors };
  await page.close();
  return out;
}

const SCENARIOS = {
  done_on_server: (b) => scenario(b, conv([['user', ASKED], ['assistant', '서버 사본에 저장된 끝난 답']]), 25000),
  not_yet: (b) => scenario(b, conv([['user', ASKED]]), 25000),
  other_turn: (b) => scenario(b, conv([['user', '앞 질문'], ['assistant', '앞 답']]), 25000),
  short_quiet: (b) => scenario(b, conv([['user', ASKED], ['assistant', '서버 사본에 저장된 끝난 답']]), 5000),
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
    out = tmp_path_factory.mktemp("resync")
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


def test_서버_사본에_끝난_답이_있으면_받는_중을_끝내고_그_답을_보인다(seen):
    s = seen("done_on_server")
    assert s["streaming"] == "false" and s["gets"] == 1, s
    assert "서버 사본에 저장된 끝난 답" in s["text"]


def test_서버에_답이_아직_없으면_그대로_받는다(seen):
    s = seen("not_yet")
    assert s["streaming"] == "true" and s["gets"] == 1, s


def test_서버의_마지막_답이_다른_턴이면_바꾸지_않는다(seen):
    """사람 발화 저장이 실패했으면 서버의 마지막 답은 앞 턴의 것이다 — 그것으로 받는 중인 답을 덮으면 안 된다."""
    s = seen("other_turn")
    assert s["streaming"] == "true" and "앞 답" not in s["text"], s


def test_조용한_시간이_짧으면_묻지도_않는다(seen):
    s = seen("short_quiet")
    assert s["streaming"] == "true" and s["gets"] == 0, s
