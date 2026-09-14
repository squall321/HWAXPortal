# 절차 라우트 — 권한 **전수** 403 · 소유자 · 409 · 202 · SPA 폴백보다 위
#
# 권한 테스트가 전수인 이유 — 손으로 고른 몇 개만 보면 나중에 단 라우트가 조용히 열린다.
# access.yaml 의 features 선언만으로는 아무 라우트도 안 막힌다(기능 키는 타일·게이트웨이
# 백엔드에만 자동으로 묶인다).
import json

import pytest
import yaml
from fastapi.testclient import TestClient

from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.main import app
from app.procedures.store import ProceduresStore

PREFIX = "/procedures-api"


def _routes():
    """등록된 절차 라우트 전수 — (method, path)."""
    out = []
    for r in app.routes:
        path = getattr(r, "path", "")
        if not path.startswith(PREFIX):
            continue
        for m in sorted(getattr(r, "methods", set()) - {"HEAD", "OPTIONS"}):
            out.append((m, path))
    return sorted(out)


def _fill(path: str) -> str:
    return (path.replace("{run_id}", "r1").replace("{procedure_id}", "c1")
            .replace("{ix}", "0"))


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
        yield c
    app.dependency_overrides.pop(get_settings, None)


def _login(c, email):
    r = c.post("/auth/local/login", json={"email": email, "password": "pw123456"})
    assert r.status_code == 200, r.text
    return {"X-CSRF-Token": c.cookies.get("hwax_csrf")}


def _users(c, grants=None):
    """권한은 `approve(groups=)` 가 아니라 관리자가 거는 **개별 허가(grants)** 로 온다."""
    c.post("/auth/local/signup",
           json={"email": "boss@corp.com", "name": "Boss", "password": "pw123456"})
    c.post("/auth/local/signup",
           json={"email": "user@corp.com", "name": "User", "password": "pw123456"})
    h = _login(c, "boss@corp.com")
    assert c.post("/auth/local/users/user@corp.com/approve",
                  json={"groups": []}, headers=h).status_code == 200
    if grants:
        r = c.patch("/auth/access/users/user@corp.com", json={"grants": grants}, headers=h)
        assert r.status_code == 200, r.text


# ── 선언 ─────────────────────────────────────────────────────────────────
def test_기능이_access_yaml_에_선언돼_있다():
    from pathlib import Path

    d = yaml.safe_load((Path(__file__).resolve().parents[1] / "config" / "access.yaml")
                       .read_text(encoding="utf-8"))
    ids = [f["id"] for f in d["features"]]
    assert "procedures" in ids


def test_라우트가_실제로_붙어_있다():
    got = {p for _m, p in _routes()}
    assert f"{PREFIX}/runs" in got and f"{PREFIX}/procedures" in got
    assert f"{PREFIX}/health" in got
    assert len(got) >= 10


# ── 권한 전수 ────────────────────────────────────────────────────────────
def test_권한_없는_계정은_모든_라우트에서_403(client):
    """손으로 고른 몇 개가 아니라 **전수**다 — 나중에 단 라우트가 조용히 열리지 않게."""
    _users(client)
    h = _login(client, "user@corp.com")
    assert "feat:procedures" not in client.get("/auth/me").json()["entitlements"]

    leaked = []
    for method, path in _routes():
        if path.endswith("/health"):
            continue  # 무인증 프로브(모듈 상태만 낸다)
        r = client.request(method, _fill(path), json={}, headers=h)
        if r.status_code != 403:
            leaked.append((method, path, r.status_code))
    assert not leaked, f"권한 없이 403 이 아닌 라우트: {leaked}"


def test_로그인조차_안_했으면_401(client):
    _users(client)
    client.post("/auth/logout", headers=_login(client, "user@corp.com"))
    r = client.get(f"{PREFIX}/runs")
    assert r.status_code in (401, 403)


def test_health_는_무인증이고_모듈만_본다(client):
    r = client.get(f"{PREFIX}/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True and r.json()["journal_mode"].lower() == "wal"


# ── 권한 있는 계정 ───────────────────────────────────────────────────────
@pytest.fixture()
def user(client):
    _users(client, grants=["feat:procedures"])
    return client, _login(client, "user@corp.com")


def test_권한이_있으면_목록이_열린다(user):
    c, h = user
    assert "feat:procedures" in c.get("/auth/me").json()["entitlements"]
    assert c.get(f"{PREFIX}/runs").json() == {"runs": []}
    assert c.get(f"{PREFIX}/procedures").json() == {"procedures": []}


def test_빈_실행은_게이트웨이_없이_만들어진다(user):
    """절차 기능의 진입점 — 절차가 하나도 없어도 시작한다."""
    c, h = user
    r = c.post(f"{PREFIX}/runs", json={"mode": "live"}, headers=h)
    assert r.status_code == 202 and r.json()["empty"] is True
    rid = r.json()["run_id"]
    assert c.get(f"{PREFIX}/runs/{rid}").json()["state"] == "queued"


def test_남의_실행은_404(user, client):
    c, h = user
    rid = c.post(f"{PREFIX}/runs", json={}, headers=h).json()["run_id"]
    boss = _login(c, "boss@corp.com")  # portal-admin 이지만 실행은 공유하지 않는다
    assert c.get(f"{PREFIX}/runs/{rid}", headers=boss).status_code == 404


def test_저장_시점_거절이_라우트에서도_먹는다(user):
    """되돌리기 어려운 도구에 게이트가 없으면 **저장 자체가 안 된다**."""
    c, h = user
    bad = {"title": "t", "steps": [{"backend": "reportarchive", "tool": "publish_report"}]}
    r = c.post(f"{PREFIX}/procedures", json={"title": "t", "spec": bad}, headers=h)
    assert r.status_code == 422
    assert "gate: human" in r.text

    good = dict(bad)
    good["steps"] = [{**bad["steps"][0], "gate": "human"}]
    r2 = c.post(f"{PREFIX}/procedures", json={"title": "t", "spec": good}, headers=h)
    assert r2.status_code == 201 and r2.json()["version_no"] == 1


def test_dry_run_미지원_도구는_저장에서_막힌다(user):
    c, h = user
    spec = {"title": "t", "steps": [
        {"backend": "heax-step_forge", "tool": "list_parts", "args": {"dry_run": True}}]}
    r = c.post(f"{PREFIX}/procedures", json={"title": "t", "spec": spec}, headers=h)
    assert r.status_code == 422 and "dry_run" in r.text


def test_판본은_올라가고_옛_판본은_그대로다(user):
    c, h = user
    spec = {"title": "t", "steps": [{"backend": "b", "tool": "a_tool"}]}
    rid = c.post(f"{PREFIX}/procedures", json={"title": "t", "spec": spec},
                 headers=h).json()["id"]
    spec2 = {"title": "t", "steps": [{"backend": "b", "tool": "a_tool"},
                                     {"backend": "b", "tool": "c_tool"}]}
    r = c.post(f"{PREFIX}/procedures/{rid}/versions", json={"title": "t", "spec": spec2},
               headers=h)
    assert r.status_code == 201 and r.json()["version_no"] == 2
    assert len(c.get(f"{PREFIX}/procedures/{rid}").json()["spec"]["steps"]) == 2


def test_도는_단계가_있으면_409(user):
    """같은 단계 재실행 방지 — nginx 504 뒤 사람이 다시 누르면 쓰기가 두 번 나간다."""
    c, h = user
    rid = c.post(f"{PREFIX}/runs", json={}, headers=h).json()["run_id"]
    app.state.procedures_store.begin_step(rid, 0, backend="b", tool="t", args={})
    r = c.post(f"{PREFIX}/runs/{rid}/steps",
               json={"backend": "b", "tool": "t"}, headers=h)
    assert r.status_code == 409


def test_게이트_승인은_인자에_묶인다(user):
    """확인 뒤 인자가 바뀌면 무효다 — 사람이 본 것과 나가는 것이 같아야 한다."""
    c, h = user
    rid = c.post(f"{PREFIX}/runs", json={}, headers=h).json()["run_id"]
    st = app.state.procedures_store
    st.begin_step(rid, 0, backend="reportarchive", tool="publish_report", args={"id": 1})
    st.finish_step(rid, 0, ok=False, state="pending", stage="gate")
    real = st.list_steps(rid)[0]["args_sha256"]

    assert c.post(f"{PREFIX}/runs/{rid}/steps/0/ack",
                  json={"args_sha256": "deadbeef"}, headers=h).status_code == 409
    r = c.post(f"{PREFIX}/runs/{rid}/steps/0/ack", json={"args_sha256": real}, headers=h)
    assert r.status_code == 200 and r.json()["acked"] is True
    assert st.gate_ack(rid, 0)["ack_by"]


def test_취소는_소유자와_관리자만(user):
    c, h = user
    rid = c.post(f"{PREFIX}/runs", json={}, headers=h).json()["run_id"]
    assert c.post(f"{PREFIX}/runs/{rid}/cancel", headers=h).status_code == 200
    assert app.state.procedures_store.get_run(rid)["state"] == "cancelled"


def test_빈_실행은_재개하지_않는다(user):
    c, h = user
    rid = c.post(f"{PREFIX}/runs", json={}, headers=h).json()["run_id"]
    r = c.post(f"{PREFIX}/runs/{rid}/resume", headers=h)
    assert r.status_code == 409 and "빈 실행" in r.text


def test_stats_는_관리자만(user, client):
    c, h = user
    assert c.get(f"{PREFIX}/stats", headers=h).status_code == 403
    boss = _login(c, "boss@corp.com")
    r = c.get(f"{PREFIX}/stats", headers=boss)
    assert r.status_code == 200 and r.json()["procedures"] == 0


def test_실행에서_절차를_뽑는다(user):
    """"하고 나서 저장" 이 성립하는 자리 — 성공한 단계만 굳힌다."""
    c, h = user
    rid = c.post(f"{PREFIX}/runs", json={}, headers=h).json()["run_id"]
    st = app.state.procedures_store
    st.begin_step(rid, 0, backend="heax-step_forge", tool="list_parts",
                  args={"project_id": "p1"})
    st.finish_step(rid, 0, ok=True, result_text="{}")
    st.begin_step(rid, 1, backend="b", tool="failed_tool", args={})
    st.finish_step(rid, 1, ok=False, error="x")

    r = c.post(f"{PREFIX}/runs/{rid}/save-as-procedure", json={"title": "내 절차"}, headers=h)
    assert r.status_code == 201
    v = c.get(f"{PREFIX}/procedures/{r.json()['id']}").json()
    assert [s["tool"] for s in v["spec"]["steps"]] == ["list_parts"]  # 실패 단계는 안 굳는다
    assert v["derived_from_run"] == rid


def test_성공한_단계가_없으면_저장할_것이_없다(user):
    c, h = user
    rid = c.post(f"{PREFIX}/runs", json={}, headers=h).json()["run_id"]
    r = c.post(f"{PREFIX}/runs/{rid}/save-as-procedure", json={"title": "t"}, headers=h)
    assert r.status_code == 422


# ── SPA 폴백보다 위 ──────────────────────────────────────────────────────
def test_API_접두사가_SPA_경로와_겹치지_않는다():
    """`/procedures-api` 와 SPA `/procedures/*` 를 가른 이유 — 겹치면 새로고침이 JSON 을 받는다."""
    assert PREFIX == "/procedures-api"
    assert not any(getattr(r, "path", "").startswith("/procedures/") for r in app.routes)


def test_라우터가_SPA_폴백보다_먼저_등록됐다(client):
    """뒤에 두면 GET 이 index.html 로 먹힌다(200 text/html 로 조용히 실패)."""
    r = client.get(f"{PREFIX}/health")
    assert r.headers["content-type"].startswith("application/json")
    assert json.loads(r.text)["ok"] is True
