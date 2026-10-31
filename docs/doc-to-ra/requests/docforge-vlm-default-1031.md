# DocForge `vlm` 기본값 — 사용자 결정 10-31 A19 와 ARCHITECTURE §3 의 'M3 부터 true'(요청 · 2026-10-31)

| 항목 | 내용 |
|---|---|
| 받는 곳 | DocForge 세션 |
| 근거 | 사용자 결정 10-31 A19 (A)([triage-1031](../../leftovers-1017/triage-1031.md) 표 A) — [PLAN](../PLAN.md) §12-8 '그림 caption 에 짧게 + 아래 rich_text 에 전문, 기본 끔' · [context-notes](../context-notes.md) DF-D25 |
| 대조한 판 | DocForge main `9eb9a52` · 포털 이 가지. DocForge 는 읽기만 했다. |

## 1. 어긋난 곳

- 앱 옵션 `vlm` 의 기본은 지금 false 다 — MCP `docforge_convert(…, vlm: bool = False, …)`(그 리포 `docforge/mcp_server.py:66`) · REST
  (`docforge/rest.py:30`).
- 그 리포 문서는 M3 부터 true 로 바꾼다고 적었다 — `docs/ARCHITECTURE.md:40`(§3 잡 옵션 표의 `vlm` 줄 '지금 기본 false · M3 부터 true').
- 사용자는 10-31 에 기본 끔으로 정했다(A19 — PLAN §12-8). M3 에서 문서대로 기본을 바꾸면 그 결정을 거스른다.
- 포털 「Report Archive — 정밀 변환」 목적지는 기본과 상관없이 켜서 맡긴다 — 목적지 이름이 '그림 판독' 이다(포털 `backend/app/agent/routes.py:1399-1400`,
  DF-D17 ②). 그래서 이 결정이 닿는 곳은 `vlm` 을 주지 않고 MCP · REST 로 바로 맡기는 쪽(개인 Claude · 챗 등)의 기본이다.

## 2. 바라는 것

- 앱의 `vlm` 기본은 false 로 둔다. 포털 목적지는 지금처럼 vlm=True 를 보낸다.
- ARCHITECTURE §3 의 `vlm` 줄을 이 결정에 맞춘다 — 예 '기본 false(사용자 결정 10-31) — 포털 정밀 변환 목적지는 켜서 맡긴다'.
- M3 에서 기본이 달라야 할 까닭이 있으면 그 까닭을 적어 포털에 알려 준다. 그때는 사용자가 다시 정한다 — 그 전에는 기본을 바꾸지 않는다.

## 3. 누가 답하나

DocForge 세션 — 문서를 고친 커밋, 또는 M3 에서 달라야 할 까닭. 포털 메인 세션이 받아 DF-D25 에 적는다.
