#!/usr/bin/env bash
# 바뀌지 않은 서비스는 받지도 재기동하지도 않는다 — update-all §2(deploy-all-from-drive)·§4(update-sites) 가 쓴다.
#   . "$ROOT/infra/scripts/lib/change-detect.sh"      (HWAX_RESTART_STATE_DIR 을 먼저 export — 기본은 <포털>/infra/.state/restart-fp)
#   hwax_fp <경로…>                        지문(sha256 앞 12자). 디렉터리는 파일 이름·크기·mtime, 32MB 넘는 파일도 크기·mtime(SIF — 내용 해시는
#                                          초 단위), 작은 파일은 내용 해시(.env 같은 설정). 없는 경로는 "missing:<경로>" 로 들어간다.
#   hwax_install_if_changed <src> <dst>    cmp 가 다를 때만 cp -p. 0=설치했다 · 1=같아서 손대지 않았다 · 2=cp 실패(stderr 에 ✗). 살아 있는 인스턴스
#                                          밑의 SIF 를 같은 내용으로 덮어쓰면 squashfs 가 깨지고, cp 는 mtime 을 리셋해 지문이 매번 달라진다.
#   hwax_alive <url>                       0 이면 답한다(200 401 302 405 406). curl 은 rc 가 아니라 코드로 판정.
#   hwax_last_fp <이름> / hwax_mark_started <이름> <지문>   마지막으로 **띄운** 시점의 지문(상태 파일). 기동이 성공한 뒤에만 적는다.
#   hwax_restart_cycle …                 아래 함수 머리 참조 — 재기동·기록의 정본 경로.
#   hwax_restart_needed <이름> <지금 지문> <url>…   0=재기동해야 한다 · 1=생략. 기준은 마지막 기동 지문이다 — '블록 전/후' 를 기준으로 삼으면
#                                          블록 밖에서 일어난 변경(update-all §1 의 git reset·§1c/1d/1e 의 .env·routes 기록·운영자 편집)을 하나도
#                                          못 봐 백엔드 커밋과 설정 변경이 재기동을 영원히 못 일으킨다(1라운드 검토 실측). 기록이 없으면 재기동.
#                                          url 이 여럿이면 전부 답해야 생략(인스턴스 여럿인 서비스). HWAX_RESTART_ALL=1 이면 항상 0.
# 문서: docs/update-all-skip-unchanged/ (PLAN·context-notes)
hwax_fp() {
  local p
  {
    for p in "$@"; do
      if [ -d "$p" ]; then
        printf 'dir:%s\n' "$p"
        find "$p" -type f ! -name '*.pyc' ! -path '*/__pycache__/*' -printf '%P\t%s\t%T@\n' 2>/dev/null | LC_ALL=C sort
      elif [ -f "$p" ]; then
        if [ "$(stat -c %s "$p" 2>/dev/null || echo 0)" -gt 33554432 ]; then
          printf 'big:%s\t%s\t%s\n' "$p" "$(stat -c %s "$p")" "$(stat -c %Y "$p")"
        else
          printf 'file:%s\t' "$p"; sha256sum "$p" 2>/dev/null | cut -c1-16; printf '\n'
        fi
      else
        printf 'missing:%s\n' "$p"
      fi
    done
  } | sha256sum | cut -c1-12
}

hwax_install_if_changed() {  # $1=src $2=dst
  if [ -f "$2" ] && cmp -s "$1" "$2"; then return 1; fi
  if cp -p "$1" "$2"; then return 0; fi
  echo "  ✗ $(basename "$2") 설치 실패 — $2 에 쓸 수 없다(권한·소유자·디스크). 옛 파일이 그대로다" >&2
  return 2
}

hwax_alive() {
  local code
  code="$(curl -sk -m 4 -o /dev/null -w '%{http_code}' "$1" 2>/dev/null)" || true
  case " 200 401 302 405 406 " in *" ${code:-000} "*) return 0 ;; esac
  return 1
}

hwax_state_file() { printf '%s/%s' "${HWAX_RESTART_STATE_DIR:?HWAX_RESTART_STATE_DIR 미설정}" "$1"; }
hwax_last_fp() { cat "$(hwax_state_file "$1")" 2>/dev/null || true; }
hwax_mark_started() {  # 못 적어도 실패로 만들지 않는다 — 재기동은 이미 됐고, 기록이 없으면 다음 실행이 한 번 더 재기동할 뿐이다(sudo 로 한 번 돌려 root 소유가 된 상태 등)
  if mkdir -p "${HWAX_RESTART_STATE_DIR:?}" 2>/dev/null && printf '%s\n' "$2" > "$(hwax_state_file "$1")" 2>/dev/null; then return 0; fi
  echo "  ⚠ $1: 기준 지문을 기록하지 못했다($(hwax_state_file "$1"), 소유자 $(stat -c %U "$(hwax_state_file "$1")" 2>/dev/null || stat -c %U "${HWAX_RESTART_STATE_DIR}" 2>/dev/null || echo ?)) — 다음 실행도 재기동한다" >&2
  return 0
}

# ── 재기동이 **실제로** 일어났는지는 프로세스로 확인한다 — start 스크립트는 떠 있는 인스턴스를 만나면 'already running' 으로 rc 0 을 낸다.
#   stop 이 실패했거나 NO_RESTART=1 이면 옛 프로세스가 그대로인데 rc 0 이라, 그 rc 만 믿고 새 지문을 적으면 영구 생략이 된다(2라운드 검토).
#   health url 의 포트를 듣는 프로세스(pid + /proc 시작시각)를 전/후로 비교해 **바뀌었을 때만** 기록한다. 자기 사용자의 프로세스만 보인다(ss -p).
hwax_port_of_url() { local u="${1#*://}"; u="${u%%/*}"; case "$u" in *:*) printf '%s' "${u##*:}" ;; *) printf 80 ;; esac; }
hwax_listener_ids() {  # $@=url… → "포트:pid:시작시각 …" (가장 작은 pid — nginx 워커 여럿의 순서에 흔들리지 않게). 못 보면 포트:?
  local u p pid st out=""
  for u in "$@"; do
    p="$(hwax_port_of_url "$u")"
    pid="$(ss -ltnpH "sport = :$p" 2>/dev/null | grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -n | head -1)"
    if [ -n "$pid" ]; then st="$(awk '{print $22}' "/proc/$pid/stat" 2>/dev/null)"; out="$out $p:$pid:${st:-?}"; else out="$out $p:?"; fi
  done
  printf '%s' "${out# }"
}
hwax_wait_down() {  # $@=url… 최대 20초(HWAX_WAIT_DOWN_MAX — 시험용) — 전부 답하지 않게 되면 0
  local i u alive
  for i in $(seq 1 "${HWAX_WAIT_DOWN_MAX:-20}"); do
    alive=0; for u in "$@"; do if hwax_alive "$u"; then alive=1; break; fi; done
    [ "$alive" = 0 ] && return 0
    sleep 1
  done
  return 1
}
hwax_wait_up() {  # $@=url… 최대 10초(HWAX_WAIT_UP_MAX) — 전부 답하면 0. start 가 포트 바인드 전에 돌아오는 스크립트(SF 프론트 up.sh 는
  local i u ok   # instance start 뒤 배너만 찍고 끝난다)에 주는 유예다 — 없으면 정상 기동을 '답하지 않는다' ✗ 로 오탐한다(3라운드).
  for i in $(seq 1 "${HWAX_WAIT_UP_MAX:-10}"); do
    ok=1; for u in "$@"; do hwax_alive "$u" || { ok=0; break; }; done
    [ "$ok" = 1 ] && return 0
    sleep 1
  done
  return 1
}
# hwax_restart_cycle <이름> <지문> <stop 함수> <start 함수> <url…>
#   생략 판정 → (RESTART!=1 이면) stop·내려갔는지 확인 → start → 뜰 때까지 짧게 기다림 → **url 마다** 리스너 프로세스를 전/후로 비교.
#   전부 바뀌었을 때만 기록(HWAX_RESTARTED=1). 하나라도 같으면 그 인스턴스는 옛 프로세스다 → ✗ rc 1·무기록(3라운드: 문자열 전체를 한 번에
#   비교해 둘 중 하나만 갈려도 기록됐다 — 정지에 실패한 인스턴스가 옛 코드로 영구 생략될 판이었다). 하나라도 식별 불가('?')면 답하는지 보고
#   답하면 ⚠ 무기록, 안 답하면 ✗ rc 1. 새 프로세스가 떴는데 health 가 아직 안 답하면 ⚠ 만 내고 기록한다(다음 실행의 생존 검사가 다시 띄운다 —
#   여기서 ✗ 로 막으면 늦게 뜨는 백엔드가 매 회 재기동된다).
#   stop 함수 자리에 `:` 를 주면 start 가 스스로 옛 프로세스를 갈아 끼우는 서비스다(AIDH boot.sh --force) — 정지·내려감 대기를 건너뛴다.
#   0 = 생략했거나 재기동했다(또는 NO_RESTART=1 로 start 만 했다 — 기록 없음) · 1 = start 실패, 같은 프로세스가 답한다, 아무것도 듣지 않는다.
hwax_restart_cycle() {
  local name="$1" cur="$2" stopf="$3" startf="$4" id0 id1 u i a b same="" unk="" dead=""; local -a _A0 _A1; shift 4
  HWAX_RESTARTED=0
  hwax_restart_needed "$name" "$cur" "$@" || return 0
  id0="$(hwax_listener_ids "$@")"
  if [ "${RESTART:-0}" != 1 ] && [ "$stopf" != ":" ]; then
    "$stopf" || true
    hwax_wait_down "$@" || echo "  ✗ $name: 정지 뒤에도 답한다 — 옛 프로세스가 내려가지 않았다(stop 실패). start 는 'already running' 이 될 것이다" >&2
  fi
  "$startf" || { echo "  ✗ $name: start 가 실패했다(rc≠0) — 기준 지문을 기록하지 않는다" >&2; return 1; }
  hwax_wait_up "$@" || true
  id1="$(hwax_listener_ids "$@")"
  # 토큰은 **배열로** 받는다 — `$id0` 를 인용 없이 펼치면 `<포트>:?` 의 `?` 가 글롭이라 cwd 에 같은 이름의 파일이 있으면
  # 토큰이 늘어나 url↔토큰 짝이 밀린다(4라운드, latent). read -ra 는 글롭도 재분할도 하지 않는다.
  read -ra _A0 <<<"$id0"; read -ra _A1 <<<"$id1"
  i=0
  for u in "$@"; do
    a="${_A0[i]:-}"; b="${_A1[i]:-}"; i=$((i+1))
    case "$b" in
      ""|*"?"*) if hwax_alive "$u"; then unk="$unk $u"; else dead="$dead $u"; fi ;;
      *) [ "$b" = "$a" ] && same="$same $u" ;;
    esac
  done
  if [ -n "$dead" ]; then echo "  ✗ $name: start 는 성공이라는데 답하지 않는다(리스너 없음):$dead — 기준 지문을 기록하지 않는다" >&2; return 1; fi
  if [ -n "$same" ]; then
    if [ "${RESTART:-0}" = 1 ]; then echo "  · $name: NO_RESTART=1 — start 만 했다(같은 프로세스:$same). 기준 지문을 기록하지 않는다(다음 정상 실행이 재기동한다)"; return 0; fi
    echo "  ✗ $name: 재기동이 되지 않았다 — 같은 프로세스가 답한다:$same (stop 실패·already running). 기준 지문을 기록하지 않는다" >&2; return 1
  fi
  if [ -n "$unk" ]; then echo "  ⚠ $name: 답은 하는데 프로세스를 식별하지 못한다:$unk (ss 없음 또는 다른 사용자 소유) → 기준 지문을 기록하지 않는다. 다음 실행도 재기동한다" >&2; return 0; fi
  for u in "$@"; do hwax_alive "$u" || echo "  ⚠ $name: 새 프로세스는 떴는데 $u 가 아직 답하지 않는다 — 기록은 하되 다음 실행이 살아 있는지 다시 본다" >&2; done
  HWAX_RESTARTED=1; hwax_mark_started "$name" "$cur"; return 0
}

hwax_restart_needed() {  # $1=이름 $2=지금 지문 $3…=health url
  local name="$1" cur="$2" last url; shift 2
  if [ "${HWAX_RESTART_ALL:-0}" = 1 ]; then echo "  · $name: HWAX_RESTART_ALL=1 → 재기동"; return 0; fi
  last="$(hwax_last_fp "$name")"
  if [ -z "$last" ]; then echo "  · $name: 마지막 기동 지문 기록이 없다(처음) → 재기동"; return 0; fi
  if [ "$last" != "$cur" ]; then echo "  · $name: 마지막 기동 뒤 변경 있음(지문 $last → $cur) → 재기동"; return 0; fi
  for url in "$@"; do
    if ! hwax_alive "$url"; then echo "  · $name: 변경 없음이지만 $url 이 답하지 않는다 → 기동"; return 0; fi
  done
  echo "  · $name: 마지막 기동 뒤 변경 없음(지문 $cur) · 살아 있음 → 재기동 생략 (전부 재기동: HWAX_RESTART_ALL=1)"
  [ -n "${HWAX_RESTART_SKIPPED_FILE:-}" ] && echo "$name" >> "$HWAX_RESTART_SKIPPED_FILE"
  return 1
}
