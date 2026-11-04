# 논문 업로드 중계 — 할 일

계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md). 날짜는 KST.

- [x] 조사 — 코퍼스 · AIDataHub 논문 레코드 · 끊긴 중계(PI-1)
- [x] PaperIngest — 당기기 move 모드 · dev 한 틱 · 문서(`dc51ccb` · `4a6f5c7`, 시험 다섯)
- [x] dev — Drive 자리 `ApptainerImages:paper-ingest/from-cae00` · cron 30분(`~/paper-ingest-relay.log`) · cron 환경으로 한 틱(표식 섬)
- [ ] cae00 — 송출 cron(move)을 건다([server-setup.md](server-setup.md))
- [ ] 첫 실제 업로드로 끝까지 — cae00 송출 줄 → dev 인입 → 논문 레코드 → 다음 날 cae00 병합 뒤 챗에서 찾힘
- [ ] 후속 — `erag export-papers` 에 새것만 고르는 칸(지금은 전체를 다시 내고 AIDataHub 가 같은 것을 건너뛴다 — 편 수가 늘면 느려진다, ExpertAgents 몫)
