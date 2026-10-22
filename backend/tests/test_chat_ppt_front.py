# 챗 PPT 화면 순수 함수 — 보내기 결과를 대화 알림 · 업로드 근거 · 입력창 지시문으로 옮기는지(docs/chat-ppt A1 · A2 · A4)
"""왜 — 10-22 cae00 에서 PPT 를 AI 데이터 허브로 보낸 결과가 업로드 패널 안에서만 끝나, 「방금 변환한 것 검토해 줘」 앞에 예전 그림만
실렸고 모델은 그 그림을 검토했다. 이제 보내기가 성공하면 대화에 어시스턴트 알림 한 건이 남고(활동 기록 origin=upload), 다음 턴 이력에서
그 근거는 kind=upload 로 간다(에이전트 서버가 '사람이 올려 보낸 결과' 머리로 싣는다). 입력창에는 이름이 박힌 지시문이 들어간다.

화면 코드를 CommonJS 로 옮겨 node 로 돌린다(tests/test_front_window_payload.py 의 _node).
"""
import json
import shutil

import pytest

from tests.test_front_window_payload import _FE, _msg, _node

pytestmark = pytest.mark.skipif(not shutil.which("node") or not (_FE / "node_modules" / "typescript").exists(),
                                reason="node 또는 frontend node_modules(typescript) 가 없다")

_FILES = ["components/chat/uploadNotice.ts"]
AIDH = {"stage": "done", "destination": "aidatahub", "inbox_name": "koo.park-설계검토.pptx",
        "result": {"status": "converted", "format": "pptx", "record": {"title": "설계검토", "sections": [{"id": "s1", "text": "낙하 1.5 m"}]}}}
RA = {"stage": "done", "destination": "reportarchive", "created": True, "pages": 29, "blocks": 87, "report_id": 7,
      "title": "설계검토", "url": "/w/personal-5/reports/7", "warnings": ["p3: 차트 1개 건너뜀"], "result": {"report_id": 7}}


def _notice(filename, r):
    return _node(_FILES, "const u = require('./components/chat/uploadNotice.js');"
                         "out({ n: u.dispatchNotice(input[0], input[1], 123), ask: u.dispatchInstruction(input[1]),"
                         " link: u.reportLink(input[1]) });", [filename, r])


def test_AIDH_보내기는_inbox_이름과_초안_전부를_업로드_근거로_남긴다():
    got = _notice("설계검토.pptx", AIDH)
    n = got["n"]
    raw = json.dumps(AIDH["result"], ensure_ascii=False, separators=(",", ":"))
    assert "inbox 파일 `koo.park-설계검토.pptx`" in n["text"] and f"{len(raw):,}자" in n["text"]
    (a,) = n["activity"]
    assert a["origin"] == "upload" and a["tool"] == "convert_file" and a["ok"] is True and a["ts"] == 123
    assert json.loads(a["detail"]) == {"file": "koo.park-설계검토.pptx"}, "그 파일 이름으로 다시 부를 수 있게"
    assert json.loads(a["result_full"]) == AIDH["result"], "모델이 그 도구를 불렀을 때 받는 것과 같다 — 다시 부르지 않고 검토한다"
    assert len(a["result_preview"]) <= 221
    assert got["ask"] == ("AI 데이터 허브 inbox 파일 `koo.park-설계검토.pptx` 을 convert_file 로 변환한 초안을 검토하고, "
                          "모자란 항목은 import_record(dry_run=true)로 물어봐 줘")
    assert got["link"] is None


def test_RA_보내기는_보고서_번호와_쪽_블록_경고를_남기고_링크를_준다():
    got = _notice("설계검토.pptx", RA)
    n = got["n"]
    assert "보고서 7「설계검토」 · 29쪽 · 블록 87개 · 변환하지 못한 요소 1건" in n["text"]
    (a,) = n["activity"]
    assert a["origin"] == "upload" and a["tool"] == "create_report_draft"
    assert json.loads(a["result_full"]) == {"report_id": 7, "title": "설계검토", "pages": 29, "blocks": 87,
                                             "url": "/w/personal-5/reports/7", "warnings": ["p3: 차트 1개 건너뜀"]}
    assert got["ask"] == "Report Archive 보고서 7(「설계검토」)를 get_report_outline · get_report 로 읽고 검토해 줘"
    assert got["link"] == "/report-archive/w/personal-5/reports/7"


def test_실패나_다른_목적지는_알림도_지시문도_없다():
    for r in ({**AIDH, "stage": "failed"}, {"stage": "done", "destination": "dynaforge", "session_id": "s"},
              {"stage": "dispatched", "destination": "stepforge"}, {**AIDH, "inbox_name": ""}, {**RA, "report_id": None}):
        got = _notice("a.pptx", r)
        assert got["n"] is None and got["ask"] == "", r


def test_아주_큰_초안은_앞부분만_싣고_다시_부를_길을_적는다():
    big = {**AIDH, "result": {"record": "가" * 500_000}}
    got = _notice("큰.pptx", big)
    full = got["n"]["activity"][0]["result_full"]
    assert full.startswith('{"record":"가가') and "자 생략 — 같은 도구로 다시 부르면 전부 나온다" in full
    assert len(full) < 400_100
    assert f"{len(json.dumps(big['result'], ensure_ascii=False, separators=(',', ':'))):,}자" in got["n"]["text"], "글자 수는 원본 길이"


def test_업로드_근거는_이력에서_kind_upload_로_간다():
    up = _notice("설계검토.pptx", AIDH)["n"]
    msgs = [_msg("user", "이 그림 봐", n=1, images=["/agent/artifacts/a.png"]),
            _msg("assistant", "봤습니다", n=2, activity=[{"ts": 1, "step": "s", "tool": "lookup", "result_full": "값"}]),
            {"id": "notice", "role": "assistant", "text": up["text"], "activity": up["activity"]}]
    hist = _node(["components/chat/history.ts"],
                 "const { buildHistory } = require('./components/chat/history.js');"
                 "out(buildHistory(input, { evidence: true, images: true }));", msgs)
    assert [h["role"] for h in hist] == ["user", "assistant", "assistant"]
    assert hist[1]["evidence"] == [{"tool": "lookup", "result": "값"}], "모델이 조회한 근거에는 kind 가 없다(옛 모양 그대로)"
    (ev,) = hist[2]["evidence"]
    assert ev["kind"] == "upload" and ev["tool"] == "convert_file" and json.loads(ev["args"]) == {"file": "koo.park-설계검토.pptx"}
    assert json.loads(ev["result"]) == AIDH["result"]
