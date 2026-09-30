# 게이트웨이의 ste 사용자 위임을 확인한다 — 설정·시크릿 대조(deleg)와 사용자 신분 실호출(probe)(docs/ste-cae00 D-30)
"""터널이 살아 있어도 그 안이 틀릴 수 있다 — 점검이 전부 초록인데 ste 도구가 실패하던 자리를 본다.

  ste-gateway-check.py deleg [--json]
      ① 게이트웨이 config 에 ste 위임(heax_registry.per_user_sso.ste)이 있는가 — 없으면 게이트웨이가 ste 를 토큰 없이
      (서비스 신분) 불러 REST 가 401 이다. ② 그 시크릿이 포털 infra/.env 의 STE_SSO_SECRET 과 같은가(값은 출력하지 않는다).
      ③ 헤드가 **게이트웨이가 쥔** 시크릿을 받아들이는가(sso_url/verify → 204). ste-doctor 의 sso-secret 행은 포털의 값을 본다.
      종료: 0 정상 · 1 문제 · 2 판정 불가(config 없음·ste 를 안 쓰는 박스)
      표준 라이브러리만 쓴다(시스템 python3 로 돈다).

  ste-gateway-check.py probe --as <이메일> [--json] [--timeout S]
      게이트웨이에 **그 사람 신분**(포털이 주는 그 사람의 권한 그대로)으로 붙어 ste 도구를 실제로 부른다.
        잡 목록 → 토큰 경로(발급·전달·REST 인증) · cluster_info → slurm 경로(헤드의 scontrol/sinfo)
      도구 이름은 /tools-map 에서 찾는다 — 이름 충돌이 박스마다 달라 접두어(ste_)가 붙거나 안 붙는다.
      둘 다 캐시되지 않는 이름이다(job·접두사 규칙) — 결과는 매번 헤드까지 간 것이다.
      mcp 모듈이 있는 python(게이트웨이·에이전트 서버 venv)으로 돌린다.
      종료: 0 둘 다 성공 · 1 실패 있음 · 2 게이트웨이에 붙지 못함
"""
import argparse
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request
from urllib.parse import quote

ROOT = pathlib.Path(__file__).resolve().parents[2]


def find_cfg() -> pathlib.Path:
    """게이트웨이 config — mcp-smoke.py 와 같은 후보 순서(형제 리포 → ~/Projects → ~/claude)."""
    env = os.environ.get("GATEWAY_CONFIG")
    if env:
        return pathlib.Path(env)
    home = pathlib.Path.home()
    for base in (ROOT.parent / "HWAXMcpGateway", home / "Projects" / "HWAXMcpGateway",
                 home / "claude" / "HWAXMcpGateway"):
        if (base / "gateway_config.json").is_file():
            return base / "gateway_config.json"
    return ROOT.parent / "HWAXMcpGateway" / "gateway_config.json"


def env_value(key: str, path: pathlib.Path) -> str:
    """bash 가 읽는 것과 같게 — 마지막 줄, 인라인 주석(공백 뒤 #)·양끝 공백·따옴표·CR 을 벗긴다(ste-doctor envv 와 같은 규칙)."""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    val = ""
    for ln in lines:
        m = re.match(rf"^\s*(?:export\s+)?{re.escape(key)}=(.*)$", ln)
        if m:
            val = m.group(1)
    val = re.sub(r"\s+#.*$", "", val).strip()
    return val.replace('"', "").replace("'", "").replace("\r", "")


# ── deleg ────────────────────────────────────────────────────────────────────
def verify(sso_url: str, secret: str, timeout: float = 5) -> str:
    """헤드가 이 시크릿을 받아들이는가 — '204' · '401' · 'old'(옛 판의 미들웨어 401) · '404' · 'unreachable'."""
    req = urllib.request.Request(sso_url.rstrip("/") + "/verify", method="POST", data=b"",
                                 headers={"X-Heax-Gateway-Secret": secret})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return str(r.status)
    except urllib.error.HTTPError as e:
        if e.code == 401 and e.headers.get("www-authenticate"):
            return "old"
        return str(e.code)
    except Exception:  # noqa: BLE001 — 연결 거부·시간초과·DNS
        return "unreachable"


def deleg(cfg_path: pathlib.Path, expected: str, do_verify: bool = True) -> dict:
    out = {"config": str(cfg_path), "state": "", "verify": "", "sso_url": "", "detail": ""}
    try:
        g = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        out.update(state="no-config", detail=f"게이트웨이 config 를 못 읽었다: {exc!r}")
        return out
    if "ste" not in g:
        out.update(state="unused", detail="게이트웨이에 ste 백엔드가 없다(ste 를 안 쓰는 박스)")
        return out
    ste = ((g.get("heax_registry") or {}).get("per_user_sso") or {}).get("ste") or {}
    if not (ste.get("sso_url") and ste.get("secret")):
        out.update(state="missing", detail="ste 사용자 위임이 없다 — 게이트웨이가 ste 를 토큰 없이(서비스 신분) 불러 REST 가 401 이다."
                                           " update-all 이 재프로비저닝한다(§5)")
        return out
    out["sso_url"] = ste["sso_url"]
    if not expected:
        out["state"] = "unknown"
        out["detail"] = "포털 infra/.env 에 STE_SSO_SECRET 이 없어 대조 못 함"
    elif ste["secret"] != expected:
        out["state"] = "stale"
        out["detail"] = "게이트웨이가 쥔 시크릿이 포털 infra/.env 와 다르다(시크릿을 바꾼 뒤 재프로비저닝이 안 됐다) — update-all 이 고친다(§5)"
    else:
        out["state"] = "ok"
    if not do_verify:
        out["verify"] = "skipped"
        return out
    v = verify(ste["sso_url"], ste["secret"])
    out["verify"] = v
    text = {"204": "헤드가 게이트웨이의 시크릿을 받아들인다(verify 204)",
            "401": "헤드와 시크릿이 다르다(verify 401) — FORCE_SSO_SECRET=1 SmartTwinExplorer/deploy/sync-sso-secret.sh 뒤 update-all",
            "old": "헤드에 옛 판이 떠 있다(/api/auth/sso 를 미들웨어가 401) — ste 코드 갱신부터",
            "404": "헤드 판이 verify 를 모르거나 시크릿이 비었다(404)",
            "unreachable": f"{ste['sso_url']} 에 닿지 않는다 — 터널(15810)·Teleport 인증서부터"}.get(v, f"verify {v} — 판정 불가")
    out["detail"] = (out["detail"] + " · " if out["detail"] else "") + text
    return out


def deleg_rc(r: dict) -> int:
    if r["state"] in ("no-config", "unused"):
        return 2
    if r["state"] in ("missing", "stale") or r["verify"] not in ("204", "skipped"):
        return 1
    return 0


# ── probe ────────────────────────────────────────────────────────────────────
def classify(text: str, is_error: bool) -> tuple[str, str]:
    """(판정, 한 줄 사유). 판정: ok · mint · token · session · forbidden · missing · slurm · other.
    문구는 게이트웨이(gateway.py)와 ste MCP(mcp_server/server.py)가 실제로 내는 모양이다 — 짐작으로 넓히지 않는다."""
    t = (text or "").strip()
    if not is_error:
        return "ok", ""
    if "자격증명으로 호출하지 못했습니다" in t:
        return "mint", "게이트웨이가 그 사람의 ste 토큰을 못 받았다(시크릿·터널 15810·헤드 판) — " + t[:300]
    if re.search(r"→ HTTP 401\b", t):
        return "token", "ste 가 토큰을 거절했다(토큰 없이 불렀거나 죽은 토큰) — " + t[:300]
    if t.startswith("backend ") and "unavailable" in t:
        return "session", "게이트웨이의 ste 세션이 없다(터널 15812·헤드 ste-mcp) — " + t[:300]
    if t.startswith("forbidden"):
        return "forbidden", "이 계정에 ste 권한이 없다(포털 '내 권한') — " + t[:300]
    if t.startswith("unknown tool"):
        return "missing", "게이트웨이에 그 도구가 없다 — " + t[:300]
    if re.search(r"→ HTTP 50[0-9]\b", t) or "클러스터 조회 실패" in t:
        return "slurm", "헤드에서 slurm 조회가 실패했다 — " + t[:300]
    return "other", t[:300]


def resolve(tmap: dict, original: str) -> str | None:
    """ste 백엔드의 그 도구가 게이트웨이에서 어떤 이름인가(충돌이 있으면 `ste_` 가 붙는다)."""
    names = [n for n, be in tmap.items() if be == "ste" and (n == original or n.endswith("_" + original))]
    return sorted(names, key=len)[0] if names else None


def probe(email: str, timeout: float) -> dict:
    import anyio
    import httpx
    from mcp.client.session import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    gw = json.loads(find_cfg().read_text(encoding="utf-8"))
    tok, port = gw["_gateway"]["token"], gw["_gateway"].get("port", 9110)
    base = f"http://127.0.0.1:{port}"
    out = {"as": email, "groups": "", "steps": []}
    # 그 사람의 **지금** 권한 — 에이전트 서버가 싣는 것과 같게. 못 읽으면 내부 서비스 신분으로 부르고 그렇다고 적는다.
    groups = None
    # 포털 주소 — 게이트웨이 `_portal_api_base` 와 같은 규칙(api_base, 없으면 jwks_url 의 origin).
    portal = gw.get("portal") or {}
    papi = portal.get("api_base") or ""
    if not papi:
        m = re.match(r"^(https?://[^/]+)", portal.get("jwks_url") or "")
        papi = m.group(1) if m else ""
    if papi:
        try:
            r = httpx.get(f"{papi.rstrip('/')}/internal/access/entitlements", params={"email": email},
                          headers={"Authorization": f"Bearer {tok}"}, timeout=6)
            if r.status_code == 200:
                groups = [str(k) for k in (r.json().get("keys") or [])]
        except Exception:  # noqa: BLE001
            groups = None
    headers = {"Authorization": f"Bearer {tok}", "x-hwax-user": quote(email.strip().lower(), safe="@.")}
    if groups is not None:
        headers["x-hwax-groups"] = quote(",".join(groups), safe=",")
        out["groups"] = "portal"
    else:
        out["groups"] = "service"          # 권한 판정은 못 했다 — 토큰·slurm 경로만 본다

    async def run():
        async with httpx.AsyncClient(timeout=6) as cli:
            tmap = (await cli.get(f"{base}/tools-map", headers={"Authorization": f"Bearer {tok}"})).json().get("map") or {}
        async with streamablehttp_client(f"{base}/mcp", headers=headers) as (r, w, _):
            async with ClientSession(r, w) as s:
                await s.initialize()
                for what, original, args in (("token", "list_jobs", {"limit": 1}), ("slurm", "cluster_info", {})):
                    name = resolve(tmap, original)
                    if not name:
                        out["steps"].append({"what": what, "tool": original, "verdict": "missing",
                                             "detail": "게이트웨이 tools-map 에 ste 의 이 도구가 없다(ste 백엔드 세션·도구 목록)"})
                        continue
                    with anyio.fail_after(timeout):
                        res = await s.call_tool(name, args)
                    text = "".join(getattr(c, "text", "") or "" for c in (res.content or []))
                    v, why = classify(text, bool(res.isError))
                    step = {"what": what, "tool": name, "verdict": v, "detail": why}
                    if v == "ok" and what == "slurm":
                        try:
                            step["detail"] = f"노드 {json.loads(text).get('nodes_total')}대"
                        except ValueError:
                            pass
                    out["steps"].append(step)
    anyio.run(run)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("deleg")
    d.add_argument("--json", action="store_true")
    d.add_argument("--no-verify", action="store_true", help="헤드에 묻지 않고 설정만 본다(update-all §5)")
    p = sub.add_parser("probe")
    p.add_argument("--as", dest="email", required=True)
    p.add_argument("--json", action="store_true")
    p.add_argument("--timeout", type=float, default=60)
    a = ap.parse_args()

    if a.cmd == "deleg":
        expected = os.environ.get("STE_SSO_SECRET") or env_value("STE_SSO_SECRET", ROOT / "infra" / ".env")
        r = deleg(find_cfg(), expected, do_verify=not a.no_verify)
        rc = deleg_rc(r)
        if a.json:
            print(json.dumps({**r, "rc": rc}, ensure_ascii=False))
        else:
            print(f"{'✓' if rc == 0 else ('·' if rc == 2 else '✗')} ste 위임({r['state']}) {r['detail']}")
        return rc

    try:
        r = probe(a.email, a.timeout)
    except Exception as exc:  # noqa: BLE001 — 붙지 못함(게이트웨이 무응답·모듈 없음)
        msg = f"게이트웨이에 붙지 못했다: {exc!r}"
        print(json.dumps({"as": a.email, "error": msg, "rc": 2}, ensure_ascii=False) if a.json else f"✗ {msg}")
        return 2
    rc = 0 if r["steps"] and all(s["verdict"] == "ok" for s in r["steps"]) else 1
    if a.json:
        print(json.dumps({**r, "rc": rc}, ensure_ascii=False))
    else:
        if r["groups"] == "service":
            print("  · 포털에서 이 사람의 권한을 못 읽어 내부 서비스 신분으로 불렀다 — 권한(plat:smarttwin) 판정은 빠졌다")
        for s in r["steps"]:
            mark = "✓" if s["verdict"] == "ok" else "✗"
            label = {"token": "토큰 경로", "slurm": "slurm 경로"}[s["what"]]
            print(f"  {mark} {label}({s['tool']}) {s['verdict']} {s['detail']}".rstrip())
    return rc


if __name__ == "__main__":
    sys.exit(main())
