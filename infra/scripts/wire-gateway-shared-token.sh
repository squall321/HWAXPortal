#!/usr/bin/env bash
# RA 연결 토큰 기능의 1회 배선 — 게이트웨이 GW_TOKEN 을 포털 backend/.env 에 복사하고,
# 게이트웨이 config 에 portal.api_base 를 넣는다. 몇 번을 다시 돌려도 안전(멱등).
#
#   ./infra/scripts/wire-gateway-shared-token.sh
#
# 왜 필요한가: 게이트웨이가 사용자별 RA 토큰을 포털 /internal/connections 에서 읽는데,
# 그 인증(공유 시크릿)과 포털 주소가 양쪽 비추적 파일에 있어 손으로 옮기다 틀리기 쉽다.
# 실행 후 포털·게이트웨이 재기동이 필요하다(둘 다 기동 시점에 읽는다).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PARENT="$(dirname "$ROOT")"
GWDIR=""
for c in "$PARENT/HWAXMcpGateway" "$HOME/Projects/HWAXMcpGateway" "$HOME/claude/HWAXMcpGateway"; do
  [ -f "$c/gateway_config.json" ] && { GWDIR="$c"; break; }
done
[ -n "$GWDIR" ] || { echo "✗ HWAXMcpGateway/gateway_config.json 을 찾지 못했다 — 게이트웨이 프로비저닝 먼저."; exit 1; }

python3 - "$ROOT" "$GWDIR" <<'PY'
import json
import sys
from pathlib import Path

root, gwdir = Path(sys.argv[1]), Path(sys.argv[2])
cfg_path = gwdir / "gateway_config.json"
cfg = json.loads(cfg_path.read_text())
tok = cfg["_gateway"]["token"]

# ① 게이트웨이 config 에 portal.api_base (없을 때만)
portal = cfg.setdefault("portal", {})
if portal.get("api_base"):
    print(f"  · 게이트웨이 portal.api_base 이미 있음: {portal['api_base']}")
else:
    portal["api_base"] = "http://127.0.0.1:8723"
    cfg_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")
    print("  ✓ 게이트웨이 portal.api_base = http://127.0.0.1:8723 추가 — 게이트웨이 재기동 필요")

# ② 포털 backend/.env 에 GATEWAY_SHARED_TOKEN (없으면 파일째 생성, 있으면 덧붙임, **다르면 갈아 끼움**)
# 종전엔 '있기만 하면' 건너뛰었다 — GW_TOKEN 이 회전되면(provision-config ROTATE_GW_TOKEN·.bak 없음) 두 값이 어긋난 채
# 남아 포털이 403 을 주고, 게이트웨이는 사용자별 RA 위임을 못 해 RA 쓰기를 거부한다(update-all §6 'RA 사용자 위임').
import re
env_path = root / "backend" / ".env"
txt = env_path.read_text() if env_path.exists() else ""
line_re = re.compile(r"^([ \t]*(?:export[ \t]+)?GATEWAY_SHARED_TOKEN=)(.*)$", re.M)
m = None
for m in line_re.finditer(txt):
    pass                                   # 마지막 활성 줄이 이긴다(.env 읽기 규칙)
if m is not None and m.group(2).strip().strip('"').strip("'") == tok:
    print("  · 포털 GATEWAY_SHARED_TOKEN 이미 배선됨(게이트웨이 GW_TOKEN 과 같다)")
elif m is not None:
    env_path.write_text(txt[:m.start(2)] + tok + txt[m.end(2):])
    print("  ✓ 포털 GATEWAY_SHARED_TOKEN 이 게이트웨이 GW_TOKEN 과 달라 갈아 끼웠다 — 포털 재기동 필요")
else:
    with env_path.open("a") as f:
        if txt and not txt.endswith("\n"):
            f.write("\n")
        f.write("# 게이트웨이 /internal/connections 인증(공유 시크릿 = 게이트웨이 GW_TOKEN)\n")
        f.write(f"GATEWAY_SHARED_TOKEN={tok}\n")
    print(f"  ✓ 포털 backend/.env 에 GATEWAY_SHARED_TOKEN 기록({'기존 파일에 추가' if txt else '새 파일 생성'}) — 포털 재기동 필요")
PY
echo "완료. 반영: 포털(instance stop hwax_portal → start.sh) + 게이트웨이 재기동."
