# 사람 의견(human_note) 상한이 포털과 엔진에서 뒤집히지 않았는지 — 엔진 기본값이 포털 상한보다 크면 그 차이만큼은 웹으로 못 넣는다
"""사람 의견(delib_opts.human_note)은 두 계층을 지난다.

  포털   backend/app/agent/routes.py      DelibOpts.human_note(max_length)  → 넘으면 422
  엔진   HWAXAgentServer/deliberation.py  HUMAN_NOTE_MAX(DELIB_HUMAN_NOTE_MAX) → 넘으면 자르고 카드로 알린다

둘은 **같은 값이 아니다.** 포털 8,000 은 바깥 경계이고 엔진 기본값 2,000 은 좌석 프롬프트가 감당하는
선이다 — 이 글은 매 라운드 전 좌석에 실리는데 엔진의 컨텍스트 회계에 들어 있지 않아, 기본값을 포털에
맞춰 올리면 좁은 창에서 좌석이 넘친다(docs/delib-engine-feedback D-7). 종전엔 엔진이 2,000자에서
**말없이** 잘라, 길게 쓴 사람은 전부 반영된 줄 알았다(S26U 피드백 1-11·4-4). 이제 엔진이 자르면 카드가 남는다.

그래서 지켜야 할 것은 순서 하나다 — **엔진 기본값 ≤ 포털 상한.** 뒤집히면 엔진이 '여기까지 받는다' 고
안내하는 길이(deliberate_jobs 의 limits.human_note_chars)를 웹에서는 422 로 못 넣는데, 두 숫자가 다른
리포에 있어 아무도 모른다. 엔진 기본값을 포털 상한 위로 올리려면 포털 상한을 같이 올린다.
"""
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.agent.routes import DelibOpts

_ENGINE = Path(__file__).resolve().parents[2].parent / "HWAXAgentServer" / "deliberation.py"


def _portal_cap() -> int:
    f = DelibOpts.model_fields["human_note"]
    caps = [m.max_length for m in f.metadata if getattr(m, "max_length", None) is not None]
    assert caps, "DelibOpts.human_note 에 max_length 가 없다 — 상한이 없으면 폭주 방지선도 없다"
    return caps[0]


def _engine_default() -> int:
    """엔진 기본값 — `HUMAN_NOTE_MAX = _env_int("DELIB_HUMAN_NOTE_MAX", N)` 의 N(그 박스의 환경값이 아니다)."""
    src = _ENGINE.read_text(encoding="utf-8")
    m = re.search(r'^HUMAN_NOTE_MAX\s*=\s*_env_int\("DELIB_HUMAN_NOTE_MAX",\s*(\d+)\)', src, re.M)
    assert m, ("deliberation.py 에서 HUMAN_NOTE_MAX 기본값을 못 찾았다 — 줄 모양이나 환경변수 이름"
               "(DELIB_HUMAN_NOTE_MAX)이 바뀌었으면 이 시험도 고쳐라")
    return int(m.group(1))


def test_엔진_기본값은_포털_상한을_넘지_않는다():
    # 형제 리포가 없는 박스(부분 체크아웃)에서는 건너뛴다 — 없는 파일로 실패시키지 않는다.
    if not _ENGINE.exists():
        pytest.skip(f"형제 리포 없음: {_ENGINE}")
    engine, portal = _engine_default(), _portal_cap()
    # 엔진에서 0 은 '무제한' 이다 — 어떤 포털 상한보다도 크다.
    assert engine != 0, (
        f"엔진 기본값이 0(무제한)인데 포털은 {portal:,}자에서 422 다 — 무제한은 MCP 로만 닿는다. "
        "포털 상한을 어떻게 둘지 정하고 이 시험을 고쳐라."
    )
    assert engine <= portal, (
        f"역전 — 엔진 기본값 {engine:,}자 > 포털 상한 {portal:,}자. 엔진이 받는다고 안내하는 길이를 "
        "웹에서는 422 로 못 넣는다. 엔진 기본값을 올렸으면 포털 DelibOpts.human_note 도 같이 올린다."
    )


def test_포털은_제_상한까지_그대로_중계하고_넘으면_소리_내_막는다():
    """포털은 자르지 않는다 — 자르는 일은 예산을 아는 엔진이 하고, 잘랐으면 엔진이 카드로 알린다."""
    cap = _portal_cap()
    note = "가" * cap
    assert DelibOpts(human_note=note).model_dump(exclude_none=True)["human_note"] == note
    with pytest.raises(ValidationError):
        DelibOpts(human_note=note + "나")
