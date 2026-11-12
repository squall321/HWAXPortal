# 챗 답의 근거 블록 — 화면은 접어 보이고 정리본(보고서)에는 빼며 복사는 그대로 싣는지(사용자 요청 11-12), 세 곳의 표지 글이 에이전트 서버와 같은지
import re
from pathlib import Path

from app.agent import docx_export as dx

ROOT = Path(__file__).resolve().parents[2]
FRONT = ROOT / "frontend/src/components/chat"
AGENT_APP = ROOT.parent / "HWAXAgentServer" / "app.py"


def _block(body: str) -> str:
    # 에이전트 서버 app.py _evidence_block 의 꼴 — "\n\n---" · 표지 · 도구 줄 · (출처 없는 값 줄)
    return (body + "\n\n---\n" + dx.EVIDENCE_MARK + "\n- `get_part`(StepForge) · id=3\n- `fatigue_life`\n\n"
            "> ⚠ 다음 수치는 위 조회 결과에서 확인되지 않았습니다 — 추론이거나 계산된 값일 수 있으니 그대로 인용하지 마십시오: `99.9`")


def test_표지_글은_에이전트_서버_화면_정리본이_같다():
    ts = (FRONT / "evidence.ts").read_text(encoding="utf-8")
    m = re.search(r"export const EVIDENCE_MARK = '([^']+)'", ts)
    assert m and m.group(1) == dx.EVIDENCE_MARK
    if AGENT_APP.exists():           # 형제 리포가 곁에 없으면 화면 · 정리본 둘만 본다
        a = re.search(r'^_EVIDENCE_MARK = "([^"]+)"', AGENT_APP.read_text(encoding="utf-8"), re.M)
        assert a and a.group(1) == dx.EVIDENCE_MARK, "에이전트 서버의 근거 블록 표지가 바뀌었다 — 화면 · 정리본도 같이 고친다"


def test_정리본_원문에는_근거_블록이_빠지고_답_본문은_남는다():
    conv = {"messages": [{"role": "user", "text": "구리 두께를 낮춰도 되나"},
                         {"role": "assistant", "text": _block("결론: 12um 는 위험하다.")}]}
    tx = dx.transcript_text(conv, None)
    assert "[질문] 구리 두께를 낮춰도 되나" in tx and "[응답] 결론: 12um 는 위험하다." in tx
    assert "실제로 조회한 것" not in tx and "get_part" not in tx and "99.9" not in tx


def test_근거_블록이_없는_글은_그대로다():
    assert dx.strip_evidence("그냥 답이다.\n\n---\n다른 구분선") == "그냥 답이다.\n\n---\n다른 구분선"
    assert dx.strip_evidence(_block("본문")) == "본문"


def test_화면은_본문과_근거를_갈라_근거를_접고_복사는_원문_그대로다():
    src = (FRONT / "MessageList.tsx").read_text(encoding="utf-8")
    assert "splitEvidence(text)" in src and '<details className={`msg-evidence' in src, "근거는 접은 칸(details — 기본 닫힘)이다"
    assert "<details className={`msg-evidence${unsourced ? ' warn' : ''}`} open" not in src, "기본으로 펼치지 않는다"
    assert "<CopyAction text={msg.text} />" in src, "복사는 근거까지 담은 원문이다"
    assert "출처 없는 값 ${unsourced}건" in src, "출처 없는 값의 건수는 접혀 있어도 보인다"
