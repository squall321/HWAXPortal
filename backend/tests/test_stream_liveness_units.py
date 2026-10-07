# 브라우저가 심의 스트림의 생존 신호(heartbeat)를 어떻게 읽고 뭐라고 말하는지 node 로 실제로 돌려 본다 — 파서와 문장 판정
"""왜 — 브라우저에는 스트림 타임아웃도 정체 감지도 없었다(없는 것이 맞다: 긴 심의를 끊을지는 중지 버튼을 쥔 사람이 정한다).
빠져 있던 것은 표시다. 깜박이는 점과 마지막 상태줄뿐이라 한 시간 전에 죽은 스트림과 생각 중인 좌석이 똑같이 보였다.

엔진이 이벤트가 없는 동안에도 15초마다 `event: ping` 을 낸다. 여기서 보는 것은 둘이다.
  · 파서(chat.api.ts) — ping 이 섞인 스트림이 **같은 내용**을 낸다(모르는 이벤트처럼 조용히 지나간다). 그리고 프레임마다
    신호를 알린다. 엔진·포털 릴레이·리스크 앱에도 같은 시험이 하나씩 있다(이벤트 이름 ping 의 계약).
  · 판정(lib/streamLive.ts) — ping 이 오는 동안은 '서버 살아 있음 · 마지막 진행 N 전', 45초(3회) 끊기면 '신호 없음',
    ping 을 한 번도 못 본 스트림(heartbeat 없는 옛 서버)은 침묵을 끊김으로 읽지 않는다.

프론트에 단위 시험 러너가 없어 TypeScript 를 한 파일씩 옮겨 적어 node 로 부른다(test_admin_screen_units 와 같은 길).
화면에 실제로 그려지는지는 test_delib_stream_in_browser 가 본다.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FE = ROOT / "frontend"

pytestmark = pytest.mark.skipif(
    not (FE / "node_modules/typescript").exists() or not shutil.which("node"),
    reason="frontend node_modules(typescript) 또는 node 가 없다 — 화면 조각을 돌려 볼 수 없다",
)

_DRIVER = r"""
const ts = require('typescript'); const fs = require('fs'); const path = require('path');
const SRC = process.argv[2];
// chat.api.ts 가 값으로 끌어오는 파일까지 옮겨 적는다(lib/chatErrors → state/chatStore)
for (const rel of ['api/chat.api.ts', 'lib/streamLive.ts', 'lib/chatErrors.ts', 'state/chatStore.ts']) {
  const js = ts.transpileModule(fs.readFileSync(path.join(SRC, rel), 'utf8'), { fileName: rel, compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } });
  const dst = path.join(__dirname, rel.replace(/\.ts$/, '.js'));
  fs.mkdirSync(path.dirname(dst), { recursive: true }); fs.writeFileSync(dst, js.outputText);
}
const req = JSON.parse(fs.readFileSync(0, 'utf8'));
// 네트워크 층만 대역 — 청크 목록을 그대로 흘리는 본문을 가진 응답을 돌려준다.
let chunks = [];
fs.writeFileSync(path.join(__dirname, 'api/client.js'),
  "exports.apiFetch = async () => new Response(new ReadableStream({ start(c) {" +
  " for (const x of global.__chunks) c.enqueue(new TextEncoder().encode(x)); c.close(); } }));\n");
global.document = { cookie: '' };
const { streamChat } = require('./api/chat.api.js');
const L = require('./lib/streamLive.js');

async function run(list) {
  global.__chunks = list;
  const calls = [], signals = [];
  const log = (name) => (e) => calls.push(e === undefined ? [name] : [name, e]);
  await streamChat('x', { onStatus: log('status'), onToken: log('token'), onResult: log('result'), onDelib: log('delib'),
    onThink: log('think'), onWarning: log('warning'), onError: log('error'), onDone: log('done'),
    onSignal: (ev) => signals.push(ev) });
  return { calls, signals };
}

(async () => {
  const out = { streams: [] };
  for (const list of req.streams) out.streams.push(await run(list));
  out.liveness = req.liveness.map(([live, now]) => L.liveness(live, now));
  out.ago = req.ago.map((ms) => L.ago(ms));
  out.noted = req.notes.map(([events, t0]) => {
    const live = L.startLive(t0);
    events.forEach(([ev, at]) => L.noteFrame(live, ev, at));
    return live;
  });
  out.consts = { SILENT_AFTER_MS: L.SILENT_AFTER_MS, QUIET_BEFORE_MS: L.QUIET_BEFORE_MS, HEARTBEAT_EVENT: L.HEARTBEAT_EVENT };
  process.stdout.write(JSON.stringify(out));
})().catch((e) => { console.error(e); process.exit(1); });
"""


@pytest.fixture(scope="module")
def front(tmp_path_factory):
    out = tmp_path_factory.mktemp("streamlive")
    (out / "drive.cjs").write_text(_DRIVER, encoding="utf-8")

    def run(streams=(), liveness=(), ago=(), notes=()) -> dict:
        r = subprocess.run(["node", "drive.cjs", str(FE / "src")], cwd=str(out), capture_output=True, text=True, timeout=120,
                           input=json.dumps({"streams": list(streams), "liveness": list(liveness), "ago": list(ago),
                                             "notes": list(notes)}),
                           env={"PATH": "/usr/bin:/bin:" + str(Path(shutil.which("node")).parent),
                                "NODE_PATH": str(FE / "node_modules")})
        assert r.returncode == 0, r.stdout + r.stderr
        return json.loads(r.stdout)
    return run


_BODY = [
    'event: status\ndata: {"step": "1라운드", "tool": null}\n\n',
    'event: delib\ndata: {"kind": "turn", "round": 1, "persona": "mech-a", "say": "초기 입장"}\n\n',
    'event: delib\ndata: {"kind": "decision", "text": "결정문"}\n\n',
    'event: done\ndata: {}\n\n',
]
_PING = 'event: ping\ndata: {"idle_s": 15, "ts": 1790000000}\n\n'


def test_ping_이_섞인_스트림이_같은_내용을_낸다(front):
    """이벤트 이름 ping 의 계약 — 파서는 모르는 이름을 버린다. 그 성질이 깨지면 heartbeat 가 화면 내용을 바꾼다."""
    mixed = [_PING] + [x for f in _BODY[:-1] for x in (f, _PING, _PING)] + _BODY[-1:]
    # 청크 경계가 프레임 경계와 안 맞는 경우도 — ping 프레임이 두 청크에 걸쳐 온다
    split = [_BODY[0] + _PING[:11], _PING[11:] + _BODY[1], _BODY[2] + _PING + _BODY[3]]
    plain, with_ping, torn = front(streams=[_BODY, mixed, split])["streams"]
    assert [c[0] for c in plain["calls"]] == ["status", "delib", "delib", "done"]
    assert with_ping["calls"] == plain["calls"], "ping 이 섞였다고 화면이 받는 내용이 달라졌다"
    assert torn["calls"] == plain["calls"]
    assert plain["signals"] == ["status", "delib", "delib", "done"], "프레임마다 신호를 알린다"
    assert with_ping["signals"].count("ping") == 7 and torn["signals"].count("ping") == 2, "heartbeat 는 신호로만 지나간다"


def test_모르는_이벤트와_깨진_ping_도_스트림을_깨지_않는다(front):
    weird = ['event: ping\n\n', 'event: ping\ndata: not-json\n\n', 'event: heartbeat2\ndata: {}\n\n', ': comment\n\n'] + _BODY
    (got,) = front(streams=[weird])["streams"]
    assert [c[0] for c in got["calls"]] == ["status", "delib", "delib", "done"]


def test_ping_은_신호_시각만_옮기고_진행_시각은_그대로_둔다(front):
    (live,) = front(notes=[([["status", 1000], ["ping", 16000], ["ping", 31000]], 0)])["noted"]
    assert live == {"signalAt": 31000, "progressAt": 1000, "pinged": True}
    (old_server,) = front(notes=[([["status", 1000], ["token", 2000]], 0)])["noted"]
    assert old_server == {"signalAt": 2000, "progressAt": 2000, "pinged": False}


def test_화면이_하는_말(front):
    t = 10_000_000
    cases = {
        "방금 진행": ({"signalAt": t - 2000, "progressAt": t - 2000, "pinged": True}, t),
        "ping 오는 중": ({"signalAt": t - 5000, "progressAt": t - 20 * 60_000, "pinged": True}, t),
        "ping 44초 전": ({"signalAt": t - 44_000, "progressAt": t - 120_000, "pinged": True}, t),
        "ping 45초 끊김": ({"signalAt": t - 45_000, "progressAt": t - 120_000, "pinged": True}, t),
        "ping 2시간 끊김": ({"signalAt": t - 7_200_000, "progressAt": t - 7_300_000, "pinged": True}, t),
        "옛 서버 10분 조용": ({"signalAt": t - 600_000, "progressAt": t - 600_000, "pinged": False}, t),
        "옛 서버 방금 진행": ({"signalAt": t - 3000, "progressAt": t - 3000, "pinged": False}, t),
        "시계가 뒤로": ({"signalAt": t + 500, "progressAt": t + 500, "pinged": True}, t),
    }
    got = dict(zip(cases, front(liveness=list(cases.values()))["liveness"], strict=True))
    assert got["방금 진행"] is None and got["옛 서버 방금 진행"] is None and got["시계가 뒤로"] is None, \
        "진행이 흐르는 동안에는 말하지 않는다(토큰마다 '0초 전' 이 깜박인다)"
    assert got["ping 오는 중"] == {"state": "alive", "text": "서버 살아 있음 · 마지막 진행 20분 전"}
    assert got["ping 44초 전"]["state"] == "alive", "세 번째 ping 이 빠지기 전까지는 살아 있다"
    assert got["ping 45초 끊김"]["state"] == "silent" and got["ping 45초 끊김"]["text"].startswith("신호 없음 45초 — 연결이 끊겼을 수")
    assert "신호 없음 2시간" in got["ping 2시간 끊김"]["text"]
    assert "서버에서 계속 돌 수" in got["ping 45초 끊김"]["text"], "끊긴 것은 구독이지 심의가 아니다 — 다시 시작하기 전에 볼 곳을 말한다"
    assert got["옛 서버 10분 조용"] == {"state": "unknown", "text": "마지막 진행 10분 전"}, \
        "heartbeat 를 본 적 없는 스트림의 침묵을 끊김으로 읽지 않는다 — 옛 엔진에서는 LLM 호출 한 번이 통째로 조용하다"


def test_시간_표기와_상수(front):
    got = front(ago=[0, 999, 59_999, 60_000, 3_599_000, 3_600_000, 3_900_000, -5])
    assert got["ago"] == ["0초", "0초", "59초", "1분", "59분", "1시간", "1시간 5분", "0초"]
    assert got["consts"] == {"SILENT_AFTER_MS": 45000, "QUIET_BEFORE_MS": 10000, "HEARTBEAT_EVENT": "ping"}, \
        "45초 = 엔진 heartbeat 15초 × 3회. 엔진 주기(DELIB_HEARTBEAT_S)를 바꾸면 이 값을 같이 본다"
