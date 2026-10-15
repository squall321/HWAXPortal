# 심층 보기의 지식카드 칸 — 빈 카드 안내·긴 카드 이어 읽기·검색칸 문구가 에이전트서버 응답과 맞는지(프론트 소스 대조)
"""읽기 칸은 에이전트서버 /catalog/record 응답을 그린다(docs/request_1015.md K1·K3·K5).

  sections·table·truncated        종전부터
  total_sections·total_chars      카드 전체(블록을 푼 절 기준 · RAG 절로 채웠으면 그 절 기준) 총량 — 없으면 구 서버
  next {section, char} | null     이어 읽을 위치. char > 0 이면 다음 쪽 첫 절은 앞 쪽 마지막 절의 뒷부분이다

프런트 전용이라 소스 지점을 본다. 이어 붙이는 동작 자체는 임시 진입점으로 화면에서 확인했다(이 시험의 몫이 아니다).
"""
from pathlib import Path

_FRONT = Path(__file__).resolve().parents[2] / "frontend" / "src"


def _view() -> str:
    return (_FRONT / "components" / "chat" / "AgentDeepView.tsx").read_text("utf-8")


# ── K1-3 빈 카드 ──────────────────────────────────────────────────────────────────────────────
def test_글이_하나도_없는_카드는_비어_있다고_말한다():
    """절이 0개일 때만 안내가 떠서, 제목만 늘어선 카드(MX 백서 427장)가 다 불러온 카드처럼 보였다. [].every 는 true 라
    에이전트서버가 빈 카드를 절 0개로 주는 지금 경우도 그대로 덮는다."""
    src = _view()
    assert ('{rec.sections.every((s) => !s.text) && !rec.table && '
            '<p className="pv-empty">본문이 비어 있는 카드입니다.</p>}') in src
    assert "rec.sections.length === 0 && !rec.table" not in src


# ── K3 긴 카드 — 총량을 말하고 다음 부분을 이어 읽는다 ─────────────────────────────────────────────────
def _api() -> str:
    return (_FRONT / "api" / "chat.api.ts").read_text("utf-8")


def test_카드_응답_타입이_총량과_다음_위치를_받는다():
    api = _api()
    blk = api[api.index("export interface RecordView"):]
    blk = blk[:blk.index("\n}\n")]
    for field in ("total_sections?: number;", "total_chars?: number;", "next?: { section: number; char: number } | null;"):
        assert f"\n  {field}" in blk, f"RecordView 에 {field} 가 없다"


def test_다음_부분은_앞_응답의_next_를_그대로_돌려보낸다():
    api = _api()
    assert "export function fetchRecord(id: string, at?: { section: number; char: number }): Promise<RecordView> {" in api, (
        "이어 읽을 위치를 받지 않으면 6만 자 뒤를 영영 못 본다")
    fn = api[api.index("export function fetchRecord"):]
    fn = fn[:fn.index("\n}\n")]
    assert "{ id, section_offset: at?.section ?? 0, char_offset: at?.char ?? 0 }" in fn


def _reader() -> str:
    src = _view()
    return src[src.index("function RecordReader"):src.index("export function AgentDeepView")]


def test_잘림_안내는_무엇이_잘렸는지_따로_말한다():
    """표가 없는 DOC 카드에도 「표는 앞 0행입니다」가 붙었다(열어 본 카드 38%). 본문은 총량 대비로, 표는 실제로 잘렸을 때만."""
    rd = _reader()
    assert "표는 앞 {nf.format(rec.table?.rows.length ?? 0)}행입니다" not in rd
    assert "const cutTable = rec.table && rec.table.total_rows > rec.table.rows.length ? rec.table : null;" in rd
    assert ("`본문 ${nf.format(rec.total_sections ?? 0)}절·${nf.format(rec.total_chars)}자 중 앞 ${nf.format(shown)}자"
            "(약 ${Math.floor((shown * 100) / rec.total_chars)}%)를 싣습니다.`") in rd
    assert "rec.next && rec.total_chars" in rd, "총량을 안 주는 구 서버면 비율을 지어내지 않는다"
    assert "cutTable ? '' : '본문이 길어 앞부분만 싣습니다.'" in rd
    assert "cutTable ? `표는 ${nf.format(cutTable.total_rows)}행 중 앞 ${nf.format(cutTable.rows.length)}행입니다.` : ''" in rd
    assert '{rec.truncated && <p className="dv-note">{note}</p>}' in rd


def test_다음_부분_보기_버튼과_실패_문구():
    rd = _reader()
    assert "function RecordReader({ rec, onMore, moreLoading, moreError }: {" in rd
    assert "{rec.next && onMore && (" in rd, "이어 읽을 위치가 없는데도 버튼을 띄우면 누를 때마다 첫 쪽이 되풀이된다"
    btn = rd[rd.index("{rec.next && onMore && ("):]
    btn = btn[:btn.index("</button>")]
    assert '<button type="button" className="pv-chip pv-chip-btn" disabled={moreLoading} onClick={onMore}>' in btn
    assert "{moreLoading ? '불러오는 중…' : '다음 부분 보기 ▼'}" in btn
    assert '{moreError && <p className="pv-empty">다음 부분을 불러오지 못했습니다({moreError}).</p>}' in rd


def test_이어_받은_쪽을_같은_카드_같은_위치에만_붙인다():
    src = _view()
    assert "const loadMore = useCallback(() => {" in src, "다음 부분을 받는 손잡이가 없다"
    fn = src[src.index("const loadMore = useCallback(() => {"):]
    fn = fn[:fn.index("}, [rec]);")]
    assert "void fetchRecord(id, at).then((more) => {" in fn
    assert "if (selRef.current !== id) return;" in fn, "다른 카드를 연 뒤 늦게 온 쪽이 그 카드에 붙으면 안 된다"
    assert "setMoreError(more.error);" in fn
    # 그사이 같은 카드를 다시 열었으면 새 첫 쪽 뒤에 엉뚱한 쪽이 붙는다 — 보낸 위치가 지금의 next 와 같을 때만 붙인다
    assert "if (!cur || cur.id !== id || cur.next?.section !== at.section || cur.next?.char !== at.char) return cur;" in fn
    # 절 중간에서 이어 받은 첫 조각은 앞 절에 붙인다 — 제목이 두 번 나오지 않게(char == 0 이면 새 절이다)
    assert "if (at.char > 0 && secs.length && add.length) {" in fn
    assert "secs.push({ ...last, text: last.text + add.shift()!.text });" in fn
    assert "return { ...cur, sections: [...secs, ...add], next: more.next ?? null, truncated: more.truncated };" in fn
    op = src[src.index("const openRecord = useCallback((id: string) => {"):]
    op = op[:op.index("}, []);")]
    assert "setMoreLoading(false);" in op and "setMoreError(null);" in op, "다른 카드를 열면 앞 카드의 이어 읽기 상태를 지운다"
    assert "<RecordReader rec={rec} onMore={loadMore} moreLoading={moreLoading} moreError={moreError} />" in src


# ── K5 검색칸 문구 ────────────────────────────────────────────────────────────────────────────
def test_검색칸은_낱말로_찾는다고_말한다():
    """AIDataHub 가 검색어를 낱말로 나눠 AND 로 건다(K5-1). 본문 검색(K5-2)은 스위치 뒤 기본 끔이라(사용자 결정 10-15)
    지금 동작대로 '제목·요약' 만 말한다 — 켜는 박스가 생기면 이 문구도 '제목·요약·본문' 으로 바꾼다."""
    src = _view()
    assert 'placeholder="제목·요약에서 낱말로 찾기"' in src
    assert "카드 제목·요약으로 찾기" not in src
