# 절차 체크리스트

[PLAN.md](PLAN.md) 의 단계를 실행 항목으로 편 것이다. **착수 전이라 전부 미체크다.**

S0 은 사용자 몫이고 나머지와 병렬이다. S1 은 S0 없이 시작할 수 있다.

> **진행 중 — S1.** 격리·저장소 등록 네 곳·모델·기계장치 둘·판정·실행기까지 섰다
> **S1 의 코드가 다 섰다** — 격리·저장소 등록·모델·판정·실행기·라우트·화면(커밋 `463ca77`
> 이후 5개, 백엔드 203 tests · tsc·빌드 통과). 남은 것은 **브라우저 실물 확인**이다.
> 챗·심의 파일 0개 변경, 새 pip·npm 의존성 0 을 매 커밋에서 확인한다. S1 의 소제목마다
**→ 검증** 한 줄이 있다 — 세션이 끊겨도 다음 세션이 어디까지 됐는지 그 줄로 안다.

---

## S0 · cae00 API 수집 (사용자, 30분)

**실행 절차는 [odb-request.md](odb-request.md) 에 따로 있다.** 여기서는 완료 여부만 센다.

- [ ] `fixtures/odb-hub/tools.json` — odb 도구 목록(앱 키로 고른 것) + `exposed_name`·`backend`·
      `original`·`args_schema`·`metadata`(annotations)·`collected_at`
- [ ] `fixtures/odb-hub/apps.txt` — `map` 집계 + **`apps` 배열(tool_count·reachable)** +
      사용자 PAT 로 `list_tool_apps(app="odb-hub")` 결과 한 줄 + 허브 버전 한 줄
- [ ] `fixtures/odb-hub/samples.json` — 읽기 게이트를 통과한 표본. 무인자 도구 전부 · 잡 정보 첫 호출 ·
      IC 계열로 좁힌 부품 목록 · 고의 실패 2건 · 항목마다 `ms`·`bytes`·`is_error`
- [ ] `fixtures/odb-hub/sed-mapping.md` — SED 필수 10 + 선택 5 + 워피지 5 대조(**"없다" 도 답이다**)
      + AP/PKG refdes 행 + `board_type` 어휘 + 쓰기·파괴 도구 표 + HWAXRisk 4도구 대조
- [ ] 메모 — 잡 수명·식별 · 파일 주는 법 · 오래 걸리는 도구와 상태 도구 이름 · 에러 코드 어휘 ·
      목록 상한 · 단위·면 · 시야·쓰기 명의 · resources 노출 여부
- [ ] 지우기 게이트 `grep` 0건 → 파일 단위 `git add` → 커밋 → **push** 완료

## S1 · 절차 저장소 + 실행기 + 최소 화면 (가장 큰 덩어리)

### 격리 — 이게 "챗에 지장 없음" 의 실질이다
- [x] **자기 `asyncio.Semaphore`** — 크기 `Settings.procedures_concurrency`(기본 2). 파이썬 기본값 1
      이면 직렬이다. `gate: human` 대기 실행은 슬롯을 놓는다. 넘치면 429 가 아니라 큐
- [x] **자기 `httpx.AsyncClient`** — read 타임아웃 **≥260초**(게이트웨이 120초 + 재연결 재시도 한 번을
      덮는다. 실행기가 게이트웨이보다 먼저 포기하면 쓰기가 뒤늦게 완료돼 `unknown` 만 늘린다)
- [x] **자기 sqlite** — 연결은 스레드별(`threading.local`) 또는 호출당 `connect`. 단일 연결을 스레드풀이
      나눠 쓰지 않는다(포털 4곳은 연결 1개 + Lock 이라 `to_thread` 로 감싸면 트랜잭션 경계가 섞인다).
      연결마다 `PRAGMA journal_mode=WAL; synchronous=NORMAL; busy_timeout=5000`(busy_timeout 은
      `backup-local.sh`·이관기가 `mode=ro` 로 동시에 여는 순간용). 쓰기는 `with conn:` 한 트랜잭션,
      메서드 단위 `asyncio.to_thread`. lifespan 종료에서 닫는다(`main.py:77-79` `agent_audit.close()` 옆)
- [x] 실행 하나에 MCP 세션 하나 — initialize 1회, 단계들은 같은 `mcp-session-id` 재사용, 종료·정지·예외
      시 `finally` 에서 `DELETE /mcp`. 게이트웨이 SDK 는 세션 유휴 만료가 없다
- [x] `main.py` 에서 절차 import·스토어 오픈을 try/except 로 감싼다 — 실패하면 라우터를 빼고
      `app.state.procedures_error` 에 남기며 포털(챗 릴레이)은 뜬다
- [x] `GET /procedures-api/health`(무인증) — 열렸으면 200 `{journal_mode, path}`, 아니면 503
- [x] agent-server 는 **안 쓴다**
- → 검증: 챗을 동시에 돌리며 재생 — 429·지연 없음. `/procedures-api/health` 가 `wal` 을 돌려준다

### 저장소 등록 — 네 곳 전부, 값까지. 하나만 빠져도 조용히 샌다
- [x] `infra/services.yaml` `portal.classes` 에 `procedures: {kind: sqlite, path: svc/portal/procedures.sqlite,
      current: backend/data/procedures.sqlite, env: PROCEDURES_STORE_PATH, fs: local, sync: mirror,
      needs_bind: true}` — `path` 는 반드시 `svc/portal/` 아래(`start.sh:53` 바인드 범위), `current` 는
      `backend/data/` 아래(`.gitignore` 앵커 — 이관기가 강제). `sync: mirror` = 실행은 사용자 데이터·prod 정본
- [x] `infra/services.yaml` 에 `procedures_artifacts: {kind: blob, path: svc/portal/procedures-artifacts, …}`
- [x] `infra/scripts/start.sh:56` env 키 목록에 `PROCEDURES_STORE_PATH`
- [x] `infra/scripts/backup-local.sh` **세 줄** — `:199` python3 인자에 `"${PROCEDURES_STORE_PATH:-}"` ·
      `:202` 튜플에 `"data/procedures.sqlite"` · `:203` 슬라이스 `[3:7]` → `[3:8]`. **튜플만 늘리면 `zip` 이
      짧은 쪽에서 멈춰 다섯째 파일이 오류 없이 빠진다.** 헤더 `:6`·`:195` 의 'sqlite 4' 를 5 로
- [x] `backend/app/config.py` `procedures_store_path: str = "data/procedures.sqlite"` · `procedures_concurrency` ·
      `procedures_max_steps`
- [x] 메모 — 새 클래스는 현행·목표 둘 다 없어 `absent` 라 첫 기동은 `backend/data/` 에 생기고 `/data` 로
      가는 것은 다음 `update-all` 2b 때다(`update-forges.sh` 는 이관을 안 부른다)
- → 검증: `./infra/scripts/backup-local.sh portal` 뒤 최신 tar 를 `tar -tzf` 로 열어 `procedures.sqlite` 가
  있다. `./infra/scripts/data-migrate.sh --check` 에서 procedures 가 보인다

### 모델 (`backend/app/procedures/models.py`, pydantic v2)
- [x] 절차 — `{id, owner_sub, visibility, title, created_by, latest_version}` + 판본
      `{version_id, version_no, spec_json, author_sub, created_at, derived_from_run}`
- [x] 변수 — `{key, label, type: string|enum|number|boolean|json, values?, required, why?}`. `why` 는
      **왜 물어보는지**(`pkg_type` 처럼 유도 불가한 값에 필수)
- [x] 단계 — `{backend, tool, schema_fp, expect, args, save?, gate?, raw?, unwrap?, warmup?}`.
      기계장치는 치환 `{{var}}` 과 추출 `save` 둘뿐이고 의미는 PLAN §2 표대로 **고정**.
      `expect` 는 `fast|slow|job` — `job` 은 저장 시점에 거절(PLAN §5-10)
- [x] 실행 — `{id, owner_sub, run_by, procedure_version_id?, inputs_json, origin: manual|replay, mode: plan|live,
      state, …}` + 단계 `{backend, tool, schema_fp, args(+sha256), result_gz/bytes/sha256, truncated, notes,
      state, ok, error, started_at, duration_ms, mode, identity_note, reused_from_run_id}` + `run_gate_acks`
- [x] 상태 CHECK — 실행 `queued|running|gated|done|failed|cancelled|unknown`, 단계
      `pending|running|done|failed|unknown|skipped`
- [x] `save` 점·인덱스 표기 파서 자체 구현(20줄 안팎, 의존성 0)
- → 검증: pytest — 치환 규칙(정확히 하나면 형 유지·섞이면 문자열)·`save` 추출·상태 CHECK

### 실행기 (`backend/app/procedures/runner.py`)
- [x] **실행은 요청 밖에서 돈다** — `POST /runs`·`POST /runs/{id}/steps` 는 `202` 로 즉시 돌려주고
      `asyncio.create_task`(자기 세마포어 안), 단계마다 sqlite 에 쓰고 화면은 `GET /runs/{id}` 폴링. 절차
      경로는 nginx catch-all(`hwax.conf.tmpl:95-97`·`gen-nginx-conf.sh:207-209`, 기본 60초)이라 동기로 두면
      nginx 는 504·uvicorn 은 완료 → 재시도 → 중복. **dev vite 프록시에선 재현되지 않는다**
- [x] 같은 단계 재실행 방지 — 단계가 `running` 이면 `POST …/steps` 는 409
- [x] 게이트웨이 호출 함수 — `upload.py:282 mcp_call` 의 방식(httpx JSON-RPC)만 따르고 **베끼지 않는다**.
      (a) `tools/call` 을 `name="invoke_tool", arguments={name: <별칭>, arguments}` 로 감싼다(파괴 도구
      거부는 `invoke_tool` 일 때만 검사) (b) `result.isError` 를 보존한다(`mcp_call` 은 버려서 `unknown tool`
      이 `{"raw"}` 로 성공 반환) (c) `content[]` 전부를 저장한다(`mcp_call` 은 `content[0]` 만)
- [x] 별칭 호출 — `f"{backend.replace('-','')}_{tool}"`. 저장 시 `/tools-map` 의 `map` 으로 노출 이름 →
      백엔드 키 해석
- [x] **사용자 명의 PAT** — `_chat_user_pat`(`backend/app/agent/routes.py:223`) 을 **단계 호출 시점마다** 찍어
      그 호출에만 싣는다. 실행 기록에 저장하거나 `gate: human` 뒤 재개·다음 단계에 재사용하지 않는다(exp 가
      창 시작+60분, 실측 401). 30분 창 결정성은 agent-server 캐시 얘기라 요건이 아니다(따라도 무해)
- [x] 단계 직전 검사 셋 — 실행 상태가 `running` 인가 · 소유자 `user_store.get(email).status == "active"` 인가 ·
      `schema_fp` 가 지금 `tools/list` 와 같은가(다르면 정지 + diff 표시, 자동 진행 금지). 셋이 PAT 발급의
      선행 조건이다
- [x] 실행 시작 전 사전검사 — 실행자 PAT 로 `tools/list` 를 받아 절차 단계 도구가 하나라도 없으면 한 단계도
      실행하지 않고 거절, 빠진 도구와 '내 권한' 링크를 보인다. 포털에서 권한을 재계산하지 않는다
      (access-control D-5). 실행 중간의 `forbidden:` 은 '권한 부족' 정지 사유로만 기록
- [x] RA 사전검사 — 연결 없음·워크스페이스 미선택을 **시작 전에** 말한다(막지는 않는다, W-63)
      ~~단계 중 `map[tool] == "reportarchive"` 가 있으면 `user_store.get_connection(email,~~
      service="reportarchive")` 확인, 없으면 시작 거절(`routes.py:969-974` 와 같은 400 문구). 단계마다
      `identity_note`(as-conn·as-user·service)를 사전검사 결과로 기록(게이트웨이는 결과에 안 돌려준다)
- [x] 예약 변수 `{{me.email}}`·`{{me.sub}}`·`{{run_id}}`
- [x] **must-gate** — `publish_report`·`request_unpublish`·`trash_report`·`restore_version`·`job_stop`·
      `risk_add_finding`·`add_report_tags` 단계에 `gate: human` 없으면 저장 거절. `submit_*`·`run_job`·
      `register_*`·`upload_*`·`ingest_*`·`train_model` 은 저장 시 경고. 게이트웨이 `_INVOKE_DENY`
      (`gateway.py:1100-1101`)는 백스톱일 뿐 — 앱 접두 이름(`odb_delete_job`)은 안 걸린다. S0 의 쓰기·파괴
      도구 표를 받으면 그것이 odb 쪽 정본
- [x] `save` 로 `confirm_token`·`*_token` 을 뽑아 다음 인자로 쓰는 절차는 저장 거절
- [ ] `publish_report` 게이트 — preview(카드) → 사람 확인 → preview 재호출 → 그 토큰으로 즉시 publish.
      대상이 다르면 다시 멈춤
- [x] 게이트 확인 — 소유자만, `(run_id, step, sha256(치환 인자))` 귀속, `run_gate_acks` 에 기록
- [x] **`dry_run` 두 뜻**(PLAN §5-7) — 계획 모드 기본. 스키마에 `dry_run` 없는 도구의 `args` 에 적혀 있으면
      저장 거절. 단계마다 `mode: plan|dry|live`
- [x] **단계 판정 규칙**(PLAN §5-6) — 실행 전 최상위 `required`·`properties` 대조(모르는 키 저장 거절).
      실행 후 `isError` · JSON 파싱 · `ok===false`/`error`/`errors[]`/`refused` · `save` non-null(빈 배열 포함)
      네 조건. 하나라도 깨지면 정지, 빈 값 치환 금지. 세 층 + 게이트웨이 접두 분류를 실행에 남긴다
- [x] 실패 카드는 `client.ts:47-60` errorDetail 관례 — `msg` 만 추려 한 줄, 원문은 접이식. pydantic 덤프
      그대로 띄우지 않는다
- [x] 재개 — `failed`·`unknown` 단계부터, 앞 단계 결과 재사용(`reused_from_run_id`). `done` 은 절대
      재실행 안 함. `unknown` 인 쓰기 단계(`create_`·`submit_`·`ingest_`·`publish_`)는 사람 확인 뒤에만.
      재개는 소유자만, PAT 는 재개자 명의로 새로. 클라이언트 타임아웃·프로세스 종료는 `failed` 가 아니라
      `unknown`. 기동 시 `running` 단계 → `unknown(stage=restart)`, 실행 → `failed(stage=restart)`
- [ ] 비멱등 재실행 경로 둘을 안다 — ① 게이트웨이가 예외(120초 포함) 뒤 재연결하고 **같은 인자로 한 번
      더** 부른다(`gateway.py:1929-1949`) ② 실행기가 먼저 포기하면 쓰기는 그 뒤 완료된다. 그래서 타임아웃
      ≥260초·`unknown` 규칙이다
- [x] 취소 — `POST /runs/{id}/cancel`, 단계 경계에서 `cancelled`, 주체·시각 기록, portal-admin 우회 한 줄
- [x] 결과 저장 — gzip BLOB + bytes + sha256, 2MB 초과는 프리뷰 4KB + `truncated`, 이미지는
      `procedures-artifacts/` 파일, 본문 90일 뒤 비움·메타 영구. `save` 는 저장·절단 전에
- [x] `notes`(4KB) 채우기 — 어댑터가 결과 속 경고·모델 출처를 뽑아 올린다
- [x] ⚠ 게이트웨이 읽기 캐시 300초 — `list_`·`get_` 접두 도구는 같은 인자·사용자면 첫 응답이 그대로 오고
      0건도 캐시된다. 상태 조회 단계는 캐시 접두 이름을 **저장 시점에 거절**. 실행 화면에 "직전 비캐시 호출 =
      X" 를 남긴다(MCP 응답만으로는 hit 를 알 수 없다)
- [x] **시간 정책**(PLAN §5-10) — 단계마다 `expect` 를 선언하고 `job` 은 저장 거절. `warmup: true`
      단계는 한 번 먼저 불러 결과를 버리고 **타임아웃이 나도 실패로 안 친다**(카탈로그 검색은 세션
      첫 호출에 **120.3초**, 이후 0.1초 — 상한 120초라 첫 호출이 잘린다). 실행 화면은 시작 전에
      "보통 N초 걸립니다" 를 실행 기록 p95 로 보이고, 선언과 실측이 어긋나면 화면이 말한다
- [x] `slow` 단계가 도는 동안 **같은 백엔드에 다른 단계를 걸지 않는다** — 재연결이 나면 그 백엔드의
      다른 실행까지 끊긴다
- [x] 감사 — 실행 기록이 정본(append-only). 게이트웨이 원장과는 시각·도구·백엔드 근사 대조만
- [x] `procedures_max_steps` 는 저장 시점 거절(금지 도구 검사와 같은 자리)
- → 검증: (1) 존재하지 않는 도구명 절차가 1단계에서 정지, `error='unknown tool: …'`, `save` 미실행
  (2) `predict_sed` 에 `sample:{ap_cx:"x"}` 가 isError=false 인데도 정지 (3) nginx :8088 경유로 60초
  넘는 단계(예: `list_materials`)가 504 없이 폴링으로 완료 — 8723 직접 호출로는 안 보인다
  (4) 재생 뒤 `gateway.log` 의 세션 생성·종료 건수가 같이 는다 (5) RA 단계 실행의 `audit.jsonl` 에
  `as-conn:<email>` 이 찍힌다

### 화면
- [x] 절차(빈 실행) — **진입점**. 도구 고르기 → 인자 → 실행 → 결과, 한 단계씩
- [x] 도구 고르기 데이터 — `GET /procedures-api/tools`: 사용자 PAT `tools/list`(권한 필터·`inputSchema`
      정본) + 무인증 `/tools-map` 의 `apps`·`areas`·`area_meta` 라벨. `/tools-map` 만 쓰면 못 부르는
      도구까지 보여 403 이 난다. `ToolAreaChips`·`toolAreasOf` 재사용, `ToolCatalogBlock` 은 `useChat`
      결합이라 안 씀. 캐시는 없거나 ≤60초
- [x] 인자 입력 2단 — `properties` 있으면 타입별 위젯 + required 표시, 속성 없는 object/array(44/465)는
      원문 JSON textarea + 도구 설명 접이식. 프론트 검증 없이 서버 에러를 '필드명 → 메시지' 로
- [x] 절차 목록 / 상세 / 판본 / 실행 이력(내 것만) / 실행(변수 폼 → 계획 모드 목록 → 진행 → 게이트)
- [x] **"절차로 저장"** — 보낸 인자를 잎 단위 트리로 펼쳐 클릭으로 변수화(key·label·type 은 잎의 JSON
      타입에서), 결과 트리에서 클릭으로 `save` 경로 생성, JSON 아니면 '추출 불가' 표시. **상수로 남는
      인자를 전부 나열해 확인**(과제 ID·워크스페이스·본문이 공유 절차에 박힌다). 키가
      `token|secret|password|authorization|api_key|cookie` 이거나 URL userinfo 가 든 값은 상수 저장 거절
      (변수·앞 단계 `save` 만 허용). `path|local_path|file_path|url` 키(10/465)와 24-hex·이메일 꼴 값은
      기본을 변수로 올린다
- [x] 재생 전 "되돌리기 어려운 단계 N개" 목록 · 게이트 카드에 실제 인자와 직전 결과 · 확인 대기 실행 상단
- [x] 절차 YAML export/import — 본문만 옮기고 **들이는 쪽도 같은 검증**을 탄다(W-61)
- [ ] ⚠ StepForge 전체 스위트가 180초를 넘는다(형상 연산) — 도는 길을 따로 마련할 것
- [x] 레이아웃 — 루트는 `.container`(ChatDock 자리 예약). 고정 액션 바는 우하단 비우고 상단·좌측.
      `AppShell` 은 손대지 않는다. `ProceduresContext` 는 `/procedures/*` 요소 안, `useChat` 안 씀,
      localStorage 는 입력 중 인자 초안에만
- [x] 실패 카드·재개 경고(위 실행기 항목)
- → 검증: 빈 실행에서 `list_projects` → 저장 → 변수 바꿔 재생이 브라우저에서 된다

### 접점 (챗·심의 0줄)
- [x] `backend/app/main.py` — import + `include_router(prefix="/procedures-api")`. **`:156`
      `if settings.serve_frontend:` 블록보다 위** — 뒤에 두면 GET 이 `index.html` 로 먹힌다(200 text/html 로
      조용히 실패, POST 는 도달). dev 에서 `SERVE_FRONTEND` 없이 uvicorn 만 띄우면 안 드러난다 —
      배포 인스턴스(8723)에서 GET 으로 확인
- [x] `frontend/src/App.tsx` 라우트 1개 `"/procedures/*"`(자식 `procedures/:id`·`runs/:id`) ·
      `AppHeader.tsx` 메뉴 1개 · `state/ProceduresContext.tsx`
- [x] `backend/config/access.yaml` `features:` 에 `procedures` + **모든 라우트에 `ensure(principal,
      "feat:procedures")`**. 실행 라우트는 추가로 `owner_sub == principal.subject`
- [x] `frontend/vite.config.ts:18-26` 프록시 `'/procedures-api'` 1줄
- [x] SSE 를 내지 않는다 — 내면 nginx **두 파일**(`hwax.conf.tmpl:74-93` + `gen-nginx-conf.sh:173-184`)을
      같이 고쳐야 한다. 폴링으로 충분하다
- [ ] ⚠ `systems.yaml` 타일을 만들면 `access.yaml` `platforms:` 에도(`test_access_control.py:28-36` 강제)
- [x] `backend/config/changelog.yaml` 에 사용자가 겪는 변화
- [x] `git diff backend/requirements.txt`·`frontend/package.json` 이 **비어 있다**
- → 검증: `git diff --stat` 에 챗·심의 파일 0개. `curl -s :8723/procedures-api/procedures` 가 JSON(HTML 아님)

### 테스트
- [x] `backend/tests/test_procedures_contract.py` — (1) `{{var}}` 치환·`required`·enum `values` (2) `save` 값이
      다음 단계 인자로 (3) must-gate·deny·비밀 키·미지 인자·`dry_run` 미지원 도구 → **저장 거절**
      (4) `gate: human` 정지, 실패 시 단계·이유 기록, 다섯 실패 모양 각각 정지 (5) 실행이 판본 id 를 박는다
      (6) 기동 시 `running` → `unknown/failed(stage=restart)`. 게이트웨이는 자기 `AsyncClient` 에
      `httpx.MockTransport`(`test_access_control.py:134` 선례)
- [x] 권한 전수 — `app.routes` 에서 `/procedures-api` 접두 라우트를 전부 뽑아 `feat:procedures` 없는 계정으로
      모두 403(열거는 `HWAXRisk/backend/tests/test_client_contract.py:33` 방식). 손으로 고른 몇 개가 아니라
      **전수**여야 나중에 단 라우트가 조용히 열리지 않는다
- [x] 첫 절차 픽스처(`project_id` 변수 → `list_parts` → `create_report_draft`)가 스키마 검증 통과 ✅ R1 씨앗이 그 자리를 대신한다(7단계, `test_procedures_r1` 이 고정)
- [x] 씨앗 가져오기 — `GET /seeds` · `POST /seeds/{name}/import`, 빈 목록에서 카드로 뜬다(W-31)
- [x] 가져오기가 저장과 **같은** 검증을 탄다(게이트 없는 씨앗 → 422) · 이름 경로 탈출 차단
- [x] 없는 API 경로가 SPA 로 새지 않는다 — JSON 404, 깊은 링크 11개는 그대로(W-32)
- [x] `bend_profile` 이 **게이트웨이에** 뜬다 — 낡은 인스턴스 교체 뒤 82개(W-33)
- [x] 씨앗 ①단계를 살아 있는 게이트웨이로 실호출 — 진리값 일치, `save` 경로 넷 다 풀림
- [x] dev 예제 과제 `R1-굴곡수명-예제(U자판)` 반입(파싱 완료) — 사람이 바로 돌릴 수 있다
- [x] 씨앗 ②~⑥ 을 살아 있는 게이트웨이로 실호출 — save 경로 여섯 다 풀림(W-34)
- [x] `equivalent_loads.chain` 이 끼어도 받는 쪽 둘이 그대로 받는다(실호출 확인)
- [x] `json` 변수 — 기본값이 아니라 `Var.example` + "예시 넣기" 버튼으로 넣는다(W-36)
- [x] **`Var.coerce` 가 운영 경로에서 안 불리던 것**을 고쳤다 — `coerce_inputs` (W-35)
- [x] 빠진 필수 변수를 **실행을 만들기 전에** 막는다(422, 실행이 안 남는다)
- [x] 게이트웨이 재집계가 이틀째 매달려 있던 원인·수정·재기동 확인(W-37)
- [x] **R1 을 ①~⑥ 끝까지 실행** — 화면 모양 입력(전부 문자열)으로 시작해 사람 확인에서 멈췄다(W-38)
- [x] 답이 나왔다 — Tsai-Wu R 0.0757 · 수명 1 사이클 · **불리**(R 6mm 는 성립 안 한다)
- [x] 교차 검증 — 적층 총두께 1.2mm = ①이 읽은 형상 두께(같은 부품이다)
- [x] 씨앗 변수 **여섯 칸 전부** 예시 + "예제 값 모두 넣기" — 예제가 실제로 돌아간다(W-39)
- [x] `POST /runs/{id}/replay` — 지난 실행을 그 값 그대로 다시 돌린다(새 실행, 덮지 않음)
- [x] 다시 돌릴 때 **옛 중간값(save)은 안 딸려온다** — 선언된 변수만 넘긴다
- [x] `GET /runs?procedure_id=` + 절차 상세의 이력 + 실행 상세의 "← 이 절차에서"
- [x] 씨앗 재가져오기 = **판본 올리기**(사본 아님), 옛 판본·이력 보존 · 멱등 스키마 마이그레이션
- [ ] 포털 **브라우저**에서 로그인해 완주(사람) — PAT 경로는 아직 사람 손으로만 지나간다
- [x] `cd backend && pytest` 전체 초록 뒤에만 S1 완료(전역 §8) ✅ 261 통과

### 검증 (S1 전체)
- [x] **챗·심의 파일 0개 변경**을 diff 로 확인 ✅ 확인했고 **1건 나왔다** — 개명이 깨뜨린 낱말이었다(W-41, 수정·검사기 추가)
- [ ] dev 첫 절차 완주 → 저장 → 변수 바꿔 재생(`create_report_draft` 는 `dry_run=true`)
- [ ] 챗 동시 실행에서 429·지연 없음
- [x] §6-1 의 네 수가 `GET /procedures-api/stats` 또는 sqlite 질의로 나온다 ✅ `store.stats()` 가 절차수·재생수·타인재생·재생완주율을 낸다(관리자 전용)
- [ ] cae00 — `update-forges.sh chat` 뒤 `/procedures` 페이지가 실제로 뜬다(dist 가 Drive 를 거쳤는지)

## S2 · R1 적층 굴곡 수명 — **dev 완주 첫 실전** (S1 만 선행)

> **진행 중.** 씨앗 절차 `fixtures/laminate-bend-life.yaml` 와 회귀
> `test_procedures_r1.py`(16개) 가 섰다 — `save` 경로가 실물 응답에서 풀리는 것까지 시험한다.
> 굽힘반경은 이제 `bend_profile` 이 준다(W-28). 남은 것은 **포털에서 한 번 완주**시키는 것이다.

절차 전문은 [examples.md#r1](examples.md). 여기서 처음 증명되는 것 — **판단 단계 없이 직선
체인이 끝까지 간다.** `save` 두 줄이 도구 넷을 잇는다.

- [x] 절차 작성 — `part_info` → `thickness_report` → `analyze_laminate` →
      `solve_prescribed_curvature` → `recover_ply_stresses` → `estimate_fatigue_life` →
      `create_report_draft`(gate)
- [x] ★체인의 핵심 — `solve_prescribed_curvature` 의 `equivalent_loads` 를 `save` 해
      `recover_ply_stresses` 의 `loads` 로 **그대로** 넘긴다. 손으로 `(z−z_ns)/R` 을 계산하지 않는다
- [x] **`M = D·κ` 지름길을 쓰지 않는다** — 도구 설명이 비대칭 스택에서 **실측 +244.8% 과대**라고 ✅ 씨앗 ③④가 `solve_prescribed_curvature`(변위 제어)를 쓴다
      못 박는다. 이 한 줄이 절차 기능의 존재 이유다
- [x] 사람이 채우는 변수 넷에 `why` 를 적는다 — `bend_radius`(StepForge 형상 도구에 곡률·반경이 ✅ 셋으로 줄었고(D-287) `test_procedures_r1` 이 `why` 를 강제한다
      **없다**) · `width_mode`(free/constrained 가 **9.6%** 갈린다) · `laminate`(StepForge 재질은
      LS-DYNA 카드 쪽이라 **형식이 다르다**) · `cycles_N`
- [x] ⚠ **W120 을 `notes` 로 올린다** — `estimate_fatigue_life` 는 `strength`/`fatigue` 없는 ply 를
      **조용히 제외하고** 경고만 낸다. 임계 ply 가 빠지면 과대평가다
- [x] `laminate` 는 속성 없는 object(44/465) — 원문 JSON 2단 입력으로 받는다. `unit_system` 은 ✅ 화면이 여러 줄 원문 JSON 칸으로 받고 `coerce_inputs` 가 푼다(W-35)
      `SI`|`SI_mm` 이고 섞이면 조용히 틀린다
- [ ] 검증: dev 에서 완주 → 저장 → `bend_radius` 만 바꿔 재생. 층별 응력·수명이 R 에 따라 변한다
- [ ] 검증: 물성 없는 ply 를 일부러 넣어 **W120 이 `notes` 에 올라오는지**

## S2.5 · 2단 도구 — 역량이 도구 뒤에 숨은 자리 (PLAN §9-4·§9-5)

- [x] 등록부 `docs/procedures/dispatchers.yaml` — **사람이 확정한 것만**(확정 2 · 후보 4)
- [x] `dispatch.py` — 등록부 읽기 · 형식 어댑터(json_schema · params_ko) · 후보 검출
- [x] 후보 검출은 **이름이 아니라 스키마 모양**으로(자유 페이로드 + 고르는 인자 + describe 짝)
- [x] `check_against_schemas(spec, gw, second_stage)` — 속 인자 오타를 **저장 시점에** 잡는다
- [x] `runner.second_stage()` — describe 를 불러 계약을 받는다. **못 받으면 검사 안 한다**
- [x] `/validate` 배선 + 정적 계약 가드가 새 호출을 본다
- [x] 테스트 13건(등록부 중복 거절 · 어댑터 둘 · 지어내지 않음 · 오타 검출 · 변수면 통과)
- [x] 후보 넷 확인 — `catalog_run` **등재**(44개 역량·JSON Schema+examples) ·
      `slurm_submit_job` 은 2단이나 **계약이 산문**이라 결손으로(`gaps/stc-template-schema.yaml`) ·
      나머지 둘은 이 박스에 항목 0건이라 **확인 못 함**(없다는 뜻이 아니다)
- [x] 절차 **저장**도 같은 스키마 대조를 탄다 — `/validate` 에만 있으면 권고지 검증이 아니다(W-52)
- [x] **안 보인다 ↔ 없다** 를 가른다 — 권한·일시 불통과 구분 못 하므로 저장을 안 막는다(W-52)
- [x] 포털 테스트를 **오프라인**으로 — 가짜 게이트웨이(도구 0개). 감사 줄수 0 증가로 확인
- [x] 화면 — 2단이면 칸이 뜬다. 목록 → 고르면 그 계약. 노출 이름 접두어도 본다(W-65)
- [x] 목록 응답 모양이 앱마다 달라 `_names_of()` 가 흡수 — 모르는 모양이면 빈 목록

## S7a · 관측 배선 — 짝·성패·표식·하나의 원장 (PLAN §9-9)

- [x] ① 도구 시작·완료 두 이벤트에 `call`(=LangGraph `run_id`) — 짝이 생긴다
- [x] ② 실패 표지 + 완료 이벤트 `ok` — `_cap_tool` 이 이미 내린 판단을 버리지 않는다
- [x] ③ 표식 절단 `…#sha1[:6]` 로 네 갈래 통일 + 포털의 2000자 **재조임 제거**
- [x] ④ 심의 — `tool_call_id` 를 두 이벤트에 태우고 `evidence` 에 인자를 붙인다
- [x] ⑤ `from_chat.record()` — 챗 턴을 `run_steps` 에(새 표 안 만든다)
- [x] **짝 키 없으면 안 접는다** — 이름으로 묶는 거짓을 원장이 물려받지 않는다
- [x] 기록 실패가 챗을 막지 않는다 · `ok` 없으면 `None`(실패 아님)
- [x] 화면도 짝 키로 묶는다(없으면 종전대로) — §5-5 증상이 사라진다
- [x] 테스트 20건(에이전트 10 · 포털 10) · 에이전트 375 · 포털 284 통과
- [x] ⑥ 게이트웨이 얇은 색인 — `caller`(MCP 10곳) · `corr` · `mode` · 밀리초 `ts`(W-47)
- [x] ⑦ 성공 기록의 `error` 오남용 제거 — 칸을 갈랐다. 정적 검사로 재발 방지(W-47)
- [x] 절차 실행의 상관 ID 가 감사에 남는다(실측 `corr: run-TEST123`)
- [ ] ⚠ 챗은 상관 ID 미결 — 도구 연결이 그룹 캐시라 대화별로 못 붙인다(원장 직접 쓰기로 대체)
- [ ] 실제 챗 한 턴을 돌려 원장에 제대로 남는지 확인(사람)
- [x] **도출** — `derive.find_path()` 가 값의 출처를 역으로 찾는다(키워드 목록 아님, W-48)
- [x] R1 실행을 넣으면 R1 체인이 그대로 나온다 · 결손도 같이 나온다
- [x] 찾은 경로는 `template.extract` 로 **대조**한다 · 짧은 값은 안 믿는다
- [x] 모르면 `needs_human` 으로 올린다 — 변수를 지어내지 않는다
- [x] 챗이 인자를 **날것으로** 남긴다(`detail_full`) — 미리보기로 만든 절차는 손상돼 있었다
- [x] `GET /runs/{id}/draft` + 화면 "절차로 펴 보기" · 저장 안 함(테스트가 지킨다)
- [x] 변수 설명을 **도구 스키마에서** 끌어온다 — description·enum·type·default(W-49)
- [x] 같은 인자·같은 값이 여러 단계에 쓰이면 **변수 하나**(갈라지던 결함 수정)
- [x] 설명 없는 인자는 `arg_undocumented` 결손 — 지어내지 않는다
- [x] 한 변수가 여러 단계에 쓰이면 **그 자리를 전부** 설명에 적는다
- [x] `GET /procedures/{id}/tool` — 절차를 **도구 계약**으로(입력 스키마·human_gates, W-50)
- [x] 화면 "도구로 보기" — 변수가 곧 입력 스키마임을 보여 준다

## S9 · 일반화된 해석 개념 (PLAN §10) — 선택·환원·보강

- [x] **① 선택** `Step.select` — 룰로 고르고 0/1/N 을 다룬다(W-51)
- [x] 여럿이면 **사람에게 묻는다**(기본 `ask`) · `first` 는 저장 시점 경고
- [x] `POST /runs/{id}/steps/{ix}/pick` — 확인과 다른 자리. **보여 준 후보 중에서만**
- [x] 0개면 실패 · 경로가 안 풀리면 후보 없음과 같다 · 테스트 17건
- [x] 화면 — 후보 목록에서 고르기(W-53). 만들어 놓고 안 만들어 막다른 길이 돼 있었다
- [x] 스키마에 없으면 **도구 산문에서 인용**한다(`from_prose`) — 인자 설명이 1%뿐이다(W-58)
- [x] 설명 없는 인자 결손을 **한 줄로 모은다** — 99%에서 울리면 검출기가 아니다(W-58)
- [ ] 전 앱이 인자 `description` 을 채운다 — `gaps/hub-arg-descriptions.yaml`(절차에 쓰는 도구부터)
- [x] **② 환원 — 스택업** 결손을 장부에 등재 + **StepForge 에 요청서**를 냈다
      (`gaps/stepforge-stackup-profile.yaml` · `StepForge/docs/REQUEST-stackup-profile.md`)
- [ ] StepForge 회신 대기 — "이미 되는 길이 있으면 알려 달라" 를 함께 물었다
- [x] **DynaForge 에도 요청서를 보냈다**(2026-09-16) — `KooRemapper/platform/docs/
      REQUEST-postprocess-operation.md`. 처음엔 "진행 중이니 요청할 것이 아니다" 로
      뒀는데, **어떤 모양으로 오면 우리가 안 고치는지**는 그쪽이 알아야 정한다.
      실측으로 아직 안 왔다(연산 47종 · 후처리 0건)
- [ ] DynaForge 회신 대기 — 세 갈래 중 어느 쪽인지(연산 / 독립 도구 / 오래 걸림)
- [ ] ② 두 번째 환원 도구가 `bend_profile` 과 **같은 모양인지** 보고 규약으로 올린다(§10-7)
- [ ] **③ 보강 — 라미나 물성**(강도·피로) 조달 경로 → MaterialTwin ↔ 적층 해석기 결손
- [x] S5 와 이었다 — `fan-out` 이 후보마다 실행을 하나씩 만든다(W-57)
- [x] 배치 = **새 실행 N개**라 게이트·재개·다시 돌리기·도출이 그대로 돈다
- [x] 첫 게이트에서 **각자 멈춘다** — 초안 N개가 안 만들어진다(구조가 그렇다, 막는 코드 없음)
- [x] 비교표 `GET /batches/{id}` — `inputs` 를 그대로 열로(역파싱 금지) + 화면

## S10 · 하드코딩 점검 (2026-09-15)

- [x] 절차 모듈 상수를 전수로 훑어 넷으로 갈랐다(W-66)
- [x] 카탈로그 목록 → **인구조사 고정물**(`fixtures/catalog-census.json`)에 대조
- [x] `backend/scripts/refresh-census.py` — 갱신은 **사람이** 돌린다
- [x] ⚠ 가드가 첫 실행에 둘을 잡았다 — 도구 465→470 · **`publish_report_to_datahub` 무게이트**
- [x] 게이트웨이에서 베낀 상수 대조 — `_CACHEABLE`·`_INVOKE_DENY_*` · **시간 상한 관계**
- [x] 검출기가 `catalog_run` 을 못 찾던 것 수정(접두만 봤다, W-67)
- [x] 못 미는 것은 **등록부에 데이터로**(`detector_finds: false`) — 규칙을 안 늘린다
- [ ] 인구조사 갱신을 주기적으로 — 지금은 사람이 생각날 때 돌린다
- [x] ⚠ 가드가 **두 번째**로 잡았다(2026-09-15 오후) — 470→471 `rigid_body_check`.
      사람이 보고 판단: 읽기 전용 점검이라 게이트 불필요(StepForge D-296)

## S11 · 세 겹 감사 (2026-09-15) — "문제가 없어질 때까지"

라운드마다 **앞 라운드의 수정 자체**를 대상으로 삼았다(W-68).

- [x] **1차** 네 갈래 병렬 — 무음 결함 · 권한/주입 · 테스트 품질 · 화면. 40여 건
- [x] 2단 계약 검사가 **통째로 죽어 있었다** — 튜플을 객체로 읽어 늘 `None`,
      그것을 "검사할 게 없다" 로 읽었다. 실호출을 태우는 검사를 달았다
- [x] 게이트 뒤 **재개가 전면 불능** — `save` 가 원장에 안 남아 `TemplateError`,
      그 예외를 아무도 안 받아 실행이 영원히 `running`
- [x] 권한 구멍 둘 — 아무나 남의 절차에 판본을 얹을 수 있었고(주인 명의로 돈다),
      `private` 는 목록에서만 걸렸다. PoC 로 재현 후 수정 + **라우트 전수 검사**
- [x] 심의에서 **도구를 부른 좌석만** 근거 0건 — 튜플 폭 불일치(직전 커밋이 만든 것)
- [x] 성패 오판 네 방향 — ✖ 전체 검색 · 삼킨 예외 · `on_tool_error` 미처리 · `None`→성공
- [x] 화면 여섯 — 짝 키를 이름으로 재병합 · `ok` 미표시 · 옛 실행 덮어쓰기 ·
      절차 갈아탈 때 입력값 잔존 · 못 받은 것이 "없다" 로 · 변수가 위치로 묶임
- [x] 테스트 품질 — 가드를 지워도 통과하던 것, 쫓는 사건에서 skip 하던 것,
      빌드 산출물에 매여 평소엔 꺼져 있던 것(W-70·W-71)
- [x] **2차** — 1차 수정이 남긴 8건. 셋은 1차가 **새로 만든** 결함이다
      (fan-out 자식 즉사 · 절단 표식이 성패를 되돌림 · 2^53 위 정수 동일시)
- [x] 실측으로 전제가 뒤집힌 지적 하나는 **고치지 않고 이유를 주석으로**(W-69)
- [x] **3차** — 2차 수정 대상 + 판정기(`judge.py`). 17건.
      가장 무거운 둘은 **판정기가 실패를 성공으로** 바꾸던 것이다(W-72) —
      목록형 응답 전부 `not_json`, `unwrap` 이 봉투를 지움. 하나는 2차가 만든 회귀
      (변수 가림으로 `save`+`select` 파손)
- [x] 깊은 인자가 500 을 만들던 것 — 상한을 **공용 순회기**에 뒀다(W-73)
- [x] 2차의 한국어 경계 완화가 과했던 것 — 앞 경계만 되돌렸다(W-74)
- [x] **4차** — 3차 수정 대상. 3차의 **간판 수정이 프로덕션에서 한 번도 안 돌았다**(W-75)
      — 고정물을 compact 로 만들어 초록이었고 실물은 pretty-print 였다. 살아 있는
      게이트웨이 실호출로 잡혔다. 같은 커밋이 자기 다른 수정을 경로 분기로 지우고 있던 것도
- [x] 저장이 원본 dict 라 `vars` 없는 YAML 하나로 **SPA 전체가 흰 화면**이 되던 것(W-76)
- [x] **5차** — 4차 수정 대상 + 실물 대조. 최대 위험(행별 봉투 검사가 실물 목록을
      실패로 뒤집는 것)은 게이트웨이 **471종 전수**로 확인해 실현되지 않음
- [x] 판정기가 **셋인데 답이 달랐다**(W-77) — 에이전트 서버 둘을 한 봉투 검사 위로
- [x] 인공 고정물이 **한 자리 더** 있었다(W-78) — `GW_DENIED` 가 감사 로그에만 있는
      문자열이었다. 고치고 **가드**를 세웠다(네 상수가 응답 본문 자리에 있는지 대조)
- [x] **6차** — 5차 수정 대상 + **아무 라운드도 안 본 자리**. 가장 큰 셋이 거기 있었다(W-79)
- [x] 업로드가 게이트웨이 거절을 `created: true` 로 내던 것 — `judge.py` 가 다섯 라운드
      내내 **이름까지 적어** 경고해 둔 함수인데 아무도 안 고쳤다
- [x] 계정 정지가 SSO·세션·PAT 에 안 먹던 것 · REST 프록시가 자격 체계를 우회하던 것
- [x] 게이트웨이 근거 원장이 세션을 넘어 새던 것 + 캐시 적중 누락 + 만료 부활(W-80)
- [x] 카탈로그 출렁임(레지스트리 깜빡임·`list_tools` 흔들림) — 부분 실패와 진짜 변경을 가른다
- [x] 파괴 관문이 이름 패턴만 보던 것 — `MUST_GATE` 를 그대로 쓰고 양쪽에 가드
- [x] 무인증 `/health` 권한 지도 노출 · 공유 시크릿 `==` 비교 5곳 · 업로드 세션 누수·상한
- [x] 신원 결속 fail-open 둘 — userinfo 가 id_token 을 덮던 것 · RA 이메일 생략
- [x] **게이트웨이 재기동 완료**(사람이 골랐다) — 16/16·472종 복귀 확인, 실물 4종 재확인(W-81)
- [x] **7차** — 6차 수정 대상 + 미탐 영역. **PAT 위조로 임의 신원·권한**이 되던 것을
      잡았다(W-82) — 일곱 라운드가 못 본 선재 결함, 완전 재현 후 수정
- [x] 정지가 절반만 듣던 것 — 게이트웨이 경로·PAT 까지 닫는다(W-83)
- [x] nginx 가 게이트웨이 무인증 진단을 외부로 열던 것(실측 200·43KB) + **반영 완료**
- [x] 6차가 만든 구멍 — 업로드 중간 실패가 부분 부작용 + 무기록이던 것(W-84)
- [x] 5차 가드가 자기가 잡으려던 회귀를 통과시키던 것 — 줄 단위로 고치고 자기검사 추가
- [x] 심의 셋 — 중단이 AI 머리말에 덮이던 것 · 공용 근거 무표식 절단 · 상태줄 과대보고
- [x] 내부 IP 가 **public GitHub** 추적 파일에 있는 것 — 늘지 않게 가드(정리·히스토리는 사람)
- [ ] 추적 파일 내부 IP 15개 정리 + 히스토리 세탁 여부 — **사람 결정**(force-push)
- [ ] 8차 — 7차 수정 대상. 미탐으로 남은 것: 챗 스트리밍·`conv_store`·docx 내보내기

## S3 · R2 낙하·충격 — 제출/회수 두 절차 (S1 만 선행)

⚠ **후처리가 DynaForge 로 온다**(KooD3plot 쪽, 진행 중). 절차를 **읽는 쪽으로** 쓰고
얻는 쪽은 `report_id` 변수 하나로 좁혀 둔다 — 그러면 옮겨졌을 때 앞에 단계 하나만 더하면
된다. 지금 사슬을 박으면 그 절차는 전부 거짓말이 된다(`gaps/dynaforge-postprocess.yaml`).

- [x] 이음매를 문서에 박았다 — 얻는 쪽/읽는 쪽을 갈랐고 옮겨 올 때 필요한 것을 미리 적었다
- [ ] 옮겨 온 뒤 — 연산으로 오면 등록부 그대로, 직접 도구로 오면 인자 스키마를 받아야 한다


절차 전문은 [examples.md#r2](examples.md). 여기서 처음 증명되는 것 — **잡 제출을 사람 확인
아래 두고, 제출과 회수를 가른다**(드라이버 walltime **167시간**).

### R2a 제출 (dev 는 `dry_run` 까지)
- [ ] `save_result_to_path`(gate) → `smarttwin_scenario_options`(`raw: true` — 반환이 텍스트
      카탈로그다) → `smarttwin_submit`(**must-gate**)
- [ ] `sim_type` 만 바꾼 판본 둘 — `fullangle_drop`(각도 프리셋) · `partial_impact`
      (`locations.mode` = grid|list|lhs|part_center, `impactor` Sphere|Cylinder)
- [ ] **제출 갈래는 `smarttwin_submit` 만** 쓴다 — `fullangle_drop_simulation` 은 `lstc_license_ip`
      를 사람에게 묻고 부분충격 빌더가 없다
- [ ] ⚠ **단위계가 실제로 섞여 있다** — 프리셋 `26direction` 은 SI(7850, 2e11), 부분충격 실제 잡은
      tonne-mm(7.85e-9, 2.0e5). `scenario_overrides` 물성은 **무변환 기입**된다. 변수 label 에 단위를 박는다
- [ ] ⚠ enum 저장 시점 검증 — `generation_mode` 오타는 **조용히 기본값 처리**된다
- [ ] ⚠ 전각도 `scenario_overrides` 에 `mode` 키가 섞이면 **조용히 부분충격으로 오실행**(사고 `799`)
- [ ] `model_path` 는 공유 FS 절대경로 — 파일 반입은 절차 밖(§4)
- [ ] ⚠ 미확인 — `smarttwin_submit` 반환 모양(제출계라 안 불렀다). `save` 경로는 첫 실행에서 확정한다

### R2b 회수 (cae00)
- [ ] `slurm_job_results` → `report_summary` → `report_worst_cases` → `report_directional` →
      `report_part_risk` → `report_findings` → `create_report_draft`(gate)
- [ ] `report_id` 를 **변수로 받는다** — 리포트 HTML 이 8~10MB 라 MCP 로 못 나른다. 반입은 REST
      intake(512MB)이고 절차 밖이다
- [ ] `sphere`/`impact` 는 리포트 `kind` — `sim_type` 과 짝이다. `ingest_report` 가 자동 판별한다
- [ ] ⚠ **부분충격은 scenario 첨부를 생략**한다 — 파서가 `scenarios` 배열을 요구하는데 평탄
      구조라 `ScenarioParseError` 로 **인제스트 전체가 실패**한다
- [ ] ⚠ 구버전 SIF 는 `impact_report` 를 **`exit 0` 으로 조용히 건너뛴다** — 산출이 없는데 성공으로
      보인다. 실행 기록에 산출 파일 유무를 남긴다
- [ ] 과제 메타(`project`·`dev_rev`·`variation`·`doe`·`focus`)를 안 넣으면 `find_reports` 로 다시 못 찾는다
- [ ] ⚠ **dev 에서 검증 불가** — `report_corpus` 가 0건이다. 계약만 확인하고 실동작은 cae00
- [ ] 이 판독 도구 묶음이 **심의 좌석에 주는 도구 목록**이다(PLAN §6 심의 경계). 제출 계열은 좌석에서
      뺀다 — 심의는 잡을 걸지 않고 이미 있는 `report_id` 를 읽는다

## S4 · R3 ODB 어댑터 + 열충격 SED (S0 선행)

절차 전문은 [examples.md#r3](examples.md). 여기서 처음 증명되는 것 — **공급자 없는 값이
사람이 채우는 칸으로 내려간다**(§5-1).

- [ ] 고정물로 어댑터 작성 — odb-hub 산출 → `SedInput`. **키 15개(필수 10·선택 5) 외엔 `sample` 에 넣지
      않는다** — 서버 `extra="forbid"`, ODB 에서 딸려 온 키 하나면 E100 통째 거부
- [ ] 예외형인지 봉투형인지를 표본으로 정하고 봉투형이면 §5-6 규칙이 그것을 실패로 친다
- [ ] 품질 플래그(`warnings`·`has_eda`·`data_type` 류)를 선행 검사로 — 걸리면 값을 채우지 않고 사유를
      `notes` 에
- [ ] `pkg_type` 은 **영구 변수**(유도 불가). 선별 규칙이 없으면 `ap_refdes`·`pkg_refdes` 도 영구 변수.
      `why` 에 이유
- [ ] `board_type` — 어휘 대응·HALF/FULL 판정 규칙이 없으면 '사람이 채운다' 로 분류
- [ ] 단위 환산 — `ball_size` 는 µm 정수 문자열, 좌표·치수는 mm, 두 중심은 같은 좌표계
- [ ] 상태 조회 단계가 캐시 접두 이름이면 저장 거절 — 비캐시 이름(`job_status` 류)만
- [ ] dev 완주 시험 — ODB 단계가 "사람이 채우는 칸" 으로 내려간 상태
- [ ] 열충격 절차를 export 해 `docs/procedures/fixtures/` 에 커밋 → cae00 에서 import
- [ ] **cae00 실주행 검증** — 여기서만 진짜 확인된다. 허브가 사용자별 스코프면 "토큰 주인 시야로만 돈다"
      를 context-notes 에 적는다
- [ ] 워피지 — `copper_imbalance_pct`·`stackup_asymmetry`(산식은 dev 에서 정한다)·`board_thickness_mm` +
      선택 `diagonal_mm`·`peak_temp_c` 가 같은 다리로 열리는지
- [ ] 보고서 경로 — `create_report_draft`(gate) → `suggest_report_tags`(후보만) → gate → `add_report_tags`.
      `create_report_from_run` 은 못 쓴다(적재 실행 `status=ready` 전용)
- [ ] `pcb_warpage_surrogate` 의 합성 데이터 경고를 `notes` 로
- [ ] HWAXRisk `odb-adapter-contract.md` 4도구와 이름이 다르면 계약 개정을 HWAXRisk 쪽 일감으로

## S5 · 일괄 재생 (S2~S4 중 하나만 서면 된다)

첫 실사용례가 이미 둘 있다 — **R1 의 굽힘반경 스윕**(R_min·R_max 유불리)과 **R2 의 각도 프리셋
비교**. 조건 분기로 보이던 자리가 "같은 절차 × 변수 N개" 였다.

- [x] 절차 1개 × 대상 N건 → 비교표(W-57). `inputs` 를 그대로 열로 편다. `notes`
      경고 유무를 열로
- [x] **첫 `gate: human` 직전까지** — 각 실행이 자기 게이트에서 멈춘다(구조가 그렇다)
- [x] 동시 상한은 **실행기의 기존 것**을 쓴다(두 곳에서 세면 어긋난다) · 기본 계획 모드
- [x] 비교표에 **왜** 를 싣는다 — 첫 실패 단계·도구·오류 + 경고 코드(W-59)
- [ ] `predict_sed_batch` 는 쓰지 않는다 — 전부-아니면-전무 검증이라 건너뛰기가 안 되고 응답 모양이 다르다

## S6 · 과제 키 레지스트리 (S5 뒤)

- [ ] 결정 — HWAXRisk `rr_sources`·`rr_projects` 확장인가 신규인가(PLAN §7 #8)
- [ ] 매핑 표 — StepForge `project_id`(23-hex) · DynaForge `session_id`(ULID) · ThermalShock `project` ·
      ReportArchive `project` · HWAXRisk `target_key` · **ODB 잡 메타의 과제 필드**(S0 에서 있으면)
      + **소유 주체 열**(사용자 위임 / 서비스 계정) + **시야 열**
- [ ] 시야 제약을 앱별로 정확히 — DynaForge `list_sessions`·`find_reports` 는 user_id 스코프(서비스 계정
      0건) · HWAXRisk `risk_list_projects` 는 소유∪멤버∪org 공개분 · RA 는 게시판 권한 기준(소유분만이
      아니다) · StepForge `list_projects`·ThermalShock 은 전사. 조직 단위 모아 보기는 DynaForge·HWAXRisk 에
      한해 관리자 자격이나 별도 원장이 필요하다
- [ ] 이름·코드로도 찾기(StepForge 가 이미 그렇게 한다)
- [ ] 검증: 실제 과제 하나로 앱을 오가며 키가 안 끊기는지

## S7 · 챗 → 절차 도출 (S7a 관측 위에서 — **본선**, PLAN §9-1)

- [x] `on_tool_start`/`on_tool_end` 의 `run_id` 를 `call` 로 싣는다 → S7a ①
- [x] 인자 절단을 `…#sha1[:6]` 한 갈래로 통일 → S7a ③
- [x] `activity[]` 에 `ok` · `call` · `via` · 날것(`detail_full`·`result_full`)
- [x] **`invoke_tool` 경유를 벗겨 안쪽 도구 이름으로** 기록(안 벗기면 도출이 전부 결손이 된다)
- [x] 실행 기록 → 절차 초안 제안(`derive.draft` · `GET /runs/{id}/draft`)
- [x] 어느 인자가 변수인지 **사람이 확정** · 자동 저장 금지(초안만 낸다)
- [x] 변수 뜻을 도구 스키마에서 끌어온다 + 절차를 **도구 계약**으로(W-49·W-50)
- [x] `activity[]` 에 `ts`·`ms` + 원장 `duration_ms` 까지 — 짝 키로 시작을 기억해 잰다
- [ ] 합격 기준 확인 — `predict_sed` 병렬 5회가 **각각 다른 인자에 짝지어지는지** 실제로 본다
- [x] 초안 확정 화면 — 사람이 정할 자리마다 체크상자·이름 칸, 고른 것만 변수로(W-59)
- [x] 결손 → 장부 **초안**(`POST /gaps/draft`) + 화면 버튼. ⚠ 파일은 포털이 안 쓴다(W-64)
- [ ] 절차를 게이트웨이에 **실제 도구로 등록**(계약은 섰다 — 등록 경로는 사람 결정)
- [ ] 실행의 '챗으로 가져가기' — `conv_store.create_with_messages(kind='procedures')`

## S8 · 리스크 패턴화 (가장 뒤)

- [ ] **실행 → 심의 다리** — 실행 상세 "심의로 넘기기". 단계 기록을 `[{source, tool, args, result}]` 로 바꿔
      `POST /agent/conversations` → `POST /agent/chat`(`'/심의 ' + 화두`, `delib_opts.evidence`,
      `chair_template: "risk-review"`). 새 엔드포인트 아님. 상한 40건·결과 150,000자·**인자 1,200자**
- [ ] **심의 좌석 도구는 읽기 전용 판독 도구만** — `report_summary`·`report_worst_cases`·
      `report_directional`·`report_part_risk`·`report_findings`·`report_query`·`report_case`·
      `report_angle_stats`·`report_scatter`·`report_energy_flow`·`report_part_series`·
      `compare_reports`. `smarttwin_submit`·`slurm_submit_job`·`run_job`·`submit_lsdyna_job` 은 **뺀다**
- [ ] `compare_reports`(리비전 비교)·`report_corpus`(반복 findings = 설계 규칙 후보)가 패턴화 재료
- [ ] 선행 결손 — `delibTaxonomy.ts:5-12` `JobId` 에 `risk-review`
- [ ] 선행 결손 — `conversations.api.ts:6` `ConvKind` 에 `'risk-review'`(없으면 `ChatContext.tsx:457` 필터에서
      조용히 걸러진다)
- [ ] 결과 → `risk_add_finding`(must-gate). `cites` 0건이면 `{"error":"cites_required"}`(isError=false — §5-6 ④).
      `claim` ≤2000자
- [ ] `risk_taxonomy` 어휘를 **코드가 대조**한다 — `mechanism`·`domain` 은 서버 검증이 없어 오타가 그대로
      저장된다(422 는 `severity`·`judgement`·`direction` 뿐)

---

## 착수 전

- [ ] PLAN §7 결정 — S0 시점 · 공유 정책(#6). **S2(R1)부터 권장** — 선행 0, dev 완주
- [ ] S1 을 먼저 시작할지(S0 과 병렬 가능) 확인
- [x] 씨앗 절차 + 실물 응답 고정물 + 회귀 16개 — `save` 경로가 봉투(`data.`) 아래라는 것을
      테스트가 잡았다(W-29). 굽힘반경은 `bend_profile` 이 준다(W-28)
- [ ] 포털 화면에서 R1 을 **실제로 완주** — StepForge 에 U자 판을 반입하고 절차를 재생한다(사람)
