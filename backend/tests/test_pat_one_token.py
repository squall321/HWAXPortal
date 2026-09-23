# 토큰 하나로 하위 사이트 공용 — 발급 화면이 청중을 **좁히지 않는지**와, 기본 청중이 게이트웨이
# REST 다리의 사이트 키와 어긋나지 않는지를 못박는다.
#
# 종전에 화면이 `audiences: ['mcp-gateway']` 를 박아 보냈다. 백엔드는 처음부터 다중 청중이었고
# 게이트웨이 REST 프록시도 살아 있었는데, 그 한 줄 때문에 사용자가 낸 토큰은 MCP 밖으로 못 나갔다 —
# **설정은 맞는데 화면이 덮는** 모양이라 서버 쪽만 보면 원인이 안 잡힌다.
import re
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient

from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.main import app

_REPO = Path(__file__).resolve().parents[2]


@pytest.fixture()
def client(tmp_path):
    s = Settings(user_store_path=str(tmp_path / "users.sqlite"),
                 jwt_keys_dir=str(tmp_path / "keys"),
                 local_bootstrap_admins="a@corp.com")
    app.dependency_overrides[get_settings] = lambda: s
    from app.auth.routes.local import _rl
    _rl.clear()
    with TestClient(app) as c:
        app.state.user_store = UserStore(s)
        yield c
    app.dependency_overrides.pop(get_settings, None)


def _login(client) -> dict:
    client.post("/auth/local/signup",
                json={"email": "a@corp.com", "name": "A", "password": "pw123456"})
    client.post("/auth/local/login", json={"email": "a@corp.com", "password": "pw123456"})
    return {"X-CSRF-Token": client.cookies.get("hwax_csrf")}


def test_청중을_안_주면_기본_목록이_통째로_실린다(client):
    h = _login(client)
    r = client.post("/auth/pat", json={"name": "claude"}, headers=h)
    assert r.status_code == 200, r.text
    aud = jwt.decode(r.json()["token"], options={"verify_signature": False},
                     algorithms=["RS256"])["aud"]
    assert isinstance(aud, list) and len(aud) > 1, "청중이 하나면 '토큰 하나로 공용'이 아니다"
    # 챗·개인 Claude MCP 가 이 청중을 요구한다 — 빠지면 토큰이 있어도 챗이 401 이다.
    assert "mcp-gateway" in aud
    # 게이트웨이 REST 다리가 아는 사이트들도 같은 한 장에 들어야 한다.
    assert {"ai-data-hub", "ste", "dyna-forge", "step-forge"} <= set(aud)


def test_발급_화면이_청중을_박아_보내지_않는다():
    """서버가 사이트를 늘려도 화면이 낸 토큰이 옛 범위에 갇히지 않게."""
    src = (_REPO / "frontend/src/pages/TokenPage.tsx").read_text(encoding="utf-8")
    body = re.search(r"createPat\(\{(.*?)\}\)", src, re.S)
    assert body, "createPat 호출을 못 찾았다 — 이 시험이 낡았다"
    assert "audiences" not in body.group(1), (
        "화면이 청중을 직접 적으면 서버 기본값이 덮인다 — 적으려면 이 시험을 함께 고쳐라")


def test_기본_청중은_게이트웨이_rest_사이트_키와_같은_이름을_쓴다():
    """이름이 어긋나면 PAT 는 발급되는데 프록시는 `unknown site` 404 로 답한다."""
    prov = (_REPO.parent / "HWAXMcpGateway" / "provision-config.sh")
    if not prov.exists():
        pytest.skip("게이트웨이 리포가 옆에 없다")
    keys = set(re.findall(r'rest\["([a-z0-9-]+)"\]', prov.read_text(encoding="utf-8")))
    assert keys, "provision 에서 rest 사이트 키를 못 찾았다 — 이 시험이 낡았다"
    default = set(Settings().pat_default_audiences.split(","))
    missing = keys - default
    assert not missing, f"게이트웨이 REST 사이트인데 기본 청중에 없다: {sorted(missing)}"
