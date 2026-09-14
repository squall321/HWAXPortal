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
    return set(_re.findall(rf"{helper}\(request\)\.([a-zA-Z_][a-zA-Z0-9_]*)\(", _ROUTES_SRC))


def test_every_runner_method_the_routes_call_exists():
    missing = sorted(n for n in _called("_runner") if not hasattr(ProceduresRunner, n))
    assert not missing, f"routes.py 가 부르는데 실행기에 없다: {missing}"


def test_every_store_method_the_routes_call_exists():
    missing = sorted(n for n in _called("_store") if not hasattr(ProceduresStore, n))
    assert not missing, f"routes.py 가 부르는데 저장소에 없다: {missing}"


def test_the_guard_actually_finds_the_calls():
    """가드가 0건을 훑고 통과하면 아무것도 안 지킨다 — 실제로 찾는지 본다."""
    assert "catalog" in _called("_runner") and "step_once" in _called("_runner")
    assert "get_run" in _called("_store") and len(_called("_store")) >= 6


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
    c, h = user
    for bad in ("../../etc/passwd", "..", "a/b", "Laminate", "x" * 80):
        r = c.post(f"{PREFIX}/seeds/{bad}/import", headers=h)
        assert r.status_code in (400, 404, 422), f"{bad} 가 {r.status_code} 로 통과했다"


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
