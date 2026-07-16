<!-- HWAX 계열 앱을 '챗 우선(chat-first)'으로 만드는 표준 지시서 — 메인=챗, AgentServer/MCP 게이트웨이 배선 -->
# HWAX — 챗 우선(chat-first) AI 통합 표준 지시서

> 각 서브 프로젝트(ReportArchive · SignalForge · AIDataHub · MXWhitePaper …)가 **자기 메인 페이지를 챗으로** 바꿀 때 따르는 표준.
> 목표는 "포털 경유 `/<app>/` 로 들어가면 첫 화면이 챗이고, 거기서 데이터를 올려 질문하면 그 앱의 MCP 도구가 답한다".
> 반드시 함께 볼 것 — 서브패스 규칙은 `PORTAL-INTEGRATION-PLAYBOOK.md §2`, 외부 vLLM/LLM 설정 원칙은 같은 문서 `§8`, 타일 연결 방식은 `LINKED-SERVICES.md`.

한 줄 그림. 브라우저 → (앱 or 포털) 얇은 릴레이 → **HWAXAgentServer(:9009)** → vLLM(추론) + **HWAXMcpGateway(:9110/mcp)** → 하위 서비스 도구(46개).
AI 배선의 실체(모델 호출·도구 fan-out)는 전부 AgentServer/게이트웨이에 있고, **각 앱은 게이트웨이 하나만 본다**(도구를 앱이 직접 물지 않는다).

---

## 1. 목적 / 원칙

- **메인 페이지 = 챗.** 앱 `/` 는 전체화면 대화창이다. 사용자는 데이터를 올리고 질문해서 **일을 시킨다** — 메뉴를 뒤지는 게 아니라 대화로 작업한다.
- **카탈로그·사용 설명 = 보조 페이지.** 기능 목록/도움말/설정은 `/apps` 같은 **보조 라우트**로 밀어낸다(챗에서 링크로 연다).
- **왜 챗 우선인가.** 진입 지점을 하나(대화)로 통일하면 사용자가 배울 게 줄고, 앱마다 다른 UI 대신 **같은 대화 인터페이스**로 페더레이션 전체를 쓴다. 실제 능력은 각 앱의 **MCP 도구**가 제공하고, 챗은 그 도구를 부르는 얇은 표면일 뿐이다.
- **앱은 AI 인프라를 소유하지 않는다.** vLLM·게이트웨이·AgentServer 는 페더레이션 공용이다. 앱이 하는 일은 ① 챗 UI 를 메인으로 올리고 ② 자기 도메인 데이터를 챗으로 받고 ③ 자기 MCP 도구를 게이트웨이에 등록하는 것뿐이다.

---

## 2. 아키텍처 (텍스트)

```
브라우저
  │  HTTPS · 세션쿠키 · X-CSRF-Token · fetch(POST)+ReadableStream 으로 SSE 수신 (EventSource 아님)
  ▼
앱 '/' 풀스크린 챗   또는   포털 ChatDock (우측 도크)
  │  same-origin  POST /agent/chat        (포털 릴레이 재사용 — 최소안)
  │        또는   POST /<app>/api/agent/chat (앱 자체 릴레이 — 데이터/컨텍스트 주입 시)
  ▼
포털/앱 백엔드 = 얇은 릴레이 (세션 인증 · CSRF · 동시성 캡 · 감사 · SSE 중계)
  │  HTTP  POST {message, system_id, groups}  →  agent_server_url  ·  SSE 를 byte-for-byte 되돌림
  ▼
HWAXAgentServer :9009  (LangGraph ReAct 루프)
  ├─ HTTP(OpenAI 호환)  →  vLLM :8000/v1        [VLLM_BASE_URL / VLLM_MODEL]
  └─ streamable-http /mcp · Authorization: Bearer <GW_TOKEN> · X-HWAX-Groups: <caller groups>
        ▼
     HWAXMcpGateway :9110/mcp  (3개 백엔드 집계 = 도구 46개 · 그룹 기반 필터)
        │  streamable-http /mcp · 백엔드별 네이티브 토큰을 중앙에서 주입 (rat_ / sfmcp_ / mxwp_)
        ▼
     하위 서비스 MCP  ── reportarchive :3002 · signalforge :8013 · mx-white-paper :8765 · (신규 앱 추가)
```

- **화살표 프로토콜.** 브라우저↔릴레이 = HTTPS(same-origin, 세션쿠키+CSRF, 응답은 `text/event-stream`). 릴레이↔AgentServer = HTTP JSON 요청 + SSE 응답. AgentServer↔vLLM = OpenAI 호환 HTTP. AgentServer↔게이트웨이 = streamable-http `/mcp`(Bearer `GW_TOKEN` + `X-HWAX-Groups`). 게이트웨이↔백엔드 = streamable-http `/mcp`(백엔드 토큰 주입).
- **SSE 계약(§5 데이터 계약).** 이벤트 순서는 `status`(진행/도구 호출) → `token`×N(부분 응답) → `result`(`{type,content,metadata}`) → `done`. 실패는 스트림 중간에 `error` 한 프레임 + `done` 으로 닫는다.
- **그룹 스코핑.** caller 의 `groups` 가 릴레이→AgentServer(body)→게이트웨이(`X-HWAX-Groups`)로 전달되고, 게이트웨이가 `allowed_groups` 교집합으로 도구 목록을 필터한다(안 보이는 도구는 LLM 이 존재조차 모름 · fail-closed).

---

## 3. 프론트 지침 (앱 프론트엔드)

- **라우트 전환.** `/` = 전체화면 챗(랜딩), 카탈로그/설명/설정은 `/apps`(또는 `/help`, `/catalog`) 보조 라우트로. 딥링크 새로고침이 200 이어야 하므로 SPA fallback 유지.
- **서브패스 3종 준수(playbook §2 — proxy 의 핵심).** 앱이 `/<app>/` 아래로 서빙되므로 세 손잡이를 모두 건다.
  - **빌드 base** — `vite build --base=/<app>/` (에셋 경로에 prefix).
  - **라우터 basename** — `createBrowserRouter(routes, { basename: import.meta.env.BASE_URL.replace(/\/+$/, '') || '/' })`. 이 한 줄이 §2 #1 함정이다. standalone 빌드(base `/`)면 `/` 가 되어 동작 동일하므로 항상 넣는다.
  - **API base** — `VITE_API_BASE_URL=/<app>` → 챗 호출이 `/<app>/api/...` 로 나가고 nginx 가 prefix 를 벗겨 백엔드 `/api/...` 에 도달.
  - 포털용 빌드 한 줄. `NODE_OPTIONS=--max-old-space-size=8192 VITE_API_BASE_URL=/<app> npx vite build --base=/<app>/`.
- **챗 컴포넌트 구성.** `ChatPage`(풀스크린) = `MessageList` + `Composer`(입력 + 파일 첨부) + 상태 표시(status 이벤트로 "도구 호출 중" 등). 렌더러는 `type` 별로 분기(`text` / `graph` / `cad`). 그래프 HTML 은 `dangerouslySetInnerHTML` 금지 — **iframe sandbox**(`sandbox="allow-scripts"`, `srcdoc`)로 격리.
- **스트리밍은 `fetch`+`ReadableStream`(EventSource 금지).** `POST` + CSRF 헤더가 필요한데 EventSource 는 GET·쿠키만 되고 커스텀 헤더를 못 보낸다. 패턴은 아래처럼 손으로 프레임을 파싱한다.
  ```ts
  // useSSE — POST 로 SSE 를 열고 event/data 프레임을 수동 파싱. AbortController 로 취소.
  const res = await fetch(`${API_BASE}/agent/chat`, {   // 포털 릴레이면 절대경로 `/agent/chat`
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    credentials: "include",
    body: JSON.stringify({ message, system_id }),
    signal: controller.signal,
  });
  const reader = res.body!.getReader();
  const dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let i;                                   // "\n\n" 경계로 이벤트 프레임 분리
    while ((i = buf.indexOf("\n\n")) !== -1) {
      const frame = buf.slice(0, i); buf = buf.slice(i + 2);
      const ev = /event: (.*)/.exec(frame)?.[1];
      const data = JSON.parse(/data: (.*)/.exec(frame)?.[1] ?? "{}");
      onEvent(ev, data);                     // status→진행표시, token→append, result→렌더, error/done→종료
    }
  }
  ```
- **최소안이면 프론트만으로 끝.** 앱이 포털과 same-origin(`/<app>/`)이라 프론트가 절대경로 `/agent/chat`(포털 릴레이)로 바로 쏘면 세션쿠키+CSRF 가 그대로 실린다 — **앱 백엔드에 챗 코드가 없어도 된다**. 앱 도메인 데이터를 챗에 얹어야 할 때만 §4 앱 자체 릴레이로 확장한다.

---

## 4. 백엔드 / agent 지침

**앱이 직접 만지는 것은 얇은 릴레이 하나뿐이다.** vLLM·게이트웨이 설정은 앱이 건드리지 않는다(공용 인프라).

- **언제 앱 릴레이가 필요한가.** 순수 챗이면 포털 `/agent/chat` 재사용으로 충분(3장 최소안). **자기 도메인 데이터/컨텍스트를 붙여야** 하면(업로드 핸들, system_id, 워크스페이스 등) 앱이 `POST /<app>/api/agent/chat` 릴레이를 둔다.
- **앱 릴레이가 하는 일.** ① 세션 인증 + CSRF ② (필요시) 업로드/컨텍스트를 앱 스토어에 저장하고 참조를 만든다 ③ `{message, system_id, groups}` 를 `agent_server_url` 의 `/chat` 으로 POST ④ AgentServer 의 SSE 를 브라우저로 **byte-for-byte 중계**. 무거운 의존성(LangGraph 등)은 넣지 않는다 — 포털 `app/agent/routes.py` 릴레이가 참조 구현.
- **`agent_server_url`.** 릴레이가 바라볼 AgentServer 주소(기본 `http://127.0.0.1:9009`). 앱 config/env 로 잡고 하드코딩 금지. AgentServer `/chat` 는 body `{message, system_id?, groups?}` 를 받아 §5 SSE 를 낸다.
- **`mcp_servers.json`(gitignore) — 앱이 아니라 AgentServer 가 든다.** AgentServer 는 이 파일 하나(`MCP_CONFIG`)로 **게이트웨이 단일 엔트리**만 본다.
  ```json
  { "gateway": { "url": "http://127.0.0.1:9110/mcp", "transport": "streamable_http",
                 "headers": { "Authorization": "Bearer <GW_TOKEN>" } } }
  ```
  이 파일과 게이트웨이의 `gateway_config.json`(600, gitignore)은 **`HWAXMcpGateway/provision-config.sh` 가 자동 생성**한다 — GW_TOKEN 발급 + 백엔드 토큰(rat_/sfmcp_/mxwp_) 조달 + 두 파일 동시 작성. 앱은 손으로 토큰을 넣지 않는다.
- **vLLM 은 config/env 로만 잡는다(playbook §8 — 외부 인프라 설정 참조 원칙).** AgentServer 박스의 `.env` 에 `VLLM_BASE_URL`(OpenAI 호환 base) + `VLLM_MODEL`(served model name) 을 둔다. **라이브 엔드포인트를 테스트로 프로빙하지 말 것**(dev 박스의 포트는 무관한 서비스일 수 있어 오해 유발) · **주소·모델명 하드코딩 금지**.
  - dev/운영 전환은 **주소·모델명 스왑만** — 코드는 한 줄도 안 바뀐다.
  - **cae00(운영 박스) 테스트** — 상암 프로덕션 LLM 이 아직 없으니 dev 박스 vLLM 을 가리켜 검증한다. `VLLM_BASE_URL=http://192.168.1.100:8000/v1`, `VLLM_MODEL=qwen2.5-7b-dev`.
  - **상암 프로덕션 LLM 이 서면** 그 주소·모델명으로 `.env` 만 교체한다(박스별 `.env`, 코드 무변경).
- **포털 SSO `.env` 배포.** 앱의 포털 로그인 연동 블록은 `infra/env-kits/apply-envs.sh` 로 일괄 배포(없는 키만 추가 · 기존 값 보존). 게이트웨이/에이전트 시크릿(GW_TOKEN·서비스 토큰)은 별도로 `provision-config.sh` 담당.

---

## 5. 데이터 업로드 (챗으로)

원칙. **원본 데이터는 앱에 남기고, 챗에는 참조만 흐른다.** 에이전트/LLM 에 raw 바이트를 태우지 않는다 — 업로드는 앱 스토어에 저장하고, 그 핸들을 MCP 도구 인자로 넘겨 도구가 앱에서 다시 읽는다. 각 앱은 자기 도메인 데이터(리포트 · VOC · 데이터셋 · 문서)를 챗으로 받는다.

- **현 단계 최소안(코드 최소).** 사용자가 앱의 **기존 업로드 경로**로 파일을 올려둔 뒤 챗에서 "방금 올린 리포트 요약해줘"처럼 참조한다. 이미 등록된 앱 MCP 도구가 앱 스토어에서 그 데이터를 찾아 처리하므로, 챗 표면에는 업로드 코드가 없어도 된다.
- **확장안(챗 네이티브 첨부).** Composer 에 첨부 버튼 → `POST /<app>/api/uploads` 가 데이터를 앱 스토어에 저장하고 **핸들/ID 반환** → 그 핸들을 챗 메시지(또는 `system_id`/컨텍스트)에 실어 AgentServer 로 → 에이전트가 앱 MCP 도구를 그 핸들로 호출 → 도구가 앱에서 원본을 읽어 처리. 핸들만 오가므로 대용량/민감 데이터도 챗 밖에 머문다.
- **도메인 매핑(예시).** ReportArchive = 리포트 템플릿/문서 업로드 → 검색·요약 도구. SignalForge = VOC(고객의 소리) 데이터 → 조회·분석 도구. AIDataHub = 데이터셋 → 조회·집계 도구. MXWhitePaper = 문서(docx 등) → 작성·변환 도구.
- **감사.** 누가·언제·어떤 도구로·어떤 데이터에 접근했는지는 릴레이(감사 로그)와 게이트웨이(`audit.jsonl`)에 남는다 — 설계/규정 데이터 접근은 backfill 이 안 되므로 처음부터 남긴다.

---

## 6. 서브프로젝트 체크리스트 (순서대로)

1. **라우트 전환** — `/` = 풀스크린 챗, 카탈로그/설명 = `/apps`. → 검증. 포털 경유 `/<app>/` 첫 화면이 챗.
2. **서브패스 3종(§2)** — 빌드 `--base=/<app>/` · 라우터 `basename` 1줄 · `VITE_API_BASE_URL=/<app>`. → 검증. `/<app>/assets/<hashed>.js` 200 · 딥링크 새로고침 200.
3. **챗 UI + useSSE** — `fetch`+`ReadableStream`, CSRF 헤더, event/data 수동 파싱, AbortController. → 검증. status/token/result/done 이 화면에 순서대로.
4. **agent 배선** — 최소안은 프론트가 `/agent/chat`(포털 릴레이) 호출로 끝. 데이터 주입이 필요하면 `POST /<app>/api/agent/chat` 릴레이 추가(`agent_server_url` env). → 검증. `/agent/chat` 200 SSE.
5. **게이트웨이 등록** — 앱 MCP 서버를 게이트웨이 백엔드로 등록(`gateway_config.json`) 하고, 토큰 조달은 `provision-config.sh` 로 자동. `allowed_groups` 필요시 지정. → 검증. 게이트웨이 `/health` 의 tools 수에 앱 도구 반영.
6. **vLLM env(§8)** — AgentServer 박스 `.env` 의 `VLLM_BASE_URL`/`VLLM_MODEL`. cae00 테스트는 dev vLLM(`http://192.168.1.100:8000/v1`, `qwen2.5-7b-dev`). 하드코딩·프로빙 금지. → 검증. AgentServer `/health` 의 `vllm`/`model` 이 env 값과 일치.
7. **데이터 업로드 흐름(§5)** — 최소안(기존 업로드 참조) 또는 확장안(챗 첨부→핸들→도구). → 검증. 챗에서 올린 데이터로 도구가 실제 응답.
8. **포털 SSO `.env`** — `infra/env-kits/apply-envs.sh` 로 배포 후 앱 재기동. → 검증. 포털 타일에서 로그인 진입 성공.

---

## 7. 검증

포털(`:8088` nginx) 경유로 아래를 순서대로 통과시킨다.

```bash
P=http://127.0.0.1:8088

# (1) '/<app>/' 첫 화면이 챗 (SPA 200) · 에셋/딥링크 200
curl -s -o /dev/null -w "%{http_code}\n" $P/<app>/
curl -s -o /dev/null -w "%{http_code}\n" $P/<app>/assets/<hashed>.js
curl -s -o /dev/null -w "%{http_code}\n" $P/<app>/<deeplink>          # SPA fallback

# (2) /agent/chat 이 200 SSE 스트림 (echo 로 릴레이 경로부터 — Agent 없이도 확인)
curl -sN -X POST "$P/agent/chat?mode=echo" \
  -H 'Content-Type: application/json' -H "X-CSRF-Token: $CSRF" -b "$COOKIES" \
  -d '{"message":"핑","system_id":"<app>"}'
#   기대: event: status → token×N → event: result → event: done

# (3) 실제 릴레이 → MCP 도구 호출 (mode 없이): status 에 "도구 호출: <tool>" 이 뜨고 result 도착
curl -sN -X POST "$P/agent/chat" \
  -H 'Content-Type: application/json' -H "X-CSRF-Token: $CSRF" -b "$COOKIES" \
  -d '{"message":"<도구가 필요한 질문>","system_id":"<app>"}'

# (4) AgentServer / 게이트웨이 헬스 — 도구 수 · vLLM 주소·모델
curl -s http://127.0.0.1:9009/health    # {status, model, vllm, mcp:["gateway"], tool_scoping}
curl -s http://127.0.0.1:9110/health    # {status, tools, backends}
```

- [ ] 포털 경유 `/<app>/` 첫 화면 = 챗 · 에셋/딥링크 200 (§2 서브패스 OK)
- [ ] `/agent/chat` 200 `text/event-stream`, `status→token→result→done` 프레임 순서
- [ ] 실제 질문에서 MCP 도구 호출(`status: 도구 호출: …`) 후 `result` 도착 (게이트웨이 46개 도구 접근)
- [ ] 챗으로 올린 앱 데이터가 도구 응답에 반영(§5)
- [ ] **vLLM env 로 dev↔prod 전환** — `.env` 의 `VLLM_BASE_URL`/`VLLM_MODEL` 만 바꿔 재기동, `/health` 의 `vllm`/`model` 반영, 코드 무변경(§8)
- [ ] 다른 앱 라우트 무영향(`/`, 타 `/<id>/` 200)

---

## 8. 개인 토큰(PAT) 하나로 — 챗 + 개인 Claude MCP

세션 로그인 없이도, 발급받은 포털 PAT **하나**로 두 가지를 다 한다 — ① 포털 챗을 스크립트/외부에서 구동하고 ② 내 Claude(Desktop/Code)에 게이트웨이를 MCP 서버로 물린다.
같은 토큰, 같은 그룹 권한. 앱이 챗을 메인으로 올리는 것(§1~§7)과 별개로, **개인이 페더레이션 전체를 토큰 하나로 쓰는 접속면**이다.

### 8.1 개념 (토큰 1개 = 챗 + 내 Claude)

- **한 토큰, 두 표면.** 포털 PAT(RS256 서명 · `scope=api` · `aud` 에 `"mcp-gateway"` 포함)는 (a) 포털 챗 `/agent/chat` 을 `Authorization: Bearer <PAT>` 로 구동하고, (b) 개인 Claude 에 MCP 서버로 등록되어 게이트웨이 도구를 열어준다. 세션쿠키·CSRF 없이 동작하므로 스크립트·CI·외부 클라이언트에서 그대로 쓴다.
- **게이트웨이가 PAT 를 직접 받는다.** 게이트웨이 `/mcp` 는 내부 에이전트용 `GW_TOKEN` 외에 **포털 PAT 도 인증 주체로 인정**한다. PAT 로 들어오면 토큰 안의 `groups` 클레임으로 도구를 필터한다 — 헤더로 넘어온 `X-HWAX-Groups`(위조 가능)는 **버린다**. 즉 개인 접속은 토큰이 곧 권한이다.
- **접속 경로는 포털 오리진 경유.** 개인 Claude 가 바라볼 URL 은 게이트웨이 포트가 아니라 `<portal>/mcp-gw/mcp` — nginx 가 이 경로를 게이트웨이 `:9110/mcp` 로 **스트리밍 프록시**한다. 인증 헤더는 `Authorization: Bearer <PAT>`.
- **그룹만큼만 보인다.** 내부 에이전트 경로(§2 그룹 스코핑)와 동일하게, 안 보이는 도구는 LLM 이 존재조차 모른다(fail-closed). 개인 Claude 에도 내 그룹 교집합 도구만 노출된다.

### 8.2 발급 (포털 '토큰' 페이지 또는 curl)

- **페이지.** 포털 로그인 후 **'토큰' 페이지**에서 발급한다. `audiences` 에 **`mcp-gateway` 를 반드시 포함**해야 개인 Claude 등록이 동작한다(빠지면 게이트웨이가 aud 불일치로 거절).
- **curl(세션+CSRF).** 스크립트로 뽑을 땐 로그인 세션 쿠키 + CSRF 로 `POST /auth/pat`.
  ```bash
  PORTAL=http://127.0.0.1:8088
  # 세션 로그인 상태에서 PAT 발급 — audiences 에 mcp-gateway 필수
  curl -s -X POST "$PORTAL/auth/pat" \
    -H 'Content-Type: application/json' -H "X-CSRF-Token: $CSRF" -b "$COOKIES" \
    -d '{"scope":"api","audiences":["mcp-gateway"],"label":"my-claude"}'
  #   → { "token": "<PAT>", ... }  이 값을 아래 두 곳(개인 Claude · 챗 curl)에 그대로 쓴다
  ```

### 8.3 개인 Claude 등록 (Code / Desktop)

- **Claude Code(CLI).** MCP 서버 하나 추가 — transport 는 streamable-http, 헤더에 Bearer.
  ```bash
  claude mcp add --transport http hwax-gateway \
    "$PORTAL/mcp-gw/mcp" \
    --header "Authorization: Bearer <PAT>"
  ```
- **Claude Desktop(config JSON).** `claude_desktop_config.json` 의 `mcpServers` 에 게이트웨이를 등록.
  ```json
  {
    "mcpServers": {
      "hwax-gateway": {
        "type": "streamable-http",
        "url": "https://<portal>/mcp-gw/mcp",
        "headers": { "Authorization": "Bearer <PAT>" }
      }
    }
  }
  ```
- 등록 후 Claude 에서 게이트웨이 도구(그룹 권한만큼)가 바로 목록에 뜬다 — 별도 서버 설치·백엔드 토큰(rat_/sfmcp_/mxwp_) 조달 없이 포털 URL 하나로 끝(백엔드 토큰은 게이트웨이가 중앙에서 주입, §2).

### 8.4 챗 curl (세션 없이 Bearer 로)

- 같은 PAT 로 포털 챗도 그대로 스크립트에서 돌린다 — §7 검증의 세션+CSRF 대신 **`Authorization: Bearer <PAT>`** 하나면 된다.
  ```bash
  # 세션쿠키 없이 PAT 로 챗 SSE 구동 (외부/CI 에서도 동일)
  curl -sN -X POST "$PORTAL/agent/chat" \
    -H 'Content-Type: application/json' -H "Authorization: Bearer <PAT>" \
    -d '{"message":"<질문>","system_id":"<app>"}'
  #   기대: event: status → token×N → event: result → event: done  (§2 SSE 계약 동일)
  ```

### 8.5 보안 노트

- **그룹 권한만큼만.** PAT 는 발급자의 권한을 넘어서지 못한다 — 토큰의 `groups` 로 게이트웨이가 도구를 필터하므로, 내가 못 보는 도구는 개인 Claude 에서도 안 보인다. 권한 상승 경로가 없다.
- **위조 헤더 무시.** PAT 경로에서는 `X-HWAX-Groups` 를 신뢰하지 않는다(버린다). 권한 판단은 서명된 토큰 클레임에서만 나온다.
- **폐기 가능.** 유출·오용 시 '토큰' 페이지에서 해당 PAT 를 즉시 폐기(revoke)한다 — 세션 로그아웃과 무관하게 그 토큰만 죽는다. 발급 시 `label` 을 달면 어떤 토큰인지 식별해 개별 폐기가 쉽다.
- **aud 최소.** `audiences` 는 실제 쓸 대상만 담는다 — 개인 Claude+챗이면 `mcp-gateway` 하나로 충분하다. aud 를 넓게 잡을수록 유출 시 노출면이 커진다.
- **평문 보관 금지.** PAT 는 비밀번호급이다 — config 파일 권한(600)·시크릿 매니저에 두고, 레포·로그·공유 채널에 남기지 않는다.

---

*작성 기준 — HWAXAgentServer(:9009) · HWAXMcpGateway(:9110/mcp, GW_TOKEN·포털 PAT) · 포털 `app/agent/routes.py` 릴레이 · `/mcp-gw/mcp` PAT 개인 Claude 접속 실동작(2026-07). 서브패스/외부 인프라 상세는 `PORTAL-INTEGRATION-PLAYBOOK.md §2·§8`, 타일 연결은 `LINKED-SERVICES.md` 참조.*
