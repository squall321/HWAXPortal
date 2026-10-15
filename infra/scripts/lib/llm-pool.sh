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
#       올라왔고 모델이 같다고 답하면 라우터 주소, 아니면 직접 주소(주지 않으면 infra/.env 의 LLM_BASE_URL). 0 = 찍었다 · 1 = 빈 값.
#       1i 가 사본을 라우터로 바꾸는 조건과 같다 — 라우터가 그렇게 답하지 않을 때 새로 더한 키만 라우터를 보지 않게(stderr 에 한 줄).
#   hwax_llm_router_recorded <포털 루트>    1i 가 마지막으로 사본에 적은 라우터 주소(infra/.state/llm-pool.router) — 0 = 찍었다 · 1 = 없다
#       (기록이 없거나 루프백 /v1 주소 모양이 아니다). 포트를 바꾸거나 포트 줄을 풀과 함께 지워도 옛 라우터를 가리키는 사본을 찾는 데 쓴다.
#   hwax_llm_router_record <포털 루트> <주소>   그 기록을 바꾼다(임시 파일 + 이름 바꾸기). 0 = 적었다 · 1 = 못 적었다.
#   hwax_llm_pool_copies <포털 루트>         관리하는 사본 — 줄마다 "<서비스>\t<리포 이름>\t<.env 상대경로>\t<키>". apply-envs 의 MAP 과 킷의
#       `<키>=@FROM_RA:LLM_BASE_URL@` 줄에서 유도하고(킷에 줄이 늘면 저절로 따라온다), 서비스 코드가 직접 읽는 키(_HWAX_LLM_EXTRA)를 더한다.
#   hwax_llm_pool_rewrite <포털 루트> <dry|write> <새 값> <관리하는 값…>
#       사본 가운데 지금 값(끝 `/` 무시)이 관리하는 값인 것만 새 값으로 바꾼다. 바꾸기 **전에** 그 파일을 **포털의** gitignore 된
#       `infra/.state/llm-pool-backups/<리포 이름>/<.env 상대경로>.<UTC 시각>[-n]` 으로 백업한다(디렉터리 700 · 파일 600 — 만드는 순간부터).
#       서비스 리포 안에 두지 않는다 — 그쪽은 gitignore 밖이라 추적 안 된 비밀 파일로 남고 deploy-all 의 `git stash push -u` 가 비밀째
#       stash 로 쓸어 간다(반대 검토 H1). 바꾸기는 원자적이다 — 같은 디렉터리의 임시 파일에 쓰고 fsync 한 뒤 이름을 바꾼다(심링크면 링크는 두고
#       가리키는 파일을 바꾼다 · 권한·소유자 그대로 — 소유자를 지킬 수 없으면 바꾸지 않는다). 단 이름 바꾸기가 무언가를 잃는 파일은 백업 뒤
#       **제자리에** 쓴다(같은 inode — LP-D14) — ACL 이 있다(새 파일은 모드만 받아 이름 붙은 사용자가 사라지고 그룹 칸이 마스크로 넓어진다) ·
#       하드 링크가 둘 이상이다(다른 이름이 옛 주소에 남는다) · 디렉터리에 쓸 수 없다(이름을 못 바꾼다). 제자리 쓰기가 도중에 막히면(디스크가
#       찼다) 원래 내용을 다시 쓴다. 그 값의 글자 말고는 파일을 한 바이트도 바꾸지
#       않는다(따옴표·`export`·줄 끝 주석·CRLF·다른 줄 그대로). 줄은 `\n` 으로만 나눈다(홀로 선 `\r` 은 줄바꿈이 아니다 — 읽는 쪽 sed 와 같다).
#       같은 파일에 키가 둘이면 백업은 한 번이다. 쓸 수 없는 파일(읽기 전용)은 백업도 만들지 않고, 쓰다 실패하면 — 파일이 그대로면 — 만든
#       백업을 지운다(제자리 쓰기가 반쯤 바꿨으면 백업을 남기고 사유에 되돌리는 cp 를 적는다).
#       줄마다 "<상태>\t<서비스>\t<리포 경로>\t<.env 상대경로>\t<키>\t<지금 값>\t<백업 경로>[\t<쓴 방법>]" — 상태는
#       changed(바꿨다 — 제자리에 썼으면 여덟째 칸에 그 사실과 까닭) · would(dry — 바꿀 것이다) · same(이미 새 값) · foreign(관리하는 값이
#       아니다 — 사람이 적은 다른 주소, 그대로 둔다) ·
#       absent(파일·키가 없다) · error(못 바꿨다 — 지금 값 칸에 사유). 리포가 없는 사본은 줄을 내지 않는다(이 박스 대상이
#       아니다). 리포는 apply-envs·update-all 의 find_repo 와 같은 순서로 찾는다(<포털 상위>/ → ~/Projects/ → ~/claude/). 줄은 파일마다
#       처리하는 대로 낸다 — 뒤 파일에서 죽어도 앞 파일의 결과는 남는다(부르는 쪽은 종료코드를 본다). 값은 바이트 그대로 다룬다(UTF-8 이
#       아닌 값도 어느 LANG 에서나 죽지 않는다).
#   hwax_llm_pool_at <포털 루트> <주소>      지금 그 주소를 가리키는 사본 수(끝 `/` 무시)를 찍고 0. **셀 수 없으면 2** 와 사유 한 줄 — 사본 lib 이
#       실패했거나(here-doc 임시 파일을 못 만든다 · 파이썬이 죽었다) 읽지 못한 사본이 있다. 부르는 쪽은 2 를 '모른다 — 사본이 그 주소를 가리킬
#       수 있다' 로 읽는다(라우터를 내리지 않는다 · 기록을 덮지 않는다 · '직접 주소다' 라고 말하지 않는다 — ✗ 와 사유. 반대 검토 2라운드 M-D:
#       0 으로 읽어 사본 둘이 아직 가리키는 라우터를 내렸다).
#   hwax_llm_pool_loopback_dead <포털 루트> <뺄 주소…>   지금 값이 루프백 /v1 주소(127.x.x.x · localhost)인데 그 포트에 아무것도 듣지 않는
#       사본 — 줄마다 "<리포 경로>\t<.env 상대경로>\t<키>\t<값>". 뺄 주소(끝 `/` 무시)와 같은 값은 보지 않는다. 0 = 다 봤다(없으면 빈
#       출력) · 2 = 셀 수 없다(사유 한 줄). **고치지 않는다** — 라우터 기록이 없으면 그 주소가 옛 라우터인지 박스의 로컬 vLLM 인지 모른다
#       (풀 꺼짐 + 기록 없음일 때 update-all 1i 가 ⚠ 로 알린다 — LP-D14).
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
  # 첫 sed 도 LC_ALL=C — UTF-8 로케일의 [[:space:]] 는 U+3000·U+2003·U+2028 도 먹어 `　LLM_UPSTREAMS=…` 가 bash 에만 활성 줄이 된다
  # (라우터·services.py 는 ASCII 여섯만 공백이다 — 검토 2라운드 LOW 2). 대조 표: backend/tests/test_llm_pool_upstreams_rules.py
  LC_ALL=C sed -n -E "s/^[[:space:]]*(export[[:space:]]+)?$2=//p" "$1" 2>/dev/null | tail -1 \
    | LC_ALL=C sed -E 's/[[:space:]]+#.*$//; s/^[[:space:]]+//; s/[[:space:]]+$//' | LC_ALL=C tr -d '"'"'"'\r'
}

_hwax_llm_raw() {  # $1=파일 $2=키 — 같은 줄의 원문(주석·양끝 공백·CR 만 벗긴다 — 따옴표는 남긴다). 고르는 줄은 hwax_llm_envv 와 같다
  LC_ALL=C sed -n -E "s/^[[:space:]]*(export[[:space:]]+)?$2=//p" "$1" 2>/dev/null | tail -1 \
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

_hwax_llm_ups_label() {  # $1=칸 → 사유에 적을 '스킴://호스트'(못 알아보면 ?). 칸 원문은 찍지 않는다 — 질의·계정에 키가 들 수 있다.
  local u="$1" s="?" h="?" rest
  case "$u" in
    *://*)
      s="${u%%://*}"; rest="${u#*://}"
      [[ "$s" =~ ^[A-Za-z][A-Za-z0-9+.-]{0,15}$ ]] || s="?"
      rest="${rest%%[/?#]*}"; rest="${rest##*@}"
      [[ "$rest" =~ :[0-9]*$ ]] && rest="${rest%:*}"
      [[ "$rest" =~ ^[A-Za-z0-9.-]{1,253}$ ]] && h="$rest" ;;
  esac
  printf '%s://%s' "$s" "$h"
}

hwax_llm_pool_upstreams() {  # $1=infra.env [$2=라우터 포트 — 주지 않으면 infra/.env 의 LLM_ROUTER_PORT(기본 9130)]
  # LLM_UPSTREAMS 규칙의 **정본**이다 — 라우터(infra/llm-router/llm_router.py parse_upstreams)가 같은 표로 이 함수와 대조된다
  # (backend/tests/test_llm_pool_upstreams_rules.py — 이 함수가 오라클이다. 규칙을 바꾸면 두 곳을 함께 바꾸고 표에 줄을 더한다).
  #   모양  값(주석·양끝 공백을 벗긴 원문)이 공백·따옴표 없이 쓰였거나, 큰따옴표 한 쌍 또는 작은따옴표 한 쌍으로 통째 감쌌고 안에 따옴표가
  #         없다. 그 밖(따옴표 밖 공백 · 짝 없는 따옴표 · 따옴표 여럿 · 안의 따옴표)은 줄이 틀렸다 — infra/.env 는 포털 start.sh(_common.sh)가
  #         `set -a; . infra/.env` 로 소싱한다. `A="x", "y"` 같은 줄은 bash 에서 뒤가 명령이 되어 set -e 인 기동이 그 자리에서 죽는다.
  #   나눔  쉼표로(따옴표 안이면 공백으로도) 나누고 빈 칸은 버린다. 칸마다 끝 `/` 를 뗀다.
  #   칸    스킴은 소문자 http·https · 계정·질의·조각이 없다 · 호스트는 점 넷의 IPv4(칸마다 0~255, 앞 0 없음 — 0 하나는 된다) 또는 라벨
  #         이름(영숫자·하이픈 — 하이픈으로 시작·끝나지 않고, 3·4번째 글자가 `--` 가 아니다)이고, 숫자·점뿐인 이름은 IPv4 여야 한다(203.0.113.256 ·
  #         0203.0.113.1 · 2130706433 은 틀렸다) · IPv6 은 받지 않는다 · 포트는 없거나 숫자 1~5자로 1~65535 · 경로는 정확히 `/v1`.
  #         `--` 규칙은 IDN(`xn--…`)을 막는다 — httpx 는 `xn--` 로 시작하는 호스트를 idna 로 풀다 ValueError 를 낸다(InvalidURL 이 아니다).
  #   고리  루프백·미지정 호스트(127.0.0.0/8 · 0.0.0.0 · localhost)에 라우터 포트(적지 않았으면 스킴 기본 포트)면 라우터 자신이다.
  #   겹침  스킴 · 호스트(대소문자 무시) · 포트(적지 않았으면 스킴 기본 포트)가 같으면 같은 서버다.
  #   틀린 칸이 하나라도 있으면 줄 전체가 틀렸다(rc 2, 사유 한 줄 — 칸은 스킴과 호스트만 적는다).
  local v raw rport u lab scheme host port eport key out="" seen=" " n=0 o quad loop
  local -a items
  raw="$(_hwax_llm_raw "$1" LLM_UPSTREAMS)"
  v="$(hwax_llm_envv "$1" LLM_UPSTREAMS)"
  if [ "$#" -ge 2 ]; then
    rport=""; [[ "$2" =~ ^[0-9]{1,5}$ ]] && rport="$((10#$2))"
  else
    rport="$(_hwax_llm_port "$1")" || rport=""
  fi
  local LC_ALL=C     # 글자 부류·범위를 바이트(ASCII)로 — 로케일마다 공백(U+3000 등)·[A-Za-z] 가 달라지면 라우터와 갈린다
  local re_dq="^\"[^\"']*\"\$" re_sq="^'[^\"']*'\$"
  local re_item='^(https?)://([A-Za-z0-9.-]+)(:([0-9]{1,5}))?/v1$'
  local re_quad='^(0|[1-9][0-9]{0,2})\.(0|[1-9][0-9]{0,2})\.(0|[1-9][0-9]{0,2})\.(0|[1-9][0-9]{0,2})$'
  local re_name='^[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?(\.[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?)*$'
  local re_dd='(^|\.)[A-Za-z0-9-]{2}--'
  local tail_msg="vLLM 의 /v1 주소(http(s)://<호스트>[:<포트>]/v1 — 계정·질의·IPv6 은 받지 않는다)여야 한다"
  case "$raw" in
    *[\"\']*)
      if ! [[ "$raw" =~ $re_dq || "$raw" =~ $re_sq ]]; then
        printf '%s\n' "LLM_UPSTREAMS 의 공백·따옴표 모양이 틀렸다(따옴표 밖의 공백 · 짝이 없거나 여럿인 따옴표 · 따옴표 안의 따옴표) — infra/.env 는 포털 start.sh 가 bash 로 소싱해 그 줄에서 기동이 죽는다. 쉼표로만(공백 없이) 나누거나 값 전체를 큰따옴표 한 쌍으로 감싼다"
        return 2
      fi ;;
    *[[:space:]]*)
      printf '%s\n' "LLM_UPSTREAMS 의 공백이 따옴표 밖에 있다 — infra/.env 는 포털 start.sh 가 bash 로 소싱해 공백 뒤가 명령이 되고 기동이 죽는다. 쉼표로만(공백 없이) 나누거나 값 전체를 큰따옴표 한 쌍으로 감싼다"
      return 2 ;;
  esac
  [ -n "$v" ] || return 1
  IFS=, read -ra items <<<"${v//[[:space:]]/,}"
  for u in ${items[@]+"${items[@]}"}; do
    [ -n "$u" ] || continue
    while [ "${u%/}" != "$u" ]; do u="${u%/}"; done
    lab="$(_hwax_llm_ups_label "$u")"
    # 칸 하나가 2,048자를 넘으면 받지 않는다 — 라우터(httpx)는 64KiB 넘는 주소를 못 만들어, 넘는 칸을 lib 만 받으면 둘이 갈린다(2라운드 대조기).
    if [ "${#u}" -gt 2048 ]; then
      printf '%s
' "LLM_UPSTREAMS 의 칸 '$lab' 이 2,048자를 넘는다 — $tail_msg"
      return 2
    fi
    if ! [[ "$u" =~ $re_item ]]; then
      case "$u" in
        *@*)        printf '%s\n' "LLM_UPSTREAMS 의 칸 '$lab' 에 계정(user@)이 있다 — $tail_msg" ;;
        *[?#]*)     printf '%s\n' "LLM_UPSTREAMS 의 칸 '$lab' 에 질의·조각(? #)이 있다 — $tail_msg" ;;
        *\[*)       printf '%s\n' "LLM_UPSTREAMS 의 칸 '$lab' 은 IPv6 이다 — $tail_msg" ;;
        http://*|https://*) printf '%s\n' "LLM_UPSTREAMS 의 칸 '$lab' 은 쓸 수 있는 주소가 아니다(호스트 글자 · 포트 · 경로가 정확히 /v1 인지) — $tail_msg" ;;
        *)          printf '%s\n' "LLM_UPSTREAMS 의 칸 '$lab' 의 스킴이 소문자 http·https 가 아니다 — $tail_msg" ;;
      esac
      return 2
    fi
    scheme="${BASH_REMATCH[1]}"; host="${BASH_REMATCH[2]}"; port="${BASH_REMATCH[4]}"
    loop=0
    if [[ "$host" =~ ^[0-9.]+$ ]]; then
      quad=0
      if [[ "$host" =~ $re_quad ]]; then
        quad=1
        for o in "${BASH_REMATCH[@]:1:4}"; do [ "$o" -le 255 ] || quad=0; done
      fi
      if [ "$quad" != 1 ]; then
        printf '%s\n' "LLM_UPSTREAMS 의 칸 '$lab' 은 IPv4 가 아니다(점 넷 · 칸마다 0~255 · 앞에 0 을 붙이지 않는다) — $tail_msg"; return 2
      fi
      { [ "${host%%.*}" = 127 ] || [ "$host" = 0.0.0.0 ]; } && loop=1
    elif ! [[ "$host" =~ $re_name ]] || [[ "$host" =~ $re_dd ]]; then
      printf '%s\n' "LLM_UPSTREAMS 의 칸 '$lab' 의 호스트 이름이 틀렸다(영숫자·하이픈 라벨 — 하이픈으로 시작·끝나지 않고 3·4번째가 -- 가 아니다) — $tail_msg"; return 2
    else
      host="${host,,}"
      [ "$host" = localhost ] && loop=1
    fi
    if [ -n "$port" ] && { [ "$((10#$port))" -lt 1 ] || [ "$((10#$port))" -gt 65535 ]; }; then
      printf '%s\n' "LLM_UPSTREAMS 의 칸 '$lab' 의 포트가 1~65535 밖이다"; return 2
    fi
    if [ -n "$port" ]; then eport="$((10#$port))"; elif [ "$scheme" = https ]; then eport=443; else eport=80; fi
    if [ "$loop" = 1 ] && [ -n "$rport" ] && [ "$eport" = "$rport" ]; then
      printf '%s\n' "LLM_UPSTREAMS 의 칸 '$lab' 이 라우터 자신을 가리킨다(포트 $rport) — 서버(vLLM)의 /v1 주소를 적는다(라우터 주소는 update-all 이 사본에 적는다)"; return 2
    fi
    key="$scheme://$host:$eport"
    case "$seen" in
      *" $key "*) printf '%s\n' "LLM_UPSTREAMS 에 같은 서버가 두 번 있다: '$lab' — 서버마다 한 번씩 적는다(호스트의 대소문자 · 적지 않은 기본 포트는 같은 것이다)"; return 2 ;;
    esac
    seen="$seen$key "; out="$out$u"$'\n'; n=$((n + 1))
  done
  if [ "$n" = 0 ]; then printf '%s\n' "LLM_UPSTREAMS 에 주소가 하나도 없다(쉼표·공백뿐이다)"; return 2; fi
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
  local direct rurl h rc=0 st up tot inf m
  if [ "$#" -ge 2 ]; then direct="$2"; else direct="$(hwax_llm_envv "$1" LLM_BASE_URL)"; fi
  if hwax_llm_pool_upstreams "$1" >/dev/null && rurl="$(hwax_llm_router_url "$1")"; then
    h="$(hwax_llm_router_health "$(hwax_llm_router_health_url "$1")")" || rc=$?
    read -r st up tot inf m <<<"$h"
    if [ "$rc" = 0 ] && [[ "${up:-}" =~ ^[0-9]+$ ]] && [ "$up" -ge 1 ] && [ "${m:-}" = true ]; then
      printf '%s\n' "$rurl"; return 0
    fi
    printf '%s\n' "   · LLM 풀이 켜져 있는데 라우터($rurl)가 올라온 서버와 같은 모델을 답하지 않는다 — 직접 주소를 쓴다(라우터가 그렇게 답하면 update-all 1i 가 사본을 라우터로 바꾼다)" >&2
  fi
  [ -n "$direct" ] || return 1
  printf '%s\n' "$direct"
}

hwax_llm_router_recorded() {  # $1=포털 루트
  local v
  v="$(head -n 1 "$1/infra/.state/llm-pool.router" 2>/dev/null)" || v=""
  [[ "$v" =~ ^http://127\.0\.0\.1:[0-9]{1,5}/v1$ ]] || return 1
  printf '%s\n' "$v"
}

hwax_llm_router_record() {  # $1=포털 루트 $2=라우터 주소
  local f="$1/infra/.state/llm-pool.router" tmp=""
  if mkdir -p "${f%/*}" 2>/dev/null && tmp="$(mktemp "$f.XXXXXX" 2>/dev/null)" && printf '%s\n' "$2" > "$tmp" && mv -f "$tmp" "$f"; then
    return 0
  fi
  [ -n "$tmp" ] && rm -f "$tmp"
  return 1
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
import os, re, stat, sys, tempfile, time
from pathlib import Path

# 값은 **바이트로** 다룬다 — 사본에 UTF-8 이 아닌 값이 하나라도 있으면 str 로 풀어 찍다가 ko_KR.UTF-8 에서 UnicodeEncodeError 로
# 죽었다(그때는 이미 파일을 다 쓴 뒤라 바꾼 줄이 하나도 안 나왔다 — 반대 검토 L4). 환경·인자도 바이트로 받고, 출력도 바이트로 낸다.
root = Path(os.environ["HWAX_LLM_ROOT"]).resolve()
mode, new = os.environ["HWAX_LLM_MODE"], os.environb[b"HWAX_LLM_NEW"]
norm = lambda s: s.rstrip(b"/")
managed = {norm(os.fsencode(m)) for m in sys.argv[1:] if m.strip()}
home = Path(os.environ.get("HOME") or "/nonexistent")
bases = (root.parent, home / "Projects", home / "claude")      # find_repo 와 같은 순서
bkroot = root / "infra/.state/llm-pool-backups"               # 포털의 gitignore 된 상태 디렉터리 — 서비스 리포 안에 두지 않는다(H1)
out = sys.stdout.buffer


def repo_dir(name):
    for b in bases:
        if (b / name).is_dir():
            return b / name
    return None


def enc(x) -> bytes:
    if isinstance(x, bytes):
        return x
    if isinstance(x, Path):
        return os.fsencode(x)
    return str(x).encode("utf-8", "surrogateescape")          # 사유 글은 UTF-8 로(스크립트의 다른 글과 같게) — LANG 과 무관하다


def emit(rows):
    """파일마다 처리하는 대로 낸다 — 뒤 파일에서 죽어도 앞 파일의 결과(바꿨다 · 백업 경로)는 부르는 쪽에 남는다."""
    for r in rows:
        out.write(b"\t".join(enc(x) for x in r) + b"\n")
    out.flush()


# update-all _envfile_value 와 같은 규칙 — 줄 머리([[:space:]]*, export 허용), 공백 뒤 # 주석, 양끝 공백, 따옴표·CR
WS = rb" \t\v\f\r"
def value_of(body: bytes) -> bytes:
    v = re.sub(rb"[" + WS + rb"]+#.*$", b"", body)
    return v.strip(WS).replace(b'"', b"").replace(b"'", b"").replace(b"\r", b"")


def split_lines(data: bytes) -> list:
    """`\\n` 으로만 나눈다 — bytes.splitlines 는 홀로 선 `\\r` 에서도 나눠, 읽는 쪽(sed — 줄은 `\\n` 뿐)이 보지 않는 줄을 고쳤다(L5)."""
    parts = data.split(b"\n")
    return [p + b"\n" for p in parts[:-1]] + ([parts[-1]] if parts[-1] else [])


def backup(repo: str, rel: str, data: bytes) -> Path:
    """<bkroot>/<리포>/<상대경로>.<UTC>[-n] — 디렉터리 700 · 파일 600(만드는 순간부터). 같은 초에 다시 돌아도 앞 백업을 덮지 않는다."""
    stem = bkroot / repo / rel
    old = os.umask(0o077)                                      # 새로 만드는 디렉터리는 전부 700(중간 디렉터리까지)
    try:
        stem.parent.mkdir(parents=True, exist_ok=True)
    finally:
        os.umask(old)
    os.chmod(bkroot, 0o700)                                    # 먼저 있던 백업 뿌리도 700 — 그 아래 전부가 이 하나로 닫힌다
    for k in range(100):
        cand = stem.with_name(f"{stem.name}.{ts}" + (f"-{k}" if k else ""))
        try:
            fd = os.open(cand, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            continue
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
        except OSError:
            cand.unlink(missing_ok=True)
            raise
        return cand
    raise OSError(0, "이름이 다 찼다")


def in_place_why(real: Path) -> str:
    """이름 바꾸기가 무언가를 잃는 파일이면 그 까닭(제자리에 쓴다 — LP-D14), 아니면 빈 글. 새 파일은 모드만 받는다 — ACL 의 이름 붙은
    사용자는 사라지고 그룹 칸은 마스크로 넓어진다(비밀 파일의 읽기 권한이 넓어진다). 하드 링크의 다른 이름은 옛 inode(옛 주소)에 남는다."""
    st = real.stat()
    if st.st_nlink > 1:
        return f"하드 링크가 {st.st_nlink}개다 — 다른 이름도 함께 바뀐다"
    try:
        os.getxattr(real, "system.posix_acl_access")              # 기본 칸(모드)뿐인 ACL 은 커널이 적지 않는다 — 있으면 확장 ACL 이다
        return "ACL 이 있다 — 그대로 둔다"
    except OSError:                                             # ENODATA(없다) · ENOTSUP(이 파일 시스템은 ACL 이 없다)
        pass
    if not os.access(real.parent, os.W_OK | os.X_OK):
        return "디렉터리에 쓸 수 없다 — 이름을 바꿀 수 없다"
    return ""


def put_at_start(fd: int, body: bytes) -> None:
    os.lseek(fd, 0, os.SEEK_SET)
    view = memoryview(body)
    while view:
        view = view[os.write(fd, view):]
    os.ftruncate(fd, len(body))
    os.fsync(fd)


def write_in_place(real: Path, content: bytes, old: bytes) -> None:
    """제자리에 쓴다 — 같은 inode 라 ACL · 하드 링크 · 소유자 · 모드가 그대로다. 쓰다 실패하면(디스크가 찼다 — 여기서는 EFBIG·ENOSPC) 원래
    내용을 다시 쓴다 — 원래 크기 안이라 자리는 이미 있다. 부르는 쪽이 결과를 읽어 본다(그래도 다르면 백업으로 되돌리라고 말한다)."""
    fd = os.open(real, os.O_WRONLY)
    try:
        try:
            put_at_start(fd, content)
        except BaseException:
            try:
                put_at_start(fd, old)                           # 반쯤 쓴 채로 두지 않는다
            except OSError:
                pass
            raise
    finally:
        os.close(fd)


def replace(path: Path, content: bytes) -> None:
    """원자적으로 바꾼다(L3) — 가리키는 파일 옆의 임시 파일에 쓰고 fsync 한 뒤 이름을 바꾼다. 제자리 쓰기는 디스크가 차면 반쯤 잘린 .env 를
    남겼다. 심링크면 링크는 그대로 두고 가리키는 파일을 바꾼다. 권한·소유자는 원본 그대로 — 소유자를 지킬 수 없으면(남의 파일) 바꾸지 않는다."""
    real = Path(os.path.realpath(path))
    st = real.stat()
    fd, tmp = tempfile.mkstemp(dir=real.parent, prefix=f"{real.name}.tmp-")   # 같은 디렉터리 — 이름 바꾸기가 원자적인 자리
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.chown(tmp, st.st_uid, st.st_gid)                    # 남의 소유면 PermissionError — 아래에서 '그대로다' 로 끝난다
        os.chmod(tmp, stat.S_IMODE(st.st_mode))
        os.replace(tmp, real)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    try:                                                       # 이름 바꾸기를 디스크에 — 실패해도 파일은 이미 새 내용이다
        dfd = os.open(real.parent, os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    except OSError:
        pass


groups = {}                                                   # 파일 → [(서비스, 리포, 리포 이름, 상대경로, 키)] — 백업은 파일마다 한 번
for ln in os.environ.get("HWAX_LLM_COPIES", "").splitlines():
    parts = ln.split("\t")
    if len(parts) != 4:
        continue
    svc, repo, rel, key = parts
    d = repo_dir(repo)
    if d is None:
        continue                                              # 이 박스에 그 리포가 없다 — 대상 아님
    groups.setdefault(d / rel, []).append((svc, d, repo, rel, key))

ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
for path, entries in groups.items():
    if not path.is_file():
        emit([["absent", s, d, r, k, b"", b""] for s, d, _, r, k in entries])
        continue
    try:
        data = path.read_bytes()
    except OSError as e:
        emit([["error", s, d, r, k, f"읽지 못했다({e.strerror})", b""] for s, d, _, r, k in entries])
        continue
    lines = split_lines(data)
    edits, mine = {}, []
    for svc, d, repo, rel, key in entries:
        pat = re.compile(rb"^[" + WS + rb"]*(?:export[" + WS + rb"]+)?" + re.escape(key.encode()) + rb"=")
        idx = [i for i, l in enumerate(lines) if pat.match(l)]
        if not idx:
            mine.append(["absent", svc, d, rel, key, b"", b""])
            continue
        i = idx[-1]                                            # 읽는 쪽(tail -1)과 같은 줄을 고친다
        line = lines[i]
        head = pat.match(line).end()
        body = line[head:]
        eol = b""
        for e in (b"\r\n", b"\n", b"\r"):                      # 끝의 `\r` 만 남은 줄은 파일 끝의 마지막 줄뿐이다(줄은 `\n` 으로만 나눴다)
            if body.endswith(e):
                eol, body = e, body[: -len(e)]
                break
        cur = value_of(body)
        shown = cur.replace(b"\t", b" ")                       # 출력 칸은 탭으로 갈린다 — 값 속 탭이 칸을 밀지 않게(보여 주기만)
        if cur and norm(cur) == norm(new):
            mine.append(["same", svc, d, rel, key, shown, b""])
            continue
        if not cur or norm(cur) not in managed:
            mine.append(["foreign", svc, d, rel, key, shown, b""])  # 사람이 일부러 적은 다른 주소(또는 빈 값) — 건드리지 않는다
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
        edits[i] = line[:head] + lead + q + new + q + trail + comment + eol
        mine.append(["changed" if mode == "write" else "would", svc, d, rel, key, shown, b""])
    if edits and mode == "write":
        repo0, rel0 = entries[0][2], entries[0][3]                # 한 파일의 키들은 같은 리포 · 같은 경로다
        real = Path(os.path.realpath(path))
        why, bak, how = None, None, ""
        if not os.access(real, os.W_OK):                       # 이름 바꾸기는 디렉터리 권한만 본다 — 읽기 전용 파일도 갈아 끼울 수 있어 먼저 본다
            why = "쓸 수 없는 파일이다(권한) — 백업도 만들지 않았다. 파일은 그대로다"
        else:
            try:
                bak = backup(repo0, rel0, data)
            except OSError as e:
                why = f"백업을 만들지 못했다({e.strerror or e}) — 파일은 그대로다"
        if bak is not None:
            content = b"".join(edits.get(i, l) for i, l in enumerate(lines))
            try:
                how = in_place_why(real)                       # 이름 바꾸기가 ACL · 하드 링크를 잃거나 못 하면 백업 뒤 제자리에(LP-D14)
                if how:
                    write_in_place(real, content, data)
                else:
                    replace(path, content)
            except OSError as e:
                try:                                           # 이름 바꾸기는 실패하면 손대지 않은 것이다 — 제자리 쓰기는 읽어 본다
                    intact = not how or real.read_bytes() == data
                except OSError:
                    intact = False
                if intact:
                    why = f"쓰지 못했다({e.strerror or e}) — 파일은 그대로다"
                    try:
                        bak.unlink()                           # 쓰지 못한 바꾸기의 백업은 남기지 않는다(비밀 사본이 하나 더 남을 뿐이다)
                        why += "(만든 백업은 지웠다)"
                    except OSError:
                        why += f"(백업 {bak} 이 남았다)"
                else:
                    why = (f"쓰지 못했다({e.strerror or e}) — 제자리에 쓰다 멈춰 파일이 반쯤 바뀌었을 수 있다. "
                           f"백업으로 되돌린다: cp '{bak}' '{path}'")
                bak = None
        if bak is None:
            mine = [["error", *r[1:5], why, b""] if r[0] == "changed" else r for r in mine]
        else:
            note = [f"제자리에 썼다 — {how}"] if how else []   # 여덟째 칸 — 이름 바꾸기 대신 제자리에 쓴 사실과 까닭(부르는 쪽이 ✓ 줄에 붙인다)
            mine = [[*r[:6], bak, *note] if r[0] == "changed" else r for r in mine]
    emit(mine)
PY
}

hwax_llm_pool_at() {  # $1=포털 루트 $2=주소 — 0 = 수를 찍었다 · 2 = 셀 수 없다(사유 한 줄 — 부르는 쪽은 '가리킬 수 있다' 로 읽는다)
  # 종전엔 lib 의 실패를 0 으로 읽었다(`… | awk 'END { print n + 0 }'` — /tmp 가 차 here-doc 을 못 만들면 '가리키는 사본 0곳').
  local out rc=0 cnt n e
  out="$(hwax_llm_pool_rewrite "$1" dry "$2" "$2")" || rc=$?
  if [ "$rc" != 0 ]; then
    printf '%s\n' "사본을 세지 못했다(사본 lib rc $rc — 위 오류 줄)"; return 2
  fi
  # 읽지 못한 사본(error 줄)도 '모른다' 다 — 그 사본이 이 주소를 가리킬 수 있다. 첫 사본의 자리와 사유를 함께 낸다.
  cnt="$(printf '%s\n' "$out" | awk -F'\t' '$1 == "same" { n++ }
           $1 == "error" { if (!e) { k = split($3, p, "/"); w = p[k] "/" $4 " " $5 " — " $6 } e++ }
           END { printf "%d\t%d\t%s\n", n, e, w }')" || cnt=""
  n="${cnt%%$'\t'*}"; e="${cnt#*$'\t'}"; e="${e%%$'\t'*}"
  if ! [[ "$n" =~ ^[0-9]+$ && "$e" =~ ^[0-9]+$ ]]; then
    printf '%s\n' "사본을 세지 못했다(수를 읽지 못했다)"; return 2
  fi
  if [ "$e" != 0 ]; then
    printf '%s\n' "사본 ${e}곳을 읽지 못했다(${cnt#*$'\t'*$'\t'})"; return 2
  fi
  printf '%s\n' "$n"
}

hwax_llm_pool_loopback_dead() {  # $1=포털 루트 $2…=뺄 주소 — 머리 주석
  local root="$1" out rc=0 st svc rp rel key cur x skip scheme host port code dead=""
  shift
  out="$(hwax_llm_pool_rewrite "$root" dry "-")" || rc=$?      # 관리하는 값 없이 — 값이 있는 사본은 전부 foreign 줄로 지금 값을 낸다
  if [ "$rc" != 0 ]; then
    printf '%s\n' "사본을 읽지 못했다(사본 lib rc $rc — 위 오류 줄)"; return 2
  fi
  while IFS=$'\t' read -r st svc rp rel key cur _; do
    case "$st" in
      error) printf '%s\n' "${rp##*/}/$rel $key 를 읽지 못했다 — $cur"; return 2 ;;
      foreign) ;;
      *) continue ;;
    esac
    [[ "$cur" =~ ^(https?)://(127\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}|localhost)(:([0-9]{1,5}))?/v1/?$ ]] || continue
    scheme="${BASH_REMATCH[1]}"; host="${BASH_REMATCH[2]}"; port="${BASH_REMATCH[4]}"
    skip=0
    for x in "$@"; do [ -n "$x" ] && [ "${x%/}" = "${cur%/}" ] && skip=1; done
    [ "$skip" = 0 ] || continue
    if [ -z "$port" ]; then if [ "$scheme" = https ]; then port=443; else port=80; fi; fi
    # 듣는 것이 없다 = 연결 거절(curl 7). 답이 무엇이든(404 · TLS 오류 · 시간 초과) 무언가 듣고 있으면 이 줄에 넣지 않는다.
    code=0; curl -s -o /dev/null --noproxy '*' --connect-timeout 2 -m 3 "http://$host:$port/" 2>/dev/null || code=$?
    [ "$code" = 7 ] && dead="$dead$rp"$'\t'"$rel"$'\t'"$key"$'\t'"$cur"$'\n'
  done <<<"$out"
  printf '%s' "$dead"
}
