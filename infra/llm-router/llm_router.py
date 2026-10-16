# vLLM 서버 여럿 앞에서 /metrics 를 읽어 덜 바쁜 서버로 요청을 넘기는 LLM 라우터 — 원시 ASGI + httpx(docs/llm-pool PLAN §3)
"""LLM 라우터 — `python3 -m uvicorn --app-dir infra/llm-router llm_router:app` 으로 뜬다(infra/scripts/llm-router.sh run).

계약(PLAN §3 · context-notes LP-D2~D13).
  설정  리포 루트의 infra/.env 를 직접 읽는다(파일 위치에서 유도 — 키를 argv·환경으로 받지 않는다). LLM_ROUTER_ENV_FILE 은 시험·손 점검용
        다른 파일이다. 읽는 규칙은 update-all `_envfile_value` 와 같고, 지표 주기마다 내용을 견줘 바뀌었으면 다시 읽는다(재기동 없음).
        LLM_UPSTREAMS 의 규칙은 lib/llm-pool.sh hwax_llm_pool_upstreams(정본)와 같고 같은 표로 대조된다 — 틀린 칸이 하나라도 있으면 줄 전체를
        받지 않는다. 다시 읽은 목록이 비거나 틀렸으면 마지막 목록으로 계속 보내고 /health 의 kept_last_list 가 true 다 — 풀을 끄는 것은
        update-all 이고(사본을 되돌린 뒤 라우터를 내린다) 재기동이 미뤄진 손님은 그때까지 이 라우터를 부른다. 처음 읽을 때 비었거나 틀렸으면 503.
  올라옴  연결이 되고 **마지막 /v1/models 가 200 으로 모델 목록을 줬고** 탐침이 연달아 PROBE_TIMEOUTS_DOWN 번 읽기 한도를 넘기지 않은 서버만
        '올라옴' 이다. 아직 답하지 않은 서버(모름 — 내려갔다 올라온 서버도 다시 물을 때까지)·목록을 못 준 서버·답이 없는 서버는 올라온 서버가
        하나도 없을 때만 쓴다. 요청이 model 을 적었으면 그 모델이 있는 서버를 먼저 고르고(없으면 올라온 서버 전부), 그 가운데 그 모델의 창
        (max_model_len)이 가장 큰 서버만 쓴다(모델을 적지 않았으면 서버마다 가장 큰 창으로 견준다).
  기동  첫 지표·모델 대조를 STARTUP_PROBE_S 까지만 기다리고 듣기 시작한다 — 답하지 않은 서버는 '모름' 이고 탐침은 이어 돈다.
  고르기  부하 = 마지막 지표의 running + waiting(라벨 묶음 전부 합) + 그 뒤로 이 라우터가 더 보낸 수 — 이 라우터가 그 서버에 보내 도는 수보다
        작아지지 않는다. 지표를 잠깐 못 읽으면(읽기 한도 · 끊김 · 5xx) 마지막 지표를 세 번째 실패까지 쓰고, 404 · vLLM 모양이 아닌 글 · 세 번
        연달은 실패면 이 라우터가 보낸 도는 수로만 잰다. 같으면 KV 사용률, 그다음 목록 순서.
  붙임  메시지 앞부분 PREFIX_CHARS 자의 해시 → 렌데부 해시로 선호 서버. 선호 서버가 가장 한가한 서버보다 STICKY_SLACK 이상 바쁘면 떨어진다.
  넘김  연결 실패(요청이 서버에 닿지 않은 것)만 그 서버를 COOLDOWN_S 동안 빼고 다른 서버로 — 요청마다 서버 하나에 한 번. 연결된 뒤의 일
        (HTTP 오류 · 생성 중 끊김)은 그대로 넘기고 다시 보내지 않는다(LP-D3). 모두 빠졌으면 전부를 다시 시도해 본다. 서버 하나에서 난 뜻밖의
        예외는 그 서버만 빼고(보낸 것이 없을 때만 다음 서버로) 라우터 전체로 번지지 않는다.
  흐름  위로는 늘 스트림으로 보내고 받은 바이트를 그대로 흘린다. 손님이 끊으면 머리 전이든 흐르는 중이든 곧바로 위 연결을 닫는다
        (vLLM 이 생성을 멈춘다 — 버려진 생성이 GPU 를 잡지 않게). 요청 머리는 손님 것만 간다(httpx 기본 머리를 덧붙이지 않는다).
  시간  연결 한도 하나뿐이다. 읽기·쓰기 한도는 부르는 쪽의 것이다 — 시간 한도 사슬에 층을 끼우지 않는다.
  키    손님의 Authorization 을 그대로 넘기고 끼워 넣지 않는다(LP-D9). LLM_API_KEY 는 라우터 자신의 /v1/models 대조에만 쓴다.
  TLS   위 서버는 http 이거나 공인 인증서의 https 여야 한다 — 사설 CA 를 줄 자리가 없다(trust_env=False · --cleanenv). 인증서 오류는 따로 알린다.
  로그  요청마다 남기지 않는다 — 기동 · 다시 읽기 · 서버 오르내림 · 지표·모델 상태가 바뀔 때 · 연결 실패만. 키와 본문은 어디에도 찍지 않고,
        틀린 LLM_UPSTREAMS 칸은 스킴과 호스트만 찍는다(질의·계정에 키가 들 수 있다).
"""
import asyncio
import contextlib
import hashlib
import json
import logging
import math
import os
import re
import ssl
import sys
import time
from dataclasses import dataclass, replace
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]   # infra/llm-router/llm_router.py → 리포 루트(dev ~/claude · cae00 ~/Projects · 컨테이너 /workspace)
DEFAULT_ENV_FILE = ROOT / "infra" / ".env"
LOG = logging.getLogger("llm_router")

MODELS_EVERY_S = 60.0     # /v1/models 대조 주기(설정이 바뀌어 서버 목록이 달라지면 곧바로 한 번 더)
PROBE_READ_S = 10.0       # 라우터 자신의 탐침(/metrics · /v1/models) 읽기 한도 — 손님 요청 경로가 아니다
BIG_BODY = 1 << 20        # 이보다 큰 본문은 JSON 해석을 이벤트 루프 밖에서 한다(1M 창 요청은 수 MB 다)
METRICS_KEEP_FAILS = 3    # 지표 일시 실패가 이만큼 연달면 마지막 지표를 버리고 보낸 수로만 잰다
PROBE_TIMEOUTS_DOWN = 3   # 탐침(지표 · 모델)이 연달아 이만큼 읽기 한도를 넘기면 다시 답할 때까지 '올라옴' 이 아니다(검토 2라운드 LOW 1)
STARTUP_PROBE_S = 2.0     # 기동 때 첫 지표·모델 대조를 함께 기다리는 한도 — 넘으면 '모름' 으로 두고 듣기 시작한다(검토 2라운드 M-C)
DEFAULT_ROUTER_PORT = 8730

# 손잡이 → (기본값, 형, 최솟값). 수가 아니거나 최솟값보다 작으면 기본값으로 두고 읽을 때마다 한 줄 알린다.
# STICKY_SLACK — 붙인 서버의 부하가 가장 한가한 서버보다 이만큼 이상 많으면 떨어진다. 같은 앞부분 요청이 한꺼번에 몰리면 두 서버의 부하
#   차이는 많아야 이만큼 벌어진다(기본 2 — 빈 서버 둘에 같은 앞부분 8 개면 5·3, 4 였을 때는 6·2). 크게 두면 캐시를 더 쓰고 더 기운다.
KNOBS: dict[str, tuple[float, type, float]] = {
    "LLM_ROUTER_SCRAPE_S": (2.0, float, 0.05),
    "LLM_ROUTER_STICKY_SLACK": (2.0, float, 0.0),
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
_TARGET_CHECK = httpx.URL("http://127.0.0.1/")                # 요청 대상이 httpx 주소 조각이 되는지 서버와 상관없이 본다


def _proxy_timeout(connect_s: float) -> httpx.Timeout:
    """손님 요청의 한도 — 연결뿐이다. 읽기·쓰기·풀 한도를 두면 부르는 쪽(엔진 1800초 · 리스크 앱 …)의 사슬 안에 라우터의 층이 하나 더
    생기고, 그 층이 먼저 끊으면 손잡이 이름 없는 끊김이 된다(docs/delib-engine-feedback D-17). 끊는 것은 부르는 쪽이고 그 끊김은 위로 전해진다."""
    return httpx.Timeout(connect=connect_s, read=None, write=None, pool=None)


def _probe_timeout(connect_s: float) -> httpx.Timeout:
    return httpx.Timeout(connect=connect_s, read=PROBE_READ_S, write=PROBE_READ_S, pool=PROBE_READ_S)


# ── 설정 ───────────────────────────────────────────────────────────────────────────────────────────
# 공백은 sed 의 [[:space:]](LC_ALL=C)와 같은 ASCII 여섯 — NBSP·U+3000 은 값의 일부다(lib 도 LC_ALL=C 로 같은 글자만 공백으로 본다).
_WS = " \t\n\v\f\r"
_ENV_LINE = re.compile(r"^[ \t\v\f\r]*(?:export[ \t\v\f\r]+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$")
_INLINE_COMMENT = re.compile(r"[ \t\v\f\r]+#.*$")


def env_values(text: str, *, quotes: bool = False) -> dict[str, str]:
    """infra/.env 글 → {키: 값}(빈 값도 남긴다 — 마지막 줄이 빈 값이면 그 키는 꺼진 것이다). 규칙은 update-all `_envfile_value`(sed)와 같다 —
    `export` 허용, 공백 뒤 `#` 이후를 벗긴 **뒤에** 양끝 공백을 지우고(먼저 지우면 `KEY=   # 설명` 의 설명이 값이 된다) CR 을 지운다.
    quotes=False 면 따옴표 문자도 지운다(_envfile_value 의 값). True 면 남긴다(lib 의 _hwax_llm_raw — LLM_UPSTREAMS 의 모양 검사에 쓴다).
    줄은 개행으로만 나눈다(sed 와 같게 — splitlines 는 \\r · \\x85 · U+2028 에서도 끊는다). 공백은 ASCII 여섯뿐이다(bash 독자는 첫 sed 까지
    LC_ALL=C — UTF-8 로케일의 [[:space:]] 는 U+3000 도 먹는다). NUL 은 마지막에 지운다 — bash 의 `$(…)` 가 그렇게 받는다(검토 2라운드 LOW 2)."""
    vals: dict[str, str] = {}
    for ln in text.split("\n"):
        m = _ENV_LINE.match(ln)
        if m:
            v = _INLINE_COMMENT.sub("", m.group(2)).strip(_WS).replace("\r", "").replace("\x00", "")
            vals[m.group(1)] = v if quotes else v.replace('"', "").replace("'", "")
    return vals


def read_env(path: Path) -> dict[str, str]:
    """infra/.env → {키: 값}. 빈 값은 없는 것이다. 못 읽으면 OSError 가 그대로 올라간다. 바이트로 읽는다 — read_text 는 홀로 선 \\r 을
    줄바꿈으로 바꿔 읽는다(_reload 와 같게)."""
    return {k: v for k, v in env_values(path.read_bytes().decode("utf-8", errors="replace")).items() if v}


# LLM_UPSTREAMS 규칙 — 정본은 lib/llm-pool.sh hwax_llm_pool_upstreams 다(그 함수 머리 주석). 같은 표로 대조된다
# (backend/tests/test_llm_pool_upstreams_rules.py). 한쪽만 고치면 1i 는 '아무것도 바꾸지 않았다' 고 하는데 떠 있는 라우터는 받는다(또는 그 거꾸로).
_QUOTED = re.compile(r"\"[^\"']*\"|'[^\"']*'")
_SPLIT = re.compile(r"[ \t\n\v\f\r,]+")
_ITEM = re.compile(r"(https?)://([A-Za-z0-9.-]+)(?::([0-9]{1,5}))?/v1")
_QUAD = re.compile(r"(0|[1-9][0-9]{0,2})\.(0|[1-9][0-9]{0,2})\.(0|[1-9][0-9]{0,2})\.(0|[1-9][0-9]{0,2})")
_NAME = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)*")
_DIGITS_DOTS = re.compile(r"[0-9.]+")
_SHAPE_PROBLEM = ("LLM_UPSTREAMS 의 공백·따옴표 모양이 틀렸다(따옴표 밖의 공백 · 짝이 없거나 여럿인 따옴표 · 따옴표 안의 따옴표) — "
                  "포털 start.sh 가 infra/.env 를 bash 로 소싱하다 그 줄에서 죽는다. 쉼표로만 나누거나 값 전체를 큰따옴표 한 쌍으로 감싼다")


def _ups_label(tok: str) -> str:
    """사유에 적을 '스킴://호스트'(못 알아보면 ?) — 칸 원문은 적지 않는다(질의·계정에 키가 들 수 있다). lib _hwax_llm_ups_label 과 같은 꼴."""
    scheme = host = "?"
    if "://" in tok:
        s, rest = tok.split("://", 1)
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9+.-]{0,15}", s):
            scheme = s
        rest = re.split(r"[/?#]", rest, maxsplit=1)[0].rsplit("@", 1)[-1]
        rest = re.sub(r":[0-9]*\Z", "", rest)
        if re.fullmatch(r"[A-Za-z0-9.-]{1,253}", rest):
            host = rest
    return f"{scheme}://{host}"


def _item_problem(url: str) -> str:
    if "@" in url:
        return "계정(user@)이 있다"
    if "?" in url or "#" in url:
        return "질의·조각(? #)이 있다"
    if "[" in url:
        return "IPv6 이다"
    if url.startswith(("http://", "https://")):
        return "쓸 수 있는 주소가 아니다(호스트 글자 · 포트 · 경로가 정확히 /v1 인지)"
    return "스킴이 소문자 http·https 가 아니다"


def _httpx_problem(url: str) -> str | None:
    """규칙을 지난 주소를 httpx 가 정말 받는지 — 나중에 요청마다 예외를 내는 칸이 목록에 들지 않게(검토 H1: 옥텟 256 이 InvalidURL)."""
    try:
        u = httpx.URL(url)
        _ = (u.host, u.port)                # host 는 xn-- 로 시작하면 idna 로 푼다 — 여기서 터져야 한다
        httpx.Request("GET", u.copy_with(raw_path=b"/metrics"))
    except Exception as exc:                # noqa: BLE001 — 무엇이든 이 칸을 못 쓴다는 뜻이다
        return f"httpx 가 받지 않는다({type(exc).__name__})"
    return None


# 칸 하나의 글자 상한 — lib(hwax_llm_pool_upstreams)과 같은 값이다. httpx 는 64KiB 넘는 주소를 못 만들어, 상한이 없으면 lib 만 받는 칸이 생긴다.
ITEM_MAX_CHARS = 2048


def parse_upstreams(raw: str | None, router_port: int | None = None) -> tuple[list[str], list[str]]:
    """LLM_UPSTREAMS 원문(따옴표를 남긴 값) → (서버 /v1 주소들, 틀린 까닭들). 틀린 칸이 하나라도 있으면 주소는 비고 까닭이 찬다 — 반만 맞는
    목록으로 보내지 않는다. 값이 비면 ([], []) — 꺼짐. router_port 는 고리(라우터 자신을 가리킴) 검사에 쓰고, None 이면 검사하지 않는다.
    끝 `/` 를 뗀 칸을 적힌 그대로 돌려준다(lib 와 같다)."""
    raw = raw or ""
    if '"' in raw or "'" in raw:
        if not _QUOTED.fullmatch(raw):
            return [], [_SHAPE_PROBLEM]
        inner = raw[1:-1]
    elif any(c in _WS for c in raw):
        return [], [_SHAPE_PROBLEM]
    else:
        inner = raw
    if not inner:
        return [], []
    toks = [t for t in _SPLIT.split(inner) if t]
    if not toks:
        return [], ["LLM_UPSTREAMS 에 주소가 하나도 없다(쉼표·공백뿐이다)"]
    good: list[str] = []
    problems: list[str] = []
    seen: set[tuple[str, str, int]] = set()
    for tok in toks:
        url = tok.rstrip("/")
        why: str | None = None
        m = _ITEM.fullmatch(url) if len(url) <= ITEM_MAX_CHARS else None
        if len(url) > ITEM_MAX_CHARS:
            why = f"{ITEM_MAX_CHARS:,}자를 넘는다"
        elif m is None:
            why = _item_problem(url)
        else:
            scheme, host, port = m.group(1), m.group(2), m.group(3)
            loop = False
            if _DIGITS_DOTS.fullmatch(host):
                q = _QUAD.fullmatch(host)
                if q is None or any(int(x) > 255 for x in q.groups()):
                    why = "IPv4 가 아니다(점 넷 · 칸마다 0~255 · 앞에 0 을 붙이지 않는다)"
                else:
                    loop = q.group(1) == "127" or host == "0.0.0.0"
            elif not _NAME.fullmatch(host) or any(lab[2:4] == "--" for lab in host.split(".")):
                why = "호스트 이름이 틀렸다(영숫자·하이픈 라벨 — 하이픈으로 시작·끝나지 않고 3·4번째가 -- 가 아니다)"
            else:
                host = host.lower()
                loop = host == "localhost"
            if why is None and port is not None and not 1 <= int(port) <= 65535:
                why = "포트가 1~65535 밖이다"
            if why is None:
                eport = int(port) if port is not None else (443 if scheme == "https" else 80)
                if loop and router_port is not None and eport == router_port:
                    why = f"라우터 자신을 가리킨다(포트 {router_port})"
                elif (scheme, host, eport) in seen:
                    why = "같은 서버가 두 번 있다(호스트의 대소문자 · 적지 않은 기본 포트는 같은 것이다)"
                else:
                    why = _httpx_problem(url)
                    if why is None:
                        seen.add((scheme, host, eport))
                        good.append(url)
        if why is not None:
            problems.append(f"LLM_UPSTREAMS 의 칸 {_ups_label(tok)} — {why}")
    return ([] if problems else good), problems


def router_port(vals: dict[str, str]) -> int | None:
    """라우터가 듣는 포트 — 띄우는 스크립트가 넘긴 환경 LLM_ROUTER_PORT(실제로 듣는 포트), 없으면 infra/.env, 없으면 8730.
    lib _hwax_llm_port 와 같은 모양(숫자 1~5자 · 1~65535)이 아니면 None — 고리 검사를 하지 않는다(lib 와 같다)."""
    raw = os.environ.get("LLM_ROUTER_PORT") or vals.get("LLM_ROUTER_PORT") or str(DEFAULT_ROUTER_PORT)
    return int(raw) if re.fullmatch(r"[0-9]{1,5}", raw) and 1 <= int(raw) <= 65535 else None


@dataclass(frozen=True)
class Config:
    upstreams: tuple[str, ...] = ()
    api_key: str | None = None
    scrape_s: float = 2.0
    sticky_slack: float = 2.0
    prefix_chars: int = 8000
    connect_timeout_s: float = 5.0
    cooldown_s: float = 15.0
    problems: tuple[str, ...] = ()
    upstreams_invalid: bool = False     # LLM_UPSTREAMS 가 있는데 틀렸다(빈 것과 다르다 — 알림 문구만 가른다)


def build_config(vals: dict[str, str], raw: dict[str, str] | None = None) -> Config:
    """vals = 따옴표를 지운 값(read_env), raw = 따옴표를 남긴 값(env_values(quotes=True)) — LLM_UPSTREAMS 의 모양은 raw 로 본다."""
    problems: list[str] = []
    knob: dict[str, float] = {}
    for key, (default, kind, floor) in KNOBS.items():
        val, v = vals.get(key), default
        if val is not None:
            try:
                f = float(val)
                if not math.isfinite(f) or f < floor:
                    raise ValueError
                v = int(f) if kind is int else f
            except ValueError:
                problems.append(f"{key}={val!r} 를 쓸 수 없어 기본값 {default:g} 로 둔다({floor:g} 이상의 수)")
        knob[key] = v
    ups, bad = parse_upstreams((vals if raw is None else raw).get("LLM_UPSTREAMS"), router_port(vals))
    problems += bad
    return Config(upstreams=tuple(ups), api_key=vals.get("LLM_API_KEY"), scrape_s=knob["LLM_ROUTER_SCRAPE_S"],
                  sticky_slack=knob["LLM_ROUTER_STICKY_SLACK"], prefix_chars=int(knob["LLM_ROUTER_PREFIX_CHARS"]),
                  connect_timeout_s=knob["LLM_ROUTER_CONNECT_TIMEOUT_S"], cooldown_s=knob["LLM_ROUTER_COOLDOWN_S"],
                  problems=tuple(problems), upstreams_invalid=bool(bad))


def config_from_text(text: str) -> Config:
    """infra/.env 글 → 설정. 라우터가 다시 읽을 때 쓰는 바로 그 길이다(정본 lib 와의 대조 시험도 이것을 부른다)."""
    raw = env_values(text, quotes=True)
    vals = {k: v for k, v in ((k, v.replace('"', "").replace("'", "")) for k, v in raw.items()) if v}
    return build_config(vals, raw)


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


def _model_list(r: httpx.Response) -> tuple[frozenset[str], tuple[tuple[str, object], ...]] | None:
    """/v1/models 의 200 답 → (모델 id 묶음, (id, max_model_len) 들). 모델 목록이 아니면(JSON 아님 · data 가 목록 아님 · id 하나 없음) None."""
    try:
        body = r.json()
    except (ValueError, RecursionError):
        return None
    data = body.get("data") if isinstance(body, dict) else None
    if not isinstance(data, list):
        return None
    rows = [(d["id"], d.get("max_model_len")) for d in data if isinstance(d, dict) and isinstance(d.get("id"), str) and d["id"]]
    if not rows:
        return None
    return frozenset(i for i, _ in rows), tuple(sorted(rows, key=lambda t: t[0]))


# ── 본문 — 붙임 열쇠 · 고른 모델 ─────────────────────────────────────────────────────────────────────
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


def body_info(body: bytes, prefix_chars: int) -> tuple[bytes | None, str | None]:
    """본문 → (붙임 열쇠, 고른 모델). 열쇠는 메시지 앞부분(PREFIX_CHARS 자)의 해시 — 같은 전문가의 카드 묶음 · 같은 대화가 같은 서버의 접두
    캐시를 다시 쓴다(LP-D2·D8). `messages` 면 `역할:내용` 을 차례로 이은 앞부분, `prompt` 면 그 앞부분. 모델은 본문의 `model`(글자)이다 —
    그 모델이 있는 서버를 먼저 고른다. JSON 이 아니거나 둘 다 없으면 None — 붙이지 않는다 · 모델을 가리지 않는다."""
    if not body.lstrip().startswith(b"{"):
        return None, None
    try:
        obj = json.loads(body)
    except (ValueError, RecursionError):
        return None, None
    if not isinstance(obj, dict):
        return None, None
    model = obj.get("model") if isinstance(obj.get("model"), str) and obj.get("model") else None
    text = _prefix_text(obj, prefix_chars) if prefix_chars > 0 else None
    key = None if text is None else hashlib.blake2b(text.encode("utf-8", "surrogatepass"), digest_size=16).digest()
    return key, model


def sticky_key(body: bytes, prefix_chars: int) -> bytes | None:
    return body_info(body, prefix_chars)[0] if prefix_chars > 0 else None


def _rank(key: bytes, url: str) -> int:
    """렌데부 해시 — 열쇠마다 서버 순위. 서버가 빠지거나 더해져도 다른 열쇠의 선호 서버는 그대로다."""
    return int.from_bytes(hashlib.blake2b(key + url.encode(), digest_size=8).digest(), "big")


def _read_timeout(exc: BaseException) -> bool:
    """연결은 됐는데 읽기·쓰기 한도를 넘겼다 — 연결 한도(ConnectTimeout)는 '연결 실패' 다(그 서버를 뺀다)."""
    return isinstance(exc, httpx.TimeoutException) and not isinstance(exc, httpx.ConnectTimeout)


def _cert_error(exc: BaseException) -> bool:
    """인증서 검증 실패인가 — httpx.ConnectError 의 원인 사슬 끝에 ssl.SSLCertVerificationError 가 있다."""
    e: BaseException | None = exc
    for _ in range(8):
        if e is None:
            break
        if isinstance(e, ssl.SSLCertVerificationError):
            return True
        e = e.__cause__ or e.__context__
    return "CERTIFICATE_VERIFY_FAILED" in str(exc)


# ── 서버 하나 ──────────────────────────────────────────────────────────────────────────────────────
class Upstream:
    """서버 하나의 상태 — 이벤트 루프에서만 만진다. url 은 parse_upstreams 를 지난 주소다(httpx 가 받는다)."""

    def __init__(self, url: str) -> None:
        self.url = url
        self.base = httpx.URL(url)                       # 요청 주소는 이것에서 조각으로 만든다(손님의 대상 글자를 이어 붙이지 않는다)
        self.metrics_url = self.base.copy_with(raw_path=b"/metrics")
        self.models_url = self.base.copy_with(raw_path=b"/v1/models")
        self.metrics: dict[str, float | None] | None = None
        self.metrics_at: float | None = None             # 지표를 마지막으로 제대로 읽은 시각
        self.metrics_fail = 0                            # 연달은 일시 실패(읽기 한도 · 끊김 · 5xx)
        self.metrics_note: str | None = None             # 마지막으로 알린 지표 상태 — 바뀔 때만 알린다
        self.scraped_at: float | None = None             # 지표 탐침이 마지막으로 서버에 닿은 시각
        self.loop_err_noted = False
        self.inflight = 0
        self.inflight_at_scrape = 0
        self.down_until = 0.0          # 연결 실패 뒤 이 시각까지 뺀다(지표 연결도 실패하면 다시 늘어난다)
        self.down_noted = False        # '내려감' 을 알렸고 아직 '올라옴' 을 못 알렸다
        self.downs = 0                 # 내려간 횟수 — 그 전에 시작한 모델 대조의 답은 버린다(옛 프로세스의 답일 수 있다)
        self.probe_timeouts = 0        # 탐침(지표 · 모델)이 연달아 읽기 한도를 넘긴 수 — 답이 오면(상태 코드와 상관없이) 0
        # 마지막으로 **답한** /v1/models 가 200 모델 목록이면 (ids, (id, max_model_len)…), 아니면 None — None 이면 '올라옴' 이 아니다.
        # 답이 없던 대조(읽기 한도 · 끊김)는 이것을 바꾸지 않는다. 내려가면 None(모름)으로 되돌린다 — 다시 올라오면 새로 묻는다.
        # models_error 는 마지막 대조의 실패(상태 코드 · 까닭)다.
        self.models: tuple[frozenset[str], tuple[tuple[str, object], ...]] | None = None
        self.models_error: int | str | None = None
        self.models_bad = False        # 마지막으로 답한 대조가 목록이 아니었다(/stats 의 models 'error' — 아직 답이 없으면 'unknown')
        self.sent = self.connect_fail = self.retried_away = self.sticky = self.overflow = 0

    def is_up(self, now: float) -> bool:
        """연결이 되는가(빼 둔 시간 밖) — '올라옴' 은 여기에 confirmed() 가 더해진다(Router._choose · health)."""
        return now >= self.down_until

    def confirmed(self) -> bool:
        """모델 목록을 확인했고 탐침에 답한다 — 연결(is_up)과 함께 '올라옴' 이다. 매달린 서버(연결은 되고 답이 없다)는 지표를 버린 뒤
        도는 수가 0 이라 가장 한가해 보이고 보낸 요청이 부르는 쪽의 한도까지 매달린다(검토 2라운드 LOW 1)."""
        return self.models is not None and self.probe_timeouts < PROBE_TIMEOUTS_DOWN

    def window(self, model: str | None) -> float:
        """그 모델(없으면 이 서버의 모델 전부)의 가장 큰 max_model_len — 수가 아니면(적지 않은 서버) -1, 아는 창보다 작은 것으로 친다."""
        lens = [n for mid, n in (self.models[1] if self.models else ()) if model is None or mid == model]
        return max((float(n) for n in lens if isinstance(n, (int, float)) and not isinstance(n, bool) and math.isfinite(n)), default=-1.0)

    def load(self) -> float:
        """마지막 지표의 running + waiting 에 '그 뒤로 이 라우터가 더 보낸 수'(0 아래는 0)를 더한다. 이 라우터가 지금 이 서버에 보내 도는
        수보다 작아지지 않는다 — vLLM 은 본문을 받고 토큰으로 바꾼 뒤에야 센다(1M 창이면 몇 초). 그 사이에 지표를 읽으면 그 요청들이 부하에서
        사라져 같은 서버로 또 몰린다(검토 L9). 지표가 없으면 보낸 수만."""
        if self.metrics is None:
            return float(self.inflight)
        seen = self.metrics["running"] + self.metrics["waiting"] + max(0, self.inflight - self.inflight_at_scrape)
        return max(seen, float(self.inflight))

    def kv(self) -> float:
        return (self.metrics or {}).get("kv") or 0.0


# ── 라우터 ─────────────────────────────────────────────────────────────────────────────────────────
class Router:
    """ASGI 앱 자체다. 기동(lifespan)에서 설정을 읽고 지표·모델을 한 바퀴 읽은 뒤(STARTUP_PROBE_S 까지만) 손님을 받는다."""

    def __init__(self, env_file: Path, *, log_to_stderr: bool = False) -> None:
        self.env_file = Path(env_file)
        self.log_to_stderr = log_to_stderr
        self.cfg = Config()
        self.ups: list[Upstream] = []
        self.inflight = 0
        self._seen: bytes | tuple | None = None    # 마지막으로 본 설정 파일 — 내용(bytes) 또는 못 읽은 모양(tuple, 알림은 모양마다 한 번)
        self._mtime: float | None = None
        self._client: httpx.AsyncClient | None = None
        self._probe: httpx.AsyncClient | None = None
        self._loops: dict[str, asyncio.Task] = {}
        self._tasks: list[asyncio.Task] = []
        self._rechecks: set[asyncio.Task] = set()   # 다시 올라온 서버 하나의 모델 대조(정기 대조를 기다리지 않는다)
        self._models_kick: asyncio.Event | None = None
        self._models_warned: str | None = None
        self._all_failed_noted = -math.inf
        self._running = False
        self.kept_last_list = False    # 파일의 목록이 비었거나 틀려 마지막 목록을 이어 쓰는 중(/health 에 싣는다)

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
        # 첫 지표·모델 대조를 함께 돌리고 STARTUP_PROBE_S 까지만 기다린다 — 그 안에 답한 것은 /health 가 처음부터 말하고, 답하지 않은 서버는
        # '모름'(올라온 서버가 없을 때만 쓴다)으로 둔 채 듣기 시작한다. 매달리거나 닿지 않는 서버 하나 때문에 재기동마다 라우터 포트가
        # 10~20초 닫혀 있으면 그동안의 LLM 호출이 전부 실패한다(검토 2라운드 M-C). 끝나지 않은 탐침은 끊지 않고 주기 탐침이 이어받는다.
        ups = list(self.ups)
        firsts = [asyncio.create_task(self._scrape(u)) for u in ups]
        check = asyncio.create_task(self._check_models())
        _, pending = await asyncio.wait([*firsts, check], timeout=STARTUP_PROBE_S)
        self._running = True
        for u, first in zip(ups, firsts, strict=True):
            self._start_loop(u, first=first)
        self._tasks = [asyncio.create_task(self._watch_config()), asyncio.create_task(self._models_loop(check)), *firsts, check]
        now = time.monotonic()
        LOG.info("기동 — 서버 %d곳(올라옴 %d) · 설정 %s%s", len(self.ups), sum(u.is_up(now) and u.confirmed() for u in self.ups), self.env_file,
                 f" · {STARTUP_PROBE_S:g}초 안에 답하지 않은 탐침 {len(pending)}개는 이어서 기다린다" if pending else "")

    async def stop(self) -> None:
        self._running = False
        tasks = [*self._tasks, *self._loops.values(), *self._rechecks]
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._loops.clear()
        self._rechecks.clear()
        for c in (self._client, self._probe):
            if c is not None:
                await c.aclose()

    # ── 설정 다시 읽기 ──
    def _reload(self, *, initial: bool = False) -> None:
        """주기마다 파일 **내용**을 견준다 — mtime·크기·inode 로 보면 같은 크기의 제자리 편집이 같은 시각 칸(NFS 1초)에 들면 영영 못 본다(검토 L12)."""
        try:
            data = self.env_file.read_bytes()
        except OSError as exc:
            # 못 읽은 것은 '모름' 이다 — 떠 있는 풀을 비우지 않는다(편집기의 바꿔치기 · 권한 실수 한 번에 모든 호출이 503 이 되지 않게).
            # 지워진 것도 같다. 알림은 못 읽은 모양마다 한 번(처음 None 이어도 알린다 — 지운 것이 조용히 지나가지 않게, 검토 L6).
            mark = ("unreadable", type(exc).__name__, exc.errno)
            if initial or mark != self._seen:
                LOG.warning("설정 파일을 읽지 못했다(%s: %s) — %s", self.env_file,
                            "없다(지워졌다)" if isinstance(exc, FileNotFoundError) else type(exc).__name__,
                            "보낼 서버가 없다" if initial else "마지막으로 읽은 설정을 그대로 쓴다")
            self._seen = mark
            return
        if not initial and data == self._seen:
            return
        self._seen = data
        try:
            self._mtime = round(self.env_file.stat().st_mtime_ns / 1e9, 3)
        except OSError:
            self._mtime = None
        cfg = config_from_text(data.decode("utf-8", errors="replace"))
        # 다시 읽은 목록이 비었거나 틀렸으면 마지막 목록으로 계속 보낸다. 풀을 끄는 것은 update-all 이다 — 사본을 직접 주소로 되돌리고 그 뒤에야
        # 라우터를 내리는데, 재기동이 미뤄진 손님(심의가 도는 에이전트 서버 · 바쁜 HEAX)은 그동안 이 라우터를 부른다. 빈 목록을 그대로 받으면
        # 그 호출이 전부 503 이 된다. 처음 읽을 때 비었거나 틀렸으면 그대로 503 이다(이어받을 목록이 없다).
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
                self._start_loop(u)
        for p in cfg.problems:
            LOG.warning("설정 — %s", p)
        what = "틀렸다(위 까닭 — 줄 전체를 받지 않는다)" if cfg.upstreams_invalid else "비었다"
        if self.kept_last_list:       # 다시 읽기는 파일 내용이 바뀔 때만 돈다 — 이 경고도 파일 내용마다 한 번이다
            LOG.warning("LLM_UPSTREAMS 가 %s(%s) — update-all 이 라우터를 내릴 때까지 마지막 목록 %d곳으로 계속 보낸다",
                        what, self.env_file, len(self.ups))
        elif not cfg.upstreams:
            LOG.warning("LLM_UPSTREAMS 가 %s(%s) — 보낼 서버가 없어 손님 요청은 503 이다", what, self.env_file)
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
    def _start_loop(self, u: Upstream, *, first: asyncio.Task | None = None) -> None:
        old = self._loops.pop(u.url, None)
        if old is not None:
            old.cancel()
        self._loops[u.url] = asyncio.create_task(self._scrape_loop(u, first))

    async def _scrape_loop(self, u: Upstream, first: asyncio.Task | None) -> None:
        """first — 기동 때 시작한 첫 탐침. 아직 돌면 끝나길 기다린다(같은 서버를 둘이 함께 찌르지 않게). 없으면(더해진 서버) 곧바로 읽는다."""
        while True:
            try:
                if first is not None:
                    await first
                else:
                    await self._scrape(u)
                u.loop_err_noted = False
            except Exception as exc:     # _scrape 안에서 가두지 못한 것 — 그 서버만 빼고, 같은 고장은 한 번만 길게 찍는다
                if not u.loop_err_noted:
                    LOG.exception("지표 읽기 실패 %s", u.url)
                    u.loop_err_noted = True
                self._mark_down(u, exc, where="뜻밖")
            first = None
            await asyncio.sleep(self.cfg.scrape_s)

    async def _scrape(self, u: Upstream) -> None:
        try:
            r = await self._probe.get(u.metrics_url, timeout=_probe_timeout(self.cfg.connect_timeout_s))
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            self._mark_down(u, exc, where="지표")
            return
        except httpx.HTTPError as exc:           # 닿기는 했다(읽기 한도 · 끊김) — 일시 실패, 마지막 지표를 이어 쓴다
            if _read_timeout(exc):
                self._probe_timed_out(u)
            self._metrics_miss(u, type(exc).__name__)
        except Exception as exc:                 # 뜻밖 — 이 서버만 나쁘다고 본다(라우터 전체로 번지지 않게)
            self._mark_down(u, exc, where="뜻밖")
            return
        else:
            self._probe_answered(u)
            if r.status_code == 200:
                m = parse_metrics(r.text)
                if m is None:
                    self._metrics_none(u, "지표 글이 vLLM 모양이 아니다")
                else:
                    self._metrics_ok(u, m)
            elif r.status_code >= 500:
                self._metrics_miss(u, f"HTTP {r.status_code}")
            else:
                self._metrics_none(u, f"HTTP {r.status_code}")
        now = time.monotonic()
        u.scraped_at = now
        if u.down_noted and u.is_up(now):
            u.down_noted = False
            LOG.info("서버 올라옴 %s — 지표 탐침이 다시 닿는다 · 모델 목록을 다시 확인한다(그때까지 다른 서버가 없을 때만 쓴다)", u.url)
            # 내려갈 때 모델 목록을 '모름' 으로 되돌렸다 — 다른 --served-model-name 으로 다시 뜬 vLLM 을 옛 목록으로 올라옴으로 치면 곧바로
            # 404 를 내 가장 한가해 보인다(검토 2라운드 M-B). 정기 대조(60초)나 매달린 서버를 기다리는 대조 뒤에 줄 세우지 않고 이 서버만 곧바로 묻는다.
            if self._running:
                t = asyncio.create_task(self._recheck(u))
                self._rechecks.add(t)
                t.add_done_callback(self._rechecks.discard)

    def _metrics_ok(self, u: Upstream, m: dict) -> None:
        u.metrics, u.metrics_at, u.metrics_fail, u.inflight_at_scrape = m, time.monotonic(), 0, u.inflight
        if u.metrics_note not in (None, "ok"):
            LOG.info("지표 다시 읽힘 %s — 지표로 잰다", u.url)
        u.metrics_note = "ok"

    def _metrics_none(self, u: Upstream, why: str) -> None:
        """vLLM 지표가 없다(404 · vLLM 모양이 아닌 글) — 곧바로 이 라우터가 보낸 도는 수로만 잰다."""
        u.metrics, u.metrics_fail = None, 0
        if u.metrics_note != why:
            LOG.warning("지표 없음 %s — %s · 이 라우터가 보낸 도는 수로만 잰다", u.url, why)
            u.metrics_note = why

    def _metrics_miss(self, u: Upstream, why: str) -> None:
        """일시 실패(읽기 한도 · 끊김 · 5xx) — 바쁜 서버는 /metrics 도 늦다. 그때 마지막 지표를 버리면 가장 바쁜 서버가 가장 한가해 보여 요청이
        몰린다(검토 M2). 그래서 METRICS_KEEP_FAILS 번째 연달은 실패까지는 마지막 지표를 쓰고(/stats 의 metrics_age_s 가 그 나이), 그 뒤에 버린다."""
        u.metrics_fail += 1
        if u.metrics_fail < METRICS_KEEP_FAILS:
            return
        note = "lost"
        if u.metrics is not None or u.metrics_note != note:
            age = "" if u.metrics_at is None else f" · 마지막 지표 {time.monotonic() - u.metrics_at:.0f}초 전"
            LOG.warning("지표를 %d번 연달아 못 읽었다 %s — %s%s · 이 라우터가 보낸 도는 수로만 잰다", u.metrics_fail, u.url, why, age)
        u.metrics, u.metrics_note = None, note

    def _probe_timed_out(self, u: Upstream) -> None:
        """탐침(지표 · 모델)이 읽기 한도를 넘겼다 — 연결은 됐는데 답이 없다. PROBE_TIMEOUTS_DOWN 번 연달으면 다시 답할 때까지 '올라옴' 이 아니다
        (매달린 vLLM — API 프로세스는 받는데 답하지 않는다. 그리 보낸 요청은 부르는 쪽의 한도까지 매달린다, 검토 2라운드 LOW 1)."""
        u.probe_timeouts += 1
        if u.probe_timeouts == PROBE_TIMEOUTS_DOWN:
            LOG.warning("서버 응답 없음 %s — 탐침(지표·모델)이 %d번 연달아 읽기 한도(%g초)를 넘겼다 · 다시 답할 때까지 '올라옴' 으로 치지 않는다"
                        "(올라온 서버가 따로 있으면 보내지 않는다)", u.url, u.probe_timeouts, PROBE_READ_S)

    def _probe_answered(self, u: Upstream) -> None:
        """탐침에 답이 왔다(상태 코드와 상관없이 — 답하는 서버다)."""
        if u.probe_timeouts >= PROBE_TIMEOUTS_DOWN:
            LOG.info("서버 다시 답함 %s — 탐침에 답이 왔다", u.url)
        u.probe_timeouts = 0

    def _mark_down(self, u: Upstream, exc: BaseException, *, where: str) -> None:
        """연결 실패(또는 이 서버에서 난 뜻밖의 예외) — COOLDOWN_S 동안 뺀다. 지표 연결이 실패할 때마다 다시 늘어나므로 죽은 서버는 계속 빠져
        있고, 지표가 다시 읽히기 시작하면 빼 둔 시간이 지난 뒤 돌아온다('올라옴' 은 그 뒤 첫 지표에서 알린다). connect_fail 은 손님 요청의
        연결 실패만 센다. 알림은 내려갈 때 한 번 — 인증서 검증 실패는 따로 말한다(사설 CA 는 받지 않는다).
        내려갈 때 모델 목록을 '모름' 으로 되돌린다 — 다시 올라오면 그 서버만 곧바로 다시 묻고, 그때까지는 올라온 서버가 없을 때만 쓴다. 빼 둔
        시간이 지나는 순간과 다음 지표 사이에 옛 목록으로 '올라옴' 이 되는 틈이 없게 올라올 때가 아니라 내려갈 때 지운다(검토 2라운드 M-B)."""
        if where == "요청":
            u.connect_fail += 1
        u.down_until = time.monotonic() + self.cfg.cooldown_s
        if not u.down_noted:
            u.down_noted = True
            u.downs += 1
            u.models, u.models_bad = None, False
            if _cert_error(exc):
                LOG.warning("서버 내려감 %s — TLS 인증서를 믿을 수 없다(%s 연결 · %s) · 라우터는 사설 CA 를 믿지 않는다 — 위 서버는 http 이거나 "
                            "공인 인증서의 https 여야 한다 · %g초 동안 뺀다", u.url, where, type(exc).__name__, self.cfg.cooldown_s)
            elif where == "뜻밖":
                LOG.warning("서버 내려감 %s — 뜻밖의 오류(%s) · 이 서버만 %g초 동안 뺀다(지표가 다시 읽힐 때까지)", u.url, type(exc).__name__,
                            self.cfg.cooldown_s)
            else:
                LOG.warning("서버 내려감 %s — %s 연결 실패(%s) · %g초 동안 뺀다(지표 연결이 실패하는 동안은 계속)", u.url, where,
                            type(exc).__name__, self.cfg.cooldown_s)

    # ── 모델 대조 ──
    async def _models_loop(self, first: asyncio.Task | None = None) -> None:
        """first — 기동 때 시작한 첫 대조(매달린 서버가 있으면 그 읽기 한도까지 이어 돈다). 그 뒤로 MODELS_EVERY_S 마다 또는 깨울 때."""
        if first is not None:
            try:
                await first
            except Exception:
                LOG.exception("모델 대조 실패")
        while True:
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self._models_kick.wait(), MODELS_EVERY_S)
            self._models_kick.clear()
            try:
                await self._check_models()
            except Exception:
                LOG.exception("모델 대조 실패")

    async def _recheck(self, u: Upstream) -> None:
        try:
            await self._check_models([u])
        except Exception:
            LOG.exception("모델 대조 실패 %s", u.url)

    async def _check_models(self, ups: list[Upstream] | None = None) -> None:
        """서버마다 /v1/models — 200 모델 목록이면 그 서버는 '올라옴' 이 될 수 있고, 답했는데 목록이 아니면(401 · 404 · 다른 글) 아니다.
        답이 없으면(읽기 한도 · 끊김) 지난 답을 그대로 둔다. 실패는 서버마다 바뀔 때 한 번 알리고 /health 의 models.errors 에 싣는다(검토 L7).
        답은 서버마다 오는 대로 적는다 — 매달린 서버 하나가 다른 서버의 확인을 읽기 한도(10초)만큼 붙들지 않게. ups 를 주면 그 서버만 묻는다."""
        ups = list(self.ups) if ups is None else ups
        hdrs = {"Authorization": f"Bearer {self.cfg.api_key}"} if self.cfg.api_key else {}
        await asyncio.gather(*(self._check_one(u, hdrs) for u in ups))
        summary = self._models_summary()
        sig = json.dumps({k: summary[k] for k in ("match", "ids", "max_model_len")}, sort_keys=True, ensure_ascii=False, default=str)
        if summary["match"] is False and sig != self._models_warned:
            self._models_warned = sig
            LOG.warning("모델 어긋남 — 서버마다 모델 id 또는 max_model_len 이 다르다(같은 모델·같은 창이어야 한다, LP-D6): ids=%s max_model_len=%s"
                        " · 같은 모델이면 창이 가장 큰 서버로만 보낸다(작은 창 서버는 그 서버가 올라와 있지 않을 때만)",
                        json.dumps(summary["ids"], ensure_ascii=False), json.dumps(summary["max_model_len"], default=str))
        elif summary["match"] is True and self._models_warned is not None:
            self._models_warned = None
            LOG.info("모델 같아짐 — ids=%s max_model_len=%s", json.dumps(summary["ids"], ensure_ascii=False), summary["max_model_len"])

    async def _check_one(self, u: Upstream, hdrs: dict[str, str]) -> None:
        downs = u.downs
        try:
            r = await self._probe.get(u.models_url, headers=hdrs, timeout=_probe_timeout(self.cfg.connect_timeout_s))
        except Exception as exc:                 # noqa: BLE001 — 답이 없다(연결 · 읽기 한도 · 끊김 · 뜻밖) — 지난 답을 그대로 둔다
            if u.downs == downs:
                if _read_timeout(exc):
                    self._probe_timed_out(u)
                self._models_failed(u, type(exc).__name__, answered=False)
            return
        if u.downs != downs:                     # 묻는 사이에 내려갔다 — 옛 프로세스의 답일 수 있다(다시 올라오면 새로 묻는다)
            return
        self._probe_answered(u)
        if r.status_code != 200:
            self._models_failed(u, r.status_code, answered=True)
        elif (got := _model_list(r)) is None:
            self._models_failed(u, "not-a-model-list", answered=True)
        else:
            u.models, u.models_bad = got, False
            if u.models_error is not None:
                LOG.info("모델 목록 다시 읽힘 %s — %s", u.url, ", ".join(sorted(got[0])))
                u.models_error = None

    def _models_failed(self, u: Upstream, code: int | str, *, answered: bool) -> None:
        if answered:
            u.models, u.models_bad = None, True     # 답했는데 목록이 아니다 — 지난 목록은 이제 사실이 아니다
        if u.models_error != code:
            u.models_error = code
            hint = " · LLM_API_KEY(infra/.env)를 본다 — 라우터는 자기 대조에만 그 키를 쓴다" if code in (401, 403) else ""
            LOG.warning("모델 목록을 못 읽었다 %s — %s · %s%s", u.url, f"HTTP {code}" if isinstance(code, int) else code,
                        "이 서버를 '올라옴' 으로 치지 않는다(올라온 서버가 따로 있으면 보내지 않는다)" if answered
                        else "답이 없다 — 지난 답을 그대로 쓴다", hint)

    def _models_summary(self) -> dict:
        errors = {u.url: u.models_error for u in self.ups if u.models_error is not None}
        known = [(u.url, u.models) for u in self.ups if u.models is not None]
        if not known:
            return {"match": None, "ids": [], "max_model_len": None, "errors": errors}
        first = known[0][1]
        if all(m == first for _, m in known):
            lens = dict(first[1])
            vals = set(map(str, lens.values()))
            return {"match": True, "ids": sorted(first[0]),
                    "max_model_len": next(iter(lens.values())) if len(vals) == 1 else lens, "errors": errors}
        return {"match": False, "ids": {url: sorted(m[0]) for url, m in known},
                "max_model_len": {url: dict(m[1]) for url, m in known}, "errors": errors}

    # ── 라우터 자신의 끝점 ──
    def health(self) -> tuple[dict, int]:
        """upstreams_up 은 '올라옴'(연결이 되고 모델 목록을 줬고 탐침에 답하는) 서버 수다 — update-all 1i 는 이것이 1 이상일 때만 사본을 라우터로 바꾼다.
        status 는 down(연결되는 서버가 없다 — 503) · degraded(올라오지 않은 서버가 있거나 모델이 다르다) · ok. upstreams_reachable 은 연결만 되는
        수다(올라온 서버가 없어도 연결되는 서버로는 보낸다). kept_last_list 는 status 를 바꾸지 않는다 — 파일의 목록과 쓰는 목록이 다르다는
        사실만 알린다(update-all 이 라우터를 내릴 차례인지 보는 데 쓴다)."""
        now = time.monotonic()
        reach = [u for u in self.ups if u.is_up(now)]
        up = sum(u.confirmed() for u in reach)
        models = self._models_summary()
        status = "down" if not reach else "degraded" if (up < len(self.ups) or models["match"] is False) else "ok"
        return ({"status": status, "upstreams_total": len(self.ups), "upstreams_up": up, "upstreams_reachable": len(reach),
                 "inflight": self.inflight, "models": models, "config_mtime": self._mtime, "kept_last_list": self.kept_last_list},
                503 if status == "down" else 200)

    def stats(self) -> list[dict]:
        now = time.monotonic()
        out = []
        for u in self.ups:
            m = u.metrics or {}
            out.append({"url": u.url, "up": u.is_up(now) and u.confirmed(), "reachable": u.is_up(now),
                        "models": "ok" if u.models is not None else ("error" if u.models_bad else "unknown"),
                        "models_error": u.models_error, "probe_timeouts": u.probe_timeouts,
                        "running": m.get("running"), "waiting": m.get("waiting"), "kv": m.get("kv"),
                        "metrics_age_s": None if u.metrics is None or u.metrics_at is None else round(now - u.metrics_at, 3),
                        "metrics_fail": u.metrics_fail,
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
    def _choose(self, key: bytes | None, model: str | None, tried: list[Upstream]) -> tuple[Upstream, str, Upstream | None] | None:
        """후보 — 시도하지 않은 서버 가운데 연결되는 것(모두 빠졌으면 전부를 다시 시도해 본다 — 멀쩡해졌을 수 있다), 그 가운데 '올라옴'
        (모델 목록 확인 · 탐침에 답함 — confirmed)인 것. 요청이 모델을 적었으면 그 모델이 있는 것(없으면 올라온 서버 전부), 그 가운데 그 모델의
        창(max_model_len — 모델을 적지 않았거나 어디에도 없으면 서버의 가장 큰 창)이 가장 큰 것만 — 작은 창 서버는 큰 창 서버가 올라와 있는
        동안 쓰지 않는다. 올라온 서버가 하나도 없을 때만 나머지(모름 · 목록 아님 · 답 없음 — 답하는 서버 먼저)를 쓴다. 빨리 실패하는 서버
        (다른 모델로 다시 뜬 vLLM · 엉뚱한 포트의 다른 앱 · 긴 요청을 곧바로 400 으로 내는 작은 창)는 도는 수가 늘 0 이라 가장 한가해 보인다 —
        그래서 부하보다 먼저 거른다(검토 M1·M5 · 2라운드 M-A)."""
        now = time.monotonic()
        rest = [u for u in self.ups if u not in tried]
        live = [u for u in rest if u.is_up(now)] or rest
        if up := [u for u in live if u.confirmed()]:
            serving = [u for u in up if model is not None and model in u.models[0]]
            pool, want = (serving, model) if serving else (up, None)
            widest = max(u.window(want) for u in pool)
            cands = [u for u in pool if u.window(want) == widest]
        else:
            cands = [u for u in live if u.probe_timeouts < PROBE_TIMEOUTS_DOWN] or live
            if model is not None:
                cands = [u for u in cands if u.models is not None and model in u.models[0]] or cands
        if not cands:
            return None
        best = min(cands, key=lambda u: (u.load(), u.kv(), self.ups.index(u)))
        if key is None:
            return best, "least", None
        pref = max(cands, key=lambda u: _rank(key, u.url))
        if pref is best or pref.load() - best.load() < self.cfg.sticky_slack:
            return pref, "sticky", pref
        return best, "overflow", pref

    async def _body_info(self, body: bytes) -> tuple[bytes | None, str | None]:
        if len(body) > BIG_BODY:
            return await asyncio.to_thread(body_info, body, self.cfg.prefix_chars)
        return body_info(body, self.cfg.prefix_chars)

    async def _proxy(self, scope, receive, send) -> None:
        # 대상은 `/` 로 시작하는 경로만 — 위 주소는 서버 주소의 조각에 이 경로를 끼워 만든다. 이어 붙이면 `GET @다른호스트:포트/…`(h11 이
        # 받는다)가 목록 밖 호스트로 가고 손님의 Bearer 가 Basic 으로 바뀐다(검토 L4).
        target = scope.get("raw_path") or scope["path"].encode("utf-8")
        if scope.get("query_string"):
            target += b"?" + scope["query_string"]
        if not _target_ok(target):
            await _send_json(send, 400, _error("LLM 라우터: 요청 대상은 `/` 로 시작하는 경로여야 한다", "llm_router_bad_target", 400))
            return
        chunks = []
        while True:
            msg = await receive()
            if msg["type"] == "http.disconnect":
                return                          # 올리는 중에 떠났다 — 위로 보낸 것이 없다
            chunks.append(msg.get("body", b""))
            if not msg.get("more_body"):
                break
        body = b"".join(chunks)
        # 도는 수는 본문을 다 받은 뒤에 센다 — 멈춘 올리기(LLM 호출이 아니다)가 /health 의 inflight 를 붙들면 update-sites 가 라우터 재기동을
        # 영영 미룬다(검토 L8).
        self.inflight += 1
        try:
            key, model = await self._body_info(body)
            started = False

            async def send_(msg) -> None:
                nonlocal started
                if msg["type"] == "http.response.start":
                    started = True
                await send(msg)

            work = asyncio.create_task(self._forward(scope, target, body, key, model, send_))
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
                try:
                    work.result()
                except Exception:                # 서버마다 가뒀는데도 샌 것 — 이 요청만 502, 라우터 전체가 500 이 되지 않게
                    LOG.exception("넘기다 뜻밖의 오류")
                    if not started:
                        await _send_json(send, 502, _error("LLM 라우터: 넘기다 뜻밖의 오류가 났다 — 다시 보내지 않는다", "llm_router_error", 502))
                return
            # 손님이 먼저 떠났다 — 일을 취소하면 위 연결이 닫히고(머리 전이든 흐르는 중이든) vLLM 이 생성을 멈춘다.
            work.cancel()
            await asyncio.gather(work, return_exceptions=True)
        finally:
            self.inflight -= 1

    async def _forward(self, scope, target: bytes, body: bytes, key: bytes | None, model: str | None, send) -> None:
        # 머리는 손님 것만 — httpx.Request 를 직접 만든다. client.build_request 는 클라이언트 기본 머리(user-agent · accept ·
        # accept-encoding: gzip)를 덧붙여 손님이 청하지 않은 gzip 이 돌아온다(검토 L3). Authorization 은 손님 것 그대로(없으면 없는 채로 — LP-D9).
        headers = _filter_headers(scope["headers"], _REQ_DROP)
        ext = {"timeout": _proxy_timeout(self.cfg.connect_timeout_s).as_dict()}
        tried: list[Upstream] = []
        failed: Upstream | None = None
        while (pick := self._choose(key, model, tried)) is not None:
            u, how, pref = pick
            if failed is not None:
                failed.retried_away += 1
            tried.append(u)
            try:
                req = httpx.Request(scope["method"], u.base.copy_with(raw_path=target), headers=headers, content=body, extensions=ext)
            except Exception as exc:          # noqa: BLE001 — 이 서버 주소로 요청을 못 만든다 — 보낸 것이 없으니 다음 서버로
                self._mark_down(u, exc, where="뜻밖")
                failed = u
                continue
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
                    self._mark_down(u, exc, where="요청")
                    failed = u
                    continue
                except httpx.HTTPError as exc:
                    # 연결은 됐다 — 닿았을 수 있으니 다시 보내지 않는다(LP-D3)
                    LOG.warning("응답 머리 전에 끊김 %s — %s · 다시 보내지 않는다", u.url, type(exc).__name__)
                    await _send_json(send, 502, _error(f"LLM 라우터: 위 서버가 응답 머리를 보내기 전에 끊겼다({type(exc).__name__}) — "
                                                       "다시 보내지 않는다(생성이 시작됐을 수 있다)", "llm_router_upstream_broken", 502))
                    return
                except Exception as exc:          # noqa: BLE001 — 뜻밖: 보냈는지 모른다 — 이 서버는 빼되 다시 보내지 않는다(LP-D3)
                    self._mark_down(u, exc, where="뜻밖")
                    await _send_json(send, 502, _error(f"LLM 라우터: 위 서버에 보내다 뜻밖의 오류가 났다({type(exc).__name__}) — "
                                                       "다시 보내지 않는다", "llm_router_upstream_error", 502))
                    return
                await self._relay(resp, send, u)
                return
            finally:
                u.inflight -= 1
        if not self.ups:
            why = "틀렸다(로그의 까닭)" if self.cfg.upstreams_invalid else "비어 있다"
            await _send_json(send, 503, _error(f"LLM 라우터: LLM_UPSTREAMS 가 {why}({self.env_file}) — 보낼 서버가 없다",
                                               "llm_router_no_upstreams", 503))
            return
        now = time.monotonic()
        if now - self._all_failed_noted >= max(self.cfg.cooldown_s, 1.0):     # 장애 동안 요청마다 찍지 않는다
            self._all_failed_noted = now
            LOG.warning("모든 서버 연결 실패 — %d곳 · 손님에게 502", len(tried))
        await _send_json(send, 502, _error(f"LLM 라우터: 서버 {len(tried)}곳에 모두 연결하지 못했다", "llm_router_upstream_unreachable", 502))

    async def _relay(self, resp: httpx.Response, send, u: Upstream) -> None:
        broken: BaseException | None = None
        try:
            await send({"type": "http.response.start", "status": resp.status_code,
                        "headers": _filter_headers(resp.headers.raw, _RESP_DROP)})
            async for chunk in resp.aiter_raw():       # 받은 바이트 그대로(압축도 풀지 않는다) — 오는 대로 흘린다
                if chunk:
                    await send({"type": "http.response.body", "body": chunk, "more_body": True})
        except Exception as exc:                       # noqa: BLE001 — httpx 의 끊김이든 뜻밖이든 손님에게는 끊김이다
            broken = exc
        finally:
            await resp.aclose()                        # 다 읽었든 끊겼든 취소됐든 위 연결을 닫는다
        if broken is not None:
            # 생성 중 끊김은 손님에게도 끊김으로 보인다 — 끝맺지 않고 돌아가면 서버가 연결을 닫는다(정상 끝처럼 보이면 잘린 답을 믿는다).
            LOG.warning("생성 중 끊김 %s — %s · 손님 연결도 끊는다(다시 보내지 않는다)", u.url, type(broken).__name__)
            return
        await send({"type": "http.response.body", "body": b"", "more_body": False})


# ── 도움 ───────────────────────────────────────────────────────────────────────────────────────────
def _target_ok(target: bytes) -> bool:
    """요청 대상이 `/` 로 시작하고 httpx 주소의 경로 조각이 되는가(조각 `#` · 비 ASCII 는 안 된다) — 서버와 상관없이 본다(손님 탓을 서버 탓으로
    돌려 서버를 빼지 않게)."""
    if not target.startswith(b"/"):
        return False
    try:
        _TARGET_CHECK.copy_with(raw_path=target)
    except Exception:       # noqa: BLE001
        return False
    return True


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
    data = json.dumps(obj, ensure_ascii=False, default=str).encode()
    await send({"type": "http.response.start", "status": status,
                "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(data)).encode())]})
    await send({"type": "http.response.body", "body": b"" if head else data})


def make_app(env_file: Path | str | None = None, *, log_to_stderr: bool = False) -> Router:
    return Router(Path(env_file or os.environ.get("LLM_ROUTER_ENV_FILE") or DEFAULT_ENV_FILE), log_to_stderr=log_to_stderr)


app = make_app(log_to_stderr=True)
