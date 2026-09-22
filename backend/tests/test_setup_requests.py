# 배선 설정 — **안 된 것만** 뜨고, 모르는 것을 됐다고 말하지 않는다
"""이 화면의 존재 이유는 이 스택에서 반복된 실패 모양이다 — "설정 한 줄이 빠졌는데
아무 데도 안 보인다". 배포는 성공하고 화면도 멀쩡한데 그 기능만 조용히 안 되고, 며칠 뒤
사용자가 "왜 안 되죠" 로 발견한다.

그래서 여기서 고정하는 것은 셋이다.
  · **된 것은 사라진다** — 다 됐는데도 상자가 남아 있으면 아무도 안 보게 된다.
  · **모르면 모른다고 한다** — 확인이 실패했을 때 ok 로 접으면, 이 화면이 거짓말을 한다.
  · **비밀은 값이 아니라 있고 없음만** 본다. 응답에 시크릿·내부 주소가 실리면 안 된다.
"""
import httpx
import pytest
import yaml
from fastapi.testclient import TestClient

from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.main import app
from app.setup_requests import parse_requests, run_check

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
async def test_an_unknown_check_never_says_ok():
    """**모르는 것을 됐다고 말하지 않는다** — 이 화면이 거짓말하면 존재 이유가 없어진다."""
    assert await run_check("이런_검사는_없다", Settings(), None) == "unknown"


@pytest.mark.anyio
async def test_access_check_reads_the_live_policy_not_the_file():
    class _Item:
        def __init__(self, gw):
            self.gateway = gw

    class _Acc:
        def __init__(self, gw):
            self.items = [_Item(gw)]

    assert await run_check("access_ste", Settings(), _Acc(("ste",))) == "ok"
    assert await run_check("access_ste", Settings(), _Acc(("other",))) == "todo"
    assert await run_check("access_ste", Settings(), None) == "unknown"


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
