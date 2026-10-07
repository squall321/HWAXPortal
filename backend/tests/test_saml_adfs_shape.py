# 운영 ADFS 모양의 Assertion(NameID 없음·URI Claim 다섯 개)으로 끝까지 로그인한다(6차 요청 §2·§3·§4-B)
"""운영 ADFS(sts.secsso.net)는 NameID 를 보내지 않고 Claim 은 LoginId·CompId·DeptId·Sabun·Mail 다섯 개뿐이다(2026-10-01
SSO 운영팀 실측). python3-saml 은 wantNameId 가 참이면 NameID 부재를 검증 실패로 쳐서, 서명·시간·Audience 를 다 통과한 Assertion 이
막혔다. dev mock IdP 가 실제로 서명한 Assertion 을 서명 **전에** 운영 모양으로 바꿔(NameID 빼거나 다른 값으로, Claim 다섯 + 선택 Claim)
실제 SP 검증 경로로 끝까지 돌린다. 시나리오는 JSON 한 덩이로 넘긴다.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
CLAIM = "http://schemas.sec.com/2018/05/identity/claims/"

_E2E = r'''
import json, re, sys
from urllib.parse import urlsplit
from fastapi.testclient import TestClient
from onelogin.saml2.utils import OneLogin_Saml2_Utils
import app.auth.routes.mock_idp as mock_idp
from app.main import app

CLAIM = "http://schemas.sec.com/2018/05/identity/claims/"
SPEC = json.loads(sys.argv[1])
_real_sign = OneLogin_Saml2_Utils.add_sign

def _attr(name, value):
    return (f'<saml:Attribute Name="{CLAIM}{name}"><saml:AttributeValue xsi:type="xs:string">{value}'
            '</saml:AttributeValue></saml:Attribute>')

class _AdfsShape(OneLogin_Saml2_Utils):
    """서명 직전의 Assertion 을 운영 모양으로 — NameID 는 빼거나(기본) SPEC 값으로, Claim 은 다섯 + SPEC.extra."""
    @staticmethod
    def add_sign(xml, *a, **kw):
        nid = SPEC.get("nameid")
        xml = re.sub(r"(<saml:NameID[^>]*>)[^<]*(</saml:NameID>)",
                     (lambda m: m.group(1) + nid + m.group(2)) if nid else "", xml)
        claims = [("LoginId", "kpark01"), ("CompId", "C100"), ("DeptId", "D2001"), ("Sabun", "1234567"),
                  ("Mail", SPEC.get("mail", "koo.park@example.com")), *SPEC.get("extra", {}).items()]
        attrs = "".join(_attr(n, v) for n, v in claims)
        xml = re.sub(r"<saml:AttributeStatement>.*</saml:AttributeStatement>",
                     f"<saml:AttributeStatement>{attrs}</saml:AttributeStatement>", xml, flags=re.S)
        assert ("NameID" in xml) == bool(nid)
        return _real_sign(xml, *a, **kw)

mock_idp.OneLogin_Saml2_Utils = _AdfsShape

def path(u):
    p = urlsplit(u); return p.path + ("?" + p.query if p.query else "")

out = {}
with TestClient(app, base_url="http://localhost:5283") as c:
    # 로컬 계정 시절의 대화 — subject 는 정규화된 이메일이다(local.py: subject=u["email"])
    app.state.conv_store.create(owner_sub="koo.park@example.com", title="로컬 계정 시절 대화")
    us = app.state.user_store
    for row in SPEC.get("seed", []):          # 로컬 계정 시절 원장 행(이름·부서·소속)
        us.signup(email=row["email"], name=row["name"], password="pw123456",
                  bootstrap_admins=[] if row.get("pending") else [row["email"]], department=row.get("department", ""))
        if row.get("affiliation"):
            us.set_access(row["email"], affiliation=row["affiliation"], grants=None)
        if row.get("sabun"):                  # 전에 SSO 로 들어와 사번이 적힌 행
            us.note_sso_login(email=row["email"], name=None, sabun=row["sabun"])
        if row.get("disabled"):
            us.set_status(row["email"], "disabled")
    r = c.get("/auth/login", follow_redirects=False)
    # 보낸 AuthnRequest(디코드)와 SP 메타데이터 — NameIDPolicy·SLO 광고를 본다(7차 요청)
    from urllib.parse import parse_qs
    raw = OneLogin_Saml2_Utils.decode_base64_and_inflate(parse_qs(urlsplit(r.headers["location"]).query)["SAMLRequest"][0])
    out["authn"] = raw.decode() if isinstance(raw, bytes) else raw
    md = c.get("/auth/saml/metadata")
    out["md_status"], out["md"] = md.status_code, md.text
    r2 = c.get(path(r.headers["location"]), follow_redirects=False)
    html = r2.text.replace("&amp;", "&")
    action = re.search(r'action="([^"]+)"', html).group(1)
    data = {"SAMLResponse": re.search(r'name="SAMLResponse" value="([^"]+)"', html).group(1)}
    m = re.search(r'name="RelayState" value="([^"]+)"', html)
    if m:
        data["RelayState"] = m.group(1)
    r3 = c.post(path(action), data=data, follow_redirects=False)
    out["status"] = r3.status_code
    out["body"] = r3.text[:400]
    out["location"] = r3.headers.get("location", "")
    # 실패는 로그인 화면으로 돌아간다(흰 JSON 화면 대신) — 원인은 detail 로 함께 간다
    if "/login?error=" in out["location"]:
        from urllib.parse import parse_qs as _pq
        q = _pq(urlsplit(out["location"]).query)
        out["failed"] = q.get("detail", [""])[0]
    elif r3.status_code in (302, 303):
        me = c.get("/auth/me")
        out["me_status"] = me.status_code
        out["me"] = me.json() if me.status_code == 200 else me.text[:300]
        out["convs"] = [x["title"] for x in c.get("/agent/conversations").json().get("conversations", [])]
        out["row"] = {k: v for k, v in (us.get(out["me"]["email"]) or {}).items()
                      if k in ("name", "department", "dept_id", "affiliation", "groups", "grants", "status")}
        # 접속 원장의 이번 로그인 줄 — 포털이 소속을 넣었으면 그 출처가 붙는다(10차 요청 §2)
        out["login_detail"] = app.state.agent_audit.query_access(
            since=0, include_auto=True, email=out["me"]["email"], event="login")[0]["detail"]
print(json.dumps(out, ensure_ascii=False))
'''


def _run(tmp_path, *, want_nameid: str | None = "false", env_extra: dict | None = None, **spec) -> dict:
    env = {**os.environ,
           "AUTH_PROVIDER": "saml", "APP_ENV": "dev", "SAML_MOCK_IDP_ENABLED": "true",
           "PUBLIC_BASE_URL": "http://localhost:5283", "FRONTEND_URL": "http://localhost:5283",
           "SAML_ACS_PATH": "/auth/callback", "SAML_ATTR_EMAIL": CLAIM + "Mail",
           "SESSION_SECRET": "t" * 48, "COOKIE_SECURE": "false",
           # 기동이 실 저장소를 건드리지 않게 전부 임시로(test_saml_acs_path 와 같은 묶음)
           "USER_STORE_PATH": str(tmp_path / "users.sqlite"), "TOKEN_STORE_PATH": str(tmp_path / "tok.sqlite"),
           "CONV_STORE_PATH": str(tmp_path / "conv.sqlite"), "PROCEDURES_STORE_PATH": str(tmp_path / "proc.sqlite"),
           "AGENT_AUDIT_LOG_PATH": str(tmp_path / "audit.sqlite"), "JWT_KEYS_DIR": str(tmp_path / "jwt"),
           "JWT_AUTOGEN_KEYS": "true", "PROCEDURES_ARTIFACT_ROOT": str(tmp_path / "art"),
           "DELIB_ARCHIVE_ROOT": str(tmp_path / "delib"), "UPLOAD_STAGING_DIR": str(tmp_path / "stage")}
    for k in ("SAML_WANT_NAMEID", "SAML_SUBJECT_SOURCE", "SAML_ATTR_NAME", "SAML_ATTR_DEPARTMENT", "SAML_ATTR_DEPT_ID",
              "SAML_ATTR_SABUN", "SAML_SEND_NAMEID_POLICY", "SAML_ADVERTISE_SLO", "SSO_DEFAULT_AFFILIATION", "ACCESS_PATH"):
        env.pop(k, None)
    if want_nameid is not None:
        env["SAML_WANT_NAMEID"] = want_nameid
    env.update(env_extra or {})
    r = subprocess.run([sys.executable, "-c", _E2E, json.dumps(spec)], cwd=BACKEND, env=env, capture_output=True,
                       text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-2000:]
    return {**json.loads(r.stdout.strip().splitlines()[-1]), "stderr": r.stderr}


def _failed(out: dict) -> str:
    """실패한 로그인 — 로그인 화면(/login?error=sso)으로 돌아갔고 원인 원문이 detail 로 갔는지. 원인 문자열을 돌려준다."""
    assert out["status"] in (302, 303) and "/login?error=sso" in out["location"], out
    assert out.get("failed"), f"원인(detail)이 비었다 — 운영 진단 단서가 사라진다: {out}"
    return out["failed"]


needs_keys = pytest.mark.skipif(
    not ((BACKEND / "secrets/saml/sp.key").exists() and (BACKEND / "secrets/saml/idp.key").exists()),
    reason="개발용 SAML 키(backend/secrets/saml/*.key)가 없다 — 추적 파일이 아니다(scripts/gen_dev_certs.py)")


# ── §2 NameID 없음 ──────────────────────────────────────────────────────────────────────────
@needs_keys
def test_기본값_그대로면_NameID_없는_Assertion_은_로그인_실패다(tmp_path):
    """**운영에서 막던 그 줄의 재현** — 기본값을 바꾸지 않았다는 것도 같이 고정한다. 실패는 로그인 화면으로, 원인은 detail 로."""
    out = _run(tmp_path, want_nameid=None)
    assert "NameID" in _failed(out), out


@needs_keys
def test_NameID_를_요구하지_않으면_Mail_Claim_으로_로그인된다(tmp_path):
    out = _run(tmp_path)
    assert out["status"] in (302, 303), out
    me = out["me"]
    assert out["me_status"] == 200, out
    assert me["email"] == "koo.park@example.com" and me["subject"] == "koo.park@example.com", me
    # 이름·그룹 Claim 이 없다 — 그래도 로그인은 되고, 기본 권한(일반 챗)은 원장에서 나온다
    assert me["groups"] == [] and "feat:chat" in me["entitlements"], me


@needs_keys
def test_Mail_Claim_의_대소문자가_달라도_로컬_계정_시절_소유가_이어진다(tmp_path):
    """AD 의 mail 값은 'Koo.Park@…' 처럼 대문자가 섞인다. 로컬 계정은 소문자로 저장되고 subject 가 곧 그 이메일이라, 정규화하지 않으면
    SAML 로 넘어온 같은 사람이 **다른 subject** 가 되어 대화·PAT·절차가 통째로 안 보인다(로컬 계정 브리지의 승계 약속이 깨진다)."""
    out = _run(tmp_path, mail="Koo.Park@Example.COM ")
    assert out["status"] in (302, 303), out
    assert out["me"]["email"] == "koo.park@example.com" and out["me"]["subject"] == "koo.park@example.com", out["me"]
    assert out["convs"] == ["로컬 계정 시절 대화"], out


# ── §3 subject 고정 ─────────────────────────────────────────────────────────────────────────
@needs_keys
def test_IdP_가_NameID_를_켜도_식별자는_이메일_그대로다(tmp_path):
    """**지뢰 제거** — 종전 `nameid or email` 은 NameID 가 오는 순간 식별자가 말없이 바뀌어 PAT·대화 소유가 끊겼다."""
    out = _run(tmp_path, nameid="kpark01")
    assert out["status"] in (302, 303), out
    assert out["me"]["subject"] == "koo.park@example.com", out["me"]
    assert out["convs"] == ["로컬 계정 시절 대화"], out


@needs_keys
def test_식별자_출처를_Claim_으로_고르면_그_값이다(tmp_path):
    out = _run(tmp_path, env_extra={"SAML_SUBJECT_SOURCE": CLAIM + "LoginId"})
    assert out["status"] in (302, 303), out
    assert out["me"]["subject"] == "kpark01" and out["me"]["email"] == "koo.park@example.com", out["me"]


@needs_keys
def test_고른_식별자_출처가_없으면_이메일로_몰래_바꾸지_않고_거절한다(tmp_path):
    """'nameid' 를 골랐는데 NameID 가 없다 — 이메일로 떨어지면 로그인마다 키가 바뀌어 한 사람이 둘로 갈린다."""
    for source in ("nameid", CLAIM + "NoSuchClaim"):
        out = _run(tmp_path, env_extra={"SAML_SUBJECT_SOURCE": source})
        assert "SAML_SUBJECT_SOURCE" in _failed(out), (source, out)


# ── §4-B 이름·부서 대체 사슬 ────────────────────────────────────────────────────────────────
SEED = [{"email": "koo.park@example.com", "name": "박구", "department": "옛 표기 부서", "affiliation": "CAEG"}]


@needs_keys
def test_이름_Claim_이_없으면_원장_이름이_나온다(tmp_path):
    out = _run(tmp_path, seed=SEED)
    assert out["me"]["display_name"] == "박구", out["me"]


@needs_keys
def test_원장에도_없는_새_사용자는_이메일이_이름이다_그리고_원장_이름은_비워_둔다(tmp_path):
    """원장에 이메일을 이름으로 박으면 나중에 Claim 이 와도 영구히 안 고쳐진다(§4-B-3) — 비워 두고 읽을 때 대체한다."""
    out = _run(tmp_path)
    assert out["me"]["display_name"] == "koo.park@example.com", out["me"]
    assert out["row"]["name"] == "", out["row"]


@needs_keys
def test_이름_Claim_이_오면_그것이_이긴다_원장은_보존한다(tmp_path):
    out = _run(tmp_path, seed=SEED, extra={"DisplayName": "Park Koo"},
               env_extra={"SAML_ATTR_NAME": CLAIM + "DisplayName"})
    assert out["me"]["display_name"] == "Park Koo", out["me"]
    assert out["row"]["name"] == "박구", "사람이 적은 원장 이름은 IdP 값으로 덮지 않는다"


@needs_keys
def test_부서_Claim_은_원장_부서를_덮고_소속은_건드리지_않는다(tmp_path):
    """§4-B-4 — 부서는 표시용이라 IdP 값으로 덮는다. 소속(affiliation)은 권한 입력이라 IdP 가 건드리면 CAEG 가 기본 권한으로 떨어진다."""
    out = _run(tmp_path, seed=SEED, extra={"DeptName": "재료시험팀"},
               env_extra={"SAML_ATTR_DEPARTMENT": CLAIM + "DeptName"})
    assert out["me"]["department"] == "재료시험팀", out["me"]
    assert out["row"]["affiliation"] == "CAEG" and out["me"]["affiliation"] == "CAEG", out
    assert out["row"]["status"] == "active" and out["row"]["groups"] == ["portal-admin"], out["row"]


@needs_keys
def test_지정한_Claim_이_없으면_첫_로그인에_경고를_남긴다_값은_안_남긴다(tmp_path):
    """§4-B-5 — 이름 Claim 이 릴리즈됐는데 대소문자·형식이 어긋나면 대체 사슬이 조용히 원장으로 떨어진다. 이름만 적고 값은 안 적는다."""
    out = _run(tmp_path, mail="secret.value@example.com", env_extra={
        "SAML_ATTR_NAME": "displayName", "SAML_ATTR_DEPARTMENT": CLAIM + "DeptName"})
    assert out["status"] in (302, 303), out
    err = out["stderr"]
    assert "SAML_ATTR_NAME='displayName'" in err and "SAML_ATTR_DEPARTMENT=" in err, err[-1500:]
    assert CLAIM + "Mail" in err, "받은 Claim 이름 목록이 있어야 .env 를 확정할 수 있다"
    assert "secret.value" not in err, "Claim 값(개인정보)은 로그에 안 남긴다"


# ── 10차 §7 부서 코드는 제 칸에 ─────────────────────────────────────────────────────────────
@needs_keys
def test_부서_코드_Claim_은_dept_id_칸에만_적고_직접_적은_부서명은_그대로다(tmp_path):
    """운영 ADFS 의 부서 Claim 은 코드(DeptId) 하나뿐이다. 그것을 SAML_ATTR_DEPARTMENT 로 받으면 사람이 적은 부서명이 로그인하는 순간
    코드로 바뀐다 — 코드는 SAML_ATTR_DEPT_ID 로 따로 받는다. 권한 칸은 이쪽도 안 건드린다."""
    out = _run(tmp_path, seed=SEED, env_extra={"SAML_ATTR_DEPT_ID": CLAIM + "DeptId"})
    assert out["row"]["dept_id"] == "D2001" and out["row"]["department"] == "옛 표기 부서", out["row"]
    assert out["me"]["department"] == "옛 표기 부서", out["me"]
    assert out["row"]["affiliation"] == "CAEG" and out["row"]["groups"] == ["portal-admin"], out["row"]


@needs_keys
def test_부서_코드_Claim_이름이_어긋나면_적지_않고_경고를_남긴다(tmp_path):
    """켰는데 이름이 틀리면 칸이 조용히 비어 있다 — 이름·부서 Claim 과 같은 한 줄을 남긴다(§4-B-5 와 같은 자리)."""
    out = _run(tmp_path, env_extra={"SAML_ATTR_DEPT_ID": CLAIM + "DeptCode"})
    assert out["status"] in (302, 303) and out["row"]["dept_id"] == "", out
    assert "SAML_ATTR_DEPT_ID=" in out["stderr"] and CLAIM + "DeptId" in out["stderr"], out["stderr"][-1500:]
    assert "D2001" not in out["stderr"], "Claim 값은 로그에 안 남긴다"


# ── 10차 §6 정지를 사번으로도 ───────────────────────────────────────────────────────────────
# 정지된 사람의 옛 행 — 다른 Mail 로 가입돼 있고, 전에 SSO 로 들어와 사번(운영 모양 Assertion 의 Sabun)이 적혀 있다.
SUSPENDED = [{"email": "k.park.old@example.com", "name": "박 구", "sabun": "1234567", "disabled": True}]


@needs_keys
def test_정지된_사람이_다른_Mail_로_오면_서명된_Assertion_이어도_거절한다(tmp_path):
    """끝까지 — 서명·시간·Audience 를 다 통과한 Assertion 이다. 정지는 이메일 행만 봐서 Mail 이 다르면 active 새 행이 생겼다."""
    out = _run(tmp_path, seed=SUSPENDED, env_extra={"SAML_ATTR_SABUN": CLAIM + "Sabun"})
    assert "정지" in _failed(out), out
    assert "me" not in out and "1234567" not in out["stderr"], "사번 값은 로그에 안 남긴다"


@needs_keys
def test_사번을_안_받는_박스는_종전대로_들어온다(tmp_path):
    """기본은 꺼짐이다 — 같은 원장·같은 Assertion 인데 SAML_ATTR_SABUN 이 없으면 사번을 보지 않는다(위 시험의 대조군)."""
    out = _run(tmp_path, seed=SUSPENDED)
    assert out["status"] in (302, 303) and out["me_status"] == 200 and out["me"]["email"] == "koo.park@example.com", out


@needs_keys
def test_사번_Claim_이름이_어긋나면_경고를_남긴다(tmp_path):
    """켰는데 이름이 틀리면 사번 검사가 한 번도 돌지 않는다 — 켜 둔 줄 아는 동안 정지된 사람이 그대로 들어온다."""
    out = _run(tmp_path, seed=SUSPENDED, env_extra={"SAML_ATTR_SABUN": CLAIM + "EmpNo"})
    assert out["status"] in (302, 303) and out["me_status"] == 200, out
    assert "SAML_ATTR_SABUN=" in out["stderr"] and CLAIM + "Sabun" in out["stderr"], out["stderr"][-1500:]
    assert "1234567" not in out["stderr"], "Claim 값은 로그에 안 남긴다"


# ── 10차 §2 SSO 로 처음 생기는 사람의 소속 ──────────────────────────────────────────────────
def _access(d: Path, *rows: str) -> dict:
    """추적된 권한 표의 사본 + 박스 파일(Claim → 소속 표)을 임시 폴더에 두고 ACCESS_PATH 로 가리킨다 — 리포의 config 는 안 건드린다."""
    d.mkdir(parents=True)
    (d / "access.yaml").write_text((BACKEND / "config" / "access.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    (d / "access.local.yaml").write_text("sso_affiliation_map:\n" + "".join(f"  - {r}\n" for r in rows), encoding="utf-8")
    return {"ACCESS_PATH": str(d / "access.yaml")}


@needs_keys
def test_운영_모양_Assertion_의_Claim_으로_새_사용자의_소속이_정해진다(tmp_path):
    """운영 ADFS 는 Claim 이름을 전체 URI 로 준다 — 박스 파일에 짧은 이름(CompId)으로 적은 표가 **진짜 서명된 Assertion** 에서
    맞는지 끝까지 본다. 소속이 들어가면 그 사람은 첫 요청부터 그 소속의 권한이고, 접속 원장에 포털이 넣었다는 흔적이 남는다."""
    out = _run(tmp_path, env_extra=_access(tmp_path / "acc", '{claim: CompId, value: "C100", affiliation: CAEG}'))
    assert out["status"] in (302, 303), out
    assert out["row"]["affiliation"] == "CAEG" and out["me"]["affiliation"] == "CAEG", out
    assert out["row"]["groups"] == [] and out["row"]["grants"] == [] and out["row"]["status"] == "active", out["row"]
    assert "feat:deliberation" in out["me"]["entitlements"], out["me"]
    assert out["login_detail"] == "sso:aff:map:CAEG", out["login_detail"]
    assert "C100" not in out["stderr"], "Claim 값(회사 코드)은 로그에 안 남긴다"


@needs_keys
def test_표가_안_맞는_새_사용자는_소속_없이_생긴다(tmp_path):
    out = _run(tmp_path, env_extra=_access(tmp_path / "acc", '{claim: CompId, value: "C999", affiliation: CAEG}',
                                           '{claim: "' + CLAIM + 'DeptId", value: "D2001 x", affiliation: CAEG}'))
    assert out["row"]["affiliation"] == "" and out["me"]["affiliation"] == "", out
    assert out["me"]["entitlements"] == ["feat:chat"] and out["login_detail"] == "sso", out


@needs_keys
def test_이미_있는_사람은_표가_맞아도_기본_소속이_있어도_그대로다(tmp_path):
    """D-2 — 최초 INSERT 때만이다. 소속이 빈 기존 행을 로그인 때 채우면 관리자가 일부러 비운 사람이 되살아나고, 승인 대기 행
    (남의 이메일로도 만들 수 있다)이 SSO 로그인으로 소속을 얻는다."""
    env = {**_access(tmp_path / "acc", '{claim: CompId, value: "C100", affiliation: CAEG}'), "SSO_DEFAULT_AFFILIATION": "CAEG"}
    old = _run(tmp_path / "old", seed=[{"email": "koo.park@example.com", "name": "박구"}], env_extra=env)
    assert old["row"]["affiliation"] == "" and old["login_detail"] == "sso", old
    wait = _run(tmp_path / "wait", seed=[{"email": "koo.park@example.com", "name": "가입 대기", "pending": True}], env_extra=env)
    assert wait["row"]["affiliation"] == "" and wait["row"]["status"] == "pending", wait["row"]
    assert wait["me"]["entitlements"] == ["feat:chat"], wait["me"]
    # 같은 설정에서 원장에 없던 사람은 받는다 — 위 둘이 '설정이 안 먹어서' 통과한 것이 아니다
    new = _run(tmp_path / "new", mail="new.person@example.com", env_extra=env)
    assert new["row"]["affiliation"] == "CAEG", new["row"]


# ── 검토 2차 ───────────────────────────────────────────────────────────────────────────────
@needs_keys
def test_승인_안_된_가입_행의_이름은_대체_사슬에_안_쓴다(tmp_path):
    """비로그인 가입은 남의 이메일로도 된다(승인 대기). 그 행의 이름이 진짜 주인의 SSO 세션·서명된 하위 토큰·PAT 에 실리면 안 된다."""
    out = _run(tmp_path, seed=[{"email": "koo.park@example.com", "name": "가로챈 이름", "pending": True}])
    assert out["status"] in (302, 303), out
    assert out["me"]["display_name"] == "koo.park@example.com", out["me"]


@needs_keys
def test_Mail_Claim_이_없으면_NameID_로_몰래_떨어지지_않고_거절한다(tmp_path):
    """IdP 가 NameID 를 켠 날 SAML_ATTR_EMAIL 이 어긋나 있으면(짧은 이름·URI 변경) 종전엔 subject·원장 키가 NameID 가 됐다."""
    out = _run(tmp_path, nameid="kpark01", env_extra={"SAML_ATTR_EMAIL": "Mail"})
    detail = _failed(out)
    assert "SAML_ATTR_EMAIL" in detail and CLAIM + "Mail" in detail, out
    assert "koo.park@example.com" not in out["location"], "Claim 값은 리다이렉트 주소에 안 싣는다"



# ── 7차 — 요청에서 NameID 형식을 요구하지 않는다 · 없는 SLO 를 광고하지 않는다 ───────────────────────
def _req_fields(xml: str) -> dict:
    import re
    return {k: (re.search(rf'{k}="([^"]+)"', xml) or [None, None])[1] for k in ("Destination", "AssertionConsumerServiceURL")} | \
        {"Issuer": (re.search(r"<saml:Issuer>([^<]+)</saml:Issuer>", xml) or [None, None])[1]}


@needs_keys
def test_기본값은_종전_그대로_NameIDPolicy_를_싣고_SLO_를_광고한다(tmp_path):
    out = _run(tmp_path)
    assert "NameIDPolicy" in out["authn"], out["authn"]
    assert out["md_status"] == 200 and out["md"].count("SingleLogoutService") == 1, out["md"]


@needs_keys
def test_NameIDPolicy_를_끄면_그_요소만_빠지고_로그인된다(tmp_path):
    """운영 ADFS 는 형식을 요구하면 **인증을 통과한 뒤** InvalidNameIDPolicy 로 거절한다(2026-10-02 실측). 플래그는 그 요소만 지워야
    한다 — Destination·ACS·Issuer 가 같아야 진단 앱(성공한 정답지)과 같은 모양이다."""
    on = _run(tmp_path / "on")
    off = _run(tmp_path / "off", env_extra={"SAML_SEND_NAMEID_POLICY": "false"})
    assert "NameIDPolicy" not in off["authn"], off["authn"]
    assert _req_fields(off["authn"]) == _req_fields(on["authn"]) and all(_req_fields(on["authn"]).values()), \
        (_req_fields(on["authn"]), _req_fields(off["authn"]))
    assert off["status"] in (302, 303) and off["me"]["email"] == "koo.park@example.com", off


@needs_keys
def test_SLO_광고를_끄면_메타데이터에서_빠지고_메타데이터는_유효하다(tmp_path):
    """미구현 SLO(/auth/saml/sls 는 501)를 광고하면 다른 RP 의 전역 로그아웃이 포털에서 조용히 실패한다 — 사용자는 로그아웃했다고 믿는다."""
    out = _run(tmp_path, env_extra={"SAML_ADVERTISE_SLO": "false"})
    assert out["md_status"] == 200 and "SingleLogoutService" not in out["md"], out["md"]
    assert "AssertionConsumerService" in out["md"]
    assert out["status"] in (302, 303), "SLO 블록이 없어도 로그인 검증은 그대로다"



# ── SSO 실패 화면 — 흰 JSON 원문 대신 로그인 화면(docs/ui-refresh 단계 4 · D-11) ─────────────────────
@needs_keys
def test_SSO_실패는_로그인_화면으로_돌아가고_원인은_서버_로그에도_남는다(tmp_path):
    """원인(예: InvalidNameIDPolicy)은 운영 진단의 단서다 — 화면 '자세히' 와 WARNING 로그(포털은 INFO 를 버린다) 둘 다에 남는다."""
    out = _run(tmp_path, want_nameid=None)
    detail = _failed(out)
    assert out["location"].startswith("http://localhost:5283/login?"), out["location"]
    assert "SSO 콜백 실패" in out["stderr"] and detail[:40] in out["stderr"], out["stderr"][-1500:]
