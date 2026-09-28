#!/usr/bin/env bash
# report-archive를 제외한 update-enabled 서비스를 포털부터 안전하게 최신화하는 헬퍼
# (repo: 있는데 없는/원격없는 서비스는 portal 상위로 자동 clone/remote → 포털 먼저 재기동+health
#  → 실패 시 나머지 보존하고 중단, 나머지는 서비스별 순차·실패해도 계속)
set -uo pipefail   # NOTE: -e 없음 — 한 서비스 실패가 전체 실행을 끊지 않도록
export PYTHONUNBUFFERED=1   # tee 파이프로 넘겨도 진행 로그가 즉시(버퍼링 없이) 흐르도록

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SVC="$ROOT/infra/scripts/services.sh"
. "$ROOT/infra/scripts/lib/change-detect.sh"
# deploy-all(§2) 과 다른 형식의 지문이라 **하위 디렉터리**를 따로 쓴다 — 같은 파일을 두 형식이 번갈아 덮으면 핑퐁 재기동이 난다(2라운드: 인자 없는 update-sites 는 portal 도 대상)
HWAX_RESTART_STATE_DIR="${HWAX_RESTART_STATE_DIR:-$ROOT/infra/.state/restart-fp/sites}"; export HWAX_RESTART_STATE_DIR
SVCPY="$ROOT/infra/scripts/services.py"
MANIFEST="$ROOT/infra/services.yaml"
PY="$ROOT/backend/.venv/bin/python"; [ -x "$PY" ] || PY="$(command -v python3)"
EXCLUDE="report-archive"
PORTAL="portal"

DRY=0
case "${1:-}" in
  -n|--dry-run) DRY=1; shift ;;
  -h|--help)
    echo "사용법: $(basename "$0") [-n|--dry-run] [서비스명...]"
    echo "  인자 없음 : report-archive·update:false·원격을 뺀 update-enabled 서비스 전부"
    echo "              (포털·게이트웨이·에이전트·MCP·사이트)."
    echo "  서비스명  : 준 목록만 대상(단 report-archive는 항상 제외)."
    echo "  사전작업  : 매니페스트에 repo: URL이 있는데 디렉토리가 없으면 portal 상위(형제)로 clone,"
    echo "              있으나 origin 미설정이면 remote 지정(경로 하드코딩 없이 discover 위치 사용)."
    echo "  방식       : 포털 먼저 down→up --update→health(실패 시 나머지 손대지 않고 중단),"
    echo "              이어서 나머지를 서비스별 순차 재기동(하나 실패해도 계속) → 요약."
    exit 0 ;;
esac

# ── 대상 산출: 인자가 있으면 그 목록, 없으면 매니페스트에서 자동 ──
if [ "$#" -gt 0 ]; then
  TARGETS="$*"
else
  TARGETS="$("$PY" - "$MANIFEST" "$EXCLUDE" <<'PY'
import sys, yaml
data = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
svcs = data if isinstance(data, list) else data.get("services", data)
out = []
for s in (svcs or []):
    if not isinstance(s, dict): continue
    if s.get("name") == sys.argv[2]: continue        # report-archive 제외
    if s.get("update") is False: continue            # update:false(vllm·일부 MCP 등)는 존중해 skip
    if s.get("host", "local") != "local": continue   # 원격은 SSH 경로라 제외
    out.append(s["name"])
print(" ".join(out))
PY
)"
fi

# report-archive는 어떤 경우에도(명시 인자 포함) 항상 제외 — 이중 안전
TARGETS="$(printf ' %s ' "$TARGETS" | sed "s/ ${EXCLUDE} / /g" | xargs || true)"
[ -n "$TARGETS" ] || { echo "대상 없음 (report-archive 제외)."; exit 0; }

# ── 사전작업 계획: repo: 있는 서비스의 discover 위치를 오케스트레이터와 동일 로직으로 확인 ──
# (services.py resolve_dir/PARENT 재사용 → 경로 하드코딩 없음. 없으면 CLONE, 있으나 origin 없으면 SETREMOTE)
PLAN="$("$PY" - "$SVCPY" "$MANIFEST" $TARGETS <<'PY'
import sys, importlib.util, yaml
spec = importlib.util.spec_from_file_location("svcmod", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
targets = set(sys.argv[3:])
data = yaml.safe_load(open(sys.argv[2], encoding="utf-8"))
svcs = data if isinstance(data, list) else data.get("services", data)
for s in (svcs or []):
    if not isinstance(s, dict) or s.get("name") not in targets: continue
    repo = s.get("repo")
    if not repo: continue
    d = m.resolve_dir(s)
    if d is None:
        print("CLONE\t%s\t%s" % (repo, m.PARENT / (s.get("discover") or s["name"])))
    elif not (d / ".git").exists():
        print("CLONE\t%s\t%s" % (repo, d))   # 디렉토리는 있으나 git repo 아님 → in-place repo화
    else:
        print("SETREMOTE\t%s\t%s" % (repo, d))
PY
)"

# 포털을 맨 앞으로 분리(있으면), 나머지는 매니페스트 순서(≈tier) 유지
HAS_PORTAL=0; REST=""
for s in $TARGETS; do
  if [ "$s" = "$PORTAL" ]; then HAS_PORTAL=1; else REST="$REST $s"; fi
done
REST="$(echo $REST | xargs || true)"

echo "▶ 대상: $TARGETS"
if [ "$HAS_PORTAL" = 1 ]; then echo "▶ 순서: portal(먼저·health 확인) → $REST"; else echo "▶ 순서: $REST"; fi
echo "▶ 방식: (사전 clone/remote) → 서비스별 down→up --update→health. 포털 실패 시 중단, 나머지는 실패해도 계속."

# ── 사전작업 실행(또는 dry-run 표시) ──
run_preflight() {
  [ -n "$PLAN" ] || { echo "  (사전작업 없음 — 모든 repo 준비됨)"; return 0; }
  while IFS=$'\t' read -r kind url dest; do
    [ -n "${kind:-}" ] || continue
    case "$kind" in
      CLONE)
        if [ "$DRY" = 1 ]; then
          echo "  clone  $url → $dest"
        elif [ ! -e "$dest" ] || [ -z "$(ls -A "$dest" 2>/dev/null)" ]; then
          echo "  clone  $url → $dest"
          git clone "$url" "$dest" || echo "  ⚠ clone 실패: $url"
        else
          # 디렉토리는 있으나 git repo 가 아님(비어있지 않음) → in-place init 후 원격 상태로 강제 체크아웃
          echo "  repair  기존 비-git 디렉토리 in-place 복구: $dest → origin=$url"
          git -C "$dest" init -q
          git -C "$dest" remote get-url origin >/dev/null 2>&1 || git -C "$dest" remote add origin "$url"
          if git -C "$dest" fetch -q origin; then
            b="$(git -C "$dest" remote show origin 2>/dev/null | sed -n 's/.*HEAD branch: //p')"; b="${b:-main}"
            git -C "$dest" checkout -f -B "$b" "origin/$b" || echo "  ⚠ checkout 실패: $dest"
          else
            echo "  ⚠ fetch 실패(원격/네트워크 확인): $url"
          fi
        fi ;;
      SETREMOTE)
        if ! git -C "$dest" remote get-url origin >/dev/null 2>&1; then
          echo "  set-remote  $dest → origin=$url"
          if [ "$DRY" != 1 ]; then
            git -C "$dest" remote add origin "$url"
            git -C "$dest" fetch -q origin || true
            b="$(git -C "$dest" rev-parse --abbrev-ref HEAD 2>/dev/null)"
            [ -n "$b" ] && git -C "$dest" branch -u "origin/$b" "$b" 2>/dev/null || true
          fi
        fi ;;
    esac
  done <<< "$PLAN"
}

echo "▶ 사전작업:"; run_preflight
if [ "$DRY" = 1 ]; then echo "(dry-run) 재기동은 실행하지 않음."; exit 0; fi

# 실패 원인 노출: up 출력의 FAIL 라인 + 서비스 로그 꼬리(크래시/헬스실패/빌드오류 원인)
show_cause() {
  local name="$1" out="$2" log
  echo "  ── ⚠ 실패 원인: $name ──"
  printf '%s\n' "$out" | grep -iE 'FAIL|✗|error|traceback|exception' | sed 's/^/    /' | head -6
  # up 출력이 알려주는 로그 경로(services.py "see <path>") 우선, 없으면 규약 경로
  log="$(printf '%s\n' "$out" | grep -oE '/[^ )]+\.log' | head -1)"
  [ -n "$log" ] || log="/tmp/hwax-services/${name}.log"
  if [ -s "$log" ]; then
    echo "    ↳ 로그 꼬리($log):"
    tail -n 30 "$log" | grep -vE '^[[:space:]]*$' | tail -20 | sed 's/^/      /'
  else
    echo "    ↳ 로그 없음/빈 파일: $log"
  fi
}

# 한 서비스 재기동: down → up --update. 진행을 라이브(tee)로 흘려보내 어디서 멈추는지 바로 보이게 한다.
# 출력을 변수에 모으지 않음 — 모으면 명령이 끝날 때까지 화면이 비어 hang을 못 본다. rc는 PIPESTATUS[0].
# 바뀌지 않았으면 재기동하지 않는다 — update(git pull) 뒤 서비스 지문(`services.py fp`: git HEAD + .env 내용)을 **마지막으로 띄운 시점**의
# 지문(상태 파일)과 비교해 같고 살아 있고 강제 목록(HWAX_FORCE_RESTART)에 없으면 down/up 을 건너뛴다. 'Already up to date' 문자열이나
# 블록 전/후 비교가 아닌 이유: §2 가 이미 reset 한 리포(signalforge-mcp)·§1c 가 먼저 고친 .env 가 전후 비교엔 안 보인다(검토 실측).
# 기동이 성공한 뒤에만 지문을 적는다. HWAX_RESTART_ALL=1 은 종전 동작. docs/update-all-skip-unchanged D-5·D-8.
SKIPPED_RESTART=""
restart_svc() {
  local name="$1" rc tmp upd cur last id0 id1 _port _url _hurl _probe _en _restart_fail=0 _upd_fail=0
  # 매니페스트에 없는 이름이면 여기서 끊는다 — 종전엔 update·up 이 조용히 아무것도 안 하고 `fp` 가 빈 값이라 아래 검증 블록을 통째로
  # 건너뛴 뒤 "✓ 완료" · exit 0 으로 끝났다(4라운드 실측). 서비스를 하나도 건드리지 않은 실행이 '전부 최신화' 로 끝나면 안 된다.
  "$SVC" enabled "$name" >/dev/null 2>&1; _en=$?
  if [ "$_en" = 2 ]; then
    echo "  ✗ $name: services.yaml 에 없는 서비스다 — 이름을 확인하라($SVC status 로 목록)" >&2; return 1
  fi
  tmp="$(mktemp)"
  echo "── $name ──  [$(date '+%H:%M:%S')]"
  echo "  · update (git pull) …"
  "$SVC" update "$name" 2>&1 | tee "$tmp"
  upd="$(tail -1 "$tmp")"
  printf '%s' "$upd" | grep -q '✗' && _upd_fail=1
  cur="$("$SVC" fp "$name" 2>/dev/null | tail -1)"; last="$(hwax_last_fp "$name")"
  # 갱신(git pull) 이 실패해도 지문이 같고 살아 있으면 재기동하지 않는다 — 같은 옛 코드를 내렸다 올려도 얻는 게 없고, GitHub 이 며칠 안 닿으면
  # update-all 마다 챗 스택이 끊긴다(3라운드). 실패는 종료코드로만 올린다(요약의 FAILED 에 든다).
  if [ "${HWAX_RESTART_ALL:-0}" != 1 ] && [ -n "$cur" ] && [ "$cur" = "$last" ] \
     && ! printf ' %s ' "${HWAX_FORCE_RESTART:-}" | grep -q " $name " \
     && "$SVC" status "$name" 2>/dev/null | grep -q '✓ up'; then
    echo "  · $name: 마지막 기동 뒤 변경 없음(지문 $cur) · 살아 있음 → 재기동 생략 (전부 재기동: HWAX_RESTART_ALL=1)  [$(date '+%H:%M:%S')]"
    SKIPPED_RESTART="$SKIPPED_RESTART $name"; rm -f "$tmp"
    # rc 2 = '갱신만 실패, 서비스는 정상·무변경'. rc 1 과 갈라야 한다 — 포털 게이트가 rc≠0 을 '재기동 실패' 로 읽어 나머지 전부를
    # 중단시켰다(무인자 실행에서 아홉 서비스가 손도 안 닿았고, 안내는 원인을 '포털 로그' 로 잘못 가리켰다. 4라운드 실측).
    if [ "$_upd_fail" = 1 ]; then echo "  · ✗ $name: 갱신(git pull) 은 실패했다 — 옛 코드 그대로 살아 있어 재기동은 생략, 종료코드만 올린다" >&2; return 2; fi
    return 0
  fi
  # 재기동이 실제로 됐는지는 health 포트를 듣는 프로세스(pid·시작시각)로 본다 — down 이 실패해도 up 은 'already-up' 으로 rc 0 을 내고,
  # 그 rc 만 믿고 새 지문을 적으면 옛 프로세스가 영구 생략된다(2라운드 검토 실측).
  # 리스너 식별은 포트로, 생존·내려감 대기는 매니페스트 health url 로 — 루트(/)가 404 인 서비스(agent-server)는 포트 루트를 두드리면
  # 살아 있어도 '내려갔다' 로 읽혀 대기가 무효가 된다(3라운드).
  _port="$("$SVC" port "$name" 2>/dev/null | tail -1)"; _url="http://127.0.0.1:${_port:-0}/"
  _hurl="$("$SVC" health "$name" 2>/dev/null | tail -1)"; _probe="${_hurl:-$_url}"   # _hurl 이 비면(매니페스트에 health 없음) 생존을 **판정할 수 없다**
  id0="$(hwax_listener_ids "$_url")"
  echo "  · down (기존 인스턴스 정리) …"
  "$SVC" down "$name" >/dev/null 2>&1 || true
  hwax_wait_down "$_probe" || echo "  ✗ $name: 정지 뒤에도 $_probe 가 답한다 — 옛 프로세스가 내려가지 않았다(down 실패)" >&2
  echo "  · up (build → start → health 대기) …"
  "$SVC" up "$name" 2>&1 | tee "$tmp"   # 화면+임시파일 동시 → 라이브 + 원인분석용 캡처
  rc=${PIPESTATUS[0]}
  if [ "$rc" = 0 ] && [ -n "$cur" ]; then
    id1="$(hwax_listener_ids "$_url")"
    case "$id1" in ""|*"?"*)
         # 이 박스 대상(only_on)인데 아무도 안 답하면 up 의 rc 0 은 거짓이다 — lib 사이클과 같은 규율(3라운드). 대상이 아닌 서비스는 up 이
         # '건너뜀' rc 0 을 내는 게 맞으므로 ✗ 로 만들지 않는다.
         # health url 이 없는 서비스(services.py 가 'started (no health url)' 로 정상 지원)는 살았는지 판정할 수 없다 → ✗ 로 만들지 않는다(4라운드).
         if [ -n "$_hurl" ] && [ "$_en" = 0 ] && ! hwax_alive "$_hurl"; then
           echo "  ✗ $name: up 은 성공이라는데 $_hurl 가 답하지 않는다(리스너 없음) — 기준 지문을 기록하지 않는다" >&2; rc=1
         else echo "  ⚠ $name: 프로세스를 식별하지 못해('${id1:-없음}') 기준 지문을 기록하지 않는다 — 다음 실행도 재기동한다" >&2; fi ;;
      *) if [ "$id1" != "$id0" ]; then hwax_mark_started "$name" "$cur"     # 띄운 시점의 지문 — 다음 실행의 비교 기준
         else echo "  ✗ $name: 재기동이 되지 않았다 — 같은 프로세스가 답한다(down 실패·already-up). 기준 지문을 기록하지 않는다" >&2; rc=1; fi ;;
    esac
  fi
  [ "$rc" -ne 0 ] && _restart_fail=1
  # 갱신 실패는 종료코드로 올린다(옛 코드로 떠 있어도 초록으로 끝내지 않는다). 재기동 자체는 됐으면 2 — 포털 게이트가 중단하지 않게.
  if [ "$_upd_fail" = 1 ]; then [ "$_restart_fail" = 1 ] && rc=1 || rc=2; fi
  if [ "$rc" = 2 ]; then
    echo "  · ✗ $name: 갱신(git pull) 실패 — 서비스 자체는 정상이다  [$(date '+%H:%M:%S')]"
    show_cause "$name" "$(cat "$tmp")"
  elif [ "$rc" -ne 0 ]; then
    echo "  · ✗ $name 실패 (rc=$rc)  [$(date '+%H:%M:%S')]"
    show_cause "$name" "$(cat "$tmp")"
  else
    echo "  · ✓ $name 완료  [$(date '+%H:%M:%S')]"
  fi
  rm -f "$tmp"
  return "$rc"
}

# 1) 포털 먼저 — 실패하면 나머지 손대지 않고 중단(프론트를 확인된 상태로 유지)
PULL_FAILED=""
if [ "$HAS_PORTAL" = 1 ]; then
  restart_svc "$PORTAL"; _prc=$?
  case "$_prc" in
    0) echo "  ✓ portal 재기동·health OK" ;;
    # 2 = 갱신만 실패하고 포털은 정상이다. 이걸로 중단하면 GitHub 이 안 닿는 박스에서 나머지 서비스가 손도 닿지 않는다(4라운드).
    2) echo "  ⚠ portal 갱신(git pull) 실패 — 포털 자체는 정상이라 나머지($REST)는 계속한다. 종료코드는 끝에서 올린다."
       PULL_FAILED="$PULL_FAILED $PORTAL" ;;
    *) echo "  ✗ portal 재기동 실패 → 나머지($REST)는 건드리지 않고 중단. 포털 로그 확인 후 재시도하세요."
       exit 1 ;;
  esac
fi

# 2) 나머지 — 하나 실패해도 계속, 끝에 요약(포털은 이미 확인됨)
FAILED=""
for s in $REST; do
  restart_svc "$s"; _rc=$?
  case "$_rc" in 0) ;; 2) PULL_FAILED="$PULL_FAILED $s" ;; *) FAILED="$FAILED $s" ;; esac
done

echo
[ -n "$SKIPPED_RESTART" ] && echo "▶ 재기동 생략(마지막 기동 뒤 변경 없음·살아 있음):$SKIPPED_RESTART  — 전부 재기동하려면 HWAX_RESTART_ALL=1"
echo "▶ 최종 상태:"; "$SVC" status $TARGETS || true
[ -n "$PULL_FAILED" ] && echo "▶ ⚠ 갱신(git pull) 실패:$PULL_FAILED  — 서비스는 정상이다(옛 코드로 돈다). 네트워크·원격을 확인하고 다시 돌려라."
if [ -n "$FAILED" ]; then
  echo "▶ ⚠ 실패(포털 제외):$FAILED  — 포털은 정상. 개별 재시도:  $SVC up --update <이름>"
  exit 1
fi
[ -n "$PULL_FAILED" ] && exit 1
echo "▶ 완료 — report-archive 제외 전부 최신화·재기동."
