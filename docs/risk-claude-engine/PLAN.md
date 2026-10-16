# 리스크 심사를 Claude 로도 돌릴 수 있게 — 계획

> 사용자 결정(2026-10-15): "일단 현행 계획대로 완료해주고, 완전 클로드 버전으로도 할 수 있게끔만 해두고, 그거는 테스트는 하지 말고 유저가 원하면 할 수 있게끔만 하자."
> 그래서 이 문서의 길은 **기본 꺼짐**이고, 켜는 것은 사용자의 몫이다. 실제 Claude 로 심사를 돌려 보는 시험은 하지 않는다 — 가짜 응답자로 배선만 확인한다(리포 규칙상 코드가 깨졌는지는 본다). 차례는 M3(GLM)를 먼저 끝내고 그 뒤다.

## 1. 무엇을 하나

지금은 Claude(MCP)가 잡을 시작·감시·읽기만 하고 판단 호출은 전부 GLM 이다(카드 대조 · 입력 결손 · 요약 · 쟁점 패널). 이 계획은 **판단 호출의 LLM 자리에 Claude 를 꽂는 길**을 하나 더 낸다. 엔진의 프롬프트 · 파서 · 보충 되묻기 · 계약, 앱의 원장 · 검증 · 완결 판정은 그대로 쓴다 — 바뀌는 것은 '누가 답을 쓰나' 뿐이다.

## 2. 모양 — 외부 응답자(external LLM)

```
리스크 앱(잡 llm=claude) ─run─▶ 포털 중계 ─▶ 에이전트 서버 card_review / 심의
                                              │ LLM 자리 = ExternalChatModel
                                              ▼
                                  과제 줄(owner 별) ◀─ MCP review_task_next / read / submit ─ Claude Code 워크플로(사용자 PAT)
```

- **에이전트 서버** — `ExternalChatModel`(LangChain 채팅 모델 꼴)이 호출을 받으면 그 메시지를 **과제**로 줄 세우고 답을 기다린다. Claude Code 워크플로가 MCP 로 과제를 집어 답을 쓰고 제출하면 그 글이 모델의 답이 되어 엔진이 평소대로 파싱·검사·보충한다. 과제는 그 잡을 시작한 사람(owner)만 집는다.
- **카드 대조 다섯 종류**(sweep · verdict · offcard · noinput · summary)는 도구 없는 단독 호출이라 그대로 맞는다. **쟁점 패널**(심의 엔진)은 좌석이 도구를 부를 수 없으므로 `tool_mode=evidence_only` 로 돈다(기존 MCP 길과 같은 등급 표지).
- **창과 출력 상한이 다르다** — GLM 은 1M 창이고 Claude 는 모델에 따라 다르다. 외부 길의 `limits`·`plan` 은 `EXTERNAL_LLM_CTX_TOKENS`·`EXTERNAL_LLM_MAX_TOKENS` 로 셈하므로 `limits_rev` 가 GLM 과 다르다 — 잡 하나 안에서 엔진을 바꾸면 셀이 처음부터 돈다(받아들인다, 문서에 적는다).
- **MCP 결과 상한** — 과제 하나의 프롬프트가 훑기면 약 12만 자라 MCP 한 응답(25,000자 안)에 안 들어간다. 과제 머리(`review_task_next`)와 본문 쪽 읽기(`review_task_read`, offset)로 나눈다. 제출도 길면 나눠 받는다.

## 3. 켜는 법과 동의(사용자 몫)

- 에이전트 서버 `.env` `EXTERNAL_LLM_ENABLED=1`(기본 0) — 꺼져 있으면 `/health.capabilities` 에 `external_llm` 이 없고 앱이 그 선택을 거절한다.
- 잡을 만들 때 `llm: "claude"` 와 `consent_external: true` — 화면·MCP 의 설명이 "이 잡의 지식카드·설계 변경 원문과, 사슬이 이어 도는 쟁점 패널·종합 요약의 입력(이 대상 전체의 등록부 행·쟁점·요약 — 다른 사람의 검토 결과도 든다)이 Claude(외부)로 나갑니다" 를 말한다(리스크 앱 `EGRESS_WARNING` — X-D7 뒤 XR-12). 동의 없이는 409. 사슬이 이어 만드는 쟁점·종합 잡은 그 선택과 동의를 물려받는다.
- Claude Code 에서 워크플로 `hwax-risk-claude` 를 돌린다(사용자 PAT 로 게이트웨이에 붙은 상태). 워크플로가 멈추면 과제가 집히지 않아 기다림 한도 뒤 잡이 `external_worker` 로 멈추고, 길잡이가 '워크플로를 다시 돌리라' 고 말한다.

## 4. 걸음

| # | 리포 | 무엇 |
|---|---|---|
| X-1 | HWAXAgentServer | `external_llm.py`(과제 줄 · `ExternalChatModel` · 기다림/답 한도 · 재시작 시 줄은 잃는다 — 앱이 인프라로 다시 낸다), card_review·plan·limits 의 `llm` 선택, 심의의 `delib_opts.llm`(evidence_only 강제), `/health.capabilities.external_llm`, MCP 도구 셋(`review_task_next` · `review_task_read` · `review_task_submit` — owner 만, 남의 과제는 없는 것과 같은 답), README 계약 절, 계약 예제 |
| X-2 | HWAXRisk | 잡 선택 `llm`(기본 glm) · 동의 · 사슬 상속 · `engine_client` 본문 · 보류 코드 `external_worker` · 길잡이 · 보고서·품질에 '판단 LLM: Claude(외부, 사용자 신고 모델)' · MCP `risk_start_job` 인자 · REST |
| X-3 | HWAXPortal | 워크플로 `infra/pipeline/hwax-risk-claude.js`(+ sync) — 과제를 집어 답하고 제출하는 고리, 동시 수·멈춤·실패 처리, 답은 엔진 프롬프트가 요구한 꼴 그대로. 워크플로 시험(가짜 MCP). 중계가 `llm` 칸을 그대로 넘기는지 시험 |
| X-4 | 게이트웨이·문서 | 에이전트 서버 MCP 새 도구가 게이트웨이 `tools/list` 에 뜨는지(프로비저닝), `server-setup-m3.md` 에 '켜는 법' 절, 업데이트 이력, CLAUDE.md 문서 표 |

## 5. 하지 않는 것

- 실제 Claude 로 심사를 돌려 보는 시험(사용량이 크다 — 전원 한 번에 입력 약 1.5억~2.4억 토큰, D-48).
- GLM 과 Claude 를 셀마다 섞는 자동 선택 · 비용 계산 · Claude API 직접 호출(키 관리가 새로 생긴다).
- 쟁점 패널 좌석의 도구 호출(외부 응답자는 엔진의 도구를 실행할 수 없다 — evidence_only 로 표시).

## 6. 위험

| 위험 | 대응 |
|---|---|
| 반출 — 카드·설계 변경 원문이 외부로 나간다 | 기본 꺼짐 + 잡마다 명시 동의 + 화면·MCP 설명 문구, 감사 행에 동의자·때 |
| 워크플로가 끊기면 잡이 끝없이 기다린다 | 기다림 한도 뒤 `external_worker` 보류(차감 없음), 길잡이가 다시 돌리라고 안내 |
| 답의 꼴이 엔진 계약과 다르다 | 엔진 파서·보충 되묻기가 그대로 걸러낸다(GLM 과 같은 그물), 워크플로 지시문이 '프롬프트가 요구한 꼴만' 을 말한다 |
| 창이 작은 모델 | 외부 길 limits 가 그 창으로 셈해 `ctx_too_small` 을 미리 낸다(GLM 길과 같은 장치) |
