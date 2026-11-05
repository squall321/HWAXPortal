# 리스크 앱 화면 세션에 — 패널의 외부 사례 미연결 · 한도 초과 표지(2026-11-06)

받는 곳: HWAXRisk 화면 세션(`frontend/`). 보내는 곳: 포털 세션(사용자 결정 11-06 — 리스크 심사에서 SIREN, [PLAN.md](PLAN.md) RK-12).

## 1. 백엔드가 새로 내는 것(응답 칸)

- `GET /api/targets/{key}/panels` · MCP `risk_list_panels` 의 패널 `quality` 에 두 칸이 생길 수 있다.
  - `conn_unregistered: ["SIREN", …]` — 잡 주인이 그 외부 사례 DB 의 토큰을 포털 '외부 연결' 에 등록하지 않았거나 그쪽이 받지 않아(401) 지정 도구를 부르지 못했다.
    패널은 그대로 끝났다(그 사례가 좌석에 가지 않았을 뿐이다).
  - `conn_rate_limited: ["SIREN", …]` — 그쪽 호출 한도(429)에 걸려 그 패널에서는 더 부르지 않았다.
  - 같은 이름이 `quality.flags` 에도 든다(`"conn_unregistered"` · `"conn_rate_limited"`). 값은 표시 이름 목록이다(못 읽으면 백엔드 키 `siren`).
- 같은 `quality` 에 `case_tools`(이 패널을 띄울 때 붙인 외부 사례 도구 목록)와 `case_tools_skipped`(싣지 않은 까닭 — `claude_job` · `llm_cap` ·
  `gateway_unread`)가 생길 수 있다. 표지가 아니라 기록이다(flags 에는 들지 않는다).
- `GET /api/meta/runtime`(관리자)의 `knobs` 에 `HWAXRISK_CASE_TOOLS` — `value` 가 **목록**이다(다른 손잡이는 수 · 참거짓 · 낱말).
- 계획의 지정 도구(`budget_json.tools_planned`)는 그대로다 — 외부 사례 도구는 러너가 띄울 때 붙인다(실은 것은 위 `quality.case_tools`).

## 2. 청하는 것

1. 패널 카드(과제 화면의 패널 목록 · 쟁점 카드의 결과 칸)에 `quality.conn_unregistered` 가 있으면 이름마다 '○○ 미연결'(예: 'SIREN 미연결') 표지를,
   `conn_rate_limited` 면 '○○ 한도 초과' 표지를 보인다. 풍선 글 — 미연결은 '잡 주인이 포털 개인 토큰 › 외부 연결 에서 등록하면 다음 패널부터 실린다',
   한도 초과는 '토큰 문제가 아니다 — 그 패널에서는 더 부르지 않았다'.
2. 관리자 런타임 손잡이 표에서 목록 값(`HWAXRISK_CASE_TOOLS`)을 쉼표로 이어 보인다.

판정 · 문구 낱말은 백엔드 린터 규칙(결함 · 오류 · 실패 · 성공 같은 판단어를 쓰지 않는다)을 따른다 — 위 글은 그 규칙 안이다.
