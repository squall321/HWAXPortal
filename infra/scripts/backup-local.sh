#!/usr/bin/env bash
# 박스 로컬 데이터 백업 — /data/backups/hwax/<box>/<svc>/daily/ 아래에 매일 스냅샷 + 세대 보관.
# ⚠ 인터넷(Drive)으로 절대 나가지 않는다. 사내 데이터·시크릿은 로컬에만 둔다.
#
# 대상(기본 WANT): aidh signalforge mxwp heax kooremapper(postgres pg_dump) · materialtwin(HEAX app_data
#   SQLite .backup) · portal(sqlite 4 + jwt, 0600) · gateway(audit.jsonl) · smarttwinmcp(sqlite 2) ·
#   delib-runs · paper-index(코퍼스 색인 원장 4) · expertagents(git bundle + knowledge 작업트리) ·
#   secrets(rclone.conf·.env·키 — 0600, 이 박스 복구용). ReportArchive 는 hands-off — 대상 아님(의도).
#   소스가 이 박스에 없는 항목은 실패가 아니라 skip 이다(cae00 에 없는 dev 전용 경로들).
#
#   ./infra/scripts/backup-local.sh                 # 전부
#   BACKUP_ROOT=/data/backups RETAIN_DAYS=7 ./infra/scripts/backup-local.sh
#   ./infra/scripts/backup-local.sh aidh portal     # named
#   ./infra/scripts/backup-local.sh --install-cron  # 03:30 크론(치환형 멱등)
#
# 레이아웃(docs/data-migration/PLAN.md §4·§9): $BACKUP_ROOT/hwax/$BOX/<svc>/daily/<svc>-<box>-<TS>.{sql.gz,tar.gz}
#   <box> 층이 있어야 두 박스가 같은 03:30:01 파일명으로 충돌하지 않고, 미래 공유 /data 에서도 섞이지 않는다.
#   옛 평면 디렉터리($BACKUP_ROOT/<svc>/) 의 산출물은 첫 실행에서 새 daily/ 로 mv -n(mtime 보존 → 같은 정책으로 자동 정리).
set -uo pipefail   # -e 없음: 한 서비스 실패가 나머지 백업을 막지 않게

BACKUP_ROOT="${BACKUP_ROOT:-/data/backups}"
RETAIN_DAYS="${RETAIN_DAYS:-7}"
TS="$(date +%Y%m%d-%H%M%S)"
SELF_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PARENT="$(dirname "$SELF_REPO")"
find_repo() { local n="$1"; for c in "$PARENT/$n" "$HOME/Projects/$n" "$HOME/claude/$n"; do [ -d "$c" ] && { printf '%s' "$c"; return; }; done; }
ok() { printf '  \033[1;32m✓\033[0m %s\n' "$*"; }
# bad 는 출력만 하고 끝났다 — 그래서 백업이 한 건도 안 떠도 스크립트는 0 으로 끝나고
# 마지막 줄에 무조건 '✓ 백업 완료' 가 찍혔다. 실패를 세어 종료코드로 올린다.
bad() { printf '  \033[1;31m✗\033[0m %s\n' "$*"; FAILED=$((FAILED+1)); }
# skip 은 '이 박스에 소스가 없다' 다 — 실패가 아니다. cae00 에는 dev 전용 경로(ExpertAgents·
# /data/delib-runs 등)가 없어서, 이것을 bad 로 세면 cae00 백업이 매일 '실패' 로 끝난다(사전점검).
skip() { printf '  · %s\n' "$*"; SKIPPED=$((SKIPPED+1)); }
hr() { printf '\n\033[1;36m── %s ─────────────\033[0m\n' "$*"; }
FAILED=0; SKIPPED=0

# 값이 없으면 반드시 비0 으로 끝나야 한다 — 안 그러면 호출부의 `|| echo 기본값` 폴백이
# 통째로 죽는다. sed -n 은 '못 찾음'도 정상 종료(0)라, 예전엔 키가 없을 때 인스턴스명으로
# 빈 문자열이 넘어갔고 pg_backup 이 grep -qx "" 로 아무것도 못 찾아 매번 skip 했다.
env_get() {
  local v
  v="$(sed -n "s/^$2=//p" "$1" 2>/dev/null | tail -1 | sed 's/[[:space:]]*#.*$//; s/^["'"'"']//; s/["'"'"']$//')"
  [ -n "$v" ] || return 1
  printf '%s' "$v"
}
# 박스 이름 — services.py 의 _hwax_setting 과 같은 우선순위(os.environ > infra/.env > hostname -s).
# 두 도구가 다른 이름을 보면 백업 디렉터리가 둘로 갈린다.
BOX="${HWAX_BOX:-$(env_get "$SELF_REPO/infra/.env" HWAX_BOX 2>/dev/null || hostname -s)}"
ROOT="$BACKUP_ROOT/hwax/$BOX"
LOG_PATH="$ROOT/backup.log"

# cron 설치(치환형 멱등) — 매일 03:30. `grep -qF "$SELF"` 로 '있으면 skip' 하던 종전 방식은 줄 내용
# (로그 경로·보존)이 바뀌어도 dev·cae00 어디서도 영원히 갱신되지 않았다(사전점검). 기존 SELF 줄을 빼고 새 줄을 넣는다.
if [ "${1:-}" = "--install-cron" ]; then
  SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/backup-local.sh"
  mkdir -p "$ROOT"
  LINE="30 3 * * * BACKUP_ROOT=$BACKUP_ROOT RETAIN_DAYS=$RETAIN_DAYS $SELF >> $LOG_PATH 2>&1"
  if crontab -l 2>/dev/null | grep -qxF "$LINE"; then
    echo "· cron 이미 최신 (crontab -l 로 확인)"
  else
    ( crontab -l 2>/dev/null | grep -vF "$SELF"; echo "$LINE" ) | crontab -
    echo "✓ cron 등록/갱신: 매일 03:30 → $ROOT (로그 $LOG_PATH)"
  fi
  exit 0
fi

WANT="${*:-aidh signalforge mxwp heax kooremapper materialtwin portal gateway smarttwinmcp delib-runs paper-index expertagents secrets}"
want() { printf '%s ' "$WANT" | grep -qiw "$1"; }

mkdir -p "$ROOT" || { echo "✗ $ROOT 생성 불가 — 경로/권한 확인"; exit 1; }
echo "로컬 백업[$BOX] → $ROOT  (retain ${RETAIN_DAYS}일, $TS)"

# ── 1회성 편입: 옛 평면 디렉터리의 산출물을 새 daily/ 로 (mv -n, mtime 보존) ──
# find 범위를 새 트리로 좁히는 순간 옛 자리 파일은 영원히 안 지워진다 — 같은 정책 안으로 들여야 자동 정리된다.
for s in aidh signalforge mxwp materialtwin portal; do
  old="$BACKUP_ROOT/$s"; [ -d "$old" ] || continue
  new="$ROOT/$s/daily"; mkdir -p "$new"
  n=0
  while IFS= read -r f; do mv -n "$f" "$new/" && n=$((n+1)); done < <(find "$old" -maxdepth 1 -type f \( -name '*.sql.gz' -o -name '*.tar.gz' -o -name '*.sha256' \) 2>/dev/null)
  [ "$n" -gt 0 ] && echo "  · 편입: $old → $new ($n개)"
  rmdir "$old" 2>/dev/null || true   # pre-merge-* 같은 다른 파일이 남아 있으면 그대로 둔다
done

# apptainer 인스턴스 안에서 pg_dump 실행 → gzip → 로컬. (env 값은 각 서비스 .env 에서)
# $7(선택) 비밀번호 — heax-pg 는 127.0.0.1 도 scram 이라 없으면 매일 '0바이트 실패' 다(다른 4개는 trust).
pg_backup() {  # $1=서비스라벨 $2=인스턴스 $3=user $4=port $5=db $6=출력디렉토리 [$7=pw]
  local label="$1" inst="$2" user="$3" port="$4" db="$5" dir="$6" pw="${7:-}"
  mkdir -p "$dir"
  local out="$dir/${label}-${BOX}-${TS}.sql.gz"
  if ! apptainer instance list 2>/dev/null | awk 'NR>1{print $1}' | grep -qx "$inst"; then
    bad "$label: 인스턴스 $inst 미동작 — skip"; return 1
  fi
  if apptainer exec ${pw:+--env "PGPASSWORD=$pw"} "instance://$inst" pg_dump -h 127.0.0.1 -p "$port" -U "$user" -d "$db" 2>/dev/null | gzip -c > "$out"; then
    [ -s "$out" ] && { sha256sum "$out" | awk '{print $1}' > "$out.sha256"; ok "$label → $(basename "$out") ($(du -h "$out" | cut -f1))"; }  \
      || { bad "$label: 덤프 0바이트 — 실패"; rm -f "$out"; return 1; }
  else bad "$label: pg_dump 실패"; rm -f "$out"; return 1; fi
}
# DATABASE_URL(postgresql+psycopg://user:pw@host:port/db) 조각 — 리터럴 비밀번호를 스크립트에 박지 않기 위함
url_part() { # $1=url $2=user|pw|port|db
  case "$2" in
    user) sed -E 's#^[a-z+]+://([^:/@]+)(:[^@]*)?@.*#\1#' <<<"$1" ;;
    pw)   sed -nE 's#^[a-z+]+://[^:/@]+:([^@]*)@.*#\1#p' <<<"$1" ;;
    port) sed -nE 's#^[a-z+]+://[^@]+@[^:/]+:([0-9]+)/.*#\1#p' <<<"$1" ;;
    db)   sed -E 's#^.*/([^/?]+)(\?.*)?$#\1#' <<<"$1" ;;
  esac
}
# 시크릿을 담는 tar — umask 077 로 0600, 디렉터리 0700. sha256 도 같은 umask 안에서.
secret_tar() { # $1=출력파일 $2=스냅샷디렉토리
  ( umask 077; mkdir -p -m 700 "$(dirname "$1")"; tar -czf "$1" -C "$2" . && sha256sum "$1" | awk '{print $1}' > "$1.sha256" )
}
SQ="$SELF_REPO/infra/scripts/lib/sqlite_backup.py"

if want aidh; then
  hr "AIDataHub"
  D="$(find_repo AIDataHub)"; E="$D/deploy/apptainer/.env"
  if [ -n "$D" ]; then
    pg_backup "aidh" "$(env_get "$E" INST_POSTGRES || echo aidh_postgres)" \
      "$(env_get "$E" POSTGRES_USER)" "$(env_get "$E" POSTGRES_PORT)" \
      "$(env_get "$E" POSTGRES_DB)" "$ROOT/aidh/daily"
  else skip "aidh: 리포 없음 — 이 박스 대상 아님"; fi
fi

if want signalforge; then
  hr "SignalForge"
  D="$(find_repo SignalForge)"; E="$D/.env"
  if [ -n "$D" ]; then
    # 폴백은 sf_postgres 다 — signalforge_postgres 는 실제로 존재한 적이 없는 이름(실측).
    pg_backup "signalforge" "$(env_get "$E" SF_PG_INSTANCE || echo sf_postgres)" \
      "$(env_get "$E" POSTGRES_USER || echo signalforge)" "$(env_get "$E" POSTGRES_PORT || echo 5434)" \
      "$(env_get "$E" POSTGRES_DB || echo signalforge)" "$ROOT/signalforge/daily"
  else skip "signalforge: 리포 없음"; fi
fi

if want mxwp; then
  hr "MX White Paper"
  D="$(find_repo MXWhitePaper)"; E="$D/.env"
  if [ -n "$D" ]; then
    pg_backup "mxwp" "$(env_get "$E" MXWP_PG_INSTANCE || echo mxwp_postgres)" \
      "$(env_get "$E" POSTGRES_USER || echo mxwp)" "$(env_get "$E" POSTGRES_PORT || echo 5532)" \
      "$(env_get "$E" POSTGRES_DB || echo mxwp)" "$ROOT/mxwp/daily"
  else skip "mxwp: 리포 없음"; fi
fi

if want heax; then
  hr "HEAX Hub postgres (users·PAT·apps·secret_values — 종전 무백업)"
  D="$(find_repo HEAXHub)"; E="$D/.env"
  URL="$(env_get "$E" DATABASE_URL 2>/dev/null || true)"
  if [ -z "$D" ]; then skip "heax: 리포 없음"
  elif [ -z "$URL" ]; then bad "heax: .env 에 DATABASE_URL 없음 — 접속값을 알 수 없다"
  else
    # ⚠ secret_values 는 .env 의 SECRET_ENCRYPTION_KEY 와 짝 — 키는 secrets 묶음이 따로 뜬다(아래).
    pg_backup "heax" "heax-pg" "$(url_part "$URL" user)" "$(url_part "$URL" port)" "$(url_part "$URL" db)" \
      "$ROOT/heax/daily" "$(url_part "$URL" pw)"
  fi
fi

if want kooremapper; then
  hr "KooRemapper postgres (users·PAT·sessions — 종전 무백업)"
  D="$(find_repo KooRemapper)"; E="$D/platform/.env"
  if [ -n "$D" ]; then
    pg_backup "kooremapper" "$(env_get "$E" INST_POSTGRES || echo koorm_postgres)" \
      "$(env_get "$E" POSTGRES_USER || echo koorm)" "$(env_get "$E" POSTGRES_PORT || echo 5436)" \
      "$(env_get "$E" POSTGRES_DB || echo koorm)" "$ROOT/kooremapper/daily" "$(env_get "$E" POSTGRES_PASSWORD 2>/dev/null || true)"
  else skip "kooremapper: 리포 없음"; fi
fi

if want materialtwin; then
  hr "materialtwin (HEAX app_data SQLite 전부)"
  D="$(find_repo HEAXHub)"; APPDATA="${HEAX_APP_DATA_ROOT:-$D/var/app_data}"
  dir="$ROOT/materialtwin/daily"; mkdir -p "$dir"
  if [ -n "$D" ] && [ -d "$APPDATA" ] && [ -n "$(ls -A "$APPDATA" 2>/dev/null)" ]; then
    snap="$(mktemp -d)"
    # SQLite .backup 원자 스냅샷(쓰기 중에도 일관) — heax appdata-to-drive 와 동일 방식
    python3 - "$APPDATA" "$snap" <<'PY'
import sys, os, glob, sqlite3
src, dst = sys.argv[1], sys.argv[2]
for db in glob.glob(os.path.join(src, "**", "*.db"), recursive=True):
    if ".pre-" in os.path.basename(db):  # 죽은 .pre-merge-* 사본은 담지 않는다
        continue
    rel = os.path.relpath(db, src); out = os.path.join(dst, rel)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    s = sqlite3.connect(f"file:{db}?mode=ro", uri=True); d = sqlite3.connect(out)
    s.backup(d); d.close(); s.close()
PY
    out="$dir/materialtwin-${BOX}-${TS}.tar.gz"
    if [ -n "$(ls -A "$snap" 2>/dev/null)" ]; then
      tar -czf "$out" -C "$snap" . && { sha256sum "$out" | awk '{print $1}' > "$out.sha256"; ok "materialtwin → $(basename "$out") ($(du -h "$out" | cut -f1))"; }
    else bad "materialtwin: *.db 없음 — skip"; fi
    rm -rf "$snap"
  elif [ -z "$D" ]; then skip "materialtwin: HEAXHub 리포 없음"
  else bad "materialtwin: app_data 비어있음 — 운영 이상"; fi
fi

if want portal; then
  hr "portal (SQLite 4 + jwt — 0600)"
  D="$(find_repo HWAXPortal)"; B="$D/backend"
  snap="$(mktemp -d)"
  # users(로컬 계정·RA 연결 토큰)·conversations·token_store(PAT/jti)·agent_audit — 레지스트리 env 가 있으면 그 경로
  python3 - "$B" "$snap" "${USER_STORE_PATH:-}" "${CONV_STORE_PATH:-}" "${TOKEN_STORE_PATH:-}" "${AGENT_AUDIT_LOG_PATH:-}" <<'PY'
import sys, os, sqlite3
base, dst = sys.argv[1], sys.argv[2]
defaults = ("data/users.sqlite", "data/conversations.sqlite", "secrets/token_store.sqlite", "secrets/agent_audit.sqlite")
for rel, override in zip(defaults, sys.argv[3:7]):
    db = override or os.path.join(base, rel)
    if not os.path.exists(db):
        continue
    out = os.path.join(dst, os.path.basename(db))
    s = sqlite3.connect(f"file:{db}?mode=ro", uri=True); d = sqlite3.connect(out)
    s.backup(d); d.close(); s.close()
PY
  JWT="${JWT_KEYS_DIR:-$B/secrets/jwt}"
  [ -d "$JWT" ] && { mkdir -p "$snap/jwt"; cp -p "$JWT"/* "$snap/jwt/" 2>/dev/null; }
  if [ -n "$(ls -A "$snap" 2>/dev/null)" ]; then
    out="$ROOT/portal/daily/portal-${BOX}-${TS}.tar.gz"
    secret_tar "$out" "$snap" && ok "portal → $(basename "$out") ($(du -h "$out" | cut -f1), 0600)" || bad "portal: tar 실패"
  else bad "portal: sqlite 없음 — skip"; fi
  rm -rf "$snap"
fi

if want gateway; then
  hr "mcp-gateway audit.jsonl (감사 원장)"
  D="$(find_repo HWAXMcpGateway)"; A="${GATEWAY_AUDIT:-$D/audit.jsonl}"
  if [ -n "$D" ] && [ -f "$A" ]; then
    snap="$(mktemp -d)"; cp -p "$A" "$snap/"
    out="$ROOT/gateway/daily/gateway-${BOX}-${TS}.tar.gz"; mkdir -p "$(dirname "$out")"
    tar -czf "$out" -C "$snap" . && { sha256sum "$out" | awk '{print $1}' > "$out.sha256"; ok "gateway → $(basename "$out") ($(du -h "$out" | cut -f1))"; } || bad "gateway: tar 실패"
    rm -rf "$snap"
  else skip "gateway: audit.jsonl 없음"; fi
fi

if want smarttwinmcp; then
  hr "SmartTwinMCP (/data/SmartTwinMCP sqlite — 슬럼 호스트 로컬)"
  if [ -d /data/SmartTwinMCP ] && ls /data/SmartTwinMCP/*.db >/dev/null 2>&1; then
    snap="$(mktemp -d)"
    for db in /data/SmartTwinMCP/*.db; do python3 "$SQ" backup "$db" "$snap/$(basename "$db")" >/dev/null || bad "smarttwinmcp: $(basename "$db") .backup 실패"; done
    out="$ROOT/smarttwinmcp/daily/smarttwinmcp-${BOX}-${TS}.tar.gz"; mkdir -p "$(dirname "$out")"
    tar -czf "$out" -C "$snap" . && { sha256sum "$out" | awk '{print $1}' > "$out.sha256"; ok "smarttwinmcp → $(basename "$out") ($(du -h "$out" | cut -f1))"; }
    rm -rf "$snap"
  else skip "smarttwinmcp: /data/SmartTwinMCP 없음 — 이 박스 대상 아님"; fi
fi

if want delib-runs; then
  hr "delib-runs (심의 아카이브)"
  DR="${DELIB_ARCHIVE_ROOT:-/data/delib-runs}"
  if [ -d "$DR" ] && [ -n "$(ls -A "$DR" 2>/dev/null)" ]; then
    out="$ROOT/delib-runs/daily/delib-runs-${BOX}-${TS}.tar.gz"; mkdir -p "$(dirname "$out")"
    tar -czf "$out" -C "$DR" . && { sha256sum "$out" | awk '{print $1}' > "$out.sha256"; ok "delib-runs → $(basename "$out") ($(du -h "$out" | cut -f1))"; } || bad "delib-runs: tar 실패"
  else skip "delib-runs: $DR 없음 — 이 박스 대상 아님"; fi
fi

if want paper-index; then
  hr "paper-index (코퍼스 색인 원장 — 잃으면 144G 재색인)"
  PI=/data/paper_patent_corpus/_index
  if [ -f "$PI/manifest.json" ]; then
    snap="$(mktemp -d)"
    for f in "$PI/manifest.json" "$PI/_verdicts/discarded.jsonl" /data/paper_patent_corpus/knowledge_grounding/agent_papers.json; do [ -f "$f" ] && { mkdir -p "$snap/$(dirname "${f#/data/paper_patent_corpus/}")"; cp -p "$f" "$snap/${f#/data/paper_patent_corpus/}"; }; done
    [ -d "$PI/proposals" ] && { mkdir -p "$snap/_index"; cp -rp "$PI/proposals" "$snap/_index/"; }
    out="$ROOT/paper-index/daily/paper-index-${BOX}-${TS}.tar.gz"; mkdir -p "$(dirname "$out")"
    tar -czf "$out" -C "$snap" . && { sha256sum "$out" | awk '{print $1}' > "$out.sha256"; ok "paper-index → $(basename "$out") ($(du -h "$out" | cut -f1))"; } || bad "paper-index: tar 실패"
    rm -rf "$snap"
  else skip "paper-index: $PI/manifest.json 없음 — 이 박스 대상 아님"; fi
fi

if want expertagents; then
  hr "ExpertAgents/knowledge (remote 없는 git — 이 박스 유일본)"
  EA="$(find_repo ExpertAgents)"
  if [ -n "$EA" ] && [ -d "$EA/.git" ]; then
    snap="$(mktemp -d)"
    # bundle 은 커밋만 담는다 — 미커밋 카드·facts 는 작업트리 tar 로 함께(사전점검: 미커밋 27건)
    git -C "$EA" bundle create "$snap/expertagents.bundle" --all >/dev/null 2>&1 || bad "expertagents: bundle 실패"
    [ -d "$EA/knowledge" ] && tar -czf "$snap/knowledge-worktree.tar.gz" -C "$EA" --exclude=.git --exclude='.env*' knowledge 2>/dev/null
    out="$ROOT/expertagents/daily/expertagents-${BOX}-${TS}.tar.gz"; mkdir -p "$(dirname "$out")"
    tar -czf "$out" -C "$snap" . && { sha256sum "$out" | awk '{print $1}' > "$out.sha256"; ok "expertagents → $(basename "$out") ($(du -h "$out" | cut -f1))"; } || bad "expertagents: tar 실패"
    rm -rf "$snap"
  else skip "expertagents: 리포 없음 — 이 박스 대상 아님"; fi
fi

if want secrets; then
  hr "secrets (이 박스 복구용 — 0600, Drive 로 절대 안 나감)"
  snap="$(mktemp -d)"; chmod 700 "$snap"
  put() { [ -e "$1" ] && { mkdir -p "$snap/$2"; cp -rp "$1" "$snap/$2/"; }; }
  put "$HOME/.config/rclone/rclone.conf" rclone
  put "$SELF_REPO/infra/.env" portal; put "$SELF_REPO/backend/.env" portal
  D="$(find_repo HEAXHub)";        [ -n "$D" ] && { put "$D/.env" heax; put "${HEAX_APP_DATA_ROOT:-$D/var/app_data}/hwax_risk/cred.key" heax/hwax_risk; }
  D="$(find_repo KooRemapper)";    [ -n "$D" ] && put "$D/platform/.env" kooremapper
  D="$(find_repo HWAXMcpGateway)"; [ -n "$D" ] && { put "$D/gateway_config.json" gateway; put "$D/provision.env" gateway; }
  D="$(find_repo HWAXAgentServer)";[ -n "$D" ] && { put "$D/.env" agent-server; put "$D/mcp_servers.json" agent-server; }
  if [ -n "$(ls -A "$snap" 2>/dev/null)" ]; then
    out="$ROOT/secrets/daily/secrets-${BOX}-${TS}.tar.gz"
    secret_tar "$out" "$snap" && ok "secrets → $(basename "$out") ($(du -h "$out" | cut -f1), 0600)" || bad "secrets: tar 실패"
  else skip "secrets: 담을 것 없음"; fi
  rm -rf "$snap"
fi

# ── 세대 보관: 우리 트리(hwax/$BOX/*/daily)만 정리한다. $BACKUP_ROOT 전체를 훑던 종전 방식은
#    운영자가 손으로 둔 아카이브·무관 잔재(cluster_setup·dpkg.*)까지 지웠다(사전점검).
#    예외: AIDH merge-from-drive.sh:46 이 update-all 마다 $BACKUP_ROOT/aidh/pre-merge-*.sql.gz(4.4G)를 계속 쓴다 — 그것만 같이 정리.
hr "세대 정리 (${RETAIN_DAYS}일 초과 삭제 — $ROOT/*/daily + aidh pre-merge)"
for d in "$ROOT"/*/daily; do
  [ -d "$d" ] || continue
  find "$d" -maxdepth 1 -type f \( -name "*.sql.gz" -o -name "*.tar.gz" \) -mtime +"$RETAIN_DAYS" -print -delete 2>/dev/null | sed 's/^/  삭제: /' || true
  find "$d" -maxdepth 1 -type f -name "*.sha256" -mtime +"$RETAIN_DAYS" -delete 2>/dev/null || true
done
[ -d "$BACKUP_ROOT/aidh" ] && find "$BACKUP_ROOT/aidh" -maxdepth 1 -type f -name 'pre-merge-*.sql.gz' -mtime +"$RETAIN_DAYS" -print -delete 2>/dev/null | sed 's/^/  삭제: /' || true

echo
du -sh "$ROOT" 2>/dev/null | sed 's/^/  총량: /'
[ "$SKIPPED" -gt 0 ] && echo "  · skip ${SKIPPED}건(이 박스에 없는 소스 — 정상)"
if [ "$FAILED" -eq 0 ]; then
  ok "백업 완료 — $ROOT"
else
  printf '  \033[1;31m✗\033[0m 백업 %s건 실패 — 위 ✗ 줄을 확인하라 (%s)\n' "$FAILED" "$ROOT"
  exit 1
fi
