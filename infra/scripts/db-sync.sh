#!/usr/bin/env bash
# 박스 간 데이터 동기화 래퍼 — 레지스트리(services.yaml data:)를 읽어 기존 merge 스크립트 + rsync(ssh) 로 잇는다.
#
# 읽기 전용 — status · keys-check · verify · ssh-check. 적용(D5, 11-24 짓기만 — 실제로 돌릴지는 사람이 정한다) — push · pull ·
# mirror · rollback. **적용 verbs 의 기본은 미리보기**다(무엇이 어디로 가는지만 찍고 아무것도 바꾸지 않는다). --apply 를 줘야 한다.
# mirror · rollback 은 이 박스의 DB 를 지우고 덮으니 '<이 박스>/<svc>' 를 한 번 더 친다(--confirm 또는 입력). rollback 은 적용한 박스에서.
#
#   ./infra/scripts/db-sync.sh status [svc]                     # 레지스트리 × 원장 last-applied 한 표
#   ./infra/scripts/db-sync.sh keys-check [svc]                 # keys_with 파일의 sha256 지문 12자(원문 절대 출력 안 함)
#   ./infra/scripts/db-sync.sh verify <manifest.json>           # 스냅샷 manifest 의 파일 sha256 전수 검증
#   ./infra/scripts/db-sync.sh ssh-check [box…]                 # infra/boxes.yaml 박스마다 ssh BatchMode · 원격 db-sync · 역할 · rsync
#   ./infra/scripts/db-sync.sh push   --svc <s> --to <box>   [--apply]     # 이 박스 daily 덤프 → 받는 박스 병합(publish)
#   ./infra/scripts/db-sync.sh pull   --svc <s> --from <box> [--apply]     # 같은 publish 를 받는 쪽에서
#   ./infra/scripts/db-sync.sh mirror --svc <s> --from <box> [--apply [--confirm <이 박스>/<s>]]   # prod → staging 통째 복원
#   ./infra/scripts/db-sync.sh rollback --svc <s> [--id <원장 id>] [--apply [--confirm <이 박스>/<s>]]   # 원장의 사전 백업으로
#
# 원장: ${HWAX_DATA_ROOT:-/data}/hwax/state/db-sync/{journal.jsonl,last-applied/}  (plan §2 state/) · 박스 목록: infra/boxes.yaml(gitignore)
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PY="$ROOT/backend/.venv/bin/python"; [ -x "$PY" ] || PY="$(command -v python3)"
VERB="${1:-}"; shift || true
case "$VERB" in
  # _ 로 시작하는 넷은 ssh 로 불리는 안쪽 verbs 다(_ping · _latest · _inbound · _apply) — 사람이 부를 일은 없다.
  status|keys-check|verify|ssh-check|push|pull|mirror|rollback|_ping|_latest|_inbound|_apply)
    exec "$PY" "$ROOT/infra/scripts/dbsync.py" "$VERB" "$@" ;;
  prune|apply|snapshot|stage)
    echo "✗ '$VERB' 는 아직 배선하지 않았다(PLAN §8 — D5 남은 줄)." >&2; exit 3 ;;
  *) sed -n '2,17p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 2 ;;
esac
