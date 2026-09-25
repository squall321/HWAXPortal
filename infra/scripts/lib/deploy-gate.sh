#!/usr/bin/env bash
# 무거운·외부 배포 단계의 **공용 게이트** — "사람이 불렀나 ∧ 바뀐 게 있나 ∧ 전제가 서 있나"
#
#   . infra/scripts/lib/deploy-gate.sh
#   if hwax_gate ste --fresh 'cmd' --precond 'cmd'; then <배포>; else echo "$HWAX_GATE_REASON"; fi
#
# 왜 공용인가 — ste 가 첫 사용처지만 사용자 결정(docs/ste-cae00 D-13)은 "새 옵션이 생겨도 유용해야
# 한다" 였다. 다음에 에어갭·외부 클러스터 배포 단계가 생기면 여기에 **이름 하나 더하는 것**으로 끝나야
# 하고, 게이트 규칙이 스크립트마다 다르게 복제되면 안 된다.
#
# 세 신호가 **모두** 참일 때만 0 을 돌려준다.
#   ① 사람 호출  — 대화형 터미널(`[ -t 0 ]`)이거나, 그 이름이 HWAX_WITH 에 있거나(update-all --with-<name>),
#                  <NAME>_DEPLOY=1 이거나(옛 손잡이·호환). 크론·파이프에서는 셋 다 아니다.
#   ② 신선도    — `--fresh` 명령이 0 이면 "바뀐 게 있다". 1 이면 "같다"(건너뜀). 그 밖(2+)은 "모름".
#                  ⚠ **모름은 같음이 아니다** — 못 잰 것을 같다고 읽으면 낡은 박스를 영원히 건너뛴다.
#                  그래서 모름이면 ①이 참일 때만 통과시킨다(사람이 봤으니 간다).
#   ③ 전제조건  — `--precond` 명령이 0 이어야 한다(예: Teleport 세션 살아 있음). 아니면 사유를 남기고 멈춘다.
#
# 명시 강제 — HWAX_WITH 에 그 이름이 있으면 ①②를 참으로 본다(사람이 "지금 이거 해라" 고 한 것).
# 결과 사유는 HWAX_GATE_REASON 에 남는다(호출자가 한 줄로 찍는다).
hwax_gate() {
  local name="$1"; shift
  local fresh="" precond=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --fresh)   fresh="$2"; shift 2 ;;
      --precond) precond="$2"; shift 2 ;;
      *) echo "hwax_gate: 모르는 인자 $1" >&2; return 2 ;;
    esac
  done
  local upper; upper="$(printf '%s' "$name" | tr '[:lower:]-' '[:upper:]_')"
  local forced=0 human=0
  case " ${HWAX_WITH:-} " in *" $name "*) forced=1 ;; esac
  eval "[ \"\${${upper}_DEPLOY:-0}\" = 1 ]" && forced=1
  { [ -t 0 ] || [ "$forced" = 1 ] || [ "${UPDATE_ALL_INTERACTIVE:-0}" = 1 ]; } && human=1
  HWAX_GATE_REASON=""

  if [ "$human" != 1 ]; then
    HWAX_GATE_REASON="$name: 사람이 부른 실행이 아니다(터미널 아님·--with-$name 없음) — routine 에서는 배포하지 않는다"
    return 1
  fi
  local freshness=0   # 0=바뀜 1=같음 2=모름
  if [ "$forced" != 1 ] && [ -n "$fresh" ]; then
    if bash -c "$fresh" >/dev/null 2>&1; then freshness=0
    else
      case $? in 1) freshness=1 ;; *) freshness=2 ;; esac
    fi
  fi
  if [ "$freshness" = 1 ]; then
    HWAX_GATE_REASON="$name: 이미 최신 — 배포할 변경이 없다"
    return 1
  fi
  if [ -n "$precond" ] && ! bash -c "$precond" >/dev/null 2>&1; then
    HWAX_GATE_REASON="$name: 전제조건 실패 — $(printf '%s' "$precond" | cut -c1-60)"
    return 1
  fi
  [ "$freshness" = 2 ] && HWAX_GATE_REASON="$name: 신선도를 못 쟀다(모름) — 사람이 불렀으니 진행한다"
  return 0
}
