// 화면 점검 — 가로 넘침·밝은 패널·마크다운 기호 노출·헤더 줄바꿈을 경로×폭마다 단언하고 캡처를 남긴다(docs/ui-refresh 단계 0)
import { test, expect, type Browser, type Page } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const TIER = process.env.UI_TIER ?? 'admin';
const WIDTHS = [1440, 1280, 1024, 768, 390];
const SHOTS = join(dirname(fileURLToPath(import.meta.url)), '.shots', TIER);
mkdirSync(SHOTS, { recursive: true });

const ROUTES = ['/', '/apps', '/deliberate', '/procedures', '/tokens', '/updates', '/access', '/risk', '/no-such-page',
  ...(TIER === 'admin' ? ['/admin/users', '/admin/access'] : [])];

const ANSWER = [
  '## 열충격 해석 결과 요약', '', 'SED 기준으로 **솔더 조인트 3곳**이 임계값을 넘었습니다.', '',
  '| 위치 | SED (MJ/m³) | 임계 대비 | 판정 |', '|---|---|---|---|',
  '| U12 코너 볼 | 0.412 | 137% | 위험 |', '| U12 엣지 볼 | 0.318 | 106% | 주의 |', '| C45 패드 | 0.301 | 100% | 경계 |', '',
  '### 권장 조치', '1. U12 언더필 적용 검토', '2. 보드 두께 1.0 → 1.2 mm 재해석', '', '```text', 'cycles: -40 ~ 125 °C, 1000 cycles', '```',
].join('\n');

/** 로그인(mock)하고, 첫 로그인 업데이트 팝업은 '본 것' 으로 표시해 다른 화면을 가리지 않게 한다. */
async function login(browser: Browser, width: number, { suppressPopup = true } = {}): Promise<Page> {
  const ctx = await browser.newContext({ viewport: { width, height: 900 } });
  const page = await ctx.newPage();
  await page.goto('/auth/login');
  await page.waitForLoadState('networkidle');
  if (suppressPopup) {
    await page.evaluate(() => {
      for (const k of Object.keys(localStorage)) if (k.startsWith('hwax.changelog.seen')) localStorage.removeItem(k);
    });
    const me = await (await page.request.get('/auth/me')).json();
    await page.evaluate((email) => localStorage.setItem(`hwax.changelog.seen.${email}`, '9999-12-31'), me.email);
  }
  return page;
}

/** 화면의 결함을 모은다 — 빈 배열이면 통과. */
async function defects(page: Page, width: number): Promise<string[]> {
  return page.evaluate((w) => {
    const out: string[] = [];
    const doc = document.documentElement;
    if (doc.scrollWidth > window.innerWidth + 1) out.push(`가로 넘침 ${doc.scrollWidth}px > ${window.innerWidth}px`);
    const lum = (c: string) => {
      const m = c.match(/rgba?\(([^)]+)\)/);
      if (!m) return { l: 0, a: 0 };
      const [r, g, b, a = '1'] = m[1].split(',').map((x) => x.trim());
      const ch = (v: string) => { const s = Number(v) / 255; return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4; };
      return { l: 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b), a: Number(a) };
    };
    for (const el of Array.from(document.querySelectorAll<HTMLElement>('body *'))) {
      if (el.closest('img,svg,video,canvas,.katex')) continue;
      const r = el.getBoundingClientRect();
      if (r.width < 200 || r.height < 40) continue;
      const st = getComputedStyle(el);
      if (st.visibility === 'hidden' || st.display === 'none' || Number(st.opacity) < 0.1) continue;
      const { l, a } = lum(st.backgroundColor);
      if (a > 0.5 && l > 0.8) out.push(`밝은 패널 ${el.tagName.toLowerCase()}.${(el.className || '').toString().split(' ')[0]} ${Math.round(r.width)}x${Math.round(r.height)}`);
    }
    const text = document.body.innerText;
    const md = text.match(/[^\n]{0,20}\*\*[^\n]{0,20}/);
    if (md) out.push(`마크다운 기호 노출 "${md[0]}"`);
    if (w >= 1024) {
      for (const a of Array.from(document.querySelectorAll<HTMLElement>('header a, header button'))) {
        const r = a.getBoundingClientRect();
        if (r.width > 0 && r.height > 44) out.push(`헤더 줄바꿈 "${a.innerText.replace(/\s+/g, '/')}" ${Math.round(r.height)}px`);
      }
    }
    return out;
  }, width);
}

test.beforeAll(async ({ browser }) => {
  // 실제처럼 보이게 대화 하나 — 임시 저장소라 매 실행 새로 만든다
  const page = await login(browser, 1440);
  await page.evaluate(async (answer) => {
    const csrf = decodeURIComponent((document.cookie.match(/hwax_csrf=([^;]+)/) || [])[1] || '');
    const h = { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf };
    // 실패하면 Playwright 가 워커를 다시 띄워 beforeAll 이 또 돈다 — 이미 있으면 다시 만들지 않는다
    const have = await (await fetch('/agent/conversations')).json();
    if ((have.conversations ?? []).some((x: { title?: string }) => x.title?.startsWith('열충격 해석 결과 검토'))) return;
    const c = await (await fetch('/agent/conversations', { method: 'POST', headers: h,
      body: JSON.stringify({ title: '열충격 해석 결과 검토 — U12 솔더' }) })).json();
    for (const [role, content] of [['user', '지난주 열충격 해석 결과에서 위험한 솔더 조인트를 정리해 줘'], ['assistant', answer]])
      await fetch(`/agent/conversations/${c.id}/messages`, { method: 'POST', headers: h, body: JSON.stringify({ role, content }) });
  }, ANSWER);
  await page.context().close();
});

for (const route of ROUTES) {
  test(`화면 ${route}`, async ({ browser }) => {
    for (const w of WIDTHS) {
      const page = await login(browser, w);
      await page.goto(route);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(600);
      const slug = route.replace(/\//g, '_').replace(/^_$/, '_home');
      await page.screenshot({ path: join(SHOTS, `${w}${slug}.png`), fullPage: true });
      expect.soft(await defects(page, w), `${route} @${w}px`).toEqual([]);
      await page.context().close();
    }
  });
}

test('대화 화면 — 시드 대화를 연다', async ({ browser }) => {
  for (const w of [1440, 1024]) {
    const page = await login(browser, w);
    await page.goto('/');
    await page.getByText('열충격 해석 결과 검토', { exact: false }).first().click();
    await page.waitForTimeout(800);
    await page.screenshot({ path: join(SHOTS, `${w}_chat-conv.png`) });
    expect.soft(await defects(page, w), `대화 @${w}px`).toEqual([]);
    await page.context().close();
  }
});

test('첫 로그인 업데이트 팝업', async ({ browser }) => {
  const page = await login(browser, 1440, { suppressPopup: false });
  await page.waitForTimeout(800);
  await page.screenshot({ path: join(SHOTS, '1440_changelog-popup.png') });
  expect.soft(await defects(page, 1440), '업데이트 팝업').toEqual([]);
  await page.context().close();
});

test('파일 첨부 패널', async ({ browser }) => {
  const page = await login(browser, 1440);
  await page.goto('/');
  await page.waitForLoadState('networkidle');
  // 첨부는 파일 올리기 권한(feat:upload)이 있을 때만 있다 — 기본 권한 층에는 입력이 없다
  test.skip(await page.locator('input[type=file]').count() === 0, '이 권한 층에는 파일 첨부가 없다');
  await page.locator('input[type=file]').first().setInputFiles({
    name: 'sample.csv', mimeType: 'text/csv', buffer: Buffer.from('strain,stress\n0,0\n0.01,210\n'),
  });
  await page.waitForTimeout(1200);
  await page.screenshot({ path: join(SHOTS, '1440_attach.png') });
  expect.soft(await defects(page, 1440), '첨부 패널').toEqual([]);
  await page.context().close();
});

test('로그인 화면(로그아웃 상태)', async ({ browser }) => {
  for (const w of [1440, 390]) {
    const ctx = await browser.newContext({ viewport: { width: w, height: 900 } });
    const page = await ctx.newPage();
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: join(SHOTS, `${w}_login.png`), fullPage: true });
    expect.soft(await defects(page, w), `로그인 @${w}px`).toEqual([]);
    await ctx.close();
  }
});
