# 배선 설정 — **안 된 것만** 뜨고, 모르는 것을 됐다고 말하지 않는다
"""이 화면의 존재 이유는 이 스택에서 반복된 실패 모양이다 — "설정 한 줄이 빠졌는데
아무 데도 안 보인다". 배포는 성공하고 화면도 멀쩡한데 그 기능만 조용히 안 되고, 며칠 뒤
사용자가 "왜 안 되죠" 로 발견한다.

그래서 여기서 고정하는 것은 셋이다.
  · **된 것은 사라진다** — 다 됐는데도 상자가 남아 있으면 아무도 안 보게 된다.
  · **모르면 모른다고 한다** — 확인이 실패했을 때 ok 로 접으면, 이 화면이 거짓말을 한다.
  · **비밀은 값이 아니라 있고 없음만** 본다. 응답에 시크릿·내부 주소가 실리면 안 된다.
"""
from pathlib import Path

import httpx
import pytest
import yaml
from fastapi.testclient import TestClient

from app.access.policy import AccessPolicy
from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.main import app
from app.catalog.registry import CatalogRegistry
from app.setup_requests import check_notes, parse_requests, run_check

YAML_DOC = """
requests:
  - id: needs-secret
    title: 시크릿을 넣어라
    tag: 연결
    severity: blocker
    check: ste_sso_secret
    body: |
      값을 .env 에 넣는다.
  - id: by-hand
    title: 사람이 해야 하는 것
    severity: request
    manual: true
    body: 다른 박스에서 한다.
  - {}
  - id: no-title
"""


@pytest.fixture()
def client(tmp_path, monkeypatch):
    cfg = tmp_path / "setup_requests.yaml"
    cfg.write_text(YAML_DOC, encoding="utf-8")

    def _make(**over):
        s = Settings(user_store_path=str(tmp_path / "u.sqlite"),
                     local_bootstrap_admins="boss@corp.com",
                     setup_requests_path=str(cfg), **over)
        app.dependency_overrides[get_settings] = lambda: s
        from app.auth.routes.local import _rl
        _rl.clear()
        c = TestClient(app)
        c.__enter__()
        app.state.user_store = UserStore(s)
        return c

    made = []

    def factory(**over):
        c = _make(**over)
        made.append(c)
        return c

    yield factory
    for c in made:
        c.__exit__(None, None, None)
    app.dependency_overrides.pop(get_settings, None)


def _login(c):
    c.post("/auth/local/signup", json={"email": "boss@corp.com", "name": "B", "password": "pw123456"})
    assert c.post("/auth/local/login",
                  json={"email": "boss@corp.com", "password": "pw123456"}).status_code == 200


# ── YAML 읽기 ───────────────────────────────────────────────────────────────
def test_broken_rows_are_skipped_not_fatal():
    """안내가 못 뜨는 것보다 포털이 500 을 내는 게 훨씬 나쁘다."""
    rows = parse_requests(yaml.safe_load(YAML_DOC))
    assert [r["id"] for r in rows] == ["needs-secret", "by-hand"]
    assert rows[1]["manual"] is True and rows[1]["check"] is None


def test_garbage_yaml_yields_nothing_rather_than_raising():
    for bad in (None, "문자열", {"requests": "목록이 아님"}, {"requests": [1, 2]}):
        assert parse_requests(bad) == []


# ── 확인 ────────────────────────────────────────────────────────────────────
@pytest.mark.anyio
async def test_a_missing_secret_is_todo_and_a_present_one_is_ok():
    s = Settings(ste_sso_secret="")
    assert await run_check("ste_sso_secret", s, None) == "todo"
    s2 = Settings(ste_sso_secret="x" * 20)
    assert await run_check("ste_sso_secret", s2, None) == "ok"


@pytest.mark.anyio
async def test_ra_sso_is_todo_until_the_secret_is_set():
    """RA 사람별 위임(docs/sso-delegation) — 포털이 아는 것은 비밀의 있고 없음뿐이다. 공백만이면 없는 것이다."""
    for v in ("", "   "):
        assert await run_check("ra_sso", Settings(_env_file=None, ra_sso_secret=v), None) == "todo"
    assert await run_check("ra_sso", Settings(_env_file=None, ra_sso_secret="x" * 32), None) == "ok"


def test_ra_sso_row_never_claims_a_default_and_says_what_to_do():
    """포털이 비밀을 만들면 RA 쪽이 준비되기 전에 게이트웨이가 위임으로만 불러 RA 호출이 전부 거부된다 — 기본값이 없어야 한다."""
    doc = yaml.safe_load(Path(Settings().resolve("config/setup_requests.yaml")).read_text("utf-8"))
    (row,) = [r for r in parse_requests(doc) if r["check"] == "ra_sso"]
    assert (row["default"], row["severity"], row["tag"]) == ("none", "request", "연결")
    assert "ra-request.md" in row["body"] and "RA_SSO_SECRET" in row["body"]


@pytest.mark.anyio
async def test_an_unknown_check_never_says_ok():
    """**모르는 것을 됐다고 말하지 않는다** — 이 화면이 거짓말하면 존재 이유가 없어진다."""
    assert await run_check("이런_검사는_없다", Settings(), None) == "unknown"


def _access(tmp_path: Path, gateway: str) -> AccessPolicy:
    """임시 권한 표로 만든 **실물** 정책 로더 — 라우트가 넘기는 app.state.access 와 같은 종류다."""
    f = tmp_path / "access.yaml"
    f.write_text(f"platforms:\n  - {{id: smarttwin, label: SmartTwin, gateway: [{gateway}]}}\n", encoding="utf-8")
    return AccessPolicy(Settings(_env_file=None, access_path=str(f)))


@pytest.mark.anyio
async def test_access_check_reads_the_live_policy_not_the_file(tmp_path):
    """**실물로 본다.** 라우트는 app.state.access(AccessPolicy — 표를 캐시하는 로더)를 넘기는데 확인은 그 객체에 없는 `.items` 를
    읽었다. 예외가 삼켜져 떠 있는 포털에서는 늘 'unknown' 이었고 — 표에 ste 가 있어도 '필수' 항목이 영영 사라지지 않았다.
    종전 시험은 `.items` 를 가진 대역을 넣어 초록이었다(대역이 틀린 모양을 굳혔다)."""
    assert await run_check("access_ste", Settings(), _access(tmp_path, "ste, smart-twin-mcp")) == "ok"
    assert await run_check("access_ste", Settings(), _access(tmp_path, "other")) == "todo"
    assert await run_check("access_ste", Settings(), None) == "unknown"


def test_the_access_item_disappears_on_a_live_portal(client, tmp_path):
    """화면까지 — 표에 ste 가 있으면 관리자의 배선 설정에서 그 항목이 사라진다(라우트가 넘기는 실물 객체로)."""
    (tmp_path / "setup_requests.yaml").write_text(
        "requests:\n  - {id: access-policy-ste, title: ste 를 smarttwin 허가에 넣는다, severity: blocker, check: access_ste, body: x}\n",
        encoding="utf-8")
    c = client()
    _login(c)
    keep = app.state.access
    try:
        app.state.access = _access(tmp_path, "other")
        got = {i["id"]: i["state"] for i in c.get("/setup/requests").json()["items"]}
        assert got == {"access-policy-ste": "todo"}, "표에 없으면 하라고 말한다(모른다고 하지 않는다)"
        app.state.access = _access(tmp_path, "ste")
        assert c.get("/setup/requests").json()["items"] == [], "표에 있으면 사라진다"
    finally:
        app.state.access = keep


# ── 어느 플랫폼에도 없는 타일 — 권한과 무관하게 모두에게 보인다 ─────────────────────────────────────
# 타일은 그것을 여는 플랫폼 허가가 있는 사람에게만 보이는데(policy.filter_tiles), 표에 없는 타일은 막지 않는다. 추적 파일끼리는
# 시험(test_access_control)이 대조하지만, 박스 파일(systems.local.yaml)로 붙인 타일은 그 박스에서 시험을 돌려야만 드러났다 —
# 운영 박스는 시험을 돌리지 않는다. 떠 있는 포털이 제 카탈로그와 제 권한 표를 대조해 관리자에게 말한다.
def _catalog_box(tmp_path: Path, *, local_tile: bool, local_platform: bool) -> tuple[CatalogRegistry, AccessPolicy]:
    (tmp_path / "systems.yaml").write_text(
        "systems:\n  - {id: known, name: Known, integration_type: external-url, url: 'https://known.example'}\n", encoding="utf-8")
    (tmp_path / "routes.env").write_text("")
    (tmp_path / "access.yaml").write_text("platforms:\n  - {id: known, label: Known, systems: [known]}\n", encoding="utf-8")
    for name, on, body in (("systems.local.yaml", local_tile, "box-lab:\n  name: 실험실 장비\n  url: http://192.0.2.30:9000/\n"),
                           ("access.local.yaml", local_platform, "platforms:\n  - {id: lab, label: 실험실, systems: [box-lab]}\n")):
        if on:
            (tmp_path / name).write_text(body, encoding="utf-8")
        else:
            (tmp_path / name).unlink(missing_ok=True)
    s = Settings(_env_file=None, catalog_path=str(tmp_path / "systems.yaml"), routes_path=str(tmp_path / "routes.env"),
                 access_path=str(tmp_path / "access.yaml"))
    return CatalogRegistry(s), AccessPolicy(s)


@pytest.mark.anyio
async def test_a_tile_outside_every_platform_is_reported_with_its_id(tmp_path):
    """**이 시험이 이 구획의 이유다** — 박스 파일로 타일만 붙이고 플랫폼을 안 붙였다."""
    cat, acc = _catalog_box(tmp_path, local_tile=True, local_platform=False)
    assert await run_check("tiles_in_access_table", Settings(), acc, cat) == "todo"
    notes = check_notes("tiles_in_access_table", Settings(), acc, cat)
    assert len(notes) == 1 and "box-lab" in notes[0] and "known" not in notes[0], notes
    assert "192.0.2.30" not in " ".join(notes), "타일의 사내 주소를 응답에 싣지 않는다"


@pytest.mark.anyio
async def test_tiles_that_all_belong_to_a_platform_are_ok(tmp_path):
    for tile, plat in ((False, False), (True, True), (False, True)):
        cat, acc = _catalog_box(tmp_path, local_tile=tile, local_platform=plat)
        assert await run_check("tiles_in_access_table", Settings(), acc, cat) == "ok", (tile, plat)
        assert check_notes("tiles_in_access_table", Settings(), acc, cat) == []


@pytest.mark.anyio
async def test_the_tile_check_says_unknown_when_it_cannot_look(tmp_path):
    cat, acc = _catalog_box(tmp_path, local_tile=True, local_platform=False)
    assert await run_check("tiles_in_access_table", Settings(), acc, None) == "unknown", "카탈로그를 못 받았다 — 됐다고 하지 않는다"
    assert await run_check("tiles_in_access_table", Settings(), None, cat) == "unknown"


@pytest.mark.anyio
async def test_the_tracked_catalog_has_no_tile_outside_the_tracked_table(tmp_path):
    """추적 파일끼리는 늘 맞아야 한다 — 어긋나면 새 박스가 첫 화면부터 이 항목을 본다. 이 박스의 local 파일에는 기대지 않는다."""
    cfg = Path(Settings().resolve("config/systems.yaml")).parent
    for name in ("systems.yaml", "access.yaml"):
        (tmp_path / name).write_text((cfg / name).read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "routes.env").write_text("")
    s = Settings(_env_file=None, catalog_path=str(tmp_path / "systems.yaml"), routes_path=str(tmp_path / "routes.env"),
                 access_path=str(tmp_path / "access.yaml"))
    assert await run_check("tiles_in_access_table", Settings(), AccessPolicy(s), CatalogRegistry(s)) == "ok"


def test_the_shipped_list_asks_the_tile_question_and_says_how_to_fix_it():
    doc = yaml.safe_load(Path(Settings().resolve("config/setup_requests.yaml")).read_text("utf-8"))
    (row,) = [r for r in parse_requests(doc) if r["check"] == "tiles_in_access_table"]
    assert row["severity"] == "blocker" and row["default"] == "none" and not row["manual"]
    assert "access.local.yaml" in row["body"] and "systems:" in row["body"]


def test_the_admin_sees_the_unlisted_tile_and_it_clears_without_a_restart(client, tmp_path):
    """화면까지 — 라우트가 떠 있는 카탈로그·권한 표를 넘긴다. 플랫폼을 붙이면 재기동 없이 사라진다(권한 표는 요청마다 파일 시각을 본다)."""
    (tmp_path / "setup_requests.yaml").write_text(
        "requests:\n  - {id: tiles, title: 표에 없는 타일, severity: blocker, check: tiles_in_access_table, body: x}\n", encoding="utf-8")
    box = tmp_path / "box"; box.mkdir()
    cat, acc = _catalog_box(box, local_tile=True, local_platform=False)
    c = client()
    _login(c)
    keep = (app.state.catalog, app.state.access)
    try:
        app.state.catalog, app.state.access = cat, acc
        (item,) = c.get("/setup/requests").json()["items"]
        assert item["state"] == "todo" and any("box-lab" in n for n in item["notes"]), item
        (box / "access.local.yaml").write_text("platforms:\n  - {id: lab, label: 실험실, systems: [box-lab]}\n", encoding="utf-8")
        assert c.get("/setup/requests").json()["items"] == [], "플랫폼을 붙였는데 항목이 남아 있다"
    finally:
        app.state.catalog, app.state.access = keep


@pytest.mark.anyio
async def test_an_unreachable_backend_is_todo_not_a_crash(monkeypatch):
    """확인이 실패하는 것은 정상이다 — 그게 곧 '안 되어 있다' 이고, 예외가 아니어야 한다."""
    import app.setup_requests as mod

    seen = []

    async def _down(url):
        seen.append(url)
        return False

    monkeypatch.setattr(mod, "_probe", _down)
    got = await run_check("ste_backend", Settings(ste_base_url="http://x/ste"), None)
    assert got == "todo"
    assert seen == ["http://x/ste/api/health"], "건강 검사 경로가 틀렸다"


@pytest.mark.anyio
async def test_a_real_timeout_is_swallowed(monkeypatch):
    """느린 백엔드가 홈 화면을 500 으로 만들면 안 된다."""
    import app.setup_requests as mod

    class _Boom:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url):
            raise httpx.ConnectTimeout("too slow")

    monkeypatch.setattr(mod.httpx, "AsyncClient", lambda **kw: _Boom())
    assert await mod._probe("http://x/api/health") is False


# ── 화면에 나가는 것 ────────────────────────────────────────────────────────
def test_anonymous_cannot_read_the_setup_list(client):
    c = client()
    assert c.get("/setup/requests").status_code in (401, 403)


def test_done_items_disappear(client, monkeypatch):
    """다 됐는데도 상자가 남으면 아무도 안 보게 된다."""
    c = client(ste_sso_secret="y" * 20)
    _login(c)
    body = c.get("/setup/requests").json()
    ids = [i["id"] for i in body["items"]]
    assert "needs-secret" not in ids, "확인을 통과한 항목이 남아 있다"
    assert "by-hand" in ids, "사람이 해야 하는 것은 남아야 한다"


def test_undone_items_show_with_their_instructions(client):
    c = client(ste_sso_secret="")
    _login(c)
    body = c.get("/setup/requests").json()
    item = next(i for i in body["items"] if i["id"] == "needs-secret")
    assert item["state"] == "todo"
    assert "값을 .env 에 넣는다" in item["body"], "무엇을 하라는지가 화면에 있어야 한다"
    assert body["pending"] == len(body["items"])


def test_no_secret_value_leaks_into_the_response(client):
    """있고 없음만 본다 — 값이 응답에 실리면 안 된다."""
    secret = "super-secret-value-0123456789"
    c = client(ste_sso_secret=secret)
    _login(c)
    assert secret not in c.get("/setup/requests").text


# ── "셋업이 안 되어 있으면 기본값이 들어가나" ────────────────────────────────
#
# 항목마다 답이 다르고, **그 차이를 화면이 말해야** 한다. 구분이 없으면 목록 전체가
# "다 내가 손으로 해야 하는 일" 로 보여서 아무도 시작하지 않는다. 반대로 기본값이 없는데
# 있다고 말하면 사람이 안 하고 넘어가 기능이 조용히 꺼진 채로 남는다.
def test_default_policy_is_one_of_three(client):
    import yaml as _yaml

    from app.config import Settings

    doc = _yaml.safe_load(
        (Path(Settings().resolve("config/setup_requests.yaml"))).read_text("utf-8"))
    for row in doc["requests"]:
        assert row.get("default") in ("auto", "generate", "none"), row["id"]


def test_an_unknown_default_is_read_as_none():
    """**기본값이 있다고 잘못 말하는 쪽이 더 나쁘다** — 모르면 '값을 정해야 함' 으로 본다."""
    rows = parse_requests({"requests": [
        {"id": "a", "title": "A", "default": "마법"},
        {"id": "b", "title": "B"},
        {"id": "c", "title": "C", "default": "auto"},
    ]})
    assert [r["default"] for r in rows] == ["none", "none", "auto"]


def test_credentials_never_claim_a_default(client):
    """자격증명은 임의로 만들면 그 잡이 누구 것인지 알 수 없어진다."""
    import yaml as _yaml

    from app.config import Settings

    doc = _yaml.safe_load(
        (Path(Settings().resolve("config/setup_requests.yaml"))).read_text("utf-8"))
    by_id = {r["id"]: r for r in doc["requests"]}
    assert by_id["dynaforge-gateway-pat"]["default"] == "none"
    assert by_id["ste-backend-route"]["default"] == "none", "주소는 찍으면 죽은 라우트가 된다"
    # 우리 서비스끼리만 쓰는 난수는 만들어도 된다
    assert by_id["ste-sso-secret"]["default"] == "generate"


def test_운영자_할_일은_관리자에게만_보인다(client):
    """일반 사용자 홈에 '배선 설정 · 필수 3' 상자가 앱 목록보다 먼저 떴다 — 운영자 할 일이다(docs/ui-refresh 단계 1)."""
    c = client(ste_sso_secret="")
    _login(c)                                                    # 부트스트랩 관리자
    assert c.get("/setup/requests").json()["items"], "전제 — 관리자에게는 할 일이 보인다"
    h = {"X-CSRF-Token": c.cookies.get("hwax_csrf")}
    c.post("/auth/local/signup", json={"email": "plain@corp.com", "name": "P", "password": "pw123456"})
    assert c.post("/auth/local/users/plain@corp.com/approve", json={"groups": []}, headers=h).status_code == 200
    c.post("/auth/local/logout", headers=h)
    assert c.post("/auth/local/login", json={"email": "plain@corp.com", "password": "pw123456"}).status_code == 200
    assert c.get("/setup/requests").json() == {"items": [], "pending": 0}


def test_manual_항목은_확인함으로_상자에서_빠지고_되돌릴_수_있다(client):
    """포털이 확인할 수 없는 항목은 영원히 남아 '늘 노란 상자' 가 됐다 — 사람이 했다고 표시해야 빠진다(docs/ui-refresh 단계 4)."""
    c = client(ste_sso_secret="")
    _login(c)
    h = {"X-CSRF-Token": c.cookies.get("hwax_csrf")}
    ids = lambda: [i["id"] for i in c.get("/setup/requests").json()["items"]]  # noqa: E731
    assert "by-hand" in ids(), "전제 — manual 항목이 상자에 있다"

    assert c.post("/setup/requests/by-hand/ack", headers=h).status_code == 200
    body = c.get("/setup/requests").json()
    assert "by-hand" not in [i["id"] for i in body["items"]]
    assert body["pending"] == len(body["items"])
    (acked,) = body["acked"]
    assert acked["id"] == "by-hand" and acked["by"] == "boss@corp.com" and acked["at"] > 0

    assert c.delete("/setup/requests/by-hand/ack", headers=h).status_code == 200
    assert "by-hand" in ids()
    assert c.get("/setup/requests").json()["acked"] == []


def test_포털이_확인하는_항목은_확인함으로_덮을_수_없다(client):
    """check 가 있는 항목은 고쳐지면 저절로 사라진다 — 사람이 '됐다' 고 눌러 안 된 것을 숨기면 이 상자가 거짓말을 한다."""
    c = client(ste_sso_secret="")
    _login(c)
    h = {"X-CSRF-Token": c.cookies.get("hwax_csrf")}
    assert c.post("/setup/requests/needs-secret/ack", headers=h).status_code == 404
    assert c.post("/setup/requests/no-such/ack", headers=h).status_code == 404
    assert "needs-secret" in [i["id"] for i in c.get("/setup/requests").json()["items"]]


def test_확인함은_관리자만_CSRF_와_함께(client):
    c = client(ste_sso_secret="")
    _login(c)
    assert c.post("/setup/requests/by-hand/ack").status_code == 403, "CSRF 없이는 안 된다"
    h = {"X-CSRF-Token": c.cookies.get("hwax_csrf")}
    c.post("/auth/local/signup", json={"email": "plain@corp.com", "name": "P", "password": "pw123456"})
    assert c.post("/auth/local/users/plain@corp.com/approve", json={"groups": []}, headers=h).status_code == 200
    c.post("/auth/local/logout", headers=h)
    assert c.post("/auth/local/login", json={"email": "plain@corp.com", "password": "pw123456"}).status_code == 200
    h = {"X-CSRF-Token": c.cookies.get("hwax_csrf")}
    assert c.post("/setup/requests/by-hand/ack", headers=h).status_code == 403
