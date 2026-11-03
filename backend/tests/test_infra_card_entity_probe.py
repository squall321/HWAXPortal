# 카드 ↔ 허브 객체 연결 범위 탐침(infra/scripts/card-entity-probe.py)의 시험 — 가짜 허브 · 가짜 AIDataHub 로 맞추기 · exact 만 · 읽기만을 본다
"""docs/expert-ontology O0a(사용자 결정 EO-2 · EO-4). 진짜 허브는 cae00 에만 있어 여기서는 SP 의 답 꼴(ObjectPageOut · ResolveManyOut)을 그대로 흉내 낸다."""
from __future__ import annotations

import asyncio
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("card_entity_probe", ROOT / "infra" / "scripts" / "card-entity-probe.py")
probe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(probe)

HUB = "rootdesigndatahub"


# ── 글 · 사전 ────────────────────────────────────────────────────────────
def test_tokens_fold_width_and_case_and_split_scripts():
    assert probe.tokens("ＰＣＢ Solder-Joint Crack이") == ["pcb", "solder", "joint", "crack", "이"]


def test_particle_is_stripped_only_when_two_syllables_remain():
    assert probe.strip_particle("균열이") == "균열"
    assert probe.strip_particle("균열에서") == "균열"
    assert probe.strip_particle("이가") == "이가", "떼면 한 글자가 남는다"
    assert probe.strip_particle("crack") == "crack"


@pytest.mark.parametrize("term,ok", [("IC", False), ("PCB", True), ("균열", True), ("균", False), ("123", False),
                                      ("solder joint crack", True), ("a b c d e f g h i", False)])
def test_term_ok(term, ok):
    assert probe.term_ok(tuple(probe.tokens(term))) is ok


def _dic(*objs, stop=()):
    d = probe.Dictionary(stop=set(stop))
    for t, label, key, aliases in objs:
        d.add_object(t, label, key, aliases)
    return d


def test_dictionary_takes_label_key_aliases_and_skips_short_and_stop():
    d = _dic(("failure_mode", "솔더 균열", "FM-0001", ["solder joint crack", "SJC"]),
             ("failure_mode", "기타", "FM-0002", []), ("test_item", "낙하", "TI-07", "drop test"), stop=("기타",))
    assert ("솔더", "균열") in d.terms and ("solder", "joint", "crack") in d.terms and ("fm", "0001") in d.terms
    assert ("sjc",) in d.terms and ("drop", "test") in d.terms, "별칭은 목록이든 글 하나든 받는다"
    assert ("기타",) not in d.terms and d.skipped["stop"] == 1
    assert d.objects == {"failure_mode": 2, "test_item": 1} and d.with_aliases == {"failure_mode": 1, "test_item": 1}
    assert d.terms[("솔더", "균열")] == {("failure_mode", "솔더 균열")}, "물을 이름은 허브가 준 글자 그대로"


def test_match_multi_token_terms_particles_and_word_units():
    d = _dic(("failure_mode", "솔더 균열", "FM-1", []), ("failure_mode", "가속도", "FM-2", []), ("test_item", "PCB", "TI-1", []))
    got = d.match("시험에서 솔더 균열이 났다. 가속도 센서와 ＰＣＢ 를 보았다. PCBs 는 아니다. 미세균열")
    assert got == {("솔더", "균열"): 1, ("가속도",): 1, ("pcb",): 1}
    # '가속도' 는 조사를 떼면 '가속' 이 되지만 원래 꼴로 맞는다 · 'PCBs' 와 '미세균열' 은 낱말 단위라 맞지 않는다(정밀도 먼저 — 계획 5절)


# ── 표본 · 칸 ────────────────────────────────────────────────────────────
def test_sample_offsets_are_seeded_distinct_and_take_all_of_small_strata():
    a = probe.sample_offsets(1000, 5, 20261103, "paper")
    assert a == probe.sample_offsets(1000, 5, 20261103, "paper") and len(set(a)) == 5 and a == sorted(a)
    assert a != probe.sample_offsets(1000, 5, 20261103, "patent"), "층마다 따로 뽑는다"
    assert probe.sample_offsets(3, 5, 1, "x") == [0, 1, 2] and probe.sample_offsets(0, 5, 1, "x") == []


def test_parse_strata_and_bad_spec():
    assert probe.parse_strata("paper:2, patent:1") == [("paper", 2), ("patent", 1)]
    with pytest.raises(ValueError):
        probe.parse_strata("paper")


def test_card_fields_report_presence_not_values():
    rec = {"content": {"eng_meta": {"project": "S26 U-01"}, "card": {"standard_refs": ["IPC-A-610", "JESD22"]}, "properties": [{}, {}, {}]}}
    assert probe.card_fields(rec) == {"project": "S26 U-01", "standard_refs": 2, "properties": 3}
    assert probe.card_fields({"content": None}) == {"project": None, "standard_refs": 0, "properties": 0}


# ── 풀이 · 이름 ──────────────────────────────────────────────────────────
def test_verdicts_read_sp_resolve_many_shape_and_keep_key_only_for_exact():
    reply = {"items": [{"name": "솔더 균열", "match": "exact", "object": {"id": "u1", "key": "FM-1", "label": "솔더 균열"}},
                       {"name": "크랙", "match": "candidates", "object": None, "candidates": [{"id": "u2"}]},
                       {"name": "없는것", "match": "none", "object": None},
                       {"name": "키없음", "match": "exact", "object": {"id": "u9", "key": None}}],
             "counts": {"exact": 2, "candidates": 1, "none": 1}}
    assert probe.verdicts(reply) == {"솔더 균열": ("exact", "FM-1"), "크랙": ("candidates", None), "없는것": ("none", None),
                                     "키없음": ("exact", "u9")}


def test_exposed_names_follow_tools_map_orig_for_prefixed_hub_family():
    tmap = {"map": {"rootdesigndatahub_objects_list": HUB, "rootdesigndatahub_objects_resolve_many": HUB, "list_records": "ai-data-hub",
                    "get_record": "ai-data-hub", "get_record_sections": "ai-data-hub", "failuretrace_objects_list": "failuretrace"},
            "orig": {"rootdesigndatahub_objects_list": "objects_list", "rootdesigndatahub_objects_resolve_many": "objects_resolve_many",
                     "failuretrace_objects_list": "objects_list"}}
    got = probe.exposed_names(tmap, {HUB: probe.HUB_TOOLS, "ai-data-hub": probe.AIDH_TOOLS})
    assert got[(HUB, "objects_list")] == "rootdesigndatahub_objects_list" and (("failuretrace", "objects_list") not in got)
    assert got[("ai-data-hub", "get_record_sections")] == "get_record_sections"


def test_caller_refuses_anything_outside_the_read_list_before_calling():
    called = []

    async def call(name, args):
        called.append(name)
        return {}
    c = probe.ReadOnlyCaller(call, {(HUB, "objects_list"): "x", (HUB, "objects_create"): "y"})
    with pytest.raises(PermissionError):
        asyncio.run(c(HUB, "objects_create", {}))
    with pytest.raises(LookupError):
        asyncio.run(c(HUB, "objects_resolve_many", {}))
    assert called == [], "거절은 부르기 전에"
    assert asyncio.run(c(HUB, "objects_list", {})) == {} and called == ["x"]


# ── 끝에서 끝까지(가짜 허브 · 가짜 AIDataHub) ─────────────────────────────
OBJECTS = {"failure_mode": [{"id": "a", "key": "FM-1", "label": "솔더 균열", "aliases": ["solder joint crack"]},
                            {"id": "b", "key": "FM-2", "label": "크랙", "aliases": []},
                            {"id": "c", "key": "FM-3", "label": "박리", "aliases": ["delamination"]}],
           "test_item": [{"id": "d", "key": "TI-1", "label": "낙하 시험", "aliases": ["drop test"]}]}
AMBIGUOUS = {"크랙"}          # 허브에 같은 이름이 둘 — candidates
CARDS = {"paper": [("P1", "Solder joint crack after drop test", "본문 비밀 낱말 ZQX"), ("P2", "Unrelated optics", "렌즈")],
         "expert_knowledge_card": [("E1", "박리와 크랙", "박리가 생기면 …"), ("E2", "크랙 사례", "크랙 만 있다")]}


def _fake(monkeypatch, calls):
    monkeypatch.setattr(probe, "LIST_PAGE", 2)

    async def call(name, args):
        calls.append(name)
        if name == "objects_list":
            rows = OBJECTS.get(args["type_slug"], [])
            o = args["offset"]
            return {"items": rows[o:o + args["limit"]], "total": len(rows), "limit": args["limit"], "offset": o}
        if name == "objects_resolve_many":
            items = []
            for n in args["names"]:
                hit = next((r for r in OBJECTS[args["type_slug"]] if n == r["label"] or n == r["key"] or n in r["aliases"]), None)
                if n in AMBIGUOUS:
                    items.append({"name": n, "match": "candidates", "object": None})
                elif hit:
                    items.append({"name": n, "match": "exact", "object": {"id": hit["id"], "key": hit["key"]}})
                else:
                    items.append({"name": n, "match": "none", "object": None})
            return {"items": items, "counts": {}}
        if name == "list_records":
            rows = CARDS.get(args.get("doc_type"), [])
            o = args["offset"]
            return {"total": len(rows), "count": 1, "offset": o, "items": [{"id": r[0]} for r in rows[o:o + 1]]}
        if name == "get_record":
            rid = args["record_id"]
            row = next(r for rows in CARDS.values() for r in rows if r[0] == rid)
            return {"id": rid, "title": row[1], "summary": "", "content": {}}
        if name == "get_record_sections":
            rid = args["record_id"]
            row = next(r for rows in CARDS.values() for r in rows if r[0] == rid)
            secs = [{"section_id": "1", "title": "", "content_text": row[2]}]
            return secs[args["offset"]:args["offset"] + args["limit"]] if len(secs) > 1 else (secs[0] if args["offset"] == 0 else [])
        raise AssertionError(f"모르는 도구 {name}")
    exposed = {(HUB, "objects_list"): "objects_list", (HUB, "objects_resolve_many"): "objects_resolve_many",
               ("ai-data-hub", "list_records"): "list_records", ("ai-data-hub", "get_record"): "get_record",
               ("ai-data-hub", "get_record_sections"): "get_record_sections"}
    return probe.ReadOnlyCaller(call, exposed)


def test_run_probe_links_exact_only_and_reports_counts_without_card_text(monkeypatch):
    calls: list[str] = []
    caller = _fake(monkeypatch, calls)
    rep = asyncio.run(probe.run_probe(caller, hub=HUB, types=["failure_mode", "test_item"], strata=[("paper", 2), ("expert_knowledge_card", 2)],
                                      seed=1, stop=set(), max_objects=100, sections_max=10, log=lambda m: None))
    fm, ti = rep["by_type"]["failure_mode"], rep["by_type"]["test_item"]
    # P1 은 'solder joint crack'(솔더 균열의 별칭 — exact), E1 은 '박리'(exact) · '크랙'(candidates), E2 는 '크랙'(candidates)뿐 — 잇지 않는다, P2 는 없음
    assert fm["cards_linked"] == 2 and fm["by_doc_type"]["paper"] == {"linked": 1, "read": 2, "pct": 50.0}
    assert fm["by_doc_type"]["expert_knowledge_card"] == {"linked": 1, "read": 2, "pct": 50.0}, "candidates 만 맞은 카드는 이어진 것이 아니다"
    assert fm["verdicts"] == {"exact": 2, "candidates": 1}
    assert ti["cards_linked"] == 1 and rep["any_type_linked"] == 2 and rep["cards_read"] == 4
    assert rep["meta"]["dictionary"]["objects"] == {"failure_mode": 3, "test_item": 1}
    assert set(calls) <= probe.READ_TOOLS and calls.count("objects_list") == 3, "failure_mode 두 쪽 + test_item 한 쪽"
    text = probe.summary_text(rep)
    assert "ZQX" not in text and "렌즈" not in text and "failure_mode" in text and "이어진 카드 2장" in text
    assert "ZQX" not in json.dumps(rep, ensure_ascii=False), "카드 글은 보고서 어디에도 없다"


def test_run_probe_survives_a_failing_stratum_and_type(monkeypatch):
    calls: list[str] = []
    caller = _fake(monkeypatch, calls)
    real = caller._call

    async def flaky(name, args):
        if name == "list_records" and args.get("doc_type") == "expert_knowledge_card":
            raise RuntimeError("AIDataHub 잠깐 불통")
        if name == "objects_list" and args["type_slug"] == "test_item":
            raise RuntimeError("허브 불통")
        return await real(name, args)
    caller._call = flaky
    rep = asyncio.run(probe.run_probe(caller, hub=HUB, types=["failure_mode", "test_item"], strata=[("paper", 2), ("expert_knowledge_card", 1)],
                                      seed=1, stop=set(), max_objects=100, sections_max=10, log=lambda m: None))
    assert rep["cards_read"] == 2 and "expert_knowledge_card" in rep["meta"]["sample_problems"]
    assert "test_item" in rep["meta"]["dictionary_problems"] and rep["by_type"]["failure_mode"]["cards_linked"] == 1


# ── 진입 ─────────────────────────────────────────────────────────────────
def test_main_stops_without_a_pat(monkeypatch, capsys):
    monkeypatch.delenv("HWAX_GATEWAY_PAT", raising=False)
    assert probe.main([]) == 2 and "HWAX_GATEWAY_PAT" in capsys.readouterr().err


def test_main_says_this_box_has_no_hub_and_stops(monkeypatch, capsys):
    monkeypatch.setenv("HWAX_GATEWAY_PAT", "pat-not-real")
    monkeypatch.setattr(probe, "_tools_map", lambda base, token: {"map": {"list_records": "ai-data-hub"}, "orig": {}})
    assert probe.main([]) == 2
    err = capsys.readouterr().err
    assert "rootdesigndatahub:objects_list" in err and "cae00" in err


def test_core_vocab_overlay_is_a_merge_patch(tmp_path):
    base = tmp_path / "core_vocab.json"
    base.write_text(json.dumps({"canonical": {"app": "rootdesigndatahub"}, "types": {"고장모드": "failure_mode", "물성": "material_property"}}),
                    encoding="utf-8")
    (tmp_path / "core_vocab.local.json").write_text(json.dumps({"types": {"물성": None, "부품": "part"}}), encoding="utf-8")
    got = probe.load_core_vocab(base)
    assert got["types"] == {"고장모드": "failure_mode", "부품": "part"} and got["canonical"]["app"] == "rootdesigndatahub"


def test_tracked_core_vocab_names_the_canonical_hub_and_types():
    v = probe.load_core_vocab(probe.CORE_VOCAB.with_name("core_vocab.json"))
    assert v["canonical"]["app"] == HUB and "failure_mode" in v["types"].values()
