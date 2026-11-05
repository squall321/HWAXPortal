# 뷰어 카드 — 포털 중계가 SSE embeds 를 화면에 그대로 넘기고 서버 사본에는 규칙에 맞는 포인터만 meta.embeds 로 남기는지(docs/chat-embeds)
"""사용자 결정 11-05 — 다른 플랫폼이 iframe 으로 보낸 화면을 챗에 띄운다(CE-1). 뷰어 카드는 같은 출처 /apps/<앱>/… 경로만 격리 창으로 — 에이전트 서버가
도구 결과에서 집어 SSE embeds 로 내고, 중계는 바이트를 그대로 흘리며(화면이 다시 거른다) 서버 사본에는 같은 규칙(app/agent/embeds.py)으로 거른 포인터만
남긴다. 중계 시험 도구는 test_mcp_apps_panel 의 것을 쓴다."""
import json

import httpx
import pytest

from app.agent import embeds as E
from app.main import app
from tests.test_mcp_apps_panel import _Turn, _login, _sse, kit  # noqa: F401  (kit 은 픽스처)

ATLAS = "/apps/step_forge/view/p1/atlas"


@pytest.mark.parametrize("url,ok", [
    (ATLAS, True), ("/apps/step_forge/view/p1/atlas?x=1", True), ("/apps/doc_forge/view/a-b", True),
    ("https://host/apps/step_forge/view/p1/atlas", False),   # 절대 주소는 에이전트 서버가 경로로 바꿔 보낸다 — 여기는 경로만
    ("/apps/x/../admin", False), ("/apps/x/%2e%2e/admin", False), ("/apps/x//evil", False), ("//evil/apps/x/", False),
    ("/apps/x/a b", False), ("/apps/x/\"q", False), ("/apps/x/<s>", False), ("/apps/X/view", False), ("/agent/x", False),
    ("/apps/x/a#frag", False), ("/apps/" + "a" * 70 + "/v", False), ("/apps/x/" + "a" * 2100, False), ("", False), (None, False),
])
def test_경로_규칙(url, ok):
    assert (E.safe_path(url) is not None) is ok, url
    if ok:
        assert E.safe_path(url) == url, "맞으면 그대로 돌려준다"


def test_포인터는_규칙에_맞는_것만_같은_주소는_하나_여덟까지():
    items = [{"app": "step_forge", "tool": "section_atlas", "url": ATLAS, "title": "단면 지도"}, {"url": ATLAS},
             {"url": "/apps/x/../admin"}, "글", {"app": "BAD APP", "tool": "t", "url": "/apps/doc_forge/view/z"}]
    items += [{"url": f"/apps/a/view/{i}"} for i in range(20)]
    got = E.pointers(items)
    assert got[0] == {"app": "step_forge", "tool": "section_atlas", "url": ATLAS, "title": "단면 지도"}
    assert got[1] == {"app": "doc_forge", "tool": "t", "url": "/apps/doc_forge/view/z", "title": "doc_forge · t"}, "앱 이름이 틀리면 경로의 앱 마디"
    assert len(got) == E.MAX_ITEMS and len({p["url"] for p in got}) == E.MAX_ITEMS


def _turn(c, h, items):
    def upstream(req):
        return httpx.Response(200, stream=_Turn([_sse("token", {"delta": "지도입니다"}), _sse("embeds", {"items": items}),
                                                 _sse("result", {"type": "text", "content": "지도입니다"}), _sse("done", {})]),
                              headers={"content-type": "text/event-stream"})
    real = app.state.agent_client
    app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(upstream))
    try:
        cid = c.post("/agent/conversations", json={"title": "t"}, headers=h).json()["id"]
        with c.stream("POST", "/agent/chat", json={"message": "지도 보여줘", "conversation_id": cid}, headers=h) as r:
            text = "".join(r.iter_text())
        msgs = c.get(f"/agent/conversations/{cid}", headers=h).json()["messages"]
    finally:
        app.state.agent_client = real
    return text, msgs


def test_중계는_사건을_넘기고_서버_사본에는_규칙에_맞는_포인터만_남긴다(kit):
    c, _gw, _s = kit()
    h = _login(c, "boss@corp.com")
    items = [{"app": "step_forge", "tool": "section_atlas", "url": ATLAS, "title": "단면 지도"},
             {"app": "x", "tool": "t", "url": "https://evil.example/apps/x/view"}, {"url": "/apps/x/../admin"}, {"url": ATLAS}]
    text, msgs = _turn(c, h, items)
    assert "event: embeds" in text and "evil.example" in text, "중계는 바이트를 그대로 넘긴다(화면이 다시 거른다)"
    meta = [m for m in msgs if m["role"] == "assistant"][-1]["meta"]
    assert meta["embeds"] == [{"app": "step_forge", "tool": "section_atlas", "url": ATLAS, "title": "단면 지도"}]
    assert "evil.example" not in json.dumps(msgs, ensure_ascii=False), "서버 사본에는 규칙 밖 주소가 없다"


def test_규칙에_맞는_것이_없으면_meta_에_칸을_만들지_않는다(kit):
    c, _gw, _s = kit()
    h = _login(c, "boss@corp.com")
    _t, msgs = _turn(c, h, [{"url": "/agent/artifacts/x.svg"}])
    assert "embeds" not in ([m for m in msgs if m["role"] == "assistant"][-1]["meta"] or {})
