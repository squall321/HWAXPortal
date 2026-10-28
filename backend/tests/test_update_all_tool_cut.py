# update-all 7) 의 챗 도구 가시성 — 에이전트 서버 /health 의 tool_cut(마지막 챗 턴의 스키마 예산 절단)을 '챗 도구 절단' 줄로 말하는지
"""왜 — 챗이 stcx(창 262,144)로 바뀐 뒤 TOOL_MAX=0 인데도 스키마 예산(창의 45%)에서 678개 중 226개가 잘렸는데, 헬스게이트는
'TOOL_MAX=0 → 게이트웨이 N개 전부 바인딩 가능' 이라고만 했다(수정 제안서 F3). 이제 에이전트 서버가 마지막 절단을 /health 에 싣는다
(HWAXAgentServer 2806672). 원문 구획(파이썬 heredoc)을 그대로 떼어 돌린다. 챗 스모크 한도도 본다(생각 켬 — 60초면 정상 챗이 실패로 찍힌다).
"""
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")


def _gate_py() -> str:
    i = SRC.index('AH="$AH" GH="$(gw_health 2>/dev/null || true)" python3 - <<\'PY\' || true\n')
    i = SRC.index("\n", i) + 1
    return SRC[i:SRC.index("\nPY\n", i)]


def _run(ah: dict, gh: dict) -> str:
    r = subprocess.run(["python3", "-c", _gate_py()], capture_output=True, text=True, timeout=30,
                       env={**os.environ, "AH": json.dumps(ah), "GH": json.dumps(gh)})
    assert r.returncode == 0, r.stderr
    return r.stdout


def test_절단이_있으면_뺀_수와_앱을_말한다():
    out = _run({"tool_max": 0, "tool_cut": {"before": 678, "after": 452, "budget": 117964,
                                           "dropped_apps": {"MaterialTwin Web": 34, "StepForge": 150}}},
               {"tools": 678})
    assert "게이트웨이 678개 — 스키마 예산(챗 창의 45%) 안이면 전부 바인딩" in out
    assert "⚠ 챗 도구 절단: 마지막 챗 턴에서 678개 중 452개만 실었다(스키마 상한 117,964토큰" in out
    assert "MaterialTwin Web 34 · StepForge 150" in out and "안내대(search_tools · invoke_tool)" in out


def test_절단이_없으면_없다고_하고_옛_에이전트_서버는_말하지_않는다():
    assert "잘린 도구 없음" in _run({"tool_max": 0, "tool_cut": None}, {"tools": 678})
    out = _run({"tool_max": 0}, {"tools": 678})          # tool_cut 칸이 없는 옛 판
    assert "절단" not in out and "게이트웨이 678개" in out


def test_챗_스모크는_생각하는_동안을_기다린다():
    blk = SRC[SRC.index('hr "7) 챗 스모크 (실제 응답 검증)"'):]
    blk = blk[:blk.index("\nPY\n")]
    assert "urlopen(req, timeout=900)" in blk and "timeout=60)" not in blk


def test_HP24_챗_자기검증의_수_시간_마지막_실패를_말한다():
    """에이전트 /health 의 self_check(HA-13 — on · counts · ms p50/p95 · last_error)를 §7 이 읽는다(docs/request-1027 HP-24)."""
    out = _run({"tool_max": 0, "self_check": {"on": True, "counts": {"revised": 3, "kept": 5, "failed": 1},
                                              "ms": {"n": 9, "p50": 4200, "p95": 18750},
                                              "last_error": {"status": "failed", "reason": "검토자 시간 초과", "at": 1}}},
               {"tools": 10})
    assert "⚠ 챗 자기검증: failed 1 · kept 5 · revised 3 · 4,200/18,750ms(p50/p95, 9턴) · 마지막 실패 failed: 검토자 시간 초과" in out, out
    out = _run({"tool_max": 0, "self_check": {"on": True, "counts": {"kept": 2}, "ms": {"n": 2, "p50": 10, "p95": 20},
                                              "last_error": None}}, {"tools": 10})
    assert "  · 챗 자기검증: kept 2 · 10/20ms(p50/p95, 2턴)" in out and "⚠ 챗 자기검증" not in out
    assert "챗 자기검증: 꺼짐" in _run({"self_check": {"on": False}}, {"tools": 1})
    assert "자기검증" not in _run({"tool_max": 0}, {"tools": 1}), "옛 판(칸 없음)은 말하지 않는다"
