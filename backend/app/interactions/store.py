# 상호작용 원장(SQLite) — 사건 · 공유한 Claude 대화 · 가져오기 자리 · 원문 열람 감사 넷과 지우기 표지(contract §2 · IX-10)
"""대화 저장소(app/agent/conv_store.py)와 같은 꼴 — stdlib sqlite3 + threading.Lock, WAL, 잠금 대기는 CONV_STORE_BUSY_TIMEOUT_S, 쓰기는 전부
`with self._lock, self._conn:`(도중에 실패하면 rollback — conv_store 머리 주석의 까닭 그대로).

넣기는 `UNIQUE(source, source_ref)` 로 한 번만이다 — 같은 원천을 다시 훑어도(가져오기 자리를 쓰기 전에 죽은 뒤 · 되돌아보기 창) 둘이 되지 않는다.
글은 넣기 전에 한 번 더 가린다(redact — 게이트웨이가 가린 것도 다시). 한 줄 상한(INTERACTIONS_OUTPUT_MAX_BYTES)을 넘는 글은 앞부분만 두고
원래 크기(output_chars) · sha256 을 남긴다.

지우기 청구는 그 사람의 사건 · 공유 대화를 지우고 **지우기 표지**(erase_marks — 그 사람 · 그 시각)를 남긴다. 표지가 없으면 대화 저장소의
되돌아보기 창이나 게이트웨이 창고에 남은 그 시각 전 줄이 다음 주기에 다시 들어와 지운 것이 조용히 되살아난다(IX-14)."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import threading
import time
import uuid
import zlib
from pathlib import Path

from app.config import Settings
from app.interactions.redact import redact, redact_text

logger = logging.getLogger(__name__)

SURFACES = ("web_chat", "web_delib", "think", "routine", "procedure", "mcp_call", "tool_search", "shared_claude")
EVENT_COLS = ("id", "ts", "surface", "actor", "affiliation", "client", "conv_id", "turn_id", "corr", "rid", "via", "app", "tool",
              "model", "status", "ms", "tokens_in", "tokens_out", "input", "output", "output_chars", "output_sha256", "meta",
              "source", "source_ref")
META_MAX_CHARS = 1_000_000     # meta JSON 상한 — 넘으면 큰 날것 칸(detail_full · result_full · result_preview)부터 떼고, 그래도 넘으면 앞부분 표지만
PREVIEW_IN, PREVIEW_OUT = 200, 300

_DDL = (
    """CREATE TABLE IF NOT EXISTS events (
        id TEXT PRIMARY KEY, ts INTEGER NOT NULL, surface TEXT NOT NULL, actor TEXT, affiliation TEXT, client TEXT,
        conv_id TEXT, turn_id TEXT, corr TEXT, rid TEXT, via TEXT, app TEXT, tool TEXT, model TEXT, status TEXT,
        ms INTEGER, tokens_in INTEGER, tokens_out INTEGER, input TEXT, output TEXT, output_chars INTEGER, output_sha256 TEXT,
        meta TEXT, source TEXT NOT NULL, source_ref TEXT NOT NULL,
        UNIQUE (source, source_ref))""",
    "CREATE INDEX IF NOT EXISTS ix_ev_actor_id ON events (actor, id)",
    "CREATE INDEX IF NOT EXISTS ix_ev_surface_id ON events (surface, id)",
    "CREATE INDEX IF NOT EXISTS ix_ev_corr ON events (corr) WHERE corr IS NOT NULL",
    """CREATE TABLE IF NOT EXISTS shared_sessions (
        id TEXT PRIMARY KEY, owner TEXT NOT NULL, session_id TEXT NOT NULL, title TEXT, client TEXT,
        created INTEGER NOT NULL, updated INTEGER NOT NULL, messages BLOB NOT NULL, chars INTEGER NOT NULL,
        kind TEXT NOT NULL, raw BLOB,
        UNIQUE (owner, session_id))""",
    "CREATE TABLE IF NOT EXISTS ingest_cursors (source TEXT PRIMARY KEY, cursor TEXT, updated INTEGER NOT NULL)",
    """CREATE TABLE IF NOT EXISTS view_audit (
        n INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER NOT NULL, viewer TEXT NOT NULL, owner TEXT,
        event_id TEXT, shared_id TEXT, action TEXT NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS ix_audit_ts ON view_audit (ts)",
    "CREATE TABLE IF NOT EXISTS erase_marks (actor TEXT PRIMARY KEY, upto INTEGER NOT NULL)",
)

_B32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def ulid(ts: float | None = None) -> str:
    """ULID — 앞 10자는 그 사건의 시각(밀리초)이라 id 차례가 시각 차례다(목록의 before 자리로 쓴다). 뒤 16자는 무작위."""
    ms = int((time.time() if ts is None else ts) * 1000)
    n = (ms << 80) | int.from_bytes(os.urandom(10), "big")
    return "".join(_B32[(n >> (5 * i)) & 31] for i in range(25, -1, -1))


def clip_utf8(s: str, max_bytes: int) -> str:
    """UTF-8 로 max_bytes 안의 앞부분 — 글자 중간에서 자르지 않는다."""
    b = s.encode("utf-8")
    return s if len(b) <= max_bytes else b[:max_bytes].decode("utf-8", "ignore")


def _meta_json(meta: dict | None) -> str | None:
    if not meta:
        return None
    s = json.dumps(meta, ensure_ascii=False, default=str)
    if len(s) <= META_MAX_CHARS:
        return s
    slim = json.loads(s)
    for a in slim.get("activity") or []:
        if isinstance(a, dict):
            for k in ("detail_full", "result_full", "result_preview"):
                a.pop(k, None)
    slim["meta_trimmed"] = True
    s = json.dumps(slim, ensure_ascii=False, default=str)
    return s if len(s) <= META_MAX_CHARS else json.dumps({"meta_trimmed": True, "meta_chars": len(s)})


class InteractionStore:
    def __init__(self, settings: Settings) -> None:
        self._path = Path(settings.resolve(settings.interactions_store_path))
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._max = max(1024, int(settings.interactions_output_max_bytes))
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.execute(f"PRAGMA busy_timeout={int(settings.conv_store_busy_timeout_s * 1000)}")
        try:
            mode = self._conn.execute("PRAGMA journal_mode=WAL").fetchone()[0]
        except sqlite3.OperationalError as exc:
            mode = f"실패 — {exc}"
        if str(mode).lower() != "wal":
            logger.warning("상호작용 원장을 WAL 로 바꾸지 못했다(%s) — 이번 기동은 종전 저널로 돈다 · %s", mode, self._path)
        with self._lock, self._conn:
            for stmt in _DDL:
                self._conn.execute(stmt)

    @property
    def path(self) -> Path:
        return self._path

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # ── 넣기 ────────────────────────────────────────────────────────────────
    def _row(self, ev: dict) -> tuple:
        """사건 하나 → 표 한 줄. 글은 가리고 상한을 건다. output_chars · sha256 을 원천이 주었으면(게이트웨이 — 이미 자른 글) 그것을 쓴다."""
        out = ev.get("output")
        out = redact_text(out) if isinstance(out, str) else (None if out is None else redact_text(json.dumps(redact(out), ensure_ascii=False, default=str)))
        inp = ev.get("input")
        inp = redact_text(inp) if isinstance(inp, str) else (None if inp is None else json.dumps(redact(inp), ensure_ascii=False, default=str))
        meta = dict(ev.get("meta") or {})
        chars = ev.get("output_chars")
        sha = ev.get("output_sha256")
        if out is not None:
            if chars is None:
                chars = len(out)
            if sha is None:
                sha = hashlib.sha256(out.encode("utf-8")).hexdigest()
            clipped = clip_utf8(out, self._max)
            if clipped != out:
                meta["output_clipped"] = True
                out = clipped
        if inp is not None:
            clipped = clip_utf8(inp, self._max)
            if clipped != inp:
                meta["input_chars"] = len(inp)
                meta["input_clipped"] = True
                inp = clipped
        ts = int(ev.get("ts") or time.time())
        actor = (str(ev["actor"]).strip().lower() or None) if ev.get("actor") else None
        vals = {**ev, "id": ev.get("id") or ulid(ts), "ts": ts, "actor": actor, "input": inp, "output": out,
                "output_chars": chars, "output_sha256": sha, "meta": _meta_json(redact(meta))}
        return tuple(vals.get(c) for c in EVENT_COLS)

    def _erased(self) -> dict[str, int]:
        return {a: u for a, u in self._conn.execute("SELECT actor, upto FROM erase_marks")}

    def put_events(self, events: list[dict], *, update: bool = False) -> int:
        """사건 여럿을 한 트랜잭션으로 → 새로 들어간(또는 update 면 바뀐) 줄 수. 지우기 표지보다 앞선 그 사람의 사건은 넣지 않는다.
        update — 같은 (source, source_ref) 가 있으면 글 · meta 를 바꾼다(도구 검색 질의 — 뒤이은 호출이 나중에 붙는다 · 공유 대화 — 같은 세션 덮어쓰기).
        바뀐 것이 없으면 쓰지 않는다(WHERE)."""
        if not events:
            return 0
        rows = [self._row(e) for e in events]
        cols = ", ".join(EVENT_COLS)
        marks = ", ".join("?" for _ in EVENT_COLS)
        if update:
            sql = (f"INSERT INTO events ({cols}) VALUES ({marks}) ON CONFLICT(source, source_ref) DO UPDATE SET "
                   "ts = excluded.ts, actor = excluded.actor, client = excluded.client, input = excluded.input, "
                   "output = excluded.output, output_chars = excluded.output_chars, output_sha256 = excluded.output_sha256, "
                   "meta = excluded.meta, status = excluded.status "
                   "WHERE events.output_sha256 IS NOT excluded.output_sha256 OR events.meta IS NOT excluded.meta "
                   "OR events.input IS NOT excluded.input")
        else:
            sql = f"INSERT INTO events ({cols}) VALUES ({marks}) ON CONFLICT(source, source_ref) DO NOTHING"
        ia, it = EVENT_COLS.index("actor"), EVENT_COLS.index("ts")
        n = 0
        with self._lock, self._conn:
            erased = self._erased()
            for r in rows:
                if r[ia] and r[ia] in erased and r[it] <= erased[r[ia]]:
                    continue
                n += self._conn.execute(sql, r).rowcount
        return n

    # ── 가져오기 자리 ────────────────────────────────────────────────────────
    def cursor(self, source: str) -> str | None:
        with self._lock:
            row = self._conn.execute("SELECT cursor FROM ingest_cursors WHERE source = ?", (source,)).fetchone()
        return row[0] if row else None

    def set_cursor(self, source: str, cursor: str | None) -> None:
        with self._lock, self._conn:
            self._conn.execute("INSERT INTO ingest_cursors (source, cursor, updated) VALUES (?, ?, ?) "
                               "ON CONFLICT(source) DO UPDATE SET cursor = excluded.cursor, updated = excluded.updated",
                               (source, cursor, int(time.time())))

    # ── 공유한 Claude 대화(M2) ───────────────────────────────────────────────
    def put_shared(self, *, owner: str, session_id: str, title: str, client: str, messages: list[dict], kind: str,
                   raw: str | None, event: dict) -> dict:
        """같은 (주인, session_id) 는 덮어쓴다 → {id, created(새로 만들었나), chars}. 사건(surface shared_claude) 한 줄도 같은 트랜잭션에서
        넣거나 바꾼다 — 공유 대화도 내 기록 · 분석가 검색에 같은 줄로 보인다. 지우기 표지는 보지 않는다(지운 뒤 새로 보낸 것이다)."""
        owner = owner.strip().lower()
        now = int(time.time())
        blob = zlib.compress(json.dumps(messages, ensure_ascii=False).encode("utf-8"))
        rawz = zlib.compress(raw.encode("utf-8")) if raw is not None else None
        chars = sum(len(str(m.get("content") or "")) for m in messages)
        with self._lock, self._conn:
            got = self._conn.execute("SELECT id FROM shared_sessions WHERE owner = ? AND session_id = ?", (owner, session_id)).fetchone()
            sid = got[0] if got else uuid.uuid4().hex
            if got:
                self._conn.execute("UPDATE shared_sessions SET title = ?, client = ?, updated = ?, messages = ?, chars = ?, kind = ?, raw = ? "
                                   "WHERE id = ?", (title, client, now, blob, chars, kind, rawz, sid))
            else:
                self._conn.execute("INSERT INTO shared_sessions (id, owner, session_id, title, client, created, updated, messages, chars, "
                                   "kind, raw) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                   (sid, owner, session_id, title, client, now, now, blob, chars, kind, rawz))
            row = self._row({**event, "ts": now, "actor": owner, "surface": "shared_claude", "client": client,
                             "source": "share", "source_ref": sid,
                             "meta": {**(event.get("meta") or {}), "shared_id": sid, "session_id": session_id, "kind": kind,
                                      "messages": len(messages), "chars": chars}})
            cols = ", ".join(EVENT_COLS)
            self._conn.execute(
                f"INSERT INTO events ({cols}) VALUES ({', '.join('?' for _ in EVENT_COLS)}) ON CONFLICT(source, source_ref) DO UPDATE SET "
                "ts = excluded.ts, client = excluded.client, input = excluded.input, output = excluded.output, "
                "output_chars = excluded.output_chars, output_sha256 = excluded.output_sha256, meta = excluded.meta", row)
        return {"id": sid, "created": not got, "chars": chars}

    def shared(self, sid: str, owner: str | None = None, *, with_raw: bool = False) -> dict | None:
        """공유 대화 하나 — owner 를 주면 그 사람 것만(남의 것은 없는 것과 같다)."""
        q = "SELECT id, owner, session_id, title, client, created, updated, messages, chars, kind, raw FROM shared_sessions WHERE id = ?"
        args: tuple = (sid,)
        if owner is not None:
            q += " AND owner = ?"
            args = (sid, owner.strip().lower())
        with self._lock:
            r = self._conn.execute(q, args).fetchone()
        if r is None:
            return None
        out = {"id": r[0], "owner": r[1], "session_id": r[2], "title": r[3], "client": r[4], "created": r[5], "updated": r[6],
               "messages": json.loads(zlib.decompress(r[7]).decode("utf-8")), "chars": r[8], "kind": r[9], "raw_available": r[10] is not None}
        if with_raw and r[10] is not None:
            out["raw"] = zlib.decompress(r[10]).decode("utf-8")
        return out

    # ── 읽기 ────────────────────────────────────────────────────────────────
    @staticmethod
    def _like(q: str) -> str:
        return "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"

    def search(self, *, actor: str | None = None, q: str = "", surface: str = "", app: str = "", status: str = "",
               since: int | None = None, until: int | None = None, before: str = "", limit: int = 50) -> dict:
        """사건 목록(새것 먼저) — 글은 앞부분만(preview). actor 를 주면 그 사람 것만. before 는 앞 쪽의 마지막 id(ULID 차례 = 시각 차례)."""
        where, args = [], []
        if actor is not None:
            where.append("actor = ?")
            args.append(actor.strip().lower())
        if surface:
            where.append("surface = ?")
            args.append(surface)
        if app:
            where.append("app = ?")
            args.append(app)
        if status:
            where.append("status = ?")
            args.append(status)
        if since is not None:
            where.append("ts >= ?")
            args.append(int(since))
        if until is not None:
            where.append("ts < ?")
            args.append(int(until))
        if before:
            where.append("id < ?")
            args.append(before)
        if q.strip():
            like = self._like(q.strip())
            where.append("(input LIKE ? ESCAPE '\\' OR output LIKE ? ESCAPE '\\' OR tool LIKE ? ESCAPE '\\')")
            args += [like, like, like]
        lim = max(1, min(200, int(limit)))
        sql = ("SELECT id, ts, surface, actor, affiliation, client, conv_id, app, tool, model, status, ms, via, "
               f"substr(input, 1, {PREVIEW_IN}), substr(output, 1, {PREVIEW_OUT}), output_chars FROM events"
               + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY id DESC LIMIT ?")
        with self._lock:
            rows = self._conn.execute(sql, (*args, lim + 1)).fetchall()
        keys = ("id", "ts", "surface", "actor", "affiliation", "client", "conv_id", "app", "tool", "model", "status", "ms", "via",
                "input_preview", "output_preview", "output_chars")
        items = [dict(zip(keys, r, strict=True)) for r in rows[:lim]]
        return {"items": items, "more": len(rows) > lim, "next_before": items[-1]["id"] if len(rows) > lim else None}

    def get(self, eid: str, actor: str | None = None) -> dict | None:
        """사건 하나의 원문 — actor 를 주면 그 사람 것만(남의 것은 없는 것과 같다)."""
        q = f"SELECT {', '.join(EVENT_COLS)} FROM events WHERE id = ?"
        args: tuple = (eid,)
        if actor is not None:
            q += " AND actor = ?"
            args = (eid, actor.strip().lower())
        with self._lock:
            r = self._conn.execute(q, args).fetchone()
        if r is None:
            return None
        d = dict(zip(EVENT_COLS, r, strict=True))
        d["meta"] = json.loads(d["meta"]) if d["meta"] else None
        return d

    def audit(self, *, viewer: str, owner: str | None, action: str, event_id: str | None = None, shared_id: str | None = None) -> None:
        with self._lock, self._conn:
            self._conn.execute("INSERT INTO view_audit (ts, viewer, owner, event_id, shared_id, action) VALUES (?, ?, ?, ?, ?, ?)",
                               (int(time.time()), viewer.strip().lower(), (owner or "").strip().lower() or None, event_id, shared_id, action))

    def audit_rows(self, limit: int = 100) -> list[dict]:
        with self._lock:
            rows = self._conn.execute("SELECT ts, viewer, owner, event_id, shared_id, action FROM view_audit ORDER BY n DESC LIMIT ?",
                                      (max(1, min(500, limit)),)).fetchall()
        return [dict(zip(("ts", "viewer", "owner", "event_id", "shared_id", "action"), r, strict=True)) for r in rows]

    # ── 지우기(본인 청구 — contract §2) ──────────────────────────────────────
    def erase(self, actor: str) -> dict:
        """그 사람의 사건 · 공유 대화를 지우고 지우기 표지를 지금 시각으로 남긴다 → 지운 수. 열람 감사는 지우지 않는다(누가 봤는지는 남는다)."""
        a = actor.strip().lower()
        now = int(time.time())
        with self._lock, self._conn:
            ev = self._conn.execute("DELETE FROM events WHERE actor = ?", (a,)).rowcount
            sh = self._conn.execute("DELETE FROM shared_sessions WHERE owner = ?", (a,)).rowcount
            self._conn.execute("INSERT INTO erase_marks (actor, upto) VALUES (?, ?) ON CONFLICT(actor) DO UPDATE SET upto = excluded.upto",
                               (a, now))
        return {"events": ev, "shared": sh, "upto": now}

    def counts(self) -> dict:
        with self._lock:
            ev = self._conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            sh = self._conn.execute("SELECT COUNT(*) FROM shared_sessions").fetchone()[0]
        return {"events": ev, "shared": sh}
