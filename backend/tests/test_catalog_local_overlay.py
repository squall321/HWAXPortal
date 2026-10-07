# 외부 타일의 사내 주소는 추적 파일(systems.yaml)이 아니라 박스별 덮어쓰기(systems.local.yaml, gitignore)에서 온다 — 박스에만 있는 새 외부 타일도 거기서 만든다
#
# 주소는 문서용 예약 대역(TEST-NET)만 쓴다 — 이 리포는 GitHub 에 있다.
import logging
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.access.policy import AccessPolicy, load_raw, parse_policy
from app.auth.user_store import UserStore
from app.catalog.registry import CatalogRegistry
from app.config import Settings, get_settings
from app.main import app

_CONFIG = Path(__file__).resolve().parents[1] / "config"


def _catalog(tmp_path, overlay: str | None):
    (tmp_path / "systems.yaml").write_text(
        "systems:\n"
        "  - {id: ext-a, name: A, integration_type: external-url}\n"
        "  - {id: ext-b, name: B, integration_type: external-url, url: 'https://b.example'}\n")
    (tmp_path / "routes.env").write_text("")
    if overlay is not None:
        (tmp_path / "systems.local.yaml").write_text(overlay)
    return CatalogRegistry(Settings(_env_file=None, catalog_path=str(tmp_path / "systems.yaml"),
                                    routes_path=str(tmp_path / "routes.env")))


def test_외부_타일_주소는_박스별_덮어쓰기에서_온다(tmp_path, caplog):
    r = _catalog(tmp_path, "ext-a:\n  url: http://192.0.2.10:3001/\nnope:\n  url: http://x/\n")
    a = {s.id: s for s in r.all()}
    assert (a["ext-a"].url, a["ext-a"].status, a["ext-a"].integration_type) == \
        ("http://192.0.2.10:3001/", "available", "external-url"), "프록시로 승격하지 않는다(직결 링크 그대로)"
    assert a["ext-b"].url == "https://b.example"
    assert any("nope" in rec.getMessage() for rec in caplog.records), "오타난 타일 id 를 조용히 넘기지 않는다"


def test_주소_없는_외부_타일은_곧_공개로_내린다(tmp_path, caplog):
    """두면 화면이 `/<id>/` 로 열어 SPA 로 떨어지고 조용히 깨진다 — 새 박스에서 덮어쓰기를 안 만들었을 때."""
    with caplog.at_level(logging.WARNING):
        a = {s.id: s for s in _catalog(tmp_path, None).all()}
    assert a["ext-a"].status == "coming_soon" and a["ext-b"].status == "available"
    assert any("systems.local.yaml" in rec.getMessage() for rec in caplog.records)


def test_덮어쓰기는_핸드오프_타일의_주소를_못_바꾼다(tmp_path, caplog):
    """핸드오프 url 은 서명된 로그인 토큰을 보내는 곳이다 — 추적되지 않는 파일로 바꾸게 두지 않는다(검토 1차)."""
    (tmp_path / "systems.yaml").write_text(
        "systems:\n  - {id: hub, name: H, integration_type: jwt-handoff, audience: hub, url: /hub/api/cb}\n")
    (tmp_path / "routes.env").write_text("")
    (tmp_path / "systems.local.yaml").write_text("hub:\n  url: https://attacker.example/collect\n")
    r = CatalogRegistry(Settings(_env_file=None, catalog_path=str(tmp_path / "systems.yaml"),
                                 routes_path=str(tmp_path / "routes.env")))
    assert r.all()[0].url == "/hub/api/cb"
    assert any("외부 타일이 아니라 무시" in rec.getMessage() for rec in caplog.records)


def test_포털_재기동_지문에_타일_덮어쓰기가_들어_있다():
    """빠뜨리면 만들어 넣어도 재기동이 생략돼 타일이 '곧 공개' 로 남는다(검토 1차)."""
    src = (Path(__file__).resolve().parents[2] / "infra/scripts/deploy-all-from-drive.sh").read_text()
    line = next(ln for ln in src.splitlines() if "_cur=\"$(_fp_git; hwax_fp" in ln)
    assert "backend/config/systems.local.yaml" in line and "backend/config/routes.local.env" in line


# ── 박스 파일로 새 타일(8차 요청 §4-(3)) ──────────────────────────────────────
# 박스에만 있는 서비스의 바로가기 하나를 붙이려고 추적 파일을 고쳐야 했다(모르는 id 는 경고만 하고 버렸다). external-url 타일에
# 한해 박스 파일이 새로 만든다. 핸드오프 타일은 서명된 로그인 토큰을 보내는 곳이라 만들지 못한다 — 위의 덮어쓰기 금지와 같은 이유다.
_NEW = "box-lab:\n  name: 시험실 장비 예약\n  tagline: 이 박스에만 있는 서비스\n  url: http://192.0.2.30:8080/\n  sort_order: 5\n"


def test_박스_파일로_새_외부_타일을_만든다(tmp_path, caplog):
    with caplog.at_level(logging.WARNING):
        r = _catalog(tmp_path, _NEW)
    t = r.get("box-lab")
    assert t is not None, "name 이 있는 모르는 id 는 새 타일이다"
    assert (t.name, t.url, t.status, t.integration_type, t.enabled) == \
        ("시험실 장비 예약", "http://192.0.2.30:8080/", "available", "external-url", True)
    assert [s.id for s in r.all()] == ["box-lab", "ext-a", "ext-b"], "sort_order 대로 끼어든다"
    assert "box-lab" in r.live_ids()
    assert not [rec for rec in caplog.records if "box-lab" in rec.getMessage()], "멀쩡한 새 타일에는 경고가 없다"


def test_주소만_적은_모르는_id_는_타일이_되지_않는다(tmp_path, caplog):
    """url 한 칸뿐이면 있는 타일의 id 를 잘못 적었을 가능성이 크다 — 타일로 만들면 오타가 이름 없는 카드로 뜬다."""
    with caplog.at_level(logging.WARNING):
        r = _catalog(tmp_path, "ext-aa:\n  url: http://192.0.2.10:3001/\n")
    assert r.get("ext-aa") is None and r.get("ext-a").status == "coming_soon"
    (msg,) = [rec.getMessage() for rec in caplog.records if "ext-aa" in rec.getMessage()]
    assert "오타" in msg and "name" in msg, "오타를 먼저 의심하게 하고, 새 타일을 뜻했다면 무엇을 적어야 하는지 말한다"


# proxy 도 받지 않는다 — 프록시 타일은 routes 파일에 목적지가 있는 박스에서 외부 타일이 승격되어 생긴다(아래 시험).
@pytest.mark.parametrize("kind", ["jwt-handoff", "saml-handoff", "proxy"])
def test_박스_파일로는_외부_타일만_새로_만든다(tmp_path, caplog, kind):
    """핸드오프 타일은 포털이 서명한 로그인 토큰을 그 url 로 보낸다 — 추적되지 않는 파일 한 줄이 새 수신처를 만들면 안 된다."""
    with caplog.at_level(logging.WARNING):
        r = _catalog(tmp_path, f"box-x:\n  name: X\n  integration_type: {kind}\n  audience: ext-b\n"
                               "  url: https://collector.example/cb\n")
    assert r.get("box-x") is None and [s.id for s in r.all()] == ["ext-a", "ext-b"]
    assert any("box-x" in rec.getMessage() and "external-url" in rec.getMessage() for rec in caplog.records), \
        "왜 안 만들어졌는지 말한다"


def test_새_타일의_id_는_박스_파일의_키다(tmp_path):
    """안에 적은 id 로 있는 핸드오프 타일의 자리를 차지하지 못한다 — 같은 id 가 둘이면 어느 쪽이 열릴지 정렬 순서가 정한다."""
    (tmp_path / "systems.yaml").write_text(
        "systems:\n  - {id: hub, name: H, integration_type: jwt-handoff, audience: hub, url: /hub/api/cb}\n")
    (tmp_path / "routes.env").write_text("")
    (tmp_path / "systems.local.yaml").write_text(
        "box-y:\n  id: hub\n  name: 가짜 허브\n  url: https://collector.example/\n  sort_order: 1\n")
    r = CatalogRegistry(Settings(_env_file=None, catalog_path=str(tmp_path / "systems.yaml"),
                                 routes_path=str(tmp_path / "routes.env")))
    assert [s.id for s in r.all()] == ["box-y", "hub"]
    assert (r.get("hub").integration_type, r.get("hub").url) == ("jwt-handoff", "/hub/api/cb")


def test_새_타일도_라우트가_있으면_프록시로_열린다(tmp_path):
    """추적된 외부 타일과 같은 규칙이다 — 라우트 파일이 박스별 진실이라 목적지가 있으면 포털 경유(`/<id>/`)로 연다.
    어느 쪽이든 로그인 토큰을 보내는 타일은 되지 않는다."""
    r = _catalog(tmp_path, None)
    (tmp_path / "routes.env").write_text("box-lab=http://192.0.2.30:8080/\n")
    (tmp_path / "systems.local.yaml").write_text(_NEW)
    r.reload()
    t = r.get("box-lab")
    assert (t.integration_type, t.status) == ("proxy", "available")


def test_읽지_못할_새_타일은_그것만_버린다(tmp_path, caplog):
    """박스 파일의 틀린 한 줄이 카탈로그 전체를 멈추면 포털이 뜨지 않는다 — 그 타일만 버리고 어느 칸이 틀렸는지 말한다.
    ⚠ 값은 싣지 않는다 — 박스 파일의 주소는 사내 주소다."""
    with caplog.at_level(logging.WARNING):
        r = _catalog(tmp_path, "box-bad:\n  name: 색이 틀렸다\n  accent: neon\n  url: [\"http://192.0.2.31:9000/\"]\n" + _NEW)
    assert r.get("box-bad") is None
    assert r.get("box-lab") is not None and r.get("ext-b").url == "https://b.example", "나머지는 그대로 산다"
    (rec,) = [rec for rec in caplog.records if "box-bad" in rec.getMessage()]
    assert "accent" in rec.getMessage() and "url" in rec.getMessage()
    logged = caplog.text
    assert "192.0.2.31" not in logged, "틀린 칸의 값이 로그에 실렸다"


# ── 새 타일과 권한 표 — 박스 파일 둘이 짝이다 ─────────────────────────────────
# 새 타일은 권한 표의 어느 플랫폼에도 속하지 않는다 — 표에 없는 타일은 **모두에게 보인다**(filter_tiles). 그래서 플랫폼도 박스
# 파일(access.local.yaml)로 같이 붙여야 권한으로 막힌다. 추적 파일 둘은 그대로 두고 박스 파일 둘만 시험이 쓴다.
_NEW_PLAT = "platforms:\n  - {id: boxlab, label: 시험실 장비 예약, systems: [box-lab]}\n"


def _unplaced(cfg: Path) -> list[str]:
    """합친 카탈로그의 타일 가운데 합친 권한 표의 어느 플랫폼에도 없는 것(test_access_control 의 대조와 같은 규칙)."""
    pol = parse_policy(load_raw(cfg / "access.yaml"))
    reg = CatalogRegistry(Settings(_env_file=None, catalog_path=str(cfg / "systems.yaml"),
                                   routes_path=str(cfg / "routes.env")))
    return [s.id for s in reg.all() if pol.system_key(s.id) is None]


@pytest.fixture()
def box(tmp_path):
    """추적된 systems.yaml·access.yaml 을 베낀 임시 박스 — 박스 파일은 여기에만 쓴다(리포의 backend/config 는 건드리지 않는다)."""
    for name in ("systems.yaml", "access.yaml"):
        shutil.copy(_CONFIG / name, tmp_path / name)
    (tmp_path / "routes.env").write_text("")
    return tmp_path


@pytest.fixture()
def portal(box):
    s = Settings(_env_file=None, user_store_path=str(box / "users.sqlite"), local_bootstrap_admins="boss@corp.com",
                 catalog_path=str(box / "systems.yaml"), routes_path=str(box / "routes.env"),
                 access_path=str(box / "access.yaml"))
    app.dependency_overrides[get_settings] = lambda: s
    from app.auth.routes.local import _rl
    _rl.clear()
    with TestClient(app) as c:
        keep = (app.state.user_store, app.state.access, app.state.catalog)
        # 컨텍스트 진입 후 교체(실DB 오염 방지 — test_local_auth 와 같다). 카탈로그·권한 표도 임시 박스 것으로 바꾼다.
        app.state.user_store, app.state.access, app.state.catalog = UserStore(s), AccessPolicy(s), CatalogRegistry(s)
        for email in ("boss@corp.com", "user@corp.com"):
            c.post("/auth/local/signup", json={"email": email, "name": email.split("@")[0], "password": "pw123456"})
        h = _login(c, "boss@corp.com")
        assert c.post("/auth/local/users/user@corp.com/approve", json={"groups": []}, headers=h).status_code == 200
        yield c
        app.state.user_store, app.state.access, app.state.catalog = keep
    app.dependency_overrides.pop(get_settings, None)


def _login(c, email):
    r = c.post("/auth/local/login", json={"email": email, "password": "pw123456"})
    assert r.status_code == 200, r.text
    return {"X-CSRF-Token": c.cookies.get("hwax_csrf")}


def test_새_타일은_플랫폼도_박스_파일로_붙여야_어디엔가_속한다(box):
    assert _unplaced(box) == [], "추적 파일만으로는 모든 타일이 어느 플랫폼에든 속한다"
    (box / "systems.local.yaml").write_text(_NEW)
    assert _unplaced(box) == ["box-lab"], "타일만 붙이면 권한과 무관하게 모두에게 보인다"
    (box / "access.local.yaml").write_text(_NEW_PLAT)
    assert _unplaced(box) == []


def test_박스_파일_둘로_붙인_타일은_그_플랫폼_허가가_있는_사람에게만_보인다(box, portal):
    c = portal
    # 같은 박스 파일에 핸드오프 타일도 하나 적어 본다 — 청중은 실제로 있는 것(heax-hub)을 댄다.
    (box / "systems.local.yaml").write_text(
        _NEW + "box-sso:\n  name: 토큰 수집\n  integration_type: jwt-handoff\n  audience: heax-hub\n"
               "  url: https://collector.example/cb\n")
    (box / "access.local.yaml").write_text(_NEW_PLAT)
    ha = _login(c, "boss@corp.com")
    assert c.post("/systems/reload", headers=ha).status_code == 200, "타일은 다시 읽기로, 권한 표는 다음 요청에 저절로"
    seen = [t["id"] for t in c.get("/systems").json()]
    assert "box-lab" in seen, "관리자는 전부 본다"
    assert "box-sso" not in seen and c.post("/systems/box-sso/launch", headers=ha).status_code == 404, \
        "박스 파일이 만든 수신처로는 관리자에게도 로그인 토큰이 발급되지 않는다"
    assert c.post("/systems/heax-hub/launch", headers=ha).json()["action"] == "/heax-hub/api/v1/auth/portal-callback", \
        "추적된 핸드오프 타일은 그대로다(위의 404 가 발급 자체가 꺼져서가 아니다)"
    plats = {r["key"]: r for r in c.get("/auth/access").json()["platforms"]}
    assert plats["plat:boxlab"]["label"] == "시험실 장비 예약" and plats["plat:boxlab"]["desc"] == "이 박스에만 있는 서비스", \
        "권한 표에 줄이 생기고 설명은 새 타일의 소개를 빌린다"

    h = _login(c, "user@corp.com")
    assert c.get("/systems").json() == [], "플랫폼 허가가 없으면 새 타일도 안 보인다"
    assert c.get("/systems/box-lab").status_code == 404
    assert c.post("/systems/box-lab/open", headers=h).status_code == 404

    ha = _login(c, "boss@corp.com")
    r = c.patch("/auth/access/users/user@corp.com", json={"grants": ["plat:boxlab"]}, headers=ha)
    assert r.status_code == 200 and r.json()["grants"] == ["plat:boxlab"], "박스 파일의 플랫폼도 허가할 수 있는 키다"

    h = _login(c, "user@corp.com")
    (tile,) = c.get("/systems").json()
    assert (tile["id"], tile["integration_type"], tile["url"], tile["status"]) == \
        ("box-lab", "external-url", "http://192.0.2.30:8080/", "available")
    assert c.post("/systems/box-lab/open", headers=h).json() == {"ok": True}
    r = c.post("/systems/box-lab/launch", headers=h)
    assert r.status_code == 400 and "fields" not in r.text, "새 타일로는 로그인 토큰이 나가지 않는다"
