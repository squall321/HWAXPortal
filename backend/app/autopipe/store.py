# 자동 파이프라인 원장 — 절차 저장소(procedures.sqlite)의 연결을 같이 쓰는 새 표(규칙 · 판 · 커서 · 주제 · 실행 · 단계 · 사건 · 잠금, portal-api §3)
"""루틴 저장소(procedures/routine_store.py)와 같은 까닭으로 절차 저장소 파일 · 스레드별 연결(WAL)을 쓴다 — 설정 · 백업 · 기동 · 시험 격리에 이미 등록된
파일이라 새로 등록할 것이 없다.

- 판(spec)은 불변이다. 고치면 새 판이다. 켜기/끄기는 판과 따로다(enabled · enabled_at · enabled_by).
- 실행의 유일 열쇠는 (rule_id, version_no, project, revision, fingerprint) 다 — 같으면 새로 만들지 않는다(INSERT 가 겹침으로 실패).
- 사건(auto_events)은 덧붙이기만 한다(감사).
- 시각은 엔진이 넘긴다(now) — 시험이 시계를 쥔다.
"""
from __future__ import annotations

import json
import sqlite3
import uuid

_DDL = (
    """CREATE TABLE IF NOT EXISTS auto_rules (
        id TEXT PRIMARY KEY, title TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 0, latest_version INTEGER NOT NULL DEFAULT 0,
        created_by TEXT NOT NULL, enabled_by TEXT, enabled_at INTEGER, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL,
        archived INTEGER NOT NULL DEFAULT 0)""",
    """CREATE TABLE IF NOT EXISTS auto_rule_versions (
        version_id TEXT PRIMARY KEY, rule_id TEXT NOT NULL, version_no INTEGER NOT NULL, spec_json TEXT NOT NULL,
        author TEXT NOT NULL, created_at INTEGER NOT NULL, UNIQUE (rule_id, version_no))""",
    """CREATE TABLE IF NOT EXISTS auto_cursors (
        source TEXT PRIMARY KEY, cursor TEXT, last_ok_at INTEGER, last_error TEXT, last_error_at INTEGER)""",
    """CREATE TABLE IF NOT EXISTS auto_subjects (
        skey TEXT PRIMARY KEY, project TEXT, revision TEXT, refs_json TEXT NOT NULL DEFAULT '{}',
        inputs_json TEXT NOT NULL DEFAULT '{}', fingerprint TEXT NOT NULL, ready_json TEXT NOT NULL DEFAULT '{}',
        first_seen INTEGER NOT NULL, last_change INTEGER NOT NULL, state TEXT NOT NULL, block_reason TEXT, updated_at INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS auto_runs (
        id TEXT PRIMARY KEY, rule_id TEXT NOT NULL, version_no INTEGER NOT NULL, project TEXT NOT NULL, revision TEXT NOT NULL,
        fingerprint TEXT NOT NULL, refs_json TEXT NOT NULL DEFAULT '{}', stage TEXT NOT NULL, state TEXT NOT NULL,
        superseded_by TEXT, approved_by TEXT, approved_at INTEGER, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL,
        ended_at INTEGER, reason TEXT, UNIQUE (rule_id, version_no, project, revision, fingerprint))""",
    """CREATE TABLE IF NOT EXISTS auto_run_steps (
        run_id TEXT NOT NULL, step_id TEXT NOT NULL, ix INTEGER NOT NULL, kind TEXT NOT NULL, state TEXT NOT NULL,
        idem_key TEXT, run_ref TEXT, check_json TEXT, status_json TEXT, result_json TEXT, verdict TEXT, report_md TEXT,
        ra_report_id TEXT, ra_state TEXT, ra_error TEXT, ra_attempts INTEGER NOT NULL DEFAULT 0, error TEXT,
        attempts INTEGER NOT NULL DEFAULT 0, submitted_at INTEGER, started_at INTEGER, ended_at INTEGER, polled_at INTEGER,
        PRIMARY KEY (run_id, step_id))""",
    """CREATE TABLE IF NOT EXISTS auto_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, at INTEGER NOT NULL, kind TEXT NOT NULL, detail_json TEXT NOT NULL DEFAULT '{}')""",
    """CREATE TABLE IF NOT EXISTS auto_lock (name TEXT PRIMARY KEY, holder TEXT, until INTEGER NOT NULL DEFAULT 0)""",
    "CREATE INDEX IF NOT EXISTS ix_auto_runs_rule ON auto_runs (rule_id, project, created_at)",
    "CREATE INDEX IF NOT EXISTS ix_auto_runs_state ON auto_runs (state)",
    "CREATE INDEX IF NOT EXISTS ix_auto_events_run ON auto_events (run_id, id)",
)

RUN_STATES = ("planned", "awaiting_approval", "running", "done", "partial", "failed", "superseded", "cancelled")
STEP_STATES = ("pending", "ready", "blocked", "queued", "running", "done", "failed", "cancelled", "skipped")
STEP_ENDED = ("done", "failed", "cancelled", "skipped", "blocked")
STEP_LIVE = ("queued", "running")          # 앱 쪽에서 도는 단계 — 대체 · 취소에도 끝까지 둔다(AP-D5)


def _j(v) -> str:
    return json.dumps(v, ensure_ascii=False)


def _l(s, default=None):
    return json.loads(s) if s else default


class AutoStore:
    def __init__(self, base) -> None:
        """base — 열린 ProceduresStore. 연결은 그것의 스레드별 연결을 그대로 쓴다."""
        self._conn = base._conn
        with self._conn() as c:
            for stmt in _DDL:
                c.execute(stmt)

    # ── 규칙 ─────────────────────────────────────────────────────────────────────────────────────────────────────────
    def create_rule(self, *, spec: dict, by: str, now: int) -> dict:
        rid, vid = uuid.uuid4().hex, uuid.uuid4().hex
        c = self._conn()
        with c:
            c.execute("INSERT INTO auto_rules (id, title, enabled, latest_version, created_by, created_at, updated_at)"
                      " VALUES (?,?,0,1,?,?,?)", (rid, spec["title"], by, now, now))
            c.execute("INSERT INTO auto_rule_versions (version_id, rule_id, version_no, spec_json, author, created_at) VALUES (?,?,1,?,?,?)",
                      (vid, rid, _j(spec), by, now))
            self._event(c, None, now, "rule_created", {"rule_id": rid, "version_no": 1, "by": by})
        return {"id": rid, "version_no": 1}

    def add_version(self, *, rule_id: str, spec: dict, by: str, now: int) -> dict | None:
        c = self._conn()
        with c:
            row = c.execute("SELECT latest_version FROM auto_rules WHERE id=? AND archived=0", (rule_id,)).fetchone()
            if row is None:
                return None
            no = int(row["latest_version"]) + 1
            c.execute("INSERT INTO auto_rule_versions (version_id, rule_id, version_no, spec_json, author, created_at) VALUES (?,?,?,?,?,?)",
                      (uuid.uuid4().hex, rule_id, no, _j(spec), by, now))
            c.execute("UPDATE auto_rules SET latest_version=?, title=?, updated_at=? WHERE id=?", (no, spec["title"], now, rule_id))
            self._event(c, None, now, "rule_version", {"rule_id": rule_id, "version_no": no, "by": by})
        return {"id": rule_id, "version_no": no}

    def set_enabled(self, *, rule_id: str, enabled: bool, by: str, now: int) -> dict | None:
        """켜면 enabled_at 을 새로 적는다 — 규칙은 켠 뒤에 바뀐 과제 · 차수에만 돈다(context-notes AP-12)."""
        c = self._conn()
        with c:
            row = c.execute("SELECT enabled FROM auto_rules WHERE id=? AND archived=0", (rule_id,)).fetchone()
            if row is None:
                return None
            if bool(row["enabled"]) != enabled:
                if enabled:
                    c.execute("UPDATE auto_rules SET enabled=1, enabled_by=?, enabled_at=?, updated_at=? WHERE id=?", (by, now, now, rule_id))
                else:
                    c.execute("UPDATE auto_rules SET enabled=0, updated_at=? WHERE id=?", (now, rule_id))
                self._event(c, None, now, "rule_enabled" if enabled else "rule_disabled", {"rule_id": rule_id, "by": by})
        return self.get_rule(rule_id)

    def _rule_row(self, row) -> dict:
        d = dict(row)
        d["enabled"] = bool(d["enabled"])
        d["archived"] = bool(d["archived"])
        return d

    def get_rule(self, rule_id: str) -> dict | None:
        c = self._conn()
        row = c.execute("SELECT * FROM auto_rules WHERE id=?", (rule_id,)).fetchone()
        if row is None:
            return None
        d = self._rule_row(row)
        vers = c.execute("SELECT version_no, spec_json, author, created_at FROM auto_rule_versions WHERE rule_id=? ORDER BY version_no DESC",
                         (rule_id,)).fetchall()
        d["versions"] = [{"version_no": v["version_no"], "author": v["author"], "created_at": v["created_at"]} for v in vers]
        d["spec"] = _l(vers[0]["spec_json"]) if vers else None
        return d

    def version_spec(self, rule_id: str, version_no: int) -> dict | None:
        row = self._conn().execute("SELECT spec_json FROM auto_rule_versions WHERE rule_id=? AND version_no=?",
                                   (rule_id, version_no)).fetchone()
        return _l(row["spec_json"]) if row else None

    def list_rules(self) -> list[dict]:
        rows = self._conn().execute(
            "SELECT r.*, v.spec_json FROM auto_rules r JOIN auto_rule_versions v ON v.rule_id=r.id AND v.version_no=r.latest_version"
            " WHERE r.archived=0 ORDER BY r.updated_at DESC").fetchall()
        out = []
        for row in rows:
            d = self._rule_row(row)
            spec = _l(d.pop("spec_json"), {})
            d["stage"] = spec.get("stage")
            d["steps"] = [{"id": s["id"], "kind": s["kind"]} for s in spec.get("steps") or []]
            out.append(d)
        return out

    def enabled_rules(self) -> list[dict]:
        """켜진 규칙과 그 최신 판의 스펙."""
        rows = self._conn().execute(
            "SELECT r.*, v.spec_json FROM auto_rules r JOIN auto_rule_versions v ON v.rule_id=r.id AND v.version_no=r.latest_version"
            " WHERE r.archived=0 AND r.enabled=1 ORDER BY r.created_at").fetchall()
        out = []
        for row in rows:
            d = self._rule_row(row)
            d["spec"] = _l(d.pop("spec_json"), {})
            out.append(d)
        return out

    # ── 감지 커서 ────────────────────────────────────────────────────────────────────────────────────────────────────
    def cursor(self, source: str) -> str | None:
        row = self._conn().execute("SELECT cursor FROM auto_cursors WHERE source=?", (source,)).fetchone()
        return row["cursor"] if row else None

    def cursor_ok(self, source: str, cursor: str | None, now: int) -> None:
        c = self._conn()
        with c:
            c.execute("INSERT INTO auto_cursors (source, cursor, last_ok_at) VALUES (?,?,?)"
                      " ON CONFLICT(source) DO UPDATE SET cursor=excluded.cursor, last_ok_at=excluded.last_ok_at, last_error=NULL",
                      (source, cursor, now))

    def cursor_error(self, source: str, error: str, now: int) -> None:
        c = self._conn()
        with c:
            c.execute("INSERT INTO auto_cursors (source, last_error, last_error_at) VALUES (?,?,?)"
                      " ON CONFLICT(source) DO UPDATE SET last_error=excluded.last_error, last_error_at=excluded.last_error_at",
                      (source, error[:500], now))

    def cursors(self) -> list[dict]:
        return [dict(r) for r in self._conn().execute("SELECT * FROM auto_cursors ORDER BY source").fetchall()]

    # ── 주제(과제 · 차수) ────────────────────────────────────────────────────────────────────────────────────────────
    def subject(self, skey: str) -> dict | None:
        row = self._conn().execute("SELECT * FROM auto_subjects WHERE skey=?", (skey,)).fetchone()
        return self._subject_row(row) if row else None

    @staticmethod
    def _subject_row(row) -> dict:
        d = dict(row)
        for k, default in (("refs_json", {}), ("inputs_json", {}), ("ready_json", {})):
            d[k.removesuffix("_json")] = _l(d.pop(k), default)
        return d

    def put_subject(self, d: dict, now: int) -> None:
        c = self._conn()
        with c:
            c.execute("INSERT INTO auto_subjects (skey, project, revision, refs_json, inputs_json, fingerprint, ready_json, first_seen,"
                      " last_change, state, block_reason, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"
                      " ON CONFLICT(skey) DO UPDATE SET refs_json=excluded.refs_json, inputs_json=excluded.inputs_json,"
                      " fingerprint=excluded.fingerprint, ready_json=excluded.ready_json, last_change=excluded.last_change,"
                      " state=excluded.state, block_reason=excluded.block_reason, updated_at=excluded.updated_at",
                      (d["skey"], d.get("project"), d.get("revision"), _j(d.get("refs") or {}), _j(d.get("inputs") or {}),
                       d["fingerprint"], _j(d.get("ready") or {}), d.get("first_seen") or now, d["last_change"], d["state"],
                       d.get("block_reason"), now))

    def drop_subject(self, skey: str) -> bool:
        """주제 줄 하나를 지운다 — 과제 key · 차수를 몰라 막힘으로 세웠던 자리 줄이 풀렸을 때만 쓴다(AP-28)."""
        c = self._conn()
        with c:
            cur = c.execute("DELETE FROM auto_subjects WHERE skey=?", (skey,))
        return cur.rowcount == 1

    def set_subject_state(self, skey: str, state: str, now: int) -> None:
        c = self._conn()
        with c:
            c.execute("UPDATE auto_subjects SET state=?, updated_at=? WHERE skey=? AND state!=?", (state, now, skey, state))

    def subjects(self, *, project: str | None = None, state: str | None = None, limit: int = 200,
                 open_only: bool = False) -> list[dict]:
        q, args = "SELECT * FROM auto_subjects WHERE 1=1", []
        if project:
            q += " AND project=?"
            args.append(project)
        if state:
            q += " AND state=?"
            args.append(state)
        if open_only:
            q += " AND state!='blocked'"
        rows = self._conn().execute(q + " ORDER BY last_change DESC LIMIT ?", (*args, limit)).fetchall()
        return [self._subject_row(r) for r in rows]

    # ── 실행 ─────────────────────────────────────────────────────────────────────────────────────────────────────────
    def has_run(self, *, rule_id: str, project: str, revision: str, fingerprint: str) -> bool:
        """이 규칙(어느 판이든)이 이 과제 · 차수 · 지문에 실행을 이미 만들었나 — 판을 고쳐도 같은 지문은 다시 돌지 않는다(AP-12)."""
        return self._conn().execute("SELECT 1 FROM auto_runs WHERE rule_id=? AND project=? AND revision=? AND fingerprint=? LIMIT 1",
                                    (rule_id, project, revision, fingerprint)).fetchone() is not None

    def create_run(self, *, rule_id: str, version_no: int, subject: dict, stage: str, steps: list[tuple[str, str]],
                   now: int) -> str | None:
        """steps — 의존 차례의 (단계 id, kind). 유일 열쇠가 겹치면 None(이미 있다)."""
        run_id = uuid.uuid4().hex
        c = self._conn()
        try:
            with c:
                c.execute("INSERT INTO auto_runs (id, rule_id, version_no, project, revision, fingerprint, refs_json, stage, state,"
                          " created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,'running',?,?)",
                          (run_id, rule_id, version_no, subject["project"], subject["revision"], subject["fingerprint"],
                           _j(subject.get("refs") or {}), stage, now, now))
                for ix, (sid, kind) in enumerate(steps):
                    c.execute("INSERT INTO auto_run_steps (run_id, step_id, ix, kind, state) VALUES (?,?,?,?,'pending')",
                              (run_id, sid, ix, kind))
                self._event(c, run_id, now, "run_created", {"rule_id": rule_id, "version_no": version_no, "stage": stage,
                                                            "project": subject["project"], "revision": subject["revision"],
                                                            "fingerprint": subject["fingerprint"]})
        except sqlite3.IntegrityError:
            return None
        return run_id

    def active_run(self, *, rule_id: str, project: str) -> str | None:
        """이 규칙 · 과제에서 나아가는(running) 또는 승인을 기다리는 실행 — 지금 돌리기가 앞 실행을 대체하지 않게 본다(AP-25)."""
        row = self._conn().execute("SELECT id FROM auto_runs WHERE rule_id=? AND project=? AND state IN ('running','awaiting_approval')"
                                   " ORDER BY created_at DESC, rowid DESC LIMIT 1", (rule_id, project)).fetchone()
        return row["id"] if row else None

    def latest_run(self, *, rule_id: str, project: str) -> str | None:
        """이 규칙 · 과제의 가장 최근 실행 — 다시 확인이 뒤 실행이 있는 옛 실행을 되살리지 않게 본다(AP-24)."""
        row = self._conn().execute("SELECT id FROM auto_runs WHERE rule_id=? AND project=? ORDER BY created_at DESC, rowid DESC LIMIT 1",
                                   (rule_id, project)).fetchone()
        return row["id"] if row else None

    def supersede(self, *, rule_id: str, project: str, new_run: str, now: int) -> list[str]:
        """AP-D5 — 같은 규칙 · 같은 과제의 앞 실행이 끝나지 않았으면: 도는 해석(queued · running)은 그대로, 아직 내지 않은 해석은 cancelled,
        보고서 단계는 남긴다(끝난 결과가 「대체됨」 표지로 보고서에 남는다), 실행은 superseded. 제출을 시작했지만 답을 잃은 단계(idem_key 만
        있다)도 그대로 둔다 — 앱에 잡이 섰을 수 있어 같은 idem_key 로 다시 물어 끝까지 본다."""
        c = self._conn()
        out = []
        with c:
            rows = c.execute("SELECT id FROM auto_runs WHERE rule_id=? AND project=? AND id!=? AND state IN ('running','awaiting_approval')",
                             (rule_id, project, new_run)).fetchall()
            for r in rows:
                rid = r["id"]
                c.execute("UPDATE auto_run_steps SET state='cancelled', error='superseded', ended_at=? WHERE run_id=? AND kind='analysis'"
                          " AND state IN ('pending','ready') AND idem_key IS NULL", (now, rid))
                c.execute("UPDATE auto_runs SET state='superseded', superseded_by=?, updated_at=? WHERE id=?", (new_run, now, rid))
                self._event(c, rid, now, "superseded", {"by": new_run})
                out.append(rid)
        return out

    def _run_row(self, row) -> dict:
        d = dict(row)
        d["refs"] = _l(d.pop("refs_json"), {})
        return d

    def get_run(self, run_id: str) -> dict | None:
        row = self._conn().execute("SELECT * FROM auto_runs WHERE id=?", (run_id,)).fetchone()
        return self._run_row(row) if row else None

    def runs(self, *, rule_id: str | None = None, project: str | None = None, state: str | None = None, limit: int = 100) -> list[dict]:
        q, args = "SELECT * FROM auto_runs WHERE 1=1", []
        for col, val in (("rule_id", rule_id), ("project", project), ("state", state)):
            if val:
                q += f" AND {col}=?"
                args.append(val)
        rows = self._conn().execute(q + " ORDER BY created_at DESC, rowid DESC LIMIT ?", (*args, limit)).fetchall()
        return [self._run_row(r) for r in rows]

    def open_runs(self) -> list[dict]:
        """엔진이 볼 실행 — 나아가는 것(running)과, 대체 · 취소됐지만 도는 해석 · 남은 보고서가 있어 끝나지 않은 것(ended_at 없음)."""
        rows = self._conn().execute("SELECT * FROM auto_runs WHERE state='running' OR (state IN ('superseded','cancelled') AND ended_at IS NULL)"
                                    " ORDER BY created_at, rowid").fetchall()
        return [self._run_row(r) for r in rows]

    def set_run(self, run_id: str, now: int, **fields) -> None:
        if not fields:
            return
        fields["updated_at"] = now
        cols = ", ".join(f"{k}=?" for k in fields)
        c = self._conn()
        with c:
            c.execute(f"UPDATE auto_runs SET {cols} WHERE id=?", (*fields.values(), run_id))

    def steps(self, run_id: str) -> list[dict]:
        out = []
        for r in self._conn().execute("SELECT * FROM auto_run_steps WHERE run_id=? ORDER BY ix", (run_id,)).fetchall():
            d = dict(r)
            for k in ("check_json", "status_json", "result_json"):
                d[k.removesuffix("_json")] = _l(d.pop(k))
            out.append(d)
        return out

    def set_step(self, run_id: str, step_id: str, now: int, **fields) -> None:
        if "state" in fields:
            if fields["state"] in STEP_ENDED:
                fields.setdefault("ended_at", now)
            fields.setdefault("started_at_if_null", now)
        start = fields.pop("started_at_if_null", None)
        for k in ("check", "status", "result"):
            if k in fields:
                v = fields.pop(k)
                fields[f"{k}_json"] = None if v is None else _j(v)
        cols = ", ".join(f"{k}=?" for k in fields)
        args = list(fields.values())
        if start is not None:
            cols += ", started_at=COALESCE(started_at, ?)"
            args.append(start)
        c = self._conn()
        with c:
            c.execute(f"UPDATE auto_run_steps SET {cols} WHERE run_id=? AND step_id=?", (*args, run_id, step_id))

    # ── 한도 셈 ──────────────────────────────────────────────────────────────────────────────────────────────────────
    def active_steps(self, rule_id: str | None = None) -> int:
        """앱 쪽에서 돌고 있거나(queued · running) 제출 답을 잃어 결과를 모르는(idem_key 만 있고 run_ref 없음) 해석 단계 수."""
        q = ("SELECT COUNT(*) FROM auto_run_steps s JOIN auto_runs r ON r.id=s.run_id WHERE s.kind='analysis' AND"
             " (s.state IN ('queued','running') OR (s.state='ready' AND s.idem_key IS NOT NULL AND s.run_ref IS NULL))")
        args: tuple = ()
        if rule_id:
            q += " AND r.rule_id=?"
            args = (rule_id,)
        return int(self._conn().execute(q, args).fetchone()[0])

    def runs_submitted_since(self, *, rule_id: str, project: str, since: int) -> int:
        """이 규칙 · 과제에서 since 뒤에 첫 제출을 한 실행 수 — 과제당 하루 상한(per_project_per_day)."""
        return int(self._conn().execute(
            "SELECT COUNT(*) FROM auto_runs r WHERE r.rule_id=? AND r.project=? AND"
            " (SELECT MIN(s.submitted_at) FROM auto_run_steps s WHERE s.run_id=r.id) >= ?", (rule_id, project, since)).fetchone()[0])

    def ra_retry_runs(self, attempts_max: int) -> list[str]:
        """RA 게시를 다시 해야 하는 보고서 단계가 있는 실행 — 초안 전 잠깐 실패(pending) · 초안만 섬(drafted), 상한 전."""
        rows = self._conn().execute("SELECT DISTINCT run_id FROM auto_run_steps WHERE kind='report' AND state='done'"
                                    " AND ra_state IN ('pending','drafted') AND ra_attempts < ?", (attempts_max,)).fetchall()
        return [r["run_id"] for r in rows]

    def previous_run(self, *, rule_id: str, project: str, revision: str, before: int) -> dict | None:
        """revdiff 의 맞댈 실행 — 같은 규칙 · 같은 과제의 다른 차수 가운데 이 실행보다 먼저 만든 마지막 done · partial 실행."""
        row = self._conn().execute(
            "SELECT * FROM auto_runs WHERE rule_id=? AND project=? AND revision!=? AND created_at<=? AND state IN ('done','partial')"
            " ORDER BY created_at DESC, rowid DESC LIMIT 1", (rule_id, project, revision, before)).fetchone()
        return self._run_row(row) if row else None

    # ── 사건 ─────────────────────────────────────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _event(c, run_id: str | None, now: int, kind: str, detail: dict) -> None:
        c.execute("INSERT INTO auto_events (run_id, at, kind, detail_json) VALUES (?,?,?,?)", (run_id, now, kind, _j(detail)))

    def event(self, run_id: str | None, now: int, kind: str, detail: dict | None = None) -> None:
        c = self._conn()
        with c:
            self._event(c, run_id, now, kind, detail or {})

    def events(self, run_id: str, limit: int = 500) -> list[dict]:
        rows = self._conn().execute("SELECT * FROM auto_events WHERE run_id=? ORDER BY id LIMIT ?", (run_id, limit)).fetchall()
        return [{"id": r["id"], "at": r["at"], "kind": r["kind"], "detail": _l(r["detail_json"], {})} for r in rows]

    # ── 세기 ─────────────────────────────────────────────────────────────────────────────────────────────────────────
    def counts(self) -> dict:
        c = self._conn()
        return {"rules_enabled": int(c.execute("SELECT COUNT(*) FROM auto_rules WHERE enabled=1 AND archived=0").fetchone()[0]),
                "runs": {r[0]: r[1] for r in c.execute("SELECT state, COUNT(*) FROM auto_runs GROUP BY state").fetchall()},
                "subjects": {r[0]: r[1] for r in c.execute("SELECT state, COUNT(*) FROM auto_subjects GROUP BY state").fetchall()}}

    # ── 박자 잠금(원장의 잠금 행 — 여러 프로세스가 같은 파일을 볼 때 한 박자만) ─────────────────────────────────────────────
    def lock(self, holder: str, now: int, lease: int = 600) -> bool:
        c = self._conn()
        with c:
            c.execute("INSERT OR IGNORE INTO auto_lock (name, holder, until) VALUES ('engine', NULL, 0)")
            cur = c.execute("UPDATE auto_lock SET holder=?, until=? WHERE name='engine' AND (holder=? OR until<?)",
                            (holder, now + lease, holder, now))
        return cur.rowcount == 1

    def unlock(self, holder: str) -> None:
        c = self._conn()
        with c:
            c.execute("UPDATE auto_lock SET until=0 WHERE name='engine' AND holder=?", (holder,))
