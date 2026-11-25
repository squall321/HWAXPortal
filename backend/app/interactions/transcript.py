# Claude Code 세션 기록 파일(JSONL) 풀이 — 사람 · 어시스턴트 글과 도구 호출을 꺼내고, 원문은 가린 채로 둔다(contract §5 · IX-13)
"""기록 파일의 줄 꼴은 Claude Code 안쪽 꼴이라 판마다 바뀐다(공식 문서 sessions — '스크립트가 직접 풀면 깨질 수 있다'). 그래서
  · 아는 꼴만 꺼낸다 — 줄의 type 이 user · assistant 이고 message.content 가 글이거나 블록 목록(text · tool_use · tool_result)일 때.
    모르는 줄 · 블록은 세기만 하고(skipped) 버리지 않는다 — 원문(raw)은 줄마다 가린 채 통째로 남는다.
  · 꺼낸 것이 0 이어도 받는다 — 원문은 남고, 꼴이 바뀐 것은 kind=transcript · messages 0 으로 드러난다.
줄마다 JSON 으로 풀어 구조 가림(redact)을 걸고 다시 쓴다. 풀지 못한 줄은 글 가림(redact_text)만."""
from __future__ import annotations

import json

from app.interactions.redact import redact, redact_text

BLOCK_CHARS = 4000        # 도구 호출 인자 · 도구 결과를 메시지에 옮길 때의 상한(원문은 raw 에 그대로)
TITLE_CHARS = 80


def _block_text(b: dict) -> tuple[str, str | None]:
    """블록 하나 → (글, 도구 이름 또는 None). 모르는 블록은 빈 글."""
    t = b.get("type")
    if t == "text":
        return str(b.get("text") or ""), None
    if t == "tool_use":
        name = str(b.get("name") or "")
        arg = json.dumps(b.get("input"), ensure_ascii=False, default=str)
        return f"[도구 호출 {name}] {arg[:BLOCK_CHARS]}", name
    if t == "tool_result":
        c = b.get("content")
        if isinstance(c, list):
            c = "\n".join(str(x.get("text") or "") for x in c if isinstance(x, dict) and x.get("type") == "text")
        mark = " 오류" if b.get("is_error") else ""
        return f"[도구 결과{mark}] {str(c or '')[:BLOCK_CHARS]}", None
    return "", None


def parse(text: str) -> dict:
    """기록 파일 글 → {messages, raw, session_id, title, client, lines, skipped}. messages 의 role 은 user · assistant · tool(도구 결과만 든 사람 차례)."""
    msgs: list[dict] = []
    raw_lines: list[str] = []
    session_id = title = summary = version = None
    skipped = 0
    lines = text.splitlines()
    for line in lines:
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            raw_lines.append(redact_text(line))
            skipped += 1
            continue
        safe = redact(obj)
        raw_lines.append(json.dumps(safe, ensure_ascii=False))
        if not isinstance(safe, dict):
            skipped += 1
            continue
        session_id = session_id or (safe.get("sessionId") if isinstance(safe.get("sessionId"), str) else None)
        version = version or (safe.get("version") if isinstance(safe.get("version"), str) else None)
        typ = safe.get("type")
        if typ == "summary" and isinstance(safe.get("summary"), str):
            summary = summary or safe["summary"]
            continue
        msg = safe.get("message")
        if typ not in ("user", "assistant") or not isinstance(msg, dict):
            skipped += 1
            continue
        content = msg.get("content")
        texts: list[str] = []
        tools: list[str] = []
        only_results = True
        if isinstance(content, str):
            texts.append(content)
            only_results = False
        elif isinstance(content, list):
            for b in content:
                if not isinstance(b, dict):
                    continue
                if b.get("type") != "tool_result":
                    only_results = False
                s, name = _block_text(b)
                if s:
                    texts.append(s)
                if name:
                    tools.append(name)
        body = "\n".join(t for t in texts if t)
        if not body:
            skipped += 1
            continue
        role = "assistant" if typ == "assistant" else ("tool" if only_results and isinstance(content, list) else "user")
        m: dict = {"role": role, "content": body}
        if isinstance(safe.get("timestamp"), str):
            m["ts"] = safe["timestamp"]
        if tools:
            m["tools"] = tools
        if safe.get("isSidechain") is True:
            m["sidechain"] = True
        msgs.append(m)
        if title is None and role == "user" and not safe.get("isMeta") and not body.lstrip().startswith("<"):
            title = body.strip().splitlines()[0][:TITLE_CHARS]
    return {"messages": msgs, "raw": "\n".join(raw_lines) + ("\n" if raw_lines else ""), "session_id": session_id,
            "title": (summary or title or "")[:200], "client": f"Claude Code {version}" if version else "Claude Code",
            "lines": len([ln for ln in lines if ln.strip()]), "skipped": skipped}


def render(messages: list[dict]) -> str:
    """메시지 목록 → 한 글(사건 output — 검색 · 미리보기용). 이름표는 사람 · 어시스턴트 · 도구."""
    label = {"user": "사람", "assistant": "어시스턴트", "tool": "도구"}
    return "\n\n".join(f"[{label.get(m.get('role'), m.get('role'))}] {m.get('content') or ''}" for m in messages)
