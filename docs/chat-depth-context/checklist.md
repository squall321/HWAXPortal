# 챗 생각 깊이 · 대화 맥락 — 체크리스트

> 계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md) · 요청서 [request.md](request.md).

## T1 챗 생각 · 강도 · 출력 상한(에이전트 서버 `a3bde55` · `35c048b`)

- [x] `CHAT_LLM_ENABLE_THINKING` 기본 1 · `CHAT_LLM_REASONING_EFFORT`(기본 `xhigh`) · `CHAT_LLM_MAX_TOKENS`(기본 보내지 않음 — stcx 서버 131,072, 끄면 `LLM_MAX_TOKENS`)
- [x] 챗 턴의 창 = min(챗 서버, GLM) − 출력 몫(`CHAT_LLM_OUTPUT_RESERVE` 생각 켜면 65,536 · 보내는 상한이 더 크면 그 값, 창 절반까지만)
- [x] `/health` 의 `chat_llm` 에 `effort` · `max_tokens` · `output_reserve`, 기동 줄
- [x] 챗 서버가 '창이 모자라다' 로 거절한 400 만 GLM 으로 넘긴다(`ChatCtxOverflow` — 다른 400 은 그대로)
- [x] 시험 — 요청 본문(가짜 서버) · 창 덮어쓰기 · 끈 경우 종전 그대로

## T2 챗 이력에 조회 근거(CD-D5 — 에이전트 서버 `ecf0f93` · 포털 `d1c55eb`)

- [x] 화면 `history.ts` — 어시스턴트 메시지의 `activity` 에서 `evidence`(도구 · 인자 · 결과), 두 번 담기(글 먼저 · 남는 몫에 근거)
- [x] 포털 `ChatHistoryMessage.evidence` · `_history_total` 에 셈 · 챗 요청으로 넘기기(도우미 셋에는 안 넘김)
- [x] 에이전트 서버 `_history_messages` — 근거 몫(`HIST_EVIDENCE_SHARE`), 그 턴의 물음 뒤에 붙임, 오래된 근거부터 줄임 · 압축본엔 도구 이름
- [x] 시험 — 세 층 각각 · 근거 없는 이력은 종전과 같은 결과

## T3 띵킹 세션 맥락(CD-D8 — 에이전트 서버 `2db2bfd`)

- [x] `run_thinking` — 세션 블록(앞 대화 [c:N] · [a:N] + 조회 근거 [e:N]) 을 본심 프롬프트에만, 몫 `THINK_SESSION_SHARE`(문서 있을 때) · `THINK_SESSION_SHARE_SOLO`
- [x] 소집 · 예심 · 위임 검색어 = 질문 + 대화 화두(`_derive_topic`), 손잡이 `THINK_WITH_HISTORY`
- [x] 상태 줄 · 종합에 실은 수(대화 · 근거 · 뺀 것) · 좌석 한도 1800초 · `THINK_LLM`
- [x] 시험 — 본심에만 · 검색어엔 화두만 · 끈 경우 종전 · 예산

## T4 생각 표시(C2) · 답한 모델(C3)(CD-D10 — 에이전트 서버 `5d50eac` · 포털 `b4a816b`)

- [x] 에이전트 서버 — 챗 서버 스트림의 생각 조각(`reasoning`·`reasoning_content`)을 `reasoning` 사건으로, 답한 모델 · 강도 · 넘김을 턴 끝 `meta` 사건으로
- [x] 화면 — 접힌 '생각 중' 칸(이력에 안 넣음 · 영속 안 함) · 메시지 아래 모델 표시(영속)
- [x] 시험

## T5 그림(CD-D11 — chat-vision V-1~V-3, 에이전트 서버 `0b2f8b6`)

- [x] 에이전트 서버 — 그림 받는지 판정(`LLM_VISION` · `CHAT_LLM_VISION` auto|1|0, 그림이 실릴 때 탐침 — 기동 때 묻지 않는다) · 챗 턴 다중모달 메시지 · 도구 그림을 그 결과 뒤에 · 이력의 그림 · 띵킹(받으면 그림, 못 받으면 판독문 [g:N]) · 심의 · 시뮬심의 · 시험계획(판독문을 근거로, 받으면 그림도)
- [x] 포털 — 챗 입력이 그림을 받고(붙여넣기 · 파일 고르기, 긴 변 1,568px) 넘긴다 · `user_images` 주소를 그 발화에 · 이력 · 브라우저 사본 · 서버 사본(답 meta)에 주소
- [x] 시험 · 상한(장수 12 · 한 장 8MiB — 세 층 같은 수)과 알림(건너뛴 그림 · 못 읽은 그림 · 못 실은 그림)

## 수정 제안서(10-18) — PLAN 2-b

- [x] F1 도구 절단 관련도 순 · 안내대 셋(에이전트 서버 `2806672`)
- [x] F2 — 이미 고침(에이전트 서버 `19a04e8`, cae00 기준 커밋 뒤) — 다음 update-all
- [x] F3 헬스게이트 「챗 도구 절단」 · 챗 스모크 900초(포털 `9c0f795`)
- [x] F4 「앱」 검색이 허브 앱도(포털 화면 · `test_front_hub_search`)
- [ ] F5 — 관찰. cae00 에서 F1 뒤 같은 질의로 다시 잰다(사람)
- [x] K1 KooRemapper 감시 · 헬스 DB 확인(KooRemapper `7172460`)
- [x] S1 · 4-b — 요청서(`docs/followups-1017/requests.md` 4 · 5절)

## T6 문서 · 배포

- [x] `docs/chat-llm-stcx/server-setup.md` 4 · 6 · 8절(생각 기본 켬 · 강도 · 상한 · 출력 몫 · 그림 · 도구 절단) · CL-D1 ③ 뒤집힘 표시 · 에이전트 서버 README(`126a604`) · 설정 킷(`a5f6b3f`)
- [x] `docs/thinking-mode/` 에 세션 맥락 한 절 · `docs/chat-vision/` 상태
- [x] 업데이트 이력(10-18 다섯 건 — 커밋 대응 빠짐 0) · CLAUDE.md 문서 표
- [x] 전체 시험 — 에이전트 서버 2420 통과(건너뜀 1) · 포털 3106 · KooRemapper 574, 끝까지 한 번(임시 포털 + 에이전트 서버 + 그림 받는 가짜 LLM — 올림 · 다음 턴 · 새로고침 · 서버 사본 · /심의 판독 · 앱 검색), 화면 `pnpm build` · Drive(`images-to-drive.sh`), push(세 리포)
- [ ] cae00(사람) — update-all · 요청서 4절 전후 비교 · `/health`(`chat_llm` · `tool_cut` · `vision`) · 그림 한 장 올려 보기
- [x] dev(사용자 확인 '그래') — 포털 10-17 23:42 · 에이전트 서버 10-18 00:02(그림 · 탐침 `0e9de92`), 다시 01:28(같은 소속 열람 `9d4c931`) — 리스너 pid 시작 시각으로 확인
