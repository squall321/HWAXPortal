# 과제 인사이트 그래프 — M2 · M2b 계약(11-02)

계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md)(M2 는 PG-28 부터) · 할 일 [checklist.md](checklist.md). 이 문서는 에이전트 서버 ·
포털 · 게이트웨이 · 리스크 앱이 함께 지키는 꼴이다. 칸 이름 · 꼴은 M2 를 짓기 전에 실물(에이전트 `0e63a65` · 포털 `32bd8784` · 게이트웨이
`6dc4abc` · 리스크 앱 `d30bef6`)에 대고 맞췄다. 정본은 코드의 상수이고, 리포를 가로지르는 칸은 시험이 서로의 원문을 맞댄다.

## 0. 한눈에

```
엔진(단마다 카드 거리 — 새 LLM 호출 0, 주제가 confirmed · claimed 이고 리스크 심사 계열이 아닐 때만)
  └ delib{kind:"insight"} 사건
      ├ 웹 심의 → 포털 중계가 받아 답을 남길 때 원장에 들인다(ins:web:…)
      └ MCP 잡  → 잡 원장 job.insights[단] → GET /insights/cards(공유 비밀) → 포털이 읽을 때 당겨 들인다(ins:delib:…)
Claude 워크플로(hwax-deliberate.js) → save_conversation(subject · chair_template) → 포털 ConvCreate 가 저장 뒤 들인다(ins:wf:…)
포털 원장(procedures.sqlite 의 insight_* 표) → /insights-api(읽을 때 거름) → 화면 '과제 인사이트' · 게이트웨이 insight_find · insight_get
리스크 앱(정본 그대로) → risk_find_projects_by_subject(그 사람 신원) → 포털 과제 보기가 같은 (과제, 차수) 칸에 싣는다
```

리스크 심사가 낳은 심의(의장 `risk-review*` · `started_by=app` · 대화 kind `risk-review`)는 어느 길로도 원장에 들지 않는다 — 엔진이 카드 거리를 짓지
않고(§1), 에이전트 창구가 빼고(§3), 포털 들이기가 한 번 더 뺀다(§5).

## 1. 카드 거리 — 엔진 사건 `delib{kind:"insight"}`

- **언제** — 단의 끝(결정문 · outcome 사건 뒤)에 한 번. 셋이 다 맞을 때만 낸다.
  1. 이 심의가 무장했다(`deliberation.INSIGHT_ARM` 문맥 변수가 참). 무장은 주제가 있을 때만 한다 — MCP 잡은 잡 원장의 `subject.sp_state` 가
     `confirmed` · `claimed` 이고 리스크 심사 계열이 아닐 때 `delib_jobs._make_spawn` 이 그 태스크 문맥에 건다(줄 · 재기동 다시 세우기 ·
     제자리 이어하기 모두 이 자리를 지난다). 웹은 `app._with_delib_images` 가 에이전트가 확인한 주제(같은 두 상태)를 받았을 때 엔진 앞에서 건다.
     `none` 은 무장하지 않는다(PLAN §3.4 — 과제 대상이 아닌 질문은 카드가 없다).
  2. 의장이 결정문을 냈다(`_chair_failed` 가 비었다).
  3. 엔진은 주제를 모른다 — 무장 표지 하나만 본다(PG-21 — 엔진이 주제를 결정문 · RA 보고서 · 위키 원천으로 옮기는 길은 없다). **예외는 사람이 고른
     근거다**(11-02 사용자 결정 — docs/ontology-first OF-14 ③) — 심의 전 '온톨로지 먼저 보기'(포털 미리보기)에서 사람이 고른 행은 호출자 근거
     (`opts.evidence`)로 들어가, 그 과제 key · 이름이 결정문의 근거 목록 · [e:N] 과 RA 보고서에 실린다. 그 심의마다 사람이 고른 만큼이고 엔진은 그것이
     주제인 줄 모른다. 이 근거는 `tool` 이 있어 아래 `calls` 에 호출자 근거로 들고, 그 `sha256` 은 포털이 줄인 행의 지문이다(도구 원문이 아니다).
- **칸**(모두 늘 싣는다 — 모르면 빈 값).

| 칸 | 꼴 | 규칙 |
|---|---|---|
| `stage` | 글 | 그 단의 의장 틀(`opts.chair_template`, 비면 `default`) — 다단 심의는 단마다 다르다(mechanism · sim-plan · build-plan · test-plan) |
| `claim` | 글 ≤ 500자 | 결정문의 '■ 핵심 요약' 불릿(엔진이 이미 지은 줄 — 빈 줄 · 머리 없이 줄마다), 없으면 '■ 쉬운 설명' 의 '### 한마디로' 첫 줄, 둘 다 없으면 빈 글. 500자를 넘으면 줄 경계에서 자르고 `…` |
| `claim_from` | `summary` · `plain` · `""` | 위에서 무엇을 썼나 |
| `tally` | `{agree, conditional, oppose, abstain}` | outcome 사건의 집계와 같은 값(착석 수 분모) |
| `report_id` · `report_url` | 정수 · 글 · null | 그 단의 RA 보고서(없으면 null) |
| `model` | 글 | 답한 모델 이름(`llm.model_name` · `llm.model`, 외부 응답자는 `external`) |
| `calls` | `[{ref, tool, app, args, sha256, ok}]` ≤ 60 | 근거 표지 — 좌석 자유 조회(gather_pool) · 호출자 근거(`opts.evidence` 의 `tool` 이 있는 항목) · 지정 도구. `ref = "call:" + sha256(tool · args · 결과 sha256)[:16]`, `args` 는 1,200자까지(엔진 인자 표기 상한), `sha256` 은 엔진이 쥔 결과 글의 지문 — 지정 도구 · 호출자 근거는 받은 글, 좌석 자유 조회는 공용 풀에 실린 몫(좁은 창에서는 앞부분 — 다른 좌석이 본 글)이라 원문 전체의 지문이 아닐 수 있다(앞부분이 같은 두 결과는 표지 하나로 접힌다 — 반대 검토 11-02). `ok` 는 `_delib_tool_result_ok`. 같은 (도구, 인자, 결과)는 하나. 제자리 이어하기는 지정 도구를 다시 부르지 않으므로 그 표지를 재개 자료 `e:pre.ins_calls` 에서 되살린다 |
| `tools` | 글 목록 | 이 단의 근거에 든 도구 이름 전부 — 위 셋 + 엔진 안의 근거(VOC 환기 · 정량 근거 선주입 · 지식카드 `agent_search`) + 같은 심의의 앞 걸음이 넘긴 것(아래 잇기). 제자리 이어하기는 라운드 전 몫을 재개 자료 `e:pre.ins_tools` 에서 되살린다 |
| `apps` · `apps_unknown` | 글 목록 · 글 목록 | `tools` 의 게이트웨이 백엔드 키(`/tools-map` — 엔진의 `_app_of_tools`, 게이트웨이 자체 도구는 `_gateway`)와 앱을 모르는 도구 이름(지도를 못 받은 때는 전부 — 포털이 확인할 때 다시 푼다, §6.2) |
| `untracked` | 글 목록(차례 고정) | 근거 표지가 없어 범위를 모르는 입력 — `evidence`(도구 없는 호출자 근거 글 · 그림 판독문) · `note`(호출자의 사람 의견 — 챗이 넘긴 보강 글일 수 있다) · `summary`(호출자가 준 앞 회차 요약) · `images`(그림 조각) + 앞 걸음이 넘긴 것. 단 준비가 채운 의견 칸(시험 설계 지시문 · 현황 글)과 다단 심의가 넘긴 앞 단 결정문은 넣지 않는다 — 그 범위는 잇기로 간다 |
| `refs` | 글 목록 | `rpt:<report_id>`(있으면) + `calls[].ref` |

- **잇기**(`deliberation.INSIGHT_CARRY` — 무장하는 쪽이 `{tools, untracked}` 를 건다) — 같은 심의 안의 뒤 단은 앞 단의 결정문에 기대므로 카드를 낼 때마다
  그 카드의 `tools` · `untracked` 를 쌓아 뒤 단 카드에 담는다. 단 준비가 사람 의견 칸에 붙이는 현황 글(시험 설계의 물성 근거 현황 · 해석 설계 2단의
  사내 자산 현황)을 지은 도구도 그 단의 `tools` 다(`_snap_with_tools` — 그 await 동안만 `_call` 이 이름을 적는다). 제자리 이어하기는 단에 들 때의
  재개 자료(`e:stage_in.carry`)와 단 경계 체크포인트(`checkpoint.carry`)로 되살린다(PLAN §6.2 최소 범위).

- 새 LLM 호출은 없다. 시험이 지키는 것 — 무장하지 않은 심의(주제 없음 · 리스크 심사)의 사건 꼴은 종전과 바이트까지 같다.

## 2. MCP 잡 원장

- `delib_jobs._apply` 가 `delib{kind:"insight"}` 를 `job["insights"][stage]` 로 둔다(사전 — 같은 단을 다시 내면 덮는다. 제자리 이어하기가 끝난 단을
  다시 내도 하나다). 사건에 `kind` 칸은 빼고 둔다.
- 이어하기 — `deliberate_continue` 의 보통 길이 새 잡에 `continues = <앞 잡 id>` 를 적는다(종전엔 응답의 `continued_from` 에만 있었다). 끊긴 잡의
  요약 이어하기는 이미 `resumed_from` 을 적는다. 창구(§3)는 `continues || resumed_from` 을 낸다.

## 3. 에이전트 서버 창구

### 3.1 `GET /insights/cards?since=<epoch 초>&limit=<1 ~ 500, 기본 200>` — 끝난 MCP 잡의 카드 거리

- 인증 — `Authorization: Bearer <GW_TOKEN>`(게이트웨이 연결의 값, 포털 `GATEWAY_SHARED_TOKEN` 과 같다 — `seat_box.authorized`, `/seat-questions` 와
  같은 꼴). 비밀이 없는 박스는 503, 다르면 401. 루프백만 믿지 않는 까닭 — 결정문 요약 · 근거 인자를 낸다.
- 고르는 잡 — `finished_at >= since` · 상태 `done` · `error`(다단 심의의 끝난 앞 단은 결정문이 있다) · 주인 `user` 를 푼 꼴(퍼센트 인코딩을 풀어
  소문자 — `_norm`)에 `@` 가 있다(주인 빈 잡은 내지 않는다, 답의 `user` 는 원문 그대로) · `subject.sp_state ∈ {confirmed, claimed}` · 리스크 심사 계열이 아니다(잡의 `chair_template` · `started_by`, 카드의 `stage` 도 본다) ·
  카드 거리가 하나 이상. 원장 파일은 mtime 으로 먼저 거르고(끝 쓰기가 `finished_at` 보다 앞서지 않는다) 메모리 원장도 본다.
- 답 — `{"contract": "insight-cards/1", "items": [...], "next_since": <float>, "complete": <bool>}`. 항목은
  `{job_id, job, user, owner_aff, chair_template, started_by, status, finished_at, continues, subject, cards: [카드 거리...]}` 이고 `finished_at`
  오름차순이다. `next_since` 는 낸 항목의 가장 늦은 `finished_at`(없으면 받은 `since`), `complete` 는 상한에 걸리지 않았는가. 경계(같은 시각)는
  다음 부름에 다시 나올 수 있다 — 받는 쪽이 id 로 하나로 만든다.
- `owner_aff` 는 그때 게이트웨이가 실은 값이다 — 포털은 넓힐 때 쓰지 않는다(§6.2 — 자칭 소속이 소속 전체에 퍼지지 않게).

### 3.2 `POST /deliberate/subject/confirm` — 주제 다시 풀기(포털 몫 둘)

- 본문 `{subject: {sp_task, round, text, artifacts}, groups: [...], user_email, user_pat, chair_template?, started_by?}`. 인증은 `/chat` 과 같은 루프백
  신뢰에 **사람 PAT 가 반드시 있다**(`user_pat` 이 비면 422 — 공유 비밀 + 신원 머리로 남의 이름을 풀지 않는다).
- 답 — 200 `{"subject": <delib_subject.confirm 의 기록 | null(빈 주제)>}`, 꼴이 틀리면 422 `{"code": "bad_request", "message"}`, 리스크 심사 계열이면
  422 `{"code": "risk_family"}`. 확인 규칙은 M1 의 `delib_subject.confirm` 하나다(PG-19 — 확인하는 쪽은 에이전트 서버 하나).
- 쓰는 곳 — 포털의 워크플로 대화 들이기(§5.3)와 기다림 줄의 주제 확인(§6.3).

## 4. 포털 원장 — `procedures.sqlite` 안의 표(새 경로 없음)

절차 저장소의 연결을 같이 쓴다(분석 루틴과 같은 자리 — 설정 · 백업 · 기동 · 시험 격리에 이미 등록됐다).

```sql
CREATE TABLE IF NOT EXISTS insight_cards (
  id TEXT PRIMARY KEY,            -- ins:delib:<job_id>:<단> · ins:web:<대화 id>:<실행 id>:<단> · ins:wf:<대화 id>
  path TEXT NOT NULL,             -- web | mcp-job | mcp-workflow
  source_id TEXT NOT NULL,        -- 잡 id · 대화 id
  stage TEXT NOT NULL,            -- 의장 틀
  owner_email TEXT NOT NULL,      -- 소문자. MCP 잡은 잡 원장의 user(자칭 — 주인이 포털에서 확인할 때까지 주인만 본다)
  owner_sub TEXT,                 -- 포털 subject(웹 · 워크플로는 들일 때, MCP 는 주인이 처음 손댈 때)
  status TEXT NOT NULL,           -- waiting | draft | confirmed | disputed | withdrawn
  sp_task TEXT,                   -- 확인된 key 만(waiting 은 NULL — 주장한 key 는 subject_json 에)
  round TEXT,                     -- 차수 코드(열하나) · NULL = 차수 모름
  round_by TEXT,                  -- person · NULL
  subject_json TEXT NOT NULL,     -- 에이전트가 확인한 주제 기록 그대로(sp_state · sp_resolved_by · sp_why · text · artifacts)
  claim TEXT NOT NULL, claim_from TEXT NOT NULL, claim_edited_by TEXT, claim_edited_at INTEGER,
  card_json TEXT NOT NULL,        -- tally · report_id · report_url · model · calls · tools · apps · apps_unknown · untracked · refs
  scope_json TEXT NOT NULL,       -- 범위 토큰 목록(§6.1)
  scope_note TEXT,                -- 넓히기가 멈춘 까닭
  continues TEXT,                 -- 앞 카드 id(그 카드가 원장에 있을 때) 또는 delib:<앞 잡 id>
  created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL,
  confirmed_at INTEGER, confirmed_by TEXT, withdrawn_at INTEGER, withdrawn_by TEXT)
CREATE TABLE IF NOT EXISTS insight_links (from_id TEXT, to_id TEXT, kind TEXT, by_email TEXT, note TEXT, at INTEGER,
  PRIMARY KEY (from_id, to_id, kind))       -- kind = disputes(from 이 to 를 반박한다)
CREATE TABLE IF NOT EXISTS insight_meta (k TEXT PRIMARY KEY, v TEXT)   -- jobs_since(MCP 잡 당기기의 커서) · jobs_partial(앞 당기기가 쪽 상한에서 멈췄나)
```

- **멱등** — 같은 id 는 하나다(`INSERT OR IGNORE`). 거둔 카드는 내용을 지운 묘비(id · 주인 · 거둔 사람 · 때)로 남아 다시 들여도 되살지 않는다.
- **카드는 확인된 주제만** — `sp_state=confirmed` 는 `draft`, `claimed` 는 `waiting`(주인의 기다림 줄 — 어느 과제 보기에도 없다), `none` 은 들이지 않는다.

## 5. 들이기 셋

| 길 | 자리 | id | 주인 | 주제 |
|---|---|---|---|---|
| 웹 | `/agent/chat` 중계가 답을 남길 때(`_save`) — 대화와 실행 id 가 있을 때만 | `ins:web:<cid>:<run_key>:<단>` | 포털 principal | 중계가 받은 `delib{kind:"subject"}`(에이전트가 확인한 값) |
| MCP 잡 | 읽기 창구가 불릴 때 당긴다(`INSIGHT_SYNC_S` 초에 한 번 · 0 이면 끔 · 기본 60) — 커서 `jobs_since` 에서 600초 겹쳐 읽고 쪽을 넘긴다(다섯 쪽 × 200). 쪽 상한에서 멈추면(`jobs_partial`) 다음 당기기는 겹침 없이 커서부터 잇는다 — 겹침 창이 빽빽해도 커서가 넘어간다 | `ins:delib:<job_id>:<단>` | 잡 원장의 `user`(자칭) | 잡 원장의 `subject` |
| Claude 워크플로 | `POST /agent/conversations`(ConvCreate)가 저장한 **뒤** — 실패해도 저장은 그대로다 | `ins:wf:<cid>` | 포털 principal(게이트웨이가 넘긴 사람 PAT 의 sub) | 받은 `subject` 를 그 사람 PAT 로 다시 푼다(§3.2) |

- **리스크 심사 계열은 빼는 겹** — 웹은 `delib_opts.chair_template` 이 `risk-review` 로 시작하거나 `started_by=app` 이면(리스크 러너 패널은 대화 kind 를
  `deliberation` 으로 만든다 — HWAXRisk `engine_client.CONVERSATION_KIND`), MCP 잡은 항목 · 카드의 의장 틀 · `started_by`, 워크플로는 `chair_template` 이
  그 계열이거나 대화 kind 가 `risk-review` 면 들이지 않는다.
- **워크플로 카드의 주장** — 저장된 assistant 메시지를 이어(머리 `(결정문 i/N)` · `(긴 발언 나눔 k/N)` 를 떼고) §1 과 같은 규칙으로 뽑는다 —
  워크플로 결정문에는 '■ 핵심 요약' 이 없어 '■ 쉬운 설명' 의 '### 한마디로' 줄이 된다. 근거 도구를 모르므로 `apps_unknown = ["(workflow)"]` 이다.
- **ConvCreate 의 새 칸 둘** — `subject: dict | null`(꼴은 들일 때 에이전트가 본다 — 꼴이 틀려도 저장을 422 로 떨어뜨리지 않는다. 20,000자를 넘는 JSON
  은 받지 않고 버린다), `chair_template: str | null`(`^[a-z0-9-]{1,40}$` 가 아니면 버린다). 답에 `insight: {id, status} | {skipped: <까닭>}` 을 싣는다.
- **PLAN §4.7 (b) 의 '첫 사용자 메시지 meta' 는 쓰지 않는다** — 워크플로의 주제는 원장의 카드 · 기다림 줄에만 산다(PG-28).

## 6. 시야 · 쓰기 — `/insights-api`(권한 `feat:insights`)

### 6.1 범위 토큰과 읽을 때 거름

- 토큰 — `user:<메일>` · `aff:<소속>` · `plat:<플랫폼>` · `org` 의 그리고(AND). 초안 · 기다림의 범위는 `[user:<주인>]` 이다.
- 카드가 읽는 사람 R 에게 보이는 때 — 거둔 것이 아니고, ① R 이 주인(메일 소문자 일치)이거나 ② 상태가 `confirmed` · `disputed` 이고 토큰을 다 만족하거나
  (`aff:` 는 R 의 **지금 포털 원장 소속**, `plat:` 은 R 의 지금 권한 그룹, `user:` 는 R 의 메일) ③ R 이 관리자다(범위 밖 읽기는 감사 한 줄
  `insight_admin_read`). 신원 없는 호출은 아무것도 못 본다(창구가 세션 · PAT 를 요구한다).
- 수 · 잇기(반박 · `continues`)는 보이는 것만 센다 — 보이지 않는 카드는 있다는 것도 말하지 않는다. 반박 줄은 늘 싣되 반박한 카드가 안 보이면 `by` 만
  가린다(카드 없이 단 반박과 같은 꼴 — 줄을 빼면 상태만 '반박' 이라 숨은 카드가 있다고 말하는 셈이다).
- 읽는 창 — 한 번에 최근 2,000장(`store.ROWS_MAX`)이고 관리자가 아니면 그 사람의 것과 공유 상태(확인 · 반박)만 센다(남의 초안이 창을 채워 보이는
  카드가 밀려나지 않게). 창이 차면 답에 `truncated: true` · `note_rows`('최근 N장만 봤다')를 싣는다. 관리자가 잇기(앞 카드 · 반박 끝)로 범위 밖 카드의
  id 를 보는 것도 감사 한 줄에 든다.

### 6.2 확인과 넓히기

- **확인**(`draft → confirmed`, 주인만 · 세션 + CSRF) — 범위를 `[aff:<주인의 지금 소속>] + plat 토큰` 으로 바꾼다. plat 토큰은 카드 `apps` 를 포털 권한표로
  풀어 `plat:` 키만 단다(`Policy.keys_for_gateway` — 표에 없는 백엔드 · `_gateway` 는 토큰이 없다). 앱을 몰랐던 도구(`apps_unknown` — 괄호 표지
  `(workflow)` 는 빼고)는 그때 게이트웨이 `/tools-map` 으로 다시 풀어 카드에 적는다 — 지도를 못 받으면 503 이고 초안 그대로다(엔진이 지도를 못 받은 때
  지은 카드가 plat 토큰 없이 열리지 않게). 주인에게 소속이 없으면 `[user:<주인>]` 그대로 `confirmed` 이고 `scope_note` 에 까닭을 단다. MCP 잡의
  `owner_aff` 는 쓰지 않는다. 여전히 앱을 모르는 도구 · 범위를 모르는 입력(`untracked`)이 있으면 같은 소속까지이고 까닭을 단다(PLAN §6.2 '한 칸 다른
  자리'). **앞선 인사이트를 근거로 쓴 카드**(`tools` · `calls` 에 `insight_*`)는 원래 카드들의 범위를 이어받는 규칙(M3)이 서기 전까지 확인해도
  `[user:<주인>]` 이고 까닭을 단다 — `insight_*` 는 `_gateway` 라 plat 토큰이 없어, 이어받지 않으면 plat 권한 카드의 결론이 그 권한 없는 같은 소속에
  열린다(반대 검토 11-02).
- **조직 공개**(`confirmed → org`) — 근거 범위를 다 알 때만이다. 이 판에서는 근거 표지(`calls` · `tools`)가 없고 `apps_unknown` · `untracked` 가 비고
  워크플로가 아닌 카드뿐이다(남의 RA 보고서 · 리포트 같은 근거의 범위를 모른다). 아니면 409 와 까닭. `plat:` 빼기는 짓지 않았다(관리자 몫 — 나중).
- **그 밖의 쓰기**(세션 + CSRF) — 차수 달기(코드 · `unknown`, 둘 다 `round_by=person` — 고른 '모름' 도 사람의 것이라 주제 확인이 되돌리지 않는다),
  주장 고치기(500자, 고친 사람 · 때), 반박 표시(주인 · 관리자 — `disputed` 와 반박한 카드 링크), 거두기(주인 · 관리자 — 묘비, 기다림 줄 카드 포함),
  기다림 줄의 주제 확인(§6.3 — 사람이 단 차수를 지킨다). PAT 로는 쓰지 못한다(사람이 화면에서 한다).

### 6.3 창구

| 메서드 · 경로 | 무엇 |
|---|---|
| `GET /insights-api/health` | 무인증 `{ok, contract: "insights/1"}` |
| `GET /insights-api/projects?q=` | 보이는 과제 목록 — `[{sp_task, rounds: {<코드 · unknown>: n}, total, latest_at, risk: n}]`(리스크 앱 과제 수 포함 · 못 읽으면 `risk_error`) |
| `GET /insights-api/project?sp_task=&round=` | 한 과제 — 차수 칸마다(`rounds: [{round, cards, risk}]`, 차수 모름은 `round: null` 칸) 일반 심의 카드와 리스크 행 |
| `GET /insights-api/mine` | 내 카드 — `waiting` · `draft` · 그 밖 |
| `GET /insights-api/find?sp_task=&round=&q=&artifact_kind=&artifact_id=&limit=` | 게이트웨이 `insight_find` 의 몸 — 보이는 카드의 짧은 행 |
| `GET /insights-api/cards/{id}` | 카드 하나(못 보면 없는 것과 같은 404) |
| `POST /insights-api/cards/{id}/confirm` · `/round` · `/claim` · `/widen` · `/dispute` · `/withdraw` · `/subject` | 위 쓰기(세션 + CSRF) |

읽기는 세션 또는 사람 PAT(게이트웨이가 넘긴 호출자 PAT)를 받는다.

## 7. 게이트웨이 도구

- `insight_find(sp_task?, round?, q?, artifact_kind?, artifact_id?, limit?)` · `insight_get(id)` — 포털 `/insights-api/find` · `/cards/{id}` 를 **호출자
  사람 PAT 로만** 부른다(루틴 도구와 같은 `_caller_bearer` — 게이트웨이 공유 비밀이나 신원 없는 호출은 거절). 낡은 포털이면 '낡았다' 로 말한다.
  읽기 전용 토큰도 부른다(`_LOCAL_READ`). 결과의 머리 표지 — '앞선 인사이트 — 검증 대상, 독립 근거 아님'. 리스크 행은 `risk_find_projects_by_subject` 가 맡는다.
- `save_conversation` — 받는 칸에 `subject`(객체 · 칸은 `sp_task` · `round` · `text` · `artifacts` 넷만, 그 밖이 있거나 꼴이 아니면 버리고 답의
  `subject_dropped` 에 까닭) · `chair_template`(`^[a-z0-9-]{1,40}$` 만)을 더해 포털 ConvCreate 에 그대로 넘긴다. 그 밖의 칸은 지금처럼 버린다.

## 8. D-18 — 새 도구는 리스크 심사 좌석에 닿지 않는다

- 엔진 `_risk_designated_refusal` — 이름이 `insight_` 로 시작하면 갈래 `insight`(리스크 심사의 지정 도구로 부르지 않는다).
- 자유 조회 후보 — 리스크 심사(`chair_template == "risk-review"`)면 `insight_*` 를 접두 허용 · 유지 목록과 상관없이 뺀다. 외부 응답자의 CALL 줄은 그 후보
  안에서만 실행되므로 같이 닫힌다.
- 리스크 앱의 새 읽기 도구 `risk_find_projects_by_subject` 는 `risk_` 로 시작해 지정 도구 갈래 `app`(변경 · 스냅샷 밖의 리스크 앱 도구)으로 닫히고,
  자유 조회 접두(`_FREE_ALLOW`)에 걸리지 않는다 — 시험이 이름으로 지킨다.
- Claude 워크플로의 리스크 심사 좌석(`hwax-deliberate.js` — 그 사람 PAT 의 게이트웨이 도구를 다 쓴다)은 좌석 프롬프트의 D-18 줄(`D18_LINE`)이
  `insight_find` · `insight_get` · `risk_find_projects_by_subject` 를 이름으로 막는다(반대 검토 11-02).

## 9. 리스크 앱(M2b)

- **v6** — `ALTER TABLE rr_projects ADD COLUMN sp_task TEXT` · `CREATE INDEX IF NOT EXISTS ix_rr_projects_sp_task ON rr_projects(sp_task)`(허용 연산 —
  `risk_store.py` 의 `MIGRATIONS`). 나간 판(v1 ~ v5)은 고치지 않는다.
- **차수** — 새 칸 없이 `stage` 다. 읽을 때 `round = norm(stage)`(NFKC · 유니코드 White_Space 빼기 · 소문자 뒤 열한 코드에 있을 때만, 아니면 null —
  에이전트 `delib_subject.norm_round` 와 같은 규칙, 시험이 견준다). 과제 만들기(`POST /projects` · `risk_create_project`)의 `stage` 는 종전대로 글이다 —
  거르면 리스크 앱 웹 폼의 `dv` · `pre1` 이 422 가 된다(PG-33). 코드로 적는 길은 아래 쓰기다.
- **쓰기** — `PUT /api/projects/{id}/sp-subject {sp_task: str | null, round?: str | null}` 와 같은 함수의 MCP `risk_set_project_subject(project_id,
  sp_task, round?)`. 과제 주인 · 편집자만(관리자는 편집자 — 쓰기 문 `_project_writer`, 보기 역할은 403 · 남 · 없는 과제는 같은 404 · 폐기된 과제는 409
  `project_purged`). ECAD 보드 붙이기는 주인만인데 이 칸은 계약대로 편집자에게도 열었다 — 풀이는 편집자 **자신의** PAT 로 돈다. `sp_task` 는 리스크 앱이
  **그 사람의 등록된 포털 PAT**(ECAD 보드 붙이기와 같은 자격 — 판정을 `_person_pat` 하나로 뗐다, 박스 PAT 로 내려가지 않는다 · 없으면 409 `sp_pat_absent`
  이고 게이트웨이에 아무것도 보내지 않는다)로 게이트웨이 별칭 `heaxstep_forge_find_plm_task({query: sp_task, limit: 50, full: true})` 를 스스로 불러(기한 20초),
  결과 행 `tasks[]` 가운데 `key` 가 글자 그대로 같고 `active` 가 거짓이 아닌 행이 꼭 하나일 때만 적는다(에이전트 `delib_subject.confirm` 과 같은 규칙 —
  같은 key 가 둘이면 하나가 비활성이어도 고르지 않는다 · 아니면 422 `sp_task_not_confirmed` 와 까닭, 결과 행의 key 는 싣지 않는다). `null` 은 풀이 없이
  뗀다 · 빈 글은 422 `E100`. `round` 는 정규화해 열한 코드면 `stage` 에 코드로 적고, 꼴이 아니면 422 `round_invalid`(`detail.allowed` — 풀이 전), 빼면
  `stage` 는 그대로다. 답 — `{ok, project_id, sp_task, stage, round, changed, previous: {sp_task, stage}, resolved_by: {tool, at, sha256} | null}`(MCP 는
  `web` 이 붙고, 위임 신원이 없으면 `delegation_required`). 바뀌었을 때만 감사 한 줄 `project.sp_subject`(앞 · 뒤 · 풀이 지문). 지문 `sha256` 은 구조화된
  답을 키 정렬한 JSON 의 해시라 에이전트의 `sp_resolved_by.sha256`(원문 글의 해시)과 같은 값이 아니다. 일반 PATCH 칸에는 넣지 않는다.
  `GET /api/projects/{id}/sp-subject` → `{project_id, sp_task, stage, round, hint: {sp_task, label, active, why, stepforge_project_id, tool} | null,
  hint_note}` — 힌트는 붙은 기구 CAD 원천의 `<앱 키>_get_project_meta.plm_task` 를 부른 사람의 PAT 로 읽은 보일 후보(확인이 아니다)이고, 못 읽으면 실패하지
  않고 `hint_note` 에 까닭이다. 구성원(보기 이상) · 관리자가 읽는다.
- **읽기** — MCP `risk_find_projects_by_subject(sp_task?, round?, artifact_kind?, artifact_id?, limit = 20(1 ~ 50), offset = 0)`. 부른 사람이 MCP 로 볼 수
  있는 과제(`visible_projects(caller)` — 소유 ∪ 구성원 ∪ 조직 공개, 위임 신원이 없으면 service 로 조직 공개만)에서 폐기된 과제를 빼고, `sp_task` 글자 그대로
  (앞뒤 공백만 뗀다) · 차수 정확히(`unknown` 은 차수 모름만 · 꼴이 아니면 422 `round_invalid`) · 설계 자료 열쇠(과제 주인의 `rr_sources.ref_json` —
  mcad 는 `stepforge_project_id`, ecad 는 `odb_job_id`, cae 는 `dyna_result` 의 `report_ids[]`, 대소문자 무시, 종류와 열쇠는 함께)로 거른다. `sp_task` 도
  설계 자료도 없으면(차수만 줄 때 포함) `sp_task` 가 있는 과제만이고, 설계 자료로 찾을 때는 `sp_task` 가 없는 과제도 든다. 답 — `{caller: user|service,
  projects: [{project_id, code, name, stage, round, sp_task, my_role, mcp_visibility, classification, targets: [{target_key, kind, level, verdict_candidate,
  verdict_final, created_at}], registry_top: [...5행까지], registry_total}], total, truncated, next_offset?}`. 대상은 과제 주인의 대체되지 않은 대상이다.
  등록부 행은 같은 사람이 `risk_get_registry` 로 받는 행과 같은 문(`mcp_scope_owner` → `registry_payload` — 시야 · 행 공개)을 지나 주의 등급 → 우선순위 →
  지지 영역 · 전문가 수 → 키 차례로 세운 앞 다섯이다. 리스크 앱의 상태 낱말 · `stale_json` 은 번역하지 않는다. 답이 MCP 결과 상한(약 2만 5천 자)을 넘으면
  과제 수를 줄이고 `truncated` · `next_offset` 으로 나눈다(자르지 않는다 — 계약에 `offset` · `total` · `next_offset` 을 더했다).
- **좌석에는 싣지 않는다** — `sp_task` 는 브리프 · 스냅샷 · 비교 · 패널 질문에 들지 않는다(D-18 — 리스크 앱 안의 칸이다).
- **반출 · 들여오기** — `sp_task` 는 이 박스의 풀이로만 선다. 반출은 싣지 않고 들여오기(`POST /api/import`)는 받지 않는다(새 행은 NULL, 뺀 줄 수는
  답의 `sp_task_dropped`) — 받으면 풀이 · 감사 없이 아무 key 나 단 과제가 남의 과제 보기에 선다(반대 검토 11-02). 받는 박스에서 주인이 주제 쓰기로
  다시 단다.
- **포털 과제 보기** — 읽는 사람의 PAT 로 게이트웨이 별칭 `heaxhwax_risk_risk_find_projects_by_subject` 를 불러(쪽마다 50, `next_offset` 을 따라 네 쪽까지 —
  더 남으면 '앞 N개만 실었다' 고 말한다) (과제, 차수) 칸에 싣는다. 리스크 권한(`plat:risk`)이 없거나 불통이면 그 칸에 까닭을 보이고 일반 심의 카드는
  그대로 보인다.
