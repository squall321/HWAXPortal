# MCP 게이트웨이의 읽기 전용 도구를 실제로 호출해 '목록엔 있는데 안 되는' 백엔드를 잡는다
"""도구 목록이 온다고 도구가 동작하는 건 아니다.

update-all 은 /tools-map 의 도구 수로 MCP 앱을 판정했다. 그런데 도구 수는 tools/list 의
응답 길이라, 백엔드가 tools/list 는 답하고 tools/call 은 전부 거절해도 초록이 찍힌다.
실제로 DynaForge MCP(heax-kooremapper_mcp)가 그랬다 — 도구 22개가 목록에 뜨는 채로
호출은 100% "토큰이 유효하지 않거나 만료되었습니다"였고, 노출된 2026-08-01 이후
감사로그 성공 0건이었다(2026-08-12 스모크로 발견).

판정 규칙은 '이 백엔드에서 성공한 호출이 하나라도 있는가'다. 개별 도구가 인자 없이
실패하는 건 정상일 수 있으므로(예: plot_curves — 그릴 곡선을 지정해야 한다) 도구
단위로는 실패를 문제 삼지 않는다. 백엔드 전체가 0성공일 때만 FAIL 이다.

또 하나 — 호출이 되는 것과 '최신 코드가 도는 것'은 다르다. DynaForge 는 프로세스가
server.py 커밋보다 1분 먼저 떠서 도구 22개만 노출한 채로 돌았다(코드엔 36개). 22개가
전부 정상 응답하니 위 판정은 초록이었고, 결과 분석 도구 14종이 통째로 빠진 걸 아무도
못 봤다(2026-08-16 발견). 그래서 자기 도구 수를 보고하는 앱은 그 값과 게이트웨이 노출
수를 대조한다.

사용:  mcp-smoke.py [--json] [--per-backend N] [--timeout S]
종료:  0=이상 없음, 1=0성공 백엔드 있음, 2=게이트웨이에 붙지 못함(판정 불가),
       3=버전 드리프트(호출은 되는데 배포본이 코드보다 오래됨)
"""
import argparse
import json
import os
import re
import sys

# 부작용이 있을 수 있는 동사 — 애매하면 쓰기로 보고 호출하지 않는다.
WRITE = re.compile(
    r"^(create|delete|update|patch|insert|upload|submit|register|import|remove|move"
    r"|train|activate|cancel|bind|link|save|export|convert|add|set|start|close|run"
    r"|recompute|prepare|fetch_|draft_|report_ingest|report_fragmentize|scenario_"
    r"|meeting_|qa_run|smarttwin_submit|slurm_submit|slurm_job_control|slurm_node_set)")

CFG = os.environ.get("GATEWAY_CONFIG") or "/home/koopark/claude/HWAXMcpGateway/gateway_config.json"

# 자기 상태를 돌려주는 무인자 도구 이름들. 이 중 하나가 있으면 드리프트 대조를 시도한다.
_SELF_REPORT = ("system_capabilities", "capabilities", "system_status")
# 그 응답에서 '이 앱이 노출한다고 주장하는 도구 수'를 담고 있을 만한 키(먼저 맞는 것 하나).
_COUNT_KEYS = ("mcp_tools", "tool_count", "tools_count", "n_tools")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="결과를 JSON 으로")
    ap.add_argument("--per-backend", type=int, default=3, help="백엔드당 최대 호출 수")
    ap.add_argument("--timeout", type=float, default=20, help="호출당 제한시간(초)")
    a = ap.parse_args()

    try:
        import anyio
        from mcp.client.session import ClientSession
        from mcp.client.streamable_http import streamablehttp_client
    except ImportError as exc:
        print(f"✗ mcp 모듈 없음({exc}) — 스모크를 돌릴 수 없다. 게이트웨이 venv 로 실행하라.",
              file=sys.stderr)
        return 2

    try:
        with open(CFG) as f:
            gw = json.load(f)["_gateway"]
    except Exception as exc:  # noqa: BLE001
        print(f"✗ 게이트웨이 config 를 읽지 못함({CFG}): {exc!r}", file=sys.stderr)
        return 2
    url = f"http://127.0.0.1:{gw.get('port', 9110)}/mcp"
    headers = {"Authorization": f"Bearer {gw['token']}"}

    result: dict[str, dict] = {}
    drift: dict[str, dict] = {}

    async def run() -> None:
        async with streamablehttp_client(url, headers=headers) as (r, w, _):
            async with ClientSession(r, w) as s:
                await s.initialize()
                tools = (await s.list_tools()).tools
                # 도구 → 백엔드 매핑은 /tools-map 이 준다. 못 얻으면 백엔드 구분 없이
                # 전체를 한 덩어리로 본다(그래도 '전량 실패'는 잡힌다).
                tmap = await _tools_map(url, headers)
                by_be: dict[str, list] = {}
                for t in tools:
                    if WRITE.match(t.name):
                        continue
                    if (t.inputSchema or {}).get("required"):
                        continue
                    by_be.setdefault(tmap.get(t.name, "?"), []).append(t.name)

                for be, names in sorted(by_be.items()):
                    if be == "_gateway":
                        continue      # 게이트웨이 자체 도구는 백엔드 건강과 무관
                    rec = result.setdefault(be, {"ok": 0, "err": 0, "probed": [], "why": ""})
                    for n in names[: a.per_backend]:
                        rec["probed"].append(n)
                        try:
                            with anyio.fail_after(a.timeout):
                                res = await s.call_tool(n, {})
                            if getattr(res, "isError", False):
                                rec["err"] += 1
                                if not rec["why"]:
                                    rec["why"] = _text(res)[:160]
                            else:
                                rec["ok"] += 1
                        except Exception as exc:  # noqa: BLE001 — 타임아웃 포함
                            rec["err"] += 1
                            if not rec["why"]:
                                rec["why"] = f"{type(exc).__name__}: {exc}"[:160]

                # ── 버전 드리프트 ───────────────────────────────────────────
                # 호출이 되는 것과 최신 코드가 도는 것은 다르다. DynaForge 가 실제로
                # 그랬다 — 프로세스가 server.py 커밋보다 1분 먼저 떠서 도구 22개만
                # 노출됐고(코드엔 36개), 스모크는 22개가 다 응답하니 초록이었다.
                # 자기 도구 수를 보고하는 앱이면 그 값과 게이트웨이 노출 수를 대조한다.
                # 표를 두지 않는다 — 이름이 맞는 도구가 있으면 자동으로 검사 대상이다.
                exposed: dict[str, int] = {}
                for t in tools:
                    be = tmap.get(t.name, "?")
                    if be != "_gateway":
                        exposed[be] = exposed.get(be, 0) + 1
                for be, names in sorted(by_be.items()):
                    if be == "_gateway":
                        continue
                    # ⚠ 후보를 하나만 보고 포기하면 안 된다. DynaForge 는 system_status 와
                    #   system_capabilities 를 둘 다 갖는데 도구 수는 뒤엣것에만 있다 —
                    #   앞엣것에서 멈추면 대조가 조용히 생략된다(이 검사를 만들며 실제로 겪었다).
                    for probe in [n for n in names if n in _SELF_REPORT]:
                        try:
                            with anyio.fail_after(a.timeout):
                                res = await s.call_tool(probe, {})
                            if getattr(res, "isError", False):
                                continue
                            rep = json.loads(_text(res))
                        except Exception:  # noqa: BLE001 — 대조 실패는 스모크를 막지 않는다
                            continue
                        if not isinstance(rep, dict):
                            continue
                        want = next((rep[k] for k in _COUNT_KEYS
                                     if isinstance(rep.get(k), int) and rep[k] > 0), None)
                        if want is None:
                            continue          # 이 도구엔 도구 수가 없다 → 다음 후보로
                        have = exposed.get(be, 0)
                        if want != have:
                            drift[be] = {"tool": probe, "key": "tools", "app": want, "gateway": have}
                        break

    try:
        anyio.run(run)
    except Exception as exc:  # noqa: BLE001
        print(f"✗ 게이트웨이({url})에 붙지 못함: {exc!r} — MCP 도구 동작을 판정할 수 없다.",
              file=sys.stderr)
        return 2

    dead = {be: r for be, r in result.items() if r["probed"] and r["ok"] == 0}
    if a.json:
        print(json.dumps({"backends": result, "dead": sorted(dead), "drift": drift},
                         ensure_ascii=False, indent=1))
    else:
        for be, r in sorted(result.items()):
            mark = "✗" if be in dead else "·"
            print(f"  {mark} {be:28} 성공 {r['ok']}/{len(r['probed'])}"
                  + (f"   {r['why']}" if be in dead else ""))
        for be, d in sorted(drift.items()):
            print(f"  ✗ {be:28} 도구 수 불일치 — 앱은 {d['app']}개라는데 게이트웨이엔 {d['gateway']}개"
                  f" ({d['tool']}.{d['key']})")
            print(f"      배포본이 코드보다 오래됐다는 뜻이다. 그 앱을 재기동/재빌드하라.")
        if not result:
            print("  ⚠ 호출 가능한 읽기 도구가 하나도 없다 — 판정하지 못했다.")
            return 2
    if dead:
        return 1
    return 3 if drift else 0


def _text(res) -> str:
    return "\n".join(c.text or "" for c in (res.content or [])
                     if getattr(c, "type", None) == "text")


async def _tools_map(url: str, headers: dict) -> dict:
    """/tools-map 의 {도구: 백엔드}. 실패하면 빈 표(그래도 스모크는 돈다)."""
    import httpx
    base = url.rsplit("/mcp", 1)[0]
    try:
        async with httpx.AsyncClient(timeout=6) as cli:
            resp = await cli.get(f"{base}/tools-map", headers=headers)
            resp.raise_for_status()
            return resp.json().get("map") or {}
    except Exception:  # noqa: BLE001
        return {}


if __name__ == "__main__":
    sys.exit(main())
