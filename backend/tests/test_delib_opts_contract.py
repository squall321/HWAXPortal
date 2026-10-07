# 프론트가 보내는 심의 손잡이 키가 전부 백엔드 모델에 선언돼 있는지 — 안 그러면 조용히 사라진다
"""⚠ 이 리포의 반복 사고를 기계가 잡게 하는 테스트다.

포털은 `body.delib_opts.model_dump(exclude_none=True)` 로만 중계한다. 그래서 `DelibOpts`
모델에 **선언 안 된 키는 에러 없이 사라지고**, 심의는 정상 동작한 것처럼 끝난다.
실제로 이 함정에 chair_template·free_tools 가 빠졌다가 고쳐졌고, 그 주석 바로 옆에서
non_negotiables·stop_after_round·rounds_so_far·append_to_report_id 네 개가 또 새고 있었다
(2026-09-11 조사). 사람이 두 파일을 번갈아 보는 것으로는 네 번 놓쳤다.

프론트에서 키를 뽑는 방식은 정규식이라 취약하다 — 그래서 **아무것도 못 뽑으면 실패**시킨다.
리팩터링으로 추출이 깨지면 테스트가 조용히 통과하는 것이 최악이다.
"""
import re
from pathlib import Path

import pytest

from app.agent.routes import DelibOpts

_FRONT = Path(__file__).resolve().parents[2] / "frontend" / "src" / "state"


def _wire_keys() -> set[str]:
    """delibOptsToWire() 가 실어 보내는 키 — 패널 토글 경로."""
    src = (_FRONT / "chatStore.ts").read_text(encoding="utf-8")
    body = src[src.index("export function delibOptsToWire") :]
    body = body[: body.index("\n}")]
    keys = set(re.findall(r"\bw\.([a-z_]+)\s*=", body))          # w.rounds = ...
    keys |= set(re.findall(r"\bw\[k\]", body)) and set()          # 루프는 아래에서
    for arr in re.findall(r"for \(const k of \[([^\]]+)\]", body):
        keys |= set(re.findall(r"'([a-z_]+)'", arr))
    return keys


def _extra_keys() -> set[str]:
    """ChatContext 가 extraDelibOpts 로 직접 싣는 키 — 이어하기·핸드오프 경로.

    이쪽은 delibOptsToWire 를 **우회**하므로(sendMessage 가 병합만 한다) 백엔드 모델만
    통과하면 된다. 그래서 더 쉽게 새고, 실제로 non_negotiables 가 그렇게 샜다.
    """
    src = (_FRONT / "ChatContext.tsx").read_text(encoding="utf-8")
    keys = _send_keys(src)
    # extra.xxx = ... (startHandoff 가 조립하는 dict)
    keys |= set(re.findall(r"\bextra\.([a-z_]+)\s*=", src))
    # ⚠ /심의 페이지도 sendMessage 두 번째 인자로 직접 싣는다(선정 패널 → personas·tools·evidence…).
    #   종전엔 ChatContext 만 봐서 여기로 들어가는 새 키는 검사 밖이었다.
    keys |= _send_keys((_FRONT.parent / "pages" / "DeliberatePage.tsx").read_text(encoding="utf-8"))
    return keys


def _send_keys(src: str) -> set[str]:
    """sendMessage(text, { ... }) 객체 리터럴의 키 — 들여쓰기에 기대지 않는다."""
    keys: set[str] = set()
    for block in re.findall(r"sendMessage\([^,]+,\s*\{(.*?)\n\s*\}\)", src, re.S):
        keys |= set(re.findall(r"^\s*(?:\.\.\.\([^)]*\?\s*\{\s*)?([a-z_]+):", block, re.M))
        keys |= set(re.findall(r"\?\s*\{\s*([a-z_]+)\s*\}", block))   # 단축 속성 ...(c ? { tools } : {})
    return keys


def test_extraction_actually_found_something():
    """추출이 깨지면 테스트가 조용히 통과한다 — 그것부터 막는다."""
    assert len(_wire_keys()) >= 6, f"delibOptsToWire 키 추출 실패: {_wire_keys()}"
    assert len(_extra_keys()) >= 4, f"extraDelibOpts 키 추출 실패: {_extra_keys()}"


def test_every_panel_toggle_is_declared_in_the_model():
    """패널 토글은 delibOptsToWire + DelibOpts **두 겹**을 다 통과해야 한다."""
    declared = set(DelibOpts.model_fields)
    missing = _wire_keys() - declared
    assert not missing, (
        f"프론트가 보내는데 백엔드 DelibOpts 에 없다 — 조용히 사라진다: {sorted(missing)}"
    )


def test_every_continuation_key_is_declared_in_the_model():
    """이어하기·핸드오프가 싣는 키도 모델에 있어야 한다(이쪽은 관문이 백엔드 하나뿐이다)."""
    declared = set(DelibOpts.model_fields)
    # 심의 손잡이가 아닌 것은 제외 — search_sources 는 top-level 로도 가고, 나머지는
    # sendMessage 의 다른 인자다.
    ignore = {"human_note"} & set()      # 현재 제외 대상 없음(전부 손잡이다)
    missing = (_extra_keys() - declared) - ignore
    assert not missing, (
        f"이어하기/핸드오프가 보내는데 백엔드 DelibOpts 에 없다: {sorted(missing)}"
    )


def test_the_four_that_were_silently_dropped_are_now_declared():
    """2026-09-11 에 발견된 네 개 — 회귀하면 여기서 잡는다."""
    for k in ("non_negotiables", "stop_after_round", "rounds_so_far", "append_to_report_id"):
        assert k in DelibOpts.model_fields, f"{k} 가 다시 빠졌다 — 웹 이어하기가 조용히 깨진다"


# ── 엔진이 요청으로 받는 키를 포털이 중계하는가 ─────────────────────────────────────
# 위 시험들은 '프론트가 보내는 키' 에서 출발한다. 반대쪽 — **엔진에 새 요청 키가 생겼는데 포털에 선언이 없는**
# 경우는 보지 못했다. 그 키는 MCP 로는 되는데 포털을 거치는 길(웹 · 리스크 앱 러너)에서는 말없이 사라진다.
# 실제로 그랬다: 엔진이 persona_knowledge(지식카드를 이 요청만 끈다)와 sealed(봉인 실행)를 요청 키로 받게 된 날
# (2026-10-07, docs/delib-engine-feedback 1-5·1-6) 포털에는 둘 다 없었다. sealed 가 여기서 떨어지면 봉인을 청한
# 심의가 **열린 채** 돌고, 청한 쪽은 봉인된 줄 안다 — 이 묶음에서 가장 나쁜 조용한 실패다.
_ENGINE = Path(__file__).resolve().parents[2].parent / "HWAXAgentServer" / "deliberation.py"

# 엔진은 받는데 포털이 중계하지 않는 키 — **알고 남겨 둔 것만** 적는다. 2026-10-07 기준으로 웹·리스크 앱 러너
# 어느 쪽도 보내지 않는 키들이다. 누가 보내기 시작하면 포털이 말없이 버리므로, 그때는 여기서 빼고 선언한다.
_NOT_RELAYED = {
    "continue_non_negotiables",   # non_negotiables 의 옛 이름 — 엔진이 둘 다 읽고 포털은 새 이름만 싣는다
    "options",                    # 후보안 목록 — MCP deliberate_start 의 인자다. 웹·러너는 보내지 않는다
    "parse_retries",              # JSON 재시도 횟수 — 운영 손잡이(DELIB_PARSE_RETRIES)다. 요청으로 보내는 곳이 없다
    "save_report",                # 보고서 저장 끄기 — MCP deliberate_start 의 인자다. 웹·러너는 보내지 않는다
}


def _engine_request_keys() -> set[str]:
    """엔진 _resolve_opts 가 요청(req_opts)에서 읽는 키 — 낱개 get("…") 과 정수 손잡이 루프의 튜플."""
    src = _ENGINE.read_text(encoding="utf-8")
    body = src[src.index("def _resolve_opts("):]
    body = body[: body.index("\n    return o\n")]
    keys = set(re.findall(r'req_opts\.get\("([a-z_]+)"\)', body))
    loop = re.search(r"for k in \(([^)]*)\):\s*\n\s*v = req_opts\.get\(k\)", body)
    assert loop, "엔진의 정수 손잡이 루프를 못 찾았다 — 모양이 바뀌었으면 이 추출도 고쳐라"
    return keys | set(re.findall(r'"([a-z_]+)"', loop.group(1)))


def test_엔진이_요청으로_받는_키는_포털이_중계하거나_알고_남겨_둔_것이다():
    if not _ENGINE.exists():
        pytest.skip(f"형제 리포 없음: {_ENGINE}")
    keys = _engine_request_keys()
    assert len(keys) >= 25, f"엔진 요청 키 추출 실패: {sorted(keys)}"   # 못 뽑으면 조용히 통과한다
    missing = keys - set(DelibOpts.model_fields) - _NOT_RELAYED
    assert not missing, (
        f"엔진은 요청 키로 받는데 포털 DelibOpts 에 없다 — 포털을 거치는 길에서 말없이 사라진다: {sorted(missing)}. "
        "DelibOpts 에 선언하거나, 중계하지 않기로 했으면 _NOT_RELAYED 에 이유와 함께 적는다."
    )
    stale = {k for k in _NOT_RELAYED if k in DelibOpts.model_fields or k not in keys}
    assert not stale, f"_NOT_RELAYED 가 낡았다(이미 선언했거나 엔진이 더는 안 읽는다): {sorted(stale)}"


def test_지식카드_끄기와_봉인이_포털을_지나_살아_나온다():
    """모델 선언만 보지 말고 값이 실제로 중계되는지 본다 — 포털은 model_dump(exclude_none=True) 로만 넘긴다."""
    from app.agent.routes import ChatRequest

    req = ChatRequest(message="/심의 화두", delib_opts={"persona_knowledge": 0, "sealed": 1})
    wire = req.delib_opts.model_dump(exclude_none=True)
    assert wire.get("persona_knowledge") == 0, "지식카드를 끄라는 요청이 포털에서 사라졌다 — 엔진 기본(켬)으로 돈다"
    assert wire.get("sealed") == 1, "봉인 요청이 포털에서 사라졌다 — 열린 채 돈다"
    # 안 보내면 안 나간다 — None 을 0 으로 바꿔 보내면 엔진 기본값을 덮는다.
    assert "sealed" not in ChatRequest(message="/심의 화두", delib_opts={}).delib_opts.model_dump(exclude_none=True)
