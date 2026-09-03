# 이메일 로컬 계정 원장(SQLite) — SSO 지연 브리지. 계정 행은 SSO 전환 후에도 남는다.
"""Local email-account store.

conv_store 와 같은 패턴(stdlib sqlite3 + threading.Lock). 이메일이 영구 키(subject)다 —
나중에 SSO 가 붙으면 단언의 email 로 이 행을 찾아 연결하고(note_sso_login), 로그인
수단(auth_source)만 갱신한다. 비밀번호는 stdlib scrypt(의존성 無).
"""
import base64
import hashlib
import hmac
import json
import secrets
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path

from app.config import Settings

_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2**14, 8, 1
LOCK_AFTER_FAILS = 5          # 연속 실패 이 횟수에서 잠금
LOCK_SECONDS = 600            # 10분


def _now() -> int:
    return int(datetime.now(tz=UTC).timestamp())


def hash_password(pw: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(pw.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
    return (f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}"
            f"${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}")


def verify_password(pw: str, stored: str) -> bool:
    try:
        _, n, r, p, salt_b64, dk_b64 = stored.split("$")
        dk = hashlib.scrypt(pw.encode(), salt=base64.b64decode(salt_b64),
                            n=int(n), r=int(r), p=int(p))
        return hmac.compare_digest(dk, base64.b64decode(dk_b64))
    except (ValueError, TypeError):
        return False


def norm_email(email: str) -> str:
    return email.strip().lower()


class UserStore:
    def __init__(self, settings: Settings) -> None:
        raw = getattr(settings, "user_store_path", None) or "data/users.sqlite"
        path = Path(settings.resolve(raw))
        path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS users ("
            "email TEXT PRIMARY KEY, name TEXT NOT NULL, pw_hash TEXT, "
            "groups TEXT NOT NULL DEFAULT '[]', "          # JSON 배열 — require_role 이 보는 역할
            "status TEXT NOT NULL DEFAULT 'pending', "     # pending | active | disabled
            "auth_source TEXT NOT NULL DEFAULT 'local', "  # local | sso — 마지막 로그인 수단
            "created_at INTEGER NOT NULL, approved_at INTEGER, approved_by TEXT, "
            "last_login_at INTEGER, failed_count INTEGER NOT NULL DEFAULT 0, "
            "locked_until INTEGER NOT NULL DEFAULT 0)"
        )
        self._conn.commit()

    # ── 조회 ────────────────────────────────────────────────────────────────
    def get(self, email: str) -> dict | None:
        cur = self._conn.execute("SELECT * FROM users WHERE email = ?", (norm_email(email),))
        row = cur.fetchone()
        if row is None:
            return None
        cols = [c[0] for c in cur.description]
        d = dict(zip(cols, row, strict=True))
        d["groups"] = json.loads(d.get("groups") or "[]")
        return d

    def list_users(self) -> list[dict]:
        cur = self._conn.execute(
            "SELECT email, name, groups, status, auth_source, created_at, approved_at, "
            "last_login_at, locked_until FROM users ORDER BY created_at DESC")
        cols = [c[0] for c in cur.description]
        out = []
        for row in cur.fetchall():
            d = dict(zip(cols, row, strict=True))
            d["groups"] = json.loads(d.get("groups") or "[]")
            out.append(d)
        return out

    def count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    def count_local(self) -> int:
        """비밀번호를 가진(=로컬 가입) 계정 수 — SSO 가 먼저 원장 행을 만들어도
        부트스트랩 창이 닫히지 않도록 부트스트랩 판정은 이걸 쓴다."""
        return self._conn.execute(
            "SELECT COUNT(*) FROM users WHERE pw_hash IS NOT NULL").fetchone()[0]

    # ── 가입·승인 ───────────────────────────────────────────────────────────
    def signup(self, *, email: str, name: str, password: str,
               bootstrap_admins: list[str]) -> dict:
        """가입 신청. 원칙은 pending — 단 테이블이 비어 있고 부트스트랩 명단에 든 이메일이면
        즉시 active+portal-admin (첫 관리자를 만들 다른 경로가 없다)."""
        email = norm_email(email)
        with self._lock:
            if self.get(email) is not None:
                raise ValueError("already exists")
            bootstrap = (self.count_local() == 0
                         and email in [norm_email(e) for e in bootstrap_admins])
            status = "active" if bootstrap else "pending"
            groups = ["portal-admin"] if bootstrap else []
            now = _now()
            self._conn.execute(
                "INSERT INTO users (email, name, pw_hash, groups, status, created_at, "
                "approved_at, approved_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (email, name.strip()[:80], hash_password(password), json.dumps(groups),
                 status, now, now if bootstrap else None, "bootstrap" if bootstrap else None))
            self._conn.commit()
        return {"email": email, "status": status}

    def approve(self, email: str, *, by: str, groups: list[str] | None = None) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "UPDATE users SET status = 'active', approved_at = ?, approved_by = ?, "
                "groups = COALESCE(?, groups) WHERE email = ? AND status = 'pending'",
                (_now(), norm_email(by), json.dumps(groups) if groups is not None else None,
                 norm_email(email)))
            self._conn.commit()
            return cur.rowcount > 0

    def set_status(self, email: str, status: str) -> bool:
        if status not in ("active", "disabled"):
            raise ValueError("bad status")
        with self._lock:
            cur = self._conn.execute(
                "UPDATE users SET status = ? WHERE email = ?", (status, norm_email(email)))
            self._conn.commit()
            return cur.rowcount > 0

    def set_password(self, email: str, password: str) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "UPDATE users SET pw_hash = ?, failed_count = 0, locked_until = 0 "
                "WHERE email = ?", (hash_password(password), norm_email(email)))
            self._conn.commit()
            return cur.rowcount > 0

    def set_groups(self, email: str, groups: list[str]) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "UPDATE users SET groups = ? WHERE email = ?",
                (json.dumps(list(groups)), norm_email(email)))
            self._conn.commit()
            return cur.rowcount > 0

    # ── 로그인 ──────────────────────────────────────────────────────────────
    def verify_login(self, *, email: str, password: str) -> dict:
        """성공 시 user dict. 실패는 ValueError(사유) — 호출부는 사유를 사용자에게
        구분해 주지 않는다(계정 존재 여부 노출 방지). 잠금만 별도 문구."""
        email = norm_email(email)
        u = self.get(email)
        # 계정 유무와 무관하게 해시 1회를 태워 타이밍 차이를 줄인다.
        if u is None or not u.get("pw_hash"):
            verify_password(password, hash_password("timing-equalizer"))
            raise ValueError("bad credentials")
        now = _now()
        if u["locked_until"] > now:
            raise ValueError("locked")
        if not verify_password(password, u["pw_hash"]):
            with self._lock:
                fails = u["failed_count"] + 1
                locked = now + LOCK_SECONDS if fails >= LOCK_AFTER_FAILS else 0
                self._conn.execute(
                    "UPDATE users SET failed_count = ?, locked_until = ? WHERE email = ?",
                    (0 if locked else fails, locked, email))
                self._conn.commit()
            raise ValueError("locked" if locked else "bad credentials")
        if u["status"] != "active":
            raise ValueError("not active")
        with self._lock:
            self._conn.execute(
                "UPDATE users SET failed_count = 0, locked_until = 0, last_login_at = ?, "
                "auth_source = 'local' WHERE email = ?", (now, email))
            self._conn.commit()
        return u

    # ── SSO 연동(미래) ──────────────────────────────────────────────────────
    def note_sso_login(self, *, email: str, name: str | None) -> None:
        """SSO 콜백 훅 — 같은 이메일 행이 있으면 연결(auth_source 갱신), 없으면 원장에
        생성(active — IdP 가 이미 신원을 보증). 계정·비밀번호 해시는 남는다."""
        email = norm_email(email)
        now = _now()
        with self._lock:
            if self.get(email) is None:
                self._conn.execute(
                    "INSERT INTO users (email, name, groups, status, auth_source, created_at, "
                    "approved_at, approved_by, last_login_at) "
                    "VALUES (?, ?, '[]', 'active', 'sso', ?, ?, 'sso', ?)",
                    (email, (name or email)[:80], now, now, now))
            else:
                self._conn.execute(
                    "UPDATE users SET auth_source = 'sso', last_login_at = ? WHERE email = ?",
                    (now, email))
            self._conn.commit()
