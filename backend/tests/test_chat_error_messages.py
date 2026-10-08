# 챗·심의가 실패했을 때 화면이 하는 말을 node 로 실제로 돌려 본다 — 걸린 한도와 손잡이를 말하는지, 줄이라고 권하지 않는지
"""왜 — 한도가 걸리는 세 경우 모두 화면이 손잡이를 말하지 않았다.
  · 엔진 타임아웃 — '라운드 수를 줄이거나 무거운 옵션을 끄고 다시 시도하세요'. 넉넉히 기다리자는 쪽과 정반대다.
  · 프록시 절단   — 원문 'TypeError: network error'. 심의는 서버에서 계속 도는데(분리 태스크) 그 말이 없어, 곧바로
                    '다시 시도' 를 누르면 두 번째 심의가 나란히 돌아 공유 LLM 부하가 말없이 두 배가 된다.
  · 범위를 넘은 값 — 'Request failed (422)'. 본문에 어느 칸이 무엇을 어겼는지(loc·msg)가 있는데 읽지 않았다.
거기에 포털 릴레이의 침묵 한도(agent_stream_idle)가 새로 생겼다 — 포털이 준 문구를 그대로 보인다.

문구 판정(lib/chatErrors.ts)과 스트림 읽기(api/chat.api.ts)를 옮겨 적어 node 로 부른다. 화면에 뜨는 것은
test_delib_stream_in_browser 가 본다.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from app.agent.routes import DelibOpts

ROOT = Path(__file__).resolve().parents[2]
FE = ROOT / "frontend"

pytestmark = pytest.mark.skipif(
    not (FE / "node_modules/typescript").exists() or not shutil.which("node"),
    reason="frontend node_modules(typescript) 또는 node 가 없다 — 화면 조각을 돌려 볼 수 없다",
)

_DRIVER = r"""
const ts = require('typescript'); const fs = require('fs'); const path = require('path');
const SRC = process.argv[2];
for (const rel of ['api/chat.api.ts', 'lib/chatErrors.ts', 'state/chatStore.ts']) {
  const js = ts.transpileModule(fs.readFileSync(path.join(SRC, rel), 'utf8'), { fileName: rel, compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } });
  const dst = path.join(__dirname, rel.replace(/\.ts$/, '.js'));
  fs.mkdirSync(path.dirname(dst), { recursive: true }); fs.writeFileSync(dst, js.outputText);
}
fs.writeFileSync(path.join(__dirname, 'api/client.js'), "exports.apiFetch = async (...a) => global.__fetch(...a);\n");
global.document = { cookie: '' };
const { streamChat } = require('./api/chat.api.js');
const E = require('./lib/chatErrors.js');
const req = JSON.parse(fs.readFileSync(0, 'utf8'));
const enc = new TextEncoder();

async function run(kind) {
  const calls = [];
  const log = (name) => (e) => calls.push(e === undefined ? [name] : [name, e]);
  const handlers = { onStatus: log('status'), onError: log('error'), onDone: log('done') };
  const ctrl = new AbortController();
  if (kind === 'cut' || kind === 'abort') {
    // 프레임 하나를 준 뒤 본문이 끊긴다 — 프록시가 응답 도중 연결을 닫은 모양
    global.__fetch = async () => new Response(new ReadableStream({
      start(c) { c.enqueue(enc.encode('event: status\ndata: {"step": "1라운드", "tool": null}\n\n')); },
      pull(c) { return new Promise((res) => setTimeout(() => {
        if (kind === 'abort') { ctrl.abort(); c.error(new DOMException('aborted', 'AbortError')); }
        else c.error(new TypeError('network error'));
        res();
      }, 5)); },
    }));
  } else if (kind === '422') {
    global.__fetch = async () => new Response(JSON.stringify({ detail: [
      { loc: ['body', 'delib_opts', 'timeout_s'], msg: 'Input should be less than or equal to 14400', type: 'less_than_equal',
        input: 'SECRET-INPUT' }] }), { status: 422, headers: { 'Content-Type': 'application/json' } });
  } else if (kind === '422-nobody') {
    global.__fetch = async () => new Response('<html>bad</html>', { status: 422 });
  } else if (kind === '429') {
    global.__fetch = async () => new Response(JSON.stringify({ detail: 'too many concurrent chats; retry shortly' }), { status: 429 });
  }
  let thrown = null;
  try { await streamChat('x', { ...handlers, signal: ctrl.signal }); } catch (e) { thrown = `${e.name}`; }
  return { calls, thrown };
}

(async () => {
  const out = { streams: {} };
  for (const k of req.streams) out.streams[k] = await run(k);
  out.friendly = req.friendly.map((r) => E.friendlyError(r));
  out.cut = E.streamCutMessage('TypeError: network error');
  process.stdout.write(JSON.stringify(out));
})().catch((e) => { console.error(e); process.exit(1); });
"""


@pytest.fixture(scope="module")
def front(tmp_path_factory):
    out = tmp_path_factory.mktemp("chaterrors")
    (out / "drive.cjs").write_text(_DRIVER, encoding="utf-8")

    def run(streams=(), friendly=()) -> dict:
        r = subprocess.run(["node", "drive.cjs", str(FE / "src")], cwd=str(out), capture_output=True, text=True, timeout=120,
                           input=json.dumps({"streams": list(streams), "friendly": list(friendly)}),
                           env={"PATH": "/usr/bin:/bin:" + str(Path(shutil.which("node")).parent),
                                "NODE_PATH": str(FE / "node_modules")})
        assert r.returncode == 0, r.stdout + r.stderr
        return json.loads(r.stdout)
    return run


_CAP = int(DelibOpts.model_fields["timeout_s"].metadata[1].le)
# 포털 릴레이가 침묵 한도에서 내는 문구(routes.py _relay_stream) — 화면은 이것을 그대로 보인다.
_IDLE = ("에이전트 서버가 46800초 동안 아무 신호도 보내지 않아 구독을 끊었다(AGENT_STREAM_IDLE_TIMEOUT_S). "
         "심의는 서버에서 계속 돌 수 있다 — 다시 시작하기 전에 Report Archive 와 대화 목록을 확인하라")


def test_응답_도중에_끊기면_절단이라고_말하고_중지는_종전대로_올린다(front):
    got = front(streams=["cut", "abort"])["streams"]
    cut = got["cut"]
    assert cut["thrown"] is None, "절단은 예외로 올리지 않는다 — 호출부가 원문('TypeError: …')을 그대로 화면에 적었다"
    assert [c[0] for c in cut["calls"]] == ["status", "error", "done"], "받은 것은 그대로 두고 error 와 done 을 한 번씩 낸다"
    err = cut["calls"][1][1]
    assert err["code"] == "stream_cut" and err["message"].startswith("스트림이 끊겼습니다")
    assert "TypeError: network error" in err["message"], "원인 원문은 버리지 않고 끝에 붙인다"
    ab = got["abort"]
    assert ab["thrown"] == "AbortError" and [c[0] for c in ab["calls"]] == ["status", "done"], \
        "사람이 누른 중지는 절단이 아니다 — 호출부가 '취소됨' 으로 적는다"


def test_422_는_어느_칸이_무엇을_어겼는지_말한다(front):
    got = front(streams=["422", "422-nobody", "429"])["streams"]
    (kind, err), done = got["422"]["calls"]
    assert (kind, done) == ("error", ["done"]) and err["code"] == "http_422"
    assert err["message"] == ("요청 값이 허용 범위를 벗어났습니다(422) — "
                              "delib_opts.timeout_s: Input should be less than or equal to 14400")
    assert "SECRET-INPUT" not in err["message"], "거절된 입력 원문(input)은 싣지 않는다 — 요청 본문 전체일 수 있다"
    assert got["422-nobody"]["calls"][0][1]["message"] == "Request failed (422)", "본문을 못 읽으면 종전 문구다"
    assert got["429"]["calls"][0][1]["message"] == "Request failed (429)", "다른 상태는 건드리지 않는다"


def test_화면이_하는_말(front):
    raws = {
        "llm": "심의 처리 중 오류: Request timed out.",
        "llm_ko": "좌석의 LLM 호출이 1,800초 안에 끝나지 않았다(2회 시도 · APITimeoutError) — 시간 초과",
        "cut": front()["cut"],
        "idle": _IDLE,
        "rejected": "요청 값이 허용 범위를 벗어났습니다(422) — delib_opts.timeout_s: Input should be less than or equal to 14400",
        "rejected_other": "요청 값이 허용 범위를 벗어났습니다(422) — delib_opts.personas: List should have at most 20 items",
        "delib_other": "심의 처리 중 오류: KeyError('rounds')",
        "no_response": "TypeError: Failed to fetch",
        "unreachable": "agent server unreachable",
        "stopped": "취소됨",
        "unknown": "뭔가 다른 오류",
    }
    got = dict(zip(raws, front(friendly=list(raws.values()))["friendly"], strict=True))

    for k in ("llm", "llm_ko"):
        assert got[k]["title"] == "LLM 호출이 제한 시간에 걸렸습니다", got[k]
        h = got[k]["hint"]
        assert "timeout_s" in h and f"{_CAP}초" in h and "DELIB_TIMEOUT_S" in h, "늘릴 손잡이 둘(요청·서버)과 상한을 말한다"
        assert "줄일 일이 아닙니다" in h and "줄이거나" not in h and "끄고" not in h, "줄이라고 권하지 않는다"
        assert raws[k] in h, "엔진이 말한 사유(초·시도 횟수)는 그대로 보인다"

    assert got["cut"]["title"] == "스트림이 끊겼습니다" and got["cut"]["retry"] is True
    h = got["cut"]["hint"]
    assert "NGINX_AGENT_READ_TIMEOUT" in h and "서버에서 계속 돌 수" in h and "Report Archive" in h
    assert "두 번째 심의가 나란히" in h, "다시 시도가 무엇을 하는지 누르기 전에 알린다"

    assert got["idle"] == {"title": "에이전트 서버의 신호가 끊겨 구독을 닫았습니다", "hint": _IDLE, "retry": True}, \
        "포털이 준 문구(초·손잡이·확인할 곳)를 그대로 보인다 — 'timeout' 이라는 글자 때문에 LLM 한도 문구로 새면 안 된다"

    assert got["rejected"]["title"] == "요청 값이 허용 범위를 벗어났습니다" and got["rejected"]["retry"] is False, \
        "같은 값으로 다시 보내면 같은 거절이다 — 다시 시도 버튼을 내지 않는다"
    assert "delib_opts.timeout_s: Input should be less than or equal to 14400" in got["rejected"]["hint"]
    assert "LLM 호출 1회 기준" in got["rejected"]["hint"] and "DELIB_TIMEOUT_MAX_S" in got["rejected"]["hint"]
    assert "timeout_s" not in got["rejected_other"]["hint"] and "personas" in got["rejected_other"]["hint"]

    assert got["delib_other"]["title"] == "심의가 완료되지 못했습니다" and "KeyError" in got["delib_other"]["hint"]
    assert "줄이거나" not in got["delib_other"]["hint"], "한도와 무관한 오류에도 줄이라고 권하던 문구다"
    assert got["no_response"]["title"] == got["unreachable"]["title"] == "서버에 연결하지 못했습니다"
    assert got["stopped"]["title"] == "중단되었습니다" and got["unknown"]["title"] == "뭔가 다른 오류"


# ── 엔진이 실제로 보내는 글 — 화면의 갈래는 엔진의 글자에 걸려 있다 ───────────────────────────────────────────────
_ENGINE = ROOT.parent / "HWAXAgentServer"
# 엔진 app.py 가 챗(심의가 아닌) LLM 호출 한도에서 내는 error 글 — 걸린 값과 손잡이(LLM_TIMEOUT_S)를 엔진이 싣는다.
_CHAT_LIMIT = ("LLM 응답이 900초 안에 오지 않았습니다(LLM_TIMEOUT_S · 3회 시도) — LLM 이 밀려 있거나 멈췄습니다. "
               "잠시 후 다시 시도해 주세요 — 질문을 바꿔도 해결되지 않습니다.")


def test_챗의_LLM_한도는_엔진이_말한_손잡이를_그대로_보인다(front):
    """심의가 아닌 챗에서 LLM 응답이 한도에 걸리면 엔진이 걸린 값과 손잡이(LLM_TIMEOUT_S)를 글에 싣는다. 그 이름 안의 'TIMEOUT'
    이라는 글자 때문에 심의 한도 문구로 새면, 챗 사용자에게 '호출 타임아웃(timeout_s)·DELIB_TIMEOUT_S 를 올려라, 라운드 수나 좌석을
    줄일 일이 아니다' 라고 말한다 — 걸린 것과 다른 손잡이다."""
    (got,) = front(friendly=[_CHAT_LIMIT])["friendly"]
    assert got == {"title": "LLM 응답이 제한 시간 안에 오지 않았습니다", "hint": _CHAT_LIMIT, "retry": True}
    assert "DELIB_TIMEOUT_S" not in got["hint"] and "timeout_s" not in got["hint"] and "좌석" not in got["hint"]


def _engine_src(name: str) -> str:
    if not (_ENGINE / name).exists():
        pytest.skip(f"형제 리포 없음: {_ENGINE}")
    return (_ENGINE / name).read_text(encoding="utf-8")


def test_챗_LLM_한도의_글자를_엔진이_아직_그렇게_말한다():
    """화면은 엔진 글에 든 손잡이 이름(LLM_TIMEOUT_S)으로 이 갈래를 알아본다 — 엔진이 그 이름을 글에서 빼면(다른 글들처럼 knob
    칸으로 옮기면) 화면은 조용히 심의 한도 문구로 돌아가 엉뚱한 손잡이를 말한다."""
    app_src = _engine_src("app.py")
    assert '"오지 않았습니다(LLM_TIMEOUT_S"' in app_src and '"LLM 응답이 "' in app_src, (
        "엔진의 챗 LLM 한도 글이 바뀌었다 — chatErrors.ts 의 LLM_TIMEOUT_S 갈래와 이 파일의 _CHAT_LIMIT 을 맞춘다")
    assert "r.includes('LLM_TIMEOUT_S')" in (FE / "src/lib/chatErrors.ts").read_text(encoding="utf-8")
