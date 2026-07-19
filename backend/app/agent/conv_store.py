"""서버 대화 저장소(SQLite) — Claude(MCP) 심의·포털 웹 챗·GLM 이어가기가 공유하는 정본.

token_store.py 와 동일 패턴(stdlib sqlite3 + threading.Lock, ORM 없음). 파일럿 단일 인스턴스라
SQLite 로 재시작 내구성을 얻는다(멀티 인스턴스면 같은 인터페이스 뒤에 다른 백엔드로 교체).

소유권: 모든 조회/변경은 owner_sub == 현재 principal 을 강제한다(타인 대화 접근 차단).
"""
import json
import sqlite3
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.config import Settings


def _now() -> int:
    return int(datetime.now(tz=UTC).timestamp())


def _uid() -> str:
    return uuid.uuid4().hex


class ConversationStore:
    def __init__(self, settings: Settings) -> None:
        # token_store 옆에 conversations.db — 전용 경로 설정 없으면 token_store_path 형제로.
        raw = getattr(settings, "conv_store_path", None) or "data/conversations.db"
        path = Path(settings.resolve(raw))
        path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS conversations ("
            "id TEXT PRIMARY KEY, owner_sub TEXT NOT NULL, title TEXT, "
            "kind TEXT NOT NULL DEFAULT 'chat', source TEXT NOT NULL DEFAULT 'web', "
            "created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL)"
        )
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS messages ("
            "id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL, seq INTEGER NOT NULL, "
            "role TEXT NOT NULL, persona TEXT, round INTEGER, content TEXT NOT NULL, "
            "meta TEXT, ts INTEGER NOT NULL)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_msg_conv ON messages (conversation_id, seq)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_conv_owner ON conversations (owner_sub, updated_at)"
        )
        self._conn.commit()

    # ── 생성 ────────────────────────────────────────────────────────────────
    def create(self, *, owner_sub: str, title: str, kind: str = "chat",
               source: str = "web", conv_id: str | None = None) -> str:
        cid = conv_id or _uid()
        now = _now()
        with self._lock:
            self._conn.execute(
                "INSERT OR IGNORE INTO conversations (id, owner_sub, title, kind, source, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (cid, owner_sub, title[:200], kind, source, now, now),
            )
            self._conn.commit()
        return cid

    def create_with_messages(self, *, owner_sub: str, title: str, kind: str,
                             source: str, messages: list[dict]) -> str:
        """MCP 심의 등 — 대화 + 메시지 일괄 생성. messages: [{role,content,persona?,round?,meta?}]."""
        cid = self.create(owner_sub=owner_sub, title=title, kind=kind, source=source)
        for m in messages:
            self.append(conversation_id=cid, owner_sub=owner_sub, role=m.get("role", "assistant"),
                        content=str(m.get("content", "")), persona=m.get("persona"),
                        round=m.get("round"), meta=m.get("meta"))
        return cid

    # ── 소유권 확인 ─────────────────────────────────────────────────────────
    def _owns(self, cid: str, owner_sub: str) -> bool:
        cur = self._conn.execute(
            "SELECT 1 FROM conversations WHERE id = ? AND owner_sub = ?", (cid, owner_sub)
        )
        return cur.fetchone() is not None

    # ── append ──────────────────────────────────────────────────────────────
    def append(self, *, conversation_id: str, owner_sub: str, role: str, content: str,
               persona: str | None = None, round: int | None = None,
               meta: dict | None = None) -> bool:
        """메시지 1건 추가. 소유자만. 대화 없으면 실패(False)."""
        now = _now()
        with self._lock:
            if not self._owns(conversation_id, owner_sub):
                return False
            cur = self._conn.execute(
                "SELECT COALESCE(MAX(seq), 0) + 1 FROM messages WHERE conversation_id = ?",
                (conversation_id,),
            )
            seq = cur.fetchone()[0]
            self._conn.execute(
                "INSERT INTO messages (id, conversation_id, seq, role, persona, round, content, meta, ts) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (_uid(), conversation_id, seq, role, persona, round, content,
                 json.dumps(meta, ensure_ascii=False) if meta else None, now),
            )
            self._conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conversation_id)
            )
            self._conn.commit()
        return True

    # ── 조회 ────────────────────────────────────────────────────────────────
    def list_for_owner(self, owner_sub: str, limit: int = 100) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT id, title, kind, source, created_at, updated_at FROM conversations "
                "WHERE owner_sub = ? ORDER BY updated_at DESC LIMIT ?",
                (owner_sub, limit),
            )
            rows = cur.fetchall()
        return [{"id": r[0], "title": r[1], "kind": r[2], "source": r[3],
                 "created_at": r[4], "updated_at": r[5]} for r in rows]

    def get(self, cid: str, owner_sub: str) -> dict | None:
        """대화 + 메시지(순서대로). 소유자만. 없거나 타인 소유면 None."""
        with self._lock:
            cur = self._conn.execute(
                "SELECT id, title, kind, source, created_at, updated_at FROM conversations "
                "WHERE id = ? AND owner_sub = ?", (cid, owner_sub),
            )
            head = cur.fetchone()
            if head is None:
                return None
            mcur = self._conn.execute(
                "SELECT role, persona, round, content, meta, ts FROM messages "
                "WHERE conversation_id = ? ORDER BY seq", (cid,),
            )
            msgs = [{"role": m[0], "persona": m[1], "round": m[2], "content": m[3],
                     "meta": json.loads(m[4]) if m[4] else None, "ts": m[5]}
                    for m in mcur.fetchall()]
        return {"id": head[0], "title": head[1], "kind": head[2], "source": head[3],
                "created_at": head[4], "updated_at": head[5], "messages": msgs}

    def delete(self, cid: str, owner_sub: str) -> bool:
        with self._lock:
            if not self._owns(cid, owner_sub):
                return False
            self._conn.execute("DELETE FROM messages WHERE conversation_id = ?", (cid,))
            self._conn.execute("DELETE FROM conversations WHERE id = ?", (cid,))
            self._conn.commit()
        return True

    def rename(self, cid: str, owner_sub: str, title: str) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "UPDATE conversations SET title = ? WHERE id = ? AND owner_sub = ?",
                (title[:200], cid, owner_sub),
            )
            self._conn.commit()
            return cur.rowcount > 0
