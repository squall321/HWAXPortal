# 자동 파이프라인의 게이트웨이 호출 — 절차 실행기의 GatewaySession 으로 부르고, /tools-map 의 orig 로 (백엔드, 원래 이름) → 노출 이름을 찾는다
"""계약 도구는 앱 도구라 게이트웨이가 접두를 붙인다(허브 가족은 늘). 노출 이름을 짐작하지 않고 `/tools-map` 의 map(노출 이름 → 백엔드)과
orig(노출 이름 → 원래 이름, 다를 때만)로 찾는다(portal-api §2).

한 호출 = 세션 하나(열기 → tools/call → 닫기). 토큰을 호출마다 새로 찍기 때문이다(AP-8) — 한 세션에 다른 jti 를 섞지 않는다.
판정은 Reply 가 한다 — `isError: false` 인데 error 칸이 실린 답은 실패다(계약 §0.3). 결과를 모르는 실패(불통 · 기한)는 transient 다 — 제출이면
같은 idem_key 로 다음 박자에 다시 부른다.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import re
import time
from dataclasses import dataclass, field

import httpx

from app.procedures.runner import GatewaySession, RunnerError

logger = logging.getLogger(__name__)

CALL_TIMEOUT = 110.0      # 벽시계 기한 — 게이트웨이 호출 상한(600초)보다 짧게(절차 slow 단계와 같은 값). 넘으면 결과 모름(transient)
MAP_TTL_S = 30.0          # 한 박자 안에서 /tools-map 을 다시 읽지 않는다
# FastMCP 는 도구가 올린 예외 앞에 「Error executing tool <원래 이름>: 」 를 붙인다 — 그 뒤가 앱의 {error, detail} JSON 이다(StepForge 11-27 · AP-30).
# 이 머리를 떼지 않으면 app:not_ready(제출 → 막힘) · app:not_done(결과 → 다음 박자)이 tool_error(실패)로 떨어진다. CallToolResult 를 직접 내는 앱
# (DynaForge `_auto_out`)은 머리가 없다 — 둘 다 받는다.
_FASTMCP_HEAD = re.compile(r"Error executing tool [A-Za-z0-9_.\-]+\s*:\s*")


@dataclass
class Reply:
    ok: bool
    data: dict | None = None
    error: str = ""               # 낱말 — unreachable · refused · permission · app:<앱 낱말> · not_json · error_in_success · tool_missing · no_token
    detail: str = ""
    transient: bool = False       # 결과를 모른다 — 다음 박자에 다시 묻는다
    extra: dict = field(default_factory=dict)


def resolve_backend(name: str, tmap: dict) -> str | None:
    """규칙의 앱 이름 → 이 박스의 게이트웨이 백엔드 키. 글자 그대로 있으면 그것, 없으면 'heax-<이름>'(허브 앱 — 계약 문서의 예 step_forge 가
    이 박스에서 heax-step_forge 인 것처럼). 둘 다 없으면 None."""
    known = set((tmap.get("map") or {}).values()) | {a.get("app") for a in tmap.get("apps") or [] if isinstance(a, dict)}
    if name in known:
        return name
    alt = f"heax-{name}"
    return alt if alt in known else None


def exposed(backend: str, orig: str, tmap: dict) -> str | None:
    """(백엔드, 원래 이름) → 노출 이름. 원래 이름은 게이트웨이 orig 칸만 믿는다 — 접두를 떼어 짐작하지 않는다."""
    names = tmap.get("map") or {}
    origs = tmap.get("orig") or {}
    hits = sorted(n for n, bk in names.items() if bk == backend and origs.get(n, n) == orig)
    return hits[0] if hits else None


def reachable(backend: str, tmap: dict) -> bool | None:
    """apps[] 의 reachable — 모르면 None."""
    for a in tmap.get("apps") or []:
        if isinstance(a, dict) and a.get("app") == backend:
            r = a.get("reachable")
            return r if isinstance(r, bool) else None
    return None


def _text(content: list) -> str:
    return "\n".join(str(c.get("text") or "") for c in content if isinstance(c, dict) and c.get("type") == "text")


def judge(is_error: bool, content: list) -> Reply:
    """tools/call 의 (isError, content[]) → Reply. 실패 다섯 모양 가운데 셋이 isError=false 였다(절차 PLAN 5-6) — 칸으로 다시 본다."""
    text = _text(content).strip()
    if is_error:
        if text.startswith("게이트웨이 HTTP "):
            code = text.removeprefix("게이트웨이 HTTP ").split()[0]
            if code in ("401", "403"):
                return Reply(False, error="permission", detail=text[:300])
            return Reply(False, error="unreachable", detail=text[:300], transient=True)
        if text.startswith("JSON-RPC 오류"):
            return Reply(False, error="rpc_error", detail=text[:300], transient=True)
        head = _FASTMCP_HEAD.match(text)
        try:
            body = json.loads(text[head.end():] if head else text)
        except ValueError:
            body = None
        if isinstance(body, dict) and isinstance(body.get("error"), str) and body["error"]:
            return Reply(False, data=body, error=f"app:{body['error'][:60]}", detail=str(body.get("detail") or "")[:500])
        if "service-denied" in text or text.startswith("forbidden"):
            return Reply(False, error="permission", detail=text[:500])
        return Reply(False, error="tool_error", detail=text[:500])
    try:
        body = json.loads(text)
    except ValueError:
        return Reply(False, error="not_json", detail=text[:300])
    if not isinstance(body, dict):
        return Reply(False, error="not_json", detail="답이 JSON 객체가 아니다")
    if "error" in body:
        return Reply(False, data=body, error="error_in_success",
                     detail=f"isError=false 인데 error 칸이 있다 — {str(body.get('error'))[:120]}")
    return Reply(True, data=body)


class AutoGateway:
    """mint(run, step) -> 토큰 | None 를 주입받는다(시험은 keystore 없이)."""

    def __init__(self, gateway_url: str, client: httpx.AsyncClient, mint) -> None:
        self.url = (gateway_url or "http://127.0.0.1:9110").rstrip("/")
        self._c = client
        self._mint = mint
        self._map: dict | None = None
        self._map_at = 0.0

    async def tools_map(self, *, fresh: bool = False) -> dict | None:
        """/tools-map(무인증 — 박스 안에서만 닿는다). 못 읽으면 None — 그 박자의 게이트웨이 일을 하지 않는다."""
        if not fresh and self._map is not None and time.monotonic() - self._map_at < MAP_TTL_S:
            return self._map
        try:
            r = await self._c.get(f"{self.url}/tools-map", timeout=20.0)
            data = r.json() if r.status_code == 200 else None
        except (httpx.HTTPError, ValueError):
            data = None
        if not isinstance(data, dict) or not isinstance(data.get("map"), dict):
            return None
        self._map, self._map_at = data, time.monotonic()
        return data

    async def call(self, backend: str, orig: str, args: dict, *, run: str, step: str, corr: str) -> Reply:
        tmap = await self.tools_map()
        if tmap is None:
            return Reply(False, error="unreachable", detail="게이트웨이 /tools-map 을 읽지 못했다", transient=True)
        name = exposed(backend, orig, tmap)
        if name is None:
            live = reachable(backend, tmap)
            if live is False:
                return Reply(False, error="unreachable", detail=f"{backend} 이 지금 게이트웨이에 붙어 있지 않다", transient=True)
            return Reply(False, error="tool_missing",
                         detail=f"게이트웨이에 {backend}:{orig} 가 없다 — 앱이 계약 도구를 아직 갖추지 않았거나 SIF 가 낡았다")
        token = self._mint(run, step)
        if not token:
            return Reply(False, error="no_token", detail="서비스 토큰을 찍지 못했다", transient=True)
        sess = GatewaySession(self.url, self._c, corr=corr)
        try:
            await asyncio.wait_for(sess.open(token), timeout=30.0)
            is_err, content = await asyncio.wait_for(sess.call(name, args, token, CALL_TIMEOUT), timeout=CALL_TIMEOUT)
        except RunnerError as exc:
            msg = str(exc)
            if "(403)" in msg:
                return Reply(False, error="permission", detail="게이트웨이가 서비스 작업 auto-pipeline 을 받지 않았다(403 — "
                                                              "service_tools.local.json 의 jobs 에 없다)")
            return Reply(False, error="unreachable", detail=msg[:300], transient=True)
        except (httpx.HTTPError, TimeoutError, ValueError) as exc:
            return Reply(False, error="unreachable", detail=f"{type(exc).__name__}", transient=True)
        finally:
            with contextlib.suppress(Exception):          # 닫기 실패로 판정을 바꾸지 않는다
                await sess.close(token)
        out = judge(is_err, content)
        out.extra["tool"] = name
        return out
