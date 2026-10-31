# 포털 챗의 MCP Apps 패널 호스트 백엔드 — 패널 세션 표 · 패널 PAT · 게이트웨이 MCP 세션 · 허용 도구 · 첫 쓰기 확인 · 크기 상한 · 감사(docs/request-1027 HP-42)
"""설계 docs/request-1027/design-ha09-ha20.md B5.4 · 사용자 결정 10-31(B-1 ~ B-7 전부 (가)).

창구 다섯 — 모두 세션 쿠키 + CSRF 로만 받는다. Bearer PAT 는 받지 않는다(패널은 브라우저 탭에서만 산다 — B-4 (가)). 박스 손잡이
MCP_APPS_HOST 가 꺼져 있으면 다섯 다 404 이고 — 인증 · CSRF 보다 먼저 본다(라우터 의존성 _knob) — 권한은 feat:panels 다(B-1 (가)).

  POST /agent/panel/open    {uri, tool, call?}             리소스를 읽어 패널 세션을 연다 → {panel_id, html, csp, prefers_border, …}
  POST /agent/panel/call    {panel_id, name, arguments}    패널의 tools/call — 허용 도구 · 크기 · 누적 · 첫 쓰기 확인 → CallToolResult 그대로
  POST /agent/panel/read    {panel_id, uri}                패널의 resources/read — 같은 앱의 ui:// 만(게이트웨이가 다시 막는다) · 동시 · 읽은 양 상한
  POST /agent/panel/confirm {panel_id, token}              첫 쓰기 확인(B-2 (가) — 패널 세션마다 한 번)
  POST /agent/panel/close   {panel_id}                     패널 세션과 게이트웨이 MCP 세션을 닫는다

게이트웨이로는 패널 PAT(그 앱 하나 · 그 주소 · 15분 — panel_pat.py)로만 간다. 챗 PAT 를 쓰지 않는다 — 감사가 chat 으로 남고 포털 결함이 곧 챗 권한
전부가 된다(B4). 게이트웨이도 같은 범위를 다시 막는다(이중 막이).

패널 세션 표는 이 프로세스의 메모리다(포털은 프로세스 하나로 뜬다 — infra/apptainer/portal.def). 재기동하면 열린 패널은 사라지고 화면이 '다시 열기'
카드를 보인다. 서버 대화 사본에는 패널의 포인터(app · tool · uri · call · 제목)만 남는다(routes.pump — pointer_of).

SimFlow 가정 — SimFlow 의 답(설계 C1 Q-S1 ~ Q-S9)이 오기 전이다. 이 파일이 기대는 그쪽 모양은 `ASSUME_*` 이름이 붙은 것뿐이다(답이 오면 그것만
본다). 크기 상한의 기본값(설정 panel_*)도 Q-S6 · Q-S7 의 답 전 값이다.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import secrets
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.access.policy import login_groups
from app.agent import panel_pat
from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.config import Settings, get_settings
from app.deps import ensure, get_current_principal, require_csrf

logger = logging.getLogger(__name__)


def _knob(settings: Settings = Depends(get_settings)) -> None:
    """박스 손잡이 MCP_APPS_HOST 가 꺼져 있으면 없는 창구와 같은 404 다. 라우터 의존성이라 인증 · CSRF 의존성보다 먼저 돈다 — 꺼진 박스에서는
    익명 · CSRF 없는 세션 · Bearer PAT 도 401 · 403 이 아니라 같은 404 를 받는다(반대 검토 10-31). 본문이 JSON 이 아니면 FastAPI 가 그보다 먼저
    422 를 낸다(본문 해석이 의존성보다 앞이다)."""
    if not settings.mcp_apps_host:
        raise HTTPException(status_code=404, detail="Not Found")


router = APIRouter(prefix="/agent/panel", tags=["agent-panel"], dependencies=[Depends(_knob)])

FEATURE = "feat:panels"
UI_HOST_TOKEN = "mcp-apps/1"        # 화면이 호스트 부품을 가졌다는 표지 — 에이전트 서버 ui_panels.HOST_TOKEN 과 같은 글자(두 리포 시험)

# ── SimFlow 가정(Q-S1 ~ Q-S9 의 답 전) ───────────────────────────────────────────────────────────────────────────
# ASSUME_MIME — 패널 HTML 의 mimeType(MCP Apps 판의 text/html;profile=mcp-app 과 그냥 text/html). 다른 꼴이면 열지 않는다(Q-S7).
ASSUME_MIME = ("text/html", "text/html;profile=mcp-app")
# ASSUME_WRITE_IS_UNKNOWN — 쓰기 판정. 게이트웨이가 읽기로 확인한 도구(/tools-map 의 panel_read — 앱 표지 readOnlyHint · 박스 읽기 목록 − deny)가
# 아니면 쓰기로 본다. 이름 규칙은 울타리로 쓰지 않는다 — routine_read(루틴 단계 판정)는 이름의 조회 낱말로도 열어 보지 않는다. 모르면 확인을
# 묻는다(Q-S2 의 답이 오면 그 앱의 되돌릴 수 없는 도구 목록과 맞대 본다).
ASSUME_WRITE_IS_UNKNOWN = True
# ASSUME_CSP_FIELDS — 리소스 _meta.ui.csp 의 칸(Q-S3). 그 밖의 칸(frameDomains · baseUriDomains)은 1단계에서 받지 않는다(frame-src · base-uri 'none').
ASSUME_CSP_FIELDS = ("connectDomains", "resourceDomains")

# 패널이 부르지 못하는 도구 — 게이트웨이 _panel_denial 과 같은 묶음의 포털 쪽 거울(게이트웨이 자체 도구 · 되돌리기 어려운 정확 이름 · 외부 응답자
# 과제). 게이트웨이 패널 PAT 의 tools/list 가 이미 뺀 목록이지만 포털이 먼저 한 번 더 뺀다(이중 막이).
_DENY_EXACT = frozenset({
    "invoke_tool", "rest_call", "rest_catalog", "search_tools", "list_tool_apps", "save_conversation", "search_conversations",
    "browse_experts", "use_experts", "verify_answer", "routine_list", "routine_get", "routine_run_start", "routine_call",
    "routine_step_done", "routine_report_submit", "review_task_next", "review_task_read", "review_task_submit",
    "publish_report", "publish_report_to_datahub", "request_unpublish", "trash_report", "restore_version", "job_stop",
    "risk_add_finding", "add_report_tags",
})
_CORR_HEADER = "X-HWAX-Corr"        # 게이트웨이 감사의 corr 칸 — 포털 감사와 같은 호출 id 로 잇는다
_MCP_PROTOCOL = "2025-06-18"        # structuredContent 가 있는 판
_DOMAIN_RE = re.compile(r"^https?://(\*\.)?[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*(:\d{1,5})?$")
_MAX_PANELS_PER_USER = 8            # 사람 한 명이 동시에 쥘 수 있는 패널 세션 — 넘으면 가장 오래된 것을 닫는다(화면은 탭에 둘까지만 연다)
_MAX_PANELS = 256                   # 프로세스 전체 — 넘으면 503
_INFLIGHT_PER_PANEL = 4             # 패널 하나가 동시에 보내는 호출 — 끝없는 루프 패널이 게이트웨이를 두드리지 않게
_RESULT_MAX_BYTES = 16 * 1024 * 1024  # 게이트웨이 리소스 상한과 같은 바깥 경계 — 넘는 답은 화면으로 옮기지 않는다

# 시험이 바꿔 끼우는 자리 — 게이트웨이로 가는 클라이언트(httpx.MockTransport 를 단다).
_client_factory = lambda timeout: httpx.AsyncClient(timeout=timeout)  # noqa: E731


# ── 게이트웨이 도구 지도(/tools-map) — 도구 → 앱 · 패널 확인용 읽기(panel_read) · 앱 라벨. 60초 붙잡고 못 읽으면 마지막으로 읽은 지도(HP-32 와 같다) ──
_GW_MAP: dict = {"at": float("-inf"), "map": None, "read": None, "labels": {}}
_GW_MAP_TTL_S = 60.0


async def gw_map(settings: Settings) -> dict:
    now = time.monotonic()
    if now - _GW_MAP["at"] < _GW_MAP_TTL_S and _GW_MAP["map"] is not None:
        return _GW_MAP
    base = (settings.mcp_gateway_url or "").rstrip("/")
    try:
        async with _client_factory(5.0) as c:
            r = await c.get(base + "/tools-map")
        body = r.json() if r.status_code < 400 else {}
        m = body.get("map")
        if isinstance(m, dict) and m:
            rr = body.get("panel_read")          # routine_read 가 아니다 — 그것은 이름 낱말로도 연다(울타리가 아니다). 없으면 모른다(다 묻는다)
            _GW_MAP.update(at=now, map={str(k): str(v) for k, v in m.items()},
                           read=frozenset(x for x in rr if isinstance(x, str)) if isinstance(rr, list) else None,
                           labels={str(a.get("app")): str(a.get("label") or a.get("app")) for a in body.get("apps") or []
                                   if isinstance(a, dict) and a.get("app")})
            return _GW_MAP
    except (httpx.HTTPError, ValueError, AttributeError):
        pass
    _GW_MAP["at"] = now - _GW_MAP_TTL_S + 5.0      # 못 읽었다 — 5초 뒤 다시 묻는다. 마지막 지도는 그대로 쓴다
    return _GW_MAP


def label_of(app: str) -> str:
    """앱 라벨 — 붙잡아 둔 지도에서만 읽는다(스트림 안에서 부른다 — 게이트웨이에 묻지 않는다)."""
    return (_GW_MAP.get("labels") or {}).get(app) or app


def pointer_of(data: dict) -> dict | None:
    """SSE ui_resource 한 건 → 서버 사본에 남길 포인터 {app, tool, uri, call, title}. 결과 본문 · 입력 · _meta 는 남기지 않는다(B-4 · B-6 (가)).
    주소가 ui:// 가 아니면 버린다."""
    uri = data.get("uri") if isinstance(data, dict) else None
    tool = data.get("tool") if isinstance(data, dict) else None
    if not (isinstance(uri, str) and uri.startswith("ui://") and len(uri) <= 2048 and isinstance(tool, str) and tool):
        return None
    app = str(data.get("app") or "")[:120]
    return {"app": app, "tool": tool[:200], "uri": uri, "call": str(data.get("call") or "")[:80], "title": label_of(app)[:200]}


# ── 게이트웨이 MCP 세션(패널 하나에 하나) ────────────────────────────────────────────────────────────────────────

class PanelUpstreamError(Exception):
    """게이트웨이 · 앱 쪽 실패 — 화면에는 code 와 사람이 읽을 글만 간다."""

    def __init__(self, code: str, message: str, *, rpc: dict | None = None) -> None:
        super().__init__(message)
        self.code, self.message, self.rpc = code, message, rpc


class _Conn:
    """패널 하나의 게이트웨이 MCP 세션 — 패널 PAT 로 붙는다. 남은 수명이 2분 아래면 PAT 를 다시 찍고, 유휴 panel_mcp_idle_s 면 닫는다(다음
    호출이 다시 연다 — 조각 업로드가 호출마다 핸드셰이크를 하지 않게 열어 둔다). 게이트웨이 SDK 는 세션 유휴 만료가 없어 닫는 일은 이쪽 몫이다."""

    def __init__(self, gateway_url: str, mint, timeout: float) -> None:
        self.url = gateway_url.rstrip("/") + "/mcp"
        self._mint = mint                 # () -> (토큰, exp epoch 초)
        self._timeout = timeout
        self._tok, self._exp = "", 0.0
        self._sid = ""
        self._client: httpx.AsyncClient | None = None
        self._lock = asyncio.Lock()
        self._seq = 0
        self.last = time.monotonic()

    def _headers(self, corr: str = "") -> dict:
        h = {"Authorization": f"Bearer {self._tok}", "Content-Type": "application/json",
             "Accept": "application/json, text/event-stream", "MCP-Protocol-Version": _MCP_PROTOCOL}
        if self._sid:
            h["mcp-session-id"] = self._sid
        if corr:
            h[_CORR_HEADER] = corr
        return h

    @staticmethod
    def _message(r: httpx.Response, want_id: int | None) -> dict:
        """응답 하나에서 그 요청의 JSON-RPC 답 — SSE 면 data 줄 가운데 id 가 맞는 것, 아니면 JSON 본문."""
        text = r.text
        if "text/event-stream" in (r.headers.get("content-type") or ""):
            msgs = []
            for ln in text.splitlines():
                if ln.startswith("data:"):
                    try:
                        msgs.append(json.loads(ln[5:].strip()))
                    except ValueError:
                        continue
            hit = [m for m in msgs if isinstance(m, dict) and m.get("id") == want_id]
            if not hit:
                raise PanelUpstreamError("bad_response", "게이트웨이 답에서 이 요청의 결과를 찾지 못했다")
            return hit[-1]
        try:
            body = json.loads(text) if text else {}
        except ValueError:
            raise PanelUpstreamError("bad_response", f"게이트웨이 답이 JSON 이 아니다(HTTP {r.status_code})") from None
        return body if isinstance(body, dict) else {}

    async def _ensure(self) -> None:
        async with self._lock:
            if time.time() > self._exp - 120:
                self._tok, self._exp = self._mint()
            if self._client is None:
                self._client = _client_factory(self._timeout)
            if self._sid:
                return
            r = await self._client.post(self.url, headers=self._headers(), json={
                "jsonrpc": "2.0", "id": 0, "method": "initialize",
                "params": {"protocolVersion": _MCP_PROTOCOL, "capabilities": {},
                           "clientInfo": {"name": "hwax-portal-panel", "version": "1"}}})
            if r.status_code == 401:
                raise PanelUpstreamError("gateway_auth", "게이트웨이가 패널 토큰을 받지 않았다(게이트웨이가 패널 PAT 를 모르는 판일 수 있다)")
            if r.status_code != 200:
                raise PanelUpstreamError("gateway_unavailable", f"게이트웨이 초기화 실패(HTTP {r.status_code})")
            self._sid = r.headers.get("mcp-session-id", "")
            await self._client.post(self.url, headers=self._headers(), json={"jsonrpc": "2.0", "method": "notifications/initialized"})

    async def request(self, method: str, params: dict, corr: str = "") -> dict:
        """JSON-RPC 요청 하나 → result. 세션을 잃었으면(게이트웨이 재기동 — 404) 한 번만 다시 열고 보낸다(그 호출은 실행되지 않았다)."""
        for attempt in (0, 1):
            await self._ensure()
            self._seq += 1
            rid = self._seq
            self.last = time.monotonic()
            try:
                r = await self._client.post(self.url, headers=self._headers(corr), json={
                    "jsonrpc": "2.0", "id": rid, "method": method, "params": params})
            except httpx.HTTPError as exc:
                raise PanelUpstreamError("gateway_unavailable", f"게이트웨이에 닿지 못했다({type(exc).__name__})") from None
            if r.status_code == 404 and attempt == 0 and self._sid:
                self._sid = ""
                continue
            if r.status_code == 401:
                raise PanelUpstreamError("gateway_auth", "게이트웨이가 패널 토큰을 받지 않았다")
            if r.status_code != 200:
                raise PanelUpstreamError("gateway_unavailable", f"게이트웨이 답이 HTTP {r.status_code} 다")
            if len(r.content) > _RESULT_MAX_BYTES:
                raise PanelUpstreamError("result_too_large", f"답이 {len(r.content):,}바이트라 화면으로 옮기지 않는다")
            msg = self._message(r, rid)
            if isinstance(msg.get("error"), dict):
                e = msg["error"]
                raise PanelUpstreamError("rpc_error", str(e.get("message") or "오류")[:500],
                                         rpc={"code": e.get("code"), "message": str(e.get("message") or "")[:500]})
            res = msg.get("result")
            return res if isinstance(res, dict) else {}
        raise PanelUpstreamError("gateway_unavailable", "게이트웨이 세션을 다시 열지 못했다")

    async def close(self) -> None:
        async with self._lock:
            if self._client is not None:
                if self._sid:
                    try:
                        await self._client.request("DELETE", self.url, headers=self._headers())
                    except httpx.HTTPError:
                        logger.info("패널 MCP 세션 닫기 실패 sid=%s", self._sid[:12])
                await self._client.aclose()
            self._client, self._sid = None, ""


# ── 패널 세션 표 ────────────────────────────────────────────────────────────────────────────────────────────────

@dataclass
class _Panel:
    id: str
    owner: str                      # principal.subject — 남의 panel_id 는 없는 것과 같다
    email: str
    app: str
    uri: str
    tool: str
    call: str
    allowed: frozenset
    conn: _Conn
    created: float = field(default_factory=time.monotonic)
    last: float = field(default_factory=time.monotonic)
    write_ok: bool = False          # 첫 쓰기 확인을 받았나(B-2 (가) — 세션마다 한 번)
    pending: dict = field(default_factory=dict)   # 기다리는 확인 {토큰: 도구} — 한꺼번에 온 쓰기 여럿이 확인 하나로 풀리게(최근 8개)
    used: int = 0                   # 보낸 인자 바이트 누적(PANEL_SESSION_MAX_MB)
    read_bytes: int = 0             # 읽기(resources/read)로 받은 바이트 누적 — 보낸 몫과 따로 같은 상한(PANEL_SESSION_MAX_MB)
    calls: int = 0
    sem: asyncio.Semaphore = field(default_factory=lambda: asyncio.Semaphore(_INFLIGHT_PER_PANEL))


_TABLE: dict[str, _Panel] = {}
_SWEEPER: dict = {"task": None}


def _expired(p: _Panel, settings: Settings, now: float) -> bool:
    return now - p.last > settings.panel_idle_s or now - p.created > settings.panel_max_s


async def _drop(pid: str) -> None:
    p = _TABLE.pop(pid, None)
    if p is not None:
        await p.conn.close()


async def _sweep(settings: Settings) -> None:
    """끝난 패널 세션을 닫고, 유휴 MCP 세션은 닫아 둔다(패널은 남는다 — 다음 호출이 다시 연다)."""
    now = time.monotonic()
    for pid, p in list(_TABLE.items()):
        if _expired(p, settings, now):
            await _drop(pid)
        elif now - p.conn.last > settings.panel_mcp_idle_s:
            await p.conn.close()


async def _sweep_loop(settings: Settings) -> None:
    """표가 빌 때까지 60초마다 쓴다 — 탭을 닫아 close 가 오지 않은 패널의 게이트웨이 세션이 남지 않게."""
    try:
        while _TABLE:
            await asyncio.sleep(60)
            await _sweep(settings)
    finally:
        _SWEEPER["task"] = None


def _start_sweeper(settings: Settings) -> None:
    t = _SWEEPER.get("task")
    if t is None or t.done():
        _SWEEPER["task"] = asyncio.get_running_loop().create_task(_sweep_loop(settings))


async def close_all() -> None:
    """내려갈 때 — 열린 게이트웨이 세션을 닫는다."""
    for pid in list(_TABLE):
        await _drop(pid)
    t = _SWEEPER.get("task")
    if t is not None:
        t.cancel()


def _own(pid: str, principal: Principal, settings: Settings) -> _Panel:
    """그 사람의 살아 있는 패널 — 없거나 남의 것이거나 끝났으면 같은 404 다(있다는 사실을 흘리지 않는다)."""
    p = _TABLE.get(pid or "")
    if p is None or p.owner != principal.subject:
        raise AuthError("panel not found", status_code=404, code="panel_not_found")
    if _expired(p, settings, time.monotonic()):
        asyncio.get_running_loop().create_task(_drop(pid))
        raise AuthError("패널 세션이 끝났다 — 다시 연다", status_code=404, code="panel_not_found")
    p.last = time.monotonic()
    return p


def _mint_for(request: Request, settings: Settings, principal: Principal, app: str, uri: str):
    keystore = request.app.state.keystore

    def mint() -> tuple[str, float]:
        now = int(time.time())
        claims = panel_pat.panel_claims(iss=settings.jwt_issuer, sub=principal.subject, email=principal.email,
                                        name=principal.display_name, groups=login_groups(principal.groups), app=app, uri=uri,
                                        now=now, audience=settings.panel_pat_audience)
        tok = jwt.encode(claims, keystore.private_pem, algorithm="RS256", headers={"kid": keystore.active_kid})
        return tok, float(claims["exp"])
    return mint


def _domains(csp: Any, allowed: set[str]) -> dict:
    """리소스가 청한 출처 ∩ 박스 허용 출처 — 꼴(scheme://host[:port], 앞 *. 허용)이 아니면 버린다. 칸은 ASSUME_CSP_FIELDS 만."""
    out: dict = {}
    for k in ASSUME_CSP_FIELDS:
        vals = csp.get(k) if isinstance(csp, dict) else None
        got = []
        for v in vals if isinstance(vals, list) else []:
            if isinstance(v, str) and _DOMAIN_RE.match(v.strip()) and v.strip().lower() in allowed:
                got.append(v.strip().lower())
        out[k] = sorted(set(got))[:32]
    return out


def _box_origins(raw: str) -> set[str]:
    return {x.strip().lower().rstrip("/") for x in (raw or "").split(",") if _DOMAIN_RE.match(x.strip().rstrip("/"))}


def _open_origins(request: Request, settings: Settings, principal: Principal, app: str) -> list[str]:
    """ui/open-link 로 열 수 있는 출처 — 박스 허용(PANEL_LINK_ORIGINS) ∪ 그 앱 플랫폼의 포털 타일 주소(이 사람에게 보이는 것). 나머지는 화면이 거절한다."""
    out = set(_box_origins(settings.panel_link_origins))
    try:
        from app.catalog.routes import _fill_host, visible_systems  # noqa: PLC0415 — 늦은 import(카탈로그가 무겁지 않게)
        policy = request.app.state.access.get()
        tiles = {sid for i in policy.items if app in i.gateway for sid in i.systems}
        for s in visible_systems(request, request.app.state.catalog, principal):
            if s.id in tiles and s.integration_type == "external-url" and s.url:
                u = urlparse(_fill_host(s.url, request) or "")
                if u.scheme in ("http", "https") and u.netloc:
                    out.add(f"{u.scheme}://{u.netloc}".lower())
    except Exception:  # noqa: BLE001 — 타일을 못 읽으면 박스 허용만(닫힌 쪽)
        logger.info("패널 open-link 출처 — 타일을 읽지 못해 박스 허용만 쓴다", exc_info=True)
    return sorted(out)


def _audit(request: Request, principal: Principal, event: str, status: str, **meta) -> None:
    try:
        request.app.state.agent_audit.record(principal=principal.subject, event=event, status=status,
                                             tool=meta.pop("tool", None), meta=meta)
    except Exception:  # noqa: BLE001 — 감사 실패가 패널을 막지 않는다(로그로는 남긴다)
        logger.warning("패널 감사 기록 실패(%s)", event, exc_info=True)


# ── 창구 ─────────────────────────────────────────────────────────────────────────────────────────────────────────

class PanelOpenIn(BaseModel):
    model_config = {"extra": "forbid"}
    uri: str = Field(min_length=6, max_length=2048)
    tool: str = Field(min_length=1, max_length=200)
    call: str = Field(default="", max_length=80)


class PanelCallIn(BaseModel):
    model_config = {"extra": "forbid"}
    panel_id: str = Field(min_length=8, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    arguments: dict = Field(default_factory=dict)


class PanelReadIn(BaseModel):
    model_config = {"extra": "forbid"}
    panel_id: str = Field(min_length=8, max_length=64)
    uri: str = Field(min_length=6, max_length=2048)


class PanelConfirmIn(BaseModel):
    model_config = {"extra": "forbid"}
    panel_id: str = Field(min_length=8, max_length=64)
    token: str = Field(min_length=8, max_length=64)


class PanelCloseIn(BaseModel):
    model_config = {"extra": "forbid"}
    panel_id: str = Field(min_length=8, max_length=64)


def _html_of(res: dict, settings: Settings) -> tuple[str, dict]:
    """resources/read 결과 → (HTML, 그 내용의 _meta.ui). mimeType · 크기를 본다 — 틀리면 열지 않는다."""
    contents = res.get("contents") if isinstance(res, dict) else None
    c = contents[0] if isinstance(contents, list) and contents and isinstance(contents[0], dict) else None
    if c is None:
        raise AuthError("패널 리소스가 비었다", status_code=502, code="panel_resource_empty")
    mime = str(c.get("mimeType") or "").replace(" ", "").lower()
    if mime not in ASSUME_MIME:
        raise AuthError(f"패널 리소스의 형식({mime or '없음'})이 HTML 이 아니다 — 열지 않는다", status_code=502, code="panel_bad_mime")
    if isinstance(c.get("text"), str):
        html = c["text"]
    elif isinstance(c.get("blob"), str):
        import base64  # noqa: PLC0415
        try:
            html = base64.b64decode(c["blob"], validate=True).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            raise AuthError("패널 리소스를 풀지 못했다(base64 · UTF-8)", status_code=502, code="panel_bad_resource") from None
    else:
        raise AuthError("패널 리소스에 HTML 이 없다", status_code=502, code="panel_resource_empty")
    n = len(html.encode("utf-8"))
    if n > settings.panel_html_max_bytes:
        raise AuthError(f"패널 HTML 이 {n:,}바이트라 상한 {settings.panel_html_max_bytes:,}(PANEL_HTML_MAX_BYTES)을 넘는다 — 열지 않는다",
                        status_code=413, code="panel_html_too_large")
    meta = c.get("_meta") if isinstance(c.get("_meta"), dict) else {}
    ui = meta.get("ui") if isinstance(meta.get("ui"), dict) else {}
    if not ui and isinstance(res.get("_meta"), dict) and isinstance(res["_meta"].get("ui"), dict):
        ui = res["_meta"]["ui"]
    return html, ui


def _declared_uri(tools: list, name: str) -> str | None:
    """게이트웨이가 보여 준 그 도구의 패널 주소(`_meta.ui.resourceUri` 또는 옛 키 "ui/resourceUri" — HG-07 이 옮긴다)."""
    for t in tools or []:
        if isinstance(t, dict) and t.get("name") == name:
            m = t.get("_meta") if isinstance(t.get("_meta"), dict) else {}
            ui = m.get("ui") if isinstance(m.get("ui"), dict) else {}
            u = ui.get("resourceUri") or m.get("ui/resourceUri")
            return u if isinstance(u, str) else None
    return None


def _app_tools(tools: list, app: str, gwmap: dict) -> frozenset:
    """패널이 부를 수 있는 도구 — 게이트웨이가 패널 PAT 로 보여 준 목록(이미 그 앱 · 막음 목록 밖) ∩ 지도에서 그 앱 − 포털 막음 목록 −
    `_meta.ui.visibility` 가 있는데 app 이 없는 도구(모델 전용)."""
    m = gwmap.get("map") or {}
    out = set()
    for t in tools or []:
        if not isinstance(t, dict) or not isinstance(t.get("name"), str):
            continue
        name = t["name"]
        ui = (t.get("_meta") or {}).get("ui") if isinstance(t.get("_meta"), dict) else None
        vis = ui.get("visibility") if isinstance(ui, dict) else None
        if isinstance(vis, list) and "app" not in vis:
            continue
        if name in _DENY_EXACT or m.get(name) != app:
            continue
        out.add(name)
    return frozenset(out)


@router.post("/open")
async def panel_open(request: Request, body: PanelOpenIn, principal: Principal = Depends(get_current_principal),
                     _csrf: None = Depends(require_csrf), settings: Settings = Depends(get_settings)) -> dict:
    ensure(principal, FEATURE)
    if not body.uri.startswith("ui://"):
        raise AuthError("패널 주소는 ui:// 만 받는다", status_code=422, code="panel_bad_uri")
    await _sweep(settings)
    gwmap = await gw_map(settings)
    if gwmap.get("map") is None:
        raise AuthError("게이트웨이 도구 지도를 읽지 못했다 — 잠시 뒤 다시 연다", status_code=503, code="gateway_unavailable")
    app = (gwmap.get("map") or {}).get(body.tool) or ""
    if not app or app == "_gateway":
        raise AuthError("그 도구를 내는 앱을 모른다", status_code=404, code="panel_unknown_tool")
    if len(_TABLE) >= _MAX_PANELS:
        raise AuthError("열린 패널이 너무 많다 — 잠시 뒤 다시 연다", status_code=503, code="panel_busy")
    mine = sorted((p for p in _TABLE.values() if p.owner == principal.subject), key=lambda p: p.last)
    for p in mine[:max(0, len(mine) - _MAX_PANELS_PER_USER + 1)]:
        await _drop(p.id)                                  # 가장 오래된 것부터 닫는다(화면은 탭에 둘까지만 연다)
    conn = _Conn(settings.mcp_gateway_url, _mint_for(request, settings, principal, app, body.uri), settings.agent_request_timeout)
    pid = secrets.token_urlsafe(18)
    t0 = time.monotonic()
    try:
        listed = await conn.request("tools/list", {}, corr=f"panel:{pid[:8]}:open")
        # 그 도구가 단 패널 주소만 연다 — 같은 앱의 다른 ui:// 를 '패널' 로 열지 않는다(패널 안의 resources/read 는 /read 의 몫이다)
        if _declared_uri(listed.get("tools") or [], body.tool) != body.uri:
            raise AuthError("그 도구가 여는 패널 주소가 아니다", status_code=404, code="panel_uri_mismatch")
        res = await conn.request("resources/read", {"uri": body.uri}, corr=f"panel:{pid[:8]}:open")
        html, ui = _html_of(res, settings)
    except PanelUpstreamError as exc:
        await conn.close()
        _audit(request, principal, "panel_open", "error", tool=body.tool, app=app, uri=body.uri, code=exc.code,
               ms=round((time.monotonic() - t0) * 1000))
        raise AuthError(f"패널을 열지 못했다 — {exc.message}", status_code=404 if exc.code == "rpc_error" else 502,
                        code="panel_resource_unavailable" if exc.code == "rpc_error" else exc.code) from None
    except AuthError as exc:
        await conn.close()
        _audit(request, principal, "panel_open", "error", tool=body.tool, app=app, uri=body.uri, code=exc.code,
               ms=round((time.monotonic() - t0) * 1000))
        raise
    allowed = _app_tools(listed.get("tools") or [], app, gwmap)
    _TABLE[pid] = _Panel(id=pid, owner=principal.subject, email=principal.email, app=app, uri=body.uri, tool=body.tool,
                         call=body.call, allowed=allowed, conn=conn)
    _start_sweeper(settings)
    csp = _domains(ui.get("csp"), _box_origins(settings.panel_allowed_origins))
    _audit(request, principal, "panel_open", "ok", tool=body.tool, app=app, uri=body.uri, panel=pid[:8], call=body.call or None,
           bytes=len(html.encode("utf-8")), tools=len(allowed), ms=round((time.monotonic() - t0) * 1000))
    return {"panel_id": pid, "html": html, "csp": csp, "prefers_border": bool(ui.get("prefersBorder", True)),
            "app": app, "app_label": label_of(app), "uri": body.uri, "tool": body.tool, "tools": sorted(allowed),
            "open_origins": _open_origins(request, settings, principal, app),
            "limits": {"call_max_bytes": settings.panel_call_max_bytes, "session_max_mb": settings.panel_session_max_mb,
                       "idle_s": settings.panel_idle_s}}


def _is_write(name: str, gwmap: dict) -> bool:
    """쓰기로 보나 — 게이트웨이가 읽기로 확인한 도구(panel_read)만 읽기다. 그 목록을 모르면(옛 게이트웨이 · 못 읽음) 다 쓰기로 본다
    (ASSUME_WRITE_IS_UNKNOWN)."""
    read = gwmap.get("read")
    return ASSUME_WRITE_IS_UNKNOWN if read is None else name not in read


@router.post("/call")
async def panel_call(request: Request, body: PanelCallIn, principal: Principal = Depends(get_current_principal),
                     _csrf: None = Depends(require_csrf), settings: Settings = Depends(get_settings)):
    ensure(principal, FEATURE)
    p = _own(body.panel_id, principal, settings)
    if body.name not in p.allowed or body.name in _DENY_EXACT:
        _audit(request, principal, "panel_call", "rejected", tool=body.name, app=p.app, uri=p.uri, panel=p.id[:8], reason="tool_not_allowed")
        raise AuthError(f"이 패널은 {body.name} 을(를) 부를 수 없다 — 그 앱({label_of(p.app)})의 허용 도구만 부른다",
                        status_code=403, code="tool_not_allowed")
    n = len(json.dumps(body.arguments, ensure_ascii=False).encode("utf-8"))
    hp15 = "큰 파일은 챗 입력창의 파일 올리기(SimFlow 목적지)로 보낸다"
    if n > settings.panel_call_max_bytes:
        raise AuthError(f"인자가 {n:,}바이트라 호출 한 번의 상한 {settings.panel_call_max_bytes:,}(PANEL_CALL_MAX_BYTES)을 넘는다 — {hp15}",
                        status_code=413, code="call_too_large")
    cap = settings.panel_session_max_mb * 1024 * 1024
    if p.used + n > cap:
        raise AuthError(f"이 패널 세션이 보낸 양이 상한 {settings.panel_session_max_mb} MB(PANEL_SESSION_MAX_MB)에 닿았다 — {hp15}",
                        status_code=413, code="session_cap")
    gwmap = await gw_map(settings)
    write = _is_write(body.name, gwmap)
    if write and not p.write_ok:
        tok = secrets.token_urlsafe(18)
        p.pending[tok] = body.name
        while len(p.pending) > 8:
            p.pending.pop(next(iter(p.pending)))
        _audit(request, principal, "panel_call", "confirm_required", tool=body.name, app=p.app, uri=p.uri, panel=p.id[:8])
        return JSONResponse(status_code=409, content={"detail": {
            "code": "confirm_required", "token": tok, "tool": body.name, "app_label": label_of(p.app),
            "message": f"{label_of(p.app)} 패널이 쓰기 · 작업 제출 도구 {body.name} 을(를) 부르려 한다 — 이 패널 세션에서 허용할지 확인한다"}})
    p.used += n
    p.calls += 1
    corr = f"panel:{p.id[:8]}:{p.calls}"
    t0 = time.monotonic()
    async with p.sem:
        try:
            res = await p.conn.request("tools/call", {"name": body.name, "arguments": body.arguments}, corr=corr)
        except PanelUpstreamError as exc:
            _audit(request, principal, "panel_call", "error", tool=body.name, app=p.app, uri=p.uri, panel=p.id[:8], corr=corr, bytes=n,
                   ok=False, ms=round((time.monotonic() - t0) * 1000), code=exc.code, write=write)
            if exc.rpc is not None:
                return {"error": exc.rpc}
            raise AuthError(f"패널 호출 실패 — {exc.message}", status_code=502, code=exc.code) from None
    from app.procedures import judge as _J  # noqa: PLC0415 — upload.mcp_call 과 같은 판정기
    text, _other = _J.join_content(res.get("content") or [])
    ok = _J.judge(is_error=bool(res.get("isError")), text=text, raw=True).ok   # 패널 도구의 글은 평문일 수 있다 — 평문 실패 머리 · 봉투는 그대로 본다
    _audit(request, principal, "panel_call", "ok" if ok else "error", tool=body.name, app=p.app, uri=p.uri, panel=p.id[:8], corr=corr,
           bytes=n, ok=ok, ms=round((time.monotonic() - t0) * 1000), write=write)
    return {"result": res}


@router.post("/read")
async def panel_read(request: Request, body: PanelReadIn, principal: Principal = Depends(get_current_principal),
                     _csrf: None = Depends(require_csrf), settings: Settings = Depends(get_settings)) -> dict:
    ensure(principal, FEATURE)
    p = _own(body.panel_id, principal, settings)
    if not body.uri.startswith("ui://"):
        raise AuthError("패널은 ui:// 리소스만 읽는다", status_code=422, code="panel_bad_uri")
    cap = settings.panel_session_max_mb * 1024 * 1024
    over = AuthError(f"이 패널 세션이 읽은 양이 상한 {settings.panel_session_max_mb} MB(PANEL_SESSION_MAX_MB)에 닿았다 — 패널을 다시 연다",
                     status_code=413, code="session_read_cap")
    if p.read_bytes >= cap:
        raise over
    # /call 과 같은 줄(패널당 동시 _INFLIGHT_PER_PANEL) — 끝없는 루프 패널이 읽기로 게이트웨이를 두드리거나 큰 답을 한꺼번에 쥐지 않게(반대 검토 10-31)
    async with p.sem:
        try:
            res = await p.conn.request("resources/read", {"uri": body.uri}, corr=f"panel:{p.id[:8]}:read")
        except PanelUpstreamError as exc:
            if exc.rpc is not None:
                return {"error": exc.rpc}
            raise AuthError(f"패널 리소스 읽기 실패 — {exc.message}", status_code=502, code=exc.code) from None
        p.read_bytes += len(json.dumps(res, ensure_ascii=False).encode("utf-8"))
        if p.read_bytes > cap:
            raise over                  # 받은 것은 세되 화면으로 옮기지 않는다 — 다음 읽기는 게이트웨이에 묻지 않는다
    return {"result": res}


@router.post("/confirm")
async def panel_confirm(request: Request, body: PanelConfirmIn, principal: Principal = Depends(get_current_principal),
                        _csrf: None = Depends(require_csrf), settings: Settings = Depends(get_settings)) -> dict:
    """첫 쓰기 확인 — 포털이 그린 확인 창의 단추가 부른다(패널은 이 창구에 닿지 못한다 — 브리지는 tools/call 만 옮긴다). 기다리는 확인의 토큰만 받는다."""
    ensure(principal, FEATURE)
    p = _own(body.panel_id, principal, settings)
    tool = next((t for k, t in p.pending.items() if secrets.compare_digest(k, body.token)), None)
    if tool is None:
        raise AuthError("기다리는 확인이 없다", status_code=409, code="no_pending_confirm")
    p.write_ok = True
    p.pending.clear()                # 세션마다 한 번(B-2 (가)) — 같이 기다리던 다른 쓰기도 이 확인으로 풀린다
    _audit(request, principal, "panel_confirm", "ok", tool=tool, app=p.app, uri=p.uri, panel=p.id[:8])
    return {"ok": True}


@router.post("/close")
async def panel_close(request: Request, body: PanelCloseIn, principal: Principal = Depends(get_current_principal),
                      _csrf: None = Depends(require_csrf)) -> dict:
    p = _TABLE.get(body.panel_id)
    if p is None or p.owner != principal.subject:
        return {"ok": True}          # 이미 닫혔거나 남의 것 — 같은 답(있다는 사실을 흘리지 않는다)
    await _drop(p.id)
    _audit(request, principal, "panel_close", "ok", app=p.app, uri=p.uri, panel=p.id[:8], calls=p.calls, bytes=p.used)
    return {"ok": True}
