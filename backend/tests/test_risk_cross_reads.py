# update-all 의 리스크 앱 조회 도구 점검(infra/scripts/risk-cross-reads.py) — 읽기 전용 PAT 로 부르는 남의 앱 도구가 게이트웨이 읽기 판정을 지나는가(docs/request-1125 HP-59)
"""왜 — 11-01 에 odb-hub find_job 이 읽기 전용 PAT 로 막혀 리스크 앱 ECAD 가 약 48분 멈췄는데 verify 204 · 스모크 3/3 은 초록이었다.
가짜 /tools-map 으로 판정을 보고, 형제 리포 HWAXRisk 가 있으면 어댑터 소스의 도구 목록과 견준다(어댑터가 도구를 더하면 여기도 더한다)."""
from __future__ import annotations

import ast
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("risk_cross_reads", ROOT / "infra/scripts/risk-cross-reads.py")
rcr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rcr)


def _tm(*, drop: tuple = (), cls_over: dict | None = None, backends=("heax-step_forge", "heax-kooremapper_mcp", "odb-hub")) -> dict:
    mp, orig, cls = {}, {}, {}
    for backend, tools in rcr.PAIRS:
        if backend not in backends:
            continue
        for t in tools:
            if (backend, t) in drop:
                continue
            n = t if t != "list_parts" else f"{backend.replace('-', '')}_{t}"   # 이름이 겹치면 게이트웨이가 접두를 단다
            mp[n], orig[n] = backend, t
            cls[n] = {"class": "read", "source": "confirmed_list"}
    for n, c in (cls_over or {}).items():
        cls[n] = c
    return {"map": mp, "orig": orig, "tool_class": cls}


def test_다_읽기면_ok_한_줄():
    out = rcr.check(_tm())
    assert out == [("ok", f"리스크 앱 조회 도구 {sum(len(t) for _b, t in rcr.PAIRS)}개 — 게이트웨이 읽기 판정을 지난다(읽기 전용 PAT 로 불린다)")]


def test_읽기_목록에서_find_job_을_빼면_fail():
    """요청서의 확인 — read_tools.json 에서 odb-hub find_job 한 줄을 빼 둔 판이면 ✗."""
    out = rcr.check(_tm(cls_over={"find_job": {"class": "unknown", "source": "none"}}))
    fails = [t for k, t in out if k == "fail"]
    assert len(fails) == 1 and "odb-hub:find_job(unknown · none)" in fails[0] and "read_tools.local.json" in fails[0], out
    assert not [k for k, _t in out if k == "ok"]


def test_쓰기로_판정된_도구도_fail_이고_백엔드가_없으면_재지_않는다():
    out = rcr.check(_tm(backends=("heax-step_forge",), cls_over={"part_mesh_map": {"class": "write", "source": "app_annotation"}}))
    assert ("info", "리스크 앱 조회 도구 — odb-hub 가 이 게이트웨이에 없어 재지 않았다") in out
    assert any(k == "fail" and "heax-step_forge:part_mesh_map(write · app_annotation)" in t for k, t in out), out


def test_없는_도구는_info_이고_판정에_들지_않는다():
    out = rcr.check(_tm(drop=(("odb-hub", "get_odb_download"),)))
    assert any(k == "info" and "get_odb_download" in t for k, t in out) and any(k == "ok" for k, _t in out), out


def test_명령으로_돌린다(tmp_path):
    f = tmp_path / "tm.json"
    f.write_text(json.dumps(_tm(cls_over={"find_job": {"class": "unknown", "source": "none"}})), encoding="utf-8")
    r = subprocess.run([sys.executable, str(ROOT / "infra/scripts/risk-cross-reads.py"), "--tools-map", str(f)], capture_output=True, text=True)
    assert r.returncode == 0 and r.stdout.startswith("fail\t"), r.stdout + r.stderr
    f.write_text(json.dumps({"map": {}}))
    r = subprocess.run([sys.executable, str(ROOT / "infra/scripts/risk-cross-reads.py"), "--tools-map", str(f)], capture_output=True, text=True)
    assert r.returncode == 0 and "tool_class 가 없어" in r.stdout, "옛 게이트웨이는 재지 않는다"
    f.write_text("{")
    assert subprocess.run([sys.executable, str(ROOT / "infra/scripts/risk-cross-reads.py"), "--tools-map", str(f)]).returncode == 2


def test_update_all_이_실패를_치명으로_센다():
    ua = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")
    i = ua.index("risk-cross-reads.py")
    block = ua[ua.rindex("if [ \"$TM_OK\" = 1 ]; then", 0, i):ua.index("\nfi\n", i)]
    assert "fail) fail \"$_rct\"" in block and "ok) ok \"$_rct\"" in block, block


def _risk_adapter_pairs(risk: Path) -> set[tuple[str, str]]:
    """HWAXRisk 어댑터 소스의 (백엔드 키, 원래 이름) — registry ADAPTERS 의 app_key 와 각 어댑터의 REQUIRED_TOOLS · CORPUS_TOOLS · 결과 도구."""
    ad = risk / "backend/app/adapters"

    def tuples(path: Path) -> dict[str, tuple[str, ...]]:
        out: dict[str, tuple[str, ...]] = {}
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            tgt = node.target if isinstance(node, ast.AnnAssign) else (node.targets[0] if isinstance(node, ast.Assign) else None)
            if isinstance(tgt, ast.Name) and isinstance(getattr(node, "value", None), ast.Tuple):
                vals = [e.value for e in node.value.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
                if vals and len(vals) == len(node.value.elts):
                    out.setdefault(tgt.id, tuple(vals))
            if isinstance(tgt, ast.Name) and tgt.id == "DEFAULT_APP_KEY" and isinstance(getattr(node, "value", None), ast.Constant):
                out["DEFAULT_APP_KEY"] = (node.value.value,)
        return out
    mcad, dyna, ecad = tuples(ad / "mcad.py"), tuples(ad / "dyna.py"), tuples(ad / "ecad.py")
    reg = (ad / "registry.py").read_text(encoding="utf-8")
    assert 'kind="mcad", app_key="heax-step_forge"' in reg and 'kind="dyna", app_key="heax-kooremapper_mcp"' in reg
    dyna_result = ()
    for node in ast.walk(ast.parse((ad / "dyna.py").read_text(encoding="utf-8"))):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "required_tools" for t in node.targets) \
                and isinstance(node.value, ast.Tuple):
            dyna_result = tuple(e.value for e in node.value.elts)
    pairs = {("heax-step_forge", t) for t in mcad["REQUIRED_TOOLS"]}
    pairs |= {("heax-kooremapper_mcp", t) for t in dyna["REQUIRED_TOOLS"] + dyna["CORPUS_TOOLS"] + dyna_result}
    pairs |= {(ecad["DEFAULT_APP_KEY"][0], t) for t in ecad["REQUIRED_TOOLS"]}
    return pairs


def test_형제_리포_리스크_앱_어댑터의_목록과_같다():
    risk = ROOT.parent / "HWAXRisk"
    if not (risk / "backend/app/adapters/registry.py").is_file():
        pytest.skip("형제 리포 HWAXRisk 가 없다")
    mine = {(b, t) for b, tools in rcr.PAIRS for t in tools}
    theirs = _risk_adapter_pairs(risk)
    assert mine == theirs, f"어긋남 — 여기만 {sorted(mine - theirs)} · 리스크 앱만 {sorted(theirs - mine)}"
