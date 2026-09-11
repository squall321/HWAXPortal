# 전문가 심층 보기 프록시 — 그룹은 로그인 주체의 것, 실패는 빈 목록이 아니라 오류
import json

import httpx


def _client_with(handler, groups):
    from fastapi.testclient import TestClient

    from app.auth.provider import Principal
    from app.deps import principal_pat_or_session
    from app.main import app

    app.dependency_overrides[principal_pat_or_session] = lambda: Principal(
        subject="u1", email="u1@hwax.local", display_name="U", groups=groups
    )
    return app, TestClient(app), principal_pat_or_session


def test_지식카드_목록과_카드_한_장을_그룹과_함께_포워딩한다():
    seen: list = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append((req.url.path, json.loads(req.content)))
        if req.url.path.endswith("/records"):
            return httpx.Response(
                200, json={"total": 2729, "offset": 50, "items": [{"id": "DOC-1"}]}
            )
        return httpx.Response(
            200, json={"id": "DOC-1", "sections": [{"title": "본문", "text": "t"}]}
        )

    app, c, dep = _client_with(handler, ["analyst", "feat:expert-chat"])
    try:
        with c:
            real = app.state.agent_client
            app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            try:
                r1 = c.post(
                    "/agent/catalog/agent/records",
                    json={"key": "material-twin-analyst", "q": "SiC", "offset": 50, "limit": 50},
                )
                r2 = c.post("/agent/catalog/record", json={"id": "DOC-1"})
                bad = c.post("/agent/catalog/agent/records", json={"key": "x", "limit": 5000})
            finally:
                app.state.agent_client = real
        assert r1.json()["total"] == 2729 and r2.json()["sections"][0]["text"] == "t"
        # 그룹은 로그인 주체의 것 — 프론트가 보낸 값을 믿지 않는다.
        grp = ["analyst", "feat:expert-chat"]
        assert seen[0] == (
            "/catalog/agent/records",
            {"key": "material-twin-analyst", "q": "SiC", "offset": 50, "limit": 50, "groups": grp},
        )
        assert seen[1] == ("/catalog/record", {"id": "DOC-1", "groups": grp})
        assert bad.status_code == 422, "한 쪽 100건 상한 — 수천 건을 한 번에 당기지 못하게"
    finally:
        app.dependency_overrides.pop(dep, None)


def test_에이전트서버_실패는_빈_목록이_아니라_오류로_보인다():
    def boom(req: httpx.Request) -> httpx.Response:
        return httpx.Response(502)

    app, c, dep = _client_with(boom, ["feat:expert-chat"])
    try:
        with c:
            real = app.state.agent_client
            app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(boom))
            try:
                r1 = c.post("/agent/catalog/agent/records", json={"key": "x"}).json()
                r2 = c.post("/agent/catalog/record", json={"id": "DOC-1"}).json()
            finally:
                app.state.agent_client = real
        assert r1["error"] == "agent_502" and r1["items"] == []
        assert r2["error"] == "agent_502"
    finally:
        app.dependency_overrides.pop(dep, None)
