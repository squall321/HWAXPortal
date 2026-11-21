# 카드 프로필에서 personas.domains 줄을 짓는 명령(infra/scripts/persona-domains-build.py)의 시험 — 문턱 · 덧씌우기만 적기 · 있는 칸 보존
"""docs/expert-ontology 6.4(EO-10). 추적 어휘표의 도메인 줄은 도메인 검토로 짓는 칸이라(D-E5-3) 이 명령은 박스 덧씌우기에만 적는다."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("persona_domains_build", ROOT / "infra" / "scripts" / "persona-domains-build.py")
pdb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pdb)

PROFILE = {"domains": {
    "material": {"cards": 2729, "types": {"material_property": {"structural": 2688, "linked": 0, "objects": 0},
                                          "failure_mode": {"structural": 1, "linked": 0, "objects": 0}}},
    "rel": {"cards": 3000, "types": {"failure_mode": {"structural": 80, "linked": 900, "objects": 40},
                                     "test_item": {"structural": 0, "linked": 299, "objects": 12},
                                     "없는타입": {"structural": 0, "linked": 2000, "objects": 9}}},
    "sim": {"cards": 100, "types": {"sim_capability": {"structural": 0, "linked": 19, "objects": 3}}},
    "he": {"cards": 50, "types": {"failure_mode": {"structural": 50, "linked": 50, "objects": 1}}},
    "zzz": {"cards": 50, "types": {"failure_mode": {"structural": 50, "linked": 50, "objects": 1}}},
}}
TYPES = {"failure_mode", "test_item", "sim_capability", "material_property"}


def test_pick_applies_both_thresholds_and_skips_operator_unknown_domain_and_unknown_type():
    lines, skipped = pdb.pick(PROFILE["domains"], known_domains={"material", "rel", "sim", "he"}, known_types=TYPES,
                              min_share=0.10, min_cards=20)
    # rel — 고장모드 900/3000(30%)은 서고, 시험 항목 299/3000(9.97%)은 비율이 모자란다 · sim — 19장이라 장수가 모자란다
    assert lines == {"material": ["material_property"], "rel": ["failure_mode"]}
    assert skipped == {"unknown_domain": ["zzz"], "operator": 1, "below": 3, "unknown_type": 1}
    looser, _ = pdb.pick(PROFILE["domains"], known_domains={"rel", "sim"}, known_types=TYPES, min_share=0.05, min_cards=10)
    assert looser == {"rel": ["failure_mode", "test_item"], "sim": ["sim_capability"]}


def test_merge_adds_by_default_and_replace_keeps_other_fields():
    overlay = {"types": {"부품": "part"},
               "personas": {"domains": {"rel": {"core_types": ["criterion"], "areas": ["quality"]}, "pcb": {"core_types": ["part"]},
                                        "cam": {"apps": ["signalforge"], "core_types": ["test_item"]}}}}
    lines = {"rel": ["failure_mode"], "material": ["material_property"]}
    added = pdb.merge_overlay(overlay, lines, replace=False)
    assert added["personas"]["domains"]["rel"] == {"core_types": ["criterion", "failure_mode"], "areas": ["quality"]}
    assert added["personas"]["domains"]["pcb"] == {"core_types": ["part"]} and added["types"] == {"부품": "part"}
    assert overlay["personas"]["domains"]["rel"]["core_types"] == ["criterion"], "받은 덧씌우기를 고치지 않는다"
    replaced = pdb.merge_overlay(overlay, lines, replace=True)
    doms = replaced["personas"]["domains"]
    assert doms["rel"] == {"core_types": ["failure_mode"], "areas": ["quality"]} and doms["material"] == {"core_types": ["material_property"]}
    assert "pcb" not in doms and doms["cam"] == {"apps": ["signalforge"]}, "줄이 서지 않는 도메인은 core_types 만 걷는다"
    assert pdb.merge_overlay({}, lines, replace=False)["personas"]["domains"] == {"rel": {"core_types": ["failure_mode"]},
                                                                                 "material": {"core_types": ["material_property"]}}


def _box(tmp_path):
    vocab = tmp_path / "core_vocab.json"
    vocab.write_text(json.dumps({"types": {"고장모드": "failure_mode", "물성": "material_property", "시험항목": "test_item"},
                                 "personas": {"domains": {}}}), encoding="utf-8")
    prof = tmp_path / "profile.json"
    prof.write_text(json.dumps(PROFILE, ensure_ascii=False), encoding="utf-8")
    return vocab, prof


def test_main_counts_only_unless_write_and_never_touches_the_tracked_file(tmp_path, capsys):
    vocab, prof = _box(tmp_path)
    before = vocab.read_text(encoding="utf-8")
    assert pdb.main(["--vocab", str(vocab), "--profile", str(prof)]) == 0
    out = capsys.readouterr().out
    assert "셈만 했다" in out and "rel" in out and "zzz" in out and not (tmp_path / "core_vocab.local.json").exists()
    assert pdb.main(["--vocab", str(vocab), "--profile", str(prof), "--write"]) == 0
    local = json.loads((tmp_path / "core_vocab.local.json").read_text(encoding="utf-8"))
    assert local == {"personas": {"domains": {"material": {"core_types": ["material_property"]}, "rel": {"core_types": ["failure_mode"]}}}}
    assert vocab.read_text(encoding="utf-8") == before, "추적 어휘표는 건드리지 않는다"
    # 덧씌우기가 더한 타입(part)도 알아본다 · 두 번 돌려도 같은 파일
    (tmp_path / "core_vocab.local.json").write_text(json.dumps({**local, "types": {"부품": "part"}}), encoding="utf-8")
    prof.write_text(json.dumps({"domains": {"pcb": {"cards": 100, "types": {"part": {"structural": 0, "linked": 60, "objects": 5}}}}}), encoding="utf-8")
    assert pdb.main(["--vocab", str(vocab), "--profile", str(prof), "--write"]) == 0
    again = json.loads((tmp_path / "core_vocab.local.json").read_text(encoding="utf-8"))
    assert again["personas"]["domains"]["pcb"] == {"core_types": ["part"]} and again["personas"]["domains"]["rel"] == {"core_types": ["failure_mode"]}
    assert pdb.main(["--vocab", str(vocab), "--profile", str(prof), "--write"]) == 0
    assert json.loads((tmp_path / "core_vocab.local.json").read_text(encoding="utf-8")) == again


def test_main_says_why_when_the_profile_cannot_be_read(tmp_path, capsys):
    vocab, prof = _box(tmp_path)
    assert pdb.main(["--vocab", str(vocab), "--aidh", str(tmp_path / "없는곳")]) == 2 and "onto.sh" in capsys.readouterr().err
    prof.write_text(json.dumps({"agents": {}}), encoding="utf-8")
    assert pdb.main(["--vocab", str(vocab), "--profile", str(prof)]) == 2 and "프로필 꼴" in capsys.readouterr().err
    sh = tmp_path / "AIDataHub" / "deploy" / "apptainer"
    sh.mkdir(parents=True)
    (sh / "onto.sh").write_text("#!/usr/bin/env bash\necho '표가 없다' >&2\nexit 3\n", encoding="utf-8")
    assert pdb.main(["--vocab", str(vocab), "--aidh", str(tmp_path / "AIDataHub")]) == 2 and "표가 없다" in capsys.readouterr().err
    (sh / "onto.sh").write_text("#!/usr/bin/env bash\n[ \"$1 $2\" = 'profile --domains' ] || exit 9\necho '" + json.dumps(PROFILE) + "'\n",
                                encoding="utf-8")
    assert pdb.main(["--vocab", str(vocab), "--aidh", str(tmp_path / "AIDataHub")]) == 0 and "줄이 서는 도메인 2" in capsys.readouterr().out


def test_written_lines_pass_the_agent_server_reader():
    """이 명령이 적는 줄 꼴(도메인 → {core_types})이 에이전트 서버의 읽는 쪽(persona_links.validate)에서 버려지지 않는다."""
    import os
    import subprocess
    import sys

    import pytest

    agent = Path(os.environ.get("HWAX_AGENT_SERVER_ROOT") or ROOT.parent / "HWAXAgentServer")
    if not (agent / "persona_links.py").exists():
        pytest.skip(f"형제 리포에 persona_links.py 가 없다: {agent}")
    vocab = json.loads(pdb.VOCAB.read_text(encoding="utf-8"))
    org = sorted(json.loads(pdb.ORG.read_text(encoding="utf-8"))["domain_label"])
    lines, _ = pdb.pick(PROFILE["domains"], known_domains=set(org), known_types=set(vocab["types"].values()), min_share=0.10, min_cards=20)
    raw = pdb.merge_overlay({}, lines, replace=False)["personas"]
    code = ("import json, sys\nimport persona_links as pl\na = json.load(sys.stdin)\n"
            "v = pl.validate(a['raw'], types_map=a['types'], domains_known=frozenset(a['org']))\n"
            "print(json.dumps({'domains': v['domains'], 'dropped': v['dropped']}, ensure_ascii=False))\n")
    r = subprocess.run([sys.executable, "-c", code], input=json.dumps({"raw": raw, "types": vocab["types"], "org": org}, ensure_ascii=False),
                       cwd=agent, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr.strip()[-400:]
    got = json.loads(r.stdout)
    assert got["dropped"] == [] and set(got["domains"]) == set(lines)
