#!/usr/bin/env bash
# 박스 간 데이터 동기화 래퍼 — 레지스트리(services.yaml data:)를 읽어 기존 merge 스크립트 + rsync(ssh) 로 잇는다.
#
# D0(2026-09-05) 범위: **읽기 전용 verbs 만** — status · keys-check · verify. 적용 verbs(push·pull·mirror·
# rollback·prune)는 D5 에서 배선한다(docs/data-migration/PLAN.md §8). 지금 부르면 3 으로 거부한다.
#
#   ./infra/scripts/db-sync.sh status [svc]            # 레지스트리 × 원장 last-applied 한 표
#   ./infra/scripts/db-sync.sh keys-check [svc]        # keys_with 파일의 sha256 지문 12자(원문 절대 출력 안 함)
#   ./infra/scripts/db-sync.sh verify <manifest.json>  # 스냅샷 manifest 의 파일 sha256 전수 검증
#
# 원장: ${HWAX_DATA_ROOT:-/data}/hwax/state/db-sync/{journal.jsonl,last-applied/}  (plan §2 state/)
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PY="$ROOT/backend/.venv/bin/python"; [ -x "$PY" ] || PY="$(command -v python3)"
VERB="${1:-}"; shift || true
case "$VERB" in
  status|keys-check|verify) exec "$PY" "$ROOT/infra/scripts/dbsync.py" "$VERB" "$@" ;;
  push|pull|mirror|rollback|prune|apply|snapshot|stage)
    echo "✗ '$VERB' 는 D5 에서 배선된다(PLAN §8) — D0 는 status·keys-check·verify 만." >&2; exit 3 ;;
  *) sed -n '2,13p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 2 ;;
esac
