# 워크벤치 체크리스트

[PLAN.md](PLAN.md) 의 단계를 실행 항목으로 편 것이다. **착수 전이라 전부 미체크다.**
결정 대기(§8)가 풀리기 전에는 P0 만 독립 착수 가능하다.

---

## P0 — 관측 충실도 (워크벤치 밖, 선행 필수)

관측할 수 없는 절차는 기록할 수 없다. 이것만으로도 챗 활동 패널과 핸드오프 근거가 정확해진다.

- [ ] `on_tool_start`/`on_tool_end` 의 `event["run_id"]` 를 status 이벤트에 싣는다
      (`HWAXAgentServer/app.py:2607`·`:2633` — **이미 손에 있는 값이다**)
- [ ] 같은 `run_id` 를 심의 경로에도 싣는다(`deliberation.py` 의 자유 조회 기록)
- [ ] 인자 절단을 하나로 통일한다 — 지금 네 갈래다
      (`app.py:1954` 220자 · `app.py:2789` 200자 · `deliberation.py:2361` 140자+지문 ·
      `app.py:2869` 없음). **`…#sha1[:6]` 방식이 유일하게 절단을 표시한다**
- [ ] 포털 `activity[]` 에 `ts`·`ms`·`ok`·`app` 을 싣는다
      (`backend/app/agent/routes.py:1363`. 프론트 타입 `types/chat.ts:13` 에는 `ts` 가
      **이미 선언돼 있는데 서버가 저장하지 않는다**)
- [ ] `activity[:60]` 앞쪽 절단이 맞는지 재검토 — `turns` 는 반대로 뒤쪽을 남긴다
- [ ] 검증: `predict_sed` 병렬 5회를 실제로 돌려 **결과 5개가 각각 다른 인자에 짝지어지는지**
      확인한다(지금은 프리뷰 5개가 전부 같다 — 이것이 P0 의 합격 기준이다)
- [ ] 회귀: 챗 응답 내용·SSE 이벤트 종류가 변하지 않았음을 테스트로 고정

## P1 — 과제 키 레지스트리

- [ ] 다섯 키의 매핑 표 설계 — StepForge `project_id`(24-hex) · DynaForge `session_id` ·
      ThermalShock `project`(문자열) · ReportArchive `project` · HWAXRisk `target_key`
- [ ] 키 해석 도구(이름·코드로도 찾게) — StepForge 가 이미 그렇게 한다(D-211)
- [ ] 한 과제의 앱별 산출물을 모아 보여 주는 조회
- [ ] 검증: 실제 과제 하나로 다섯 앱을 오가며 키가 끊기지 않는지

## P2 — 레시피 저장소 + 인벤토리 화면

- [ ] 앱 골격 — 리포·`.portal/manifest.yaml`·`mcp:{expose:true}`
- [ ] sqlite **WAL 켜기**(`risk_store.py:599` 선례. 포털 sqlite 4곳은 WAL 이 없다)
- [ ] 데이터 경로 — `HEAX_DATA_DIR` 규약(HEAX 앱은 `HWAX_DATA_ROOT` 를 안 탄다)
- [ ] 레시피 스키마 + JSON Schema 검증 (KooRemapper `catalog.py` 의 Draft2020 방식)
- [ ] 레시피 CRUD·판본·태그·검색
- [ ] MCP 표면 — `list_recipes` · `describe_recipe` · `run_recipe` · `recipe_runs`
      (게이트웨이에 절차 카탈로그 도구가 **0개**다 — 없으면 검색에서 안 보인다)
- [ ] 포털 창 — `App.tsx` +1 라우트 · `AppHeader.tsx` +1 메뉴 · `systems.yaml` +1 타일 ·
      `access.yaml` +1 그룹(**코드 0·재기동 0**)
- [ ] dev 프록시 — `frontend/vite.config.ts:18-26` 에 prefix 1줄
- [ ] ⚠ SSE 를 `/agent/` 밖으로 내면 nginx 두 파일을 같이 고쳐야 한다
      (`infra/nginx/hwax.conf.tmpl:74-93` + `gen-nginx-conf.sh:173-184`)
- [ ] ⚠ `test_access_control.py:28-36` — `systems.yaml` 타일을 만들면 `access.yaml`
      `platforms:` 에도 넣어야 한다
- [ ] 검증: 챗·심의 파일 **0개 변경**을 diff 로 확인

## P3 — 실행기 + 슬롯·공급자

- [ ] 실행기 — `invoke_tool` 경유, 단계 순서·의존, 체크포인트·재개
- [ ] **자기 세마포어·자기 httpx 클라이언트**(포털 `agent_semaphore`·`agent_client` 재사용 금지)
- [ ] `dry_run` 기본값
- [ ] 슬롯 모델 — 공급자 없으면 **사람에게 묻는 칸**(실패 아님)
- [ ] `gate: human` — `publish_report` 2단 확인 등 의도된 사람 자리를 레시피에 박는다
- [ ] 런 기록 — SmartTwinMCP `audit_events` 모양
      `(occurred_at, actor, tool@version, action, target, detail JSON=args)`
- [ ] 판본 고정 — 도구 판본 불일치 시 **경고하고 멈춘다**(HEAXHub `app_version_id` 방식)
- [ ] 능력 등록 공백 채우기 — `describe_data_capability("CAD")` 의 `capability_tools` 가
      **0건이다**(SIM 은 2건)
- [ ] 잡 정규화 어댑터 — 8개 앱의 상태 enum·id 형식·인자 봉투를 하나로
- [ ] 검증: 열충격 레시피를 ODB 없이 끝까지 — 사람이 채우는 칸 5개로 완주

## P4 — ODB 연동

- [ ] 결정 대기 §8-1 이 풀린 뒤 착수
- [ ] `ODB/documents/MCP_INTEGRATION.md` 447줄 규격 구현
      (서비스 계층이 이미 인터페이스 독립이라 "서버를 얹기만" 하면 된다)
- [ ] ⚠ 규격서 §2.2 — **지오메트리를 도구 결과로 반환하지 않는다**(가장 중요한 규칙)
- [ ] 도구 13종 — `odb_ingest`·`odb_list_components`·`odb_extract_parts`·
      `odb_copper_ratio`·`odb_interposer_ratio`·`odb_run_checklist` 등
- [ ] SedInput 어댑터 — ODB 산출 → `predict_sed` 의 필수 10개
- [ ] 검증: 실제 ODB++ 로 SED 까지 완주, 사람 입력이 **`pkg_type` 하나**로 줄었는지
- [ ] 워피지 3인자(`copper_imbalance_pct`·`stackup_asymmetry`·`board_thickness_mm`)도
      같은 다리로 열리는지 확인

## P5 — 학습(챗 → 레시피 제안)

- [ ] P0 완료가 전제다. 미완이면 착수 금지
- [ ] 런 기록 → 레시피 초안 제안기
- [ ] 어느 인자가 **과제마다 바뀌는 값(입력)** 이고 어느 것이 **고정(상수)** 인지 구분
- [ ] 사람이 확인·편집하는 화면. **자동 저장하지 않는다**
- [ ] 검증: 실제 챗 한 건에서 레시피를 뽑아 다른 대상으로 재생

## P6 — 일괄 재생 + 리스크 패턴화

- [ ] 선행 결손 — `frontend/src/components/chat/delibTaxonomy.ts:5-12` `JobId` 에
      `risk-review` 추가(엔진 양쪽·MCP 는 이미 지원하는데 **웹에서만 못 고른다**)
- [ ] 선행 결손 — `frontend/src/api/conversations.api.ts:6` `ConvKind` 에 `'risk-review'`
      (백엔드는 받는데 프론트가 없어 `ChatContext.tsx:457` 필터에서 조용히 걸러진다)
- [ ] 과거 과제 N건 일괄 재생 + 비교표
- [ ] 결과 → `risk_add_finding`. ⚠ `cites` 0건이면 422, `claim`·`warrant` 는 자유 산문 —
      **근거를 대는 자리가 완전 자동이 아니다**
- [ ] `risk_taxonomy` 의 통제 어휘 사용(38 메커니즘·동의어 18 — **추측해 넣으면 422**)
- [ ] ⚠ 합성 데이터 모델 경고를 런 기록에 싣는다(`pcb_warpage_surrogate`)
- [ ] 자원 상한 — 동시 실행 수·배치 크기

---

## 착수 전 확인

- [ ] PLAN §8 결정 5건에 대한 사용자 답
- [ ] cae00 `odb-hub` 의 실제 도구 목록(§9 — dev 에서 확인 불가)
- [ ] `/home/koopark/claude/ODB` 서비스 함수 시그니처가 규격서 13종과 맞는지
