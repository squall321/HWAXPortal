# 도구 진입 구조 — 결정 기록 (2026-09-03)

MCP 도구가 351개(14 백엔드)로 늘며 "적절한 입구 찾기"가 병목이 됐다(RA 70개 입구 헤맴
실사고). 실측(감사 8,916건): 상위 10개가 호출의 58%, 상위 40개가 79%, 107개(30%)는
한 번도 안 불림 — 평면 노출의 비용을 데이터로 확인하고 3층 진입 구조로 전환.

## 구현 (①② 완료)

- **② search_tools(게이트웨이 로컬 도구)** — "하고 싶은 일 한 문장 → 도구 추천".
  전 가시 도구 대상, 임베딩 없이 substring + **한→영 도메인 동의어**(보고서→report,
  곡선→curve 등 ~30항) + 빈도·커버리지 승수 랭킹. 5질의 실검증(보고서 요약→
  search_reports/report_summary, 메쉬 품질→mesh_report 등). 이름이 전부 영어라
  동의어 확장이 랭킹 품질의 핵심이었다.
- **① 챗 진입 보강(agent-server)** — 챗엔 이미 TOOL_MAX=80 캡 + 질의별 관련도
  선택(_select_tools)이 있었다. 이번에 얹은 것: (a) 안내대 2종(search_tools·
  list_tool_apps)을 _TOOL_PRIORITY 맨 앞에 — 랭킹이 빗나가도 폴백이 항상 실림,
  (b) 실측 상위권인데 core 에 없던 10종 보강(get_record_sections·get_curve 등),
  (c) 시스템 프롬프트에 "없다고 단정하기 전에 search_tools" 폴백 지시.
- 심의 자유조회는 _FREE_ALLOW 접두사(search_/list_)로 안내대 2종이 자동 통과 — 무수정.
- TOOL_MAX 기본값(80)은 안 건드렸다 — 감사로 튜닝된 시스템이라 측정 없는 축소는
  회귀 위험만 산다. 개인 Claude 경로는 클라이언트의 지연 로드(ToolSearch)가 이미 해결.

## 남긴 것 (③, 후속)

- 심의 **좌석별 도구 노출 필터**(도메인→앱 매핑) — 감사 원장 백로그와 병합해 진행.
- search_tools 동의어 맵은 실사용 감사에서 "검색했는데 빗나간 질의"를 보며 증보한다.
- 도입 후 감시 지표: 감사 로그에서 search_tools 호출 빈도·후속 호출 성공률.

## 반영 경로

- 게이트웨이: git pull + ./start.sh restart
- agent-server: git pull + ./start.sh -d
