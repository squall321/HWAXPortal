# 화면의 뷰어 카드 — 같은 출처 /apps/<앱>/… 경로 판정 · 포인터 거르기 · 저장 · 되살리기와 카드 iframe 의 격리(docs/chat-embeds)
"""사용자 결정 11-05(CE-1) — 도구가 준 같은 출처 화면을 답 아래 격리 창으로. 화면은 SSE embeds 의 items · 서버 사본 meta.embeds · 브라우저 사본을 같은 규칙
(chatStore.isEmbedPath — 포털 app/agent/embeds.py 와 같다)으로 다시 거른다. 허브 앱은 포털과 같은 출처라 창은 sandbox="allow-scripts" 하나다(CE-2).

판정은 화면 코드를 CommonJS 로 옮겨 node 로 돌린다(tests/test_front_window_payload.py 의 _node). 격리 · 배선은 소스로 단언한다."""
import re
import shutil

import pytest

from tests.test_front_window_payload import _FE, _SRC, _node

pytestmark = pytest.mark.skipif(
    not (_FE / "node_modules/typescript").exists() or not shutil.which("node"),
    reason="frontend node_modules(typescript) 또는 node 가 없다 — 화면 조각을 돌려 볼 수 없다",
)

ATLAS = "/apps/step_forge/view/p1/atlas"


def _store(script: str, data=None):
    return _node(["state/chatStore.ts"], "const m = require('./state/chatStore.js');" + script, data)


def test_경로_판정은_포털_중계와_같다():
    cases = [ATLAS, "/apps/step_forge/view/p1/atlas?x=1", "https://host/apps/x/v", "/apps/x/../admin", "/apps/x/%2E%2E/a",
             "/apps/x//e", "//e/apps/x/", "/apps/x/a b", "/apps/X/v", "/agent/x", "/apps/x/a#f", "", None, 7]
    got = _store("out(input.map(m.isEmbedPath));", cases)
    assert got == [True, True, False, False, False, False, False, False, False, False, False, False, False, False], list(zip(cases, got))


def test_포인터_거르기는_규칙_밖을_버리고_같은_주소는_하나_여덟까지():
    items = [{"app": "step_forge", "tool": "section_atlas", "url": ATLAS, "title": "단면 지도"}, {"url": ATLAS},
             {"url": "/apps/x/../a"}, "글", {"app": "BAD APP", "tool": "t", "url": "/apps/doc_forge/view/z"}]
    items += [{"url": f"/apps/a/view/{i}"} for i in range(20)]
    got = _store("out(m.embedsFromMeta(input));", items)
    assert got[0] == {"app": "step_forge", "tool": "section_atlas", "url": ATLAS, "title": "단면 지도"}
    assert got[1] == {"app": "doc_forge", "tool": "t", "url": "/apps/doc_forge/view/z", "title": "doc_forge · t"}
    assert len(got) == 8 and len({p["url"] for p in got}) == 8
    assert _store("out([m.embedsFromMeta([]) ?? null, m.embedsFromMeta('x') ?? null]);") == [None, None]


def _src(rel: str) -> str:
    return (_SRC / rel).read_text(encoding="utf-8")


def test_카드_창은_allow_scripts_하나다():
    """같은 출처(allow-same-origin)를 주면 허브 앱 스크립트가 포털 쿠키 · 저장소에 닿는다 — 창 열기 · 폼 · 최상위 이동도 주지 않는다."""
    frames = re.findall(r"<iframe\b[^>]*?/>", _src("components/chat/EmbedCard.tsx"), flags=re.S)
    assert len(frames) == 1, frames
    assert 'sandbox="allow-scripts"' in frames[0] and "allow-same-origin" not in frames[0] and "allow-top" not in frames[0], frames[0]
    assert 'referrerPolicy="no-referrer"' in frames[0], frames[0]
    assert "isEmbedPath(e.url)" in _src("components/chat/EmbedCard.tsx"), "그리기 직전에 다시 거른다"


def test_배선_사건에서_카드까지():
    api = _src("api/chat.api.ts")
    assert re.search(r"case 'embeds':\s*h\.onEmbeds\?\.\(", api), "SSE embeds 를 나눠 준다"
    ctx = _src("state/ChatContext.tsx")
    assert re.search(r"onEmbeds: \(e\) => \{\s*const list = embedsFromMeta\(e\?\.items\);", ctx) and "embedsLive: true" in ctx
    assert "<EmbedCards embeds={msg.embeds} live={Boolean(msg.embedsLive)} />" in _src("components/chat/MessageList.tsx")
    conv = _src("api/conversations.api.ts")
    assert "embedsFromMeta((m.meta as { embeds?: unknown } | null)?.embeds)" in conv, "서버 사본 meta.embeds 를 되살린다"
    store = _src("state/chatStore.ts")
    assert "...(m.embeds?.length ? { embeds: m.embeds.slice(0, 8) } : {})" in store and "embedsLive" not in store.split("export function embedsFromMeta")[0].split("interface StoredMessage")[1], \
        "브라우저 사본에 포인터는 남기고 '이 탭에서 받음' 표지는 남기지 않는다"
