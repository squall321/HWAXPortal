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
import re
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

    def __init__(self, app, *, port: int = 0, http: str = "auto", lifespan: str = "off", tls: tuple[Path, Path] | None = None):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", port))
        self.port = self.sock.getsockname()[1]
        self.lifespan = lifespan
        cfg = uvicorn.Config(app, log_config=None, log_level="warning", lifespan=lifespan, http=http, timeout_graceful_shutdown=1,
                             **({"ssl_certfile": str(tls[0]), "ssl_keyfile": str(tls[1])} if tls else {}))
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
    """가짜 vLLM. mode — json · sse · 500 · break(머리와 한 조각 뒤 끊음) · hold(머리 전에 붙든다) · hold_stream(한 조각 뒤 붙든다) · slow(3초 침묵) ·
    404model(모델이 없다는 404 를 곧바로 — 다른 --served-model-name 으로 다시 뜬 vLLM).
    metrics_mode — ok · 404 · 500 · hang(5초 침묵 — 라우터 탐침의 읽기 한도를 넘긴다) · garbage(200 인데 vLLM 지표가 아니다).
    models_mode — ok · 401 · 404 · hang · garbage(200 인데 모델 목록이 아니다)."""

    def __init__(self, name: str, *, running=0.0, waiting=0.0, kv=0.0, model="glm", max_len=1_048_576):
        self.name, self.running, self.waiting, self.kv = name, running, waiting, kv
        self.model, self.max_len = model, max_len
        self.mode = "json"
        self.metrics_mode = "ok"
        self.models_mode = "ok"
        self.metrics_hits = 0
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
            self.metrics_hits += 1
            mm = self.metrics_mode
            if mm == "hang":
                await asyncio.sleep(5)
            status = {"404": 404, "500": 500}.get(mm, 200)
            data = b"<html>not metrics</html>" if mm == "garbage" else self.metrics_text().encode() if status == 200 else b"no"
            await send({"type": "http.response.start", "status": status, "headers": [(b"content-type", b"text/plain")]})
            await send({"type": "http.response.body", "body": data})
            return
        if scope["path"] == "/v1/models":
            self.model_hits.append(headers)
            mm = self.models_mode
            if mm == "hang":
                await asyncio.sleep(5)
            if mm in ("401", "404"):
                await _send_json(send, int(mm), {"error": {"message": "no"}})
            elif mm == "garbage":
                await _send_json(send, 200, {"detail": "not a list"})
            else:
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
        if mode == "404model":
            await _send_json(send, 404, {"error": {"message": "The model does not exist."}, "served_by": self.name})
        elif mode == "json":
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

    def router(self, fakes: list, *, http: str = "auto", **knobs) -> "_Router":
        env = self.tmp / f"router{len(self.routers)}.env"
        _write_env(env, [f if isinstance(f, str) else f.base for f in fakes], **knobs)     # 글자는 주소 그대로(틀린 칸 시험)
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
        self.app = srv.server.config.app                     # Router 객체 — 뜻밖의 예외를 끼워 넣는 시험이 쓴다
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
             "X=1\nX=", "X=\nX=2", "X=\t# c", "X=1\r", "X=a ", "  export   X='q'  ", "# X=주석",
             # sed 의 [[:space:]] 는 ASCII 여섯이다 — CRLF 줄 끝 앞의 공백 · 수직탭 · 폼피드도 공백이다(LLM_UPSTREAMS 모양 검사가 이 값으로 갈린다)
             "X=http://a:1/v1 \r", "X=\x0bq", "X=q\x0c# c", "\x0bexport X=q"]
    f = tmp_path / "e.env"
    for line in cases:
        f.write_text(line + "\n", encoding="utf-8")
        sh = subprocess.run(["bash", "-c", f'{_envfile_fn()}\nprintf %s "$(_envfile_value "{f}" X)"'], capture_output=True, text=True).stdout
        assert R.read_env(f).get("X", "") == sh, (line, R.read_env(f), sh)
    f.write_text("LLM_UPSTREAMS=http://a:1/v1,http://b:2/v1   # 두 서버\nLLM_API_KEY=\n", encoding="utf-8")
    assert R.read_env(f) == {"LLM_UPSTREAMS": "http://a:1/v1,http://b:2/v1"}, "빈 값은 없는 것이다"


def test_서버_목록은_정본_규칙으로_읽고_틀린_칸이_하나라도_있으면_줄_전체를_받지_않는다(monkeypatch):
    """규칙 표 전체의 bash 대조는 test_llm_pool_upstreams_rules 가 한다 — 여기는 라우터 쪽 모양(따옴표 안 공백 · 끝 빗금 · 탐침 주소)만."""
    monkeypatch.delenv("LLM_ROUTER_PORT", raising=False)
    good, bad = R.parse_upstreams('"http://h1:8000/v1/ , http://h2:8000/v1\thttps://h3/v1"')
    assert (good, bad) == (["http://h1:8000/v1", "http://h2:8000/v1", "https://h3/v1"], [])
    good, bad = R.parse_upstreams("http://h1:8000/v1,ftp://x/v1,http://u:p@h5/v1?k=SECRET")
    assert good == [] and len(bad) == 2, "반만 맞는 목록으로 보내지 않는다"
    assert "ftp://x" in bad[0] and "http://h5" in bad[1] and not any("u:p" in b or "SECRET" in b for b in bad), \
        "틀린 칸은 스킴과 호스트만 — 계정·질의에 키가 들 수 있다"
    assert R.parse_upstreams("") == ([], []) and R.parse_upstreams('""') == ([], []), "빈 값은 꺼짐이다(틀림이 아니다)"
    ups = [R.Upstream(u) for u in ("http://h1:8000/v1", "https://h3/v1")]
    assert [(str(u.metrics_url), str(u.models_url)) for u in ups] == [
        ("http://h1:8000/metrics", "http://h1:8000/v1/models"), ("https://h3/metrics", "https://h3/v1/models")]
    cfg = R.build_config({"LLM_UPSTREAMS": "http://h:1/v1", "LLM_ROUTER_SCRAPE_S": "abc", "LLM_ROUTER_PREFIX_CHARS": "16000",
                          "LLM_ROUTER_COOLDOWN_S": "-1"})
    assert (cfg.scrape_s, cfg.prefix_chars, cfg.cooldown_s, cfg.sticky_slack, cfg.connect_timeout_s) == (2.0, 16000, 15.0, 2.0, 5.0)
    assert len(cfg.problems) == 2 and not cfg.upstreams_invalid, cfg.problems
    cfg = R.build_config({"LLM_UPSTREAMS": "http://h:1/v1,http://203.0.113.256:8000/v1"})
    assert cfg.upstreams == () and cfg.upstreams_invalid and "http://203.0.113.256" in cfg.problems[0]
    raw = {"LLM_UPSTREAMS": '"http://h:1/v1", "http://g:1/v1"'}                       # 포털 start.sh 의 소싱을 죽이는 줄(검토 배선 M1)
    assert R.build_config({"LLM_UPSTREAMS": "http://h:1/v1, http://g:1/v1"}, raw).upstreams == (), "모양은 따옴표를 남긴 원문으로 본다"


def test_라우터_자신을_가리키는_칸은_띄우는_스크립트가_넘긴_포트로_거른다(monkeypatch):
    monkeypatch.delenv("LLM_ROUTER_PORT", raising=False)
    assert R.router_port({}) == 9130 and R.router_port({"LLM_ROUTER_PORT": "09555"}) == 9555 and R.router_port({"LLM_ROUTER_PORT": "x"}) is None
    assert R.build_config({"LLM_UPSTREAMS": "http://127.0.0.1:9130/v1"}).upstreams == ()
    assert R.build_config({"LLM_UPSTREAMS": "http://localhost:9555/v1", "LLM_ROUTER_PORT": "9555"}).upstreams == ()
    monkeypatch.setenv("LLM_ROUTER_PORT", "9777")               # llm-router.sh run 이 --env 로 넘기는 실제 포트가 파일보다 먼저다
    assert R.build_config({"LLM_UPSTREAMS": "http://0.0.0.0:9777/v1", "LLM_ROUTER_PORT": "9555"}).upstreams == ()
    assert R.build_config({"LLM_UPSTREAMS": "http://127.0.0.1:9555/v1", "LLM_ROUTER_PORT": "9555"}).upstreams == ("http://127.0.0.1:9555/v1",)


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
    """연결을 받아 요청 머리를 읽고 응답 없이 닫는다 — 미리 채우기 중에 죽은 vLLM(연결은 됐다 — 요청이 닿았을 수 있다).
    /v1/models 에는 모델 목록으로 답한다 — 그래야 '올라온' 서버로 쳐져 고르는 후보가 된다(지표는 끊겨 이 라우터가 보낸 수 0 으로 잰다)."""

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
                if data.startswith(b"GET /v1/models "):
                    body = json.dumps({"data": [{"id": "glm", "max_model_len": 1_048_576}]}).encode()
                    c.sendall(b"HTTP/1.1 200 OK\r\ncontent-type: application/json\r\nconnection: close\r\n"
                              b"content-length: %d\r\n\r\n" % len(body) + body)
                    continue
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
    assert body["upstreams_reachable"] == 2
    assert body["models"] == {"match": True, "ids": ["glm"], "max_model_len": 1_048_576, "errors": {}}
    assert body["config_mtime"] == pytest.approx(r.env.stat().st_mtime, abs=0.01)
    assert set(r.stats()[0]) == {"url", "up", "reachable", "models", "models_error", "running", "waiting", "kv", "metrics_age_s",
                                 "metrics_fail", "scrape_age_s", "inflight", "sent", "connect_fail", "retried_away", "sticky", "overflow"}
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


def test_다시_읽은_목록이_비면_update_all_이_내릴_때까지_마지막_목록으로_보낸다(lab, caplog):
    """풀을 끄는 것은 update-all 이다 — LLM_UPSTREAMS 를 지우면 사본을 직접 주소로 되돌리고 그 뒤에야 라우터를 내리는데, 재기동이 미뤄진
    손님(심의가 도는 에이전트 서버 · 바쁜 HEAX)은 그동안 라우터를 계속 부른다. 빈 목록을 그대로 받아 503 을 내면 그 호출이 전부 깨진다.
    처음 읽을 때 비었으면 이어받을 목록이 없으니 503 이다."""
    caplog.set_level(logging.INFO)
    a, b = lab.fake("A"), lab.fake("B")
    r = lab.router([a], LLM_ROUTER_PREFIX_CHARS=0, LLM_ROUTER_SCRAPE_S=0.1)
    assert r.health().json()["kept_last_list"] is False
    kept = lambda: [x for x in caplog.records if "마지막 목록" in x.getMessage()]   # noqa: E731
    _write_env(r.env, [], LLM_ROUTER_PREFIX_CHARS=0, LLM_ROUTER_SCRAPE_S=0.1)          # 줄은 남고 값이 빈 꼴
    _wait(lambda: r.health().json()["kept_last_list"] is True, what="빈 목록을 읽기")
    body = r.health().json()
    assert (body["status"], body["upstreams_total"], [s["url"] for s in r.stats()]) == ("ok", 1, [a.base]), "status 는 보내는 능력만 말한다"
    assert r.chat("x").json()["served_by"] == "A", "마지막 목록으로 계속 보낸다"
    assert len(kept()) == 1
    _write_env(r.env, ["ftp://nope/v1"], LLM_ROUTER_PREFIX_CHARS=0, LLM_ROUTER_SCRAPE_S=0.1)   # 쓸 수 있는 항목이 없는 목록도 같다
    _wait(lambda: len(kept()) == 2, what="파일 모양이 바뀌면 다시 한 줄")
    time.sleep(0.4)
    assert len(kept()) == 2, "같은 파일 모양에는 한 번만 알린다"
    assert r.chat("x").json()["served_by"] == "A" and r.health().json()["kept_last_list"] is True
    _write_env(r.env, [b.base], LLM_ROUTER_PREFIX_CHARS=0, LLM_ROUTER_SCRAPE_S=0.1)
    _wait(lambda: [s["url"] for s in r.stats()] == [b.base], what="다시 채운 목록으로 바뀌기")
    assert r.health().json()["kept_last_list"] is False
    assert r.chat("x").json()["served_by"] == "B", "다시 채우면 새 목록이다"
    # 처음 읽을 때 비었으면 503
    empty = lab.router([], LLM_ROUTER_SCRAPE_S=0.1)
    resp = empty.chat("x")
    assert resp.status_code == 503 and resp.json()["error"]["type"] == "llm_router_no_upstreams"
    h = empty.health()
    assert h.status_code == 503 and h.json()["status"] == "down" and h.json()["kept_last_list"] is False


# ── 띄우는 스크립트 ──────────────────────────────────────────────────────────────────────────────────
def _lay(tmp_path: Path, env_text: str) -> tuple[Path, Path, Path]:
    lay = (tmp_path / "repo").resolve()
    (lay / "infra/scripts/lib").mkdir(parents=True)
    (lay / "infra/apptainer").mkdir()
    shutil.copy(LAUNCHER, lay / "infra/scripts/llm-router.sh")
    shutil.copy(ROOT / "infra/scripts/lib/llm-pool.sh", lay / "infra/scripts/lib/llm-pool.sh")    # run 이 목록을 정본 규칙으로 본다
    (lay / "infra/.env").write_text(env_text, encoding="utf-8")
    (lay / "infra/apptainer/portal.sif").write_text("")
    stub = tmp_path / "apptainer"
    stub.write_text('#!/usr/bin/env bash\nprintf "%s\\n" "$@" > "$STUB_OUT"\n', encoding="utf-8")
    stub.chmod(0o755)
    return lay, stub, tmp_path / "argv.txt"


def _launch(lay: Path, stub: Path, out: Path, *args: str, env: dict | None = None, path: str | None = None) -> subprocess.CompletedProcess:
    e = {"PATH": path or os.environ["PATH"], "HOME": os.environ.get("HOME", "/tmp"), "APPTAINER": str(stub), "STUB_OUT": str(out),
         **(env or {})}
    return subprocess.run(["bash", str(lay / "infra/scripts/llm-router.sh"), *args], capture_output=True, text=True, env=e, timeout=60)


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
        "dir": ".", "if_env": "LLM_UPSTREAMS", "update": False, "fp_git": False,
        "fp": ["infra/llm-router", "infra/scripts/llm-router.sh", "infra/apptainer/portal.sif"],   # 라우터가 도는 이미지 — §2 가 갈아 끼운다
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
    # 지문 — 라우터가 도는 이미지(portal.sif)는 들고 포털 루트 .env(env-sync 가 덧붙인다)는 들지 않는다(검토 배선 M2 · 라우터 L2)
    (tmp_path / "infra/apptainer").mkdir()
    sif = tmp_path / "infra/apptainer/portal.sif"
    sif.write_bytes(b"old image")
    f1 = m.service_fp(entry)
    (tmp_path / ".env").write_text("NEW_KEY=1\n", encoding="utf-8")
    assert m.service_fp(entry) == f1, "포털 루트 .env 는 라우터 지문이 아니다"
    sif.write_bytes(b"new image!")
    assert m.service_fp(entry) != f1, "§2 가 portal.sif 를 갈아 끼우면 라우터도 다시 띄운다(그 이미지로 돈다)"


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


# ── 반대 검토 1라운드(LP-D13) — 검토자의 탐침을 회귀 시험으로 ─────────────────────────────────────────────
def _until(fn, cond, timeout: float = 5.0, what: str = ""):
    """fn() 을 cond 가 맞을 때까지 다시 부르고 그 값을 돌려준다 — 한 번 읽은 값으로 둘 이상을 함께 단언하려고."""
    deadline = time.monotonic() + timeout
    while True:
        v = fn()
        if cond(v):
            return v
        if time.monotonic() > deadline:
            raise AssertionError(f"{timeout}초 안에 되지 않았다: {what} — 마지막 값 {v!r}")
        time.sleep(0.01)


def _raw_request(port: int, head: bytes, *, limit: float = 5.0) -> bytes:
    """손으로 쓴 요청 하나(Connection: close) — 시험 클라이언트가 붙이는 머리 없이 보낸다."""
    s = socket.create_connection(("127.0.0.1", port), timeout=limit)
    try:
        s.sendall(head)
        got = b""
        while chunk := s.recv(65536):
            got += chunk
        return got
    finally:
        s.close()


def test_검토H1_오타_한_칸이면_다시_읽은_줄을_통째로_받지_않고_마지막_목록으로_보낸다(lab, caplog):
    """옥텟 256 같은 오타가 검사를 지나 httpx 가 요청마다 InvalidURL 을 냈다 — 10/10 이 500, /health 는 ok, 지표 주기마다 traceback.
    이제 그 줄은 틀렸고(정본 규칙 — 옥텟 0~255), 떠 있는 라우터는 마지막 목록으로 계속 보낸다(kept_last_list)."""
    caplog.set_level(logging.INFO)
    a = lab.fake("A", running=3)
    r = lab.router([a], LLM_ROUTER_PREFIX_CHARS=0, LLM_ROUTER_SCRAPE_S=0.1)
    assert r.chat("x").json()["served_by"] == "A"
    _write_env(r.env, [a.base, "http://127.0.0.256:8000/v1"], LLM_ROUTER_PREFIX_CHARS=0, LLM_ROUTER_SCRAPE_S=0.1)
    _wait(lambda: r.health().json()["kept_last_list"] is True, what="틀린 줄을 읽기")
    assert [r.chat("x").status_code for _ in range(10)] == [200] * 10 and [s["url"] for s in r.stats()] == [a.base]
    time.sleep(0.5)
    msgs = [x.getMessage() for x in caplog.records]
    assert sum("http://127.0.0.256" in m and "IPv4" in m for m in msgs) == 1, "틀린 칸은 파일 내용마다 한 번 — 스킴과 호스트로"
    assert sum("틀렸다" in m and "마지막 목록" in m for m in msgs) == 1
    assert not any(x.exc_info for x in caplog.records), "traceback 이 없다"


def test_검토H1_기동_때_틀린_줄이면_뜨기는_하고_503_으로_까닭을_말한다(lab):
    """오타 한 칸에 'Application startup failed' 로 멀쩡한 서버까지 못 쓰던 것(검토 H1b) — 줄 전체를 받지 않지만 라우터는 뜬다. 처음 읽은
    줄이 틀렸으면 이어받을 목록이 없으니 503 이다(띄우는 스크립트는 같은 규칙으로 아예 띄우지 않는다)."""
    a = lab.fake("A")
    r = lab.router([a, "http://203.0.113.256:8000/v1"])
    h = r.health()
    assert h.status_code == 503 and (h.json()["status"], h.json()["upstreams_total"]) == ("down", 0)
    resp = r.chat("x")
    assert resp.status_code == 503 and "틀렸다" in resp.json()["error"]["message"] and not a.hits


class _Boom:
    """httpx 클라이언트를 감싸 한 서버(포트)로 가는 호출에서 httpx 가 아닌 예외를 낸다 — 검사를 빠져나간 주소 · httpx 의 버그를 흉내 낸다."""

    def __init__(self, inner, port: int):
        self.inner, self.mark, self.calls = inner, f":{port}/", 0

    def _hit(self, url) -> bool:
        if self.mark in str(url):
            self.calls += 1
            return True
        return False

    async def get(self, url, **kw):
        if self._hit(url):
            raise RuntimeError("뜻밖")
        return await self.inner.get(url, **kw)

    async def send(self, req, **kw):
        if self._hit(req.url):
            raise RuntimeError("뜻밖")
        return await self.inner.send(req, **kw)

    async def aclose(self):
        await self.inner.aclose()


def test_검토H1_서버_하나의_뜻밖의_예외는_그_서버만_빼고_한_번만_알린다(lab, caplog):
    caplog.set_level(logging.INFO)
    a, b = lab.fake("A", running=0), lab.fake("B", running=5)
    r = lab.router([a, b], LLM_ROUTER_PREFIX_CHARS=0, LLM_ROUTER_SCRAPE_S=0.1, LLM_ROUTER_COOLDOWN_S=0.3)
    boom = _Boom(r.app._probe, a.srv.port)
    r.app._probe = boom
    _wait(lambda: boom.calls >= 5, what="A 의 지표 탐침이 여러 번 터지기")
    st = r.by_url()
    assert st[a.base]["reachable"] is False and st[b.base]["up"] is True
    assert [r.chat("x").json()["served_by"] for _ in range(5)] == ["B"] * 5, "A 가 한가해 보여도(0 대 5) 뺀 서버다"
    warns = [x for x in caplog.records if "뜻밖의 오류" in x.getMessage() and a.base in x.getMessage()]
    assert len(warns) == 1 and not any(x.exc_info for x in caplog.records), "주기마다 traceback 을 찍지 않는다"


def test_검토H1_요청을_못_만든_서버는_빼고_다음_서버로_보낸_뒤의_뜻밖은_다시_보내지_않는다(lab):
    a, b = lab.fake("A", running=0), lab.fake("B", running=5)
    r = lab.router([a, b], LLM_ROUTER_PREFIX_CHARS=0, LLM_ROUTER_COOLDOWN_S=30)
    ua = next(u for u in r.app.ups if u.url == a.base)

    class _BadBase:
        def copy_with(self, **kw):
            raise ValueError("이 서버 주소로는 요청을 못 만든다")

    good_base, ua.base = ua.base, _BadBase()
    resp = r.chat("x")
    assert resp.status_code == 200 and resp.json()["served_by"] == "B", "보낸 것이 없으니 다음 서버로"
    st = r.by_url()[a.base]
    assert (st["reachable"], st["sent"], st["retried_away"]) == (False, 0, 1)
    # 보내는 중의 뜻밖 — 닿았는지 모르니 다시 보내지 않는다(LP-D3). 이 요청은 502 이고 그 서버는 뺀다.
    ua.base, ua.down_until = good_base, 0.0
    r.app._client = _Boom(r.app._client, a.srv.port)
    resp = r.chat("x")
    assert resp.status_code == 502 and resp.json()["error"]["type"] == "llm_router_upstream_error", resp.text
    assert len(b.hits) == 1, "B 에 다시 보내지 않았다"
    assert r.chat("x").json()["served_by"] == "B", "뺀 서버는 고르지 않는다 — 라우터 전체는 멀쩡하다"


def test_검토H1_기동_때_서버_하나가_터져도_라우터는_뜬다(lab, monkeypatch):
    a, b = lab.fake("A"), lab.fake("B")
    orig = R.Router._scrape

    async def scrape(self, u):
        if u.url == a.base:
            raise RuntimeError("뜻밖")
        return await orig(self, u)
    monkeypatch.setattr(R.Router, "_scrape", scrape)
    r = lab.router([a, b], LLM_ROUTER_PREFIX_CHARS=0, LLM_ROUTER_SCRAPE_S=0.1)       # 기동 gather 가 return_exceptions 가 아니면 여기서 죽는다
    assert r.chat("x").status_code == 200
    _wait(lambda: r.by_url()[a.base]["reachable"] is False, what="터지는 서버를 빼기")
    assert all(r.chat("x").json()["served_by"] == "B" for _ in range(3))


def test_검토M1_다른_모델로_다시_뜬_서버는_빨리_실패해도_요청을_끌어가지_않는다(lab):
    """한쪽 vLLM 이 다른 --served-model-name 으로 다시 떴다 — 그 서버는 '모델 없음' 404 를 곧바로 내 도는 수가 늘 0 이라 가장 한가해 보였다
    (검토: 20/20 실패). 요청이 적은 모델이 있는 서버를 먼저 고른다."""
    a = lab.fake("A", running=6)
    b = lab.fake("B", running=0, model="other")
    b.mode = "404model"
    r = lab.router([a, b], LLM_ROUTER_SCRAPE_S=0.1)
    h = r.health().json()
    assert (h["status"], h["upstreams_up"], h["models"]["match"]) == ("degraded", 2, False)
    assert [r.chat(f"대화 {i} — 서로 다른 앞부분").status_code for i in range(20)] == [200] * 20 and not b.hits
    assert r.http.post("/v1/chat/completions", json={"model": "other", "messages": []}).json()["served_by"] == "B", \
        "그 모델을 적은 요청은 그 모델이 있는 서버로"


def test_요청이_적은_모델이_있는_서버를_먼저_고르고_어디에도_없으면_가장_한가한_서버(lab):
    a, b = lab.fake("A", running=0), lab.fake("B", running=9, model="qwen")
    r = lab.router([a, b], LLM_ROUTER_PREFIX_CHARS=0)
    post = lambda body: r.http.post("/v1/chat/completions", json=body).json()["served_by"]   # noqa: E731
    assert post({"model": "qwen", "messages": []}) == "B", "바빠도 그 모델은 B 에만 있다"
    assert post({"model": "glm", "messages": []}) == "A"
    assert post({"model": "nope", "messages": []}) == "A" and post({"messages": []}) == "A", "어디에도 없거나 적지 않았으면 부하로"


def test_검토M5_모델_목록을_못_주는_서버는_올라옴이_아니다(lab):
    """오타 난 포트의 다른 앱(모든 경로 404) — 연결은 되고 지표가 없어 가장 한가해 보였다(검토: /health ok 2/2 · 10/10 이 그 앱으로).
    /v1/models 가 모델 목록을 줄 때만 '올라옴' 이고 upstreams_up 은 그 수다(update-all 1i 의 관문)."""
    a = lab.fake("A", running=3)
    other = lab.fake("OTHER")
    other.metrics_mode = other.models_mode = "404"
    other.mode = "404model"
    r = lab.router([a, other], LLM_ROUTER_SCRAPE_S=0.1)
    h = r.health().json()
    assert (h["status"], h["upstreams_up"], h["upstreams_reachable"], h["upstreams_total"]) == ("degraded", 1, 2, 2)
    assert h["models"]["errors"] == {other.base: 404}
    assert [r.chat(f"q{i}").json()["served_by"] for i in range(10)] == ["A"] * 10 and not other.hits
    no_model = [r.http.post("/v1/chat/completions", json={"messages": [{"role": "user", "content": f"q{i}"}]}).json()["served_by"]
                for i in range(5)]
    assert no_model == ["A"] * 5 and not other.hits, "모델을 적지 않은 요청도 — 고르는 것은 '올라옴' 이 먼저다(모델 고르기가 가려 주지 않는다)"
    st = r.by_url()[other.base]
    assert (st["up"], st["reachable"], st["models"], st["models_error"]) == (False, True, "error", 404)
    other.models_mode = "garbage"                       # 200 인데 모델 목록이 아니다 — 역시 올라옴이 아니다
    r.app._models_kick.set()
    _wait(lambda: r.health().json()["models"]["errors"] == {other.base: "not-a-model-list"}, what="목록 아님")
    assert r.health().json()["upstreams_up"] == 1


def test_모델_목록을_아직_모르는_서버는_올라온_서버가_없을_때만_쓴다(lab, monkeypatch):
    monkeypatch.setattr(R, "PROBE_READ_S", 0.3)
    monkeypatch.setattr(R, "MODELS_EVERY_S", 0.3)
    a, b = lab.fake("A", running=5), lab.fake("B", running=0)
    b.models_mode = "hang"
    r = lab.router([a], LLM_ROUTER_PREFIX_CHARS=0, LLM_ROUTER_SCRAPE_S=0.1)
    _write_env(r.env, [a.base, b.base], LLM_ROUTER_PREFIX_CHARS=0, LLM_ROUTER_SCRAPE_S=0.1)
    st = _until(r.by_url, lambda s: b.base in s and s[b.base]["running"] == 0.0 and s[b.base]["models_error"] == "ReadTimeout",
                what="B 가 더해지고 지표는 읽히되 모델 대조는 답 없이 끝나기")[b.base]
    assert (st["models"], st["up"], st["reachable"]) == ("unknown", False, True) and r.health().json()["upstreams_up"] == 1
    assert all(r.chat("x").json()["served_by"] == "A" for _ in range(3)), "B(0) 가 A(5) 보다 한가해도 모르는 서버다"
    assert all(r.http.post("/v1/chat/completions", json={"messages": []}).json()["served_by"] == "A" for _ in range(3)), \
        "모델을 적지 않은 요청도 모르는 서버로 가지 않는다"
    b.models_mode = "ok"
    _wait(lambda: r.by_url()[b.base]["models"] == "ok", what="B 의 모델 목록이 읽히기")
    assert r.chat("x").json()["served_by"] == "B"


def test_올라온_서버가_없으면_연결되는_서버로_보내되_upstreams_up_은_0_이고_까닭을_싣는다(lab, caplog, monkeypatch):
    """검토 L7 — vLLM 이 --api-key 로 떴는데 infra/.env 에 LLM_API_KEY 가 없다(401). 대조를 못 해도 손님 요청은 손님 키로 간다 — 보내기는 하되
    1i 가 사본을 바꾸지 않게 upstreams_up 은 0 이고, 까닭은 서버마다 한 번 로그와 /health 의 models.errors 에."""
    caplog.set_level(logging.INFO)
    monkeypatch.setattr(R, "MODELS_EVERY_S", 0.1)
    a, b = lab.fake("A"), lab.fake("B", max_len=16_384)
    a.models_mode = b.models_mode = "401"
    r = lab.router([a, b], LLM_ROUTER_SCRAPE_S=0.1)
    h = r.health()
    body = h.json()
    assert h.status_code == 200 and (body["status"], body["upstreams_up"], body["upstreams_reachable"]) == ("degraded", 0, 2)
    assert body["models"]["errors"] == {a.base: 401, b.base: 401} and body["models"]["match"] is None
    assert r.chat("x").status_code == 200
    _wait(lambda: len(a.model_hits) >= 4, what="대조가 여러 번 돌기")
    warns = [x.getMessage() for x in caplog.records if "모델 목록을 못 읽었다" in x.getMessage()]
    assert len(warns) == 2 and all("HTTP 401" in w and "LLM_API_KEY" in w for w in warns), warns


def test_검토M2_지표를_잠깐_못_읽어도_세_번째_실패까지는_마지막_지표로_잰다(lab, monkeypatch, caplog):
    """바쁜 서버는 /metrics 도 늦다 — 한 번 읽기 한도를 넘겼다고 마지막 지표를 버리면 가장 바쁜 서버(40)가 가장 한가해 보여 5/5 가 그리로 갔다."""
    caplog.set_level(logging.INFO)
    monkeypatch.setattr(R, "PROBE_READ_S", 0.3)
    a, b = lab.fake("A", running=40), lab.fake("B", running=10)
    r = lab.router([a, b], LLM_ROUTER_PREFIX_CHARS=0, LLM_ROUTER_SCRAPE_S=0.2)
    assert r.chat("x").json()["served_by"] == "B"
    a.metrics_mode = "hang"
    st = _until(r.by_url, lambda s: 1 <= s[a.base]["metrics_fail"] < R.METRICS_KEEP_FAILS, what="A 의 지표 읽기 실패 1~2번")[a.base]
    assert st["running"] == 40.0 and st["metrics_age_s"] > 0 and st["up"] is True
    assert [r.chat("x").json()["served_by"] for _ in range(5)] == ["B"] * 5, "A 는 여전히 40 이 돈다"
    _wait(lambda: r.by_url()[a.base]["running"] is None, timeout=8, what="세 번째 실패에 마지막 지표를 버리기")
    lost = [x.getMessage() for x in caplog.records if "연달아 못 읽었다" in x.getMessage()]
    assert len(lost) == 1 and a.base in lost[0]
    a.metrics_mode = "ok"
    _wait(lambda: r.by_url()[a.base]["running"] == 40.0, timeout=8, what="다시 읽히기")
    assert any("지표 다시 읽힘" in x.getMessage() for x in caplog.records)
    time.sleep(0.6)
    assert len([x for x in caplog.records if "연달아 못 읽었다" in x.getMessage()]) == 1, "바뀔 때만 한 번"


def test_지표_5xx_는_일시_실패이고_vLLM_아닌_글은_곧바로_보낸_수로만(lab, caplog):
    caplog.set_level(logging.INFO)
    a, b = lab.fake("A", running=7), lab.fake("B", running=7)
    r = lab.router([a, b], LLM_ROUTER_PREFIX_CHARS=0, LLM_ROUTER_SCRAPE_S=0.1)
    a.metrics_mode = "500"
    st = _until(r.by_url, lambda s: 1 <= s[a.base]["metrics_fail"] < R.METRICS_KEEP_FAILS, what="5xx 한두 번")[a.base]
    assert st["running"] == 7.0, "5xx 는 일시 실패 — 마지막 지표를 쓴다"
    _wait(lambda: r.by_url()[a.base]["running"] is None, what="세 번째에 버리기")
    b.metrics_mode = "garbage"
    st = _until(r.by_url, lambda s: s[b.base]["running"] is None, what="vLLM 모양이 아닌 글은 곧바로")[b.base]
    assert st["metrics_fail"] == 0 and st["up"] is True
    time.sleep(0.4)
    assert sum("지표 없음" in x.getMessage() and b.base in x.getMessage() for x in caplog.records) == 1


def test_검토L9_지표가_아직_세지_않은_요청도_부하에서_빠지지_않는다(lab):
    """vLLM 은 본문을 받고 토큰으로 바꾼 뒤에야 센다(1M 창이면 몇 초). 그 사이 지표를 읽으면 그 요청들이 부하에서 사라져 같은 서버로 또 몰렸다
    (검토: 2 대 2 인데 다음 둘도 A). 부하는 이 라우터가 그 서버에 보내 도는 수보다 작아지지 않는다."""
    a, b = lab.fake("A", running=0), lab.fake("B", running=2)
    a.mode = b.mode = "hold"
    r = lab.router([a, b], LLM_ROUTER_PREFIX_CHARS=0, LLM_ROUTER_SCRAPE_S=0.1)
    jobs = []

    def send_one():
        n = len(a.hits) + len(b.hits)
        jobs.append(_bg(lambda: r.chat("x")))
        _wait(lambda: len(a.hits) + len(b.hits) > n, what="닿기")
    send_one()
    send_one()
    assert (len(a.hits), len(b.hits)) == (2, 0)
    time.sleep(0.35)          # 지표 주기 세 번 — A 에 둘이 도는 동안 A 의 지표(running 0)를 다시 읽는다
    assert (r.by_url()[a.base]["running"], r.by_url()[a.base]["inflight"]) == (0.0, 2)
    send_one()
    send_one()
    assert (len(a.hits), len(b.hits)) == (3, 1), "A 는 둘이 돈다 — 지표가 0 이어도 B(2)와 같고(목록 앞), 그다음은 B"
    a.release.set()
    b.release.set()
    for j in jobs:
        j["t"].join(10)
        assert j["r"].status_code == 200


def test_검토L3_손님이_보내지_않은_머리를_덧붙이지_않는다(lab):
    """client.build_request 는 클라이언트 기본 머리(user-agent · accept · accept-encoding: gzip)를 덧붙였다 — 위 서버가 gzip 으로 답하면
    손님은 청하지 않은 content-encoding 을 받는다."""
    a = lab.fake("A")
    r = lab.router([a])
    got = _raw_request(r.srv.port, b"GET /v1/echo HTTP/1.1\r\nHost: r\r\nConnection: close\r\n\r\n")
    assert b" 200 " in got.split(b"\r\n", 1)[0] and a.hits[-1]["path"] == "/v1/echo"
    assert not {"accept-encoding", "accept", "user-agent"} & set(a.hits[-1]["headers"]), a.hits[-1]["headers"]


@pytest.mark.parametrize("impl", HTTP_IMPLS)
def test_검토L4_요청_대상이_빗금으로_시작하지_않으면_목록_밖_호스트로_가지_않는다(lab, impl):
    """`origin + 대상` 으로 이으면 h11 이 받는 `GET @다른호스트:포트/…` 가 목록 밖 호스트로 가고 Bearer 가 Basic 으로 바뀌었다."""
    a, other = lab.fake("A"), lab.fake("OTHER")
    r = lab.router([a], http=impl)
    for target in (b"@127.0.0.1:%d/v1/models" % other.srv.port, b"http://127.0.0.1:%d/v1/models" % other.srv.port):
        got = _raw_request(r.srv.port, b"GET " + target + b" HTTP/1.1\r\nHost: r\r\nAuthorization: Bearer k\r\nConnection: close\r\n\r\n")
        status = got.split(b"\r\n", 1)[0]
        if impl == "h11":
            assert b" 400 " in status and b"llm_router_bad_target" in got, got[:200]
    assert other.model_hits == [] and other.hits == [], "목록 밖 호스트에는 아무것도 가지 않는다"
    got = _raw_request(r.srv.port, b"GET /v1/x#frag HTTP/1.1\r\nHost: r\r\nConnection: close\r\n\r\n")   # httptools 는 조각을 떼고 넘긴다
    if impl == "h11":
        assert b" 400 " in got.split(b"\r\n", 1)[0], got[:200]
    assert r.by_url()[a.base]["reachable"] is True, "손님 탓은 서버를 빼지 않는다"


def test_검토L8_멈춘_올리기는_도는_수에_들지_않는다(lab):
    """본문이 다 오기 전에 센 도는 수는 멈춘 올리기 하나에 영영 1 이다 — update-sites 가 라우터 재기동을 강행 전까지 미뤘다."""
    a = lab.fake("A")
    r = lab.router([a])
    s = socket.create_connection(("127.0.0.1", r.srv.port), timeout=5)
    try:
        s.sendall(b"POST /v1/chat/completions HTTP/1.1\r\nHost: r\r\nContent-Length: 1000\r\n\r\n{\"model\":")
        time.sleep(0.5)
        assert r.health().json()["inflight"] == 0
    finally:
        s.close()
    assert not a.hits


def test_검토L6_설정_파일이_지워지면_한_번_알리고_마지막_설정으로_보낸다(lab, caplog):
    caplog.set_level(logging.INFO)
    a = lab.fake("A")
    r = lab.router([a], LLM_ROUTER_SCRAPE_S=0.1)
    r.env.unlink()
    _wait(lambda: any("없다(지워졌다)" in x.getMessage() for x in caplog.records), what="지워진 것을 알리기")
    time.sleep(0.5)
    assert sum("없다(지워졌다)" in x.getMessage() for x in caplog.records) == 1, "못 읽은 모양마다 한 번"
    assert r.chat("x").json()["served_by"] == "A", "마지막으로 읽은 설정을 그대로 쓴다"
    _write_env(r.env, [a.base], LLM_ROUTER_SCRAPE_S=0.1)
    _wait(lambda: any("설정 다시 읽음" in x.getMessage() for x in caplog.records), what="다시 생긴 파일을 읽기")


def test_검토L12_같은_크기_같은_시각의_제자리_편집도_읽는다(lab):
    """mtime·크기·inode 로 보면 NFS 처럼 시각 칸이 굵은 곳에서 같은 길이의 편집을 영영 못 본다 — 주기마다 내용을 견준다."""
    a, b = lab.fake("A"), lab.fake("B")
    r = lab.router([a], LLM_ROUTER_PREFIX_CHARS=0, LLM_ROUTER_SCRAPE_S=0.1)
    st = r.env.stat()
    text = r.env.read_text(encoding="utf-8")
    new = text.replace(a.base, b.base)
    assert len(new) == len(text)
    with open(r.env, "r+", encoding="utf-8") as f:
        f.write(new)
    os.utime(r.env, ns=(st.st_atime_ns, st.st_mtime_ns))
    _wait(lambda: [s["url"] for s in r.stats()] == [b.base], what="바뀐 내용을 읽기")


def test_검토L5_틀린_칸은_원문을_찍지_않는다(monkeypatch):
    """질의에 붙인 키 · 잘못 붙여 넣은 키가 그대로 로그(0664)에 남았다 — 스킴과 호스트만."""
    monkeypatch.delenv("LLM_ROUTER_PORT", raising=False)
    cfg = R.build_config({"LLM_UPSTREAMS": "http://h:8000/v1?api_key=SECRET123,sk-live-SECRET456,http://user:pw@h2/v1"})
    assert cfg.upstreams == () and len(cfg.problems) == 3
    assert not any("SECRET" in p or "user:pw" in p for p in cfg.problems), cfg.problems
    assert [re.search(r"칸 (\S+)", p).group(1) for p in cfg.problems] == ["http://h", "?://?", "http://h2"]


def test_검토L10_인증서를_믿을_수_없는_https_서버는_따로_알린다(lab, tmp_path, caplog):
    """사설 CA 를 줄 자리가 없다(trust_env=False · --cleanenv) — 받지 않기로 했다(LP-D13). 대신 '연결 실패' 와 섞이지 않게 따로 말한다."""
    if not shutil.which("openssl"):
        pytest.skip("openssl 이 없다")
    caplog.set_level(logging.INFO)
    key, crt = tmp_path / "k.pem", tmp_path / "c.pem"
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", str(key), "-out", str(crt), "-days", "1",
                    "-subj", "/CN=127.0.0.1"], check=True, capture_output=True, timeout=60)
    f = _Fake("TLS")
    f.srv = _Srv(f, tls=(crt, key))
    lab.servers.append(f.srv)
    r = lab.router([f"https://127.0.0.1:{f.srv.port}/v1"], LLM_ROUTER_COOLDOWN_S=30)
    assert r.health().status_code == 503
    tls = [x.getMessage() for x in caplog.records if "TLS 인증서" in x.getMessage()]
    assert len(tls) == 1 and "사설 CA" in tls[0] and "http 이거나 공인 인증서" in tls[0], tls


def test_같은_앞부분이_몰려도_두_서버의_차이는_기본_문턱_2_까지만_벌어진다(lab):
    """LP-D7 이 말한 '8 개가 나뉜다' — 문턱 4 에서는 같은 앞부분 8 개가 6·2 였다(검토 L11). 기본 2 면 5·3 이다(차이는 많아야 문턱)."""
    a, b = lab.fake("A"), lab.fake("B")
    a.mode = b.mode = "hold"
    r = lab.router([a, b])
    assert r.app.cfg.sticky_slack == 2.0
    jobs = []
    for _ in range(8):
        n = len(a.hits) + len(b.hits)
        jobs.append(_bg(lambda: r.chat("같은 서식")))
        _wait(lambda n=n: len(a.hits) + len(b.hits) > n, what="닿기")
    assert sorted((len(a.hits), len(b.hits))) == [3, 5], (len(a.hits), len(b.hits))
    a.release.set()
    b.release.set()
    for j in jobs:
        j["t"].join(10)
        assert j["r"].status_code == 200


# ── 띄우는 스크립트 — 검토 L1 · 배선 M4 ───────────────────────────────────────────────────────────────
def test_run_은_정본_규칙에_틀린_목록이면_띄우지_않고_환경의_포트를_먼저_본다(tmp_path):
    cases = ['LLM_UPSTREAMS="http://a.example:8000/v1", "http://b.example:8000/v1"\n',     # 포털 start.sh 의 소싱을 죽이는 줄(배선 M1)
             "LLM_UPSTREAMS=http://203.0.113.256:8000/v1\n",
             "LLM_UPSTREAMS=http://127.0.0.1:9131/v1\nLLM_ROUTER_PORT=9131\n"]               # 라우터 자신
    for i, text in enumerate(cases):
        sub = tmp_path / f"c{i}"
        sub.mkdir()
        lay, stub, out = _lay(sub, text)
        r = _launch(lay, stub, out, "run")
        assert r.returncode == 2 and "LLM_UPSTREAMS 를 쓸 수 없어" in r.stderr and not out.exists(), (text, r.stderr)
    sub = tmp_path / "env"
    sub.mkdir()
    lay, stub, out = _lay(sub, "LLM_UPSTREAMS=http://127.0.0.1:9131/v1\nLLM_ROUTER_PORT=9555\n")
    r = _launch(lay, stub, out, "run", env={"LLM_ROUTER_PORT": "9131"})
    assert r.returncode == 2 and "라우터 자신" in r.stderr and not out.exists(), "환경의 포트가 실제로 듣는 포트다"
    r = _launch(lay, stub, out, "run", env={"LLM_ROUTER_PORT": "9132"})
    argv = out.read_text().splitlines()
    assert r.returncode == 0 and argv[argv.index("--port") + 1] == "9132" and "LLM_ROUTER_PORT=9132" in argv, (r.stderr, argv)


def _bin_without(tmp_path: Path, *drop: str) -> str:
    """PATH 로 쓸 디렉터리 — 띄우는 스크립트가 부르는 명령을 링크로 두고 drop 은 뺀다."""
    d = tmp_path / "bin"
    d.mkdir()
    for name in ("bash", "sed", "tail", "tr", "grep", "cut", "sort", "seq", "sleep", "dirname", "basename", "ss", "cat"):
        p = shutil.which(name)
        if name not in drop and p:
            (d / name).symlink_to(p)
    return str(d)


def test_stop_은_모르면_실패한다_ss_가_없거나_pid_가_안_보이는_리스너(tmp_path):
    """'이미 내려가 있다' rc 0 이던 두 경우(검토 L1) — update-all 의 내리기는 rc 를 믿는다. 그 포트에 남이 떠 있으면 사본들이 키와 프롬프트를
    그리로 보낸다."""
    port = _free_port()
    lay, stub, out = _lay(tmp_path, f"LLM_UPSTREAMS=http://203.0.113.5:8000/v1\nLLM_ROUTER_PORT={port}\n")
    mine = _listener(port, "llm_router:app")
    try:
        r = _launch(lay, stub, out, "stop", path=_bin_without(tmp_path, "ss"))
        assert r.returncode == 1 and "ss" in r.stderr and "이미 내려가" not in r.stdout and mine.poll() is None, r.stdout + r.stderr
    finally:
        mine.kill()
        mine.wait(10)
    fake = tmp_path / "fakess"
    fake.mkdir()
    (fake / "ss").write_text(f"#!/usr/bin/env bash\necho 'LISTEN 0 4096 127.0.0.1:{port} 0.0.0.0:*'\n", encoding="utf-8")
    (fake / "ss").chmod(0o755)
    r = _launch(lay, stub, out, "stop", path=f"{fake}:{os.environ['PATH']}")
    assert r.returncode == 1 and "pid 가 안 보인다" in r.stderr, r.stdout + r.stderr


def test_stop_은_환경의_포트를_infra_env_보다_먼저_본다(tmp_path):
    """update-all 이 옛 포트에 남은 라우터를 내릴 때 그 포트를 환경으로 준다(배선 M4)."""
    port = _free_port()
    other = next(p for p in iter(_free_port, None) if p != port)
    lay, stub, out = _lay(tmp_path, f"LLM_UPSTREAMS=http://203.0.113.5:8000/v1\nLLM_ROUTER_PORT={other}\n")
    mine = _listener(port, "llm_router:app")
    try:
        r = _launch(lay, stub, out, "stop", env={"LLM_ROUTER_PORT": str(port)})
        assert r.returncode == 0 and f":{port}" in r.stdout and "내려갔다" in r.stdout, r.stdout + r.stderr
        assert mine.wait(10) is not None
    finally:
        if mine.poll() is None:
            mine.kill()


# ── 지문 — 검토 L2 ───────────────────────────────────────────────────────────────────────────────────
def test_지문은_바이트코드를_보지_않고_fp_git_false_면_리포_루트_env_도_보지_않는다(tmp_path):
    """`services.py fp llm-router` 가 import 한 번(__pycache__)과 포털 루트 .env(env-sync 가 덧붙인다)에 바뀌었다 — 라우터가 쓸데없이 재기동된다."""
    spec = importlib.util.spec_from_file_location("svc_for_router_fp", ROOT / "infra/scripts/services.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    work = tmp_path / "work"
    (work / "code").mkdir(parents=True)
    (work / "code/router.py").write_text("v1\n", encoding="utf-8")
    svc = {"name": "r", "dir": str(work), "fp_git": False, "fp": ["code"]}
    plain = {"name": "p", "dir": str(work), "fp": ["code"]}             # fp_git 기본 — 다른 모든 서비스
    a, p0 = m.service_fp(svc), m.service_fp(plain)
    (work / "code/__pycache__").mkdir()
    (work / "code/__pycache__/router.cpython-313.pyc").write_bytes(b"\0" * 16)
    (work / "code/stray.pyc").write_bytes(b"\0")
    assert (m.service_fp(svc), m.service_fp(plain)) == (a, p0), "바이트코드는 어느 서비스의 지문에도 넣지 않는다"
    (work / ".env").write_text("NEW_KEY=1\n", encoding="utf-8")
    assert m.service_fp(svc) == a, "fp_git: false 면 리포 루트 .env 를 넣지 않는다"
    assert m.service_fp(plain) != p0, "기본은 종전대로 .env 가 든다"
    (work / "code/router.py").write_text("v2 — 코드가 바뀌었다\n", encoding="utf-8")
    assert m.service_fp(svc) != a
