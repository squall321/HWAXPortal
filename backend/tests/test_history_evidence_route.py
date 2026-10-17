# 챗 이력 항목의 조회 근거(evidence) — 포털이 받고(합계 상한에 셈) 에이전트 서버 /chat 으로 넘기고, 심의 전 도우미에는 넘기지 않는지
"""왜 — 이력이 역할 + 글 두 칸뿐이라 다음 턴의 모델이 앞 턴에서 무엇을 조회했고 어떤 값이 나왔는지 몰랐다(docs/chat-depth-context CD-D5).
화면이 그 턴의 활동 기록에서 모은 [{tool, args, result}] 를 이력 항목에 싣는다. 근거는 글보다 크기 쉬워 합계 상한(창 하나)에 함께 센다.
"""
import pytest
from pydantic import ValidationError

from app.agent import routes as R

SRC = R.__file__ and open(R.__file__, encoding="utf-8").read()


def _req(history):
    return R.ChatRequest(message="다음 질문", history=history)


def test_근거를_받고_에이전트_서버로는_있을_때만_넘긴다():
    req = _req([{"role": "user", "content": "두께?"},
                {"role": "assistant", "content": "1.0mm",
                 "evidence": [{"tool": "stepforge_part_info", "args": '{"part": "H1"}', "result": "thickness=1.0mm"},
                              {"tool": "materialtwin_lookup", "result": "SUS301"}]}])
    out = [m.to_agent() for m in req.history]
    assert out[0] == {"role": "user", "content": "두께?"}, "근거 없는 항목은 종전 모양 그대로(빈 칸을 늘리지 않는다)"
    assert out[1]["evidence"] == [{"tool": "stepforge_part_info", "args": '{"part": "H1"}', "result": "thickness=1.0mm"},
                                  {"tool": "materialtwin_lookup", "result": "SUS301"}], "args 없는 근거는 그 칸을 싣지 않는다"
    assert '"history": [m.to_agent() for m in body.history],' in SRC, "/chat 은 to_agent 로 넘긴다"


def test_근거도_이력_합계_상한에_센다():
    half = R._WINDOW_CHARS // 2
    ok = [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a" * half,
                                             "evidence": [{"tool": "t", "result": "r" * (half - 10)}]}]
    _req(ok)
    over = [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a" * half,
                                               "evidence": [{"tool": "t", "result": "r" * (half + 10)}]}]
    with pytest.raises(ValidationError, match="이력 합계"):
        _req(over)


def test_모양이_틀린_근거는_막는다():
    with pytest.raises(ValidationError):
        _req([{"role": "assistant", "content": "a", "evidence": [{"tool": "", "result": "r"}]}])
    with pytest.raises(ValidationError):
        _req([{"role": "assistant", "content": "a", "evidence": [{"tool": "t" * 201, "result": "r"}]}])


def test_심의_전_도우미에는_근거를_넘기지_않는다():
    """전문가 고르기 · 되묻기 · 화두는 글만 본다 — 근거가 실려 와도 요청만 무거워진다."""
    assert SRC.count('"history": [m.model_dump(exclude={"evidence"}) for m in body.history]') == 3
    assert '[m.model_dump() for m in body.history]' not in SRC
