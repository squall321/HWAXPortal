# 리스크 심사 Claude 길 — 체크리스트

> 차례: M3(GLM) 완료 뒤. 실제 Claude 로 돌리는 시험은 하지 않는다(사용자 결정 10-15). 근거는 PLAN.md · context-notes.md.

- [x] X-0 시작 — 닻 다시 찾기(card_review 의 `delib_llm`·`ainvoke`·`bind(max_tokens)`, 심의의 LLM 자리·`tool_mode`, 에이전트 서버 MCP `FastMCP` 와 신원, 앱 `engine_client.run_body`·잡 params·사슬 상속)
- [x] X-1 에이전트 서버(가지 `external-llm` 24커밋 → main `faadf28` push, 10-15 — 반대 검토 2라운드(X-D5 · X-D6) · 전체 2,354 통과(스위치를 셸에 켜도 같다) · 변이 21/22 → 30/31 → 24/24 · 스위치 끈 길은 main 과 바이트째 같다 · dev 재기동 확인) — `external_llm.py` · `llm` 선택(run·plan·limits·심의) · `/health.capabilities.external_llm` · MCP 도구 셋(owner 만, 쪽 나누기) · README 계약 · 계약 예제 · 가짜 응답자 시험 · 변이 검사
- [x] X-2 리스크 앱 — 잡 선택 `llm` · 동의 · 사슬 상속 · 보류 `external_worker` · 길잡이 · 보고서·품질 표기 · REST·MCP 인자 · 시험 · 변이 검사 — 10-16 리스크 앱 main `54c4385`(반대 검토 X-D7 → 줄(lane) 나누기 · StrictBool · 재개 뒤 재시도 몫 · 패널 모델 기록 · 동의자 없으면 닫힘, 전체 3,300 통과 · 변이 30/30, GLM 출력 옛·새 대조 같음) · SIF `eee3240f` Drive · dev 교체(9418)
- [x] X-3 포털 — 워크플로 `hwax-risk-claude.js` + sync · 워크플로 시험(가짜 MCP) · 중계가 `llm` 을 넘기는지 — 중계 몫(X-3a)은 10-16 `f53858b`·`671f08d`(limits 의 ?llm · delib_opts 의 llm·consent_external StrictBool, 변이 6/6), 워크플로(X-3b)는 10-16 가지 `x3b-workflow` 에 지었다(합치기 전 — 가짜 런타임 · 가짜 과제 줄 시험 36 · 변이 31/31 · sync `--check` 사본에서 0, 결정 X-D8) · 워크플로 `hwax-risk-claude.js`(10-16 `3b517b9`~`78b992b`, 시험 36 · 변이 32/32) · 쟁점 패널 대상 열쇠 중계 `e4ebb2f`(X-D9)
  - [x] 쟁점 패널 심의 과제에 대상 표지가 없다(X-D8 ⑦) — 엔진은 심의 과제의 target_key 를 질문 머리 `[리스크심사 <과제> <대상>]` 에서만 읽는데 쟁점 질문은 `[쟁점 …]` 로 열린다. 워크플로는 대상을 가릴 수 없는 과제에 답하지 않으므로 Claude 잡의 쟁점 패널이 답 한도 뒤 external_worker 로 멈춘다 — 엔진 · 앱(· 포털 중계) 몫, 길은 X-D8 ⑦ 의 셋 중에서 고른다 — 10-16 (a) 명시적으로 싣는다(X-D9): 엔진 `53082a4` · 리스크 앱 `a111e95` · 포털 중계 `e4ebb2f`
- [x] X-4 배선·문서 — 10-16: 에이전트 서버 README 시간 한도 표에 `EXTERNAL_LLM_WAIT_S` · `EXTERNAL_LLM_ANSWER_S`(사슬 문단 포함) · 포털 env 킷 `agent-server.env` 의 시간 한도 구획(둘) · '외부 응답자' 구획(넷) — 킷 시험이 엔진 상수 · README 표 · 층(2×(기다림+답) < 논리 호출 1회)을 맞댄다(변이 6/6) · `server-setup-m3.md` 8절 '켜는 법'(엔진 · 확인 · 게이트웨이 `/tools-map` 으로 도구 셋 판정 · 잡 주인의 Claude Code · 아직 없는 것) · 5-5 보류 표의 낡은 줄(`external_worker` '이 판에 없다')을 실제 셋(`external_worker` · `external_config` · `llm_mismatch`)으로 · 7절 손잡이 표 · 업데이트 이력
- [x] 반대 검토 1라운드(가짜 응답자로 — 반출 동의 우회 · 남의 과제 집기 · 끝없는 기다림 · 꼴 어긋남) — X-1 몫은 두 라운드(X-D5 · X-D6). X-2·X-3 은 지은 뒤 다시
- [x] push(엔진·앱·포털) — 기본 꺼짐 그대로 — 엔진 `53082a4` · 리스크 앱 `54c4385`(SIF `eee3240f` Drive) · 포털 `56adf3b`(10-16)
