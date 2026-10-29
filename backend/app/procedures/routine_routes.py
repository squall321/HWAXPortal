# 분석 루틴 API(/routines-api) — 정의(짜기 · 판 · 보관 · 준비도 · 검증 · YAML)와 고를 수 있는 플랫폼(docs/analysis-routines/contracts.md §3, R1)
"""권한은 `feat:routines`. 짜기 · 판 더하기 · 보관 · 가져오기는 브라우저 세션 + CSRF 만 받는다(루틴은 사람이 화면에서 짠다). 읽기 · 준비도 · 검증은
세션 또는 PAT 를 받는다 — 게이트웨이의 `routine_list` · `routine_get` 이 호출자 PAT 를 그대로 넘긴다(대화 저장과 같은 길).

준비도는 막지 않는다 — 이 사람의 도구 목록(사람 PAT 의 tools/list, 권한 필터의 정본)과 이 박스의 /tools-map 으로 단계마다
allowed · denied(권한 없음) · not_connected(RA · 외부 연결 토큰 미등록) · unavailable(이 박스 게이트웨이에 없음)을 말한다.
"""
import logging

import yaml
from fastapi import APIRouter, Body, Depends, Query, Request, Response
from pydantic import BaseModel, Field

from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.config import Settings, get_settings
from app.deps import ensure, get_current_principal, principal_pat_or_session, require_csrf
from app.procedures.models import SpecError
from app.procedures.routes import RA_BACKEND, _gw, _runner, _tools_map
from app.procedures.routines import CONTRACT, RoutineSpec, is_write_tool, parse_spec

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/routines-api", tags=["routines"])
FEAT = "feat:routines"
DELIB_BACKEND = "hwax-deliberation"
IMPORT_MAX = 64 * 1024


def _store(request: Request):
    st = getattr(request.app.state, "routine_store", None)
    if st is None:
        raise AuthError("루틴 저장소가 열리지 않았습니다", status_code=503)
    return st


def _me(principal: Principal = Depends(get_current_principal)) -> Principal:
    """화면 전용(세션) — 쓰기 라우트는 여기에 require_csrf 를 더한다."""
    ensure(principal, FEAT)
    return principal


def _me_any(principal: Principal = Depends(principal_pat_or_session)) -> Principal:
    """세션 또는 PAT(게이트웨이가 넘긴 호출자 PAT) — 세션의 POST 는 principal_pat_or_session 이 CSRF 를 본다."""
    ensure(principal, FEAT)
    return principal


def _parse(raw) -> dict:
    try:
        return parse_spec(raw).model_dump(mode="json")
    except SpecError as exc:
        raise AuthError(f"루틴 스펙이 틀렸습니다 — {exc}"[:600], status_code=422) from None


class SpecIn(BaseModel):
    spec: dict


class ImportIn(BaseModel):
    yaml: str = Field(min_length=1, max_length=IMPORT_MAX)


@router.get("/health")
def health(request: Request, response: Response) -> dict:
    """무인증 — 게이트웨이가 '포털이 이 판보다 낡았다' 를 가르는 데 쓴다. 저장소가 안 열렸으면 503."""
    if getattr(request.app.state, "routine_store", None) is None:
        response.status_code = 503
        return {"ok": False, "contract": CONTRACT, "error": "루틴 저장소가 열리지 않았습니다"}
    return {"ok": True, "contract": CONTRACT}


async def _catalog(request: Request, principal: Principal) -> tuple[dict, dict]:
    """(이 사람이 부를 수 있는 도구 {백엔드: {원래 이름: 노출 이름 · 설명}}, 이 박스의 /tools-map)."""
    cat = await _gw(_runner(request).catalog(principal, run_id="routines"), "도구 목록")
    tmap = await _tools_map(request)
    owner = tmap.get("map") or {}
    mine: dict[str, dict] = {}
    for name, meta in cat.items():
        bk = owner.get(name)
        if not bk or bk == "_gateway":
            continue
        p = bk.replace("-", "") + "_"
        orig = name[len(p):] if name.startswith(p) else name     # 게이트웨이 별칭 규칙 — <백엔드에서 하이픈 뺀 것>_<원래 이름>
        mine.setdefault(bk, {})[orig] = {"exposed": name,
                                         "description": (meta.get("description") or "").strip().split("\n")[0][:200]}
    return mine, tmap


def _labels(tmap: dict) -> dict:
    return {a.get("app"): a.get("label") or a.get("app") for a in tmap.get("apps") or []}


@router.get("/platforms")
async def platforms(request: Request, principal: Principal = Depends(_me_any)) -> dict:
    """루틴 단계에 고를 수 있는 플랫폼 — 내 도구 목록을 백엔드로 묶는다. 이 박스에 있지만 내 권한 밖인 것은 따로 이름만."""
    mine, tmap = await _catalog(request, principal)
    labels = _labels(tmap)
    rows = [{"backend": bk, "label": labels.get(bk, bk),
             "tools": [{"name": n, "exposed": t["exposed"], "write": is_write_tool(n), "description": t["description"]}
                       for n, t in sorted(tools.items())]}
            for bk, tools in mine.items() if bk != DELIB_BACKEND]
    on_box = [a.get("app") for a in tmap.get("apps") or [] if a.get("app") not in (None, "_gateway")]
    return {"platforms": sorted(rows, key=lambda r: (r["label"].lower(), r["backend"])),
            "deliberation": "deliberate_start" in (mine.get(DELIB_BACKEND) or {}),
            "not_permitted": [{"backend": b, "label": labels.get(b, b)} for b in sorted(on_box) if b not in mine]}


def _connections_missing(request: Request, principal: Principal, settings: Settings, backends: set[str]) -> dict[str, str]:
    """토큰 등록이 필요한 백엔드(RA · 박스 권한표의 외부 연결) 가운데 이 사람이 등록하지 않은 것 → 까닭. 사전검사는 막지 않는다."""
    users = getattr(request.app.state, "user_store", None)
    if users is None:
        return {}
    need: dict[str, str] = {}
    if RA_BACKEND in backends and not settings.ra_sso_secret:
        need[RA_BACKEND] = "Report Archive"
    access = getattr(request.app.state, "access", None)
    if access is not None:
        try:
            for key, c in access.get().connections().items():
                if key in backends:
                    need[key] = c.label or key
        except Exception:  # noqa: BLE001 — 선언을 못 읽으면 모르는 것으로 둔다
            logger.info("루틴 준비도 — 외부 연결 선언을 읽지 못했다", exc_info=True)
    out = {}
    for key, label in need.items():
        try:
            conn = users.get_connection(email=principal.email, service=key)
        except Exception:  # noqa: BLE001
            continue
        if not (conn and conn.get("token")):
            out[key] = f"{label} 토큰이 등록되어 있지 않습니다 — 개인 토큰 › 외부 연결(/tokens?tab=connect)에서 등록하면 이 단계가 돈다"
    return out


async def readiness_of(request: Request, principal: Principal, settings: Settings, spec: RoutineSpec) -> list[dict]:
    mine, tmap = await _catalog(request, principal)
    labels = _labels(tmap)
    on_box = {a.get("app") for a in tmap.get("apps") or []}
    missing_conn = _connections_missing(request, principal, settings,
                                        {b for s in spec.steps for b in s.backends})
    out = []
    for s in spec.steps:
        if s.kind == "deliberation":
            ok = "deliberate_start" in (mine.get(DELIB_BACKEND) or {})
            state = "allowed" if ok else ("denied" if DELIB_BACKEND in on_box else "unavailable")
            out.append({"step": s.id, "state": state, "backends": [], "missing_tools": [],
                        "reason": "" if ok else "심의(전문가 심의 권한)를 부를 수 없다" if state == "denied" else "이 박스에 심의 엔진이 없다"})
            continue
        per = []
        for b in s.backends:
            st = ("not_connected" if b in missing_conn else "allowed") if b in mine else ("denied" if b in on_box else "unavailable")
            per.append({"backend": b, "label": labels.get(b, s.label or b), "state": st, "reason": missing_conn.get(b, "")})
        have = {t for b in s.backends for t in (mine.get(b) or {})}
        states = {p["state"] for p in per}
        state = "allowed" if "allowed" in states else next(
            (x for x in ("not_connected", "denied", "unavailable") if x in states), "unavailable")
        reasons = {"denied": "이 플랫폼 권한이 없다", "unavailable": "이 박스 게이트웨이에 없다",
                   "not_connected": next((p["reason"] for p in per if p["reason"]), "")}
        out.append({"step": s.id, "state": state, "backends": per,
                    "missing_tools": [t for t in s.tools if t not in have] if state == "allowed" else [],
                    "reason": "" if state == "allowed" else reasons[state]})
    return out


@router.get("/routines")
def list_routines(request: Request, q: str = Query("", max_length=200),
                  principal: Principal = Depends(_me_any)) -> dict:
    rows = _store(request).list(sub=principal.subject, q=q)
    return {"count": len(rows), "routines": rows}


@router.post("/routines", status_code=201, dependencies=[Depends(require_csrf)])
def create_routine(request: Request, body: SpecIn, principal: Principal = Depends(_me)) -> dict:
    return _store(request).create(owner_sub=principal.subject, spec=_parse(body.spec))


def _readable(request: Request, principal: Principal, routine_id: str, version: int | None) -> dict:
    got = _store(request).readable(sub=principal.subject, routine_id=routine_id, version_no=version)
    if got is None:
        raise AuthError("루틴을 찾을 수 없습니다", status_code=404)
    return got


@router.get("/routines/{routine_id}")
def get_routine(request: Request, routine_id: str, version: int | None = Query(None, ge=1),
                principal: Principal = Depends(_me_any)) -> dict:
    got = _readable(request, principal, routine_id, version)
    return {**got, "mine": got["routine"]["owner_sub"] == principal.subject,
            "versions": _store(request).versions(sub=principal.subject, routine_id=routine_id) or []}


@router.post("/routines/{routine_id}/versions", status_code=201, dependencies=[Depends(require_csrf)])
def add_version(request: Request, routine_id: str, body: SpecIn, principal: Principal = Depends(_me)) -> dict:
    try:
        return _store(request).add_version(routine_id=routine_id, author_sub=principal.subject, spec=_parse(body.spec))
    except KeyError:
        raise AuthError("루틴을 찾을 수 없습니다 — 판은 주인만 더한다(남의 루틴은 내보내기 · 가져오기로 내 것을 만든다)",
                        status_code=404) from None


@router.delete("/routines/{routine_id}", dependencies=[Depends(require_csrf)])
def archive_routine(request: Request, routine_id: str, principal: Principal = Depends(_me)) -> dict:
    if not _store(request).archive(routine_id=routine_id, owner_sub=principal.subject):
        raise AuthError("루틴을 찾을 수 없습니다 — 보관은 주인만 한다", status_code=404)
    return {"ok": True, "archived": True}


@router.get("/routines/{routine_id}/readiness")
async def readiness(request: Request, routine_id: str, version: int | None = Query(None, ge=1),
                    settings: Settings = Depends(get_settings), principal: Principal = Depends(_me_any)) -> dict:
    got = _readable(request, principal, routine_id, version)
    spec = RoutineSpec.model_validate(got["version"]["spec"])
    return {"routine_id": routine_id, "version_no": got["version"]["version_no"],
            "steps": await readiness_of(request, principal, settings, spec)}


@router.post("/validate")
def validate(body: SpecIn, principal: Principal = Depends(_me_any)) -> dict:
    """검증만 — 저장하지 않는다. 틀리면 422 와 까닭, 맞으면 기본값을 채운 스펙."""
    return {"ok": True, "spec": _parse(body.spec)}


@router.get("/routines/{routine_id}/export")
def export_routine(request: Request, routine_id: str, version: int | None = Query(None, ge=1),
                   principal: Principal = Depends(_me_any)) -> Response:
    got = _readable(request, principal, routine_id, version)
    text = yaml.safe_dump(got["version"]["spec"], allow_unicode=True, sort_keys=False)
    return Response(content=text, media_type="application/x-yaml; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="routine-{routine_id[:8]}.yaml"'})


@router.post("/import", status_code=201, dependencies=[Depends(require_csrf)])
def import_routine(request: Request, body: ImportIn = Body(...), principal: Principal = Depends(_me)) -> dict:
    """YAML 을 내 새 루틴으로 — 남의 루틴을 고치는 길이다(판은 주인만 더한다)."""
    try:
        raw = yaml.safe_load(body.yaml)
    except yaml.YAMLError as exc:
        raise AuthError(f"YAML 을 읽지 못했습니다 — {str(exc)[:200]}", status_code=422) from None
    return _store(request).create(owner_sub=principal.subject, spec=_parse(raw))
