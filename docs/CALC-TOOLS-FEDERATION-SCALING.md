# 수치 계산 도구 페더레이션 — 스케일 설계 제안 (laminate 연동에서 도출)

> **대상**: HWAXPortal(관제)·HWAXMcpGateway·AIDataHub 관리 주체.
> **배경**: laminate-analyzer + materialtwin이 [HEAX-MCP-AUTOWIRE](HEAX-MCP-AUTOWIRE.md) 경로로
> 게이트웨이에 자동 합류하면서(2026-07-16) 실증된 사실과, **이런 수치 계산 MCP가 수십~수백 개로
> 늘어날 때** 페더레이션이 버티기 위한 원칙·백로그를 전달한다.
> 발신: LaminateAnalyzerMCP 연동 작업 (근거 문서: 해당 리포 `docs/mcp_laminate_planning.md` §16,
> `docs/agent_guide.md`, `context-notes.md`).

## 0. 현황 (2026-07-16 실측 — 전부 동작 확인됨)

- 게이트웨이(:9110) **147 도구** = 정적 백엔드 5종 + heax 자동탐지 2종
  (`heax-laminate_analyzer_mcp` 11종, `heax-materialtwin_web` 18종 — 삭제 툴 2종은 HTTP 표면 비노출).
- 포털 챗(HWAXAgentServer → 게이트웨이 단일 엔트리) 경로에서
  **재료 실측 E(materialtwin) → 단위 브리지 → 적층 해석(laminate)** 체인 E2E 검증.
  결과는 payload_hash로 재현 가능, 가정 상수는 W120 경고로 추적된다.
- 인증: HEAXHub PAT(HEAXHub commit `6221405`)를 게이트웨이가 중앙 주입 — 클라이언트 무설정.
- AIDataHub(309 페르소나)는 게이트웨이 백엔드로 이미 연결되어 있어, 페르소나 세션에서
  위 계산 도구가 **지금도 호출 가능**하다. 남은 것은 "잘 쓰게"와 "스케일"뿐.

## 1. 스케일 불변식 5 (제안의 핵심)

계산 도구가 N개, 페르소나가 M개일 때 유지보수가 N×M으로 터지지 않으려면.

| # | 불변식 | 구현 위치 |
|---|---|---|
| P1 | **도구 지식은 도구 자신에게** — description·guide 리소스·reference case로 자기설명. 프롬프트/게이트웨이/페르소나에 도구 사용법을 복제하지 않는다 | 각 MCP 서버 (laminate가 표준 예시: 규약 3줄이 담긴 description + `laminate://guide` + `get_reference_cases` 자가검증) |
| P2 | **페르소나는 도구당이 아니라 계산 도메인당** — "구조 계산 전문가" 1명이 적층+보+좌굴+체결 도구군을 담당. 도구 100개 ≠ 페르소나 100개 | AIDataHub agent 등록 |
| P3 | **연결은 동적 라우팅** — 309 페르소나 프롬프트에 도구/전담 페르소나를 박지 않고, 공통 가이드 1줄 + `recommend_agents` 재라우팅으로 해결. 새 계산 페르소나는 등록만 하면 전체에 자동 연결 | AIDataHub `_tool_guide_block` (아래 A1) |
| P4 | **가시성은 게이트웨이 그룹 필터** — 쓰기 도구·민감 도구는 `allowed_groups`로 제한. 현재 heax 자동탐지 백엔드에는 이 슬롯이 없음 | 게이트웨이 + heax 레지스트리 (아래 G1) |
| P5 | **세션 컨텍스트 O(1)** — 도구가 수백이면 전량 노출 대신 도구 검색 메타도구로 lazy 로드 (Claude Code의 ToolSearch/deferred와 동일 패턴) | 게이트웨이 (아래 G2) |

## 2. 백로그 (구체 변경점, 우선순위순)

**A1. AIDataHub 공통 가이드에 계산 재라우팅 1줄** — 소규모, 즉효.
`api_server/src/api/services/recommend_svc.py:463` `_tool_guide_block()`에 추가.
동적 조립이라 DB/재시드 불필요, 309 페르소나 전원 즉시 적용.

```
수치 계산(강성·적층·재료 물성 등)은 절대 직접 암산하지 말 것 — 게이트웨이의 계산
도구를 사용하고, 당신 도메인 밖이면 recommend_agents로 계산 전문 페르소나를 찾아 전환하라.
```

**A2. 계산 도메인 페르소나 등록 + 밀접 페르소나 포인터** — 소규모.
- 신규: `sim-structural-calc`(가칭) — admin_prompt에 도구 워크플로
  (materialtwin 조회→E_GPa×1000→laminate 해석→warnings/assumptions 보고).
  LaminateAnalyzerMCP `docs/agent_guide.md`를 압축해 쓰면 된다.
  설명/태그에 "적층, ABD, 중립면, 강성, warpage" — recommend_agents 라우팅의 열쇠.
- 기존 밀접 페르소나 **포인터 1줄만**(지식 복제 금지): `pcb-material`(기판 = 문자 그대로
  적층판, warpage 직결), `mech-exterior-materials`(CFRP 백커버), `mech-drop-impact`,
  `mech-cover-glass`, sim-* 구조 계열.

**G1. heax 자동탐지 백엔드에 그룹 필터 슬롯** — 3파일 소규모.
manifest `mcp.allowed_groups: [...]` → HEAXHub `app/api/v1/mcp.py` 레지스트리 응답에 포함
→ 게이트웨이 `_discover_heax()`가 spec에 전달(정적 백엔드의 기존 필터 로직 재사용).
현재 heax 자동 백엔드는 전체 공개로 합류한다 — materialtwin의 등록(register_*) 도구처럼
쓰기 성격 도구가 늘수록 이 슬롯이 필요해진다.

**G2. 게이트웨이 도구 검색 메타도구(find_tools)** — 규모 도달 시(도구 ~300+).
`tools/list` 전량 노출 대신 요약 카탈로그 + `find_tools(q)` → 상세 스키마 lazy 반환 모드.
지금은 147개라 급하지 않으나, 계산 도구 수십 개 추가 시점 전에 설계해 두길 권장.

**참고(HEAXHub 백로그)**: manifest schema v2에 `mcp` 블록 정식 등재
(현재 additionalProperties:false 위반 상태로 동작 — 스캐너가 스키마를 강제하지 않아서).

## 3. 하지 말 것 (반패턴)

- 309 페르소나 각각의 프롬프트에 도구 지식/목록 복제 — N×M 유지보수 파산.
- 도구당 전담 페르소나 신설 — 페르소나 폭발.
- 게이트웨이 config에 heax 앱 수동 등록 — auto-wire 우회(단일 경로 유지).
- 새 계산 MCP를 자기설명 없이(빈약한 description) 배포 — P1 위반. 신규 도구의
  체크리스트는 laminate의 §6.6(도구 description 작성 규칙)을 표준으로 삼을 것.

## 실행 현황 (2026-07-16, 포털 관제 측 반영)

- **A1 완료** — AIDataHub `recommend_svc._tool_guide_block`에 계산 재라우팅 1줄 추가
  (AIDataHub commit `6bace02`). 동적 조립이라 315 페르소나 전원 즉시 적용, ai-data-hub 재기동됨.
- **G1 완료** — 매니페스트 `mcp.allowed_groups` → heax `mcp.py` 레지스트리 노출(HEAXHub `0702294`)
  → 게이트웨이 `_discover_heax`+lifespan/revive가 POLICY에 반영(HWAXMcpGateway `6d61dc1`),
  문서 `4d6b9ba`. 라이브 검증: `/health.policy`에 `heax-*` 백엔드가 allowed_groups와 함께 등장
  (현재 두 앱 모두 `[]`=공개).
- **A2 신규 페르소나 완료** — `sim-structural-calc`(구조·적층 계산 전문) 등록(315개째,
  tags 12·sample_queries 7, 샘플 임베딩 동기화됨). 직접 선택(`get_agent_session`)용 도구-오케스트레이터.
  recommend 랭킹은 데이터 유사도 주도라 데이터 없는 이 페르소나는 상위에 안 뜨는 게 정상 —
  밀접 데이터 페르소나(mech-exterior-materials·mech-drop-impact·sim-structural-static 등)가 관문.
- **A2 밀접 페르소나 포인터 — A1에 포섭되어 생략.** A1의 append 가이드가 이미 전 페르소나에
  "계산은 도구로, 도메인 밖이면 recommend_agents" 를 부여하므로, 명시된 5개 도메인 페르소나에
  중복 포인터를 박지 않는다(도메인 데이터 불필요 편집 회피). 특정 페르소나에 계산 강조가
  더 필요하면 그때 개별 `update_agent`로 1줄 추가.
- **G2 지연** — 현재 148 도구로 불필요. 계산 도구 수십 개 추가 시점 전에 설계 착수 권장(문서 §2 G2).

## 4. 새 계산 MCP 온보딩 절차 (현행 기준, 변경 불필요)

1. FastAPI/streamable HTTP로 `/mcp` 서빙 (DNS rebinding Host 검증 off — loopback+Caddy 경계).
2. `.portal/manifest.yaml`에 `mcp: {expose: true, path: /mcp}` 선언.
3. HEAXHub integrations 등록(심볼릭 링크 또는 git source) → 스캐너 빌드·기동.
4. 게이트웨이 60초 폴링으로 자동 합류 — **게이트웨이/포털 쪽 작업 0.**
5. (A2 채택 시) 해당 계산 도메인 페르소나의 담당 도구군에 한 줄 추가.
