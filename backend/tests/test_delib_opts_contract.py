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
