#!/usr/bin/env python3
# 상시 상태판(Gatus) 설정을 매니페스트·infra/.env·포털 메일 설정에서 만드는 생성기 — infra/.state/status/config.yaml(디렉터리 700 · 파일 600)
"""상시 상태판 설정 생성기 — docs/improvement-1015/status-board.md

    python3 ./infra/scripts/gen-status-config.py      # update-all 5b 가 STATUS_BOARD 가 있으면 매번 부른다(걸린 경보 멈춤도 푼다)
    python3 ./infra/scripts/gen-status-config.py --pause 60          # 경보 멈춤 — update-all 1b2 가 1c~§5 재기동 앞에서
    python3 ./infra/scripts/gen-status-config.py --unpause           # 멈춤을 푼다 — update-all 이 5b 전에 멈췄을 때
    python3 ./infra/scripts/gen-status-config.py --unpause-if-expired  # 시한이 지난 멈춤만 푼다 — 밀어 넣는 쪽(status-push.py)이

무엇을 보나
  · 이 박스가 다루는 서비스(services.py 의 enabled_here — only_on · unless_env · if_env)의 **리스너 전부**(health + urls, services.py 의
    service_urls 와 같은 목록 · 같은 `${KEY:-기본}` 풀이). 인스턴스가 아니라 리스너의 응답을 본다 — 포털 인스턴스는 '떠 있음' 인데 안의
    백엔드만 죽은 2026-10-16 사례(IM-D4)가 까닭이다. 상태판 자신은 보지 않는다(죽으면 이 화면도 없다).
  · 조건 — 연결이 되고, 매니페스트에 expect 가 있으면 그 코드, 없으면 5xx 가 아니다(services.py 는 응답만 오면 산 것으로 치는데, 5xx 는
    프록시가 죽은 뒤를 대신 답한 것이다). 연결 조건을 빼면 연결 실패(상태 0)가 '5xx 아님' 으로 초록이 된다(Gatus 는 호출 오류만으로 실패로
    치지 않는다 — v5.37.0 원문).
  · 게이트웨이 /health — status ok · 도구 수 · 백엔드마다 `!= false`(이름이 경보 본문에 찍힌다). 이름은 지금 떠 있는 게이트웨이에서 읽는다
    (HEAX 앱 백엔드는 허브 등록으로 그때그때 생긴다). 사라진 백엔드는 `!= false` 라 실패로 치지 않는다. 생성 뒤에 생긴 백엔드는
    `!= pat(*:false*)` 한 줄이 잡는다(하나라도 false 면 실패). 게이트웨이가 답하지 않으면 그 한 줄만 싣는다.
  · 에이전트 서버 /health — status ok · 도는 심의·줄 선 심의 수(update-all·start.sh 가 재기동을 미루는 근거 칸 — 없으면 옛 판이다).
  · LLM 라우터 /health — 풀을 켠 박스만(llm-router 항목의 if_env: LLM_UPSTREAMS) status ok · models.match == true · 올라온 서버 수.
  · MX 백서 위키 워커 — 리스너가 없어 API 의 /api/v1/wiki/health 로 본다(최근 10분 안에 박동한 워커가 있고 맨 앞이 stopped 가 아니다 ·
    줄 선 작업 · 24시간 실패 수). 이 박스의 MXWhitePaper 에 워커가 있는 판(위키 W3 뒤)만 싣는다(docs/mxwp-wiki P9).
  · 끝점마다 성공한 조건도 값을 풀어 보인다(resolve-successful-conditions) — 도구 수 · 도는 심의 수가 화면에 숫자로 보인다.
경보(메일) — infra/.env 의 STATUS_ALERT_TO(팀 공용 주소, 쉼표로 여럿) **와** 포털 backend/.env 의 SMTP 설정(MAIL_BACKEND=smtp · SMTP_HOST ·
  MAIL_FROM · SMTP_PORT(기본 587) · SMTP_USERNAME · SMTP_PASSWORD · SMTP_STARTTLS)이 다 있을 때만 싣는다(IM-D6). 포털에 맡기지 않는다 —
  포털이 죽은 순간 경보도 죽는다(IM-D3). 자격은 이 생성 파일(600)에만 쓴다 — 화면·로그에 찍지 않는다. STATUS_ALERT_TO 는 있는데 메일을 못
  꾸리면 화면만 띄우고 종료코드 3 으로 알린다(update-all 은 ⚠). backend/.env 는 포털이 읽는 규칙(pydantic-settings → python-dotenv: 키 대소문자
  무시 · 마지막 줄 · 따옴표 · 공백 뒤 `#` 주석 · `${이름}`)으로 읽는다. SMTP_STARTTLS=false 면 Gatus 가 STARTTLS 를 끌 수단이 없어(서버가
  내밀면 쓴다) 검증을 끈다 — 포털이 평문으로 보내는 박스에서 Gatus 가 인증서 검증에 막혀 조용히 못 보내는 것보다 낫다.
Gatus 는 설정 글 전체에서 `$이름` 을 환경변수로 푼다 — 값의 `$` 는 전부 `$$` 로 적는다(Gatus 가 `$` 로 되돌린다). 안 그러면 `$` 가 든
  비밀번호가 조용히 잘린다.
같은 내용이면 파일을 다시 쓰지 않는다 — Gatus 는 파일 시각이 바뀌면 다시 읽고, update-sites 는 내용 지문으로 재기동을 정한다.

2단계(IM-D24~) —
  · 기록 보존 — sqlite(infra/.state/status/data/gatus.db, 컨테이너 /data). 메모리 저장소는 설정을 다시 읽을 때마다 기록과 **경보 상태**를
    잃어 울린 경보의 풀림 메일이 오지 않았다(v5.37.0 실측). sqlite 면 다시 읽기·재기동을 넘어 이어진다.
  · 스크립트 검사 — Gatus 가 직접 못 보는 둘을 외부 끝점(external-endpoints)으로 싣고, 밀어 넣는 쪽(status-push.py)이 쓸 것을
    infra/.state/status/push.json(600 — 밀어 넣기 토큰)에 쓴다. MCP 실호출(mcp-smoke --periodic, 30분)은 게이트웨이가 이 박스 대상이고
    에이전트 서버 venv 가 있을 때, Drive latest/ 따라옴(60분)은 rclone 과 Drive 리모트(drive-drift 와 같은 셋)가 있을 때만 싣는다.
    밀어 넣기가 끊기면 heartbeat 가 실패로 친다(밀어 넣는 쪽이 죽은 것도 잡는다). 메일 본문에는 밀어 넣은 사유가 실리지 않아(실측)
    설명에 사유를 보는 곳을 적는다. 토큰은 처음 한 번 만들고 다시 쓴다(같은 내용이면 다시 쓰지 않는다를 지키려고).
  · 경보 멈춤 — 설정을 읽어 maintenance 칸만 넣고 뺀다(전체를 다시 만들면 손잡이가 틀린 박스에서 못 걸고, 못 풀면 창이 남는다).
    창은 UTC · 그날 요일(영어 — 로캘 요일은 Gatus 가 거부한다) · 분 단위이고 Gatus 는 요일마다 되풀이한다 — 그래서 시한을
    pause.json 에 적고, 시한이 지나면 밀어 넣는 쪽이 --unpause-if-expired 로 걷어낸다. 일반 생성(5b)은 늘 멈춤을 푼다.
  모든 실행은 infra/.state/status/.gen.lock 을 잡는다(밀어 넣는 쪽의 걷어내기와 update-all 의 걸기가 겹치지 않게).

종료코드 — 0 썼다(또는 그대로) · 2 손잡이 값이 틀렸다(쓰지 않았다 — 옛 설정이 그대로 돈다) · 3 썼는데 경보를 못 켰다 · 1 그 밖의 실패.
"""

import argparse
import codecs
import contextlib
import fcntl
import importlib.util
import json
import os
import re
import secrets
import shutil
import tempfile
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "infra" / ".state" / "status"
OUT = STATE / "config.yaml"
DATA = STATE / "data"          # sqlite — status-board.sh 가 컨테이너 /data 로 쓰기 바인드한다
PUSH = STATE / "push.json"     # 밀어 넣는 쪽(status-push.py)이 읽는다 — 토큰이 들어 600
PAUSE = STATE / "pause.json"   # 경보 멈춤의 시한 — 밀어 넣는 쪽이 지난 것을 걷어낸다
LOCK = STATE / ".gen.lock"
RUNBOOK = "docs/improvement-1015/status-board.md"
SELF = "status-board"
DEFAULT_PORT = 8740            # 9100~9999 는 HEAXHub 가 앱마다 그때그때 나눠 주는 포트 풀이다(docs/PORT-MAP.md)
DEFAULT_INTERVAL = "1m"
FAILURES = 5                   # 연속 실패 수 — 주기 1분이면 5분. update-all 의 재기동(대개 1~2분)으로는 메일이 나가지 않게
SUCCESSES = 2                  # 다시 살아난 것으로 치는 연속 성공 수(풀림 메일)
GATEWAY, AGENT, ROUTER = "mcp-gateway", "agent-server", "llm-router"
# MX 백서 위키 워커(인스턴스 mxwp_wiki — MXWhitePaper docs/llm-wiki W3). 그 리포에 워커가 있는 판만 본다(docs/mxwp-wiki P9).
MXWP, MXWP_REPO = "mx-white-paper", "MXWhitePaper"
_MXWP_WIKI_HEALTH = "/api/v1/wiki/health"
_MXWP_WIKI_WORKER = Path("apps/api/app/wiki/worker.py")
_NAME_OK = re.compile(r"[A-Za-z0-9_-]+")      # Gatus 경로·조건에 그대로 넣을 수 있는 백엔드 이름(점·괄호·공백이 있으면 경로가 갈린다)
_ADDR = re.compile(r"[^@\s<>,;\"']+@[^@\s<>,;\"']+")
# 스크립트 검사(외부 끝점) — 주기 · 한 번의 상한(초). heartbeat 는 주기 + 상한 + 5분이다(한 번이 늦어도 끊긴 것으로 치지 않게).
CHECK_GROUP = "checks"
SMOKE_EVERY_S, SMOKE_TIMEOUT_S = 1800, 600
DRIVE_EVERY_S, DRIVE_TIMEOUT_S = 3600, 300
CHECK_FAILURES = 2             # 주기가 길어 연속 2번이면 MCP 1시간 · Drive 2시간이다
# Drive 리모트 — drive-drift.sh 와 같은 셋 · 같은 자리(포털은 infra/.env, 나머지는 그 리포의 .env). 접두는 시각 붙은 업로드 폴더다.
DRIVE_REMOTES = (("포털", None, "HWAX_DRIVE_REMOTE", "images-"),
                 ("HEAXHub", ("HEAXHub", ".env"), "HEAX_DRIVE_REMOTE", "dist-"),
                 ("KooRemapper", ("KooRemapper", "platform/.env"), "KOORM_DRIVE_REMOTE", "dist-"))
_TOKEN_OK = re.compile(r"[A-Za-z0-9_-]{32,128}")
PAUSE_MAX_MIN = 240
_WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")   # time.gmtime 의 tm_wday 순서


class Bad(ValueError):
    """손잡이 값이 틀렸다 — 쓰지 않는다(종료코드 2)."""


def _services():
    """services.py 를 모듈로 — 대상 판정(only_on · unless_env · if_env)과 url 풀이의 정본이다. 같은 디렉터리의 사본을 읽는다."""
    spec = importlib.util.spec_from_file_location("hwax_services_for_status", Path(__file__).resolve().parent / "services.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ── 손잡이(infra/.env) ──────────────────────────────────────────────────────────────────────────────
def _port(raw: str | None) -> int:
    if raw is None:
        return DEFAULT_PORT
    if not re.fullmatch(r"[0-9]{1,5}", raw) or not 1 <= int(raw) <= 65535:
        raise Bad(f"STATUS_BOARD_PORT='{raw}' 는 1~65535 의 포트 번호가 아니다(기본 {DEFAULT_PORT})")
    return int(raw)


def _interval(raw: str | None) -> str:
    if raw is None:
        return DEFAULT_INTERVAL
    if not re.fullmatch(r"[1-9][0-9]*[smh]", raw):
        raise Bad(f"STATUS_BOARD_INTERVAL='{raw}' 는 Gatus 길이가 아니다 — 30s · 1m · 5m 처럼 수와 s·m·h 하나(기본 {DEFAULT_INTERVAL})")
    return raw


def _alert_to(raw: str | None) -> list[str]:
    if raw is None:
        return []
    out = [a.strip() for a in raw.split(",") if a.strip()]
    bad = [i for i, a in enumerate(out, 1) if not _ADDR.fullmatch(a)]
    if not out or bad:
        # 값은 찍지 않는다 — 자리표시(<…>)를 그대로 둔 줄이 가장 흔하다. 몇 번째가 틀렸는지만.
        raise Bad("STATUS_ALERT_TO 는 쉼표로 가른 메일 주소여야 한다" + (f" — {', '.join(map(str, bad))}번째가 주소 모양이 아니다" if bad else "")
                  + "(자리표시를 그대로 뒀는지 본다)")
    return out


# ── 포털 메일 설정(backend/.env) — 포털이 읽는 규칙 그대로 ─────────────────────────────────────────────
_DQ_ESC = re.compile(r"\\[\\'\"abfnrtv]")
_SQ_ESC = re.compile(r"\\[\\']")
_VAR = re.compile(r"\$\{(?P<name>[^}:]*)(?::-(?P<default>[^}]*))?\}")
_BINDING = re.compile(r"[ \t]*(?:export[ \t]+)?(?P<key>[^=#\s]+)[ \t]*(?P<eq>=?)[ \t]*(?P<rest>.*)")
_TAIL_OK = re.compile(r"[ \t]*(?:#.*)?")


def _unescape(rx: re.Pattern, s: str) -> str:
    return rx.sub(lambda m: codecs.decode(m.group(0), "unicode-escape"), s)


def _dotenv(path: Path) -> dict[str, str]:
    """backend/.env 를 포털(pydantic-settings → python-dotenv 1.x)처럼 — 한 줄짜리 `KEY=값` 에 대해. 키는 소문자로(대소문자 무시), 마지막
    줄이 이긴다. 값 — 작은따옴표·큰따옴표는 닫는 따옴표까지(이스케이프 풀기, 뒤에는 공백과 `#` 주석만 — 다른 글이 붙으면 그 줄을 버린다),
    따옴표가 없으면 공백 뒤 `#` 이후를 버리고 오른쪽 공백을 지운다. `${이름}`·`${이름:-기본}` 은 앞서 읽은 키, 다음 이 프로세스의 환경, 다음
    기본값으로 푼다. 여러 줄에 걸친 따옴표 값은 읽지 않는다(그 키는 없는 것으로 — 메일 설정에 쓸 일이 없다)."""
    raw: list[tuple[str, str]] = []
    for ln in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        m = _BINDING.fullmatch(ln)
        if not m or not m.group("eq"):
            continue
        rest = m.group("rest")
        if rest[:1] in ("'", '"'):
            q = rest[0]
            mq = re.match(r"'((?:\\'|[^'])*)'" if q == "'" else r'"((?:\\"|[^"])*)"', rest)
            if not mq or not _TAIL_OK.fullmatch(rest[mq.end():]):
                continue
            val = _unescape(_SQ_ESC if q == "'" else _DQ_ESC, mq.group(1))
        else:
            val = re.sub(r"\s+#.*", "", rest).rstrip()
        raw.append((m.group("key"), val))
    resolved: dict[str, str] = {}
    for key, val in raw:
        env = {**os.environ, **resolved}
        resolved[key] = _VAR.sub(lambda v, env=env: env.get(v.group("name"), v.group("default") or "") or "", val)
    out: dict[str, str] = {}
    for key, val in resolved.items():
        out[key.lower()] = val
    return out


_TRUE, _FALSE = {"1", "on", "t", "true", "y", "yes"}, {"0", "off", "f", "false", "n", "no"}


def _mail(be_env: Path, to: list[str]) -> tuple[dict | None, str]:
    """(Gatus email 블록 또는 None, 한 줄 사유) — to 가 비었으면 묻지 않는다."""
    if not to:
        return None, "경보 꺼짐 — infra/.env 에 STATUS_ALERT_TO 가 없다(켜려면 팀 공용 주소를 적는다 — 화면만 돈다)"
    if not be_env.is_file():
        return None, "경보를 못 켰다 — 포털 backend/.env 가 없어 메일 설정(SMTP)을 모른다"
    try:
        e = _dotenv(be_env)
    except OSError as exc:
        return None, f"경보를 못 켰다 — backend/.env 를 읽지 못했다({type(exc).__name__})"
    backend = e.get("mail_backend", "")
    if backend != "smtp":
        why = "Graph 다 — Gatus 는 Graph 로 못 보낸다(독립 발신기는 2단계 — IM-D3)" if backend == "graph" else f"'{backend or 'console(기본)'}' 다"
        return None, f"경보를 못 켰다 — 포털 메일(backend/.env MAIL_BACKEND)이 smtp 가 아니라 {why}"
    host, sender = e.get("smtp_host", "").strip(), e.get("mail_from", "").strip()
    if not host:
        return None, "경보를 못 켰다 — backend/.env 에 SMTP_HOST 가 없다"
    if not sender:
        return None, "경보를 못 켰다 — backend/.env 에 MAIL_FROM 이 없다(보내는 주소를 모른다 — 포털이 쓰는 주소를 적는다)"
    port_raw = e.get("smtp_port", "").strip() or "587"
    if not re.fullmatch(r"[0-9]{1,5}", port_raw) or not 1 <= int(port_raw) <= 65535:
        return None, "경보를 못 켰다 — backend/.env 의 SMTP_PORT 가 포트 번호가 아니다"
    tls_raw = e.get("smtp_starttls", "").strip().lower() or "true"
    if tls_raw not in _TRUE | _FALSE:
        return None, "경보를 못 켰다 — backend/.env 의 SMTP_STARTTLS 가 참·거짓이 아니다"
    block: dict = {"from": sender, "host": host, "port": int(port_raw), "to": ",".join(to)}
    if e.get("smtp_username"):
        block["username"] = e["smtp_username"]
    if e.get("smtp_password"):
        block["password"] = e["smtp_password"]
    starttls = tls_raw in _TRUE
    if not starttls:
        block["client"] = {"insecure": True}
    block["default-alert"] = {"enabled": True, "failure-threshold": FAILURES, "success-threshold": SUCCESSES, "send-on-resolved": True}
    how = "STARTTLS 는 서버가 내밀면 쓰고 인증서를 검증한다" if starttls else "SMTP_STARTTLS=false — 서버가 STARTTLS 를 내밀면 검증 없이 쓴다"
    return block, (f"경보 켜짐 — 받는 곳 {len(to)}곳(infra/.env STATUS_ALERT_TO) · 보내는 길 backend/.env 의 SMTP(포트 {int(port_raw)} · "
                   f"{'로그인' if block.get('password') else '로그인 없음'} · {how}) · 연속 {FAILURES}번 실패에 메일, {SUCCESSES}번 성공에 풀림 메일")


# ── 검사 ──────────────────────────────────────────────────────────────────────────────────────────
def _gateway_backends(url: str) -> list[str] | None:
    """떠 있는 게이트웨이 /health 의 backends 이름(정렬). 답이 없거나 모양이 다르면 None. 루프백이라 프록시를 타지 않는다."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(url, timeout=3) as r:            # noqa: S310 — 매니페스트의 루프백 주소
            body = json.loads(r.read(2_000_000).decode("utf-8", "replace"))
    except Exception:  # noqa: BLE001 — 어떤 실패든 '이름을 모른다' 다
        return None
    b = body.get("backends") if isinstance(body, dict) else None
    return sorted(k for k in b if isinstance(k, str)) if isinstance(b, dict) else None


def _status_conditions(code: object) -> list[str]:
    if code is None:
        return ["[CONNECTED] == true", "[STATUS] < 500"]
    codes = [int(c) for c in (code if isinstance(code, (list, tuple, set)) else [code])]
    return ["[CONNECTED] == true", f"[STATUS] == {codes[0]}" if len(codes) == 1 else f"[STATUS] == any({', '.join(map(str, codes))})"]


def _endpoint_name(url: str) -> str:
    u = urlsplit(url)
    port = u.port or (443 if u.scheme == "https" else 80)
    return f"{u.hostname}:{port}{u.path or '/'}" + (f"?{u.query}" if u.query else "")


def _enriched(name: str, notes: list[str], gw_names: list[str] | None) -> list[str] | None:
    """이 서비스의 health(첫 url) 에 얹는 조건 — 없으면 None(일반 조건)."""
    if name == GATEWAY:
        # 수 조건은 화면에 그 수를 보이려는 것이기도 하다 — 오른쪽이 0 이면 Gatus 가 길이(0s)로 읽어 '(0s)' 를 덧붙인다. 그래서 >= 1 · > -1.
        conds = ["[CONNECTED] == true", "[STATUS] == 200", "[BODY].status == ok", "[BODY].tools >= 1"]
        if gw_names is None:
            notes.append("게이트웨이가 답하지 않아 백엔드 이름을 몰랐다 — '하나라도 false 면 실패' 한 줄만 싣는다(다음 update-all 이 이름을 채운다)")
        else:
            ok_names = [n for n in gw_names if _NAME_OK.fullmatch(n)]
            odd = len(gw_names) - len(ok_names)
            conds += [f"[BODY].backends.{n} != false" for n in ok_names]
            notes.append(f"게이트웨이 백엔드 {len(ok_names)}곳을 이름으로 싣는다(false 면 그 이름이 경보 본문에 찍힌다)"
                         + (f" — 이름에 쓸 수 없는 글자가 있는 {odd}곳은 아래 한 줄로만 본다" if odd else ""))
        conds.append("[BODY].backends != pat(*:false*)")
        return conds
    if name == AGENT:
        return ["[CONNECTED] == true", "[STATUS] == 200", "[BODY].status == ok",
                "has([BODY].delib_active) == true", "[BODY].delib_active > -1", "[BODY].delib_queued > -1"]
    if name == ROUTER:
        return ["[CONNECTED] == true", "[STATUS] == 200", "[BODY].status == ok", "[BODY].models.match == true",
                "[BODY].upstreams_up == [BODY].upstreams_total"]
    return None


def _mxwp_wiki(health: str, interval: str, mail: dict | None, notes: list[str]) -> dict | None:
    """MX 백서 위키 워커 끝점 — 이 박스의 MXWhitePaper 에 워커가 있는 판만(없으면 None · 그 까닭을 notes 에). 워커는 리스너가 없어 API
    (health 와 같은 호스트 · 포트)의 위키 상태로 본다. 그 응답은 최근 10분 안에 박동한 워커만 싣고(위키를 꺼도 워커는 disabled 로 박동한다)
    멈출 때 stopped 를 남긴다 — API 만 살아 있으면 200 이라 상태 코드로는 죽은 워커를 못 본다. 수 조건 둘은 화면에 그 수를 보이려는 것이다."""
    repo = _find_repo(MXWP_REPO)
    if repo is None or not (repo / _MXWP_WIKI_WORKER).is_file():
        notes.append("MX 백서 위키 워커는 보지 않는다 — 이 박스의 MXWhitePaper 에 워커가 없는 판이다(위키 W3 전)")
        return None
    u = urlsplit(health)
    url = f"{u.scheme}://{u.netloc}{_MXWP_WIKI_HEALTH}"
    ep: dict = {"name": _endpoint_name(url), "group": MXWP, "url": url, "interval": interval,
                "conditions": ["[CONNECTED] == true", "[STATUS] == 200", "len([BODY].data.workers) >= 1",
                               "[BODY].data.workers[0].state != stopped",
                               "[BODY].data.jobs.queued > -1", "[BODY].data.jobs.failed_24h > -1"],
                "ui": {"resolve-successful-conditions": True}}
    if mail:
        ep["alerts"] = [{"type": "email", "description": "MX 백서 위키 워커(mxwp_wiki)가 박동하지 않는다 — 확인: (MXWhitePaper) "
                                                     f"./infra/scripts/diag.sh · 안내 {RUNBOOK}"}]
    notes.append("MX 백서 위키 워커를 본다 — 최근 10분 안에 박동한 워커가 있고 맨 앞이 stopped 가 아니어야 한다")
    return ep


def _find_repo(name: str) -> Path | None:
    """형제 리포 → ~/Projects → ~/claude — update-all find_repo · drive-drift 와 같은 순서(박스마다 리포 자리가 다르다)."""
    for base in (ROOT.parent, Path.home() / "Projects", Path.home() / "claude"):
        if (base / name).is_dir():
            return base / name
    return None


def _env_get(path: Path, key: str) -> str:
    """남의 리포 .env 값 하나 — drive-drift.sh 의 env_get 과 같은 규칙(`KEY=` 로 시작하는 마지막 줄, 따옴표 글자를 지운다)."""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    vals = [ln[len(key) + 1:] for ln in lines if ln.startswith(f"{key}=")]
    return vals[-1].replace('"', "").replace("'", "").strip() if vals else ""


def _token() -> str:
    """밀어 넣기 토큰 — 있던 것을 다시 쓴다(매번 바꾸면 설정이 매번 달라져 상태판이 매 update-all 에 다시 뜬다)."""
    try:
        old = json.loads(PUSH.read_text(encoding="utf-8")).get("token")
    except (OSError, ValueError, AttributeError):
        old = None
    return old if isinstance(old, str) and _TOKEN_OK.fullmatch(old) else secrets.token_urlsafe(32)


def _check_key(name: str) -> str:
    return f"{_san(CHECK_GROUP)}_{_san(name)}"


def _script_checks(svc_mod, gateway_here: bool, port: int, mail: dict | None, notes: list[str]) -> tuple[list[dict], dict]:
    """(외부 끝점 목록, push.json 내용). 이 박스에서 돌 수 없는 검사는 싣지 않고 그 까닭을 notes 에 적는다."""
    token = _token()
    eps: list[dict] = []
    checks: list[dict] = []
    on: list[str] = []
    off: list[str] = []

    def _ep(name: str, every_s: int, timeout_s: int, desc: str) -> None:
        ep: dict = {"name": name, "group": CHECK_GROUP, "token": token,
                    "heartbeat": {"interval": f"{(every_s + timeout_s) // 60 + 5}m"}}
        if mail:
            ep["alerts"] = [{"type": "email", "failure-threshold": CHECK_FAILURES, "success-threshold": 1, "description": desc}]
        eps.append(ep)

    agent = _find_repo("HWAXAgentServer")
    smoke_py = agent / ".venv" / "bin" / "python" if agent else None
    if not gateway_here:
        off.append("MCP 실호출(게이트웨이가 이 박스 대상이 아니다)")
    elif not smoke_py or not os.access(smoke_py, os.X_OK):
        off.append("MCP 실호출(mcp 모듈이 있는 에이전트 서버 venv 를 못 찾았다 — HWAXAgentServer/.venv)")
    else:
        _ep("mcp-smoke", SMOKE_EVERY_S, SMOKE_TIMEOUT_S,
            f"MCP 도구 실호출이 실패한다 — 사유는 상태판 화면의 이 검사 결과와 /tmp/hwax-services/status-board.log 의 [status-push] 줄 · "
            f"손으로: python3 ./infra/scripts/status-push.py once mcp-smoke · 안내 {RUNBOOK}")
        checks.append({"kind": "mcp-smoke", "key": _check_key("mcp-smoke"), "every_s": SMOKE_EVERY_S,
                       "timeout_s": SMOKE_TIMEOUT_S, "python": str(smoke_py)})
        on.append(f"MCP 실호출({SMOKE_EVERY_S // 60}분마다 · 읽기 도구 백엔드당 하나)")

    remotes: list[dict] = []
    for label, where, key, prefix in DRIVE_REMOTES:
        if where is None:
            val = (svc_mod._infra_value(key) or "").strip()
        else:
            repo = _find_repo(where[0])
            val = _env_get(repo / where[1], key) if repo else ""
        if val:
            remotes.append({"label": label, "remote": val.rstrip("/"), "prefix": prefix})
    if not remotes:
        off.append("Drive latest/(Drive 리모트가 하나도 없다 — infra/.env HWAX_DRIVE_REMOTE 등)")
    elif not shutil.which("rclone"):
        off.append("Drive latest/(rclone 이 없다)")
    else:
        _ep("drive-latest", DRIVE_EVERY_S, DRIVE_TIMEOUT_S,
            "Drive latest/ 가 가장 새 업로드 폴더보다 낡았거나 Drive 에 닿지 못한다 — 소비자는 latest/ 를 먼저 받아 옛 산출물이 오류 없이 간다"
            f"(docs/gotchas.md 8). 사유는 상태판 화면의 이 검사 결과 · 손으로: python3 ./infra/scripts/status-push.py once drive-latest · 안내 {RUNBOOK}")
        checks.append({"kind": "drive-latest", "key": _check_key("drive-latest"), "every_s": DRIVE_EVERY_S,
                       "timeout_s": DRIVE_TIMEOUT_S, "remotes": remotes})
        on.append(f"Drive latest/({DRIVE_EVERY_S // 60}분마다 · 리모트 {len(remotes)}곳: {' · '.join(r['label'] for r in remotes)})")
    if on:
        notes.append("스크립트 검사 " + " · ".join(on) + " — 밀어 넣는 쪽(status-push.py)은 상태판과 함께 뜬다")
    if off:
        notes.append("스크립트 검사 안 함: " + " · ".join(off))
    return eps, {"url": f"http://127.0.0.1:{port}", "token": token, "checks": checks}


def _san(s: str) -> str:
    """Gatus 의 config/key 와 같은 정리 — 소문자로 바꾸고 / _ . , 빈칸 # + & 를 - 로."""
    return re.sub(r"[/_.,#+& ]", "-", s.strip().lower())


def _dollars(v: object) -> object:
    """Gatus 는 설정 글 전체에서 `$이름` 을 환경변수로 풀고 `$$` 를 `$` 로 되돌린다 — 값의 `$` 를 전부 `$$` 로."""
    if isinstance(v, str):
        return v.replace("$", "$$")
    if isinstance(v, dict):
        return {k: _dollars(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_dollars(x) for x in v]
    return v


def build(svc_mod) -> tuple[dict, list[str], str, bool, dict]:
    """(설정, 알림 줄, 경보 한 줄, 경보를 원했는데 못 켰다, push.json 내용)."""
    iv = svc_mod._infra_value
    port = _port(iv("STATUS_BOARD_PORT"))
    interval = _interval(iv("STATUS_BOARD_INTERVAL"))
    to = _alert_to(iv("STATUS_ALERT_TO"))
    mail, mail_why = _mail(ROOT / "backend" / ".env", to)
    notes: list[str] = []
    endpoints: list[dict] = []
    skipped: list[str] = []
    services = [s for s in svc_mod.load() if s.get("name") != SELF]
    n_svc = 0
    gateway_here = False
    for s in services:
        name = s["name"]
        if not svc_mod.enabled_here(s):
            skipped.append(f"{name}({svc_mod.skip_reason(s)})")
            continue
        gateway_here = gateway_here or name == GATEWAY
        urls = svc_mod.service_urls(s)
        if not urls:
            skipped.append(f"{name}(health url 없음)")
            continue
        n_svc += 1
        gw_names = _gateway_backends(urls[0]) if name == GATEWAY else None
        for i, url in enumerate(urls):
            conds = (_enriched(name, notes, gw_names) if i == 0 else None) or _status_conditions(s.get("expect") if i == 0 else None)
            ep: dict = {"name": _endpoint_name(url), "group": name, "url": url, "interval": interval, "conditions": conds,
                        "ui": {"resolve-successful-conditions": True}}
            if mail:
                ep["alerts"] = [{"type": "email", "description": f"확인: ./infra/scripts/services.sh status {name} · 안내 {RUNBOOK}"}]
            endpoints.append(ep)
        if name == MXWP:
            wiki = _mxwp_wiki(urls[0], interval, mail, notes)
            if wiki:
                endpoints.append(wiki)
    if not endpoints:
        raise RuntimeError("이 박스에서 볼 리스너가 하나도 없다 — 매니페스트(infra/services.yaml)와 infra/.env 를 본다")
    # 같은 키가 둘이면 Gatus 가 설정을 거부한다 — 뒤에 번호를 붙인다. 키는 Gatus 의 config/key 그대로다(그룹과 이름을 따로 _san 한 뒤
    # _ 로 잇는다). 스크립트 검사의 그룹(checks)은 서비스 이름이 아니라 겹치지 않는다.
    seen: dict[str, int] = {}
    for ep in endpoints:
        key = f"{_san(ep['group'])}_{_san(ep['name'])}"
        seen[key] = seen.get(key, 0) + 1
        if seen[key] > 1:
            ep["name"] = f"{ep['name']} ({seen[key]})"
    externals, push = _script_checks(svc_mod, gateway_here, port, mail, notes)
    box = svc_mod.box_name()
    cfg: dict = {
        "skip-invalid-config-update": True,           # 손으로 고친 파일이 틀려도 도는 상태판이 죽지 않고 옛 설정으로 돈다(기본은 panic)
        "web": {"address": "127.0.0.1", "port": port},  # 기본은 0.0.0.0 이다 — 화면·API 에 인증이 없다
        # 기록 보존 — 메모리 저장소는 설정을 다시 읽을 때마다 기록과 경보 상태를 잃었다(풀림 메일이 안 온다 — v5.37.0 실측, IM-D25).
        "storage": {"type": "sqlite", "path": "/data/gatus.db"},
        "ui": {"title": f"HWAX 상태판 — {box}", "header": f"HWAX 상태판 — {box}",
               "dashboard-subheading": f"이 박스의 서비스 리스너 · 게이트웨이 백엔드 · 에이전트 서버 · LLM 라우터(켠 박스만)를 {interval} 마다, "
                                       f"MCP 실호출 · Drive latest/(있는 박스만)를 스크립트로 본다 — 안내 {RUNBOOK}"},
        "endpoints": endpoints,
    }
    if externals:
        cfg["external-endpoints"] = externals
    if mail:
        cfg["alerting"] = {"email": mail}
    notes.insert(0, f"검사 {len(endpoints)}개 — 서비스 {n_svc}곳의 리스너 전부 · 주기 {interval} · 화면 http://127.0.0.1:{port}")
    if skipped:
        notes.insert(1, "이 박스 대상 아님: " + " · ".join(skipped))
    return cfg, notes, mail_why, bool(to) and mail is None, push


_HEAD = ("# 생성 파일 — infra/scripts/gen-status-config.py 가 매 update-all(5b)에 다시 쓴다. 손으로 고치면 다음 실행이 덮는다.\n"
         "# 메일 자격이 들어 있을 수 있다 — 600 을 지키고 옮기지 않는다. 값의 달러 기호는 Gatus 의 환경변수 풀이를 피해 두 번 적었다.\n")


def _dump(doc: dict) -> str:
    """이미 `$$` 로 적힌 문서를 글로 — 멈춤 걸기·풀기는 읽은 문서를 이것으로 다시 쓴다(두 번 겹쳐 적지 않게). render 와 같은 손잡이라
    maintenance 칸만 넣었다 뺀 문서는 일반 생성과 글자까지 같다(지문이 그대로라 update-sites 가 다시 띄우지 않는다)."""
    return _HEAD + yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, default_flow_style=False, width=1_000_000)


def render(cfg: dict) -> str:
    return _dump(_dollars(cfg))


def write(text: str, path: Path = OUT) -> bool:
    """바뀌었을 때만 이름 바꾸기로 갈아 끼운다(같은 디렉터리의 임시 파일 — 처음부터 600). 디렉터리 700 · 파일 600 은 늘 맞춘다. → 썼나."""
    STATE.mkdir(parents=True, exist_ok=True)
    os.chmod(STATE, 0o700)
    if path.is_file() and not path.is_symlink():
        try:
            same = path.read_text(encoding="utf-8") == text
        except (OSError, UnicodeDecodeError):
            same = False
        if same:
            os.chmod(path, 0o600)
            return False
    fd, tmp = tempfile.mkstemp(dir=STATE, prefix=f".{path.stem}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise
    os.chmod(path, 0o600)
    return True


def _write_json(path: Path, obj: object) -> bool:
    return write(json.dumps(obj, ensure_ascii=False, indent=1) + "\n", path)


@contextlib.contextmanager
def _locked():
    """생성기 실행 하나씩 — 밀어 넣는 쪽의 걷어내기(--unpause-if-expired)와 update-all 의 걸기·일반 생성이 겹치지 않게."""
    STATE.mkdir(parents=True, exist_ok=True)
    os.chmod(STATE, 0o700)
    fd = os.open(LOCK, os.O_RDWR | os.O_CREAT, 0o600)      # 파이썬 fd 는 물려주지 않는다(PEP 446)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


# ── 경보 멈춤 ──────────────────────────────────────────────────────────────────────────────────────
def _load_doc() -> dict | None:
    """지금 생성 설정(값의 `$` 는 `$$` 그대로) — 없거나 문서 모양이 아니면 None."""
    if not OUT.is_file() or OUT.is_symlink():
        return None
    doc = yaml.safe_load(OUT.read_text(encoding="utf-8"))
    return doc if isinstance(doc, dict) else None


def _maintenance(since: int, until: int) -> dict:
    """Gatus 점검 창 — UTC 분 단위 시작 · 길이 · 그날 요일 하나(영어). 요일은 strftime(%A)을 쓰지 않는다 — 로캘 요일('토요일')이면 Gatus 가
    설정을 거부한다(skip-invalid 가 없으면 panic — 2026-10-17 실측)."""
    start = since - since % 60
    t = time.gmtime(start)
    return {"start": f"{t.tm_hour:02d}:{t.tm_min:02d}", "duration": f"{max(1, -(-(until - start) // 60))}m",
            "timezone": "UTC", "every": [_WEEKDAYS[t.tm_wday]]}


def pause(minutes: int) -> int:
    if not 1 <= minutes <= PAUSE_MAX_MIN:
        print(f"✗ --pause 는 1~{PAUSE_MAX_MIN} 분이다({minutes}) — 멈추지 않았다")
        return 2
    doc = _load_doc()
    if doc is None:
        print("○ 상태판 설정이 없다 — 멈출 경보가 없다")
        return 0
    now = int(time.time())
    until = now + minutes * 60
    _write_json(PAUSE, {"since": now, "until": until})      # 시한 먼저 — 그 사이에 죽어도 창만 남는 일이 없다
    doc["maintenance"] = _maintenance(now, until)            # 이미 걸려 있으면 갈아 끼운다(시한을 새로 잡는다)
    write(_dump(doc))
    m = doc["maintenance"]
    print(f"✓ 경보를 멈췄다 — {minutes}분(UTC {m['start']}부터 {m['duration']}). 실패는 그대로 기록하고 메일만 보내지 않는다 — "
          "5b 의 설정 생성이 풀고, 그 전에 끝나지 않으면 시한에 밀어 넣는 쪽이 걷어낸다")
    return 0


def unpause(only_if_expired: bool) -> int:
    rec = None
    with contextlib.suppress(OSError, ValueError):
        rec = json.loads(PAUSE.read_text(encoding="utf-8"))
    until = rec.get("until") if isinstance(rec, dict) else None
    if only_if_expired and isinstance(until, (int, float)) and until > time.time():
        return 0                                             # 아직 시한 안이다 — 조용히
    doc = _load_doc()
    had = doc is not None and "maintenance" in doc
    if had:
        doc.pop("maintenance")
        write(_dump(doc))
    with contextlib.suppress(FileNotFoundError):
        PAUSE.unlink()
    if had:
        print("✓ 경보 멈춤을 풀었다" + (" — 시한이 지났다(update-all 이 5b 전에 끝났다)" if only_if_expired else ""))
    elif not only_if_expired:
        print("· 경보 멈춤이 걸려 있지 않다")
    return 0


def generate() -> int:
    try:
        svc = _services()
        cfg, notes, mail_why, wanted_but_off, push = build(svc)
    except Bad as exc:
        print(f"✗ {exc} — 설정을 쓰지 않았다(옛 설정이 있으면 그대로 돈다)")
        with contextlib.suppress(Exception):
            unpause(False)                                   # 일반 생성은 늘 멈춤을 끝낸다 — 못 만들었어도 옛 설정의 창은 걷는다
        return 2
    except Exception as exc:  # noqa: BLE001 — 매니페스트·infra/.env 를 못 읽었다(InfraEnvUnreadable 포함)
        print(f"✗ 상태판 설정을 만들지 못했다 — {type(exc).__name__}: {exc}")
        with contextlib.suppress(Exception):
            unpause(False)
        return 1
    for n in notes:
        print(f"· {n}")
    print(("⚠ " if wanted_but_off else "· ") + mail_why)
    paused = PAUSE.exists()
    with contextlib.suppress(Exception):                     # 옛 설정이 깨져 있어도 새로 쓰는 길은 막지 않는다
        paused = paused or "maintenance" in (_load_doc() or {})
    try:
        DATA.mkdir(parents=True, exist_ok=True)
        os.chmod(DATA, 0o700)
        _write_json(PUSH, push)
        changed = write(render(cfg))
        with contextlib.suppress(FileNotFoundError):
            PAUSE.unlink()
    except OSError as exc:
        print(f"✗ 설정을 쓰지 못했다({OUT.relative_to(ROOT)}) — {type(exc).__name__}: {exc}. infra/.state 의 권한·소유자를 본다")
        return 1
    rel = OUT.relative_to(ROOT)
    print(f"✓ 설정을 새로 썼다 — {rel} (600)" if changed else f"· 설정 그대로 — {rel}(바뀐 것 없음)")
    if paused:
        print("✓ 경보 멈춤을 풀었다")
    return 3 if wanted_but_off else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="상시 상태판(Gatus) 설정 생성 · 경보 멈춤 — docs/improvement-1015/status-board.md")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--pause", type=int, metavar="분", help=f"경보를 그만큼 멈춘다(1~{PAUSE_MAX_MIN}) — 설정의 maintenance 칸만 넣는다")
    g.add_argument("--unpause", action="store_true", help="멈춤을 푼다")
    g.add_argument("--unpause-if-expired", action="store_true", help="시한이 지난 멈춤만 푼다(밀어 넣는 쪽이 부른다)")
    a = ap.parse_args(argv)
    try:
        with _locked():
            if a.pause is not None:
                return pause(a.pause)
            if a.unpause or a.unpause_if_expired:
                return unpause(a.unpause_if_expired)
            return generate()
    except (OSError, yaml.YAMLError) as exc:
        print(f"✗ 상태판 설정을 다루지 못했다 — {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
