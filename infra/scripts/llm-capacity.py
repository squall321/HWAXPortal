#!/usr/bin/env python3
# LLM 풀 용량 측정의 계산 — 길이 분포로 GuideLLM 시나리오를 만들고(scenario), 서버 지표를 떠 두고(metrics), 결과에서 표와 세 손잡이 권장을 낸다(summarize)
"""llm-capacity.sh 가 부른다(docs/llm-pool/capacity.md). 표준 라이브러리만 쓴다 — 호스트 python3 로 돈다.

  scenario   길이 분포(llm-lengths.py 의 JSON) → GuideLLM 시나리오 JSON. 키는 싣지 않는다(실행 환경 GUIDELLM__SPEC__BACKEND__API_KEY 로만 간다).
  metrics    vLLM 서버들의 /metrics 에서 도는 수·기다리는 수·접두 캐시 누계를 떠서 JSON 으로(키가 필요 없는 주소다 — 프록시 없이 부른다).
  busy · activity  에이전트 서버 /health — 재기 전에 도는 심의·카드 대조가 없는지(busy), 변형 앞뒤로 다른 일이 돌았는지(activity).
  wait-router      측정용 라우터가 서버 전부를 '올라옴' 으로 보고 모델이 같다고 답할 때까지 기다린다.
  summarize  결과 디렉터리의 변형마다(<변형>/benchmarks.json) 동시 수별 한 줄 — 표(summary.md)·JSON(summary.json)·권장.

권장 규칙(RULE — summary.md 에 그대로 싣는다). 변형마다 동시 수가 낮은 단계부터 차례로 본다. 한 단계가 받아들여지려면
  ① 실패한 요청이 0 이다(GuideLLM errored — 기한에 걸려 끝나지 못한 incomplete 는 실패로 치지 않는다),
  ② TTFT p95 가 한도 이하다 — 한도는 그 변형의 가장 낮은 단계의 TTFT p50 × --ttft-ratio(기본 3), --ttft-max-s 를 주면 그 초,
  ③ 요청/초가 바로 앞에 받아들인 단계보다 --growth(기본 5%) 이상 늘었다(첫 단계는 ③ 을 보지 않는다).
처음 어긋나는 단계에서 멈추고, 마지막으로 받아들인 단계의 동시 수가 그 변형의 권장 C 다.
세 손잡이는 라우터 경로 변형 가운데 C 가 가장 큰 것(같으면 그 C 의 요청/초가 큰 것, 그래도 같으면 붙임 문턱이 기본(2)인 것)의 C 로 —
  CARD_REVIEW_CONCURRENCY = C · HWAXRISK_REVIEW_CONCURRENCY = C · CARD_REVIEW_MAX_STREAMS = C + ⌈C/2⌉ (기본 8·8·12 와 같은 비).
라우터 경로를 재지 않았으면 직결 변형으로 낸다. 직결(서버 하나) 값은 한쪽 서버를 정비하는 날 되돌릴 값으로 함께 적는다.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOKENIZER_IN_SIF = "/opt/tokenizers/glm-5.2"     # build-guidellm.sh 가 굽는 자리
DEFAULT_SLACK = 2.0                              # 라우터 LLM_ROUTER_STICKY_SLACK 기본(llm_router.KNOBS)
WARMUP_SHARE = 0.33                              # 단계마다 데우기로 빼는 요청 몫(요청 수가 3 × 동시 수라 첫 물결이다)
STICKY_KEY_TOKENS = 2000                         # 라우터 붙임 열쇠(앞 8,000자)를 앞부분이 다 채우는 대략의 토큰 수(합성 영어 글 ≈ 4자/토큰)
KNOB_DEFAULTS = {"CARD_REVIEW_CONCURRENCY": 8, "HWAXRISK_REVIEW_CONCURRENCY": 8, "CARD_REVIEW_MAX_STREAMS": 12}
RULE = ("변형마다 동시 수가 낮은 단계부터 차례로 본다 — ① 실패한 요청 0(기한에 걸린 미완료는 실패가 아니다) ② TTFT p95 ≤ 한도"
        "(가장 낮은 단계의 TTFT p50 × {ratio:g}{absolute}) ③ 요청/초가 앞 단계보다 {growth:.0%} 이상 는다(첫 단계 제외). "
        "처음 어긋나는 단계에서 멈추고 마지막으로 받아들인 단계의 동시 수가 권장 C 다. "
        "세 손잡이 — CARD_REVIEW_CONCURRENCY = C · HWAXRISK_REVIEW_CONCURRENCY = C · CARD_REVIEW_MAX_STREAMS = C + ⌈C/2⌉"
        "(라우터 경로 변형 가운데 C 가 가장 큰 것, 같으면 요청/초가 큰 것, 그래도 같으면 붙임 문턱 기본 2).")


# ── 시나리오 ──────────────────────────────────────────────────────────────────────────────────────
class LengthsError(ValueError):
    pass


def pick_lengths(lengths: dict, kind: str) -> dict:
    """카드 대조 분포 하나 — kind 가 all 이면 전부 합친 것, 아니면 그 종류."""
    cr = lengths.get("card_review") or {}
    block = cr.get("all") if kind == "all" else (cr.get("by_kind") or {}).get(kind)
    if not block or not (block.get("prompt_tokens") or {}).get("n") or not (block.get("output_tokens") or {}).get("n"):
        raise LengthsError(f"길이 분포에 카드 대조 '{kind}' 의 프롬프트·출력 토큰이 없다 — llm-lengths.py 가 원장을 읽었는지 본다"
                           "(카드 대조를 한 번이라도 돌린 박스여야 한다)")
    return block


def _dist(s: dict, prefix: str, shift: int = 0) -> dict:
    """분포 → GuideLLM 합성 칸(평균 · 표준편차 · 하한 p5 · 상한 p95). shift 만큼 빼고(붙임 앞부분 몫) 1 아래로 내리지 않는다."""
    lo = max(1, int(round(s["p5"])) - shift)
    hi = max(lo, int(round(s["p95"])) - shift)
    mean = min(max(int(round(s["mean"])) - shift, lo), hi)
    out = {prefix: mean, f"{prefix}_min": lo, f"{prefix}_max": hi}
    if int(round(s.get("std") or 0)) >= 1:
        out[f"{prefix}_stdev"] = int(round(s["std"]))
    return out


def requests_per_level(levels: list, fixed: int, minimum: int) -> list:
    """단계마다 낼 요청 수 — fixed 를 주면 그 수, 아니면 max(minimum, 3 × 동시 수)(물결 셋 — 첫 물결의 몰림이 p95 를 다 차지하지 않게)."""
    return [fixed if fixed > 0 else max(minimum, 3 * c) for c in levels]


def scenario(lengths: dict, *, kind: str, target: str, levels: list, requests: int, min_requests: int, max_seconds: float,
             prefix_share: float, prefix_count: int, tokenizer: str, report: str, labels: dict, timeout_s: float,
             seed: int) -> tuple[dict, dict]:
    """(GuideLLM 시나리오, 고른 수의 요약). 붙임 앞부분 — 카드 대조 프롬프트는 [당신]→[카드]→[단위]→[지시] 차례라 같은 전문가·같은 묶음의
    호출이 앞을 공유한다(card_review.build_prompt). 원장에는 그 몫이 따로 없으므로 프롬프트 중앙값 × prefix_share 를 앞부분으로 두고
    (p5 를 넘지 않게) 서로 다른 앞부분 prefix_count 개를 요청마다 고른다. GuideLLM 은 앞부분을 system 메시지로 보낸다 — 라우터의 붙임 열쇠
    (앞 8,000자)가 그 앞부분으로 정해지는 크기면 같은 앞부분은 같은 서버로 붙는다.
    seed 는 변형마다 달라야 한다 — 같은 씨앗이면 다음 변형이 앞 변형의 프롬프트를 그대로 다시 보내 vLLM 접두 캐시에 거저 맞는다(dev 스모크 실측:
    첫 변형 적중 18% · 같은 씨앗의 다음 변형 96%)."""
    block = pick_lengths(lengths, kind)
    pt, ot = block["prompt_tokens"], block["output_tokens"]
    prefix = int(round(prefix_share * pt["p50"])) if prefix_share > 0 else 0
    prefix = max(0, min(prefix, int(round(pt["p5"])) - 1))
    if prefix_count <= 0:
        inflight = ((lengths.get("card_review") or {}).get("experts_in_flight") or {}).get("p50")
        prefix_count = max(1, int(round(inflight))) if inflight else 4
    data = {"kind": "synthetic_text", **_dist(pt, "prompt_tokens", prefix), **_dist(ot, "output_tokens")}
    if prefix > 0:
        data["prefix_buckets"] = [{"prefix_count": prefix_count, "prefix_tokens": prefix}]
    counts = requests_per_level(levels, requests, min_requests)
    spec = {
        "backend": {"kind": "openai_http", "target": target, "timeout": timeout_s, "http2": False},
        # 첫 물결(동시에 C 개가 한꺼번에 미리 채우기)은 재지 않는다 — 단계마다 요청의 앞 1/3(≈ 물결 하나)을 데우기로 뺀다. 카드 대조는 잡이
        # 시작할 때만 몰리고 그 뒤로는 끝나는 대로 하나씩 들어온다(그 고른 상태를 잰다). 'requests' 로 못박는다 — 기본(prefer_duration)은
        # max_duration 의 비율(900초의 1/3)로 읽는다.
        "profile": {"kind": "concurrent", "streams": list(levels), "warmup": {"percent": WARMUP_SHARE, "mode": "requests"}},
        "constraints": [{"kind": "max_requests", "count": counts}, {"kind": "max_duration", "seconds": max_seconds}],
        "tokenizer": {"kind": "huggingface_auto", "model": tokenizer},
        "data": [data],
        # 요청마다의 글(합성 프롬프트·생성문)은 남기지 않는다 — 수만 남는다(결과 파일이 수백 MB 가 되지 않게)
        "metrics": {"kind": "generative", "sample_size": 0},
        "outputs": [{"kind": "json", "path": report}],
        "seed": {"kind": "static", "value": seed},
    }
    info = {"kind": kind, "levels": list(levels), "requests": counts, "prefix_tokens": prefix,
            "prefix_count": prefix_count if prefix else 0, "prompt_tokens": data["prompt_tokens"], "output_tokens": data["output_tokens"],
            "sticky_key_from_prefix": prefix >= STICKY_KEY_TOKENS, "seed": seed}
    return {"spec": spec, "metadata": {"labels": {k: str(v) for k, v in {**labels, **info}.items()}}}, info


# ── 서버 지표 ──────────────────────────────────────────────────────────────────────────────────────
_METRICS = {"vllm:num_requests_running": "running", "vllm:num_requests_waiting": "waiting",
            "vllm:prefix_cache_queries_total": "cache_queries", "vllm:prefix_cache_hits_total": "cache_hits"}


def parse_metrics(text: str) -> dict:
    """Prometheus 글 → {running, waiting, cache_queries, cache_hits}(라벨 묶음 합). 이름이 정확히 같은 줄만 센다(라우터와 같은 규칙)."""
    acc: dict = {}
    for ln in text.split("\n"):
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        name = ln.split("{", 1)[0].split(" ", 1)[0]
        if name in _METRICS:
            try:
                v = float(ln.rsplit(" ", 1)[-1])
            except ValueError:
                continue
            if math.isfinite(v):
                acc[_METRICS[name]] = acc.get(_METRICS[name], 0.0) + v
    return acc


def metrics_url(base: str) -> str:
    """서버 /v1 주소 → 같은 서버의 /metrics."""
    b = base.rstrip("/")
    return (b[:-3] if b.endswith("/v1") else b) + "/metrics"


def snapshot(urls: list, timeout_s: float = 5.0) -> list:
    """서버마다 지표 한 번 — 못 읽으면 그 칸은 {error: 오류 이름}(재지 않은 것을 0 으로 적지 않는다). 프록시를 타지 않는다."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    out = []
    for i, u in enumerate(urls):
        try:
            with opener.open(metrics_url(u), timeout=timeout_s) as r:
                out.append({"server": i + 1, **parse_metrics(r.read().decode("utf-8", errors="replace"))})
        except Exception as exc:  # noqa: BLE001 — 무엇이든 '못 읽었다' 다
            out.append({"server": i + 1, "error": type(exc).__name__})
    return out


def get_json(url: str, timeout_s: float = 5.0):
    """루프백 JSON 하나(프록시 없이) — 못 읽으면 None."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(url, timeout=timeout_s) as r:
            return json.loads(r.read().decode("utf-8", errors="replace"))
    except Exception:  # noqa: BLE001 — 무엇이든 '못 읽었다' 다
        return None


def busy(health_url: str) -> tuple[int, str]:
    """에이전트 서버 /health 의 도는 심의·카드 대조 — (0 비었다 · 3 돈다 · 2 모른다, 한 줄). 측정은 GPU 를 차지하므로 둘 다 0 일 때만 돈다."""
    h = get_json(health_url)
    if not isinstance(h, dict):
        return 2, f"에이전트 서버 {health_url} 가 답하지 않는다 — 심의·카드 대조가 도는지 모른다"
    rv, dl = h.get("review_active"), h.get("delib_active")
    if not isinstance(rv, int) or not isinstance(dl, int):
        return 2, f"에이전트 서버 /health 에 review_active·delib_active 가 없다(받은 값 {rv!r} · {dl!r}) — 도는지 모른다"
    if rv or dl:
        return 3, f"카드 대조 {rv}건 · 심의 {dl}건이 돈다 — 끝난 뒤 다시 돌린다"
    return 0, "카드 대조 0 · 심의 0"


def activity(health_url: str) -> dict:
    """에이전트 서버의 일 — 도는 카드 대조 · 도는·줄 선 심의 · 카드 대조 누계(기동 뒤). 변형 앞뒤로 떠서 그 사이에 다른 일이 GPU 를
    나눠 썼는지 본다(누계가 늘었거나 앞뒤 어느 쪽이든 돌고 있었으면 흐려진 변형이다). 못 읽으면 {error}."""
    h = get_json(health_url)
    if not isinstance(h, dict):
        return {"error": "unreachable"}
    tot = ((h.get("card_review") or {}).get("totals") or {})
    vals = {"review_active": h.get("review_active"), "delib_active": h.get("delib_active"), "delib_queued": h.get("delib_queued"),
            "review_calls_total": tot.get("calls")}
    return {k: (v if isinstance(v, int) and not isinstance(v, bool) else None) for k, v in vals.items()}


def interference(before: dict, after: dict):
    """흐려졌나 — True(다른 일이 돌았다) · False · None(모른다). 앞뒤 어느 쪽이든 읽지 못했으면 모른다."""
    if "error" in before or "error" in after:
        return None
    busy = any((x.get(k) or 0) > 0 for x in (before, after) for k in ("review_active", "delib_active"))
    b, a = before.get("review_calls_total"), after.get("review_calls_total")
    if b is None or a is None:
        return True if busy else None
    return busy or a > b


def wait_router(url: str, expect: int, timeout_s: float) -> tuple[int, str]:
    """측정용 라우터가 서버 expect 곳을 '올라옴' 으로 보고 모델이 같다고 답할 때까지 — (0 됐다 · 2 기한 안에 안 됐다, 마지막 상태)."""
    deadline = time.monotonic() + timeout_s
    last = "답 없음"
    while True:
        h = get_json(url.rstrip("/") + "/health", timeout_s=2.0)
        if isinstance(h, dict):
            last = (f"status={h.get('status')} 올라옴 {h.get('upstreams_up')}/{h.get('upstreams_total')} "
                    f"모델 같음={(h.get('models') or {}).get('match')}")
            if h.get("upstreams_up") == expect and h.get("upstreams_total") == expect and (h.get("models") or {}).get("match") is True:
                return 0, last
        if time.monotonic() >= deadline:
            return 2, last
        time.sleep(0.5)


# ── 결과 읽기 ──────────────────────────────────────────────────────────────────────────────────────
def _pick(m: dict, name: str, field: str = "p50", status: str = "successful"):
    s = ((m.get(name) or {}).get(status) or {})
    if field in ("mean", "median", "count"):
        return s.get(field)
    return (s.get("percentiles") or {}).get(field)


def _sec(ms):
    return None if ms is None else ms / 1000.0


def report_rows(report: dict) -> list:
    """GuideLLM 보고서 → 동시 수마다 한 줄(동시 수 차례). 초 단위로 바꾼 TTFT, ms 인 ITL, 요청/초, 출력 토큰/초."""
    rows = []
    for b in report.get("benchmarks") or []:
        strat = (b.get("config") or {}).get("strategy") or {}
        m = b.get("metrics") or {}
        tot = m.get("request_totals") or {}
        ok = int(tot.get("successful") or 0)
        rps = _pick(m, "requests_per_second", "mean")
        if rps is None and b.get("duration"):
            rps = ok / b["duration"]
        rows.append({"level": int(strat.get("streams") or strat.get("max_concurrency") or 0), "ok": ok,
                     "errored": int(tot.get("errored") or 0), "incomplete": int(tot.get("incomplete") or 0),
                     "ttft_p50_s": _sec(_pick(m, "time_to_first_token_ms", "p50")),
                     "ttft_p95_s": _sec(_pick(m, "time_to_first_token_ms", "p95")),
                     "itl_p50_ms": _pick(m, "inter_token_latency_ms", "p50"), "itl_p95_ms": _pick(m, "inter_token_latency_ms", "p95"),
                     "req_s": rps, "out_tok_s": _pick(m, "output_tokens_per_second", "mean"),
                     "prompt_tokens_mean": _pick(m, "prompt_token_count", "mean"),
                     "output_tokens_mean": _pick(m, "output_token_count", "mean"), "duration_s": b.get("duration")})
    return sorted(rows, key=lambda r: r["level"])


def recommend(rows: list, *, ttft_ratio: float = 3.0, ttft_max_s: float | None = None, growth: float = 0.05) -> dict:
    """RULE 그대로 — {level: 권장 C 또는 None, limit_s, verdicts: [(동시 수, ok|stop|after, 까닭)]}."""
    rows = sorted(rows, key=lambda r: r["level"])
    out = {"level": None, "limit_s": None, "verdicts": []}
    if not rows:
        return out
    base = rows[0].get("ttft_p50_s")
    limit = ttft_max_s if ttft_max_s is not None else (base * ttft_ratio if base is not None else None)
    out["limit_s"] = limit
    prev = None
    stopped = False
    for r in rows:
        if stopped:
            out["verdicts"].append((r["level"], "after", ""))
            continue
        why = []
        if r["errored"] > 0 or r["ok"] == 0:
            why.append(f"실패 {r['errored']}" if r["errored"] else "완료 0")
        if limit is None or r.get("ttft_p95_s") is None or r["ttft_p95_s"] > limit:
            why.append("TTFT p95 한도 초과" if limit is not None and r.get("ttft_p95_s") is not None else "TTFT 를 모른다")
        if prev is not None and (r.get("req_s") is None or prev.get("req_s") is None or r["req_s"] < prev["req_s"] * (1 + growth)):
            why.append(f"요청/초 증가 {growth:.0%} 미만")
        if why:
            stopped = True
            out["verdicts"].append((r["level"], "stop", " · ".join(why)))
            continue
        out["verdicts"].append((r["level"], "ok", ""))
        out["level"] = r["level"]
        prev = r
    return out


def knobs_for(c: int) -> dict:
    """세 손잡이 — 관문 = 워커 = C, 중계 = C + ⌈C/2⌉(기본 8·8·12 · 절차서의 16·16·24 와 같은 비)."""
    return {"CARD_REVIEW_CONCURRENCY": c, "HWAXRISK_REVIEW_CONCURRENCY": c, "CARD_REVIEW_MAX_STREAMS": c + math.ceil(c / 2)}


def _variant_order(name: str, labels: dict) -> tuple:
    return (labels.get("path") != "direct", float(labels.get("slack") or 0), name)


def summarize(results: Path, *, ttft_ratio: float = 3.0, ttft_max_s: float | None = None, growth: float = 0.05,
              knobs_now: dict | None = None) -> dict:
    """결과 디렉터리 → {variants: [...], basis, knobs, single_server, rule}. summary.json · summary.md 를 쓴다."""
    variants = []
    for f in sorted(results.glob("*/benchmarks.json")):
        rep = json.loads(f.read_text(encoding="utf-8"))
        labels = ((rep.get("config") or {}).get("metadata") or {}).get("labels") or {}
        rows = report_rows(rep)
        cache = None
        before, after = f.parent / "metrics-before.json", f.parent / "metrics-after.json"
        if before.is_file() and after.is_file():
            b0, a0 = json.loads(before.read_text(encoding="utf-8")), json.loads(after.read_text(encoding="utf-8"))
            # 두 번 다 읽힌 서버만 — 한쪽을 못 읽은 서버의 누계를 0 으로 치면 서버가 켜진 뒤 전부가 이 변형의 몫이 된다
            both = [(a, b) for a, b in zip(a0, b0) if all(isinstance(x.get(k), (int, float)) for x in (a, b) for k in ("cache_queries", "cache_hits"))]
            dq = sum(a["cache_queries"] - b["cache_queries"] for a, b in both)
            dh = sum(a["cache_hits"] - b["cache_hits"] for a, b in both)
            cache = round(dh / dq, 3) if both and dq > 0 else None
        routing = None
        stats_f = f.parent / "router-stats.json"
        if stats_f.is_file():
            st = json.loads(stats_f.read_text(encoding="utf-8"))
            # 서버는 차례 번호로만 — 주소(사내 IP)는 표에 싣지 않는다(이 표를 문서로 옮겨 적는다)
            routing = {"sent": [int(u.get("sent") or 0) for u in st], "sticky": sum(int(u.get("sticky") or 0) for u in st),
                       "overflow": sum(int(u.get("overflow") or 0) for u in st)}
        ab, aa = f.parent / "agent-before.json", f.parent / "agent-after.json"
        mixed = (interference(json.loads(ab.read_text(encoding="utf-8")), json.loads(aa.read_text(encoding="utf-8")))
                 if ab.is_file() and aa.is_file() else None)
        variants.append({"name": f.parent.name, "path": labels.get("path", "?"), "slack": labels.get("slack"),
                         "labels": labels, "rows": rows, "prefix_cache_hit_ratio": cache, "routing": routing, "interference": mixed,
                         "rec": recommend(rows, ttft_ratio=ttft_ratio, ttft_max_s=ttft_max_s, growth=growth)})
    variants.sort(key=lambda v: _variant_order(v["name"], v["labels"]))

    def strength(v):
        lv = v["rec"]["level"]
        rps = next((r["req_s"] or 0 for r in v["rows"] if r["level"] == lv), 0) if lv else 0
        default = v["slack"] is not None and float(v["slack"]) == DEFAULT_SLACK
        return (lv or 0, rps, default)

    routed = [v for v in variants if v["path"] == "router" and v["rec"]["level"]]
    direct = [v for v in variants if v["path"] == "direct" and v["rec"]["level"]]
    basis = max(routed or direct, key=strength) if (routed or direct) else None
    single = max(direct, key=strength) if direct else None
    res = {"rule": RULE.format(ratio=ttft_ratio, growth=growth, absolute=f" — 주어진 절대 한도 {ttft_max_s:g}초" if ttft_max_s else ""),
           "variants": variants, "basis": basis["name"] if basis else None,
           "knobs": knobs_for(basis["rec"]["level"]) if basis else None,
           "single_server_knobs": knobs_for(single["rec"]["level"]) if single else None,
           "slack": basis["slack"] if basis and basis["path"] == "router" else None,
           "knobs_now": knobs_now}
    (results / "summary.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    (results / "summary.md").write_text(render(res), encoding="utf-8")
    return res


def _f(v, nd=2):
    return "—" if v is None else (f"{v:.{nd}f}" if isinstance(v, float) else str(v))


def render(res: dict) -> str:
    out = ["# LLM 풀 용량 측정 — 결과", "",
           "| 변형 | 경로 | 붙임 문턱 | 동시 | 완료 | 실패 | 미완료 | TTFT p50 (s) | TTFT p95 (s) | ITL p50 (ms) | ITL p95 (ms) | 출력 tok/s | 요청/s | 판정 |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for v in res["variants"]:
        verdict = {lv: (st, why) for lv, st, why in v["rec"]["verdicts"]}
        for r in v["rows"]:
            st, why = verdict.get(r["level"], ("", ""))
            mark = {"ok": "✓", "stop": f"✗ {why}", "after": "—"}.get(st, "")
            out.append(f"| {v['name']} | {v['path']} | {v['slack'] or '—'} | {r['level']} | {r['ok']} | {r['errored']} | {r['incomplete']} | "
                       f"{_f(r['ttft_p50_s'])} | {_f(r['ttft_p95_s'])} | {_f(r['itl_p50_ms'], 1)} | {_f(r['itl_p95_ms'], 1)} | "
                       f"{_f(r['out_tok_s'], 1)} | {_f(r['req_s'], 3)} | {mark} |")
    out += ["", "## 변형마다", ""]
    for v in res["variants"]:
        lim = v["rec"]["limit_s"]
        cache = v["prefix_cache_hit_ratio"]
        lb, rt = v["labels"], v.get("routing")
        out.append(f"- **{v['name']}** — 권장 C {v['rec']['level'] or '없음'} · TTFT p95 한도 {_f(lim)}초"
                   + (f" · 이 변형 동안 접두 캐시 적중 {cache:.1%}" if cache is not None else "")
                   + (f" · 부하 프롬프트 {lb['prompt_tokens']}(앞부분 {lb.get('prefix_tokens', '0')} × {lb.get('prefix_count', '0')}종) · "
                      f"출력 {lb.get('output_tokens', '?')} 토큰" if "prompt_tokens" in lb else "")
                   + (f" · 라우터가 보낸 수 서버별 {'·'.join(map(str, rt['sent']))} · 붙음 {rt['sticky']} · 넘침 {rt['overflow']}" if rt else "")
                   + {True: " · ⚠ 이 변형 동안 카드 대조·심의가 돌았다 — 흐려진 값이다(조용할 때 다시 잰다)",
                      None: " · 이 변형 동안 다른 일이 돌았는지 모른다(에이전트 서버 /health 를 못 읽었다)", False: ""}[v.get("interference")])
    out += ["", "## 권장", ""]
    if res["knobs"]:
        now = res.get("knobs_now")
        out.append(f"기준 변형 **{res['basis']}**" + (f" · 붙임 문턱 `LLM_ROUTER_STICKY_SLACK={res['slack']}`" if res["slack"] else ""))
        out.append("")
        for k, v in res["knobs"].items():
            was = "" if now is None else (f"  (지금 {now[k]})" if k in now else f"  (지금 적힌 값 없음 — 코드 기본 {KNOB_DEFAULTS[k]})")
            out.append(f"- `{k}={v}`{was}")
        if res["single_server_knobs"]:
            ss = res["single_server_knobs"]
            out.append(f"- 서버 하나로 줄어드는 날(정비) — {' · '.join(f'{k}={v}' for k, v in ss.items())}")
    else:
        out.append("권장 없음 — 가장 낮은 단계부터 규칙에 어긋났다. 손잡이를 그대로 두고 표의 ✗ 까닭을 본다.")
    out += ["", "## 규칙", "", res["rule"], ""]
    return "\n".join(out)


# ── 명령 ──────────────────────────────────────────────────────────────────────────────────────────
def _levels(s: str) -> list:
    vals = [int(x) for x in s.replace(",", " ").split()]
    if not vals or any(v < 1 for v in vals) or len(set(vals)) != len(vals):
        raise argparse.ArgumentTypeError("동시 수는 1 이상의 서로 다른 정수들이다(예: '1 2 4 8')")
    return sorted(vals)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="LLM 풀 용량 측정 계산(llm-capacity.sh 가 부른다)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scenario")
    s.add_argument("--lengths", required=True, type=Path)
    s.add_argument("--kind", default="all")
    s.add_argument("--target", required=True)
    s.add_argument("--levels", required=True, type=_levels)
    s.add_argument("--requests", type=int, default=0)
    s.add_argument("--min-requests", type=int, default=10)
    s.add_argument("--max-seconds", type=float, default=900.0)
    s.add_argument("--prefix-share", type=float, default=0.5)
    s.add_argument("--prefix-count", type=int, default=0)
    s.add_argument("--tokenizer", default=TOKENIZER_IN_SIF)
    s.add_argument("--timeout", type=float, default=1800.0)
    s.add_argument("--report", required=True)
    s.add_argument("--label", action="append", default=[])
    s.add_argument("--seed", type=int, help="합성 글의 씨앗(기본 실행마다 새로 — 변형끼리 같은 프롬프트를 다시 보내지 않게)")
    s.add_argument("--out", required=True, type=Path)
    m = sub.add_parser("metrics")
    m.add_argument("--out", required=True, type=Path)
    m.add_argument("urls", nargs="+")
    bz = sub.add_parser("busy")
    bz.add_argument("url")
    ac = sub.add_parser("activity")
    ac.add_argument("url")
    ac.add_argument("--out", required=True, type=Path)
    w = sub.add_parser("wait-router")
    w.add_argument("url")
    w.add_argument("--expect", type=int, required=True)
    w.add_argument("--timeout", type=float, default=60.0)
    z = sub.add_parser("summarize")
    z.add_argument("results", type=Path)
    z.add_argument("--ttft-ratio", type=float, default=3.0)
    z.add_argument("--ttft-max-s", type=float)
    z.add_argument("--growth", type=float, default=0.05)
    z.add_argument("--now", action="append", default=[], help="세 손잡이의 지금 값 KEY=수(llm-capacity.sh 가 정본 독자로 읽어 넘긴다)")
    a = ap.parse_args(argv)
    if a.cmd == "scenario":
        if not 0 <= a.prefix_share < 1:
            print("[capacity] --prefix-share 는 0 이상 1 미만이다", file=sys.stderr)
            return 2
        labels = dict(x.split("=", 1) for x in a.label if "=" in x)
        try:
            sc, info = scenario(json.loads(a.lengths.read_text(encoding="utf-8")), kind=a.kind, target=a.target, levels=a.levels,
                                requests=a.requests, min_requests=a.min_requests, max_seconds=a.max_seconds,
                                prefix_share=a.prefix_share, prefix_count=a.prefix_count, tokenizer=a.tokenizer, report=a.report,
                                labels=labels, timeout_s=a.timeout,
                                seed=a.seed if a.seed is not None else int.from_bytes(os.urandom(4), "big"))
        except LengthsError as exc:
            print(f"[capacity] ✗ {exc}", file=sys.stderr)
            return 2
        a.out.write_text(json.dumps(sc, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[capacity] 부하 — 카드 대조 {info['kind']} · 프롬프트 {info['prompt_tokens']}(앞부분 {info['prefix_tokens']} × "
              f"{info['prefix_count']}종) · 출력 {info['output_tokens']} 토큰 · 동시 {info['levels']} · 요청 {info['requests']}")
        if not info["sticky_key_from_prefix"]:
            print(f"[capacity] ⚠ 앞부분이 {STICKY_KEY_TOKENS} 토큰보다 짧다 — 라우터 붙임 열쇠(앞 8,000자)에 요청마다 다른 글이 섞여 붙임 문턱 "
                  "변형끼리 차이가 나지 않는다(붙임 효과는 재지 못한다)")
        return 0
    if a.cmd == "metrics":
        a.out.write_text(json.dumps(snapshot(a.urls)), encoding="utf-8")
        return 0
    if a.cmd == "activity":
        a.out.write_text(json.dumps(activity(a.url)), encoding="utf-8")
        return 0
    if a.cmd in ("busy", "wait-router"):
        rc, msg = busy(a.url) if a.cmd == "busy" else wait_router(a.url, a.expect, a.timeout)
        print(msg)
        return rc
    now = {k: int(v) for k, v in (x.split("=", 1) for x in a.now if "=" in x) if k in KNOB_DEFAULTS and v.isdigit()}
    res = summarize(a.results, ttft_ratio=a.ttft_ratio, ttft_max_s=a.ttft_max_s, growth=a.growth, knobs_now=now)
    print(render(res))
    return 0 if res["variants"] else 1


if __name__ == "__main__":
    sys.exit(main())
