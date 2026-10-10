# Claude 로 돌린 리스크 심사가 원장에 내는 발언 — 엔진과 같은 순서로, 고정 칸 상한 없이, 제출 에코 예산에 들 때까지만 줄이는지
"""hwax-risk-review.js 는 패널 결과를 에이전트가 risk_submit_panel_result 의 인자로 되받아 적게 해서 원장에 낸다(에코). 두 결함이
같은 자리에서 났다.

  - 검토 P-3 — 1라운드 발언을 [관점, 해석(reads)…, 권장, 우려…] 로 이어 2,000자(앱 화면 발췌 칸)에서 꼬리를 잘랐다. M1 이 해석을 넣고
    600자 절단도 없애자 해석이 긴 좌석은 권장과 우려가 원장에서 사라졌다(권장은 position 에 남지만 우려는 어디에도 없다). 엔진의 기록용
    발언(deliberation._say_of full)은 관점 → 권장 → 해석 → 우려 순이라 같은 패널이 웹 길과 Claude 길에서 다른 모양이 됐다. 게다가 앱은
    이제 원문을 say 로 남기고 발췌를 스스로 만든다(HWAXRisk R-63) — 여기서 먼저 2,000자로 자르면 그 수리가 Claude 길에는 닿지 않는다
    (D-21 이 걷기로 한 '앱이 받는 발언 2,000자').
  - 검토 X-4 — 같은 변경으로 발언 JSON 이 커져, 결정문에 남는 몫이 줄었다(7석×3라운드 실측: 30,492자 → 22,078자). 결정문 25,000자인
    패널이 M1 전에는 제출되고 지금은 payload_too_large 로 웹에 안 올라간다(D-23 위반). 결정적으로 다시 낼 도구도 없다.

고친 규칙 — 결정문은 통째로 싣는다(앱이 risk_spec 을 파싱한다). 발언은 남는 몫에 맞추되, 다 들어가면 손대지 않고, 넘을 때만 가장 긴
글부터 같은 상한으로 줄이고(표식) 그 상한과 줄인 수를 원장과 반환에 남긴다. 1라운드는 해석을 줄이고 권장·우려를 지킨다.

스크립트를 스텁 런타임에서 실제로 돌린다(test_infra_pipeline_notices 의 구동기 — 좌석 답은 시험이 정한다).
"""
import json

from tests.test_infra_pipeline_notices import _RISK, _brief, _run, _submit_arg

_BUDGET = 60_000
_SEATS6 = [{"key": k, "role": f"역할 {k}", "origin": "counter" if k == "counter-f" else "primary"}
           for k in ("mech-a", "sim-b", "elec-c", "mat-d", "rel-e", "counter-f")]


def _s(prefix: str, n: int) -> str:
    base = prefix + " 힌지 브래킷 두께 0.8→0.6 mm 변경으로 낙하 시 굽힘 응력이 항복 근처까지 오르고 계면 박리 가능성이 커진다."
    return (base * (n // len(base) + 1))[:n]


def _seat(reads_each: int = 180) -> dict:
    """tier B 좌석 한 명의 세 라운드 답 — 브리프 근거 11항목을 하나씩 해석한 크기(스키마 hwax-deliberate R1·R2·R3)."""
    return {"lens": _s("관점 —", 120), "reads": [_s(f"[e:{i + 1}|E{i}]", reads_each) for i in range(11)],
            "recommendation": "권장표지 " + _s("권장 —", 300), "concerns": ["우려표지 " + _s(f"우려 {i} —", 150) for i in range(3)],
            "rebut": [{"target": "sim-b", "quote": _s("인용 —", 120), "counter": _s("반박 —", 200), "basis": "[e:4] 낙하 시험"}] * 2,
            "deepen": _s("심화 —", 350), "final_position": _s("최종 —", 300), "non_negotiable": _s("양보 불가 —", 200),
            "vote": _s("표결 —", 200)}


def _decision(n: int) -> str:
    return "## 리스크 심사 보고서\n" + "판" * (n - 30) + "\n〔결정문 끝〕"


def _body(n: int) -> str:
    """자식 심의는 결정문 끝 표식(〔결정문 끝〕)을 떼고 뒤에 '쉬운 설명' 을 붙여 돌려준다 — 그 앞 본문."""
    return _decision(n).replace("\n〔결정문 끝〕", "")


def _panel(seat: dict, decision_len: int = 2_000, seats=None, rounds: int = 3) -> dict:
    brief = _brief([{"key": "E0", "source": "scope", "result": "스코프"}], seats=seats or _SEATS6, rounds=rounds)
    return _run(_RISK, {"targetKey": "T1", "briefToken": "tok", "tier": "B"}, brief=brief, seat=seat,
                decision=_decision(decision_len))


def _raw(out: dict, name: str) -> str:
    prompt = next(c for c in out["calls"] if c["label"].startswith("submit:"))["prompt"]
    return next(ln.strip() for ln in prompt.split("\n") if ln.strip().startswith(f"{name} = "))[len(name) + 3:]


def _r1(out: dict) -> list[dict]:
    return [t for t in _submit_arg(out, "turns") if t["round"] == 1]


# ── P-3 — 엔진과 같은 순서, 고정 칸 상한 없음 ────────────────────────────────────────────────
def test_1라운드_발언은_엔진과_같은_순서다():
    """관점 → 권장 → 해석 → 우려(엔진 _say_of full). 종전엔 해석을 권장 앞에 끼웠다."""
    seat = _seat()
    out = _panel(seat, seats=_SEATS6[:2], rounds=2)
    say = _r1(out)[0]["say"]
    at = [say.index(x) for x in (seat["lens"], "권장표지", seat["reads"][0], seat["reads"][-1], "우려표지")]
    assert at == sorted(at), f"순서가 엔진과 다르다 — {at}"


def test_해석이_길어도_예산_안이면_발언을_통째로_낸다():
    """**P-3 의 이유다** — 해석 11항목(약 2,000자)이 붙은 1라운드 발언이 2,000자에서 꼬리가 잘려 권장과 우려가 원장에서 사라졌다.
    앱은 원문을 남기고 발췌를 스스로 만든다 — 예산 안이면 손대지 않는다."""
    seat = _seat()
    out = _panel(seat, seats=_SEATS6[:2], rounds=2)
    for t in _r1(out):
        assert "권장표지" in t["say"] and t["say"].count("우려표지") == 3, t["say"][-80:]
        assert all(r in t["say"] for r in seat["reads"]) and "…[" not in t["say"]
        assert len(t["say"]) > 2_000, "이 시험의 발언은 종전 칸(2,000자)보다 길어야 한다"
    assert out["result"]["submitted"][0]["flags"]["sayCut"] == 0
    assert all(x["source"] != "발언 길이 상한 초과" for x in _submit_arg(out, "evidence_omitted"))


# ── X-4 — 결정문은 통째로, 발언은 남는 몫에 ─────────────────────────────────────────────────
def test_결정문이_커서_예산을_넘으면_발언을_줄여_제출한다():
    """**X-4 의 이유다** — 7석×3라운드(tier B 6석 + 지정 반대석) · 결정문 25,000자. M1 전에는 제출됐고 M1 뒤에는 payload_too_large 로
    웹에 안 올라갔다. 결정문은 한 글자도 줄이지 않고, 발언을 줄여 에코 예산 안에 넣는다."""
    out = _panel(_seat(), decision_len=25_000)
    res = out["result"]
    assert res["failed"] == [] and len(res["submitted"]) == 1, res["failed"]
    sent = _submit_arg(out, "decision_text")   # 자식 심의가 결정문 뒤에 '쉬운 설명' 을 붙여 돌려준다 — 그것까지 통째로 낸다
    assert sent.startswith(_body(25_000)) and len(sent) == res["submitted"][0]["decisionChars"], "결정문을 줄였다"
    size = len(_raw(out, "turns")) + len(sent) + len(_raw(out, "evidence_omitted"))
    assert size <= _BUDGET, f"에코 {size:,}자 — 예산 {_BUDGET:,}자를 넘었다"
    flags = res["submitted"][0]["flags"]
    assert flags["sayCut"] > 0 and flags["sayCap"] and flags["sayCap"] >= 300, flags
    note = next(x["text"] for x in _submit_arg(out, "evidence_omitted") if x["source"] == "발언 길이 상한 초과")
    assert f"{flags['sayCap']:,}자" in note and "60,000자" in note and "결정문" in note, note
    assert len(note) <= 200


def test_줄일_때는_해석을_줄이고_권장과_우려를_지킨다():
    out = _panel(_seat(), decision_len=25_000)
    cap = out["result"]["submitted"][0]["flags"]["sayCap"]
    for t in _r1(out):
        assert "권장표지" in t["say"] and t["say"].count("우려표지") == 3, t["say"][-120:]
        assert "…[해석 " in t["say"] and len(t["say"]) <= cap, (len(t["say"]), cap)


def test_결정문만으로_예산을_넘으면_종전대로_제출하지_않고_보존한다():
    out = _panel(_seat(), decision_len=59_000)
    res = out["result"]
    assert res["submitted"] == [] and res["failed"][0]["error"].startswith("payload_too_large"), res["failed"]
    part = res["partials"][0]
    assert part["why"] == "payload_too_large" and part["decision"].startswith(_body(59_000)) and part["rounds"]
    assert any("결정문 59," in ln and "60,000자" in ln and "partials" in ln for ln in out["logs"]), out["logs"]


def test_다_들어가면_상한을_쓰지_않는다():
    out = _panel(_seat(), decision_len=2_000)
    flags = out["result"]["submitted"][0]["flags"]
    assert flags["sayCut"] == 0 and flags["sayCap"] is None
    assert len(json.loads(_raw(out, "turns"))) == 21, "7석×3라운드"
