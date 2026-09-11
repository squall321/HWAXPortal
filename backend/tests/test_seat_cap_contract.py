# 심의 좌석 상한이 엔진·포털·프론트 두 입구에서 같은 값인지 — 어긋나면 조용히 잘리거나 422 가 난다
"""좌석 상한은 네 곳에 박혀 있다.

  엔진   HWAXAgentServer/deliberation.py  MAX_REQ_SEATS        (넘으면 잘라 버린다)
  포털   backend/app/agent/routes.py      DelibOpts.personas   (넘으면 422)
  프론트 ExpertPicker.tsx                 MAX_EXPERTS          (넘게 못 고른다)
  프론트 HandoffBrief.tsx                 MAX_SEATS            (넘게 못 고른다)

한 곳만 올리면 두 가지로 샌다 — 프론트만 올리면 심의가 422 로 시작조차 안 되고, 포털까지
올리고 엔진을 빼먹으면 초과 좌석이 **소리 없이** 사라진다(종전 엔진은 cp[:12] 였다).
"""
import re
from pathlib import Path

import pytest

from app.agent.routes import DelibOpts

_ROOT = Path(__file__).resolve().parents[2]
_ENGINE = _ROOT.parent / "HWAXAgentServer" / "deliberation.py"
_CHAT = _ROOT / "frontend" / "src" / "components" / "chat"


def _portal_cap() -> int:
    f = DelibOpts.model_fields["personas"]
    caps = [m.max_length for m in f.metadata if getattr(m, "max_length", None) is not None]
    assert caps, "DelibOpts.personas 에 max_length 가 없다 — 상한이 없으면 폭주 방지선도 없다"
    return caps[0]


def _front_cap(fname: str, const: str) -> int:
    src = (_CHAT / fname).read_text(encoding="utf-8")
    m = re.search(rf"\bconst {const}\s*=\s*(\d+)", src)
    assert m, f"{fname} 에서 {const} 를 못 찾았다 — 이름이 바뀌었으면 이 테스트도 고쳐라"
    return int(m.group(1))


def test_좌석_상한은_네_곳이_같다():
    portal = _portal_cap()
    picker = _front_cap("ExpertPicker.tsx", "MAX_EXPERTS")
    brief = _front_cap("HandoffBrief.tsx", "MAX_SEATS")
    assert picker == portal, f"ExpertPicker {picker} ≠ 포털 {portal} — 넘치면 422"
    assert brief == portal, f"HandoffBrief {brief} ≠ 포털 {portal} — 넘치면 422"


def test_엔진_상한도_같다():
    # 형제 리포가 없는 박스(부분 체크아웃)에서는 건너뛴다 — 없는 파일로 실패시키지 않는다.
    if not _ENGINE.exists():
        pytest.skip(f"형제 리포 없음: {_ENGINE}")
    m = re.search(r"^MAX_REQ_SEATS\s*=\s*(\d+)", _ENGINE.read_text(encoding="utf-8"), re.M)
    assert m, "deliberation.py 에서 MAX_REQ_SEATS 를 못 찾았다"
    assert int(m.group(1)) == _portal_cap(), "엔진 상한이 다르면 초과 좌석이 소리 없이 잘린다"


def test_엔진이_상한을_하드코딩으로_자르지_않는다():
    # 상수를 만들어 놓고 옆에서 cp[:12] 같은 숫자를 또 쓰면 상수가 거짓말이 된다.
    if not _ENGINE.exists():
        pytest.skip(f"형제 리포 없음: {_ENGINE}")
    src = _ENGINE.read_text(encoding="utf-8")
    assert not re.search(r"\bcp\[:\d+\]", src), "personas 를 숫자로 자르는 곳이 남아 있다"
