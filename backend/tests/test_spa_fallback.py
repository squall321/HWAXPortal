# SPA 폴백이 **API 오류를 삼키지 않는지** — 그리고 깊은 링크는 그대로 사는지
#
# 백엔드가 SPA 를 함께 내므로 catch-all 이 하나 있다. 그냥 두면 `/auth/오타` 가
# **200 + HTML** 로 돌아온다 — 호출부는 res.ok 를 보고 성공으로 알았다가 한참 뒤
# JSON 파싱에서 엉뚱한 자리에서 터진다. 이 리포가 반복해서 만난 모양 그대로다.
#
# 고치면서 생긴 새 위험은 반대쪽이다. 접두사를 잘못 잡으면 **사용자의 깊은 링크가
# 새로고침에서 404** 가 된다. 그래서 여기서 두 개를 같이 건다 —
#   ① 없는 API 경로는 JSON 404 다.
#   ② SPA 경로 이름과 백엔드 접두사는 **한 칸도 겹치지 않는다**(②가 ①의 안전장치다).
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
APP_TSX = BACKEND.parent / "frontend" / "src" / "App.tsx"


def _api_segments() -> set[str]:
    """등록된 라우트의 첫 칸 — main.py 가 유도하는 것과 같은 집합이다."""
    from app.main import app

    return {
        r.path.split("/")[1]
        for r in app.routes
        if getattr(r, "path", "").startswith("/") and "{full_path" not in r.path
    } - {""}


def _spa_segments() -> set[str]:
    """React Router 표에서 첫 칸만 — `/launch/:id` 는 `launch`, `/procedures/*` 는 `procedures`."""
    src = APP_TSX.read_text(encoding="utf-8")
    paths = re.findall(r"path:\s*'([^']+)'", src)
    assert paths, "App.tsx 에서 라우트를 하나도 못 읽었다 — 표 모양이 바뀌었는지 본다"
    return {p.split("/")[1] for p in paths if p.startswith("/")} - {"", "*"}


# ── ② 안전장치: 두 이름 공간이 겹치지 않는다 ────────────────────────────────
def test_spa_routes_and_api_prefixes_never_collide():
    """겹치는 순간 그 SPA 화면은 **새로고침에서 죽는다**. 라우터를 더할 때 여기서 걸린다.

    지금 지켜지는 이유는 우연이 아니다 — `/procedures`(SPA) 와 `/procedures-api`(API) 를
    일부러 갈라 놓았고, `/updates`(SPA) 와 `/changelog`(API) 도 같은 이유로 이름이 다르다.
    """
    overlap = _api_segments() & _spa_segments()
    assert not overlap, (
        f"SPA 경로와 API 접두사가 겹친다: {sorted(overlap)} — "
        "이 화면은 새로고침하면 404 가 된다. 접두사 이름을 갈라라."
    )


def test_spa_route_table_is_actually_being_read():
    """위 테스트가 **빈 집합끼리 비교해** 통과하는 사고를 막는다."""
    spa, api = _spa_segments(), _api_segments()
    assert {"procedures", "deliberate", "login"} <= spa, f"SPA 표를 잘못 읽었다: {sorted(spa)}"
    assert {"auth", "procedures-api"} <= api, f"API 표를 잘못 읽었다: {sorted(api)}"


# ── ① 본 동작: 없는 API 경로는 JSON 404 ─────────────────────────────────────
_PROBE = r"""
import json, sys
from fastapi.testclient import TestClient
from app.main import app

c = TestClient(app)
out = {}
for label, path in [
    ("api_typo", "/auth/이런경로는없다"),
    ("api_typo_nested", "/procedures-api/seeds/zzz/nope"),
    ("spa_deep", "/procedures/saved"),
    ("spa_root", "/deliberate"),
    ("spa_index", "/"),
    ("api_real", "/health"),
]:
    r = c.get(path)
    out[label] = {"code": r.status_code, "ctype": r.headers.get("content-type", "")}
print(json.dumps(out))
"""


@pytest.fixture(scope="module")
def probe(tmp_path_factory) -> dict:
    """`serve_frontend` 는 기본이 꺼짐이라 폴백이 아예 안 달린다 — 켜서 **따로** 세운다.

    같은 프로세스에서 reload 하면 다른 테스트가 쥔 앱과 섞인다. 자식 프로세스가 싸다.

    ⚠ **빌드 산출물에 매지 않는다.** 예전엔 `frontend/dist/index.html` 이 없으면
    skip 했는데, `dist` 는 gitignore 라 보통 없다 — 즉 이 파일의 세 검사(이게 이 리포에서
    API 404 대 SPA 200 을 보는 **유일한** 자리다)가 평소엔 통째로 꺼져 있었다.
    누가 `pnpm build` 를 돌렸는지에 따라 켜지고 꺼지는 검사는 검사가 아니다.
    두 줄짜리 가짜 dist 를 만들어 쓴다 — 폴백이 보는 것은 파일의 **존재**이지 내용이 아니다.
    """
    dist = tmp_path_factory.mktemp("dist")
    (dist / "assets").mkdir()
    (dist / "index.html").write_text("<!doctype html><title>stub</title>", encoding="utf-8")
    r = subprocess.run(
        [sys.executable, "-c", _PROBE],
        cwd=BACKEND,
        env={"PATH": "/usr/bin:/bin", "HOME": str(Path.home()), "SERVE_FRONTEND": "true",
             "FRONTEND_DIST": str(dist)},
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, f"탐침이 죽었다:\n{r.stderr[-2000:]}"
    return json.loads(r.stdout.strip().splitlines()[-1])


def test_unknown_api_path_is_a_json_404_not_an_html_200(probe):
    """**이 한 줄이 요점이다.** 200+HTML 로 오면 호출부가 성공으로 읽는다."""
    for key in ("api_typo", "api_typo_nested"):
        got = probe[key]
        assert got["code"] == 404, f"{key}: {got} — API 오탈자가 SPA 로 샜다"
        assert "json" in got["ctype"], f"{key}: {got} — 404 는 맞는데 본문이 HTML 이다"


def test_spa_deep_links_still_serve_the_app(probe):
    """고치면서 이쪽을 깨뜨리면 사용자가 즉시 본다 — 새로고침이 404 가 된다."""
    for key in ("spa_deep", "spa_root", "spa_index"):
        got = probe[key]
        assert got["code"] == 200 and "html" in got["ctype"], f"{key}: {got}"


def test_real_api_route_is_untouched(probe):
    assert probe["api_real"]["code"] == 200
