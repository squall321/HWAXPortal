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

## 웹 '찾은 즉시 호출' (2026-09-03 추가 — 사용자 지시 "웹을 잘 해보자")

- **invoke_tool(게이트웨이 범용 실행기)** — search_tools 로 찾은 미바인딩 도구를 같은
  턴에 즉시 호출. 이름·인자를 안쪽 도구로 바꿔 끼워 정상 경로(인가·캐시·RA 사용자
  위임·감사)를 그대로 탄다 — 감사는 안쪽 도구명으로 귀속(실검증). 이로써 웹 챗이
  Claude Code 의 ToolSearch 즉시 호출과 동급이 된다.
- 안전장치: 파괴·제어성 도구(delete_/remove_/cancel_/purge_/destroy_/_control/
  _set_state)는 범용 실행기로 못 부른다(직접 바인딩 전용) + 자기 재귀 차단.
- search_tools 결과에 args 요약(required+타입)을 실었다 — 범용 실행기의 최대 실패
  모드는 인자 추측이다. 프롬프트에도 '모르면 추측 말고 재검색'을 박았다.
- 심의 자유조회는 invoke_ 가 _FREE_ALLOW 접두사 밖이라 자동 미노출 — 읽기 전용
  단계에서 범용 실행기로 쓰기가 뚫리는 일이 없다(의도된 비대칭).

## 남긴 것 (③, 후속)

- 심의 **좌석별 도구 노출 필터**(도메인→앱 매핑) — 감사 원장 백로그와 병합해 진행.
- search_tools 동의어 맵은 실사용 감사에서 "검색했는데 빗나간 질의"를 보며 증보한다.
- 도입 후 감시 지표: 감사 로그에서 search_tools 호출 빈도·후속 호출 성공률.

## 전수 역감사 (2026-09-03 — 체크리스트를 기존 356개에 적용)

- **① 캐시 위험(읽기 접두사+쓰기): 실질 위반 0** — 휴리스틱에 걸린 30여 건은 전부
  설명에 이웃 쓰기 도구를 언급한 오탐(describe_metadata 등). 기존 _CACHE_DENY 3종으로 충분.
- **② invoke 차단망 구멍: 실질 0** — 걸린 것들은 복구 가능한 편집·제출 도구
  (update_report_draft, scenario_patch 등). smarttwin_submit·slurm_submit_job 같은
  자원 소모성 제출은 직접 바인딩과 동일 권한이라 허용 유지(dry_run 기본 등 자체 완화).
- **③ 설명 60자 미만 38건** — 최다 보유 StepForge 10건 보강 완료(create_project 12자
  →133자 등, 커밋 4970ac0). 재배포는 반드시 `redeploy-app.sh <slug> --rebuild` —
  --rebuild 없이는 옛 이미지 재시작이라 반영 안 됨(재확인된 함정). 게이트웨이 지문
  감지가 60초 내 자동 재집계함을 실증(07:13 "메타 변경 (60→60) — 재집계").
- **잔여 백로그(설명 보강)**: KooRemapper 8건(list_sessions·cancel_job 등 — 타 세션
  WIP 정리 후), MXWP 2건(delete_block·get_block), PaperIngest·ThermalShock·
  WebDesignAgents·HWAXRisk·d3plot 계열 각 1~3건. 시스템 도구(*_whoami 등)는 의도적 간결.

## 반영 경로

- 게이트웨이: git pull + ./start.sh restart
- agent-server: git pull + ./start.sh -d
