# DynaForge(KooRemapper)에서 지금 도는 로컬 작업 수 — 배치가 그 스택을 내리기 전에 센다(내리면 끊기고 실패로 적힌다)
#
# hwax_koorm_running_jobs <KooRemapper 리포> → 수(0 이상) 한 줄, 셀 수 없으면 빈 값(인스턴스가 없다 · DB 가 안 받는다 · .env 가 없다).
#   stcx 외부 잡(external_kind 가 있는 것)은 빼고 센다 — 클러스터에서 돌고 재기동을 넘긴다(DynaForge 의 worker/runner_loop ·
#   modules/system/routes 와 같은 기준). 로컬 작업은 스택을 내리면 SIGKILL 로 끊기고, 다시 뜰 때 'worker restarted while job was
#   running' 으로 실패가 된다(10-25 cae00 업데이트 점검).
#   psql 은 그 리포의 backup-db.sh 와 같은 길로 부른다 — _common.sh 가 .env(POSTGRES_*) · APPTAINER · INST_POSTGRES 를 세운다.
hwax_koorm_running_jobs() {
  local repo="$1"
  ( cd "$repo" 2>/dev/null || exit 0
    . platform/infra/scripts/_common.sh >/dev/null 2>&1 || exit 0
    "$APPTAINER" exec instance://"$INST_POSTGRES" psql -U "$POSTGRES_USER" -p "$POSTGRES_PORT" "$POSTGRES_DB" -tAc \
      "SELECT count(*) FROM jobs WHERE status = 'running' AND external_kind IS NULL" 2>/dev/null
  ) | tr -d '[:space:]' | grep -E '^[0-9]+$' || true
}
