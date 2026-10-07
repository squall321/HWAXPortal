# 부서 코드(DeptId)는 표시용 부서와 다른 칸에 적는다 — 켜도 사람이 적은 부서명이 코드로 덮이지 않는다(10차 요청 §7)
"""운영 ADFS 가 주는 부서 Claim 은 코드(DeptId) 하나뿐이다. 그것을 SAML_ATTR_DEPARTMENT 로 받으면 원장 `department`(표시용,
사람이 직접 적은 부서명)가 로그인하는 순간 코드로 바뀐다. 그래서 코드는 `dept_id` 칸에 따로 적는다(SAML_ATTR_DEPT_ID, 기본 꺼짐).

칸을 더하는 일은 **이미 사람이 들어 있는 원장 파일**에서 일어난다 — 여기서 실패하면 원장을 못 열어 전원이 막힌다. 그래서 옛 스키마로
만든 파일을 실제로 열어 본다. 모든 파일은 임시 폴더에 만든다. 코드·이름은 지어낸 값이다.
"""
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.auth.provider import Principal
from app.auth.routes.session import complete_login
from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.main import app

CLAIM = "http://idp.example/claims/"

# 이 변경 **직전**의 users 표(포털 614a764) — 지금 박스들의 원장이 이 모양이다. 코드에서 베껴 오지 않고 얼려 둔다:
# 코드의 CREATE 문을 불러 쓰면 '새 코드가 만든 표를 새 코드가 여는' 시험이 되어 아무것도 못 잡는다.
_V0 = ("CREATE TABLE users (email TEXT PRIMARY KEY, name TEXT NOT NULL, pw_hash TEXT, groups TEXT NOT NULL DEFAULT '[]', "
       "status TEXT NOT NULL DEFAULT 'pending', auth_source TEXT NOT NULL DEFAULT 'local', created_at INTEGER NOT NULL, "
       "approved_at INTEGER, approved_by TEXT, last_login_at INTEGER, failed_count INTEGER NOT NULL DEFAULT 0, "
       "locked_until INTEGER NOT NULL DEFAULT 0)")
_LATER = ["department TEXT NOT NULL DEFAULT ''", "affiliation TEXT NOT NULL DEFAULT ''", "grants TEXT NOT NULL DEFAULT '[]'",
          "hub_muted_apps TEXT NOT NULL DEFAULT '[]'", "changelog_seen TEXT NOT NULL DEFAULT ''"]


def _old_db(path, *, columns_added: int) -> None:
    """옛 포털이 만든 원장 파일. `columns_added` 는 그 뒤 붙은 칸 중 몇 개까지 있는 파일인가(0 = 최초 스키마)."""
    conn = sqlite3.connect(str(path))
    conn.execute(_V0)
    for col in _LATER[:columns_added]:
        conn.execute(f"ALTER TABLE users ADD COLUMN {col}")
    conn.execute("INSERT INTO users (email, name, pw_hash, groups, status, auth_source, created_at) "
                 "VALUES ('boss@corp.com', '관리자', 'scrypt$x', '[\"portal-admin\"]', 'active', 'local', 1700000000)")
    conn.execute("INSERT INTO users (email, name, groups, status, auth_source, created_at) "
                 "VALUES ('off@corp.com', '정지된 사람', '[]', 'disabled', 'sso', 1700000100)")
    if columns_added >= 3:
        conn.execute("UPDATE users SET department = '직접 적은 부서', affiliation = 'CAEG', grants = '[\"plat:ste\"]' "
                     "WHERE email = 'boss@corp.com'")
    conn.commit()
    conn.close()


def _dump(path) -> dict:
    conn = sqlite3.connect(str(path))
    cur = conn.execute("SELECT * FROM users ORDER BY email")
    cols = [c[0] for c in cur.description]
    rows = {r[0]: dict(zip(cols, r, strict=True)) for r in cur.fetchall()}
    conn.close()
    return rows


def _store(tmp_path) -> UserStore:
    return UserStore(Settings(user_store_path=str(tmp_path / "u.sqlite")))


# ── 칸 더하기 — 사람이 들어 있는 옛 원장에서 ─────────────────────────────────
@pytest.mark.parametrize("columns_added", [len(_LATER), 3, 0])
def test_옛_스키마_원장을_열면_칸이_생기고_있던_행은_그대로다(tmp_path, columns_added):
    path = tmp_path / "u.sqlite"
    _old_db(path, columns_added=columns_added)
    before = _dump(path)
    s = UserStore(Settings(user_store_path=str(path)))
    after = _dump(path)
    for email, old in before.items():
        assert {k: after[email][k] for k in old} == old, f"{email} 의 있던 칸이 바뀌었다"
        assert after[email]["dept_id"] == "", "새 칸의 기본값은 빈 값"
    # 정지·관리자·소속이 그대로 읽힌다 — 원장을 못 열거나 칸을 못 읽으면 전원이 막힌다
    assert s.get("off@corp.com")["status"] == "disabled"
    assert s.get("boss@corp.com")["groups"] == ["portal-admin"]
    assert {u["email"]: u["dept_id"] for u in s.list_users()} == {"boss@corp.com": "", "off@corp.com": ""}
    s.note_sso_login(email="boss@corp.com", name=None, dept_id="D12345")       # 옛 행에 쓰기
    s.note_sso_login(email="new@corp.com", name=None, dept_id="D54321")        # 새 행 쓰기
    assert s.get("boss@corp.com")["dept_id"] == "D12345" and s.get("new@corp.com")["dept_id"] == "D54321"


def test_두_번째_기동도_멀쩡하다(tmp_path):
    """칸이 이미 있는 원장을 다시 연다 — 재기동마다 일어나는 일이다. 값이 지워지지도 않는다."""
    path = tmp_path / "u.sqlite"
    _old_db(path, columns_added=len(_LATER))
    UserStore(Settings(user_store_path=str(path))).note_sso_login(email="boss@corp.com", name=None, dept_id="D12345")
    again = UserStore(Settings(user_store_path=str(path)))
    assert again.get("boss@corp.com")["dept_id"] == "D12345"
    assert len(again.list_users()) == 2


# ── 쓰기 규칙 ────────────────────────────────────────────────────────────────
def test_새_SSO_사용자의_부서_코드는_dept_id_에만_간다(tmp_path):
    s = _store(tmp_path)
    s.note_sso_login(email="New.User@Example.com", name=None, dept_id=" D12345 ")
    u = s.get("new.user@example.com")
    assert u["dept_id"] == "D12345" and u["department"] == "", u


def test_있던_사람은_코드만_채우고_직접_적은_부서명은_그대로다(tmp_path):
    """요청의 핵심 — DeptId 를 켜는 순간 사람이 적은 부서명이 코드로 바뀌던 것."""
    s = _store(tmp_path)
    s.signup(email="a@x.com", name="에이", password="pw123456", bootstrap_admins=["a@x.com"], department="재료시험팀")
    s.note_sso_login(email="a@x.com", name=None, dept_id="D12345")
    u = s.get("a@x.com")
    assert (u["department"], u["dept_id"]) == ("재료시험팀", "D12345"), u


def test_코드는_IdP_값이_있을_때만_바꾼다(tmp_path):
    s = _store(tmp_path)
    s.note_sso_login(email="b@x.com", name=None, dept_id="D12345")
    for empty in (None, "", "   "):
        s.note_sso_login(email="b@x.com", name=None, dept_id=empty)
        assert s.get("b@x.com")["dept_id"] == "D12345", repr(empty)
    s.note_sso_login(email="b@x.com", name=None, dept_id="D99999")             # 부서를 옮겼다
    assert s.get("b@x.com")["dept_id"] == "D99999"


def test_부서_코드는_권한_칸을_건드리지_않는다(tmp_path):
    s = _store(tmp_path)
    s.signup(email="c@x.com", name="씨", password="pw123456", bootstrap_admins=["c@x.com"])
    s.set_access("c@x.com", affiliation="CAEG", grants=["plat:ste"])
    s.set_status("c@x.com", "disabled")
    before = {k: s.get("c@x.com")[k] for k in ("affiliation", "groups", "grants", "status")}
    s.note_sso_login(email="c@x.com", name=None, dept_id="D12345")
    assert {k: s.get("c@x.com")[k] for k in before} == before


# ── 콜백에서 수확 ────────────────────────────────────────────────────────────
def _callback(tmp_path, settings, attributes):
    """SSO 콜백의 IdP 무관 뒷부분(complete_login)을 실제로 돌린다 — 원시 Claim 은 여기서만 살아 있다."""
    store = UserStore(settings)
    with TestClient(app) as c:
        req = Request({"type": "http", "method": "POST", "path": "/auth/callback", "headers": [], "query_string": b"",
                       "app": app, "client": ("203.0.113.5", 50000)})
        complete_login(principal=Principal(subject="d@x.com", email="d@x.com", display_name=None, groups=[],
                                           attributes=attributes),
                       expected_state=None, settings=settings, jwt_service=c.app.state.jwt_service,
                       user_store=store, request=req)
    return store.get("d@x.com")


def test_설정한_Claim_에서_코드를_수확한다(tmp_path):
    s = Settings(user_store_path=str(tmp_path / "u.sqlite"), saml_attr_dept_id=CLAIM + "DeptId")
    u = _callback(tmp_path, s, {CLAIM + "DeptId": ["D12345"], CLAIM + "CompId": ["C999"]})
    assert u["dept_id"] == "D12345" and u["department"] == "", u


def test_기본은_꺼짐이라_Claim_이_와도_적지_않는다(tmp_path):
    s = Settings(_env_file=None, user_store_path=str(tmp_path / "u.sqlite"))
    assert s.saml_attr_dept_id == ""
    u = _callback(tmp_path, s, {CLAIM + "DeptId": ["D12345"], "": ["빈 이름 Claim"]})
    assert u["dept_id"] == "", "꺼져 있는데 빈 이름의 Claim 을 집어 오면 안 된다"


# ── 관리자 화면이 읽는 목록 ──────────────────────────────────────────────────
def test_사용자_목록_API_가_부서_코드를_준다(tmp_path):
    s = Settings(user_store_path=str(tmp_path / "u.sqlite"), local_bootstrap_admins="boss@corp.com")
    app.dependency_overrides[get_settings] = lambda: s
    from app.auth.routes.local import _rl
    _rl.clear()
    try:
        with TestClient(app) as c:
            app.state.user_store = UserStore(s)            # 컨텍스트 진입 후 교체(실DB 오염 방지)
            c.post("/auth/local/signup", json={"email": "boss@corp.com", "name": "B", "password": "pw123456"})
            assert c.post("/auth/local/login", json={"email": "boss@corp.com", "password": "pw123456"}).status_code == 200
            app.state.user_store.note_sso_login(email="sso@corp.com", name=None, dept_id="D12345")
            rows = {u["email"]: u for u in c.get("/auth/local/users").json()}
    finally:
        app.dependency_overrides.pop(get_settings, None)
    assert rows["sso@corp.com"]["dept_id"] == "D12345" and rows["boss@corp.com"]["dept_id"] == ""
    assert json.dumps(rows)  # 직렬화되는 값만 실린다


# ── 칸 추가가 실패하면 — 조용히 넘어가지 않는다 ───────────────────────────────────────────────────
def test_칸을_더하지_못하면_원장을_연_척하지_않는다(tmp_path, monkeypatch):
    """칸 추가는 `OperationalError` 를 통째로 삼켰다('이미 있는 칸' 을 넘기려던 것). 그 예외에는 'database is locked' 도 있다 —
    다른 프로세스가 쓰기 잠금을 쥔 채 포털이 뜨면 칸이 안 생긴 채 기동이 '성공' 하고, 그 칸을 읽는 사용자 목록은 요청마다 500,
    SSO 원장 쓰기는 로그인마다 실패한다(재기동할 때까지). 못 더했으면 여기서 던진다 — 기동이 멈추고 start.sh 가 로그 끝을 보인다."""
    import app.auth.user_store as mod

    db = tmp_path / "u.sqlite"
    # 지금 박스들의 원장 모양 — 표는 전부 있고(허가 요청·연결·확인함 포함) users 에 dept_id·sabun 만 아직 없다.
    # users 표만 있는 파일로는 이 결함이 안 보인다: 없는 표를 만드는 쓰기가 먼저 잠금에 걸려 (삼키지 않는 자리에서) 던진다.
    UserStore(Settings(_env_file=None, user_store_path=str(db)))._conn.close()
    seed = sqlite3.connect(str(db))
    for col in ("sabun", "dept_id"):
        seed.execute(f"ALTER TABLE users DROP COLUMN {col}")
    seed.execute("INSERT INTO users (email, name, groups, status, auth_source, created_at, affiliation) "
                 "VALUES ('boss@corp.com', '관리자', '[\"portal-admin\"]', 'active', 'local', 1700000000, 'CAEG')")
    seed.commit()
    seed.close()
    assert not {"dept_id", "sabun"} & set(_dump(db)["boss@corp.com"]), "전제 — 두 칸이 없는 원장"
    real = sqlite3.connect
    monkeypatch.setattr(mod.sqlite3, "connect", lambda path, **kw: real(path, timeout=0.05, **kw))   # 잠금 대기를 짧게
    other = real(str(db))
    other.execute("BEGIN IMMEDIATE")                  # 다른 프로세스가 쓰는 중
    try:
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            UserStore(Settings(_env_file=None, user_store_path=str(db)))
    finally:
        other.rollback()
        other.close()
    # 잠금이 풀린 뒤 다시 띄우면 칸이 생기고 있던 행은 그대로다
    store = UserStore(Settings(_env_file=None, user_store_path=str(db)))
    assert {"dept_id", "sabun"} <= set(_dump(db)["boss@corp.com"]), "다음 기동이 스스로 낫는다"
    assert store.get("boss@corp.com")["affiliation"] == "CAEG"


def test_이미_있는_칸은_여전히_조용히_넘어간다(tmp_path):
    """좁힌 것은 '이미 있는 칸' 이 아닌 실패뿐이다 — 같은 원장을 두 번 열어도(재기동) 죽지 않는다."""
    db = tmp_path / "u.sqlite"
    _old_db(db, columns_added=2)
    for _ in range(3):
        UserStore(Settings(_env_file=None, user_store_path=str(db)))
    assert {"department", "affiliation", "grants", "hub_muted_apps", "changelog_seen", "dept_id", "sabun"} <= set(_dump(db)["boss@corp.com"])

