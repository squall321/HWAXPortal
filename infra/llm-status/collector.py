#!/usr/bin/env python3
# LLM 서버 · 에이전트 서버 · 라우터의 상태를 15초마다 읽어 sqlite 에 쌓고 루프백 HTTP(/health · /snapshot · /series)로 내는 호스트 수집기(docs/ops-dashboard)
"""LLM/GPU 현황 수집기 — docs/ops-dashboard PLAN §3 · context-notes OD-2 ~ OD-4 · 절차 docs/ops-dashboard/server-setup.md.

    python3 infra/llm-status/collector.py serve [--port 8760]     # infra/scripts/llm-status.sh run 이 띄운다(services.yaml llm-status)
    python3 infra/llm-status/collector.py once                    # 한 번 읽어 스냅숏을 찍는다(저장하지 않는다 — 켜기 전에 손으로 본다)

설정 — 리포 루트의 infra/.env 를 **직접** 읽는다(파일 위치에서 유도). 키는 argv · 환경으로 받지 않는다(라우터 규칙 LP-D11). 읽는 규칙은
update-all `_envfile_value` 와 같다. 주기마다 파일이 바뀌었는지 보고 바뀌었으면 다시 읽는다(재기동 없음 — 지문에 infra/.env 가 없다).
  LLM_STATUS_TARGETS        `이름=<주소>/v1` 를 쉼표로. 없으면 LLM_UPSTREAMS(GLM-1 · GLM-2 …), 그것도 없으면 LLM_BASE_URL(GLM),
                            그리고 CHAT_LLM_BASE_URL(챗 LLM). 이름은 영숫자 · . _ - 40자까지(그래프 주소에 쓴다).
  LLM_STATUS_REPLICA_PORTS  챗 LLM 복제본의 포트(예 `18711-18720`) — 호스트 · 스킴은 CHAT_LLM_BASE_URL 의 것이다.
  LLM_STATUS_REPLICA_MAP    포트 → 노드 짝 파일(줄마다 `<포트> <노드>` 또는 JSON {포트: 노드}). 진짜 자리 · 꼴은 받은 편지함 Q7 의 답이다.
  LLM_STATUS_AGENT_URL      에이전트 서버(기본 http://127.0.0.1:9009). 라우터는 LLM_UPSTREAMS 가 있을 때만 127.0.0.1:LLM_ROUTER_PORT 를 본다.
  키 — /v1/models 에만 싣는다. CHAT_LLM_BASE_URL 과 같은 호스트:포트와 복제본은 CHAT_LLM_API_KEY, 나머지는 LLM_API_KEY. /health ·
       /version · /metrics 는 키를 묻지 않는다(vLLM — OD-2). 키는 로그 · 답 · 자식 프로세스 어디에도 싣지 않는다(답을 내기 전에 한 번 더 가린다).
읽기 — 대상마다 따로 돈다(스레드 하나). 연결 3초 · 읽기 5초 — 한 대가 걸려도 다른 대상은 제 주기에 읽는다. 앞 읽기가 안 끝난 대상은 그 주기를
  건너뛴다(값이 낡음으로 보인다). 15초마다 /health · /version · /metrics, 60초마다 /v1/models.
값 — 모두 {value, at, source, error, stale, age_s} 다. at 은 마지막으로 제대로 읽은 때, error 는 마지막 시도가 실패한 까닭(또는 값이 없는 까닭).
  주기 세 번을 놓치면 stale. 설정된 대상은 숨기지 않는다 — 못 읽으면 `모름 — <까닭>` 이다. 주소는 호스트:포트만 낸다.
속도 · 분위수 — 카운터는 이웃한 표본의 차로 잰다. 줄어든 쌍(서버 재기동)은 빈칸이다(음수 속도 없음). p50 · p95 는 히스토그램 칸의 증가로 셈한
  어림(5분 창)이다 — 답에 approx 표지가 붙는다.
저장 — infra/.state/llm-status/(폴더 700 · 파일 600)의 sqlite. 표본 48시간 · 5분 접기 35일(samplestore.py).
Slurm · GPU — 아직 원천이 없다(M3 · M4). 자리만 있고 `모름 — <무엇이 필요한가>` 를 낸다.
표준 라이브러리만 쓴다(시스템 python3 3.10 이상).
"""
import argparse
import contextlib
import fcntl
import http.client
import http.server
import json
import math
import os
import re
import signal
import socket
import ssl
import sys
import threading
import time
import urllib.parse
from collections import deque
from pathlib import Path
from typing import NamedTuple

HERE = Path(__file__).resolve().parent
if not sys.path or sys.path[0] != str(HERE):      # 곁 모듈(promtext · samplestore)을 이 폴더에서 — 같은 이름의 남의 모듈이 가리지 않게
    sys.path.insert(0, str(HERE))
import promtext  # noqa: E402
from samplestore import RANGES, Store  # noqa: E402

ROOT = HERE.parents[1]                       # infra/llm-status/collector.py → 리포 루트(dev ~/claude · cae00 ~/Projects)
DEFAULT_ENV_FILE = ROOT / "infra" / ".env"
DEFAULT_STATE_DIR = ROOT / "infra" / ".state" / "llm-status"
DB_NAME = "llm-status.sqlite"
DEFAULT_PORT = 8760
DEFAULT_AGENT_URL = "http://127.0.0.1:9009"
DEFAULT_ROUTER_PORT = 8730

INTERVAL_S = 15.0
MODELS_EVERY_S = 60.0
CONNECT_S = 3.0
READ_S = 5.0
STALE_AFTER = 3                  # 놓친 주기 수
RATE_WINDOW_S = 60.0             # 카드의 토큰 속도 창
WINDOW_S = 300.0                 # 분위수 · 오류 · 선점 · 캐시 적중의 창
MAX_BODY = 16 << 20              # /metrics 한 번의 상한
MAX_JSON = 2 << 20               # JSON 답 한 번의 상한
TARGET_MAX = 32
REPLICA_MAX = 64
MAP_MAX_BYTES = 1 << 20
KEY_MIN = 8                      # 이보다 짧은 키는 가리기 대상으로 치지 않는다(낱말을 지운다)
VERSION = 1

# 저장하는 지표 — 대상 종류마다. 나머지는 지금 값만 낸다.
STORE_MAIN = ("up", "running", "waiting", "kv", "prompt_tps", "gen_tps", "ttft_p50", "ttft_p95", "e2e_p50", "e2e_p95", "queue_p95",
              "errors_per_min", "preempt_per_min", "prefix_hit")
STORE_REPLICA = ("up", "running", "waiting", "kv", "gen_tps", "ttft_p95")
STORE_AGENT = ("up", "delib_active", "delib_queued", "delib_seats_running", "routine_active", "review_active", "chat_active")
STORE_ROUTER = ("up", "inflight")
APPROX = frozenset({"ttft_p50", "ttft_p95", "e2e_p50", "e2e_p95", "queue_p50", "queue_p95"})
# 화면이 늘 받는 칸(못 읽었으면 '모름' 으로라도) — 대상을 숨기지 않는 약속
VLLM_VALUES = {"up": "health", "version": "version", "models": "models", "context": "models", "running": "metrics",
               "waiting": "metrics", "kv": "metrics", "prompt_tps": "metrics", "gen_tps": "metrics", "ttft_p50": "metrics",
               "ttft_p95": "metrics", "e2e_p50": "metrics", "e2e_p95": "metrics", "queue_p50": "metrics", "queue_p95": "metrics",
               "requests_per_min": "metrics", "errors_per_min": "metrics", "aborts_per_min": "metrics", "preempt_per_min": "metrics",
               "prefix_hit": "metrics"}
AGENT_VALUES = ("up", "delib_active", "delib_queued", "delib_seats_running", "delib_paused", "routine_active", "routine_parked",
                "routine_max", "review_active", "card_review", "chat_active", "chat", "chat_llm", "context_tokens", "model")
ROUTER_VALUES = ("up", "status", "inflight", "upstreams_up", "upstreams_total", "models_match", "upstreams")
SOURCES = ("health", "version", "metrics", "models")

# M3 · M4 자리 — 원천이 생기면 같은 꼴(poll · view)의 것으로 갈아 끼운다(docs/ops-dashboard PLAN §3.4).
SLURM_WHY = ("모름 — stcx(356대) GPU 잡 표는 cae00 에서 사람 없이 `ssh stcx` 가 되는지가 먼저다(받은 편지함 2026-11-02 Q8). "
             "되면 60초마다 ssh 한 번(BatchMode · 정해진 읽기 명령)으로 squeue 를 읽는다(M3)")
GPU_WHY = ("모름 — GPU 사용률 · 메모리 · 온도 · 전력을 읽는 길이 아직 없다. stcx 노드는 노드 관리자(Q11), GLM 서버는 그 운영 팀(Q12)의 "
           "승인이 먼저다(M4)")


_LOG = {"stream": sys.stdout}            # once 는 표준 오류로 — 표준 출력은 스냅숏 JSON 이다


def log(msg: str) -> None:
    print(f"[llm-status] {time.strftime('%Y-%m-%dT%H:%M:%S%z')} {_REDACT.apply(msg)}", file=_LOG["stream"], flush=True)


# ── infra/.env — update-all `_envfile_value` · 라우터 env_values 와 같은 규칙 ────────────────────────────────
_WS = " \t\n\v\f\r"
_ENV_LINE = re.compile(r"^[ \t\v\f\r]*(?:export[ \t\v\f\r]+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$")
_INLINE_COMMENT = re.compile(r"[ \t\v\f\r]+#.*$")


def env_values(text: str) -> dict[str, str]:
    """infra/.env 글 → {키: 값}. 마지막 줄이 이기고 빈 값은 없는 것이다. 줄은 개행으로만 나누고, 공백 뒤 `#` 이후를 벗긴 **뒤에** 양끝
    ASCII 공백 · CR · NUL · 따옴표 문자를 지운다(라우터 env_values 와 같다)."""
    vals: dict[str, str] = {}
    for ln in text.split("\n"):
        m = _ENV_LINE.match(ln)
        if m:
            v = _INLINE_COMMENT.sub("", m.group(2)).strip(_WS)
            vals[m.group(1)] = v.replace("\r", "").replace("\x00", "").replace('"', "").replace("'", "")
    return {k: v for k, v in vals.items() if v}


class _Redact:
    """키 값을 글에서 가린다 — 로그 · 답을 내기 직전 마지막 그물(키가 오류 글에 섞여 돌아와도 나가지 않게)."""

    def __init__(self) -> None:
        self.secrets: tuple[str, ...] = ()

    def set(self, keys) -> None:
        self.secrets = tuple(sorted({k for k in keys if k and len(k) >= KEY_MIN}, key=len, reverse=True))

    def apply(self, text: str) -> str:
        for s in self.secrets:
            if s in text:
                text = text.replace(s, "<가림>")
        return text


_REDACT = _Redact()
_URL_IN_TEXT = re.compile(r"\b[A-Za-z][A-Za-z0-9+.-]{0,15}://[^\s'\"<>()\[\]]+")
_BEARER = re.compile(r"(?i)\bbearer\s+[^\s'\"]+")


def scrub(text, limit: int = 300) -> str | None:
    """원격에서 받은 글(오류 문구 등) — 주소는 호스트:포트로 줄이고(계정 · 경로 · 질의를 버린다) Bearer 값과 설정의 키는 가린다(받는 자리에서 한 번,
    답 · 로그를 내기 직전에 한 번 더 — dumps · log)."""
    if text is None:
        return None
    s = str(text)

    def _host(m: "re.Match[str]") -> str:
        try:
            u = urllib.parse.urlsplit(m.group(0))
            return (u.hostname or "?") + (f":{u.port}" if u.port else "")
        except ValueError:
            return "?"
    s = _REDACT.apply(_BEARER.sub("Bearer <가림>", _URL_IN_TEXT.sub(_host, s)))
    return s[:limit]


# ── 설정 ───────────────────────────────────────────────────────────────────────────────────────────
_SPLIT = re.compile(r"[ \t\n\v\f\r,]+")
_V1 = re.compile(r"(https?)://([A-Za-z0-9.-]+)(?::([0-9]{1,5}))?/v1/?")
_BASE = re.compile(r"(https?)://([A-Za-z0-9.-]+)(?::([0-9]{1,5}))?/?")
_HOST = re.compile(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)*")
_QUAD = re.compile(r"(0|[1-9][0-9]{0,2})\.(0|[1-9][0-9]{0,2})\.(0|[1-9][0-9]{0,2})\.(0|[1-9][0-9]{0,2})")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,39}")
_NODE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")


class Addr(NamedTuple):
    scheme: str
    host: str
    port: int

    def __str__(self) -> str:
        return f"{self.host}:{self.port}"


class Target(NamedTuple):
    id: str
    label: str
    addr: Addr | None
    key: str | None          # "llm" · "chat" · None — /v1/models 에 실을 키
    group: str | None        # 복제본이면 묶음 id
    origin: str              # targets · upstreams · base · chat · replica
    problem: str | None      # 설정이 틀려 읽지 않는다 — 그래도 '모름 — 까닭' 으로 남긴다
    node: str | None = None  # 복제본의 노드(짝 파일)


class Config(NamedTuple):
    targets: tuple[Target, ...]
    agent: Addr | None
    agent_problem: str | None
    router: Addr | None
    keys: dict
    problems: tuple[str, ...]
    enabled: bool             # infra/.env 에 LLM_STATUS 가 있나(꺼진 박스에서 손으로 띄운 것을 화면이 알게)


def _label_of(tok: str) -> str:
    """사유에 적을 호스트만(못 알아보면 ?) — 칸 원문은 적지 않는다(질의 · 계정에 키가 들 수 있다). 라우터 _ups_label 에서 스킴을 뺀 꼴이다
    (답에는 주소를 호스트:포트로만 싣는다)."""
    host = "?"
    if "://" in tok:
        rest = tok.split("://", 1)[1]
        rest = re.split(r"[/?#]", rest, maxsplit=1)[0].rsplit("@", 1)[-1]
        rest = re.sub(r":[0-9]*\Z", "", rest)
        if re.fullmatch(r"[A-Za-z0-9.-]{1,253}", rest):
            host = rest
    return host


def parse_addr(tok: str, *, v1: bool) -> tuple[Addr | None, str | None]:
    """주소 하나 → (Addr, None) 또는 (None, 까닭). v1 이면 경로가 정확히 /v1 이어야 한다(vLLM 의 OpenAI 꼴 — 라우터와 같은 규칙)."""
    m = (_V1 if v1 else _BASE).fullmatch(tok)
    if m is None:
        if "@" in tok:
            return None, "계정(user@)이 있다"
        if "?" in tok or "#" in tok:
            return None, "질의 · 조각(? #)이 있다"
        if "[" in tok:
            return None, "IPv6 는 받지 않는다"
        if not tok.startswith(("http://", "https://")):
            return None, "스킴이 소문자 http · https 가 아니다"
        return None, "쓸 수 있는 주소가 아니다(호스트 글자 · 포트 · 경로가 " + ("정확히 /v1 인지)" if v1 else "없는지)")
    scheme, host, port = m.group(1), m.group(2).lower(), m.group(3)
    if re.fullmatch(r"[0-9.]+", host):
        q = _QUAD.fullmatch(host)
        if q is None or any(int(x) > 255 for x in q.groups()):
            return None, "IPv4 가 아니다(점 넷 · 칸마다 0~255)"
    elif not _HOST.fullmatch(host):
        return None, "호스트 이름이 틀렸다"
    n = int(port) if port else (443 if scheme == "https" else 80)
    if not 1 <= n <= 65535:
        return None, "포트가 1~65535 밖이다"
    return Addr(scheme, host, n), None


def _ports(raw: str) -> tuple[list[int], str | None]:
    """`18711-18720,18725` → 포트들. 틀리면 ([], 까닭)."""
    out: list[int] = []
    for part in (p for p in _SPLIT.split(raw) if p):
        m = re.fullmatch(r"([0-9]{1,5})(?:-([0-9]{1,5}))?", part)
        if not m:
            return [], f"LLM_STATUS_REPLICA_PORTS 의 '{part[:20]}' 는 포트(또는 포트-포트)가 아니다"
        a, b = int(m.group(1)), int(m.group(2) or m.group(1))
        if not (1 <= a <= 65535 and 1 <= b <= 65535 and a <= b):
            return [], "LLM_STATUS_REPLICA_PORTS 의 포트가 1~65535 밖이거나 범위가 거꾸로다"
        if b - a + 1 + len(out) > REPLICA_MAX:
            return [], f"LLM_STATUS_REPLICA_PORTS 가 {REPLICA_MAX}개를 넘는다"
        out.extend(p for p in range(a, b + 1) if p not in out)
    return out, None


def _resolve_path(raw: str) -> Path:
    p = Path(os.path.expanduser(raw))
    return p if p.is_absolute() else ROOT / p


def read_replica_map(raw: str) -> tuple[dict[int, str], str | None]:
    """포트 → 노드 짝 파일(LLM_STATUS_REPLICA_MAP). 진짜 파일의 자리 · 꼴은 받은 편지함 2026-11-02 Q7 의 답이다 — 그 답이 오면 여기를 맞춘다.
    지금 받는 꼴 — JSON {"18711": "노드", …} · [{"port": 18711, "node": "노드"}, …], 또는 줄마다 `<포트> <노드>`(사이는 공백 · = · : · ,
    중 하나, 순서는 바뀌어도 된다, # 뒤는 설명). 노드 이름 꼴이 아닌 칸은 버린다."""
    path = _resolve_path(raw)
    try:
        with open(path, "rb") as f:
            data = f.read(MAP_MAX_BYTES + 1)
    except OSError as exc:
        return {}, f"짝 파일(LLM_STATUS_REPLICA_MAP)을 읽지 못했다 — {type(exc).__name__}"
    if len(data) > MAP_MAX_BYTES:
        return {}, "짝 파일이 1 MiB 를 넘는다"
    text = data.decode("utf-8", errors="replace")
    out: dict[int, str] = {}

    def put(port, node) -> None:
        try:
            p = int(str(port).strip())
        except ValueError:
            return
        n = str(node or "").strip()
        if 1 <= p <= 65535 and _NODE.fullmatch(n):
            out[p] = n
    try:
        obj = json.loads(text)
    except (ValueError, RecursionError):
        obj = None
    if isinstance(obj, dict):
        for k, v in obj.items():
            put(k, v)
    elif isinstance(obj, list):
        for row in obj:
            if isinstance(row, dict):
                put(row.get("port"), row.get("node") or row.get("host") or row.get("name"))
    else:
        for ln in text.split("\n"):
            toks = [t for t in re.split(r"[\s=:,]+", ln.split("#", 1)[0].strip()) if t]
            if len(toks) < 2:
                continue
            if re.fullmatch(r"[0-9]{1,5}", toks[0]):
                put(toks[0], toks[1])
            elif re.fullmatch(r"[0-9]{1,5}", toks[1]):
                put(toks[1], toks[0])
    if not out:
        return {}, "짝 파일에서 포트 · 노드 짝을 하나도 읽지 못했다(꼴은 docs/ops-dashboard/server-setup.md)"
    return out, None


def build_config(vals: dict[str, str]) -> Config:
    """infra/.env 값 → 설정. 틀린 칸도 대상으로 남긴다(problem) — 화면이 '모름 — 까닭' 으로 보인다."""
    problems: list[str] = []
    rows: list[Target] = []
    chat, chat_why = (parse_addr(vals["CHAT_LLM_BASE_URL"], v1=True) if vals.get("CHAT_LLM_BASE_URL") else (None, None))

    def key_for(a: Addr | None) -> str:
        return "chat" if a is not None and chat is not None and a == chat else "llm"

    if vals.get("LLM_STATUS_TARGETS"):
        for n, tok in enumerate((t for t in _SPLIT.split(vals["LLM_STATUS_TARGETS"]) if t), 1):
            label, sep, url = tok.partition("=")
            if not sep or not url:
                rows.append(Target(f"item-{n}", f"칸 {n}", None, None, None, "targets",
                                   f"LLM_STATUS_TARGETS 의 칸 {n} 이 `이름=주소/v1` 꼴이 아니다"))
            elif not _ID.fullmatch(label):
                rows.append(Target(f"item-{n}", f"칸 {n}", None, None, None, "targets",
                                   f"LLM_STATUS_TARGETS 의 칸 {n} 이름은 영숫자 · . _ - 로 40자까지다"))
            else:
                a, why = parse_addr(url, v1=True)
                rows.append(Target(label, label, a, key_for(a), None, "targets",
                                   None if why is None else f"LLM_STATUS_TARGETS 의 {label} — {_label_of(url)} {why}"))
    else:
        ups = [t for t in _SPLIT.split(vals.get("LLM_UPSTREAMS", "")) if t]
        if ups:
            for n, tok in enumerate(ups, 1):
                a, why = parse_addr(tok.rstrip("/"), v1=True)
                rows.append(Target(f"glm-{n}", f"GLM-{n}", a, "llm", None, "upstreams",
                                   None if why is None else f"LLM_UPSTREAMS 의 칸 {n} — {_label_of(tok)} {why}"))
        elif vals.get("LLM_BASE_URL"):
            a, why = parse_addr(vals["LLM_BASE_URL"].rstrip("/"), v1=True)
            rows.append(Target("glm", "GLM", a, "llm", None, "base",
                               None if why is None else f"LLM_BASE_URL — {_label_of(vals['LLM_BASE_URL'])} {why}"))
        if vals.get("CHAT_LLM_BASE_URL"):
            rows.append(Target("chat", "챗 LLM", chat, "chat", None, "chat",
                               None if chat_why is None else f"CHAT_LLM_BASE_URL — {_label_of(vals['CHAT_LLM_BASE_URL'])} {chat_why}"))
    chat_id = next((t.id for t in rows if chat is not None and t.addr == chat and t.problem is None), "chat")
    rp = vals.get("LLM_STATUS_REPLICA_PORTS")
    rm = vals.get("LLM_STATUS_REPLICA_MAP")
    if rp or rm:
        nodes, map_why = read_replica_map(rm) if rm else ({}, None)
        ports, ports_why = _ports(rp) if rp else (sorted(nodes), None)
        if map_why:
            problems.append(map_why)
        if chat is None:
            rows.append(Target(f"{chat_id}-replicas", "챗 LLM 복제본", None, "chat", chat_id, "replica",
                               "CHAT_LLM_BASE_URL 이 없거나 틀려 복제본의 호스트를 모른다"))
        elif ports_why:
            rows.append(Target(f"{chat_id}-replicas", "챗 LLM 복제본", None, "chat", chat_id, "replica", ports_why))
        else:
            for p in ports:
                rows.append(Target(f"{chat_id}-{p}", f":{p}", Addr(chat.scheme, chat.host, p), "chat", chat_id, "replica", None,
                                   nodes.get(p)))
    # 이름 · 주소가 겹치면 뒤의 것을 '모름' 으로 남긴다(같은 서버를 두 번 묻지 않는다)
    seen_id: set[str] = set()
    seen_addr: dict[Addr, str] = {}
    out: list[Target] = []
    for t in rows:
        why = t.problem
        if t.id in seen_id:
            t = t._replace(id=f"{t.id}-{len(out) + 1}")
            why = why or f"이름 {t.label} 이 겹친다"
        elif t.addr is not None and t.problem is None and t.addr in seen_addr:
            why = f"같은 서버({t.addr})를 이미 {seen_addr[t.addr]} 로 읽는다"
        if t.addr is not None and why is None:
            seen_addr[t.addr] = t.label
        seen_id.add(t.id)
        if len(out) >= TARGET_MAX and why is None:
            why = f"대상이 {TARGET_MAX}개를 넘어 읽지 않는다"
        out.append(t._replace(problem=why))
    agent, agent_why = parse_addr(vals.get("LLM_STATUS_AGENT_URL", DEFAULT_AGENT_URL).rstrip("/"), v1=False)
    router = None
    if vals.get("LLM_UPSTREAMS"):
        raw = vals.get("LLM_ROUTER_PORT", str(DEFAULT_ROUTER_PORT))
        if re.fullmatch(r"[0-9]{1,5}", raw) and 1 <= int(raw) <= 65535:
            router = Addr("http", "127.0.0.1", int(raw))
        else:
            problems.append("LLM_ROUTER_PORT 가 1~65535 의 수가 아니라 라우터를 보지 않는다")
    keys = {"llm": vals.get("LLM_API_KEY"), "chat": vals.get("CHAT_LLM_API_KEY")}
    return Config(tuple(out), agent, None if agent_why is None else f"LLM_STATUS_AGENT_URL — {agent_why}", router, keys,
                  tuple(problems), bool(vals.get("LLM_STATUS")))


# ── HTTP 읽기 ───────────────────────────────────────────────────────────────────────────────────────
class Resp(NamedTuple):
    status: int | None
    body: bytes
    error: str | None
    kind: str        # ok · http · refused · connect_timeout · dns · tls · connect · read_timeout · closed · too_big · other


UNREACHABLE = frozenset({"refused", "connect_timeout", "dns", "tls", "connect", "read_timeout"})
_SSL_CTX: ssl.SSLContext | None = None


def fetch(a: Addr, path: str, *, headers: dict | None = None, connect_s: float | None = None, read_s: float | None = None,
          max_bytes: int = MAX_BODY) -> Resp:
    """GET 한 번 — 연결 connect_s(기본 CONNECT_S) · 읽기 read_s(기본 READ_S — 머리부터 몸까지의 기한). 프록시를 타지 않는다(http.client 는
    환경의 프록시를 보지 않는다). 기본값은 부를 때 읽는다(시험이 줄여 쓴다)."""
    global _SSL_CTX
    connect_s = CONNECT_S if connect_s is None else connect_s
    read_s = READ_S if read_s is None else read_s
    if a.scheme == "https":
        _SSL_CTX = _SSL_CTX or ssl.create_default_context()
        conn = http.client.HTTPSConnection(a.host, a.port, timeout=connect_s, context=_SSL_CTX)
    else:
        conn = http.client.HTTPConnection(a.host, a.port, timeout=connect_s)
    try:
        try:
            conn.connect()
        except ConnectionRefusedError:
            return Resp(None, b"", "연결 거부 — 그 포트에 듣는 것이 없다", "refused")
        except socket.timeout:
            return Resp(None, b"", f"연결 시간 초과({connect_s:g}초)", "connect_timeout")
        except socket.gaierror:
            return Resp(None, b"", "호스트 이름을 풀지 못했다", "dns")
        except (ssl.SSLError, ssl.CertificateError) as exc:
            return Resp(None, b"", f"TLS 오류({type(exc).__name__})", "tls")
        except OSError as exc:
            return Resp(None, b"", f"닿지 못했다({type(exc).__name__})", "connect")
        deadline = time.monotonic() + read_s
        # 소켓을 따로 쥔다 — 서버가 닫는 답이면 getresponse() 가 conn.sock 을 비운다(몸은 그 소켓으로 계속 읽힌다)
        sock = conn.sock
        sock.settimeout(read_s)
        conn.request("GET", path, headers={"Accept": "*/*", "User-Agent": "hwax-llm-status/1", "Connection": "close",
                                           **(headers or {})})
        resp = conn.getresponse()
        chunks: list[bytes] = []
        size = 0
        while not resp.isclosed():          # 몸을 다 읽으면 응답이 소켓을 닫는다 — 그 뒤 settimeout 은 EBADF 다
            left = deadline - time.monotonic()
            if left <= 0:
                raise socket.timeout()
            sock.settimeout(left)
            chunk = resp.read(65536)
            if not chunk:
                break
            size += len(chunk)
            if size > max_bytes:
                return Resp(resp.status, b"", f"답이 너무 크다({max_bytes >> 20} MiB 넘음)", "too_big")
            chunks.append(chunk)
        body = b"".join(chunks)
        if resp.status != 200:
            return Resp(resp.status, body, f"HTTP {resp.status}", "http")
        return Resp(200, body, None, "ok")
    except socket.timeout:
        return Resp(None, b"", f"읽기 시간 초과({read_s:g}초) — 서버가 답하지 않는다", "read_timeout")
    except (http.client.RemoteDisconnected, http.client.IncompleteRead, ConnectionResetError, BrokenPipeError):
        return Resp(None, b"", "답 도중 연결이 끊겼다", "closed")
    except (http.client.HTTPException, OSError) as exc:
        return Resp(None, b"", f"읽지 못했다({type(exc).__name__})", "other")
    finally:
        conn.close()


def _json(r: Resp) -> object | None:
    if r.status not in (200, 503) or len(r.body) > MAX_JSON:
        return None
    try:
        return json.loads(r.body.decode("utf-8", errors="replace"))
    except (ValueError, RecursionError):
        return None


# ── 값 칸 ───────────────────────────────────────────────────────────────────────────────────────────
class Cell:
    """값 하나 — 마지막으로 제대로 읽은 값과 때, 마지막 시도의 실패(또는 값이 없는 까닭)."""
    __slots__ = ("value", "at", "error", "source", "every")

    def __init__(self, source: str, every: float):
        self.value, self.at, self.error, self.source, self.every = None, None, None, source, every

    def ok(self, value, now: float, note: str | None = None) -> None:
        self.value, self.at, self.error = value, now, note

    def fail(self, why: str) -> None:
        self.error = why

    def view(self, now: float) -> dict:
        stale = self.at is not None and now - self.at > STALE_AFTER * self.every
        err = self.error
        if self.at is None and err is None:
            err = "모름 — 아직 읽지 못했다(첫 읽기 중)"
        return {"value": self.value, "at": self.at, "source": self.source, "error": err, "stale": stale,
                "age_s": None if self.at is None else round(now - self.at, 1)}


def unknown(source: str, why: str) -> dict:
    return {"value": None, "at": None, "source": source, "error": why, "stale": False, "age_s": None}


class Snap(NamedTuple):
    """/metrics 한 번에서 증가분을 셀 것만."""
    ts: float
    counters: dict
    by_label: dict
    hists: dict


class TState:
    """대상 하나의 상태 — 값 칸 · 원천마다 마지막 읽기 · 최근 표본(창 셈)."""

    def __init__(self, t: Target, interval: float, models_every: float):
        self.t = t
        self.lock = threading.Lock()
        self.busy = False
        self.busy_since: float | None = None
        self.polls = self.skipped = 0
        self.interval, self.models_every = interval, models_every
        self.cells: dict[str, Cell] = {}
        self.src: dict[str, dict] = {}
        self.hist: deque = deque(maxlen=max(4, int(WINDOW_S / interval) + 2))
        self.models_try: float | None = None
        self.noted: dict[str, str | None] = {}     # 바뀔 때만 로그에 남기려고 — 원천 → 마지막으로 알린 상태

    def cell(self, name: str, source: str) -> Cell:
        c = self.cells.get(name)
        if c is None:
            c = self.cells[name] = Cell(source, self.models_every if source == "models" else self.interval)
        return c

    def mark(self, source: str, now: float, error: str | None) -> None:
        s = self.src.setdefault(source, {"at": None, "tried": None, "error": None})
        s["tried"] = now
        s["error"] = error
        if error is None:
            s["at"] = now

    def src_view(self, now: float) -> dict:
        out = {}
        for name, s in self.src.items():
            every = self.models_every if name == "models" else self.interval
            out[name] = {"at": s["at"], "tried": s["tried"], "error": s["error"],
                         "age_s": None if s["at"] is None else round(now - s["at"], 1),
                         "stale": s["at"] is None or now - s["at"] > STALE_AFTER * every}
            if "bad_lines" in s:                # 지표 글에서 읽지 못하고 버린 줄 수(판이 바뀌어 꼴이 달라졌는지 보는 실마리)
                out[name]["bad_lines"] = s["bad_lines"]
        return out


# ── 창 셈 ───────────────────────────────────────────────────────────────────────────────────────────
def _pairs(hist: deque, since: float, max_gap: float) -> list[tuple[Snap, Snap]]:
    """이웃한 표본 쌍 — 뒤 표본이 since 뒤이고 사이가 0 < 차 <= max_gap 인 것(서버가 오래 안 닿았던 사이는 평균으로 치지 않는다)."""
    xs = list(hist)
    return [(a, b) for a, b in zip(xs, xs[1:]) if b.ts > since and 0 < b.ts - a.ts <= max_gap]


def _rate(pairs, get, per: float) -> tuple[float | None, str | None]:
    """창 안 쌍마다의 증가를 더해 'per 초당' 으로 — 줄어든 쌍(리셋)은 빈칸으로 빼고 음수를 내지 않는다."""
    inc = dur = 0.0
    n = 0
    seen = reset = False
    for a, b in pairs:
        x, y = get(a), get(b)
        if y is not None:
            seen = True
        d = promtext.counter_delta(x, y)
        if d is None:
            reset = reset or (x is not None and y is not None)
            continue
        inc += d
        dur += b.ts - a.ts
        n += 1
    if n:
        return inc / dur * per, None
    if pairs and not seen:
        return None, "모름 — 이 판의 vLLM 지표에 그 칸이 없다"
    if reset:
        return None, "카운터가 다시 0 부터 센다(서버가 다시 떴다) — 이 구간은 빈칸이다"
    return None, "모름 — 표본이 둘 이상 쌓여야 잰다"


def _labeled(name: str, key: tuple[str, ...] | None):
    """라벨 값마다 센 카운터 하나(key 의 라벨 값들을 더한 것 — None 이면 전부). 패밀리가 아예 없으면 None, 있는데 그 라벨이 아직 없으면
    0(한 번도 없었다 — prometheus_client 는 처음 셀 때 그 라벨 줄을 만든다)."""
    def get(s: Snap):
        d = s.by_label.get(name)
        if d is None or (not d and s.counters.get("_has_" + name) is None):
            return None
        return sum(d.values()) if key is None else sum(v for k, v in d.items() if k in key)
    return get


def _hist_window(pairs, name: str) -> tuple[promtext.Hist | None, str | None]:
    acc = None
    seen = reset = False
    for a, b in pairs:
        ha, hb = a.hists.get(name), b.hists.get(name)
        if hb is not None:
            seen = True
        d = promtext.hist_delta(ha, hb)
        if d is None:
            reset = reset or (ha is not None and hb is not None)
            continue
        acc = promtext.hist_add(acc, d)
    if acc is not None:
        return (acc, None) if acc.cum[-1] > 0 else (None, "요청 없음(5분)")
    if pairs and not seen:
        return None, "모름 — 이 판의 vLLM 지표에 그 히스토그램이 없다"
    if reset:
        return None, "카운터가 다시 0 부터 센다(서버가 다시 떴다) — 이 구간은 빈칸이다"
    return None, "모름 — 표본이 둘 이상 쌓여야 잰다"


def derive(hist: deque, interval: float) -> tuple[dict, dict]:
    """최근 표본 → (카드의 지금 값 {이름: (값, 까닭)}, 저장할 표본 값 {이름: 값}). 저장하는 속도는 마지막 쌍 하나로 잰다(리셋이면 빈칸)."""
    max_gap = 4 * interval
    last = hist[-1]
    p60 = _pairs(hist, last.ts - RATE_WINDOW_S, max_gap)
    p5 = _pairs(hist, last.ts - WINDOW_S, max_gap)
    p1 = _pairs(hist, last.ts - 1e-6, max_gap)[-1:]
    now: dict = {}
    keep: dict = {}
    for name, key in (("prompt_tps", "prompt_tokens"), ("gen_tps", "generation_tokens")):
        get = (lambda k: (lambda s: s.counters.get(k)))(key)
        now[name] = _rate(p60, get, 1.0)
        keep[name] = _rate(p1, get, 1.0)[0]
    now["preempt_per_min"] = _rate(p5, lambda s: s.counters.get("preemptions"), 60.0)
    now["requests_per_min"] = _rate(p5, _labeled("finished", None), 60.0)
    now["aborts_per_min"] = _rate(p5, _labeled("finished", ("abort",)), 60.0)

    def errors(s: Snap):
        http_ = _labeled("http", ("5xx",))(s)
        fin = _labeled("finished", ("error",))(s)
        return None if http_ is None and fin is None else (http_ or 0.0) + (fin or 0.0)
    now["errors_per_min"] = _rate(p5, errors, 60.0)
    hits = qs = 0.0
    n = 0
    for a, b in p5:
        dh = promtext.counter_delta(a.counters.get("prefix_hits"), b.counters.get("prefix_hits"))
        dq = promtext.counter_delta(a.counters.get("prefix_queries"), b.counters.get("prefix_queries"))
        if dh is None or dq is None:
            continue
        hits, qs, n = hits + dh, qs + dq, n + 1
    if n and qs > 0:
        now["prefix_hit"] = (min(1.0, hits / qs), None)
    elif n:
        now["prefix_hit"] = (None, "요청 없음(5분)")
    else:   # 쓸 쌍이 없다 — 칸이 없는지 · 리셋인지 · 표본이 모자란지(_rate 의 까닭을 빌린다)
        why = (_rate(p5, lambda s: s.counters.get("prefix_hits"), 1.0)[1]
               or _rate(p5, lambda s: s.counters.get("prefix_queries"), 1.0)[1] or "모름 — 앞부분 캐시 칸을 셀 수 없다")
        now["prefix_hit"] = (None, why)
    for h in ("ttft", "e2e", "queue"):
        acc, why = _hist_window(p5, h)
        for q, tag in ((0.5, "p50"), (0.95, "p95")):
            now[f"{h}_{tag}"] = (promtext.quantile(q, acc), why) if acc is not None else (None, why)
    for k in ("preempt_per_min", "errors_per_min", "prefix_hit", "ttft_p50", "ttft_p95", "e2e_p50", "e2e_p95", "queue_p95"):
        keep[k] = now[k][0]
    return now, keep


# ── 수집기 ─────────────────────────────────────────────────────────────────────────────────────────
class Collector:
    def __init__(self, env_file: Path, store: Store | None, *, interval: float = INTERVAL_S, models_every: float = MODELS_EVERY_S,
                 store_error: str | None = None, port: int | None = None, clock=time.time):
        self.clock = clock                    # 벽시계(초) — 시험이 바꿔 끼운다. 읽기 기한은 따로 monotonic 이다(fetch)
        self.env_file = Path(env_file)
        self.store, self.store_error = store, store_error
        self.interval, self.models_every = interval, models_every
        self.port = port
        self.lock = threading.Lock()
        self.stop_evt = threading.Event()
        self.cfg = Config((), None, None, None, {}, (), False)
        self.states: dict[str, TState] = {}
        self.agent = TState(Target("agent", "에이전트 서버", None, None, None, "agent", None), interval, models_every)
        self.router = TState(Target("router", "LLM 라우터", None, None, None, "router", None), interval, models_every)
        self._env_sig: object = ()
        self.env_problem: str | None = None
        self.started_at = self.clock()
        self.last_tick: float | None = None
        self.thread: threading.Thread | None = None

    # ── 설정 다시 읽기 ──
    def reload(self, *, force: bool = False) -> None:
        try:
            st = os.stat(self.env_file)
            sig: object = (st.st_mtime_ns, st.st_size, st.st_ino)
        except FileNotFoundError:
            sig = None
        except OSError as exc:
            sig = ("err", type(exc).__name__)
        if not force and sig == self._env_sig:
            return
        self._env_sig = sig
        vals: dict[str, str] = {}
        why = None
        if sig is None:
            why = f"{self._rel(self.env_file)} 이 없다 — 기본값(에이전트 서버만)으로 본다"
        else:
            try:
                vals = env_values(self.env_file.read_bytes().decode("utf-8", errors="replace"))
            except OSError as exc:
                why = f"{self._rel(self.env_file)} 을 읽지 못했다({type(exc).__name__}) — 기본값으로 본다"
        cfg = build_config(vals)
        _REDACT.set(cfg.keys.values())
        with self.lock:
            fresh: dict[str, TState] = {}
            for t in cfg.targets:
                old = self.states.get(t.id)
                if old is not None and old.t.addr == t.addr and old.t.key == t.key:
                    old.t = t
                    fresh[t.id] = old
                else:
                    fresh[t.id] = TState(t, self.interval, self.models_every)
            self.states, self.cfg, self.env_problem = fresh, cfg, why
            self.agent.t = self.agent.t._replace(addr=cfg.agent, problem=cfg.agent_problem)
            self.router.t = self.router.t._replace(addr=cfg.router)
        live = [f"{t.label}({t.addr})" for t in cfg.targets if t.problem is None]
        bad = [t.problem for t in cfg.targets if t.problem] + list(cfg.problems) + ([why] if why else [])
        log(f"설정을 읽었다 — LLM 대상 {len(live)}" + (f" · {', '.join(live)}" if live else "")
            + f" · 에이전트 {cfg.agent or '없음'} · 라우터 {cfg.router or '없음(LLM_UPSTREAMS 없음)'}"
            + (" · ⚠ infra/.env 에 LLM_STATUS 가 없다(꺼진 박스 — 다음 update-all 이 내린다)" if not cfg.enabled else ""))
        for b in bad:
            log(f"⚠ {b}")

    @staticmethod
    def _rel(p: Path) -> str:
        try:
            return str(Path(p).resolve().relative_to(ROOT))
        except ValueError:
            return Path(p).name

    # ── 돌리기 ──
    def start(self) -> None:
        self.reload(force=True)
        self.thread = threading.Thread(target=self._loop, name="llm-status-tick", daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_evt.set()

    def _loop(self) -> None:
        while not self.stop_evt.is_set():
            t0, m0 = self.clock(), time.monotonic()
            try:
                self.tick()
            except Exception as exc:  # noqa: BLE001 — 주기 하나의 결함이 수집기를 멈추지 않게
                log(f"⚠ 주기 오류 — {type(exc).__name__}: {exc}")
            self.last_tick = t0
            self.stop_evt.wait(max(0.05, self.interval - (time.monotonic() - m0)))

    def tick(self) -> None:
        self.reload()
        with self.lock:
            states = list(self.states.values())
        for st in states:
            if st.t.problem is None and st.t.addr is not None:
                self._kick(st, self.poll_vllm)
        if self.agent.t.addr is not None:
            self._kick(self.agent, self.poll_agent)
        if self.router.t.addr is not None:
            self._kick(self.router, self.poll_router)
        if self.store is not None:
            self.store.maintain(self.clock())

    def _kick(self, st: TState, fn) -> None:
        """앞 읽기가 끝나지 않았으면 이 주기는 건너뛴다 — 걸린 서버가 다른 대상을 세우지 않고, 자기 스레드를 쌓지도 않는다."""
        with st.lock:
            if st.busy:
                st.skipped += 1
                return
            st.busy, st.busy_since = True, self.clock()
        threading.Thread(target=self._run, args=(st, fn), name=f"llm-status-{st.t.id}", daemon=True).start()

    def _run(self, st: TState, fn) -> None:
        try:
            fn(st)
        except Exception as exc:  # noqa: BLE001 — 한 대상의 결함은 그 대상의 '모름' 으로
            with st.lock:
                for s in ("health",) if st.t.origin in ("agent", "router") else SOURCES:
                    st.mark(s, self.clock(), f"수집기 오류 — {type(exc).__name__}")
            log(f"⚠ {st.t.label} 읽기 오류 — {type(exc).__name__}: {exc}")
        finally:
            with st.lock:
                st.busy, st.busy_since = False, None
                st.polls += 1

    def poll_all_once(self, timeout: float = 60.0) -> None:
        """once — 모든 대상을 한 번씩(나란히) 읽고 기다린다."""
        self.reload(force=True)
        with self.lock:
            jobs = [(st, self.poll_vllm) for st in self.states.values() if st.t.problem is None and st.t.addr is not None]
        if self.agent.t.addr is not None:
            jobs.append((self.agent, self.poll_agent))
        if self.router.t.addr is not None:
            jobs.append((self.router, self.poll_router))
        threads = [threading.Thread(target=self._run, args=job, daemon=True) for job in jobs]
        for th in threads:
            th.start()
        end = time.monotonic() + timeout
        for th in threads:
            th.join(max(0.0, end - time.monotonic()))

    def _note(self, st: TState, what: str, state: str | None, msg: str, *, quiet_first_ok: bool = False) -> None:
        """상태가 바뀔 때만 한 줄 — 요청마다 남기지 않는다. quiet_first_ok 면 처음부터 멀쩡한 것은 적지 않는다(실패와 회복만)."""
        prev = st.noted.get(what, "∅")
        if prev != state:
            st.noted[what] = state
            if not (quiet_first_ok and prev == "∅" and state is None):
                log(msg)

    # ── vLLM 서버 ──
    def poll_vllm(self, st: TState) -> None:
        t = st.t
        a = t.addr
        want_models = st.models_try is None or self.clock() - st.models_try >= self.models_every
        h = fetch(a, "/health")
        now = self.clock()
        if h.kind in UNREACHABLE:
            with st.lock:
                st.cell("up", "health").ok(False, now, h.error)
                for s in ("version", "metrics") + (("models",) if want_models else ()):
                    st.mark(s, now, f"{h.error}(/health 에서 — 묻지 않았다)")
                st.mark("health", now, h.error)
                for name, src in VLLM_VALUES.items():
                    if src in ("version", "metrics") or (src == "models" and want_models):
                        st.cell(name, src).fail(f"{h.error}(/health 에서 — 묻지 않았다)")
                if want_models:
                    st.models_try = now
            self._save(t, now, {"up": 0.0})
            self._note(st, "up", "down:" + h.kind, f"{t.label}({a}) 내려감 — {h.error}")
            return
        up = h.status == 200
        with st.lock:
            st.mark("health", now, None if up else h.error)
            st.cell("up", "health").ok(up, now, None if up else f"/health 가 {h.error}")
        self._save(t, now, {"up": 1.0 if up else 0.0})
        self._note(st, "up", "up" if up else f"http:{h.status}",
                   f"{t.label}({a}) " + ("살아 있다" if up else f"/health {h.error}"))
        # /version — {"version": "0.23.0"}
        v = fetch(a, "/version")
        now = self.clock()
        ver = _json(v) if v.status == 200 else None
        vs = ver.get("version") if isinstance(ver, dict) else None
        with st.lock:
            if isinstance(vs, str) and vs:
                st.mark("version", now, None)
                st.cell("version", "version").ok(scrub(vs, 40), now)
            else:
                why = v.error or "판 글이 {\"version\": …} 꼴이 아니다"
                st.mark("version", now, why)
                st.cell("version", "version").fail(why)
        self._metrics(st, fetch(a, "/metrics"))
        if want_models:
            key = self.cfg.keys.get(t.key or "llm")
            mo = fetch(a, "/v1/models", headers={"Authorization": f"Bearer {key}"} if key else None)
            self._models(st, mo, key_name="CHAT_LLM_API_KEY" if t.key == "chat" else "LLM_API_KEY", had_key=bool(key))

    def _metrics(self, st: TState, m: Resp) -> None:
        now = self.clock()
        t = st.t
        ex = None
        bad = 0
        if m.status == 200:
            parsed = promtext.parse(m.body.decode("utf-8", errors="replace"))
            ex, bad = promtext.vllm(parsed), parsed.bad
        if ex is None:
            why = m.error or "지표 글이 vLLM 모양이 아니다(running · waiting 칸이 없다)"
            with st.lock:
                st.mark("metrics", now, why)
                for name, src in VLLM_VALUES.items():
                    if src == "metrics":
                        st.cell(name, src).fail(why)
            self._note(st, "metrics", why, f"{t.label}({t.addr}) 지표를 못 읽는다 — {why}")
            return
        counters = dict(ex["counters"])
        for k, d in ex["by_label"].items():   # 라벨 칸이 아직 하나도 없는 것(한 번도 없었다 — 0)과 패밀리가 없는 것(모름)을 가른다(_labeled)
            fam = promtext.BY_LABEL[k][0]
            counters["_has_" + k] = 1.0 if (d or fam in parsed.types or parsed.named(fam)) else None
        snap = Snap(now, counters, ex["by_label"], ex["hists"])
        with st.lock:
            if st.hist and now <= st.hist[-1].ts:
                st.hist.clear()                     # 시계가 거꾸로 갔다 — 창을 새로 쌓는다
            st.hist.append(snap)
            cur, keep = derive(st.hist, self.interval)
            g = ex["gauges"]
            st.mark("metrics", now, None)
            st.cell("running", "metrics").ok(g["running"], now)
            st.cell("waiting", "metrics").ok(g["waiting"], now)
            st.cell("kv", "metrics").ok(g["kv"], now, None if g["kv"] is not None else "모름 — 이 판의 지표에 KV 캐시 칸이 없다")
            for name, (val, why) in cur.items():
                st.cell(name, "metrics").ok(val, now, why)
            st.src["metrics"]["bad_lines"] = bad
        self._note(st, "metrics", None, f"{t.label}({t.addr}) 지표를 다시 읽는다", quiet_first_ok=True)
        vals = {"running": g["running"], "waiting": g["waiting"], "kv": g["kv"], **keep}
        self._save(t, now, vals)

    def _models(self, st: TState, r: Resp, *, key_name: str, had_key: bool) -> None:
        now = self.clock()
        body = _json(r) if r.status == 200 else None
        data = body.get("data") if isinstance(body, dict) else None
        rows = []
        if isinstance(data, list):
            for d in data:
                if isinstance(d, dict) and isinstance(d.get("id"), str) and d["id"]:
                    n = d.get("max_model_len")
                    rows.append({"id": scrub(d["id"], 120), "max_model_len": n if isinstance(n, int) and not isinstance(n, bool) else None})
        with st.lock:
            st.models_try = now
            if rows:
                st.mark("models", now, None)
                st.cell("models", "models").ok(rows, now)
                lens = [x["max_model_len"] for x in rows if x["max_model_len"]]
                st.cell("context", "models").ok(max(lens) if lens else None, now,
                                                None if lens else "모름 — 모델 목록에 max_model_len 이 없다")
            else:
                if r.status in (401, 403):
                    why = (f"HTTP {r.status} — 키가 맞지 않는다({key_name}, infra/.env)" if had_key
                           else f"HTTP {r.status} — 키가 없다(infra/.env 의 {key_name})")
                else:
                    why = r.error or "모델 목록이 {\"data\": [{\"id\": …}]} 꼴이 아니다"
                st.mark("models", now, why)
                st.cell("models", "models").fail(why)
                st.cell("context", "models").fail(why)
        self._note(st, "models", None if rows else (r.kind + str(r.status)),
                   f"{st.t.label}({st.t.addr}) " + ("모델 목록을 다시 읽는다" if rows else f"모델 목록을 못 읽는다 — {st.cells['models'].error}"),
                   quiet_first_ok=True)

    # ── 에이전트 서버 /health — '지금 쓰는 일'(HWAX 몫만) ──
    def poll_agent(self, st: TState) -> None:
        r = fetch(st.t.addr, "/health")
        now = self.clock()
        d = _json(r) if r.status == 200 else None
        if not isinstance(d, dict):
            why = r.error or "/health 가 JSON 이 아니다"
            with st.lock:
                st.mark("health", now, why)
                st.cell("up", "agent").ok(False, now, why)
                for name in AGENT_VALUES[1:]:
                    st.cell(name, "agent").fail(why)
            self._save(st.t, now, {"up": 0.0})
            self._note(st, "up", why, f"에이전트 서버({st.t.addr})를 못 읽는다 — {why}")
            return

        def num(x):
            return x if isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) else None

        def pick(src, keys):
            return {k: (scrub(src.get(k), 160) if isinstance(src.get(k), str) else src.get(k)) for k in keys} \
                if isinstance(src, dict) else None
        chat = ((d.get("load") or {}).get("chat") if isinstance(d.get("load"), dict) else None)
        chat_v = None
        if isinstance(chat, dict):
            ttft = chat.get("ttft_ms") if isinstance(chat.get("ttft_ms"), dict) else {}
            chat_v = {"active": num(chat.get("active")), "slow": bool(chat.get("slow")), "ratio_p50": num(chat.get("ratio_p50")),
                      "ttft_ms": {k: {q: num((ttft.get(k) or {}).get(q)) for q in ("n", "p50", "p95")}
                                  for k in ("idle", "review") if isinstance(ttft.get(k), dict)}}
        cl = d.get("chat_llm")
        chat_llm = None
        if isinstance(cl, dict):
            chat_llm = pick(cl, ("enabled", "server", "model", "thinking", "effort", "streaming", "ctx_tokens", "last_error", "last_error_at"))
            fb = cl.get("fallback")
            chat_llm["fallback"] = pick(fb, ("enabled", "count", "last_at")) if isinstance(fb, dict) else None
        vals = {"delib_active": num(d.get("delib_active")), "delib_queued": num(d.get("delib_queued")),
                "delib_seats_running": num(d.get("delib_seats_running")),
                "delib_paused": d.get("delib_paused") if isinstance(d.get("delib_paused"), bool) else None,
                "routine_active": num(d.get("routine_active")), "routine_parked": num(d.get("routine_parked")),
                "routine_max": num(d.get("routine_max")), "review_active": num(d.get("review_active")),
                "card_review": pick(d.get("card_review"), ("active", "limit", "limit_reason", "delib_human", "retry_after_s")),
                "chat_active": None if chat_v is None else chat_v["active"], "chat": chat_v, "chat_llm": chat_llm,
                "context_tokens": num(d.get("context_tokens")),
                "model": scrub(d.get("model"), 120) if isinstance(d.get("model"), str) else None}
        with st.lock:
            st.mark("health", now, None)
            st.cell("up", "agent").ok(True, now)
            for name, v in vals.items():
                st.cell(name, "agent").ok(v, now, None if v is not None else "모름 — 이 판의 에이전트 서버 /health 에 그 칸이 없다")
        self._note(st, "up", None, f"에이전트 서버({st.t.addr})를 다시 읽는다", quiet_first_ok=True)
        self._save(st.t, now, {"up": 1.0, **{k: vals[k] for k in STORE_AGENT[1:]}})

    # ── LLM 라우터 /health · /stats ──
    def poll_router(self, st: TState) -> None:
        h = fetch(st.t.addr, "/health")
        now = self.clock()
        hd = _json(h)
        if not isinstance(hd, dict):
            why = h.error or "/health 가 JSON 이 아니다"
            with st.lock:
                st.mark("health", now, why)
                st.cell("up", "router").ok(False, now, why)
                for name in ROUTER_VALUES[1:]:
                    st.cell(name, "router").fail(why)
            self._save(st.t, now, {"up": 0.0})
            self._note(st, "up", why, f"LLM 라우터({st.t.addr})를 못 읽는다 — {why}")
            return
        s = fetch(st.t.addr, "/stats")
        sd = _json(s) if s.status == 200 else None
        ups = None
        if isinstance(sd, list):
            ups = []
            for u in sd:
                if not isinstance(u, dict):
                    continue
                url = u.get("url") if isinstance(u.get("url"), str) else ""
                try:
                    p = urllib.parse.urlsplit(url)
                    addr = f"{p.hostname}:{p.port or (443 if p.scheme == 'https' else 80)}" if p.hostname else "?"
                except ValueError:
                    addr = "?"
                row = {"addr": addr}
                for k in ("up", "reachable", "models", "running", "waiting", "kv", "inflight", "sent", "connect_fail",
                          "retried_away", "sticky", "overflow", "metrics_age_s"):
                    v = u.get(k)
                    row[k] = v if isinstance(v, (bool, int, float, str)) or v is None else None
                    if isinstance(row[k], str):
                        row[k] = scrub(row[k], 40)
                ups.append(row)
        models = hd.get("models") if isinstance(hd.get("models"), dict) else {}
        vals = {"status": scrub(hd.get("status"), 20), "inflight": hd.get("inflight"), "upstreams_up": hd.get("upstreams_up"),
                "upstreams_total": hd.get("upstreams_total"), "models_match": models.get("match")}
        with st.lock:
            st.mark("health", now, None)
            st.cell("up", "router").ok(True, now)
            for k, v in vals.items():
                st.cell(k, "router").ok(v if v is None or isinstance(v, (bool, int, float, str)) else None, now)
            if ups is not None:
                st.cell("upstreams", "router").ok(ups, now)
            else:
                st.cell("upstreams", "router").fail(s.error or "/stats 가 목록이 아니다")
        self._note(st, "up", None, f"LLM 라우터({st.t.addr})를 다시 읽는다", quiet_first_ok=True)
        inflight = hd.get("inflight")
        self._save(st.t, now, {"up": 1.0, "inflight": inflight if isinstance(inflight, (int, float)) else None})

    def _save(self, t: Target, now: float, vals: dict) -> None:
        if self.store is None:
            return
        keep = (STORE_REPLICA if t.origin == "replica" else STORE_AGENT if t.origin == "agent"
                else STORE_ROUTER if t.origin == "router" else STORE_MAIN)
        clean = {k: (1.0 if v is True else 0.0 if v is False else v) for k, v in vals.items() if k in keep}
        self.store.add(t.id, now, clean)

    # ── 보기 ──
    def _target_view(self, st: TState, now: float) -> dict:
        t = st.t
        with st.lock:
            if t.problem is not None:
                values = {name: unknown("config", f"모름 — {t.problem}") for name in VLLM_VALUES}
            else:
                values = {}
                for name, src in VLLM_VALUES.items():
                    c = st.cells.get(name)
                    values[name] = c.view(now) if c is not None else Cell(src, st.models_every if src == "models"
                                                                         else self.interval).view(now)
            for name in APPROX:
                values[name]["approx"] = True
            return {"id": t.id, "label": t.label, "addr": None if t.addr is None else str(t.addr), "origin": t.origin,
                    "group": t.group, "node": t.node, "key": t.key, "problem": t.problem, "busy": st.busy,
                    "busy_s": None if st.busy_since is None else round(now - st.busy_since, 1), "polls": st.polls,
                    "skipped": st.skipped, "sources": st.src_view(now), "values": values}

    def _side_view(self, st: TState, names: tuple[str, ...], source: str, now: float) -> dict:
        t = st.t
        with st.lock:
            if t.addr is None:
                why = t.problem or "모름 — 설정되지 않았다"
                values = {n: unknown(source, f"모름 — {why}" if not why.startswith("모름") else why) for n in names}
            else:
                values = {n: (st.cells[n].view(now) if n in st.cells else Cell(source, self.interval).view(now)) for n in names}
            return {"id": t.id, "label": t.label, "addr": None if t.addr is None else str(t.addr), "problem": t.problem,
                    "busy": st.busy, "polls": st.polls, "skipped": st.skipped, "sources": st.src_view(now), "values": values}

    def snapshot(self) -> dict:
        now = self.clock()
        with self.lock:
            states = list(self.states.values())
            cfg = self.cfg
        targets = [self._target_view(st, now) for st in states]
        # 같은 모델의 창이 서버마다 다르면 표지 — 섞인 풀 · rolling 중의 복제본(chat-llm-stcx CL-D9)
        by_model: dict[str, dict[str, int]] = {}
        for tv in targets:
            mv = tv["values"]["models"]
            if mv["value"] and not mv["stale"]:
                for m in mv["value"]:
                    if m.get("max_model_len"):
                        by_model.setdefault(m["id"], {})[tv["label"]] = m["max_model_len"]
        differs = [{"model": m, "windows": w} for m, w in sorted(by_model.items()) if len(set(w.values())) > 1]
        flagged = {lab for d in differs for lab in d["windows"]}
        for tv in targets:
            known = tv["values"]["models"]["value"] is not None
            tv["values"]["context_mismatch"] = {"value": (tv["label"] in flagged) if known else None, "at": now if known else None,
                                                "source": "models", "error": None if known else tv["values"]["models"]["error"],
                                                "stale": False, "age_s": 0.0 if known else None}
        router = self._side_view(self.router, ROUTER_VALUES, "router", now) if cfg.router is not None else None
        tick_age = None if self.last_tick is None else round(now - self.last_tick, 1)
        stalled = self.thread is not None and (not self.thread.is_alive() or (tick_age is not None
                                                                              and tick_age > STALE_AFTER * self.interval + 5))
        return {
            "collector": {"version": VERSION, "state": "stalled" if stalled else "ok", "now": now, "started_at": self.started_at,
                          "last_tick_at": self.last_tick, "tick_age_s": tick_age, "interval_s": self.interval,
                          "models_every_s": self.models_every, "stale_after_s": STALE_AFTER * self.interval,
                          "enabled": cfg.enabled, "port": self.port,
                          "problems": [p for p in [*cfg.problems, self.env_problem] if p],
                          "db": (self.store.stats() if self.store is not None else {"bytes": 0, "series": 0, "error": self.store_error}),
                          "keys": {"LLM_API_KEY": bool(cfg.keys.get("llm")), "CHAT_LLM_API_KEY": bool(cfg.keys.get("chat"))}},
            "targets": targets,
            "context": {"value": differs, "at": now, "source": "models", "error": None, "stale": False, "age_s": 0.0},
            "agent": dict(self._side_view(self.agent, AGENT_VALUES, "agent", now),
                          caption="HWAX 에이전트 서버가 보는 몫만이다 — 같은 LLM 서버를 바로 부르는 다른 서비스(AIDataHub · SignalForge 등)는 들지 않는다"),
            "router": router,
            "slurm": {**unknown("slurm", SLURM_WHY), "rows": [], "milestone": "M3"},
            "gpu": {**unknown("gpu", GPU_WHY), "rows": [], "milestone": "M4"},
        }

    def series_view(self, target: str, metric: str, rng: str) -> tuple[dict, int]:
        with self.lock:
            known = {st.t.id: st.t.origin for st in self.states.values()}
        known.update({"agent": "agent", **({"router": "router"} if self.cfg.router is not None else {})})
        if target not in known:
            return {"error": f"모르는 대상이다 — 설정된 대상: {', '.join(sorted(known))}"}, 404
        origin = known[target]
        allowed = (STORE_REPLICA if origin == "replica" else STORE_AGENT if origin == "agent"
                   else STORE_ROUTER if origin == "router" else STORE_MAIN)
        if metric not in allowed:
            return {"error": f"그 대상은 그 지표를 쌓지 않는다 — 쌓는 지표: {', '.join(allowed)}"}, 400
        if rng not in RANGES:
            return {"error": f"범위는 {', '.join(RANGES)} 중 하나다"}, 400
        head = {"target": target, "metric": metric, "approx": metric in APPROX}
        if self.store is None:
            return {**head, "range": rng, "step_s": RANGES[rng][2], "source": "none", "points": [], "at": None,
                    "error": f"저장소가 없다 — {self.store_error or '수집기가 저장 없이 돈다'}"}, 200
        s = self.store.series(target, metric, rng)
        pts = s["points"]
        return {**head, **s, "at": pts[-1][0] if pts else None,
                "error": None if pts else "아직 쌓인 표본이 없다", "db_error": self.store.error}, 200

    def health(self) -> tuple[dict, int]:
        now = self.clock()
        tick_age = None if self.last_tick is None else round(now - self.last_tick, 1)
        alive = self.thread is not None and self.thread.is_alive() and (tick_age is None or tick_age <= STALE_AFTER * self.interval + 5)
        with self.lock:
            n = len(self.states)
        db = self.store.stats() if self.store is not None else {"error": self.store_error}
        return ({"status": "ok" if alive else "stalled", "version": VERSION, "now": now, "started_at": self.started_at,
                 "last_tick_at": self.last_tick, "tick_age_s": tick_age, "interval_s": self.interval, "targets": n,
                 "agent": self.agent.t.addr is not None, "router": self.cfg.router is not None, "enabled": self.cfg.enabled,
                 "db_error": db.get("error")}, 200 if alive else 503)


# ── HTTP 창구 ───────────────────────────────────────────────────────────────────────────────────────
def json_safe(o):
    """유한하지 않은 수(NaN · Inf)는 null — 브라우저의 JSON.parse 가 NaN 을 못 읽는다."""
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    if isinstance(o, dict):
        return {k: json_safe(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [json_safe(v) for v in o]
    return o


def dumps(obj) -> bytes:
    return _REDACT.apply(json.dumps(json_safe(obj), ensure_ascii=False, separators=(",", ":"), allow_nan=False)).encode("utf-8")


_Q_TARGET = re.compile(r"[A-Za-z0-9._:-]{1,64}")
_Q_METRIC = re.compile(r"[a-z0-9_]{1,40}")


def make_handler(coll: Collector):
    class Api(http.server.BaseHTTPRequestHandler):
        server_version = "hwax-llm-status/1"
        sys_version = ""

        def log_message(self, fmt, *args) -> None:     # 요청마다 남기지 않는다
            return

        def _send(self, code: int, obj, head: bool = False) -> None:
            data = dumps(obj)
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if not head:
                self.wfile.write(data)

        def _route(self, head: bool) -> None:
            u = urllib.parse.urlsplit(self.path)
            if u.path == "/health":
                body, code = coll.health()
            elif u.path == "/snapshot":
                body, code = coll.snapshot(), 200
            elif u.path == "/series":
                q = urllib.parse.parse_qs(u.query)
                target, metric, rng = (q.get("target") or [""])[0], (q.get("metric") or [""])[0], (q.get("range") or ["1h"])[0]
                if not _Q_TARGET.fullmatch(target) or not _Q_METRIC.fullmatch(metric):
                    body, code = {"error": "target · metric 이 없거나 꼴이 틀렸다"}, 400
                else:
                    body, code = coll.series_view(target, metric, rng)
            else:
                body, code = {"error": "없는 창구다 — /health · /snapshot · /series"}, 404
            self._send(code, body, head)

        def do_GET(self) -> None:
            self._route(False)

        def do_HEAD(self) -> None:
            self._route(True)

        def _no(self) -> None:
            self._send(405, {"error": "GET 만 받는다"})

        do_POST = do_PUT = do_DELETE = do_PATCH = _no

    return Api


class _Server(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def _port_arg(args, vals: dict[str, str]) -> int:
    if args.port is not None:
        return args.port
    raw = vals.get("LLM_STATUS_PORT", str(DEFAULT_PORT))
    if not re.fullmatch(r"[0-9]{1,5}", raw) or not 1 <= int(raw) <= 65535:
        raise SystemExit(f"✗ LLM_STATUS_PORT='{raw[:20]}' 는 1~65535 의 포트가 아니다(기본 {DEFAULT_PORT})")
    return int(raw)


def _env_file(args) -> Path:
    return Path(args.env_file or os.environ.get("LLM_STATUS_ENV_FILE") or DEFAULT_ENV_FILE)


def state_dir(args) -> Path:
    """저장 자리 — 인자 > 환경 LLM_STATUS_STATE_DIR(시험 · 손 점검) > 리포의 infra/.state/llm-status."""
    return Path(getattr(args, "state_dir", None) or os.environ.get("LLM_STATUS_STATE_DIR") or DEFAULT_STATE_DIR)


def open_state(state: Path):
    """(잠금 파일, 저장소|None, 까닭|None) — 폴더는 700, 파일은 600(umask). 잠금을 다른 수집기가 쥐고 있으면 (None, None, 까닭).
    저장소를 못 열면 잠금만 쥐고 지금 값만 낸다(저장소 칸이 까닭을 보인다). umask 는 만드는 동안만 077 이다(부른 프로세스의 것을 되돌린다 —
    수집기 자신은 serve 가 처음부터 077 로 돈다. WAL 곁 파일도 그래서 600 이다)."""
    old = os.umask(0o077)
    try:
        state.mkdir(parents=True, exist_ok=True)
        state.chmod(0o700)
        lock = open(state / ".lock", "a")                   # noqa: SIM115 — 사는 동안 쥔다
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            lock.close()
            return None, None, (f"다른 수집기가 이 상태 디렉터리({state})를 쓰고 있다 — 포트를 바꿨다면 옛 포트의 것을 먼저 내린다: "
                                "LLM_STATUS_PORT=<옛 포트> ./infra/scripts/llm-status.sh stop")
        try:
            return lock, Store(state / DB_NAME), None
        except Exception as exc:  # noqa: BLE001 — 저장소가 없어도 지금 값은 낸다
            return lock, None, f"{type(exc).__name__}: {exc}"[:200]
    finally:
        os.umask(old)


def serve(args) -> int:
    os.umask(0o077)                    # 수집기가 만드는 것은 모두 이 계정만 읽는다(로그 · sqlite 와 그 곁 파일)
    env_file = _env_file(args)
    try:
        vals = env_values(env_file.read_bytes().decode("utf-8", errors="replace"))
    except OSError:
        vals = {}
    port = _port_arg(args, vals)
    state = state_dir(args)
    lock, store, store_error = open_state(state)
    if lock is None:
        print(f"✗ {store_error}", file=sys.stderr, flush=True)
        return 1
    if store is None:
        log(f"⚠ 저장소를 열지 못했다 — 지금 값만 낸다({store_error})")
    coll = Collector(env_file, store, interval=args.interval, models_every=args.models_every, store_error=store_error, port=port)
    try:
        httpd = _Server(("127.0.0.1", port), make_handler(coll))
    except OSError as exc:
        print(f"✗ 127.0.0.1:{port} 를 잡지 못했다({type(exc).__name__}: {exc}) — 그 포트에 다른 것이 떠 있다(docs/PORT-MAP.md)",
              file=sys.stderr, flush=True)
        return 1

    def _term(signum, _frame) -> None:
        coll.stop()
        threading.Thread(target=httpd.shutdown, daemon=True).start()
    signal.signal(signal.SIGTERM, _term)
    signal.signal(signal.SIGINT, _term)
    log(f"시작 — 127.0.0.1:{port} · {coll.interval:g}초마다(모델 목록 {coll.models_every:g}초) · 저장 {Collector._rel(state)}")
    coll.start()
    try:
        httpd.serve_forever(poll_interval=0.5)
    finally:
        coll.stop()
        httpd.server_close()
        if store is not None:
            with contextlib.suppress(Exception):
                store.close()
        lock.close()
        log("끝낸다")
    return 0


def once(args) -> int:
    _LOG["stream"] = sys.stderr
    coll = Collector(_env_file(args), None, store_error="once — 저장하지 않는다")
    coll.poll_all_once()
    sys.stdout.buffer.write(_REDACT.apply(json.dumps(json_safe(coll.snapshot()), ensure_ascii=False, indent=1)).encode("utf-8") + b"\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="LLM/GPU 현황 수집기 — docs/ops-dashboard/server-setup.md")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("serve", help="루프백 한 포트로 돈다(llm-status.sh run 이 띄운다)")
    sp.add_argument("--port", type=int, default=None, help=f"듣는 포트(기본 infra/.env 의 LLM_STATUS_PORT, 없으면 {DEFAULT_PORT})")
    sp.add_argument("--interval", type=float, default=INTERVAL_S, help=argparse.SUPPRESS)          # 시험용
    sp.add_argument("--models-every", type=float, default=MODELS_EVERY_S, help=argparse.SUPPRESS)  # 시험용
    sp.add_argument("--state-dir", default=None, help=argparse.SUPPRESS)
    sp.add_argument("--env-file", default=None, help=argparse.SUPPRESS)
    op = sub.add_parser("once", help="한 번 읽어 스냅숏을 찍는다(저장하지 않는다)")
    op.add_argument("--env-file", default=None, help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    if a.cmd == "serve":
        if not (0.05 <= a.interval <= 3600 and 0.05 <= a.models_every <= 86400):
            ap.error("주기가 틀렸다")
        return serve(a)
    return once(a)


if __name__ == "__main__":
    sys.exit(main())
