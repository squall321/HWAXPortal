# 코어 어휘표 정본(backend/config/core_vocab.json)의 꼴 — 게이트웨이 · 에이전트 서버가 형제 리포에서 읽는다(docs/request-1029 B-1 · D-1)
"""왜 — 코어 낱말이 세 곳의 손 표(에이전트 프롬프트 · 게이트웨이 동의어 · 에이전트 분야 힌트)에 따로 있어 같은 낱말을 서로 다르게 틀렸다
(10-29 cae00 웹 챗 QA — R-1 · R-4). 표를 하나로 모았으니 그 꼴이 깨지면 두 소비자가 함께 옛 동작으로 떨어진다. 꼴을 여기서 막고, 소비자 쪽은
각자의 리포에서 이 파일을 실제로 읽어 본다.
"""
import json
import re
from pathlib import Path

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
        assert re.fullmatch(r"[a-z][a-z0-9_]*", slug), f"타입 이름은 허브의 slug 꼴이다 — {slug}"
    for key, a in d["apps"].items():
        assert a["role"] in ROLES, (key, a)
        assert a.get("label", "").strip(), key
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
    assert {k for k, a in d["apps"].items() if a["role"] == "staging"} == {"stepforge-prod", "dynaforge-prod"}
    assert {r["relation"] for r in d["relations"]} == {"occurs_in_part", "detects", "predicts", "guards_against"}


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
