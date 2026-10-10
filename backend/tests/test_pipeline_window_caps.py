# Claude 로 돌리는 심의 워크플로(infra/pipeline)가 상한을 서브에이전트 창에서 유도하고 줄인 것을 알리는지
"""MCP 경로의 심의는 엔진이 아니라 워크플로 스크립트가 돈다 — 좌석·의장은 이 세션의 Claude 서브에이전트다(GLM 이 아니다).
사용자 지침은 '전부' 다(docs/risk-review-redesign D-21) — 작은 창 시절에 박은 상한은 올리거나 없애되, Claude 서브에이전트의 창을
넘기지 않는 선을 지킨다. 그래서 상한은 args.ctxTokens(기본 200,000 토큰)에서 유도하고, 작은 창(16,384)에서는 종전 값 그대로다
(그 바닥의 알림 장치는 test_delib_pipeline_js · test_infra_pipeline_notices 가 본다).

종전 자리는 이렇다.
  - 근거 12건 · 합 11,000자 · 항목 2,000자(엔진은 120건 · 500,000자 · 150,000자) — 같은 브리프가 Claude 길에서는 열세 번째부터 빠졌다.
  - 1라운드 근거 해석(reads)을 600자에서 표식 없이 끊어 다음 라운드와 의장에게 넘겼다. 반박 인용은 80자.
  - 대화 저장이 발언을 19,500자에서 표식 없이 잘랐고, meta 의 조항을 1,200자·반박을 4건에서 끊었다.
  - 쉬운 설명 입력 16,000자 · 의장 크기 경고 40만 자(창보다 크다) · 수치 대조 목록 40건.
  - 리스크 심사 길은 1라운드 발언에서 reads 를 통째로 뺐고, 발언을 줄이거나 버린 것을 원장에 알리지 않았다.
  - 시뮬 2단 심의는 결정문 꼬리 발췌가 '쉬운 설명' 을 집었고, 조항을 12건에서 먼저 잘라 자식의 알림을 막았고, 자식의 알림을 승계하지 않았다.
"""
import json
import re

import pytest

from tests.test_infra_pipeline_notices import _DELIB, _RISK, _SEATS, _brief, _run, _submit_arg

_SIM = "infra/pipeline/hwax-sim-deliberate.js"
_DECISION = "## 의사결정문\n결정.\n〔결정문 끝〕"


def _delib(evidence=None, ctx=None, **kw) -> dict:
    """ctx=None 이면 ctxTokens 를 주지 않는다(기본 200,000 토큰)."""
    extra = {k: kw.pop(k) for k in ("decision", "decisionFails", "seat") if k in kw}
    args = {"question": "화두", "personas": _SEATS, "evidence": evidence or [], "stopAfterRound": 1,
            "saveConversation": False, **({"ctxTokens": ctx} if ctx else {}), **kw}
    return _run(_DELIB, args, **extra)


def _prompt(out: dict, prefix: str) -> str:
    return next(c["prompt"] for c in out["calls"] if c["label"].startswith(prefix))


def _notes(out: dict, key: str) -> dict:
    return {x["source"]: x for x in out["result"][key]}


# ── 근거 상한 — 창에서 유도한다 ──────────────────────────────────────────────────────────
def test_기본_창에서는_근거를_엔진과_같은_건수까지_싣는다():
    """**이 구획의 이유다** — 브리프 근거 15건(건당 3,000자)이 종전엔 5건만, 그것도 2,000자씩 실렸다(12건·11,000자·2,000자)."""
    out = _delib([{"key": f"E{i}", "source": f"s{i}", "result": "가" * 3000} for i in range(15)])
    prompt = _prompt(out, "r1:")
    assert "[e:15|E14]" in prompt and "…[" not in prompt.split("[e:1|E0]")[1].split("\n")[0]
    assert out["result"]["evidenceOmitted"] == [] and out["result"]["inputNotices"] == []


def test_기본_창의_상한은_서브에이전트_창_200000_토큰에서_나온다():
    """합 = (200,000 − 출력 32,000) × 30% = 50,400자, 항목 = 합 × 30% = 15,120자. 넘으면 종전처럼 표식·알림이 붙는다."""
    out = _delib([{"key": "DOC", "source": "발표자료", "result": "가" * 40_000}])
    note = _notes(out, "inputNotices")["사전 근거 항목 상한 초과"]
    assert "15,120자" in note["text"] and "40,000자" in note["text"]
    assert "…[40000자 중 15,120자]" in _prompt(out, "r1:")
    over = _delib([{"source": f"s{i}", "result": "가" * 15_000} for i in range(5)])
    assert _notes(over, "evidenceOmitted")["사전 근거 예산 초과"]["text"].count("50,400자") == 1


def test_1M_창으로_돌리면_결정문_한_건이_통째로_들어간다():
    out = _delib([{"key": "DEC", "source": "앞 심의 결정문", "result": "나" * 75_000}], ctx=1_048_576)
    assert out["result"]["inputNotices"] == [] and "나" * 75_000 in _prompt(out, "r1:")


def test_건수는_엔진과_같은_120건에서_끊고_알린다():
    out = _delib([{"source": f"s{i}", "result": f"본문 {i}"} for i in range(125)])
    note = _notes(out, "evidenceOmitted")["사전 근거 건수 초과"]
    assert note["count"] == 5 and "120건" in note["text"]


# ── 라운드 사이에 넘기는 글 ──────────────────────────────────────────────────────────────
def test_1라운드_근거_해석을_600자에서_끊지_않는다():
    reads = ["[e:1] 두께 0.8→0.6 mm " + "가" * 700, "끝 인용 [e:9] 힌지 간극 0.2 mm"]
    out = _delib([], seat={"reads": reads}, stopAfterRound=0, rounds=2, decision=_DECISION)
    final = _prompt(out, "r2:")
    assert "끝 인용 [e:9] 힌지 간극 0.2 mm" in final, "수렴 라운드 좌석이 1라운드 근거 해석의 뒤쪽을 못 본다"
    chair = next(c["prompt"] for c in out["calls"] if c["prompt"].startswith("당신은 심의체 의장"))
    assert "끝 인용 [e:9]" in chair, "의장이 1라운드 근거 해석의 뒤쪽을 못 본다"


def test_반박_인용을_80자에서_끊지_않는다():
    quote = "브래킷 두께 0.6 mm 는 낙하 하중에서도 충분하다는 앞 좌석의 주장 — " + "근거 문장 " * 30 + "끝"
    rebut = [{"target": "sim-b", "quote": quote, "counter": "항복을 넘는다", "basis": "[e:2]"}]
    out = _delib([], seat={"rebut": rebut}, stopAfterRound=0, rounds=3, decision=_DECISION)
    assert quote in _prompt(out, "r3:"), "다음 라운드가 반쪽 인용을 받는다"


# ── 대화 저장 — 자르지 않고 나눈다 ───────────────────────────────────────────────────────
def _conv_messages(out: dict) -> list[dict]:
    prompt = _prompt(out, "conv-save")
    return json.loads(re.search(r"^messages=(.*)$", prompt, re.M).group(1))


def test_대화_저장은_긴_발언을_나눠_싣고_meta_를_자르지_않는다():
    rec = "권장 " + "다" * 21_000 + " 끝 인용 [e:3]"
    nn = "양보 불가 — " + "라" * 1500
    out = _delib([], seat={"recommendation": rec, "non_negotiable": nn}, stopAfterRound=0, rounds=2,
                 decision=_DECISION, saveConversation=True, personas=[_SEATS[0]])
    msgs = [m for m in _conv_messages(out) if m["role"] == "persona" and m["persona"] == "mech-a"]
    r1 = [m for m in msgs if m["round"] == 1]
    assert [m["content"].split("\n", 1)[0] for m in r1] == ["(발언 1/2)", "(발언 2/2)"]
    assert "".join(m["content"].split("\n", 1)[1] for m in r1).endswith("끝 인용 [e:3]")
    assert all(len(m["content"]) <= 20_000 for m in msgs), "종전 포털·게이트웨이(20,000)에도 들어가야 한다"
    last = [m for m in msgs if m["round"] == 2]
    assert last[0]["meta"]["non_negotiable"] == nn, "조항을 1,200자에서 끊었다"
    assert out["result"]["conversationSkipped"] is None


# ── 결정 뒤 ──────────────────────────────────────────────────────────────────────────────
def test_쉬운_설명은_기본_창에서_긴_결정문을_전문으로_읽는다():
    decision = "## 의사결정문\n" + "(1) 결론. " + "마" * 40_000 + "\n(10) 한계 — 끝\n〔결정문 끝〕"
    out = _delib([], stopAfterRound=0, rounds=2, decision=decision)
    assert out["result"]["plainPartial"] is False
    assert "(10) 한계 — 끝" in next(c["prompt"] for c in out["calls"] if c["label"] == "explain")
    assert out["result"]["decisionText"].endswith("(10) 한계 — 끝"), "결정문만(쉬운 설명 앞) 돌려준다"
    assert "■ 쉬운 설명" in out["result"]["decision"]


def test_수치_대조_목록을_40건에서_끊지_않는다():
    decision = "## 의사결정문\n" + " ".join(f"{1000 + i}.5 N" for i in range(45)) + "\n〔결정문 끝〕"
    out = _delib([], stopAfterRound=0, rounds=2, decision=decision)
    assert len(out["result"]["citationAudit"]["unmatched"]) == 45


def test_양보_불가_조항을_넘으면_반환값에_남긴다():
    nns = [f"조항 {i}" for i in range(165)]
    out = _delib([], continueFrom={"summary": "앞 결정", "roundsSoFar": 3, "nonNegotiables": nns})
    note = _notes(out, "inputNotices")["양보 불가 조항 상한 초과"]
    assert note["count"] == 5 and "160건" in note["text"]
    assert "- 조항 159" in _prompt(out, "r4:") and "- 조항 160" not in _prompt(out, "r4:")
    assert _delib([], continueFrom={"summary": "앞", "roundsSoFar": 3, "nonNegotiables": nns[:21]})["result"]["inputNotices"] == []


# ── 리스크 심사 길 — 원장에 내는 발언 ────────────────────────────────────────────────────────
def _risk(brief: dict, **extra) -> dict:
    extra.setdefault("decision", "## 리스크 심사 보고서\n판정.\n〔결정문 끝〕")
    args = {"targetKey": "T1", "briefToken": "tok", "tier": "B", **extra.pop("args", {})}
    return _run(_RISK, args, brief=brief, **extra)


def test_리스크_심사_1라운드_발언에_근거_해석을_싣는다():
    reads = ["[e:1|E1] 두께 0.8→0.6 mm — 힌지 응력 증가", "[c:CK-3] 낙하 실패 사례와 같은 계면"]
    out = _risk(_brief([{"key": "E1", "source": "변경 원장", "result": "두께 0.8→0.6"}]),
                seat={"lens": "관점", "reads": reads, "recommendation": "권장"})
    first = next(t for t in _submit_arg(out, "turns") if t["round"] == 1)
    assert all(r in first["say"] for r in reads), "1라운드 인용이 원장에 안 간다"


def test_리스크_심사가_원장에_내며_줄인_발언을_원장에_알린다():
    """발언은 고정 칸(2,000자)으로 자르지 않는다 — 결정문을 통째로 싣고 제출 에코 예산(60,000자)에 남는 몫에 맞출 때만 줄이고, 그 상한을
    원장에 적는다(검토 P-3·X-4). 결정문 55,000자면 1라운드 좌석 셋(지정 반대석 포함)의 2,600자 권장이 남는 몫을 넘는다."""
    out = _risk(_brief([{"key": "E0", "source": "scope", "result": "스코프"}]), seat={"recommendation": "라" * 2600},
                decision="## 리스크 심사 보고서\n" + "판" * 55_000 + "\n〔결정문 끝〕")
    by = {x["source"]: x["text"] for x in _submit_arg(out, "evidence_omitted")}
    flags = out["result"]["submitted"][0]["flags"]
    assert flags["sayCut"] == 3, "1라운드 좌석 셋(지정 반대석 포함)"
    assert "발언 길이 상한 초과" in by and f"{flags['sayCap']:,}자" in by["발언 길이 상한 초과"], by
    assert "60,000자" in by["발언 길이 상한 초과"] and "2000자" not in by["발언 길이 상한 초과"]
    small = _risk(_brief([{"key": "E0", "source": "scope", "result": "스코프"}]), seat={"recommendation": "라" * 2600})
    assert small["result"]["submitted"][0]["flags"]["sayCut"] == 0, "예산 안이면 2,000자 넘는 발언도 줄이지 않는다"


def test_리스크_심사가_창을_자식_심의에_넘긴다():
    out = _risk(_brief([{"key": "E0", "source": "scope", "result": "가" * 3000}]), args={"ctxTokens": 16384})
    assert any(n["source"] == "사전 근거 항목 상한 초과" for n in out["result"]["submitted"][0]["flags"]["inputNotices"])
    out = _risk(_brief([{"key": "E0", "source": "scope", "result": "가" * 3000}]))
    assert out["result"]["submitted"][0]["flags"]["inputNotices"] == [], "기본 창이면 3,000자 근거는 통째로 실린다"


def test_리스크_심사가_이번에_돌리지_않은_패널을_반환에_남긴다():
    brief = _brief([{"key": "E0", "source": "scope", "result": "스코프"}])
    brief["panels"] = [dict(brief["panels"][0], panel_id=f"P{i}") for i in range(3)]
    out = _risk(brief)
    assert [s["panel_id"] for s in out["result"]["submitted"]] == ["P0"]
    assert out["result"]["panelsRemaining"] == ["P1", "P2"]


# ── 시뮬 2단 — 단계 사이 발췌 ────────────────────────────────────────────────────────────
def test_시뮬_2단은_결정문만_발췌해_넘기고_발췌를_알리고_자식_알림을_승계한다():
    decision = "## 메커니즘 결론\n" + "(1) 상태변수 " + "바" * 30_000 + "\n(5) 반증 관측 — 끝\n〔결정문 끝〕"
    out = _run(_SIM, {"question": "화두", "personas": _SEATS, "rounds": 2, "simRounds": 2, "saveConversation": False,
                      "simPersonas": [{"key": "cae-a", "role": "해석"}]}, decision=decision)
    # 이전 요약은 유임 좌석이 받는다(신규 좌석은 앵커링을 막으려 1라운드에 받지 않는다).
    stage2 = next(c["prompt"] for c in out["calls"] if c["label"] == "r3:mech-a")
    summary = stage2.split("[이전 심의 요약 — ")[1].split("\n\n[")[0]
    assert "(5) 반증 관측 — 끝" in summary and "■ 쉬운 설명" not in summary, "꼬리 발췌가 결정문 대신 쉬운 설명을 집었다"
    res = out["result"]
    assert res["handoffExcerpts"] == [], "기본 창이면 결정문 3만 자는 전문이 넘어간다"
    assert "inputNotices" in res["mechanism"] and "evidenceOmitted" in res["simPlan"]


# ── 결정적 대화 저장 스크립트(infra/scripts/save-delib-conversation.py) — 워크플로·포털과 같은 모양 ──────────────
def test_결정적_대화_저장_스크립트도_meta_와_인용을_자르지_않는다():
    """워크플로가 에코 예산 때문에 건너뛴 심의를 LLM 없이 저장하는 스크립트다. 워크플로·포털(웹 길)과 '같은 자르기' 를 하던 것이라
    둘이 자르지 않게 되면 이것도 같이 바뀌어야 한다 — 그대로 두면 같은 심의가 저장 길에 따라 다른 조항을 승계한다."""
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "infra" / "scripts" / "save-delib-conversation.py"
    spec = importlib.util.spec_from_file_location("save_delib_conversation", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    nn = "양보 불가 — " + "가" * 1500
    rebut = [{"target": f"s{i}", "quote": "인용 " * 50, "counter": "반박 " * 100, "basis": "근거 " * 40} for i in range(6)]
    assert mod._meta({"non_negotiable": nn, "rebut": rebut}) == {"non_negotiable": nn, "rebut": rebut}
    assert ("인용 " * 50).strip() in mod._item(rebut[0])
    chunks = list(mod._chunks("나" * 40_000, "발언"))
    assert len(chunks) == 3 and "".join(c.split("\n", 1)[1] for c in chunks) == "나" * 40_000, "나누되 버리지 않는다(종전 그대로)"


# ── 근거 곁 필드(출처·도구·인자) — 엔진과 같은 상한, 끊으면 원문 길이 ─────────────────────────────
def test_근거_곁_필드는_엔진과_같은_상한에서_끊고_원문_길이를_남긴다():
    """엔진(deliberation._cut_mark — 출처 200·도구 80·인자 DELIB_EVID_ARGS_MAX 1,200)과 같은 값·같은 표식이다. 종전 JS 는 출처 120·
    인자 400 에서 말없이 끊어, 같은 근거가 웹 길과 Claude 길에서 다른 출처·인자로 좌석에 갔다."""
    src, args = "변경 원장 " + "가" * 250, '{"q": "' + "P" * 1500 + '"}'
    line = next(ln for ln in _prompt(_delib([{"key": "E1", "source": src, "tool": "risk_get_diff", "args": args,
                                             "result": "본문"}]), "r1:").split("\n") if "[e:1|E1]" in ln)
    assert f"…[{len(src):,}자 중 앞 200자]" in line and src[:200] in line
    assert f"…[{len(args):,}자 중 앞 1,200자]" in line and args[:1200] in line
    short = _delib([{"key": "E1", "source": "scope", "tool": "brief", "args": "T1", "result": "스코프"}])
    assert "· [e:1|E1] [scope · brief(T1)] 스코프" in _prompt(short, "r1:"), "상한 안이면 종전과 같다"
