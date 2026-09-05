#!/usr/bin/env bash
# /data 이관 실행기 래퍼 — 아직 현행 경로에 있는 데이터만 /data 로 옮긴다(멱등·자동 롤백). 본체 datamigrate.py.
#
#   ./infra/scripts/data-migrate.sh plan [svc...]         # 무엇을 옮길지·막힌 이유 — 변경 없음
#   ./infra/scripts/data-migrate.sh run  [svc...] --yes   # 실행(서비스 단위 정지 창 수분). HWAX_DATA_ROOT 필요
#   ./infra/scripts/data-migrate.sh rollback <svc> [--class C]
#   ./infra/scripts/data-migrate.sh resume-crons          # 비정상 종료 뒤 크론 복원
#
# cae00 은 infra/.env 에 HWAX_DATA_ROOT=/data 한 줄만 넣으면 update-all 이 이걸 부른다(옵트인) — 이미 옮겨진 건 건너뛴다.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PY="$ROOT/backend/.venv/bin/python"; [ -x "$PY" ] || PY="$(command -v python3)"
exec "$PY" -u "$ROOT/infra/scripts/datamigrate.py" "$@"   # -u: 하위 스크립트 출력과 순서가 섞이지 않게
