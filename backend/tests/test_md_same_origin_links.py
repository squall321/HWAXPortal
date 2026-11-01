# 챗 글의 같은 오리진 절대경로 링크([x](/…))가 링크로 그려지는지 — 발표자료 알림의 받기 링크 · 앱 산출물 영상(db0c364a 의 뜻)(docs/wda-deck)
"""왜 — db0c364a 가 링크 href 에 같은 오리진 절대경로를 허용했지만, 그 검사는 토큰을 고른 **뒤**의 정규식에만 들어가고 토큰을 고르는
RE_INLINE 은 여전히 http(s) 링크만 골랐다. 그래서 `[PPT 받기](/agent/deck/jobs/…/files/pptx)` · `[영상](/apps/…/download/video)` 이 글자 그대로
보였다(발표자료 알림의 받기 링크가 눌리지 않는다). 프로토콜 상대(//host) · 브라우저가 같게 읽는 /\\host · 스킴(javascript:)은 여전히 글이다
(/\\ 는 적대 검토가 찾았다 — docs/wda-deck WD-D44).
"""
from tests.test_front_window_payload import _node, pytestmark  # noqa: F401 — 같은 도구가 없으면 같이 건너뛴다


def _inline(texts: list[str]):
    return _node(["components/chat/renderers/md.ts"],
                 "const m = require('./components/chat/renderers/md.js'); out(input.map((s) => m.parseInline(s)));", texts)


def test_같은_오리진_절대경로는_링크다():
    got = _inline(["받기 — [PPT 받기](/agent/deck/jobs/abc/files/pptx) · 끝",
                   "[영상](/apps/web_design_agents/api/render_jobs/rj-1/download/video)"])
    assert got[0] == [{"t": "text", "s": "받기 — "}, {"t": "link", "s": "PPT 받기", "href": "/agent/deck/jobs/abc/files/pptx"},
                      {"t": "text", "s": " · 끝"}]
    assert got[1] == [{"t": "link", "s": "영상", "href": "/apps/web_design_agents/api/render_jobs/rj-1/download/video"}]


def test_프로토콜_상대와_스킴은_글로_남는다():
    got = _inline(["[x](//evil.example/a)", "[x](javascript:alert(1))", "[x](agent/deck)"])
    assert all(len(toks) == 1 and toks[0]["t"] == "text" for toks in got), got


def test_역슬래시로_시작하는_프로토콜_상대도_글이다():
    """브라우저는 /\\host 를 //host 로 읽는다(new URL('/\\evil.example/a', base) → https://evil.example/a). 주소 안의 \\ 도 받지 않는다."""
    got = _inline(["[다시 받기](/\\phish.example/login)", "[x](/\\\\evil.example/a)", "[x](/agent/deck\\..\\x)",
                   "[x](https://x.example/a\\b)"])
    assert all(len(toks) == 1 and toks[0]["t"] == "text" for toks in got), got


def test_http_링크와_그림은_그대로다():
    got = _inline(["[a](https://x.example/z)", "![g](/agent/artifacts/a.png)"])
    assert got[0] == [{"t": "link", "s": "a", "href": "https://x.example/z"}]
    assert got[1] == [{"t": "img", "s": "g", "href": "/agent/artifacts/a.png"}]
