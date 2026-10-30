# 확인 카드(10-30 HA-29) 단추를 헤드리스 브라우저에서 실제 ChatProvider · MessageList 로 누른다 — 보내는 글 · 켜 둔 루틴 · 닫힌 카드 · 잠긴 꼴
"""왜 — 카드 단추는 서버가 준 승인 · 거절 글을 '다음 말' 로 보낸다. 서버는 그 말을 이력의 마지막 항목이 그 카드일 때만 답으로 받고(_confirm_reply),
루틴 칸이 실린 요청은 카드 판정 전에 루틴 가지로 보낸다. 그래서 화면이 지킬 것이 셋이다(10-30 반대 검토).

  · 단추는 켜 둔 분석 루틴을 싣지 않는다 — 실리면 '취소' 를 눌러도 루틴 실행이 새로 서고 카드는 답하지 못한 채 닫힌다.
  · 카드 바로 뒤에 무엇이든(사람 말 · 보내기 알림) 붙으면 단추를 잠근다 — 서버는 그 단추 글을 카드의 답으로 받지 않는다.
  · 입력창에 쓰던 글 · 붙인 그림이 있으면 잠근다 — 보내기가 그 글을 지우고 그림을 이 말에 싣는다(ChatActionBar 와 같은 까닭).

잠긴 단추가 켜진 단추와 똑같이 보이던 것(.btn-secondary 에 :disabled 꼴이 없다)은 실제 CSS 로 잰다.
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
  const { messages, sendMessage, streaming, armedRoutine, setArmedRoutine, addUploadNotice, setInput, setAttachedImages } = useChat();
  return (
    <>
      <button id="send" type="button" onClick={() => sendMessage('판 전체 그래프 다시 봐줘')}>send</button>
      <button id="arm" type="button" onClick={() => setArmedRoutine({ id: 'rt-swelling', title: '스웰링 점검', inputs: {} })}>arm</button>
      <button id="notice" type="button"
        onClick={() => addUploadNotice({ text: 'Report Archive 에 보냈습니다 — 「점검 결과」', title: '점검',
          activity: [{ ts: 1, step: '도구 완료: ra_upload', tool: 'ra_upload', origin: 'upload', ok: true, result_preview: 'report 12' }] })}>notice</button>
      <button id="draft" type="button" onClick={() => setInput('쓰던 글')}>draft</button>
      <button id="clear" type="button" onClick={() => setInput('')}>clear</button>
      <button id="img" type="button"
        onClick={() => setAttachedImages([{ name: 'a.png', mime: 'image/png', dataUrl: 'data:image/png;base64,AAAA', width: 1, height: 1, bytes: 3 }])}>img</button>
      <span id="streaming">{String(streaming)}</span>
      <span id="armed">{armedRoutine ? armedRoutine.id : ''}</span>
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

# 가짜 백엔드 — 보낸 본문을 __calls 에 남긴다. 챗 스트림은 시험이 __push · __end 로 민다.
_STUB = r"""
(() => {
  window.__calls = [];
  const enc = new TextEncoder();
  const json = (body, status = 200) =>
    Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }));
  window.fetch = (url, init = {}) => {
    const u = String(url);
    const method = (init.method || 'GET').toUpperCase();
    window.__calls.push({ url: u, method, body: init.body ? JSON.parse(init.body) : null });
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
const fs = require('fs');
const [FE, OUT] = process.argv.slice(2);
const { chromium } = createRequire(path.join(FE, 'package.json'))('@playwright/test');
const frame = (event, data) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;

// 에이전트 서버가 내는 꼴 그대로(app._confirm_card · _confirm_card_text) — 사건이 먼저, 카드 글은 본문 끝에 token · result 로 온다
const CID = 'cf-7f3a9c2e41d0';
const CARD = {
  id: CID, expires_at: Date.now() + 30 * 60 * 1000,
  calls: [{ tool: 'run_job', app: 'StepForge', kind: 'job', args_text: 'kind=graph · project_id=P1', workload: '약 60초', again: false }],
  approve_text: `실행 — 확인 번호 ${CID}`, decline_text: `취소 — 확인 번호 ${CID} 는 실행하지 않음`,
};
const TEXT = '그래프 잡을 다시 걸려 했습니다.\n\n---\n**확인이 필요합니다** — 이번 말로 시키지 않은 작업이라 보내지 않았습니다.\n'
  + '1. StepForge `run_job` · kind=graph · project_id=P1 — 예상 작업량: 약 60초\n'
  + `실행하려면 **실행** 을 누르거나 '실행' 이라고 답하세요. 다른 말을 하면 보내지 않습니다. (확인 번호 \`${CID}\` · 30분)`;
const CARD_TURN = frame('status', { step: '확인 대기: run_job — 사람의 확인 전에는 보내지 않습니다', tool: 'run_job', ok: false, call: 'r1' })
  + frame('confirm', CARD) + frame('token', { delta: TEXT }) + frame('result', { type: 'text', content: TEXT }) + frame('done', {});

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
const idle = (page) => page.waitForFunction(() => document.getElementById('streaming').textContent === 'false');
const chats = (page) => page.evaluate(() => window.__calls.filter((c) => c.url.startsWith('/agent/chat')).map((c) => c.body));
// 카드마다 단추 둘의 잠김과 알림 글
const cards = (page) => page.evaluate(() => [...document.querySelectorAll('.msg-confirm')].map((el) => ({
  disabled: [...el.querySelectorAll('button')].map((b) => b.disabled),
  title: [...el.querySelectorAll('button')].map((b) => b.title || ''),
  note: (el.querySelector('.msg-confirm-note') || {}).textContent || '',
})));

async function cardTurn(page) {
  await page.click('#send');
  await page.waitForFunction(() => typeof window.__push === 'function');
  await page.evaluate((f) => { window.__push(f); window.__end(); }, CARD_TURN);
  await idle(page);
  await page.waitForSelector('.msg-confirm');
}

// 켜 둔 루틴이 있는 채 단추를 누른다 — which 는 '.btn-primary'(실행) · '.btn-secondary'(취소)
async function pressWithRoutine(page, which) {
  await cardTurn(page);
  await page.click('#arm');
  await page.waitForFunction(() => document.getElementById('armed').textContent === 'rt-swelling');
  const before = await cards(page);
  await page.click(`.msg-confirm ${which}`);
  await page.waitForFunction(() => window.__calls.filter((c) => c.url.startsWith('/agent/chat')).length >= 2);
  const during = await cards(page);
  await page.evaluate((f) => { window.__push(f); window.__end(); }, frame('result', { type: 'text', content: '네' }) + frame('done', {}));
  await idle(page);
  const sent = (await chats(page))[1];
  const after = await cards(page);
  const armed = await page.evaluate(() => document.getElementById('armed').textContent);
  return { before, during, after, sent, armed };
}

const SCENARIOS = {
  approve: (page) => pressWithRoutine(page, '.btn-primary'),
  decline: (page) => pressWithRoutine(page, '.btn-secondary'),
  // 카드 뒤에 사람 말 없이 보내기 알림이 붙는다 — 서버는 이력 끝이 그 알림이라 단추 글을 카드의 답으로 받지 않는다
  notice: async (page) => {
    await cardTurn(page);
    const before = await cards(page);
    await page.click('#notice');
    await page.waitForFunction(() => document.querySelectorAll('.msg.assistant').length >= 2);
    const after = await cards(page);
    await page.click('.msg-confirm .btn-primary', { force: true });
    await page.waitForTimeout(300);
    return { before, after, chats: (await chats(page)).length };
  },
  // 입력창에 쓰던 글 · 붙인 그림 — 보내기가 그 글을 지우고 그림을 이 말에 싣는다
  composer: async (page) => {
    await cardTurn(page);
    await page.click('#draft');
    await page.waitForTimeout(100);
    const draft = await cards(page);
    await page.click('.msg-confirm .btn-primary', { force: true });
    await page.waitForTimeout(300);
    const pressed = (await chats(page)).length;
    await page.click('#clear');
    await page.waitForTimeout(100);
    const cleared = await cards(page);
    await page.click('#img');
    await page.waitForTimeout(100);
    const img = await cards(page);
    return { draft, pressed, cleared, img };
  },
};

// 잠긴 단추의 꼴 — 실제 CSS(tokens · globals · chat)를 올린 빈 문서에서 잰다
async function looks(browser) {
  const css = ['tokens.css', 'globals.css', 'chat.css'].map((f) => fs.readFileSync(path.join(FE, 'src/styles', f), 'utf8')).join('\n');
  const page = await browser.newPage();
  await page.setContent(`<!doctype html><html><head><style>${css}</style></head><body><div class="msg-confirm">`
    + '<button id="on" type="button" class="btn-secondary">취소</button>'
    + '<button id="off" type="button" class="btn-secondary" disabled>취소</button>'
    + '<button id="off1" type="button" class="btn-primary" disabled>실행</button></div></body></html>');
  const st = (id) => page.$eval('#' + id, (e) => { const s = getComputedStyle(e); return { opacity: s.opacity, cursor: s.cursor, bg: s.backgroundColor }; });
  const out = { on: await st('on'), off: await st('off'), off1: await st('off1') };
  await page.hover('#off', { force: true });
  out.off_hover = await st('off');
  await page.close();
  return out;
}

(async () => {
  let browser;
  try { browser = await chromium.launch(); } catch (e) { process.stdout.write(JSON.stringify({ skip: String(e).slice(0, 300) })); return; }
  const out = {};
  try {
    for (const [name, run] of Object.entries(SCENARIOS)) {
      const page = await open(browser);
      try { out[name] = { ...(await run(page)), errors: page.__errors }; }
      catch (e) { out[name] = { failed: String((e && e.stack) || e).slice(0, 1500) }; }
      await page.close();
    }
    out.looks = await looks(browser);
  } finally { await browser.close(); }
  out.card = CARD;
  process.stdout.write(JSON.stringify(out));
})().catch((e) => { process.stderr.write(String((e && e.stack) || e)); process.exit(1); });
"""


@pytest.fixture(scope="module")
def seen(tmp_path_factory):
    out = tmp_path_factory.mktemp("confirmcard")
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
        if name in ("looks", "card"):
            return got[name]
        assert "failed" not in got[name], f"시나리오 {name} 이 끝까지 돌지 못했다:\n{got[name].get('failed')}"
        assert not got[name].get("errors"), f"화면이 예외를 던졌다: {got[name]['errors']}"
        return got[name]
    return scenario


def test_실행_단추는_서버가_준_글만_보내고_켜_둔_루틴을_싣지_않는다(seen):
    s, card = seen("approve"), seen("card")
    assert s["before"] == [{"disabled": [False, False], "title": ["", ""],
                            "note": f"1건 · 잡 · 확인 번호 {card['id']} · 30분"}], s["before"]
    assert s["sent"]["message"] == card["approve_text"], s["sent"]
    # 루틴이 실리면 에이전트 chat() 은 카드를 판정하기 전에 루틴 가지로 보낸다 — 승인되지 않고 단추 글을 덧붙인 말로 루틴이 돈다
    assert "routine" not in s["sent"], s["sent"]
    assert s["armed"] == "rt-swelling", "켜 둔 루틴은 입력창의 다음 보내기를 기다린다(쓰지도 끄지도 않는다)"
    assert s["sent"]["history"][-1]["role"] == "assistant" and card["id"] in s["sent"]["history"][-1]["content"], \
        "이력의 마지막 항목이 그 카드 글이어야 서버가 답으로 받는다"
    assert s["during"][0]["disabled"] == [True, True] and s["after"][0]["disabled"] == [True, True]
    assert s["after"][0]["note"] == "이 카드에는 이미 답했습니다", s["after"]


def test_취소_단추도_켜_둔_루틴을_싣지_않는다(seen):
    s, card = seen("decline"), seen("card")
    assert s["sent"]["message"] == card["decline_text"] and "routine" not in s["sent"], s["sent"]
    assert s["armed"] == "rt-swelling"


def test_카드_뒤에_보내기_알림이_붙으면_단추를_잠근다(seen):
    s = seen("notice")
    assert s["before"][0]["disabled"] == [False, False]
    assert s["after"][0]["disabled"] == [True, True], "서버는 이력 끝이 그 알림이면 단추 글을 카드의 답으로 받지 않는다(카드를 지운다)"
    assert "닫혔습니다" in s["after"][0]["note"] and "새 카드" in s["after"][0]["note"], s["after"]
    assert s["chats"] == 1, "잠긴 단추는 아무것도 보내지 않는다"


def test_입력창에_쓰던_글이나_붙인_그림이_있으면_단추를_잠근다(seen):
    s = seen("composer")
    assert s["draft"][0]["disabled"] == [True, True], s["draft"]
    assert "입력창" in s["draft"][0]["note"] and "입력창" in s["draft"][0]["title"][0], s["draft"]
    assert s["pressed"] == 1, "잠긴 단추는 쓰던 글을 지우고 보내지 않는다"
    assert s["cleared"][0]["disabled"] == [False, False], "글을 비우면 다시 누를 수 있다"
    assert s["img"][0]["disabled"] == [True, True], "붙인 그림이 승인 말에 실려 사라지지 않게"


def test_잠긴_취소_단추는_켜진_단추와_다르게_보인다(seen):
    lk = seen("looks")
    assert lk["on"]["opacity"] == "1" and lk["on"]["cursor"] == "pointer"
    assert float(lk["off"]["opacity"]) < 1 and lk["off"]["cursor"] == "not-allowed", lk["off"]
    assert lk["off_hover"]["bg"] == lk["off"]["bg"], "잠긴 단추에는 hover 가 먹지 않는다"
    assert lk["off1"]["opacity"] == lk["off"]["opacity"], "실행 · 취소가 같은 꼴로 잠긴다"
