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
