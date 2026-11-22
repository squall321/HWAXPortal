# 전문가 팀 화면을 헤드리스 브라우저에 실제 컴포넌트로 올려 본다 — 팀을 고르면 지정값으로 복사 · 지금 조합을 팀으로 저장 · 절차의 팀으로 좌석 미리 채우기(docs/expert-teams)
"""test_persona_chat_in_browser 와 같은 길 — 실제 컴포넌트(ChatProvider · ExpertToggle · StartPicker · ExpertPicker)를 esbuild 로 한 파일로 묶어 빈 문서에
올리고 fetch 를 가짜로 바꾼다. 도구는 프론트가 이미 가진 것만 쓴다. 없으면 건너뛴다(운영 박스).

보는 것 — ① 입력창 전문가 알약 → 가벼운 선택기 → 「팀에서 고르기」 → 팀 하나 → 그 순간 주 · 보조 · 앱 · 도구가 지정값이 되고 보낸 요청에 실린다(팀을
다시 묻지 않는다 — 복사다) ② 지금 조합을 「팀으로 저장」 하면 그 조합이 POST 본문이다 ③ 시작 화면에서 팀을 고르면 고르기 칸이 채워지고 '적용' 으로 지정값이
된다 ④ 빠진 전문가가 있으면 닫지 않고 알리고, 못 푸는 팀은 지정값을 건드리지 않는다 ⑤ 서버 대화를 팀 사본과 함께 열면(절차 → 챗) 지정값이다 ⑥ 절차의 팀으로
심의 좌석을 미리 채우면 그 사람들로 시작한다.
"""
import json
import subprocess

import pytest

from tests.test_delib_stream_in_browser import _BUILD, FE, pytestmark  # noqa: F401 — 같은 도구가 없으면 같이 건너뛴다

_HARNESS = r"""
import { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { AuthContext } from '__FE__/src/auth/AuthContext';
import { ChatProvider, useChat } from '__FE__/src/state/ChatContext';
import { ExpertToggle } from '__FE__/src/components/chat/ExpertToggle';
import { StartPicker } from '__FE__/src/components/chat/StartPicker';
import { ExpertPicker } from '__FE__/src/components/chat/ExpertPicker';
import { RoutineDetailView, RoutineNew } from '__FE__/src/pages/procedures/RoutinesView';

function Pins() {
  const { pinnedAgent, pinnedAgentName, pinnedHelpers, pinnedApps, pinnedTools } = useChat();
  return <span id="pins">{JSON.stringify({ agent: pinnedAgent, name: pinnedAgentName, helpers: pinnedHelpers, apps: pinnedApps,
                                           tools: pinnedTools })}</span>;
}
function Toggle() {
  const { setPinnedAgent, setPinnedHelpers, setPinnedApps, setPinnedTools, sendMessage } = useChat();
  return (
    <>
      <button id="pin" type="button" onClick={() => { setPinnedAgent('mech-a', '기구 강도 전문가'); }}>pin</button>
      <button id="combo" type="button" onClick={() => { setPinnedHelpers([{ key: 'cae-b', name: '구조 해석 전문가' }]);
        setPinnedApps(['step_forge']); setPinnedTools(['section_atlas']); }}>combo</button>
      <button id="send" type="button" onClick={() => sendMessage('힌지 강도 봐 줘')}>send</button>
      <Pins />
      <ExpertToggle />
    </>
  );
}
function Start() {
  const [open, setOpen] = useState(true);
  return <><Pins />{open && <StartPicker onClose={() => setOpen(false)} />}</>;
}
function Open() {
  const { openServerConversation, sendMessage } = useChat();
  return (
    <>
      <button id="open" type="button" onClick={() => openServerConversation('srv-9', '절차 실행 — 열충격', {
        agent: 'rel-thermal', agentName: '열충격 신뢰성 전문가', helpers: [{ key: 'cae-b', name: '구조 해석 전문가' }],
        apps: ['odb-hub'], tools: ['odb_list_components'] })}>open</button>
      <button id="send" type="button" onClick={() => sendMessage('이어서 묻는다')}>send</button>
      <Pins />
    </>
  );
}
function Seats() {
  const experts = { recommended: [], candidates: [{ key: 'x-1', name: '추천 1', role: '' }, { key: 'x-2', name: '추천 2', role: '' }],
                    pool: [{ key: 'x-1', name: '추천 1', tags: [] }, { key: 'x-2', name: '추천 2', tags: [] }] };
  return <ExpertPicker topic="힌지 파손 원인" loading={false} experts={experts as any} onCancel={() => undefined}
           seedSeats={[{ key: 'rel-thermal', name: '열충격 신뢰성 전문가', role: '' }, { key: 'cae-b', name: '구조 해석 전문가', role: '' }]}
           seedNote="절차의 팀 「열충격 검토팀」 으로 좌석을 미리 채웠습니다"
           onConfirm={(p) => { (window as any).__confirmed = p.map((x) => x.key); }} />;
}
(window as unknown as { __mount: (what?: string) => void }).__mount = (what) => {
  const user = { subject: 'u1@corp.example', email: 'u1@corp.example', display_name: 'U', groups: [] };
  const body = what === 'start' ? <Start /> : what === 'open' ? <Open /> : what === 'seats' ? <Seats /> : what === 'routine' ? <RoutineNew />
    : what === 'routineview' ? <Routes><Route path="/r/:id" element={<RoutineDetailView />} /></Routes> : <Toggle />;
  createRoot(document.getElementById('root')!).render(
    <AuthContext.Provider
      value={{ user, status: 'authenticated', login: () => undefined, logout: async () => undefined, refresh: async () => undefined }}
    >
      <MemoryRouter initialEntries={[what === 'routineview' ? '/r/r1' : '/']}>
        <ChatProvider storagePrefix="hwax.chat" serverKind="chat">{body}</ChatProvider>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
};
"""

# 가짜 백엔드 — 팀 목록 · 사본(__resolve 로 바꾼다) · 만들기, 전문가 명부, 서버 대화, 챗 스트림(바로 끝낸다). 부른 차례를 __calls 에 적는다.
_STUB = r"""
(() => {
  window.__calls = [];
  const TEAM = { id: 'tm_' + 'a'.repeat(32), name: '힌지 낙하 검토팀', description: '힌지 낙하를 볼 때', scope: 'org', official: true,
    lead: { key: 'mech-a', name: '기구 강도 전문가 (Mechanical Strength Expert)' },
    helpers: [{ key: 'cae-b', name: '구조 해석 전문가' }, { key: 'he-cad-stepforge', name: 'StepForge 운영자' }],
    apps: ['step_forge'], tools: ['section_atlas'], owner_email: 'boss@corp.example', owner_aff: 'CAEG', version: 3,
    created_at: 1, updated_at: 2, mine: false, editable: false, deletable: false };
  const SNAP = { id: TEAM.id, name: TEAM.name, version: 3, lead: TEAM.lead, helpers: TEAM.helpers, apps: TEAM.apps, tools: TEAM.tools,
                 resolved_at: 1763800000 };
  window.__resolve = { team: SNAP, why: '', hidden: [] };
  const json = (body, status = 200) =>
    Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }));
  window.fetch = (url, init = {}) => {
    const u = String(url);
    const method = (init.method || 'GET').toUpperCase();
    window.__calls.push({ url: u, method, body: typeof init.body === 'string' ? JSON.parse(init.body) : null });
    if (u === '/agent/teams' && method === 'GET') return json({ teams: [TEAM], note: '' });
    if (u === '/agent/teams' && method === 'POST') return json({ ...TEAM, id: 'tm_' + 'b'.repeat(32), ...JSON.parse(init.body), mine: true }, 201);
    if (u.startsWith('/agent/teams/') && u.endsWith('/resolve')) return json(window.__resolve);
    if (u.startsWith('/agent/deliberate/experts')) return json({ recommended: [], pool: [
      { key: 'mech-a', name: '기구 강도 전문가 (Mechanical Strength Expert)', tags: [] },
      { key: 'cae-b', name: '구조 해석 전문가', tags: [] }], tools: { all: [] } });
    if (u.startsWith('/agent/catalog/agent')) return json({ key: 'mech-a', name: '기구 강도 전문가', role: '', tags: [], samples: [], records: [] });
    if (u === '/agent/conversations' && method === 'GET') return json({ conversations: [] });
    if (u === '/agent/conversations' && method === 'POST') return json({ id: 'srv-1' });
    if (u.startsWith('/agent/conversations/')) return json({ detail: 'not found' }, 404);
    if (u === '/routines-api/platforms') return json({ deliberation: true, not_permitted: [],
      platforms: [{ backend: 'signalforge', label: 'SignalForge VOC', tools: [{ name: 'search_voc', exposed: 'search_voc', write: false, description: '' }] }] });
    if (u === '/routines-api/routines' && method === 'POST') return json({ id: 'r1', version_no: 1 }, 201);
    if (u.startsWith('/routines-api/routines/r1/readiness')) return json({ version_no: 1, steps: [{ step: 's1', state: 'allowed', backends: [],
      missing_tools: [], reason: '' }], teams: [{ where: 'routine', team_id: TEAM.id, name: TEAM.name, state: 'partial',
      why: '보조 전문가 StepForge 운영자(he-cad-stepforge) 는 이 사람이 쓸 수 없어 뺐다', hidden: [{ key: 'he-cad-stepforge', name: 'StepForge 운영자' }] }] });
    if (u.startsWith('/routines-api/routines/r1')) return json({ mine: true, versions: [{ version_no: 1 }], routine: { id: 'r1' },
      version: { version_no: 1, spec: { title: '낙하 루틴', purpose: '', vars: [], team: TEAM.id, report: { title: '', sections: ['s1'], ra: { upload: 'off' } },
        limits: { minutes: 60, calls: 60 }, visibility: 'private', steps: [{ id: 's1', title: 'VOC', kind: 'platform', backends: ['signalforge'],
        goal: 'VOC 를 본다', tools: [], uses: [], expect: { keys: [] }, budget: { calls: 8, seconds: 300 },
        blocked: { empty: 'continue', denied: 'skip', unavailable: 'skip' } }] } } });
    if (u.startsWith('/agent/chat')) {
      const body = new ReadableStream({ start(c) { c.enqueue(new TextEncoder().encode('event: done\ndata: {}\n\n')); c.close(); } });
      return Promise.resolve(new Response(body, { status: 200, headers: { 'Content-Type': 'text/event-stream' } }));
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

async function open(browser, what = '', before = null) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  page.setDefaultTimeout(10000);
  page.__errors = [];
  page.on('pageerror', (e) => page.__errors.push(String(e)));
  page.on('dialog', (d) => d.accept());
  await page.route('http://harness.invalid/**', (r) =>
    r.fulfill({ contentType: 'text/html', body: '<!doctype html><html><body><div id="root"></div></body></html>' }));
  await page.goto('http://harness.invalid/');
  await page.addScriptTag({ path: path.join(OUT, 'stub.js') });
  await page.addScriptTag({ path: path.join(OUT, 'bundle.js') });
  if (before) await page.evaluate(before);
  await page.evaluate((w) => window.__mount(w), what);
  return page;
}
const pins = (page) => page.evaluate(() => JSON.parse(document.getElementById('pins').textContent));
const chatBody = (page) => page.evaluate(() => (window.__calls.find((c) => c.url.startsWith('/agent/chat') && c.method === 'POST') || {}).body);
const teamCalls = (page) => page.evaluate(() => window.__calls.filter((c) => c.url.startsWith('/agent/teams')).map((c) => `${c.method} ${c.url}`));

const SCENARIOS = {
  // 입력창 알약 → 가벼운 선택기 → 팀 → 고른 순간 지정값 · 보낸 요청에 실림 · 보낼 때 팀을 다시 묻지 않는다(복사)
  async pick(browser) {
    const page = await open(browser);
    await page.locator('.tool-pill').click();
    await page.locator('.pp-teams').click();
    await page.locator('.tm-row').first().waitFor();
    const row = await page.locator('.tm-row').first().textContent();
    const hint = await page.locator('.pp-hint').first().textContent();
    await page.locator('.tm-row').first().click();
    await page.locator('.tm-card').waitFor({ state: 'detached' });
    const got = await pins(page);
    const before = await teamCalls(page);
    await page.locator('#send').click();
    await page.waitForFunction(() => window.__calls.some((c) => c.url.startsWith('/agent/chat')));
    return { row, hint, pins: got, sent: await chatBody(page), team_calls_before: before, team_calls_after: await teamCalls(page),
             errors: page.__errors };
  },
  // 지금 조합(주 · 보조 · 앱 · 도구)을 팀으로 저장 — 이름 · 공유 범위
  async save(browser) {
    const page = await open(browser);
    await page.locator('#pin').click();
    await page.locator('#combo').click();
    await page.locator('.tool-pill').click();
    await page.locator('.pp-teams').click();
    await page.locator('.tm-save-open').click();
    await page.locator('.tm-name').fill('내 낙하팀');
    await page.locator('.tm-scope').selectOption('org');
    await page.locator('.tm-submit').click();
    await page.waitForFunction(() => window.__calls.some((c) => c.url === '/agent/teams' && c.method === 'POST'));
    const post = (await page.evaluate(() => window.__calls)).find((c) => c.url === '/agent/teams' && c.method === 'POST');
    return { body: post.body, pins: await pins(page), errors: page.__errors };
  },
  // 시작 화면 — 팀을 고르면 고르기 칸이 채워지고 '적용' 으로 지정값
  async start(browser) {
    const page = await open(browser, 'start');
    await page.locator('.sp-team').click();
    await page.locator('.tm-row').first().click();
    await page.locator('.tm-card').waitFor({ state: 'detached' });
    const note = await page.locator('.sp-team-note').textContent();
    const before = await pins(page);
    await page.locator('.sp-apply').click();
    return { note, before, after: await pins(page), errors: page.__errors };
  },
  // 빠진 전문가가 있으면 복사하되 닫지 않고 알린다 · 못 푸는 팀은 지정값을 건드리지 않는다
  async dropped(browser) {
    const page = await open(browser, '', `window.__resolve = { ...window.__resolve, team: { ...window.__resolve.team,
      helpers: [window.__resolve.team.helpers[0]] }, why: '보조 전문가 StepForge 운영자(he-cad-stepforge) 는 이 사람이 쓸 수 없어 뺐다',
      hidden: [{ key: 'he-cad-stepforge' }] };`);
    await page.locator('.tool-pill').click();
    await page.locator('.pp-teams').click();
    await page.locator('.tm-row').first().click();
    await page.locator('.tm-notice').waitFor();
    const notice = await page.locator('.tm-notice').textContent();
    const got = await pins(page);
    await page.evaluate(() => { window.__resolve = { team: null, why: '팀 tm_x 를 찾을 수 없다 — 지워졌거나 이 사람에게 보이지 않는다', hidden: [] }; });
    await page.locator('.tm-row').first().click();
    await page.locator('.tm-err').waitFor();
    return { notice, pins: got, err: await page.locator('.tm-err').textContent(), after: await pins(page), errors: page.__errors };
  },
  // 서버 대화를 팀 사본과 함께 연다(절차 → 챗) — 지정값 · 보낸 요청
  async opened(browser) {
    const page = await open(browser, 'open');
    await page.locator('#open').click();
    const got = await pins(page);
    await page.locator('#send').click();
    await page.waitForFunction(() => window.__calls.some((c) => c.url.startsWith('/agent/chat')));
    return { pins: got, sent: await chatBody(page), errors: page.__errors };
  },
  // 루틴 짜기 — 루틴의 팀 · 단계의 팀(이 단계는 팀 없이)을 골라 저장하면 스펙에 실린다
  async routine(browser) {
    const page = await open(browser, 'routine');
    await page.locator('#rt-team').waitFor();
    await page.locator('#rt-title').fill('낙하 루틴');
    await page.locator('#rt-s0-title').fill('VOC');
    await page.locator('#rt-s0-add').selectOption('signalforge');
    await page.locator('textarea').nth(1).fill('VOC 를 본다');
    await page.locator('#rt-team').selectOption({ label: '[공식] 힌지 낙하 검토팀' });
    await page.locator('#rt-s0-team').selectOption('@none');
    await page.getByRole('button', { name: '저장', exact: true }).click();
    await page.waitForFunction(() => window.__calls.some((c) => c.url === '/routines-api/routines' && c.method === 'POST'));
    const post = (await page.evaluate(() => window.__calls)).find((c) => c.url === '/routines-api/routines' && c.method === 'POST');
    return { spec: post.body.spec, errors: page.__errors };
  },
  // 루틴 보기 — 준비도의 팀 줄(내가 못 쓰는 사람)
  async routineview(browser) {
    const page = await open(browser, 'routineview');
    await page.locator('[data-testid="routine-team-readiness"]').waitFor();
    return { line: await page.locator('[data-testid="routine-team-readiness"]').textContent(), errors: page.__errors };
  },
  // 절차의 팀으로 심의 좌석을 미리 채운다 — 추천 대신 그 사람들로 시작
  async seats(browser) {
    const page = await open(browser, 'seats');
    await page.locator('[data-testid="ep-seed-note"]').waitFor();
    await page.locator('.cx-ep-start').click();
    return { confirmed: await page.evaluate(() => window.__confirmed), note: await page.locator('[data-testid="ep-seed-note"]').textContent(),
             errors: page.__errors };
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
    out = tmp_path_factory.mktemp("teams")
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


TEAM_HELPERS = [{"key": "cae-b", "name": "구조 해석 전문가"}, {"key": "he-cad-stepforge", "name": "StepForge 운영자"}]


def test_알약에서_팀을_고르면_그_순간_지정값으로_복사되고_보낸_요청에_실린다(seen):
    s = seen("pick")
    assert "힌지 낙하 검토팀" in s["row"] and "공식" in s["row"] and "같은 소속" in s["row"], s["row"]
    assert "복사" in s["hint"]
    assert s["pins"] == {"agent": "mech-a", "name": "기구 강도 전문가 (Mechanical Strength Expert)", "helpers": TEAM_HELPERS,
                         "apps": ["step_forge"], "tools": ["section_atlas"]}, s["pins"]
    sent = s["sent"]
    assert sent["pinned_agent"] == "mech-a" and sent["pinned_agents"] == ["mech-a", "cae-b", "he-cad-stepforge"], sent
    assert sent["pinned_apps"] == ["step_forge"] and sent["pinned_tools"] == ["section_atlas"], sent
    assert not any("team" in k for k in sent), "에이전트 서버 계약은 그대로 — 새 칸이 없다"
    assert s["team_calls_after"] == s["team_calls_before"], "보낼 때 팀을 다시 묻지 않는다(지정값은 복사본이다)"
    assert s["team_calls_before"][-1].endswith("/resolve"), "고르는 순간 그 사람의 시야로 푼 사본을 받는다"


def test_지금_조합을_팀으로_저장하면_그_조합이_본문이다(seen):
    s = seen("save")
    assert s["body"] == {"name": "내 낙하팀", "description": "", "scope": "org", "lead": {"key": "mech-a", "name": "기구 강도 전문가"},
                         "helpers": [{"key": "cae-b", "name": "구조 해석 전문가"}], "apps": ["step_forge"], "tools": ["section_atlas"]}, s["body"]


def test_시작_화면에서_팀을_고르면_칸이_채워지고_적용하면_지정값이다(seen):
    s = seen("start")
    assert "힌지 낙하 검토팀" in s["note"]
    assert s["before"]["agent"] is None, "적용 전에는 지정값이 그대로"
    assert s["after"] == {"agent": "mech-a", "name": "기구 강도 전문가 (Mechanical Strength Expert)", "helpers": TEAM_HELPERS,
                          "apps": ["step_forge"], "tools": ["section_atlas"]}, s["after"]


def test_빠진_전문가는_알리고_못_푸는_팀은_지정값을_건드리지_않는다(seen):
    s = seen("dropped")
    assert "he-cad-stepforge" in s["notice"] and "복사했습니다" in s["notice"]
    assert s["pins"]["helpers"] == [{"key": "cae-b", "name": "구조 해석 전문가"}], s["pins"]
    assert "찾을 수 없다" in s["err"] and s["after"] == s["pins"], "못 푼 팀은 앞서 고른 지정값을 바꾸지 않는다"


def test_서버_대화를_팀_사본과_함께_열면_지정값이다(seen):
    s = seen("opened")
    assert s["pins"] == {"agent": "rel-thermal", "name": "열충격 신뢰성 전문가", "helpers": [{"key": "cae-b", "name": "구조 해석 전문가"}],
                         "apps": ["odb-hub"], "tools": ["odb_list_components"]}, s["pins"]
    assert s["sent"]["pinned_agents"] == ["rel-thermal", "cae-b"] and s["sent"]["pinned_apps"] == ["odb-hub"], s["sent"]


def test_절차의_팀으로_심의_좌석을_미리_채운다(seen):
    s = seen("seats")
    assert s["confirmed"] == ["rel-thermal", "cae-b"], "추천(x-1 · x-2) 대신 팀의 사람들로 시작한다"
    assert "열충격 검토팀" in s["note"]


def test_루틴_짜기에서_루틴_팀과_단계_팀을_골라_저장하면_스펙에_실린다(seen):
    s = seen("routine")
    spec = s["spec"]
    assert spec["team"] == "tm_" + "a" * 32, spec
    assert spec["steps"][0]["team"] == "", "단계는 「이 단계는 팀 없이」 — 빈 글"


def test_루틴_보기의_준비도에_팀_줄과_내가_못_쓰는_사람이_보인다(seen):
    line = seen("routineview")["line"]
    assert "루틴" in line and "힌지 낙하 검토팀" in line and "일부 빠짐" in line and "StepForge 운영자" in line, line
