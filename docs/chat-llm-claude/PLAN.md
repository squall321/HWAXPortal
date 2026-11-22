# 웹 챗을 Claude API 로 — dev 는 정본, cae00 은 지정한 사람만

> 사용자 지시(2026-11-22) — 「dev 서버는 웹챗의 LLM 을 Claude API 로 해 둬라」 에 이어 「dev 에서는 Claude API 를 정본으로 하고 cae00 에서는 선택할
> 수 있게. 운영자가 지정한 몇 사람은 Claude API 를 쓰고 그 외 사람은 기존처럼 Qwen 으로」. 결정과 까닭은 [context-notes.md](context-notes.md),
> 할 일은 [checklist.md](checklist.md).

## 무엇을

| 박스 | 누가 Claude 인가 | 나머지 |
|---|---|---|
| dev | 모두(정본) | — |
| cae00 | 운영자가 개별 허가로 `feat:chat-claude` 를 준 사람 | 지금처럼 챗 전용 LLM(stcx Qwen) → GLM |

범위는 **웹 챗 턴**(챗 ReAct · 챗 안 도구 계획 · 그 턴의 자기검증)이다. 띵킹 · 심의 · 카드 대조는 지금 LLM 그대로다.

## 어떻게

1. **포털 — 개별 허가로만 열리는 키.** 권한 표에 `feat:chat-claude`(웹 챗 Claude 모델)를 두되 `grant_only: true` — 소속의 `"*"` 와 관리자 전권에 딸려
   오지 않는다(CAEG 는 `"*"` 라 보통 키 하나로는 「몇 사람」 이 안 된다). 운영자가 관리 › 사용자에서 사람마다 준다(관리자 자신도 개별 허가로).
   포털은 요청마다 원장으로 권한을 다시 셈해 에이전트 서버에 싣는다(종전 길).
2. **에이전트 서버 — Claude 를 추가 챗 모델로.** Anthropic 공식 SDK(langchain-anthropic 위)로 짓는다 — OpenAI 호환 길로 붙이지 않는다(Claude API
   안내서). 설정 `CLAUDE_CHAT_MODEL`(비면 꺼짐) · `CLAUDE_CHAT_API_KEY_FILE`(0600 키 파일) · `CLAUDE_CHAT_FOR`(`all` | `feat:chat-claude`) ·
   effort 등. 요청마다 사람의 권한으로 고르고, 권한 칸이 없는 호출은 주지 않는다(닫힌 쪽). Claude 가 실패하면 그 박스의 기본 챗 길로 넘긴다.
   의존성은 `requirements-anthropic.txt`(선택 — 운영 박스 update-all 의 기본 설치에 넣지 않는다).
3. **키** — 사람이 0600 파일에 직접 넣는다. 서버는 기동 때 그 파일을 읽는다. 키는 추적 파일 · 로그 · /health 에 싣지 않는다.
4. **사람이 모델 · 생각 깊이를 고른다(11-22 사용자 요청 — CC-8).** 박스가 고를 수 있는 목록을 정하고(`CLAUDE_CHAT_MODELS` · `CLAUDE_CHAT_EFFORTS` —
   비면 기본 하나 · 다섯 다), Claude 로 답받는 사람은 입력창의 칸에서 고른다(이 브라우저에 기억). 목록 밖 값은 박스 기본으로 돌고 답 아래에 알린다.
   dev 는 넷(Opus 5.5 · Fable 5.2 · Sonnet 5.5 · Haiku 5.5), cae00 은 운영자가 적지 않으면 기본 하나다.

## 차례

1. 포털 키(`wt1122/chat-claude-key`) — 지음.
2. 에이전트 서버(`wt1122/claude-chat`) — 짓는 중.
3. dev — 서비스 venv 에 `requirements-anthropic.txt` 설치(사람 확인) · 키 파일 · `.env` 줄 · 재기동(통합 재기동과 함께) · 웹 챗 한 턴.
4. cae00 — 받은 편지함으로 절차(키 파일 · 설치 · `.env` 의 `CLAUDE_CHAT_FOR=feat:chat-claude` · 사람에게 개별 허가).
