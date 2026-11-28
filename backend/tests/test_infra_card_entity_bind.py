# 카드 ↔ 허브 객체 잇는 명령(infra/scripts/card-entity-bind.py)의 시험 — 가짜 허브 · 가짜 AIDataHub 명령으로 exact 만 · 읽기만 · 사전 파일 권한을 본다
"""docs/expert-ontology 6.3(사용자 결정 EO-6 · EO-8). 진짜 허브는 cae00 에만 있어 SP 의 답 꼴(ObjectPageOut · ResolveManyOut)을 그대로 흉내 낸다."""
from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import stat
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("card_entity_bind", ROOT / "infra" / "scripts" / "card-entity-bind.py")
bind = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bind)
probe = bind._probe()

HUB = "rootdesigndatahub"
OBJECTS = {"failure_mode": [{"id": "a", "key": "FM-1", "label": "솔더 균열", "aliases": ["solder joint crack", "솔더 균열"]},
                            {"id": "b", "key": "FM-2", "label": "크랙", "aliases": []},
                            {"id": "c", "key": "FM-3", "label": "박리", "aliases": "delamination"},
                            {"id": "e", "key": None, "label": "키 없는 객체", "aliases": []}],
           "test_item": [{"id": "d", "key": "TI-1", "label": "낙하 시험", "aliases": ["drop test"]}]}
AMBIGUOUS = {"크랙"}          # 허브에 같은 이름이 둘 — candidates


def _caller(calls, *, fail_type=""):
    async def call(name, args):
        calls.append((name, args.get("type_slug")))
        t = args["type_slug"]
        if t == fail_type:
            raise RuntimeError("허브 불통")
        rows = OBJECTS.get(t, [])
        if name == "objects_list":
            o = args["offset"]
            return {"items": rows[o:o + args["limit"]], "total": len(rows)}
        if name == "objects_resolve_many":
            items = []
            for n in args["names"]:
                hit = next((r for r in rows if n in (r["label"], r["key"]) or n == r["aliases"] or n in (r["aliases"] or [])), None)
                if n in AMBIGUOUS:
                    items.append({"name": n, "match": "candidates", "object": None})
                elif hit:
                    items.append({"name": n, "match": "exact", "object": {"id": hit["id"], "key": hit["key"]}})
                else:
                    items.append({"name": n, "match": "none", "object": None})
            return {"items": items}
        raise AssertionError(f"모르는 도구 {name}")
    return probe.ReadOnlyCaller(call, {(HUB, "objects_list"): "objects_list", (HUB, "objects_resolve_many"): "objects_resolve_many"})


# ── 판정 · 사전 ──────────────────────────────────────────────────────────
def test_exact_keys_keep_only_exact_names_that_have_a_key():
    reply = {"items": [{"name": "솔더 균열", "match": "exact", "object": {"id": "u1", "key": "FM-1"}},
                       {"name": "크랙", "match": "candidates", "object": None},
                       {"name": "없는것", "match": "none", "object": None},
                       {"name": "키없음", "match": "exact", "object": {"id": "u9", "key": None}},
                       {"name": "판정없음"}, "줄이 아니다"]}
    got, counts = bind.exact_keys(reply)
    assert got == {"솔더 균열": "FM-1"}, "키 없는 exact 는 잇지 않는다 — id 는 허브마다 다르다"
    assert counts == {"exact": 1, "candidates": 1, "none": 1, "exact_no_key": 1, "unanswered": 1}


def test_build_entries_asks_every_name_and_keeps_exact_only():
    calls: list = []
    entries, report = asyncio.run(bind.build_entries(_caller(calls), HUB, ["failure_mode", "test_item"], page=2, chunk=3, log=lambda m: None))
    assert {(e["type_slug"], e["key"], e["term"]) for e in entries} == {
        ("failure_mode", "FM-1", "솔더 균열"), ("failure_mode", "FM-1", "FM-1"), ("failure_mode", "FM-1", "solder joint crack"),
        ("failure_mode", "FM-2", "FM-2"), ("failure_mode", "FM-3", "박리"), ("failure_mode", "FM-3", "FM-3"),
        ("failure_mode", "FM-3", "delamination"), ("test_item", "TI-1", "낙하 시험"), ("test_item", "TI-1", "TI-1"), ("test_item", "TI-1", "drop test")}
    fm = report["failure_mode"]
    # 이름 9 — 솔더 균열 · FM-1 · solder joint crack · 크랙 · FM-2 · 박리 · FM-3 · delamination · 키 없는 객체(별칭의 겹침은 한 번)
    assert fm["objects"] == 4 and fm["names"] == 9 and fm["problem"] == ""
    assert fm["verdicts"] == {"candidates": 1, "exact": 7, "exact_no_key": 1}, "'크랙' 은 후보 · '키 없는 객체' 는 키가 없다"
    assert [c for c in calls if c[1] == "failure_mode"].count(("objects_list", "failure_mode")) == 3, "두 줄씩 세 쪽(마지막은 빈 쪽)"
    assert [c for c in calls if c[1] == "failure_mode"].count(("objects_resolve_many", "failure_mode")) == 3, "세 이름씩"
    assert {c[0] for c in calls} == set(bind.HUB_TOOLS), "읽기 둘만"


def test_build_entries_survives_a_failing_type_and_says_so():
    entries, report = asyncio.run(bind.build_entries(_caller([], fail_type="failure_mode"), HUB, ["failure_mode", "test_item"], log=lambda m: None))
    assert "목록을 받지 못했다" in report["failure_mode"]["problem"] and report["test_item"]["problem"] == ""
    assert {e["type_slug"] for e in entries} == {"test_item"}


def test_caller_refuses_write_tools_before_calling():
    c = probe.ReadOnlyCaller(lambda *a: None, {(HUB, "objects_create"): "x"})
    with pytest.raises(PermissionError):
        asyncio.run(c(HUB, "objects_create", {}))


def test_dictionary_file_is_private_and_version_ignores_order(tmp_path):
    entries = [{"type_slug": "failure_mode", "key": "FM-1", "term": "솔더 균열"}, {"type_slug": "test_item", "key": "TI-1", "term": "drop test"}]
    path = tmp_path / "run" / "dict.json"
    version = bind.write_dict(path, HUB, entries)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600 and stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc == {"hub": HUB, "dict_version": version, "entries": entries}
    assert bind.dict_version(list(reversed(entries))) == version and bind.dict_version(entries[:1]) != version


def test_summary_has_counts_only():
    summary = {"hub": HUB, "dict_version": "abc", "entries": 10,
               "types": {"failure_mode": {"objects": 4, "names": 9, "verdicts": {"exact": 7, "candidates": 1}, "problem": ""}},
               "bind": {"written": True, "records_linked": 3, "records": 9, "links": 5, "sections_scanned": 12,
                        "records_by_type": {"failure_mode": 3}, "objects_linked": {"failure_mode": 2}, "links_by_where": {"keyword": 2, "section": 3},
                        "records_by_doc_type": {"paper": {"linked": 1, "total": 4}}, "dictionary": {"terms": 9, "short": 1, "stop": 0, "ambiguous": 0}}}
    text = bind.summary_text(summary)
    assert "이어진 카드 3 / 9" in text and "25.0%" in text and "candidates 1" in text
    assert "솔더" not in text and "FM-1" not in text
    assert "잇지 않았다 — --dry-run" in bind.summary_text({**summary, "bind": None, "why": "--dry-run"})
    assert "쓰지 않았다" in bind.summary_text({**summary, "bind": {"written": False, "why": "맞출 낱말이 없다"}})


# ── 진입 ─────────────────────────────────────────────────────────────────
class _Session:
    """mcp ClientSession 흉내 — call_tool 이 가짜 허브에 닿는다."""

    def __init__(self, caller_calls):
        self._inner = _caller(caller_calls)._call

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def initialize(self):
        return None

    async def call_tool(self, name, args):
        out = await self._inner(name, args)
        return type("R", (), {"isError": False, "content": [type("C", (), {"type": "text", "text": json.dumps(out, ensure_ascii=False)})()]})()


def _fake_mcp(monkeypatch, calls):
    import contextlib
    import types

    @contextlib.asynccontextmanager
    async def streamablehttp_client(url, headers=None):
        assert headers["Authorization"] == "Bearer pat-not-real" and headers["X-HWAX-Corr"] == "card-entity-bind"
        yield (None, None, None)

    sess = types.ModuleType("mcp.client.session")
    sess.ClientSession = lambda r, w: _Session(calls)
    http = types.ModuleType("mcp.client.streamable_http")
    http.streamablehttp_client = streamablehttp_client
    for name, mod in (("mcp", types.ModuleType("mcp")), ("mcp.client", types.ModuleType("mcp.client")),
                      ("mcp.client.session", sess), ("mcp.client.streamable_http", http)):
        monkeypatch.setitem(sys.modules, name, mod)


def _fake_aidh(tmp_path, body: str, *, per_type: bool = True) -> Path:
    """AIDataHub 리포 흉내 — deploy/apptainer/onto.sh 가 받은 인자 · 사전 파일의 권한을 적고 정해 둔 JSON 을 낸다.
    per_type — 잇기가 사전에 든 타입만 다시 쓰는 판(AD-22)의 소스 표지를 둔다(타입 일부만 잇는 시험이 그 판에서만 돈다, HPO-2)."""
    d = tmp_path / "AIDataHub" / "deploy" / "apptainer"
    d.mkdir(parents=True)
    (d / "onto.sh").write_text(body, encoding="utf-8")
    if per_type:
        svc = tmp_path / "AIDataHub" / "api_server" / "src" / "api" / "services"
        svc.mkdir(parents=True)
        (svc / "onto_svc.py").write_text('type_counts = {}\n', encoding="utf-8")
    return tmp_path / "AIDataHub"


_OK_SH = '''#!/usr/bin/env bash
[ "$1" = bind ] && [ "$2" = --hub ] && [ "$4" = --dict ] || exit 9
stat -c %a "$5" > "$(dirname "$0")/seen.txt"
python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d['hub'], len(d['entries']), d['dict_version'])" "$5" >> "$(dirname "$0")/seen.txt"
cat <<JSON
{"mentions": {"rows": 7, "skipped": true}, "bind": {"hub": "$3", "written": true, "links": 5, "records": 9, "records_linked": 3,
 "sections_scanned": 12, "records_by_type": {"failure_mode": 3}, "objects_linked": {"failure_mode": 2}, "links_by_where": {"keyword": 5},
 "records_by_doc_type": {"paper": {"linked": 3, "total": 9}}, "dictionary": {"terms": 10, "short": 0, "stop": 0, "ambiguous": 0}}}
JSON
'''


def _env(monkeypatch, calls):
    monkeypatch.setenv("HWAX_GATEWAY_PAT", "pat-not-real")
    tmap = {"map": {"rootdesigndatahub_objects_list": HUB, "rootdesigndatahub_objects_resolve_many": HUB},
            "orig": {"rootdesigndatahub_objects_list": "objects_list", "rootdesigndatahub_objects_resolve_many": "objects_resolve_many"}}
    monkeypatch.setattr(probe, "_tools_map", lambda base, token: tmap)
    monkeypatch.setattr(bind, "_probe", lambda: probe)
    _fake_mcp(monkeypatch, calls)
    # 가짜 허브는 드러난 이름이 아니라 원래 이름으로 받는다 — 드러난 이름 → 원래 이름으로 돌려 준다
    real = probe.ReadOnlyCaller.__call__

    async def call(self, app, original, args):
        self.exposed = {k: k[1] for k in self.exposed}
        return await real(self, app, original, args)
    monkeypatch.setattr(probe.ReadOnlyCaller, "__call__", call)


def test_main_binds_through_the_aidatahub_command_and_removes_the_dictionary(monkeypatch, tmp_path, capsys):
    calls: list = []
    _env(monkeypatch, calls)
    aidh = _fake_aidh(tmp_path, _OK_SH)
    out = tmp_path / "out"
    rc = bind.main(["--types", "failure_mode,test_item", "--aidh", str(aidh), "--out", str(out), "--sleep", "0"])
    assert rc == 0
    seen = (aidh / "deploy" / "apptainer" / "seen.txt").read_text().split("\n")
    assert seen[0] == "600" and seen[1].startswith(f"{HUB} 10 "), "사전은 그 사람만 읽게 · exact 열 줄"
    assert not (out / "dict.json").exists(), "사전 파일은 끝나면 지운다"
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["entries"] == 10 and summary["bind"]["links"] == 5 and summary["hub"] == HUB
    assert summary["calls"] == {"objects_list": 2, "objects_resolve_many": 2}
    text = capsys.readouterr().out
    assert "이어진 카드 3 / 9" in text and "솔더" not in text and "솔더" not in json.dumps(summary, ensure_ascii=False)


def test_main_dry_run_never_calls_aidatahub_and_keep_dict_keeps_the_file(monkeypatch, tmp_path, capsys):
    _env(monkeypatch, [])
    aidh = _fake_aidh(tmp_path, _OK_SH)
    out = tmp_path / "out"
    assert bind.main(["--types", "failure_mode", "--aidh", str(aidh), "--out", str(out), "--sleep", "0", "--dry-run"]) == 0
    assert not (aidh / "deploy" / "apptainer" / "seen.txt").exists() and not (out / "dict.json").exists()
    assert "--dry-run" in capsys.readouterr().out
    assert bind.main(["--types", "failure_mode", "--aidh", str(aidh), "--out", str(out), "--sleep", "0", "--keep-dict"]) == 0
    assert stat.S_IMODE((out / "dict.json").stat().st_mode) == 0o600


def test_main_reports_a_failing_aidatahub_command_and_an_empty_dictionary(monkeypatch, tmp_path, capsys):
    _env(monkeypatch, [])
    aidh = _fake_aidh(tmp_path, "#!/usr/bin/env bash\necho '표가 없다' >&2\nexit 3\n")
    out = tmp_path / "out"
    assert bind.main(["--types", "failure_mode", "--aidh", str(aidh), "--out", str(out), "--sleep", "0"]) == 5
    assert "표가 없다" in capsys.readouterr().err and not (out / "dict.json").exists()
    # exact 가 하나도 없는 타입만 — 잇지 않는다(연결을 지우지 않는다)
    assert bind.main(["--types", "없는타입", "--aidh", str(aidh), "--out", str(tmp_path / "o2"), "--sleep", "0"]) == 4


def test_main_stops_without_a_pat_a_hub_or_the_aidatahub_command(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("HWAX_GATEWAY_PAT", raising=False)
    assert bind.main([]) == 2 and "HWAX_GATEWAY_PAT" in capsys.readouterr().err
    monkeypatch.setenv("HWAX_GATEWAY_PAT", "pat-not-real")
    assert bind.main(["--aidh", str(tmp_path / "없는곳")]) == 2 and "onto.sh" in capsys.readouterr().err
    monkeypatch.setattr(bind, "_probe", lambda: probe)
    monkeypatch.setattr(probe, "_tools_map", lambda base, token: {"map": {"list_records": "ai-data-hub"}, "orig": {}})
    assert bind.main(["--dry-run"]) == 2
    assert "rootdesigndatahub:objects_list" in capsys.readouterr().err


# ── 두 리포의 낱말 규칙이 같다 ────────────────────────────────────────────
def test_token_rules_match_aidatahub_service_letter_for_letter():
    """탐침(포털)과 잇는 쪽(AIDataHub onto_svc)의 낱말 규칙이 다르면 탐침이 잰 수와 실제 연결이 어긋난다."""
    src = ROOT.parent / "AIDataHub" / "api_server" / "src" / "api" / "services" / "onto_svc.py"
    if not src.is_file():
        pytest.skip("형제 리포 AIDataHub 에 onto_svc.py 가 없다(옛 판)")
    # 서비스 모듈은 DB 패키지에 묶여 있어 통째로 import 하지 않고 낱말 규칙 토막(상수 · tokens · strip_particle · term_ok)만 돌린다
    text = src.read_text(encoding="utf-8")
    ns: dict = {}
    exec("import os, re, unicodedata\n" + text[text.index("PARTICLES = tuple("):text.index("# ── 규칙")], ns)  # noqa: S102
    assert ns["PARTICLES"] == probe.PARTICLES
    for s in ("ＰＣＢ Solder-Joint Crack이", "균열에서는 미세균열과 가속도", "E=70 GPa, CTE 17ppm/°C", "휨이 0.3mm", ""):
        assert ns["tokens"](s) == probe.tokens(s)
        for tok in probe.tokens(s):
            assert ns["strip_particle"](tok) == probe.strip_particle(tok)
    for term in ("IC", "PCB", "균열", "균", "123", "solder joint crack", "a b c d e f g h i"):
        toks = tuple(probe.tokens(term))
        assert ns["term_ok"](toks) is probe.term_ok(toks)



# ── 타입 일부만 잇기(docs/request-1125 HPO-2) · 연결 0 의 까닭(HPO-3) ──────────────────────────────────────
def test_앞_판_AIDataHub_에_타입_일부만_주면_잇기_전에_멈춘다(monkeypatch, tmp_path, capsys):
    """AD-22 앞 판의 잇기는 그 허브의 연결을 통째로 다시 쓴다 — --types part 처럼 일부만 주면 다른 타입 연결이 지워진다."""
    _env(monkeypatch, [])
    aidh = _fake_aidh(tmp_path, _OK_SH, per_type=False)
    for args in (["--types", "failure_mode"], ["--only-types", "failure_mode"]):
        assert bind.main([*args, "--aidh", str(aidh), "--out", str(tmp_path / "o"), "--sleep", "0"]) == 2
        err = capsys.readouterr().err
        assert "다른 타입 연결이 지워진다" in err, err
    assert not (aidh / "deploy" / "apptainer" / "seen.txt").exists(), "AIDataHub 를 부르지 않았다"
    assert bind.main(["--types", "failure_mode", "--aidh", str(aidh), "--out", str(tmp_path / "o2"), "--sleep", "0", "--dry-run"]) == 0, \
        "--dry-run 은 AIDataHub 를 부르지 않으니 된다"
    assert bind.main(["--types", "a,b", "--only-types", "a", "--aidh", str(aidh)]) == 2 and "하나만" in capsys.readouterr().err


_TYPED_SH = _OK_SH.replace('"dictionary": {"terms": 10, "short": 0, "stop": 0, "ambiguous": 0}}}',
                           '"dictionary": {"terms": 10, "short": 0, "stop": 0, "ambiguous": 0}, "links_by_type": {"failure_mode": 5},'
                           ' "types": ["failure_mode"], "type_counts": {"failure_mode": {"before": 2, "after": 5, "rewritten": true},'
                           ' "plm_task": {"before": 7, "after": 7, "rewritten": false}}, "links_hub_total": 12}}')


def test_only_types_는_그_타입_사전만_넘기고_타입별_전후를_싣는다(monkeypatch, tmp_path, capsys):
    calls: list = []
    _env(monkeypatch, calls)
    aidh = _fake_aidh(tmp_path, _TYPED_SH)
    out = tmp_path / "out"
    assert bind.main(["--only-types", "failure_mode", "--aidh", str(aidh), "--out", str(out), "--sleep", "0"]) == 0
    assert {t for _n, t in calls} == {"failure_mode"}, "그 타입만 허브에 묻는다"
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["scope"] == "only-types" and summary["bind"]["type_counts"]["plm_task"]["after"] == 7
    text = capsys.readouterr().out
    assert "failure_mode" in text and "2 →       5  다시 씀" in text and "7 →       7  그대로" in text and "허브 전체 연결 12" in text, text


def test_연결_0_인_타입의_까닭이_요약에_있다(monkeypatch, tmp_path, capsys):
    """11-23 결합 요약에서 개발모델 · 과제 · 관리 기준이 0 이었다 — 카드에 이름이 없는지 · 허브 쪽인지를 타입별로 적는다(수만)."""
    _env(monkeypatch, [])
    aidh = _fake_aidh(tmp_path, _TYPED_SH)
    out = tmp_path / "out"
    monkeypatch.setitem(OBJECTS, "criterion", [])
    assert bind.main(["--types", "failure_mode,test_item,criterion", "--aidh", str(aidh), "--out", str(out), "--sleep", "0"]) == 0
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    z = summary["zero"]
    assert "failure_mode" not in z, "이어진 타입은 까닭이 없다"
    assert z["criterion"] == "허브에 그 타입의 객체가 없다"
    assert z["test_item"].startswith("사전 낱말 3개가 AIDataHub 규칙에서 다 걸러졌다"), z
    assert "연결 0 — test_item" in capsys.readouterr().out
    r = {"x": {"objects": 3, "names": 3, "verdicts": {"none": 3}, "problem": ""},
         "y": {"objects": 3, "names": 3, "verdicts": {"exact": 3}, "problem": ""}}
    w = bind.zero_reasons(r, [{"type_slug": "y", "key": "K", "term": "t"}], {"written": True, "links_by_type": {}})
    assert w["x"].startswith("허브가 이름을 하나도 exact 로 확인하지 못했다") and w["y"].startswith("카드 글")
    assert bind.zero_reasons(r, [], None) == {"x": w["x"]}, "잇지 않았으면 허브 쪽 까닭만"
    assert "솔더" not in json.dumps(z, ensure_ascii=False)
