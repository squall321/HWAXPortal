# 새 앱 점검(update-all §6) — 처음 본 앱을 적고 붙은 지 14일 동안 영역 · 권한 행 · 이름 겹침 · 인자 설명을 짚는지(docs/request-1029 E-6)
"""스크립트는 실제로 돌린다(입력 · 기록은 임시 파일). update-all 블록은 원문을 떼어 ok · bad 를 셸 함수로 갈아 돌린다 — 실물 게이트웨이 ·
포털을 치지 않고, 기록은 임시 SELF_REPO 의 infra/.state 에만 쓴다."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "infra" / "scripts" / "app-checks.py"
UA = (ROOT / "infra" / "scripts" / "update-all.sh").read_text(encoding="utf-8")
NOW = 1_793_000_000
DAY = 86400


def _tmap(*, new_app: bool = True, unclassified=("newtool_b",), clash=True, described=1, threshold=0.3, new_tools=True) -> dict:
    """게이트웨이 /tools-map 꼴 — map · apps · areas · unclassified · arg_scores."""
    m = {"list_parts": "heax-step_forge", "signalforge_get_material" if clash else "get_material": "signalforge",
         "search_tools": "_gateway"}
    apps = [{"app": "heax-step_forge", "label": "StepForge", "description": "", "tool_count": 1, "reachable": True},
            {"app": "signalforge", "label": "SignalForge VOC", "description": "", "tool_count": 1, "reachable": True},
            {"app": "_gateway", "label": "게이트웨이", "description": "", "tool_count": 1, "reachable": True}]
    rows = [{"app": "heax-step_forge", "tools": 1, "args": 4, "described": 0, "unit_or_range": 0, "described_ratio": 0.0,
             "unit_or_range_ratio": 0.0, "worst": [{"tool": "list_parts", "args": 4, "described": 0}]}]
    if new_app:
        if new_tools:
            m.update({"newtool_a": "heax-new_app", "newtool_b": "heax-new_app",
                      ("heaxnew_app_get_material" if clash else "get_material_v2"): "heax-new_app"})
        apps.append({"app": "heax-new_app", "label": "새 앱", "description": "", "tool_count": 3 if new_tools else 0,
                     "reachable": new_tools})
        if new_tools:
            rows.insert(0, {"app": "heax-new_app", "tools": 3, "args": 10, "described": described, "unit_or_range": 0,
                            "described_ratio": described / 10, "unit_or_range_ratio": 0.0,
                            "worst": [{"tool": "newtool_a", "args": 6, "described": 0}]})
    return {"map": m, "backends": sorted(set(m.values())), "apps": apps,
            "areas": {n: ("" if n in unclassified else "cad") for n in m}, "area_meta": [],
            "unclassified": sorted(n for n in m if n in unclassified),
            "arg_scores": {"threshold": threshold, "total": {}, "apps": rows}}


def _run(tmp_path, tmap: dict, *, policy=None, now=NOW, state: Path | None = None) -> tuple[int, list, Path]:
    (tmp_path / "tm.json").write_text(json.dumps(tmap, ensure_ascii=False), encoding="utf-8")
    state = state or tmp_path / "state" / "app-checks.json"
    argv = [sys.executable, str(SCRIPT), "--tools-map", str(tmp_path / "tm.json"), "--state", str(state), "--now", str(now)]
    if policy is not None:
        (tmp_path / "pol.json").write_text(json.dumps(policy), encoding="utf-8")
        argv += ["--policy", str(tmp_path / "pol.json")]
    p = subprocess.run(argv, capture_output=True, text=True, timeout=60)
    lines = [tuple(x.split("\t", 1)) for x in p.stdout.splitlines() if x]
    return p.returncode, lines, state


def _seed(tmp_path, apps: dict) -> Path:
    st = tmp_path / "state" / "app-checks.json"
    st.parent.mkdir(parents=True, exist_ok=True)
    st.write_text(json.dumps({"version": 1, "apps": apps}), encoding="utf-8")
    return st


OLD = {"heax-step_forge": 0, "signalforge": 0}
POL = {"backends": {"heax-step_forge": ["plat:x"], "signalforge": ["plat:y"]}}


def test_기록이_없던_첫_실행은_지금_앱을_전부터_있던_것으로_적기만_한다(tmp_path):
    rc, lines, st = _run(tmp_path, _tmap(described=0), policy=POL)
    assert rc == 0 and [k for k, _ in lines] == ["info"] and "기록이 없어 지금 앱 3개를 전부터 있던 것으로" in lines[0][1], lines
    assert json.loads(st.read_text())["apps"] == {"heax-new_app": 0, "heax-step_forge": 0, "signalforge": 0}, "게이트웨이 자체는 앱이 아니다"


def test_새_앱은_넷을_짚는다(tmp_path):
    """**이 시험이 이 점검의 이유다** — 영역 없음 · 권한 행 없음 · 이름 겹침 · 인자 설명 부족."""
    rc, lines, st = _run(tmp_path, _tmap(), policy=POL, state=_seed(tmp_path, OLD))
    warns = [t for k, t in lines if k == "warn"]
    assert rc == 0 and len(warns) == 4, lines
    assert all(t.startswith("새 앱 새 앱(heax-new_app, 붙은 지 0일) — ") for t in warns), warns
    assert any("영역 없는 도구 1/3개" in t and '"heax-new_app": "<영역>"' in t for t in warns)
    assert any("포털 권한표에 행이 없다" in t for t in warns)
    assert any("이름 겹침 1개 — get_material(signalforge)" in t for t in warns), "다른 앱의 같은 원래 이름을 댄다"
    assert any("인자 설명 1/10개(10%) — 기준 30% 미만 · 가장 나쁜 도구 newtool_a(인자 6개 중 설명 0개)" in t for t in warns)
    assert json.loads(st.read_text())["apps"]["heax-new_app"] == NOW, "처음 본 시각을 적는다"
    assert not any("StepForge" in t for _, t in lines), "옛 앱(전부터 있던 것)은 인자 설명이 0% 여도 짚지 않는다"


def test_이상_없는_새_앱은_초록_한_줄(tmp_path):
    pol = {"backends": {**POL["backends"], "heax-new_app": ["plat:z"]}}
    rc, lines, _ = _run(tmp_path, _tmap(unclassified=(), clash=False, described=9), policy=pol, state=_seed(tmp_path, OLD))
    assert rc == 0 and lines[-1] == ("ok", "새 앱 새 앱(heax-new_app, 붙은 지 0일) — 도구 3개 · 영역 · 권한 행 · 이름 · 인자 설명 이상 없음"), lines


def test_붙은_지_14일_동안은_실행마다_짚고_그_뒤에는_조용하다(tmp_path):
    st = _seed(tmp_path, {**OLD, "heax-new_app": NOW})
    _, lines, _ = _run(tmp_path, _tmap(), policy=POL, now=NOW + 13 * DAY, state=st)
    assert sum(k == "warn" for k, _ in lines) == 4 and "붙은 지 13일" in lines[1][1], "한 번 놓친 경고가 다음 실행에도 보인다"
    _, lines, _ = _run(tmp_path, _tmap(), policy=POL, now=NOW + 14 * DAY, state=st)
    assert lines == [("ok", "새 앱 점검 — 붙은 지 14일 안의 앱이 없다(앱 3개)")], lines


def test_정책을_못_읽었으면_권한_행은_건너뛰고_기준_0_이면_인자_설명을_안_본다(tmp_path):
    _, lines, _ = _run(tmp_path, _tmap(threshold=0), state=_seed(tmp_path, OLD))
    warns = [t for k, t in lines if k == "warn"]
    assert len(warns) == 2 and not any("권한표" in t or "인자 설명" in t for t in warns), warns


def test_도구가_아직_없는_새_앱은_다음_실행에_다시_본다(tmp_path):
    rc, lines, _ = _run(tmp_path, _tmap(new_tools=False), policy=POL, state=_seed(tmp_path, OLD))
    assert rc == 0 and lines[-1][0] == "info" and "도구가 아직 없다" in lines[-1][1] and not any(k == "warn" for k, _ in lines), lines


def test_기록이_깨졌으면_알리고_전부터_있던_것으로_다시_적는다(tmp_path):
    st = tmp_path / "state" / "app-checks.json"
    st.parent.mkdir(parents=True)
    st.write_text("{깨진", encoding="utf-8")
    rc, lines, _ = _run(tmp_path, _tmap(), policy=POL, state=st)
    assert rc == 0 and lines == [("warn", "새 앱 점검 — 기록을 못 읽었다(JSONDecodeError) · 지금 앱 3개를 전부터 있던 것으로 다시 적는다")], lines
    assert json.loads(st.read_text())["apps"]["heax-new_app"] == 0


def test_기록을_못_쓰면_알린다(tmp_path):
    (tmp_path / "file").write_text("x")
    rc, lines, _ = _run(tmp_path, _tmap(), policy=POL, state=tmp_path / "file" / "app-checks.json")
    assert rc == 0 and lines[-1][0] == "warn" and "기록을 쓰지 못했다" in lines[-1][1], lines


def test_입력을_못_읽으면_2_와_까닭(tmp_path):
    p = subprocess.run([sys.executable, str(SCRIPT), "--tools-map", str(tmp_path / "없음.json"), "--state", str(tmp_path / "s.json")],
                       capture_output=True, text=True, timeout=60)
    assert p.returncode == 2 and p.stdout == "warn\t새 앱 점검 — 입력을 읽지 못했다(FileNotFoundError)\n", p.stdout


# ── update-all 블록 ─────────────────────────────────────────────────────────────────────────────────────────
def _block() -> str:
    i = UA.index("# ── 새 앱 점검 — 처음 본 앱을 infra/.state/app-checks.json 에")
    return UA[i:UA.index("\nfi\n", i) + 4]


def _ua(tmp_path, *, apol: str | None, script_body: str | None = None) -> tuple[str, Path]:
    repo = tmp_path / "repo"
    (repo / "infra" / "scripts").mkdir(parents=True)
    if script_body is None:
        shutil.copy(SCRIPT, repo / "infra" / "scripts" / "app-checks.py")
    else:
        (repo / "infra" / "scripts" / "app-checks.py").write_text(script_body, encoding="utf-8")
    st = repo / "infra" / ".state" / "app-checks.json"
    st.parent.mkdir(parents=True)
    st.write_text(json.dumps({"version": 1, "apps": OLD}), encoding="utf-8")
    script = "\n".join([
        "set -uo pipefail",                                     # update-all 과 같은 셸 설정
        'ok() { echo "OK:$*"; }', 'bad() { echo "BAD:$*"; }',
        f"SELF_REPO='{repo}'", "TM_OK=1", "TM=\"$(cat '" + str(tmp_path / "tm.json") + "')\"",
        *([f"_apol='{apol}'"] if apol is not None else []),
        _block(),
    ])
    (tmp_path / "tm.json").write_text(json.dumps(_tmap(), ensure_ascii=False), encoding="utf-8")
    p = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=60,
                       env={"PATH": os.environ["PATH"], "HOME": str(tmp_path)})
    assert p.returncode == 0, p.stderr
    return p.stdout, st


def test_update_all_블록은_경고를_비치명_경고로_찍고_기록을_리포의_state_에_쓴다(tmp_path):
    out, st = _ua(tmp_path, apol=json.dumps(POL))
    assert out.startswith("  · 새 앱 점검 — 붙은 지 14일 안의 앱 1개"), out
    assert out.count("BAD:새 앱 새 앱(heax-new_app") == 4 and "FAIL" not in out, out
    assert "포털 권한표에 행이 없다" in out, "위 '권한 표 대조' 가 받은 정책(_apol)을 넘긴다"
    assert "heax-new_app" in json.loads(st.read_text())["apps"]


def test_update_all_블록은_정책이_없으면_권한_행을_건너뛴다(tmp_path):
    out, _ = _ua(tmp_path, apol=None)
    assert out.count("BAD:") == 3 and "권한표" not in out, out


def test_update_all_블록은_스크립트가_실패해도_멈추지_않고_알린다(tmp_path):
    out, _ = _ua(tmp_path, apol=None, script_body="import sys\nsys.exit(3)\n")
    assert out.strip() == "BAD:새 앱 점검을 하지 못했다(rc 3) — python3 infra/scripts/app-checks.py 를 손으로 돌려 본다", out


def test_update_all_블록은_지도를_파일로_넘기고_도구_수_판정_뒤에_있다():
    b = _block()
    assert 'printf \'%s\' "$TM" > "$_acm"' in b and 'environ["TM"]' not in b, "도구 지도는 파일로(HP-06 — 128 KiB 상한)"
    assert UA.index("MCP_COUNTS=\"\"") < UA.index(b) < UA.index("SMOKE_PY="), "갱신한 지도(TM)를 읽은 뒤 · 스모크 앞"
