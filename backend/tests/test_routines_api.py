# 분석 루틴 API(/routines-api, R1) — 권한 전수 403 · 주인과 공개 · 판 · 보관 · 검증 · YAML · 준비도 · 고를 수 있는 플랫폼(docs/analysis-routines)
"""저장소 · 원장은 임시 폴더, 게이트웨이는 MockTransport 다(tools/list · /tools-map 을 실제 꼴로 — 노출 이름은 원래 이름이거나
'<백엔드에서 하이픈 뺀 것>_<원래 이름>'). 공유 서비스를 부르지 않는다(절차 라우트 시험과 같은 까닭)."""
import copy
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.main import app
from app.procedures.routine_store import RoutineStore
from app.procedures.store import ProceduresStore

PREFIX = "/routines-api"
PW = "pw123456"
SPEC = {
    "title": "VOC → 심의",
    "purpose": "{{model}} 의 불량",
    "vars": [{"key": "model", "label": "모델"}],
    "steps": [
        {"id": "voc", "title": "VOC", "backends": ["signalforge"], "goal": "{{model}} VOC 를 본다",
         "tools": ["search_voc", "defect_profile"], "expect": {"keys": ["product_code"]}},
        {"id": "ra", "title": "기존 보고서", "kind": "cite", "backends": ["reportarchive"], "goal": "보고서를 찾는다"},
        {"id": "ft", "title": "FailureTrace", "backends": ["failuretrace"], "goal": "불량 기록"},
        {"id": "risk", "title": "리스크", "backends": ["heax-hwax_risk"], "goal": "리스크"},
        {"id": "delib", "title": "메커니즘", "kind": "deliberation", "goal": "메커니즘", "uses": ["voc"]},
    ],
}
# 이 사람의 tools/list(권한 필터의 정본) — signalforge 둘(하나는 별칭 꼴) · RA 하나 · 심의 · 게이트웨이 자체
TOOLS = [{"name": "search_voc", "description": "VOC 검색\n둘째 줄"}, {"name": "signalforge_defect_profile", "description": "불량 분포"},
         {"name": "submit_job", "description": "쓰기"}, {"name": "search_reports", "description": "RA"},
         {"name": "deliberate_start", "description": "심의"}, {"name": "search_tools", "description": "게이트웨이"}]
TMAP = {"map": {"search_voc": "signalforge", "signalforge_defect_profile": "signalforge", "submit_job": "signalforge",
                "search_reports": "reportarchive", "deliberate_start": "hwax-deliberation", "search_tools": "_gateway",
                "risk_list": "heax-hwax_risk"},
        "apps": [{"app": "signalforge", "label": "SignalForge VOC"}, {"app": "reportarchive", "label": "Report Archive"},
                 {"app": "hwax-deliberation", "label": "심의"}, {"app": "heax-hwax_risk", "label": "HWAX Risk"},
                 {"app": "_gateway", "label": "게이트웨이"}]}


def _gateway(tools=TOOLS):
    def handler(req: httpx.Request) -> httpx.Response:
        if req.method == "GET" and req.url.path.endswith("/tools-map"):
            return httpx.Response(200, json=TMAP)
        body = json.loads(req.content or b"{}") if req.content else {}
        if body.get("method") == "initialize":
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": {}}, headers={"mcp-session-id": "s"})
        if body.get("method") == "tools/list":
            payload = {"jsonrpc": "2.0", "id": 3, "result": {"tools": tools}}
            return httpx.Response(200, text=f"data: {json.dumps(payload)}\n\n", headers={"content-type": "text/event-stream"})
        return httpx.Response(200)
    return handler


@pytest.fixture()
def client(tmp_path):
    s = Settings(_env_file=None, user_store_path=str(tmp_path / "users.sqlite"), token_store_path=str(tmp_path / "tok.sqlite"),
                 procedures_store_path=str(tmp_path / "wb.sqlite"), jwt_keys_dir=str(tmp_path / "keys"),
                 upload_staging_dir=str(tmp_path / "stage"),
                 local_bootstrap_admins="boss@corp.com", gateway_shared_token="gw-test-secret")
    app.dependency_overrides[get_settings] = lambda: s
    from app.auth.routes.local import _rl
    from app.procedures.runner import ProceduresRunner
    _rl.clear()
    with TestClient(app) as c:
        app.state.user_store = UserStore(s)
        app.state.procedures_store = ProceduresStore(s)
        app.state.routine_store = RoutineStore(app.state.procedures_store)
        app.state.procedures_runner = ProceduresRunner(
            settings=s, store=app.state.procedures_store, mint_pat=lambda p, run, ix: "pat-test",
            client=httpx.AsyncClient(transport=httpx.MockTransport(_gateway()), timeout=5.0))
        for email in ("boss@corp.com", "peer@corp.com", "user@corp.com"):
            c.post("/auth/local/signup", json={"email": email, "name": email.split("@")[0], "password": PW})
        assert app.state.user_store.approve("user@corp.com", by="boss@corp.com", groups=[])
        assert app.state.user_store.approve("peer@corp.com", by="boss@corp.com", groups=["portal-admin"])   # 부트스트랩은 첫 가입자 하나뿐
        yield c, s
        app.state.procedures_runner = None
    app.dependency_overrides.pop(get_settings, None)


def _login(c, email) -> dict:
    c.cookies.clear()
    assert c.post("/auth/local/login", json={"email": email, "password": PW}).status_code == 200
    return {"X-CSRF-Token": c.cookies.get("hwax_csrf")}


def _routes():
    out = []
    for r in app.routes:
        path = getattr(r, "path", "")
        if path.startswith(PREFIX):
            out += [(m, path) for m in sorted(getattr(r, "methods", set()) - {"HEAD", "OPTIONS"})]
    return sorted(out)


def _create(c, h, spec=None) -> dict:
    r = c.post(f"{PREFIX}/routines", json={"spec": spec or SPEC}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def test_권한_없는_사람은_모든_루틴_라우트에서_403_이고_health_만_열려_있다(client):
    c, _ = client
    routes = _routes()
    assert len(routes) >= 10, routes
    h = _login(c, "user@corp.com")               # 승인된 일반 사용자 — feat:chat 뿐
    for m, path in routes:
        url = path.replace("{routine_id}", "r1")
        body = {"spec": SPEC} if m == "POST" and not path.endswith("/import") else {"yaml": "title: x"}
        r = c.request(m, url, headers=h, json=body if m in ("POST", "PUT", "PATCH") else None)
        if path == f"{PREFIX}/health":
            assert r.status_code == 200 and r.json() == {"ok": True, "contract": 1}, r.text
        else:
            assert r.status_code == 403, (m, path, r.status_code, r.text[:200])


def test_짜기_판_공개_보관은_주인만_고치고_없는_것과_못_보는_것은_같은_404(client):
    c, _ = client
    hb = _login(c, "boss@corp.com")
    made = _create(c, hb)
    assert made["version_no"] == 1
    rid = made["id"]
    got = c.get(f"{PREFIX}/routines/{rid}").json()
    assert got["mine"] and got["version"]["spec"]["visibility"] == "private" and got["version"]["spec"]["report"]["ra"]["upload"] == "auto"
    assert [v["version_no"] for v in got["versions"]] == [1]
    assert c.post(f"{PREFIX}/routines", json={"spec": SPEC}).status_code == 403, "CSRF 없이 쓰지 않는다"
    hp = _login(c, "peer@corp.com")
    assert c.get(f"{PREFIX}/routines/{rid}").status_code == 404, "비공개는 주인만"
    assert c.get(f"{PREFIX}/routines/nope").status_code == 404
    assert c.get(f"{PREFIX}/routines").json()["count"] == 0
    hb = _login(c, "boss@corp.com")
    r = c.post(f"{PREFIX}/routines/{rid}/versions", json={"spec": {**SPEC, "visibility": "all", "title": "VOC → 심의 v2"}}, headers=hb)
    assert r.status_code == 201 and r.json()["version_no"] == 2
    hp = _login(c, "peer@corp.com")
    rows = c.get(f"{PREFIX}/routines", params={"q": "v2"}).json()["routines"]
    assert [x["title"] for x in rows] == ["VOC → 심의 v2"] and rows[0]["mine"] is False
    assert [s["id"] for s in rows[0]["steps"]] == ["voc", "ra", "ft", "risk", "delib"] and rows[0]["vars"][0]["key"] == "model"
    assert c.get(f"{PREFIX}/routines/{rid}", params={"version": 1}).json()["version"]["spec"]["title"] == "VOC → 심의"
    r = c.post(f"{PREFIX}/routines/{rid}/versions", json={"spec": SPEC}, headers=hp)
    assert r.status_code == 404 and "주인만" in r.json()["detail"], "공개는 '남도 본다' 이지 '남도 고친다' 가 아니다"
    assert c.delete(f"{PREFIX}/routines/{rid}", headers=hp).status_code == 404
    text = c.get(f"{PREFIX}/routines/{rid}/export").text
    assert "title: VOC → 심의 v2" in text and "upload: auto" in text
    mine = c.post(f"{PREFIX}/import", json={"yaml": text}, headers=hp)
    assert mine.status_code == 201 and mine.json()["id"] != rid, "남의 루틴은 가져오기로 내 것을 만든다"
    hb = _login(c, "boss@corp.com")
    assert c.delete(f"{PREFIX}/routines/{rid}", headers=hb).json() == {"ok": True, "archived": True}
    assert c.get(f"{PREFIX}/routines/{rid}").status_code == 200, "보관해도 주인은 읽는다(실행 원장이 그 판을 가리킨다)"
    _login(c, "peer@corp.com")
    assert c.get(f"{PREFIX}/routines/{rid}").status_code == 404 and rid not in json.dumps(c.get(f"{PREFIX}/routines").json())


def test_틀린_스펙은_422_와_까닭이고_검증만_하는_길이_있다(client):
    c, _ = client
    h = _login(c, "boss@corp.com")
    bad = copy.deepcopy(SPEC)
    bad["steps"][0]["tools"] = ["publish_report"]
    r = c.post(f"{PREFIX}/routines", json={"spec": bad}, headers=h)
    assert r.status_code == 422 and "쓰기 도구" in r.json()["detail"], r.text
    r = c.post(f"{PREFIX}/validate", json={"spec": SPEC}, headers=h)
    assert r.status_code == 200 and r.json()["spec"]["report"]["sections"] == ["voc", "ra", "ft", "risk", "delib", "insight"]
    assert c.get(f"{PREFIX}/routines").json()["count"] == 0, "검증은 저장하지 않는다"
    r = c.post(f"{PREFIX}/import", json={"yaml": "title: [깨진"}, headers=h)
    assert r.status_code == 422 and "YAML" in r.json()["detail"]


def test_준비도는_단계마다_권한_토큰_박스를_말하고_막지_않는다(client):
    c, _ = client
    h = _login(c, "boss@corp.com")
    spec = copy.deepcopy(SPEC)
    spec["steps"][0]["tools"] = ["search_voc", "defect_profile", "nope_tool"]
    rid = _create(c, h, spec)["id"]
    r = c.get(f"{PREFIX}/routines/{rid}/readiness")
    assert r.status_code == 200, r.text
    by = {s["step"]: s for s in r.json()["steps"]}
    assert by["voc"]["state"] == "allowed" and by["voc"]["missing_tools"] == ["nope_tool"], "별칭 꼴(signalforge_defect_profile)도 원래 이름으로 센다"
    assert by["ra"]["state"] == "not_connected" and "/tokens?tab=connect" in by["ra"]["reason"], "RA 토큰이 없다 — 서비스 계정으로 떨어지지 않는다"
    assert by["ft"]["state"] == "unavailable" and "이 박스" in by["ft"]["reason"]
    assert by["risk"]["state"] == "denied", "이 박스에 있지만 내 도구 목록에 없다"
    assert by["delib"]["state"] == "allowed"


def test_고를_수_있는_플랫폼은_내_도구를_백엔드로_묶는다(client):
    c, _ = client
    _login(c, "boss@corp.com")
    d = c.get(f"{PREFIX}/platforms").json()
    sf = next(p for p in d["platforms"] if p["backend"] == "signalforge")
    assert sf["label"] == "SignalForge VOC"
    assert {t["name"]: t["write"] for t in sf["tools"]} == {"defect_profile": False, "search_voc": False, "submit_job": True}
    assert next(t for t in sf["tools"] if t["name"] == "search_voc")["description"] == "VOC 검색", "설명은 첫 줄만"
    assert {p["backend"] for p in d["platforms"]} == {"signalforge", "reportarchive"}, "심의 · 게이트웨이 자체는 플랫폼 목록 밖"
    assert d["deliberation"] is True
    assert d["not_permitted"] == [{"backend": "heax-hwax_risk", "label": "HWAX Risk"}]


def test_게이트웨이가_넘긴_PAT_로도_읽는다(client):
    c, _ = client
    h = _login(c, "boss@corp.com")
    rid = _create(c, h)["id"]
    tok = c.post("/auth/pat", json={"name": "claude"}, headers=h).json()["token"]
    c.cookies.clear()
    auth = {"Authorization": f"Bearer {tok}"}
    assert c.get(f"{PREFIX}/routines", headers=auth).json()["count"] == 1
    assert c.get(f"{PREFIX}/routines/{rid}", headers=auth).status_code == 200
    assert c.post(f"{PREFIX}/routines", json={"spec": SPEC}, headers=auth).status_code in (401, 403), "짜기는 화면(세션 + CSRF)만"


# ── 실행 원장(R2) — 계획 · 울타리 · 예산 · 단계 닫기(원장과 맞대기) · 근거 · 보고서 · RA 결과 ─────────────────────────────────
RUN_SPEC = copy.deepcopy(SPEC)
RUN_SPEC["steps"][0]["budget"] = {"calls": 2}


def _start(c, spec=None, inputs=None, h=None):
    rid = _create(c, h, spec or RUN_SPEC)["id"]
    r = c.post(f"{PREFIX}/runs", json={"routine_id": rid, "inputs": {"model": "S26"} if inputs is None else inputs}, headers=h)
    return rid, r


def _call(c, run_id, step="voc", backend="signalforge", tool="search_voc", result='{"product_code": "SM-S938", "n": 3}', ok=True, h=None):
    return c.post(f"{PREFIX}/runs/{run_id}/calls", json={"step": step, "backend": backend, "tool": tool, "args": {"q": "x"},
                                                        "ok": ok, "ms": 12, "result": result}, headers=h)


def test_실행은_계획을_찍고_막힌_단계는_그_상태로_닫혀_시작한다(client):
    c, _ = client
    h = _login(c, "boss@corp.com")
    _, r = _start(c, h=h)
    assert r.status_code == 201, r.text
    v = r.json()
    assert v["run"]["state"] == "running" and v["purpose"] == "S26 의 불량" and v["next_step"] == "voc"
    by = {s["id"]: s for s in v["steps"]}
    assert by["voc"]["allowed"] == {"signalforge": ["search_voc", "defect_profile"]}, "도구를 적었으면 그 차례로 · 내 목록에 있는 것만"
    assert by["voc"]["goal"] == "S26 VOC 를 본다" and by["voc"]["state"] == "pending"
    assert by["ra"]["state"] == "not_connected" and "/tokens?tab=connect" in by["ra"]["reason"]
    assert by["ft"]["state"] == "unavailable" and by["risk"]["state"] == "denied"
    assert by["delib"]["backends"] == ["hwax-deliberation"] and by["delib"]["allowed"] == {"hwax-deliberation": ["deliberate_start"]}
    assert v["report"] == {"title": "VOC → 심의", "sections": ["voc", "ra", "ft", "risk", "delib", "insight"], "upload": "auto"}
    assert c.get(f"{PREFIX}/runs").json()["count"] == 1
    _login(c, "peer@corp.com")
    assert c.get(f"{PREFIX}/runs/{v['run']['id']}").status_code == 404, "실행은 주인만"


def test_입력은_선언한_형으로_받고_모르는_키와_빠진_필수는_422(client):
    c, _ = client
    h = _login(c, "boss@corp.com")
    _, r = _start(c, inputs={}, h=h)
    assert r.status_code == 422 and "모델(model)" in r.json()["detail"]
    _, r = _start(c, inputs={"model": "S26", "modle": "x"}, h=h)
    assert r.status_code == 422 and "modle" in r.json()["detail"]


def test_멈춤으로_짠_단계가_막히면_실행이_failed_로_시작한다(client):
    c, _ = client
    h = _login(c, "boss@corp.com")
    spec = copy.deepcopy(RUN_SPEC)
    spec["steps"][2]["blocked"] = {"unavailable": "stop"}         # ft — 이 박스에 없음
    _, r = _start(c, spec=spec, h=h)
    v = r.json()
    assert v["run"]["state"] == "failed" and "단계 ft(FailureTrace)" in v["run"]["reason"] and "멈춤" in v["run"]["reason"]


def test_호출_원장은_울타리_예산_상태를_본다(client):
    c, _ = client
    h = _login(c, "boss@corp.com")
    _, r = _start(c, h=h)
    run_id = r.json()["run"]["id"]
    assert _call(c, run_id, backend="reportarchive", tool="search_reports", h=h).status_code == 409, "다른 단계의 백엔드"
    assert _call(c, run_id, tool="submit_job", h=h).status_code == 409, "쓰기 도구는 허용 목록에 없다"
    assert _call(c, run_id, step="ra", backend="reportarchive", tool="search_reports", h=h).status_code == 409, "닫힌 단계"
    assert [_call(c, run_id, h=h).json()["call_id"] for _ in range(2)] == ["voc.c1", "voc.c2"]
    r = _call(c, run_id, h=h)
    assert r.status_code == 409 and "호출 예산(2번)" in r.json()["detail"]
    v = c.get(f"{PREFIX}/runs/{run_id}").json()
    assert v["run"]["calls"] == 2 and next(s for s in v["steps"] if s["id"] == "voc")["state"] == "running"
    long = c.post(f"{PREFIX}/runs/{run_id}/calls", json={"step": "delib", "backend": "hwax-deliberation", "tool": "deliberate_start",
                                                         "args": {}, "ok": True, "result": "가" * 130_000}, headers=h).json()["call_id"]
    p2 = c.get(f"{PREFIX}/runs/{run_id}/calls/{long}", params={"page": 3}).json()
    assert (p2["pages"], p2["page"], len(p2["text"])) == (3, 3, 10_000)
    assert c.get(f"{PREFIX}/runs/{run_id}/calls/{long}", params={"page": 4}).status_code == 404


def test_단계_닫기는_원장과_맞대_상태를_고치고_다음_단계를_준다(client):
    c, _ = client
    h = _login(c, "boss@corp.com")
    _, r = _start(c, h=h)
    run_id = r.json()["run"]["id"]
    done = c.post(f"{PREFIX}/runs/{run_id}/steps/voc/done", json={"status": "ok", "summary": "요약"}, headers=h).json()
    assert done["state"] == "skipped" and "호출 없이" in done["flags"][0], "호출 없이 '했다' 는 건너뜀"
    _, r = _start(c, h=h)
    run_id = r.json()["run"]["id"]
    _call(c, run_id, h=h)
    body = {"status": "ok", "summary": "3건 [voc.c1]", "keys": {"product_code": "SM-S938", "nope": "x"},
            "findings": [{"text": "스웰링이 많다", "refs": ["voc.c1", "voc.c9"]}]}
    done = c.post(f"{PREFIX}/runs/{run_id}/steps/voc/done", json=body, headers=h).json()
    assert done["state"] == "ok" and done["next_step"]["id"] == "delib"
    assert any("계획에 없는 키" in f for f in done["flags"]) and any("voc.c9" in f for f in done["flags"])
    v = c.get(f"{PREFIX}/runs/{run_id}").json()
    voc = next(s for s in v["steps"] if s["id"] == "voc")
    assert voc["keys"] == {"product_code": "SM-S938"}
    body["keys"] = {"product_code": "SM-X000"}
    _, r = _start(c, h=h)
    run2 = r.json()["run"]["id"]
    _call(c, run2, h=h)
    done = c.post(f"{PREFIX}/runs/{run2}/steps/voc/done", json=body, headers=h).json()
    assert any("글자 그대로 없는 키" in f for f in done["flags"]), "지어낸 키 · 잘못 이은 제품은 넘기지 않는다"
    _, r = _start(c, h=h)
    run3 = r.json()["run"]["id"]
    _call(c, run3, ok=False, result="boom", h=h)
    assert c.post(f"{PREFIX}/runs/{run3}/steps/voc/done", json={"status": "ok"}, headers=h).json()["state"] == "failed"
    assert c.post(f"{PREFIX}/runs/{run3}/steps/voc/done", json={"status": "ok"}, headers=h).status_code == 409, "닫힌 단계"
    assert c.post(f"{PREFIX}/runs/{run3}/steps/delib/done", json={"status": "weird"}, headers=h).status_code == 422


def test_고를_것이_있으면_기다리고_사람이_고르면_이어진다(client):
    c, _ = client
    h = _login(c, "boss@corp.com")
    _, r = _start(c, h=h)
    run_id = r.json()["run"]["id"]
    _call(c, run_id, result='[{"key": "SM-S938", "label": "S26"}, {"key": "SM-S931", "label": "S26 FE"}]', h=h)
    amb = {"status": "ambiguous", "candidates": [{"label": "S26", "key": "SM-S938"}, {"label": "S26 FE", "key": "SM-S931"}]}
    done = c.post(f"{PREFIX}/runs/{run_id}/steps/voc/done", json=amb, headers=h).json()
    assert done["state"] == "ambiguous" and done["run_state"] == "waiting" and done["next_step"]["id"] == "voc"
    assert c.post(f"{PREFIX}/runs/{run_id}/steps/voc/pick", json={"key": "SM-X"}, headers=h).status_code == 422
    got = c.post(f"{PREFIX}/runs/{run_id}/steps/voc/pick", json={"key": "SM-S931"}, headers=h).json()
    assert got["state"] == "ok" and got["next_step"]["id"] == "delib"
    v = c.get(f"{PREFIX}/runs/{run_id}").json()
    assert v["run"]["state"] == "running" and next(s for s in v["steps"] if s["id"] == "voc")["keys"] == {"product_code": "SM-S931"}


def test_결과_없음을_멈춤으로_짠_단계는_실행을_멈춘다(client):
    c, _ = client
    h = _login(c, "boss@corp.com")
    spec = copy.deepcopy(RUN_SPEC)
    spec["steps"][0]["blocked"] = {"empty": "stop"}
    _, r = _start(c, spec=spec, h=h)
    run_id = r.json()["run"]["id"]
    _call(c, run_id, result="[]", h=h)
    done = c.post(f"{PREFIX}/runs/{run_id}/steps/voc/done", json={"status": "empty", "reason": "0건"}, headers=h).json()
    assert done["run_state"] == "failed"
    assert _call(c, run_id, h=h).status_code == 409


def test_심의_근거는_앞_단계의_성공한_원문이고_결론은_넘기지_않는다(client):
    c, _ = client
    h = _login(c, "boss@corp.com")
    _, r = _start(c, h=h)
    run_id = r.json()["run"]["id"]
    _call(c, run_id, result="가" * 20_000, h=h)
    _call(c, run_id, ok=False, result="boom", h=h)
    ev = c.get(f"{PREFIX}/runs/{run_id}/evidence", params={"step": "delib"}).json()
    assert [e["key"] for e in ev["evidence"]] == ["voc.c1"] and len(ev["evidence"][0]["result"]) == 15_000
    assert ev["evidence"][0]["source"] == "signalforge:search_voc" and ev["evidence"][0]["args"] == {"q": "x"}


def test_보고서는_단계가_다_닫힌_뒤_렌더하고_실행을_끝낸다(client):
    c, _ = client
    h = _login(c, "boss@corp.com")
    _, r = _start(c, h=h)
    run_id = r.json()["run"]["id"]
    assert c.post(f"{PREFIX}/runs/{run_id}/report", json={}, headers=h).status_code == 409, "열린 단계가 있다"
    _call(c, run_id, h=h)
    c.post(f"{PREFIX}/runs/{run_id}/steps/voc/done", json={"status": "ok", "summary": "VOC 요약 [voc.c1]",
                                                           "keys": {"product_code": "SM-S938"}}, headers=h)
    c.post(f"{PREFIX}/runs/{run_id}/calls", json={"step": "delib", "backend": "hwax-deliberation", "tool": "deliberate_start",
                                                  "args": {"question": "왜"}, "ok": True, "result": '{"job_id": "j1"}'}, headers=h)
    c.post(f"{PREFIX}/runs/{run_id}/steps/delib/done", json={"status": "ok", "summary": "메커니즘 [delib.c1]"}, headers=h)
    long = "문장이다. " * 600
    rep = c.post(f"{PREFIX}/runs/{run_id}/report", json={"sections": {"insight": f"스웰링 3건이다.\n\n근거가 있다 [voc.c1] [voc.c7]\n\n{long}",
                                                                      "elsewhere": "x"}}, headers=h)
    assert rep.status_code == 200, rep.text
    out = rep.json()
    md = out["report_md"]
    assert md.startswith("# VOC → 심의") and "## VOC" in md and "VOC 요약 [voc.c1]" in md and "## 근거 부록" in md
    assert "- [voc.c1] signalforge:search_voc" in md and "## FailureTrace" in md and "이 박스에 없음" in md
    assert "**커버리지**" in md and "FailureTrace(ft) — 이 박스에 없음" in md, "건너뛴 단계와 까닭을 숨기지 않는다"
    assert any("voc.c7" in w for w in out["warnings"]) and any("근거 없는 수치 문단 1개" in w for w in out["warnings"])
    assert any("elsewhere" in w for w in out["warnings"])
    ra = out["ra"]
    assert ra["upload"] == "auto" and ra["title"] == "VOC → 심의" and ra["tags"] == ["분석 루틴", "VOC → 심의"]
    assert set(ra["blocks"]) == {"background", "results", "recommendation", "minutes"}
    assert all(len(x) <= 1900 for v in ra["blocks"].values() for x in v) and len(ra["blocks"]["recommendation"]) >= 2, "RA 항목은 1,900자 이하로 나눈다"
    v = c.get(f"{PREFIX}/runs/{run_id}").json()
    assert v["run"]["state"] == "done" and v["run"]["report_ready"] is True
    assert c.post(f"{PREFIX}/runs/{run_id}/report", json={}, headers=h).status_code == 409
    assert c.post(f"{PREFIX}/runs/{run_id}/ra", json={"report_id": "58"}, headers=h).json() == {"ok": True}
    assert c.get(f"{PREFIX}/runs/{run_id}").json()["run"]["ra_report_id"] == "58"


def test_멈추면_더_부르지_않는다(client):
    c, _ = client
    h = _login(c, "boss@corp.com")
    _, r = _start(c, h=h)
    run_id = r.json()["run"]["id"]
    assert c.post(f"{PREFIX}/runs/{run_id}/cancel", headers=h).json() == {"ok": True, "state": "cancelled"}
    assert _call(c, run_id, h=h).status_code == 409
    assert c.post(f"{PREFIX}/runs/{run_id}/cancel", headers=h).status_code == 409


def test_RA_나눔은_에이전트_서버_엔진과_같은_결과다():
    """포털 렌더의 ra_split 과 엔진 deliberation._ra_split 을 같은 글로 돌려 맞댄다 — 엔진 원문 글에서 함수 · 상수를 떼어 돌린다(엔진을 import 하지
    않는다 — 포털 venv 에 엔진 의존성이 없다)."""
    import re
    from pathlib import Path

    from app.procedures.routines import RA_ITEM_MAX, ra_split
    src = (Path(__file__).resolve().parents[3] / "HWAXAgentServer" / "deliberation.py").read_text(encoding="utf-8")
    item = re.search(r'^_RA_ITEM_MAX = _env_int\("DELIB_RA_ITEM_MAX", (\d+)\)', src, re.M)
    assert item and int(item.group(1)) == RA_ITEM_MAX, "상한이 엔진과 다르다"
    split_re = re.search(r"^(_RA_SPLIT_RE = re\.compile\(.*\))$", src, re.M).group(1)
    fn = re.search(r"^def _ra_split\(s: str\) -> list\[str\]:\n(?:(?:    .*|)\n)+?(?=\n\S)", src, re.M).group(0)
    ns = {"re": re, "_RA_ITEM_MAX": RA_ITEM_MAX}
    exec(split_re + "\n" + fn, ns)
    for s in ("", "짧다", "가" * 5000, ("문장이다. " * 900) + "\n끝", "\n".join(["줄" * 700] * 9), "a.b " * 2000):
        assert ra_split(s) == ns["_ra_split"](s), s[:30]
