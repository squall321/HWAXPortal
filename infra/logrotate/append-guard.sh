#!/usr/bin/env bash
# logrotate prerotate 가드 — 그 로그를 쥔 프로세스가 모두 O_APPEND 일 때만 회전을 허락한다(copytruncate 의 NUL 구멍 방지)
#
# 쓰는 곳: infra/logrotate/hwax.conf.tmpl 의 (C). 인자 $1 은 logrotate 가 넘기는 로그의 절대경로다.
# 판정: /proc/<pid>/fd/* 가 그 파일을 가리키면 /proc/<pid>/fdinfo/<fd> 의 flags(8진)에 02000(O_APPEND)이 있어야 한다.
# 하나라도 없으면 exit 1 — logrotate 는 그 로그만 건너뛴다(nosharedscripts). 아무도 안 쥐었으면 0(회전해도 안전하다).
# 왜: 기동 스크립트는 10-17 결정 16 으로 >> · "ab" 로 열게 고쳤지만, 박스마다 그 전에 뜬 프로세스가 옛 > · "wb" fd 를 쥐고
# 남아 있을 수 있다. 그런 쓰기자를 truncate 하면 다음 write 가 옛 오프셋으로 가서 파일 앞이 NUL 구멍이 된다.
set -u
f="$(readlink -f -- "${1:?로그 경로}")" || exit 1
pat="$(printf '%s' "$f" | sed 's/[][*?\\]/\\&/g')"      # find -lname 은 셸 패턴이다 — 경로의 패턴 글자를 글자로
bad=""
while IFS= read -r fd; do
  pid="${fd#/proc/}"; pid="${pid%%/*}"; n="${fd##*/}"
  flags="$(awk '/^flags:/{print $2; exit}' "/proc/$pid/fdinfo/$n" 2>/dev/null)"
  [ -n "$flags" ] || continue                             # 그 사이 닫혔다
  (( (8#$flags & 8#2000) != 0 )) && continue
  case " $bad " in *" $pid "*) ;; *) bad="$bad $pid" ;; esac   # fd 1 · 2 가 같은 파일이면 pid 는 한 번만
done < <(find /proc/[0-9]*/fd -maxdepth 1 -lname "$pat" 2>/dev/null)
if [ -n "$bad" ]; then
  echo "append-guard: $f 를 O_APPEND 없이 쥔 프로세스(pid$bad) — 이번 회전을 건너뛴다(그 쓰기자가 >> 로 다시 뜨면 풀린다)" >&2
  exit 1
fi
exit 0
