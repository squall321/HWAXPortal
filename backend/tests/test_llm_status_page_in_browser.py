# 'LLM · GPU 현황' 화면을 헤드리스 브라우저에 올려 — 실제 수집기가 낸 스냅숏으로 카드 · 작은 그래프 · 모름 줄 · 수집기 장애 띠를 본다(docs/ops-dashboard)
"""왜 — 화면은 수집기 답의 꼴에 기대고(값마다 {value, at, source, error, stale}), 그 꼴이 바뀌면 타입 검사는 지나도 화면은 빈칸이나 예외가 된다.
그래서 스냅숏을 손으로 짓지 않고 **실제 수집기**(test_llm_status_collector 의 가짜 vLLM · 에이전트 · 라우터 앞에서)가 낸 JSON 을 그대로 먹인다.
서버는 띄우지 않는다 — 페이지 컴포넌트를 esbuild 로 묶어 빈 문서에 올리고 fetch 만 바꾼다(test_admin_pages_in_browser 와 같은 길).
도구는 프론트가 이미 가진 것만 쓴다(esbuild · @playwright/test). 없으면 건너뛴다(운영 박스).
"""
import json
import re
import shutil
import subprocess
import time
from pathlib import Path

import pytest
from tests.test_admin_pages_in_browser import _BUILD
from tests.test_llm_status_collector import (
    KEY,
    C,
    Clock,
    FakeJson,
    FakeVllm,
    _collector,
    _free_port,
)

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
import LlmStatusPage from '__FE__/src/pages/admin/LlmStatusPage';

(window as unknown as { __mount: (admin: boolean) => void }).__mount = (admin) => {
  const user = { subject: 'root@corp.example', email: 'root@corp.example', display_name: 'Root', groups: admin ? ['portal-admin'] : [] };
  createRoot(document.getElementById('root')!).render(
    <AuthContext.Provider
      value={{ user, status: 'authenticated', login: () => undefined, logout: async () => undefined, refresh: async () => undefined }}
    >
      <MemoryRouter initialEntries={['/admin/llm-status']}>
        <LlmStatusPage />
      </MemoryRouter>
    </AuthContext.Provider>,
  );
};
"""

# 가짜 포털 창구 — 스냅숏 · 시계열은 data.js 가 심는다(실제 수집기의 답). __fail 이 있으면 그 상태로 거절한다.
_STUB = r"""
(() => {
  window.__calls = [];
  window.__fail = null;
  const json = (body, status = 200) =>
    Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }));
  window.fetch = (url) => {
    const u = decodeURIComponent(String(url));
    window.__calls.push(u);
    if (u === '/auth/admin/llm-status') return window.__fail ? json({ detail: window.__fail.detail }, window.__fail.status) : json(window.__snap);
    if (u.startsWith('/auth/admin/llm-status/series?')) {
      const q = new URLSearchParams(u.split('?')[1]);
      const k = q.get('target') + '|' + q.get('metric') + '|' + q.get('range');
      return window.__series[k] ? json(window.__series[k]) : json({ detail: 'no series ' + k }, 404);
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

async function open(browser, { seed = '', admin = true } = {}) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  page.setDefaultTimeout(10000);
  page.__errors = [];
  page.on('pageerror', (e) => page.__errors.push(String(e)));
  await page.route('http://harness.invalid/**', (r) =>
    r.fulfill({ contentType: 'text/html', body: '<!doctype html><html><body><div id="root"></div></body></html>' }));
  await page.goto('http://harness.invalid/');
  await page.addScriptTag({ path: path.join(OUT, 'stub.js') });
  await page.addScriptTag({ path: path.join(OUT, 'data.js') });
  if (seed) await page.evaluate(seed);
  await page.addScriptTag({ path: path.join(OUT, 'bundle.js') });
  await page.evaluate((a) => window.__mount(a), admin);
  return page;
}
const look = (page) => page.evaluate(() => ({
  text: document.getElementById('root').innerText,
  cards: Array.from(document.querySelectorAll('.lls-card h3')).map((h) => h.textContent),
  polylines: document.querySelectorAll('.lls-spark polyline').length,
  styled: document.querySelectorAll('#root [style]').length,
  replicaRows: Array.from(document.querySelectorAll('.lls-replicas tbody tr')).map((tr) => tr.innerText),
  badges: Array.from(document.querySelectorAll('.lls-badge')).map((b) => b.textContent),
  alerts: Array.from(document.querySelectorAll('[role=alert]')).map((a) => a.innerText),
  calls: [...window.__calls],
}));

const SCENARIOS = {
  async ok(browser) {
    const page = await open(browser);
    await page.waitForSelector('.lls-card');
    await page.waitForFunction(() => document.querySelectorAll('.lls-spark polyline').length > 0);
    const seen = await look(page);
    await page.screenshot({ path: path.join(OUT, 'ok.png'), fullPage: true });
    return { ...seen, errors: page.__errors };
  },
  async down(browser) {
    const page = await open(browser, { seed: `window.__fail = { status: 502, detail: '수집기가 답하지 않는다(ConnectError) — 수집기가 떠 있는지 본다' }` });
    await page.waitForSelector('[role=alert]');
    return { ...(await look(page)), errors: page.__errors };
  },
  async off(browser) {
    const page = await open(browser, { seed: `window.__fail = { status: 503, detail: 'LLM/GPU 현황 수집기가 꺼져 있다 — infra/.env 에 LLM_STATUS=1' }` });
    await page.waitForSelector('[role=alert]');
    return { ...(await look(page)), errors: page.__errors };
  },
  async later_down(browser) {
    const page = await open(browser);
    await page.waitForSelector('.lls-card');
    await page.evaluate(() => { window.__fail = { status: 502, detail: '수집기가 답하지 않는다(ReadTimeout)' }; });
    await page.getByRole('button', { name: '새로 고침' }).click();
    await page.waitForSelector('[role=alert]');
    return { ...(await look(page)), errors: page.__errors };
  },
  async not_admin(browser) {
    const page = await open(browser, { admin: false });
    await page.getByText('관리자(portal-admin)만').waitFor();
    await page.waitForTimeout(150);
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


def _real_data(tmp: Path) -> tuple[dict, dict]:
    """실제 수집기가 가짜 서버들 앞에서 낸 스냅숏 · 시계열 — 25주기(15초씩, 끝이 지금)를 시계를 끼워 돌린다."""
    glm, chat = FakeVllm(key=KEY), FakeVllm(model="qwen-test")
    r1, r2 = FakeVllm(model="qwen-test"), FakeVllm(model="qwen-test", max_len=1_010_000)
    agent = FakeJson({"/health": (200, {"status": "ok", "delib_active": 2, "delib_queued": 1, "delib_seats_running": 12,
                                        "delib_paused": False, "routine_active": 1, "routine_parked": 0, "routine_max": 2,
                                        "review_active": 3, "card_review": {"active": 3, "limit": 8, "limit_reason": "normal"},
                                        "load": {"chat": {"active": 1, "slow": False, "ttft_ms": {"idle": {"n": 9, "p50": 850, "p95": 2100},
                                                                                                  "review": {"n": 3, "p50": 1900, "p95": 4000}}}},
                                        "chat_llm": {"enabled": True, "server": "127.0.0.1:18700", "model": "qwen-test",
                                                     "fallback": {"enabled": True, "count": 2, "last_at": 1.0}},
                                        "context_tokens": 200000, "model": "glm-test"})})
    rt = FakeJson({"/health": (200, {"status": "ok", "upstreams_total": 1, "upstreams_up": 1, "inflight": 2, "models": {"match": True}}),
                   "/stats": (200, [{"url": glm.base, "up": True, "reachable": True, "running": 2.0, "waiting": 1.0, "kv": 0.25,
                                     "inflight": 2, "sent": 40, "connect_fail": 0, "models": "ok"}])})
    dead = _free_port()
    start = time.time() - 25 * 15
    clock = Clock(start)
    try:
        coll = _collector(tmp, f"LLM_STATUS_TARGETS=GLM-1={glm.base},GLM-2=http://127.0.0.1:{dead}/v1,QWEN={chat.base},"
                               f"BAD=http://u:p@x.example:1/v1\nLLM_API_KEY={KEY}\nCHAT_LLM_BASE_URL={chat.base}\n"
                               f"LLM_STATUS_REPLICA_PORTS={r1.port},{r2.port}\nLLM_UPSTREAMS={glm.base}\nLLM_ROUTER_PORT={rt.port}\n"
                               f"LLM_STATUS_AGENT_URL=http://127.0.0.1:{agent.port}\nLLM_STATUS=1\n", clock=clock)
        for i in range(25):
            for f in (glm, chat, r1, r2):
                f.running, f.waiting = float(1 + i % 4), float(i % 3)
                f.step(gen=300 + 10 * i, ttft=0.07 if i % 5 else 0.4)
            if i == 20:                      # 5xx 둘 — 그 가운데 하나는 엔진 오류로 끝난 요청이다(둘에 함께 든다 — OD-30)
                glm.c["h5xx"] += 2
                glm.c["error"] += 1
            for st in coll.states.values():
                if st.t.problem is None:
                    coll.poll_vllm(st)
            coll.poll_agent(coll.agent)
            coll.poll_router(coll.router)
            clock.tick(15)
        clock.tick(-15)
        coll.store.maintain(clock(), force=True)
        snap = json.loads(C.dumps(coll.snapshot()))
        series = {}
        for t in snap["targets"]:
            for metric in ("running", "waiting"):
                for rng in ("1h", "24h"):
                    body, code = coll.series_view(t["id"], metric, rng)
                    if code == 200:
                        series[f"{t['id']}|{metric}|{rng}"] = json.loads(C.dumps(body))
        return snap, series
    finally:
        for f in (glm, chat, r1, r2, agent, rt):
            f.close()


@pytest.fixture(scope="module")
def seen(tmp_path_factory):
    out = tmp_path_factory.mktemp("llmst-page")
    snap, series = _real_data(tmp_path_factory.mktemp("llmst-data"))
    (out / "harness.tsx").write_text(_HARNESS.replace("__FE__", str(FE)), encoding="utf-8")
    for name, text in (("build.cjs", _BUILD), ("stub.js", _STUB), ("drive.cjs", _DRIVE)):
        (out / name).write_text(text, encoding="utf-8")
    (out / "data.js").write_text(f"window.__snap = {json.dumps(snap)};\nwindow.__series = {json.dumps(series)};\n", encoding="utf-8")
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
    scenario.snap = snap
    scenario.out = out
    return scenario


def test_서버_카드는_설정된_대상을_모두_보이고_모름에는_까닭을_글로_적는다(seen):
    s = seen("ok")
    assert s["cards"] == ["GLM-1", "GLM-2", "QWEN", "BAD"], "설정된 대상은 숨기지 않는다(못 읽은 것 · 설정이 틀린 것도)"
    text = s["text"]
    assert "수집기 도는 중" in text and "살아 있음" in text and "내려감" in text
    assert "연결 거부" in text, "내려간 서버의 까닭은 풍선 도움말이 아니라 글로 보인다"
    assert "설정 문제" in text and "계정(user@)이 있다" in text
    assert "://" not in text and KEY not in text, "주소는 호스트:포트만"
    assert s["styled"] == 0, "인라인 style 을 쓰지 않는다(토큰 CSS 클래스만 — docs/ui-refresh)"


def test_작은_그래프_분위수_어림_창_다름_표지가_실제_수집기_답으로_그려진다(seen):
    s = seen("ok")
    assert s["polylines"] >= 4, "도는 · 기다리는 요청의 1시간 · 24시간 그래프"
    assert "≈" in s["text"], "분위수는 어림 표지가 붙는다"
    assert any("창이 다르다" in b for b in s["badges"]) or any(b == "다름" for b in s["badges"]), s["badges"]
    assert "같은 모델의 창이 서버마다 다르다" in s["text"]
    assert len(s["replicaRows"]) == 2 and all("살아 있음" in r for r in s["replicaRows"]), s["replicaRows"]
    assert "1,010,000" in "".join(s["replicaRows"]), "복제본마다 창을 보인다(rolling 중에 섞인다)"
    calls = [c for c in s["calls"] if c.startswith("/auth/admin/llm-status/series?")]
    targets = {c.split("target=")[1].split("&")[0] for c in calls}
    assert targets == {"GLM-1", "GLM-2", "QWEN"}, "그래프는 카드(복제본 · 설정 문제 대상 빼고)만 받는다"


def test_오류는_HTTP_5xx_답과_오류로_끝난_요청을_따로_보인다(seen):
    """vLLM 은 스트리밍이 아닌 요청이 엔진 오류로 끝나면 500 으로도 답한다 — 더하면 한 요청을 두 번 센다(반대 검토 11-02 · OD-30)."""
    s = seen("ok")
    v = next(t for t in seen.snap["targets"] if t["id"] == "GLM-1")["values"]
    assert v["http_5xx_per_min"]["value"] == pytest.approx(0.4) and v["finished_error_per_min"]["value"] == pytest.approx(0.2), v
    assert re.search(r"HTTP 5xx 답\s*0\.4/분", s["text"]) and re.search(r"오류로 끝난 요청\s*0\.2/분", s["text"]), s["text"]
    assert "끊김 · 선점" in s["text"]


def test_지금_쓰는_일은_HWAX_몫이라고_적고_Slurm_GPU_는_무엇이_필요한지_말한다(seen):
    s = seen("ok")
    text = s["text"]
    assert "지금 쓰는 일" in text and "HWAX 에이전트 서버가 보는 몫만" in text
    assert "LLM 라우터" in text and seen.snap["router"] is not None
    assert "GPU 잡(stcx Slurm)" in text and "Q8" in text and "GPU 하드웨어" in text and "Q11" in text


def test_수집기가_답하지_않거나_꺼져_있으면_그렇게_말한다(seen):
    d = seen("down")
    assert d["alerts"] and "수집기가 답하지 않는다" in d["alerts"][0] and d["cards"] == []
    o = seen("off")
    assert o["alerts"] and "수집기가 꺼져 있다" in o["alerts"][0] and "LLM_STATUS=1" in o["alerts"][0]
    later = seen("later_down")
    assert "수집기가 답하지 않는다" in later["alerts"][0] and "마지막으로 받은 값" in later["alerts"][0]
    assert later["cards"] == ["GLM-1", "GLM-2", "QWEN", "BAD"], "답이 끊겨도 마지막으로 받은 값은 남긴다"


def test_관리자가_아니면_보이지_않고_부르지도_않는다(seen):
    s = seen("not_admin")
    assert "관리자(portal-admin)만" in s["text"] and not [c for c in s["calls"] if "llm-status" in c]
