# 허브에 보일 앱 — 포털 스위치 저장·검증·게이트웨이 전달(docs/mcp-app-toggle)
#
# 게이트웨이는 HTTP 전송 계층만 가짜로 둔다 — `/tools-map` 을 읽는 코드와 `/conn-invalidate` 를 부르는 코드는
# 진짜로 돈다(앱 목록 함수를 가짜로 갈아 끼우면 그 함수의 거름·실패 처리를 시험이 베껴 쓰게 된다).
import sqlite3

import httpx
import pytest
from fastapi.testclient import TestClient

from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.main import app

APPS = [
    {"app": "_gateway", "label": "허브", "tool_count": 8, "reachable": True},
    {"app": "heax-step_forge", "label": "StepForge", "tool_count": 129, "reachable": True},
    {"app": "signalforge", "label": "SignalForge", "tool_count": 34, "reachable": True},
    {"app": "reportarchive", "label": "Report Archive", "tool_count": 70, "reachable": False},
]


class _Gateway:
    def __init__(self):
        self.calls: list[tuple[str, str, dict]] = []
        self.down = False
        self.apps = list(APPS)

    def handle(self, req: httpx.Request) -> httpx.Response:
        self.calls.append((req.method, req.url.path, dict(req.url.params)))
        if self.down:
            raise httpx.ConnectError("gateway down")
        if req.url.path.endswith("/tools-map"):
            return httpx.Response(200, json={"apps": self.apps})
        if req.url.path.endswith("/conn-invalidate"):
            return httpx.Response(200, json={"ok": True})
        return httpx.Response(404)


@pytest.fixture()
def env(tmp_path, monkeypatch):
    s = Settings(user_store_path=str(tmp_path / "users.sqlite"), local_bootstrap_admins="boss@corp.com",
                 gateway_shared_token="gw-test-secret")
    app.dependency_overrides[get_settings] = lambda: s
    from app.auth.routes.local import _rl

    _rl.clear()
    gw = _Gateway()
    real = httpx.AsyncClient

    class _Client(real):
        def __init__(self, *a, **k):
            k["transport"] = httpx.MockTransport(gw.handle)
            super().__init__(*a, **k)

    with TestClient(app) as c:
        app.state.user_store = UserStore(s)          # 컨텍스트 진입 후 교체(실DB 오염 방지)
        monkeypatch.setattr(httpx, "AsyncClient", _Client)   # 진입 뒤 — 앱이 시작 때 만든 클라이언트는 그대로
        c.post("/auth/local/signup", json={"email": "boss@corp.com", "name": "Boss", "password": "pw123456"})
        c.post("/auth/local/signup", json={"email": "user@corp.com", "name": "User", "password": "pw123456"})
        h = _login(c, "boss@corp.com")
        assert c.post("/auth/local/users/user@corp.com/approve", json={"groups": []}, headers=h).status_code == 200
        yield c, gw
    app.dependency_overrides.pop(get_settings, None)


def _login(c, email):
    r = c.post("/auth/local/login", json={"email": email, "password": "pw123456"})
    assert r.status_code == 200, r.text
    return {"X-CSRF-Token": c.cookies.get("hwax_csrf")}


def _ent(c, email):
    return c.get("/internal/access/entitlements", params={"email": email},
                 headers={"Authorization": "Bearer gw-test-secret"}).json()


def test_앱_표는_게이트웨이_목록에서_허브_자체_도구를_빼고_권한을_붙인다(env):
    c, _ = env
    _login(c, "user@corp.com")
    body = c.get("/auth/access/apps").json()
    rows = {r["app"]: r for r in body["apps"]}
    assert "_gateway" not in rows, "허브 자체 도구는 끌 수 없다"
    assert rows["heax-step_forge"]["tool_count"] == 129 and rows["reportarchive"]["reachable"] is False
    assert rows["heax-step_forge"]["allowed"] is False, "기본 사용자는 StepForge 권한이 없다(표에 그대로 보인다)"
    assert not any(r["muted"] for r in rows.values()) and "재연결" in body["note"]
    _login(c, "boss@corp.com")
    assert {r["app"]: r for r in c.get("/auth/access/apps").json()["apps"]}["heax-step_forge"]["allowed"] is True


def _put(c, h, app, muted):
    return c.put(f"/auth/access/apps/{app}", json={"muted": muted}, headers=h)


def test_끄면_저장되고_게이트웨이_캐시를_깨고_게이트웨이가_읽는_응답에_실린다(env):
    c, gw = env
    h = _login(c, "user@corp.com")
    assert _ent(c, "user@corp.com")["muted_apps"] == []
    r = _put(c, h, "signalforge", True)
    assert r.status_code == 200, r.text
    assert {x["app"] for x in r.json()["apps"] if x["muted"]} == {"signalforge"}
    assert ("POST", "/conn-invalidate", {"email": "user@corp.com"}) in gw.calls, "안 깨면 최대 60초 늦게 먹는다"
    assert _put(c, h, "heax-step_forge", True).status_code == 200
    assert _ent(c, "user@corp.com")["muted_apps"] == ["heax-step_forge", "signalforge"]
    assert _ent(c, "boss@corp.com")["muted_apps"] == [], "남의 설정에 섞이지 않는다"
    assert _put(c, h, "signalforge", False).status_code == 200
    assert _ent(c, "user@corp.com")["muted_apps"] == ["heax-step_forge"], "다시 켜기 — 다른 앱은 그대로"


def test_두_탭이_앱_하나씩_바꿔도_서로를_덮지_않는다(env):
    """종전엔 화면이 자기 옛 목록 전체를 보내 다른 탭의 선택을 조용히 되돌렸다(검토 2026-09-29)."""
    c, _ = env
    h = _login(c, "user@corp.com")
    tab_a = c.get("/auth/access/apps").json()      # 두 탭 모두 '아무것도 안 끔' 을 보고 있다
    tab_b = c.get("/auth/access/apps").json()
    assert tab_a["muted"] == tab_b["muted"] == []
    _put(c, h, "signalforge", True)                 # 탭 A
    _put(c, h, "heax-step_forge", True)             # 탭 B — 옛 화면에서 눌렀어도 A 의 선택을 지우지 않는다
    assert _ent(c, "user@corp.com")["muted_apps"] == ["heax-step_forge", "signalforge"]


@pytest.mark.parametrize("app,code", [("_gateway", 400), ("no-such-app", 400), ("bad key!", 400)])
def test_모르는_앱과_허브_자체는_끌_수_없다(env, app, code):
    c, _ = env
    h = _login(c, "user@corp.com")
    assert _put(c, h, app, True).status_code == code
    assert _ent(c, "user@corp.com")["muted_apps"] == []


def test_CSRF_없이는_못_바꾼다(env):
    c, _ = env
    _login(c, "user@corp.com")
    assert c.put("/auth/access/apps/signalforge", json={"muted": True}).status_code == 403
    assert _ent(c, "user@corp.com")["muted_apps"] == []


def test_게이트웨이에서_빠진_앱의_끈_기록은_보이고_켜서_지울_수_있다(env):
    c, gw = env
    h = _login(c, "user@corp.com")
    _put(c, h, "signalforge", True)
    gw.apps = [a for a in APPS if a["app"] != "signalforge"]          # 게이트웨이에서 잠시 빠졌다
    rows = {r["app"]: r for r in c.get("/auth/access/apps").json()["apps"]}
    assert rows["signalforge"]["muted"] and rows["signalforge"].get("absent") is True
    assert _put(c, h, "signalforge", True).status_code == 400, "지금 없는 앱을 새로 끌 수는 없다"
    assert _put(c, h, "signalforge", False).status_code == 200, "빠진 앱의 끈 기록은 켜서 지울 수 있다(막히면 화면이 그 앱 때문에 계속 실패한다)"
    assert _ent(c, "user@corp.com")["muted_apps"] == []


def test_게이트웨이에_못_닿으면_모름이지_빈_목록이_아니다(env):
    c, gw = env
    h = _login(c, "user@corp.com")
    gw.down = True
    assert c.get("/auth/access/apps").status_code == 502
    assert _put(c, h, "signalforge", True).status_code == 502
    assert _ent(c, "user@corp.com")["muted_apps"] == []


def test_옛_DB_에도_칸이_생긴다(tmp_path):
    db = tmp_path / "users.sqlite"
    con = sqlite3.connect(str(db))
    con.execute("CREATE TABLE users (email TEXT PRIMARY KEY, name TEXT NOT NULL, pw_hash TEXT, "
                "groups TEXT NOT NULL DEFAULT '[]', status TEXT NOT NULL DEFAULT 'pending', "
                "auth_source TEXT NOT NULL DEFAULT 'local', created_at INTEGER NOT NULL, approved_at INTEGER, "
                "approved_by TEXT, last_login_at INTEGER, failed_count INTEGER NOT NULL DEFAULT 0, "
                "locked_until INTEGER NOT NULL DEFAULT 0)")
    con.execute("INSERT INTO users(email, name, created_at) VALUES('old@corp.com', 'Old', 0)")
    con.commit(); con.close()
    st = UserStore(Settings(user_store_path=str(db)))
    assert st.get("old@corp.com")["hub_muted_apps"] == []
    assert st.set_hub_app_muted("old@corp.com", "b", True) == ["b"]
    assert st.set_hub_app_muted("old@corp.com", "a", True) == ["a", "b"]
    assert st.set_hub_app_muted("old@corp.com", "a", True) == ["a", "b"], "두 번 꺼도 한 번"
    assert st.set_hub_app_muted("old@corp.com", "b", False) == ["a"]
    assert st.get("old@corp.com")["hub_muted_apps"] == ["a"]
    assert st.set_hub_app_muted("nobody@corp.com", "a", True) is None
