# 전문가 팀 API(/agent/teams) — 권한 · 보이기(주인 · 같은 소속 · 관리자) · 상한 · 판 번호 409 · 공식 표지 · 그 사람의 시야로 푼 사본 · 지운 팀(docs/expert-teams)
"""실제 로그인 다섯 사람 — boss(원장 관리자) · me · peer(CAEG — 전부) · out(소속 없음 + 개별 허가 feat:expert-chat 만 — HE팀 운영자의 앱 권한이 없다) ·
plain(feat:chat 뿐). 저장소는 임시 폴더다(절차 저장소의 연결을 같이 쓴다)."""
import pytest
from fastapi.testclient import TestClient

from app.agent.teams import TeamStore
from app.auth.cookies import CSRF_COOKIE
from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.main import app
from app.procedures.store import ProceduresStore

PW = "pw123456"
P = "/agent/teams"
OP = "he-cad-stepforge"      # HE팀 운영자 — StepForge 앱 권한이 있어야 쓴다(agent_guard.persona_allowed)
TEAM = {"name": "힌지 낙하 검토팀", "description": "힌지 낙하 결과를 볼 때",
        "lead": {"key": "mech-a", "name": "기구 강도 전문가"},
        "helpers": [{"key": "cae-b", "name": "구조 해석 전문가"}, {"key": OP, "name": "StepForge 운영자"}],
        "apps": ["step_forge"], "tools": ["section_atlas"]}


def _login(c, email) -> dict:
    c.cookies.clear()
    assert c.post("/auth/local/login", json={"email": email, "password": PW}).status_code == 200
    return {"X-CSRF-Token": c.cookies.get(CSRF_COOKIE)}


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.delenv("PORTAL_ADMIN_EMAILS", raising=False)
    s = Settings(_env_file=None, user_store_path=str(tmp_path / "users.sqlite"), token_store_path=str(tmp_path / "tokens.sqlite"),
                 conv_store_path=str(tmp_path / "conv.sqlite"), procedures_store_path=str(tmp_path / "procedures.sqlite"),
                 conn_key_path=str(tmp_path / "conn.key"), local_bootstrap_admins="boss@example.com")
    app.dependency_overrides[get_settings] = lambda: s
    from app.auth.routes.local import _rl
    _rl.clear()
    with TestClient(app) as c:
        keep = (app.state.user_store, app.state.team_store)
        ps = ProceduresStore(s)
        app.state.user_store, app.state.team_store = UserStore(s), TeamStore(ps)
        for email in ("boss@example.com", "me@example.com", "peer@example.com", "out@example.com", "plain@example.com"):
            assert c.post("/auth/local/signup", json={"email": email, "name": email.split("@")[0], "password": PW}).status_code < 300
        for email in ("me@example.com", "peer@example.com", "out@example.com", "plain@example.com"):
            assert app.state.user_store.approve(email, by="boss@example.com", groups=[])
        hb = _login(c, "boss@example.com")
        for email in ("me@example.com", "peer@example.com"):
            assert c.patch(f"/auth/access/users/{email}", json={"affiliation": "CAEG"}, headers=hb).status_code == 200
        assert c.patch("/auth/access/users/out@example.com", json={"grants": ["feat:expert-chat"]}, headers=hb).status_code == 200
        c.cookies.clear()
        yield c, app.state.team_store
        app.state.user_store, app.state.team_store = keep
        ps.close()
    app.dependency_overrides.pop(get_settings, None)


def _make(c, who="me@example.com", **over) -> dict:
    h = _login(c, who)
    r = c.post(P, json={**TEAM, **over}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def _ids(c) -> list:
    r = c.get(P)
    assert r.status_code == 200, r.text
    return [t["id"] for t in r.json()["teams"]]


def _routes():
    out = []
    for r in app.routes:
        path = getattr(r, "path", "")
        if path.startswith(P):
            out += [(m, path) for m in sorted(getattr(r, "methods", set()) - {"HEAD", "OPTIONS"})]
    return sorted(out)


def test_전문가와_대화_권한이_없으면_모든_팀_라우트가_403(env):
    c, _ = env
    routes = _routes()
    assert len(routes) == 6, routes
    h = _login(c, "plain@example.com")
    for m, path in routes:
        url = path.replace("{tid}", "tm_" + "0" * 32)
        r = c.request(m, url, headers=h, json={**TEAM, "expected_version": 1} if m == "PATCH" else {"on": True} if
                      path.endswith("/official") else TEAM if m == "POST" else None)
        assert r.status_code == 403, (m, path, r.status_code, r.text[:200])


def test_쓰기는_세션과_CSRF_만(env):
    c, _ = env
    _login(c, "me@example.com")
    assert c.post(P, json=TEAM).status_code == 403, "CSRF 없이 만들지 않는다"
    c.cookies.clear()
    assert c.post(P, json=TEAM, headers={"Authorization": "Bearer x.y.z"}).status_code == 401, "PAT 로는 쓰지 않는다"


def test_나만은_주인만_같은_소속은_소속끼리_관리자는_전부_보고_없는_것과_못_보는_것은_같은_404(env):
    c, _ = env
    t = _make(c)
    assert t["id"].startswith("tm_") and t["version"] == 1 and t["owner_aff"] == "CAEG" and t["scope"] == "private"
    assert t["mine"] and t["editable"] and t["deletable"] and not t["official"]
    for who in ("peer@example.com", "out@example.com"):
        _login(c, who)
        assert t["id"] not in _ids(c)
        assert c.get(f"{P}/{t['id']}/resolve").json()["team"] is None
    h = _login(c, "peer@example.com")
    gone = c.patch(f"{P}/{t['id']}", json={"expected_version": 1, "name": "x"}, headers=h)
    nothing = c.patch(f"{P}/tm_{'0' * 32}", json={"expected_version": 1, "name": "x"}, headers=h)
    assert gone.status_code == nothing.status_code == 404 and gone.json() == nothing.json()
    h = _login(c, "me@example.com")
    r = c.patch(f"{P}/{t['id']}", json={"expected_version": 1, "scope": "org"}, headers=h)
    assert r.status_code == 200 and r.json()["scope"] == "org" and r.json()["version"] == 2, r.text
    h = _login(c, "peer@example.com")
    row = next(x for x in c.get(P).json()["teams"] if x["id"] == t["id"])
    assert not row["mine"] and not row["editable"] and not row["deletable"] and row["owner_email"] == "me@example.com"
    assert c.patch(f"{P}/{t['id']}", json={"expected_version": 2, "name": "남의 팀"}, headers=h).status_code == 403
    assert c.delete(f"{P}/{t['id']}", headers=h).status_code == 403
    _login(c, "out@example.com")
    assert t["id"] not in _ids(c), "다른(없는) 소속은 같은 소속 공유를 못 본다"
    _login(c, "boss@example.com")
    row = next(x for x in c.get(P).json()["teams"] if x["id"] == t["id"])
    assert row["editable"] and row["deletable"] and not row["mine"], "관리자는 다 보고 고친다"


def test_소속이_바뀌면_같은_소속_공유도_바뀐다(env):
    c, _ = env
    t = _make(c, scope="org")
    _login(c, "peer@example.com")
    assert t["id"] in _ids(c)
    hb = _login(c, "boss@example.com")
    assert c.patch("/auth/access/users/peer@example.com", json={"affiliation": "", "grants": ["feat:expert-chat"]},
                   headers=hb).status_code == 200
    _login(c, "peer@example.com")
    assert t["id"] not in _ids(c)


@pytest.mark.parametrize("over, say", [
    ({"name": "가" * 61}, "name"), ({"name": "   "}, "이름"), ({"description": "가" * 301}, "description"),
    ({"helpers": [{"key": f"h{i}"} for i in range(5)]}, "helpers"), ({"apps": ["a", "b", "c", "d"]}, "apps"),
    ({"tools": [f"t{i}" for i in range(13)]}, "tools"), ({"helpers": [{"key": "mech-a"}]}, "주 전문가"),
    ({"helpers": [{"key": "x"}, {"key": "x"}]}, "겹친다"), ({"lead": {"key": "a b"}}, "키 꼴"), ({"apps": ["a/b"]}, "앱"),
    ({"scope": "all"}, "scope"), ({"owner_email": "boss@example.com"}, "owner_email"),
])
def test_상한과_칸_규칙(env, over, say):
    c, _ = env
    h = _login(c, "me@example.com")
    r = c.post(P, json={**TEAM, **over}, headers=h)
    assert r.status_code == 422 and say in r.text, r.text[:400]


def test_소속이_없으면_같은_소속으로_공유하지_못한다(env):
    c, _ = env
    h = _login(c, "out@example.com")
    r = c.post(P, json={**TEAM, "scope": "org"}, headers=h)
    assert r.status_code == 422 and "소속이 없어" in r.json()["detail"], r.text
    assert c.post(P, json=TEAM, headers=h).status_code == 201


def test_판_번호가_어긋나면_409_이고_고치지_않는다(env):
    c, st = env
    t = _make(c)
    h = _login(c, "me@example.com")
    ok = c.patch(f"{P}/{t['id']}", json={"expected_version": 1, "helpers": [{"key": "cae-b", "name": "구조"}]}, headers=h)
    assert ok.status_code == 200 and ok.json()["version"] == 2 and [x["key"] for x in ok.json()["helpers"]] == ["cae-b"]
    stale = c.patch(f"{P}/{t['id']}", json={"expected_version": 1, "name": "늦은 고침"}, headers=h)
    assert stale.status_code == 409 and "지금 판 2" in stale.json()["detail"], stale.text
    assert st.get(t["id"])["name"] == TEAM["name"] and st.get(t["id"])["version"] == 2
    bad = c.patch(f"{P}/{t['id']}", json={"expected_version": 2, "helpers": [{"key": "mech-a"}]}, headers=h)
    assert bad.status_code == 422, "고친 뒤의 전체 칸 규칙도 다시 본다"


def test_공식_표지는_관리자만_달고_떼며_목록_맨_앞이고_주인은_공식_팀을_지우지_못한다(env):
    c, _ = env
    a = _make(c, name="먼저 만든 팀", scope="org")
    b = _make(c, name="나중 만든 팀", scope="org")
    h = _login(c, "me@example.com")
    assert c.post(f"{P}/{a['id']}/official", json={"on": True}, headers=h).status_code == 403
    assert _ids(c)[:2] == [b["id"], a["id"]], "최근 고친 것 먼저"
    hb = _login(c, "boss@example.com")
    r = c.post(f"{P}/{a['id']}/official", json={"on": True}, headers=hb)
    assert r.status_code == 200 and r.json()["official"] and r.json()["version"] == a["version"], "공식 표지는 판을 바꾸지 않는다"
    for who in ("me@example.com", "peer@example.com"):
        _login(c, who)
        assert _ids(c)[:2] == [a["id"], b["id"]], "공식 먼저"
    h = _login(c, "me@example.com")
    row = next(x for x in c.get(P).json()["teams"] if x["id"] == a["id"])
    assert row["editable"] and not row["deletable"]
    r = c.delete(f"{P}/{a['id']}", headers=h)
    assert r.status_code == 403 and "관리자만" in r.json()["detail"]
    assert c.patch(f"{P}/{a['id']}", json={"expected_version": 1, "description": "주인은 고친다"}, headers=h).status_code == 200
    hb = _login(c, "boss@example.com")
    assert c.post(f"{P}/{a['id']}/official", json={"on": False}, headers=hb).json()["official"] is False
    assert c.post(f"{P}/{a['id']}/official", json={"on": True}, headers=hb).status_code == 200
    assert c.delete(f"{P}/{a['id']}", headers=hb).status_code == 200
    _login(c, "me@example.com")
    assert a["id"] not in _ids(c)


def test_사본은_그_사람의_권한으로_풀고_못_쓰는_보조는_빼고_알린다(env):
    c, _ = env
    t = _make(c, scope="org")
    _login(c, "me@example.com")
    got = c.get(f"{P}/{t['id']}/resolve").json()
    snap = got["team"]
    assert got["why"] == "" and got["hidden"] == []
    assert set(snap) == {"id", "name", "version", "lead", "helpers", "apps", "tools", "resolved_at"}, snap
    assert snap["lead"] == TEAM["lead"] and snap["helpers"] == TEAM["helpers"] and snap["apps"] == ["step_forge"]
    assert snap["tools"] == ["section_atlas"] and snap["version"] == 1 and isinstance(snap["resolved_at"], int)
    # out — 자기 팀(StepForge 앱 권한 없음): 운영자 보조는 빠지고 까닭 · 빠진 사람이 남는다
    o = _make(c, who="out@example.com")
    _login(c, "out@example.com")
    got = c.get(f"{P}/{o['id']}/resolve").json()
    assert [h["key"] for h in got["team"]["helpers"]] == ["cae-b"], got
    assert OP in got["why"] and got["hidden"] == [{"key": OP, "name": "StepForge 운영자"}]
    # 주 전문가를 못 쓰면 사본이 없다(닫힌 쪽)
    o2 = _make(c, who="out@example.com", lead={"key": OP, "name": "운영자"}, helpers=[{"key": "cae-b"}])
    _login(c, "out@example.com")
    got = c.get(f"{P}/{o2['id']}/resolve").json()
    assert got["team"] is None and "주 전문가" in got["why"], got


def test_지운_팀은_사본이_null_이고_까닭이_있다(env):
    c, _ = env
    t = _make(c)
    h = _login(c, "me@example.com")
    assert c.delete(f"{P}/{t['id']}", headers=h).status_code == 200
    got = c.get(f"{P}/{t['id']}/resolve")
    assert got.status_code == 200 and got.json()["team"] is None and "찾을 수 없다" in got.json()["why"]
    assert c.delete(f"{P}/{t['id']}", headers=h).status_code == 404
    assert c.get(f"{P}/아무거나/resolve").json()["team"] is None
