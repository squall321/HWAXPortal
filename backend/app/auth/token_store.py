"""Durable token state (SQLite) behind a small interface.

Pilot scale = single instance, so SQLite (stdlib, no ORM) gives the durability that an
in-process dict lacks (survives restart) without operating Redis. At multi-instance prod
scale, swap in a Redis-backed implementation behind the same `TokenStore` methods.

Currently used for launch-token replay defense (single-use jti) and the portal PAT
registry/denylist (issued long-lived tokens + their revocation).
"""

import json
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path

from app.config import Settings


class TokenStore:
    def __init__(self, settings: Settings) -> None:
        path = Path(settings.resolve(settings.token_store_path))
        path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS used_jti (jti TEXT PRIMARY KEY, exp INTEGER NOT NULL)"
        )
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS pat ("
            "jti TEXT PRIMARY KEY, sub TEXT NOT NULL, email TEXT, name TEXT, "
            "aud TEXT NOT NULL, scopes TEXT NOT NULL, "
            "created INTEGER NOT NULL, exp INTEGER NOT NULL, revoked INTEGER NOT NULL DEFAULT 0)"
        )
        # 토큰 교환(`/auth/pat/exchange`)으로 받은 PAT 의 원 jti — 원을 폐기하면 자식도 폐기한다.
        # 돌고 있는 원장에도 칸이 생겨야 한다(새 DB 에만 있으면 읽는 길이 운영에서만 터진다).
        if "parent_jti" not in {r[1] for r in self._conn.execute("PRAGMA table_info(pat)")}:
            self._conn.execute("ALTER TABLE pat ADD COLUMN parent_jti TEXT")
        self._conn.commit()

    def mark_jti_once(self, jti: str, exp: int) -> bool:
        """Record a jti as used. Returns True on first use, False if already seen (replay)."""
        now = int(datetime.now(tz=UTC).timestamp())
        with self._lock:
            self._conn.execute("DELETE FROM used_jti WHERE exp < ?", (now,))  # opportunistic GC
            try:
                self._conn.execute("INSERT INTO used_jti (jti, exp) VALUES (?, ?)", (jti, exp))
                self._conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    # ── Portal PAT registry (issue / list / revoke) + published denylist ──────────
    def record_pat(self, *, jti: str, sub: str, email: str | None, name: str,
                   aud: list[str], scopes: list[str], created: int, exp: int) -> None:
        with self._lock:
            self._insert_pat(jti, sub, email, name, aud, scopes, created, exp, None)
            self._conn.commit()

    def record_exchanged_pat(self, *, parent_jti: str, jti: str, sub: str, email: str | None,
                             name: str, aud: list[str], scopes: list[str], created: int,
                             exp: int) -> str | None:
        """교환으로 받은 PAT 을 기록한다. 기록했으면 None, 못 했으면 그 까닭(code)이다.

        같은 이름의 앞선 교환 PAT 을 여기서 폐기하지 않는다(context-notes C-11) — 소비자가 새것을
        받아들이기 전에 옛것을 죽이면, 소비자가 새것을 거절했을 때 폐기된 옛것만 쥐고 남는다. 옛것은
        소비자가 새것을 받아들인 뒤 `/auth/pat/revoke-self` 로 스스로 폐기한다.

        `source_revoked` — 원이 그사이 폐기됐다. 검사와 기록 사이에 원을 폐기하면 연쇄가 아직 없는
        자식을 못 보고, 자식이 원의 폐기를 피해 살아남는다. 폐기도 같은 잠금을 쥐므로 여기서 보면
        닫힌다. 원이 될 수 있는지는 `pat_is_exchangeable` 이 이미 봤다 — 여기는 '그사이 폐기'
        하나만 본다."""
        with self._lock:
            if self._conn.execute("SELECT 1 FROM pat WHERE jti = ? AND revoked = 1",
                                  (parent_jti,)).fetchone():
                return "source_revoked"
            self._insert_pat(jti, sub, email, name, aud, scopes, created, exp, parent_jti)
            self._conn.commit()
            return None

    def _insert_pat(self, jti, sub, email, name, aud, scopes, created, exp, parent_jti) -> None:
        self._conn.execute(
            "INSERT INTO pat (jti, sub, email, name, aud, scopes, created, exp, revoked, "
            "parent_jti) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)",
            (jti, sub, email, name, json.dumps(aud), json.dumps(scopes), created, exp, parent_jti),
        )

    def pat_is_exchangeable(self, jti: str, sub: str) -> bool:
        """토큰 교환의 원이 될 수 있나 — 토큰 화면(`/auth/pat`)에서 사람이 낸 살아 있는 PAT 만이다.

        챗·절차 PAT 은 여기 기록되지 않으므로 거절된다(24시간짜리로 90일짜리를 받는 수명 늘리기).
        교환으로 받은 PAT(parent 있음)도 원이 못 된다 — 자식이 다시 원이 되면 폐기 연쇄가 한 단만
        내려가 손자가 원 PAT 의 폐기를 피해 살아남는다."""
        with self._lock:
            row = self._conn.execute(
                "SELECT 1 FROM pat WHERE jti = ? AND sub = ? AND revoked = 0 "
                "AND parent_jti IS NULL", (jti, sub)).fetchone()
        return row is not None

    def count_pats(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) FROM pat").fetchone()[0]

    def all_pats(self, limit: int = 500) -> list[dict]:
        """전체 소유자의 PAT 메타(토큰 자체는 절대 아님). 관리자 전용.

        왜 필요한가 — 무기한 토큰은 만료로 안 죽고 폐기로만 죽는데, 관리자가 남의 토큰을
        '찾을' 방법이 없으면 그 폐기를 실행할 수 없다. 통제 수단이 있다고 적어 놓고
        실행 경로가 없으면 없는 것과 같다.
        """
        with self._lock:
            # ⚠ created DESC 로 자르면 안 된다. 무기한 토큰은 정의상 가장 오래 남는 쪽이라,
            # 정확히 폐기해야 할 것부터 목록에서 사라진다. 만료가 먼 것(= 오래 사는 것)을
            # 먼저 보여 준다 — 이 목록의 존재 이유가 그것이다.
            cur = self._conn.execute(
                "SELECT jti, name, aud, scopes, created, exp, revoked, sub, email FROM pat "
                "ORDER BY revoked ASC, exp DESC, created DESC LIMIT ?", (limit,))
            rows = cur.fetchall()
        return [{"jti": r[0], "name": r[1], "audiences": json.loads(r[2]),
                 "scopes": json.loads(r[3]), "created": r[4], "exp": r[5],
                 "revoked": bool(r[6]), "sub": r[7], "email": r[8]} for r in rows]

    def list_pats(self, sub: str) -> list[dict]:
        """Metadata (never the token itself) for one owner's PATs, newest first."""
        with self._lock:
            cur = self._conn.execute(
                "SELECT jti, name, aud, scopes, created, exp, revoked FROM pat "
                "WHERE sub = ? ORDER BY created DESC",
                (sub,),
            )
            rows = cur.fetchall()
        return [
            {"jti": r[0], "name": r[1], "audiences": json.loads(r[2]),
             "scopes": json.loads(r[3]), "created": r[4], "exp": r[5], "revoked": bool(r[6])}
            for r in rows
        ]

    def revoke_pat(self, jti: str, sub: str | None = None) -> bool:
        """Mark a PAT revoked. sub=None → admin (any owner); else only the owner.

        True if the row exists — 이미 폐기된 행도 True 다(SQLite UPDATE 는 값이 같아도 맞은 행을
        센다). `/auth/pat/revoke-self` 의 멱등이 이것에 기댄다.

        그 PAT 을 원으로 교환해 받은 자식도 함께 폐기한다(연쇄) — 안 하면 자식이 원의 폐기를 피해
        살아남는다."""
        with self._lock:
            if sub is None:
                cur = self._conn.execute("UPDATE pat SET revoked = 1 WHERE jti = ?", (jti,))
            else:
                cur = self._conn.execute(
                    "UPDATE pat SET revoked = 1 WHERE jti = ? AND sub = ?", (jti, sub)
                )
            if cur.rowcount > 0:
                self._conn.execute(
                    "UPDATE pat SET revoked = 1 WHERE parent_jti = ? AND revoked = 0", (jti,))
            self._conn.commit()
            return cur.rowcount > 0

    def revoke_all_for(self, email: str) -> int:
        """그 사람의 **살아 있는 PAT 을 전부** 폐기한다. 폐기한 개수를 돌려준다.

        ⚠ 계정 정지가 토큰까지 죽이지 않으면 정지가 절반만 듣는다 — 권한 계산은 막혀도
        (`compute` 가 정지면 0개) **서명 자체는 여전히 유효**해서, 자격을 안 보는 경로가
        생기는 순간 다시 뚫린다. 무기한 토큰은 만료로 안 죽고 폐기로만 죽는다(7차 감사).
        """
        e = (email or "").strip().lower()
        if not e:
            return 0
        with self._lock:
            cur = self._conn.execute(
                "UPDATE pat SET revoked = 1 WHERE lower(email) = ? AND revoked = 0", (e,))
            self._conn.commit()
            return cur.rowcount

    def revoked_jtis(self) -> list[str]:
        """Non-expired revoked jtis — the denylist the REST gateway polls. GCs expired rows."""
        now = int(datetime.now(tz=UTC).timestamp())
        with self._lock:
            self._conn.execute("DELETE FROM pat WHERE exp < ?", (now,))  # opportunistic GC
            self._conn.commit()
            cur = self._conn.execute(
                "SELECT jti FROM pat WHERE revoked = 1 AND exp >= ?", (now,)
            )
            return [r[0] for r in cur.fetchall()]
