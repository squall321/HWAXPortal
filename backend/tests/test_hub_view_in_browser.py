# '개인 Claude 보기' 칸의 목적 고르기를 헤드리스 브라우저에 올려 — 진짜 포털 창구가 낸 답으로 목록 · 거르기 · 여럿 고르기 · 저장 · 좁은 화면을 본다(docs/mcp-modernize M3)
"""왜 — 화면은 `/auth/access/view` 답의 꼴(purpose_options · purpose_supported)에 기대고, 그 꼴이 바뀌면 타입 검사는 지나도 화면은 빈칸이나 예외가 된다.
그래서 답을 손으로 짓지 않고 **진짜 포털 창구**(게이트웨이 전송만 가짜 — test_hub_view 의 env)가 낸 JSON 을 그대로 먹인다. 저장(PUT)도 화면이 보낸
몸통을 진짜 창구에 그대로 넣어 받은 답을 돌려준다. 서버는 띄우지 않는다 — 칸 컴포넌트를 esbuild 로 묶어 빈 문서에 올리고 fetch 만 바꾼다
(test_admin_pages_in_browser 와 같은 길). 도구는 프론트가 이미 가진 것만 쓴다. 없으면 건너뛴다(운영 박스).
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from tests.test_admin_pages_in_browser import _BUILD
from tests.test_hub_view import PURPOSE_MAP, TOOLS_MAP, _login, env  # noqa: F401 — env 는 픽스처다

ROOT = Path(__file__).resolve().parents[2]
FE = ROOT / "frontend"

pytestmark = pytest.mark.skipif(
    not shutil.which("node") or not (FE / "node_modules/@playwright/test").exists() or not (FE / "node_modules/vite").exists(),
    reason="node 또는 frontend node_modules(@playwright/test · vite) 가 없다 — 화면을 올려 볼 수 없다",
)

_HARNESS = r"""
import { createRoot } from 'react-dom/client';
import HubViewPanel from '__FE__/src/components/HubViewPanel';

(window as unknown as { __mount: () => void }).__mount = () => {
  createRoot(document.getElementById('root')!).render(<HubViewPanel rev={0} onChange={(v) => { (window as any).__changed.push(v.mode); }} />);
};
"""

# 가짜 포털 창구 — GET 은 진짜 창구의 답(window.__get), PUT 은 몸통을 적고 진짜 창구가 그 몸통에 낸 답(window.__put[몸통])을 돌려준다.
_STUB = r"""
(() => {
  window.__calls = [];
  window.__changed = [];
  const json = (body, status = 200) =>
    Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }));
  window.fetch = (url, init) => {
    const u = String(url);
    const method = ((init && init.method) || 'GET').toUpperCase();
    window.__calls.push(method + ' ' + u + (init && init.body ? ' ' + init.body : ''));
    if (u === '/auth/access/view' && method === 'GET') return json(window.__get);
    if (u === '/auth/access/view' && method === 'PUT') {
      const hit = window.__put[init.body];
      return hit ? json(hit.body, hit.status) : json({ detail: 'stub: 모르는 몸통 ' + init.body }, 400);
    }
    return json({ detail: 'stub: no route ' + u }, 404);
  };
})();
"""

_DRIVE = r"""
const { createRequire } = require('module');
const path = require('path');
const [FE, OUT] = process.argv.slice(2);
const { chromium } = createRequire(path.join(FE, 'package.json'))('@playwright/test');

async function open(browser, data, width) {
  const page = await browser.newPage({ viewport: { width, height: 900 } });
  page.setDefaultTimeout(10000);
  page.__errors = [];
  page.on('pageerror', (e) => page.__errors.push(String(e)));
  await page.route('http://harness.invalid/**', (r) =>
    r.fulfill({ contentType: 'text/html', body: '<!doctype html><html><body><div id="root"></div></body></html>' }));
  await page.goto('http://harness.invalid/');
  await page.addScriptTag({ path: path.join(OUT, 'stub.js') });
  await page.addScriptTag({ path: path.join(OUT, data) });
  await page.addScriptTag({ path: path.join(OUT, 'bundle.js') });
  // 캡처가 실제 화면처럼 보이게 포털의 토큰 · 전역 · 토큰 화면 스타일을 얹는다(묶음은 CSS 를 비운다 — 판정은 스타일과 상관없다)
  for (const css of ['tokens.css', 'globals.css', 'tokenpage.css']) await page.addStyleTag({ path: path.join(FE, 'src/styles', css) });
  await page.evaluate(() => window.__mount());
  await page.waitForSelector('.hub-view-modes');
  return page;
}
const look = (page) => page.evaluate(() => ({
  text: document.getElementById('root').innerText,
  rows: Array.from(document.querySelectorAll('.hub-view-purpose')).map((l) => ({
    title: l.querySelector('b').textContent, count: l.querySelector('.hub-num').textContent,
    disabled: l.querySelector('input').disabled, checked: l.querySelector('input').checked,
    apps: (l.querySelector('.hub-view-papps') || { textContent: '' }).textContent })),
  purposeRadio: (() => { const r = document.querySelector('input[name=hub-view-mode][value=purpose]'); return { disabled: r.disabled, checked: r.checked }; })(),
  overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  calls: [...window.__calls], changed: [...window.__changed],
}));

const SCENARIOS = {
  async pick(browser) {
    const page = await open(browser, 'data-ok.js', 1280);
    await page.check('input[name=hub-view-mode][value=purpose]');
    await page.waitForSelector('.hub-view-purpose');
    const listed = await look(page);
    await page.fill('.hub-view-filter', 'VOC');
    const filtered = await look(page);
    await page.fill('.hub-view-filter', '');
    await page.locator('.hub-view-purpose', { hasText: '낙하 해석 준비' }).locator('input').check();
    await page.locator('.hub-view-purpose', { hasText: 'VOC 훑기' }).locator('input').check();
    await page.screenshot({ path: path.join(OUT, 'purpose-pick.png'), fullPage: true });
    await page.getByRole('button', { name: '보기 저장' }).click();
    await page.getByText('저장했습니다 — 새로 연결할 때부터 적용됩니다.').waitFor();
    const saved = await look(page);
    return { listed, filtered, saved, errors: page.__errors };
  },
  async narrow(browser) {
    const page = await open(browser, 'data-ok.js', 390);
    await page.check('input[name=hub-view-mode][value=purpose]');
    await page.waitForSelector('.hub-view-purpose');
    await page.screenshot({ path: path.join(OUT, 'purpose-narrow.png'), fullPage: true });
    return { ...(await look(page)), errors: page.__errors };
  },
  async unsupported(browser) {
    const page = await open(browser, 'data-old.js', 1280);
    await page.waitForTimeout(100);
    return { ...(await look(page)), errors: page.__errors };
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


def test_목적_보기를_골라_저장하는_화면(env, tmp_path):  # noqa: F811 — env 픽스처
    c, gw = env
    gw.tools_map = PURPOSE_MAP
    h = _login(c, "boss@corp.com")
    got = c.get("/auth/access/view").json()
    body = json.dumps({"mode": "purpose", "areas": [], "purposes": ["drop-prep", "voc-scan"]}, separators=(",", ":"))
    put = c.put("/auth/access/view", content=body, headers={**h, "Content-Type": "application/json"})
    assert put.status_code == 200, put.text
    gw.tools_map = TOOLS_MAP                                   # 목적 보기를 모르는 게이트웨이
    old = c.get("/auth/access/view").json()
    assert old["mode"] == "purpose" and old["purpose_supported"] is False
    old = {**old, "mode": "full", "purposes": []}              # 목적을 저장한 적 없는 사람의 화면
    out = tmp_path
    (out / "harness.tsx").write_text(_HARNESS.replace("__FE__", str(FE)), encoding="utf-8")
    for name, text in (("build.cjs", _BUILD), ("stub.js", _STUB), ("drive.cjs", _DRIVE)):
        (out / name).write_text(text, encoding="utf-8")
    puts = {body: {"status": 200, "body": put.json()}}
    (out / "data-ok.js").write_text(f"window.__get = {json.dumps(got)};\nwindow.__put = {json.dumps(puts)};\n", encoding="utf-8")
    (out / "data-old.js").write_text(f"window.__get = {json.dumps(old)};\nwindow.__put = {{}};\n", encoding="utf-8")
    r = subprocess.run(["node", "build.cjs", str(FE), str(out)], cwd=str(out), capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, "화면을 묶지 못했다:\n" + r.stdout + r.stderr
    r = subprocess.run(["node", "drive.cjs", str(FE), str(out)], cwd=str(out), capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
    seen = json.loads(r.stdout)
    if "skip" in seen:
        pytest.skip("헤드리스 브라우저를 띄우지 못했다(playwright 브라우저 미설치) — " + seen["skip"])
    for name in ("pick", "narrow", "unsupported"):
        assert "failed" not in seen[name], f"시나리오 {name} 이 끝까지 돌지 못했다:\n{seen[name].get('failed')}"
        assert not seen[name]["errors"], f"화면이 예외를 던졌다: {seen[name]['errors']}"

    pick = seen["pick"]
    rows = pick["listed"]["rows"]
    assert [x["title"] for x in rows] == ["낙하 해석 준비", "VOC 훑기", "정본 지식 찾기", "다른 박스 전용"], "여러 앱을 잇는 목적이 먼저"
    assert rows[0]["count"] == "3" and "StepForge · SmartTwin" in rows[0]["apps"], rows[0]
    assert rows[3]["disabled"] is True and "이 박스에 없음" in pick["listed"]["text"], "이 박스에 단계가 없는 목적은 고를 수 없다"
    assert [x["title"] for x in pick["filtered"]["rows"]] == ["VOC 훑기"], "거르기는 제목 · 요약 · 앱 이름에서"
    assert f"PUT /auth/access/view {body}" in pick["saved"]["calls"], pick["saved"]["calls"]
    assert "목적 · 지금" in pick["saved"]["text"].replace("\n", " ") or "목적 · 지금" in pick["saved"]["text"]
    assert pick["saved"]["changed"][-1] == "purpose", "토큰 화면의 고정 칸이 새 보기를 받는다(onChange)"
    assert sum(1 for x in pick["saved"]["rows"] if x["checked"]) == 2
    assert not [c for c in pick["saved"]["calls"] if "list_tool_apps" in c], "목적 목록은 포털 창구 한 번으로 — 게이트웨이 목록 도구를 부르지 않는다"

    narrow = seen["narrow"]
    assert narrow["overflow"] <= 0, f"좁은 화면(390px)에서 가로로 넘친다({narrow['overflow']}px)"

    old_seen = seen["unsupported"]
    assert old_seen["purposeRadio"] == {"disabled": True, "checked": False}
    assert "목적 보기를 모릅니다" in old_seen["text"] and not old_seen["rows"]
    for png in ("purpose-pick.png", "purpose-narrow.png"):
        assert (out / png).stat().st_size > 1000
        if os.environ.get("HWAX_SHOT_DIR"):                    # 사람이 볼 캡처를 남기려면 그 자리를 준다(리포 안에는 남기지 않는다)
            shutil.copy(out / png, Path(os.environ["HWAX_SHOT_DIR"]) / png)
