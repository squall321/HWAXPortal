# 화면의 그림 — 이력에 올린 그림 주소를 싣는지, 서버 사본의 답 meta(user_images)를 앞 발화에 되붙이는지, 브라우저 사본엔 주소만 남는지
"""docs/chat-depth-context T5 — 사용자 지시(10-18) "이전 대화나 심의에 넘기는 게 챗 이력뿐 아니라 올린 이미지 … 도 들어가야 한다".

  · buildHistory(…, {images: true}) — 사람 항목에 그 발화의 그림 주소(images). 끄면 종전 모양(심의 전 도우미).
  · serverMessagesToLocal — 포털이 답의 meta.user_images 에 남긴 주소를 바로 앞 사람 발화에 붙인다(다른 기기에서 연 대화).
  · 브라우저 사본(localStorage) — 주소(images)는 남기고 보낼 때의 썸네일(localImages · data URL)은 남기지 않는다(쿼터).
  · 줄이기 셈 — 긴 변 1,568px 에 맞추고 작은 그림은 키우지 않는다.

화면 코드를 CommonJS 로 옮겨 node 로 돌린다(tests/test_front_window_payload.py 의 _node).
"""
import shutil

import pytest

from tests.test_front_window_payload import _FE, _node, _msg

pytestmark = pytest.mark.skipif(
    not (_FE / "node_modules/typescript").exists() or not shutil.which("node"),
    reason="frontend node_modules(typescript) 또는 node 가 없다 — 화면 조각을 돌려 볼 수 없다",
)

URL = "/agent/artifacts/0a1b2c3d4e5f60718293.png"


def test_이력은_사람_발화의_그림_주소를_싣고_끄면_종전_모양이다():
    msgs = [_msg("user", "이 응력 지도 봐", images=[URL]), _msg("assistant", "최대 432 MPa"),
            _msg("user", "그림 없는 질문", n=1)]
    got = _node(["components/chat/history.ts"],
                "const { buildHistory } = require('./components/chat/history.js');"
                " out([buildHistory(input, { evidence: true, images: true }), buildHistory(input, { evidence: true })]);", msgs)
    on, off = got
    assert on[0] == {"role": "user", "content": "이 응력 지도 봐", "images": [URL]}
    assert "images" not in on[1] and "images" not in on[2], "그림 없는 항목에 빈 칸을 늘리지 않는다"
    assert all("images" not in h for h in off), "끄면 종전 모양"


def test_서버_사본의_답_meta_의_그림을_앞_사람_발화에_되붙인다():
    server = [{"role": "user", "content": "이 그림", "ts": 1},
              {"role": "assistant", "content": "봤습니다", "ts": 2, "meta": {"user_images": [URL, 7]}},
              {"role": "user", "content": "다음", "ts": 3},
              {"role": "assistant", "content": "네", "ts": 4}]
    got = _node(["api/conversations.api.ts", "state/chatStore.ts"],
                "const { serverMessagesToLocal } = require('./api/conversations.api.js');"
                " out(serverMessagesToLocal(input).map(m => ({ role: m.role, images: m.images || null })));", server)
    assert got == [{"role": "user", "images": [URL]}, {"role": "assistant", "images": None},
                   {"role": "user", "images": None}, {"role": "assistant", "images": None}], "주소 꼴이 아닌 값(7)은 버린다"


def test_브라우저_사본엔_주소만_남고_썸네일은_남지_않는다():
    conv = {"id": "c1", "title": "t", "createdAt": 1, "updatedAt": 2,
            "messages": [_msg("user", "봐", images=[URL], localImages=["data:image/png;base64,AAAA"]),
                         _msg("assistant", "네")]}
    got = _node(["state/chatStore.ts"],
                "const S = require('./state/chatStore.js'); S.saveConversations([input]);"
                " const raw = JSON.parse(localStorage.getItem('hwax.chat.conversations'));"
                " const back = S.loadConversations();"
                " out({ stored: raw[0].messages[0], loaded: back[0].messages[0] });", conv)
    assert got["stored"].get("images") == [URL] and "localImages" not in got["stored"], got["stored"]
    assert got["loaded"]["images"] == [URL] and "localImages" not in got["loaded"]


def test_줄이기는_긴_변을_맞추고_작은_그림은_키우지_않는다():
    got = _node(["components/chat/imageAttach.ts"],
                "const I = require('./components/chat/imageAttach.js');"
                " out([I.fitSize(3136, 1568), I.fitSize(800, 600), I.isImageFile({ name: 'a.PNG', type: '' }),"
                " I.isImageFile({ name: 'a.txt', type: 'text/plain' }), I.dataUrlBytes('data:image/png;base64,AAAA'),"
                " I.dataUrlBytes('data:image/png;base64,AA==')])", None)
    assert got[0] == {"w": 1568, "h": 784, "scaled": True}
    assert got[1] == {"w": 800, "h": 600, "scaled": False}
    assert got[2] is True and got[3] is False
    assert got[4] == 3 and got[5] == 1
