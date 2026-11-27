# 자동 파이프라인 보고서 — 결과 봉투에서 코드가 쓴다(per_analysis · summary · revdiff, 서술 LLM 은 M5 — portal-api §5)
"""수치 · 판정 · 그림은 봉투 그대로 옮기고 정해진 문장만 붙인다. 실패 · 건너뜀 · 막힘은 숨기지 않는다.

머리 — 「자동 — 규칙 <title> v<판> · 입력 지문 · 앱 판」, 켠 사람(연락처 — 서명이 아니다, PLAN §4.6), 대체된 실행이면 「대체됨 — 차수 <새 차수> 가 뒤에 왔다」.
RA 블록은 심의 형식과 같은 네 칸(background · results · recommendation · minutes)이고 나눔은 분석 루틴의 ra_blocks(항목 2,000자) 그대로다 —
그래서 등록 형식(infra/ra/formats/auto-pipeline.json)과 심의 형식 어느 쪽에도 실린다.
"""
from __future__ import annotations

from app.procedures.routines import ra_blocks

LABELS = {"per_analysis": "해석별 보고서", "summary": "종합 보고서", "revdiff": "이전 차수 대비"}
STATE_KO = {"pending": "대기", "ready": "준비", "blocked": "막힘", "queued": "줄 섬", "running": "도는 중", "done": "끝",
            "failed": "실패", "cancelled": "취소", "skipped": "건너뜀"}
VERDICT_KO = {"pass": "합", "fail": "부", "marginal": "경계", "unknown": "모름"}
TITLE_MAX = 255


def _fmt(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, (int, float)):
        return f"{v:.6g}"
    return str(v)


def _cell(s) -> str:
    return str(s).replace("|", "\\|").replace("\n", " ")


def _verdict(v) -> str:
    return f"{VERDICT_KO.get(v, v)}({v})" if v else "—"


def head(*, kind: str, rule_title: str, version_no: int, run: dict, steps: list[dict], enabled_by: str | None,
         superseded_rev: str | None) -> tuple[str, list[str]]:
    """(제목, 머리 줄들)."""
    vers = sorted({(s.get("result") or {}).get("app_version") for s in steps if (s.get("result") or {}).get("app_version")})
    title = f"[자동] {rule_title} — {run['project']} {run['revision']} · {LABELS.get(kind, kind)}"[:TITLE_MAX]
    lines = [f"자동 — 규칙 「{rule_title}」 v{version_no} · 과제 {run['project']} · 차수 {run['revision']} · 실행 {run['id'][:8]}"
             f" · 입력 지문 {run['fingerprint'][:12]} · 앱 판 {', '.join(vers) or '—'}"]
    if enabled_by:
        lines.append(f"규칙을 켠 사람 {enabled_by}(연락처 — 서명이 아니다)")
    if superseded_rev:
        lines.append(f"⚠ 대체됨 — 차수 {superseded_rev} 가 뒤에 왔다(이 보고서는 그 전에 끝난 결과다)")
    return title, lines


def _metrics_rows(env: dict) -> list[str]:
    rows = ["| 이름 | 값 | 단위 | 기준 | 기준 출처 | 판정 |", "|---|---|---|---|---|---|"]
    for m in env.get("metrics") or []:
        rows.append(f"| {_cell(m.get('label') or m['name'])} | {_fmt(m['value'])} | {_cell(m['unit'])} | {_fmt(m.get('limit'))}"
                    f" | {_cell(m.get('limit_source') or '—')} | {_verdict(m.get('verdict'))} |")
    return rows


def _not_done(step: dict) -> str:
    why = step.get("error") or ""
    return f"_(이 해석은 {STATE_KO.get(step['state'], step['state'])}" + (f" — {why}" if why else "") + ")_"


def analysis_md(step: dict, spec_step: dict) -> list[str]:
    """해석 하나의 자세한 절(per_analysis)."""
    out = [f"## {step['step_id']} — {spec_step.get('app')} · profile {spec_step.get('profile')}", ""]
    env = step.get("result")
    if step["state"] != "done" or not env:
        return out + [_not_done(step), ""]
    out += [f"**판정** {_verdict(env['verdict'])} · 앱 판 {env.get('app_version') or '—'}", ""]
    if env.get("metrics"):
        out += _metrics_rows(env) + [""]
    else:
        out += ["_(수치 없음)_", ""]
    for f in env.get("figures") or []:
        out.append(f"- 그림 `{f['ref']}`" + (f" — {f['caption']}" if f.get("caption") else ""))
    for a in env.get("artifacts") or []:
        out.append(f"- 원자료 {a['kind']} — `{a['location']}`")
    for n in env.get("notes") or []:
        out.append(f"- 메모 — {n}")
    return out + [""]


def _summary_line(step: dict) -> str:
    env = step.get("result") or {}
    if step["state"] == "done" and env:
        return f"{step['step_id']}: {_verdict(env.get('verdict'))} — 수치 {len(env.get('metrics') or [])}개"
    return f"{step['step_id']}: {STATE_KO.get(step['state'], step['state'])}" + (f" — {step['error']}" if step.get("error") else "")


def _diff(prev_env: dict | None, env: dict | None) -> list[str]:
    """두 봉투의 판정 · 수치를 이름으로 맞댄 줄들."""
    if not env:
        return ["_(이번 차수의 결과가 없다)_"]
    if not prev_env:
        return ["_(앞 차수에 이 해석의 결과가 없다)_"]
    out = [f"판정 {_verdict(prev_env.get('verdict'))} → {_verdict(env.get('verdict'))}"
           + (" (바뀜)" if prev_env.get("verdict") != env.get("verdict") else ""), "",
           "| 이름 | 앞 차수 | 이번 | 단위 | 변화 | 판정 |", "|---|---|---|---|---|---|"]
    before = {m["name"]: m for m in prev_env.get("metrics") or []}
    now = {m["name"]: m for m in env.get("metrics") or []}
    for name in list(now) + [n for n in before if n not in now]:
        a, b = before.get(name), now.get(name)
        if a and b:
            if a["unit"] != b["unit"]:
                change = f"단위가 다르다({a['unit']} → {b['unit']}) — 맞대지 않는다"
            else:
                d = b["value"] - a["value"]
                change = f"{d:+.6g}" + (f" ({d / a['value'] * 100:+.1f}%)" if a["value"] else "")
            verdict = f"{_verdict(a.get('verdict'))} → {_verdict(b.get('verdict'))}"
            out.append(f"| {_cell(b.get('label') or name)} | {_fmt(a['value'])} | {_fmt(b['value'])} | {_cell(b['unit'])} | {change} | {verdict} |")
        elif b:
            out.append(f"| {_cell(b.get('label') or name)} | — | {_fmt(b['value'])} | {_cell(b['unit'])} | 새로 생김 | {_verdict(b.get('verdict'))} |")
        else:
            out.append(f"| {_cell(a.get('label') or name)} | {_fmt(a['value'])} | — | {_cell(a['unit'])} | 없어짐 | — |")
    return out


def render(*, kind: str, rule_title: str, version_no: int, run: dict, steps: list[dict], spec: dict, needs: list[str],
           enabled_by: str | None = None, superseded_rev: str | None = None,
           prev: tuple[dict, list[dict]] | None = None) -> dict:
    """{title, md, blocks, tags}. steps 는 이 실행의 단계 전부(원장 꼴), needs 는 이 보고서 단계가 가리키는 해석 단계 id."""
    by = {s["step_id"]: s for s in steps}
    spec_by = {s["id"]: s for s in spec.get("steps") or []}
    mine = [by[n] for n in needs if n in by]
    title, lines = head(kind=kind, rule_title=rule_title, version_no=version_no, run=run, steps=mine, enabled_by=enabled_by,
                        superseded_rev=superseded_rev)
    md = [f"# {title}", ""] + [f"> {ln}" for ln in lines] + [""]
    results: list[str] = []
    verdicts = [_summary_line(s) for s in mine]
    if kind == "per_analysis":
        for s in mine:
            sec = analysis_md(s, spec_by.get(s["step_id"], {}))
            md += sec
            results.append("\n".join(x for x in sec if x))
    elif kind == "summary":
        md += ["## 해석마다", ""] + [f"- {v}" for v in verdicts] + [""]
        table = ["| 해석 | 이름 | 값 | 단위 | 기준 | 판정 |", "|---|---|---|---|---|---|"]
        for s in mine:
            done_metrics = ((s.get("result") or {}).get("metrics") or []) if s["state"] == "done" else []
            for m in done_metrics:
                table.append(f"| {s['step_id']} | {_cell(m.get('label') or m['name'])} | {_fmt(m['value'])} | {_cell(m['unit'])}"
                             f" | {_fmt(m.get('limit'))} | {_verdict(m.get('verdict'))} |")
        md += ["## 수치", ""] + (table if len(table) > 2 else ["_(수치 없음)_"]) + [""]
        bad = [s for s in mine if s["state"] != "done"]
        if bad:
            md += ["## 끝나지 않은 해석(숨기지 않는다)", ""] + [f"- {_summary_line(s)}" for s in bad] + [""]
        results.append("\n".join(table) if len(table) > 2 else "수치 없음")
    elif kind == "revdiff":
        if prev is None:
            md += ["## 첫 차수", "", "같은 규칙 · 같은 과제에 맞댈 앞 차수 실행(끝남 · 일부 끝남)이 없다.", ""]
            results.append("첫 차수 — 맞댈 앞 차수 실행이 없다")
        else:
            prun, psteps = prev
            pby = {s["step_id"]: s for s in psteps}
            md += [f"앞 차수 — {prun['revision']}(실행 {prun['id'][:8]} · 입력 지문 {prun['fingerprint'][:12]})", ""]
            for s in mine:
                ps = pby.get(s["step_id"])
                penv = (ps or {}).get("result") if (ps or {}).get("state") == "done" else None
                env = s.get("result") if s["state"] == "done" else None
                sec = [f"## {s['step_id']}", ""] + _diff(penv, env) + [""]
                md += sec
                results.append("\n".join(x for x in sec if x))
    appendix = [f"- {s['step_id']} · {STATE_KO.get(s['state'], s['state'])} · run_ref {s.get('run_ref') or '—'} · idem {str(s.get('idem_key') or '—')[:12]}"
                + (f" · {s['error']}" if s.get("error") else "") for s in mine]
    md += ["## 근거 부록", ""] + (appendix or ["_(해석 단계 없음)_"])
    blocks = {"background": ["\n".join(lines)], "results": [r for r in results if r],
              "recommendation": ["\n".join(verdicts)] if verdicts else [], "minutes": ["\n".join(appendix)] if appendix else []}
    return {"title": title, "md": "\n".join(md), "blocks": ra_blocks(blocks),
            "tags": ["자동 파이프라인", rule_title[:40], str(run["project"])[:40], str(run["revision"])[:40]]}
