# 다른 플랫폼의 화면을 챗 안에 — 할 일

계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md). 날짜는 KST.

## 에이전트 서버

- [x] 뷰어 주소 모으기(`embed_url` 표지 · `CHAT_EMBED_PATHS` 허용 목록 · 공개 주소 → 같은 출처 경로 · 위험 버림 · 턴마다 4) — 챗 턴만 — 에이전트 서버 `af17496`(`embeds.py`)
- [x] 챗 스트림이 `result` 앞에 SSE `embeds` 한 번(자기검증 감싸개를 지난다) · 시험(52 · 전체 4,486 · 변이 다섯 붉음) · dev 재기동

## 포털

- [x] 중계 — `embeds` 를 같은 규칙으로 걸러 화면에 넘기고 답 `meta.embeds` 에 남김 · 시험 — 포털 `d9e498cd`
- [x] 화면 — 경로 판정(`chatStore.isEmbedPath` — 저장 계층 시험 때문에 그 파일에) · 카드(`EmbedCard.tsx` — sandbox="allow-scripts" · 새 탭 · 크게 · 접기 · 기록은 접힌 채 · 열기 전 세션 새로 함) · 저장 · 되살리기 · 시험 — `d9e498cd`
- [x] `MCP_APPS_HOST` 기본 켬 · 시험 — 포털 `fb3da32d`(env 예시에는 없던 키라 더하지 않음 — 끄기는 박스 `backend/.env` 에 `MCP_APPS_HOST=0`)

## StepForge

- [x] 요청서(패널 꼴 — `ui://` · `_meta.ui.resourceUri` · `embed_url` 표지) · 보내기(11-05 세션 메시지) — 답 받음: 패널 둘(`0d5cb6a`, CE-7)
- [x] 포털 호환 확인(dev — 앱 표지 · 자원 · 이름 꼴 · panel_read · teardown · 세션 상한)
- [ ] 실제 포털 화면에서 두 패널 열기(사람 — 로그인 필요) · cae00 확인(받은 편지함 11-05 Q6)

## 반영

- [x] 빌드 · Drive 이미지 판 `images-20261105-092549Z`(SVG iframe 과 묶음) · dev 재기동(에이전트 09:31 · 포털 09:25 — 패널 창구가 404 → 401) · 0절 줄 · 업데이트 이력 · 받은 편지함 Q6 · CLAUDE.md · 메모리
