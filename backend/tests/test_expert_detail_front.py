# 전문가 상세 화면이 실패·빈 전문가·운영자 연결 상태를 사실대로 말하는지 — 상세칸 셋·심층 보기·시작 패널(프론트 소스 대조)
"""상세를 못 받은 전문가가 '역할도 지식도 없는 사람' 으로 보였다(docs/request_1015.md K2). 에이전트서버 catalog_agent 는
이제 실패를 error="session_failed"·records_error="records_failed" 로 주고(성공이면 두 키가 없다), 포털은 그것을 그린다.
프론트 전용이라 소스 지점을 본다 — 세 칸 중 하나만 빠져도 그 칸은 실패를 빈 전문가로 보인다.
"""
import re
from pathlib import Path

_CHAT = Path(__file__).resolve().parents[2] / "frontend" / "src" / "components" / "chat"
_API = Path(__file__).resolve().parents[2] / "frontend" / "src" / "api" / "chat.api.ts"


def _src(name: str) -> str:
    return (_CHAT / name).read_text("utf-8")


# ── K2-3 상세칸 셋의 공용 실패 문구 ──────────────────────────────────────────────────────────────
def test_상세_응답에_목록_실패_칸이_있다():
    api = _API.read_text("utf-8")
    blk = api[api.index("export interface AgentDetail"):]
    blk = blk[:blk.index("}\n")]
    assert re.search(r"\n  records_error\?: string;", blk), "목록 실패(records_failed)를 받을 칸이 없으면 '0건' 으로 읽힌다"


def test_공용_실패_문구가_상세와_목록_실패를_가른다():
    src = _src("AgentFacts.tsx")
    assert "export function DetailError({ detail, className = 'pv-empty' }" in src, "세 칸이 같이 쓸 실패 문구 조각이 없다"
    fn = src[src.index("export function DetailError"):]
    assert "if (detail.error) return <p className={className}>상세를 불러오지 못했습니다({detail.error}).</p>;" in fn
    assert ("<p className={className}>보유 지식을 불러오지 못했습니다({detail.records_error}) — "
            "보유 지식이 없다는 뜻이 아닙니다.</p>") in fn
    assert fn.index("detail.error") < fn.index("detail.records_error"), "둘 다 실패면 상세 실패를 말한다"


def _after_records(src: str, records_marker: str) -> str:
    """보유 지식 목록 블록이 닫힌 뒤 상세 블록이 닫히기 전까지 — 실패 문구가 놓일 자리."""
    i = src.index(records_marker)
    j = src.index("</ul>", i)
    return src[j:src.index("</>", src.index(")}", j) + 2)]


def test_세_칸_모두_목록_블록_바로_뒤에_실패_문구를_둔다():
    pb = _src("PersonaBrowser.tsx")
    assert "<DetailError detail={detail} />" in _after_records(pb, "<RecordsHeading detail={detail}")
    assert "상세를 불러오지 못했습니다({detail.error})" not in pb, "공용 조각으로 바꾼다 — 문구가 칸마다 갈리지 않게"
    sb = _src("SeatBrowser.tsx")
    assert "<DetailError detail={detail} />" in _after_records(sb, "<RecordsHeading detail={detail}"), (
        "심의 좌석 상세는 error 를 한 번도 안 읽어 이름·키·버튼만 남았다")
    assert re.search(r"import \{[^}]*\bDetailError\b[^}]*\} from './AgentFacts';", sb)
    sp = _src("StartPicker.tsx")
    assert '<DetailError detail={detail} className="sp-warn" />' in _after_records(sp, "sp-detail-list sp-scroll")
    assert "import { DetailError } from './AgentFacts';" in sp


def test_시작_패널이_고정된_전문가로_열리면_상세를_불러온다():
    """pinnedAgent 로 열면 showAgent 를 안 불러 키만 든 빈 상자가 남았다."""
    sp = _src("StartPicker.tsx")
    m = re.search(r"useEffect\(\(\) => \{\s*if \(pinnedAgent\) showAgent\(pinnedAgent\);\s*"
                  r"// eslint-disable-next-line react-hooks/exhaustive-deps\s*\}, \[\]\);", sp)
    assert m, "고정된 전문가의 상세를 여는 effect 가 없다"
    assert m.start() > sp.index("const showAgent = (key: string) => {"), "showAgent 를 정의한 뒤에 둔다"
