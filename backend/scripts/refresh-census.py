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


def health_down(url: str = "http://127.0.0.1:9110") -> set[str]:
    """게이트웨이 `/health` 가 내려갔다고 적은 백엔드. 못 읽으면 빈 집합 — 이유를 붙이는 데만 쓰고 판정은 도구 수로 한다."""
    try:
        h = json.loads(urllib.request.urlopen(f"{url}/health", timeout=10).read())
    except (OSError, ValueError):
        return set()
    return {k for k, v in (h.get("backends") or {}).items() if v is False}


def compare(old: dict, fresh: dict) -> dict:
    """기록 → 지금. 사라진 도구를 **백엔드째 안 보이는 것**과 정말 없어진 것으로 가른다.

    ⚠ 백엔드 하나가 내려가면 그 도구가 통째로 tools/list 에서 빠진다(dev 10-17 — reportarchive ·
    smart-twin-cluster 89종). 다른 백엔드가 그만큼 늘면 '크게 줄면 막는다' 를 지나쳐, 갱신이 내려간
    백엔드의 도구를 고정물에서 조용히 지우고 그 뒤 가드는 없는 도구로 친다."""
    was = {t["name"]: t.get("backend") for t in old["tools"]}
    now = {t["name"] for t in fresh["tools"]}
    live = {t.get("backend") for t in fresh["tools"]}
    absent: dict[str, list[str]] = {}
    gone: list[str] = []
    for n in sorted(set(was) - now):
        b = was[n]
        (absent.setdefault(b, []) if b and b not in live else gone).append(n)
    dry_was = {t["name"] for t in old["tools"] if t["dry_run"]}
    dry_now = {t["name"] for t in fresh["tools"] if t["dry_run"]}
    return {"added": sorted(now - set(was)), "gone": gone, "absent": absent,
            "dry_added": sorted(dry_now - dry_was),
            # 안 보이는 도구는 dry_run 을 잃은 게 아니다 — 위 두 갈래에 이미 있다.
            "dry_removed": sorted((dry_was - dry_now) & now)}


def _age(generated) -> str:
    try:
        return f"{(datetime.date.today() - datetime.date.fromisoformat(str(generated))).days}일 전"
    except ValueError:
        return "날짜 모름"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="갱신하지 않고 어긋난 것만 보고")
    ap.add_argument("--force", action="store_true",
                    help="도구가 크게 줄거나 백엔드째 안 보여도 덮어쓴다(부분 실패 · 내려감이 아님을 확인했을 때)")
    a = ap.parse_args()

    fresh = pull()
    # ⚠ 0종을 고정물로 쓰면 그 뒤 인구조사 가드가 **전부 통과한다**(비교 대상이 없다).
    if not fresh["tools"]:
        print("✗ 게이트웨이에서 도구를 하나도 못 받았다 — 고정물을 건드리지 않는다")
        return 2
    if not CENSUS.is_file():
        # ⚠ `--check` 는 **절대 안 쓴다.** 이 파일 머리말이 "갱신은 사람이 돌린다 —
        # 테스트가 자동으로 뽑으면 어긋난 것이 조용히 정상이 된다" 인데, 고정물이 없을 때
        # `--check` 가 만들어 버리면 그 규칙이 정확히 깨진다(2026-09-15 4차 감사).
        if a.check:
            print("✗ 고정물이 없다 — `--check` 는 만들지 않는다. 사람이 인자 없이 돌려라")
            return 1
        CENSUS.write_text(json.dumps(fresh, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"✓ 새로 만들었다 — {fresh['gateway_tools']}종")
        return 0

    old = json.loads(CENSUS.read_text(encoding="utf-8"))
    was = {t["name"] for t in old["tools"]}
    now = {t["name"] for t in fresh["tools"]}
    c = compare(old, fresh)
    down = health_down()
    print(f"기록 {len(was)}종({old.get('generated')}, {_age(old.get('generated'))}) → 지금 {len(now)}종")
    for label, s in (("새로 생긴 도구", c["added"]), ("사라진 도구", c["gone"]),
                     ("dry_run 이 생긴 도구", c["dry_added"]),
                     ("dry_run 이 없어진 도구", c["dry_removed"])):
        if s:
            print(f"  ⚠ {label} {len(s)}: {s[:12]}")
    for b, names in sorted(c["absent"].items()):
        why = "게이트웨이 /health 가 내려갔다고 한다" if b in down else "도구가 하나도 안 보인다(내려갔거나 빠졌다)"
        print(f"  ⚠ 백엔드째 안 보임 — {b} {len(names)}종: {why}")
    if a.check:
        return 1 if any(c.values()) else 0
    # ⚠ **안 보이는 백엔드의 도구를 지우지 않는다**(compare 머리말). 띄운 뒤 다시 돌리는 게 맞다.
    if c["absent"] and not a.force:
        print(f"✗ 백엔드째 안 보이는 도구가 있다({', '.join(sorted(c['absent']))}) — 지금 갱신하면 그 도구가 "
              f"고정물에서 빠진다. 띄운 뒤 다시 돌리거나, 정말 뺀 백엔드면 --force")
        return 2
    # ⚠ **줄어든 것을 그냥 덮어쓰지 않는다.** 부분 실패로 소수만 받아 고정물을 줄이면,
    # 그 뒤 가드는 줄어든 목록을 기준으로 삼아 조용히 통과한다. 크게 줄면 사람이 본다.
    if len(now) < len(was) * 0.9 and not a.force:
        print(f"✗ {len(was)}종 → {len(now)}종으로 **크게 줄었다**. 부분 실패일 수 있어 "
              f"덮어쓰지 않는다 — 맞으면 --force 로 다시 돌려라")
        return 2
    CENSUS.write_text(json.dumps(fresh, ensure_ascii=False, indent=1), encoding="utf-8")
    print("✓ 갱신했다 — **models.py 의 목록도 사람이 다시 본다**"
          "(MUST_GATE·DRY_RUN_TOOLS·WARN_EXACT)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
