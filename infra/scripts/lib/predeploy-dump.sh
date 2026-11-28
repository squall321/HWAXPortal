#!/usr/bin/env bash
# update-all §1b 가 AIDataHub 배포 전 덤프를 새로 뜰지, 그날 일일 덤프를 롤백 지점으로 다시 쓸지 정한다(docs/request-1125 SE-2 ③ · SYNCEFF-4)
#
# 왜 — §1b 의 AIDataHub 덤프가 27 ~ 28분 · 11 GB 였고, 03:30 일일 덤프 두어 시간 뒤 같은 DB 를 다시 떴다(그 사이 WAL 51 kB). 사용자 결정 11-28 —
# 그날(박스 시각) 일일 덤프가 온전하고 이번에 받을 AIDataHub 판에 alembic 이관이 없으면 그것을 배포 전 롤백 지점으로 쓴다. 이관이 있거나 일일 덤프가
# 없 · 낡 · 깨졌거나, 그 어느 것을 볼 수 없으면(모름) 지금처럼 새로 뜬다 — 모름을 없음으로 읽지 않는다.
# 이관이 없는 배포는 DB 를 건드리지 않아 03:30 뒤의 쓰기를 잃을 일이 없고, 이관이 있으면 바로 앞의 덤프가 있어야 되돌려도 잃는 것이 없다.
#
#   . infra/scripts/lib/predeploy-dump.sh
#   hwax_predeploy_dump_decide <AIDataHub 리포> <aidh daily 폴더> <박스> [<손잡이 값>]
#
# 한 줄을 낸다(탭으로 가른다). **끝 코드는 늘 0** — 판정은 글로만 준다. set -e 아래 `x="$(f)"` 는 f 가 1 이면 조용히 끝나고(메모 set -e 아래
# 상태 반환 함수), 끝 코드로 판정하면 '모름' 과 '없음' 이 한 값이 된다.
#   reuse  <파일 절대 경로>  <덤프 시각 YYYY-MM-DD HH:MM:SS>  <까닭>
#   fresh  <갈래>  <까닭>           갈래 = knob(손잡이) · none(그날 덤프 없음) · stale(낡음) · nosha(sha256 짝 없음 — 아직 뜨는 중이거나 끝나지 못함)
#                                          · broken(깨짐) · migration(받을 판에 이관) · unknown(볼 수 없음)
# 손잡이 — fresh 면 늘 새로 뜬다. 비었거나 auto 면 판정한다. 그 밖의 값은 모르는 값이라 새로 뜬다(knob).
# 이름 꼴은 backup-local.sh 의 pg_backup 과 같다 — <svc>-<박스>-<YYYYmmdd-HHMMSS>.sql.gz, 이 실행이 뜬 것은 끝에 -pre. 일일 덤프는 -pre 가 아닌 것이다.
# 이관은 deploy-all git_update 와 같은 판을 본다 — 지금 가지의 origin/<가지>(fetch 뒤)와 HEAD 사이에 api_server/alembic/versions 가 바뀌었는가.
# 바깥 명령의 출력은 먼저 받고 본다(파이프 끝의 grep -q 가 SIGPIPE 로 '없다' 를 내던 판정 파이프 함정).

HWAX_AIDH_MIGRATIONS_DIR="api_server/alembic/versions"

hwax_predeploy_dump_decide() {
  local repo="$1" daily="$2" box="$3" knob="${4:-}"
  local today f best="" any="" exp sum br fe diff ts
  case "$knob" in
    ''|auto) ;;
    fresh) printf 'fresh\tknob\tHWAX_PREDEPLOY_DUMP=fresh — 늘 새로 뜬다\n'; return 0 ;;
    *) printf 'fresh\tknob\tHWAX_PREDEPLOY_DUMP 의 값(%s)을 모른다 — fresh · auto 만 받는다. 새로 뜬다\n' "$knob"; return 0 ;;
  esac
  today="$(date +%Y%m%d)"
  # glob 은 이름 차례로 펼친다 — 시각이 이름에 있어 마지막이 가장 새 것이다. -pre(update-all 이 배포 전에 뜬 것) · pre-merge-*(병합 전 덤프)는 꼴이 달라 빠진다.
  for f in "$daily/aidh-$box-"[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9][0-9][0-9].sql.gz; do
    [ -e "$f" ] || continue
    any="$f"
    case "$(basename "$f")" in "aidh-$box-$today-"*) best="$f" ;; esac
  done
  if [ -z "$best" ]; then
    if [ -n "$any" ]; then
      ts="$(basename "$any" .sql.gz)"; ts="${ts#aidh-"$box"-}"
      printf 'fresh\tstale\t그날(%s) 일일 덤프가 없다 — 가장 새 것이 %s 다\n' "${today:0:4}-${today:4:2}-${today:6:2}" "${ts:0:4}-${ts:4:2}-${ts:6:2}"
    else
      printf 'fresh\tnone\t일일 덤프가 없다(%s)\n' "$daily"
    fi
    return 0
  fi
  ts="$(basename "$best" .sql.gz)"; ts="${ts#aidh-"$box"-}"
  ts="${ts:0:4}-${ts:4:2}-${ts:6:2} ${ts:9:2}:${ts:11:2}:${ts:13:2}"
  if [ ! -s "$best" ]; then
    printf 'fresh\tbroken\t그날 일일 덤프 %s 가 0바이트다\n' "$(basename "$best")"; return 0
  fi
  if [ ! -f "$best.sha256" ]; then
    printf 'fresh\tnosha\t그날 일일 덤프 %s 에 sha256 짝이 없다(아직 뜨는 중이거나 끝나지 못했다)\n' "$(basename "$best")"; return 0
  fi
  exp="$(head -c 200 -- "$best.sha256" 2>/dev/null | tr -d '[:space:]')" || exp=""
  if [[ ! "$exp" =~ ^[0-9a-f]{64}$ ]]; then
    printf 'fresh\tbroken\t그날 일일 덤프 %s 의 sha256 파일이 꼴이 아니다\n' "$(basename "$best")"; return 0
  fi
  # 이관 — sha256 다시 셈(11 GB 에 수십 초)보다 싸서 먼저 본다
  br="$(git -C "$repo" rev-parse --abbrev-ref HEAD 2>/dev/null)" || br=""
  if [ -z "$br" ] || [ "$br" = HEAD ]; then
    printf 'fresh\tunknown\tAIDataHub 리포의 가지를 모른다(%s) — 받을 판의 이관을 볼 수 없다\n' "${br:-git 실패}"; return 0
  fi
  local to=(); command -v timeout >/dev/null 2>&1 && to=(timeout 120)     # 프록시에 걸린 fetch 가 §1b 를 붙들지 않게
  fe="$(${to[@]+"${to[@]}"} git -C "$repo" fetch origin "$br" --quiet 2>&1)" \
    || { printf 'fresh\tunknown\tAIDataHub git fetch 실패 — 받을 판의 이관을 볼 수 없다(%s)\n' "${fe%%$'\n'*}"; return 0; }
  diff="$(git -C "$repo" diff --name-only HEAD "origin/$br" -- "$HWAX_AIDH_MIGRATIONS_DIR" 2>/dev/null)" \
    || { printf 'fresh\tunknown\tAIDataHub HEAD 와 origin/%s 를 견주지 못했다 — 받을 판의 이관을 볼 수 없다\n' "$br"; return 0; }
  if [ -n "$diff" ]; then
    printf 'fresh\tmigration\t받을 AIDataHub 판에 이관 파일 %s\n' \
      "$(printf '%s\n' "$diff" | awk -F/ 'NF{n++; if (n <= 3) s = s (n > 1 ? ", " : "") $NF} END{printf "%d개(%s%s)", n, s, (n > 3 ? " …" : "")}')"
    return 0
  fi
  sum="$(sha256sum -- "$best" 2>/dev/null)" || sum=""
  sum="${sum%% *}"
  if [ "$sum" != "$exp" ]; then
    printf 'fresh\tbroken\t그날 일일 덤프 %s 의 sha256 이 짝 파일과 다르다\n' "$(basename "$best")"; return 0
  fi
  printf 'reuse\t%s\t%s\t그날 일일 덤프 · sha256 맞음 · 받을 AIDataHub 판(origin/%s)에 이관 없음\n' "$best" "$ts" "$br"
  return 0
}
