"""서버 대화 저장소(SQLite) — Claude(MCP) 심의·포털 웹 챗·GLM 이어가기가 공유하는 정본.

token_store.py 와 동일 패턴(stdlib sqlite3 + threading.Lock, ORM 없음). 파일럿 단일 인스턴스라
SQLite 로 재시작 내구성을 얻는다(멀티 인스턴스면 같은 인터페이스 뒤에 다른 백엔드로 교체).

소유권: 모든 조회/변경은 owner_sub == 현재 principal 을 강제한다(타인 대화 접근 차단).
"""
import json
import logging
import sqlite3
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.config import Settings

logger = logging.getLogger(__name__)


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
        # 잠금 대기(CONV_STORE_BUSY_TIMEOUT_S) — 절차 저장소(procedures/store.py)와 같은 방식. 끝난 심의의 유일한 서버 사본을
        # 쓰는 자리라 sqlite3 기본 5초는 짧다. 그래도 유한하다 — 넘으면 저장하는 쪽이 로그로 알린다. 아래 WAL 에서 이 대기가
        # 걸리는 것은 다른 연결이 **쓰는** 동안뿐이다(읽는 쪽은 막지 않는다).
        self._conn.execute(f"PRAGMA busy_timeout={int(settings.conv_store_busy_timeout_s * 1000)}")
        # WAL — 읽는 쪽이 쓰기를 막지 않게 한다. 백업(backup-local.sh)은 이 DB 를 mode=ro 로 통째로 읽는 동안 읽기 잠금을 쥐는데,
        # 종전 저널(delete)에서는 그 동안 append 의 commit 이 위 잠금 대기만큼 멈췄다. 잠금 대기를 5초에서 30초로 늘린 뒤로는 그
        # 멈춤이 최대 30초가 됐다(사본 실측 — 1.3GB DB 의 백업 15초 동안 저장도 15초 멈췄다). 절차 저장소가 같은 백업을 같은
        # 방식으로 견딘다. 한 번 바뀌면 파일에 남는다(옆에 -wal·-shm 이 생긴다 — 지우지 않는다).
        # 잠금 대기를 **먼저** 건다 — 바꾸는 순간 다른 연결이 쥐고 있으면 기다렸다가 바꾼다. 그래도 못 바꾸면 기동을 막지 않는다
        # (포털은 SSO 허브다). 종전 모드로 돌고 다음 기동이 다시 바꾼다.
        try:
            mode = self._conn.execute("PRAGMA journal_mode=WAL").fetchone()[0]
        except sqlite3.OperationalError as exc:
            mode = f"실패 — {exc}"
        if str(mode).lower() != "wal":
            logger.warning("대화 저장소를 WAL 로 바꾸지 못했다(%s) — 이번 기동은 종전 저널 모드로 돈다. 읽는 쪽(백업)이 DB 를 쥔 동안 "
                           "저장이 CONV_STORE_BUSY_TIMEOUT_S 만큼 기다린다. 다음 기동이 다시 바꾼다 · %s", mode, path)
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
        # MCP 로 연 심의(엔진 잡)를 잡 주인의 대화로 들인 기록(docs/request-1125 WD-03 — app/agent/mcp_delib.py). 잡 하나에 한 줄이고(job_id 로 멱등),
        # 같은 주인의 같은 뿌리 잡(이어하기 사슬의 맨 앞)은 한 대화에 붙는다. finished_at 은 들인 판 — 끊긴 잡을 제자리에서 이어(같은 job_id) 다시 끝나면
        # 더 늦은 판이 와서 그 잡의 줄만 바꾼다. 대화를 지워도 이 줄은 남긴다 — 경계의 잡이 다음 당기기에 다시 나와도 지운 대화를 되살리지 않게.
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS mcp_delib_jobs ("
            "job_id TEXT PRIMARY KEY, root_job_id TEXT NOT NULL, owner_sub TEXT NOT NULL, conversation_id TEXT NOT NULL, "
            "finished_at REAL NOT NULL DEFAULT 0, at INTEGER NOT NULL)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_mcp_delib_root ON mcp_delib_jobs (owner_sub, root_job_id)"
        )
        # 당기기 커서(앞으로만 간다 — advance 가 MAX 로 쓴다)
        self._conn.execute("CREATE TABLE IF NOT EXISTS conv_cursors (k TEXT PRIMARY KEY, since REAL NOT NULL)")
        self._conn.commit()

    # ⚠ 쓰기는 전부 `with self._lock, self._conn:` 이다 — 연결 문맥이 끝에서 commit 하고, **도중에 실패하면 rollback 한다.**
    #   되돌리지 않으면 잠금 대기가 다 찬 INSERT 가 파이썬이 먼저 연 BEGIN 을 남긴다. 연결이 하나라 그 뒤의 읽기가 그 트랜잭션
    #   안에서 스냅샷을 쥐고, WAL 에서는 다른 연결이 한 번이라도 커밋하면 그 스냅샷이 낡는다 — 이 연결의 쓰기는 기다리지도 않고
    #   'database is locked' 로 실패하고 읽기는 옛 내용만 본다. 포털을 다시 띄울 때까지다(사본 재현). 종전 저널에서는 남은
    #   읽기 잠금이 다른 연결의 commit 을 막았다.

    # ── 생성 ────────────────────────────────────────────────────────────────
    def create(self, *, owner_sub: str, title: str, kind: str = "chat",
               source: str = "web", conv_id: str | None = None) -> str:
        cid = conv_id or _uid()
        now = _now()
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT OR IGNORE INTO conversations (id, owner_sub, title, kind, source, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (cid, owner_sub, title[:200], kind, source, now, now),
            )
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

    def owner_state(self, cid: str, owner_sub: str) -> str:
        """'mine'(주인) · 'other'(남의 대화) · 'none'(없다). 남의 대화의 내용도 주인도 돌려주지 않는다. 웹 심의 멈춤(POST
        /agent/deliberate/cancel)이 '없는 대화(404)' 와 '남의 대화(403)' 를 가를 때만 쓴다 — 다른 대화 REST 는 종전대로 둘을 같은 404 로 답한다."""
        with self._lock:
            row = self._conn.execute("SELECT owner_sub FROM conversations WHERE id = ?", (cid,)).fetchone()
        if row is None:
            return "none"
        return "mine" if row[0] == owner_sub else "other"

    # ── append ──────────────────────────────────────────────────────────────
    def append(self, *, conversation_id: str, owner_sub: str, role: str, content: str,
               persona: str | None = None, round: int | None = None,
               meta: dict | None = None, msg_id: str | None = None) -> bool:
        """메시지 1건 추가. 소유자만. 대화 없으면 실패(False).

        msg_id 를 주면 한 번만이다 — 그 id 의 메시지가 이미 있으면 다시 넣지 않고 True 다(덧붙인 뒤 부른 쪽의 기록이 실패해 다시 불러도
        둘이 되지 않게 — 발표자료 알림, docs/wda-deck WD-D54). 없으면 종전처럼 새 id."""
        now = _now()
        with self._lock, self._conn:
            if not self._owns(conversation_id, owner_sub):
                return False
            if msg_id is not None and self._conn.execute("SELECT 1 FROM messages WHERE id = ?", (msg_id,)).fetchone():
                return True
            cur = self._conn.execute(
                "SELECT COALESCE(MAX(seq), 0) + 1 FROM messages WHERE conversation_id = ?",
                (conversation_id,),
            )
            seq = cur.fetchone()[0]
            self._conn.execute(
                "INSERT INTO messages (id, conversation_id, seq, role, persona, round, content, meta, ts) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (msg_id or _uid(), conversation_id, seq, role, persona, round, content,
                 json.dumps(meta, ensure_ascii=False) if meta else None, now),
            )
            self._conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conversation_id)
            )
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

    def count_for_owner(self, owner_sub: str) -> int:
        """그 사람의 대화 총수 — 목록(list_for_owner)이 최근 limit 건만 줄 때 끊었다는 것을 알리는 데 쓴다."""
        with self._lock:
            return int(self._conn.execute("SELECT COUNT(*) FROM conversations WHERE owner_sub = ?",
                                          (owner_sub,)).fetchone()[0])

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
        with self._lock, self._conn:
            if not self._owns(cid, owner_sub):
                return False
            self._conn.execute("DELETE FROM messages WHERE conversation_id = ?", (cid,))
            self._conn.execute("DELETE FROM message_vectors WHERE conversation_id = ?", (cid,))
            self._conn.execute("DELETE FROM conversations WHERE id = ?", (cid,))
        return True

    def rename(self, cid: str, owner_sub: str, title: str) -> bool:
        with self._lock, self._conn:
            cur = self._conn.execute(
                "UPDATE conversations SET title = ? WHERE id = ? AND owner_sub = ?",
                (title[:200], cid, owner_sub),
            )
            return cur.rowcount > 0

    # ── MCP 심의 대화(WD-03) ────────────────────────────────────────────────
    def ingest_mcp_delib(self, *, owner_sub: str, job_id: str, root_job_id: str, title: str,
                         messages: list[dict], finished_at: float) -> str:
        """끝난 엔진 잡 하나를 주인의 대화에 — 한 트랜잭션이다(반쪽 대화가 남지 않는다). 답은 새로 만듦(new) · 같은 뿌리 대화에 붙임(appended) ·
        더 늦은 판으로 그 잡의 줄을 바꿈(replaced) · 이미 들임(already) · 들인 대화를 주인이 지웠다(deleted — 되살리지 않는다).
        메시지 id 는 mcpd:<job_id>:<차례> 다 — 판을 바꿀 때 그 잡의 줄만 걷는다. 시각은 잡이 끝난 때다(목록에서 그날로 선다)."""
        ts = int(finished_at) if finished_at and finished_at > 0 else _now()
        with self._lock, self._conn:
            had = self._conn.execute("SELECT conversation_id, finished_at FROM mcp_delib_jobs WHERE job_id = ?",
                                     (job_id,)).fetchone()
            if had is not None:
                cid = had[0]
                if float(had[1] or 0) >= float(finished_at or 0):
                    return "already"
                self._conn.execute("UPDATE mcp_delib_jobs SET finished_at = ?, at = ? WHERE job_id = ?",
                                   (float(finished_at or 0), _now(), job_id))
                if not self._owns(cid, owner_sub):
                    return "deleted"
                self._conn.execute("DELETE FROM message_vectors WHERE message_id LIKE ?", (f"mcpd:{job_id}:%",))
                self._conn.execute("DELETE FROM messages WHERE conversation_id = ? AND id LIKE ?", (cid, f"mcpd:{job_id}:%"))
                how = "replaced"
            else:
                row = self._conn.execute(
                    "SELECT j.conversation_id FROM mcp_delib_jobs j JOIN conversations c "
                    "ON c.id = j.conversation_id AND c.owner_sub = j.owner_sub "
                    "WHERE j.owner_sub = ? AND j.root_job_id = ? ORDER BY j.at DESC LIMIT 1",
                    (owner_sub, root_job_id)).fetchone()
                if row is not None:
                    cid, how = row[0], "appended"
                else:
                    cid, how = _uid(), "new"
                    self._conn.execute(
                        "INSERT INTO conversations (id, owner_sub, title, kind, source, created_at, updated_at) "
                        "VALUES (?, ?, ?, 'deliberation', 'mcp', ?, ?)", (cid, owner_sub, title[:200], ts, ts))
                self._conn.execute(
                    "INSERT INTO mcp_delib_jobs (job_id, root_job_id, owner_sub, conversation_id, finished_at, at) "
                    "VALUES (?, ?, ?, ?, ?, ?)", (job_id, root_job_id, owner_sub, cid, float(finished_at or 0), _now()))
            seq = self._conn.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM messages WHERE conversation_id = ?",
                                     (cid,)).fetchone()[0]
            for n, m in enumerate(messages):
                meta = m.get("meta")
                self._conn.execute(
                    "INSERT INTO messages (id, conversation_id, seq, role, persona, round, content, meta, ts) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (f"mcpd:{job_id}:{n}", cid, seq + n, m.get("role", "assistant"), m.get("persona"), m.get("round"),
                     str(m.get("content", "")), json.dumps(meta, ensure_ascii=False) if meta else None, ts))
            self._conn.execute("UPDATE conversations SET updated_at = MAX(updated_at, ?) WHERE id = ?", (ts, cid))
        return how

    def mcp_delib_conversation(self, owner_sub: str, job_id: str) -> str | None:
        """그 주인의 대화로 들인 잡이면 그 대화 id(대화가 남아 있을 때만). 아니면 None."""
        with self._lock:
            row = self._conn.execute(
                "SELECT j.conversation_id FROM mcp_delib_jobs j JOIN conversations c "
                "ON c.id = j.conversation_id AND c.owner_sub = j.owner_sub WHERE j.job_id = ? AND j.owner_sub = ?",
                (job_id, owner_sub)).fetchone()
        return row[0] if row else None

    def mcp_delib_jobs_in(self, cid: str, owner_sub: str) -> list[str]:
        """그 대화에 들인 잡 id 들(들인 차례). 남의 대화 · 없는 대화는 빈 목록."""
        with self._lock:
            if not self._owns(cid, owner_sub):
                return []
            rows = self._conn.execute("SELECT job_id FROM mcp_delib_jobs WHERE conversation_id = ? AND owner_sub = ? ORDER BY at",
                                      (cid, owner_sub)).fetchall()
        return [r[0] for r in rows]

    def cursor(self, k: str) -> float:
        with self._lock:
            row = self._conn.execute("SELECT since FROM conv_cursors WHERE k = ?", (k,)).fetchone()
        return float(row[0]) if row else 0.0

    def advance(self, k: str, since: float) -> float:
        """커서를 앞으로만 — 지금 값과 since 가운데 큰 것을 쓰고 돌려준다."""
        with self._lock, self._conn:
            self._conn.execute("INSERT INTO conv_cursors (k, since) VALUES (?, ?) "
                               "ON CONFLICT(k) DO UPDATE SET since = MAX(since, excluded.since)", (k, float(since)))
            row = self._conn.execute("SELECT since FROM conv_cursors WHERE k = ?", (k,)).fetchone()
        return float(row[0])

    # ── 의미검색 인덱스 ──────────────────────────────────────────────────────
    def unindexed(self, owner_sub: str, model: str, limit: int = 2000) -> list[dict]:
        """이 모델로 아직 색인 안 된 내 메시지. 색인은 증분이다.

        ⚠ model 조건이 있어야 한다. 없으면 임베딩 모델을 바꿨을 때 옛 모델 벡터가 존재한다는
        이유로 전부 '색인됨' 으로 판정되고, 읽는 쪽(vectors_for)은 새 모델로 걸러 0건을 본다 —
        검색이 영구히 빈손인데 통계는 전량 색인됐다고 말하는 상태가 된다.
        """
        with self._lock:
            rows = self._conn.execute(
                "SELECT m.id, m.conversation_id, m.content FROM messages m "
                "JOIN conversations c ON c.id = m.conversation_id "
                "LEFT JOIN message_vectors v "
                "       ON v.message_id = m.id AND v.model = ? "
                "WHERE c.owner_sub = ? AND v.message_id IS NULL "
                "ORDER BY m.ts DESC LIMIT ?",
                (model, owner_sub, limit),
            ).fetchall()
        return [{"message_id": r[0], "conversation_id": r[1], "content": r[2]} for r in rows]

    def remaining(self, owner_sub: str, model: str) -> int:
        """아직 색인 안 된 내 메시지 수. 부분 색인 위에서 나온 결과를 완전한 검색처럼
        보이게 하지 않으려면 이 값을 응답에 실어야 한다."""
        with self._lock:
            return self._conn.execute(
                "SELECT COUNT(*) FROM messages m "
                "JOIN conversations c ON c.id = m.conversation_id "
                "LEFT JOIN message_vectors v ON v.message_id = m.id AND v.model = ? "
                "WHERE c.owner_sub = ? AND v.message_id IS NULL",
                (model, owner_sub),
            ).fetchone()[0]

    def put_vectors(self, rows: list[dict]) -> int:
        """(message_id, chunk_ix) 단위 upsert. 같은 메시지를 다시 색인해도 중복되지 않는다."""
        if not rows:
            return 0
        now = _now()
        with self._lock, self._conn:
            self._conn.executemany(
                "INSERT OR REPLACE INTO message_vectors "
                "(message_id, chunk_ix, conversation_id, owner_sub, text, model, dim, vec, ts) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [(r["message_id"], r["chunk_ix"], r["conversation_id"], r["owner_sub"],
                  r["text"], r["model"], r["dim"], r["vec"], now) for r in rows],
            )
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
                "WHERE v.owner_sub = ? AND v.model = ? AND v.chunk_ix >= 0",
                (owner_sub, model),
            ).fetchall()

    def index_stats(self, owner_sub: str, model: str) -> dict:
        """messages/indexed 만 센다. chunk_ix=-1(짧아서 색인 대상 아님) 표식도 '처리됨'이다.

        ⚠ model 로 걸러야 한다. 안 그러면 옛 모델 벡터까지 세어 indexed 가 부풀고, 같은
        응답에 나란히 실리는 not_indexed_yet(모델별)과 숫자가 어긋난다 — 서로 안 맞는
        두 숫자를 함께 보여주는 것이 제일 나쁘다."""
        with self._lock:
            total = self._conn.execute(
                "SELECT COUNT(*) FROM messages m JOIN conversations c ON c.id = m.conversation_id "
                "WHERE c.owner_sub = ?", (owner_sub,)).fetchone()[0]
            indexed = self._conn.execute(
                "SELECT COUNT(DISTINCT message_id) FROM message_vectors "
                "WHERE owner_sub = ? AND model = ?", (owner_sub, model)).fetchone()[0]
        # 'pending' 을 total-indexed 로 내지 않는다 — 너무 짧아 색인 대상이 아닌 메시지가
        # 영영 남아 "아직 10개 남았다"가 고정 표시된다. 남은 일이 없는데 남았다고 말하는
        # 숫자는 그냥 거짓말이다. 색인 대상 판정은 청크 규칙을 아는 conv_search 가 한다.
        return {"messages": total, "indexed": indexed}
