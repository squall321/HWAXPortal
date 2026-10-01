# SSO 로그인이 원장에 적는 것 — 이름은 빈 때만 채우고, 부서는 IdP 값으로 덮고, 권한 칸은 절대 안 건드린다(6차 요청 §4-B)
"""운영 ADFS 는 이름 Claim 을 아직 안 준다. 그 동안 들어온 사람이 원장 이름에 이메일이 박힌 채 굳으면 Claim 이 릴리즈돼도 안 낫는다
(종전: 새 행 name=email, UPDATE 는 name 을 안 건드림). 부서는 사람 입력 표기가 갈려 있어 IdP 값으로 덮지만, 소속(affiliation)은
권한 입력이라 IdP 가 건드리면 모르는 값이 조용히 버려져 CAEG 사용자가 기본 권한으로 떨어진다."""
from app.auth.user_store import UserStore
from app.config import Settings


def _store(tmp_path) -> UserStore:
    return UserStore(Settings(user_store_path=str(tmp_path / "u.sqlite")))


def _row(s, email):
    u = s.get(email)
    return {k: u[k] for k in ("name", "department", "affiliation", "groups", "grants", "status")}


def _local(s, email, name, dept=""):
    s.signup(email=email, name=name, password="pw123456", bootstrap_admins=[email], department=dept)
    s.set_access(email, affiliation="CAEG", grants=["plat:ste"])


def test_새_SSO_사용자의_이름은_비워_둔다_부서는_받는다(tmp_path):
    s = _store(tmp_path)
    s.note_sso_login(email="New.User@Example.com", name=None, department=" 재료시험팀 ")
    r = _row(s, "new.user@example.com")
    assert r["name"] == "" and r["department"] == "재료시험팀" and r["status"] == "active", r


def test_사람이_적은_이름은_IdP_이름이_와도_보존한다(tmp_path):
    s = _store(tmp_path)
    _local(s, "a@x.com", "박구")
    s.note_sso_login(email="a@x.com", name="Park Koo")
    assert _row(s, "a@x.com")["name"] == "박구"


def test_이메일이_박힌_옛_이름과_빈_이름은_IdP_이름이_오면_낫는다(tmp_path):
    """종전 note_sso_login 이 만든 행(name=email)이 영구히 굳지 않게 — 그 꼴도 '빈 이름' 으로 본다."""
    s = _store(tmp_path)
    s.note_sso_login(email="b@x.com", name=None)                      # 이름 없이 생성
    s._conn.execute("UPDATE users SET name = 'B@X.com' WHERE email = 'b@x.com'"); s._commit()   # 옛 판이 만든 꼴
    s.note_sso_login(email="b@x.com", name=None)                      # 아직 Claim 없음 — 그대로
    assert _row(s, "b@x.com")["name"] == "B@X.com"
    s.note_sso_login(email="b@x.com", name="  비이  ")                 # Claim 릴리즈
    assert _row(s, "b@x.com")["name"] == "비이"


def test_빈_이름은_NOT_NULL_을_깨지_않는다(tmp_path):
    s = _store(tmp_path)
    _local(s, "c@x.com", "씨")
    for empty in (None, "", "   "):
        s.note_sso_login(email="c@x.com", name=empty)
    assert _row(s, "c@x.com")["name"] == "씨"


def test_부서는_IdP_값이_있을_때만_덮는다(tmp_path):
    s = _store(tmp_path)
    _local(s, "d@x.com", "디", dept="옛 표기")
    for empty in (None, "", "  "):
        s.note_sso_login(email="d@x.com", name=None, department=empty)
        assert _row(s, "d@x.com")["department"] == "옛 표기", empty
    s.note_sso_login(email="d@x.com", name=None, department="재료시험팀")
    assert _row(s, "d@x.com")["department"] == "재료시험팀"


def test_권한_칸은_절대_안_건드린다(tmp_path):
    """§4-B-4 — affiliation·groups·grants·status 는 사람이 정한다. 정지된 계정도 SSO 로그인으로 살아나지 않는다."""
    s = _store(tmp_path)
    _local(s, "e@x.com", "이")
    s.set_status("e@x.com", "disabled")
    before = _row(s, "e@x.com")
    s.note_sso_login(email="E@X.com", name="Ee", department="재료시험팀")
    after = _row(s, "e@x.com")
    for k in ("affiliation", "groups", "grants", "status"):
        assert after[k] == before[k], (k, before[k], after[k])
