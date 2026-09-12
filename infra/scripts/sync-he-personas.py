#!/usr/bin/env python3
# HE팀 MCP 운영자 페르소나를 AIDataHub 에 동기화한다 — 정본 infra/personas/he-team.json, 기본은 미리보기
"""HE팀 페르소나 동기화.

  python3 infra/scripts/sync-he-personas.py                 # 미리보기 — 무엇이 바뀌는지만 본다
  python3 infra/scripts/sync-he-personas.py --apply         # 반영
  python3 infra/scripts/sync-he-personas.py --show he-calc-laminate   # 한 명의 system_prompt 를 찍는다

게이트웨이 /tools-map(토큰 불필요)으로 앱 도구·영역·라벨을 받아, 정본에 적은 도구 이름을 대조하고
system_prompt 를 만든 뒤 AIDataHub REST(/api/agents)로 만들거나 고친다. 바뀐 칸만 PATCH 한다 —
안 바뀐 것까지 쓰면 에이전트 이력(history)이 매번 쌓인다.

앱이 게이트웨이에 없으면 그 페르소나는 건너뛴다(dev 의 arp·odb-hub). cae00 에서 같은 명령을 돌리면
그 박스 게이트웨이에 붙은 앱으로 만들어진다.

  GATEWAY_HTTP_BASE  기본 http://127.0.0.1:9110
  AIDH_HTTP_BASE     기본 http://127.0.0.1:8001
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "infra" / "personas" / "he-team.json"
GATEWAY = os.environ.get("GATEWAY_HTTP_BASE", "http://127.0.0.1:9110").rstrip("/")
AIDH = os.environ.get("AIDH_HTTP_BASE", "http://127.0.0.1:8001").rstrip("/")
ACTOR = "he-team-sync"

# 에이전트서버가 페르소나 역할을 이만큼만 싣는다(app.py _persona_meta ROLE_MAX). 넘으면 뒤가 조용히
# 잘리므로 여기서 먼저 멈춘다 — 잘린 페르소나는 '답하는 법' 이 통째로 빠진 채 돈다.
PROMPT_MAX = 8000
NO_GUIDE = "<!-- no-tool-guide -->"   # AIDataHub 가 지식카드 도구 안내를 덧붙이지 않게 하는 표지
MANAGED = ("name", "description", "common_tags", "sample_queries", "system_prompt", "response_config")


def _http(method: str, url: str, body: dict | None = None) -> tuple[int, object]:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json", "X-User-Id": ACTOR})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode("utf-8")
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:300]


def _bullets(items: list[str]) -> list[str]:
    return [f"- {x}" for x in items]


def build_prompt(p: dict, app_labels: list[str], n_tools: int, tool_map: list[tuple[str, list[str]]]) -> str:
    """정본 한 명 → system_prompt. 모든 페르소나가 같은 뼈대를 쓴다(읽는 쪽이 칸을 예상할 수 있게)."""
    lines = [NO_GUIDE, f"# {p['name']}",
             f"HE팀 MCP 운영자 — {' · '.join(app_labels)} 도구 {n_tools}개를 직접 호출해 일한다.",
             "", "## 역할", p["mission"],
             "", "## 할 수 있는 일", *_bullets(p["can"]),
             "", "## 기본 작업 순서", *[f"{i}. {x}" for i, x in enumerate(p["workflow"], 1)],
             "", "## 알아 둘 개념", *_bullets(p["concepts"]),
             "", "## 틀리기 쉬운 것", *_bullets(p["pitfalls"])]
    if p["writes"] or p["confirm"]:
        lines += ["", "## 상태를 바꾸는 도구"]
        if p["writes"]:
            lines.append(f"- 사용자가 그 작업을 요청했을 때만 부른다 — {', '.join(p['writes'])}.")
        if p["confirm"]:
            lines.append("- 되돌리기 어렵다. 무엇이 바뀌는지 먼저 말하고 확인을 받은 뒤 부른다 — "
                         f"{', '.join(p['confirm'])}.")
    if p.get("tool_map"):
        # 사전 지식이 아직 얇은 앱(cae00 전용)은 도구 이름이라도 영역별로 준다.
        lines += ["", "## 도구 지도", *[f"- {label}: {', '.join(names)}" for label, names in tool_map]]
    lines += ["", "## 답하는 법",
              "- 도구가 돌려준 값·ID·경로만 근거로 쓴다. 도구가 주지 않은 수치·ID 를 지어내지 않는다.",
              "- 어떤 도구를 어떤 인자로 불렀는지 답 끝에 짧게 밝힌다.",
              "- 바인딩 목록에 없는 이 앱 도구는 search_tools 로 인자를 확인하고 invoke_tool 로 부른다.",
              "- 이 앱으로 안 되는 요청이면 그렇다고 말하고, 맞는 앱·전문가를 list_tool_apps·recommend_agents 로 안내한다."]
    return "\n".join(lines)


def plan(spec: dict, tmap: dict) -> tuple[list[dict], list[str], list[str]]:
    """정본 + 게이트웨이 → 올릴 페이로드 목록, 건너뛴 사유, 오류."""
    tool_app: dict = tmap.get("map") or {}
    areas: dict = tmap.get("areas") or {}
    area_label = {a["area"]: a.get("label") or a["area"] for a in (tmap.get("area_meta") or []) if a.get("area")}
    app_label = {a["app"]: (a.get("label") or a["app"]) for a in (tmap.get("apps") or []) if a.get("app")}
    by_app: dict[str, list[str]] = {}
    for t, a in tool_app.items():
        by_app.setdefault(a, []).append(t)

    out, skipped, errors = [], [], []
    for p in spec["personas"]:
        key = p["key"]
        grp = key.split("-")[1] if key.count("-") >= 2 else ""
        if not key.startswith("he-") or grp not in spec["groups"]:
            errors.append(f"{key}: 키는 he-<묶음>-<앱> 이고 묶음은 groups 에 있어야 한다")
            continue
        missing = [a for a in p["apps"] if a not in by_app]
        if missing:
            skipped.append(f"{key}: 이 게이트웨이에 앱이 없다({', '.join(missing)}) — 붙어 있는 박스에서 돌리면 생긴다")
            continue
        tools = sorted(t for a in p["apps"] for t in by_app[a])
        for fld in ("key_tools", "writes", "confirm"):
            bad = [n for n in p[fld] if n not in tools]
            if bad:
                errors.append(f"{key}: {fld} 에 이 앱에 없는 도구 — {', '.join(bad)}")
        both = sorted(set(p["writes"]) & set(p["confirm"]))
        if both:
            errors.append(f"{key}: writes 와 confirm 에 같이 있다 — {', '.join(both)}")
        tool_map: dict[str, list[str]] = {}
        for t in tools:
            tool_map.setdefault(area_label.get(areas.get(t, ""), "미분류"), []).append(t)
        labels = [app_label.get(a, a) for a in p["apps"]]
        prompt = build_prompt(p, labels, len(tools), sorted(tool_map.items()))
        if len(prompt) > PROMPT_MAX:
            errors.append(f"{key}: system_prompt {len(prompt)}자 > {PROMPT_MAX}자 — 에이전트서버가 뒤를 자른다. 문구를 줄여라")
        out.append({
            "agent_type": key,
            "name": p["name"],
            "description": p["summary"],
            "common_tags": ["HE팀", "MCP 운영자", spec["groups"][grp], *labels],
            "sample_queries": p["samples"],
            "system_prompt": prompt,
            "data_types": [],
            "response_config": {"persona_kind": "mcp_operator", "mcp_apps": p["apps"],
                                "key_tools": p["key_tools"],
                                "managed_by": "HWAXPortal/infra/personas/he-team.json"},
        })
    return out, skipped, errors


def main() -> int:
    ap = argparse.ArgumentParser(description="HE팀 MCP 운영자 페르소나를 AIDataHub 에 동기화")
    ap.add_argument("--apply", action="store_true", help="실제로 쓴다(없으면 미리보기)")
    ap.add_argument("--show", metavar="KEY", help="이 페르소나의 system_prompt 를 찍고 끝낸다")
    args = ap.parse_args()

    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    st, tmap = _http("GET", f"{GATEWAY}/tools-map")
    if st != 200 or not isinstance(tmap, dict) or not tmap.get("map"):
        print(f"✗ 게이트웨이 /tools-map 을 못 읽었다({st}) — {GATEWAY}", file=sys.stderr)
        return 2
    rows, skipped, errors = plan(spec, tmap)
    for s in skipped:
        print(f"  · 건너뜀 {s}")
    if errors:
        for e in errors:
            print(f"✗ {e}", file=sys.stderr)
        return 2

    if args.show:
        row = next((r for r in rows if r["agent_type"] == args.show), None)
        if not row:
            print(f"✗ {args.show} 는 이 박스에서 만들 수 없다(정본에 없거나 건너뜀)", file=sys.stderr)
            return 2
        print(row["system_prompt"])
        print(f"\n({len(row['system_prompt'])}자)")
        return 0

    created = updated = same = 0
    for r in rows:
        key = r["agent_type"]
        st, cur = _http("GET", f"{AIDH}/api/agents/{key}")
        if st == 404:
            print(f"  + {key} 새로 만든다 ({len(r['system_prompt'])}자)")
            if args.apply:
                st2, res = _http("POST", f"{AIDH}/api/agents", r)
                if st2 not in (200, 201):
                    print(f"✗ {key} 생성 실패 {st2}: {res}", file=sys.stderr)
                    return 1
            created += 1
            continue
        if st != 200 or not isinstance(cur, dict):
            print(f"✗ {key} 조회 실패 {st}: {cur}", file=sys.stderr)
            return 1
        patch = {k: r[k] for k in MANAGED if cur.get(k) != r[k]}
        if not patch:
            same += 1
            continue
        print(f"  ~ {key} 고친다: {', '.join(patch)}")
        if args.apply:
            st2, res = _http("PATCH", f"{AIDH}/api/agents/{key}", patch)
            if st2 != 200:
                print(f"✗ {key} 수정 실패 {st2}: {res}", file=sys.stderr)
                return 1
        updated += 1

    # 정본에서 빠진 he-* 는 지우지 않고 알리기만 한다 — 사람이 만든 것일 수 있다.
    st, allrows = _http("GET", f"{AIDH}/api/agents")
    if st == 200 and isinstance(allrows, list):
        known = {p["key"] for p in spec["personas"]}
        stray = sorted(a.get("agent_type", "") for a in allrows
                       if str(a.get("agent_type", "")).startswith("he-") and a.get("agent_type") not in known)
        if stray:
            print(f"  ? 정본에 없는 he-* 에이전트 {len(stray)}명 — {', '.join(stray)} (지우지 않았다)")

    verb = "반영" if args.apply else "미리보기(--apply 로 반영)"
    print(f"{verb} — 새로 {created} · 고침 {updated} · 그대로 {same} · 건너뜀 {len(skipped)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
