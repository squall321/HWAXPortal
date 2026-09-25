#!/usr/bin/env bash
# "기능은 있는데 옵션·설정이 없어 이번 실행에서 셋업하지 않은 것" 의 장부 — update-all 이 쓴다.
#
# 왜 — 옵션(--with-<name>)·설정(routes.local.env·.env 값)이 없으면 그 단계는 조용히 지나갔고, 사용자는
# 그 기능이 리포에 있는 줄도 몰랐다(사용자 지시 2026-09-25: "옵션 없어서 셋업 안 된 것도 전부 로그에").
# 실패(✗)·경고(⚠)와 섞이면 안 된다 — 이건 "안 켰다" 지 "깨졌다" 가 아니다. 그래서 표식이 다르다(○).
#
#   . infra/scripts/lib/skip-ledger.sh
#   HWAX_SKIP_LEDGER="$(mktemp)"; export HWAX_SKIP_LEDGER      # update-all 이 만들고 자식에게 물려준다
#   hwax_skip <name> <why> <how>          # 즉시 한 줄 찍고 장부에 적는다
#   hwax_skip_record <name> <why> <how>   # 장부에만(호출자가 이미 사유를 찍었을 때 — 게이트 lib)
#   hwax_skip_summary                     # 마지막 요약: 전부 다시, "켜려면" 과 함께
#
# 장부는 파일이다 — 자식 스크립트(deploy-ste.sh·deploy-gate.sh·env-sync.sh)가 같은 파일에 적어야
# 요약이 한 곳에 모인다. 변수로는 자식이 부모에게 못 돌려준다.
hwax_skip_record() {
  [ -n "${HWAX_SKIP_LEDGER:-}" ] || return 0
  printf '%s\t%s\t%s\n' "$1" "$2" "$3" >> "$HWAX_SKIP_LEDGER"
}
hwax_skip() {
  printf '  \033[1;35m○\033[0m %s — %s\n      켜려면: %s\n' "$1" "$2" "$3"
  hwax_skip_record "$1" "$2" "$3"
}
hwax_skip_summary() {
  [ -n "${HWAX_SKIP_LEDGER:-}" ] && [ -s "$HWAX_SKIP_LEDGER" ] || return 0
  # 중복은 지운다(같은 키를 두 번 적는 경우가 있다). "설정 <키>" 항목은 env-sync 가 1c 에서 이미 키마다 한 줄씩
  # 찍었으므로 여기서는 **키 이름만 한 줄로 접는다** — 실측에서 28개가 풀려 나와 정작 기능 항목(ste 라우트)이 묻혔다.
  local body; body="$(awk -F'\t' '!seen[$0]++' "$HWAX_SKIP_LEDGER")"
  local feats cfgs
  feats="$(printf '%s\n' "$body" | awk -F'\t' '$1 !~ /^설정 /')"
  cfgs="$(printf '%s\n' "$body" | awk -F'\t' '$1 ~ /^설정 / {sub(/^설정 /, "", $1); print $1}' | awk '!seen[$0]++')"
  local n_f n_c; n_f="$(printf '%s' "$feats" | grep -c . || true)"; n_c="$(printf '%s' "$cfgs" | grep -c . || true)"
  printf '  \033[1;35m○\033[0m 있는데 안 켠 기능 %s개 · 값 미정 설정 %s개 — 옵션·설정이 없어 이번 실행에서 셋업하지 않았다(실패가 아니다)\n' "$n_f" "$n_c"
  [ -n "$feats" ] && printf '%s\n' "$feats" | while IFS="$(printf '\t')" read -r name why how; do
    printf '    · %s — %s\n        켜려면: %s\n' "$name" "$why" "$how"
  done
  if [ -n "$cfgs" ]; then
    printf '    · 값 미정 설정(주석으로만 들어감 — 그 설정이 켜는 기능은 꺼져 있다): %s\n' "$(printf '%s\n' "$cfgs" | paste -sd, - | sed 's/,/, /g')"
    printf '        켜려면: 각 리포 .env 에서 값을 정하고 재실행 (어느 리포인지는 위 1c 의 ⚠ 줄)\n'
  fi
}
