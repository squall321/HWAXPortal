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
import os
import re
import subprocess
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
        # ARP 운영자가 정본에 적은 도구(docs/request-1030 HP-53) — 조회 둘은 10-29 QA 가 적은 이름(선택 칸 — 있을 때만 잇는다),
        # 올리기 넷은 10-30 cae00 /tools-map
        "search_data": "arp",
        "compare_items": "arp",
        "arp_upload_create": "arp",
        "arp_upload_stage": "arp",
        "arp_upload_register": "arp",
        "arp_upload_discard": "arp",
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
# cae00 에서 접두 이름으로만 있는 것 — 그 박스 미리보기가 '이 앱에 없는 도구' 로 exit 2 였다(10-27, docs/request-1027 HP-19).
# cae00 /tools-map 에는 heaxkooremapper_mcp_get_job · aidatahub_list_tags · reportarchive_get_guide · reportarchive_restore_version
# 으로만 있다(겹치는 상대 앱은 그 미리보기에 없다). dev 는 겹치는 상대가 없어 맨 이름으로 낸다 — 정본만 보면 겹침이 안 보인다.
_CAE00_PREFIXED = frozenset({"get_job", "list_tags", "get_guide", "restore_version"})
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
    shared = {n for n, who in owners.items() if len(who) > 1} | _STE_NATIVE | _CAE00_PREFIXED
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


# cae00 게이트웨이(10-15 실측) — simflow 가 같은 이름을 내놓아 reportarchive 의 upload_from_url·upload_file 은 접두 이름으로만 나오고,
# 웹 리서치 브로커는 공급자(WEB_PROVIDER)가 없어 search_web 을 등록하지 않았다(도구 7개).
_CAE00_SHARED = {"upload_from_url": "simflow", "upload_file": "simflow", "prepare_upload": "ste",
                 "list_reports": "heax-kooremapper_mcp"}


def _cae00_map(persona: dict, extra: set[str], drop: set[str]) -> dict:
    app = persona["apps"][0]
    names = ({_native(n, persona["apps"]) for fld in _TOOL_FIELDS for n in persona[fld]} | extra) - drop
    tmap = {"map": {}, "areas": {}, "area_meta": [], "apps": [{"app": app, "label": app}]}
    for n in names:
        if n in _CAE00_SHARED:   # 겹치면 게이트웨이가 양쪽 다 접두 이름으로 낸다
            tmap["map"][f"{app.replace('-', '')}_{n}"] = app
            other = _CAE00_SHARED[n]
            tmap["map"][f"{other.replace('-', '')}_{n}"] = other
        else:
            tmap["map"][n] = app
    return tmap


def test_정본은_cae00_게이트웨이에서도_멈추지_않는다():
    """오류가 하나라도 있으면 동기화는 아무도 안 올린다 — cae00 에서 정본 두 줄 때문에 ODB 허브 운영자를 만들 수 없었다(K8-1)."""
    sync = _sync()
    ra = _one("he-doc-reportarchive")
    _rows, skipped, errors = sync.plan(ra, _cae00_map(ra["personas"][0], {"upload_file"}, set()))
    assert not errors and not skipped, errors
    web = _one("he-research-web")
    _rows, skipped, errors = sync.plan(web, _cae00_map(web["personas"][0], {"list_egress_log"}, {"search_web"}))
    assert not errors and not skipped, errors


def test_HP19_cae00_에서_접두로만_있는_이름도_멈추지_않는다():
    """정본에 접두 별칭을 적으면 cae00(접두로만 노출) · dev(맨 이름 노출) 둘 다 통과하고, 올리는 값이 박스마다 같다(HP-19)."""
    sync = _sync()
    for key in ("he-sim-dynaforge", "he-data-aidatahub", "he-doc-reportarchive"):
        one = _one(key)
        p = one["personas"][0]
        app = p["apps"][0]
        names = {_native(n, p["apps"]) for fld in _TOOL_FIELDS for n in p[fld]}
        assert names & _CAE00_PREFIXED, key
        cae00 = {(f"{app.replace('-', '')}_{n}" if n in _CAE00_PREFIXED else n): app for n in names}
        dev = dict.fromkeys(names, app)
        rows = []
        for m in (cae00, dev):
            got, skipped, errors = sync.plan(one, {"map": m, "areas": {}, "area_meta": [], "apps": [{"app": app, "label": app}]})
            assert not errors and not skipped, (key, errors, skipped)
            rows.append(got[0]["response_config"]["key_tools"])
        assert rows[0] == rows[1] == p["key_tools"], key


def _cluster_tool(name: str) -> bool:
    """smart-twin-cluster(:5012, KooSlurmInstallAutomationRefactory dashboard/mcp_slurm)가 내는 도구 — slurm_* 와
    smarttwin_submit·smarttwin_scenario_options 다(dev 게이트웨이 감사 로그 backend=smart-twin-cluster). SmartTwinMCP(:5013)
    카탈로그에는 smarttwin_* 가 없다 — slurm_ 접두로만 나누면 cae00 에서 이 둘이 '이 앱에 없는 도구' 로 동기화를 멈춘다."""
    return name.startswith(("slurm_", "smarttwin_"))


def _smarttwin_maps() -> tuple[dict, dict]:
    """he-sim-smarttwin 이 적은 이름으로 만든 게이트웨이 둘 — smart-twin-mcp 만 붙은 박스(cae00)와 둘 다 붙은 박스(dev)."""
    p = _one("he-sim-smarttwin")["personas"][0]
    names = {n for src in [p, *(p.get("optional") or [])] for fld in _TOOL_FIELDS for n in src.get(fld) or []}
    mcp = {_native(n, ["smart-twin-mcp"]): "smart-twin-mcp" for n in names if not _cluster_tool(n)}
    cluster = {n: "smart-twin-cluster" for n in names if _cluster_tool(n)}
    base = {"areas": {}, "area_meta": [], "apps": [{"app": "smart-twin-mcp", "label": "시뮬레이션 실행(SmartTwin)"},
                                                   {"app": "smart-twin-cluster", "label": "시뮬레이션 클러스터"}]}
    return {**base, "map": mcp}, {**base, "map": {**mcp, **cluster}}


def test_선택_앱이_빠진_박스에서도_운영자를_만든다():
    """cae00 에는 smart-twin-cluster 가 없다 — 앱 둘을 다 필수로 적으면 SmartTwinMCP 가 붙어도 이 운영자는 늘 건너뛰어졌다(K8-2)."""
    sync = _sync()
    one = _one("he-sim-smarttwin")
    mcp_only, both = _smarttwin_maps()
    rows, skipped, errors = sync.plan(one, mcp_only)
    assert not errors and not skipped, (errors, skipped)
    notes: list[str] = []
    rows, skipped, errors = sync.plan(one, mcp_only, notes)
    assert not errors and not skipped and len(rows) == 1
    assert notes == ["he-sim-smarttwin: smart-twin-cluster 없이 만든다(선택 앱)"], "빼고 만든 것을 건너뜀으로 세거나 말없이 넘기면 안 된다"
    r = rows[0]
    assert r["response_config"]["mcp_apps"] == ["smart-twin-mcp"], "없는 앱을 묶으면 챗이 '연결 안 됨' 경고를 낸다"
    # 없는 앱의 도구를 프롬프트가 대면 모델이 그 도구를 부른다
    for name in ("slurm_", "smarttwin_submit", "smarttwin_scenario_options"):
        assert name not in r["system_prompt"], name
    assert not any(_cluster_tool(t) for t in r["response_config"]["key_tools"])


def test_선택_앱이_붙은_박스에서는_지금과_같게_만든다():
    sync = _sync()
    one = _one("he-sim-smarttwin")
    p = one["personas"][0]
    assert p["apps"] == ["smart-twin-mcp"] and [o["app"] for o in p.get("optional") or []] == ["smart-twin-cluster"], (
        "클러스터는 선택 앱이다 — 필수 apps 에 두면 붙지 않은 박스에서 운영자 전체가 건너뛰어진다")
    _mcp_only, both = _smarttwin_maps()
    notes: list[str] = []
    rows, skipped, errors = sync.plan(one, both, notes)
    assert not errors and not skipped and notes == [], (errors, skipped, notes)
    assert one == _one("he-sim-smarttwin"), "plan() 이 정본을 제자리에서 고쳤다 — 두 번 부르면 선택 앱 칸이 두 번 붙는다"
    rc = rows[0]["response_config"]
    assert rc["mcp_apps"] == ["smart-twin-mcp", "smart-twin-cluster"]
    # 둘 다 붙은 박스(dev)는 옮기기 전과 같은 도구를 입구로 묶는다(선택 앱 몫이 뒤로 가 순서만 바뀐다)
    assert sorted(rc["key_tools"]) == sorted(["smarttwin_scenario_options", "smarttwin_submit", "list_recent_jobs",
                                              "smarttwinmcp_job_status", "get_job_details", "job_diagnose",
                                              "slurm_list_jobs", "slurm_job_results", "slurm_job_log"])
    assert "slurm_job_control" in rows[0]["system_prompt"], "선택 앱의 confirm 도 상태를 바꾸는 도구 줄에 실린다"
    # 선택 앱 몫의 이름도 붙은 박스에서는 대조한다 — 오타를 그대로 올리면 모델이 없는 도구를 부른다
    bad = json.loads(json.dumps(one))
    bad["personas"][0]["optional"][0]["key_tools"].append("slurm_job_logg")
    _rows, _skipped, errors = sync.plan(bad, both)
    assert errors and "slurm_job_logg" in errors[0]


def test_미리보기가_선택_앱을_빼고_만든_운영자를_알린다(monkeypatch, capsys):
    sync = _sync()
    mcp_only, _both = _smarttwin_maps()

    def fake_http(method, url, body=None):
        if url.endswith("/tools-map"):
            return 200, mcp_only
        if url.endswith("/api/agents"):
            return 200, []
        return 404, "not found"      # 아직 없는 운영자 — 미리보기는 + 줄만 찍고 쓰지 않는다

    monkeypatch.setattr(sync, "_http", fake_http)
    monkeypatch.setattr(sync.sys, "argv", ["sync-he-personas.py"])
    assert sync.main() == 0
    out = capsys.readouterr().out
    assert "· 일부 he-sim-smarttwin: smart-twin-cluster 없이 만든다(선택 앱)" in out
    assert "+ he-sim-smarttwin 새로 만든다" in out and "건너뜀 he-sim-smarttwin" not in out


def test_본문의_올리기_도구도_부를_수_있는_이름으로_적는다():
    """맨 이름 upload_from_url·upload_file 은 simflow 가 붙은 박스에서 없는 도구다 — 본문이 그 이름을 대면 모델이 그대로 부른다."""
    p = _one("he-doc-reportarchive")["personas"][0]
    text = " ".join([p["mission"], *p["can"], *p["workflow"], *p["concepts"], *p["pitfalls"]])
    bare = re.findall(r"(?<![a-z_])upload_(?:from_url|file)\b", text)
    assert not bare, bare


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



def test_클러스터의_제출_도구를_조회_전용이라_하지_않는다():
    """smart-twin-cluster 의 smarttwin_submit·slurm_submit_job 은 잡을 실제로 제출한다 — '그 앱 도구는 조회 전용' 이라 쓰면 모델이
    확인 없이 부른다. 허브 규칙(잡 제출은 무엇을 어디에 돌릴지 사용자가 확인한 뒤)을 그 두 도구에 적는다."""
    p = _one("he-sim-smarttwin")["personas"][0]
    cluster = next(o for o in p.get("optional") or [] if o["app"] == "smart-twin-cluster")
    text = " ".join(s for src in (p, cluster) for f in ("can", "workflow", "concepts", "pitfalls") for s in src.get(f) or [])
    assert "smart-twin-cluster 도구는 조회 전용" not in text
    line = next((s for s in cluster["concepts"] if "smarttwin_submit" in s and "slurm_submit_job" in s), None)
    assert line is not None and "확인한 뒤에만" in line, line


def test_DocForge_운영자는_RA_를_선택_앱으로_묶고_변환은_업로드로_안내한다():
    """정밀 변환은 포털 업로드가 맡기고(호스트 경로) · 사람 명의로 RA 에 넣는다 — 운영자는 그 길을 안내하고 진행 · 변환 보고서를 풀어 준다.
    만든 보고서를 읽는 RA 도구는 선택 앱(RA 가 없는 박스에서도 운영자는 생긴다). DocForge 가 게이트웨이에 없으면(draft) 건너뛴다."""
    sync = _sync()
    one = _one("he-doc-docforge")
    df = {"docforge_capabilities", "docforge_convert", "docforge_status", "docforge_package", "docforge_cancel"}
    ra = {"get_report_outline", "get_report", "search_reports"}
    base = {"areas": {}, "area_meta": [], "apps": [{"app": "heax-doc_forge", "label": "DocForge"},
                                                   {"app": "reportarchive", "label": "Report Archive"}]}
    rows, skipped, errors = sync.plan(one, {**base, "map": {**dict.fromkeys(df, "heax-doc_forge"), **dict.fromkeys(ra, "reportarchive")}})
    assert not errors and not skipped, errors
    (r,) = rows
    assert r["response_config"]["mcp_apps"] == ["heax-doc_forge", "reportarchive"]
    prompt = r["system_prompt"]
    assert "「Report Archive — 정밀 변환」" in prompt and "'모델 판독'" in prompt and len(prompt) <= sync.PROMPT_MAX
    writes = prompt.split("## 상태를 바꾸는 도구", 1)[1]
    assert "docforge_convert" in writes and "docforge_cancel" in writes.split("되돌리기 어렵다", 1)[1], "취소는 확인받고 부른다"
    notes: list[str] = []
    rows, skipped, errors = sync.plan(one, {**base, "map": dict.fromkeys(df, "heax-doc_forge")}, notes)
    assert not errors and not skipped and notes == ["he-doc-docforge: reportarchive 없이 만든다(선택 앱)"]
    assert "get_report_outline" not in rows[0]["system_prompt"], "없는 앱의 도구를 대면 모델이 그 도구를 부른다"
    rows, skipped, _errors = sync.plan(one, {**base, "map": dict.fromkeys(ra, "reportarchive")})
    assert rows == [] and skipped, "DocForge 가 게이트웨이에 실리기 전(draft)에는 만들지 않는다"


# ── 같은 앱 안의 켜고 끄는 기능 — needs_tool(10-28, docs/request-1027 HP-35 미리보기에서 드러났다) ──────────────────
# MX 백서는 위키가 꺼진 박스에서 wiki_* 를 내지 않고(MXWhitePaper MW-01), 서버 경로를 읽는 도구(import_file · upload_image ·
# extract_pptx_images)는 http 모드에서 아예 싣지 않는다(MW-02). 정본 필수 칸에 그 이름이 있으면 그 박스에서 동기화가 통째로 멈췄다.
def _mxwp_map(with_wiki: bool) -> dict:
    p = _one("he-doc-mxwhitepaper")["personas"][0]
    base = {n for fld in _TOOL_FIELDS for n in p[fld]}
    wiki = {n for o in p.get("optional") or [] for fld in _TOOL_FIELDS for n in o.get(fld) or []}
    names = base | (wiki if with_wiki else set())
    return {"map": dict.fromkeys(names, "mx-white-paper"), "areas": {}, "area_meta": [],
            "apps": [{"app": "mx-white-paper", "label": "MX 백서"}]}


def test_MX_백서_운영자는_위키가_켜진_박스에서_위키부터_묻는다():
    sync = _sync()
    one = _one("he-doc-mxwhitepaper")
    p = one["personas"][0]
    assert [o.get("needs_tool") for o in p.get("optional") or []] == ["wiki_ask"], "위키 몫은 needs_tool 로 묶는다"
    notes: list[str] = []
    rows, skipped, errors = sync.plan(one, _mxwp_map(True), notes)
    assert not errors and not skipped and notes == [], (errors, skipped, notes)
    (r,) = rows
    assert r["response_config"]["mcp_apps"] == ["mx-white-paper"], "같은 앱을 두 번 묶었다 — 도구 수 · 라벨이 두 번 센다"
    assert r["common_tags"].count("MX 백서") == 1
    assert {"wiki_ask", "wiki_read"} <= set(r["response_config"]["key_tools"]) and "wiki_fileback" in r["system_prompt"]
    assert f"도구 {len(_mxwp_map(True)['map'])}개" in r["system_prompt"], "도구 수를 두 번 셌다"


def test_MX_백서_운영자는_위키가_꺼진_박스에서도_멈추지_않고_위키를_대지_않는다():
    sync = _sync()
    one = _one("he-doc-mxwhitepaper")
    notes: list[str] = []
    rows, skipped, errors = sync.plan(one, _mxwp_map(False), notes)
    assert not errors and not skipped, (errors, skipped)
    assert notes == ["he-doc-mxwhitepaper: mx-white-paper 의 wiki_ask 없이 만든다(선택 앱)"]
    (r,) = rows
    assert "wiki_" not in r["system_prompt"] and not any(t.startswith("wiki_") for t in r["response_config"]["key_tools"])
    p = one["personas"][0]
    text = " ".join([*p["can"], *p["workflow"], *p["pitfalls"], *p["writes"], *p["key_tools"]])
    for gone in ("import_file", "upload_image,", "extract_pptx_images"):
        assert gone not in text and "upload_image" not in p["writes"], f"http 모드에서 실리지 않는 도구를 댄다 — {gone}"


def _onto_map(hubs: tuple[str, ...]) -> dict:
    """cae00 꼴 — 허브 셋이 같은 도구 이름을 내놓아 게이트웨이가 모두 접두로 낸다(HWAXAgentServer _ONTO_CORE 의 노출 이름)."""
    core = {"rootdesigndatahub": ("object_resolve", "objects_resolve_many", "objects_list", "objects_summary", "object_get",
                                  "object_fields", "graph_neighbors", "search",
                                  # 쓰기 · 잡(10-30 cae00 /tools-map — docs/request-1030 HP-53)
                                  "object_create", "object_update", "objects_delete", "object_merge", "datasource_sync",
                                  "bundle_import", "job_apply"),
            "failuretrace": ("object_resolve", "objects_list", "objects_summary", "graph_neighbors"),
            "caegroupdatahub": ("object_resolve", "objects_list", "objects_summary")}
    return {"map": {f"{h}_{t}": h for h in hubs for t in core[h]}, "areas": {}, "area_meta": [],
            "apps": [{"app": h, "label": h} for h in hubs]}


def test_HP20_코어_온톨로지_운영자는_정본_허브를_몰고_붙은_허브만_잇는다():
    """운영자 key_tools 가 먼저 묶이는 길을 코어 질문에 쓴다(docs/request-1027 HP-20). 이름은 허브끼리 겹쳐 접두로만 있다(HP-19 와 같은 까닭)."""
    sync = _sync()
    one = _one("he-data-coreontology")
    notes: list[str] = []
    (r,), skipped, errors = sync.plan(one, _onto_map(("rootdesigndatahub", "failuretrace", "caegroupdatahub")), notes)
    assert not errors and not skipped and not notes, (errors, skipped, notes)
    assert r["response_config"]["mcp_apps"] == ["rootdesigndatahub", "failuretrace", "caegroupdatahub"]
    assert r["response_config"]["key_tools"][:5] == ["rootdesigndatahub_object_resolve", "rootdesigndatahub_objects_list",
                                                    "rootdesigndatahub_objects_summary", "rootdesigndatahub_graph_neighbors",
                                                    "rootdesigndatahub_object_get"]
    assert len(r["response_config"]["key_tools"]) <= 12, "에이전트 서버가 12개까지만 싣는다(_persona_meta)"
    prompt = r["system_prompt"]
    assert len(prompt) <= sync.PROMPT_MAX and "candidates" in prompt and "조회하지 못했다" in prompt
    (r,), skipped, errors = sync.plan(one, _onto_map(("rootdesigndatahub",)), notes)
    assert not errors and r["response_config"]["mcp_apps"] == ["rootdesigndatahub"], "다른 허브가 없는 박스에서도 만든다"
    assert any("failuretrace" in n and "caegroupdatahub" in n for n in notes), notes
    _rows, skipped, errors = sync.plan(one, _onto_map(("failuretrace",)))
    assert not errors and skipped, "정본 허브가 없으면 건너뛴다(dev)"


# ── HP-53(docs/request-1030) — 운영자 정의의 writes · confirm 을 채운다 ─────────────────────────────────────────────
# 10-30 cae00 /tools-map 과 대조한 목록 밖 도구다. 잡 · 쓰기는 writes(요청했을 때만 부른다), 지우기 · 권한 · 되돌리기 어려운 것은
# confirm(무엇이 바뀌는지 말하고 확인 뒤). 지금은 프롬프트의 두 줄이 되고, 에이전트서버의 확인 관문(HA-29)이 들어가면 그 관문도 이 두
# 목록을 읽는다 — 빠지면 안내도 관문도 그 도구를 비켜 간다(DW-03 은 확인 없이 잡을 걸었다).
_HP53 = {
    "he-cad-odbhub": ({"run_checklist", "run_analysis", "run_compare", "run_curvature", "create_modified_odb",
                       "import_modified_odb"}, set()),
    "he-data-arp": ({"arp_upload_create", "arp_upload_stage"}, {"arp_upload_register", "arp_upload_discard"}),
    "he-data-coreontology": ({"rootdesigndatahub_object_create", "rootdesigndatahub_object_update"},
                             {"rootdesigndatahub_objects_delete", "rootdesigndatahub_object_merge",
                              "rootdesigndatahub_datasource_sync", "rootdesigndatahub_bundle_import",
                              "rootdesigndatahub_job_apply"}),
    "he-expert-risk": ({"risk_start_job", "risk_create_project", "risk_create_diff"}, {"risk_job_action"}),
    # save_recipe 는 10-31 StepForge 세션의 분류(되돌리기 어려운 여덟)로 confirm 에 옮겼다 — 아래 HA-29 StepForge 시험
    "he-cad-stepforge": ({"run_recipe", "set_revision"}, {"set_admin", "save_recipe"}),
    "he-sim-dynaforge": ({"recipe_propose", "heaxkooremapper_mcp_recipe_run"}, {"recipe_register"}),
}


def test_HP53_잡_쓰기_도구가_writes_confirm_에_있다():
    by_key = {p["key"]: p for p in _load()["personas"]}
    for key, (writes, confirm) in _HP53.items():
        p = by_key[key]
        assert writes <= set(p["writes"]), (key, sorted(writes - set(p["writes"])))
        assert confirm <= set(p["confirm"]), (key, sorted(confirm - set(p["confirm"])))
    # recipe_run 은 smart-twin-mcp 와 이름이 겹친다(dev /tools-map 이 양쪽 다 접두로 낸다) — 맨 이름은 그 박스에서 없는 도구다
    assert "recipe_run" not in by_key["he-sim-dynaforge"]["writes"]
    # 코어 허브 도구는 허브 셋이 같은 이름을 낸다 — 정본 허브 접두로 적는다(key_tools 와 같은 까닭)
    assert not [n for fld in _TOOL_FIELDS for n in by_key["he-data-coreontology"][fld] if not n.startswith("rootdesigndatahub_")]
    # ODB 운영자는 둔다(10-31 OB-26 사용자 결정) — 입구 도구는 cae00 에서만 보이는 이름이라 필수 칸은 비우고 선택 칸(needs_tool)에 둔다(아래 OB-26 시험)
    assert by_key["he-cad-odbhub"]["key_tools"] == [] and by_key["he-cad-odbhub"].get("todo")


def test_HP53_ARP_운영자는_낙하_높이를_cm_로_읽는다():
    """ARP 의 낙하 높이 칸에는 단위가 없어 챗이 152 를 mm 로 읽었다(DW-06 · OT-08). ARP 가 단위를 싣기(AR-9) 전까지 함정 줄로 메운다."""
    one = _one("he-data-arp")
    p = one["personas"][0]
    line = next((s for s in p["pitfalls"] if s.startswith("낙하 높이 칸은 단위가 없다 — 시험 조건은 cm")), None)
    assert line is not None, p["pitfalls"]
    rows, skipped, errors = _sync().plan(one, FAKE_MAP)
    assert not errors and not skipped, (errors, skipped)
    assert rows[0]["response_config"]["key_tools"] == ["arp_search_data", "arp_compare_items"], "조회 도구가 있는 박스에서는 입구 도구로 잇는다"
    prompt = rows[0]["system_prompt"]
    assert line in prompt
    assert "arp_upload_register 로 등록한다" in prompt.split("## 기본 작업 순서", 1)[0], "할 수 있는 일에 올리기도 적는다 — 조회만 하는 운영자로 읽혔다"
    state = prompt.split("## 상태를 바꾸는 도구", 1)[1]
    assert "arp_upload_create" in state.split("되돌리기 어렵다", 1)[0], "올리기 준비는 요청했을 때만"
    assert "arp_upload_register" in state.split("되돌리기 어렵다", 1)[1], "등록은 공유 저장소로 나간다 — 확인 뒤"


def test_HP53_ARP_조회_도구_이름이_다른_박스에서도_동기화가_멈추지_않는다():
    """조회 둘(search_data · compare_items)은 10-29 QA 가 적은 이름이라 cae00 /tools-map 으로 맞춰 보지 못했다. 필수 칸(key_tools)에 두면
    이름 하나만 틀려도 그 박스 동기화가 운영자 전부를 멈춘다(context-notes C-8 과 같은 까닭) — 그 도구가 있을 때만 잇고 없으면 '· 일부' 로."""
    sync = _sync()
    one = _one("he-data-arp")
    up = {"arp_upload_create", "arp_upload_stage", "arp_upload_register", "arp_upload_discard"}
    both = ["arp_search_data", "arp_compare_items"]
    for reads, want in (({"search_data", "compare_items"}, both),
                        ({"arp_search_data", "arp_compare_items"}, both),   # 앱이 접두를 붙여 낸다
                        ({"arp_search", "arp_compare"}, [])):               # 이름이 다르다
        notes: list[str] = []
        tm = {"map": dict.fromkeys(up | reads, "arp"), "areas": {}, "area_meta": [], "apps": [{"app": "arp", "label": "ARP"}]}
        rows, skipped, errors = sync.plan(one, tm, notes)
        assert not errors and not skipped and len(rows) == 1, (reads, errors, skipped)
        assert rows[0]["response_config"]["key_tools"] == want, reads
        assert rows[0]["response_config"]["mcp_apps"] == ["arp"], "같은 앱을 두 번 싣지 않는다(도구 수 · 라벨이 두 번 센다)"
        assert notes == ([] if want else ["he-data-arp: arp 의 search_data, arp 의 compare_items 없이 만든다(선택 앱)"]), notes


def test_HP53_채운_이름은_cae00_꼴_게이트웨이에서_멈추지_않는다():
    """dev 에는 odb-hub · arp · 코어 허브가 없다. 오류가 하나라도 있으면 cae00 동기화는 아무도 안 올린다 — 정본 이름이 cae00 꼴 표에서
    통과하는지 본다. 접두로 적은 운영자(ARP · 코어)는 원래 이름으로 낸 표와 접두로 낸 표(겹치는 상대가 붙은 박스) 둘 다 통과해야 한다."""
    sync = _sync()
    for key in ("he-cad-odbhub", "he-data-arp", "he-data-coreontology"):
        one = _one(key)
        p = one["personas"][0]
        app = p["apps"][0]
        pre = app.replace("-", "") + "_"
        names = {n for fld in _TOOL_FIELDS for n in p[fld]}
        maps = [{_native(n, p["apps"]): app for n in names}]
        if all(n.startswith(pre) for n in names):
            maps.append({pre + _native(n, p["apps"]): app for n in names})
        for m in maps:
            rows, skipped, errors = sync.plan(one, {"map": m, "areas": {}, "area_meta": [], "apps": [{"app": app, "label": app}]})
            assert not errors and not skipped and len(rows) == 1, (key, errors, skipped)
            assert len(rows[0]["system_prompt"]) <= sync.PROMPT_MAX


# ── OB-26(10-31 사용자 결정 — ODB 허브 운영자를 둔다) ────────────────────────────────────────────────────────────────────────
# 입구 도구 이름은 cae00 에서만 볼 수 있다(dev 게이트웨이에 odb-hub 가 없다). 필수 칸(key_tools)의 이름 하나가 그 박스 게이트웨이에 없으면 동기화가
# 운영자 전부를 멈추므로(K8-1 · C-8 과 같은 까닭) 선택 칸(needs_tool)에 하나씩 둔다 — 있을 때만 잇고 없으면 '· 일부' 로 알린다. 이름은 접두 별칭
# (odbhub_<이름>)이다. needs_tool 은 맨 이름 노출과 접두 노출을 둘 다 받으므로, 맨 이름을 적으면 접두로만 나온 박스(다른 앱과 겹치는 박스 —
# list_jobs 는 cae00 에서 이미 odbhub_list_jobs 다, 10-29 QA OT-11)에서 '이 앱에 없는 도구' 로 멈춘다.
def _odb_map(reads: tuple[str, ...], *, prefixed: bool = False) -> dict:
    p = _one("he-cad-odbhub")["personas"][0]
    names = set(p["writes"]) | {f"odbhub_{n}" if prefixed else n for n in reads}
    return {"map": dict.fromkeys(names, "odb-hub"), "areas": {}, "area_meta": [],
            "apps": [{"app": "odb-hub", "label": "ECAD Automation Hub"}]}


def test_OB26_ODB_운영자는_입구_도구를_게이트웨이에_있을_때만_잇는다():
    sync = _sync()
    one = _one("he-cad-odbhub")
    opt = one["personas"][0].get("optional") or []
    needs = tuple(o.get("needs_tool") for o in opt)
    assert {o["app"] for o in opt} == {"odb-hub"} and all(needs), "같은 앱 안의 도구 — needs_tool 로 하나씩 묶는다(이름 하나가 틀려도 나머지는 잇는다)"
    assert "get_task" in needs, "DW-02(10-30) — run_checklist 를 건 뒤 get_task 로 끝을 본다"
    assert [o["key_tools"] for o in opt] == [[f"odbhub_{n}"] for n in needs], "입구 도구는 접두 별칭으로 적는다"
    assert not any(o.get(f) for o in opt for f in ("writes", "confirm")), "쓰기 · 확인 목록은 필수 칸 그대로다(HP-53)"
    every = [f"odbhub_{n}" for n in needs]
    for reads, prefixed, want in ((needs, False, every),                   # cae00 꼴 — 맨 이름으로 나온다
                                  (needs, True, every),                    # 다른 앱과 겹쳐 접두로만 나온다
                                  (("get_task",), False, ["odbhub_get_task"]),
                                  ((), False, [])):                        # 이름이 다 다르다 — 그래도 운영자는 만든다
        notes: list[str] = []
        rows, skipped, errors = sync.plan(one, _odb_map(reads, prefixed=prefixed), notes)
        assert not errors and not skipped and len(rows) == 1, (reads, prefixed, errors, skipped)
        rc = rows[0]["response_config"]
        assert rc["key_tools"] == want and rc["mcp_apps"] == ["odb-hub"], (reads, prefixed, rc)
        gone = [f"odb-hub 의 {n}" for n in needs if n not in reads]
        assert notes == ([f"he-cad-odbhub: {', '.join(gone)} 없이 만든다(선택 앱)"] if gone else []), notes
    # 맨 이름으로 적은 사본은 접두로만 나온 박스에서 멈춘다 — 그래서 별칭이다
    bare = json.loads(json.dumps(one))
    for o in bare["personas"][0]["optional"]:
        o["key_tools"] = [o["needs_tool"]]
    _rows, _skipped, errors = sync.plan(bare, _odb_map(needs, prefixed=True))
    assert errors and "key_tools" in errors[0], errors


def _write_map(persona_key: str, extra_write: set[str], read_ok: set[str], exposed: dict[str, str] | None = None) -> dict:
    """그 운영자가 적은 이름(원래 이름으로 낸 꼴) + 더한 도구 — write 칸에는 정본의 writes · confirm 과 extra_write 를 싣는다."""
    p = _one(persona_key)["personas"][0]
    app = p["apps"][0]
    names = {_native(n, p["apps"]) for fld in _TOOL_FIELDS for n in p[fld]} | extra_write | read_ok
    m = {**dict.fromkeys(names, app), **(exposed or {})}
    listed = {_native(n, p["apps"]) for n in [*p["writes"], *p["confirm"]]} | extra_write | read_ok
    return {"map": m, "areas": {}, "area_meta": [], "apps": [{"app": app, "label": app}],
            "write": sorted(n for n in m if _native(n, p["apps"]) in listed), "routine_read": sorted(read_ok)}


def test_HP53_미리보기는_목록_밖_쓰기_도구를_알리고_막지_않는다():
    sync = _sync()
    one = _one("he-calc-thermalshock")
    warns: list[str] = []
    # recompute_cache — 쓰기 꼴인데 두 목록 어디에도 없다 · get_record_view — 이름은 쓰기 꼴(record)이지만 읽기로 확인된 것
    rows, skipped, errors = sync.plan(one, _write_map("he-calc-thermalshock", {"recompute_cache"}, {"get_record_view"}), None, warns)
    assert rows and not errors and not skipped, "알리기만 한다 — 오류로 세면 동기화가 통째로 멈춘다"
    assert warns == ["목록 밖 쓰기 he-calc-thermalshock: 1개 — recompute_cache(writes · confirm 어디에도 없다 — 맞는 쪽에 넣는다)"], warns
    # 다 적혀 있으면 조용하다 · warns 를 안 주면(옛 호출) 지금과 같다
    warns = []
    sync.plan(one, _write_map("he-calc-thermalshock", set(), set()), None, warns)
    assert warns == []
    assert sync.plan(one, _write_map("he-calc-thermalshock", {"recompute_cache"}, set()))[2] == []


def test_HP53_목록_밖_쓰기는_접두_별칭으로_적은_이름도_적힌_것으로_센다():
    """정본은 겹치는 도구를 접두 별칭(heaxkooremapper_mcp_recipe_run)으로 적는다 — 겹치는 상대가 없는 박스는 맨 이름(recipe_run)으로 낸다.
    노출 이름과만 견주면 적어 둔 도구를 '목록 밖' 이라 거짓으로 알린다."""
    sync = _sync()
    one = _one("he-sim-dynaforge")
    warns: list[str] = []
    rows, _s, errors = sync.plan(one, _write_map("he-sim-dynaforge", set(), set()), None, warns)
    assert rows and not errors and warns == [], warns
    # 겹치는 박스(smart-twin-mcp 가 붙은 dev) — 양쪽 다 접두로 낸다
    tm = _write_map("he-sim-dynaforge", set(), set())
    tm["map"].pop("recipe_run")
    tm["map"]["heaxkooremapper_mcp_recipe_run"] = "heax-kooremapper_mcp"
    tm["write"] = sorted({*tm["write"], "heaxkooremapper_mcp_recipe_run"} - {"recipe_run"})
    warns = []
    rows, _s, errors = sync.plan(one, tm, None, warns)
    assert rows and not errors and warns == [], warns


def test_HP53_write_칸이_없는_옛_게이트웨이면_건너뛰었다고_한_줄_남긴다():
    sync = _sync()
    tm = _write_map("he-calc-thermalshock", {"recompute_cache"}, set())
    del tm["write"]
    warns: list[str] = []
    rows, _s, errors = sync.plan(_one("he-calc-thermalshock"), tm, None, warns)
    assert rows and not errors
    assert warns == ["목록 밖 쓰기 점검 건너뜀 — 이 게이트웨이 /tools-map 에 write 칸이 없다(옛 판)"], warns


def test_HP53_목록_밖_쓰기는_붙은_선택_앱의_도구까지_본다():
    """선택 앱(smart-twin-cluster)이 붙은 박스에서는 그 앱 도구도 이 운영자가 부른다 — 기본 앱만 보면 클러스터 쪽 쓰기를 놓친다."""
    _mcp_only, both = _smarttwin_maps()
    tm = {**both, "map": {**both["map"], "slurm_drain_node": "smart-twin-cluster"}, "write": ["slurm_drain_node"], "routine_read": []}
    warns: list[str] = []
    rows, skipped, errors = _sync().plan(_one("he-sim-smarttwin"), tm, None, warns)
    assert rows and not errors and not skipped, (errors, skipped)
    assert warns == ["목록 밖 쓰기 he-sim-smarttwin: 1개 — slurm_drain_node(writes · confirm 어디에도 없다 — 맞는 쪽에 넣는다)"], warns


def test_HP53_목록_밖_쓰기가_많으면_앞_여덟만_적고_나머지는_수로_말한다():
    sync = _sync()
    extra = {f"recompute_cache_{i:02d}" for i in range(11)}
    warns: list[str] = []
    sync.plan(_one("he-calc-thermalshock"), _write_map("he-calc-thermalshock", extra, set()), None, warns)
    n = sync.LOOSE_SHOW
    assert n < len(extra)
    shown = ", ".join(sorted(extra)[:n])
    assert warns == [f"목록 밖 쓰기 he-calc-thermalshock: 11개 — {shown} 외 {11 - n}개(writes · confirm 어디에도 없다 — 맞는 쪽에 넣는다)"], warns


# ── 미리보기 · 반영 본체(main) — 게이트웨이와 AIDataHub 를 흉내 낸다 ─────────────────────────────────────────────
class _FakeHub:
    """게이트웨이 /tools-map + AIDataHub /api/agents. save_status 가 5xx 이면 AD-21 꼴 — 저장(saves)은 하고 응답만 500 이다.
    row_status 를 주면 한 명씩 읽기(GET /api/agents/<key>)가 그 코드로 실패한다."""

    def __init__(self, tmap: dict, rows: dict | None = None, save_status: int = 200, saves: bool = True, list_status: int = 200,
                 row_status: int | None = None):
        self.tmap, self.rows = tmap, {k: dict(v) for k, v in (rows or {}).items()}
        self.save_status, self.saves, self.list_status, self.row_status = save_status, saves, list_status, row_status
        self.calls: list[tuple[str, str]] = []

    def __call__(self, method, url, body=None):
        path = url.split("/api/", 1)[1] if "/api/" in url else url.rsplit("/", 1)[1]
        self.calls.append((method, path))
        if path == "tools-map":
            return 200, self.tmap
        if path == "agents":
            if method == "POST":
                if self.saves:
                    self.rows[body["agent_type"]] = dict(body)
                return self.save_status, ("Internal Server Error" if self.save_status >= 300 else dict(body))
            return (self.list_status, list(self.rows.values())) if self.list_status == 200 else (self.list_status, "boom")
        key = path.split("/", 1)[1]
        if method == "PATCH":
            if self.saves:
                self.rows[key] = {**self.rows[key], **body}
            return self.save_status, ("Internal Server Error" if self.save_status >= 300 else self.rows[key])
        if self.row_status is not None:
            return self.row_status, "boom"
        return (200, dict(self.rows[key])) if key in self.rows else (404, "not found")


def _run_main(monkeypatch, capsys, hub: _FakeHub, *args: str) -> tuple[int, str, str]:
    sync = _sync()
    monkeypatch.setattr(sync, "_http", hub)
    monkeypatch.setattr(sync.sys, "argv", ["sync-he-personas.py", *args])
    rc = sync.main()
    cap = capsys.readouterr()
    return rc, cap.out, cap.err


def _op_row(key: str, apps: list[str]) -> dict:
    return {"agent_type": key, "name": key, "response_config": {"persona_kind": "mcp_operator", "mcp_apps": apps}}


def test_HP51_미리보기가_앱이_이_게이트웨이에_없는_운영자를_알린다(monkeypatch, capsys):
    """이 박스 AIDataHub 의 운영자(dev 덤프로 들어온 것)가 모는 앱이 이 게이트웨이에 없으면 조직도에서는 고를 수 있는데 챗을 보낸 뒤에야 주의가
    떴다(DW-12). 정본이 아니라 올라가 있는 행의 mcp_apps 를 본다 — 에이전트서버가 그 주의를 낼 때 보는 값이다."""
    mcp_only, _both = _smarttwin_maps()
    rows = {"he-sim-smarttwin": _op_row("he-sim-smarttwin", ["smart-twin-mcp", "smart-twin-cluster"]),   # dev 판 — 선택 앱까지
            "he-doc-reportarchive": _op_row("he-doc-reportarchive", ["reportarchive"]),
            "he-calc-old": _op_row("he-calc-old", ["smart-twin-mcp"]),                                     # 앱이 다 있다
            "he-calc-legacy": _op_row("he-calc-legacy", ["ghost-app"]),                                    # 정본에 없는 운영자
            "pcb-warpage": {"agent_type": "pcb-warpage", "name": "x", "response_config": {}}}               # 운영자가 아니다
    rc, out, err = _run_main(monkeypatch, capsys, _FakeHub(mcp_only, rows))
    assert rc == 0, err
    assert "  ! 운영자 앱이 이 게이트웨이에 없다 — he-doc-reportarchive: reportarchive · 챗에서 고르면 그 앱 도구 없이 답한다" in out, out
    assert ("  ! 운영자 앱이 이 게이트웨이에 없다 — he-sim-smarttwin: smart-twin-cluster · smart-twin-mcp 도구로만 답한다") in out, out
    # 사람이 만들었거나 정본에서 빠진 운영자도 조직도에서 고를 수 있다 — 정본 키만 보면 놓친다
    assert "  ! 운영자 앱이 이 게이트웨이에 없다 — he-calc-legacy: ghost-app · 챗에서 고르면 그 앱 도구 없이 답한다" in out, out
    gone = [ln for ln in out.splitlines() if ln.startswith("  ! ")]
    assert len(gone) == 3, gone
    assert "  ~ he-sim-smarttwin 고친다" in out, "어긋남(+ · ~)은 그대로 따로 찍는다 — --apply 하면 없는 선택 앱이 빠진다"


def test_HP51_AIDataHub_목록을_못_읽으면_건너뛰었다고_말한다(monkeypatch, capsys):
    mcp_only, _both = _smarttwin_maps()
    rc, out, _err = _run_main(monkeypatch, capsys, _FakeHub(mcp_only, list_status=500))
    assert rc == 0
    assert "  · AIDataHub 전문가 목록을 못 읽었다(500) — 정본에 없는 he-* · 운영자 앱 점검을 건너뛴다" in out, out


def _name_error_map() -> dict:
    """smart-twin-mcp 만 붙은 박스에서 he-sim-smarttwin 의 key_tools 하나(list_recent_jobs)가 없다 — 정본 이름 오류(계획 오류)."""
    mcp_only, _both = _smarttwin_maps()
    return {**mcp_only, "map": {k: v for k, v in mcp_only["map"].items() if k != "list_recent_jobs"}}


def test_HP51_정본_이름_오류로_멈춰도_운영자_앱_줄은_찍는다(monkeypatch, capsys):
    """이름 하나가 이 게이트웨이에 없으면 계획 오류로 멈춘다(rc 2). '!' 는 계획과 상관이 없다 — 같이 사라지면 update-all 에는 '미리보기를 못
    했다' 만 남고, 그 박스에서 운영자 앱이 없다는 것을 알 길이 다시 없어진다(종전 동작)."""
    rows = {"he-doc-reportarchive": _op_row("he-doc-reportarchive", ["reportarchive"])}
    rc, out, err = _run_main(monkeypatch, capsys, _FakeHub(_name_error_map(), rows))
    assert rc == 2 and "✗ he-sim-smarttwin: key_tools 에 이 앱에 없는 도구 — list_recent_jobs" in err, (out, err)
    assert "  ! 운영자 앱이 이 게이트웨이에 없다 — he-doc-reportarchive: reportarchive · 챗에서 고르면 그 앱 도구 없이 답한다" in out, out
    # --show 는 프롬프트 하나를 찍는 손 명령이다 — 알림을 섞지 않는다
    rc, out, _err = _run_main(monkeypatch, capsys, _FakeHub(_name_error_map(), rows), "--show", "he-sim-smarttwin")
    assert rc == 2 and "  ! " not in out, out


def test_HP51_행_조회가_실패해_멈춰도_운영자_앱_줄은_찍는다(monkeypatch, capsys):
    mcp_only, _both = _smarttwin_maps()
    rows = {"he-doc-reportarchive": _op_row("he-doc-reportarchive", ["reportarchive"])}
    rc, out, err = _run_main(monkeypatch, capsys, _FakeHub(mcp_only, rows, row_status=500))
    assert rc == 1 and "✗ he-sim-smarttwin 조회 실패 500" in err, (out, err)
    assert "  ! 운영자 앱이 이 게이트웨이에 없다 — he-doc-reportarchive: reportarchive" in out, out
    assert "미리보기(--apply 로 반영)" not in out, "멈춘 실행은 요약 줄을 찍지 않는다(종전과 같다)"


def test_HP51_HP53_check_는_알림_줄만_찍고_행마다_묻지_않는다(monkeypatch, capsys):
    """update-all §6 이 실행마다 부른다. 정본 이름 오류가 있어도 알림 줄은 다 찍고 0 으로 끝난다(점검은 했다 — 이름 오류 · 어긋남은 미리보기
    몫이다). 행마다 조회하지 않고 + · ~ 도 찍지 않는다."""
    tm = _name_error_map()
    tm = {**tm, "map": {**tm["map"], "purge_results": "smart-twin-mcp"}, "write": ["purge_results"], "routine_read": []}
    hub = _FakeHub(tm, {"he-doc-reportarchive": _op_row("he-doc-reportarchive", ["reportarchive"])})
    rc, out, err = _run_main(monkeypatch, capsys, hub, "--check")
    assert rc == 0 and err == "", (out, err)
    assert "  ! 운영자 앱이 이 게이트웨이에 없다 — he-doc-reportarchive: reportarchive" in out, out
    assert "  · 목록 밖 쓰기 he-sim-smarttwin: 1개 — purge_results(writes · confirm 어디에도 없다 — 맞는 쪽에 넣는다)" in out, out
    assert not [c for c in hub.calls if c[1].startswith("agents/")], hub.calls
    assert not [ln for ln in out.splitlines() if ln.startswith(("  + ", "  ~ "))], out


# ── AD-21(AIDataHub) — 저장은 됐는데 500 이면 다시 읽어 확인하고 이어 간다 ──────────────────────────────────────────
def test_AD21_만들기가_500_이어도_저장됐으면_이어_간다(monkeypatch, capsys):
    mcp_only, _both = _smarttwin_maps()
    hub = _FakeHub(mcp_only, save_status=500)
    rc, out, err = _run_main(monkeypatch, capsys, hub, "--apply")
    assert rc == 0, err
    assert "  ⚠ he-sim-smarttwin 생성 응답이 500 였지만 다시 읽으니 저장됐다 — 이어 간다(AIDataHub AD-21)" in out, out
    assert "반영 — 새로 1" in out
    assert hub.calls.count(("GET", "agents/he-sim-smarttwin")) == 2, "저장 뒤 다시 읽어 봐야 안다"


def test_AD21_고치기가_500_이어도_저장됐으면_이어_간다(monkeypatch, capsys):
    mcp_only, _both = _smarttwin_maps()
    old = {**_op_row("he-sim-smarttwin", ["smart-twin-mcp"]), "description": "옛 설명", "common_tags": [], "sample_queries": [],
           "system_prompt": "옛 역할"}
    rc, out, err = _run_main(monkeypatch, capsys, _FakeHub(mcp_only, {"he-sim-smarttwin": old}, save_status=500), "--apply")
    assert rc == 0, err
    assert "  ⚠ he-sim-smarttwin 수정 응답이 500 였지만 다시 읽으니 저장됐다 — 이어 간다(AIDataHub AD-21)" in out, out
    assert "반영 — 새로 0 · 고침 1" in out


def test_AD21_저장되지_않았으면_멈춘다(monkeypatch, capsys):
    mcp_only, _both = _smarttwin_maps()
    rc, out, err = _run_main(monkeypatch, capsys, _FakeHub(mcp_only, save_status=500, saves=False), "--apply")
    assert rc == 1 and "✗ he-sim-smarttwin 생성 실패 500" in err, (out, err)
    old = {**_op_row("he-sim-smarttwin", ["smart-twin-mcp"]), "description": "옛 설명"}
    rc, out, err = _run_main(monkeypatch, capsys, _FakeHub(mcp_only, {"he-sim-smarttwin": old}, save_status=500, saves=False), "--apply")
    assert rc == 1 and "✗ he-sim-smarttwin 수정 실패 500" in err, (out, err)
    assert "다시 읽으니 저장됐다" not in out


def test_AD21_거절은_다시_읽지_않고_멈춘다(monkeypatch, capsys):
    """4xx 는 저장 전에 거절한 것이다 — 다시 읽어 '저장됐다' 로 넘기면 안 된다."""
    mcp_only, _both = _smarttwin_maps()
    hub = _FakeHub(mcp_only, save_status=422)
    rc, _out, err = _run_main(monkeypatch, capsys, hub, "--apply")
    assert rc == 1 and "✗ he-sim-smarttwin 생성 실패 422" in err, err
    assert hub.calls.count(("GET", "agents/he-sim-smarttwin")) == 1


def test_AD21_다시_읽은_행이_보낸_칸과_모두_같고_200_일_때만_저장된_것으로_본다(monkeypatch):
    """칸 하나만 같아도 '저장됐다' 로 넘기면 반쯤 쓴 행 · 옛 행을 맞다고 하고 다음 운영자로 간다."""
    sync = _sync()
    want = {"name": "새 이름", "system_prompt": "새 역할", "response_config": {"persona_kind": "mcp_operator", "mcp_apps": ["a"]}}
    calls: list[str] = []

    def reads(st, cur):
        def fake(method, url, body=None):
            calls.append(method)
            return st, cur
        monkeypatch.setattr(sync, "_http", fake)

    reads(200, {**want, "id": 7})
    assert sync._saved_anyway(500, "he-x", want) is True
    reads(200, {**want, "system_prompt": "옛 역할"})
    assert sync._saved_anyway(500, "he-x", want) is False, "한 칸이라도 다르면 저장되지 않은 것이다"
    reads(202, dict(want))
    assert sync._saved_anyway(503, "he-x", want) is False, "다시 읽기도 200 이어야 한다"
    reads(404, "not found")
    assert sync._saved_anyway(500, "he-x", want) is False
    calls.clear()
    reads(200, dict(want))
    assert sync._saved_anyway(422, "he-x", want) is False and calls == [], "4xx 는 거절이다 — 다시 읽지 않는다"


# ── update-all §6 — HE팀 운영자 점검(HP-51 · HP-53)을 실행마다 ─────────────────────────────────────────────────────
# §3 의 미리보기(HP-35)는 새 덤프를 병합한 실행에만 돌고 갱신 전 게이트웨이를 본다 — 덤프가 그대로인 실행(대부분)은 '!' 를 못 봤고,
# '목록 밖 쓰기' 는 어느 실행에도 올라오지 않았다. 블록은 원문을 떼어 ok · bad 를 셸 함수로 갈아 돌린다(스크립트는 대역).
_UA = (_ROOT / "infra" / "scripts" / "update-all.sh").read_text(encoding="utf-8")
_GONE = "  ! 운영자 앱이 이 게이트웨이에 없다 — he-sim-smarttwin: smart-twin-mcp · 챗에서 고르면 그 앱 도구 없이 답한다\n"
_LOOSE = ("  · 목록 밖 쓰기 he-sim-dynaforge: 2개 — remove_task_alias, unlink_report_revision"
          "(writes · confirm 어디에도 없다 — 맞는 쪽에 넣는다)\n")


def _s6_block() -> str:
    i = _UA.index("# ── HE팀 운영자 점검 — 실행마다")
    return _UA[i:_UA.index("\nfi\n", i) + 4]


def _s6(tmp_path, out: str, rc: int = 0, tm_ok: int = 1) -> str:
    repo = tmp_path / "repo"
    (repo / "infra" / "scripts").mkdir(parents=True)
    (repo / "infra" / "scripts" / "sync-he-personas.py").write_text(
        "import sys, pathlib\n"
        f"pathlib.Path({str(tmp_path / 'called')!r}).write_text(' '.join(sys.argv[1:]))\n"
        f"sys.stdout.write({out!r})\nsys.exit({rc})\n", encoding="utf-8")
    script = "\n".join(["set -uo pipefail",                       # update-all 과 같은 셸 설정
                        'ok() { echo "OK:$*"; }', 'bad() { echo "BAD:$*"; }',
                        f"SELF_REPO='{repo}'", f"TM_OK={tm_ok}", _s6_block(), "echo END"])
    p = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=60,
                       env={"PATH": os.environ["PATH"], "HOME": str(tmp_path)})
    assert p.returncode == 0 and p.stdout.endswith("END\n"), p.stdout + p.stderr
    return p.stdout[:-len("END\n")]


def test_update_all_6_은_운영자_점검을_check_로_부르고_경고로_올린다(tmp_path):
    out = _s6(tmp_path, "  · 건너뜀 he-data-arp: 이 게이트웨이에 앱이 없다(arp)\n" + _GONE + _LOOSE)
    assert (tmp_path / "called").read_text() == "--check", "쓰지 않는 알림 모드다(--apply 아님 · 행마다 조회 없음)"
    assert "BAD:HE팀 운영자 1명의 앱이 이 게이트웨이에 없다 — 조직도에서 고르면 그 앱 도구 없이 답한다" in out, out
    assert "    ! 운영자 앱이 이 게이트웨이에 없다 — he-sim-smarttwin: smart-twin-mcp" in out, out
    assert "BAD:HE팀 운영자 1명의 앱에 writes · confirm 어디에도 없는 쓰기 도구가 있다" in out, out
    assert "    · 목록 밖 쓰기 he-sim-dynaforge: 2개 — remove_task_alias" in out, out
    assert "OK:" not in out and "건너뜀 he-data-arp" not in out, out


def test_update_all_6_은_다_맞으면_초록_한_줄이다(tmp_path):
    out = _s6(tmp_path, "  · 건너뜀 he-data-arp: 이 게이트웨이에 앱이 없다(arp)\n  ? 정본에 없는 he-* 에이전트 1명 — he-old (지우지 않았다)\n")
    assert out == "OK:HE팀 운영자 — 모는 앱이 다 이 게이트웨이에 있고 목록 밖 쓰기 도구 · 읽기를 막는 목록이 없다\n", out


def test_update_all_6_은_점검을_건너뛰었으면_초록이라_하지_않고_그_줄을_보인다(tmp_path):
    skipped = ("  · 목록 밖 쓰기 점검 건너뜀 — 이 게이트웨이 /tools-map 에 write 칸이 없다(옛 판)\n"
               "  · AIDataHub 전문가 목록을 못 읽었다(500) — 정본에 없는 he-* · 운영자 앱 점검을 건너뛴다\n")
    assert _s6(tmp_path, skipped) == skipped


def test_update_all_6_은_스크립트가_실패하면_못_했다고_말한다(tmp_path):
    out = _s6(tmp_path, "✗ 게이트웨이 /tools-map 을 못 읽었다(0) — http://127.0.0.1:9110\n", rc=2)
    assert out == "BAD:HE팀 운영자 점검을 하지 못했다(rc 2) — python3 infra/scripts/sync-he-personas.py --check 를 손으로 돌려 본다\n", out


def test_update_all_6_은_게이트웨이_지도를_못_읽었으면_부르지_않는다(tmp_path):
    assert _s6(tmp_path, _GONE, tm_ok=0) == "" and not (tmp_path / "called").exists()


def test_update_all_운영자_점검은_재기동_뒤_6_에서_올리고_3_은_어긋남만_본다():
    b = _s6_block()
    assert _UA.index('hr "5) 게이트웨이 config 정합') < _UA.index(b) < _UA.index('hr "6b) 등록 정합'), "재기동 · 재프로비저닝을 마친 게이트웨이로 본다"
    assert _UA.index("# ── 새 앱 점검 — 처음 본 앱을") < _UA.index(b) < _UA.index("SMOKE_PY="), "갱신한 지도를 읽은(TM_OK) 뒤 · 스모크 앞"
    s3 = _UA[_UA.index('hr "3) AIDataHub 데이터'):_UA.index('hr "2c) ste 코드 최신화')]
    assert 'sync-he-personas.py" 2>&1' in s3, "§3 은 merge 뒤 미리보기(HP-35)를 그대로 돈다"
    assert "'^  ! '" not in s3 and "목록 밖 쓰기" not in s3 and "읽기를 쓰기로" not in s3, \
        "§3 은 갱신 전 게이트웨이다 — 알림은 §6 한 곳에서만 올린다(두 번 찍지 않는다)"


# ── C-15(docs/request-1030 design-integration) — 확인 관문(HA-29)과 운영자 정의의 맞물림 ─────────────────────────────────────────
def test_C15_confirm_줄은_확인하는_길을_시스템_규칙에_맡긴다():
    """관문이 켜진 박스는 서버가 카드로 묻는다 — 운영자 글이 '먼저 말하고 확인을 받은 뒤' 를 박으면 사람에게 두 번 묻는다."""
    one = _one("he-expert-risk")
    rows, skipped, errors = _sync().plan(one, _write_map("he-expert-risk", set(), set()))
    assert rows and not errors and not skipped, (errors, skipped)
    state = rows[0]["system_prompt"].split("## 상태를 바꾸는 도구", 1)[1]
    assert "확인하는 길은 시스템 규칙을 따른다" in state and "risk_job_action" in state
    assert "먼저 말하고 확인을 받은 뒤 부른다" not in state
    # 이 글은 관문을 끈 박스 · MCP 직결(게이트웨이 use_experts 가 role_doc 으로 그대로 넘긴다)에도 간다 — 카드가 없는 곳의 갈래를 적고,
    # '확인을 받은 뒤에만 실행된다' 처럼 서버가 막아 준다고 약속하지 않는다(10-30 반대 검토)
    line = next(ln for ln in state.splitlines() if ln.startswith("- 되돌리기 어렵다"))
    assert "서버가 확인 카드를 띄운다는 규칙이 있으면 글로 따로 묻지 말고" in line, line
    assert "그런 규칙이 없으면 무엇이 바뀌는지 먼저 말해 사람의 확인을 받고 부른다" in line, line
    assert "실행된다" not in line, line


def test_C15_미리보기는_읽기로_확인된_도구를_쓰기_목록에_적으면_알린다():
    sync = _sync()
    one = _one("he-calc-thermalshock")
    p = one["personas"][0]
    listed = [*p["writes"], *p["confirm"]]
    assert listed, "시험 운영자는 쓰기 목록이 있어야 한다"
    victim = listed[0]
    tm = _write_map("he-calc-thermalshock", set(), set())
    tm["routine_read"] = sorted({*tm["routine_read"], _native(victim, p["apps"])})
    warns: list[str] = []
    rows, _s, errors = sync.plan(one, tm, None, warns)
    assert rows and not errors, "알리기만 한다"
    assert any(w.startswith("읽기를 쓰기로 he-calc-thermalshock: 1개 — ") and victim in w for w in warns), warns


def test_C15_거꾸로_점검은_관문처럼_다른_앱의_같은_꼬리_읽기_도구도_본다():
    """확인 관문은 모든 운영자의 목록을 모든 도구에 이름 그대로이거나 '_<이름>' 으로 끝나는 꼴로 건다(에이전트서버 _confirm_class — 접두 별칭은
    접두를 뗀 꼴도). 운영자 자기 앱의 도구만 보면 다른 앱의 같은 꼬리 읽기 도구가 카드에 걸리는 것을 놓친다(10-30 반대 검토)."""
    sync = _sync()
    one = _one("he-cad-stepforge")
    p = one["personas"][0]
    assert "set_admin" in p["confirm"] and "heaxstep_forge_cancel_job" in p["confirm"]
    tm = _write_map("he-cad-stepforge", set(), set())
    # ste_list_nodes — 같은 꼬리가 없는 읽기 도구는 걸리지 않는다
    tm["map"].update({"other_set_admin": "heax-other", "ste_cancel_job": "ste", "ste_list_nodes": "ste"})
    tm["apps"] = [*tm["apps"], {"app": "heax-other", "label": "다른 앱"}, {"app": "ste", "label": "ste"}]
    tm["routine_read"] = ["other_set_admin", "ste_cancel_job", "ste_list_nodes"]
    warns: list[str] = []
    rows, _s, errors = sync.plan(one, tm, None, warns)
    assert rows and not errors, errors
    assert warns == ["읽기를 쓰기로 he-cad-stepforge: 2개 — other_set_admin ← set_admin, ste_cancel_job ← heaxstep_forge_cancel_job"
                     "(게이트웨이가 읽기로 확인했다 — 확인 관문이 조회마다 카드를 세운다, 맞는지 본다)"], warns


def test_C15_거꾸로_점검은_앱이_없는_운영자의_목록도_본다():
    """관문은 정본 파일을 통째로 읽는다 — 이 게이트웨이에 앱이 없어 동기화가 건너뛰는 운영자(he-cad-odbhub)의 목록도 이 박스의 도구에 걸린다."""
    sync = _sync()
    one = _one("he-cad-odbhub")
    assert "run_checklist" in one["personas"][0]["writes"]
    tm = {"map": {"x_run_checklist": "heax-x"}, "areas": {}, "area_meta": [], "apps": [{"app": "heax-x", "label": "x"}],
          "write": [], "routine_read": ["x_run_checklist"]}
    warns: list[str] = []
    rows, skipped, _e = sync.plan(one, tm, None, warns)
    assert not rows and skipped, "앱이 없으니 동기화는 건너뛴다"
    assert any(w.startswith("읽기를 쓰기로 he-cad-odbhub: 1개 — x_run_checklist ← run_checklist") for w in warns), warns


def test_update_all_6_은_읽기를_막는_목록을_경고로_올린다(tmp_path):
    """거꾸로 점검 줄만 있는 박스에서 §6 이 '목록 밖 쓰기 도구가 없다' 초록을 찍었다 — §3 도 그 줄을 내지 않아 cae00 에서는 아무도 못 봤다."""
    line = ("  · 읽기를 쓰기로 he-expert-risk: 1개 — risk_get_registry(게이트웨이가 읽기로 확인했다 — 확인 관문이 조회마다 카드를 세운다,"
            " 맞는지 본다)\n")
    out = _s6(tmp_path, line)
    assert "OK:" not in out, out
    assert "BAD:HE팀 운영자 1명의 writes · confirm 이 게이트웨이가 읽기로 확인한 도구를 막는다" in out, out
    assert "    · 읽기를 쓰기로 he-expert-risk: 1개 — risk_get_registry" in out, out


# ── 10-30 반대 검토 — 운영자 목록이 관문에 빠뜨린 쓰기 ──────────────────────────────────────────────────────────────────────────
_RISK_MCP = _ROOT.parent / "HWAXRisk" / "backend" / "app" / "mcp_server.py"


def test_리스크_앱이_쓰기라고_적은_도구는_운영자_목록에_있다():
    """리스크 앱의 MCP 설명이 '쓰기: … 사용자에게 확인한 뒤 부른다' 로 적은 도구는 he-expert-risk 의 writes · confirm 어딘가에 있어야 한다 —
    없으면 확인 관문(HA-29)이 부류 없음으로 보아 사람이 시키지 않아도 카드 없이 나간다. 게이트웨이 쓰기 표지가 없는 것(캡처 · 대상 열기 ·
    다시 저장)은 '목록 밖 쓰기' 미리보기에도 안 걸린다(risk_job_action 과 같은 처지 — design-ha29 10절 10)."""
    if not _RISK_MCP.exists():
        pytest.skip(f"형제 리포 없음: {_RISK_MCP}")
    import ast
    tree = ast.parse(_RISK_MCP.read_text(encoding="utf-8"))
    writes = sorted(n.name for n in tree.body if isinstance(n, (ast.AsyncFunctionDef, ast.FunctionDef)) and n.name.startswith("risk_")
                    and "쓰기:" in (ast.get_docstring(n) or "").split("—", 1)[-1][:40])
    assert len(writes) >= 10, writes
    p = _one("he-expert-risk")["personas"][0]
    missing = [t for t in writes if t not in {*p["writes"], *p["confirm"]}]
    assert not missing, f"he-expert-risk 의 writes · confirm 에 없다 — {missing}"
    # 되돌리기 어려운 것은 confirm(늘 카드) — 소스는 지울 수 없고, 게이트 사유 · same-as 는 사람 판정이고, 다시 저장은 포기(discard)할 수 있다
    assert {"risk_add_source", "risk_ack_gate", "risk_decide_sameas", "risk_repersist_panel", "risk_job_action"} <= set(p["confirm"])


def test_StepForge_의_되돌릴_수_없는_치수_지우기는_confirm_에_있다():
    """forget_dimension 은 StepForge 가 '⚠ 되돌릴 수 없다' 로 적은 지우기다 — 목록 밖이면 확인 관문이 사람이 시키지 않아도 보낸다."""
    p = _one("he-cad-stepforge")["personas"][0]
    assert "forget_dimension" in p["confirm"] and "forget_dimension" not in p["writes"]


# ── HA-29(10-31) — StepForge 의 수정 도구 마흔하나를 StepForge 세션이 가른 대로 ────────────────────────────────────────────────────
# StepForge 는 readOnlyHint 를 달지 않고 카탈로그 범주(@register(mcp, MODIFY))로 수정 도구를 가른다. 확인 관문(HA-29)은 이름만 보므로 그 마흔하나가
# 모두 writes · confirm 에 있어야 한다 — 빠진 것은 사람이 시키지 않아도 카드 없이 나간다. 게이트웨이 쓰기 표지는 이름 낱말이라 export_step · shape_op ·
# align_image_to_geometry 처럼 '목록 밖 쓰기' 미리보기에도 안 걸리는 것이 있다. 되돌리기 어려운 여덟만 confirm(늘 카드)이고 나머지는 writes(이번 말로
# 시켰을 때만)다. 그래서 늘 카드였던 rename_part · remove_part · confirm_interfaces 는 시키면 나가고, upload_step · import_archive · save_recipe 는 늘 카드다.
_SF_MCP = _ROOT.parent / "StepForge" / "app" / "mcp_server.py"
_SF_CONFIRM = frozenset({"delete_project", "forget_dimension", "upload_step", "import_archive", "cancel_job", "set_admin",
                         "save_failure_mode", "save_recipe"})


def test_HA29_StepForge_는_되돌리기_어려운_여덟만_confirm_이다():
    p = _one("he-cad-stepforge")["personas"][0]
    confirm = {_native(n, p["apps"]) for n in p["confirm"]}
    writes = {_native(n, p["apps"]) for n in p["writes"]}
    assert confirm == _SF_CONFIRM, sorted(confirm ^ _SF_CONFIRM)
    assert not writes & confirm and len(writes) == len(p["writes"]) == 33, sorted(writes)
    assert {"rename_part", "remove_part", "confirm_interfaces", "mesh_size_advice", "shape_op", "record_dimension"} <= writes
    # 다른 앱과 겹치는 둘은 접두 별칭이다(dev /tools-map — ste · DynaForge 의 cancel_job, MaterialTwin 의 register_material)
    assert "heaxstep_forge_cancel_job" in p["confirm"] and "heaxstep_forge_register_material" in p["writes"]


def test_HA29_StepForge_가_MODIFY_로_등록한_도구는_모두_writes_confirm_에_있다():
    """StepForge 소스의 MODIFY 도구와 두 목록이 같은지 — 앱이 수정 도구를 더하면 목록에 넣고, 읽기로 바꾸면 목록에서 뺀다(읽기를 막으면 조회마다
    카드가 선다). 형제 리포가 없는 박스(cae00)에서는 건너뛴다."""
    if not _SF_MCP.exists():
        pytest.skip(f"형제 리포 없음: {_SF_MCP}")
    import ast
    tree = ast.parse(_SF_MCP.read_text(encoding="utf-8"))
    modify = {n.name for n in tree.body if isinstance(n, (ast.AsyncFunctionDef, ast.FunctionDef))
              for d in n.decorator_list
              if isinstance(d, ast.Call) and getattr(d.func, "id", None) == "register" and len(d.args) > 1
              and ast.unparse(d.args[1]) == "MODIFY"}
    assert len(modify) >= 41, sorted(modify)
    p = _one("he-cad-stepforge")["personas"][0]
    listed = {_native(n, p["apps"]) for n in [*p["writes"], *p["confirm"]]}
    assert not modify - listed, f"he-cad-stepforge 의 writes · confirm 에 없다 — {sorted(modify - listed)}"
    assert not listed - modify, f"StepForge 가 수정 도구로 등록하지 않았다 — {sorted(listed - modify)}"


def test_HA29_StepForge_인자로_덮어쓰는_도구는_함정_줄이_말한다():
    """관문은 이름만 본다 — overwrite=true · redefine=true · 같은 name 처럼 인자 하나로 덮어쓰는 호출도 그 도구의 부류(write)대로 사람이 시키면
    지나간다. 그래서 함정 줄이 그 인자는 사람이 바꾸라고 할 때만 쓰라고 말한다. 본문의 이름은 부를 수 있는 꼴이다(register_material 은 겹친다)."""
    one = _one("he-cad-stepforge")
    p = one["personas"][0]
    line = next((s for s in p["pitfalls"] if s.startswith("인자 하나로 덮어쓰는 도구가 있다")), None)
    assert line is not None, p["pitfalls"]
    for word in ("heaxstep_forge_register_material", "register_materials_csv", "overwrite=true", "record_dimension(redefine=true)",
                 "align_image_to_geometry", 'region="none"', "region_mask_transfer", "사람이 바꾸라고 하지 않았으면"):
        assert word in line, word
    assert not re.search(r"(?<![a-z_])register_material(?![a-z_])", line), "맨 이름 register_material 은 MaterialTwin 과 겹쳐 없는 도구다"
    advice = next((s for s in p["pitfalls"] if s.startswith("mesh_size_advice 는 store 기본이 true")), None)
    assert advice is not None and "store=false" in advice, p["pitfalls"]
    rows, skipped, errors = _sync().plan(one, _write_map("he-cad-stepforge", set(), set()))
    assert rows and not errors and not skipped, (errors, skipped)
    prompt = rows[0]["system_prompt"]
    assert line in prompt and advice in prompt and len(prompt) <= _sync().PROMPT_MAX
