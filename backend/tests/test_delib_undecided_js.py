# Claude 심의 워크플로(hwax-deliberate.js)의 T7(판정 불가 과반 → 측정 계획)이 엔진(deliberation.py)과 같은 규칙으로 도는지 — 같은 입력표를 두 쪽에 넣어 맞댄다
"""docs/deliberation-quality checklist T7 · docs/leftovers-1121 L21-12 · L21-16(엔진 쪽) — 워크플로 쪽(11-22).

실제 Claude 워크플로는 돌리지 않는다(사용자 결정 10-15). 스크립트를 스텁 런타임에서 끝까지 돌린다 — 좌석 답은 좌석 키마다 시험이 정하고
스키마로 거른다(구조화 출력은 선언하지 않은 칸을 받지 않는다). 엔진은 import 하지 않고 T7 의 상수 · 함수만 AST 로 떼어 실행한다
(그 리포의 의존성 · 환경변수를 끌어오지 않게 — tests/test_insight_workflows.py 와 같은 방식).
고정하는 것.
  · 꺼져 있으면 좌석 · 의장 프롬프트 · 스키마 · 결과에 T7 이 없다(끄는 값마다 '안 준 것' 과 바이트까지 같다).
  · 켜는 값은 엔진과 같은 낱말 · 정수로 읽고, 못 읽으면 꺼진 채로 돌며 inputNotices 에 남긴다.
  · '판정 불가' 식은 엔진의 식과 같은 답을 낸다(파이썬 \\W · \\b 는 유니코드, JS 는 ASCII — 그 차이가 새지 않는다).
  · 켜면 수렴 라운드에만 엔진과 같은 지시 · 두 칸이 붙고, **앉은 좌석**의 과반일 때만 의장 전제 · 결정문 머리 표지가 엔진과 같은 글자로 붙는다.
  · 리스크 심사 · 계획서 틀에는 켜도 붙지 않고, 다단 워크플로는 자식에 넘기지 않는다(엔진의 다단 1단). 의장이 결정문을 못 냈으면 표지가 없다.
"""
import ast
import functools
import json
import re
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_DELIB = "infra/pipeline/hwax-deliberate.js"
_ENGINE = _ROOT.parent / "HWAXAgentServer" / "deliberation.py"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node 가 없다")

# 구동기 — 표준입력 {args, final?, decisionFails?}. final 은 좌석 키 → 수렴 라운드 답(덮어쓰기)이고 null 이면 그 좌석은 답하지 못한다.
_NODE_RUN = r"""
const fs = require('fs');
const path = require('path');
const root = process.argv[1], scriptRel = process.argv[2];
const inp = JSON.parse(fs.readFileSync(0, 'utf8'));
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
const calls = [], logs = [], childArgs = [];
const fin = inp.final || {};
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
  calls.push({ label, prompt: String(prompt), schema: o.schema ? JSON.stringify(o.schema) : null });
  const props = (o.schema && o.schema.properties) || {};
  const key = label.includes(':') ? label.slice(label.indexOf(':') + 1) : '';
  if (props.lens) return { lens: '관점', reads: [], recommendation: '권장', concerns: [] };
  if (props.deepen) return { concede: [], rebut: [], deepen: '심화' };
  if (props.final_position) {
    if (fin[key] === null) return null;
    return project({ final_position: '최종', vote: '찬성', ...(fin[key] || {}) }, o.schema);
  }
  if (String(prompt).startsWith('당신은 심의체 의장')) return inp.decisionFails ? null : '## 의사결정문\n결정.\n〔결정문 끝〕';
  if (label === 'explain') return '쉬운 설명';
  if (label === 'ra-save') return '77';
  if (label === 'conv-save') return 'conv-1';
  return null;
}
const parallel = fns => Promise.all(fns.map(f => f()));
const log = m => { logs.push(String(m)); };
const run = (rel, a) => {
  const src = fs.readFileSync(path.resolve(root, rel), 'utf8').replace(/^export const meta/m, 'const meta');
  return new AsyncFunction('args', 'agent', 'parallel', 'log', 'phase', 'workflow', src)(a, agent, parallel, log, () => {}, workflow);
};
const workflow = async (ref, a) => { childArgs.push(a); return run(ref.scriptPath, a); };
run(scriptRel, inp.args)
  .then(result => { process.stdout.write(JSON.stringify({ result, calls, logs, childArgs })); })
  .catch(e => { process.stderr.write(String((e && e.stack) || e)); process.exit(1); });
"""

_SEATS = [{"key": "mech-a", "role": "기구"}, {"key": "rel-b", "role": "신뢰성"}, {"key": "mat-c", "role": "재료"}]
_U = {"stance": "판정 불가", "next_measurement": "접촉각을 재서 30도 이하면 A 안"}
_TWO_OF_THREE = {"mech-a": _U, "rel-b": {"stance": "판정 불가 — 데이터 없음"}}
_LEGACY_TAIL = " 결정 가능하도록 구체적으로."
_ON = SimpleNamespace(undecided=1, chair_template="default")


def _run(args: dict, script: str = _DELIB, **extra) -> dict:
    r = subprocess.run(["node", "-e", _NODE_RUN, str(_ROOT), script], input=json.dumps({"args": args, **extra}),
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-3000:]
    return json.loads(r.stdout)


def _delib(final=None, **kw) -> dict:
    extra = {"final": final or {}, **({"decisionFails": True} if kw.pop("decisionFails", False) else {})}
    return _run({"question": "코팅 A 안과 B 안 가운데 무엇으로 갈 것인가", "personas": _SEATS, "rounds": 2,
                 "saveReport": True, "saveConversation": True, **kw}, **extra)


def _calls(out: dict, prefix: str) -> list:
    return [c for c in out["calls"] if c["label"].startswith(prefix)]


def _chair(out: dict) -> str:
    return next(c["prompt"] for c in out["calls"] if c["label"] == "decision")


@functools.lru_cache(maxsize=1)
def _engine() -> SimpleNamespace:
    """엔진의 T7 상수 · 함수와 켜고 끄는 낱말표만 AST 로 떼어 실행한다(엔진 모듈 전체를 읽지 않는다)."""
    if not _ENGINE.exists():
        pytest.skip(f"형제 리포 없음: {_ENGINE}")
    fns = {"_undecided_on", "_undecided_ask", "_is_undecided", "_undecided_seats", "_undecided_majority",
           "_undecided_chair_note", "_undecided_mark"}
    names = {"_UNDECIDED_RE", "_UNDECIDED_TEMPLATES_OFF", "_ONOFF_WORDS"}
    tree = ast.parse(_ENGINE.read_text(encoding="utf-8"))
    body = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name in fns)
            or (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in names for t in n.targets))]
    assert len(body) == len(fns) + len(names), "엔진의 T7 모양이 바뀌었다 — 이 맞대기 시험도 고쳐라"
    ns: dict = {"re": re}
    exec(compile(ast.Module(body=body, type_ignores=[]), str(_ENGINE), "exec"), ns)  # noqa: S102 — 형제 리포의 우리 코드다
    return SimpleNamespace(**{k: ns[k] for k in fns | names})


def _js_line(name: str) -> str:
    m = re.search(rf"^const {name} = (.+)$", (_ROOT / _DELIB).read_text(encoding="utf-8"), re.M)
    assert m, f"hwax-deliberate.js 에서 {name} 을 못 찾았다"
    return m.group(1).strip()


def _node_eval(expr: str, inputs: list) -> list:
    """JS 식 하나(정규식 · Map)를 node 로 풀어 입력마다 답을 받는다."""
    code = ("const x = eval(process.argv[1]); const xs = JSON.parse(require('fs').readFileSync(0, 'utf8'));"
            "process.stdout.write(JSON.stringify(x instanceof RegExp ? xs.map(s => x.test(s)) : Object.fromEntries(x)));")
    r = subprocess.run(["node", "-e", code, expr], input=json.dumps(inputs), capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr[-2000:]
    return json.loads(r.stdout)


# ── 꺼짐 ─────────────────────────────────────────────────────────────
def test_꺼져_있으면_프롬프트_스키마_결과에_T7_이_없고_끄는_값마다_안_준_것과_같다():
    base = _delib(_TWO_OF_THREE)
    conv = _calls(base, "r2:")
    assert len(conv) == 3 and all(c["prompt"].endswith(_LEGACY_TAIL) for c in conv), "꺼져 있는데 수렴 지시가 달라졌다"
    assert not any("next_measurement" in (c["schema"] or "") or "next_measurement" in c["prompt"] for c in base["calls"])
    assert "판정 불가 과반" not in _chair(base) and "판정 불가 과반" not in json.dumps(base["result"], ensure_ascii=False)
    assert "undecidedMajority" not in base["result"] and "다음에 잴 것" not in json.dumps(base["calls"], ensure_ascii=False)
    for off in (0, "0", "off", "OFF", False, "no", " false ", "", None):
        out = _delib(_TWO_OF_THREE, undecided=off)
        assert (out["calls"], out["result"]) == (base["calls"], base["result"]), f"undecided={off!r} 가 안 준 것과 다르다"


# ── 켜는 값 ───────────────────────────────────────────────────────────
def _engine_reads(v):
    """엔진 _resolve_opts 가 이 값을 어떻게 읽는가 — 켬 True · 끔 False · 못 읽음 None(그 자리의 셈 그대로: 낱말표 → int)."""
    if v is None or v == "":
        return False
    if isinstance(v, str):
        v = _engine()._ONOFF_WORDS.get(v.strip().lower(), v)
    try:
        return int(v) != 0
    except (ValueError, TypeError):
        return None


def test_켜고_끄는_낱말은_엔진과_같다():
    js = _node_eval(_js_line("UNDECIDED_WORDS"), [])
    assert js == {k: bool(v) for k, v in _engine()._ONOFF_WORDS.items()}


@pytest.mark.parametrize("v", [1, 2, -1, 1.5, 0.5, True, "1", " 1 ", "+2", "on", "ON", "yes", "True", "off", "no", 0, "0",
                               "maybe", "1.5", "켬", [1], {"a": 1}])
def test_켜는_값은_엔진과_같이_읽고_못_읽으면_꺼진_채로_알린다(v):
    want = _engine_reads(v)
    out = _delib(_TWO_OF_THREE, undecided=v)
    on = any("next_measurement" in (c["schema"] or "") for c in _calls(out, "r2:"))
    notes = [n for n in out["result"]["inputNotices"] if n["source"] == "요청 값 해석 불가"]
    assert on is bool(want), f"undecided={v!r} — 엔진은 {want} 로 읽는데 워크플로는 {'켰다' if on else '껐다'}"
    assert bool(notes) is (want is None), notes
    if notes:
        assert "undecided=" in notes[0]["text"] and len(notes[0]["text"]) <= 200


# ── '판정 불가' 식 ─────────────────────────────────────────────────────
_RE_TABLE = [
    # 엔진 시험의 표(tests/test_undecided_plan.py) — 센다
    ("판정 불가", True), ("판정불가", True), ("「판정 불가」 — 측정 필요", True), ("판정 불가 — 다음에 측정할 것: 접촉각", True),
    ("판단 불가", True), ("Undecided", True), ("cannot be decided yet", True), ("판정 불가능", True), ("판정 불가(근거 부족)", True),
    ("판정 불가. 접촉각 자료가 없다", True), ("판정 불가입니다", True),
    # 세지 않는다 — 부정 · 지난 일 · 다른 낱말 · 머리가 아님
    ("판정 불가는 아니다", False), ("판정 불가가 아님 — A 안", False), ("판정 불가도 아니고 반대도 아니다", False), ("판정 불가능하지 않다", False),
    ("판정 불가였으나 근거가 생겨 A 안", False), ("판정 불가했지만 지금은 동의", False), ("판정 불가피 — A 안으로 간다", False),
    ("판단 불가결한 자료는 다 있다", False), ("동의", False), ("조건부 동의 — 판정 불가였으나 근거가 생겼다", False), ("A 안", False), ("", False),
    # 파이썬 \W · \b(유니코드)와 JS \W · \b(ASCII)가 갈리는 자리 — 앞의 한글 · 숫자 · 밑줄, 뒤의 한글
    ("조건부 동의 — 판정 불가", False), ("동의 판정 불가", False), ("A안 판정 불가", False), ("1) 판정 불가", False), ("_판정 불가", False),
    ("undecided한 상태", False), ("undecidedness", False), ("판정 불가 아님", False),
    ("— 판정 불가", True), ("  『판정 불가』", True), ("﻿판정 불가", True), ("판정 불가", True), ("UNDECIDED.", True),
    ("Cannot decide", True), ("cannot judge", True), ("cannot be decidedly said", False), ("**판정 불가**", True),
]


def test_판정_불가_식은_엔진과_같은_답을_낸다():
    eng = _engine()._UNDECIDED_RE
    strings = [s for s, _w in _RE_TABLE]
    js = _node_eval(_js_line("UNDECIDED_RE"), strings)
    for (s, want), got in zip(_RE_TABLE, js, strict=True):
        e = eng.search(s) is not None
        assert e is want, f"표가 엔진과 어긋났다 — {s!r}: 엔진 {e}"
        assert got is e, f"{s!r} — 엔진 {e} · 워크플로 {got}"


# ── 꺼지는 틀 · 다단 ─────────────────────────────────────────────────
def test_꺼지는_틀은_엔진과_같고_켜도_안_켠_것과_같다():
    js = re.findall(r"'([a-z-]+)'", _js_line("UNDECIDED_TEMPLATES_OFF"))
    assert set(js) == set(_engine()._UNDECIDED_TEMPLATES_OFF) and len(js) == len(set(js))
    for tpl in [*js, "risk-review-sealed"]:
        off, on = _delib(_TWO_OF_THREE, chairTemplate=tpl), _delib(_TWO_OF_THREE, chairTemplate=tpl, undecided=1)
        assert (on["calls"], on["result"]) == (off["calls"], off["result"]), tpl
        assert any("붙지 않는다" in ln for ln in on["logs"]), "켜도 안 붙는다는 것을 로그에 남긴다"
    assert "next_measurement" in json.dumps(_delib(_TWO_OF_THREE, chairTemplate="mechanism", undecided=1)["calls"]), \
        "단독 mechanism 심의는 켤 수 있다(엔진은 틀 이름이 아니라 다단 1단에서 끈다)"


@pytest.mark.parametrize("script, args", [
    ("infra/pipeline/hwax-sim-deliberate.js", {"simRounds": 2, "simPersonas": [{"key": "cae-a", "role": "해석"}], "buildPlan": True}),
    ("infra/pipeline/hwax-test-plan.js", {}),
])
def test_다단_워크플로는_자식에_undecided_를_넘기지_않는다(script, args):
    """엔진은 다단 심의 1단(mechanism)을 세우며 undecided 를 끈다 — 1단 결정문이 측정 계획이 되면 2단이 메커니즘 없이 해석을 설계한다.
    워크플로에서는 부모가 이 칸을 자식에 넘기지 않는 것이 같은 일이다(뒤 단은 꺼지는 틀이다)."""
    out = _run({"question": "화두", "personas": _SEATS, "rounds": 2, "saveConversation": False, "undecided": 1, **args},
               script=script, final=_TWO_OF_THREE)
    assert out["childArgs"] and all(not a.get("undecided") for a in out["childArgs"])
    assert not any("next_measurement" in c["prompt"] or "next_measurement" in (c["schema"] or "") for c in out["calls"])
    assert "판정 불가 과반" not in json.dumps(out["result"], ensure_ascii=False)


# ── 켜짐 ─────────────────────────────────────────────────────────────
def test_켜면_수렴_라운드에만_엔진과_같은_지시와_두_칸이_붙는다():
    off, on = _delib(_TWO_OF_THREE, rounds=3), _delib(_TWO_OF_THREE, rounds=3, undecided=1)
    for pre in ("r1:", "r2:"):
        assert [(c["prompt"], c["schema"]) for c in _calls(on, pre)] == [(c["prompt"], c["schema"]) for c in _calls(off, pre)], pre
    ask = _engine()._undecided_ask(_ON)
    assert ask
    conv_on, conv_off = _calls(on, "r3:"), _calls(off, "r3:")
    assert len(conv_on) == 3 and [c["prompt"] for c in conv_on] == [c["prompt"] + ask for c in conv_off]
    schema = json.loads(conv_on[0]["schema"])
    assert {"stance", "next_measurement"} <= set(schema["properties"]) and schema["required"] == ["persona", "final_position", "vote"]
    assert schema["additionalProperties"] is False


_MAJ_CASES = {
    "셋_가운데_둘": (_SEATS, _TWO_OF_THREE, {}),
    "셋_가운데_하나": (_SEATS, {"mech-a": _U}, {}),
    "넷_가운데_딱_절반": (_SEATS + [{"key": "sw-d", "role": "SW"}], _TWO_OF_THREE, {}),
    "다섯_가운데_답한_둘이_모두": (_SEATS + [{"key": "sw-d", "role": "SW"}, {"key": "xd-e", "role": "XD"}],
                          {**_TWO_OF_THREE, "mat-c": None, "sw-d": None, "xd-e": None}, {}),
    "셋_가운데_둘_한_석_유실": (_SEATS, {**_TWO_OF_THREE, "mat-c": None}, {}),
    "vote_머리": (_SEATS, {"mech-a": {"stance": "동의", "vote": "판정 불가 — 다음에 측정할 것: 접촉각"},
                          "rel-b": {"vote": "판정 불가"}}, {}),
    "부정과_지난_일": (_SEATS, {"mech-a": {"stance": "판정 불가는 아니다"}, "rel-b": {"stance": "판정 불가였으나 근거가 생겨 A 안"}}, {}),
    "영어": (_SEATS, {"mech-a": {"stance": "Undecided"}, "rel-b": {"vote": "cannot be decided yet"}}, {}),
    "선택지_표결": (_SEATS, {"mech-a": {"vote": "판정 불가 — 다음에 측정할 것: 접촉각"}, "rel-b": {"vote": "판정 불가"}},
                {"options": ["A 안", "B 안"]}),
    "지정_반대석도_앉은_좌석": (_SEATS[:2], {"mech-a": _U, "rel-b": _U}, {"chairTemplate": "diagnosis"}),
}


@pytest.mark.parametrize("case", list(_MAJ_CASES))
def test_과반은_앉은_좌석으로_세고_의장_전제와_표지가_엔진과_같은_글자다(case):
    seats, final, kw = _MAJ_CASES[case]
    out = _delib(final, personas=seats, undecided=1, **kw)
    seated = [c["label"].split(":", 1)[1] for c in _calls(out, "r2:")]   # 앉은 좌석 전원(지정 반대석 포함) — 답하지 못한 좌석도 불린다
    r3 = json.loads(_calls(out, "r2:")[0]["schema"])
    last = [{k: v for k, v in {"final_position": "최종", "vote": "찬성", **(final.get(k) or {})}.items() if k in r3["properties"]}
            for k in seated if final.get(k, {}) is not None]
    e = _engine()
    want = e._undecided_majority(_ON, last, len(seated))
    got = out["result"].get("undecidedMajority")
    assert (tuple(got.values()) if got else None) == want, f"{case} — 엔진 {want} · 워크플로 {got}"
    chair, dec = _chair(out), out["result"]["decision"]
    if want:
        assert e._undecided_chair_note(want) + "\n산출: ## " in chair
        mark = e._undecided_mark(want) + "\n\n## 의사결정문"
        assert dec.startswith(mark) and out["result"]["decisionText"].startswith(mark)
        assert out["result"]["decisionTruncated"] is False, "표지는 절단 판정 뒤에 찍는다"
        explain = next(c["prompt"] for c in out["calls"] if c["label"] == "explain")
        assert e._undecided_mark(want) in explain, "쉬운 설명은 결론부가 측정 계획임을 안다(엔진과 같은 차례)"
    else:
        assert "판정 불가 과반" not in chair and "판정 불가 과반" not in dec


def test_회의록과_대화에_다음에_잴_것이_실리고_화면이_칠할_입장_칸은_없다():
    """엔진은 다음 측정을 기록용 발언에 싣는다(_say_of full). 워크플로의 기록은 RA 회의록과 대화 저장이다. 워크플로에는 코드 집계가 없고
    대화에 입장 칸(meta.stance)을 싣지 않는다 — 화면(stanceClass)은 모르는 입장 글을 초록(동의)으로 칠한다. 실으려면 엔진처럼 판정 불가를
    '미표명' 으로 바꿔 실어야 한다(_stance_label)."""
    out = _delib(_TWO_OF_THREE, undecided=1)
    for label in ("ra-save", "conv-save"):
        p = next(c["prompt"] for c in out["calls"] if c["label"] == label)
        assert "다음에 잴 것 — 접촉각을 재서 30도 이하면 A 안" in p, label
        assert '"stance"' not in p, label


def test_의장이_결정문을_못_내면_표지가_없다():
    out = _delib(_TWO_OF_THREE, undecided=1, decisionFails=True)
    res = out["result"]
    assert res["decisionFailed"] is True and res["decision"] is None
    assert res["undecidedMajority"] == {"undecided": 2, "seated": 3}, "과반은 의장 전에 정해진다(엔진은 그때 경고를 낸다)"
    assert "■ 판정 불가 과반" not in json.dumps(res, ensure_ascii=False)
    assert "[판정 불가 과반" in _chair(out)


def test_스킬_설명과_머리_주석이_켜는_칸을_말한다():
    src = (_ROOT / _DELIB).read_text(encoding="utf-8")
    when = re.search(r"whenToUse: '([^']+)'", src).group(1)
    assert "undecided?" in when and "측정 계획" in when
    head = src.split("export const meta", 1)[0]
    assert "//   - undecided       :" in head and "undecidedMajority" in head
