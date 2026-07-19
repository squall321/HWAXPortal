#!/usr/bin/env bash
# cae00 프로덕션 데이터 로컬 백업 — /data/backups 아래에 매일 스냅샷 + 세대 보관.
# ⚠ 인터넷(Drive)으로 절대 나가지 않는다. cae00 사내 데이터는 로컬에만 둔다.
# 대상: AIDataHub·SignalForge·MXWhitePaper postgres(pg_dump) + materialtwin SQLite(.backup).
#       ReportArchive 는 hands-off — 백업 대상 아님(의도).
#
#   ./infra/scripts/backup-local.sh                 # 전부
#   BACKUP_ROOT=/data/backups RETAIN_DAYS=7 ./infra/scripts/backup-local.sh
#   ./infra/scripts/backup-local.sh aidh materialtwin   # named
set -uo pipefail   # -e 없음: 한 서비스 실패가 나머지 백업을 막지 않게

BACKUP_ROOT="${BACKUP_ROOT:-/data/backups}"
RETAIN_DAYS="${RETAIN_DAYS:-7}"
TS="$(date +%Y%m%d-%H%M%S)"
SELF_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PARENT="$(dirname "$SELF_REPO")"
find_repo() { local n="$1"; for c in "$PARENT/$n" "$HOME/Projects/$n" "$HOME/claude/$n"; do [ -d "$c" ] && { printf '%s' "$c"; return; }; done; }
WANT="${*:-aidh signalforge mxwp materialtwin}"
want() { printf '%s ' "$WANT" | grep -qiw "$1"; }
ok() { printf '  \033[1;32m✓\033[0m %s\n' "$*"; }
bad() { printf '  \033[1;31m✗\033[0m %s\n' "$*"; }
hr() { printf '\n\033[1;36m── %s ─────────────\033[0m\n' "$*"; }

# cron 설치(멱등) — 매일 03:30 로컬 백업. 운영자 crontab 에 1줄 추가.
if [ "${1:-}" = "--install-cron" ]; then
  SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/backup-local.sh"
  LINE="30 3 * * * BACKUP_ROOT=$BACKUP_ROOT RETAIN_DAYS=$RETAIN_DAYS $SELF >> /data/backups/backup.log 2>&1"
  if crontab -l 2>/dev/null | grep -qF "$SELF"; then
    echo "· cron 이미 등록됨 (crontab -l 로 확인)"
  else
    ( crontab -l 2>/dev/null; echo "$LINE" ) | crontab -
    echo "✓ cron 등록: 매일 03:30 → $BACKUP_ROOT (로그 /data/backups/backup.log)"
  fi
  exit 0
fi

mkdir -p "$BACKUP_ROOT" || { echo "✗ $BACKUP_ROOT 생성 불가 — 경로/권한 확인"; exit 1; }
echo "cae00 로컬 백업 → $BACKUP_ROOT  (retain ${RETAIN_DAYS}일, $TS)"

# apptainer 인스턴스 안에서 pg_dump 실행 → gzip → 로컬. (env 값은 각 서비스 .env 에서)
pg_backup() {  # $1=서비스라벨 $2=인스턴스 $3=user $4=port $5=db $6=출력디렉토리
  local label="$1" inst="$2" user="$3" port="$4" db="$5" dir="$6"
  mkdir -p "$dir"
  local out="$dir/${db}-${TS}.sql.gz"
  if ! apptainer instance list 2>/dev/null | awk 'NR>1{print $1}' | grep -qx "$inst"; then
    bad "$label: 인스턴스 $inst 미동작 — skip"; return 1
  fi
  if apptainer exec "instance://$inst" pg_dump -h 127.0.0.1 -p "$port" -U "$user" -d "$db" 2>/dev/null | gzip -c > "$out"; then
    [ -s "$out" ] && { sha256sum "$out" | awk '{print $1}' > "$out.sha256"; ok "$label → $(basename "$out") ($(du -h "$out" | cut -f1))"; }  \
      || { bad "$label: 덤프 0바이트 — 실패"; rm -f "$out"; return 1; }
  else bad "$label: pg_dump 실패"; rm -f "$out"; return 1; fi
}
env_get() { sed -n "s/^$2=//p" "$1" 2>/dev/null | tail -1 | sed 's/^["'"'"']//; s/["'"'"']$//'; }

if want aidh; then
  hr "AIDataHub"
  D="$(find_repo AIDataHub)"; E="$D/deploy/apptainer/.env"
  pg_backup "aidh" "$(env_get "$E" INST_POSTGRES || echo aidh_postgres)" \
    "$(env_get "$E" POSTGRES_USER)" "$(env_get "$E" POSTGRES_PORT)" \
    "$(env_get "$E" POSTGRES_DB)" "$BACKUP_ROOT/aidh"
fi

if want signalforge; then
  hr "SignalForge"
  D="$(find_repo SignalForge)"; E="$D/.env"
  # SF 는 인스턴스명·포트가 다를 수 있어 .env 우선, 기본값 폴백
  pg_backup "signalforge" "$(env_get "$E" SF_PG_INSTANCE || echo signalforge_postgres)" \
    "$(env_get "$E" POSTGRES_USER || echo signalforge)" "$(env_get "$E" POSTGRES_PORT || echo 5434)" \
    "$(env_get "$E" POSTGRES_DB || echo signalforge)" "$BACKUP_ROOT/signalforge"
fi

if want mxwp; then
  hr "MX White Paper"
  D="$(find_repo MXWhitePaper)"; E="$D/.env"
  pg_backup "mxwp" "$(env_get "$E" MXWP_PG_INSTANCE || echo mxwp_postgres)" \
    "$(env_get "$E" POSTGRES_USER || echo mxwp)" "$(env_get "$E" POSTGRES_PORT || echo 5532)" \
    "$(env_get "$E" POSTGRES_DB || echo mxwp)" "$BACKUP_ROOT/mxwp"
fi

if want materialtwin; then
  hr "materialtwin (SQLite)"
  D="$(find_repo HEAXHub)"; APPDATA="$D/var/app_data"
  dir="$BACKUP_ROOT/materialtwin"; mkdir -p "$dir"
  if [ -d "$APPDATA" ] && [ -n "$(ls -A "$APPDATA" 2>/dev/null)" ]; then
    snap="$(mktemp -d)"
    # SQLite .backup 원자 스냅샷(쓰기 중에도 일관) — heax appdata-to-drive 와 동일 방식
    python3 - "$APPDATA" "$snap" <<'PY'
import sys, os, glob, sqlite3
src, dst = sys.argv[1], sys.argv[2]
for db in glob.glob(os.path.join(src, "**", "*.db"), recursive=True):
    rel = os.path.relpath(db, src); out = os.path.join(dst, rel)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    s = sqlite3.connect(f"file:{db}?mode=ro", uri=True); d = sqlite3.connect(out)
    s.backup(d); d.close(); s.close()
PY
    out="$dir/app_data-${TS}.tar.gz"
    if [ -n "$(ls -A "$snap" 2>/dev/null)" ]; then
      tar -czf "$out" -C "$snap" . && { sha256sum "$out" | awk '{print $1}' > "$out.sha256"; ok "materialtwin → $(basename "$out") ($(du -h "$out" | cut -f1))"; }
    else bad "materialtwin: *.db 없음 — skip"; fi
    rm -rf "$snap"
  else bad "materialtwin: var/app_data 비어있음 — skip"; fi
fi

# ── 세대 보관: 서비스별로 RETAIN_DAYS 보다 오래된 스냅샷 정리 ──
hr "세대 정리 (${RETAIN_DAYS}일 초과 삭제)"
find "$BACKUP_ROOT" -type f \( -name "*.sql.gz" -o -name "*.tar.gz" \) -mtime +"$RETAIN_DAYS" -print -delete 2>/dev/null | sed 's/^/  삭제: /' || true
find "$BACKUP_ROOT" -type f -name "*.sha256" -mtime +"$RETAIN_DAYS" -delete 2>/dev/null || true

echo; ok "백업 완료 — $BACKUP_ROOT"
du -sh "$BACKUP_ROOT" 2>/dev/null | sed 's/^/  총량: /'
