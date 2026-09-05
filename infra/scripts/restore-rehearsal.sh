#!/usr/bin/env bash
# 백업 복원 리허설 — backup-local 의 최신 pg 덤프를 실제로 복원해 표 행수를 라이브와 대조한다(원칙 D3: 백업 없이 이동 없음).
#
#   ./infra/scripts/restore-rehearsal.sh <svc>                 # 인스턴스 안에 <db>_rehearsal 생성·복원·대조·DROP (mxwp·kooremapper·heax)
#   ./infra/scripts/restore-rehearsal.sh <svc> --temp PORT      # 같은 SIF 로 임시 인스턴스를 /data 에 띄워 복원(aidh·signalforge —
#                                                               #   HNSW 인덱스 재빌드를 라이브 인스턴스(maintenance_work_mem 64MB)에 시키지 않는다; D12 예외)
#   ./infra/scripts/restore-rehearsal.sh <svc> --sqlite <db>    # sqlite: python .backup → integrity → 표 행수 대조
#
# 입력은 backup-local 의 plain SQL(pg_dump|gzip) — pg_restore 가 아니라 psql. ON_ERROR_STOP 없으면 거짓 초록(사전점검).
# 끝나면 항상 정리한다(DROP / instance stop / rm -r) — 실패해도 trap 으로.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PARENT="$(dirname "$ROOT")"
find_repo() { local n="$1"; for c in "$PARENT/$n" "$HOME/Projects/$n" "$HOME/claude/$n"; do [ -d "$c" ] && { printf '%s' "$c"; return; }; done; }
env_get() { local v; v="$(sed -n "s/^$2=//p" "$1" 2>/dev/null | tail -1 | sed 's/[[:space:]]*#.*$//; s/^["'"'"']//; s/["'"'"']$//')"; [ -n "$v" ] || return 1; printf '%s' "$v"; }
url_part() { case "$2" in user) sed -E 's#^[a-z+]+://([^:/@]+)(:[^@]*)?@.*#\1#' <<<"$1";; pw) sed -nE 's#^[a-z+]+://[^:/@]+:([^@]*)@.*#\1#p' <<<"$1";; port) sed -nE 's#^[a-z+]+://[^@]+@[^:/]+:([0-9]+)/.*#\1#p' <<<"$1";; db) sed -E 's#^.*/([^/?]+)(\?.*)?$#\1#' <<<"$1";; esac; }
BOX="${HWAX_BOX:-$(env_get "$ROOT/infra/.env" HWAX_BOX 2>/dev/null || hostname -s)}"
BK="${BACKUP_ROOT:-/data/backups}/hwax/$BOX"
ok() { printf '  \033[1;32m✓\033[0m %s\n' "$*"; }; bad() { printf '  \033[1;31m✗\033[0m %s\n' "$*"; }
SVC="${1:?사용: restore-rehearsal.sh <svc> [--temp PORT|--sqlite <db>]}"; MODE="${2:-}"; ARG="${3:-}"

# ── 서비스 → 인스턴스·접속값·SIF ──
case "$SVC" in
  mxwp)        D="$(find_repo MXWhitePaper)"; E="$D/.env"; INST=mxwp_postgres; USER_="$(env_get "$E" POSTGRES_USER || echo mxwp)"; PORT="$(env_get "$E" POSTGRES_PORT || echo 5532)"; DB="$(env_get "$E" POSTGRES_DB || echo mxwp)"; PW="$(env_get "$E" POSTGRES_PASSWORD || true)"; SIF="$D/infra/apptainer/postgres.sif" ;;
  kooremapper) D="$(find_repo KooRemapper)"; E="$D/platform/.env"; INST=koorm_postgres; USER_="$(env_get "$E" POSTGRES_USER || echo koorm)"; PORT="$(env_get "$E" POSTGRES_PORT || echo 5436)"; DB="$(env_get "$E" POSTGRES_DB || echo koorm)"; PW="$(env_get "$E" POSTGRES_PASSWORD || true)"; SIF="$D/platform/infra/apptainer/postgres.sif" ;;
  heax)        D="$(find_repo HEAXHub)"; URL="$(env_get "$D/.env" DATABASE_URL)"; INST=heax-pg; USER_="$(url_part "$URL" user)"; PORT="$(url_part "$URL" port)"; DB="$(url_part "$URL" db)"; PW="$(url_part "$URL" pw)"; SIF="$HOME/serviceApptainers/heaxhub_postgres.sif" ;;
  signalforge) D="$(find_repo SignalForge)"; E="$D/.env"; INST=sf_postgres; USER_="$(env_get "$E" POSTGRES_USER || echo signalforge)"; PORT="$(env_get "$E" POSTGRES_PORT || echo 5434)"; DB="$(env_get "$E" POSTGRES_DB || echo signalforge)"; PW="$(env_get "$E" POSTGRES_PASSWORD || true)"; SIF="$D/apptainer/sif/postgres.sif" ;;
  aidh)        D="$(find_repo AIDataHub)"; E="$D/deploy/apptainer/.env"; INST="$(env_get "$E" INST_POSTGRES || echo aidh_postgres)"; USER_="$(env_get "$E" POSTGRES_USER)"; PORT="$(env_get "$E" POSTGRES_PORT)"; DB="$(env_get "$E" POSTGRES_DB)"; PW="$(env_get "$E" POSTGRES_PASSWORD || true)"; SIF="$D/deploy/apptainer/postgres.sif" ;;
  *) [ "$MODE" = "--sqlite" ] || { echo "모르는 서비스: $SVC"; exit 2; } ;;
esac

# ── sqlite 모드 ──
if [ "$MODE" = "--sqlite" ]; then
  SRC="$ARG"; T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
  python3 "$ROOT/infra/scripts/lib/sqlite_backup.py" backup "$SRC" "$T/r.db" && ok "backup → $T/r.db" || { bad "backup 실패"; exit 1; }
  [ "$(python3 "$ROOT/infra/scripts/lib/sqlite_backup.py" check "$T/r.db")" = ok ] && ok "integrity ok" || { bad "integrity 실패"; exit 1; }
  A="$(python3 "$ROOT/infra/scripts/lib/sqlite_backup.py" counts "$SRC")"; B="$(python3 "$ROOT/infra/scripts/lib/sqlite_backup.py" counts "$T/r.db")"
  [ "$A" = "$B" ] && ok "표 행수 일치: $B" || { bad "표 행수 불일치"; echo "  live=$A"; echo "  copy=$B"; exit 1; }
  exit 0
fi

DUMP="$(ls -t "$BK/$SVC/daily/${SVC}-${BOX}-"*.sql.gz 2>/dev/null | head -1)"
[ -n "$DUMP" ] || { bad "덤프 없음: $BK/$SVC/daily/ — backup-local.sh $SVC 먼저"; exit 1; }
sha256sum -c --quiet <(printf '%s  %s\n' "$(cat "$DUMP.sha256")" "$DUMP") && ok "입력 $(basename "$DUMP") ($(du -h "$DUMP" | cut -f1)) sha256 OK" || { bad "sha256 불일치"; exit 1; }

PSQL_LIVE=(apptainer exec ${PW:+--env "PGPASSWORD=$PW"} "instance://$INST" psql -h 127.0.0.1 -p "$PORT" -U "$USER_" -v ON_ERROR_STOP=1 -q)
table_counts() { # psql-prefix... -d DB → 'table=count' 줄들(정확 count)
  local -a P=("${@:1:$#-1}"); local db="${@: -1}"
  "${P[@]}" -d "$db" -Atc "select string_agg(format('select %L||''=''||count(*) from %I.%I', table_name, table_schema, table_name), ' union all ') from information_schema.tables where table_schema not in ('pg_catalog','information_schema') and table_type='BASE TABLE'" 2>/dev/null | { read -r q; [ -n "$q" ] && "${P[@]}" -d "$db" -Atc "$q" 2>/dev/null | sort; }
}

if [ "$MODE" = "--temp" ]; then
  # ── 같은 SIF 임시 인스턴스(/data, 별 포트) ──
  TPORT="${ARG:?--temp 는 포트 필요}"; TINST="rehearsal_${SVC}"; R="/data/hwax/.staging/rehearsal/$SVC"
  ss -ltn 2>/dev/null | grep -q ":$TPORT " && { bad ":$TPORT 사용 중"; exit 1; }
  [ -f "$SIF" ] || { bad "SIF 없음: $SIF"; exit 1; }
  cleanup() { apptainer instance stop "$TINST" >/dev/null 2>&1 || true; rm -rf "$R"; echo "  · 정리: instance $TINST stop · $R 삭제"; }
  trap cleanup EXIT
  rm -rf "$R"; mkdir -p "$R/pgdata" "$R/run"
  apptainer instance start --bind "$R:/var/lib/postgresql/data" --bind "$R/run:/var/run/postgresql" \
    --env "POSTGRES_USER=$USER_" --env "POSTGRES_PASSWORD=${PW:-rehearsal}" --env "POSTGRES_DB=postgres" --env "PGPORT=$TPORT" \
    --env "PGDATA=/var/lib/postgresql/data/pgdata" --env "LANG=C.UTF-8" --env "LC_ALL=C.UTF-8" "$SIF" "$TINST" >/dev/null 2>&1 || { bad "임시 인스턴스 기동 실패"; exit 1; }
  for i in $(seq 1 60); do apptainer exec "instance://$TINST" pg_isready -h 127.0.0.1 -p "$TPORT" -q 2>/dev/null && break; sleep 2; done
  apptainer exec "instance://$TINST" pg_isready -h 127.0.0.1 -p "$TPORT" -q 2>/dev/null && ok "임시 인스턴스 $TINST :$TPORT (PGDATA $R)" || { bad "임시 인스턴스 준비 실패"; exit 1; }
  PSQL_T=(apptainer exec --env "PGPASSWORD=${PW:-rehearsal}" "instance://$TINST" psql -h 127.0.0.1 -p "$TPORT" -U "$USER_" -v ON_ERROR_STOP=1 -q)
  RDB="$DB"
  "${PSQL_T[@]}" -d postgres -c "CREATE DATABASE \"$RDB\"" >/dev/null || { bad "CREATE DATABASE 실패"; exit 1; }
else
  # ── 라이브 인스턴스 안 <db>_rehearsal ──
  RDB="${DB}_rehearsal"; PSQL_T=("${PSQL_LIVE[@]}")
  cleanup() { "${PSQL_LIVE[@]}" -d postgres -c "DROP DATABASE IF EXISTS \"$RDB\" WITH (FORCE)" >/dev/null 2>&1 && echo "  · 정리: DROP $RDB"; }
  trap cleanup EXIT
  "${PSQL_LIVE[@]}" -d postgres -c "DROP DATABASE IF EXISTS \"$RDB\" WITH (FORCE)" >/dev/null 2>&1
  "${PSQL_LIVE[@]}" -d postgres -c "CREATE DATABASE \"$RDB\"" >/dev/null || { bad "CREATE DATABASE $RDB 실패"; exit 1; }
fi

t0=$(date +%s)
if gunzip -c "$DUMP" | "${PSQL_T[@]}" -d "$RDB" >/dev/null 2>"$BK/$SVC/rehearsal-${SVC}.err"; then
  ok "복원 완료 → $RDB ($(( $(date +%s) - t0 ))s)"; rm -f "$BK/$SVC/rehearsal-${SVC}.err"
else
  bad "복원 실패(ON_ERROR_STOP) — $BK/$SVC/rehearsal-${SVC}.err:"; tail -3 "$BK/$SVC/rehearsal-${SVC}.err" | sed 's/^/    /'; exit 1
fi
LIVE="$(table_counts "${PSQL_LIVE[@]}" "$DB")"; REH="$(table_counts "${PSQL_T[@]}" "$RDB")"
if [ -n "$LIVE" ] && [ "$LIVE" = "$REH" ]; then
  ok "표 행수 전부 일치 ($(printf '%s\n' "$REH" | wc -l)표)"
else
  # 라이브는 덤프 뒤에도 쓰이므로 소수 표의 증분은 정상 — 표 집합이 같고 차이가 '늘어난 쪽' 뿐인지 보인다
  echo "  · 표별 차이(live vs rehearsal):"; diff <(printf '%s\n' "$LIVE") <(printf '%s\n' "$REH") | grep -E '^[<>]' | sed 's/^/    /' | head -12
  [ "$(printf '%s\n' "$LIVE" | cut -d= -f1)" = "$(printf '%s\n' "$REH" | cut -d= -f1)" ] && ok "표 집합 동일(행수 차이는 덤프 이후 라이브 증분 — 위 목록 검토)" || { bad "표 집합 불일치"; exit 1; }
fi
