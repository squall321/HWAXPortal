# 운영 수정 요청 10-15 — 체크리스트

> 정본 `docs/request_1015.md` · 계획 `PLAN.md` · 결정 `context-notes.md`.

- [x] 사용자 결정 — K6-1 (나) · K6-2 (가)+업로드 막기 · K6-3 strict 기본 켬 · K3-9 (가) · K5-2 스위치 뒤 기본 끔 · K2-6 갱신 때 연장
- [x] 갈래 A 에이전트서버 — K1 → K3 → K9 → K2-5 → K8 → K7 → K5 독스트링 · 시험 · push · 재기동(dev) — 10-15 `bc6e2ff..3bba0c5` push(전체 2,203 통과 · 변이 73/74, 남은 하나는 동치), dev 재기동(9009 새 pid 확인). 요청서와 다르게 한 것 둘 — 실패 판정에 `_result_ok` 를 더함(실제 게이트웨이 실패 문구가 `_tool_text_ok` 를 빠져나감) · K5 독스트링은 본문 검색이 기본 끔이라 '켜면 본문까지'. 안 한 것 — K3 의 선택(빈 줄에서 자르기) · K9-2(요청서가 '나중에')
- [ ] 갈래 B 포털 — 프런트 묶음(K1-3·K2·K6-5·K3·K4·K5·K8) · 백엔드(K3 프록시·K2-6) · K8 정본 · 시험·lint · 빌드 · Drive · push
- [ ] 갈래 C AIDataHub(K5·K6-3·K6-4·K3-9 받는 쪽) · KooRemapper(K6-1 나·K6-2 가) · MaterialTwinWeb(K3-9 가) · 시험 · push
- [ ] 업데이트 이력(사용자 체감 + 기술)
- [ ] 운영 몫 안내(사용자) — 동기화 재개(K6-4)·데이터 정리(K6-1·K6-2)·`sim-drop-impact` data_types·K5-2 측정 뒤 켜기·stcx SmartTwinMCP 등록(K8)·sync-he-personas 미리보기·kc_sweep 재점검
