# 심의 페이지의 첫 발화 · 다시 시도가 이미 심의 트리거(/시뮬심의 · /시험계획 …)로 시작하는 글에 '/심의 ' 를 또 붙이지 않는다 — 트리거 목록은 포털과 같다(헤드리스 브라우저 · 가짜 fetch)
"""10-31 — 심의 페이지(ChatProvider sendPrefix='/심의 ')의 방법 메뉴에서 해석 계획(sim-plan) · 시험 계획(test-plan) · 구축 계획(build-plan)을 고르면
첫 발화가 '/심의 /시뮬심의 …' 로 나갔다. 에이전트 서버는 글 머리로 트리거를 가르므로(startswith) 일반 /심의 로 열려 다단 심의 · 시험 계획이 돌지
않았다. 다시 시도도 같은 글을 만들었다. 고정하는 것.
  · 프론트 목록(delibTaxonomy.DELIB_TRIGGERS)은 포털 routes._DELIB_TRIGGERS 와 같다(포털 목록은 test_chat_idle_split 이 에이전트 서버와 대조한다).
    방법 메뉴(JOB_ROUTING)의 트리거도 그 안이다.
  · 방법 메뉴의 첫 발화(DeliberatePage.confirmExperts 와 같은 부름)는 트리거 그대로 나간다. 메뉴를 거치지 않은 첫 발화는 종전대로 '/심의 ' 가 붙는다.
  · 다시 시도도 같다 — 트리거로 시작하는 발화는 그대로, 아닌 발화는 종전대로 '/심의 ' 를 붙여 심의를 다시 연다.
test_delib_stop_in_browser 와 같은 길이다 — 실제 ChatProvider · MessageList 를 esbuild 로 묶어 빈 문서에 올리고 fetch 를 가짜로 바꾼다.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from tests.test_delib_stop_in_browser import _BUILD, _STUB

from app.agent.routes import _DELIB_TRIGGERS

ROOT = Path(__file__).resolve().parents[2]
FE = ROOT / "frontend"
_TAXONOMY = FE / "src" / "components" / "chat" / "delibTaxonomy.ts"
_PAGE = FE / "src" / "pages" / "DeliberatePage.tsx"


def test_프론트_심의_트리거는_포털과_같고_방법_메뉴의_트리거도_그_안이다():
    src = _TAXONOMY.read_text(encoding="utf-8")
    m = re.search(r"^export const DELIB_TRIGGERS = \[(.*?)\] as const;", src, re.M | re.S)
    assert m, "delibTaxonomy.ts 에서 DELIB_TRIGGERS 를 못 찾았다 — 이름이 바뀌었으면 이 시험도 고쳐라"
    assert re.findall(r"'([^']*)'", m.group(1)) == list(_DELIB_TRIGGERS), "프론트 · 포털의 심의 트리거가 어긋났다"
    routed = re.findall(r"trigger: '([^']*)'", src)
    assert routed and {t.strip() for t in routed} <= set(_DELIB_TRIGGERS), routed


def test_심의_페이지는_방법_메뉴의_트리거를_화두_앞에_붙여_보낸다():
    """아래 브라우저 시험이 흉내 내는 부름 — 화면이 바뀌면 시험도 같이 바꾼다."""
    page = _PAGE.read_text(encoding="utf-8")
    assert "const route = JOB_ROUTING[job];" in page and "sendMessage(route.trigger + topic, {" in page


_HARNESS = r"""
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { AuthContext } from '__FE__/src/auth/AuthContext';
import { ChatProvider, useChat } from '__FE__/src/state/ChatContext';
import { MessageList } from '__FE__/src/components/chat/MessageList';
import { JOB_ROUTING } from '__FE__/src/components/chat/delibTaxonomy';

function Probe() {
  const { messages, sendMessage, streaming } = useChat();
  (window as unknown as { __send: typeof sendMessage }).__send = sendMessage;
  return (
    <>
      <span id="streaming">{String(streaming)}</span>
      <MessageList messages={messages} />
    </>
  );
}
(window as unknown as { __routing: typeof JOB_ROUTING }).__routing = JOB_ROUTING;
(window as unknown as { __mount: () => void }).__mount = () => {
  const user = { subject: 'u1@corp.example', email: 'u1@corp.example', display_name: 'U', groups: [] };
  createRoot(document.getElementById('root')!).render(
    <AuthContext.Provider
      value={{ user, status: 'authenticated', login: () => undefined, logout: async () => undefined, refresh: async () => undefined }}
    >
      <MemoryRouter>
        {/* 심의 페이지의 Provider 그대로(App.tsx) */}
        <ChatProvider storagePrefix="hwax.delib" sendPrefix="/심의 " serverKind="deliberation">
          <Probe />
        </ChatProvider>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
};
"""

_DRIVE = r"""
const { createRequire } = require('module');
const path = require('path');
const [FE, OUT] = process.argv.slice(2);
const { chromium } = createRequire(path.join(FE, 'package.json'))('@playwright/test');

const frame = (event, data) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
const TOPIC = '힌지 파손 원인';

async function open(browser) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });   // 새 저장소 — 새 대화의 첫 발화
  page.setDefaultTimeout(10000);
  page.__errors = [];
  page.on('pageerror', (e) => page.__errors.push(String(e)));
  await page.route('http://harness.invalid/**', (r) =>
    r.fulfill({ contentType: 'text/html', body: '<!doctype html><html><body><div id="root"></div></body></html>' }));
  await page.goto('http://harness.invalid/');
  await page.evaluate(() => { document.cookie = 'hwax_csrf=csrf-1; path=/'; });
  await page.addScriptTag({ path: path.join(OUT, 'stub.js') });
  await page.addScriptTag({ path: path.join(OUT, 'bundle.js') });
  await page.evaluate(() => window.__mount());
  // 기동 효과가 돈 뒤에 보낸다 — 계정별 캐시 로드가 대화 목록을 갈아 끼운다. 서버 대화 목록 요청은 같은 커밋의 뒤 효과가 낸다
  await page.waitForFunction(() => window.__calls.some((c) => c.url === '/agent/conversations' && c.method === 'GET'));
  return page;
}
const sent = (page) => page.evaluate(() => window.__calls.filter((c) => c.url.startsWith('/agent/chat')).map((c) => c.body.message));
// 방법 메뉴의 첫 발화 — DeliberatePage.confirmExperts 와 같은 부름(route.trigger + topic, 그 손잡이)
async function sendJob(page, job) {
  await page.evaluate(([j, topic]) => {
    const r = window.__routing[j];
    window.__send(r.trigger + topic, { ...(r.chair ? { chair_template: r.chair } : {}), ...(r.opts || {}) });
  }, [job, TOPIC]);
  await page.waitForFunction(() => typeof window.__push === 'function');
}
// 받던 턴을 실패로 끝낸다 — 오류 상자의 '다시 시도' 가 그 발화를 다시 보낸다
async function fail(page) {
  await page.evaluate((f) => { window.__push(f); window.__end(); }, frame('error', { code: 'deliberation_error', message: '심의 처리 중 오류: 시험이 낸 실패' }) + frame('done', {}));
  await page.waitForFunction(() => document.getElementById('streaming').textContent === 'false');
}

const SCENARIOS = {
  async jobs(browser) {
    const out = {};
    for (const job of ['sim-plan', 'test-plan', 'build-plan', 'default', 'diagnosis']) {
      const page = await open(browser);
      await sendJob(page, job);
      out[job] = { trigger: await page.evaluate((j) => window.__routing[j].trigger, job), sent: await sent(page), errors: page.__errors };
      await page.close();
    }
    return out;
  },
  // 메뉴를 거치지 않은 첫 발화 — 종전대로 '/심의 ' 가 붙고, 이미 '/심의' 로 쓴 글에는 한 번만
  async typed(browser) {
    const out = {};
    for (const [name, text] of [['plain', TOPIC], ['delib', '/심의 ' + TOPIC]]) {
      const page = await open(browser);
      await page.evaluate((t) => window.__send(t), text);
      await page.waitForFunction(() => typeof window.__push === 'function');
      out[name] = { sent: await sent(page), errors: page.__errors };
      await page.close();
    }
    return out;
  },
  // 다시 시도 — 실패한 첫 발화를 다시 보낸다(시뮬 다단 · 메뉴를 거치지 않은 글)
  async retry(browser) {
    const out = {};
    for (const [name, go] of [['sim', (p) => sendJob(p, 'sim-plan')],
                              ['plain', async (p) => { await p.evaluate((t) => window.__send(t), TOPIC); await p.waitForFunction(() => typeof window.__push === 'function'); }]]) {
      const page = await open(browser);
      await go(page);
      await fail(page);
      await page.locator('.chat-error-retry').click();
      await page.waitForFunction(() => window.__calls.filter((c) => c.url.startsWith('/agent/chat')).length === 2);
      out[name] = { sent: await sent(page), errors: page.__errors };
      await page.close();
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
    if not shutil.which("node") or not (FE / "node_modules/@playwright/test").exists() or not (FE / "node_modules/vite").exists():
        pytest.skip("node 또는 frontend node_modules(@playwright/test · vite) 가 없다 — 화면을 올려 볼 수 없다")
    out = tmp_path_factory.mktemp("prefix")
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
        for k, v in got[name].items():
            assert not v.get("errors"), f"{name}/{k} 화면이 예외를 던졌다: {v['errors']}"
        return got[name]
    return scenario


TOPIC = "힌지 파손 원인"


@pytest.mark.parametrize("job, trigger", [("sim-plan", "/시뮬심의 "), ("test-plan", "/시험계획 "), ("build-plan", "/시뮬심의 ")])
def test_방법_메뉴의_다단_트리거_첫_발화는_트리거_그대로_나간다(seen, job, trigger):
    """종전엔 '/심의 /시뮬심의 …' 로 나가 에이전트가 일반 /심의 로 열었다(다단 심의 · 시험 계획이 돌지 않았다)."""
    got = seen("jobs")[job]
    assert got["trigger"] == trigger, got
    assert got["sent"] == [trigger + TOPIC], got


def test_다른_첫_발화는_종전_그대로다(seen):
    jobs, typed = seen("jobs"), seen("typed")
    for job in ("default", "diagnosis"):              # '/심의 ' 트리거의 방법 — 한 번만
        assert jobs[job]["sent"] == ["/심의 " + TOPIC], jobs[job]
    assert typed["plain"]["sent"] == ["/심의 " + TOPIC], "메뉴를 거치지 않은 첫 발화에는 '/심의 ' 가 붙는다"
    assert typed["delib"]["sent"] == ["/심의 " + TOPIC], "이미 '/심의' 로 쓴 글에는 한 번만"


def test_다시_시도도_트리거로_시작하는_발화에는_또_붙이지_않는다(seen):
    r = seen("retry")
    assert r["sim"]["sent"] == ["/시뮬심의 " + TOPIC] * 2, r["sim"]
    assert r["plain"]["sent"] == ["/심의 " + TOPIC] * 2, "트리거로 시작하지 않는 발화의 다시 시도는 종전대로 심의를 다시 연다"
