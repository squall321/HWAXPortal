# 심의 좌석 상한이 엔진 기본값·포털·프론트 세 입구에서 같은 값인지 — 어긋나면 조용히 잘리거나 422 가 난다
"""좌석 상한은 다섯 곳에 박혀 있다.

  엔진   HWAXAgentServer/deliberation.py  MAX_REQ_SEATS        (넘으면 잘라 버린다 · 기본값 — 아래)
  포털   backend/app/agent/routes.py      DelibOpts.personas   (넘으면 422)
  프론트 ExpertPicker.tsx                 MAX_EXPERTS          (넘게 못 고른다)
  프론트 HandoffBrief.tsx                 MAX_SEATS            (넘게 못 고른다)
  프론트 RosterEditor.tsx                 MAX_SEATS            (이어하기 좌석 조정)

한 곳만 올리면 두 가지로 샌다 — 프론트만 올리면 심의가 422 로 시작조차 안 되고, 포털까지
올리고 엔진을 빼먹으면 초과 좌석이 **소리 없이** 사라진다(종전 엔진은 cp[:12] 였다).

엔진 쪽은 이제 설정이다 — `MAX_REQ_SEATS = _env_int("DELIB_MAX_SEATS", 20)`. 실사용 팀의 21·22석
패널은 MCP 와 리스크 앱으로 들어오고 둘 다 포털 스키마를 안 거치므로, 엔진 환경값만 올리면 풀린다
(docs/delib-engine-feedback D-3). 포털 넷은 20 그대로다 — 더 좁은 쪽이어도 초과는 422 로 **소리 내**
막히니 안전하다. 그래서 여기서 대조하는 것은 엔진의 **기본값**(소스에 적힌 수)이지 그 박스의 환경값이
아니다. 기본값을 바꾸려면 포털 넷을 같이 바꾼다 — 한쪽만 바꾸면 이 시험이 어느 쪽인지 말한다.
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
    roster = _front_cap("RosterEditor.tsx", "MAX_SEATS")
    assert picker == portal, f"ExpertPicker {picker} ≠ 포털 {portal} — 넘치면 422"
    assert brief == portal, f"HandoffBrief {brief} ≠ 포털 {portal} — 넘치면 422"
    assert roster == portal, f"RosterEditor(이어하기 좌석 조정) {roster} ≠ 포털 {portal} — 넘치면 422"


def _engine_default() -> int:
    """엔진 좌석 상한의 **기본값** — `MAX_REQ_SEATS = _env_int("DELIB_MAX_SEATS", N)` 의 N.

    종전 정규식은 `MAX_REQ_SEATS = 20` 꼴만 읽어서, 엔진이 설정으로 바꾼 날부터 이 시험이 '못 찾았다' 로
    죽었다(2026-10-07). 맨 숫자 꼴도 같이 읽는다 — 되돌려도 시험이 깨지지 않게."""
    src = _ENGINE.read_text(encoding="utf-8")
    m = re.search(r'^MAX_REQ_SEATS\s*=\s*(?:_env_int\("DELIB_MAX_SEATS",\s*)?(\d+)\)?\s*(?:#.*)?$', src, re.M)
    assert m, ("deliberation.py 에서 MAX_REQ_SEATS 기본값을 못 찾았다 — 줄 모양이나 환경변수 이름"
               "(DELIB_MAX_SEATS)이 바뀌었으면 이 시험도 고쳐라")
    return int(m.group(1))


def test_엔진_기본값도_같다():
    # 형제 리포가 없는 박스(부분 체크아웃)에서는 건너뛴다 — 없는 파일로 실패시키지 않는다.
    if not _ENGINE.exists():
        pytest.skip(f"형제 리포 없음: {_ENGINE}")
    engine, portal = _engine_default(), _portal_cap()
    assert engine == portal, (
        f"좌석 상한 불일치 — 엔진 기본값 {engine} · 포털 {portal}. "
        + ("엔진 기본값을 올렸으면 포털 넷(routes.py DelibOpts.personas · ExpertPicker · HandoffBrief · "
           "RosterEditor)도 같이 올린다 — 안 올리면 웹에서는 여전히 포털 수까지만 앉는다. 한 박스에서만 "
           "더 앉히려는 것이면 기본값은 두고 환경값(DELIB_MAX_SEATS)을 올린다."
           if engine > portal else
           "포털이 엔진 기본값보다 넓다 — 포털을 통과한 초과 좌석을 엔진이 잘라 낸다(알림은 상태줄 한 줄뿐이다).")
    )


def test_포털은_상한을_넘는_좌석을_소리_내_막는다():
    """D-3 이 기대는 전제다 — 포털이 더 좁은 쪽이어도 되는 것은 초과가 422 로 드러나기 때문이다."""
    from pydantic import ValidationError

    cap = _portal_cap()
    seats = [{"key": f"mech-{i}", "role": ""} for i in range(cap + 1)]
    assert len(DelibOpts(personas=seats[:cap]).model_dump(exclude_none=True)["personas"]) == cap
    with pytest.raises(ValidationError):
        DelibOpts(personas=seats)


def test_엔진이_상한을_하드코딩으로_자르지_않는다():
    # 상수를 만들어 놓고 옆에서 cp[:12] 같은 숫자를 또 쓰면 상수가 거짓말이 된다.
    if not _ENGINE.exists():
        pytest.skip(f"형제 리포 없음: {_ENGINE}")
    src = _ENGINE.read_text(encoding="utf-8")
    assert not re.search(r"\bcp\[:\d+\]", src), "personas 를 숫자로 자르는 곳이 남아 있다"
