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
}


def _engine_request_keys() -> set[str]:
    """엔진 _resolve_opts 가 요청(req_opts)에서 읽는 키 — 낱개 get("…") 과 정수 손잡이 루프의 튜플."""
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
    return keys | set(re.findall(r'"([a-z_]+)"', listed))


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
