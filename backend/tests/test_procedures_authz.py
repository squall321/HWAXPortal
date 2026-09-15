# 남의 절차에 닿는 길 — **전수**로 막혔는지 본다(2026-09-15 감사에서 뚫려 있었다)
#
# 무엇이 뚫려 있었나. 둘 다 재현해서 확인했다.
#   ① `POST /procedures/{id}/versions` 에 주인 확인이 없었다. 아무나 남의 절차에 판본을
#      얹으면 그것이 최신이 되고, 제목은 그대로라 목록에서는 **아무 일도 없어 보인다.**
#      주인이 그걸 돌리면 실행 PAT 는 **부르는 사람**에게서 나오므로 남이 쓴 단계가
#      주인 명의로 돈다. 원장에는 주인이 한 일로 남는다.
#   ② `visibility='private'` 는 **목록에서만** 걸렸다. id 만 있으면 읽기·내보내기·
#      도구계약·실행이 전부 열렸다.
#
# 손으로 고른 몇 개가 아니라 전수인 이유. 절차 라우트는 계속 는다. 나중에 단
# `/{procedure_id}/...` 하나가 게이트를 빼먹으면 이 검사가 잡아야 한다.
import pytest
from fastapi.testclient import TestClient

from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.main import app
from app.procedures.store import ProceduresStore
from tests.test_procedures_routes import PREFIX, _offline_runner, _routes

SPEC = {"title": "원본", "vars": [],
        "steps": [{"backend": "aidatahub", "tool": "list_records", "args": {}}]}
EVIL = {"title": "탈취", "vars": [],
        "steps": [{"backend": "reportarchive", "tool": "create_report_draft",
                   "args": {"title": "남이 쓴 단계"}}]}


@pytest.fixture()
def client(tmp_path):
    s = Settings(user_store_path=str(tmp_path / "users.sqlite"),
                 procedures_store_path=str(tmp_path / "wb.sqlite"),
                 local_bootstrap_admins="boss@corp.com",
                 gateway_shared_token="gw-test-secret")
    app.dependency_overrides[get_settings] = lambda: s
    from app.auth.routes.local import _rl

    _rl.clear()
    with TestClient(app) as c:
        app.state.user_store = UserStore(s)
        app.state.procedures_store = ProceduresStore(s)
        app.state.procedures_runner = _offline_runner(s)
        yield c
        app.state.procedures_runner = None
    app.dependency_overrides.pop(get_settings, None)


def _login(c, email):
    assert c.post("/auth/local/login",
                  json={"email": email, "password": "pw123456"}).status_code == 200
    return {"X-CSRF-Token": c.cookies.get("hwax_csrf")}


def _two(c):
    """앨리스와 말로리 — **둘 다 정당한 사용자**다. 권한이 없어서 막히는 게 아니라,
    권한이 있어도 남의 것이라 막혀야 한다는 것이 요점이다."""
    c.post("/auth/local/signup",
           json={"email": "boss@corp.com", "name": "B", "password": "pw123456"})
    for e in ("alice@corp.com", "mallory@corp.com"):
        c.post("/auth/local/signup", json={"email": e, "name": e, "password": "pw123456"})
    h = _login(c, "boss@corp.com")
    for e in ("alice@corp.com", "mallory@corp.com"):
        assert c.post(f"/auth/local/users/{e}/approve", json={"groups": []},
                      headers=h).status_code == 200
        assert c.patch(f"/auth/access/users/{e}", json={"grants": ["feat:procedures"]},
                       headers=h).status_code == 200


def _make(c, h, *, visibility="all", title="앨리스 절차"):
    r = c.post(f"{PREFIX}/procedures",
               json={"title": title, "spec": SPEC, "visibility": visibility}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


# ── ① 쓰기 ───────────────────────────────────────────────────────────────
def test_남의_절차에는_판본을_못_얹는다(client):
    c = client
    _two(c)
    got = _make(c, _login(c, "alice@corp.com"))
    hm = _login(c, "mallory@corp.com")
    # 공유라 목록에 보이는 것은 맞다 — 보이는 것과 고치는 것은 다르다
    assert got["id"] in [p["id"] for p in
                         c.get(f"{PREFIX}/procedures", headers=hm).json()["procedures"]]

    r = c.post(f"{PREFIX}/procedures/{got['id']}/versions",
               json={"title": "탈취", "spec": EVIL}, headers=hm)
    assert r.status_code == 404, r.text

    ha = _login(c, "alice@corp.com")
    body = c.get(f"{PREFIX}/procedures/{got['id']}", headers=ha).json()
    assert body["spec"]["title"] == "원본", "남이 얹은 본문이 주인의 최신이 됐다"


# ── ② 읽기 ───────────────────────────────────────────────────────────────
def test_남의_private_에_닿는_모든_라우트가_404(client):
    """**전수**다 — `{procedure_id}` 를 받는 라우트를 전부 훑는다."""
    c = client
    _two(c)
    got = _make(c, _login(c, "alice@corp.com"), visibility="private", title="비공개")
    hm = _login(c, "mallory@corp.com")

    paths = [(m, p) for m, p in _routes() if "{procedure_id}" in p]
    assert len(paths) >= 4, f"라우트를 못 찾았다 — 경로 이름이 바뀌었나: {paths}"
    leaked = []
    for method, path in paths:
        url = path.replace("{procedure_id}", got["id"]).replace("{ix}", "0")
        r = c.request(method, url, json={"title": "x", "spec": SPEC}, headers=hm)
        if r.status_code not in (403, 404):
            leaked.append((method, path, r.status_code))
    assert not leaked, f"남의 private 에 닿은 라우트: {leaked}"


def test_남의_private_판본은_실행도_못_한다(client):
    """`POST /runs` 는 경로에 절차 id 가 없어 위 전수에 안 잡힌다 — 따로 본다."""
    c = client
    _two(c)
    got = _make(c, _login(c, "alice@corp.com"), visibility="private", title="비공개")
    hm = _login(c, "mallory@corp.com")
    for body in ({"version_id": got["version_id"], "mode": "plan"},
                 {"procedure_id": got["id"], "mode": "plan"}):
        assert c.post(f"{PREFIX}/runs", json=body, headers=hm).status_code == 404, body


def test_공유_절차는_남도_읽고_돌린다(client):
    """게이트가 **너무 세게** 잠기지 않았는지 — 절차는 공유 자산이다(PLAN §1).

    이 짝이 없으면 위 두 검사는 '전부 404 로 만들면 통과' 가 된다.
    """
    c = client
    _two(c)
    got = _make(c, _login(c, "alice@corp.com"))
    hm = _login(c, "mallory@corp.com")
    for suffix in ("", "/tool", "/export"):
        r = c.get(f"{PREFIX}/procedures/{got['id']}{suffix}", headers=hm)
        assert r.status_code == 200, (suffix, r.text[:120])
    assert c.post(f"{PREFIX}/runs", json={"procedure_id": got["id"], "mode": "plan"},
                  headers=hm).status_code == 202


def test_남의_주소가_딸려_나오지_않는다(client):
    """로컬 계정은 `author_sub` 이 **이메일**이다. 내보내기는 이미 떼고 있었다."""
    c = client
    _two(c)
    got = _make(c, _login(c, "alice@corp.com"))
    body = c.get(f"{PREFIX}/procedures/{got['id']}",
                 headers=_login(c, "mallory@corp.com")).json()
    assert "author_sub" not in body, body
