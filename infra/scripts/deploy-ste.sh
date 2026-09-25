#!/usr/bin/env bash
# cae00 에서 ste 웹(ste 헤드노드, 에어갭) 코드 갱신 배포를 트리거한다 — 메커니즘은 STE 소유
#
#   infra/scripts/deploy-ste.sh                 # STE 배포(저장소 없으면 Drive 에서 받아와 클론까지)
#   STE_REPO=~/SmartTwinExplorer deploy-ste.sh   # STE 레포 위치 지정(기본 ~/SmartTwinExplorer)
#   STE_DRIVE_REMOTE=MyDrive: STE_STAGING_PATH=SmartTwinExplorer/staging deploy-ste.sh  # 리모트/경로 지정
#
# **전송 방식이 경로를 가른다** — ste 리포의 `deploy/transport.env` 가 정본이다.
#
#   TRANSPORT_MODE=direct   : 같은 박스에서 ssh 로 닿는 ste 헤드(dev 의 libvirt VM).
#                             Drive 를 거치지 않고 리포에서 **직접** rsync 한다. 싸고 멱등해서
#                             update-all 이 매번 불러도 된다.
#   TRANSPORT_MODE=teleport : 에어갭 운영 클러스터. Drive 스테이징 왕복 + 살아 있는 Teleport
#                             세션이 필요하다. 자동 호출(--if-stale)에서는 **공용 게이트**(사람 호출 ∧
#                             신선도 ∧ 세션, infra/scripts/lib/deploy-gate.sh)를 통과할 때만 돈다 —
#                             routine·크론에서는 배포하지 않고, `update-all --with-ste` 나 STE_DEPLOY=1 이면 강제.
#
# 즉 "의도적·비정기" 라는 원칙은 **운영 클러스터에만** 적용한다. dev VM 을 최신으로 두는 것은
# 위험이 없고, 오히려 낡은 채로 두면 "소스에는 있는데 박스에는 없다" 가 생긴다 —
# 실제로 그 때문에 포털→ste 자격 중계가 조용히 죽어 있었다(2026-09-23, docs/one-token D-12).
#
# `--if-stale` 을 주면 원격과 리포를 대조해 **다를 때만** 배포한다(update-all 이 이걸 쓴다).
# 저장소가 없으면(최초) Drive 스테이징 번들에서 rclone 으로 받아 git clone 한다 — 단 Teleport 접속
# 설정(transport.env)만은 클러스터 비밀이라 자동 못 채우고, 한 번 채우라 안내하고 멈춘다(그 뒤 재실행).
set -euo pipefail

SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

ok()  { printf '  \033[1;32m✓\033[0m %s\n' "$*"; }
bad() { printf '  \033[1;31m✗\033[0m %s\n' "$*" >&2; }
die() { bad "$*"; exit 1; }

# 리포 위치 — 형제 리포가 먼저다(박스마다 루트가 다르므로 절대경로를 박지 않는다).
# dev 는 ~/claude/SmartTwinExplorer, cae00 은 ~/Projects/SmartTwinExplorer 이고 둘 다 `../` 로 닿는다.
if [ -z "${STE_REPO:-}" ]; then
  if [ -d "$SELF/../SmartTwinExplorer/deploy" ]; then
    STE_REPO="$(cd "$SELF/../SmartTwinExplorer" && pwd)"
  else
    STE_REPO="$HOME/SmartTwinExplorer"
  fi
fi
STAGING="${STE_STAGING:-$HOME/ste-staging}"
DEPLOY="$STE_REPO/deploy/refresh-code.sh"
SKIP_PULL=""
IF_STALE=0
ARGS=()
for a in "$@"; do
  case "$a" in
    --if-stale) IF_STALE=1 ;;
    *) ARGS+=("$a") ;;
  esac
done
set -- ${ARGS[@]+"${ARGS[@]}"}

# 전송 방식을 먼저 읽는다 — 이것이 경로와 게이팅을 가른다.
TRANSPORT_MODE=""
_TENV="$STE_REPO/deploy/transport.env"
# ⚠ `[ -f x ] && VAR=...` 로 쓰면 안 된다 — `set -e` 아래서 파일이 없을 때 그 && 리스트가
#   0 이 아닌 상태를 돌려주고 스크립트가 **그 자리에서 죽는다**(고전적 함정).
if [ -f "$_TENV" ]; then
  TRANSPORT_MODE="$(sed -n 's/^[[:space:]]*TRANSPORT_MODE=[[:space:]]*//p' "$_TENV" | head -1 | tr -d '"'"'"' \r')"
fi

# ── 자동 호출(--if-stale)은 **있는 것만 최신화한다** ─────────────────────────
# 리포가 없거나 접속 설정이 없으면 한 줄 말하고 끝낸다. 여기서 Drive 부트스트랩으로 넘어가면
# update-all 한 번이 22MB 다운로드와 git clone 을 발화시킨다 — "routine 이 실배포를 발화" 의
# 또 다른 얼굴이다(실측으로 잡았다: STE_REPO 를 없는 경로로 두고 --if-stale 을 주면 받기 시작했다).
if [ "$IF_STALE" = 1 ]; then
  if [ ! -x "$DEPLOY" ]; then
    printf '  · ste 리포가 이 박스에 없다(%s) — 건너뛴다. 최초 반입은 infra/scripts/deploy-ste.sh 를 직접 부른다.\n' "$STE_REPO"
    exit 0
  fi
  if [ -z "$TRANSPORT_MODE" ]; then
    printf '  · ste 접속 설정이 없다(%s) — 건너뛴다. 채우면 그때부터 자동 최신화된다.\n' "$_TENV"
    exit 0
  fi
fi

# ── direct(같은 박스에서 ssh 로 닿는 ste 헤드) ────────────────────────────────
# Drive 를 거치지 않는다. 리포가 곧 정본이라 rsync 한 번이면 끝이고, 그래서 멱등하다.
if [ "$TRANSPORT_MODE" = direct ]; then
  [ -x "$STE_REPO/deploy/deploy-backend.sh" ] || die "ste 리포에 deploy-backend.sh 가 없다: $STE_REPO"

  # `--if-stale` — 원격과 리포가 같으면 아무것도 하지 않는다. rsync 자체는 멱등이지만
  # **재기동은 아니다**. 매번 재기동하면 돌던 잡의 연결이 끊기고, update-all 이 자주 도는 박스에서
  # 그것만으로 사용자에게 장애처럼 보인다. 그래서 "다를 때만" 을 여기서 판정한다.
  if [ "$IF_STALE" = 1 ]; then
    _man() {  # 배포 대상 트리의 내용 지문. 경로+sha256 만 본다(시각·권한은 무시 — 재배포마다 바뀐다).
      ( cd "$1" 2>/dev/null && find . -type f \
          ! -name '*.pyc' ! -path './__pycache__/*' ! -path '*/__pycache__/*' ! -path './.pytest_cache/*' \
          -exec sha256sum {} + 2>/dev/null | LC_ALL=C sort -k2 ) | sha256sum | cut -d' ' -f1
    }
    # ⚠ backend/src·web 만 보면 **MCP 서버(backend/mcp_server)와 앱 정의(apps)가 낡아도 "이미 최신"** 이다
    #   (2026-09-24 적대 검토). 배포가 실제로 나르는 트리 넷을 전부 본다.
    _lman="$(for d in backend/src backend/mcp_server apps frontend/dist; do _man "$STE_REPO/$d"; done | tr '\n' ' ')"
    # 원격은 같은 계산을 원격 셸에서 한다 — 트리를 끌어오지 않으려고.
    _rman="$(cd "$STE_REPO" && . deploy/lib/transport.sh >/dev/null 2>&1 && \
      $SSH "$TARGET" 'for d in /opt/ste/backend/src /opt/ste/backend/mcp_server /opt/ste/apps /opt/ste/web; do
          if [ -d "$d" ]; then (cd "$d" && find . -type f ! -name "*.pyc" ! -path "*/__pycache__/*" \
             -exec sha256sum {} + 2>/dev/null | LC_ALL=C sort -k2) | sha256sum | cut -d" " -f1
          else echo "-"; fi; done' 2>/dev/null | tr '\n' ' ' || true)"
    # ⚠ 원격 지문을 못 읽었으면(접속 실패·빈 값) **같다고 보지 않는다.** 모름을 같음으로
    #   읽으면 낡은 박스를 영원히 건너뛰면서 초록을 낸다 — 이 리포가 반복해서 당한 그 모양이다.
    if [ -n "$_rman" ] && [ "$(printf '%s' "$_rman" | wc -w)" = 4 ] && [ "$_rman" = "$_lman" ]; then
      ok "ste 이미 최신 — 배포·재기동 생략 (backend/src·mcp_server·apps·web 지문 일치)"
      STE_SKIPPED=1
    fi
  fi

  if [ "${STE_SKIPPED:-0}" != 1 ]; then
    printf '\033[1;36m▶ ste 코드 갱신 (direct: 리포 → 헤드, Drive 경유 없음) — %s\033[0m\n' "$STE_REPO"
    ( cd "$STE_REPO" && bash deploy/deploy-backend.sh ) || die "ste 백엔드 배포 실패"
    # 프론트는 dist 가 있으면 그것을 보낸다. 빌드는 dev 에서만 되므로(cae00 은 npm 이 막혔다)
    # 없으면 **조용히 넘기지 않고** 말한다 — 프론트가 낡으면 화면만 옛것이라 원인이 안 보인다.
    if [ -f "$STE_REPO/frontend/dist/index.html" ]; then
      ( cd "$STE_REPO" && bash deploy/deploy-frontend.sh --no-build ) || die "ste 프론트 전송 실패"
    else
      bad "ste frontend/dist 가 없다 — 프론트는 옛 채로 남는다 (dev 에서 deploy/deploy-frontend.sh 로 빌드)"
    fi
  fi

  # 코드가 새것이어도 **시크릿이 없으면 자격 중계는 404** 다. 배포 경로가 둘이라
  # 이 일을 refresh-code.sh 안에만 두면 이 경로에서 빠진다 — 그래서 떼어낸 것을 부른다.
  if [ -x "$STE_REPO/deploy/sync-sso-secret.sh" ]; then
    PORTAL_ENV="$SELF/infra/.env" bash "$STE_REPO/deploy/sync-sso-secret.sh" \
      || bad "STE_SSO_SECRET 정합 실패 — 포털 로그인으로 ste 가 안 열린다(위 사유 참조)"
  else
    bad "ste 리포에 sync-sso-secret.sh 가 없다 — 자격 중계 시크릿이 안 맞을 수 있다"
  fi
else

# ── STE 저장소가 없으면 Drive 스테이징 번들에서 부트스트랩 ──────────────────────
# ste 웹은 에어갭(ste 헤드노드)이라 코드가 github 이 아니라 dev→Drive 번들로 온다. 저장소가
# 통째로 없는 cae00 에서도 이 스크립트 하나로 받아오게 한다(dev 가 pack-staging+push-to-drive 선행).
if [ ! -x "$DEPLOY" ]; then
  printf '\033[1;36m▶ STE 저장소 없음(%s) — Drive 스테이징에서 부트스트랩\033[0m\n' "$STE_REPO"
  RCLONE="$(command -v rclone || echo "$SELF/infra/bin/rclone")"
  [ -x "$RCLONE" ] || die "rclone 이 없다 (HWAXPortal infra/bin/rclone 또는 PATH)"
  # 리모트: STE_DRIVE_REMOTE 우선, 없으면 pull-from-drive 와 같은 규칙(ApptainerImages: → 첫 리모트)
  REMOTE="${STE_DRIVE_REMOTE:-}"
  [ -z "$REMOTE" ] && "$RCLONE" listremotes 2>/dev/null | grep -qx 'ApptainerImages:' && REMOTE="ApptainerImages:"
  [ -z "$REMOTE" ] && REMOTE="$("$RCLONE" listremotes 2>/dev/null | head -1)"
  [ -n "$REMOTE" ] || die "rclone remote 가 없다 — STE_DRIVE_REMOTE 로 지정하라"
  STE_PATH="${STE_STAGING_PATH:-SmartTwinExplorer/staging}"
  echo "  Drive: ${REMOTE}${STE_PATH} → $STAGING"
  "$RCLONE" copy "${REMOTE}${STE_PATH}" "$STAGING" --progress \
    || die "스테이징 수신 실패 — dev 가 push-to-drive 했는지, 리모트/경로가 맞는지 확인"
  [ -f "$STAGING/ste-code.bundle" ] || die "스테이징에 ste-code.bundle 이 없다: $STAGING"
  ( cd "$STAGING" && sha256sum -c SHA256SUMS >/dev/null ) || die "무결성(sha256) 실패 — 깨진 파일 재수신(런북 §9-B)"
  ok "스테이징 수신·검증"
  mkdir -p "$STE_REPO"
  git clone "$STAGING/ste-code.bundle" "$STE_REPO" >/dev/null 2>&1 || die "번들 클론 실패: $STAGING/ste-code.bundle"
  ok "STE 저장소 클론 → $STE_REPO"
  # 접속 설정 — Teleport 값은 클러스터 비밀이라 자동으로 못 채운다. 예시 복사 후 채우라 안내하고 멈춘다.
  if [ ! -f "$STE_REPO/deploy/transport.env" ]; then
    cp "$STAGING/transport.env.example" "$STE_REPO/deploy/transport.env" 2>/dev/null \
      || cp "$STE_REPO/deploy/transport.env.example" "$STE_REPO/deploy/transport.env" 2>/dev/null || true
    die "접속 설정을 채워라: $STE_REPO/deploy/transport.env
    teleport 블록(REMOTE_USER·TP_PROXY·TP_CLUSTER·HEAD_NODE)을 채운 뒤 이 스크립트를 다시 실행하면 배포까지 이어진다(런북 §4)."
  fi
  SKIP_PULL="--skip-pull"   # 방금 받은 스테이징을 재사용(중복 pull 방지)
  ok "부트스트랩 완료 — 배포로 진행"
fi

  # ── 운영 클러스터 게이트 — 명시 플래그 하나가 아니라 **세 신호**(사람 호출 ∧ 신선도 ∧ 세션) ──────
  # 종전 `STE_DEPLOY=1` 게이트는 존재하지 않는 크론을 막느라 "update-all 한 번에 셋업" 을 깼다
  # (리포·가이드에 update-all 크론이 없다 — 2026-09-24 조사). 규칙은 공용 lib 에 있고(ste 가 첫 사용처,
  # 새 옵션은 이름만 더한다), 여기서는 ste 의 두 명령만 준다.
  #   신선도: Drive 의 ste-code.commit(pack-staging 이 쓴다) ≠ 헤드의 /opt/ste/.deployed-commit(deploy-backend 가 쓴다)
  #           → 0(바뀜) / 1(같음) / 2(모름 — 어느 한쪽을 못 읽음. 모름은 같음이 아니다)
  #   전제  : Teleport 세션이 살아 있어 헤드에 닿는다(tr_run 'true', ConnectTimeout 10)
  # 사람이 직접 부르면(--if-stale 없음) 게이트 없이 종전대로 간다.
  if [ "$IF_STALE" = 1 ]; then
    . "$SELF/infra/scripts/lib/deploy-gate.sh"
    _fresh_cmd="$(cat <<'EOF'
set -u
RCLONE="$(command -v rclone || echo "$SELF/infra/bin/rclone")"; [ -x "$RCLONE" ] || exit 2
REMOTE="${STE_DRIVE_REMOTE:-}"
[ -z "$REMOTE" ] && "$RCLONE" listremotes 2>/dev/null | grep -qx 'ApptainerImages:' && REMOTE="ApptainerImages:"
[ -z "$REMOTE" ] && REMOTE="$("$RCLONE" listremotes 2>/dev/null | head -1)"
[ -n "$REMOTE" ] || exit 2
drive="$("$RCLONE" cat "${REMOTE}${STE_STAGING_PATH:-SmartTwinExplorer/staging}/ste-code.commit" 2>/dev/null | tr -d '[:space:]')"
[ -n "$drive" ] || exit 2
head="$(cd "$STE_REPO" && . deploy/lib/transport.sh >/dev/null 2>&1 && tr_run 'cat /opt/ste/.deployed-commit 2>/dev/null' 2>/dev/null | tr -d '[:space:]')"
[ -n "$head" ] || exit 2
[ "$drive" != "$head" ]
EOF
)"
    _precond_cmd='cd "$STE_REPO" && . deploy/lib/transport.sh >/dev/null 2>&1 && tr_run true >/dev/null 2>&1'
    if SELF="$SELF" STE_REPO="$STE_REPO" hwax_gate ste --fresh "$_fresh_cmd" --precond "$_precond_cmd"; then
      [ -n "${HWAX_GATE_REASON:-}" ] && printf '  · %s\n' "$HWAX_GATE_REASON"
    else
      printf '  · %s\n' "$HWAX_GATE_REASON"
      printf '    지금 돌리려면: ./infra/scripts/update-all.sh --with-ste   또는   STE_DEPLOY=1 infra/scripts/deploy-ste.sh\n'
      exit 0
    fi
  fi
  printf '\033[1;36m▶ STE 코드 갱신 배포 트리거 — %s\033[0m\n' "$STE_REPO"
  STE_STAGING="$STAGING" "$DEPLOY" $SKIP_PULL "$@" || die "STE 배포 실패 — 위 로그와 런북 §9(실패 대처) 참조"
fi

# 포털 프록시 경유로 살아났는지 확인
HTTP_PORT=8088
[ -f "$SELF/infra/.env" ] && HTTP_PORT="$(sed -n 's/^HTTP_PORT=\([0-9]*\).*/\1/p' "$SELF/infra/.env" | head -1)"
HTTP_PORT="${HTTP_PORT:-8088}"
# 상태코드만 보면 안 된다 — /ste/ 라우트 미반영 시 포털 catch-all 이 SPA(index.html)를 200 으로
# 돌려줘 배포 성공으로 오판한다(update-all.sh 가 실측·정리한 문제). 본문으로 백엔드 응답을 확인한다.
resp="$(curl -sk -m 5 -w '\n%{http_code}' "http://127.0.0.1:$HTTP_PORT/ste/api/health" 2>/dev/null || true)"
code="${resp##*$'\n'}"; body="${resp%$'\n'*}"
if printf '%s' "$body" | grep -q 'smart-twin-explorer'; then
  ok "포털 프록시 :$HTTP_PORT/ste/api/health → 백엔드 응답 확인"
else
  bad "포털 프록시 :$HTTP_PORT/ste/api/health → [$code] 백엔드 응답 아님 (포털 SPA 폴백/미도달 — nginx /ste/ 라우트·ste-tunnel 확인)"
fi
