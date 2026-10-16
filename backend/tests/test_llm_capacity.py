# LLM 풀 용량 측정 — 시나리오 · 권장 규칙 · 요약 · 실행 스크립트의 인자와 키(argv 에 없다) · 측정용 라우터(llm-capacity.py · llm-capacity.sh, docs/llm-pool/capacity.md)
"""왜 — 권장 규칙은 사람이 세 손잡이를 고치는 근거라, 규칙의 조항 하나가 빠져도 조용히 큰 값을 권한다. 조항마다 그것만 어긋나는 결과를 만든다.

실행 스크립트는 가짜 apptainer(argv·환경을 적고 안의 명령을 흉내 낸다)로 끝까지 돌린다 — 측정용 라우터는 **진짜** llm_router 를 이 venv 로
띄우고(가짜 vLLM 둘 앞에서), GuideLLM 자리는 시나리오의 대상으로 실제 요청을 보낸 뒤 정해 둔 보고서를 쓴다. 키가 어느 argv 에도 없는지,
그래도 가짜 vLLM 까지 Bearer 로 닿는지(직결·라우터 둘 다), 라우터 설정 파일이 600 이고 끝나면 사라지는지, 운영 라우터 포트를 쓰지 않는지 본다.
주소는 루프백만 쓴다(내부 IP 는 추적 파일 금지). 진짜 GuideLLM 실주행은 이 시험에 없다 — dev vLLM 스모크로 한 번 했다(capacity.md 8절).
"""
import http.server
import importlib.util
import json
import shutil
import socket
import subprocess
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CAP_PY = ROOT / "infra/scripts/llm-capacity.py"
CAP_SH = ROOT / "infra/scripts/llm-capacity.sh"
KEY = "sk-capacity-test-key-7f3a9c"      # 머리(latin-1)로 가는 값이라 ASCII 다


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    keep, sys.dont_write_bytecode = sys.dont_write_bytecode, True     # infra/scripts 에 __pycache__ 를 남기지 않는다
    try:
        spec.loader.exec_module(m)
    finally:
        sys.dont_write_bytecode = keep
    return m


C = _load(CAP_PY, "hwax_llm_capacity")


# ── 시나리오 ────────────────────────────────────────────────────────────────────────────────────────
def _lengths(prompt=None, output=None, inflight=3.0) -> dict:
    p = prompt or {"n": 50, "mean": 20000.0, "std": 6000.0, "min": 3000, "p5": 9500, "p50": 18000, "p95": 32000, "max": 60000}
    o = output or {"n": 50, "mean": 600.0, "std": 150.0, "min": 50, "p5": 300, "p50": 580, "p95": 900, "max": 1500}
    return {"card_review": {"all": {"prompt_tokens": p, "output_tokens": o},
                            "by_kind": {"verdict": {"prompt_tokens": p, "output_tokens": o}},
                            "experts_in_flight": {"n": 9, "p50": inflight}}}


def _scn(lengths, **kw):
    args = dict(kind="all", target="http://127.0.0.1:1/v1", levels=[1, 2, 4], requests=0, min_requests=10, max_seconds=900,
                prefix_share=0.5, prefix_count=0, tokenizer="/opt/tokenizers/glm-5.2", report="/r/benchmarks.json",
                labels={"path": "direct"}, timeout_s=1800, seed=7)
    args.update(kw)
    return C.scenario(lengths, **args)


def test_시나리오는_분포로_합성_부하를_만들고_앞부분을_뗀다():
    sc, info = _scn(_lengths())
    d = sc["spec"]["data"][0]
    assert d["prefix_buckets"] == [{"prefix_count": 3, "prefix_tokens": 9000}], "앞부분 = 중앙값 × 0.5, 종류 = 돌던 전문가 중앙값"
    assert (d["prompt_tokens"], d["prompt_tokens_min"], d["prompt_tokens_max"], d["prompt_tokens_stdev"]) == (11000, 500, 23000, 6000), \
        "고유 부분 = 분포 − 앞부분"
    assert (d["output_tokens"], d["output_tokens_min"], d["output_tokens_max"], d["output_tokens_stdev"]) == (600, 300, 900, 150)
    assert sc["spec"]["constraints"] == [{"kind": "max_requests", "count": [10, 10, 12]}, {"kind": "max_duration", "seconds": 900}]
    assert sc["spec"]["profile"]["warmup"] == {"percent": 0.33, "mode": "requests"}, "첫 물결은 빼고 잰다 — 요청 수로"
    assert sc["spec"]["metrics"] == {"kind": "generative", "sample_size": 0}, "요청마다의 글을 결과에 남기지 않는다"
    assert sc["spec"]["seed"]["value"] == 7 and sc["spec"]["backend"]["http2"] is False
    assert "api_key" not in json.dumps(sc), "키는 시나리오에 싣지 않는다(환경으로만)"
    assert all(isinstance(v, str) for v in sc["metadata"]["labels"].values()) and info["sticky_key_from_prefix"] is True


def test_시나리오의_앞부분은_가장_짧은_프롬프트를_넘지_않고_없으면_4종이다():
    small = {"n": 9, "mean": 400.0, "std": 0.4, "min": 100, "p5": 150, "p50": 800, "p95": 900, "max": 999}
    lengths = _lengths(prompt=small)
    del lengths["card_review"]["experts_in_flight"]
    sc, info = _scn(lengths)
    d = sc["spec"]["data"][0]
    assert d["prefix_buckets"] == [{"prefix_count": 4, "prefix_tokens": 149}] and d["prompt_tokens_min"] == 1
    assert "prompt_tokens_stdev" not in d, "표준편차가 1 아래면 싣지 않는다(GuideLLM 은 0 을 받지 않는다)"
    assert info["sticky_key_from_prefix"] is False
    sc0, info0 = _scn(_lengths(), prefix_share=0)
    assert "prefix_buckets" not in sc0["spec"]["data"][0] and info0["prefix_count"] == 0
    assert C.requests_per_level([1, 2, 4, 8, 24], 0, 10) == [10, 10, 12, 24, 72] and C.requests_per_level([1, 8], 3, 10) == [3, 3]


def test_시나리오는_카드_대조_분포가_없으면_멈춘다(tmp_path):
    with pytest.raises(C.LengthsError):
        _scn({"card_review": {}})
    with pytest.raises(C.LengthsError):
        _scn(_lengths(), kind="sweep")
    f = tmp_path / "l.json"
    f.write_text(json.dumps({"card_review": {}}), encoding="utf-8")
    r = subprocess.run([sys.executable, str(CAP_PY), "scenario", "--lengths", str(f), "--target", "http://127.0.0.1:1/v1", "--levels", "1",
                        "--report", "x", "--out", str(tmp_path / "s.json")], capture_output=True, text=True, timeout=60)
    assert r.returncode == 2 and "카드 대조" in r.stderr and not (tmp_path / "s.json").exists()


# ── 결과 읽기 · 권장 규칙 ─────────────────────────────────────────────────────────────────────────────
def _dist(p50, p95, mean=None):
    return {"mean": mean if mean is not None else p50, "median": p50, "count": 5,
            "percentiles": {"p05": p50, "p50": p50, "p95": p95, "p99": p95}}


def _bench(level, *, ok=10, err=0, inc=0, ttft_p50_ms=1000.0, ttft_p95_ms=1500.0, rps=1.0, otps=100.0):
    """GuideLLM 0.8.0 보고서의 벤치마크 하나와 같은 모양(쓰는 칸만) — dev 스모크의 실제 보고서에서 옮겼다."""
    m = {"request_totals": {"successful": ok, "errored": err, "incomplete": inc, "total": ok + err + inc},
         "requests_per_second": {"successful": _dist(rps, rps, rps)},
         "time_to_first_token_ms": {"successful": _dist(ttft_p50_ms, ttft_p95_ms)},
         "inter_token_latency_ms": {"successful": _dist(20.0, 30.0)},
         "output_tokens_per_second": {"successful": _dist(otps, otps, otps)},
         "prompt_token_count": {"successful": _dist(20000, 30000, 21000)},
         "output_token_count": {"successful": _dist(600, 900, 610)}}
    return {"type_": "generative_benchmark", "config": {"strategy": {"type_": "concurrent", "streams": level, "max_concurrency": level}},
            "metrics": m, "duration": 60.0}


def _rows(*benches):
    return C.report_rows({"benchmarks": list(benches)})


def test_보고서는_동시_수마다_한_줄이고_초와_ms_로_바꾼다():
    rows = _rows(_bench(4, ttft_p50_ms=2000, ttft_p95_ms=5000, rps=2.5, otps=300, err=1, inc=2), _bench(1))
    assert [r["level"] for r in rows] == [1, 4]
    r = rows[1]
    assert (r["ttft_p50_s"], r["ttft_p95_s"], r["req_s"], r["out_tok_s"], r["errored"], r["incomplete"]) == (2.0, 5.0, 2.5, 300, 1, 2)
    assert (r["itl_p50_ms"], r["itl_p95_ms"], r["prompt_tokens_mean"]) == (20.0, 30.0, 21000)


def test_권장은_세_조항을_다_지킨_마지막_단계다():
    rows = _rows(_bench(1, ttft_p50_ms=1000, ttft_p95_ms=1200, rps=1.0), _bench(2, ttft_p95_ms=1500, rps=1.9),
                 _bench(4, ttft_p95_ms=2900, rps=3.5), _bench(8, ttft_p95_ms=2950, rps=3.6))
    rec = C.recommend(rows)
    assert rec["level"] == 4 and rec["limit_s"] == 3.0
    assert rec["verdicts"][-1][:2] == (8, "stop") and "요청/초" in rec["verdicts"][-1][2], "4 → 8 에서 요청/초가 5% 미만 늘었다"


def test_권장은_TTFT_p95_가_한도를_넘으면_멈춘다_p50_이_아니다():
    rows = _rows(_bench(1, ttft_p50_ms=1000, ttft_p95_ms=1100, rps=1.0), _bench(2, ttft_p50_ms=1100, ttft_p95_ms=3100, rps=2.0))
    rec = C.recommend(rows)
    assert rec["level"] == 1 and "TTFT" in rec["verdicts"][1][2]
    assert C.recommend(rows, ttft_max_s=3.2)["level"] == 2, "절대 한도를 주면 그 초로 본다"
    assert C.recommend(rows, ttft_ratio=3.2)["level"] == 2


def test_권장은_처음_어긋난_뒤의_단계를_받지_않는다():
    rows = _rows(_bench(1, rps=1.0), _bench(2, rps=1.0), _bench(4, rps=5.0))
    rec = C.recommend(rows)
    assert rec["level"] == 1 and [v[1] for v in rec["verdicts"]] == ["ok", "stop", "after"]


def test_권장은_실패한_요청이_있으면_멈추고_미완료는_실패로_치지_않는다():
    rows = _rows(_bench(1, rps=1.0), _bench(2, rps=2.0, inc=3), _bench(4, rps=4.0, err=1))
    rec = C.recommend(rows)
    assert rec["level"] == 2 and "실패 1" in rec["verdicts"][2][2]
    assert C.recommend(_rows(_bench(1, err=1)))["level"] is None, "첫 단계부터 어긋나면 권장이 없다"
    assert C.recommend(_rows(_bench(1, ok=0)))["level"] is None
    assert C.recommend([])["level"] is None


def test_세_손잡이는_관문_워커_C_중계_C_더하기_반올림한_절반():
    assert C.knobs_for(8) == {"CARD_REVIEW_CONCURRENCY": 8, "HWAXRISK_REVIEW_CONCURRENCY": 8, "CARD_REVIEW_MAX_STREAMS": 12}
    assert C.knobs_for(16)["CARD_REVIEW_MAX_STREAMS"] == 24 and C.knobs_for(5)["CARD_REVIEW_MAX_STREAMS"] == 8
    assert C.knobs_for(1)["CARD_REVIEW_MAX_STREAMS"] == 2


def _results(tmp_path, variants: dict, metrics: dict | None = None) -> Path:
    res = tmp_path / "res"
    for name, (labels, benches) in variants.items():
        d = res / name
        d.mkdir(parents=True)
        (d / "benchmarks.json").write_text(json.dumps({"config": {"metadata": {"labels": labels}}, "benchmarks": benches}), encoding="utf-8")
        for k, v in (metrics or {}).get(name, {}).items():
            (d / k).write_text(json.dumps(v), encoding="utf-8")
    return res


def _climb(levels, p95_step_ms, rps_step):
    return [_bench(c, ttft_p50_ms=1000, ttft_p95_ms=1000 + p95_step_ms * c, rps=rps_step * c) for c in levels]


def test_요약은_라우터_경로의_가장_큰_C_로_세_손잡이를_권하고_직결_값을_정비일_값으로_적는다(tmp_path):
    res = _results(tmp_path, {
        "direct": ({"path": "direct"}, _climb([1, 2, 4, 8], 400, 1.0)),                      # p95 1.4 · 1.8 · 2.6 · 4.2 → C 4
        "router-slack2": ({"path": "router", "slack": "2"}, _climb([1, 2, 4, 8, 12], 150, 1.0)),   # p95 … 2.2 · 2.8 → C 12
        "router-slack0": ({"path": "router", "slack": "0"}, _climb([1, 2, 4, 8, 12], 150, 1.1)),   # 같은 C 에 요청/초가 크다
    }, metrics={"router-slack2": {"metrics-before.json": [{"server": 1, "cache_queries": 100, "cache_hits": 10},
                                                         {"server": 2, "error": "URLError"}],
                                  "metrics-after.json": [{"server": 1, "cache_queries": 300, "cache_hits": 160},
                                                         {"server": 2, "cache_queries": 9e9, "cache_hits": 9e9}]}})
    out = C.summarize(res, knobs_now={"CARD_REVIEW_CONCURRENCY": 8})
    assert [v["name"] for v in out["variants"]] == ["direct", "router-slack0", "router-slack2"]
    assert out["basis"] == "router-slack0" and out["slack"] == "0", "같은 C 면 요청/초가 큰 변형"
    assert out["knobs"] == {"CARD_REVIEW_CONCURRENCY": 12, "HWAXRISK_REVIEW_CONCURRENCY": 12, "CARD_REVIEW_MAX_STREAMS": 18}
    assert out["single_server_knobs"] == {"CARD_REVIEW_CONCURRENCY": 4, "HWAXRISK_REVIEW_CONCURRENCY": 4, "CARD_REVIEW_MAX_STREAMS": 6}
    v2 = next(v for v in out["variants"] if v["name"] == "router-slack2")
    assert v2["prefix_cache_hit_ratio"] == 0.75, "한쪽을 못 읽은 서버는 빼고 센다"
    md = (res / "summary.md").read_text(encoding="utf-8")
    assert "CARD_REVIEW_MAX_STREAMS=18" in md and "(지금 8)" in md and "지금 적힌 값 없음 — 코드 기본 8" in md
    assert "처음 어긋나는 단계에서 멈추고" in md and md.count("| router-slack2 |") == 5
    assert json.loads((res / "summary.json").read_text(encoding="utf-8"))["basis"] == "router-slack0"


def test_요약은_같은_값이면_기본_문턱을_고르고_라우터가_없으면_직결로_권한다(tmp_path):
    same = _climb([1, 2, 4], 100, 1.0)
    out = C.summarize(_results(tmp_path / "a", {"router-slack0": ({"path": "router", "slack": "0"}, same),
                                                "router-slack2": ({"path": "router", "slack": "2"}, same)}))
    assert out["basis"] == "router-slack2"
    out2 = C.summarize(_results(tmp_path / "b", {"direct": ({"path": "direct"}, _climb([1, 2], 100, 1.0))}))
    assert out2["basis"] == "direct" and out2["knobs"]["CARD_REVIEW_CONCURRENCY"] == 2 and out2["slack"] is None
    out3 = C.summarize(_results(tmp_path / "c", {"direct": ({"path": "direct"}, [_bench(1, err=2)])}))
    assert out3["knobs"] is None and "권장 없음" in (tmp_path / "c" / "res" / "summary.md").read_text(encoding="utf-8")


def test_변형_앞뒤의_에이전트_서버_일로_흐려진_변형을_가린다(tmp_path):
    calm = {"review_active": 0, "delib_active": 0, "delib_queued": 0, "review_calls_total": 5}
    assert C.interference(calm, dict(calm)) is False
    assert C.interference(calm, {**calm, "review_calls_total": 6}) is True, "그 사이에 카드 대조가 돌고 끝났다"
    assert C.interference(calm, {**calm, "delib_active": 1}) is True and C.interference({**calm, "review_active": 2}, calm) is True
    assert C.interference({"error": "unreachable"}, calm) is None
    assert C.interference({**calm, "review_calls_total": None}, calm) is None
    assert C.interference({**calm, "review_calls_total": None, "delib_active": 1}, calm) is True
    res = _results(tmp_path, {"direct": ({"path": "direct"}, _climb([1, 2], 100, 1.0))},
                   metrics={"direct": {"agent-before.json": calm, "agent-after.json": {**calm, "review_calls_total": 9}}})
    out = C.summarize(res)
    assert out["variants"][0]["interference"] is True and "흐려진 값" in (res / "summary.md").read_text(encoding="utf-8")


def test_지표_읽기는_이름이_같은_줄만_라벨_묶음을_더한다():
    text = ('# HELP x\nvllm:num_requests_running{engine="0"} 2.0\nvllm:num_requests_running{engine="1"} 1.0\n'
            'vllm:num_requests_waiting{engine="0"} 0.0\nvllm:num_requests_waiting_by_reason{reason="capacity"} 5.0\n'
            'vllm:prefix_cache_queries_total{engine="0"} 1.5e+08\nvllm:prefix_cache_hits_total{engine="0"} 4e+07\n')
    assert C.parse_metrics(text) == {"running": 3.0, "waiting": 0.0, "cache_queries": 1.5e8, "cache_hits": 4e7}
    assert C.metrics_url("http://127.0.0.1:8000/v1") == "http://127.0.0.1:8000/metrics"


# ── 실행 스크립트 ───────────────────────────────────────────────────────────────────────────────────
# 가짜 apptainer — argv 와(키는 값 대신 '있다') 를 적고, `exec … <SIF> <명령>` 의 명령을 흉내 낸다. --cleanenv 처럼 빈 환경에 --env 와
# APPTAINERENV_* 만 넣는다. 라우터(python3 -m uvicorn …)는 이 venv 로 진짜로 띄우고(/workspace 를 바인드 원천으로 바꾼다), guidellm run 은
# 시나리오의 대상으로 실제 요청(모델 목록 · 채팅 하나)을 보낸 뒤 정해 둔 보고서를 쓴다.
_STUB = r'''#!__PY__
import json, os, sys, time, urllib.request
argv = sys.argv[1:]
log = open(os.environ["STUB_LOG"], "a", encoding="utf-8")
assert argv and argv[0] == "exec", argv
i, binds, envs = 1, [], {}
while argv[i].startswith("--"):
    if argv[i] == "--cleanenv":
        i += 1
    elif argv[i] in ("--bind", "--env"):
        if argv[i] == "--bind":
            binds.append(argv[i + 1])
        else:
            k, v = argv[i + 1].split("=", 1)
            envs[k] = v
        i += 2
    else:
        raise SystemExit("stub: 모르는 옵션 " + argv[i])
sif, cmd = argv[i], argv[i + 1:]
env = {"PATH": "/usr/bin:/bin", "HOME": os.environ.get("HOME", "/tmp"), **envs}
for k, v in os.environ.items():
    if k.startswith("APPTAINERENV_"):
        env[k[len("APPTAINERENV_"):]] = v
rec = {"argv": argv, "sif": os.path.basename(sif), "key_env": "GUIDELLM__SPEC__BACKEND__API_KEY" in env}
if cmd[:3] == ["python3", "-m", "uvicorn"]:
    ws = next(b.split(":", 1)[0] for b in binds if b.endswith(":/workspace"))
    ef = envs["LLM_ROUTER_ENV_FILE"]
    rec.update(router_port=int(cmd[cmd.index("--port") + 1]), router_env_file=ef, router_env_mode=oct(os.stat(ef).st_mode & 0o777),
               router_env_lines=sorted(ln.split("=", 1)[0] for ln in open(ef).read().splitlines()))
    log.write(json.dumps(rec) + "\n"); log.flush()
    args = [a.replace("/workspace", ws) for a in cmd[1:]]
    env["PYTHONPATH"] = ""
    os.execve(sys.executable, [sys.executable] + args, env)
if cmd[:2] == ["guidellm", "run"]:
    sc = json.load(open(cmd[cmd.index("--scenario") + 1]))
    spec = sc["spec"]
    target = spec["backend"]["target"].rstrip("/")
    if target.endswith("/v1"):
        target = target[:-3]
    key = env.get("GUIDELLM__SPEC__BACKEND__API_KEY")
    hdr = {"Authorization": "Bearer " + key} if key else {}
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    op.open(urllib.request.Request(target + "/v1/models", headers=hdr), timeout=10).read()
    body = json.dumps({"model": "fake", "stream": True, "max_tokens": 4,
                       "messages": [{"role": "system", "content": "앞부분"}, {"role": "user", "content": "x"}]}).encode()
    op.open(urllib.request.Request(target + "/v1/chat/completions", data=body, headers={**hdr, "content-type": "application/json"}),
            timeout=10).read()
    labels = sc["metadata"]["labels"]
    step = 150 if labels.get("path") == "router" else 400
    def d(p50, p95, mean=None):
        return {"mean": p50 if mean is None else mean, "median": p50, "count": 5, "percentiles": {"p50": p50, "p95": p95}}
    benches = []
    for c in spec["profile"]["streams"]:
        m = {"request_totals": {"successful": 10, "errored": 0, "incomplete": 0, "total": 10},
             "requests_per_second": {"successful": d(c * 1.0, c * 1.0)},
             "time_to_first_token_ms": {"successful": d(1000.0, 1000.0 + step * c)},
             "inter_token_latency_ms": {"successful": d(20.0, 30.0)}, "output_tokens_per_second": {"successful": d(c * 50.0, c * 50.0)},
             "prompt_token_count": {"successful": d(100, 120)}, "output_token_count": {"successful": d(20, 24)}}
        benches.append({"config": {"strategy": {"streams": c}}, "metrics": m, "duration": 10.0})
    out = spec["outputs"][0]["path"]
    with open(out, "w") as f:
        json.dump({"config": {"metadata": sc["metadata"]}, "benchmarks": benches}, f)
    log.write(json.dumps(rec) + "\n"); log.flush()
    print("가짜 guidellm — 보고서", out)
    sys.exit(0)
raise SystemExit("stub: 모르는 명령 " + " ".join(cmd))
'''


class _FakeVLLM:
    """가짜 vLLM — /v1/models · /metrics · /v1/chat/completions(SSE). 받은 Authorization 을 경로마다 적는다(값이 아니라 맞았는지)."""

    def __init__(self, key: str | None):
        self.auth: list = []
        fake = self

        class H(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *a):
                pass

            def _note(self):
                a = self.headers.get("Authorization")
                fake.auth.append((self.path, "match" if key and a == f"Bearer {key}" else ("none" if a is None else "other")))

            def _send(self, code, body: bytes, ctype="application/json"):
                self.send_response(code)
                self.send_header("content-type", ctype)
                self.send_header("content-length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if self.path == "/metrics":
                    self._send(200, b'vllm:num_requests_running{engine="0"} 0.0\nvllm:num_requests_waiting{engine="0"} 0.0\n'
                                    b'vllm:prefix_cache_queries_total{engine="0"} 100.0\nvllm:prefix_cache_hits_total{engine="0"} 50.0\n',
                               "text/plain")
                    return
                self._note()
                self._send(200, json.dumps({"data": [{"id": "fake", "max_model_len": 4096}]}).encode())

            def do_POST(self):
                self._note()
                self.rfile.read(int(self.headers.get("content-length") or 0))
                self._send(200, b'data: {"choices":[{"delta":{"content":"a"}}]}\n\ndata: [DONE]\n\n', "text/event-stream")

        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}/v1"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def close(self):
        self.srv.shutdown()
        self.srv.server_close()


class _FakeAgent:
    def __init__(self, review=0, delib=0):
        body = json.dumps({"status": "ok", "review_active": review, "delib_active": delib, "delib_queued": 0,
                           "card_review": {"totals": {"calls": 5}}}).encode()

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                self.send_response(200)
                self.send_header("content-length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}/health"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def close(self):
        self.srv.shutdown()
        self.srv.server_close()


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture()
def lay(tmp_path):
    """임시 리포 — 실행 스크립트 · 계산 · lib · 라우터를 진짜로 복사하고 SIF 자리는 빈 파일. infra/.env 에 키와 운영 라우터 포트."""
    repo = (tmp_path / "repo").resolve()
    (repo / "infra/scripts/lib").mkdir(parents=True)
    (repo / "infra/llm-router").mkdir(parents=True)
    (repo / "infra/apptainer").mkdir(parents=True)
    for rel in ("infra/scripts/llm-capacity.sh", "infra/scripts/llm-capacity.py", "infra/scripts/lib/llm-pool.sh",
                "infra/llm-router/llm_router.py"):
        shutil.copy(ROOT / rel, repo / rel)
    for sif in ("guidellm.sif", "portal.sif"):
        (repo / "infra/apptainer" / sif).write_text("")
    prod = _free_port()
    (repo / "infra/.env").write_text(f"LLM_API_KEY={KEY}\nLLM_ROUTER_PORT={prod}\n", encoding="utf-8")
    stub = tmp_path / "apptainer"
    stub.write_text(_STUB.replace("__PY__", sys.executable), encoding="utf-8")
    stub.chmod(0o755)
    lengths = tmp_path / "lengths.json"
    lengths.write_text(json.dumps(_lengths()), encoding="utf-8")
    log = tmp_path / "stub.jsonl"

    def run(*args, timeout=180):
        env = {"PATH": f"{Path(sys.executable).parent}:/usr/bin:/bin", "HOME": str(tmp_path), "APPTAINER": str(stub),
               "STUB_LOG": str(log), "TMPDIR": str(tmp_path), "PYTHONDONTWRITEBYTECODE": "1"}
        return subprocess.run(["bash", str(repo / "infra/scripts/llm-capacity.sh"), *args], capture_output=True, text=True,
                              env=env, timeout=timeout)

    def calls():
        return [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()] if log.exists() else []

    return {"repo": repo, "run": run, "calls": calls, "lengths": lengths, "prod": prod, "tmp": tmp_path}


@pytest.mark.parametrize("args, word", [
    ([], "--lengths"),
    (["--lengths", "/없는/파일.json"], "없다"),
    (["--lengths", "L", "--levels", "0 2"], "--levels"),
    (["--lengths", "L", "--levels", "2 2"], "두 번"),
    (["--lengths", "L", "--levels", "a"], "--levels"),
    (["--lengths", "L", "--paths", "direct bogus"], "--paths"),
    (["--lengths", "L", "--slack", "-1"], "--slack"),
    (["--lengths", "L", "--slack", "2 2"], "두 번"),
    (["--lengths", "L", "--kind", "chat"], "--kind"),
    (["--lengths", "L", "--requests", "x"], "--requests"),
    (["--lengths", "L", "--max-seconds", "0"], "--max-seconds"),
    (["--lengths", "L", "--bogus"], "모르는 인자"),
    (["--lengths"], "값이 없다"),
    (["--lengths", "L", "--upstreams", "http://10.0.0.1:8000/v1?key=x"], "질의"),
    (["--lengths", "L", "--upstreams", "http://127.0.0.1:PROD/v1"], "라우터 자신"),
    (["--lengths", "L", "--upstreams", "http://127.0.0.1:8001/v1,http://127.0.0.1:8001/v1"], "두 번"),
    (["--lengths", "L", "--upstreams", "http://127.0.0.1:8001/v1", "--direct", "nope"], "--direct"),
    (["--lengths", "L"], "잴 서버가 없다"),
])
def test_스크립트는_틀린_인자로_아무것도_부르지_않는다(lay, args, word):
    args = [a.replace("PROD", str(lay["prod"])) if "PROD" in a else (str(lay["lengths"]) if a == "L" else a) for a in args]
    r = lay["run"](*args)
    assert r.returncode == 2 and word in r.stderr, (args, r.returncode, r.stdout, r.stderr)
    assert lay["calls"]() == [], "apptainer 를 불렀다"
    assert KEY not in r.stdout + r.stderr


def test_dry_run_은_계획만_찍고_아무것도_부르지_않는다(lay):
    r = lay["run"]("--lengths", str(lay["lengths"]), "--upstreams", "http://127.0.0.1:8001/v1,http://127.0.0.1:8002/v1", "--dry-run")
    assert r.returncode == 0, r.stderr
    assert "변형 — direct router-slack2 router-slack0" in r.stdout and "직결 대상 http://127.0.0.1:8001/v1" in r.stdout
    assert "최대 212건 × 변형 3" in r.stdout and "LLM_API_KEY 를 환경으로만" in r.stdout and KEY not in r.stdout + r.stderr
    assert lay["calls"]() == [] and not (lay["repo"] / "infra/.state").exists()
    assert not [p for p in lay["tmp"].iterdir() if p.name.startswith("tmp.")], "임시 디렉터리를 남겼다"


def test_도는_심의가_있으면_재지_않는다(lay):
    agent = _FakeAgent(delib=1)
    try:
        r = lay["run"]("--lengths", str(lay["lengths"]), "--upstreams", "http://127.0.0.1:8001/v1", "--agent-health", agent.url,
                       "--out", str(lay["tmp"] / "res"))
    finally:
        agent.close()
    assert r.returncode == 3 and "심의 1건이 돈다" in r.stderr and "--force" in r.stderr
    assert lay["calls"]() == [] and not (lay["tmp"] / "res").exists(), "재지 않았으면 결과 디렉터리도 만들지 않는다"
    dead = f"http://127.0.0.1:{_free_port()}/health"
    r2 = lay["run"]("--lengths", str(lay["lengths"]), "--upstreams", "http://127.0.0.1:8001/v1", "--agent-health", dead,
                    "--out", str(lay["tmp"] / "res2"))
    assert r2.returncode == 3 and "모른다" in r2.stderr and lay["calls"]() == []


def test_끝까지_돌고_키는_어느_argv_에도_없이_환경으로만_서버에_닿는다(lay):
    a, b, agent = _FakeVLLM(KEY), _FakeVLLM(KEY), _FakeAgent()
    out = lay["tmp"] / "res"
    try:
        r = lay["run"]("--lengths", str(lay["lengths"]), "--upstreams", f"{a.url},{b.url}", "--levels", "1 2 4 8 12",
                       "--agent-health", agent.url, "--out", str(out))
    finally:
        for s in (a, b, agent):
            s.close()
    assert r.returncode == 0, r.stdout + r.stderr
    calls = lay["calls"]()
    guide = [c for c in calls if "guidellm" in c["argv"]]
    routers = [c for c in calls if "router_port" in c]
    assert len(guide) == 3 and len(routers) == 2, calls
    for c in calls:
        assert not any(KEY in x for x in c["argv"]), f"키가 argv 에 있다: {c['argv']}"
    assert all(c["key_env"] for c in guide), "GuideLLM 에 키가 환경으로 가지 않았다"
    assert all(c["sif"] == "guidellm.sif" for c in guide) and all(c["sif"] == "portal.sif" for c in routers)
    for c in routers:
        assert c["router_port"] != lay["prod"] and c["router_port"] != 9130, "운영 라우터 포트에 띄웠다"
        assert c["router_env_mode"] == "0o600", c
        assert c["router_env_lines"] == ["LLM_API_KEY", "LLM_ROUTER_STICKY_SLACK", "LLM_UPSTREAMS"]
        assert not Path(c["router_env_file"]).exists(), "키가 든 라우터 설정 파일이 남았다"
        with socket.socket() as s:
            assert s.connect_ex(("127.0.0.1", c["router_port"])) != 0, "측정용 라우터가 내려가지 않았다"
    # 키는 서버까지 Bearer 로 닿는다 — 직결은 첫 서버에, 라우터 경로는 라우터를 지나(라우터 자신의 /v1/models 대조도 같은 키)
    assert ("/v1/chat/completions", "match") in a.auth and all(v == "match" for _, v in a.auth + b.auth), (a.auth, b.auth)
    assert len([1 for p, _ in a.auth + b.auth if p == "/v1/chat/completions"]) == 3
    assert ("/v1/models", "match") in b.auth, "라우터가 둘째 서버의 모델 목록을 키로 대조했다"
    # 결과 — 직결 C 4(1·2·4 · 8 에서 TTFT), 라우터 C 12(라우터 경로가 기준) → 12·12·18, 정비일 4·4·6
    summ = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summ["basis"] == "router-slack2" and summ["knobs"]["CARD_REVIEW_MAX_STREAMS"] == 18
    assert [v["interference"] for v in summ["variants"]] == [False, False, False], "변형 앞뒤로 에이전트 서버의 일을 떴다"
    assert summ["single_server_knobs"]["CARD_REVIEW_CONCURRENCY"] == 4
    assert "CARD_REVIEW_CONCURRENCY=12" in r.stdout and "처음 어긋나는 단계에서 멈추고" in r.stdout
    assert "라우터가 보낸 수 서버별" in r.stdout and "127.0.0.1" not in (out / "summary.md").read_text(encoding="utf-8"), \
        "문서로 옮길 표에 서버 주소를 싣지 않는다"
    leaked = [p for p in out.rglob("*") if p.is_file() and KEY.encode() in p.read_bytes()]
    assert not leaked and KEY not in r.stdout + r.stderr, f"키가 결과·출력에 샜다: {leaked}"
    sc = json.loads((out / "router-slack0" / "scenario.json").read_text(encoding="utf-8"))
    assert sc["metadata"]["labels"]["slack"] == "0" and sc["spec"]["backend"]["target"].startswith("http://127.0.0.1:")
    seeds = {json.loads((out / v / "scenario.json").read_text(encoding="utf-8"))["spec"]["seed"]["value"] for v in
             ("direct", "router-slack2", "router-slack0")}
    assert len(seeds) == 3, "변형마다 씨앗이 달라야 앞 변형의 프롬프트가 캐시에 거저 맞지 않는다"
    assert not [p for p in lay["tmp"].iterdir() if p.name.startswith("tmp.")], "임시 디렉터리를 남겼다"
    r2 = lay["run"]("--lengths", str(lay["lengths"]), "--upstreams", f"{a.url}", "--out", str(out), "--force")
    assert r2.returncode == 2 and "비어 있지 않다" in r2.stderr, "지난 결과를 덮지 않는다"


def test_시나리오의_토크나이저_자리는_이미지가_굽는_자리다():
    assert C.TOKENIZER_IN_SIF == "/opt/tokenizers/glm-5.2" and C.TOKENIZER_IN_SIF in (ROOT / "infra/scripts/build-guidellm.sh").read_text(encoding="utf-8")
