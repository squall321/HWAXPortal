# 소속·허가 기반 접근 — 정책 대조·권한 계산·요청 승인·즉시 회수(PAT)·게이트웨이 조회·가드
import json
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from app.access import agent_guard
from app.access.policy import compute, parse_policy
from app.agent import upload as up
from app.auth.provider import Principal
from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.main import app

_BACKEND = Path(__file__).resolve().parents[1]
_ROOT = _BACKEND.parent


def _policy():
    return parse_policy(
        yaml.safe_load((_BACKEND / "config" / "access.yaml").read_text(encoding="utf-8"))
    )


# ── 정책 대조 ────────────────────────────────────────────────────────────────
def test_모든_포털_타일이_어느_플랫폼에든_속한다():
    pol = _policy()
    tiles = [
        s["id"]
        for s in yaml.safe_load((_BACKEND / "config" / "systems.yaml").read_text(encoding="utf-8"))[
            "systems"
        ]
    ]
    missing = [t for t in tiles if pol.system_key(t) is None]
    assert not missing, f"플랫폼 표에 없는 타일 — 권한과 무관하게 모두에게 보인다: {missing}"


def test_HE팀_페르소나_앱이_모두_플랫폼에_속한다():
    pol = _policy()
    spec = json.loads((_ROOT / "infra" / "personas" / "he-team.json").read_text(encoding="utf-8"))
    for p in spec["personas"]:
        assert pol.keys_for_gateway(p["apps"]), f"{p['key']} 의 앱 {p['apps']} 이 플랫폼 표에 없다"


def test_CAEG_는_전부_기본은_일반_챗():
    pol = _policy()
    assert pol.affiliations["CAEG"]["grants"] == ["*"]
    assert pol.default_grants == ["feat:chat"]
    assert pol.gateway_policy()["hwax-deliberation"] == ["feat:deliberation"], (
        "MCP 심의 도구도 기능 권한으로 막는다"
    )


# ── 권한 계산 ────────────────────────────────────────────────────────────────
def test_계산_관리자·소속·개별·함의_그리고_들어온_합성그룹은_버린다():
    pol = _policy()
    admin = compute(pol, groups=["portal-admin"], row=None)
    assert admin.keys == set(pol.keys) and admin.is_admin
    caeg = compute(pol, groups=[], row={"affiliation": "CAEG", "grants": [], "groups": []})
    assert caeg.keys == set(pol.keys) and caeg.reasons["feat:deliberation"] == "affiliation"
    none = compute(
        pol, groups=["feat:deliberation", "plat:stepforge"], row={"affiliation": "", "grants": []}
    )
    assert none.keys == {"feat:chat"}, "JWT·PAT 에 박힌 합성 그룹이 권한이 되면 거둔 권한이 남는다"
    g = compute(
        pol, groups=[], row={"affiliation": "", "grants": ["feat:deliberation", "plat:nope"]}
    )
    assert g.keys == {"feat:chat", "feat:deliberation", "plat:aidatahub"}, (
        "표에 없는 키는 버리고 함의는 더한다"
    )
    assert g.reasons["plat:aidatahub"] == "implied:feat:deliberation"


# ── API 흐름 ────────────────────────────────────────────────────────────────
@pytest.fixture()
def client(tmp_path):
    s = Settings(
        user_store_path=str(tmp_path / "users.sqlite"),
        local_bootstrap_admins="boss@corp.com",
        gateway_shared_token="gw-test-secret",
    )
    app.dependency_overrides[get_settings] = lambda: s
    from app.auth.routes.local import _rl

    _rl.clear()
    with TestClient(app) as c:
        # 컨텍스트 진입 후 교체(실DB 오염 방지 — test_local_auth 와 같다)
        app.state.user_store = UserStore(s)
        yield c
    app.dependency_overrides.pop(get_settings, None)


def _login(c, email):
    r = c.post("/auth/local/login", json={"email": email, "password": "pw123456"})
    assert r.status_code == 200, r.text
    return {"X-CSRF-Token": c.cookies.get("hwax_csrf")}


def _setup_users(c):
    c.post(
        "/auth/local/signup",
        json={"email": "boss@corp.com", "name": "Boss", "password": "pw123456"},
    )
    c.post(
        "/auth/local/signup",
        json={"email": "user@corp.com", "name": "User", "password": "pw123456"},
    )
    h = _login(c, "boss@corp.com")
    assert (
        c.post(
            "/auth/local/users/user@corp.com/approve", json={"groups": []}, headers=h
        ).status_code
        == 200
    )


def test_CAEG_밖은_일반_챗만_요청하고_승인되면_바로_보인다(client):
    _setup_users(client)
    h = _login(client, "user@corp.com")
    me = client.get("/auth/me").json()
    assert me["entitlements"] == ["feat:chat"] and me["affiliation"] == ""
    assert client.get("/systems").json() == [], "플랫폼 허가가 없으면 타일이 하나도 안 보인다"
    assert client.post("/auth/pat", json={"name": "t"}, headers=h).status_code == 403
    assert client.post("/agent/deliberate/voc", json={"message": "x"}, headers=h).status_code == 403
    assert (
        client.post("/agent/chat", json={"message": "x", "thinking": True}, headers=h).status_code
        == 403
    )
    # 회귀 — 프론트는 일반 챗에도 delib_opts(search_sources 담아)를 늘 싣는다. 심의 권한으로 막으면
    # 모든 챗이 403 이 된다(구현 중 실제로 그렇게 짰다가 잡았다).
    import httpx

    real = app.state.agent_client
    app.state.agent_client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda req: httpx.Response(200, stream=httpx.ByteStream(b"event: done\ndata: {}\n\n"))
        )
    )
    try:
        r = client.post(
            "/agent/chat",
            json={"message": "안녕", "delib_opts": {"search_sources": []}, "search_sources": []},
            headers=h,
        )
    finally:
        app.state.agent_client = real
    assert r.status_code == 200, "일반 챗은 기본 권한만으로 된다"
    table = client.get("/auth/access").json()
    feats = {r["key"]: r for r in table["features"]}
    assert feats["feat:chat"]["allowed"] and feats["feat:chat"]["reason"] == "모든 사용자 기본"
    assert not feats["feat:deliberation"]["allowed"]

    r = client.post(
        "/auth/access/requests",
        json={"key": "feat:deliberation", "note": "원인 규명에 씁니다"},
        headers=h,
    )
    assert r.json()["status"] == "pending"
    again = client.post(
        "/auth/access/requests", json={"key": "feat:deliberation"}, headers=h
    ).json()
    assert again["duplicate"] is True, "두 번 눌러도 요청은 하나"
    assert client.get("/auth/access/requests").status_code == 403, "요청 목록은 관리자만"

    ha = _login(client, "boss@corp.com")
    reqs = client.get("/auth/access/requests").json()
    assert [(q["email"], q["key"]) for q in reqs] == [("user@corp.com", "feat:deliberation")]
    assert (
        client.post(
            f"/auth/access/requests/{reqs[0]['id']}/decide", json={"approve": True}, headers=ha
        ).status_code
        == 200
    )

    _login(client, "user@corp.com")
    me = client.get("/auth/me").json()
    assert {"feat:deliberation", "plat:aidatahub"} <= set(me["entitlements"])
    rows = {
        r["key"]: r
        for r in client.get("/auth/access").json()["features"]
        + client.get("/auth/access").json()["platforms"]
    }
    assert rows["feat:deliberation"]["reason"] == "개별 허가"
    assert rows["plat:aidatahub"]["reason"] == "전문가 심의에 포함"


def test_관리자가_소속을_CAEG_로_두면_전부_열리고_표에_없는_값은_거절한다(client):
    _setup_users(client)
    ha = _login(client, "boss@corp.com")
    assert (
        client.patch(
            "/auth/access/users/user@corp.com", json={"affiliation": "CAEG"}, headers=ha
        ).status_code
        == 200
    )
    assert (
        client.patch(
            "/auth/access/users/user@corp.com", json={"affiliation": "NOPE"}, headers=ha
        ).status_code
        == 422
    )
    assert (
        client.patch(
            "/auth/access/users/user@corp.com", json={"grants": ["feat:typo"]}, headers=ha
        ).status_code
        == 422
    )
    n_tiles = len(client.get("/systems").json())
    hu = _login(client, "user@corp.com")
    me = client.get("/auth/me").json()
    assert me["affiliation"] == "CAEG" and "feat:deliberation" in me["entitlements"]
    assert len(client.get("/systems").json()) == n_tiles, "CAEG 는 관리자와 같은 타일을 본다"
    assert (
        client.patch(
            "/auth/access/users/user@corp.com", json={"affiliation": ""}, headers=hu
        ).status_code
        == 403
    )


def test_PAT_는_발급_때_권한이_아니라_지금_권한을_탄다(client):
    _setup_users(client)
    ha = _login(client, "boss@corp.com")
    client.patch(
        "/auth/access/users/user@corp.com",
        json={"grants": ["feat:api-token", "feat:deliberation"]},
        headers=ha,
    )
    hu = _login(client, "user@corp.com")
    tok = client.post("/auth/pat", json={"name": "claude", "ttl_days": 30}, headers=hu).json()[
        "token"
    ]
    bearer = {"Authorization": f"Bearer {tok}"}
    import httpx

    real = app.state.agent_client
    app.state.agent_client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda req: httpx.Response(200, json={"applicable": False, "slots": [], "ask": []})
        )
    )
    try:
        client.cookies.clear()
        ok = client.post("/agent/deliberate/clarify", json={"message": "x"}, headers=bearer)
        assert ok.status_code == 200, "대조군 — 권한이 있을 때는 같은 토큰이 통과한다"
        ha = _login(client, "boss@corp.com")
        client.patch(
            "/auth/access/users/user@corp.com", json={"grants": ["feat:api-token"]}, headers=ha
        )
        client.cookies.clear()
        r = client.post("/agent/deliberate/clarify", json={"message": "x"}, headers=bearer)
    finally:
        app.state.agent_client = real
    assert r.status_code == 403, "거둔 권한이 PAT 수명 동안 남으면 안 된다"
    assert "feat:deliberation" in r.json().get("detail", r.text)


def test_게이트웨이_내부_조회는_공유_시크릿으로만(client):
    _setup_users(client)
    assert client.get("/internal/access/policy").status_code == 403
    auth = {"Authorization": "Bearer gw-test-secret"}
    pol = client.get("/internal/access/policy", headers=auth).json()["backends"]
    assert pol["heax-step_forge"] == ["plat:stepforge"] and pol["ai-data-hub"] == ["plat:aidatahub"]
    ents = client.get(
        "/internal/access/entitlements", params={"email": "user@corp.com"}, headers=auth
    ).json()
    assert ents["keys"] == ["feat:chat"]
    adm = client.get(
        "/internal/access/entitlements",
        params={"email": "x@corp.com", "groups": "portal-admin"},
        headers=auth,
    ).json()
    assert "plat:stepforge" in adm["keys"], "토큰의 관리자 그룹은 인정한다"


# ── 챗·업로드 가드(단위) ──────────────────────────────────────────────────────
def _p(*groups):
    return Principal(subject="u", email="u@corp.com", groups=list(groups))


def test_HE팀_운영자는_그_플랫폼_허가가_있어야_고르고_보인다():
    pol = _policy()
    from app.auth.errors import AuthError

    with pytest.raises(AuthError):
        no_plat = _p("feat:chat", "feat:expert-chat")
        agent_guard.check_chat(pol, no_plat, thinking=False, pinned_agent="he-cad-stepforge")
    ok = _p("feat:expert-chat", "plat:stepforge")
    agent_guard.check_chat(pol, ok, thinking=False, pinned_agent="he-cad-stepforge")
    with pytest.raises(AuthError):
        agent_guard.check_chat(pol, _p("feat:chat"), thinking=True, pinned_agent=None)
    resp = {"pool": [{"key": "he-cad-stepforge"}, {"key": "rel-drop-impact"}], "recommended": []}
    out = agent_guard.filter_experts(resp, pol, ["feat:expert-chat"])
    assert [r["key"] for r in out["pool"]] == ["rel-drop-impact"]


def test_업로드는_기능_권한과_목적지_플랫폼이_함께_있어야_한다():
    s = Settings(upload_allowed_groups="", upload_groups_step="")
    assert [
        d["id"] for d in up.allowed_destinations(s, ["feat:upload", "plat:stepforge"], "step")
    ] == ["stepforge"]
    assert up.allowed_destinations(s, ["plat:stepforge"], "step") == [], (
        "기능 권한 없이 플랫폼만으로는 못 올린다"
    )
    assert up.allowed_destinations(s, ["feat:upload", "plat:stepforge"], "csv") == [], (
        "물성 DB 는 materialtwin 허가"
    )
