# '전문가 고르기 검토' 화면을 헤드리스 브라우저에 올려 고르기 · 저장 · 보기만 · 모으기를 사람처럼 눌러 본다 — 서버는 띄우지 않는다(가짜 fetch)
"""왜 — 표시의 꼴(주 · 같이 · 나무에서 골랐나 · 찾아서 골랐나 · 없음 · 모르겠음)은 화면의 상태가 만든다. 타입 검사로는 '찾아서 고른 전문가가 search 로
적히는가' · '다는 사람이 아닌 관리자의 단추가 잠기는가' 를 못 본다. 그리고 누설 규칙 L6 — 답에 순위 · 점수 칸이 섞여 와도(옛 판) 화면이 그리지 않는가.
도구는 test_admin_pages_in_browser 와 같다(esbuild · @playwright/test). 없으면 건너뛴다(운영 박스). 주소 · 질문 글은 지어낸 값이다.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

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
import SeatReviewPage from '__FE__/src/pages/admin/SeatReviewPage';

(window as unknown as { __mount: () => void }).__mount = () => {
  const user = { subject: 'root@corp.example', email: 'root@corp.example', display_name: 'Root', groups: ['portal-admin'] };
  createRoot(document.getElementById('root')!).render(
    <AuthContext.Provider
      value={{ user, status: 'authenticated', login: () => undefined, logout: async () => undefined, refresh: async () => undefined }}
    >
      <MemoryRouter initialEntries={['/admin/seat-review']}>
        <SeatReviewPage />
      </MemoryRouter>
    </AuthContext.Provider>,
  );
};
"""

_BUILD = r"""
const { createRequire } = require('module');
const path = require('path');
const [FE, OUT] = process.argv.slice(2);
const fe = createRequire(path.join(FE, 'package.json'));
const esbuild = createRequire(fe.resolve('vite/package.json'))('esbuild');
esbuild.buildSync({
  entryPoints: [path.join(OUT, 'harness.tsx')], bundle: true, format: 'iife', outfile: path.join(OUT, 'bundle.js'),
  jsx: 'automatic', nodePaths: [path.join(FE, 'node_modules')], logLevel: 'error',
  loader: { '.css': 'empty', '.svg': 'dataurl', '.png': 'dataurl', '.woff2': 'empty', '.woff': 'empty' },
  define: { 'import.meta.env': '{}', 'process.env.NODE_ENV': '"development"' },
});
"""

# 가짜 포털 — /auth/admin/seat-review/* 만. 답에 순위 · 점수 칸을 일부러 섞는다(L6 — 화면이 그리지 않아야 한다).
_STUB = r"""
(() => {
  window.__calls = [];
  window.__view = {
    contract: 'seat-review/1', total: 2, counts: { persona: 1, thinking: 1, delib: 0, expert_cmd: 0 },
    filtered: { short: 3, not_standalone: 1, near_dup: 2 }, labeled: { mine: 1, any: 1 },
    collect: { on: true, days: 60 }, labelers_set: true, me: { by: 'root@corp.example', can_label: true },
    items: [
      { qid: 'H-aaaaaaaaaaaa', d: '2026-10-30', src: 'thinking', text: '보드 낙하 시 솔더 크랙 판정 기준', mine: null, others: 0,
        score: 0.91, rank: 1, seats: ['sim-drop-impact'] },
      { qid: 'H-bbbbbbbbbbbb', d: '2026-10-29', src: 'persona', text: '과제 코드 A1 의 개발모델 목록', others: 1,
        mine: { primary: ['rel-drop-impact'], also: [], none: null, unsure: false, via: { 'rel-drop-impact': 'tree' }, memo: '', t: 1 } },
    ],
  };
  window.__experts = [
    { key: 'cam-lens-molding', name: '렌즈 사출 전문가' }, { key: 'rel-drop-impact', name: '낙하 시험 전문가' },
    { key: 'rel-thermal-shock', name: '열충격 시험 전문가' }, { key: 'sim-drop-impact', name: '낙하 해석 전문가' },
  ];
  const json = (body, status = 200) =>
    Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }));
  window.fetch = (url, init = {}) => {
    const u = decodeURIComponent(String(url)), method = (init.method || 'GET').toUpperCase();
    const body = init.body ? JSON.parse(init.body) : null;
    window.__calls.push({ method, u, body });
    let m;
    if (u.startsWith('/auth/admin/seat-review/items?')) return json(window.__view);
    if (u === '/auth/admin/seat-review/catalog') return json({ contract: 'seat-review/1', experts: window.__experts });
    if ((m = u.match(/^\/auth\/admin\/seat-review\/expert\?key=(.+)$/)))
      return json({ contract: 'seat-review/1', key: m[1], name: m[1], desc: `${m[1]} 의 설명`, error: null, score: 0.77 });
    if (u === '/auth/admin/seat-review/label' && method === 'POST') return json({ contract: 'seat-review/1', ok: true, qid: body.qid, removed: !!body.remove });
    if (u === '/auth/admin/seat-review/collect' && method === 'POST')
      return json({ contract: 'seat-review/1', harvest: { days: 60, seen: {}, sent: 7, skipped: {}, scrubbed: 2 },
                    agent: { added: 5, dup: 2, old: 0, short: 0 } });
    return json({ detail: 'stub: no route ' + u }, 404);
  };
})();
"""

_DRIVE = r"""
const { createRequire } = require('module');
const path = require('path');
const [FE, OUT] = process.argv.slice(2);
const { chromium } = createRequire(path.join(FE, 'package.json'))('@playwright/test');

async function open(browser, seed = '') {
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  page.setDefaultTimeout(10000);
  page.__errors = [];
  page.on('pageerror', (e) => page.__errors.push(String(e)));
  await page.route('http://harness.invalid/**', (r) =>
    r.fulfill({ contentType: 'text/html', body: '<!doctype html><html><body><div id="root"></div></body></html>' }));
  await page.goto('http://harness.invalid/');
  await page.addScriptTag({ path: path.join(OUT, 'stub.js') });
  if (seed) await page.evaluate(seed);
  await page.addScriptTag({ path: path.join(OUT, 'bundle.js') });
  await page.evaluate(() => window.__mount());
  await page.getByText('보드 낙하 시 솔더 크랙 판정 기준').waitFor();
  return page;
}
const posts = (page) => page.evaluate(() => window.__calls.filter((c) => c.method === 'POST').map((c) => ({ u: c.u, body: c.body })));
const editRow = (page, text) => page.locator('tr', { hasText: text }).getByRole('button', { name: '표시 달기' });

const SCENARIOS = {
  // 나무에서 주 전문가 · 이름 찾기로 같이 맡을 전문가를 골라 저장 — via 가 tree · search 로 갈린다
  async pick(browser) {
    const page = await open(browser);
    const text = await page.locator('body').innerText();
    await editRow(page, '보드 낙하').click();
    await page.locator('.pv-tree .pv-tree-name', { hasText: '신뢰성' }).click();
    await page.locator('.srv-experts li', { hasText: '낙하 시험 전문가' }).getByRole('button', { name: '주', exact: true }).click();
    await page.locator('.srv-search').fill('렌즈');
    await page.locator('.srv-experts li', { hasText: '렌즈 사출 전문가' }).getByRole('button', { name: '같이', exact: true }).click();
    await page.locator('.srv-experts li', { hasText: '렌즈 사출 전문가' }).locator('.srv-name').click();
    await page.locator('.srv-card').getByText('cam-lens-molding 의 설명').waitFor();
    const chips = await page.locator('.srv-chip').allInnerTexts();
    await page.getByRole('button', { name: '저장', exact: true }).click();
    await page.waitForFunction(() => window.__calls.filter((c) => c.u.startsWith('/auth/admin/seat-review/items?')).length >= 2);
    const card = await page.evaluate(() => window.__calls.filter((c) => c.u.includes('/expert?')).map((c) => c.u));
    return { text, chips, posts: await posts(page), card, errors: page.__errors };
  },
  // 없음 — 코어 데이터로 바꿔 저장 · 내 표시 지우기
  async none(browser) {
    const page = await open(browser);
    await editRow(page, '개발모델 목록').click();
    const kept = await page.locator('.srv-chip').allInnerTexts();
    await page.getByLabel('없음 — 코어 데이터(정본 허브에서 조회할 질문)').check();
    await page.getByRole('button', { name: '저장', exact: true }).click();
    await page.waitForFunction(() => window.__calls.some((c) => c.method === 'POST'));
    await editRow(page, '개발모델 목록').click();
    await page.getByRole('button', { name: '내 표시 지우기' }).click();
    await page.waitForFunction(() => window.__calls.filter((c) => c.method === 'POST').length >= 2);
    return { kept, posts: await posts(page), errors: page.__errors };
  },
  // 다는 사람이 아닌 관리자 · 모으기가 꺼진 박스 — 단추가 잠기고 무엇을 적으면 되는지 말한다
  async viewer(browser) {
    const page = await open(browser, `window.__view = { ...window.__view, collect: { on: false, days: 60 }, labelers_set: false,
      me: { by: 'root@corp.example', can_label: false } }`);
    const marks = await page.getByRole('button', { name: '표시 달기' }).evaluateAll((bs) => bs.map((b) => b.disabled));
    const collect = await page.getByRole('button', { name: '지난 날 모으기' }).isDisabled();
    return { marks, collect, text: await page.locator('body').innerText(), errors: page.__errors };
  },
  async collect(browser) {
    const page = await open(browser);
    await page.getByRole('button', { name: '지난 날 모으기' }).click();
    await page.getByText(/새로 든 것 5/).waitFor();
    return { posts: await posts(page), text: await page.locator('body').innerText(), errors: page.__errors };
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
    """화면을 한 번 묶고 시나리오를 한 번에 돌린다(브라우저를 시험마다 띄우지 않는다)."""
    out = tmp_path_factory.mktemp("seat-review")
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
        assert not got[name].get("errors"), f"화면이 예외를 던졌다: {got[name]['errors']}"
        return got[name]
    return scenario


def test_나무에서_고른_주_전문가와_찾아서_고른_같이_전문가가_via_와_함께_저장된다(seen):
    s = seen("pick")
    assert s["posts"] == [{"u": "/auth/admin/seat-review/label", "body": {
        "qid": "H-aaaaaaaaaaaa", "primary": ["rel-drop-impact"], "also": ["cam-lens-molding"],
        "via": {"rel-drop-impact": "tree", "cam-lens-molding": "search"}, "memo": ""}}], s["posts"]
    assert any("주 · 낙하 시험 전문가" in c for c in s["chips"]) and any("같이 · 렌즈 사출 전문가 · 찾음" in c for c in s["chips"]), s["chips"]
    assert s["card"] == ["/auth/admin/seat-review/expert?key=cam-lens-molding"], "카드는 누른 사람 하나만 부른다"


def test_화면에는_순위_점수_지금_좌석이_그려지지_않는다(seen):
    """누설 규칙 L6 — 답에 score · rank · seats 가 섞여 와도(옛 판) 화면은 질문 · 출처 · 내 표시 · 다른 표시 수만 그린다."""
    text = seen("pick")["text"]
    for v in ("0.91", "sim-drop-impact", "score", "rank", "0.77"):
        assert v not in text, f"{v} 가 화면에 그려졌다"
    assert "보드 낙하 시 솔더 크랙 판정 기준" in text and "띵킹" in text and "주 낙하 시험 전문가" in text


def test_없음_으로_바꿔_저장하고_내_표시를_지운다(seen):
    s = seen("none")
    assert any("주 · 낙하 시험 전문가" in c for c in s["kept"]), "내 표시를 열면 앞서 고른 전문가가 그대로 든다"
    assert s["posts"] == [
        {"u": "/auth/admin/seat-review/label", "body": {"qid": "H-bbbbbbbbbbbb", "none": "core_data", "memo": ""}},
        {"u": "/auth/admin/seat-review/label", "body": {"qid": "H-bbbbbbbbbbbb", "remove": True}},
    ], s["posts"]


def test_다는_사람이_아니면_단추가_잠기고_모으기가_꺼지면_그렇게_말한다(seen):
    s = seen("viewer")
    assert s["marks"] == [True, True] and s["collect"] is True
    assert "SEAT_QUESTIONS_LABELERS" in s["text"] and "SEAT_QUESTIONS_COLLECT=1" in s["text"]
    assert "다는 사람이 정해지지 않아" in s["text"]


def test_지난_날_모으기는_한_번_밀고_수를_보인다(seen):
    s = seen("collect")
    assert s["posts"] == [{"u": "/auth/admin/seat-review/collect", "body": None}]
    assert "대화 저장소에서 7건을 넣었다" in s["text"] and "이미 있던 것 2" in s["text"]
