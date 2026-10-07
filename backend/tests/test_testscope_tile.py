# TestScope 타일 — 다른 조직 포털이라 그쪽 주소로 여는 직결 링크, 주소(systems.local.yaml)가 없는 박스에서는 숨긴다(docs/sso-delegation)
"""TestScope 는 그쪽 주소로 노출되는 남의 포털이다 — 로그인 토큰을 넘기는 핸드오프가 아니라 external-url 이다. 주소는 사내
주소라 추적 파일에 적지 않고 박스별 systems.local.yaml 에 둔다. 없는 박스가 정상이므로 '곧 공개' 카드로도 안 보이게 숨기고,
경고 대신 안내 한 줄만 남긴다. 다른 타일의 규칙은 그대로다.

주소는 문서용 예약 대역(TEST-NET)만 쓴다 — 이 리포는 GitHub 에 있다.
"""
import logging
from pathlib import Path

import pytest
import yaml

from app.access.policy import load_raw, parse_policy
from app.catalog.registry import CatalogRegistry
from app.config import Settings
from app.schemas.system import LinkedSystem

_BACKEND = Path(__file__).resolve().parents[1]
_SYSTEMS = _BACKEND / "config" / "systems.yaml"
_ADDR = "http://192.0.2.20:8020/"


def _reg(tmp_path: Path, overlay: str | None = None) -> CatalogRegistry:
    """추적된 systems.yaml 그대로, 덮어쓰기만 시험이 정한다(이 박스의 실제 local 파일을 읽지 않는다)."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "systems.yaml").write_text(_SYSTEMS.read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "routes.env").write_text("", encoding="utf-8")
    if overlay is not None:
        (tmp_path / "systems.local.yaml").write_text(overlay, encoding="utf-8")
    return CatalogRegistry(Settings(_env_file=None, catalog_path=str(tmp_path / "systems.yaml"),
                                    routes_path=str(tmp_path / "routes.env")))


@pytest.fixture(autouse=True)
def _no_env_route(monkeypatch):
    monkeypatch.delenv("SYS_TESTSCOPE_URL", raising=False)


def test_tracked_entry_is_an_external_link_without_address_or_handoff_bits():
    """주소는 박스별 파일에 — 추적 파일에 사내 주소를 적지 않는다. 로그인 토큰을 넘기지 않으므로 audience 도 없다."""
    raw = yaml.safe_load(_SYSTEMS.read_text(encoding="utf-8"))
    (ts,) = [s for s in raw["systems"] if s["id"] == "testscope"]
    assert ts["integration_type"] == "external-url" and ts.get("hide_unless_routed") is True
    assert "url" not in ts and "audience" not in ts


def test_without_an_address_testscope_is_hidden_not_coming_soon(tmp_path, caplog):
    with caplog.at_level(logging.INFO, logger="app.catalog.registry"):
        reg = _reg(tmp_path)
    t = reg.get("testscope")
    assert (t.status, t.enabled) == ("coming_soon", False)
    assert "testscope" not in {s.id for s in reg.visible_for(["portal-admin"])}, "'곧 공개' 카드로도 안 보인다"
    assert "testscope" not in reg.live_ids()
    mine = [r for r in caplog.records if "testscope" in r.getMessage()]
    assert len(mine) == 1 and mine[0].levelno == logging.INFO, "없는 박스가 정상 — 경고가 아니라 안내 한 줄"
    assert "systems.local.yaml" in mine[0].getMessage(), "켜는 법을 말한다"


def test_an_overlay_address_makes_it_an_available_external_link(tmp_path):
    reg = _reg(tmp_path, f"testscope:\n  url: {_ADDR}\n")
    t = reg.get("testscope")
    assert (t.status, t.enabled, t.integration_type, t.url) == ("available", True, "external-url", _ADDR)
    assert "testscope" in reg.live_ids()
    assert "testscope" in {s.id for s in reg.visible_for(["portal-admin"])}


def test_other_tiles_are_unchanged(tmp_path):
    """TestScope 주소를 넣고 빼도 다른 타일의 상태·모드·주소는 그대로다 — 숨김 규칙이 번지지 않는다."""
    def snap(reg):
        return {s.id: (s.status, s.enabled, s.integration_type, s.url) for s in reg.all() if s.id != "testscope"}
    assert snap(_reg(tmp_path / "a")) == snap(_reg(tmp_path / "b", f"testscope:\n  url: {_ADDR}\n"))
    ra = _reg(tmp_path / "c").get("report-archive")
    assert ra.integration_type == "jwt-handoff" and not ra.hide_unless_routed
    assert (ra.status, ra.enabled) == ("available", True), "핸드오프 타일은 콜백 url 로 켜진다"


def test_hide_unless_routed_is_only_for_proxy_and_external_url():
    LinkedSystem(id="a", name="a", integration_type="external-url", hide_unless_routed=True)
    LinkedSystem(id="b", name="b", integration_type="proxy", hide_unless_routed=True)
    for kind in ("jwt-handoff", "saml-handoff"):
        with pytest.raises(ValueError, match="external-url"):
            LinkedSystem(id="x", name="x", integration_type=kind, url="/x/cb", hide_unless_routed=True)


def test_testscope_is_gated_by_its_own_platform():
    """게이트웨이 testscope 백엔드는 이 권한으로 막힌다 — 표에 없는 백엔드는 '전체 공개' 다."""
    pol = parse_policy(load_raw(_BACKEND / "config" / "access.yaml"))
    assert pol.system_key("testscope") == "plat:testscope"
    assert pol.gateway_policy()["testscope"] == ["plat:testscope"]
    assert pol.hidden_keys(set()) >= {"plat:testscope"}, "TestScope 가 없는 박스에서는 권한 표에서도 뺀다"
    assert "plat:testscope" not in pol.hidden_keys({"testscope"})
