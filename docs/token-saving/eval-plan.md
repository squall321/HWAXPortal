# 토큰 절감 2판 비교 테스트셋 — 계획

> 사용자 요청(2026-11-24) — 「GLM · Qwen 에 맡기는 비중을 만들어도 품질 차이 없이 속도나 토큰량이 나아지는지 확인하는 테스트셋」.
> 2판 계약 [offload-v2.md](offload-v2.md), 결정 [context-notes.md](context-notes.md) TS-14, 실행 · 사람 차례 [`infra/offload-eval/README.md`](../../infra/offload-eval/README.md).

## 1. 목적

같은 과제를 baseline(지금처럼) · offload(2판 — 결과 손잡이 머리 · 2판 도구 여덟 · PC 킷 E 규칙 묶음)로 Claude Code 를 사람 없이 돌려, Claude 토큰 · 비용 · 시간 ·
도구 호출이 줄었는지와 품질이 그대로인지를 한 보고서로 본다. 서버 LLM 이 대신 쓴 몫도 따로 센다 — Claude 토큰만 줄고 서버가 더 쓰는 것을 숨기지 않는다.

## 2. 사용자 결정(2026-11-24)

| 무엇 | 결정 |
|---|---|
| 돌릴 곳 | cae00 박스 — Claude Code CLI 와 로그인은 사람이 준비, 여기서는 안내만 |
| 실험 대상 모델 | Opus 5.5(`claude-opus-5-5`) |
| 품질 판정 | Claude 눈가림 판정(기본 `claude-sonnet-5-5` · 손잡이) + 사람 표본 4쌍 |
| 규모 | 과제 16 × 반복 2 — 두 갈래 64 실행 + 판정 32 |

## 3. 설계

- **과제** — 네 갈래 넷씩(R 큰 결과 읽기 → B · M 다단계 조사 → A · W 긴 글 → C · T 변환 → D). 모두 「읽기만 하고 아무것도 바꾸지 마라」, 공개 리포라 과제명 ·
  주소 없이 「가장 최근 것 하나를 골라」 로 스스로 찾게 한다. 과제마다 코드로 볼 기대 꼴(표 행 수 · 줄 수 · 글자 수 · 낱말 · 영어 비율).
- **실행** — `claude -p --output-format stream-json --verbose`. 과제 × 반복 × 갈래를 씨앗으로 섞은 차례로, 동시 1, 이어 하기(끝난 것은 건너뛰고 기반 오류만 다시).
- **안전** — 허용 목록은 게이트웨이 `/tools-map` 의 `routine_read`(루틴 울타리) ∪ 게이트웨이 로컬 조회, `invoke_tool` · `rest_call` 없음, offload 만 2판 여덟.
  허용 밖 · 내장 도구는 deny 맨 이름으로 문맥에서 빼고 권한 모드 dontAsk. 사용자 · 프로젝트 설정은 싣지 않는다. 실행마다 울타리를 대조해 위반이면 멈춘다.
  PAT 는 환경변수로만 받아 0600 임시 파일 머리에만 쓰고 지우며, 남는 산출물은 가린다.
- **셈** — 실행마다 `result` 의 usage(입력 · 출력 · 캐시 쓰기 · 캐시 읽기) · `total_cost_usd` · `duration_ms` · `num_turns` · 도구 호출 · 막힌 호출 · 쓴 2판 도구,
  답의 숫자 대조(에이전트 서버 `evidence` 와 같은 판정), 서버 쪽(위임 tokens · 서버 numbers.mismatched · tokens 칸 없는 호출 수). 합계 · 중앙값 · 개선율은
  두 갈래가 다 끝난 짝만.
- **판정** — 같은 과제 · 반복의 두 답을 A/B 무작위 · 눈가림(갈래 이름 없음, 답 안의 2판 도구 이름 · 손잡이는 같은 표지로)으로 판정 모델에. 꼴
  `{winner, scores{A,B}{correct, complete, clear}, reason}`, 틀리면 한 번 다시. 사람 표본 4쌍은 따로 섞은 A/B 로 `human-review.md` 에.

## 4. 판정 기준(제안 — 사람이 정한다)

「품질 차이 없음 = 판정 패배율 ≤ 10% 이고 숫자 대조 어긋남이 늘지 않음」. offload 의 어긋남에는 서버가 표시한 numbers.mismatched 를 더한다. 두 값은 실행기의
손잡이(`--max-loss-rate` · `--max-mismatch-increase`)라 결과를 본 뒤 바꿔 다시 낼 수 있다.

## 5. 남은 것

- cae00 — 스위치 켜기 → 사전 점검 → 연기 시험 → 본 실행 · 판정 · 사람 표본 → 보고서 돌려받기(사람, README 1).
- 결과 파일 Read 허용(README 4-3)이 요청의 「Read 도 막는다」 와 다르다 — 사용자 확인.
- `draft_section` · `llm_transform` · `result_ask` 결과에 tokens 칸이 없어 서버 토큰은 위임 몫만 정확하다 — 셋에 칸을 더할지(에이전트 서버 · 게이트웨이)는 결과를 본 뒤.
