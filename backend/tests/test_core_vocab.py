# 코어 어휘표 정본(backend/config/core_vocab.json)의 꼴 — 게이트웨이 · 에이전트 서버가 형제 리포에서 읽는다(docs/request-1029 B-1 · D-1)
"""왜 — 코어 낱말이 세 곳의 손 표(에이전트 프롬프트 · 게이트웨이 동의어 · 에이전트 분야 힌트)에 따로 있어 같은 낱말을 서로 다르게 틀렸다
(10-29 cae00 웹 챗 QA — R-1 · R-4). 표를 하나로 모았으니 그 꼴이 깨지면 두 소비자가 함께 옛 동작으로 떨어진다. 꼴을 여기서 막고, 소비자 쪽은
각자의 리포에서 이 파일을 실제로 읽어 본다.
"""
import json
import re
from pathlib import Path

import pytest

VOCAB = Path(__file__).resolve().parents[1] / "config" / "core_vocab.json"
ROLES = {"sibling", "staging", "noncore"}


def _load() -> dict:
    return json.loads(VOCAB.read_text(encoding="utf-8"))


def test_꼴과_필수_칸():
    d = _load()
    assert d["version"] == 1
    c = d["canonical"]
    assert c["app"] and c["label"].strip() and c["tagline"].strip()
    assert d["rule_words"] and all(isinstance(w, str) and w.strip() == w and w for w in d["rule_words"])
    assert len(d["rule_words"]) == len(set(d["rule_words"])), "발동 낱말이 겹친다"
    for e in d["search"]:
        assert e["words"] and e["tools"], e
        assert all(w.strip() == w and w for w in e["words"])
        assert all(t == t.lower() and " " not in t for t in e["tools"]), "도구 이름은 노출 꼴의 원래 이름(소문자 · 공백 없음)이다"
    seen: set = set()
    for e in d["search"]:
        dup = seen & set(e["words"])
        assert not dup, f"검색 낱말이 두 묶음에 있다 — {dup}"
        seen |= set(e["words"])
    for r in d["relations"]:
        assert r["phrase"].strip() and r["relation"] == r["relation"].strip() and " " not in r["relation"]
    vocab_words = set(d["rule_words"]) | {w for e in d["search"] for w in e["words"]}
    assert d["types"] and isinstance(d["types"], dict)
    for w, slug in d["types"].items():
        assert w in vocab_words, f"타입 대응의 낱말은 어휘표 낱말(rule_words · search)이다 — {w}"
        assert re.fullmatch(r"[a-z][a-z0-9_]{0,31}", slug), \
            f"타입 이름은 허브의 slug 꼴이다(StandardPlatform SLUG_RE — 에이전트 서버가 같은 꼴로 거르고, 아니면 이 표를 버린다) — {slug}"
    for key, a in d["apps"].items():
        assert a["role"] in ROLES, (key, a)
        assert a.get("label", "").strip(), key
        if "tagline" in a:
            # 형제 소개 줄(docs/request-1029 E-2 · E2-4) — 게이트웨이가 그 형제 도구 설명 앞에 붙인다. 형제에만 쓴다(비코어 · 시험 앱의 설명은 그쪽
            # 몫 — 게이트웨이도 읽지 않는다). 웹 챗 묶음에 늘 드는 형제 도구 넷의 설명이 이 길이만큼 는다 — 120자 이내.
            assert a["role"] == "sibling", f"소개 줄은 형제에만 — {key}"
            assert isinstance(a["tagline"], str) and 0 < len(a["tagline"].strip()) <= 120, (key, a["tagline"])
    assert d["canonical"]["app"] not in d["apps"], "정본은 apps 에 다시 적지 않는다"


def test_요청서가_짚은_낱말과_앱이_들어_있다():
    """10-29 QA 에서 코어를 건너뛴 다섯 질문(OT-06 ~ 10)의 낱말과, 코어 질문을 가로챈 셋(FMEA · ARP · ODB 허브)이 빠지면 고친 것이 사라진다."""
    d = _load()
    for w in ("고장모드", "시험항목", "가상검증", "관리 기준", "물성", "PLM 과제", "부품"):
        assert w in d["rule_words"], w
    words = {w for e in d["search"] for w in e["words"]}
    for w in ("고장모드", "시험항목", "가상검증", "관리기준", "관리 기준", "영률", "대책"):
        assert w in words, w
    assert "메커니즘" in d["rule_words"] and "메커니즘" not in words, "검색 낱말이 되면 '메커니즘 규명'(심의)을 허브가 가로챈다(R-5)"
    assert "실패모드" in words, "챗이 부른 질의 '규격 실패모드'(요청서 HG-01)"
    hub = next(e for e in d["search"] if "고장모드" in e["words"])
    assert {"object_resolve", "objects_summary", "graph_neighbors"} <= set(hub["tools"]), "타입 이름이 아니라 허브 읽기 도구 이름에 잇는다(R-4)"
    noncore = {k for k, a in d["apps"].items() if a["role"] == "noncore"}
    assert {"fmea", "arp", "odb-hub", "reportarchive", "matnexus", "componentcore"} <= noncore
    assert {r["relation"] for r in d["relations"]} == {"occurs_in_part", "detects", "predicts", "guards_against"}


def test_OB04_운영_앱_둘은_시험_사본으로_숨기지_않는다():
    """10-31 OB-04(사용자 결정 — 10-29 D-2 를 뒤집음) — dynaforge-prod · stepforge-prod 는 운영 앱이다. 역할 staging(시험 사본)이면 게이트웨이가
    목록 · 검색에서 숨긴다(R-6). 다른 역할로 적어도 뜻이 바뀐다 — sibling 이면 다른 허브 id 막이(HA-30)의 허브가 되고, noncore 면 챗 코어 규칙 ⑦ 에
    '코어 객체를 갖지 않는다' 로 실린다. 그래서 어휘표에 두지 않는다(보통 앱). 역할 staging 은 남는다 — 박스 덧씌우기가 시험 사본을 숨기는 길이다."""
    d = _load()
    assert not {"dynaforge-prod", "stepforge-prod"} & set(d["apps"]), d["apps"]


def test_HA32_요청서가_이름을_댄_타입_대응():
    """10-30 HA-32 — 챗이 없는 타입 이름을 지어냈다(DW-22 의 management_standard, 실제는 criterion). 요청서가 이름을 댄 대응 셋이 빠지면 고친 것이
    사라진다."""
    d = _load()
    assert {"고장모드": "failure_mode", "관리 기준": "criterion", "시험항목": "test_item"}.items() <= d["types"].items()
    assert "management_standard" not in d["types"].values()


def test_HP56_전작은_발동_낱말이고_맨_후속은_아니다():
    """10-30 HP-56 — '전작' 은 세 리포에서 코어(앞 모델)로만 쓰이고, 맨 '후속' 은 '후속 심의(이어하기)' · '후속 라운드' · '후속 조치' 같은 심의 ·
    일반 말이다. 발동 낱말은 모델에게 '이 낱말이 나오면 첫 걸음은 정본 resolve' 라 말하므로 맨 '후속' 은 심의를 가로챈다 — '후속 모델' 로 둔다."""
    d = _load()
    assert "전작" in d["rule_words"] and "후속 모델" in d["rule_words"]
    assert "후속" not in d["rule_words"], "맨 '후속' 은 '후속 심의' 를 가로챈다"


# ── personas — 페르소나 연결(docs/request-1029 design-e5 3.1 · E5-4 · 결정 D-E5-3 (가)) ────────────────────────────────
# 꼴과 대조는 형제 리포의 실제 파일로 본다(design-e5 3.1 '형제 리포 시험이 실제 파일로 대조한다'). 에이전트 서버가 읽는 쪽(persona_links.validate)은 틀린
# 줄을 그 줄만 버리므로, 정본 판에 버려지는 줄이 하나라도 있으면 그 연결은 조용히 빠진 채 돈다 — 여기서 막는다. 게이트웨이는 이 칸을 읽지 않는다.
import ast  # noqa: E402
import os  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
ORG = ROOT / "frontend" / "src" / "components" / "chat" / "orgTaxonomy.json"
GW = ROOT.parent / "HWAXMcpGateway"
# 에이전트 서버 리포를 다른 자리(아직 합치지 않은 작업 트리)에서 보려면 HWAX_AGENT_SERVER_ROOT 로 준다.
AGENT = Path(os.environ.get("HWAX_AGENT_SERVER_ROOT") or ROOT.parent / "HWAXAgentServer")
PERSONA_FIELDS = {"domains", "experts", "data_types", "no_tools"}
LINE_FIELDS = {"core_types", "areas", "apps"}


def _org_domains() -> set[str]:
    return set(json.loads(ORG.read_text(encoding="utf-8"))["domain_label"])


def _tool_areas() -> dict:
    p = GW / "tool_areas.json"
    if not p.exists():
        pytest.skip(f"형제 리포 HWAXMcpGateway 의 tool_areas.json 이 없다: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def test_personas_꼴():
    p = _load()["personas"]
    assert set(p) - {"_doc"} == PERSONA_FIELDS, f"받는 칸은 {sorted(PERSONA_FIELDS)} 와 설명 _doc 뿐이다(에이전트 서버가 모르는 칸은 버린다) — {sorted(p)}"
    assert isinstance(p["domains"], dict) and isinstance(p["experts"], dict)
    assert isinstance(p["data_types"], list) and isinstance(p["no_tools"], list)
    for d, line in p["domains"].items():
        assert re.fullmatch(r"[a-z][a-z0-9_]{0,31}", d) and isinstance(line, dict) and set(line) <= LINE_FIELDS, (d, line)
        assert all(isinstance(line.get(f, []), list) for f in LINE_FIELDS), (d, line)
    for k, line in p["experts"].items():
        assert re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,120}", k), k
        assert set(line) == {"apps"} and 1 <= len(line["apps"]) <= 3 and len(set(line["apps"])) == len(line["apps"]), (k, line)


def test_personas_도메인은_조직도에_타입은_types_에_운영자는_없다():
    d, p = _load(), _load()["personas"]
    org, types = _org_domains(), set(d["types"].values())
    for dom in [*p["domains"], *p["no_tools"]]:
        assert dom in org, f"조직도 라벨 정본(orgTaxonomy domain_label)에 없는 도메인 — {dom}"
        assert dom != "he", "운영자 도메인은 넣지 않는다 — 운영자의 앱은 infra/personas/he-team.json 이 맡는다"
    assert not set(p["domains"]) & set(p["no_tools"]), "한 도메인은 줄이 있거나 no_tools 거나 하나다"
    for dom, line in p["domains"].items():
        assert set(line.get("core_types", [])) <= types, f"{dom} 의 core_types 는 이 표 types 의 값만 — {line}"
    assert set(p["data_types"]) <= types, f"data_types 는 이 표 types 의 값만 — {p['data_types']}"
    assert not [k for k in p["experts"] if k.split("-", 1)[0] == "he"], "운영자는 experts 에 넣지 않는다"


def test_personas_영역_앱은_게이트웨이_표에():
    p, ta = _load()["personas"], _tool_areas()
    areas, apps = {a["key"] for a in ta["areas"]}, set(ta["apps"])
    for dom, line in p["domains"].items():
        assert set(line.get("areas", [])) <= areas, f"{dom} — 게이트웨이 tool_areas.json 에 없는 영역 {set(line['areas']) - areas}"
        assert set(line.get("apps", [])) <= apps, f"{dom} — 게이트웨이 tool_areas.json 에 없는 앱 {set(line['apps']) - apps}"
    for k, line in p["experts"].items():
        assert set(line["apps"]) <= apps, f"{k} — 게이트웨이 tool_areas.json 에 없는 앱 {set(line['apps']) - apps}"


def test_personas_첫_판은_앱_전문가_덮어쓰기만이다():
    """design-e5 3.1 — 도메인 줄은 A-dev 와 도메인 검토로 짓고 연결을 쓰는 사람은 실사용 H 를 보지 않는다(L7). 첫 판(10-31)은 자기 앱이 있는 지식
    전문가(적층 계산 · 열충격 예측 · 물성 · 낙하 해석 · 변환 · 백서 · 시장 — 열 명 안팎)의 덮어쓰기뿐이다. 도메인 줄을 더할 때 이 시험을 고친다 —
    그때 L7 을 지켰는지(A-test · H 를 보지 않고 썼는지)를 context-notes 에 적는다."""
    p = _load()["personas"]
    assert p["domains"] == {} and p["data_types"] == [] and p["no_tools"] == []
    assert 5 <= len(p["experts"]) <= 15, len(p["experts"])


_VALIDATE = (
    "import json, sys\n"
    "import persona_links as pl\n"
    "a = json.load(sys.stdin)\n"
    "v = pl.validate(a['raw'], types_map=a['types'], domains_known=frozenset(a['org']), areas_known=frozenset(a['areas']),\n"
    "                apps_known=frozenset(a['apps']))\n"
    "print(json.dumps({k: v[k] for k in ('present', 'domains', 'experts', 'data_types', 'no_tools', 'dropped', 'unchecked')},\n"
    "                 ensure_ascii=False))\n"
)


def test_personas_에이전트_서버_읽기가_한_줄도_버리지_않는다():
    """형제 리포 에이전트 서버의 읽는 쪽(persona_links.validate)에 정본 판을 그대로 넣는다 — 대조 표는 조직도 정본 · 이 표 types · 게이트웨이
    tool_areas.json. 박스에서는 그 박스 게이트웨이 도구 지도에 있는 앱만 통과한다(없는 앱을 적은 줄은 /health core_vocab.personas.dropped)."""
    if not (AGENT / "persona_links.py").exists():
        pytest.skip(f"형제 리포에 persona_links.py 가 없다: {AGENT}")
    d, ta = _load(), _tool_areas()
    arg = {"raw": d["personas"], "types": d["types"], "org": sorted(_org_domains()),
           "areas": sorted(a["key"] for a in ta["areas"]), "apps": sorted(ta["apps"])}
    r = subprocess.run([sys.executable, "-c", _VALIDATE], input=json.dumps(arg, ensure_ascii=False), cwd=AGENT,
                       env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True, timeout=120)
    # 형제 리포가 있는데 읽는 쪽을 못 부르면 건너뛰지 않는다 — 건너뜀은 통과가 아니다.
    assert r.returncode == 0, f"persona_links.validate 를 이 venv 로 부르지 못했다 — {r.stderr.strip()[-600:]}"
    v = json.loads(r.stdout)
    assert v["present"] is True and v["dropped"] == [] and v["unchecked"] == [], v
    assert v["experts"] == d["personas"]["experts"] and v["domains"] == d["personas"]["domains"], "읽은 연결이 정본과 다르다"
    assert v["data_types"] == d["personas"]["data_types"] and v["no_tools"] == d["personas"]["no_tools"]


# 게이트웨이에서 어휘표를 읽는 자리 — 읽기(_core_vocab) · 꼴(_core_vocab_parse) · /health(_core_vocab_health).
_GW_VOCAB_FNS = ("_core_vocab", "_core_vocab_parse", "_core_vocab_health")


def _gateway_parse():
    """게이트웨이 gateway._core_vocab_parse 를 형제 리포 원문에서 떼어 온다(게이트웨이 의존을 포털 venv 에 들이지 않는다) — 그 함수가 부르는 게이트웨이
    모듈 함수(10-31 E2-5 의 _label_names 처럼)까지 함께 떼어 온다(하나만 떼면 NameError 로 붉었다 — 반대 검토 10-31 · C-48). 돌려주는 것은 함수와,
    어휘표를 읽는 자리 셋 · 함께 떼어 온 함수의 원문이다."""
    p = GW / "gateway.py"
    if not p.exists():
        pytest.skip(f"형제 리포 HWAXMcpGateway 가 없다: {p}")
    src = p.read_text(encoding="utf-8")
    top = {n.name: n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef)}
    fns = {k: top[k] for k in _GW_VOCAB_FNS if k in top}
    assert set(fns) == set(_GW_VOCAB_FNS), f"게이트웨이에 {sorted(set(_GW_VOCAB_FNS) - set(fns))} 가 없다 — 어휘표를 읽는 자리가 바뀌었으면 이 시험도 고쳐라"
    need, todo = [], ["_core_vocab_parse"]
    while todo:
        name = todo.pop()
        if name in need:
            continue
        need.append(name)
        todo += [x.id for x in ast.walk(top[name]) if isinstance(x, ast.Name) and x.id in top and x.id not in need]
    ns: dict = {"re": re}
    for name in reversed(need):
        exec(compile(ast.get_source_segment(src, top[name]), f"gateway:{name}", "exec"), ns)  # noqa: S102 — 형제 리포 원문
    bodies = {k: ast.get_source_segment(src, n) for k, n in fns.items()}
    bodies.update({k: ast.get_source_segment(src, top[k]) for k in need})
    return ns["_core_vocab_parse"], bodies


def test_personas_를_더해도_게이트웨이_검색이_읽는_것은_같다():
    """게이트웨이 도구 검색(search_tools)은 어휘표에서 _core_vocab_parse 가 낸 것(동의어 · 정본 · 소개 줄 · 시험 사본)만 쓴다. personas 를 빼고 넣은 두 판의
    읽은 값이 바이트까지 같으면 검색 순위도 같다(design-e5 2.7 지킴 6). 어휘표 지문은 표 전체라 바뀐다 — E-7 검색 기록을 견줄 때 그 사실을 안다.
    게이트웨이가 personas 를 읽기 시작하면 이 시험이 먼저 짚는다 — 그때 순위가 그대로인지 다시 잰다."""
    parse, fns = _gateway_parse()
    d = _load()
    bare = {k: v for k, v in d.items() if k != "personas"}
    assert repr(parse(d)) == repr(parse(bare)), "personas 가 게이트웨이 검색이 읽는 값을 바꿨다"
    readers = [k for k, body in fns.items() if "personas" in body]
    assert not readers, f"게이트웨이 {readers} 가 personas 칸을 읽는다 — 검색 순위가 그대로인지 다시 잰다"
