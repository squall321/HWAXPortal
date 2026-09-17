# Knox 킬 스위치 — knox-bridge 타일은 목적지(환경변수·routes 파일)가 있을 때만 available 이다
#
# 챗·심의 툴바의 메일 버튼(frontend ChatActionBar)은 이 타일이 available·proxy 일 때만 매니페스트를 읽는다.
# 그래서 이 판정이 곧 "Knox 연결 설정이 없는 환경에서는 꺼진다" 의 실행부다(docs/chat-actions A-1).
from pathlib import Path

import yaml

from app.access.policy import parse_policy
from app.catalog.registry import CatalogRegistry
from app.config import Settings

_BACKEND = Path(__file__).resolve().parents[1]
_ENV = "SYS_KNOX_BRIDGE_URL"


def _tile(tmp_path: Path, routes: str = "", local: str | None = None):
    base = tmp_path / "routes.env"
    base.write_text(routes, encoding="utf-8")
    if local is not None:
        (tmp_path / "routes.local.env").write_text(local, encoding="utf-8")
    reg = CatalogRegistry(Settings(routes_path=str(base)))
    return next(s for s in reg.all() if s.id == "knox-bridge")


def test_목적지가_없으면_coming_soon_이다(tmp_path, monkeypatch):
    monkeypatch.delenv(_ENV, raising=False)
    t = _tile(tmp_path, "report-archive=http://127.0.0.1:3000/\n", local="# knox-bridge=http://x/\n")
    assert t.integration_type == "proxy"
    assert t.status == "coming_soon", "Knox 연결 설정이 없는데 타일이 열린다 — 메일 버튼도 뜬다"


def test_환경변수가_있으면_available_이다(tmp_path, monkeypatch):
    monkeypatch.setenv(_ENV, "http://127.0.0.1:1/")
    t = _tile(tmp_path)
    assert (t.status, t.integration_type) == ("available", "proxy")


def test_routes_local_env_한_줄이면_available_이다(tmp_path, monkeypatch):
    monkeypatch.delenv(_ENV, raising=False)
    t = _tile(tmp_path, local="knox-bridge=http://127.0.0.1:1/\n")
    assert (t.status, t.integration_type) == ("available", "proxy")


def test_빈_값은_목적지가_아니다(tmp_path, monkeypatch):
    monkeypatch.setenv(_ENV, "")
    t = _tile(tmp_path, local="knox-bridge=\n")
    assert t.status == "coming_soon"


def test_추적_routes_파일에는_knox_목적지가_없다():
    """사내 목적지를 git 추적 routes 파일에 적으면 사외·dev 에서도 타일이 열린다(킬 스위치 무력화)."""
    for name in ("routes.env", "routes.prod.env"):
        p = _BACKEND / "config" / name
        if not p.exists():
            continue
        live = [
            ln
            for ln in p.read_text(encoding="utf-8").splitlines()
            if ln.strip().startswith("knox-bridge") and "=" in ln and ln.split("=", 1)[1].strip()
        ]
        assert not live, f"{name} 에 knox-bridge 목적지가 있다 — routes.local.env(gitignore)에 둔다"


def test_타일은_knoxbridge_플랫폼_허가로만_보인다():
    pol = parse_policy(yaml.safe_load((_BACKEND / "config" / "access.yaml").read_text(encoding="utf-8")))
    assert pol.system_key("knox-bridge") == "plat:knoxbridge"


# ── Knox 가 없는 박스에서는 숨긴다(사용자 결정 2026-09-17) ─────────────────────────────────────
def test_목적지가_없으면_타일_목록에서_빠진다(tmp_path, monkeypatch):
    """coming_soon 카드로도 안 보인다 — 그 박스에서는 영영 열릴 일이 없다. 권한 대조는 계속 표에 남는다."""
    monkeypatch.delenv(_ENV, raising=False)
    base = tmp_path / "routes.env"
    base.write_text("", encoding="utf-8")
    reg = CatalogRegistry(Settings(routes_path=str(base)))
    admin = ["portal-admin"]
    assert "knox-bridge" not in {s.id for s in reg.visible_for(admin)}
    assert "knox-bridge" not in reg.live_ids()
    monkeypatch.setenv(_ENV, "http://127.0.0.1:1/")
    reg.reload()
    assert "knox-bridge" in {s.id for s in reg.visible_for(admin)} and "knox-bridge" in reg.live_ids()


def test_숨김은_proxy_타일과_타일_있는_플랫폼에만():
    import pytest
    from app.schemas.system import LinkedSystem

    with pytest.raises(ValueError, match="proxy"):
        LinkedSystem(id="x", name="x", integration_type="external-url", url="http://x", hide_unless_routed=True)
    with pytest.raises(ValueError, match="systems"):
        parse_policy({"platforms": [{"id": "p", "label": "p", "hide_unless_routed": True}]})


def test_플랫폼_숨김은_표시만이고_게이트웨이_정책은_그대로다():
    pol = parse_policy({"platforms": [
        {"id": "kb", "label": "K", "systems": ["knox-bridge"], "gateway": ["bridge"], "hide_unless_routed": True},
        {"id": "sf", "label": "S", "systems": ["step"], "gateway": ["heax-step_forge"]}]})
    assert pol.hidden_keys(set()) == {"plat:kb"}            # 숨김 표식이 없는 플랫폼은 늘 보인다
    assert pol.hidden_keys({"knox-bridge"}) == set()
    assert pol.gateway_policy()["bridge"] == ["plat:kb"], "숨긴 플랫폼도 게이트웨이 권한은 계속 막아야 한다"
