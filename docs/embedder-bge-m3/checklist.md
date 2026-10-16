# 임베더 BGE-M3 전환 — 체크리스트

> 계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md).

- [ ] B0 정확 범위 검색(AIDataHub `5507c68`) 재측정 · 올림 · 문서(`ko-search-baseline.md` 고친 뒤 절)
- [ ] B1 AIDataHub 코드 — `bge_m3` 임베더 · 슬롯 둘(네 표의 `*_m3 halfvec(1024)` 열 · 이행) · 청크 백필(키셋 · 청크 커밋 · advisory lock · 이어하기 · 슬롯별) · 읽기 슬롯(설정 한 줄) · `/api/embed` 모델 표지 · 시험
- [ ] B2 dev 이행 · v2 백필(GPU) · HNSW 색인(CONCURRENTLY)
- [ ] B3 견주기 — v1 대 v2, 같은 평가셋(좌석 · 전역), 지연 포함
- [ ] B4 소비처 — 포털 대화 검색 모델 표지 + 다시 색인 · 에이전트 서버 도구 벡터 캐시 서명
- [ ] B5 dev 전환 · 재기동 · 다시 재기
- [ ] B6 cae00 절차서 — 모델 받기(model-to/from-drive 에 bge_m3) · 갱신 · merge 로 v2 벡터 · 전환 한 줄(사람)
- [ ] B7 v1 정리(나중 — 한동안 돌려 본 뒤)
- [ ] 업데이트 이력 · CLAUDE.md 문서 표
