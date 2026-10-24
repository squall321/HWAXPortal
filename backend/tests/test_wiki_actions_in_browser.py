# 답 아래 '위키에 남기기' · '해결됨' 을 헤드리스 브라우저에서 실제 ChatProvider · MessageList 로 본다(docs/mxwp-wiki P6 · P7)
"""왜 — 버튼이 보내는 것(그 답의 본문 · 방식 · 모델 꼬리표)과, 보낸 결과가 대화에 알림으로 남는지(다음 턴이 '위키에 남겼다' 를 안다)는
실제 화면으로만 안다. 서버 쪽 봉투 · 짝 찾기는 tests/test_wiki_send.py 가 본다.

  · MX 백서 권한(plat:mxwhitepaper)이 없으면 버튼이 없다.
  · '위키에 남기기' → POST /agent/conversations/<서버 id>/wiki {text: 그 답, mode: button, model} → 답 아래 '위키에 남겼습니다' ·
    대화에 알림 한 건(서버에도 meta.upload 로 붙는다).
  · '해결됨' → mode candidate → '후보로 보냈습니다' · 알림은 '내 후보' 에서 승인하라는 말.
  · 서버가 거절하면(409 등) 그 까닭을 답 아래에 보인다 — 알림은 남기지 않는다.
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
      <button id="send" type="button" onClick={() => sendMessage('힌지 브래킷 응력은?')}>send</button>
      <span id="streaming">{String(streaming)}</span>
      <MessageList messages={messages} />
    </>
  );
}
(window as unknown as { __mount: (ents: string[]) => void }).__mount = (ents: string[]) => {
  const user = { subject: 'u1@corp.example', email: 'u1@corp.example', display_name: 'U', groups: [], entitlements: ents };
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

# 가짜 백엔드 — 대화 만들기 · 메시지 붙이기(기록) · 위키 보내기(기록 · 거절 흉내) · 챗 스트림
_STUB = r"""
(() => {
  const enc = new TextEncoder();
  const json = (body, status = 200) =>
    Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }));
  window.__wiki = []; window.__msgs = []; window.__wikiReject = false;
  window.fetch = (url, init = {}) => {
    const u = String(url);
    const method = (init.method || 'GET').toUpperCase();
    if (u === '/agent/conversations' && method === 'GET') return json({ conversations: [] });
    if (u === '/agent/conversations' && method === 'POST') return json({ id: 'srv-1' });
    if (/^\/agent\/conversations\/[^/]+\/messages$/.test(u)) { window.__msgs.push(JSON.parse(init.body || '{}')); return json({ ok: true }); }
    if (/^\/agent\/conversations\/[^/]+\/wiki$/.test(u)) {
      const b = JSON.parse(init.body || '{}');
      window.__wiki.push({ url: u, body: b });
      if (window.__wikiReject) return json({ detail: '소속이 없어 바로 남길 수 없습니다 — 해결됨 으로 후보를 만드세요' }, 409);
      return json({ ok: true, mode: b.mode, audience: ['aff:CAEG'], id: 'u1', short: 'src_u1', dedup: false,
                    doc_slug: 'src-u1', ingest_state: 'queued' });
    }
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
const ANSWER = '힌지 브래킷 최대 응력은 412 MPa 입니다.';
const META = { models: { 'qwen3.8-flash-next': 1 }, chat_model: 'qwen3.8-flash-next', thinking: true, effort: 'xhigh', fallback_to: null };

async function answered(browser, ents) {
  const page = await browser.newPage();
  page.setDefaultTimeout(10000);
  page.__errors = [];
  page.on('pageerror', (e) => page.__errors.push(String(e)));
  await page.route('http://harness.invalid/**', (r) =>
    r.fulfill({ contentType: 'text/html', body: '<!doctype html><html><body><div id="root"></div></body></html>' }));
  await page.goto('http://harness.invalid/');
  await page.addScriptTag({ path: path.join(OUT, 'stub.js') });
  await page.addScriptTag({ path: path.join(OUT, 'bundle.js') });
  await page.evaluate((e) => window.__mount(e), ents);
  await page.click('#send');
  await page.waitForFunction(() => typeof window.__push === 'function');
  await page.evaluate((f) => { window.__push(f); window.__end(); }, frame('token', { delta: ANSWER }) + frame('meta', META)
    + frame('result', { type: 'text', content: ANSWER }) + frame('done', {}));
  await page.waitForFunction(() => document.getElementById('streaming').textContent === 'false');
  return page;
}
const buttons = (page) => page.evaluate(() => [...document.querySelectorAll('.msg-wiki')].map((b) => b.textContent));
const state = (page) => page.evaluate(() => ({
  wiki: window.__wiki, msgs: window.__msgs,
  note: (document.querySelector('.msg-wiki-note') || {}).textContent || null,
  noteErr: Boolean(document.querySelector('.msg-wiki-note.is-err')),
  assistants: [...document.querySelectorAll('.msg.assistant .chat-text')].map((n) => n.textContent),
}));

async function press(browser, label, reject) {
  const page = await answered(browser, ['chat', 'plat:mxwhitepaper']);
  if (reject) await page.evaluate(() => { window.__wikiReject = true; });
  const before = await buttons(page);
  await page.click(`.msg-wiki:has-text("${label}")`);
  await page.waitForSelector('.msg-wiki-note');
  await page.waitForTimeout(400);    // 알림이 서버로 붙는 사슬(appendServerMessage)이 끝나게
  const s = await state(page);
  const errors = page.__errors;
  await page.close();
  return { before, ...s, errors };
}

(async () => {
  let browser;
  try { browser = await chromium.launch(); } catch (e) { process.stdout.write(JSON.stringify({ skip: String(e).slice(0, 300) })); return; }
  const out = {};
  try {
    for (const [name, fn] of Object.entries({
      button: () => press(browser, '위키에 남기기', false),
      candidate: () => press(browser, '해결됨', false),
      rejected: () => press(browser, '위키에 남기기', true),
      noperm: async () => { const p = await answered(browser, ['chat']); const b = await buttons(p); const errors = p.__errors; await p.close(); return { before: b, errors }; },
    })) {
      try { out[name] = await fn(); } catch (e) { out[name] = { failed: String((e && e.stack) || e).slice(0, 1500) }; }
    }
  } finally { await browser.close(); }
  process.stdout.write(JSON.stringify(out));
})().catch((e) => { process.stderr.write(String((e && e.stack) || e)); process.exit(1); });
"""

ANSWER = "힌지 브래킷 최대 응력은 412 MPa 입니다."


@pytest.fixture(scope="module")
def seen(tmp_path_factory):
    out = tmp_path_factory.mktemp("wikiactions")
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


def test_권한이_없으면_버튼이_없다(seen):
    assert seen("noperm")["before"] == []


def test_위키에_남기기는_그_답을_보내고_대화에_알림을_남긴다(seen):
    s = seen("button")
    assert s["before"] == ["위키에 남기기", "해결됨"]
    (req,) = s["wiki"]
    assert req["url"] == "/agent/conversations/srv-1/wiki"
    assert req["body"] == {"text": ANSWER, "mode": "button", "model": "qwen3.8-flash-next"}
    assert s["note"] == "위키에 남겼습니다" and not s["noteErr"]
    assert any("MX 백서 위키에 남겼습니다 — 원천 src_u1(범위 aff:CAEG)" in t for t in s["assistants"]), s["assistants"]
    up = [m for m in s["msgs"] if (m.get("meta") or {}).get("upload")]
    assert len(up) == 1 and up[0]["meta"]["activity"][0]["tool"] == "wiki_submit_source" \
        and up[0]["meta"]["activity"][0]["origin"] == "upload", "다음 턴이 알게 서버 대화에도 업로드 근거로 붙는다"


def test_해결됨은_후보로_보내고_내_후보에서_승인하라고_말한다(seen):
    s = seen("candidate")
    assert s["wiki"][0]["body"]["mode"] == "candidate"
    assert s["note"] == "후보로 보냈습니다"
    assert any("후보로 보냈습니다" in t and "'내 후보'" in t for t in s["assistants"]), s["assistants"]


def test_거절되면_까닭을_답_아래에_보이고_알림은_남기지_않는다(seen):
    s = seen("rejected")
    assert s["noteErr"] and "소속이 없어" in s["note"]
    assert not [m for m in s["msgs"] if (m.get("meta") or {}).get("upload")]
