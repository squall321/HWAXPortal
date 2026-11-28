#!/usr/bin/env python3
# 리스크 앱이 사람의 읽기 전용 PAT 로 부르는 남의 앱 조회 도구가 게이트웨이 읽기 판정을 지나는지 /tools-map 으로 보는 update-all 점검(docs/request-1125 HP-59)
"""왜 — 11-01 에 리스크 앱 ECAD 도구가 odb-hub find_job 을 사람의 읽기 전용 PAT 로 부르다 약 48분 막혔다. odb-hub verify 204 와 스모크 3/3 은
통과였다 — 도구가 있고 불리는 것과 '읽기 전용 토큰으로 불리는 것' 은 다른 판정이다. 게이트웨이 /tools-map 의 tool_class(한 판정 — 읽기 전용
PAT 를 여는 쪽보다 좁거나 같다: 엄격 판에서는 같고, 옛 판에서는 이것이 read 면 읽기 전용 PAT 도 연다)가 read 인지 본다.

쌍은 리스크 앱 어댑터(HWAXRisk backend/app/adapters — mcad · dyna · dyna_result · 전사 집계 · ecad)가 부르는 (백엔드 키, 원래 이름)이다.
포털 시험(test_risk_cross_reads)이 형제 리포가 있으면 그 소스의 목록과 견준다 — 어댑터가 도구를 더하면 여기도 더한다.

  python3 infra/scripts/risk-cross-reads.py --tools-map <파일>
줄마다 '<종류>\t<글>' — ok · fail · info. 끝 코드 0(읽음) · 2(지도를 못 읽음).
"""
from __future__ import annotations

import argparse
import json
import sys

# (백엔드 키, 원래 이름) — HWAXRisk adapters 의 app_key · REQUIRED_TOOLS(+ dyna 결과 · 전사 집계)
PAIRS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("heax-step_forge", ("list_parts", "list_interfaces", "interface_graph", "project_tree", "job_status", "part_mesh_map")),
    ("heax-kooremapper_mcp", ("inspect_file", "list_session_files", "report_summary", "report_part_risk", "report_energy_flow",
                              "report_findings", "report_worst_cases",
                              "corpus_summary", "material_usage", "section_contact_usage", "operation_usage")),
    ("odb-hub", ("find_job", "get_board_layers", "check_job_stackup", "get_volume_result", "get_odb_download", "list_parts")),
)


def check(tm: dict) -> list[tuple[str, str]]:
    """지도 → 줄들. 백엔드가 이 박스에 없으면 info 한 줄(재지 않는다), 도구가 없으면 info(어댑터가 unavailable 로 스스로 말한다),
    부류가 read 가 아니면 fail(그 도구 · 부류 · 근거와 고치는 자리)."""
    mp, orig, cls = tm.get("map") or {}, tm.get("orig") or {}, tm.get("tool_class") or {}
    exposed = {(b, orig.get(n, n)): n for n, b in mp.items()}
    present = set(mp.values())
    out: list[tuple[str, str]] = []
    bad: list[str] = []
    seen = 0
    for backend, tools in PAIRS:
        if backend not in present:
            out.append(("info", f"리스크 앱 조회 도구 — {backend} 가 이 게이트웨이에 없어 재지 않았다"))
            continue
        missing = [t for t in tools if (backend, t) not in exposed]
        if missing:
            out.append(("info", f"리스크 앱 조회 도구 — {backend} 에 없는 도구 {', '.join(missing)}(어댑터가 unavailable 로 말한다)"))
        for t in tools:
            n = exposed.get((backend, t))
            if n is None:
                continue
            seen += 1
            c = cls.get(n) or {}
            if c.get("class") != "read":
                bad.append(f"{backend}:{t}({c.get('class') or '모름'} · {c.get('source') or '근거 없음'})")
    if bad:
        out.append(("fail", f"리스크 앱이 사람의 읽기 전용 PAT 로 부르는 조회 도구 {len(bad)}개가 게이트웨이 읽기 판정을 지나지 못한다 — "
                            + ", ".join(bad) + ". 조회가 맞으면 게이트웨이 read_tools.local.json(재기동 없이) 또는 read_tools.json 에 그 '백엔드:이름' "
                            "을 더하거나 앱이 readOnlyHint 를 단다(11-01 odb-hub find_job 이 이렇게 48분 막혔다)"))
    elif seen:
        out.append(("ok", f"리스크 앱 조회 도구 {seen}개 — 게이트웨이 읽기 판정을 지난다(읽기 전용 PAT 로 불린다)"))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="리스크 앱이 부르는 남의 앱 조회 도구의 읽기 판정(/tools-map)")
    ap.add_argument("--tools-map", required=True, help="게이트웨이 /tools-map 응답을 담은 파일")
    a = ap.parse_args(argv)
    try:
        with open(a.tools_map, encoding="utf-8") as f:
            tm = json.load(f)
    except (OSError, ValueError) as exc:
        print(f"✗ /tools-map 을 읽지 못했다 — {exc}", file=sys.stderr)
        return 2
    if not isinstance(tm, dict) or not isinstance(tm.get("tool_class"), dict):
        print("info\t리스크 앱 조회 도구 — 이 게이트웨이 /tools-map 에 tool_class 가 없어(옛 판) 재지 않았다")
        return 0
    for kind, text in check(tm):
        print(f"{kind}\t{text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
