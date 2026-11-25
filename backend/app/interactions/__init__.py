# 상호작용 기록 — 챗 · 심의 · 개인 Claude 의 MCP 호출 · 공유한 Claude 대화를 이 박스의 원장 하나에 모은다(docs/interaction-data contract.md)
"""포털 몫 M1 원장 · M2 공유 길 · M3 열람 · 지우기. 박스 스위치 INTERACTIONS_ENABLED(기본 꺼짐)가 꺼지면 창구는 404 이고 수집기는 돌지 않는다.

원문은 이 박스 안에만 둔다 — Drive · 조각 동기화 · 받은 편지함 · 리포로 나가는 길을 만들지 않는다(PLAN §7)."""

# 알림 문구(contract §7 초안 — 사람이 확정한다). 토큰 화면 · 웹 챗 첫 화면이 /interactions/status 로 받아 그대로 그린다(켜졌을 때만).
NOTICE = ("이 포털을 거친 대화와 도구 호출은 기록되어 품질 개선과 지식 정리에 쓰입니다. "
          "원문은 본인과 지정 분석가만 보며, 언제든 지우기를 청할 수 있습니다.")

# 남의 원문을 보는 권한 — access.yaml 의 grant_only 키(「전부」 · 관리자 전권에 딸려 오지 않는다, contract §6)
ANALYST = "feat:interaction-analyst"
