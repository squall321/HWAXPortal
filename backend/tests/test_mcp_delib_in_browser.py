# MCP 심의 화면(WD-03 · 04 · 05 · 06 · 08 · 13)을 헤드리스 브라우저에서 실제 ChatProvider · ChatSidebar · MessageList 로 누른다 — 가짜 fetch · 가짜 시계
"""docs/request-1125 WD-03 · WD-04 · WD-05 · WD-06 · WD-08 · WD-13 의 화면 몫. 서버는 띄우지 않는다(test_confirm_card_in_browser 와 같은 길).
서버 사본은 진짜 꼴로 만든다 — 엔진 _conv_item(AST) → 포털 messages_of → 대화 저장소에 쓰고 읽은 그대로다.

  · 사이드바(WD-03 · WD-04) — 출처 mcp 대화에 'MCP' 표지 · 전부 · 웹 · MCP 거르기 · 새로 고침 없이(창 포커스) 새 대화가 선다.
  · 엔진 이어가기(WD-05) — 들인 MCP 심의의 이어가기는 /agent/chat 이 아니라 /agent/engine-delib/continue 로 · 진행 카드가 서고 다시 물어 끝나면 결과가 붙는다.
  · 확인 카드(WD-06) — 맨 위 요약 · 종류 · 라운드 · RA 저장을 바꾸면 '바꾼 대로 실행' 이 바꾼 칸만 confirm_edit 로 싣는다.
  · 진행 카드(WD-13) — SSE job_card 가 카드가 되고 다시 물어 끝나면 보고서 링크 · 심의 페이지로 가는 단추.
  · 엔진 잡(WD-08) — 찾기 · 결정문 전문 · 이 대화에 싣기 · 더 보기.
화면 캡처는 실제 CSS 를 얹어 스크래치(HWAX_SHOTS 가 있으면 그 폴더)에 남긴다.
"""
import json
import os
import subprocess

import pytest

from app.agent import mcp_delib as M
from app.agent.conv_store import ConversationStore
from app.config import Settings
from tests.test_delib_stream_in_browser import _BUILD, FE, pytestmark  # noqa: F401 — 같은 도구가 없으면 같이 건너뛴다
from tests.test_mcp_delib import _engine_conv, _job

_HARNESS = r"""
import { createRoot } from 'react-dom/client';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { AuthContext } from '__FE__/src/auth/AuthContext';
import { ChatProvider, useChat } from '__FE__/src/state/ChatContext';
import { MessageList } from '__FE__/src/components/chat/MessageList';
import { ChatSidebar } from '__FE__/src/components/chat/ChatSidebar';

function Probe() {
  const { messages, sendMessage, streaming, activeId } = useChat();
  const loc = useLocation();
  return (
    <div style={{ display: 'flex', gap: 12 }}>
      <div id="side" style={{ width: 280, position: 'relative' }}><ChatSidebar open onToggle={() => undefined} /></div>
      <div style={{ flex: 1, maxWidth: 820 }}>
        <button id="send" type="button" onClick={() => sendMessage('힌지 심의 열어 줘')}>send</button>
        <span id="streaming">{String(streaming)}</span>
        <span id="active">{activeId ?? ''}</span>
        <span id="path">{loc.pathname}</span>
        <span id="navstate">{JSON.stringify(loc.state ?? null)}</span>
        <div id="thread"><MessageList messages={messages} /></div>
      </div>
    </div>
  );
}
(window as unknown as { __mount: (kind: 'chat' | 'deliberation') => void }).__mount = (kind) => {
  const user = { subject: 'me@example.com', email: 'me@example.com', display_name: '나', groups: [] };
  createRoot(document.getElementById('root')!).render(
    <AuthContext.Provider
      value={{ user, status: 'authenticated', login: () => undefined, logout: async () => undefined, refresh: async () => undefined }}
    >
      <MemoryRouter>
        <ChatProvider storagePrefix={kind === 'chat' ? 'hwax.chat' : 'hwax.delib'} serverKind={kind}><Probe /></ChatProvider>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
};
"""

# 가짜 백엔드 — 보낸 요청을 __calls 에. 대화 목록 · 상세 · 엔진 창구는 window.__srv 가 답한다. 챗 스트림은 시험이 __push · __end 로 민다.
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
    const S = window.__srv;
    if (u === '/agent/conversations' && method === 'GET') return json({ conversations: S.list });
    if (u === '/agent/conversations' && method === 'POST') return json({ id: 'srv-new' });
    if (/^\/agent\/conversations\/[^/]+\/messages$/.test(u)) return json({ ok: true });
    const m = /^\/agent\/conversations\/([^/?]+)$/.exec(u);
    if (m && method === 'GET') return S.convs[decodeURIComponent(m[1])] ? json(S.convs[decodeURIComponent(m[1])]) : json({ detail: 'nf' }, 404);
    if (u === '/agent/engine-delib/continue') return json(S.cont);
    if (u.startsWith('/agent/engine-delib/status/')) return json(S.status.length > 1 ? S.status.shift() : S.status[0]);
    if (/^\/agent\/engine-delib\/jobs\/[^/]+\/decision$/.test(u)) return json(S.decision);
    if (u.startsWith('/agent/engine-delib/jobs')) return json(u.includes('until=') ? S.jobsMore : S.jobs);
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
const [FE, OUT, SHOTS] = process.argv.slice(2);
const { chromium } = createRequire(path.join(FE, 'package.json'))('@playwright/test');
const DATA = JSON.parse(fs.readFileSync(path.join(OUT, 'data.json'), 'utf8'));
const frame = (event, data) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
const CSS = ['tokens.css', 'globals.css', 'chat.css', 'chatpage.css', 'ui.css']
  .map((f) => fs.readFileSync(path.join(FE, 'src/styles', f), 'utf8')).join('\n');

async function open(browser, kind, srv) {
  const page = await browser.newPage({ viewport: { width: 1200, height: 900 } });
  page.setDefaultTimeout(10000);
  page.__errors = [];
  page.on('pageerror', (e) => page.__errors.push(String(e)));
  await page.clock.install({ time: new Date('2026-11-28T06:00:00Z') });
  await page.route('http://harness.invalid/**', (r) =>
    r.fulfill({ contentType: 'text/html', body: `<!doctype html><html><head><style>${CSS}</style></head><body><div id="root"></div></body></html>` }));
  await page.goto('http://harness.invalid/');
  await page.addScriptTag({ path: path.join(OUT, 'stub.js') });
  await page.evaluate((s) => { window.__srv = s; }, srv);
  await page.addScriptTag({ path: path.join(OUT, 'bundle.js') });
  await page.evaluate((k) => window.__mount(k), kind);
  return page;
}
const shot = async (page, name, sel) => {
  if (!SHOTS) return;
  const el = sel ? await page.$(sel) : null;
  await (el || page).screenshot({ path: path.join(SHOTS, name) });
};
const idle = (page) => page.waitForFunction(() => document.getElementById('streaming').textContent === 'false');
const calls = (page, pre) => page.evaluate((p) => window.__calls.filter((c) => c.url.startsWith(p)), pre);
const items = (page) => page.evaluate(() => [...document.querySelectorAll('#side .sb-item-title')].map((b) => b.textContent));

const SCENARIOS = {
  // WD-03 · WD-04 — 표지 · 거르기 · 창 포커스에 새 대화
  sidebar: async (page) => {
    await page.waitForSelector('#side .sb-item-src');
    const before = await items(page);
    const btns = await page.$$eval('#side .sb-src-btn', (bs) => bs.map((b) => b.textContent));
    await page.click('#side .sb-src-btn:has-text("MCP")');
    const onlyMcp = await items(page);
    await page.click('#side .sb-src-btn:has-text("웹")');
    const onlyWeb = await items(page);
    await page.click('#side .sb-src-btn:has-text("전부")');
    await page.evaluate((m) => { window.__srv.list = [m, ...window.__srv.list]; window.dispatchEvent(new Event('focus')); }, DATA.lateMeta);
    await page.waitForFunction(() => document.querySelectorAll('#side .sb-item').length === 3);
    const after = await items(page);
    await shot(page, 'wd-sidebar.png', '#side');
    return { before, btns, onlyMcp, onlyWeb, after };
  },
  // WD-05 · WD-13 — 들인 MCP 심의를 엔진으로 잇고 진행 카드가 끝나면 다시 읽는다
  continue: async (page) => {
    await page.click(`#side .sb-item-title:has-text("${DATA.mcpMeta.title}")`);
    await page.waitForSelector('.dv-mcpjob');
    const line = await page.textContent('.dv-mcpjob');
    const head = await page.textContent('.dv-continue-head');
    await page.fill('.dv-continue-input', '낙하 성능을 최우선으로');
    await page.selectOption('.dv-continue-opts select', '4');
    await page.click('.dv-continue-btn');
    await page.waitForSelector('.job-card');
    const firstState = await page.textContent('.job-card-state');
    await shot(page, 'wd-continue-running.png', '#thread');
    // 다음 물음(10초 뒤) — 끝남 · 이 대화에 들었다
    // 포털이 다음 잡을 같은 대화에 들였다 — 상세와 목록의 시각이 함께 바뀐다
    await page.evaluate((c) => {
      window.__srv.convs[c.id] = c;
      window.__srv.list = window.__srv.list.map((m) => (m.id === c.id ? { ...m, updated_at: c.updated_at } : m));
    }, DATA.mcpConvAfter);
    await page.clock.fastForward(11000);
    await page.waitForSelector('.job-card.is-end');
    await page.waitForFunction(() => document.querySelectorAll('.dv-decision').length >= 2, null, { timeout: 5000 }).catch(() => null);
    const endLinks = await page.textContent('.job-card-links').catch(() => '');
    await shot(page, 'wd-continue-done.png', '#thread');
    return { line, head, firstState, endLinks, cont: await calls(page, '/agent/engine-delib/continue'), chats: (await calls(page, '/agent/chat')).length,
             status: (await calls(page, '/agent/engine-delib/status/')).length, decisions: await page.$$eval('.dv-decision', (d) => d.length),
             lists: (await calls(page, '/agent/conversations')).filter((c) => c.url === '/agent/conversations' && c.method === 'GET').length };
  },
  // WD-06 — 요약 · 바꾸기 · confirm_edit
  confirm: async (page) => {
    await page.click('#send');
    await page.waitForFunction(() => typeof window.__push === 'function');
    await page.evaluate((f) => { window.__push(f); window.__end(); }, DATA.confirmTurn);
    await idle(page);
    await page.waitForSelector('.msg-confirm-sum');
    const sum = await page.textContent('.msg-confirm-sum');
    const label0 = await page.textContent('.msg-confirm .btn-primary');
    await page.selectOption('.msg-confirm-sum select[aria-label="심의 종류"]', 'option-select');
    await page.selectOption('.msg-confirm-sum select[aria-label="라운드"]', '5');
    await page.uncheck('.msg-confirm-sum input[aria-label="RA 저장"]');
    const label1 = await page.textContent('.msg-confirm .btn-primary');
    await shot(page, 'wd-confirm-card.png', '#thread');
    await page.evaluate(() => { window.__push = null; });
    await page.click('.msg-confirm .btn-primary');
    await page.waitForFunction(() => window.__calls.filter((c) => c.url.startsWith('/agent/chat')).length >= 2);
    const sent = (await calls(page, '/agent/chat'))[1].body;
    await page.waitForFunction(() => typeof window.__push === 'function');
    await page.evaluate((f) => { window.__push(f); window.__end(); }, frame('result', { type: 'text', content: '네' }) + frame('done', {}));
    await idle(page);
    return { sum, label0, label1, sent };
  },
  // WD-13 — SSE job_card → 다시 묻기 → 끝나면 보고서 · 심의 페이지
  jobcard: async (page) => {
    await page.click('#send');
    await page.waitForFunction(() => typeof window.__push === 'function');
    await page.evaluate((f) => { window.__push(f); window.__end(); }, DATA.jobTurn);
    await idle(page);
    await page.waitForSelector('.job-card');
    const running = await page.textContent('.job-card-state');
    await page.clock.fastForward(11000);              // 다음 물음(10초 뒤) — 끝남
    await page.waitForSelector('.job-card.is-end');
    const text = await page.textContent('.job-card');
    await shot(page, 'wd-job-card.png', '#thread');
    await page.click('.job-card-btn');
    await page.waitForFunction(() => document.getElementById('path').textContent === '/deliberate');
    return { running, text, nav: JSON.parse(await page.textContent('#navstate')), status: await calls(page, '/agent/engine-delib/status/') };
  },
  // WD-08 — 찾기 · 결정문 · 싣기 · 더 보기
  jobs: async (page) => {
    await page.click('#side .sb-engine');
    await page.waitForSelector('.ejp');
    await page.fill('.ejp-filter input[type="search"]', '힌지');
    await page.fill('.ejp-filter input[aria-label="시작일"]', '2026-11-01');
    await page.click('.ejp-filter button[type="submit"]');
    await page.waitForSelector('.ejp-row');
    const rows = await page.$$eval('.ejp-row', (r) => r.length);
    await page.click('.ejp-row:first-child .cx-chip:has-text("결정문 보기")');
    await page.waitForSelector('.ejp-decision .tb-root, .ejp-decision');
    await page.waitForFunction(() => (document.querySelector('.ejp-decision') || {}).textContent.includes('리브'));
    const decision = await page.textContent('.ejp-decision');
    await shot(page, 'wd-engine-jobs.png', '.ejp');
    await page.click('.ejp-row:first-child .cx-chip:has-text("이 대화에 싣기")');
    const putLabel = await page.textContent('.ejp-row:first-child .cx-chip:nth-child(2)');
    await page.click('.ejp-more');
    await page.waitForFunction(() => document.querySelectorAll('.ejp-row').length === 3);
    await page.click('.pp-x');
    await page.waitForFunction(() => !document.querySelector('.ejp'));
    await page.waitForFunction(() => [...document.querySelectorAll('.msg.assistant')].some((m) => m.textContent.includes('결정문을 이 대화에 실었습니다')));
    return { rows, decision, putLabel, jobsCalls: await calls(page, '/agent/engine-delib/jobs?'),
             created: (await calls(page, '/agent/conversations')).filter((c) => c.method === 'POST' && c.url === '/agent/conversations').length,
             appended: (await calls(page, '/agent/conversations/srv-new/messages')).map((c) => c.body) };
  },
};

(async () => {
  let browser;
  try { browser = await chromium.launch(); } catch (e) { process.stdout.write(JSON.stringify({ skip: String(e).slice(0, 300) })); return; }
  const out = {};
  try {
    for (const [name, run] of Object.entries(SCENARIOS)) {
      const kind = name === 'confirm' || name === 'jobcard' ? 'chat' : 'deliberation';
      const page = await open(browser, kind, JSON.parse(JSON.stringify(DATA.srv)));
      try { out[name] = { ...(await run(page)), errors: page.__errors }; }
      catch (e) { out[name] = { failed: String((e && e.stack) || e).slice(0, 1500), errors: page.__errors }; }
      await page.close();
    }
  } finally { await browser.close(); }
  process.stdout.write(JSON.stringify(out));
})().catch((e) => { process.stderr.write(String((e && e.stack) || e)); process.exit(1); });
"""

ROOT_JOB = "diagnosis-20261128-040000-abc123"
NEXT_JOB = "diagnosis-20261128-090000-fff000"
CID = "cf-7f3a9c2e41d0"


def _frame(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _data(tmp_path) -> dict:
    """서버 사본은 엔진 _conv_item → 포털 messages_of → 대화 저장소 그대로. 이어하기 뒤 판은 같은 뿌리 대화에 다음 잡이 붙은 것."""
    conv_item, ledger = _engine_conv()
    root = _job(ROOT_JOB, q="힌지 크랙 원인 — 엔진 심의", report_id=7, report_url="/w/a/reports/7")
    ledger[root["id"]] = root
    store = ConversationStore(Settings(_env_file=None, conv_store_path=str(tmp_path / "conv.sqlite")))
    store.ingest_mcp_delib(owner_sub="me@example.com", job_id=ROOT_JOB, root_job_id=ROOT_JOB, title=M._title(root["question"]),
                           messages=M.messages_of(conv_item(root)), finished_at=root["finished_at"])
    (meta,) = store.list_for_owner("me@example.com")
    before = store.get(meta["id"], "me@example.com")
    nxt = _job(NEXT_JOB, q=root["question"], continues=ROOT_JOB, decision="결론 — 낙하 우선으로 리브 1.4 mm", fin=1_800_000_000.0)
    store.append(conversation_id=meta["id"], owner_sub="me@example.com", role="assistant", content="엔진에 이어하기를 맡겼습니다",
                 meta={"job_cards": [M.card_of({"job_id": NEXT_JOB, "status": "queued"}, tool="deliberate_continue", continued_from=ROOT_JOB)]})
    store.ingest_mcp_delib(owner_sub="me@example.com", job_id=NEXT_JOB, root_job_id=ROOT_JOB, title="t",
                           messages=M.messages_of(conv_item(nxt)), finished_at=nxt["finished_at"])
    after = store.get(meta["id"], "me@example.com")
    web = {"id": "c-web", "title": "웹 심의 하나", "kind": "deliberation", "source": "web", "created_at": 1_700_000_100, "updated_at": 1_700_000_100}
    late = {"id": "c-late", "title": "Claude 가 방금 저장한 심의", "kind": "deliberation", "source": "mcp",
            "created_at": 1_900_000_000, "updated_at": 1_900_000_000}
    summary = {"call": "deliberate_start", "job": "diagnosis", "rounds": 0, "seats": ["기구 설계", "재료"], "seats_n": 2, "save_report": True,
               "evidence_n": 3, "evidence_chars": 12_345, "apps": ["step_forge"], "editable": ["save_report", "job", "rounds"]}
    card = {"id": CID, "expires_at": 4_102_444_800_000,
            "calls": [{"tool": "deliberate_start", "app": "hwax-deliberation", "kind": "job", "args_text": "question=힌지 · job=diagnosis",
                       "summary": summary, "again": False}],
            "approve_text": f"실행 — 확인 번호 {CID}", "decline_text": f"취소 — 확인 번호 {CID} 는 실행하지 않음"}
    text = f"심의를 열려 했습니다.\n\n---\n**확인이 필요합니다**\n1. `deliberate_start`\n(확인 번호 `{CID}` · 30분)"
    job_card = {"call": "c1", "tool": "deliberate_start", "app": "hwax-deliberation", "kind": "deliberation", "job_ids": [NEXT_JOB],
                "phase": "run", "state": "queued", "progress": None, "detail": "",
                "status_call": {"tool": "deliberate_status", "args": {"job_id": NEXT_JOB}}}
    done = {"job_id": NEXT_JOB, "status": "done", "phase": "end", "round": 3, "total_rounds": 3, "report_id": 7, "conversation_id": meta["id"]}
    rows = [{"job_id": ROOT_JOB, "job": "diagnosis", "label": "원인 규명", "status": "done", "question": root["question"], "question_chars": 14,
             "mine": True, "owner": "me@example.com", "created": "2026-11-28T04:00:00", "report_id": 7, "conversation_id": meta["id"]},
            {"job_id": "default-20261120-100000-aaaaaa", "job": "default", "label": "자유 심의", "status": "error", "question": "옛 심의",
             "question_chars": 5, "mine": True, "owner": "me@example.com", "created": "2026-11-20T10:00:00", "conversation_id": None}]
    srv = {"list": [web, meta], "convs": {meta["id"]: before}, "status": [{"job_id": NEXT_JOB, "status": "running", "phase": "run", "round": 1,
                                                                             "total_rounds": 3}, done],
           "cont": {"job_id": NEXT_JOB, "status": "queued", "saved": True, "text": "엔진에 이어하기를 맡겼습니다 — 잡 `" + NEXT_JOB + "`",
                    "card": M.card_of({"job_id": NEXT_JOB, "status": "queued"}, tool="deliberate_continue", continued_from=ROOT_JOB)},
           "jobs": {"jobs": rows, "more": True, "next_until": "2026-11-20T10:00:00"},
           "jobsMore": {"jobs": [{**rows[1], "job_id": "default-20261101-090000-bbbbbb", "question": "보름 전 심의", "created": "2026-11-01T09:00:00"}],
                        "more": False, "next_until": None},
           "decision": {"job_id": ROOT_JOB, "status": "done", "job": "diagnosis", "label": "원인 규명", "question": root["question"],
                        "decision": "## 결론\n리브를 1.2 mm 로 보강한다", "report_id": 7, "conversation_id": meta["id"]}}
    return {"srv": srv, "mcpMeta": meta, "mcpConvAfter": after, "lateMeta": late,
            "confirmTurn": _frame("confirm", card) + _frame("token", {"delta": text}) + _frame("result", {"type": "text", "content": text})
            + _frame("done", {}),
            "jobTurn": _frame("token", {"delta": "심의를 맡겼습니다"}) + _frame("job_card", job_card)
            + _frame("result", {"type": "text", "content": "심의를 맡겼습니다"}) + _frame("done", {}),
            "done": done}


@pytest.fixture(scope="module")
def seen(tmp_path_factory):
    out = tmp_path_factory.mktemp("mcpdelib")
    shots = os.environ.get("HWAX_SHOTS", "")
    data = _data(out)
    (out / "data.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    (out / "harness.tsx").write_text(_HARNESS.replace("__FE__", str(FE)), encoding="utf-8")
    for name, body in (("build.cjs", _BUILD), ("stub.js", _STUB), ("drive.cjs", _DRIVE)):
        (out / name).write_text(body, encoding="utf-8")
    r = subprocess.run(["node", "build.cjs", str(FE), str(out)], cwd=str(out), capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, "화면을 묶지 못했다:\n" + r.stdout + r.stderr
    r = subprocess.run(["node", "drive.cjs", str(FE), str(out), shots], cwd=str(out), capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
    got = json.loads(r.stdout)
    if "skip" in got:
        pytest.skip("헤드리스 브라우저를 띄우지 못했다(playwright 브라우저 미설치) — " + got["skip"])

    def scenario(name: str) -> dict:
        if name == "data":
            return data
        assert "failed" not in got[name], f"시나리오 {name} 이 끝까지 돌지 못했다:\n{got[name].get('failed')}\n{got[name].get('errors')}"
        assert not got[name].get("errors"), f"화면이 예외를 던졌다: {got[name]['errors']}"
        return got[name]
    return scenario


def test_사이드바는_MCP_표지와_거르기를_그리고_창_포커스에_새_대화를_세운다(seen):
    s, d = seen("sidebar"), seen("data")
    mcp_title = d["mcpMeta"]["title"]
    assert any(t.startswith("MCP") and mcp_title in t for t in s["before"]) and "웹 심의 하나" in s["before"]
    assert s["btns"] == ["전부", "웹", "MCP 1"]
    assert len(s["onlyMcp"]) == 1 and mcp_title in s["onlyMcp"][0] and s["onlyWeb"] == ["웹 심의 하나"]
    assert any("Claude 가 방금 저장한 심의" in t for t in s["after"]), "새로 고침 없이(창 포커스) 새 MCP 대화가 섰다"


def test_들인_MCP_심의의_이어가기는_엔진으로_가고_진행_카드가_끝나면_결과가_붙는다(seen):
    s = seen("continue")
    assert ROOT_JOB in s["line"] and "엔진이 같은 잡 계보로" in s["head"]
    (c,) = s["cont"]
    assert c["method"] == "POST" and c["body"]["previous_job_id"] == ROOT_JOB and c["body"]["human_note"] == "낙하 성능을 최우선으로"
    assert c["body"]["rounds"] == 4 and "keep_seats" not in c["body"], "같은 좌석(기본)은 싣지 않는다"
    assert s["chats"] == 0, "새 웹 심의를 열지 않았다(/agent/chat 을 부르지 않는다)"
    assert "줄 서는 중" in s["firstState"] or "도는 중" in s["firstState"]
    assert s["status"] >= 2 and "이 대화에 좌석 발언과 결정문이 붙었습니다" in s["endLinks"] and "보고서 #7" in s["endLinks"]
    assert s["decisions"] >= 2, "끝난 뒤 서버 사본을 다시 읽어 이어진 회차의 결정문이 붙었다"
    assert s["lists"] >= 2, "끝나면 목록을 다시 읽었다"


def test_확인_카드는_요약을_보이고_바꾼_칸만_confirm_edit_로_싣는다(seen):
    s = seen("confirm")
    assert "심의 시작" in s["sum"] and "근거 3건 · 12,345자" in s["sum"] and "step_forge" in s["sum"] and "좌석 2석" in s["sum"]
    assert s["label0"] == "실행" and s["label1"] == "바꾼 대로 실행"
    assert s["sent"]["message"] == f"실행 — 확인 번호 {CID}" and "routine" not in s["sent"]
    assert s["sent"]["confirm_edit"] == {"id": CID, "set": {"save_report": False, "job": "option-select", "rounds": 5}}


def test_진행_카드는_다시_물어_끝나면_보고서와_심의_페이지로_간다(seen):
    s, d = seen("jobcard"), seen("data")
    assert "도는 중" in s["running"] and "라운드 1/3" in s["running"]
    assert NEXT_JOB in s["text"] and "끝남" in s["text"] and "보고서 #7" in s["text"] and "라운드 3/3" in s["text"]
    assert s["status"][0]["url"] == f"/agent/engine-delib/status/{NEXT_JOB}"
    assert s["nav"] == {"openConversation": {"id": d["mcpMeta"]["id"], "title": f"심의 {NEXT_JOB}"}}


def test_엔진_잡_찾기는_결정문을_보이고_대화에_싣고_더_본다(seen):
    s = seen("jobs")
    assert s["rows"] == 2 and "리브를 1.2 mm 로 보강한다" in s["decision"] and s["putLabel"] == "실었습니다"
    first, more = s["jobsCalls"][0]["url"], s["jobsCalls"][1]["url"]
    assert "query=%ED%9E%8C%EC%A7%80" in first and "since=2026-11-01" in first and "scope=mine" in first
    assert "until=2026-11-20T10%3A00%3A00" in more and "since=2026-11-01" in more
    assert s["created"] == 1, "대화가 없으면 새로 만든다"
    (note,) = [b for b in s["appended"] if b["role"] == "assistant"]
    assert note["meta"]["upload"] is True and note["meta"]["activity"][0]["result_full"] == "## 결론\n리브를 1.2 mm 로 보강한다", note
