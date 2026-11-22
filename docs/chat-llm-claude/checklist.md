# 웹 챗을 Claude API 로 — 할 일

계획은 [PLAN.md](PLAN.md), 결정은 [context-notes.md](context-notes.md).

## 포털
- [x] 권한 항목 표지 `grant_only` — `"*"` · 관리자 전권이 펼치지 않는다 · 함의로 열지 않는다(검사) · 관리자도 개별 허가로
- [x] 권한 표에 `feat:chat-claude`(웹 챗 Claude 모델)
- [x] 시험 둘 · 변이 다섯(별표 · 관리자 전권 · 관리자 개별 허가 · 함의 검사 · 표지 읽기)
- [x] 업데이트 이력

## 에이전트 서버
- [x] Claude 추가 챗 모델(`CLAUDE_CHAT_*`) · 요청마다 고르기 · 넘김 · 캐시 열쇠 · /health — 에이전트 서버 `b65a19c`(main `01a7852`)
- [x] 생각 블록을 받은 그대로 되돌림 · temperature 를 보내지 않음 · 거절 표시 · 서버 쪽 대체 모델
- [x] 시험(진짜 SSE 꼴 가짜 전송) 27 · 변이 18 · 기본 박스 바이트 동일 · 전체 회귀 꾸러미 없이 4,919 · 있게 4,942

## dev
- [x] 키 파일(`~/.config/hwax/anthropic.key`, 0600 — 사용자가 「클립보드에 키 있어」 로 다시 지시해 세션이 꼴만 확인해 넣음 · 값은 어디에도 찍지 않음, 11-22)
- [x] 서비스 venv 에 `requirements-anthropic.txt` 설치(사용자 확인 11-22 — langchain-core 판 그대로)
- [x] `.env` 줄 — `CLAUDE_CHAT_MODEL=claude-opus-5-5` · `CLAUDE_CHAT_API_KEY_FILE` · `CLAUDE_CHAT_FOR=all`(재기동 — 키 파일이 없어 「꺼짐 · 키 파일이 없다」 로 뜸, 파일이 생기면 한 번 더 띄운다)
- [x] 재기동 · 웹 챗 한 턴(2.9초 · 답 meta `models: {claude-opus-5-5: 1}`) · 사람별 LLM 토큰에 세짐(고침 `a996b69` — 기록기가 Claude LLM 에 안 붙어 있었다)

## cae00(사람 몫 — 받은 편지함)
- [ ] 키 파일 · 설치 · `.env` 의 `CLAUDE_CHAT_FOR=feat:chat-claude` · 사람에게 개별 허가 · 한 사람으로 한 턴

## 모델 · 생각 깊이 고르기(CC-8 — 사용자 요청 11-22)
- [x] 에이전트 서버 — `CLAUDE_CHAT_MODELS` · `CLAUDE_CHAT_EFFORTS` · 요청 칸 `claude_model` · `claude_effort` · 쌍마다 지어 두기 · 목록 밖은 기본 + 알림 ·
      Haiku 에는 서버 대체 모델을 싣지 않음 · 캐시 열쇠 칸 · 답 meta 에 고른 값 · `/claude-models` · 시험 열다섯
- [x] 포털 — 요청 칸 둘(꼴만 보고 옮김) · `/agent/claude-models`(Claude 대상에게만 목록) · 입력창 칸 · 답 아래 표시 · 시험 열
- [ ] dev — `.env` 에 `CLAUDE_CHAT_MODELS` 넷 · 재기동 · 고른 모델로 한 턴씩
- [ ] cae00(사람 몫) — 넓히려면 `CLAUDE_CHAT_MODELS` 를 적는다(비용 · Fable 은 30일 보존 조직만)
