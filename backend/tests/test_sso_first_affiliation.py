# SSO 로 처음 생기는 사람의 소속 — Claim 매핑이 먼저, 안 맞으면 기본 소속, 그리고 **최초 INSERT 때만**(10차 요청 §2)
"""SSO 로 처음 들어온 사람은 소속 없이 생겨 기본 권한(일반 챗)만 받았고, 관리자가 한 사람씩 찾아 지정할 때까지 막혀 있었다
(2026-10-07 실측: 소속 공란 16명, 그중 7명이 이미 거부를 겪음). 그래서 처음 생길 때 Claim 으로 소속을 정한다.

여기서 고정하는 것은 **언제 넣지 않는가**다. 소속은 권한 입력이다 —
  · 이미 있는 행은 로그인해도 안 건드린다. 관리자가 일부러 비워 둔 사람을 다시 채우면 회수가 무효가 된다.
  · 표에 없는 소속은 넣지 않는다. 그리고 그 사실이 관리자에게 보인다(조용히 버리면 그 사람은 다시 '막힌 16명' 이 된다).
  · 이메일 로컬 계정 경로는 이 값을 받는 자리가 없다. 사람이 고를 수 있는 값이 소속이 되면 스스로 올린다.

원장·권한 표는 전부 임시 폴더에 만든다. 코드·소속·주소는 지어낸 값이다.
"""
import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

import app.main as main
from app.access.policy import AccessPolicy, claim_values, compute, sso_default_problems
from app.auth.provider import Principal
from app.auth.routes.session import complete_login
from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.main import app
from app.setup_requests import check_notes, parse_requests, run_check

_BACKEND = Path(__file__).resolve().parents[1]
CLAIM = "http://idp.example/claims/"
PC = ("203.0.113.5", 50000)

BASE = """
default_grants: [feat:chat]
affiliations:
  - {id: CAEG, label: CAE그룹, grants: ["*"]}
  - {id: LAB, label: 시험실, grants: [plat:alpha]}
features:
  - {id: chat, label: 일반 챗}
platforms:
  - {id: alpha, label: Alpha, gateway: [alpha]}
"""


class _Box:
    def __init__(self, tmp_path):
        self.dir = tmp_path
        (tmp_path / "access.yaml").write_text(BASE, encoding="utf-8")
        self.settings = Settings(_env_file=None, user_store_path=str(tmp_path / "u.sqlite"),
                                 access_path=str(tmp_path / "access.yaml"), local_bootstrap_admins="boss@corp.com")
        self.store = UserStore(self.settings)
        self.access = AccessPolicy(self.settings)

    def map(self, *rows: str) -> None:
        """박스 파일(access.local.yaml)에 Claim → 소속 표를 쓴다. 새 AccessPolicy 로 바꿔 mtime 캐시와 무관하게 읽힌다."""
        (self.dir / "access.local.yaml").write_text(
            "sso_affiliation_map:\n" + "".join(f"  - {r}\n" for r in rows), encoding="utf-8")
        self.access = app.state.access = AccessPolicy(self.settings)

    def sso(self, email: str, attrs: dict | None = None, *, request: bool = True, **over) -> dict:
        """SSO 콜백의 IdP 무관 뒷부분을 실제로 돌린다 — 원시 Claim 은 여기서만 살아 있다."""
        req = Request({"type": "http", "method": "POST", "path": "/auth/callback", "headers": [], "query_string": b"",
                       "app": app, "client": PC}) if request else None
        complete_login(principal=Principal(subject=email, email=email, display_name=None, groups=[],
                                           attributes=attrs or {}),
                       expected_state=None, settings=self.settings.model_copy(update=over),
                       jwt_service=app.state.jwt_service, user_store=self.store, request=req)
        return self.store.get(email)

    def last_login(self, email: str) -> dict:
        return app.state.agent_audit.query_access(since=0, include_auto=True, email=email, event="login")[0]


@pytest.fixture()
def box(tmp_path, monkeypatch):
    monkeypatch.delenv("SSO_DEFAULT_AFFILIATION", raising=False)
    from app.auth.routes.local import _rl
    _rl.clear()
    with TestClient(app) as c:
        keep = (app.state.access, app.state.user_store)
        b = _Box(tmp_path)
        b.client = c
        app.state.access, app.state.user_store = b.access, b.store       # 기동 뒤 교체 — 실 원장·실 권한 표를 안 쓴다
        app.dependency_overrides[get_settings] = lambda: b.settings      # 라우트도 이 박스의 설정으로
        yield b
        app.dependency_overrides.pop(get_settings, None)
        app.state.access, app.state.user_store = keep


COMP = {CLAIM + "CompId": ["C999"], CLAIM + "DeptId": ["D12345"], CLAIM + "Mail": ["new@corp.com"]}


# ── 기본은 꺼짐 ──────────────────────────────────────────────────────────────
def test_설정이_없으면_종전대로_소속_없이_생긴다(box):
    assert box.settings.sso_default_affiliation == ""
    u = box.sso("new@corp.com", COMP)
    assert (u["affiliation"], u["status"], u["auth_source"], u["groups"], u["grants"]) == ("", "active", "sso", [], [])
    assert compute(box.access.get(), groups=[], row=u).keys == {"feat:chat"}
    assert box.last_login("new@corp.com")["detail"] == "sso", "넣은 것이 없으면 원장 표기도 종전 그대로"


# ── ⓑ Claim → 소속 ───────────────────────────────────────────────────────────
def test_매핑이_맞으면_처음_생길_때_그_소속이고_흔적이_남는다(box, caplog):
    box.map('{claim: CompId, value: "C999", affiliation: LAB}')
    with caplog.at_level(logging.WARNING):
        u = box.sso("new@corp.com", COMP)
    assert u["affiliation"] == "LAB" and u["status"] == "active" and u["groups"] == [] and u["grants"] == []
    assert compute(box.access.get(), groups=[], row=u).keys == {"feat:chat", "plat:alpha"}
    # 흔적 둘 — 접속 원장(관리자 '접속 이력')과 WARNING 로그(포털은 INFO 를 버린다). Claim 값은 어디에도 안 남긴다.
    assert box.last_login("new@corp.com")["detail"] == "sso:aff:map:LAB"
    said = [r.getMessage() for r in caplog.records if "new@corp.com" in r.getMessage()]
    assert said and "LAB" in said[0] and "CompId" in said[0], said
    assert not any("C999" in r.getMessage() for r in caplog.records)


def test_Claim_은_전체_이름으로도_짧은_이름으로도_적을_수_있다(box):
    box.map('{claim: "' + CLAIM + 'DeptId", value: "D12345", affiliation: LAB}')
    assert box.sso("full@corp.com", COMP)["affiliation"] == "LAB"
    box.map('{claim: DeptId, value: "D12345", affiliation: LAB}')
    assert box.sso("short@corp.com", COMP)["affiliation"] == "LAB"


def test_값은_앞뒤_공백만_떼고_글자_그대로_견준다(box):
    box.map('{claim: CompId, value: " C999 ", affiliation: LAB}')
    assert box.sso("a@corp.com", {CLAIM + "CompId": ["  C999 "]})["affiliation"] == "LAB"
    for n, near in enumerate(("C9990", "c999", "XC999", "C99", "")):
        assert box.sso(f"near{n}@corp.com", {CLAIM + "CompId": [near]})["affiliation"] == "", near
    assert box.sso("multi@corp.com", {CLAIM + "CompId": ["C100", "C999"]})["affiliation"] == "LAB", "여러 값 중 하나"


def test_위에서부터_처음_맞는_행이_이긴다(box):
    box.map('{claim: DeptId, value: "D12345", affiliation: LAB}', '{claim: CompId, value: "C999", affiliation: CAEG}')
    assert box.sso("a@corp.com", COMP)["affiliation"] == "LAB"
    box.map('{claim: CompId, value: "C999", affiliation: CAEG}', '{claim: DeptId, value: "D12345", affiliation: LAB}')
    assert box.sso("b@corp.com", COMP)["affiliation"] == "CAEG"


def test_짧은_이름은_마지막_조각이_통째로_같을_때만_맞는다(box):
    box.map('{claim: Id, value: "C999", affiliation: LAB}', '{claim: mpId, value: "C999", affiliation: LAB}')
    # 속성이 하나뿐이라 '모호해서' 빠지는 것이 아니다 — 끝 글자만 같은 이름은 애초에 맞지 않아야 한다
    assert box.sso("a@corp.com", {CLAIM + "CompId": ["C999"]})["affiliation"] == "", "'Id' 가 '…/CompId' 에 걸리면 안 된다"
    assert claim_values({"CompId": ["x"]}, "CompId") == ["x"], "IdP 가 짧은 이름 그대로 주면 정확한 키다"
    assert claim_values({CLAIM + "CompId": ["x"]}, CLAIM + "Nope") == []
    assert claim_values({"urn:x:CompId": ["x"]}, "CompId") == [], "URN 은 경로가 아니다 — 전체 이름으로만"


def test_짧은_이름이_두_속성에_걸리면_고르지_않는다(box, caplog):
    """다른 네임스페이스의 같은 이름이 소속을 정하면 안 된다 — 모호하면 안 넣고, 전체 이름으로 적으라고 남긴다."""
    two = {CLAIM + "CompId": ["C999"], "http://other.example/claims/CompId": ["C000"]}
    box.map('{claim: CompId, value: "C999", affiliation: LAB}')
    with caplog.at_level(logging.WARNING):
        assert box.sso("a@corp.com", two)["affiliation"] == ""
    assert any("CompId" in r.getMessage() and "둘 이상" in r.getMessage() for r in caplog.records)
    assert not any("C999" in r.getMessage() or "C000" in r.getMessage() for r in caplog.records)
    box.map('{claim: "' + CLAIM + 'CompId", value: "C999", affiliation: LAB}')
    assert box.sso("b@corp.com", two)["affiliation"] == "LAB", "전체 이름은 모호할 수 없다"


# ── ⓐ 기본 소속(매핑이 안 맞을 때만) ─────────────────────────────────────────
def test_매핑이_안_맞으면_기본_소속이고_맞으면_매핑이_이긴다(box):
    box.map('{claim: CompId, value: "C999", affiliation: CAEG}')
    miss = box.sso("miss@corp.com", {CLAIM + "CompId": ["C100"]}, sso_default_affiliation="LAB")
    assert miss["affiliation"] == "LAB" and box.last_login("miss@corp.com")["detail"] == "sso:aff:default:LAB"
    hit = box.sso("hit@corp.com", COMP, sso_default_affiliation="LAB")
    assert hit["affiliation"] == "CAEG" and box.last_login("hit@corp.com")["detail"] == "sso:aff:map:CAEG"


def test_표가_없어도_기본_소속만으로_돈다(box):
    assert box.sso("a@corp.com", {}, sso_default_affiliation=" LAB ")["affiliation"] == "LAB"


# ── 표에 없는 소속은 넣지 않고, 보인다 ───────────────────────────────────────
@pytest.mark.anyio
async def test_매핑의_모르는_소속은_적용하지_않고_관리자에게_보인다(box):
    box.map('{claim: CompId, value: "C999", affiliation: NOPE}')
    assert box.sso("a@corp.com", COMP)["affiliation"] == ""
    assert any("1번째" in p and "NOPE" in p for p in box.access.problems())
    assert await run_check("access_overlay", box.settings, box.access) == "todo"


@pytest.mark.anyio
async def test_기본_소속이_모르는_값이면_적용하지_않고_관리자에게_보인다(box, caplog):
    s = box.settings.model_copy(update={"sso_default_affiliation": "NOPE"})
    with caplog.at_level(logging.WARNING):
        u = box.sso("a@corp.com", COMP, sso_default_affiliation="NOPE")
    assert u["affiliation"] == "" and box.last_login("a@corp.com")["detail"] == "sso"
    assert any("SSO_DEFAULT_AFFILIATION" in r.getMessage() and "NOPE" in r.getMessage() for r in caplog.records)
    assert await run_check("sso_default_affiliation", s, box.access) == "todo"
    (note,) = check_notes("sso_default_affiliation", s, box.access)
    assert "NOPE" in note and "affiliations" in note


@pytest.mark.anyio
async def test_전권_소속을_기본으로_주면_막지는_않되_크게_경고한다(box):
    """grants 가 '*' 인 소속을 기본으로 주면 ADFS 를 통과한 누구나 처음 로그인하는 순간 전권이다 — 운영자의 결정이라 막지 않는다."""
    s = box.settings.model_copy(update={"sso_default_affiliation": "CAEG"})
    assert box.sso("a@corp.com", {}, sso_default_affiliation="CAEG")["affiliation"] == "CAEG", "막지는 않는다"
    assert [code for code, _ in sso_default_problems(box.access.get(), "CAEG")] == ["wildcard"]
    assert await run_check("sso_default_affiliation", s, box.access) == "todo"
    (note,) = check_notes("sso_default_affiliation", s, box.access)
    assert "CAEG" in note and "전권" in note
    # 전권이 아닌 소속·꺼짐은 조용하다
    for quiet in ("LAB", "", "  "):
        assert sso_default_problems(box.access.get(), quiet) == []
        assert await run_check("sso_default_affiliation", box.settings.model_copy(
            update={"sso_default_affiliation": quiet}), box.access) == "ok"
    assert await run_check("sso_default_affiliation", s, None) == "unknown", "모르면 모른다고 한다"


@pytest.mark.parametrize(("value", "level", "word"), [("CAEG", logging.CRITICAL, "전권"), ("NOPE", logging.WARNING, "NOPE")])
def test_기동_때도_경고한다(monkeypatch, caplog, value, level, word):
    """추적된 access.yaml 로 실제 기동을 돌린다 — CAEG 의 grants 가 '*' 다."""
    monkeypatch.setattr(main.settings, "sso_default_affiliation", value)
    with caplog.at_level(logging.WARNING), TestClient(app):
        pass
    hits = [r for r in caplog.records if "SSO_DEFAULT_AFFILIATION" in r.getMessage()]
    assert hits and hits[0].levelno == level and word in hits[0].getMessage(), [r.getMessage() for r in hits]


def test_기동_때_설정이_없으면_조용하다(monkeypatch, caplog):
    monkeypatch.setattr(main.settings, "sso_default_affiliation", "")
    with caplog.at_level(logging.WARNING), TestClient(app):
        pass
    assert not [r for r in caplog.records if "SSO_DEFAULT_AFFILIATION" in r.getMessage()]


def test_추적된_배선_목록에_기본_소속_확인이_있다():
    import yaml
    doc = yaml.safe_load((_BACKEND / "config" / "setup_requests.yaml").read_text("utf-8"))
    (row,) = [r for r in parse_requests(doc) if r["check"] == "sso_default_affiliation"]
    assert "SSO_DEFAULT_AFFILIATION" in row["body"] and not row["manual"]


# ── 이미 있는 행은 안 건드린다 ───────────────────────────────────────────────
def test_소속이_빈_기존_행은_다음_로그인에_채우지_않는다(box):
    """D-2 — 로그인 때마다 빈 소속을 채우면 관리자가 일부러 비워 둔 사람이 다시 채워진다. 기존 사람은 관리자가 지정한다."""
    assert box.sso("old@corp.com", COMP)["affiliation"] == ""          # 표가 없던 때 생긴 사람
    box.map('{claim: CompId, value: "C999", affiliation: CAEG}')
    again = box.sso("old@corp.com", COMP, sso_default_affiliation="LAB")
    assert again["affiliation"] == "" and box.last_login("old@corp.com")["detail"] == "sso"


def test_이미_있는_사람의_로그인은_소속을_계산하지도_않는다(box, caplog):
    """있던 행에는 어차피 안 쓴다 — 계산만 해도 '적용하지 않았다' 경고가 로그인마다 쌓여 진짜 경고가 묻힌다."""
    two = {CLAIM + "CompId": ["C999"], "http://other.example/claims/CompId": ["C000"]}
    box.map('{claim: CompId, value: "C999", affiliation: LAB}')
    box.sso("old@corp.com", {})
    with caplog.at_level(logging.WARNING):
        assert box.sso("old@corp.com", two, sso_default_affiliation="NOPE")["affiliation"] == ""
    assert not [r.getMessage() for r in caplog.records
                if "SSO_DEFAULT_AFFILIATION" in r.getMessage() or "소속" in r.getMessage()]


def test_관리자가_정한_소속은_그대로다_비운_것도(box):
    box.map('{claim: CompId, value: "C999", affiliation: CAEG}')
    assert box.sso("a@corp.com", COMP)["affiliation"] == "CAEG"
    box.store.set_access("a@corp.com", affiliation="LAB")                # 관리자가 바꿨다
    assert box.sso("a@corp.com", COMP, sso_default_affiliation="CAEG")["affiliation"] == "LAB"
    box.store.set_access("a@corp.com", affiliation="")                   # 관리자가 거뒀다
    assert box.sso("a@corp.com", COMP, sso_default_affiliation="CAEG")["affiliation"] == ""


def test_승인_대기는_승인_대기로_남고_소속도_안_받는다(box):
    """비로그인 가입은 남의 이메일로도 된다 — 그 행이 SSO 로그인으로 활성·소속을 얻으면 가입 승인이 무력해진다."""
    box.map('{claim: CompId, value: "C999", affiliation: CAEG}')
    box.store.signup(email="wait@corp.com", name="대기", password="pw123456", bootstrap_admins=[])
    u = box.sso("wait@corp.com", COMP, sso_default_affiliation="LAB")
    assert (u["status"], u["affiliation"], u["groups"], u["grants"]) == ("pending", "", [], [])


def test_정지된_사람은_정지된_채다(box):
    box.map('{claim: CompId, value: "C999", affiliation: CAEG}')
    box.sso("off@corp.com", {})
    box.store.set_status("off@corp.com", "disabled")
    u = box.sso("off@corp.com", COMP, sso_default_affiliation="LAB")
    assert (u["status"], u["affiliation"]) == ("disabled", "")


# ── 이메일 로컬 계정 경로는 받는 자리가 없다 ─────────────────────────────────
def test_로컬_가입과_로컬_로그인은_소속을_받지_않는다(box):
    box.map('{claim: provider, value: "local", affiliation: CAEG}')       # 로컬 로그인이 싣는 속성까지 겨냥해도
    box.settings = box.settings.model_copy(update={"sso_default_affiliation": "CAEG"})
    c = box.client
    # 가입 본문에 소속·부서를 실어 보내도 받는 칸이 없다
    c.post("/auth/local/signup", json={"email": "boss@corp.com", "name": "B", "password": "pw123456",
                                       "affiliation": "CAEG"})
    assert c.post("/auth/local/login", json={"email": "boss@corp.com", "password": "pw123456"}).status_code == 200
    h = {"X-CSRF-Token": c.cookies.get("hwax_csrf")}
    c.post("/auth/local/signup", json={"email": "user@corp.com", "name": "U", "password": "pw123456",
                                       "affiliation": "CAEG", "department": "CAEG"})
    assert c.post("/auth/local/users/user@corp.com/approve", json={"groups": []}, headers=h).status_code == 200
    assert c.post("/auth/local/login", json={"email": "user@corp.com", "password": "pw123456"}).status_code == 200
    assert c.get("/auth/me").json()["affiliation"] == ""
    assert box.store.get("user@corp.com")["affiliation"] == "" and box.store.get("boss@corp.com")["affiliation"] == ""
    # 그 로컬 계정이 나중에 SSO 로 들어와도 이미 있는 행이다
    assert box.sso("user@corp.com", COMP, sso_default_affiliation="CAEG")["affiliation"] == ""


# ── 원장 층 ──────────────────────────────────────────────────────────────────
def test_원장은_새_행에만_소속을_쓰고_만들었는지_돌려준다(box):
    assert box.store.note_sso_login(email="A@Corp.com", name=None, affiliation=" LAB ") is True
    assert box.store.get("a@corp.com")["affiliation"] == "LAB"
    assert box.store.note_sso_login(email="a@corp.com", name=None, affiliation="CAEG") is False
    assert box.store.get("a@corp.com")["affiliation"] == "LAB"
    assert box.store.note_sso_login(email="b@corp.com", name=None) is True
    assert box.store.get("b@corp.com")["affiliation"] == ""


def test_원장_쓰기가_실패해도_로그인은_되고_경고가_남는다(box, monkeypatch, caplog):
    """원장은 부기록이다. 다만 조용히 삼키면 새 사람이 행 없이(소속도 없이) 들어오고 관리자 목록에도 안 보인다 — 칸 추가가 실패한
    원장에서는 이 쓰기가 로그인마다 실패한다."""
    box.map('{claim: CompId, value: "C999", affiliation: LAB}')

    def boom(**_kw):
        raise RuntimeError("table users has no column named dept_id")
    monkeypatch.setattr(box.store, "note_sso_login", boom)
    with caplog.at_level(logging.WARNING):
        assert box.sso("a@corp.com", COMP) is None, "행은 안 생겼다"
    assert any("원장 기록 실패" in r.getMessage() and "a@corp.com" in r.getMessage() for r in caplog.records)
    assert box.last_login("a@corp.com")["detail"] == "sso", "넣지 못한 소속을 넣었다고 적지 않는다"


def test_요청_없이_부른_옛_호출부는_소속_없이_만든다(box):
    """권한 표를 못 읽는 자리에서는 넣지 않는다 — 검증 못 한 소속을 원장에 쓰지 않는다."""
    box.map('{claim: CompId, value: "C999", affiliation: CAEG}')
    assert box.sso("a@corp.com", COMP, request=False, sso_default_affiliation="LAB")["affiliation"] == ""


# ── ⓒ 관리자가 판단할 재료 ───────────────────────────────────────────────────
def test_사용자_목록_API_가_생성_시각과_로그인_수단을_준다(box):
    c = box.client
    c.post("/auth/local/signup", json={"email": "boss@corp.com", "name": "B", "password": "pw123456"})
    assert c.post("/auth/local/login", json={"email": "boss@corp.com", "password": "pw123456"}).status_code == 200
    box.sso("sso@corp.com", COMP)
    rows = {u["email"]: u for u in c.get("/auth/local/users").json()}
    sso = rows["sso@corp.com"]
    assert sso["auth_source"] == "sso" and sso["affiliation"] == "" and sso["status"] == "active"
    assert isinstance(sso["created_at"], int) and sso["created_at"] > 1_700_000_000
    assert rows["boss@corp.com"]["auth_source"] == "local"
