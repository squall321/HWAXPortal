# HWAX Portal — MCP Chat 통합 계획서

> 목적: 포털 최상단에 **MCP 기반 멀티에이전트 챗**을 붙인다. 채팅 UI는 포털 프론트 내부,
> 게이트웨이/에이전트 라우터는 포털 백엔드 내부에 통합한다(사용자 결정).
> 무거운 GPU 추론서버(vLLM)와 개별 MCP 서버들은 포털 밖 별도 호스트에 두고 `routes.env`로 연결한다.
>
> **작성 근거**: 검토 문서(아키텍처 일반론) + **포털 실제 코드 실측**(file:line). 추측 아님.
> 계획 → 4-에이전트 적대적 검증(§8) → 결정(§7 A·F·G) → 구현·실측 검증 완료.

---

## ★ 구현 현황 (2026-06-17 — dev 전체 체인 실동작)

전체 파이프라인이 dev에서 **끝까지 동작·검증**됨. LLM이 실제 MCP 툴을 호출하고 답이 챗까지 SSE로 흐름("123×7"→multiply→861, "서울 시간"→current_time).

```
ChatDock → 포털 :8723 /agent/chat → Agent Server :9009 (LangGraph ReAct)
            인증·CSRF·동시성·감사       → vLLM :8000 (Qwen2.5-7B, tool calling)
                                        → MCP :8011 (add/multiply/current_time)
```

| 단계 | 상태 | 커밋 / 위치 |
|---|---|---|
| Phase 0 레이아웃 mock | ✅ 검증 7/7 | `cc02233` · `docs/chatdock-layout-mock.html` |
| Phase 1 백엔드 SSE 골격 | ✅ echo 실 HTTP | `6c34c4e` · `backend/app/agent`, `app/mcp` |
| Phase 2 프론트 ChatDock | ✅ tsc/build/lint | `d34c995` · `frontend/src/components/chat` |
| Phase 3 nginx SSE + relay | ✅ `nginx -t`, relay 검증 | `817c454`, `0e7e5fd` |
| dev vLLM (Qwen 7B, 5070 Ti) | ✅ 추론+tool_calls | `docs/dev-vllm-setup.md` |
| Agent Server (LangGraph+MCP) | ✅ 툴 호출 | repo `squall321/HWAXAgentServer` |
| config 흠 수정 (port/문서) | ✅ env 없이 동작 | `24b85b3` |

**운영 가이드**: `docs/dev-stack-runbook.md` (기동/검증/정리 — 스택 미영속이라 재시작 절차 필수).

**남은 것(별도 작업, 코드 흠 아님)**: ① 스택 영속화(apptainer instance/supervisor) ② Agent Server JWKS 인증(현재 dev localhost 신뢰) ③ 실제 업무 MCP 툴(현재 데모) ④ 브라우저 UI 클릭 테스트(현재 curl) ⑤ MCP Gateway(tools/list·circuit breaker — 현재 Agent Server가 MCP 직접 연결).

---

## 0. 한 장 요약

```
                         ┌──────────────────────────────────────────────┐
   브라우저  ──https──▶  │ HWAX Portal (기존: React+Vite / FastAPI)       │
                         │  ─ 프론트: AppShell 안에 <ChatDock/> (신규)    │
                         │  ─ 백엔드: /agent, /mcp 라우터 (신규)          │
                         │     · 인증/groups/jwt-handoff = 기존 재사용 ★  │
                         └───────────────┬──────────────────────────────┘
                        routes.env / 원격 URL │  (SSE·HTTP)
              ┌──────────────────────────────┼─────────────────────────┐
              ▼                              ▼                          ▼
     Agent Server (LangGraph)        MCP Gateway (단일 진입점)    vLLM (Qwen 72B)
     · ReAct 멀티스텝                · 등록/라우팅/통합 툴목록     · OpenAI 호환 API
     · SSE 스트리밍                  · groups 기반 툴 필터          · 별도 GPU 호스트(B300)
                                     ├─ MCP-A · MCP-B · MCP-N …
```

**핵심 원칙 3가지**
1. **인증은 새로 만들지 않는다** — 포털은 이미 JWT `groups` 클레임 + `require_role()` + RS256 `jwt-handoff`(JWKS·jti replay 방어)를 갖췄다. 검토 문서가 "Keycloak 도입"으로 잡은 §4는 **이미 포털 안에 있다**. 게이트웨이의 `allowed_groups` 필터링은 기존 `visible_for(groups)` 패턴을 복제한다.
2. **무거운 것은 밖에 둔다** — vLLM·개별 MCP 서버는 포털과 다른 호스트. 포털은 `routes.env`에 원격 URL만 등록(원격 IP/도메인 지원 확인됨). 포털 apptainer(rootless, GPU 미할당)는 손대지 않는다.
3. **포털 안에 새로 만드는 건 두 가지뿐** — ① 프론트 `ChatDock` ② 백엔드 `/agent`(에이전트 프록시·SSE) + `/mcp`(서버 레지스트리). 나머지(Agent Server·Gateway·vLLM)는 포털 밖 별도 서비스.

---

## 1. 미결 사항 — 실측으로 닫힌 것 (검토 문서 §9)

검토 문서의 "확인 필요" 6개 중 포털 코드로 답 나온 것:

| 검토 문서 미결 | 실측 결론 | 근거 |
|---|---|---|
| 사내 Keycloak 존재 여부 | **불필요.** 포털이 SAML SP + 자체 JWT 발급(HS256 세션 / RS256 다운스트림)을 이미 함 | `backend/app/auth/saml_provider.py`, `auth/jwt_service.py`, `auth/downstream.py` |
| 포털 상태관리 라이브러리 | **React Context.** Redux/Zustand/Recoil 없음. 챗은 새 `ChatContext` | `frontend/src/auth/AuthContext.tsx` (유일 전역상태), `package.json` |
| MCP 서버 인증 방식 | 게이트웨이가 **RS256 launch 토큰**(audience 스코핑) 재사용 가능. MCP 서버는 포털 JWKS로 검증 | `auth/downstream.py:44-64`, `auth/routes/jwks.py` |
| JWT에 groups/권한 있나 | **있음.** `Principal.groups` ← SAML `memberOf`. `require_role()`, `visible_for(groups)` 동작 중 | `auth/provider.py:17-25`, `catalog/registry.py:80-87` |
| 응답 히스토리 저장 | 결정 필요(§7-D) — 기존 SQLite `TokenStore` 패턴 확장 가능 | `auth/token_store.py:19-40` |
| MCP 등록 권한자 | 결정 필요(§7-A) — `require_role("portal-admin")` 그대로 적용 가능 | `catalog/routes.py:57-64` |

**남는 진짜 미결**(포털 밖 영역, §7에서 다룸): CAD 포맷 범위, 대화 히스토리 영속화 여부, MCP 등록 거버넌스, vLLM 호스트 확보.

---

## 2. 컴포넌트별 구현 위치 (포털 내부)

### 2-A. 프론트엔드 — `ChatDock`

| 항목 | 결정 | 근거(실측) |
|---|---|---|
| 끼우는 위치 | `AppShell` 한 곳 (AppHeader 아래/옆) → 전 보호 라우트에 자동 노출 | `components/layout/AppShell.tsx:4-12`, `App.tsx:10-33` |
| 레이아웃 | **우측 고정 도크(fixed dock) + 토글**. AppShell을 flex로 바꾸지 않고 z-index/right로 격리해 `.hero` full-bleed·`.pgrid` 반응형과 충돌 회피 | `pages/PortalHomePage.tsx:42-91`(hero+pgrid 구조), 충돌 분석 결과 |
| 상태관리 | 새 `ChatContext`(메시지/입력/스트림 상태) — `App.tsx`의 `AuthProvider`와 같은 층에 Provider | `auth/AuthContext.tsx` 패턴 복제 |
| API 호출 | 비-스트림 호출(히스토리 등)은 `apiFetch` 재사용(쿠키·CSRF·401 자동 refresh). **스트림은 EventSource 불가** → `fetch`+`ReadableStream` 직접 사용(아래 ★) | `api/client.ts:31-46`, §8-검증3 |
| 사용자 정보 | `useAuth()` 훅으로 user/groups | `auth/useAuth.ts` |
| 스타일 | 기존 CSS 변수(`--bg/--fg/--accent/--card/--border`) 재사용 → 다크테마 일관 | `styles/globals.css` |

**신규 파일**: `components/chat/ChatDock.tsx`, `components/chat/MessageList.tsx`, `components/chat/Composer.tsx`, `components/chat/renderers/{TextBlock,GraphFrame,CadFrame}.tsx`, `state/ChatContext.tsx`, `api/chat.api.ts`, `hooks/useSSE.ts`, `types/chat.ts`, `styles/chat.css`.

**렌더러 격리**: 에이전트가 돌려준 그래프 HTML은 `dangerouslySetInnerHTML` 금지 → **iframe sandbox**(`sandbox="allow-scripts"`, srcdoc)로 XSS 차단. Plotly(2D)·Three.js(3D)·CAD(OCCT-wasm)는 Phase 4.

**★ 스트리밍은 EventSource가 아니라 `fetch`+`ReadableStream`** (검증에서 확정): `POST /agent/chat`은 CSRF 헤더(`X-CSRF-Token`)가 필요한데 EventSource는 GET·쿠키만 되고 커스텀 헤더를 못 보낸다. 따라서 `useSSE` 훅은 `fetch(POST, body=메시지, headers=CSRF)` → `response.body.getReader()`로 스트림을 읽고 `event:`/`data:` 프레임을 **수동 파싱**한다. (CSRF·credentials는 `apiFetch`와 동일 규칙을 손으로 맞춤 — `apiFetch` 자체는 스트림 미지원이라 직접 못 씀.)

**도크 레이아웃은 CSS로 명시 격리** (검증에서 확정 — 자동 회피 안 됨): `.hero`는 full-bleed가 아니라 중앙 1180px이고, `.pgrid`의 `auto-fill minmax(320px)`는 우측 도크 너비를 **모른다** → 그대로 두면 마지막 카드가 도크 뒤로 숨는다. 해결: 도크 `width:340px; position:fixed; right:0; top:<header>; height:calc(100vh-<header>); z-index:100`로 고정하고, **도크 열림 상태에서 `.home-wrap`에 `padding-right:340px`**(또는 body class 토글)로 그리드 공간을 비운다. 모바일(`max-width:768px`)은 도크를 **풀스크린 모달**로 전환(고정 사이드바 금지). AppHeader는 `position` 없음(정상 flow)이라 top만 헤더 높이로 맞추면 됨.

### 2-B. 백엔드 — `/agent` + `/mcp` 라우터

| 항목 | 결정 | 근거(실측) |
|---|---|---|
| 라우터 등록 | `app/agent/routes.py`, `app/mcp/routes.py` → `main.py`에서 `include_router` | `main.py:46-87` 패턴 |
| MCP 레지스트리 | `mcp_servers.yaml` + `MCPRegistry`(YAML 로드·검증·reload) — `CatalogRegistry` 복제. **단 health/상태 추적 추가** | `catalog/registry.py:23-76` |
| 권한 필터링 | `visible_for(groups)` 동일 로직으로 툴 목록을 그룹별 필터 | `catalog/registry.py:80-87` |
| 외부 호출 | `httpx.AsyncClient`(timeout, 토큰 캐싱) fan-out. **연결 풀 1개 공유**(앱 state) | `mail/graph.py:11-64`, gap: 풀 관리 |
| 설정 | `pydantic Settings`에 `AGENT_SERVER_URL`/`MCP_GATEWAY_URL` 필드 추가 | `config.py:11-142` |
| 싱글톤 | `app.state`에 `mcp_registry`·`agent_client`를 lifespan에서 초기화 | `main.py:29-87` |
| **SSE (신규)** | `StreamingResponse`(`media_type="text/event-stream"`)로 `/agent/chat` 스트리밍 — **포털에 SSE 전례 없음**(전부 JSONResponse). `sse-starlette`는 requirements에 없음 → 추가하거나 표준 `StreamingResponse`로 직접 | gap: SSE 미구현, §8-검증3 |
| **httpx 풀 (신규)** | lifespan에서 `httpx.AsyncClient(limits=Limits(max_connections=…))` 1개를 `app.state.agent_client`로 생성·공유. 현재 mail은 매 호출마다 새로 만듦(풀 없음) → 중계엔 부적합 | `mail/graph.py:36,64`, §8-검증4 |
| **동시성 가드 (신규)** | `asyncio.Semaphore`로 동시 `/agent/chat` 상한. SSE 1연결=1스트림이라 1만 동시 언급은 가드 없이 못 버팀 | §8-검증4 |

**포털 백엔드의 역할은 "얇은 프록시 + 권한 게이트"**: 실제 LLM·LangGraph·MCP fan-out은 **Agent Server**(포털 밖)가 한다. 포털 `/agent`는 ① 세션 인증(`get_current_principal`) ② groups를 RS256 토큰으로 Agent Server에 handoff ③ SSE를 브라우저로 중계만 한다. → 포털 프로세스에 무거운 의존성(LangGraph 등)을 넣지 않는다.

### 2-C. 인프라 — `routes.env` + nginx

| 항목 | 결정 | 근거(실측) |
|---|---|---|
| Agent/Gateway 등록 | `routes.env`에 `agent-server=http://<원격>:<port>/` 등 — 원격 호스트 지원 확인 | `gen-nginx-conf.sh:3-4`, `routes.prod.env` |
| **SSE 버퍼링 (신규)** | SSE location에 `proxy_buffering off; proxy_read_timeout 1h; proxy_connect_timeout 300; gzip off; add_header X-Accel-Buffering no;` — **`gzip off`가 핵심**(전역 `gzip on`이 SSE 청크를 버퍼링), 기본 `proxy_read_timeout 60s`는 긴 대화를 끊음 | `hwax.conf.tmpl:24-41`, §8-검증3 |
| vLLM 분리 | 별도 GPU 호스트(B300). 포털 apptainer 무관(host network) | `start.sh:44-90`, `_common.sh:24-26` |
| 토큰 검증 | Agent/MCP는 포털 `/.well-known/jwks.json`로 RS256 검증 → 비밀 공유 불필요 | `auth/routes/jwks.py` |

---

## 3. 포털 밖 별도 서비스 (이 레포 아님 / 별도 추진)

> 포털 통합 범위 **밖**. 계획엔 넣되 구현은 별도 레포·별도 일정. 포털은 URL로만 연결.

- **Agent Server** (LangGraph + Qwen): `/chat`(SSE)·`/chat/{id}/cancel`. ReAct 멀티스텝, 툴 호출 상한(10~20), 응답 포맷 표준(`{type: text|graph|cad, content, metadata}`).
- **MCP Gateway**: `/servers`·`/tools/list`·`/tools/call`·`/health`. 네임스페이스 충돌 방지(`<prefix>.<tool>`), Circuit Breaker, 툴목록 캐싱, per-server timeout(30s).
- **vLLM**: OpenAI 호환 API. 초기 vLLM → 병목 시 TensorRT-LLM 검토. **dev/prod 2-트랙으로 분리(아래 §3-1)**.
- **개별 MCP 서버**: 서브페이지마다 1개. 표준 등록 JSON(`name/url/description/auth/allowed_groups/tools_prefix`).

### 3-1. vLLM 추론 서버 — dev / prod 2-트랙

포털은 vLLM을 URL로만 연결하므로(§2-C), **개발과 운영을 다른 GPU·다른 모델로 분리**하고 `routes.env`의 IP·모델명만 스왑한다. **코드는 한 줄도 안 바뀐다.**

| | **개발 (이 서버)** | **운영 (별도 호스트)** |
|---|---|---|
| GPU | RTX 5070 Ti (VRAM 16GB) | B300 8장 |
| 모델 | Qwen2.5 **7B/14B** AWQ(16GB에 맞춤) | Qwen2.5 **72B** + Coder **72B** |
| 용도 | SSE·에이전트·MCP·ChatDock 경로 **끝까지 검증** | 실제 품질·동시성 |
| 연결 | `routes.env`(dev): `agent-server=http://127.0.0.1:9000/` | `routes.prod.env`(prod): `agent-server=http://<B300-IP>:9000/` |

- **5070 Ti로 72B는 불가**(72B는 INT4도 ~40GB ≫ 16GB) → dev는 **7B 권장**(가장 안정), 데모는 14B까지.
- 5070 Ti = Blackwell(sm_120) → **CUDA 12.8+ / 최신 vLLM** 필요(구버전은 GPU 미인식).
- **B300은 지금 막힌 게 아님** — dev vLLM으로 Phase 0~3 전부 검증 가능. B300은 **운영 연결(Phase 3 prod) 직전에만** 확보되면 된다.
- dev↔prod 전환은 기존 `ROUTES_PATH`(routes.env vs routes.prod.env) 패턴 그대로 사용.

---

## 4. 인증·권한 흐름 (기존 자산 재사용 ★)

```
브라우저(세션쿠키) ─▶ 포털 /agent/chat
   │  get_current_principal()  → Principal{sub,email,groups}      [기존 deps.py]
   │  require_role(...) (선택)  → 그룹 게이트                       [기존 deps.py]
   ▼
포털이 RS256 launch 토큰 발급(audience=agent-server, TTL 90s)       [기존 downstream.py]
   │  groups 클레임 포함
   ▼
Agent Server: 포털 JWKS로 토큰 검증 → groups 추출                   [기존 jwks.py 재사용]
   │
   ▼
MCP Gateway: tools/list를 groups로 필터 (allowed_groups)           [visible_for 패턴 복제]
```

- 새 IdP·Keycloak·새 토큰 체계 **불필요**. 검토 문서 §4(SAML→JWT 변환 레이어)는 포털이 이미 수행.
- **권한 필터 알고리즘 재확인(용어 정정)**: 포털의 `visible_for(groups)`는 시스템의 **`required_role`(단일 문자열)이 사용자 `groups` 리스트에 포함되는지**를 본다(`registry.py:80-87`, `schema/system.py:38`). MCP의 `allowed_groups`(복수 허용)는 이와 **다른 개념** — 게이트웨이 측에서 "툴의 allowed_groups ∩ 사용자 groups ≠ ∅"로 구현한다. "동일 패턴을 참고"하되 단순 복붙 아님.
- **토큰 TTL 정책(확정 필요 → §7-F)**: launch 토큰 TTL=90초(`config.py:88`)인데 멀티스텝 ReAct(툴 10~20회)가 수 분 걸리면 만료된다. **채택안**: Agent Server가 받은 토큰은 *세션 식별·인가 스냅샷용*으로만 쓰고(만료돼도 진행 중 루프엔 영향 없음), MCP 호출의 실시간 권한은 **게이트웨이가 자체 단기 서비스토큰**으로 처리. 또는 `/agent` 전용으로 TTL을 별도 설정값(예 10분)으로 분리. → §7-F에서 택1.
- **gap(보완)**: 감사 로깅 부재(누가 어떤 툴 호출했는지), refresh 토큰 revocation 없음 → 감사 로깅은 Phase 1로 당김(§7-D 수정).

---

## 5. 데이터 계약 (포털이 의존하는 표준)

에이전트 응답 — 포털 렌더러가 파싱하는 유일한 계약:
```jsonc
{ "type": "text",  "content": "…" }
{ "type": "graph", "content": "<html>…</html>", "metadata": {"title":"…","source":"mcp_stress"} }
{ "type": "cad",   "content": "base64…",        "metadata": {"part_id":"…","format":"STEP"} }
```
호출 방식 — **`POST /agent/chat`**(body=메시지/현재 시스템 id, 헤더=CSRF). 응답 `Content-Type: text/event-stream`. 브라우저는 `fetch`+`ReadableStream`으로 수신(EventSource 아님 — §2-A ★).
SSE 이벤트 — 진행 상태 표시용:
```text
event: status   data: {"step":"응력 데이터 조회 중","tool":"stress.get_curve"}
event: token    data: {"delta":"…"}
event: result   data: { …위 응답 객체… }
event: error    data: {"code":"gateway_down|timeout|token_expired|cancelled","message":"…"}
event: done     data: {}
```
- **중간 종료 이벤트 필수**(검증): 취소(`POST /agent/chat/{id}/cancel`)·타임아웃·토큰만료·게이트웨이 장애는 스트림 중간에 `event: error` 한 프레임 + `event: done`으로 깔끔히 닫는다. 클라이언트는 reader를 abort하고 도크에 사유 표시.
- 이 계약만 고정하면 Agent Server 내부 구현(LangGraph 버전 등)이 바뀌어도 포털은 영향 없음.

---

## 6. 단계별 구현 순서 (포털 통합 관점)

```text
Phase 0 — 레이아웃 검증 (코드 전, CSS mock)   검증: 도크 mock을 끼우고 375/768/1920px 3폭에서 콘텐츠 안 가림
└── ChatDock 더미(width340/fixed/z-index) + .home-wrap padding-right + 모바일 모달 분기

Phase 1 — 백엔드 골격 (포털 내부)        검증: POST /agent/chat?mode=echo가 text/event-stream으로 status×N+done 반환
├── /mcp 레지스트리(mcp_servers.yaml + MCPRegistry, reload, /mcp/health)
├── /agent 프록시 라우터(get_current_principal + require_csrf + RS256 handoff + SSE 중계)
├── ★ dev echo: /agent/chat?mode=echo — 원격 Agent Server 없이 SSE 경로 자체를 검증(mock 경계 = 이 한 엔드포인트)
├── config 필드(AGENT_SERVER_URL, MCP_GATEWAY_URL, agent_token_ttl, max_concurrent_chats)
├── httpx 풀 싱글톤(app.state.agent_client) + asyncio.Semaphore 동시성 가드
└── ★ 감사 로그 스키마(audit_logs: ts, principal, tool, status, meta) + insert 지점 (Phase 4 아님)

Phase 2 — 프론트 ChatDock (포털 내부)    검증: 도크 토글·메시지 송수신·SSE 스트림·중간 error/cancel 화면 표시
├── ChatContext + ChatDock + Composer + MessageList
├── ★ useSSE 훅(fetch+ReadableStream, CSRF 헤더, event/data 수동 파싱, AbortController)
└── AppShell에 <ChatDock/> 삽입(Phase 0에서 확정한 격리 CSS 적용)

Phase 3 — 인프라 SSE 경로                검증: https로 /agent/chat 스트림이 nginx 버퍼링 없이 끊김없이 흐름(60s↑ 유지)
├── routes.env에 agent-server / mcp-gateway 등록
├── nginx SSE location(proxy_buffering off, gzip off, read_timeout 1h, X-Accel-Buffering no)
└── Agent Server·Gateway·vLLM은 원격 URL 연결(별도 서비스 가동 전제)

Phase 4 — 렌더러·고도화
├── GraphFrame(iframe sandbox, Plotly/Three.js)
├── CadFrame(OCCT-wasm, progressive load)
├── 게이트웨이 degrade(tools/list 로컬 캐시 + stale flag, /mcp/health 폴링, "일부 툴 사용불가" UI)
└── 히스토리 영속화(결정 시) / Circuit Breaker(게이트웨이 측)
```

각 Phase는 **포털만으로 검증 가능한 종료조건**을 가진다. **mock 경계는 단 하나 — `/agent/chat?mode=echo`** dev 엔드포인트(`dev_downstream.py` 패턴 확장). 이것만 있으면 원격 Agent Server 없이 Phase 1·2·3을 전부 검증한다. 그 외 어디에도 mock 없음.

---

## 7. 결정 사항

**구현 착수 전 닫아야 하는 3개 — 확정 완료(2026-06-14):**

- **A. MCP 등록 거버넌스 → ✅ PR 기반 + admin reload.** `mcp_servers.yaml`은 git PR로만 추가(diff = 감사 기록), 런타임 반영은 `require_role("portal-admin")`이 건 `POST /mcp/reload`. systems.yaml과 동일 관례.
- **F. 토큰 TTL 전략 → ✅ 게이트웨이 서비스토큰(②).** 포털 launch 토큰(90s)은 "누구인가"의 인가 스냅샷용 — 진행 중 ReAct 루프 중 만료돼도 무방. MCP 실시간 권한은 **게이트웨이가 자체 단기 서비스토큰**으로 처리. → 포털 `config.py:88`의 90s TTL은 그대로 두고 별도 분리 불필요.
- **G. 동시성 상한 → ✅ 429 + 재시도 안내.** `max_concurrent_chats`(`asyncio.Semaphore`) 초과 시 즉시 `429` + "잠시 후 다시" 안내. 대기 큐 아님(서버 보호·예측 가능).

**구현 중/Phase에서 닫아도 되는 것(기본값 채택, 변경 시에만 알림):**

- **B. ChatDock 레이아웃** — 우측 fixed 도크 채택(전 페이지 호출 + 현재 페이지 컨텍스트 인지). Phase 0에서 CSS로 확정.
- **C. 페이지별 컨텍스트** — systems.yaml의 현재 시스템 id를 챗에 전달해 시스템 프롬프트/툴 스코프 자동 분기. Phase 2에서 구현.
- **D. 히스토리 영속화** — 대화 맥락 유지는 추후 결정(기본: 세션 메모리). **단 감사 로깅(누가/언제/어떤 툴/어떤 데이터)은 영속화와 무관하게 Phase 1 필수** — 설계데이터 접근은 규정상 backfill 불가.
- **E. vLLM 호스트 → 2-트랙 확정(§3-1).** dev=이 서버 5070 Ti(Qwen 7B/14B)로 Phase 0~3 검증, prod=B300(72B)는 운영 연결 직전 확보. `routes.env`/`routes.prod.env` IP·모델명만 스왑. **B300 미확보는 개발을 막지 않음.**

---

## 8. 계획 검증 결과 (4-에이전트 적대적 검토 완료)

이 계획서를 4갈래(재사용 주장·레이아웃·SSE·누락/위험)로 실제 코드 대조 검증했다. 결과를 본문에 반영했고, 핵심은 아래와 같다.

### 검증1 — 재사용 주장: 대부분 confirmed, 용어 1건 정정
- `get_current_principal`·`require_role(role)`·`JwtDownstreamIssuer.mint(principal, audience=)`·JWKS 엔드포인트 — **전부 confirmed**. `mint`는 `groups` 클레임을 실제로 토큰에 넣음(`downstream.py:52`). RS256·kid 헤더 확인.
- `visible_for(groups)` — **partial(용어 정정)**: `required_role`(단일 str|None)을 groups에 매칭. MCP의 `allowed_groups`(복수)와 다른 개념 → §4 본문 정정 완료.

### 검증2 — 레이아웃: "자동 회피" 주장은 wrong, 명시 CSS 필수
- `.hero` full-bleed 주장 **wrong** — 실제 중앙 1180px(`home.css:76-81`).
- `.pgrid auto-fill이 도크만큼 줄어든다` **wrong** — 그리드는 도크를 모름 → 카드가 도크 뒤로 숨음(`home.css:182-186`).
- 모바일 브레이크포인트 **전무**(`@media`는 reduced-motion 1개뿐).
- → **Phase 0 신설**(코드 전 CSS mock 검증), `.home-wrap padding-right:340px` + 모바일 풀스크린 모달로 §2-A 수정 완료.

### 검증3 — SSE: 구조 결함 1건(EventSource) + nginx 누락 1건, 둘 다 치명
- **EventSource 불가(구조 결함)** — POST+CSRF 필요한데 EventSource는 GET·쿠키만·헤더 불가 → `fetch`+`ReadableStream` 수동 파싱으로 확정(§2-A ★, §5, §6 Phase 2 수정).
- **nginx 버퍼링(FAIL)** — 전역 `gzip on` + 기본 `proxy_buffering on` + `proxy_read_timeout 60s`가 SSE를 끊음. `gzip off`까지 포함해 §2-C·Phase 3 수정.
- FastAPI/Starlette는 `StreamingResponse(media_type="text/event-stream")` 가능, `sse-starlette`는 requirements에 없음(추가 또는 표준 사용). apptainer rootless는 long-lived 연결에 문제없음(확인).

### 검증4 — 누락/위험: 5건 모두 본문에 반영
- **토큰 90s TTL** vs 멀티스텝 → §7-F 결정항 신설.
- **취소/타임아웃/만료 중 스트림** 미정의 → §5에 `event: error` 종료 프레임 계약 추가.
- **동시성(1만)** 가드 없음 → httpx 풀 싱글톤 + `Semaphore`(§2-B), §7-G 결정항.
- **감사 로깅 Phase 4는 늦음**(설계데이터 규정) → Phase 1로 당김(§6, §7-D).
- **게이트웨이 degrade 부재** → tools/list 로컬 캐시 + `/mcp/health` 폴링(§6 Phase 4).
- **mock 경계 불명확** → `/agent/chat?mode=echo` 단일 dev 엔드포인트로 확정(§6).

### 검증 후 잔여 리스크(구현 중 실측으로만 닫힘)
1. **SSE end-to-end가 apptainer+nginx(TLS)에서 실제로 안 끊기는지** — 가장 큰 미검증. Phase 3에서 60초↑ 스트림으로 실측.
2. **토큰 TTL 최종안(§7-F)** — ②(게이트웨이 서비스토큰) 채택 시 게이트웨이 설계와 맞물림.
3. **1만 동시 SSE의 실제 워커/메모리 한계** — 부하 테스트 전엔 추정치.

→ **위 3개를 제외하면 계획은 검증 통과.** §7 결정항(A·F·G 특히)을 닫은 뒤 Phase 0(CSS mock) → Phase 1 순으로 착수.

---

## 부록 — 재사용 자산 인덱스 (file:line)

| 자산 | 위치 | 챗에서 용도 |
|---|---|---|
| `get_current_principal` | `backend/app/deps.py:33-45` | /agent 인증 게이트 |
| `require_role(role)` | `backend/app/deps.py:48-56` | 툴/엔드포인트 그룹 게이트 |
| `require_csrf` | `backend/app/deps.py:59-72` | POST /agent/chat CSRF |
| `Principal{groups}` | `backend/app/auth/provider.py:17-25` | groups 추출 |
| `JwtDownstreamIssuer.mint` | `backend/app/auth/downstream.py:44-64` | Agent Server handoff 토큰 |
| JWKS 엔드포인트 | `backend/app/auth/routes/jwks.py:9-14` | Agent/MCP 토큰 검증 |
| `CatalogRegistry`(YAML 로드·reload) | `backend/app/catalog/registry.py:23-76` | MCPRegistry 복제 원형 |
| `visible_for(groups)` | `backend/app/catalog/registry.py:80-87` | allowed_groups 필터 |
| include_router 패턴 | `backend/app/main.py:46-87` | /agent·/mcp 등록 |
| `httpx.AsyncClient` 패턴 | `backend/app/mail/graph.py:11-64` | Gateway fan-out |
| `apiFetch`(쿠키·CSRF·재시도) | `frontend/src/api/client.ts:31-46` | chat.api 호출 |
| `AppShell` 레이아웃 | `frontend/src/components/layout/AppShell.tsx:4-12` | ChatDock 삽입점 |
| `AuthContext`/`useAuth` | `frontend/src/auth/AuthContext.tsx` | 챗 user/groups |
| CSS 변수 테마 | `frontend/src/styles/globals.css` | ChatDock 스타일 |
| routes.env + gen-nginx-conf | `infra/scripts/gen-nginx-conf.sh:3-46` | agent-server 라우팅 |
| WebSocket map(참고) | `infra/nginx/hwax.conf.tmpl:28-41` | SSE 설정 추가 지점 |
