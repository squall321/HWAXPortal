# LLM 라우터(infra/llm-router/llm_router.py) — 진짜 HTTP 로 뜬 가짜 vLLM 둘 앞에서 고르기·붙임·넘김·스트림·끊김 전파·키·다시 읽기를 본다(docs/llm-pool)
"""왜 — 라우터는 몇 시간 도는 카드 대조·심의의 LLM 호출이 전부 지나는 자리다. 여기서 틀리면 조용히 틀린다 — waiting 을 두 배로 세면
한쪽 서버만 바쁘다고 읽고, 연결된 뒤의 실패를 다시 보내면 같은 답을 두 번 만들고, 손님이 떠난 생성을 닫지 않으면 GPU 를 버려진 생성이 잡는다.

가짜 vLLM 은 uvicorn 으로 띄운 진짜 서버다(스레드마다 이벤트 루프 하나). 지표·모델·응답 모양과 실패 모양을 시험이 정하고, 받은 요청과
손님(라우터)이 끊은 시각을 적는다. 끊김 전파는 대역으로는 못 본다 — 손님 소켓을 실제로 닫고 위 서버가 그것을 1초 안에 보는지 잰다.
주소는 루프백만 쓴다(내부 IP 는 추적 파일 금지).
"""
import asyncio
import importlib.util
import json
import logging
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx
import pytest
import uvicorn
import yaml

ROOT = Path(__file__).resolve().parents[2]
ROUTER_PY = ROOT / "infra/llm-router/llm_router.py"
LAUNCHER = ROOT / "infra/scripts/llm-router.sh"
UA = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")


def _load_router():
    spec = importlib.util.spec_from_file_location("hwax_llm_router", ROUTER_PY)
    m = importlib.util.module_from_spec(spec)
    sys.modules["hwax_llm_router"] = m
    keep, sys.dont_write_bytecode = sys.dont_write_bytecode, True   # 지문(services.yaml fp: infra/llm-router)에 __pycache__ 를 남기지 않는다
    try:
        spec.loader.exec_module(m)
    finally:
        sys.dont_write_bytecode = keep
    return m


R = _load_router()


# ── 진짜 서버 띄우기 ──────────────────────────────────────────────────────────────────────────────
class _Srv:
    """uvicorn 하나를 스레드에서 띄운다. port 를 주면 그 포트로(다시 띄우기)."""

    def __init__(self, app, *, port: int = 0, http: str = "auto", lifespan: str = "off"):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", port))
        self.port = self.sock.getsockname()[1]
        self.lifespan = lifespan
        cfg = uvicorn.Config(app, log_config=None, log_level="warning", lifespan=lifespan, http=http, timeout_graceful_shutdown=1)
        self.server = uvicorn.Server(cfg)
        self.thread = threading.Thread(target=lambda: asyncio.run(self.server.serve(sockets=[self.sock])), daemon=True)
        self.thread.start()
        deadline = time.monotonic() + 20
        while not self.server.started:
            if not self.thread.is_alive() or time.monotonic() > deadline:
                raise RuntimeError("서버가 뜨지 않았다")
            time.sleep(0.01)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def stop(self) -> None:
        if not self.thread.is_alive():
            return
        self.server.should_exit = True
        self.server.force_exit = self.lifespan == "off"     # 라우터는 lifespan 종료(stop)까지 태운다
        self.thread.join(15)
        self.sock.close()


async def _until_gone(receive) -> None:
    while (await receive())["type"] != "http.disconnect":
        pass


async def _send_json(send, status: int, obj, headers=()) -> None:
    data = json.dumps(obj).encode()
    await send({"type": "http.response.start", "status": status, "headers": [(b"content-type", b"application/json"), *headers]})
    await send({"type": "http.response.body", "body": data})


SSE = [(b"content-type", b"text/event-stream"), (b"cache-control", b"no-cache")]


class _Fake:
    """가짜 vLLM. mode — json · sse · 500 · break(머리와 한 조각 뒤 끊음) · hold(머리 전에 붙든다) · hold_stream(한 조각 뒤 붙든다) · slow(3초 침묵)."""

    def __init__(self, name: str, *, running=0.0, waiting=0.0, kv=0.0, model="glm", max_len=1_048_576):
        self.name, self.running, self.waiting, self.kv = name, running, waiting, kv
        self.model, self.max_len = model, max_len
        self.mode = "json"
        self.metrics_mode = "ok"
        self.hits: list[dict] = []          # 채팅·그 밖의 넘어온 요청
        self.model_hits: list[dict] = []    # /v1/models 요청의 머리
        self.gone: list[float] = []         # 손님(라우터)이 끊은 것을 본 시각
        self.release = threading.Event()
        self.srv: _Srv | None = None

    @property
    def base(self) -> str:
        return f"{self.srv.url}/v1"

    def metrics_text(self) -> str:
        lab = 'engine="0",model_name="m"'
        return "\n".join([
            "# HELP vllm:num_requests_running Number of requests in model execution batches.",
            "# TYPE vllm:num_requests_running gauge",
            f"vllm:num_requests_running{{{lab}}} {self.running}",
            f"vllm:num_requests_waiting{{{lab}}} {self.waiting}",
            # 함정 — 같은 접두의 다른 지표(합이 waiting 과 같다). 접두로 세면 waiting 이 두 배가 된다
            f'vllm:num_requests_waiting_by_reason{{{lab},reason="capacity"}} {self.waiting}',
            f'vllm:num_requests_waiting_by_reason{{{lab},reason="deferred"}} 0.0',
            f"vllm:kv_cache_usage_perc{{{lab}}} {self.kv}", ""])

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return
        headers = {k.decode().lower(): v.decode() for k, v in scope["headers"]}
        if scope["path"] == "/metrics":
            data = self.metrics_text().encode()
            await send({"type": "http.response.start", "status": 200 if self.metrics_mode == "ok" else 404,
                        "headers": [(b"content-type", b"text/plain")]})
            await send({"type": "http.response.body", "body": data if self.metrics_mode == "ok" else b"not found"})
            return
        if scope["path"] == "/v1/models":
            self.model_hits.append(headers)
            await _send_json(send, 200, {"object": "list", "data": [{"id": self.model, "object": "model", "max_model_len": self.max_len}]})
            return
        body = b""
        while True:
            m = await receive()
            body += m.get("body", b"")
            if not m.get("more_body"):
                break
        self.hits.append({"path": scope["path"], "headers": headers, "size": len(body), "t": time.monotonic()})
        mode = self.mode
        if mode == "json":
            await _send_json(send, 200, {"served_by": self.name})
        elif mode == "500":
            await _send_json(send, 500, {"error": {"message": "boom"}, "served_by": self.name})
        elif mode == "slow":
            await asyncio.sleep(3)
            await _send_json(send, 200, {"served_by": self.name})
        elif mode == "sse":
            await send({"type": "http.response.start", "status": 200, "headers": SSE})
            for i in range(3):
                await send({"type": "http.response.body", "body": f'data: {{"i": {i}}}\n\n'.encode(), "more_body": True})
                await asyncio.sleep(0.4)
            await send({"type": "http.response.body", "body": b"data: [DONE]\n\n"})
        elif mode == "break":
            await send({"type": "http.response.start", "status": 200, "headers": SSE})
            await send({"type": "http.response.body", "body": b'data: {"i": 0}\n\n', "more_body": True})
            return                              # 끝맺지 않고 돌아간다 — 서버가 연결을 닫는다(생성 중 죽은 vLLM)
        elif mode in ("hold", "hold_stream"):
            if mode == "hold_stream":
                await send({"type": "http.response.start", "status": 200, "headers": SSE})
                await send({"type": "http.response.body", "body": b"data: first\n\n", "more_body": True})
            gone = asyncio.create_task(_until_gone(receive))
            while not gone.done() and not self.release.is_set():
                await asyncio.sleep(0.01)
            if gone.done():
                self.gone.append(time.monotonic())
                return
            gone.cancel()
            if mode == "hold":
                await _send_json(send, 200, {"served_by": self.name})
            else:
                await send({"type": "http.response.body", "body": b"data: [DONE]\n\n"})


def _write_env(path: Path, urls: list[str], **knobs) -> None:
    vals = {"LLM_ROUTER_SCRAPE_S": 60, "LLM_ROUTER_COOLDOWN_S": 0.5, "LLM_ROUTER_CONNECT_TIMEOUT_S": 2, **knobs}
    text = f"LLM_UPSTREAMS={','.join(urls)}\n" + "".join(f"{k}={v}\n" for k, v in vals.items())
    old = path.stat().st_mtime_ns if path.exists() else 0
    path.write_text(text, encoding="utf-8")
    t = max(path.stat().st_mtime_ns, old + 1_000_000_000)    # 같은 순간에 두 번 써도 바뀐 것이 보이게
    os.utime(path, ns=(t, t))


class _Lab:
    def __init__(self, tmp: Path):
        self.tmp, self.servers, self.fakes, self.routers = tmp, [], [], []

    def fake(self, name: str, **kw) -> _Fake:
        f = _Fake(name, **kw)
        f.srv = _Srv(f)
        self.servers.append(f.srv)
        self.fakes.append(f)
        return f

    def restart(self, f: _Fake) -> None:
        f.srv = _Srv(f, port=f.srv.port)
        self.servers.append(f.srv)

    def router(self, fakes: list[_Fake], *, http: str = "auto", **knobs) -> "_Router":
        env = self.tmp / f"router{len(self.routers)}.env"
        _write_env(env, [f.base for f in fakes], **knobs)
        s = _Srv(R.make_app(env), http=http, lifespan="on")
        self.servers.append(s)
        self.routers.append(_Router(s, env))
        return self.routers[-1]

    def close(self) -> None:
        for f in self.fakes:
            f.release.set()
        for r in self.routers:
            r.http.close()
        for s in reversed(self.servers):
            s.stop()


class _Router:
    def __init__(self, srv: _Srv, env: Path):
        self.srv, self.env = srv, env
        self.http = httpx.Client(base_url=srv.url, trust_env=False, timeout=15)

    def chat(self, text: str | None = None, *, messages=None, headers=None, **extra) -> httpx.Response:
        body = {"model": "glm", **extra}
        if messages is not None or text is not None:
            body["messages"] = messages or [{"role": "system", "content": "당신은 전문가다"}, {"role": "user", "content": text}]
        return self.http.post("/v1/chat/completions", json=body, headers=headers or {})

    def stats(self) -> list[dict]:
        return self.http.get("/stats").json()

    def by_url(self) -> dict[str, dict]:
        return {s["url"]: s for s in self.stats()}

    def health(self) -> httpx.Response:
        return self.http.get("/health")


@pytest.fixture
def lab(tmp_path):
    lb = _Lab(tmp_path)
    yield lb
    lb.close()


def _wait(cond, timeout: float = 5.0, what: str = "") -> None:
    deadline = time.monotonic() + timeout
    while not cond():
        if time.monotonic() > deadline:
            raise AssertionError(f"{timeout}초 안에 되지 않았다: {what}")
        time.sleep(0.01)


def _bg(fn) -> dict:
    out: dict = {}

    def run():
        try:
            out["r"] = fn()
        except Exception as exc:      # noqa: BLE001 — 시험이 꺼내 본다
            out["e"] = exc
    out["t"] = threading.Thread(target=run, daemon=True)
    out["t"].start()
    return out


# ── 지표 읽기 — 정확한 이름만 ───────────────────────────────────────────────────────────────────────
DEV_SAMPLE = """# HELP vllm:num_requests_running Number of requests in model execution batches.
# TYPE vllm:num_requests_running gauge
vllm:num_requests_running{engine="0",model_name="qwen2.5-7b-dev"} 0.0
# HELP vllm:num_requests_waiting Number of requests waiting to be processed.
# TYPE vllm:num_requests_waiting gauge
vllm:num_requests_waiting{engine="0",model_name="qwen2.5-7b-dev"} 0.0
vllm:num_requests_waiting_by_reason{engine="0",model_name="qwen2.5-7b-dev",reason="capacity"} 0.0
vllm:kv_cache_usage_perc{engine="0",model_name="qwen2.5-7b-dev"} 0.0
"""


def test_지표는_정확한_이름만_세고_by_reason_은_waiting_에_더하지_않는다():
    """dev vLLM 의 실제 글 모양(라벨 묶음 · HELP/TYPE 줄)에서 읽고, 엔진 둘의 라벨 묶음은 더한다. `_by_reason` 은 합이 waiting 과 같아서
    접두로 세면 waiting 이 두 배가 된다 — 그러면 바쁜 서버가 두 배로 바빠 보여 한쪽만 쓴다."""
    assert R.parse_metrics(DEV_SAMPLE) == {"running": 0.0, "waiting": 0.0, "kv": 0.0}
    two = "\n".join([
        'vllm:num_requests_running{engine="0",model_name="m"} 2.0', 'vllm:num_requests_running{engine="1",model_name="m"} 1.0',
        'vllm:num_requests_waiting{engine="0",model_name="m"} 3.0', 'vllm:num_requests_waiting{engine="1",model_name="m"} 4.0',
        'vllm:num_requests_waiting_by_reason{engine="0",model_name="m",reason="capacity"} 3.0',
        'vllm:num_requests_waiting_by_reason{engine="1",model_name="m",reason="capacity"} 4.0',
        'vllm:num_requests_running_total{engine="0"} 100',       # 같은 접두의 다른 이름 — 세지 않는다
        'vllm:kv_cache_usage_perc{engine="0",model_name="m"} 0.3', 'vllm:kv_cache_usage_perc{engine="1",model_name="m"} 0.7',
        'vllm:gpu_cache_usage_perc{engine="0",model_name="m"} 0.99'])     # 새 이름이 있으면 옛 이름은 보지 않는다
    assert R.parse_metrics(two) == {"running": 3.0, "waiting": 7.0, "kv": 0.7}
    old = 'vllm:num_requests_running 1\nvllm:num_requests_waiting 0\nvllm:gpu_cache_usage_perc{a="x}y"} 0.25 1700000000\n'
    assert R.parse_metrics(old) == {"running": 1.0, "waiting": 0.0, "kv": 0.25}, "옛 이름 · 라벨 없는 줄 · 값 안의 } · 시각 붙은 줄"
    nan = 'vllm:num_requests_running{e="0"} NaN\nvllm:num_requests_running{e="1"} 2\nvllm:num_requests_waiting 1\n'
    assert R.parse_metrics(nan) == {"running": 2.0, "waiting": 1.0, "kv": None}, "NaN 표본은 빼고, KV 가 없으면 None"
    assert R.parse_metrics('vllm:num_requests_running 1\nvllm:num_requests_waiting_by_reason{reason="capacity"} 5\n') is None, \
        "waiting 이 없으면(by_reason 만 있어도) 지표 없음 — 이 라우터가 보낸 수로만 잰다"
    assert R.parse_metrics("<html>not found</html>") is None


# ── 설정 읽기 — update-all 의 정본 독자와 같게 ─────────────────────────────────────────────────────
def _envfile_fn() -> str:
    i = UA.index("_envfile_value() {")
    return UA[i:UA.index("\n}\n", i) + 3]


def test_infra_env_를_update_all_정본과_같은_규칙으로_읽는다(tmp_path):
    """일치 시험은 둘 다 틀리면 통과한다 — update-all `_envfile_value`(bash)를 오라클로 댄다(감사 라운드 교훈)."""
    cases = ["X=http://a:1/v1   # 설명", 'X="http://a:1/v1"', "export X=http://a:1/v1", "X=a#b", "X=   # 값 없이 주석만",
             "X=1\nX=", "X=\nX=2", "X=\t# c", "X=1\r", "X=a ", "  export   X='q'  ", "# X=주석"]
    f = tmp_path / "e.env"
    for line in cases:
        f.write_text(line + "\n", encoding="utf-8")
        sh = subprocess.run(["bash", "-c", f'{_envfile_fn()}\nprintf %s "$(_envfile_value "{f}" X)"'], capture_output=True, text=True).stdout
        assert R.read_env(f).get("X", "") == sh, (line, R.read_env(f), sh)
    f.write_text("LLM_UPSTREAMS=http://a:1/v1,http://b:2/v1   # 두 서버\nLLM_API_KEY=\n", encoding="utf-8")
    assert R.read_env(f) == {"LLM_UPSTREAMS": "http://a:1/v1,http://b:2/v1"}, "빈 값은 없는 것이다"


def test_서버_목록은_쉼표_공백으로_나누고_끝_빗금을_떼고_못_쓰는_항목은_뺀다():
    good, bad = R.parse_upstreams(" http://h1:8000/v1/ , http://h2:8000/v1\thttp://h1:8000/v1  https://h3/v1 ftp://x/v1 h4:80/v1 http://u:p@h5/v1 ")
    assert good == ["http://h1:8000/v1", "http://h2:8000/v1", "https://h3/v1"]
    assert bad[:2] == ["ftp://x/v1", "h4:80/v1"] and "u:p" not in bad[2], "사용자 정보가 든 항목은 값을 찍지 않는다"
    assert [R.Upstream(u).origin for u in good] == ["http://h1:8000", "http://h2:8000", "https://h3"]
    assert R.Upstream("http://h:1/llm").origin == "http://h:1/llm", "/v1 로 끝나지 않으면 그대로가 원점이다"
    cfg = R.build_config({"LLM_UPSTREAMS": "http://h:1/v1", "LLM_ROUTER_SCRAPE_S": "abc", "LLM_ROUTER_PREFIX_CHARS": "16000",
                          "LLM_ROUTER_COOLDOWN_S": "-1"})
    assert (cfg.scrape_s, cfg.prefix_chars, cfg.cooldown_s, cfg.sticky_slack, cfg.connect_timeout_s) == (2.0, 16000, 15.0, 4.0, 5.0)
    assert len(cfg.problems) == 2, cfg.problems


# ── 고르기 ─────────────────────────────────────────────────────────────────────────────────────────
def test_가장_한가한_서버로_보내고_지표_사이에_보낸_수를_더한다(lab):
    """지표는 2초마다다. 그 사이에 몰려온 요청을 마지막 지표만 보고 고르면 전부 한 서버로 간다 — 이 라우터가 그 뒤로 보낸 수를 더한다.
    A 는 0, B 는 2 로 시작한다 → A, A, A(2 대 2 — 같으면 목록 앞), 그다음 B(3 대 2)."""
    a, b = lab.fake("A", running=0), lab.fake("B", running=2)
    a.mode = b.mode = "hold"
    r = lab.router([a, b], LLM_ROUTER_PREFIX_CHARS=0)
    order, jobs = [], []
    for _ in range(4):
        before = len(a.hits) + len(b.hits)
        jobs.append(_bg(lambda: r.chat("x")))
        _wait(lambda n=before: len(a.hits) + len(b.hits) > n, what="요청이 위 서버에 닿기")
        order.append("A" if len(a.hits) > order.count("A") else "B")
    assert order == ["A", "A", "A", "B"], order
    st = r.by_url()
    assert (st[a.base]["inflight"], st[b.base]["inflight"]) == (3, 1)
    assert (st[a.base]["running"], st[b.base]["running"]) == (0.0, 2.0), "지표는 시작 때 한 번 읽은 그대로(SCRAPE_S=60)"
    a.release.set()
    b.release.set()
    for j in jobs:
        j["t"].join(10)
        assert j["r"].status_code == 200
    _wait(lambda: r.health().json()["inflight"] == 0, what="도는 수가 0 으로")


def test_부하가_같으면_KV_사용률이_낮은_쪽_그것도_같으면_목록_앞(lab):
    a, b = lab.fake("A", running=1, kv=0.8), lab.fake("B", running=1, kv=0.2)
    r = lab.router([a, b], LLM_ROUTER_PREFIX_CHARS=0, LLM_ROUTER_SCRAPE_S=0.1)
    assert r.chat("x").json()["served_by"] == "B"
    b.kv = 0.9
    _wait(lambda: r.by_url()[b.base]["kv"] == 0.9, what="B 의 KV 가 다시 읽히기")
    assert r.chat("x").json()["served_by"] == "A"
    a.kv = b.kv = 0.5
    _wait(lambda: all(s["kv"] == 0.5 for s in r.stats()), what="두 서버의 KV 가 다시 읽히기")
    assert r.chat("x").json()["served_by"] == "A"


def test_지표가_없는_서버는_이_라우터가_보낸_수로만_잰다(lab):
    """/metrics 가 404 인 서버(지표를 끈 vLLM · 다른 OpenAI 호환 서버)는 내려간 것이 아니다 — 올라온 채 이 라우터가 보낸 수로 잰다."""
    a, b = lab.fake("A", running=3), lab.fake("B", running=50)
    b.metrics_mode = "404"
    b.mode = "hold"
    r = lab.router([a, b], LLM_ROUTER_PREFIX_CHARS=0)
    st = r.by_url()[b.base]
    assert (st["up"], st["running"], st["waiting"], st["kv"]) == (True, None, None, None)
    held = [_bg(lambda: r.chat("x")) for _ in range(3)]
    _wait(lambda: len(b.hits) == 3, what="B 가 셋을 받기(0·1·2 < 3)")
    assert r.chat("x").json()["served_by"] == "A", "보낸 수가 3 이 되면 A(3)와 같고 목록 앞이 이긴다"
    b.release.set()
    for j in held:
        j["t"].join(10)
        assert j["r"].status_code == 200


# ── 붙임 ───────────────────────────────────────────────────────────────────────────────────────────
def test_같은_앞부분은_같은_서버로_가고_다른_앞부분은_흩어진다(lab):
    """같은 전문가의 카드 묶음 · 같은 대화는 같은 서버의 접두 캐시를 다시 쓴다(LP-D2·D8). 열쇠는 메시지 앞부분 PREFIX_CHARS 자의 해시이고
    서버는 렌데부 해시로 정한다 — 라우터의 셈과 같은 서버로 가는지 본다."""
    a, b = lab.fake("A"), lab.fake("B")
    r = lab.router([a, b], LLM_ROUTER_PREFIX_CHARS=40)
    first = r.chat("같은 대화").json()["served_by"]
    assert all(r.chat("같은 대화").json()["served_by"] == first for _ in range(3))
    seen = {r.chat(f"주제 {i}번 — 서로 다른 앞부분").json()["served_by"] for i in range(16)}
    assert seen == {"A", "B"}, "다른 열쇠는 두 서버로 흩어진다"
    long_sys = [{"role": "system", "content": "역할과 카드 묶음 " * 10}]
    one = r.chat(messages=long_sys + [{"role": "user", "content": "셀 1"}]).json()["served_by"]
    two = r.chat(messages=long_sys + [{"role": "user", "content": "셀 2"}]).json()["served_by"]
    assert one == two, "앞 40자(system 부분)가 같으면 뒤가 달라도 같은 서버"
    body = json.dumps({"model": "glm", "messages": long_sys + [{"role": "user", "content": "셀 3"}]}).encode()
    key = R.sticky_key(body, 40)
    want = max((a, b), key=lambda f: R._rank(key, f.base)).name
    assert r.http.post("/v1/chat/completions", content=body, headers={"content-type": "application/json"}).json()["served_by"] == want
    st = r.stats()
    assert sum(s["sticky"] for s in st) == 1 + 3 + 16 + 3 and sum(s["overflow"] for s in st) == 0
    assert R.sticky_key(b'{"model": "glm", "input": "x"}', 40) is None and R.sticky_key(b"not json", 40) is None
    assert R.sticky_key(b'{"prompt": "abc"}', 40) == R.sticky_key(b'{"prompt": "abc", "max_tokens": 9}', 40), "prompt 도 앞부분이 열쇠"


def test_붙인_서버가_문턱만큼_바빠지면_가장_한가한_서버로_넘친다(lab):
    """같은 서식(같은 앞부분)의 요청이 한 서버에 몰리는 것은 STICKY_SLACK 이 푼다 — 붙인 서버의 부하 − 최소 부하 ≥ 문턱이면 떨어진다."""
    a, b = lab.fake("A"), lab.fake("B")
    a.mode = b.mode = "hold"
    r = lab.router([a, b], LLM_ROUTER_STICKY_SLACK=2)
    jobs, got = [], []
    for _ in range(3):
        before = (len(a.hits), len(b.hits))
        jobs.append(_bg(lambda: r.chat("같은 서식")))
        _wait(lambda n=before: (len(a.hits), len(b.hits)) != n, what="요청이 닿기")
        got.append("A" if len(a.hits) > before[0] else "B")
    pref = got[0]
    other = "B" if pref == "A" else "A"
    assert got == [pref, pref, other], got
    st = {("A" if s["url"] == a.base else "B"): s for s in r.stats()}
    assert (st[pref]["sticky"], st[pref]["overflow"], st[other]["sticky"], st[other]["sent"]) == (2, 1, 0, 1), st
    a.release.set()
    b.release.set()
    for j in jobs:
        j["t"].join(10)
        assert j["r"].status_code == 200


# ── 넘김 ───────────────────────────────────────────────────────────────────────────────────────────
def test_연결_실패만_다른_서버로_넘기고_빼_둔_뒤_돌아온다(lab):
    a, b = lab.fake("A", running=0), lab.fake("B", running=5)
    r = lab.router([a, b], LLM_ROUTER_PREFIX_CHARS=0, LLM_ROUTER_COOLDOWN_S=0.8)
    a.srv.stop()                                         # 연결 거절 — 지표 주기(60초)는 아직 모른다
    assert r.chat("x").json()["served_by"] == "B", "요청이 서버에 닿지 않았으니 다른 서버로 다시 보낸다"
    st = r.by_url()
    assert (st[a.base]["up"], st[a.base]["connect_fail"], st[a.base]["retried_away"], st[a.base]["sent"]) == (False, 1, 1, 0)
    assert st[b.base]["sent"] == 1
    assert r.chat("x").json()["served_by"] == "B"
    assert r.by_url()[a.base]["connect_fail"] == 1, "빼 둔 동안은 시도하지 않는다"
    lab.restart(a)
    time.sleep(0.9)                                      # 빼 둔 시간(0.8초)이 지나면 다시 고른다
    assert r.chat("x").json()["served_by"] == "A"
    assert r.by_url()[a.base]["up"] is True
    # 모두 빠졌으면 전부를 다시 시도해 본다(멀쩡해졌을 수 있다)
    a.srv.stop()
    b.srv.stop()
    resp = r.chat("x")
    assert resp.status_code == 502 and resp.json()["error"]["type"] == "llm_router_upstream_unreachable"
    lab.restart(b)
    assert r.chat("x").json()["served_by"] == "B", "둘 다 빼 둔 사이라도 시도해 본다"
    st = r.by_url()
    assert (st[a.base]["connect_fail"], st[a.base]["retried_away"], st[b.base]["connect_fail"]) == (3, 3, 1), st


class _Dropper:
    """연결을 받아 요청 머리를 읽고 응답 없이 닫는다 — 미리 채우기 중에 죽은 vLLM(연결은 됐다 — 요청이 닿았을 수 있다)."""

    def __init__(self):
        self.sock = socket.create_server(("127.0.0.1", 0))
        self.base = f"http://127.0.0.1:{self.sock.getsockname()[1]}/v1"
        self.posts = 0
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        while True:
            try:
                c, _ = self.sock.accept()
            except OSError:
                return
            with c:
                c.settimeout(5)
                data = b""
                while b"\r\n\r\n" not in data and (chunk := c.recv(65536)):
                    data += chunk
                self.posts += data.startswith(b"POST ")


def test_연결된_뒤의_실패는_그대로_넘기고_다시_보내지_않는다(lab):
    """LP-D3 — 닿은 요청을 다른 서버에 다시 보내면 같은 답을 두 번 만들고, 부르는 쪽의 재시도·차감 규칙과 겹친다."""
    a, b = lab.fake("A", running=0), lab.fake("B", running=5)
    r = lab.router([a, b], LLM_ROUTER_PREFIX_CHARS=0)
    a.mode = "500"
    resp = r.chat("x")
    assert resp.status_code == 500 and resp.json()["served_by"] == "A", "HTTP 오류는 상태·본문 그대로"
    a.mode = "break"
    with pytest.raises(httpx.TransportError):
        r.chat("x")                                      # 생성 중 끊김은 손님에게도 끊김으로 보인다(정상 끝처럼 보이면 잘린 답을 믿는다)
    assert (len(a.hits), len(b.hits)) == (2, 0), "위 서버에는 정확히 한 번씩, 다른 서버에는 한 번도"
    st = r.by_url()
    assert (st[a.base]["sent"], st[a.base]["connect_fail"], st[a.base]["up"]) == (2, 0, True)
    _wait(lambda: r.health().json()["inflight"] == 0, what="도는 수가 0 으로")
    # 머리를 받기 전에 끊긴 것도 같다 — 연결은 됐으니 다시 보내지 않고 502 로 말한다
    d = _Dropper()
    try:
        r2 = lab.router([d, b], LLM_ROUTER_PREFIX_CHARS=0)       # d 는 지표가 없어(끊는다) 보낸 수 0 으로 잰다 — b(5)보다 한가하다
        before = len(b.hits)
        resp = r2.chat("x")
        assert resp.status_code == 502 and resp.json()["error"]["type"] == "llm_router_upstream_broken", resp.text
        assert d.posts == 1 and len(b.hits) == before, "끊은 서버에 한 번, 다른 서버에는 다시 보내지 않는다"
    finally:
        d.sock.close()


# ── 흐름 ───────────────────────────────────────────────────────────────────────────────────────────
def test_SSE_는_모으지_않고_오는_대로_흘린다(lab):
    a = lab.fake("A")
    a.mode = "sse"
    r = lab.router([a])
    arrived = []
    with r.http.stream("POST", "/v1/chat/completions", json={"model": "glm", "stream": True, "messages": []}) as resp:
        assert resp.status_code == 200 and resp.headers["content-type"].startswith("text/event-stream")
        for chunk in resp.iter_raw():
            arrived.append((time.monotonic(), chunk))
    joined = b"".join(c for _, c in arrived)
    assert joined.count(b"data: ") == 4 and joined.endswith(b"data: [DONE]\n\n")
    first = next(t for t, c in arrived if b'"i": 0' in c)
    assert arrived[-1][0] - first >= 0.6, "첫 조각이 끝보다 0.8초 앞서 왔어야 한다 — 모아서 한 번에 보내면 같은 순간에 온다"


def _raw_post(port: int, body: bytes) -> socket.socket:
    s = socket.create_connection(("127.0.0.1", port), timeout=5)
    s.sendall(b"POST /v1/chat/completions HTTP/1.1\r\nHost: r\r\nContent-Type: application/json\r\n"
              b"Content-Length: %d\r\n\r\n" % len(body) + body)
    return s


HTTP_IMPLS = ["h11"] + (["httptools"] if importlib.util.find_spec("httptools") else [])


@pytest.mark.parametrize("impl", HTTP_IMPLS)
def test_머리를_받기_전에_손님이_떠나면_1초_안에_위_연결을_닫는다(lab, impl):
    """vLLM 은 연결이 닫혀야 생성을 멈춘다. 라우터가 손님의 떠남을 모르면 버려진 생성이 끝날 때까지 GPU 를 잡는다(1M 창이면 몇 분).
    uvicorn 은 끊긴 뒤의 send 를 조용히 버리므로 '보내다 실패' 로는 못 안다 — ASGI receive 를 지켜본다. 운영 SIF 는 httptools 다."""
    a = lab.fake("A")
    a.mode = "hold"
    r = lab.router([a], http=impl)
    s = _raw_post(r.srv.port, b'{"model": "glm", "messages": [{"role": "user", "content": "x"}]}')
    _wait(lambda: len(a.hits) == 1, what="요청이 위 서버에 닿기")
    t0 = time.monotonic()
    s.close()
    _wait(lambda: a.gone, timeout=3, what="위 서버가 끊김을 보기")
    assert a.gone[0] - t0 < 1.0, f"{a.gone[0] - t0:.2f}초"
    _wait(lambda: r.health().json()["inflight"] == 0, timeout=2, what="라우터의 도는 수가 0 으로")


@pytest.mark.parametrize("impl", HTTP_IMPLS)
def test_흐르는_중에_손님이_떠나도_1초_안에_위_연결을_닫는다(lab, impl):
    a = lab.fake("A")
    a.mode = "hold_stream"
    r = lab.router([a], http=impl)
    s = _raw_post(r.srv.port, b'{"model": "glm", "stream": true, "messages": [{"role": "user", "content": "x"}]}')
    got = b""
    while b"data: first" not in got:
        chunk = s.recv(65536)
        assert chunk, "첫 조각 전에 닫혔다"
        got += chunk
    t0 = time.monotonic()
    s.close()
    _wait(lambda: a.gone, timeout=3, what="위 서버가 끊김을 보기")
    assert a.gone[0] - t0 < 1.0, f"{a.gone[0] - t0:.2f}초"
    _wait(lambda: r.health().json()["inflight"] == 0, timeout=2, what="라우터의 도는 수가 0 으로")


def test_읽기_한도가_없다_3초_조용한_위_서버도_기다리는_손님에게_간다(lab):
    """한도는 부르는 쪽의 것이다(시간 한도 사슬에 층을 끼우지 않는다) — 1M 창의 미리 채우기는 몇 분 조용할 수 있다."""
    a = lab.fake("A")
    a.mode = "slow"
    r = lab.router([a])
    t0 = time.monotonic()
    resp = r.chat("x")
    assert resp.status_code == 200 and resp.json()["served_by"] == "A" and time.monotonic() - t0 >= 2.9


def test_1MB_넘는_본문도_그대로_넘기고_같은_앞부분이면_같은_서버다(lab):
    """1M 창 요청은 수 MB 다 — JSON 해석은 루프 밖에서 하고, 본문은 바이트 하나 안 바뀐 채 간다."""
    a, b = lab.fake("A"), lab.fake("B")
    r = lab.router([a, b])
    system = [{"role": "system", "content": "카드 묶음 " * 2000}]
    big = json.dumps({"model": "glm", "messages": system + [{"role": "user", "content": "가" * 600_000}]}).encode()
    assert len(big) > R.BIG_BODY
    resp = r.http.post("/v1/chat/completions", content=big, headers={"content-type": "application/json"})
    small = r.chat(messages=system + [{"role": "user", "content": "짧다"}]).json()["served_by"]
    assert resp.json()["served_by"] == small, "앞부분(8000자)이 같으면 본문 크기와 상관없이 같은 서버"
    assert next(f for f in (a, b) if f.name == small).hits[0]["size"] == len(big)


# ── 키 ─────────────────────────────────────────────────────────────────────────────────────────────
def test_손님_키를_그대로_넘기고_라우터_키는_끼워_넣지_않는다(lab, caplog):
    """LP-D9 — 라우터가 LLM_API_KEY 를 끼우면 이 박스(여러 계정)의 누구든 루프백으로 키 없이 GLM 을 쓴다. 키는 자기 /v1/models 대조에만."""
    caplog.set_level(logging.INFO)
    a = lab.fake("A")
    r = lab.router([a], LLM_API_KEY="router-secret-key-123")
    assert a.model_hits[0].get("authorization") == "Bearer router-secret-key-123", "라우터 자신의 모델 대조는 키로"
    r.chat("x", headers={"Authorization": "Bearer client-key"})
    assert a.hits[-1]["headers"]["authorization"] == "Bearer client-key"
    r.chat("x")
    assert "authorization" not in a.hits[-1]["headers"], "키 없는 손님은 키 없이 간다"
    n = len(a.model_hits)
    assert r.http.get("/v1/models").status_code == 200
    assert "authorization" not in a.model_hits[n], "손님이 부른 /v1/models 에도 끼우지 않는다"
    assert "router-secret-key-123" not in caplog.text, "키는 어디에도 찍지 않는다"


# ── /health · 모델 대조 · 다시 읽기 ───────────────────────────────────────────────────────────────────
def test_health_는_올라온_서버_수로_ok_degraded_down_이고_down_이면_503(lab):
    a, b = lab.fake("A"), lab.fake("B")
    r = lab.router([a, b], LLM_ROUTER_SCRAPE_S=0.1, LLM_ROUTER_COOLDOWN_S=0.3)
    h = r.health()
    body = h.json()
    assert h.status_code == 200 and body["status"] == "ok" and (body["upstreams_total"], body["upstreams_up"], body["inflight"]) == (2, 2, 0)
    assert body["models"] == {"match": True, "ids": ["glm"], "max_model_len": 1_048_576}
    assert body["config_mtime"] == pytest.approx(r.env.stat().st_mtime, abs=0.01)
    assert set(r.stats()[0]) == {"url", "up", "running", "waiting", "kv", "scrape_age_s", "inflight", "sent", "connect_fail",
                                 "retried_away", "sticky", "overflow"}
    b.srv.stop()
    _wait(lambda: r.health().json()["status"] == "degraded", what="degraded")
    assert r.health().status_code == 200 and r.health().json()["upstreams_up"] == 1
    a.srv.stop()
    _wait(lambda: r.health().json()["status"] == "down", what="down")
    assert r.health().status_code == 503 and r.by_url()[a.base]["connect_fail"] == 0, "지표 연결 실패는 요청 실패 수에 넣지 않는다"


def test_모델이_다르면_match_false_와_경고는_바뀔_때만(lab, caplog, monkeypatch):
    """LP-D6 — 두 서버는 같은 모델·같은 창이어야 한다. 한쪽만 다시 띄우다 인자가 갈리는 날을 코드가 다시 확인한다."""
    caplog.set_level(logging.INFO)
    monkeypatch.setattr(R, "MODELS_EVERY_S", 0.1)
    a, b = lab.fake("A"), lab.fake("B", max_len=16_384)
    r = lab.router([a, b], LLM_ROUTER_SCRAPE_S=0.1)
    body = r.health().json()
    assert body["status"] == "degraded" and body["models"]["match"] is False
    assert body["models"]["max_model_len"] == {a.base: {"glm": 1_048_576}, b.base: {"glm": 16_384}}
    _wait(lambda: len(a.model_hits) >= 5, what="대조가 여러 번 돌기")
    warns = lambda: [x for x in caplog.records if "모델 어긋남" in x.getMessage()]   # noqa: E731
    assert len(warns()) == 1, "같은 어긋남은 한 번만 알린다"
    _write_env(r.env, [a.base], LLM_ROUTER_SCRAPE_S=0.1)
    _wait(lambda: r.health().json()["models"]["match"] is True, what="B 를 뺀 뒤 같아짐")
    assert r.health().json()["status"] == "ok" and any("모델 같아짐" in x.getMessage() for x in caplog.records)
    _write_env(r.env, [a.base, b.base], LLM_ROUTER_SCRAPE_S=0.1)
    _wait(lambda: len(warns()) == 2, what="다시 어긋나면 다시 알린다")


def test_설정을_다시_읽어_재기동_없이_서버를_더하고_뺀다(lab):
    a, b = lab.fake("A", running=5), lab.fake("B", running=0)
    r = lab.router([a], LLM_ROUTER_PREFIX_CHARS=0, LLM_ROUTER_SCRAPE_S=0.1)
    assert r.chat("x").json()["served_by"] == "A" and len(r.stats()) == 1
    mtime0 = r.health().json()["config_mtime"]
    _write_env(r.env, [a.base, b.base], LLM_ROUTER_PREFIX_CHARS=0, LLM_ROUTER_SCRAPE_S=0.1)
    _wait(lambda: len(r.stats()) == 2 and r.by_url()[b.base]["running"] == 0.0, what="B 가 더해지고 지표가 읽히기")
    assert r.chat("x").json()["served_by"] == "B", "더해진 서버가 더 한가하면 그쪽으로"
    assert r.health().json()["config_mtime"] != mtime0
    _write_env(r.env, [b.base], LLM_ROUTER_PREFIX_CHARS=0, LLM_ROUTER_SCRAPE_S=0.1)
    _wait(lambda: [s["url"] for s in r.stats()] == [b.base], what="A 가 빠지기")
    hits_a = len(a.hits)
    a.running = -100                                          # 빠진 서버는 아무리 한가해 보여도 고르지 않는다
    assert all(r.chat("x").json()["served_by"] == "B" for _ in range(3)) and len(a.hits) == hits_a
    _write_env(r.env, [], LLM_ROUTER_SCRAPE_S=0.1)
    _wait(lambda: r.stats() == [], what="목록이 비기")
    resp = r.chat("x")
    assert resp.status_code == 503 and resp.json()["error"]["type"] == "llm_router_no_upstreams"
    assert r.health().status_code == 503


# ── 띄우는 스크립트 ──────────────────────────────────────────────────────────────────────────────────
def _lay(tmp_path: Path, env_text: str) -> tuple[Path, Path, Path]:
    lay = (tmp_path / "repo").resolve()
    (lay / "infra/scripts").mkdir(parents=True)
    (lay / "infra/apptainer").mkdir()
    shutil.copy(LAUNCHER, lay / "infra/scripts/llm-router.sh")
    (lay / "infra/.env").write_text(env_text, encoding="utf-8")
    (lay / "infra/apptainer/portal.sif").write_text("")
    stub = tmp_path / "apptainer"
    stub.write_text('#!/usr/bin/env bash\nprintf "%s\\n" "$@" > "$STUB_OUT"\n', encoding="utf-8")
    stub.chmod(0o755)
    return lay, stub, tmp_path / "argv.txt"


def _launch(lay: Path, stub: Path, out: Path, *args: str) -> subprocess.CompletedProcess:
    env = {"PATH": os.environ["PATH"], "HOME": os.environ.get("HOME", "/tmp"), "APPTAINER": str(stub), "STUB_OUT": str(out)}
    return subprocess.run(["bash", str(lay / "infra/scripts/llm-router.sh"), *args], capture_output=True, text=True, env=env, timeout=60)


def test_run_은_서버_목록이_없거나_포트가_수가_아니면_띄우지_않는다(tmp_path):
    for i, (env_text, word) in enumerate((("LLM_UPSTREAMS=   # 나중에 적는다\n", "LLM_UPSTREAMS"),
                           ("LLM_UPSTREAMS=http://203.0.113.5:8000/v1\nLLM_ROUTER_PORT=91x0\n", "LLM_ROUTER_PORT"),
                           ("LLM_UPSTREAMS=http://203.0.113.5:8000/v1\nLLM_ROUTER_PORT=70000\n", "LLM_ROUTER_PORT"))):
        sub = tmp_path / f"case{i}"
        sub.mkdir()
        lay, stub, out = _lay(sub, env_text)
        r = _launch(lay, stub, out, "run")
        assert r.returncode != 0 and word in r.stderr, (env_text, r.returncode, r.stderr)
        assert not out.exists(), "apptainer 를 부르지 않는다"


def test_run_은_리포를_바인드하고_루프백에만_듣고_키를_argv_로_넘기지_않는다(tmp_path):
    lay, stub, out = _lay(tmp_path, "LLM_UPSTREAMS=http://203.0.113.5:8000/v1\nLLM_ROUTER_PORT=9131\nLLM_API_KEY=sk-not-in-argv\n")
    r = _launch(lay, stub, out, "run")
    assert r.returncode == 0, r.stderr
    argv = out.read_text().splitlines()
    assert argv[:4] == ["exec", "--cleanenv", "--bind", f"{lay}:/workspace"], argv
    assert argv[argv.index(f"{lay}/infra/apptainer/portal.sif") + 1:] == [
        "python3", "-m", "uvicorn", "--app-dir", "/workspace/infra/llm-router", "llm_router:app",
        "--host", "127.0.0.1", "--port", "9131", "--no-access-log"]
    assert "PYTHONDONTWRITEBYTECODE=1" in argv and not any("sk-not-in-argv" in x for x in argv)
    (lay / "infra/.env").write_text("export LLM_UPSTREAMS='http://203.0.113.5:8000/v1'\n", encoding="utf-8")
    assert _launch(lay, stub, out, "run").returncode == 0 and "9130" in out.read_text().splitlines(), "기본 포트 9130"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _listener(port: int, *tag: str) -> subprocess.Popen:
    code = ("import socket,sys,time; s=socket.socket(); s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1); "
            "s.bind(('127.0.0.1',int(sys.argv[1]))); s.listen(); time.sleep(120)")
    p = subprocess.Popen([sys.executable, "-c", code, str(port), *tag], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    deadline = time.monotonic() + 10
    while True:
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            return p
        except OSError:
            if time.monotonic() > deadline:
                p.kill()
                raise
            time.sleep(0.05)


def test_stop_은_그_포트를_듣는_라우터만_내린다(tmp_path):
    port = _free_port()
    lay, stub, out = _lay(tmp_path, f"LLM_UPSTREAMS=http://203.0.113.5:8000/v1\nLLM_ROUTER_PORT={port}\n")
    r = _launch(lay, stub, out, "stop")
    assert r.returncode == 0 and "이미 내려가 있다" in r.stdout, r.stdout + r.stderr
    other = _listener(port)
    try:
        r = _launch(lay, stub, out, "stop")
        assert r.returncode == 1 and "LLM 라우터가 아니다" in r.stderr and other.poll() is None, "남의 리스너는 건드리지 않는다"
    finally:
        other.kill()
        other.wait(10)
    mine = _listener(port, "llm_router:app")
    try:
        r = _launch(lay, stub, out, "stop")
        assert r.returncode == 0 and "내려갔다" in r.stdout, r.stdout + r.stderr
        assert mine.wait(10) is not None
    finally:
        if mine.poll() is None:
            mine.kill()


# ── 매니페스트 항목 ──────────────────────────────────────────────────────────────────────────────────
def test_매니페스트_항목은_LLM_UPSTREAMS_있는_박스에서만_라우터_파일로_지문을_잡는다(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("svc_for_router", ROOT / "infra/scripts/services.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    entry = {s["name"]: s for s in yaml.safe_load((ROOT / "infra/services.yaml").read_text(encoding="utf-8"))["services"]}["llm-router"]
    assert {k: entry[k] for k in ("dir", "if_env", "update", "fp_git", "fp", "start", "stop", "health", "tier")} == {
        "dir": ".", "if_env": "LLM_UPSTREAMS", "update": False, "fp_git": False, "fp": ["infra/llm-router", "infra/scripts/llm-router.sh"],
        "start": "./infra/scripts/llm-router.sh run", "stop": "./infra/scripts/llm-router.sh stop",
        "health": "http://127.0.0.1:${LLM_ROUTER_PORT:-9130}/health", "tier": 5}
    (tmp_path / "infra").mkdir()
    monkeypatch.setattr(m, "PORTAL_ROOT", tmp_path)
    monkeypatch.delenv("LLM_UPSTREAMS", raising=False)
    (tmp_path / "infra/.env").write_text("LLM_ROUTER_PORT=9555\n", encoding="utf-8")
    assert m.enabled_here(entry) is False and "if_env=LLM_UPSTREAMS" in m.skip_reason(entry)
    assert m.health_url(entry) == "http://127.0.0.1:9555/health", "포트는 infra/.env 를 따른다(기동 대기·상태가 같은 주소를 본다)"
    (tmp_path / "infra/.env").write_text("LLM_UPSTREAMS=http://203.0.113.5:8000/v1\n", encoding="utf-8")
    assert m.enabled_here(entry) is True and m.health_url(entry) == "http://127.0.0.1:9130/health"


def test_services_cli_enables_llm_router_only_with_upstreams_in_the_file(tmp_path):
    """systemd 유닛과 같은 환경(env -i, infra/.env 파일만)에서 실제 매니페스트의 llm-router 항목을 묻는다."""
    lay = tmp_path / "HWAXPortal"
    (lay / "infra/scripts").mkdir(parents=True)
    shutil.copy(ROOT / "infra/scripts/services.py", lay / "infra/scripts/services.py")
    shutil.copy(ROOT / "infra/services.yaml", lay / "infra/services.yaml")

    def run(env_text, *args):
        (lay / "infra/.env").write_text(env_text)
        return subprocess.run(["env", "-i", f"PATH={os.environ['PATH']}", sys.executable, str(lay / "infra/scripts/services.py"), *args],
                              capture_output=True, text=True, timeout=60)
    assert run("HWAX_BOX=x\n", "enabled", "llm-router").returncode == 1
    r = run("HWAX_BOX=x\n", "status", "llm-router")
    assert "if_env=LLM_UPSTREAMS" in r.stdout and "only_on=None" not in r.stdout, r.stdout + r.stderr
    assert run("LLM_UPSTREAMS=http://203.0.113.5:8000/v1,http://203.0.113.6:8000/v1   # 둘\n", "enabled", "llm-router").returncode == 0
