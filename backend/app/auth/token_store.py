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
            self._conn.execute(
                "INSERT INTO pat (jti, sub, email, name, aud, scopes, created, exp, revoked) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)",
                (jti, sub, email, name, json.dumps(aud), json.dumps(scopes), created, exp),
            )
            self._conn.commit()

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
        """Mark a PAT revoked. sub=None → admin (any owner); else only the owner. True if changed."""
        with self._lock:
            if sub is None:
                cur = self._conn.execute("UPDATE pat SET revoked = 1 WHERE jti = ?", (jti,))
            else:
                cur = self._conn.execute(
                    "UPDATE pat SET revoked = 1 WHERE jti = ? AND sub = ?", (jti, sub)
                )
            self._conn.commit()
            return cur.rowcount > 0

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
