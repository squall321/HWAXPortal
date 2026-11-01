# 실행 화면의 '재개' 단추를 헤드리스 브라우저에서 실제 ProceduresPage 로 두 번 눌러, 재개 요청이 한 번만 나가는지 본다(W-110)
"""왜 — 재개 단추는 누르는 동안 막히지 않았다(확인 · 고르기 카드는 막는다). 두 번 누르면 재개 요청이 둘 나가고, 서버는 둘 다 실행기를
띄웠다 — 같은 실행에 실행기가 둘 돌며 바깥 쓰기가 두 번 나갔다. 서버는 이제 둘째를 409 로 막지만(실행을 잡는 쓰기 — routes `_take`), 화면도
누르는 동안 단추를 막는다. 응답을 붙잡아 둔 채 실제 사용자처럼 두 번 눌러(dblclick) 나간 요청을 센다.
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
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { AuthContext } from '__FE__/src/auth/AuthContext';
import { ProceduresProvider } from '__FE__/src/state/ProceduresContext';
import ProceduresPage from '__FE__/src/pages/procedures/ProceduresPage';

(window as unknown as { __mount: () => void }).__mount = () => {
  const user = { subject: 'u1@corp.example', email: 'u1@corp.example', display_name: 'U', groups: [] };
  createRoot(document.getElementById('root')!).render(
    <AuthContext.Provider
      value={{ user, status: 'authenticated', login: () => undefined, logout: async () => undefined, refresh: async () => undefined }}
    >
      <MemoryRouter initialEntries={['/procedures/runs/r1']}>
        <Routes>
          <Route path="/procedures/*" element={<ProceduresProvider><ProceduresPage /></ProceduresProvider>} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
};
"""

# 가짜 백엔드 — 멈춘(failed) 실행 하나. 재개 요청은 __release() 까지 답하지 않는다(그동안 단추가 막혀 있어야 한다).
_STUB = r"""
(() => {
  window.__calls = [];
  const json = (body, status = 200) =>
    new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
  const RUN = { id: 'r1', state: 'failed', stage: 'step:0', mode: 'live', origin: 'replay', title: '재개 시험',
    procedure_version_id: 'v1', procedure_id: 'p1', version_no: 1, inputs: {}, started_at: 1, ended_at: 2,
    steps: [{ ix: 0, backend: 'ra', tool: 'submit_job', expect: 'fast', args: { x: 1 }, args_sha256: 'fp', state: 'failed',
      ok: 0, error: '잠깐 불통', stage: 'tool_error', duration_ms: 10, result_bytes: null, truncated: 0, notes: null }] };
  let release;
  const held = new Promise((r) => { release = r; });
  window.__release = () => release();
  window.fetch = (url, init = {}) => {
    const u = String(url);
    const method = (init.method || 'GET').toUpperCase();
    window.__calls.push({ url: u, method });
    if (u === '/procedures-api/runs/r1' && method === 'GET') return Promise.resolve(json(RUN));
    if (u === '/procedures-api/runs/r1/resume' && method === 'POST') return held.then(() => json({ resumed_at: 0 }));
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
  try {
    const page = await browser.newPage();
    page.setDefaultTimeout(10000);
    page.on('pageerror', (e) => out.errors.push(String(e)));
    await page.route('http://harness.invalid/**', (rt) =>
      rt.fulfill({ contentType: 'text/html', body: '<!doctype html><html><body><div id="root"></div></body></html>' }));
    await page.goto('http://harness.invalid/');
    await page.addScriptTag({ path: path.join(OUT, 'stub.js') });
    await page.addScriptTag({ path: path.join(OUT, 'bundle.js') });
    await page.evaluate(() => window.__mount());
    const btn = page.getByRole('button', { name: '재개', exact: true });
    try {
      await btn.waitFor();
      await btn.dblclick();                                  // 사람이 두 번 누른다 — 응답은 아직 붙잡혀 있다
      await page.waitForTimeout(200);
      out.disabledWhilePending = await btn.isDisabled();
      out.resumeWhilePending = (await page.evaluate(() => window.__calls)).filter(
        (c) => c.method === 'POST' && c.url.endsWith('/resume')).length;
      await page.evaluate(() => window.__release());
      await page.waitForFunction(() => window.__calls.filter((c) => c.method === 'GET').length >= 2);   // 재개 뒤 실행을 다시 읽었다
      await page.waitForTimeout(100);
      out.disabledAfter = await btn.isDisabled();
      out.resumeTotal = (await page.evaluate(() => window.__calls)).filter(
        (c) => c.method === 'POST' && c.url.endsWith('/resume')).length;
    } catch (e) { out.failed = String((e && e.stack) || e).slice(0, 1500); }
  } finally { await browser.close(); }
  process.stdout.write(JSON.stringify(out));
})().catch((e) => { process.stderr.write(String((e && e.stack) || e)); process.exit(1); });
"""


@pytest.fixture(scope="module")
def seen(tmp_path_factory):
    out = tmp_path_factory.mktemp("resumebutton")
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
    assert not got["errors"], f"화면이 예외를 던졌다: {got['errors']}"
    return got


def test_재개를_두_번_눌러도_재개_요청은_한_번이다(seen):
    assert seen["resumeWhilePending"] == 1, f"재개 요청이 {seen['resumeWhilePending']}번 나갔다"
    assert seen["disabledWhilePending"] is True, "응답을 기다리는 동안 단추가 열려 있다"
    assert seen["resumeTotal"] == 1


def test_응답이_오면_단추가_다시_열린다(seen):
    assert seen["disabledAfter"] is False, "재개가 끝난 뒤에도 단추가 막혀 있다"
