"""실행기 — 절차를 한 단계씩 돌리고 실행에 남긴다. **챗과 자원을 공유하지 않는다.**

격리가 이 파일의 절반이다(PLAN §3). 자기 세마포어·자기 httpx 클라이언트·실행당 MCP 세션 하나.

게이트웨이 호출은 `agent/upload.py:mcp_call` 의 **방식만** 따르고 **베끼지 않는다**. 그 함수는
JSON-RPC `error` 만 보고 `result.isError` 를 버리며, `content[0]` 만 취하고, 파싱 실패를
`{"raw": …}` 로 정상 반환한다 — 셋 다 실패를 성공으로 만든다(context-notes W-16).

시간은 PLAN §5-10 이다. 게이트웨이 상한이 120초이고 실측이 이미 그 위에 있다
(`search_catalog_property` 세션 첫 호출 120.3초). 넘기면 그 백엔드 영속 세션이 재연결되면서
같은 백엔드에 걸린 챗·심의 호출까지 끊긴다.
"""

import asyncio
import json
import logging
import time

import httpx

from app.procedures import dispatch
from app.procedures import judge as J
from app.procedures import template
from app.procedures.models import ProcedureSpec, Step, schema_fingerprint
from app.procedures.store import ProceduresStore

logger = logging.getLogger(__name__)

# 실행기 클라이언트는 게이트웨이(120초)보다 **늦게** 포기한다 — 재연결 재시도 한 번까지 덮는다.
# 먼저 포기하면 쓰기는 그 뒤 완료되고 실행에는 unknown 만 남아 사람이 확인해야 한다.
CLIENT_TIMEOUT = 260.0
# 단계 자체의 상한. 게이트웨이 120초보다 짧게 둬 우리가 먼저 끊고 기록을 남긴다.
EXPECT_TIMEOUT = {"fast": 30.0, "slow": 110.0, "job": 110.0}
WARMUP_TIMEOUT = 125.0  # 콜드스타트가 120.3초다 — 워밍업은 그걸 넘겨 기다린다


class RunnerError(RuntimeError):
    """실행기가 단계를 시작조차 못 했다(세션·권한·사전검사)."""


def _last_data(text: str) -> dict:
    """SSE 응답에서 마지막 `data:` 줄의 JSON. 게이트웨이는 event-stream 으로 답한다."""
    lines = [ln[6:] for ln in text.splitlines() if ln.startswith("data: ")]
    return json.loads(lines[-1]) if lines else json.loads(text)


class GatewaySession:
    """실행 하나에 MCP 세션 하나. 종료·정지·예외 시 `finally` 에서 닫는다.

    `mcp_call` 은 호출마다 세션을 만들고 **안 닫는다.** 게이트웨이 SDK 는 세션 유휴 만료가
    없어서 폴링처럼 반복 호출하면 챗과 공유하는 게이트웨이에 세션이 쌓인다.
    """

    def __init__(self, gateway_url: str, client: httpx.AsyncClient,
                 corr: str | None = None) -> None:
        self.url = gateway_url.rstrip("/") + "/mcp"
        self._c = client
        self.sid: str | None = None
        # 어느 실행의 호출인가. 게이트웨이 감사에 `corr` 로 남아 **감사 줄과 실행이 이어진다**
        # (PLAN §9-9 ⑥). 챗은 도구 연결을 그룹 집합으로 캐시해서 여기 붙이면 대화마다 캐시가
        # 쪼개진다 — 절차는 **세션이 실행 단위**라 붙일 자리가 여기다.
        self.corr = corr

    def _hdr(self, pat: str) -> dict:
        h = {"Authorization": f"Bearer {pat}", "Content-Type": "application/json",
             "Accept": "application/json, text/event-stream"}
        if self.sid:
            h["mcp-session-id"] = self.sid
        if self.corr:
            h["X-HWAX-Corr"] = self.corr
        return h

    async def open(self, pat: str) -> None:
        r = await self._c.post(self.url, headers=self._hdr(pat), json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                       "clientInfo": {"name": "portal-procedures", "version": "1"}}})
        if r.status_code != 200:
            raise RunnerError(f"게이트웨이 초기화 실패 ({r.status_code})")
        self.sid = r.headers.get("mcp-session-id") or None
        await self._c.post(self.url, headers=self._hdr(pat),
                           json={"jsonrpc": "2.0", "method": "notifications/initialized"})

    async def close(self, pat: str) -> None:
        if not self.sid:
            return
        try:
            await self._c.request("DELETE", self.url, headers=self._hdr(pat))
        except Exception:  # noqa: BLE001 — 닫기 실패로 실행을 실패시키지 않는다
            logger.warning("절차 MCP 세션 닫기 실패 sid=%s", self.sid, exc_info=True)
        finally:
            self.sid = None

    async def call(self, name: str, arguments: dict, pat: str, timeout: float
                   ) -> tuple[bool, list]:
        """`(isError, content[])` 를 **그대로** 돌려준다. 판정은 judge 가 한다."""
        r = await self._c.post(self.url, headers=self._hdr(pat), timeout=timeout, json={
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": name, "arguments": arguments}})
        if r.status_code != 200:
            return True, [{"type": "text", "text": f"게이트웨이 HTTP {r.status_code}"}]
        env = _last_data(r.text)
        if env.get("error"):
            e = env["error"]
            msg = e.get("message") if isinstance(e, dict) else str(e)
            return True, [{"type": "text", "text": f"JSON-RPC 오류: {msg}"}]
        res = env.get("result") or {}
        return bool(res.get("isError")), (res.get("content") or [])

    async def list_tools(self, pat: str, timeout: float = 60.0) -> dict:
        """`{노출이름: {description, inputSchema}}`. 권한 필터는 여기가 정본이다."""
        out: dict = {}
        cursor = None
        for _ in range(20):  # 페이지 폭주 방어
            params = {"cursor": cursor} if cursor else {}
            r = await self._c.post(self.url, headers=self._hdr(pat), timeout=timeout, json={
                "jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": params})
            if r.status_code != 200:
                raise RunnerError(f"tools/list 실패 ({r.status_code})")
            env = _last_data(r.text)
            res = env.get("result") or {}
            for t in res.get("tools") or []:
                out[t.get("name")] = {"description": t.get("description") or "",
                                      "inputSchema": t.get("inputSchema") or {}}
            cursor = res.get("nextCursor")
            if not cursor:
                break
        return out


class ProceduresRunner:
    """실행 하나를 끝까지(또는 게이트·실패까지) 돌린다.

    `mint_pat`·`is_active` 는 주입받는다 — 시험이 keystore·user_store 를 안 세워도 되게.
    """

    def __init__(self, *, settings, store: ProceduresStore, mint_pat, is_active=None,
                 client: httpx.AsyncClient | None = None) -> None:
        self.settings = settings
        self.store = store
        self.mint_pat = mint_pat
        self.is_active = is_active or (lambda _email: True)
        self.gateway_url = getattr(settings, "mcp_gateway_url", None) or \
            "http://127.0.0.1:9110"
        n = int(getattr(settings, "procedures_concurrency", 2) or 2)
        # 챗의 agent_semaphore(64)를 **재사용하지 않는다** — 넘치면 큐 없이 429 라 챗이 막힌다.
        self.sem = asyncio.Semaphore(n)
        self._own_client = client is None
        self._client = client or httpx.AsyncClient(timeout=CLIENT_TIMEOUT)
        # slow 단계가 도는 동안 같은 백엔드에 다른 단계를 걸지 않는다 — 재연결이 나면
        # 그 백엔드의 다른 실행까지 끊긴다.
        self._backend_locks: dict[str, asyncio.Lock] = {}

    async def aclose(self) -> None:
        if self._own_client:
            await self._client.aclose()

    def _blk(self, backend: str) -> asyncio.Lock:
        lk = self._backend_locks.get(backend)
        if lk is None:
            lk = self._backend_locks[backend] = asyncio.Lock()
        return lk

    # ── 실행 ────────────────────────────────────────────────────────────────
    async def run(self, *, run_id: str, spec: ProcedureSpec, principal, scope: dict | None = None,
                  start_at: int = 0) -> dict:
        """`start_at` 부터 단계를 돈다. 게이트·실패·취소에서 멈추고 상태를 남긴다."""
        run = self.store.get_run(run_id)
        if run is None:
            raise RunnerError(f"실행이 없다: {run_id}")
        mode = run.get("mode") or "plan"
        scope = dict(scope or run.get("inputs") or {})
        scope.setdefault("run_id", run_id)
        scope.setdefault("me.email", getattr(principal, "email", "") or "")
        scope.setdefault("me.sub", getattr(principal, "subject", "") or "")

        if mode == "plan":
            return self._plan(run_id, spec, scope)

        async with self.sem:  # 게이트에서 멈춘 실행은 이 블록 밖이라 슬롯을 쥐지 않는다
            sess = GatewaySession(self.gateway_url, self._client, corr=run_id)
            pat = self.mint_pat(principal, run_id, start_at)
            if not pat:
                raise RunnerError("사용자 명의 PAT 발급 실패 — 서비스 계정으로 대신 돌지 않는다")
            try:
                await sess.open(pat)
                catalog = await sess.list_tools(pat)
                drift = self._check_drift(spec, catalog)
                if drift:
                    self.store.set_run_state(run_id, "failed", stage="schema_drift",
                                             ended=True)
                    return {"state": "failed", "stage": "schema_drift", "detail": drift}
                self.store.set_run_state(run_id, "running")
                return await self._loop(run_id, spec, scope, principal, sess, start_at)
            finally:
                try:
                    await sess.close(self.mint_pat(principal, run_id, -1) or pat)
                except Exception:  # noqa: BLE001
                    logger.warning("세션 정리 실패 run=%s", run_id, exc_info=True)

    def _plan(self, run_id: str, spec: ProcedureSpec, scope: dict) -> dict:
        """계획 모드 — 게이트웨이를 **부르지 않는다.** 부를 호출 목록만 보여 준다."""
        calls, unknown = [], []
        known = set(scope)
        for ix, st in enumerate(spec.steps):
            try:
                args = template.substitute(st.args, scope) if _resolvable(st, known) else st.args
                pending = not _resolvable(st, known)
            except template.TemplateError:
                args, pending = st.args, True
            calls.append({"ix": ix, "backend": st.backend, "tool": st.tool,
                          "alias": st.alias, "gate": st.gate, "expect": st.expect,
                          "args": args, "unverified": pending})
            if pending:
                unknown.append(st.tool)
            known |= set((st.save or {}).keys())
        self.store.set_run_state(run_id, "done", stage="plan", ended=True)
        return {"state": "done", "stage": "plan", "calls": calls, "unverified": unknown}

    def _check_drift(self, spec: ProcedureSpec, catalog: dict) -> list[str]:
        """도구에 판본이 없으니 **변화를 잡아 멈추는 것까지** 한다(PLAN §5-8)."""
        out = []
        for i, st in enumerate(spec.steps, 1):
            meta = catalog.get(st.alias) or catalog.get(st.tool)
            if meta is None:
                out.append(f"{i}단계 {st.tool}: 게이트웨이에 없다({st.alias})")
                continue
            if not st.schema_fp:
                continue
            now = schema_fingerprint(meta["description"], meta["inputSchema"])
            if now != st.schema_fp:
                out.append(f"{i}단계 {st.tool}: 스키마가 바뀌었다 "
                           f"({st.schema_fp} → {now}) — 자동 진행하지 않는다")
        return out

    async def _loop(self, run_id, spec, scope, principal, sess, start_at) -> dict:
        for ix in range(start_at, len(spec.steps)):
            st = spec.steps[ix]

            # 단계 경계에서 취소·중단을 본다
            run = self.store.get_run(run_id)
            if run is None or run["state"] in ("cancelled", "failed"):
                return {"state": run["state"] if run else "unknown", "stopped_at": ix}
            email = getattr(principal, "email", "") or ""
            if email and not self.is_active(email):
                self.store.set_run_state(run_id, "failed", stage="owner_inactive", ended=True)
                return {"state": "failed", "stage": "owner_inactive", "stopped_at": ix}

            # 게이트 — 승인이 없으면 여기서 멈춘다. 인자 지문에 묶인 1회용 승인이다.
            if st.gate == "human":
                args = template.substitute(st.args, scope)
                ack = self.store.gate_ack(run_id, ix)
                want = _sha(args)
                if ack is None or ack["args_sha256"] != want:
                    self.store.begin_step(run_id, ix, backend=st.backend, tool=st.tool,
                                          args=args, schema_fp=st.schema_fp,
                                          expect=st.expect, mode="live")
                    self.store.finish_step(run_id, ix, ok=False, state="pending",
                                           error=None, stage="gate")
                    self.store.set_run_state(run_id, "gated", stage=f"step:{ix}")
                    return {"state": "gated", "stopped_at": ix, "args_sha256": want}

            v = await self._one(run_id, ix, st, scope, principal, sess)
            if v is None:  # warmup — 결과를 버린다
                continue
            if not v.ok:
                self.store.set_run_state(run_id, "failed", stage=f"step:{ix}", ended=True)
                return {"state": "failed", "stopped_at": ix, "kind": v.kind,
                        "error": J.short_error(v)}
            for key, path in (st.save or {}).items():
                scope[key] = template.extract(v.parsed, path)

            # 선택 — 룰이 고른 것을 범위에 담는다(PLAN §10-1). 0/1/N 이 여기서 갈린다.
            if st.select is not None:
                picked = self._pick(run_id, ix, st, v, scope)
                if picked is not None:
                    return picked   # 0개 실패 · 여럿이라 사람에게 묻는다

        self.store.set_run_state(run_id, "done", ended=True)
        return {"state": "done"}

    async def step_once(self, *, run_id: str, step: Step, principal,
                        scope: dict | None = None) -> dict:
        """빈 실행에 단계 하나 — **절차 기능의 진입점**이다(저장된 절차 목록이 아니다).

        세션을 열고 한 단계만 돌리고 닫는다. 여러 단계를 이어 붙이는 것은 사람이 화면에서
        한다 — 그 기록이 나중에 "절차로 저장" 의 재료가 된다.
        """
        run = self.store.get_run(run_id)
        if run is None:
            raise RunnerError(f"실행이 없다: {run_id}")
        ix = len(run["steps"])
        if any(s["state"] == "running" for s in run["steps"]):
            raise RunnerError("이미 도는 단계가 있다")

        scope = dict(scope or run.get("inputs") or {})
        scope.setdefault("run_id", run_id)
        scope.setdefault("me.email", getattr(principal, "email", "") or "")
        scope.setdefault("me.sub", getattr(principal, "subject", "") or "")

        async with self.sem:
            sess = GatewaySession(self.gateway_url, self._client, corr=run_id)
            pat = self.mint_pat(principal, run_id, ix)
            if not pat:
                raise RunnerError("사용자 명의 PAT 발급 실패 — 서비스 계정으로 대신 돌지 않는다")
            try:
                await sess.open(pat)
                self.store.set_run_state(run_id, "running")
                v = await self._one(run_id, ix, step, scope, principal, sess)
                if v is None:
                    return {"ix": ix, "state": "skipped"}
                saved = {}
                if v.ok:
                    for key, path in (step.save or {}).items():
                        saved[key] = template.extract(v.parsed, path)
                    # 뽑은 값은 실행 입력에 합쳐 다음 단계가 {{key}} 로 쓸 수 있게 한다.
                    if saved:
                        self.store.merge_inputs(run_id, saved)
                self.store.set_run_state(run_id, "queued" if v.ok else "failed",
                                         stage=None if v.ok else f"step:{ix}",
                                         ended=not v.ok)
                return {"ix": ix, "ok": v.ok, "kind": v.kind, "saved": saved,
                        "error": None if v.ok else J.short_error(v)}
            finally:
                await sess.close(pat)

    async def catalog(self, principal, run_id: str = "catalog") -> dict:
        """도구 고르기 화면의 데이터 — 사용자 PAT `tools/list` 가 권한 필터의 정본이다."""
        sess = GatewaySession(self.gateway_url, self._client, corr=run_id)
        pat = self.mint_pat(principal, run_id, 0)
        if not pat:
            raise RunnerError("사용자 명의 PAT 발급 실패")
        try:
            await sess.open(pat)
            return await sess.list_tools(pat)
        finally:
            await sess.close(pat)

    async def second_stage(self, principal, spec, run_id: str = "describe") -> dict:
        """2단 도구의 **두 번째 단 계약**을 받아 온다(PLAN §9-4·§9-5).

        `run_operation(operation="matdb", args={…})` 의 `args` 는 게이트웨이 스키마상 속성
        없는 object 라 1단 검사를 그냥 통과한다. 그러면 오타가 실행 시점에야 터진다.
        여기서 `describe_operation("matdb")` 를 불러 진짜 계약을 가져온다.

        ⚠ **못 받아 오면 빈 칸으로 둔다.** 모르는 것을 틀렸다고 하지 않는다 —
        호출부(`check_against_schemas`)가 없는 항목은 검사하지 않는다.
        """
        reg = dispatch.load()
        want: list[tuple] = []
        for st in spec.steps:
            d = reg.get((st.backend, st.tool))
            if d is None:
                continue
            item = dispatch.selected(st.args, d)
            if item and (st.backend, st.tool, item) not in {w[0] for w in want}:
                want.append(((st.backend, st.tool, item), d, item))
        if not want:
            return {}

        sess = GatewaySession(self.gateway_url, self._client, corr=run_id)
        pat = self.mint_pat(principal, run_id, 0)
        if not pat:
            raise RunnerError("사용자 명의 PAT 발급 실패")
        out: dict = {}
        try:
            await sess.open(pat)
            for key, d, item in want:
                alias = f"{d.backend.replace('-', '')}_{d.describe}"
                try:
                    res = await sess.call("invoke_tool",
                                          {"name": alias, "arguments": {d.describe_arg: item}},
                                          pat, 30.0)
                except Exception:  # noqa: BLE001 — 계약을 못 받는 것이 저장을 막으면 안 된다
                    logger.info("2단 계약 조회 실패 — 검사 건너뜀 %s/%s", d.tool, item)
                    continue
                # ⚠ `call` 은 **튜플** `(isError, content[])` 다(94행). 객체인 줄 알고
                # `getattr(res,"content")` 로 읽던 동안 이 층 전체가 늘 None 을 냈고,
                # 그것을 "검사할 게 없다" 로 읽어 **2단 계약 검사가 통째로 안 돌았다**.
                is_error, content = res
                text, _ = J.join_content(content)
                body = J.judge(is_error=is_error, text=text).parsed
                sch = dispatch.to_json_schema(body, d, item=item)
                if sch:
                    out[key] = sch
        finally:
            await sess.close(pat)
        return out

    def _pick(self, run_id: str, ix: int, st: Step, v, scope: dict) -> dict | None:
        """룰이 고른 후보를 범위에 담는다. 멈춰야 하면 그 결과를 돌려준다(아니면 None).

        ⚠ **여럿에서 첫 번째를 조용히 집는 것이 가장 위험하다.** 엉뚱한 대상으로 절차
        전체가 돌고 결과는 정상으로 나온다. StepForge 가 이미 그 자세다 — "이름이 겹치면
        후보를 돌려주고 **고르지 않는다**"(D-170). 기본이 `ask` 인 이유다.
        """
        sel = st.select
        try:
            cand = template.extract(v.parsed, sel.from_)
        except Exception:  # noqa: BLE001 — 경로가 안 풀리면 후보 없음과 같다
            cand = None
        rows = cand if isinstance(cand, list) else ([] if cand is None else [cand])
        rows = [r for r in rows if isinstance(r, dict)]

        if not rows:
            if sel.on_none == "skip":
                self.store.finish_step(run_id, ix, ok=True, state="skipped",
                                       stage="select:none",
                                       notes={"select": "룰이 아무것도 못 골랐다 — 건너뛴다"})
                return None
            self.store.finish_step(run_id, ix, ok=False, stage="select:none",
                                   error=f"룰이 아무것도 못 골랐다 (`{sel.from_}` 가 비었다)")
            self.store.set_run_state(run_id, "failed", stage=f"step:{ix}", ended=True)
            return {"state": "failed", "stopped_at": ix, "kind": "select_none",
                    "error": "룰이 아무것도 못 골랐다"}

        if len(rows) > 1 and sel.on_many != "first":
            shown = [{"i": i, "label": str(r.get(sel.label or sel.save, ""))[:120],
                      "value": r.get(sel.save)} for i, r in enumerate(rows[:50])]
            if sel.on_many == "fail":
                self.store.finish_step(run_id, ix, ok=False, stage="select:many",
                                       error=f"룰이 {len(rows)}개를 골랐다 — 하나로 좁혀라",
                                       notes={"candidates": shown})
                self.store.set_run_state(run_id, "failed", stage=f"step:{ix}", ended=True)
                return {"state": "failed", "stopped_at": ix, "kind": "select_many",
                        "error": f"룰이 {len(rows)}개를 골랐다"}
            # ask — 사람이 고른다. 게이트와 같은 자리에서 멈춘다.
            self.store.finish_step(run_id, ix, ok=False, state="pending", stage="select:ask",
                                   error=None, notes={"candidates": shown, "pick_into": sel.var})
            self.store.set_run_state(run_id, "gated", stage=f"step:{ix}")
            return {"state": "gated", "stopped_at": ix, "kind": "select_ask",
                    "candidates": shown}

        scope[sel.var] = rows[0].get(sel.save)
        self.store.merge_inputs(run_id, {sel.var: scope[sel.var]})
        return None

    async def dispatcher_items(self, principal, d, run_id: str = "items") -> list[dict]:
        """2단 도구 뒤에 **무엇이 있나**. 목록 도구가 없으면 빈 목록이다(모른다).

        응답 모양이 앱마다 달라(JSON 목록·텍스트) 이름만 골라 낸다 — 지어내지 않는다.
        """
        if not d.list_tool:
            return []
        body = await self._call_one(principal, d.backend, d.list_tool, {}, run_id)
        return _names_of(body)

    async def second_stage_one(self, principal, d, item: str,
                               run_id: str = "describe") -> dict | None:
        """그 항목 **하나**의 계약. 못 받으면 None — 모르는 것을 틀렸다고 하지 않는다."""
        body = await self._call_one(principal, d.backend, d.describe,
                                    {d.describe_arg: item}, run_id)
        return dispatch.to_json_schema(body, d, item=item)

    async def _call_one(self, principal, backend: str, tool: str, args: dict,
                        run_id: str):
        """세션 하나 열고 한 번 부르고 닫는다 — 조회용 짧은 길."""
        sess = GatewaySession(self.gateway_url, self._client, corr=run_id)
        pat = self.mint_pat(principal, run_id, 0)
        if not pat:
            raise RunnerError("사용자 명의 PAT 발급 실패")
        try:
            await sess.open(pat)
            alias = f"{backend.replace('-', '')}_{tool}"
            res = await sess.call("invoke_tool", {"name": alias, "arguments": args},
                                  pat, 30.0)
            is_error, content = res   # 튜플이다 — 377행과 같은 이유
            text, _ = J.join_content(content)
            return J.judge(is_error=is_error, text=text).parsed
        finally:
            await sess.close(pat)

    async def _one(self, run_id, ix, st: Step, scope, principal, sess):
        """단계 하나 — 치환 → 호출 → 판정 → 기록. 판정이 실패면 `save` 를 하지 않는다."""
        args = template.substitute(st.args, scope)
        pat = self.mint_pat(principal, run_id, ix)
        timeout = WARMUP_TIMEOUT if st.warmup else EXPECT_TIMEOUT.get(st.expect, 30.0)

        if st.warmup:
            # 콜드스타트를 흡수하는 한 번 버리는 호출. 타임아웃이 나도 실패로 치지 않는다.
            try:
                await sess.call("invoke_tool", {"name": st.alias, "arguments": args},
                                pat, timeout)
            except Exception:  # noqa: BLE001
                logger.info("절차 워밍업 무응답 — 그대로 진행 tool=%s", st.tool)
            return None

        self.store.begin_step(run_id, ix, backend=st.backend, tool=st.tool, args=args,
                              schema_fp=st.schema_fp, expect=st.expect, mode="live")
        t0 = time.perf_counter()
        lock = self._blk(st.backend) if st.expect == "slow" else _NULL_LOCK
        try:
            async with lock:
                is_error, content = await sess.call(
                    "invoke_tool", {"name": st.alias, "arguments": args}, pat, timeout)
        except (httpx.TimeoutException, asyncio.TimeoutError):
            ms = int((time.perf_counter() - t0) * 1000)
            # 클라이언트가 먼저 포기했다 — 쓰기는 그 뒤 완료됐을 수 있다. failed 가 아니다.
            self.store.finish_step(run_id, ix, ok=False, state="unknown", stage="timeout",
                                   duration_ms=ms,
                                   error=f"{timeout:.0f}초 안에 응답이 없다 — 실행 여부를 "
                                         f"모른다. 쓰기 단계면 사람이 확인한 뒤 재실행한다")
            return J.Verdict(False, "mcp", "timeout", error="timeout", retriable=True)
        except Exception as exc:  # noqa: BLE001
            ms = int((time.perf_counter() - t0) * 1000)
            self.store.finish_step(run_id, ix, ok=False, state="unknown", stage="transport",
                                   duration_ms=ms, error=f"{type(exc).__name__}: {exc}")
            return J.Verdict(False, "mcp", "transport", error=str(exc), retriable=True)

        ms = int((time.perf_counter() - t0) * 1000)
        text, other = J.join_content(content)
        v = J.judge(is_error=is_error, text=text, raw=st.raw, unwrap=st.unwrap)

        # `save` 는 저장·절단 **전에** 원문에서 한다. 프리뷰만 남은 뒤엔 값이 없다.
        if v.ok and st.save:
            for key, path in st.save.items():
                try:
                    got = template.extract(v.parsed, path)
                except template.TemplateError as exc:
                    v = J.Verdict(False, "save", "save_missing", parsed=v.parsed,
                                  error=str(exc))
                    break
                if template.is_empty(got):
                    v = J.Verdict(False, "save", "save_empty", parsed=v.parsed,
                                  error=f"save {key}: '{path}' 가 빈 값이다 — 다음 단계에 "
                                        f"빈 값을 넘기지 않는다")
                    break

        notes = dict(v.notes or {})
        if other:
            notes["non_text_blocks"] = [b.get("type") for b in other if isinstance(b, dict)]
        notes["judge"] = v.as_row()
        self.store.finish_step(run_id, ix, ok=v.ok, result_text=text, duration_ms=ms,
                               notes=notes or None,
                               error=None if v.ok else J.short_error(v),
                               stage=None if v.ok else v.kind)
        return v


class _NullLock:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return False


_NULL_LOCK = _NullLock()


def _sha(args: dict) -> str:
    import hashlib

    blob = json.dumps(args, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _resolvable(st: Step, known: set) -> bool:
    for name in template.refs(st.args):
        root = name.split(".")[0]
        if root == "me" or name == "run_id":
            continue
        if name not in known:
            return False
    return True


def _names_of(body) -> list[dict]:
    """목록 응답에서 **이름과 한 줄 요약**만 골라 낸다.

    앱마다 모양이 다르다 — DynaForge 는 `{name, category, summary}` 의 연속,
    SmartTwinMCP 는 `{hits: [{name, summary}]}`. 모르는 모양이면 빈 목록이다.
    """
    rows = []
    if isinstance(body, dict):
        for key in ("operations", "items", "hits", "tools", "results"):
            if isinstance(body.get(key), list):
                rows = body[key]
                break
        else:
            rows = [body] if body.get("name") else []
    elif isinstance(body, list):
        rows = body
    out = []
    for r in rows:
        if not isinstance(r, dict) or not r.get("name"):
            continue
        out.append({"name": str(r["name"]),
                    "summary": str(r.get("summary") or r.get("description") or "")[:160],
                    **({"category": str(r["category"])} if r.get("category") else {})})
    return out[:200]
