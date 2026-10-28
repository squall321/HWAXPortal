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


_COMPOSER = _CHAT / "Composer.tsx"


def test_HP15_입력창의_고르기와_끌어_놓기가_서버가_준_확장자를_더한다():
    """화면 목록은 빌드 때 정해져 박스 설정 확장자(SIMFLOW_UPLOAD_EXTS)의 .x_t 를 몰랐다 — 끌어 놓으면 '붙이지 않는 형식' 이었다."""
    src = _COMPOSER.read_text("utf-8")
    assert "void fetchUploadExts().then((v) => {" in src
    assert "const acceptExts = useMemo(() => [...new Set([...ACCEPT_EXTS, ...serverExts])], [serverExts]);" in src
    assert "!acceptExts.includes(extOf(f.name))" in src and "ACCEPT_EXTS.includes(" not in src, "끌어 놓기도 같은 목록"
    assert "accept={acceptExts.map((x) => `.${x}`).join(',')}" in src and "accept={ACCEPT}" not in src, "고르기도 같은 목록"
    router = (_CHAT / "UploadRouter.tsx").read_text("utf-8")
    assert "picked === 'simflow')" in router, "SimFlow 는 문서 보내기 패널의 일반 흐름을 탄다"
