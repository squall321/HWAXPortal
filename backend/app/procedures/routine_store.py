# 분석 루틴 저장소 — 절차 저장소(procedures.sqlite)의 연결을 같이 쓰는 새 표 둘(루틴 · 판)(docs/analysis-routines AR-D1)
"""절차와 같은 파일 · 같은 스레드별 연결(WAL)을 쓴다 — 설정 · 서비스 표 · 백업 · 기동 네 곳에 이미 등록된 저장소라 새로 등록할 것이 없다.
규칙도 절차와 같다.

- 판(spec)은 불변이다. 고치면 새 판이 된다.
- **판을 더하는 것은 주인만**이다. 공개(`all`)는 '남도 본다' 이지 '남도 고친다' 가 아니다 — 남의 루틴을 고치고 싶으면 내보내기 · 가져오기로
  자기 것을 만든다(절차 add_version 과 같은 까닭).
- 없는 것과 못 보는 것은 같은 None 이다(라우트가 같은 404 로 낸다) — id 를 넣어 보는 것만으로 남의 루틴이 있는지 알 수 없게.
- 지우지 않고 보관한다(archived) — 실행 원장이 그 판을 가리킨다. 보관한 루틴은 목록에서 빠지고 주인만 읽는다.

실행 원장(R2) — 실행 · 단계 · 호출 표 셋. 호출 결과는 gzip 으로 두고(2MB 넘으면 앞부분 · 표시), 덧붙이기만 한다. 실행은 주인만 본다 — 결과에
그 사람 시야의 데이터가 담긴다(절차 실행과 같은 까닭). 단계 상태 · 호출 수는 여기서 세고, 판정(울타리 · 예산 · 상태 고치기)은 라우트가 한다.
다만 호출 한 줄의 '세기와 넣기' 는 한 쓰기 트랜잭션(BEGIN IMMEDIATE)이라 예산 · 상태도 그 안에서 다시 본다(R3 — 동시 호출이 예산을 넘기거나
call_id 가 겹치지 않게).
"""
import gzip
import hashlib
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
    """CREATE TABLE IF NOT EXISTS routine_runs (
        id TEXT PRIMARY KEY, owner_sub TEXT NOT NULL, routine_id TEXT NOT NULL, version_id TEXT NOT NULL,
        version_no INTEGER NOT NULL, title TEXT NOT NULL, inputs_json TEXT NOT NULL, plan_json TEXT NOT NULL,
        executor TEXT NOT NULL, conversation_id TEXT, state TEXT NOT NULL, reason TEXT,
        calls INTEGER NOT NULL DEFAULT 0, started_at INTEGER NOT NULL, deadline INTEGER NOT NULL, ended_at INTEGER,
        report_md TEXT, ra_report_id TEXT, ra_error TEXT, report_json TEXT, note TEXT)""",
    """CREATE TABLE IF NOT EXISTS routine_stages (
        run_id TEXT NOT NULL, step_id TEXT NOT NULL, ix INTEGER NOT NULL, state TEXT NOT NULL,
        calls INTEGER NOT NULL DEFAULT 0, reason TEXT, envelope_json TEXT, flags_json TEXT,
        started_at INTEGER, ended_at INTEGER, PRIMARY KEY (run_id, step_id))""",
    """CREATE TABLE IF NOT EXISTS routine_calls (
        run_id TEXT NOT NULL, call_id TEXT NOT NULL, step_id TEXT NOT NULL, n INTEGER NOT NULL,
        backend TEXT NOT NULL, tool TEXT NOT NULL, args_json TEXT NOT NULL, args_sha256 TEXT NOT NULL,
        ok INTEGER NOT NULL, ms INTEGER, result_gz BLOB, result_chars INTEGER NOT NULL DEFAULT 0,
        result_sha256 TEXT, truncated INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL,
        PRIMARY KEY (run_id, call_id))""",
    "CREATE INDEX IF NOT EXISTS ix_routine_runs_owner ON routine_runs (owner_sub, started_at DESC)",
)
# ⚠ `CREATE TABLE IF NOT EXISTS` 는 이미 있는 표를 고치지 않는다 — 더하는 칼럼은 DDL 과 여기 둘 다에 적는다(멱등, 절차 저장소 _ADD_COLUMNS 와 같은 꼴).
_ADD_COLUMNS = (("routine_runs", "report_json", "TEXT"),      # R3 — 렌더한 RA 블록 · 커버리지 · 경고(끝난 실행의 보고서 다시 내기)
                ("routine_runs", "note", "TEXT"))             # 사용자가 덧붙인 말(시작 때 한 번) — 이어서 · 고른 뒤 잇기에도 같은 말(C-12)
RESULT_MAX = 2_000_000        # 원장에 두는 결과 글자 상한(게이트웨이 ROUTINE_LEDGER_CHARS 와 같다) — 넘으면 앞부분과 truncated


def _now() -> int:
    return int(datetime.now(tz=UTC).timestamp())


class CallRefused(Exception):
    """호출 한 줄을 넣는 트랜잭션 안에서 다시 본 거절(상태 · 예산 · 호출 상한) — 라우트가 409 와 이 글로 낸다."""


class RoutineStore:
    def __init__(self, base) -> None:
        """base — 열린 ProceduresStore. 연결은 그것의 스레드별 연결을 그대로 쓴다."""
        self._conn = base._conn
        with self._conn() as c:
            for stmt in _DDL:
                c.execute(stmt)
            for table, col, decl in _ADD_COLUMNS:
                have = {r["name"] for r in c.execute(f"PRAGMA table_info({table})")}
                if col not in have:
                    c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")

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

    def version_spec(self, version_id: str) -> dict | None:
        """판 하나의 스펙(판 id 로) — 공개 범위 · 보관을 다시 보지 않는다. 실행이 묶인 판을 읽는 자리(보고서 렌더)만 쓴다 — 실행은 시작할 때 이미
        그 판을 읽을 수 있었고, 주인이 도중에 보관 · 비공개로 바꿔도 그 실행의 보고서는 나야 한다."""
        row = self._conn().execute("SELECT spec_json FROM routine_versions WHERE version_id=?", (version_id,)).fetchone()
        return json.loads(row["spec_json"]) if row else None

    def versions(self, *, sub: str, routine_id: str) -> list[dict] | None:
        if self._visible(routine_id, sub) is None:
            return None
        rows = self._conn().execute(
            "SELECT version_id, version_no, author_sub, created_at FROM routine_versions WHERE routine_id=?"
            " ORDER BY version_no DESC", (routine_id,)).fetchall()
        return [dict(r) for r in rows]

    def list_routines(self, *, sub: str, q: str = "", limit: int = 200) -> list[dict]:
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
            # 필수 표시 — 게이트웨이 prompts/list 가 루틴 변수를 인자로 싣고 required 를 단다(R3-design 3.4 ⑥ — 루틴마다 계획을 다시 읽지 않게).
            # 저장한 스펙에는 늘 있다(Var 기본 True)
            d["vars"] = [{"key": v["key"], "label": v["label"], "required": bool(v.get("required", True))}
                         for v in spec.get("vars") or []]
            d["mine"] = d["owner_sub"] == sub
            out.append(d)
        return out

    # ── 실행 원장(R2) ──────────────────────────────────────────────────────────────────────────────────────────
    def create_run(self, *, owner_sub: str, routine: dict, version: dict, inputs: dict, plan: dict, executor: str,
                   conversation_id: str | None, deadline: int, state: str, reason: str | None,
                   stages: list[tuple[str, str, str | None]], note: str = "") -> str:
        """stages — 계획 차례대로 (단계 id, 첫 상태, 까닭). note — 사용자가 덧붙인 말(실행기가 단계 · 인사이트 프롬프트에 싣는다)."""
        run_id, now = uuid.uuid4().hex, _now()
        c = self._conn()
        with c:
            c.execute("INSERT INTO routine_runs (id, owner_sub, routine_id, version_id, version_no, title, inputs_json, plan_json,"
                      " executor, conversation_id, state, reason, started_at, deadline, ended_at, note)"
                      " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (run_id, owner_sub, routine["id"], version["version_id"], version["version_no"], routine["title"],
                       json.dumps(inputs, ensure_ascii=False), json.dumps(plan, ensure_ascii=False), executor, conversation_id,
                       state, reason, now, deadline, now if state not in ("queued", "running", "waiting") else None, note))
            for ix, (step_id, st, why) in enumerate(stages):
                c.execute("INSERT INTO routine_stages (run_id, step_id, ix, state, reason, ended_at) VALUES (?,?,?,?,?,?)",
                          (run_id, step_id, ix, st, why, now if st not in ("pending", "running") else None))
        return run_id

    def get_run(self, *, run_id: str, owner_sub: str) -> dict | None:
        row = self._conn().execute("SELECT * FROM routine_runs WHERE id=? AND owner_sub=?", (run_id, owner_sub)).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["inputs"] = json.loads(d.pop("inputs_json"))
        d["plan"] = json.loads(d.pop("plan_json"))
        d["report"] = json.loads(d.pop("report_json") or "null")     # 렌더 저장본(R3) — 없으면 None(R3 전에 낸 보고서 · 아직 안 낸 실행)
        return d

    def list_runs(self, *, owner_sub: str, routine_id: str | None = None, limit: int = 50) -> list[dict]:
        # conversation_id — 챗에서 ■ 로 끊긴 루틴 턴을 다시 보낼 때 화면이 이 대화의 실행을 찾아 이어서로 바꾼다(두 번째 실행을 세우지 않게).
        q, args = ("SELECT id, routine_id, version_no, title, executor, state, reason, calls, started_at, ended_at, ra_report_id,"
                   " conversation_id FROM routine_runs WHERE owner_sub=?"), [owner_sub]
        if routine_id:
            q += " AND routine_id=?"
            args.append(routine_id)
        rows = self._conn().execute(q + " ORDER BY started_at DESC LIMIT ?", (*args, limit)).fetchall()
        return [dict(r) for r in rows]

    def stages(self, run_id: str) -> list[dict]:
        out = []
        for r in self._conn().execute("SELECT * FROM routine_stages WHERE run_id=? ORDER BY ix", (run_id,)).fetchall():
            d = dict(r)
            d["envelope"] = json.loads(d.pop("envelope_json") or "null")
            d["flags"] = json.loads(d.pop("flags_json") or "[]")
            out.append(d)
        return out

    def set_run(self, run_id: str, **fields) -> None:
        if not fields:
            return
        if fields.get("state") in ("done", "failed", "cancelled", "interrupted"):
            fields.setdefault("ended_at", _now())
        cols = ", ".join(f"{k}=?" for k in fields)
        c = self._conn()
        with c:
            c.execute(f"UPDATE routine_runs SET {cols} WHERE id=?", (*fields.values(), run_id))

    def set_stage(self, run_id: str, step_id: str, *, state: str, reason: str | None = None, envelope: dict | None = None,
                  flags: list | None = None) -> None:
        closed = state not in ("pending", "running", "ambiguous")
        c = self._conn()
        with c:
            c.execute("UPDATE routine_stages SET state=?, reason=?, envelope_json=COALESCE(?, envelope_json),"
                      " flags_json=COALESCE(?, flags_json), started_at=COALESCE(started_at, ?), ended_at=? WHERE run_id=? AND step_id=?",
                      (state, reason, json.dumps(envelope, ensure_ascii=False) if envelope is not None else None,
                       json.dumps(flags, ensure_ascii=False) if flags is not None else None, _now(),
                       _now() if closed else None, run_id, step_id))

    def add_call(self, *, run_id: str, step_id: str, backend: str, tool: str, args: dict, ok: bool, ms: int | None,
                 result: str, truncated: bool, step_budget: int | None = None, run_budget: int | None = None) -> str:
        """호출 한 줄 — 단계 · 실행 호출 수를 함께 올리고 call_id(<단계>.c<n>)를 낸다. 단계는 running 이 된다.

        세기와 넣기는 한 쓰기 트랜잭션이다(BEGIN IMMEDIATE — 쓰기 잠금을 읽기 전에 잡는다). 암묵 BEGIN 은 첫 INSERT 앞에서야 열려, 두 스레드가
        같은 calls 를 읽고 같은 call_id 로 부딪치거나(기본키 → 500) 예산을 넘겼다. 그래서 실행 · 단계 상태와 예산(step_budget · run_budget —
        None 이면 안 본다)을 잠금 안에서 다시 보고, 어긋나면 CallRefused. 연결은 스레드별이라(절차 저장소) 트랜잭션이 스레드 사이에서 섞이지 않고,
        다른 스레드는 busy_timeout 만큼 잠금을 기다린다."""
        text = result[:RESULT_MAX]
        cut = truncated or len(result) > RESULT_MAX
        args_json = json.dumps(args, ensure_ascii=False, sort_keys=True)
        raw = text.encode("utf-8")
        gz, sha = gzip.compress(raw), hashlib.sha256(raw).hexdigest()      # 큰 결과(2MB)의 압축은 잠금 밖에서 — 잠금은 짧게 쥔다
        c = self._conn()
        with c:
            c.execute("BEGIN IMMEDIATE")
            run = c.execute("SELECT state, calls FROM routine_runs WHERE id=?", (run_id,)).fetchone()
            row = c.execute("SELECT state, calls FROM routine_stages WHERE run_id=? AND step_id=?", (run_id, step_id)).fetchone()
            if run is None or row is None:
                raise CallRefused(f"이 실행에 단계 {step_id!r} 가 없다")
            if run["state"] != "running":
                raise CallRefused(f"실행이 {run['state']} 상태다")
            if row["state"] not in ("pending", "running"):
                raise CallRefused(f"단계 {step_id} 는 이미 닫혔다({row['state']})")
            if step_budget is not None and int(row["calls"]) >= step_budget:
                raise CallRefused(f"단계 {step_id} 의 호출 예산({step_budget}번)을 다 썼다")
            if run_budget is not None and int(run["calls"]) >= run_budget:
                raise CallRefused(f"실행 상한에 닿았다(호출 {run_budget}번)")
            n = int(row["calls"]) + 1
            call_id = f"{step_id}.c{n}"
            c.execute("INSERT INTO routine_calls (run_id, call_id, step_id, n, backend, tool, args_json, args_sha256, ok, ms,"
                      " result_gz, result_chars, result_sha256, truncated, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (run_id, call_id, step_id, n, backend, tool, args_json, hashlib.sha256(args_json.encode()).hexdigest(),
                       1 if ok else 0, ms, gz, len(text), sha, 1 if cut else 0, _now()))
            c.execute("UPDATE routine_stages SET calls=calls+1, state='running', started_at=COALESCE(started_at, ?)"
                      " WHERE run_id=? AND step_id=?", (_now(), run_id, step_id))
            c.execute("UPDATE routine_runs SET calls=calls+1 WHERE id=?", (run_id,))
        return call_id

    def calls(self, run_id: str, step_ids: list[str] | None = None, *, with_result: bool = False) -> list[dict]:
        q, args = "SELECT * FROM routine_calls WHERE run_id=?", [run_id]
        if step_ids is not None:
            if not step_ids:
                return []
            q += f" AND step_id IN ({','.join('?' * len(step_ids))})"
            args += step_ids
        out = []
        for r in self._conn().execute(q + " ORDER BY created_at, n", args).fetchall():
            d = dict(r)
            gz = d.pop("result_gz")
            d["args"] = json.loads(d.pop("args_json"))
            d["ok"] = bool(d["ok"])
            d["truncated"] = bool(d["truncated"])
            if with_result:
                d["result"] = gzip.decompress(gz).decode("utf-8") if gz else ""
            out.append(d)
        return out

    def get_call(self, run_id: str, call_id: str) -> dict | None:
        rows = [c for c in self.calls(run_id, with_result=True) if c["call_id"] == call_id]
        return rows[0] if rows else None
