<!-- 설계 리스크 심사(ECAD/MCAD/Dyna 그래프 diff + HW/XD 크로스도메인 의견 DB) — 결정과 근거(계속 갱신) -->
# 설계 리스크 심사 — 컨텍스트 노트

착수 2026-08-31. 계획서는 `plan.md`, 실행 항목은 `checklist.md`. 이 문서는 결정과 그 이유, 지형 조사 결과를 남긴다.

## 요구 (사용자 원문 취지)

- ECAD·MCAD·Dyna 파일에서 과제의 **디멘전·connectivity** 를 뽑아 (1) 이전 과제와 비교, (2) 한 과제 안의 개념설계 변동을
  HW/XD 전문가 크로스도메인 관점으로 심사해 **리스크 심사 보고서**를 만든다.
- 과제 메타를 DB 화, 전문가별 **의견 서술**을 DB 에 보관·재참조, 두 과제 비교는 **그래프 정보(connectivity)** 로 비교하고
  그 결과도 DB 화. 특정 과제/과제쌍 심사를 한 전문가는 **한번 하면 넘어가게**(커버리지 회계) 해서 전체 HW/XD 가 한번씩
  서술적 비교를 다 하게 한다. 배치가 쌓일수록 리스크 이해가 높아진다.
- **가장 강조**: 데이터 가져오기보다 "그래프 diff/현재 상태 평가를 어떻게 정리해 그 과제 평가를 서술하고, 그 데이터를
  다음 과제·다른 connectivity 에서 재사용하게 하나"가 핵심. 정성적 과제 특징(성격)도 드러나야. 기존 기능 무손상. 아주 유용해야.

## 지형 조사 (2026-08-31, 실측 — 재조사 없이 전제)

- **StepForge**(heax-step_forge) 는 이미 MCAD 그래프. project → run_job(parse|detect|mesh|pipeline, scope 부분검출) →
  tree.json(하이라키), list_parts(name/path/kind/bbox/volume/area/centroid/material/density), list_interfaces
  (tied|touching|clearance|interference, min_gap, contact_area_est, penetration, cross_file, status auto|confirmed|manual),
  interface_graph(json: counts/orphans/edges). set_interface/confirm_interfaces = **사람 게이트**. part rules yaml.
- **DynaForge**(heax-kooremapper_mcp) = K파일 47 op(upload_kfile, inspect_file, material_usage, section_contact_usage,
  run_operation) + d3plot 리포트(report_part_risk/energy_flow/worst_cases/findings…) + **compare_reports** 기존재.
- **ODB hub**(ECAD) = 외부·미상·게이트웨이에 아직 없음 → 어댑터 계약만 정의, 스텁.
- **RA KG**(reportarchive, ⚠ 코드 hands-off — API/관리설정만) = 객체 타입(model/part/bom/phase/defect/rel_test/sim_type
  reference · project/supplier/test_run/incident/failure_mode record · dept/user/report system) + 관계(part_of, supersedes,
  variant_of, has_defect, caused_by, simulated_by, tested_by, documents…). **create_type 로 타입 확장 가능**. 보고서 템플릿
  deliberation/doe-analysis(widget-v1), report_types 비어 있음(태그로만 분류 중).
- **AIDataHub** = doc_type(design_spec, lessons_learned, checklist, expert_knowledge_card… create_doc_type 확장) 레코드/섹션/
  태그 + 전문가 RAG(agent_search, bind_records_to_agent) + hybrid/semantic/find_similar_data.
- **전문가 풀**: xd 122·sim 22·cam 21·rel 20·soc 20·disp 19·mech 19·pcb 19·rf 19·passive 18·pwr 18·sh 17·mem 16·std 8 ≈ HW/XD 350
  (sw 408 제외).
- **심의 엔진**(웹 deliberation.py ↔ MCP hwax-deliberate.js 정합): chair 8종·modifiers 5·지정 반대석·evidence 채널(≤12·~11KB)·
  좌석 자유조회(free_tools)·지식카드 RAG·RA 저장(template deliberation)·conv_store. 시뮬 2/3단 래퍼 패턴.
- **포털**: FastAPI 모듈(agent/auth/catalog/mail/mcp) + sqlite 저장소 패턴(conv_store: stdlib sqlite3+Lock+owner_sub). 라우트
  /, /deliberate, /apps, /tokens.
- **선례**: heax-thermal_shock_mcp(배치·치수→SED 리스크 예측 + 학습데이터 수명주기), laminate check_design_rules, build-plan 의
  "자산 3경로→단일 모델 IR·dry_run 게이트", sim_spec(기계판독+산문 병기), 헌법 P1(브리프 결론 금지).

## 결정

### D0. 계획 도출 방식
- 추측이 아니라 실측 위에서. 설계 패널 워크플로(리더 5축 정독 → 독립 설계안 5관점(IR·전문가워크플로·학습루프·정성서술·
  포털UX) → 적대 비평 2렌즈 → 합성 → 완결성 비평)로 계획서 초안을 뽑고 사람이 확정. 결과는 `plan.md`.

### D2. 합성은 파일 쓰기·분할로 (1차 실행 사고)
- 1차 워크플로(23 에이전트·48분)에서 합성 에이전트가 100KB 급 문서를 최종 메시지로 반환하다 **앞부분 §1~§6.3 이 잘림**
  (반환 크기 상한). 완결성 비평도 잘린 본을 봤다. 후반부(§6.4~§10)와 어휘는 살아남아 정본으로 재사용.
- 완결성 비평이 **코드 대조로 확인한 실제 모순**은 그대로 반영한다 — `_restore_role` 이 personas[].role 접미(좌석 계약)를
  원본으로 덮어씀 → chair_template 조건부 `_RISK_SEAT_CONTRACT` 를 prompt_fn 에서 붙이는 것이 주경로. apps 제한이 타 앱
  도구(search_objects·check_design_rules·predict_sed…)를 제거 → `_RISK_KEEP_TOOLS` 앱 무관 통과. SSE status 에 persona 필드
  없음 → 좌석 귀속은 step 문자열·evidence.source 파싱. toulmin≠parse_retries 하한. C1 에서 RA 의존 제거. parse_risk_spec 은 P0.
- 재실행은 resume(리더·설계·비평 18개 캐시) + 합성부만 교체: spine(공통 어휘 정본) → 섹션 작성기 5 병렬(파트 파일 Write)
  → 통합기(plan.md 조립) → 완결성(파일 Read) → 수정(Edit in-place). 에이전트 반환은 짧은 JSON 만.

### D3. 계획 검토 결과 (2026-08-31, plan.md 정본 확정)
- 2차 워크플로(29 에이전트·57분·4.4M 토큰)로 `plan.md`(§0~§10, 366K자) 생성. 2차 완결성 판정 "조건부 통과 — 수정 후
  착수 가능", 지적 실질 3건(`_RISK_READ_TOOLS` 게이트 위치는 `_narrow` 가 아니라 `_g` 조립식 / evidence 예산은 라인
  오버헤드 포함 / ckey 가 부피 버킷으로 리비전 간 바뀜 → 결정론 pair 대응 승계)이 수정 단계에서 반영됨을 본문에서 확인.
- **직접 정독**(§1·§3.4·§4·§5.6~5.9·§6.5·§6.8~6.9·§8.4·§9·§10)으로 6기준 충족 확인 — (1) diff/상태→서술은 원자(finding·
  gain·character_statement)+cites+L0~L4 스택, (2) 재사용은 prior_evidence E0~E9 예산표 + 과제 무관 키(ckey·alias_key·
  subject_key)+별칭 사전+원장 상속, (3) 성격은 8 facet 통제 어휘·dissent 보존, (4) 회계는 PK(target_key, agent_key)+
  부분 유니크+상태기계+불변식, (5) 학습은 delta_priors→patterns→rules→predictor 승격+라벨 지표, (6) additive 변경 목록·
  건드리지 않을 것·회귀 검사·반영 절차. 단계마다 수치 통과 기준과 "이 단계만으로 얻는 것" 있음.
- **코드 인용 실측**: 계획이 인용한 deliberation.py 줄번호(`_g` 1897·`_narrow` 1916·`_amap` 1915·`_FREE_ALLOW` 1233·
  `_FREE_DENY` 1241·`_MATERIAL_TOOLS` 1251·`doc_title` 2375) 정확 일치, `_restore_role` 1360·`_persona_round` 877·
  반대석 append 2076 은 ±2줄. `_restore_role` 이 description 있으면 제공 role 을 버리는 동작 확인 — 좌석 계약을 :2044
  직후 role 접미로 붙이는 설계가 맞다.
- 1차 산출(doc_20·doc_22)은 잘린 본이라 폐기, plan.md 가 유일 정본. 워크플로 산출 파트 파일은 scratchpad 에만.
- 남은 리스크: 문서가 커서 개요 페이지(artifact)로 진입점 제공. P0 착수 전 §10 (1)(2)(3)(10) 사용자 결정 필요.

### D1. 조립 우선 (신규 최소화)
- IR 소스는 forge 들, 그래프 저장은 RA KG(타입 확장 API), 서술·코퍼스는 AIDataHub(레코드+전문가 RAG), 회계·스냅샷 원본은
  포털 sqlite, 심사는 기존 심의 엔진의 **신규 chair_template + 배치 오케스트레이션 래퍼**. 새로 만드는 건 IR 어댑터·diff
  엔진·심사 Job·커버리지 회계·코퍼스 인덱싱.

## 열린 질문 (사용자 결정 필요)
- ODB hub 가 내주는 것(API/포맷). 크로스도메인 부품 명명 규칙 유무. 저장소 선택(RA KG 확장 vs 별도). 전문가 범위(전체 발굴
  vs HW/XD 큐레이션). 리스크를 가르는 디멘전 범위.
