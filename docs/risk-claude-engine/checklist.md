# 리스크 심사 Claude 길 — 체크리스트

> 차례: M3(GLM) 완료 뒤. 실제 Claude 로 돌리는 시험은 하지 않는다(사용자 결정 10-15). 근거는 PLAN.md · context-notes.md.

- [ ] X-0 시작 — 닻 다시 찾기(card_review 의 `delib_llm`·`ainvoke`·`bind(max_tokens)`, 심의의 LLM 자리·`tool_mode`, 에이전트 서버 MCP `FastMCP` 와 신원, 앱 `engine_client.run_body`·잡 params·사슬 상속)
- [ ] X-1 에이전트 서버 — `external_llm.py` · `llm` 선택(run·plan·limits·심의) · `/health.capabilities.external_llm` · MCP 도구 셋(owner 만, 쪽 나누기) · README 계약 · 계약 예제 · 가짜 응답자 시험 · 변이 검사
- [ ] X-2 리스크 앱 — 잡 선택 `llm` · 동의 · 사슬 상속 · 보류 `external_worker` · 길잡이 · 보고서·품질 표기 · REST·MCP 인자 · 시험 · 변이 검사
- [ ] X-3 포털 — 워크플로 `hwax-risk-claude.js` + sync · 워크플로 시험(가짜 MCP) · 중계가 `llm` 을 넘기는지
- [ ] X-4 배선·문서 — 게이트웨이 `tools/list` 에 새 도구 · `server-setup-m3.md` '켜는 법' · 업데이트 이력 · CLAUDE.md 문서 표
- [ ] 반대 검토 1라운드(가짜 응답자로 — 반출 동의 우회 · 남의 과제 집기 · 끝없는 기다림 · 꼴 어긋남)
- [ ] push(엔진·앱·포털) — 기본 꺼짐 그대로
