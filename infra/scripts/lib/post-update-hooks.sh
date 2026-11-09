#!/usr/bin/env bash
# update-all 끝의 박스 훅 — infra/hooks/post-update.d/*.local.sh 를 이름 차례로 돌린다(docs/core-link SRC-12)
#
#   . infra/scripts/lib/post-update-hooks.sh
#   hwax_post_update_hooks <포털 리포 루트>   # 훅을 돌리고 끝 요약 줄을 HWAX_HOOKS_NOTE 에 남긴다 — 반환은 늘 0
#   hwax_box_busy <포털 리포 루트>            # 일이 있나 — 0 있다 · 1 없다 · 2 셀 수 없다, 표준 출력에 한 줄 설명
#
# 규칙(docs/core-link design §1 · context-notes CK-6)
#   · 훅은 git 이 모르는 박스 파일이다 — .gitignore 가 지킨다. 지키지 않으면 update-all §1 · deploy-all 의 git stash -u 가 치운다.
#   · 실패는 update-all 의 종료코드에 섞지 않는다(fail 도 bad 도 아니다) — 끝 요약의 따로 줄 하나로만 낸다.
#   · 훅이 없으면 ○(있는데 안 켠 것)다. 종료 요청이 있었거나, --hooks-when-idle 인데 일이 있거나 셀 수 없으면 ○ 로 건너뛴다.
#   · 훅마다 상한 HWAX_HOOK_TIMEOUT_S(기본 3600초) — 넘기면 HWAX_STEP_ID 표식으로 남은 프로세스까지 정리하고(_reap_step) 실패로 센다.
#   · 훅은 포털 리포 루트에서, 표준 입력 없이 bash 로 돈다. 환경에 HWAX_UPDATE_FAIL(이 실행이 이미 실패를 셌으면 1)이 실린다.

_HWAX_HOOK_LIB="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

_hwax_hook_repo() {  # <이름> <포털 루트> — update-all 의 find_repo 와 같은 차례(<포털 상위>/ → ~/Projects/ → ~/claude/). 없으면 빈 값
  local c
  for c in "$2/../$1" "$HOME/Projects/$1" "$HOME/claude/$1"; do
    [ -d "$c" ] && { (cd "$c" && pwd); return 0; }
  done
  return 0
}

_hwax_join() {  # <구분자> <항목…>
  local sep="$1" out="" x
  shift
  for x in "$@"; do out="${out:+$out$sep}$x"; done
  printf '%s' "$out"
}

# 바쁨은 사전 점검(update-preflight.py '지금 도는 일')과 update-all 이 이미 쓰는 셈 그대로다 — 에이전트 /health(도는 · 줄 선 심의, 리스크
# 카드 대조) · DynaForge 로컬 작업 · StepForge(pending · running) · DocForge(queued · running). 그 앱이 없는 박스는 그 칸을 빼고 센다.
# MX 백서 위키 작업은 lease 로 이어 집으므로 넣지 않는다. 셀 수 없는 칸이 하나라도 있으면 '없다' 가 아니라 '모름' 이다(모름 ≠ 없음).
hwax_box_busy() {
  local root="$1" parts=() unknown=() busy=0 st rc=0 ra dr don da dq krm hub app rel sts db n line
  declare -F hwax_review_state >/dev/null || . "$_HWAX_HOOK_LIB/review-drain.sh"
  declare -F hwax_koorm_running_jobs >/dev/null || . "$_HWAX_HOOK_LIB/koorm-busy.sh"
  st="$(hwax_review_state)" || rc=$?
  if [ "$rc" = 0 ] && read -r ra dr don da dq <<<"$st" && [ -n "${dq:-}" ]; then
    parts+=("심의 $da · 줄 $dq · 카드 대조 $ra")
    [ $((ra + da + dq)) -gt 0 ] && busy=1
  else
    unknown+=("에이전트 서버 /health(rc $rc)")
  fi
  krm="$(_hwax_hook_repo KooRemapper "$root")"
  if [ -n "$krm" ] && [ -f "$krm/platform/infra/scripts/_common.sh" ]; then
    n="$(hwax_koorm_running_jobs "$krm")"
    if [ -n "$n" ]; then
      parts+=("DynaForge $n"); [ "$n" -gt 0 ] && busy=1
    else
      unknown+=("DynaForge 작업")
    fi
  fi
  hub="$(_hwax_hook_repo HEAXHub "$root")"
  if [ -n "$hub" ]; then
    for spec in "StepForge:step_forge/stepforge.db:pending,running" "DocForge:doc_forge/docforge.db:queued,running"; do
      IFS=: read -r app rel sts <<<"$spec"
      db="$hub/var/app_data/$rel"
      [ -e "$db" ] || continue
      # 읽기로만 연다 — 떠 있는 앱의 DB 를 잠그지 않는다(사전 점검의 ro_sqlite 와 같은 길).
      n="$(python3 -I - "$db" "$sts" <<'PY' 2>/dev/null
import pathlib, sqlite3, sys
st = sys.argv[2].split(",")
try:
    c = sqlite3.connect(pathlib.Path(sys.argv[1]).resolve().as_uri() + "?mode=ro", uri=True, timeout=2)
    try:
        print(c.execute("SELECT count(*) FROM jobs WHERE status IN (%s)" % ",".join("?" * len(st)), st).fetchone()[0])
    finally:
        c.close()
except sqlite3.Error:
    sys.exit(2)
PY
)"
      if [[ "$n" =~ ^[0-9]+$ ]]; then
        parts+=("$app $n"); [ "$n" -gt 0 ] && busy=1
      else
        unknown+=("$app 작업 DB")
      fi
    done
  fi
  line="$(_hwax_join ' · ' "${parts[@]}")"
  [ ${#unknown[@]} -eq 0 ] || line="${line:+$line · }셀 수 없음: $(_hwax_join ' · ' "${unknown[@]}")"
  printf '%s\n' "$line"
  [ "$busy" = 1 ] && return 0
  [ ${#unknown[@]} -gt 0 ] && return 2
  return 1
}

hwax_post_update_hooks() {
  local root="$1" dir h name rc n=0 to busy brc=0
  local hooks=() odd=() done_=() failed=()
  dir="$root/infra/hooks/post-update.d"
  HWAX_HOOKS_NOTE=""
  if [ -d "$dir" ]; then
    # 이름 차례는 로캘과 무관하게 C 차례다 — 박스마다 LANG 이 달라도 같은 차례로 돈다.
    while IFS= read -r h; do [ -n "$h" ] && hooks+=("$h"); done < <(
      shopt -s nullglob; for h in "$dir"/*.local.sh; do printf '%s\n' "$h"; done | LC_ALL=C sort)
    while IFS= read -r h; do [ -n "$h" ] && odd+=("${h##*/}"); done < <(
      shopt -s nullglob; for h in "$dir"/*.sh; do case "$h" in *.local.sh) ;; *) printf '%s\n' "$h" ;; esac; done | LC_ALL=C sort)
  fi
  # 이름이 틀린 훅은 돌리지 않고 짚는다 — 조용히 넘어가면 '두었는데 안 돈다' 를 찾을 데가 없고, git 이 몰라 다음 stash 가 치운다.
  [ ${#odd[@]} -eq 0 ] || echo "  · 박스 훅 — 돌리지 않는 파일: $(_hwax_join ' · ' "${odd[@]}") (훅은 이름이 .local.sh 로 끝나야 한다 — 그 밖의 이름은 git 이 몰라 update-all 의 stash 가 치운다)"
  if [ ${#hooks[@]} -eq 0 ]; then
    hwax_skip "박스 훅(update-all 끝)" "infra/hooks/post-update.d 에 *.local.sh 가 없다" \
      "그 폴더에 NN-이름.local.sh 를 두면 끝 요약 앞에서 이름 차례로 돈다 — 실패는 종료코드에 들지 않는다(infra/hooks/post-update.d/README.md)"
    return 0
  fi
  if [ "${HWAX_UPDATE_ALL_STOP:-0}" = 1 ]; then
    hwax_skip "박스 훅 ${#hooks[@]}개" "종료 요청이 있어 돌리지 않았다" "다음 update-all 끝에서 돈다"
    return 0
  fi
  if [ "${HWAX_HOOKS_WHEN_IDLE:-0}" = 1 ]; then
    busy="$(hwax_box_busy "$root")" || brc=$?
    case "$brc" in
      1) echo "  · 박스 훅 — 일이 없다($busy)" ;;
      0) hwax_skip "박스 훅 ${#hooks[@]}개" "--hooks-when-idle — 일이 있다($busy)" \
           "일이 끝난 뒤 update-all 을 다시 돌리거나 --hooks-when-idle 없이 돌린다"
         return 0 ;;
      *) hwax_skip "박스 훅 ${#hooks[@]}개" "--hooks-when-idle — 일이 있는지 셀 수 없다($busy)" \
           "셀 수 없는 칸을 살린 뒤 다시 돌리거나 --hooks-when-idle 없이 돌린다"
         return 0 ;;
    esac
  fi
  to="${HWAX_HOOK_TIMEOUT_S:-3600}"
  [[ "$to" =~ ^[1-9][0-9]*$ ]] || { echo "  · 박스 훅 — HWAX_HOOK_TIMEOUT_S=${to:0:20} 을 읽지 못했다(양의 정수 초) — 3600초로 돈다"; to=3600; }
  for h in "${hooks[@]}"; do
    name="${h##*/}"; n=$((n + 1)); rc=0
    echo "  ▶ 박스 훅 $name"
    # --foreground 는 단계 상한(§2c ste)과 같은 까닭이다 — 사람이 Ctrl-C 를 누르면 훅도 받는다. 대신 훅의 자식은 TERM 을 못 받으니
    # 표식(HWAX_STEP_ID)으로 _reap_step 이 거둔다. -k 30 — TERM 을 삼키는 훅도 30초 뒤에는 끝난다.
    ( cd "$root" && HWAX_STEP_ID="hook-$$-$n" HWAX_UPDATE_FAIL="${FAIL:-0}" timeout --foreground -k 30 "$to" bash "$h" </dev/null ) || rc=$?
    case "$rc" in
      0) done_+=("$name") ;;
      124) failed+=("$name(상한 ${to}초)")
           declare -F _reap_step >/dev/null && _reap_step "hook-$$-$n" ;;
      137) failed+=("$name(rc 137 — 상한 뒤 KILL 했거나 밖에서 죽었다)")
           declare -F _reap_step >/dev/null && _reap_step "hook-$$-$n" ;;
      *) failed+=("$name(rc $rc)") ;;
    esac
  done
  if [ ${#failed[@]} -eq 0 ]; then
    printf -v HWAX_HOOKS_NOTE '  · 박스 훅 %s개 — 모두 끝났다: %s\n' "${#hooks[@]}" "$(_hwax_join ' · ' "${done_[@]}")"
  else
    printf -v HWAX_HOOKS_NOTE '  \033[1;33m⚠\033[0m 박스 훅 %s개 중 %s개 실패 — %s · 종료코드에는 넣지 않는다(출력은 위 ▶ 박스 훅 줄 아래)\n' \
      "${#hooks[@]}" "${#failed[@]}" "$(_hwax_join ' · ' "${failed[@]}")"
  fi
  printf '%s' "$HWAX_HOOKS_NOTE"
  return 0
}
