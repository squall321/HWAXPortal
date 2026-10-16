# 임베더 BGE-M3 전환 — 체크리스트

> 계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md).

- [x] B0 정확 범위 검색(AIDataHub `5507c68`) 재측정 · 올림 · 문서(`ko-search-baseline.md` 고친 뒤 절 `d99ddc9`) — 좌석이 받는 것 0.617→0.667
- [x] B1 AIDataHub 코드 — `bge_m3` 임베더 · 슬롯 둘(네 표의 `*_m3 halfvec(1024)` 열 · 이행) · 청크 백필(키셋 · 청크 커밋 · advisory lock · 이어하기 · 슬롯별) · 읽기 슬롯(설정 한 줄) · `/api/embed` 모델 표지 · 시험 — 합침 · 올림 `e036812`(EM-D10)
- [ ] B2 dev 이행 · v2 백필(GPU) · HNSW 색인(CONCURRENTLY)
  - [x] 이행 0032(dev, 09:27 UTC) · 작은 표 셋 m3 백필(9분)
  - [x] HDD 캐시 데우기(EM-D11) · 절차서 `29c9c38`
  - [ ] 절 1,090,531 m3 백필(약 2시간) · 인앱 v1 스윕 214,837
  - [ ] m3 HNSW 색인 · `AIDH_EMBED_FILL=v1,m3` · 재기동
- [ ] B3 견주기 — v1 대 v2, 같은 평가셋(좌석 · 전역), 지연 포함 — v1 도 같은 DB 에서 다시 잰다(EM-D12)
- [x] B4 소비처 — 포털 대화 검색(응답 모델을 표지로 · 모델별 하한 · 재지 않은 모델은 거르지 않고 알림, 시험 4 · 변이 4/4) · 에이전트 서버 도구 벡터 캐시(공간 = 모델 · 차원, 에이전트 서버 `76f9557` · 변이 2/2) — BGE-M3 하한은 B5 에서 잰다
- [ ] B5 dev 전환 · 재기동 · 다시 재기
- [ ] B6 cae00 절차서 — 모델 받기(model-to/from-drive 에 bge_m3) · 갱신 · merge 로 v2 벡터 · 전환 한 줄(사람)
- [ ] B7 v1 정리(나중 — 한동안 돌려 본 뒤)
- [ ] 업데이트 이력 · CLAUDE.md 문서 표
