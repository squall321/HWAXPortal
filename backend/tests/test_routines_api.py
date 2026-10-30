# 분석 루틴 API(/routines-api, R1) — 권한 전수 403 · 주인과 공개 · 판 · 보관 · 검증 · YAML · 준비도 · 고를 수 있는 플랫폼(docs/analysis-routines)
"""저장소 · 원장은 임시 폴더, 게이트웨이는 MockTransport 다(tools/list · /tools-map 을 실제 꼴로 — 노출 이름은 원래 이름이거나
'<백엔드에서 하이픈 뺀 것>_<원래 이름>'). 공유 서비스를 부르지 않는다(절차 라우트 시험과 같은 까닭)."""
import copy
import json
import re
import threading
import time
from datetime import datetime, timedelta, timezone

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
                 {"app": "_gateway", "label": "게이트웨이"}],
        # 단계 도구 판정 — 쓰기 분류(write, 이름 동사 · 표지 — R3-D6)와 읽기로 확인된 것(routine_read, 표지 · 읽기 목록 · 조회 낱말 — C-12).
        # 지금 게이트웨이의 판정 그대로다 — submit · start 는 쓰기 동사, 조회 낱말(search · profile · list)이 있는 백엔드 도구만 읽기
        "write": ["deliberate_start", "submit_job"],
        "routine_read": ["risk_list", "search_reports", "search_voc", "signalforge_defect_profile"]}
# 옛 게이트웨이 — routine_read 를 안 주는 판. write 만 주는 판은 {**TMAP_OLD, "write": [...]}, 둘 다 없으면 이름 꼴만(종전 판정 그대로)
TMAP_OLD = {k: v for k, v in TMAP.items() if k not in ("write", "routine_read")}


def _gateway(tools=TOOLS, tmap=TMAP):
    def handler(req: httpx.Request) -> httpx.Response:
        if req.method == "GET" and req.url.path.endswith("/tools-map"):
            return httpx.Response(200, json=tmap)
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


def _call(c, run_id, step="voc", backend="signalforge", tool="search_voc", result='{"product_code": "SM-S938", "n": 3}', ok=True, h=None,
          args=None):
    return c.post(f"{PREFIX}/runs/{run_id}/calls", json={"step": step, "backend": backend, "tool": tool,
                                                        "args": {"q": "x"} if args is None else args,
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
    assert by["delib"]["deliberation"] == {"job": "mechanism", "chair_template": None}, "실행자가 deliberate_start 에 넘길 일 · 의장 틀"
    assert by["voc"]["deliberation"] is None
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
    # R2 에서는 끝난 실행에 다시 내면 늘 409 였다 — RA 'ask' 의 다시 내기가 막혔다(R3-D12). 이제 저장본을 그대로 준다(다시 렌더하지 않는다)
    again = c.post(f"{PREFIX}/runs/{run_id}/report", json={}, headers=h)
    assert again.status_code == 200 and again.json() == out
    assert c.post(f"{PREFIX}/runs/{run_id}/ra", json={"report_id": "58"}, headers=h).json() == {"ok": True}
    assert c.get(f"{PREFIX}/runs/{run_id}").json()["run"]["ra_report_id"] == "58"


def test_멈추면_더_부르지_않는다(client):
    c, _ = client
    h = _login(c, "boss@corp.com")
    _, r = _start(c, h=h)
    run_id = r.json()["run"]["id"]
    assert c.post(f"{PREFIX}/runs/{run_id}/cancel", headers=h).json() == {"ok": True, "state": "cancelled", "delib_cancelled": [],
                                                                         "delib_cancel_errors": []}, "세운 심의가 없으면 접을 것도 없다"
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


# ── R3(docs/analysis-routines/R3-design.md 3.5) — 이어서 · 발견 · 상한 종류 · 시작 시각 · 보고서 읽기 · 끝난 실행의 저장본 · 묶인 판 ·
#    동시 원장 쓰기 · 시간 상한 뒤 심의 결과 · 쓰기 분류(게이트웨이 write) · 읽기 전용 PAT ─────────────────────────────────────────────────
DELIB_MORE = [{"name": "deliberate_status", "description": "진행"}, {"name": "deliberate_result", "description": "결과"}]


def _use_gateway(tools=TOOLS, tmap=TMAP):
    """이 시험만의 게이트웨이(tools/list · /tools-map)로 실행기를 바꿔 끼운다 — 픽스처가 끝에 걷는다."""
    from app.procedures.runner import ProceduresRunner
    old = app.state.procedures_runner
    app.state.procedures_runner = ProceduresRunner(
        settings=old.settings, store=old.store, mint_pat=old.mint_pat,
        client=httpx.AsyncClient(transport=httpx.MockTransport(_gateway(tools, tmap)), timeout=5.0))


def _kst(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M")


def _skip(c, run_id, step, h):
    return c.post(f"{PREFIX}/runs/{run_id}/steps/{step}/done", json={"status": "skipped"}, headers=h)


def test_이어서는_도는_실행과_끊긴_실행을_running_으로_하고_시간_상한이면_마감을_다시_잡는다(client):
    c, _ = client
    h = _login(c, "boss@corp.com")
    _, r = _start(c, h=h)
    run_id = r.json()["run"]["id"]
    store = app.state.routine_store
    # 시작 마감(지금 + 60분)과 다른 앞날로 박는다 — 시작과 같은 초에 다시 셈한 '지금 + 60분' 은 시작 마감과 같아, 이어서가 마감을 늘 다시
    # 잡는 고장이 이 단언을 그대로 지나갔다(반대 검토 #37)
    deadline = int(time.time()) + 500
    store.set_run(run_id, deadline=deadline)
    got = c.post(f"{PREFIX}/runs/{run_id}/resume", headers=h)
    assert got.status_code == 200 and got.json()["run"]["state"] == "running", got.text
    assert got.json()["run"]["deadline"] == deadline, "상한 전이면 마감을 건드리지 않는다"
    assert c.post(f"{PREFIX}/runs/{run_id}/resume").status_code == 403, "세션은 CSRF 가 있어야 쓴다"
    store.set_run(run_id, deadline=int(time.time()) - 5)
    late = c.get(f"{PREFIX}/runs/{run_id}").json()["run"]
    assert (late["limit_kind"], late["limit_reached"]) == ("time", "시간 60분")
    t0 = int(time.time())
    got = c.post(f"{PREFIX}/runs/{run_id}/resume", headers=h).json()["run"]
    assert t0 + 3600 <= got["deadline"] <= int(time.time()) + 3600, "마감은 지금 + limits.minutes"
    assert got["limit_kind"] is None and got["limit_reached"] is None
    store.set_run(run_id, state="interrupted", reason="에이전트 서버가 다시 떴다")
    got = c.post(f"{PREFIX}/runs/{run_id}/resume", headers=h).json()["run"]
    assert (got["state"], got["reason"], got["ended_at"]) == ("running", None, None), "끊긴 실행은 다시 돈다(끝 시각을 지운다)"
    _call(c, run_id, h=h)
    amb = {"status": "ambiguous", "candidates": [{"label": "S26", "key": "SM-S938"}, {"label": "S26 FE", "key": "SM-S931"}]}
    assert c.post(f"{PREFIX}/runs/{run_id}/steps/voc/done", json=amb, headers=h).json()["run_state"] == "waiting"
    r = c.post(f"{PREFIX}/runs/{run_id}/resume", headers=h)
    assert r.status_code == 409 and r.json()["detail"] == "고를 것이 있다 — 고른 뒤 이어서"
    assert c.post(f"{PREFIX}/runs/{run_id}/cancel", headers=h).status_code == 200
    r = c.post(f"{PREFIX}/runs/{run_id}/resume", headers=h)
    assert r.status_code == 409 and r.json()["detail"] == "실행이 cancelled 다"
    hp = _login(c, "peer@corp.com")
    assert c.post(f"{PREFIX}/runs/{run_id}/resume", headers=hp).status_code == 404, "이어서도 주인만"


def test_실행_보기는_단계_발견_상한_종류_시작_시각을_준다(client):
    c, _ = client
    h = _login(c, "boss@corp.com")
    spec = copy.deepcopy(RUN_SPEC)
    spec["purpose"] = "{{model}} 의 불량 — {{run.started}} 기준"
    spec["steps"][0]["goal"] = "{{model}} VOC 를 {{run.started}} 까지 본다"
    spec["report"] = {"title": "{{model}} 보고 {{run.started}}"}
    spec["limits"] = {"calls": 1}
    _, r = _start(c, spec=spec, h=h)
    v = r.json()
    run_id, when = v["run"]["id"], _kst(v["run"]["started_at"])
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", when)
    assert v["purpose"] == f"S26 의 불량 — {when} 기준" and v["report"]["title"] == f"S26 보고 {when}", "실행 시작 시각(KST)으로 푼다"
    assert next(s for s in v["steps"] if s["id"] == "voc")["goal"] == f"S26 VOC 를 {when} 까지 본다"
    assert all(s["findings"] == [] for s in v["steps"]) and v["run"]["limit_kind"] is None
    _call(c, run_id, h=h)
    body = {"status": "ok", "summary": "3건", "findings": [{"text": "스웰링이 많다", "refs": ["voc.c1", "voc.c9"]}]}
    assert c.post(f"{PREFIX}/runs/{run_id}/steps/voc/done", json=body, headers=h).json()["state"] == "ok"
    v = c.get(f"{PREFIX}/runs/{run_id}").json()
    assert next(s for s in v["steps"] if s["id"] == "voc")["findings"] == [{"text": "스웰링이 많다", "refs": ["voc.c1"]}], \
        "봉투의 발견 — 원장에 없는 인용은 뗀 채로"
    assert (v["run"]["limit_kind"], v["run"]["limit_reached"]) == ("calls", "호출 1번")
    app.state.routine_store.set_run(run_id, deadline=int(time.time()) - 5)
    v = c.get(f"{PREFIX}/runs/{run_id}").json()
    assert (v["run"]["limit_kind"], v["run"]["limit_reached"]) == ("calls", "호출 1번"), \
        "둘 다 닿으면 호출 상한이다 — 시간 상한 예외(심의 결과 읽기)가 호출 상한까지 넘기지 않게"
    assert _skip(c, run_id, "delib", h).json()["state"] == "skipped"
    rep = c.post(f"{PREFIX}/runs/{run_id}/report", json={"sections": {"insight": "스웰링 [voc.c1]"}}, headers=h).json()
    assert rep["report_md"].startswith(f"# S26 보고 {when}") and rep["ra"]["title"] == f"S26 보고 {when}", "보고서도 같은 시각으로"
    v = c.get(f"{PREFIX}/runs/{run_id}").json()
    assert v["run"]["state"] == "done" and v["run"]["limit_kind"] is None and v["run"]["limit_reached"] is None, "상한은 도는 실행에서만"


def test_보고서_읽기와_끝난_실행에_다시_내면_저장본이다(client):
    c, _ = client
    h = _login(c, "boss@corp.com")
    spec = copy.deepcopy(RUN_SPEC)
    spec["report"] = {"ra": {"upload": "ask"}}
    _, r = _start(c, spec=spec, h=h)
    run_id = r.json()["run"]["id"]
    assert c.get(f"{PREFIX}/runs/{run_id}/report").json() == {
        "run_id": run_id, "state": "running", "report_ready": False, "report_md": "", "ra_upload": "ask",
        "ra_report_id": None, "ra_error": None}, "아직 안 냈다"
    _call(c, run_id, h=h)
    c.post(f"{PREFIX}/runs/{run_id}/steps/voc/done", json={"status": "ok", "summary": "VOC 요약 [voc.c1]"}, headers=h)
    _skip(c, run_id, "delib", h)
    first = c.post(f"{PREFIX}/runs/{run_id}/report", json={"sections": {"insight": "스웰링이 많다 [voc.c1]"}}, headers=h)
    assert first.status_code == 200 and first.json()["ra"]["upload"] == "ask", first.text
    again = c.post(f"{PREFIX}/runs/{run_id}/report", json={"title": "다른 제목", "sections": {"insight": "전혀 다른 글"}}, headers=h)
    assert again.status_code == 200 and again.json() == first.json(), "RA 'ask' 다시 내기 — 다시 렌더하지 않고 저장본(새 절은 보지 않는다)"
    assert c.post(f"{PREFIX}/runs/{run_id}/ra", json={"report_id": "77"}, headers=h).json() == {"ok": True}
    assert c.get(f"{PREFIX}/runs/{run_id}/report").json() == {
        "run_id": run_id, "state": "done", "report_ready": True, "report_md": first.json()["report_md"], "ra_upload": "ask",
        "ra_report_id": "77", "ra_error": None}
    r = c.post(f"{PREFIX}/runs/{run_id}/resume", headers=h)
    assert r.status_code == 409 and r.json()["detail"] == "실행이 done 다"
    app.state.routine_store.set_run(run_id, report_json=None)          # R3 전에 낸 보고서 — 저장본이 없다
    r = c.post(f"{PREFIX}/runs/{run_id}/report", json={}, headers=h)
    assert r.status_code == 409 and "도는 실행에서만" in r.json()["detail"], "저장본이 없는 끝난 실행은 종전대로 409"
    _login(c, "peer@corp.com")
    assert c.get(f"{PREFIX}/runs/{run_id}/report").status_code == 404, "보고서도 주인만"


def test_주인이_도중에_보관해도_남의_실행_보고서는_묶인_판으로_난다(client):
    c, _ = client
    hb = _login(c, "boss@corp.com")
    rid = _create(c, hb, {**RUN_SPEC, "visibility": "all"})["id"]
    hp = _login(c, "peer@corp.com")
    r = c.post(f"{PREFIX}/runs", json={"routine_id": rid, "inputs": {"model": "S26"}}, headers=hp)
    assert r.status_code == 201, r.text
    run_id = r.json()["run"]["id"]
    for step in ("voc", "delib"):
        assert _skip(c, run_id, step, hp).status_code == 200
    hb = _login(c, "boss@corp.com")
    assert c.delete(f"{PREFIX}/routines/{rid}", headers=hb).json()["archived"] is True
    hp = _login(c, "peer@corp.com")
    assert c.get(f"{PREFIX}/routines/{rid}").status_code == 404, "보관한 남의 루틴은 이제 못 읽는다"
    rep = c.post(f"{PREFIX}/runs/{run_id}/report", json={}, headers=hp)
    assert rep.status_code == 200 and rep.json()["report_md"].startswith("# VOC → 심의"), rep.text


def test_동시_원장_쓰기는_예산을_넘기지_않고_call_id_가_겹치지_않는다(tmp_path):
    """add_call 의 세기와 넣기는 한 쓰기 트랜잭션이다(BEGIN IMMEDIATE). 스레드별 연결로 실제로 동시에 쓴다(포털 라우트도 스레드 풀에서 돈다) —
    단계 예산 4 · 실행 호출 상한 6 에 16 스레드."""
    from app.procedures.routine_store import CallRefused
    store = RoutineStore(ProceduresStore(Settings(_env_file=None, procedures_store_path=str(tmp_path / "wb.sqlite"))))
    run_id = store.create_run(owner_sub="u", routine={"id": "r1", "title": "t"}, version={"version_id": "v1", "version_no": 1},
                              inputs={}, plan={"steps": [], "limits": {"minutes": 60, "calls": 6}, "report": {}},
                              executor="mcp", conversation_id=None, deadline=int(time.time()) + 3600, state="running",
                              reason=None, stages=[("a", "pending", None), ("b", "pending", None)])
    gate = threading.Barrier(16)
    got, refused, errors = [], [], []

    def worker(step: str) -> None:
        gate.wait()
        try:
            got.append(store.add_call(run_id=run_id, step_id=step, backend="bk", tool="t", args={"i": 1}, ok=True, ms=1,
                                      result="가" * 50_000, truncated=False, step_budget=4, run_budget=6))
        except CallRefused as exc:
            refused.append(str(exc))
        except Exception as exc:  # noqa: BLE001 — 기본키 충돌 · 잠금 시간 초과도 단언으로 보인다
            errors.append(repr(exc))

    threads = [threading.Thread(target=worker, args=("ab"[i % 2],)) for i in range(16)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(30)
    assert errors == [], errors
    assert len(got) == 6 and len(set(got)) == 6 and len(refused) == 10, (got, refused)
    for step in "ab":
        ns = sorted(int(x.split(".c")[1]) for x in got if x.startswith(f"{step}."))
        assert len(ns) <= 4 and ns == list(range(1, len(ns) + 1)), (step, ns)
    assert {st["step_id"]: st["calls"] for st in store.stages(run_id)} == {s: sum(x.startswith(f"{s}.") for x in got) for s in "ab"}
    assert store.get_run(run_id=run_id, owner_sub="u")["calls"] == 6 and len(store.calls(run_id)) == 6


def test_시간_상한_뒤에도_심의_결과_읽기는_원장에_남고_호출_상한은_그대로다(client):
    c, _ = client
    h = _login(c, "boss@corp.com")
    _use_gateway(TOOLS + DELIB_MORE, {**TMAP, "map": {**TMAP["map"], "deliberate_status": "hwax-deliberation",
                                                      "deliberate_result": "hwax-deliberation"}})
    spec = copy.deepcopy(RUN_SPEC)
    spec["limits"] = {"calls": 3}
    _, r = _start(c, spec=spec, h=h)
    v = r.json()
    run_id = v["run"]["id"]
    assert next(s for s in v["steps"] if s["id"] == "delib")["allowed"] == {
        "hwax-deliberation": ["deliberate_start", "deliberate_status", "deliberate_result"]}

    def delib(tool):
        return c.post(f"{PREFIX}/runs/{run_id}/calls", json={"step": "delib", "backend": "hwax-deliberation", "tool": tool,
                                                             "args": {"job_id": "j1"}, "ok": True, "result": '{"job_id": "j1"}'},
                      headers=h)

    assert delib("deliberate_start").json()["call_id"] == "delib.c1"
    app.state.routine_store.set_run(run_id, deadline=int(time.time()) - 5)
    assert c.get(f"{PREFIX}/runs/{run_id}").json()["run"]["limit_kind"] == "time"
    r = _call(c, run_id, h=h)
    assert r.status_code == 409 and r.json()["detail"] == "실행 상한에 닿았다(시간 60분)", "다른 도구는 막힌다"
    assert delib("deliberate_status").status_code == 409, "진행 보기는 예외가 아니다(원장 없이 직접 부른다)"
    assert delib("deliberate_result").json()["call_id"] == "delib.c2", "이미 세운 심의의 결정문은 받는다"
    assert delib("deliberate_result").json()["call_id"] == "delib.c3"
    r = delib("deliberate_result")
    assert r.status_code == 409 and r.json()["detail"] == "실행 상한에 닿았다(호출 3번)", "호출 상한은 그대로다"


def test_쓰기_분류는_게이트웨이_write_가_정본이고_없으면_이름_꼴만(client):
    c, _ = client
    h = _login(c, "boss@corp.com")
    spec = copy.deepcopy(RUN_SPEC)
    spec["steps"] = [
        {"id": "voc", "title": "VOC", "backends": ["signalforge"], "goal": "VOC", "tools": ["search_voc", "defect_profile"]},
        {"id": "any", "title": "아무 도구", "backends": ["signalforge"], "goal": "읽기만"},
        {"id": "prof", "title": "분포", "backends": ["signalforge"], "goal": "분포", "tools": ["defect_profile"]},
    ]
    rid = _create(c, h, spec)["id"]
    # 읽기 목록(routine_read)을 안 주는 게이트웨이(옛 판)의 종전 판정 — 읽기 목록을 주는 판은 test_읽기_목록을_주는_게이트웨이면_…
    # 게이트웨이가 노출 이름으로 쓰기를 준다 — defect_profile 은 이름으로는 읽기지만 게이트웨이 분류(readOnlyHint 등)로 쓰기다
    _use_gateway(TOOLS, {**TMAP_OLD, "write": ["signalforge_defect_profile", "submit_job"]})
    plan = c.get(f"{PREFIX}/routines/{rid}/plan").json()
    assert plan["write_class"] == "gateway"
    by = {s["id"]: s for s in plan["steps"]}
    assert by["voc"]["allowed"] == {"signalforge": ["search_voc"]} and by["voc"]["dropped_write"] == ["signalforge:defect_profile"]
    assert by["voc"]["readiness"]["state"] == "allowed" and "signalforge:defect_profile" in by["voc"]["readiness"]["reason"], \
        "단계가 남아도 쓰기로 뺀 도구는 준비도 까닭에 적는다(R3-design 3.5 ⑦)"
    assert by["any"]["allowed"] == {"signalforge": ["search_voc"]} and by["any"]["dropped_write"] == [], "비운 단계 — 이름 꼴 + 게이트웨이 쓰기를 뺀다"
    assert by["prof"]["allowed"] == {"signalforge": []} and "signalforge:defect_profile" in by["prof"]["readiness"]["reason"]
    v = c.post(f"{PREFIX}/runs", json={"routine_id": rid, "inputs": {"model": "S26"}}, headers=h).json()
    assert v["write_class"] == "gateway"
    voc = next(s for s in v["steps"] if s["id"] == "voc")
    assert (voc["state"], voc["reason"]) == ("pending", ""), "남은 도구가 있으면 그대로 돈다 — 뺀 까닭은 준비도에만 남는다"
    prof = next(s for s in v["steps"] if s["id"] == "prof")
    assert prof["state"] == "unavailable" and "쓰기로 분류돼 뺐다" in prof["reason"], "쓰기를 빼서 빈 단계는 그 까닭으로 닫힌다"
    assert _call(c, v["run"]["id"], tool="defect_profile", h=h).status_code == 409, "뺀 쓰기 도구는 원장도 받지 않는다(울타리 밖)"
    sf = next(p for p in c.get(f"{PREFIX}/platforms").json()["platforms"] if p["backend"] == "signalforge")
    assert {t["name"]: t["write"] for t in sf["tools"]} == {"defect_profile": True, "search_voc": False, "submit_job": True}
    # 옛 게이트웨이 — write 칸이 없으면 이름 꼴만(도구를 적은 단계는 그대로)
    _use_gateway(TOOLS, TMAP_OLD)
    plan = c.get(f"{PREFIX}/routines/{rid}/plan").json()
    by = {s["id"]: s for s in plan["steps"]}
    assert plan["write_class"] == "name" and by["voc"]["allowed"] == {"signalforge": ["search_voc", "defect_profile"]}
    assert by["voc"]["dropped_write"] == [] and by["any"]["allowed"] == {"signalforge": ["defect_profile", "search_voc"]}
    # 플랫폼의 내 도구가 모두 쓰기면 비운 단계의 까닭이 그것이다('목록에 없다' 가 아니다)
    _use_gateway(TOOLS, {**TMAP_OLD, "write": ["search_voc", "signalforge_defect_profile", "submit_job"]})
    by = {s["id"]: s for s in c.get(f"{PREFIX}/routines/{rid}/plan").json()["steps"]}
    assert by["any"]["allowed"] == {"signalforge": []} and "모두 쓰기로 분류된다" in by["any"]["readiness"]["reason"]


def test_읽기_전용_판정은_게이트웨이와_같다():
    """게이트웨이 rest_proxy.is_read_only 와 같은 규칙 — scopes 에 read 가 있고 write 가 없을 때만. 챗 · 절차 PAT 의 ["chat"] · 칸 없는 옛 PAT 는 아니다."""
    import jwt

    from app.procedures.routine_routes import _read_only_pat

    def tok(**kw):
        return jwt.encode({"sub": "u", **kw}, "k" * 32, algorithm="HS256")
    assert _read_only_pat(tok(scopes=["read"])) is True and _read_only_pat(tok(scopes=["Read ", "upload"])) is True
    assert _read_only_pat(tok(scopes=["read", "write"])) is False
    assert _read_only_pat(tok(scopes=["chat"])) is False and _read_only_pat(tok()) is False


def test_읽기_전용_PAT_는_실행_원장에_못_쓰고_읽기는_된다(client):
    c, _ = client
    h = _login(c, "boss@corp.com")
    _, r = _start(c, h=h)
    run_id, rid = r.json()["run"]["id"], r.json()["run"]["routine_id"]
    ro = c.post("/auth/pat", json={"name": "ro", "scopes": ["read"]}, headers=h).json()["token"]
    rw = c.post("/auth/pat", json={"name": "rw"}, headers=h).json()["token"]
    c.cookies.clear()
    auth = {"Authorization": f"Bearer {ro}"}
    writes = [("/runs", {"routine_id": rid, "inputs": {"model": "S26"}}), (f"/runs/{run_id}/resume", None),
              (f"/runs/{run_id}/calls", {"step": "voc", "backend": "signalforge", "tool": "search_voc", "ok": True}),
              (f"/runs/{run_id}/steps/voc/done", {"status": "skipped"}), (f"/runs/{run_id}/steps/voc/pick", {"key": "SM-S938"}),
              (f"/runs/{run_id}/report", {}), (f"/runs/{run_id}/ra", {"report_id": "1"}), (f"/runs/{run_id}/cancel", None)]
    for path, body in writes:
        r = c.post(f"{PREFIX}{path}", json=body, headers=auth)
        assert r.status_code == 403 and r.json()["detail"] == "읽기 전용 토큰은 원장에 쓰지 못한다", (path, r.status_code, r.text[:200])
    for path in ("/runs", f"/runs/{run_id}", f"/runs/{run_id}/report", f"/runs/{run_id}/evidence?step=delib", "/routines"):
        assert c.get(f"{PREFIX}{path}", headers=auth).status_code == 200, path
    v = c.get(f"{PREFIX}/runs/{run_id}", headers=auth).json()
    assert (v["run"]["state"], v["run"]["calls"]) == ("running", 0) and c.get(f"{PREFIX}/runs", headers=auth).json()["count"] == 1, \
        "거절된 쓰기는 원장에 흔적이 없다"
    assert _call(c, run_id, h={"Authorization": f"Bearer {rw}"}).status_code == 201, "읽기 · 쓰기 PAT 는 그대로 쓴다(CSRF 없이)"


def test_옛_원장에도_report_json_칸을_붙인다(tmp_path):
    base = ProceduresStore(Settings(_env_file=None, procedures_store_path=str(tmp_path / "wb.sqlite")))
    with base._conn() as conn:          # R2 판의 표 — report_json 이 없다
        conn.execute("""CREATE TABLE routine_runs (
            id TEXT PRIMARY KEY, owner_sub TEXT NOT NULL, routine_id TEXT NOT NULL, version_id TEXT NOT NULL,
            version_no INTEGER NOT NULL, title TEXT NOT NULL, inputs_json TEXT NOT NULL, plan_json TEXT NOT NULL,
            executor TEXT NOT NULL, conversation_id TEXT, state TEXT NOT NULL, reason TEXT,
            calls INTEGER NOT NULL DEFAULT 0, started_at INTEGER NOT NULL, deadline INTEGER NOT NULL, ended_at INTEGER,
            report_md TEXT, ra_report_id TEXT, ra_error TEXT)""")
        conn.execute("INSERT INTO routine_runs (id, owner_sub, routine_id, version_id, version_no, title, inputs_json, plan_json,"
                     " executor, state, started_at, deadline, report_md) VALUES"
                     " ('old', 'u', 'r', 'v', 1, 't', '{}', '{}', 'mcp', 'done', 1, 2, '# 옛 보고서')")
    store = RoutineStore(base)
    RoutineStore(base)                  # 두 번 열어도 된다(멱등)
    assert {"report_json", "note"} <= {row["name"] for row in base._conn().execute("PRAGMA table_info(routine_runs)")}
    old = store.get_run(run_id="old", owner_sub="u")
    assert old["report"] is None and old["report_md"] == "# 옛 보고서", "옛 줄은 저장본이 없다(끝난 실행의 다시 내기는 409 로 남는다)"
    assert old["note"] is None, "덧붙인 말 칸(note)도 붙는다 — 옛 줄은 비어 있다(실행 보기는 빈 글)"


def test_루틴_목록의_변수는_필수_표시를_싣는다(client):
    """게이트웨이 prompts/list 는 루틴 변수를 인자로 싣고 필수를 표시한다(R3-design 3.4 ⑥) — 그 표시는 목록(GET /routines)에서 온다(루틴마다
    계획을 다시 읽지 않는다). 칸을 비우면 Var 기본값(필수)이다."""
    c, _ = client
    h = _login(c, "boss@corp.com")
    spec = copy.deepcopy(SPEC)
    spec["vars"] = [{"key": "model", "label": "모델"}, {"key": "since", "label": "시작일", "required": False}]
    _create(c, h, spec)
    rows = c.get(f"{PREFIX}/routines").json()["routines"]
    assert rows[0]["vars"] == [{"key": "model", "label": "모델", "required": True},
                               {"key": "since", "label": "시작일", "required": False}], rows[0]["vars"]


# ── R3 고침 — 보고서의 발견 겹침 · 준비도의 쓰기 분류 · 계획 행의 앱 라벨 · 끝난 실행 보고서의 RA 결과 ─────────────────────────────────────
def _with_findings(c, h) -> str:
    """voc 를 발견 둘(같은 호출 인용) · 키 하나로 닫고 delib 를 건너뛴 실행 — 단계가 다 닫혀 보고서를 낼 수 있다."""
    _, r = _start(c, h=h)
    run_id = r.json()["run"]["id"]
    _call(c, run_id, h=h)
    body = {"status": "ok", "summary": "VOC 요약 [voc.c1]", "keys": {"product_code": "SM-S938"},
            "findings": [{"text": "스웰링이 많다", "refs": ["voc.c1"]}, {"text": "발열은 드물다", "refs": ["voc.c1"]}]}
    assert c.post(f"{PREFIX}/runs/{run_id}/steps/voc/done", json=body, headers=h).json()["state"] == "ok"
    assert _skip(c, run_id, "delib", h).json()["state"] == "skipped"
    return run_id


def _squash(s: str) -> str:
    return " ".join(s.split())


def test_실행자가_쓴_절에_있는_발견은_보고서에_다시_붙이지_않는다(client):
    """에이전트 실행기의 단계 절은 요약 + '- 발견 [ref]' 줄이다 — 렌더가 봉투의 발견을 그 뒤에 또 붙여 report_md · RA results 에 발견이 두 번
    실렸다. 절에 이미 있는 발견(공백을 줄여 맞댄다)은 빼고 없는 것만 붙인다. 절이 없으면 지금처럼 요약 · 키 · 발견 전부."""
    c, _ = client
    h = _login(c, "boss@corp.com")
    run_id = _with_findings(c, h)
    sec = "VOC 요약 [voc.c1]\n\n- 스웰링이\n  많다 [voc.c1]"          # 발견 둘 가운데 하나만 · 줄바꿈과 겹친 띄어쓰기가 달라도 같은 발견이다
    out = c.post(f"{PREFIX}/runs/{run_id}/report", json={"sections": {"voc": sec, "insight": "인사이트 [voc.c1]"}}, headers=h).json()
    md, results = _squash(out["report_md"]), _squash("\n".join(out["ra"]["blocks"]["results"]))
    for text in ("스웰링이 많다", "발열은 드물다"):
        assert (md.count(text), results.count(text)) == (1, 1), (text, out["report_md"])
    assert "넘긴 키 — product_code=SM-S938" in out["report_md"], "키 줄은 절에 없으니 그대로 붙인다"
    run_id = _with_findings(c, h)
    out = c.post(f"{PREFIX}/runs/{run_id}/report", json={"sections": {"insight": "인사이트 [voc.c1]"}}, headers=h).json()
    assert ("## VOC\n\nVOC 요약 [voc.c1]\n\n넘긴 키 — product_code=SM-S938\n- 스웰링이 많다 [voc.c1]\n- 발열은 드물다 [voc.c1]\n\n"
            in out["report_md"]), out["report_md"]
    assert out["ra"]["blocks"]["results"][0] == \
        "VOC\nVOC 요약 [voc.c1]\n넘긴 키 — product_code=SM-S938\n- 스웰링이 많다 [voc.c1]\n- 발열은 드물다 [voc.c1]", "절이 없으면 지금 꼴 그대로"


def test_준비도도_계획과_같은_쓰기_분류로_단계를_말한다(client):
    """GET /readiness 가 계획(plan_steps)과 같은 쓰기 판정을 쓴다(R3-D6) — 고른 도구가 모두 쓰기거나(도구를 적은 단계) 읽기 도구가 하나도
    없으면(도구를 비운 단계) '이 박스에 없음' 과 계획과 같은 까닭, 일부만 뺐으면 allowed 그대로 뺀 것을 까닭에. 그전에는 준비도가 allowed 라
    고르는 화면에는 돈다고 보였는데 실행을 만들면 그 단계가 닫혀 시작했다."""
    c, _ = client
    h = _login(c, "boss@corp.com")
    spec = copy.deepcopy(RUN_SPEC)
    spec["steps"] = [
        {"id": "voc", "title": "VOC", "backends": ["signalforge"], "goal": "VOC", "tools": ["search_voc", "defect_profile", "nope_tool"]},
        {"id": "prof", "title": "분포", "backends": ["signalforge"], "goal": "분포", "tools": ["defect_profile", "nope_tool"]},
        {"id": "any", "title": "아무 도구", "backends": ["signalforge"], "goal": "읽기만"},
    ]
    rid = _create(c, h, spec)["id"]

    def both():
        ready = {s["step"]: s for s in c.get(f"{PREFIX}/routines/{rid}/readiness").json()["steps"]}
        plan = {s["id"]: s["readiness"] for s in c.get(f"{PREFIX}/routines/{rid}/plan").json()["steps"]}
        return ready, plan

    # 읽기 목록(routine_read)을 안 주는 게이트웨이(옛 판)의 종전 판정 — 읽기 목록을 주는 판은 test_읽기_목록을_주는_게이트웨이면_…
    _use_gateway(TOOLS, {**TMAP_OLD, "write": ["signalforge_defect_profile", "submit_job"]})
    ready, plan = both()
    assert ready["voc"]["state"] == "allowed" and ready["voc"]["reason"] == plan["voc"]["reason"], ready["voc"]
    assert "signalforge:defect_profile" in ready["voc"]["reason"] and "남은 도구로 돈다" in ready["voc"]["reason"], "일부만 뺐다 — 돈다"
    assert (ready["prof"]["state"], ready["prof"]["reason"]) == (
        "unavailable", "고른 도구가 쓰기로 분류돼 뺐다(단계 안 쓰기 금지 v1) — signalforge:defect_profile"), ready["prof"]
    assert plan["prof"]["reason"] == ready["prof"]["reason"], "계획과 같은 까닭"
    assert ready["voc"]["missing_tools"] == ["nope_tool"] and ready["prof"]["missing_tools"] == ["nope_tool"], "목록에 없는 도구도 그대로 보인다"
    assert (ready["any"]["state"], ready["any"]["reason"]) == ("allowed", ""), "도구를 비운 단계 — 읽기 도구(search_voc)가 남는다"
    v = c.post(f"{PREFIX}/runs", json={"routine_id": rid, "inputs": {"model": "S26"}}, headers=h).json()
    prof = next(s for s in v["steps"] if s["id"] == "prof")
    assert (prof["state"], prof["reason"]) == (ready["prof"]["state"], ready["prof"]["reason"]), "준비도가 말한 대로 실행이 시작한다"
    _use_gateway(TOOLS, {**TMAP_OLD, "write": ["search_voc", "signalforge_defect_profile", "submit_job"]})
    ready, plan = both()
    assert (ready["any"]["state"], ready["any"]["reason"]) == ("unavailable", plan["any"]["reason"]), ready["any"]
    assert "모두 쓰기로 분류된다" in ready["any"]["reason"], "플랫폼의 내 도구가 모두 쓰기면 도구를 비운 단계도 닫힌다"
    _use_gateway(TOOLS, TMAP_OLD)          # 옛 게이트웨이(write 칸 없음) — 이름 꼴만이라 defect_profile 은 읽기다
    ready, _ = both()
    assert {k: (r["state"], r["reason"]) for k, r in ready.items()} == {
        "voc": ("allowed", ""), "prof": ("allowed", ""), "any": ("allowed", "")}


def test_계획_행은_단계의_앱_라벨을_싣는다(client):
    """챗의 plan 프레임 · 화면이 단계마다 앱 라벨을 보인다(R3-design 3.2 — steps[{…, label}]). 계획 행마다 스펙의 Step.label(안 적었으면 빈 글)이
    있고, 실행 보기(routine_run_start · routine_get 이 돌려주는 것)의 단계도 같은 라벨이다."""
    c, _ = client
    h = _login(c, "boss@corp.com")
    spec = copy.deepcopy(RUN_SPEC)
    spec["steps"][0]["label"] = "SignalForge VOC"
    spec["steps"][4]["label"] = "전문가 심의"
    rid = _create(c, h, spec)["id"]
    want = {"voc": "SignalForge VOC", "ra": "", "ft": "", "risk": "", "delib": "전문가 심의"}
    plan = c.get(f"{PREFIX}/routines/{rid}/plan").json()
    assert {s["id"]: s.get("label", "<없음>") for s in plan["steps"]} == want, plan["steps"]
    v = c.post(f"{PREFIX}/runs", json={"routine_id": rid, "inputs": {"model": "S26"}}, headers=h).json()
    assert {s["id"]: s.get("label", "<없음>") for s in v["steps"]} == want
    assert {s["id"]: s.get("label", "<없음>") for s in c.get(f"{PREFIX}/runs/{v['run']['id']}").json()["steps"]} == want


def test_끝난_실행에_다시_낸_보고서는_지금의_RA_결과를_싣는다(client):
    """RA 'ask' 다시 올리기(R3-D12) — 저장본을 다시 받은 게이트웨이가 이미 올렸는지 알아야 RA 초안을 두 번 만들지 않는다. 저장본은 다시 렌더하지
    않지만 RA 결과(ra_report_id · ra_error)와 올리기 방식(ra_upload)은 실행 행의 지금 값이다(GET /report 와 같은 칸)."""
    c, _ = client
    h = _login(c, "boss@corp.com")
    spec = copy.deepcopy(RUN_SPEC)
    spec["report"] = {"ra": {"upload": "ask"}}
    _, r = _start(c, spec=spec, h=h)
    run_id = r.json()["run"]["id"]
    for step in ("voc", "delib"):
        assert _skip(c, run_id, step, h).status_code == 200

    def ra(d):
        return d.get("ra_upload"), d.get("ra_report_id", "<없음>"), d.get("ra_error", "<없음>")

    def rest(d):
        return {k: v for k, v in d.items() if k not in ("ra_report_id", "ra_error")}

    first = c.post(f"{PREFIX}/runs/{run_id}/report", json={}, headers=h).json()
    assert ra(first) == ("ask", None, None), "처음 렌더 — 아직 안 올렸다(같은 칸)"
    assert c.post(f"{PREFIX}/runs/{run_id}/ra", json={"error": "RA 토큰이 없다"}, headers=h).json() == {"ok": True}
    again = c.post(f"{PREFIX}/runs/{run_id}/report", json={}, headers=h).json()
    assert ra(again) == ("ask", None, "RA 토큰이 없다"), "올리기에 실패했다 — 다시 올려도 된다"
    assert c.post(f"{PREFIX}/runs/{run_id}/ra", json={"report_id": "77"}, headers=h).json() == {"ok": True}
    again = c.post(f"{PREFIX}/runs/{run_id}/report", json={"sections": {"insight": "전혀 다른 글"}}, headers=h).json()
    assert ra(again) == ("ask", "77", None), "이미 올렸다 — 게이트웨이가 다시 올리지 않는다"
    assert rest(again) == rest(first), "저장본은 그대로다(다시 렌더하지 않는다)"
    assert ra(c.get(f"{PREFIX}/runs/{run_id}/report").json()) == ra(again), "GET /report 와 같은 칸 · 같은 값"


# ── 반대 검토 고침(context-notes C-12) — 읽기로 확인된 것만 · 심의 결정문 읽기의 예산 · 덧붙인 말 · 키의 근거 · 고르기는 기다릴 때만 ·
#    원장 쓰기 트랜잭션의 다시 보기 ──────────────────────────────────────────────────────────────────────────────────────────
def test_읽기_목록을_주는_게이트웨이면_읽기로_확인된_도구만_단계에_묶는다(client):
    """게이트웨이 /tools-map 의 routine_read(읽기로 확인된 것 — 표지 · 읽기 목록 · 조회 낱말)가 오면 계획 · 준비도 · 고르는 화면이 그것만 단계에
    묶는다(write_class gateway_read). 이름 동사 규칙(write)은 표지를 안 단 쓰기 · 잡 시작을 '쓰기 아님' 으로 넘겼다 — risk_job_action(되돌릴 수
    없는 취소) · single_drop_simulation(Slurm 잡 제출) · docforge_convert. 실제 이름 그대로 쓴다. 모르는 이름은 읽기가 아니고, 읽기 목록에
    있어도 이름 꼴(is_write_tool)이 쓰기면 뺀다. 적은 도구에서 뺀 것은 dropped_write 와 준비도 까닭('읽기로 확인되지 않았다')에 남는다."""
    c, _ = client
    h = _login(c, "boss@corp.com")
    risk = ["risk_job_action", "risk_open_target", "risk_capture_snapshot", "risk_repersist_panel", "risk_next_step", "risk_get_report"]
    sim = ["single_drop_simulation", "fullangle_drop_simulation", "job_postprocess", "list_recent_jobs"]
    owners = {**dict.fromkeys(risk, "heax-hwax_risk"), **dict.fromkeys(sim, "smart-twin-mcp"), "docforge_convert": "heax-doc_forge",
              "ingest_status": "signalforge"}
    tools = TOOLS + [{"name": n, "description": "실제 이름"} for n in owners]
    # 지금 게이트웨이의 판정 그대로 — write(이름 동사)는 이 쓰기들을 하나도 못 잡는다. routine_read 는 조회 낱말이 있는 것만 싣는다
    # (ingest_status 는 status 낱말이라 읽기로 오지만 포털 이름 꼴 ingest_ 가 쓰기다)
    tmap = {**TMAP, "map": {**TMAP["map"], **owners},
            "apps": TMAP["apps"] + [{"app": "smart-twin-mcp", "label": "SmartTwin"}, {"app": "heax-doc_forge", "label": "DocForge"}],
            "routine_read": sorted(TMAP["routine_read"] + ["risk_get_report", "list_recent_jobs", "ingest_status"])}
    _use_gateway(tools, tmap)
    spec = copy.deepcopy(RUN_SPEC)
    spec["steps"] = [
        {"id": "risk_any", "title": "리스크", "backends": ["heax-hwax_risk"], "goal": "리스크를 읽는다"},
        {"id": "risk_named", "title": "리스크 둘", "backends": ["heax-hwax_risk"], "goal": "읽는다",
         "tools": ["risk_job_action", "risk_get_report"]},
        {"id": "sim_any", "title": "해석", "backends": ["smart-twin-mcp"], "goal": "지난 잡을 본다"},
        {"id": "sim_named", "title": "낙하", "backends": ["smart-twin-mcp"], "goal": "낙하", "tools": ["single_drop_simulation"]},
        {"id": "doc", "title": "변환", "backends": ["heax-doc_forge"], "goal": "변환"},
        {"id": "voc", "title": "VOC", "backends": ["signalforge"], "goal": "VOC"},
    ]
    rid = _create(c, h, spec)["id"]
    plan = c.get(f"{PREFIX}/routines/{rid}/plan").json()
    assert plan["write_class"] == "gateway_read"
    by = {s["id"]: s for s in plan["steps"]}
    assert by["risk_any"]["allowed"] == {"heax-hwax_risk": ["risk_get_report"]}, "모르는 이름(risk_job_action · risk_next_step …)은 읽기가 아니다"
    assert (by["risk_named"]["allowed"], by["risk_named"]["dropped_write"]) == (
        {"heax-hwax_risk": ["risk_get_report"]}, ["heax-hwax_risk:risk_job_action"]), "적은 도구도 읽기로 확인된 것만 — 뺀 것은 남긴다"
    assert by["sim_any"]["allowed"] == {"smart-twin-mcp": ["list_recent_jobs"]}, "잡 제출(single · fullangle) · 후처리 다시 돌리기는 빠진다"
    assert (by["sim_named"]["allowed"], by["sim_named"]["dropped_write"]) == (
        {"smart-twin-mcp": []}, ["smart-twin-mcp:single_drop_simulation"])
    assert by["doc"]["allowed"] == {"heax-doc_forge": []} and by["doc"]["dropped_write"] == []
    assert by["voc"]["allowed"] == {"signalforge": ["defect_profile", "search_voc"]}, "읽기 목록에 있어도 이름 꼴(ingest_)이 쓰기면 뺀다"
    ready = {s["step"]: s for s in c.get(f"{PREFIX}/routines/{rid}/readiness").json()["steps"]}
    assert ready["risk_named"]["state"] == "allowed", ready["risk_named"]
    assert "heax-hwax_risk:risk_job_action 는 읽기로 확인되지 않았다" in ready["risk_named"]["reason"] and \
        "남은 도구로 돈다" in ready["risk_named"]["reason"], ready["risk_named"]
    assert ready["sim_named"]["state"] == "unavailable" and "읽기로 확인되지 않았다" in ready["sim_named"]["reason"] and \
        "smart-twin-mcp:single_drop_simulation" in ready["sim_named"]["reason"], ready["sim_named"]
    assert ready["doc"]["state"] == "unavailable" and "하나도 읽기로 확인되지 않았다" in ready["doc"]["reason"], ready["doc"]
    assert "read_tools.local.json" in ready["doc"]["reason"], "읽기 도구라면 어떻게 여는지 까닭에 적는다"
    assert {k: (r["state"], r["reason"]) for k, r in ready.items()} == {
        k: (s["readiness"]["state"], s["readiness"]["reason"]) for k, s in by.items()}, "준비도와 계획이 같은 판정 · 같은 까닭"
    plats = {p["backend"]: {t["name"]: t["write"] for t in p["tools"]} for p in c.get(f"{PREFIX}/platforms").json()["platforms"]}
    assert plats["heax-hwax_risk"] == {n: n != "risk_get_report" for n in risk}, "고르는 화면도 같은 판정 — 읽기로 확인되지 않은 것은 쓰기 표지"
    assert plats["smart-twin-mcp"] == {n: n != "list_recent_jobs" for n in sim}
    assert plats["signalforge"] == {"defect_profile": False, "ingest_status": True, "search_voc": False, "submit_job": True}
    v = c.post(f"{PREFIX}/runs", json={"routine_id": rid, "inputs": {"model": "S26"}}, headers=h).json()
    st = {s["id"]: s for s in v["steps"]}
    assert v["write_class"] == "gateway_read" and st["risk_named"]["state"] == "pending"
    assert (st["sim_named"]["state"], st["doc"]["state"]) == ("unavailable", "unavailable"), "준비도가 말한 대로 닫혀 시작한다"
    r = _call(c, v["run"]["id"], step="risk_named", backend="heax-hwax_risk", tool="risk_job_action", h=h)
    assert r.status_code == 409 and "울타리 밖" in r.json()["detail"], "뺀 도구는 원장도 받지 않는다"
    assert _call(c, v["run"]["id"], step="risk_named", backend="heax-hwax_risk", tool="risk_get_report", h=h).status_code == 201
    # 읽기 목록을 안 주는 게이트웨이(옛 판)는 종전 판정 그대로다 — 같은 루틴이 write · 이름 꼴로 묶인다
    _use_gateway(tools, {k: x for k, x in tmap.items() if k != "routine_read"})
    plan = c.get(f"{PREFIX}/routines/{rid}/plan").json()
    by = {s["id"]: s for s in plan["steps"]}
    assert plan["write_class"] == "gateway" and by["risk_any"]["allowed"] == {"heax-hwax_risk": sorted(risk)}
    assert by["risk_named"]["dropped_write"] == [] and by["sim_named"]["allowed"] == {"smart-twin-mcp": ["single_drop_simulation"]}


def test_심의_단계의_결정문_읽기는_단계_호출_예산을_보지_않고_실행_호출_상한은_그대로다(client):
    """심의 단계가 예산을 시작에 다 쓰면 결정문을 읽지 못했다 — 게이트웨이가 save_report 를 false 로 넣으니 RA 에도 없다(C-12). 심의 단계의
    deliberate_result 만 단계 호출 예산에서 빠진다(게이트웨이 앞 검사와 같은 규칙). 진행 보기 · 심의 단계가 아닌 단계의 같은 도구 · 실행 호출
    상한은 그대로다."""
    c, _ = client
    h = _login(c, "boss@corp.com")
    tmap = {**TMAP, "map": {**TMAP["map"], "deliberate_status": "hwax-deliberation", "deliberate_result": "hwax-deliberation"}}
    _use_gateway(TOOLS + DELIB_MORE, tmap)
    spec = copy.deepcopy(RUN_SPEC)
    spec["steps"][4]["budget"] = {"calls": 1}
    spec["limits"] = {"calls": 4}
    _, r = _start(c, spec=spec, h=h)
    run_id = r.json()["run"]["id"]

    def delib(tool):
        return c.post(f"{PREFIX}/runs/{run_id}/calls", json={"step": "delib", "backend": "hwax-deliberation", "tool": tool,
                                                             "args": {"job_id": "j1"}, "ok": True, "result": '{"job_id": "j1"}'},
                      headers=h)

    assert delib("deliberate_start").json()["call_id"] == "delib.c1"
    r = delib("deliberate_status")
    assert r.status_code == 409 and r.json()["detail"] == "단계 delib 의 호출 예산(1번)을 다 썼다", "진행 보기는 예외가 아니다"
    assert delib("deliberate_result").json()["call_id"] == "delib.c2", "예산을 시작에 다 써도 결정문은 읽는다"
    assert delib("deliberate_result").json()["call_id"] == "delib.c3", "쪽이 여럿이면 이어 읽는다"
    assert _call(c, run_id, h=h).json()["call_id"] == "voc.c1"            # 실행의 넷째 호출 — 호출 상한
    r = delib("deliberate_result")
    assert r.status_code == 409 and r.json()["detail"] == "실행 상한에 닿았다(호출 4번)", "실행 호출 상한은 그대로다"
    # 심의 단계가 아니면 같은 도구도 예산을 본다(계획의 kind) — 플랫폼 단계가 심의 백엔드를 울타리로 적은 옛 판정의 계획
    _use_gateway(TOOLS + DELIB_MORE, {k: x for k, x in tmap.items() if k != "routine_read"})
    peek = copy.deepcopy(RUN_SPEC)
    peek["steps"] = [{"id": "peek", "title": "결정문 보기", "backends": ["hwax-deliberation"], "goal": "읽는다",
                      "tools": ["deliberate_result"], "budget": {"calls": 1}}]
    _, r = _start(c, spec=peek, h=h)
    run2 = r.json()["run"]["id"]
    assert _call(c, run2, step="peek", backend="hwax-deliberation", tool="deliberate_result", h=h).json()["call_id"] == "peek.c1"
    r = _call(c, run2, step="peek", backend="hwax-deliberation", tool="deliberate_result", h=h)
    assert r.status_code == 409 and r.json()["detail"] == "단계 peek 의 호출 예산(1번)을 다 썼다"


def test_덧붙인_말은_실행에_남고_이어서도_그대로다(client):
    """챗에서 루틴을 켜고 쓴 말(note)을 실행에 남긴다 — 이어서 · 고른 뒤 잇기에서 화면이 보내는 글은 '루틴 이어서: <제목>' 이라 실행기가 그 글을
    '사용자가 덧붙인 말' 로 쓰면 사람의 말이 사라졌다(C-12). 실행 보기 맨 위 칸 note 로 돌려준다(없으면 빈 글) — 2,000자까지."""
    c, _ = client
    h = _login(c, "boss@corp.com")
    rid = _create(c, h, RUN_SPEC)["id"]
    note = "스웰링 위주로 — 3분기 출하분만"
    r = c.post(f"{PREFIX}/runs", json={"routine_id": rid, "inputs": {"model": "S26"}, "note": note}, headers=h)
    assert r.status_code == 201 and r.json()["note"] == note, r.text
    run_id = r.json()["run"]["id"]
    assert c.get(f"{PREFIX}/runs/{run_id}").json()["note"] == note
    assert c.post(f"{PREFIX}/runs/{run_id}/resume", headers=h).json()["note"] == note, "이어서도 시작 때의 말"
    assert c.post(f"{PREFIX}/runs", json={"routine_id": rid, "inputs": {"model": "S26"}}, headers=h).json()["note"] == "", "말이 없으면 빈 글"
    r = c.post(f"{PREFIX}/runs", json={"routine_id": rid, "inputs": {"model": "S26"}, "note": "가" * 2001}, headers=h)
    assert r.status_code == 422, r.text
    assert c.post(f"{PREFIX}/runs", json={"routine_id": rid, "inputs": {"model": "S26"}, "note": "가" * 2000},
                  headers=h).status_code == 201


def test_키의_근거는_성공한_호출의_결과이고_받은_인자를_되돌려_준_값은_아니다(client):
    """키는 그 단계의 성공한 호출 결과에 글자 그대로 있고 그 호출의 인자(JSON)에는 없는 값만 넘긴다(C5 — 에이전트 실행기의 봉투 검사와 같은
    규칙). 모델이 짐작한 코드로 찾았는데 도구가 그 코드를 되돌려 주며 '없다' 고 하면(오류 · 빈 결과 · SignalForge no_catalog_match 꼴) 그 코드가
    다음 단계의 할 일에 박혔다 — AR-D2 가 막으려던 '지어낸 키' 다."""
    c, _ = client
    h = _login(c, "boss@corp.com")
    spec = copy.deepcopy(RUN_SPEC)
    spec["steps"][0]["budget"] = {"calls": 4}
    spec["steps"][4]["goal"] = "{{steps.voc.product_code}} 의 메커니즘"
    rid = _create(c, h, spec)["id"]

    def run(*calls, key="SM-S999"):
        run_id = c.post(f"{PREFIX}/runs", json={"routine_id": rid, "inputs": {"model": "S26"}}, headers=h).json()["run"]["id"]
        for args, result, ok in calls:
            assert _call(c, run_id, args=args, result=result, ok=ok, h=h).status_code == 201
        done = c.post(f"{PREFIX}/runs/{run_id}/steps/voc/done", json={"status": "ok", "keys": {"product_code": key}},
                      headers=h).json()
        by = {s["id"]: s for s in c.get(f"{PREFIX}/runs/{run_id}").json()["steps"]}
        return done["flags"], by["voc"]["keys"], by["delib"]["goal"]

    echo = "받은 인자를 되돌려 준 값 · 실패한 호출에만 있는 키는 넘기지 않는다: product_code"
    flags, keys, goal = run(({"q": "S26"}, "모델 'SM-S999' 를 찾을 수 없다", False))
    assert (keys, goal) == ({}, "{{steps.voc.product_code}} 의 메커니즘") and echo in flags, "실패한 호출의 오류 글은 근거가 아니다"
    flags, keys, _ = run(({"q": "SM-S999"}, '{"query": "SM-S999", "items": []}', True))
    assert keys == {} and echo in flags, "받은 인자를 되돌려 준 값은 근거가 아니다"
    flags, keys, _ = run(({"keyword": "SM-S999"}, '{"keyword": "SM-S999", "status": "no_catalog_match",'
                                                  ' "note": "SM-S999 와 일치하는 카탈로그 제품이 없다"}', True))
    assert keys == {} and echo in flags, "되돌려 준 값이 결과에 두 번 있어도 근거가 아니다(no_catalog_match 꼴)"
    flags, keys, goal = run(({"q": "SM-S938"}, '{"query": "SM-S938", "items": []}', True),
                            ({"q": "S26"}, '{"items": [{"plm_model": "SM-S938"}]}', True), key="SM-S938")
    assert (keys, goal) == ({"product_code": "SM-S938"}, "SM-S938 의 메커니즘") and flags == [], "인자에 그 값이 없는 성공한 호출이 근거다"
    flags, keys, _ = run(({"q": "S26"}, '{"items": [{"plm_model": "SM-S938"}]}', True), key="SM-X000")
    assert keys == {} and flags == ["결과에 글자 그대로 없는 키는 넘기지 않는다: product_code"], "결과에 없는 값은 종전대로"


def test_고르기는_기다리는_실행에서만_되고_멈춘_실행을_되살리지_않는다(client):
    """멈춘 실행의 고르기 단추가 다른 탭 · 앞 메시지에 남아 있으면 /pick 이 단계를 닫고 실행을 running 으로 되돌렸다 — 화면은 이어서 불러 사람이
    멈춘 실행을 끝까지 돌리고 RA 초안까지 냈다(C-12). 기다리는(waiting) 실행에서만 고른다(그 밖은 409, 상태는 그대로)."""
    c, _ = client
    h = _login(c, "boss@corp.com")
    _, r = _start(c, h=h)
    run_id = r.json()["run"]["id"]
    _call(c, run_id, result='[{"key": "SM-S938"}, {"key": "SM-S931"}]', h=h)
    amb = {"status": "ambiguous", "candidates": [{"label": "S26", "key": "SM-S938"}, {"label": "S26 FE", "key": "SM-S931"}]}
    assert c.post(f"{PREFIX}/runs/{run_id}/steps/voc/done", json=amb, headers=h).json()["run_state"] == "waiting"
    assert c.post(f"{PREFIX}/runs/{run_id}/cancel", headers=h).json() == {"ok": True, "state": "cancelled", "delib_cancelled": [],
                                                                         "delib_cancel_errors": []}
    r = c.post(f"{PREFIX}/runs/{run_id}/steps/voc/pick", json={"key": "SM-S931"}, headers=h)
    assert r.status_code == 409 and r.json()["detail"] == "실행이 cancelled 다 — 고를 수 없다", r.text
    v = c.get(f"{PREFIX}/runs/{run_id}").json()
    assert (v["run"]["state"], v["run"]["reason"]) == ("cancelled", "사람이 멈췄다"), "멈춘 실행은 멈춘 그대로"
    assert next(s for s in v["steps"] if s["id"] == "voc")["state"] == "ambiguous", "단계도 닫지 않는다"
    assert c.post(f"{PREFIX}/runs/{run_id}/resume", headers=h).status_code == 409
    _, r = _start(c, h=h)
    r = c.post(f"{PREFIX}/runs/{r.json()['run']['id']}/steps/voc/pick", json={"key": "SM-S931"}, headers=h)
    assert r.status_code == 409 and r.json()["detail"] == "실행이 running 다 — 고를 수 없다", r.text


def test_원장_쓰기_트랜잭션은_실행_상태와_단계_닫힘을_다시_본다(tmp_path):
    """라우트는 실행 · 단계를 잠금 전에 읽는다(큰 결과의 압축도 잠금 밖이다) — 그 틈에 멈춤 · 단계 닫기가 끼면 라우트 검사만으로는 멈춘 실행 ·
    닫힌 단계에 줄이 들어가고 단계가 다시 running 으로 열린다. add_call 이 쓰기 트랜잭션 안에서 다시 본다(R3-design §8). 단계 예산을 안 보는
    호출(step_budget=None — 심의 단계의 결정문 읽기)도 실행 호출 상한은 안에서 본다."""
    from app.procedures.routine_store import CallRefused
    store = RoutineStore(ProceduresStore(Settings(_env_file=None, procedures_store_path=str(tmp_path / "wb.sqlite"))))

    def new_run(limit: int = 6) -> str:
        return store.create_run(owner_sub="u", routine={"id": "r1", "title": "t"}, version={"version_id": "v1", "version_no": 1},
                                inputs={}, plan={"steps": [], "limits": {"minutes": 60, "calls": limit}, "report": {}},
                                executor="mcp", conversation_id=None, deadline=int(time.time()) + 3600, state="running",
                                reason=None, stages=[("a", "pending", None)])

    def add(run_id: str, step_budget: int | None = 4, run_budget: int = 6) -> str:
        return store.add_call(run_id=run_id, step_id="a", backend="bk", tool="t", args={}, ok=True, ms=1, result="x",
                              truncated=False, step_budget=step_budget, run_budget=run_budget)

    run_id = new_run()
    store.set_run(run_id, state="cancelled")
    with pytest.raises(CallRefused, match="실행이 cancelled 상태다"):
        add(run_id)
    assert store.calls(run_id) == [] and store.get_run(run_id=run_id, owner_sub="u")["calls"] == 0
    assert store.stages(run_id)[0]["state"] == "pending", "멈춘 실행의 단계를 running 으로 열지 않는다"
    run_id = new_run()
    store.set_stage(run_id, "a", state="ok")
    with pytest.raises(CallRefused, match=r"단계 a 는 이미 닫혔다\(ok\)"):
        add(run_id)
    assert store.calls(run_id) == [] and store.stages(run_id)[0]["state"] == "ok", "닫힌 단계를 다시 열지 않는다"
    run_id = new_run(limit=1)
    assert add(run_id, step_budget=None, run_budget=1) == "a.c1"
    with pytest.raises(CallRefused, match=r"실행 상한에 닿았다\(호출 1번\)"):
        add(run_id, step_budget=None, run_budget=1)
    assert len(store.calls(run_id)) == 1


def test_남의_실행은_실행_길_어디서나_404_이고_원장은_그대로다(client):
    """주인 검사는 실행 길마다 `_run`(owner_sub 조건) 한 곳이 맡는다 — 길 하나가 그것을 건너뛰면 남의 원장을 읽거나 쓴다(반대 검토 C-12 ②, 시험 빈칸을 메운다)."""
    c, _ = client
    h = _login(c, "boss@corp.com")
    _, r = _start(c, h=h)
    run_id = r.json()["run"]["id"]
    assert _call(c, run_id, h=h).status_code == 201
    before = c.get(f"{PREFIX}/runs/{run_id}").json()
    hp = _login(c, "peer@corp.com")              # portal-admin — 루틴 권한은 있다. 주인만 아니다
    bodies = {
        ("POST", "/runs/{run_id}/resume"): {},
        ("POST", "/runs/{run_id}/calls"): {"step": "voc", "backend": "signalforge", "tool": "search_voc", "args": {"q": "x"},
                                           "ok": True, "ms": 1, "result": "{}"},
        ("POST", "/runs/{run_id}/steps/{step}/done"): {"status": "ok", "summary": "남이 닫는다"},
        ("POST", "/runs/{run_id}/steps/{step}/pick"): {"key": "SM-S938"},
        ("POST", "/runs/{run_id}/report"): {"sections": {}},
        ("POST", "/runs/{run_id}/ra"): {"report_id": "1"},
        ("POST", "/runs/{run_id}/cancel"): {},
    }
    seen = 0
    for m, path in _routes():
        if not path.startswith(f"{PREFIX}/runs/{{run_id}}"):
            continue
        tail = path[len(PREFIX):]
        url = (path.replace("{run_id}", run_id).replace("{step}", "voc").replace("{call_id}", "voc.c1"))
        params = {"step": "delib"} if tail.endswith("/evidence") else None    # 필수 쿼리 — 없으면 주인 검사 전에 422
        r2 = c.request(m, url, headers=hp, params=params, json=bodies.get((m, tail)) if m == "POST" else None)
        assert r2.status_code == 404, (m, tail, r2.status_code, r2.text[:200])
        seen += 1
    assert seen >= 11, f"실행 길이 줄었다 — 이 시험이 보는 길 수를 다시 센다({seen})"
    _login(c, "boss@corp.com")
    after = c.get(f"{PREFIX}/runs/{run_id}").json()
    assert after["run"]["state"] == before["run"]["state"] == "running" and after["run"]["calls"] == before["run"]["calls"]
    assert [s["state"] for s in after["steps"]] == [s["state"] for s in before["steps"]], "남이 단계를 닫지 못했다"


def test_실행_목록은_대화_id_를_싣는다(client):
    """챗에서 ■ 로 끊긴 루틴 턴의 '다시 시도' 가 이 대화의 실행을 찾아 이어서로 바꾼다 — 목록에 대화 id 가 없으면 두 번째 실행을 세운다(R3 마지막 빈틈)."""
    c, _ = client
    h = _login(c, "boss@corp.com")
    rid = _create(c, h, RUN_SPEC)["id"]
    r = c.post(f"{PREFIX}/runs", json={"routine_id": rid, "inputs": {"model": "S26"}, "conversation_id": "conv-7"}, headers=h)
    assert r.status_code == 201, r.text
    rows = c.get(f"{PREFIX}/runs", params={"routine_id": rid}).json()["runs"]
    assert [(x["id"], x["conversation_id"]) for x in rows] == [(r.json()["run"]["id"], "conv-7")]


# ── 멈춤이 실행이 세운 심의를 접는다(R3-design §8 · R2 반대 검토 #2) ─────────────────────────────────────────────────────────
# 재기동 · 실행기 오류로 실행기가 사라진 뒤의 멈춤은 상태만 바꿨다 — 재기동 뒤 다시 줄 선 심의가 멈춤이 풀리면 몇 시간씩 돌며 GLM 자리를 쥐었다.
# 이제 포털 멈춤이 닫히지 않은 심의 단계의 성공한 deliberate_start 잡을 그 사람의 챗 PAT 로 접는다(게이트웨이 deliberate_cancel).
FOLD_SPEC = copy.deepcopy(RUN_SPEC)
FOLD_SPEC["steps"].append({"id": "delib2", "title": "다음 심의", "kind": "deliberation", "goal": "더 본다", "uses": ["voc"]})
FOLD_TMAP = {**TMAP, "map": {**TMAP["map"], "deliberate_cancel": "hwax-deliberation"}}


def _fold_gateway(seen: list, answer=None, tmap=FOLD_TMAP):
    """멈춤의 심의 접기를 보는 게이트웨이 — tools/call 을 (노출 이름, 인자, Authorization 의 토큰)으로 seen 에 적고 answer(job_id) →
    (isError, 글)로 답한다(None 이면 엔진의 접기 답). 그 밖(tools/list · /tools-map · 세션)은 _gateway 그대로다."""
    base = _gateway(TOOLS, tmap)

    def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content) if req.content else {}
        if body.get("method") != "tools/call":
            return base(req)
        p = body["params"]
        seen.append((p["name"], p["arguments"], req.headers.get("authorization", "").removeprefix("Bearer ")))
        jid = p["arguments"].get("job_id")
        is_err, text = answer(jid) if answer else (False, json.dumps({"job_id": jid, "status": "cancelled"}))
        payload = {"jsonrpc": "2.0", "id": 2, "result": {"content": [{"type": "text", "text": text}], "isError": is_err}}
        return httpx.Response(200, text=f"data: {json.dumps(payload, ensure_ascii=False)}\n\n",
                              headers={"content-type": "text/event-stream"})
    return handler


def _use_handler(handler, mint_pat=None):
    """이 시험만의 게이트웨이 처리기(동기 · 비동기)로 실행기를 바꿔 끼운다(mint_pat 을 주면 절차 PAT 발급도) — 픽스처가 끝에 걷는다."""
    from app.procedures.runner import ProceduresRunner
    old = app.state.procedures_runner
    app.state.procedures_runner = ProceduresRunner(
        settings=old.settings, store=old.store, mint_pat=mint_pat or old.mint_pat,
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=5.0))


def _delib_start(c, run_id, step, job_id, h, ok=True) -> str:
    r = c.post(f"{PREFIX}/runs/{run_id}/calls", json={"step": step, "backend": "hwax-deliberation", "tool": "deliberate_start",
                                                      "args": {"question": "왜"}, "ok": ok,
                                                      "result": json.dumps({"job_id": job_id, "status": "queued"})}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["call_id"]


def test_멈추면_닫히지_않은_심의_단계가_세운_심의를_그_사람의_챗_PAT_로_접는다(client):
    """접을 것은 닫히지 않은 심의 단계의 성공한 deliberate_start 잡 전부다(같은 단계에 다시 세운 것도) — 닫힌 심의 단계 · 플랫폼 단계 · 거절된
    시작은 건드리지 않는다. 토큰은 그 사람 명의의 챗 PAT 다(절차 PAT · 부른 사람의 PAT 를 그대로 넘기지 않는다) — 세션 멈춤과 Claude 길(게이트웨이
    routine_run_start 의 cancel — 부른 사람의 PAT 로 온다) 둘 다."""
    import jwt

    from app.procedures.pat import mint
    c, s = client
    h = _login(c, "boss@corp.com")
    me = c.get("/auth/me").json()
    seen: list = []
    # 절차 PAT 도 진짜 꼴로 찍는다(purpose=procedure) — 접기가 그것을 집으면 아래 표지 단언이 잡는다
    _use_handler(_fold_gateway(seen), mint_pat=lambda p, run, ix: mint(app.state.keystore, s, p, run, ix))
    _, r = _start(c, spec=FOLD_SPEC, h=h)
    run_id = r.json()["run"]["id"]
    assert _call(c, run_id, result='{"job_id": "j-voc"}', h=h).status_code == 201      # 플랫폼 단계 — 글에 job_id 가 있어도 심의가 아니다
    _delib_start(c, run_id, "delib2", "j-closed", h)
    assert c.post(f"{PREFIX}/runs/{run_id}/steps/delib2/done", json={"status": "ok", "summary": "결정문을 읽었다"},
                  headers=h).json()["state"] == "ok"                                   # 닫힌 심의 단계
    _delib_start(c, run_id, "delib", "j-refused", h, ok=False)                        # 거절된 시작 — 잡이 없다
    _delib_start(c, run_id, "delib", "j-live", h)
    _delib_start(c, run_id, "delib", "j-again", h)                                    # 같은 단계에 다시 세운 것(Claude 길)
    out = c.post(f"{PREFIX}/runs/{run_id}/cancel", headers=h).json()
    assert out == {"ok": True, "state": "cancelled", "delib_cancelled": ["j-live", "j-again"], "delib_cancel_errors": []}, out
    assert [(n, a) for n, a, _ in seen] == [("deliberate_cancel", {"job_id": "j-live"}), ("deliberate_cancel", {"job_id": "j-again"})]
    tok = seen[0][2]
    claims = jwt.decode(tok, options={"verify_signature": False})
    assert claims["pat_name"] == "chat-session" and "purpose" not in claims, "챗 PAT 다 — 절차 PAT(purpose=procedure)가 아니다"
    assert (claims["sub"], claims["email"], claims["aud"], claims["scopes"]) == (me["subject"], "boss@corp.com",
                                                                                  [s.pat_chat_audience], ["chat"])
    assert {t for _, _, t in seen} == {tok}
    v = c.get(f"{PREFIX}/runs/{run_id}").json()
    assert (v["run"]["state"], v["run"]["reason"]) == ("cancelled", "사람이 멈췄다 — 이 실행이 세운 심의 j-live · j-again 를 접었다")
    # Claude 길 — 게이트웨이가 부른 사람의 PAT 로 멈춘다. 접기는 그 PAT 가 아니라 같은 사람의 챗 PAT 로 한다
    pat = c.post("/auth/pat", json={"name": "claude"}, headers=h).json()["token"]
    _, r = _start(c, spec=FOLD_SPEC, h=h)
    run2 = r.json()["run"]["id"]
    _delib_start(c, run2, "delib", "j-claude", h)
    seen.clear()
    c.cookies.clear()
    out = c.post(f"{PREFIX}/runs/{run2}/cancel", headers={"Authorization": f"Bearer {pat}"}).json()
    assert out["delib_cancelled"] == ["j-claude"] and [a for _, a, _ in seen] == [{"job_id": "j-claude"}], out
    claims = jwt.decode(seen[0][2], options={"verify_signature": False})
    assert seen[0][2] != pat and claims["pat_name"] == "chat-session" and claims["sub"] == me["subject"] and "purpose" not in claims


def test_게이트웨이가_실패해도_멈춤은_막히지_않고_접지_못한_심의는_까닭과_함께_돌려준다(client, monkeypatch):
    """엔진의 거절 · 게이트웨이 연결 실패 · 답 없음 — 멈춤은 그대로 서고(200 · cancelled · 원장 닫힘) 접지 못한 잡은 delib_cancel_errors 와 실행의
    까닭에 남는다. 답 없는 게이트웨이는 시간 전부(DELIB_FOLD_S)에서 끊는다."""
    import asyncio

    import app.procedures.routine_routes as rr
    c, _ = client
    h = _login(c, "boss@corp.com")
    _use_handler(_fold_gateway([]))

    def run_with(*jobs) -> str:
        _, r = _start(c, spec=FOLD_SPEC, h=h)
        run_id = r.json()["run"]["id"]
        for jid in jobs:
            _delib_start(c, run_id, "delib", jid, h)
        return run_id

    gone, down, slow = run_with("j-gone", "j-ok"), run_with("j-a", "j-b"), run_with("j-slow")
    # 엔진이 거절한다(이 프로세스 밖의 잡) — 그 잡만 까닭과 함께, 나머지는 접는다
    _use_handler(_fold_gateway([], answer=lambda jid: (True, f"그런 심의 잡이 없다: {jid}") if jid == "j-gone" else (False, "{}")))
    r = c.post(f"{PREFIX}/runs/{gone}/cancel", headers=h)
    assert r.status_code == 200 and r.json()["delib_cancelled"] == ["j-ok"], r.text
    assert r.json()["delib_cancel_errors"] == [{"job_id": "j-gone", "error": "그런 심의 잡이 없다: j-gone"}]
    run = c.get(f"{PREFIX}/runs/{gone}").json()["run"]
    assert run["state"] == "cancelled" and run["reason"] == (
        "사람이 멈췄다 — 이 실행이 세운 심의 j-ok 를 접었다 — 심의 j-gone 는 접지 못했다(그런 심의 잡이 없다: j-gone). "
        "서버에서 계속 돌 수 있다 — deliberate_cancel 로 접는다")

    # 게이트웨이가 죽었다 — 멈춤은 서고, 잡마다 까닭
    def refuse(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("연결 거부", request=req)
    _use_handler(refuse)
    r = c.post(f"{PREFIX}/runs/{down}/cancel", headers=h)
    assert r.status_code == 200 and r.json()["delib_cancelled"] == [], r.text
    assert r.json()["delib_cancel_errors"] == [{"job_id": "j-a", "error": "ConnectError: 연결 거부"},
                                               {"job_id": "j-b", "error": "ConnectError: 연결 거부"}]
    assert c.get(f"{PREFIX}/runs/{down}").json()["run"]["state"] == "cancelled"
    assert _call(c, down, h=h).status_code == 409, "멈춘 실행의 원장은 닫혔다"

    # 게이트웨이가 답하지 않는다 — 시간 전부에서 끊고 멈춤 답을 낸다(붙잡지 않는다)
    monkeypatch.setattr(rr, "DELIB_FOLD_S", 0.5)
    base = _fold_gateway([])

    async def hang(req: httpx.Request) -> httpx.Response:
        if req.content and json.loads(req.content).get("method") == "tools/call":
            await asyncio.sleep(10)
        return base(req)
    _use_handler(hang)
    t0 = time.monotonic()
    r = c.post(f"{PREFIX}/runs/{slow}/cancel", headers=h)
    assert time.monotonic() - t0 < 5, "답 없는 게이트웨이가 멈춤 답을 붙잡았다"
    assert r.status_code == 200 and r.json()["delib_cancel_errors"] == [{"job_id": "j-slow", "error": "0.5초 안에 끝나지 않았다"}], r.text
    assert c.get(f"{PREFIX}/runs/{slow}").json()["run"]["state"] == "cancelled"

