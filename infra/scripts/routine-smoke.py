#!/usr/bin/env python3
# 분석 루틴을 각본 MCP 클라이언트로 끝까지 한 번 돌려 보는 실물 점검 — 포털 원장 · 게이트웨이 울타리 · 실제 백엔드(LLM 없이, docs/analysis-routines R5)
"""사람 PAT 하나로 게이트웨이 루틴 도구를 차례로 부른다 — 계획을 읽고, 실행을 세우고, 각본에 적은 도구를 단계 울타리 안에서 부르고, 단계를 닫고,
보고서를 낸다. 덤으로 울타리(읽기로 확인 안 된 도구는 거절) · 멈춤(routine_run_start cancel) · prompts 를 본다. LLM 은 쓰지 않는다 — 실행기 자리를
이 각본이 맡는다(Claude 길과 같은 계약). 챗(Qwen) 길은 챗 LLM 이 있는 박스에서 화면으로 본다.

  HWAX_GATEWAY_PAT=<포털 /tokens 에서 발급한 PAT — feat:routines 가 있는 사람> \\
    python3 infra/scripts/routine-smoke.py --scenario <각본.json>

각본(JSON) —
  {"routine_id": "<절차 › 루틴의 id>", "inputs": {"model": "S26"}, "note": "스모크",
   "calls": {"<단계 id>": [{"name": "<백엔드>:<원래 이름>", "arguments": {...}}]},
   "fence_probe": "<백엔드>:<읽기로 확인 안 된 도구>",   # 선택 — 거절돼야 한다
   "cancel_probe": true}                                   # 선택 — 새 실행을 세워 멈춘다

PAT 는 화면 · 로그에 찍지 않는다(환경변수로만). 끝나면 세션을 닫는다. 돌린 실행은 포털 원장에 남는다(절차 › 루틴 › 실행 이력).
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

GW = os.environ.get("HWAX_GATEWAY_URL", "http://127.0.0.1:9110/mcp")
PAT = os.environ.get("HWAX_GATEWAY_PAT", "").strip()
TIMEOUT = float(os.environ.get("ROUTINE_SMOKE_TIMEOUT_S", "900"))


class Gw:
    """게이트웨이 MCP 원 세션 — initialize → initialized → tools/call · prompts/* → DELETE."""

    def __init__(self) -> None:
        self.sid = ""
        self.n = 0

    def _post(self, body: dict) -> tuple[dict, dict]:
        h = {"Authorization": f"Bearer {PAT}", "Content-Type": "application/json",
             "Accept": "application/json, text/event-stream"}
        if self.sid:
            h["mcp-session-id"] = self.sid
        req = urllib.request.Request(GW, data=json.dumps(body).encode(), headers=h, method="POST")
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            text = r.read().decode("utf-8", "replace")
            headers = dict(r.headers)
        env = {}
        for line in text.splitlines():          # 마지막 data: 줄이 정본이다(SSE), 아니면 JSON 그대로
            if line.startswith("data:"):
                env = json.loads(line[5:].strip())
        if not env and text.strip().startswith("{"):
            env = json.loads(text)
        return env, headers

    def open(self) -> None:
        env, headers = self._post({"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {
            "protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "routine-smoke", "version": "1"}}})
        self.sid = headers.get("mcp-session-id") or headers.get("Mcp-Session-Id") or ""
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})
        if "error" in env:
            raise SystemExit(f"initialize 실패 — {env['error']}")

    def rpc(self, method: str, params: dict) -> dict:
        self.n += 1
        env, _ = self._post({"jsonrpc": "2.0", "id": self.n, "method": method, "params": params})
        if "error" in env:
            raise RuntimeError(f"{method} 오류 — {env['error']}")
        return env.get("result") or {}

    def tool(self, name: str, args: dict) -> tuple[bool, str, list[str]]:
        """(isError, 첫 글, 나머지 글들)."""
        res = self.rpc("tools/call", {"name": name, "arguments": args})
        texts = [c.get("text", "") for c in res.get("content") or [] if c.get("type") == "text"]
        return bool(res.get("isError")), (texts[0] if texts else ""), texts[1:]

    def close(self) -> None:
        if not self.sid:
            return
        req = urllib.request.Request(GW, headers={"Authorization": f"Bearer {PAT}", "mcp-session-id": self.sid}, method="DELETE")
        try:
            urllib.request.urlopen(req, timeout=10).read()
        except (urllib.error.URLError, OSError):
            pass


def _json(text: str) -> dict:
    try:
        return json.loads(text)
    except ValueError:
        return {}


def main() -> int:
    ap = argparse.ArgumentParser(description="분석 루틴 각본 MCP 점검(LLM 없이)")
    ap.add_argument("--scenario", required=True, help="각본 JSON 파일")
    a = ap.parse_args()
    if not PAT:
        print("HWAX_GATEWAY_PAT 가 비었다 — 포털 /tokens 에서 발급한 사람 PAT(feat:routines)를 환경변수로 준다", file=sys.stderr)
        return 2
    sc = json.load(open(a.scenario, encoding="utf-8"))
    rid = sc["routine_id"]
    results: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> bool:
        results.append((name, ok, detail[:300]))
        print(f"{'✓' if ok else '✗'} {name}" + (f" — {detail[:300]}" if detail else ""))
        return ok

    gw = Gw()
    gw.open()
    try:
        prompts = gw.rpc("prompts/list", {}).get("prompts") or []
        check("prompts/list 에 그 루틴", any(p.get("name") == f"routine-{rid}" for p in prompts), f"{len(prompts)}개")
        err, head, _ = gw.tool("routine_get", {"routine_id": rid})
        plan = _json(head)
        if not check("routine_get 계획", not err and bool(plan.get("steps")), head if err else f"단계 {len(plan.get('steps') or [])}"):
            return 1
        err, head, _ = gw.tool("routine_run_start", {"routine_id": rid, "inputs": sc.get("inputs") or {}, "note": sc.get("note") or "각본 점검"})
        view = _json(head)
        run_id = (view.get("run") or {}).get("id") or ""
        if not check("routine_run_start", not err and bool(run_id), head if err else f"run {run_id} · {view['run'].get('state')}"):
            return 1
        probe = sc.get("fence_probe")
        steps = view.get("steps") or []
        open_steps = [s for s in steps if s.get("state") in ("pending", "running")]
        if probe and open_steps:
            first = next((s for s in open_steps if s.get("kind") != "deliberation"), None)
            if first:
                err, head, _ = gw.tool("routine_call", {"run_id": run_id, "step": first["id"], "name": probe, "arguments": {}})
                check("울타리 — 읽기로 확인 안 된 도구는 거절", head.startswith("ROUTINE_ERROR"), head)
        for st in steps:
            sid = st["id"]
            if st.get("state") not in ("pending", "running"):
                check(f"단계 {sid} — 시작 때 닫힘", True, f"{st.get('state')}: {st.get('reason') or ''}")
                continue
            refs, ok_any = [], False
            for c in (sc.get("calls") or {}).get(sid) or []:
                err, head, body = gw.tool("routine_call", {"run_id": run_id, "step": sid, "name": c["name"], "arguments": c.get("arguments") or {}})
                h = _json(head)
                good = bool(h.get("routine_call")) and h.get("ok") is True
                check(f"단계 {sid} 호출 {c['name']}", good, head if not h else f"{h.get('routine_call')} · {h.get('chars')}자")
                if h.get("routine_call"):
                    refs.append(h["routine_call"])
                ok_any = ok_any or good
            env = {"status": "ok" if ok_any else ("failed" if refs else "skipped"),
                   "summary": f"각본 점검 — 호출 {len(refs)}건", "keys": {},
                   "findings": [{"text": "각본 점검의 근거", "refs": refs[:10]}] if refs else []}
            err, head, _ = gw.tool("routine_step_done", {"run_id": run_id, "step": sid, **env})
            done = _json(head)
            check(f"단계 {sid} 닫기", not err and bool(done.get("state")), head if err else f"{done.get('state')} · 실행 {done.get('run_state')}")
            if done.get("run_state") not in (None, "running"):
                break
        err, head, _ = gw.tool("routine_get", {"run_id": run_id})
        if _json(head).get("run", {}).get("state") == "running":
            err, head, _ = gw.tool("routine_report_submit", {"run_id": run_id, "sections": {"insight": "각본 점검 — 인사이트 자리."}})
            rep = _json(head)
            check("routine_report_submit", not err and bool(rep.get("report_md")),
                  head if err else f"보고서 {len(rep.get('report_md') or '')}자 · RA {rep.get('ra_report_id') or rep.get('ra_error') or rep.get('ra_next') or '-'}")
        err, head, _ = gw.tool("routine_get", {"run_id": run_id})
        check("실행이 끝났다", _json(head).get("run", {}).get("state") in ("done", "failed", "waiting"), _json(head).get("run", {}).get("state") or head)
        if sc.get("cancel_probe"):
            err, head, _ = gw.tool("routine_run_start", {"routine_id": rid, "inputs": sc.get("inputs") or {}, "note": "멈춤 점검"})
            rid2 = (_json(head).get("run") or {}).get("id")
            if rid2:
                err, head, _ = gw.tool("routine_run_start", {"run_id": rid2, "cancel": True})
                check("멈춤 — routine_run_start cancel", not err and "cancelled" in head, head)
    finally:
        gw.close()
    bad = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(bad)}/{len(results)} 통과" + (f" — 실패: {', '.join(r[0] for r in bad)}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
