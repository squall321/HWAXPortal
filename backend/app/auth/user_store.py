# 이메일 로컬 계정 원장(SQLite) — SSO 지연 브리지. 계정 행은 SSO 전환 후에도 남는다.
"""Local email-account store.

conv_store 와 같은 패턴(stdlib sqlite3 + threading.Lock). 이메일이 영구 키(subject)다 —
나중에 SSO 가 붙으면 단언의 email 로 이 행을 찾아 연결하고(note_sso_login), 로그인
수단(auth_source)만 갱신한다. 비밀번호는 stdlib scrypt(의존성 無).
"""
import base64
import contextlib
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
        # 연결 하나를 스레드풀이 나눠 쓴다(check_same_thread=False) — 읽기도 잠가야 한다. 권한을 요청마다
        # 계산하면서 get() 이 모든 요청에서 동시에 돌자 'bad parameter or other API misuse'·열 개수
        # 불일치로 500 이 났다(dev 실측). 쓰기 안에서 get() 을 부르므로 재진입 잠금이다.
        self._lock = threading.RLock()
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
        # 부서 — 가입 폼 입력(또는 RA 연동 시 자동 채움). 기존 DB 는 컬럼 추가 마이그레이션.
        with contextlib.suppress(sqlite3.OperationalError):  # 이미 있으면 무시
            self._conn.execute("ALTER TABLE users ADD COLUMN department TEXT NOT NULL DEFAULT ''")
        # 소속·개별 허가 — 권한 계산의 입력(docs/access-control). 소속은 관리자만 정한다 — 부서(자유
        # 텍스트, 본인 입력)와 따로 둔다. 본인이 바꿀 수 있는 값이 권한이 되면 스스로 올릴 수 있다.
        with contextlib.suppress(sqlite3.OperationalError):
            self._conn.execute("ALTER TABLE users ADD COLUMN affiliation TEXT NOT NULL DEFAULT ''")
        with contextlib.suppress(sqlite3.OperationalError):
            self._conn.execute("ALTER TABLE users ADD COLUMN grants TEXT NOT NULL DEFAULT '[]'")
        # 허가 요청 — 사용자가 내 권한 페이지에서 보내고 관리자가 승인·거절한다.
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS access_requests ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL, key TEXT NOT NULL, "
            # status: pending | approved | rejected
            "note TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'pending', "
            "created_at INTEGER NOT NULL, decided_at INTEGER, decided_by TEXT)"
        )
        # 외부 서비스 연결 토큰(예: Report Archive PAT) — 사용자가 등록, 게이트웨이가 소비.
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS connections ("
            "email TEXT NOT NULL, service TEXT NOT NULL, token TEXT NOT NULL, "
            "workspace TEXT NOT NULL DEFAULT '', "   # RA 부서(워크스페이스) slug — 호출 헤더용
            "created_at INTEGER NOT NULL, PRIMARY KEY (email, service))"
        )
        self._conn.commit()

    # ── 조회 ────────────────────────────────────────────────────────────────
    def get(self, email: str) -> dict | None:
        with self._lock:
            cur = self._conn.execute("SELECT * FROM users WHERE email = ?", (norm_email(email),))
            row = cur.fetchone()
            cols = [c[0] for c in cur.description] if row is not None else []
        if row is None:
            return None
        d = dict(zip(cols, row, strict=True))
        d["groups"] = json.loads(d.get("groups") or "[]")
        d["grants"] = json.loads(d.get("grants") or "[]")
        return d

    def list_users(self) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT email, name, department, affiliation, grants, groups, status, auth_source, "
                "created_at, approved_at, last_login_at, locked_until FROM users "
                "ORDER BY created_at DESC")
            cols = [c[0] for c in cur.description]
            rows = cur.fetchall()
        out = []
        for row in rows:
            d = dict(zip(cols, row, strict=True))
            d["groups"] = json.loads(d.get("groups") or "[]")
            d["grants"] = json.loads(d.get("grants") or "[]")
            out.append(d)
        return out

    def count(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    def count_local(self) -> int:
        """비밀번호를 가진(=로컬 가입) 계정 수 — SSO 가 먼저 원장 행을 만들어도
        부트스트랩 창이 닫히지 않도록 부트스트랩 판정은 이걸 쓴다."""
        with self._lock:
            return self._conn.execute(
                "SELECT COUNT(*) FROM users WHERE pw_hash IS NOT NULL").fetchone()[0]

    # ── 가입·승인 ───────────────────────────────────────────────────────────
    def signup(self, *, email: str, name: str, password: str,
               bootstrap_admins: list[str], department: str = "") -> dict:
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
                "approved_at, approved_by, department) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (email, name.strip()[:80], hash_password(password), json.dumps(groups),
                 status, now, now if bootstrap else None, "bootstrap" if bootstrap else None,
                 department.strip()[:80]))
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

    def set_department(self, email: str, department: str) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "UPDATE users SET department = ? WHERE email = ?",
                (department.strip()[:80], norm_email(email)))
            self._conn.commit()
            return cur.rowcount > 0

    # ── 외부 서비스 연결 토큰(RA PAT 등) ─────────────────────────────────────
    def set_connection(self, *, email: str, service: str, token: str, workspace: str = "") -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO connections (email, service, token, workspace, created_at) "
                "VALUES (?, ?, ?, ?, ?)", (norm_email(email), service, token, workspace, _now()))
            self._conn.commit()

    def get_connection(self, *, email: str, service: str) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT token, workspace FROM connections WHERE email = ? AND service = ?",
                (norm_email(email), service)).fetchone()
        return {"token": row[0], "workspace": row[1]} if row else None

    def set_connection_workspace(self, *, email: str, service: str, workspace: str) -> bool:
        """토큰은 그대로 두고 워크스페이스만 바꾼다.

        set_connection 을 쓰면 토큰을 다시 받아야 하는데, 조직만 옮기는 사람에게 PAT 재발급을
        시키는 것은 과하다(그리고 그 과정에서 토큰이 한 번 더 사람 손을 탄다).
        """
        with self._lock:
            cur = self._conn.execute(
                "UPDATE connections SET workspace = ? WHERE email = ? AND service = ?",
                (workspace, norm_email(email), service))
            self._conn.commit()
            return cur.rowcount > 0

    def delete_connection(self, *, email: str, service: str) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM connections WHERE email = ? AND service = ?",
                (norm_email(email), service))
            self._conn.commit()
            return cur.rowcount > 0

    def connection_meta(self, *, email: str, service: str) -> dict | None:
        """토큰 원문 없이 표시용 요약만 — 꼬리 4자·부서·등록 시각."""
        with self._lock:
            row = self._conn.execute(
                "SELECT token, workspace, created_at FROM connections "
                "WHERE email = ? AND service = ?", (norm_email(email), service)).fetchone()
        if not row:
            return None
        return {"tail": row[0][-4:], "workspace": row[1], "created_at": row[2]}

    def set_groups(self, email: str, groups: list[str]) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "UPDATE users SET groups = ? WHERE email = ?",
                (json.dumps(list(groups)), norm_email(email)))
            self._conn.commit()
            return cur.rowcount > 0

    # ── 소속·개별 허가·허가 요청(docs/access-control) ──────────────────────────
    def set_access(self, email: str, *, affiliation: str | None = None,
                   grants: list[str] | None = None) -> bool:
        """준 칸만 바꾼다. 소속은 관리자만 정한다(호출부가 관리자 확인)."""
        sets, args = [], []
        if affiliation is not None:
            sets.append("affiliation = ?")
            args.append(affiliation.strip()[:40])
        if grants is not None:
            sets.append("grants = ?")
            args.append(json.dumps(sorted(set(grants))))
        if not sets:
            return False
        with self._lock:
            cur = self._conn.execute(f"UPDATE users SET {', '.join(sets)} WHERE email = ?",  # noqa: S608 — 칸 이름은 고정 목록
                                     (*args, norm_email(email)))
            self._conn.commit()
            return cur.rowcount > 0

    def create_request(self, *, email: str, key: str, note: str = "") -> dict:
        """허가 요청. 같은 키로 대기 중인 요청이 있으면 새로 만들지 않고 그걸 돌려준다
        (두 번 누름)."""
        email = norm_email(email)
        with self._lock:
            row = self._conn.execute(
                "SELECT id FROM access_requests WHERE email = ? AND key = ? AND status = 'pending'",
                (email, key)).fetchone()
            if row:
                return {"id": row[0], "status": "pending", "duplicate": True}
            cur = self._conn.execute(
                "INSERT INTO access_requests (email, key, note, created_at) VALUES (?, ?, ?, ?)",
                (email, key, note.strip()[:500], _now()))
            self._conn.commit()
            return {"id": cur.lastrowid, "status": "pending", "duplicate": False}

    def list_requests(self, *, status: str | None = None, email: str | None = None,
                      limit: int = 200) -> list[dict]:
        q = ("SELECT id, email, key, note, status, created_at, decided_at, decided_by "
             "FROM access_requests")
        args: list = []
        conds = []
        if status:
            conds.append("status = ?")
            args.append(status)
        if email:
            conds.append("email = ?")
            args.append(norm_email(email))
        if conds:
            q += " WHERE " + " AND ".join(conds)
        with self._lock:
            cur = self._conn.execute(q + " ORDER BY id DESC LIMIT ?", (*args, limit))
            cols = [c[0] for c in cur.description]
            rows = cur.fetchall()
        return [dict(zip(cols, r, strict=True)) for r in rows]

    def decide_request(self, req_id: int, *, approve: bool, by: str) -> dict | None:
        """승인이면 그 키를 사용자 개별 허가에 더한다. 이미 결정된 요청은 건드리지 않는다(None)."""
        with self._lock:
            row = self._conn.execute(
                "SELECT email, key FROM access_requests WHERE id = ? AND status = 'pending'",
                (req_id,)).fetchone()
            if not row:
                return None
            email, key = row
            self._conn.execute(
                "UPDATE access_requests SET status = ?, decided_at = ?, decided_by = ? "
                "WHERE id = ?",
                ("approved" if approve else "rejected", _now(), norm_email(by), req_id))
            if approve:
                cur = self._conn.execute(
                    "SELECT grants FROM users WHERE email = ?", (email,)).fetchone()
                have = set(json.loads((cur or ["[]"])[0] or "[]"))
                have.add(key)
                self._conn.execute("UPDATE users SET grants = ? WHERE email = ?",
                                   (json.dumps(sorted(have)), email))
            self._conn.commit()
            return {"id": req_id, "email": email, "key": key,
                    "status": "approved" if approve else "rejected"}

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
