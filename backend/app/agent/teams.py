# 전문가 팀 — 미리 만든 주 1 + 보조 4 조합의 저장소 · 칸 검증 · 보이기 규칙 · 그 사람의 시야로 푼 사본(docs/expert-teams PLAN 1 · 3)
"""절차 저장소(procedures.sqlite)의 연결을 같이 쓰는 표 하나다 — 분석 루틴 · 과제 인사이트와 같은 자리라 설정 · 서비스 표 · 백업 · 기동 · 시험 격리에
이미 등록된 저장소다(새로 등록할 것이 없다). 표가 없으면 기동이 만든다(CREATE TABLE IF NOT EXISTS — 이관은 그것 하나다).

- 팀은 **사람만 묶는다**(ET-2). 그 사람이 페르소나를 쓸 수 있는지는 저장 때 거르지 않고 쓰는 순간 그 사람의 권한으로 다시 본다(resolve).
- 보이기 — 주인 · scope=org 면 같은 소속(지금 원장 소속 — 과제 인사이트 카드의 소속 셈과 같다) · 관리자 전부. 없는 것과 못 보는 것은 같은 404 다.
- 판 번호(version)는 고칠 때마다 +1 — 고치기는 expected_version 이 지금 판과 같을 때만(어긋나면 409).
- 지우면 행이 사라진다. 이미 만든 사본(루틴 실행 원장 · 연 대화)은 제 사본을 쥐어 흔들리지 않는다(ET-3).
"""
from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.insights.cards import Viewer, owner_of

FEAT = "feat:expert-chat"
NAME_MAX, DESC_MAX, HELPERS_MAX, APPS_MAX, TOOLS_MAX = 60, 300, 4, 3, 12     # PLAN 1절 표 — 챗 지정값 상한과 같다(앱 3 · 도구 12)
TEAM_ID_RE = re.compile(r"^tm_[0-9a-f]{32}$")
_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:@-]{0,119}$")                # 페르소나 키(챗 pinned_agent 상한 120)
_APP_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$")                  # 게이트웨이 백엔드 키(루틴 단계의 울타리 꼴과 같다)
_TOOL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,119}$")                # 노출 도구 이름


class Member(BaseModel):
    model_config = {"extra": "forbid"}
    key: str
    name: str = Field("", max_length=200)

    @field_validator("key")
    @classmethod
    def _key(cls, v: str) -> str:
        v = (v or "").strip()
        if not _KEY_RE.match(v):
            raise ValueError(f"전문가 키 꼴이 아니다: {v[:40]!r}")
        return v

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        return (v or "").strip()


def _clean_list(v: list[str], pat: re.Pattern, what: str) -> list[str]:
    out = [str(x).strip() for x in v]
    bad = [x for x in out if not pat.match(x)]
    if bad:
        raise ValueError(f"{what} 이름 꼴이 아니다: {bad[:3]}")
    if len(set(out)) != len(out):
        raise ValueError(f"{what} 이 겹친다")
    return out


class TeamBody(BaseModel):
    """만들기 · 고치기에서 같은 칸 규칙. 고치기는 PATCH 라 칸이 다 없어도 된다(TeamPatch)."""
    model_config = {"extra": "forbid"}
    name: str = Field(min_length=1, max_length=NAME_MAX)
    description: str = Field("", max_length=DESC_MAX)
    lead: Member
    helpers: list[Member] = Field(default_factory=list, max_length=HELPERS_MAX)
    apps: list[str] = Field(default_factory=list, max_length=APPS_MAX)
    tools: list[str] = Field(default_factory=list, max_length=TOOLS_MAX)
    scope: Literal["private", "org"] = "private"

    @field_validator("name", "description")
    @classmethod
    def _strip(cls, v: str) -> str:
        return (v or "").strip()

    @field_validator("apps")
    @classmethod
    def _apps(cls, v: list[str]) -> list[str]:
        return _clean_list(v, _APP_RE, "앱")

    @field_validator("tools")
    @classmethod
    def _tools(cls, v: list[str]) -> list[str]:
        return _clean_list(v, _TOOL_RE, "도구")

    @model_validator(mode="after")
    def _whole(self):
        if not self.name:
            raise ValueError("팀 이름이 비었다")
        keys = [h.key for h in self.helpers]
        if len(set(keys)) != len(keys):
            raise ValueError("보조 전문가가 겹친다")
        if self.lead.key in keys:
            raise ValueError("주 전문가를 보조로 또 넣지 않는다")
        return self


class TeamPatch(BaseModel):
    model_config = {"extra": "forbid"}
    expected_version: int = Field(ge=1)
    name: str | None = Field(None, min_length=1, max_length=NAME_MAX)
    description: str | None = Field(None, max_length=DESC_MAX)
    lead: Member | None = None
    helpers: list[Member] | None = Field(None, max_length=HELPERS_MAX)
    apps: list[str] | None = Field(None, max_length=APPS_MAX)
    tools: list[str] | None = Field(None, max_length=TOOLS_MAX)
    scope: Literal["private", "org"] | None = None

    def merged(self, row: dict) -> TeamBody:
        """지금 행에 고칠 칸을 얹은 전체 — 전체 칸 규칙(겹침 · 주 전문가 중복)을 다시 본다."""
        cur = {k: row[k] for k in ("name", "description", "lead", "helpers", "apps", "tools", "scope")}
        cur.update(self.model_dump(exclude_none=True, exclude={"expected_version"}))
        return TeamBody.model_validate(cur)


# ── 보이기 ─────────────────────────────────────────────────────────────────────────────────────────────────
def visible(row: dict, v: Viewer) -> bool:
    """주인 · scope=org 면 같은 소속(빈 소속끼리는 같지 않다) · 관리자."""
    if not v.email:
        return False
    if owner_of(row, v) or v.admin:
        return True
    aff = str(row.get("owner_aff") or "")
    return row.get("scope") == "org" and bool(aff) and aff == v.aff


def editable(row: dict, v: Viewer) -> bool:
    return owner_of(row, v) or v.admin


def deletable(row: dict, v: Viewer) -> bool:
    """공식 표지가 달린 팀은 관리자만 지운다(PLAN 1절)."""
    return v.admin or (owner_of(row, v) and not row.get("official"))


def view(row: dict, v: Viewer) -> dict:
    """원장 행 → 응답 꼴(PLAN 3-1 Team) — 칸 + mine · editable · deletable."""
    return {k: row[k] for k in ("id", "name", "description", "lead", "helpers", "apps", "tools", "scope", "owner_email",
                                "owner_aff", "version", "created_at", "updated_at")} | {
        "official": bool(row.get("official")), "mine": owner_of(row, v), "editable": editable(row, v),
        "deletable": deletable(row, v)}


# ── 그 사람의 시야로 푼 사본(PLAN 3-2) ───────────────────────────────────────────────────────────────────────
@dataclass
class Resolved:
    """사본(없으면 None) · 까닭(빈 글이면 다 풀었다) · 이 사람이 못 쓰는 사람(빠진 보조 · 못 쓰는 주 전문가)."""
    team: dict | None
    why: str = ""
    hidden: list[dict] = field(default_factory=list)
    name: str = ""


def _who(m: dict) -> str:
    return f"{m.get('name') or m['key']}({m['key']})" if m.get("name") else m["key"]


def resolve(row: dict | None, v: Viewer, allowed, *, team_id: str = "") -> Resolved:
    """팀 → 그 사람의 사본. `allowed(key) -> bool` 은 그 사람이 그 페르소나를 쓸 수 있나(HE팀 운영자의 앱 권한 — agent_guard.persona_allowed).
    닫힌 쪽이다 — 못 보는 팀 · 전문가와 대화 권한 없음 · 주 전문가를 못 씀이면 사본이 없다(None + 까닭). 보조를 못 쓰면 그 사람만 빼고 알린다."""
    tid = (row or {}).get("id") or team_id
    if row is None or not visible(row, v):
        return Resolved(None, f"팀 {tid} 를 찾을 수 없다 — 지워졌거나 이 사람에게 보이지 않는다")
    if FEAT not in v.groups:
        return Resolved(None, f"전문가와 대화 권한({FEAT})이 없어 팀 「{row['name']}」 을 쓰지 않는다", name=row["name"])
    lead = row["lead"]
    if not allowed(lead["key"]):
        return Resolved(None, f"팀 「{row['name']}」 의 주 전문가 {_who(lead)} 를 이 사람이 쓸 수 없어(그 앱 권한이 없다) 팀을 쓰지 않는다",
                        hidden=[lead], name=row["name"])
    keep = [h for h in row["helpers"] if allowed(h["key"])]
    gone = [h for h in row["helpers"] if not allowed(h["key"])]
    snap = {"id": row["id"], "name": row["name"], "version": row["version"], "lead": dict(lead),
            "helpers": [dict(h) for h in keep], "apps": list(row["apps"]), "tools": list(row["tools"]),
            "resolved_at": int(time.time())}
    why = (f"팀 「{row['name']}」 의 보조 전문가 {', '.join(_who(h) for h in gone)} 는 이 사람이 쓸 수 없어(그 앱 권한이 없다) 뺐다"
           if gone else "")
    return Resolved(snap, why, gone, row["name"])


# ── 저장소 ─────────────────────────────────────────────────────────────────────────────────────────────────
_DDL = (
    """CREATE TABLE IF NOT EXISTS expert_teams (
        id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
        lead_json TEXT NOT NULL, helpers_json TEXT NOT NULL, apps_json TEXT NOT NULL, tools_json TEXT NOT NULL,
        scope TEXT NOT NULL DEFAULT 'private', official INTEGER NOT NULL DEFAULT 0, official_by TEXT, official_at INTEGER,
        owner_email TEXT NOT NULL, owner_sub TEXT, owner_aff TEXT NOT NULL DEFAULT '',
        version INTEGER NOT NULL DEFAULT 1, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL, updated_by TEXT)""",
    "CREATE INDEX IF NOT EXISTS ix_expert_teams_owner ON expert_teams (owner_email)",
    "CREATE INDEX IF NOT EXISTS ix_expert_teams_aff ON expert_teams (scope, owner_aff)",
)
_JSON = ("lead", "helpers", "apps", "tools")


def _row(r) -> dict | None:
    if r is None:
        return None
    d = dict(r)
    for k in _JSON:
        try:
            d[k] = json.loads(d.pop(f"{k}_json"))
        except ValueError:
            d[k] = {} if k == "lead" else []
    return d


def _cols(body: TeamBody) -> dict:
    return {"name": body.name, "description": body.description,
            "lead_json": json.dumps(body.lead.model_dump(), ensure_ascii=False),
            "helpers_json": json.dumps([h.model_dump() for h in body.helpers], ensure_ascii=False),
            "apps_json": json.dumps(body.apps, ensure_ascii=False), "tools_json": json.dumps(body.tools, ensure_ascii=False),
            "scope": body.scope}


class TeamStore:
    def __init__(self, base) -> None:
        """base — 열린 ProceduresStore. 연결은 그것의 스레드별 연결을 그대로 쓴다."""
        self._conn = base._conn
        with self._conn() as c:
            for stmt in _DDL:
                c.execute(stmt)

    def create(self, body: TeamBody, *, owner_email: str, owner_sub: str, owner_aff: str) -> dict:
        tid, now = f"tm_{uuid.uuid4().hex}", int(time.time())
        cols = _cols(body) | {"id": tid, "owner_email": owner_email.lower(), "owner_sub": owner_sub, "owner_aff": owner_aff or "",
                              "version": 1, "created_at": now, "updated_at": now, "updated_by": owner_email.lower()}
        c = self._conn()
        with c:
            c.execute(f"INSERT INTO expert_teams ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})", tuple(cols.values()))
        return self.get(tid)

    def get(self, tid: str) -> dict | None:
        return _row(self._conn().execute("SELECT * FROM expert_teams WHERE id=?", (tid,)).fetchone())

    def rows(self, v: Viewer) -> list[dict]:
        """그 사람이 볼 수 있는 팀 — 공식 먼저 · 최근 고친 것 먼저. 관리자는 전부."""
        q = "SELECT * FROM expert_teams"
        args: tuple = ()
        if not v.admin:
            q += " WHERE owner_email = ? OR (scope = 'org' AND owner_aff != '' AND owner_aff = ?)"
            args = (v.email, v.aff or "")
        q += " ORDER BY official DESC, updated_at DESC, id"
        return [_row(r) for r in self._conn().execute(q, args).fetchall()]

    def update(self, tid: str, body: TeamBody, *, expected_version: int, by: str,
               owner_aff: str | None = None) -> Literal["ok", "conflict", "missing"]:
        """판이 expected_version 일 때만 고친다(한 문장의 비교 — 동시에 고친 두 사람 중 하나만 이긴다). owner_aff 를 주면 그 값으로(주인이 고칠 때
        지금 소속으로 새긴다 — ET-6)."""
        cols = _cols(body) | {"updated_at": int(time.time()), "updated_by": by.lower()}
        if owner_aff is not None:
            cols["owner_aff"] = owner_aff
        c = self._conn()
        with c:
            cur = c.execute(f"UPDATE expert_teams SET {', '.join(f'{k}=?' for k in cols)}, version = version + 1"
                            " WHERE id=? AND version=?", (*cols.values(), tid, expected_version))
        if cur.rowcount == 1:
            return "ok"
        return "conflict" if self.get(tid) is not None else "missing"

    def delete(self, tid: str) -> bool:
        c = self._conn()
        with c:
            cur = c.execute("DELETE FROM expert_teams WHERE id=?", (tid,))
        return cur.rowcount == 1

    def set_official(self, tid: str, on: bool, *, by: str) -> bool:
        """공식 표지 — 판 번호 · 고친 때는 그대로다(구성이 바뀐 것이 아니다)."""
        c = self._conn()
        with c:
            cur = c.execute("UPDATE expert_teams SET official=?, official_by=?, official_at=? WHERE id=?",
                            (1 if on else 0, by.lower() if on else None, int(time.time()) if on else None, tid))
        return cur.rowcount == 1
