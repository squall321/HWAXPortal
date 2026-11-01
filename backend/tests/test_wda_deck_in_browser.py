# '발표자료로' 를 헤드리스 브라우저에서 실제 ChatProvider · MessageList 로 본다 — 서버는 띄우지 않는다(가짜 fetch · 가짜 시계, docs/wda-deck)
"""왜 — 단추의 일은 '어느 자리에 서는가' 와 '끝난 알림이 어느 대화에 남는가' 다. 순수 함수 시험으로는 안 잡힌다.

  · 자리 — '/보고서' 저장 답(deliberation 템플릿)은 WDA 의 심의 꼴(delib-16x9)이 준비되지 않으면 숨고(사용자 결정 U-6), RA 보내기 알림(그 밖)은
    owner 만 있으면 선다. 권한 둘 중 하나가 없거나 스위치가 꺼졌으면 어디에도 없다.
  · 맡기기 — 출력 PPT · PDF 와 정식 보고서 꼴이 기본이고 단추를 누른 대화의 서버 id 가 간다.
  · 끝 — 진행을 보다가 끝나면 advance 한 번, 알림은 **단추를 누른 그 대화**에 남는다 — 다른 대화로 옮겨 가 단추 칸이 사라져도 입력창 위 줄이 잇는다.
  · 다시 묻기 — 줄이 목록을 한 번 못 읽어도 다음 차례에 다시 묻는다(멈추면 끝 알림이 남지 않는다).
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
import { DeckResume } from '__FE__/src/components/chat/DeckResume';

function Probe() {
  const { messages, conversations, activeConversation, selectConversation } = useChat();
  return (
    <>
      <span id="active">{activeConversation?.serverId ?? ''}</span>
      <span id="counts">{conversations.map((c) => `${c.serverId}:${c.messages.length}`).join(',')}</span>
      <span id="lastA">{conversations.find((c) => c.serverId === 'srv-A')?.messages.slice(-1)[0]?.text ?? ''}</span>
      <button id="toA" type="button" onClick={() => selectConversation('cA')}>A</button>
      <button id="toB" type="button" onClick={() => selectConversation('cB')}>B</button>
      <DeckResume />
      <MessageList messages={messages} />
    </>
  );
}
(window as unknown as { __mount: (ents?: string[]) => void }).__mount = (ents) => {
  const user = { subject: 'u1@corp.example', email: 'u1@corp.example', display_name: 'U', groups: [],
                 entitlements: ents ?? ['feat:chat', 'plat:webdesign', 'plat:reportarchive'] };
  createRoot(document.getElementById('root')!).render(
    <AuthContext.Provider
      value={{ user, status: 'authenticated', login: () => undefined, logout: async () => undefined, refresh: async () => undefined }}
    >
      <MemoryRouter>
        <ChatProvider>
          <Probe />
        </ChatProvider>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
};
"""

_STUB = r"""
(() => {
  window.__calls = [];
  const json = (body, status = 200) =>
    Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }));
  window.fetch = (url, init = {}) => {
    const u = String(url);
    const method = (init.method || 'GET').toUpperCase();
    window.__calls.push({ url: u, method, body: typeof init.body === 'string' ? JSON.parse(init.body) : null });
    if (u === '/agent/deck/status') return json(window.__status);
    if (u === '/agent/deck/jobs' && method === 'POST') return json(window.__created);
    if (u === '/agent/deck/jobs' && method === 'GET') {
      if (window.__listFail > 0) { window.__listFail -= 1; return json({ detail: '잠시 답하지 않는다' }, 502); }
      return json({ jobs: window.__list || [], keep_days: 7 });
    }
    if (u.startsWith('/agent/deck/jobs/')) {
      if (u.endsWith('/advance')) { window.__list = []; return json(window.__advanced); }
      if (u.endsWith('/dismiss')) return json({ dismissed: true });
      return json(window.__states.length > 1 ? window.__states.shift() : window.__states[0]);
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

const JOB = 'f'.repeat(32);
const NOTICE_TEXT = '보고서 41「설계 검토」로 발표자료를 만들었습니다 — PPT(글자를 고칠 수 있는 꼴) · PDF(정식 보고서 문서). 받기 — '
  + `[PPT 받기](/agent/deck/jobs/${JOB}/files/pptx) · [PDF 받기](/agent/deck/jobs/${JOB}/files/pdf).`;
const base = { job_id: JOB, report: { id: 41, title: '설계 검토' }, options: { targets: ['pptx', 'pdf'], doc_style: 'report', pptx_mode: 'hybrid' },
  conversation_id: 'srv-A', created_at: 1, elapsed_s: 3, step: '', progress: 0, error: null, late: false, next: null, skipped: [], files: [] };
const QUEUED = { ...base, state: 'queued', step: '줄 서는 중', created: true };
const RENDERING = { ...base, state: 'rendering', step: '만드는 중', progress: 80, elapsed_s: 4 };
const FINISH = { ...base, state: 'done', step: '끝', progress: 100, next: 'finish', elapsed_s: 6 };
const DONE = { ...base, state: 'done', step: '끝', progress: 100, next: null, elapsed_s: 6,
  files: [{ kind: 'pptx', bytes: 1228800, label: 'PPT', url: `/agent/deck/jobs/${JOB}/files/pptx` },
          { kind: 'pdf', bytes: 1972224, label: 'PDF', url: `/agent/deck/jobs/${JOB}/files/pdf` }],
  noticed: true, notice: { text: NOTICE_TEXT, deck: { job_id: JOB, state: 'done', report_id: 41, files: ['pptx', 'pdf'] },
    activity: [{ ts: 1, step: '발표자료 만들기(사람이 맡김)', tool: 'web_design_agents', detail: '{}', result_full: '{"report_id":41}', ok: true, origin: 'upload' }] } };
const STATUS = (deliberation) => ({ enabled: true, reason: null, formats: { deliberation }, targets: ['pptx', 'pdf', 'docx', 'html', 'video'],
  doc_styles: ['report', 'brief', 'memo'], defaults: { targets: ['pptx', 'pdf'], doc_style: 'report' }, keep_days: 7 });

// 대화 둘 — A 에 '/보고서' 저장 답(58, deliberation)과 RA 보내기 알림(41, 그 밖), B 에 일반 답
const SEED = JSON.stringify([
  { id: 'cA', serverId: 'srv-A', title: 'A', createdAt: 2, updatedAt: 2, messages: [
    { role: 'user', content: '/보고서', ts: 1 },
    { role: 'assistant', content: '📄 Report Archive 보고서 #58 로 저장했습니다 — 「심의 — 굽힘」', ts: 2, raReport: { id: 58, title: '심의 — 굽힘' } },
    { role: 'assistant', content: '「설계.pptx」 으로 Report Archive 보고서 초안을 만들었습니다 — 보고서 41', ts: 3,
      activity: [{ ts: 3, step: 'Report Archive 보고서 초안(사람이 올림)', tool: 'create_report_draft', detail: '{"file":"설계.pptx"}',
                   result_full: '{"report_id":41,"title":"설계 검토"}', ok: true, origin: 'upload' }] } ] },
  { id: 'cB', serverId: 'srv-B', title: 'B', createdAt: 1, updatedAt: 1, messages: [
    { role: 'user', content: '안녕', ts: 1 }, { role: 'assistant', content: '안녕하세요', ts: 2 } ] } ]);

async function open(browser, { status, ents } = {}) {
  const page = await browser.newPage();
  page.setDefaultTimeout(10000);
  page.__errors = [];
  page.on('pageerror', (e) => page.__errors.push(String(e)));
  await page.route('http://harness.invalid/**', (r) =>
    r.fulfill({ contentType: 'text/html', body: '<!doctype html><html><body><div id="root"></div></body></html>' }));
  await page.clock.install({ time: new Date('2026-11-01T00:00:00Z') });
  await page.goto('http://harness.invalid/');
  await page.addScriptTag({ path: path.join(OUT, 'stub.js') });
  await page.evaluate(([seed, st]) => {
    localStorage.setItem('hwax.chat.u1@corp.example.conversations', seed);
    localStorage.setItem('hwax.chat.u1@corp.example.activeId', 'cA');
    window.__status = st;
    window.__states = [];
  }, [SEED, status === undefined ? STATUS(false) : status]);
  await page.addScriptTag({ path: path.join(OUT, 'bundle.js') });
  await page.evaluate((e) => window.__mount(e), ents || null);
  await page.waitForTimeout(80);
  return page;
}
const text = (page, id) => page.evaluate((i) => document.getElementById(i).textContent, id);
const buttons = (page) => page.evaluate(() => document.querySelectorAll('.deck-go').length);
const calls = (page, prefix) => page.evaluate((p) => window.__calls.filter((c) => c.url.startsWith(p)), prefix);
async function forward(page, ms) { await page.clock.fastForward(ms); await page.waitForTimeout(60); }

async function makeJob(page) {
  await page.evaluate(([q, r, f, d]) => { window.__created = q; window.__states = [r, f]; window.__advanced = d; window.__list = [q]; },
                      [QUEUED, RENDERING, FINISH, DONE]);
  await page.locator('.deck-go').first().click();
  const opts = await page.evaluate(() => ({
    checked: Array.from(document.querySelectorAll('.deck-opts input')).map((i) => i.checked),
    style: (document.querySelector('.deck-style select') || {}).value || null }));
  await page.locator('.deck-panel .upl-go').click();
  await page.getByText('발표자료 만드는 중').first().waitFor();
  return opts;
}

const SCENARIOS = {
  // 심의 꼴이 없는 WDA — '/보고서'(deliberation)는 숨고 RA 보내기 알림은 선다. 꼴이 서면 둘 다
  async spots(browser) {
    const page = await open(browser);
    const without = await buttons(page);
    const titles = await page.evaluate(() => Array.from(document.querySelectorAll('.deck-go')).map((b) =>
      b.closest('.msg').querySelector('.msg-content').textContent));
    const page2 = await open(browser, { status: STATUS(true) });
    const withFormat = await buttons(page2);
    return { without, titles, withFormat, errors: [...page.__errors, ...page2.__errors] };
  },
  // 권한 둘 중 하나가 없으면 묻지도 않는다 · 스위치가 꺼졌으면 어디에도 없다
  async hidden(browser) {
    const noPerm = await open(browser, { ents: ['feat:chat', 'plat:webdesign'] });
    const off = await open(browser, { status: { ...STATUS(true), enabled: false, reason: 'off' } });
    return { noPerm: await buttons(noPerm), noPermCalls: (await calls(noPerm, '/agent/deck')).length,
             off: await buttons(off), errors: [...noPerm.__errors, ...off.__errors] };
  },
  // 그 대화에 머문다 — 진행을 보다가 끝나면 advance 한 번 · 알림이 이 대화에 · 받기 링크는 포털 경로
  async stay(browser) {
    const page = await open(browser);
    const before = await text(page, 'counts');
    const opts = await makeJob(page);
    const create = (await calls(page, '/agent/deck/jobs')).find((c) => c.method === 'POST' && c.url === '/agent/deck/jobs');
    await forward(page, 3100);
    const mid = await page.evaluate(() => (document.querySelector('.deck-panel .upl-note') || {}).textContent || '');
    await forward(page, 3100);
    await page.getByText('발표자료를 만들었습니다').first().waitFor();
    const links = await page.evaluate(() => Array.from(document.querySelectorAll('.deck-file')).map((a) => a.getAttribute('href')));
    const advances = (await calls(page, '/agent/deck/jobs/')).filter((c) => c.url.endsWith('/advance')).length;
    // 대화에 남은 알림의 받기 링크도 눌리는 링크다(같은 오리진 절대경로 — md.ts)
    const noticeLinks = await page.evaluate(() => Array.from(document.querySelectorAll('.msg .md-link')).map((a) => a.getAttribute('href')));
    return { before, opts, create: create && create.body, mid, links, noticeLinks, advances, after: await text(page, 'counts'),
             last: await text(page, 'lastA'), errors: page.__errors };
  },
  // 다른 대화로 옮겨 간다 — 단추 칸이 사라져도 입력창 위 줄이 잇고, 알림은 단추를 누른 A 에 남는다(B 가 아니라)
  async away(browser) {
    const page = await open(browser);
    await makeJob(page);
    await page.locator('#toB').click();
    await page.waitForTimeout(60);
    await page.evaluate((f) => { window.__list = [f]; }, FINISH);      // 그 사이 WDA 가 끝냈다
    await forward(page, 10500);
    await page.waitForFunction(() => document.getElementById('lastA').textContent.includes('발표자료를 만들었습니다'));
    return { active: await text(page, 'active'), counts: await text(page, 'counts'),
             advances: (await calls(page, '/agent/deck/jobs/')).filter((c) => c.url.endsWith('/advance')).length, errors: page.__errors };
  },
  // 목록을 한 번 못 읽어도 줄이 다시 묻기를 멈추지 않는다 — 다음 차례에 끝을 보고 알림을 A 에
  async blip(browser) {
    const page = await open(browser);
    await makeJob(page);
    await page.locator('#toB').click();
    await page.waitForTimeout(60);
    await page.evaluate((f) => { window.__list = [f]; window.__listFail = 1; }, FINISH);
    await forward(page, 10500);                                         // 이 차례는 못 읽는다
    const mid = { last: await text(page, 'lastA'), strip: await page.evaluate(() => !!document.querySelector('.deck-resume')) };
    await forward(page, 10500);                                         // 다음 차례에 다시 묻는다
    await page.waitForFunction(() => document.getElementById('lastA').textContent.includes('발표자료를 만들었습니다'));
    return { mid, counts: await text(page, 'counts'),
             lists: (await calls(page, '/agent/deck/jobs')).filter((c) => c.method === 'GET' && c.url === '/agent/deck/jobs').length,
             errors: page.__errors };
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
    out = tmp_path_factory.mktemp("wdadeck")
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


def test_심의_꼴이_없으면_보고서_저장_답은_숨고_RA_보내기_알림만_선다(seen):
    s = seen("spots")
    assert s["without"] == 1 and "보고서 초안을 만들었습니다" in s["titles"][0], "사용자 결정 U-6 — 심의 형식이 설 때까지 숨긴다"
    assert s["withFormat"] == 2


def test_권한이나_스위치가_없으면_단추가_없다(seen):
    s = seen("hidden")
    assert s["noPerm"] == 0 and s["noPermCalls"] == 0, "권한이 없으면 상태도 묻지 않는다"
    assert s["off"] == 0


def test_맡기면_진행을_보이고_끝나면_그_대화에_알림과_포털_받기_링크(seen):
    s = seen("stay")
    assert s["opts"] == {"checked": [True, True, False, False, False], "style": "report"}, "기본 PPT + PDF · 정식 보고서"
    assert s["create"] == {"report_id": 41, "conversation_id": "srv-A", "targets": ["pptx", "pdf"], "doc_style": "report"}
    assert "만드는 중" in s["mid"]
    assert s["links"] == [f"/agent/deck/jobs/{'f' * 32}/files/pptx", f"/agent/deck/jobs/{'f' * 32}/files/pdf"], "받기는 포털 경로 — WDA 주소가 아니다"
    assert s["advances"] == 1
    assert s["before"] == "srv-A:3,srv-B:2" and s["after"] == "srv-A:4,srv-B:2" and "발표자료를 만들었습니다" in s["last"]
    assert s["noticeLinks"] == s["links"], "대화에 남은 알림의 받기 링크도 눌린다"


def test_다른_대화로_옮겨_가도_알림은_단추를_누른_대화에(seen):
    s = seen("away")
    assert s["active"] == "srv-B"
    assert s["counts"] == "srv-A:4,srv-B:2", "알림은 A 에 — 지금 보는 B 가 아니다"
    assert s["advances"] == 1


def test_목록을_한_번_못_읽어도_줄이_다시_묻고_알림을_남긴다(seen):
    s = seen("blip")
    assert s["mid"]["strip"] is True and "발표자료를 만들었습니다" not in s["mid"]["last"], "못 읽은 차례에는 줄을 그대로 둔다"
    assert s["counts"] == "srv-A:4,srv-B:2", "다음 차례에 다시 물어 끝 알림을 A 에"
    assert s["lists"] >= 3
