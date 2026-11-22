#!/usr/bin/env bash
# 웹 챗 Claude 를 켜기 전에 그 박스에서 도는 읽기 전용 점검(키 없이) — 바깥 연결 · 파이썬 인증서 · 꾸러미 · 키 파일 · 에이전트 서버 상태
#
# docs/chat-llm-claude/server-setup.md 1절. cae00 은 TLS 를 가로채는 사내 프록시 뒤라 dev 에서 되던 것이 안 될 수 있다 — 켜기 전에 이것부터 본다.
# 아무것도 쓰지 않고 키도 읽지 않는다(키 파일은 있는지 · 권한만). 프록시 주소 · 키 값은 찍지 않는다 — 결과 줄을 그대로 받은 편지함에 옮겨도 된다.
#
#   ./infra/scripts/claude-chat-check.sh
#
# 종료코드 0 = 바깥 연결과 파이썬 인증서가 된다(설치 · 키 · .env 는 절차대로), 1 = 막힌 것이 있다(줄의 ✗ 와 '다음' 을 본다).
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
AG="$ROOT/../HWAXAgentServer"
PY="$AG/.venv/bin/python"
URL="https://api.anthropic.com/v1/models"
FAIL=0
ok() { printf '  ✓ %s\n' "$*"; }
bad() { printf '  ✗ %s\n' "$*"; FAIL=1; }
note() { printf '  ○ %s\n' "$*"; }

[ -x "$PY" ] || { echo "✗ 에이전트 서버 venv 가 없다($AG/.venv) — 형제 리포 자리를 본다"; exit 1; }

# 에이전트 서버는 start.sh 가 .env 를 읽고 띄운다 — 프록시 · 인증서 칸만 같은 규칙(KEY=값 · 양끝 따옴표)으로 이 점검의 환경에 싣는다.
NET_KEYS="HTTPS_PROXY https_proxy HTTP_PROXY http_proxy NO_PROXY no_proxy SSL_CERT_FILE SSL_CERT_DIR"
env_from_agent() {
  local l k v
  [ -f "$AG/.env" ] || return 0
  while IFS= read -r l || [ -n "$l" ]; do
    case "$l" in ''|'#'*) continue ;; esac
    k="${l%%=*}"; v="${l#*=}"
    case " $NET_KEYS CLAUDE_CHAT_API_KEY_FILE " in *" $k "*) ;; *) continue ;; esac
    case "$v" in \"*\") v="${v#\"}"; v="${v%\"}" ;; \'*\') v="${v#\'}"; v="${v%\'}" ;; esac
    export "$k=$v"
  done < "$AG/.env"
}

echo "1. 프록시 · 인증서 설정(있음 · 없음만 — 값은 찍지 않는다)"
for k in $NET_KEYS; do
  in_env=""; in_file=""
  [ -n "${!k:-}" ] && in_env="셸"
  grep -q "^$k=" "$AG/.env" 2>/dev/null && in_file="에이전트 서버 .env"
  [ -n "$in_env$in_file" ] && note "$k — ${in_env}${in_env:+${in_file:+ · }}${in_file}"
done
if [ -n "${HTTPS_PROXY:-${https_proxy:-}}" ] && ! grep -qiE '^https_proxy=' "$AG/.env" 2>/dev/null; then
  note "프록시가 이 셸에만 있다 — update-all 같은 비로그인 셸로 다시 띄우면 빠질 수 있다(다음: 에이전트 서버 .env 에 HTTPS_PROXY 를 적는다)"
fi
env_from_agent

echo "2. curl — $URL(키 없이 — 401 이면 닿는다)"
code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 "$URL" 2>/dev/null)"; rc=$?
# curl 의 오류 글에는 프록시 주소가 섞인다 — 찍지 않고 끝 코드로 갈래만 말한다(결과 줄을 받은 편지함에 옮겨도 되게).
case "$rc:$code" in
  0:401) ok "닿는다(401 — 키가 없어서다)" ;;
  0:403) bad "HTTP 403 — 프록시 · 회사 정책이 막는 것으로 보인다(사람 확인)" ;;
  0:*) bad "뜻밖의 답 HTTP $code" ;;
  5:*) bad "프록시 이름을 풀지 못했다(curl 5) — 다음: 프록시 설정" ;;
  6:*) bad "api.anthropic.com 이름을 풀지 못했다(curl 6) — 다음: 프록시를 거쳐야 하는 박스다(HTTPS_PROXY)" ;;
  7:*) bad "연결하지 못했다(curl 7) — 다음: 방화벽 · 프록시" ;;
  28:*) bad "시간 초과(curl 28) — 다음: 방화벽 · 프록시" ;;
  35:*|60:*) bad "TLS · 인증서 오류(curl $rc) — 다음: 사내 루트 인증서(server-setup.md 1절)" ;;
  56:*) bad "프록시가 연결을 거절했다(curl 56) — 회사 정책일 수 있다(사람 확인)" ;;
  *) bad "curl 실패(끝 코드 $rc)" ;;
esac

echo "3. 에이전트 서버 파이썬(httpx — 에이전트 서버와 같은 클라이언트 · 같은 환경변수)"
"$PY" - "$URL" <<'EOF'
import sys
import httpx
url = sys.argv[1]
try:
    r = httpx.get(url, timeout=20)          # trust_env 기본 — 프록시 · SSL_CERT_FILE 을 읽는다(anthropic SDK 의 기본 클라이언트와 같다)
    if r.status_code == 401:
        print("  ✓ 닿는다(401) — 파이썬도 인증서를 믿는다")
    else:
        print(f"  ✗ 뜻밖의 답 HTTP {r.status_code}")
        sys.exit(1)
except httpx.ConnectError as e:
    msg = str(e)
    if "CERTIFICATE_VERIFY_FAILED" in msg or "certificate" in msg.lower():
        print("  ✗ 인증서를 믿지 못한다(사내 프록시가 TLS 를 바꿔 낀다) — 다음: 에이전트 서버 .env 에 "
              "SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt(시스템 묶음 — 사내 루트가 들어 있으면)")
    else:
        print(f"  ✗ 연결 못 함({type(e).__name__}) — 다음: 프록시 설정(server-setup.md 1절)")
    sys.exit(1)
except Exception as e:  # noqa: BLE001
    print(f"  ✗ {type(e).__name__}: {str(e)[:160]}")
    sys.exit(1)
EOF
[ $? -eq 0 ] || FAIL=1

echo "4. 꾸러미(requirements-anthropic.txt)"
have="$("$PY" -c 'import importlib.metadata as m
out = []
for p in ("anthropic", "langchain-anthropic"):
    try:
        out.append(f"{p} {m.version(p)}")
    except m.PackageNotFoundError:
        out.append(f"{p} 없음")
print(" · ".join(out))' 2>/dev/null)"
case "$have" in
  *없음*) note "설치 전 — $have(다음: server-setup.md 2절 — pip 가 안 되면 Drive 꾸러미 묶음)" ;;
  *) ok "$have" ;;
esac

echo "5. 키 파일(있는지 · 권한만 — 읽지 않는다)"
kf="${CLAUDE_CHAT_API_KEY_FILE:-}"
if [ -z "$kf" ]; then
  note "에이전트 서버 .env 에 CLAUDE_CHAT_API_KEY_FILE 이 없다(다음: server-setup.md 3 · 4절)"
elif [ ! -f "$kf" ]; then
  note "적힌 키 파일이 없다(다음: install -m 600 /dev/null <그 경로> 뒤 사람이 키를 넣는다)"
else
  mode="$(stat -c '%a' "$kf")"
  [ "$mode" = 600 ] && ok "있다 · 권한 600" || bad "있다 · 권한 $mode — chmod 600"
fi

echo "6. 에이전트 서버 상태(/health claude_chat)"
HEALTH="$(curl -s --noproxy '*' --max-time 5 http://127.0.0.1:9009/health 2>/dev/null)" "$PY" - <<'EOF'
import json, os
try:
    c = json.loads(os.environ.get("HEALTH") or "").get("claude_chat") or {}
except ValueError:
    print("  ○ /health 를 읽지 못했다(에이전트 서버가 꺼져 있나)")
    raise SystemExit(0)
if c.get("enabled"):
    n = len(c.get("models") or [])
    print("  ✓ 켜짐 — 모델 %s · 대상 %s · 고를 수 있는 모델 %d개" % (c.get("model"), c.get("for"), n))
elif c.get("error"):
    print("  ✗ 켜려다 못 켰다 — %s" % c.get("error"))
else:
    print("  ○ 꺼짐(CLAUDE_CHAT_MODEL 이 비었다 — 지금 그대로)")
EOF

echo
if [ "$FAIL" = 0 ]; then
  echo "→ 바깥 연결 · 인증서는 된다. server-setup.md 2절(설치)부터 이어 간다."
else
  echo "→ 막힌 것이 있다 — 위 ✗ 의 '다음' 을 하고 다시 돌린다. 결과 줄(✓ ✗ ○)은 그대로 받은 편지함 답에 옮겨도 된다(주소 · 키는 찍지 않았다)."
fi
exit "$FAIL"
