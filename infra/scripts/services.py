#!/usr/bin/env python3
"""HWAX stack orchestrator — bring the federated services + chat stack up/down/status.

Reads infra/services.yaml. Local services start in a detached session (survives this
process); remote services start over SSH (KEY auth — no passwords anywhere). Each service
is polled at its health URL. Idempotent: a service that's already answering is skipped.

  services.py up [name ...]      start all (or named) services, tier by tier, wait healthy
  services.py status [name ...]  show which are up (health probe only)
  services.py down [name ...]    stop (uses `stop:` if given, else best-effort by port)

NO SECRETS: remote = ssh <ssh_user>@<host> with key auth. sudo on a remote = that host's
NOPASSWD sudoers, never a password here.
"""

import os
import re
import shlex
import subprocess
import time
import sys
import urllib.request
from pathlib import Path

import yaml

PORTAL_ROOT = Path(__file__).resolve().parent.parent.parent  # infra/scripts → repo root
PARENT = PORTAL_ROOT.parent
MANIFEST = PORTAL_ROOT / "infra" / "services.yaml"
LOG_DIR = Path("/tmp/hwax-services")
LOG_ROTATE_BYTES = 64 * 1024 * 1024   # 기동 · 갱신 때 이보다 크면 한 벌(.1)만 넘기고 새로 연다


def svc_log(svc: dict, wd: Path | None = None) -> Path:
    """서비스 로그 자리 — 매니페스트 `log:`(서비스 디렉터리 기준) 또는 LOG_DIR/<이름>.log.

    게이트웨이는 `log: gateway.log` 로 손 기동(`start.sh --bg`)과 같은 한 곳에 쓴다(데이터 레지스트리의 그 서비스 log 와 같다).
    """
    rel = svc.get("log")
    base = wd if wd is not None else resolve_dir(svc)
    return (base / rel) if rel and base else LOG_DIR / f"{svc['name']}.log"


def prep_log(path: Path) -> Path:
    """덧붙여 쓸 로그를 준비한다 — 디렉터리 700(LOG_DIR) · 파일 600 · 크면 한 벌 회전.

    ⚠ 기동마다 'wb' 로 열어 지웠다 — cae00 게이트웨이 10-14~10-17 기록이 사라졌고(10-17 리뷰 P1), 바로 앞 갱신 단계가 같은
    파일에 덧붙인 출력도 함께 날아갔다. 그리고 토큰이 든 주소가 찍히는 로그(G1)를 같은 박스의 다른 사용자도 읽을 수 있었다(775 · 664).
    """
    if path.parent == LOG_DIR:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        os.chmod(LOG_DIR, 0o700)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if path.stat().st_size > LOG_ROTATE_BYTES:
            os.replace(path, path.with_name(path.name + ".1"))
    except FileNotFoundError:
        pass
    os.close(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600))
    os.chmod(path, 0o600)
    return path


def _log_tail(path: Path, start: int) -> str:
    """이번 기동이 쓴 부분(start 이후)의 마지막 비지 않은 줄 — 덧붙여 쓰므로 앞 기동의 줄을 진행으로 보이지 않게 한다."""
    try:
        with open(path, "rb") as lf:
            size = lf.seek(0, os.SEEK_END)
            lf.seek(max(start, size - 65536))
            ls = [ln for ln in lf.read().decode("utf-8", errors="replace").splitlines() if ln.strip()]
    except OSError:
        return ""
    return ls[-1].rstrip()[:90] if ls else ""

# ── 데이터 경로 레지스트리(docs/data-migration/PLAN.md §5) ──────────────────────────
# services.yaml 의 서비스별 `data:` 블록을 기동 env 로 해석한다. HWAX_DATA_ROOT 가 없으면 {} 를
# 돌려 기동 명령줄이 종전과 바이트 하나 안 달라진다(원칙 D1 — 켜지 않으면 무영향).
# infra/.env 는 여기서만, HWAX_* 키만 읽고 **os.environ 에 넣지 않는다**. 유닛 EnvironmentFile 로
# 파일 전체를 실으면 APP_ENV·SESSION_SECRET 이 모든 자식 서비스에 상속되는데, heax Settings 가
# APP_ENV=dev 를 거부하며 죽은 것이 2026-09-04 실사고다(사전점검 NO-GO).
_INFRA_ENV_RE = re.compile(r"^\s*(?:export\s+)?(HWAX_(?:DATA_ROOT|BOX|BOX_ROLE|DATA_[A-Z0-9_]+))=(.*)$")


def _infra_env() -> dict[str, str]:
    p = PORTAL_ROOT / "infra" / ".env"
    out: dict[str, str] = {}
    if not p.exists():
        return out
    for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
        m = _INFRA_ENV_RE.match(ln)
        if not m:
            continue
        try:
            toks = shlex.split(m.group(2), comments=True)  # 인라인 주석·따옴표 처리, $VAR 는 확장 안 함
        except ValueError:
            continue
        if toks and toks[0].strip():  # 빈 값(.env.example 의 `KEY=`)은 미설정과 같다
            out[m.group(1)] = toks[0]
    return out


class InfraEnvUnreadable(RuntimeError):
    """infra/.env 가 있는데 못 읽는다 — '모름' 이다. unless_env 판정은 이것을 '대상 아님'(닫힘) 으로 다룬다."""


# 공백은 sed(LC_ALL=C)의 [[:space:]] 와 같은 ASCII 여섯(줄 안에는 \n 이 없다) — `\s` 는 NBSP·U+3000 도 먹어 두 독자가 갈린다(4라운드),
# 스페이스·탭만 보면 수직탭·폼피드·CR 에서 갈린다(LLM 풀 검토 2라운드 LOW 2).
_ENV_WS = " \t\n\v\f\r"
_INLINE_COMMENT = re.compile(r"[ \t\v\f\r]+#.*$")


def _infra_value(key: str) -> str | None:
    """infra/.env 의 **임의 키** 하나. `unless_env` 가 가리키는 키(RA_HOST 등)는 위 HWAX_* 허용 목록 밖이라 _infra_env()
    가 싣지 않는다 — 그래서 파일에만 적은 RA_HOST 를 이 파일이 절대 못 보고 구 RA 를 되살렸다(2026-09-27 2라운드 검토 실측:
    부팅 유닛·services.sh 어느 경로도 RA_HOST 를 env 로 넘기지 않는다).

    규칙은 **update-all 의 `_envfile_value`(sed) 와 글자 단위로 같다** — `export KEY=` 허용, 공백 뒤 `#` 이후 제거, 양끝 공백 제거,
    따옴표 문자(`"` `'`)·CR 제거, 마지막 줄이 이기고 빈 값은 미설정. `=` 뒤 공백은 **주석을 벗긴 뒤에** 지운다 — 먼저 지우면
    `KEY=   # 설명`(값 없이 주석만) 에서 `#` 앞 공백이 사라져 주석 문구가 값이 된다(4라운드: shlex 시절엔 맞게 읽던 회귀였다). shlex 를 쓰지 않는 이유: shlex 는 `x#y` 의 `#` 도 주석으로
    잘라 `x` 를 돌리고 `don't` 는 예외로 줄을 버려, 같은 파일을 두 독자가 다르게 읽었다(3라운드 검토 — 그러면 services.py 는
    'RA 원격' 인데 update-all 은 '미설정' 으로 로컬 RA 가 죽는다). 줄은 `\n` 으로만 나눈다 — splitlines() 는 홀로 선 `\r` · U+2028 에서도
    끊어 `X=1\rLLM_ROUTER_PORT=9555` 의 뒤를 활성 줄로 읽었다(sed 에는 한 줄이다 — LLM 풀 검토 2라운드 LOW 2). NUL 은 마지막에 지운다(bash 의
    `$(…)` 가 그렇게 받는다). 대조 표: backend/tests/test_llm_pool_upstreams_rules.py. os.environ 에는 넣지 않는다. 못 읽으면 InfraEnvUnreadable."""
    p = PORTAL_ROOT / "infra" / ".env"
    if not p.exists():
        return None
    try:
        text = p.read_bytes().decode("utf-8", errors="replace")    # read_text 는 홀로 선 \r 을 줄바꿈으로 바꿔 읽는다
    except OSError as exc:
        raise InfraEnvUnreadable(f"{p}: {exc}") from exc
    pat = re.compile(r"^[ \t\v\f\r]*(?:export[ \t\v\f\r]+)?" + re.escape(key) + r"=(.*)$")
    val: str | None = None
    for ln in text.split("\n"):
        m = pat.match(ln)
        if not m:
            continue
        v = _INLINE_COMMENT.sub("", m.group(1)).strip(_ENV_WS)
        v = v.replace('"', "").replace("'", "").replace("\r", "").replace("\x00", "")
        val = v or None
    return val


def skip_reason(svc: dict) -> str:
    """status/up/down/update 가 '왜 건너뛰었나' 를 찍을 때 — only_on 만 알던 문구(`only_on=None`)로는 unless_env 로 꺼진
    항목의 사유가 보이지 않았다(3라운드). '설정됨'(앎)과 '못 읽음'(모름)은 다른 문구다 — 못 읽은 것을 '다른 서버에서 돈다' 로
    찍으면 `2>/dev/null` 로 부르는 자리(update-all §5·deploy-all)에서 거짓만 남는다(4라운드). 경고는 enabled_here 가 이미 찍었다."""
    for state in (_unless_env_state, _if_env_state):
        allowed, why = state(svc, warn=False)
        if not allowed:
            return why
    return f"only_on={svc.get('only_on')}"


def _unless_env_state(svc: dict, *, warn: bool = True) -> tuple[bool, str]:
    """(이 박스 대상인가, 아니면 왜). unless_env 키가 환경 또는 infra/.env 에 설정돼 있으면 대상이 아니다."""
    unless = svc.get("unless_env")
    if not unless:
        return True, ""
    k = str(unless)
    v = os.environ.get(k)
    if v is None or not v.strip():
        try:
            v = _infra_value(k)                 # _hwax_setting 은 HWAX_* 만 본다 — 여기는 임의 키
        except InfraEnvUnreadable as exc:
            # 모름은 '대상' 이 아니다 — 못 읽은 채 로컬 항목을 띄우면 이사 간 서비스를 되살린다. 닫고 말한다.
            if warn:
                print(f"  ⚠ infra/.env 를 읽을 수 없어 {svc.get('name')} 을 이 박스 대상 아님으로 둔다({exc})", file=sys.stderr, flush=True)
            return False, f"unless_env={k}(infra/.env 를 읽을 수 없음 — 모름이라 닫는다: {exc})"
    if v:
        return False, f"unless_env={k}(설정됨 — 이 서비스는 다른 서버에서 돈다)"
    return True, ""


def _unless_env_allows(svc: dict) -> bool:
    return _unless_env_state(svc)[0]


def _if_env_state(svc: dict, *, warn: bool = True) -> tuple[bool, str]:
    """unless_env 의 거울 — `if_env: <KEY>` 는 그 키가 환경 또는 infra/.env 에 **있는** 박스에서만 다룬다(예: LLM_UPSTREAMS 가 있어야
    LLM 라우터를 띄운다 — docs/llm-pool). 읽는 규칙·순서는 unless_env 와 같다(환경 > infra/.env, 빈 값 = 없음). 못 읽으면 '모름' 이고
    모름은 닫는다 — 못 읽은 채 띄우면 그 박스가 켜지 않은 서비스를 되살린다."""
    want = svc.get("if_env")
    if not want:
        return True, ""
    k = str(want)
    v = os.environ.get(k)
    if v is None or not v.strip():
        try:
            v = _infra_value(k)
        except InfraEnvUnreadable as exc:
            if warn:
                print(f"  ⚠ infra/.env 를 읽을 수 없어 {svc.get('name')} 을 이 박스 대상 아님으로 둔다({exc})", file=sys.stderr, flush=True)
            return False, f"if_env={k}(infra/.env 를 읽을 수 없음 — 모름이라 닫는다: {exc})"
    if v:
        return True, ""
    return False, f"if_env={k}(비어 있음 — 이 박스에서는 켜지 않았다)"


def _hwax_setting(key: str) -> str | None:
    """우선순위 os.environ > infra/.env, 빈 값 = 미설정. backup-local.sh 의 폴백과 같은 순서여야
    두 도구가 같은 박스 이름·경로를 본다."""
    v = os.environ.get(key)
    if v is None or not v.strip():
        v = _infra_env().get(key)
    return v.strip() if v and v.strip() else None


def box_name() -> str:
    import socket
    return _hwax_setting("HWAX_BOX") or socket.gethostname().split(".")[0]


def class_paths(svc: dict, cname: str, c: dict, root: str | None, box: str) -> tuple[Path | None, Path | None]:
    """클래스의 (현행 경로, 목표 경로). 목표는 HWAX_DATA_ROOT 있을 때만, HWAX_DATA_<SVC>_<CLASS> 오버레이 우선."""
    sdir = None if svc.get("_data_only") else resolve_dir(svc)
    curp: Path | None = None
    cur = c.get("current")
    if cur and "#" not in str(cur):  # ".env#KEY" 같은 키 참조는 경로가 아니다
        curp = Path(os.path.expandvars(str(cur))).expanduser()
        if not curp.is_absolute():
            curp = (sdir / curp) if sdir else None
    tgt: Path | None = None
    if root and c.get("path") and c.get("enabled") is not False:
        key = svc["name"].upper().replace("-", "_")
        override = _hwax_setting(f"HWAX_DATA_{key}_{cname.upper()}")
        tgt = Path(override) if override else Path(f"{root}/{c['path']}".replace("{box}", box))
    return curp, tgt


def data_root() -> str | None:
    """HWAX_DATA_ROOT — 반드시 절대경로. cae00 실사고(2026-09-05): 'data'(슬래시 없음)가 들어가 목표가 전부 cwd 상대경로로 계산돼
    포털이 상대경로 --bind 로 기동 실패, 두 서비스 심링크가 허공을 가리켰다. 절대경로가 아니면 미설정으로 본다(경고 1회)."""
    v = _hwax_setting("HWAX_DATA_ROOT")
    if v and not v.startswith("/"):
        if not getattr(data_root, "_warned", False):
            print(f"  ⚠ HWAX_DATA_ROOT='{v}' 는 절대경로가 아니다(예: /data) — 미설정으로 취급", file=sys.stderr, flush=True)
            data_root._warned = True  # type: ignore[attr-defined]
        return None
    return v


def resolve_data(svc: dict) -> dict[str, str]:
    """`data:` 블록 → 주입할 env. HWAX_DATA_ROOT 없으면 {}.

    ⚠ **이동이 끝난 클래스만 주입한다**(상태 same·only-target). 아직 현행 경로에 있는 클래스에 새 경로 env 를
    주면 앱이 그 자리에 빈 DB 를 새로 만든다 — 포털은 users/token_store 가 비고 JWT 키를 새로 민팅한다.
    이동은 data-migrate.sh 가 하고, 그 뒤 재기동에서야 이 env 가 붙는다(브리지 심링크가 있어 안 붙어도 동작한다)."""
    root = data_root()
    data = svc.get("data") or {}
    if not root or not data:
        return {}
    box = box_name()
    env: dict[str, str] = {}
    # root_env 는 주입하지 않는다 — 4 리포 모두 DATA_DIR 이 리포 상대로 고정돼 읽는 코드가 없고, 클래스가
    # /data/pg 와 /data/svc 로 갈리므로 한 루트로 가리킬 수도 없다. 브리지 심링크(D2)가 경로를 잇는다.
    for cname, c in (data.get("classes") or {}).items():
        if not isinstance(c, dict) or c.get("enabled") is False or not c.get("env") or not c.get("path"):
            continue
        curp, tgt = class_paths(svc, cname, c, root, box)
        if tgt is None or _data_status(curp, tgt) not in ("same", "only-target"):
            continue
        env[c["env"]] = str(tgt)
    return env


def _data_status(cur: Path | None, tgt: Path | None) -> str:
    """same(같은 inode·브리지 완료) / divergent(둘 다 있고 다름 — 위험) / only-current / only-target / absent"""
    ce = cur is not None and (cur.exists() or cur.is_symlink())
    te = tgt is not None and tgt.exists()
    if not ce and not te:
        return "absent"
    if ce and not te:
        return "only-current"
    if te and not ce:
        return "only-target"
    try:
        if os.path.samefile(str(cur), str(tgt)):
            return "same"
    except OSError:
        pass
    return "divergent"


def cmd_data(names: list[str], check: bool = False) -> int:
    """data [svc] [--check] — 레지스트리 해석 결과(현행 → 목표·상태). --check 는 이동 대상 종류에 divergent·only-target 이 있으면 1.
    HWAX_DATA_ROOT 미설정이면 목표가 없으므로 상태는 only-current/absent 만 나온다."""
    root = data_root()
    box = box_name()
    print(f"  HWAX_DATA_ROOT={root or '(미설정 — 주입 없음, 현행 경로)'}  box={box}  role={_hwax_setting('HWAX_BOX_ROLE') or '-'}")
    raw = yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) or {}
    items: list[dict] = [s for s in load() if s.get("data") and (not names or s["name"] in names)]
    for dname, d in (raw.get("data_only") or {}).items():  # 기동 대상이 아닌 데이터만 등록된 것(슬럼 헤드 등)
        if not names or dname in names:
            items.append({"name": dname, "data": d, "_data_only": True})
    bad = 0
    for s in items:
        data = s["data"]
        sdir = None if s.get("_data_only") else resolve_dir(s)
        print(f"── {s['name']}{'  (data_only)' if s.get('_data_only') else ''}")
        for cname, c in (data.get("classes") or {}).items():
            if not isinstance(c, dict):
                continue
            curp, tgt = class_paths(s, cname, c, root, box)
            if c.get("kind") == "identity" or c.get("enabled") is False or (not c.get("path") and curp is None):
                st = "n/a"
            elif tgt is None:
                st = "only-current" if (curp is not None and (curp.exists() or curp.is_symlink())) else "absent"
            else:
                st = _data_status(curp, tgt)
            if st in ("divergent", "only-target") and c.get("kind") not in ("backup", "log", "cache"):   # 옮기지 않는 종류는 참고만
                bad = 1
            print(f"  {st:<13} {cname:<16} {str(c.get('kind', '-')):<9} {str(curp) if curp else '-'}  →  {str(tgt) if tgt else '-'}")
    return bad if check else 0


def load() -> list[dict]:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) or {}
    svcs = data.get("services", [])
    return sorted(svcs, key=lambda s: s.get("tier", 10))


def enabled_here(svc: dict) -> bool:
    """`only_on: <hostname|[hostnames]>` — 그 박스에서만 다루는 서비스(예: dev 전용 로컬 vLLM).
    다른 박스에선 up/down/update 가 조용히 skip 한다(공유 manifest 하나로 박스별 차이 표현)."""
    # `unless_env: <KEY>` — 그 설정이 **있는** 박스에서는 이 서비스가 다른 서버에서 돈다는 뜻이라 여기서 다루지
    # 않는다(예: RA_HOST 가 있으면 Report Archive 는 원격 서버쌍 — 로컬 항목을 띄우면 이사 전 DB 를 되살린다).
    # 박스 이름(only_on)이 아니라 사실(설정값)로 가른다 — cae00 호스트명이 바뀌거나 운영 박스가 늘어도 맞다.
    # `if_env: <KEY>` 는 그 거울이다 — 그 설정이 있는 박스에서만 다룬다(예: LLM_UPSTREAMS → LLM 라우터).
    if not _unless_env_allows(svc) or not _if_env_state(svc)[0]:
        return False
    only = svc.get("only_on")
    if not only:
        return True
    hosts = [only] if isinstance(only, str) else list(only)
    import socket
    return socket.gethostname() in hosts


def resolve_dir(svc: dict) -> Path | None:
    """Explicit dir wins; else auto-discover the repo by name in the usual roots."""
    if svc.get("dir"):
        d = Path(svc["dir"]).expanduser()
        return (PORTAL_ROOT / d).resolve() if not d.is_absolute() else d
    name = svc.get("discover")
    if not name:
        return None
    for root in (PARENT, Path.home() / "Projects", Path.home() / "claude"):
        cand = root / name
        if cand.is_dir():
            return cand
    return None


def health_ok(url: str, timeout: float = 2.0, expect: object = None) -> bool:
    """Any HTTP response (even 4xx) means the port is serving → up.

    expect 가 주어지면 상태코드까지 본다. 프록시 뒤에 있는 서비스는 '응답이 왔다'만으로는
    판정이 안 되기 때문이다 — heax-hub 는 Caddy(:4180)가 앞에 있어서 백엔드(:4040)가 죽어도
    정적 SPA 를 200 으로 돌려주고, 죽은 upstream 이면 502 가 오는데 그것도 '응답'이라 up 이
    됐다. 그래서 '앱이 죽었는데 초록' 이 구조적으로 가능했다.
    expect 가 없으면 종전 그대로다 — 406 을 up 으로 봐야 하는 항목들이 있어 전역 강제는 못 한다.
    """
    allowed = None
    if expect is not None:
        allowed = {int(c) for c in (expect if isinstance(expect, (list, tuple, set)) else [expect])}
    try:
        r = urllib.request.urlopen(url, timeout=timeout)  # noqa: S310 (trusted local/own URLs)
        return allowed is None or r.getcode() in allowed
    except urllib.error.HTTPError as e:
        return allowed is None or e.code in allowed  # 404/406 etc — it answered, so it's up
    except Exception:
        return False


def wait_health(url: str, tries: int = 60, gap: float = 2.0, tick=None, expect=None) -> bool:
    import time
    for i in range(tries):
        if health_ok(url, expect=expect):
            return True
        if tick:
            tick(i + 1, tries)  # 실패한 폴 직후 진행 알림(어디서 멈추는지 가시화)
        time.sleep(gap)
    return False


def env_prefix(env: dict | None) -> str:
    if not env:
        return ""
    return " ".join(f"{k}={shlex.quote(str(v))}" for k, v in env.items()) + " "


def start_one(svc: dict) -> str:
    name = svc["name"]
    url = health_url(svc)
    if url and health_ok(url, expect=svc.get("expect")):
        return "already-up"

    host = svc.get("host", "local")
    log = svc_log(svc)
    # 레지스트리 env(HWAX_DATA_ROOT 있을 때만) 위에 명시 env: 가 덮는다. 미설정이면 종전과 동일.
    inner = f"{env_prefix({**resolve_data(svc), **(svc.get('env') or {})})}{svc['start']}"

    if host == "local":
        wd = resolve_dir(svc)
        if not wd or not wd.is_dir():
            return f"FAIL: dir not found (discover={svc.get('discover')}, dir={svc.get('dir')})"
        prep_log(log)
        with open(log, "ab") as lf:
            lf.write(f"\n=== start {time.strftime('%Y-%m-%dT%H:%M:%S%z')}: {svc['start']}\n".encode())
        log_start = log.stat().st_size
        # Detached session: survives this orchestrator; foreground servers keep running.
        with open(log, "ab") as lf, open("/dev/null", "rb") as devnull:
            subprocess.Popen(  # noqa: S602 — commands come from our own manifest
                ["bash", "-c", inner], cwd=str(wd),
                stdout=lf, stderr=subprocess.STDOUT, stdin=devnull,
                start_new_session=True,
            )
    else:
        user = svc.get("ssh_user")
        if not user:
            return "FAIL: remote service needs ssh_user (key auth)"
        wd = svc.get("dir") or f"~/claude/{svc.get('discover', '')}"
        remote = f"cd {shlex.quote(wd)} && setsid bash -c {shlex.quote(inner)} " \
                 f"> /tmp/{name}.log 2>&1 < /dev/null &"
        subprocess.Popen(  # noqa: S603 — ssh with key auth, no password
            ["ssh", "-o", "BatchMode=yes", f"{user}@{host}", remote],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    if not url:
        return "started (no health url)"
    gap = 2.0
    tries = max(1, int(int(os.environ.get("HWAX_HEALTH_WAIT") or 120) / gap))   # 초. 이관기는 300 — HEAX 전체 재기동이 120s 를 넘긴다
    print(f"      ▸ {name}: health 대기 {url} (최대 {int(tries * gap)}s) …", flush=True)

    def _tick(i: int, n: int) -> None:
        if i != 1 and i % 5 != 0:      # ~10초마다(1회차 + 5의 배수)만 출력
            return
        # 서비스 자기 로그 꼬리를 함께 보여 heal.sh/기동 진행을 노출 — 원격은 로그가 이 박스에 없다
        last = _log_tail(log, log_start) if host == "local" else ""
        print(f"        · 대기 {int(i * gap)}s/{int(n * gap)}s"
              + (f"  | log꼬리: {last}" if last else "  | (로그 아직 없음)"), flush=True)

    return "up" if wait_health(url, tries, gap, _tick, expect=svc.get("expect")) else \
        f"FAIL: no health after start (see {log})"


def update_one(svc: dict) -> str:
    """Pull latest code (git ff-only by default; `update:` in the manifest overrides),
    streaming output live to the terminal AND the service log so a slow build / hang is
    visible where it happens. Remote/none-update services are skipped."""
    if svc.get("host", "local") != "local":
        return "skip (remote)"
    cmd = svc.get("update")
    if cmd is None:  # default: a safe fast-forward pull if it's a git repo
        # ⚠ 예전 명령은 `… && git pull --ff-only || echo 'no-git'` 이었다. bash 의 `A && B || C` 는
        # pull(B)이 실패해도 C 를 돌려 **rc 가 0** 이 된다. 그래서 로컬 수정·갈라진 이력·자격증명
        # 문제로 pull 이 막혀도 "updated: no-git" 으로 보고했고, 옛 코드로 기동한 뒤 update-all 이
        # 초록으로 끝났다(2026-09-17 cae00 점검 — 절차가 게이트웨이 옛 코드에 걸려 있었다).
        # 이제 git 리포가 아니면 먼저 빠지고, pull 실패는 rc 그대로 올라온다.
        cmd = ("git rev-parse --git-dir >/dev/null 2>&1 || { echo 'no-git'; exit 0; }; "
               "GIT_TERMINAL_PROMPT=0 git pull --ff-only")
    if cmd is False or cmd == "":  # explicit opt-out (e.g. vllm: stateless)
        return "skip"
    wd = resolve_dir(svc)
    if not wd or not wd.is_dir():
        return "FAIL: dir not found"
    logp = prep_log(svc_log(svc, wd))
    lines: list[str] = []

    def _head() -> str | None:  # git HEAD — 갱신 전/후를 비교해 '바뀌었나' 를 문자열("Already up to date")이 아니라 커밋으로 말한다
        try:
            r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(wd), capture_output=True, text=True, timeout=10)  # noqa: S603
            return r.stdout.strip() or None if r.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired):
            return None

    h0 = _head()
    with open(logp, "a", encoding="utf-8") as lf:
        lf.write(f"\n=== update START: {cmd}\n")
        lf.flush()
        proc = subprocess.Popen(  # noqa: S602 — manifest-owned cmd
            ["bash", "-c", cmd], cwd=str(wd),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        for line in proc.stdout:  # 라인 도착 즉시 화면+로그로 흘려 진행(빌드/pull)을 가시화
            lines.append(line)
            lf.write(line)
            lf.flush()
            print(f"        · {line.rstrip()}", flush=True)
        rc = proc.wait()
        if rc != 0:
            lf.write(f"=== update FAILED (rc={rc})\n")
    tail = lines[-1].strip() if lines else ""
    if rc == 0:
        h1 = _head()
        if h0 and h1:   # update-sites 가 이 마커로 재기동 생략을 정한다(docs/update-all-skip-unchanged D-5)
            mark = f"unchanged ({h1[:7]})" if h0 == h1 else f"{h0[:7]}→{h1[:7]}"
            return f"updated: {mark}" + (f" · {tail[:40]}" if tail else "")
    return ("updated" if rc == 0 else "FAIL") + (f": {tail[:60]}" if tail else "")


def _fp_noise(f: Path, top: Path) -> bool:
    """`fp:` 디렉터리 안의 파이썬 바이트코드(`__pycache__` · `*.pyc`) — import 한 번에 생기고 코드는 그대로다. 지문에 넣으면 시험이나 손 점검이
    모듈을 읽기만 해도 다음 update-all 이 그 서비스를 재기동한다(LLM 라우터 — docs/llm-pool LP-D13)."""
    return f.suffix == ".pyc" or "__pycache__" in f.relative_to(top).parts


def service_fp(svc: dict) -> str:
    """서비스 지문 — git HEAD + <dir>/.env 내용(+manifest `fp:` 경로들). update-sites 가 '마지막으로 띄운 시점' 의 지문과 비교해
    재기동 생략을 정한다(docs/update-all-skip-unchanged). 디렉터리를 못 찾으면 그 사실이 지문이다(모름 → 재기동).
    `fp_git: false` 면 git HEAD 도 <dir>/.env 도 넣지 않는다 — 남의 리포 안에 사는 작은 서비스(LLM 라우터는 포털 리포 안이다)가 그 리포의
    커밋마다(그리고 env-sync 가 덧붙이는 그 리포 루트 .env 마다) 재기동되지 않게. 그때는 `fp:` 경로만이 지문이다(docs/llm-pool LP-D10).
    `fp:` 디렉터리는 파일마다 크기·시각으로 넣되 바이트코드는 뺀다(_fp_noise)."""
    import hashlib
    wd = resolve_dir(svc)
    parts: list[str] = []
    if not wd or not wd.is_dir():
        parts.append("dir:missing")
    else:
        if svc.get("fp_git", True) is not False:
            try:
                r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(wd), capture_output=True, text=True, timeout=10)  # noqa: S603
                parts.append("git:" + (r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else "nogit"))
            except (OSError, subprocess.TimeoutExpired):
                parts.append("git:nogit")
        # .env + 매니페스트 data.identity(글롭·백업 제외) — 게이트웨이는 .env 가 없고 gateway_config.json·provision.env 가 동작을 정한다(2라운드).
        # identity 의 **디렉터리**는 넣지 않는다 — 이관용 신원 목록이라 런타임 상태 디렉터리(heax var/integration_state 는 celery 가 45초마다
        # 다시 쓴다)가 들어 있고, 그것을 지문에 넣으면 '변경 없음' 이 영영 성립하지 않아 매 회 전체 스택을 내렸다 올린다(3라운드). 디렉터리 지문이
        # 필요하면 매니페스트 `fp:` 에 명시한다(그쪽은 디렉터리도 rglob 로 넣는다).
        idents = [x for x in ((svc.get("data") or {}).get("identity") or []) if "*" not in str(x)]
        fps = list(svc.get("fp") or [])
        for rel in dict.fromkeys([".env", *idents, *fps]):
            if rel == ".env" and svc.get("fp_git", True) is False and rel not in idents and rel not in fps:
                continue   # fp_git: false — 남의 리포 루트 .env(env-sync 가 덧붙인다)는 이 서비스의 설정이 아니다(LP-D13)
            q = wd / rel
            if q.is_file():
                st = q.stat()
                parts.append(f"{rel}:{hashlib.sha256(q.read_bytes()).hexdigest()[:16]}" if st.st_size <= 32 * 1024 * 1024 else f"{rel}:{st.st_size}:{int(st.st_mtime)}")
            elif rel in idents and rel != ".env" and rel not in fps:
                continue   # identity 항목은 파일일 때만 — 디렉터리·없는 경로는 지문에 흔적을 남기지 않는다(생기는 순간 한 번 바뀌는 것도 막는다)
            elif q.is_dir():
                for f in sorted(x for x in q.rglob("*") if x.is_file() and not _fp_noise(x, q)):
                    st = f.stat(); parts.append(f"{f.relative_to(wd)}:{st.st_size}:{int(st.st_mtime)}")
            else:
                parts.append(f"{rel}:missing")
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()[:16]


def cmd_port(names: list[str]) -> int:
    """이 서비스가 듣는 포트 전부(한 줄에 하나, service_urls 와 **같은 순서**) — update-sites 가 '재기동이 실제로 됐나' 를 그 포트를 듣는
    프로세스로 확인한다(2라운드: already-up 이 새 지문을 적었다). 순서가 어긋나면 url↔리스너 짝이 밀린다."""
    from urllib.parse import urlparse
    svcs = [s for s in load() if not names or s["name"] in names]
    for s in svcs:
        for u in service_urls(s) or [""]:
            q = urlparse(u); port = q.port or (443 if q.scheme == "https" else 80 if q.scheme else "")
            print(str(port) if len(svcs) == 1 else f"{s['name']} {port}")
    return 0 if svcs else 1


_URLVAR_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


def service_urls(svc: dict) -> list[str]:
    """이 서비스가 **듣는 url 전부** — `health` + 매니페스트 `urls`. 재기동이 됐는지는 이 전부가 새 프로세스여야 한다(5라운드:
    하나만 갈렸는데 기록하면 그 인스턴스가 옛 코드로 영구 생략된다). `${KEY:-기본}` 은 infra/.env 를 정본 규칙(_infra_value)으로 푼다 —
    포털의 nginx 포트(HTTP_PORT)처럼 박스마다 다른 값을 매니페스트에 박지 않기 위한 것이다."""
    out: list[str] = []
    for u in [svc.get("health"), *(svc.get("urls") or [])]:
        t = _expand_url(u)
        if t and t not in out:
            out.append(t)
    return out


def _expand_url(u: object) -> str:
    def _sub(m: "re.Match[str]") -> str:
        try:
            v = _infra_value(m.group(1))
        except InfraEnvUnreadable:
            v = None
        return v if v else (m.group(2) or "")
    return _URLVAR_RE.sub(_sub, str(u or "")).strip()


def health_url(svc: dict) -> str:
    """기동 대기·상태·정지가 두드리는 health — `${KEY:-기본}` 을 service_urls 와 같은 규칙으로 푼다. 풀지 않고 두드리면 포트 자리의
    `${…}` 때문에 늘 '죽었다' 로 읽혀 up 이 이미 뜬 것을 또 띄우고 status 는 영구 ✗ 다(LLM 라우터의 LLM_ROUTER_PORT — docs/llm-pool)."""
    return _expand_url(svc.get("health"))


def cmd_health(names: list[str]) -> int:
    """이 서비스가 듣는 url 전부(한 줄에 하나) — update-sites 가 내려감 대기·생존·리스너 비교에 쓴다. 포트만으로 루트(/)를 두드리면
    루트가 404 인 서비스(agent-server)는 살아 있어도 '내려갔다' 로 읽혀 대기가 무효가 된다(3라운드). 여러 이름을 주면 `<이름> <url>` 로 낸다."""
    svcs = [s for s in load() if not names or s["name"] in names]
    for s in svcs:
        for u in service_urls(s) or [""]:
            print(u if len(svcs) == 1 else f"{s['name']} {u}")
    return 0 if svcs else 1


def cmd_fp(names: list[str]) -> int:
    svcs = [s for s in load() if not names or s["name"] in names]
    for s in svcs:
        print(service_fp(s) if len(svcs) == 1 else f"{s['name']} {service_fp(s)}")
    return 0 if svcs else 1


def cmd_update(names: list[str]) -> int:
    svcs = [s for s in load() if not names or s["name"] in names]
    rc = 0
    for s in svcs:
        if not enabled_here(s):
            print(f"  · {s['name']:<16} skip ({skip_reason(s)})")
            continue
        r = update_one(s)
        if r.startswith("FAIL"):
            rc = 1
        print(f"  {'✗' if r.startswith('FAIL') else '·'} {s['name']:<16} {r}")
    return rc


def cmd_up(names: list[str], do_update: bool = False) -> int:
    svcs = [s for s in load() if not names or s["name"] in names]
    rc = 0
    cur_tier = None
    for s in svcs:
        if s.get("tier") != cur_tier:
            cur_tier = s.get("tier")
            print(f"── tier {cur_tier} ──", flush=True)
        if not enabled_here(s):
            print(f"  · {s['name']:<16} skip ({skip_reason(s)} — 이 박스 대상 아님)", flush=True)
            continue
        if do_update:
            print(f"  ↻ {s['name']:<16} update …", flush=True)
            up = update_one(s)
            # 갱신 실패는 **종료코드로** 올린다 — 기동은 그대로 하되(옛 코드라도 서비스는 떠 있어야
            # 한다) 부르는 쪽(update-sites·update-all §4)이 초록으로 끝내지 않게 한다.
            if up.startswith("FAIL"):
                rc = 1
            print(f"  {'✗' if up.startswith('FAIL') else '↻'} {s['name']:<16} {up}", flush=True)
        print(f"  ▷ {s['name']:<16} start + health …", flush=True)
        r = start_one(s)
        mark = "✓" if r in ("up", "already-up", "started (no health url)") else "✗"
        if mark == "✗":
            rc = 1
        print(f"  {mark} {s['name']:<16} {r}", flush=True)
    return rc


def cmd_status(names: list[str]) -> int:
    svcs = [s for s in load() if not names or s["name"] in names]
    any_down = 0
    for s in svcs:
        if not enabled_here(s):
            print(f"  {'· skip':<12} {s['name']:<16} {skip_reason(s)}")
            continue
        url = health_url(s)
        up = health_ok(url, expect=s.get("expect")) if url else None
        mark = "✓ up" if up else ("? no-health" if up is None else "✗ down")
        if up is False:
            any_down = 1
        host = s.get("host", "local")
        print(f"  {mark:<12} {s['name']:<16} {host:<14} {url}")
    return any_down


def cmd_down(names: list[str]) -> int:
    # Reverse tier order. Use an explicit `stop:` if the manifest gives one; otherwise
    # best-effort kill by the health port (local only). Remote down is left to `stop:`.
    svcs = [s for s in load() if not names or s["name"] in names]
    for s in reversed(svcs):
        name = s["name"]
        if not enabled_here(s):
            print(f"  · {name}: skip ({skip_reason(s)})")
            continue
        if s.get("stop"):
            wd = resolve_dir(s)
            subprocess.run(["bash", "-c", s["stop"]], cwd=str(wd) if wd else None, check=False)
            print(f"  • {name}: ran stop")
            continue
        url = health_url(s)
        port = url.rsplit(":", 1)[-1].split("/")[0] if ":" in url else ""
        if s.get("host", "local") == "local" and port.isdigit():
            subprocess.run(  # noqa: S607
                ["bash", "-c", f"fuser -k {port}/tcp 2>/dev/null || true"], check=False
            )
            print(f"  • {name}: killed :{port}")
        else:
            print(f"  • {name}: no stop defined (remote/unknown) — skip")
    return 0


def cmd_enabled(names: list[str]) -> int:
    """이 박스가 그 서비스의 대상인가 — 종료코드로만 답한다(0=대상, 1=아님, 2=그런 서비스 없음).

    왜 있나 — 호스트명 비교를 부르는 쪽마다 복제하면 정본이 둘이 된다. 실제로 헬스게이트가
    `only_on` 을 안 보고 searxng 를 두드려, 같은 화면에서 "✗ 죽었다" 와 "이 박스 대상 아님" 이
    나란히 찍혔다(2026-09-20 cae00). 사람이 읽고 진짜 고장으로 오해하는 자리다.
    조용히 쓰라고 만든 것이라 출력이 없다 — 부르는 쪽이 자기 문구로 말한다."""
    svcs = {s["name"]: s for s in load()}
    for n in names:
        svc = svcs.get(n)
        if svc is None:
            return 2
        if not enabled_here(svc):
            return 1
    return 0


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in ("up", "down", "status", "update", "data", "enabled", "fp", "port", "health"):
        print(__doc__)
        return 2
    action = sys.argv[1]
    args = sys.argv[2:]
    do_update = "--update" in args
    names = [a for a in args if not a.startswith("-")]
    if action == "up":
        return cmd_up(names, do_update=do_update)
    if action == "enabled":  # 이 박스 대상인가(종료코드로만) — 헬스게이트가 only_on 을 보게 한다
        # 판정이 죽으면 2(모름)다 — 잡히지 않은 예외는 파이썬이 1 로 끝내 '이 박스 대상 아님' 과 똑같아진다(10-17: 매니페스트가 없는
        # 사본에서 상태판 · 호출 추적 이미지가 '꺼짐' 으로 빠졌다). 1 은 판정이 끝까지 돈 때만 낸다.
        try:
            return cmd_enabled(names)
        except Exception as e:  # noqa: BLE001
            print(f"services.py enabled: 판정 실패 — {e}", file=sys.stderr)
            return 2
    if action == "data":  # 데이터 경로 레지스트리 조회·검증(docs/data-migration)
        return cmd_data(names, check="--check" in args)
    return {"status": cmd_status, "down": cmd_down, "update": cmd_update, "fp": cmd_fp, "port": cmd_port, "health": cmd_health}[action](names)


if __name__ == "__main__":
    raise SystemExit(main())
