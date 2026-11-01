# 발표자료로 화면 순수 함수 — 단추가 설 보고서 찾기(자리 셋) · 서버 사본에서 보고서 번호 되살리기 · 잡 상태 한 줄(docs/wda-deck)
"""화면 코드를 CommonJS 로 옮겨 node 로 돌린다(test_docforge_front.py 와 같은 길).

고정하는 것.
  · 단추 자리 셋 — 심의 결과(delib.outcome) · '/보고서' 답(raReport)은 deliberation 템플릿, RA 보내기 알림(create_report_draft · docforge_convert 근거)은
    그 밖. 발표자료 알림 자신 · 도는 답 · 사람 발화 · 번호 없는 결과에는 서지 않는다.
  · 새로고침 · 다른 기기 — 서버 사본의 meta.delib_outcome · ra_report · deck.job_id 를 되살린다(종전엔 심의 결과 카드가 사라졌다).
"""
import json

import pytest

from tests.test_front_window_payload import _node, pytestmark  # noqa: F401 — 같은 도구가 없으면 같이 건너뛴다

_DECK = ["components/chat/deck.ts"]
_CONV = ["api/conversations.api.ts", "state/chatStore.ts"]


def _report(msg: dict):
    return _node(_DECK, "const d = require('./components/chat/deck.js'); out(d.deckReportOf(input));", msg)


def _ra_notice(tool: str, facts, ok=True) -> dict:
    return {"id": "a", "role": "assistant", "text": "보고서 초안을 만들었습니다",
            "activity": [{"ts": 1, "step": "Report Archive 보고서 초안(사람이 올림)", "tool": tool, "detail": "{}",
                          "result_full": facts if isinstance(facts, str) else json.dumps(facts, ensure_ascii=False),
                          "ok": ok, "origin": "upload"}]}


def test_심의_결과와_보고서_저장_답은_deliberation_템플릿이다():
    delib = {"id": "d", "role": "assistant", "text": "결정문", "delib": {"turns": [], "outcome": {"report_id": 58, "title": "심의 — x"}}}
    assert _report(delib) == {"id": 58, "title": "심의 — x", "template": "deliberation"}
    saved = {"id": "s", "role": "assistant", "text": "📄 저장", "raReport": {"id": 77, "title": "심의 — y"}}
    assert _report(saved) == {"id": 77, "title": "심의 — y", "template": "deliberation"}


def test_RA_보내기_알림은_그_밖의_템플릿이다():
    assert _report(_ra_notice("create_report_draft", {"report_id": 41, "title": "설계 검토"})) == \
        {"id": 41, "title": "설계 검토", "template": "other"}
    assert _report(_ra_notice("docforge_convert", {"report_id": "42", "title": "정밀"}))["id"] == 42


@pytest.mark.parametrize("msg", [
    {"id": "u", "role": "user", "text": "x", "raReport": {"id": 5, "title": ""}},
    {"id": "s", "role": "assistant", "text": "x", "raReport": {"id": 5, "title": ""}, "streaming": True},
    {"id": "d", "role": "assistant", "text": "x", "delib": {"outcome": {"report_id": None, "title": "t"}}},
    {"id": "z", "role": "assistant", "text": "x", "raReport": {"id": 0, "title": ""}},
    {"id": "w", "role": "assistant", "text": "발표자료를 만들었습니다", "activity": [{"ts": 1, "step": "s", "tool": "web_design_agents",
                                                                         "result_full": "{\"report_id\": 41}", "origin": "upload"}]},
    _ra_notice("create_report_draft", {"report_id": 41}, ok=False),
    _ra_notice("create_report_draft", "보고서 41 …(잘린 미리보기)"),
    _ra_notice("convert_file", {"report_id": 41}),
    {"id": "p", "role": "assistant", "text": "그냥 답"},
])
def test_단추가_서지_않는_메시지(msg):
    assert _report(msg) is None


def test_잡_상태를_한_줄로():
    got = _node(_DECK, """const d = require('./components/chat/deck.js');
out([d.deckStateText({state: 'queued', step: '', elapsed_s: 4, late: false}),
     d.deckStateText({state: 'preparing', step: '장면 구성', elapsed_s: 75, late: false}),
     d.deckStateText({state: 'rendering', step: '만드는 중', elapsed_s: 1000, late: true}),
     d.deckStateText({state: 'done', step: '끝', elapsed_s: 6, late: false}),
     d.deckStateText({state: 'failed', step: 'x', elapsed_s: 6, late: false}),
     d.deckSize(1228800), d.deckSize(500), d.deckSize(null),
     d.deckOpen({state: 'done', next: 'finish'}), d.deckOpen({state: 'done', next: null}), d.deckOpen({state: 'rendering', next: null})]);""", None)
    assert got == ["줄 서는 중 · 4초", "장면 구성 · 1분", "만드는 중 · 16분 — 오래 걸립니다", "끝", "만들지 못했습니다",
                   "1.2 MB", "1 KB", "", True, False, True]


def _local(server: list[dict]) -> list[dict]:
    return _node(_CONV, "const a = require('./api/conversations.api.js'); out(a.serverMessagesToLocal(input));", server)


TALLY = {"agree": 2, "conditional": 1, "oppose": 0, "abstain": 0, "total": 3, "responded": 3}


def test_서버_사본에서_심의_결과와_보고서_번호를_되살린다():
    got = _local([
        {"role": "user", "content": "/심의 x", "ts": 1},
        {"role": "persona", "content": "발언", "persona": "mech-a", "round": 1, "ts": 2},
        {"role": "assistant", "content": "결정문", "ts": 3,
         "meta": {"delib_outcome": {"report_id": 58, "title": "심의 — x", "tally": TALLY, "unanimous": False}}},
    ])
    out = got[-1]["delib"]["outcome"]
    assert out == {"report_id": 58, "title": "심의 — x", "tally": TALLY, "unanimous": False}
    half = _local([
        {"role": "persona", "content": "발언", "persona": "p", "round": 1, "ts": 2},
        {"role": "assistant", "content": "결정문", "ts": 3, "meta": {"delib_outcome": {"report_id": "58", "title": 7, "tally": {"total": 2}}}},
    ])[-1]["delib"]["outcome"]
    assert half == {"report_id": None, "title": "", "unanimous": False}, "반쪽 집계 · 숫자 아닌 번호는 되살리지 않는다"
    old = _local([{"role": "persona", "content": "발언", "persona": "p", "round": 1, "ts": 2},
                  {"role": "assistant", "content": "결정문", "ts": 3}])[-1]["delib"]
    assert "outcome" not in old, "옛 사본은 종전대로 없다"


def test_서버_사본에서_보고서_저장_답과_발표자료_알림의_잡을_되살린다():
    got = _local([
        {"role": "assistant", "content": "📄 저장", "ts": 1, "meta": {"ra_report": {"id": 58, "title": "심의 — x"}}},
        {"role": "assistant", "content": "발표자료를 만들었습니다", "ts": 2,
         "meta": {"activity": [{"ts": 1, "step": "s", "tool": "web_design_agents", "origin": "upload"}], "upload": True,
                  "deck": {"job_id": "a" * 32, "state": "done"}}},
        {"role": "assistant", "content": "x", "ts": 3, "meta": {"ra_report": {"id": "58"}}},
    ])
    assert got[0]["raReport"] == {"id": 58, "title": "심의 — x"}
    assert got[1]["deckJob"] == "a" * 32 and "raReport" not in got[1]
    assert "raReport" not in got[2]


def test_브라우저_사본도_보고서_번호와_잡을_잇는다():
    got = _node(["state/chatStore.ts"], """const s = require('./state/chatStore.js');
s.saveConversations(input, 'p');
out(s.loadConversations('p')[0].messages.map((m) => [m.raReport || null, m.deckJob || null]));""",
                [{"id": "c", "title": "t", "createdAt": 0, "updatedAt": 0, "serverId": "srv",
                  "messages": [{"id": "1", "role": "assistant", "text": "저장", "raReport": {"id": 58, "title": "심의 — x"}},
                               {"id": "2", "role": "assistant", "text": "알림", "deckJob": "b" * 32},
                               {"id": "3", "role": "assistant", "text": "x", "raReport": {"id": -1, "title": ""}}]}])
    assert got == [[{"id": 58, "title": "심의 — x"}, None], [None, "b" * 32], [None, None]]
