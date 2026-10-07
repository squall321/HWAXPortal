# 포털 로그아웃이 SPA 에 내려주는 하위 서비스 로그아웃 목록 — 이 박스에 라우트가 있는 핸드오프 타일만 싣는다
"""포털은 로그아웃 때 "어느 하위 서비스의 로그아웃을 쳐야 하는지" 만 알려 주고 SPA 가 그 주소들을 POST 한다. 목록은 콜백 url 이
있는 타일에서 유도하는데 **이 박스에 그 서비스가 붙어 있는지**는 보지 않았다. AI Ready Portal 타일이 핸드오프가 되면서
(8517dd5) 추적 파일에 콜백 url 이 생겼고, 라우트가 없는 박스(dev·새 박스)에서 매 로그아웃마다 `/aireadyportal/api/auth/logout`
이 실렸다 — nginx 에 그 location 이 없어 POST 는 포털 자신이 받고 405 로 확정 실패한다. 같은 함수의 주석이 말하는
'늘 울리는 경보' 다(진짜 실패를 아무도 안 본다).

추적 파일(systems.yaml·access.yaml)의 사본과 지어낸 라우트 파일로 카탈로그를 만들어 실제 라우트를 부른다. 박스 파일은 읽지 않는다.
"""
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.access.policy import AccessPolicy
from app.auth.cookies import CSRF_COOKIE
from app.auth.user_store import UserStore
from app.catalog.registry import CatalogRegistry
from app.config import Settings, get_settings
from app.main import app

_CONFIG = Path(__file__).resolve().parents[1] / "config"
# dev 의 추적 라우트 모양 — 화면과 API 가 따로 붙는 서비스는 키가 `<id>/api` 다
_BASE = ("heax-hub=http://127.0.0.1:1/\nai-data-hub=http://127.0.0.1:2/\nmx-white-paper/api=http://127.0.0.1:3/api/\n"
         "signalforge/api=http://127.0.0.1:4/api/\n")


@pytest.fixture()
def logout_list(tmp_path):
    for name in ("systems.yaml", "access.yaml"):
        shutil.copy(_CONFIG / name, tmp_path / name)

    def run(routes: str, *, local: str | None = None) -> list[str]:
        (tmp_path / "routes.env").write_text(routes)
        if local is not None:
            (tmp_path / "routes.local.env").write_text(local)
        s = Settings(_env_file=None, user_store_path=str(tmp_path / "users.sqlite"), local_bootstrap_admins="boss@corp.com",
                     catalog_path=str(tmp_path / "systems.yaml"), routes_path=str(tmp_path / "routes.env"),
                     access_path=str(tmp_path / "access.yaml"))
        app.dependency_overrides[get_settings] = lambda: s
        from app.auth.routes.local import _rl
        _rl.clear()
        try:
            with TestClient(app) as c:
                keep = (app.state.user_store, app.state.access, app.state.catalog)
                # 기동 뒤 교체 — 실 원장·박스의 카탈로그를 안 쓴다
                app.state.user_store, app.state.access, app.state.catalog = UserStore(s), AccessPolicy(s), CatalogRegistry(s)
                try:
                    c.post("/auth/local/signup", json={"email": "boss@corp.com", "name": "boss", "password": "pw123456"})
                    assert c.post("/auth/local/login", json={"email": "boss@corp.com", "password": "pw123456"}).status_code == 200
                    r = c.post("/auth/logout", headers={"X-CSRF-Token": c.cookies.get(CSRF_COOKIE)})
                    assert r.status_code == 200, r.text
                    return r.json()["downstream_logout"]
                finally:
                    app.state.user_store, app.state.access, app.state.catalog = keep
        finally:
            app.dependency_overrides.pop(get_settings, None)
    return run


def test_라우트가_없는_타일의_로그아웃은_싣지_않는다(logout_list):
    """**이 파일의 이유다** — 종전엔 라우트가 없어도 /aireadyportal/ 과 /report-archive/ 가 실렸다."""
    outs = logout_list(_BASE)
    assert outs == ["/heax-hub/api/v1/auth/logout-session", "/mx-white-paper/api/v1/auth/logout",
                    "/signalforge/api/v1/auth/logout"], outs


def test_라우트가_있으면_싣는다_박스_파일의_라우트도_같다(logout_list):
    """ARP 의 /api/auth/logout 은 있는지 확인된 적이 없다 — 그래도 라우트가 있는 박스에서는 친다. 빼면 '못 끊고 조용하다' 가 된다."""
    outs = logout_list(_BASE + "aireadyportal=http://203.0.113.20:3001/\n")
    assert "/aireadyportal/api/auth/logout" in outs
    outs = logout_list(_BASE, local="aireadyportal=http://203.0.113.20:3001/\nreport-archive=http://203.0.113.10:3000/\n")
    assert "/aireadyportal/api/auth/logout" in outs and "/report-archive/api/auth/logout" in outs
    assert not any("/ai-data-hub/" in u for u in outs), "로그아웃 경로가 없는 서비스는 라우트가 있어도 종전대로 뺀다"


def test_같은_콜백을_쓰는_타일은_한_번만_친다(logout_list):
    """리스크 심사 타일은 heax-hub 의 콜백을 같이 쓴다 — 같은 주소가 두 번 실려 로그아웃마다 두 번 쳤다."""
    outs = logout_list(_BASE)
    assert outs.count("/heax-hub/api/v1/auth/logout-session") == 1, outs


def test_라우트가_하나도_없으면_목록은_비어_있다(logout_list):
    assert logout_list("") == []
