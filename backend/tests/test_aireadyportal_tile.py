# AI Ready Portal 타일 — id 는 aireadyportal, 포털 경유 + 타일 클릭 SSO(jwt-handoff)이고 플랫폼 id·게이트웨이 키는 arp 그대로다(ARP·ODB 작업지시 7-3·7-4·7-5)
"""타일 id 를 `arp` 에서 `aireadyportal` 로 바꾸고 직결 링크를 핸드오프로 돌린다. 한 글자 차이로 셋이 갈린다.

- **타일 id** `aireadyportal` — 포털 경로 접두어(`/aireadyportal/`)이자 routes 파일의 키, 로고를 고르는 값.
- **플랫폼 id** `arp` — 권한 키 `plat:arp`. 게이트웨이 `allowed_groups` 가 이 값을 요구하고 사람들의 허가가 이 키로 원장에 있다.
  바꾸면 그 허가가 전부 '표에 없는 키' 가 되어 버려진다.
- **게이트웨이 백엔드 키** `arp` — MCP 도구가 붙는 백엔드.

여기서 고정하는 것은 그 갈림과, 타일을 누르면 ARP 청중의 토큰이 콜백으로 간다는 것이다. 주소는 문서용 예약 대역만 쓴다.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient

from app.access.policy import AccessPolicy, load_raw, parse_policy
from app.auth.user_store import UserStore
from app.catalog.registry import CatalogRegistry
from app.config import Settings, get_settings
from app.main import app

_ROOT = Path(__file__).resolve().parents[2]
_CONFIG = _ROOT / "backend" / "config"
_FE = _ROOT / "frontend"
_TSC = _FE / "node_modules/.bin/tsc"
_CALLBACK = "/aireadyportal/api/auth/portal-callback"


@pytest.fixture()
def box(tmp_path):
    """추적된 systems.yaml·access.yaml 을 베낀 임시 박스 — 이 박스의 실제 local 파일에 기대지 않는다."""
    for name in ("systems.yaml", "access.yaml"):
        shutil.copy(_CONFIG / name, tmp_path / name)
    (tmp_path / "routes.env").write_text("")
    return tmp_path


def _reg(box: Path) -> CatalogRegistry:
    return CatalogRegistry(Settings(_env_file=None, catalog_path=str(box / "systems.yaml"),
                                    routes_path=str(box / "routes.env")))


def test_타일은_aireadyportal_이고_콜백으로_토큰을_넘기는_핸드오프다(box):
    reg = _reg(box)
    assert reg.get("arp") is None, "옛 타일 id 가 남으면 타일이 둘이 된다"
    t = reg.get("aireadyportal")
    assert (t.name, t.integration_type, t.audience, t.url, t.handoff_mode, t.handoff_param) == \
        ("AI Ready Portal", "jwt-handoff", "aireadyportal", _CALLBACK, "auto_post", "token")
    assert (t.status, t.enabled) == ("available", True)


def test_라우트도_박스_파일도_콜백_주소를_못_바꾼다(box, caplog):
    """routes 파일의 `aireadyportal=` 은 nginx 가 넘길 곳이지 토큰을 보낼 곳이 아니다. 박스에 남아 있는 옛 `arp:` 덮어쓰기
    (직결 링크 시절 것)는 고아가 된다 — 타일을 하나 더 만들지도, 새 타일의 주소를 바꾸지도 않고 경고만 남긴다."""
    (box / "routes.env").write_text("aireadyportal=http://203.0.113.20:3001/\n")
    (box / "systems.local.yaml").write_text(
        "arp:\n  url: http://203.0.113.20:3001/\naireadyportal:\n  url: http://203.0.113.20:3001/\n")
    reg = _reg(box)
    t = reg.get("aireadyportal")
    assert (t.integration_type, t.url, t.status) == ("jwt-handoff", _CALLBACK, "available")
    assert reg.get("arp") is None
    assert any("'arp'" in r.getMessage() and "카탈로그에 없는" in r.getMessage() for r in caplog.records), \
        "남은 옛 덮어쓰기를 조용히 넘기지 않는다"


def test_권한은_플랫폼_arp_그대로다(box):
    """타일 목록만 바뀐다 — 플랫폼 id 를 같이 바꾸면 plat:arp 로 허가받은 전원이 막힌다."""
    pol = parse_policy(load_raw(box / "access.yaml"))
    assert pol.system_key("aireadyportal") == "plat:arp"
    assert pol.system_key("arp") is None, "옛 타일 id 가 표에 남으면 없는 타일을 가리킨다"
    assert pol.gateway_policy()["arp"] == ["plat:arp"], "게이트웨이 백엔드 키와 그 권한은 그대로"
    assert pol.item("plat:arp").label == "AI Ready Portal"


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


def test_타일을_누르면_ARP_청중의_토큰이_콜백으로_간다(portal):
    """plat:arp 를 이미 받은 사람은 타일 id 가 바뀌어도 그대로 보고 연다 — 권한 공백이 없다. 없는 사람에게는 없는 타일이다."""
    c = portal
    h = _login(c, "user@corp.com")
    assert c.get("/systems").json() == []
    assert c.post("/systems/aireadyportal/launch", headers=h).status_code == 404

    ha = _login(c, "boss@corp.com")
    assert c.patch("/auth/access/users/user@corp.com", json={"grants": ["plat:arp"]}, headers=ha).status_code == 200

    h = _login(c, "user@corp.com")
    (tile,) = c.get("/systems").json()
    assert (tile["id"], tile["integration_type"], tile["status"], tile["url"]) == \
        ("aireadyportal", "jwt-handoff", "available", None), "핸드오프 타일은 주소를 화면에 주지 않는다(launch 로만 연다)"
    assert c.post("/systems/arp/launch", headers=h).status_code == 404, "옛 id 로는 열리지 않는다"
    r = c.post("/systems/aireadyportal/launch", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body["mode"], body["action"]) == ("auto_post", _CALLBACK)
    claims = jwt.decode(body["fields"]["token"], options={"verify_signature": False})
    assert claims["aud"] == "aireadyportal", "ARP 의 ARP_PORTAL_AUDIENCE 와 글자 단위로 같아야 받는다"
    assert (claims["email"], claims["scope"]) == ("user@corp.com", "launch")


# ── 로고(7-5) — 타일 id 로 고른다 ─────────────────────────────────────────────
@pytest.mark.skipif(not _TSC.exists() or not shutil.which("node"),
                    reason="frontend node_modules(tsc) 또는 node 가 없다 — 로고를 그려 볼 수 없다")
def test_로고는_새_타일_id_로_그려진다(tmp_path):
    """타일 id 만 바꾸면 로고가 기본 원으로 떨어진다(기능은 멀쩡해서 아무도 신고하지 않는다). PlatformLogo 만 컴파일해
    실제로 그려 본다 — 새 id 는 제 그림을, 옛 id 는 이제 기본 원을 낸다."""
    r = subprocess.run([str(_TSC), str(_FE / "src/components/catalog/PlatformLogo.tsx"), "--outDir", str(tmp_path),
                        "--module", "commonjs", "--target", "es2019", "--jsx", "react-jsx", "--skipLibCheck"],
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
    (tmp_path / "draw.cjs").write_text(
        "const { renderToStaticMarkup } = require('react-dom/server');\n"
        "const { createElement } = require('react');\n"
        "const { PlatformLogo } = require('./PlatformLogo.js');\n"
        "const out = {};\n"
        "for (const id of process.argv.slice(2)) out[id] = renderToStaticMarkup(createElement(PlatformLogo, { id }));\n"
        "process.stdout.write(JSON.stringify(out));\n")
    r = subprocess.run(["node", "draw.cjs", "aireadyportal", "arp", "no-such-tile", "odb-hub"], cwd=str(tmp_path),
                       capture_output=True, text=True, timeout=120,
                       env={**os.environ, "NODE_PATH": str(_FE / "node_modules")})
    assert r.returncode == 0, r.stdout + r.stderr
    svg = json.loads(r.stdout)
    assert svg["aireadyportal"] != svg["no-such-tile"], "새 타일 id 가 기본 원으로 떨어졌다"
    assert "<ellipse" in svg["aireadyportal"], "AI Ready 데이터(적층) 그림"
    assert svg["arp"] == svg["no-such-tile"], "옛 타일 id 의 그림이 남아 있다 — 그 id 의 타일은 이제 없다"
    assert svg["odb-hub"] != svg["no-such-tile"], "다른 타일의 그림은 그대로"
