# HE팀 운영자 박스 덧씌우기 — 할 일

계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md). 날짜는 KST.

## 포털

- [ ] `infra/personas/he_team.py` — 기본 + 덧씌우기 합치기 · 지문 · 상태(표준 라이브러리만)
- [ ] `sync-he-personas.py` — 합친 정의로 · 미리보기 · `--check` 에 덧씌우기 줄
- [ ] `agent_guard.py` — 합친 정의의 `apps` 로 허가 검사 · 두 파일의 바뀐 시각으로 다시 읽기
- [ ] `.gitignore` 에 `infra/personas/he-team.local.json`
- [ ] update-all — `--check` 의 덧씌우기 줄 올리기 · 관문 줄에 덧씌우기 상태 · 목록 밖 쓰기 안내 글
- [ ] 시험 — 합치기 꼴 · 깨진 덧씌우기 · 동기화 · 허가 검사 · 시험 격리(박스 파일을 읽지 않는다)
- [ ] 포털 전체 시험 · 병합 · push

## 에이전트 서버

- [ ] `_confirm_lists` — 덧씌우기도 읽고 합친다 · 바뀐 시각 열쇠에 둘 다 · `/health` 에 상태 · 지문
- [ ] conftest 격리 — 덧씌우기 경로도 '없음'
- [ ] 시험 — 더함 · 뺌 · 깨짐 · 다시 읽기 · 포털 `he_team.py` 와 같은 합친 정의(형제 리포가 있을 때)
- [ ] 전체 시험 · 병합 · push · dev 재기동(도는 심의 · 켜질 남의 커밋 먼저 본다)

## 문서 · cae00

- [ ] server-setup — 만드는 법 · 고치는 법 · 확인 · 고치기 전 판 남기기
- [ ] request-1030 `server-setup.md` 0절 줄 · 업데이트 이력 · CLAUDE.md(규칙 · 문서 줄) · org-chart D-4 에 가리킴
