# 정지를 사번으로도 본다 — 정지된 사람이 다른 Mail 로 들어오면 active 새 행이 생겨 그대로 로그인됐다(10차 요청 §6)
"""정지 검사는 이메일 행 하나만 봤다(deps.entitled). 같은 사람이 다른 Mail Claim 으로 들어오면 원장에 없는 이메일이라
`note_sso_login` 이 active 새 행을 만들고, 정지가 따라오지 않았다. 그래서 사번(SAML_ATTR_SABUN, 기본 꺼짐)을 원장에 적어 두고,
SSO 콜백에서 **같은 사번의 정지된 행**이 있으면 로그인을 거절한다.

여기서 고정하는 것.
  · 거절은 진짜 거절이다 — 세션 쿠키가 나가지 않고, 새 행도 생기지 않는다. 콜백의 '원장은 부기록이라 실패해도 로그인은 계속'
    갈래(except·suppress) 안에 판정을 두면 거절이 삼켜져 그대로 로그인된다.
  · 판정을 못 하면(원장 오류) 들여보내지 않는다.
  · 칸 추가는 사람이 들어 있는 옛 원장에서 일어난다 — 옛 스키마 파일을 실제로 열어 본다.

원장은 전부 임시 폴더에 만든다. 사번·주소는 지어낸 값이다.
"""
import logging
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.auth.cookies import CSRF_COOKIE, SESSION_COOKIE
from app.auth.provider import Principal
from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.main import app

CLAIM = "http://idp.example/claims/"
SABUN = CLAIM + "Sabun"

# users 표의 최초 모양과 그 뒤 붙은 칸들(이 변경 **직전**까지) — 코드에서 베껴 오지 않고 얼려 둔다. 코드의 CREATE 문을 불러 쓰면
# '새 코드가 만든 표를 새 코드가 여는' 시험이 되어 아무것도 못 잡는다(test_dept_id_column 과 같은 규율).
_V0 = ("CREATE TABLE users (email TEXT PRIMARY KEY, name TEXT NOT NULL, pw_hash TEXT, groups TEXT NOT NULL DEFAULT '[]', "
       "status TEXT NOT NULL DEFAULT 'pending', auth_source TEXT NOT NULL DEFAULT 'local', created_at INTEGER NOT NULL, "
       "approved_at INTEGER, approved_by TEXT, last_login_at INTEGER, failed_count INTEGER NOT NULL DEFAULT 0, "
       "locked_until INTEGER NOT NULL DEFAULT 0)")
_LATER = ["department TEXT NOT NULL DEFAULT ''", "affiliation TEXT NOT NULL DEFAULT ''", "grants TEXT NOT NULL DEFAULT '[]'",
          "hub_muted_apps TEXT NOT NULL DEFAULT '[]'", "changelog_seen TEXT NOT NULL DEFAULT ''",
          "dept_id TEXT NOT NULL DEFAULT ''"]


def _old_db(path, *, columns_added: int) -> None:
    conn = sqlite3.connect(str(path))
    conn.execute(_V0)
    for col in _LATER[:columns_added]:
        conn.execute(f"ALTER TABLE users ADD COLUMN {col}")
    conn.execute("INSERT INTO users (email, name, pw_hash, groups, status, auth_source, created_at) "
                 "VALUES ('boss@corp.com', '관리자', 'scrypt$x', '[\"portal-admin\"]', 'active', 'local', 1700000000)")
    conn.execute("INSERT INTO users (email, name, groups, status, auth_source, created_at) "
                 "VALUES ('off@corp.com', '정지된 사람', '[]', 'disabled', 'sso', 1700000100)")
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
    return UserStore(Settings(_env_file=None, user_store_path=str(tmp_path / "u.sqlite")))


# ── 칸 더하기 — 사람이 들어 있는 옛 원장에서 ─────────────────────────────────
@pytest.mark.parametrize("columns_added", [len(_LATER), 3, 0])
def test_옛_스키마_원장을_열면_사번_칸이_생기고_있던_행은_그대로다(tmp_path, columns_added):
    path = tmp_path / "u.sqlite"
    _old_db(path, columns_added=columns_added)
    before = _dump(path)
    s = UserStore(Settings(_env_file=None, user_store_path=str(path)))
    after = _dump(path)
    for email, old in before.items():
        assert {k: after[email][k] for k in old} == old, f"{email} 의 있던 칸이 바뀌었다"
        assert after[email]["sabun"] == "", "새 칸의 기본값은 빈 값"
    assert s.get("off@corp.com")["status"] == "disabled" and s.get("boss@corp.com")["groups"] == ["portal-admin"]
    assert s.disabled_by_sabun("") is False, "사번이 빈 정지 행이 있어도 빈 사번과 맞으면 안 된다"
    # 옛 행에 쓰기 · 새 행 쓰기 · 정지된 옛 행의 사번으로 판정
    s.note_sso_login(email="off@corp.com", name=None, sabun="S0001")
    s.note_sso_login(email="new@corp.com", name=None, sabun="S0002")
    assert s.get("off@corp.com")["sabun"] == "S0001" and s.get("new@corp.com")["sabun"] == "S0002"
    assert s.disabled_by_sabun("S0001") is True and s.disabled_by_sabun("S0002") is False


def test_두_번째_기동도_멀쩡하다(tmp_path):
    path = tmp_path / "u.sqlite"
    _old_db(path, columns_added=len(_LATER))
    UserStore(Settings(_env_file=None, user_store_path=str(path))).note_sso_login(email="off@corp.com", name=None, sabun="S0001")
    again = UserStore(Settings(_env_file=None, user_store_path=str(path)))
    assert again.get("off@corp.com")["sabun"] == "S0001" and again.disabled_by_sabun("S0001") and len(again.list_users()) == 2


# ── 쓰기 규칙 ────────────────────────────────────────────────────────────────
def test_사번은_IdP_값이_있을_때만_적고_권한_칸은_건드리지_않는다(tmp_path):
    s = _store(tmp_path)
    s.signup(email="a@x.com", name="에이", password="pw123456", bootstrap_admins=["a@x.com"], department="재료시험팀")
    s.set_access("a@x.com", affiliation="CAEG", grants=["plat:ste"])
    s.set_status("a@x.com", "disabled")
    keep = ("affiliation", "groups", "grants", "status", "department", "dept_id", "name")
    before = {k: s.get("a@x.com")[k] for k in keep}
    s.note_sso_login(email="a@x.com", name=None, sabun=" S0001 ")
    assert s.get("a@x.com")["sabun"] == "S0001"
    assert {k: s.get("a@x.com")[k] for k in keep} == before
    for empty in (None, "", "   "):
        s.note_sso_login(email="a@x.com", name=None, sabun=empty)
        assert s.get("a@x.com")["sabun"] == "S0001", repr(empty)
    assert "sabun" not in s.list_users()[0], "관리자 표에는 사번을 싣지 않는다 — 요청받은 것은 판정뿐이다"


def test_정지_판정은_같은_사번의_정지된_행이_있을_때만_참이다(tmp_path):
    s = _store(tmp_path)
    s.note_sso_login(email="a@x.com", name=None, sabun="S0001")
    s.note_sso_login(email="b@x.com", name=None, sabun="S0002")
    s.note_sso_login(email="none@x.com", name=None)                 # 사번 없이 생긴 행
    assert s.disabled_by_sabun("S0001") is False, "활성 행뿐이다"
    s.set_status("a@x.com", "disabled")
    s.set_status("none@x.com", "disabled")
    assert s.disabled_by_sabun("S0001") is True and s.disabled_by_sabun(" S0001 ") is True
    assert s.disabled_by_sabun("S0002") is False and s.disabled_by_sabun("S000") is False
    for empty in ("", "   ", None):
        assert s.disabled_by_sabun(empty) is False, "사번 없는 정지 행이 사번 없는 사람 전부를 막으면 안 된다"
    s.set_status("a@x.com", "active")
    assert s.disabled_by_sabun("S0001") is False, "다시 활성화하면 풀린다"


# ── SSO 콜백 ─────────────────────────────────────────────────────────────────
class _Idp:
    """IdP 응답 검증을 통과한 뒤의 신원만 정해 주는 가짜 공급자 — 콜백 라우트부터는 실제 코드가 돈다."""
    name = "fake"

    def __init__(self) -> None:
        self.next: Principal | None = None

    async def handle_callback(self, request, *, expected_state):  # noqa: ARG002
        return self.next


class _Box:
    def __init__(self, c, settings, store, idp):
        self.c, self.settings, self.store, self.idp = c, settings, store, idp

    def sso(self, email: str, sabun: str | None, route=("GET", "/auth/callback")):
        """그 사람이 IdP 를 통과해 콜백에 닿는다. 브라우저 쿠키는 새로 시작한다(다른 사람의 세션이 섞이지 않게)."""
        attrs = {CLAIM + "Mail": [email]} | ({SABUN: [sabun]} if sabun is not None else {})
        self.idp.next = Principal(subject=email, email=email, attributes=attrs)
        self.c.cookies.clear()
        return self.c.request(route[0], route[1], follow_redirects=False)

    def logged_in(self) -> bool:
        return self.c.get("/auth/me").status_code == 200

    def last(self, email: str) -> dict:
        return app.state.agent_audit.query_access(since=0, include_auto=True, email=email)[0]


@pytest.fixture()
def box(tmp_path):
    s = Settings(_env_file=None, user_store_path=str(tmp_path / "users.sqlite"), saml_attr_sabun=SABUN)
    app.dependency_overrides[get_settings] = lambda: s
    with TestClient(app) as c:
        keep = (app.state.user_store, app.state.auth_provider)
        idp = _Idp()
        app.state.user_store, app.state.auth_provider = UserStore(s), idp   # 기동 뒤 교체 — 실 원장을 안 쓴다
        yield _Box(c, s, app.state.user_store, idp)
        app.state.user_store, app.state.auth_provider = keep
    app.dependency_overrides.pop(get_settings, None)


def _refused(r) -> bool:
    """로그인 화면으로 돌려보냈고(사유 포함) 세션 쿠키는 내지 않았다."""
    return (r.status_code == 302 and "/login?error=sso" in r.headers["location"]
            and not any(SESSION_COOKIE in v for v in r.headers.get_list("set-cookie")))


@pytest.mark.parametrize("route", [("GET", "/auth/callback"), ("POST", "/auth/saml/acs")])   # 두 라우트가 다른 함수다
def test_정지된_사람이_다른_Mail_로_들어오면_거절한다(box, route, caplog):
    assert box.sso("a@corp.com", "S0001").status_code == 302 and box.logged_in(), "전제 — 평소에는 들어온다"
    box.store.set_status("a@corp.com", "disabled")
    with caplog.at_level(logging.WARNING):
        r = box.sso("a.other@corp.com", "S0001", route)
    assert _refused(r), f"{r.status_code} {r.headers.get('location')} {r.headers.get_list('set-cookie')}"
    assert "%EC%A0%95%EC%A7%80" in r.headers["location"], "로그인 화면이 '정지' 사유를 보인다"
    # 사유 코드가 같이 간다 — 화면은 이것으로 '잠시 뒤 다시 시도' 가 아니라 정지라고 말한다(문장을 URL 의 detail 에서 가져오지 않는다)
    assert "reason=disabled" in r.headers["location"].split("?", 1)[1].split("&"), r.headers["location"]
    assert not box.logged_in(), "거절이 삼켜져 그대로 로그인됐다"
    assert box.store.get("a.other@corp.com") is None, "거절한 사람의 active 새 행을 만들지 않는다"
    last = box.last("a.other@corp.com")
    assert (last["event"], last["detail"]) == ("login_fail", "sso:disabled:sabun")
    said = [rec.getMessage() for rec in caplog.records if "a.other@corp.com" in rec.getMessage()]
    assert said, "누가 왜 거절됐는지 서버 로그에 남는다"
    assert not any("S0001" in rec.getMessage() for rec in caplog.records), "사번 값은 로그에 싣지 않는다"
    # 제 Mail 로 와도 이제 콜백에서 끝난다(종전엔 세션을 받고 요청마다 403). 접속 원장에는 종전 표기 그대로 남는다.
    own = box.sso("a@corp.com", "S0001", route)
    assert _refused(own) and not box.logged_in()
    assert "reason=disabled" in own.headers["location"], "제 Mail 로 온 정지된 사람에게도 같은 사유 코드다"
    assert box.last("a@corp.com")["detail"] == "sso:disabled"


def test_사번이_다르거나_정지가_풀리면_들어온다(box):
    box.sso("a@corp.com", "S0001")
    box.store.set_status("a@corp.com", "disabled")
    assert box.sso("c@corp.com", "S0002").status_code == 302 and box.logged_in(), "다른 사번은 다른 사람이다"
    assert box.store.get("c@corp.com")["sabun"] == "S0002"
    assert box.sso("d@corp.com", None).status_code == 302 and box.logged_in(), "사번 Claim 이 없는 사람은 사번으로 막지 않는다"
    assert box.sso("e@corp.com", "  ").status_code == 302 and box.logged_in()
    box.store.set_status("a@corp.com", "active")
    assert box.sso("a.other@corp.com", "S0001").status_code == 302 and box.logged_in(), "다시 활성화하면 사번으로도 풀린다"


def test_기본은_꺼짐이라_사번_Claim_이_와도_보지도_적지도_않는다(box):
    assert Settings(_env_file=None).saml_attr_sabun == ""
    box.settings.saml_attr_sabun = ""
    box.sso("a@corp.com", "S0001")
    assert box.store.get("a@corp.com")["sabun"] == ""
    box.store._conn.execute("UPDATE users SET sabun = 'S0001', status = 'disabled' WHERE email = 'a@corp.com'")
    box.store._commit()
    assert box.sso("a.other@corp.com", "S0001").status_code == 302 and box.logged_in(), "꺼져 있으면 종전 그대로다"


def test_정지된_뒤에_처음_사번이_온_사람도_다음부터_걸린다(box):
    """사번을 받기 전에 정지된 행에는 사번이 없다. 그 사람이 제 Mail 로 들어오면(세션은 받지만 모든 요청이 403 — 종전 그대로)
    그때 사번이 적히고, 그다음부터는 다른 Mail 로 와도 거절된다."""
    box.sso("a@corp.com", None)
    box.store.set_status("a@corp.com", "disabled")
    assert box.sso("a@corp.com", "S0001").status_code == 302
    assert box.c.get("/auth/me").status_code == 403, "제 이메일의 정지는 요청마다 본다(deps)"
    assert box.store.get("a@corp.com")["sabun"] == "S0001" and box.store.get("a@corp.com")["status"] == "disabled"
    assert _refused(box.sso("a.other@corp.com", "S0001")) and not box.logged_in()


def test_정지_여부를_확인하지_못하면_들여보내지_않는다(box, monkeypatch):
    """원장을 못 읽었다고 '정지 아님' 으로 넘어가면 원장이 고장 난 동안 정지된 사람이 전부 들어온다."""
    def broken(_sabun):
        raise sqlite3.OperationalError("no such column: sabun")

    monkeypatch.setattr(box.store, "disabled_by_sabun", broken)
    r = box.sso("a@corp.com", "S0001")
    assert _refused(r) and not box.logged_in(), f"{r.status_code} {r.headers.get('location')}"
    assert "reason=" not in r.headers["location"], "확인하지 못한 것은 정지가 아니다 — '잠시 뒤 다시 시도' 가 맞는 안내다"
    assert box.sso("d@corp.com", None).status_code == 302 and box.logged_in(), "사번이 없는 로그인은 그 판정을 지나지 않는다"


# ── 같은 사번의 다른 행을 정지할 때 — 본인·마지막 관리자 보호가 사번까지 본다 ─────────────────────────────────
# 정지의 본인·마지막 관리자 보호(9e94162)는 이메일 행 하나만 봤다. 그런데 사번을 보는 박스에서는 한 행을 정지하면 **같은 사번의
# 활성 행 전부**가 다음 SSO 로그인에서 거절된다(위 판정). 주소가 둘인 관리자가 안 쓰는 쪽 행을 정리 삼아 정지하면 — 이 화면에는
# 삭제가 없어 정지가 유일한 정리다 — 보호를 지나 제 SSO 로그인을 막았다. 마지막 관리자였으면 세션이 끝난 뒤 관리자 화면을 열
# 사람이 없다.
def _suspend_as(box, admin_email: str, admin_sabun: str | None, target: str):
    """그 관리자가 SSO 로 들어와 사용자 관리에서 target 을 정지한다."""
    assert box.sso(admin_email, admin_sabun).status_code == 302 and box.logged_in()
    return box.c.post(f"/auth/local/users/{target}/status", json={"status": "disabled"},
                      headers={"X-CSRF-Token": box.c.cookies.get(CSRF_COOKIE)})


def test_주소가_둘인_혼자_남은_관리자가_안_쓰는_주소를_정지하지_못한다(box):
    """**이 구획의 이유다** — 종전엔 200 이었고, 그 뒤 a@corp.com 의 SSO 로그인이 sso:disabled:sabun 으로 거절됐다."""
    box.sso("a@corp.com", "S0001"); box.sso("a.old@corp.com", "S0001")
    box.settings.portal_admin_emails = "a@corp.com,a.old@corp.com"       # 주소가 둘인 사람은 둘 다 적는다(config 주석)
    r = _suspend_as(box, "a@corp.com", "S0001", "a.old@corp.com")
    assert r.status_code == 409 and "사번" in r.json()["detail"], r.text
    assert "S0001" not in r.text, "사번 값은 응답에 싣지 않는다"
    assert box.store.get("a.old@corp.com")["status"] == "active"
    assert box.sso("a@corp.com", "S0001").status_code == 302 and box.logged_in(), "관리자가 여전히 SSO 로 들어온다"


def test_원장_관리자가_같은_사번의_일반_행을_정지해도_거절한다(box):
    """대상 행이 관리자가 아니어도 같다 — 종전의 마지막 관리자 셈은 대상 행의 표지만 봐서 이 갈래를 아예 세지 않았다."""
    box.sso("a@corp.com", "S0001"); box.sso("a.old@corp.com", "S0001")
    assert box.store.set_admin("a@corp.com", True) == "set"
    r = _suspend_as(box, "a@corp.com", "S0001", "a.old@corp.com")
    assert r.status_code == 409 and "사번" in r.json()["detail"], r.text
    assert box.store.disabled_by_sabun("S0001") is False


def test_다른_관리자가_남아_있으면_같은_사번의_행을_정지할_수_있고_그_사람은_사번으로_막힌다(box):
    """10차 §6 의 설계는 그대로다 — 정지된 사람이 다른 Mail 로 들어오는 길을 막는 것. 거절하는 것은 본인과 마지막 관리자뿐이다."""
    box.sso("a@corp.com", "S0001"); box.sso("a.old@corp.com", "S0001"); box.sso("boss@corp.com", "S0009")
    for admin in ("a@corp.com", "boss@corp.com"):
        assert box.store.set_admin(admin, True) == "set"
    r = _suspend_as(box, "boss@corp.com", "S0009", "a.old@corp.com")
    assert r.status_code == 200, r.text
    assert _refused(box.sso("a@corp.com", "S0001")) and box.last("a@corp.com")["detail"] == "sso:disabled:sabun"


def test_사번을_보지_않는_박스에서는_종전_그대로_정지된다(box):
    """꺼져 있으면 같은 사번의 행이 함께 막히지 않는다 — 막을 이유가 없다."""
    box.sso("a@corp.com", "S0001"); box.sso("a.old@corp.com", "S0001")
    box.store.set_admin("a@corp.com", True)
    box.settings.saml_attr_sabun = ""
    r = _suspend_as(box, "a@corp.com", None, "a.old@corp.com")
    assert r.status_code == 200, r.text
    assert box.sso("a@corp.com", "S0001").status_code == 302 and box.logged_in()


def test_저장소는_같은_사번의_관리자_행이_함께_막히는_것을_마지막_관리자로_센다(tmp_path):
    """두 관리자가 서로의 다른 주소를 동시에 정지하는 경합은 라우트의 본인 확인을 지난다 — 판정을 저장소의 잠금 안에서 한다.
    남는 관리자는 '이 쓰기 뒤에도 SSO 로 들어올 수 있는 활성 관리자' 다."""
    s = _store(tmp_path)
    for email, sabun in (("a@x.com", "S0001"), ("a.old@x.com", "S0001"), ("u@x.com", "S0002"), ("none@x.com", None)):
        s.note_sso_login(email=email, name=None, sabun=sabun)
    for admin in ("a@x.com", "a.old@x.com"):
        s.set_admin(admin, True)
    assert s.suspend("a.old@x.com", by_sabun=True) == "last" and s.get("a.old@x.com")["status"] == "active"
    assert s.suspend("a.old@x.com", by_sabun=True, actor="a@x.com") == "self"
    assert s.suspend("a.old@x.com", by_sabun=True, actor="A@X.com ") == "self", "주소는 소문자·공백을 다듬어 견준다"
    # 본인 행 그 자체는 라우트가 먼저 막는다 — 저장소는 종전 셈(마지막 관리자)으로 답한다
    assert s.suspend("a@x.com", by_sabun=True, actor="a@x.com") == "last"
    # 사번이 다른 관리자가 남으면 된다
    s.set_admin("u@x.com", True)
    assert s.suspend("a.old@x.com", by_sabun=True, actor="u@x.com") == "set"
    # 사번이 빈 행은 아무와도 묶이지 않는다(빈 사번끼리 같은 사람으로 보지 않는다)
    s.note_sso_login(email="none2@x.com", name=None)
    assert s.suspend("none@x.com", by_sabun=True, actor="none2@x.com") == "set"
    # 사번을 보지 않으면(기본) 종전과 같다
    s2 = _store(tmp_path / "off")
    for email in ("a@x.com", "a.old@x.com"):
        s2.note_sso_login(email=email, name=None, sabun="S0001")
    s2.set_admin("a@x.com", True)
    assert s2.suspend("a.old@x.com", actor="a@x.com") == "set"
