# 정밀 변환(DocForge) 화면 순수 함수 — 배달 결과를 대화 알림(변환 보고서 요약 · 모델 판독 확인 문구) · 지시문 · 링크로 옮기는지(DF-D17)
"""화면 코드를 CommonJS 로 옮겨 node 로 돌린다(tests/test_chat_ppt_front.py 와 같은 길)."""
import json
import shutil

import pytest

from tests.test_front_window_payload import _FE, _node

pytestmark = pytest.mark.skipif(not shutil.which("node") or not (_FE / "node_modules" / "typescript").exists(),
                                reason="node 또는 frontend node_modules(typescript) 가 없다")

_FILES = ["components/chat/uploadNotice.ts"]
PRECISE = {"stage": "done", "destination": "reportarchive_precise", "created": True, "job_id": "j_abc123", "report_id": 41,
           "title": "설계 검토", "url": "/w/personal-5/reports/41", "pages": 3, "blocks": 12, "dropped": 2, "model_written": 1,
           "unaccounted": 0, "fidelity": "full", "resources": 4, "warnings": [], "conversion_warnings": ["u1.e3: 경고"]}


def _notice(r):
    return _node(_FILES, "const u = require('./components/chat/uploadNotice.js');"
                         "out({ n: u.dispatchNotice(input[0], input[1], 123), ask: u.dispatchInstruction(input[1]),"
                         " link: u.reportLink(input[1]) });", ["설계검토.pptx", r])


def test_정밀_변환은_변환_보고서_요약과_모델_판독_확인을_남긴다():
    got = _notice(PRECISE)
    n = got["n"]
    assert ("보고서 41「설계 검토」 · 3쪽 · 블록 12개 · 버린 요소 2건(까닭은 변환 보고서) · 모델 판독 1건 · 무음 누락 0." in n["text"])
    assert "'모델 판독' 블록은 모델이 그림을 읽은 것이니 원본과 맞는지 확인하세요." in n["text"] and "경고 1건" in n["text"]
    (a,) = n["activity"]
    assert a["origin"] == "upload" and a["tool"] == "docforge_convert" and a["ok"] is True
    facts = json.loads(a["result_full"])
    assert facts["report_id"] == 41 and facts["model_written"] == 1 and facts["warnings"] == ["u1.e3: 경고"]
    assert got["ask"] == "Report Archive 보고서 41(「설계 검토」)를 get_report_outline · get_report 로 읽고 검토해 줘"
    assert got["link"] == "/report-archive/w/personal-5/reports/41"


def test_모델_판독이_없으면_확인_문구도_없고_PC_추출본은_충실도를_말한다():
    n = _notice({**PRECISE, "model_written": 0, "fidelity": "drm_bundle", "conversion_warnings": []})["n"]
    assert "모델 판독 0건" in n["text"] and "확인하세요" not in n["text"] and "경고" not in n["text"]
    assert "PC 추출본으로 만들어 충실도가 낮습니다" in n["text"]


def test_맡기기만_한_것은_알림이_없다():
    got = _notice({"stage": "dispatched", "destination": "reportarchive_precise", "job_id": "j_abc123"})
    assert got["n"] is None and got["ask"] == ""
