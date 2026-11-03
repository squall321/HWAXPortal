#!/usr/bin/env python3
# CAD 위치 가시화 · 분석이 실제 데이터로 끝까지 되는지 cae00 에서 사람이 보는 점검(리스크 항목 → 위치 → 짝 단면 · 묶음 · 접힘 · 적층 → 그림 받기 → 보고서, docs/report-figures RF-31)
"""리스크 항목 하나를 골라 F2 → F1 · F3 · F6 → 그림 보관 → (고르면) 보고서까지 한 번에 본다.

  list   — 이 사람이 볼 수 있는 리스크 과제와 StepForge 과제(파트 수 · 단계)를 화면에만 찍는다(이름이 든다 — 답에 옮기지 않는다).
  run    — 고른 항목으로 차례대로 부른다.
           1) risk_locate_for_section — 위치를 못 정하면 까닭 · 고칠 곳(fix)을 찍고 멈춘다(변환 등록은 사람이 — 아래 참고).
           2) 평면마다 f1.calls 줄에 견줄 판(--compare)을 더해 section_pair_view(--fold 를 주면 접힌 상태로).
           3) 같은 줄들을 section_batch 로 → section_batch_result 로 줄마다 그림.
           4) --stackup-other 를 주면 stackup_figure(바로 길 — 예산에서 멈추면 잡을 기다려 job_id 로, 줄이 많아 쪽이 나뉘면 끝 쪽까지).
           5) 받은 그림마다 figure_get 의 주소로 받아 크기 · sha256 을 맞댄다(개인 Claude 가 PC 로 받는 길과 같다).
           6) --ra-report · --mxwp-doc 을 주었을 때만 figure_to_report · figure_to_doc(쓰기 — 그 보고서 · 문서에 그림이 들어간다).

읽기가 기본이다 — 부르는 도구는 READ_TOOLS 뿐이고, WRITE_TOOLS 둘은 그 인자를 줄 때만 열린다. section_batch · 적층 측정 잡은 StepForge 의 잡 행만 쓴다
(CAD · DB 의 다른 자리는 안 쓴다). 요약(summary.txt)은 상태 · 수 · 초만 — 과제 · 파트 이름은 report.json 과 받은 그림 폴더에만 둔다(infra/.state — 추적 밖).

쓰는 법(cae00 — 리포 루트에서, 게이트웨이와 같은 파이썬)
  export HWAX_GATEWAY_PAT='<포털 /auth/pat 로 발급한 PAT>'          # 그 사람의 권한 · 이름으로 부른다
  PY=../HWAXAgentServer/.venv/bin/python
  $PY infra/scripts/cad-figure-check.py list
  $PY infra/scripts/cad-figure-check.py run --project <리스크 과제 id> --refdes U1001 --compare <다른 판 StepForge 과제 id>
  $PY infra/scripts/cad-figure-check.py run --project <id> --finding <finding id> --compare <id> --fold '{"axis_point":[..],"axis_dir":[0,1,0],"angle_deg":180,"moving":["*COVER*"]}'
  $PY infra/scripts/cad-figure-check.py run ... --stackup-other <다른 보드 StepForge 과제 id> --axis-a z --axis-b z
  $PY infra/scripts/cad-figure-check.py run ... --ra-report <보고서 id> --mxwp-doc <slug> --mxwp-section <절 id>   # 쓰기 — 시험용 보고서 · 문서로

끝 코드 — 0 고른 걸음이 다 됨 · 2 준비 실패(PAT · mcp 모듈 · 도구 없음 · 인자) · 3 걸음 가운데 안 된 것이 있다(요약의 ✗ 줄).
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Awaitable, Callable

ROOT = Path(__file__).resolve().parents[2]
RISK, SF, GW = "heax-hwax_risk", "heax-step_forge", "_gateway"
READ_TOOLS = frozenset({(RISK, "risk_list_projects"), (RISK, "risk_locate_for_section"), (SF, "list_projects"), (SF, "section_pair_view"),
                        (SF, "section_batch"), (SF, "section_batch_result"), (SF, "stackup_figure"), (GW, "figure_get")})
WRITE_TOOLS = frozenset({(GW, "figure_to_report"), (GW, "figure_to_doc")})
_FIG_REF = re.compile(r"그림 저장 — (fig_[A-Za-z0-9_-]+)")
POLL_BATCH_S, POLL_STACKUP_S = 5.0, 15.0     # 잡 결과를 다시 묻는 사이(초) — 적층 측정은 길어 드물게
_EXT = {"image/png": "png", "image/jpeg": "jpg", "image/svg+xml": "svg", "image/gif": "gif", "image/webp": "webp"}


# ── 부르기 ───────────────────────────────────────────────────────────────
class Caller:
    """원래 이름으로 부른다. 드러난 이름은 /tools-map 의 map · orig 로 찾고(게이트웨이 자체 도구는 맨 이름), 읽기 목록 밖은 부르기 전에 거절한다 —
    쓰기 둘은 `allow_writes` 에 든 것만."""

    def __init__(self, call: Callable[[str, dict], Awaitable[Any]], exposed: dict[tuple[str, str], str], allow_writes: set[tuple[str, str]] = frozenset()):
        self._call, self.exposed, self.allow_writes = call, exposed, set(allow_writes)
        self.calls: dict[str, int] = {}

    async def __call__(self, app: str, original: str, args: dict) -> Any:
        key = (app, original)
        if key not in READ_TOOLS and not (key in WRITE_TOOLS and key in self.allow_writes):
            raise PermissionError(f"부르지 않는 도구 — {app}:{original}(쓰기는 그 인자를 줄 때만)")
        name = self.exposed.get(key) or (original if app == GW else None)
        if not name:
            raise LookupError(f"이 게이트웨이에 {app}:{original} 가 없다")
        self.calls[original] = self.calls.get(original, 0) + 1
        return await self._call(name, args)


def exposed_names(tools_map: dict) -> dict[tuple[str, str], str]:
    m, orig = tools_map.get("map") or {}, tools_map.get("orig") or {}
    out: dict[tuple[str, str], str] = {}
    for exposed, app in m.items():
        out.setdefault((app, orig.get(exposed, exposed)), exposed)
    return out


class Reply:
    """도구 답 하나 — 글 덩어리(JSON 이면 읽은 것) · 그림 수 · 오류 · 게이트웨이 그림 보관 표지의 ref."""

    def __init__(self, raw: Any):
        self.texts = [getattr(c, "text", "") for c in getattr(raw, "content", []) if getattr(c, "type", "") == "text"]
        self.images = sum(1 for c in getattr(raw, "content", []) if getattr(c, "type", "") == "image")
        self.error = bool(getattr(raw, "isError", False))
        self.data: Any = None
        for t in self.texts:
            if t.lstrip().startswith(("{", "[")):
                try:
                    self.data = json.loads(t)
                    break
                except ValueError:
                    continue
        self.fig_refs = [m.group(1) for t in self.texts for m in _FIG_REF.finditer(t)]

    @property
    def head(self) -> str:
        return (self.texts[0] if self.texts else "")[:300].replace("\n", " ")


# ── 걸음 ─────────────────────────────────────────────────────────────────
def locate_args(a: argparse.Namespace) -> dict:
    args: dict[str, Any] = {"project_id": a.project}
    for k in ("finding", "refdes", "net", "target_key", "cluster_key", "side", "odb_job", "stepforge"):
        v = getattr(a, k, None)
        if v:
            args[{"finding": "finding_id", "odb_job": "odb_job_id", "stepforge": "stepforge_project_id"}.get(k, k)] = v
    if a.x is not None and a.y is not None:
        args["x"], args["y"] = a.x, a.y
    return args


def pair_rows(calls: list[dict], compare: list[str], fold: dict | None) -> list[dict]:
    """f1.calls 줄마다 견줄 판을 더한 짝 단면 인자 — 그림은 jpg(256 KB 안에 맞추기 쉽다), fold 를 주면 함께."""
    rows = []
    for c in calls:
        row = {**c, "projects": list(dict.fromkeys(list(c.get("projects") or []) + compare)), "format": "jpg"}
        if fold:
            row["fold"] = fold
        rows.append(row)
    return rows


def view_summary(rep: Reply) -> dict:
    d = rep.data if isinstance(rep.data, dict) else {}
    panels = d.get("panels") or []
    return {"ok": not rep.error and rep.images > 0, "error": rep.head if rep.error else None, "images": rep.images, "fig_refs": rep.fig_refs,
            "rows_total": d.get("rows_total"), "unmatched_highlight": len((d.get("highlight") or {}).get("unmatched") or []),
            "body_missing": sum(1 for p in panels if p.get("body_missing")), "not_drawn": sum(int(p.get("not_drawn_count") or 0) for p in panels),
            "fold_moved": [p.get("fold_moved") for p in panels] if any("fold_moved" in p for p in panels) else None}


async def wait_ready(fetch: Callable[[], Awaitable[Reply]], deadline_s: float, poll_s: float = 5.0) -> tuple[Reply | None, float]:
    """잡 결과를 그림이 나오거나(또는 오류) 기한까지 기다린다 — ready: false 면 다시."""
    t0 = time.time()
    last = None
    while time.time() - t0 < deadline_s:
        last = await fetch()
        d = last.data if isinstance(last.data, dict) else {}
        if last.error or last.images or d.get("ready") is True or (d.get("ready") is None and not d.get("job")):
            return last, time.time() - t0
        await asyncio.sleep(poll_s)
    return last, time.time() - t0


def fetch_figure(meta: dict, out_dir: Path, opener: Callable[..., Any] = urllib.request.urlopen) -> dict:
    """figure_get 이 준 주소로 받아 크기 · sha256 을 맞댄다 — 주소가 없으면 그 까닭(note)."""
    url = meta.get("url")
    if not url:
        return {"ok": False, "why": str(meta.get("note") or "주소 없음")[:200]}
    with opener(url, timeout=60) as r:
        body = r.read()
    ok = len(body) == int(meta.get("bytes") or -1) and hashlib.sha256(body).hexdigest() == meta.get("sha256")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{meta.get('tool') or 'figure'}-{meta.get('ref')}.{_EXT.get(meta.get('mime'), 'bin')}"
    path.write_bytes(body)
    return {"ok": ok, "bytes": len(body), "path": str(path), "why": None if ok else "크기 · sha256 이 figure_get 과 다르다"}


async def run_check(call: Caller, a: argparse.Namespace, out_dir: Path, log: Callable[[str], None] = print,
                    opener: Callable[..., Any] = urllib.request.urlopen) -> dict:
    rep: dict[str, Any] = {"stages": {}}
    stages = rep["stages"]
    compare = [c for c in (a.compare or "").split(",") if c.strip()]
    fold = json.loads(a.fold) if a.fold else None
    # 1) 위치
    t0 = time.time()
    loc = Reply(await call(RISK, "risk_locate_for_section", locate_args(a)))
    d = loc.data if isinstance(loc.data, dict) else {}
    stages["locate"] = {"ok": d.get("status") == "located", "seconds": round(time.time() - t0, 2), "status": d.get("status"),
                        "reason": (d.get("reason") or {}).get("code"), "fix": (d.get("reason") or {}).get("fix"), "error": loc.head if loc.error else None}
    if not stages["locate"]["ok"]:
        log(f"✗ 위치를 정하지 못했다 — {stages['locate']['reason'] or stages['locate']['error']}"
            + (f" · 고칠 곳 {stages['locate']['fix']}" if stages['locate']['fix'] else ""))
        return rep
    f1 = d.get("f1") or {}
    calls = f1.get("calls") or []
    rep["located"] = {"stepforge_project_id": f1.get("stepforge_project_id"), "point": (d.get("mcad") or {}), "planes": d.get("planes"),
                      "body": (d.get("body") or {}).get("path"), "window_mm": d.get("window_mm"), "transform": (d.get("transform") or {}).get("status")}
    if not calls:
        stages["locate"].update(ok=False, reason="no_f1_calls")
        log("✗ 답에 f1.calls 가 없다 — 리스크 앱이 옛 판이다(fc384f4b 뒤 판이어야 한다)")
        return rep
    if not compare:
        log("· --compare 가 없어 짝 단면은 이 과제 하나로만 부를 수 없다 — 견줄 판 id 를 준다(F1 은 2 ~ 6 과제)")
        stages["pair_view"] = {"ok": False, "why": "no_compare"}
        return rep
    rows = pair_rows(calls, compare, fold)
    # 2) 짝 단면 — 평면마다
    views = []
    for row in rows:
        t0 = time.time()
        r = Reply(await call(SF, "section_pair_view", row))
        views.append({**view_summary(r), "axis": row.get("axis"), "seconds": round(time.time() - t0, 2)})
    stages["pair_view"] = {"ok": all(v["ok"] for v in views), "views": views}
    # 3) 묶음
    t0 = time.time()
    b = Reply(await call(SF, "section_batch", {"rows": rows}))
    bd = b.data if isinstance(b.data, dict) else {}
    batch = {"ok": False, "job_id": bd.get("job_id"), "reused": bd.get("reused"), "error": b.head if b.error else None, "rows": []}
    if bd.get("job_id"):
        for i in range(1, len(rows) + 1):
            got, waited = await wait_ready(lambda i=i: _reply(call, SF, "section_batch_result", {"job_id": bd["job_id"], "row": i}), a.job_wait, POLL_BATCH_S)
            batch["rows"].append({**(view_summary(got) if got else {"ok": False}), "row": i, "waited_s": round(waited, 1)})
        batch["ok"] = all(r["ok"] for r in batch["rows"])
    batch["seconds"] = round(time.time() - t0, 1)
    stages["batch"] = batch
    # 4) 적층 그림
    if a.stackup_other:
        t0 = time.time()
        args = {"project_id": a.stackup_a or f1.get("stepforge_project_id"), "other_project_id": a.stackup_other, "format": "jpg"}
        for k in ("axis_a", "axis_b"):
            if getattr(a, k):
                args[k] = getattr(a, k)
        s = Reply(await call(SF, "stackup_figure", args))
        sd = s.data if isinstance(s.data, dict) else {}
        st = {"ok": not s.error and s.images > 0, "path": "direct", "fig_refs": s.fig_refs, "error": s.head if s.error else None,
              "job_not_queued": sd.get("job_not_queued"), "comparable": sd.get("comparable")}
        job = sd.get("job") or {}
        last = s
        if not st["ok"] and job.get("job_id"):
            got, waited = await wait_ready(lambda: _reply(call, SF, "stackup_figure", {"job_id": job["job_id"], "format": "jpg"}), a.job_wait, POLL_STACKUP_S)
            st.update(path="job", job_id=job["job_id"], waited_s=round(waited, 1), ok=bool(got and not got.error and got.images),
                      fig_refs=(got.fig_refs if got else []), error=(got.head if got and got.error else None))
            last = got
        # 쪽 — 줄이 60 넘으면 쪽마다 그림이 따로다(StepForge a77 — 답의 page{page, pages, next}). 끝 쪽까지 따라가 다 받는다.
        pg = (last.data or {}).get("page") if last and isinstance(last.data, dict) else None
        if st["ok"] and isinstance(pg, dict) and int(pg.get("pages") or 1) > int(pg.get("page") or 1):
            base = {"job_id": st["job_id"], "format": "jpg"} if st.get("job_id") else args
            bad = 0
            for k in range(int(pg.get("page") or 1) + 1, int(pg["pages"]) + 1):
                pr = Reply(await call(SF, "stackup_figure", {**base, "page": k}))
                st["fig_refs"] = st["fig_refs"] + pr.fig_refs
                bad += int(pr.error or not pr.images)
            st.update(pages=int(pg["pages"]), page_failures=bad, ok=st["ok"] and not bad)
        st["seconds"] = round(time.time() - t0, 1)
        stages["stackup"] = st
    # 5) 그림 받기
    refs = list(dict.fromkeys(ref for v in views for ref in v["fig_refs"]))
    refs += [ref for r in batch["rows"] for ref in r.get("fig_refs", []) if ref not in refs]
    refs += [ref for ref in (stages.get("stackup") or {}).get("fig_refs", []) if ref not in refs]
    fetched = []
    for ref in refs:
        g = Reply(await call(GW, "figure_get", {"ref": ref}))
        meta = g.data if isinstance(g.data, dict) else {}
        try:
            got = fetch_figure(meta, out_dir / "figs", opener) if not g.error else {"ok": False, "why": g.head}
        except (urllib.error.URLError, OSError) as exc:
            got = {"ok": False, "why": f"받지 못했다 — {exc!r}"[:200]}
        fetched.append({"ref": ref, **got})
    stages["fetch"] = {"ok": bool(fetched) and all(f["ok"] for f in fetched), "figures": fetched}
    # 6) 쓰기(고른 것만)
    if a.ra_report and refs:
        res = []
        for ref in refs:
            w = Reply(await call(GW, "figure_to_report", {"ref": ref, "report_id": a.ra_report, "caption": f"CAD 점검 — {ref}"}))
            res.append({"ref": ref, "ok": not w.error, "head": w.head[:160]})
        stages["to_report"] = {"ok": all(r["ok"] for r in res), "results": res}
    if a.mxwp_doc and a.mxwp_section and refs:
        w = Reply(await call(GW, "figure_to_doc", {"ref": refs[0], "slug": a.mxwp_doc, "section_id": a.mxwp_section, "caption": f"CAD 점검 — {refs[0]}"}))
        stages["to_doc"] = {"ok": not w.error, "head": w.head[:160]}
    return rep


async def _reply(call: Caller, app: str, original: str, args: dict) -> Reply:
    return Reply(await call(app, original, args))


def summary_text(rep: dict) -> str:
    """사람이 답에 옮길 요약 — 상태 · 수 · 초만(이름 · 경로 · id 없음)."""
    st = rep["stages"]
    mark = lambda ok: "✓" if ok else "✗"  # noqa: E731
    lines = []
    lo = st.get("locate", {})
    lines.append(f"{mark(lo.get('ok'))} 위치 찾기 — {lo.get('status')} · {lo.get('seconds')}초" + (f" · 까닭 {lo.get('reason')}" if not lo.get("ok") else
                 f" · 평면 {len((rep.get('located') or {}).get('planes') or [])} · 몸체 {'있음' if (rep.get('located') or {}).get('body') else '없음'} · 변환 {(rep.get('located') or {}).get('transform')}"))
    if "pair_view" in st:
        pv = st["pair_view"]
        if pv.get("views"):
            for v in pv["views"]:
                lines.append(f"{mark(v['ok'])} 짝 단면({v.get('axis')}) — {v['seconds']}초 · 그림 {v['images']} · 간극 행 {v.get('rows_total')} · 강조 못 찾음 "
                             f"{v['unmatched_highlight']} · 몸체 없는 칸 {v['body_missing']} · 안 그린 파트 {v['not_drawn']}"
                             + (f" · 접혀 움직인 파트 {v['fold_moved']}" if v.get("fold_moved") is not None else "") + (f" · 오류 {v['error'][:80]}" if v.get("error") else ""))
        else:
            lines.append(f"✗ 짝 단면 — {pv.get('why')}")
    if "batch" in st:
        b = st["batch"]
        lines.append(f"{mark(b['ok'])} 묶음 — 줄 {len(b['rows'])} · 그림 {sum(r.get('images', 0) for r in b['rows'])} · {b['seconds']}초 · 같은 줄 다시 {b.get('reused')}"
                     + (f" · 오류 {b['error'][:80]}" if b.get("error") else ""))
    if "stackup" in st:
        s = st["stackup"]
        lines.append(f"{mark(s['ok'])} 적층 그림 — {s['path']} · {s['seconds']}초" + (f" · 기다림 {s.get('waited_s')}초" if s.get("waited_s") is not None else "")
                     + (f" · 쪽 {s['pages']}(실패 {s['page_failures']})" if s.get("pages") else "")
                     + (f" · 잡 안 넣음 {str(s['job_not_queued'])[:80]}" if s.get("job_not_queued") else "") + (f" · 오류 {s['error'][:80]}" if s.get("error") else ""))
    if "fetch" in st:
        f = st["fetch"]
        bad = [x for x in f["figures"] if not x["ok"]]
        lines.append(f"{mark(f['ok'])} 그림 받기 — {len(f['figures']) - len(bad)}/{len(f['figures'])} 크기 · sha256 맞음" + (f" · 첫 실패 {bad[0]['why'][:80]}" if bad else ""))
    if "to_report" in st:
        lines.append(f"{mark(st['to_report']['ok'])} 보고서에 넣기 — {sum(r['ok'] for r in st['to_report']['results'])}/{len(st['to_report']['results'])}")
    if "to_doc" in st:
        lines.append(f"{mark(st['to_doc']['ok'])} MX 백서 문서에 넣기")
    return "\n".join(lines)


def _tools_map(base: str, token: str) -> dict:
    url = base.rstrip("/").removesuffix("/mcp") + "/tools-map"
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as exc:
        if exc.code not in (401, 403):
            raise
    with urllib.request.urlopen(urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"}), timeout=30) as r:
        return json.load(r)


async def list_things(call: Caller, log: Callable[[str], None] = print) -> None:
    r = Reply(await call(RISK, "risk_list_projects", {}))
    rows = (r.data or {}).get("projects") if isinstance(r.data, dict) else (r.data or [])
    log(f"리스크 과제 {len(rows or [])}개(이 사람이 볼 수 있는 것) — 이름은 화면에만, 답에 옮기지 않는다")
    for p in (rows or [])[:50]:
        keys = {k: p.get(k) for k in ("id", "name", "title", "code", "stepforge_project_id", "odb_job_id", "sp_task") if k in p}
        log("  " + json.dumps(keys, ensure_ascii=False)[:220])
    s = Reply(await call(SF, "list_projects", {"limit": 50}))
    rows = (s.data or {}).get("projects") if isinstance(s.data, dict) else (s.data or [])
    log(f"StepForge 과제(앞 50) — 파트 수 · 단계")
    for p in (rows or [])[:50]:
        parts = p.get("parts")
        log(f"  {p.get('id')}  {str(p.get('name'))[:40]}  파트 {parts if isinstance(parts, int) else len(parts or [])}  {p.get('stage')}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="CAD 위치 가시화 · 분석 끝에서 끝까지 점검(읽기가 기본)")
    ap.add_argument("--gateway", default=os.environ.get("HWAX_GATEWAY_URL", "http://127.0.0.1:9110/mcp"))
    ap.add_argument("--token-env", default="HWAX_GATEWAY_PAT")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    r = sub.add_parser("run")
    r.add_argument("--project", required=True, help="리스크 과제 id")
    for flag in ("--finding", "--refdes", "--net", "--target-key", "--cluster-key", "--side", "--odb-job", "--stepforge"):
        r.add_argument(flag)
    r.add_argument("--x", type=float)
    r.add_argument("--y", type=float)
    r.add_argument("--compare", default="", help="견줄 판 StepForge 과제 id(쉼표로 여럿) — 짝 단면은 2 ~ 6 과제")
    r.add_argument("--fold", default="", help='접힘 JSON — {"axis_point":[x,y,z],"axis_dir":[..],"angle_deg":..,"moving":["글롭"]}')
    r.add_argument("--stackup-other", default="", help="적층 그림을 견줄 다른 보드 StepForge 과제 id")
    r.add_argument("--stackup-a", default="", help="적층 그림의 A 쪽 과제(기본은 위치의 CAD 과제)")
    r.add_argument("--axis-a", default="")
    r.add_argument("--axis-b", default="")
    r.add_argument("--job-wait", type=float, default=900, help="잡 하나를 기다릴 상한(초)")
    r.add_argument("--ra-report", default="", help="쓰기 — 이 RA 보고서에 받은 그림을 넣는다(시험용 보고서로)")
    r.add_argument("--mxwp-doc", default="", help="쓰기 — 이 MX 백서 문서(slug)에 첫 그림을 넣는다")
    r.add_argument("--mxwp-section", default="", help="그 문서의 절 id")
    r.add_argument("--out", default="")
    a = ap.parse_args(argv)
    if a.cmd == "run" and not (a.finding or a.refdes or a.net or (a.target_key and a.cluster_key) or (a.x is not None and a.y is not None)):
        print("✗ 항목을 하나 준다 — --finding · --refdes · --net · --target-key + --cluster-key · --x + --y 가운데", file=sys.stderr)
        return 2
    if a.cmd == "run" and a.fold:
        try:
            json.loads(a.fold)
        except ValueError as exc:
            print(f"✗ --fold 가 JSON 이 아니다 — {exc}", file=sys.stderr)
            return 2
    token = os.environ.get(a.token_env, "").strip()
    if not token:
        print(f"✗ {a.token_env} 가 비었다 — 포털 /auth/pat 로 발급한 PAT 를 넣고 다시(그 사람의 권한 · 이름으로 부른다)", file=sys.stderr)
        return 2
    try:
        tmap = _tools_map(a.gateway, token)
    except Exception as exc:  # noqa: BLE001
        print(f"✗ 게이트웨이 /tools-map 을 읽지 못했다 — {exc!r}", file=sys.stderr)
        return 2
    exposed = exposed_names(tmap)
    need = [f"{app}:{t}" for app, t in sorted(READ_TOOLS) if app != GW and (app, t) not in exposed]
    if need:
        print(f"✗ 이 게이트웨이에 없는 도구 — {', '.join(need)}(StepForge · 리스크 앱이 새 판인지 — docs/request-1030/server-setup.md 0절)", file=sys.stderr)
        return 2
    try:
        from mcp.client.session import ClientSession
        from mcp.client.streamable_http import streamablehttp_client
    except ImportError as exc:
        print(f"✗ mcp 모듈 없음({exc}) — 게이트웨이와 같은 파이썬(venv)으로 돌린다", file=sys.stderr)
        return 2
    writes = set()
    if a.cmd == "run" and a.ra_report:
        writes.add((GW, "figure_to_report"))
    if a.cmd == "run" and a.mxwp_doc and a.mxwp_section:
        writes.add((GW, "figure_to_doc"))
    out_dir = Path(a.out) if getattr(a, "out", "") else ROOT / "infra" / ".state" / "cad-figure-check" / time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())

    async def go() -> dict | None:
        async with streamablehttp_client(a.gateway, headers={"Authorization": f"Bearer {token}", "X-HWAX-Corr": "cad-figure-check"}) as (rr, ww, _):
            async with ClientSession(rr, ww) as s:
                await s.initialize()
                caller = Caller(lambda name, args: s.call_tool(name, args), exposed, writes)
                if a.cmd == "list":
                    await list_things(caller)
                    return None
                return await run_check(caller, a, out_dir, log=lambda m: print(m, file=sys.stderr))

    rep = asyncio.run(go())
    if rep is None:
        return 0
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    text = summary_text(rep)
    (out_dir / "summary.txt").write_text(text + "\n", encoding="utf-8")
    print(text)
    print(f"\n결과 — {out_dir}(받은 그림은 figs/ — 열어 자리 · 강조 · 간극 치수가 맞는지 사람이 본다. report.json 의 이름 · 경로는 답에 옮기지 않는다)")
    return 0 if all(v.get("ok") for v in rep["stages"].values()) else 3


if __name__ == "__main__":
    sys.exit(main())
