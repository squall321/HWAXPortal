# 절차 실행의 단계 기록을 실어 연 심의가 실패한 뒤 '다시 시도' 가 그 실행 id 를 다시 싣는지 — 헤드리스 브라우저에서 실제 ChatProvider 로 본다
"""단계 근거는 서버가 `delib_opts.procedure_run` 칸으로만 싣는다(docs/procedures W-114). '다시 시도' 가 글만 다시 보내면 그 칸이 빠져 단계
근거 없는 심의가 아무 말 없이 돈다(반대 검토 M3). 그 칸을 실어 보낸 발화의 다시 시도는 그때의 손잡이(실행 id · 유형)를 다시 싣는다.
그 칸이 없는 발화의 다시 시도는 종전 그대로다(글만).
"""
import json
import subprocess

import pytest
from tests.test_delib_stream_in_browser import (  # noqa: F401 — 같은 도구가 없으면 같이 건너뛴다
    _BUILD,
    FE,
    pytestmark,
)

_RUN = "0123456789abcdef0123456789abcdef"

_HARNESS = r"""
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { AuthContext } from '__FE__/src/auth/AuthContext';
import { ChatProvider, useChat } from '__FE__/src/state/ChatContext';
import { MessageList } from '__FE__/src/components/chat/MessageList';

function Probe() {
  const { messages, sendMessage } = useChat();
  return (
    <>
      <button id="bridge" type="button"
              onClick={() => sendMessage('SED 가 기준을 넘는 까닭', { procedure_run: '__RUN__', chair_template: 'diagnosis' })}>bridge</button>
      <button id="plain" type="button" onClick={() => sendMessage('힌지 파손 원인', { chair_template: 'diagnosis' })}>plain</button>
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
        <ChatProvider storagePrefix="hwax.delib" sendPrefix="/심의 ">
          <Probe />
        </ChatProvider>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
};
"""

# 가짜 백엔드 — /agent/chat 의 첫 요청은 연결 실패, 그 뒤는 곧바로 끝나는 스트림이다. 보낸 몸을 적는다.
_STUB = r"""
(() => {
  window.__chats = [];
  const enc = new TextEncoder();
  window.fetch = (url, init = {}) => {
    const u = String(url);
    if (u.startsWith('/agent/chat')) {
      window.__chats.push(init.body ? JSON.parse(init.body) : null);
      if (window.__chats.length === 1) return Promise.reject(new TypeError('Failed to fetch'));
      const body = new ReadableStream({ start(c) {
        c.enqueue(enc.encode('event: result\ndata: {"type":"text","content":"끝"}\n\nevent: done\ndata: {}\n\n'));
        c.close();
      } });
      return Promise.resolve(new Response(body, { status: 200, headers: { 'Content-Type': 'text/event-stream' } }));
    }
    return Promise.resolve(new Response(JSON.stringify({ detail: 'stub: no route ' + u }), { status: 404,
      headers: { 'Content-Type': 'application/json' } }));
  };
})();
"""

_DRIVE = r"""
const { createRequire } = require('module');
const path = require('path');
const [FE, OUT] = process.argv.slice(2);
const { chromium } = createRequire(path.join(FE, 'package.json'))('@playwright/test');

(async () => {
  let browser;
  try { browser = await chromium.launch(); } catch (e) { process.stdout.write(JSON.stringify({ skip: String(e).slice(0, 300) })); return; }
  const out = { errors: [] };
  const run = async (button) => {
    const page = await browser.newPage();
    page.setDefaultTimeout(10000);
    page.on('pageerror', (e) => out.errors.push(String(e)));
    await page.route('http://harness.invalid/**', (rt) =>
      rt.fulfill({ contentType: 'text/html', body: '<!doctype html><html><body><div id="root"></div></body></html>' }));
    await page.goto('http://harness.invalid/');
    await page.addScriptTag({ path: path.join(OUT, 'stub.js') });
    await page.addScriptTag({ path: path.join(OUT, 'bundle.js') });
    await page.evaluate(() => window.__mount());
    await page.locator(button).click();
    const retry = page.getByRole('button', { name: '다시 시도', exact: true });
    await retry.waitFor();                                   // 첫 요청이 실패했다
    await retry.click();
    await page.waitForFunction(() => window.__chats.length >= 2);
    await page.getByText('끝').first().waitFor();
    return page.evaluate(() => window.__chats.map((b) => ({ message: b.message, delib_opts: b.delib_opts || null })));
  };
  try {
    out.bridge = await run('#bridge');
    out.plain = await run('#plain');
  } catch (e) { out.failed = String((e && e.stack) || e).slice(0, 1500); }
  finally { await browser.close(); }
  process.stdout.write(JSON.stringify(out));
})().catch((e) => { process.stderr.write(String((e && e.stack) || e)); process.exit(1); });
"""


@pytest.fixture(scope="module")
def seen(tmp_path_factory):
    out = tmp_path_factory.mktemp("procretry")
    (out / "harness.tsx").write_text(_HARNESS.replace("__FE__", str(FE)).replace("__RUN__", _RUN), encoding="utf-8")
    for name, body in (("build.cjs", _BUILD), ("stub.js", _STUB), ("drive.cjs", _DRIVE)):
        (out / name).write_text(body, encoding="utf-8")
    r = subprocess.run(["node", "build.cjs", str(FE), str(out)], cwd=str(out), capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, "화면을 묶지 못했다:\n" + r.stdout + r.stderr
    r = subprocess.run(["node", "drive.cjs", str(FE), str(out)], cwd=str(out), capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
    got = json.loads(r.stdout)
    if "skip" in got:
        pytest.skip("헤드리스 브라우저를 띄우지 못했다(playwright 브라우저 미설치) — " + got["skip"])
    assert "failed" not in got, f"끝까지 돌지 못했다:\n{got.get('failed')}"
    assert not got["errors"], f"화면이 예외를 던졌다: {got['errors']}"
    return got


def test_실행_기록을_실은_심의의_다시_시도는_실행_id_를_다시_싣는다(seen):
    first, again = seen["bridge"]
    assert first["delib_opts"]["procedure_run"] == _RUN and first["message"] == "/심의 SED 가 기준을 넘는 까닭"
    assert again["message"] == first["message"], "다시 보내는 글은 그 발화 그대로다"
    assert again["delib_opts"].get("procedure_run") == _RUN, "다시 시도가 실행 id 를 빼면 단계 근거 없는 심의가 조용히 돈다"
    assert again["delib_opts"].get("chair_template") == "diagnosis", "사람이 고른 유형도 그때 그대로다"


def test_실행_기록을_싣지_않은_발화의_다시_시도는_종전_그대로다(seen):
    first, again = seen["plain"]
    assert first["delib_opts"]["chair_template"] == "diagnosis" and "procedure_run" not in first["delib_opts"]
    assert again["message"] == first["message"]
    assert "procedure_run" not in (again["delib_opts"] or {}) and "chair_template" not in (again["delib_opts"] or {}), \
        "그 칸이 없는 발화의 다시 시도는 글만 다시 보낸다(종전 동작)"
