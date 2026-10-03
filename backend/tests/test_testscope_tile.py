# TestScope 타일 — `testscope=` 라우트가 있는 박스에서만 켜고, 없으면 '곧 공개' 로도 안 보인다(docs/sso-delegation)
"""jwt-handoff 타일은 콜백 url(`/testscope/api/auth/portal-callback`)이 yaml 에 늘 있다. 종전 규칙(라우트 또는 url 이면 켠다)
그대로면 TestScope 가 없는 박스에서도 타일이 열리고, 누르면 없는 서비스로 서명된 로그인 토큰을 보낸다 — nginx catch-all 이
SPA 를 200 으로 돌려 조용히 깨진다. 그래서 `hide_unless_routed` 를 jwt-handoff 에도 쓰고, 그때는 **라우트로만** 켠다.
다른 핸드오프 타일(report-archive 등)의 규칙은 그대로다.
"""
from pathlib import Path

import pytest
import yaml

from app.access.policy import parse_policy
from app.catalog.registry import CatalogRegistry
from app.config import Settings
from app.schemas.system import LinkedSystem

_BACKEND = Path(__file__).resolve().parents[1]
_ENV = "SYS_TESTSCOPE_URL"
_CALLBACK = "/testscope/api/auth/portal-callback"


def _reg(tmp_path: Path, routes: str = "", local: str | None = None) -> CatalogRegistry:
    base = tmp_path / "routes.env"
    base.write_text(routes, encoding="utf-8")
    if local is not None:
        (tmp_path / "routes.local.env").write_text(local, encoding="utf-8")
    return CatalogRegistry(Settings(routes_path=str(base)))


def _ts(reg: CatalogRegistry) -> LinkedSystem:
    return reg.get("testscope")


@pytest.fixture(autouse=True)
def _no_env_route(monkeypatch):
    monkeypatch.delenv(_ENV, raising=False)


def test_unrouted_testscope_is_hidden_not_coming_soon(tmp_path):
    reg = _reg(tmp_path, "report-archive=http://127.0.0.1:3000/\n", local="# testscope=http://x:8020/\n")
    t = _ts(reg)
    assert (t.status, t.enabled) == ("coming_soon", False)
    assert "testscope" not in {s.id for s in reg.visible_for(["portal-admin"])}, "'곧 공개' 카드로도 안 보인다"
    assert "testscope" not in reg.live_ids()


@pytest.mark.parametrize("where", ["local", "base", "env"])
def test_routed_testscope_is_available_and_keeps_its_callback(tmp_path, monkeypatch, where):
    """라우트는 nginx 프록시 목적지일 뿐이다 — 로그인 토큰을 보내는 콜백 url 을 덮지 않고, 모드도 그대로 jwt-handoff 다."""
    route = "testscope=http://127.0.0.1:8020/\n"
    if where == "env":
        monkeypatch.setenv(_ENV, "http://127.0.0.1:8020/")
        reg = _reg(tmp_path)
    else:
        reg = _reg(tmp_path, route if where == "base" else "", local=route if where == "local" else None)
    t = _ts(reg)
    assert (t.status, t.enabled, t.integration_type, t.url) == ("available", True, "jwt-handoff", _CALLBACK)
    assert "testscope" in reg.live_ids()


def test_an_empty_route_value_is_not_a_route(tmp_path):
    assert _ts(_reg(tmp_path, local="testscope=\n")).status == "coming_soon"


def test_other_handoff_tiles_are_unchanged(tmp_path):
    """report-archive 는 라우트가 없어도 콜백 url 로 켜진다 — 숨김 규칙이 다른 핸드오프 타일로 번지지 않는다."""
    reg = _reg(tmp_path)
    ra = reg.get("report-archive")
    assert ra.integration_type == "jwt-handoff" and not ra.hide_unless_routed
    assert (ra.status, ra.enabled) == ("available", True)
    others = [s for s in reg.all() if s.integration_type in ("jwt-handoff", "saml-handoff") and s.id != "testscope"]
    assert others and all(not s.hide_unless_routed for s in others), "숨김 표식은 testscope 에만 있다"
    assert all(s.status == "available" for s in others if s.url)


def test_hide_unless_routed_is_only_for_proxy_and_jwt_handoff():
    LinkedSystem(id="a", name="a", integration_type="jwt-handoff", url="/a/cb", hide_unless_routed=True)
    for kind in ("external-url", "saml-handoff"):
        with pytest.raises(ValueError, match="jwt-handoff"):
            LinkedSystem(id="x", name="x", integration_type=kind, url="http://x", hide_unless_routed=True)


def test_testscope_is_gated_by_its_own_platform():
    """게이트웨이 testscope 백엔드는 이 권한으로 막힌다 — 표에 없는 백엔드는 '전체 공개' 다."""
    pol = parse_policy(yaml.safe_load((_BACKEND / "config" / "access.yaml").read_text(encoding="utf-8")))
    assert pol.system_key("testscope") == "plat:testscope"
    assert pol.gateway_policy()["testscope"] == ["plat:testscope"]
    assert pol.hidden_keys(set()) >= {"plat:testscope"}, "TestScope 가 없는 박스에서는 권한 표에서도 뺀다"
    assert "plat:testscope" not in pol.hidden_keys({"testscope"})
