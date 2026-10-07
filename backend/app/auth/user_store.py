# 이메일 로컬 계정 원장(SQLite) — SSO 지연 브리지. 계정 행은 SSO 전환 후에도 남는다.
"""Local email-account store.

conv_store 와 같은 패턴(stdlib sqlite3 + threading.Lock). 이메일이 영구 키(subject)다 —
나중에 SSO 가 붙으면 단언의 email 로 이 행을 찾아 연결하고(note_sso_login), 로그인
수단(auth_source)만 갱신한다. 비밀번호는 stdlib scrypt(의존성 無).
"""
import base64
import contextlib
import copy
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import threading
import time
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
        # 연결 하나를 스레드풀이 나눠 쓴다(check_same_thread=False) — 읽기도 잠가야 한다. 권한을
        # 요청마다 계산하면서 get() 이 모든 요청에서 동시에 돌자 'bad parameter or other API
        # misuse'·열 개수 불일치로 500 이 났다(dev 실측). 쓰기 안에서 get() 을 부르므로 재진입 잠금.
        self._lock = threading.RLock()
        # 권한을 요청마다 계산하면서 get() 이 **모든 요청**의 임계경로가 됐다. 연결 하나를 락으로
        # 직렬화하므로 사람이 늘수록 여기서 줄을 선다. 아주 짧은 TTL 로 같은 사람의 연속 조회를
        # 합친다 — 쓰기는 _commit 이 epoch 를 올려 **즉시** 무효화하므로, 관리자가 권한을 바꾸면
        # 그 순간부터 새 값이다(TTL 은 '아무도 안 고쳤을 때'만 의미가 있다). 0 이면 캐시 끔.
        self._row_ttl = float(os.environ.get("USER_ROW_TTL_S", "3") or 0)
        self._row_cache: dict[str, tuple[float, int, dict | None]] = {}
        self._epoch = 0
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
        # 허브에서 끈 앱(게이트웨이 앱 키 JSON 배열) — 본인이 고른다. 도구를 **덜 보게만** 하므로 본인이 바꿔도 되지만
        # 권한(grants)과 섞지 않는다(docs/mcp-app-toggle D-5). 게이트웨이가 개인 MCP 시야에서 숨긴다.
        with contextlib.suppress(sqlite3.OperationalError):
            self._conn.execute("ALTER TABLE users ADD COLUMN hub_muted_apps TEXT NOT NULL DEFAULT '[]'")
        # 업데이트 이력 '본 날짜'(ISO) — 종전엔 브라우저 저장소에만 있어 새 PC·캐시 삭제 뒤 첫 로그인에
        # '마지막으로 보신 뒤' 가 비어 처음 온 사람처럼 다뤄졌다(docs/ui-refresh 단계 4). 앞으로만 간다.
        with contextlib.suppress(sqlite3.OperationalError):
            self._conn.execute("ALTER TABLE users ADD COLUMN changelog_seen TEXT NOT NULL DEFAULT ''")
        # 부서 코드(IdP 의 DeptId) — 표시용 department 와 따로 둔다. 한 칸에 받으면 사람이 적은 부서명이 코드로 덮인다(10차 요청 §7).
        with contextlib.suppress(sqlite3.OperationalError):
            self._conn.execute("ALTER TABLE users ADD COLUMN dept_id TEXT NOT NULL DEFAULT ''")
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
        # 배선 설정의 '확인함' — 포털이 스스로 확인할 수 없는 항목(manual)은 사람이 했다고 표시해야 상자에서
        # 빠진다. 종전엔 영원히 남아 '늘 노란 상자' 가 됐다(docs/ui-refresh 단계 4). 누가·언제를 같이 남긴다.
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS setup_acks ("
            "id TEXT PRIMARY KEY, by TEXT NOT NULL, at INTEGER NOT NULL)"
        )
        self._commit()

    def _commit(self) -> None:
        """쓰기 확정 — 행 캐시도 함께 버린다. 쓰기가 이 함수를 안 거치면 캐시가 낡은 권한을
        들고 있게 되므로, 테스트가 `self._conn.commit()` 직접 호출이 없는지 대조한다."""
        self._conn.commit()
        self._epoch += 1

    # ── 조회 ────────────────────────────────────────────────────────────────
    def get(self, email: str) -> dict | None:
        key = norm_email(email)
        hit = self._row_cache.get(key)
        if hit and hit[1] == self._epoch and (time.monotonic() - hit[0]) < self._row_ttl:
            return copy.deepcopy(hit[2])   # 호출부가 고쳐도 캐시가 오염되지 않게
        with self._lock:
            cur = self._conn.execute("SELECT * FROM users WHERE email = ?", (key,))
            row = cur.fetchone()
            cols = [c[0] for c in cur.description] if row is not None else []
        d: dict | None = None
        if row is not None:
            d = dict(zip(cols, row, strict=True))
            d["groups"] = json.loads(d.get("groups") or "[]")
            d["grants"] = json.loads(d.get("grants") or "[]")
            d["hub_muted_apps"] = json.loads(d.get("hub_muted_apps") or "[]")
        if self._row_ttl > 0:
            self._row_cache[key] = (time.monotonic(), self._epoch, d)
        return copy.deepcopy(d)

    def list_users(self) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT email, name, department, dept_id, affiliation, grants, groups, status, auth_source, "
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
            self._commit()
        return {"email": email, "status": status}

    def approve(self, email: str, *, by: str, groups: list[str] | None = None) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "UPDATE users SET status = 'active', approved_at = ?, approved_by = ?, "
                "groups = COALESCE(?, groups) WHERE email = ? AND status = 'pending'",
                (_now(), norm_email(by), json.dumps(groups) if groups is not None else None,
                 norm_email(email)))
            self._commit()
            return cur.rowcount > 0

    def set_status(self, email: str, status: str) -> bool:
        if status not in ("active", "disabled"):
            raise ValueError("bad status")
        with self._lock:
            cur = self._conn.execute(
                "UPDATE users SET status = ? WHERE email = ?", (status, norm_email(email)))
            self._commit()
            return cur.rowcount > 0

    def set_password(self, email: str, password: str) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "UPDATE users SET pw_hash = ?, failed_count = 0, locked_until = 0 "
                "WHERE email = ?", (hash_password(password), norm_email(email)))
            self._commit()
            return cur.rowcount > 0

    def set_department(self, email: str, department: str) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "UPDATE users SET department = ? WHERE email = ?",
                (department.strip()[:80], norm_email(email)))
            self._commit()
            return cur.rowcount > 0

    def changelog_seen(self, email: str) -> str:
        with self._lock:
            row = self._conn.execute(
                "SELECT changelog_seen FROM users WHERE email = ?", (norm_email(email),)).fetchone()
        return (row[0] or "") if row else ""

    def mark_changelog_seen(self, email: str, date: str) -> bool:
        """본 날짜를 **앞으로만** 옮긴다 — 옛 탭이 늦게 옛 날짜를 적어도 되돌아가지 않는다(ISO 는 문자열 비교로 순서가 맞다)."""
        with self._lock:
            cur = self._conn.execute(
                "UPDATE users SET changelog_seen = ? WHERE email = ? AND changelog_seen < ?",
                (date, norm_email(email), date))
            self._commit()
            return cur.rowcount > 0

    # ── 외부 서비스 연결 토큰(RA PAT 등) ─────────────────────────────────────
    def set_connection(self, *, email: str, service: str, token: str, workspace: str = "") -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO connections (email, service, token, workspace, created_at) "
                "VALUES (?, ?, ?, ?, ?)", (norm_email(email), service, token, workspace, _now()))
            self._commit()

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
            self._commit()
            return cur.rowcount > 0

    def delete_connection(self, *, email: str, service: str) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM connections WHERE email = ? AND service = ?",
                (norm_email(email), service))
            self._commit()
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

    def set_hub_app_muted(self, email: str, app: str, muted: bool) -> list[str] | None:
        """허브에서 앱 **하나**를 끄거나 켠다 — 읽고-고쳐-쓰기를 잠금 안에서 한 번에. 목록을 통째로 받던 때는 두 탭이
        각자 옛 목록을 보내 서로의 선택을 조용히 되돌렸다(검토 2026-09-29). 행이 없으면 None, 있으면 새 목록."""
        key = norm_email(email)
        with self._lock:
            row = self._conn.execute("SELECT hub_muted_apps FROM users WHERE email = ?", (key,)).fetchone()
            if row is None:
                return None
            cur = set(json.loads(row[0] or "[]"))
            if muted:
                cur.add(app)
            else:
                cur.discard(app)
            new = sorted(cur)
            self._conn.execute("UPDATE users SET hub_muted_apps = ? WHERE email = ?", (json.dumps(new), key))
            self._commit()
            return new

    # ── 배선 설정 '확인함' ──────────────────────────────────────────────────
    def setup_acks(self) -> dict[str, dict]:
        with self._lock:
            rows = self._conn.execute("SELECT id, by, at FROM setup_acks").fetchall()
        return {r[0]: {"by": r[1], "at": r[2]} for r in rows}

    def ack_setup(self, rid: str, *, by: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO setup_acks (id, by, at) VALUES (?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET by = excluded.by, at = excluded.at",
                (rid, norm_email(by), int(time.time())),
            )
            self._commit()

    def unack_setup(self, rid: str) -> bool:
        with self._lock:
            cur = self._conn.execute("DELETE FROM setup_acks WHERE id = ?", (rid,))
            self._commit()
        return cur.rowcount > 0

    def set_groups(self, email: str, groups: list[str]) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "UPDATE users SET groups = ? WHERE email = ?",
                (json.dumps(list(groups)), norm_email(email)))
            self._commit()
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
            self._commit()
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
            self._commit()
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
            self._commit()
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
                self._commit()
            raise ValueError("locked" if locked else "bad credentials")
        if u["status"] != "active":
            raise ValueError("not active")
        with self._lock:
            self._conn.execute(
                "UPDATE users SET failed_count = 0, locked_until = 0, last_login_at = ?, "
                "auth_source = 'local' WHERE email = ?", (now, email))
            self._commit()
        return u

    # ── SSO 연동(미래) ──────────────────────────────────────────────────────
    def note_sso_login(self, *, email: str, name: str | None, department: str | None = None,
                       dept_id: str | None = None) -> None:
        """SSO 콜백 훅 — 같은 이메일 행이 있으면 연결(auth_source 갱신), 없으면 원장에
        생성(active — IdP 가 이미 신원을 보증). 계정·비밀번호 해시는 남는다.

        이름은 **비어 있을 때만** 채운다 — 사람이 적은 이름을 보존하고, IdP 가 이름을 안 주는 동안 들어온 사람도 나중에 Claim 이
        오면 스스로 낫는다. 예전엔 새 행에 이메일을 이름으로 박고 UPDATE 는 이름을 안 건드려 영구히 이메일로 굳었다 — 그래서
        이름이 이메일과 같은 행도 빈 것으로 본다(6차 요청 §4-B-3). 읽을 때의 대체는 deps.entitled 가 한다.
        부서는 IdP 값이 있으면 덮는다(사람 입력 표기가 21종으로 갈려 있다), 없으면 그대로 둔다.
        부서 **코드**(dept_id)도 같은 규칙이되 제 칸에만 적는다 — 표시용 부서는 코드로 덮지 않는다(10차 요청 §7).
        ⚠ affiliation·groups·grants·status 는 **절대 안 건드린다** — 권한 입력이다(§4-B-4)."""
        email = norm_email(email)
        name = (name or "").strip()[:80]
        dept = (department or "").strip()[:80] or None
        did = (dept_id or "").strip()[:80] or None
        now = _now()
        with self._lock:
            if self.get(email) is None:
                self._conn.execute(
                    "INSERT INTO users (email, name, groups, status, auth_source, created_at, "
                    "approved_at, approved_by, last_login_at, department, dept_id) "
                    "VALUES (?, ?, '[]', 'active', 'sso', ?, ?, 'sso', ?, ?, ?)",
                    (email, name, now, now, now, dept or "", did or ""))
            else:
                self._conn.execute(
                    "UPDATE users SET auth_source = 'sso', last_login_at = ?, "
                    "name = CASE WHEN ? <> '' AND (TRIM(name) = '' OR lower(TRIM(name)) = lower(email)) "
                    "THEN ? ELSE name END, "
                    "department = COALESCE(?, department), dept_id = COALESCE(?, dept_id) WHERE email = ?",
                    (now, name, name, dept, did, email))
            self._commit()
