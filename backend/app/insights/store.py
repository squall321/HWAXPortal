# 과제 인사이트 원장 — 절차 저장소(procedures.sqlite)의 연결을 같이 쓰는 표 셋(카드 · 잇기 · 커서)(docs/project-insight-graph contracts §4)
"""분석 루틴과 같은 자리다 — 설정 · 서비스 표 · 백업 · 기동 · 시험 격리에 이미 등록된 저장소라 새로 등록할 것이 없다(PLAN §5.2).

- 같은 원천은 같은 id 하나다(INSERT OR IGNORE — 다시 들여도 하나). 거둔 카드는 내용을 지운 묘비(id · 주인 · 거둔 사람 · 때)로 남아 다시 들여도
  되살지 않는다.
- 시야는 여기서 거르지 않는다 — 원장의 행을 내고 라우트가 읽는 사람 기준으로 거른다(cards.visible). 원문(결정문 전문 · 회의록)은 옮기지 않는다 —
  짧은 주장 · 근거 표지 · 주제만 쥔다.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime

_DDL = (
    """CREATE TABLE IF NOT EXISTS insight_cards (
        id TEXT PRIMARY KEY, path TEXT NOT NULL, source_id TEXT NOT NULL, stage TEXT NOT NULL,
        owner_email TEXT NOT NULL, owner_sub TEXT, status TEXT NOT NULL,
        sp_task TEXT, round TEXT, round_by TEXT, subject_json TEXT NOT NULL,
        claim TEXT NOT NULL, claim_from TEXT NOT NULL, claim_edited_by TEXT, claim_edited_at INTEGER,
        card_json TEXT NOT NULL, scope_json TEXT NOT NULL, scope_note TEXT, continues TEXT,
        created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL,
        confirmed_at INTEGER, confirmed_by TEXT, withdrawn_at INTEGER, withdrawn_by TEXT)""",
    "CREATE INDEX IF NOT EXISTS ix_insight_sp ON insight_cards (sp_task, round)",
    "CREATE INDEX IF NOT EXISTS ix_insight_owner ON insight_cards (owner_email, status)",
    """CREATE TABLE IF NOT EXISTS insight_links (
        from_id TEXT NOT NULL, to_id TEXT NOT NULL, kind TEXT NOT NULL, by_email TEXT NOT NULL, note TEXT, at INTEGER NOT NULL,
        PRIMARY KEY (from_id, to_id, kind))""",
    "CREATE TABLE IF NOT EXISTS insight_meta (k TEXT PRIMARY KEY, v TEXT)",
)
_JSON = ("subject_json", "card_json", "scope_json")


def _now() -> int:
    return int(datetime.now(tz=UTC).timestamp())


def _row(r) -> dict | None:
    if r is None:
        return None
    d = dict(r)
    for k in _JSON:
        raw, empty = d.pop(k), ([] if k == "scope_json" else {})
        try:
            d[k[:-5]] = json.loads(raw) if raw else empty
        except ValueError:
            d[k[:-5]] = empty
    return d


class InsightStore:
    def __init__(self, base) -> None:
        """base — 열린 ProceduresStore. 연결은 그것의 스레드별 연결을 그대로 쓴다."""
        self._conn = base._conn
        with self._conn() as c:
            for stmt in _DDL:
                c.execute(stmt)

    # ── 들이기 ──
    def ingest(self, card: dict) -> bool:
        """카드 하나 — 같은 id 가 있으면(묘비 포함) 아무것도 하지 않고 거짓. 칸은 contracts §4 의 표 그대로다."""
        now = _now()
        c = self._conn()
        with c:
            cur = c.execute(
                "INSERT OR IGNORE INTO insight_cards (id, path, source_id, stage, owner_email, owner_sub, status, sp_task, round, round_by,"
                " subject_json, claim, claim_from, card_json, scope_json, continues, created_at, updated_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (card["id"], card["path"], card["source_id"], card["stage"], card["owner_email"].lower(), card.get("owner_sub"),
                 card["status"], card.get("sp_task"), card.get("round"), card.get("round_by"),
                 json.dumps(card.get("subject") or {}, ensure_ascii=False), card.get("claim") or "", card.get("claim_from") or "",
                 json.dumps(card.get("card") or {}, ensure_ascii=False), json.dumps(card.get("scope") or [], ensure_ascii=False),
                 card.get("continues"), now, now))
        return cur.rowcount == 1

    # ── 읽기 ──
    def get(self, cid: str) -> dict | None:
        return _row(self._conn().execute("SELECT * FROM insight_cards WHERE id=?", (cid,)).fetchone())

    def rows(self, *, sp_task: str | None = None, owner_email: str | None = None, limit: int = 2000) -> list[dict]:
        """거두지 않은 카드 — 최신 것부터. sp_task 는 글자 그대로, owner_email 은 그 사람의 것만(소문자)."""
        where, args = ["status != 'withdrawn'"], []
        if sp_task is not None:
            where.append("sp_task = ?")
            args.append(sp_task)
        if owner_email is not None:
            where.append("owner_email = ?")
            args.append(owner_email.lower())
        q = f"SELECT * FROM insight_cards WHERE {' AND '.join(where)} ORDER BY created_at DESC, id LIMIT ?"
        return [_row(r) for r in self._conn().execute(q, (*args, int(limit))).fetchall()]

    def links(self, ids: list[str]) -> list[dict]:
        """그 카드들에 닿는 잇기(반박) — 한쪽 끝이 ids 안에 있는 것."""
        if not ids:
            return []
        qs = ",".join("?" for _ in ids)
        return [dict(r) for r in self._conn().execute(
            f"SELECT * FROM insight_links WHERE from_id IN ({qs}) OR to_id IN ({qs}) ORDER BY at", (*ids, *ids)).fetchall()]

    # ── 쓰기(라우트가 권한을 본 뒤에 부른다) ──
    _COLS = frozenset({"owner_sub", "status", "sp_task", "round", "round_by", "subject", "claim", "claim_from", "claim_edited_by",
                       "claim_edited_at", "card", "scope", "scope_note", "confirmed_at", "confirmed_by"})

    def update(self, cid: str, **fields) -> bool:
        """거두지 않은 카드의 칸을 고친다(updated_at 도). 모르는 칸은 거절한다."""
        bad = set(fields) - self._COLS
        if bad:
            raise ValueError(f"모르는 칸 {sorted(bad)}")
        cols, args = [], []
        for k, v in fields.items():
            if k in ("subject", "card", "scope"):
                cols.append(f"{k}_json = ?")
                args.append(json.dumps(v, ensure_ascii=False))
            else:
                cols.append(f"{k} = ?")
                args.append(v)
        c = self._conn()
        with c:
            cur = c.execute(f"UPDATE insight_cards SET {', '.join(cols)}, updated_at = ? WHERE id = ? AND status != 'withdrawn'",
                            (*args, _now(), cid))
        return cur.rowcount == 1

    def withdraw(self, cid: str, *, by: str) -> bool:
        """거둔다 — 내용(주장 · 주제 · 카드 · 범위)을 지우고 묘비만 남긴다(PLAN §6.5). 잇기도 지운다."""
        now = _now()
        c = self._conn()
        with c:
            cur = c.execute(
                "UPDATE insight_cards SET status='withdrawn', sp_task=NULL, round=NULL, round_by=NULL, subject_json='{}', claim='',"
                " claim_from='', claim_edited_by=NULL, claim_edited_at=NULL, card_json='{}', scope_json='[]', scope_note=NULL,"
                " continues=NULL, withdrawn_at=?, withdrawn_by=?, updated_at=? WHERE id=? AND status != 'withdrawn'",
                (now, by.lower(), now, cid))
            c.execute("DELETE FROM insight_links WHERE from_id=? OR to_id=?", (cid, cid))
        return cur.rowcount == 1

    def link(self, from_id: str, to_id: str, *, kind: str, by: str, note: str = "") -> None:
        c = self._conn()
        with c:
            c.execute("INSERT OR REPLACE INTO insight_links (from_id, to_id, kind, by_email, note, at) VALUES (?,?,?,?,?,?)",
                      (from_id, to_id, kind, by.lower(), note, _now()))

    # ── 커서 ──
    def meta_get(self, k: str) -> str | None:
        r = self._conn().execute("SELECT v FROM insight_meta WHERE k=?", (k,)).fetchone()
        return r["v"] if r else None

    def meta_set(self, k: str, v: str) -> None:
        c = self._conn()
        with c:
            c.execute("INSERT INTO insight_meta (k, v) VALUES (?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, v))
