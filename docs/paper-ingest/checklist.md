# 논문 업로드 중계 — 할 일

계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md). 날짜는 KST.

- [x] 조사 — 코퍼스 · AIDataHub 논문 레코드 · 끊긴 중계(PI-1)
- [x] PaperIngest — 당기기 move 모드 · dev 한 틱 · 문서(`dc51ccb` · `4a6f5c7`, 시험 다섯)
- [x] dev — Drive 자리 `ApptainerImages:paper-ingest/from-cae00` · cron 30분(`~/paper-ingest-relay.log`) · cron 환경으로 한 틱(표식 섬)
- [x] 11-06 왜 안 흘렀나 — 받은 편지함에 안 실음 · SIF 를 Drive 로 안 보냄 · 절차서 컨테이너 경로 · 송출기 dev 절대경로(PI-4 ~ PI-7, PaperIngest `e03d6d2`)
- [x] Drive 에 `paper-ingest.sif`(`e03d6d2`) 올리기 — 사람(11-06, `dist-20261106-035741Z` · latest — drive-drift ✓)
- [ ] cae00 — 앱 확인 · 새 SIF 받기 · 송출 cron(move)을 건다([server-setup.md](server-setup.md) 0 · 2절, 받은 편지함 2026-11-06 Q4)
- [ ] 첫 실제 업로드로 끝까지 — cae00 송출 줄 → dev 인입 → 논문 레코드 → 다음 날 cae00 병합 뒤 챗에서 찾힘
- [ ] 후속 — `erag export-papers` 에 새것만 고르는 칸(지금은 전체를 다시 내고 AIDataHub 가 같은 것을 건너뛴다 — 편 수가 늘면 느려진다, ExpertAgents 몫)
