# 챗 전용 LLM(stcx) — 체크리스트

> 계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md) · cae00 절차 [server-setup.md](server-setup.md).

- [x] C1 에이전트 서버 — 챗 전용 클라이언트(`CHAT_LLM_*`) · 호출 단위 GLM 넘김 · 생각 끔 · 챗 경로 창(작은 쪽) · 호출별 글 꺼내기 · `/health` 의 `chat_llm` · 시험 8 · 변이 8/8 · 전체 2,459 — `fd110a6`
- [x] C2 포털 update-all 3.5c — `infra/.env` → 에이전트 서버 `.env` 맞추기(없음 ○ · 빈 값 끔 · 지운 줄은 적었던 값만 끔 · 값 적기 · 모델 확인) · `.env.example` · 킷 주석 · 시험 8 · 변이 6/6
- [x] C3 cae00 절차서(server-setup.md) · 업데이트 이력 · CLAUDE.md 문서 표 — 포털 `aacc7a0` · `4fd8470` · `2d5d933`, 에이전트 서버 `fd110a6` · `51f85e3`(포털 전체 2,952 통과 + timeout --foreground 고친 뒤 관련 67 · 에이전트 서버 전체 2,459)
- [ ] C4 cae00 — `infra/.env` 두 줄 · update-all · `/health` 의 `chat_llm` · 챗 한 번 · stcx nginx 로그(사람)
- [x] C5 에이전트 서버 — 챗 서버의 '창이 모자라다' 400 만 GLM 으로 넘긴다(`ChatCtxOverflow` · 다른 400 은 그대로) · 가짜 LLM `ctx_overflow`(vLLM 0.23.0 본문) · 시험 둘 · 변이 6/6 · 전체 2,466 — `35c048b`(CL-D9)
- [x] C6 cae00 절차서 9절(Qwen 1M — 덮어쓰기 생성기 · sbatch · 시범 · rolling · 확인 · 되돌리기) — 생성기는 vLLM 0.23.0 의 실제 설정 함수로 확인
- [ ] C7 cae00 · stcx — 9절(update-all 로 `35c048b` · 덮어쓰기 · sbatch · 시범 수치 · rolling · 확인)과 CL-D9 에 시범 수치 적기(사람)
