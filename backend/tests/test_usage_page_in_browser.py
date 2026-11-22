# 이용 통계 화면(/admin/usage)을 헤드리스 브라우저에 실제로 올려 본다 — 백엔드가 낸 한 판을 가짜 fetch 로 주고 화면이 터지지 않는지, 접어 둔 표의 카드가 M1 카드와 함께 서는지(docs/ops-dashboard M2)
"""왜 — 화면 파일(UsageStatsPage)은 로그인 상태 · 라우터 · fetch 가 있어야 떠서 node 단위 시험(test_usage_fold_screen — 카드만 따로 그린다)으로는 못 돌린다.
칸 하나의 꼴이 어긋나 화면 전체가 흰 화면이 되는 것은 타입 검사가 모른다. test_admin_pages_in_browser 와 같은 길이다 — 실제 페이지를 esbuild 로 한 파일로
묶어 빈 문서에 올리고 fetch 만 바꾼다. 주는 답은 접기 시험의 장면을 백엔드가 실제로 지은 한 판이다(서버 · 네트워크 없음).

도구는 프론트가 이미 가진 것만 쓴다(esbuild · @playwright/test · 그 브라우저) — 없으면 건너뛴다. HWAX_USAGE_SHOT 에 폴더를 주면 그린 화면을 PNG 로 남긴다
(눈으로 볼 때만 — 판정에는 쓰지 않는다).
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from tests.test_usage_fold import NOW, _at, _box
from tests.test_usage_fold_sections import D19, A, B, C, scene  # noqa: F401 — 장면 고정물

ROOT = Path(__file__).resolve().parents[2]
FE = ROOT / "frontend"

pytestmark = pytest.mark.skipif(
    not shutil.which("node") or not (FE / "node_modules/@playwright/test").exists() or not (FE / "node_modules/vite").exists(),
    reason="node 또는 frontend node_modules(@playwright/test · vite) 가 없다 — 화면을 올려 볼 수 없다",
)

_HARNESS = r"""
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { AuthContext } from '__FE__/src/auth/AuthContext';
import '__FE__/src/styles/tokens.css';
import '__FE__/src/styles/globals.css';
import '__FE__/src/styles/ui.css';
import UsageStatsPage from '__FE__/src/pages/admin/UsageStatsPage';

(window as unknown as { __mount: (admin: boolean) => void }).__mount = (admin) => {
  const user = { subject: 'root@corp.example', email: 'root@corp.example', display_name: 'Root', groups: admin ? ['portal-admin'] : [] };
  createRoot(document.getElementById('root')!).render(
    <AuthContext.Provider
      value={{ user, status: 'authenticated', login: () => undefined, logout: async () => undefined, refresh: async () => undefined }}
    >
      <MemoryRouter initialEntries={['/admin/usage']}>
        <UsageStatsPage />
      </MemoryRouter>
    </AuthContext.Provider>,
  );
};
"""

# CSS 는 따로 묶어(bundle.css) 그림을 남길 때만 입힌다 — 판정은 글자와 요소로 한다. 글꼴 파일은 비운다.
_BUILD = r"""
const { createRequire } = require('module');
const path = require('path');
const [FE, OUT] = process.argv.slice(2);
const fe = createRequire(path.join(FE, 'package.json'));
const esbuild = createRequire(fe.resolve('vite/package.json'))('esbuild');
esbuild.buildSync({
  entryPoints: [path.join(OUT, 'harness.tsx')], bundle: true, format: 'iife', outfile: path.join(OUT, 'bundle.js'),
  jsx: 'automatic', nodePaths: [path.join(FE, 'node_modules')], logLevel: 'error',
  loader: { '.svg': 'dataurl', '.png': 'dataurl', '.woff2': 'empty', '.woff': 'empty' },
  define: { 'import.meta.env': '{}', 'process.env.NODE_ENV': '"development"' },
});
"""

_STUB = r"""
(() => {
  window.__calls = [];
  window.__report = null;
  const json = (body, status = 200) =>
    Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }));
  window.fetch = (url) => {
    const u = String(url);
    window.__calls.push(u);
    if (u.startsWith('/auth/admin/usage?')) return window.__report ? json(window.__report) : json({ detail: '시험용 실패' }, 502);
    return json({ detail: 'stub: no route ' + u }, 404);
  };
})();
"""

_DRIVE = r"""
const { createRequire } = require('module');
const fs = require('fs');
const path = require('path');
const [FE, OUT, SHOT] = process.argv.slice(2);
const { chromium } = createRequire(path.join(FE, 'package.json'))('@playwright/test');
const reports = JSON.parse(fs.readFileSync(path.join(OUT, 'reports.json'), 'utf8'));

async function open(browser, name, admin = true) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.setDefaultTimeout(10000);
  page.__errors = [];
  page.on('pageerror', (e) => page.__errors.push(String(e)));
  page.on('console', (m) => { if (m.type() === 'error') page.__errors.push('console: ' + m.text()); });
  await page.route('http://harness.invalid/**', (r) =>
    r.fulfill({ contentType: 'text/html', body: '<!doctype html><html><body><div id="root"></div></body></html>' }));
  await page.goto('http://harness.invalid/');
  await page.addScriptTag({ path: path.join(OUT, 'stub.js') });
  await page.evaluate((rep) => { window.__report = rep; }, name ? reports[name] : null);
  if (SHOT && fs.existsSync(path.join(OUT, 'bundle.css'))) await page.addStyleTag({ path: path.join(OUT, 'bundle.css') });
  await page.addScriptTag({ path: path.join(OUT, 'bundle.js') });
  await page.evaluate((a) => window.__mount(a), admin);
  return page;
}
const seen = (page) => page.evaluate(() => ({
  text: document.body.innerText,
  // 사람별 이용 카드를 뺀 글 — 이메일은 그 카드에만 나와야 한다(OD-55)
  text_wo_people: Array.from(document.querySelectorAll('body *')).filter((el) => !el.closest('section[aria-label="사람별 이용"]')
    && !el.querySelector('section[aria-label="사람별 이용"]') && el.children.length === 0).map((el) => el.textContent).join(' '),
  people: (document.querySelector('section[aria-label="사람별 이용"]') || { innerText: '' }).innerText,
  cards: Array.from(document.querySelectorAll('.uc-card > h2')).map((h) => h.textContent),
  tiles: Array.from(document.querySelectorAll('.uc-tile')).map((t) => t.textContent),
  plots: document.querySelectorAll('.uc-plot svg').length,
  calls: window.__calls,
}));

(async () => {
  let browser;
  try { browser = await chromium.launch(); } catch (e) { process.stdout.write(JSON.stringify({ skip: String(e).slice(0, 300) })); return; }
  const out = {};
  try {
    for (const name of ['folded', 'failed', 'pending']) {
      const page = await open(browser, name);
      await page.getByRole('heading', { name: '접기 상태' }).waitFor();
      if (SHOT) {
        await page.screenshot({ path: path.join(SHOT, `usage-${name}.png`), fullPage: true });
        await page.locator('.uc-tiles').screenshot({ path: path.join(SHOT, `usage-${name}-tiles.png`) });
        const cards = page.locator('.uc-card');
        for (let i = 0; i < (await cards.count()); i += 1)
          await cards.nth(i).screenshot({ path: path.join(SHOT, `usage-${name}-card${String(i).padStart(2, '0')}.png`) });
      }
      out[name] = { ...(await seen(page)), errors: page.__errors };
      if (name === 'folded') {
        await page.locator('#usage-days').selectOption('7');
        await page.waitForFunction(() => window.__calls.some((u) => u.includes('days=7')));
        out.picked = { ...(await seen(page)), errors: page.__errors };
      }
      await page.close();
    }
    const down = await open(browser, null);
    await down.getByText('시험용 실패').first().waitFor();
    out.down = { ...(await seen(down)), errors: down.__errors.filter((e) => !e.includes('502')) };
    const plain = await open(browser, 'folded', false);
    await plain.getByText('관리자(portal-admin)만').waitFor();
    out.plain = { ...(await seen(plain)), errors: plain.__errors };
  } finally {
    await browser.close();
  }
  process.stdout.write(JSON.stringify(out));
})().catch((e) => { process.stdout.write(JSON.stringify({ crash: String(e && e.stack || e).slice(0, 2000) })); });
"""


@pytest.fixture()
def shown(scene, tmp_path, tmp_path_factory):  # noqa: F811
    box, rem = scene
    reports = {"folded": box.build(days=30, now=NOW, labels={"service": {"heax-hub": "HEAX 허브"}})}
    rem.status["gateway.test"] = 404
    from tests.test_usage_fold import _fold
    _fold(box, NOW + 3600, rem)
    reports["failed"] = box.build(days=30, now=NOW)
    empty = _box(tmp_path / "empty")
    empty.access((int(_at(D19, 9)), A, "login", "portal", "local"))
    reports["pending"] = empty.build(days=30, now=NOW)
    out = tmp_path_factory.mktemp("usagepage")
    for name, text in (("build.cjs", _BUILD), ("stub.js", _STUB), ("drive.cjs", _DRIVE),
                       ("harness.tsx", _HARNESS.replace("__FE__", str(FE)))):
        (out / name).write_text(text, encoding="utf-8")
    (out / "reports.json").write_text(json.dumps(reports, ensure_ascii=False), encoding="utf-8")
    env = {"PATH": "/usr/bin:/bin:" + str(Path(shutil.which("node")).parent), "HOME": os.environ.get("HOME", "")}
    r = subprocess.run(["node", "build.cjs", str(FE), str(out)], cwd=str(out), capture_output=True, text=True, timeout=120, env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    shot = os.environ.get("HWAX_USAGE_SHOT", "")
    r = subprocess.run(["node", "drive.cjs", str(FE), str(out), shot], cwd=str(out), capture_output=True, text=True, timeout=300, env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    got = json.loads(r.stdout)
    if "skip" in got:
        pytest.skip("헤드리스 브라우저를 띄우지 못했다(playwright 브라우저 미설치) — " + got["skip"])
    assert "crash" not in got, got.get("crash")
    return got


def test_화면은_터지지_않고_접어_둔_표의_카드와_M1_카드를_함께_그린다(shown):
    page = shown["folded"]
    assert page["errors"] == [], page["errors"]
    assert page["cards"] == ["쓴 사람(원천을 가로질러)", "MCP 도구", "MCP 도구 — 앱 · 도구", "MCP 심의 · RA 초안", "LLM 토큰(에이전트 서버)",
                             "정문 요청(허브 앱 열기)", "로그인", "챗", "타일 진입", "대화", "포털 사건", "절차 · 루틴", "계정", "PAT", "권한 수요",
                             "사람별 이용", "접기 상태"]
    tiles = " | ".join(page["tiles"])
    assert "쓴 사람3" in tiles and "MCP 도구 호출10" in tiles and "MCP 심의 잡2" in tiles and "로그인한 계정1" in tiles, tiles
    for want in ("ai-data-hub · search_cards", "개인 PAT(개인 Claude) (pat)", "apps/step_forge", "수명이 끝난 토큰", "≈ 38ms", "접어 둔 새 대화"):
        assert want in page["text"], want
    assert "undefined" not in page["text"] and "NaN" not in page["text"] and "[object" not in page["text"]
    assert page["plots"] >= 12, "그림(막대)이 그려진다"
    for leak in (A, B, C):
        assert leak not in page["text_wo_people"], "이메일은 사람별 이용 카드에만 나온다(OD-55)"
        assert leak in page["people"], leak
    assert [u for u in page["calls"] if u.startswith("/auth/admin/usage")] == ["/auth/admin/usage?days=30"]


def test_기간을_고르면_그_기간으로_다시_읽는다(shown):
    calls = [u for u in shown["picked"]["calls"] if u.startswith("/auth/admin/usage")]
    assert calls == ["/auth/admin/usage?days=30", "/auth/admin/usage?days=7"] and shown["picked"]["errors"] == []


def test_접지_못한_원천이_있으면_위에_까닭이_뜨고_접은_적이_없으면_카드마다_그렇다고_말한다(shown):
    failed, pending = shown["failed"], shown["pending"]
    assert failed["errors"] == [] and "날마다 접지 못한 원천이 있다" in failed["text"] and "그쪽 판이 낡았다" in failed["text"]
    assert "ai-data-hub · search_cards" in failed["text"], "앞서 접은 수는 그대로 보인다"
    assert pending["errors"] == [] and pending["text"].count("아직 접은 적이 없다") >= 10
    assert "쓴 사람—" in " | ".join(pending["tiles"]), "접은 적이 없으면 타일은 0 이 아니라 빈 값이다"
    assert len(pending["cards"]) == 17 and "undefined" not in pending["text"]


def test_읽기가_실패하면_까닭을_보이고_관리자가_아니면_묻지도_않는다(shown):
    assert "시험용 실패" in shown["down"]["text"] and shown["down"]["errors"] == [] and shown["down"]["cards"] == []
    assert "관리자(portal-admin)만" in shown["plain"]["text"]
    assert not [u for u in shown["plain"]["calls"] if u.startswith("/auth/admin/usage")], "관리자가 아니면 통계를 묻지 않는다"
