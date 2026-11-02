# 심의 주제의 포털 몫 — 허브 과제 찾기 행의 꼴과, 에이전트 서버가 확인해 낸 주제를 대화 meta 에 옮기는 꼴(과제 인사이트 그래프 M1)
"""docs/project-insight-graph PLAN §4.1 · §4.3 · §9 M1.

포털은 과제 목록을 쥐지 않는다(사용자 결정 A13 (A)). 고르기 화면의 후보는 그 사람의 도구 결과에서만 온다 — 대화에서 부른 도구의 결과(화면이
읽는다) 아니면 이 모듈의 찾기(그 사람의 PAT 로 게이트웨이 풀이 도구를 부른다). 브라우저가 보낸 주제는 믿지 않는다 — 에이전트 서버가 같은
풀이로 다시 확인하고(HWAXAgentServer delib_subject.confirm) 그 결과를 SSE delib 사건(kind=subject)으로 낸다. 중계는 그 사건만 답 meta.subject
로 남긴다(subject_of) — 사람 발화는 스트림 전에 남아 확인한 값을 아직 모른다(그림 주소 user_images 와 같은 까닭).
"""
from __future__ import annotations

# 풀이 도구 — 게이트웨이의 호출 전용 별칭(<백엔드 키에서 하이픈 뺀 것>_<도구>, 겹침 · 접두와 무관하게 늘 선다). 에이전트 서버
# delib_subject.RESOLVER_CALL 과 같은 이름이어야 한다 — 고르기 화면의 후보와 서버의 확인이 같은 풀이에서 온다(tests/test_subject_m1.py 가 견준다).
RESOLVER_CALL = "heaxstep_forge_find_plm_task"
SEARCH_LIMIT = 20
_ROW_TEXT_MAX = 200
_STATES = ("confirmed", "claimed", "none")
_ART_KINDS = ("mcad", "ecad", "cae")


def _s(v, cap: int = _ROW_TEXT_MAX) -> str | None:
    return v[:cap] if isinstance(v, str) and v else None


def sp_rows(body: dict) -> dict:
    """find_plm_task 답(StepForge core/sp_core.py find_tasks 꼴 — {query, count, tasks[{key, label, active, project{label}, properties{task_code}}],
    why?}) → 고르기 화면의 행. key 는 결과 행의 key 칸 그대로다(과제코드 · 과제명으로 바꾸지 않는다). 0건이면 까닭(why)을 그대로 옮긴다."""
    rows = []
    for t in body.get("tasks") or []:
        if not isinstance(t, dict) or not isinstance(t.get("key"), str) or not t["key"]:
            continue
        props = t.get("properties") if isinstance(t.get("properties"), dict) else {}
        proj = t.get("project") if isinstance(t.get("project"), dict) else {}
        code = props.get("task_code")
        rows.append({"key": t["key"], "label": _s(t.get("label")), "task_code": _s(code if isinstance(code, str) else None, 80),
                     "project": _s(proj.get("label")), "active": t.get("active") is not False})
    why = body.get("why") if isinstance(body.get("why"), dict) else None
    count = body.get("count")
    return {"rows": rows, "count": count if isinstance(count, int) else len(rows),
            **({"why": {"cause": _s(why.get("cause"), 40), "message": _s(why.get("message"), 400)}} if why else {})}


def subject_of(raw) -> dict | None:
    """에이전트 서버 delib 사건(kind=subject)의 subject → 답 meta 에 남길 꼴. 알려진 칸만 · 길이 상한 안에서 옮긴다(에이전트가 낸 값이지만 대화
    저장소에 들어가는 자리라 꼴을 다시 본다). 꼴이 아니면 None — 남기지 않는다."""
    if not isinstance(raw, dict) or raw.get("sp_state") not in _STATES:
        return None
    by = raw.get("sp_resolved_by")
    arts = []
    for a in raw.get("artifacts") or []:
        if isinstance(a, dict) and a.get("kind") in _ART_KINDS and isinstance(a.get("id"), str):
            arts.append({k: a[k][:120] for k in ("kind", "app", "id", "rev") if isinstance(a.get(k), str) and a[k]})
    out = {"sp_task": _s(raw.get("sp_task")), "sp_state": raw["sp_state"],
           "sp_resolved_by": ({k: by[k] for k in ("tool", "app", "at", "sha256") if isinstance(by.get(k), (str, int, float))}
                              if isinstance(by, dict) else None),
           "round": _s(raw.get("round"), 8), "round_by": _s(raw.get("round_by"), 40), "text": _s(raw.get("text"), 600) or "",
           "artifacts": arts[:8]}
    if isinstance(raw.get("sp_why"), str) and raw["sp_why"]:
        out["sp_why"] = raw["sp_why"][:400]
    return out
