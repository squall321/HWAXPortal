# 운영 현황 — 체크리스트

계획은 [PLAN.md](PLAN.md), 결정은 [context-notes.md](context-notes.md).

## M0. 계획 · 물음(dev — 11-02)
- [x] 조사(읽기만) — 이용 통계 원천 · LLM/GPU 원천 · 셋 다 근거 줄(OD-1 · OD-2)
- [x] 계획서 · 받은 편지함 물음(`../cae00-inbox/2026-11-02.md`)
- [x] 사용자 결정 — 합계도 관리자만 · 호스트 수집기(OD-4, 11-02) — 나머지는 권장 기본값
- [ ] cae00 답(받은 편지함 Q1 ~ Q12) — 사용자를 거쳐

## 이용 통계
- [ ] M1 — 포털 안 원장으로 S 지표 · 관리자 API · `/admin/usage` 화면 · `agent_audit` ts 색인 · 예열 줄 · 시험 계정 빼기 · 시험 격리 · 이력
- [ ] M2 — `usage_daily` · `usage_actor_daily`(agent_audit.sqlite 안) · lifespan 접기 · 되채우기 · 게이트웨이 `/usage-rollup` · 에이전트 서버 창구 · nginx 날마다 접기 · MCP · 심의 · RA 칸 · DAU/WAU/MAU
- [ ] M3 — 2단계 (가) 턴 종류 · 모델 (나) 날마다 PAT · 연결 수 (다) 에이전트 토큰(결정 뒤) (라) 게이트웨이 PAT 종류 · 엔진 호출 주인 · 리스크 토큰 · (정하면) 합계 공개 · 내 이용
- [ ] cae00 절차서 · 반대 검토

## LLM/GPU 현황
- [ ] M1 — 수집기(HTTP · 해석기 · sqlite · 가짜 vLLM 시험 · 라우터 해석기와 같은 결과)
- [ ] M2 — 포털 API · `/admin/llm-status` · update-all 배선(끄면 '꺼짐' 한 줄) · 이력 · 문서
- [ ] M3 — Slurm 잡 표 · 남은 때(답 뒤 · cae00 에서만 확인)
- [ ] M4 — GPU 하드웨어(dev nvidia-smi · stcx 표본은 사람이 sbatch 에 넣은 뒤 · GLM 은 그 팀이 줄 때)
- [ ] M5(선택) — 에이전트 서버 안 서버별 지연 · 오류 고리
- [ ] cae00 절차서 · 반대 검토
