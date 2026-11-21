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
                "절차 저장소": _db_file(st.procedures_store._conn()),
                "연결 암호 키": st.user_store._cipher.path.resolve()}     # sqlite 는 아니지만 계정 원장을 열면 없을 때 만든다(HP-05)


@pytest.mark.parametrize("name", ["계정 원장", "토큰 저장소", "대화 저장소", "감사 원장", "절차 저장소", "연결 암호 키"])
def test_기동이_여는_저장소는_이_박스의_실_저장소가_아니다(opened, name):
    path = opened[name]
    for root in REAL_ROOTS:
        assert root not in path.parents, f"{name} 가 실 저장소를 열었다 — {path}"


def test_저장소마다_다른_파일이다(opened):
    """한 임시 파일을 여럿이 나눠 쓰면 표 이름이 겹칠 때 서로의 스키마를 본다."""
    assert len(set(opened.values())) == len(opened), opened


def test_알림_원장은_격리된_대화_저장소_파일_안의_표다():
    """알림 원장(docs/request-1117 contracts §7)은 새 경로 설정 없이 대화 저장소 파일에 표를 더한다(app/notices/store.py 머리) — 그래서 따로 띄워
    연 파일이 대화 저장소와 **같고**(위의 '다른 파일' 목록에는 넣지 않는다) 이 박스의 실 저장소가 아님을 본다. 경로가 갈라지면 격리가 빠진다."""
    with TestClient(app):
        st = app.state
        assert st.notice_store is not None, "알림 원장이 뜨지 않았다"
        got = _db_file(st.notice_store._conn)
        assert got == _db_file(st.conv_store._conn), got
        for root in REAL_ROOTS:
            assert root not in got.parents, f"알림 원장이 실 저장소를 열었다 — {got}"


def test_이용_통계의_접는_표는_격리된_감사_원장_파일_안이고_시험_기동은_접기를_띄우지_않는다():
    """날마다 접는 표(docs/ops-dashboard M2)는 새 경로 설정 없이 감사 원장 파일에 표를 더한다(app/usage_fold.py 머리) — 접는 쪽의 제 연결이 연 파일이
    감사 원장과 같고 이 박스의 실 저장소가 아님을 본다. 접기 작업은 conftest 가 끈다(USAGE_FOLD_S=0) — 켜진 채 포털을 띄우면 시험마다 이 박스에 떠 있는
    게이트웨이 · 에이전트 서버를 backend/.env 의 공유 비밀로 부르고 정문 로그를 읽는다."""
    from contextlib import closing

    from app import usage_fold
    from app.config import get_settings
    with TestClient(app):
        st = app.state
        assert st.usage_fold is None, "시험 기동이 이용 통계 접기를 띄웠다 — conftest 의 USAGE_FOLD_S=0 이 빠졌다"
        with closing(usage_fold.connect(get_settings())) as conn:
            got = _db_file(conn)
        assert got == _db_file(st.agent_audit._conn), got
        for root in REAL_ROOTS:
            assert root not in got.parents, f"접는 표가 실 저장소를 열었다 — {got}"


# ── LLM/GPU 현황 수집기(docs/ops-dashboard) — 포털 밖의 호스트 서비스지만 시험이 그 모듈을 부른다 ───────────────────────────────────
def test_수집기가_여는_저장소와_읽는_설정은_이_박스의_실_자리가_아니다():
    """인자 없이(= 시험이 기본값을 탈 때) 수집기가 여는 sqlite 와 읽는 infra/.env — conftest 가 둘 다 임시 자리로 돌린다. 없으면 수집기 시험
    하나가 이 박스의 infra/.state/llm-status 에 표본을 쌓거나, 실제 infra/.env 의 키로 실 LLM 서버를 부른다. 실제로 연 파일은 sqlite 에 묻는다."""
    import argparse
    import importlib.util
    import sys
    root = BACKEND_DIR.parent / "infra"
    keep, sys.dont_write_bytecode = sys.dont_write_bytecode, True     # 지문(services.yaml fp: infra/llm-status)의 폴더에 __pycache__ 를 남기지 않는다
    try:
        spec = importlib.util.spec_from_file_location("llm_status_collector_iso", root / "llm-status" / "collector.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
    finally:
        sys.dont_write_bytecode = keep
    args = argparse.Namespace(state_dir=None, env_file=None)
    real = root.resolve()
    env_file = Path(m._env_file(args)).resolve()
    assert real not in env_file.parents, f"수집기가 이 리포의 infra/ 아래 설정을 읽는다 — {env_file}"
    st = m.state_dir(args).resolve()
    for r in (*REAL_ROOTS, real):                  # 열기 **전에** 본다 — 실 자리면 여는 순간 그 자리에 폴더 · DB 가 생긴다
        assert r not in st.parents, f"수집기 저장 자리가 실 자리다 — {st}"
    lock, store, why = m.open_state(st)
    assert store is not None, why
    try:
        db = _db_file(store.conn)
        for r in (*REAL_ROOTS, real):
            assert r not in db.parents, f"수집기가 실 저장소를 열었다 — {db}"
    finally:
        store.close()
        lock.close()

