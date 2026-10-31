"""실행기 — 절차를 한 단계씩 돌리고 실행에 남긴다. **챗과 자원을 공유하지 않는다.**

격리가 이 파일의 절반이다(PLAN §3). 자기 세마포어·자기 httpx 클라이언트·실행당 MCP 세션 하나.

게이트웨이 호출은 `agent/upload.py:mcp_call` 의 **방식만** 따르고 **베끼지 않는다**. 그 함수는
JSON-RPC `error` 만 보고 `result.isError` 를 버리며, `content[0]` 만 취하고, 파싱 실패를
`{"raw": …}` 로 정상 반환한다 — 셋 다 실패를 성공으로 만든다(context-notes W-16).

시간은 PLAN §5-10 이다. 게이트웨이 상한이 120초이던 때 실측이 이미 그 위에 있었다
(`search_catalog_property` 세션 첫 호출 120.3초). 넘기면 그 백엔드 영속 세션이 재연결되면서
같은 백엔드에 걸린 챗·심의 호출까지 끊긴다. 게이트웨이 상한은 이제 600초다(GATEWAY_CALL_TIMEOUT) —
아래 값들은 그 수와 **관계로** 묶여 있고 tests/test_procedures_census.py 가 게이트웨이 소스의 기본값과 대조한다.
"""

import asyncio
import json
import logging
import re
import time

import httpx

from app.procedures import dispatch
from app.procedures import judge as J
from app.procedures import template
from app.procedures.models import (MUST_GATE, PREVIEW_TOOL, PUBLISH_TOKEN, PUBLISH_TOOL, ProcedureSpec, Step,
                                   omit_empty_optionals, schema_fingerprint)
from app.procedures.store import ProceduresStore

logger = logging.getLogger(__name__)

# 실행기 클라이언트의 기본 한도 — 단계 호출은 아래 값을 요청마다 따로 주므로, 이 값은 세션 열기·닫기 같은 나머지 호출에 걸린다.
# 게이트웨이 상한이 120초이던 때 '게이트웨이보다 늦게 포기한다(재연결 재시도 한 번까지)' 로 잡은 값이다 — 먼저 포기하면
# 쓰기는 그 뒤 완료되고 실행에는 unknown 만 남는다. 상한이 600초가 된 지금은 죽은 게이트웨이를 잡는 침묵 한도로 남긴다
# (httpx 한도는 바이트 사이 간격이고 게이트웨이는 응답에 15초마다 ping 을 싣는다).
CLIENT_TIMEOUT = 260.0
# 단계 자체의 상한. 게이트웨이 상한(600초)보다 짧게 둬 우리가 먼저 끊고 기록을 남긴다.
# ⚠ **벽시계 기한**이다(`_one` 이 wait_for 로 건다). httpx 에 넘기는 같은 값은 바이트 사이 간격이라, 15초마다 ping 을 싣는
#   살아 있는 게이트웨이 앞에서는 한 번도 안 걸린다 — 그것만 있던 동안 '빠름 30초' 단계가 게이트웨이 상한(600초)까지 기다렸고,
#   게이트웨이가 끊은 쓰기는 `unknown` 이 아니라 `failed/tool_error` 로 남아 재개가 확인 없이 다시 보냈다.
EXPECT_TIMEOUT = {"fast": 30.0, "slow": 110.0, "job": 110.0}
# 워밍업은 게이트웨이가 스스로 포기할 때까지 기다린다 — 콜드스타트를 한 번 버리는 호출이라 먼저 끊으면 흡수를 못 한다.
# 게이트웨이 호출 상한 600초 + 단발 세션 바깥 기한 60초 = 660초, 거기에 30초 여유. 게이트웨이 상한이 120초이던 때는 125초였다.
# ⚠ GATEWAY_CALL_TIMEOUT 기본값을 다시 올리면 이 값도 같은 폭으로 올린다(시험이 묻는다).
WARMUP_TIMEOUT = 690.0
# 빈 실행 하나가 가질 수 있는 단계 수. 저장된 절차의 `procedures_max_steps`(30)보다
# 넉넉하다 — 여기는 사람이 탐색하며 붙이는 자리라 30 은 좁다. 다만 천장은 있어야 한다.
STEP_MAX = 120
# `save` 로 뽑은 값을 실행 `inputs` 에 남길 때의 한 값 상한. 넘으면 안 남기고 말한다 —
# `inputs_json` 은 통째로 다시 쓰는 한 덩이라 큰 값이 들어가면 단계 수의 제곱으로 자란다.
SAVE_PERSIST_MAX = 256 * 1024


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
        # ⚠ 조회용(카탈로그·2단 계약·목록)은 **따로 센다.** 실행 세마포어에 묶으면 저장
        # 화면이 긴 실행 뒤에 줄을 서고, 안 묶으면 `GET /tools` 를 반복하는 것만으로
        # 게이트웨이에 세션이 무제한 쌓인다 — 챗·심의가 그 게이트웨이를 같이 쓴다.
        self.lookup_sem = asyncio.Semaphore(4)
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
        # 비운 선택 변수 — 통째 자리면 그 칸을 빼고 나간다(W-102). 실행마다 다시 채우므로 재개 · 게이트 지문이 같다.
        omit_empty_optionals(spec, scope)
        # ⚠ **덮어쓴다, 양보하지 않는다.** `setdefault` 면 `inputs` 에 먼저 들어간 값이
        # 이긴다 — 신원은 부르는 사람에게서 나와야 하고 입력이 정할 것이 아니다.
        scope["run_id"] = run_id
        scope["me.email"] = getattr(principal, "email", "") or ""
        scope["me.sub"] = getattr(principal, "subject", "") or ""

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
                # 자리 · 세션을 기다리는 사이 누른 중단을 다시 본다 — `queued` 인 실행을 중단해도 아래가 running(또는 드리프트 failed)을 써
                # 중단이 지워지고 단계가 돌았다. 재개 계열(ack · pick · resume)도 이 길을 탄다. failed 는 보지 않는다 — 실패한 단계부터
                # 재개하는 실행은 failed 에서 출발한다.
                run = self.store.get_run(run_id)
                if run is None or run["state"] == "cancelled":
                    return {"state": run["state"] if run else "unknown", "stopped_at": start_at}
                drift = self._check_drift(spec, catalog)
                if drift:
                    # ⚠ 이유를 stage 에 실어 원장에 남긴다. 예전엔 `schema_drift` 한 낱말뿐이라
                    # 화면에서 **어느 단계의 어떤 도구가 없는지** 알 길이 없었다(cae00 점검).
                    self.store.set_run_state(run_id, "failed",
                                             stage=f"schema_drift: {' / '.join(drift)}"[:400],
                                             ended=True)
                    return {"state": "failed", "stage": "schema_drift", "detail": drift}
                self.store.set_run_state(run_id, "running")
                # 설명에만 있는 경고(합성 데이터 모델)는 실행 기록에 남긴다 — 결과에는 안 실린다(W-7 ③).
                caveats = {ix: c for ix, st in enumerate(spec.steps)
                           if (c := J.description_caveat(_meta(catalog, st).get("description")))}
                return await self._loop(run_id, spec, scope, principal, sess, start_at, caveats)
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
            tpl = _without_token(st, st.args)   # 실제로 나갈 것을 보인다 — 게시 토큰은 실행기가 넣는다
            try:
                args = template.substitute(tpl, scope) if _resolvable(tpl, known) else tpl
                pending = not _resolvable(tpl, known)
            except template.TemplateError:
                args, pending = tpl, True
            calls.append({"ix": ix, "backend": st.backend, "tool": st.tool,
                          "alias": st.alias, "gate": _gate_of(st), "expect": st.expect,
                          "args": args, "unverified": pending})
            if pending:
                unknown.append(st.tool)
            known |= set((st.save or {}).keys())
            # ⚠ **원장에 적는다.** 여태 이 목록을 계산해 놓고 반환만 했는데, 부르는 쪽은
            # 전부 `_spawn(...)` 이라 반환값을 버린다. 그래서 `run["steps"]` 가 비고,
            # 화면은 "무엇을 어떤 인자로 부를지 보여 준다" 고 해 놓고 **빈 페이지**를 띄웠다.
            # 사람은 그걸 "이 절차는 단계가 없다" 로 읽는다. 실행과 섞이지 않게 `mode="plan"`
            # 이고, 상태는 `skipped` 다 — **안 불렀다**는 뜻이지 성공이 아니다.
            self.store.begin_step(run_id, ix, backend=st.backend, tool=st.tool, args=args,
                                  schema_fp=st.schema_fp, expect=st.expect, mode="plan")
            self.store.finish_step(
                run_id, ix, ok=True, state="skipped",
                stage="plan:unverified" if pending else "plan",
                notes={"plan": {"alias": st.alias, "gate": _gate_of(st),
                                "unverified": pending}})
        self.store.set_run_state(run_id, "done", stage="plan", ended=True)
        return {"state": "done", "stage": "plan", "calls": calls, "unverified": unknown}

    def _check_drift(self, spec: ProcedureSpec, catalog: dict) -> list[str]:
        """도구에 판본이 없으니 **변화를 잡아 멈추는 것까지** 한다(PLAN §5-8)."""
        out = []
        for i, st in enumerate(spec.steps, 1):
            # ⚠ 맨이름으로 물러서는 것의 **정확한 뜻**(2026-09-15 실측). 게이트웨이는 한 앱만
            # 가진 도구를 맨이름으로, **겹치면 전부 앱 접두로** 낸다 — 겹칠 때 맨이름은
            # 아예 사라진다(`whoami`·`list_reports` 확인). 그래서 "맨이름이 있다" 는
            # **그 도구가 이 게이트웨이에 딱 하나 있다** 는 뜻이지, **우리 앱 것**이라는 뜻은
            # 아니다. backend 를 잘못 적었으면 남의 앱 계약으로 검사하게 된다. 그 경우는
            # `schema_fp` 가 안 맞아 드리프트로 멈추고(아래), 없으면 실행이 `unknown tool` 로
            # 터진다 — 조용히 틀리지는 않는다. 지도 없이 여기서 더 가릴 방법은 없다.
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

    async def _loop(self, run_id, spec, scope, principal, sess, start_at, caveats=None) -> dict:
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

            # 인자 치환은 **여기서 한 번**이다. 게이트가 따로 치환하면 승인한 지문과
            # 실제로 나가는 인자가 다른 것을 셀 수 있다 — 같은 값을 아래로 내린다.
            args, bad = self._args(run_id, ix, st, scope)
            if bad is not None:
                self.store.set_run_state(run_id, "failed", stage=f"step:{ix}", ended=True)
                return {"state": "failed", "stopped_at": ix, "kind": bad.kind,
                        "error": J.short_error(bad)}

            pub = None

            # 게이트 — 승인이 없으면 여기서 멈춘다. 인자 지문에 묶인 1회용 승인이다.
            # ⚠ `_gate_of` — 저장된 판본의 `gate` 만 보면 **MUST_GATE 가 나중에 늘었을 때** 옛 판본이
            # 확인 없이 지나간다(`publish_report_to_datahub` 는 09-15 에야 들었다). 판본은 불변이라
            # 저장 검증을 다시 안 탄다. 게이트웨이가 절차 호출에 파괴 도구 차단을 면제하는 근거가
            # "포털이 사람 확인을 받았다" 이므로(W-100) 그 전제를 **여기서** 참으로 만든다.
            if st.tool == PUBLISH_TOOL:   # MUST_GATE 라 늘 사람 자리다 — 게이트 앞뒤로 미리보기를 받는 따로 길
                pub = await self._publish_gate(run_id, ix, st, args, principal, sess)
                if "state" in pub:   # 게이트 · 실패 — 게시는 나가지 않았다
                    return pub
            elif _gate_of(st) == "human":
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

            v = await self._one(run_id, ix, st, scope, principal, sess, args=args,
                                caveat=(caveats or {}).get(ix),
                                secret={PUBLISH_TOKEN: pub["token"]} if pub else None,
                                fingerprint=pub["fp"] if pub else None)
            if pub and v is not None:
                # 무엇을 보고 승인해 어디에 올렸나 — 게이트 카드의 미리보기를 게시 기록에도 남긴다(토큰은 없다)
                self.store.annotate_step(run_id, ix, {"publish_preview": pub["view"]})
            # 호출을 기다리는 사이 누른 중단을 다시 본다 — 중단은 단계 경계(위)에서만 봤고 그 뒤 호출을 기다렸다. 안 보면 아래 쓰기가 덮는다
            # — 마지막 단계면 done, 실패면 failed, 고르기면 확인 대기(gated). 미리보기를 기다린 뒤 다시 보는 `_publish_gate` 와 같은 자리다.
            # 호출의 기록은 `_one` 이 이미 남겼다(이미 나갔다).
            run = self.store.get_run(run_id)
            if run is None or run["state"] in ("cancelled", "failed"):
                return {"state": run["state"] if run else "unknown", "stopped_at": ix}
            if v is None:  # warmup — 결과를 버린다
                continue
            if not v.ok:
                self.store.set_run_state(run_id, "failed", stage=f"step:{ix}", ended=True)
                return {"state": "failed", "stopped_at": ix, "kind": v.kind,
                        "error": J.short_error(v)}
            for key, path in (st.save or {}).items():
                scope[key] = template.extract(v.parsed, path)
            if st.save:
                # ⚠ **원장에도 남긴다.** scope 는 이 호출 안에서만 산다. 게이트에서 멈췄다
                # 재개하면 `run()` 이 scope 를 `inputs` 에서 다시 만드는데, 거기 없으면
                # 그 값을 쓰는 단계가 `TemplateError` 로 죽고 — 그 예외가 `_loop` 밖이라
                # 실행은 `running` 인 채 영원히 남았다. '앞에서 뽑아 두고 되돌리기 어려운
                # 단계를 게이트로 막는다' 는 **가장 흔한 모양**이 재개가 안 됐다.
                #
                # ⚠ 다만 **상한이 있다.** `inputs_json` 은 통째로 읽고-합치고-다시 쓰는
                # 한 덩이라, 큰 값을 넣으면 단계마다 그만큼을 다시 쓴다(실측: 2.5MB 짜리
                # save 10단계 = 25MB · 2.7초, 전부 이벤트 루프 위다). 결과 본문은 이미
                # gzip 으로 따로 있으니 원장이 그것을 또 품을 이유가 없다. 넘치는 값은
                # **안 넣고 그 사실을 단계에 적는다** — 조용히 넣는 것보다 낫다.
                # ⚠ 루프 변수를 `v` 로 두면 **바로 위의 판정(Verdict)을 덮는다** — 아래
                # `select` 가 `v.parsed` 를 읽으므로 `AttributeError` 가 나고, `_pick` 의
                # 넓은 except 가 그걸 "후보 없음" 으로 바꾼다. 후보가 있는데 "룰이 아무것도
                # 못 골랐다" 가 되고, `on_none: skip` 이면 **전부 초록인 채로** 뒤 단계가
                # 헛돈다. 실제로 그렇게 냈다(2026-09-15 3차 감사).
                keep, oversize = {}, []
                for k in st.save:
                    got = scope[k]
                    # ⚠ **바이트로 센다.** 글자 수로 세면 한국어가 3배 아래에서 통과해
                    # 상한이 막으려던 병이 그대로 난다(실측: 25만 자 = 75만 바이트).
                    n = len(json.dumps(got, ensure_ascii=False,
                                       default=str).encode("utf-8"))
                    (oversize.append((k, n)) if n > SAVE_PERSIST_MAX
                     else keep.__setitem__(k, got))
                if keep:
                    self.store.merge_inputs(run_id, keep)
                if oversize:
                    logger.info("save 값이 커서 원장에 안 남겼다 run=%s ix=%s %s",
                                run_id, ix, oversize)
                    self.store.annotate_step(run_id, ix, {
                        "save_not_persisted": [k for k, _ in oversize],
                        "why": f"뽑은 값이 {SAVE_PERSIST_MAX // 1024}KB 를 넘어 원장에 안 남겼다"
                               f"({', '.join(f'{k} {n // 1024}KB' for k, n in oversize)}) — "
                               "이 실행을 **재개하면** 그 값을 다시 만들지 못한다. "
                               "결과 자체는 이 단계에 그대로 있다"})

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
        # ⚠ **여기는 게이트가 없다.** `gate: human` 을 달고 오면 검증은 통과하는데 실행은 확인 없이
        # 바로 나갔다(2026-09-18 재현 — `trash_report` 가 게이트웨이까지 도달). 선언된 사람 자리가
        # 조용히 무시되는 것이고, 게이트웨이 면제의 전제도 거짓이 된다. 라우트가 먼저 거르지만
        # 다른 호출부가 생겨도 뚫리지 않게 여기서도 막는다.
        if _gate_of(step) == "human":
            raise RunnerError("사람 확인이 필요한 단계는 즉석으로 돌리지 않는다 — 절차로 저장해 실행하라")
        run = self.store.get_run(run_id)
        if run is None:
            raise RunnerError(f"실행이 없다: {run_id}")
        ix = len(run["steps"])
        if any(s["state"] == "running" for s in run["steps"]):
            raise RunnerError("이미 도는 단계가 있다")
        # ⚠ **상한이 없었다.** 저장된 절차는 `procedures_max_steps` 로 막히는데 빈 실행에
        # 한 단계씩 붙이는 이 길에는 아무 천장도 없었다. 초안 만들기가 단계 수의 제곱으로
        # 자라므로(실측 120단계 10.8초) 길게 키운 실행 하나로 포털을 세울 수 있다.
        if ix >= STEP_MAX:
            raise RunnerError(f"한 실행의 단계 상한({STEP_MAX})을 넘었다 — "
                              f"절차로 저장하고 새 실행에서 이어가라")

        scope = dict(scope or run.get("inputs") or {})
        # ⚠ **덮어쓴다, 양보하지 않는다.** `setdefault` 면 `inputs` 에 먼저 들어간 값이
        # 이긴다 — 신원은 부르는 사람에게서 나와야 하고 입력이 정할 것이 아니다.
        scope["run_id"] = run_id
        scope["me.email"] = getattr(principal, "email", "") or ""
        scope["me.sub"] = getattr(principal, "subject", "") or ""

        async with self.sem:
            sess = GatewaySession(self.gateway_url, self._client, corr=run_id)
            pat = self.mint_pat(principal, run_id, ix)
            if not pat:
                raise RunnerError("사용자 명의 PAT 발급 실패 — 서비스 계정으로 대신 돌지 않는다")
            try:
                await sess.open(pat)
                # 실행 경로와 같은 경고(합성 데이터 모델) — 이 길이 절차 기능의 진입점이다(독스트링). 빠지면 한 단계씩 돌린 기록에 없다.
                caveat = J.description_caveat(_meta(await sess.list_tools(pat), step).get("description"))
                # 세션을 여는 사이 누른 중단 — 아래 running 이 지운다(실행 `run` 과 같은 자리). failed 는 보지 않는다 — 빈 실행은
                # 실패한 단계 뒤에도 단계를 더 받는다(add_step 이 막는 것은 cancelled · gated 다).
                if (self.store.get_run(run_id) or {}).get("state") == "cancelled":
                    return {"ix": ix, "state": "cancelled"}
                self.store.set_run_state(run_id, "running")
                args, bad = self._args(run_id, ix, step, scope)
                if bad is not None:
                    self.store.set_run_state(run_id, "failed", stage=f"step:{ix}", ended=True)
                    return {"ix": ix, "ok": False, "kind": bad.kind, "saved": {},
                            "error": J.short_error(bad)}
                v = await self._one(run_id, ix, step, scope, principal, sess, args=args,
                                    caveat=caveat)
                if v is None:
                    return {"ix": ix, "state": "skipped"}
                # 호출을 기다리는 사이 누른 중단 — 아래 queued 가 지워 실행이 단계를 다시 받았다(화면은 단계가 도는 동안 '중단' 을 보인다).
                if (self.store.get_run(run_id) or {}).get("state") == "cancelled":
                    return {"ix": ix, "state": "cancelled"}
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
        async with self.lookup_sem:
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
        async with self.lookup_sem:
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
        missing = False
        try:
            cand = template.extract(v.parsed, sel.from_)
        except Exception:  # noqa: BLE001 — 경로가 안 풀리면 후보 없음과 같다
            cand, missing = None, True
        raw_rows = cand if isinstance(cand, list) else ([] if cand is None else [cand])
        rows = [r for r in raw_rows if isinstance(r, dict)]
        if raw_rows and not rows:
            # ⚠ **"없다" 가 아니다.** `parts: ["BRKT_1","BRKT_2"]` 처럼 이름 목록으로 오면
            # 여기서 전부 걸러진다. 그걸 "비었다" 로 말하면 사람은 질의를 고치러 간다 —
            # 고칠 곳은 `select` 쪽이다.
            kinds = sorted({type(r).__name__ for r in raw_rows})
            self.store.finish_step(
                run_id, ix, ok=False, stage="select:shape",
                error=f"`{sel.from_}` 에 {len(raw_rows)}개가 있는데 객체가 아니다"
                      f"({'·'.join(kinds)}) — `save: {sel.save}` 로 꺼낼 칸이 없다")
            self.store.set_run_state(run_id, "failed", stage=f"step:{ix}", ended=True)
            return {"state": "failed", "stopped_at": ix, "kind": "select_shape",
                    "error": f"`{sel.from_}` 가 객체 목록이 아니다"}
        if rows and not any(sel.save in r for r in rows):
            # 칸 이름이 틀린 것도 "비었다" 와 다르다. 이걸 안 가르면 후보가 전부
            # `value: null` 로 뜨고, 사람이 그중 하나를 고르면 None 이 다음 단계로 간다.
            # ⚠ **목록을 봉투로 싸 주는 도구**(KooRemapper `find_reports` 의
            # `{items, total, reason, truncated}`)를 `from: "$"` 로 읽으면 봉투 하나가 후보가
            # 되어 여기서 멈춘다 — 0건이어도 `on_none` 이 아니라 이 오류다(HP-52). 고칠 곳은
            # 절차의 `from` 이라 그렇게 말한다. 몰래 벗기지는 않는다 — `$` 의 뜻이 바뀌면
            # 이미 저장된 판본의 뜻이 바뀐다(PLAN §2). 옛 씨앗을 가져온 사람은 다시 받기 전까지
            # 이 글을 본다.
            # ⚠ 다시 받아도 **이 실행**은 옛 판본에 묶여 있다 — '다시 돌리기' · '재개' 는 실행의
            # 판본 id 로 돈다(PLAN §2). 받으라고만 하면 받은 사람이 이 실행으로 돌아와 다시 돌리고
            # 같은 글을 또 본다(반대 검토). 그래서 절차 화면에서 새로 재생하라고까지 말한다.
            env = (sel.from_.strip() == "$" and isinstance(cand, dict)
                   and isinstance(cand.get("items"), list))
            hint = (f" · 결과가 목록이 아니라 봉투다(`items` 에 후보 {len(cand['items'])}개) — "
                    "`from: items` 로 고친다. 정본 예제에서 가져온 절차는 '최신으로' 로 "
                    "다시 받으면 고친 판본이 오른다. 고친 판본은 절차 화면에서 새로 '재생' 해야 "
                    "돈다 — 이 실행의 '이 값으로 다시 돌리기' · '재개' 는 그때 판본으로 다시 돈다"
                    if env else "")
            self.store.finish_step(
                run_id, ix, ok=False, stage="select:no_field",
                error=f"고른 {len(rows)}개 어디에도 `{sel.save}` 칸이 없다 — "
                      f"있는 칸: {sorted(rows[0])[:12]}{hint}")
            self.store.set_run_state(run_id, "failed", stage=f"step:{ix}", ended=True)
            return {"state": "failed", "stopped_at": ix, "kind": "select_no_field",
                    "error": f"`{sel.save}` 칸이 없다"
                             + (" — 봉투다(`from: items` 로 고른다)" if env else "")}

        if not rows:
            if sel.on_none == "skip":
                self.store.finish_step(run_id, ix, ok=True, state="skipped",
                                       stage="select:none",
                                       notes={"select": "룰이 아무것도 못 골랐다 — 건너뛴다"})
                return None
            # ⚠ 경로가 **안 풀린 것**을 "비었다" 로 말하지 않는다. 멈추는 길(on_none)은 같지만,
            # 결과 꼴이 바뀐 것(봉투 이전의 맨 목록 · 칸 이름 변경)이 0건과 같은 글이면 사람은
            # '아직 없다' 로 읽는다 — 씨앗이 `from: items` 에 기대게 된 뒤의 HP-52 거울상이다.
            p = v.parsed
            seen = (f"있는 칸: {sorted(p)[:12]}" if isinstance(p, dict)
                    else f"결과가 목록이다({len(p)}개)" if isinstance(p, list)
                    else "결과가 객체가 아니다")
            why = (f"`{sel.from_}` 가 결과에 없다 — 0건이 아니라 결과 꼴이 다르다 · {seen}"
                   if missing else f"`{sel.from_}` 가 비었다")
            self.store.finish_step(run_id, ix, ok=False, stage="select:none",
                                   error=f"룰이 아무것도 못 골랐다 ({why})")
            self.store.set_run_state(run_id, "failed", stage=f"step:{ix}", ended=True)
            return {"state": "failed", "stopped_at": ix, "kind": "select_none",
                    "error": "룰이 아무것도 못 골랐다"}

        if sel.multi:
            # 여럿이 답인 자리 — 사람이 **골라서 한 단계에 넘긴다**(태그 적용 등). 하나뿐이면
            # 묻지 않는다(on_many 규율과 같다 — 여럿일 때만 사람에게 간다).
            values, empty = [], []
            for r in rows:
                val = r.get(sel.save)
                (empty if template.is_empty(val) else values).append(val)
            if empty:
                self.store.finish_step(run_id, ix, ok=False, stage="select:empty",
                                       error=f"후보 {len(empty)}개의 `{sel.save}` 가 빈 값이다 — "
                                             f"빈 값을 다음 단계에 넘기지 않는다")
                self.store.set_run_state(run_id, "failed", stage=f"step:{ix}", ended=True)
                return {"state": "failed", "stopped_at": ix, "kind": "select_empty",
                        "error": f"`{sel.save}` 가 빈 값인 후보가 있다"}
            if len(values) == 1:
                scope[sel.var] = values
                self.store.merge_inputs(run_id, {sel.var: values})
                return None
            # 사람이 훑는 목록이라 50개만 보여 준다 — 총수를 같이 싣는다. 없으면 51번째부터는 있는 줄도 모른 채 못 고른다.
            shown = [{"i": i, "label": str(r.get(sel.label or sel.save, ""))[:120],
                      "value": r.get(sel.save)} for i, r in enumerate(rows[:50])]
            self.store.finish_step(run_id, ix, ok=False, state="pending", stage="select:ask_many",
                                   error=None,
                                   notes={"candidates": shown, "candidates_total": len(rows),
                                          "pick_into": sel.var, "pick_multi": True})
            self.store.set_run_state(run_id, "gated", stage=f"step:{ix}")
            return {"state": "gated", "stopped_at": ix, "kind": "select_ask_many",
                    "candidates": shown, "candidates_total": len(rows)}

        if len(rows) > 1 and sel.on_many != "first":
            # 보여 주는 것은 50개까지 — 총수를 같이 싣는다(위 ask_many 와 같다).
            shown = [{"i": i, "label": str(r.get(sel.label or sel.save, ""))[:120],
                      "value": r.get(sel.save)} for i, r in enumerate(rows[:50])]
            if sel.on_many == "fail":
                self.store.finish_step(run_id, ix, ok=False, stage="select:many",
                                       error=f"룰이 {len(rows)}개를 골랐다 — 하나로 좁혀라",
                                       notes={"candidates": shown, "candidates_total": len(rows)})
                self.store.set_run_state(run_id, "failed", stage=f"step:{ix}", ended=True)
                return {"state": "failed", "stopped_at": ix, "kind": "select_many",
                        "error": f"룰이 {len(rows)}개를 골랐다"}
            # ask — 사람이 고른다. 게이트와 같은 자리에서 멈춘다.
            self.store.finish_step(run_id, ix, ok=False, state="pending", stage="select:ask",
                                   error=None, notes={"candidates": shown, "candidates_total": len(rows),
                                                      "pick_into": sel.var})
            self.store.set_run_state(run_id, "gated", stage=f"step:{ix}")
            return {"state": "gated", "stopped_at": ix, "kind": "select_ask",
                    "candidates": shown, "candidates_total": len(rows)}

        got = rows[0].get(sel.save)
        if template.is_empty(got):
            # `save` 경로는 40줄 위에서 이미 이러고 있다(PLAN §5-6). 여기만 안 보고
            # 있었다 — `find_parts(name=null)` 은 대개 **필터 없음**으로 읽혀 전부가
            # 돌아오고, 실행은 `done` 이 되고, 보고서는 엉뚱한 집합 위에서 나온다.
            self.store.finish_step(run_id, ix, ok=False, stage="select:empty",
                                   error=f"고른 것의 `{sel.save}` 가 빈 값이다 — "
                                         f"다음 단계에 빈 값을 넘기지 않는다")
            self.store.set_run_state(run_id, "failed", stage=f"step:{ix}", ended=True)
            return {"state": "failed", "stopped_at": ix, "kind": "select_empty",
                    "error": f"`{sel.save}` 가 빈 값이다"}
        scope[sel.var] = got
        self.store.merge_inputs(run_id, {sel.var: got})
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
        async with self.lookup_sem:
            try:
                await sess.open(pat)
                alias = f"{backend.replace('-', '')}_{tool}"
                res = await sess.call("invoke_tool", {"name": alias, "arguments": args},
                                      pat, 30.0)
                is_error, content = res   # 튜플이다 — 위 second_stage 와 같은 이유
                text, _ = J.join_content(content)
                return J.judge(is_error=is_error, text=text).parsed
            finally:
                await sess.close(pat)

    def _args(self, run_id, ix, st: Step, scope) -> tuple[dict | None, "J.Verdict | None"]:
        """인자 치환 — 못 풀면 **그 단계에서** 끝낸다. 예외를 밖으로 내보내지 않는다.

        ⚠ 내보내면 `_loop` 도 `step_once` 도 그걸 안 잡아 실행이 **`running` 인 채 영원히**
        남는다(2026-09-17 재현: 앞 단계가 `select on_none: skip` 으로 건너뛰면 뒤 단계가
        쓸 변수가 없다). 화면에는 도는 것처럼 보이고, 끝나지 않으니 재개도 취소도 아니다 —
        runner.py:309 가 적어 둔 그 사고의 **다른 입구**다.

        게시 확인 토큰 칸은 **치환 전에** 뗀다(`_without_token`) — 옛 판본이 그 칸에 적은 변수는 이제 입력이 아니어서
        (`coerce_inputs`) 범위에 없다. 치환 뒤에 떼면 없는 변수로 이 단계가 멈춘다.
        """
        tpl = _without_token(st, st.args)
        try:
            return template.substitute(tpl, scope), None
        except template.TemplateError as exc:
            self.store.begin_step(run_id, ix, backend=st.backend, tool=st.tool, args=tpl,
                                  schema_fp=st.schema_fp, expect=st.expect, mode="live")
            # 비운 선택 변수(W-102)는 앞 단계 탓이 아니다 — 저장 검증이 save · select 이름과 변수가 겹치는 것을 막는다
            why = ("선택 변수를 채워 다시 돌리거나, 절차에서 그 변수를 객체의 칸 하나에 통째로(\"{{변수}}\") 두면 비웠을 때 그 칸이 빠진다"
                   if isinstance(exc, template.OmitError) else "앞 단계가 그 값을 안 냈다(건너뛰었거나 뽑지 못했다)")
            self.store.finish_step(run_id, ix, ok=False, stage="args", error=f"{exc} — {why}")
            return None, J.Verdict(False, "args", "args_missing", error=str(exc))

    async def _publish_gate(self, run_id, ix, st: Step, args: dict, principal, sess) -> dict:
        """게시(RA `publish_report`)의 2단 확인 — PLAN §5-4 · 남은 일 B3.

        승인 전에는 `preview_publish` 의 대상 · 볼 사람 수 · 못 올리는 사유를 게이트 카드(단계 노트)에 놓고 멈춘다.
        승인 뒤에는 미리보기를 **다시** 받아 사람이 본 것과 같을 때만 그때 받은 토큰을 돌려준다 — 호출부가 곧바로
        게시한다(두 호출 사이에 사람 대기가 없어 토큰 수명 600초에 안 걸린다). 다르면 차이를 카드에 싣고 다시 멈춘다.

        승인 지문은 치환된 인자와 **토큰을 뺀 미리보기**의 sha256 이다. 그래서 미리보기가 바뀌면 같은 인자라도 승인이
        무효가 되고, 미리보기마다 새로 나오는 토큰은 지문을 바꾸지 않는다. 토큰은 원장(단계 인자 · 노트 · 결과 · 실행
        입력) 어디에도 넣지 않는다 — 돌려준 값은 이 실행의 이 호출 안에서만 산다.

        돌려주는 것 — 멈출 때는 `_loop` 가 그대로 돌려줄 결과(`state` 가 있다), 갈 때는 `{fp, token, view}`.
        """
        got = await self._preview(run_id, ix, st, args, principal, sess)
        # 미리보기를 기다리는 사이 사람이 '중단' 을 눌렀으면 여기서 멈춘다 — 중단은 단계 경계(`_loop`)에서 봤고 그 뒤 네트워크를
        # 기다렸다. 다시 안 보면 승인 뒤에는 되돌릴 수 없는 게시가 나가고, 승인 전에는 게이트 카드가 중단을 '확인 대기' 로 덮는다.
        run = self.store.get_run(run_id)
        if run is None or run["state"] in ("cancelled", "failed"):
            return {"state": run["state"] if run else "unknown", "stopped_at": ix}
        ack = self.store.gate_ack(run_id, ix)
        seen = self._approved_view(run_id, ix, ack)
        if isinstance(got, J.Verdict):
            # 사람에게 보일 대상이 없다 — 게이트를 세울 것이 없으니 그 단계에서 멈춘다(재개하면 미리보기부터 다시 받는다).
            # 승인이 있으면 그 지문과 승인한 미리보기를 이 행에 그대로 둔다 — 행을 새로 쓰며 지우면 재개한 카드가 '승인한 뒤
            # 바뀐 것' 을 못 보이고 처음 보는 카드처럼 뜬다.
            why = J.short_error(got)
            self.store.begin_step(run_id, ix, backend=st.backend, tool=st.tool, args=args,
                                  schema_fp=st.schema_fp, expect=st.expect, mode="live",
                                  fingerprint=ack["args_sha256"] if seen is not None else None)
            self.store.finish_step(run_id, ix, ok=False, stage="preview",
                                   error=f"게시 미리보기({PREVIEW_TOOL})를 못 받았다 — {why}",
                                   notes={"publish_preview": seen} if seen is not None else None)
            self.store.set_run_state(run_id, "failed", stage=f"step:{ix}", ended=True)
            return {"state": "failed", "stopped_at": ix, "kind": got.kind, "error": why}
        view, token = got
        fp = _sha({"args": args, "publish_preview": view})
        blocked = _publish_blockers(view, token)
        if ack is not None and ack["args_sha256"] == fp:
            if not blocked:
                return {"fp": fp, "token": token, "view": view}
            # 사람이 승인했지만 이대로는 RA 가 게시 전체를 거절한다(막힌 게시판이 하나라도 있으면 커밋 없이 오류 —
            # ReportArchive mounts/services.py mount_report). 알면서 부르지 않는다.
            why = "게시하지 않았다 — " + " · ".join(blocked)
            self.store.begin_step(run_id, ix, backend=st.backend, tool=st.tool, args=args,
                                  schema_fp=st.schema_fp, expect=st.expect, mode="live", fingerprint=fp)
            self.store.finish_step(run_id, ix, ok=False, stage="publish:blocked", error=why,
                                   notes={"publish_preview": view, "publish_blocked": blocked})
            self.store.set_run_state(run_id, "failed", stage=f"step:{ix}", ended=True)
            return {"state": "failed", "stopped_at": ix, "kind": "publish_blocked", "error": why}
        # 승인한 뒤 바뀌었으면 그 차이를 싣는다
        notes: dict = {"publish_preview": view}
        if blocked:
            notes["publish_blocked"] = blocked
        if seen is not None:
            notes["publish_changed"] = _preview_changes(seen, view)
        self.store.begin_step(run_id, ix, backend=st.backend, tool=st.tool, args=args,
                              schema_fp=st.schema_fp, expect=st.expect, mode="live", fingerprint=fp)
        self.store.finish_step(run_id, ix, ok=False, state="pending", error=None, stage="gate", notes=notes)
        self.store.set_run_state(run_id, "gated", stage=f"step:{ix}")
        out = {"state": "gated", "stopped_at": ix, "args_sha256": fp}
        if "publish_changed" in notes:
            out["changed"] = notes["publish_changed"]
        return out

    def _approved_view(self, run_id, ix, ack) -> dict | None:
        """사람이 승인한 미리보기 — 승인 지문이 지금 행의 것과 같을 때만 그 행의 미리보기가 '사람이 본 것' 이다."""
        if ack is None:
            return None
        row = next((s for s in self.store.list_steps(run_id) if s["ix"] == ix), None)
        if row is None or row["args_sha256"] != ack["args_sha256"]:
            return None
        pv = (row.get("notes") or {}).get("publish_preview")
        return pv if isinstance(pv, dict) else None

    async def _preview(self, run_id, ix, st: Step, args: dict, principal, sess):
        """`preview_publish` 한 번 — `(토큰을 뺀 미리보기, 토큰)` 또는 실패 판정. 결과 원문은 남기지 않는다(토큰이 들어 있다)."""
        alias = f"{st.backend.replace('-', '')}_{PREVIEW_TOOL}"   # 게시 단계와 같은 앱 — `Step.alias` 와 같은 식
        timeout = EXPECT_TIMEOUT.get(st.expect, 30.0)
        # 미리보기의 인자는 둘이다(RA mcp_server `preview_publish`) — note · folder_ids 는 게시에만 간다
        pargs = {k: args[k] for k in ("report_id", "boards") if k in args}
        try:
            is_error, content = await asyncio.wait_for(sess.call(
                "invoke_tool", {"name": alias, "arguments": pargs},
                self.mint_pat(principal, run_id, ix), timeout), timeout)
        except (httpx.TimeoutException, asyncio.TimeoutError):
            return J.Verdict(False, "mcp", "timeout", error=f"{timeout:.0f}초 안에 응답이 없다", retriable=True)
        except Exception as exc:  # noqa: BLE001
            return J.Verdict(False, "mcp", "transport", error=f"{type(exc).__name__}: {exc}", retriable=True)
        v = J.judge(is_error=is_error, text=J.join_content(content)[0])
        if not v.ok:
            return v
        p = v.parsed
        if not isinstance(p, dict) or not isinstance(p.get("targets"), list):
            # 대상을 못 읽으면 사람에게 보일 것이 없다 — 꼴이 바뀐 것을 '대상 없음' 으로 읽지 않는다
            seen = sorted(p)[:12] if isinstance(p, dict) else type(p).__name__
            return J.Verdict(False, "envelope", "preview_shape",
                             error=f"미리보기에 대상 목록(targets)이 없다 — 응답 꼴이 바뀌었다(있는 칸: {seen})")
        view = {"report_id": p.get("report_id"), "title": p.get("title"),
                "targets": [{k: t[k] for k in _TARGET_KEYS if k in t}
                            for t in p["targets"] if isinstance(t, dict)]}
        if p.get("warnings"):
            view["warnings"] = p["warnings"]
        tok = p.get(PUBLISH_TOKEN)
        return view, (tok if isinstance(tok, str) and tok else None)

    async def _one(self, run_id, ix, st: Step, scope, principal, sess, *, args: dict,
                   caveat: str | None = None, secret: dict | None = None,
                   fingerprint: str | None = None):
        """단계 하나 — 호출 → 판정 → 기록. 판정이 실패면 `save` 를 하지 않는다.

        인자는 이미 치환된 것을 받는다(`_args`) — 게이트가 승인한 지문 그대로 나간다.
        `secret` 은 **보내기만 하고 남기지 않는** 인자다(게시 확인 토큰 — `_publish_gate`). 원장의 인자 ·
        결과 · 오류 어디에도 안 들어가고, 그 단계의 승인 지문은 `fingerprint` 다.
        """
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
                              schema_fp=st.schema_fp, expect=st.expect, mode="live",
                              fingerprint=fingerprint)
        t0 = time.perf_counter()
        lock = self._blk(st.backend) if st.expect == "slow" else _NULL_LOCK
        try:
            async with lock:
                # 기한은 잠금 **안**에서 센다 — 잠금을 기다린 시간은 이 단계의 몫이 아니고, 기한이 차면 잠금도 같이 놓는다.
                is_error, content = await asyncio.wait_for(sess.call(
                    "invoke_tool", {"name": st.alias, "arguments": {**args, **(secret or {})}}, pat, timeout),
                    timeout)
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
                                   duration_ms=ms, error=_redact(f"{type(exc).__name__}: {exc}", secret))
            return J.Verdict(False, "mcp", "transport", error=_redact(str(exc), secret), retriable=True)

        ms = int((time.perf_counter() - t0) * 1000)
        text, other = J.join_content(content)
        # 보내기만 한 값이 응답에 되비쳐 오면 가린다 — pydantic 의 '칸 없음' 오류는 받은 인자를 통째로 싣는다
        text = _redact(text, secret)
        if st.tool == PREVIEW_TOOL:
            # 게시 미리보기를 단계로 둔 절차(챗 기록을 편 초안) · 한 단계씩 돌린 미리보기 — 결과 원문에 600초짜리 확인 토큰이
            # 있다. 판정 · save · 원장에 넣기 전에 가린다. 게시 단계는 이 토큰을 쓰지 않는다(`_publish_gate` 가 따로 받는다).
            text = _mask_publish_token(text)
        v = J.judge(is_error=is_error, text=text, raw=st.raw, unwrap=st.unwrap, ok_text=st.ok_text)

        # 값 단언 — **save 보다 먼저** 본다. 엉뚱한 대상의 응답에서 값을 뽑아 다음 단계로
        # 넘기면, 그 뒤 판독은 전부 성공하고 보고서만 다른 해석 위에서 나온다.
        if v.ok and st.asserts:
            for chk in st.asserts:
                try:
                    got = template.extract(v.parsed, chk.path)
                except template.TemplateError as exc:
                    v = J.Verdict(False, "assert", "assert_missing", parsed=v.parsed, error=str(exc))
                    break
                why = chk.check(got)
                if why:
                    v = J.Verdict(False, "assert", "assert_failed", parsed=v.parsed, error=why)
                    break

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
        if caveat:
            # 화면(단계 · 배치 표)이 읽는 `warnings` 에 **덧붙인다** — 결과가 준 경고는 그대로 둔다.
            w = notes.get("warnings")
            notes["warnings"] = [*(w if isinstance(w, list) else [w] if w else []), caveat]
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


def _without_token(st: Step, args):
    """게시 단계의 확인 토큰 칸을 뗀다 — 실행기가 승인 뒤 미리보기에서 받아 넣는다(`_publish_gate`).

    옛 판본은 이 칸을 변수로 적어야만 저장됐다(저장 대조가 스키마의 필수 칸으로 요구했다). 그대로 두면 그 값이 단계
    인자 · 승인 지문에 남고 카드는 나가지 않을 값을 보인다. 저장 검증은 이제 그 판본을 거절하지만 판본은 불변이다.
    그 변수는 입력도 아니다(`models.publish_token_vars` — 실행 입력에 안 남는다). 그래서 **치환 전에** 뗀다.
    """
    if st.tool == PUBLISH_TOOL and isinstance(args, dict) and PUBLISH_TOKEN in args:
        return {k: v for k, v in args.items() if k != PUBLISH_TOKEN}
    return args


def _redact(text: str, secret: dict | None) -> str:
    """보내기만 한 값(`_one` 의 secret)을 글에서 가린다 — 원장에 남기지 않는다."""
    for k, v in (secret or {}).items():
        if isinstance(v, str) and v:
            text = text.replace(v, f"[가림:{k}]")
    return text


# 결과 글의 확인 토큰 칸 `"confirm_token": "<값>"` — 결과가 JSON 글 안에 한 겹 더(문자열로) 싸여 와도 잡는다(따옴표 앞 역빗금).
_TOKEN_FIELD = re.compile(r'(\\*"' + PUBLISH_TOKEN + r'\\*"\s*:\s*\\*")([^"\\]+)')


def _mask_publish_token(text: str) -> str:
    """미리보기 결과의 확인 토큰 값을 가린다 — 나머지(대상 · 볼 사람 수)는 그대로 남는다. 토큰이 없으면(null) 그대로다."""
    return _TOKEN_FIELD.sub(lambda m: f"{m.group(1)}[가림:{PUBLISH_TOKEN}]", text)


# 게시 미리보기에서 카드에 싣고 승인 지문에 넣는 칸 — RA `mounts/routes.py` preview_mount 의 대상 칸 그대로다.
# 토큰과 안내문(note)은 넣지 않는다.
_TARGET_KEYS = ("slug", "name", "parent_slug", "audience", "descendant_boards", "already_mounted",
                "blocked", "error")
_TARGET_LABEL = {"name": "이름", "parent_slug": "상위 게시판", "audience": "볼 수 있는 사람",
                 "descendant_boards": "하위 게시판", "already_mounted": "이미 게시됨", "blocked": "못 올리는 사유",
                 "error": "오류"}


def _publish_blockers(view: dict, token: str | None) -> list[str]:
    """이대로는 게시되지 않는 까닭. 막힌 게시판이 하나라도 있으면 RA 는 게시 전체를 거절한다 — 이미 게시된 곳은 건너뛴다."""
    out = [f"{t.get('slug')}: {t.get('blocked') or t.get('error')}" for t in view["targets"]
           if (t.get("blocked") or t.get("error")) and not t.get("already_mounted")]
    if not token and not out:
        out.append("확인 토큰이 없다 — 미리보기가 올릴 수 있는 대상을 못 찾았다")
    return out


def _preview_changes(before: dict, after: dict) -> list[str]:
    """사람이 승인한 미리보기와 지금 것의 차이 — 게이트 카드에 그대로 싣는 줄들."""
    out = []
    for k, lab in (("report_id", "보고서"), ("title", "제목")):
        if before.get(k) != after.get(k):
            out.append(f"{lab}: {_show(before.get(k))} → {_show(after.get(k))}")
    b = {t.get("slug"): t for t in before.get("targets") or [] if isinstance(t, dict)}
    a = {t.get("slug"): t for t in after.get("targets") or [] if isinstance(t, dict)}
    out += [f"{s}: 대상에서 빠졌다" for s in b if s not in a]
    out += [f"{s}: 새 대상" for s in a if s not in b]
    for s in (x for x in a if x in b):
        for k, lab in _TARGET_LABEL.items():
            if b[s].get(k) != a[s].get(k):
                out.append(f"{s} {lab}: {_show(b[s].get(k))} → {_show(a[s].get(k))}")
    if before.get("warnings") != after.get("warnings"):
        out.append("경고가 바뀌었다")
    # 보이는 칸이 같은데 지문이 다르면 인자가 바뀐 것이다 — '같다' 로 보이게 두지 않는다
    return out or ["미리보기나 인자가 바뀌었다"]


def _show(v) -> str:
    if v is None:
        return "없음"
    if isinstance(v, bool):
        return "예" if v else "아니오"
    return str(v)


def _meta(catalog: dict, st: Step) -> dict:
    """카탈로그에서 이 단계의 도구 — 노출 이름(alias) 먼저, 맨이름은 그다음(`_check_drift` 의 주석). 없으면 빈 dict."""
    return catalog.get(st.alias) or catalog.get(st.tool) or {}


def _gate_of(st: Step) -> str | None:
    """이 단계가 **실제로** 멈출 자리인가. 선언(`gate`)이 없어도 되돌리기 어려운 도구는 멈춘다."""
    return "human" if (st.gate == "human" or st.tool in MUST_GATE) else st.gate


def _resolvable(args, known: set) -> bool:
    for name in template.refs(args):
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
    # 끊지 않는다 — 이름과 한 줄 요약뿐이라 가볍고, 종전 200개 컷은 201번째부터 '없는 항목' 으로 보이게 했다.
    return out
