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


# ── K2-4·K6-5 심층 보기 프로필 — 실패면 프로필 대신 다시 시도, 설명이 없으면 '아직 등록되지 않은 전문가' ──────────
def test_심층_보기는_실패한_상세를_물려받지_않고_다시_부른다():
    src = _src("AgentDeepView.tsx")
    assert "const [reload, setReload] = useState(0);" in src, "다시 시도할 손잡이가 없다"
    eff = src[src.index("const [reload, setReload] = useState(0);"):]
    eff = eff[:eff.index("}, [agent.key, initialDetail, reload]);")]
    assert "if (initialDetail && !initialDetail.error) {" in eff, "실패본을 물려받으면 상세칸의 실패가 전체 화면에도 그대로 남는다"
    assert eff.index("setDetail(null);") < eff.index("fetchAgentDetail(agent.key)"), "다시 부를 때는 불러오는 중으로 돌린다"


def test_실패하면_프로필_대신_다시_시도를_준다():
    src = _src("AgentDeepView.tsx")
    assert "{detail?.error && (" in src, "실패 문구에 다시 시도 버튼이 붙지 않았다"
    err = src[src.index("{detail?.error && ("):]
    err = err[:err.index("</p>")]
    assert "설명을 불러오지 못했습니다({detail.error}).{' '}" in err
    assert '<button type="button" className="pv-more" onClick={() => setReload((n) => n + 1)}>다시 시도</button>' in err
    assert "{detail && !detail.error && (" in src, "실패해도 프로필을 그리면 '위 설명이 전부입니다' 가 실패 문구 밑에 붙는다"
    assert "{detail && (" not in src
    # 실패본의 name 은 키다 — 제목은 전문가 목록의 이름을 쓴다
    assert "const name = (detail && !detail.error && detail.name) || agent.name;" in src


def test_설명도_역할_문서도_없으면_아직_등록되지_않은_전문가라고_쓴다():
    """위에 아무것도 없는데 '위 설명이 전부입니다' 라고 썼다(K6-5) — 화면이 덜 그려진 것으로 읽힌다."""
    src = _src("AgentDeepView.tsx")
    assert re.search(
        r"\{detail\.prompt \? \(\s*<div className=\"dv-doc\">\s*<TextBlock text=\{detail\.prompt\} />\s*</div>\s*"
        r"\) : detail\.role \? \(\s*<p className=\"pv-empty\">따로 쓴 역할 문서가 없습니다 — 위 설명이 전부입니다\.</p>\s*"
        r"\) : \(\s*<p className=\"pv-empty\">설명과 역할 문서가 아직 등록되지 않은 전문가입니다\.</p>\s*\)\}", src)
