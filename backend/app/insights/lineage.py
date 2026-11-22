# 과제 인사이트의 읽을 때 셈 — 설계 판의 뒤 판(StepForge 개정 줄) · 뒤 판의 리스크 변경 심사 · 과제 key 의 이력(docs/project-insight-graph PLAN §4.3 · §8 · M4)
"""읽는 사람의 PAT 로 게이트웨이를 불러 그때 셈하고 저장하지 않는다(PLAN §8). 못 읽으면 '모름' 이다 — 낡았다고도 그대로라고도 하지 않는다.

  · 기구 CAD(StepForge) — 과제 하나가 CAD 개정 하나다. `get_project_meta.revision` 의 뒤 판(`next` — 이 과제를 앞 판으로 가리키는 개정)과 내용 지문
    (`content_fp` · `content_changed`)으로 '새 판 있음 · 내용이 바뀜' 까지만 안다(일반 심의 카드에는 부품 열쇠가 없다).
  · 리스크 변경 심사 — 뒤 판의 CAD 과제를 원천으로 쓰는 리스크 과제의 변경 심사(diff:)가 그 사람 시야에 있으면 바뀐 줄을 함께 보인다. 그 비교의 앞
    판이 카드의 판인지는 리스크 앱 도구가 말해 주지 않아 확인하지 않는다 — 그렇게 적어 보이고 판단은 사람이 한다.
  · 과제 key 의 이력 — 지금 key 의 옛 key(이름 바뀜 · 합쳐짐 — StepForge onto_object 의 keys)로 남은 카드를 지금 과제에 모은다. 옛 key 가 지금 다른
    산 과제의 key 면 그 과제의 것이라 모으지 않는다.
  · 회로 보드(ODB 허브) · 해석 리포트의 뒤 판은 셈하지 않는다(보드는 그 팀의 답 뒤 — PLAN §10 · 받은 편지함 Q18).
도구 이름은 게이트웨이의 호출 전용 별칭이다(<백엔드 키에서 - 를 뺀 것>_<원래 이름> — 겹침과 무관하게 늘 선다)."""
from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable, Callable

from app.agent import subject as _subject
from app.auth.errors import AuthError

Call = Callable[[str, dict], Awaitable[dict]]

STEPFORGE_META = "heaxstep_forge_get_project_meta"
STEPFORGE_OBJECT = "heaxstep_forge_onto_object"
RISK_FIND = "heaxhwax_risk_risk_find_projects_by_subject"
RISK_DIFF = "heaxhwax_risk_risk_get_diff"
TASK_TYPE = "plm_task"            # SP 과제의 타입 slug(StepForge core/sp_core.py TASK_TYPE)
# 기한 — 안쪽이 먼저 걸려야 한다. 호출 하나(CALL_TIMEOUT_S) ≤ 한 갈래 전체(READ_BUDGET_S — 개정 줄 · 리스크 변경 심사 · key 이력이 저마다) 이고,
# 카드 하나를 읽는 창구의 안쪽 합(개정 줄 + 리스크 변경 심사 = 2 × READ_BUDGET_S)이 게이트웨이 insight_get 의 기한(30초)보다 짧아야 한다 — 넘으면
# '모름' 으로 답하지 못하고 도구가 통째로 실패한다(반대 검토 11-22 L6 — 종전엔 호출 하나 15초를 차례로 불러 안쪽이 더 길었다). 시험이 견준다.
CALL_TIMEOUT_S = 8.0
READ_BUDGET_S = 10.0
CONCURRENCY = 4
PROJECTS_MAX = 12                 # 한 번에 StepForge 에 묻는 CAD 과제 수 — 넘는 것은 '모름' 으로 말한다
OLD_KEYS_MAX = 5                  # 한 과제에 모으는 옛 key 수
NEXT_MAX, DIFFS_MAX, DIFF_LINES, LINE_MAX = 2, 3, 20, 300
_FP_RE = re.compile(r"[0-9a-f]{8,64}")     # 내용 지문 꼴(16진) — 사람이 적은 판 표지('C2')와 지문을 견주지 않는다
NOT_CHECKED = {"ecad": "회로 보드의 뒤 판은 셈하지 않는다(ODB 허브 팀의 답 뒤)", "cae": "해석 리포트의 뒤 판은 셈하지 않는다"}
RISK_DIFF_NOTE = ("뒤 판의 CAD 과제를 원천으로 쓰는 리스크 과제의 변경 심사다 — 그 비교의 앞 판이 이 카드의 판인지는 확인하지 않았다"
                  "(리스크 앱에서 본다). 판단은 사람이 한다.")


def caller(settings, pat: str, *, timeout: float = CALL_TIMEOUT_S) -> Call:
    """그 사람의 PAT 로 게이트웨이 도구를 한 번 부르는 함수."""
    from app.agent import upload as _upload

    async def call(tool: str, args: dict) -> dict:
        return await _upload.mcp_call(settings.mcp_gateway_url, pat, tool, args, timeout=timeout)
    return call


async def bounded(coro, budget_s: float):
    """coro 를 budget_s 초 안에서 — 넘기면 TimeoutError 를 낸다. 넘긴 일은 취소만 걸고 **끝나기를 기다리지 않는다**(게이트웨이 호출은 취소된 뒤에도
    세션 닫기를 보내느라 호출 기한만큼 더 걸린다 — 그것을 기다리면 상한이 그만큼 늘어난다, 반대 검토 11-22 L5). 부른 쪽이 취소되면 같이 취소한다."""
    task = asyncio.ensure_future(coro)
    try:
        done, _pending = await asyncio.wait({task}, timeout=budget_s)
    except BaseException:
        _abandon(task)
        raise
    if not done:
        _abandon(task)
        raise TimeoutError
    return task.result()


def _abandon(task: asyncio.Future) -> None:
    """취소를 걸고 뒤처리는 뒤에서 끝나게 둔다 — 끝난 뒤의 예외는 읽어 둔다(읽지 않은 예외 경고가 로그를 채우지 않게)."""
    task.cancel()
    task.add_done_callback(lambda t: t.cancelled() or t.exception())


async def _ask(call: Call, tool: str, args: dict) -> tuple[dict | None, str]:
    """(답, "") 또는 (None, 까닭) — 도구 거절 · 불통 · 못 읽은 답을 '모름' 으로 가른다(읽기를 막지 않는다)."""
    try:
        out = await call(tool, args)
    except AuthError as exc:
        return None, str(exc.message)[:200]
    except Exception as exc:  # noqa: BLE001 — 게이트웨이 불통 · 기한 · JSON 이 아닌 답
        return None, f"게이트웨이에 닿지 못했다({type(exc).__name__})"
    return (out, "") if isinstance(out, dict) else (None, "답을 읽지 못했다")


# ── 기구 CAD 의 개정 줄 ──────────────────────────────────────────────────────────────────────────────────
def revision_of(meta: dict) -> dict:
    """get_project_meta 답 → {state: ok, decided, content_fp, content_changed, rev_label, next[{project_id, rev_label}]} · 개정 칸이 없으면 unknown."""
    rev = meta.get("revision") if isinstance(meta, dict) else None
    if not isinstance(rev, dict):
        return {"state": "unknown", "why": "답에 개정 정보(revision)가 없다"}
    nxt = [{"project_id": k["project_id"][:64], "rev_label": (str(k["rev_label"])[:80] if k.get("rev_label") else None)}
           for k in rev.get("next") or [] if isinstance(k, dict) and isinstance(k.get("project_id"), str) and k["project_id"]]
    fp, changed, label = rev.get("content_fp"), rev.get("content_changed"), rev.get("rev_label")
    return {"state": "ok", "decided": rev.get("decided") is True, "content_fp": fp if isinstance(fp, str) and fp else None,
            "content_changed": changed if isinstance(changed, bool) else None,
            "rev_label": label[:80] if isinstance(label, str) and label else None, "next": nxt}


async def mcad_revisions(call: Call, project_ids: list[str], *, budget_s: float = READ_BUDGET_S) -> dict[str, dict]:
    """CAD 과제 id → 개정 정보(revision_of) 또는 {state: unknown, why}. 같은 id 는 한 번, PROJECTS_MAX 개까지 묻고 나머지는 모름이다. 전체가
    budget_s 초를 넘으면 그때까지 답한 것만 쓰고 나머지는 모름이다(늦은 호출은 취소만 걸고 기다리지 않는다)."""
    ids = list(dict.fromkeys(i for i in project_ids if isinstance(i, str) and i))
    out: dict[str, dict] = {i: {"state": "unknown", "why": f"한 번에 보는 CAD 과제 수({PROJECTS_MAX})를 넘어 묻지 않았다"} for i in ids[PROJECTS_MAX:]}
    sem = asyncio.Semaphore(CONCURRENCY)

    async def one(pid: str) -> None:
        async with sem:
            meta, why = await _ask(call, STEPFORGE_META, {"project_id": pid})
        out[pid] = revision_of(meta) if meta is not None else {"state": "unknown", "why": why}
    tasks = [asyncio.ensure_future(one(i)) for i in ids[:PROJECTS_MAX]]
    if tasks:
        try:
            _done, pending = await asyncio.wait(tasks, timeout=budget_s)
        except BaseException:
            for t in tasks:
                _abandon(t)
            raise
        for t in pending:
            _abandon(t)
    for i in ids[:PROJECTS_MAX]:
        out.setdefault(i, {"state": "unknown", "why": f"개정 줄의 답이 기한({budget_s:.0f}초) 안에 오지 않았다"})
    return out


def mcad_ids(rows: list[dict]) -> list[str]:
    """카드들의 주제에 든 기구 CAD 과제 id(차례대로 · 한 번씩)."""
    return list(dict.fromkeys(str(a["id"]) for r in rows for a in (r.get("subject") or {}).get("artifacts") or ()
                              if isinstance(a, dict) and a.get("kind") == "mcad" and isinstance(a.get("id"), str) and a["id"]))


_REASON = {"newer": "뒤 판이 있다", "fp_changed": "그때의 내용 지문과 지금이 다르다", "content_changed": "개정을 정한 뒤 STEP 내용이 바뀌었다"}


def card_stale(subject: dict, revs: dict[str, dict]) -> dict | None:
    """카드의 주제(설계 자료 · 그때의 판) + 지금의 개정 정보 → {state, say, items[...]} · 설계 자료가 없으면 None.
    state — stale(기구 CAD 가운데 하나라도 뒤 판이 있거나 내용이 바뀌었다) · current(견준 것이 다 그대로다) · unknown(못 읽은 것이 있다) ·
    not_checked(견줄 수 있는 설계 자료가 없다 — 보드 · 해석뿐)."""
    items: list[dict] = []
    for a in (subject or {}).get("artifacts") or ():
        if not isinstance(a, dict) or not isinstance(a.get("id"), str):
            continue
        kind, aid, rev = str(a.get("kind") or ""), a["id"], (a.get("rev") if isinstance(a.get("rev"), str) and a["rev"] else None)
        if kind != "mcad":
            items.append({"kind": kind, "id": aid, "rev": rev, "state": "not_checked", "why": NOT_CHECKED.get(kind, "셈하지 않는 종류다")})
            continue
        info = revs.get(aid)
        if not info or info.get("state") != "ok":
            items.append({"kind": kind, "id": aid, "rev": rev, "state": "unknown", "why": (info or {}).get("why") or "묻지 않았다"})
            continue
        reasons = ["newer"] if info["next"] else []
        if rev and _FP_RE.fullmatch(rev) and info["content_fp"] and rev != info["content_fp"]:
            reasons.append("fp_changed")
        if info["content_changed"] is True:
            reasons.append("content_changed")
        items.append({"kind": kind, "id": aid, "rev": rev, "state": "stale" if reasons else "current", "reasons": reasons,
                      "next": info["next"], "now_rev": info["content_fp"], "now_label": info["rev_label"]})
    if not items:
        return None
    mc = [i for i in items if i["kind"] == "mcad"]
    state = ("stale" if any(i["state"] == "stale" for i in mc) else "unknown" if any(i["state"] == "unknown" for i in mc)
             else "current" if mc else "not_checked")
    return {"state": state, "say": stale_say(state, items), "items": items}


def stale_say(state: str, items: list[dict], *, detail: bool = True) -> str:
    """판 표지 한 줄. detail 이 거짓이면 판정 낱말만이다 — 뒤 판의 이름 · id 를 싣지 않는다(public)."""
    if state == "stale":
        why = list(dict.fromkeys(_REASON[x] for i in items if i["state"] == "stale" for x in i.get("reasons") or ()))
        nxt = [n.get("rev_label") or n["project_id"] for i in items if i["state"] == "stale" for n in i.get("next") or ()] if detail else []
        return "낡았을 수 있다 — 기구 CAD: " + " · ".join(why) + (f"(뒤 판 {', '.join(nxt[:3])})" if nxt else "")
    if state == "unknown":
        return "판이 바뀌었는지 모른다 — 기구 CAD 의 개정 줄을 읽지 못했다"
    if state == "current":
        return "기구 CAD 는 그때의 판 그대로다(뒤 판 없음)"
    return "판이 바뀌었는지 셈하지 않았다 — 기구 CAD 가 없는 주제다"


def public(stale: dict | None) -> dict | None:
    """판 표지의 **판정 낱말만** — {state, say}. 뒤 판의 CAD 과제 id · 개정 이름 · 지금 지문 · 리스크 변경 줄은 싣지 않는다. 그것들은 읽는 사람의
    플랫폼 권한(StepForge · 리스크 앱)으로 읽은 것이라, 근거로 다시 퍼지는 자리(깐 근거의 '판' 줄 · 게이트웨이 insight_get 의 답 — 그 답을 근거로 쓴
    카드의 범위에는 그 플랫폼 토큰이 없다)에는 낱말만 낸다. 자세한 것은 포털 화면(세션)의 그 사람에게만이다(반대 검토 11-22 M1)."""
    if not stale:
        return None
    return {"state": stale["state"], "say": stale_say(stale["state"], stale.get("items") or [], detail=False)}


def next_ids(stale: dict | None) -> list[str]:
    """낡음 표지에서 뒤 판의 CAD 과제 id(차례대로 · 한 번씩)."""
    return list(dict.fromkeys(n["project_id"] for i in (stale or {}).get("items") or () for n in i.get("next") or ()))


# ── 뒤 판의 리스크 변경 심사 ───────────────────────────────────────────────────────────────────────────────
async def risk_diffs(call: Call, mcad_next: list[str], *, budget_s: float = READ_BUDGET_S) -> tuple[list[dict], str]:
    """뒤 판의 CAD 과제를 원천으로 쓰는 리스크 과제의 변경 심사(diff:) — (줄 묶음들, 까닭). 리스크 앱이 그 사람 시야로 낸 것만이다. 줄은 리스크 앱의
    변경 목록 글 그대로다(DIFF_LINES 줄까지 · 줄마다 LINE_MAX 자). 전체가 budget_s 초를 넘으면 그때까지 읽은 것만 낸다."""
    out: list[dict] = []
    notes: list[str] = []
    try:
        await bounded(_risk_diffs(call, mcad_next, out, notes), budget_s)
    except TimeoutError:
        notes.append(f"리스크 앱의 답이 기한({budget_s:.0f}초) 안에 다 오지 않았다")
    return out, " · ".join(dict.fromkeys(notes))


async def _risk_diffs(call: Call, mcad_next: list[str], out: list, notes: list) -> None:
    for pid in mcad_next[:NEXT_MAX]:
        found, why = await _ask(call, RISK_FIND, {"artifact_kind": "mcad", "artifact_id": pid, "limit": 5})
        if found is None:
            notes.append(f"리스크 앱을 읽지 못했다 — {why}")
            continue
        for p in found.get("projects") or ():
            for t in (p.get("targets") or ()) if isinstance(p, dict) else ():
                key = t.get("target_key") if isinstance(t, dict) else None
                if not (isinstance(key, str) and key.startswith("diff:") and key[5:]) or len(out) >= DIFFS_MAX:
                    continue
                head = {"target_key": key[:80], "mcad_project_id": pid,
                        "risk_project": {"project_id": str(p.get("project_id") or "")[:64], "code": str(p.get("code") or "")[:80],
                                         "name": str(p.get("name") or "")[:200]}}
                got, why = await _ask(call, RISK_DIFF, {"diff_id": key[5:], "part": "lines", "limit": DIFF_LINES})
                if got is None:
                    out.append({**head, "error": why})
                    continue
                lines = [ln[:LINE_MAX] for ln in str(got.get("lines") or "").split("\n") if ln.strip()][:DIFF_LINES]
                total = got.get("total")
                out.append({**head, "total": total if isinstance(total, int) and not isinstance(total, bool) else len(lines),
                            "by_kind": {str(k)[:40]: v for k, v in (got.get("by_kind") or {}).items() if isinstance(v, int)}
                            if isinstance(got.get("by_kind"), dict) else {},
                            "lines": lines, "truncated": bool(got.get("truncated"))})


# ── 과제 key 의 이력 ──────────────────────────────────────────────────────────────────────────────────────
async def old_keys(call: Call, key: str, have: set[str], *, budget_s: float = READ_BUDGET_S) -> tuple[list[str], str]:
    """지금 과제 key 의 옛 key(previous_keys — 이름 바뀜 · merged_from — 합쳐진 과제) 가운데 have(원장에 카드가 있는 key)에 든 것 — (옛 key 들, 까닭).
    옛 key 가 지금 다른 산 과제의 key 면(풀이 결과에 글자 그대로 같은 활성 행이 하나) 그 과제의 것이라 뺀다. 못 읽으면 모으지 않는다(닫힌 쪽) —
    전체가 budget_s 초를 넘겨도 같다."""
    want = {k for k in have if k != key}
    if not want:
        return [], ""
    try:
        return await bounded(_old_keys(call, key, want), budget_s)
    except TimeoutError:
        return [], f"과제 key 의 이력을 기한({budget_s:.0f}초) 안에 읽지 못했다 — 옛 key 로 남은 카드가 있어도 여기 모으지 않았다"


async def _old_keys(call: Call, key: str, want: set[str]) -> tuple[list[str], str]:
    card, why = await _ask(call, STEPFORGE_OBJECT, {"focus": f"{TASK_TYPE}:{key}", "history": False})
    if card is None or card.get("type") != TASK_TYPE or card.get("key") != key:
        return [], f"과제 key 의 이력을 읽지 못했다 — 옛 key 로 남은 카드가 있어도 여기 모으지 않았다({why or '답이 그 과제가 아니다'})"
    keys = card.get("keys") if isinstance(card.get("keys"), dict) else {}
    cand = [k for k in dict.fromkeys([*(keys.get("previous_keys") or ()), *(keys.get("merged_from") or ())])
            if isinstance(k, str) and k in want]
    out, taken, lost = [], [], []
    for k in cand[:OLD_KEYS_MAX]:
        rows, why = await _ask(call, _subject.RESOLVER_CALL, {"query": k, "limit": _subject.CONFIRM_LIMIT, "full": True})
        if rows is None:
            lost.append(k)
        elif _subject.confirm_rows(rows, k)[0]:
            taken.append(k)          # 지금 다른 산 과제가 그 key 를 쓴다 — 그 key 의 카드는 그 과제의 것이다
        else:
            out.append(k)
    notes = []
    if taken:
        notes.append(f"옛 key {len(taken)}개는 지금 다른 과제의 key 라 모으지 않았다")
    if lost:
        notes.append(f"옛 key {len(lost)}개는 지금도 쓰이는 key 인지 확인하지 못해 모으지 않았다")
    if len(cand) > OLD_KEYS_MAX:
        notes.append(f"옛 key 가 많아 앞 {OLD_KEYS_MAX}개만 봤다")
    return out, " · ".join(notes)
