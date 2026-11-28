# 토큰 절감 2판 — 개인 Claude 의 일을 서버 Qwen · GLM 에 맡긴다(A ~ E, 하나씩 켜고 끈다)

> 1판 [PLAN.md](PLAN.md)(11-02 — 판정 · P1 ~ P9 · R1 ~ R8). 결정 [context-notes.md](context-notes.md) TS-6 ~. 할 일 [checklist.md](checklist.md) 「2판」.
> 사용자 요청(2026-11-24) — 「Claude MCP 를 쓸 때 일부 기능을 Qwen · GLM 으로 하면 토큰이 절약될 듯 — 방법을 제시해라」 → 제안 다섯 → 「진행해 줘 ·
> 이 옵션은 온오프가 되게」.

## 1. 왜

개인 Claude 의 토큰은 생각보다 **도구 결과가 Claude 문맥으로 그대로 들어오는 양**에서 나온다 — 도구 열 번이면 결과 열 개가 다 입력에 쌓이고, dev 감사에는
한 번에 50만 자가 나간 줄이 있다. 그래서 「결과를 Claude 대신 서버의 Qwen · GLM 이 읽게」 한다. 판단과 지휘는 Claude 가, 찾기 · 읽기 · 쓰기의 노동은 서버가.

## 2. 다섯과 스위치(모두 기본 꺼짐 — 끄면 바이트까지 지금과 같다)

| # | 무엇 | 도구(개인 Claude 가 부름) | 스위치 | 리포 |
|---|---|---|---|---|
| A | **위임** — 한 줄 과제를 서버 실행기(Qwen)가 그 사람 권한으로 도구 여러 번 불러 풀고, 답 · 근거 · 숫자 대조만 돌려준다 | `delegate_start` · `delegate_status(wait_s)` · `delegate_result(view)` · `delegate_cancel` | 에이전트 서버 `DELEGATE_ENABLED=1` | 에이전트 서버 |
| B | **결과 손잡이 + 결과에 묻기** — 큰 결과는 원문 대신 머리 + 손잡이(ref)만, 필요하면 쪽으로 받거나 서버에 묻는다 | `result_get(ref, page)` · `result_ask(ref, question)` | 게이트웨이 `GATEWAY_RESULT_REFS=1` **그리고** 연결 머리 `X-HWAX-Result: ref`(그 연결만 — TS-3) | 게이트웨이(+ 에이전트 서버 묻기 창구) |
| C | **긴 글 서버 작성** — 개요 + 근거 손잡이로 GLM 이 절 초안을 쓰고 숫자는 코드가 대조 | `draft_section` | 에이전트 서버 `DRAFT_ENABLED=1` | 에이전트 서버 |
| D | **단순 변환** — 번역 · 요약 · 표 바꾸기 · 용어 통일 | `llm_transform` | 에이전트 서버 `TRANSFORM_ENABLED=1` | 에이전트 서버 |
| E | **PC 킷 습관 묶음** — 위 도구를 기본으로 쓰게 하는 Claude Code 명령 · CLAUDE.md 규칙 · B 의 연결 머리 | (명령 `/hwax-ask` · `/hwax-draft`) | 토큰 화면 설정 배치의 선택 칸(기본 끔 — 다시 돌리면 걷는다) | 포털 |

- 스위치가 꺼져 있으면 A · C · D 도구는 **등록되지 않는다**(`tools/list` 에 없다 — 에이전트 서버 `_register_external` 과 같은 꼴). B 는 머리가 없는 연결 · 엔진
  (GW_TOKEN) · 웹 챗 · 절차 · 패널 · 루틴에는 늘 지금처럼 원문을 준다(TS-3).
- update-all 끝 요약 「있는데 안 켠 것」 에 넷이 ○ 로 뜬다(켜는 법 붙여) — 안 켠 기능도 로그에(메모리 규칙).

## 3. 계약(리포 사이)

### 3-1. A 위임(에이전트 서버 MCP)

- `delegate_start(task: str, apps?: [앱 키], max_steps?: int(기본 12 · 상한 30), max_minutes?: int(기본 10 · 상한 30))` → `{job_id}`. 심의 잡과 같은 잡 원장 ·
  줄 · 이어하기 · 취소 · 재기동 넘김을 쓴다(새 종류 `delegate`).
- 실행기 — 루틴 실행기의 단계 하나(작은 ReAct)와 같은 기계를 한 번 쓰는 꼴로. LLM 은 챗 LLM(stcx Qwen — 넘김 GLM). **울타리는 루틴과 같다 — 확인된 읽기 도구만**
  (`_routine_read`: readOnlyHint · 읽기 목록 · 박스 덧씌우기, 모르면 막는다). 쓰기 · 잡 제출 · 지우기는 못 한다 — 위임은 조사만 한다.
- 신원 — 그 MCP 호출을 한 사람(게이트웨이가 넘기는 사람 · 그룹 · 소속). 도구는 그 사람의 시야로만(루틴 · MCP 심의 잡과 같은 길). 리스크 심사 울타리(D-18)는 그대로.
- `delegate_result(view=full|summary)` → `{answer, evidence: [{tool, args, ref?, chars}], numbers: {checked, mismatched: [...]}, model, steps, tokens}`.
  숫자는 답의 수를 근거 원문과 코드로 대조한다(챗 자기검증 · `evidence.py` 재사용). 어긋나면 그대로 알린다 — 고쳐 쓰지 않는다.
- 동시 — `DELEGATE_MAX_RUNNING`(기본 2) · 사람마다 1. 심의 · 띵킹과 LLM 을 같이 쓴다 — 넘치면 줄.

### 3-2. B 결과 손잡이(게이트웨이)

- 켜는 조건 — 박스 `GATEWAY_RESULT_REFS=1` **그리고** 그 연결의 머리 `X-HWAX-Result: ref`. 둘 중 하나라도 없으면 지금 그대로.
- 결과 글이 `GATEWAY_RESULT_REF_MIN_CHARS`(기본 20,000)를 넘으면 — 원문(content 글 · structuredContent)을 **주인만** 보는 저장소에 두고(그림 보관소와 같은 꼴 ·
  기한 `GATEWAY_RESULT_REF_TTL_DAYS` 기본 7), Claude 에는 머리(앞 `…_HEAD_CHARS` 기본 4,000자) + `{ref, chars, sha256, pages, how}` 를 준다. structuredContent 도 같은
  꼴로 줄인다(Claude Code 가 그것을 받는다 — TS-3).
- `result_get(ref, page=1, page_chars=20000)` — 원문을 쪽으로. 주인이 아니면 거절.
- `result_ask(ref, question, max_answer_chars?)` — 게이트웨이가 원문을 에이전트 서버 묻기 창구에 넘긴다 → `{answer, quotes: [{page, start, end, text}], numbers, model,
  tokens}`(tokens 는 TS-16 — 창구 답을 칸을 고르지 않고 그대로).
- 에이전트 서버 묻기 창구 — `POST /llm/ask_over_text`(게이트웨이 서비스 자격 · 사람 이메일 머리) `{text, question, max_answer_chars}` → 위 꼴. 창이 모자라면 쪽마다
  읽고 모은다(리스크 20만 창과 같은 나눠 부르기). 인용은 원문 위치로 — 원문에 없는 인용은 버린다(코드 대조).
- 그림 · 큰 바이너리는 지금처럼 그림 보관소 ref 로 간다(이것과 따로).
- 지금의 응답 캐시 · 쓰기 뒤 비우기 · 감사(`chars` 는 원문 크기 그대로)는 바꾸지 않는다.
- **짓고 나서 정한 꼴(게이트웨이 `57212f4` — 11-24, TS-7)**
  - 머리로 청한 연결의 `tools/list` 는 `outputSchema` 를 뗀다 — 떼지 않으면 Claude Code(MCP TS SDK)가 줄인 structuredContent 를 출력 스키마로 검증해 거절한다.
    다른 연결의 목록은 그대로.
  - 줄인 꼴 — 글 블록은 앞머리 한 블록 + 손잡이 JSON 한 블록, structuredContent 는 `{ref, chars, sha256, pages, how, head}`.
  - 원문 = 글 블록을 줄바꿈으로 이은 것(structuredContent 의 촘촘한 JSON 이 더 길면 그것). chars · sha256 · 쪽 나누기가 이 글 기준.
  - `result_get` 답 — 첫 블록 `{ref, page, pages, page_chars, start, end, chars}`, 둘째 블록 그 쪽의 원문 글(JSON 이스케이프로 불지 않게).
  - `result_ask` 의 `quotes.page` 는 20,000자 단위(= `result_get` 기본 page_chars), start · end 는 원문 전체 자리.
  - 묻기 창구 호출 — `POST {hwax-deliberation 주소에서 /mcp 를 뗀 것}/llm/ask_over_text`, 머리 `Authorization: Bearer <GW_TOKEN>` · `x-hwax-user`(%-인코딩) ·
    있으면 `x-hwax-corr`. 404 는 「꺼짐 또는 낡은 판」 · 401 / 403 / 503 은 「공유 비밀 어긋남」.
  - 내부 ref 창구 — `GET <게이트웨이>/internal/result/<ref>`, 머리 `Authorization: Bearer <GW_TOKEN>`(정확히 한 번) · `x-hwax-user`. 200 `{ref, tool, chars,
    sha256, pages, created, expires, text, structured}` · 400 사람 머리 없음 · 401 · 404(없음 · 끝남 · 남의 것 — 같은 404) · 405. `X-Forwarded-*` 가 실린 요청은
    이 길을 타지 않는다(바깥 차단) — 포털 nginx 도 `/mcp-gw/internal` 을 404 로 막는다.
  - 도구 등록은 박스 스위치만 본다 — 켜면 머리 없는 연결 · 웹 챗 목록에도 두 도구가 보이지만, 그 연결에는 손잡이가 생기지 않아 불러도 「없다」 로 끝난다.
  - 같은 사람 · 같은 원문은 같은 ref. 실패 결과 · 신원 없는 호출 · 저장 실패 · `result_*` 자신은 원문 그대로. 계약 밖 손잡이 넷 — 자리 · 사람마다 1 GiB ·
    전체 10 GiB · 청소 주기(그림 보관소 꼴).

### 3-3. C 긴 글 · D 변환(에이전트 서버 MCP)

- `draft_section(outline: str, refs?: [B 의 ref | {tool, args}], style?: "report|memo|minutes|plain", target_chars?: int)` → `{draft, numbers, sources, model, tokens}`.
  LLM 은 GLM(긴 글 · 결정문과 같은 자리). `{tool, args}` 근거는 A 와 같은 읽기 울타리로 부른다. ref 는 게이트웨이 내부 창구(`GET /internal/result/{ref}` — 서비스
  자격 · 주인 이메일 대조)로 읽는다.
- `llm_transform(instruction: str, text?: str, ref?: str)` → `{text, ref?}` — 결과가 길면 B 저장소에 두고 ref 로 준다. LLM 은 챗 LLM.
- 둘 다 동기 호출(긴 것은 게이트웨이 호출 상한 안에서 — 넘으면 잡으로 돌리지 않고 거절하며 줄이라 알린다).

### 3-5. 짓고 나서 정한 꼴 — 에이전트 서버(`b0fd922` — 11-24, TS-8)

- A 재기동 — 줄 선 위임만 재기동을 넘긴다. 도는 위임은 `interrupted` 로 끝나고 이어 돌리지 않는다(읽기만 하는 일이라 다시 맡기면 된다).
- A 반환 — `delegate_start` → `{job_id, status, queue?, clamped?, max_steps, max_minutes, note}`. `delegate_result` 의 evidence 행은 `{id(답의 [eN]), tool, args, ok,
  chars}`(서비스 길이라 ref 는 생기지 않는다) · `notes` · `tokens {input, output}|null` · 기본 view full. `numbers` 는 `{checked, mismatched[≤30], mismatched_total?}`.
- A 신원 · 시야 — MCP 심의 잡과 같은 길(공유 비밀 + 신원 머리, 사람 PAT 없음). 신원 없는 호출은 여섯 도구 모두 거절. 위임 결과는 주인만(그 사람 시야로 읽은 발췌라
  같은 소속에도 열지 않는다). 위임은 심의 GLM 자리를 쓰지 않고 제 상한으로 줄을 선다 · 도는 수(`delib_active`)에는 든다.
- 울타리 — 루틴과 같은 `routine_read` 에서 이 서버 백엔드와 게이트웨이 로컬 도구를 뺀다. 웹 챗 · 심의 좌석(리스크 심사 포함) · 루틴은 여섯 도구를 묶지도
  invoke_tool 로 부르지도 못한다(`_OFFLOAD_TOOLS` — D-18).
- D `llm_transform` — `ref?` 반환은 뺐다. `{text, numbers, model, tokens, cut?}` · 20,000자에서 자른다(큰 결과의 ref 는 B 가 연결 머리로 붙인다).
- C `draft_section` 의 `sources` — `[{n, kind, ref | tool+args, chars, ok, error?}]` + `notes?`.
- 묻기 창구 — 사람 머리 없음은 400(403 은 게이트웨이가 「공유 비밀 어긋남」 으로 읽는다) · 모르는 칸 422 · 6쪽 넘음 413 · 540초 넘음 504 · LLM 실패 502.
- 읽기 전용 PAT 와 위임 — 이름 낱말로 `delegate_start` 는 쓰기 쪽으로 갈린다. **열지 않는다**(이 세션 판단 TS-8 — 읽기 전용 토큰이 서버 잡을 세우는 길을 새로
  만들지 않는다. 필요해지면 게이트웨이 읽기 목록에 이름 하나로 연다).
- 서버 LLM 토큰(TS-16) — 작성 · 변환 · 묻기 창구 답에도 위임과 같은 `tokens: {input, output} | null`(AI 메시지 usage 합 · 하나도 없으면 null). 묻기는 쪽마다 +
  모으기의 합이다.
- 사람별 LLM 사용량(TS-16) — 넷 모두 종류 `offload` 로 단다(에이전트 서버 `usage_tokens.KINDS` · 포털 `LLM_KINDS` · 화면 이름표 '서버에 맡긴 일'). 위임은 잡 원장이
  사람을 · 실행기가 종류를, 작성 · 변환 · 묻기는 그 함수 머리에서 사람 + 종류를 단다. 그 전 기록의 그 몫은 `other` 그대로다.
- 도구 영역 — 위임 넷은 `system`, `draft_section` · `llm_transform` 은 `report`(게이트웨이 `tool_areas.json`).

### 3-4. E PC 킷(포털)

- 토큰 화면 설정 배치에 선택 칸 「서버 LLM 에 일 맡기기(토큰 절약)」 — 켜면 ① MCP 등록에 `X-HWAX-Result: ref` 머리 ② Claude Code 사용자 명령 `/hwax-ask`(A 로
  맡기기) · `/hwax-draft`(C) ③ 사용자 CLAUDE.md 에 규칙 묶음(큰 결과는 ref 로 받고 묻기 · 조사는 위임 · 긴 글은 draft). 끄고 다시 돌리면 셋을 걷는다(표지 줄 사이만).
  - **11-28 바뀜(사용자 결정 — HWAXPortal docs/request-1125 P-1)** — ① 의 머리는 칸과 상관없이 늘 단다(박스 `GATEWAY_RESULT_REFS` 가 꺼져 있으면 아무 일도 없다).
    칸은 ② · ③ 만 넣고 걷는다.
- 박스에 그 기능이 꺼져 있으면 칸을 보이되 「이 박스에서 꺼져 있음」 으로 둔다(포털이 에이전트 서버 · 게이트웨이 `/health` 의 표지를 읽는다).

## 4. 지키는 것

- 모든 스위치 기본 꺼짐 · 끄면 지금과 같은 바이트. E 만 예외 — 칸을 켠 적 없는 PC 의 화면 출력이 같고, 배치는 걷기만 더한다(끄고 다시 돌리면 걷어야 해서 — TS-10).
- B 의 박스 스위치는 게이트웨이 곁 `provision.env` 한 줄로 둔다(환경이 먼저 — TS-9).
- 서버는 그 사람의 시야로만 · 쓰기 없음(A) · 리스크 심사 울타리 그대로.
- 숫자는 코드가 원문과 대조하고, 어긋나면 표시한다(고쳐 쓰지 않는다).
- 원문 손잡이는 주인만 · 기한 뒤 지움. 감사에는 원문 크기 그대로.
- 상호작용 데이터 원장(`../interaction-data/`)이 생기면 위임 · 묻기 · 작성도 사건으로 남는다(같은 corr).

## 5. 차례

1. 계약(이 문서) — 세 리포 작업자가 같이 읽는다.
2. 에이전트 서버(A · C · D · 묻기 창구) ∥ 게이트웨이(B · 내부 ref 창구) ∥ 포털(E · update-all ○ 줄 · 문서) — 가지에서.
3. 합치기 — 게이트웨이 → 에이전트 서버 → 포털, 리포마다 전체 회귀. dev 에서 스위치를 켜 실제 한 번씩(위임 · ref · 묻기 · 작성 · 변환).
4. 받은 편지함 — cae00 은 켜는 법만(켤지는 사람).
