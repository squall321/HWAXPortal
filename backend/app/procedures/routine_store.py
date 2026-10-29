# 분석 루틴 저장소 — 절차 저장소(procedures.sqlite)의 연결을 같이 쓰는 새 표 둘(루틴 · 판)(docs/analysis-routines AR-D1)
"""절차와 같은 파일 · 같은 스레드별 연결(WAL)을 쓴다 — 설정 · 서비스 표 · 백업 · 기동 네 곳에 이미 등록된 저장소라 새로 등록할 것이 없다.
규칙도 절차와 같다.

- 판(spec)은 불변이다. 고치면 새 판이 된다.
- **판을 더하는 것은 주인만**이다. 공개(`all`)는 '남도 본다' 이지 '남도 고친다' 가 아니다 — 남의 루틴을 고치고 싶으면 내보내기 · 가져오기로
  자기 것을 만든다(절차 add_version 과 같은 까닭).
- 없는 것과 못 보는 것은 같은 None 이다(라우트가 같은 404 로 낸다) — id 를 넣어 보는 것만으로 남의 루틴이 있는지 알 수 없게.
- 지우지 않고 보관한다(archived) — 실행 원장이 그 판을 가리킨다. 보관한 루틴은 목록에서 빠지고 주인만 읽는다.
"""
import json
import uuid
from datetime import UTC, datetime

_DDL = (
    """CREATE TABLE IF NOT EXISTS routines (
        id TEXT PRIMARY KEY, owner_sub TEXT NOT NULL, title TEXT NOT NULL,
        visibility TEXT NOT NULL DEFAULT 'private', latest_version INTEGER NOT NULL DEFAULT 0,
        archived INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS routine_versions (
        version_id TEXT PRIMARY KEY, routine_id TEXT NOT NULL, version_no INTEGER NOT NULL,
        spec_json TEXT NOT NULL, author_sub TEXT NOT NULL, created_at INTEGER NOT NULL,
        UNIQUE (routine_id, version_no))""",
    "CREATE INDEX IF NOT EXISTS ix_routines_owner ON routines (owner_sub, updated_at DESC)",
)


def _now() -> int:
    return int(datetime.now(tz=UTC).timestamp())


class RoutineStore:
    def __init__(self, base) -> None:
        """base — 열린 ProceduresStore. 연결은 그것의 스레드별 연결을 그대로 쓴다."""
        self._conn = base._conn
        with self._conn() as c:
            for stmt in _DDL:
                c.execute(stmt)

    def create(self, *, owner_sub: str, spec: dict) -> dict:
        rid, vid, now = uuid.uuid4().hex, uuid.uuid4().hex, _now()
        c = self._conn()
        with c:
            c.execute("INSERT INTO routines (id, owner_sub, title, visibility, latest_version, created_at, updated_at)"
                      " VALUES (?,?,?,?,1,?,?)",
                      (rid, owner_sub, spec["title"], spec.get("visibility") or "private", now, now))
            c.execute("INSERT INTO routine_versions (version_id, routine_id, version_no, spec_json, author_sub, created_at)"
                      " VALUES (?,?,1,?,?,?)", (vid, rid, json.dumps(spec, ensure_ascii=False), owner_sub, now))
        return {"id": rid, "version_id": vid, "version_no": 1}

    def add_version(self, *, routine_id: str, author_sub: str, spec: dict) -> dict:
        """주인만 — 없거나 남의 것이면 KeyError. 제목 · 공개 범위는 새 판의 값을 따른다."""
        c = self._conn()
        with c:
            row = c.execute("SELECT latest_version FROM routines WHERE id=? AND owner_sub=?",
                            (routine_id, author_sub)).fetchone()
            if row is None:
                raise KeyError(routine_id)
            no, vid, now = int(row["latest_version"]) + 1, uuid.uuid4().hex, _now()
            c.execute("INSERT INTO routine_versions (version_id, routine_id, version_no, spec_json, author_sub, created_at)"
                      " VALUES (?,?,?,?,?,?)", (vid, routine_id, no, json.dumps(spec, ensure_ascii=False), author_sub, now))
            c.execute("UPDATE routines SET latest_version=?, title=?, visibility=?, archived=0, updated_at=? WHERE id=?",
                      (no, spec["title"], spec.get("visibility") or "private", now, routine_id))
        return {"id": routine_id, "version_id": vid, "version_no": no}

    def archive(self, *, routine_id: str, owner_sub: str) -> bool:
        c = self._conn()
        with c:
            cur = c.execute("UPDATE routines SET archived=1, updated_at=? WHERE id=? AND owner_sub=?",
                            (_now(), routine_id, owner_sub))
        return cur.rowcount == 1

    def _visible(self, routine_id: str, sub: str) -> dict | None:
        row = self._conn().execute(
            "SELECT * FROM routines WHERE id=? AND (owner_sub=? OR (visibility='all' AND archived=0))",
            (routine_id, sub)).fetchone()
        return dict(row) if row else None

    def readable(self, *, sub: str, routine_id: str, version_no: int | None = None) -> dict | None:
        """그 사람이 볼 수 있는 루틴과 판 하나(기본 최신). 못 보면 None."""
        r = self._visible(routine_id, sub)
        if r is None:
            return None
        row = self._conn().execute(
            "SELECT * FROM routine_versions WHERE routine_id=? AND version_no=?",
            (routine_id, version_no or r["latest_version"])).fetchone()
        if row is None:
            return None
        v = dict(row)
        v["spec"] = json.loads(v.pop("spec_json"))
        return {"routine": r, "version": v}

    def versions(self, *, sub: str, routine_id: str) -> list[dict] | None:
        if self._visible(routine_id, sub) is None:
            return None
        rows = self._conn().execute(
            "SELECT version_id, version_no, author_sub, created_at FROM routine_versions WHERE routine_id=?"
            " ORDER BY version_no DESC", (routine_id,)).fetchall()
        return [dict(r) for r in rows]

    def list(self, *, sub: str, q: str = "", limit: int = 200) -> list[dict]:
        """내 것 + 공개된 것(보관 제외), 최근 고친 것 먼저. 판의 단계 수 · 단계 백엔드를 곁들인다(고르는 화면 · routine_list)."""
        rows = self._conn().execute(
            "SELECT r.*, v.spec_json FROM routines r JOIN routine_versions v"
            " ON v.routine_id=r.id AND v.version_no=r.latest_version"
            " WHERE r.archived=0 AND (r.owner_sub=? OR r.visibility='all')"
            " ORDER BY r.updated_at DESC LIMIT ?", (sub, limit)).fetchall()
        out = []
        ql = q.strip().lower()
        for row in rows:
            d = dict(row)
            spec = json.loads(d.pop("spec_json"))
            if ql and ql not in d["title"].lower() and ql not in (spec.get("purpose") or "").lower():
                continue
            d["steps"] = [{"id": s["id"], "title": s["title"], "kind": s.get("kind") or "platform",
                           "backends": s.get("backends") or []} for s in spec.get("steps") or []]
            d["vars"] = [{"key": v["key"], "label": v["label"]} for v in spec.get("vars") or []]
            d["mine"] = d["owner_sub"] == sub
            out.append(d)
        return out
