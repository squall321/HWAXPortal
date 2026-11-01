# 토큰 절감 — 설계안 v1.0 검토와 계획

> 검토 대상 — 「토큰 1/10 을 위한 포탈 개선 · GLM 역할 확대 설계안 v1.0(2026-11-02)」(cae00 에서 쓴 것. 짝 문서 「T_토큰절감_분석_v1.1」 은 받지 못했다).
> 사용자 요청(2026-11-02 KST) — "클로드로 mcp 연결해놓고 하니까 토큰이 너무 심하게 나오는 경향이 있거든 … 할만한 부분인지 검토해봐".
> 읽기만 했다. 근거 줄은 게이트웨이 master `63fbc4f` · 에이전트 서버 `9f08507`(설계안 기준 `63ad54b` 위에 보고서 저장 커밋 셋 — 인용 줄은 그대로) · 포털 `ad3c0ca6` ·
> DocForge `27b1a97` · 리스크 앱 `d30bef6` · WDA `38f95d3` 판이다. 앞선 설계 [`../MCP-TOKEN-SAVING-DESIGN.md`](../MCP-TOKEN-SAVING-DESIGN.md)(07-21)와 이어진다.
> 결정은 [context-notes.md](context-notes.md), 할 일은 [checklist.md](checklist.md).

## 1. 판정

- **할 만하다 — 다만 순서가 다르다.**
  - P1 은 **이미 지어져 있다**(E-4, 10-31). PC 의 Claude Code 연결에 머리 한 줄이면 오늘 된다.
  - P3(심의 상태를 한 번에 기다리기) · P4a(심의 결과 요약 — 골라 쓰기) · `search_tools` 압축은 작고 안전한 코드다.
  - P4b(게이트웨이 공통 결과 줄이기) · P2(근거를 참조로)는 조건이 붙는 중간 일이다.
  - P5 · P7 · P9 · R5 · R7 은 **대부분 이미 있다**(리스크 앱 비교 · WDA 렌더 · '발표자료로').
  - P6 · P8 은 측정 뒤로 미룬다.
- **'1/10' 은 설계안 숫자로도 나오지 않는다.** 효과를 다 더해도 52.3%p — 남는 몫 약 1/2 이다(§4).
- **빠진 가장 큰 지렛대** — Claude 가 좌석마다 직접 도는 워크플로(`infra/pipeline/hwax-deliberate.js` — 라운드마다 좌석 수만큼 Claude 에이전트 · 의장,
  `hwax-risk-claude.js` — 엔진의 판단 과제마다 Claude, 한 번에 최대 800)를 서버 엔진(GLM — `deliberate_start` · 리스크 잡 `llm=glm`)으로 돌리는 것이다.
  코드가 아니라 **쓰는 길의 선택**이다.

## 2. 사실 확인

| 설계안 주장 | 판정 | 근거 |
|---|---|---|
| `x-hwax-view` 보기(full · light · bundle · portal) | **맞다 — 이미 있다** | 게이트웨이 `gateway.py:288-330`(뜻) · `:5452`(light = search_tools + invoke_tool) · `:5455-5483`(bundle) · `:6521-6535`(tools/list 에만) · `:7272-7287`(PAT — 머리 → 포털 설정 → full). 포털 `backend/app/access/hub_view.py` · `/auth/access/view` · 토큰 화면 '허브에 보일 앱' · 등록 배치가 이미 `X-HWAX-View:portal` 을 단다(`frontend/src/pages/tokens/setupBat.ts:491`) |
| 1,389 개 이름 ≈ 20.5k 토큰 | 셈 방법은 맞다 · cae00 숫자는 dev 에서 못 잰다 | 백엔드마다 하나 + 로컬 도구, 사람마다 권한 · 숨김으로 거른다(`gateway.py:1280-1413`, `:5440-5450`). dev 는 575(16 백엔드) — 전부 볼 수 있는 사람에게 약 590 |
| `search_tools` 결과가 1건 20.4k 까지 | 반만 | 바이트 상한이 없다(`gateway.py:3748`). 다만 기본은 이미 줄여 낸다 — 한 줄 설명 200자 · 필수 인자 스키마만(`:3511-3517` · `:3712-3726`), `detail=true` 일 때만 전부. JSON 을 `indent=2` 로 낸다(`:3771`) |
| `deliberate_status` · `deliberate_result` 인자는 job_id · part 뿐 | 맞다 | 에이전트 `mcp_server.py:957` · `:985`. 둘 다 부를 때마다 질문 전문을 되풀이한다(`delib_jobs.py:1994`) |
| `status_wait` 은 포털 챗에서만 | 맞다 · 그런데 본뜰 꼴이 아니다 | `app.py:112` 만 쓴다. 본뜰 꼴은 같은 파일의 `review_task_next(wait_s ≤ 25)`(`mcp_server.py:1211-1225`) |
| `mcp_pages` 25,000 토큰 넘으면 쪽으로 | 반만 | 25,000 **자**다(`mcp_pages.py:27-31`). 버리지 않고 쪽으로 나눈다 |
| `evidence.py` 가 숫자 출처를 대조 | 맞다 · 어림이다 | 부분 문자열 대조 — 소수점이 있거나 100 이상인 수만, '1232' 안의 '232' 도 출처로 친다(`evidence.py:17-63`) |
| `_RESP_CACHE` 1 MB · 64 MB 를 큰 결과 다시 보기에 | 숫자는 맞다 · **그 일에는 못 쓴다** | TTL 300초 · 512 개(`gateway.py:476-482`). 1 MB 넘는 결과는 아예 넣지 않고(`:941-957`), 정해진 이름만 · task/status/job 이름은 빼고 넣고, 쓰기가 오면 그 백엔드 몫을 다 비운다(`:6691`) |
| 근거 한도 120건 · 15만 자 · 50만 자 | 맞다 | `deliberation.py:205-206, 224`. 50만은 천장일 뿐 실제 몫은 모델 창에서 나온다(`:398-419`) |
| 루틴은 Qwen 만 · 단계별 LLM 이 없다 | 반만 | 박스 전체 손잡이 `ROUTINE_LLM=chat\|glm` 이 있다(`routine.py:50-51`). 단계 꼴에는 `llm` 칸이 없고 여분 칸을 막는다(포털 `routines.py:77-90`). 1판은 단계 안 쓰기 도구를 막는다 |
| DocForge 에 md → docx 쓰기가 없다 | 맞다 | 도구 여섯은 읽기 · 변환 · 상태뿐이다. `md2docx_v2.py` · `verify_docx.py` 는 dev 어느 리포에도 없다 |
| 영역 14 · `hub_view.py` | 맞다 | `tool_areas.json` 영역 14 · 앱 기본 34 · 도구별 덮어쓰기 136 |

설계안이 놓친 것(이미 있다):

- 결과 손잡이 + 나중에 받기 — 07-21 설계의 C 안이다. 그 설계가 이미 같은 위험(남의 손잡이 · 모델이 나머지를 안 받음)과 '모드로 골라 쓰기' 원칙을 적었다. 0단계 계측(호출마다 결과 크기)은 끝났다 — `audit.jsonl` 의 `chars`.
- 리스크 앱 — `risk_create_diff` + `risk_get_diff(part=summary|diff|events|lines …)` 가 서버에서 StepForge · ODB 허브 비교를 돌리고, 코드가 짓고 판단 낱말을 거르는 `summary_text` 를 준다. `risk_next_step` · 쟁점 등록부 · 선례도 있다.
- WDA — `render_submit(targets=video|pptx|html|pdf|docx, narration)` · TTS · `render_status`, 마크다운 → docx/pdf(`exporter_doc.py`). WDA 파이프라인 LLM 은 이미 GLM 이다.
- 포털 '발표자료로'(11-01 합침) — RA 보고서를 그 사람 명의로 읽어 WDA 로, 진행은 포털이 묻고 대화에 알린다(LLM 이 묻지 않는다). 박스 스위치로 켠다.
- AIDataHub `list_agents` 에 `compact` 가 있지만 기본은 전부다 — dev 감사에서 개인 PAT 로 501,141 자가 나간 줄이 있다.
- mcp-remote 0.1.38 의 `--ignore-tool <glob>` — 클라이언트 쪽에서 도구를 숨기고 막는다.

## 3. 항목별 판정

| 안 | 판정 | 품 | 위험 · 조건 | 겹치는 것 | 주인 |
|---|---|---|---|---|---|
| P1 보기 머리 | 지금 된다 | 설정 | 보기마다 득실(§5) | E-4 그 자체 | 사용자 PC |
| P3 `wait_s` | 된다 | S | 시간 층이 맞다 — 게이트웨이 호출 600초 · 백엔드 읽기 660초 · nginx 3600초 · SSE 15초 ping · mcp-remote 는 요청마다 상한 없음 · Claude Code `MCP_TOOL_TIMEOUT` 기본 1e8 ms(dev 판). 게이트웨이 재기동은 도는 호출을 30초만 기다리니 그때는 일찍 돌아온다. 상태 · 단계 · 라운드가 바뀌면 일찍 돌아온다. 질문 되풀이를 빼는 `brief` 를 함께 둔다 | `review_task_next` · 루틴은 이미 코드가 20초마다 묻는다 | 에이전트 서버 |
| P4a 심의 결과 요약 | 된다 | S | **기본은 full 그대로** — 루틴의 심의 단계가 결정문을 쪽마다 다 읽는다(`routine.py:1769-1782`). summary 는 골라 쓰기 | — | 에이전트 서버 |
| P4b 게이트웨이 공통 결과 줄이기 + `result_get` | 조건부 | M | **연결 머리로 고를 때만** — via=pat 로 가르면 루틴 · 리스크 앱 · MXWP 위키 같은 서버 쪽 길도 걸린다. 엔진 · 챗 · 절차 · 패널은 그대로. **따로 쓰는 저장소**(무작위 손잡이 · 메일 · 그룹 · 소속에 묶음 · TTL · 사람마다 몫 · 디스크) — `_RESP_CACHE` 는 안 된다. `content` 와 `structuredContent` 를 함께 줄인다(출력 스키마가 있는 도구 — Claude Code 가 거절한다). 검증 근거에는 전체를 남긴다. 25k 넘는 결과는 Claude Code 가 이미 파일로 빼므로 겨냥은 5~25k. **가장 싼 첫걸음** — JSON 들여쓰기 빼기(약 1.3배) | 07-21 C 안 · 앱 안 쪽 나누기 | 게이트웨이 |
| P2 근거를 참조로 | `{tool, args}` 는 된다 · `{ref}` 는 나중 | M | 설계안의 'PAT 로 다시 부른다' 는 틀렸다 — MCP 로 연 잡은 사람 · 그룹 · 소속만 넘어오고 엔진은 게이트웨이 비밀 + 그 머리로 부른다. **확인된 읽기 도구만**(`/tools-map` `panel_read` — 이름 짐작 없이), 사람이 없으면 막고, 봉인 · 기준일 아래서는 바깥 조회로 친다. 근거 표지에 도구 · 인자 · 때 · sha256 | 지정 도구 미리 부르기 · 좌석 자유 조회 · 근거 앞 단계 | 에이전트 서버 |
| P5 CAD · ECAD 비교 요약 | 거의 있다 | S~M(감싸기) | LLM 이 쓰는 비교 해설은 리스크 앱의 '판단 낱말 금지' 를 깬다 | `risk_create_diff` · `risk_get_diff(summary)` · ODB 허브 `run_compare` | 리스크 앱 |
| P6 인사이트 원장 | 크다 | L | 허브 셋이 함께 쓰는 플랫폼 스키마 변경 · 쓰기는 확인 도구 · 숫자 대조가 어림 · 인용한 도구 이름을 dev 에서 확인 못 함 | 리스크 쟁점 등록부 · MXWP 위키 · 루틴 통찰 절 | SP 세션 + 에이전트 |
| P7 md → docx | 된다 | M | Claude 가 여전히 마크다운을 쓴다 — 스크립트 · 대조 왕복만 준다 | WDA 마크다운 → docx/pdf · '발표자료로' Word | DocForge 보다 WDA 세션 |
| P8 큰 결과 서버 집계 | 크다 | L | 아무 꼴의 결과를 다뤄야 하고 틀린 집계가 사실처럼 보인다 · P4b 에 기댄다 · 효과(−10)의 근거가 가장 약하다 | 앱 안 거르개 | 게이트웨이 |
| P9 영상 서버 렌더 | 있다 | S(켜기) | cae00 에 WDA 새 판 · 스위치. 포털은 지금 내레이션을 끈 채 보낸다(`wda_deck.py:472`) | WDA 영상 + TTS · 포털 중계 | WDA + 포털 |
| 리스크 심사를 루틴으로 | 적힌 대로는 안 된다 | L | 1판이 단계 안 쓰기를 막고 단계별 LLM 칸이 없다 | 리스크 앱 웹 러너(GLM) | 포털 + 에이전트 + 게이트웨이 |
| R1 결과 요약 · R2 근거 묶음 | 된다 | M 씩 | 숫자가 흐트러진다 → 코드 대조 · 원문 손잡이 동봉 | P4b · P2 · 근거 앞 단계 | 에이전트 서버 |
| R3 원장 적재 | 크다 | L | P6 와 같다 | P6 · 리스크 등록부 | 에이전트 + SP |
| R4 절 초안 | 된다 | M | 검수 · 숫자 대조 | 루틴 보고서 절 · 심의 보고서 저장 · WDA 문서 | 에이전트 서버 |
| R5 차이 해설 | 작다 | S | 판단 낱말 | 리스크 앱 `summary_text` | 리스크 앱 |
| R6 용어 | 작다~중간 | S~M | — | `core_vocab.json` · 검색 동의어 · `risk_taxonomy` | 포털 · 게이트웨이 |
| R7 장면 JSON | 있다 | — | — | WDA(GLM) | WDA |
| R8 결정문 1차 대조 | 작다 | S | 표시 0 이어도 숫자 대조는 필수 | 챗 자기검증 · 결정문 숫자 대조 | 에이전트 서버 |
| 역할별 한도(심의 아래) | 새 코드 | M | 공용 GLM 우선순위 줄이 없다(심의 입장 · 카드 대조 관문 · 세마포어뿐) | — | 에이전트 서버 |
| §4.5 Claude Code 를 GLM 으로 | 코드로 판단 못 함 | — | 모델을 바꾸는 일이지 줄이는 일이 아니다 · 도구 사용 품질을 따로 재야 한다 | — | 사용자 PC |

## 4. 셈

- 설계안의 효과를 더하면 3.8 + 3.0 + 8 + 3.5 + 3 + 7 + 6 + 10 + 8 = **52.3%p** — 겹치지 않고 더해진다 쳐도 47.7% 가 남는다(약 1/2.1). 차례로 곱하면 약 42% 를 줄여 0.58 이 남는다.
- 겹침이 있어 실제는 더 작다 — P4 · P8 · P5 · R1 이 모두 큰 결과를 겨냥하고, P2 · R2 가 모두 근거를 겨냥한다. P6 · P7 · P9 는 Claude 가 지금 그 일을 할 때만 줄고, P5 · P9 는 대부분 이미 있다.
- 90% 까지 약 38%p 가 모자란다. 목록 안에는 그것을 메울 것이 없다. 메울 후보(먼저 잰다) — ① Claude 쪽 워크플로를 서버 엔진으로(코드 0) ② 턴 수 × 문맥 크기(P3 · 세션 정리) ③ 진짜 가중 기준 — cae00 `audit.jsonl` 의 `via=pat` 도구별 `chars` 와 Claude Code 자체 사용량 나눔.
- 설계안의 '17k 토큰 = 3.8%' 는 가중치를 모르면 코드로 다시 셀 수 없다. 다만 상태 묻기는 실제로 많다 — dev 에서 09-06 하루 `deliberate_status` 168번 대 `deliberate_result` 통틀어 5번.

## 5. 권장 순서

### 오늘 — PC 설정만(사용자)

1. **P1 보기 머리.** 포털 등록 배치와 같은 꼴(`setupBat.ts:491`):
   ```
   claude mcp add -s user hwax -e AUTH="Bearer <PAT>" -- npx -y mcp-remote <MCP_URL> --header "Authorization:${AUTH}" --header "X-HWAX-View:<보기>"
   ```
   JSON 인자 꼴 — `["-y","mcp-remote","<MCP_URL>","--header","Authorization:${AUTH}","--header","X-HWAX-View:bundle:expert,report,knowledge"]`
   (mcp-remote 는 첫 쌍점에서 가르니 `bundle:` 은 괜찮다 — 쌍점 뒤에 빈칸을 두지 않는다). 다시 띄운 뒤 `list_tool_apps` 로 `view.mode` · `listed` · `hidden_by_view` 를 본다.

   | 보기 | 무엇 | 득실 |
   |---|---|---|
   | `full` | 지금과 같다 | cae00 에서 요청마다 이름 목록 약 20k |
   | `bundle:expert,report,knowledge`(시작으로 권장) | 주로 쓰는 영역의 이름과 도구별 권한 규칙이 남는다(dev 약 590 중 약 155) | 그 밖은 `search_tools` → `invoke_tool` |
   | `light` | 두 개만 | 모든 호출이 `invoke_tool` 이라 권한 하나가 전부를 덮는다 — 늘 허용하면 `deliberate_start` 같은 쓰기도 저절로 허락된다. 지우기 · 멈추기 · 게시 같은 도구는 `invoke_tool` 로 닿지 않는다. 패널이 그려지지 않는다. 검색이 는다 |
   | `portal` | 토큰 화면 '허브에 보일 앱' 에서 고른 대로 · Claude Code · Desktop 이 같은 설정 | 다시 붙어야 먹는다 |

2. **PC 의 CLAUDE.md 습관** — `deliberate_status` 를 고리로 부르지 않는다, `search_tools` 는 `detail` 없이, `list_agents(compact=true)`, 위험 일은 `risk_next_step` 부터, `MAX_MCP_OUTPUT_TOKENS` 를 25k 아래로 내리면 서버의 쪽 크기도 같이 내린다.
3. **큰 심의 · 리스크 판단은 서버 엔진으로**(`deliberate_start` · 리스크 잡 `llm=glm`) — Claude 워크플로는 품질을 따로 재야 할 때만.
4. **보고서 → PPT · PDF · Word · 영상은 '발표자료로'** 를 cae00 에서 켠 뒤 쓴다(P7 · P9 를 짓기 전에).
5. **cae00 에서 먼저 잰다** — `audit.jsonl` 에서 `via=pat` 의 도구별 `chars` · 호출 수, `/health` 의 보기 셈(받은 편지함 Q13).

### 작은 코드(S) — 바로 해도 안전하다

- 에이전트 서버 — `deliberate_status(wait_s ≤ 240, brief)`(`review_task_next` 꼴 · 게이트웨이 비우기 · 상태 변화에 일찍 돌아온다).
- 에이전트 서버 — `deliberate_result(view="summary")` 골라 쓰기(기본 full).
- 게이트웨이 — `search_tools` 를 촘촘한 JSON 으로(골라 쓰기) · `detail=true` 에 크기 상한.

### 중간(M) — 잰 뒤

- P2 `{tool, args}`(확인된 읽기 울타리 · 출처 표지).
- P4b 머리로 고르는 결과 줄이기 + `result_get`(따로 쓰는 저장소 · 사람에 묶은 손잡이).

### 나중 · 데이터가 필요를 보일 때만

- P8 · P6 · P7(WDA 의 마크다운 입구로) · 리스크 심사 루틴 · R1 ~ R4 와 GLM 우선순위 관문 · §4.5 는 따로 시험.

## 6. 사용자가 정할 것

1. 작은 코드 셋(P3 · P4a · search_tools 압축)을 바로 지을지.
2. Claude 쪽 워크플로 대신 서버 엔진을 기본 길로 안내할지(스킬 · 지침 · 등록 배치의 안내 글).
3. P4b · P2 를 cae00 측정 뒤에 정할지(권장), 지금 지을지.

## 7. cae00 에서 잴 것

받은 편지함 [`../cae00-inbox/2026-11-02.md`](../cae00-inbox/2026-11-02.md) Q13 — `audit.jsonl` 의 via=pat 도구별 호출 수 · `chars` 합 · 상위 20, 상태 묻기 도구의 비율, 보기 머리별 연결 수(`/health`).
