# 챗 뷰어 카드 포인터 — 에이전트 서버의 SSE embeds 를 같은 규칙으로 걸러 답 meta.embeds 로 남긴다(docs/chat-embeds CE-2)
"""뷰어 카드는 같은 출처 `/apps/<앱>/…` 경로만 격리 창(sandbox="allow-scripts")으로 띄운다. 에이전트 서버가 도구 결과에서 집어 SSE `embeds` 로 내고(중계는 그 바이트를
그대로 화면에 흘린다), 여기는 서버 사본(답 meta)에 남길 것을 거른다 — 화면도 같은 규칙으로 다시 거른다. 세 층의 규칙은 docs/chat-embeds/PLAN.md 1절이다."""
from __future__ import annotations

import re

# /apps/<앱>/ 로 여는 경로 — 따옴표 · 꺾쇠 · 공백 · 역슬래시 · # 은 글자 집합에 없다. 질의는 하나.
_SAFE_PATH = re.compile(r"/apps/[a-z0-9][a-z0-9_-]{0,63}/[A-Za-z0-9._~!$&()*+,;=:@/%-]*(?:\?[A-Za-z0-9._~!$&()*+,;=:@/?%-]*)?")
# 경로를 벗어나는 꼴 — 점 마디 · 겹 빗금 · 인코딩한 점 · 빗금 · 역슬래시(브라우저는 %2e 를 점 마디로 푼다)
_ESCAPE = re.compile(r"(?:^|/)\.\.?(?:/|$|\?)|//|%2e|%2f|%5c", re.I)
_APP = re.compile(r"[a-z0-9][a-z0-9_.-]{0,63}")
MAX_URL = 2048
MAX_ITEMS = 8


def safe_path(url: object) -> str | None:
    """카드로 띄울 수 있는 같은 출처 경로면 그대로, 아니면 None."""
    if not isinstance(url, str) or not url or len(url) > MAX_URL or not _SAFE_PATH.fullmatch(url):
        return None
    if _ESCAPE.search(url.split("?", 1)[0][1:]):
        return None
    return url


def _text(v: object, limit: int) -> str:
    return v.strip()[:limit] if isinstance(v, str) else ""


def pointer_of(item: object) -> dict | None:
    """SSE embeds 의 한 항목 → 서버 사본에 남길 포인터 {app, tool, url, title}. 주소가 규칙 밖이면 None."""
    if not isinstance(item, dict):
        return None
    url = safe_path(item.get("url"))
    if url is None:
        return None
    app = _text(item.get("app"), 64)
    if not _APP.fullmatch(app):
        app = url.split("/", 3)[2]          # 경로의 앱 마디(규칙이 이미 걸렀다)
    tool = _text(item.get("tool"), 120)
    title = _text(item.get("title"), 120) or f"{app} · {tool}".strip(" ·")
    return {"app": app, "tool": tool, "url": url, "title": title}


def pointers(items: object) -> list[dict]:
    """한 답의 포인터들 — 규칙 밖은 버리고 같은 주소는 하나, MAX_ITEMS 까지."""
    out: list[dict] = []
    seen: set[str] = set()
    for it in items if isinstance(items, list) else []:
        p = pointer_of(it)
        if p is None or p["url"] in seen:
            continue
        seen.add(p["url"])
        out.append(p)
        if len(out) >= MAX_ITEMS:
            break
    return out
