#!/usr/bin/env bash
# LLM 서버 풀(LLM_UPSTREAMS)의 규칙 한 곳 — 목록 검사 · 라우터 주소 · 지금 써야 할 주소 · 관리하는 사본 목록 · 사본 바꾸기(백업 먼저).
#
# 왜 — LLM 주소의 정본은 포털 infra/.env 의 LLM_BASE_URL 하나인데, 서비스마다 자기 .env 에 사본을 든다(에이전트 서버 VLLM_BASE_URL ·
# AIDataHub OPENAI_BASE_URL·LLM_BASE_URL · SignalForge · 허브 앱 · MXWhitePaper …). 설정 킷(apply-envs)은 없는 키만 더하므로 정본만
# 바꾸면 사본들은 조용히 옛 주소로 돈다(docs/llm-pool LP-D4 — 무음 결함 다섯째 '앱은 정상, env 만 빠졌다' 와 같은 꼴). 그래서 풀을 켜고
# 끌 때 사본을 함께 바꾸는 규칙을 여기 한 곳에 두고 update-all 1i · apply-envs 의 @FROM_RA:LLM_BASE_URL@ · update-sites 의 라우터 재기동
# 미룸 · §6 이 같은 규칙을 쓴다. 정의만 있다 — 소싱해도 아무 일도 하지 않는다.
#
#   . "$ROOT/infra/scripts/lib/llm-pool.sh"
#   hwax_llm_envv <파일> <키>               값 하나 — update-all 의 _envfile_value 와 **글자 단위로 같은 규칙**(마지막 활성 줄 · `export` 허용 ·
#                                            공백 뒤 `#` 주석 · 따옴표·CR 제거). 없거나 빈 값이면 빈 문자열. 라우터도 infra/.env 를 이 규칙으로 읽는다.
#   hwax_llm_pool_upstreams <infra.env>     LLM_UPSTREAMS 를 검사해 서버 주소를 한 줄에 하나 찍는다(끝 `/` 는 뗀다). 쉼표·공백으로 나눈다.
#       0 = 켜짐 · 1 = 없다(꺼짐) · 2 = 모양이 틀렸다 — 사유 한 줄을 찍는다. **하나라도 틀리면 줄 전체를 버린다**(반만 맞는 목록으로
#       라우터를 띄우거나 사본을 바꾸지 않게 — 부르는 쪽은 아무것도 바꾸지 않는다).
#   hwax_llm_router_url <infra.env>         라우터 주소 http://127.0.0.1:<LLM_ROUTER_PORT, 기본 9130>/v1 · 2 = 포트가 틀렸다(사유를 찍는다).
#   hwax_llm_router_health_url <infra.env>  라우터 /health 주소(같은 포트).
#   hwax_llm_router_health <health url>     라우터 /health 를 읽어 "<status> <올라온 서버> <전체> <도는 요청> <모델 같음>" 을 찍는다(모르는 칸은 ?).
#       0 = 라우터가 답했다(down 의 503 도 답이다) · 2 = 답이 없다 · JSON 이 아니다 · 라우터의 답이 아니다(upstreams_total 이 없다 —
#       같은 포트에 다른 것이 떠 있다).
#   hwax_llm_router_busy <health url>       라우터를 지나는 요청(inflight)이 **확실한** 양의 정수면 그 수를 찍고 0 · 0 이면 1 · 모르면 2.
#       LLM_ROUTER_RESTART_FORCE=1 이면 묻지 않고 1 — 사람이 끊기로 한 것이다. 부르는 쪽은 **0 일 때만** 미룬다 — 모르는데 미루면 죽은·
#       매달린 라우터를 영영 못 띄우고 새 코드를 영영 못 올린다(delib-busy 와 같은 규율).
#   hwax_llm_effective_url <infra.env> [직접 주소]   LLM 클라이언트가 **지금** 써야 할 주소 — 풀이 켜져 있고 라우터가 서버 하나 이상이
#       올라왔다고 답하면 라우터 주소, 아니면 직접 주소(주지 않으면 infra/.env 의 LLM_BASE_URL). 0 = 찍었다 · 1 = 빈 값.
#       1i 가 사본을 라우터로 바꾸는 조건과 같다 — 라우터가 그렇게 답하지 않을 때 새로 더한 키만 죽은 라우터를 보지 않게(stderr 에 한 줄).
#   hwax_llm_pool_copies <포털 루트>         관리하는 사본 — 줄마다 "<서비스>\t<리포 이름>\t<.env 상대경로>\t<키>". apply-envs 의 MAP 과 킷의
#       `<키>=@FROM_RA:LLM_BASE_URL@` 줄에서 유도하고(킷에 줄이 늘면 저절로 따라온다), 서비스 코드가 직접 읽는 키(_HWAX_LLM_EXTRA)를 더한다.
#   hwax_llm_pool_rewrite <포털 루트> <dry|write> <새 값> <관리하는 값…>
#       사본 가운데 지금 값(끝 `/` 무시)이 관리하는 값인 것만 새 값으로 바꾼다. 바꾸기 **전에** 그 파일을 같은 디렉터리의
#       `<파일>.bak-<UTC 시각>` 으로 백업하고(권한 그대로 — 비밀 파일은 600 그대로, 만드는 순간부터 600), 그 값의 글자 말고는 파일을
#       한 바이트도 바꾸지 않는다(따옴표·`export`·줄 끝 주석·CRLF·다른 줄 그대로). 같은 파일에 키가 둘이면 백업은 한 번이다.
#       줄마다 "<상태>\t<서비스>\t<리포 경로>\t<.env 상대경로>\t<키>\t<지금 값>\t<백업 경로>" — 상태는
#       changed(바꿨다) · would(dry — 바꿀 것이다) · same(이미 새 값) · foreign(관리하는 값이 아니다 — 사람이 적은 다른 주소, 그대로 둔다) ·
#       absent(파일·키가 없다 — apply-envs 몫) · error(못 바꿨다 — 지금 값 칸에 사유, 파일은 그대로). 리포가 없는 사본은 줄을 내지
#       않는다(이 박스 대상이 아니다). 리포는 apply-envs·update-all 의 find_repo 와 같은 순서로 찾는다(<포털 상위>/ → ~/Projects/ → ~/claude/).
#   hwax_llm_pool_at <포털 루트> <주소>      지금 그 주소를 가리키는 사본 수(끝 `/` 무시).
#
# ⚠ 0 아닌 값을 정상으로 돌려준다 — `set -e` 스크립트에서는 `_x="$(hwax_llm_… )" || _rc=$?` 로 받는다. 맨 문장이면 1·2 에서 조용히 끝난다.

# 서비스 코드가 직접 읽는데 킷의 @FROM_RA:LLM_BASE_URL@ 줄에는 없는 사본 — 코드로 확인한 것만 적는다(2026-10-15).
#   ai-data-hub    LLM_BASE_URL — api_server chat_svc.py 가 OPENAI_BASE_URL 보다 **먼저** 읽는다(데이터 챗). deploy/apptainer/.env 는
#                  start_api.sh(load_env)가 set -a 로 소싱해 프로세스 환경이 된다.
#   mx-white-paper LLM_BASE_URL — apps/api config.py 의 llm_base_url(pydantic env_file .env · 인스턴스는 --env-file .env).
#   HEAXHub 자신은 LLM_BASE_URL 을 읽지 않는다(자기 LLM 은 LLM_LOCAL_ENDPOINT — OpenAI /v1 이 아니다). 허브 앱은 HEAX_APP_LLM_BASE_URL
#   (킷 줄)을 LLM_BASE_URL 로 바꿔 받는다. HWAXRisk 는 LLM 을 직접 부르지 않는다(카드 대조는 에이전트 서버가 부른다).
_HWAX_LLM_EXTRA=(
  $'ai-data-hub\tAIDataHub\tdeploy/apptainer/.env\tLLM_BASE_URL'
  $'mx-white-paper\tMXWhitePaper\t.env\tLLM_BASE_URL'
)

hwax_llm_envv() {  # $1=파일 $2=키 — update-all _envfile_value 와 같은 줄(그 머리 주석의 까닭 그대로: LC_ALL=C · 주석을 벗긴 뒤에 공백)
  sed -n -E "s/^[[:space:]]*(export[[:space:]]+)?$2=//p" "$1" 2>/dev/null | tail -1 \
    | LC_ALL=C sed -E 's/[[:space:]]+#.*$//; s/^[[:space:]]+//; s/[[:space:]]+$//' | LC_ALL=C tr -d '"'"'"'\r'
}

_hwax_llm_raw() {  # $1=파일 $2=키 — 같은 줄의 원문(주석·양끝 공백·CR 만 벗긴다 — 따옴표는 남긴다)
  sed -n -E "s/^[[:space:]]*(export[[:space:]]+)?$2=//p" "$1" 2>/dev/null | tail -1 \
    | LC_ALL=C sed -E 's/[[:space:]]+#.*$//; s/^[[:space:]]+//; s/[[:space:]]+$//' | LC_ALL=C tr -d '\r'
}

_hwax_llm_port() {  # $1=infra.env → 라우터 포트(기본 9130) · 2 = 틀렸다(사유)
  local p
  p="$(hwax_llm_envv "$1" LLM_ROUTER_PORT)"
  if [ -z "$p" ]; then printf '9130\n'; return 0; fi
  if [[ "$p" =~ ^[0-9]{1,5}$ ]] && [ "$((10#$p))" -ge 1 ] && [ "$((10#$p))" -le 65535 ]; then
    printf '%s\n' "$((10#$p))"; return 0
  fi
  printf "LLM_ROUTER_PORT 는 1~65535 의 수여야 한다: '%s'\n" "$p"; return 2
}

hwax_llm_router_url() {  # $1=infra.env
  local p rc=0
  p="$(_hwax_llm_port "$1")" || rc=$?
  if [ "$rc" != 0 ]; then printf '%s\n' "$p"; return 2; fi
  printf 'http://127.0.0.1:%s/v1\n' "$p"
}

hwax_llm_router_health_url() {  # $1=infra.env
  local u rc=0
  u="$(hwax_llm_router_url "$1")" || rc=$?
  if [ "$rc" != 0 ]; then printf '%s\n' "$u"; return 2; fi
  printf '%s/health\n' "${u%/v1}"
}

hwax_llm_pool_upstreams() {  # $1=infra.env
  local v raw u host port rport re out="" seen=" " n=0
  local -a items
  v="$(hwax_llm_envv "$1" LLM_UPSTREAMS)"
  [ -n "$v" ] || return 1
  # 따옴표 밖의 공백은 받지 않는다 — infra/.env 는 포털 start.sh(_common.sh)가 `set -a; . infra/.env` 로 소싱한다. `A=x y` 는 bash 에서
  # 'y' 를 명령으로 돌리고(그 대입은 남지 않는다) set -e 인 기동이 그 자리에서 죽는다. 이 독자는 공백을 나눔표로 읽어 맞는 목록으로 볼 것이라
  # 여기서 막지 않으면 update-all 은 초록인데 다음 포털 기동이 죽는다.
  raw="$(_hwax_llm_raw "$1" LLM_UPSTREAMS)"
  case "$raw" in
    \"*|\'*) ;;
    *[[:space:]]*) printf '%s\n' "LLM_UPSTREAMS 의 공백이 따옴표 밖에 있다 — infra/.env 는 포털 start.sh 가 bash 로 소싱해 공백 뒤가 명령이 되고 기동이 죽는다. 쉼표로만(공백 없이) 나누거나 값 전체를 큰따옴표로 감싼다"
                   return 2 ;;
  esac
  rport="$(_hwax_llm_port "$1")" || rport=""
  # 호스트 규칙은 1e(RA_HOST)와 같다 — IPv4 또는 라벨(영숫자, 안쪽 하이픈)을 점으로 이은 이름. 경로는 vLLM(OpenAI 호환)의 /v1 로 끝난다.
  # 계정(user@)·질의(?)·조각(#)·IPv6 은 받지 않는다.
  re='^https?://([A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?(\.[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?)*)(:([0-9]{1,5}))?(/[A-Za-z0-9._~-]+)*/v1$'
  IFS=$', \t' read -ra items <<<"$v"
  for u in ${items[@]+"${items[@]}"}; do
    [ -n "$u" ] || continue
    while [ "${u%/}" != "$u" ]; do u="${u%/}"; done
    if ! [[ "$u" =~ $re ]]; then
      printf '%s\n' "LLM_UPSTREAMS 에 쓸 수 없는 주소가 있다: '$u' — vLLM 의 /v1 주소(http(s)://<호스트>[:<포트>]/…/v1)여야 한다(계정·질의·IPv6 은 받지 않는다)"
      return 2
    fi
    host="${BASH_REMATCH[1],,}"; port="${BASH_REMATCH[6]}"
    if [ -n "$port" ] && { [ "$((10#$port))" -lt 1 ] || [ "$((10#$port))" -gt 65535 ]; }; then
      printf '%s\n' "LLM_UPSTREAMS 의 포트가 1~65535 밖이다: '$u'"; return 2
    fi
    case "$host" in
      localhost|127.*)
        if [ -n "$rport" ] && [ -n "$port" ] && [ "$((10#$port))" = "$rport" ]; then
          printf '%s\n' "LLM_UPSTREAMS 가 라우터 자신을 가리킨다: '$u' — 서버(vLLM)의 /v1 주소를 적는다(라우터 주소는 update-all 이 사본에 적는다)"; return 2
        fi ;;
    esac
    case "$seen" in
      *" $u "*) printf '%s\n' "LLM_UPSTREAMS 에 같은 주소가 두 번 있다: '$u' — 서버마다 한 번씩 적는다"; return 2 ;;
    esac
    seen="$seen$u "; out="$out$u"$'\n'; n=$((n + 1))
  done
  if [ "$n" = 0 ]; then printf '%s\n' "LLM_UPSTREAMS 에 주소가 하나도 없다: '$v'"; return 2; fi
  printf '%s' "$out"
}

hwax_llm_router_health() {  # $1=health url
  local body rc=0
  # 로컬 health 다 — 운영자 셸의 http_proxy 를 타면 프록시가 이 박스의 루프백에 못 닿아 '모름' 이 된다(delib-busy 와 같다).
  body="$(curl -s --noproxy '*' -m 4 "$1" 2>/dev/null)" || rc=$?
  { [ "$rc" = 0 ] && [ -n "$body" ]; } || return 2
  B="$body" python3 - <<'PY'
import json, os, sys
try:
    h = json.loads(os.environ["B"])
except ValueError:
    sys.exit(2)
if not isinstance(h, dict) or "upstreams_total" not in h:
    sys.exit(2)                        # 라우터의 답이 아니다 — 같은 포트에 다른 것이 떠 있다
def n(v):
    return v if isinstance(v, int) and not isinstance(v, bool) and v >= 0 else "?"
models = h.get("models") if isinstance(h.get("models"), dict) else {}
match = models.get("match")
match = "true" if match is True else ("false" if match is False else "?")
status = h.get("status") if h.get("status") in ("ok", "degraded", "down") else "?"
print(status, n(h.get("upstreams_up")), n(h.get("upstreams_total")), n(h.get("inflight")), match)
PY
}

hwax_llm_router_busy() {  # $1=health url
  local h rc=0 st up tot inf m
  [ "${LLM_ROUTER_RESTART_FORCE:-0}" = 1 ] && return 1
  h="$(hwax_llm_router_health "$1")" || rc=$?
  [ "$rc" = 0 ] || return 2
  read -r st up tot inf m <<<"$h"
  case "${inf:-}" in ''|*[!0-9]*) return 2 ;; esac
  [ "$inf" -gt 0 ] || return 1
  printf '%s\n' "$inf"
}

hwax_llm_effective_url() {  # $1=infra.env [$2=직접 주소]
  local direct rurl h rc=0 st up rest
  if [ "$#" -ge 2 ]; then direct="$2"; else direct="$(hwax_llm_envv "$1" LLM_BASE_URL)"; fi
  if hwax_llm_pool_upstreams "$1" >/dev/null && rurl="$(hwax_llm_router_url "$1")"; then
    h="$(hwax_llm_router_health "$(hwax_llm_router_health_url "$1")")" || rc=$?
    read -r st up rest <<<"$h"
    if [ "$rc" = 0 ] && [[ "${up:-}" =~ ^[0-9]+$ ]] && [ "$up" -ge 1 ]; then
      printf '%s\n' "$rurl"; return 0
    fi
    printf '%s\n' "   · LLM 풀이 켜져 있는데 라우터($rurl)가 올라온 서버를 답하지 않는다 — 직접 주소를 쓴다(라우터가 살아나면 update-all 1i 가 사본을 라우터로 바꾼다)" >&2
  fi
  [ -n "$direct" ] || return 1
  printf '%s\n' "$direct"
}

hwax_llm_pool_copies() {  # $1=포털 루트
  local root="$1" svc repo rel key kit x
  {
    while read -r svc repo rel; do
      kit="$root/infra/env-kits/$svc.env"
      [ -f "$kit" ] || continue
      while read -r key; do
        [ -n "$key" ] && printf '%s\t%s\t%s\t%s\n' "$svc" "$repo" "$rel" "$key"
      done < <(sed -n -E 's/^([A-Z_][A-Z0-9_]*)=@FROM_RA:LLM_BASE_URL@[[:space:]]*$/\1/p' "$kit")
    done < <(sed -n -E '/^declare -A MAP=\(/,/^\)/ s/^[[:space:]]*\[([A-Za-z0-9_-]+)\]="([^":]+):([^"]+)".*$/\1 \2 \3/p' \
               "$root/infra/env-kits/apply-envs.sh" 2>/dev/null)
    for x in "${_HWAX_LLM_EXTRA[@]}"; do printf '%s\n' "$x"; done
  } | LC_ALL=C sort -u
}

hwax_llm_pool_rewrite() {  # $1=포털 루트 $2=dry|write $3=새 값 $4…=관리하는 값
  local root="$1" mode="$2" new="$3"
  shift 3
  case "$mode" in dry|write) ;; *) echo "hwax_llm_pool_rewrite: dry 또는 write 다 — '$mode'" >&2; return 2 ;; esac
  [ -n "$new" ] || { echo "hwax_llm_pool_rewrite: 새 값이 비었다 — 사본을 빈 주소로 바꾸지 않는다" >&2; return 2; }
  HWAX_LLM_COPIES="$(hwax_llm_pool_copies "$root")" HWAX_LLM_ROOT="$root" HWAX_LLM_MODE="$mode" HWAX_LLM_NEW="$new" \
    python3 - "$@" <<'PY'
import os, re, shutil, sys, time
from pathlib import Path

root = Path(os.environ["HWAX_LLM_ROOT"]).resolve()
mode, new = os.environ["HWAX_LLM_MODE"], os.environ["HWAX_LLM_NEW"]
norm = lambda s: s.rstrip("/")
managed = {norm(m) for m in sys.argv[1:] if m.strip()}
home = Path(os.environ.get("HOME") or "/nonexistent")
bases = (root.parent, home / "Projects", home / "claude")      # find_repo 와 같은 순서


def repo_dir(name):
    for b in bases:
        if (b / name).is_dir():
            return b / name
    return None


# update-all _envfile_value 와 같은 규칙 — 줄 머리([[:space:]]*, export 허용), 공백 뒤 # 주석, 양끝 공백, 따옴표·CR
WS = rb" \t\v\f\r"
def value_of(body: bytes) -> str:
    v = re.sub(rb"[" + WS + rb"]+#.*$", b"", body)
    v = v.strip(WS).replace(b'"', b"").replace(b"'", b"").replace(b"\r", b"")
    return v.decode("utf-8", "surrogateescape")


groups = {}                                                   # 파일 → [(서비스, 리포, 상대경로, 키)] — 백업은 파일마다 한 번
for ln in os.environ.get("HWAX_LLM_COPIES", "").splitlines():
    parts = ln.split("\t")
    if len(parts) != 4:
        continue
    svc, repo, rel, key = parts
    d = repo_dir(repo)
    if d is None:
        continue                                              # 이 박스에 그 리포가 없다 — 대상 아님
    groups.setdefault(d / rel, []).append((svc, d, rel, key))

rows = []
ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
for path, entries in groups.items():
    if not path.is_file():
        rows += [["absent", s, d, r, k, "", ""] for s, d, r, k in entries]
        continue
    try:
        data = path.read_bytes()
    except OSError as e:
        rows += [["error", s, d, r, k, f"읽지 못했다({e.strerror})", ""] for s, d, r, k in entries]
        continue
    lines = data.splitlines(keepends=True)
    edits, mine = {}, []
    for svc, d, rel, key in entries:
        pat = re.compile(rb"^[" + WS + rb"]*(?:export[" + WS + rb"]+)?" + re.escape(key.encode()) + rb"=")
        idx = [i for i, l in enumerate(lines) if pat.match(l)]
        if not idx:
            mine.append(["absent", svc, d, rel, key, "", ""])
            continue
        i = idx[-1]                                            # 읽는 쪽(tail -1)과 같은 줄을 고친다
        line = lines[i]
        head = pat.match(line).end()
        body = line[head:]
        eol = b""
        for e in (b"\r\n", b"\n", b"\r"):
            if body.endswith(e):
                eol, body = e, body[: -len(e)]
                break
        cur = value_of(body)
        if cur and norm(cur) == norm(new):
            mine.append(["same", svc, d, rel, key, cur, ""])
            continue
        if not cur or norm(cur) not in managed:
            mine.append(["foreign", svc, d, rel, key, cur, ""])  # 사람이 일부러 적은 다른 주소(또는 빈 값) — 건드리지 않는다
            continue
        # 값의 글자만 바꾼다 — 앞뒤 공백·감싼 따옴표·줄 끝 주석·줄 끝은 그대로
        cm = re.search(rb"[ \t\v\f]+#.*$", body)
        comment = body[cm.start():] if cm else b""
        core = body[: cm.start()] if cm else body
        lead = core[: len(core) - len(core.lstrip(b" \t"))]
        core = core[len(lead):]
        stripped = core.rstrip(b" \t")
        trail, core = core[len(stripped):], stripped
        q = core[:1] if len(core) >= 2 and core[:1] in (b'"', b"'") and core[-1:] == core[:1] else b""
        edits[i] = line[:head] + lead + q + new.encode() + q + trail + comment + eol
        mine.append(["changed" if mode == "write" else "would", svc, d, rel, key, cur, ""])
    if edits and mode == "write":
        bak = None
        for k in range(100):                                   # 같은 초에 다시 돌아도 앞 백업을 덮지 않는다
            cand = path.with_name(f"{path.name}.bak-{ts}" + (f"-{k}" if k else ""))
            try:
                fd = os.open(cand, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)   # 만드는 순간부터 600 — 비밀 사본이 잠깐도 열리지 않게
            except FileExistsError:
                continue
            except OSError as e:
                bak = e
                break
            try:
                with os.fdopen(fd, "wb") as f:
                    f.write(data)
                shutil.copystat(path, cand)                     # 권한·시각을 원본과 같게(644 면 644, 600 이면 600)
                bak = cand
            except OSError as e:
                bak = e
            break
        if not isinstance(bak, Path):
            why = f"백업을 만들지 못했다({getattr(bak, 'strerror', None) or '이름이 다 찼다'}) — 파일은 그대로다"
            mine = [["error", *r[1:5], why, ""] if r[0] == "changed" else r for r in mine]
        else:
            try:
                with open(path, "r+b") as f:                    # 제자리 — inode·권한·소유자 그대로(_upsert_kv 와 같다)
                    f.write(b"".join(edits.get(i, l) for i, l in enumerate(lines)))
                    f.truncate()
                mine = [[*r[:6], str(bak)] if r[0] == "changed" else r for r in mine]
            except OSError as e:
                why = f"쓰지 못했다({e.strerror}) — 백업 {bak} 로 되돌린다: cp -p '{bak}' '{path}'"
                mine = [["error", *r[1:5], why, str(bak)] if r[0] == "changed" else r for r in mine]
    rows += mine

for r in rows:
    print("\t".join(str(x) for x in r))
PY
}

hwax_llm_pool_at() {  # $1=포털 루트 $2=주소
  hwax_llm_pool_rewrite "$1" dry "$2" "$2" | awk -F'\t' '$1 == "same" { n++ } END { print n + 0 }'
}
