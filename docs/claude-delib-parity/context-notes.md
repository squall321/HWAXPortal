# Claude 길 심의 기능 맞추기 — 결정과 까닭

> 계획 [PLAN.md](PLAN.md) · 체크리스트 [checklist.md](checklist.md). 앞선 결정은 [risk-claude-engine](../risk-claude-engine/context-notes.md) X-D1 ~ X-D9.

**CP-D1 막힌 것과 문을 가른다(2026-10-21 조사).** 엔진 · 포털 워크플로 · 리스크 앱을 훑어 외부 응답자 길에서 GLM 길과 다른 것을 모두
모았다. 기능 제약은 넷(좌석 자유 조회와 그 위에 얹힌 것 · 일반 심의를 워크플로가 안 맡음 · 그림 · 리스크 패널 잡)이고, 나머지는 보안 ·
동의의 문(기본 꺼짐 · 반출 동의 · 신원 · GLM 자체 에이전트 차단 · 주인마다 하나 · 이어하기는 요청마다 동의)이다. 문은 X-D5 ~ X-D7 의
반대 검토에서 실제 결함(거짓 동의 · 동의 번짐)을 막으려 세운 것이라 그대로 둔다 — 사용자 요청은 '제약된 기능' 이다.

**CP-D2 좌석 도구는 엔진이 실행한다 — 응답자는 부를 도구를 글로 적는다.** 응답자(Claude Code 워크플로)가 제 MCP 로 게이트웨이 도구를
직접 부르게 하는 길이 더 짧아 보이지만 버린다. ① 응답자의 MCP 에는 쓰기 도구도 닿는다 — 엔진의 읽기 전용 허용 목록(_FREE_ALLOW ·
_FREE_DENY · 리스크 도구 통로 · D-18 의 앞 패널 판정 차단)이 지시문 한 줄로 내려간다. ② 결과가 엔진의 근거 원장에 안 남는다 — 좌석 조회
기록이 수치 대조의 원천인데 응답자의 신고를 믿어야 한다. ③ 워크플로의 '과제 글만으로 답한다'(X-D8 ① — 지식카드 · 근거에 숨은 지시
방어)와 어긋난다. 엔진이 실행하면 응답자는 지금처럼 글만 쓰고, 도구 · 캐시 · 예산 · 결과 상한 · 감사가 GLM 길과 바이트까지 같은 자리를
지난다.

**CP-D3 두 번째 Claude 길(engine=mcp)은 고치지 않는다(10-21).** Claude Code 가 심의를 직접 도는 길(`hwax-deliberate.js` · 리스크 보충 회차
`hwax-risk-review.js`)도 좌석 도구가 없다(EVIDENCE_ONLY_NOTE). 그 길에 도구를 주려면 서브에이전트가 제 MCP 로 게이트웨이 도구를 직접
불러야 해서 CP-D2 가 버린 길(허용 목록이 지시뿐 · 근거 원장 밖 · 주입 방어와 어긋남)이 된다. 같은 기능은 엔진이 도는 Claude 길에서
얻는다 — 일반 심의는 MCP `deliberate_start`(advanced.llm=external) + 워크플로 `jobId`(C2), 리스크 Tier 패널은 패널 잡 `llm=claude`(C4).

**CP-D4 tool_mode 의 새 낱말을 만들지 않는다 — `tools`(10-21).** 계획은 `text_tools` 였지만 리스크 원장 `rr_panels.tool_mode` 는
`CHECK(tool_mode IN ('tools','evidence_only'))` 라 새 낱말은 스키마 판(v6 — M4 몫)이 든다. 소비처에게 뜻도 같다 — 좌석 호출은 엔진이
실행해 같은 원장(상태줄 · 근거 카드 · 공용 풀 · 수치 대조 · used_tool)에 남는다. 글 왕복이라는 것은 알림 카드 · 결정문 머리가 말한다.
리스크 앱의 strong 비율(engine=mcp 나 evidence_only 패널을 뺀다)은 글 왕복 패널을 센다 — 좌석이 도구를 불렀다.

**CP-D5 첫 차례에 터지면 '조회 도중 중단' 이다(10-21 실측).** `_TextReactAgent.astream` 은 입력 상태([system, human])를 먼저 흘린다.
langgraph `create_react_agent` 도 stream_mode="values" 에서 입력 상태를 먼저 흘린 뒤 모델 호출에서 터진다(가짜 모델로 확인) — 그래서
`_free_gather_one` 의 사유 글이 두 길에서 같다(`(조회 도중 중단: …)`).

**CP-D6 CALL 줄은 백틱으로 감싸도 받고, 규약 글에는 백틱을 쓰지 않는다(10-21).** 첫 규약 글이 꼴을 `` `CALL {…}` `` 로 보였는데,
모델이 그 백틱까지 옮겨 적으면 줄 맨 앞이 CALL 이 아니라 실행되지 않았다(시험이 드러냈다). 줄 앞뒤 백틱 하나는 받고 규약 글은 맨 꼴로
보인다. 줄 가운데의 CALL(산문 속)은 받지 않는다.

**CP-D7 Claude 패널 잡은 검토 잡과 같은 문을 지난다(10-21).** `runner.create_job` 이 `check_llm_choice`(JSON true 동의) ·
`resolve_job_credential`(동의한 사람의 PAT 하나 — 대상 소유자 · 서비스 계정으로 내려가지 않는다, 러너가 잡을 집을 때도 같은 함수) ·
`require_external_llm`(/health 의 external_llm) 을 차례로 본다. 러너의 패널 실행은 쟁점 잡이 이미 쓰던 길(외부 창의 브리프 · delib_opts
llm/consent/target_key · llm_mismatch · 보류 external_worker)이라 고치지 않았다. 동시 수는 죄지 않는다 — 워크플로의 일꾼 수(기본 4)가
받는다. 감사 행은 Claude 패널 잡만(동의 기록), GLM 패널 잡은 종전대로 없다. 입구가 살아 있는 같은 Tier 잡을 돌려줄 때 판단 LLM 이 다르면
`differs: ['llm']`(검토 잡과 같다 — 바꾸지 않는다). 통합 보고서 `[패널]` 줄에 외부 응답자 패널만 `llm=external` 을 붙인다 — 붙이지
않으면 Claude 가 판정한 패널이 GLM 패널과 같은 줄로 남는다.

**CP-D8 조회 실패 경고에는 cause 를 싣지 않는다(10-21).** 외부 응답자 한도(external_worker_absent 등)로 좌석 조회가 끊기면
`free_gather_failed` 경고의 글에 그 코드가 실린다(`ExternalLLMError: external_worker_absent: …`). 프레임 칸 `cause` 는 싣지 않는다 —
앱이 가르는 것은 의장 실패(error)의 cause 이고, 좌석 유실 · 의장 실패에는 종전대로 실린다. 조회 실패 뒤의 발언 과제가 같은 한도로 곧바로
끝나 좌석 유실(cause 있음)로 이어진다.

**CP-D9 심의 메뉴에 외부 창의 한도를 따로 싣는다(10-21 — C5).** 외부 심의는 근거 · 사람 의견 상한을 외부 창에서 유도하는데 MCP
`deliberate_jobs` 의 `limits` 는 이 서버의 LLM 창(1M) 값뿐이었다. 길이 열린 서버에서만 `limits_external`(ctx_tokens · evidence_* ·
human_note_chars — `/health.external_llm.evid_budget` 과 같은 셈)을 더한다. 꺼진 서버의 응답은 종전 그대로다.

**결과(10-21).** 엔진 `82c8f37`(그림 상태 줄) · `235e493`(글 왕복 조회) · `63554c0`(과제 머리 job_id) · `e436d15`(메뉴 limits_external)
올림. 리스크 앱 `3b6e42e`(보고서가 엔진 tool_mode 를 따른다 · 계약 사본) · `ecad8c8`(Tier 패널 잡 Claude). 포털 워크플로 `d4f15de`(jobId ·
CALL 줄 답 지시). 엔진 시험 2,482 + 루트 83(글 왕복 단위 시험 15), 리스크 앱 3,393(xfail 4), 포털 워크플로 37 · 중계 재생 · 계약 122. 변이
엔진 37개(글 왕복 27 · 잡 id 6 · 그림 1 · 메뉴 3) · 리스크 앱 14개 모두 잡힘(살아남은 둘 — 살아 있는 Claude 잡의 판단 LLM 칸 · 보고서 쟁점
줄의 길 — 은 시험을 더해 잡았다). 실제 Claude 로는 돌리지 않았다(사용자 결정 10-15).
