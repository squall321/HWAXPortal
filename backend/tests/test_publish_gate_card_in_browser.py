# 게시 단계의 게이트 카드(남은 일 B3)를 헤드리스 브라우저에서 실제 RunSteps 로 그린다 — 미리보기 · 막힌 사유 · 바뀐 것 · 확인이 보내는 지문
"""왜 — 실행기는 게시(publish_report) 앞에서 Report Archive 미리보기를 받아 단계 노트에 싣는다(runner `_publish_gate`). 화면이
그것을 그리지 않으면 사람은 인자 JSON 만 보고 승인한다 — 어디에 몇 명에게 보이게 되는지 모른 채다. 그래서 카드가 지킬 것이 셋이다.

  · 대상마다 이름 · 볼 사람 수 · 하위 게시판 · 이미 게시됨 · 못 올리는 사유를 보인다. 막힌 곳이 있으면 이대로는 안 올라간다고 말한다.
  · 승인 뒤 미리보기가 바뀌어 다시 멈췄으면 바뀐 줄을 보인다.
  · '확인하고 계속' 은 그 행의 지문(args_sha256)만 보낸다 — 지문이 사람이 본 미리보기에 묶여 있다.

미리보기가 없는 게이트(게시가 아닌 단계)는 종전 카드 그대로다.
"""
import json
import subprocess

import pytest

from tests.test_delib_stream_in_browser import _BUILD, FE, pytestmark  # noqa: F401 — 같은 도구가 없으면 같이 건너뛴다

_HARNESS = r"""
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { RunSteps } from '__FE__/src/pages/procedures/RunSteps';

(window as unknown as { __mount: (run: unknown) => void }).__mount = (run) => {
  createRoot(document.getElementById('root')!).render(
    <MemoryRouter>
      <RunSteps run={run as never} onChanged={() => { (window as unknown as { __changed: number }).__changed += 1; }} />
    </MemoryRouter>,
  );
};
"""

# 가짜 백엔드 — 확인(ack)만 받는다. 보낸 본문을 __calls 에 남긴다.
_STUB = r"""
(() => {
  window.__calls = [];
  window.__changed = 0;
  window.fetch = (url, init = {}) => {
    const u = String(url);
    window.__calls.push({ url: u, method: (init.method || 'GET').toUpperCase(), body: init.body ? JSON.parse(init.body) : null });
    const ok = /^\/procedures-api\/runs\/[^/]+\/steps\/\d+\/ack$/.test(u);
    return Promise.resolve(new Response(JSON.stringify(ok ? { acked: true, resumed: true } : { detail: 'stub: no route ' + u }),
      { status: ok ? 200 : 404, headers: { 'Content-Type': 'application/json' } }));
  };
})();
"""

_DRIVE = r"""
const { createRequire } = require('module');
const path = require('path');
const [FE, OUT] = process.argv.slice(2);
const { chromium } = createRequire(path.join(FE, 'package.json'))('@playwright/test');

// 실행기가 남기는 꼴 그대로(runner `_publish_gate` — 노트의 publish_preview · publish_blocked · publish_changed)
const PREVIEW = {
  report_id: 41, title: '낙하 해석 보고서',
  targets: [
    { slug: 'dept-a', name: '가 부서', parent_slug: 'div-x', audience: 12, descendant_boards: 0, already_mounted: false, blocked: null },
    { slug: 'dept-b', name: '나 부서', parent_slug: 'div-x', audience: 30, descendant_boards: 2, already_mounted: false,
      blocked: '이 게시판에 게시할 권한이 없습니다.' },
  ],
  // RA MCP 가 태그 없는 보고서의 미리보기에 덧붙이는 경고(mcp_server preview_publish)
  warnings: ['기준정보 태그가 비어 있다. 게시 전에 `suggest_report_tags(41)` → `add_report_tags(...)` 로 모델·과제 등을 붙여라'],
};
const step = (tool, notes) => ({
  ix: 0, backend: 'reportarchive', tool, expect: 'fast', args: { report_id: 41, boards: ['dept-a', 'dept-b'], note: '절차가 올린다' },
  args_sha256: 'fp-' + tool, state: 'pending', ok: 0, error: null, stage: 'gate', duration_ms: null, result_bytes: null,
  truncated: 0, notes,
});
const run = (st) => ({ id: 'r1', state: 'gated', stage: 'step:0', mode: 'live', origin: 'manual', title: '게시',
  procedure_version_id: 'v1', inputs: { report_id: 41 }, steps: [st], started_at: 1, ended_at: null });

const SCENARIOS = {
  blocked: run(step('publish_report', { publish_preview: PREVIEW, publish_blocked: ['dept-b: 이 게시판에 게시할 권한이 없습니다.'] })),
  changed: run(step('publish_report', {
    publish_preview: { ...PREVIEW, targets: [{ ...PREVIEW.targets[0] }, { ...PREVIEW.targets[1], audience: 340, blocked: null }] },
    publish_changed: ['dept-b 볼 수 있는 사람: 30 → 340', 'dept-b 못 올리는 사유: 이 게시판에 게시할 권한이 없습니다. → 없음'] })),
  plain: run({ ...step('trash_report', null), args: { report_id: 41 } }),
};

(async () => {
  let browser;
  try { browser = await chromium.launch(); } catch (e) { process.stdout.write(JSON.stringify({ skip: String(e).slice(0, 300) })); return; }
  const out = {};
  try {
    for (const [name, r] of Object.entries(SCENARIOS)) {
      const page = await browser.newPage();
      page.setDefaultTimeout(10000);
      const errors = [];
      page.on('pageerror', (e) => errors.push(String(e)));
      await page.route('http://harness.invalid/**', (rt) =>
        rt.fulfill({ contentType: 'text/html', body: '<!doctype html><html><body><div id="root"></div></body></html>' }));
      await page.goto('http://harness.invalid/');
      await page.addScriptTag({ path: path.join(OUT, 'stub.js') });
      await page.addScriptTag({ path: path.join(OUT, 'bundle.js') });
      await page.evaluate((x) => window.__mount(x), r);
      try {
        await page.waitForSelector('.pr-callout');
        const card = await page.$eval('.pr-callout', (el) => el.innerText);
        const items = await page.$$eval('.pr-callout li', (els) => els.map((e) => e.innerText));
        await page.click('.pr-callout .btn-primary');
        await page.waitForFunction(() => window.__changed === 1);
        const calls = await page.evaluate(() => window.__calls);
        out[name] = { card, items, calls, errors };
      } catch (e) { out[name] = { failed: String((e && e.stack) || e).slice(0, 1500), errors }; }
      await page.close();
    }
  } finally { await browser.close(); }
  process.stdout.write(JSON.stringify(out));
})().catch((e) => { process.stderr.write(String((e && e.stack) || e)); process.exit(1); });
"""


@pytest.fixture(scope="module")
def seen(tmp_path_factory):
    out = tmp_path_factory.mktemp("publishgate")
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


def test_게이트_카드에_대상_볼_사람_수_못_올리는_사유를_보인다(seen):
    s = seen("blocked")
    assert "게시할 보고서 낙하 해석 보고서 #41" in s["card"], s["card"]
    assert s["items"][:2] == ["가 부서 dept-a — 12명이 봅니다",
                              "나 부서 dept-b — 30명이 봅니다 · 하위 게시판 2개 · 못 올림: 이 게시판에 게시할 권한이 없습니다."], s["items"]
    assert "이대로는 게시되지 않습니다" in s["card"]
    assert "바뀌어 게시하지 않았습니다" not in s["card"]
    assert any(i.startswith("기준정보 태그가 비어 있다.") for i in s["items"]), s["items"]   # 지문에 든 경고도 보인다


def test_확인은_그_행의_지문만_보낸다(seen):
    s = seen("blocked")
    assert s["calls"] == [{"url": "/procedures-api/runs/r1/steps/0/ack", "method": "POST",
                           "body": {"args_sha256": "fp-publish_report"}}], s["calls"]


def test_승인_뒤_바뀐_미리보기는_바뀐_줄을_보인다(seen):
    s = seen("changed")
    assert "확인한 뒤 미리보기가 바뀌어 게시하지 않았습니다" in s["card"], s["card"]
    assert s["items"][:2] == ["dept-b 볼 수 있는 사람: 30 → 340",
                              "dept-b 못 올리는 사유: 이 게시판에 게시할 권한이 없습니다. → 없음"], s["items"]
    assert "340명이 봅니다" in s["card"] and "이대로는 게시되지 않습니다" not in s["card"]


def test_미리보기가_없는_게이트는_종전_카드다(seen):
    s = seen("plain")
    assert "게시할 보고서" not in s["card"] and "명이 봅니다" not in s["card"], s["card"]
    assert "치환이 끝난 실제 인자" in s["card"]
    assert s["calls"][0]["body"] == {"args_sha256": "fp-trash_report"}
