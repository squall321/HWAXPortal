# 리스크 앱 웹 — Tier 패널 잡에 '판단 LLM: Claude' 를 다는 요청 (프론트 세션 몫)

> 배경 [PLAN.md](PLAN.md) C4 · 결정 [context-notes.md](context-notes.md) CP-D7. 백엔드(리스크 앱 API · MCP)는 10-21 에 받도록 바뀌었다 —
> 화면만 남았다. 리스크 앱 `frontend/` 는 다른 세션이 맡으므로 여기서는 고치지 않는다.

## 1. 무엇이 바뀌었나 (API)

`POST /api/targets/{target_key}/jobs` 의 패널 잡 본문(`mode: "panels"`, `tier` 필수)이 검토 잡과 같은 두 칸을 받는다.

| 칸 | 값 | 뜻 |
|---|---|---|
| `llm` | `"glm"`(없음과 같다) · `"claude"` | 판단 LLM. `claude` 면 패널의 좌석 · 의장 호출이 그 사람의 Claude Code 워크플로(`hwax-risk-claude`)로 간다 |
| `consent_external` | JSON `true` 만 | 반출 동의 — 사람이 아래 경고를 보고 동의했을 때만 보낸다. 글자 `"true"` · `1` 은 거절된다 |

거절 · 응답 —

- 422 `consent_external_required` — `llm: "claude"` 인데 `consent_external` 이 JSON `true` 가 아니다.
- 422 `pat_unavailable` — 동의한 사람(지금 로그인한 사람)의 포털 PAT 가 없다. Claude 잡은 대상 소유자 · 서비스 계정의 PAT 로 내려가지 않는다.
- 409 `external_llm_unavailable` — 에이전트 서버가 외부 응답자 길을 열지 않았다(기본 꺼짐).
- 성공 응답에 `llm: "claude"` · `consent_external: {by, at, source}` 가 더해진다(GLM 잡은 종전 모양 그대로).
- MCP `risk_start_job` 은 같은 Tier 의 살아 있는 잡을 돌려줄 때 판단 LLM 이 다르면 `differs: ["llm"]` 을 싣는다. 웹 REST 는 종전대로 중복
  검사 없이 부를 때마다 잡을 만든다 — 화면이 살아 있는 잡을 보이고 있으면 그 잡의 판단 LLM 을 함께 보인다.
- 진행판 `GET /api/targets/{key}/coverage` 의 `job`(패널 잡) — Claude 잡이면 `llm` · `consent_external`(· `llm_mismatch`) 칸이 붙는다.

## 2. 화면에 바라는 것

1. 패널 잡 만들기(Tier A · B · C)에 '판단 LLM' 선택 — 기본 이 박스의 LLM(GLM), 다른 하나는 Claude. 검토 잡 만들기에 이미 있는 선택과 같은
   모양 · 같은 문구를 쓴다.
2. Claude 를 고르면 반출 경고를 보이고 동의 체크를 받는다 — 체크해야 `consent_external: true` 를 보낸다(미리 체크해 두지 않는다). 경고 글은
   검토 잡의 것(`review_runner.EGRESS_WARNING`)에 '패널 잡은 그 패널의 브리프 · 좌석 조회 결과' 를 덧붙인 뜻이면 된다.
3. 만든 뒤 — 잡을 만든 사람이 자기 Claude Code 에서 `hwax-risk-claude` 워크플로를 `targetKey` 로 돌려야 나아간다는 안내(검토 잡과 같은
   안내). 워크플로가 없으면 잡이 보류 `external_worker` 로 멈춘다.
4. 진행판 — 패널 잡 줄에 `llm: claude` 면 'Claude' 배지(검토 잡 줄과 같은 배지).

## 3. 하지 않아도 되는 것

- 패널 결과 화면의 좌석 도구 표시는 그대로 둔다 — 글 왕복이어도 좌석 조회가 GLM 패널과 같은 이벤트 · 같은 칸으로 온다.
