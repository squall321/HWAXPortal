"""Agent/MCP audit log (SQLite) — who/when/which tool/which status.

Compliance-driven and present from Phase 1 (NOT deferred): design-data access through the
chat must be traceable, and an audit trail cannot be back-filled. Mirrors TokenStore's
stdlib-sqlite shape; swap for a central store at multi-instance prod scale.
"""

import json
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path

from app.config import Settings


class AuditLog:
    def __init__(self, settings: Settings) -> None:
        path = Path(settings.resolve(settings.agent_audit_log_path))
        path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS agent_audit ("
            " id INTEGER PRIMARY KEY AUTOINCREMENT,"
            " ts INTEGER NOT NULL,"
            " principal TEXT NOT NULL,"   # subject / email
            " chat_id TEXT,"
            " event TEXT NOT NULL,"       # chat_start | tool_call | chat_done | chat_error
            " tool TEXT,"                 # tool name when event=tool_call
            " status TEXT,"               # ok | error | cancelled | rejected
            " meta TEXT"                  # JSON blob (free-form context)
            ")"
        )
        self._conn.commit()

    def record(
        self,
        *,
        principal: str,
        event: str,
        chat_id: str | None = None,
        tool: str | None = None,
        status: str | None = None,
        meta: dict | None = None,
    ) -> None:
        now = int(datetime.now(tz=UTC).timestamp())
        with self._lock:
            self._conn.execute(
                "INSERT INTO agent_audit (ts, principal, chat_id, event, tool, status, meta)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (now, principal, chat_id, event, tool, status,
                 json.dumps(meta, ensure_ascii=False) if meta else None),
            )
            self._conn.commit()
