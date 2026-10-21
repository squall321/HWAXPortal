# 외부 연결을 설정만으로 — 박스 권한표 connect: 선언의 파싱 · 내부 정책 응답 · '외부 연결' 목록 · 등록 · 해제 · 재기동 없는 반영 · 합성 권한
"""docs/ext-connect(요청서 1-8 포털 시험). 모든 파일은 임시 폴더에 쓰고 주소는 지어낸 이름이다(*.test) — 리포의 backend/config 는 건드리지
않고, 포털 코드가 만드는 AsyncClient 는 MockTransport 로 바꿔 진짜 서비스 · 게이트웨이를 치지 않는다.

  · 선언은 박스 파일에서만 읽는다. 추적 파일의 connect 는 떼고 알린다. 틀린 블록은 그 블록만 버리고 알린다(모르는 칸도).
  · 내부 정책 응답의 connections 키는 늘 backends 에 있다(한 파싱 · 한 응답).
  · 등록은 브라우저 세션 + CSRF 만 — 포털 JWT · 다른 서비스 접두 · 꼴이 틀린 토큰은 네트워크를 쓰기 전에 거른다. 확인은 trust_env=False.
"""
import json
import logging
import os
from pathlib import Path

import httpx
import jwt
import pytest
from fastapi.testclient import TestClient

from app.access.policy import AccessPolicy, CONNECT_FEATURE, compute, load_raw, parse_policy
from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.main import app

GW = "gw-test-secret"
_REAL_CLIENT = httpx.AsyncClient

BASE = """
default_grants: [feat:chat]
affiliations:
  - {id: CAEG, label: CAE그룹, grants: ["*"]}
features:
  - {id: chat, label: 일반 챗}
  - {id: api-token, label: API 토큰}
platforms:
  - {id: fmea, label: FMEA Agent, systems: [fmea], gateway: [fmea], hide_unless_routed: true}
  - {id: matnexus, label: MatNexus, systems: [matnexus], gateway: [matnexus]}
  - {id: reportarchive, label: Report Archive, systems: [report-archive], gateway: [reportarchive]}
"""

FMEA = {"mcp_url": "http://fmea.test:5190/mcp", "token_prefix": "fmea_", "issue": "토큰 메뉴(/tokens)에서 발급한 토큰",
        "issue_url": "http://fmea.test:5195/tokens", "verify": "mcp", "list_auth": "registered:Lister@Corp.com",
        "note": "쓰기 도구 2개는 이 토큰 주인 명의로 저장합니다."}
MNX = {"mcp_url": "http://mnx.test:8012/mcp", "token_prefix": "mnx_pat_", "verify": "none",
       "issue": "내 계정 › 토큰에서 발급"}


def _local(**platforms) -> str:
    """박스 파일 — 플랫폼 id → (항목 칸, connect 블록 또는 None)."""
    rows = []
    for pid, (item, connect) in platforms.items():
        row = {"id": pid, **item}
        if connect is not None:
            row["connect"] = connect
        rows.append(row)
    return json.dumps({"platforms": rows}, ensure_ascii=False)        # JSON 은 YAML 이다


def _fmea_item(**over):
    return {"label": "FMEA Agent", "desc": "FMEA 분석", "systems": ["fmea"], "gateway": ["fmea"],
            "hide_unless_routed": True, **over}


def _mnx_item(**over):
    return {"label": "MatNexus", "systems": ["matnexus"], "gateway": ["matnexus"], **over}


def _write(p: Path, text: str, *, tick: int = 0) -> Path:
    p.write_text(text, encoding="utf-8")
    if tick:
        st = p.stat()
        os.utime(p, (st.st_atime + tick, st.st_mtime + tick))
    return p


@pytest.fixture()
def box(tmp_path):
    base = _write(tmp_path / "access.yaml", BASE)
    return base, tmp_path / "access.local.yaml"


def _parse(box, text):
    base, local = box
    _write(local, text)
    return parse_policy(load_raw(base))


# ── 파싱 ─────────────────────────────────────────────────────────────────────
def test_박스_파일의_선언_둘이_읽히고_게이트웨이에는_쓰는_칸만_간다(box):
    pol = _parse(box, _local(fmea=(_fmea_item(), FMEA), matnexus=(_mnx_item(), MNX)))
    assert not pol.warnings, pol.warnings
    conns = pol.connections()
    assert sorted(conns) == ["fmea", "matnexus"]
    f = conns["fmea"]
    assert (f.backend, f.platform_id, f.label, f.desc, f.need) == ("fmea", "fmea", "FMEA Agent", "FMEA 분석", "plat:fmea")
    assert f.token_hint == "fmea_…", "자리표시 기본값은 접두 + …"
    assert f.list_auth == "registered:lister@corp.com", "목록 계정 이메일은 소문자로 맞춘다"
    gw = pol.gateway_connections()
    assert set(gw) <= set(pol.gateway_policy()), "선언 키는 늘 권한 행에 있다"
    assert gw["fmea"] == {"platform": "fmea", "label": "FMEA Agent", "desc": "FMEA 분석", "hint": "fmea_…", "prefix": "fmea_",
                          "mcp_url": "http://fmea.test:5190/mcp", "list_auth": "registered:lister@corp.com", "read_tools": [],
                          "workspace_header": ""}
    blob = json.dumps(gw, ensure_ascii=False)
    assert "발급한 토큰" not in blob and "verify" not in blob, "카드 문구 · 확인 방법은 게이트웨이로 가지 않는다"


def test_추적_파일의_connect_는_떼고_알린다(box):
    base, _local_path = box
    _write(base, BASE.replace("gateway: [matnexus]}", "gateway: [matnexus], connect: {mcp_url: 'http://mnx.test:8012/mcp'}}"))
    pol = parse_policy(load_raw(base))
    assert pol.connections() == {}
    (note,) = pol.warnings
    assert "access.yaml" in note and "matnexus" in note and "connect" in note and "박스 파일" in note


def test_gateway_를_빼고_바꿔_쓴_박스_항목은_connect_도_버린다(box):
    pol = _parse(box, _local(matnexus=({"label": "MatNexus", "systems": ["matnexus"]}, MNX)))
    assert pol.connections() == {}
    assert any("matnexus" in w and "gateway:" in w for w in pol.warnings), pol.warnings


@pytest.mark.parametrize("bad,needle", [
    ({"backend": "other"}, "gateway:"),
    ({"backend": "testscope"}, "받지 않는다"),
    ({"backend": "reportarchive"}, "받지 않는다"),
    ({"backend": "heax-thing"}, "받지 않는다"),
    ({"backend": "Bad Key"}, "꼴"),
    ({"mcp_url": "http://mnx.test:8012/mcp?token=abc"}, "쿼리"),
    ({"mcp_url": "http://user@mnx.test:8012/mcp"}, "계정"),
    ({"mcp_url": "http://mnx.test:8012/mcp#x"}, "조각"),
    ({"mcp_url": "ftp://mnx.test/mcp"}, "http(s)"),
    ({"mcp_url": "http://mnx test/mcp"}, "호스트"),
    ({"mcp_url": ""}, "비었다"),
    ({"issue_url": "javascript:alert(1)"}, "issue_url"),
    ({"list_auth": "everyone"}, "list_auth"),
    ({"list_auth": "registered:nobody"}, "list_auth"),
    ({"workspace_header": "Authorization"}, "헤더"),
    ({"workspace_header": "X-Hwax-User"}, "헤더"),
    ({"workspace_header": "Mcp-Session-Id"}, "헤더"),
    ({"workspace_label": "부서"}, "workspace_header"),
    ({"verify": "mcp", "owner_field": "email"}, "owner_field"),
    ({"verify": "url"}, "verify_url"),
    ({"verify_url": "http://mnx.test:8010/api/auth/me"}, "verify_url"),
    ({"verify": "maybe"}, "verify"),
    ({"owner_feild": "email"}, "모르는 칸"),
    ({"token_prefix": "mnx pat"}, "token_prefix"),
    ({"read_tools": "list_all"}, "read_tools"),
    ({"issue": 3}, "글자가 아니다"),
    ({"note": "가" * 1001}, "1000자"),
], ids=lambda v: json.dumps(v, ensure_ascii=False)[:40] if isinstance(v, dict) else str(v))
def test_틀린_블록은_그_블록만_버리고_알린다(box, bad, needle):
    backend = bad.get("backend")
    # 내장 · 허브 · 꼴 틀린 키는 gateway: 안에 있어도 버린다 — 'other' 만 gateway: 밖의 키다
    item = _mnx_item(gateway=["matnexus"] + ([backend] if backend and backend != "other" else []))
    pol = _parse(box, _local(fmea=(_fmea_item(), FMEA), matnexus=(item, {**MNX, **bad})))
    assert sorted(pol.connections()) == ["fmea"], "다른 플랫폼의 선언은 그대로 산다"
    assert pol.item("plat:matnexus") is not None, "플랫폼 행은 그대로 — 버리는 것은 connect 블록뿐이다"
    warn = [w for w in pol.warnings if "'matnexus'" in w]
    assert len(warn) == 1 and needle in warn[0], pol.warnings


def test_connect_가_매핑이_아니면_버린다(box):
    pol = _parse(box, _local(matnexus=(_mnx_item(), "yes")))
    assert pol.connections() == {} and any("매핑" in w for w in pol.warnings)


def test_같은_백엔드_키를_두_플랫폼이_선언하면_뒤엣것을_버린다(box):
    pol = _parse(box, _local(fmea=(_fmea_item(gateway=["fmea", "shared"]), {**FMEA, "backend": "shared"}),
                             matnexus=(_mnx_item(gateway=["matnexus", "shared"]), {**MNX, "backend": "shared"})))
    assert sorted(pol.connections()) == ["shared"] and pol.connections()["shared"].platform_id == "fmea"
    assert any("이미 선언" in w for w in pol.warnings)


def test_합성_권한_feat_connect_는_선언_플랫폼_권한을_따라온다(box):
    pol = _parse(box, _local(matnexus=(_mnx_item(), MNX)))
    row = {"email": "u@corp.com", "status": "active", "affiliation": "", "grants": ["plat:matnexus"]}
    ents = compute(pol, groups=[], row=row)
    assert CONNECT_FEATURE in ents.keys and ents.reasons[CONNECT_FEATURE] == "implied:plat:matnexus"
    assert CONNECT_FEATURE not in compute(pol, groups=[], row={**row, "grants": ["plat:fmea"]}).keys, \
        "선언이 없는 플랫폼 권한은 문을 열지 않는다"
    assert CONNECT_FEATURE not in compute(pol, groups=[], row={**row, "grants": []}).keys
    assert CONNECT_FEATURE in compute(pol, groups=[], row={**row, "affiliation": "CAEG", "grants": []}).keys
    box[1].unlink()                                            # 박스 파일이 없으면 선언도 없다
    assert CONNECT_FEATURE not in compute(parse_policy(load_raw(box[0])), groups=[], row={**row, "affiliation": "CAEG"}).keys, \
        "선언이 하나도 없으면 아무에게도 없다"


# ── API ──────────────────────────────────────────────────────────────────────
class _Catalog:
    """카탈로그 대역 — live_ids 만 정하고 나머지는 진짜에 넘긴다(숨긴 키 셈만 바꾼다)."""

    def __init__(self, real, live):
        self._real, self._live = real, set(live)

    def live_ids(self):
        return set(self._live)

    def __getattr__(self, name):
        return getattr(self._real, name)


def _net(monkeypatch, handler=None):
    """포털 코드가 만드는 AsyncClient 를 MockTransport 로 — (보낸 요청, 만든 클라이언트의 인자) 를 돌려준다."""
    seen: list[httpx.Request] = []
    made: list[dict] = []

    def _h(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        if req.url.path == "/conn-invalidate":
            return httpx.Response(200, json={"ok": True})
        if handler is None:
            raise AssertionError(f"네트워크를 쓰지 않아야 한다 — {req.method} {req.url}")
        return handler(req)

    def _client(**kw):
        made.append(dict(kw))
        return _REAL_CLIENT(transport=httpx.MockTransport(_h), **kw)

    monkeypatch.setattr(httpx, "AsyncClient", _client)
    return seen, made


@pytest.fixture
def portal(tmp_path, box):
    base, local = box
    _write(local, _local(fmea=(_fmea_item(), FMEA), matnexus=(_mnx_item(), MNX),
                         plain=({"label": "Plain", "gateway": ["plain"]},
                                {"mcp_url": "http://plain.test/mcp", "verify": "none"}),
                         owned=({"label": "Owned", "gateway": ["owned"]},
                                {"mcp_url": "http://own.test/mcp", "verify": "url", "verify_url": "http://own.test/api/me",
                                 "owner_field": "email", "token_prefix": "own_"})))
    s = Settings(_env_file=None, user_store_path=str(tmp_path / "u.sqlite"), access_path=str(base),
                 local_bootstrap_admins="boss@corp.com", gateway_shared_token=GW, mcp_gateway_url="http://gw.test:9110")
    app.dependency_overrides[get_settings] = lambda: s
    from app.auth.routes.local import _rl
    _rl.clear()
    c = TestClient(app)
    c.__enter__()
    app.state.user_store = UserStore(s)
    app.state.access = AccessPolicy(s)
    real_catalog = app.state.catalog
    app.state.catalog = _Catalog(real_catalog, live=["matnexus"])       # fmea 타일은 이 박스에 없다 → 숨긴 키
    for email in ("boss@corp.com", "user@corp.com"):
        c.post("/auth/local/signup", json={"email": email, "name": email[:4], "password": "pw123456"})
    _login(c, "boss@corp.com")
    assert c.post("/auth/local/users/user@corp.com/approve", json={"groups": []},
                  headers={"X-CSRF-Token": c.cookies.get("hwax_csrf")}).status_code == 200
    c.settings, c.local = s, local
    yield c
    app.state.catalog = real_catalog
    c.__exit__(None, None, None)
    app.dependency_overrides.pop(get_settings, None)


def _login(c, email):
    r = c.post("/auth/local/login", json={"email": email, "password": "pw123456"})
    assert r.status_code == 200, r.text
    return {"X-CSRF-Token": c.cookies.get("hwax_csrf")}


def _store(c):
    return c.app.state.user_store


def _put(c, service, token, **body):
    return c.put(f"/auth/connections/ext/{service}", json={"token": token, **body},
                 headers={"X-CSRF-Token": c.cookies.get("hwax_csrf")})


def _ext(c):
    r = c.get("/auth/connections/ext")
    assert r.status_code == 200, r.text
    return r.json()


def test_목록은_선언마다_문구_권한_상태를_내고_주소_자격은_내지_않는다(portal):
    out = _ext(portal)
    by = {p["service"]: p for p in out["platforms"]}
    assert sorted(by) == ["fmea", "matnexus", "owned", "plain"]
    f = by["fmea"]
    assert (f["label"], f["token_hint"], f["verify"], f["need"], f["entitled"]) == (
        "FMEA Agent", "fmea_…", "mcp", "plat:fmea", True), "관리자는 전부 쓸 수 있다"
    assert f["issue"].startswith("토큰 메뉴") and f["issue_url"] == "http://fmea.test:5195/tokens" and f["note"]
    assert f["requestable"] is False, "타일이 없는 숨긴 플랫폼은 요청을 받지 않는다(관리자에게 문의)"
    assert by["matnexus"]["requestable"] is True and f["connected"] is None
    assert by["owned"]["owner_checked"] is True and f["owner_checked"] is False, "화면이 '주인을 확인하지 않습니다' 를 고른다"
    blob = json.dumps(out, ensure_ascii=False)
    for secret in ("5190/mcp", "mnx.test:8012", "registered:", "lister@", "verify_url", "/api/me", "list_auth"):
        assert secret not in blob, secret
    assert out["orphans"] == []


def test_권한이_없으면_entitled_가_거짓이고_합성_권한도_없다(portal):
    _login(portal, "user@corp.com")
    assert all(p["entitled"] is False for p in _ext(portal)["platforms"])
    assert CONNECT_FEATURE not in portal.get("/auth/me").json()["entitlements"]
    _store(portal).set_access("user@corp.com", affiliation="", grants=["plat:matnexus"])
    by = {p["service"]: p["entitled"] for p in _ext(portal)["platforms"]}
    assert by == {"fmea": False, "matnexus": True, "owned": False, "plain": False}
    assert CONNECT_FEATURE in portal.get("/auth/me").json()["entitlements"], "선언 플랫폼 권한 하나로 '외부 연결' 문이 열린다"


def test_고아_행은_내장도_선언도_아닌_것만_나온다(portal):
    st = _store(portal)
    st.set_connection(email="boss@corp.com", service="oldsvc", token="old_token_1234", workspace="")
    st.set_connection(email="boss@corp.com", service="reportarchive", token="rat_abcdefgh", workspace="")
    st.set_connection(email="boss@corp.com", service="matnexus", token="mnx_pat_abcdefgh", workspace="")
    out = _ext(portal)
    assert [o["service"] for o in out["orphans"]] == ["oldsvc"] and out["orphans"][0]["tail"] == "1234"
    assert {p["service"]: p["connected"]["tail"] for p in out["platforms"] if p["connected"]} == {"matnexus": "efgh"}


def test_내부_정책의_connections_키는_늘_backends_에_있고_틀린_토큰은_403(portal):
    r = portal.get("/internal/access/policy", headers={"Authorization": f"Bearer {GW}"})
    assert r.status_code == 200
    body = r.json()
    assert sorted(body["connections"]) == ["fmea", "matnexus", "owned", "plain"]
    assert set(body["connections"]) <= set(body["backends"])
    assert body["connections"]["fmea"]["list_auth"] == "registered:lister@corp.com"
    assert portal.get("/internal/access/policy", headers={"Authorization": "Bearer nope"}).status_code == 403


# ── 등록 ─────────────────────────────────────────────────────────────────────
def test_등록은_세션과_CSRF_만_받는다(portal, monkeypatch):
    _net(monkeypatch)
    assert portal.put("/auth/connections/ext/matnexus", json={"token": "mnx_pat_abcdefgh"}).status_code == 403
    anon = TestClient(app)
    r = anon.put("/auth/connections/ext/matnexus", json={"token": "mnx_pat_abcdefgh"},
                 headers={"Authorization": "Bearer some.portal.pat"})
    assert r.status_code in (401, 403), "PAT 로는 남의 행에 토큰을 넣지 못한다"
    assert _store(portal).get_connection(email="boss@corp.com", service="matnexus") is None


@pytest.mark.parametrize("service", ["nope", "reportarchive", "testscope", "Bad_Upper"])
def test_모르는_연결과_내장_키는_404(portal, monkeypatch, service):
    _net(monkeypatch)
    assert _put(portal, service, "mnx_pat_abcdefgh").status_code == 404
    assert portal.delete(f"/auth/connections/ext/{service}",
                         headers={"X-CSRF-Token": portal.cookies.get("hwax_csrf")}).status_code == 404


def test_권한이_없는_플랫폼은_403(portal, monkeypatch):
    _net(monkeypatch)
    _login(portal, "user@corp.com")
    r = _put(portal, "matnexus", "mnx_pat_abcdefgh")
    assert r.status_code == 403 and "plat:matnexus" in r.json()["detail"]


def test_Bearer_를_붙여도_같은_값으로_저장하고_게이트웨이_캐시를_깬다(portal, monkeypatch, caplog):
    seen, _made = _net(monkeypatch)
    caplog.set_level(logging.INFO)
    for raw in ("Bearer mnx_pat_abcdefgh", "  bearer   mnx_pat_abcdefgh ", "mnx_pat_abcdefgh"):
        r = _put(portal, "matnexus", raw)
        assert r.status_code == 200, r.text
        assert r.json() == {"ok": True, "verify": "none"}
        assert _store(portal).get_connection(email="boss@corp.com", service="matnexus") == {
            "token": "mnx_pat_abcdefgh", "workspace": ""}
    assert [q.url.path for q in seen] == ["/conn-invalidate"] * 3, "verify: none 은 그쪽에 묻지 않는다"
    assert "mnx_pat_abcdefgh" not in caplog.text and "connection set: matnexus" in caplog.text


@pytest.mark.parametrize("service,token,needle", [
    ("matnexus", "fmea_abcdefgh", "mnx_pat_ 로 시작"),
    ("plain", "fmea_abcdefgh", "fmea_ 로 시작하는 토큰은 다른 서비스"),
    ("plain", "rat_abcdefgh123", "rat_ 로 시작하는 토큰은 다른 서비스"),
    ("plain", "tsc_pat_abcdefgh", "tsc_pat_ 로 시작하는 토큰은 다른 서비스"),
    ("matnexus", "mnx_pat_ab cdefgh", "토큰 꼴"),
    ("matnexus", "mnx_pat_ab\ncdefgh", "토큰 꼴"),
    ("matnexus", "mnx_patXabcdefgh", "mnx_pat_ 로 시작"),
    ("plain", "short", "토큰 꼴"),
])
def test_꼴이_틀리거나_다른_서비스의_토큰은_네트워크_전에_거른다(portal, monkeypatch, service, token, needle):
    seen, _made = _net(monkeypatch)
    r = _put(portal, service, token)
    assert r.status_code == 400 and needle in r.json()["detail"], r.text
    assert seen == [] and _store(portal).get_connection(email="boss@corp.com", service=service) is None


def test_자기_접두의_앞부분인_다른_접두는_막지_않는다(box, tmp_path, monkeypatch):
    base, local = box
    _write(local, _local(matnexus=(_mnx_item(), MNX),
                         mnx=({"label": "Mnx", "gateway": ["mnx"]}, {"mcp_url": "http://m.test/mcp", "token_prefix": "mnx_"})))
    from app.auth.routes.connections import _foreign_prefix
    reg = parse_policy(load_raw(base)).connections()
    assert _foreign_prefix(reg["matnexus"], "mnx_pat_abcdefgh", reg) == "", "mnx_ 는 mnx_pat_ 의 앞부분이다"
    assert _foreign_prefix(reg["mnx"], "mnx_pat_abcdefgh", reg) == "mnx_pat_", "더 긴 다른 접두는 잡는다"
    assert _foreign_prefix(reg["mnx"], "mnx_abcdefgh", reg) == ""


def test_포털_JWT_는_네트워크를_쓰지_않고_거절한다(portal, monkeypatch):
    seen, _made = _net(monkeypatch)
    tok = jwt.encode({"iss": portal.settings.jwt_issuer, "sub": "boss@corp.com", "aud": "hwax-chat"}, "k", algorithm="HS256")
    r = _put(portal, "plain", tok)
    assert r.status_code == 400 and "HWAX 포털 토큰" in r.json()["detail"]
    assert seen == []
    other = jwt.encode({"iss": "https://elsewhere.test", "sub": "x"}, "k", algorithm="HS256")
    assert _put(portal, "plain", other).status_code == 200, "다른 발급자의 JWT 는 그 서비스의 토큰일 수 있다"


def test_mcp_확인은_initialize_200_이면_저장하고_세션을_닫는다(portal, monkeypatch):
    def fmea(req):
        if req.method == "POST":
            assert json.loads(req.content)["method"] == "initialize"
            assert req.headers["Authorization"] == "Bearer fmea_abcdefgh"
            assert "text/event-stream" in req.headers["Accept"]
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": {}}, headers={"Mcp-Session-Id": "s-1"})
        assert req.method == "DELETE" and req.headers["Mcp-Session-Id"] == "s-1"
        return httpx.Response(204)

    seen, made = _net(monkeypatch, fmea)
    r = _put(portal, "fmea", "Bearer fmea_abcdefgh")
    assert r.status_code == 200 and r.json()["verify"] == "mcp", r.text
    assert [(q.method, q.url.host) for q in seen if q.url.host == "fmea.test"] == [("POST", "fmea.test"), ("DELETE", "fmea.test")]
    assert any(kw.get("trust_env") is False for kw in made), "사람 토큰이 사내 프록시를 지나지 않게"
    assert _store(portal).get_connection(email="boss@corp.com", service="fmea")["token"] == "fmea_abcdefgh"


@pytest.mark.parametrize("resp,code,needle", [
    (httpx.Response(401, json={"error": {"code": "unauthenticated"}}), 400, "거부했습니다"),
    (httpx.Response(403), 400, "거부했습니다"),
    (httpx.Response(500), 400, "HTTP 500"),
])
def test_mcp_확인이_거절하면_저장하지_않는다(portal, monkeypatch, resp, code, needle):
    _net(monkeypatch, lambda req: resp)
    r = _put(portal, "fmea", "fmea_abcdefgh")
    assert r.status_code == code and needle in r.json()["detail"], r.text
    assert "unauthenticated" not in r.text, "그쪽 응답 본문은 돌려주지 않는다"
    assert _store(portal).get_connection(email="boss@corp.com", service="fmea") is None


def test_확인_주소에_못_닿으면_502_이고_저장하지_않는다(portal, monkeypatch):
    def down(req):
        raise httpx.ConnectError("refused", request=req)

    _net(monkeypatch, down)
    r = _put(portal, "fmea", "fmea_abcdefgh")
    assert r.status_code == 502 and "ConnectError" in r.json()["detail"]
    assert _store(portal).get_connection(email="boss@corp.com", service="fmea") is None


@pytest.mark.parametrize("payload,code", [
    ({"email": "Boss@Corp.com"}, 200),
    ({"data": {"email": "boss@corp.com"}}, 200),
    ({"email": "other@corp.com"}, 400),
    ({"email": ""}, 502),
    ({"id": 1}, 502),
])
def test_owner_field_가_있으면_주인을_fail_closed_로_본다(portal, monkeypatch, payload, code):
    _net(monkeypatch, lambda req: httpx.Response(200, json=payload))
    r = _put(portal, "owned", "own_abcdefgh")
    assert r.status_code == code, r.text
    stored = _store(portal).get_connection(email="boss@corp.com", service="owned")
    assert (stored is not None) == (code == 200)


def test_워크스페이스는_선언된_헤더가_있을_때만_받는다(portal, monkeypatch):
    _net(monkeypatch)
    r = _put(portal, "matnexus", "mnx_pat_abcdefgh", workspace="dept")
    assert r.status_code == 400 and "워크스페이스" in r.json()["detail"]


# ── 해제 ─────────────────────────────────────────────────────────────────────
def test_해제는_CSRF_를_보고_고아_행도_지우고_캐시를_깬다(portal, monkeypatch):
    seen, _made = _net(monkeypatch)
    st = _store(portal)
    st.set_connection(email="boss@corp.com", service="oldsvc", token="old_token_1234", workspace="")
    assert portal.delete("/auth/connections/ext/oldsvc").status_code == 403
    r = portal.delete("/auth/connections/ext/oldsvc", headers={"X-CSRF-Token": portal.cookies.get("hwax_csrf")})
    assert r.status_code == 200 and st.get_connection(email="boss@corp.com", service="oldsvc") is None
    assert [q.url.path for q in seen] == ["/conn-invalidate"]
    assert portal.delete("/auth/connections/ext/oldsvc",
                         headers={"X-CSRF-Token": portal.cookies.get("hwax_csrf")}).status_code == 404


# ── 재기동 없는 반영 · 내부 조회 ───────────────────────────────────────────────
def test_박스_파일을_고치면_다음_요청부터_반영되고_선언을_지우면_내부_조회가_404(portal, monkeypatch):
    _net(monkeypatch)
    assert _put(portal, "matnexus", "mnx_pat_abcdefgh").status_code == 200
    q = {"email": "boss@corp.com"}
    gw = {"Authorization": f"Bearer {GW}"}
    r = portal.get("/internal/connections/matnexus", params=q, headers=gw)
    assert r.status_code == 200 and r.json() == {"token": "mnx_pat_abcdefgh", "workspace": ""}
    _write(portal.local, _local(fmea=(_fmea_item(), FMEA), matnexus=(_mnx_item(), None)), tick=5)
    assert [p["service"] for p in _ext(portal)["platforms"]] == ["fmea"]
    assert [o["service"] for o in _ext(portal)["orphans"]] == ["matnexus"], "선언이 사라진 행은 고아로 보인다"
    assert portal.get("/internal/connections/matnexus", params=q, headers=gw).status_code == 404
    _write(portal.local, _local(fmea=(_fmea_item(), FMEA), matnexus=(_mnx_item(), MNX)), tick=10)
    assert portal.get("/internal/connections/matnexus", params=q, headers=gw).status_code == 200


def test_내장_연결의_목록_응답은_한_글자도_바뀌지_않는다(portal):
    """기존 /auth/connections 는 그대로다 — 새 목록은 새 주소로 낸다(TestScope 시험이 키 집합을 정확히 단언한다)."""
    body = portal.get("/auth/connections").json()
    assert set(body) == {"reportarchive", "testscope", "reportarchive_mode", "testscope_enabled", "testscope_mode"}
