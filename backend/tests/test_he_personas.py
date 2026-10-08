# HE팀 MCP 운영자 정본(he-team.json)·동기화 스크립트·조직도 라벨·에이전트서버 상한이 서로 맞는지
"""HE팀 페르소나는 네 곳이 맞물린다.

  정본      infra/personas/he-team.json          키·묶음·앱·사전 지식
  동기화    infra/scripts/sync-he-personas.py    system_prompt 조립·도구 이름 대조·AIDataHub upsert
  조직도    frontend/.../personaCatalog.ts       HE_GROUP_LABEL(묶음 라벨)
  에이전트  HWAXAgentServer/app.py               PERSONA_ROLE_MAX(역할을 이만큼만 싣는다)

한 곳만 고치면 조용히 샌다 — 묶음 라벨이 빠지면 조직도에 코드가 뜨고, 상한이 어긋나면 역할 뒤쪽
('답하는 법')이 잘린 채 돈다.
"""

import importlib.util
import json
import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = _ROOT / "infra" / "personas" / "he-team.json"
_SCRIPT = _ROOT / "infra" / "scripts" / "sync-he-personas.py"
_CATALOG = _ROOT / "frontend" / "src" / "components" / "chat" / "personaCatalog.ts"
_AGENT = _ROOT.parent / "HWAXAgentServer" / "app.py"


def _sync():
    spec = importlib.util.spec_from_file_location("sync_he_personas", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load():
    return json.loads(_SPEC.read_text(encoding="utf-8"))


def test_정본_키와_칸():
    spec = _load()
    keys = [p["key"] for p in spec["personas"]]
    assert len(keys) == len(set(keys)), "키가 겹친다"
    for p in spec["personas"]:
        m = re.fullmatch(r"he-([a-z]+)-([a-z0-9]+)", p["key"])
        assert m, f"{p['key']}: he-<묶음>-<앱> 형식이어야 조직도가 묶음으로 접는다"
        assert m.group(1) in spec["groups"], f"{p['key']}: 묶음 {m.group(1)} 이 groups 에 없다"
        for fld in ("name", "summary", "mission"):
            assert p[fld].strip(), f"{p['key']}: {fld} 가 비었다"
        for fld in ("can", "workflow", "concepts", "pitfalls", "samples"):
            assert p[fld], f"{p['key']}: {fld} 가 비었다"
        assert p["apps"], f"{p['key']}: 모는 앱이 없다"
        assert not set(p["writes"]) & set(p["confirm"]), f"{p['key']}: writes·confirm 겹침"


def test_한국어_문장은_콜론으로_끝나지_않는다():
    for p in _load()["personas"]:
        for fld in ("mission", "summary"):
            assert not p[fld].rstrip().endswith(":"), f"{p['key']}.{fld}"
        for fld in ("can", "workflow", "concepts", "pitfalls"):
            for s in p[fld]:
                assert not s.rstrip().endswith(":"), f"{p['key']}.{fld}: {s}"


def test_조직도_묶음_라벨이_정본과_같다():
    """라벨 정본은 orgTaxonomy.json 하나다 — 프론트가 import 하고, 포털이 /internal/org-taxonomy
    로 내보내 MCP 게이트웨이(클로드 조직도)도 같은 표를 쓴다. 어긋나면 조직도에 코드가 뜬다."""
    tax = json.loads((_CATALOG.parent / "orgTaxonomy.json").read_text(encoding="utf-8"))
    assert tax["he_group_label"] == _load()["groups"]


FAKE_MAP = {
    "map": {
        "predict_sed": "heax-thermal_shock_mcp",
        "get_dataset_summary": "heax-thermal_shock_mcp",
        "parse_raw_rows": "heax-thermal_shock_mcp",
        "predict_sed_batch": "heax-thermal_shock_mcp",
        "get_model_info": "heax-thermal_shock_mcp",
        "add_training_data": "heax-thermal_shock_mcp",
        "remove_training_data": "heax-thermal_shock_mcp",
        "train_model": "heax-thermal_shock_mcp",
        "activate_model": "heax-thermal_shock_mcp",
        "arp_search": "arp",
        "arp_get": "arp",
    },
    "areas": {"predict_sed": "calc", "arp_search": "knowledge"},
    "area_meta": [
        {"area": "calc", "label": "해석 계산·예측"},
        {"area": "knowledge", "label": "사내 지식 검색"},
    ],
    "apps": [
        {"app": "heax-thermal_shock_mcp", "label": "Thermal Shock"},
        {"app": "arp", "label": "AI Ready Portal"},
    ],
}


def _one(key):
    spec = _load()
    return {**spec, "personas": [p for p in spec["personas"] if p["key"] == key]}


def test_조립한_프롬프트는_지식카드_안내를_끄고_앱을_묶는다():
    rows, skipped, errors = _sync().plan(_one("he-calc-thermalshock"), FAKE_MAP)
    assert not errors and not skipped
    (r,) = rows
    assert r["system_prompt"].startswith("<!-- no-tool-guide -->"), (
        "없으면 AIDataHub 가 agent_search 안내를 덧붙인다"
    )
    assert r["response_config"] == {
        "persona_kind": "mcp_operator",
        "mcp_apps": ["heax-thermal_shock_mcp"],
        "key_tools": _one("he-calc-thermalshock")["personas"][0]["key_tools"],
        "managed_by": "HWAXPortal/infra/personas/he-team.json",
    }
    assert "HE팀" in r["common_tags"] and "해석 계산·물성" in r["common_tags"]
    assert "## 답하는 법" in r["system_prompt"]


def test_게이트웨이에_없는_앱은_건너뛰고_없는_도구_이름은_멈춘다():
    sync = _sync()
    rows, skipped, errors = sync.plan(_one("he-cad-odbhub"), FAKE_MAP)
    assert rows == [] and skipped and not errors
    bad = _one("he-calc-thermalshock")
    bad["personas"][0] = {**bad["personas"][0], "key_tools": ["predict_sedd"]}
    _rows, _skipped, errors = sync.plan(bad, FAKE_MAP)
    assert errors and "predict_sedd" in errors[0], (
        "오타 난 도구 이름을 그대로 올리면 모델이 없는 도구를 부른다"
    )


def test_사전_지식이_얇은_앱은_도구_지도를_싣는다():
    rows, _s, errors = _sync().plan(_one("he-data-arp"), FAKE_MAP)
    assert not errors
    assert "## 도구 지도" in rows[0]["system_prompt"]
    assert "arp_search" in rows[0]["system_prompt"] and "arp_get" in rows[0]["system_prompt"]


def test_프롬프트_상한이_에이전트서버와_같다():
    if not _AGENT.exists():
        pytest.skip(f"형제 리포 없음: {_AGENT}")
    m = re.search(r"^PERSONA_ROLE_MAX\s*=\s*(\d+)", _AGENT.read_text(encoding="utf-8"), re.M)
    assert m, "app.py 에서 PERSONA_ROLE_MAX 를 못 찾았다"
    assert int(m.group(1)) == _sync().PROMPT_MAX, (
        "동기화가 허락한 길이를 에이전트서버가 자르면 역할 뒤쪽이 사라진다"
    )


# ── 다른 앱과 이름이 겹치는 도구 — 접두 이름으로 적는다 ───────────────────────────────────────────
# 게이트웨이는 붙어 있는 두 백엔드가 같은 도구 이름을 내놓으면 **양쪽 다** `<백엔드 키에서 하이픈을 뺀 것>_<이름>` 으로
# 노출한다(HWAXMcpGateway `_aggregate`). 동기화 스크립트는 정본의 이름을 그 노출 이름(/tools-map)과 대조하고, 에이전트
# 서버도 key_tools 를 같은 표에서 찾아 묶는다 — 겹치는 도구를 맨 이름으로 적으면 묶이지 않고 모델은 없는 도구를 부른다.
# 접두 이름으로 적는 이유는 '이 박스가 그렇게 내놓아서' 가 아니다 — 그 이름이 **언제나 부를 수 있는 별칭**이라서다. 노출 이름은
# 겹치는 상대가 붙어 있느냐로 뒤집히지만(ste 가 없는 박스는 list_jobs 를 맨 이름으로 낸다) 별칭은 어느 박스에서나 받는다.
# ste 가 게이트웨이에 붙으면서 list_jobs·submit_job·prepare_upload 가 맨 이름으로 안 나오게 됐는데 정본 세 곳이 맨 이름으로
# 남아, 동기화 미리보기가 '이 앱에 없는 도구' 로 멈췄다(2026-10-07). ste 는 페르소나가 없어 정본에서는 겹침이 안 보인다 —
# 그래서 그쪽 이름을 여기 적어 둔다(dev 게이트웨이 /tools-map 실측). ste 가 도구를 더 내놓으면 이 목록에 더한다.
_STE_NATIVE = frozenset({"list_jobs", "submit_job", "prepare_upload", "cancel_job"})
_TOOL_FIELDS = ("key_tools", "writes", "confirm")


def _native(name: str, apps: list[str]) -> str:
    """노출 이름 → 그 앱이 원래 내놓는 이름. 접두(앱 키에서 하이픈을 뺀 것 + '_')가 붙어 있으면 뗀다."""
    for app in apps:
        prefix = app.replace("-", "") + "_"
        if name.startswith(prefix):
            return name[len(prefix):]
    return name


def test_다른_앱과_이름이_겹치는_도구는_접두_이름으로_적는다():
    personas = _load()["personas"]
    assert len({tuple(p["apps"]) for p in personas}) == len(personas), "앱 묶음을 같이 쓰는 페르소나가 생겼다 — 아래 판정을 다시 본다"
    owners: dict[str, set[str]] = {}
    for p in personas:
        for fld in _TOOL_FIELDS:
            for name in p[fld]:
                owners.setdefault(_native(name, p["apps"]), set()).add(p["key"])
    # 겹치는 이름 = 두 페르소나(= 서로 다른 앱)가 같이 적은 이름 + ste 가 내놓는 이름
    shared = {n for n, who in owners.items() if len(who) > 1} | _STE_NATIVE
    bare = [f"{p['key']}.{fld}: {name}" for p in personas for fld in _TOOL_FIELDS for name in p[fld]
            if name in shared and _native(name, p["apps"]) == name]
    assert not bare, ("다른 앱과 겹치는 도구를 맨 이름으로 적었다 — 게이트웨이는 `<앱 키에서 하이픈 뺀 것>_<이름>` 으로 내놓는다"
                      f"(예: heaxstep_forge_list_jobs). {bare}")
    # 그 세 자리 — 게이트웨이가 언제나 받는 별칭이다(ste 가 붙은 박스에서는 노출 이름이기도 하다 — /tools-map 으로 확인)
    by_key = {p["key"]: p for p in personas}
    assert "heaxstep_forge_list_jobs" in by_key["he-cad-stepforge"]["key_tools"]
    assert "smarttwinmcp_submit_job" in by_key["he-sim-smarttwin"]["writes"]
    assert "reportarchive_prepare_upload" in by_key["he-doc-reportarchive"]["writes"]


def test_맨_이름으로_적으면_동기화가_멈춘다():
    """이 방향은 느슨하게 하지 않는다 — 접두로 노출된 도구를 맨 이름으로 적으면 그 이름은 정말 없는 도구라 멈추는 것이 맞다.
    ste 가 붙은 게이트웨이의 표를 흉내 내 정본의 접두 이름은 통과하고 맨 이름으로 되돌린 사본은 걸리는지 본다."""
    sync = _sync()
    one = _one("he-doc-reportarchive")
    persona = one["personas"][0]
    names = {n for fld in _TOOL_FIELDS for n in persona[fld]}
    tmap = {"map": {**dict.fromkeys(names, "reportarchive"), "ste_prepare_upload": "ste"}, "areas": {}, "area_meta": [],
            "apps": [{"app": "reportarchive", "label": "리포트 아카이브"}, {"app": "ste", "label": "ste"}]}
    _rows, skipped, errors = sync.plan(one, tmap)
    assert not errors and not skipped, (errors, skipped)
    back = {**one, "personas": [{**persona, "writes": [n.replace("reportarchive_prepare_upload", "prepare_upload")
                                                       for n in persona["writes"]]}]}
    _rows, _skipped, errors = sync.plan(back, tmap)
    assert errors and "prepare_upload" in errors[0] and "writes" in errors[0]


def test_접두_이름은_겹치는_앱이_빠진_게이트웨이에서도_통과한다():
    """노출 이름은 **붙어 있는 다른 백엔드**에 따라 뒤집힌다 — 게이트웨이는 지금 붙은 백엔드끼리 이름이 겹칠 때만 접두를 붙인다.
    ste 가 없는 박스(또는 ste 가 한동안 안 닿은 dev)는 list_jobs·submit_job·prepare_upload 를 맨 이름으로 내놓고,
    smart-twin-mcp 가 없는 박스(cae00 기본)는 job_status 를 맨 이름으로 내놓는다. 정본의 접두 이름을 노출 이름과만 대조하면
    그 박스에서 동기화가 '이 앱에 없는 도구' 로 통째로 멈춘다(한 명이 걸리면 아무도 안 올라간다) — 어느 정본도 두 박스를
    같이 통과하지 못했다. 접두 이름은 게이트웨이가 **언제나** 받는 호출 전용 별칭이라 그 표에서도 맞는 이름이다."""
    sync = _sync()
    for key in ("he-doc-reportarchive", "he-cad-stepforge", "he-sim-smarttwin"):
        one = _one(key)
        persona = one["personas"][0]
        names = {n for fld in _TOOL_FIELDS for n in persona[fld]}
        assert any(_native(n, persona["apps"]) != n for n in names), f"{key}: 접두 이름이 없다 — 이 시험이 아무것도 안 본다"
        # 겹치는 상대가 하나도 안 붙은 게이트웨이 — 이 앱의 도구가 전부 원래 이름으로 나온다
        app = persona["apps"][0]
        tmap = {"map": dict.fromkeys({_native(n, persona["apps"]) for n in names}, app), "areas": {}, "area_meta": [],
                "apps": [{"app": a, "label": a} for a in persona["apps"]]}
        tmap["map"].update({f"{a}-ping": a for a in persona["apps"][1:]})      # 둘째 앱도 붙어는 있다(없으면 건너뛴다)
        rows, skipped, errors = sync.plan(one, tmap)
        assert not errors and not skipped, (key, errors, skipped)
        assert rows[0]["response_config"]["key_tools"] == persona["key_tools"], "올리는 값은 정본 그대로다 — 박스마다 바뀌면 AIDataHub 사본이 출렁인다"


# ── 심의 운영자 — 엔진이 바꾼 계약을 안내문이 따라간다 ─────────────────────────────────────────────
# 이 페르소나의 안내문은 모델이 심의 도구를 모는 법이다. 엔진(HWAXAgentServer)이 대기열을 넣고(상한에 걸리면 거절이 아니라
# status=queued) 남의 심의를 접지 못하게 한 뒤에도 안내문은 옛 계약을 말했다 — 그대로면 모델이 줄 선 심의를 실패로 읽고 같은
# 심의를 다시 시작하고(두 번 줄을 선다), 막히면 남의 심의를 접으라고 사용자에게 권한다(거절된다).
_DELIB_TOOLS = ("deliberate_jobs", "deliberate_start", "deliberate_status", "deliberate_result", "deliberate_transcript",
                "deliberate_continue", "deliberate_list", "deliberate_cancel")
_DELIB_MAP = {"map": dict.fromkeys(_DELIB_TOOLS, "hwax-deliberation"), "areas": {}, "area_meta": [],
              "apps": [{"app": "hwax-deliberation", "label": "HWAX 심의"}]}
_ENGINE_MCP = _ROOT.parent / "HWAXAgentServer" / "mcp_server.py"
_ENGINE = _ROOT.parent / "HWAXAgentServer" / "deliberation.py"


def _delib_prompt() -> str:
    rows, skipped, errors = _sync().plan(_one("he-expert-deliberation"), _DELIB_MAP)
    assert not errors and not skipped, (errors, skipped)       # 길이 상한(PROMPT_MAX)을 넘겨도 여기서 걸린다
    return rows[0]["system_prompt"]


def test_심의_운영자는_줄_선_심의를_다시_시작하지_않는다():
    prompt = _delib_prompt()
    assert "queued" in prompt and "queue.position" in prompt, "줄을 섰다는 응답(status=queued)과 순번을 읽는 법이 없다"
    assert "다시 시작하지" in prompt, "줄 선 심의를 실패로 읽으면 같은 심의를 또 시작한다"
    if _ENGINE_MCP.exists():
        src = _ENGINE_MCP.read_text(encoding="utf-8")
        assert "queued" in src and "queue.position" in src, "엔진의 대기열 계약이 바뀌었다 — 이 안내문을 다시 맞춘다"


def test_심의_운영자는_남의_심의를_접으라고_권하지_않는다():
    """엔진은 신원이 다른 사람의 심의를 접지 못하게 한다. '막히면 필요 없는 것을 접으라' 는 옛 안내는 남의 심의를 가리킨다."""
    spec = _one("he-expert-deliberation")["personas"][0]
    said = " ".join(spec["pitfalls"] + spec["workflow"])
    assert "필요 없는 것을 사용자 확인 뒤 deliberate_cancel" not in said
    assert "내 심의" in said and "deliberate_cancel" in spec["confirm"]


def test_심의_운영자는_근거_상한을_숫자로_박아_두지_않는다():
    """안내문에 적어 둔 '최대 12' 는 엔진 값(지금 120, env 로 바뀐다)과 달랐다 — 숫자를 고쳐 적으면 같은 일이 또 난다.
    지금 값은 deliberate_jobs 의 limits 가 알려 준다."""
    spec = _one("he-expert-deliberation")["personas"][0]
    line = next(c for c in spec["concepts"] if c.startswith("evidence"))
    assert not re.search(r"최대\s*\d+", line), line
    assert "deliberate_jobs" in line and "limits" in line
    if _ENGINE_MCP.exists():
        assert '"limits"' in _ENGINE_MCP.read_text(encoding="utf-8"), "deliberate_jobs 가 limits 를 더는 내지 않는다 — 안내문을 다시 맞춘다"


def test_심의_운영자는_좌석_상한을_숫자로_박아_두지_않는다():
    """같은 낡음이 바로 아랫줄에 남아 있었다 — '직접 지정은 최대 20석'. 엔진의 좌석 상한은 이제 env 손잡이다(DELIB_MAX_SEATS,
    docs/delib-engine-feedback D-3). 22석으로 올린 박스에서 이 안내문은 20 이라 말하고 도구는 22 라 답해, 운영자 페르소나가
    21·22석 패널을 줄이거나 거절하게 이끈다. '2석 미만' 은 코드에 박힌 하한이라 그대로 둔다."""
    spec = _one("he-expert-deliberation")["personas"][0]
    line = next(c for c in spec["concepts"] if c.startswith("personas"))
    assert not re.search(r"최대\s*\d+\s*석", line), line
    assert "deliberate_jobs" in line and "limits.seats" in line
    assert "2석 미만" in line
    if _ENGINE_MCP.exists():
        assert '"seats": _engine.MAX_REQ_SEATS' in _ENGINE_MCP.read_text(encoding="utf-8"), (
            "deliberate_jobs 가 limits.seats 를 더는 엔진 상수에서 내지 않는다 — 안내문을 다시 맞춘다")

