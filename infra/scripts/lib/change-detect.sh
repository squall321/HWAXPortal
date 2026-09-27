#!/usr/bin/env bash
# 바뀌지 않은 서비스는 받지도 재기동하지도 않는다 — update-all §2(deploy-all-from-drive)·§4(update-sites) 가 쓴다.
#   . "$ROOT/infra/scripts/lib/change-detect.sh"
#   hwax_fp <경로…>                        지문(sha256 앞 12자). 디렉터리는 파일 이름·크기·mtime 만(내용 해시 없음 — SIF 수백 MB),
#                                          파일은 내용 해시(.env 같은 작은 설정). 없는 경로는 "missing:<경로>" 로 들어간다.
#   hwax_install_if_changed <src> <dst>    cmp 가 다를 때만 cp -p — 살아 있는 인스턴스 밑의 SIF 를 같은 내용으로 덮어쓰면 squashfs 가 깨지고,
#                                          cp 는 mtime 을 리셋해 지문이 매번 달라진다. 0=설치했다 · 1=같아서 손대지 않았다.
#   hwax_alive <url> [허용코드…]           0 이면 살아 있음(기본 200 401 302 405 406 — 답하면 살아 있다). curl 은 rc 가 아니라 코드로 판정.
#   hwax_restart_needed <이름> <전> <후> <url>   0=재기동해야 한다 · 1=생략. 문구를 찍고 생략은 HWAX_RESTART_SKIPPED_FILE 에 적는다.
#                                          HWAX_RESTART_ALL=1 이면 항상 0.
# 문서: docs/update-all-skip-unchanged/ (PLAN·context-notes D-2~D-4)
hwax_fp() {
  local p
  {
    for p in "$@"; do
      if [ -d "$p" ]; then
        printf 'dir:%s\n' "$p"
        find "$p" -type f ! -name '*.pyc' ! -path '*/__pycache__/*' -printf '%P\t%s\t%T@\n' 2>/dev/null | LC_ALL=C sort
      elif [ -f "$p" ]; then
        # 32MB 넘는 파일(SIF)은 내용 해시가 초 단위라 이름·크기·mtime 으로 — 설치가 cp -p(원격 modtime 보존)·cmp 뒤에만 쓰기라 안정적이다
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
  cp -p "$1" "$2"
}

hwax_alive() {
  local url="$1" code; shift
  code="$(curl -sk -m 4 -o /dev/null -w '%{http_code}' "$url" 2>/dev/null)" || true
  code="${code:-000}"
  set -- "${@:-200 401 302 405 406}"
  case " $* " in *" $code "*) return 0 ;; esac
  return 1
}

hwax_restart_needed() {  # $1=이름 $2=지문 전 $3=지문 후 $4=health url
  local name="$1" before="$2" after="$3" url="$4"
  if [ "${HWAX_RESTART_ALL:-0}" = 1 ]; then
    echo "  · $name: HWAX_RESTART_ALL=1 → 재기동"; return 0
  fi
  if [ "$before" != "$after" ]; then
    echo "  · $name: 변경 있음(지문 $before → $after) → 재기동"; return 0
  fi
  if ! hwax_alive "$url"; then
    echo "  · $name: 변경 없음이지만 살아 있지 않다($url) → 기동"; return 0
  fi
  echo "  · $name: 변경 없음(git·아티팩트·설정 지문 $after) · 살아 있음 → 재기동 생략 (전부 재기동: HWAX_RESTART_ALL=1)"
  [ -n "${HWAX_RESTART_SKIPPED_FILE:-}" ] && echo "$name" >> "$HWAX_RESTART_SKIPPED_FILE"
  return 1
}
