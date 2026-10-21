# 심의를 Claude 길로 돌려도 GLM 길과 같은 기능을 — 계획 (2026-10-21)

> 사용자 요청(10-21): "클로드로 할 때는 제약된 기능이 있었다면 그것도 할 수 있게끔 하자 — 심의 기능에서."
> 앞선 맥락은 [risk-claude-engine](../risk-claude-engine/PLAN.md)(외부 응답자 길, X-1 ~ X-4)이다. 그 계획 5절이 '하지 않는 것' 으로
> 남긴 좌석 도구 호출을 이번에 연다. 결정 [context-notes.md](context-notes.md) · 체크리스트 [checklist.md](checklist.md).

## 1. 지금 막힌 것 (조사 10-21 — 엔진 · 포털 워크플로 · 리스크 앱)

| # | 막힌 것 | 까닭 | 고칠 것 |
|---|---|---|---|
| C1 | **좌석 자유 조회(도구)** — 외부 길이면 `free_tools` 를 0 으로 강제한다(evidence_only). 그 위에 얹힌 것이 함께 닫힌다 — 웹 검색(search_web · search_scholar), 좌석이 스스로 부르는 agent_search, 리스크 도구 통로(risk_get_diff · get_record_sections · RA · VOC · KG · 물성 DB …)와 고정 · 조회 지침, 좌석끼리 나누는 공용 조회 풀, 수치 대조의 원천(좌석 조회 기록). 좌석 계약의 '1R 발언 전 도구를 1개 이상 실제 호출' 도 지킬 수 없다 | 외부 응답자는 '글 과제 → 글 답' 이라 LLM 에 도구를 묶을 수 없다(`ExternalChatModel.bind_tools` 가 예외, 도구를 묶는 자리는 좌석 자유 조회의 `create_react_agent` 하나) | **글 왕복 ReAct** — 엔진이 좌석의 도구 목록을 과제에 싣고, 응답자가 `CALL {json}` 줄로 부를 도구를 적으면 **엔진이** 그 도구를 실행해 결과를 다음 과제로 보낸다. 실행은 늘 엔진이다 — 허용 목록 · 캐시 · 예산 · 결과 상한 · 감사 · 근거 원장이 GLM 길과 같다 |
| C2 | **일반 심의**(리스크 대상이 없는 MCP `deliberate_start`)는 배포된 워크플로가 답하지 않는다 | 워크플로는 제 대상(target_key)의 과제만 답하고(X-D6 '맡은 과제만'), 일반 심의 과제에는 대상이 없다 | 심의 잡 id 를 과제 머리에 싣고 워크플로가 `jobId` 로 맡는다(맡은 과제만 원칙 그대로 — 대상 대신 잡) |
| C3 | **그림** — 외부 길은 그림 조각을 말없이 버리는데 상태 줄은 '그림 N장을 싣는다' 고 말한다 | 과제가 글뿐이다. 판독문(그림을 글로 옮긴 것)은 근거로 실려 응답자에게 간다 | 상태 줄을 바로잡는다(판독문으로 간다고 말한다). 그림 자체를 보내는 길은 입구가 생길 때 — 지금 외부 심의에 그림을 싣는 입구가 없다(포털 화면은 외부 선택이 없고 MCP · 리스크 앱은 그림을 안 보낸다) |
| C4 | **리스크 앱 티어 패널 잡**(mode=panels)은 llm=claude 를 거절한다 — Claude 는 카드 대조 잡(reviews)과 그 사슬(쟁점 · 종합)에만 | X-2 의 범위(M3 검토 흐름) 결정 — 패널 잡은 이 박스의 LLM 으로 돈다 | 패널 잡도 llm=claude · 동의 · 그 사람 PAT 로. 엔진이 알린 tool_mode 를 적는다 |
| C5 | 작은 것 — MCP `deliberate_jobs` 안내의 한도가 GLM 창 기준 · 의장이 evidence_only 를 모른다 · 도구가 없는데 '도구로 더 확인하라' 는 문구 | | C1 뒤 대부분 사라진다. 남는 MCP 안내를 외부 창 기준으로 |

**그대로 두는 것 — 기능 제약이 아니라 보안 · 동의의 문이다.** 기본 꺼짐(`EXTERNAL_LLM_ENABLED`), 잡마다 반출 동의(`consent_external`),
호출자 신원, 이 박스의 GLM 챗 · 심의 에이전트가 외부 길을 스스로 열지 못하는 것(X-D5 · X-D6 — 지식카드에 숨은 지시로 거짓 동의가 서지
않게), 주인마다 외부 심의 하나, 이어하기는 llm 을 이어받지 않는 것(요청마다 동의). **고칠 수 없는 것** — GLM 손잡이(온도 ·
DELIB_TIMEOUT_S), 토큰 사용량(응답자가 알리지 않는다), 생각 깊이(Claude 는 그 세션의 effort 를 따른다).

## 2. 설계 — C1 글 왕복 ReAct

```
좌석 조회 차례 ── 과제(시스템: GLM 조회 지시 + 글 도구 규약 + 도구 목록 / 사람: 주제 · 논의 · 앞 차례 결과) ──▶ Claude 워크플로
      ▲                                                                                              │
      └── 엔진이 실행한 결과(ToolMessage) ◀── 엔진이 CALL 줄을 읽어 그 좌석 도구를 실행 ◀── "CALL {...}" 줄 답
```

- **엔진이 실행한다.** 대안(응답자가 제 MCP 로 직접 부르기)은 버린다 — 응답자의 MCP 에는 쓰기 도구도 닿아 허용 목록이 지시뿐이 되고,
  결과가 엔진의 근거 원장에 안 남아 수치 대조가 응답자의 신고를 믿어야 하며, 워크플로의 '과제 글만으로 답한다'(주입 방어, X-D8 ①)와
  어긋난다. 엔진이 실행하면 응답자는 지금처럼 글만 쓴다 — 워크플로를 고칠 것이 없다.
- `_text_react_agent(llm, tools)` 가 `create_react_agent` 와 같은 `astream` 꼴(도구 호출을 단 AIMessage · ToolMessage)을 낸다 — 그래서
  `_free_gather_one` · 근거 카드 · 공용 조회 풀 · 수치 대조 · 리스크 앱의 좌석 `used_tool` 이 바꾸지 않고 그대로 쓴다.
- 과제 한 차례 — 시스템은 GLM 조회 지시 그대로에 글 도구 규약(한 줄에 하나 `CALL {"tool": "<이름>", "args": {…}}`, 한 번에 남은 예산까지,
  끝은 '조회 요약:' 또는 '조회 불필요')과 도구 목록(이름 · 설명 · 인자 JSON 스키마 — 좌석별 추림 `_tools_for_seat` 의 결과)을 더한다.
  사람 글은 GLM 조회 사람 글에 앞 차례의 호출과 결과를 잇는다.
- 예산 — 호출 합은 `tool_budget`(1~6), 차례는 예산 + 1. 넘친 줄 · 모르는 도구 · 깨진 줄은 실행하지 않고 그 사실을 결과로 돌려준다.
- 표지 — 외부 실행 카드 · 결과 프레임 · 잡 기록의 `tool_mode` 가 `evidence_only` 에서 `tools`(좌석이 도구를 불렀다 — 리스크 원장과 같은
  말, CP-D4)로. 글 왕복이라는 것은 알림 카드 · 결정문 머리가 말한다. 호출자가 `free_tools=0` 이거나 쓸 조회 도구가 하나도 없으면 종전대로
  evidence_only 다.
- 비용 · 시간 — 좌석마다 조회 과제가 2~3개 더 든다(사람 속도의 워크플로). 받아들인다 — 끄려면 `free_tools=0`.

## 3. 걸음

| # | 리포 | 무엇 | 상태(10-21) |
|---|---|---|---|
| P1 | HWAXAgentServer | C1 — 글 왕복 ReAct · 외부 길의 free_tools 강제 해제 · 표지(tool_mode tools) · 문구 · 시험(가짜 일꾼이 CALL 줄로 답한다) · 변이 | 끝 · 올림 `235e493` |
| P2 | HWAXAgentServer · HWAXPortal | C2 — 심의 잡 id 를 과제 머리에 · 워크플로 `jobId` · 시험 | 끝 · 엔진 `63554c0` · 워크플로 `d4f15de` |
| P3 | HWAXAgentServer | C3 — 외부 길 상태 줄(그림은 판독문으로) · 시험 | 끝 · 올림 `82c8f37` |
| P4 | HWAXRisk | C4 — 패널 잡 llm=claude(동의 · 그 사람 PAT · external_worker 보류) · 엔진 tool_mode 를 받아 적기 · 시험 | 끝 · 리스크 앱 `3b6e42e` · `ecad8c8` |
| P5 | 세 리포 문서 | C5 MCP 안내(심의 메뉴 `limits_external` — 엔진 `e436d15`) · README 외부 응답자 절 · risk-claude-engine PLAN 5절 고침 · 업데이트 이력 · CLAUDE.md | 끝 |

화면 — 리스크 앱 웹의 패널 잡 만들기에 Claude 선택을 다는 것은 프론트 세션 몫이다(API · MCP 는 받는다) — [frontend-request.md](frontend-request.md).

## 4. 하지 않는 것

- 실제 Claude 로 돌려 보는 시험 — 사용자 결정(10-15 '테스트는 하지 말고 유저가 원하면') 그대로, 가짜 일꾼으로 배선만 본다.
- 1절의 보안 · 동의 문을 여는 것.
- **두 번째 Claude 길**(Claude Code 가 심의를 직접 도는 `hwax-deliberate.js` · 리스크 보충 회차 `hwax-risk-review.js` — engine=mcp)의 좌석
  도구 — 그 길에서 좌석이 도구를 부르려면 응답자가 제 MCP 로 직접 불러야 해서 CP-D2 가 버린 길이다. 같은 기능은 엔진이 도는 Claude 길로
  얻는다 — 일반 심의는 MCP `deliberate_start`(advanced.llm=external) + 워크플로 `jobId`(C2), 리스크 Tier 패널은 패널 잡 llm=claude(C4)
  (CP-D3).

## 5. 사람 몫

- dev 에이전트 서버 재기동(사용자 확인 뒤) · cae00 은 `update-all` 이 엔진 · 리스크 앱 · 포털 워크플로 사본을 함께 올린다. 외부 응답자 길은
  기본 꺼짐이라 켜지 않은 박스에서는 바뀌는 것이 없다(켜는 법 — `docs/risk-review-redesign/server-setup-m3.md` 8절).
- 켠 박스에서 Claude Code 의 `hwax-risk-claude` 워크플로를 다시 받아야 CALL 줄 답 지시가 실린다(사본 `.claude/workflows/` 는 sync).
