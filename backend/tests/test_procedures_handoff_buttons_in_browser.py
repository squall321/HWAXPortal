# 실행 화면의 '심의로 넘기기' · '챗으로 가져가기' 를 헤드리스 브라우저에서 실제 ProceduresPage 로 눌러, 나가는 요청과 넘어간 주소 상태를 본다(W-114 · W-115)
"""화면이 넘기는 것은 실행 id 와 보이기용 수뿐이어야 한다 — 단계 결과를 읽어 근거를 짓지 않는다(근거는 심의를 열 때 포털이 원장에서 짓는다).
절차 화면은 챗 컨텍스트 없이 뜬다(PLAN §3 의 페이지 스코프) — 이 뼈대에는 ChatProvider 가 없다. 챗으로 가져간 대화는 챗 화면이 주소 상태로 받는다.
"""
import json
import subprocess

import pytest
from tests.test_delib_stream_in_browser import (  # noqa: F401 — 같은 도구가 없으면 같이 건너뛴다
    _BUILD,
    FE,
    pytestmark,
)

_HARNESS = r"""
import { createRoot } from 'react-dom/client';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { AuthContext } from '__FE__/src/auth/AuthContext';
import { ProceduresProvider } from '__FE__/src/state/ProceduresContext';
import ProceduresPage from '__FE__/src/pages/procedures/ProceduresPage';

// 넘어간 자리 — 주소와 주소 상태를 그대로 적는다(심의 화면 · 챗 화면이 읽는 것)
function Landed() {
  const loc = useLocation();
  return <pre id="landed">{JSON.stringify({ path: loc.pathname, state: loc.state })}</pre>;
}

(window as unknown as { __mount: (ents: string[]) => void }).__mount = (ents) => {
  const user = { subject: 'u1@corp.example', email: 'u1@corp.example', display_name: 'U', groups: [], entitlements: ents };
  createRoot(document.getElementById('root')!).render(
    <AuthContext.Provider
      value={{ user, status: 'authenticated', login: () => undefined, logout: async () => undefined, refresh: async () => undefined }}
    >
      <MemoryRouter initialEntries={['/procedures/runs/r1']}>
        <Routes>
          <Route path="/procedures/*" element={<ProceduresProvider><ProceduresPage /></ProceduresProvider>} />
          <Route path="/deliberate" element={<Landed />} />
          <Route path="/" element={<Landed />} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
};
"""

# 가짜 백엔드 — 끝난(done) live 실행 하나. 단계 하나는 성공, 하나는 실행 여부 모름, 하나는 확인 카드에서 멈춘 채(부르지 않았다).
_STUB = r"""
(() => {
  window.__calls = [];
  const json = (body, status = 200) =>
    new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
  const step = (ix, tool, state, extra = {}) => ({ ix, backend: 'ra', tool, expect: 'fast', args: { x: ix }, args_sha256: 'fp' + ix, state,
    ok: state === 'done' ? 1 : 0, error: null, stage: null, duration_ms: 10, result_bytes: state === 'done' ? 20 : null, truncated: 0,
    notes: null, ...extra });
  const RUN = { id: 'r1', state: window.__runState || 'done', stage: null, mode: window.__runMode || 'live', origin: 'replay',
    title: '열충격 SED 판정', procedure_version_id: window.__empty ? null : 'v1', procedure_id: window.__empty ? null : 'p1',
    version_no: window.__empty ? null : 1, inputs: {}, started_at: 1, ended_at: 2,
    steps: [step(0, 'find_reports', 'done'), step(1, 'predict_sed', 'unknown', { stage: 'timeout', error: '응답 없음' }),
            step(2, 'add_report_tags', 'pending', { stage: 'gate' })] };
  const HANDOFF = { run_id: '0123456789abcdef0123456789abcdef', title: '열충격 SED 판정', state: 'done', mode: 'live',
    evidence_count: 2, called: 2, dropped: 0,
    items: [{ ix: 0, tool: 'find_reports', state: 'done', chars: 20 }, { ix: 1, tool: 'predict_sed', state: 'unknown', chars: 30 }],
    not_called: [{ ix: 2, tool: 'add_report_tags', state: 'pending', stage: 'gate' }],
    limits: { items: 40, result_chars: 150000, args_chars: 1200 } };
  window.fetch = (url, init = {}) => {
    const u = String(url);
    const method = (init.method || 'GET').toUpperCase();
    window.__calls.push({ url: u, method });
    if (u === '/procedures-api/runs/r1' && method === 'GET') return Promise.resolve(json(RUN));
    if (u === '/procedures-api/runs/r1/handoff' && method === 'GET') return Promise.resolve(json(HANDOFF));
    if (u === '/procedures-api/runs/r1/chat' && method === 'POST')
      return Promise.resolve(json({ conversation_id: 'c0ffee', title: '절차 실행 — 열충격 SED 판정' }, 201));
    return Promise.resolve(json({ detail: 'stub: no route ' + u }, 404));
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
  // 화면을 새로 올린다 — pre 는 스텁보다 먼저 도는 설정(실행 상태 · 모드), ents 는 그 사람의 권한
  const open = async (ents, pre) => {
    const page = await browser.newPage();
    page.setDefaultTimeout(10000);
    page.on('pageerror', (e) => out.errors.push(String(e)));
    await page.route('http://harness.invalid/**', (rt) =>
      rt.fulfill({ contentType: 'text/html', body: '<!doctype html><html><body><div id="root"></div></body></html>' }));
    await page.goto('http://harness.invalid/');
    if (pre) await page.evaluate(pre);
    await page.addScriptTag({ path: path.join(OUT, 'stub.js') });
    await page.addScriptTag({ path: path.join(OUT, 'bundle.js') });
    await page.evaluate((e) => window.__mount(e), ents);
    await page.getByText('열충격 SED 판정').first().waitFor();
    return page;
  };
  const landed = async (page) => JSON.parse(await page.locator('#landed').innerText());
  const calls = async (page) => (await page.evaluate(() => window.__calls)).map((c) => c.method + ' ' + c.url);
  try {
    let page = await open(['feat:procedures', 'feat:deliberation']);
    await page.getByRole('button', { name: '심의로 넘기기', exact: true }).click();
    out.delib = await landed(page);
    out.delibCalls = await calls(page);

    page = await open(['feat:procedures', 'feat:deliberation']);
    await page.getByRole('button', { name: '챗으로 가져가기', exact: true }).click();
    out.chat = await landed(page);
    out.chatCalls = await calls(page);

    page = await open(['feat:procedures']);                       // 심의 권한이 없다
    out.noDelib = { delib: await page.getByRole('button', { name: '심의로 넘기기', exact: true }).count(),
                    chat: await page.getByRole('button', { name: '챗으로 가져가기', exact: true }).count() };

    page = await open(['feat:procedures', 'feat:deliberation'], () => { window.__runMode = 'plan'; });
    out.plan = { delib: await page.getByRole('button', { name: '심의로 넘기기', exact: true }).count(),
                 chat: await page.getByRole('button', { name: '챗으로 가져가기', exact: true }).count() };

    page = await open(['feat:procedures', 'feat:deliberation'], () => { window.__runState = 'running'; });
    out.running = { delib: await page.getByRole('button', { name: '심의로 넘기기', exact: true }).count(),
                    chat: await page.getByRole('button', { name: '챗으로 가져가기', exact: true }).count() };

    // 절차 실행의 queued 는 실행기를 기다리는 중(도는 실행) · 한 단계씩 돌린 실행(판본 없음)의 queued 는 단계 사이에 쉬는 중이다
    page = await open(['feat:procedures', 'feat:deliberation'], () => { window.__runState = 'queued'; });
    out.queued = { delib: await page.getByRole('button', { name: '심의로 넘기기', exact: true }).count(),
                   chat: await page.getByRole('button', { name: '챗으로 가져가기', exact: true }).count() };
    page = await open(['feat:procedures', 'feat:deliberation'], () => { window.__runState = 'queued'; window.__empty = true; });
    out.emptyResting = { delib: await page.getByRole('button', { name: '심의로 넘기기', exact: true }).count(),
                         chat: await page.getByRole('button', { name: '챗으로 가져가기', exact: true }).count() };
    page = await open(['feat:procedures', 'feat:deliberation'], () => { window.__runState = 'running'; window.__empty = true; });
    out.emptyRunning = { delib: await page.getByRole('button', { name: '심의로 넘기기', exact: true }).count(),
                         chat: await page.getByRole('button', { name: '챗으로 가져가기', exact: true }).count() };
  } catch (e) { out.failed = String((e && e.stack) || e).slice(0, 1500); }
  finally { await browser.close(); }
  process.stdout.write(JSON.stringify(out));
})().catch((e) => { process.stderr.write(String((e && e.stack) || e)); process.exit(1); });
"""


@pytest.fixture(scope="module")
def seen(tmp_path_factory):
    out = tmp_path_factory.mktemp("handoffbuttons")
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
    assert "failed" not in got, f"끝까지 돌지 못했다:\n{got.get('failed')}"
    assert not got["errors"], f"화면이 예외를 던졌다(챗 컨텍스트 없이 떠야 한다): {got['errors']}"
    return got


def test_심의로_넘기기는_실행_id_와_수만_들고_심의_화면으로_간다(seen):
    d = seen["delib"]
    assert d["path"] == "/deliberate"
    assert d["state"] == {"procedureRun": {"run_id": "0123456789abcdef0123456789abcdef", "title": "열충격 SED 판정", "count": 2,
                                           "dropped": 0, "failed": 0, "unknown": 1, "not_called": 1}}
    asked = [c for c in seen["delibCalls"] if "/handoff" in c]
    assert asked == ["GET /procedures-api/runs/r1/handoff"], seen["delibCalls"]
    assert not [c for c in seen["delibCalls"] if "/result" in c], "화면이 단계 결과를 읽어 근거를 짓는다"


def test_챗으로_가져가기는_대화를_만들고_그_id_를_챗_화면에_넘긴다(seen):
    assert seen["chat"] == {"path": "/", "state": {"openConversation": {"id": "c0ffee", "title": "절차 실행 — 열충격 SED 판정"}}}
    assert [c for c in seen["chatCalls"] if c.startswith("POST")] == ["POST /procedures-api/runs/r1/chat"], seen["chatCalls"]


def test_넘기기_단추는_넘길_수_있는_실행에만_보인다(seen):
    assert seen["noDelib"] == {"delib": 0, "chat": 1}, "심의 권한이 없으면 심의로 넘기기를 권하지 않는다"
    assert seen["plan"] == {"delib": 0, "chat": 0}, "계획 모드 실행은 부른 단계가 없다"
    assert seen["running"] == {"delib": 0, "chat": 0}, "도는 실행은 넘기지 않는다"
    assert seen["queued"] == {"delib": 0, "chat": 0}, "실행기를 기다리는 절차 실행도 도는 실행이다"


def test_단계_사이에_쉬는_빈_실행에는_넘기기_단추가_보인다(seen):
    """한 단계씩 돌린 실행은 단계가 끝나면 queued 로 쉰다 — 도는 실행으로 읽으면 성공해도 단추가 영영 안 뜬다(반대 검토 M2)."""
    assert seen["emptyResting"] == {"delib": 1, "chat": 1}
    assert seen["emptyRunning"] == {"delib": 0, "chat": 0}, "단계가 도는 동안은 빈 실행도 넘기지 않는다"
