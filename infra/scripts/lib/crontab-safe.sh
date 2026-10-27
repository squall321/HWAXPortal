#!/usr/bin/env bash
# crontab 을 읽고 고쳐 쓰는 안전한 길 — 'no crontab for <user>' 만 빈 목록으로 보고, 그 밖의 읽기 실패에는 쓰지 않는다.
#
# 왜 — `crontab -l 2>/dev/null | grep -v … ; echo 새 줄) | crontab -` 꼴은 일시 실패(스풀 권한 · 잠금 · 계정 조회)도 빈 목록으로
# 읽어, 줄 하나를 고치려다 백업 · 감시 · 터널 줄을 통째로 지운다(docs/request-1027 HP-18). 「없음」 과 「못 읽음」 을 가른다.
#
#   . "$ROOT/infra/scripts/lib/crontab-safe.sh"
#   cur="$(hwax_crontab_get)" || exit 1        # rc 0 = 읽음(없으면 빈 값) · rc 1 = 못 읽음(stderr 에 ✗ 한 줄)
#   hwax_crontab_replace "<표지>" "<새 줄>"     # 표지가 든 줄을 빼고 새 줄을 붙인다 — 읽기에 실패하면 쓰지 않고 rc 1
#   hwax_crontab_replace "<표지>"               # 새 줄 없이 — 지우기
hwax_crontab_get() {
  local _err _out _rc=0
  _err="$(mktemp)" || return 1
  # 문구로 가른다 — cron 은 없을 때와 못 읽을 때 둘 다 rc 1 이다. 문구가 번역되지 않게 C 로캘.
  _out="$(LC_ALL=C crontab -l 2>"$_err")" || _rc=$?
  if [ "$_rc" -ne 0 ]; then
    if grep -q '^no crontab for ' "$_err"; then rm -f "$_err"; return 0; fi
    printf '✗ crontab -l 실패(rc %s) — %s\n' "$_rc" "$(head -c 300 "$_err" | tr '\n' ' ')" >&2
    rm -f "$_err"; return 1
  fi
  rm -f "$_err"
  [ -z "$_out" ] || printf '%s\n' "$_out"
}

hwax_crontab_replace() {
  local _cur
  [ -n "${1:-}" ] || { echo "✗ hwax_crontab_replace — 표지가 비었다(빈 표지는 모든 줄에 걸린다)" >&2; return 1; }
  _cur="$(hwax_crontab_get)" || return 1
  { [ -z "$_cur" ] || grep -vF -- "$1" <<<"$_cur"; [ -z "${2:-}" ] || printf '%s\n' "$2"; } | crontab -
}
