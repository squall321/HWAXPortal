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
        # 의미검색용 벡터. owner_sub 를 여기에 한 번 더 적는다(비정규화) — 검색은 항상
        # "내 대화 안에서"이고, 조인 없이 소유자로 먼저 좁혀야 스캔량이 내 것만큼으로 준다.
        # 소유권 판정을 이 테이블 하나로 끝내는 것이 더 중요하다: 조인을 빠뜨린 쿼리 하나가
        # 남의 대화를 물어오는 사고가 되는데, 여기 owner_sub 가 있으면 그런 쿼리를 쓸 수 없다.
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS message_vectors ("
            "message_id TEXT NOT NULL, chunk_ix INTEGER NOT NULL, conversation_id TEXT NOT NULL, "
            "owner_sub TEXT NOT NULL, text TEXT NOT NULL, model TEXT NOT NULL, dim INTEGER NOT NULL, "
            "vec BLOB NOT NULL, ts INTEGER NOT NULL, PRIMARY KEY (message_id, chunk_ix))"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_vec_owner ON message_vectors (owner_sub)"
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
            self._conn.execute("DELETE FROM message_vectors WHERE conversation_id = ?", (cid,))
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

    # ── 의미검색 인덱스 ──────────────────────────────────────────────────────
    def unindexed(self, owner_sub: str, limit: int = 2000) -> list[dict]:
        """아직 벡터가 없는 내 메시지. 색인은 증분이다 — 매번 전량 임베딩하면 느리고 비싸다."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT m.id, m.conversation_id, m.content FROM messages m "
                "JOIN conversations c ON c.id = m.conversation_id "
                "LEFT JOIN message_vectors v ON v.message_id = m.id "
                "WHERE c.owner_sub = ? AND v.message_id IS NULL "
                "ORDER BY m.ts DESC LIMIT ?",
                (owner_sub, limit),
            ).fetchall()
        return [{"message_id": r[0], "conversation_id": r[1], "content": r[2]} for r in rows]

    def put_vectors(self, rows: list[dict]) -> int:
        """(message_id, chunk_ix) 단위 upsert. 같은 메시지를 다시 색인해도 중복되지 않는다."""
        if not rows:
            return 0
        now = _now()
        with self._lock:
            self._conn.executemany(
                "INSERT OR REPLACE INTO message_vectors "
                "(message_id, chunk_ix, conversation_id, owner_sub, text, model, dim, vec, ts) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [(r["message_id"], r["chunk_ix"], r["conversation_id"], r["owner_sub"],
                  r["text"], r["model"], r["dim"], r["vec"], now) for r in rows],
            )
            self._conn.commit()
        return len(rows)

    def vectors_for(self, owner_sub: str, model: str) -> list[tuple]:
        """내 벡터 전량. 모델이 다르면 섞지 않는다 — 다른 임베딩 공간의 코사인은 무의미하다."""
        with self._lock:
            return self._conn.execute(
                "SELECT v.message_id, v.chunk_ix, v.conversation_id, v.text, v.vec, "
                "       c.title, m.role, m.persona, m.ts "
                "FROM message_vectors v "
                "JOIN conversations c ON c.id = v.conversation_id "
                "JOIN messages m ON m.id = v.message_id "
                "WHERE v.owner_sub = ? AND v.model = ?",
                (owner_sub, model),
            ).fetchall()

    def index_stats(self, owner_sub: str) -> dict:
        with self._lock:
            total = self._conn.execute(
                "SELECT COUNT(*) FROM messages m JOIN conversations c ON c.id = m.conversation_id "
                "WHERE c.owner_sub = ?", (owner_sub,)).fetchone()[0]
            indexed = self._conn.execute(
                "SELECT COUNT(DISTINCT message_id) FROM message_vectors WHERE owner_sub = ?",
                (owner_sub,)).fetchone()[0]
        # 'pending' 을 total-indexed 로 내지 않는다 — 너무 짧아 색인 대상이 아닌 메시지가
        # 영영 남아 "아직 10개 남았다"가 고정 표시된다. 남은 일이 없는데 남았다고 말하는
        # 숫자는 그냥 거짓말이다. 색인 대상 판정은 청크 규칙을 아는 conv_search 가 한다.
        return {"messages": total, "indexed": indexed}
