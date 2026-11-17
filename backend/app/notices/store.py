# 포털 알림 원장 — 사람마다 쌓이는 알림 한 줄(kind · 제목 · 한 줄 · 링크)을 대화 저장소 파일 안의 표 둘에 둔다(docs/request-1117 contracts §7)
"""왜 대화 저장소 파일인가 — 새 sqlite 파일은 데이터 경로 레지스트리(infra/services.yaml — cae00 은 /data 로 옮기는 needs_bind 클래스가 되어 update-all
이 재기동하며 옮긴다) · 백업(backup-local.sh) · 기동 env 전달(start.sh) · 화면 점검(ui-check.sh) · 시험 격리(conftest)에 모두 새로 올려야 한다. 알림은 사람이
만든 것과 같은 몫의 사람별 데이터(대화와 같은 mirror)라 이미 그 모든 곳에 오른 conversations.sqlite 에 표를 더한다 — 과제 인사이트가 절차 저장소에
표를 더한 것과 같은 길이다. 연결은 따로 연다(대화 저장소의 잠금을 다투지 않는다 — 파일은 대화 저장소가 기동 때 WAL 로 바꿔 둔다).

- 같은 원천은 한 줄이다 — (kind, source_id) 유일 색인 + INSERT OR IGNORE. 당기기가 재기동 · 여러 일꾼 · 경계 겹침으로 같은 묶음을 다시 받아도 하나다.
- 주인은 포털 계정 이메일(소문자)이다 — 포털은 사람을 원장(users.email)으로 가린다. 읽기 · 읽음 표시는 늘 그 사람의 줄만 본다.
- 링크는 포털 안 경로만 싣는다(safe_link) — 바깥 주소 · '//' 로 시작하는 주소는 버린다. 화면도 한 번 더 본다.
- 커서(당기기의 since)는 앞으로만 간다(advance — MAX) — 두 일꾼이 서로 다른 값을 써도 뒤로 가지 않는다.
"""
from __future__ import annotations

import re
import sqlite3
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path

KIND_MAX, TITLE_MAX, LINE_MAX, LINK_MAX, SOURCE_MAX = 40, 200, 500, 500, 200
LIST_DEFAULT, LIST_MAX = 50, 200

_DDL = (
    """CREATE TABLE IF NOT EXISTS notices (
        id TEXT PRIMARY KEY, user_email TEXT NOT NULL, kind TEXT NOT NULL, title TEXT NOT NULL, line TEXT NOT NULL,
        link TEXT, source_id TEXT NOT NULL, created_at INTEGER NOT NULL, read_at INTEGER)""",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_notice_source ON notices (kind, source_id)",
    "CREATE INDEX IF NOT EXISTS ix_notice_user ON notices (user_email, created_at)",
    "CREATE TABLE IF NOT EXISTS notice_cursors (k TEXT PRIMARY KEY, since REAL NOT NULL)",
)
_COLS = "id, kind, title, line, link, source_id, created_at, read_at"
# 줄바꿈 · 제어 문자(유니코드 줄 나눔 포함)는 빈칸 하나로 — 알림은 한 줄이다
_CTRL = re.compile(r"[\x00-\x1f\x7f\x85  ]+")


def _now() -> int:
    return int(datetime.now(tz=UTC).timestamp())


def one_line(v, cap: int) -> str:
    """글 하나를 한 줄로(제어 문자 → 빈칸, 겹친 빈칸 하나로) · cap 자까지."""
    return re.sub(r" {2,}", " ", _CTRL.sub(" ", str(v or ""))).strip()[:cap]


def safe_link(v) -> str | None:
    """포털 안 경로만 — '/' 로 시작하고 '//' 가 아니며 역슬래시 · 제어 문자가 없다. 아니면 None(링크 없이 싣는다)."""
    if not isinstance(v, str):
        return None
    s = v.strip()
    if not s.startswith("/") or s.startswith("//") or "\\" in s or _CTRL.search(s) or len(s) > LINK_MAX:
        return None
    return s


class NoticeStore:
    def __init__(self, settings) -> None:
        raw = getattr(settings, "conv_store_path", None) or "data/conversations.sqlite"
        self.path = Path(settings.resolve(raw))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        # 대화 저장소와 같은 잠금 대기 — 그쪽이 쓰는 동안만 걸린다(WAL). 넘으면 쓰는 쪽(당기기)이 예외로 알고 다음 틱에 다시 한다.
        self._conn.execute(f"PRAGMA busy_timeout={int(float(getattr(settings, 'conv_store_busy_timeout_s', 30.0)) * 1000)}")
        # 쓰기는 늘 `with self._lock, self._conn:` — 끝에서 commit, 도중 실패면 rollback(conv_store.py 의 ⚠ 와 같은 까닭).
        with self._lock, self._conn:
            for stmt in _DDL:
                self._conn.execute(stmt)

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # ── 쓰기 ──
    def add(self, *, user_email: str, kind: str, title: str, line: str, source_id: str, link: str | None = None,
            created_at: int | None = None) -> str | None:
        """알림 한 줄 — 새로 넣었으면 그 id, 같은 (kind, source_id) 가 이미 있으면 None(아무것도 바꾸지 않는다)."""
        who, k, src = (user_email or "").strip().lower(), one_line(kind, KIND_MAX), one_line(source_id, SOURCE_MAX)
        if "@" not in who or not k or not src:
            raise ValueError("알림에는 주인(이메일) · kind · source_id 가 있어야 한다")
        nid = uuid.uuid4().hex
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT OR IGNORE INTO notices (id, user_email, kind, title, line, link, source_id, created_at, read_at)"
                " VALUES (?,?,?,?,?,?,?,?,NULL)",
                (nid, who, k, one_line(title, TITLE_MAX), one_line(line, LINE_MAX), safe_link(link), src,
                 int(created_at) if created_at else _now()))
        return nid if cur.rowcount == 1 else None

    def mark_read(self, user_email: str, nid: str) -> bool:
        """그 사람의 알림 하나를 읽음으로 — 그 사람의 것이면(이미 읽었어도) 참, 없거나 남의 것이면 거짓. 처음 읽은 시각은 바꾸지 않는다."""
        with self._lock, self._conn:
            cur = self._conn.execute("UPDATE notices SET read_at = COALESCE(read_at, ?) WHERE id = ? AND user_email = ?",
                                     (_now(), nid, (user_email or "").strip().lower()))
        return cur.rowcount == 1

    def mark_all_read(self, user_email: str) -> int:
        """그 사람의 안 읽은 알림을 모두 읽음으로 → 바꾼 수."""
        with self._lock, self._conn:
            cur = self._conn.execute("UPDATE notices SET read_at = ? WHERE user_email = ? AND read_at IS NULL",
                                     (_now(), (user_email or "").strip().lower()))
        return cur.rowcount

    # ── 읽기 ──
    def list_for(self, user_email: str, *, limit: int = LIST_DEFAULT) -> list[dict]:
        """그 사람의 알림 — 최신 것부터 limit 개(LIST_MAX 까지)."""
        lim = max(1, min(int(limit), LIST_MAX))
        with self._lock:
            rows = self._conn.execute(f"SELECT {_COLS} FROM notices WHERE user_email = ? ORDER BY created_at DESC, rowid DESC LIMIT ?",
                                      ((user_email or "").strip().lower(), lim)).fetchall()
        return [dict(r) for r in rows]

    def unread(self, user_email: str) -> int:
        with self._lock:
            return int(self._conn.execute("SELECT COUNT(*) FROM notices WHERE user_email = ? AND read_at IS NULL",
                                          ((user_email or "").strip().lower(),)).fetchone()[0])

    def find(self, kind: str, source_id: str) -> dict | None:
        """그 원천의 알림(있으면) — 당기기 시험 · 점검용."""
        with self._lock:
            r = self._conn.execute(f"SELECT user_email, {_COLS} FROM notices WHERE kind = ? AND source_id = ?",
                                   (kind, source_id)).fetchone()
        return dict(r) if r else None

    # ── 커서 ──
    def cursor(self, k: str) -> float:
        with self._lock:
            r = self._conn.execute("SELECT since FROM notice_cursors WHERE k = ?", (k,)).fetchone()
        return float(r[0]) if r else 0.0

    def advance(self, k: str, since: float) -> float:
        """커서를 since 로 — 지금 값보다 클 때만(앞으로만). 남은 값을 돌려준다."""
        with self._lock, self._conn:
            self._conn.execute("INSERT INTO notice_cursors (k, since) VALUES (?, ?) "
                               "ON CONFLICT(k) DO UPDATE SET since = MAX(since, excluded.since)", (k, float(since)))
            return float(self._conn.execute("SELECT since FROM notice_cursors WHERE k = ?", (k,)).fetchone()[0])
