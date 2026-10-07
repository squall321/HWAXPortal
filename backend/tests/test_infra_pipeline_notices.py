# 심의 JS 파이프라인이 받은 입력을 그대로 쓰지 못했을 때(항목 상한 절단 · 본문 후보 여럿 · 키 없는 좌석) 반환값과 원장에 남기는지
"""엔진(deliberation.py)은 이 셋을 카드로 알린다. MCP 길의 워크플로(infra/pipeline/hwax-deliberate.js)에는 같은 상황이 있는데
아무 말이 없었다 — 긴 근거는 앞 2,000자만 실리고, `{summary, body}` 는 summary 한 줄만 실리고, 키 없는 좌석은 "undefined" 라는
이름으로 끝까지 돌았다. 호출자는 '보낸 대로 돌았다' 로 읽는다. 버린 근거를 남기는 방식(evidenceOmitted) 그대로 `inputNotices` 에
남기고, 리스크 심사 오케스트레이터(hwax-risk-review.js)가 그것을 제출 기록과 원장으로 넘긴다.

스크립트를 스텁 런타임에서 **실제로 돌린다**(test_delib_pipeline_js 와 같은 방식). 여기 구동기는 좌석이 내는 글을 시험이 정한다 —
긴 발언이 원장까지 줄지 않고 가는지를 보려면 좌석의 답이 길어야 한다.
"""
import ast
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_DELIB = "infra/pipeline/hwax-deliberate.js"
_RISK = "infra/pipeline/hwax-risk-review.js"
_ENGINE = _ROOT.parent / "HWAXAgentServer"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node 가 없다")

# 워크플로 스크립트를 스텁 런타임에서 돌리는 구동기. 표준입력 {args, brief?, decision?, seat?} — seat 은 좌석 답의 덮어쓰기다.
_NODE_RUN = r"""
const fs = require('fs');
const path = require('path');
const root = process.argv[1], scriptRel = process.argv[2];
const inp = JSON.parse(fs.readFileSync(0, 'utf8'));
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
const calls = [], logs = [];
const seat = inp.seat || {};
const project = (v, s) => {
  if (!s || v == null) return v;
  if (s.type === 'array') return Array.isArray(v) ? v.map(x => project(x, s.items)) : v;
  if (s.type === 'object' && s.properties && typeof v === 'object') {
    return Object.fromEntries(Object.entries(v).filter(([k]) => k in s.properties).map(([k, x]) => [k, project(x, s.properties[k])]));
  }
  return v;
};
async function agent(prompt, opts) {
  const o = (opts && typeof opts === 'object') ? opts : {};
  const label = String(o.label || '');
  calls.push({ label, prompt: String(prompt) });
  const props = (o.schema && o.schema.properties) || {};
  if (label === 'brief') return project(inp.brief, o.schema);
  if (label.startsWith('submit:')) return { ok: true, detail: '' };
  if (props.lens) return { lens: seat.lens || '관점', reads: seat.reads || [], recommendation: seat.recommendation || '권장', concerns: seat.concerns || [] };
  if (props.deepen) return { concede: [], rebut: [], deepen: seat.deepen || '심화' };
  if (props.final_position) return { final_position: seat.final_position || '최종', vote: seat.vote || '찬성' };
  if (String(prompt).startsWith('당신은 심의체 의장')) return inp.decisionFails ? null : (inp.decision || '## 의사결정문\n결정.\n〔결정문 끝〕');
  if (label === 'explain') return '쉬운 설명';
  if (label === 'ra-save') return '77';
  return null;
}
const parallel = fns => Promise.all(fns.map(f => f()));
const log = m => { logs.push(String(m)); };
const run = (rel, a) => {
  const src = fs.readFileSync(path.resolve(root, rel), 'utf8').replace(/^export const meta/m, 'const meta');
  return new AsyncFunction('args', 'agent', 'parallel', 'log', 'phase', 'workflow', src)(a, agent, parallel, log, () => {}, workflow);
};
const workflow = async (ref, a) => run(ref.scriptPath, a);
run(scriptRel, inp.args)
  .then(result => { process.stdout.write(JSON.stringify({ result, calls, logs })); })
  .catch(e => { process.stderr.write(String((e && e.message) || e)); process.exit(1); });
"""

_SEATS = [{"key": "mech-a", "role": "기구 역할"}, {"key": "sim-b", "role": "해석 역할"}]


def _node(script: str, args: dict, **extra) -> subprocess.CompletedProcess:
    return subprocess.run(["node", "-e", _NODE_RUN, str(_ROOT), script], input=json.dumps({"args": args, **extra}),
                          capture_output=True, text=True, timeout=120)


def _run(script: str, args: dict, **extra) -> dict:
    r = _node(script, args, **extra)
    assert r.returncode == 0, r.stderr[-3000:]
    return json.loads(r.stdout)


def _delib(evidence=None, personas=None, **kw) -> dict:
    """심의 한 건 — 기본은 1라운드 체크포인트까지만."""
    extra = {k: kw.pop(k) for k in ("decision", "decisionFails", "seat") if k in kw}
    args = {"question": "화두", "personas": _SEATS if personas is None else personas, "evidence": evidence or [],
            "stopAfterRound": 1, "saveConversation": False, **kw}
    return _run(_DELIB, args, **extra)


def _notice(out: dict, source: str) -> dict | None:
    return next((x for x in out["result"]["inputNotices"] if x["source"] == source), None)


def _seat_prompt(out: dict) -> str:
    return next(c["prompt"] for c in out["calls"] if c["label"].startswith("r1:"))


def _seated(out: dict) -> list[str]:
    return [c["label"][3:] for c in out["calls"] if c["label"].startswith("r1:")]


# ── ① 항목 상한에서 줄여 실은 근거 ─────────────────────────────────────────────────────────
CUT = "사전 근거 항목 상한 초과"


def test_항목_상한에서_줄인_근거를_결과에_남긴다():
    """**좌석은 본문 끝의 표식으로 절단을 알지만 호출자는 몰랐다** — '2건 보냈고 2건 실렸다' 로 읽히는데 긴 항목은 앞 2,000자뿐이다."""
    out = _delib([{"key": "E1", "source": "변경 원장", "result": "가" * 3000}, {"source": "짧은 것", "result": "본문"}])
    note = _notice(out, CUT)
    assert note and note["count"] == 1, out["result"]["inputNotices"]
    for want in ("[e:1|E1]", "3,000자", "2,000자", "보지 못했다"):
        assert want in note["text"], (want, note["text"])
    assert "[e:2]" not in note["text"], "줄이지 않은 항목은 적지 않는다"
    assert "…[3000자 중 2,000자]" in _seat_prompt(out), "좌석이 보는 표식은 종전 그대로다"
    assert out["result"]["evidenceOmitted"] == [], "통째로 빠진 근거는 없다 — 그쪽 칸의 뜻은 그대로다"
    assert any("항목 상한 초과 1건" in ln and "inputNotices" in ln for ln in out["logs"]), out["logs"]


@pytest.mark.parametrize("n,cut", [(2000, False), (2001, True)])
def test_상한_그대로인_항목은_줄인_것이_아니다(n, cut):
    out = _delib([{"source": "s", "result": "가" * n}])
    assert (_notice(out, CUT) is not None) is cut


def test_줄인_항목은_실린_것만_센다():
    """예산을 넘겨 통째로 빠진 항목은 evidenceOmitted 가 말한다 — 두 칸에 두 번 세면 '5건 줄이고 3건 뺐다' 가 '8건 줄였다' 로 읽힌다."""
    out = _delib([{"source": f"s{i}", "result": "가" * 3000} for i in range(1, 9)])
    assert _notice(out, CUT)["count"] == 5
    assert [(x["source"], x["count"]) for x in out["result"]["evidenceOmitted"]] == [("사전 근거 예산 초과", 3)]
    assert "[e:6]" not in _notice(out, CUT)["text"]


def test_사유_한_줄은_앱_원장의_상한_안쪽이다():
    """리스크 앱 원장의 줄은 200자다(HWAXRisk routes.EVENT_FIELD_MAX). 키가 긴 항목이 여럿이면 낱개를 다 적을 수 없다 —
    표지 중간에서 자르지 않고 들어가는 만큼만 적은 뒤 '외 N건' 으로 센다."""
    ev = [{"key": f"E{i}-" + "K" * 20, "source": f"s{i}", "result": "가" * 2500} for i in range(1, 6)]
    note = _notice(_delib(ev), CUT)
    assert note["count"] == 5 and len(note["text"]) <= 200, (len(note["text"]), note["text"])
    assert re.search(r"외 \d건", note["text"]) and note["text"].count("[e:") >= 1
    assert re.search(r"\[e:\d+\|[A-Za-z0-9_.-]+\] 원문 2,500자", note["text"]), "적은 표지는 온전하다"
    assert note["text"].rstrip().endswith("보지 못했다."), "꼬리 문장이 잘리지 않는다"


# ── ② 본문 후보가 여럿이던 근거 ───────────────────────────────────────────────────────────
SHADOW = "사전 근거 본문 후보 여럿"


def test_본문_후보가_여럿이면_뺀_것을_결과에_남긴다():
    """`{summary: 한 줄, body: 본문}` 은 summary 한 줄만 좌석에 간다(순서가 우선순위다). 본문을 넣은 호출자는 그것이 실린 줄 안다."""
    out = _delib([{"key": "E3", "source": "선례", "summary": "한 줄 요약", "body": "나" * 3400}, {"source": "하나", "result": "본문"}])
    note = _notice(out, SHADOW)
    assert note and note["count"] == 1, out["result"]["inputNotices"]
    for want in ("[e:1|E3]", "summary 6자를 싣고", "body 3,400자", "뺐다", "'result'"):
        assert want in note["text"], (want, note["text"])
    prompt = _seat_prompt(out)
    assert "한 줄 요약" in prompt and "나나나" not in prompt, "실리는 것은 종전 그대로 앞선 키 하나다"
    assert _notice(out, CUT) is None, "실린 본문(summary)은 짧다 — 줄인 것이 아니다"
    assert any("본문 후보 여럿 1건" in ln for ln in out["logs"]), out["logs"]


def test_뺀_후보는_키_순서대로_전부_적는다():
    out = _delib([{"source": "s", "data": {"a": 1}, "text": "글", "result": "값"}])
    assert "result 1자를 싣고 text 1자, data 7자는 뺐다" in _notice(out, SHADOW)["text"]


@pytest.mark.parametrize("item", [
    {"source": "s", "result": "본문"},
    {"source": "s", "result": True, "data": "진짜 본문"},        # 참·거짓은 본문이 아니다 — 후보가 하나다
    {"source": "s", "result": "   ", "summary": "요약"},          # 빈 앞 키는 후보가 아니다
    {"source": "s", "result": [], "body": {}, "text": "글"},
])
def test_본문이_하나뿐이면_조용하다(item):
    assert _notice(_delib([item]), SHADOW) is None


def test_후보가_여럿인_항목도_실린_것만_센다():
    ev = [{"source": f"s{i}", "summary": "가" * 3000, "body": "뒤"} for i in range(1, 9)]
    out = _delib(ev)
    assert _notice(out, SHADOW)["count"] == 5 and _notice(out, CUT)["count"] == 5
    assert len(_notice(out, SHADOW)["text"]) <= 200


# ── 엔진을 오라클로 — 어느 키가 본문 후보인가, 어느 항목이 좌석인가 ────────────────────────────────
def _engine_fn(name: str, extra: dict | None = None):
    """엔진 소스에서 함수 하나를 꺼내 돌린다(import 하지 않는다 — 그 리포의 의존성·환경변수를 끌어오지 않게)."""
    src_file = _ENGINE / "deliberation.py"
    if not src_file.exists():
        pytest.skip(f"형제 리포 없음: {src_file}")
    tree = ast.parse(src_file.read_text(encoding="utf-8"))
    fn = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name), None)
    if fn is None:
        pytest.skip(f"옆의 엔진에 {name} 가 없는 판이다")
    ns: dict = {"json": json, **(extra or {})}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(src_file), "exec"), ns)  # noqa: S102 — 옆 리포의 추적 파일 발췌
    return ns[name]


_BODY_ITEMS = [
    {"result": "r", "text": "t"},
    {"summary": "s", "body": "b", "output": "o"},
    {"result": True, "data": "d", "content": "c"},
    {"result": "  ", "text": "", "excerpt": "e", "data": "d"},
    {"result": 0, "text": "t"},                       # 0 은 본문이다(수치) — None·참거짓과 다르다
    {"result": None, "text": [], "content": {}, "body": "b", "data": [1]},
    {"text": "t", "result": "r"},                     # 항목 안의 순서가 아니라 키 목록의 순서다
]


@pytest.mark.parametrize("item", _BODY_ITEMS, ids=[str(i) for i in range(len(_BODY_ITEMS))])
def test_본문_후보를_가르는_규칙이_엔진과_같다(item):
    """같은 근거가 웹 길과 MCP 길에서 다른 본문으로 실리면 안 된다. 엔진의 _ev_bodies 가 정본이다 — 실은 키와 뺀 키가 같아야 한다."""
    keys = _engine_fn("_ev_bodies", {"_EVID_BODY_KEYS": ("result", "text", "content", "excerpt", "summary", "body", "output", "data")})
    want = [k for k, _ in keys(item)]
    note = _notice(_delib([{"source": "s", **item}]), SHADOW)
    if len(want) < 2:
        assert note is None, (want, note)
        return
    m = re.search(r"\[e:1\] (\w+) [\d,]+자를 싣고 (.+?)는 뺐다", note["text"])
    assert m, note["text"]
    got = [m.group(1)] + [part.split(" ")[0] for part in m.group(2).split(", ")]
    assert got == want, f"엔진 {want} · JS {got}"


# ── ③ 키가 없어 앉히지 못한 좌석 ──────────────────────────────────────────────────────────
NOKEY = "지정 좌석 키 없음"


def test_키_없는_좌석은_앉히지_않고_결과에_남긴다():
    """**종전엔 "undefined" 라는 이름의 좌석이 끝까지 돌았다** — 역할을 못 찾아 그 낱말이 곧 역할이었고, 결정문은 한 도메인으로 셌다."""
    out = _delib(personas=[{"key": "mech-a", "role": "기구 역할"}, {"name": "해석 담당", "role": "키를 name 에 넣었다"},
                           {"key": "sim-b", "role": "해석 역할"}])
    assert _seated(out) == ["mech-a", "sim-b"], _seated(out)
    assert not any('"undefined"' in c["prompt"] or "undefined" in c["label"] for c in out["calls"])
    note = _notice(out, NOKEY)
    assert note and note["count"] == 1, out["result"]["inputNotices"]
    for want in ("3석 중 1석", "name, role", "agent_type", "키가 있는 좌석만"):
        assert want in note["text"], (want, note["text"])
    assert len(note["text"]) <= 200
    assert any("키가 없어" in ln and "2석으로 돈다" in ln for ln in out["logs"]), out["logs"]


def test_추천_도구가_돌려준_줄을_그대로_넘겨도_앉는다():
    """recommend_agents 는 좌석 키를 agent_type 으로 돌려준다 — 그 줄을 그대로 넘긴 호출자의 좌석이 전부 걸러지면 안 된다
    (엔진 _seat_key 와 같은 규칙). 역할도 그 키로 찾는다."""
    out = _delib(personas=[{"agent_type": "mech-a", "role": "기구 역할"}, {"key": "sim-b", "agent_type": "다른이름", "role": "해석 역할"}])
    assert _seated(out) == ["mech-a", "sim-b"], "key 가 정본이고 agent_type 은 key 가 없을 때만"
    assert '당신은 "mech-a" 전문가. 영역: 기구 역할' in _seat_prompt(out)
    assert out["result"]["inputNotices"] == []


@pytest.mark.parametrize("bad,said", [(None, "객체가 아님(null)"), ("mech-x", "객체가 아님(string)"), (["k"], "객체가 아님(array)"),
                                      ({"key": "   ", "role": "r"}, "key, role"), ({}, "없음"), ({"key": None, "agent_type": ""}, "key, agent_type")])
def test_객체가_아니거나_키가_빈_항목도_죽지_않고_센다(bad, said):
    """null 한 줄이 워크플로를 통째로 죽였다(`p.key` 를 읽다 TypeError) — 몇 시간짜리 심의가 좌석 목록의 빈 줄 하나로 시작도 못 했다."""
    out = _delib(personas=[*_SEATS, bad])
    assert _seated(out) == ["mech-a", "sim-b"]
    note = _notice(out, NOKEY)
    assert note["count"] == 1 and said in note["text"], note["text"]


def test_전부_키가_없으면_시작하지_않고_이유를_말한다():
    """이 워크플로는 좌석을 스스로 발굴하지 못한다(엔진은 발굴로 넘어간다) — 0석으로 돌 수 없으니 무엇이 틀렸는지 말하고 멈춘다."""
    r = _node(_DELIB, {"question": "화두", "personas": [{"name": "a"}, {"persona": "b"}]})
    assert r.returncode != 0 and "2석 전부 좌석 키(key)가 없다" in r.stderr and "name" in r.stderr, r.stderr
    r = _node(_DELIB, {"question": "화두", "personas": []})
    assert r.returncode != 0 and "personas 가 비어 있음" in r.stderr, "아예 안 준 것은 종전 문구 그대로다"


_SEAT_ITEMS = [{"key": "a"}, {"agent_type": "b"}, {"key": "", "agent_type": "c"}, {"key": "  ", "agent_type": "d"}, {"key": " e "},
               {"key": None}, {"name": "f"}, "g", None, {"key": 7}, {"key": "h", "agent_type": "i"}]


def test_좌석_키를_읽는_규칙이_엔진과_같다():
    """엔진의 _seat_key 가 정본이다 — 같은 좌석 목록이 웹 길과 MCP 길에서 같은 패널이 돼야 한다."""
    seat_key = _engine_fn("_seat_key")
    want = [k for k in (seat_key(p) for p in _SEAT_ITEMS) if k]
    out = _delib(personas=_SEAT_ITEMS)
    assert _seated(out) == want, f"엔진 {want} · JS {_seated(out)}"
    assert _notice(out, NOKEY)["count"] == len(_SEAT_ITEMS) - len(want)


# ── 반환 자리 셋 — 한 곳이라도 빠지면 그 경로에서는 다시 조용해진다 ──────────────────────────────────
_MIXED = dict(evidence=[{"source": "긴 것", "result": "가" * 2500}, {"source": "둘", "summary": "요약", "body": "본문"}],
              personas=[*_SEATS, {"role": "키 없음"}])
_ALL = {CUT, SHADOW, NOKEY}


def test_체크포인트_의장_실패_정상_반환에_모두_실린다():
    for name, kw in (("체크포인트", {}), ("정상", {"stopAfterRound": 0, "rounds": 2}),
                     ("의장 실패", {"stopAfterRound": 0, "rounds": 2, "decisionFails": True})):
        out = _delib(**_MIXED, **kw)
        assert {x["source"] for x in out["result"]["inputNotices"]} == _ALL, name
        assert all(set(x) == {"source", "count", "text"} and 0 < len(x["text"]) <= 200 for x in out["result"]["inputNotices"]), name
    assert out["result"]["decisionFailed"] is True


def test_알릴_것이_없으면_빈_목록이다():
    """필드가 없는 것(옛 스크립트)과 '알릴 것이 없다' 를 구분한다 — evidenceOmitted·seatLoss 와 같은 규약."""
    assert _delib([{"source": "s", "result": "본문"}])["result"]["inputNotices"] == []
    assert _delib(None)["result"]["inputNotices"] == []


# ── 리스크 심사 오케스트레이터 — 자식 심의의 알림을 제출 기록과 원장으로 넘긴다 ─────────────────────────
def _brief(evidence, seats=None, **panel) -> dict:
    seats = seats or [{"key": "mech-a", "role": "기구", "origin": "primary"}, {"key": "sim-b", "role": "해석", "origin": "primary"}]
    return {"panels": [{"panel_id": "P1", "question": "패널 화두", "rounds": 2, "seats": seats, "evidence": evidence, **panel}]}


def _risk(brief: dict, **extra) -> dict:
    extra.setdefault("decision", "## 리스크 심사 보고서\n판정.\n〔결정문 끝〕")
    return _run(_RISK, {"targetKey": "T1", "briefToken": "tok", "tier": "B"}, brief=brief, **extra)


def _submit_arg(out: dict, name: str):
    prompt = next(c for c in out["calls"] if c["label"].startswith("submit:"))["prompt"]
    line = next((ln.strip() for ln in prompt.split("\n") if ln.strip().startswith(f"{name} = ")), None)
    return None if line is None else json.loads(line[len(name) + 3:])


def test_리스크_심사가_줄인_근거를_제출_기록과_원장에_남긴다():
    """브리프 근거는 길다(변경 원장·선례). 2,000자에서 앞부분만 실려도 패널의 어느 기록에도 안 남아, 원장은 좌석이 브리프를 전부
    본 것으로 읽혔다. 반환(flags)은 원장이 아니다 — 제출 도구의 evidence_omitted 로도 보낸다(앱이 engine_withheld 에 적는다)."""
    out = _risk(_brief([{"key": "E1", "source": "변경 원장", "tool": "diff", "args": "T1", "result": "가" * 4000},
                        {"key": "E0", "source": "scope", "result": "스코프"}]))
    flags = out["result"]["submitted"][0]["flags"]
    assert [(n["source"], n["count"]) for n in flags["inputNotices"]] == [(CUT, 1)]
    assert flags["evidenceOmitted"] == []
    sent = _submit_arg(out, "evidence_omitted")
    assert [x["source"] for x in sent] == [CUT] and "[e:1|E1]" in sent[0]["text"] and "4,000자" in sent[0]["text"]
    assert all(set(x) == {"source", "text"} and 0 < len(x["text"]) <= 200 for x in sent)
    assert any("P1" in ln and "항목 상한 초과 1건" in ln for ln in out["logs"]), "사람이 보는 로그에도 패널 이름과 함께"


def test_리스크_심사가_키_없는_좌석을_말없이_버리지_않는다():
    """종전엔 오케스트레이터가 `.filter(s => s.key)` 로 먼저 버려, 편성된 좌석 하나가 빠진 패널이 '전원 착석' 으로 원장에 들어갔다."""
    seats = [{"key": "mech-a", "role": "기구", "origin": "primary"}, {"role": "키가 빠진 좌석", "origin": "counter"},
             {"key": "sim-b", "role": "해석", "origin": "primary"}]
    out = _risk(_brief([{"key": "E0", "source": "scope", "result": "스코프"}], seats=seats))
    assert _seated(out) == ["mech-a", "sim-b", "delib-baseline-defender"], "키 있는 좌석과 지정 반대석만 앉는다"
    flags = out["result"]["submitted"][0]["flags"]
    assert [(n["source"], n["count"]) for n in flags["inputNotices"]] == [(NOKEY, 1)]
    assert NOKEY in [x["source"] for x in _submit_arg(out, "evidence_omitted")]


def test_제출하지_못한_패널의_보존분에도_남긴다():
    out = _risk(_brief([{"source": "s", "result": "가" * 3000}]), decision="제목 없이 시작한 결정문")
    assert out["result"]["submitted"] == [] and out["result"]["failed"][0]["error"] == "decision_truncated"
    assert [(n["source"], n["count"]) for n in out["result"]["partials"][0]["inputNotices"]] == [(CUT, 1)]


def test_알릴_것이_없는_패널은_종전과_같다():
    out = _risk(_brief([{"key": "E0", "source": "scope", "result": "스코프"}]))
    assert out["result"]["submitted"][0]["flags"]["inputNotices"] == []
    assert _submit_arg(out, "evidence_omitted") == []
