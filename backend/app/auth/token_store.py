"""Durable token state (SQLite) behind a small interface.

Pilot scale = single instance, so SQLite (stdlib, no ORM) gives the durability that an
in-process dict lacks (survives restart) without operating Redis. At multi-instance prod
scale, swap in a Redis-backed implementation behind the same `TokenStore` methods.

Currently used for launch-token replay defense (single-use jti). The same store is the
natural home for refresh-token revocation later.
"""

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
