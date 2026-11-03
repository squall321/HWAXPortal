# CAD 위치 가시화 끝에서 끝까지 점검(infra/scripts/cad-figure-check.py)의 시험 — 가짜 리스크 앱 · StepForge · 게이트웨이 그림 도구로 걸음 · 읽기만 · 쓰기 문을 본다
"""docs/report-figures RF-31. 진짜 흐름은 cae00 의 실제 리스크 항목 · 개정으로만 돈다(ODB 허브 · RA 가 거기 있다). 여기서는 도구 답의 꼴을 흉내 낸다 —
risk_locate_for_section(f1.calls), section_pair_view(그림 블록 + '그림 저장 — fig_…' 표지), section_batch_result(ready), stackup_figure(job), figure_get(url · sha256)."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.util
import io
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("cad_figure_check", ROOT / "infra" / "scripts" / "cad-figure-check.py")
chk = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(chk)

BODY = b"\xff\xd8\xff-jpeg-bytes-not-real"


@pytest.fixture(autouse=True)
def _no_wait(monkeypatch):
    monkeypatch.setattr(chk, "POLL_BATCH_S", 0.0)
    monkeypatch.setattr(chk, "POLL_STACKUP_S", 0.0)


class _T:
    type = "text"

    def __init__(self, text):
        self.text = text


class _I:
    type = "image"


class _R:
    def __init__(self, data=None, images=0, error=False, extra=()):
        self.content = ([_T(json.dumps(data, ensure_ascii=False))] if data is not None else []) + [_T(t) for t in extra] + [_I() for _ in range(images)]
        self.isError = error


def _ns(**kw):
    base = dict(project="P1", finding=None, refdes="U1001", net=None, target_key=None, cluster_key=None, side=None, odb_job=None, stepforge=None,
                x=None, y=None, compare="SF-B", fold="", stackup_other="", stackup_a="", axis_a="", axis_b="", job_wait=5, ra_report="",
                mxwp_doc="", mxwp_section="")
    base.update(kw)
    return argparse.Namespace(**base)


LOCATED = {"status": "located", "mcad": {"x": 5.0, "y": 5.0, "z": 1.5, "unit": "mm"}, "planes": [{"axis": "y"}, {"axis": "x"}], "window_mm": 30.0,
           "body": {"path": "/비밀모델/main.step/ASM/U1001_BODY"}, "transform": {"status": "verified"},
           "f1": {"stepforge_project_id": "SF-A", "calls": [
               {"projects": ["SF-A"], "point": [5.0, 5.0, 1.5], "axis": "y", "window_mm": 30.0, "unit": "mm", "highlight": ["/비밀모델/main.step/ASM/U1001_BODY"]},
               {"projects": ["SF-A"], "point": [5.0, 5.0, 1.5], "axis": "x", "window_mm": 30.0, "unit": "mm", "highlight": ["/비밀모델/main.step/ASM/U1001_BODY"]}]}}
VIEW = {"rows_total": 3, "panels": [{"not_drawn_count": 0}, {"not_drawn_count": 2}], "highlight": {"unmatched": []}}


def _fake(seen, *, locate=LOCATED, batch_waits=1, stackup=None, stackup_waits=1, fig_url=True, sha_ok=True):
    state = {"batch": 0, "stack": 0, "fig": 0}

    async def call(name, args):
        seen.append((name, args))
        if name == "risk_locate_for_section":
            return _R(locate)
        if name == "section_pair_view":
            state["fig"] += 1
            return _R(VIEW, images=1, extra=[f"그림 저장 — fig_view{state['fig']} (jpeg · 100 KB) · 파일로 받기 figure_get"])
        if name == "section_batch":
            return _R({"job_id": "JB", "reused": False, "rows": len(args["rows"])})
        if name == "section_batch_result":
            state["batch"] += 1
            if state["batch"] <= batch_waits:
                return _R({"ready": False, "progress": 40})
            return _R(VIEW, images=1, extra=[f"그림 저장 — fig_row{args['row']} (jpeg · 90 KB)"])
        if name == "stackup_figure":
            if "job_id" in args:
                state["stack"] += 1
                if state["stack"] <= stackup_waits:
                    return _R({"ready": False, "progress": 20})
                return _R({"rows_total": 4}, images=1, extra=["그림 저장 — fig_stack (jpeg · 80 KB)"])
            return _R(stackup if stackup is not None else {"rows_total": 4}, images=0 if stackup is not None else 1,
                      extra=[] if stackup is not None else ["그림 저장 — fig_stack (jpeg · 80 KB)"])
        if name == "figure_get":
            sha = hashlib.sha256(BODY).hexdigest() if sha_ok else "0" * 64
            return _R({"ref": args["ref"], "tool": "section_pair_view", "mime": "image/jpeg", "bytes": len(BODY), "sha256": sha,
                       "url": f"http://127.0.0.1:9110/fig/{args['ref']}?t=v1.1.x" if fig_url else None,
                       "note": None if fig_url else "박스 안 서비스를 거쳐 와서 PC 가 쓸 주소를 모른다"})
        if name in ("figure_to_report", "figure_to_doc"):
            return _R({"ok": True})
        raise AssertionError(f"모르는 도구 {name}")
    return call


def _caller(call, writes=()):
    exposed = {(app, t): t for app, t in chk.READ_TOOLS | chk.WRITE_TOOLS}
    return chk.Caller(call, exposed, set(writes))


def _opener(url, timeout=60):
    return io.BytesIO(BODY)


def _run(call, a, tmp_path, writes=()):
    return asyncio.run(chk.run_check(_caller(call, writes), a, tmp_path, log=lambda m: None, opener=_opener))


def test_a_located_item_runs_pair_views_batch_and_fetches_every_figure(tmp_path):
    seen = []
    rep = _run(_fake(seen), _ns(), tmp_path)
    st = rep["stages"]
    assert st["locate"]["ok"] and st["pair_view"]["ok"] and st["batch"]["ok"] and st["fetch"]["ok"]
    views = [args for name, args in seen if name == "section_pair_view"]
    assert [v["axis"] for v in views] == ["y", "x"] and all(v["projects"] == ["SF-A", "SF-B"] and v["format"] == "jpg" for v in views), \
        "f1.calls 줄 그대로에 견줄 판만 더한다"
    assert [len(args["rows"]) for name, args in seen if name == "section_batch"] == [2]
    assert {f["ref"] for f in st["fetch"]["figures"]} == {"fig_view1", "fig_view2", "fig_row1", "fig_row2"}
    assert all(Path(f["path"]).read_bytes() == BODY for f in st["fetch"]["figures"])
    assert not any(name.startswith("figure_to") for name, _ in seen), "쓰기는 그 인자를 줄 때만"
    text = chk.summary_text(rep)
    assert "✗" not in text and "짝 단면(y)" in text and "그림 받기 — 4/4" in text
    assert "비밀모델" not in text and "U1001" not in text and "SF-A" not in text, "요약에는 이름 · id 가 없다"


def test_fold_is_passed_to_every_pair_view_and_batch_row(tmp_path):
    seen = []
    fold = {"axis_point": [10, 0, 2], "axis_dir": [0, 1, 0], "angle_deg": 90, "moving": ["*PLATE_3"]}
    _run(_fake(seen), _ns(fold=json.dumps(fold)), tmp_path)
    assert all(args.get("fold") == fold for name, args in seen if name == "section_pair_view")
    assert all(row.get("fold") == fold for name, args in seen if name == "section_batch" for row in args["rows"])


def test_an_unlocated_item_stops_with_the_reason_and_calls_nothing_else(tmp_path):
    seen = []
    unknown = {"status": "unknown", "reason": {"code": "transform_missing", "message": "…", "fix": "risk_propose_board_transform → risk_set_board_transform"}}
    rep = _run(_fake(seen, locate=unknown), _ns(), tmp_path)
    assert rep["stages"]["locate"] == {"ok": False, "seconds": rep["stages"]["locate"]["seconds"], "status": "unknown", "reason": "transform_missing",
                                       "fix": "risk_propose_board_transform → risk_set_board_transform", "error": None}
    assert [name for name, _ in seen] == ["risk_locate_for_section"]
    assert "까닭 transform_missing" in chk.summary_text(rep)


def test_an_old_risk_app_without_f1_calls_and_a_missing_compare_are_said(tmp_path):
    old = {**LOCATED, "f1": {"stepforge_project_id": "SF-A", "point": LOCATED["mcad"], "planes": LOCATED["planes"]}}
    assert _run(_fake([]), _ns(), tmp_path) and _run(_fake([], locate=old), _ns(), tmp_path)["stages"]["locate"]["reason"] == "no_f1_calls"
    rep = _run(_fake([]), _ns(compare=""), tmp_path)
    assert rep["stages"]["pair_view"] == {"ok": False, "why": "no_compare"}


def test_stackup_waits_on_the_self_queued_job_and_gets_the_figure(tmp_path):
    seen = []
    rep = _run(_fake(seen, stackup={"job": {"job_id": "JS", "kind": "measure"}, "job_call": {}}, stackup_waits=2),
               _ns(stackup_other="SF-C", axis_a="z", axis_b="z", job_wait=60), tmp_path)
    s = rep["stages"]["stackup"]
    assert s["ok"] and s["path"] == "job" and s["job_id"] == "JS" and s["fig_refs"] == ["fig_stack"]
    direct = [args for name, args in seen if name == "stackup_figure" and "job_id" not in args][0]
    assert direct == {"project_id": "SF-A", "other_project_id": "SF-C", "format": "jpg", "axis_a": "z", "axis_b": "z"}
    assert "fig_stack" in {f["ref"] for f in rep["stages"]["fetch"]["figures"]}


def test_stackup_job_not_queued_is_reported_not_waited(tmp_path):
    seen = []
    rep = _run(_fake(seen, stackup={"job_not_queued": "A 쪽 쌓임 축을 모른다 — axis_a 를 주거나 파트를 좁힌다", "comparable": False}),
               _ns(stackup_other="SF-C"), tmp_path)
    s = rep["stages"]["stackup"]
    assert not s["ok"] and s["path"] == "direct" and s["job_not_queued"].startswith("A 쪽")
    assert [args for name, args in seen if name == "stackup_figure" and "job_id" in args] == []
    assert "잡 안 넣음" in chk.summary_text(rep)


def test_figure_without_a_pc_address_or_with_a_wrong_hash_is_a_failed_fetch(tmp_path):
    rep = _run(_fake([], fig_url=False), _ns(), tmp_path)
    assert not rep["stages"]["fetch"]["ok"] and "PC 가 쓸 주소" in rep["stages"]["fetch"]["figures"][0]["why"]
    rep = _run(_fake([], sha_ok=False), _ns(), tmp_path)
    assert not rep["stages"]["fetch"]["ok"] and "sha256" in rep["stages"]["fetch"]["figures"][0]["why"]


def test_writes_happen_only_with_their_targets(tmp_path):
    seen = []
    rep = _run(_fake(seen), _ns(ra_report="R-9", mxwp_doc="doc-x", mxwp_section="s1"), tmp_path,
               writes={(chk.GW, "figure_to_report"), (chk.GW, "figure_to_doc")})
    to_report = [args for name, args in seen if name == "figure_to_report"]
    assert len(to_report) == 4 and all(a["report_id"] == "R-9" for a in to_report)
    assert [args["slug"] for name, args in seen if name == "figure_to_doc"] == ["doc-x"]
    assert rep["stages"]["to_report"]["ok"] and rep["stages"]["to_doc"]["ok"]


def test_caller_refuses_writes_and_unlisted_tools_before_calling():
    called = []

    async def call(name, args):
        called.append(name)
        return _R({})
    c = _caller(call)
    with pytest.raises(PermissionError):
        asyncio.run(c(chk.GW, "figure_to_report", {"ref": "x", "report_id": "y"}))
    with pytest.raises(PermissionError):
        asyncio.run(c(chk.RISK, "risk_set_board_transform", {}))
    assert called == []


def test_exposed_names_follow_tools_map_and_gateway_tools_stay_bare():
    tmap = {"map": {"risk_locate_for_section": chk.RISK, "heaxstep_forge_section_batch": chk.SF},
            "orig": {"heaxstep_forge_section_batch": "section_batch"}}
    got = chk.exposed_names(tmap)
    assert got[(chk.SF, "section_batch")] == "heaxstep_forge_section_batch" and got[(chk.RISK, "risk_locate_for_section")] == "risk_locate_for_section"

    async def call(name, args):
        return _R({"name": name})
    c = chk.Caller(call, got)
    assert chk.Reply(asyncio.run(c(chk.GW, "figure_get", {"ref": "r"}))).data == {"name": "figure_get"}


def test_main_refuses_without_an_item_a_pat_or_the_tools(monkeypatch, capsys):
    monkeypatch.setenv("HWAX_GATEWAY_PAT", "pat-not-real")
    assert chk.main(["run", "--project", "P1"]) == 2 and "항목을 하나" in capsys.readouterr().err
    assert chk.main(["run", "--project", "P1", "--refdes", "U1", "--fold", "{not json"]) == 2
    monkeypatch.delenv("HWAX_GATEWAY_PAT")
    assert chk.main(["run", "--project", "P1", "--refdes", "U1"]) == 2 and "HWAX_GATEWAY_PAT" in capsys.readouterr().err
    monkeypatch.setenv("HWAX_GATEWAY_PAT", "pat-not-real")
    monkeypatch.setattr(chk, "_tools_map", lambda base, token: {"map": {"list_projects": chk.SF}, "orig": {}})
    assert chk.main(["run", "--project", "P1", "--refdes", "U1"]) == 2
    assert "heax-hwax_risk:risk_locate_for_section" in capsys.readouterr().err
