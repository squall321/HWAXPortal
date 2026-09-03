#!/usr/bin/env bash
# DynaForge(KooRemapper)·StepForge 표적 최신화 — update-all(전체 배포)이 무거울 때.
#
#   ./infra/scripts/update-forges.sh                 # 둘 다
#   ./infra/scripts/update-forges.sh stepforge       # 하나만
#   ./infra/scripts/update-forges.sh dynaforge
#
# 박스 자동 감지 — 리포 루트가 */Projects/* 면 cae00(운영: git pull + Drive 반입),
# 아니면 dev(로컬 소스 그대로 — 타 세션 WIP 를 pull/reset 으로 건드리지 않는다).
#
# 무엇을 하나.
#   stepforge : HEAXHub redeploy-app.sh step_forge --rebuild
#               (--rebuild 가 upstream git fetch→SIF 빌드→재기동까지. 게이트웨이는
#                지문 감지가 60초 내 자동 재집계 — 재기동 불필요)
#   dynaforge : [cae00] KooRemapper git pull --ff-only + dist-from-drive(비치명)
#               [dev]   build-frontend.sh (⚠ plain 'pnpm build' 는 포털용
#                       index.portal.html 을 안 만들어 포털 경유가 깨진다 — 실사고)
#               → stop/start → install-autostart(멱등) → :8700/:8701 프로브
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PARENT="$(dirname "$ROOT")"
find_repo() { for c in "$PARENT/$1" "$HOME/Projects/$1" "$HOME/claude/$1"; do [ -d "$c" ] && { printf '%s' "$c"; return; }; done; }
case "$ROOT" in */Projects/*) BOX=cae00 ;; *) BOX=dev ;; esac
hr() { printf '\n\033[1;36m── %s ─────────────────────\033[0m\n' "$*"; }
FAIL=0

do_stepforge() {
  hr "StepForge — upstream fetch + SIF 리빌드 + 재기동"
  local heax; heax="$(find_repo HEAXHub)"
  [ -n "$heax" ] || { echo "✗ HEAXHub 리포 없음"; FAIL=1; return; }
  # ⚠ heax Settings 가 CWD 상대 .env 를 읽는다 — 포털 루트에서 부르면 포털의
  #   backend/.env(APP_ENV=dev)를 집어 ValidationError 로 죽는다(실측). heax 루트에서 실행.
  if ( cd "$heax" && bash deploy/apptainer/redeploy-app.sh step_forge --rebuild ); then
    echo "✓ step_forge 재배포 — 게이트웨이 지문 재집계는 60초 내 자동"
  else
    echo "✗ step_forge 재배포 실패"; FAIL=1
  fi
}

do_dynaforge() {
  hr "DynaForge(KooRemapper) — $BOX 모드"
  local koor; koor="$(find_repo KooRemapper)"
  [ -n "$koor" ] || { echo "✗ KooRemapper 리포 없음"; FAIL=1; return; }
  ( cd "$koor"
    if [ "$BOX" = cae00 ]; then
      git pull --ff-only || { echo "✗ git pull 실패(로컬 변경?) — 수동 확인 필요"; exit 1; }
      bash platform/infra/scripts/dist-from-drive.sh \
        || echo "  ⚠ dist-from-drive 실패(비치명) — 로컬 아티팩트로 진행"
    else
      # dev: pull 하지 않는다(타 세션 WIP 보호). 프론트만 정식 이중 빌드로 갱신.
      bash platform/infra/scripts/build-frontend.sh
    fi
    bash platform/infra/scripts/stop.sh 2>/dev/null || true
    bash platform/infra/scripts/start.sh
    bash platform/infra/scripts/install-autostart.sh || echo "  ⚠ autostart 설치 실패(비치명)"
  ) || { FAIL=1; return; }
  # 업스트림 생존 — rc 가 아니라 출력값으로 판정한다(000 폴백 덧붙임 함정, deploy-all 주석 참조).
  for p in 8700 8701; do
    c="$(curl -s -o /dev/null -w '%{http_code}' -m 5 "http://127.0.0.1:$p/" 2>/dev/null)" || true
    case "${c:-000}" in
      000) echo "✗ :$p 무응답 — /apps/kooremapper* 는 502 가 된다"; FAIL=1 ;;
      *)   echo "✓ :$p → $c" ;;
    esac
  done
}

WANT="${*:-stepforge dynaforge}"
for t in $WANT; do
  case "$t" in
    stepforge) do_stepforge ;;
    dynaforge) do_dynaforge ;;
    *) echo "✗ 모르는 대상: $t (stepforge|dynaforge)"; FAIL=1 ;;
  esac
done

hr "게이트웨이 확인"
curl -s -m 5 http://127.0.0.1:9110/health | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    down = [k for k, v in d['backends'].items() if not v]
    print(f\"도구 {d['tools']}개 · 백엔드 {sum(d['backends'].values())}/{len(d['backends'])}\"
          + (f' · DOWN: {down}' if down else ''))
except Exception:
    print('게이트웨이 응답 해석 실패')" || echo "게이트웨이 무응답"
[ "$FAIL" = 0 ] && echo "완료 — 전 대상 성공" || echo "일부 실패 — 위 ✗ 항목 확인"
exit "$FAIL"
