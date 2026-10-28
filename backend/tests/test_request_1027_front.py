# 10-27 수정 요청 — 화면 소스 지점(HP-41 챗 시작 패널의 「전체 보기 →」)
"""왜 — 챗 시작 패널(StartPicker)에서 고른 전문가의 지식카드 전체를 열 길이 없었다. 조직도 창(PersonaBrowser)에만 AgentDeepView 가 이어져
있었다(docs/request-1027 HP-41). 화면 전용이라 test_expert_detail_front.py 와 같이 소스 지점을 본다.
"""
from pathlib import Path

_CHAT = Path(__file__).resolve().parents[2] / "frontend" / "src" / "components" / "chat"


def test_HP41_시작_패널이_고른_전문가의_전체_보기를_연다():
    sp = (_CHAT / "StartPicker.tsx").read_text("utf-8")
    assert "import { AgentDeepView } from './AgentDeepView';" in sp
    assert "const selExpert = agentSel ? pool.find((a) => a.key === agentSel) : undefined;" in sp
    head = sp[sp.index('<div className="sp-detail-name">'):]
    head = head[:head.index("</div>")]
    assert "onClick={() => setDeep(true)}>전체 보기 →</button>" in head and "{selExpert && (" in head, \
        "버튼은 제목 옆이고, 풀에 그 전문가가 있을 때만 단다"
    assert "{deep && selExpert && (\n            <AgentDeepView agent={selExpert} initialDetail={detail} onClose={() => setDeep(false)} />" in sp, \
        "받아 둔 상세를 넘겨 다시 부르지 않는다(/catalog/agent 는 콜드 6~11초)"
