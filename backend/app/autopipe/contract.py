# 자동 파이프라인 계약(contract.md v1.1)의 답 꼴 검사 · 입력 지문 · idem_key — 꼴이 틀린 답은 성공으로 읽지 않는다
"""앱 답의 꼴을 여기 한 곳에서 본다. 엔진은 이 함수들이 None(틀림)을 돌려주면 그 단계를 실패 · 막힘으로 세운다.

- 상태 낱말은 다섯(queued · running · done · failed · cancelled), 판정은 넷(pass · fail · marginal · unknown) — 앱이 바꿔 싣는다(§0.3).
- `isError: false` 인데 `error` 칸이 있는 답은 실패다(§0.3 — 절차 PLAN 5-6 의 교훈). 그 판정은 gateway.Reply 가 한다.
- 결과 봉투는 run_ref · subject(과제 · 차수) · profile 이 낸 것과 맞아야 한다 — 다른 실행의 봉투를 이 단계의 성공으로 읽지 않는다.
- 막힘 낱말(`missing[].kind`)은 정해진 여섯(project_key · revision · input · human_input · infra · permission)이지만 모르는 낱말도 그대로 둔다.
"""
from __future__ import annotations

import hashlib
import json
import math

STATES = ("queued", "running", "done", "failed", "cancelled")
VERDICTS = ("pass", "fail", "marginal", "unknown")
MISSING_KINDS = ("project_key", "revision", "input", "human_input", "infra", "permission")
ENVELOPE_MAX = 1_000_000          # 결과 봉투 글자 상한 — 넘으면 원장에 두지 않고 꼴 틀림으로 본다
_TEXT = 2000                      # 짧은 글 칸 상한(이름 · 단위 · 까닭)


def _s(v, n: int = _TEXT, *, empty: bool = False) -> bool:
    return isinstance(v, str) and (empty or bool(v.strip())) and len(v) <= n


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def canon(v) -> str:
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha(v) -> str:
    return hashlib.sha256((v if isinstance(v, str) else canon(v)).encode("utf-8")).hexdigest()


# ── 입력 · 지문 ──────────────────────────────────────────────────────────────────────────────────────────────────────
def inputs_ok(v) -> list[dict] | None:
    """입력 목록 [{kind, ref, sha256?, at?}] — 틀리면 None."""
    if not isinstance(v, list):
        return None
    out = []
    for x in v:
        if not isinstance(x, dict) or not _s(x.get("kind"), 200) or not _s(x.get("ref"), 2000):
            return None
        if x.get("sha256") is not None and not _s(x.get("sha256"), 200):
            return None
        out.append({"kind": x["kind"], "ref": x["ref"], **({"sha256": x["sha256"]} if x.get("sha256") else {})})
    return out


def _input_key(x: dict) -> list:
    return [x.get("kind") or "", x.get("ref") or "", x.get("sha256") or ""]


def fingerprint(by_source: dict[str, list[dict]]) -> str:
    """주제의 입력 지문 — 원천마다 받은 입력을 (원천, 종류, ref, sha256)으로 정렬해 해시한다. 시각(at)은 넣지 않는다(같은 파일이 다시 와도 같은 지문)."""
    rows = sorted([src, *_input_key(x)] for src, xs in by_source.items() for x in xs)
    return sha(rows)


def step_fingerprint(run_fp: str, check_inputs: list[dict], upstream: dict[str, dict]) -> str:
    """단계의 입력 지문 — 주제 지문 + 이 단계 auto_check 가 준 입력 + 앞 해석 단계 결과의 inputs · artifacts(계약 v1.1 upstream).
    앞 단계가 같은 결과를 냈으면 같은 지문이라 앱이 idem_key 로 다시 내지 않는다."""
    up = {sid: {"inputs": sorted(_input_key(x) for x in env.get("inputs") or []),
                "artifacts": sorted([a.get("kind") or "", a.get("location") or ""] for a in env.get("artifacts") or [])}
          for sid, env in sorted(upstream.items())}
    return sha({"run": run_fp, "inputs": sorted(_input_key(x) for x in check_inputs), "upstream": up})


def idem_key(project: str, revision: str, rule_id: str, version_no: int, step_fp: str, step_id: str) -> str:
    """(과제, 차수, 규칙 판, 입력 지문, 단계 id)의 sha256 — 64자 소문자 16진수(계약 §2 auto_submit)."""
    return sha([project, revision, f"{rule_id}@{version_no}", step_fp, step_id])


# ── 원천 — auto_changes ─────────────────────────────────────────────────────────────────────────────────────────────
def subject_ok(v) -> dict | None:
    """subject {project: str|null, revision: str|null, refs: {앱: id}} — project · revision 은 짐작하지 않는다(null 그대로)."""
    if not isinstance(v, dict):
        return None
    p, r, refs = v.get("project"), v.get("revision"), v.get("refs", {})
    if p is not None and not _s(p, 200):
        return None
    if r is not None and not _s(r, 40):
        return None
    if not isinstance(refs, dict) or not all(_s(k, 80) and isinstance(x, (str, int)) and len(str(x)) <= 200 for k, x in refs.items()):
        return None
    return {"project": p, "revision": r, "refs": {k: str(x) for k, x in refs.items()}}


def changes_ok(v) -> dict | None:
    """auto_changes 답 — {items[], next_since, complete}. 항목 하나라도 꼴이 틀리면 답 전체를 버린다(커서를 나아가지 않는다)."""
    if not isinstance(v, dict) or not isinstance(v.get("items"), list) or not isinstance(v.get("complete"), bool):
        return None
    nxt = v.get("next_since")
    if nxt is not None and not _s(nxt, 2000):
        return None
    items = []
    for it in v["items"]:
        if not isinstance(it, dict):
            return None
        subj = subject_ok(it.get("subject"))
        inputs = inputs_ok(it.get("inputs", []))
        ready = it.get("ready", {})
        upd = it.get("updated_at")
        if subj is None or inputs is None or not isinstance(ready, dict) or not all(_s(k, 40) for k in ready):
            return None
        if upd is not None and not _s(upd, 40):
            return None
        items.append({"subject": subj, "inputs": inputs, "ready": {k: bool(x) for k, x in ready.items()}, "updated_at": upd})
    return {"items": items, "next_since": nxt, "complete": v["complete"]}


# ── 해석 — 다섯 ─────────────────────────────────────────────────────────────────────────────────────────────────────
def profiles_ok(v) -> dict | None:
    """auto_profiles 답 — {app_version, service_identity, profiles: [{id, title, inputs, cost, sync, …}]}."""
    if not isinstance(v, dict) or not isinstance(v.get("profiles"), list):
        return None
    if not isinstance(v.get("service_identity", True), bool):
        return None
    out = {}
    for p in v["profiles"]:
        if not isinstance(p, dict) or not _s(p.get("id"), 64):
            return None
        cost = p.get("cost") if isinstance(p.get("cost"), dict) else {}
        out[p["id"]] = {"id": p["id"], "title": str(p.get("title") or p["id"])[:200], "sync": p.get("sync") is True,
                        "cost": {k: cost[k] for k in ("cores", "minutes", "cluster") if k in cost and (_num(cost[k]) or _s(cost[k], 80))},
                        "criteria_source": str(p.get("criteria_source") or "")[:300]}
    return {"app_version": str(v.get("app_version") or "")[:80], "service_identity": v.get("service_identity", True), "profiles": out}


def check_ok(v) -> dict | None:
    """auto_check 답 — {ready, missing[{kind, name?, why?}], inputs[]}. 모르는 막힘 낱말도 그대로 둔다(계약 v1.1 — 실패시키지 않는다)."""
    if not isinstance(v, dict) or not isinstance(v.get("ready"), bool):
        return None
    missing = v.get("missing", [])
    if not isinstance(missing, list):
        return None
    ms = []
    for m in missing:
        if not isinstance(m, dict) or not _s(m.get("kind"), 80):
            return None
        ms.append({"kind": m["kind"], **{k: str(m[k])[:500] for k in ("name", "why") if m.get(k) is not None}})
    inputs = inputs_ok(v.get("inputs", []))
    if inputs is None:
        return None
    return {"ready": v["ready"], "missing": ms, "inputs": inputs}


def missing_reason(missing: list[dict]) -> str:
    """막힘 까닭 한 줄 — 'missing:human_input(pkg_type),infra'. 낱말은 앱이 준 그대로다."""
    if not missing:
        return "missing:(앱이 까닭을 주지 않았다)"
    return "missing:" + ",".join(m["kind"] + (f"({m['name']})" if m.get("name") else "") for m in missing)[:400]


def submit_ok(v) -> dict | None:
    """auto_submit 답 — {run_ref, state, created?}."""
    if not isinstance(v, dict) or not _s(v.get("run_ref"), 200) or v.get("state") not in STATES:
        return None
    if v.get("created") is not None and not isinstance(v.get("created"), bool):
        return None
    return {"run_ref": v["run_ref"], "state": v["state"], "created": v.get("created")}


def status_ok(v) -> dict | None:
    """auto_status 답 — {state(다섯), progress?, detail?, updated_at?}."""
    if not isinstance(v, dict) or v.get("state") not in STATES:
        return None
    prog = v.get("progress")
    if prog is not None and not (_num(prog) and 0 <= prog <= 1):
        return None
    det = v.get("detail")
    if det is not None and not isinstance(det, str):
        return None
    return {"state": v["state"], **({"progress": prog} if prog is not None else {}), **({"detail": det[:500]} if det else {})}


def _metric(m) -> dict | None:
    if not isinstance(m, dict) or not _s(m.get("name"), 120) or not _s(m.get("unit"), 40) or not _num(m.get("value")):
        return None
    out = {"name": m["name"], "unit": m["unit"], "value": m["value"]}
    if m.get("label") is not None:
        if not _s(m["label"], 200, empty=True):
            return None
        out["label"] = m["label"]
    if m.get("limit") is not None:
        if not _num(m["limit"]):
            return None
        out["limit"] = m["limit"]
    if m.get("limit_source") is not None:
        if not _s(m["limit_source"], 300, empty=True):
            return None
        out["limit_source"] = m["limit_source"]
    if m.get("verdict") is not None:
        if m["verdict"] not in VERDICTS:
            return None
        out["verdict"] = m["verdict"]
    return out


def envelope_ok(v, *, run_ref: str, project: str, revision: str, profile: str) -> tuple[dict | None, str]:
    """auto_result 결과 봉투 — (정리한 봉투, '') 또는 (None, 까닭). 낸 것과 다른 실행 · 과제 · 차수 · profile 의 봉투는 받지 않는다."""
    if not isinstance(v, dict):
        return None, "객체가 아니다"
    if len(canon(v)) > ENVELOPE_MAX:
        return None, f"봉투가 {ENVELOPE_MAX}자를 넘는다"
    if v.get("run_ref") != run_ref:
        return None, "run_ref 가 낸 실행과 다르다"
    subj = subject_ok(v.get("subject"))
    if subj is None or subj["project"] != project or subj["revision"] != revision:
        return None, "subject 의 과제 · 차수가 낸 것과 다르다"
    if v.get("profile") != profile:
        return None, "profile 이 낸 것과 다르다"
    if not _s(v.get("app_version"), 80):
        return None, "app_version 이 없다"
    if v.get("verdict") not in VERDICTS:
        return None, f"verdict 는 {' · '.join(VERDICTS)} 가운데 하나다"
    if not isinstance(v.get("metrics"), list):
        return None, "metrics 가 목록이 아니다"
    metrics = []
    for m in v["metrics"]:
        got = _metric(m)
        if got is None:
            return None, "metrics 의 칸이 틀렸다(name · unit · 숫자 value 는 꼭)"
        metrics.append(got)
    figs = v.get("figures", [])
    if not isinstance(figs, list) or not all(isinstance(f, dict) and _s(f.get("ref"), 2000) and
                                             (f.get("caption") is None or isinstance(f.get("caption"), str)) for f in figs):
        return None, "figures 는 [{ref, caption?}] 다"
    arts = v.get("artifacts", [])
    if not isinstance(arts, list) or not all(isinstance(a, dict) and _s(a.get("kind"), 80) and _s(a.get("location"), 2000) for a in arts):
        return None, "artifacts 는 [{kind, location}] 다"
    inputs = inputs_ok(v.get("inputs", []))
    if inputs is None:
        return None, "inputs 의 꼴이 틀렸다"
    notes = v.get("notes", [])
    if not isinstance(notes, list) or not all(isinstance(n, str) for n in notes):
        return None, "notes 는 글의 목록이다"
    if not metrics and not any(n.strip() for n in notes):
        return None, "빈 결과인데 notes 에 사유가 없다"
    return {"run_ref": run_ref, "subject": subj, "profile": profile, "app_version": v["app_version"], "verdict": v["verdict"],
            "metrics": metrics, "figures": [{"ref": f["ref"], "caption": str(f.get("caption") or "")[:300]} for f in figs],
            "artifacts": [{"kind": a["kind"], "location": a["location"]} for a in arts], "inputs": inputs,
            "notes": [n[:2000] for n in notes], "finished_at": str(v.get("finished_at") or "")[:40]}, ""
