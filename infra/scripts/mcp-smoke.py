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

사용:  mcp-smoke.py [--json] [--per-backend N] [--timeout S] [--periodic]
종료:  0=이상 없음, 1=0성공 백엔드 있음, 2=게이트웨이에 붙지 못함(판정 불가),
       3=버전 드리프트(호출은 되는데 배포본이 코드보다 오래됨)

--periodic — 상시 상태판이 30분마다 부르는 판(infra/scripts/status-push.py, docs/improvement-1015/status-board.md).
  쓰기 낱말을 빼는 것만으로는 샌다(위 ingest_now). 몇 분마다 부르면 샌 도구도 그만큼 자주 불리므로 **읽기 낱말 허용
  목록**(READ)에 드는 도구만, 백엔드당 하나만 부른다. 허용 목록에 드는 도구가 없는 백엔드는 '검사 못 함' 이다. 호출마다
  묶음 표지(X-HWAX-Corr: status-board:mcp-smoke)를 실어 게이트웨이 감사에서 이 호출을 가려낼 수 있게 한다.
"""
import argparse
import json
import os
import pathlib
import re
import sys

# 부작용이 있을 수 있는 동사 — 애매하면 쓰기로 보고 호출하지 않는다.
#
# ⚠ **접두사 목록만으로는 샌다.** 실제로 샜다(2026-09-20 cae00 로그에서 드러남) —
# `ingest_now`(paper_ingest)는 맨 앞 `ingest` 가 목록에 없어(`report_ingest` 만 있었다)
# **읽기 도구로 뽑혀 매 update-all 마다 실제로 불렸다.** 그 도구는 드롭폴더 전량을 분류·증분색인·
# 그라운딩하고, 게이트가 켜져 있으면 카드 적용까지 한다. 스모크는 "살아 있나" 를 묻는 것이지
# 파이프라인을 돌리는 것이 아니다. cae00 에서는 그게 실패로 찍혀(경로가 dev 절대경로로 박혀 있다)
# 오히려 드러났지만, dev 에서는 **조용히 성공**하고 있었다 — 그쪽이 더 나쁘다.
WRITE = re.compile(
    r"^(create|delete|update|patch|insert|upload|submit|register|import|remove|move"
    r"|train|activate|cancel|bind|link|save|export|convert|add|set|start|close|run"
    r"|recompute|prepare|ingest|gate_|fetch_|draft_|report_ingest|report_fragmentize|scenario_"
    r"|meeting_|qa_run|smarttwin_submit|slurm_submit|slurm_job_control|slurm_node_set)")

# 이름 **어디든** 이 말이 들어 있으면 쓰기로 본다 — 접두사 규칙이 못 잡는 자리를 메운다
# (예: `render_submit` 은 submit 으로 시작하지 않아 접두사 목록을 통과한다).
WRITE_ANY = re.compile(r"(submit|ingest|reload|_now$|_apply$|purge|rebuild)")

# --periodic 의 허용 목록 — 이름의 낱말 하나(맨 앞이거나 _ 로 갈린 자리)가 읽기 동사여야 부른다. 앱 접두가 붙은 이름
# (`risk_list_projects`·`heaxstep_forge_system_status`)도 잡도록 맨 앞에 묶지 않는다. 쓰기 규칙(위 둘)이 먼저다.
# ⚠ 게이트웨이의 '필수 인자 없음' 은 보호가 아니다 — smart-twin-mcp 는 직접 도구를 `args: dict` 하나로 내보내 잡을 내는
# `fullangle_drop_simulation` 도 필수 인자가 없어 보인다(서버가 실행 전에 jsonschema 로 막는다 — 2026-10-17 확인).
READ = re.compile(r"(^|_)(list|get|search|find|describe|show|query|read|lookup|status|health|ping|version|info"
                  r"|capabilities|count|stats|whoami|taxonomy|catalog)(_|$)")
PERIODIC_CORR = "status-board:mcp-smoke"

def _find_cfg() -> str:
    """게이트웨이 config 경로. 박스마다 리포 위치가 달라 하드코딩하면 안 된다.

    dev 는 ~/claude/, cae00 은 ~/Projects/ 아래다. 하드코딩 탓에 cae00 에서 스모크가
    통째로 안 돌았고(FileNotFoundError → rc=2), 그러면 '도구가 동작한다'가 검증되지
    않은 채로 배포가 끝난다 — 미검증이 초록처럼 지나가는 게 이 버그의 값이다.
    update-all.sh 의 find_repo 와 같은 후보 순서를 쓴다(형제 리포 → Projects → claude).
    """
    env = os.environ.get("GATEWAY_CONFIG")
    if env:
        return env
    here = pathlib.Path(__file__).resolve()
    sibling = here.parents[3] / "HWAXMcpGateway"     # <parent>/HWAXPortal/infra/scripts/…
    home = pathlib.Path.home()
    for base in (sibling, home / "Projects" / "HWAXMcpGateway", home / "claude" / "HWAXMcpGateway"):
        cand = base / "gateway_config.json"
        if cand.is_file():
            return str(cand)
    return str(sibling / "gateway_config.json")      # 없으면 가장 그럴듯한 경로로 에러를 내게 둔다


CFG = _find_cfg()

def _identity_only(cfg: dict, health: dict | None = None) -> set[str]:
    """사람 신원으로만 답하는 백엔드 — 이 스모크는 게이트웨이 토큰(신원 없음)으로 부르므로 거절될 수밖에 없다.

    설정에 url 을 직접 적은 정적 백엔드 가운데 사람별 위임(`heax_registry.per_user_sso`)에 있고 서비스 자격(`headers`)이
    없는 것이다. ste 가 그렇다 — 프로비저닝이 url 만 적고, 신원 없이 부르면 REST 가 401 이다(2026-10-17 dev 실측 0/3 ·
    감사 note no-identity). 그것을 0성공으로 세면 update-all §6 이 매번 '복구'(재프로비저닝 · 게이트웨이 재기동)를 돌리고
    ✗ 로 끝났다. 그래서 부르지 않고 '검사 못 함' 으로 말한다 — ste 는 update-all 의 '사람 신분 실호출'
    (ste-gateway-check.py probe)이 사람 명의로 따로 본다.
    허브 앱(heax-*)은 허브 등록 토큰이 서비스 자격이라 넣지 않는다 — DynaForge 의 토큰 만료(이 스모크가 생긴 까닭)는
    그대로 0성공으로 잡힌다.
    외부 연결 플랫폼(포털 박스 권한표의 connect: — HWAXPortal docs/ext-connect PX1)도 같다 — 사람이 포털에 등록한 그쪽 토큰으로만
    부르고 신원 없는 호출은 게이트웨이가 거절한다. 설정 파일에는 없어 게이트웨이 `/health` 의 `conn_platforms` 로 안다. 붙어 있는
    것(ok · down)만 뺀다 — collision 같은 사유의 키는 선언이 아닌 진짜 백엔드라 그대로 부른다."""
    per_user = set(((cfg.get("heax_registry") or {}).get("per_user_sso") or {}).keys())
    conn = (health or {}).get("conn_platforms")
    declared = {k for k, st in conn.items() if st in ("ok", "down")} if isinstance(conn, dict) else set()
    return declared | {k for k, v in cfg.items()
                       if not k.startswith("_") and isinstance(v, dict) and v.get("url") and k in per_user and not v.get("headers")}


# 자기 상태를 돌려주는 무인자 도구 이름들. 이 중 하나가 있으면 드리프트 대조를 시도한다.
# 인자가 있어야 하는 도구라는 거절인가 — 스키마에 required 가 없어도 본문이 '둘 중 하나를 준다' 로 막는 도구가 있다(StepForge
# part_history: "projects(…)나 task_code(…) 중 하나를 준다", 10-17 cae00 리뷰 P6 · X5). 실패로 세면 그 백엔드가 2/3 이고, 주기 판
# (백엔드당 하나)에서는 '죽음' 이 되어 상태판이 헛경보를 낸다. 낱말('필수' · '필요')로만 가르면 '인증이 필요합니다' 같은 진짜 장애를
# 건너뛴다 — 그래서 **그 도구의 인자 이름**이 문구에 나와야 하고, 인증 · 연결 거절로 보이면 인자 이름이 있어도 실패로 센다.
_AUTH_OR_TRANSPORT = re.compile(r"(?i)\b40[13]\b|unauthori|forbidden|인증|권한|토큰|\btoken\b|connect|timed? ?out|refused")


def _args_needed(text: str, props: dict) -> bool:
    if not props or _AUTH_OR_TRANSPORT.search(text or ""):
        return False
    return any(re.search(rf"(?<![A-Za-z0-9_]){re.escape(p)}(?![A-Za-z0-9_])", text or "") for p in props)


def _order(names: list, props_of: dict) -> list:
    """인자 칸이 아예 없는 도구부터 — 숨은 '둘 중 하나' 요구가 없다. 같은 무리 안의 차례는 그대로(안정 정렬)."""
    return sorted(names, key=lambda n: bool(props_of.get(n)))


async def _probe(rec: dict, names: list, call, per_backend: int, timeout: float, props_of: dict) -> None:
    """백엔드 하나를 부른다 — 인자를 요구하는 거절(_args_needed)은 세지 않고 다음 후보로 넘어간다. 센 호출이 per_backend 개면 멈춘다."""
    import anyio
    for n in names:
        if len(rec["probed"]) >= per_backend:
            break
        try:
            with anyio.fail_after(timeout):
                res = await call(n, {})
            if getattr(res, "isError", False):
                txt = _text(res)
                if _args_needed(txt, props_of.get(n) or {}):
                    rec.setdefault("skipped", []).append(n)
                    continue
                rec["probed"].append(n)
                rec["err"] += 1
                if not rec["why"]:
                    rec["why"] = txt[:160]
            else:
                rec["probed"].append(n)
                rec["ok"] += 1
        except Exception as exc:  # noqa: BLE001 — 타임아웃 포함
            rec["probed"].append(n)
            rec["err"] += 1
            if not rec["why"]:
                rec["why"] = f"{type(exc).__name__}: {exc}"[:160]
    if not rec["probed"] and rec.get("skipped"):
        rec.update(unprobed=True, why=f"부를 후보가 모두 인자를 요구했다(건너뜀 {len(rec['skipped'])} — {', '.join(rec['skipped'][:3])})")


_SELF_REPORT = ("system_capabilities", "capabilities", "system_status")
# 그 응답에서 '이 앱이 노출한다고 주장하는 도구 수'를 담고 있을 만한 키(먼저 맞는 것 하나).
_COUNT_KEYS = ("mcp_tools", "tool_count", "tools_count", "n_tools")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="결과를 JSON 으로")
    ap.add_argument("--per-backend", type=int, default=None, help="백엔드당 최대 호출 수(기본 3, --periodic 은 1)")
    ap.add_argument("--timeout", type=float, default=20, help="호출당 제한시간(초)")
    ap.add_argument("--periodic", action="store_true", help="상시 상태판 판 — 읽기 낱말 허용 목록 · 백엔드당 하나 · 감사 묶음 표지")
    a = ap.parse_args()
    if a.per_backend is None:
        a.per_backend = 1 if a.periodic else 3

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
            full = json.load(f)
        gw = full["_gateway"]
    except Exception as exc:  # noqa: BLE001
        print(f"✗ 게이트웨이 config 를 읽지 못함({CFG}): {exc!r}", file=sys.stderr)
        return 2
    identity_only = _identity_only(full)
    url = f"http://127.0.0.1:{gw.get('port', 9110)}/mcp"
    headers = {"Authorization": f"Bearer {gw['token']}"}
    if a.periodic:
        headers["X-HWAX-Corr"] = PERIODIC_CORR

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
                # 외부 연결 플랫폼은 설정 파일에 없다 — 게이트웨이 /health 의 conn_platforms 로 안다(PX1). 못 읽으면 종전대로다.
                conn_keys = _identity_only({}, await _health(url))
                identity_only.update(conn_keys)
                by_be: dict[str, list] = {}
                # ⚠ **검사를 못 돌린 것과 통과한 것은 다르다**(update-all §6 의 같은 규율).
                # 쓰기 도구만 있는 백엔드는 부를 게 없어 결과에서 **통째로 사라진다** — 그러면
                # 화면에는 아무 줄도 안 나오고, 읽는 사람은 문제없다고 읽는다. 그래서 그런 백엔드를
                # 따로 세어 "무인자 읽기 도구 없음" 으로 **말한다**(초록도 빨강도 아니다).
                seen_be: set[str] = set()
                props_of = {t.name: (t.inputSchema or {}).get("properties") or {} for t in tools}
                for t in tools:
                    be = tmap.get(t.name, "?")
                    seen_be.add(be)
                    if be in identity_only:
                        continue
                    if WRITE.match(t.name) or WRITE_ANY.search(t.name):
                        continue
                    if (t.inputSchema or {}).get("required"):
                        continue
                    if a.periodic and not READ.search(t.name):
                        continue
                    by_be.setdefault(be, []).append(t.name)
                for be in by_be:
                    by_be[be] = _order(by_be[be], props_of)
                for be in sorted(seen_be - set(by_be) - {"_gateway", "?"}):
                    if be in conn_keys:
                        why = ("외부 연결 플랫폼 — 사람이 포털에 등록한 그쪽 토큰으로만 답해 게이트웨이 토큰(신원 없음)으로는 확인 못 함"
                               "(상태는 게이트웨이 /health 의 conn_platforms)")
                    elif be in identity_only:
                        why = "사람 신원으로만 답하는 백엔드라 게이트웨이 토큰(신원 없음)으로는 확인 못 함 — 사람 신분 실호출이 따로 본다"
                    elif a.periodic:
                        why = "읽기 낱말 허용 목록에 드는 무인자 도구가 없어 호출로는 확인 못 함"
                    else:
                        why = "무인자 읽기 도구가 없어 호출로는 확인 못 함"
                    result.setdefault(be, {"ok": 0, "err": 0, "probed": [], "why": why, "unprobed": True})

                for be, names in sorted(by_be.items()):
                    if be == "_gateway":
                        continue      # 게이트웨이 자체 도구는 백엔드 건강과 무관
                    rec = result.setdefault(be, {"ok": 0, "err": 0, "probed": [], "why": ""})
                    await _probe(rec, names, s.call_tool, a.per_backend, a.timeout, props_of)

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
            if r.get("unprobed"):
                # 초록도 빨강도 아니다 — **못 물어봤다**고 말한다(무음이 가장 나쁘다)
                print(f"  ? {be:28} 검사 못 함 — {r['why']}")
                continue
            mark = "✗" if be in dead else "·"
            print(f"  {mark} {be:28} 성공 {r['ok']}/{len(r['probed'])}"
                  + (f"   {r['why']}" if be in dead else "")
                  + (f"   · 인자 필요로 건너뜀 {len(r['skipped'])}({', '.join(r['skipped'][:3])})" if r.get("skipped") else ""))
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


async def _health(url: str) -> dict:
    """게이트웨이 /health(무인증). 실패하면 빈 것 — 외부 연결 플랫폼을 가려내지 못할 뿐 스모크는 종전대로 돈다."""
    import httpx
    base = url.rsplit("/mcp", 1)[0]
    try:
        async with httpx.AsyncClient(timeout=6) as cli:
            resp = await cli.get(f"{base}/health")
            resp.raise_for_status()
            body = resp.json()
            return body if isinstance(body, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


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
