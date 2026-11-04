# HE팀 운영자 박스 덧씌우기 — 할 일

계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md). 날짜는 KST.

## 포털

- [x] `infra/personas/he_team.py` — 기본 + 덧씌우기 합치기 · 지문 · 상태(표준 라이브러리만)
- [x] `sync-he-personas.py` — 합친 정의로 · 미리보기 · `--check` 에 덧씌우기 줄
- [x] `agent_guard.py` — 합친 정의의 `apps` 로 허가 검사 · 두 파일의 바뀐 시각으로 다시 읽기
- [x] `.gitignore` 에 `infra/personas/he-team.local.json`
- [x] update-all — `--check` 의 덧씌우기 줄 올리기 · 관문 줄에 덧씌우기 상태 · 목록 밖 쓰기 안내 글
- [x] 시험 — 합치기 꼴 · 깨진 덧씌우기 · 동기화 · 허가 검사 · 시험 격리(박스 파일을 읽지 않는다)
- [x] 포털 전체 시험(4,452 통과) · 병합 `e871b3c1`(코드 `c5c7c2bc`) · push

## 에이전트 서버

- [x] `_confirm_lists` — 덧씌우기도 읽고 합친다 · 바뀐 시각 열쇠에 둘 다 · `/health` 에 상태 · 지문
- [x] conftest 격리 — 덧씌우기 경로도 '없음'
- [x] 시험 — 더함 · 뺌 · 깨짐 · 다시 읽기 · 포털 `he_team.py` 와 같은 합친 정의(형제 리포가 있을 때)
- [x] 전체 시험(4,429 통과) · 병합 `a3d441f`(코드 `550a42d`) · push · dev 재기동(도는 심의 0 · 켜질 남의 커밋 없음 — 11-04 06:46 UTC)

## 문서 · cae00

- [x] server-setup — 만드는 법 · 고치는 법 · 확인 · 고치기 전 판 남기기
- [x] request-1030 `server-setup.md` 0절 줄 · 업데이트 이력 · CLAUDE.md(규칙 · 문서 줄) · org-chart D-4 에 가리킴
- [x] dev 실시험 — 박스 파일을 잠깐 만들어 동기화 · 확인 관문이 같은 지문으로 읽고(재기동 없이) 지우면 기본으로 돌아오는지 본 뒤 지웠다(HO-5)
- [ ] cae00 — 이 박스에만 있는 앱의 운영자를 고칠 일이 생길 때 server-setup 1절대로 만든다(만들 일이 없으면 파일 없이 기본으로 돈다)
