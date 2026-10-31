# StepForge 반입 폼을 헤드리스 브라우저에서 진짜 입력창(Composer)으로 눌러 보낸 본문을 본다 — 서버는 띄우지 않는다(가짜 fetch, docs/upload)
"""왜 — 업로드 목적지 폼은 API 계층까지만 실증했다(docs/upload 체크리스트 '브라우저에서 폼을 실제로 눌러본 적은 없다'). 폼이 무엇을
보내는지는 화면에서만 갈린다.

  · 새 과제 — 과제명 · 단계 · 특이사항은 펴 있고 과제번호 · 부서 · 해석목적은 접힌 칸(<details>)에 있다. 다 채워 보내면 본문에 여섯이
    그대로 실린다. 담당자는 묻지 않고 로그인한 사람(이메일)이라고 안내한다.
  · 기존 과제 — 과제 목록에서 고른 project_id 만 간다. 과제 메타는 남의 기록이라 덮지 않는다(D-12) — 메타 칸 · 담당자 안내가 없다.

test_chat_ppt_in_browser 와 같은 틀(진짜 Composer · 가짜 fetch, esbuild 로 묶어 빈 문서에 올린다).
"""
import json
import subprocess

import pytest

from tests.test_delib_stream_in_browser import _BUILD, FE, pytestmark  # noqa: F401 — 같은 도구가 없으면 같이 건너뛴다

_HARNESS = r"""
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { AuthContext } from '__FE__/src/auth/AuthContext';
import { ChatProvider } from '__FE__/src/state/ChatContext';
import { Composer } from '__FE__/src/components/chat/Composer';

(window as unknown as { __mount: () => void }).__mount = () => {
  const user = { subject: 'u1@corp.example', email: 'u1@corp.example', display_name: 'U', groups: [] };
  createRoot(document.getElementById('root')!).render(
    <AuthContext.Provider
      value={{ user, status: 'authenticated', login: () => undefined, logout: async () => undefined, refresh: async () => undefined }}
    >
      <MemoryRouter>
        <ChatProvider storagePrefix="hwax.chat" serverKind="chat">
          <Composer />
        </ChatProvider>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
};
"""

# 가짜 백엔드 — 올리기(스테이징 상자) · StepForge 과제 목록 · 보내기. 부른 차례를 __calls 에 적는다.
_STUB = r"""
(() => {
  window.__calls = [];
  const json = (body, status = 200) =>
    Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }));
  window.fetch = (url, init = {}) => {
    const u = String(url);
    const method = (init.method || 'GET').toUpperCase();
    window.__calls.push({ url: u, method, body: typeof init.body === 'string' ? JSON.parse(init.body) : null });
    if (u === '/agent/upload' && method === 'POST') {
      const f = init.body.get('file');
      return json({ staging_id: 'st1', filename: f.name, size: f.size, ext: 'step', content_type: '',
                    destinations: [{ id: 'stepforge', label: 'StepForge — 3D 모델 반입' }] });
    }
    if (u === '/agent/upload/destinations/stepforge/projects')
      return json({ projects: [{ id: 'p-12', name: '힌지 낙하' }, { id: 'p-7', name: '미드프레임 강성' }] });
    if (u === '/agent/upload/dispatch') {
      const b = JSON.parse(init.body);
      return json(b.project_id
        ? { stage: 'dispatched', destination: 'stepforge', project_id: b.project_id, created_project: false, job_id: 'j-2', kind: b.run }
        : { stage: 'dispatched', destination: 'stepforge', project_id: 'p-99', created_project: true, job_id: 'j-1', kind: b.run });
    }
    if (u === '/agent/conversations' && method === 'GET') return json({ conversations: [] });
    return json({ detail: 'stub: no route ' + u }, 404);
  };
})();
"""

_DRIVE = r"""
const { createRequire } = require('module');
const path = require('path');
const [FE, OUT] = process.argv.slice(2);
const { chromium } = createRequire(path.join(FE, 'package.json'))('@playwright/test');

async function open(browser) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  page.setDefaultTimeout(10000);
  page.__errors = [];
  page.on('pageerror', (e) => page.__errors.push(String(e)));
  await page.route('http://harness.invalid/**', (r) =>
    r.fulfill({ contentType: 'text/html', body: '<!doctype html><html><body><div id="root"></div></body></html>' }));
  await page.goto('http://harness.invalid/');
  await page.addScriptTag({ path: path.join(OUT, 'stub.js') });
  await page.addScriptTag({ path: path.join(OUT, 'bundle.js') });
  await page.evaluate(() => window.__mount());
  return page;
}
// 입력창의 '+'(파일 입력)로 STEP 하나를 고르고 '어디로 보낼까요' 에서 StepForge 를 누른다
async function toStepForge(page) {
  await page.locator('input[type=file]').setInputFiles({ name: 'frame.step', mimeType: 'application/octet-stream',
    buffer: Buffer.from('ISO-10303-21;\nHEADER;\nENDSEC;\n') });
  await page.getByText('어디로 보낼까요').waitFor();
  await page.getByRole('button', { name: /StepForge/ }).click();
  await page.getByText('StepForge 반입', { exact: true }).waitFor();
}
// 칸 이름(라벨의 첫 글자 마디)이 꼭 그것인 칸 — 라벨 글에는 안의 select 선택지까지 섞여 '포함' 으로 찾으면 다른 칸이 걸린다
const field = (page, label) =>
  page.locator(`xpath=//div[contains(@class,'upl-panel')]//label[normalize-space(text()[1])='${label}']`).locator('input, select');
const sent = (page) => page.evaluate(() => window.__calls.filter((c) => c.url === '/agent/upload/dispatch').map((c) => c.body));
const notes = (page) => page.evaluate(() => Array.from(document.querySelectorAll('.upl-panel .upl-note')).map((e) => e.textContent));

const SCENARIOS = {
  // 새 과제 — 펴 있는 셋 + 접힌 셋을 다 채우고 작업을 바꿔 보낸다
  async new_project(browser) {
    const page = await open(browser);
    await toStepForge(page);
    const before = {
      name: await field(page, '과제명').inputValue(),
      stages: await field(page, '단계').locator('option').allTextContents(),
      folded: await page.locator('details.upl-more').evaluate((d) => !d.open),
      notes: await notes(page),
    };
    await field(page, '과제명').fill('힌지 낙하 1.5m');
    await field(page, '단계').selectOption('DV');
    await field(page, '특이사항').fill('힌지 브래킷만, 배터리 제외');
    await field(page, '반입 후 작업').selectOption('pipeline');
    await page.locator('details.upl-more > summary').click();
    await field(page, '과제번호').fill('HINGE-DROP-001');
    await field(page, '부서').fill('구조해석');
    await field(page, '해석목적').fill('낙하 후 힌지 크랙 평가');
    await page.getByRole('button', { name: 'StepForge 로 보내기' }).click();
    await page.getByText('✓ StepForge 반입').waitFor();
    return { before, sent: await sent(page), done: await page.locator('.upl-done').textContent(), errors: page.__errors };
  },
  // 기존 과제 — 목록에서 둘째를 골라 보낸다. 메타 칸 · 담당자 안내는 없다
  async existing_project(browser) {
    const page = await open(browser);
    await toStepForge(page);
    await field(page, '과제').selectOption('existing');
    await page.locator('.upl-panel option', { hasText: '미드프레임 강성' }).waitFor({ state: 'attached' });
    const shown = {
      fields: await page.locator('.upl-panel label').evaluateAll((ls) => ls.map((l) => l.firstChild.textContent.trim())),
      details: await page.locator('details.upl-more').count(),
      notes: await notes(page),
    };
    await field(page, '기존 과제').selectOption('p-7');
    await page.getByRole('button', { name: 'StepForge 로 보내기' }).click();
    await page.getByText('✓ StepForge 반입').waitFor();
    const calls = await page.evaluate(() => window.__calls.map((c) => `${c.method} ${c.url}`));
    return { shown, sent: await sent(page), done: await page.locator('.upl-done').textContent(), calls, errors: page.__errors };
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
    out = tmp_path_factory.mktemp("uploadform")
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


def test_새_과제는_펴진_셋과_접힌_셋을_다_실어_보내고_담당자는_로그인한_사람이다(seen):
    s = seen("new_project")
    b = s["before"]
    assert b["name"] == "frame", "과제명은 파일 이름(확장자 뺌)으로 시작한다"
    assert b["stages"] == ["(미지정)", "선행", "DV", "PV", "양산"], "단계는 고정 목록(백엔드 _STEP_STAGES 와 같다 — D-13)"
    assert b["folded"] is True, "과제번호 · 부서 · 해석목적은 접혀 있다"
    assert any("담당자는 u1@corp.example 로 자동 기입됩니다" in n for n in b["notes"]), b["notes"]
    assert s["sent"] == [{
        "staging_id": "st1", "filename": "frame.step", "destination": "stepforge", "run": "pipeline",
        "project_name": "힌지 낙하 1.5m", "stage": "DV", "note": "힌지 브래킷만, 배터리 제외",
        "code": "HINGE-DROP-001", "department": "구조해석", "purpose": "낙하 후 힌지 크랙 평가",
    }], s["sent"]
    assert "과제 p-99 (새로 만듦)" in s["done"] and "잡 j-1 · pipeline 진행 중" in s["done"], s["done"]


def test_기존_과제는_project_id_만_보내고_메타를_묻지_않는다(seen):
    s = seen("existing_project")
    assert s["shown"]["fields"] == ["과제", "기존 과제", "반입 후 작업"], s["shown"]
    assert s["shown"]["details"] == 0, "접힌 메타 칸도 없다 — 기존 과제의 기록을 덮지 않는다(D-12)"
    assert not any("담당자" in n for n in s["shown"]["notes"]), s["shown"]["notes"]
    assert s["sent"] == [{"staging_id": "st1", "filename": "frame.step", "destination": "stepforge", "run": "parse",
                          "project_id": "p-7"}], s["sent"]
    assert "GET /agent/upload/destinations/stepforge/projects" in s["calls"], "기존 과제를 고를 때 목록을 부른다"
    assert "과제 p-7 (기존에 추가)" in s["done"], s["done"]
