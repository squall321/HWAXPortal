#!/usr/bin/env python3
# 상시 상태판(Gatus) 설정을 매니페스트·infra/.env·포털 메일 설정에서 만드는 생성기 — infra/.state/status/config.yaml(디렉터리 700 · 파일 600)
"""상시 상태판 설정 생성기 — docs/improvement-1015/status-board.md

    python3 ./infra/scripts/gen-status-config.py      # update-all 5b 가 STATUS_BOARD 가 있으면 매번 부른다

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

종료코드 — 0 썼다(또는 그대로) · 2 손잡이 값이 틀렸다(쓰지 않았다 — 옛 설정이 그대로 돈다) · 3 썼는데 경보를 못 켰다 · 1 그 밖의 실패.
"""

import codecs
import contextlib
import importlib.util
import json
import os
import re
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "infra" / ".state" / "status"
OUT = STATE / "config.yaml"
RUNBOOK = "docs/improvement-1015/status-board.md"
SELF = "status-board"
DEFAULT_PORT = 8740            # 9100~9999 는 HEAXHub 가 앱마다 그때그때 나눠 주는 포트 풀이다(docs/PORT-MAP.md)
DEFAULT_INTERVAL = "1m"
FAILURES = 5                   # 연속 실패 수 — 주기 1분이면 5분. update-all 의 재기동(대개 1~2분)으로는 메일이 나가지 않게
SUCCESSES = 2                  # 다시 살아난 것으로 치는 연속 성공 수(풀림 메일)
GATEWAY, AGENT, ROUTER = "mcp-gateway", "agent-server", "llm-router"
_NAME_OK = re.compile(r"[A-Za-z0-9_-]+")      # Gatus 경로·조건에 그대로 넣을 수 있는 백엔드 이름(점·괄호·공백이 있으면 경로가 갈린다)
_ADDR = re.compile(r"[^@\s<>,;\"']+@[^@\s<>,;\"']+")


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


def _dollars(v: object) -> object:
    """Gatus 는 설정 글 전체에서 `$이름` 을 환경변수로 풀고 `$$` 를 `$` 로 되돌린다 — 값의 `$` 를 전부 `$$` 로."""
    if isinstance(v, str):
        return v.replace("$", "$$")
    if isinstance(v, dict):
        return {k: _dollars(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_dollars(x) for x in v]
    return v


def build(svc_mod) -> tuple[dict, list[str], str, bool]:
    """(설정, 알림 줄, 경보 한 줄, 경보를 원했는데 못 켰다)."""
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
    for s in services:
        name = s["name"]
        if not svc_mod.enabled_here(s):
            skipped.append(f"{name}({svc_mod.skip_reason(s)})")
            continue
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
    if not endpoints:
        raise RuntimeError("이 박스에서 볼 리스너가 하나도 없다 — 매니페스트(infra/services.yaml)와 infra/.env 를 본다")
    # 같은 키가 둘이면 Gatus 가 설정을 거부한다 — 뒤에 번호를 붙인다. 키는 Gatus 의 config/key 그대로다(그룹과 이름을 따로 소문자로 바꾸고
    # / _ . , 빈칸 # + & 를 - 로 바꾼 뒤 _ 로 잇는다).
    def _san(s: str) -> str:
        return re.sub(r"[/_.,#+& ]", "-", s.strip().lower())
    seen: dict[str, int] = {}
    for ep in endpoints:
        key = f"{_san(ep['group'])}_{_san(ep['name'])}"
        seen[key] = seen.get(key, 0) + 1
        if seen[key] > 1:
            ep["name"] = f"{ep['name']} ({seen[key]})"
    box = svc_mod.box_name()
    cfg: dict = {
        "skip-invalid-config-update": True,           # 손으로 고친 파일이 틀려도 도는 상태판이 죽지 않고 옛 설정으로 돈다(기본은 panic)
        "web": {"address": "127.0.0.1", "port": port},  # 기본은 0.0.0.0 이다 — 화면·API 에 인증이 없다
        "ui": {"title": f"HWAX 상태판 — {box}", "header": f"HWAX 상태판 — {box}",
               "dashboard-subheading": f"이 박스의 서비스 리스너 · 게이트웨이 백엔드 · 에이전트 서버 · LLM 라우터(켠 박스만)를 {interval} 마다 본다 — 안내 {RUNBOOK}"},
        "endpoints": endpoints,
    }
    if mail:
        cfg["alerting"] = {"email": mail}
    notes.insert(0, f"검사 {len(endpoints)}개 — 서비스 {n_svc}곳의 리스너 전부 · 주기 {interval} · 화면 http://127.0.0.1:{port}")
    if skipped:
        notes.insert(1, "이 박스 대상 아님: " + " · ".join(skipped))
    return cfg, notes, mail_why, bool(to) and mail is None


def render(cfg: dict) -> str:
    head = ("# 생성 파일 — infra/scripts/gen-status-config.py 가 매 update-all(5b)에 다시 쓴다. 손으로 고치면 다음 실행이 덮는다.\n"
            "# 메일 자격이 들어 있을 수 있다 — 600 을 지키고 옮기지 않는다. 값의 달러 기호는 Gatus 의 환경변수 풀이를 피해 두 번 적었다.\n")
    return head + yaml.safe_dump(_dollars(cfg), allow_unicode=True, sort_keys=False, default_flow_style=False, width=1_000_000)


def write(text: str) -> bool:
    """바뀌었을 때만 이름 바꾸기로 갈아 끼운다(같은 디렉터리의 임시 파일 — 처음부터 600). 디렉터리 700 · 파일 600 은 늘 맞춘다. → 썼나."""
    STATE.mkdir(parents=True, exist_ok=True)
    os.chmod(STATE, 0o700)
    if OUT.is_file() and not OUT.is_symlink():
        try:
            same = OUT.read_text(encoding="utf-8") == text
        except (OSError, UnicodeDecodeError):
            same = False
        if same:
            os.chmod(OUT, 0o600)
            return False
    fd, tmp = tempfile.mkstemp(dir=STATE, prefix=".config.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, OUT)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise
    os.chmod(OUT, 0o600)
    return True


def main() -> int:
    try:
        svc = _services()
        cfg, notes, mail_why, wanted_but_off = build(svc)
    except Bad as exc:
        print(f"✗ {exc} — 설정을 쓰지 않았다(옛 설정이 있으면 그대로 돈다)")
        return 2
    except Exception as exc:  # noqa: BLE001 — 매니페스트·infra/.env 를 못 읽었다(InfraEnvUnreadable 포함)
        print(f"✗ 상태판 설정을 만들지 못했다 — {type(exc).__name__}: {exc}")
        return 1
    for n in notes:
        print(f"· {n}")
    print(("⚠ " if wanted_but_off else "· ") + mail_why)
    try:
        changed = write(render(cfg))
    except OSError as exc:
        print(f"✗ 설정을 쓰지 못했다({OUT.relative_to(ROOT)}) — {type(exc).__name__}: {exc}. infra/.state 의 권한·소유자를 본다")
        return 1
    rel = OUT.relative_to(ROOT)
    print(f"✓ 설정을 새로 썼다 — {rel} (600)" if changed else f"· 설정 그대로 — {rel}(바뀐 것 없음)")
    return 3 if wanted_but_off else 0


if __name__ == "__main__":
    raise SystemExit(main())
