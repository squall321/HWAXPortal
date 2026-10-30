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
    assert re.search(r"import \{[^}]*\bDetailError\b[^}]*\} from './AgentFacts';", sp)


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
    assert "}, [agent.key, initialDetail, reload]);" in src, "다시 시도가 상세 effect 를 다시 돌리지 않는다"
    eff = src[src.index("const [reload, setReload] = useState(0);"):]
    eff = eff[:eff.index("}, [agent.key, initialDetail, reload]);")]
    assert "if (initialDetail && !initialDetail.error) {" in eff, "실패본을 물려받으면 상세칸의 실패가 전체 화면에도 그대로 남는다"
    assert "setDetail(null);" in eff and eff.index("setDetail(null);") < eff.index("fetchAgentDetail(agent.key)"), (
        "다시 부를 때는 불러오는 중으로 돌린다 — 안 그러면 실패 문구가 응답이 올 때까지 남는다")


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


# ── K4 시작 패널의 보유 지식 수 ───────────────────────────────────────────────────────────────────
def test_시작_패널은_미리보기가_아니라_전체_수를_센다():
    """records 는 앞 20건 미리보기다 — 2,729건인 사람이 시작 패널에서만 20건으로 보였다(761명). 전문가 목록(RecordsHeading)과
    같은 계산·같은 문구로 맞춘다. records_total 이 null(구 서버·목록 실패)이면 지금처럼 미리보기 수만 보인다."""
    sp = _src("StartPicker.tsx")
    assert "보유 지식 ({detail.records.length}건)" not in sp
    head = sp[sp.index('<div className="sp-sub sp-dim">\n'):]
    head = head[:head.index("</div>")]
    assert "보유 지식 {(detail.records_total ?? detail.records.length).toLocaleString('ko-KR')}건" in head
    assert "{(detail.records_total ?? 0) > detail.records.length && (" in head
    assert '<span className="sp-dim"> · 앞 {detail.records.length}건</span>' in head
    # 'git grep 보유 지식 (' 가 0 이어야 한다(요청서 확인) — 미리보기 수로 세는 곳이 프런트에 더 없다
    front = Path(__file__).resolve().parents[2] / "frontend" / "src"
    left = [str(p) for p in front.rglob("*.tsx") if "보유 지식 (" in p.read_text("utf-8")]
    assert not left, left


# ── K8-4 운영자의 앱이 하나도 안 붙었을 때 ─────────────────────────────────────────────────────────
def test_앱이_전부_연결_안_됐을_때만_도구로_답하지_못한다고_쓴다():
    """머리말은 늘 '도구를 직접 호출해 답합니다' 였고 바로 밑 줄은 '이 서버에 연결 안 됨' 이었다(he-sim-smarttwin, cae00).
    connected 가 null(매핑을 못 받음)이면 없다고 단정하지 않는다 — 에이전트서버 _op_missing 과 같은 규칙."""
    src = _src("AgentFacts.tsx")
    assert ("// eslint-disable-next-line react-refresh/only-export-components\n"
            "export function operatorOffline(detail: AgentDetail | null | undefined): boolean {") in src, (
        "컴포넌트가 아닌 함수를 내보내면 pnpm lint(--max-warnings 0)가 걸린다")
    fn = src[src.index("export function operatorOffline"):]
    fn = fn[:fn.index("\n}\n")]
    assert "return !!detail?.operator && apps.length > 0 && apps.every((a) => a.connected === false);" in fn
    head = src[src.index('<h4 className="pv-detail-h">'):]
    head = head[:head.index("</h4>")]
    assert "operatorOffline(detail)" in head
    assert "'MCP 운영자 — 이 서버에는 이 운영자의 앱이 연결돼 있지 않아 지금은 도구로 답하지 못합니다'" in head
    assert "'MCP 운영자 — 대화하면 이 앱의 도구를 직접 호출해 답합니다'" in head


def test_심층_보기의_빈_카드_문구도_연결_상태를_본다():
    src = _src("AgentDeepView.tsx")
    assert "import { OperatorApps, operatorOffline } from './AgentFacts';" in src
    blk = src[src.index(": detail?.operator"):]
    blk = blk[:blk.index("'연결된 지식카드가 없습니다.'")]
    assert "? operatorOffline(detail)" in blk
    assert "'지식카드가 없습니다 — 이 운영자의 앱이 이 서버에 연결돼 있지 않아 지금은 도구로도 답하지 못합니다.'" in blk
    assert "'지식카드가 없습니다 — 이 전문가는 지식카드가 아니라 앱 도구를 직접 호출해 답합니다.'" in blk


# ── HP-51(docs/request-1030) 운영자의 앱이 이 서버에 없다는 것을 보내기 전에 ───────────────────────────────────
# cae00 에서 he-sim-smarttwin 의 앱이 게이트웨이에 없는데 챗을 보낸 뒤에야 '연결돼 있지 않습니다' 주의가 떴다(DW-12). 그 주의(에이전트서버
# operator_app_missing)와 같은 판정 — 상세(/agent/catalog/agent)의 apps[].connected — 으로 고르는 자리와 입력창 알약에 단다.
def test_HP51_시작_패널도_운영자_앱_줄을_보인다():
    """조직도 · 좌석 · 심층 보기 상세칸은 OperatorApps 로 '이 서버에 연결 안 됨' 을 보였는데 시작 패널만 빠졌다."""
    sp = _src("StartPicker.tsx")
    assert re.search(r"import \{[^}]*\bOperatorApps\b[^}]*\} from './AgentFacts';", sp)
    blk = sp[sp.index('<p className="sp-dim">태그: '):]
    blk = blk[:blk.index("이런 걸 물을 수 있어요")]
    assert "<OperatorApps detail={detail} />" in blk, "태그 뒤 · 샘플 질의 앞(조직도 상세칸과 같은 자리)에 둔다"


def test_HP51_앱이_하나라도_없으면_그_앱_라벨을_준다():
    """에이전트서버 _op_missing 은 일부만 빠져도 주의를 낸다 — 다 빠졌을 때만 보는 operatorOffline 과 따로 둔다."""
    src = _src("AgentFacts.tsx")
    assert ("// eslint-disable-next-line react-refresh/only-export-components\n"
            "export function operatorGoneApps(detail: AgentDetail | null | undefined): string[] {") in src, (
        "컴포넌트가 아닌 함수를 내보내면 pnpm lint(--max-warnings 0)가 걸린다")
    fn = src[src.index("export function operatorGoneApps"):]
    fn = fn[:fn.index("\n}\n")]
    assert "if (!detail?.operator) return [];" in fn
    assert ".filter((a) => a.connected === false)" in fn, "null(매핑을 못 받음)은 없다고 단정하지 않는다 — 에이전트서버와 같은 규칙"


def test_HP51_입력창_전문가_알약이_보내기_전에_표지를_단다():
    src = _src("ExpertToggle.tsx")
    assert "import { operatorGoneApps } from './AgentFacts';" in src
    eff = src[src.index("const [gone, setGone] = useState<string[]>([]);"):]
    eff = eff[:eff.index("}, [pinnedAgent]);")]
    assert "if (!key?.startsWith('he-')) {" in eff, "운영자 키만 묻는다 — 풀의 전문가마다 상세를 부르지 않는다"
    assert "fetchAgentDetail(key)" in eff and "if (d.error) return;" in eff, "상세를 못 받으면 없다고 단정하지 않는다"
    assert "goneCache.set(key, g);" in eff and "if (alive) setGone(g);" in eff, "늦게 온 응답이 바뀐 전문가의 알약을 덮지 않는다"
    assert "${conflict || gone.length > 0 ? ' is-warn' : ''}" in src, "Thinking 충돌과 같은 표지(is-warn)를 쓴다"
    assert "이 서버 게이트웨이에 연결돼 있지 않아 그 앱 도구 없이 답합니다" in src
