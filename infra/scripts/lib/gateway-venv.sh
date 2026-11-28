#!/usr/bin/env bash
# 게이트웨이를 다시 띄우기 전에 게이트웨이 전용 venv(MCP SDK 2.x)를 맞추는 lib — update-sites · update-all 이 읽는다(docs/mcp-modernize M4)
#
# 왜 — 게이트웨이가 SDK 2.x 로 옮겨 가면서 그 start.sh 는 고른 파이썬(./.venv, 없으면 형제 에이전트 venv)의 mcp 가 2.x 가 아니면 띄우지 않는다
# (HWAXMcpGateway README 「게이트웨이 전용 venv」). update-sites 는 down → up 이라 venv 없이 새 판을 받은 박스는 내린 게이트웨이를 다시 못 띄운다 —
# 챗 · 심의 · 개인 Claude 의 도구가 통째로 끊긴다. cae00 은 바깥 pip 이 막혀 있을 수 있어(사내 프록시) 바퀴 꾸러미를 Drive 로 받는다
# (앞선 사례 tools/claude-chat-wheels/ — docs/chat-llm-claude/server-setup.md). 그래서 **내리기 전에** venv 를 맞추고, 못 맞추면 내리지 않는다
# (떠 있는 옛 프로세스가 그대로 돈다) — ✗ 와 까닭 · 사람 몫 한 줄을 남긴다(실패가 정상처럼 보이면 안 된다).
#
#   . infra/scripts/lib/gateway-venv.sh
#   hwax_gw_venv_prepare [게이트웨이 리포]  0 = 띄워도 된다(판 일치 · SDK 2.x 를 고정하지 않는 판) 또는 꾸러미를 받아 대조까지 마쳤다(install 차례)
#                                          1 = 못 한다(✗ · 사람 몫을 찍었다) — 부르는 쪽은 게이트웨이를 내리지 않는다
#   hwax_gw_venv_install                   prepare 가 받아 둔 꾸러미로 짓는다 — 0 지음(또는 할 일 없음) · 1 실패(install.sh 가 있던 venv 를 되돌렸다)
#   hwax_gw_venv_discard                   받아 둔 꾸러미를 버린다(재기동을 미뤘을 때 — 다음 실행이 다시 받는다)
#   hwax_gw_venv_ensure [게이트웨이 리포]   prepare + install — 심의 확인을 이미 지난 자리(update-all §5 재프로비저닝 · 자동 복구)
#   hwax_gw_venv_note_take                 자식(update-sites)이 남긴 ✗ 사유를 「까닭 · 사람 몫: …」 한 줄로 찍고 지운다 — 0 있었다 · 1 없다(update-all 이 fail 로 끝 요약에 싣는다)
#   hwax_gw_venv_push_cmd <파이썬 판> <아키텍처> [게이트웨이 리포]   꾸러미 짓기 · 올리기 명령(바깥에 닿는 박스에서 사람이 돌린다 — 올리기는 짓지 않는다)
#
# 차례가 둘인 까닭 — install.sh 는 있던 .venv 를 .venv.old-<시각> 으로 비켜 두고 새로 짓는다. 그 venv 로 떠 있는 게이트웨이는 그 순간부터 늦게 읽는
# 모듈을 못 찾는다. 그래서 받기 · 대조(prepare)는 심의 기다림 **앞**(못 받으면 새 심의를 멈추지 않는다), 짓기(install)는 기다림을 지나 내리기
# **바로 앞**에 둔다(재기동을 미루면 짓지 않는다 — 옛 프로세스가 비켜 난 venv 위에서 몇 시간 돌지 않게).
#
# 꾸러미 자리 — <HWAX_DRIVE_REMOTE 의 부모(…/HWAXPortal)>/tools/gateway-wheels/<열쇠>/ (HWAXMcpGateway tools/gateway-wheels/build.sh 가 지은 폴더 그대로).
#   열쇠 = py<파이썬 판>-<아키텍처>-<requirements.txt 의 `이름==판` 고정을 이름 차례로 이은 글의 sha256 앞 12자>. 바이너리 바퀴(pydantic-core 등)가
#   파이썬 판 · 아키텍처마다 달라 둘을 넣고, 판 고정이 바뀌면 열쇠가 바뀌어 옛 꾸러미를 새 판으로 잘못 깔지 않는다.
# 파이썬 — infra/.env(또는 환경)의 GATEWAY_VENV_PYTHON 이 있으면 그것만(틀리면 ✗ — 다른 것으로 슬쩍 넘어가지 않는다). 없으면 python3.12 ·
#   python3.13 · python3.11 · HEAXHub 가 푼 standalone 파이썬 · python3 가운데 3.11 이상이고 venv · ensurepip 가 있는 첫 것(받은 편지함 MQ-8).
#
# ⚠ update-sites · update-all 은 set -e 가 아니다. set -e 스크립트에서 부르면 `hwax_gw_venv_prepare || _rc=$?` 로 받는다(1 이 정상 상태다).
_HWAX_GW_VENV_PORTAL="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
HWAX_GW_VENV_STATE=""   # na(SDK 2.x 를 고정하지 않는 판) · ok(판 일치) · staged(꾸러미 받음 — install 차례) · fail
HWAX_GW_VENV_STAGE=""
HWAX_GW_VENV_DIR=""
HWAX_GW_VENV_PY=""
HWAX_GW_VENV_KEY=""
HWAX_GW_VENV_WHY=""

_hwax_gw_venv_envv() {   # <키> — 환경이 먼저, 없으면 포털 infra/.env 의 마지막 줄(따옴표 · 끝 공백을 벗긴다)
  local v="${!1:-}"
  if [ -z "$v" ] && [ -f "$_HWAX_GW_VENV_PORTAL/infra/.env" ]; then
    v="$(sed -n "s/^$1=//p" "$_HWAX_GW_VENV_PORTAL/infra/.env" 2>/dev/null | tail -1 | tr -d "\"'" | sed 's/[[:space:]]*#.*$//; s/[[:space:]]*$//')"
  fi
  printf '%s' "$v"
}

hwax_gw_venv_dir() {     # 게이트웨이 리포 — HWAX_GW_DIR > 포털 형제 > ~/Projects > ~/claude(update-all 의 find_repo 와 같은 차례)
  local c
  if [ -n "${HWAX_GW_DIR:-}" ]; then printf '%s' "$HWAX_GW_DIR"; return 0; fi
  for c in "$(dirname "$_HWAX_GW_VENV_PORTAL")/HWAXMcpGateway" "$HOME/Projects/HWAXMcpGateway" "$HOME/claude/HWAXMcpGateway"; do
    if [ -f "$c/gateway.py" ]; then printf '%s' "$c"; return 0; fi
  done
  return 1
}

_hwax_gw_venv_pins() {   # <requirements 파일> → `이름==판` 줄(이름은 소문자 · '-' '_' '.' 를 '-' 로 — pip 의 같은 이름 규칙), 이름 차례
  awk '{ sub(/#.*/, ""); gsub(/^[ \t]+|[ \t]+$/, "") }
       /^-/ || $0 == "" { next }
       match($0, /^[A-Za-z0-9_.-]+/) {
         n = tolower(substr($0, 1, RLENGTH)); rest = substr($0, RLENGTH + 1)
         gsub(/[-_.]+/, "-", n); sub(/^\[[^]]*\]/, "", rest); gsub(/^[ \t]+/, "", rest)
         if (substr(rest, 1, 2) == "==") { v = substr(rest, 3); gsub(/^[ \t]+/, "", v); sub(/[ \t;].*$/, "", v); if (v != "") print n "==" v }
       }' "$1" 2>/dev/null | LC_ALL=C sort -u
}

_hwax_gw_venv_key() {    # <파이썬 판> <아키텍처> <고정 줄들>
  printf 'py%s-%s-%s' "$1" "$2" "$(printf '%s\n' "$3" | sha256sum | cut -c1-12)"
}

_hwax_gw_venv_pyver() {  # <파이썬> → "3.12"(3.11 이상이고 venv · ensurepip 가 있을 때만), 아니면 빈 글과 1
  local v
  v="$("$1" -c 'import sys, venv, ensurepip; print("%d.%d" % sys.version_info[:2]) if sys.version_info[:2] >= (3, 11) else sys.exit(3)' 2>/dev/null)" || return 1
  case "$v" in 3.1[1-9]|3.[2-9][0-9]) printf '%s' "$v" ;; *) return 1 ;; esac
}

_hwax_gw_venv_pick_py() { # → 파이썬 경로(HWAX_GW_VENV_PY) — 0 찾음 · 1 못 찾음(까닭을 찍지 않는다 — 부르는 쪽이 ✗)
  local want c p
  want="$(_hwax_gw_venv_envv GATEWAY_VENV_PYTHON)"
  if [ -n "$want" ]; then
    p="$(command -v "$want" 2>/dev/null || true)"
    [ -n "$p" ] && _hwax_gw_venv_pyver "$p" >/dev/null && { HWAX_GW_VENV_PY="$p"; return 0; }
    return 1
  fi
  # HEAXHub standalone 파이썬(install-python.sh 가 root 없이 푼 것) — 허브 리포는 update-all 의 HEAX_DIR(없으면 포털 형제)
  for c in python3.12 python3.13 python3.11 "${HEAX_DIR:-$(dirname "$_HWAX_GW_VENV_PORTAL")/HEAXHub}"/deploy/apptainer/.tools/python-*/bin/python3 python3; do
    p="$(command -v "$c" 2>/dev/null || true)"
    [ -n "$p" ] || continue
    if _hwax_gw_venv_pyver "$p" >/dev/null; then HWAX_GW_VENV_PY="$p"; return 0; fi
  done
  return 1
}

_hwax_gw_venv_diff() {   # <파이썬> <고정 줄들> → 어긋난 것 "이름 있는판→고정판, …"(없으면 빈 글). 그 파이썬을 읽지 못하면 "읽지 못함" 과 1
  local py="$1" pins="$2" names have
  names="$(printf '%s\n' "$pins" | sed 's/==.*//')"
  # shellcheck disable=SC2086 — 이름은 [a-z0-9-] 뿐이다
  have="$("$py" -c 'import importlib.metadata as m, sys
for n in sys.argv[1:]:
    try:
        print(n, m.version(n))
    except Exception:
        print(n, "-")' $names 2>/dev/null)" || { printf '읽지 못함'; return 1; }
  [ -n "$have" ] || { printf '읽지 못함'; return 1; }
  # 두 목록은 파일로 넘긴다 — awk -v 는 줄바꿈 든 값을 awk 마다 다르게 읽는다(mawk 는 거절한다)
  awk 'NR == FNR { h[$1] = $2; next }
       { split($0, p, "=="); got = (p[1] in h) ? h[p[1]] : "-"; if (got != p[2]) { printf "%s%s %s→%s", (k++ ? ", " : ""), p[1], (got == "-" ? "없음" : got), p[2] } }' \
    <(printf '%s\n' "$have") <(printf '%s\n' "$pins")
}

_hwax_gw_venv_lock_diff() { # <고정 줄들> <requirements.lock> → 꾸러미에 없거나 다른 고정 "이름 고정판≠꾸러미판, …"
  # 잠금이 없거나 비면 awk 의 NR == FNR 이 고정 줄에 걸려 '같다' 로 읽힌다 — 먼저 가른다
  [ -s "$2" ] || { printf 'requirements.lock 없음'; return 0; }
  awk 'NR == FNR { line = tolower($0); gsub(/[ \t\r]/, "", line); split(line, f, "=="); n = f[1]; gsub(/[-_.]+/, "-", n); lock[n] = f[2]; next }
       { split($0, p, "=="); got = (p[1] in lock) ? lock[p[1]] : "없음"; if (got != p[2]) printf "%s%s %s≠%s", (k++ ? ", " : ""), p[1], p[2], got }' \
    "$2" <(printf '%s\n' "$1") 2>/dev/null
}

_hwax_gw_venv_note() {   # ✗ 사유를 자식 → 부모로 넘기는 파일(update-all 의 장부 옆) — 단독 실행이면 없다
  if [ -n "${HWAX_GW_VENV_NOTE:-}" ]; then printf '%s' "$HWAX_GW_VENV_NOTE"
  elif [ -n "${HWAX_SKIP_LEDGER:-}" ]; then printf '%s.gw-venv' "$HWAX_SKIP_LEDGER"; fi
}

_hwax_gw_venv_fail() {   # <까닭> <사람 몫>
  local f
  HWAX_GW_VENV_STATE=fail
  printf '  ✗ 게이트웨이 전용 venv — %s. 게이트웨이를 다시 띄우지 않는다(떠 있는 옛 프로세스가 그대로 돈다)\n      사람 몫: %s\n' "$1" "$2"
  f="$(_hwax_gw_venv_note)"
  if [ -n "$f" ]; then { printf '%s\t%s\n' "$1" "$2" > "$f"; } 2>/dev/null || true; fi
  hwax_gw_venv_discard
  return 1
}

hwax_gw_venv_discard() {
  if [ -n "$HWAX_GW_VENV_STAGE" ]; then rm -rf "$HWAX_GW_VENV_STAGE"; fi
  HWAX_GW_VENV_STAGE=""
  return 0
}

hwax_gw_venv_note_take() {
  local f n
  f="$(_hwax_gw_venv_note)"
  [ -n "$f" ] && [ -s "$f" ] || return 1
  n="$(head -1 "$f")"; rm -f "$f"
  printf '%s · 사람 몫: %s' "${n%%$'\t'*}" "${n#*$'\t'}"
}

hwax_gw_venv_push_cmd() { # <파이썬 판> <아키텍처> [게이트웨이 리포] — 짓기 한 줄 · 올리기 한 줄(올리기는 사람이 한다)
  local pyv="$1" arch="$2" gw="${3:-}" pins key remote
  [ -n "$gw" ] || gw="$(hwax_gw_venv_dir)" || { echo "✗ 게이트웨이 리포를 찾지 못했다 — HWAX_GW_DIR=<리포> 로 준다" >&2; return 2; }
  pins="$(_hwax_gw_venv_pins "$gw/requirements.txt")"
  case "$pins" in *mcp==2.*) ;; *) echo "✗ $gw/requirements.txt 가 mcp 2.x 를 고정하지 않는다 — 꾸러미가 필요 없는 판이다" >&2; return 2 ;; esac
  key="$(_hwax_gw_venv_key "$pyv" "$arch" "$pins")"
  remote="$(_hwax_gw_venv_envv HWAX_DRIVE_REMOTE)"; remote="${remote%/}"; remote="${remote%/images}"
  printf '# 게이트웨이 전용 venv 꾸러미 %s — 게이트웨이 %s 의 requirements.txt(파이썬 %s · %s)\n' "$key" "$(git -C "$gw" rev-parse --short HEAD 2>/dev/null || echo '?')" "$pyv" "$arch"
  printf 'O="$(mktemp -d)/gw-wheels" && %s/tools/gateway-wheels/build.sh --python %s --arch %s --out "$O"\n' "$gw" "$pyv" "$arch"
  printf 'rclone sync "$O" "%s/tools/gateway-wheels/%s/" && rclone lsf "%s/tools/gateway-wheels/%s/"\n' "${remote:-<HWAX_DRIVE_REMOTE 의 부모>}" "$key" "${remote:-<HWAX_DRIVE_REMOTE 의 부모>}" "$key"
}

hwax_gw_venv_prepare() {
  local gw pins mcp pyv arch remote rclone lsf lrc=0 drive diff push what man_py man_arch
  hwax_gw_venv_discard
  HWAX_GW_VENV_STATE=""; HWAX_GW_VENV_PY=""; HWAX_GW_VENV_KEY=""; HWAX_GW_VENV_WHY=""
  gw="${1:-}"
  [ -n "$gw" ] || gw="$(hwax_gw_venv_dir)" || gw=""
  HWAX_GW_VENV_DIR="$gw"
  if [ -z "$gw" ] || [ ! -f "$gw/gateway.py" ]; then
    # 리포가 없으면 update(git pull)가 이미 ✗(dir not found)다 — 띄울 것도 없다. 여기서 막을 까닭이 없다.
    echo "  · 게이트웨이 전용 venv: 게이트웨이 리포를 찾지 못해 보지 않는다(${gw:-자리 모름})"
    HWAX_GW_VENV_STATE=na; return 0
  fi
  pins="$(_hwax_gw_venv_pins "$gw/requirements.txt")"
  mcp="$(printf '%s\n' "$pins" | sed -n 's/^mcp==//p')"
  case "$mcp" in
    2.*) ;;
    *) echo "  · 게이트웨이 전용 venv: 이 판의 requirements.txt 는 MCP SDK 2.x 를 고정하지 않는다(mcp ${mcp:-고정 없음}) — 짓지 않는다(종전 venv 로 뜬다)"
       HWAX_GW_VENV_STATE=na; return 0 ;;
  esac
  if [ -x "$gw/.venv/bin/python" ]; then
    diff="$(_hwax_gw_venv_diff "$gw/.venv/bin/python" "$pins")" || diff="venv 파이썬을 읽지 못함"
    if [ -z "$diff" ]; then
      echo "  ✓ 게이트웨이 전용 venv 판 일치 — mcp $mcp(requirements.txt 고정 $(printf '%s\n' "$pins" | grep -c .)개 모두)"
      HWAX_GW_VENV_STATE=ok; return 0
    fi
    HWAX_GW_VENV_WHY="판이 다르다($diff)"
  else
    HWAX_GW_VENV_WHY=".venv 가 없다"
  fi
  # ── 지어야 한다 — 파이썬 · 아키텍처로 열쇠를 정하고 Drive 꾸러미를 받는다 ─────────────────────────────
  if ! _hwax_gw_venv_pick_py; then
    if [ -n "$(_hwax_gw_venv_envv GATEWAY_VENV_PYTHON)" ]; then
      _hwax_gw_venv_fail "$HWAX_GW_VENV_WHY · infra/.env 의 GATEWAY_VENV_PYTHON($(_hwax_gw_venv_envv GATEWAY_VENV_PYTHON))이 파이썬 3.11 이상(venv · ensurepip 있음)이 아니다" \
        "GATEWAY_VENV_PYTHON 을 맞는 파이썬 경로로 고치고 다시 돈다(받은 편지함 MQ-8 의 출력 — HEAXHub standalone 파이썬도 된다)"
    else
      _hwax_gw_venv_fail "$HWAX_GW_VENV_WHY · venv 를 지을 파이썬 3.11 이상(venv · ensurepip 있음)을 찾지 못했다(python3.12 · 3.13 · 3.11 · HEAXHub standalone · python3)" \
        "infra/.env 에 GATEWAY_VENV_PYTHON=<파이썬 3.11+ 실행 파일> 을 적고 다시 돈다(받은 편지함 MQ-8)"
    fi
    return 1
  fi
  pyv="$(_hwax_gw_venv_pyver "$HWAX_GW_VENV_PY")"
  arch="$(uname -m)"
  HWAX_GW_VENV_KEY="$(_hwax_gw_venv_key "$pyv" "$arch" "$pins")"
  push="바깥에 닿는 박스(dev)에서 ./infra/scripts/gateway-venv.sh push-cmd --python $pyv --arch $arch 가 내는 짓기 · 올리기 두 줄을 돌린 뒤(꾸러미 열쇠 $HWAX_GW_VENV_KEY 가 같아야 한다) 이 박스에서 update-all 을 다시 돈다(게이트웨이만이면 ./infra/scripts/update-sites.sh mcp-gateway)"
  remote="$(_hwax_gw_venv_envv HWAX_DRIVE_REMOTE)"; remote="${remote%/}"; remote="${remote%/images}"
  if [ -z "$remote" ]; then
    _hwax_gw_venv_fail "$HWAX_GW_VENV_WHY · infra/.env 에 HWAX_DRIVE_REMOTE 가 없어 Drive 바퀴 꾸러미를 받을 수 없다" \
      "HWAX_DRIVE_REMOTE 를 적고 다시 돈다 — 이 박스가 PyPI 에 닿으면 손으로: cd $gw && $HWAX_GW_VENV_PY -m venv .venv && .venv/bin/pip install -r requirements.txt"
    return 1
  fi
  rclone="$(command -v rclone 2>/dev/null || true)"; [ -n "$rclone" ] || rclone="$_HWAX_GW_VENV_PORTAL/infra/bin/rclone"
  if [ ! -x "$rclone" ]; then
    _hwax_gw_venv_fail "$HWAX_GW_VENV_WHY · rclone 이 없어 Drive 바퀴 꾸러미를 받을 수 없다" "./infra/scripts/bootstrap-rclone.sh 로 rclone 을 깔고 다시 돈다"
    return 1
  fi
  drive="$remote/tools/gateway-wheels/$HWAX_GW_VENV_KEY/"
  # 있음 · 없음 · 모름을 가른다 — 출력을 먼저 받고 본다(파이프 판정은 pipefail 아래서 '없음' 으로 읽힌다). rclone 3 = 디렉터리 없음.
  lsf="$("$rclone" lsf --max-depth 1 "$drive" 2>/dev/null)" || lrc=$?
  if [ "$lrc" != 0 ] && [ "$lrc" != 3 ]; then
    _hwax_gw_venv_fail "$HWAX_GW_VENV_WHY · Drive 를 읽지 못했다(rclone lsf rc $lrc — $drive)" "rclone 설정 · 네트워크(사내 프록시)를 확인하고 다시 돈다 — 꾸러미가 아직 없으면: $push"
    return 1
  fi
  case $'\n'"$lsf"$'\n' in
    *$'\n'MANIFEST.txt$'\n'*) ;;
    *) _hwax_gw_venv_fail "$HWAX_GW_VENV_WHY · Drive 에 이 판의 꾸러미가 없다($drive)" "$push"; return 1 ;;
  esac
  [ "${HWAX_GW_VENV_PROBE:-0}" = 1 ] && { echo "  · 게이트웨이 전용 venv: 지어야 한다($HWAX_GW_VENV_WHY) — Drive 꾸러미 있음($drive)"; HWAX_GW_VENV_STATE=probe; return 0; }
  HWAX_GW_VENV_STAGE="$(mktemp -d)"
  if ! "$rclone" copy "$drive" "$HWAX_GW_VENV_STAGE/" >/dev/null 2>&1; then
    _hwax_gw_venv_fail "$HWAX_GW_VENV_WHY · Drive 꾸러미를 받지 못했다($drive)" "rclone 설정 · 네트워크를 확인하고 다시 돈다"
    return 1
  fi
  if ! ( cd "$HWAX_GW_VENV_STAGE" && sha256sum -c --quiet SHA256SUMS ) >/dev/null 2>&1; then
    _hwax_gw_venv_fail "$HWAX_GW_VENV_WHY · 받은 꾸러미의 sha256 이 맞지 않는다($drive)" "꾸러미를 다시 짓고 덮어 올린다 — $push"
    return 1
  fi
  man_py="$(sed -n 's/^python=\([0-9.]*\).*/\1/p' "$HWAX_GW_VENV_STAGE/MANIFEST.txt" | head -1)"
  man_arch="$(sed -n 's/^arch=//p' "$HWAX_GW_VENV_STAGE/MANIFEST.txt" | head -1)"
  what="$(_hwax_gw_venv_lock_diff "$pins" "$HWAX_GW_VENV_STAGE/requirements.lock")"
  if [ "$man_py" != "$pyv" ] || [ "$man_arch" != "$arch" ] || [ -n "$what" ]; then
    _hwax_gw_venv_fail "$HWAX_GW_VENV_WHY · Drive 꾸러미의 판이 이 게이트웨이 판과 다르다(꾸러미 파이썬 ${man_py:-?} · ${man_arch:-?}${what:+ · $what} — 이 박스 파이썬 $pyv · $arch)" \
      "꾸러미를 다시 짓고 덮어 올린다 — $push"
    return 1
  fi
  echo "  · 게이트웨이 전용 venv: 지어야 한다($HWAX_GW_VENV_WHY) — Drive 꾸러미 $HWAX_GW_VENV_KEY 받음 · sha256 · 판 대조 통과(파이썬 $HWAX_GW_VENV_PY)"
  HWAX_GW_VENV_STATE=staged
  return 0
}

hwax_gw_venv_install() {
  local gw="$HWAX_GW_VENV_DIR" inst log rc=0 pins diff
  case "$HWAX_GW_VENV_STATE" in
    staged) ;;
    fail) return 1 ;;
    *) return 0 ;;
  esac
  inst="$gw/tools/gateway-wheels/install.sh"
  [ -f "$inst" ] || inst="$HWAX_GW_VENV_STAGE/install.sh"
  log="$(mktemp)"
  echo "  · 게이트웨이 전용 venv 짓기 — $inst"
  GATEWAY_DIR="$gw" bash "$inst" "$HWAX_GW_VENV_STAGE" "$HWAX_GW_VENV_PY" >"$log" 2>&1 || rc=$?
  sed 's/^/      /' "$log"
  if [ "$rc" != 0 ]; then
    _hwax_gw_venv_fail "꾸러미 $HWAX_GW_VENV_KEY 로 venv 를 짓지 못했다(install.sh rc $rc — $(tail -n 2 "$log" | tr '\n' ' ' | cut -c1-200)) · 있던 venv 는 install.sh 가 되돌렸다" \
      "이 박스에서 ./infra/scripts/gateway-venv.sh ensure 로 다시 지어 전체 출력을 본다(파이썬에 venv 모듈이 없으면 infra/.env 의 GATEWAY_VENV_PYTHON 을 다른 파이썬으로)"
    rm -f "$log"; return 1
  fi
  rm -f "$log"
  pins="$(_hwax_gw_venv_pins "$gw/requirements.txt")"
  diff="$(_hwax_gw_venv_diff "$gw/.venv/bin/python" "$pins")" || diff="venv 파이썬을 읽지 못함"
  if [ -n "$diff" ]; then
    _hwax_gw_venv_fail "꾸러미 $HWAX_GW_VENV_KEY 로 지은 venv 의 판이 requirements.txt 와 다르다($diff)" "꾸러미를 다시 짓고 덮어 올린다 — 바깥에 닿는 박스(dev)에서 ./infra/scripts/gateway-venv.sh push-cmd"
    return 1
  fi
  echo "  ✓ 게이트웨이 전용 venv 지음 — mcp $(printf '%s\n' "$pins" | sed -n 's/^mcp==//p') · 꾸러미 $HWAX_GW_VENV_KEY($HWAX_GW_VENV_WHY 였다) · 옛 venv 는 $gw/.venv.old-* (새 판이 선 뒤 지워도 된다)"
  hwax_gw_venv_discard
  HWAX_GW_VENV_STATE=ok
  return 0
}

hwax_gw_venv_ensure() {
  hwax_gw_venv_prepare "$@" || return 1
  hwax_gw_venv_install
}
