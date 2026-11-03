# SP 최신판 따라가기 — 할 일

계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md). 날짜는 KST.

## 1. 0.4.72(SP `ab41cff` · 키트 2026-11-03)

- [x] SP HEAD 와 키트 판 확인 — 소비처 넷 모두 키트 2026-10-21 이었다(11-03)
- [x] 소비처 넷에 맞추기 보냄 — StepForge · DocForge · SignalForge · KooRemapper, 맡은 세션 확인(11-03)
- [x] DocForge — main `ab0861d`(배치 불요 · 거울 57 · 전체 283 통과), SL-5
- [ ] DocForge 시험장 8단계 — 자동 모드가 막아 사람 몫(명령은 SL-5)
- [x] StepForge — a78 main `b9db3d0` · `ec721ef` · `ce478ca` · Drive `dist-20261103-234515Z`(키트 판 · 시험장 8/8 · 새 읽기 셋 `onto_reach` · `onto_explode` · `onto_lineage`), SL-5
- [ ] StepForge a78 — cae00 게이트웨이 확인(받은 편지함 2026-11-04 Q3)
- [ ] SignalForge — 그 세션(`signalforge-7f`)이 사용자 답 「관계 매핑」(§2-3 — `plm_derived_from` 을 어떻게 쓸지)을 기다린다
- [x] KooRemapper — main `225da1b`(서브모듈 `ab41cff` · 키트 판 2026-11-03 · 시험장 8/8 · 백엔드 829 통과 · dev API 재기동), SL-5
- [x] 게이트웨이 — 쓰기 낱말 `repin`(`lineage_repin`) · 새 도구 일곱 판정 시험 · dev 재기동(`a3ae08b2`, SL-1)
- [x] 포털 — 허브 운영자 writes · confirm 에 바꾸는 도구 마흔둘(도구마다 `needs_tool`, SL-2) · 미리보기 대조를 관문과 같은 셈으로(SL-3) — `1dd1bd71`(병합 — `4ce5eb71`), dev 관문에 들어감(`/health` 쓰기 161 · 확인 114)
- [x] SP 에 표지 요청서 — [sp-annotations-request.md](sp-annotations-request.md)(SL-4)
- [ ] 요청서를 SP 쪽에 건넴(사용자)
- [ ] cae00 — 허브 셋 판 확인(받은 편지함 2026-11-04 Q1) → 0.4.72 로 올림([server-setup.md](server-setup.md) 1절) → 운영자 반영(2절 · 받은 편지함 Q2)
