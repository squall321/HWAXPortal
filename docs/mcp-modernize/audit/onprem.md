# 사내 MCP(cae00 에만 붙은 백엔드) 감사 — 2026-11-27

읽기만 한 감사다. 리포를 고치지 않았고, 어떤 서비스도 부르지 않았다. dev 에서는 사내 MCP 에 닿지 않으므로 숫자는 모두 리포 문서(받은 편지함 · 운영 요청서 · 운영 답을 옮긴 context-notes)에서 옮겼다.
실제 내부 주소 · 계정 · 토큰 · 사람 이름은 옮기지 않았다(포털 리포는 공개다).

표기 — **확인** 은 운영 답 · 운영 실측이 문서에 적힌 값이다(날짜를 붙였다). **추정** 은 확인된 값으로 계산한 어림이다. **모름** 은 문서에 값이 없다는 뜻이다.
근거는 `파일:행` 으로 적었다. 파일 경로는 따로 적지 않으면 포털 리포(`HWAXPortal/`) 기준이고, 게이트웨이 리포는 `GW/` 로 줄였다.

---

## 0. 요약

- cae00 게이트웨이는 **백엔드 35 · 도구 1,984**(11-26 확인, 로컬 32 포함)다. dev 는 **백엔드 18 · 도구 797**(11-27 dev `/tools-map`)이다.
  - 근거 — `docs/request-1125/context-notes.md:374`(35 · 1,984) · `docs/request-1125/request.md:1029`(로컬 32) · `docs/leftovers-1121/context-notes.md:466`(11-23 은 34 · 1,947).
- 차이 약 1,190개 가운데 **dev 소스가 같은 앱(운영 사본 포함) 몫은 거의 0** 이고, **cae00 에만 있는 백엔드 18개가 약 1,150개**(확인값 합)다. 나머지 약 50개는 수를 모르는 백엔드(plm-defect · plm-search-agent 등)와 10-27 이후 늘어난 몫이다(추정).
- 가장 큰 덩어리는 **같은 틀(StandardPlatform)로 띄운 데이터허브 다섯 — 약 580개(백엔드 도구의 약 30%)** 이고, 그다음이 ComponentCore 183 · MatNexus 128 · TestScope 99 다. 이 넷이 cae00 전용 도구의 약 85% 다(추정).
- 계약 품질은 **표지 없음 83.5%**(1,972개 중, 11-24 확인) · **설명 1,000자 넘는 도구 296개**(11-24 확인) · **새 사내 앱 넷 인자 설명 0%**(11-23 확인) · **허브 넷의 도구 설명이 글자까지 같음**(DP-03) 이 눈에 띈다.
- 측정 도구는 많다(`/tools-map` 의 `arg_scores` · 피드백 보고서 · 안 불린 도구 · 검색 평가 · 스모크). 빠진 것은 **백엔드마다 한 장으로 모은 품질 카드**(표지 · 설명 길이 · 중복 설명 · 지연 백분위까지)와 **사내 앱 정답쌍**(추적 평가셋 186쌍 가운데 사내 앱 정답은 정본 허브 30 · MatNexus 1 · ComponentCore 1 뿐)이다.

---

## 1. 규모 — cae00 1,984 와 dev 797 의 차이가 어디서 오나

### 1-1. 전체 수의 흐름(확인)

| 날짜 | 백엔드 | 도구 | 근거 |
|---|---|---|---|
| 10-21 | — | 946(노출) | `docs/ext-connect/request.md:41` |
| 10-27 | — | 1,612(`/tools-map`, 미분류 996) | `docs/request-1027/02-HWAXMcpGateway.md:52` |
| 11-16 | — | 백엔드 1,590 + 로컬 23 | `docs/ontology-first/request-1116.md:25` |
| 11-23 | 34 | 1,947 | `docs/leftovers-1121/context-notes.md:466` |
| 11-24 | — | 1,978 → 1,970(토큰 절감 2판 스위치를 끔) · 1,972(표지 셈) | `docs/request-1125/request.md:7337` · `:2997` |
| 11-26 | 35 | 1,984 | `docs/request-1125/context-notes.md:374` |

11-23 → 11-26 의 백엔드 하나 증가는 11-24 에 등록된 SmartTwin MCP(23 도구)로 보인다(추정 — `docs/request-1125/request.md:7473` 의 '게이트웨이 23 도구 등록' 과 11-23 update-all 의 'SmartTwinMCP 미등재' ○ 줄, `docs/leftovers-1121/context-notes.md:515`).

### 1-2. 앱별로 가르기

**(가) dev 와 소스가 같은 앱 — cae00 에서 돌지만 dev 에도 같은 코드가 있다.** 이 몫은 dev 797 에도 거의 같은 수로 들어 있다.

| 백엔드 키(cae00) | dev 키 · 수(11-27) | cae00 수 | 상태 | 근거 |
|---|---|---|---|---|
| `stepforge-prod`(운영 사본, 선언 백엔드) | `heax-step_forge` 207 | 207(11-26) | 확인 | `docs/request-1125/context-notes.md:385` |
| `dynaforge-prod`(운영 사본, 선언 백엔드) | `heax-kooremapper_mcp` 120 | 120(11-23) | 확인 | `docs/leftovers-1121/context-notes.md:468` |
| `reportarchive` | 96 | 모름(RA 는 그 박스 밖 서버 쌍, 판이 다르다) | dev 값으로 어림 | — |
| `heax-hwax_risk` | 52 | 모름 | dev 값으로 어림 | — |
| `heax-laminate_analyzer_mcp` | 43 | 43(11-08) | 확인 | `docs/cae00-inbox/2026-11-08.md:28` |
| `mx-white-paper` | 41 | 40(10-30) | 확인(옛 값) | `docs/request-1030/outbound.md:14` |
| `signalforge` | 37 | 모름 | dev 값으로 어림 | — |
| `heax-materialtwin_web` | 34 | 모름 | dev 값으로 어림 | — |
| `ai-data-hub` | 32 | 32(11-24) | 확인 | `docs/request-1125/request.md:2369` |
| `heax-web_design_agents` | 24 | 모름 | dev 값으로 어림 | — |
| `smart-twin-mcp`(stcx 쪽 운영판) | 23 | 23(11-24) | 확인 | `docs/request-1125/request.md:7473` |
| `ste`(24대) | 13 | 12(11-24 요청서) | 확인 | `docs/request-1125/request.md:3795` |
| `hwax-deliberation` | 13 | 13(11-18) | 확인 | `docs/request-1125/request.md:1021` |
| `heax-thermal_shock_mcp` | 12 | 12(기대값) | 추정 | `docs/cae00-inbox/2026-10-31-backlog.md:162` |
| `heax-doc_forge` | 6 | 6 | 확인 | `docs/request-1030/platforms/00-INDEX.md`(docforge_* 여섯) |
| `heax-paper_ingest` | 4 | 모름 | dev 값으로 어림 | — |
| `_gateway`(로컬) | 31 | 32(11-24) | 확인 | `docs/request-1125/request.md:1029` |
| `heax-web_research_mcp` | 8 | 모름(cae00 에 있는지도 모름) | — | — |

합(로컬 포함) 약 **787**(추정 — 확인값 + 모르는 칸은 dev 값). 그러면 cae00 전용 몫은 1,984 − 787 = **약 1,197** 이다(추정).

**(나) cae00 에만 있는 백엔드(사내 MCP)** — 확인된 수만 더하면 **1,149** 다.

| 묶음 | 백엔드 키 | 도구 수(날짜) | 상태 | 근거 |
|---|---|---|---|---|
| SP 데이터허브 다섯 | `rootdesigndatahub`(정본) | 115(11-16 — '정본 도구 115개') | 확인 | `docs/ontology-first/request-1116.md:84` |
| | `failuretrace` · `caegroupdatahub` | 102~103(10-27) → 약 116(11-24) | 추정 | `docs/request-1027/02-HWAXMcpGateway.md:52` · `docs/request-1125/request.md:2995` |
| | `mountsoldatahub` · `ncdevdatahub` | 각 108(11-21) | 확인 | `docs/request-1125/request.md:1061` |
| | 다섯의 합 | 「같은 도구 116개」 × 5 ≈ 580 | 추정 | `docs/request-1125/request.md:2995`(G-4 '−464개' = 4 × 116) |
| 비코어 대형 | `componentcore` | 183(10-27) | 확인(옛 값) | `docs/request-1027/02-HWAXMcpGateway.md:52` |
| | `matnexus`(선언 백엔드) | 128(10-27 `/tools-map`) · 114(10-21 `tools/list`) | 확인(옛 값) | 같은 줄 · `docs/ext-connect/request.md:38` |
| | `testscope` | 99(11-21) · 100(11-13) | 확인 | `docs/request-1125/request.md:1061` · `:6659` |
| ECAD · 해석 | `odb-hub` | 39 | 확인 | `docs/request_1015.md:2813` · `docs/request-1027/02-HWAXMcpGateway.md:52` |
| | `arp` | 30(10-27) | 확인(옛 값) | `docs/request-1027/02-HWAXMcpGateway.md:52` |
| | `simengbay` | 26(10-27) | 확인(옛 값) | `docs/request-1125/request.md:6597` |
| | `simflow` | 21(5차 요청 실측, 10월 초) | 확인(옛 값) | `backend/config/access.yaml:177-178` |
| | `devlab-checklist`(PCB 체크리스트 중계) | 9(11-11) | 확인 | `docs/request-1111/request.md:393` |
| | `circuittrace` | 6(11-21) | 확인 | `docs/request-1125/request.md:981` |
| 품질 · 불량 | `fmea`(선언 백엔드) | 23(10-21) — 11-11 에 '붙지 않음' | 확인 · 지금은 모름 | `docs/ext-connect/request.md:37` · `docs/request-1111/request.md:431` |
| | `siren`(선언 백엔드) | 5(11-04) | 확인 | `docs/siren-delib/request.md:6` |
| | `plm-defect` | 모름(알려진 이름 셋 — `plm_defect_search` · `plm_case_detail` · `plm_similar_cases`) | 모름 | `docs/mxwp-wiki/context-notes.md:137` |
| | `plm-search-agent` | 모름 | 모름 | `GW/tool_areas.json` apps |
| 그 밖 | `knox-bridge` · `smart-twin-cluster` | 모름(dev 의 `smart-twin-cluster` 는 0 · 닿지 않음) | 모름 | `backend/config/access.yaml:141-145` |

남는 약 48개(1,197 − 1,149)는 plm-defect · plm-search-agent · 35번째 백엔드와 10-27 값이 낡은 앱(ComponentCore · MatNexus · ARP · SimEngBay)의 증가분으로 본다(추정). FMEA 가 지금 붙어 있지 않다면 그 23개도 이 남는 몫에 섞인다.

### 1-3. 규모가 뜻하는 것(추정)

- 백엔드 도구 1,952개 가운데 SP 허브 다섯이 약 30%, StepForge 운영 사본 10.6%, ComponentCore 9.4%, MatNexus 6.6%, DynaForge 운영 사본 6.1%, TestScope 5.1% 다.
- 도구 이름 목록만으로 세션 시작 문맥이 36.9k ~ 38.8k 토큰 뛴다(11-24 확인, `docs/request-1125/request.md:2961`). 허브 다섯을 한 벌로 접는 G-4 는 도구 −464개(−23.5%)로 어림됐다(`:2995`).
- '조회' · '검색' 같은 낱말이 도구 수백 개에 들어 낱말 순위로는 정본을 1위로 못 올린다(11-16 확인, `docs/ontology-first/request-1116.md:30-35`). 도구 수가 늘수록 이 잡음이 커진다.

---

## 2. 사내 MCP 목록 — 무엇 · 붙는 길 · 주인 · dev 소스 · 최근 상태

붙는 길의 낱말 — **정적** 은 게이트웨이 설정(`provision-config.sh` 가 쓰는 `gateway_config.json`)의 백엔드, **선언** 은 박스 권한표 `access.local.yaml` 의 `connect:` 블록(사람이 그쪽 토큰을 등록), **등록 토큰** 은 `PORTAL_CONN_BACKENDS`(RA · TestScope 방식), **위임** 은 `heax_registry.per_user_sso`(ste 방식 — 게이트웨이가 사람 토큰을 발급받는다), **서비스 토큰** 은 팀 토큰 하나로 붙는 것이다. 붙는 길을 문서에서 못 찾은 칸은 '모름' 이다.

| 백엔드 | 무엇 | 붙는 길 | 주인 | dev 소스 | 최근 상태 · 알려진 결함 |
|---|---|---|---|---|---|
| `rootdesigndatahub` | 사내 코어 정본 허브(고장모드 · 시험항목 · 가상검증 · 관리 기준 · 물성 · PLM 과제) | 정적 · 어휘표 정본(`backend/config/core_vocab.json` canonical) | Datahub 플랫폼 담당(사내 다른 팀) | SP 틀만 있다(StepForge · KooRemapper 서브모듈, 0.4.72) — 설치 데이터 · 설정은 없다 | 표지 없음(바꾸는 도구 49 · 읽기 60 — SP 에 표지 요청, 건네기는 사용자 몫, `docs/sp-latest/sp-annotations-request.md:20-27`) · 응답이 크다(DP-01 — objects_list 34행 135,566자) · `graph_neighbors` truncated 늘 참(DP-06) · 조건 주소 오류에 예시 없음(DP-14) |
| `failuretrace` | 불량 추적 허브(PLM 문제점 약 42.7만 건) | 정적 · 형제(sibling) | 허브 관리자 | 같은 SP 틀 | `failuretrace_whoami` 한 번 27 ~ 33초(DP-07) · `pd_defect` 행에 사람 이름(DP-08) · 자기소개 비어 있음(DHO-4) · 고장모드 낱말 대응 약 18.6만 건만 낱말(DHO-3) |
| `caegroupdatahub` | CAE 그룹 데이터 허브 | 정적 · 형제 | 허브 관리자 | 같은 SP 틀 | 기록 타입 0건(DHO-5) · 근거 문서 → 모델 참조 0(DHO-6) |
| `mountsoldatahub` | 실장 쪽 데이터 허브 | 정적 · 형제(11-24 박스 덧씌우기로, git 반영 요청 HPO-4) | 허브 관리자 | 같은 SP 틀 | 인자 설명 0% · 도구 영역 없음(11-23) · 위임 토큰으로 소스 목록 403(DHO-8) |
| `ncdevdatahub` | NC 개발 쪽 데이터 허브 | 정적 · 형제(박스 덧씌우기) | 허브 관리자 | 같은 SP 틀 | 인자 설명 0% · 영역 없음(11-23) · 자기소개에 새 타입 17개 빠짐(DHO-11) |
| `componentcore` | 부품 코어(비코어 앱) | 정적 · 비코어(noncore) | ComponentCore 담당 | 없다 | 코어 타입 0 · 객체 5(CCO-1) · 위임 토큰으로 `datasources_list` 거절(CCO-2) · SSO 클레임 빔(DP-10) |
| `matnexus` | 다른 조직의 물성 관리 시스템 | 선언(`connect:`, 개인 토큰 `mnx_pat_…`) | MatNexus 팀(TestScope 와 같은 팀) | 없다 | 위임 창구 404(SSO 없음) · 이름 겹침 넷(MaterialTwin 셋 · SignalForge 하나 — 선언 쪽만 접두하게 고침 GW19) · 코어를 받지 않음(MNO-1) · 토큰 확인 길 없음(FM-06) |
| `testscope` | 다른 조직의 신뢰성 시험 포털 | 등록 토큰(11-13 내장 사람별 토큰 백엔드) — v0.65.2 에 SSO 창구가 있어 전환 대기 | TestScope 팀 | 옛 사본 있음(`../TestScope` v0.62.0) | 표지 없음 · 쓰기 목록(46)에 쓰기 여섯 빠지고 읽기 하나 섞임(TS-1, `docs/request-1125/request.md:6513-6527`) · 인자 설명 0% · 영역 없음(11-23) |
| `odb-hub` | ECAD Automation Hub(ODB++ 보드) | 정적 · 서비스 토큰(10-28 부터 Authorization 머리) + 사람별 위임 | ODB 허브 담당 | 다른 사람 리포 사본 `../ODB` 가 있으나 같은 서비스인지 모름 | 표지 없음 → 읽기 여섯을 게이트웨이 읽기 목록에 손으로(HG-25, `GW/read_tools.json`) · `find_nets` 200건 조용한 잘림(OH-01) · `list_parts` 100 묶임 · 부품 빠짐(OH-02) · 위임 호출이 anonymous 로 남음(PA-09) · 옛 넓은 토큰(OD-5) |
| `arp` | AI Ready Portal(해석 실측) | 정적 · 서비스 토큰 + 사람별 위임(`X-Heax-Client: gateway`) · 주소는 `infra/.env` `ARP_HOST` 한 줄(`docs/arp-binding/PLAN.md`) | ARP 담당 | 없다 | 출력에 담당자 실명(AR-10) · 낙하 높이 단위 없음(cm 를 mm 로 읽음 — AR-9) · 모델 42 중 10 코어 태그 없음(ARO-1) · `arp_upload_open` 이 패널인지 모름(Q-A1) |
| `fmea` | 사내 FMEA 규격 · 사례 | 선언(`connect:`, 토큰 `fmea_…`) | FMEA 담당(다른 조직) | 없다 | 토큰 없이 `initialize` 부터 401 → 목록 전용 계정이 따로 든다(FM-01) · 표지 0/23(FM-02) · 개인 PC 에서 도는 것으로 보임(FM-03, 추정) · 11-11 '붙지 않음' |
| `siren` | 부품 불량 · 대책 사례 | 선언(`connect:`, trust · `mask_keep_hosts` 칸) | SIREN 팀 | 없다 | 인자 설명 0/12 · `list_groups` 가 MatNexus 와 겹침(`docs/request-1111/request.md:427`) · 표지 요청은 사용자 보류(R-1) · 사례에 코어 key 없음(SRO-1 ~ 3) |
| `simflow` | 해석 워크플로(패널 여섯) | 위임(`per_user_sso` — 발급마다 이전 토큰을 무효화) | SimFlow 담당 | 없다 | 패널 질문 아홉(Q-S1 ~ S9) · 위임 발급 500(PA-13) · 과제코드 0건 이유 없음(SMO-1) · 권한표 행 없을 땐 21개 전원 공개였다(`backend/config/access.yaml:177`) |
| `simengbay` | 해석 엔지니어링 저장소 | 모름 | SimEngBay 담당 | 없다 | 코어 받기 없음(PA-08) |
| `devlab-checklist` | 개발실 PCB 체크리스트(검증 서버 앞의 중계 MCP) | 모름 — 중계는 운영 쪽이 만든 것 | 중계는 운영 쪽 · 원 서버는 PCB 체크리스트 담당 | 없다(박스) | 중계 인자 설명 0/26(운영 쪽이 고치기로 함) · 13.8 MB 보드 30초 500(RQ-12 ~ 16) · 로그인 없이 결과 · 제출자 노출(RQ-04) · 응답 스키마 빔(RR-01) |
| `circuittrace` | 회로 추적 | 모름 | CircuitTrace(박스 폴더, git 없음) | 없다 | 영역 없음 6개(CT-01 — 받았으나 안 함) · 인자 설명 0%(11-23) |
| `plm-defect` | PLM 결함 검색(시장 불량 원천 후보) | 정적 · `allowed_groups plat:plmdefect` | 모름 | 없다 | 권한표에 키가 없을 땐 전원 차단이었다(`backend/config/access.yaml:178`) · MXWP 위키 W8 이 도구 꼴을 적을 예정 |
| `plm-search-agent` | PLM 유사 사례 검색 | 모름 | PLM 검색 에이전트 담당 | 없다 | 품질 대분류 필터 늘 0건(PL-01) · 구어 질의 오답 · 낮은 신뢰 표지 없음(PL-02) · 시험용 기록이 상위(PL-08) |
| `knox-bridge` | Knox 연계(챗 액션 사이드카) | 정적(키만 실측) | 모름 | 없다 | 도구 수 · 쓰임 모름 |
| `smart-twin-mcp`(참고 — dev 소스 있음) | stcx(356대) 해석 카탈로그 · 직접 sbatch | 정적(11-24 운영 배포 r20261124b) | KooSlurm 세션(`dashboard/smarttwin_mcp`) | **있다** | 직접 sbatch 셋이 호출자 · 작업 폴더를 안 봄(SM-01, P1 보안) · SSO 꺼짐이면 모두 admin(SM-04) · 표지 없음 → 박스 읽기 목록 9 → 19(SM-02, mode-* 태그는 시야라 읽기 칸을 따로 두기로 — `docs/cae00-inbox/2026-11-25.md:31-32`) |
| `stepforge-prod` · `dynaforge-prod`(참고) | 운영 노드의 StepForge · DynaForge | 선언(운영 사본 — 10-31 OB-04 로 시험 사본 숨김에서 뺌) | 각 세션 | **있다** | build · instance 칸 없음(PT-2) · StepForge 표지는 176 전부(10-31 판) |

빠뜨렸을 수 있는 것 — ReportArchive 는 사내 다른 팀 서비스지만 dev 에도 붙어 있어 여기 넣지 않았다(요청 27건은 `docs/request-1125/request.md:3043`). 35번째 백엔드가 무엇인지는 모름이다.

---

## 3. 계약 품질 — 알려진 것

### 3-1. 인자 설명

- 게이트웨이는 재집계마다 앱별 `arg_scores` 를 무인증 `/tools-map` 에 싣는다(`GW/README.md:309-317`). 기준은 설명 비율 0.3 미만이면 부족이다.
- cae00 에서 알려진 값(확인) — 새 앱 넷(circuittrace · mountsoldatahub · ncdevdatahub · testscope) 0%(`docs/leftovers-1121/context-notes.md:432`) · devlab-checklist 중계 0/26 · SIREN 0/12(`docs/request-1111/request.md:425-427`) · LaminateAnalyzer 173/173(dev 소스).
- 나머지 사내 앱(ComponentCore · MatNexus · ODB · ARP · FMEA · SimFlow · SimEngBay · PLM 둘 · 정본 허브)의 값은 cae00 `/tools-map` 에는 있지만 **dev 쪽 문서에 옮겨진 적이 없다**(모름). 09-15 dev 전수에서 SP 계열 허브 도구 인자 설명은 거의 0 이었다(`docs/procedures/gaps/hub-arg-descriptions.yaml` — 1,348 중 15).
- 비교 — dev 18 앱 전체는 인자 2,998 중 설명 1,136(0.379) · 단위 · 범위 348(0.116)이다(11-27 dev `/tools-map`).

### 3-2. 읽기 · 쓰기 표지

- 1,972개 중 83.5% 가 표지 없음(11-24 확인, `docs/request-1125/request.md:2997` — G-5 요청).
- 사내 앱별 — FMEA 0/23(FM-02) · ODB 없음(OH-06, 11-01 ECAD 길 약 48분 막힘) · SmartTwin MCP 없음(SM-02) · TestScope 없음(TS-1) · SP 허브 없음(바꾸는 49 · 읽기 60, 이름으로는 바꾸는 도구 14개가 읽기로 읽히고 읽기 60 가운데 23개만 열린다 — `docs/sp-latest/sp-annotations-request.md:20-27`) · SIREN 은 사용자 보류(R-1).
- 받는 쪽 대처 — 게이트웨이 읽기 목록(`GW/read_tools.json`)에 odb-hub 여섯 · testscope `resolve` 를 손으로 넣었다. 박스 덧씌우기 `read_tools.local.json` 에 SmartTwin MCP 19개(11-24)와 결함 집계 읽기 넷(운영 쪽 할 일)을 둔다(`docs/request-1125/request.md:5999` · `:3015`).
- 허브 쓰기 42개 — 정본 허브 운영자(`infra/personas/he-team.json:461` `he-data-coreontology`)의 선택 칸에 confirm 27 · writes 15 를 도구마다 `needs_tool` 로 넣었다(11-04 사용자 결정, `docs/sp-latest`). 표지가 아니라 이름 낱말에 기댄 판정이라, 판이 바뀔 때마다 받는 쪽을 다시 고쳐야 한다(예 — `lineage_repin` 낱말 `repin` 을 게이트웨이에 더함).
- 주의(원칙) — 이름 규칙은 순위 보정이지 울타리가 아니다. 읽기 목록에는 앱 소스 · 문서로 읽기임이 확인된 것만 넣는다(`GW/read_tools.json` `_note`).

### 3-3. 설명 — 길이 · 중복 · 자기소개

- 설명이 1,000자 넘는 도구가 모든 백엔드 합 296개다(11-24 확인, B-2 — 다른 팀 몫은 그 요청에 들지 않았다, `docs/request-1125/request.md:3005`).
- 허브 넷(이제 다섯)의 도구 설명이 글자까지 같아 챗이 허브를 가르지 못한다(DP-03 — 자주검증 id 로 부른 `failuretrace_graph_neighbors` 가 `APP-GRAPH-0001`). 게이트웨이에는 같은 설명을 접는 `copy_fold` 스위치와 형제 tagline 칸이 있다(`GW/search_tuning.json` switches · `backend/config/core_vocab.json` `_doc`). tagline 문안은 cae00 덧씌우기 몫이다.
- FailureTrace 자기소개 빔(DHO-4) · NCDev 자기소개에 새 타입 17개 빠짐(DHO-11).
- 응답 크기 — 허브 `objects_list` 135,566자 · `objects_summary` group_options 79,056자(DP-01), 기준선 결과 2.34M자 가운데 20,000자 넘는 35건이 44%(11-24, `docs/request-1125/request.md:2963`). 결과 손잡이(`X-HWAX-Result: ref`)는 `stored: 0` — PC 연결이 머리를 보내지 않아 쓰인 적이 없다.

### 3-4. 이름 겹침 · 허브 가족 접두

- 정본 + 형제(허브 가족)의 도구는 늘 `<백엔드 키에서 하이픈 뺀 것>_` 접두를 달고 원래 이름으로 접는다(`backend/config/core_vocab.json` `_doc`). 맨 이름으로는 어느 허브인지 가릴 수 없다(`infra/personas/he-team.json` `he-data-coreontology` pitfalls).
- 선언 백엔드와 겹치면 선언 쪽만 접두한다(GW19 고침, `docs/ext-connect/request.md:193`). MatNexus 넷 · SIREN `list_groups` 가 그 예다.
- 11-23 update-all 이 이름 겹침 경고 11줄을 냈다(`docs/leftovers-1121/context-notes.md:516`). 목록은 문서에 없다(모름).
- G-4(허브 다섯의 같은 도구 116개를 한 벌로 · `hub` 인자) 요청이 있다(`docs/request-1125/request.md:2995`). 옛 접두 이름은 별칭으로 남긴다.

### 3-5. 도구 영역

- 10-27 미분류 61.8%(996/1,612)를 `GW/tool_areas.json` apps 기본값으로 걷었다. 지금 남은 미분류는 circuittrace 6 · mountsoldatahub 108 · ncdevdatahub 108 · testscope 99(321개, CT-01 · CT-02 — 받았으나 안 함).
- 영역 표에는 **박스 덧씌우기가 없다**(게이트웨이가 읽는 `.local.json` 은 `app_keys` · `core_vocab` · `read_tools` · `search_tuning` · `service_tools` · `formats` · `ingest_routes` 뿐). 그래서 사내 앱 영역은 git 커밋으로만 바뀐다.

### 3-6. 위임 · 신원

| 문제 | 앱 | 근거 |
|---|---|---|
| 서비스 계정 명의 sbatch(누구든 GPU 잡) | SmartTwin MCP | SM-01 |
| SSO 꺼짐이면 모두 admin · 내 잡 거르기가 안 갈림 | SmartTwin MCP | SM-04 |
| 위임 호출이 anonymous 로 기록 | ODB 허브 | PA-09 |
| 위임 토큰으로 관리 목록 거절(403) | ComponentCore · MountSol | CCO-2 · DHO-8 |
| 목록부터 토큰 요구 · 본인 확인 창구 없음 | FMEA | FM-01 · `docs/ext-connect/request.md:37-40` |
| 토큰 확인 길 없음(verify none) | MatNexus | FM-06 |
| 발급마다 이전 토큰 무효화 · 발급 500 | SimFlow | HG-03 · PA-13 |
| 로그인 없이 결과 · 제출자 · 서버 경로 노출 | PCB 체크리스트 서버 | RQ-04 |
| 권한표 행이 없으면 게이트웨이가 전원 공개 | 박스 권한표에 허브 셋 · componentcore · plm-search-agent · simengbay 행이 있는지 확인 필요 | `docs/request-1029/PLAN.md:161`(O-13) |

### 3-7. 출력 위생 · 정직성

- 개인정보 — ARP `partOwner` 실명(AR-10) · FailureTrace `pd_defect` 사람 이름(DP-08) · PCB 체크리스트 제출자(RQ-04). 게이트웨이 가림(HG-21 · HG-22)이 뒤를 받친다.
- 단위 — ARP 낙하 높이(AR-9).
- 조용한 잘림 — ODB `find_nets` 200(OH-01) · `list_parts` 100(OH-02). 반대로 허브 `graph_neighbors` 는 truncated 가 늘 참(DP-06).
- 지연 — `failuretrace_whoami` 27 ~ 33초(DP-07) · PCB 체크리스트 제출 30초 500(RQ-14).

---

## 4. cae00 에서 이미 돌릴 수 있는 측정 · 점검

| 도구 | 어디 | 재는 것 | 사내 MCP 에 쓸모 · 한계 |
|---|---|---|---|
| `GET /tools-map`(무인증) | 게이트웨이 | 앱마다 tool_count · reachable · role · declared, 영역 · 미분류, `arg_scores`(설명 · 단위 비율, 앱마다 나쁜 도구 다섯), `write` · `routine_read` · `panel_read`(게이트웨이 판정), `orig`(겹침 · 가족 접두) | 2,000 개 전부를 한 번에 본다. 표지 원값 · 설명 길이 · 중복 설명은 없다(`GW/gateway.py:12448-12530`) |
| `GET /health` | 게이트웨이 | conn_platforms · 어휘표 · 손잡이 지문 · `tools_list_by_view` 등 | 덧씌우기 상태 확인용 |
| `tool_search_eval/run.py snapshot` | 게이트웨이 | `tools/list` 전부(이름 · 앱 · 설명 · 스키마) | **표지 · `_meta` 를 버린다**(`GW/tool_search_eval/run.py:46-80`) |
| `POST /search-eval` · `run.py live` | 게이트웨이 | 정답쌍(추적 + 박스)으로 hit@1 · hit@5 · MRR@20, 판마다(덧씌운 값 · 기본값 · 보정 끔 · 묶음 끔) | 앱별로 가르지 않는다. 추적 186쌍 중 사내 앱 정답은 정본 허브 30 · MatNexus 1 · ComponentCore 1 |
| `GET /search-log` · `POST /search-review`(관리자 '도구 검색 검토') | 게이트웨이 · 포털 | 실사용 질의 · 상위 다섯 · 뒤이은 호출 · 박스 정답 달기 | 사내 앱 정답쌍을 늘리는 길이다(사람 몫) |
| `platform_feedback_report.py` | 게이트웨이 | 플랫폼마다 ① 보정 덕에만 찾아진 질의 ② 보이고도 안 불림 ③ 밖에서 불림 ④ 실패(플랫폼 쪽 · 관문 쪽 가름) ⑤ 큰 응답 ⑥ 인자 설명 ⑦ 안 불린 도구(`GW/README.md:390-401`) | 사내 팀에 보낼 피드백의 바탕이 이미 있다. 지연 백분위 · 표지는 없다 |
| `tool_usage_report.py` | 게이트웨이 | 30일 안 불린 도구 | 앱 주인에게 넘길 목록 |
| `tool_registration_scan.py` | 게이트웨이 | 데이터 주인 추정 · 보고만 하는 함수 의심(D1 규칙) | 사내 앱에는 규칙이 하나뿐(낙하 결과) |
| `/usage-rollup` · `usage_rollup.py` | 게이트웨이 | 이용 통계 | 앱별 호출 수 |
| `infra/scripts/app-checks.py`(update-all §6) | 포털 | 새 앱(붙은 지 14일)의 영역 · 권한 행 · 이름 겹침 · 인자 설명 | **14일이 지나면 안 본다** — 옛 사내 앱은 대상 밖 |
| `infra/scripts/mcp-smoke.py`(`--periodic` 은 상태판 30분) | 포털 | 백엔드마다 읽기 도구 하나 실호출 · 0성공 백엔드 · 판 드리프트 | 선언 백엔드는 사람 토큰이 없어 '검사 못 함' 이다 |
| `infra/scripts/check-mcp-registration.sh` | 포털 | HEAX 앱 등록 5단계 | HEAX 허브 앱만 |
| 운영자 미리보기(페르소나 동기화) | 포털 | 운영자 목록 밖 쓰기 · 읽기를 쓰기로 · 없는 도구 | ODB · ARP 운영자는 key_tools 가 비어 있다(`infra/personas/he-team.json:69` · `:417`) |
| 감사 원장 `audit.jsonl` | 게이트웨이 | 호출마다 ts · backend · tool · ok · ms · chars · via | 지연 · 크기 백분위는 손으로 뽑아야 한다 |

### 빈 곳

1. **백엔드마다 한 장의 품질 카드가 없다.** 표지 원값(readOnlyHint 참 · 거짓 · 없음, destructiveHint) · 설명 길이 분포 · 다른 앱과 같은 설명 · 패널 도구 수 · 지연 p50/p95 · 결과 크기 p95 · 실패율을 한 번에 내는 점검이 없다. 11-24 의 83.5% · 296개는 그때그때 손으로 쟀다.
2. **사내 앱 검색 평가가 없다.** 정답쌍이 거의 없고, `/search-eval` 은 앱별로 가르지 않는다.
3. **옛 사내 앱은 정기 점검 밖이다.** `app-checks.py` 는 붙은 지 14일 동안만 본다.
4. **선언 백엔드 실호출을 못 한다.** 스모크는 사람 토큰이 있어야 하는 FMEA · MatNexus · SIREN · 운영 사본을 '검사 못 함' 으로 둔다.
5. **출력 위생(실명 · 단위 · 조용한 잘림) 점검이 없다.** 모두 QA 사람이 찾았다.
6. **영역 표에 박스 덧씌우기가 없다.** 사내 앱 영역이 git 에 묶여 '받았으나 안 함' 으로 쌓였다.

---

## 5. 고도화 안

원칙 — 사내 MCP 는 dev 에서 대조할 수 없다. 재기 · 튜닝 · 피드백은 cae00 안에서 하고, 고칠 것은 박스 덧씌우기 · 앱 주인 요청서로 보낸다(`GW/platform_feedback_report.py:2-3` 'cae00 에서 짓는다').

### 5-1. cae00 점검 한 벌 — 받은 편지함 글 초안

> 아래는 `docs/cae00-inbox/YYYY-MM-DD.md` 꼴의 초안이다. 이 감사는 글을 커밋하지 않았다.

```markdown
# YYYY-MM-DD — 사내 MCP 품질 한 판(읽기만)

> 게이트웨이 도구 약 2,000개 가운데 cae00 에만 있는 백엔드 약 1,200개의 계약 품질을 앱마다 한 줄로 받는다.
> 쓰기 · 재기동 · 설정 바꾸기는 하지 않는다. 답은 리포가 아니라 사용자를 거쳐(받은 편지함 README), 수 · 도구 이름만 — 설명 원문 · 주소 · 사람 이름은 빼고.

| 번호 | 받는 곳 | 무엇 | 돌려받을 것 |
|---|---|---|---|
| MQ-1 | 이 박스 — 게이트웨이 | 카탈로그 품질(앱마다 표지 · 설명 · 인자 · 겹침 · 영역) | JSON 한 개(앱 35줄) |
| MQ-2 | 이 박스 — 게이트웨이 감사 | 30일 신뢰도(호출 · 실패 · 지연 · 크기) | JSON 한 개(앱마다 한 줄) |
| MQ-3 | 이 박스 — 게이트웨이 | 피드백 보고서 · 안 불린 도구 | 마크다운 둘(그대로) |
| MQ-4 | 이 박스 — 포털 | 실호출 스모크 | `mcp-smoke.py --json` 출력 |
| MQ-5 | 이 박스 — 포털 · 게이트웨이 | 붙는 길 · 권한 행 · 덧씌우기 현황 | 표 하나 |
| MQ-6 | 사람(관리자) | 사내 앱 정답쌍 달기 → 검색 평가 | 단 쌍 수 · `/search-eval` 요약 |

## MQ-1 — 카탈로그 품질
- 까닭 — `/tools-map` 은 인자 설명 · 쓰기 판정을 주지만 표지 원값 · 설명 길이 · 같은 설명을 주지 않는다. 11-24 의 83.5% · 296개를 앱마다 다시 잰다.
- 명령 — 게이트웨이 리포 루트에서 에이전트 venv 파이썬으로(`tool_search_eval/run.py snapshot` 과 같은 길 — 토큰은 설정 파일에서 읽는다).
  (아래 5-1-a 의 스크립트)
- 기대 꼴 — `{"total": N, "apps": [{"app", "tools", "ro_true", "ro_false", "ro_none", "destructive", "gw_write", "routine_read", "panel", "unclassified", "prefixed", "desc_empty", "desc_gt1000", "desc_shared_other_app", "desc_p50", "desc_p95", "desc_max", "args", "arg_described_ratio", "arg_unit_or_range_ratio"}]}`.
- 돌려받을 것 — 그 JSON. 앱 줄이 35 가 아니면 닿지 않은 앱 이름.

## MQ-2 — 30일 신뢰도
- 명령 — 5-1-b 의 스크립트(감사 원장만 읽는다).
- 기대 꼴 — 앱마다 `calls · fail · fail_rate · ms_p50 · ms_p95 · ms_max · chars_p50 · chars_p95 · over_50k`. 실패는 ok=false 전부(관문 거절이 섞인다 — 가름은 MQ-3 의 ④).
- 돌려받을 것 — 그 JSON.

## MQ-3 — 피드백 보고서 · 안 불린 도구
- 명령 — `python3 platform_feedback_report.py --out fb.md` · `python3 tool_usage_report.py --days 30 --out unused.md`.
- 돌려받을 것 — 두 마크다운(질의 원문은 싣되 사람 · 주소는 없다 — 그 스크립트가 이미 뺀다). 사내 팀에 보낼 때는 그 팀 절만 떼어 보낸다.

## MQ-4 — 실호출 스모크
- 명령 — `python3 infra/scripts/mcp-smoke.py --json`.
- 돌려받을 것 — 백엔드마다 PASS · FAIL · 검사 못 함과 판 드리프트. 선언 백엔드는 '검사 못 함' 이 정상이다(사람 토큰).

## MQ-5 — 붙는 길 · 권한 행 · 덧씌우기
- 명령 — 게이트웨이 설정의 **키만**(값 말고): `heax_registry.per_user_sso` 의 키 · 정적 백엔드 키 · `/health` 의 `conn_platforms`. 포털 `access.local.yaml` 에 위 백엔드마다 행이 있는지(update-all §6 '권한 표 대조' 줄). 박스 덧씌우기 파일 다섯(`core_vocab.local.json` · `search_tuning.local.json` · `read_tools.local.json` · `app_keys.local.json` · `he-team.local.json`)의 있음 · 키 수.
- 돌려받을 것 — 표(백엔드 · 붙는 길 · 권한 행 있음/없음).

## MQ-6 — 사내 앱 정답쌍(사람)
- 까닭 — 추적 정답쌍에 사내 앱이 거의 없다(정본 허브 30 · MatNexus 1 · ComponentCore 1). 검색 고리를 cae00 에서 닫으려면 박스 정답쌍이 있어야 한다.
- 할 일 — 관리자 '도구 검색 검토'(`/search-log` 에서 실사용 질의를 골라 `gold` 표시)로 사내 앱마다 5 ~ 10쌍. 그 뒤 `run.py live --detail`.
- 돌려받을 것 — 앱별 단 쌍 수 · hit@1 · hit@5 · MRR(전체와 덧씌운 값 대 기본값).
```

**5-1-a. MQ-1 스크립트(읽기만 — 초안, dev 에서 돌려 보지 않았다).**

```python
# MQ-1 — 게이트웨이 리포 루트에서 $PY(에이전트 venv)로. 읽기만 한다.
import asyncio, collections, hashlib, json, urllib.request
from pathlib import Path
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client

BASE = "http://127.0.0.1:9110"
tmap = json.load(urllib.request.urlopen(BASE + "/tools-map", timeout=60))
tok = json.loads(Path("gateway_config.json").read_text(encoding="utf-8"))["_gateway"]["token"]

async def list_all():
    out = []
    async with streamablehttp_client(BASE + "/mcp", headers={"Authorization": "Bearer " + tok}) as (r, w, _):
        async with ClientSession(r, w) as s:
            await s.initialize()
            cur = None
            while True:
                res = await (s.list_tools(cursor=cur) if cur else s.list_tools())
                out += res.tools
                cur = getattr(res, "nextCursor", None)
                if not cur:
                    return out

tools = asyncio.run(list_all())
own = tmap.get("map") or {}
write, rr = set(tmap.get("write") or []), set(tmap.get("routine_read") or [])
uncl, orig = set(tmap.get("unclassified") or []), tmap.get("orig") or {}
h = lambda d: hashlib.sha1(d.encode()).hexdigest()
apps_of_desc = collections.defaultdict(set)
for t in tools:
    apps_of_desc[h(t.description or "")].add(own.get(t.name, "_gateway"))
per, lens = collections.defaultdict(collections.Counter), collections.defaultdict(list)
for t in tools:
    a, d, ann = own.get(t.name, "_gateway"), t.description or "", t.annotations
    ro = getattr(ann, "readOnlyHint", None)
    c = per[a]
    c["tools"] += 1
    c["ro_true" if ro is True else "ro_false" if ro is False else "ro_none"] += 1
    c["destructive"] += bool(getattr(ann, "destructiveHint", None))
    c["gw_write"] += t.name in write
    c["routine_read"] += t.name in rr
    c["unclassified"] += t.name in uncl
    c["prefixed"] += t.name in orig
    c["panel"] += bool((getattr(t, "meta", None) or {}).get("ui"))
    c["desc_empty"] += not d.strip()
    c["desc_gt1000"] += len(d) > 1000
    c["desc_shared_other_app"] += len(apps_of_desc[h(d)]) > 1
    lens[a].append(len(d))
args = {x["app"]: x for x in (tmap.get("arg_scores") or {}).get("apps", [])}
rows = []
for a, c in sorted(per.items(), key=lambda kv: -kv[1]["tools"]):
    L, s = sorted(lens[a]), args.get(a, {})
    rows.append({"app": a, **c, "desc_p50": L[len(L) // 2], "desc_p95": L[min(len(L) - 1, int(len(L) * 0.95))],
                 "desc_max": L[-1], "args": s.get("args"), "arg_described_ratio": s.get("described_ratio"),
                 "arg_unit_or_range_ratio": s.get("unit_or_range_ratio")})
print(json.dumps({"total": len(tools), "apps": rows}, ensure_ascii=False, indent=1))
```

**5-1-b. MQ-2 스크립트(감사 원장만).**

```python
# MQ-2 — 게이트웨이 리포 루트에서 python3 로. 감사 경로가 GATEWAY_AUDIT 로 따로면 그 값을 쓴다.
import collections, json, os
from datetime import datetime, timedelta, timezone
path = os.environ.get("GATEWAY_AUDIT", "audit.jsonl")
since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
ms, ch, n, bad = (collections.defaultdict(list), collections.defaultdict(list), collections.Counter(), collections.Counter())
with open(path, encoding="utf-8", errors="replace") as f:
    for line in f:
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if str(e.get("ts", "")) < since[:19]:
            continue
        b = e.get("backend") or "?"
        n[b] += 1
        bad[b] += e.get("ok") is False
        if isinstance(e.get("ms"), (int, float)):
            ms[b].append(e["ms"])
        if isinstance(e.get("chars"), int):
            ch[b].append(e["chars"])
q = lambda L, p: (sorted(L)[min(len(L) - 1, int(len(L) * p))] if L else None)
print(json.dumps([{"app": b, "calls": n[b], "fail": bad[b], "fail_rate": round(bad[b] / n[b], 3),
                   "ms_p50": q(ms[b], .5), "ms_p95": q(ms[b], .95), "ms_max": max(ms[b], default=None),
                   "chars_p50": q(ch[b], .5), "chars_p95": q(ch[b], .95),
                   "over_50k": sum(c > 50000 for c in ch[b])} for b in sorted(n, key=lambda k: -n[k])],
                 ensure_ascii=False, indent=1))
```

- 2,000 개 규모에서 주의할 것 — 답에는 도구마다의 줄을 싣지 않고 앱마다 한 줄 · 나쁜 도구 다섯만 싣는다. `tools/list` 한 번은 설명 원문을 다 받으므로(dev 797 개가 약 1.6 MB — 같은 날 dev 스냅숏) cae00 은 4 MB 남짓으로 어림된다(추정). `/search-eval` 은 한 번에 하나만 돈다(409).
- ts 꼴 — 감사의 `ts` 가 ISO UTC 가 아니면 MQ-2 의 기간 자르기를 고친다(dev 원장은 확인하지 않았다 — 짐작).

### 5-2. 박스 덧씌우기로 할 수 있는 것(코드 · 빌드 없이, 재기동 없이)

| 파일 | 할 수 있는 것 | 사내 MCP 에 쓸 곳 | 주의 |
|---|---|---|---|
| `backend/config/core_vocab.local.json`(포털 옆, merge patch) | 앱 역할(sibling · noncore + note) · 형제 tagline(120자) · 검색 낱말 → 도구 · types · `ontology.lookup` 줄 | 허브 다섯의 **설치별 tagline**(DP-03 을 받는 쪽에서 덜어 준다) · TestScope · SIREN · SimFlow · SimEngBay · PLM 둘 · 체크리스트 · CircuitTrace 를 noncore + note 로(지금 noncore 는 다섯뿐 — `backend/config/core_vocab.json` apps) · MountSol · NCDev lookup 줄(이미 박스에 — git 반영 요청 HPO-1 · HPO-4) | 앱 줄의 모르는 칸은 줄째 버려진다 · 지문은 update-all §7 이 맞댄다 |
| `GW/search_tuning.local.json` | 동의어(owner · source_fix 를 달면 피드백 보고서가 그 팀 몫으로 적는다) · 스위치(`noncore_demote` 는 이미 켬 · `onto_first` · `onto_lookup_first`) · 품질 낱말 | 사내 앱 한국어 이름 → 도구 이름(11-16 앱 이름 6문항 hit@1 0.33 → 0.83 — `docs/ontology-first/request-1116.md:30-35`) | 켜기 전후로 `/search-eval` 의 판을 견준다 · 보정이 그쪽 설명의 빈 곳을 가리므로 owner · source_fix 를 꼭 단다 |
| `GW/read_tools.local.json` | 읽기 목록 더하기 · `deny` | 앱 표지가 없는 사내 앱의 확인된 읽기(FMEA 21 · TestScope 읽기 · SP 허브 읽기 60 가운데 이름으로 안 열리는 37 · ODB `find_nets` · `get_net` · `get_part_detail` 등) · 부작용을 모르는 것은 deny(예 — PCB 체크리스트 resolve, RQ-09 답 전) | 앱 소스 · 문서로 읽기임이 확인된 것만 · 관리자 `GET /readonly-allowlist` 로 본다 |
| `infra/personas/he-team.local.json` | 운영자 더하기 · 덮기 · 빼기(운영자 키로 merge patch) | ODB · ARP 운영자의 빈 `key_tools` 채우기 · SmartTwin 운영자(11-24 등록 뒤 다시 동기화) · 허브 운영자 선택 칸에 MountSol · NCDev · TestScope · FMEA · MatNexus 운영자 | dev 에 없는 앱의 운영자는 dev 에서 고치지 않는다(11-04 결정) |
| `GW/app_keys.local.json` | `list_tool_apps` 의 env · canonical · 별칭 | 운영 사본 · 형제의 canonical 표시 | — |
| 박스 권한표 `access.local.yaml` 의 `connect:` | 선언 백엔드의 `read_tools` · `mask_keep_hosts` · trust | FMEA · MatNexus · SIREN 의 읽기 선언 | 같은 id 는 통째로 바뀐다(합치지 않는다) |
| 게이트웨이 `provision.env` | `GATEWAY_RESULT_REFS=1` 등 | 큰 결과 손잡이(11-24 운영 쪽 할 일) | 재기동이 든다 |

덧씌우기로 못 하는 것 — **영역 표**(`tool_areas.json` 은 git 만), 표지 자체, 설명 · 인자 설명, 응답 크기, 위임 · 신원.

### 5-3. dev 쪽에서 지을 것(제안 — 이 감사는 짓지 않았다)

1. **사내 MCP 품질 카드** — MQ-1 · MQ-2 · 피드백 보고서 ⑤ ⑥ ⑦ · 스모크를 앱마다 한 장으로 묶는 읽기 전용 스크립트(게이트웨이 리포, 표준 라이브러리 + 기존 MCP 클라이언트). 출력은 앱 주인에게 그대로 보낼 마크다운과 수만 든 JSON 둘. 사람 · 주소 · 설명 원문은 싣지 않는다.
2. `tool_search_eval/run.py snapshot` 이 `annotations` · `_meta.ui` 를 남기게 · `live --by-app`(앱별 hit@1 · MRR).
3. `/tools-map` 의 `arg_scores` 곁에 앱별 표지 원값 셈(`ro_true · ro_false · ro_none`)을 덧붙이기(있던 칸은 그대로).
4. `app-checks.py` 의 14일 창 밖 옛 앱도 한 달에 한 번 보는 갈래(경고는 요약 한 줄로).
5. `tool_areas.local.json` 덧씌우기 또는 CT-01 · CT-02 의 기본값 커밋(값은 앱 주인이 정한다는 CT-02 의 단서를 사용자에게 물어야 한다).
6. 2,000 규모의 큰 지렛대 — G-4(허브 다섯 한 벌 · −464) · G-1(light 보기에 패널 · verify · list_tool_apps) · P-1(PC 연결 생성에 결과 손잡이 · 보기 머리). 이미 요청돼 있다(`docs/request-1125/request.md:2989-3007`).

### 5-4. 앱 주인에게 보낼 요청서

`docs/request-1125/request.md` 3절에 다른 팀 몫 170건이 이미 모여 있고 대부분 '보낸 기록 없음' 이다(그 박스가 담당에게 보낸다 — `docs/cae00-inbox/2026-11-25.md:12`). 새로 더할 것은 **모든 사내 앱에 같은 '계약 기준표' 한 장과 MQ-1 의 그 앱 줄** 이다.

**계약 기준표(모든 사내 앱 공통 — 제안).**

1. 도구마다 `readOnlyHint`(바꾸는 도구는 False, 지우기 · 덮어쓰기는 `destructiveHint`).
2. 인자 설명 — 게이트웨이 기준 0.3 이상, 수치 인자는 단위 · 범위(기준 모델 LaminateAnalyzer 173/173).
3. 설명 첫 문단 600자 안 — '언제 쓰나 · 필수 인자 · 함정 한 줄'(B-2 를 다른 팀에도).
4. 같은 틀의 설치는 설치마다 다른 자기소개 · tagline(DP-03).
5. 목록(`initialize` · `tools/list`)은 토큰 없이 또는 서비스 토큰으로(FM-01).
6. 위임 호출은 그 사람으로 기록하고 본인 확인 창구를 둔다(PA-09 · FM-06 · SM-04).
7. 잘림은 `total` · `truncated` · 다음 쪽 손잡이로 말한다(OH-01 · DP-06).
8. 출력에 사람 실명 · 메일을 싣지 않는다(AR-10 · DP-08). 수치 칸에 단위(AR-9).
9. 가벼운 상태 확인 경로(RR-03).

**받는 곳별(이미 있는 묶음 + 덧붙일 것).**

| 받는 곳 | 이미 있는 묶음(request-1125 3절) | 덧붙일 것 |
|---|---|---|
| StandardPlatform(틀) | DP-01 · 03 · 04 · 06 · 07 · 11 · 12 · 14(3-5) · SP 표지 요청(`docs/sp-latest/sp-annotations-request.md`, 건넸는지 모름) | 인자 설명(09-15 전수 1%) · 설명 길이 |
| 허브 관리자(FailureTrace · MountSol · NCDev · CAE그룹) | DHO-2 ~ 12 | 자기소개 · tagline 문안(받는 쪽 덧씌우기와 맞추기) |
| ComponentCore | CCO-1 · 2 · DP-10 | 183 개(사내 단일 앱 최대)의 표지 · 인자 설명 — MQ-1 값으로 |
| MatNexus | MNO-1 · 2 · FM-06 | 표지 · 인자 설명(모름) |
| TestScope | TS-1 · PA-18 | 인자 설명 0% · SSO 전환 일정(v0.65.2) |
| ODB 허브 | OH-01 ~ 06 · OD-5 · 8 · 9 · ODO-1 ~ 4 · PA-09 | 인자 설명(모름) |
| ARP | AR-9 · 10 · ARO-1 ~ 3 · PA-10 · 11 · Q-A1 | 표지 · 인자 설명(모름) |
| FMEA | FM-01 ~ 05 · FMO-1 ~ 3 | 상시 운영(지금 '붙지 않음') |
| SIREN | SRO-1 ~ 3 · R-1(사용자 보류) · R-8 | `list_groups` 이름(겹침) |
| SimFlow | PA-04 ~ 07 · 12 ~ 14 · Q-S1 ~ S9 · SMO-1 · 2 | 인자 설명 · 표지(모름) |
| SimEngBay | PA-08 | 표지 · 인자 설명(모름) |
| PLM 검색 에이전트 | PL-01 ~ 08 | 표지 · 낮은 신뢰 표지 |
| plm-defect | 없음(주인을 모름) | 주인 확인부터 — MXWP W8 과 함께 |
| PCB 체크리스트 서버 | RQ-01 ~ 16 · RR-01 ~ 04 | (중계 인자 설명 0/26 은 운영 쪽 몫) |
| CircuitTrace | CT-01(게이트웨이 영역) | 인자 설명 0% · git 없는 박스 폴더 |
| SmartTwin MCP(KooSlurm 세션 — dev 소스 있음) | SM-01(P1) · SM-02(전제 고쳐 보냄) · SM-03 · SM-04 | dev 에서 바로 고칠 수 있는 유일한 사내 쪽 서비스 |

---

## 6. 짐작 · 열린 물음

- cae00 의 공용 앱(RA · SignalForge · 리스크 · MaterialTwin · WDA · PaperIngest) 수는 dev 값으로 어림했다. 판이 달라 몇 개씩 다를 수 있다.
- 35번째 백엔드 · plm-defect · plm-search-agent · knox-bridge · smart-twin-cluster 의 수는 모름이다. MQ-1 한 번이면 모두 채워진다.
- FMEA 가 지금 붙어 있는지 모른다(11-11 '붙지 않음' 뒤 기록 없음).
- `../ODB` 리포가 ODB 허브 · PCB 체크리스트 가운데 어느 것의 원천인지 모른다(체크리스트 규칙 파일 꼴이 보인다 — 짐작).
- SP 표지 요청서가 SP 쪽에 건네졌는지 모른다(건네기는 사용자 몫 — `docs/sp-latest/sp-annotations-request.md:3`).
- MQ-1 · MQ-2 스크립트는 dev 에서 돌려 보지 않았다(사내 백엔드가 없다). dev 게이트웨이에서 먼저 한 번 돌려 꼴을 확인한 뒤 편지함에 싣기를 권한다.
