# 전문가 고르기 검토 — 포털 대화 저장소의 지난 날들에서 실사용 첫 발화(H 후보)를 읽기 전용으로 떼어 낸다(docs/request-1029 E-5 · E5-2)
"""design-e5 2.2 H 의 출처 넷 가운데 포털 대화 저장소에 있는 셋을 지난 창(에이전트 서버 SEAT_QUESTIONS_DAYS — 기본 60일)만큼 모은다.
켠 뒤의 발화는 에이전트 서버가 받을 때 바로 남긴다(seat_questions.note) — 여기는 켜기 전의 날들을 밀어 넣는 쪽(ingest)이다. 출처를 가르는 규칙은
에이전트 서버 app._seat_q_source 와 같게 둔다(다르면 같은 발화가 두 길에서 다른 출처로 들어간다).

  persona     대화의 첫 사람 발화이고 그 발화에 고른 전문가(meta.pinned_agent · pinned_agents)가 실렸다 — 앞선 사람 발화가 없다
  thinking    '## Thinking —' 답 바로 앞의 사람 발화(빗금 트리거 '/띵킹' · '/생각' · '/thinking' · '/think' 는 뗀다)
  expert_cmd  '/전문가' · '/에이전트' · '/agents' · '/agent' 로 시작하는 사람 발화의 나머지 글
  한 발화는 한 출처에만 — expert_cmd > thinking > persona(에이전트 서버 갈래 차례). 그 밖의 빗금 명령(/심의 · /보고서 …)은 넣지 않는다 —
  사람이 고른 심의 좌석은 이 저장소에 없다(delib 은 에이전트 서버 몫).

떼는 것 — 대화 · 메시지 id 와 사람(주인)을 싣지 않는다. 메일 주소는 '[메일]', 포털 원장의 사람 이름 · 메일 앞부분은 '[이름]' 으로 바꾼다
(사용자 결정 D-E5-2 (가)). 에이전트 서버가 받을 때 메일 · uuid · 긴 16진 id · 전화를 한 번 더 지우고(seat_questions.strip), 날짜만 남긴다 —
발화 시각(ts)은 그 날짜와 창 밖 거름에만 쓰인다. 짧은 글 · 홀로 서지 않는 글 · 겹침은 에이전트 서버가 센다(여기서 거르지 않는다 — 한 곳에서 센다).
저장소는 읽기 전용 연결(mode=ro)로 연다. WAL 이라 저장을 막지 않는다(백업과 같은 방식). 이벤트 루프 밖(스레드)에서 부른다.
"""
import json
import re
import sqlite3
import time
from collections.abc import Iterable
from pathlib import Path

# 에이전트 서버 app._AGENT_SEARCH_TRIGGERS 와 같은 차례('/agents' 가 '/agent' 보다 먼저) — 대소문자까지 그쪽 startswith 와 같다.
AGENT_SEARCH_TRIGGERS = ("/전문가", "/에이전트", "/agents", "/agent")
# 에이전트 서버 thinking._TRIGGERS 와 같다 — 그쪽은 소문자로 견준다('/Thinking' 도 띵킹이다).
THINKING_TRIGGERS = ("/띵킹", "/생각", "/thinking", "/think")
# 에이전트 서버 thinking.py 의 답 머리 — '## Thinking — N명 답변 · M명 기권'.
THINKING_HEAD = "## Thinking —"
TEXT_MAX = 2000                    # 에이전트 서버 seat_questions.MAX_CHARS — 그쪽이 이 길이에서 자른다
SOURCES = ("expert_cmd", "thinking", "persona")      # 갈래 차례 — 앞의 것이 이긴다
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_ASCII_EDGE = (r"(?<![A-Za-z0-9])", r"(?![A-Za-z0-9])")
_HANGUL_RE = re.compile(r"[가-힣]")


def _clean(text: str) -> str:
    return " ".join(str(text or "").split())


def name_re(names: Iterable[str], locals_: Iterable[str]) -> re.Pattern | None:
    """포털 원장의 사람 이름과 메일 앞부분을 한 정규식으로(긴 것부터). 이름은 원장 값과 괄호 · 빗금 앞 머리('박구현(CAE그룹)' → '박구현').
    한글 이름은 2자 이상이고 경계를 보지 않는다(조사가 붙는다 — '홍길동님'). 영문 이름은 3자 이상 · 영숫자 경계 안에서만('Jo' 가 'Job' 을
    지우지 않게). 메일 앞부분은 3자 이상이면서 점 · 밑줄 · 붙임표 · 숫자가 든 것만이다 — 'user' · 'design' 같은 낱말 꼴은 질문 글을 지운다."""
    parts: dict[str, str] = {}
    for raw in names:
        full = _clean(raw)
        for n in {full, _clean(re.split(r"[(/]", full, maxsplit=1)[0])}:
            if _HANGUL_RE.search(n) and len(n) >= 2:
                parts[n] = re.escape(n)
            elif len(n) >= 3:
                parts[n] = _ASCII_EDGE[0] + re.escape(n) + _ASCII_EDGE[1]
    for lp in {(x or "").strip() for x in locals_}:
        if len(lp) >= 3 and re.search(r"[._\-0-9]", lp):
            parts[lp] = _ASCII_EDGE[0] + re.escape(lp) + _ASCII_EDGE[1]
    if not parts:
        return None
    return re.compile("|".join(parts[k] for k in sorted(parts, key=len, reverse=True)), re.IGNORECASE)


def scrub(text: str, nre: re.Pattern | None) -> str:
    """메일 주소 → '[메일]', 원장의 이름 · 메일 앞부분 → '[이름]'."""
    out = _EMAIL_RE.sub("[메일]", text)
    return nre.sub("[이름]", out) if nre is not None else out


def strip_agent_trigger(text: str) -> str | None:
    """'/전문가 …' 의 나머지 글(에이전트 서버 strip_agent_trigger 의 빗금 갈래 그대로) — 머리가 아니면 None."""
    for t in AGENT_SEARCH_TRIGGERS:
        if text.startswith(t):
            return text[len(t):].strip()
    return None


def strip_thinking_trigger(text: str) -> str:
    """에이전트 서버 thinking.strip_thinking_trigger 그대로 — 트리거만 있으면 글을 그대로 둔다."""
    for t in THINKING_TRIGGERS:
        if text.lower().startswith(t):
            return text[len(t):].strip() or text
    return text


def _pinned(meta_raw) -> list[str]:
    """사람 발화 meta 의 고른 전문가 — 에이전트 서버 _persona_keys 와 같이 목록이 있으면 목록, 없으면 그 한 명. 못 읽으면 빈 목록."""
    try:
        meta = json.loads(meta_raw) if isinstance(meta_raw, str) else (meta_raw or {})
    except ValueError:
        return []
    if not isinstance(meta, dict):
        return []
    many = [k for k in (meta.get("pinned_agents") or []) if isinstance(k, str) and k.strip()]
    one = meta.get("pinned_agent")
    keys = many or ([one] if isinstance(one, str) and one.strip() else [])
    return list(dict.fromkeys(k.strip()[:120] for k in keys))


def _open_ro(db_path: str) -> sqlite3.Connection:
    uri = Path(db_path).resolve().as_uri() + "?mode=ro"
    return sqlite3.connect(uri, uri=True, check_same_thread=False)


def _rows(conn: sqlite3.Connection, since: int) -> list[tuple[str, str, int, int, str, list[str]]]:
    """(출처, 대화 id, 차례, 시각, 글, 고른 전문가) — 대화 id · 차례는 출처를 가르는 데만 쓰고 밖으로 내지 않는다."""
    out: list[tuple[str, str, int, int, str, list[str]]] = []
    # 지목 전문가 챗 — 대화의 첫 사람 발화가 고른 전문가를 실었고 그 발화가 창 안일 때.
    for cid, seq, ts, content, meta in conn.execute(
        "SELECT m.conversation_id, m.seq, m.ts, substr(m.content, 1, ?), m.meta FROM messages m "
        "JOIN (SELECT conversation_id, MIN(seq) AS s FROM messages WHERE role = 'user' GROUP BY conversation_id) f "
        "  ON m.conversation_id = f.conversation_id AND m.seq = f.s "
        "WHERE m.ts >= ? AND m.meta LIKE '%\"pinned_agent%'", (TEXT_MAX * 2, since)):
        keys = _pinned(meta)
        if keys:
            out.append(("persona", cid, seq, ts, content or "", keys))
    # 띵킹 질문 — '## Thinking —' 답 바로 앞의 사람 발화.
    for cid, seq, ts, content in conn.execute(
        "SELECT u.conversation_id, u.seq, u.ts, substr(u.content, 1, ?) FROM messages a JOIN messages u "
        "  ON u.conversation_id = a.conversation_id AND u.seq = (SELECT MAX(seq) FROM messages "
        "     WHERE conversation_id = a.conversation_id AND seq < a.seq AND role = 'user') "
        "WHERE a.role = 'assistant' AND substr(a.content, 1, ?) = ? AND a.ts >= ?",
            (TEXT_MAX * 2, len(THINKING_HEAD), THINKING_HEAD, since)):
        out.append(("thinking", cid, seq, ts, content or "", []))
    # '/전문가' 질의 — '=' 비교라 대소문자까지 그쪽 startswith 와 같다('/agents' 는 '/agent' 로 걸린다).
    for cid, seq, ts, content in conn.execute(
        "SELECT conversation_id, seq, ts, substr(content, 1, ?) FROM messages WHERE role = 'user' AND ts >= ? AND "
        "(substr(ltrim(content), 1, 4) = '/전문가' OR substr(ltrim(content), 1, 5) = '/에이전트' "
        " OR substr(ltrim(content), 1, 6) = '/agent')", (TEXT_MAX * 2, since)):
        out.append(("expert_cmd", cid, seq, ts, content or "", []))
    return out


def harvest(db_path: str, *, days: int, names: Iterable[str] = (), locals_: Iterable[str] = (),
            now: float | None = None) -> tuple[list[dict], dict]:
    """대화 저장소 → (후보, 셈). 후보는 [{src, text, ts, picked?}] 를 발화 시각 순으로 — 에이전트 서버 ingest 의 items 꼴 그대로다.
    셈은 수만 담는다(글 없이)."""
    since = int((now if now is not None else time.time()) - days * 86400)
    conn = _open_ro(db_path)
    try:
        rows = _rows(conn, since)
    finally:
        conn.close()
    rank = {s: i for i, s in enumerate(SOURCES)}
    by_msg: dict[tuple[str, int], tuple[str, int, str, list[str]]] = {}
    for src, cid, seq, ts, content, picked in rows:
        cur = by_msg.get((cid, seq))
        if cur is None or rank[src] < rank[cur[0]]:
            by_msg[(cid, seq)] = (src, ts, content, picked)
    seen = dict.fromkeys(SOURCES, 0)
    skipped = {"slash": 0, "empty": 0}
    scrubbed = 0
    nre = name_re(names, locals_)
    items: list[dict] = []
    for (_cid, _seq), (src, ts, content, picked) in sorted(by_msg.items(), key=lambda kv: (kv[1][1], kv[0])):
        seen[src] += 1
        text = _clean(content)
        if src == "expert_cmd":
            text = strip_agent_trigger(text) or ""
        elif src == "thinking":
            text = strip_thinking_trigger(text)
        if src != "expert_cmd" and text.startswith("/"):
            skipped["slash"] += 1           # 빗금 명령(/심의 · /보고서 … · 글 없는 '/띵킹') — 사람이 고른 좌석 · 질문을 이 저장소에서 알 수 없다
            continue
        if not text:
            skipped["empty"] += 1
            continue
        clean = scrub(text, nre)
        scrubbed += clean != text
        item: dict = {"src": src, "text": clean[:TEXT_MAX], "ts": int(ts)}
        if src == "persona":
            item["picked"] = picked
        items.append(item)
    return items, {"days": days, "seen": seen, "sent": len(items), "skipped": skipped, "scrubbed": scrubbed}
