# 심의 전 '온톨로지 먼저 보기' — 확인된 주제 과제를 정본 허브에서 풀고 한 걸음 이웃을 사람이 고를 행으로 줄인다(docs/ontology-first M4 · OF-14 ③)
"""docs/ontology-first PLAN §5.2 · §6 · OF-8 · OF-14 ③. 엔진은 바뀌지 않는다 — 사람이 고른 행만 호출자 근거(delib_opts.evidence)로 들어간다.

  · 닻 — 심의 주제(과제 인사이트 그래프 M1)의 과제 key. 브라우저가 보낸 key 는 근거가 아니다 — M1 과 같은 풀이(StepForge find_plm_task — 허브 거울)를
    그 사람의 PAT 로 불러 key 가 글자 그대로 같은 활성 행이 하나일 때만 확인이다(subject.confirm_rows — 에이전트 서버 delib_subject.confirm 과 같은 규칙).
    확인하지 못하면 허브를 부르지 않는다.
  · 부르기 — 정본 허브(어휘표 canonical)의 object_resolve(type_slug=facts.focus, name=key) → exact 이고 그 객체의 key 가 닻과 글자 그대로 같을 때만
    graph_neighbors(depth 1 · 어휘표 types 의 값에서 focus 를 뺀 타입 · facts.limit). candidates · none 은 그대로 보이고 아무것도 고르지 않는다 —
    포털이 대신 고르지 않는다(HA-30 · 규칙 ①). exact 가 다른 key(별칭 · 이름으로 맞은 다른 객체)를 가리켜도 고르지 않는다. 두 이름은 허브 가족이라 늘
    접두(<정본 키>_<도구>)다 — 박스마다 같다.
  · 읽기 확인 — 두 이름이 이 박스 게이트웨이 /tools-map 에서 정본 백엔드의 것이고 routine_read(게이트웨이가 읽기로 확인한 것)에 있어야 부른다. 아니면
    부르지 않고 까닭을 말한다(object_resolve 는 박스 읽기 목록이 먼저다 — 게이트웨이 read_tools.local.json, PLAN M-R).
  · 행 — 닻과 바로 이어진 이웃을 줄마다 '타입 · key · 이름 · 관계(방향)' 로 줄여 facts.chars 안에(넘치면 '전체 N 중 M'). 어휘표 타입이 아닌 노드
    (판정 · 기록 · 인사이트)는 싣지 않는다. 사람이 고른 행만 근거가 된다 — 호출 하나에 근거 한 항목(화면 ontoEvidence.ts). 근거의 글과 지문은 포털이
    줄인 행이지 도구 원문이 아니다.
  · 리스크 심사에는 쓰지 않는다(D-18 — 같은 과제의 앞 판정에 닿는 길을 넓히지 않는다). 창구가 의장 risk-review* 를 422 로 거절한다.
  · 어휘표는 코어 어휘표(backend/config/core_vocab.json)와 박스 덧씌우기(core_vocab.local.json — JSON merge patch, 에이전트 서버 · 게이트웨이와 같은
    규칙)를 읽는다. facts 꼴이 틀리면 기본값으로 돌고 note 에 적는다.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from app.agent import subject as _subject

VOCAB_PATH = Path(__file__).resolve().parents[2] / "config" / "core_vocab.json"
VOCAB_LOCAL_PATH = VOCAB_PATH.with_name("core_vocab.local.json")
FACTS_DEFAULT = {"focus": "plm_task", "depth": 1, "limit": 60, "chars": 4000}
CALL_TIMEOUT_S = 30.0          # 호출마다 — 사람이 기다리는 자리다(주제 찾기와 같다)
_SLUG = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
_V: dict = {"key": None, "v": None}
NOTE = ("고른 행만 심의의 원천 근거로 들어가고, 그 과제 key · 이름은 결정문 · Report Archive 보고서의 근거에 남는다. 행은 포털이 줄인 글이다"
        "(도구 원문이 아니다 — 근거 표지의 지문도 이 글의 것이다).")


def risk_chair(chair_template) -> bool:
    """리스크 심사 계열 의장인가(에이전트 서버 delib_subject.risk_family 의 의장 쪽과 같다 — risk-review · risk-review-sealed)."""
    return str(chair_template or "").strip().lower().startswith("risk-review")


def _merge_patch(target, patch):
    """JSON merge patch(RFC 7386) — 에이전트 서버 · 게이트웨이와 같다(객체는 재귀로 합치고 그 밖은 바꾸며 null 은 지운다)."""
    if not isinstance(patch, dict):
        return patch
    out = dict(target) if isinstance(target, dict) else {}
    for k, v in patch.items():
        if v is None:
            out.pop(k, None)
        else:
            out[k] = _merge_patch(out.get(k), v)
    return out


def _mtime(p: Path):
    try:
        return p.stat().st_mtime_ns
    except OSError:
        return None


def _facts(raw, types: list) -> tuple[dict, str]:
    """facts 칸 → (쓸 값, 버렸으면 까닭). 꼴이 틀리면 기본값."""
    if raw is None:
        return dict(FACTS_DEFAULT), ""
    ok = (isinstance(raw, dict) and set(raw) <= set(FACTS_DEFAULT)
          and isinstance(raw.get("focus", "plm_task"), str) and raw.get("focus", "plm_task") in types
          and raw.get("depth", 1) == 1 and type(raw.get("depth", 1)) is int
          and type(raw.get("limit", 60)) is int and 1 <= raw.get("limit", 60) <= 200
          and type(raw.get("chars", 4000)) is int and 1000 <= raw.get("chars", 4000) <= 20000)
    if not ok:
        return dict(FACTS_DEFAULT), "어휘표 ontology.facts 의 꼴이 틀려 기본값(plm_task · depth 1 · 60 · 4,000자)으로 돈다"
    return {**FACTS_DEFAULT, **raw}, ""


def vocab() -> dict | None:
    """{canonical, label, facts, types, notes} — 코어 어휘표(덧씌우기 포함). 표를 못 읽으면 None. 바뀐 시각을 보고 다시 읽는다."""
    key = (_mtime(VOCAB_PATH), _mtime(VOCAB_LOCAL_PATH))
    if key == _V["key"]:
        return _V["v"]
    notes: list = []
    try:
        raw = json.loads(VOCAB_PATH.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("어휘표는 객체다")
    except (OSError, ValueError):
        _V.update(key=key, v=None)
        return None
    if key[1] is not None:
        try:
            patch = json.loads(VOCAB_LOCAL_PATH.read_text(encoding="utf-8"))
            if not isinstance(patch, dict):
                raise ValueError("덧씌우기는 객체다")
            raw = _merge_patch(raw, patch)
        except (OSError, ValueError) as exc:
            notes.append(f"박스 덧씌우기(core_vocab.local.json)를 버리고 기본 표로 돈다({type(exc).__name__})")
    can = raw.get("canonical") if isinstance(raw.get("canonical"), dict) else {}
    app = can.get("app") if isinstance(can.get("app"), str) and can.get("app") else None
    tmap = raw.get("types") if isinstance(raw.get("types"), dict) else {}
    types = list(dict.fromkeys(v for v in tmap.values() if isinstance(v, str) and _SLUG.fullmatch(v)))
    onto = raw.get("ontology") if isinstance(raw.get("ontology"), dict) else {}
    facts, why = _facts(onto.get("facts"), types)
    if why:
        notes.append(why)
    v = None if app is None else {"canonical": app, "label": str(can.get("label") or app), "facts": facts, "types": types, "notes": notes}
    _V.update(key=key, v=v)
    return v


def tool_names(canonical: str) -> tuple[str, str]:
    """정본 허브의 (풀이, 이웃) 노출 이름 — 허브 가족은 늘 접두다(게이트웨이 E2-3)."""
    pre = canonical.replace("-", "")
    return f"{pre}_object_resolve", f"{pre}_graph_neighbors"


def read_check(tools_map, canonical: str, names: tuple) -> str:
    """두 이름을 이 박스에서 부를 수 있나 — 비면 된다, 아니면 까닭. 게이트웨이가 읽기로 확인한 것(routine_read)만 부른다(닫힌 쪽)."""
    if not isinstance(tools_map, dict) or not isinstance(tools_map.get("map"), dict):
        return "게이트웨이 도구 지도(/tools-map)를 읽지 못했다 — 부르지 않는다"
    m = tools_map["map"]
    gone = [n for n in names if m.get(n) != canonical]
    if gone:
        return f"이 박스 게이트웨이에 정본 허브({canonical}) 도구가 없다 — {' · '.join(gone)}"
    rr = tools_map.get("routine_read")
    if not isinstance(rr, list):
        return "이 게이트웨이는 읽기로 확인한 도구 목록(routine_read)을 주지 않는다 — 읽기로 확인되지 않은 도구는 부르지 않는다"
    miss = [n for n in names if n not in rr]
    if miss:
        return (f"이 박스에서 읽기로 확인되지 않았다 — {' · '.join(miss)}. 게이트웨이 박스 읽기 목록(read_tools.local.json)에 "
                + " · ".join(f"{canonical}:{n.split('_', 1)[1]}" for n in miss) + " 를 더하면 열린다(docs/ontology-first M-R)")
    return ""


def _hit(h) -> dict | None:
    """SP ResolveHit → 화면 행(id · key · label · type · status · matched_by)."""
    if not isinstance(h, dict) or not isinstance(h.get("id"), str):
        return None
    return {"id": h["id"], "key": h.get("key") if isinstance(h.get("key"), str) else None, "label": str(h.get("label") or "")[:200],
            "type": str(h.get("type_slug") or "")[:40], "status": str(h.get("status") or "")[:40],
            "matched_by": str(h.get("matched_by") or "")[:20]}


def resolve_view(body) -> dict:
    """object_resolve 답(SP ResolveOut — match · object · candidates · hint · truncated) → {match, object?, candidates, hint}. 꼴이 아니면 match=''."""
    if not isinstance(body, dict) or body.get("match") not in ("exact", "candidates", "none"):
        return {"match": "", "candidates": [], "hint": ""}
    cands = [c for c in (_hit(x) for x in (body.get("candidates") or [])) if c][:20]
    return {"match": body["match"], "object": _hit(body.get("object")), "candidates": cands,
            "hint": str(body.get("hint") or "")[:300], "truncated": body.get("truncated") is True}


def neighbor_rows(body, focus_id: str, allowed: set, chars: int) -> dict:
    """graph_neighbors 답(SP NeighborhoodOut — nodes · edges · truncated) → {rows, total, shown, hub_truncated}. 닻과 바로 이어진 노드 가운데 어휘표 타입만,
    줄마다 '타입 · key · 이름 · 관계(방향)' 로 줄이고 chars 안에서 끊는다. 답이 그 꼴(nodes · edges 가 목록인 객체)이 아니면 ValueError — 부르는 쪽이
    '못 물어봄'(error)으로 말한다. 빈 행으로 돌려주면 '이웃이 없다' 로 읽히고, 그냥 두면 TypeError 가 500 이 됐다(반대 검토 11-02 — OF-26)."""
    if not isinstance(body, dict) or not isinstance(body.get("nodes"), list) or not isinstance(body.get("edges"), list):
        raise ValueError("graph_neighbors 답이 NeighborhoodOut 꼴(nodes · edges 목록)이 아니다")
    nodes = [n for n in body["nodes"] if isinstance(n, dict)]
    edges = [e for e in body["edges"] if isinstance(e, dict)]
    rel: dict = {}
    for e in edges:
        src, dst, slug = str(e.get("src") or ""), str(e.get("dst") or ""), str(e.get("relation") or "")[:60]
        if src == focus_id and dst != focus_id:
            rel.setdefault(dst, []).append(f"이 과제 → {str(e.get('label') or slug)[:60]}({slug})")
        elif dst == focus_id and src != focus_id:
            rel.setdefault(src, []).append(f"이 과제 ← {str(e.get('inverse_label') or e.get('label') or slug)[:60]}({slug})")
    rows = []
    for n in nodes:
        nid, typ = str(n.get("id") or ""), str(n.get("type_slug") or "")
        if not nid or nid == focus_id or typ not in allowed or nid not in rel:
            continue
        key = n.get("key") if isinstance(n.get("key"), str) and n.get("key") else None
        label, tlabel = str(n.get("label") or "")[:200], str(n.get("type_label") or typ)[:40]
        rows.append({"id": nid, "type": typ, "type_label": tlabel, "key": key, "label": label, "rel": " / ".join(rel[nid])[:300],
                     "line": f"{tlabel}({typ}) · {key or 'key 없음'} · {label} · {' / '.join(rel[nid])[:300]}"})
    total, used, shown = len(rows), 0, []
    for r in rows:
        if used + len(r["line"]) + 1 > chars and shown:
            break
        shown.append(r)
        used += len(r["line"]) + 1
    return {"rows": shown, "total": total, "shown": len(shown), "hub_truncated": body.get("truncated") is True}


def _err(exc) -> str:
    """호출 실패의 까닭 한 줄 — 게이트웨이 · 도구 거절(AuthError 의 message)은 그대로, 연결 · 기한 · 꼴 실패는 예외 이름과 함께."""
    msg = " ".join(str(getattr(exc, "message", None) or exc or "").split())[:300]
    return msg if hasattr(exc, "message") and msg else f"{type(exc).__name__}{': ' + msg if msg else ''}"


async def preview(key: str, *, tools_map, call) -> dict:
    """미리보기 한 번 — call(도구, 인자) 는 그 사람의 PAT 로 게이트웨이를 부르는 함수(창구가 준다). 답의 state —
    ok(이웃 행) · unavailable(부를 수 없다) · unconfirmed(닻을 확인 못 함) · candidates · none · mismatch(exact 가 다른 key) · error(호출 실패)."""
    v = vocab()
    if v is None:
        return {"state": "unavailable", "why": "코어 어휘표를 읽지 못했다 — 정본 허브를 모른다", "note": NOTE}
    res_tool, nb_tool = tool_names(v["canonical"])
    base = {"canonical": {"app": v["canonical"], "label": v["label"]}, "tools": {"resolve": res_tool, "neighbors": nb_tool},
            "sp_task": key, "note": NOTE, **({"notes": v["notes"]} if v["notes"] else {})}
    why = read_check(tools_map, v["canonical"], (res_tool, nb_tool))
    if why:
        return {**base, "state": "unavailable", "why": why}
    try:
        found = await call(_subject.RESOLVER_CALL, {"query": key, "limit": _subject.CONFIRM_LIMIT, "full": True})
    except Exception as exc:  # noqa: BLE001 — 확인 못 함은 허브를 부르지 않는 까닭이다
        return {**base, "state": "unconfirmed", "why": f"주제 과제를 확인하지 못했다(허브 과제 풀이 실패 — {_err(exc)})"}
    ok, why = _subject.confirm_rows(found, key)
    if not ok:
        return {**base, "state": "unconfirmed", "why": f"주제 과제를 확인하지 못했다 — {why}"}
    focus = v["facts"]["focus"]
    r_args = {"type_slug": focus, "name": key}
    try:
        rv = resolve_view(await call(res_tool, r_args))
    except Exception as exc:  # noqa: BLE001
        return {**base, "state": "error", "why": f"정본 허브 풀이({res_tool})를 부르지 못했다 — {_err(exc)}"}
    calls = {"resolve": {"tool": res_tool, "args": r_args}}
    if not rv["match"]:
        return {**base, "calls": calls, "state": "error", "why": f"정본 허브 풀이({res_tool})의 답 꼴을 읽지 못했다 — 아무것도 고르지 않는다"}
    if rv["match"] == "candidates":
        return {**base, "calls": calls, "state": "candidates", "candidates": rv["candidates"],
                "why": "정본 허브에서 여럿과 맞았다 — 고르지 않는다(어느 것인지 허브에서 확인한다)" + (f" · {rv['hint']}" if rv["hint"] else "")}
    if rv["match"] == "none" or not rv.get("object"):
        return {**base, "calls": calls, "state": "none", "why": "정본 허브에 그 과제가 없다 — 짐작하지 않는다" + (f" · {rv['hint']}" if rv["hint"] else "")}
    obj = rv["object"]
    if obj["key"] != key:
        return {**base, "calls": calls, "state": "mismatch", "candidates": [obj],
                "why": f"정본 허브의 exact 가 다른 key 를 가리킨다({obj['matched_by'] or '맞은 칸 모름'}로 맞음) — 주제와 같은 객체라고 볼 수 없어 고르지 않는다"}
    anchor = {**obj, "line": f"{focus} · {obj['key']} · {obj['label']} · 정본 허브 exact({obj['matched_by'] or '맞은 칸 모름'}) · 상태 {obj['status'] or '-'}"}
    ntypes = [t for t in v["types"] if t != focus]
    n_args = {"object_id": obj["id"], "depth": 1, "types": ntypes, "limit": v["facts"]["limit"]}
    calls["neighbors"] = {"tool": nb_tool, "args": n_args}
    try:
        nb = await call(nb_tool, n_args)
    except Exception as exc:  # noqa: BLE001
        return {**base, "calls": calls, "anchor": anchor, "state": "error", "rows": [],
                "why": f"정본 허브 이웃({nb_tool})을 부르지 못했다 — {_err(exc)}"}
    try:
        rows = neighbor_rows(nb, obj["id"], set(v["types"]), v["facts"]["chars"])
    except (TypeError, ValueError, AttributeError) as exc:
        return {**base, "calls": calls, "anchor": anchor, "state": "error", "rows": [],
                "why": f"정본 허브 이웃({nb_tool})의 답 꼴을 읽지 못했다 — 아무것도 고르지 않는다({_err(exc)})"}
    return {**base, "calls": calls, "anchor": anchor, "state": "ok", **rows}
