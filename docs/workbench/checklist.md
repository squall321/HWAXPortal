# 워크벤치 체크리스트

[PLAN.md](PLAN.md) 의 단계를 실행 항목으로 편 것이다. **착수 전이라 전부 미체크다.**

S0 은 사용자 몫이고 나머지와 병렬이다. S1 은 S0 없이 시작할 수 있다.

---

## S0 · cae00 API 수집 (사용자, 30분)

**실행 절차는 [odb-request.md](odb-request.md) 에 따로 있다.** 그 문서 하나만 보고 cae00 에서
할 수 있게 썼다. 여기서는 완료 여부만 센다.

- [ ] `fixtures/odb-hub/tools.json` — odb 도구 목록 + `args_schema`
- [ ] `fixtures/odb-hub/apps.txt` — 앱 키
- [ ] `fixtures/odb-hub/samples.json` — 읽기 도구 응답 표본
- [ ] `fixtures/odb-hub/sed-mapping.md` — SED 필수 10개 대조표(**"없다" 도 답이다**)
- [ ] 세 줄 메모 — 잡 수명 · 파일 주는 법 · 오래 걸리는 도구 유무

## S1 · 레시피 저장소 + 실행기 + 최소 화면 (가장 큰 덩어리)

### 격리 — 이게 "챗에 지장 없음" 의 실질이다
- [ ] **자기 `asyncio.Semaphore`** (포털 `agent_semaphore` 재사용 금지 — 넘치면 챗이 429)
- [ ] **자기 `httpx.AsyncClient`** (포털 `agent_client` 재사용 금지 — read 타임아웃이 없어
      풀을 먹으면 챗이 조용히 멈춘다)
- [ ] **자기 sqlite + `PRAGMA journal_mode=WAL`** (포털 sqlite 4곳은 WAL 이 없다.
      `HWAXRisk/backend/app/risk_store.py:599` 가 선례)
- [ ] sqlite 호출을 `to_thread` 로 (포털은 async 안에서 동기 sqlite 를 부른다 — 그 함정 회피)
- [ ] agent-server 는 **안 쓴다**

### 저장소 등록 — 네 곳 전부. 하나만 빠져도 조용히 샌다
- [ ] `infra/services.yaml` `classes:` 에 1줄 (안 하면 이관기·DB동기화가 존재를 모른다)
- [ ] `infra/scripts/start.sh:56` env 키 하드코딩 목록에 1줄 (안 하면 경로가 컨테이너에 안 간다)
- [ ] `infra/scripts/backup-local.sh:202` 기본 튜플에 1줄 (안 하면 **백업에서 빠진다**)
- [ ] `backend/app/config.py` Settings 필드 1개

### 모델
- [ ] 레시피 — `{id, version, title, vars[], steps[]}`
- [ ] 변수 — `{key, label, type, values?, required, why?}`. `why` 는 **왜 물어보는지**
      (`pkg_type` 처럼 유도 불가한 값에 필수)
- [ ] 단계 — `{tool, args, save?, gate?}`. **치환 `{{var}}` 과 추출 `save` 두 가지뿐**
- [ ] 런 — 단계마다 도구·**전문 인자**·**전문 결과**·시각·소요·성공 여부
- [ ] 레시피 판본 — 고치면 새 판본. 런은 어느 판본으로 돌았는지 박는다
      (HEAXHub `app_version_id` 방식)

### 실행기
- [ ] `invoke_tool` 경유 (인가·캐시·사용자 위임·감사를 그대로 탄다)
- [ ] 사용자 명의 PAT — `_chat_user_pat`(`backend/app/agent/routes.py:223`) 과 **같은 방식**.
      ⚠ 30분 창 결정적 발급을 반드시 지킨다(매번 새로 찍으면 캐시가 옛 토큰을 물고 조용히 죽는다)
- [ ] `dry_run` 기본값
- [ ] `gate: human` — 그 단계에서 멈추고 사람 확인을 받는다
- [ ] 실패 시 **어느 단계에서 왜** 멈췄는지 남기고 정지. 재개 가능
- [ ] ⚠ `invoke_tool` 이 막는 것 — `delete_`·`remove_`·`cancel_`·`purge_`·`destroy_` 접두사와
      `_control`·`_set_state` 접미사. 레시피가 그런 도구를 쓰면 **저장 시점에 거절**한다

### 화면
- [ ] 레시피 목록 / 상세 / 판본
- [ ] 단계별 실행(한 단계씩) + 런 이력
- [ ] **"레시피로 저장"** — 런에서 레시피를 뽑고, 어느 인자가 변수인지 사람이 표시
- [ ] 실행 화면에서 변수 입력 → 한 번에 재생

### 접점 (챗·심의 0줄)
- [ ] `backend/app/main.py` — import 1줄 + `include_router` 1줄. **`:156` SPA 폴백보다 위**
- [ ] `frontend/src/App.tsx` 라우트 1개 · `AppHeader.tsx` 메뉴 1개
- [ ] `backend/config/access.yaml` `features:` 에 `workbench` (코드 0 · 재기동 0)
- [ ] `frontend/vite.config.ts:18-26` dev 프록시 1줄
- [ ] ⚠ SSE 를 `/agent/` 밖으로 내면 nginx **두 파일**을 같이 고쳐야 한다
      (`infra/nginx/hwax.conf.tmpl:74-93` + `gen-nginx-conf.sh:173-184`). **안 쓰는 쪽이 낫다** —
      v1 은 폴링으로 충분하다
- [ ] ⚠ `systems.yaml` 타일을 만들면 `access.yaml` `platforms:` 에도 넣어야 한다
      (`backend/tests/test_access_control.py:28-36` 이 강제)
- [ ] `backend/config/changelog.yaml` 에 사용자가 겪는 변화

### 검증
- [ ] **챗·심의 파일 0개 변경**을 diff 로 확인
- [ ] dev 에서 도구 2~3개짜리 레시피(예: STEP 반입 → 파트 조회 → 보고서 초안)를
      만들어 저장 → 변수 바꿔 재생
- [ ] 챗을 동시에 돌려 **느려지거나 429 가 나지 않는지** 확인

## S2 · 과제 키 레지스트리 (작다)

- [ ] 매핑 표 — StepForge `project_id`(24-hex) · DynaForge `session_id` ·
      ThermalShock `project`(문자열) · ReportArchive `project` · HWAXRisk `target_key`
- [ ] 이름·코드로도 찾기 (StepForge 가 이미 그렇게 한다)
- [ ] 한 과제의 앱별 산출물 모아 보기
- [ ] 검증: 실제 과제 하나로 다섯 앱을 오가며 키가 안 끊기는지

## S3 · ODB 어댑터 + 열충격 레시피 (S0 선행)

- [ ] 고정물로 어댑터 작성 — odb-hub 산출 → SedInput 필수 10개
- [ ] `pkg_type` 은 **영구 변수**(유도 불가). `why` 에 이유를 적는다
- [ ] dev 완주 시험 — ODB 단계가 "사람이 채우는 칸" 으로 내려간 상태
- [ ] **cae00 실주행 검증** — 여기서만 진짜 확인된다
- [ ] 워피지 3인자(`copper_imbalance_pct`·`stackup_asymmetry`·`board_thickness_mm`)도
      같은 다리로 열리는지
- [ ] ⚠ 보고서 경로 — 계산기는 `create_report_from_run` 을 **못 쓴다**(반입 해석 런 전용).
      `create_report_draft` 쪽이고 `suggest_report_tags` 가 필수다(안 달면 검색에서 사라진다)
- [ ] ⚠ `pcb_warpage_surrogate` 의 합성 데이터 경고를 런 기록에 싣는다

## S4 · 일괄 재생 (S1~S3 이 서면 작다)

- [ ] 레시피 1개 × 과제 N건 → 비교표
- [ ] 동시 실행 상한 + `dry_run` 기본
- [ ] 실패한 과제를 건너뛰고 계속 + 무엇이 왜 실패했는지 표에 남긴다

## S5 · 챗 → 레시피 제안 (선택, 관측 개선 선행)

관측 개선 — 워크벤치와 무관하게 그 자체로 값어치가 있다.
- [ ] `on_tool_start`/`on_tool_end` 의 `event["run_id"]` 를 status 에 싣는다
      (`HWAXAgentServer/app.py:2607`·`:2633` — **이미 손에 있는 값**)
- [ ] 인자 절단을 하나로 통일 (지금 네 갈래 · 셋은 표시조차 없다.
      `deliberation.py:2361` 의 `…#sha1[:6]` 가 유일한 선례)
- [ ] `activity[]` 에 `ts`·`ms`·`ok`·`app` (프론트 타입엔 `ts` 가 이미 선언돼 있는데
      서버가 저장하지 않는다)
- [ ] 합격 기준 — `predict_sed` 병렬 5회에서 **결과 5개가 각각 다른 인자에 짝지어질 것**
      (지금은 프리뷰 5개가 전부 같다)

그 뒤에
- [ ] 런 기록 → 레시피 초안 제안
- [ ] 어느 인자가 변수이고 어느 것이 상수인지 사람이 확정. **자동 저장 금지**

## S6 · 리스크 패턴화 (가장 뒤)

- [ ] 선행 결손 — `frontend/src/components/chat/delibTaxonomy.ts:5-12` `JobId` 에
      `risk-review` 추가 (엔진 양쪽·MCP 는 이미 지원하는데 **웹에서만 못 고른다**)
- [ ] 선행 결손 — `frontend/src/api/conversations.api.ts:6` `ConvKind` 에 `'risk-review'`
      (백엔드는 받는데 프론트가 없어 `ChatContext.tsx:457` 필터에서 조용히 걸러진다)
- [ ] 결과 → `risk_add_finding`. ⚠ `cites` 0건이면 **422**, `claim`·`warrant` 는 자유 산문 —
      근거를 대는 자리가 완전 자동이 아니다
- [ ] `risk_taxonomy` 통제 어휘 사용 (38 메커니즘 · 동의어 18 — **추측하면 422**)

---

## 착수 전

- [ ] PLAN §7 결정 — S0 시점, 첫 레시피를 무엇으로 할지
- [ ] S1 을 먼저 시작할지(S0 과 병렬 가능) 확인
