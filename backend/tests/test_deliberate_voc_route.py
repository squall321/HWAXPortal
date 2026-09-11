# 포털 'VOC 먼저 보기' 경로 — 에이전트서버로 무엇을 포워딩하는지, voc 손잡이가 모델을 통과하는지
import httpx


def test_voc_경로는_그룹과_검색어를_포워딩한다():
    from fastapi.testclient import TestClient

    from app.auth.provider import Principal
    from app.deps import principal_pat_or_session
    from app.main import app

    seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        import json
        seen["path"] = req.url.path
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json={"keywords": ["hinge"], "items": [{"id": 1, "text": "t"}]})

    app.dependency_overrides[principal_pat_or_session] = lambda: Principal(
        subject="u1", email="u1@hwax.local", display_name="U", groups=["analyst"])
    try:
        with TestClient(app) as c:
            real = app.state.agent_client
            app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            try:
                r = c.post("/agent/deliberate/voc",
                           json={"message": "폴드 힌지 파손", "keywords": [" hinge ", "", "crease"]})
            finally:
                app.state.agent_client = real
        assert r.status_code == 200 and r.json()["items"][0]["id"] == 1
        assert seen["path"] == "/deliberate/voc-preview"
        # 그룹은 로그인 주체의 것 — 프론트가 보낸 값을 믿지 않는다. 빈 검색어는 버린다.
        assert seen["body"] == {"message": "폴드 힌지 파손", "groups": ["analyst"], "keywords": ["hinge", "crease"]}
    finally:
        app.dependency_overrides.pop(principal_pat_or_session, None)


def test_voc_손잡이는_세_값만_통과한다():
    import pytest
    from pydantic import ValidationError

    from app.agent.routes import DelibOpts

    for v in ("auto", "off", "always"):
        assert DelibOpts(voc=v).model_dump(exclude_none=True)["voc"] == v
    with pytest.raises(ValidationError):
        DelibOpts(voc="sometimes")


def test_clarify_경로는_방법과_대화를_포워딩하고_실패는_묻지_않음이다():
    from fastapi.testclient import TestClient

    from app.auth.provider import Principal
    from app.deps import principal_pat_or_session
    from app.main import app

    seen = {}

    def ok(req: httpx.Request) -> httpx.Response:
        import json
        seen["path"], seen["body"] = req.url.path, json.loads(req.content)
        return httpx.Response(200, json={"applicable": True, "slots": [], "ask": ["condition"]})

    def boom(req: httpx.Request) -> httpx.Response:
        return httpx.Response(502)

    app.dependency_overrides[principal_pat_or_session] = lambda: Principal(
        subject="u1", email="u1@hwax.local", display_name="U", groups=[])
    try:
        with TestClient(app) as c:
            real = app.state.agent_client
            try:
                app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(ok))
                r = c.post("/agent/deliberate/clarify", json={
                    "message": "폴드 힌지 파손", "job": "diagnosis",
                    "history": [{"role": "user", "content": "낙하 1.5m"}]})
                assert r.json()["ask"] == ["condition"]
                assert seen["path"] == "/deliberate/clarify"
                assert seen["body"]["job"] == "diagnosis" and seen["body"]["history"][0]["content"] == "낙하 1.5m"
                app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(boom))
                assert c.post("/agent/deliberate/clarify", json={"message": "x"}).json()["ask"] == []
            finally:
                app.state.agent_client = real
    finally:
        app.dependency_overrides.pop(principal_pat_or_session, None)
