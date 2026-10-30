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


GATE_CALL = ('AH="$AH" GH="$(gw_health 2>/dev/null || true)" CTSB="$_ctsb" TSB="$_tsb" AGSTALE="$_agstale"'
             ' python3 - <<\'PY\' || true\n')
# 에이전트 /health 의 창 칸 — cae00 10-30(GLM 풀 300,000 · 챗 Qwen 262,144 · 출력 몫 65,536 → 챗 턴 창 196,608 의 45% = 88,473)과
# dev(챗 전용 LLM 없음 · 16,384 의 45% = 7,372). 칸 꼴은 에이전트 서버 /health(context_tokens · chat_llm)가 내는 그대로다.
CAE00 = {"context_tokens": 300000, "chat_llm": {"enabled": True, "ctx_tokens": 262144, "output_reserve": 65536}}
DEV = {"context_tokens": 16384, "chat_llm": {"enabled": False}}


def _gate_py() -> str:
    i = SRC.index(GATE_CALL)
    i = SRC.index("\n", i) + 1
    return SRC[i:SRC.index("\nPY\n", i)]


def _run(ah: dict, gh: dict, **knobs) -> str:
    """knobs — CTSB · TSB(에이전트 서버 .env 의 CHAT_TOOL_SCHEMA_BUDGET · TOOL_SCHEMA_BUDGET) · AGSTALE(이번 실행이 에이전트 서버 재기동을
    미뤘다 — 장부) — 구획이 넘기는 이름이다."""
    env = {k: v for k, v in os.environ.items() if k not in ("CTSB", "TSB", "AGSTALE")}
    r = subprocess.run(["python3", "-c", _gate_py()], capture_output=True, text=True, timeout=30,
                       env={**env, "AH": json.dumps(ah), "GH": json.dumps(gh), **knobs})
    assert r.returncode == 0, r.stderr
    return r.stdout


def test_절단이_있으면_뺀_수와_앱을_말한다():
    # 10-18 stcx(창 262,144 · 출력 몫 없음) — 상한 117,964 가 그 창의 45% 다
    out = _run({"context_tokens": 1048576, "chat_llm": {"enabled": True, "ctx_tokens": 262144, "output_reserve": None},
                "tool_max": 0, "tool_cut": {"before": 678, "after": 452, "budget": 117964,
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
    싣으므로 값이 같은 출처를 고른다. 수는 cae00 10-30 실측(1,379 → 209, 88,473)과 O-3 · OB-93 의 견줄 값(30,000)이다."""
    cut = {"before": 1379, "after": 209, "budget": 88473, "dropped_apps": {"StepForge": 150}}
    out = _run({**CAE00, "tool_max": 0, "tool_cut": cut}, {"tools": 1412})
    assert "도구 설명 예산 88,473토큰(챗 창의 45%) 안에서" in out and "(스키마 상한 88,473토큰 — 챗 창의 45%)" in out, out
    # 손잡이를 적고 재기동했다 — 절단의 상한이 그 값이다
    out = _run({**CAE00, "tool_max": 0, "tool_cut": {**cut, "after": 140, "budget": 30000}}, {"tools": 1412}, CTSB="30000")
    assert "도구 설명 예산 30,000토큰(CHAT_TOOL_SCHEMA_BUDGET) 안에서" in out, out
    assert "(스키마 상한 30,000토큰 — CHAT_TOOL_SCHEMA_BUDGET)" in out and "챗 창의 45%" not in out, out
    # 손잡이는 있는데 아직 절단이 없다 — 값은 손잡이 값이다
    out = _run({**CAE00, "tool_max": 0, "tool_cut": None}, {"tools": 1412}, CTSB="30000")
    assert "도구 설명 예산 30,000토큰(CHAT_TOOL_SCHEMA_BUDGET) 안에서" in out and "잘린 도구 없음" in out, out
    # .env 에는 적었는데 그 프로세스는 아직 창의 45% 로 돈다(재기동 전) — 절단의 값이 그 45% 와 같다
    out = _run({**CAE00, "tool_max": 0, "tool_cut": cut}, {"tools": 1412}, CTSB="30000")
    assert "88,473토큰(챗 창의 45%)" in out and "CHAT_TOOL_SCHEMA_BUDGET" not in out, out
    # 손잡이도 절단도 없다 — 값은 모르고 출처만 말한다
    out = _run({**CAE00, "tool_max": 0, "tool_cut": None}, {"tools": 1412})
    assert "도구 설명 예산(챗 창의 45%) 안에서" in out, out
    # 캡 길(dev — TOOL_MAX=40 · TOOL_SCHEMA_BUDGET=12000) — 절단의 상한은 TOOL_SCHEMA_BUDGET 이다. 비면 코드 기본값 40,000 이다.
    capped = {"before": 40, "after": 31, "budget": 12000, "dropped_apps": {"StepForge": 9}}
    out = _run({**DEV, "tool_max": 40, "tool_cut": capped}, {"tools": 700}, TSB="12000")
    assert "⚠ 챗 도구 캡: TOOL_MAX=40 < 게이트웨이 700개" in out and "(스키마 상한 12,000토큰 — TOOL_SCHEMA_BUDGET)" in out, out
    out = _run({**DEV, "tool_max": 40, "tool_cut": {**capped, "budget": 40000}}, {"tools": 700})
    assert "(스키마 상한 40,000토큰 — TOOL_SCHEMA_BUDGET)" in out, out
    # 캡 경고는 GLM 시절의 권고(프로드는 TOOL_MAX=0 — '전부 실림')를 하지 않는다. 0 은 캡을 풀 뿐 예산 안에서 고른다(HP-55).
    assert "권장" not in out and "캡을 풀려면 TOOL_MAX=0(도구 설명 예산 안에서 질의 관련도 순으로 고른다)" in out, out


def test_HP55_값이_같은_출처가_없으면_모른다고_한다():
    """출처는 값이 같을 때만 말한다 — 종전엔 어느 손잡이와도 다르면 늘 '챗 창의 45%' 라 적어, 에이전트 서버 .env 를 40,000 → 30,000 으로
    고치거나 그 줄을 지우고 재기동을 미룬 박스(OB-93 견주기)에서 옛 40,000 을 '챗 창의 45%' 로 적었다(반대 검토). 45% 값은 에이전트 서버의
    셈(_agent_stream 의 챗 턴 창 · _select_tools 의 45% · 바닥 4,000)을 /health 의 창 칸으로 다시 한다."""
    old = {"before": 1379, "after": 260, "budget": 40000, "dropped_apps": {"StepForge": 150}}
    for knobs in ({"CTSB": "30000"}, {}):
        out = _run({**CAE00, "tool_max": 0, "tool_cut": old}, {"tools": 1412}, **knobs)
        assert "(스키마 상한 40,000토큰 — 출처 모름 · 손잡이 값 · 챗 창의 45% 88,473토큰과 다르다)" in out, out
        assert "도구 설명 예산 40,000토큰(출처 모름 · " in out and "40,000토큰(챗 창의 45%)" not in out, out
    # 이번 실행이 에이전트 서버 재기동을 미뤘다(장부) — 까닭을 붙인다
    out = _run({**CAE00, "tool_max": 0, "tool_cut": old}, {"tools": 1412}, CTSB="30000", AGSTALE="1")
    assert "88,473토큰과 다르다 · 이번 실행이 에이전트 서버 재기동을 미뤄 옛 .env 로 돈다)" in out, out
    # 절단 없이 .env 손잡이만 말할 때도 — 그 값은 아직 그 프로세스의 것이 아닐 수 있다
    out = _run({**CAE00, "tool_max": 0, "tool_cut": None}, {"tools": 1412}, CTSB="30000", AGSTALE="1")
    assert "도구 설명 예산 30,000토큰(CHAT_TOOL_SCHEMA_BUDGET — 이번 실행이 에이전트 서버 재기동을 미뤄 아직 안 실렸을 수 있다)" in out, out
    # 챗 서버 창을 아직 모른다(첫 챗 턴 전) — 45% 값도 모른다
    unknown_chat = {**CAE00, "chat_llm": {**CAE00["chat_llm"], "ctx_tokens": None}}
    out = _run({**unknown_chat, "tool_max": 0, "tool_cut": {**old, "budget": 88473}}, {"tools": 1412})
    assert "(스키마 상한 88,473토큰 — 출처 모름 · 손잡이 값과 다르다)" in out, out
    # 챗 턴 창은 두 창 중 작은 값이다(GLM 창 200,000 이 더 작으면 그것 — 134,464 의 45%) · 출력 몫은 창의 절반까지만 뗀다(100,000 − 50,000)
    out = _run({**CAE00, "context_tokens": 200000, "tool_max": 0, "tool_cut": {**old, "budget": 60508}}, {"tools": 1412})
    assert "(스키마 상한 60,508토큰 — 챗 창의 45%)" in out, out
    small = {**CAE00, "chat_llm": {**CAE00["chat_llm"], "ctx_tokens": 100000}}
    out = _run({**small, "tool_max": 0, "tool_cut": {**old, "budget": 22500}}, {"tools": 1412})
    assert "(스키마 상한 22,500토큰 — 챗 창의 45%)" in out, out
    # 챗 전용 LLM 이 없는 박스 — 창은 context_tokens 그대로다(16,384 의 45% = 7,372 · 8,192 면 바닥 4,000)
    out = _run({**DEV, "tool_max": 0, "tool_cut": {**old, "budget": 7372}}, {"tools": 700})
    assert "(스키마 상한 7,372토큰 — 챗 창의 45%)" in out, out
    out = _run({**DEV, "context_tokens": 8192, "tool_max": 0, "tool_cut": {**old, "budget": 4000}}, {"tools": 700})
    assert "(스키마 상한 4,000토큰 — 챗 창의 45%)" in out, out


def test_HP55_캡_길만_TOOL_SCHEMA_BUDGET_이다():
    """캡 길(TOOL_MAX>0 이고 도구가 그보다 많다 — 절단의 앞 수가 TOOL_MAX)의 상한은 TOOL_SCHEMA_BUDGET 이고, 캡이 안 걸린 길(같은 박스에서
    도구가 TOOL_MAX 개 이하인 사람의 턴)은 그 값을 쓰지 않는다(에이전트 서버 _select_tools). 두 손잡이가 같은 값이어도 길로 가른다 — 종전엔
    CHAT_TOOL_SCHEMA_BUDGET 을 먼저 보아 캡 길을 그 손잡이로 적었고, 캡 길의 옛 값은 '챗 창의 45%' 로 적었다(반대 검토)."""
    capped = {"before": 40, "after": 31, "budget": 12000, "dropped_apps": {"StepForge": 9}}
    under = {**capped, "before": 30, "after": 25}
    out = _run({**DEV, "tool_max": 40, "tool_cut": capped}, {"tools": 700}, CTSB="12000", TSB="12000")
    assert "(스키마 상한 12,000토큰 — TOOL_SCHEMA_BUDGET)" in out and "CHAT_TOOL_SCHEMA_BUDGET" not in out, out
    out = _run({**DEV, "tool_max": 40, "tool_cut": under}, {"tools": 700}, CTSB="12000", TSB="12000")
    assert "(스키마 상한 12,000토큰 — CHAT_TOOL_SCHEMA_BUDGET)" in out, out
    out = _run({**DEV, "tool_max": 40, "tool_cut": under}, {"tools": 700}, TSB="12000")
    assert "— TOOL_SCHEMA_BUDGET)" not in out and "(스키마 상한 12,000토큰 — 출처 모름 · " in out, out
    # 캡 길에서 TOOL_SCHEMA_BUDGET 을 고치고 재기동 전 — 옛 12,000 은 '챗 창의 45%' 가 아니다
    out = _run({**DEV, "tool_max": 40, "tool_cut": capped}, {"tools": 700}, TSB="15000")
    assert "(스키마 상한 12,000토큰 — 출처 모름 · 손잡이 값 · 챗 창의 45% 7,372토큰과 다르다)" in out, out


def test_HP55_TOOL_MAX_머리_주석이_전량_바인딩을_말하지_않는다():
    """3.5 의 TOOL_MAX 머리 주석은 사람과 에이전트가 절차로 읽는다 — 0 은 캡을 풀 뿐 도구 설명 예산 안에서 고르고(HP-55), 원격이어도 값이
    없을 때만 적는다(HP-07). GLM 시절의 '전량 바인딩' · '대형 컨텍스트라 캡을 아예 푼다' 가 남아 있었다(반대 검토)."""
    head = SRC[SRC.index("# TOOL_MAX 정리(prod)"):SRC.index("  TM=\"$(", SRC.index("# TOOL_MAX 정리(prod)"))]
    assert "전량 바인딩이 필요하면" not in head and "대형 컨텍스트)이면 캡을 아예 푼다" not in head, head


def test_HP55_45퍼센트_셈은_에이전트_서버의_셈과_같다():
    """§7 은 45% 값을 /health 의 창 칸으로 다시 셈한다 — 에이전트 서버가 셈을 바꾸면 출처가 '모름' 으로 떨어진다(틀린 출처를 말하지는
    않는다). 형제 리포가 있으면 그 셈과 /health 칸이 그대로인지 본다."""
    app = ROOT.parent / "HWAXAgentServer" / "app.py"
    if not app.is_file():
        pytest.skip(f"형제 리포 없음: {app}")
    src = app.read_text(encoding="utf-8")
    for anchor in ("budget = CHAT_TOOL_SCHEMA_BUDGET if CHAT_TOOL_SCHEMA_BUDGET > 0 else max(4000, int(_model_context_tokens() * 0.45))",
                   "win = min(chat_ctx, base_ctx)",
                   'out = max(0, int(chat_cfg.get("output_reserve") or chat_cfg.get("max_tokens") or 0))',
                   "ctx_override.set(win - min(out, win // 2))",
                   '"context_tokens": _model_context_tokens()', '"ctx_tokens": _chat_ctx_cache.get("n")',
                   '"output_reserve": out_reserve or None'):
        assert anchor in src, f"에이전트 서버 app.py 에 `{anchor}` 가 없다 — 셈이 바뀌었으면 update-all §7 의 w45 도 고친다"


def _region_s7() -> str:
    """§7 챗 도구 구획 원문 — 주석 머리부터 /health 를 읽는 if 의 fi 까지."""
    i = SRC.index("# 챗 도구 바인딩 가시성")
    j = SRC.index("\nPY\nfi\n", i) + len("\nPY\nfi\n")
    return SRC[i:j]


def _run_s7(tmp_path, agent_env: str | None, ah: dict, ledger: str | None = None) -> str:
    """구획(bash)을 원문 그대로 돌린다 — /health 두 곳은 대역 함수(curl · gw_health)라 실 포트를 두드리지 않는다. agent_env 가 None 이면
    에이전트 서버 .env 를 모르는 박스, ledger 는 이번 실행의 ○ 장부(이름 · 사유 · 켜려면 — 탭으로)다. 둘 다 임시 파일이다."""
    body = _region_s7()
    assert "/home/" not in body, "구획에 실물 경로가 박혀 있다"
    lines = ["set -uo pipefail"]
    for name, text, var in (("agent.env", agent_env, "AGENT_ENV"), ("ledger", ledger, "HWAX_SKIP_LEDGER")):
        if text is None:
            lines.append(f"unset {var}")
        else:
            (tmp_path / name).write_text(text, encoding="utf-8")
            lines.append(f'{var}="{tmp_path / name}"')
    script = "\n".join([*lines, "curl() { printf '%s' \"$STUB_AH\"; }", "gw_health() { printf '%s' \"$STUB_GH\"; }", body, "echo END"])
    env = {"PATH": os.environ["PATH"], "HOME": str(tmp_path), "LANG": "C.UTF-8",
           "STUB_AH": json.dumps(ah), "STUB_GH": json.dumps({"tools": 1412})}
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=30, env=env)
    assert "END" in r.stdout and "unbound variable" not in r.stderr and "command not found" not in r.stderr, r.stdout + r.stderr
    return r.stdout + r.stderr


@pytest.mark.parametrize("agent_env,want", [
    ("CHAT_TOOL_SCHEMA_BUDGET=30000\n", "도구 설명 예산 30,000토큰(CHAT_TOOL_SCHEMA_BUDGET) 안에서"),
    ('CHAT_TOOL_SCHEMA_BUDGET="40000"\r\nCHAT_TOOL_SCHEMA_BUDGET="30000"\r\n',          # 마지막 줄 · 따옴표 · CRLF
     "도구 설명 예산 30,000토큰(CHAT_TOOL_SCHEMA_BUDGET) 안에서"),
    ("# CHAT_TOOL_SCHEMA_BUDGET=30000\nTOOL_MAX=0\n", "도구 설명 예산(챗 창의 45%) 안에서"),     # 킷이 적는 주석 꼴은 꺼진 것이다
    ("export CHAT_TOOL_SCHEMA_BUDGET=30000\n", "도구 설명 예산(챗 창의 45%) 안에서"),          # 에이전트 서버 start.sh 가 건너뛰는 줄
    ("  CHAT_TOOL_SCHEMA_BUDGET=30000\n", "도구 설명 예산(챗 창의 45%) 안에서"),
    (None, "도구 설명 예산(챗 창의 45%) 안에서"),                                               # 에이전트 서버 .env 를 모르는 박스
])
def test_HP55_구획이_에이전트_서버가_싣는_손잡이를_넘긴다(tmp_path, agent_env, want):
    """손잡이는 에이전트 서버 start.sh 가 싣는 줄로 읽는다 — 맨 앞이 `KEY=` 인 줄의 마지막 것(따옴표 · CR 은 벗긴다). export · 들여쓴 줄은
    그 서버가 건너뛰므로 손잡이가 아니다(종전 _envfile_value 는 그 줄도 읽어 서버가 45% 로 도는데 30,000 이라 적었다 — 반대 검토).
    손잡이를 파이썬에 넘기지 않으면 출처가 늘 '챗 창의 45%' 로 찍힌다."""
    out = _run_s7(tmp_path, agent_env, {"tool_max": 0, "tool_cut": None})
    assert want in out, out


def test_HP55_구획이_TOOL_SCHEMA_BUDGET_과_재기동_미룸을_넘긴다(tmp_path):
    """캡 길의 손잡이(TOOL_SCHEMA_BUDGET)와 이번 실행이 에이전트 서버 재기동을 미뤘다는 사실(update-sites 가 장부에 적는 'agent-server 재기동
    건너뜀')을 구획이 파이썬에 넘긴다. 다른 ○ 줄 — 이름이 다르면 사유 글에 그 말이 있어도 — 은 미룸이 아니다."""
    capped = {"tool_max": 40, "tool_cut": {"before": 40, "after": 31, "budget": 12000, "dropped_apps": {"StepForge": 9}}}
    out = _run_s7(tmp_path, "TOOL_MAX=40\nTOOL_SCHEMA_BUDGET=12000\n", capped)
    assert "(스키마 상한 12,000토큰 — TOOL_SCHEMA_BUDGET)" in out, out
    deferred = "agent-server 재기동 건너뜀\t심의 1건 진행 중, 0건 대기 — 재기동하면 끊긴다\t심의가 끝난 뒤 다시 돌린다\n"
    out = _run_s7(tmp_path, "CHAT_TOOL_SCHEMA_BUDGET=30000\n", {"tool_max": 0, "tool_cut": None}, ledger=deferred)
    assert "30,000토큰(CHAT_TOOL_SCHEMA_BUDGET — 이번 실행이 에이전트 서버 재기동을 미뤄 아직 안 실렸을 수 있다)" in out, out
    others = ("llm-router 재기동 미룸\tLLM 요청 2건\t요청이 빈 뒤\n"
              "게이트웨이 재프로비저닝 건너뜀\tagent-server 재기동 건너뜀 과 같은 까닭\t심의가 끝난 뒤\n")
    out = _run_s7(tmp_path, "CHAT_TOOL_SCHEMA_BUDGET=30000\n", {"tool_max": 0, "tool_cut": None}, ledger=others)
    assert "30,000토큰(CHAT_TOOL_SCHEMA_BUDGET) 안에서" in out, out


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


def test_10_30_관문_넷과_접기를_말하고_목록을_못_읽으면_경고한다():
    """10-30 HA-27 · HA-28 · HA-29 · HA-30 · HA-34 의 /health 칸 — cae00 재시험(docs/request-1030 server-setup)이 이 줄로 켜졌는지 · 도는지 본다.
    운영자 목록을 못 읽은 확인 관문은 바닥 목록만 돌아 쓰기 도구가 카드 없이 나간다 — 그때만 ⚠."""
    ah = {"self_check": {"on": True, "counts": {"ok": 3, "fixed": 1}, "ms": {}, "fixed_ratio": 0.25,
                         "gate": {"mode": "1", "turns": 4, "raw_partial": 0,
                                  "counts": {"applied": 1, "drop_sourced_number": 2, "demote_removes_value": 1}}},
          "status_wait": {"on": True, "poll_s": 10.0, "max_s": 600.0, "waits": 2, "ended": 1, "capped": 1, "failed": 0},
          "confirm_gate": {"on": True, "lists": {"loaded": True, "error": None, "jobs": 24, "writes": 90, "confirm": 37},
                           "pending": 1, "counts": {"cards": 2, "approved": 1}},
          "xhub_gate": {"on": True, "blocked": 3}, "hub_fold": {"count": 12, "chars_in": 1250000, "chars_out": 210000}}
    out = _run(ah, {})
    assert "· 자기검증 관문: 모드 1 · 관문 턴 4 · 넣음 1 · 짚음 1 · 버림 2 · 고친 비율 0.25" in out, out
    assert "· 상태 기다림: 10.0초 간격 · 턴 합 600.0초 · 기다림 2 · 끝남 1 · 상한 1 · 실패 0" in out, out
    assert "· 확인 관문: 목록 잡 24 · 쓰기 90 · 확인 37 · 살아 있는 카드 1 · approved 1 · cards 2" in out, out
    assert "· 다른 허브 id 막이: 켬 · 막은 호출 3" in out and "· 허브 응답 접기: 12번 · 1,250,000자 → 210,000자" in out, out
    bad = {**ah, "confirm_gate": {"on": True, "lists": {"loaded": False, "error": "없음", "jobs": 24, "writes": 0, "confirm": 0},
                                  "pending": 0, "counts": {}}}
    assert "· ⚠ 확인 관문: 목록 잡 24 · 쓰기 0 · 확인 0 · 살아 있는 카드 0 · 아직 센 것 없음 — 운영자 목록을 못 읽었다(없음)" in _run(bad, {})
    off = _run({"status_wait": {"on": False}, "confirm_gate": {"on": False}, "xhub_gate": {"on": False, "blocked": 0}}, {})
    assert "상태 기다림: 꺼짐" in off and "확인 관문: 꺼짐" in off and "다른 허브 id 막이: 꺼짐(CHAT_XHUB_ID_GATE=0)" in off, off
    # 옛 판(칸 없음)은 말하지 않는다
    assert "관문" not in _run({}, {}) and "접기" not in _run({}, {})
