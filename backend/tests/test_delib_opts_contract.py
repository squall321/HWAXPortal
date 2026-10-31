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
import shutil
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
}


def _engine_request_keys() -> set[str]:
    """엔진이 요청(req_opts)에서 읽는 키 — _resolve_opts 의 낱개 get("…") 과 정수 손잡이 루프의 튜플, 그리고 파일 어디서든 이름 붙인
    상수로 읽는 키(get(external_llm.CONSENT_FIELD) 같은)."""
    src = _ENGINE.read_text(encoding="utf-8")
    body = src[src.index("def _resolve_opts("):]
    body = body[: body.index("\n    return o\n")]
    keys = set(re.findall(r'req_opts\.get\("([a-z_]+)"\)', body))
    # 루프가 도는 목록은 그 자리의 튜플이거나 모듈 최상위의 이름 붙인 튜플이다(엔진 386740a 가 `_INT_KEYS` 로 올렸다 — 켜고 끄는
    # 손잡이 표와 나란히 두려고). 옮겨 간 뒤 이 추출이 그 자리의 튜플만 찾아, 계약 시험이 '루프를 못 찾았다' 로 죽어 있었다.
    loop = re.search(r"for k in (\([^)]*\)|[A-Za-z_][A-Za-z0-9_]*):\s*\n\s*v = req_opts\.get\(k\)", body)
    assert loop, "엔진의 정수 손잡이 루프를 못 찾았다 — 모양이 바뀌었으면 이 추출도 고쳐라"
    listed = loop.group(1)
    if not listed.startswith("("):
        named = re.search(rf"^{listed} = \(([^)]*)\)", src, re.M)
        assert named, f"엔진의 정수 손잡이 목록 {listed} 을 모듈 최상위에서 못 찾았다 — 모양이 바뀌었으면 이 추출도 고쳐라"
        listed = named.group(1)
    keys |= set(re.findall(r'"([a-z_]+)"', listed))
    # 이름 붙인 상수로 읽는 키 — 반출 동의(consent_external)는 _resolve_opts 밖(_external_refusal)에서 get(external_llm.CONSENT_FIELD)
    # 로 읽는다. 글자 그대로의 get("…") 만 찾던 추출은 이 키를 못 봐서, 포털이 동의를 버려도 아래 시험이 지나갔다. 상수 값은 그 모듈
    # (없으면 deliberation.py)의 `이름 = "값"` 줄에서 읽는다 — 못 찾으면 실패한다.
    for mod, name in re.findall(r"req_opts\.get\((?:([a-z_]+)\.)?([A-Z][A-Z0-9_]*)\)", src):
        where = _ENGINE.with_name(f"{mod}.py") if mod else _ENGINE
        const = re.search(rf'^{name}\s*=\s*"([a-z_]+)"', where.read_text(encoding="utf-8"), re.M)
        assert const, f"엔진이 요청 키로 읽는 상수 {name} 의 값을 {where.name} 에서 못 찾았다 — 모양이 바뀌었으면 이 추출도 고쳐라"
        keys.add(const.group(1))
    return keys


def test_엔진이_요청으로_받는_키는_포털이_중계하거나_알고_남겨_둔_것이다():
    if not _ENGINE.exists():
        pytest.skip(f"형제 리포 없음: {_ENGINE}")
    keys = _engine_request_keys()
    assert len(keys) >= 25, f"엔진 요청 키 추출 실패: {sorted(keys)}"   # 못 뽑으면 조용히 통과한다
    ext_src = _ENGINE.with_name("external_llm.py").read_text(encoding="utf-8")
    consent = re.search(r'^CONSENT_FIELD\s*=\s*"([a-z_]+)"', ext_src, re.M)
    assert consent and consent.group(1) in keys, (
        "엔진의 반출 동의 칸(external_llm.CONSENT_FIELD)이 추출에 안 잡혔다 — 엔진이 읽는 모양이 바뀌었으면 추출을 고쳐라"
        "(못 보면 포털이 동의를 버려도 이 시험이 지나간다)")
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


def test_지식카드_검색어와_보고서_저장_끄기가_포털을_지나_살아_나온다():
    """리스크 앱 러너가 실어 보낼 좌석 검색어(문자열 또는 좌석별 사전)와 '저장 끄기' 가 엔진에 닿는가.

    선언이 없으면 model_dump(exclude_none=True) 에서 오류 없이 사라진다 — 검색어를 준 패널이 화두로 찾고,
    저장을 끈 줄 아는 심의가 보고서를 만든다."""
    from app.agent.routes import ChatRequest

    one = "C-12 리브 두께 0.8→0.6 mm · 커넥터 간극 축소"
    wire = ChatRequest(message="/심의 화두", delib_opts={"knowledge_query": one, "save_report": 0}) \
        .delib_opts.model_dump(exclude_none=True)
    assert wire.get("knowledge_query") == one, "좌석 검색어(문자열)가 포털에서 사라졌다 — 엔진이 화두로 찾는다"
    assert wire.get("save_report") == 0, "보고서 저장 끄기가 포털에서 사라졌다 — 엔진 기본(저장)으로 돈다"

    by_seat = {"mech-a": "리브 두께 감소 강성", "*": "커넥터 간극 축소"}
    wire = ChatRequest(message="/심의 화두", delib_opts={"knowledge_query": by_seat}) \
        .delib_opts.model_dump(exclude_none=True)
    assert wire.get("knowledge_query") == by_seat, "좌석별 검색어 사전이 포털에서 사라졌거나 모양이 바뀌었다"

    # 경계값은 지나간다 — 600자 하나, 64항목 사전, 빈 사전.
    edge = "가" * 600
    assert ChatRequest(message="/심의 화두", delib_opts={"knowledge_query": edge}) \
        .delib_opts.model_dump(exclude_none=True)["knowledge_query"] == edge
    full = {f"seat-{i}": "q" for i in range(64)}
    assert ChatRequest(message="/심의 화두", delib_opts={"knowledge_query": full}) \
        .delib_opts.model_dump(exclude_none=True)["knowledge_query"] == full
    assert ChatRequest(message="/심의 화두", delib_opts={"knowledge_query": {}}) \
        .delib_opts.model_dump(exclude_none=True)["knowledge_query"] == {}

    # 안 보내면 안 나간다 — None 을 0 이나 빈 값으로 바꿔 보내면 엔진 기본값을 덮는다.
    silent = ChatRequest(message="/심의 화두", delib_opts={}).delib_opts.model_dump(exclude_none=True)
    assert "knowledge_query" not in silent and "save_report" not in silent


@pytest.mark.parametrize("bad", [
    {"knowledge_query": "가" * 601},                              # 값 하나가 엔진 상한을 넘는다
    {"knowledge_query": {"mech-a": "가" * 601}},                  # 사전의 값이 넘는다
    {"knowledge_query": {"": "q"}},                               # 좌석 키가 비었다
    {"knowledge_query": ["리브", "간극"]},                         # 목록
    {"knowledge_query": 3},                                       # 수
    {"knowledge_query": {"mech-a": 3}},                           # 값이 수인 사전
    {"knowledge_query": {f"seat-{i}": "q" for i in range(65)}},   # 사전 항목이 엔진 상한을 넘는다
    {"save_report": 2},
    {"save_report": "off"},
], ids=["str601", "dict-val601", "empty-key", "list", "int", "dict-int", "dict65", "save2", "save-off"])
def test_검색어_모양이_틀리면_소리_내_막는다(bad):
    """넘거나 틀린 값은 422(ValidationError)로 막는다 — 말없이 잘라 보내면 보낸 쪽은 다 실린 줄 안다."""
    from pydantic import ValidationError

    from app.agent.routes import ChatRequest

    with pytest.raises(ValidationError):
        ChatRequest(message="/심의 화두", delib_opts=bad)


# ── 좌석 검색어 · 보고서 저장 — 포털이 낸 값을 엔진이 실제로 읽는가(형제 리포의 실제 _resolve_opts) ─────────────
# 위 시험들은 포털 모델만 본다. 검색어의 두 상한(값 하나 600자 · 좌석별 사전 64항목)은 포털 routes.py 와 엔진
# deliberation.py 에 따로 적혀 있어, 한쪽만 고치면 포털이 엔진이 받는 값을 422 로 막거나(포털이 작을 때) 엔진이
# 포털을 지난 값을 말없이 줄인다(엔진이 작을 때). 그래서 엔진 소스의 상수 줄을 읽어 포털 모델을 **동작으로** 견주고,
# 포털 모델이 낸 출력을 JSON 으로 엔진의 실제 _resolve_opts 에 넣어 읽은 값을 돌려받는다(소비자의 입력을 생산자의
# 실제 출력으로 만든다 — docs/risk-review-redesign PLAN 9절).
def _engine_const(name: str) -> int:
    """엔진 소스의 `이름 = 수` 한 줄(주석 없이) — 못 찾으면 실패한다. 추출이 깨졌는데 조용히 통과하는 것이 최악이다."""
    m = re.search(rf"^{name}\s*=\s*(\d+)\s*$", _ENGINE.read_text(encoding="utf-8"), re.M)
    assert m, (f"deliberation.py 에서 `{name} = 수` 줄을 못 찾았다 — 이름을 바꿨거나 같은 줄에 주석·식을 붙였으면 "
               "엔진을 그 꼴로 되돌리거나 이 추출을 고쳐라")
    return int(m.group(1))


def test_검색어_상한은_엔진과_같은_수다():
    if not _ENGINE.exists():
        pytest.skip(f"형제 리포 없음: {_ENGINE}")
    from pydantic import ValidationError

    n, k = _engine_const("_KNOWLEDGE_Q_MAX"), _engine_const("_KNOWLEDGE_Q_KEYS_MAX")
    assert DelibOpts(knowledge_query="가" * n).knowledge_query == "가" * n, (
        f"포털이 엔진 상한({n}자)까지의 검색어를 그대로 못 넘긴다")
    with pytest.raises(ValidationError):    # 포털이 더 크면 엔진이 포털을 지난 값을 말없이 줄인다
        DelibOpts(knowledge_query="가" * (n + 1))
    assert DelibOpts(knowledge_query={"seat": "가" * n}).knowledge_query == {"seat": "가" * n}
    with pytest.raises(ValidationError):
        DelibOpts(knowledge_query={"seat": "가" * (n + 1)})
    full = {f"seat-{i}": "q" for i in range(k)}
    assert DelibOpts(knowledge_query=full).knowledge_query == full, f"포털이 엔진 상한({k}항목)의 사전을 못 넘긴다"
    with pytest.raises(ValidationError):
        DelibOpts(knowledge_query={f"seat-{i}": "q" for i in range(k + 1)})


# 엔진이 읽은 값만 찍는다 — 경우마다 (검색어, 보고서 저장, 읽지 못한 값, 줄인 값).
_ENGINE_READ = (
    "import json, sys, deliberation as d\n"
    "out = []\n"
    "for req in json.load(sys.stdin):\n"
    "    o = d._resolve_opts(req)\n"
    "    out.append({'kq': o.knowledge_query, 'save': o.save_report, 'unread': o.req_unread, 'cut': o.req_cut})\n"
    "print(json.dumps(out, ensure_ascii=False))\n"
)


def test_포털이_낸_값을_엔진이_실제로_읽는다():
    if not _ENGINE.exists():
        pytest.skip(f"형제 리포 없음: {_ENGINE}")
    import json
    import os
    import subprocess
    import sys

    from app.agent.routes import ChatRequest

    n = _engine_const("_KNOWLEDGE_Q_MAX")
    one = "C-12 리브 두께 0.8→0.6 mm · 커넥터 간극 축소"
    # 좌석 키는 포털 상한(120자) 끝까지 — 엔진이 그보다 짧게 끊으면 이 좌석의 검색어가 엔진에서 다른 키로 읽힌다.
    by_seat = {"mech-a": "리브 두께 감소 강성", "*": "커넥터 간극 축소", "k" * 120: "가" * n}
    cases = [{"knowledge_query": one}, {"knowledge_query": "가" * n}, {"knowledge_query": by_seat},
             {"knowledge_query": {f"seat-{i}": f"검색어 {i}" for i in range(_engine_const("_KNOWLEDGE_Q_KEYS_MAX"))}},
             {"save_report": 0}]
    wire = [ChatRequest(message="/심의 화두", delib_opts=c).delib_opts.model_dump(exclude_none=True) for c in cases]
    assert wire == cases, "포털 모델이 값을 바꾸거나 버렸다 — 엔진에 닿기 전에 갈라졌다"
    r = subprocess.run([sys.executable, "-c", _ENGINE_READ], input=json.dumps(wire, ensure_ascii=False),
                       cwd=_ENGINE.parent, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                       capture_output=True, text=True, timeout=120)
    # 형제 리포가 있는데 엔진을 못 부르면 건너뛰지 않는다 — 건너뜀은 통과가 아니다.
    assert r.returncode == 0, f"엔진 _resolve_opts 를 이 venv 로 부르지 못했다 — {r.stderr.strip()[-600:]}"
    got = json.loads(r.stdout)
    for sent, read in zip(wire, got):
        assert read["kq"] == sent.get("knowledge_query", ""), f"엔진이 포털이 낸 검색어를 다르게 읽었다 — {sent}"
        assert read["save"] == sent.get("save_report", 1), f"엔진이 포털이 낸 보고서 저장 값을 다르게 읽었다 — {sent}"
        assert read["unread"] == {} and read["cut"] == {}, (
            f"포털을 지난 값을 엔진이 못 읽거나 줄였다 — 두 리포의 모양·상한이 갈라졌다: {read}")



# ── 기준일(as_of) — docs/request-1027 HA-11 · 사용자 결정 10-31 A-keep ───────────────────────────────────────────────────
# 엔진은 delib_opts.as_of('YYYY-MM-DD')가 오면 그 심의의 좌석 지식카드 검색(agent_search)을 그 날까지의 카드로 거르고 결정문 머리에 찍는다.
# 포털에 선언이 없으면 model_dump(exclude_none=True) 에서 말없이 떨어져, 기준일을 준 소급 검증이 오늘의 카드로 돈다. 꼴은 엔진 _as_of_ok 와
# 같아야 한다 — 포털이 넓으면 포털을 지난 값을 엔진이 시작 전에 거절하고(웹 심의가 오류로 끝난다), 좁으면 엔진이 받는 날을 포털이 422 로 막는다.
_AS_OF_CASES = ["2025-06-01", "2024-02-29", "2025-02-30", "2025-13-01", "2025-6-1", " 2025-06-01", "2025-06-01 ",
                "2025-06-01\n", "2025-06-01T09:00:00", "20250601", "", "２０２５-０６-０１", "٢٠٢٥-٠٦-٠١"]


def _portal_takes_as_of(v) -> bool:
    from pydantic import ValidationError
    try:
        DelibOpts(as_of=v)
    except ValidationError:
        return False
    return True


def test_기준일이_포털을_지나_살아_나온다():
    from app.agent.routes import ChatRequest

    wire = ChatRequest(message="/심의 화두", delib_opts={"as_of": "2025-06-01"}).delib_opts.model_dump(exclude_none=True)
    assert wire == {"as_of": "2025-06-01"}, "기준일이 포털에서 사라졌거나 모양이 바뀌었다 — 엔진이 거르지 않고 돈다"
    # 안 보내면 안 나간다 — 빈 값을 채워 보내지 않는다.
    assert "as_of" not in ChatRequest(message="/심의 화두", delib_opts={}).delib_opts.model_dump(exclude_none=True)


@pytest.mark.parametrize("bad", ["2025-02-30", "2025-13-01", "2025-6-1", " 2025-06-01", "2025-06-01T09:00:00",
                                 "20250601", "", "２０２５-０６-０１", 20250601, ["2025-06-01"]],
                         ids=["no-day", "no-month", "short", "space", "datetime", "compact", "empty", "fullwidth", "int", "list"])
def test_기준일_꼴이_틀리면_422(bad):
    """틀린 날을 말없이 버리면 보낸 쪽은 기준일로 거른 줄 안다 — 소리 내 막는다."""
    assert not _portal_takes_as_of(bad)


_ENGINE_AS_OF = (
    "import json, sys, deliberation as d\n"
    "out = []\n"
    "for v in json.load(sys.stdin):\n"
    "    o = d._resolve_opts({'as_of': v})\n"
    "    out.append({'ok': d._as_of_ok(v), 'read': o.as_of, 'unread': o.req_unread,\n"
    "                'refused': (d._as_of_refusal({'as_of': v}) or {}).get('code')})\n"
    "print(json.dumps(out, ensure_ascii=False))\n"
)


def test_기준일_꼴은_엔진과_같고_포털이_낸_값을_엔진이_그대로_읽는다():
    if not _ENGINE.exists():
        pytest.skip(f"형제 리포 없음: {_ENGINE}")
    import json
    import os
    import subprocess
    import sys

    portal = [_portal_takes_as_of(v) for v in _AS_OF_CASES]
    assert portal[:2] == [True, True] and not any(portal[2:]), f"시험 전제 — 포털이 받는 것: {portal}"
    r = subprocess.run([sys.executable, "-c", _ENGINE_AS_OF], input=json.dumps(_AS_OF_CASES, ensure_ascii=False),
                       cwd=_ENGINE.parent, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                       capture_output=True, text=True, timeout=120)
    # 형제 리포가 있는데 엔진을 못 부르면 건너뛰지 않는다 — 건너뜀은 통과가 아니다.
    assert r.returncode == 0, f"엔진 _resolve_opts · _as_of_ok 를 이 venv 로 부르지 못했다 — {r.stderr.strip()[-600:]}"
    got = json.loads(r.stdout.strip().splitlines()[-1])
    assert [g["ok"] for g in got] == portal, f"기준일 꼴이 포털과 엔진에서 갈라졌다 — {list(zip(_AS_OF_CASES, portal, got))}"
    for v, ok, g in zip(_AS_OF_CASES, portal, got):
        if ok:     # 포털이 낸 값을 엔진이 그대로 읽는다 — 못 읽거나 거절하면 웹 심의가 시작조차 안 된다
            assert g["read"] == v and g["unread"] == {} and g["refused"] is None, (v, g)
        elif v:    # 포털을 거치지 않고 엔진에 닿은 틀린 꼴(MCP)은 엔진이 시작 전에 거절한다. 빈 값은 '안 줬다' 다
            assert g["read"] == "" and g["refused"] == "bad_request", (v, g)


def test_기준일이_심의_중계_길에서_엔진_본문에_그대로_닿는다():
    codes, seen = _relay_chat({"message": "/심의 화두", "delib_opts": {"as_of": "2025-06-01", "rounds": 3}},
                              {"message": "/심의 화두", "delib_opts": {"as_of": "2025-02-30"}},
                              {"message": "/심의 화두", "delib_opts": {"rounds": 3}})
    assert codes == [200, 422, 200]
    assert len(seen) == 2, "422 로 막힌 요청이 엔진으로 나갔다"
    assert seen[0]["delib_opts"] == {"as_of": "2025-06-01", "rounds": 3}
    assert seen[1]["delib_opts"] == {"rounds": 3}, "기준일을 안 준 심의에 기준일 칸이 생겼다"


@pytest.mark.parametrize("health", [{"status": "ok"}, {"status": "ok", "delib_as_of": False}, "down"],
                         ids=["old-engine", "flag-false", "health-down"])
def test_기준일을_받지_않는_엔진이면_포털이_기준일_심의를_넘기지_않는다(health):
    """옛 엔진은 delib_opts.as_of 를 말없이 버린다(_resolve_opts 에 칸이 없다) — 포털을 먼저 올리고 에이전트 서버 재기동이 미뤄진 창(update-all §2
    포털 뒤 §4 가 도는 심의를 기다리다 재기동을 미룬다)에서 웹 '기준일' 심의가 경고 없이 오늘의 카드로 돌았다(반대 검토 10-31). 엔진 /health 의
    delib_as_of 가 참일 때만 넘기고, 아니면(모름 포함) 엔진을 부르지 않고 SSE 오류로 끝낸다. 기준일 없는 심의는 묻지도 않는다."""
    texts, probes = [], []
    codes, seen = _relay_chat({"message": "/심의 화두", "delib_opts": {"as_of": "2025-06-01", "rounds": 3}},
                              {"message": "/심의 화두", "delib_opts": {"rounds": 3}},
                              health=health, texts=texts, probes=probes)
    assert codes == [200, 200]
    assert len(seen) == 1 and seen[0]["delib_opts"] == {"rounds": 3}, f"기준일 심의가 기준일을 모르는 엔진으로 나갔다 — {[x.get('delib_opts') for x in seen]}"
    assert "event: error" in texts[0] and '"code": "as_of_unsupported"' in texts[0] and "event: done" in texts[0], texts[0]
    assert "기준일" in texts[0] and "다시 띄운" in texts[0], texts[0]
    assert len(probes) == 1, f"기준일 없는 심의에도 /health 를 물었다 — {len(probes)}번"


def test_기준일을_받는_엔진이면_한_번_묻고_그대로_넘긴다():
    texts, probes = [], []
    codes, seen = _relay_chat({"message": "/심의 화두", "delib_opts": {"as_of": "2025-06-01"}}, texts=texts, probes=probes)
    assert codes == [200] and len(probes) == 1 and seen[0]["delib_opts"] == {"as_of": "2025-06-01"}
    assert "as_of_unsupported" not in texts[0]


def test_심의_옵션_화면이_기준일을_싣는다():
    """화면 입구 — 심의 옵션의 date 입력칸이 delibOpts.as_of 를 고치고, delibOptsToWire 가 꼴이 맞을 때만 싣는다(포털 422 를 피한다)."""
    panel = (_FRONT.parent / "components" / "chat" / "DelibOptsPanel.tsx").read_text(encoding="utf-8")
    blk = panel[panel.index('<span className="do-label">기준일</span>'):]
    blk = blk[:blk.index("</li>")]
    assert 'type="date"' in blk and "delibOpts.as_of" in blk and "as_of: e.target.value || undefined" in blk, blk
    store = (_FRONT / "chatStore.ts").read_text(encoding="utf-8")
    body = store[store.index("export function delibOptsToWire"):]
    body = body[: body.index("\n}")]
    assert "if (o.as_of && AS_OF_RE.test(o.as_of)) w.as_of = o.as_of;" in body, body[-400:]
    m = re.search(r"^export const AS_OF_RE = /(.+)/;$", store, re.M)
    pats = [x.get("pattern") for x in DelibOpts.model_json_schema()["properties"]["as_of"].get("anyOf", []) if x.get("pattern")]
    assert m and pats == [m.group(1)], f"프론트의 기준일 꼴({m and m.group(1)})이 포털 pattern({pats})과 다르다"


@pytest.mark.skipif(not (_FRONT.parents[1] / "node_modules/typescript").exists() or not shutil.which("node"),
                    reason="frontend node_modules(typescript) 또는 node 가 없다 — 보내기 함수를 돌려 볼 수 없다")
def test_프론트는_꼴이_맞는_기준일만_싣는다(tmp_path):
    """chatStore.ts 를 옮겨 적어 node 로 부른다(test_delib_timeout_cap_contract 와 같은 길) — 틀린 꼴을 실으면 포털이 요청째 422 로 막는다."""
    import json
    import subprocess

    (tmp_path / "run.cjs").write_text(
        "const ts = require('typescript'); const fs = require('fs');\n"
        f"const js = ts.transpileModule(fs.readFileSync({json.dumps(str(_FRONT / 'chatStore.ts'))}, 'utf8'),\n"
        "  { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2019 } });\n"
        "fs.writeFileSync(__dirname + '/chatStore.js', js.outputText);\n"
        "const { delibOptsToWire } = require('./chatStore.js');\n"
        "const sent = JSON.parse(process.argv[2]).map((v) => delibOptsToWire({ as_of: v }).as_of ?? null);\n"
        "process.stdout.write(JSON.stringify(sent));\n", encoding="utf-8")
    vals = ["2025-06-01", "2025-6-1", " 2025-06-01", "2025-06-01T09:00:00", "", "２０２５-０６-０１"]
    r = subprocess.run(["node", "run.cjs", json.dumps(vals, ensure_ascii=False)], cwd=str(tmp_path), capture_output=True,
                       text=True, timeout=120, env={"PATH": "/usr/bin:/bin:" + str(Path(shutil.which("node")).parent),
                                                    "NODE_PATH": str(_FRONT.parents[1] / "node_modules")})
    assert r.returncode == 0, r.stdout + r.stderr
    sent = json.loads(r.stdout)
    assert sent == ["2025-06-01", None, None, None, None, None], sent
    assert all(_portal_takes_as_of(v) for v in sent if v is not None), "프론트가 실은 기준일을 포털이 받지 않는다"


@pytest.mark.parametrize("v", ["human", "app"])
def test_누가_띄운_심의인지가_포털을_지나_살아_나온다(v):
    """M3 #26 — 리스크 앱 러너가 패널마다 started_by:"app" 을 싣는다. 선언이 없으면 model_dump(exclude_none=True) 에서 조용히
    사라지고, 엔진은 쟁점 패널을 사람 심의로 세어 카드 대조 관문을 절반(4)으로 내린다."""
    from app.agent.routes import ChatRequest

    wire = ChatRequest(message="/심의 화두", delib_opts={"started_by": v}).delib_opts.model_dump(exclude_none=True)
    assert wire.get("started_by") == v
    assert "started_by" not in ChatRequest(message="/심의 화두", delib_opts={}).delib_opts.model_dump(exclude_none=True)


@pytest.mark.parametrize("bad", ["robot", "", 1, "APP"])
def test_started_by_는_human_app_밖이면_422(bad):
    from pydantic import ValidationError

    from app.agent.routes import ChatRequest

    with pytest.raises(ValidationError):
        ChatRequest(message="/심의 화두", delib_opts={"started_by": bad})


# ── 외부 응답자 선택 · 반출 동의(X-3a) — docs/risk-claude-engine ────────────────────────────────────────────
# 엔진은 delib_opts.llm=external 이면 판단 호출을 잡 주인의 과제 줄로 보내고, consent_external 이 JSON true 가 아니면 시작하지 않는다.
# 포털에 선언이 없던 동안은 둘 다 model_dump(exclude_none=True) 에서 말없이 떨어져 외부를 고른 심의가 GLM 으로 돌았다. 보내는 곳은
# 리스크 앱뿐이다(포털 화면에는 입구가 없다). 동의는 StrictBool — "true"·1 을 true 로 바꿔 넘기면 동의가 아닌 것을 동의로 세탁한다.
@pytest.mark.parametrize("opts", [
    {"llm": "external", "consent_external": True},
    {"llm": "external", "consent_external": False},     # 엔진이 거절할 값도 바꾸지 않고 넘긴다 — 거절은 엔진의 몫이다
    {"llm": "glm"},
    {"consent_external": True},
], ids=["external+consent", "external+false", "glm", "consent-only"])
def test_외부_응답자_선택과_반출_동의가_포털을_지나_살아_나온다(opts):
    from app.agent.routes import ChatRequest

    wire = ChatRequest(message="/심의 화두", delib_opts=opts).delib_opts.model_dump(exclude_none=True)
    assert wire == opts
    if "consent_external" in opts:
        assert wire["consent_external"] is opts["consent_external"], "동의는 bool 그대로 간다"
    # 안 보내면 안 나간다 — 없는 선택을 glm 으로, 없는 동의를 false 로 채워 보내지 않는다.
    silent = ChatRequest(message="/심의 화두", delib_opts={}).delib_opts.model_dump(exclude_none=True)
    assert "llm" not in silent and "consent_external" not in silent


@pytest.mark.parametrize("bad", [
    {"llm": "claude"}, {"llm": "External"}, {"llm": " external"}, {"llm": ""}, {"llm": 1}, {"llm": True},
    {"consent_external": "true"}, {"consent_external": "True"}, {"consent_external": 1}, {"consent_external": "1"},
    {"consent_external": 1.0}, {"consent_external": 0}, {"consent_external": "false"}, {"consent_external": "yes"},
], ids=lambda b: f"{next(iter(b))}={next(iter(b.values()))!r}")
def test_외부_응답자_선택과_동의의_모양이_틀리면_422(bad):
    from pydantic import ValidationError

    from app.agent.routes import ChatRequest

    with pytest.raises(ValidationError):
        ChatRequest(message="/심의 화두", delib_opts={"llm": "external", "consent_external": True, **bad})


# 포털을 지나는 심의 요청의 세 모양 — 셋 다 POST /agent/chat 하나(_relay_stream)로 엔진의 /chat 에 간다. 리스크 앱 러너(engine_client)도
# 이어하기·핸드오프(프론트 sendMessage 의 extraDelibOpts)도 같은 길이다. 웹 화면은 llm 을 내지 않지만 길은 같다.
_SHAPES = {
    "web": {"evidence_prepass": 1, "rounds": 3, "search_sources": []},
    "risk_runner": {"started_by": "app", "free_tools": 1, "tools": [], "voc": "off", "save_report": 0,
                    "persona_knowledge": 1, "chair_template": "risk-review",
                    "knowledge_query": {"mech-a": "리브 두께 감소", "*": "커넥터 간극"},
                    "personas": [{"key": "mech-a", "name": "기구 A"}],
                    "evidence": [{"id": "E0", "title": "브리프", "result": "근거 원문"}]},
    "continue": {"continue_summary": "이전 결정문", "non_negotiables": ["조항 1"], "rounds_so_far": 3,
                 "human_note": "사람 의견", "append_to_report_id": 7, "rescreen": 0},
}


_HEALTH_NEW = {"status": "ok", "delib_as_of": True}      # 기준일을 받는 판의 /health(에이전트 서버 wt1031/ha11)


def _relay_chat(*bodies: dict, health: dict | str = _HEALTH_NEW, texts: list | None = None,
                probes: list | None = None) -> tuple[list[int], list[dict]]:
    """POST /agent/chat 을 차례로 부르고 (상태들, 엔진 /chat 이 받은 본문들)을 돌려준다. 엔진은 MockTransport 대역이다 — /health 는
    health(사전, 또는 'down' 이면 연결 실패)로 답한다. texts 를 주면 응답 본문(SSE)을, probes 를 주면 /health 를 물은 횟수를 담는다."""
    import json

    import httpx
    from fastapi.testclient import TestClient

    from app.auth.provider import Principal
    from app.deps import principal_pat_or_session
    from app.main import app

    seen: list[dict] = []

    def engine(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/health":
            if probes is not None:
                probes.append(1)
            if health == "down":
                raise httpx.ConnectError("에이전트 서버 대역 — /health 무응답", request=req)
            return httpx.Response(200, json=health)
        assert req.url.path == "/chat"
        seen.append(json.loads(req.content))
        return httpx.Response(200, stream=httpx.ByteStream(b"event: done\ndata: {}\n\n"))

    app.dependency_overrides[principal_pat_or_session] = lambda: Principal(
        subject="u1", email="u1@hwax.local", display_name="U", groups=["eng-team", "feat:deliberation"])
    try:
        with TestClient(app) as c:
            real = app.state.agent_client
            app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(engine))
            try:
                codes = []
                for b in bodies:
                    r = c.post("/agent/chat", json=b)
                    codes.append(r.status_code)
                    if texts is not None:
                        texts.append(r.text)
            finally:
                app.state.agent_client = real
    finally:
        app.dependency_overrides.pop(principal_pat_or_session, None)
    return codes, seen


@pytest.mark.parametrize("shape", sorted(_SHAPES))
def test_외부_응답자_선택과_동의가_심의_중계_길마다_엔진_본문에_그대로_닿는다(shape):
    base = _SHAPES[shape]
    ext = {**base, "llm": "external", "consent_external": True}
    codes, seen = _relay_chat(
        {"message": "/심의 화두", "delib_opts": ext},
        {"message": "/심의 화두", "delib_opts": base},                                            # GLM — 종전 그대로
        {"message": "/심의 화두", "delib_opts": {**ext, "consent_external": "true"}},             # 문자열 동의
        {"message": "/심의 화두", "delib_opts": {**ext, "consent_external": 1}},                  # 수 동의
        {"message": "/심의 화두", "delib_opts": {**ext, "llm": "claude"}})                        # 모르는 선택
    assert codes == [200, 200, 422, 422, 422]
    assert len(seen) == 2, "422 로 막힌 요청이 엔진으로 나갔다"
    assert seen[0]["delib_opts"] == ext, "외부 선택·동의를 실은 심의 손잡이가 엔진에 그대로 닿지 않았다"
    assert seen[0]["delib_opts"]["consent_external"] is True and seen[0]["user_email"] == "u1@hwax.local"
    assert seen[1]["delib_opts"] == base, "GLM 심의 본문이 바뀌었다(없는 llm·동의를 채워 보내면 안 된다)"


# 포털 모델의 출력을 스위치를 켠 엔진(EXTERNAL_LLM_ENABLED=1)의 실제 _resolve_opts · _external_refusal 에 넣는다 — 소비자의 입력을
# 생산자의 실제 출력으로 만든다. 셸의 다른 EXTERNAL_LLM_* · DELIB_* 는 물려받지 않는다(값이 틀리면 엔진이 길을 닫아 시험이 흔들린다).
_ENGINE_EXTERNAL = (
    "import json, sys, types, deliberation as d\n"
    "app = types.SimpleNamespace(state=types.SimpleNamespace())\n"
    "out = []\n"
    "for req in json.load(sys.stdin):\n"
    "    o = d._resolve_opts(req)\n"
    "    refused = d._external_refusal(app, req, 'u1@hwax.local')\n"
    "    out.append({'llm': o.llm, 'unread': o.req_unread, 'refused': (refused or {}).get('code')})\n"
    "print(json.dumps(out, ensure_ascii=False))\n"
)


def test_포털이_낸_외부_선택과_동의를_엔진이_그대로_읽는다():
    if not _ENGINE.exists():
        pytest.skip(f"형제 리포 없음: {_ENGINE}")
    import json
    import os
    import subprocess
    import sys

    from app.agent.routes import ChatRequest

    cases = [{"llm": "external", "consent_external": True}, {"llm": "external"},
             {"llm": "external", "consent_external": False}, {"llm": "glm"}, {}]
    wire = [ChatRequest(message="/심의 화두", delib_opts=c).delib_opts.model_dump(exclude_none=True) for c in cases]
    assert wire == cases, "포털 모델이 값을 바꾸거나 버렸다 — 엔진에 닿기 전에 갈라졌다"
    env = {k: v for k, v in os.environ.items() if not k.startswith(("EXTERNAL_LLM_", "DELIB_"))}
    r = subprocess.run([sys.executable, "-c", _ENGINE_EXTERNAL], input=json.dumps(wire), cwd=_ENGINE.parent,
                       env={**env, "EXTERNAL_LLM_ENABLED": "1", "PYTHONDONTWRITEBYTECODE": "1"},
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, f"엔진 _resolve_opts·_external_refusal 을 이 venv 로 부르지 못했다 — {r.stderr.strip()[-600:]}"
    got = json.loads(r.stdout.strip().splitlines()[-1])
    assert [(g["llm"], g["refused"]) for g in got] == [
        ("external", None),                               # 동의가 JSON true 로 닿아 열린다
        ("external", "external_consent_required"),        # 동의 없는 외부 선택은 엔진이 막는다(포털은 동의를 지어내지 않는다)
        ("external", "external_consent_required"),
        ("glm", None), ("glm", None)], got
    assert all(g["unread"] == {} for g in got), f"포털을 지난 llm 을 엔진이 못 읽었다: {got}"


def test_외부_응답자_과제의_대상_열쇠를_엔진에_그대로_넘긴다():
    """쟁점 패널(질문 머리가 `[쟁점 …]`)의 외부 과제는 엔진이 delib_opts.target_key 로만 대상을 안다(X-D9) — 포털이 떨어뜨리면 워크플로가
    그 과제를 답하지 않아 잡이 external_worker 로 선다. 모양은 엔진과 같아야 한다(다르면 포털이 멀쩡한 열쇠를 422 로 막거나 틀린 것을 넘긴다)."""
    from pydantic import ValidationError

    from app.agent.routes import ChatRequest
    ok = "diff:eacc7fb1134d416096a088b8a1ea9246"
    wire = ChatRequest(message="/심의 화두", delib_opts={"llm": "external", "consent_external": True, "target_key": ok}) \
        .delib_opts.model_dump(exclude_none=True)
    assert wire["target_key"] == ok
    assert ChatRequest(message="/심의 화두", delib_opts={"target_key": "snap:abc_1-2"}).delib_opts.target_key == "snap:abc_1-2"
    for bad in ("proj:abc", "diff:", "diff:-abc", "diff:" + "a" * 65, "diff:a b", " diff:abc"):
        with pytest.raises(ValidationError):
            ChatRequest(message="/심의 화두", delib_opts={"target_key": bad})
    assert "target_key" not in ChatRequest(message="/심의 화두", delib_opts={}).delib_opts.model_dump(exclude_none=True)



def test_위키에_남기기와_원장의_소속이_엔진_본문에_닿는다(monkeypatch):
    """P8(docs/mxwp-wiki) — 손잡이 wiki 는 delib_opts 로, 범위가 될 소속은 원장 값으로 본문 꼭대기 affiliation 에 간다. 브라우저가 실어 보낸
    소속은 버린다(ChatRequest 가 모르는 칸) — 신원은 검증된 주체에서만 채운다. 손잡이 범위 밖(2)은 422 다."""
    from app.agent import wiki_send

    monkeypatch.setattr(wiki_send, "known_affiliation", lambda _request: "CAEG")
    codes, seen = _relay_chat({"message": "/심의 화두", "delib_opts": {"wiki": 1}},
                              {"message": "/심의 화두", "delib_opts": {"wiki": 2}},
                              {"message": "/심의 화두", "affiliation": "OTHER"})
    assert codes == [200, 422, 200]
    assert seen[0]["delib_opts"] == {"wiki": 1} and seen[0]["affiliation"] == "CAEG"
    assert seen[1]["affiliation"] == "CAEG" and "delib_opts" not in seen[1], "브라우저가 보낸 소속이 엔진에 닿았다"
