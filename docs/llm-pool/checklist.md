# LLM 서버 둘 나눠 쓰기 — 체크리스트

> 차례: 리스크 심사 M3 를 올린 바로 뒤(사용자 결정 10-15). 근거는 PLAN.md · context-notes.md.

- [x] 시작 — 열린 물음 둘(라우터 자리 · …136 의 모델·창이 …137 과 같은가)을 사용자에게 — 10-15 cae00 · 같다(LP-D5·D6)
- [ ] L-1 라우터 · `llm-router.sh` · 매니페스트 항목 · `services.py`(`if_env` · `fp_git`) · 시험(가짜 vLLM 둘 — 고르기 · 붙임 · 넘김 · 스트림 · 끊김 전파 · 한쪽 죽음 · 다시 읽기)
- [ ] L-2·3 `lib/llm-pool.sh` · update-all 1i(기동 → 답할 때만 사본 바꾸기 · 백업 · 되돌리기) · `update-sites` 미룸 · `apply-envs` 새 키 · §6 한 줄 · `infra/.env.example` · 시험
- [ ] L-4 절차서의 동시 수 세 줄(자동 아님 — LP-D7)
- [ ] L-5 반대 검토 · 변이 검사
- [ ] L-6 절차서(cae00) · 업데이트 이력 · push · Drive(포털)
