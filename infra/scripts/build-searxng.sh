#!/usr/bin/env bash
# SearxNG SIF 를 굽는다 — 온라인 박스에서 1회. 폐쇄망은 Drive 로 받는다.
#
# 왜 한 겹 더 굽는가.
#   공식 이미지의 searx 패키지는 venv 에 설치돼 있지 않고 /usr/local/searxng 에 놓여 있을
#   뿐이다. 도커는 WORKDIR 로 버티지만 apptainer 로 옮기면 그 전제가 깨진다. .pth 한 줄로
#   어느 프로세스에서든 잡히게 만든다(그래도 granian mp 워커는 못 잡아 Flask 로 띄운다 —
#   infra/scripts/searxng.sh 주석 참조).
set -euo pipefail
OUT="${1:-$HOME/serviceApptainers/searxng-fixed.sif}"
BASE="${SEARXNG_BASE_SIF:-$HOME/serviceApptainers/searxng.sif}"
APPT="$(command -v apptainer)"

[ -f "$BASE" ] || { echo "→ 원본 이미지 받기"; "$APPT" pull --force "$BASE" docker://searxng/searxng:latest; }

DEF="$(mktemp --suffix=.def)"
trap 'rm -f "$DEF"' EXIT
cat > "$DEF" <<DEFEOF
Bootstrap: localimage
From: $BASE

%post
    set -eux
    SP=\$(ls -d /usr/local/searxng/.venv/lib/python3.*/site-packages)
    echo /usr/local/searxng > "\$SP/zz-searxng.pth"
    /usr/local/searxng/.venv/bin/python -c "import searx; print('searx OK', searx.__file__)"
DEFEOF

"$APPT" build --force "$OUT" "$DEF"
echo "✓ $OUT"
echo "  설정: /data/hwax/secrets/searxng/{settings.yml,serve.py}  (없으면 아래 참고)"
echo "  기동: ./infra/scripts/services.sh up searxng"
