// 화면 점검 — 가로 넘침·밝은 패널·마크다운 기호 노출·헤더 줄바꿈을 경로×폭마다 단언하고 캡처를 남긴다(docs/ui-refresh 단계 0)
import { test, expect, type Browser, type Page } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const TIER = process.env.UI_TIER ?? 'admin';
const WIDTHS = [1440, 1280, 1024, 768, 390];
const SHOTS = join(dirname(fileURLToPath(import.meta.url)), '.shots', TIER);
mkdirSync(SHOTS, { recursive: true });

const ROUTES = ['/', '/apps', '/deliberate', '/procedures', '/tokens', '/tokens?tab=apps', '/tokens?tab=connect', '/updates', '/access', '/risk', '/no-such-page',
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
    if (doc.scrollWidth > window.innerWidth + 1) {
      // 범인을 같이 적는다 — 화면 오른쪽 밖으로 나간 요소 중 가장 바깥 셋(가로 스크롤 상자 안쪽은 뺀다)
      const sticking = Array.from(document.querySelectorAll<HTMLElement>('body *'))
        .filter((el) => el.getBoundingClientRect().right > window.innerWidth + 1)
        .filter((el) => !el.parentElement?.closest('[style*="overflow-x: auto"], [style*="overflow: auto"], pre, .md-table-wrap'))
        .slice(0, 3)
        .map((el) => `${el.tagName.toLowerCase()}${el.className ? '.' + String(el.className).split(' ')[0] : ''}→${Math.round(el.getBoundingClientRect().right)}`);
      out.push(`가로 넘침 ${doc.scrollWidth}px > ${window.innerWidth}px [${sticking.join(', ')}]`);
    }
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
    // 저장된 심의 하나 — 서버 저장본에서 되살린 회의록(진행 표시·화자 이름)을 본다
    const dc = await (await fetch('/agent/conversations', { method: 'POST', headers: h,
      body: JSON.stringify({ title: '배터리 스웰링 대응 심의', kind: 'deliberation' }) })).json();
    const say = (persona: string, round: number, content: string, stance: string) =>
      fetch(`/agent/conversations/${dc.id}/messages`, { method: 'POST', headers: h,
        body: JSON.stringify({ role: 'persona', persona, round, content, meta: { stance } }) });
    await fetch(`/agent/conversations/${dc.id}/messages`, { method: 'POST', headers: h,
      body: JSON.stringify({ role: 'user', content: '배터리 스웰링 불량 — 셀 적층 설계에서 어떤 대응이 우선인가' }) });
    await say('battery-cell', 1, '**가스 발생**이 지배적입니다. 전해액 분해 온도 마진부터 확인해야 합니다.', '조건부');
    await say('cae-structure', 1, '파우치 구속 강성을 올리면 두께 증가를 30% 줄일 수 있습니다.', '동의');
    await say('battery-cell', 3, '구속 강성 보강에 동의하되 전해액 첨가제 검토를 병행합니다.', '동의');
    await say('cae-structure', 3, '보강안으로 수렴합니다.', '동의');
    await fetch(`/agent/conversations/${dc.id}/messages`, { method: 'POST', headers: h,
      body: JSON.stringify({ role: 'assistant', content: '## 의사결정\n1. 파우치 구속 강성 보강을 우선한다.\n2. 전해액 첨가제 검토를 병행한다.' }) });
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
      const slug = route.replace(/[/?=]/g, '_').replace(/^_$/, '_home');
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

test('로그인 화면 — SSO 실패로 돌아왔을 때', async ({ browser }) => {
  for (const w of [1440, 390]) {
    const ctx = await browser.newContext({ viewport: { width: w, height: 900 } });
    const page = await ctx.newPage();
    const detail = encodeURIComponent('SAML 응답에 사번(Mail) 클레임이 없습니다. 받은 클레임: http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name, http://schemas.microsoft.com/ws/2008/06/identity/claims/groups');
    await page.goto(`/login?error=sso&detail=${detail}`);
    await page.waitForLoadState('networkidle');
    await expect(page.getByRole('alert')).toContainText('SSO 로그인을 마치지 못했습니다');
    await page.getByText('자세히').click();
    await page.screenshot({ path: join(SHOTS, `${w}_login_sso_fail.png`), fullPage: true });
    expect.soft(await defects(page, w), `로그인 실패 @${w}px`).toEqual([]);
    await ctx.close();
  }
});

test('개인 토큰 — 탭을 화살표로 옮기면 그 탭이 열리고 주소에 남는다', async ({ browser }) => {
  const page = await login(browser, 1440);
  await page.goto('/tokens');
  await page.waitForLoadState('networkidle');
  const tabs = page.getByRole('tab');
  test.skip((await tabs.count()) === 0, '이 권한 층은 토큰 탭이 없다(연결 설정만)');
  await tabs.first().focus();
  await page.keyboard.press('ArrowRight');
  await expect(page.getByRole('tab', { name: '허브에 보일 앱' })).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByRole('tab', { name: '허브에 보일 앱' })).toBeFocused();
  expect(page.url()).toContain('tab=apps');
  await page.keyboard.press('End');
  await expect(page.getByRole('tabpanel')).toContainText('Report Archive 연결');
  await page.keyboard.press('Home');
  await expect(page.getByRole('tabpanel')).toContainText('내 토큰');
  await page.context().close();
});

test('개인 토큰 — 발급 직후(한 번만 보이는 상자)', async ({ browser }) => {
  for (const w of [1440, 390]) {
    const page = await login(browser, w);
    await page.goto('/tokens');
    await page.waitForLoadState('networkidle');
    const name = page.getByRole('textbox', { name: '토큰 이름' });
    test.skip((await name.count()) === 0, '이 권한 층은 토큰을 발급하지 않는다');
    await name.fill(`ui-check-${w}`);
    await page.getByRole('button', { name: '토큰 발급' }).click();
    await expect(page.getByText('지금만 보이는 토큰')).toBeVisible();
    await page.waitForTimeout(400);
    await page.screenshot({ path: join(SHOTS, `${w}_tokens_created.png`), fullPage: true });
    expect.soft(await defects(page, w), `발급 직후 @${w}px`).toEqual([]);
    await page.context().close();
  }
});

test('저장된 심의 — 진행 표시는 완료, 화자는 이름', async ({ browser }) => {
  for (const w of [1440, 390]) {
    const page = await login(browser, w);
    await page.goto('/deliberate');
    await page.waitForLoadState('networkidle');
    test.skip((await page.getByText('어떤 판단이 필요하세요?').count()) === 0, '이 권한 층은 심의가 없다');
    if (w < 900) await page.getByRole('button', { name: '사이드바 열기' }).click();
    // 좁은 화면에선 서랍 위 항목을 실제로 누른다 — 배경이 서랍과 같은 층이라 클릭을 가로채던 회귀를 여기서 잡았다
    await page.getByText('배터리 스웰링 대응 심의').first().click({ timeout: 10000 });
    await page.waitForTimeout(800);
    // 되살린 심의는 단계를 못 찾아 전부 빈 점이었다 — 이제 남은 단계가 모두 완료다
    const steps = page.locator('.dv-step');
    expect(await steps.count()).toBeGreaterThan(0);
    expect(await page.locator('.dv-step:not(.done)').count()).toBe(0);
    await page.screenshot({ path: join(SHOTS, `${w}_delib-saved.png`), fullPage: true });
    expect.soft(await defects(page, w), `저장된 심의 @${w}px`).toEqual([]);
    await page.context().close();
  }
});

test('배선 설정 — 앱 목록이 아니라 사용자 관리 맨 위, 헤더 관리 옆에 건수', async ({ browser }) => {
  test.skip(TIER !== 'admin', '관리자만');
  const page = await login(browser, 1440);
  await page.goto('/apps');
  await page.waitForLoadState('networkidle');
  await expect(page.locator('.setup-requests')).toHaveCount(0);
  const n = (await (await page.request.get('/setup/requests')).json()).items.length as number;
  test.skip(n === 0, '임시 포털에 남은 배선이 없다');
  await expect(page.locator('.hdr-admin .hdr-badge')).toHaveText(String(n));
  await page.goto('/admin/users');
  await page.waitForLoadState('networkidle');
  await expect(page.locator('.setup-requests')).toBeVisible();
  // manual 항목 하나를 펴서 '확인함' — 상자에서 빠지고 헤더 건수가 하나 준다
  const manual = page.locator('.setup-requests li').filter({ hasText: '확인 필요' }).first();
  if (await manual.count()) {
    await manual.locator('button').first().click();
    await page.getByRole('button', { name: '했습니다 — 확인함' }).click();
    await expect(page.locator('.hdr-admin .hdr-badge')).toHaveText(String(n - 1));
    await expect(page.getByText(/확인한 항목 \d+건/)).toBeVisible();
    await page.screenshot({ path: join(SHOTS, '1440_setup-acked.png'), fullPage: true });
    // 되돌려 둔다 — 같은 임시 포털로 다른 시험이 이어 돈다
    await page.getByText(/확인한 항목 \d+건/).click();
    await page.getByRole('button', { name: '되돌리기' }).first().click();
    await expect(page.locator('.hdr-admin .hdr-badge')).toHaveText(String(n));
  }
  await page.context().close();
});

test('업데이트 본 날짜 — 브라우저 저장소가 비어도 서버 원장으로 판정한다', async ({ browser }) => {
  const page = await login(browser, 1440, { suppressPopup: false });
  const csrf = (await page.context().cookies()).find((c) => c.name === 'hwax_csrf')?.value ?? '';
  let seen = (await (await page.request.get('/changelog/seen')).json()).seen as string;
  if (!seen) {
    await page.request.post('/changelog/seen', { data: { date: '2026-01-01' }, headers: { 'X-CSRF-Token': csrf } });
    seen = '2026-01-01';
  }
  const latest = (await (await page.request.get('/changelog?limit=1')).json()).latest as string;
  const me = await (await page.request.get('/auth/me')).json();
  // 새 PC 처럼 — 이 브라우저의 기록을 지우고 다시 연다
  await page.evaluate(() => {
    for (const k of Object.keys(localStorage)) if (k.startsWith('hwax.changelog.seen')) localStorage.removeItem(k);
  });
  await page.goto('/apps');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(600);
  if (seen < latest) {
    // 서버에 옛 날짜가 있으니 그 뒤 것이 뜬다(종전: 처음 온 사람으로 보고 안 띄웠다)
    await expect(page.locator('.cl-card')).toBeVisible();
  } else {
    // 다 봤으면 안 뜨고, '처음 온 사람' 경로(브라우저에 latest 를 적는 것)도 타지 않는다
    await expect(page.locator('.cl-card')).toHaveCount(0);
    expect(await page.evaluate((e) => localStorage.getItem(`hwax.changelog.seen.${e}`), me.email)).toBeNull();
  }
  await page.context().close();
});

test('대화상자 — 네이티브 dialog: 열면 안으로 포커스, Esc 로 닫으면 연 버튼으로 돌아오고 스크롤 잠금이 풀린다', async ({ browser }) => {
  const page = await login(browser, 1440);
  await page.goto('/');
  await page.waitForLoadState('networkidle');
  const pill = page.getByRole('button', { name: '전문가', exact: true });
  test.skip((await pill.count()) === 0, '이 권한 층은 전문가 챗이 없다');
  await pill.click();
  const picker = page.getByRole('dialog', { name: '전문가 고르기' });
  await expect(picker).toBeVisible();
  expect(await page.evaluate(() => !!document.activeElement?.closest('dialog[open]'))).toBe(true);
  expect(await page.evaluate(() => document.body.style.overflow)).toBe('hidden');
  await page.keyboard.press('Escape');
  await expect(page.locator('dialog[open]')).toHaveCount(0);
  await expect(pill).toBeFocused();
  expect(await page.evaluate(() => document.body.style.overflow)).toBe('');

  // 고르기 → 전체 조직도로 갈아타고 Esc — 남는 대화상자·잠금이 없어야 한다
  await pill.click();
  await page.getByRole('button', { name: /전체 조직도 열기/ }).click();
  await expect(page.getByRole('dialog', { name: '전문가 조직도' })).toBeVisible();
  await expect(page.locator('dialog[open]')).toHaveCount(1);
  await page.waitForTimeout(500); // 나타나기 애니메이션(0.18s)이 끝난 뒤
  await page.screenshot({ path: join(SHOTS, '1440_dialog-org.png') });
  await page.keyboard.press('Escape');
  await expect(page.locator('dialog[open]')).toHaveCount(0);
  expect(await page.evaluate(() => document.body.style.overflow)).toBe('');
  await page.context().close();
});
