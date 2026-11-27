# 자동 파이프라인 창구 /autopipe-api — 권한 전수(grant_only — 전권 소속 · 관리자도 403) · CSRF · 꺼짐일 때 409 · 상태 꼴 · 규칙 → 현황판 → 승인 흐름
"""포털을 TestClient 로 띄우고 원장 · 엔진만 임시 것으로 바꾼다. 게이트웨이 · 앱은 계약 꼴 가짜(MockTransport)다 — 공유 서비스를 부르지 않는다."""
from __future__ import annotations

import asyncio
import re

import httpx
import pytest
from autopipe_fakes import SPEC, SRC, T0, THERMAL, FakeAnalysis, FakeGateway, FakeSource
from fastapi.testclient import TestClient

from app.access.policy import compute, load_raw, parse_policy
from app.agent import ra_post as _ra_post
from app.auth.user_store import UserStore
from app.autopipe.engine import Engine
from app.autopipe.store import AutoStore
from app.config import BACKEND_DIR, Settings, get_settings
from app.main import app
from app.procedures.store import ProceduresStore

PREFIX = "/autopipe-api"
PW = "pw123456"
KEY = "feat:auto-pipeline"


def _login(c, email) -> dict:
    c.cookies.clear()
    assert c.post("/auth/local/login", json={"email": email, "password": PW}).status_code == 200
    return {"X-CSRF-Token": c.cookies.get("hwax_csrf")}


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.delenv("PORTAL_ADMIN_EMAILS", raising=False)
    monkeypatch.setattr(_ra_post, "PATH", tmp_path / "없는-ra-formats.json")
    s = Settings(_env_file=None, user_store_path=str(tmp_path / "users.sqlite"), token_store_path=str(tmp_path / "tok.sqlite"),
                 conv_store_path=str(tmp_path / "conv.sqlite"), procedures_store_path=str(tmp_path / "wb.sqlite"),
                 conn_key_path=str(tmp_path / "conn.key"), jwt_keys_dir=str(tmp_path / "keys"), local_bootstrap_admins="boss@example.com",
                 mcp_gateway_url="http://gw.test", auto_pipeline_enabled=False, auto_pipeline_tick_s=0)
    box = {"s": s, "t": T0}
    app.dependency_overrides[get_settings] = lambda: box["s"]
    from app.auth.routes.local import _rl
    _rl.clear()
    src, thermal = FakeSource(SRC), FakeAnalysis(THERMAL)
    gw = FakeGateway(src, thermal)
    loop_client = httpx.AsyncClient(transport=httpx.MockTransport(gw))
    with TestClient(app) as c:
        keep = (app.state.user_store, app.state.autopipe_store, app.state.autopipe_engine)
        app.state.user_store = UserStore(s)
        base = ProceduresStore(s)
        app.state.autopipe_store = AutoStore(base)
        app.state.autopipe_engine = Engine(settings=s, store=app.state.autopipe_store, mint=lambda run, step: "tok", client=loop_client,
                                           clock=lambda: box["t"])
        for email in ("boss@example.com", "caeg@example.com", "op@example.com"):
            assert c.post("/auth/local/signup", json={"email": email, "name": email.split("@")[0], "password": PW}).status_code < 300
        for email in ("caeg@example.com", "op@example.com"):
            assert app.state.user_store.approve(email, by="boss@example.com", groups=[])
        hb = _login(c, "boss@example.com")
        assert c.patch("/auth/access/users/caeg@example.com", json={"affiliation": "CAEG"}, headers=hb).status_code == 200
        assert c.patch("/auth/access/users/op@example.com", json={"grants": [KEY]}, headers=hb).status_code == 200
        c.cookies.clear()
        box.update(src=src, thermal=thermal, gw=gw)
        yield c, box
        app.state.user_store, app.state.autopipe_store, app.state.autopipe_engine = keep
        base.close()
    asyncio.run(loop_client.aclose())
    app.dependency_overrides.pop(get_settings, None)


def _routes() -> list[tuple[str, str]]:
    out = []
    for r in app.routes:
        path = getattr(r, "path", "")
        if path.startswith(PREFIX):
            out += [(m, path) for m in sorted(getattr(r, "methods", set()) - {"HEAD", "OPTIONS"})]
    return sorted(out)


def test_박스_스위치는_값이_있을_때만_넘기고_예시는_주석으로만_적는다():
    root = BACKEND_DIR.parent
    start = (root / "infra/scripts/start.sh").read_text(encoding="utf-8")
    assert re.search(r"for k in AUTO_PIPELINE_ENABLED AUTO_PIPELINE_TICK_S[^;]*; do\n\s+\[ -n \"\$\{!k:-\}\" \] && AP_ENVS\+=", start)
    assert '${AP_ENVS[@]+"${AP_ENVS[@]}"}' in start.split('"$APPTAINER" instance start', 1)[1].split('"$PORTAL_SIF"', 1)[0]
    ex = (root / "infra/.env.example").read_text(encoding="utf-8")
    assert "# AUTO_PIPELINE_ENABLED=1" in ex and not re.search(r"(?m)^AUTO_PIPELINE_", ex), "env-sync 가 켜서 옮겨 적지 않게 — 기본 꺼짐"
    assert Settings(_env_file=None).auto_pipeline_enabled is False


def test_권한은_grant_only_라_전권_소속과_관리자에게도_닫혀_있다():
    pol = parse_policy(load_raw(BACKEND_DIR / "config" / "access.yaml"))
    assert pol.item(KEY) is not None and pol.item(KEY).grant_only
    assert KEY in pol.keys and KEY not in pol.broad_keys
    assert KEY not in compute(pol, groups=[], row={"affiliation": "CAEG", "grants": [], "groups": []}).keys
    assert KEY not in compute(pol, groups=[], row={"groups": ["portal-admin"], "grants": []}).keys
    assert KEY in compute(pol, groups=[], row={"grants": [KEY]}).keys


def test_창구는_모두_권한을_본다(env):
    c, _ = env
    routes = _routes()
    assert len(routes) == 15, routes
    for who in ("boss@example.com", "caeg@example.com"):
        h = _login(c, who)
        for method, path in routes:
            url = re.sub(r"\{[^}]+\}", "x", path)
            r = c.request(method, url, headers=h, json={"spec": {}, "enabled": True} if method == "POST" else None,
                          params={"step": "s"} if url.endswith("/report") else None)
            assert r.status_code == 403, (who, method, path, r.status_code, r.text[:200])
    c.cookies.clear()
    assert c.get(f"{PREFIX}/health").status_code == 401


def test_쓰기는_CSRF_를_본다(env):
    c, _ = env
    _login(c, "op@example.com")
    assert c.post(f"{PREFIX}/rules", json={"spec": SPEC}).status_code == 403
    assert c.post(f"{PREFIX}/validate", json={"spec": SPEC}).status_code == 200, "검증은 저장하지 않는다(문서 — CSRF 없음)"


def test_꺼져_있으면_tick_승인_취소는_409_이고_규칙_편집_검증은_된다(env):
    c, box = env
    h = _login(c, "op@example.com")
    hl = c.get(f"{PREFIX}/health").json()
    assert hl["enabled"] is False and "AUTO_PIPELINE_ENABLED=1" in hl["how_to_enable"]
    assert set(hl) == {"enabled", "how_to_enable", "engine", "sources", "ra", "counts"}
    assert {"running", "last_tick", "last_error"} <= set(hl["engine"]) and {"configured", "board"} <= set(hl["ra"])
    assert c.post(f"{PREFIX}/tick", headers=h).status_code == 409
    assert c.post(f"{PREFIX}/runs/x/approve", headers=h).status_code == 409
    assert c.post(f"{PREFIX}/runs/x/cancel", headers=h).status_code == 409
    r = c.post(f"{PREFIX}/rules", json={"spec": SPEC}, headers=h)
    assert r.status_code == 200 and r.json()["version_no"] == 1
    rid = r.json()["id"]
    assert c.post(f"{PREFIX}/rules/{rid}/enabled", json={"enabled": True}, headers=h).json()["enabled"] is True
    bad = c.post(f"{PREFIX}/rules/{rid}/versions", json={"spec": {**SPEC, "stage": "live"}}, headers=h)
    assert bad.status_code == 422 and any("stage" in e for e in bad.json()["errors"])
    v = c.post(f"{PREFIX}/validate", json={"spec": {**SPEC, "steps": [{"id": "d", "kind": "deliberation"}]}}, headers=h).json()
    assert v["ok"] is False and any("M5" in e for e in v["errors"])
    assert box["gw"].calls == [], "꺼져 있으면 게이트웨이를 부르지 않는다"


def test_규칙에서_현황판_승인_보고서까지(env):
    c, box = env
    box["s"] = box["s"].model_copy(update={"auto_pipeline_enabled": True})
    app.state.autopipe_engine.settings = box["s"]
    h = _login(c, "op@example.com")
    rid = c.post(f"{PREFIX}/rules", json={"spec": {**SPEC, "stage": "approve"}}, headers=h).json()["id"]
    assert c.post(f"{PREFIX}/rules/{rid}/enabled", json={"enabled": True}, headers=h).status_code == 200
    box["src"].add("TASK-A", "dv1", at=box["t"] + 10)
    box["t"] += 20
    assert c.post(f"{PREFIX}/tick", headers=h).status_code == 200
    subs = c.get(f"{PREFIX}/subjects").json()["subjects"]
    assert subs[0]["project"] == "TASK-A" and subs[0]["state"] == "waiting_quiet" and "skey" not in subs[0]
    box["t"] += 700
    c.post(f"{PREFIX}/tick", headers=h)
    board = c.get(f"{PREFIX}/board", params={"rule": rid}).json()
    assert board["columns"] == ["thermal", "summary"]
    row = board["rows"][0]
    assert (row["project"], row["revision"], row["run_state"]) == ("TASK-A", "dv1", "awaiting_approval")
    assert row["steps"]["thermal"] == {"state": "ready", "verdict": None}
    run_id = row["run_id"]
    assert c.post(f"{PREFIX}/runs/{run_id}/approve", headers=h).json()["run"]["approved_by"] == "op@example.com"
    assert c.post(f"{PREFIX}/runs/{run_id}/approve", headers=h).status_code == 409
    for dt in (1, 120, 120):
        box["t"] += dt
        c.post(f"{PREFIX}/tick", headers=h)
    d = c.get(f"{PREFIX}/runs/{run_id}").json()
    assert d["run"]["state"] == "done" and {s["step_id"]: s["state"] for s in d["steps"]} == {"thermal": "done", "summary": "done"}
    assert all("report_md" not in s for s in d["steps"]) and [s["has_report"] for s in d["steps"]] == [False, True]
    assert "approved" in [e["kind"] for e in d["events"]]
    md = c.get(f"{PREFIX}/runs/{run_id}/report", params={"step": "summary"})
    assert md.status_code == 200 and md.text.startswith("# [자동]") and md.headers["content-type"].startswith("text/markdown")
    assert c.get(f"{PREFIX}/runs/{run_id}/report", params={"step": "thermal"}).status_code == 404
    assert c.get(f"{PREFIX}/runs", params={"state": "done"}).json()["runs"][0]["id"] == run_id
    hl = c.get(f"{PREFIX}/health").json()
    assert hl["enabled"] is True and hl["how_to_enable"] is None and hl["sources"][0]["app"] == SRC and hl["counts"]["runs"] == {"done": 1}
    assert c.get(f"{PREFIX}/rules").json()["rules"][0]["stage"] == "approve"
    assert c.get(f"{PREFIX}/rules/{rid}").json()["versions"][0]["version_no"] == 1
    assert c.get(f"{PREFIX}/rules/없음").status_code == 404 and c.get(f"{PREFIX}/runs/없음").status_code == 404
