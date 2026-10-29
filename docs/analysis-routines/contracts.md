# 분석 루틴 — 계약(R0, 10-30)

계획 [PLAN.md](PLAN.md) · 판단 [context-notes.md](context-notes.md). 이 문서는 포털 · 게이트웨이 · 에이전트 서버가 함께 지키는 꼴이다.
기계가 읽는 정본은 포털 `backend/config/routine_contract.json`(봉투 · 상태 · 도구 입력)이고, 스펙의 정본은 포털 `app/procedures/routines.py` 의
pydantic 모델이다. 세 리포의 시험이 그 파일을 읽어 맞댄다(코어 어휘표와 같은 형제 파일 방식).

## 1. 루틴 스펙(RoutineSpec v1)

```yaml
version: 1
title: 시장불량 원인 분석                         # 1 ~ 120자
purpose: "{{model}} 의 {{symptom}} 시장불량 — 원인 · 시험 · 대책"   # 0 ~ 2,000자, 질문의 틀
vars:                                             # 절차의 Var 그대로(key · label · type · values · required · why · example), 12개까지
  - {key: model, label: 모델, type: string}
  - {key: symptom, label: 증상, type: string}
steps:                                            # 1 ~ 12
  - id: anchor                                    # [a-z][a-z0-9_]{0,23}, 고유
    title: 기준 키
    kind: platform                                # platform | deliberation | cite
    backends: [rootdesigndatahub]                 # 게이트웨이 백엔드 키 1 ~ 3 — 단계의 울타리
    goal: "{{model}} 을 코어 허브의 plm_model 로 푼다"   # 1 ~ 2,000자
    tools: [object_resolve]                       # 원래 이름, 12개까지 — 비면 그 백엔드 도구 전부
    expect: {keys: [model_key]}                   # 이 단계가 다음 단계에 넘길 키(8개까지)
    blocked: {empty: stop, denied: stop, unavailable: stop}   # 기준 키 단계는 멈춘다(사용자 결정 Q4)
  - id: ft
    title: 시장불량 이력(FailureTrace)
    kind: platform
    backends: [failuretrace]
    goal: "{{steps.anchor.model_key}} 의 {{symptom}} 불량 기록을 유형 · 시기별로"
    uses: [anchor]                                # 앞 단계만 — 그 단계의 요약 · 키 · 근거 id 가 이 단계에 실린다
    budget: {calls: 6, seconds: 300}              # 기본 8 · 300, 상한 30 · 1,800
  - id: delib
    title: 메커니즘
    kind: deliberation                            # backends 없음 — 심의 엔진(deliberate_start)을 부른다
    goal: "불량의 메커니즘을 밝힌다"
    uses: [ft]                                    # 앞 단계의 원 근거(도구 · 인자 · 결과)를 evidence 로 넘긴다(결론 아님 — 심의 헌법 P1)
    deliberation: {job: mechanism}
report:
  title: "{{model}} {{symptom}} 분석"
  sections: [anchor, ft, delib, insight]          # 단계 id 와 insight · cite 의 순서
  ra: {upload: auto}                              # auto(기본 — 사용자 결정 Q1) | ask | off
limits: {minutes: 60, calls: 60}                  # 5 ~ 240 · 1 ~ 200
visibility: private                               # private(기본) | all
```

- `blocked` 기본은 `{empty: continue, denied: skip, unavailable: skip}` 다(칸 이름이 `on` 이 아닌 까닭 — YAML 1.1 은 `on` 을 참으로 읽는다) — 막힌 단계는 사유를 적고 건너뛴다(사용자 결정 Q2 · Q4).
- 참조는 셋뿐이다 — `{{<var>}}` · `{{steps.<id>.<key>}}`(그 단계 `expect.keys` 에 있어야 한다) · `{{run.started}}`.
- 단계 안 쓰기는 없다(v1) — `tools` 에 쓰기 도구(절차 `MUST_GATE` · `WARN_*` · 게이트웨이 차단 접두)를 적으면 저장이 거절된다. `tools` 를 비우면 런타임에
  읽기 도구만 묶는다(`readOnlyHint` 또는 게이트웨이 `read_tools`).

### 저장 때 검증과 실행 때 준비도

| | 저장 때(검증 — 막는다) | 실행 때(준비도 — 막지 않고 단계 상태로) |
|---|---|---|
| 꼴 | 칸 · 길이 · id 고유 · `uses` 는 앞 단계 · 참조가 풀린다 · 쓰기 도구 없음 · 비밀 상수 없음 | — |
| 백엔드 | 꼴만(이 박스에 없어도 저장된다 — cae00 루틴을 dev 로 가져올 수 있다) | `allowed` · `denied`(권한 없음) · `not_connected`(RA · FMEA · TestScope 토큰 미등록) · `unavailable`(이 박스 게이트웨이에 없음) · `muted`(허브 앱 끔 — 루틴은 부른다) |

## 2. 실행 — 상태와 원장

- 실행 상태 — `queued → running → (waiting) → done | failed | cancelled | interrupted`. `waiting` 은 사람이 고를 것이 있을 때(기준 키 후보 여럿)뿐이다.
  `interrupted` 는 실행자가 사라졌을 때(에이전트 서버 재기동 · Claude 세션 종료) — 저절로 다시 돌지 않고 '이어서' 로 끝난 단계를 건너뛴다.
- 단계 상태 — `pending · running · ok · empty · ambiguous · denied · not_connected · unavailable · failed · skipped`. **포털이 정한다** — 실행자가 보낸 봉투를
  원장과 맞대 고친다(호출 0 인데 ok 면 skipped, 결과가 다 오류면 failed, 이 박스에 없는 백엔드면 unavailable).
- 호출 원장 — `routine_call` 하나가 `routine_calls` 표의 한 줄이다(`call_id` = `<단계 id>.c<n>`, 백엔드 · 원래 이름 · 인자(sha256) · 결과(gzip, 2,000,000자
  넘으면 앞부분과 truncated) · ok · ms). 절차 원장(`runs` · `run_steps`)과 따로 둔 까닭 — 그 표의 칸(schema_fp · expect · 게이트)은 절차 것이라 루틴 호출에
  맞지 않는다(R2, 10-30). 좋은 단계를 절차로 굳히는 길(derive)은 그 뒤에 이 표를 읽어 짓는다.

### 단계 봉투(실행자 → 포털, `routine_step_done`)

```json
{"status": "ok", "reason": "", "summary": "마크다운 6,000자까지",
 "keys": {"model_key": "SM-S938"},
 "findings": [{"text": "솔더 크랙이 3분기에 몰린다", "refs": ["ft.c2"]}],
 "candidates": []}
```

- `keys` 의 값은 그 단계 호출 결과 어딘가에 글자 그대로 있어야 원장에 든다 — 없으면 `unsourced_keys` 로 표시하고 다음 단계에 넘기지 않는다.
- `refs` 는 그 실행의 `call_id` 여야 한다 — 없는 것은 `bad_refs`. `findings` 20개 · `text` 500자 · `candidates` 20개까지.
- `status=ambiguous` 면 `candidates`(`{label, key}`)가 있어야 한다 — 실행은 `waiting` 이 되고 사람이 고르면 그 단계가 `ok` 로 닫힌다. 고르는 길은 둘 —
  화면의 `/pick`, 또는 실행자가 같은 단계를 `status=ok` + 고른 후보의 키로 다시 닫는다(Claude 가 대화에서 사람에게 물은 뒤).

## 3. 포털 `/routines-api`

권한 `feat:routines`(사용자 결정 기본값 Q5). 짜기 · 고치기 · 공유는 세션 + CSRF, 읽기 · 실행 · 원장 쓰기는 세션 또는 PAT(`principal_pat_or_session` — 게이트웨이가
호출자 PAT 를 그대로 넘긴다). 실행은 주인만 본다.

| 길 | 하는 일 |
|---|---|
| `GET /health` | 무인증 — `{ok, contract: 1}`(게이트웨이가 '포털이 낡았다' 를 가르는 데 쓴다) |
| `GET /platforms` | 내 도구 목록(사람 PAT 의 tools/list)을 백엔드로 묶어 라벨 · 원래 이름 · 읽기 여부 · 이 박스에 있나 |
| `GET /routines` · `POST /routines` | 내 것 + 공개된 것 / 새로(첫 판) |
| `GET /routines/{id}` · `POST /routines/{id}/versions` · `PATCH /routines/{id}` · `DELETE /routines/{id}` | 판 목록 · 새 판(주인만) · 공개 범위 · 보관(지우지 않는다) |
| `GET /routines/{id}/readiness` | 단계마다 나의 준비도 |
| `POST /validate` · `GET /routines/{id}/export` · `POST /import` | 검증만 · YAML |
| `POST /runs` · `GET /runs/{id}` · `GET /runs` | 실행 시작(판 · 입력 박기 → 계획) · 진행 · 내 실행 |
| `POST /runs/{id}/calls` | 호출 한 줄(게이트웨이 `routine_call` 이 쓴다) |
| `POST /runs/{id}/steps/{step}/done` · `POST /runs/{id}/steps/{step}/pick` | 단계 봉투 · 사람이 고른 후보 |
| `POST /runs/{id}/report` · `POST /runs/{id}/ra` · `POST /runs/{id}/cancel` | 절 → 렌더(RA 블록) · RA 결과 · 멈춤 |

## 4. 게이트웨이 MCP 도구(로컬 — 호출자 PAT 를 포털로 넘긴다)

| 도구 | 입력 | 하는 일 |
|---|---|---|
| `routine_list` | `q?` | 볼 수 있는 루틴 · 단계마다 지금 부를 수 있나 |
| `routine_get` | `routine_id` · `version?` 또는 `run_id`(+ `call_id` · `page`) | 계획(단계 · 울타리 · 허용 도구 · 할 일 · 기대 출력 · 예산 · 보고서 절) 또는 진행과 다음 단계 — `call_id` 면 원장의 큰 결과 한 쪽(60,000자) |
| `routine_run_start` | `routine_id` · `version?` · `inputs` | 실행 id 와 계획 |
| `routine_call` | `run_id` · `step` · `name` · `arguments` | 단계 울타리 안의 도구를 부른다 — 계획의 허용 도구 `{백엔드: [원래 이름]}` 만(포털이 실행을 시작할 때 그 사람의 목록에서 읽기 도구만 찍는다 — 쓰기 분류의 정본은 포털 하나). 이름은 원래 이름 · 노출 이름 · `백엔드:원래 이름`(두 백엔드에 같은 이름이면 이 꼴만). 정상 호출 길을 그대로 타고(절차 면제 없음) 감사 corr 는 `routine:<실행>:<단계>`, 원장에 남긴다. 큰 결과는 원장에 다 두고 응답은 쪽. 심의 단계 `deliberate_start` 는 evidence 를 비우면 앞 단계 원 근거로 채운다 |
| `routine_step_done` | `run_id` · `step` · 봉투 | 단계 상태 · 다음 단계 또는 보고서 틀 |
| `routine_report_submit` | `run_id` · `sections` · `citations?` | 포털이 렌더 → `ra.upload=auto` 면 게이트웨이가 호출자 이름으로 `create_report_draft`(RA 토큰 없으면 건너뛰고 알림 — 서비스 계정 없음) |

- 포털이 `/routines-api/health` 에 답하지 않으면 도구는 '포털이 이 판보다 낡았다' 를 낸다('루틴 없음' 이 아니다).
- 읽기 전용 PAT 는 `routine_list` · `routine_get` 만 — 실행은 원장을 쓰므로 막는다.

## 5. 챗(Qwen)

- 요청 칸 `routine = {id, version?, inputs, run_id?}` — 포털 · 에이전트 서버 두 곳에 선언한다(안 하면 조용히 버려진다). 포털 중계가 실행을 만들고 계획을 붙여 넘긴다.
- SSE 이벤트 `routine` 하나 — `{kind: plan | step | step_done | gate | report | done, run_id, step?, status?, title?, detail?}`. `token` 은 최종 보고서만.
- 에이전트 서버는 단계마다 그 백엔드 도구만 묶고(안내대 도구 없음) 도구 호출을 `routine_call` 로 감싼다 — 울타리와 원장이 Claude 길과 같다.

## 6. 보고서

- 절 = 단계 제목. 절마다 그 단계의 요약 · 수치 · 근거 id. `insight` 절은 근거 id(`[ft.c2]`)를 인용해야 한다. `cite` 단계의 결과는 인용 목록이 된다.
- 포털이 덧붙인다 — 커버리지(한 단계 · 건너뜀 · 권한 없음 · 이 박스에 없음 — 숨기지 않는다) · 근거 부록(원장) · 출처 없는 수치 표지.
- RA — 템플릿 `deliberation` v1 블록 넷으로 렌더한다: `background`(목적 · 입력 · 기준 키 · 커버리지) · `results`(단계 절) · `recommendation`(인사이트 · 인용) ·
  `minutes`(근거 부록). 항목은 2,000자 이하로 나눈다(에이전트 서버 `_ra_split` 과 같은 결과 — 계약 시험). 태그 `분석 루틴` · 루틴 제목.

## 7. R2 에서 정한 것(10-30)

- 실행 보기(`GET /runs/{id}`)는 계획에 단계 상태 · 호출 수 · 넘긴 키 · 요약 · 고친 표지(flags)를 얹고, 할 일의 참조를 지금까지 넘긴 키로 푼다. `run.limit_reached` 는
  시간 · 호출 상한에 닿았을 때의 까닭이다(게이트웨이가 부르기 전에 보고 거절한다 — 포털도 원장 쓰기에서 다시 본다).
- 실행 시작은 '멈춤' 으로 짠 단계가 막혔으면 `failed` 로 시작한다(까닭과 함께). 입력은 선언한 형으로 맞추고 모르는 키 · 빠진 필수는 422.
- 심의 근거(`GET /runs/{id}/evidence?step=`)는 그 단계가 쓰는 앞 단계들의 **성공한** 호출 원문 — 120건 · 건마다 15,000자까지(엔진이 창에 맞게 더 줄인다).
- 보고서는 모든 단계가 닫힌 뒤에만 낸다(`done` 으로 끝낸다). RA 블록은 deliberation v1 넷 · 항목마다 1,900자 이하(엔진 `_ra_split` 과 같은 결과 — 포털
  시험이 엔진 원문 글에서 함수를 떼어 맞댄다). 경고 — 루틴에 없는 절 · 원장에 없는 인용 · 근거 없는 수치 문단.
- 읽기 전용 PAT 는 `routine_list` · `routine_get` 만(게이트웨이 `_readonly_denial` — 루틴 도구는 경로에 없는 로컬 도구라 따로 막는다).
- 일반 챗(에이전트 서버 ReAct)은 루틴 도구 여섯을 묶지도 `invoke_tool` 로 부르지도 않는다 — 루틴은 사람이 골라 켜는 것이다(R3 의 루틴 모드는 코드가 부른다).
