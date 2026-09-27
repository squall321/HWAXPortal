#!/usr/bin/env bash
# 바뀌지 않은 서비스는 받지도 재기동하지도 않는다 — update-all §2(deploy-all-from-drive)·§4(update-sites) 가 쓴다.
#   . "$ROOT/infra/scripts/lib/change-detect.sh"      (HWAX_RESTART_STATE_DIR 을 먼저 export — 기본은 <포털>/infra/.state/restart-fp)
#   hwax_fp <경로…>                        지문(sha256 앞 12자). 디렉터리는 파일 이름·크기·mtime, 32MB 넘는 파일도 크기·mtime(SIF — 내용 해시는
#                                          초 단위), 작은 파일은 내용 해시(.env 같은 설정). 없는 경로는 "missing:<경로>" 로 들어간다.
#   hwax_install_if_changed <src> <dst>    cmp 가 다를 때만 cp -p. 0=설치했다 · 1=같아서 손대지 않았다 · 2=cp 실패(stderr 에 ✗). 살아 있는 인스턴스
#                                          밑의 SIF 를 같은 내용으로 덮어쓰면 squashfs 가 깨지고, cp 는 mtime 을 리셋해 지문이 매번 달라진다.
#   hwax_alive <url>                       0 이면 답한다(200 401 302 405 406). curl 은 rc 가 아니라 코드로 판정.
#   hwax_last_fp <이름> / hwax_mark_started <이름> <지문>   마지막으로 **띄운** 시점의 지문(상태 파일). 기동이 성공한 뒤에만 적는다.
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
hwax_mark_started() { mkdir -p "${HWAX_RESTART_STATE_DIR:?}" && printf '%s\n' "$2" > "$(hwax_state_file "$1")"; }

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
