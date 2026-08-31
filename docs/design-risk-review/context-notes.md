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

### D4. 토폴로지 B — 자산은 HEAX 앱 `hwax-risk`, 포털은 메뉴/창 (2026-08-31, 사용자 결정)
- **질문.** 재활용을 위해 별도 포털/DB 가 필요한가. 재분석 시 같으면 드랍·다르면 add 가 가능한가.
- **답.** 별도 DB 는 A 계획에도 이미 있었다(포털 내부 sqlite). 다만 이 자산은 과제 수십 개·수년치가 쌓이는 **장기 자산**이라
  포털 릴리스·박스 수명에 묶이는 A 보다, thermal_shock MCP 선례처럼 **데이터를 품은 HEAX 앱**으로 분리하는 B 가 맞다 —
  `HEAX_DATA_DIR` 영구 경로 + `appdata-to-drive.sh` 백업 + 매니페스트 `mcp:{expose}` 로 게이트웨이 자동 흡수 + Caddy
  forward_auth 가 `X-Heax-User-*` 로 신원 전달. 포털에는 '심의'와 별개 메뉴 하나(창)만.
- **멱등 규칙(재분석).** 입력 같음 → `(project_id, ir_hash)` 로 새 행 없음. 의견 같음 → 드랍이 아니라 `cluster_key` 병합으로
  `support+1`(재현성 신호 보존). 다름 → (a) 입력 변경=새 타깃·옛 것 superseded/stale, (b) 같은 입력 다른 의견=dissent/contested
  보존, (c) 코드 버전 변경=버전 스탬프 재계산. 외부 반영 UPSERT(external_id)·RA create_object 멱등.
- **불변.** rr_* 스키마·원자·해시·prior_evidence E0~E9·커버리지 상태기계·학습 루프·엔진 additive 항목. 바뀌는 건 위치·
  호출 경로·인증·P0 산출물.
- **실측 지형.** HEAX 매니페스트 v2(thermal_shock 예), integration_launcher 가 `var/app_data/<id>` 를 `HEAX_DATA_DIR` 로 주입,
  Caddy `/apps/<id>/*` strip_prefix, authz 2xx 시 `X-Heax-User-*` 복사, 포털→heax 는 jwt-handoff(localStorage bearer, 쿠키 아님)
  → 포털 SPA 가 앱 REST 를 직접 fetch 못 함 → 포털 메뉴는 앱 UI 를 여는 방식이 자연스러움. 게이트웨이 rest_proxy 에 heax
  사이트 없음(설정 변경 필요 시 §10). odb-hub 는 external_link 앱이고 게이트웨이 백엔드에 없음(계약만 유지).
- **개정 방식.** 워크플로(리더 2 → 섹션 개정기 4 순차 in-place → 일관성 스위프 → 완결성 → 수정). 원본은 커밋 396b720.

### D5. 프로젝트 경로·이름 관례 (2026-08-31, 실측 — 다른 앱과 동일하게)
- 리포: `~/claude/<PascalCase>` — 앱 리포는 ThermalShockMCP·WebResearchMCP·PaperIngest, HWAX 계열은 HWAX 접두(HWAXPortal·
  HWAXAgentServer·HWAXMcpGateway). → **`/home/koopark/claude/HWAXRisk`**, GitHub **`squall321/HWAXRisk`**(다른 앱 전부 squall321).
- HEAXHub 등록: `HEAXHub/integrations/<kebab>/.portal/manifest.yaml` **매니페스트 복사본만**(심볼릭 링크 아님, 리포의
  `.portal/manifest.yaml` 과 동일 파일). `source:{type: git, url: github, ref: main}` 으로 5분 주기 스캔·재빌드가 GitHub 에서
  받아온다. → **`HEAXHub/integrations/hwax-risk/`**, 매니페스트 **`id: hwax_risk`**, Caddy **`/apps/hwax_risk/`**, MCP
  `/apps/hwax_risk/mcp` → 게이트웨이 백엔드 `heax-hwax_risk`.
- 리포 표준 구성(ThermalShockMCP 기준): `app/{main,config,mcp_server,…}.py` · `tests/` · `pyproject.toml`(mcp>=1.10,<2 핀 —
  2.0 이 FastMCP 제거) · `README.md` · `docs/` · `checklist.md` · `context-notes.md` · `.portal/manifest.yaml` · `.gitignore`
  (.venv/__pycache__/egg-info/.pytest_cache/.bkit/.koo-llm-sessions) · `data/`(HEAX_DATA_DIR 폴백). 여기에 `frontend/`(SPA) 추가.
- 데이터: `HEAX_DATA_DIR`(=HEAXHub/var/app_data/hwax_risk) 우선, 없으면 리포 `data/` 폴백(thermal_shock config.py 패턴).

### D6. 어떤 LLM 이 점검했는지 기록한다 — 모델 출처(provenance) 축 추가 (2026-08-31, 사용자 지적)
- **갭(실측).** 계획의 `rr_panels` 는 `engine(web|mcp)`·`tool_mode` 만 있고 **모델 식별이 없다**. 엔진도 SSE 에 모델 이벤트가 없고
  agent-server 는 `GET /health` 의 `model`(=`VLLM_MODEL`, 기본 qwen2.5-7b-dev)·`vllm`(base_url)만 노출한다(app.py:2419). 같은 좌석·
  같은 브리프라도 모델이 다르면 의견의 성격·정밀도가 다르고, 학습 루프(§7)가 모델을 섞어 세면 지표가 오염된다. 선례 — 포털
  `message_vectors.model`(conv_store.py:59·179, 임베더 교체 시 옛 벡터 혼입 방지용 model 조건).
- **결정.** 패널 단위 `rr_panels.model_json` 을 추가하고 원자(finding·opinion·character)는 panel_id 로 승계한다.
  `model_json = {runtime: 'agent-server'|'claude-code', provider: 'vllm'|'anthropic'|…, model: '<served name>', endpoint_host,
  captured: 'health_snapshot'|'caller_reported', engine_rev: <deliberation.py 또는 hwax-deliberate.js 의 git sha>,
  chair_rev: <chair_template 텍스트 sha>, seat_contract_rev}`.
  - 웹 러너 — 패널 시작 직전·직후 agent-server `/health` 를 읽어 `model`·`vllm` 을 담고 둘이 다르면 `quality.flag=model_changed_midrun`.
  - MCP 경로 — `risk_submit_panel_result(model?)`·`POST /panels/{id}/complete{model?}` 로 **호출자 신고값**(actor 와 같은 등급,
    `captured:'caller_reported'`, 미검증). L2 오케스트레이터 `hwax-risk-review.js` 는 args.model 을 그대로 넘기고 없으면 `unknown`.
  - 커버리지 원장 — 종결 판정은 모델 무관(한 번 봤으면 넘어감)이되 `rr_coverage.model` 열을 두어 진행판·통합 보고서에 **모델 혼합 표**
    (모델별 패널 수·strong 비율·contested)를 싣는다. 모델 교체 시 재심은 자동이 아니라 Settings `risk_recheck_on_model_change`(기본 off) 로
    `carried` 를 다시 `pending` 으로 돌리는 명시 동작.
  - 학습 루프(§7) — delta_priors·patterns 집계는 `model` 로 층화하고, 승격 조건에 "서로 다른 모델 ≥2 에서 재현" 을 선택 가드로 둔다.
  - 보고서·브리프 — RA 보고서 background 와 `prior_evidence` E0 에 모델명을 표기해 다음 과제가 "무엇이 본 의견인지" 알게 한다.
- **반영 위치(개정 워크플로 종료 후 편집 — 동시 편집 회피).** plan.md §5.2 DDL(rr_panels.model_json·rr_coverage.model) · §6.7 러너
  1·7단계(health 스냅샷) · §6.11 MCP 경로(caller_reported) · §7.4 층화·승격 가드 · §4.5 seat_opinion 봉투 `model` · §8.3.4 도구 인자 ·
  §9 P1 테스트(모델 기록·midrun 변경 플래그) · checklist P1 항목. 스캐폴드(P0 4표)에는 rr_panels 가 없어 지금 변경 없음.

### D7. P0 스캐폴드 실측으로 드러난 계획 정정 사항 (2026-08-31, 개정 워크플로 종료 후 plan.md 에 반영)
- **§0.4.1 의 `Mount('/mcp')` 권고는 틀렸다(실측).** Starlette `Mount('/mcp')` + `streamable_http_path='/'` 는 `POST /mcp` 에 307 → `/mcp/`
  리다이렉트를 내고 MCP 클라이언트·게이트웨이는 따라가지 않는다. `mount('/', mcp_app)`(thermal_shock 방식)는 동작하지만 StaticFiles
  `'/'` 와 공존 불가. **정본은 MaterialTwinWeb 패턴** — `mcp._session_manager = None` 후 `streamable_http_app().routes` 의 `Route('/mcp')`
  를 메인 라우터에 이식(exact 매칭, 리다이렉트 없음), StaticFiles 는 마지막에 `'/'`. (MaterialTwinWeb/backend/app/main.py:53~66)
- **레이아웃은 fastapi_react 로 확정** — 계획 §0.4.1·§8.2.1 대로 `backend/`(app·tests·pyproject·scripts/heaxhub-build.sh) + `frontend/`
  (Vite base './', 상대경로 fetch), health `/api/health`, REST `/api/…`(v1 접두 없음). 첫 스캐폴드가 fastapi(app/ 루트)·`/health`·
  `/api/v1` 로 나와 전환 워크플로로 정합(P1 에서 옮기면 더 비쌈).
- **이름 정합** — env 접두는 **`HWAXRISK_`**(개정기가 plan 전체 124곳을 이 표기로 통일했고 HEAX 앱 선례 `THERMALSHOCK_DATA_DIR`·
  `MATERIALTWIN_MCP_*` 와 같은 '구분자 없는 앱명' 관례라 채택. 전환 워크플로가 만든 `HWAX_RISK_DATA_DIR` 는 후속 정합 패스에서
  `HWAXRISK_DATA_DIR` 로 되돌린다), DB `risk_review.db`(`.db` 여야 appdata-to-drive.sh 가
  `sqlite3 .backup` 원자 스냅샷으로 교체 — `.sqlite` 는 WAL 내용이 빠진 사본이 된다), `PRAGMA user_version` 이 스키마 버전 정본이고
  `schema_migrations` 는 이력표(§5.2.5 (6) 과 일치).
- **신원 헤더는 service 모드에서 오지 않는다(재확인).** HEAXHub proxy_manager `_build_route` 는 launch.mode=service 앱에 forward_auth 만
  세우고 `copy_identity` 없음 → `X-Heax-User-*` 는 도착하지 않고 클라이언트 위조값이 통과한다. 스캐폴드 identity.py 는
  `source='header_unverified'` 스탠드인, P1 에서 heax `GET /api/v1/auth/me` 되묻기(§8.2.8)로 교체.
- **rr_ 표는 33개다(32 아님).** §5.2.2 DDL 을 바이트 그대로 옮기면 `rr_delta_contrib`(§4.7.1 추가)까지 33표·인덱스 36 — 요약 문구
  '32표' 7곳을 33 으로 고쳤다(정합 커밋 4cf8ed5 이후 코드 `_DDL_V1_SQL` 은 plan DDL 과 diff 0, test_store 가 33 단언).
- **identity 불통은 P0 에서 anonymous.** §8.2.8 은 401→401·5xx/불통→503 이나 P0(읽기 전용)는 401/불통/없음 전부 anonymous(불통은
  캐시하지 않음)로 구현했고 P1 쓰기 라우트 확장 시 401/503 구분을 재결정한다. 같은 이유로 `PUT /me/portal-pat` 의 포털 검증
  불통이 지금은 422 `pat_invalid` 로 보이는데, P1 에서 503 `pat_verify_unavailable` 로 분리하는 것을 §8.2.3 오류 표에 제안한다.
- **HEAXHub 매니페스트 스키마 파일은 v1** (`schemas/manifest.schema.json` const 1). v2 검증은 backend `manifest_validator` 분기
  (`manifest.schema.v2.json`)와 같은 기준이어야 하고, `mcp`·`source.ref` 확장 키는 validator 도 통과시킨다(thermal-shock-mcp 동일).

### D1. 조립 우선 (신규 최소화)
- IR 소스는 forge 들, 그래프 저장은 RA KG(타입 확장 API), 서술·코퍼스는 AIDataHub(레코드+전문가 RAG), 회계·스냅샷 원본은
  포털 sqlite, 심사는 기존 심의 엔진의 **신규 chair_template + 배치 오케스트레이션 래퍼**. 새로 만드는 건 IR 어댑터·diff
  엔진·심사 Job·커버리지 회계·코퍼스 인덱싱.

## 열린 질문 (사용자 결정 필요)
- ODB hub 가 내주는 것(API/포맷). 크로스도메인 부품 명명 규칙 유무. 저장소 선택(RA KG 확장 vs 별도). 전문가 범위(전체 발굴
  vs HW/XD 큐레이션). 리스크를 가르는 디멘전 범위.
