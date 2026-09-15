"""절차 저장소(SQLite) — 절차·판본·실행·단계·게이트 승인. **실행 기록이 감사 정본이다.**

챗의 `conv_store` 와 **연결을 공유하지 않는다**(PLAN §3 격리표). 다른 점 셋이 의도다.

1. **스레드별 연결** — 포털 4곳은 연결 1개 + Lock 이라 `to_thread` 로 감싸면 트랜잭션 경계가
   스레드 사이에서 섞인다. S5 일괄 재생(실행 N개 동시)에서 바로 난다.
2. **WAL + busy_timeout=5000** — `backup-local.sh`·이관기가 `mode=ro` 로 동시에 여는 순간을
   견딘다. 포털 sqlite 4곳은 디스크 실측이 전부 `journal_mode=delete` 다.
3. **append-only** — 단계 기록에 수정·삭제 API 가 없다. 게이트웨이 원장은 MCP 경로에서
   호출자를 안 적으므로(context-notes W-17) 이 표가 유일한 사람 단위 흔적이다.
"""

import gzip
import hashlib
import json
import sqlite3
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.config import Settings

# 결과 본문 상한. 넘으면 해시·크기·앞 4KB 프리뷰만 남긴다(PLAN §2 실행).
RESULT_MAX = 2 * 1024 * 1024
PREVIEW = 4096

RUN_STATES = ("queued", "running", "gated", "done", "failed", "cancelled", "unknown")
STEP_STATES = ("pending", "running", "done", "failed", "unknown", "skipped")

_DDL = (
    """CREATE TABLE IF NOT EXISTS procedures (
        id TEXT PRIMARY KEY, owner_sub TEXT NOT NULL, created_by TEXT NOT NULL,
        title TEXT NOT NULL, visibility TEXT NOT NULL DEFAULT 'all',
        latest_version INTEGER NOT NULL DEFAULT 0,
        created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL,
        from_seed TEXT)""",
    """CREATE TABLE IF NOT EXISTS procedure_versions (
        version_id TEXT PRIMARY KEY, procedure_id TEXT NOT NULL, version_no INTEGER NOT NULL,
        spec_json TEXT NOT NULL, author_sub TEXT NOT NULL, created_at INTEGER NOT NULL,
        derived_from_run TEXT,
        UNIQUE (procedure_id, version_no))""",
    """CREATE TABLE IF NOT EXISTS runs (
        id TEXT PRIMARY KEY, owner_sub TEXT NOT NULL, run_by TEXT NOT NULL,
        procedure_version_id TEXT, title TEXT,
        inputs_json TEXT NOT NULL DEFAULT '{}',
        origin TEXT NOT NULL DEFAULT 'manual',
        mode TEXT NOT NULL DEFAULT 'plan',
        state TEXT NOT NULL DEFAULT 'queued', stage TEXT,
        started_at INTEGER NOT NULL, ended_at INTEGER,
        cancelled_by TEXT, cancelled_at INTEGER,
        trigger_kind TEXT, trigger_ref TEXT, batch_id TEXT)""",
    """CREATE TABLE IF NOT EXISTS run_steps (
        run_id TEXT NOT NULL, ix INTEGER NOT NULL,
        backend TEXT NOT NULL, tool TEXT NOT NULL, schema_fp TEXT, expect TEXT,
        args_json TEXT NOT NULL, args_sha256 TEXT NOT NULL,
        result_gz BLOB, result_bytes INTEGER, result_sha256 TEXT,
        truncated INTEGER NOT NULL DEFAULT 0, preview TEXT, notes TEXT,
        state TEXT NOT NULL DEFAULT 'pending', ok INTEGER, error TEXT, stage TEXT,
        started_at INTEGER, duration_ms INTEGER, mode TEXT,
        identity_note TEXT, reused_from_run_id TEXT,
        PRIMARY KEY (run_id, ix))""",
    """CREATE TABLE IF NOT EXISTS run_gate_acks (
        run_id TEXT NOT NULL, step_ix INTEGER NOT NULL,
        ack_by TEXT NOT NULL, ack_at INTEGER NOT NULL,
        args_sha256 TEXT NOT NULL, args_override_json TEXT,
        PRIMARY KEY (run_id, step_ix))""",
    "CREATE INDEX IF NOT EXISTS ix_runs_owner ON runs (owner_sub, started_at DESC)",
    "CREATE INDEX IF NOT EXISTS ix_runs_state ON runs (state)",
    "CREATE INDEX IF NOT EXISTS ix_ver_procedure ON procedure_versions (procedure_id, version_no)",
)


def _now() -> int:
    return int(datetime.now(tz=UTC).timestamp())


def _uid() -> str:
    return uuid.uuid4().hex


class ProceduresStore:
    def __init__(self, settings: Settings) -> None:
        raw = getattr(settings, "procedures_store_path", None) or "data/procedures.sqlite"
        self._path = Path(settings.resolve(raw))
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        with self._conn() as c:  # 스키마는 한 번만
            for stmt in _DDL:
                c.execute(stmt)
            self._migrate(c)

    # ⚠ `CREATE TABLE IF NOT EXISTS` 는 **이미 있는 표를 고치지 않는다.** 칼럼을 DDL 에만
    #    더하면 새 DB 에서는 되고 돌고 있는 DB 에서는 조용히 없다 — 그러면 그 칼럼을 읽는
    #    코드가 운영에서만 터진다. 더하는 칼럼은 여기 한 줄씩 적는다(멱등).
    _ADD_COLUMNS = (("procedures", "from_seed", "TEXT"),
                    ("runs", "batch_id", "TEXT"))

    @classmethod
    def _migrate(cls, c: sqlite3.Connection) -> None:
        for table, col, decl in cls._ADD_COLUMNS:
            have = {r["name"] for r in c.execute(f"PRAGMA table_info({table})")}
            if col not in have:
                c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")

    # ── 연결 ──────────────────────────────────────────────────────────────
    def _conn(self) -> sqlite3.Connection:
        """스레드별 연결. 단일 연결을 스레드풀이 나눠 쓰면 트랜잭션 경계가 섞인다."""
        c = getattr(self._local, "conn", None)
        if c is None:
            c = sqlite3.connect(str(self._path), check_same_thread=False)
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA synchronous=NORMAL")
            c.execute("PRAGMA busy_timeout=5000")
            self._local.conn = c
        return c

    def close(self) -> None:
        c = getattr(self._local, "conn", None)
        if c is not None:
            c.close()
            self._local.conn = None

    def health(self) -> dict:
        c = self._conn()
        mode = c.execute("PRAGMA journal_mode").fetchone()[0]
        return {"journal_mode": mode, "path": str(self._path)}

    # ── 절차 · 판본 ─────────────────────────────────────────────────────
    def find_by_seed(self, *, owner_sub: str, seed: str) -> str | None:
        """이 사람이 이미 이 씨앗을 들여놨나 — 다시 가져오기를 **사본이 아니라 판본**으로."""
        r = self._conn().execute(
            "SELECT id FROM procedures WHERE owner_sub=? AND from_seed=?"
            " ORDER BY created_at LIMIT 1", (owner_sub, seed)).fetchone()
        return r["id"] if r else None

    def create_procedure(self, *, owner_sub: str, spec: dict, title: str,
                      visibility: str = "all", derived_from_run: str | None = None,
                      from_seed: str | None = None) -> dict:
        rid, vid, now = _uid(), _uid(), _now()
        c = self._conn()
        with c:
            c.execute(
                "INSERT INTO procedures (id, owner_sub, created_by, title, visibility,"
                " latest_version, created_at, updated_at, from_seed)"
                " VALUES (?,?,?,?,?,1,?,?,?)",
                (rid, owner_sub, owner_sub, title, visibility, now, now, from_seed),
            )
            c.execute(
                "INSERT INTO procedure_versions (version_id, procedure_id, version_no, spec_json,"
                " author_sub, created_at, derived_from_run) VALUES (?,?,1,?,?,?,?)",
                (vid, rid, json.dumps(spec, ensure_ascii=False), owner_sub, now,
                 derived_from_run),
            )
        return {"id": rid, "version_id": vid, "version_no": 1}

    def add_version(self, *, procedure_id: str, author_sub: str, spec: dict,
                    derived_from_run: str | None = None) -> dict:
        """판본을 덧붙인다 — **주인만**. 없거나 남의 것이면 `KeyError`(라우트가 404 로 낸다).

        ⚠ **공유는 읽기까지다.** `visibility='all'` 은 "남도 본다" 이지 "남도 고친다" 가
        아니다. 게이트가 없던 동안, 아무나 남의 절차에 판본을 얹으면 그것이 최신이 되고
        주인이 그것을 **자기 명의로** 돌렸다(실행 PAT 는 부르는 사람에게서 나온다).
        제목은 그대로라 목록에서는 아무 일도 없어 보인다 — 이 리포가 쫓는 바로 그 모양이다.
        남의 절차를 고치고 싶으면 **내보내기·들여오기로 자기 것을 만든다.**
        """
        c = self._conn()
        with c:
            row = c.execute("SELECT latest_version FROM procedures"
                            " WHERE id=? AND owner_sub=?",
                            (procedure_id, author_sub)).fetchone()
            if row is None:
                raise KeyError(procedure_id)
            no = int(row["latest_version"]) + 1
            vid, now = _uid(), _now()
            c.execute(
                "INSERT INTO procedure_versions (version_id, procedure_id, version_no, spec_json,"
                " author_sub, created_at, derived_from_run) VALUES (?,?,?,?,?,?,?)",
                (vid, procedure_id, no, json.dumps(spec, ensure_ascii=False), author_sub, now,
                 derived_from_run),
            )
            c.execute("UPDATE procedures SET latest_version=?, updated_at=? WHERE id=?",
                      (no, now, procedure_id))
        return {"id": procedure_id, "version_id": vid, "version_no": no}

    def get_version(self, version_id: str) -> dict | None:
        """⚠ **게이트가 없다.** 이미 소유를 확인한 실행에서 그 실행이 돌린 판본을 꺼낼
        때만 쓴다. 사람이 판본·절차 id 를 들고 들어오는 길에서는 `readable_version` 이다.
        """
        row = self._conn().execute(
            "SELECT * FROM procedure_versions WHERE version_id=?", (version_id,)).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["spec"] = json.loads(d.pop("spec_json"))
        return d

    def latest_version_of(self, procedure_id: str) -> dict | None:
        """⚠ `get_version` 과 같이 **게이트가 없다**."""
        row = self._conn().execute(
            "SELECT version_id FROM procedure_versions WHERE procedure_id=?"
            " ORDER BY version_no DESC LIMIT 1", (procedure_id,)).fetchone()
        return self.get_version(row["version_id"]) if row else None

    def readable_version(self, *, sub: str, procedure_id: str | None = None,
                         version_id: str | None = None) -> dict | None:
        """그 사람이 **볼 수 있는** 판본. 못 보면 None — 라우트가 404 로 낸다.

        `visibility='all'` 이면 남의 것도 보인다(PLAN §1 — 절차는 공유 자산이다).
        `private` 는 주인만이다. **없는 것과 못 보는 것을 같은 404 로 낸다** — 구분해
        주면 id 를 넣어 보는 것만으로 남의 절차가 있는지 알 수 있다.

        ⚠ 게이트는 `procedures` 행에 있는데 `version_id` 는 판본 표의 열쇠라, 판본에서
        절차로 **거슬러 올라가 확인한다**. 판본만 보고 내주면 private 이 새어 나간다.
        """
        v = (self.get_version(version_id) if version_id
             else self.latest_version_of(procedure_id or ""))
        if v is None:
            return None
        row = self._conn().execute(
            "SELECT 1 FROM procedures WHERE id=? AND (visibility='all' OR owner_sub=?)",
            (v["procedure_id"], sub)).fetchone()
        return v if row else None

    def list_procedures(self, *, owner_sub: str, limit: int = 100) -> list[dict]:
        """`visibility='all'` 이면 남의 것도 보인다 — 절차는 공유 자산이다(PLAN §1).

        실행은 따라가지 않는다. 실행 결과에는 그 사람 시야의 데이터가 담긴다.
        """
        rows = self._conn().execute(
            "SELECT * FROM procedures WHERE visibility='all' OR owner_sub=?"
            " ORDER BY updated_at DESC LIMIT ?", (owner_sub, limit)).fetchall()
        return [dict(r) for r in rows]

    # ── 실행 ────────────────────────────────────────────────────────────────
    def create_run(self, *, owner_sub: str, run_by: str | None = None,
                   procedure_version_id: str | None = None, inputs: dict | None = None,
                   origin: str = "manual", mode: str = "plan", title: str | None = None,
                   trigger_kind: str | None = None, trigger_ref: str | None = None,
                   batch_id: str | None = None) -> str:
        """`procedure_version_id` 가 없으면 **빈 실행** — 도구를 한 단계씩 돌리는 절차다."""
        run_id, now = _uid(), _now()
        with self._conn() as c:
            c.execute(
                "INSERT INTO runs (id, owner_sub, run_by, procedure_version_id, title,"
                " inputs_json, origin, mode, state, started_at, trigger_kind, trigger_ref,"
                " batch_id) VALUES (?,?,?,?,?,?,?,?,'queued',?,?,?,?)",
                (run_id, owner_sub, run_by or owner_sub, procedure_version_id, title,
                 json.dumps(inputs or {}, ensure_ascii=False), origin, mode, now,
                 trigger_kind, trigger_ref, batch_id),
            )
        return run_id

    def merge_inputs(self, run_id: str, extra: dict) -> None:
        """빈 실행에서 한 단계씩 돌 때, 뽑은 값을 다음 단계가 쓸 수 있게 합친다."""
        c = self._conn()
        with c:
            row = c.execute("SELECT inputs_json FROM runs WHERE id=?", (run_id,)).fetchone()
            if row is None:
                raise KeyError(run_id)
            cur = json.loads(row["inputs_json"] or "{}")
            cur.update(extra)
            c.execute("UPDATE runs SET inputs_json=? WHERE id=?",
                      (json.dumps(cur, ensure_ascii=False), run_id))

    def set_run_state(self, run_id: str, state: str, *, stage: str | None = None,
                      ended: bool = False) -> None:
        if state not in RUN_STATES:
            raise ValueError(f"모르는 실행 상태: {state}")
        with self._conn() as c:
            c.execute("UPDATE runs SET state=?, stage=?, ended_at=? WHERE id=?",
                      (state, stage, _now() if ended else None, run_id))

    def cancel_run(self, run_id: str, by: str) -> None:
        """다음 단계 경계에서 반영된다. 진행 중 호출은 끝까지 간다."""
        with self._conn() as c:
            c.execute("UPDATE runs SET state='cancelled', cancelled_by=?, cancelled_at=?,"
                      " ended_at=? WHERE id=?", (by, _now(), _now(), run_id))

    def get_run(self, run_id: str, *, owner_sub: str | None = None) -> dict | None:
        row = self._conn().execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if row is None:
            return None
        if owner_sub is not None and row["owner_sub"] != owner_sub:
            return None  # 실행은 공유하지 않는다
        d = dict(row)
        d["inputs"] = json.loads(d.pop("inputs_json") or "{}")
        d["steps"] = self.list_steps(run_id)
        # 어느 절차에서 나왔나 — 화면이 절차로 되짚고 "이 값으로 다시" 를 걸 수 있게 한다
        d["procedure_id"] = d["version_no"] = None
        if d.get("procedure_version_id"):
            v = self._conn().execute(
                "SELECT procedure_id, version_no FROM procedure_versions WHERE version_id=?",
                (d["procedure_version_id"],)).fetchone()
            if v is not None:
                d["procedure_id"], d["version_no"] = v["procedure_id"], v["version_no"]
        return d

    def list_runs(self, *, owner_sub: str, limit: int = 50,
                  procedure_id: str | None = None, batch_id: str | None = None) -> list[dict]:
        """확인 대기(`gated`)를 맨 위에 — 게이트에서 멈춘 실행의 표면이 이 목록이다.

        **어느 절차의 몇 판본에서 나왔는지**를 함께 낸다. 실행이 `procedure_version_id`
        하나만 들고 있으면 화면에서 절차로 되짚을 수가 없어서, 한 절차의 이력을 모아
        보는 것 자체가 불가능했다. `procedure_id` 를 주면 그 절차의 이력만 낸다.
        """
        sql = ("SELECT r.id, r.title, r.state, r.stage, r.mode, r.origin,"
               " r.procedure_version_id, r.started_at, r.ended_at, r.batch_id,"
               " r.inputs_json, v.procedure_id, v.version_no"
               " FROM runs r LEFT JOIN procedure_versions v"
               "   ON v.version_id = r.procedure_version_id"
               " WHERE r.owner_sub=?")
        args: list = [owner_sub]
        if procedure_id:
            sql += " AND v.procedure_id=?"
            args.append(procedure_id)
        if batch_id:
            sql += " AND r.batch_id=?"
            args.append(batch_id)
        sql += " ORDER BY (r.state='gated') DESC, r.started_at DESC LIMIT ?"
        args.append(limit)
        out = []
        for r in self._conn().execute(sql, args).fetchall():
            d = dict(r)
            # ⚠ 비교표는 **`inputs_json` 을 그대로 열로 편다**(PLAN S5). 단계 인자를
            # 역파싱하면 치환된 뒤 값이라 무엇이 달랐는지가 흐려진다.
            d["inputs"] = json.loads(d.pop("inputs_json") or "{}")
            out.append(d)
        return out

    # ── 단계 ──────────────────────────────────────────────────────────────
    def begin_step(self, run_id: str, ix: int, *, backend: str, tool: str, args: dict,
                   schema_fp: str | None = None, expect: str = "fast",
                   mode: str = "live", identity_note: str | None = None) -> None:
        """도구를 부르기 **전에** running 을 먼저 저장한다.

        재기동이 이 사이에 나면 그 단계는 `unknown(stage=restart)` 로 마감된다 — 쓰기가
        뒤늦게 완료됐을 수 있어 `failed` 가 아니다.
        """
        blob = json.dumps(args, ensure_ascii=False, sort_keys=True)
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO run_steps (run_id, ix, backend, tool, schema_fp,"
                " expect, args_json, args_sha256, state, started_at, mode, identity_note)"
                " VALUES (?,?,?,?,?,?,?,?,'running',?,?,?)",
                (run_id, ix, backend, tool, schema_fp, expect, blob,
                 hashlib.sha256(blob.encode("utf-8")).hexdigest(), _now(), mode,
                 identity_note),
            )

    def finish_step(self, run_id: str, ix: int, *, ok: bool, result_text: str | None = None,
                    error: str | None = None, duration_ms: int | None = None,
                    notes: dict | None = None, state: str | None = None,
                    stage: str | None = None) -> None:
        """결과는 gzip BLOB + bytes + sha256. 2MB 초과는 프리뷰만 남긴다."""
        st = state or ("done" if ok else "failed")
        if st not in STEP_STATES:
            raise ValueError(f"모르는 단계 상태: {st}")
        gz = size = digest = None
        trunc, preview = 0, None
        if result_text is not None:
            raw = result_text.encode("utf-8")
            size = len(raw)
            digest = hashlib.sha256(raw).hexdigest()
            if size > RESULT_MAX:
                trunc, preview = 1, result_text[:PREVIEW]
            else:
                gz = gzip.compress(raw)
        with self._conn() as c:
            c.execute(
                "UPDATE run_steps SET state=?, ok=?, error=?, result_gz=?, result_bytes=?,"
                " result_sha256=?, truncated=?, preview=?, notes=?, duration_ms=?, stage=?"
                " WHERE run_id=? AND ix=?",
                (st, 1 if ok else 0, error, gz, size, digest, trunc, preview,
                 json.dumps(notes, ensure_ascii=False) if notes else None,
                 duration_ms, stage, run_id, ix),
            )

    def step_result(self, run_id: str, ix: int) -> str | None:
        row = self._conn().execute(
            "SELECT result_gz, preview FROM run_steps WHERE run_id=? AND ix=?",
            (run_id, ix)).fetchone()
        if row is None:
            return None
        if row["result_gz"] is not None:
            return gzip.decompress(row["result_gz"]).decode("utf-8")
        return row["preview"]

    def list_steps(self, run_id: str) -> list[dict]:
        rows = self._conn().execute(
            "SELECT run_id, ix, backend, tool, schema_fp, expect, args_json, args_sha256,"
            " result_bytes, result_sha256, truncated, preview, notes, state, ok, error,"
            " stage, started_at, duration_ms, mode, identity_note, reused_from_run_id"
            " FROM run_steps WHERE run_id=? ORDER BY ix", (run_id,)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["args"] = json.loads(d.pop("args_json"))
            d["notes"] = json.loads(d["notes"]) if d.get("notes") else None
            out.append(d)
        return out

    def ack_gate(self, run_id: str, ix: int, *, by: str, args_sha256: str,
                 override: dict | None = None) -> None:
        """게이트 승인은 별도 행 — 승인자와 실행자가 달라도 감사가 된다."""
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO run_gate_acks (run_id, step_ix, ack_by, ack_at,"
                " args_sha256, args_override_json) VALUES (?,?,?,?,?,?)",
                (run_id, ix, by, _now(), args_sha256,
                 json.dumps(override, ensure_ascii=False) if override else None),
            )

    def gate_ack(self, run_id: str, ix: int) -> dict | None:
        row = self._conn().execute(
            "SELECT * FROM run_gate_acks WHERE run_id=? AND step_ix=?",
            (run_id, ix)).fetchone()
        return dict(row) if row else None

    # ── 기동 회복 ─────────────────────────────────────────────────────────
    def close_stale(self) -> int:
        """기동 시 `running` 이던 것을 마감한다. 프로세스와 함께 죽은 태스크들이다.

        단계는 `unknown` 이다 — 쓰기가 뒤늦게 완료됐을 수 있어 재실행 전에 사람이 본다.
        """
        with self._conn() as c:
            n = c.execute(
                "UPDATE run_steps SET state='unknown', stage='restart'"
                " WHERE state='running'").rowcount
            c.execute(
                "UPDATE runs SET state='failed', stage='restart', ended_at=?"
                " WHERE state IN ('running','queued')", (_now(),))
        return n

    # ── §6-1 쓸모 판정 ────────────────────────────────────────────────────
    def stats(self) -> dict:
        """절차 수 · 재생 실행 수 · 타인 재생 수 · 재생 완주율. 사후 복원이 안 되는 값들이다."""
        c = self._conn()
        procedures = c.execute("SELECT COUNT(*) FROM procedures").fetchone()[0]
        replays = c.execute("SELECT COUNT(*) FROM runs WHERE origin='replay'").fetchone()[0]
        by_others = c.execute(
            "SELECT COUNT(*) FROM runs r JOIN procedure_versions v"
            " ON r.procedure_version_id = v.version_id"
            " WHERE r.origin='replay' AND r.run_by <> v.author_sub").fetchone()[0]
        done = c.execute(
            "SELECT COUNT(*) FROM runs WHERE origin='replay' AND state='done'").fetchone()[0]
        return {
            "procedures": procedures,
            "replays": replays,
            "replays_by_others": by_others,
            "replay_completion": round(done / replays, 3) if replays else None,
        }
