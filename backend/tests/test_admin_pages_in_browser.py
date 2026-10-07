# 관리자·로그인 화면을 헤드리스 브라우저에 실제로 올려 상태가 있는 동작을 본다 — 서버는 띄우지 않는다(가짜 fetch)
"""왜 — 화면의 상태 동작(필터가 언제 걸리고 풀리는가 · 거절 사유가 어디에 뜨는가 · 확인창을 거치는가)은 타입 검사·린트로는
안 잡히고, 순수 함수가 아니라 node 단위 시험(test_admin_screen_units)으로도 못 돌린다. 화면 점검(frontend/e2e)은 빌드한 dist 와
임시 포털이 있어야 돌아 평소 시험에 들지 않는다. 그래서 실제 페이지 컴포넌트를 esbuild 로 한 파일로 묶어, 빈 문서 한 장에
올리고 fetch 만 가짜 원장으로 바꿔 사람처럼 눌러 본다. 서버도 네트워크도 없다.

도구는 프론트가 이미 가진 것만 쓴다 — esbuild(vite 가 들고 있다) · @playwright/test · 그 브라우저. 없으면 건너뛴다(운영 박스).
주소는 지어낸 값이다.
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

# 실제 페이지를 가짜 로그인 상태 위에 올리는 진입점. `__FE__` 는 이 리포의 frontend 절대경로로 바꿔 쓴다.
_HARNESS = r"""
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { AuthContext } from '__FE__/src/auth/AuthContext';
import UsersAdminPage from '__FE__/src/pages/admin/UsersAdminPage';

const PAGES = { users: UsersAdminPage } as const;
type Name = keyof typeof PAGES;
(window as unknown as { __mount: (name: Name, url: string, signedIn: boolean) => void }).__mount = (name, url, signedIn) => {
  const Page = PAGES[name];
  const user = signedIn
    ? { subject: 'root@corp.example', email: 'root@corp.example', display_name: 'Root', groups: ['portal-admin'] }
    : null;
  createRoot(document.getElementById('root')!).render(
    <AuthContext.Provider
      value={{ user, status: signedIn ? 'authenticated' : 'unauthenticated', login: () => undefined,
               logout: async () => undefined, refresh: async () => undefined }}
    >
      <MemoryRouter initialEntries={[url]}>
        <Page />
      </MemoryRouter>
    </AuthContext.Provider>,
  );
};
"""

# esbuild 는 vite 의 의존성이라 최상위 node_modules 에 없다(pnpm) — vite 자리에서 찾는다. CSS·글꼴은 비운다(동작만 본다).
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

# 가짜 백엔드 — 포털 라우트의 원장 동작만 흉내 낸다. __db 가 원장, __calls 가 받은 요청, __refuse 가 한 번 거절할 요청.
_STUB = r"""
(() => {
  const now = Math.floor(Date.now() / 1000);
  window.__mk = (email, o = {}) => ({
    email, name: email.split('@')[0], department: '', affiliation: '', grants: [], groups: [], status: 'active',
    auth_source: 'sso', created_at: now, approved_at: now, last_login_at: null, locked_until: 0, admin_pinned: false, ...o,
  });
  window.__db = [];
  window.__calls = [];
  window.__refuse = {};
  const policy = {
    features: [{ key: 'feat:chat', label: '챗', desc: '', implies: [] }], platforms: [{ key: 'plat:x', label: 'X', desc: '' }],
    affiliations: [{ id: 'CAEG', label: 'CAE그룹', grants: ['*'] }, { id: 'LAB', label: '시험실', grants: [] }],
    default_grants: ['feat:chat'],
  };
  const json = (body, status = 200) =>
    Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }));
  window.fetch = (url, init = {}) => {
    const u = String(url), method = (init.method || 'GET').toUpperCase();
    const body = init.body ? JSON.parse(init.body) : {};
    const key = `${method} ${decodeURIComponent(u)}`;
    window.__calls.push({ key, body });
    if (window.__refuse[key]) { const detail = window.__refuse[key]; delete window.__refuse[key]; return json({ detail }, 409); }
    let m;
    if (u === '/auth/local/users') return json(window.__db.map((r) => ({ ...r })));
    if (u === '/auth/access/policy') return json(policy);
    if (u.startsWith('/auth/access/requests')) return json([]);
    if (u === '/setup/requests') return json({ items: [], pending: 0 });
    if ((m = u.match(/^\/auth\/local\/users\/([^/]+)\/approve$/))) {
      const r = window.__db.find((x) => x.email === decodeURIComponent(m[1]));
      r.status = 'active'; r.groups = body.groups ?? r.groups;
      return json({ ok: true });
    }
    if ((m = u.match(/^\/auth\/access\/users\/([^/]+)$/)) && method === 'PATCH') {
      const r = window.__db.find((x) => x.email === decodeURIComponent(m[1]));
      if (body.admin === true && !r.groups.includes('portal-admin')) r.groups = [...r.groups, 'portal-admin'];
      if (body.admin === false) r.groups = r.groups.filter((g) => g !== 'portal-admin');
      if (body.affiliation !== undefined) r.affiliation = body.affiliation;
      return json({ email: r.email, affiliation: r.affiliation, grants: r.grants, admin: r.groups.includes('portal-admin'), pats_revoked: 0 });
    }
    return json({ detail: 'stub: no route ' + u }, 404);
  };
})();
"""

# 시나리오 구동기 — 묶은 페이지를 빈 문서에 올려 사람처럼 누르고, 본 것을 JSON 으로 낸다. 시나리오마다 새 탭이다.
_DRIVE = r"""
const { createRequire } = require('module');
const path = require('path');
const [FE, OUT] = process.argv.slice(2);
const { chromium } = createRequire(path.join(FE, 'package.json'))('@playwright/test');

async function open(browser, pageName, url, { signedIn = true, seed = '', dialog = 'accept' } = {}) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  page.setDefaultTimeout(10000);
  page.__dialogs = [];
  page.on('dialog', (d) => { page.__dialogs.push(d.message()); return dialog === 'accept' ? d.accept() : d.dismiss(); });
  page.__errors = [];
  page.on('pageerror', (e) => page.__errors.push(String(e)));
  // 가로챈 주소로 빈 문서를 준다 — about:blank 에서는 document.cookie 가 막혀 apiFetch 의 CSRF 읽기가 던진다(서버는 여전히 없다)
  await page.route('http://harness.invalid/**', (r) =>
    r.fulfill({ contentType: 'text/html', body: '<!doctype html><html><body><div id="root"></div></body></html>' }));
  await page.goto('http://harness.invalid/');
  await page.addScriptTag({ path: path.join(OUT, 'stub.js') });
  if (seed) await page.evaluate(seed);
  await page.addScriptTag({ path: path.join(OUT, 'bundle.js') });
  await page.evaluate(([n, u, s]) => window.__mount(n, u, s), [pageName, url, signedIn]);
  return page;
}
const filterBox = (page) => page.evaluate(() => {
  const cb = document.querySelector('.adm-filter input[type=checkbox]');
  return { rows: Array.from(document.querySelectorAll('.adm-table tbody tr > td:first-child')).map((td) => td.textContent),
           checked: cb.checked, disabled: cb.disabled };
});
const unassignedIs = (page, n) =>
  page.waitForFunction((k) => document.querySelector('.adm-filter label').textContent.includes(`(${k}명)`), n);

const SCENARIOS = {
  // '소속 미지정만 보기' 를 켠 채 마지막 미지정을 지정한 뒤, 누군가 다시 미지정이 됐을 때(대기 가입자를 승인)
  async filter(browser) {
    const page = await open(browser, 'users', '/admin/users', { seed: `window.__db = [
      __mk('root@corp.example', { groups: ['portal-admin'] }), __mk('u1@corp.example', { affiliation: 'CAEG' }),
      __mk('u2@corp.example'), __mk('u3@corp.example'), __mk('p1@corp.example', { status: 'pending', approved_at: null })]` });
    await page.waitForSelector('select[aria-label="u3@corp.example 소속"]');
    await page.locator('.adm-filter input[type=checkbox]').check();
    const on = await filterBox(page);
    await page.locator('select[aria-label="u2@corp.example 소속"]').selectOption('CAEG');
    await unassignedIs(page, 1);
    const one_left = await filterBox(page);
    await page.locator('select[aria-label="u3@corp.example 소속"]').selectOption('CAEG');
    await unassignedIs(page, 0);
    const emptied = await filterBox(page);
    await page.locator('tr', { hasText: 'p1@corp.example' }).getByRole('button', { name: '승인', exact: true }).click();
    await unassignedIs(page, 1);
    return { on, one_left, emptied, later: await filterBox(page), errors: page.__errors };
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
    """화면을 한 번 묶고 시나리오를 한 번에 돌려, 시나리오 이름 → 본 것을 돌려준다(브라우저를 시험마다 띄우지 않는다)."""
    out = tmp_path_factory.mktemp("pages")
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


ALL = ["root@corp.example", "u1@corp.example", "u2@corp.example", "u3@corp.example", "p1@corp.example"]


def test_소속_미지정만_보기는_미지정이_0명이_되면_꺼지고_나중에_저절로_다시_걸리지_않는다(seen):
    """필터를 켠 채 마지막 미지정을 지정하면 표는 전체로 돌아가고 체크박스는 꺼진 채 잠긴다 — 그런데 값은 켜진 채 남아 있었다
    (잠긴 체크박스로는 끌 수도 없다). 그 뒤 누가 미지정이 되는 순간(대기 가입자 승인 · 소속 없는 관리자 해제 · '없음' 으로 바꿈 ·
    새 SSO 사용자) 손대지 않은 필터가 다시 걸려, 표가 그 한 줄로 접히고 나머지 사용자가 사라졌다."""
    s = seen("filter")
    assert s["on"] == {"rows": ["u2@corp.example", "u3@corp.example"], "checked": True, "disabled": False}, "전제 — 켜면 미지정만 보인다"
    assert s["one_left"] == {"rows": ["u3@corp.example"], "checked": True, "disabled": False}, "미지정이 남아 있는 동안은 켜진 채다"
    assert s["emptied"] == {"rows": ALL, "checked": False, "disabled": True}, "0명이 되면 전체로 돌아간다(종전부터)"
    assert s["later"] == {"rows": ALL, "checked": False, "disabled": False}, (
        "미지정이 다시 생겼을 때 표가 그 한 줄로 접혔다 — 필터 값이 켜진 채 남아 있었다")
