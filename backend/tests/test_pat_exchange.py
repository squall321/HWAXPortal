# 토큰 교환(/auth/pat/exchange)이 좁은 PAT 만 내고 넓히기·수명 늘리기·폐기 피하기를 막는지 본다
"""docs/risk-credentials PLAN §4.1 · context-notes C-2.

원 PAT 은 진짜 `/auth/pat` 길(세션 + CSRF)로 받는다. 거절 시험은 막는 검사 하나를 빼면 깨지게
짰다 — 두 검사가 같은 거절을 겹쳐 막는 곳은 그 겹침을 비켜 가는 입력을 쓴다(절차 PAT 의 jti 를
기록해 둔다, 거절 code 까지 본다 등). 토큰 원장은 시험마다 새 파일이다(conftest 의 격리 위에 한
겹 더 — 앞 시험의 PAT 이 폐기 목록·자식 수에 섞이지 않게).
"""
import sqlite3
import time
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient

import app.auth.routes.pat as pat_routes
from app.agent.routes import _chat_user_pat
from app.auth.pat_verify import verify_pat
from app.auth.provider import Principal
from app.auth.token_store import MAX_LIVE_CHILDREN, TokenStore
from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.main import app
from app.procedures.pat import mint as mint_procedure_pat

AUD = "mcp-gateway"
U = "u@corp.com"
BOSS = "boss@corp.com"


@pytest.fixture()
def client(tmp_path):
    s = Settings(user_store_path=str(tmp_path / "users.sqlite"), local_bootstrap_admins=BOSS)
    app.dependency_overrides[get_settings] = lambda: s
    from app.auth.routes.local import _rl
    _rl.clear()
    with TestClient(app) as c:
        app.state.user_store = UserStore(s)
        app.state.token_store = TokenStore(
            Settings(token_store_path=str(tmp_path / "tokens.sqlite")))
        yield c
    app.dependency_overrides.pop(get_settings, None)


def _login(c, email) -> dict:
    c.cookies.clear()
    c.post("/auth/local/login", json={"email": email, "password": "pw123456"})
    return {"X-CSRF-Token": c.cookies.get("hwax_csrf")}


@pytest.fixture()
def box(client):
    """boss(부트스트랩 관리자)와 u(`feat:api-token` 허가). u 로 로그인해 둔다."""
    for e, n in ((BOSS, "Boss"), (U, "U")):
        client.post("/auth/local/signup", json={"email": e, "name": n, "password": "pw123456"})
    hb = _login(client, BOSS)
    client.post(f"/auth/local/users/{U}/approve", json={"groups": []}, headers=hb)
    client.patch(f"/auth/access/users/{U}", json={"grants": ["feat:api-token"]}, headers=hb)
    return client, _login(client, U)


def _source(c, h, **body) -> dict:
    r = c.post("/auth/pat", json={"name": "claude", **body}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def _exchange(c, token: str, **over):
    body = {"name": "hwax-risk", "audiences": [AUD], "scopes": ["read"], "ttl_days": 30, **over}
    return c.post("/auth/pat/exchange", json=body, headers={"Authorization": f"Bearer {token}"})


def _refused(r, status: int, code: str) -> dict:
    assert r.status_code == status, r.text
    detail = r.json()["detail"]
    assert detail["code"] == code and detail["message"], detail   # 게이트웨이가 code 로 가른다
    return detail


def _claims(token: str) -> dict:
    return jwt.decode(token, options={"verify_signature": False})


def _revoked(c) -> set[str]:
    return set(c.get("/auth/pat/revoked.json").json()["revoked"])


def _verify(token: str) -> Principal:
    return verify_pat(token, keystore=app.state.keystore,
                      revoked_jtis=app.state.token_store.revoked_jtis(), audience=AUD)


def _me() -> Principal:
    return Principal(subject=U, email=U, display_name="U", groups=[])


# ── 되는 길 ──────────────────────────────────────────────────────────────────
def test_좁힌_PAT_을_같은_사람에게_낸다(box, caplog):
    c, hu = box
    src = _source(c, hu)                                   # 기본 청중 전부 · read+write · 90일
    caplog.set_level("WARNING", logger="app.auth.routes.pat")
    r = _exchange(c, src["token"], ttl_days=7)
    assert r.status_code == 200, r.text
    got = r.json()
    assert got["audiences"] == [AUD] and got["scopes"] == ["read"] and got["revoked"] is False
    assert abs(got["exp"] - (time.time() + 7 * 86400)) < 120 and got["exp"] < src["exp"]
    claims = _claims(got["token"])
    assert claims["aud"] == [AUD] and claims["scopes"] == ["read"] and claims["exp"] == got["exp"]
    assert claims["pat_name"] == "hwax-risk" and "purpose" not in claims
    assert claims["jti"] == got["jti"] != src["jti"]
    p = _verify(got["token"])                              # 게이트웨이·포털이 받는 그 검증
    assert p.subject == _claims(src["token"])["sub"] and p.email == U
    # 토큰 목록에 보이고(폐기할 수 있게), 원장에는 원이 적힌다
    assert got["jti"] in {m["jti"] for m in c.get("/auth/pat").json()}
    row = app.state.token_store._conn.execute(
        "SELECT parent_jti FROM pat WHERE jti = ?", (got["jti"],)).fetchone()
    assert row == (src["jti"],)
    assert any("PAT exchanged:" in m and src["jti"] in m for m in caplog.messages)


def test_만료는_원_PAT_을_넘지_않는다(box):
    c, hu = box
    src = _source(c, hu, ttl_days=2)
    got = _exchange(c, src["token"], ttl_days=30).json()
    assert got["exp"] == src["exp"] == _claims(got["token"])["exp"]


def test_scopes_칸이_없는_옛_원은_read_write_로_본다(box):
    c, _hu = box
    now = datetime.now(tz=UTC)
    ks = app.state.keystore
    old = jwt.encode({"iss": "x", "sub": U, "email": U, "aud": [AUD], "scope": "api",
                      "iat": now, "exp": now + timedelta(days=10), "jti": "legacy-1"},
                     ks.private_pem, algorithm="RS256", headers={"kid": ks.active_kid})
    app.state.token_store.record_pat(jti="legacy-1", sub=U, email=U, name="old", aud=[AUD],
                                     scopes=[], created=int(now.timestamp()),
                                     exp=int((now + timedelta(days=10)).timestamp()))
    _refused(_exchange(c, old, scopes=["read", "write", "admin"]), 400, "widen_scopes")
    assert _exchange(c, old, scopes=["read", "write"]).status_code == 200


# ── 넓히기 거절 ───────────────────────────────────────────────────────────────
def test_청중을_넓히면_거절한다(box):
    c, hu = box
    src = _source(c, hu, audiences=[AUD])
    _refused(_exchange(c, src["token"], audiences=[AUD, "heax-hub"]), 400, "widen_audience")
    # 빈 청중은 `/auth/pat` 에서 '기본 전체' 다 — 교환에서 좁히기로 읽으면 안 된다
    _refused(_exchange(c, src["token"], audiences=[]), 400, "widen_audience")


def test_범위를_넓히면_거절한다(box):
    c, hu = box
    src = _source(c, hu, scopes=["read"])
    _refused(_exchange(c, src["token"], scopes=["read", "write"]), 400, "widen_scopes")


def test_수명은_1일부터_상한까지다(box):
    c, hu = box
    src = _source(c, hu)
    top = get_settings().pat_max_ttl_days
    for bad in (0, -1, top + 1):                           # 0 = 무기한은 교환에 없다
        _refused(_exchange(c, src["token"], ttl_days=bad), 400, "bad_ttl")
    assert _exchange(c, src["token"], ttl_days=top).status_code == 200


@pytest.fixture()
def mints(monkeypatch) -> list:
    """`_mint_pat` 이 불린 횟수 — 거절이 서명 **전에** 나는지 본다."""
    calls: list = []
    real = pat_routes._mint_pat

    def counting(*a, **kw):
        calls.append(kw.get("name"))
        return real(*a, **kw)

    monkeypatch.setattr(pat_routes, "_mint_pat", counting)
    return calls


def _rows() -> int:
    return app.state.token_store._conn.execute("SELECT COUNT(*) FROM pat").fetchone()[0]


# ── 남은 수명(min_remaining_s) ────────────────────────────────────────────────
def test_원이_곧_만료되면_내지_않는다(box, mints):
    c, hu = box
    src = _source(c, hu, ttl_days=2)
    before, mints[:] = _rows(), []
    detail = _refused(_exchange(c, src["token"], min_remaining_s=3 * 86400), 400, "source_expiring")
    assert "원 PAT 자체가 곧 만료된다" in detail["message"] and "새 PAT" in detail["message"]
    assert mints == [] and _rows() == before                # 서명도 기록도 하지 않았다
    assert _exchange(c, src["token"], min_remaining_s=86400).status_code == 200


def test_남은_수명은_ttl_과_원_만료_중_짧은_쪽이다(box, mints):
    """원이 넉넉하면 ttl_days 가 수명이다 — 경계(같으면 낸다)를 시계에 안 기대고 본다."""
    c, hu = box
    src = _source(c, hu)                                   # 90일
    mints.clear()
    assert _exchange(c, src["token"], ttl_days=1, min_remaining_s=86400).status_code == 200
    detail = _refused(_exchange(c, src["token"], ttl_days=1, min_remaining_s=86401),
                      400, "source_expiring")
    assert "ttl_days" in detail["message"]
    assert mints == ["hwax-risk"]                           # 거절된 쪽은 서명하지 않았다
    r = _exchange(c, src["token"], min_remaining_s=-1)      # 음수는 본문 꼴이 틀린 것(422)
    assert r.status_code == 422, r.text


# ── 원 하나의 살아 있는 자식 상한(SEC-5) ──────────────────────────────────────
def test_살아_있는_자식은_원마다_다섯까지다(box, mints):
    c, hu = box
    src, other_src = _source(c, hu), _source(c, hu, name="claude-2")
    kids = [_exchange(c, src["token"], name=f"k{i}").json() for i in range(MAX_LIVE_CHILDREN)]
    mints.clear()
    before = _rows()
    _refused(_exchange(c, src["token"], name="k-over"), 409, "too_many_children")
    assert mints == [] and _rows() == before                # 서명도 기록도 하지 않았다
    assert _exchange(c, other_src["token"]).status_code == 200   # 다른 원은 따로 센다
    assert _revoke_self(c, kids[0]["token"]).status_code == 200   # 폐기한 자식은 안 센다
    assert _exchange(c, src["token"], name="k-again").status_code == 200


def test_자식_상한은_기록할_때_다시_본다(tmp_path):
    """동시 교환 둘이 끝점의 검사를 함께 지나도 기록이 상한을 지킨다. 만료된 자식은 안 센다."""
    ts = TokenStore(Settings(token_store_path=str(tmp_path / "t.sqlite")))
    row = {"sub": U, "email": U, "aud": [AUD], "scopes": ["read"], "created": 1}
    ts.record_pat(jti="p", name="claude", exp=2**31, **row)
    for i in range(MAX_LIVE_CHILDREN):                      # 만료된 자식 다섯 — 세지 않는다
        assert ts.record_exchanged_pat(parent_jti="p", jti=f"old{i}", name="x", exp=1,
                                       **row) is None
    assert ts.live_children("p") == 0
    for i in range(MAX_LIVE_CHILDREN):
        assert ts.record_exchanged_pat(parent_jti="p", jti=f"k{i}", name="x", exp=2**31,
                                       **row) is None
    refused = ts.record_exchanged_pat(parent_jti="p", jti="over", name="x", exp=2**31, **row)
    assert refused == "too_many_children"
    assert ts._conn.execute("SELECT COUNT(*) FROM pat WHERE jti = 'over'").fetchone() == (0,)


# ── 원이 될 수 없는 PAT ───────────────────────────────────────────────────────
def test_챗_PAT_으로는_못_바꾼다(box):
    """24시간짜리 챗 PAT 로 긴 PAT 을 받는 수명 늘리기. 본문은 챗 PAT 기준으로 좁혀 둔다 —
    원장 대조를 빼면 200 이 나야 이 시험이 그 검사를 문다."""
    c, _hu = box
    chat = _chat_user_pat(app.state.keystore, get_settings(), _me())
    assert chat and _claims(chat)["jti"].startswith("chat-")
    _refused(_exchange(c, chat, scopes=["chat"]), 403, "source_not_exchangeable")


def test_절차_PAT_으로는_못_바꾼다(box):
    c, _hu = box
    proc = mint_procedure_pat(app.state.keystore, get_settings(), _me(), "run-1", 0)
    _refused(_exchange(c, proc, scopes=["chat"]), 403, "source_not_exchangeable")
    # 원장에 적혀 있어도 `purpose` 가 있으면 원이 못 된다 — 원장 대조와 따로 문다
    cl = _claims(proc)
    app.state.token_store.record_pat(jti=cl["jti"], sub=cl["sub"], email=U, name="procedures",
                                     aud=[AUD], scopes=["chat"], created=cl["iat"], exp=cl["exp"])
    _refused(_exchange(c, proc, scopes=["chat"]), 403, "source_not_exchangeable")


def test_교환으로_받은_PAT_은_원이_못_된다(box):
    """자식이 원이 되면 연쇄 폐기가 한 단만 내려가 손자가 원 PAT 의 폐기를 피해 산다."""
    c, hu = box
    child = _exchange(c, _source(c, hu)["token"], scopes=["read"]).json()
    _refused(_exchange(c, child["token"], name="grandchild"), 403, "source_not_exchangeable")


def test_폐기된_원은_거절한다(box):
    c, hu = box
    src = _source(c, hu)
    assert c.delete(f"/auth/pat/{src['jti']}", headers=hu).status_code == 200
    _refused(_exchange(c, src["token"]), 401, "invalid_source")


def test_만료된_원은_거절한다(box, monkeypatch):
    c, hu = box

    class _ThreeDaysAgo(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.now(tz) - timedelta(days=3)

    with monkeypatch.context() as m:                       # 진짜 /auth/pat 길로, 사흘 전에 1일짜리
        m.setattr(pat_routes, "datetime", _ThreeDaysAgo)
        src = _source(c, hu, ttl_days=1)
    assert src["exp"] < time.time() - 86400
    _refused(_exchange(c, src["token"]), 401, "invalid_source")


def test_게이트웨이_청중이_없는_원은_거절한다(box):
    c, hu = box
    src = _source(c, hu, audiences=["heax-hub"])
    _refused(_exchange(c, src["token"], audiences=["heax-hub"]), 401, "invalid_source")


# ── 인증 길·권한 ──────────────────────────────────────────────────────────────
def test_세션_쿠키로는_못_부른다(box):
    """웹은 `/auth/pat` 이 있다. 쿠키 + CSRF 를 다 실어도 Bearer 가 없으면 401 이다."""
    c, hu = box
    _source(c, hu)
    body = {"name": "hwax-risk", "audiences": [AUD], "scopes": ["read"], "ttl_days": 30}
    detail = _refused(c.post("/auth/pat/exchange", json=body, headers=hu), 401, "invalid_source")
    assert "Bearer" in detail["message"]


def test_api_token_허가가_없으면_거절한다(box):
    c, hu = box
    src = _source(c, hu)
    app.state.user_store.set_access(U, grants=[])          # 원장에서 거둔다(토큰은 그대로 둔다)
    _refused(_exchange(c, src["token"]), 403, "permission_denied")


def test_정지된_계정은_거절한다(box):
    c, hu = box
    src = _source(c, hu)
    app.state.user_store.set_status(U, "disabled")         # 화면 정지와 달리 PAT 을 폐기하지 않는다
    _refused(_exchange(c, src["token"]), 403, "account_disabled")


# ── 같은 이름·연쇄 폐기 ───────────────────────────────────────────────────────
def test_같은_이름으로_다시_바꿔도_앞선_것은_산다(box):
    """교환이 앞선 것을 폐기하면, 소비자가 새것을 거절했을 때 폐기된 옛것만 쥐고 남는다(C-11).
    옛것은 소비자가 새것을 받아들인 뒤 revoke-self 로 죽인다."""
    c, hu = box
    src = _source(c, hu)
    first = _exchange(c, src["token"]).json()
    second = _exchange(c, src["token"]).json()
    assert not {first["jti"], second["jti"], src["jti"]} & _revoked(c)
    assert _verify(first["token"]).email == _verify(second["token"]).email == U


def test_원을_폐기하면_자식도_폐기된다(box):
    c, hu = box
    src = _source(c, hu)
    child = _exchange(c, src["token"]).json()
    assert _verify(child["token"]).email == U
    assert c.delete(f"/auth/pat/{src['jti']}", headers=hu).status_code == 200
    assert {src["jti"], child["jti"]} <= _revoked(c)       # 게이트웨이가 당겨 가는 폐기 목록
    with pytest.raises(ValueError, match="revoked"):
        _verify(child["token"])
    listed = {m["jti"]: m["revoked"] for m in c.get("/auth/pat", headers=hu).json()}
    assert listed[child["jti"]] is True


def test_검사_뒤_원이_폐기되면_자식을_기록하지_않는다(tmp_path):
    """검사와 기록 사이에 원이 폐기되면 연쇄가 아직 없는 자식을 못 본다 — 기록이 원을 다시 본다."""
    ts = TokenStore(Settings(token_store_path=str(tmp_path / "t.sqlite")))
    row = {"sub": U, "email": U, "aud": [AUD], "scopes": ["read"], "created": 1, "exp": 2**31}
    ts.record_pat(jti="p", name="claude", **row)
    ts.revoke_pat("p")
    refused = ts.record_exchanged_pat(parent_jti="p", jti="k", name="hwax-risk", **row)
    assert refused == "source_revoked"
    assert ts._conn.execute("SELECT COUNT(*) FROM pat WHERE jti = 'k'").fetchone() == (0,)


def test_돌고_있는_원장에_parent_jti_칸이_생긴다(tmp_path):
    path = tmp_path / "old.sqlite"
    old = sqlite3.connect(path)
    old.execute("CREATE TABLE pat (jti TEXT PRIMARY KEY, sub TEXT NOT NULL, email TEXT, name TEXT, "
                "aud TEXT NOT NULL, scopes TEXT NOT NULL, created INTEGER NOT NULL, "
                "exp INTEGER NOT NULL, revoked INTEGER NOT NULL DEFAULT 0)")
    old.execute("INSERT INTO pat VALUES ('p', ?, ?, 'claude', '[]', '[]', 1, ?, 0)", (U, U, 2**31))
    old.commit()
    old.close()
    ts = TokenStore(Settings(token_store_path=str(path)))
    TokenStore(Settings(token_store_path=str(path)))      # 두 번째 기동도 멀쩡하다(멱등)
    assert ts.record_exchanged_pat(parent_jti="p", jti="k", sub=U, email=U, name="hwax-risk",
                                   aud=[AUD], scopes=["read"], created=1, exp=2**31) is None
    assert {m["jti"] for m in ts.list_pats(U)} == {"k", "p"}      # 옛 행이 그대로 있다
    assert ts.revoke_pat("p", U)
    assert set(ts.revoked_jtis()) == {"p", "k"}


# ── revoke-self(소비자가 새것을 받아들인 뒤 옛것을 죽이는 길, C-11) ───────────────────
def _revoke_self(c, token: str, **kw):
    return c.post("/auth/pat/revoke-self", headers={"Authorization": f"Bearer {token}"}, **kw)


def test_revoke_self_는_그_토큰만_폐기한다(box):
    """본문·쿼리에 남의 jti 를 실어도 Bearer 토큰 자신만 죽는다 — 형제·원·손으로 낸 같은 이름·
    남의 것은 산다."""
    c, hu = box
    manual = _source(c, hu, name="hwax-risk")
    hb = _login(c, BOSS)
    boss_child = _exchange(c, _source(c, hb)["token"]).json()
    hu = _login(c, U)
    src = _source(c, hu)
    first = _exchange(c, src["token"]).json()
    second = _exchange(c, src["token"]).json()
    r = _revoke_self(c, first["token"], json={"jti": second["jti"]},
                     params={"jti": boss_child["jti"]})
    assert r.status_code == 200 and r.json() == {"revoked": first["jti"]}, r.text
    revoked = _revoked(c)
    assert first["jti"] in revoked
    assert not {second["jti"], manual["jti"], boss_child["jti"], src["jti"]} & revoked
    with pytest.raises(ValueError, match="revoked"):
        _verify(first["token"])
    assert _verify(second["token"]).email == U


def test_revoke_self_로_원을_죽이면_자식도_죽는다(box):
    c, hu = box
    src = _source(c, hu)
    child = _exchange(c, src["token"]).json()
    assert _revoke_self(c, src["token"]).json() == {"revoked": src["jti"]}
    assert {src["jti"], child["jti"]} <= _revoked(c)


def test_revoke_self_는_멱등이다(box):
    """응답을 잃은 재시도·연쇄로 이미 폐기된 자식도 200 — 실패처럼 보이면 소비자가 옛것이 살아
    있다고 읽는다."""
    c, hu = box
    src = _source(c, hu)
    child = _exchange(c, src["token"]).json()
    for _ in range(2):
        r = _revoke_self(c, child["token"])
        assert r.status_code == 200 and r.json() == {"revoked": child["jti"]}, r.text
    other = _exchange(c, src["token"], name="other").json()
    # 원을 폐기하면 연쇄로 other 도 폐기된다
    assert c.delete(f"/auth/pat/{src['jti']}", headers=hu).status_code == 200
    r = _revoke_self(c, other["token"])
    assert r.status_code == 200 and r.json() == {"revoked": other["jti"]}, r.text


def test_revoke_self_는_기록되지_않은_PAT_에_404(box):
    c, _hu = box
    chat = _chat_user_pat(app.state.keystore, get_settings(), _me())
    proc = mint_procedure_pat(app.state.keystore, get_settings(), _me(), "run-1", 0)
    for tok in (chat, proc):
        _refused(_revoke_self(c, tok), 404, "not_recorded")


def test_revoke_self_는_유효한_Bearer_만_받는다(box, monkeypatch):
    c, hu = box
    _source(c, hu)
    _refused(c.post("/auth/pat/revoke-self", headers=hu), 401, "invalid_token")   # 쿠키 + CSRF 만
    _refused(_revoke_self(c, "not-a-jwt"), 401, "invalid_token")
    _refused(_revoke_self(c, _source(c, hu, audiences=["heax-hub"])["token"]), 401, "invalid_token")

    class _ThreeDaysAgo(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.now(tz) - timedelta(days=3)

    with monkeypatch.context() as m:
        m.setattr(pat_routes, "datetime", _ThreeDaysAgo)
        old = _source(c, hu, ttl_days=1)
    _refused(_revoke_self(c, old["token"]), 401, "invalid_token")
