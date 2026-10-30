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
        # ARP 운영자가 정본에 적은 도구(docs/request-1030 HP-53) — 조회 둘은 cae00 챗이 부른 이름, 올리기 넷은 10-30 cae00 /tools-map
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
# confirm(무엇이 바뀌는지 말하고 확인 뒤). 에이전트서버의 확인 관문(HA-29)이 이 두 목록을 읽는다 — 빠지면 확인 없이 불린다(DW-03).
_HP53 = {
    "he-cad-odbhub": ({"run_checklist", "run_analysis", "run_compare", "run_curvature", "create_modified_odb",
                       "import_modified_odb"}, set()),
    "he-data-arp": ({"arp_upload_create", "arp_upload_stage"}, {"arp_upload_register", "arp_upload_discard"}),
    "he-data-coreontology": ({"rootdesigndatahub_object_create", "rootdesigndatahub_object_update"},
                             {"rootdesigndatahub_objects_delete", "rootdesigndatahub_object_merge",
                              "rootdesigndatahub_datasource_sync", "rootdesigndatahub_bundle_import",
                              "rootdesigndatahub_job_apply"}),
    "he-expert-risk": ({"risk_start_job", "risk_create_project", "risk_create_diff"}, set()),
    "he-cad-stepforge": ({"run_recipe", "save_recipe", "set_revision"}, {"set_admin"}),
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
    # ODB 운영자의 할 일 · 입구 도구는 OB-26(운영자를 둘지) 뒤다 — 목록만 지금 채운다(docs/request-1030 context-notes C-5)
    assert by_key["he-cad-odbhub"]["key_tools"] == [] and by_key["he-cad-odbhub"].get("todo")


def test_HP53_ARP_운영자는_낙하_높이를_cm_로_읽는다():
    """ARP 의 낙하 높이 칸에는 단위가 없어 챗이 152 를 mm 로 읽었다(DW-06 · OT-08). ARP 가 단위를 싣기(AR-9) 전까지 함정 줄로 메운다."""
    one = _one("he-data-arp")
    p = one["personas"][0]
    line = next((s for s in p["pitfalls"] if s.startswith("낙하 높이 칸은 단위가 없다 — 시험 조건은 cm")), None)
    assert line is not None, p["pitfalls"]
    assert p["key_tools"], "ARP 운영자의 입구 도구가 비었다"
    rows, skipped, errors = _sync().plan(one, FAKE_MAP)
    assert not errors and not skipped, (errors, skipped)
    prompt = rows[0]["system_prompt"]
    assert line in prompt
    state = prompt.split("## 상태를 바꾸는 도구", 1)[1]
    assert "arp_upload_create" in state.split("되돌리기 어렵다", 1)[0], "올리기 준비는 요청했을 때만"
    assert "arp_upload_register" in state.split("되돌리기 어렵다", 1)[1], "등록은 공유 저장소로 나간다 — 확인 뒤"


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

