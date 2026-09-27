#!/usr/bin/env bash
# ste 진단 — 이 박스에서 ste 가 "다 서 있는지" 를 **한 화면**에 낸다 (읽기 전용, 아무것도 고치지 않는다)
#
#   ./infra/scripts/ste-doctor.sh            # 사람용 한 화면
#   ./infra/scripts/ste-doctor.sh --report   # 기계용 JSON 한 줄(S0 실측을 context-notes 에 붙일 때)
#
# 왜 — cae00 에서 ste 가 죽어 있어도 초록으로 가려지던 자리가 넷이었다(2026-09-24 적대 검토):
# 터널 15812 부재·시크릿 불일치·게이트웨이 ste DOWN·권한 정책 미적재. update-all §6 이 이제 그것을
# 빨강으로 내지만, 사람이 "지금 무엇이 문제인가" 를 한 번에 보려면 이 스크립트다. 항목마다 **어떻게
# 쟀는지**(주소·코드)를 같이 찍어 짐작이 끼어들 자리를 없앤다.
#
# 종료코드: 0 = 전부 초록 · 1 = 빨강 있음 · 2 = ste 를 안 쓰는 박스(라우트·접속설정 없음)
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPORT=0; [ "${1:-}" = "--report" ] && REPORT=1
RED=0; declare -A R

ok()   { R["$1"]="ok:$2";   [ "$REPORT" = 1 ] || printf '  \033[1;32m✓\033[0m %-14s %s\n' "$1" "$2"; }
bad()  { R["$1"]="fail:$2"; RED=1; [ "$REPORT" = 1 ] || printf '  \033[1;31m✗\033[0m %-14s %s\n' "$1" "$2"; }
warn() { R["$1"]="warn:$2"; [ "$REPORT" = 1 ] || printf '  \033[1;33m⚠\033[0m %-14s %s\n' "$1" "$2"; }
code() { curl -s -o /dev/null -w '%{http_code}' -m "${2:-4}" "$1" 2>/dev/null || echo 000; }
# bash 가 읽는 것과 같게 — 인라인 주석(공백 뒤 #)·양끝 공백·따옴표·CR 을 벗긴다(`COOKIE_SECURE=true   # …` 가 `true#…` 로 읽혀 빨강이던 것).
# LC_ALL=C — UTF-8 로케일의 GNU sed 가 한글 주석 줄에서 `.*$` 를 못 맞추는 경우가 있다(update-all _ra_envv 와 같은 이유).
envv() { sed -n -E "s/^[[:space:]]*(export[[:space:]]+)?$1=[[:space:]]*//p" "$2" 2>/dev/null | tail -1 | LC_ALL=C sed -E 's/[[:space:]]+#.*$//; s/^[[:space:]]+//; s/[[:space:]]+$//' | LC_ALL=C tr -d '"'"'"'\r'; }

HTTP_PORT="$(envv HTTP_PORT "$ROOT/infra/.env")"; HTTP_PORT="${HTTP_PORT:-8088}"
SECRET="$(envv STE_SSO_SECRET "$ROOT/infra/.env")"

# ── 1) 이 박스가 ste 를 쓰는가 — 라우트(local 우선)와 접속 설정 ─────────────────────────
ROUTE=""; SRC=""
for f in "$ROOT/backend/config/routes.local.env" "$ROOT/backend/config/routes.env"; do
  [ -f "$f" ] || continue
  if grep -qE '^[[:space:]]*ste=' "$f"; then ROUTE="$(envv ste "$f")"; SRC="$(basename "$f")"; break; fi
done
TENV=""; for c in "$ROOT/../SmartTwinExplorer/deploy/transport.env" "$HOME/SmartTwinExplorer/deploy/transport.env"; do [ -f "$c" ] && { TENV="$c"; break; }; done
MODE="$([ -n "$TENV" ] && envv TRANSPORT_MODE "$TENV" || echo "")"
if [ -z "$ROUTE" ] && [ -z "$TENV" ]; then
  [ "$REPORT" = 1 ] && echo '{"ste":"unused"}' || echo "· ste 를 안 쓰는 박스다(라우트도 접속 설정도 없다)"
  exit 2
fi
[ -n "$ROUTE" ] && ok route "$SRC ste=$ROUTE" || bad route "ste= 라우트 없음(routes.local.env) — 포털 /ste 와 게이트웨이 ste 백엔드가 안 생긴다$([ "$MODE" = teleport ] && echo ' (update-all 1d 가 적어 준다)')"
[ -n "$TENV" ] && ok transport "$MODE ($TENV)" || warn transport "SmartTwinExplorer/deploy/transport.env 없음 — 이 박스는 배포하지 않는다(프록시만)"
ORIGIN="$(printf '%s' "$ROUTE" | sed -n 's|^\(https\?://[^/]*\).*|\1|p')"
HOST="$(printf '%s' "$ORIGIN" | sed 's|^https\?://||; s|:[0-9]*$||')"

# ── 2) 헤드 도달 — 웹(15810)과 MCP(15812) — 라우트가 루프백이면 터널 경유다 ────────────────
if [ -n "$ORIGIN" ]; then
  h="$(code "$ORIGIN/api/health")"
  [ "$h" = 200 ] && ok web "$ORIGIN/api/health → 200$([ "$HOST" = 127.0.0.1 ] && echo ' (터널 경유)')" \
                 || bad web "$ORIGIN/api/health → $h$([ "$HOST" = 127.0.0.1 ] && echo ' — ste-tunnel 확인(systemctl --user status ste-tunnel)')"
  MCP_URL="${STE_MCP_URL:-http://$HOST:15812/mcp}"
  m="$(code "$MCP_URL")"
  case "$m" in
    200|405|406) ok mcp "$MCP_URL → $m (살아 있음)" ;;
    *) bad mcp "$MCP_URL → $m — ste 도구 8종이 안 뜨는 원인$([ "$HOST" = 127.0.0.1 ] && echo '. ste-tunnel 의 -L 에 15812 가 있나(install-ste-tunnel.sh --check)')" ;;
  esac
fi
if [ "$MODE" = teleport ]; then
  if [ -f "$HOME/.config/systemd/user/ste-tunnel.service" ]; then
    ok tunnel-unit "$(systemctl --user is-active ste-tunnel 2>/dev/null || echo unknown) (리포 유닛)"
  else
    warn tunnel-unit "리포 유닛이 없다 — 손으로 만든 터널이거나 미설치(install-ste-tunnel.sh)"
  fi
  # Teleport 세션 — tsh 가 있으면 잔여 시간을 읽는다(형식이 버전마다 달라 못 읽으면 '모름')
  if command -v tsh >/dev/null 2>&1; then
    TH="$(envv TELEPORT_HOME "$TENV")"
    # 먼저 JSON(최근 tsh) — valid_until 이 정확하다. 없으면 텍스트 grep. 그래도 못 읽으면 **원문 첫 줄들**을 보여 다음에 형식을 맞춘다
    # (cae00 실측 2026-09-27: 터널은 살았는데 이 행이 '못 읽었다' 만 말해 판정 근거가 없었다).
    st="$( ${TH:+TELEPORT_HOME=$TH} tsh status -f json 2>/dev/null | python3 -c 'import json,sys
d=json.load(sys.stdin); a=d.get("active") or d
v=a.get("valid_until") or a.get("expires") or ""
print(("valid until " + v) if v else "")' 2>/dev/null)"
    [ -n "$st" ] || st="$( ${TH:+TELEPORT_HOME=$TH} tsh status 2>/dev/null | grep -iE 'valid until|expires' | head -1)"
    if [ -n "$st" ]; then ok teleport "$st"
    else
      raw="$( ${TH:+TELEPORT_HOME=$TH} tsh status 2>&1 | grep -v '^[[:space:]]*$' | head -3 | tr '\n' '|' | cut -c1-160)"
      warn teleport "tsh status 에서 만료 시각을 못 읽었다 — 세션이 없거나 형식이 다르다. 원문: ${raw:-(출력 없음 — tsh 없거나 로그인 안 됨)}"
    fi
  else
    warn teleport "tsh 없음 — 세션 잔여 시간을 여기서 못 본다(전제 검사는 배포 시 tr_run true 로 한다)"
  fi
fi

# ── 3) 자격 중계 — 시크릿이 **같은 값**인가(verify, 실제 값은 루프백으로만) ────────────────
if [ -z "$SECRET" ]; then bad sso-secret "포털 infra/.env 에 STE_SSO_SECRET 이 없다 — start.sh 가 만든다"
else
  # 시크릿은 argv 로 넘기지 않는다(ps 에 보인다) — curl 설정을 stdin 으로 준다(-K -).
  # 401 은 둘이다 — 핸들러가 "시크릿이 다르다" 고 낸 401 과, 그 경로를 모르는 **옛 판**의 인증 미들웨어가 낸 401(WWW-Authenticate 헤더).
  # update-all §6 이 헤더로 가른다 — doctor 만 "다르다" 로 읽으면 처방(FORCE_SSO_SECRET)이 틀린다(cae00 실측 2026-09-27).
  hdr="$(curl -s -D - -o /dev/null -m 4 -X POST -H 'X-Heax-Gateway-Secret: probe-not-a-secret' -H 'X-Heax-User-Email: probe@invalid' "http://127.0.0.1:$HTTP_PORT/ste/api/auth/sso" 2>/dev/null || true)"
  if printf '%s' "$hdr" | grep -qi '^www-authenticate:'; then v=mw; else
    v="$(printf 'header = "X-Heax-Gateway-Secret: %s"\n' "$SECRET" | curl -s -o /dev/null -w '%{http_code}' -m 4 -X POST -K - "http://127.0.0.1:$HTTP_PORT/ste/api/auth/sso/verify" 2>/dev/null || echo 000)"
  fi
  case "$v" in
    mw)  bad sso-secret "헤드에 **옛 판**이 떠 있다(/api/auth/sso 를 미들웨어가 401) — 시크릿 비교 이전 문제. 코드 갱신부터: ./infra/scripts/update-all.sh --with-ste 또는 infra/scripts/deploy-ste.sh" ;;
    204) ok sso-secret "양쪽 같은 값 (verify 204 via :$HTTP_PORT)" ;;
    401) bad sso-secret "양쪽 **다르다** (verify 401) — FORCE_SSO_SECRET=1 SmartTwinExplorer/deploy/sync-sso-secret.sh" ;;
    404) warn sso-secret "헤드 판이 verify 를 모른다(404) — 코드 갱신 뒤 다시(옛 판이거나 시크릿 미설정)" ;;
    000) bad sso-secret "포털 프록시 :$HTTP_PORT/ste 무응답 — 위 web 항목을 먼저" ;;
    *)   warn sso-secret "verify $v — 판정 불가" ;;
  esac
fi

# ── 4) 게이트웨이 — ste 백엔드 세션·도구 수·권한 정책 ───────────────────────────────────
H="$(curl -s -m 4 http://127.0.0.1:9110/health 2>/dev/null || true)"
if [ -n "$H" ] && printf '%s' "$H" | python3 -c 'import json,sys;json.load(sys.stdin)' 2>/dev/null; then
  read -r gste gpol gready <<<"$(H="$H" python3 -c 'import json,os;h=json.loads(os.environ["H"]);b=h.get("backends") or {};print(("up" if b.get("ste") is True else ("absent" if "ste" not in b else "down")), int(h.get("access_policy_loaded") or 0), str(h.get("access_policy_ready","?")))')"
  [ "$gste" = up ] && ok gateway-ste "ste 백엔드 세션 up" || bad gateway-ste "ste 백엔드 $gste — 정적 백엔드는 /refresh 로 안 붙는다(재기동) · 15812 도달 확인"
  if [ "$gpol" = 0 ]; then bad policy "권한 정책 미적재(0) — 전 백엔드가 전원에게 열리고 위임 백엔드는 닫힌다"; else ok policy "백엔드 ${gpol}개분 적재됨 (ready=$gready)"; fi
else
  bad gateway "게이트웨이 /health 무응답(:9110)"
fi

# ── 4b) 포털 TLS — 사용자 PC 의 Claude(Node)가 이 포털을 믿을 수 있는가(/tls/info) ─────────
# S0 의 "cae00 인증서 종류" 가 여기서 판정된다: 공개 CA 면 설치 불필요, 사설·자체서명이면 발급 CA 체인이
# 있어야 배치파일이 심는다. 리프만 있는 사내 CA 발급은 연결 불가다(리프는 CA 를 대신하지 못한다 — 실측).
TI="$(curl -s -m 4 "http://127.0.0.1:$HTTP_PORT/tls/info" 2>/dev/null || true)"
if [ -n "$TI" ] && printf '%s' "$TI" | python3 -c 'import json,sys;json.load(sys.stdin)' 2>/dev/null; then
  read -r tavail tver tneed tca texp <<<"$(TI="$TI" python3 -c 'import json,os;d=json.loads(os.environ["TI"]);print(*[int(bool(d.get(k))) for k in ("available","verified","needs_ca","ca_available","expired")])')"
  # 두 사유는 다른 질문에 답한다 — verify_error 는 "왜 공개 루트에 안 닿나", ca_error 는 "왜 체인을 못 쓰나".
  # needs_ca 면 verify_error 는 늘 차 있으므로 or 로 고르면 ca_error 가 영영 안 보인다(3라운드 검토).
  tverr="$(TI="$TI" python3 -c 'import json,os;d=json.loads(os.environ["TI"]);print((d.get("verify_error") or "")[:120])')"
  tcaerr="$(TI="$TI" python3 -c 'import json,os;d=json.loads(os.environ["TI"]);print((d.get("ca_error") or "")[:160])')"
  if [ "$tavail" = 0 ]; then warn tls "포털 인증서 파일 없음(TLS 미설정 또는 TLS_CERT_PATH 오류)"
  elif [ "$texp" = 1 ]; then bad tls "포털 인증서 만료 — CA 를 심어도 연결 안 됨, 갱신 필요"
  elif [ "$tver" = 0 ]; then warn tls "체인 판정 못 함(모름≠정상) — ${tverr:-$tcaerr}"
  elif [ "$tneed" = 0 ]; then ok tls "공개 CA 체인 — 사용자 PC 에 인증서 설치 불필요"
  elif [ "$tca" = 1 ]; then ok tls "사설·자체서명 — 발급 CA 체인 준비됨(/tls/ca.crt, 배치파일이 심는다)"
  else bad tls "사설 CA 인데 발급 CA 체인 없음 — 개인 Claude 연결 불가: $tcaerr"; fi
else
  warn tls "포털 /tls/info 무응답(:$HTTP_PORT) — 포털이 안 떠 있거나 옛 버전"
fi

# ── 4c) 공개 https 종단 — 포털 nginx 가 https 를 실제로 내는가, 공개 주소 스킴·쿠키 Secure 가 맞는가 ─────
# tls 행은 "어떤 인증서인가", 이 행은 "https 가 켜져서 응답하는가". 둘은 다른 질문이다(2026-09-27 RA 재연결 감사 —
# RA 요청서의 공개 주소가 https 인데 ENABLE_TLS 기본값은 false 다).
ETLS="$(envv ENABLE_TLS "$ROOT/infra/.env")"; HPORT="$(envv HTTPS_PORT "$ROOT/infra/.env")"; HPORT="${HPORT:-443}"
PBU="$(envv PUBLIC_BASE_URL "$ROOT/infra/.env")"; CSEC="$(envv COOKIE_SECURE "$ROOT/infra/.env")"
if [ "$ETLS" != true ]; then
  case "$PBU" in
    # 앞단(사내 프록시)이 https 를 종단하고 포털엔 http 로 넘기는 구성이면 이 조합이 정상이다 — 포털은 URL 을 헤더가 아니라
    # PUBLIC_BASE_URL 로 만들기 때문이다. 포털이 직접 종단할 박스면 ENABLE_TLS 를 켜야 한다. 어느 쪽인지는 사람이 안다 → 경고.
    https://*) [ "$CSEC" = true ] && warn https "ENABLE_TLS 꺼짐 + PUBLIC_BASE_URL https($PBU) — 앞단이 https 를 종단하고 :$HTTP_PORT 로 넘기는 구성이면 정상. 포털이 직접 종단할 박스면 ENABLE_TLS=true·TLS_CERT_PATH" \
                                  || bad  https "PUBLIC_BASE_URL 이 https($PBU) 인데 COOKIE_SECURE≠true — 외부 IdP 의 cross-site POST 에 상태 쿠키가 안 실린다. infra/.env 에 COOKIE_SECURE=true" ;;
    *)         warn https "꺼짐(ENABLE_TLS≠true) — 이 박스는 http :$HTTP_PORT 만 낸다. 공개 주소가 https 면 infra/.env 에 ENABLE_TLS=true·TLS_CERT_PATH(fullchain)·PUBLIC_BASE_URL=https://…·COOKIE_SECURE=true" ;;
  esac
else
  hc="$(curl -sk -o /dev/null -w '%{http_code}' -m 4 "https://127.0.0.1:$HPORT/health" 2>/dev/null || echo 000)"
  if [ "$hc" != 200 ]; then
    bad https ":$HPORT 무응답($hc) — 인증서 경로(TLS_CERT_PATH, 리포 루트 상대)·rootless 저포트(grant-net-bind.sh)·nginx 로그"
  else
    _mm=""
    case "$PBU" in https://*) : ;; *) _mm="PUBLIC_BASE_URL 이 https 가 아니다($PBU)" ;; esac
    [ "$CSEC" = true ] || _mm="${_mm:+$_mm · }COOKIE_SECURE≠true(브라우저가 상태 쿠키를 SameSite=lax 로 남긴다)"
    if [ -n "$_mm" ]; then bad https ":$HPORT 200 인데 설정이 어긋난다 — $_mm"; else ok https ":$HPORT 200 · PUBLIC_BASE_URL https · COOKIE_SECURE=true"; fi
  fi
fi

# ── 5) 배포 신선도 — 헤드 마커 vs 리포 HEAD(direct) / Drive 커밋(teleport) ──────────────
if [ -n "$TENV" ] && [ -d "$(dirname "$TENV")/.." ]; then
  STE_DIR="$(cd "$(dirname "$TENV")/.." && pwd)"
  head_marker="$(cd "$STE_DIR" && . deploy/lib/transport.sh >/dev/null 2>&1 && tr_run 'cat /opt/ste/.deployed-commit 2>/dev/null' 2>/dev/null | tr -d '[:space:]' || true)"
  if [ -z "$head_marker" ]; then warn deployed "헤드에 배포 커밋 마커가 없다(옛 deploy-backend 로 배포됨) — 다음 배포부터 생긴다"
  else
    if [ "$MODE" = direct ]; then ref="$(git -C "$STE_DIR" rev-parse HEAD 2>/dev/null)"; refn="리포 HEAD"
    else ref="$(rclone cat "${RCLONE_REMOTE:-ApptainerImages:}SmartTwinExplorer/staging/ste-code.commit" 2>/dev/null | tr -d '[:space:]')"; refn="Drive 스테이징"; fi
    if [ -z "$ref" ]; then warn deployed "헤드 ${head_marker:0:12} · $refn 을 못 읽었다"
    elif [ "${head_marker%-dirty}" = "$ref" ]; then ok deployed "헤드 ${head_marker:0:12} = $refn"
    elif [ "$MODE" = direct ]; then
      # direct 는 커밋이 아니라 **내용 지문**으로 갱신을 판정한다(deploy-ste --if-stale). 마커가 HEAD 뒤인 것은
      # 배포 뒤 커밋만 더 있었을 수 있으니 여기서는 정보로만 낸다 — 경고로 내면 "갱신했는데 왜 경고" 가 된다.
      ok deployed "헤드 ${head_marker:0:12} (리포 HEAD ${ref:0:12}) — direct 는 내용 지문으로 판정, deploy-ste --if-stale 참조"
    else warn deployed "헤드 ${head_marker:0:12} ≠ $refn ${ref:0:12} — 갱신 대상(update-all --with-ste)"; fi
  fi
fi

if [ "$REPORT" = 1 ]; then
  # 행은 env 로 넘긴다 — heredoc 과 here-string 을 같이 주면 stdin 이 하나만 남아 스크립트가 데이터에 밀린다(실측).
  ROWS="$(for k in "${!R[@]}"; do printf '%s\t%s\n' "$k" "${R[$k]}"; done)" RED="$RED" python3 - <<'PY'
import os,json
rows=[l.split("\t",1) for l in os.environ["ROWS"].splitlines() if "\t" in l]
print(json.dumps({"ok": os.environ["RED"]=="0",
                  "items": {k:{"state":v.split(":",1)[0],"detail":v.split(":",1)[1]} for k,v in rows}}, ensure_ascii=False))
PY
fi
exit $RED
