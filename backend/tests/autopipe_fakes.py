# 자동 파이프라인 시험의 가짜 — 계약 v1.1 꼴 그대로의 원천 · 해석 앱과, 그 도구를 /tools-map · MCP(tools/call)로 내주는 게이트웨이(MockTransport)
"""가짜는 진짜 꼴로(메모리 test-fakes-must-match-real-shape). 게이트웨이는 진짜처럼
- /tools-map 은 map(노출 이름 → 백엔드) · orig(노출 이름 → 원래 이름, 다를 때만) · apps[].reachable 을 준다. 허브 가족은 늘 접두가 붙는다
  (<백엔드에서 하이픈 뺀 것>_<원래 이름>).
- POST /mcp 는 initialize(mcp-session-id) · notifications/initialized · tools/call(SSE data: 줄, result{content[text], isError}) · DELETE 를 받는다.
- 서비스 허용 목록 밖 도구는 isError=true 와 'forbidden: … service-denied(not-listed)' 글이다(gateway.py 와 같은 꼴).
- 앱을 raises=True 로 만들면 오류를 예외로 올리는 FastMCP 앱(StepForge)처럼 글 앞에 'Error executing tool <원래 이름>: ' 가 붙는다.
  기본(False)은 CallToolResult 를 직접 내는 앱(DynaForge `_auto_out`) — 머리 없는 JSON 이다.
앱은 contract.md §1 · §2 의 답 꼴 그대로다 — 같은 idem_key 로 다시 내면 created:false 로 같은 run_ref.
"""
from __future__ import annotations

import asyncio
import copy
import json

import httpx

from app.autopipe import spec as S
from app.autopipe.engine import Engine
from app.autopipe.store import AutoStore
from app.config import Settings
from app.procedures.store import ProceduresStore

T0 = 1_800_000_000          # 시험 시계의 시작(2027-01-15 08:00 UTC = 17:00 KST)


def iso(ts: int) -> str:
    from datetime import UTC, datetime
    return datetime.fromtimestamp(ts, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def envelope(run_ref: str, subject: dict, profile: str, *, verdict: str = "pass", metrics: list | None = None,
             app_version: str = "abc12345", **over) -> dict:
    env = {"run_ref": run_ref, "subject": subject, "profile": profile, "app_version": app_version, "verdict": verdict,
           "metrics": metrics if metrics is not None else [
               {"name": "sed_max", "label": "솔더 SED 최대", "unit": "MJ/m3", "value": 0.82, "limit": 1.0, "limit_source": "사내 기준",
                "verdict": "pass"}],
           "figures": [{"ref": "fig-1", "caption": "SED 분포"}], "artifacts": [{"kind": "d3plot", "location": "/cluster/run/1"}],
           "inputs": [{"kind": "cad_assembly", "ref": "cad-1", "sha256": "a" * 64}], "notes": [], "finished_at": "2027-01-15T09:00:00Z"}
    env.update(over)
    return env


class FakeAnalysis:
    """해석 앱 — auto_profiles · auto_check · auto_submit · auto_status · auto_result (+ 선택 auto_cancel)."""

    def __init__(self, backend: str, *, profile: str = "default", sync: bool = False, service_identity: bool = True,
                 with_cancel: bool = False, raises: bool = False) -> None:
        self.backend = backend
        self.raises = raises
        self.profile = profile
        self.sync = sync
        self.service_identity = service_identity
        self.tools = ["auto_profiles", "auto_check", "auto_submit", "auto_status", "auto_result"] + (["auto_cancel"] if with_cancel else [])
        self.check_answer: dict | None = None        # None 이면 준비됨
        self.status_seq: list[str] = ["running", "done"]
        self.result_over: dict = {}
        self.result_raw = None                        # 주면 봉투 대신 이것을 그대로 낸다(꼴 틀림 시험)
        self.runs: dict[str, dict] = {}               # run_ref → {idem, subject, state, polls}
        self.by_idem: dict[str, str] = {}
        self.calls: list[tuple[str, dict]] = []
        self.lose_submit = 0                          # 이만큼 제출 답을 잃는다(실행은 선다 — 게이트웨이 502)
        self.metrics: list | None = None
        self.verdict = "pass"
        self.fail: dict[str, dict] = {}               # 도구 → 본문 — 주면 그 도구는 isError=true 로 이것을 낸다(not_ready · not_done 등)

    def handle(self, tool: str, args: dict):
        """(isError, 답 dict) 또는 ('lost', None)."""
        self.calls.append((tool, args))
        if tool in self.fail:
            return True, self.fail[tool]
        if tool == "auto_profiles":
            return False, {"app_version": "abc12345", "service_identity": self.service_identity,
                           "profiles": [{"id": self.profile, "title": "기본 조건", "inputs": [{"kind": "cad_assembly", "required": True}],
                                         "cost": {} if self.sync else {"cores": 64, "minutes": 240, "cluster": "stcx"}, "sync": self.sync,
                                         "criteria_source": "사내 기준", "outputs": ["verdict", "metrics"]}]}
        if tool == "auto_check":
            if self.check_answer is not None:
                return False, self.check_answer
            return False, {"ready": True, "missing": [], "inputs": [{"kind": "cad_assembly", "ref": "cad-1", "sha256": "a" * 64}]}
        if tool == "auto_submit":
            if self.check_answer is not None and not self.check_answer.get("ready"):
                return True, {"error": "not_ready", "detail": "입력이 없다", "missing": self.check_answer.get("missing")}
            key = args["idem_key"]
            created = key not in self.by_idem
            if created:
                ref = f"{self.backend[-6:]}-r{len(self.runs) + 1}"
                self.by_idem[key] = ref
                self.runs[ref] = {"idem": key, "subject": args["subject"], "state": "done" if self.sync else "queued", "polls": 0,
                                  "upstream": args.get("upstream")}
            ref = self.by_idem[key]
            if self.lose_submit > 0:        # 실행은 섰고(또는 이미 있고) 답만 잃는다
                self.lose_submit -= 1
                return "lost", None
            return False, {"run_ref": ref, "state": self.runs[ref]["state"], "created": created}
        if tool == "auto_status":
            run = self.runs.get(args["run_ref"])
            if run is None:
                return True, {"error": "unknown_run", "detail": "그런 실행이 없다"}
            run["polls"] += 1
            if run["state"] not in ("done", "failed", "cancelled"):
                run["state"] = self.status_seq[min(run["polls"] - 1, len(self.status_seq) - 1)]
            return False, {"state": run["state"], "progress": 1.0 if run["state"] == "done" else 0.5, "detail": "진행"}
        if tool == "auto_result":
            run = self.runs.get(args["run_ref"])
            if run is None or run["state"] != "done":
                return True, {"error": "not_done", "detail": "아직 안 끝났다"}
            if self.result_raw is not None:
                return False, self.result_raw
            env = envelope(args["run_ref"], run["subject"], self.profile, verdict=self.verdict, metrics=self.metrics)
            env.update(self.result_over)
            return False, env
        if tool == "auto_cancel":
            run = self.runs.get(args["run_ref"])
            if run is not None:
                run["state"] = "cancelled"
            return False, {"run_ref": args["run_ref"], "state": "cancelled"}
        return True, {"error": "unknown_tool"}


class FakeSource:
    """원천 앱 — auto_changes(since, limit). 커서는 항목 순번 글이다(불투명)."""

    def __init__(self, backend: str, page: int = 200, *, raises: bool = False) -> None:
        self.backend = backend
        self.raises = raises
        self.error: dict | None = None      # 주면 isError=true 로 이것을 낸다(bad_since 등)
        self.tools = ["auto_changes"]
        self.items: list[dict] = []
        self.page = page
        self.calls: list[tuple[str, dict]] = []
        self.raw = None                     # 주면 그대로 낸다(꼴 틀림 시험)

    def add(self, project, revision, *, ref: str = "p-1", sha: str = "a" * 64, at: int = T0, parsed: bool = True,
            kind: str = "cad_assembly") -> None:
        self.items.append({"subject": {"project": project, "revision": revision, "refs": {"step_forge": ref}},
                           "inputs": [{"kind": kind, "ref": ref, "sha256": sha, "at": iso(at)}], "ready": {"parsed": parsed},
                           "updated_at": iso(at)})

    def handle(self, tool: str, args: dict):
        self.calls.append((tool, args))
        if self.error is not None:
            return True, self.error
        if self.raw is not None:
            return False, self.raw
        start = int(args.get("since") or 0)
        lim = min(int(args.get("limit") or 200), self.page)
        chunk = self.items[start:start + lim]
        end = start + len(chunk)
        return False, {"items": chunk, "next_since": str(end), "complete": end >= len(self.items)}


class FakeGateway:
    """MockTransport 처리기 — 앱들을 노출하고 호출 · 토큰을 적는다. allowed 를 주면 그 '백엔드:원래 이름' 만 서비스 신원에 연다."""

    def __init__(self, *apps, allowed: set | None = None) -> None:
        self.apps = {a.backend: a for a in apps}
        self.allowed = allowed
        self.tokens: list[str] = []
        self.calls: list[tuple[str, str, dict]] = []
        self.unreachable: set = set()
        self.down = False

    def exposed(self, backend: str, orig: str) -> str:
        return backend.replace("-", "") + "_" + orig

    def tools_map(self) -> dict:
        m, o = {}, {}
        for bk, a in self.apps.items():
            if bk in self.unreachable:
                continue
            for t in a.tools:
                n = self.exposed(bk, t)
                m[n] = bk
                o[n] = t
        m["search_tools"] = "_gateway"
        return {"map": m, "orig": o, "apps": [{"app": bk, "label": bk, "reachable": bk not in self.unreachable} for bk in self.apps]
                + [{"app": "_gateway", "reachable": True}]}

    def __call__(self, req: httpx.Request) -> httpx.Response:
        if self.down:
            raise httpx.ConnectError("게이트웨이 내려감")
        if req.method == "GET" and req.url.path.endswith("/tools-map"):
            return httpx.Response(200, json=self.tools_map())
        if req.method == "DELETE":
            return httpx.Response(200)
        body = json.loads(req.content or b"{}")
        auth = req.headers.get("authorization", "")
        if body.get("method") == "initialize":
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": {}}, headers={"mcp-session-id": "sess"})
        if body.get("method") == "notifications/initialized":
            return httpx.Response(202)
        if body.get("method") == "tools/call":
            self.tokens.append(auth.removeprefix("Bearer "))
            name = body["params"]["name"]
            args = body["params"].get("arguments") or {}
            hit = next(((bk, o) for bk, a in self.apps.items() for o in a.tools if self.exposed(bk, o) == name), None)
            if hit is None:
                return self._sse({"content": [{"type": "text", "text": f"unknown tool: {name}"}], "isError": True})
            bk, orig = hit
            self.calls.append((bk, orig, args))
            if self.allowed is not None and f"{bk}:{orig}" not in self.allowed:
                return self._sse({"content": [{"type": "text", "text": f"forbidden: {name} — service-denied(not-listed): 허용 목록에 없다"}],
                                  "isError": True})
            is_err, data = self.apps[bk].handle(orig, args)
            if is_err == "lost":
                return httpx.Response(502, text="bad gateway")
            text = json.dumps(data, ensure_ascii=False)
            if is_err and getattr(self.apps[bk], "raises", False):
                text = f"Error executing tool {orig}: {text}"      # FastMCP 가 올린 예외에 붙이는 머리(이름은 앱의 원래 이름)
            return self._sse({"content": [{"type": "text", "text": text}], "isError": bool(is_err)})
        return httpx.Response(400)

    @staticmethod
    def _sse(result: dict) -> httpx.Response:
        payload = {"jsonrpc": "2.0", "id": 2, "result": result}
        return httpx.Response(200, text=f"event: message\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n",
                              headers={"content-type": "text/event-stream"})

    def count(self, orig: str, backend: str | None = None) -> int:
        return sum(1 for bk, o, _ in self.calls if o == orig and (backend is None or bk == backend))


# ── 엔진 하네스(원장 · 엔진 · 가짜 게이트웨이 · 시계) — 엔진 · 보고서 · RA 시험이 같이 쓴다 ─────────────────────────────────
SRC = "heax-step_forge"
THERMAL = "heax-thermal_shock_mcp"
DROP = "heax-kooremapper_mcp"
SPEC = {"title": "낙하 · 열충격 기본", "stage": "auto",
        "scope": {"all_projects": True, "exclude": []},
        "trigger": {"ready_when": ["step_forge.parsed"], "quiet_s": 600},
        "steps": [{"id": "thermal", "kind": "analysis", "app": "thermal_shock_mcp", "profile": "default"},
                  {"id": "summary", "kind": "report", "report": "summary", "needs": ["thermal"]}]}


class Harness:
    def __init__(self, tmp_path, *apps, settings_over: dict | None = None, allowed=None):
        self.t = T0
        self.settings = Settings(_env_file=None, procedures_store_path=str(tmp_path / "wb.sqlite"), auto_pipeline_enabled=True,
                                 auto_pipeline_tick_s=0, mcp_gateway_url="http://gw.test", **(settings_over or {}))
        self.base = ProceduresStore(self.settings)
        self.store = AutoStore(self.base)
        self.src = FakeSource(SRC)
        self.apps = {a.backend: a for a in apps}
        self.gw = FakeGateway(self.src, *apps, allowed=allowed)
        self.loop = asyncio.new_event_loop()
        self.client = httpx.AsyncClient(transport=httpx.MockTransport(self.gw))
        self.engine = self.new_engine()

    def new_engine(self) -> Engine:
        return Engine(settings=self.settings, store=self.store, mint=lambda run, step: f"tok-{run}-{step}", client=self.client,
                      clock=lambda: self.t)

    def rule(self, spec=None, *, enable=True) -> str:
        sp = S.parse(copy.deepcopy(spec or SPEC))
        rid = self.store.create_rule(spec=sp, by="maker@example.com", now=self.t)["id"]
        if enable:
            self.store.set_enabled(rule_id=rid, enabled=True, by="maker@example.com", now=self.t)
        return rid

    def tick(self, dt: int = 0) -> dict:
        self.t += dt
        return self.loop.run_until_complete(self.engine.tick())

    def runs(self, **kw):
        return self.store.runs(**kw)

    def steps(self, run_id) -> dict:
        return {s["step_id"]: s for s in self.store.steps(run_id)}

    def close(self):
        self.loop.run_until_complete(self.client.aclose())
        self.loop.close()
        self.base.close()


def ready_run(h, project="TASK-A", revision="dv1", **add):
    """주제를 하나 넣고 조용해질 때까지 박자를 돌려 실행 하나를 세운다."""
    h.src.add(project, revision, at=h.t + 10, **add)
    h.tick(20)
    assert h.runs() == [], "조용해지기 전에는 실행이 없다"
    h.tick(700)
    runs = [r for r in h.runs() if r["project"] == project and r["revision"] == revision]
    assert len(runs) == 1, runs
    return runs[0]


