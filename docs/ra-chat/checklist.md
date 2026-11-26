# 체크리스트 — 챗 안의 Report Archive

> 계획은 [PLAN.md](PLAN.md), 결정은 [context-notes.md](context-notes.md).

## 1. 보고서 링크 접두

- [x] 원인 확인 — RA 상대 경로 → LLM 이 그대로 옮김 → TextBlock 이 apiBase 만 붙임
- [x] TextBlock — RA 화면 경로 링크에 `/report-archive` (raLink.ts 의 함수 하나로)
- [x] 타입 검사 · 린트(빌드는 2번과 함께)
- [x] 커밋 · push

## 2. 내 부서 시작 카드

- [x] 서버 `GET /agent/ra/home` — 그 사람 명의로 `/api/me` · `/api/workspaces` → `{home, chain}`, 실패는 `{home: null, reason}`
- [x] 서버 시험(`test_ra_home.py` 36건 · RA 열기 시험 포함) — 사슬 · 개인 공간 제외 · 연결 없음 · 홈 없음 · RA 실패 · 순환 · slug 꼴 · 권한
- [x] 화면 — 한 탭에 한 번 묻기 · 인사 아래 소속 표기 · 시작 카드 맨 앞
- [x] 타입 검사 · 빌드 · 포털 전체 회귀(5,921 통과)
- [x] 업데이트 이력(changelog.yaml)
- [x] CLAUDE.md 문서 표에 한 줄
- [x] 커밋 · push
- [x] dev 반영(11-26 사용자 승인 — 포털 재기동, 빌드는 HEAD 프론트 트리와 같음 · 새 리스너가 커밋 뒤에 떴고 `/agent/ra/home` 이 401(없으면 404) — 함께 켜진 다른 세션 커밋 없음)
