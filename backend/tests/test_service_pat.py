# 서비스 PAT(박스 작업의 system:<작업> 토큰)의 클레임 꼴 · 관리자 발급 · 목록 · 회수와, 포털 챗 · 토큰 교환이 이 토큰을 받지 않는지 본다
"""docs/core-link design §2 · context-notes CK-4.

클레임 꼴은 게이트웨이 `_service_scope` 와 맞물린다 — 게이트웨이 계약 시험이 app/auth/service_pat.py 를 그대로 읽으므로 칸 하나하나를 글자 그대로
본다. 발급은 진짜 `/auth/pat/service` 길(세션 + CSRF)로 받는다. 토큰 원장은 시험마다 새 파일이다(test_pat_exchange 와 같은 격리).
"""
import ast
import importlib.util
import re
import sqlite3
import sys
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient

from app.auth import service_pat
from app.auth.service_pat import (
    SERVICE_AUDIENCE,
    SERVICE_JTI_PREFIX,
    SERVICE_MAX_DAYS,
    SERVICE_MIN_DAYS,
    SERVICE_PURPOSE,
    service_claims,
)
from app.auth.token_store import TokenStore
from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.main import app

U = "u@corp.com"
BOSS = "boss@corp.com"
PIN = "pin@corp.com"        # PORTAL_ADMIN_EMAILS 로 고정한 관리자 — 원장 groups 에 portal-admin 이 없다
ISS = "https://portal.example"
NOW = 1_800_000_000
CLAIM_KEYS = {"iss", "sub", "aud", "scope", "scopes", "pat_name", "purpose", "jti", "iat", "nbf", "exp"}
LIST_KEYS = {"jti", "job", "note", "issued_by", "created_at", "expires_at", "revoked"}


# ── 클레임 꼴(모듈 — 게이트웨이 계약 시험이 읽는 그 파일) ───────────────────────────
def test_클레임은_계약_2절_그대로다():
    c = service_claims(iss=ISS, job="core-link", now=NOW, days=30)
    assert set(c) == CLAIM_KEYS, "칸을 더하거나 빼면 게이트웨이 판별과 어긋난다 — email · name · groups 는 없다"
    assert c["iss"] == ISS
    assert c["sub"] == "system:core-link"
    assert c["aud"] == ["mcp-gateway-service"] == [SERVICE_AUDIENCE]
    assert c["scope"] == "api"
    assert c["scopes"] == ["service"]
    assert c["pat_name"] == "service:core-link"
    assert c["purpose"] == "service" == SERVICE_PURPOSE
    assert re.fullmatch(r"svc-[0-9a-f]{32}", c["jti"]) and c["jti"].startswith(SERVICE_JTI_PREFIX)
    assert (c["iat"], c["nbf"], c["exp"]) == (NOW, NOW, NOW + 30 * 86400)
    assert all(type(c[k]) is int for k in ("iat", "nbf", "exp"))


def test_jti_는_매번_새것이다():
    a, b = (service_claims(iss=ISS, job="core-link", now=NOW, days=1)["jti"] for _ in range(2))
    assert a != b


@pytest.mark.parametrize("job", ["a", "0", "core-link", "box-12-sync", "a" * 40, "9-"])
def test_작업_이름_되는_꼴(job):
    assert service_claims(iss=ISS, job=job, now=NOW, days=1)["sub"] == f"system:{job}"


@pytest.mark.parametrize("job", ["", "-core", "Core-link", "core_link", "core link", "core/link", "a" * 41,
                                 "core-link\n", "코어", None, 7])
def test_작업_이름_틀린_꼴은_ValueError(job):
    with pytest.raises(ValueError, match="job"):
        service_claims(iss=ISS, job=job, now=NOW, days=1)


@pytest.mark.parametrize("days", [SERVICE_MIN_DAYS, 90, SERVICE_MAX_DAYS])
def test_수명은_1일부터_365일까지(days):
    c = service_claims(iss=ISS, job="core-link", now=NOW, days=days)
    assert c["exp"] - c["iat"] == days * 86400
    assert (SERVICE_MIN_DAYS, SERVICE_MAX_DAYS) == (1, 365)


@pytest.mark.parametrize("days", [0, -1, 366, 36500, True, 1.5, "30", None])
def test_수명_밖은_ValueError(days):
    with pytest.raises(ValueError, match="days"):
        service_claims(iss=ISS, job="core-link", now=NOW, days=days)


def test_모듈은_표준_라이브러리만_쓰고_따로_읽힌다():
    """게이트웨이 계약 시험은 이 파일을 패키지 밖에서 spec_from_file_location 으로 읽는다(패널 PAT 와 같은 꼴) — app.* 이나 바깥 패키지를
    import 하면 그쪽 시험 환경에서 깨진다."""
    path = Path(service_pat.__file__)
    tree = ast.parse(path.read_text(encoding="utf-8"))
    mods = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    mods |= {(n.module or "").split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert mods and mods <= set(sys.stdlib_module_names), mods
    spec = importlib.util.spec_from_file_location("portal_service_pat_alone", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    c = mod.service_claims(iss=ISS, job="core-link", now=NOW, days=1)
    assert c["aud"] == [mod.SERVICE_AUDIENCE] and c["jti"].startswith(mod.SERVICE_JTI_PREFIX)


def test_포털이_받는_청중에_서비스_청중이_없다():
    """포털 챗 · 토큰 교환 · revoke-self 는 pat_chat_audience 로만 검증한다. 기본 청중(사람 PAT)에 서비스 청중이 섞이면 사람 PAT 가 게이트웨이의
    서비스 판별에 걸린다."""
    s = Settings()
    assert s.pat_chat_audience != SERVICE_AUDIENCE
    assert SERVICE_AUDIENCE not in s.pat_default_audience_list
    assert s.panel_pat_audience != SERVICE_AUDIENCE


# ── 발급 · 목록 · 회수(진짜 끝점) ─────────────────────────────────────────────────
@pytest.fixture()
def client(tmp_path):
    s = Settings(user_store_path=str(tmp_path / "users.sqlite"), local_bootstrap_admins=BOSS, portal_admin_emails=PIN)
    app.dependency_overrides[get_settings] = lambda: s
    from app.auth.routes.local import _rl
    _rl.clear()
    with TestClient(app) as c:
        app.state.user_store = UserStore(s)
        app.state.token_store = TokenStore(Settings(token_store_path=str(tmp_path / "tokens.sqlite")))
        yield c
    app.dependency_overrides.pop(get_settings, None)


def _login(c, email) -> dict:
    c.cookies.clear()
    c.post("/auth/local/login", json={"email": email, "password": "pw123456"})
    return {"X-CSRF-Token": c.cookies.get("hwax_csrf")}


@pytest.fixture()
def box(client):
    """boss(부트스트랩 관리자) · u(`feat:api-token` 허가 — 관리자 아님) · pin(고정 관리자, 원장 groups 비어 있음). boss 로 로그인해 둔다."""
    for e, n in ((BOSS, "Boss"), (U, "U"), (PIN, "Pin")):
        client.post("/auth/local/signup", json={"email": e, "name": n, "password": "pw123456"})
    hb = _login(client, BOSS)
    for e in (U, PIN):
        assert client.post(f"/auth/local/users/{e}/approve", json={"groups": []}, headers=hb).status_code == 200
    client.patch(f"/auth/access/users/{U}", json={"grants": ["feat:api-token"]}, headers=hb)
    return client, hb


def _issue(c, h, **over):
    return c.post("/auth/pat/service", json={"job": "core-link", "days": 30, "note": "BOX-11", **over}, headers=h)


def _rows(jti: str | None = None) -> list:
    sql = "SELECT jti, sub, email, name, aud, scopes, created, exp, revoked, parent_jti, issued_by, note FROM pat"
    return app.state.token_store._conn.execute(sql + (" WHERE jti = ?" if jti else ""), (jti,) if jti else ()).fetchall()


def _revoked(c) -> set[str]:
    return set(c.get("/auth/pat/revoked.json").json()["revoked"])


def test_관리자가_발급하면_토큰은_응답에만_있고_원장에_남는다(box, caplog):
    c, hb = box
    caplog.set_level("WARNING", logger="app.auth.routes.pat")
    r = _issue(c, hb)
    assert r.status_code == 200, r.text
    got = r.json()
    assert set(got) == {"token", "jti", "job", "expires_at"}
    tok = got["token"]
    pub = app.state.keystore.public_pem(jwt.get_unverified_header(tok)["kid"])
    claims = jwt.decode(tok, pub, algorithms=["RS256"], audience=SERVICE_AUDIENCE,
                        options={"require": ["exp", "aud", "sub", "jti"]})
    assert set(claims) == CLAIM_KEYS
    assert claims["iss"] == app.dependency_overrides[get_settings]().jwt_issuer      # 사람 PAT 의 iss 그대로
    assert (claims["sub"], claims["pat_name"], claims["purpose"], claims["scope"], claims["scopes"], claims["aud"]) == (
        "system:core-link", "service:core-link", "service", "api", ["service"], ["mcp-gateway-service"])
    assert claims["jti"] == got["jti"] and got["job"] == "core-link" and got["expires_at"] == claims["exp"]
    assert claims["exp"] - claims["iat"] == 30 * 86400
    # 원장 — 사람 칸(email)은 비고 발급 관리자 · 메모가 남는다. 토큰 자체는 어디에도 없다.
    row = _rows(got["jti"])
    assert row == [(got["jti"], "system:core-link", None, "service:core-link", '["mcp-gateway-service"]', '["service"]',
                    claims["iat"], claims["exp"], 0, None, BOSS, "BOX-11")]
    assert tok not in repr(_rows())
    assert any("service PAT issued:" in m and "job=core-link" in m and BOSS in m for m in caplog.messages)
    assert not any(tok in m for m in caplog.messages)


def test_목록은_칸만_싣고_토큰_값은_없다(box):
    c, hb = box
    got = _issue(c, hb).json()
    r = c.get("/auth/pat/service")
    assert r.status_code == 200, r.text
    rows = r.json()
    assert isinstance(rows, list) and len(rows) == 1
    assert set(rows[0]) == LIST_KEYS
    assert rows[0] == {"jti": got["jti"], "job": "core-link", "note": "BOX-11", "issued_by": BOSS,
                       "created_at": rows[0]["created_at"], "expires_at": got["expires_at"], "revoked": False}
    assert got["expires_at"] - rows[0]["created_at"] == 30 * 86400
    assert got["token"] not in r.text


def test_사람_PAT_과_서비스_PAT_은_서로의_목록에_섞이지_않는다(box):
    c, hb = box
    svc = _issue(c, hb).json()
    hu = _login(c, U)
    mine = c.post("/auth/pat", json={"name": "claude"}, headers=hu).json()
    assert {m["jti"] for m in c.get("/auth/pat", headers=hu).json()} == {mine["jti"]}
    hb = _login(c, BOSS)
    assert c.get("/auth/pat", headers=hb).json() == [], "관리자 자기 목록에 서비스 PAT 가 섞이면 '내 토큰' 처럼 보인다"
    assert [m["jti"] for m in c.get("/auth/pat/service").json()] == [svc["jti"]]
    # 사람 PAT 의 발급 길은 그대로다 — purpose 없음 · 발급자 · 메모 칸은 비어 있다
    assert "purpose" not in jwt.decode(mine["token"], options={"verify_signature": False})
    assert _rows(mine["jti"])[0][10:] == (None, None)


def test_고정_관리자도_발급한다(box):
    """PORTAL_ADMIN_EMAILS 로만 관리자인 사람(원장 groups 에 portal-admin 없음)도 관리자 문을 지난다 — /admin/usage 와 같은 문."""
    c, _hb = box
    hp = _login(c, PIN)
    r = _issue(c, hp, job="pin-job")
    assert r.status_code == 200, r.text
    assert _rows(r.json()["jti"])[0][10] == PIN
    assert c.get("/auth/pat/service").status_code == 200


def test_관리자가_아니면_403_로그인하지_않았으면_401(box):
    c, _hb = box
    hu = _login(c, U)                                   # feat:api-token 은 있지만 관리자는 아니다
    for r in (_issue(c, hu), c.get("/auth/pat/service")):
        assert r.status_code == 403, r.text
        assert "portal-admin" in r.json()["detail"]
    c.cookies.clear()
    assert _issue(c, {}).status_code == 401
    assert c.get("/auth/pat/service").status_code == 401
    assert _rows() == []


def test_CSRF_가_없거나_틀리면_403(box):
    c, hb = box
    for h in ({}, {"X-CSRF-Token": "wrong"}):
        r = _issue(c, h)
        assert r.status_code == 403, r.text
        assert "CSRF" in r.json()["detail"]
    assert _rows() == []
    assert _issue(c, hb).status_code == 200


@pytest.mark.parametrize("days", [0, -1, 366, 36500])
def test_수명_밖은_400(box, days):
    c, hb = box
    r = _issue(c, hb, days=days)
    assert r.status_code == 400, r.text
    assert "days" in r.json()["detail"]
    assert _rows() == []


@pytest.mark.parametrize("days", [1, 365])
def test_수명_끝값은_된다(box, days):
    c, hb = box
    got = _issue(c, hb, days=days).json()
    assert got["expires_at"] - _rows(got["jti"])[0][6] == days * 86400


@pytest.mark.parametrize("job", ["", "Core-Link", "core link", "-core", "core_link", "a" * 41, "core-link\n"])
def test_작업_꼴이_틀리면_400(box, job):
    c, hb = box
    r = _issue(c, hb, job=job)
    assert r.status_code == 400, r.text
    assert "job" in r.json()["detail"]
    assert job not in r.json()["detail"] or job == "", "거절 글에 받은 값을 되싣지 않는다"
    assert _rows() == []


def test_메모는_200자까지_없어도_된다(box):
    c, hb = box
    assert _issue(c, hb, note="가" * 201).status_code == 422
    assert _issue(c, hb, note="가" * 200).status_code == 200
    r = c.post("/auth/pat/service", json={"job": "no-note", "days": 1}, headers=hb)
    assert r.status_code == 200, r.text
    listed = {m["job"]: m["note"] for m in c.get("/auth/pat/service").json()}
    assert listed["no-note"] == ""


def test_기존_관리자_회수가_revoked_json_에_싣는다(box):
    c, hb = box
    got = _issue(c, hb).json()
    other = _issue(c, hb, job="other").json()
    assert got["jti"] not in _revoked(c)
    r = c.delete(f"/auth/pat/{got['jti']}", headers=hb)
    assert r.status_code == 200, r.text
    assert got["jti"] in _revoked(c) and other["jti"] not in _revoked(c)
    listed = {m["jti"]: m["revoked"] for m in c.get("/auth/pat/service").json()}
    assert listed == {got["jti"]: True, other["jti"]: False}


def test_관리자가_아니면_서비스_PAT_을_회수하지_못한다(box):
    c, hb = box
    got = _issue(c, hb).json()
    hu = _login(c, U)
    assert c.delete(f"/auth/pat/{got['jti']}", headers=hu).status_code == 404
    assert got["jti"] not in _revoked(c)


# ── 포털은 서비스 PAT 를 받지 않는다(청중이 다르다) ────────────────────────────────
def test_서비스_PAT_으로_토큰을_바꿔_받을_수_없다(box):
    c, hb = box
    svc = _issue(c, hb).json()["token"]
    body = {"name": "x", "audiences": [SERVICE_AUDIENCE], "scopes": ["service"], "ttl_days": 1}
    r = c.post("/auth/pat/exchange", json=body, headers={"Authorization": f"Bearer {svc}"})
    assert r.status_code == 401, r.text
    assert r.json()["detail"]["code"] == "invalid_source"
    assert len(_rows()) == 1


def test_서비스_PAT_으로_포털_챗을_부를_수_없다(box):
    c, hb = box
    svc = _issue(c, hb).json()["token"]
    hu = _login(c, U)
    mine = c.post("/auth/pat", json={"name": "claude"}, headers=hu).json()["token"]
    c.cookies.clear()                                   # 쿠키 없이 Bearer 하나로만
    assert c.get("/agent/conversations", headers={"Authorization": f"Bearer {mine}"}).status_code == 200
    assert c.get("/agent/conversations", headers={"Authorization": f"Bearer {svc}"}).status_code == 401
    r = c.post("/agent/chat", json={"message": "hi"}, headers={"Authorization": f"Bearer {svc}"})
    assert r.status_code == 401, r.text
    assert c.post("/auth/pat/revoke-self", headers={"Authorization": f"Bearer {svc}"}).status_code == 401


# ── 원장 ──────────────────────────────────────────────────────────────────────
def test_서비스_목록은_jti_머리와_sub_머리를_함께_본다(tmp_path):
    """사람 PAT 의 jti 는 무작위(token_urlsafe)라 svc- 로 시작할 수 있다 — 머리 하나로 가르면 그 사람 토큰이 서비스 목록에 섞인다."""
    ts = TokenStore(Settings(token_store_path=str(tmp_path / "t.sqlite")))
    row = {"aud": [SERVICE_AUDIENCE], "scopes": ["service"], "created": 1, "exp": 2**31}
    ts.record_pat(jti="svc-lucky", sub=U, email=U, name="claude", **row)                 # 사람 PAT, jti 만 우연히 같은 머리
    ts.record_pat(jti="plain", sub="system:core-link", email=None, name="x", **row)       # sub 만 같은 머리
    ts.record_pat(jti="svc-real", sub="system:core-link", email=None, name="service:core-link", issued_by=BOSS, **row)
    assert [m["jti"] for m in ts.service_pats()] == ["svc-real"]


# ── 원장 이관 ───────────────────────────────────────────────────────────────────
def test_돌고_있는_원장에_issued_by_note_칸이_생긴다(tmp_path):
    path = tmp_path / "old.sqlite"
    old = sqlite3.connect(path)
    old.execute("CREATE TABLE pat (jti TEXT PRIMARY KEY, sub TEXT NOT NULL, email TEXT, name TEXT, "
                "aud TEXT NOT NULL, scopes TEXT NOT NULL, created INTEGER NOT NULL, "
                "exp INTEGER NOT NULL, revoked INTEGER NOT NULL DEFAULT 0, parent_jti TEXT)")
    old.execute("INSERT INTO pat VALUES ('p', ?, ?, 'claude', '[]', '[]', 1, ?, 0, NULL)", (U, U, 2**31))
    old.commit()
    old.close()
    ts = TokenStore(Settings(token_store_path=str(path)))
    TokenStore(Settings(token_store_path=str(path)))      # 두 번째 기동도 멀쩡하다(멱등)
    cols = {r[1] for r in ts._conn.execute("PRAGMA table_info(pat)")}
    assert {"parent_jti", "issued_by", "note"} <= cols
    c = service_claims(iss=ISS, job="core-link", now=NOW, days=1)
    ts.record_pat(jti=c["jti"], sub=c["sub"], email=None, name=c["pat_name"], aud=c["aud"], scopes=c["scopes"],
                  created=c["iat"], exp=2**31, issued_by=BOSS, note="m")
    assert [m["jti"] for m in ts.list_pats(U)] == ["p"]            # 옛 행이 그대로 있고 사람 목록에 서비스 PAT 이 없다
    assert [(m["jti"], m["issued_by"], m["note"]) for m in ts.service_pats()] == [(c["jti"], BOSS, "m")]
