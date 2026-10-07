# 심의 JS 파이프라인(infra/pipeline/hwax-deliberate.js·hwax-risk-review.js)을 스텁 런타임에서 실제로 돌려 좌석·의장이 무엇을 받는지 본다
"""MCP 경로의 심의는 엔진(deliberation.py)이 아니라 워크플로 스크립트가 돈다. 이 스크립트에는 시험이
없었다 — 문면 파리티(scripts/check_chair_parity.py)만 있었고, 스크립트를 **돌려 보는** 것은 실심의뿐이었다.

소스 문자열을 grep 하지 않고 스크립트를 돌린다. 워크플로 스크립트는 최상위에 await·return 이 있는
함수 본문이라, node 에서 async 함수로 감싸고 런타임이 주는 것(args·agent·parallel·log·phase·workflow)을
스텁으로 넣는다. 좌석·의장 스텁은 스키마에 맞는 고정 답을 돌려주고, 받은 호출을 전부 적어 둔다 —
'좌석이 무엇을 받았는가' 를 프롬프트에서 직접 본다.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_DELIB = "infra/pipeline/hwax-deliberate.js"
_RISK = "infra/pipeline/hwax-risk-review.js"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node 가 없다")

# 워크플로 스크립트를 스텁 런타임에서 돌리는 구동기. 표준입력으로 {args, decision?, decisionFails?, brief?} 를 받는다.
_NODE_RUN = r"""
const fs = require('fs');
const path = require('path');
const root = process.argv[1], scriptRel = process.argv[2];
const inp = JSON.parse(fs.readFileSync(0, 'utf8'));
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
const calls = [], logs = [], childArgs = [];

// 스키마가 선언하지 않은 필드는 버린다 — 구조화 출력이 실제로 그렇게 한다(브리프 옮겨 적기 스텁용).
const project = (v, s) => {
  if (!s || v == null) return v;
  if (s.type === 'array') return Array.isArray(v) ? v.map(x => project(x, s.items)) : v;
  if (s.type === 'object' && s.properties && typeof v === 'object') {
    return Object.fromEntries(Object.entries(v).filter(([k]) => k in s.properties)
      .map(([k, x]) => [k, project(x, s.properties[k])]));
  }
  return v;
};
// 실제 런타임의 서명은 agent(prompt, opts?) 다 — 셋째 인자부터는 버려지고, opts 가 객체가 아니면 통째로 무시된다.
async function agent(prompt, opts) {
  const o = (opts && typeof opts === 'object') ? opts : {};
  const label = String(o.label || '');
  calls.push({ label, prompt: String(prompt), argc: arguments.length, optsType: opts === undefined ? 'none' : typeof opts });
  const props = (o.schema && o.schema.properties) || {};
  if (label === 'brief') return project(inp.brief, o.schema);
  if (label.startsWith('submit:')) return { ok: true, detail: '' };
  if (props.lens) return { lens: '관점', reads: [], recommendation: '권장', concerns: [] };
  if (props.deepen) return { concede: [], rebut: [], deepen: '심화' };
  if (props.final_position) return { final_position: '최종', vote: '찬성' };
  if (String(prompt).startsWith('당신은 심의체 의장')) {
    return inp.decisionFails ? null : (inp.decision || '## 의사결정문\n결정.\n〔결정문 끝〕');
  }
  if (label === 'explain') return '쉬운 설명';
  return null;
}
const parallel = fns => Promise.all(fns.map(f => f()));
const log = m => { logs.push(String(m)); };
const phase = () => {};
const run = (rel, a) => {
  const src = fs.readFileSync(path.resolve(root, rel), 'utf8').replace(/^export const meta/m, 'const meta');
  return new AsyncFunction('args', 'agent', 'parallel', 'log', 'phase', 'workflow', src)(
    a, agent, parallel, log, phase, workflow);
};
const workflow = async (ref, a) => { childArgs.push(a); return run(ref.scriptPath, a); };
run(scriptRel, inp.args)
  .then(result => { process.stdout.write(JSON.stringify({ result, calls, logs, childArgs })); })
  .catch(e => { process.stderr.write(String((e && e.stack) || e)); process.exit(1); });
"""

_SEATS = [{"key": "mech-a", "role": "기구"}, {"key": "sim-b", "role": "해석"}]


def _run(script: str, args: dict, **extra) -> dict:
    r = subprocess.run(["node", "-e", _NODE_RUN, str(_ROOT), script],
                       input=json.dumps({"args": args, **extra}), capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-3000:]
    return json.loads(r.stdout)


def _delib(evidence=None, **kw) -> dict:
    """심의 한 건 — 기본은 1라운드 체크포인트까지만(좌석 프롬프트와 반환값을 보는 데는 그걸로 충분하다)."""
    extra = {k: kw.pop(k) for k in ("decision", "decisionFails") if k in kw}
    args = {"question": "화두", "personas": _SEATS, "evidence": evidence or [], "stopAfterRound": 1,
            "saveConversation": False, **kw}
    return _run(_DELIB, args, **extra)


def _brief(evidence, **panel) -> dict:
    return {"panels": [{"panel_id": "P1", "question": "패널 화두", "rounds": 2,
                        "seats": [{"key": "mech-a", "role": "기구", "origin": "primary"},
                                  {"key": "sim-b", "role": "해석", "origin": "primary"}],
                        "evidence": evidence, **panel}]}


def _risk(brief: dict, **extra) -> dict:
    extra.setdefault("decision", "## 리스크 심사 보고서\n판정.\n〔결정문 끝〕")
    return _run(_RISK, {"targetKey": "T1", "briefToken": "tok", "tier": "B"}, brief=brief, **extra)


def _chair(out: dict) -> dict:
    return next(c for c in out["calls"] if c["prompt"].startswith("당신은 심의체 의장"))


# ── 의장 호출 — 출력 형식 지시가 프롬프트에 실려 가는가 ────────────────────────────────
def test_의장은_출력_형식_지시를_받는다():
    """의장 프롬프트 뒤에 붙인 [출력 형식] 블록(한 응답으로 · '## ' 머리 · 〔결정문 끝〕 마커 · [e:N] 인용)이
    쉼표 하나 때문에 agent() 의 둘째 인자(옵션 자리)로 들어가 **한 번도 의장에게 가지 않았다**(2026-09-01~).
    마커를 찍으라는 말을 못 들은 의장은 마커를 안 찍었고, 그게 '절단 의심' 으로 올라왔다 — 실제 실행의
    의장 전사 23건 전부에 이 블록이 없었다(2026-10-07 대조)."""
    chair = _chair(_delib(stopAfterRound=0, rounds=2))
    for want in ("[출력 형식 — 반드시 지킬 것]", "〔결정문 끝〕", "첫 줄은 반드시 '## ' 로 시작",
                 "그 항목의 [e:N] 표지를 함께 적어라"):
        assert want in chair["prompt"], f"의장 프롬프트에 없다: {want}"
    assert chair["label"] == "decision", "옵션 객체가 셋째 인자로 밀려 라벨도 버려졌다"


@pytest.mark.parametrize("kind", ["심의", "심의+저장", "리스크 심사"])
def test_에이전트_호출은_프롬프트와_옵션_둘만_넘긴다(kind):
    """같은 실수(문자열 이음표 대신 쉼표)를 어디서든 잡는다 — 셋째 인자는 런타임이 버리고, 문자열 옵션은 통째로 무시된다."""
    if kind == "리스크 심사":
        out = _risk(_brief([{"source": "scope", "result": "스코프"}]))
    else:
        save = kind == "심의+저장"
        out = _delib(stopAfterRound=0, rounds=3, saveReport=save, saveConversation=save)
    assert len(out["calls"]) >= 6, "스텁이 호출을 못 잡았다"
    bad = [(c["label"] or c["prompt"][:30], c["argc"], c["optsType"]) for c in out["calls"]
           if c["argc"] > 2 or c["optsType"] not in ("object", "none")]
    assert not bad, f"agent(prompt, opts) 서명을 벗어난 호출: {bad}"


# ── 사전 근거 — 본문 키 폴백(엔진 _EVID_BODY_KEYS 와 같은 순서) ─────────────────────────
# 엔진에서 고친 것과 같은 결함이 여기에도 있었다(2026-10-07 S26U 실사용 피드백, docs/delib-engine-feedback 1-2):
# 필터가 `e.result != null` 만 봐서, 본문을 다른 키에 넣은 근거가 통째로 사라졌다.
_BODY_KEYS = ["result", "text", "content", "excerpt", "summary", "body", "output", "data"]


def _seat_prompt(out: dict) -> str:
    """첫 좌석이 1라운드에 받은 프롬프트 — 근거 블록이 여기 실린다."""
    return next(c["prompt"] for c in out["calls"] if c["label"].startswith("r1:"))


def test_본문이_result_아닌_키에_있어도_좌석에_간다():
    prompt = _seat_prompt(_delib([{"source": f"출처-{k}", k: f"본문-{k}"} for k in _BODY_KEYS]))
    for i, k in enumerate(_BODY_KEYS, start=1):
        assert f"· [e:{i}] [출처-{k}] 본문-{k}" in prompt, f"'{k}' 에 든 본문이 좌석에 안 갔다"


@pytest.mark.parametrize("i", range(len(_BODY_KEYS) - 1))
def test_본문_키는_앞의_것이_이긴다(i):
    """순서가 우선순위다 — 엔진과 다르면 같은 근거가 경로마다 다른 본문으로 실린다."""
    first, second = _BODY_KEYS[i], _BODY_KEYS[i + 1]
    prompt = _seat_prompt(_delib([{"source": "s", second: "뒤-본문", first: "앞-본문"}]))
    assert "앞-본문" in prompt and "뒤-본문" not in prompt


def test_빈_앞_키는_건너뛰고_참거짓은_본문이_아니다():
    prompt = _seat_prompt(_delib([
        {"source": "빈result", "result": "   ", "summary": "요약-본문"},
        # `{"result": true, "data": …}` 의 result 는 성패 표시다 — 그걸 본문으로 집으면 진짜 본문을 가린다.
        {"source": "성패", "result": True, "data": "진짜-본문"},
    ]))
    assert "· [e:1] [빈result] 요약-본문" in prompt
    assert "· [e:2] [성패] 진짜-본문" in prompt


def test_문자열이_아닌_본문은_JSON_으로_싣는다():
    """종전엔 String() 이라 객체가 '[object Object]' 로 실렸다 — 좌석이 수치를 읽지 못한다."""
    prompt = _seat_prompt(_delib([
        {"source": "표", "data": {"행": [1, 2.5], "단위": "MPa"}},
        {"source": "수", "result": 12.5},
        {"source": "객체result", "result": {"값": 3}},
    ]))
    assert '· [e:1] [표] {"행":[1,2.5],"단위":"MPa"}' in prompt
    assert "· [e:2] [수] 12.5" in prompt
    assert '· [e:3] [객체result] {"값":3}' in prompt and "[object Object]" not in prompt


def test_본문_없는_항목은_번호를_먹지_않는다():
    empties = [{"source": "빈것"}, "문자열", None, {"source": "공백", "result": "  "},
               {"result": False}, {"result": []}, {"result": {}}, ["배열"]]
    prompt = _seat_prompt(_delib(empties + [{"source": "멀쩡", "result": "본문"}]))
    assert "· [e:1] [멀쩡] 본문" in prompt and "[e:2]" not in prompt


def _unmatched(decision: str, evidence: list) -> list:
    out = _delib(evidence, stopAfterRound=0, rounds=2, decision=f"## 의사결정문\n{decision}\n〔결정문 끝〕")
    return out["result"]["citationAudit"]["unmatched"]


def test_폴백_키의_본문도_수치_대조_출처다():
    """대조 말뭉치도 `e.result` 만 읽었다 — text 에 든 수치를 의장이 옮기면 '어느 원문에도 없는 수치' 로 올라온다."""
    assert _unmatched("하중은 4567.8 N 이다.", [{"source": "s", "text": "하중 4567.8 N"}]) == []
    assert _unmatched("하중은 4567.8 N 이다.", [{"source": "s", "text": "하중 9999.9 N"}]) == ["4567.8"]
