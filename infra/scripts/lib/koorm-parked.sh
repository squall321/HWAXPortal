#!/usr/bin/env bash
# 이 박스의 DynaForge(KooRemapper) 로컬 스택을 '멈춰 둔 되돌림 사본' 으로 표시했는지 — 포털 infra/.env 의 KOORM_LOCAL_PARKED 를 배치들이 한 규칙으로 읽는다
#
# 왜 — cae00 은 11-12 에 DynaForge 를 운영 노드로 옮겼고(컷오버) 이 박스의 KooRemapper 스택은 일부러 멈춰 둔 되돌림 사본이다. deploy-all 의 기본 목록이
# 그 스택을 다시 띄우고 이관(start.sh) · 감시 크론 · 백업 크론(install-autostart.sh)까지 걸었다(11-23 라운드 — 21:31 에 떴고 박스 뒤처리가 22:04 에 다시
# 내렸다, HP-66 · HP-67). §1b 사전 백업은 일부러 내린 DB 를 ✗ 로 셌다.
#
# 표시 — 포털 infra/.env 의 KOORM_LOCAL_PARKED. 값이 있으면(0 도) 멈춰 둔 것이다. services.yaml kooremapper 의 unless_env 와 같은 키 · 같은 뜻 · 같은
# 차례다(환경변수가 비어 있지 않으면 그것, 아니면 infra/.env 의 마지막 활성 줄 — 그래서 services.sh up · 상태판도 그 스택을 '이 박스 대상 아님' 으로 둔다).
# 줄 읽기는 update-all _envfile_value · deploy-all _envv · services.py _infra_value 와 글자 단위로 같은 규칙이다(시험 test_koorm_parked 가 견준다).
# 동결 SIF(HEAX_FROZEN_SIFS — 허브 앱 SIF 의 판을 묶는다, lib/heax-frozen.sh)와는 다른 것이다 — 이것은 스택을 띄우지 않는다.
# 표시가 있어도 코드(git) · Drive 배포물은 받는다 — 인스턴스가 내려가 있어 덮어도 깨질 마운트가 없고, 다시 쓸 때 코드 · 바이너리 · 화면이 같은 판이며,
# 운영 측이 KooRemapper 의 점검 문서(docs/requests/…)를 그 리포의 HEAD 로 읽는다.
#
#   hwax_koorm_parked <포털 리포>   0 = 멈춰 둠 · 1 = 아니다(키가 없다 — 종전 동작)
#   hwax_koorm_parked_skip          ○ 한 줄(화면) + 장부 — deploy-all 의 KooRemapper 구역
#   hwax_koorm_parked_record        장부에만 — 자기 문맥 줄을 따로 찍는 곳(사전 백업). 둘이 같은 이름 · 사유 · 켜는 법이라 끝 요약에는 한 번만 남는다.
# ○ 장부(hwax_skip · hwax_skip_record)는 lib/skip-ledger.sh 다 — 부르는 쪽이 먼저 소싱한다.

_HWAX_KOORM_PARKED_NAME="DynaForge(KooRemapper) 로컬 스택 — 멈춰 둠"
_HWAX_KOORM_PARKED_WHY="포털 infra/.env 의 KOORM_LOCAL_PARKED 가 이 박스의 스택을 멈춰 둔 되돌림 사본으로 표시했다 — 띄우지 · 이관하지 · 감시와 백업 예약을 걸지 · 사전 백업을 뜨지 않는다(코드 · Drive 배포물은 받는다)"
_HWAX_KOORM_PARKED_HOW="이 박스의 스택을 다시 쓸 때 — infra/.env 의 KOORM_LOCAL_PARKED 줄을 지우고(0 도 멈춤으로 읽는다) update-all(또는 deploy-all-from-drive.sh kooremapper)을 돌린다"

_hwax_koorm_parked_value() {  # $1=파일 → 마지막 활성 줄의 값(없으면 빈 문자열). update-all _envfile_value 와 같은 줄이다 — 고치면 함께 고친다
  # `|| :` — 파일이 없으면 첫 sed 가 2 로 끝나고 pipefail 이 그것을 문다. set -e 인 배치(deploy-all)에서 그 자리에 죽지 않게 한다.
  LC_ALL=C sed -n -E "s/^[[:space:]]*(export[[:space:]]+)?KOORM_LOCAL_PARKED=//p" "$1" 2>/dev/null | tail -1 \
    | LC_ALL=C sed -E 's/[[:space:]]+#.*$//; s/^[[:space:]]+//; s/[[:space:]]+$//' | LC_ALL=C tr -d '"'"'"'\r' || :
}

hwax_koorm_parked() {
  local v="${KOORM_LOCAL_PARKED:-}"
  case "$v" in
    *[![:space:]]*) ;;                                     # 환경에 비어 있지 않은 값 — 그것이 이긴다(services.py 와 같은 차례)
    *) v="$(_hwax_koorm_parked_value "$1/infra/.env")" ;;
  esac
  [ -n "$v" ]
}

hwax_koorm_parked_skip() {
  hwax_skip "$_HWAX_KOORM_PARKED_NAME" "$_HWAX_KOORM_PARKED_WHY" "$_HWAX_KOORM_PARKED_HOW"
}

hwax_koorm_parked_record() {
  hwax_skip_record "$_HWAX_KOORM_PARKED_NAME" "$_HWAX_KOORM_PARKED_WHY" "$_HWAX_KOORM_PARKED_HOW"
}
