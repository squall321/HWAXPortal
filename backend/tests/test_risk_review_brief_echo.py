# Claude 로 돌리는 리스크 심사가 브리프를 LLM 의 옮겨 적기로 받을 때 — 못 받음·바뀜·파일로 저장됨을 틀린 진단 없이 가르는지
"""hwax-risk-review.js 는 risk_get_brief 의 응답을 에이전트의 구조화 출력으로 '원문 그대로' 다시 받는다(에코). 이 길에는 크기 가드도
대조 장치도 없었다(검토 P-1·GA-1).

  - 에이전트가 아무것도 돌려주지 않으면(출력 상한·API 오류 — agent() 는 null) panels=[] 로 떨어져 '편성된 패널이 없다 — 앱에서 먼저
    패널을 편성해야 한다'(no_planned_panel)는 틀린 진단으로 멈췄다. 앱에는 패널이 있다.
  - 근거 result 는 [c:12자리 hex]·부품 이름 같은 고엔트로피 글이다. 옮겨 적다 줄이거나 바꿔도 잡을 장치가 없어, 좌석은 동결 브리프와
    다른 글을 보고 인용 대조가 말없이 어긋난다(등급은 소급하지 않아 그 패널에 영구히 남는다).
  - Claude Code 는 MCP 결과가 MAX_MCP_OUTPUT_TOKENS(기본 25,000토큰)를 넘으면 본문 대신 'Error: result (N characters) exceeds maximum
    allowed tokens. Output has been saved to <경로>' 를 준다. 프롬프트는 '호출이 실패하면 brief_unavailable, 재시도 금지' 뿐이라 그
    문구를 실패로 읽을 수 있었다. Read 도구는 2,000자 넘는 줄을 잘라 보여 주므로 파일을 Read 로만 읽으면 긴 근거가 앞부분만 옮겨진다.

스크립트를 스텁 런타임에서 실제로 돌린다(test_infra_pipeline_notices 의 구동기 — 브리프 스텁은 스키마가 선언하지 않은 필드를 버린다).
"""
from tests.test_infra_pipeline_notices import _RISK, _brief, _run

_DECISION = "## 리스크 심사 보고서\n판정.\n〔결정문 끝〕"


def _risk(brief) -> dict:
    return _run(_RISK, {"targetKey": "T1", "briefToken": "tok", "tier": "B"}, brief=brief, decision=_DECISION)


def _seated(out: dict) -> list[str]:
    return [c["label"] for c in out["calls"] if c["label"].startswith("r1:")]


def _submits(out: dict) -> list[str]:
    return [c["label"] for c in out["calls"] if c["label"].startswith("submit:")]


# ── 못 받음 — 에이전트가 null 을 돌려주면 ────────────────────────────────────────────────────
def test_브리프_에이전트가_아무것도_돌려주지_않으면_패널이_없다고_하지_않는다():
    """**P-1 의 오진** — null 은 '앱에 패널이 없다' 가 아니다. 옮겨 적기가 실패했다는 사실과 손잡이를 말한다."""
    out = _risk(None)
    res = out["result"]
    assert res["error"] == "brief_echo_failed", res
    assert res["submitted"] == [] and _seated(out) == []
    assert not any("편성된 패널이 없다" in ln for ln in out["logs"]), out["logs"]
    assert any("옮겨 적" in ln and "다시" in ln for ln in out["logs"]), out["logs"]


def test_패널이_정말_없으면_종전대로_no_planned_panel():
    out = _risk({"panels": []})
    assert out["result"]["error"] == "no_planned_panel"
    assert any("편성된 패널이 없다" in ln for ln in out["logs"])


# ── 바뀜 — 앱이 알린 원문 길이와 견준다 ──────────────────────────────────────────────────────
def test_옮겨_적은_근거의_길이가_앱이_알린_길이와_다르면_심의를_돌리지_않는다():
    """앱이 항목마다 원문 길이(result_chars)를 실으면 옮겨 적은 result 와 견준다. 줄여 옮긴 근거로 좌석을 앉히지 않는다 —
    그러면 원장은 좌석이 받지 않은 동결 브리프를 '받았다' 고 기록한다."""
    ev = [{"key": "E0", "source": "scope", "result": "스코프", "result_chars": 3},
          {"key": "E2", "source": "변경 목록", "result": "가" * 2_000, "result_chars": 15_120}]
    out = _risk(_brief(ev))
    res = out["result"]
    assert res["error"] == "brief_echo_mismatch", res
    assert res["echoMismatch"] == [{"panel_id": "P1", "key": "E2", "want": 15_120, "got": 2_000}]
    assert _seated(out) == [] and _submits(out) == [], "바뀐 근거로 좌석을 앉혔다"
    line = next(ln for ln in out["logs"] if "E2" in ln)
    assert "15,120" in line and "2,000" in line


def test_길이가_맞으면_그대로_돈다():
    ev = [{"key": "E0", "source": "scope", "result": "스코프", "result_chars": 3},
          {"key": "E2", "source": "변경 목록", "result": "가" * 2_000, "result_chars": 2_000}]
    out = _risk(_brief(ev))
    assert out["result"].get("error") is None and len(out["result"]["submitted"]) == 1
    assert _seated(out), "좌석이 앉지 않았다"


def test_길이는_파이썬_len_과_같은_코드포인트로_센다():
    """앱은 파이썬 len(코드포인트)으로 센다. JS 의 .length 는 UTF-16 단위라 BMP 밖 글자(이모지 등)에서 두 배가 된다 — 그대로 견주면
    멀쩡한 브리프를 '바뀌었다' 로 멈춘다."""
    ev = [{"key": "E0", "source": "scope", "result": "모드 😀" * 5, "result_chars": len("모드 😀" * 5)}]
    out = _risk(_brief(ev))
    assert out["result"].get("error") is None, out["result"]


def test_앞뒤_공백만_빠진_것은_바뀐_것이_아니다():
    """앱은 앞뒤 공백을 뗀 길이를 싣는다(len(result.strip())). 옮겨 적으며 끝 줄바꿈이 빠지는 것까지 막으면 헛멈춤이다."""
    ev = [{"key": "E0", "source": "scope", "result": "  스코프\n", "result_chars": 3}]
    assert _risk(_brief(ev))["result"].get("error") is None


def test_앱이_길이를_싣지_않으면_대조하지_못했다고_남긴다():
    """옛 앱(result_chars 없음)은 막지 않는다 — 대신 대조하지 못했다는 사실을 남긴다(대조한 척하지 않는다)."""
    out = _risk(_brief([{"key": "E0", "source": "scope", "result": "스코프"}]))
    assert out["result"].get("error") is None and len(out["result"]["submitted"]) == 1
    assert any("result_chars" in ln and "대조하지 못했다" in ln for ln in out["logs"]), out["logs"]


# ── 파일로 저장됨 — Claude Code 의 MCP 결과 상한 ────────────────────────────────────────────
def _brief_prompt(out: dict) -> str:
    return next(c["prompt"] for c in out["calls"] if c["label"] == "brief")


def test_결과가_파일로_저장되면_실패가_아니라_파일을_읽으라고_시킨다():
    prompt = _brief_prompt(_risk({"panels": []}))
    assert "exceeds maximum allowed tokens" in prompt and "saved to" in prompt, "하네스의 파일 저장 안내를 짚지 않는다"
    assert "실패가 아니다" in prompt
    assert "2,000자" in prompt and "jq" in prompt, "Read 의 줄 절단을 피해 긴 필드를 끝까지 읽으라는 말이 없다"
    assert 'error="brief_too_large"' in prompt


def test_앱이_알린_원문_길이를_세지_말고_옮기라고_시킨다():
    prompt = _brief_prompt(_risk({"panels": []}))
    assert "result_chars" in prompt and "세지 마라" in prompt


def test_파일을_끝까지_못_읽었으면_손잡이를_말하고_멈춘다():
    out = _risk({"error": "brief_too_large", "panels": []})
    assert out["result"]["error"] == "brief_too_large" and _seated(out) == []
    assert any("MAX_MCP_OUTPUT_TOKENS" in ln for ln in out["logs"]), out["logs"]


# ── 앱·게이트웨이가 거절하면 — 오류 코드와 까닭·고칠 곳을 그대로 사람에게 ─────────────────────────────────
_WHY = ("이 호출의 단언(admin@example.com)은 게이트웨이가 위임 헤더(X-Hwax-Delegate-Email) 없이 받아 온 것이다 — 쓰기 도구는 게이트웨이 "
        "위임으로 확인된 신원으로만 쓴다(그 계정으로 대신 쓰지 않는다).")
_FIX = ("운영자가 게이트웨이를 사람별 위임에 X-Hwax-Delegate-Email 을 싣는 판으로 올리고, 이 앱의 per_user_sso 가 설정됐는지 본다. "
        "그 전에는 웹 리스크 앱(/risk/)에서 같은 일을 한다.")


def test_위임이_없어_앱이_거절하면_코드와_까닭과_고칠_곳을_그대로_보인다():
    """리스크 앱(m1)은 결과를 낼 수 없는 신원(게이트웨이 위임 없음)에게 risk_get_brief 단계에서 {error:'delegation_required', message,
    detail:{fix}} 를 돌려준다(HWAXRisk RV-1). 종전 스키마에는 message·fix 칸이 없어 구조화 출력이 버렸고, 사람은 '브리프 중단 —
    delegation_required' 만 보고 어디를 고칠지 몰랐다(RR2-PF-1)."""
    out = _risk({"error": "delegation_required", "message": _WHY, "fix": _FIX, "panels": []})
    res = out["result"]
    assert res["error"] == "delegation_required" and _seated(out) == [] and _submits(out) == []
    assert res["message"] == _WHY and res["fix"] == _FIX, res
    said = "\n".join(out["logs"])
    assert "delegation_required" in said and _WHY in said and _FIX in said, out["logs"]


def test_앱이_고칠_곳을_주지_않아도_위임_거절은_어디를_볼지_말한다():
    out = _risk({"error": "delegation_required", "panels": []})
    line = next(ln for ln in out["logs"] if "위임" in ln)
    assert "게이트웨이" in line and "웹 리스크 앱" in line, out["logs"]


def test_호출이_실패해도_그_오류_문구를_버리지_않는다():
    """게이트웨이가 접힌 위임을 거부하면(HWAXMcpGateway RR2-GW-1) 도구 호출 자체가 실패해 brief_unavailable 로 닫힌다 — 그 오류 문구가
    유일한 단서인데 종전엔 칸이 없어 버려졌다."""
    msg = "heax-hwax_risk: a@example.com 자격증명으로 호출하지 못했습니다 (RuntimeError('SSO 단언이 호출자가 아닌 다른 계정으로 발급됐다'))"
    out = _risk({"error": "brief_unavailable", "message": msg, "panels": []})
    assert out["result"]["error"] == "brief_unavailable" and out["result"]["message"] == msg
    assert any(msg in ln for ln in out["logs"]), out["logs"]


def test_오류_문구와_고칠_곳을_줄이지_말고_옮기라고_시킨다():
    prompt = _brief_prompt(_risk({"panels": []}))
    assert "detail.fix" in prompt and "message" in prompt
    tail = prompt[prompt.index('error="brief_unavailable"'):]
    assert "message" in tail, "호출 실패 문구를 옮기라는 말이 없다"
