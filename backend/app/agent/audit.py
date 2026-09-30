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
        # 서비스 접속 원장 — 누가(email) 어디서(ip) 언제 어느 서비스에 들어갔나(docs/access-history).
        # agent_audit 의 meta JSON 에 넣지 않고 표를 따로 둔다: IP·서비스로 찾을 때마다 JSON 을 풀지 않게,
        # 그리고 principal(subject)이 아니라 이메일로 찾게(D-3). 같은 파일·같은 잠금이다.
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS access_log ("
            " id INTEGER PRIMARY KEY AUTOINCREMENT,"
            " ts INTEGER NOT NULL,"
            " email TEXT NOT NULL,"       # 소문자. login_fail 은 **시도한** 이메일(주장일 뿐)
            " event TEXT NOT NULL,"       # login | login_fail | launch | open
            " service TEXT,"              # 시스템 id(로그인은 portal)
            " ip TEXT, ua TEXT,"
            " uid TEXT,"                  # 로그인 연결 ID(hwax_uid 쿠키) — nginx 로그와 잇는 열쇠
            " detail TEXT"                # local·sso·primer·credential·실패 사유
            ")"
        )
        self._conn.execute("CREATE INDEX IF NOT EXISTS access_log_email_ts ON access_log(email, ts)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS access_log_ts ON access_log(ts)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS access_log_uid ON access_log(uid)")
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

    def record_access(self, *, email: str, event: str, service: str | None = None, ip: str | None = None,
                      ua: str | None = None, uid: str | None = None, detail: str | None = None) -> None:
        now = int(datetime.now(tz=UTC).timestamp())
        with self._lock:
            self._conn.execute(
                "INSERT INTO access_log (ts, email, event, service, ip, ua, uid, detail)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (now, (email or "").strip().lower()[:200], event, service, ip or None,
                 (ua or "")[:200] or None, uid, (detail or "")[:120] or None),
            )
            self._conn.commit()

    def query_access(self, *, email: str | None = None, service: str | None = None, event: str | None = None,
                     since: int = 0, include_auto: bool = False, limit: int = 500) -> list[dict]:
        """최신 것부터. `include_auto=False` 면 화면의 SSO 미리 로그인(detail=primer)을 뺀다 — 45분마다 저절로 쌓인다."""
        where, args = ["ts >= ?"], [since]
        if email:
            where.append("email = ?"); args.append(email.strip().lower())
        if service:
            where.append("service = ?"); args.append(service)
        if event:
            where.append("event = ?"); args.append(event)
        if not include_auto:
            where.append("(detail IS NULL OR detail != 'primer')")
        with self._lock:
            rows = self._conn.execute(
                "SELECT ts, email, event, service, ip, ua, uid, detail FROM access_log WHERE "
                + " AND ".join(where) + " ORDER BY ts DESC, id DESC LIMIT ?", (*args, limit)).fetchall()
        keys = ("ts", "email", "event", "service", "ip", "ua", "uid", "detail")
        return [dict(zip(keys, r)) for r in rows]

    def uids_for(self, email: str, since: int) -> set[str]:
        """그 사람이 `since` 이후 로그인하며 받은 연결 ID 들."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT DISTINCT uid FROM access_log WHERE email = ? AND event = 'login' AND uid IS NOT NULL"
                " AND ts >= ?", (email.strip().lower(), since)).fetchall()
        return {r[0] for r in rows}

    def close(self) -> None:
        with self._lock:
            self._conn.close()
