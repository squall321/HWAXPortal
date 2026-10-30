# update-all 7) 의 챗 도구 가시성 — 에이전트 서버 /health 의 tool_cut(마지막 챗 턴의 스키마 예산 절단)을 '챗 도구 절단' 줄로 말하는지
"""왜 — 챗이 stcx(창 262,144)로 바뀐 뒤 TOOL_MAX=0 인데도 스키마 예산(창의 45%)에서 678개 중 226개가 잘렸는데, 헬스게이트는
'TOOL_MAX=0 → 게이트웨이 N개 전부 바인딩 가능' 이라고만 했다(수정 제안서 F3). 이제 에이전트 서버가 마지막 절단을 /health 에 싣는다
(HWAXAgentServer 2806672). 원문 구획(파이썬 heredoc)을 그대로 떼어 돌린다. 챗 스모크 한도도 본다(생각 켬 — 60초면 정상 챗이 실패로 찍힌다).
"""
import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")


GATE_CALL = 'AH="$AH" GH="$(gw_health 2>/dev/null || true)" CTSB="$_ctsb" TSB="$_tsb" python3 - <<\'PY\' || true\n'


def _gate_py() -> str:
    i = SRC.index(GATE_CALL)
    i = SRC.index("\n", i) + 1
    return SRC[i:SRC.index("\nPY\n", i)]


def _run(ah: dict, gh: dict, **knobs) -> str:
    """knobs — CTSB · TSB(에이전트 서버 .env 의 CHAT_TOOL_SCHEMA_BUDGET · TOOL_SCHEMA_BUDGET 을 구획이 넘기는 이름)."""
    env = {k: v for k, v in os.environ.items() if k not in ("CTSB", "TSB")}
    r = subprocess.run(["python3", "-c", _gate_py()], capture_output=True, text=True, timeout=30,
                       env={**env, "AH": json.dumps(ah), "GH": json.dumps(gh), **knobs})
    assert r.returncode == 0, r.stderr
    return r.stdout


def test_절단이_있으면_뺀_수와_앱을_말한다():
    out = _run({"tool_max": 0, "tool_cut": {"before": 678, "after": 452, "budget": 117964,
                                           "dropped_apps": {"MaterialTwin Web": 34, "StepForge": 150}}},
               {"tools": 678})
    assert "게이트웨이 678개 — 도구 설명 예산 117,964토큰(챗 창의 45%) 안에서 질의 관련도 순으로 싣는다" in out, out
    assert "⚠ 챗 도구 절단: 마지막 챗 턴에서 678개 중 452개만 실었다(스키마 상한 117,964토큰 — 챗 창의 45%)" in out, out
    assert "MaterialTwin Web 34 · StepForge 150" in out and "안내대(search_tools · invoke_tool)" in out
    # '전부 바인딩' · GLM 권고 · '챗 서버 창을 넓힌다' 는 걷었다 — 예산을 값으로 정한 박스에서 틀린 말이다(docs/request-1030 HP-55).
    assert "전부 바인딩" not in out and "GLM" not in out and "창을 넓힌다" not in out, out


def test_HP55_예산의_값과_출처를_말한다():
    """챗 도구 줄 · 절단 줄이 /health tool_cut 의 budget 과 그 출처를 말한다(docs/request-1030 HP-55). 출처는 에이전트 서버 _select_tools 의
    규칙이다 — 캡이 안 걸리는 길은 CHAT_TOOL_SCHEMA_BUDGET 이 있으면 그 값, 없으면 챗 창의 45%, 캡 길은 TOOL_SCHEMA_BUDGET. /health 는 값만
    싣으므로 손잡이 값과 같은지로 가른다. 수는 cae00 10-30 실측(1,379 → 209, 88,473)과 O-3 · OB-93 의 견줄 값(30,000)이다."""
    cut = {"before": 1379, "after": 209, "budget": 88473, "dropped_apps": {"StepForge": 150}}
    out = _run({"tool_max": 0, "tool_cut": cut}, {"tools": 1412})
    assert "도구 설명 예산 88,473토큰(챗 창의 45%) 안에서" in out and "(스키마 상한 88,473토큰 — 챗 창의 45%)" in out, out
    # 손잡이를 적고 재기동했다 — 절단의 상한이 그 값이다
    out = _run({"tool_max": 0, "tool_cut": {**cut, "after": 140, "budget": 30000}}, {"tools": 1412}, CTSB="30000")
    assert "도구 설명 예산 30,000토큰(CHAT_TOOL_SCHEMA_BUDGET) 안에서" in out, out
    assert "(스키마 상한 30,000토큰 — CHAT_TOOL_SCHEMA_BUDGET)" in out and "챗 창의 45%" not in out, out
    # 손잡이는 있는데 아직 절단이 없다 — 값은 손잡이 값이다
    out = _run({"tool_max": 0, "tool_cut": None}, {"tools": 1412}, CTSB="30000")
    assert "도구 설명 예산 30,000토큰(CHAT_TOOL_SCHEMA_BUDGET) 안에서" in out and "잘린 도구 없음" in out, out
    # .env 에는 적었는데 그 프로세스는 아직 옛 예산이다(재기동 전) — 절단의 값은 그 프로세스의 출처로 읽는다
    out = _run({"tool_max": 0, "tool_cut": cut}, {"tools": 1412}, CTSB="30000")
    assert "88,473토큰(챗 창의 45%)" in out and "CHAT_TOOL_SCHEMA_BUDGET" not in out, out
    # 손잡이도 절단도 없다 — 값은 모르고 출처만 말한다
    out = _run({"tool_max": 0, "tool_cut": None}, {"tools": 1412})
    assert "도구 설명 예산(챗 창의 45%) 안에서" in out, out
    # 캡 길(dev — TOOL_MAX=40 · TOOL_SCHEMA_BUDGET=12000) — 절단의 상한은 TOOL_SCHEMA_BUDGET 이다. 비면 코드 기본값 40,000 이다.
    capped = {"before": 40, "after": 31, "budget": 12000, "dropped_apps": {"StepForge": 9}}
    out = _run({"tool_max": 40, "tool_cut": capped}, {"tools": 700}, TSB="12000")
    assert "⚠ 챗 도구 캡: TOOL_MAX=40 < 게이트웨이 700개" in out and "(스키마 상한 12,000토큰 — TOOL_SCHEMA_BUDGET)" in out, out
    out = _run({"tool_max": 40, "tool_cut": {**capped, "budget": 40000}}, {"tools": 700})
    assert "(스키마 상한 40,000토큰 — TOOL_SCHEMA_BUDGET)" in out, out


def _region_s7() -> str:
    """§7 챗 도구 구획 원문 — 주석 머리부터 /health 를 읽는 if 의 fi 까지."""
    i = SRC.index("# 챗 도구 바인딩 가시성")
    j = SRC.index("\nPY\nfi\n", i) + len("\nPY\nfi\n")
    return SRC[i:j]


@pytest.mark.parametrize("agent_env,want", [
    ("CHAT_TOOL_SCHEMA_BUDGET=30000\n", "도구 설명 예산 30,000토큰(CHAT_TOOL_SCHEMA_BUDGET) 안에서"),
    ("# CHAT_TOOL_SCHEMA_BUDGET=30000\nTOOL_MAX=0\n", "도구 설명 예산(챗 창의 45%) 안에서"),     # 킷이 적는 주석 꼴은 꺼진 것이다
    (None, "도구 설명 예산(챗 창의 45%) 안에서"),                                               # 에이전트 서버 .env 를 모르는 박스
])
def test_HP55_구획이_에이전트_서버_env_의_손잡이를_넘긴다(tmp_path, agent_env, want):
    """구획(bash)을 원문 그대로 돌린다 — /health 두 곳은 대역 함수(curl · gw_health)라 실 포트를 두드리지 않고, 손잡이는 update-all 의
    _envfile_value 로 임시 에이전트 서버 .env 에서 읽는다. 손잡이를 파이썬에 넘기지 않으면 출처가 늘 '챗 창의 45%' 로 찍힌다."""
    body = _region_s7()
    assert "/home/" not in body, "구획에 실물 경로가 박혀 있다"
    envfile = SRC[SRC.index("_envfile_value() {"):SRC.index("\n}\n", SRC.index("_envfile_value() {"))] + "\n}\n"
    if agent_env is None:
        agent_line = "unset AGENT_ENV"
    else:
        (tmp_path / "agent.env").write_text(agent_env, encoding="utf-8")
        agent_line = f'AGENT_ENV="{tmp_path / "agent.env"}"'
    script = "\n".join([
        "set -uo pipefail", agent_line, envfile,
        "curl() { printf '%s' \"$STUB_AH\"; }", "gw_health() { printf '%s' \"$STUB_GH\"; }",
        body, "echo END",
    ])
    env = {"PATH": os.environ["PATH"], "HOME": str(tmp_path), "LANG": "C.UTF-8",
           "STUB_AH": json.dumps({"tool_max": 0, "tool_cut": None}), "STUB_GH": json.dumps({"tools": 1412})}
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=30, env=env)
    assert "END" in r.stdout and "unbound variable" not in r.stderr and "command not found" not in r.stderr, r.stdout + r.stderr
    assert want in r.stdout, r.stdout + r.stderr


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


def test_E7_검색_손잡이와_코어_어휘표_지문을_말하고_다르면_경고한다():
    """게이트웨이 /health 의 search_tuning · core_vocab 과 에이전트 /health 의 core_vocab(docs/request-1029 E-7 ③). 칸 꼴은 게이트웨이
    `_tuning_health` · `_core_vocab_health` 와 에이전트 `_core_vocab_health` 가 내는 그대로다."""
    gh = {"tools": 10,
          "search_tuning": {"fingerprint": "aaa111", "base": "bbb222", "switches_off": [], "synonyms": 73,
                            "overlay": {"present": True, "fingerprint": "ccc333", "changed": ["synonyms.낙하", "switches.quality"]}},
          "core_vocab": {"loaded": True, "fingerprint": "vvv000", "base": "vvv000", "overlay": {"present": False}}}
    out = _run({"tool_max": 0, "core_vocab": {"loaded": True, "fingerprint": "vvv000", "base": "vvv000", "overlay": {"present": False}}}, gh)
    assert "  · 검색 손잡이: 지문 aaa111(기본값 bbb222 · 덧씌우기 ccc333 · 건드린 칸 2개)" in out, out
    assert "  · 코어 어휘표 지문: 게이트웨이 vvv000 · 에이전트 vvv000" in out and "⚠ 코어" not in out
    out = _run({"tool_max": 0, "core_vocab": {"loaded": True, "fingerprint": "old999", "base": "old999",
                                              "overlay": {"present": True, "error": "덧씌우기를 버렸다(ValueError: …)"}}},
               {**gh, "search_tuning": {**gh["search_tuning"], "overlay": {"present": True, "error": "덧씌우기를 버렸다(TypeError: x)"}}})
    assert "⚠ 검색 손잡이: 지문 aaa111(기본값 bbb222 · 덧씌우기 ? · 건드린 칸 0개) — 덧씌우기를 버렸다(TypeError: x)" in out, out
    assert "⚠ 코어 어휘표 지문: 게이트웨이 vvv000 · 에이전트 old999 — 다르다" in out
    assert "⚠ 코어 어휘표 덧씌우기(에이전트): 덧씌우기를 버렸다(ValueError: …)" in out
    out = _run({"tool_max": 0}, {"tools": 10})
    assert "검색 손잡이" not in out and "어휘표" not in out, "옛 판(칸 없음)은 말하지 않는다"
