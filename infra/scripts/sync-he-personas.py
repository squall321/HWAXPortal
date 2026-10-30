#!/usr/bin/env python3
# HE팀 MCP 운영자 페르소나를 AIDataHub 에 동기화한다 — 정본 infra/personas/he-team.json, 기본은 미리보기
"""HE팀 페르소나 동기화.

  python3 infra/scripts/sync-he-personas.py                 # 미리보기 — 무엇이 바뀌는지만 본다
  python3 infra/scripts/sync-he-personas.py --apply         # 반영
  python3 infra/scripts/sync-he-personas.py --show he-calc-laminate   # 한 명의 system_prompt 를 찍는다

게이트웨이 /tools-map(토큰 불필요)으로 앱 도구·영역·라벨을 받아, 정본에 적은 도구 이름을 대조하고
system_prompt 를 만든 뒤 AIDataHub REST(/api/agents)로 만들거나 고친다. 바뀐 칸만 PATCH 한다 —
안 바뀐 것까지 쓰면 에이전트 이력(history)이 매번 쌓인다.

다른 앱과 이름이 겹치는 도구는 정본에 접두 이름(`<앱 키에서 하이픈을 뺀 것>_<이름>`)으로 적는다. 게이트웨이가 언제나 받는
이름이라 겹치는 상대가 붙어 있든 아니든 통과한다(plan 의 주석).

앱이 게이트웨이에 없으면 그 페르소나는 건너뛴다(dev 의 arp·odb-hub). cae00 에서 같은 명령을 돌리면
그 박스 게이트웨이에 붙은 앱으로 만들어진다. 선택 앱(페르소나의 optional)은 다르다 — 붙어 있으면 그 칸을 정본 뒤에 잇고,
없으면 빼고 만든다(건너뛰지 않는다. 미리보기에 '· 일부' 로 찍는다).

막지 않고 알리기만 하는 것이 둘 더 있다(docs/request-1030). 운영자 앱의 쓰기 꼴 도구(/tools-map 의 write) 가운데 writes · confirm
어디에도 없는 것은 '· 목록 밖 쓰기' 로(HP-53), 이 박스 AIDataHub 의 운영자가 모는 앱이 이 게이트웨이에 없는 것은 '! ' 로 찍는다(HP-51 —
update-all §2b 가 ⚠ 로 올린다). --apply 에서 저장 요청이 5xx 면 다시 읽어 저장됐는지 보고, 저장됐으면 알리고 이어 간다(AIDataHub AD-21).

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
LOOSE_SHOW = 8                         # 목록 밖 쓰기 도구를 몇 개까지 적나


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


def _saved_anyway(st: int, key: str, want: dict) -> bool:
    """저장 요청이 5xx 였는데 실제로는 저장됐나 — AIDataHub 가 저장(commit)한 뒤 응답을 만들다 500 을 낸다(AD-21, 10-28 실측). 그때 멈추면
    동기화가 첫 운영자에서 끝난다. 다시 읽어 보낸 칸이 그대로면 저장된 것으로 본다. 4xx 는 거절이라 저장되지 않았다."""
    if st < 500:
        return False
    st2, cur = _http("GET", f"{AIDH}/api/agents/{key}")
    return st2 == 200 and isinstance(cur, dict) and all(cur.get(k) == want[k] for k in MANAGED if k in want)


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


# 박스마다 붙은 앱이 다르다(cae00 에는 smart-twin-cluster 가 없다). 그 앱 몫의 칸은 페르소나의 optional 에 묶고,
# 앱이 이 게이트웨이에 붙어 있을 때만 정본 뒤에 잇는다. 없어도 그 페르소나는 건너뛰지 않는다.
_LISTS = ("can", "workflow", "concepts", "pitfalls", "samples", "key_tools", "writes", "confirm")


def _with_optional(p: dict, by_app: dict) -> tuple[dict, list[str]]:
    """정본 한 명 → 붙어 있는 선택 앱의 칸을 이은 사본, 빠진 선택 앱.

    `needs_tool` 이 있으면 앱이 붙어 있고 그 도구도 낼 때만 잇는다(노출 이름 또는 접두 별칭) — 같은 앱 안에서 켜고 끄는 기능을 그 칸에
    묶는다. MX 백서는 위키가 꺼진 박스에서 wiki_* 를 내지 않는다(MXWhitePaper MW-01) — 필수 칸에 두면 그 박스에서 동기화가 통째로
    멈춘다(한 명이 걸리면 아무도 안 올라간다). 같은 앱을 apps 에 두 번 넣지 않는다(도구 수 · 라벨이 두 번 센다)."""
    q = {**p, "apps": list(p["apps"]), **{f: list(p[f]) for f in _LISTS}}
    absent: list[str] = []
    for o in p.get("optional") or []:
        app, need = o["app"], o.get("needs_tool")
        names = by_app.get(app) or []
        if app not in by_app or (need and need not in names and f"{app.replace('-', '')}_{need}" not in names):
            absent.append(f"{app} 의 {need}" if app in by_app else app)
            continue
        if app not in q["apps"]:
            q["apps"].append(app)
        for f in _LISTS:
            q[f] += o.get(f) or []
    return q, absent


def plan(spec: dict, tmap: dict, notes: list[str] | None = None,
         warns: list[str] | None = None) -> tuple[list[dict], list[str], list[str]]:
    """정본 + 게이트웨이 → 올릴 페이로드 목록, 건너뛴 사유, 오류. notes 를 주면 선택 앱을 빼고 만든 페르소나를, warns 를 주면
    writes · confirm 어디에도 없는 쓰기 꼴 도구를 적는다(막지 않는다)."""
    tool_app: dict = tmap.get("map") or {}
    areas: dict = tmap.get("areas") or {}
    area_label = {a["area"]: a.get("label") or a["area"] for a in (tmap.get("area_meta") or []) if a.get("area")}
    app_label = {a["app"]: (a.get("label") or a["app"]) for a in (tmap.get("apps") or []) if a.get("app")}
    by_app: dict[str, list[str]] = {}
    for t, a in tool_app.items():
        by_app.setdefault(a, []).append(t)
    # 쓰기 꼴 판정은 게이트웨이 몫이다(/tools-map 의 write — 앱의 표지 → 이름 낱말). 읽기로 확인된 것(routine_read — 읽기 목록 ·
    # readOnlyHint)은 이름이 쓰기 꼴이어도 뺀다(get_record 의 record). write 칸이 없는 옛 게이트웨이면 보지 않았다고 한 줄 남긴다.
    write = set(tmap["write"]) if isinstance(tmap.get("write"), list) else None
    read_ok = set(tmap.get("routine_read") or [])
    if warns is not None and write is None:
        warns.append("목록 밖 쓰기 점검 건너뜀 — 이 게이트웨이 /tools-map 에 write 칸이 없다(옛 판)")

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
        p, absent = _with_optional(p, by_app)
        if absent and notes is not None:
            notes.append(f"{key}: {', '.join(absent)} 없이 만든다(선택 앱)")
        tools = sorted(t for a in p["apps"] for t in by_app[a])
        # 정본의 이름은 노출 이름이거나 **접두 별칭**(`<앱 키에서 하이픈을 뺀 것>_<이름>`)이면 맞다. 게이트웨이는 지금 붙은 백엔드끼리
        # 이름이 겹칠 때만 접두를 붙여 내놓으므로, 같은 도구의 노출 이름이 **다른 앱이 붙어 있느냐**로 뒤집힌다(ste 가 없는 박스는
        # list_jobs 를 맨 이름으로 낸다). 별칭은 겹치든 말든 게이트웨이가 언제나 받는다(gateway `alias_route`) — 노출 이름과만
        # 대조하면 겹치는 상대가 빠진 박스에서 동기화가 통째로 멈췄다. 반대 방향은 받지 않는다 — 접두로 노출된 도구를 맨 이름으로
        # 적으면 그 이름은 정말 `unknown tool` 이다.
        callable_names = set(tools) | {f"{a.replace('-', '')}_{t}" for a in p["apps"] for t in by_app[a]
                                       if not t.startswith(a.replace("-", "") + "_")}
        for fld in ("key_tools", "writes", "confirm"):
            bad = [n for n in p[fld] if n not in callable_names]
            if bad:
                errors.append(f"{key}: {fld} 에 이 앱에 없는 도구 — {', '.join(bad)}")
        both = sorted(set(p["writes"]) & set(p["confirm"]))
        if both:
            errors.append(f"{key}: writes 와 confirm 에 같이 있다 — {', '.join(both)}")
        # 운영자 앱의 쓰기 꼴 도구가 두 목록 어디에도 없다(docs/request-1030 HP-53) — 프롬프트의 '요청했을 때만 · 확인을 받은 뒤' 줄에도,
        # 에이전트서버의 확인 관문(HA-29)이 읽는 목록에도 빠진다. 정본은 노출 이름이나 접두 별칭으로 적으므로 둘 다 대조한다.
        if warns is not None and write is not None:
            listed = set(p["writes"]) | set(p["confirm"])
            loose = [t for t in tools if t in write and t not in read_ok and t not in listed
                     and f"{tool_app[t].replace('-', '')}_{t}" not in listed]
            if loose:
                more = f" 외 {len(loose) - LOOSE_SHOW}개" if len(loose) > LOOSE_SHOW else ""
                warns.append(f"목록 밖 쓰기 {key}: {len(loose)}개 — {', '.join(loose[:LOOSE_SHOW])}{more}"
                             "(writes · confirm 어디에도 없다 — 맞는 쪽에 넣는다)")
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
    notes: list[str] = []
    warns: list[str] = []
    rows, skipped, errors = plan(spec, tmap, notes, warns)
    for s in skipped:
        print(f"  · 건너뜀 {s}")
    for n in notes:
        print(f"  · 일부 {n}")
    for w in warns:
        print(f"  · {w}")
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
                    if not _saved_anyway(st2, key, r):
                        print(f"✗ {key} 생성 실패 {st2}: {res}", file=sys.stderr)
                        return 1
                    print(f"  ⚠ {key} 생성 응답이 {st2} 였지만 다시 읽으니 저장됐다 — 이어 간다(AIDataHub AD-21)")
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
                if not _saved_anyway(st2, key, patch):
                    print(f"✗ {key} 수정 실패 {st2}: {res}", file=sys.stderr)
                    return 1
                print(f"  ⚠ {key} 수정 응답이 {st2} 였지만 다시 읽으니 저장됐다 — 이어 간다(AIDataHub AD-21)")
        updated += 1

    # 정본에서 빠진 he-* 는 지우지 않고 알리기만 한다 — 사람이 만든 것일 수 있다.
    st, allrows = _http("GET", f"{AIDH}/api/agents")
    if st == 200 and isinstance(allrows, list):
        known = {p["key"] for p in spec["personas"]}
        stray = sorted(a.get("agent_type", "") for a in allrows
                       if str(a.get("agent_type", "")).startswith("he-") and a.get("agent_type") not in known)
        if stray:
            print(f"  ? 정본에 없는 he-* 에이전트 {len(stray)}명 — {', '.join(stray)} (지우지 않았다)")
        # 운영자 앱이 이 게이트웨이에 없다(docs/request-1030 HP-51) — 이 박스 AIDataHub 의 운영자는 조직도에서 고를 수 있는데, 모는 앱이
        # 이 게이트웨이에 없으면 챗을 보낸 뒤에야 주의가 떴다(DW-12 — dev 덤프 merge 로 들어온 he-sim-smarttwin). 정본이 아니라 올라가 있는
        # 행(response_config.mcp_apps)을 본다 — 에이전트서버가 그 주의를 낼 때 보는 값이다. 판정도 같다(/tools-map 에 도구가 하나도 없는 앱).
        have = set((tmap.get("map") or {}).values())
        for a in sorted(allrows, key=lambda a: str(a.get("agent_type", ""))):
            rc = a.get("response_config") if isinstance(a.get("response_config"), dict) else {}
            if rc.get("persona_kind") != "mcp_operator":
                continue
            apps = [x for x in rc.get("mcp_apps") or [] if isinstance(x, str) and x.strip()]
            gone = [x for x in apps if x not in have]
            if gone:
                rest = [x for x in apps if x in have]
                print(f"  ! 운영자 앱이 이 게이트웨이에 없다 — {a.get('agent_type')}: {', '.join(gone)}"
                      + (f" · {', '.join(rest)} 도구로만 답한다" if rest else " · 챗에서 고르면 그 앱 도구 없이 답한다"))
    else:
        print(f"  · AIDataHub 전문가 목록을 못 읽었다({st}) — 정본에 없는 he-* · 운영자 앱 점검을 건너뛴다")

    verb = "반영" if args.apply else "미리보기(--apply 로 반영)"
    print(f"{verb} — 새로 {created} · 고침 {updated} · 그대로 {same} · 건너뜀 {len(skipped)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
