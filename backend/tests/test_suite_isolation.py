# 시험이 이 박스의 실 저장소를 열지 않는지 — 포털 기동(lifespan)이 여는 sqlite 다섯을 실제로 띄워서 본다
"""왜 — 시험 26개 파일이 `TestClient(app)` 로 포털을 띄운다. 기동은 저장소 다섯(계정·토큰·대화·감사·절차)을 **설정된 경로에서**
열고, 그 경로를 따로 정하지 않으면 이 박스의 실 저장소다(dev 는 backend/secrets·backend/data 가 /data/svc/portal 로 걸려 있다).
감사·계정 원장은 conftest 가 임시 경로로 돌려 두었는데(dev 감사 원장 814줄 중 622줄이 시험 기록이던 실사고) 나머지 셋은 빠져
있었다 — 시험을 돌릴 때마다
  · 토큰 저장소 — 시험이 발급한 PAT 가 실 원장에 쌓이고, 정지·관리자 해제 시험의 `revoke_all_for` 가 실 원장에서 돈다.
  · 절차 저장소 — 기동이 `close_stale()` 로 '돌던 단계' 를 unknown 으로 마감한다. 떠 있는 포털이 실제로 돌리던 단계까지다.
  · 대화 저장소 — 스키마 이관이 실 DB 에서 돈다.
시험마다 `app.state.*` 를 임시 저장소로 바꾸는 것은 기동 **뒤**라 이것을 못 막는다. 처음부터 임시 경로로 띄워야 한다.
"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import BACKEND_DIR
from app.main import app

# 이 박스의 실 저장소가 있을 수 있는 자리 — 리포의 backend/ 아래(기본 상대경로)와 /data(레지스트리 이관 뒤)
REAL_ROOTS = (BACKEND_DIR.resolve(), Path("/data"))


def _db_file(conn) -> Path:
    """이 연결이 실제로 연 파일 — 심링크를 따라간 경로(설정값이 아니라 sqlite 에 묻는다)."""
    return Path(conn.execute("PRAGMA database_list").fetchone()[2]).resolve()


@pytest.fixture(scope="module")
def opened() -> dict[str, Path]:
    """아무 override 없이 포털을 띄웠을 때(= 시험 대부분이 하는 그대로) 각 저장소가 연 파일."""
    with TestClient(app):
        st = app.state
        assert st.procedures_store is not None, getattr(st, "procedures_error", "절차 저장소가 뜨지 않았다")
        return {"계정 원장": _db_file(st.user_store._conn), "토큰 저장소": _db_file(st.token_store._conn),
                "대화 저장소": _db_file(st.conv_store._conn), "감사 원장": _db_file(st.agent_audit._conn),
                "절차 저장소": _db_file(st.procedures_store._conn())}


@pytest.mark.parametrize("name", ["계정 원장", "토큰 저장소", "대화 저장소", "감사 원장", "절차 저장소"])
def test_기동이_여는_저장소는_이_박스의_실_저장소가_아니다(opened, name):
    path = opened[name]
    for root in REAL_ROOTS:
        assert root not in path.parents, f"{name} 가 실 저장소를 열었다 — {path}"


def test_저장소마다_다른_파일이다(opened):
    """한 임시 파일을 여럿이 나눠 쓰면 표 이름이 겹칠 때 서로의 스키마를 본다."""
    assert len(set(opened.values())) == len(opened), opened
