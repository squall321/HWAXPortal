# 진입 토큰의 소속 클레임 — 켠 시스템(MX WhitePaper)에만, 값이 있고 표에 있는 소속일 때만 싣는다(docs/mxwp-wiki P3 · MW-D3)
"""MX WhitePaper 위키는 소속 단위로 읽기 범위를 가른다(MXWhitePaper docs/llm-wiki CONTRACTS §2-11). 브라우저로 들어온 사람의
소속은 포털 진입 토큰으로만 알 수 있다 — 플랫폼 권한(plat:)은 이미 `groups` 에 실리므로 더하는 것은 `affiliation` 하나다.

여기서 고정하는 것.
- 켠 시스템(`claims_affiliation: true`)의 토큰에만 실린다 — 다른 jwt-handoff 앱의 토큰은 그대로다.
- 소속이 없거나 표(access.yaml)에 없는 id 면 칸 자체를 싣지 않는다 — 빈 소속 · 지운 소속이 하위 앱에서 하나의 소속으로
  묶이면 그 사람들끼리 서로의 문서를 읽는다(게이트웨이 `/internal/access/entitlements` 와 같은 규칙).
"""
import shutil
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient

from app.access.policy import AccessPolicy
from app.auth.user_store import UserStore
from app.catalog.registry import CatalogRegistry
from app.config import Settings, get_settings
from app.main import app
from app.schemas.system import CatalogFile

import yaml

_CONFIG = Path(__file__).resolve().parents[1] / "config"


@pytest.fixture()
def portal(tmp_path):
    for name in ("systems.yaml", "access.yaml"):
        shutil.copy(_CONFIG / name, tmp_path / name)
    (tmp_path / "routes.env").write_text("\n")
    s = Settings(_env_file=None, user_store_path=str(tmp_path / "users.sqlite"), local_bootstrap_admins="boss@corp.com",
                 catalog_path=str(tmp_path / "systems.yaml"), routes_path=str(tmp_path / "routes.env"),
                 access_path=str(tmp_path / "access.yaml"))
    app.dependency_overrides[get_settings] = lambda: s
    from app.auth.routes.local import _rl
    _rl.clear()
    with TestClient(app) as c:
        keep = (app.state.user_store, app.state.access, app.state.catalog)
        # 컨텍스트 진입 후 교체(실DB 오염 방지 — test_aireadyportal_tile 과 같다).
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


def _claims(c, system_id, h):
    r = c.post(f"/systems/{system_id}/launch", headers=h)
    assert r.status_code == 200, r.text
    return jwt.decode(r.json()["fields"]["token"], options={"verify_signature": False})


def test_소속이_있으면_MX_백서_토큰에만_싣는다(portal):
    c = portal
    ha = _login(c, "boss@corp.com")
    assert c.patch("/auth/access/users/user@corp.com", json={"affiliation": "CAEG", "grants": []},
                   headers=ha).status_code == 200
    h = _login(c, "user@corp.com")

    mx = _claims(c, "mx-white-paper", h)
    assert mx["affiliation"] == "CAEG"
    assert mx["aud"] == "mx-white-paper" and mx["scope"] == "launch"
    assert "plat:mxwhitepaper" in mx["groups"], "플랫폼 권한은 원래 groups 에 실린다 — 위키의 plat: 범위가 이것을 읽는다"

    sf = _claims(c, "signalforge", h)
    assert "affiliation" not in sf, "켜지 않은 jwt-handoff 앱에는 소속이 퍼지지 않는다"


def test_소속이_없으면_칸을_싣지_않는다(portal):
    c = portal
    ha = _login(c, "boss@corp.com")
    assert c.patch("/auth/access/users/user@corp.com", json={"grants": ["plat:mxwhitepaper"]},
                   headers=ha).status_code == 200
    h = _login(c, "user@corp.com")
    mx = _claims(c, "mx-white-paper", h)
    assert "affiliation" not in mx, "빈 문자열도 싣지 않는다 — '소속 없음' 이 하나의 소속으로 묶인다"


def test_표에_없는_소속_id_는_싣지_않는다(portal):
    """조직 개편으로 표에서 지운 소속이 원장에 남은 경우 — 화면 API 는 모르는 소속을 거부하므로 원장에 바로 적는다."""
    c = portal
    app.state.user_store.set_access("user@corp.com", affiliation="GONE-TEAM", grants=["plat:mxwhitepaper"])
    h = _login(c, "user@corp.com")
    mx = _claims(c, "mx-white-paper", h)
    assert "affiliation" not in mx


def test_추적된_카탈로그에서_소속을_싣는_시스템은_MX_백서뿐이다():
    """늘리려면 그 앱이 소속을 쓰는지 확인하고 여기를 같이 고친다 — 쓰지 않는 앱에 소속이 퍼지지 않게."""
    cat = CatalogFile.model_validate(yaml.safe_load((_CONFIG / "systems.yaml").read_text(encoding="utf-8")))
    assert [s.id for s in cat.systems if s.claims_affiliation] == ["mx-white-paper"]


def test_HP40_떠_있는_카탈로그의_소속_싣는_시스템을_health_ready_가_말한다(portal):
    """점검은 파일(update-preflight)만 봤다 — 박스 파일이 덮은 뒤의 떠 있는 값은 볼 길이 없었다(docs/request-1027 HP-40)."""
    r = portal.get("/health/ready")
    assert r.status_code == 200 and r.json()["claims_affiliation"] == ["mx-white-paper"], r.json()
