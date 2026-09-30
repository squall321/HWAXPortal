# 외부 타일의 사내 주소는 추적 파일(systems.yaml)이 아니라 박스별 덮어쓰기(systems.local.yaml, gitignore)에서 온다
#
# 주소는 문서용 예약 대역(TEST-NET)만 쓴다 — 이 리포는 GitHub 에 있다.
import logging

from app.catalog.registry import CatalogRegistry
from app.config import Settings


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
    from pathlib import Path
    src = (Path(__file__).resolve().parents[2] / "infra/scripts/deploy-all-from-drive.sh").read_text()
    line = next(ln for ln in src.splitlines() if "_cur=\"$(_fp_git; hwax_fp" in ln)
    assert "backend/config/systems.local.yaml" in line and "backend/config/routes.local.env" in line
