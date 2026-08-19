#!/usr/bin/env bash
# Drive 의 배포 아티팩트가 이 박스(dev)의 것보다 오래됐는지 본다 — '올렸다고 생각했는데 안 올라간' 것을 잡는다.
#
# 왜 필요한가.
#   앱을 dev 에서 다시 빌드하는 일(허브 재등록·redeploy-app)과 그걸 Drive 로 올리는 일
#   (build-all-to-drive.sh)은 서로 다른 명령이고 아무도 둘을 잇지 않는다. 그래서 dev 의
#   var/sifs/<app>.sif 는 새것인데 Drive 는 일주일 전 것인 상태가 조용히 유지된다.
#   cae00 의 '✓ checksums OK' 는 이걸 못 잡는다 — 그건 '받은 파일이 Drive 의 것과 같다'만
#   증명하지, 'Drive 가 dev 와 같다'는 말하지 않는다.
#   실제 사고(2026-08-18): materialtwin-web.sif 가 Drive 에 8/11 본으로 남아 cae00 이 옛 앱을
#   돌렸고, 새 데이터가 옛 스키마의 CHECK 에 걸려 app-data 병합이 통째로 실패했다.
#
#   ./infra/scripts/drive-drift.sh          # 전부 확인
#   ./infra/scripts/drive-drift.sh heax     # 지정한 것만 (portal | heax | koorm)
#
# 종료코드 0=일치, 1=드리프트 있음(올려야 함), 2=확인 불가.
set -uo pipefail

SELF_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PARENT="$(dirname "$SELF_REPO")"
find_repo() { local n="$1"; for c in "$PARENT/$n" "$HOME/Projects/$n" "$HOME/claude/$n"; do
  [ -d "$c" ] && { printf '%s' "$c"; return 0; }; done; return 0; }

WANT="${*:-portal heax koorm}"
want() { printf '%s\n' $WANT | grep -qx "$1"; }
command -v rclone >/dev/null 2>&1 || { echo "✗ rclone 없음 — 확인 불가"; exit 2; }

DRIFT=0
env_get() { sed -n "s/^$1=//p" "$2" 2>/dev/null | tail -1 | tr -d "\"'"; }

# ── 포털 자신 — SPA(frontend/dist)와 SIF 가 Drive 아티팩트로 cae00 에 간다.
# cae00 은 포털을 빌드하지 않는다(images-from-drive 로 받기만 한다). 그래서 프론트를 고치고
# 올리지 않으면 그 화면은 영영 안 바뀐다 — 실제로 시험계획 탭과 mermaid 테마가 9일간
# dev 에만 있었다(2026-08-19). 이 검사가 포털을 안 보고 있던 것이 그 원인이다.
if want portal; then
  R="$(env_get HWAX_DRIVE_REMOTE "$SELF_REPO/infra/.env")"; R="${R%/}"
  if [ -z "$R" ]; then echo "· HWAX_DRIVE_REMOTE 미설정 — 건너뜀"; else
    echo "── HWAX Portal ($R/latest)"
    q=0
    newest="$(find "$SELF_REPO/frontend/dist" -type f -printf '%T@\n' 2>/dev/null | sort -rn | head -1)"
    t="$(rclone lsl "$R/latest/frontend-dist.tar.gz" 2>/dev/null | awk '{print $2" "$3}')"
    if [ -n "$newest" ] && [ -n "$t" ]; then
      e="$(date -d "$t" +%s 2>/dev/null || echo 0)"
      if [ "${newest%.*}" -gt "$e" ]; then
        echo "  ✗ frontend/dist — Drive frontend-dist.tar.gz($t)보다 새것이다"; DRIFT=1; q=1
      fi
    elif [ -z "$t" ]; then
      echo "  ✗ frontend-dist.tar.gz — Drive 에 없다"; DRIFT=1; q=1
    fi
    # SIF 도 본다 — 백엔드 의존성이 바뀌면(예: python-docx 추가) dist 는 그대로인데 SIF 만
    # 달라진다. dist 만 보고 있으면 '올렸는데 500' 이 된다(실측 2026-08-19: 컨테이너에
    # python-docx 가 없어 워드 내보내기가 500 이었다).
    # searxng-fixed.sif 도 본다. images-to-drive 가 latest/ 를 sync(미러)하므로 스테이징에서
    # 빠지면 조용히 삭제된다 — 실제로 한 번 그렇게 사라졌고(2026-08-19), 이 검사가 그 파일을
    # 안 보고 있어서 "✓ 일치" 로 보였다.
    for _sif in portal nginx searxng-fixed; do
      _l="$SELF_REPO/infra/apptainer/${_sif}.sif"
      [ -f "$_l" ] || _l="$HOME/serviceApptainers/${_sif}.sif"   # dev 는 여기에 굽는다
      [ -f "$_l" ] || continue
      _ls="$(stat -c%s "$_l")"
      _ds="$(rclone lsl "$R/latest/${_sif}.sif" 2>/dev/null | awk '{print $1}')"
      if [ -z "$_ds" ]; then
        echo "  ✗ ${_sif}.sif — Drive 에 없다"; DRIFT=1; q=1
      elif [ "$_ls" != "$_ds" ]; then
        echo "  ✗ ${_sif}.sif — 로컬 $_ls ≠ Drive $_ds"; DRIFT=1; q=1
      fi
    done
    # 소스가 dist 보다 새것이면 빌드부터 안 한 것이다 — 올려도 옛 화면이 간다.
    src="$(find "$SELF_REPO/frontend/src" -type f -printf '%T@\n' 2>/dev/null | sort -rn | head -1)"
    if [ -n "$src" ] && [ -n "$newest" ] && [ "${src%.*}" -gt "${newest%.*}" ]; then
      echo "  ✗ frontend/src 가 dist 보다 새것이다 — pnpm --dir frontend build 부터 하라"; DRIFT=1; q=1
    fi
    [ "$q" = 0 ] && echo "  ✓ 일치"
  fi
fi

# ── HEAXHub: 앱 SIF 는 크기로 비교한다(내용이 다르면 크기가 거의 항상 다르고, 해시보다 싸다) ──
if want heax; then
  D="$(find_repo HEAXHub)"
  if [ -z "$D" ]; then echo "· HEAXHub 레포 없음 — 건너뜀"; else
    R="$(env_get HEAX_DRIVE_REMOTE "$D/.env")"; R="${R%/}"
    if [ -z "$R" ]; then echo "· HEAX_DRIVE_REMOTE 미설정 — 건너뜀"; else
      echo "── HEAXHub 앱 SIF ($R/latest)"
      TMP="$(mktemp)"; trap 'rm -f "$TMP"' EXIT
      rclone lsl "$R/latest/" 2>/dev/null | awk '{print $1, $NF}' > "$TMP"
      for f in "$D"/var/sifs/*.sif; do
        [ -e "$f" ] || continue
        b="$(basename "$f")"; ls_="$(stat -c%s "$f")"
        ds="$(awk -v n="$b" '$2==n{print $1}' "$TMP")"
        if [ -z "$ds" ]; then
          echo "  ✗ $b — Drive 에 없다(한 번도 안 올라갔다)"; DRIFT=1
        elif [ "$ls_" != "$ds" ]; then
          echo "  ✗ $b — 로컬 $ls_ ≠ Drive $ds"; DRIFT=1
        fi
      done
      # app-data(재료·장비 DB 등)는 tar 로 올라가므로 '가장 최근에 바뀐 DB' 와 tar 시각을 견준다.
      newest="$(find "$D/var/app_data" -name '*.db' -printf '%T@\n' 2>/dev/null | sort -rn | head -1)"
      tar_t="$(rclone lsl "${R%/dist}/app-data/latest/app-data.tar.gz" 2>/dev/null | awk '{print $2" "$3}')"
      if [ -n "$newest" ] && [ -n "$tar_t" ]; then
        tar_e="$(date -d "$tar_t" +%s 2>/dev/null || echo 0)"
        if [ "${newest%.*}" -gt "$tar_e" ]; then
          echo "  ✗ app-data — DB 가 Drive tar($tar_t)보다 새것이다"; DRIFT=1
        fi
      fi
      [ "$DRIFT" = 0 ] && echo "  ✓ 일치"
    fi
  fi
fi

# ── KooRemapper: 프론트 dist 와 솔버 바이너리가 Drive tar 보다 새것인지 ──
if want koorm; then
  D="$(find_repo KooRemapper)"
  if [ -z "$D" ]; then echo "· KooRemapper 레포 없음 — 건너뜀"; else
    R="$(env_get KOORM_DRIVE_REMOTE "$D/platform/.env")"; R="${R%/}"
    if [ -z "$R" ]; then echo "· KOORM_DRIVE_REMOTE 미설정 — 건너뜀"; else
      echo "── KooRemapper ($R/latest)"
      k=0
      for pair in "platform/frontend/dist:koorm-frontend-dist.tar.gz" "platform/backend/bin:koorm-bin.tar.gz"; do
        src="${pair%%:*}"; obj="${pair##*:}"
        newest="$(find "$D/$src" -type f -printf '%T@\n' 2>/dev/null | sort -rn | head -1)"
        t="$(rclone lsl "$R/latest/$obj" 2>/dev/null | awk '{print $2" "$3}')"
        [ -n "$newest" ] && [ -n "$t" ] || continue
        e="$(date -d "$t" +%s 2>/dev/null || echo 0)"
        if [ "${newest%.*}" -gt "$e" ]; then
          echo "  ✗ $src — Drive $obj($t)보다 새것이다"; DRIFT=1; k=1
        fi
      done
      [ "$k" = 0 ] && echo "  ✓ 일치"
    fi
  fi
fi

if [ "$DRIFT" = 1 ]; then
  echo
  echo "→ 올려야 한다:"
  echo "    ./infra/scripts/build-all-to-drive.sh            # 전체(빌드+업로드)"
  echo "    (HEAXHub 만)  cd \$HEAXHub && bash deploy/apptainer/dist-to-drive.sh"
  echo "    (app-data 만) cd \$HEAXHub && bash deploy/apptainer/appdata-to-drive.sh"
  echo "    (KooRemapper) cd \$KooRemapper && bash platform/infra/scripts/dist-to-drive.sh"
  exit 1
fi
echo "✓ Drive 가 이 박스의 아티팩트와 일치한다"
