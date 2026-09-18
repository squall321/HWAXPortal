# 절차 라우트 — 권한 **전수** 403 · 소유자 · 409 · 202 · SPA 폴백보다 위
#
# 권한 테스트가 전수인 이유 — 손으로 고른 몇 개만 보면 나중에 단 라우트가 조용히 열린다.
# access.yaml 의 features 선언만으로는 아무 라우트도 안 막힌다(기능 키는 타일·게이트웨이
# 백엔드에만 자동으로 묶인다).
import json
from pathlib import Path

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


def _offline_runner(s):
    """도구 0개를 돌려주는 가짜 게이트웨이 위의 실행기.

    `tools/list` 가 빈 목록이면 저장 검증은 **"못 물어봤다"** 로 다루고 경고만 남긴다.
    실제 백엔드는 부르지 않는다 — 테스트가 공유 서비스에 세션을 쌓지 않는다.
    """
    import httpx

    from app.procedures.runner import ProceduresRunner

    def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content or b"{}") if req.content else {}
        if body.get("method") == "initialize":
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": {}},
                                  headers={"mcp-session-id": "offline"})
        if body.get("method") == "tools/list":
            payload = {"jsonrpc": "2.0", "id": 2, "result": {"tools": []}}
            return httpx.Response(200, text=f"data: {json.dumps(payload)}\n\n",
                                  headers={"content-type": "text/event-stream"})
        return httpx.Response(200)

    return ProceduresRunner(
        settings=s, store=app.state.procedures_store,
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=5.0),
        mint_pat=lambda p, run, ix: "pat-offline")


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
        # ⚠ **테스트는 공유 서비스를 치면 안 된다.** lifespan 이 진짜 실행기를 세우고,
        # 그 실행기는 이 박스에 떠 있는 게이트웨이(:9110)를 실제로 부른다. 그러면 —
        #   · 게이트웨이가 내려가면 테스트 결과가 달라지고
        #   · 결과가 **그 신원의 권한**에 좌우된다(실제로 R1 씨앗이 저장 거절됐다, W-52)
        #   · 남의 게이트웨이에 세션이 쌓인다
        # 그래서 **오프라인 실행기**를 세운다 — 도구 0개를 돌려주는 가짜 게이트웨이다.
        # 0개는 "못 물어봤다" 로 다뤄지므로(W-52) 저장은 경고만 남기고 통과한다.
        app.state.procedures_runner = _offline_runner(s)
        yield c
        app.state.procedures_runner = None
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
    body = r.json()
    assert body["ok"] is True and body["journal_mode"].lower() == "wal"
    # ⚠ **무인증 라우트다.** 저장소 경로·기동 예외 문구를 여기서 낼 이유가 없다 —
    # 내부 배치와 모듈 구조가 그대로 드러난다. 상세는 서버 로그에 있다.
    assert "path" not in body, body


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


def test_취소는_소유자와_관리자만(user, client):
    """⚠ 이름은 규칙 **둘**인데 몸통은 소유자만 봤다 — 조건을 통째로 지워도 통과했다.

    셋 다 본다. 소유자 ○ · 관리자 ○ · 그 밖의 정당한 사용자 ✗.
    """
    c, h = user
    st = app.state.procedures_store

    rid = c.post(f"{PREFIX}/runs", json={}, headers=h).json()["run_id"]
    assert c.post(f"{PREFIX}/runs/{rid}/cancel", headers=h).status_code == 200
    assert st.get_run(rid)["state"] == "cancelled"

    # 관리자는 남의 실행도 세운다 — 폭주를 세울 길이 재기동뿐이면 안 된다
    rid2 = c.post(f"{PREFIX}/runs", json={}, headers=h).json()["run_id"]
    hb = _login(c, "boss@corp.com")
    assert c.post(f"{PREFIX}/runs/{rid2}/cancel", headers=hb).status_code == 200
    assert st.get_run(rid2)["state"] == "cancelled"

    # 권한은 있지만 남인 사람은 못 세운다 — 있는지조차 알려 주지 않는다(404)
    # ⚠ 신원은 **쿠키**가 정한다 — 관리자 작업은 관리자로 로그인한 채로 해야 한다.
    c.post("/auth/local/signup",
           json={"email": "third@corp.com", "name": "T", "password": "pw123456"})
    hb = _login(c, "boss@corp.com")
    assert c.post("/auth/local/users/third@corp.com/approve",
                  json={"groups": []}, headers=hb).status_code == 200
    assert c.patch("/auth/access/users/third@corp.com",
                   json={"grants": ["feat:procedures"]}, headers=hb).status_code == 200
    h = _login(c, "user@corp.com")
    rid3 = c.post(f"{PREFIX}/runs", json={}, headers=h).json()["run_id"]
    h3 = _login(c, "third@corp.com")
    assert c.post(f"{PREFIX}/runs/{rid3}/cancel", headers=h3).status_code == 404
    assert st.get_run(rid3)["state"] != "cancelled"


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
    assert not any(getattr(r, "path", "").startswith("/procedures/") for r in app.routes)


def test_라우터가_SPA_폴백보다_먼저_등록됐다(client):
    """⚠ **이 환경에는 폴백이 아예 없다.** `serve_frontend` 는 import 시점에 읽히므로
    `dependency_overrides` 로 켤 수 없다. 그래서 '먼저 등록됐다' 를 여기서 증명할 수는
    없고, 그 사실을 먼저 확인해 검사가 무엇을 안 보는지 드러낸다. 진짜 검증은
    `test_spa_fallback.py` 의 별도 프로세스 프로브가 한다.
    """
    assert not any("{full_path" in getattr(r, "path", "") for r in app.routes), \
        "폴백이 붙어 있다 — 이 검사의 전제가 바뀌었으니 순서를 실제로 확인하라"


# ── 라우트가 부르는 이름이 실제로 있나 ──────────────────────────────────
#
# 2026-09-14 에 실제로 이것 때문에 화면이 죽었다. routes.py 가
# `_runner(request).catalog(...)` 를 부르는데 그 메서드가 **아예 없었다** — 셸에서
# `cd backend && python …` 의 cd 가 실패해 &&  가 끊겼고, 편집이 안 된 채로 커밋됐다.
# 기존 테스트가 못 잡은 이유는 그 라우트를 아무도 안 쳤고, 202 라우트는 실패가
# 백그라운드 로거로만 가기 때문이다. **호출하는 이름을 소스에서 뽑아 대조한다.**
import re as _re

from app.procedures.runner import ProceduresRunner
from app.procedures.store import ProceduresStore

_ROUTES_SRC = (Path(__file__).resolve().parents[1] / "app" / "procedures" /
               "routes.py").read_text(encoding="utf-8")


def _called(helper: str) -> set[str]:
    """`routes.py` 가 부르는 메서드 이름들.

    ⚠ **두 모양을 다 본다.** `_store(request).x()` 만 찾던 동안, 라우트가 흔히 쓰는
    `store = _store(request)` → `store.x()` 형이 통째로 빠져 있었다. 실측으로 12개를
    보고 5개를 놓쳤는데, 놓친 것이 하필 **가장 최근에 추가된 것들**이다
    (`find_by_seed`·`merge_inputs`·`cancel_run`·`create_run`·`finish_step`).
    이 가드가 존재하는 이유가 바로 그 재발 유형(W-30)이다.
    """
    var = helper.lstrip("_")
    return set(_re.findall(
        rf"(?:{helper}\(request\)|(?<![\w.]){var})\.([a-zA-Z_][a-zA-Z0-9_]*)\(",
        _ROUTES_SRC))


def test_every_runner_method_the_routes_call_exists():
    missing = sorted(n for n in _called("_runner") if not hasattr(ProceduresRunner, n))
    assert not missing, f"routes.py 가 부르는데 실행기에 없다: {missing}"


def test_every_store_method_the_routes_call_exists():
    missing = sorted(n for n in _called("_store") if not hasattr(ProceduresStore, n))
    assert not missing, f"routes.py 가 부르는데 저장소에 없다: {missing}"


def test_the_guard_actually_finds_the_calls():
    """가드가 0건을 훑고 통과하면 아무것도 안 지킨다 — 실제로 찾는지 본다.

    ⚠ 하한은 **실측에 맞춰 올려 둔다.** `>= 6` 이던 동안 가드는 12개를 보고 5개를
    놓치고 있었는데, 그 하한이 그걸 '충분하다' 고 통과시켰다 — 없는 확신을 준 셈이다.
    """
    assert "catalog" in _called("_runner") and "step_once" in _called("_runner")
    got = _called("_store")
    assert "get_run" in got and len(got) >= 15, sorted(got)
    # 지역변수 형이 실제로 잡히는지 — 이 이름들이 그 형으로만 불린다
    for n in ("merge_inputs", "find_by_seed", "create_run"):
        assert n in got, f"`store = _store(request)` 형을 놓쳤다: {n}"


# ── /tools 가 실제로 도는가 ─────────────────────────────────────────────
def test_tools_route_returns_the_catalog(user):
    """화면이 처음 부르는 라우트다. 게이트웨이는 MockTransport 로 세운다."""
    import httpx

    from app.config import Settings

    c, h = user

    async def handler(req: httpx.Request) -> httpx.Response:
        if req.method == "DELETE":
            return httpx.Response(200)
        body = json.loads(req.content) if req.content else {}
        if body.get("method") == "initialize":
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": {}},
                                  headers={"mcp-session-id": "s1"})
        if body.get("method") == "tools/list":
            payload = {"jsonrpc": "2.0", "id": 3, "result": {"tools": [
                {"name": "heaxstep_forge_bend_profile", "description": "굽힘 구조",
                 "inputSchema": {"properties": {"project_id": {"type": "string"}},
                                 "required": ["project_id"]}}]}}
            return httpx.Response(200, text=f"data: {json.dumps(payload)}\n\n",
                                  headers={"content-type": "text/event-stream"})
        return httpx.Response(200)

    s = Settings()
    app.state.procedures_runner = ProceduresRunner(
        settings=s, store=app.state.procedures_store,
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=5.0),
        mint_pat=lambda p, run, ix: "pat-test")
    try:
        r = c.get(f"{PREFIX}/tools", headers=h)
        assert r.status_code == 200, r.text
        got = r.json()
        assert got["count"] == 1
        t = got["tools"][0]
        assert t["name"] == "heaxstep_forge_bend_profile"
        assert t["inputSchema"]["required"] == ["project_id"]
        assert len(t["schema_fp"]) == 16, "스키마 지문이 실려야 드리프트를 잡는다"
    finally:
        app.state.procedures_runner = None


# ── 씨앗 절차 ────────────────────────────────────────────────────────────
def test_seeds_list_the_bundled_examples(user):
    """첫날 화면이 비어 있으면 무엇을 만들 수 있는지 모른다 — 씨앗이 그 자리다."""
    c, h = user
    got = c.get(f"{PREFIX}/seeds", headers=h).json()["seeds"]
    r1 = next(s for s in got if s["name"] == "laminate-bend-life")
    assert "broken" not in r1, f"씨앗이 깨져 있다: {r1}"
    assert r1["steps"] == 7 and "create_report_draft" in r1["gates"]
    assert "heax-step_forge" in r1["backends"]
    # 사람이 채울 값은 **왜 물어보는지**가 있어야 한다
    asked = [v for v in r1["vars"] if v["key"] != "project_id"]
    assert asked and all(v["why"] for v in asked)


def test_importing_a_seed_puts_it_in_my_procedures(user):
    c, h = user
    assert c.get(f"{PREFIX}/procedures", headers=h).json()["procedures"] == []
    r = c.post(f"{PREFIX}/seeds/laminate-bend-life/import", headers=h)
    assert r.status_code == 201, r.text
    assert r.json()["from_seed"] == "laminate-bend-life" and r.json()["version_no"] == 1

    rows = c.get(f"{PREFIX}/procedures", headers=h).json()["procedures"]
    assert len(rows) == 1 and "굴곡 수명" in rows[0]["title"]
    v = c.get(f"{PREFIX}/procedures/{rows[0]['id']}", headers=h).json()
    assert len(v["spec"]["steps"]) == 7
    assert v["spec"]["steps"][0]["tool"] == "bend_profile"


def test_imported_seed_is_a_normal_procedure(user):
    """들어온 뒤에는 특별하지 않다 — 고치면 새 판본이다."""
    c, h = user
    pid = c.post(f"{PREFIX}/seeds/laminate-bend-life/import", headers=h).json()["id"]
    v = c.get(f"{PREFIX}/procedures/{pid}", headers=h).json()
    spec = dict(v["spec"])
    spec["steps"] = spec["steps"][:2]
    r = c.post(f"{PREFIX}/procedures/{pid}/versions",
               json={"title": spec["title"], "spec": spec}, headers=h)
    assert r.status_code == 201 and r.json()["version_no"] == 2


def test_seed_name_cannot_escape_the_directory(user):
    """⚠ 이 검사는 한때 **가드를 통째로 지워도 통과**했다.

    `../../etc/passwd`·`..`·`a/b` 는 `/` 가 더 있어 `/seeds/{name}/import` 에 아예
    라우팅되지 않는다 — Starlette 가 핸들러 전에 404 를 낸다. 남은 둘은 가드가 없어도
    `p.is_file()` 에서 404 가 나므로 허용 목록 `(400, 404, 422)` 를 그대로 만족했다.
    그래서 **가드 자신의 신호**를 본다.
    """
    c, h = user
    # 라우팅조차 안 되는 모양 — 막히기는 하는데 **가드 덕분이 아니다**
    for bad in ("../../etc/passwd", "..", "a/b"):
        assert c.post(f"{PREFIX}/seeds/{bad}/import",
                      headers=h).status_code in (400, 404, 422), bad
    # 가드에 닿는 모양 — 여기서는 가드의 문구가 나와야 한다
    # (인코딩한 `%2F` 는 클라이언트가 먼저 풀어 역시 라우팅에서 걸린다 — 가드에 안 닿는다)
    for bad in ("Laminate", "x" * 80, "has space", "dot.name"):
        r = c.post(f"{PREFIX}/seeds/{bad}/import", headers=h)
        assert r.status_code == 400 and "씨앗 이름이 아닙니다" in r.text, \
            f"{bad} -> {r.status_code} {r.text[:80]}"

    # 가드 자체도 직접 친다 — 라우팅이 어떻게 바뀌든 이건 변하지 않는다
    from app.auth.errors import AuthError
    from app.procedures.routes import SEED_DIR, _seed_path

    for bad in ("../../etc/passwd", "..", "a/b", "/etc/passwd", "laminate\n", ""):
        with pytest.raises(AuthError) as e:
            _seed_path(bad)
        assert e.value.status_code == 400, bad
    assert _seed_path("laminate-bend-life").parent == SEED_DIR


def test_unknown_seed_is_404(user):
    c, h = user
    assert c.post(f"{PREFIX}/seeds/nope/import", headers=h).status_code == 404


def test_seed_import_goes_through_the_same_validation(user, tmp_path, monkeypatch):
    """가져오기가 저장 시점 검증의 우회로가 되면 안 된다."""
    from app.procedures import routes as R

    bad = tmp_path / "bad-seed.yaml"
    bad.write_text("title: 나쁜 씨앗\nsteps:\n  - backend: reportarchive\n"
                   "    tool: publish_report\n", encoding="utf-8")
    monkeypatch.setattr(R, "SEED_DIR", tmp_path)
    c, h = user
    r = c.post(f"{PREFIX}/seeds/bad-seed/import", headers=h)
    assert r.status_code == 422 and "gate: human" in r.text


# ── 화면에서 온 값의 형 — 실행을 만들기 전에 맞춘다 ─────────────────────────
def _json_var_procedure(c, h) -> str:
    """`json` 변수 하나와 `number` 변수 하나를 쓰는 최소 절차."""
    spec = {
        "title": "형 맞추기",
        "vars": [
            {"key": "laminate", "label": "적층 정의", "type": "json", "why": "형상에 없다"},
            {"key": "r_unfold", "label": "펼침 R", "type": "number", "why": "쓰임새가 정한다"},
            {"key": "memo", "label": "비고", "type": "string", "required": False},
        ],
        "steps": [{"backend": "heax-laminate_analyzer_mcp", "tool": "analyze_laminate",
                   "args": {"laminate": "{{laminate}}", "bend_radius": "{{r_unfold}}"}}],
    }
    r = c.post(f"{PREFIX}/procedures", json={"title": "형 맞추기", "spec": spec}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_화면에서_온_적층은_문자열이_아니라_객체로_들어간다(user):
    """**이것이 첫 실행을 깨뜨리던 자리다.**

    화면의 입력칸은 문자열밖에 못 보낸다. `Var.coerce` 는 있었지만 **운영 경로에서
    한 번도 안 불렸다** — 그래서 적층 정의가 문자열인 채 실행 범위로 들어갔고,
    `laminate` 인자에 객체가 아니라 문자열이 실려 도구가 거절했다. 사람은 자기가
    옳게 붙여 넣었는데 왜 틀렸는지 알 수 없다.
    """
    c, h = user
    pid = _json_var_procedure(c, h)
    r = c.post(f"{PREFIX}/runs", headers=h, json={
        "procedure_id": pid, "mode": "plan",
        "vars": {"laminate": '{"unit_system": "SI_mm", "laminae": [{"thickness": 0.3}]}',
                 "r_unfold": "1000"},
    })
    assert r.status_code == 202, r.text
    got = c.get(f"{PREFIX}/runs/{r.json()['run_id']}", headers=h).json()["inputs"]
    assert isinstance(got["laminate"], dict), f"문자열 그대로 들어갔다: {got['laminate']!r}"
    assert got["laminate"]["unit_system"] == "SI_mm"
    assert got["r_unfold"] == 1000.0, f"숫자가 문자열이다: {got['r_unfold']!r}"


def test_깨진_JSON_은_실행을_만들기_전에_막힌다(user):
    """실행을 만들고 나서 터지면 앞 단계가 이미 돌아 있다."""
    c, h = user
    pid = _json_var_procedure(c, h)
    before = len(c.get(f"{PREFIX}/runs", headers=h).json()["runs"])
    r = c.post(f"{PREFIX}/runs", headers=h, json={
        "procedure_id": pid, "mode": "plan",
        "vars": {"laminate": "{적층: 없음", "r_unfold": "1000"}})
    assert r.status_code == 422 and "JSON" in r.text
    after = len(c.get(f"{PREFIX}/runs", headers=h).json()["runs"])
    assert after == before, "거절했는데 실행이 남았다"


def test_필수_변수가_비면_시작조차_안_한다(user):
    """빠진 변수는 그것을 쓰는 **단계에 가서야** 터졌다 — 그전 단계는 이미 돌고 난 뒤다."""
    c, h = user
    pid = _json_var_procedure(c, h)
    r = c.post(f"{PREFIX}/runs", headers=h, json={
        "procedure_id": pid, "mode": "plan", "vars": {"laminate": "{}"}})
    assert r.status_code == 422
    assert "펼침 R" in r.text and "r_unfold" in r.text, "무엇을 채워야 하는지 안 알려 준다"


def test_안_채운_선택_변수는_빈_문자열로_안_들어간다(user):
    c, h = user
    pid = _json_var_procedure(c, h)
    r = c.post(f"{PREFIX}/runs", headers=h, json={
        "procedure_id": pid, "mode": "plan",
        "vars": {"laminate": "{}", "r_unfold": "6", "memo": ""}})
    assert r.status_code == 202
    got = c.get(f"{PREFIX}/runs/{r.json()['run_id']}", headers=h).json()["inputs"]
    assert "memo" not in got, "빈 칸이 값으로 들어갔다"


def test_빈_실행은_형_맞추기를_건너뛴다(user):
    """절차 없이 도구를 한 단계씩 돌리는 실행에는 선언된 변수가 없다."""
    c, h = user
    r = c.post(f"{PREFIX}/runs", json={"mode": "live"}, headers=h)
    assert r.status_code == 202 and r.json()["empty"] is True


def test_씨앗을_가져오면_붙여_넣을_예시까지_따라온다(user):
    """예시가 저장·조회 경로에서 떨어지면 화면의 "예시 넣기" 버튼이 안 뜬다."""
    c, h = user
    r = c.post(f"{PREFIX}/seeds/laminate-bend-life/import", headers=h)
    assert r.status_code == 201, r.text
    spec = c.get(f"{PREFIX}/procedures/{r.json()['id']}", headers=h).json()["spec"]
    lam = next(v for v in spec["vars"] if v["key"] == "laminate")
    assert lam["example"]["unit_system"] == "SI_mm"
    assert len(lam["example"]["laminae"]) == 4
    assert lam["required"] is True, "예시가 있다고 필수가 풀리면 안 된다"


# ── 이력은 절차에 묶이고, 그 값 그대로 다시 돌아간다 ─────────────────────────
def test_실행_이력이_어느_절차에서_나왔는지_안다(user):
    """`procedure_version_id` 하나만 들고 있으면 화면에서 절차로 되짚을 수 없다."""
    c, h = user
    pid = _json_var_procedure(c, h)
    rid = c.post(f"{PREFIX}/runs", headers=h, json={
        "procedure_id": pid, "mode": "plan",
        "vars": {"laminate": "{}", "r_unfold": "6"}}).json()["run_id"]

    row = next(r for r in c.get(f"{PREFIX}/runs", headers=h).json()["runs"] if r["id"] == rid)
    assert row["procedure_id"] == pid and row["version_no"] == 1
    detail = c.get(f"{PREFIX}/runs/{rid}", headers=h).json()
    assert detail["procedure_id"] == pid and detail["version_no"] == 1


def test_절차별_이력만_따로_본다(user):
    """한 절차로 돌린 것이 전체 목록에 섞이면 '이 절차를 몇 번 돌렸나' 를 못 본다."""
    c, h = user
    a, b = _json_var_procedure(c, h), _json_var_procedure(c, h)
    for pid in (a, a, b):
        c.post(f"{PREFIX}/runs", headers=h, json={
            "procedure_id": pid, "mode": "plan",
            "vars": {"laminate": "{}", "r_unfold": "6"}})
    c.post(f"{PREFIX}/runs", json={"mode": "plan"}, headers=h)   # 빈 실행도 하나

    only_a = c.get(f"{PREFIX}/runs?procedure_id={a}", headers=h).json()["runs"]
    assert len(only_a) == 2 and {r["procedure_id"] for r in only_a} == {a}
    assert len(c.get(f"{PREFIX}/runs", headers=h).json()["runs"]) == 4


def test_지난_실행을_그_값_그대로_다시_돌린다(user):
    """이력이 값을 들고 있는데 다시 돌릴 길이 없으면 사람이 칸을 손으로 옮겨 적는다."""
    c, h = user
    pid = _json_var_procedure(c, h)
    first = c.post(f"{PREFIX}/runs", headers=h, json={
        "procedure_id": pid, "mode": "plan",
        "vars": {"laminate": '{"unit_system": "SI_mm"}', "r_unfold": "1000", "memo": "1차"},
    }).json()["run_id"]

    r = c.post(f"{PREFIX}/runs/{first}/replay", json={"mode": "plan"}, headers=h)
    assert r.status_code == 202 and r.json()["from_run"] == first
    again = c.get(f"{PREFIX}/runs/{r.json()['run_id']}", headers=h).json()
    assert again["id"] != first, "같은 실행을 덮어쓰면 이력이 사라진다"
    assert again["origin"] == "replay"
    assert again["inputs"]["laminate"] == {"unit_system": "SI_mm"}
    assert again["inputs"]["r_unfold"] == 1000.0 and again["inputs"]["memo"] == "1차"
    assert again["procedure_id"] == pid, "다시 돌린 것도 같은 절차의 이력이다"

    hist = c.get(f"{PREFIX}/runs?procedure_id={pid}", headers=h).json()["runs"]
    assert {x["id"] for x in hist} == {first, again["id"]}, "둘 다 이력에 남아야 한다"


def test_다시_돌릴_때_지난_중간값은_안_딸려온다(user):
    """`inputs` 에는 앞 단계가 뽑은 save 값도 섞인다 — 그걸 그대로 물려주면
    이번 실행이 **옛 중간값을 쥔 채** 시작해 단계가 조용히 건너뛰어진다."""
    c, h = user
    pid = _json_var_procedure(c, h)
    rid = c.post(f"{PREFIX}/runs", headers=h, json={
        "procedure_id": pid, "mode": "plan",
        "vars": {"laminate": "{}", "r_unfold": "6"}}).json()["run_id"]
    # 실행 중 save 로 합쳐진 값을 흉내 낸다
    c.app.state.procedures_store.merge_inputs(rid, {"loads_bent": {"N": [1, 2, 3]}})
    assert "loads_bent" in c.get(f"{PREFIX}/runs/{rid}", headers=h).json()["inputs"]

    again_id = c.post(f"{PREFIX}/runs/{rid}/replay", json={"mode": "plan"},
                      headers=h).json()["run_id"]
    got = c.get(f"{PREFIX}/runs/{again_id}", headers=h).json()["inputs"]
    assert "loads_bent" not in got, f"옛 중간값이 딸려 왔다: {sorted(got)}"
    assert set(got) == {"laminate", "r_unfold"}


def test_다시_돌리기는_남의_실행을_못_건드린다(user):
    """실행은 공유하지 않는다 — 결과에 그 사람 시야의 데이터가 담긴다.

    ⚠ 만들기를 **먼저** 하고 로그인을 나중에 한다. 로그인이 세션을 갈아 끼우면
    앞서 받은 CSRF 헤더가 낡아 403 이 난다(실제로 이 순서로 한 번 걸렸다).
    """
    c, h = user
    pid = _json_var_procedure(c, h)
    rid = c.post(f"{PREFIX}/runs", headers=h, json={
        "procedure_id": pid, "mode": "plan",
        "vars": {"laminate": "{}", "r_unfold": "6"}}).json()["run_id"]

    boss = _login(c, "boss@corp.com")   # 관리자여도 남의 실행은 못 본다
    assert c.post(f"{PREFIX}/runs/{rid}/replay", json={"mode": "plan"},
                  headers=boss).status_code == 404


def test_빈_실행은_다시_돌릴_절차가_없다(user):
    c, h = user
    rid = c.post(f"{PREFIX}/runs", json={"mode": "plan"}, headers=h).json()["run_id"]
    r = c.post(f"{PREFIX}/runs/{rid}/replay", json={"mode": "plan"}, headers=h)
    assert r.status_code == 422 and "절차" in r.text


def test_같은_씨앗을_다시_가져오면_사본이_아니라_판본이_올라간다(user):
    """씨앗은 리포와 함께 자란다(예시가 늘고 경고가 붙는다). 가져올 때마다 사본이 생기면
    목록이 같은 이름으로 채워지고 어느 것이 최신인지 사람이 알 수 없다."""
    c, h = user
    a = c.post(f"{PREFIX}/seeds/laminate-bend-life/import", headers=h).json()
    assert a["version_no"] == 1 and a["updated"] is False

    b = c.post(f"{PREFIX}/seeds/laminate-bend-life/import", headers=h).json()
    assert b["id"] == a["id"], "사본이 생겼다"
    assert b["version_no"] == 2 and b["updated"] is True

    rows = c.get(f"{PREFIX}/procedures", headers=h).json()["procedures"]
    assert len(rows) == 1, f"목록에 {len(rows)}건 — 사본이 늘었다"


def test_옛_판본과_그_이력은_판본이_올라도_남는다(user):
    """판본을 올리는 것이 지우는 것이면 안 된다 — 지난 실행이 어느 절차였는지 잃는다."""
    c, h = user
    a = c.post(f"{PREFIX}/seeds/laminate-bend-life/import", headers=h).json()
    rid = c.post(f"{PREFIX}/runs", headers=h, json={
        "version_id": a["version_id"], "mode": "plan",
        "vars": {"project_id": "p", "part": "x", "r_unfold": "1000", "bend_axis": "x",
                 "width_mode": "free", "laminate": '{"unit_system": "SI_mm"}'},
    }).json()["run_id"]

    c.post(f"{PREFIX}/seeds/laminate-bend-life/import", headers=h)   # 판본 2
    hist = c.get(f"{PREFIX}/runs?procedure_id={a['id']}", headers=h).json()["runs"]
    assert [r["id"] for r in hist] == [rid] and hist[0]["version_no"] == 1


# ── 실행 → 절차 초안 (도출) ──────────────────────────────────────────────
def test_챗_실행을_절차_초안으로_편다(user):
    """**한 고리의 마지막 칸이다.** 챗에서 한 일이 원장에 남았으면 절차로 펴 본다."""
    from app.procedures import from_chat

    c, h = user
    store = c.app.state.procedures_store
    me = c.get("/auth/me", headers=h).json()
    rid = from_chat.record(
        store, owner_sub=me["subject"], conversation_id="conv-1",
        title="R1-예제 의 UBEND_1 굽힘 좀 봐줘",
        activity=[
            {"tool": "bend_profile", "call": "a", "ok": True,
             "detail_full": '{"project_id": "R1-예제", "part": "UBEND_1"}'},
            {"tool": "bend_profile", "call": "a", "ok": True,
             "result_full": '{"parts": [{"for_bending_analysis": {"bend_radius_mm": 6.0}}]}'},
            {"tool": "solve_prescribed_curvature", "call": "b", "ok": True,
             "detail_full": '{"bend_radius": 6.0, "width": "free"}'},
            {"tool": "solve_prescribed_curvature", "call": "b", "ok": True,
             "result_full": '{"status": "ok"}'},
        ])
    assert rid

    got = c.get(f"{PREFIX}/runs/{rid}/draft", headers=h)
    assert got.status_code == 200, got.text
    d = got.json()
    s1, s2 = d["spec"]["steps"]
    # ①이 읽은 값을 ③이 쓴 것을 **사람이 안 적어 줘도** 알아낸다
    assert list(s1["save"].values()) == ["parts[0].for_bending_analysis.bend_radius_mm"]
    assert s2["args"]["bend_radius"] == "{{%s}}" % list(s1["save"])[0]
    # 사람이 대화에서 준 값은 변수
    assert {v["label"] for v in d["spec"]["vars"]} >= {"project_id", "part"}
    # 모르는 값은 상수로 두고 물어본다
    assert any(r["arg"] == "width" for r in d["needs_human"])


def test_초안은_저장하지_않는다(user):
    """자동 저장 금지 — 펴 보기만 한다(PLAN §7)."""
    from app.procedures import from_chat

    c, h = user
    me = c.get("/auth/me", headers=h).json()
    rid = from_chat.record(c.app.state.procedures_store, owner_sub=me["subject"],
                           conversation_id="c", title="t",
                           activity=[{"tool": "t", "call": "a", "ok": True, "detail": "{}"},
                                     {"tool": "t", "call": "a", "ok": True, "result_preview": "{}"}])
    before = len(c.get(f"{PREFIX}/procedures", headers=h).json()["procedures"])
    c.get(f"{PREFIX}/runs/{rid}/draft", headers=h)
    assert len(c.get(f"{PREFIX}/procedures", headers=h).json()["procedures"]) == before


def test_초안은_남의_실행을_안_보여준다(user):
    from app.procedures import from_chat

    c, h = user
    me = c.get("/auth/me", headers=h).json()
    rid = from_chat.record(c.app.state.procedures_store, owner_sub=me["subject"],
                           conversation_id="c", title="t",
                           activity=[{"tool": "t", "call": "a", "ok": True, "detail": "{}"},
                                     {"tool": "t", "call": "a", "ok": True, "result_preview": "{}"}])
    boss = _login(c, "boss@corp.com")
    assert c.get(f"{PREFIX}/runs/{rid}/draft", headers=boss).status_code == 404


def test_절차를_도구_계약으로_낸다(user):
    """절차는 사실상 도구다 — 계약을 같은 모양으로 내면 부르는 쪽이 같아진다(PLAN §9)."""
    c, h = user
    got = c.post(f"{PREFIX}/seeds/laminate-bend-life/import", headers=h).json()
    r = c.get(f"{PREFIX}/procedures/{got['id']}/tool", headers=h)
    assert r.status_code == 200, r.text
    t = r.json()

    sc = t["inputSchema"]
    assert sc["type"] == "object" and sc["additionalProperties"] is False
    assert "laminate" in sc["properties"] and sc["properties"]["laminate"]["type"] == "object"
    # 허용값이 있는 변수는 고르는 칸으로 나간다 — 오타가 조용히 살면 안 된다
    assert sc["properties"]["bend_axis"]["enum"] == ["x", "y"]
    # 왜 물어보는지가 설명으로 실린다 — LLM 이 읽을 수 있어야 한다
    assert "9.6%" in sc["properties"]["width_mode"]["description"]
    assert set(sc["required"]) >= {"project_id", "part", "laminate"}

    # ⚠ 사람 확인에서 멈춘다는 사실이 **계약의 일부**다 — 모르면 "왜 안 끝나지" 가 된다
    assert t["human_gates"] == ["create_report_draft"]
    assert "사람 확인" in t["description"] and "bend_profile" in t["description"]


def test_없는_절차의_도구_계약은_404(user):
    c, h = user
    assert c.get(f"{PREFIX}/procedures/없는id/tool", headers=h).status_code == 404


# ── 룰이 여럿을 골랐을 때 사람이 고른다 (PLAN §10-1) ─────────────────────
def _gated_pick_run(c, h):
    """select:ask 로 멈춘 실행을 흉내 낸다."""
    store = c.app.state.procedures_store
    me = c.get("/auth/me", headers=h).json()["subject"]
    spec = {"title": "룰로 고르기",
            "vars": [{"key": "project_id", "label": "과제"}],
            "steps": [{"backend": "heax-step_forge", "tool": "find_parts",
                       "args": {"project_id": "{{project_id}}"},
                       "select": {"from": "parts", "save": "name", "as": "part"}}]}
    got = c.post(f"{PREFIX}/procedures", json={"title": "t", "spec": spec},
                 headers=h).json()
    rid = store.create_run(owner_sub=me, run_by=me, procedure_version_id=got["version_id"],
                           inputs={"project_id": "p"}, origin="replay", mode="live")
    store.begin_step(rid, 0, backend="heax-step_forge", tool="find_parts", args={}, mode="live")
    store.finish_step(rid, 0, ok=False, state="pending", stage="select:ask", error=None,
                      notes={"pick_into": "part",
                             "candidates": [{"i": 0, "label": "PANEL_1", "value": "PANEL_1"},
                                            {"i": 1, "label": "PANEL_2", "value": "PANEL_2"}]})
    store.set_run_state(rid, "gated", stage="step:0")
    return rid


def test_보여_준_후보_중에서_고른다(user):
    c, h = user
    rid = _gated_pick_run(c, h)
    r = c.post(f"{PREFIX}/runs/{rid}/steps/0/pick", json={"value": "PANEL_2"}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["picked"] == "PANEL_2"
    run = c.get(f"{PREFIX}/runs/{rid}", headers=h).json()
    assert run["inputs"]["part"] == "PANEL_2", "고른 것이 범위에 안 담겼다"


def test_후보_밖의_값은_못_넣는다(user):
    """⚠ 아무 값이나 받으면 룰을 우회해 엉뚱한 대상으로 절차가 돈다 — 그건 고르는 게
    아니라 박는 것이다."""
    c, h = user
    rid = _gated_pick_run(c, h)
    r = c.post(f"{PREFIX}/runs/{rid}/steps/0/pick", json={"value": "남의부품"}, headers=h)
    assert r.status_code == 422 and "후보" in r.text
    run = c.get(f"{PREFIX}/runs/{rid}", headers=h).json()
    assert "part" not in run["inputs"]


def test_고를_것이_없는_단계는_거절한다(user):
    c, h = user
    rid = c.post(f"{PREFIX}/runs", json={"mode": "live"}, headers=h).json()["run_id"]
    c.app.state.procedures_store.begin_step(rid, 0, backend="b", tool="t", args={}, mode="live")
    r = c.post(f"{PREFIX}/runs/{rid}/steps/0/pick", json={"value": "x"}, headers=h)
    assert r.status_code == 409


def test_고르기는_남의_실행을_못_건드린다(user):
    c, h = user
    rid = _gated_pick_run(c, h)
    boss = _login(c, "boss@corp.com")
    assert c.post(f"{PREFIX}/runs/{rid}/steps/0/pick", json={"value": "PANEL_1"},
                  headers=boss).status_code == 404


# ── 룰이 고른 전부를 돌린다 (PLAN §10-1 · S5) ────────────────────────────
def test_후보_전부를_펼쳐_배치로_돌린다(user):
    """"디스플레이 패널에 해당하는 것" 처럼 **여럿이 답인** 물음이 있다.
    하나만 고르면 나머지는 버려진다."""
    c, h = user
    rid = _gated_pick_run(c, h)
    r = c.post(f"{PREFIX}/runs/{rid}/steps/0/fan-out", json={"mode": "plan"}, headers=h)
    assert r.status_code == 202, r.text
    got = r.json()
    assert got["count"] == 2 and len(got["runs"]) == 2
    assert {x["value"] for x in got["runs"]} == {"PANEL_1", "PANEL_2"}

    # 비교표 — inputs 를 **그대로 열로** 편다
    tbl = c.get(f"{PREFIX}/batches/{got['batch_id']}", headers=h).json()
    assert tbl["count"] == 2
    assert "part" in tbl["columns"] and "project_id" in tbl["columns"]
    assert sorted(x["inputs"]["part"] for x in tbl["runs"]) == ["PANEL_1", "PANEL_2"]
    assert all(x["inputs"]["project_id"] == "p" for x in tbl["runs"]), "공통 변수가 안 물렸다"


def test_후보_밖으로는_못_펼친다(user):
    """⚠ 아무 값이나 받으면 룰을 우회한다 — 고르기(pick)와 같은 규율이다."""
    c, h = user
    rid = _gated_pick_run(c, h)
    r = c.post(f"{PREFIX}/runs/{rid}/steps/0/fan-out",
               json={"values": ["PANEL_1", "남의부품"]}, headers=h)
    assert r.status_code == 422 and "후보 밖" in r.text
    # ⚠ `runs[0]["id"] == rid` 로는 못 잡는다 — 목록이 `gated` 를 맨 앞으로 정렬하므로
    # 실행이 몇 개 새든 이 실행이 첫 줄이다. **개수**를 센다.
    runs = c.get(f"{PREFIX}/runs", headers=h).json()["runs"]
    assert [x["id"] for x in runs] == [rid], f"실행이 샜다: {[x['id'] for x in runs]}"


def test_일부만_골라_펼칠_수_있다(user):
    c, h = user
    rid = _gated_pick_run(c, h)
    got = c.post(f"{PREFIX}/runs/{rid}/steps/0/fan-out",
                 json={"values": ["PANEL_2"], "mode": "plan"}, headers=h).json()
    assert got["count"] == 1 and got["runs"][0]["value"] == "PANEL_2"


def test_기본은_계획_모드다(user):
    """N개를 live 로 던지는 것은 사람이 골라야 한다."""
    c, h = user
    rid = _gated_pick_run(c, h)
    got = c.post(f"{PREFIX}/runs/{rid}/steps/0/fan-out", json={}, headers=h).json()
    assert got["mode"] == "plan"
    run = c.get(f"{PREFIX}/runs/{got['runs'][0]['run_id']}", headers=h).json()
    assert run["mode"] == "plan" and run["origin"] == "batch"


def test_상한을_넘으면_룰을_좁히라고_말한다(user, monkeypatch):
    from app.procedures import routes as _r

    c, h = user
    monkeypatch.setattr(_r, "BATCH_MAX", 1)
    rid = _gated_pick_run(c, h)
    r = c.post(f"{PREFIX}/runs/{rid}/steps/0/fan-out", json={}, headers=h)
    assert r.status_code == 422 and "좁혀" in r.text


def test_고른_후보가_없는_단계는_못_펼친다(user):
    c, h = user
    rid = c.post(f"{PREFIX}/runs", json={"mode": "plan"}, headers=h).json()["run_id"]
    c.app.state.procedures_store.begin_step(rid, 0, backend="b", tool="t", args={}, mode="live")
    assert c.post(f"{PREFIX}/runs/{rid}/steps/0/fan-out", json={},
                  headers=h).status_code == 409


def test_배치는_남의_것을_안_보여준다(user):
    c, h = user
    rid = _gated_pick_run(c, h)
    bid = c.post(f"{PREFIX}/runs/{rid}/steps/0/fan-out", json={},
                 headers=h).json()["batch_id"]
    boss = _login(c, "boss@corp.com")
    assert c.get(f"{PREFIX}/batches/{bid}", headers=boss).json()["count"] == 0


def test_비교표가_왜_실패했는지_싣는다(user):
    """⚠ 상태만 보이면 "5건 중 2건 실패" 로 끝나고 사람이 실행을 하나씩 열어야 한다 —
    표의 값어치가 거기서 사라진다(PLAN S5)."""
    c, h = user
    store = c.app.state.procedures_store
    rid = _gated_pick_run(c, h)
    got = c.post(f"{PREFIX}/runs/{rid}/steps/0/fan-out", json={}, headers=h).json()
    a, b = [x["run_id"] for x in got["runs"]]

    store.begin_step(a, 1, backend="x", tool="analyze_laminate", args={}, mode="live")
    store.finish_step(a, 1, ok=False, error="E100 입력 스키마가 유효하지 않습니다")
    store.set_run_state(a, "failed", ended=True)
    store.begin_step(b, 1, backend="x", tool="estimate_fatigue_life", args={}, mode="live")
    store.finish_step(b, 1, ok=True, notes={"warnings": [{"code": "W120"}]})

    tbl = c.get(f"{PREFIX}/batches/{got['batch_id']}", headers=h).json()
    by = {r["id"]: r for r in tbl["runs"]}
    assert by[a]["failed_at"]["tool"] == "analyze_laminate"
    assert "E100" in by[a]["failed_at"]["error"]
    assert by[b]["failed_at"] is None
    # 결과는 정상인데 경고만이 유일한 신호인 자리 — 표에 보여야 한다
    assert by[b]["warnings"] == ["W120"]


# ── 절차 내보내기·가져오기 (dev → cae00 이관, PLAN S1) ───────────────────
def test_절차를_YAML_한_장으로_뽑는다(user):
    """두 박스는 망이 갈려 DB 를 못 옮긴다. 옮기는 것은 **판본의 본문**뿐이다."""
    c, h = user
    got = c.post(f"{PREFIX}/seeds/laminate-bend-life/import", headers=h).json()
    r = c.get(f"{PREFIX}/procedures/{got['id']}/export", headers=h)
    assert r.status_code == 200
    assert "attachment" in r.headers.get("content-disposition", "")

    text = r.text
    assert text.startswith("# 절차 내보내기"), text[:60]
    body = yaml.safe_load(text)
    assert body["title"] and len(body["steps"]) == 7
    # ⚠ 실행 기록·소유자·id 는 안 담긴다 — 그 사람 시야의 데이터이고 박스마다 다르다
    assert not ({"owner_sub", "id", "runs", "version_id"} & set(body))


def test_내보낸_것을_그대로_들인다(user):
    c, h = user
    a = c.post(f"{PREFIX}/seeds/laminate-bend-life/import", headers=h).json()
    text = c.get(f"{PREFIX}/procedures/{a['id']}/export", headers=h).text

    r = c.post(f"{PREFIX}/procedures/import",
               json={"yaml_text": text, "title": "cae00 로 옮긴 R1"}, headers=h)
    assert r.status_code == 201, r.text
    spec = c.get(f"{PREFIX}/procedures/{r.json()['id']}", headers=h).json()["spec"]
    assert spec["title"] == "cae00 로 옮긴 R1" and len(spec["steps"]) == 7
    # 변수의 뜻·예시가 함께 건너간다 — 그게 없으면 받은 쪽이 못 쓴다
    lam = next(v for v in spec["vars"] if v["key"] == "laminate")
    assert lam["example"]["unit_system"] == "SI_mm" and lam["why"]


def test_들이는_것도_같은_검증을_탄다(user):
    """⚠ 내보낸 것이라고 통과시키면 안 된다 — 게이트 없는 절차가 그 길로 들어온다."""
    c, h = user
    bad = yaml.safe_dump({"title": "나쁜 것",
                          "steps": [{"backend": "reportarchive", "tool": "publish_report"}]},
                         allow_unicode=True)
    r = c.post(f"{PREFIX}/procedures/import", json={"yaml_text": bad}, headers=h)
    assert r.status_code == 422 and "gate: human" in r.text


def test_YAML_이_아니면_그렇게_말한다(user):
    c, h = user
    r = c.post(f"{PREFIX}/procedures/import", json={"yaml_text": "{{{ 이건 YAML 이 아니다"},
               headers=h)
    assert r.status_code == 422 and "YAML" in r.text
    r2 = c.post(f"{PREFIX}/procedures/import", json={"yaml_text": "- 목록이다\n- 맵이 아니다"},
                headers=h)
    assert r2.status_code == 422 and "맵" in r2.text


# ── ReportArchive 사전검사 (PLAN S1) ─────────────────────────────────────
def _ra_procedure(c, h) -> str:
    spec = {"title": "보고서 쓰는 절차",
            "vars": [{"key": "t", "label": "제목"}],
            "steps": [{"backend": "reportarchive", "tool": "create_report_draft",
                       "gate": "human",
                       "args": {"title": "{{t}}", "template_id": "__import_blank__",
                                "template_version": 1, "blocks": {}}}]}
    r = c.post(f"{PREFIX}/procedures", json={"title": "t", "spec": spec}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_RA_연결이_없으면_시작_전에_말한다(user):
    """⚠ 연결이 없으면 게이트웨이가 **서비스 계정으로 내려앉아** 남의 함에 쓰거나 401 이
    난다 — 어느 쪽이든 그 단계에 가서야 안다."""
    c, h = user
    pid = _ra_procedure(c, h)
    r = c.post(f"{PREFIX}/runs", json={"procedure_id": pid, "mode": "plan",
                                       "vars": {"t": "보고서"}}, headers=h)
    assert r.status_code == 202, r.text
    w = " ".join(r.json().get("warnings") or [])
    assert "Report Archive 연결이 없습니다" in w and "토큰 페이지" in w, r.json()


def test_사전검사는_막지_않는다(user):
    """계획 모드로 무엇을 부를지만 보려는 경우가 있다 — 모르는 것과 틀린 것을 안 섞는다."""
    c, h = user
    pid = _ra_procedure(c, h)
    r = c.post(f"{PREFIX}/runs", json={"procedure_id": pid, "mode": "plan",
                                       "vars": {"t": "보고서"}}, headers=h)
    assert r.status_code == 202 and r.json()["state"] == "queued"


def test_워크스페이스를_안_골랐으면_그것도_말한다(user):
    """연결만 있고 워크스페이스가 없으면 보고서가 **개인함**에 쌓인다(실사고)."""
    c, h = user
    me = c.get("/auth/me", headers=h).json()
    c.app.state.user_store.set_connection(email=me["email"], service="reportarchive",
                                          token="tok", workspace="")
    pid = _ra_procedure(c, h)
    w = " ".join(c.post(f"{PREFIX}/runs", json={"procedure_id": pid, "mode": "plan",
                                                "vars": {"t": "x"}},
                        headers=h).json().get("warnings") or [])
    assert "워크스페이스를 안 골랐습니다" in w, w


def test_RA_단계가_없으면_아무_말도_안_한다(user):
    """경고를 남발하면 사람이 무시하게 된다."""
    c, h = user
    pid = _json_var_procedure(c, h)
    r = c.post(f"{PREFIX}/runs", json={"procedure_id": pid, "mode": "plan",
                                       "vars": {"laminate": "{}", "r_unfold": "6"}}, headers=h)
    assert "warnings" not in r.json()


# ── 결손을 장부 초안으로 (PLAN §9-6) ─────────────────────────────────────
def test_결손을_장부_파일_초안으로_만든다(user):
    """도출이 찾은 결손이 화면에만 떠 있으면 앱 팀에 안 간다."""
    from app.procedures import from_chat

    c, h = user
    me = c.get("/auth/me", headers=h).json()["subject"]
    rid = from_chat.record(c.app.state.procedures_store, owner_sub=me, conversation_id="c",
                           title="t",
                           activity=[{"tool": "t", "call": "a", "ok": True, "detail": "{}"},
                                     {"tool": "t", "call": "a", "ok": True, "result_preview": "{}"}])
    r = c.post(f"{PREFIX}/gaps/draft", headers=h, json={
        "run_id": rid,
        "gap": {"step": 1, "tool": "모르는도구", "kind": "backend_unknown",
                "why": "이 도구가 어느 앱 것인지 기록에 없다"},
        "owner_candidate": "heax-step_forge"})
    assert r.status_code == 200, r.text
    got = r.json()
    assert got["filename"].endswith(".yaml")
    d = yaml.safe_load(got["yaml_text"])
    assert d["status"] == "open" and d["confirmed_by"] is None, "자동으로 확정하면 안 된다"
    assert d["owner_candidate"] == "heax-step_forge"
    assert rid in d["evidence"][0], "근거가 안 붙었다"
    assert "§9-3 순서" in d["checked"][0], "검사 순서를 안 일깨운다"


def test_장부_초안은_파일을_쓰지_않는다(user, tmp_path):
    """⚠ 포털이 리포에 직접 쓰면 검토 없이 결손이 늘고, 누가 등재했는지가 git 이 아니라
    웹 세션에 남는다."""
    from pathlib import Path

    from app.procedures import from_chat

    c, h = user
    gaps = Path(__file__).resolve().parents[2] / "docs" / "procedures" / "gaps"
    before = sorted(p.name for p in gaps.glob("*.yaml"))
    me = c.get("/auth/me", headers=h).json()["subject"]
    rid = from_chat.record(c.app.state.procedures_store, owner_sub=me, conversation_id="c",
                           title="t",
                           activity=[{"tool": "t", "call": "a", "ok": True, "detail": "{}"},
                                     {"tool": "t", "call": "a", "ok": True, "result_preview": "{}"}])
    c.post(f"{PREFIX}/gaps/draft", headers=h,
           json={"run_id": rid, "gap": {"kind": "backend_unknown", "tool": "x"}})
    assert sorted(p.name for p in gaps.glob("*.yaml")) == before, "파일을 썼다"


def test_남의_실행으로는_결손을_못_만든다(user):
    from app.procedures import from_chat

    c, h = user
    me = c.get("/auth/me", headers=h).json()["subject"]
    rid = from_chat.record(c.app.state.procedures_store, owner_sub=me, conversation_id="c",
                           title="t",
                           activity=[{"tool": "t", "call": "a", "ok": True, "detail": "{}"},
                                     {"tool": "t", "call": "a", "ok": True, "result_preview": "{}"}])
    boss = _login(c, "boss@corp.com")
    assert c.post(f"{PREFIX}/gaps/draft", headers=boss,
                  json={"run_id": rid, "gap": {"kind": "x"}}).status_code == 404


# ── 재개 — 약속만 있고 확인이 없던 자리(2026-09-15 감사) ──────────────────
def _run_with_unknown_write(c, h, tool: str):
    """쓰기 단계가 `unknown` 으로 끝난 실행을 만든다 — 타임아웃·재기동이 남기는 모양이다."""
    spec = {"title": "t", "vars": [],
            "steps": [{"backend": "ra", "tool": tool, "gate": "human", "args": {"x": 1}}]}
    r = c.post(f"{PREFIX}/procedures", json={"title": "t", "spec": spec}, headers=h)
    assert r.status_code == 201, r.text
    st = c.app.state.procedures_store
    rid = st.create_run(owner_sub=c.get("/auth/me").json()["subject"],
                        procedure_version_id=r.json()["version_id"], mode="live")
    st.begin_step(rid, 0, backend="ra", tool=tool, args={"x": 1})
    st.finish_step(rid, 0, ok=False, state="unknown", stage="timeout")
    return rid, st


def test_실행_여부를_모르는_쓰기는_승인_없이_재개하지_않는다(user):
    """독스트링은 여태 '사람이 확인한 뒤에만 돈다' 고 했는데 **확인이 없었다.**
    타임아웃 뒤 재기동하면 `close_stale()` 이 진행 중 단계를 전부 unknown 으로 만든다 —
    그 상태로 재개를 한 번 누르면 중단된 쓰기가 전부 다시 나간다."""
    c, h = user
    rid, st = _run_with_unknown_write(c, h, "add_report_tags")   # MUST_GATE
    r = c.post(f"{PREFIX}/runs/{rid}/resume", headers=h)
    assert r.status_code == 409, r.text
    assert "실행 여부를 모르는 쓰기" in r.text

    # 사람이 확인하고 승인하면 재개한다 — 인자 지문에 묶인 1회용이다
    sha = st.get_run(rid)["steps"][0]["args_sha256"]
    st.ack_gate(rid, 0, by="u", args_sha256=sha)
    assert c.post(f"{PREFIX}/runs/{rid}/resume", headers=h).status_code == 200


def test_읽기_단계는_그대로_재개한다(user):
    """가드가 **너무 넓으면** 평범한 조회 재개까지 막는다 — 그 짝을 함께 고정한다."""
    c, h = user
    rid, _st = _run_with_unknown_write(c, h, "find_reports")
    assert c.post(f"{PREFIX}/runs/{rid}/resume", headers=h).status_code == 200


def test_펼치기는_같은_값을_두_번_안_만든다(user):
    """같은 값을 두 번 주면 **똑같은 실행이 둘** 생겼다 — 배치는 대상마다 하나다."""
    c, h = user
    rid = _gated_pick_run(c, h)
    before = len(c.get(f"{PREFIX}/runs", headers=h).json()["runs"])
    r = c.post(f"{PREFIX}/runs/{rid}/steps/0/fan-out",
               json={"values": ["PANEL_1", "PANEL_1"], "mode": "plan"}, headers=h)
    assert r.status_code == 202, r.text
    after = c.get(f"{PREFIX}/runs", headers=h).json()["runs"]
    assert len(after) - before == 1, f"{len(after) - before}개가 생겼다"


# ── 2차 감사(2026-09-15) — 고친 것이 남긴 자리들 ──────────────────────────
def test_펼친_자식이_앞_단계_값을_물려받는다(user):
    """자식은 **고른 단계 다음부터** 돈다. 선언 변수만 넘기면 앞 단계가 뽑아 둔 값이
    비어 첫 치환에서 `TemplateError` 로 죽는다 — 단계 0개짜리 실패 N건이 되어,
    비교표가 **이유 없이** 실패만 보인다(그 표가 존재하는 이유가 사라진다)."""
    c, h = user
    st = c.app.state.procedures_store
    me = c.get("/auth/me", headers=h).json()["subject"]
    spec = {"title": "t", "vars": [{"key": "rule", "label": "룰"}],
            "steps": [
                {"backend": "ra", "tool": "list_reports", "args": {},
                 "save": {"proj": "project"}},
                {"backend": "ra", "tool": "find_parts", "args": {"q": "{{rule}}"},
                 "select": {"from": "parts", "save": "name", "as": "part"}},
                {"backend": "ra", "tool": "part_info",
                 "args": {"project": "{{proj}}", "part": "{{part}}"}}]}
    got = c.post(f"{PREFIX}/procedures", json={"title": "t", "spec": spec},
                 headers=h).json()
    rid = st.create_run(owner_sub=me, run_by=me, procedure_version_id=got["version_id"],
                        inputs={"rule": "*", "proj": "P9"}, origin="replay", mode="live")
    st.begin_step(rid, 1, backend="ra", tool="find_parts", args={}, mode="live")
    st.finish_step(rid, 1, ok=False, state="pending", stage="select:ask", error=None,
                   notes={"pick_into": "part",
                          "candidates": [{"i": 0, "label": "A", "value": "A"},
                                         {"i": 1, "label": "B", "value": "B"}]})
    st.set_run_state(rid, "gated", stage="step:1")

    r = c.post(f"{PREFIX}/runs/{rid}/steps/1/fan-out", json={"mode": "plan"}, headers=h)
    assert r.status_code == 202, r.text
    for row in r.json()["runs"]:
        got_in = st.get_run(row["run_id"])["inputs"]
        assert got_in.get("proj") == "P9", f"앞 단계 산출을 안 물려줬다: {got_in}"
        assert got_in.get("part") == row["value"]


def test_단계_상한은_받기_전에_말한다(user, monkeypatch):
    """실행기 안에서만 보면 라우트는 202 를 주고 배경에서 `RunnerError` 가 나는데,
    그것이 **실행 전체의 failed** 로 옮겨져 잘 쌓아 온 기록이 붉게 마감된다.
    안내는 로그로만 나가 사람에게 절대 안 닿는다."""
    from app.procedures import routes as R

    c, h = user
    rid = c.post(f"{PREFIX}/runs", json={"mode": "live"}, headers=h).json()["run_id"]
    st = c.app.state.procedures_store
    for i in range(3):
        st.begin_step(rid, i, backend="b", tool="t", args={})
        st.finish_step(rid, i, ok=True, result_text="{}")
    monkeypatch.setattr(R, "_STEP_MAX", 3)

    r = c.post(f"{PREFIX}/runs/{rid}/steps",
               json={"backend": "b", "tool": "list_parts", "args": {}}, headers=h)
    assert r.status_code == 409 and "상한" in r.text, r.text
    assert st.get_run(rid)["state"] != "failed", "쌓아 온 기록이 붉게 마감됐다"


def test_모양이_안_맞는_절차는_422_다(user):
    """`ValidationError` 가 그대로 올라가 **500** 이 됐다. 도구 지도가 불통일 때 초안은
    `backend: ""` 를 내는데(가장 흔한 결손), 그걸 저장하면 "서버 오류" 가 뜨고 왜 안 되는지가
    화면에 없다. 거절이지 고장이 아니다."""
    c, h = user
    r = c.post(f"{PREFIX}/procedures", headers=h, json={"title": "t", "spec": {
        "title": "t", "vars": [],
        "steps": [{"backend": "", "tool": "list_parts", "args": {}}]}})
    assert r.status_code == 422, f"{r.status_code} {r.text[:120]}"
    assert "모양이 맞지 않습니다" in r.text and "backend" in r.text


def test_재개가_터지면_게이트에_매달리지_않는다(user):
    """재개 계열이 띄우는 `run()` 은 `sess.open()` 이 **성공한 뒤에야** `running` 을
    쓴다. 게이트웨이가 죽어 있으면 그 전에 터지고 실행은 `gated` 그대로 남아,
    화면은 "사람 확인 대기" 를 계속 보인다 — 사람은 이미 눌렀는데."""
    import asyncio as _a

    from app.procedures.runner import RunnerError

    c, h = user
    st = c.app.state.procedures_store
    me = c.get("/auth/me", headers=h).json()["subject"]
    spec = {"title": "t", "vars": [],
            "steps": [{"backend": "ra", "tool": "add_report_tags", "gate": "human",
                       "args": {"x": 1}}]}
    got = c.post(f"{PREFIX}/procedures", json={"title": "t", "spec": spec},
                 headers=h).json()
    rid = st.create_run(owner_sub=me, run_by=me, procedure_version_id=got["version_id"],
                        inputs={}, origin="replay", mode="live")
    st.begin_step(rid, 0, backend="ra", tool="add_report_tags", args={"x": 1}, mode="live")
    st.finish_step(rid, 0, ok=False, state="pending", stage="gate")
    st.set_run_state(rid, "gated", stage="step:0")

    async def _boom(**kw):
        raise RunnerError("게이트웨이 초기화 실패 (503)")

    c.app.state.procedures_runner.run = _boom
    sha = st.get_run(rid)["steps"][0]["args_sha256"]
    r = c.post(f"{PREFIX}/runs/{rid}/steps/0/ack", json={"args_sha256": sha}, headers=h)
    assert r.status_code == 200, r.text

    async def _settle():
        await _a.sleep(0.1)
    _a.run(_settle())
    state = st.get_run(rid)["state"]
    assert state == "failed", f"게이트에 매달려 있다: {state}"


def test_저장된_명세는_늘_모델_모양이다(user):
    """⚠ 받은 dict 를 그대로 저장하면 모델이 보장하는 칸이 없을 수 있다. `vars` 는
    `default_factory=list` 라 YAML 에 없어도 통과하는데, 그대로 저장되면 화면이
    `spec.vars.length` 를 읽다 **TypeError** 로 죽는다 — 이 리포에 ErrorBoundary 가
    하나도 없어 라우트가 아니라 **앱 전체가 흰 화면**이 된다(4차 감사)."""
    c, h = user
    bare = {"title": "vars 없는 절차",
            "steps": [{"backend": "b", "tool": "list_parts", "args": {}}]}
    r = c.post(f"{PREFIX}/procedures", json={"title": "t", "spec": bare}, headers=h)
    assert r.status_code == 201, r.text
    got = c.get(f"{PREFIX}/procedures/{r.json()['id']}", headers=h).json()["spec"]
    assert got["vars"] == [], got
    assert {"title", "vars", "steps"} <= set(got)
    # 들여오기 경로도 같다 — 거기가 YAML 을 받는 자리라 더 잘 닿는다
    import yaml as _y

    r2 = c.post(f"{PREFIX}/procedures/import",
                json={"yaml_text": _y.safe_dump(bare, allow_unicode=True)}, headers=h)
    assert r2.status_code == 201, r2.text
    got2 = c.get(f"{PREFIX}/procedures/{r2.json()['id']}", headers=h).json()["spec"]
    assert got2["vars"] == [], got2


# ── 게이트웨이가 거절·불통일 때 — 원인이 화면까지 오는가(2026-09-17 cae00 점검) ─────────────
def _runner_with(handler):
    import httpx

    from app.procedures.runner import ProceduresRunner

    return ProceduresRunner(
        settings=Settings(), store=app.state.procedures_store,
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=5.0),
        mint_pat=lambda p, run, ix: "pat-test")


def test_게이트웨이가_PAT_를_거절하면_502_에_이유가_실린다(user):
    """예전엔 500 평문 'Internal Server Error' 였다 — 챗은 서비스 계정으로 물러서서 멀쩡해 보이므로
    사람에게는 '챗은 되는데 절차만 깨졌다' 로만 보였다."""
    import httpx

    c, h = user
    app.state.procedures_runner = _runner_with(lambda req: httpx.Response(401, text="invalid token"))
    try:
        r = c.get(f"{PREFIX}/tools", headers=h)
        assert r.status_code == 502, r.text
        assert "401" in r.json()["detail"], r.json()
    finally:
        app.state.procedures_runner = None


def test_게이트웨이가_안_뜨면_502_에_연결_실패가_실린다(user):
    import httpx

    def down(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=req)

    c, h = user
    app.state.procedures_runner = _runner_with(down)
    try:
        r = c.get(f"{PREFIX}/tools", headers=h)
        assert r.status_code == 502 and "연결 실패" in r.json()["detail"], r.text
    finally:
        app.state.procedures_runner = None


# ── 여럿을 골라 한 단계에 넘긴다(select.multi) ────────────────────────────
def _gated_multi_run(c, h):
    """select:ask_many 로 멈춘 실행 — 태그 후보를 사람이 고르는 자리다."""
    store = c.app.state.procedures_store
    me = c.get("/auth/me", headers=h).json()["subject"]
    spec = {"title": "태그 적용",
            "vars": [{"key": "rid", "label": "보고서"}],
            "steps": [{"backend": "reportarchive", "tool": "suggest_report_tags",
                       "args": {"report_id": "{{rid}}"},
                       "select": {"from": "items", "save": "id", "as": "tag_ids",
                                  "label": "value", "multi": True}},
                      {"backend": "reportarchive", "tool": "add_report_tags", "gate": "human",
                       "args": {"report_id": "{{rid}}", "entity_ids": "{{tag_ids}}"}}]}
    got = c.post(f"{PREFIX}/procedures", json={"title": "t", "spec": spec}, headers=h).json()
    assert "version_id" in got, got
    rid = store.create_run(owner_sub=me, run_by=me, procedure_version_id=got["version_id"],
                           inputs={"rid": 4210}, origin="replay", mode="live")
    store.begin_step(rid, 0, backend="reportarchive", tool="suggest_report_tags", args={}, mode="live")
    store.finish_step(rid, 0, ok=False, state="pending", stage="select:ask_many", error=None,
                      notes={"pick_into": "tag_ids", "pick_multi": True,
                             "candidates": [{"i": 0, "label": "A22", "value": 101},
                                            {"i": 1, "label": "낙하", "value": 102},
                                            {"i": 2, "label": "PCB", "value": 103}]})
    store.set_run_state(rid, "gated", stage="step:0")
    return rid


def test_여럿을_골라_목록으로_넘긴다(user):
    c, h = user
    rid = _gated_multi_run(c, h)
    r = c.post(f"{PREFIX}/runs/{rid}/steps/0/pick", json={"values": [101, 103, 101]}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["picked"] == [101, 103], "같은 것을 두 번 고르면 도구가 같은 일을 두 번 한다"
    run = c.get(f"{PREFIX}/runs/{rid}", headers=h).json()
    assert run["inputs"]["tag_ids"] == [101, 103]


def test_하나짜리와_여럿짜리를_섞지_않는다(user):
    c, h = user
    rid = _gated_multi_run(c, h)
    r = c.post(f"{PREFIX}/runs/{rid}/steps/0/pick", json={"value": 101}, headers=h)
    assert r.status_code == 422 and "values" in r.json()["detail"], r.text
    rid2 = _gated_pick_run(c, h)
    r2 = c.post(f"{PREFIX}/runs/{rid2}/steps/0/pick", json={"values": ["PANEL_1"]}, headers=h)
    assert r2.status_code == 422 and "value" in r2.json()["detail"], r2.text


def test_여럿_고르기도_보여_준_후보_안에서만(user):
    c, h = user
    rid = _gated_multi_run(c, h)
    assert c.post(f"{PREFIX}/runs/{rid}/steps/0/pick", json={"values": [101, 999]},
                  headers=h).status_code == 422
    assert c.post(f"{PREFIX}/runs/{rid}/steps/0/pick", json={"values": []},
                  headers=h).status_code == 422


def test_여럿_고르기_단계는_펼치지_않는다(user):
    """펼치면 실행마다 값 하나가 스칼라로 들어가고, 같은 보고서에 태그를 한 개씩 N 번 붙인다."""
    c, h = user
    rid = _gated_multi_run(c, h)
    r = c.post(f"{PREFIX}/runs/{rid}/steps/0/fan-out", json={"mode": "plan"}, headers=h)
    assert r.status_code == 422 and "골라서 한 번에" in r.json()["detail"], r.text


# ── 즉석 단계가 `gate: human` 을 조용히 무시하던 것(W-100, 2026-09-18 재현) ─────────────
def test_즉석_단계는_사람_확인이_필요한_단계를_받지_않는다(user):
    """즉석 단계에는 확인 화면이 없다. 받으면 `gate: human` 이 **조용히 무시된 채** 바로 나갔다 —
    `trash_report` 가 게이트웨이까지 도달했다. 게이트웨이가 절차 호출에 파괴 도구 차단을
    면제하는 근거("포털이 사람 확인을 받았다")가 이 입구에서 거짓이 된다."""
    c, h = user
    rid = c.post(f"{PREFIX}/runs", json={}, headers=h).json()["run_id"]
    for body in ({"backend": "reportarchive", "tool": "trash_report", "gate": "human",
                  "args": {"report_id": 1}},
                 {"backend": "reportarchive", "tool": "trash_report", "args": {"report_id": 1}},
                 {"backend": "b", "tool": "harmless_read", "gate": "human"}):
        r = c.post(f"{PREFIX}/runs/{rid}/steps", json=body, headers=h)
        assert r.status_code == 422, (body, r.status_code, r.text)
        assert "즉석으로 돌릴 수 없습니다" in r.json()["detail"], r.json()
    assert app.state.procedures_store.list_steps(rid) == [], "거른 단계는 기록도 안 남긴다"
