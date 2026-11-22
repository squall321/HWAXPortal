# 심의 준비 · 카탈로그 중계가 로그인 주체의 이메일을 '누구의 일' 로 싣는지 — 에이전트 서버가 그 창구의 LLM 토큰 · 서비스 자격 게이트웨이 호출을 이 사람의 것으로 센다(docs/ops-dashboard OD-52 · OD-53)
"""브라우저가 보낸 값이 아니라 검증된 주체의 이메일이어야 한다 — 본문에 user_email 을 적어 보내도 주체의 것으로 덮인다. 권한에는 쓰이지 않는다(에이전트 서버는
이 칸으로 자리만 단다). 계정은 example.com 시험 신원만 쓴다."""
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.auth.provider import Principal
from app.deps import principal_pat_or_session
from app.main import app

ME = "me@example.com"
CASES = [
    ("/agent/deliberate/experts", {"message": "힌지", "user_email": "forged@example.com"}, "/deliberate/experts"),
    ("/agent/deliberate/clarify", {"message": "힌지", "user_email": "forged@example.com"}, "/deliberate/clarify"),
    ("/agent/deliberate/topic", {"history": [{"role": "user", "content": "힌지"}], "fallback": "힌지", "user_email": "forged@example.com"},
     "/deliberate/topic"),
    ("/agent/deliberate/voc", {"message": "힌지", "user_email": "forged@example.com"}, "/deliberate/voc-preview"),
    ("/agent/catalog/agent", {"key": "k", "user_email": "forged@example.com"}, "/catalog/agent"),
    ("/agent/catalog/agent/records", {"key": "k", "user_email": "forged@example.com"}, "/catalog/agent/records"),
    ("/agent/catalog/record", {"id": "DOC-1", "user_email": "forged@example.com"}, "/catalog/record"),
]


@pytest.mark.parametrize(("route", "body", "upstream"), CASES)
def test_중계는_로그인_주체의_이메일을_누구의_일로_싣는다(route, body, upstream):
    seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["path"], seen["body"] = req.url.path, json.loads(req.content)
        return httpx.Response(200, json={})

    app.dependency_overrides[principal_pat_or_session] = lambda: Principal(
        subject=ME, email=ME, display_name="Me", groups=["feat:deliberation", "feat:expert-chat"])
    try:
        with TestClient(app) as c:
            real = app.state.agent_client
            app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            try:
                c.post(route, json=body)
            finally:
                app.state.agent_client = real
    finally:
        app.dependency_overrides.pop(principal_pat_or_session, None)
    assert seen["path"] == upstream and seen["body"]["user_email"] == ME, seen
