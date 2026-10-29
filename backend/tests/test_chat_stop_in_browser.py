# 챗 중지 단추가 읽기 루프를 기다리지 않고 화면을 곧바로 푸는지 헤드리스 브라우저에서 실제 ChatProvider 로 본다(docs/request-1029 P-1 ③)
"""10-29 cae00 QA — 숨은 탭에서 화면이 '생각 중' 에 25분 멈췄고 중지 단추도 듣지 않았다(OT-07). 종전 중지는 abort 만 했고, 화면은
읽기 루프가 AbortError 로 거절된 뒤에야 풀렸다 — 루프가 멈춰 있으면 그 거절이 늦거나 오지 않는다. 가짜 fetch 의 본문은 abort 에도
닫히지 않아(test_delib_stream_in_browser 의 _STUB) 바로 그 꼴이다. 중지가 화면을 먼저 풀면 다음 발화를 곧바로 보낼 수 있으므로, 늦게 온
옛 스트림의 끝이 새 스트림의 상태를 지우지 않는지도 본다.
"""
import json
import subprocess

import pytest

from tests.test_delib_stream_in_browser import _BUILD, _HARNESS, _STUB, FE, pytestmark  # noqa: F401 — 같은 도구가 없으면 같이 건너뛴다

_DRIVE = r"""
const { createRequire } = require('module');
const path = require('path');
const [FE, OUT] = process.argv.slice(2);
const { chromium } = createRequire(path.join(FE, 'package.json'))('@playwright/test');

const frame = (event, data) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
async function open(browser) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
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
const push = (page, text) => page.evaluate((t) => window.__push(t), text);
const streaming = (page) => page.evaluate(() => document.getElementById('streaming').textContent);
const settled = (page) => page.waitForFunction(() => document.getElementById('streaming').textContent === 'false', null,
  { timeout: 3000 });
const errorTitle = (page) => page.evaluate(() => (document.querySelector('.chat-error-title') || {}).textContent || '');

const SCENARIOS = {
  // 부분 답을 받은 뒤 중지 — 본문은 남고 화면이 풀린다. 이어서 새 발화를 보내고, 옛 스트림의 늦은 done 을 흘린다.
  async stuck(browser) {
    const page = await open(browser);
    await page.locator('#send').click();
    await page.waitForFunction(() => typeof window.__push === 'function');
    await push(page, frame('token', { delta: '부분 답' }));
    await page.getByText('부분 답').first().waitFor();
    await page.locator('#stop').click();
    await settled(page);
    const after_stop = { aborted: await page.evaluate(() => window.__aborted), error: await errorTitle(page),
                         text: await page.evaluate(() => document.body.textContent) };
    await page.evaluate(() => { window.__old = { push: window.__push, end: window.__end }; });
    await page.locator('#send').click();
    await page.waitForFunction(() => window.__push !== window.__old.push);
    await page.evaluate((f) => { window.__old.push(f); window.__old.end(); }, frame('done', {}));
    await page.waitForTimeout(300);
    const while_new = await streaming(page);
    await push(page, frame('result', { type: 'text', content: '새 답' }));
    await push(page, frame('done', {}));
    await page.evaluate(() => window.__end());
    await settled(page);
    return { after_stop, while_new, final: await page.evaluate(() => document.body.textContent), errors: page.__errors };
  },
  // 첫 프레임도 오기 전에 중지 — '취소됨'(화면은 '중단되었습니다')으로 풀린다
  async before_first(browser) {
    const page = await open(browser);
    await page.locator('#send').click();
    await page.waitForFunction(() => typeof window.__push === 'function');
    await page.locator('#stop').click();
    await settled(page);
    return { error: await errorTitle(page), errors: page.__errors };
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
    out = tmp_path_factory.mktemp("stop")
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


def test_중지는_읽기_루프가_멈춰_있어도_화면을_곧바로_푼다(seen):
    s = seen("stuck")["after_stop"]
    assert s["aborted"] is True, "중지가 요청을 끊지 않았다"
    assert "부분 답" in s["text"] and not s["error"], "받은 부분 답은 그대로 두고 오류 상자를 띄우지 않는다(종전과 같다)"


def test_중지_뒤_새_발화는_옛_스트림의_늦은_끝에_지워지지_않는다(seen):
    s = seen("stuck")
    assert s["while_new"] == "true", "옛 스트림의 늦은 done 이 새 스트림의 '도는 중' 을 풀었다"
    assert "새 답" in s["final"]


def test_첫_프레임_전에_중지하면_중단으로_풀린다(seen):
    assert "중단되었습니다" in seen("before_first")["error"], "'취소됨' 은 화면에서 '중단되었습니다' 다(lib/chatErrors)"
