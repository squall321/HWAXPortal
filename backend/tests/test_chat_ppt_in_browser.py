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
  const { messages, activeConversation, attachedDocs } = useChat();
  return (
    <>
      <span id="roles">{messages.map((m) => m.role).join(',')}</span>
      <span id="sid">{activeConversation?.serverId ?? ''}</span>
      <span id="docs">{attachedDocs.map((d) => `${d.name}:${d.chars}`).join(',')}</span>
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
          {what === 'composer' ? <><Composer /><Peek /></> : <Probe />}
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
      window.__staged = (window.__staged || 0) + 1;
      return json({ staging_id: 'st' + window.__staged, filename: f.name, size: f.size, ext: 'pptx', content_type: '',
                    destinations: [{ id: 'aidatahub', label: 'AI 데이터 허브 — 지식카드로 변환' },
                                   { id: 'reportarchive', label: 'Report Archive — 보고서로' }] });
    }
    if (u === '/agent/upload/dispatch') return json(window.__dispatch);
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
async function pick(page, name, head) {
  await page.locator('input[type=file]').setInputFiles({ name, mimeType: 'application/octet-stream',
    buffer: Buffer.concat([Buffer.from(head), Buffer.alloc(64)]) });
}

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


def test_알림만_있는_대화의_첫_발화에도_심의_트리거가_붙는다(seen):
    assert seen("delib_first_turn")["message"] == "/심의 방금 변환한 것 검토해 줘"
