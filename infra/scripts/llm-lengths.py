#!/usr/bin/env python3
# LLM 풀 용량 측정의 입력 — 카드 대조 호출 원장과 심의 기록에서 프롬프트·출력 '길이' 만 뽑아 분위수·히스토그램 JSON 으로 쓴다(본문은 꺼내지 않는다)
"""길이 분포 추출기(docs/llm-pool/capacity.md 1절). 나오는 JSON 은 수(int·float·bool·null)와 이 파일에 적힌 이름뿐이다.

읽는 곳(전부 읽기만 한다).
  카드 대조  리스크 앱 원장 rr_review_calls — 호출 하나가 한 줄이고 서버가 돌려준 사용량(tokens_in·tokens_out, 보충 시도 합)과 프롬프트 글자 수가
            있다. 기본 자리는 ../HEAXHub/var/app_data/hwax_risk/risk_review.db(/data 이관 박스는 심링크를 따라간다). SQLite 를 mode=ro 로
            열고, 글 열은 SQL 안에서 수로 바꿔서만 꺼낸다 — 종류(kind)는 아래 KINDS 의 차례 번호로, 전문가(agent_key)는 DENSE_RANK 번호로.
            그래서 원장의 글 한 조각도 이 프로세스에 들어오지 않는다.
  GLM 심의   에이전트 서버 잡 원장(DELIB_JOB_DIR — 기본 ../HWAXAgentServer/artifacts 의 실제 경로 옆 delib-jobs)의 좌석 발언·의장 결정문 글자 수.
            프롬프트 길이는 어디에도 남지 않는다(출력만). 발언은 화면용으로 다듬은 글이라 모델 원출력(JSON)보다 짧다 — 아래 한계.
  Claude 심의 포털 심의 보관소(DELIB_ARCHIVE_ROOT — 기본 $HWAX_DATA_ROOT/delib-runs)의 워크플로 저널 result 글자 수. 좌석이 Claude
            서브에이전트라 GLM 부하가 아니다 — 참고로만 싣고 용량 측정(llm-capacity.py scenario)은 쓰지 않는다.

토큰 — 카드 대조는 서버가 센 값이다. 보충 시도가 여럿인 호출(attempts > 1)은 합을 시도 수로 나눈 값을 시도마다 하나씩 센다(시도마다 LLM 요청이
하나다). 심의 글자 수의 토큰 추정은 카드 대조 호출(시도 1회)에서 잰 '글자/토큰' 중앙값으로 나눈 값이다 — 카드 대조 기록이 없으면 싣지 않는다.

  python3 infra/scripts/llm-lengths.py --out <결과 디렉터리>/lengths.json
  python3 infra/scripts/llm-lengths.py --out lengths.json --risk-db <원장 사본> --delib-jobs <디렉터리> --delib-runs <디렉터리>
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REV = 1                     # 이 JSON 모양의 판 — 수다(나오는 값은 전부 수여야 한다)
# 카드 대조 호출 종류 — 에이전트 서버 card_review.KINDS 와 같은 차례. 밖의 값은 other 로 센다(원장의 글을 이름으로 쓰지 않는다).
KINDS = ("sweep", "verdict", "offcard", "noinput", "summary")
QS = (("p5", 0.05), ("p10", 0.10), ("p25", 0.25), ("p50", 0.50), ("p75", 0.75), ("p90", 0.90), ("p95", 0.95), ("p99", 0.99))


# ── 수 ────────────────────────────────────────────────────────────────────────────────────────────
def _pct(ys: list, q: float) -> float:
    """가장 가까운 순위(nearest-rank) — llm_ttft_probe 와 같은 규칙."""
    return ys[min(len(ys) - 1, max(0, math.ceil(q * len(ys)) - 1))]


def _hist(ys: list) -> dict:
    """2의 거듭제곱 칸 — [0,1) [1,2) [2,4) … 마지막 칸이 최댓값을 덮는다. 토큰·글자는 몇 자리씩 차이 나서 고른 칸이 쓸모없다."""
    edges = [0, 1]
    while edges[-1] <= ys[-1]:
        edges.append(edges[-1] * 2)
    counts = [0] * (len(edges) - 1)
    for y in ys:
        i = 0 if y < 1 else min(len(counts) - 1, int(math.floor(math.log2(y))) + 1)
        counts[i] += 1
    return {"edges": edges, "counts": counts}


def stats(values, *, hist: bool = True) -> dict:
    """수 목록 → {n, mean, std, min, p5…p99, max, hist}. 수가 아니거나 유한하지 않은 값은 버린다. 비면 {n: 0}."""
    ys = sorted(float(v) for v in values if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v))
    if not ys:
        return {"n": 0}
    n = len(ys)
    mean = sum(ys) / n
    out = {"n": n, "mean": round(mean, 3), "std": round(math.sqrt(sum((y - mean) ** 2 for y in ys) / n), 3), "min": ys[0]}
    out.update({name: _pct(ys, q) for name, q in QS})
    out["max"] = ys[-1]
    if hist:
        out["hist"] = _hist(ys)
    return out


# ── 설정 읽기(infra/.env 와 같은 규칙 — 마지막 활성 줄 · export · 공백 뒤 # 주석 · 따옴표) ─────────────────────────────
def env_value(path: Path, key: str) -> str:
    try:
        text = path.read_bytes().decode("utf-8", errors="replace")
    except OSError:
        return ""
    val = ""
    for ln in text.split("\n"):
        s = ln.lstrip(" \t\v\f\r")
        if s.startswith("export") and s[6:7] in (" ", "\t"):
            s = s[6:].lstrip(" \t")
        if s.startswith(key + "="):
            v = s[len(key) + 1:]
            for i, ch in enumerate(v):
                if ch == "#" and i > 0 and v[i - 1] in " \t\v\f\r":
                    v = v[:i]
                    break
            val = v.strip(" \t\n\v\f\r").replace('"', "").replace("'", "").replace("\r", "")
    return val


def default_risk_db() -> Path:
    """리스크 앱 데이터 디렉터리 — 허브가 ../HEAXHub/var/app_data/hwax_risk 를 앱의 /data 로 묶는다(server-setup-m2.md 2-1)."""
    return (ROOT.parent / "HEAXHub" / "var" / "app_data" / "hwax_risk").resolve() / "risk_review.db"


def default_delib_jobs() -> Path:
    """에이전트 서버 delib_jobs.JOB_DIR 과 같은 규칙 — DELIB_JOB_DIR, 없으면 ARTIFACT_DIR(기본 리포의 artifacts)의 실제 경로 옆 delib-jobs."""
    agent = ROOT.parent / "HWAXAgentServer"
    env = agent / ".env"
    explicit = os.environ.get("DELIB_JOB_DIR") or env_value(env, "DELIB_JOB_DIR")
    if explicit:
        return Path(explicit)
    art = os.environ.get("ARTIFACT_DIR") or env_value(env, "ARTIFACT_DIR") or str(agent / "artifacts")
    return Path(os.path.realpath(art)).parent / "delib-jobs"


def default_delib_runs() -> Path:
    """포털 심의 보관소 — archive-delib-run.sh·backup-local.sh 와 같은 규칙(DELIB_ARCHIVE_ROOT, 없으면 데이터 루트의 delib-runs)."""
    infra_env = ROOT / "infra" / ".env"
    explicit = os.environ.get("DELIB_ARCHIVE_ROOT") or env_value(infra_env, "DELIB_ARCHIVE_ROOT")
    if explicit:
        return Path(explicit)
    data_root = os.environ.get("HWAX_DATA_ROOT") or env_value(infra_env, "HWAX_DATA_ROOT") or "/data"
    return Path(data_root) / "delib-runs"


# ── 카드 대조 원장 ────────────────────────────────────────────────────────────────────────────────
_KIND_SQL = "CASE kind " + " ".join(f"WHEN '{k}' THEN {i}" for i, k in enumerate(KINDS)) + " ELSE -1 END"
_CALLS_SQL = (f"SELECT {_KIND_SQL}, prompt_chars, tokens_in, tokens_out, attempts, started_at, duration_ms, llm_ms, "
              "DENSE_RANK() OVER (ORDER BY agent_key) FROM rr_review_calls")


def _in_flight(rows: list) -> tuple[list, list]:
    """LLM 을 부른 호출마다 그 시작 순간에 돌던 호출 수와 서로 다른 전문가 수 — (calls, experts). 시작·끝으로 훑는다(n log n).
    같은 순간에 끝나는 호출은 시작보다 먼저 뺀다."""
    events = []
    for start, end, agent in rows:
        events.append((end, 0, agent))
        events.append((start, 1, agent))
    events.sort()
    active: dict = {}
    calls, experts = [], []
    n = 0
    for _t, is_start, agent in events:
        if is_start:
            n += 1
            active[agent] = active.get(agent, 0) + 1
            calls.append(n)
            experts.append(len(active))
        else:
            n -= 1
            active[agent] -= 1
            if not active[agent]:
                del active[agent]
    return calls, experts


def card_review(db: Path) -> tuple[dict, dict]:
    """(출처 표, 분포) — 원장이 없거나 표가 없으면 분포는 비고 출처 표가 까닭의 칸을 든다."""
    src = {"found": False, "rows": 0, "rows_with_usage": 0, "multi_attempt_rows": 0, "llm_calls": 0, "other_kind_rows": 0}
    if not db.is_file():
        return src, {}
    try:
        con = sqlite3.connect(f"{db.as_uri()}?mode=ro", uri=True)
    except sqlite3.Error:
        src["unreadable"] = True
        return src, {}
    try:
        rows = con.execute(_CALLS_SQL).fetchall()
    except sqlite3.Error:
        src["unreadable"] = True
        return src, {}
    finally:
        con.close()
    src["found"] = True
    src["rows"] = len(rows)
    per: dict = {k: {"prompt_tokens": [], "output_tokens": [], "prompt_chars": [], "chars_per_token": []} for k in (*KINDS, "other")}
    spans = []
    for kind_i, p_chars, t_in, t_out, attempts, started, dur_ms, llm_ms, agent in rows:
        kind = KINDS[kind_i] if 0 <= kind_i < len(KINDS) else "other"
        src["other_kind_rows"] += kind == "other"
        b = per[kind]
        if isinstance(p_chars, int) and p_chars > 0:
            b["prompt_chars"].append(p_chars)
        n = attempts if isinstance(attempts, int) and attempts > 0 else 0
        if n and (isinstance(t_in, int) or isinstance(t_out, int)):
            src["rows_with_usage"] += 1
            src["multi_attempt_rows"] += n > 1
            src["llm_calls"] += n
            if isinstance(t_in, int):
                b["prompt_tokens"] += [t_in / n] * n
            if isinstance(t_out, int):
                b["output_tokens"] += [t_out / n] * n
            if n == 1 and isinstance(t_in, int) and t_in > 0 and isinstance(p_chars, int) and p_chars > 0:
                b["chars_per_token"].append(p_chars / t_in)
        if isinstance(llm_ms, int) and llm_ms > 0 and isinstance(started, int) and isinstance(dur_ms, int) and dur_ms > 0:
            spans.append((started, started + dur_ms / 1000.0, agent))
    def block(lists: dict) -> dict:
        return {"prompt_tokens": stats(lists["prompt_tokens"]), "output_tokens": stats(lists["output_tokens"]),
                "prompt_chars": stats(lists["prompt_chars"]), "chars_per_token": stats(lists["chars_per_token"], hist=False)}
    pooled = {key: [v for k in per for v in per[k][key]] for key in ("prompt_tokens", "output_tokens", "prompt_chars", "chars_per_token")}
    calls, experts = _in_flight(spans)
    dist = {"all": block(pooled),
            "by_kind": {k: block(per[k]) for k in (*KINDS, "other") if any(per[k].values())},
            "calls_in_flight": stats(calls, hist=False), "experts_in_flight": stats(experts, hist=False)}
    return src, dist


# ── 심의 기록 ──────────────────────────────────────────────────────────────────────────────────────
def _turn_chars(t: dict):
    n = t.get("say_full_chars")
    if isinstance(n, int) and not isinstance(n, bool):
        return n
    for k in ("say_full", "say"):
        if isinstance(t.get(k), str):
            return len(t[k])
    return None


def delib_jobs(d: Path) -> tuple[dict, dict]:
    """GLM 심의 잡 원장 — 파일마다 잡 하나(바로 아래의 *.json 만 — list/ 같은 하위 디렉터리는 목록 캐시다)."""
    src = {"found": d.is_dir(), "jobs": 0, "unreadable_files": 0, "turns": 0}
    seat, chair, per_job = [], [], []
    if not src["found"]:
        return src, {}
    for f in sorted(d.glob("*.json")):
        try:
            job = json.loads(f.read_bytes().decode("utf-8", errors="replace"))
        except (OSError, ValueError, RecursionError):
            src["unreadable_files"] += 1
            continue
        if not isinstance(job, dict):
            src["unreadable_files"] += 1
            continue
        src["jobs"] += 1
        turns = [t for t in (job.get("turns") or []) if isinstance(t, dict) and "note" not in t]
        per_job.append(len(turns))
        for t in turns:
            c = _turn_chars(t)
            if c is not None:
                seat.append(c)
        if isinstance(job.get("decision"), str) and job["decision"]:
            chair.append(len(job["decision"]))
    src["turns"] = len(seat)
    return src, {"seat_output_chars": stats(seat), "chair_output_chars": stats(chair), "turns_per_job": stats(per_job, hist=False)}


def delib_runs(d: Path) -> tuple[dict, dict]:
    """Claude 워크플로 심의 저널 — result 줄의 글자 수(글이면 그 길이, 아니면 JSON 으로 적은 길이)."""
    src = {"found": d.is_dir(), "journals": 0, "results": 0, "bad_lines": 0}
    out = []
    if not src["found"]:
        return src, {}
    for f in sorted(set(d.rglob("journal.jsonl")) | set(d.rglob("*.journal.jsonl"))):
        src["journals"] += 1
        try:
            lines = f.read_bytes().decode("utf-8", errors="replace").split("\n")
        except OSError:
            continue
        for ln in lines:
            if not ln.strip():
                continue
            try:
                r = json.loads(ln)
            except (ValueError, RecursionError):
                src["bad_lines"] += 1
                continue
            if isinstance(r, dict) and r.get("type") == "result" and r.get("result") is not None:
                v = r["result"]
                out.append(len(v) if isinstance(v, str) else len(json.dumps(v, ensure_ascii=False)))
    src["results"] = len(out)
    return src, {"result_chars": stats(out)}


def _tokens_est(chars_stats: dict, cpt: float | None) -> dict:
    """글자 분포를 글자/토큰 비로 나눈 추정(분위수마다 나눈다 — 단조라 순서가 보존된다). 비율이 없으면 {n: 0}."""
    if not cpt or not chars_stats.get("n"):
        return {"n": 0}
    out = {k: (round(v / cpt, 1) if isinstance(v, (int, float)) and k != "n" else v) for k, v in chars_stats.items() if k != "hist"}
    return out


def extract(risk_db: Path, jobs_dir: Path, runs_dir: Path) -> dict:
    cr_src, cr = card_review(risk_db)
    dj_src, dj = delib_jobs(jobs_dir)
    dr_src, dr = delib_runs(runs_dir)
    cpt = ((cr.get("all") or {}).get("chars_per_token") or {}).get("p50")
    if dj:
        dj["seat_output_tokens_est"] = _tokens_est(dj["seat_output_chars"], cpt)
        dj["chair_output_tokens_est"] = _tokens_est(dj["chair_output_chars"], cpt)
    return {"rev": REV, "made_at": int(time.time()), "chars_per_token_p50": cpt,
            "sources": {"card_review": cr_src, "delib_jobs": dj_src, "delib_runs_claude": dr_src},
            "card_review": cr, "delib_jobs": dj, "delib_runs_claude": dr}


def _line(name: str, s: dict) -> str:
    if not s.get("n"):
        return f"  {name:<28} 없음"
    return f"  {name:<28} n={s['n']:<6} p50={s['p50']:<10g} p95={s['p95']:<10g} max={s['max']:g}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="LLM 풀 용량 측정의 길이 분포(본문 없이 수만)")
    ap.add_argument("--out", required=True, help="결과 JSON(있으면 --force 없이는 덮지 않는다)")
    ap.add_argument("--risk-db", type=Path, help="리스크 앱 원장(기본 ../HEAXHub/var/app_data/hwax_risk/risk_review.db)")
    ap.add_argument("--delib-jobs", type=Path, help="에이전트 서버 심의 잡 원장 디렉터리(기본 DELIB_JOB_DIR 규칙)")
    ap.add_argument("--delib-runs", type=Path, help="포털 심의 보관소(기본 DELIB_ARCHIVE_ROOT 규칙)")
    ap.add_argument("--force", action="store_true", help="--out 이 있어도 덮는다")
    a = ap.parse_args(argv)
    out = Path(a.out)
    if out.exists() and not a.force:
        print(f"[lengths] {out} 가 이미 있다 — 덮지 않는다(--force)", file=sys.stderr)
        return 2
    risk_db, jobs_dir, runs_dir = a.risk_db or default_risk_db(), a.delib_jobs or default_delib_jobs(), a.delib_runs or default_delib_runs()
    res = extract(risk_db, jobs_dir, runs_dir)
    src = res["sources"]
    print(f"[lengths] 카드 대조 원장 {risk_db} — " + (f"호출 {src['card_review']['rows']}줄 · 사용량 있는 줄 {src['card_review']['rows_with_usage']}"
          if src["card_review"]["found"] else ("못 읽었다" if src["card_review"].get("unreadable") else "없다")))
    print(f"[lengths] GLM 심의 잡 원장 {jobs_dir} — " + (f"잡 {src['delib_jobs']['jobs']} · 좌석 발언 {src['delib_jobs']['turns']}"
          if src["delib_jobs"]["found"] else "없다"))
    print(f"[lengths] Claude 심의 보관소 {runs_dir} — " + (f"저널 {src['delib_runs_claude']['journals']} · result {src['delib_runs_claude']['results']}"
          if src["delib_runs_claude"]["found"] else "없다") + "(GLM 부하가 아니다 — 참고)")
    cr = res["card_review"]
    for k in ("all", *KINDS, "other"):
        b = cr.get("all") if k == "all" else (cr.get("by_kind") or {}).get(k)
        if b:
            print(_line(f"카드 대조 {k} 프롬프트 토큰", b["prompt_tokens"]))
            print(_line(f"카드 대조 {k} 출력 토큰", b["output_tokens"]))
    if cr:
        print(_line("돌던 호출 수(호출 시작 때)", cr["calls_in_flight"]))
        print(_line("돌던 전문가 수(호출 시작 때)", cr["experts_in_flight"]))
    if res["delib_jobs"]:
        print(_line("GLM 심의 좌석 발언 글자", res["delib_jobs"]["seat_output_chars"]))
    if not (cr.get("all") or {}).get("prompt_tokens", {}).get("n"):
        print("[lengths] ⚠ 카드 대조 사용량이 없다 — llm-capacity.sh 는 이 파일로 부하를 만들 수 없다(원장 자리를 --risk-db 로 준다)", file=sys.stderr)
    tmp = out.with_name(f".{out.name}.tmp-{os.getpid()}")
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, out)
    print(f"[lengths] ✓ {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
