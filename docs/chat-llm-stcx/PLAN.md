# 챗은 stcx GPU LLM, 심의는 GLM — 챗 전용 LLM

> 받은 것 — 사용자(2026-10-17) "지금 새로 사용할 수 있는 stcx 의 그래픽 카드를 chat 에서 사용하고, 심의에서 GLM 을 사용하게끔 할 수
> 있어?" 근거는 사용자가 붙인 「stcx GPU LLM 사용 가이드 v1.1」(stcx viz 노드 10대의 Qwen3.8-Flash-Next 10벌 · hwax=cae00 의
> `127.0.0.1:18700/v1` 부하분산기 · OpenAI 호환). 결정과 까닭은 [context-notes.md](context-notes.md), 할 일은 [checklist.md](checklist.md),
> cae00 절차는 [server-setup.md](server-setup.md).

## 1. 지금

에이전트 서버는 LLM 클라이언트를 둘 만든다 — `app.state.llm`(챗 ReAct · 챗 안 도구 계획 · 띵킹 · 심의 준비 도우미)과
`app.state.delib_llm`(심의 라운드 · 카드 대조). 둘 다 `VLLM_BASE_URL` · `VLLM_MODEL`(cae00 은 GLM-5.2) 하나를 본다. 가이드의 '방법 B'
(에이전트 서버 `.env` 의 `VLLM_BASE_URL` 교체)는 둘을 함께 바꿔 심의까지 stcx 로 보낸다.

## 2. 바꾸는 것

| 자리 | LLM |
|---|---|
| 챗 ReAct · 챗 안 도구 계획(`_agent_stream`) | **챗 전용**(설정하면 stcx, 아니면 지금처럼 GLM) |
| 띵킹(`run_thinking`) | GLM(사용자 결정) |
| 심의 준비(전문가 고르기 축 · VOC 미리보기 · 되묻기 · 챗→심의 주제) · 심의 라운드 · 카드 대조 | GLM |

- **챗 전용 클라이언트** — 에이전트 서버 `.env` 의 `CHAT_LLM_BASE_URL` · `CHAT_LLM_MODEL`(· `CHAT_LLM_API_KEY`). 비면 챗도 지금 클라이언트를
  그대로 쓴다(바뀌는 것 없음).
- **장애 때 GLM 으로 넘긴다(호출 단위)** — 연결 실패 · 시간 초과 · 5xx 면 그 LLM 호출을 GLM 으로 다시 보낸다. 턴 전체를 다시 돌리지 않는다
  (이미 실행한 도구가 두 번 돈다). 토큰이 흐르기 시작한 뒤 끊긴 것은 넘길 수 없다(가이드 6장).
- **생각 모드 끔** — `chat_template_kwargs.enable_thinking=false`(사용자 결정). `CHAT_LLM_ENABLE_THINKING=1` 로 켠다.
- **문맥 창** — 챗 경로의 예산은 챗 서버 창(Qwen 262,144)과 GLM 창 중 작은 값. 지금은 GLM 의 1M 으로 챗 예산까지 잡으므로 그대로면 긴
  챗이 400 으로 죽는다.
- **보이기** — `/health` 의 `chat_llm`(주소 · 모델 · 창 · 넘긴 횟수 · 마지막 넘김 사유).
- **포털 update-all 3.5** — `infra/.env` 의 `CHAT_LLM_*` 를 에이전트 서버 `.env` 로 맞춘다(없으면 ○ · 빈 값이면 끔 · 값이면 적고 그 서버가
  모델을 내는지 본다). 에이전트 서버 `.env` 는 그 서비스의 지문이라 바뀌면 재기동된다.

## 3. 단계

| 단계 | 무엇 | 누가 |
|---|---|---|
| C1 | 에이전트 서버 — 챗 전용 클라이언트 · 넘김 · 생각 끔 · 창 · /health · 시험 | dev |
| C2 | 포털 update-all 3.5 · 킷 주석 · 시험 | dev |
| C3 | cae00 절차서 · 업데이트 이력 · CLAUDE.md 문서 표 | dev |
| C4 | cae00 — `infra/.env` 두 줄 · update-all · 확인 | 사람 |
