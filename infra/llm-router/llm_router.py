# vLLM 서버 여럿 앞에서 /metrics 를 읽어 덜 바쁜 서버로 요청을 넘기는 LLM 라우터 — 원시 ASGI + httpx(docs/llm-pool PLAN §3)
"""LLM 라우터 — `python3 -m uvicorn --app-dir infra/llm-router llm_router:app` 으로 뜬다(infra/scripts/llm-router.sh run).

계약(PLAN §3 · context-notes LP-D2~D10).
  설정  리포 루트의 infra/.env 를 직접 읽는다(파일 위치에서 유도 — 키를 argv·환경으로 받지 않는다). LLM_ROUTER_ENV_FILE 은 시험·손 점검용
        다른 파일이다. 읽는 규칙은 update-all `_envfile_value` 와 같고, 파일이 바뀌면 다음 지표 주기에 다시 읽는다(재기동 없음).
        다시 읽은 목록이 비면 마지막 목록으로 계속 보내고 /health 의 kept_last_list 가 true 다 — 풀을 끄는 것은 update-all 이고(사본을 되돌린
        뒤 라우터를 내린다) 재기동이 미뤄진 손님은 그때까지 이 라우터를 부른다. 처음 읽을 때 비었으면 503 이다.
  고르기  부하 = 마지막 지표의 running + waiting(라벨 묶음 전부 합) + 그 뒤로 이 라우터가 더 보낸 수. 같으면 KV 사용률, 그다음 목록 순서.
  붙임  메시지 앞부분 PREFIX_CHARS 자의 해시 → 렌데부 해시로 선호 서버. 선호 서버가 가장 한가한 서버보다 STICKY_SLACK 이상 바쁘면 떨어진다.
  넘김  연결 실패(요청이 서버에 닿지 않은 것)만 그 서버를 COOLDOWN_S 동안 빼고 다른 서버로 — 요청마다 서버 하나에 한 번. 연결된 뒤의 일
        (HTTP 오류 · 생성 중 끊김)은 그대로 넘기고 다시 보내지 않는다(LP-D3). 모두 빠졌으면 전부를 다시 시도해 본다.
  흐름  위로는 늘 스트림으로 보내고 받은 바이트를 그대로 흘린다. 손님이 끊으면 머리 전이든 흐르는 중이든 곧바로 위 연결을 닫는다
        (vLLM 이 생성을 멈춘다 — 버려진 생성이 GPU 를 잡지 않게).
  시간  연결 한도 하나뿐이다. 읽기·쓰기 한도는 부르는 쪽의 것이다 — 시간 한도 사슬에 층을 끼우지 않는다.
  키    손님의 Authorization 을 그대로 넘기고 끼워 넣지 않는다(LP-D9). LLM_API_KEY 는 라우터 자신의 /v1/models 대조에만 쓴다.
  로그  요청마다 남기지 않는다 — 기동 · 다시 읽기 · 서버 오르내림 · 모델 어긋남 · 연결 실패만. 키와 본문은 어디에도 찍지 않는다.
"""
import asyncio
import contextlib
import hashlib
import json
import logging
import math
import os
import re
import sys
import time
from dataclasses import dataclass, replace
from pathlib import Path
from urllib.parse import urlsplit

import httpx

ROOT = Path(__file__).resolve().parents[2]   # infra/llm-router/llm_router.py → 리포 루트(dev ~/claude · cae00 ~/Projects · 컨테이너 /workspace)
DEFAULT_ENV_FILE = ROOT / "infra" / ".env"
LOG = logging.getLogger("llm_router")

MODELS_EVERY_S = 60.0     # /v1/models 대조 주기(설정이 바뀌어 서버 목록이 달라지면 곧바로 한 번 더)
PROBE_READ_S = 10.0       # 라우터 자신의 탐침(/metrics · /v1/models) 읽기 한도 — 손님 요청 경로가 아니다
BIG_BODY = 1 << 20        # 이보다 큰 본문은 JSON 해석을 이벤트 루프 밖에서 한다(1M 창 요청은 수 MB 다)

# 손잡이 → (기본값, 형, 최솟값). 수가 아니거나 최솟값보다 작으면 기본값으로 두고 읽을 때마다 한 줄 알린다.
KNOBS: dict[str, tuple[float, type, float]] = {
    "LLM_ROUTER_SCRAPE_S": (2.0, float, 0.05),
    "LLM_ROUTER_STICKY_SLACK": (4.0, float, 0.0),
    "LLM_ROUTER_PREFIX_CHARS": (8000, int, 0),
    "LLM_ROUTER_CONNECT_TIMEOUT_S": (5.0, float, 0.1),
    "LLM_ROUTER_COOLDOWN_S": (15.0, float, 0.0),
}

# 연결을 붙여 두지 않는다(keep-alive 0) — 요청마다 새로 연결하니 '연결 실패' 가 곧 '서버에 닿지 않았다' 이고, vLLM 이 닫은 유휴 연결을
# 다시 쓰다 생기는 '보냈는지 모르는 실패' 가 없다. 연결 수 상한도 없다 — 줄은 vLLM 이 세운다(waiting 으로 보인다).
_LIMITS = httpx.Limits(max_connections=None, max_keepalive_connections=0)
_HOP = frozenset({b"connection", b"keep-alive", b"proxy-authenticate", b"proxy-authorization", b"te", b"trailer", b"trailers",
                  b"transfer-encoding", b"upgrade"})
_REQ_DROP = _HOP | {b"host", b"content-length", b"expect"}    # 길이·호스트는 httpx 가 위 서버에 맞게 다시 단다
_RESP_DROP = _HOP | {b"date", b"server"}                      # uvicorn 이 자기 것을 단다 — 두 벌이 되지 않게


def _proxy_timeout(connect_s: float) -> httpx.Timeout:
    """손님 요청의 한도 — 연결뿐이다. 읽기·쓰기·풀 한도를 두면 부르는 쪽(엔진 1800초 · 리스크 앱 …)의 사슬 안에 라우터의 층이 하나 더
    생기고, 그 층이 먼저 끊으면 손잡이 이름 없는 끊김이 된다(docs/delib-engine-feedback D-17). 끊는 것은 부르는 쪽이고 그 끊김은 위로 전해진다."""
    return httpx.Timeout(connect=connect_s, read=None, write=None, pool=None)


def _probe_timeout(connect_s: float) -> httpx.Timeout:
    return httpx.Timeout(connect=connect_s, read=PROBE_READ_S, write=PROBE_READ_S, pool=PROBE_READ_S)


# ── 설정 ───────────────────────────────────────────────────────────────────────────────────────────
_ENV_LINE = re.compile(r"^[ \t]*(?:export[ \t]+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$")
_INLINE_COMMENT = re.compile(r"[ \t]+#.*$")    # ASCII 공백만 — services.py _infra_value 와 같다(NBSP 는 값의 일부다)


def read_env(path: Path) -> dict[str, str]:
    """infra/.env → {키: 값}. 규칙은 update-all `_envfile_value`(sed)·services.py `_infra_value` 와 같다 — `export` 허용, 공백 뒤 `#` 이후를
    벗긴 **뒤에** 양끝 공백을 지우고(먼저 지우면 `KEY=   # 설명` 의 설명이 값이 된다) 따옴표 문자·CR 을 지운다. 마지막 줄이 이기고 빈 값은
    없는 것이다. 줄은 개행으로만 나눈다(sed 와 같게 — splitlines 는 \\x85 같은 글자에서도 끊는다). 못 읽으면 OSError 가 그대로 올라간다."""
    vals: dict[str, str] = {}
    for ln in path.read_text(encoding="utf-8", errors="replace").split("\n"):
        m = _ENV_LINE.match(ln)
        if m:
            v = _INLINE_COMMENT.sub("", m.group(2)).strip(" \t")
            vals[m.group(1)] = v.replace('"', "").replace("'", "").replace("\r", "")
    return {k: v for k, v in vals.items() if v}


def parse_upstreams(raw: str | None) -> tuple[list[str], list[str]]:
    """LLM_UPSTREAMS → (쓸 /v1 주소들, 못 쓰는 항목들). 쉼표·공백으로 나누고 끝 `/` 를 떼고 같은 주소는 하나로 둔다."""
    good: list[str] = []
    bad: list[str] = []
    for tok in re.split(r"[\s,]+", raw or ""):
        if not tok:
            continue
        url = tok.rstrip("/")
        try:
            p = urlsplit(url)
            ok = p.scheme in ("http", "https") and bool(p.hostname) and not (p.query or p.fragment or "@" in p.netloc)
            _ = p.port          # 포트가 수가 아니면 ValueError
        except ValueError:
            ok = False
        if not ok:
            bad.append("(사용자 정보가 든 항목 — 값은 찍지 않는다)" if "@" in tok else tok)
        elif url not in good:
            good.append(url)
    return good, bad


@dataclass(frozen=True)
class Config:
    upstreams: tuple[str, ...] = ()
    api_key: str | None = None
    scrape_s: float = 2.0
    sticky_slack: float = 4.0
    prefix_chars: int = 8000
    connect_timeout_s: float = 5.0
    cooldown_s: float = 15.0
    problems: tuple[str, ...] = ()


def build_config(vals: dict[str, str]) -> Config:
    problems: list[str] = []
    knob: dict[str, float] = {}
    for key, (default, kind, floor) in KNOBS.items():
        raw, v = vals.get(key), default
        if raw is not None:
            try:
                f = float(raw)
                if not math.isfinite(f) or f < floor:
                    raise ValueError
                v = int(f) if kind is int else f
            except ValueError:
                problems.append(f"{key}={raw!r} 를 쓸 수 없어 기본값 {default:g} 로 둔다({floor:g} 이상의 수)")
        knob[key] = v
    ups, bad = parse_upstreams(vals.get("LLM_UPSTREAMS"))
    problems += [f"LLM_UPSTREAMS 의 항목 {b} 는 http(s)://호스트[:포트][/v1] 모양이 아니라 뺐다" for b in bad]
    return Config(upstreams=tuple(ups), api_key=vals.get("LLM_API_KEY"), scrape_s=knob["LLM_ROUTER_SCRAPE_S"],
                  sticky_slack=knob["LLM_ROUTER_STICKY_SLACK"], prefix_chars=int(knob["LLM_ROUTER_PREFIX_CHARS"]),
                  connect_timeout_s=knob["LLM_ROUTER_CONNECT_TIMEOUT_S"], cooldown_s=knob["LLM_ROUTER_COOLDOWN_S"],
                  problems=tuple(problems))


def _file_sig(p: Path) -> tuple[int, int, int] | None:
    try:
        st = p.stat()
    except OSError:
        return None
    return st.st_mtime_ns, st.st_size, st.st_ino


# ── 지표 ───────────────────────────────────────────────────────────────────────────────────────────
RUNNING, WAITING = "vllm:num_requests_running", "vllm:num_requests_waiting"
KV_NAMES = ("vllm:kv_cache_usage_perc", "vllm:gpu_cache_usage_perc")   # 새 이름 먼저 — 옛 vLLM 은 뒤의 이름만 낸다
_SAMPLE = re.compile(r"([A-Za-z_:][A-Za-z0-9_:]*)(\{.*\})?[ \t]+([^ \t]+)")


def parse_metrics(text: str) -> dict[str, float | None] | None:
    """Prometheus 글 → {running, waiting, kv}. running·waiting 중 하나라도 없으면 None(지표 없음 — 이 라우터가 보낸 수로만 잰다).
    이름은 **정확히** 같은 것만 센다 — vLLM 은 `vllm:num_requests_waiting_by_reason{reason=…}` 도 내고 그 합이 waiting 과 같아서, 접두로
    세면 waiting 이 두 배가 된다. running·waiting 은 라벨 묶음(엔진) 전부를 더하고 KV 는 가장 큰 값이다."""
    acc: dict[str, list[float]] = {}
    wanted = (RUNNING, WAITING, *KV_NAMES)
    for ln in text.split("\n"):
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        m = _SAMPLE.match(ln)
        if not m or m.group(1) not in wanted:
            continue
        try:
            v = float(m.group(3))
        except ValueError:
            continue
        if math.isfinite(v):
            acc.setdefault(m.group(1), []).append(v)
    if RUNNING not in acc or WAITING not in acc:
        return None
    kv = next((max(acc[n]) for n in KV_NAMES if n in acc), None)
    return {"running": sum(acc[RUNNING]), "waiting": sum(acc[WAITING]), "kv": kv}


# ── 붙임 열쇠 ───────────────────────────────────────────────────────────────────────────────────────
def _prefix_text(obj: dict, n: int) -> str | None:
    msgs = obj.get("messages")
    if isinstance(msgs, list) and msgs:
        out: list[str] = []
        total = 0
        for m in msgs:
            if not isinstance(m, dict):
                continue
            role = m.get("role") if isinstance(m.get("role"), str) else ""
            c = m.get("content")
            if isinstance(c, str):
                text = c
            elif isinstance(c, list):    # 내용 조각 목록 — 글 조각만(그림 조각은 뺀다)
                text = "".join(p["text"] for p in c if isinstance(p, dict) and isinstance(p.get("text"), str))
            else:
                text = ""
            seg = f"{role}:{text}\n"
            out.append(seg)
            total += len(seg)
            if total >= n:
                break
        return "".join(out)[:n]
    p = obj.get("prompt")
    if isinstance(p, str):
        return p[:n]
    if isinstance(p, list) and p:
        return ("\n".join(p) if all(isinstance(x, str) for x in p) else json.dumps(p, ensure_ascii=False))[:n]
    return None


def sticky_key(body: bytes, prefix_chars: int) -> bytes | None:
    """본문의 메시지 앞부분(PREFIX_CHARS 자)의 해시 — 같은 전문가의 카드 묶음 · 같은 대화가 같은 서버의 접두 캐시를 다시 쓴다(LP-D2·D8).
    `messages` 면 `역할:내용` 을 차례로 이은 앞부분, `prompt` 면 그 앞부분. 그 밖(JSON 이 아님 · 둘 다 없음)이면 None — 붙이지 않는다."""
    if prefix_chars <= 0 or not body.lstrip().startswith(b"{"):
        return None
    try:
        obj = json.loads(body)
    except (ValueError, RecursionError):
        return None
    text = _prefix_text(obj, prefix_chars) if isinstance(obj, dict) else None
    if text is None:
        return None
    return hashlib.blake2b(text.encode("utf-8", "surrogatepass"), digest_size=16).digest()


def _rank(key: bytes, url: str) -> int:
    """렌데부 해시 — 열쇠마다 서버 순위. 서버가 빠지거나 더해져도 다른 열쇠의 선호 서버는 그대로다."""
    return int.from_bytes(hashlib.blake2b(key + url.encode(), digest_size=8).digest(), "big")


# ── 서버 하나 ──────────────────────────────────────────────────────────────────────────────────────
class Upstream:
    """서버 하나의 상태 — 이벤트 루프에서만 만진다."""

    def __init__(self, url: str) -> None:
        self.url = url
        self.origin = url[:-3] if url.endswith("/v1") else url
        self.metrics: dict[str, float | None] | None = None
        self.scraped_at: float | None = None
        self.inflight = 0
        self.inflight_at_scrape = 0
        self.down_until = 0.0          # 연결 실패 뒤 이 시각까지 뺀다(지표 연결도 실패하면 다시 늘어난다)
        self.down_noted = False        # '내려감' 을 알렸고 아직 '올라옴' 을 못 알렸다
        self.models: tuple[frozenset[str], tuple[tuple[str, object], ...]] | None = None
        self.sent = self.connect_fail = self.retried_away = self.sticky = self.overflow = 0

    def is_up(self, now: float) -> bool:
        return now >= self.down_until

    def load(self) -> float:
        """마지막 지표의 running + waiting 에 '그 뒤로 이 라우터가 더 보낸 수'(0 아래는 0)를 더한다. 지표가 없으면 보낸 수만."""
        if self.metrics is None:
            return float(self.inflight)
        return self.metrics["running"] + self.metrics["waiting"] + max(0, self.inflight - self.inflight_at_scrape)

    def kv(self) -> float:
        return (self.metrics or {}).get("kv") or 0.0


# ── 라우터 ─────────────────────────────────────────────────────────────────────────────────────────
class Router:
    """ASGI 앱 자체다. 기동(lifespan)에서 설정을 읽고 지표를 한 바퀴 읽은 뒤 손님을 받는다."""

    def __init__(self, env_file: Path, *, log_to_stderr: bool = False) -> None:
        self.env_file = Path(env_file)
        self.log_to_stderr = log_to_stderr
        self.cfg = Config()
        self.ups: list[Upstream] = []
        self.inflight = 0
        self._sig: tuple[int, int, int] | None = None
        self._bad_sig: tuple[int, int, int] | None = None
        self._mtime: float | None = None
        self._client: httpx.AsyncClient | None = None
        self._probe: httpx.AsyncClient | None = None
        self._loops: dict[str, asyncio.Task] = {}
        self._tasks: list[asyncio.Task] = []
        self._models_kick: asyncio.Event | None = None
        self._models_warned: str | None = None
        self._all_failed_noted = -math.inf
        self._running = False
        self.kept_last_list = False    # 파일의 목록이 비어 마지막 목록을 이어 쓰는 중(/health 에 싣는다)

    # ── ASGI ──
    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] == "lifespan":
            await self._lifespan(receive, send)
        elif scope["type"] == "http":
            if scope["path"] in ("/health", "/stats"):
                await self._own(scope, send)
            else:
                await self._proxy(scope, receive, send)
        # 웹소켓은 다루지 않는다 — 받지 않고 돌아가면 서버가 닫는다

    async def _lifespan(self, receive, send) -> None:
        while True:
            msg = await receive()
            if msg["type"] == "lifespan.startup":
                try:
                    await self.start()
                except Exception as exc:
                    LOG.exception("기동 실패")
                    await send({"type": "lifespan.startup.failed", "message": str(exc)})
                    return
                await send({"type": "lifespan.startup.complete"})
            elif msg["type"] == "lifespan.shutdown":
                await self.stop()
                await send({"type": "lifespan.shutdown.complete"})
                return

    async def start(self) -> None:
        if self.log_to_stderr and not LOG.handlers:
            h = logging.StreamHandler(sys.stderr)
            h.setFormatter(logging.Formatter("%(asctime)s llm-router %(levelname)s %(message)s"))
            LOG.addHandler(h)
        LOG.setLevel(logging.INFO)
        # trust_env=False — 운영자 셸의 http_proxy 를 물려받으면 사내 GPU 서버로 가는 호출이 프록시를 탄다(NO_PROXY 에 그 주소가 없을 수 있다).
        self._client = httpx.AsyncClient(trust_env=False, limits=_LIMITS, timeout=_proxy_timeout(self.cfg.connect_timeout_s))
        self._probe = httpx.AsyncClient(trust_env=False, limits=_LIMITS, timeout=_probe_timeout(self.cfg.connect_timeout_s))
        self._models_kick = asyncio.Event()
        self._reload(initial=True)
        await asyncio.gather(*(self._scrape(u) for u in self.ups))     # 첫 지표를 읽고서 손님을 받는다 — /health 가 처음부터 사실을 말한다
        await self._check_models()
        self._running = True
        for u in self.ups:
            self._start_loop(u, delay=True)
        self._tasks = [asyncio.create_task(self._watch_config()), asyncio.create_task(self._models_loop())]
        now = time.monotonic()
        LOG.info("기동 — 서버 %d곳(올라옴 %d) · 설정 %s", len(self.ups), sum(u.is_up(now) for u in self.ups), self.env_file)

    async def stop(self) -> None:
        self._running = False
        tasks = [*self._tasks, *self._loops.values()]
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._loops.clear()
        for c in (self._client, self._probe):
            if c is not None:
                await c.aclose()

    # ── 설정 다시 읽기 ──
    def _reload(self, *, initial: bool = False) -> None:
        sig = _file_sig(self.env_file)
        if not initial and sig == self._sig:
            return
        try:
            vals = read_env(self.env_file)
        except OSError as exc:
            # 못 읽은 것은 '모름' 이다 — 떠 있는 풀을 비우지 않는다(편집기의 바꿔치기 · 권한 실수 한 번에 모든 호출이 503 이 되지 않게).
            # 읽은 표시(_sig)를 옮기지 않아 다음 주기에 다시 해 본다(권한을 고쳐도 mtime 은 그대로다). 알림은 파일 모양마다 한 번.
            if initial or sig != self._bad_sig:
                LOG.warning("설정 파일을 읽지 못했다(%s: %s) — %s", self.env_file, type(exc).__name__,
                            "보낼 서버가 없다" if initial else "마지막으로 읽은 설정을 그대로 쓴다")
            self._bad_sig = sig
            return
        self._sig, self._bad_sig = sig, None
        self._mtime = round(sig[0] / 1e9, 3) if sig else None
        cfg = build_config(vals)
        # 다시 읽은 목록이 비었으면(줄을 지웠거나 쓸 수 있는 항목이 없다) 마지막 목록으로 계속 보낸다. 풀을 끄는 것은 update-all 이다 — 사본을
        # 직접 주소로 되돌리고 그 뒤에야 라우터를 내리는데, 재기동이 미뤄진 손님(심의가 도는 에이전트 서버 · 바쁜 HEAX)은 그동안 이 라우터를
        # 부른다. 빈 목록을 그대로 받으면 그 호출이 전부 503 이 된다. 처음 읽을 때 비었으면 그대로 503 이다(이어받을 목록이 없다).
        self.kept_last_list = not initial and not cfg.upstreams and bool(self.cfg.upstreams)
        if self.kept_last_list:
            cfg = replace(cfg, upstreams=self.cfg.upstreams)
        old = {u.url: u for u in self.ups}
        self.ups = [old.get(url) or Upstream(url) for url in cfg.upstreams]
        added = [u for u in self.ups if u.url not in old]
        removed = [u for u in old.values() if u.url not in cfg.upstreams]
        self.cfg = cfg
        for u in removed:
            t = self._loops.pop(u.url, None)
            if t is not None:
                t.cancel()
        if self._running:
            for u in added:
                self._start_loop(u, delay=False)
        for p in cfg.problems:
            LOG.warning("설정 — %s", p)
        if self.kept_last_list:       # 다시 읽기는 파일 모양이 바뀔 때만 돈다 — 이 경고도 파일 모양마다 한 번이다
            LOG.warning("LLM_UPSTREAMS 가 비었다(쓸 수 있는 항목 없음, %s) — update-all 이 라우터를 내릴 때까지 마지막 목록 %d곳으로 계속 보낸다",
                        self.env_file, len(self.ups))
        elif not cfg.upstreams:
            LOG.warning("LLM_UPSTREAMS 가 비어 있다(%s) — 보낼 서버가 없어 손님 요청은 503 이다", self.env_file)
        if not initial:
            LOG.info("설정 다시 읽음 — 서버 %d곳(더함 %d · 뺌 %d)", len(self.ups), len(added), len(removed))
            if (added or removed) and self._models_kick is not None:
                self._models_kick.set()

    async def _watch_config(self) -> None:
        while True:
            await asyncio.sleep(self.cfg.scrape_s)
            try:
                self._reload()
            except Exception:       # 루프가 조용히 죽으면 서버 목록이 영영 안 바뀐다 — 알리고 계속 돈다
                LOG.exception("설정 다시 읽기 실패")

    # ── 지표 ──
    def _start_loop(self, u: Upstream, *, delay: bool) -> None:
        old = self._loops.pop(u.url, None)
        if old is not None:
            old.cancel()
        self._loops[u.url] = asyncio.create_task(self._scrape_loop(u, delay))

    async def _scrape_loop(self, u: Upstream, delay: bool) -> None:
        if delay:
            await asyncio.sleep(self.cfg.scrape_s)
        while True:
            try:
                await self._scrape(u)
            except Exception:
                LOG.exception("지표 읽기 실패 %s", u.url)
            await asyncio.sleep(self.cfg.scrape_s)

    async def _scrape(self, u: Upstream) -> None:
        try:
            r = await self._probe.get(u.origin + "/metrics", timeout=_probe_timeout(self.cfg.connect_timeout_s))
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            self._mark_down(u, exc, request=False)
            return
        except httpx.HTTPError:
            metrics = None           # 닿기는 했다(읽기 실패 · 끊김) — 이번 주기는 지표 없음
        else:
            metrics = parse_metrics(r.text) if r.status_code == 200 else None    # 404 · 못 읽는 글 = 지표 없음
        now = time.monotonic()
        u.metrics, u.scraped_at, u.inflight_at_scrape = metrics, now, u.inflight
        if u.down_noted and u.is_up(now):
            u.down_noted = False
            LOG.info("서버 올라옴 %s — 지표가 다시 읽힌다", u.url)

    def _mark_down(self, u: Upstream, exc: Exception, *, request: bool) -> None:
        """연결 실패 — COOLDOWN_S 동안 뺀다. 지표 연결이 실패할 때마다 다시 늘어나므로 죽은 서버는 계속 빠져 있고, 지표가 다시 읽히기
        시작하면 빼 둔 시간이 지난 뒤 돌아온다('올라옴' 은 그 뒤 첫 지표에서 알린다). connect_fail 은 손님 요청의 연결 실패만 센다."""
        if request:
            u.connect_fail += 1
        u.down_until = time.monotonic() + self.cfg.cooldown_s
        if not u.down_noted:
            u.down_noted = True
            LOG.warning("서버 내려감 %s — %s 연결 실패(%s) · %g초 동안 뺀다(지표 연결이 실패하는 동안은 계속)", u.url,
                        "요청" if request else "지표", type(exc).__name__, self.cfg.cooldown_s)

    # ── 모델 대조 ──
    async def _models_loop(self) -> None:
        while True:
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self._models_kick.wait(), MODELS_EVERY_S)
            self._models_kick.clear()
            try:
                await self._check_models()
            except Exception:
                LOG.exception("모델 대조 실패")

    async def _check_models(self) -> None:
        ups = list(self.ups)
        hdrs = {"Authorization": f"Bearer {self.cfg.api_key}"} if self.cfg.api_key else {}
        res = await asyncio.gather(*(self._probe.get(u.origin + "/v1/models", headers=hdrs,
                                                     timeout=_probe_timeout(self.cfg.connect_timeout_s)) for u in ups),
                                   return_exceptions=True)
        for u, r in zip(ups, res, strict=True):
            if isinstance(r, BaseException) or r.status_code != 200:
                continue                 # 못 읽은 서버는 마지막으로 읽은 것을 그대로 둔다(다음 대조에서 다시)
            try:
                data = [d for d in r.json()["data"] if isinstance(d, dict) and "id" in d]
            except (ValueError, KeyError, TypeError):
                continue
            u.models = (frozenset(str(d["id"]) for d in data),
                        tuple(sorted((str(d["id"]), d.get("max_model_len")) for d in data)))
        summary = self._models_summary()
        sig = json.dumps(summary, sort_keys=True, ensure_ascii=False)
        if summary["match"] is False and sig != self._models_warned:
            self._models_warned = sig
            LOG.warning("모델 어긋남 — 서버마다 모델 id 또는 max_model_len 이 다르다(같은 모델·같은 창이어야 한다, LP-D6): ids=%s max_model_len=%s",
                        json.dumps(summary["ids"], ensure_ascii=False), json.dumps(summary["max_model_len"]))
        elif summary["match"] is True and self._models_warned is not None:
            self._models_warned = None
            LOG.info("모델 같아짐 — ids=%s max_model_len=%s", json.dumps(summary["ids"], ensure_ascii=False), summary["max_model_len"])

    def _models_summary(self) -> dict:
        known = [(u.url, u.models) for u in self.ups if u.models is not None]
        if not known:
            return {"match": None, "ids": [], "max_model_len": None}
        first = known[0][1]
        if all(m == first for _, m in known):
            lens = dict(first[1])
            vals = set(map(str, lens.values()))
            return {"match": True, "ids": sorted(first[0]),
                    "max_model_len": next(iter(lens.values())) if len(vals) == 1 else lens}
        return {"match": False, "ids": {url: sorted(m[0]) for url, m in known},
                "max_model_len": {url: dict(m[1]) for url, m in known}}

    # ── 라우터 자신의 끝점 ──
    def health(self) -> tuple[dict, int]:
        """status 는 올라온 서버 수와 모델 대조로만 정한다(down 이면 503). kept_last_list 는 status 를 바꾸지 않는다 — 보내는 데는 문제가 없고,
        파일의 목록과 쓰는 목록이 다르다는 사실만 알린다(update-all 이 라우터를 내릴 차례인지 보는 데 쓴다)."""
        now = time.monotonic()
        total, up = len(self.ups), sum(u.is_up(now) for u in self.ups)
        models = self._models_summary()
        status = "down" if up == 0 else "degraded" if (up < total or models["match"] is False) else "ok"
        return ({"status": status, "upstreams_total": total, "upstreams_up": up, "inflight": self.inflight, "models": models,
                 "config_mtime": self._mtime, "kept_last_list": self.kept_last_list}, 503 if status == "down" else 200)

    def stats(self) -> list[dict]:
        now = time.monotonic()
        out = []
        for u in self.ups:
            m = u.metrics or {}
            out.append({"url": u.url, "up": u.is_up(now), "running": m.get("running"), "waiting": m.get("waiting"), "kv": m.get("kv"),
                        "scrape_age_s": None if u.scraped_at is None else round(now - u.scraped_at, 3), "inflight": u.inflight,
                        "sent": u.sent, "connect_fail": u.connect_fail, "retried_away": u.retried_away, "sticky": u.sticky,
                        "overflow": u.overflow})
        return out

    async def _own(self, scope, send) -> None:
        if scope["method"] not in ("GET", "HEAD"):
            await _send_json(send, 405, {"error": {"message": "GET 만 받는다", "type": "method_not_allowed", "code": 405}})
            return
        body, code = self.health() if scope["path"] == "/health" else (self.stats(), 200)
        await _send_json(send, code, body, head=scope["method"] == "HEAD")

    # ── 넘기기 ──
    def _choose(self, key: bytes | None, tried: list[Upstream]) -> tuple[Upstream, str, Upstream | None] | None:
        now = time.monotonic()
        rest = [u for u in self.ups if u not in tried]
        cands = [u for u in rest if u.is_up(now)] or rest     # 모두 빠졌으면 전부를 다시 시도해 본다(멀쩡해졌을 수 있다)
        if not cands:
            return None
        best = min(cands, key=lambda u: (u.load(), u.kv(), self.ups.index(u)))
        if key is None:
            return best, "least", None
        pref = max(cands, key=lambda u: _rank(key, u.url))
        if pref is best or pref.load() - best.load() < self.cfg.sticky_slack:
            return pref, "sticky", pref
        return best, "overflow", pref

    async def _key(self, body: bytes) -> bytes | None:
        n = self.cfg.prefix_chars
        if n <= 0:
            return None
        if len(body) > BIG_BODY:
            return await asyncio.to_thread(sticky_key, body, n)
        return sticky_key(body, n)

    async def _proxy(self, scope, receive, send) -> None:
        self.inflight += 1
        try:
            chunks = []
            while True:
                msg = await receive()
                if msg["type"] == "http.disconnect":
                    return                          # 올리는 중에 떠났다 — 위로 보낸 것이 없다
                chunks.append(msg.get("body", b""))
                if not msg.get("more_body"):
                    break
            body = b"".join(chunks)
            key = await self._key(body)
            work = asyncio.create_task(self._forward(scope, body, key, send))
            gone = asyncio.create_task(_until_disconnect(receive))
            try:
                await asyncio.wait((work, gone), return_when=asyncio.FIRST_COMPLETED)
            except asyncio.CancelledError:
                work.cancel()
                gone.cancel()
                await asyncio.gather(work, gone, return_exceptions=True)
                raise
            if work.done():
                gone.cancel()
                await asyncio.gather(gone, return_exceptions=True)
                work.result()                       # 뜻밖의 예외는 서버에 올린다(기록 · 500)
                return
            # 손님이 먼저 떠났다 — 일을 취소하면 위 연결이 닫히고(머리 전이든 흐르는 중이든) vLLM 이 생성을 멈춘다.
            work.cancel()
            await asyncio.gather(work, return_exceptions=True)
        finally:
            self.inflight -= 1

    async def _forward(self, scope, body: bytes, key: bytes | None, send) -> None:
        target = (scope.get("raw_path") or scope["path"].encode()).decode("latin-1")
        if scope.get("query_string"):
            target += "?" + scope["query_string"].decode("latin-1")
        headers = _filter_headers(scope["headers"], _REQ_DROP)     # Authorization 은 손님 것 그대로(없으면 없는 채로 — LP-D9)
        tried: list[Upstream] = []
        failed: Upstream | None = None
        while (pick := self._choose(key, tried)) is not None:
            u, how, pref = pick
            if failed is not None:
                failed.retried_away += 1
            tried.append(u)
            req = self._client.build_request(scope["method"], u.origin + target, headers=headers, content=body,
                                             timeout=_proxy_timeout(self.cfg.connect_timeout_s))
            # 세는 것은 보낼 때다 — 머리를 받을 때 세면 몇 시간 붙든 생성이 /stats 에 안 보인다. 연결이 안 되면 되돌린다.
            u.inflight += 1
            u.sent += 1
            _count_pick(how, u, pref, +1)
            try:
                try:
                    resp = await self._client.send(req, stream=True)
                except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
                    u.sent -= 1                                # 요청이 서버에 닿지 않았다 — 되돌리고 다음 서버로
                    _count_pick(how, u, pref, -1)
                    self._mark_down(u, exc, request=True)
                    failed = u
                    continue
                except httpx.HTTPError as exc:
                    # 연결은 됐다 — 닿았을 수 있으니 다시 보내지 않는다(LP-D3)
                    LOG.warning("응답 머리 전에 끊김 %s — %s · 다시 보내지 않는다", u.url, type(exc).__name__)
                    await _send_json(send, 502, _error(f"LLM 라우터: 위 서버가 응답 머리를 보내기 전에 끊겼다({type(exc).__name__}) — "
                                                       "다시 보내지 않는다(생성이 시작됐을 수 있다)", "llm_router_upstream_broken", 502))
                    return
                await self._relay(resp, send, u)
                return
            finally:
                u.inflight -= 1
        if not self.ups:
            await _send_json(send, 503, _error(f"LLM 라우터: LLM_UPSTREAMS 가 비어 있다({self.env_file}) — 보낼 서버가 없다",
                                               "llm_router_no_upstreams", 503))
            return
        now = time.monotonic()
        if now - self._all_failed_noted >= max(self.cfg.cooldown_s, 1.0):     # 장애 동안 요청마다 찍지 않는다
            self._all_failed_noted = now
            LOG.warning("모든 서버 연결 실패 — %d곳 · 손님에게 502", len(tried))
        await _send_json(send, 502, _error(f"LLM 라우터: 서버 {len(tried)}곳에 모두 연결하지 못했다", "llm_router_upstream_unreachable", 502))

    async def _relay(self, resp: httpx.Response, send, u: Upstream) -> None:
        broken: Exception | None = None
        try:
            await send({"type": "http.response.start", "status": resp.status_code,
                        "headers": _filter_headers(resp.headers.raw, _RESP_DROP)})
            async for chunk in resp.aiter_raw():       # 받은 바이트 그대로(압축도 풀지 않는다) — 오는 대로 흘린다
                if chunk:
                    await send({"type": "http.response.body", "body": chunk, "more_body": True})
        except httpx.HTTPError as exc:
            broken = exc
        finally:
            await resp.aclose()                        # 다 읽었든 끊겼든 취소됐든 위 연결을 닫는다
        if broken is not None:
            # 생성 중 끊김은 손님에게도 끊김으로 보인다 — 끝맺지 않고 돌아가면 서버가 연결을 닫는다(정상 끝처럼 보이면 잘린 답을 믿는다).
            LOG.warning("생성 중 끊김 %s — %s · 손님 연결도 끊는다(다시 보내지 않는다)", u.url, type(broken).__name__)
            return
        await send({"type": "http.response.body", "body": b"", "more_body": False})


# ── 도움 ───────────────────────────────────────────────────────────────────────────────────────────
async def _until_disconnect(receive) -> None:
    """본문을 다 받은 뒤의 receive() 는 손님이 끊을 때(또는 응답을 다 보낸 뒤) http.disconnect 를 준다 — ASGI 규약이라 서버 판에 기대지 않는다.
    uvicorn 은 끊긴 뒤의 send() 를 조용히 버리므로, 보내기만 해서는 끊김을 모른 채 위 생성을 끝까지 기다린다."""
    while True:
        if (await receive())["type"] == "http.disconnect":
            return
        await asyncio.sleep(0.05)       # 규약을 어기고 곧바로 돌아오는 서버에서 헛돌지 않게


def _count_pick(how: str, u: Upstream, pref: Upstream | None, d: int) -> None:
    """붙임 셈 — sticky 는 선호 서버로 간 요청(그 서버에), overflow 는 선호 서버가 바빠 다른 서버로 간 요청(선호 서버에)."""
    if how == "sticky":
        u.sticky += d
    elif how == "overflow":
        pref.overflow += d


def _filter_headers(raw, drop: frozenset[bytes]) -> list[tuple[bytes, bytes]]:
    named = {t.strip().lower() for k, v in raw if k.lower() == b"connection" for t in v.split(b",")}   # Connection 이 가리킨 홉 헤더도
    return [(k.lower(), v) for k, v in raw if k.lower() not in drop and k.lower() not in named]


def _error(message: str, kind: str, code: int) -> dict:
    return {"error": {"message": message, "type": kind, "code": code}}


async def _send_json(send, status: int, obj, *, head: bool = False) -> None:
    data = json.dumps(obj, ensure_ascii=False).encode()
    await send({"type": "http.response.start", "status": status,
                "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(data)).encode())]})
    await send({"type": "http.response.body", "body": b"" if head else data})


def make_app(env_file: Path | str | None = None, *, log_to_stderr: bool = False) -> Router:
    return Router(Path(env_file or os.environ.get("LLM_ROUTER_ENV_FILE") or DEFAULT_ENV_FILE), log_to_stderr=log_to_stderr)


app = make_app(log_to_stderr=True)
