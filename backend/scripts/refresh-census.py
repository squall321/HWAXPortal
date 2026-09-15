#!/usr/bin/env python3
# 도구 인구조사를 **살아 있는 게이트웨이에서 다시 뽑는다**(docs/procedures/fixtures/catalog-census.json)
#
# 왜 이 스크립트가 있나. `models.py` 의 손으로 적은 목록(MUST_GATE·DRY_RUN_TOOLS·
# WARN_EXACT)은 465종 전수에서 뽑은 것이고 "게이트웨이가 바뀌면 다시 뽑는다" 고만
# 적혀 있었다 — **확인하는 코드가 없었다.** 그러면 새 파괴 도구가 게이트 없이 저장되고,
# dry_run 을 안 받는 도구에 dry_run 을 적어도 조용히 버려진다.
#
#   python3 backend/scripts/refresh-census.py            # 다시 뽑아 파일을 갱신
#   python3 backend/scripts/refresh-census.py --check    # 갱신 없이 어긋난 것만 보고
#
# ⚠ 갱신은 **사람이 돌린다.** 테스트가 자동으로 뽑으면 어긋난 것이 조용히 정상이 된다.
import argparse
import datetime
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CENSUS = ROOT / "docs" / "procedures" / "fixtures" / "catalog-census.json"


def _gateway_token() -> str:
    for c in (ROOT.parent / "HWAXMcpGateway", Path.home() / "Projects" / "HWAXMcpGateway",
              Path.home() / "claude" / "HWAXMcpGateway"):
        cfg = c / "gateway_config.json"
        if cfg.is_file():
            return json.loads(cfg.read_text())["_gateway"]["token"]
    raise SystemExit("게이트웨이 설정을 못 찾았습니다 — 이 박스에서 돌릴 수 없습니다")


def _rpc(url: str, headers: dict, body: dict, timeout: float = 90.0) -> str:
    req = urllib.request.Request(url, method="POST",
                                 data=json.dumps(body).encode(), headers=headers)
    return urllib.request.urlopen(req, timeout=timeout).read().decode()


def pull(url: str = "http://127.0.0.1:9110") -> dict:
    tok = _gateway_token()
    h = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json",
         "Accept": "application/json, text/event-stream"}
    req = urllib.request.Request(f"{url}/mcp", method="POST", headers=h,
        data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "census", "version": "1"}}}).encode())
    r = urllib.request.urlopen(req, timeout=30)
    h["mcp-session-id"] = r.headers.get("mcp-session-id")
    _rpc(f"{url}/mcp", h, {"jsonrpc": "2.0", "method": "notifications/initialized"}, 30)
    raw = _rpc(f"{url}/mcp", h, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    tools = []
    for ln in raw.splitlines():
        if ln.startswith("data: "):
            tools = json.loads(ln[6:]).get("result", {}).get("tools", [])
    tmap = json.loads(urllib.request.urlopen(f"{url}/tools-map", timeout=30).read())
    tmap = tmap.get("map") or tmap

    rows = []
    for t in sorted(tools, key=lambda x: x["name"]):
        props = (t.get("inputSchema") or {}).get("properties") or {}
        rows.append({
            "name": t["name"], "backend": tmap.get(t["name"]),
            "dry_run": "dry_run" in props, "args": len(props),
            "args_documented": sum(1 for v in props.values()
                                   if isinstance(v, dict)
                                   and str(v.get("description") or "").strip()),
        })
    old = json.loads(CENSUS.read_text(encoding="utf-8")) if CENSUS.is_file() else {}
    return {**{k: v for k, v in old.items() if k.startswith("_")},
            "generated": datetime.date.today().isoformat(),
            "gateway_tools": len(rows), "tools": rows}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="갱신하지 않고 어긋난 것만 보고")
    a = ap.parse_args()

    fresh = pull()
    if not CENSUS.is_file():
        CENSUS.write_text(json.dumps(fresh, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"✓ 새로 만들었다 — {fresh['gateway_tools']}종")
        return 0

    old = json.loads(CENSUS.read_text(encoding="utf-8"))
    was = {t["name"] for t in old["tools"]}
    now = {t["name"] for t in fresh["tools"]}
    dry_was = {t["name"] for t in old["tools"] if t["dry_run"]}
    dry_now = {t["name"] for t in fresh["tools"] if t["dry_run"]}
    print(f"기록 {len(was)}종({old.get('generated')}) → 지금 {len(now)}종")
    for label, s in (("새로 생긴 도구", now - was), ("사라진 도구", was - now),
                     ("dry_run 이 생긴 도구", dry_now - dry_was),
                     ("dry_run 이 없어진 도구", dry_was - dry_now)):
        if s:
            print(f"  ⚠ {label} {len(s)}: {sorted(s)[:12]}")
    if a.check:
        return 1 if (was != now or dry_was != dry_now) else 0
    CENSUS.write_text(json.dumps(fresh, ensure_ascii=False, indent=1), encoding="utf-8")
    print("✓ 갱신했다 — **models.py 의 목록도 사람이 다시 본다**"
          "(MUST_GATE·DRY_RUN_TOOLS·WARN_EXACT)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
