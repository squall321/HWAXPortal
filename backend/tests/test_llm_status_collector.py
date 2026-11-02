# LLM/GPU 현황 수집기 — 해석기(라우터와 같은 셈) · 증가분 · 분위수 · 가짜 vLLM(리셋 · 히스토그램 · 401 · 걸린 서버 · 틀린 지표) · 스냅숏 · 시계열 · 띄우는 스크립트
"""왜 — 수집기는 운영 박스(cae00)에서만 실제 서버를 본다(dev 의 vLLM 은 자주 꺼져 있다). 그래서 틀리면 조용히 틀린다 — 서버가 다시 떠서 카운터가
0 이 되면 음수 속도가 그래프에 찍히고, 한 대가 매달리면 다른 서버의 값까지 낡고, 키가 화면이나 로그로 새고, 못 읽은 서버는 줄째 사라진다.

가짜 vLLM 은 표준 라이브러리 HTTP 서버다(스레드). 지표 · 모드를 시험이 정하고 받은 요청(경로 · Authorization 유무)을 적는다. 시계가 필요한 시험은
수집기에 시계를 끼운다(Collector(clock=…)). 주소는 루프백만 쓰고(내부 IP 는 추적 파일 금지), 에이전트 서버 · 라우터 주소도 시험이 정한 닫힌 포트나
가짜로 돌린다 — 이 박스에 떠 있는 서비스를 두드리지 않는다. 띄우는 스크립트는 임시 리포 사본에서 돌린다.
"""
import fcntl
import http.client
import importlib.util
import itertools
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LS = ROOT / "infra/llm-status"
LAUNCHER = ROOT / "infra/scripts/llm-status.sh"
KEY = "k-test-llm-key-0123456789"
CHAT_KEY = "k-test-chat-key-9876543210"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    keep, sys.dont_write_bytecode = sys.dont_write_bytecode, True   # 지문 폴더(infra/llm-status · infra/llm-router)에 __pycache__ 를 남기지 않는다
    try:
        spec.loader.exec_module(m)
    finally:
        sys.dont_write_bytecode = keep
    return m


C = _load("hwax_llm_status_collector", LS / "collector.py")
P = sys.modules["promtext"]
R = _load("hwax_llm_router_for_status", ROOT / "infra/llm-router/llm_router.py")
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _get(url: str, timeout: float = 5.0) -> tuple[int, dict]:
    try:
        with _OPENER.open(url, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


# ── 가짜 vLLM ───────────────────────────────────────────────────────────────────────────────────────
class _Quiet(ThreadingHTTPServer):
    """시험이 끊은 연결에 쓰다 난 오류(BrokenPipe)를 화면에 찍지 않는다."""
    daemon_threads = True

    def handle_error(self, request, client_address) -> None:
        return


def _go_float(d: float) -> str:
    """prometheus_client utils.floatToGoString 그대로(0.25.0, 유한한 수만) — 지표 글의 수 꼴(큰 수는 Go 처럼 지수로)."""
    s = repr(float(d))
    dot = s.find(".")
    if d > 0 and dot > 6:
        return f"{s[0]}.{s[1:dot]}{s[dot + 1:]}".rstrip("0.") + f"e+0{dot - 1}"
    return s


# prometheus_client 0.25.0 의 ProcessCollector 가 가짜 /proc(btime 1793578000 · 시작 76976 틱 · 100Hz)로 낸 글 그대로(generate_latest).
# vLLM 0.23.0 은 API 서버가 하나면 기본 레지스트리라 /metrics 에 이 덩이가 든다 — 가짜 vLLM 의 표지 줄이 이 꼴과 같은지 본다.
REAL_PROCESS = """# HELP process_virtual_memory_bytes Virtual memory size in bytes.
# TYPE process_virtual_memory_bytes gauge
process_virtual_memory_bytes 1.23456789e+08
# HELP process_resident_memory_bytes Resident memory size in bytes.
# TYPE process_resident_memory_bytes gauge
process_resident_memory_bytes 8.388608e+06
# HELP process_start_time_seconds Start time of the process since unix epoch in seconds.
# TYPE process_start_time_seconds gauge
process_start_time_seconds 1.79357876976e+09
# HELP process_cpu_seconds_total Total user and system CPU time spent in seconds.
# TYPE process_cpu_seconds_total counter
process_cpu_seconds_total 0.08
"""
_STARTS = itertools.count(1)


class FakeVllm:
    """가짜 vLLM. mode — ok · garbage(200 인데 vLLM 지표가 아니다) · hang(답하기 전에 붙든다 — release 까지) · health503(/health 만 503).
    ident — 프로세스 표지(process_start_time_seconds)를 싣는다(API 서버 하나인 vLLM). False 면 싣지 않는다(api_server_count > 1 — 다중 프로세스
    레지스트리). 가짜마다 뜬 때가 다르고, restart 하면 바뀐다."""

    BOUNDS = (0.05, 0.1, 0.5, 1.0, 5.0)

    def __init__(self, *, key: str | None = None, model: str = "glm-test", max_len: int = 200_000, version: str = "0.23.0",
                 ident: bool = True):
        self.key, self.model, self.max_len, self.version = key, model, max_len, version
        self.ident, self.started = ident, 1_793_578_769.76 + 1000 * next(_STARTS)
        self.mode = "ok"
        self.release = threading.Event()
        self.running, self.waiting, self.kv = 2.0, 1.0, 0.25
        self.c = dict.fromkeys(("prompt", "gen", "preempt", "pq", "ph", "stop", "abort", "error", "h2xx", "h5xx"), 0.0)
        self.h = {k: [0.0] * (len(self.BOUNDS) + 1) for k in ("ttft", "e2e", "queue")}   # 칸마다(누적 아님) · 마지막은 +Inf
        self.seen: list[tuple[str, str | None]] = []
        fake = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                return

            def _send(self, code: int, body: bytes, ctype: str = "application/json") -> None:
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                fake.seen.append((self.path, self.headers.get("Authorization")))
                if fake.mode == "hang":
                    fake.release.wait(30)
                if self.path == "/health":
                    self._send(503 if fake.mode == "health503" else 200, b"")
                elif self.path == "/version":
                    self._send(200, json.dumps({"version": fake.version}).encode())
                elif self.path == "/metrics":
                    body = b"<html>404 not here</html>" if fake.mode == "garbage" else fake.text().encode()
                    if fake.mode == "one_bad_line":         # 판이 바뀌어 한 줄이 낯선 꼴이 됐다 — 나머지는 읽는다
                        body += b'vllm:new_thing{engine="0" 1\n'

                    self._send(200, body, "text/plain; version=0.0.4")
                elif self.path == "/v1/models":
                    if fake.key and self.headers.get("Authorization") != f"Bearer {fake.key}":
                        self._send(401, b'{"error":"Unauthorized"}')
                    else:
                        self._send(200, json.dumps({"object": "list", "data": [
                            {"id": fake.model, "object": "model", "max_model_len": fake.max_len}]}).encode())
                else:
                    self._send(404, b"{}")

        self.srv = _Quiet(("127.0.0.1", 0), H)
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.port}/v1"

    def observe(self, kind: str, seconds: float, n: int = 1) -> None:
        i = next((j for j, b in enumerate(self.BOUNDS) if seconds <= b), len(self.BOUNDS))
        self.h[kind][i] += n

    def step(self, *, prompt: float = 1500, gen: float = 300, done: int = 10, ttft: float = 0.07, e2e: float = 0.8) -> None:
        for k, v in (("prompt", prompt), ("gen", gen), ("pq", 400), ("ph", 100), ("stop", done), ("h2xx", done)):
            self.c[k] += v
        self.observe("ttft", ttft, done)
        self.observe("e2e", e2e, done)
        self.observe("queue", 0.01, done)

    def restart(self) -> None:
        """서버가 다시 떴다 — 카운터 · 히스토그램이 0 부터, 프로세스 표지(뜬 때)가 바뀐다."""
        for k in self.c:
            self.c[k] = 0.0
        for k in self.h:
            self.h[k] = [0.0] * len(self.h[k])
        self.started += 61.37

    def text(self) -> str:
        lab = f'engine="0",model_name="{self.model}"'
        out = ["# HELP process_start_time_seconds Start time of the process since unix epoch in seconds.",
               "# TYPE process_start_time_seconds gauge", f"process_start_time_seconds {_go_float(self.started)}"] if self.ident else []
        out += ["# HELP vllm:num_requests_running Number of requests in model execution batches.",
               "# TYPE vllm:num_requests_running gauge", f"vllm:num_requests_running{{{lab}}} {self.running}",
               "# TYPE vllm:num_requests_waiting gauge", f"vllm:num_requests_waiting{{{lab}}} {self.waiting}",
               # 함정 — 합이 waiting 과 같은 다른 지표(접두로 세면 두 배)
               f'vllm:num_requests_waiting_by_reason{{{lab},reason="capacity"}} {self.waiting}',
               "# TYPE vllm:kv_cache_usage_perc gauge", f"vllm:kv_cache_usage_perc{{{lab}}} {self.kv}"]
        for name, key in (("prompt_tokens", "prompt"), ("generation_tokens", "gen"), ("num_preemptions", "preempt"),
                          ("prefix_cache_queries", "pq"), ("prefix_cache_hits", "ph")):
            out += [f"# TYPE vllm:{name}_total counter", f"vllm:{name}_total{{{lab}}} {self.c[key]}",
                    f"vllm:{name}_created{{{lab}}} 1.7e+09"]
        out.append("# TYPE vllm:request_success_total counter")
        for reason in ("stop", "abort", "error"):
            if self.c[reason] or reason == "stop":
                out.append(f'vllm:request_success_total{{{lab},finished_reason="{reason}"}} {self.c[reason]}')
        for kind, base in (("ttft", "time_to_first_token_seconds"), ("e2e", "e2e_request_latency_seconds"),
                           ("queue", "request_queue_time_seconds")):
            out.append(f"# TYPE vllm:{base} histogram")
            cum = 0.0
            for b, n in zip((*self.BOUNDS, "+Inf"), self.h[kind]):
                cum += n
                le = b if b == "+Inf" else repr(float(b))
                out.append(f'vllm:{base}_bucket{{engine="0",le="{le}",model_name="{self.model}"}} {cum}')
            out += [f"vllm:{base}_count{{{lab}}} {cum}", f"vllm:{base}_sum{{{lab}}} {cum * 0.1}"]
        out.append("# TYPE http_requests_total counter")
        out.append(f'http_requests_total{{handler="/v1/chat/completions",method="POST",status="2xx"}} {self.c["h2xx"]}')
        if self.c["h5xx"]:
            out.append(f'http_requests_total{{handler="/v1/chat/completions",method="POST",status="5xx"}} {self.c["h5xx"]}')
        return "\n".join(out) + "\n"

    def close(self) -> None:
        self.release.set()
        self.srv.shutdown()
        self.srv.server_close()


class FakeJson:
    """가짜 에이전트 서버 · 라우터 — 경로 → (상태, JSON)."""

    def __init__(self, routes: dict):
        self.routes = routes
        fake = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                return

            def do_GET(self):
                code, obj = fake.routes.get(self.path, (404, {}))
                body = json.dumps(obj).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        self.srv = _Quiet(("127.0.0.1", 0), H)
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.srv.shutdown()
        self.srv.server_close()


class FakePool:
    """묶음 주소(요청마다 아무 한 대로 보내는 nginx — OD-2)의 가짜. /metrics 는 뒤 서버들에 차례로, 나머지 경로는 첫 서버로 보낸다(시험이 어느
    표본이 어느 서버의 것인지 정하게)."""

    def __init__(self, backs: list):
        self.backs, self.n = backs, 0
        pool = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                return

            def do_GET(self):
                back = pool.backs[0]
                if self.path == "/metrics":
                    back = pool.backs[pool.n % len(pool.backs)]
                    pool.n += 1
                c = http.client.HTTPConnection("127.0.0.1", back.port, timeout=5)
                try:
                    c.request("GET", self.path, headers={k: v for k, v in self.headers.items() if k.lower() == "authorization"})
                    r = c.getresponse()
                    body = r.read()
                finally:
                    c.close()
                self.send_response(r.status)
                self.send_header("Content-Type", r.getheader("Content-Type") or "text/plain")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        self.srv = _Quiet(("127.0.0.1", 0), H)
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.port}/v1"

    def close(self) -> None:
        self.srv.shutdown()
        self.srv.server_close()


@pytest.fixture
def fakes():
    made: list = []

    def make(cls=FakeVllm, *a, **kw):
        f = cls(*a, **kw)
        made.append(f)
        return f
    yield make
    for f in made:
        f.close()


class Clock:
    def __init__(self, t: float = 1_800_000_000.0):
        self.t = t

    def __call__(self) -> float:
        return self.t

    def tick(self, s: float) -> None:
        self.t += s


def _collector(tmp_path: Path, env_text: str, *, store: bool = True, clock=None, interval: float = 15.0):
    """수집기 하나 — 에이전트 서버는 따로 주지 않으면 닫힌 포트(이 박스의 9009 를 두드리지 않는다)."""
    if "LLM_STATUS_AGENT_URL" not in env_text:
        env_text += f"LLM_STATUS_AGENT_URL=http://127.0.0.1:{_free_port()}\n"
    envf = tmp_path / "infra.env"
    envf.write_text(env_text, encoding="utf-8")
    st = C.Store(tmp_path / "s.sqlite") if store else None
    coll = C.Collector(envf, st, interval=interval, clock=clock or time.time)
    coll.reload(force=True)
    return coll


def _state(coll, tid: str):
    return coll.states[tid]


def _vals(snap: dict, tid: str) -> dict:
    return next(t for t in snap["targets"] if t["id"] == tid)["values"]


def _wait_idle(coll, timeout: float = 10.0) -> None:
    end = time.monotonic() + timeout
    sts = [*coll.states.values(), coll.agent, coll.router]
    while any(s.busy for s in sts):
        assert time.monotonic() < end, "읽기가 끝나지 않았다"
        time.sleep(0.02)


# ── 해석기 ─────────────────────────────────────────────────────────────────────────────────────────
RICH = """# HELP vllm:num_requests_running Number of requests in model execution batches.
# TYPE vllm:num_requests_running gauge
vllm:num_requests_running{engine="0",model_name="glm"} 3.0
vllm:num_requests_running{engine="1",model_name="glm"} 1.0
# TYPE vllm:num_requests_waiting gauge
vllm:num_requests_waiting{engine="0",model_name="glm"} 2.0
vllm:num_requests_waiting_by_reason{engine="0",model_name="glm",reason="capacity"} 2.0
vllm:kv_cache_usage_perc{engine="0",model_name="glm"} 0.5
vllm:gpu_cache_usage_perc{engine="0",model_name="glm"} 0.99
# TYPE vllm:prompt_tokens_total counter
vllm:prompt_tokens_total{engine="0",model_name="glm"} 1.5e+06
vllm:prompt_tokens_total{engine="1",model_name="glm"} 500000
vllm:prompt_tokens_created{engine="0",model_name="glm"} 1.7e+09
vllm:generation_tokens_total{engine="0",model_name="glm"} 250000.0
vllm:gpu_prefix_cache_queries_total{engine="0"} 999
vllm:prefix_cache_queries_total{engine="0"} 400
vllm:prefix_cache_hits_total{engine="0"} 100
# TYPE vllm:request_success_total counter
vllm:request_success_total{engine="0",finished_reason="stop",model_name="glm"} 900.0
vllm:request_success_total{engine="0",finished_reason="abort",model_name="glm"} 3.0
vllm:request_success_total{engine="1",finished_reason="stop",model_name="glm"} 100.0
# TYPE vllm:time_to_first_token_seconds histogram
vllm:time_to_first_token_seconds_bucket{engine="0",le="0.1",model_name="glm"} 5.0
vllm:time_to_first_token_seconds_bucket{engine="0",le="1.0",model_name="glm"} 9.0
vllm:time_to_first_token_seconds_bucket{engine="0",le="+Inf",model_name="glm"} 10.0
vllm:time_to_first_token_seconds_bucket{engine="1",le="0.1",model_name="glm"} 5.0
vllm:time_to_first_token_seconds_bucket{engine="1",le="1.0",model_name="glm"} 9.0
vllm:time_to_first_token_seconds_bucket{engine="1",le="+Inf",model_name="glm"} 10.0
vllm:time_to_first_token_seconds_count{engine="0",model_name="glm"} 10.0
vllm:time_to_first_token_seconds_count{engine="1",model_name="glm"} 10.0
vllm:time_to_first_token_seconds_sum{engine="0",model_name="glm"} 4.0
http_requests_total{handler="/v1/chat/completions",method="POST",status="2xx"} 1000
http_requests_total{handler="/v1/chat/completions",method="POST",status="5xx"} 7
http_requests_total{handler="/metrics",method="GET",status="2xx"} 50
vllm:cache_config_info{block_size="16",note="a \\"quoted\\" \\\\ back\\nslash"} 1.0
this line is broken {
vllm:num_requests_running{engine="2"} 1_000
vllm:num_requests_running{engine="3" 7
"""


def test_해석기는_게이지_카운터_히스토그램_라벨을_읽고_틀린_줄은_세고_버린다():
    p = P.parse(RICH)
    assert p.bad == 3, "틀린 줄 셋(조각난 줄 · 1_000 · 닫히지 않은 라벨)은 세고 버린다 — 지표 전체를 잃지 않는다"
    assert p.types["vllm:time_to_first_token_seconds"] == "histogram" and p.types["vllm:prompt_tokens_total"] == "counter"
    info = p.named("vllm:cache_config_info")[0]
    assert info.label("note") == 'a "quoted" \\ back\nslash', "라벨 값의 이스케이프(\\\" \\\\ \\n)를 푼다"
    ex = P.vllm(p)
    assert ex["gauges"] == {"running": 4.0, "waiting": 2.0, "kv": 0.5}, "엔진 묶음은 더하고 by_reason · 옛 KV 이름은 세지 않는다"
    c = ex["counters"]
    assert c["prompt_tokens"] == 2_000_000.0, "_created 는 카운터가 아니다(정확한 이름만)"
    assert c["prefix_queries"] == 400 and c["prefix_hits"] == 100, "새 이름이 있으면 옛 이름(gpu_prefix_…)을 더하지 않는다"
    assert c["preemptions"] is None, "없는 카운터는 0 이 아니라 None(모름)"
    assert ex["by_label"]["finished"] == {"stop": 1000.0, "abort": 3.0}
    assert ex["by_label"]["http"] == {"2xx": 1050.0, "5xx": 7.0}
    h = ex["hists"]["ttft"]
    assert h.bounds == (0.1, 1.0, float("inf")) and h.cum == (10.0, 18.0, 20.0) and h.count == 20.0, "히스토그램은 칸마다 엔진을 더한다"
    assert ex["hists"]["e2e"] is None and ex["hists"]["queue"] is None
    assert P.vllm(P.parse("<html>not metrics</html>")) is None and P.vllm(P.parse("")) is None


# 라우터 시험(test_llm_router.py)의 견본 그대로 + 위 RICH + 가짜 vLLM 의 글 — 같은 글에서 running · waiting · KV 가 글자 그대로 같아야 한다
ROUTER_FIXTURES = [
    """# HELP vllm:num_requests_running Number of requests in model execution batches.
# TYPE vllm:num_requests_running gauge
vllm:num_requests_running{engine="0",model_name="qwen2.5-7b-dev"} 0.0
# HELP vllm:num_requests_waiting Number of requests waiting to be processed.
# TYPE vllm:num_requests_waiting gauge
vllm:num_requests_waiting{engine="0",model_name="qwen2.5-7b-dev"} 0.0
vllm:num_requests_waiting_by_reason{engine="0",model_name="qwen2.5-7b-dev",reason="capacity"} 0.0
vllm:kv_cache_usage_perc{engine="0",model_name="qwen2.5-7b-dev"} 0.0
""",
    "\n".join([
        'vllm:num_requests_running{engine="0",model_name="m"} 2.0', 'vllm:num_requests_running{engine="1",model_name="m"} 1.0',
        'vllm:num_requests_waiting{engine="0",model_name="m"} 3.0', 'vllm:num_requests_waiting{engine="1",model_name="m"} 4.0',
        'vllm:num_requests_waiting_by_reason{engine="0",model_name="m",reason="capacity"} 3.0',
        'vllm:num_requests_waiting_by_reason{engine="1",model_name="m",reason="capacity"} 4.0',
        'vllm:num_requests_running_total{engine="0"} 100',
        'vllm:kv_cache_usage_perc{engine="0",model_name="m"} 0.3', 'vllm:kv_cache_usage_perc{engine="1",model_name="m"} 0.7',
        'vllm:gpu_cache_usage_perc{engine="0",model_name="m"} 0.99']),
    'vllm:num_requests_running 1\nvllm:num_requests_waiting 0\nvllm:gpu_cache_usage_perc{a="x}y"} 0.25 1700000000\n',
    'vllm:num_requests_running{e="0"} NaN\nvllm:num_requests_running{e="1"} 2\nvllm:num_requests_waiting 1\n',
    'vllm:num_requests_running 1\nvllm:num_requests_waiting_by_reason{reason="capacity"} 5\n',
    "<html>not found</html>",
    "",
    'vllm:num_requests_running{e="0"} NaN\nvllm:num_requests_waiting 1\n',
    "vllm:num_requests_running 1\nvllm:num_requests_waiting 2\nvllm:kv_cache_usage_perc +Inf\nvllm:gpu_cache_usage_perc 0.4\n",
    "  vllm:num_requests_running 5\n\tvllm:num_requests_waiting 6 1700000000000\nvllm:kv_cache_usage_perc{} 1e-1\n",
    RICH.replace("1_000", "1"),
]


@pytest.mark.parametrize("i", range(len(ROUTER_FIXTURES) + 1))
def test_running_waiting_KV_는_라우터_해석기와_글자_그대로_같다(i):
    """라우터 해석기는 고치지 않는다(지문 — 바꾸면 라우터가 다시 뜬다). 넓힌 해석기가 같은 셈인지 같은 견본으로 본다."""
    text = ROUTER_FIXTURES[i] if i < len(ROUTER_FIXTURES) else FakeVllm.text(_FakeText())
    assert P.basic(P.parse(text)) == R.parse_metrics(text), text[:200]


class _FakeText:
    """FakeVllm.text 를 서버 없이 부르려는 껍데기."""
    BOUNDS = FakeVllm.BOUNDS
    model, running, waiting, kv = "m", 4.0, 2.0, 0.6
    ident, started = True, 1_793_578_769.76
    c = dict.fromkeys(("prompt", "gen", "preempt", "pq", "ph", "stop", "abort", "error", "h2xx", "h5xx"), 1.0)
    h = {k: [1.0] * (len(FakeVllm.BOUNDS) + 1) for k in ("ttft", "e2e", "queue")}


def test_분위수는_칸의_증가분으로_어림하고_Inf_칸이면_앞_칸의_위끝이다():
    h = P.Hist((0.1, 0.5, 1.0, float("inf")), (5.0, 9.0, 10.0, 10.0), 10.0, None)
    assert P.quantile(0.5, h) == pytest.approx(0.1), "순위 5 — 첫 칸의 끝"
    assert P.quantile(0.7, h) == pytest.approx(0.1 + 0.4 * (7 - 5) / 4), "칸 안은 선형 보간"
    assert P.quantile(0.95, h) == pytest.approx(0.5 + 0.5 * 0.5)
    tail = P.Hist((0.1, 1.0, float("inf")), (1.0, 2.0, 10.0), 10.0, None)
    assert P.quantile(0.95, tail) == 1.0, "+Inf 칸에 떨어지면 그 앞 칸의 위끝(더 큰 값은 칸이 말하지 않는다)"
    assert P.quantile(0.5, P.Hist((0.1, float("inf")), (0.0, 0.0), 0.0, None)) is None, "들어온 것이 없으면 None"
    a = P.Hist((0.1, float("inf")), (5.0, 6.0), 6.0, 1.0)
    b = P.Hist((0.1, float("inf")), (7.0, 9.0), 9.0, 2.0)
    assert P.hist_delta(a, b) == P.Hist((0.1, float("inf")), (2.0, 3.0), 3.0, 1.0)
    assert P.hist_delta(b, a) is None, "줄었으면(서버 재기동) 빈칸 — 음수 칸을 만들지 않는다"
    assert P.hist_delta(a, P.Hist((0.5, float("inf")), (7.0, 9.0), 9.0, None)) is None, "칸이 바뀌면 빈칸"
    assert P.counter_delta(10.0, 4.0) is None and P.counter_delta(4.0, 10.0) == 6.0 and P.counter_delta(None, 1.0) is None


# ── 가짜 vLLM 을 읽기 ────────────────────────────────────────────────────────────────────────────────
def test_다시_뜬_서버는_새_프로세스의_표본으로만_재고_음수_속도를_내지_않는다(tmp_path, fakes):
    """서버가 다시 뜨면 표지(process_start_time_seconds)가 바뀐다 — 앞 프로세스의 표본은 셈에서 빠지고(OD-26) 새 프로세스의 표본이 둘 쌓이면 잰다.
    그래프(표본마다 잰 속도)에 다시 뜬 첫 표본의 줄은 없고, 음수 · 0 으로 끌어내린 값도 없다."""
    f = fakes()
    clock = Clock()
    coll = _collector(tmp_path, f"LLM_BASE_URL={f.base}\n", clock=clock)
    st = _state(coll, "glm")
    stamps = []
    for _ in range(3):                           # t0 · t15 · t30 — 15초마다 출력 300 토큰 = 초당 20
        f.step(gen=300)
        coll.poll_vllm(st)
        stamps.append(int(clock()))
        clock.tick(15)
    v = _vals(coll.snapshot(), "glm")
    assert v["gen_tps"]["value"] == pytest.approx(20.0) and v["gen_tps"]["source"] == C.BASIS_IDENT, v["gen_tps"]
    f.restart()
    f.step(gen=300)                              # 다시 뜬 서버의 첫 300 — 앞의 900 보다 작다
    coll.poll_vllm(st)
    t_reset = int(clock())
    g = _vals(coll.snapshot(), "glm")["gen_tps"]
    assert g["value"] is None and "process_start_time_seconds" in g["error"] and "다시 떴거나" in g["error"], \
        "앞 프로세스의 표본과 섞지 않는다 — 새 프로세스의 표본이 하나뿐이면 값 대신 까닭이다"
    clock.tick(15)
    f.step(gen=300)
    coll.poll_vllm(st)
    assert _vals(coll.snapshot(), "glm")["gen_tps"]["value"] == pytest.approx(20.0), "새 프로세스의 둘째 표본부터 잰다"
    s = coll.store.series("glm", "gen_tps", "1h", now=clock())
    assert [p[0] for p in s["points"]] == [stamps[1], stamps[2], int(clock())], "다시 뜬 첫 표본(t45)은 빈칸 — 줄이 없다"
    assert all(p[1] == pytest.approx(20.0) for p in s["points"]), s["points"]
    assert t_reset not in [p[0] for p in s["points"]]
    for metric in ("prompt_tps", "gen_tps", "preempt_per_min", "http_5xx_per_min", "finished_error_per_min"):
        pts = coll.store.series("glm", metric, "1h", now=clock())["points"]
        assert all(p[1] >= 0 for p in pts), f"{metric} 에 음수가 있다 — {pts}"


def test_표지가_없는_서버는_창_안에서_카운터가_줄면_그_창을_비운다(tmp_path, fakes):
    """api_server_count > 1 인 vLLM 은 process_start_time_seconds 를 내지 않는다 — 종전처럼 이웃한 표본으로 재되, 창 안에서 카운터가 하나라도
    줄면 그 창(카드 60초 · 5분)의 값을 모두 비운다(줄어든 쌍만 빼고 나머지로 재지 않는다 — OD-26). 줄어든 쌍이 창을 나가면 다시 잰다."""
    f = fakes(ident=False)
    clock = Clock()
    coll = _collector(tmp_path, f"LLM_BASE_URL={f.base}\n", clock=clock)
    st = _state(coll, "glm")
    t0 = int(clock())
    for _ in range(3):                           # t0 · t15 · t30
        f.step(gen=300)
        coll.poll_vllm(st)
        clock.tick(15)
    v = _vals(coll.snapshot(), "glm")
    assert v["gen_tps"]["value"] == pytest.approx(20.0) and v["gen_tps"]["source"] == C.BASIS_COUNTERS, v["gen_tps"]
    f.restart()                                  # t45 — 카운터가 0 부터
    for i in range(5):                           # t45 · t60 · t75 · t90 · t105
        f.step(gen=300)
        coll.poll_vllm(st)
        v = _vals(coll.snapshot(), "glm")
        if i < 4:                                # 줄어든 쌍(t30 → t45)이 60초 창 안에 있다
            assert v["gen_tps"]["value"] is None and "창 안에서 카운터가 줄었다" in v["gen_tps"]["error"], (i, v["gen_tps"])
            assert "process_start_time_seconds 가 없어" in v["gen_tps"]["error"], "어느 길로 쟀는지(표지가 없다) 말한다"
        assert v["ttft_p95"]["value"] is None and v["requests_per_min"]["value"] is None, "5분 창에는 아직 그 쌍이 있다"
        clock.tick(15)
    assert v["gen_tps"]["value"] == pytest.approx(20.0), "그 쌍이 60초 창을 나가면 다시 잰다"
    pts = coll.store.series("glm", "gen_tps", "1h", now=clock())["points"]
    assert [p[0] for p in pts] == [t0 + 15, t0 + 30, t0 + 105], f"줄어든 쌍이 창 안에 있는 동안은 저장하지 않는다 — {pts}"


def test_묶음_주소는_같은_서버_프로세스의_표본끼리만_잰다(tmp_path, fakes):
    """묶음 nginx 는 요청마다 아무 한 대로 보낸다(OD-2) — 서로 다른 서버의 누적 차를 속도로 재면 한 대 초당 100 토큰이 수만으로 찍혔다(반대 검토
    11-02 — 96,766 · 128,989 tok/s). 표지가 같은 표본끼리만 재면 그 한 대의 값이다 — 사이에 다른 서버가 답해도 건너 이웃으로 친다(OD-26)."""
    a, b = fakes(), fakes()
    for _ in range(30):
        b.step(prompt=100_000, gen=20_000, done=50)          # b 는 오래 돌아 누적이 크다
    pool = fakes(FakePool, [a, b])
    clock = Clock()
    coll = _collector(tmp_path, f"LLM_BASE_URL={pool.base}\n", clock=clock)
    st = _state(coll, "glm")
    got = []
    for _ in range(8):                                       # /metrics 는 a · b · a · b … 가 답한다
        for f in (a, b):
            f.step(prompt=1500, gen=300, done=5)             # 서버마다 15초에 1500 · 300 토큰 · 5건 — 초당 100 · 20, 분당 20건
        coll.poll_vllm(st)
        v = _vals(coll.snapshot(), "glm")
        got.append({k: (v[k]["value"], v[k]["error"], v[k]["source"]) for k in ("prompt_tps", "gen_tps", "requests_per_min")})
        clock.tick(15)
    assert got[1]["prompt_tps"][0] is None and "process_start_time_seconds" in got[1]["prompt_tps"][1], "b 의 첫 표본 — 아직 잴 쌍이 없다"
    for i, g in enumerate(got[2:], 2):
        assert g["prompt_tps"][0] == pytest.approx(100.0) and g["gen_tps"][0] == pytest.approx(20.0), (i, g)
        assert g["requests_per_min"][0] == pytest.approx(20.0) and g["prompt_tps"][2] == C.BASIS_IDENT, (i, g)
    pts = coll.store.series("glm", "prompt_tps", "1h", now=clock())["points"]
    assert len(pts) == 6 and all(p[1] == pytest.approx(100.0) for p in pts), f"저장한 속도도 한 대의 값이다 — {pts}"


def test_표지가_없는_묶음_주소는_줄어든_카운터를_본_뒤로_속도를_비운다(tmp_path, fakes):
    """표지가 없으면 같은 서버의 표본만 고를 수 없다 — 다른 서버로 넘어가 카운터가 줄면 그 창을 비운다. 늘기만 한 첫 넘어감(작은 누적 → 큰 누적)은
    표지 없이 가려낼 수 없다(OD-26 — 그 한 표본은 남는다). 줄어든 쌍을 본 뒤로는 카드도 저장도 비운다."""
    a, b = fakes(ident=False), fakes(ident=False)
    for _ in range(30):
        b.step(prompt=100_000, gen=20_000, done=50)
    pool = fakes(FakePool, [a, b])
    clock = Clock()
    coll = _collector(tmp_path, f"LLM_BASE_URL={pool.base}\n", clock=clock)
    st = _state(coll, "glm")
    t0 = int(clock())
    for i in range(8):
        for f in (a, b):
            f.step(prompt=1500, gen=300, done=5)
        coll.poll_vllm(st)
        v = _vals(coll.snapshot(), "glm")
        if i >= 2:                                           # t30 — b → a 에서 카운터가 줄었다
            for k in ("prompt_tps", "gen_tps", "requests_per_min", "ttft_p95", "prefix_hit"):
                assert v[k]["value"] is None and "창 안에서 카운터가 줄었다" in v[k]["error"], (i, k, v[k])
        clock.tick(15)
    pts = coll.store.series("glm", "prompt_tps", "1h", now=clock())["points"]
    assert [p[0] for p in pts] == [t0 + 15], f"줄어든 카운터를 본 뒤로는 저장하지 않는다(t15 는 가려내지 못한 첫 넘어감) — {pts}"


def test_프로세스_표지는_prometheus_client_가_내는_꼴_그대로_읽는다():
    p = P.parse(REAL_PROCESS)
    assert P.ident(p) == 1793578769.76 and p.bad == 0, "prometheus_client 의 ProcessCollector 가 낸 덩이"
    fake = [ln for ln in FakeVllm.text(_FakeText()).splitlines() if "process_start_time_seconds" in ln]
    assert fake == [ln for ln in REAL_PROCESS.splitlines() if "process_start_time_seconds" in ln], "가짜 vLLM 의 표지 줄이 실제 꼴과 같다"
    assert _go_float(1793578001.0) == "1.793578001e+09" and _go_float(0.08) == "0.08", "floatToGoString 과 같은 수 꼴"
    assert P.vllm(P.parse(FakeVllm.text(_FakeText())))["ident"] == 1793578769.76
    assert P.ident(P.parse("vllm:num_requests_running 1\n")) is None, "다중 프로세스 레지스트리 — 그 줄이 없다"
    assert P.ident(P.parse('process_start_time_seconds{pid="1"} 1.7e+09\n')) is None, "라벨이 붙은 것은 표지가 아니다"
    assert P.ident(P.parse("process_start_time_seconds 1.7e+09\nprocess_start_time_seconds 1.8e+09\n")) is None, "둘이면 모른다"


def test_히스토그램_지연은_누적이_아니라_창_안의_증가로_잰다(tmp_path, fakes):
    """서버가 뜬 뒤 쌓인 누적으로 재면 몇 시간 전의 느린 요청이 지금의 p95 를 끌어올린다 — 5분 창 안의 칸 증가로 잰다."""
    f = fakes()
    for _ in range(200):
        f.observe("ttft", 4.0)                   # 수집기가 보기 전에 쌓인 느린 것
    clock = Clock()
    coll = _collector(tmp_path, f"LLM_BASE_URL={f.base}\n", clock=clock)
    st = _state(coll, "glm")
    coll.poll_vllm(st)
    for _ in range(3):
        clock.tick(15)
        f.step(ttft=0.07, done=10)               # 창 안의 빠른 것
        coll.poll_vllm(st)
    v = _vals(coll.snapshot(), "glm")
    assert 0.05 <= v["ttft_p50"]["value"] <= 0.1 and 0.05 <= v["ttft_p95"]["value"] <= 0.1, v["ttft_p95"]
    assert v["ttft_p95"]["approx"] is True and v["e2e_p95"]["approx"] is True, "분위수는 어림 표지가 붙는다"
    assert v["requests_per_min"]["value"] == pytest.approx(40.0), "15초마다 10 건"
    assert v["prefix_hit"]["value"] == pytest.approx(0.25), "적중 100 / 질의 400"
    assert v["http_5xx_per_min"]["value"] == 0.0 and v["finished_error_per_min"]["value"] == 0.0 and v["aborts_per_min"]["value"] == 0.0, \
        "라벨이 아직 없으면 0(한 번도 없었다)"
    f.c["h5xx"] += 3          # 5xx 셋 — 그 가운데 하나는 엔진 오류로 끝난 요청이다(스트리밍이 아니면 vLLM 이 500 으로 답한다)
    f.c["error"] += 1
    f.c["abort"] += 2
    f.c["preempt"] += 1
    clock.tick(15)
    f.step()
    coll.poll_vllm(st)
    v = _vals(coll.snapshot(), "glm")
    assert v["http_5xx_per_min"]["value"] == pytest.approx(3 / 1.0), "5분 창(1분 걸린 넷 쌍)에 5xx 셋 — 분당 3"
    assert v["finished_error_per_min"]["value"] == pytest.approx(1.0), "오류로 끝난 요청은 따로 — 한 요청을 둘에 더해 넷으로 세지 않는다(OD-30)"
    assert "errors_per_min" not in v, "더한 칸은 없다"
    assert v["aborts_per_min"]["value"] == pytest.approx(2.0) and v["preempt_per_min"]["value"] == pytest.approx(1.0)
    s = coll.store.series("glm", "finished_error_per_min", "1h", now=clock())
    assert s["points"] and s["points"][-1][1] == pytest.approx(1.0), "둘 다 쌓는다"


def test_v1_models_는_키가_없으면_401_을_까닭으로_보이고_키는_v1_models_에만_싣는다(tmp_path, fakes):
    f = fakes(key=KEY)
    coll = _collector(tmp_path, f"LLM_BASE_URL={f.base}\n")
    coll.poll_vllm(_state(coll, "glm"))
    v = _vals(coll.snapshot(), "glm")
    assert v["models"]["value"] is None and "401" in v["models"]["error"] and "LLM_API_KEY" in v["models"]["error"], v["models"]
    assert "키가 없다" in v["models"]["error"]
    assert v["up"]["value"] is True and v["running"]["value"] == 2.0, "/health · /metrics 는 키 없이 읽힌다(vLLM — OD-2)"
    (tmp_path / "w").mkdir()
    coll = _collector(tmp_path / "w", f"LLM_BASE_URL={f.base}\nLLM_API_KEY=wrong-key-000000000\n")
    coll.poll_vllm(_state(coll, "glm"))
    assert "키가 맞지 않는다" in _vals(coll.snapshot(), "glm")["models"]["error"]
    (tmp_path / "r").mkdir()
    f.seen.clear()
    coll = _collector(tmp_path / "r", f"LLM_BASE_URL={f.base}\nLLM_API_KEY={KEY}\n")
    coll.poll_vllm(_state(coll, "glm"))
    v = _vals(coll.snapshot(), "glm")
    assert v["models"]["value"] == [{"id": "glm-test", "max_model_len": 200_000}] and v["context"]["value"] == 200_000
    assert v["version"]["value"] == "0.23.0"
    with_auth = {p for p, a in f.seen if a}
    assert with_auth == {"/v1/models"} and {p for p, _ in f.seen} == {"/health", "/version", "/metrics", "/v1/models"}, f.seen


def test_챗_LLM_주소와_복제본은_챗_LLM_키로_나머지는_LLM_키로_묻는다(tmp_path, fakes):
    glm, chat = fakes(key=KEY), fakes(key=CHAT_KEY, model="qwen-test")
    r1, r2 = fakes(key=CHAT_KEY, model="qwen-test"), fakes(key=CHAT_KEY, model="qwen-test", max_len=1_010_000)
    mapfile = tmp_path / "ports.map"
    mapfile.write_text(f"# 포트 노드\n{r1.port} gpu-node-a\n{r2.port}=gpu-node-b\n", encoding="utf-8")
    coll = _collector(tmp_path, f"LLM_BASE_URL={glm.base}\nLLM_API_KEY={KEY}\nCHAT_LLM_BASE_URL={chat.base}\n"
                                f"CHAT_LLM_API_KEY={CHAT_KEY}\nLLM_STATUS_REPLICA_PORTS={r1.port},{r2.port}\n"
                                f"LLM_STATUS_REPLICA_MAP={mapfile}\n")
    ids = [t.id for t in coll.cfg.targets]
    assert ids == ["glm", "chat", f"chat-{r1.port}", f"chat-{r2.port}"], ids
    coll.poll_all_once(timeout=20)
    snap = coll.snapshot()
    for tid in ids:
        assert _vals(snap, tid)["models"]["value"], (tid, _vals(snap, tid)["models"])
    rep = {t["id"]: t for t in snap["targets"]}
    assert rep[f"chat-{r1.port}"]["group"] == "chat" and rep[f"chat-{r1.port}"]["node"] == "gpu-node-a"
    assert rep[f"chat-{r2.port}"]["node"] == "gpu-node-b" and rep[f"chat-{r2.port}"]["origin"] == "replica"
    assert {a for _, a in glm.seen if a} == {f"Bearer {KEY}"} and {a for _, a in r1.seen if a} == {f"Bearer {CHAT_KEY}"}
    # 같은 모델의 창이 복제본마다 다르면(rolling 중) 표지
    assert snap["context"]["value"] == [{"model": "qwen-test", "windows": {"챗 LLM": 200_000, f":{r1.port}": 200_000,
                                                                            f":{r2.port}": 1_010_000}}]
    assert rep[f"chat-{r2.port}"]["values"]["context_mismatch"]["value"] is True
    assert rep["glm"]["values"]["context_mismatch"]["value"] is False


def test_걸린_서버는_다른_대상을_세우지_않고_그_주기는_건너뛴다(tmp_path, fakes, monkeypatch):
    """한 대가 연결은 받고 답하지 않아도 다른 서버는 제 주기에 읽히고, 스냅숏은 곧바로 답한다. 걸린 대상의 다음 주기는 쌓지 않고 건너뛴다."""
    monkeypatch.setattr(C, "READ_S", 1.0)
    hung, good = fakes(), fakes()
    hung.mode = "hang"
    coll = _collector(tmp_path, f"LLM_STATUS_TARGETS=HUNG={hung.base},GOOD={good.base}\n")
    t0 = time.monotonic()
    coll.tick()
    end = time.monotonic() + 0.8
    while _vals(coll.snapshot(), "GOOD")["running"]["value"] is None:
        assert time.monotonic() < end, "걸린 서버가 다른 대상을 세웠다"
        time.sleep(0.02)
    s0 = time.monotonic()
    snap = coll.snapshot()
    assert time.monotonic() - s0 < 0.5, "스냅숏이 걸린 읽기를 기다렸다"
    hv = next(t for t in snap["targets"] if t["id"] == "HUNG")
    assert hv["busy"] is True and hv["values"]["up"]["value"] is None
    coll.tick()                                   # 앞 읽기가 안 끝났다 — 건너뛴다(스레드를 쌓지 않는다)
    assert coll.states["HUNG"].skipped == 1
    while coll.states["HUNG"].busy:
        assert time.monotonic() - t0 < 6, "읽기 기한이 걸리지 않았다"
        time.sleep(0.05)
    hv = _vals(coll.snapshot(), "HUNG")
    assert hv["up"]["value"] is False and "읽기 시간 초과" in hv["up"]["error"], hv["up"]
    assert "읽기 시간 초과" in hv["running"]["error"], "걸린 서버는 /health 에서 멈추고 나머지를 묻지 않는다"
    assert [p for p, _ in hung.seen] == ["/health"], hung.seen


def test_읽기_스레드를_못_띄우면_그_대상만_까닭을_남기고_주기는_이어진다(tmp_path, fakes, monkeypatch):
    """Thread.start 가 한 번 실패하면(자원 고갈) 그 대상이 영영 바쁨으로 남고 그 주기의 나머지 대상 · 정리까지 끊겼다(반대 검토 11-02 · 재현
    thread_fail.py). 바쁨을 풀고 그 대상의 원천에 까닭을 남기고 나머지는 그대로 돈다(OD-32)."""
    a, b = fakes(), fakes()
    clock = Clock()
    coll = _collector(tmp_path, f"LLM_STATUS_TARGETS=glm={a.base},B={b.base}\n", clock=clock)
    real = threading.Thread.start
    state = {"n": 0}

    def flaky(self):
        if self.name == "llm-status-glm" and state["n"] == 0:
            state["n"] += 1
            raise RuntimeError("can't start new thread")
        return real(self)
    monkeypatch.setattr(threading.Thread, "start", flaky)
    coll.tick()
    _wait_idle(coll)
    st = _state(coll, "glm")
    assert st.busy is False and st.busy_since is None and st.polls == 0, "바쁨을 풀었다"
    snap = coll.snapshot()
    g = next(t for t in snap["targets"] if t["id"] == "glm")
    assert "읽기 스레드를 띄우지 못했다" in g["sources"]["health"]["error"] and "RuntimeError" in g["sources"]["health"]["error"], g["sources"]
    assert _vals(snap, "B")["up"]["value"] is True, "같은 주기의 다른 대상은 읽었다"
    assert coll.store._last_maint == clock(), "같은 주기의 정리(접기 · 지우기)도 돌았다"
    clock.tick(15)
    coll.tick()
    _wait_idle(coll)
    assert _vals(coll.snapshot(), "glm")["up"]["value"] is True and st.polls == 1, "다음 주기에는 읽는다"


def test_닫힌_포트는_연결_거부_연결이_안_되면_연결_시간_초과로_말한다(tmp_path, monkeypatch):
    assert (C.CONNECT_S, C.READ_S, C.INTERVAL_S, C.MODELS_EVERY_S, C.STALE_AFTER) == (3.0, 5.0, 15.0, 60.0, 3), "계획서 §3.3 의 수"
    port = _free_port()
    r = C.fetch(C.Addr("http", "127.0.0.1", port), "/health")
    assert r.kind == "refused" and "연결 거부" in r.error
    import http.client

    def slow_connect(self):
        raise socket.timeout("timed out")
    monkeypatch.setattr(http.client.HTTPConnection, "connect", slow_connect)
    r = C.fetch(C.Addr("http", "127.0.0.1", port), "/health")
    assert r.kind == "connect_timeout" and r.error == "연결 시간 초과(3초)", r


class _Drip:
    """바이트를 조금씩 흘리는 서버 — body(머리는 곧바로 · 몸을 0.2초마다 한 바이트) · headers(머리부터 0.2초마다 한 바이트). recv 하나하나는 소켓
    시간 초과 안에 들어온다 — 기한을 주기 사이에서만 재면 끝없이 붙든다(반대 검토 11-02 · 재현 drip.py)."""

    def __init__(self, mode: str):
        self.mode = mode
        self.srv = socket.socket()
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srv.bind(("127.0.0.1", 0))
        self.srv.listen(5)
        self.port = self.srv.getsockname()[1]
        threading.Thread(target=self._accept, daemon=True).start()

    def _accept(self) -> None:
        while True:
            try:
                c, _ = self.srv.accept()
            except OSError:
                return
            threading.Thread(target=self._drip, args=(c,), daemon=True).start()

    def _drip(self, c: socket.socket) -> None:
        try:
            c.recv(65536)
            if self.mode == "body":
                c.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 200000\r\n\r\n")
                data = b"x" * 200000
            else:
                data = b"HTTP/1.1 200 OK\r\nX-Slow: " + b"y" * 100000
            for i in range(len(data)):
                c.sendall(data[i:i + 1])
                time.sleep(0.2)
        except OSError:
            pass
        finally:
            c.close()

    def close(self) -> None:
        self.srv.close()


@pytest.mark.parametrize("mode", ["body", "headers"])
def test_읽기_기한은_조금씩_흘리는_서버에도_머리부터_몸까지_하나다(mode):
    """recv 마다는 소켓 시간 초과 안이라 기한을 덩이 사이에서만 재면 끝없이 붙들렸다(20초에도 그대로 — 반대 검토 11-02). 기한이 지나면 소켓을 닫아
    막힌 recv 를 깨우고, 그 뒤 http.client 가 낸 것(잘린 머리 · 몸)은 모두 읽기 시간 초과다(OD-31)."""
    d = _Drip(mode)
    got: dict = {}
    try:
        t0 = time.monotonic()
        th = threading.Thread(target=lambda: got.update(r=C.fetch(C.Addr("http", "127.0.0.1", d.port), "/metrics", read_s=1.0),
                                                        took=time.monotonic() - t0), daemon=True)
        th.start()
        th.join(6)                                # 붙들려도 시험은 끝난다(실패로)
    finally:
        d.close()
    assert "r" in got, "기한 1초인데 6초 뒤에도 붙들려 있다"
    assert got["took"] < 2.5, f"기한 1초인데 {got['took']:.1f}초 붙들렸다"
    r = got["r"]
    assert r.kind == "read_timeout" and r.status is None and r.body == b"" and "읽기 시간 초과(1초)" in r.error, r


def test_지표가_vLLM_꼴이_아니면_까닭을_말하고_대상은_남는다(tmp_path, fakes):
    f = fakes()
    f.mode = "garbage"
    coll = _collector(tmp_path, f"LLM_BASE_URL={f.base}\n")
    coll.poll_vllm(_state(coll, "glm"))
    v = _vals(coll.snapshot(), "glm")
    assert v["up"]["value"] is True, "/health 는 200 이다"
    assert v["running"]["value"] is None and "vLLM 모양이 아니다" in v["running"]["error"], v["running"]
    assert v["kv"]["error"] == v["running"]["error"]
    f.mode = "one_bad_line"
    coll.poll_vllm(_state(coll, "glm"))
    t = next(x for x in coll.snapshot()["targets"] if x["id"] == "glm")
    assert t["values"]["running"]["value"] == 2.0 and t["sources"]["metrics"]["bad_lines"] == 1, "한 줄 때문에 지표 전체를 잃지 않고 센다"


def test_스냅숏의_모든_값은_value_at_source_error_와_낡음이다(tmp_path, fakes):
    f = fakes(key=KEY)
    agent = fakes(FakeJson, {"/health": (200, {"status": "ok", "delib_active": 1})})
    clock = Clock()
    coll = _collector(tmp_path, f"LLM_BASE_URL={f.base}\nLLM_API_KEY={KEY}\nLLM_STATUS_AGENT_URL=http://127.0.0.1:{agent.port}\n",
                      clock=clock)
    coll.poll_vllm(_state(coll, "glm"))
    coll.poll_agent(coll.agent)
    want = {"value", "at", "source", "error", "stale", "age_s"}

    def cells(snap):
        for t in snap["targets"]:
            yield from t["values"].items()
        yield from snap["agent"]["values"].items()
        yield "slurm", snap["slurm"]
        yield "gpu", snap["gpu"]
        yield "context", snap["context"]
    snap = coll.snapshot()
    for name, c in cells(snap):
        assert want <= set(c), (name, c)
        assert c["value"] is not None or c["error"], f"{name} 는 값도 까닭도 없다 — '모름 — 까닭' 이어야 한다"
    v = _vals(snap, "glm")
    assert set(v) == {*C.VLLM_VALUES, "context_mismatch"} and v["running"]["source"] == "metrics" and v["models"]["source"] == "models"
    clock.tick(44)
    assert _vals(coll.snapshot(), "glm")["running"]["stale"] is False
    clock.tick(2)                                 # 15초 주기 셋을 놓쳤다(45초 넘음)
    v = _vals(coll.snapshot(), "glm")
    assert v["running"]["stale"] is True and v["running"]["value"] == 2.0, "낡아도 마지막 값은 남긴다(표지만 단다)"
    assert v["models"]["stale"] is False, "모델 목록은 60초 주기 — 180초까지는 낡지 않았다"
    assert coll.snapshot()["agent"]["values"]["delib_active"]["stale"] is True
    clock.tick(140)
    assert _vals(coll.snapshot(), "glm")["models"]["stale"] is True


def test_설정된_대상은_숨기지_않고_모름과_까닭을_보이며_주소_원문을_되비추지_않는다(tmp_path):
    dead = _free_port()
    coll = _collector(tmp_path, "LLM_STATUS_TARGETS=DEAD=http://127.0.0.1:%d/v1,nolabel,SECRET=http://user:pw-should-not-show@h.example:1/v1,"
                                "한글=http://127.0.0.1:1/v1,BAD=http://127.0.0.1:1/v2\n"
                                "LLM_STATUS_REPLICA_PORTS=18711-18712\n" % dead)
    coll.poll_vllm(_state(coll, "DEAD"))
    snap = coll.snapshot()
    ids = [t["id"] for t in snap["targets"]]
    assert ids == ["DEAD", "item-2", "SECRET", "item-4", "BAD", "chat-replicas"], ids
    v = _vals(snap, "DEAD")
    assert v["up"]["value"] is False and "연결 거부" in v["up"]["error"]
    assert v["running"]["value"] is None and "연결 거부" in v["running"]["error"]
    for tid, needle in (("item-2", "이름=주소/v1"), ("SECRET", "계정(user@)"), ("item-4", "영숫자"), ("BAD", "/v1"),
                        ("chat-replicas", "CHAT_LLM_BASE_URL")):
        t = next(x for x in snap["targets"] if x["id"] == tid)
        assert t["problem"] and needle in t["problem"], (tid, t["problem"])
        assert all(c["value"] is None and c["error"].startswith("모름 — ") for c in t["values"].values()), tid
    text = C.dumps(snap).decode()
    assert "pw-should-not-show" not in text and "user:" not in text and "://" not in text, "주소 원문(계정 · 스킴)을 되비추지 않는다"


def test_주소는_호스트_포트만_내고_키는_답에도_로그에도_나가지_않는다(tmp_path, fakes, capsys):
    f = fakes(key=KEY)
    agent = fakes(FakeJson, {"/health": (200, {
        "status": "ok", "delib_active": 2, "delib_queued": 1, "delib_seats_running": 9, "delib_paused": False,
        "routine_active": 1, "routine_parked": 0, "routine_max": 2, "review_active": 3,
        "card_review": {"active": 3, "limit": 8, "limit_reason": f"note {KEY}", "delib_human": 1, "retry_after_s": 30, "totals": {"x": 1}},
        "load": {"chat": {"active": 4, "window": 50, "ttft_ms": {"idle": {"n": 12, "p50": 800, "p95": 2100},
                                                                "review": {"n": 0, "p50": None, "p95": None}},
                          "ratio_p50": None, "slow": False, "slow_since": None}},
        "chat_llm": {"enabled": True, "server": "127.0.0.1:18700", "model": "qwen-test", "thinking": True, "effort": "xhigh",
                     "streaming": False, "ctx_tokens": 262144, "fallback": {"enabled": True, "to": "glm", "count": 5, "last_at": 1.0},
                     "last_error": f"APIConnectionError: http://svc:{KEY}@10-not-ip.example:18700/v1 Bearer {KEY}",
                     "last_error_at": 2.0},
        "context_tokens": 200000, "model": "glm-test", "vllm": f"http://user:{KEY}@gpu.example:8000/v1",
        "mcp": ["a"], "tool_load_errors": {"x": "boom http://h.example:1/"}})})
    coll = _collector(tmp_path, f"LLM_BASE_URL={f.base}\nLLM_API_KEY={KEY}\nLLM_STATUS_AGENT_URL=http://127.0.0.1:{agent.port}\n")
    coll.poll_all_once(timeout=20)
    snap = coll.snapshot()
    text = C.dumps(snap).decode()
    assert KEY not in text and "://" not in text, "키 · 주소 원문이 답에 섞였다"
    a = snap["agent"]["values"]
    assert set(a) == set(C.AGENT_VALUES), "정한 칸만 싣는다(vllm · mcp · tool_load_errors 는 안 싣는다)"
    assert a["delib_active"]["value"] == 2 and a["delib_seats_running"]["value"] == 9 and a["chat_active"]["value"] == 4
    assert a["card_review"]["value"] == {"active": 3, "limit": 8, "limit_reason": "note <가림>", "delib_human": 1, "retry_after_s": 30}, \
        "주소 꼴이 아닌 글에 섞인 키도 답을 내기 직전에 가린다(마지막 그물)"
    assert a["chat_llm"]["value"]["fallback"] == {"enabled": True, "count": 5, "last_at": 1.0}
    assert "10-not-ip.example:18700" in a["chat_llm"]["value"]["last_error"] and "<가림>" in a["chat_llm"]["value"]["last_error"]
    assert "HWAX 에이전트 서버가 보는 몫만" in snap["agent"]["caption"]
    assert next(t for t in snap["targets"] if t["id"] == "glm")["addr"] == f"127.0.0.1:{f.port}"
    out = capsys.readouterr()
    assert KEY not in out.out + out.err, "키가 로그에 나갔다"


def test_기본_대상은_LLM_UPSTREAMS_먼저_없으면_LLM_BASE_URL_그리고_챗_LLM():
    cfg = C.build_config(C.env_values("LLM_UPSTREAMS=http://a.example:8000/v1,http://b.example:8000/v1/\n"
                                      "LLM_BASE_URL=http://c.example:8000/v1\nCHAT_LLM_BASE_URL=http://127.0.0.1:18700/v1\n"
                                      "LLM_ROUTER_PORT=18730\n"))
    assert [(t.id, t.label, str(t.addr), t.key) for t in cfg.targets] == [
        ("glm-1", "GLM-1", "a.example:8000", "llm"), ("glm-2", "GLM-2", "b.example:8000", "llm"),
        ("chat", "챗 LLM", "127.0.0.1:18700", "chat")], "LLM_UPSTREAMS 가 있으면 LLM_BASE_URL 은 보지 않는다(같은 서버를 두 번 묻지 않게)"
    assert str(cfg.router) == "127.0.0.1:18730", "풀을 켠 박스만 라우터를 본다"
    cfg = C.build_config(C.env_values("LLM_BASE_URL=http://c.example:8000/v1\nCHAT_LLM_BASE_URL=http://c.example:8000/v1\n"))
    assert [(t.id, t.problem) for t in cfg.targets][0] == ("glm", None) and "이미 GLM 로 읽는다" in cfg.targets[1].problem, \
        "같은 서버는 한 번만 — 둘째는 까닭과 함께 남는다"
    assert cfg.router is None and str(cfg.agent) == "127.0.0.1:9009"
    cfg = C.build_config(C.env_values("LLM_STATUS_TARGETS=GLM-1=http://a.example:8000/v1,Q=http://127.0.0.1:18700/v1\n"
                                      "LLM_UPSTREAMS=http://z.example:1/v1\nCHAT_LLM_BASE_URL=http://127.0.0.1:18700/v1\n"))
    assert [(t.id, t.key) for t in cfg.targets] == [("GLM-1", "llm"), ("Q", "chat")], "LLM_STATUS_TARGETS 가 있으면 그것만 · 키는 주소로 고른다"
    many = ",".join(f"T{i}=http://127.0.0.1:{20000 + i}/v1" for i in range(C.TARGET_MAX + 2))
    cfg = C.build_config(C.env_values(f"LLM_STATUS_TARGETS={many}\n"))
    assert len(cfg.targets) == C.TARGET_MAX + 2 and all("넘어" in t.problem for t in cfg.targets[C.TARGET_MAX:]), "상한을 넘은 것도 숨기지 않는다"
    assert C.build_config(C.env_values("")).targets == ()


def test_짝_파일은_줄_꼴과_JSON_꼴을_읽고_못_읽으면_포트로만_돈다(tmp_path):
    f = tmp_path / "m.txt"
    f.write_text("18711 node-a\nnode-b 18712\n18713: node-c  # 설명\nbad line\n18714 bad/name\n", encoding="utf-8")
    assert C.read_replica_map(str(f)) == ({18711: "node-a", 18712: "node-b", 18713: "node-c"}, None)
    f.write_text(json.dumps({"18711": "node-a", "x": "y"}), encoding="utf-8")
    assert C.read_replica_map(str(f)) == ({18711: "node-a"}, None)
    f.write_text(json.dumps([{"port": 18712, "host": "node-b"}]), encoding="utf-8")
    assert C.read_replica_map(str(f)) == ({18712: "node-b"}, None)
    nodes, why = C.read_replica_map(str(tmp_path / "nope"))
    assert nodes == {} and "읽지 못했다" in why
    cfg = C.build_config(C.env_values(f"CHAT_LLM_BASE_URL=http://127.0.0.1:18700/v1\nLLM_STATUS_REPLICA_PORTS=18711-18713\n"
                                      f"LLM_STATUS_REPLICA_MAP={tmp_path / 'nope'}\n"))
    assert [t.id for t in cfg.targets] == ["chat", "chat-18711", "chat-18712", "chat-18713"] and any("짝 파일" in p for p in cfg.problems)
    for bad, needle in (("18720-18711", "거꾸로"), ("1-200", "넘는다"), ("18711,x", "포트")):
        cfg = C.build_config(C.env_values(f"CHAT_LLM_BASE_URL=http://127.0.0.1:18700/v1\nLLM_STATUS_REPLICA_PORTS={bad}\n"))
        assert cfg.targets[-1].id == "chat-replicas" and needle in cfg.targets[-1].problem, (bad, cfg.targets[-1])


def test_라우터는_LLM_UPSTREAMS_가_있을_때만_보고_주소는_호스트_포트만(tmp_path, fakes):
    rt = fakes(FakeJson, {"/health": (503, {"status": "down", "upstreams_total": 2, "upstreams_up": 0, "inflight": 3,
                                            "models": {"match": None}}),
                          "/stats": (200, [{"url": "http://a.example:8000/v1", "up": False, "reachable": False, "running": None,
                                            "waiting": None, "kv": None, "inflight": 3, "sent": 10, "connect_fail": 2,
                                            "models": "unknown"}])})
    coll = _collector(tmp_path, f"LLM_UPSTREAMS=http://127.0.0.1:{_free_port()}/v1\nLLM_ROUTER_PORT={rt.port}\n")
    coll.poll_router(coll.router)
    r = coll.snapshot()["router"]
    assert r["values"]["up"]["value"] is True and r["values"]["status"]["value"] == "down", "503 이어도 라우터는 답했다"
    assert r["values"]["upstreams"]["value"][0]["addr"] == "a.example:8000" and r["values"]["inflight"]["value"] == 3
    assert "://" not in C.dumps(r).decode()
    (tmp_path / "n").mkdir()
    assert _collector(tmp_path / "n", "LLM_BASE_URL=http://127.0.0.1:1/v1\n").snapshot()["router"] is None


# ── 시계열 · 저장 ──────────────────────────────────────────────────────────────────────────────────
def test_시계열_1h_는_표본_24h_는_5분_칸이고_48시간_35일이_지나면_지운다(tmp_path):
    S = sys.modules["samplestore"]
    st = S.Store(tmp_path / "x.sqlite")
    t0 = 1_800_000_000 // 300 * 300
    for i in range(40):                                      # 10분(15초마다) — 5분 칸 둘
        st.add("glm", t0 + 15 * i, {"running": float(i % 4), "waiting": None, "kv": float("nan")})
    now = t0 + 15 * 40
    s = st.series("glm", "running", "1h", now=now)
    assert s["source"] == "raw" and s["step_s"] == 15 and len(s["points"]) == 40 and s["points"][0] == [t0, 0.0]
    assert st.series("glm", "waiting", "1h", now=now)["points"] == [] and st.series("glm", "kv", "1h", now=now)["points"] == [], \
        "None · NaN 은 적지 않는다(빈칸)"
    st.maintain(now, force=True)
    s = st.series("glm", "running", "24h", now=now)
    assert s["source"] == "rollup:5m" and s["step_s"] == 300
    assert [p[0] for p in s["points"]] == [t0, t0 + 300], "칸이 끝나고 60초 뒤에 접는다 — 둘째 칸의 끝은 표본으로 잇는다"
    assert s["points"][0][1] == pytest.approx(1.5) and s["points"][0][2] == 3.0, "[칸 시작, 평균, 최대]"
    st.maintain(now + 3600, force=True)
    s7 = st.series("glm", "running", "7d", now=now + 3600)
    assert s7["step_s"] == 1800 and len(s7["points"]) == 1 and s7["points"][0][1] == pytest.approx(1.5)
    st.maintain(t0 + 48 * 3600 + 15 * 40 + 1, force=True)
    assert st.series("glm", "running", "1h", now=now)["points"] == [], "48시간 지난 표본은 지운다"
    assert len(st.series("glm", "running", "35d", now=t0 + 48 * 3600)["points"]) == 1, "접은 칸은 남는다"
    st.maintain(t0 + 36 * 86400, force=True)
    assert st.series("glm", "running", "35d", now=t0 + 36 * 86400)["points"] == [], "35일 지난 칸도 지운다"
    st.close()


def test_되돌린_쓰기가_만든_계열_번호는_남기지_않는다(tmp_path):
    """새 계열의 첫 쓰기가 되돌려지면(디스크 가득 · I/O 오류) series 줄도 사라진다 — 그 번호를 캐시에 남기면 다음 새 계열이 같은 번호를 받아 두 계열이
    한 번호를 나눠 쓰고 같은 초의 값을 서로 덮는다(반대 검토 11-02 LOW-MED · 재현 store_rollback.py). 캐시는 COMMIT 된 줄만 남긴다."""
    S = sys.modules["samplestore"]
    st = S.Store(tmp_path / "x.sqlite")
    st.conn.execute("CREATE TEMP TRIGGER boom BEFORE INSERT ON raw WHEN NEW.v = -999 BEGIN SELECT RAISE(ABORT, 'disk full (simulated)'); END")
    st.add("glm-1", 1000, {"running": 1.0, "waiting": -999.0})
    assert st.error and "disk full" in st.error, "쓰기 실패는 저장소 칸에 보인다"
    assert st.conn.execute("SELECT COUNT(*) FROM series").fetchone()[0] == 0 and st._sids == {}, "되돌린 계열 번호를 캐시에 남기지 않는다"
    st.add("chat", 1015, {"kv": 0.5})
    st.add("glm-1", 1015, {"running": 2.0})
    assert st.series("chat", "kv", "1h", now=1100)["points"] == [[1015, 0.5]], "다른 계열이 덮지 않는다"
    assert st.series("glm-1", "running", "1h", now=1100)["points"] == [[1015, 2.0]]
    rows = st.conn.execute("SELECT id, target, metric FROM series ORDER BY id").fetchall()
    assert len({i for i, _, _ in rows}) == len(rows) == 2 and st._sids == {(t, m): i for i, t, m in rows}, rows
    assert st.error is None, "다음 쓰기가 되면 오류 칸이 풀린다"
    st.close()


def test_시계열_창구는_모르는_대상_지표_범위를_거절하고_어림을_표시한다(tmp_path, fakes):
    f = fakes()
    coll = _collector(tmp_path, f"LLM_BASE_URL={f.base}\n")
    coll.poll_vllm(_state(coll, "glm"))
    body, code = coll.series_view("glm", "running", "1h")
    assert code == 200 and body["target"] == "glm" and body["approx"] is False and len(body["points"]) == 1
    assert coll.series_view("nope", "running", "1h")[1] == 404
    assert coll.series_view("glm", "nope", "1h")[1] == 400 and coll.series_view("glm", "running", "2y")[1] == 400
    assert coll.series_view("glm", "ttft_p95", "1h")[0]["approx"] is True
    assert coll.series_view("agent", "delib_active", "24h")[1] == 200 and coll.series_view("agent", "running", "1h")[1] == 400


def test_Slurm_GPU_는_무엇이_필요한지_말하는_모름이고_클러스터는_규모로_부른다(tmp_path):
    snap = _collector(tmp_path, "").snapshot()
    assert snap["slurm"]["value"] is None and "Q8" in snap["slurm"]["error"] and "stcx(356대)" in snap["slurm"]["error"]
    assert snap["gpu"]["value"] is None and "Q11" in snap["gpu"]["error"] and "Q12" in snap["gpu"]["error"]
    assert snap["slurm"]["milestone"] == "M3" and snap["gpu"]["milestone"] == "M4"
    from tests.test_cluster_naming import ALIAS_CTX, BARE_STC   # 리포를 가로지르는 가드의 정본 식(이 시험은 그 가드가 아직 보지 않는 사본에서도 돈다)
    for p in (*LS.glob("*.py"), LAUNCHER):
        hits = [ln for ln in p.read_text(encoding="utf-8").splitlines() if BARE_STC.search(ln) and not ALIAS_CTX.search(ln)]
        assert not hits, f"{p.name} 에 클러스터 이름을 옛 이름으로 적은 줄이 있다 — 356대는 stcx, 24대는 ste: {hits[:3]}"


# ── 띄우는 스크립트 ───────────────────────────────────────────────────────────────────────────────
@pytest.fixture
def repo(tmp_path):
    """임시 포털 리포 — 띄우는 스크립트와 수집기 사본(이 박스의 infra/.state · infra/.env 를 쓰지 않는다)."""
    r = (tmp_path / "HWAXPortal").resolve()
    (r / "infra/scripts").mkdir(parents=True)
    shutil.copytree(LS, r / "infra/llm-status", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(LAUNCHER, r / "infra/scripts/llm-status.sh")
    return r


def _env(repo: Path, **extra) -> dict:
    return {"PATH": os.environ["PATH"], "HOME": str(repo.parent), **extra}


def _wait_health(port: int, proc=None, timeout: float = 20.0) -> dict:
    end = time.monotonic() + timeout
    while True:
        try:
            code, body = _get(f"http://127.0.0.1:{port}/health", timeout=1)
            if code == 200:
                return body
        except OSError:
            pass
        assert time.monotonic() < end and (proc is None or proc.poll() is None), "수집기가 뜨지 않았다"
        time.sleep(0.05)


def _listener(port: int, *tag: str) -> subprocess.Popen:
    code = ("import socket,sys,time; s=socket.socket(); s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1); "
            "s.bind(('127.0.0.1',int(sys.argv[1]))); s.listen(); time.sleep(120)")
    p = subprocess.Popen([sys.executable, "-c", code, str(port), *tag], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    end = time.monotonic() + 10
    while True:
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            return p
        except OSError:
            if time.monotonic() > end:
                p.kill()
                raise
            time.sleep(0.05)


def test_run_은_환경을_비우고_시스템_python3_으로_루프백_한_포트에서_돈다(repo, fakes):
    f = fakes(key=KEY)
    port = _free_port()
    (repo / "infra/.env").write_text(f"LLM_STATUS=1\nLLM_STATUS_PORT={port}\nLLM_BASE_URL={f.base}\nLLM_API_KEY={KEY}\n"
                                     f"LLM_STATUS_AGENT_URL=http://127.0.0.1:{_free_port()}\n", encoding="utf-8")
    log = repo.parent / "run.log"
    with open(log, "wb") as lf:
        proc = subprocess.Popen(["bash", str(repo / "infra/scripts/llm-status.sh"), "run"], stdout=lf, stderr=subprocess.STDOUT,
                                env=_env(repo, SHELL_SECRET="from-shell", LLM_API_KEY="shell-key-0000000000", http_proxy="http://proxy.test:3128"),
                                start_new_session=True)
    try:
        h = _wait_health(port, proc)
        assert h["status"] == "ok" and h["enabled"] is True and h["targets"] == 1 and h["service"] == "hwax-llm-status"
        pr = subprocess.run(["bash", str(repo / "infra/scripts/llm-status.sh"), "probe"], capture_output=True, text=True, timeout=30,
                            env=_env(repo))
        assert pr.returncode == 0 and "수집기의 답이다" in pr.stdout, "update-all 5d 가 내리기 전에 묻는 표지(OD-28)"
        pid = proc.pid                                       # exec 라 bash 의 pid 가 곧 수집기다
        argv = Path(f"/proc/{pid}/cmdline").read_bytes().rstrip(b"\0").split(b"\0")
        env = dict(x.split(b"=", 1) for x in Path(f"/proc/{pid}/environ").read_bytes().split(b"\0") if b"=" in x)
        assert argv[:3] == [b"/usr/bin/python3", b"-I", b"-B"] or argv[1:3] == [b"-I", b"-B"], argv
        assert argv[-3:] == [b"serve", b"--port", str(port).encode()], argv
        assert set(env) == {b"PATH", b"HOME", b"LANG"}, f"띄운 셸의 환경이 딸려 들어갔다 — {sorted(env)}"
        assert all(KEY.encode() not in x for x in argv + list(env.values())), "키가 명령줄 · 환경에 있다"
        end = time.monotonic() + 10
        while True:
            code, snap = _get(f"http://127.0.0.1:{port}/snapshot")
            if code == 200 and snap["targets"][0]["values"]["models"]["value"]:
                break
            assert time.monotonic() < end, snap
            time.sleep(0.1)
        assert snap["targets"][0]["values"]["models"]["value"][0]["id"] == "glm-test", "키는 수집기가 infra/.env 에서 스스로 읽었다"
        code, s = _get(f"http://127.0.0.1:{port}/series?target=glm&metric=up&range=1h")
        assert code == 200 and s["points"] and s["points"][-1][1] == 1.0
        assert _get(f"http://127.0.0.1:{port}/nope")[0] == 404
        state = repo / "infra/.state/llm-status"
        assert oct(state.stat().st_mode & 0o777) == "0o700" and oct((state / "llm-status.sqlite").stat().st_mode & 0o777) == "0o600"
        r = subprocess.run(["bash", str(repo / "infra/scripts/llm-status.sh"), "stop"], capture_output=True, text=True, timeout=30,
                           env=_env(repo))
        assert r.returncode == 0 and "내려갔다" in r.stdout and proc.wait(10) is not None, r.stdout + r.stderr
    finally:
        if proc.poll() is None:
            proc.kill()
    text = log.read_text(encoding="utf-8")
    assert KEY not in text and "shell-key" not in text and "시작 — 127.0.0.1:%d" % port in text, text
    assert not list((repo / "infra/llm-status").rglob("__pycache__")), "바이트코드를 남기지 않는다(-B)"


def test_start_는_뒤에서_띄우고_곧바로_돌아온다(repo):
    """nohup + disown — `( … & )` 서브셸이면 호출자가 자식 수명만큼 매달린다. 걸린 시간을 단언한다."""
    port = _free_port()
    (repo / "infra/.env").write_text(f"LLM_STATUS_PORT={port}\nLLM_STATUS_AGENT_URL=http://127.0.0.1:{_free_port()}\n", encoding="utf-8")
    log = repo.parent / "logs/llm-status.log"
    t0 = time.monotonic()
    r = subprocess.run(["bash", str(repo / "infra/scripts/llm-status.sh"), "start"], capture_output=True, text=True, timeout=30,
                       env=_env(repo, LLM_STATUS_LOG=str(log)))
    took = time.monotonic() - t0
    try:
        assert r.returncode == 0 and "뒤에서 띄웠다" in r.stdout, r.stdout + r.stderr
        assert took < 5, f"start 가 {took:.1f}초 매달렸다"
        assert "LLM_STATUS 가 없다" in r.stderr, "꺼진 박스에서 손으로 띄우면 알린다(다음 update-all 이 내린다)"
        assert _wait_health(port)["status"] == "ok", "start 가 끝난 뒤에도 수집기는 돈다"
        assert oct(log.stat().st_mode & 0o777) == "0o600" and oct(log.parent.stat().st_mode & 0o777) == "0o700"
        again = subprocess.run(["bash", str(repo / "infra/scripts/llm-status.sh"), "start"], capture_output=True, text=True,
                               timeout=30, env=_env(repo, LLM_STATUS_LOG=str(log)))
        assert again.returncode == 0 and "이미 듣는" in again.stdout
    finally:
        s = subprocess.run(["bash", str(repo / "infra/scripts/llm-status.sh"), "stop"], capture_output=True, text=True, timeout=30,
                           env=_env(repo))
    assert s.returncode == 0 and "내려갔다" in s.stdout, s.stdout + s.stderr


def test_stop_은_그_포트를_듣는_수집기만_내린다(repo):
    port = _free_port()
    (repo / "infra/.env").write_text(f"LLM_STATUS_PORT={port}\n", encoding="utf-8")

    def stop(**env):
        return subprocess.run(["bash", str(repo / "infra/scripts/llm-status.sh"), "stop"], capture_output=True, text=True,
                              timeout=30, env=_env(repo, **env))
    r = stop()
    assert r.returncode == 0 and "이미 내려가 있다" in r.stdout
    other = _listener(port, "--note", "/tmp/infra/llm-status/collector.py.bak", "serve")
    try:
        r = stop()
        assert r.returncode == 1 and "수집기가 아니다" in r.stderr and other.poll() is None, "남의 리스너는 건드리지 않는다"
    finally:
        other.kill()
        other.wait(10)
    mine = _listener(port, "/x/infra/llm-status/collector.py", "serve", "--port", str(port))
    try:
        r = stop()
        assert r.returncode == 0 and "내려갔다" in r.stdout and mine.wait(10) is not None, r.stdout + r.stderr
    finally:
        if mine.poll() is None:
            mine.kill()
    old = _listener(port, "/x/infra/llm-status/collector.py", "serve")
    try:
        (repo / "infra/.env").write_text(f"LLM_STATUS_PORT={_free_port()}\n", encoding="utf-8")
        r = stop(LLM_STATUS_PORT=str(port))
        assert r.returncode == 0 and f":{port}" in r.stdout and old.wait(10) is not None, "stop 만 환경의 포트(옛 포트)를 먼저 본다"
    finally:
        if old.poll() is None:
            old.kill()


def test_start_check_는_그_포트를_듣는_것이_수집기인지_명령줄로_본다(repo):
    """반대 검토 11-02 LOW — start 는 그 포트에 듣는 것이 있기만 하면 '이미 떠 있다' 로 0 을 냈다(남의 앱이어도). stop 과 같은 명령줄 판정으로 보고,
    남이면 띄우지 않고 크게 실패한다. check 는 update-sites 가 재기동을 생략하기 전에 묻는 같은 판정이다(OD-29)."""
    port = _free_port()
    (repo / "infra/.env").write_text(f"LLM_STATUS=1\nLLM_STATUS_PORT={port}\n", encoding="utf-8")
    log = repo.parent / "logs/llm-status.log"

    def run(cmd):
        return subprocess.run(["bash", str(repo / "infra/scripts/llm-status.sh"), cmd], capture_output=True, text=True, timeout=30,
                              env=_env(repo, LLM_STATUS_LOG=str(log)))
    r = run("check")
    assert r.returncode == 1 and "듣는 프로세스가 없다" in r.stderr, r.stdout + r.stderr
    other = _listener(port, "--note", "/tmp/infra/llm-status/collector.py.bak", "serve")
    try:
        r = run("start")
        assert r.returncode == 1 and "수집기가 아니다" in r.stderr and "띄우지 않았다" in r.stderr, r.stdout + r.stderr
        assert not log.exists(), "남이 쥔 포트에 수집기를 띄우지 않는다"
        r = run("check")
        assert r.returncode == 1 and "수집기가 아니다" in r.stderr and other.poll() is None, r.stdout + r.stderr
    finally:
        other.kill()
        other.wait(10)
    mine = _listener(port, "/x/infra/llm-status/collector.py", "serve", "--port", str(port))
    try:
        r = run("start")
        assert r.returncode == 0 and "이미 듣는 수집기가 있다" in r.stdout and f"pid {mine.pid}" in r.stdout, r.stdout + r.stderr
        r = run("check")
        assert r.returncode == 0 and "수집기다" in r.stdout and mine.poll() is None, r.stdout + r.stderr
    finally:
        mine.kill()
        mine.wait(10)


@pytest.mark.parametrize("line, needle", [("LLM_STATUS_PORT=87x0\n", "LLM_STATUS_PORT='87x0'"), ("LLM_STATUS_PORT=70000\n", "1~65535")])
def test_run_은_포트_손잡이가_틀리면_띄우지_않는다(repo, line, needle):
    (repo / "infra/.env").write_text(line, encoding="utf-8")
    r = subprocess.run(["bash", str(repo / "infra/scripts/llm-status.sh"), "run"], capture_output=True, text=True, timeout=30,
                       env=_env(repo))
    assert r.returncode == 2 and needle in r.stderr, r.stderr


def test_상태_디렉터리를_다른_수집기가_쥐면_띄우지_않는다(tmp_path):
    state = tmp_path / "state"
    state.mkdir()
    with open(state / ".lock", "a") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock, store, why = C.open_state(state)
        assert lock is None and store is None and "다른 수집기" in why and "llm-status.sh stop" in why
    lock, store, why = C.open_state(state)
    assert store is not None and why is None
    assert oct(state.stat().st_mode & 0o777) == "0o700" and oct((state / C.DB_NAME).stat().st_mode & 0o777) == "0o600"
    store.close()
    lock.close()
