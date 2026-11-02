# 보고서에 도구 그림 싣기 — 체크리스트

> 계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md). 가지 — 포털 `wt1102/figures` · 에이전트 서버 `wt1102/figures`(올리지 않음).

## 포털

- [x] DocForge 배달의 RA 올리기를 `RaSession` 하나로 떼기(배달 동작은 그대로 — 기존 시험 그대로 통과)(RF-3)
- [x] `POST /agent/figures/to-report` — 게이트웨이 계약(RF-1 · RF-2 · RF-4 ~ RF-8)
- [x] `POST /agent/figures/upload` — 에이전트 서버용 올리기만(RF-1)
- [x] 시험 — 가짜 RA · 자격 · 읽기 전용 거절 · 꼴 · 크기 · sha256 · RA 오류 · 칸을 버린 RA · 동시 호출
- [x] 계약 시험 — 에이전트 서버의 `report_figures.attach` 를 진짜 포털 앱에 물린다(RF-15)
- [ ] 포털 전체 시험

## 에이전트 서버

- [x] `report_figures.py` — 그림 줄 찾기 · 그 사람 PAT 로 올리기 · 자리 표지 · 그림 칸 · 셈(RF-9 ~ RF-12)
- [x] `/보고서`(`run_report_save`) 에 잇기 — 결과 사건 `figures`
- [x] 심의 보고서(새 보고서 · 이어붙이기)에 잇기 — outcome `figures` · 결정문 끝 안내
- [x] 잡 원장이 outcome 의 `figures` 를 `report_figures` 로 접고 `deliberate_result` 가 낸다
- [x] 시험 — 단위 · `/보고서` · 심의(웹 · PAT 없는 잡)
- [ ] 에이전트 서버 전체 시험

## 마무리

- [ ] 반대 검토(사본에서) — 신원 · 조용히 사라지는 그림 · 크기 · 꼴 · RA 오류 길, 재현한 것만 고침
- [ ] 결정 기록(RF-*) 마감

## 하지 않은 것(다음 몫)

- [ ] 반영 — push · 병합 · 재기동(에이전트 서버 · 포털)은 사람 몫이다
- [ ] 업데이트 이력(`docs/changelog.md`) 항목 — 올리는 세션이 쓴다
- [ ] CLAUDE.md 문서 표 한 줄 — 올리는 세션이 더한다
- [ ] `/ai-data-hub/attachments/…` 그림(AIDataHub 첨부)은 아직 싣지 않는다(RF-13)
