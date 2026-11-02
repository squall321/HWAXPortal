# Prometheus 글(텍스트 꼴)을 게이지 · 카운터 · 히스토그램 · 라벨까지 읽고 vLLM 지표 · 증가분 · 분위수를 셈하는 해석기 — 표준 라이브러리만(docs/ops-dashboard PLAN §3.3)
"""LLM 라우터의 해석기(infra/llm-router/llm_router.py parse_metrics)를 넓힌 것이다. 라우터 것은 고치지 않는다 — 라우터 지문(services.yaml
fp: infra/llm-router)에 들어 있어 바꾸면 라우터가 다시 뜬다(docs/ops-dashboard OD-13). 대신 같은 견본에서 running · waiting · KV 가 라우터와
**글자 그대로 같은지** 시험이 본다(backend/tests/test_llm_status_collector.py).

읽는 꼴 — `# HELP` · `# TYPE` · 표본 줄 `이름{라벨="값",…} 값 [시각]`. 라벨 값의 이스케이프(\\\\ \\" \\n)를 푼다. 값은 실수 · NaN · +Inf · -Inf 이고
시각은 버린다. 틀린 줄은 세고(bad) 버린다 — 한 줄 때문에 지표 전체를 잃지 않는다.

셈하는 규칙.
  · 이름은 **정확히** 같은 것만 센다 — vLLM 은 `vllm:num_requests_waiting_by_reason{reason=…}` 도 내고 그 합이 waiting 과 같아서 접두로 세면
    두 배가 된다. 라벨 묶음(엔진 · 모델)은 더한다. 대체 이름이 있는 것(옛 vLLM)은 새 이름이 있으면 옛 이름을 보지 않는다(둘을 더하지 않는다).
  · 카운터의 증가분은 이웃한 표본 쌍마다 잰다. 값이 줄어든 쌍(서버가 다시 떠서 0 부터 센다)은 **빈칸**이다 — 음수 속도를 만들지 않고, 리셋 뒤
    값을 0 부터의 증가로 치지도 않는다. 시각이 거꾸로 가거나 너무 벌어진 쌍도 빈칸이다. 어느 표본끼리 쌍을 짓나(같은 서버 프로세스 — `ident`)는
    수집기가 정한다(collector.py derive · docs/ops-dashboard OD-26).
  · 분위수(p50 · p95)는 히스토그램 칸의 증가분으로 셈한 어림이다(Prometheus histogram_quantile 과 같은 칸 안 선형 보간). 화면은 ≈ 를 붙인다.
"""
import math
import re
from typing import NamedTuple

_NAME = re.compile(r"[A-Za-z_:][A-Za-z0-9_:]*")
_LABEL = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
# 실수 · NaN · ±Inf — float() 가 받는 1_000 · 0x · infinity 같은 꼴은 지표 글이 아니다
_NUM = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?|[+-]?Inf|NaN")
_TS = re.compile(r"-?[0-9]+(?:\.[0-9]*)?")
_ESC = {"\\": "\\", '"': '"', "n": "\n"}
_WS = " \t"


class Sample(NamedTuple):
    name: str
    labels: tuple[tuple[str, str], ...]
    value: float

    def label(self, key: str) -> str | None:
        return next((v for k, v in self.labels if k == key), None)


class Parsed(NamedTuple):
    types: dict[str, str]           # # TYPE 줄 — 패밀리 이름 → counter · gauge · histogram · summary · untyped
    samples: list[Sample]
    bad: int                        # 읽지 못하고 버린 줄 수
    index: dict[str, list[Sample]]  # 이름 → 표본들(읽을 때 한 번 만든다 — 대상마다 15초에 수천 줄을 스무 번 훑지 않게)

    def named(self, name: str) -> list[Sample]:
        return self.index.get(name, [])


class Hist(NamedTuple):
    """한 히스토그램(라벨 묶음을 더한 것) — bounds 는 오름차순 칸 위끝(마지막은 +Inf), cum 은 그 칸까지의 누적 수."""
    bounds: tuple[float, ...]
    cum: tuple[float, ...]
    count: float
    total: float | None             # _sum(초 합) — 없으면 None


def _value(tok: str) -> float | None:
    if not _NUM.fullmatch(tok):
        return None
    return float(tok.replace("Inf", "inf"))


def _sample(ln: str) -> Sample | None:
    """표본 줄 하나 → Sample. 모양이 틀리면 None."""
    m = _NAME.match(ln)
    if not m:
        return None
    name, i, n = m.group(0), m.end(), len(ln)
    labels: list[tuple[str, str]] = []
    if i < n and ln[i] == "{":
        i += 1
        while True:
            while i < n and ln[i] in _WS:
                i += 1
            if i < n and ln[i] == "}":
                i += 1
                break
            lm = _LABEL.match(ln, i)
            if not lm:
                return None
            key, i = lm.group(0), lm.end()
            while i < n and ln[i] in _WS:
                i += 1
            if i >= n or ln[i] != "=":
                return None
            i += 1
            while i < n and ln[i] in _WS:
                i += 1
            if i >= n or ln[i] != '"':
                return None
            i += 1
            buf: list[str] = []
            while True:
                if i >= n:
                    return None
                c = ln[i]
                if c == "\\":
                    if i + 1 >= n:
                        return None
                    buf.append(_ESC.get(ln[i + 1], "\\" + ln[i + 1]))
                    i += 2
                elif c == '"':
                    i += 1
                    break
                else:
                    buf.append(c)
                    i += 1
            labels.append((key, "".join(buf)))
            while i < n and ln[i] in _WS:
                i += 1
            if i < n and ln[i] == ",":
                i += 1
                continue
            if i < n and ln[i] == "}":
                i += 1
                break
            return None
    rest = ln[i:]
    if not rest or rest[0] not in _WS:
        return None
    toks = rest.split()
    if not 1 <= len(toks) <= 2 or (len(toks) == 2 and not _TS.fullmatch(toks[1])):
        return None
    v = _value(toks[0])
    return None if v is None else Sample(name, tuple(labels), v)


def parse(text: str) -> Parsed:
    """Prometheus 글 → Parsed. 줄은 개행으로만 나눈다(라우터 · update-all 독자와 같다)."""
    types: dict[str, str] = {}
    samples: list[Sample] = []
    index: dict[str, list[Sample]] = {}
    bad = 0
    for raw in (text or "").split("\n"):
        ln = raw.strip()
        if not ln:
            continue
        if ln.startswith("#"):
            parts = ln.split(None, 3)
            if len(parts) >= 4 and parts[1] == "TYPE" and _NAME.fullmatch(parts[2]):
                types[parts[2]] = parts[3].strip()
            continue
        s = _sample(ln)
        if s is None:
            bad += 1
        else:
            samples.append(s)
            index.setdefault(s.name, []).append(s)
    return Parsed(types, samples, bad, index)


# ── vLLM 지표 ──────────────────────────────────────────────────────────────────────────────────────
RUNNING, WAITING = "vllm:num_requests_running", "vllm:num_requests_waiting"
KV_NAMES = ("vllm:kv_cache_usage_perc", "vllm:gpu_cache_usage_perc")   # 새 이름 먼저 — 옛 vLLM 은 뒤의 이름만 낸다(라우터와 같다)
# 카운터 — 이름 하나이거나(새 이름, 옛 이름) 순서. 라벨 묶음을 더한다.
COUNTERS: dict[str, tuple[str, ...]] = {
    "prompt_tokens": ("vllm:prompt_tokens_total",),
    "generation_tokens": ("vllm:generation_tokens_total",),
    "preemptions": ("vllm:num_preemptions_total",),
    "prefix_queries": ("vllm:prefix_cache_queries_total", "vllm:gpu_prefix_cache_queries_total"),
    "prefix_hits": ("vllm:prefix_cache_hits_total", "vllm:gpu_prefix_cache_hits_total"),
}
# 라벨 값마다 나눠 세는 카운터 — 끝난 요청의 까닭(stop · length · abort · …), HTTP 답의 묶음(2xx · 4xx · 5xx)
BY_LABEL: dict[str, tuple[str, str]] = {
    "finished": ("vllm:request_success_total", "finished_reason"),
    "http": ("http_requests_total", "status"),
}
HISTOGRAMS: dict[str, str] = {
    "ttft": "vllm:time_to_first_token_seconds",
    "e2e": "vllm:e2e_request_latency_seconds",
    "queue": "vllm:request_queue_time_seconds",
}
# 서버 프로세스의 표지 — prometheus_client 기본 레지스트리(ProcessCollector)가 내는, 그 프로세스가 뜬 때(초 · 라벨 없음)
IDENT = "process_start_time_seconds"


def _finite(samples: list[Sample]) -> list[float]:
    return [s.value for s in samples if math.isfinite(s.value)]


def basic(p: Parsed) -> dict[str, float | None] | None:
    """{running, waiting, kv} — llm_router.parse_metrics 와 같은 셈이다(같은 견본으로 대조한다). running · waiting 은 정확한 이름의 유한한
    표본을 라벨 묶음 전부 더하고, 둘 중 하나라도 없으면 None(vLLM 지표가 아니다). KV 는 있는 이름 가운데 새 이름 먼저 · 가장 큰 값."""
    run, wait = _finite(p.named(RUNNING)), _finite(p.named(WAITING))
    if not run or not wait:
        return None
    kv = next((max(v) for v in (_finite(p.named(n)) for n in KV_NAMES) if v), None)
    return {"running": sum(run), "waiting": sum(wait), "kv": kv}


def _counter(p: Parsed, names: tuple[str, ...]) -> float | None:
    for n in names:
        vals = _finite(p.named(n))
        if vals:
            return sum(vals)
    return None


def _by_label(p: Parsed, name: str, key: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for s in p.named(name):
        lab = s.label(key)
        if lab is not None and math.isfinite(s.value):
            out[lab] = out.get(lab, 0.0) + s.value
    return out


def _bound(le: str | None) -> float | None:
    if le is None:
        return None
    v = _value(le.strip())
    return v if v is not None and not math.isnan(v) else None


def histogram(p: Parsed, base: str) -> Hist | None:
    """`<base>_bucket{le=…}` · `_count` · `_sum` → Hist(라벨 묶음을 칸마다 더한다). 칸이 없거나 누적이 줄어들거나(묶음마다 칸이 달라 더할 수
    없다) +Inf 칸이 없으면 None."""
    by_le: dict[float, float] = {}
    for s in p.named(base + "_bucket"):
        b = _bound(s.label("le"))
        if b is None or not math.isfinite(s.value):
            continue
        by_le[b] = by_le.get(b, 0.0) + s.value
    if not by_le:
        return None
    bounds = tuple(sorted(by_le))
    cum = tuple(by_le[b] for b in bounds)
    if bounds[-1] != math.inf or any(y < x for x, y in zip(cum, cum[1:])):
        return None
    count = _counter(p, (base + "_count",))
    return Hist(bounds, cum, cum[-1] if count is None else count, _counter(p, (base + "_sum",)))


def ident(p: Parsed) -> float | None:
    """그 서버 프로세스의 표지 — 라벨 없는 유한한 IDENT 표본이 정확히 하나일 때 그 값, 아니면 None(표지 없음). 같은 프로세스는 늘 같은 값을
    낸다(부팅 시각을 한 번 읽어 둔다 — prometheus_client process_collector). 다시 뜨면 바뀐다. vLLM 0.23.0 은 API 서버가 하나면 기본 레지스트리라
    이 줄이 있고, api_server_count > 1 이면 다중 프로세스 레지스트리라 없다(vllm/v1/metrics/prometheus.py get_prometheus_registry)."""
    vals = [s.value for s in p.named(IDENT) if not s.labels and math.isfinite(s.value)]
    return vals[0] if len(vals) == 1 else None


def vllm(p: Parsed) -> dict | None:
    """vLLM 지표 전부 — {gauges: {running, waiting, kv}, counters: {이름: 값|None}, by_label: {finished, http}, hists: {ttft, e2e, queue},
    ident: 프로세스 표지|None}. running · waiting 이 없으면 None(그 서버의 글이 vLLM 지표가 아니다 — 404 페이지 · 다른 앱)."""
    g = basic(p)
    if g is None:
        return None
    return {"gauges": g,
            "counters": {k: _counter(p, names) for k, names in COUNTERS.items()},
            "by_label": {k: _by_label(p, name, key) for k, (name, key) in BY_LABEL.items()},
            "hists": {k: histogram(p, base) for k, base in HISTOGRAMS.items()},
            "ident": ident(p)}


# ── 증가분 · 분위수 ─────────────────────────────────────────────────────────────────────────────────
def counter_delta(a: float | None, b: float | None) -> float | None:
    """이웃한 두 표본의 증가 — 줄었으면(리셋) None(빈칸). 음수를 내지 않는다."""
    if a is None or b is None or not (math.isfinite(a) and math.isfinite(b)) or b < a:
        return None
    return b - a


def hist_delta(a: Hist | None, b: Hist | None) -> Hist | None:
    """두 히스토그램의 증가 — 칸이 같고 모든 칸 · 수가 줄지 않았을 때만. 아니면 None(리셋이거나 칸이 바뀌었다 — 빈칸)."""
    if a is None or b is None or a.bounds != b.bounds:
        return None
    if b.count < a.count or any(y < x for x, y in zip(a.cum, b.cum)):
        return None
    tot = None if a.total is None or b.total is None or b.total < a.total else b.total - a.total
    return Hist(b.bounds, tuple(y - x for x, y in zip(a.cum, b.cum)), b.count - a.count, tot)


def hist_add(a: Hist | None, b: Hist) -> Hist:
    if a is None:
        return b
    tot = None if a.total is None or b.total is None else a.total + b.total
    return Hist(b.bounds, tuple(x + y for x, y in zip(a.cum, b.cum)), a.count + b.count, tot)


def quantile(q: float, h: Hist | None) -> float | None:
    """히스토그램 칸으로 어림한 q 분위수(초) — Prometheus histogram_quantile 과 같다. 들어온 것이 없으면 None. 순위가 +Inf 칸에 떨어지면
    그 앞 칸의 위끝을 낸다(더 큰 값은 칸이 말해 주지 않는다)."""
    if h is None or not h.cum or h.cum[-1] <= 0 or not 0.0 <= q <= 1.0:
        return None
    rank = q * h.cum[-1]
    i = next((j for j, c in enumerate(h.cum) if c >= rank), len(h.cum) - 1)
    if h.bounds[i] == math.inf:
        return h.bounds[i - 1] if i > 0 else None
    lower = h.bounds[i - 1] if i > 0 else 0.0
    prev = h.cum[i - 1] if i > 0 else 0.0
    inside = h.cum[i] - prev
    if inside <= 0:
        return h.bounds[i]
    return lower + (h.bounds[i] - lower) * (rank - prev) / inside
