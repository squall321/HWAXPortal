# 심의 사전 근거 상한이 프론트·포털·엔진 세 곳에서 같은 값인지 — 어긋나면 조용히 잘린다
"""사전 근거(delib_opts.evidence)는 세 계층을 지난다.

  프론트 frontend/src/components/chat/handoff.ts  EVID_ITEMS / EVID_ITEM_MAX
  포털   backend/app/agent/routes.py              DelibOpts.evidence(max_length)  → 넘으면 422
  엔진   HWAXAgentServer/deliberation.py          _EVID_ITEMS / _EVID_ITEM_MAX    → 넘으면 잘라 버린다

좌석 상한(test_seat_cap_contract)과 달리 이쪽은 **어긋나도 아무 신호가 없다.** 프론트가
항목을 12건만 만들면 포털이 40 을 받아도 12건만 오고, 엔진이 2,000자에서 자르면 발표자료
한 장 분량만 좌석에 간다 — 심의는 정상적으로 돌고 결론도 나온다. 틀린 줄 모른 채로.

실제로 그랬다. 종전 값(12항목 · 항목당 2,000자 · 합계 11,000자)은 챗 도구결과 몇 건을
나르려고 잡은 것이라, 추출하면 30,000~80,000자인 발표자료·보고서를 넣으면 첫 항목에서
잘렸다. 그래서 여기 숫자를 박아 둔다.
"""
import re
from pathlib import Path

from app.agent.routes import DelibOpts

_ROOT = Path(__file__).resolve().parents[2]
_ENGINE = _ROOT.parent / "HWAXAgentServer" / "deliberation.py"
_HANDOFF = _ROOT / "frontend" / "src" / "components" / "chat" / "handoff.ts"


def _portal_items() -> int:
    f = DelibOpts.model_fields["evidence"]
    caps = [m.max_length for m in f.metadata if getattr(m, "max_length", None) is not None]
    assert caps, "DelibOpts.evidence 에 max_length 가 없다 — 상한이 없으면 폭주 방지선도 없다"
    return caps[0]


def _front(const: str) -> int:
    src = _HANDOFF.read_text(encoding="utf-8")
    m = re.search(rf"^export const {const}\s*=\s*(\d+)", src, re.M)
    assert m, f"handoff.ts 에서 {const} 를 못 찾았다 — 이름이 바뀌었으면 이 테스트도 고쳐라"
    return int(m.group(1))


def _engine(const: str) -> int:
    src = _ENGINE.read_text(encoding="utf-8")
    m = re.search(rf'^{const}\s*=\s*_env_int\("[A-Z_]+",\s*(\d+)\)', src, re.M)
    assert m, f"deliberation.py 에서 {const} 기본값을 못 찾았다 — 이름이 바뀌었으면 이 테스트도 고쳐라"
    return int(m.group(1))


def test_근거_항목수_상한이_세_곳에서_같다():
    front, portal, engine = _front("EVID_ITEMS"), _portal_items(), _engine("_EVID_ITEMS")
    assert front == portal == engine, (
        f"항목수 상한 불일치 — 프론트 {front} · 포털 {portal} · 엔진 {engine}. "
        "작은 쪽에서 잘리고 잘린 사실은 아무 데도 안 남는다."
    )


def test_항목당_글자_상한이_프론트와_엔진에서_같다():
    front, engine = _front("EVID_ITEM_MAX"), _engine("_EVID_ITEM_MAX")
    assert front == engine, (
        f"항목당 상한 불일치 — 프론트 {front} · 엔진 {engine}. 프론트가 더 작으면 엔진 상한을 "
        "올려도 소용없고, 더 크면 엔진이 말없이 자른다."
    )


def test_합계_예산은_항목당_상한보다_크다():
    """예산이 항목 하나보다 작으면 문서 한 건도 못 들어간다 — 종전이 정확히 그 상태였다."""
    budget, item = _engine("_EVID_BUDGET"), _engine("_EVID_ITEM_MAX")
    assert budget >= item * 2, (
        f"합계 예산 {budget:,}자가 항목당 상한 {item:,}자의 2배 미만이다 — 문서 한 건에 "
        "근거 한 줄도 못 붙인다."
    )


def test_문서_한_건_분량이_들어간다():
    """발표자료·보고서를 추출하면 보통 30,000자를 넘는다. 이 기능의 최소 요구다."""
    assert _engine("_EVID_ITEM_MAX") >= 12000, "항목당 상한이 발표자료 한 건을 못 담는다"
    assert _engine("_EVID_BUDGET") >= 40000, "합계 예산이 문서 한 건 + 챗 근거를 못 담는다"


# ── 붙인 문서 상한 — 계층이 역전되면 **전송 자체가 422 로 죽는다** ──────────────────
# 근거 예산(위)과 달리 이쪽은 조용하지 않다. 프론트가 포털보다 큰 문서를 허용하면
# 사용자가 붙일 수는 있는데 보내는 순간 실패한다. 실제로 그 상태로 커밋된 적이 있다
# (프론트 400,000 · 포털 200,000).
_DOCATTACH = _ROOT / "frontend" / "src" / "components" / "chat" / "docAttach.ts"
_EXTRACTOR = _ROOT / "frontend" / "public" / "doc-extract" / "hwax-doc-extract.ps1"


def _portal_doc_chars() -> int:
    from app.agent.routes import ChatDocument

    f = ChatDocument.model_fields["text"]
    caps = [m.max_length for m in f.metadata if getattr(m, "max_length", None) is not None]
    assert caps, "ChatDocument.text 에 max_length 가 없다"
    return caps[0]


def _front_doc_chars() -> int:
    src = _DOCATTACH.read_text(encoding="utf-8")
    m = re.search(r"^export const DOC_CHARS_MAX\s*=\s*([\d_]+)", src, re.M)
    assert m, "docAttach.ts 에서 DOC_CHARS_MAX 를 못 찾았다"
    return int(m.group(1).replace("_", ""))


def _extractor_max_chars() -> int:
    src = _EXTRACTOR.read_text(encoding="utf-8-sig")
    m = re.search(r"\[int\]\s*\$MaxChars\s*=\s*(\d+)", src)
    assert m, "추출기에서 $MaxChars 기본값을 못 찾았다"
    return int(m.group(1))


def test_문서_상한은_뒤로_갈수록_작아지면_안_된다():
    """추출기 → 프론트 → 포털. 뒤가 작으면 그 계층에서 거절당한다."""
    ext, front, portal = _extractor_max_chars(), _front_doc_chars(), _portal_doc_chars()
    assert front <= portal, (
        f"역전 — 프론트가 {front:,}자까지 붙이게 해 놓고 포털이 {portal:,}자에서 422 를 낸다. "
        "긴 발표자료를 붙이면 전송 자체가 실패한다."
    )
    assert ext <= front, (
        f"역전 — 추출기가 {ext:,}자까지 뽑는데 프론트가 {front:,}자에서 잘라 버린다."
    )


def test_긴_발표자료_한_건이_들어간다():
    """200슬라이드급이 보통 30만~60만 자다. 이 기능의 실질 요구다."""
    assert _extractor_max_chars() >= 1_000_000, "추출기가 긴 발표자료를 통째로 못 뽑는다"
    assert _portal_doc_chars() >= 1_000_000, "포털이 긴 발표자료를 거절한다"


# ── 목적지↔앱 매핑 — 어긋나면 '지금 전문가' 추천이 조용히 안 뜬다 ──────────────────
def test_업로드_목적지가_전부_앱_매핑에_있다():
    """전문가를 고르면 그 앱이 pinnedApps 로 묶이고, 그걸로 행선지를 앞세운다.
    매핑이 빠지면 **아무 오류 없이 추천만 사라진다** — 그래서 테스트로 본다."""
    from app.agent.upload import DESTINATIONS

    src = (_ROOT / "frontend" / "src" / "components" / "chat" / "destApps.ts").read_text(encoding="utf-8")
    for dest in DESTINATIONS:
        assert re.search(rf"^\s+{re.escape(dest)}:\s*\[", src, re.M), (
            f"destApps.ts 에 '{dest}' 가 없다 — 그 목적지는 '지금 전문가' 추천이 안 뜬다"
        )


def test_k파일은_dynaforge_로_간다():
    """K파일은 챗 프롬프트로 못 나른다(수십 MB). 서버 스테이징 경로여야 한다."""
    from app.agent.upload import DESTINATIONS

    assert "k" in DESTINATIONS["dynaforge"]["exts"]
    front = (_ROOT / "frontend" / "src" / "components" / "chat" / "docAttach.ts").read_text(encoding="utf-8")
    m = re.search(r"const EXT_UPLOAD = \[([^\]]+)\]", front)
    assert m and "'k'" in m.group(1), "프론트가 .k 를 브라우저에서 읽으려 한다 — 수십 MB 가 프롬프트로 간다"
    m2 = re.search(r"const EXT_TEXT = \[([^\]]+)\]", front)
    assert m2 and "'k'" not in m2.group(1)
