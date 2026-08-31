<!-- 설계 리스크 심사 — 단계별 실행 체크리스트(plan.md §9 에서 도출, 진행하며 체크) -->
# 설계 리스크 심사 — 체크리스트

정본은 `plan.md`(§9 단계 계획·§10 열린 질문). 이 문서는 실행 순서와 완료 판정만 요약한다. 항목 뒤 괄호는 plan.md 절. B 토폴로지(§0.7 #12) — 자산·러너·UI 는 HEAX 앱 `hwax_risk`(리포 `HWAXRisk`, `/apps/hwax_risk/*`, DB `$HEAX_DATA_DIR/risk_review.db`), 포털은 창(타일·`/risk`·NavLink)만. 아래 경로에서 `backend/`·`frontend/` 는 앱 리포 기준이고 포털 파일은 `포털:` 접두를 붙였다.

## 착수 전 — 사용자 결정 (§10, P0 착수 전 답이 필요한 것)
- [ ] (23) 매니페스트 확정값 — `id hwax_risk · name HWAX Risk Review · owner cae-automation · status beta · visibility company · resources{1, 2, false}` 승인(`team` 은 `seed_admin_org` 일치 확인 선행)
- [ ] (24) 리포 위치 — `source.url` GitHub `https://github.com/squall321/HWAXRisk.git`(ref main) 승인(`file://` 은 cae00 스캔 fetch 실패 반복)
- [ ] (28) 스캐폴드 관례 확정 — 이름은 실존 리포 `HWAXRisk`·env 접두 `HWAXRISK_`·`source.url` 로 확정(계획서 반영 완료). 레이아웃은 선택 — (i) P0 착수 시 `backend/`+`frontend/`+`fastapi_react` 로 이동(기본) / (ii) P0 는 루트 `app/`+`fastapi` 유지, P1 전환. 어느 쪽이든 §9.1 A-δ 코드 델타는 P0 즉시(§10.8 #28)
- [ ] (3) 러너 자격 — (a) 서비스 계정 포털 PAT `HWAXRISK_PORTAL_PAT` 발급(계정·groups·ttl 365·aud `mcp-gateway`) 승인 · (b) SettingsPage 사용자 PAT 등록 UX P0 포함 승인(대리 발급 없음)
- [ ] (25) 러너 엔진 호출 경로 — (A) 앱 → 포털 `/agent/chat` 정본, (B) `:9009` 직접은 `HWAXRISK_AGENT_URL` 설정 박스 폴백만(기본 꺼짐)
- [ ] (1) RA 시스템관리자 PAT — `bootstrap_ra_ontology.py --base <RA REST 오리진>` 실행자 env `RA_ADMIN_PAT` 1회 사용 승인(앱 런타임 무보유. 미승인이면 P0(2) 보류, `external_sync.ra=unavailable`)
- [ ] (10) AIDataHub doc_type 3종·`risk-review-memory` 생성·`external_source=hwax-risk`·`HWAXRISK_AIDH_API_KEY` 발급 주체·`AUTH_REQUIRED` 값 확인
- [ ] (16) 브라우저 신원 = 앱 `identity.py` 가 heax `/api/v1/auth/me` 되묻기(HEAX 무수정) — 기본값 그대로 갈지, `copy_identity` additive 를 원하는지
- [ ] (17) MCP 호출자 = `actor` 미검증(`actor_verified:false`) — 기본값 그대로 갈지
- [ ] (18) 앱 시크릿 `secrets.env`·`_user_credentials` 가 Drive tar 에 포함됨 — ① ttl ≤365 로 수용 / ② `appdata-to-drive.sh` 제외 패턴 / ③ 암호화
- [ ] (19) HEAX 콜백 `next` allowlist additive(2단 → 1단) 채택 여부 — 기본 미채택
- [ ] (20) app-data 백업 — dev crontab `appdata-to-drive.sh` 일 1회 시각(기본 03:30), RETAIN 5
- [ ] (2) 게이트웨이 `rest.heax` — 기본 불필요(heax 서비스 PAT 직접 읽기). 원하면 설정 3곳 변경(P1 착수 전 선택)
- [ ] (8) 성격 통제 어휘 v1·택소노미 v1 초안 확정 주체 지정(초안 그대로 시작 가능)

## P0 부트스트랩 — 계약·엔진 손잡이·저장소 준비 (§9.1)
산출물 A — 앱 리포 `HWAXRisk` 스캐폴드(ThermalShockMCP 골격 복제 + `fastapi_react` 레이아웃, 파일 첫 줄 한국어 주석). `[x]` = 파일이 실존 스캐폴드(`/home/koopark/claude/HWAXRisk`, 2026-08-31 커밋 0건)에 이미 있음 — 계획값과의 차이는 바로 아래 '델타' 줄이고 델타가 닫혀야 항목 완료(§9.1 A-δ, §10.8 #28)
- [x] `.portal/manifest.yaml` — §8.2.2 확정값 전문(schema_version 2 · mcp{expose true, path /mcp, streamable_http, allowed_groups []} · launch{service, /api/health, on_failure 3, env{HWAXRISK_DATA_DIR:/data, PYTHONNOUSERSITE:"1"}}) — 실존
  - [ ] 델타: health `/health`→`/api/health` · `build.stack fastapi`→`fastapi_react`(#28 (i)) · visibility `team`→`company` · memory_gb 1→2 · `launch.env` 추가 · `mcp.allowed_groups: []` 추가 · description 의 `/api/v1`·`/health`·`hwax_risk.db`·'도구 3종' 문구 갱신
- [x] `backend/pyproject.toml`(fastapi · uvicorn[standard] · 'mcp>=1.10,<2' · pydantic · httpx, packages.find include app*, version 0.1.0) — 실존 루트 `pyproject.toml`(jsonschema·pyyaml 포함)
  - [ ] 델타: `backend/` 로 이동(#28 (i)) · `httpx` 를 runtime deps 로 · package-data 에 `assets/*.json`
- [x] `backend/app/main.py` — ① `/api/*` ② `app.mount('/mcp', FastMCP(streamable_http_path='/').streamable_http_app())` ③ 마지막 `app.mount('/', StaticFiles(../../frontend/dist, html=True))`, lifespan §8.2.10 ①~⑦(`mount('/', mcp_app)` 금지) — 실존 `app/main.py`
  - [ ] 델타: `mount('/', mcp_app)` 제거 → `/mcp` 서브마운트 + 마지막 `/` StaticFiles((ii) 면 `app/static/`) · `GET /health`→`GET /api/health {ok, app_version, schema_version}` · lifespan ③④⑤⑦ 추가
- [x] `backend/app/config.py` — 데이터 루트 `HWAXRISK_DATA_DIR > HEAX_DATA_DIR > <리포>/data`, `mkdir -p`+`W_OK`, Settings §8.2.6(env 접두 `HWAXRISK_`), `secrets.env`(0600) 로드 — 실존 `app/config.py`(우선순위·W_OK 기동 중단 구현됨)
  - [ ] 델타: `DB_FILENAME` `hwax_risk.db`→`risk_review.db` · Settings §8.2.6 전 필드 · `secrets.env` 로드
- [x] `backend/app/identity.py` — `identity.current(request) -> Identity{email, display_name, role, organization, anonymous, source}`, Bearer → 쿠키 `heax_access_token` → heax `/api/v1/auth/me`, sha256 키 TTL 60 s 캐시, `X-Heax-User-*` 미사용 — 실존 `app/identity.py`(`X-Heax-User-Email` 을 `header_unverified` 로 읽는 방식 — §8.2.8 위반)
  - [ ] 델타: 헤더 읽기 제거 → `identity.current` `/auth/me` 되묻기 + TTL 60 s 캐시, `api.py` 호출부 `Depends(identity.current)`
- [x] `backend/app/risk_store.py` — `MIGRATIONS` v1 = §5.2.2 DDL 전문(rr_* 32표) + 살림 표 `_schema_migrations`·`_user_credentials`, `PRAGMA user_version`·WAL, `pre-migrate-<ts>` 사본 — 실존 `app/risk_store.py`(v1 = 4표, 이력 표 `schema_migrations`)
  - [ ] 델타: `schema_migrations`→`_schema_migrations(+app_version)` · v1 32표 전문(`rr_panels.model_json`·`rr_coverage.model` 포함) + `_user_credentials` · `.pre-migrate-<ts>` 사본
- [x] `backend/app/routes.py`(prefix `/api`) — `GET /health {ok, app_version, schema_version}` · `GET /me` · `PUT /me/portal-pat`(422 `pat_invalid·pat_email_mismatch·pat_audience·pat_expiring`) · `GET /meta/taxonomy|adapters` — 실존 `app/api.py`(prefix `/api/v1`, `/meta*` 4종)
  - [ ] 델타: 파일명 `routes.py`·prefix `/api` · `GET /health`·`GET /me`·`PUT /me/portal-pat` 추가(`/meta/vocab` 유지)
- [x] `backend/app/mcp_server.py` — FastMCP `hwax-risk`(DNS rebinding 비활성), 도구 6종 시그니처(`risk_get_brief(target_key, tier='B')`·`risk_submit_panel_result(…, actor, model?)` 포함), 본문 `{error:'not_implemented'}` — 실존 `app/mcp_server.py`(도구 3종 `risk_health·risk_get_taxonomy·risk_get_meta`, DNS rebinding 비활성)
  - [ ] 델타: 3종 제거·6종 시그니처 `not_implemented` · `streamable_http_path='/'`(`tools/list` == 6)
- [x] `backend/app/narrative.py` v0 = `parse_risk_spec` · `taxonomy.py` — 실존 `app/narrative.py`(`parse_risk_spec`+`validate_risk_spec`)·`app/taxonomy.py`
- [ ] `backend/app/adapters/{base,registry}.py` v0(`/tools-map` 도구명 집합 바인딩) · `runner.py` 골격(`panel_loop` 5 s·`sync_loop` 60 s·`nightly_loop` 00:30·`pat_unavailable` 표기) — 실존 없음, 신규
- [x] `backend/app/assets/*.v1.json` 6종(정본) · `backend/app/schemas/{rr_ir, rr_state, rr_diff, risk_spec, seat_opinion}.v1.json` + 유효/무효 픽스처 각 ≥2 — 실존 `app/schemas/*.v1.json` 5종+픽스처, 자산 6종은 `docs/*.v1.json` 에 실존
  - [ ] 델타: 자산 6종을 `backend/app/assets/` 로 이동(package-data 등록)·`docs/` 에서 제거(§0.4.5 문서 디렉터리 금지)
- [ ] `backend/scripts/bootstrap_ra_ontology.py --base <RA REST 오리진>`(6축·12관계, dry-run 기본, 멱등, env `RA_ADMIN_PAT`) · `bootstrap_adh.py`(doc_type 3종·`risk-review-memory`·`external_source=hwax-risk`, env `HWAXRISK_AIDH_API_KEY`) — 실존 없음, 신규
- [x] `backend/tests/{test_boot, test_parity(env HWAX_PORTAL_REPO), test_schemas, test_parser, test_identity}.py` — 실존 `tests/{test_health, test_config_datadir, test_store, test_parse_risk_spec, test_schemas, test_mcp_tools, test_manifest, test_identity}.py`
  - [ ] 델타: `test_boot.py`(3점)·`test_parity.py` 신설 · `test_parse_risk_spec`→`test_parser` · `test_mcp_tools` 6종·`not_implemented` · `test_identity` 되묻기·캐시 1회·위조 헤더 무시 · `test_manifest` 허용 오류 = 루트 `mcp`·`source.ref` 2건
- [ ] `frontend/` — Vite base './' · HashRouter 라우트 5 · 페이지 셸 5 + `SettingsPage` 완성(`GET me`·`PUT me/portal-pat`·box 상태·동의 문구) · `api/risk.api.ts` · `mermaid` 의존 · `pnpm-lock.yaml` — 실존 없음(`app/static/index.html` 플레이스홀더뿐), #28 (ii) 면 P1
- [x] `README.md · checklist.md · context-notes.md` — 실존(+`docs/plan.md` 포인터)
  - [ ] 델타: `hwax_risk.db`→`risk_review.db` · `/api/v1`→`/api` · `/health`→`/api/health` · `schema_migrations`→`_schema_migrations` · 도구 3종→6종 · `.sqlite` 문자열 0건(역사 언급 포함) · context-notes D2 '경로·이름은 이 노트가 정본' → '정본은 포털 plan.md(#28)'
산출물 B — HEAXHub 등록(코드 0)
- [ ] `HEAXHub/integrations/hwax-risk/.portal/manifest.yaml`(매니페스트 전용 디렉터리, 심볼릭 링크 아님) 커밋 → 스캔(즉시 트리거 가능) → `var/sifs/hwax-risk.sif` 빌드 → reconcile 기동 → Caddy `/apps/hwax_risk/*` 자동 라우트 → `var/app_data/hwax_risk/` 생성
- [ ] `var/app_data/hwax_risk/secrets.env`(0600) — `HWAXRISK_PORTAL_PAT · HWAXRISK_HEAX_SERVICE_PAT · HWAXRISK_AIDH_API_KEY` → `redeploy-app.sh hwax-risk`
- [ ] 게이트웨이 `heax-hwax_risk` 자동 흡수 확인(`gateway_config.json`·재시작 없음)
산출물 C — 포털 창(additive)
- [ ] 포털: `backend/config/systems.yaml` 타일 `hwax-risk`(리스크 심사 · jwt-handoff · audience heax-hub · `/heax-hub/api/v1/auth/portal-callback` · auto_post/token · accent rose · category engineering · sort_order 60) + `POST /systems/reload`
- [ ] 포털: `frontend/src/App.tsx` 라우트 `/risk` · `AppHeader.tsx` NavLink '리스크 심사'(카탈로그 조건부) · `pages/risk/RiskLaunchPage.tsx`(launch → 앱 링크 2단, 앱 REST fetch 없음)
- [ ] 포털: `delibTaxonomy.ts`(JobId·JOBS 8행째·JOB_ROUTING·suggestJob append) · `conversations.api.ts` ConvKind · `backend/app/agent/routes.py` `ConvCreate.kind`. 포털 백엔드 라우트·Settings·`.env`·nginx 변경 0
산출물 D — 엔진 additive(A 계획과 동일)
- [ ] `deliberation.py`: `_CHAIR_ITEMS['risk-review']` · `_CHAIR_ADVERSARY['risk-review']`(delib-baseline-defender) · doc_title · `_RISK_SEAT_CONTRACT`(+:2044 직후 role 접미 3줄) · `_RISK_READ_TOOLS` · `_RISK_KEEP_TOOLS`(+`_g` 조립식 조건 ≈3줄 :1897 + `_amap` 상향 + `_narrow` keep or 1줄 :1916) · `_resolve_opts` origin 통과 1줄
- [ ] `hwax-deliberate.js`: `CHAIR_ITEMS` · `CHAIR_ADVERSARY` · 제목 삼항 · `RISK_SEAT_CONTRACT` · whenToUse(순수 리터럴)
- [ ] `HWAXPortal/scripts/check_chair_parity.py`(`--py ../HWAXAgentServer/deliberation.py --js infra/pipeline/hwax-deliberate.js --contract ../HWAXRisk/backend/app/assets/seat-contract.v1.json`)
- [ ] `delib_metrics.py` 에 risk_spec 파싱 성공률 1종
산출물 E — 문서(포털 `docs/design-risk-review/{plan, checklist, context-notes}.md` · 앱 리포 `HWAXRisk/docs/odb-adapter-contract.md`(정본, 실존 — §2.5.3) · decision-table.md §8.3.7)
통과 기준 (17)
- [ ] (1) `check_chair_parity.py` exit 0 — 결정문·반대석·좌석 계약 16 문자열·제목 바이트 동일, 앱 `test_parity.py` 동일 결과(env 없으면 skip)
- [ ] (2) RA `list_object_types` 에 6축·12관계, `--apply` 재실행 생성 0·기존 15축 17관계 무변경, 앱 코드·`secrets.env` 에 `rat_`·`RA_ADMIN_PAT` 0건
- [ ] (3) AIDataHub doc_type 3종·`risk-review-memory` 존재, 재실행 생성 0, `import?external_source=hwax-risk` dry_run 200(키 없이 401 또는 anonymous 통과 기록)
- [ ] (4) StepForge 직접 읽기 — Caddy `/apps/step_forge/api/projects/{id}/tree` heax 서비스 PAT 로 200 · 무헤더 401 · 게이트웨이 `heax-step_forge` `project_tree` 동일 노드 수 · 앱 코드에 GET 외 메서드 0건 · `gateway_config.json` diff 0(`rest.heax` 불요)
- [ ] (5) 기존 8 chair e2e 결정문 형식 불변 + `_g`/`_narrow` 단위 테스트(apps 유무·chair 유무 조합, `get_agent_session` 항상 부재)
- [ ] (6) `/심의`+risk-review 단발 3회 — 파싱 ≥2/3 · 반대석 origin=adversary 3/3 · personas origin 보존 3/3 · `extra_seats==∅` 3/3
- [ ] (7) `_persona_round` sysmsg 덤프에서 `[리스크 심사 좌석 계약]`+`[<dom>]` 5/5석 검출, chair=default 에서 0/6
- [ ] (8) apps 지정 상태에서 rel 좌석 `search_objects`(keep) · sim 좌석 `report_part_risk`(app+read) 실호출 SSE ≥1
- [ ] (9) 러너 자격 실측 3항 → context-notes — (a) 서비스 PAT 로 SIF 안에서 `/agent/conversations` conv_id + `/agent/chat` 200·SSE done / (b) 등록 사용자 PAT 로 DynaForge per_user_sso `list_sessions` ≥1, 서비스 PAT 는 0건 / (c) aud 불일치 422 `pat_audience`·`/agent/chat` 401, 만료 임박 422 `pat_expiring`. (a) 실패 시 폴백은 §6.7.1 (B)
- [ ] (10) 앱 pytest 스키마 라운드트립 5종·무효 픽스처 거부 ≥10·`parse_risk_spec` 픽스처 3종
- [ ] (11) 포털 `tsc -b && vite build` + playwright: `/deliberate` Job 카드 8·기존 7 텍스트 불변·`/risk` 버튼 2·`/apps/hwax_risk/api/*` 요청 0·타일 밖 그룹 NavLink 4. 앱 `pnpm build` 통과
- [ ] (12) 포털 무변경 — `openapi.json` diff 0(`/api/risk/*` 부재)·`/agent/conversations` 응답 동일·`config.py`·`.env.example` diff 0·앱 정지 전후 포털/HEAX 응답 코드 동일
- [ ] (13) 앱 기동 3점(로컬·SIF) — `GET /api/health` 200 `{ok, app_version '0.1.0', schema_version 1}` ≤20 s · `POST /mcp` initialize 200 + `mcp-session-id` + `tools/list` 6 · `GET /` index.html. Caddy `/apps/hwax_risk/` 익명 401·인증 200
- [ ] (14) 매니페스트·등록 — `validate_manifest` 루트 `mcp`·`source.ref` 외 오류 0(정확히 2건, `tags` 는 스키마 안) · 스캐너 `by_action` 1건 · 카탈로그 `hwax_risk beta company` · `sif_build_hwax-risk.log` 성공 · `var/sifs/hwax-risk.sif`+`.hash` · state 파일 `hwax_risk.json` · Caddy 라우트 2건
- [ ] (15) 게이트웨이 자동 흡수 — heax `/api/v1/mcp/servers` 에 `hwax_risk` 1건 · 재시작 없이 `/tools-map` 에 `heax-hwax_risk` `risk_*` 6종(len +6, 타 백엔드 불변) · `gateway_config.json` diff 0 · `risk_get_registry` → `not_implemented`
- [ ] (16) 데이터 경로·app-data 왕복 — `var/app_data/hwax_risk/{risk_review.db(user_version 1, 32+2표), origin.json(hostname dev), exports/}` · `appdata-to-drive.sh` → Drive `latest/` tar 에 `.backup` 스냅샷 · 비운 뒤 `appdata-merge-from-drive.sh` 복원 `integrity_check ok` · `redeploy-app.sh hwax-risk` 후 보존
- [ ] (17) 신원 해석 — `GET /api/me` 쿠키 `source:'cookie'` / Bearer `source:'bearer'` / 위조 `X-Heax-User-Email` 무시 / 무토큰 Caddy 401 / 10회 호출에 `/auth/me` 1회. `PUT /api/me/portal-pat` 오류 4종 422 · 정상 등록 `_user_credentials` 1행 · null 삭제 0행
얻는 것 — 핸드오프 카드·MCP `chairTemplate:'risk-review'` 로 evidence 기반 단발 심사(결정문 8항목+risk_spec+기준선 옹호 지정석) + 포털 메뉴 → HEAX SSO → 앱 셸(`/apps/hwax_risk/`, PAT 등록) + 게이트웨이 `risk_*` 6종 노출 + dev app-data 백업 경로 검증

## P1 단일 과제 IR 스냅샷·상태 평가·게이트·규칙(MCAD) (§9.2) — 전부 앱 리포
- [ ] `backend/app/risk_store.py` P1 표 11종 쓰기 경로 · `adapters/{mcad,ecad_stub}.py`(Caddy `/apps/step_forge/api` GET, heax 서비스 PAT + 게이트웨이 `heax-step_forge`) · `ir_builder.py` · `sameas.py` v0 · `state.py` · `render.py`(판단어 린터) · `routes.py`(projects/sources/snapshots/dims/refs/rule_hits) · rules 시드 6종 · `frontend/src/pages/{RiskHomePage,ProjectPage,SnapshotPage}.tsx`(HashRouter) · '단발 심사 열기'(포털 `/deliberate` 새 탭 + E0·E1 클립보드) · `prior_evidence` v0(E0·E1·E9) · `ra_client` v0(게이트웨이 MCP) · `export.py` v0(`GET /api/export`·`POST /api/import`) · 골든 `backend/tests/golden/sif-e2e.ir.json`
- [ ] D6 모델 출처 — `rr_panels.model_json`·`rr_coverage.model`(v1 DDL, §5.2.2 E) · `runner.snapshot_model(origin)`(agent-server `GET /health` 픽스처 → `model_json{…, captured:'health_snapshot'}`, 시작·종료 불일치 → `quality.flag=model_changed_midrun`, 불통 → `unavailable`/`'unknown'`) 단위 테스트 · export JSONL 에 두 컬럼 포함(§9.2 (13))
- [ ] 통과 13항 — sif-e2e 노드3·엣지2 일치·ir_hash 결정론 / Caddy GET 원문만·StepForge sqlite mtime 불변 / world_center ±0.01mm / G1~G7 픽스처 5 / 500파트 누락0·≤10s / 린터 판단어 0 / rule_hits 6종·payload_hash 동일 / rr_snapshot_calls gzip / ckey 결정론 / prior_evidence 라인 ≤CAP·드롭 0 / 앱 ruff·pytest·pnpm build·포털 `/deliberate` 스모크 / export→import 라운드트립 행 수 동일·409 `schema_mismatch`·재import inserted 0 / 모델 출처 컬럼 2·`snapshot_model()` 픽스처·`model_changed_midrun`(§9.2 (13))
- [ ] 선행(§10 15·2): 기존 StepForge 프로젝트 재파싱·재검출은 사용자 실행, 골든 프로젝트 준비, heax 서비스 PAT 발급
얻는 것 — 앱 화면의 과제 등록·스냅샷 현황판·게이트·성격 씨앗·규칙 히트·단발 심사 브리프 + export/import v0

## P2 Dyna 어댑터·same-as·원장·3층 diff·summary_text (§9.3) — 전부 앱 리포
- [ ] `adapters/dyna.py`(게이트웨이 `heax-kooremapper_mcp`, 러너 자격 (b) 사용자 PAT / (a) 서비스 시야 = `dyna_absent`) · `sameas.py`(사다리 7단·헝가리안·원장 재적용·ckey 자동 승계) · `diff.py`(3층·임계·comparability·의미 이벤트) · `rr_diffs/rr_diff_events` · `mcp_server.py` `risk_get_snapshot`·`risk_get_diff` 실구현 · `components/{SameAsResolver,GateBanner,DiffView}.tsx`·`pages/ComparePage.tsx` · `prior_evidence` v1(E2~E4) · 합성 픽스처 6종 · `ra_client` design_diff · `export.py` 표 추가
- [ ] 통과 11항 — 합성 6종 이벤트 정확·self-diff 0 / 브리지 same-as 100% / 교란 30쌍 정밀 ≥0.95·재현 ≥0.9 / 원장 manual_ledger 복원 / tol·result parity 제외 / summary ≤2000·린터 0 / 500·2000 diff <5s + RSS 피크 기록(§10 27) / (a) 서비스 PAT 는 `list_sessions` 0건 → `dyna_absent`·예외 0·`kr_` 문자열 0건 / energy_flow src/dst 확정 / G2 fail 시 semantic.blocked_by / ckey·subject_key 일치 ≥0.95 + §4.9 픽스처 승계
- [ ] 선행: P0(9)(b) 결과, DynaForge 세션·K파일·리포트 각 1건(§10 15·15a), §10 4
얻는 것 — 앱 화면의 두 과제 비교(3층 diff·결론 없는 요약)·pair 단발 심사(E0~E4)·게이트웨이 `risk_get_snapshot/diff`

## P3 risk-review 패널 e2e·서술 저장 (§9.4) — 전부 앱 리포
- [ ] `narrative.py` 완성(cites·dangling·evidence_grade·seat_opinion·E0c·E0~E4+E9) · `runner.py` 단일 패널(§6.7.1 (A) 포털 `/agent/chat` 포털 PAT Bearer · 자격 (a)/(b) 결정 · `/agent/conversations kind:'risk-review'` · SSE 캡처 · 사전 예산 · 커버리지 · `quality_json.{call_path,credential,call_groups}` · (B) 폴백 규칙) · `registry.py` · `character.py` · `ra_client`(게이트웨이 MCP, 항상 서비스 PAT)/`adh_client`(`external_source=hwax-risk`) · 표 7종 · `routes.py`(targets/jobs/panels/complete/resync/refs) · `mcp_server.py` `risk_get_registry·risk_claims_for_ref·risk_submit_panel_result` 실구현 · `TargetPage` 최소 + `PanelTranscript`(앱 DB 렌더) · SSE 픽스처 3종
- [ ] 통과 14항 — 파싱 성공·findings ≥3·gains ≥1·facet 8·dangling 0 / 도구 사용률 ≥80%·IR 인용 ≥50%·contested ≥1 / personas 집합==seats∪adversary·extra_seats==∅·human_note 부재 / SSE 귀속 ≥95%(events[] 경로 포함) / conv_store kind='risk-review'·owner=PAT sub·`/deliberate` 0건·`call_path='portal'`·`credential` 일치 / UPSERT 중복 0·agents 실전문가 0·`rat_` 0건 / 70분 뒤 (b) 등록 PAT 그대로 성공(재발급 없음)·만료 임박 픽스처 (a) 강등 / 사전 예산 ≤120·≤20분·over_budget 재실행 0 / MCP `risk_submit_panel_result`·REST complete 동일 파서·evidence_only·`actor_verified:false`·owner_sub 승계 / header_mismatch 픽스처 / 회귀 0·openapi diff 0 / 병합 멱등 / 폴백 (B) — 기본 꺼짐·dev 켜면 3회 후 `agent_direct` 완주·401 은 `pat_unavailable` / `resync` → pending·비소유자 403
얻는 것 — 등록부·성격 서술·좌석 의견이 3층(앱 DB 정본·RA·AIDataHub)에 저장되는 완결 심사 1건 + MCP 결과 원장 반영 + 러너 경로 (A) 실증

## P4 커버리지 원장·편성·배치 러너·완결 판정·통합 보고서 (§9.5) — 전부 앱 리포
- [ ] `planner.py`(Tier A/B/C·라운드로빈·인접·deferred·carried·결정론) · `rr_roster/rr_coverage`(부분 유니크 `rr_cov_active`)·`rr_jobs` · `runner.py` 배치 모드(경로 (A) 동일) · C1~C3 · 통합 보고서 v1/v2/v3(게이트웨이 MCP) · `TargetPage` 완성 + `CoverageHeatmap/PanelRunner`(히트맵·자격 표시·미착석 배지·verdict 확정) · `GET /api/meta/metrics` · `delib_metrics.py` 지표 6종(원천 앱 REST) · `tests/test_coverage_sm.py`
- [ ] 통과 12항 — C1 도달(RA 백엔드 불통/403 에서도, 포털 PAT 유효) / 원장 불변식 / 편성 결정론·동시 편성 이중 착석 0 / 실패 주입 재시도→skipped / ecad deferred ≈105석 / carried 조건·되돌리기 / Tier B ≤6h·슬롯 ≤2·일일 24 / done_weak→C2 strong / 미착석 배지 N 일치 / close_level C2/C3 동작 / 수확 체감 정지 / `redeploy-app.sh hwax-risk` 재기동 복구·conv_id 연결 유지
- [ ] 결정(§10 5·6·7·6a·6b·12a): 로스터 도메인 15·ECAD 6·xd 전원 / 기본 마감 C2 vs C3 / carried 90일 / 패널 LLM 상한 120 / 야간 창·concurrency / DOCX 불요
얻는 것 — "전체 HW/XD 전문가 한 번씩" 회계(C3 문자적 충족, C2 비용 타협)와 레벨별 리스크 심사 보고서

## P5 재사용 루프 (§9.6)
- [ ] 앱: `prior_evidence` 완성(E5~E8·별칭·kNN·hybrid·agent_search 예산표) · `rr_delta_priors/rr_iface_alias` · `rr_part_keys` merge/rename UI · `mcp_server.py` `risk_get_brief(target_key, tier='B')` 실구현(게이트웨이 흡수는 P0 완료, 설정 변경 0) · 성격 승격 UI · `RecallPreview` · `/api/precedents` · `/api/projects/{id}/similar`
- [ ] 엔진·포털: `deliberation.py` `_RISK_READ_TOOLS['heax-hwax_risk']`(registry 발견값 앱키) · `HWAXPortal/infra/pipeline/hwax-risk-review.js`(args `{targetKey, tier, panels?, actor?}`, 포털 REST fetch 없음) + `sync-workflows.sh`
- [ ] 통과 9항 — E5~E8 실림·드롭 0(최대 길이 픽스처) / kNN top1 / agent_search 재현 ≥0.8·E7 슬롯 규칙 / narr:/reg: 인용 ≥1·없는 인용 dangling / **계보 없는 과제 회수 ≥1** / sim-plan 좌석이 apps `heax-hwax_risk` 로 `risk_get_registry` 자유조회·`/tools-map` 수 P0 기준 불변 / MCP 워크플로 1패널 `risk_get_brief`→`risk_submit_panel_result` 원장 done·tier A `tier_a_web_only` / 판단어 0·부정 증거 항목 / MCP `actor` 미검증 기록·owner_sub 승계·미해석 `caller_unresolved`·헤더 미사용 0건
- [ ] 결정(§10 8a·13·13a·17·26)
얻는 것 — 배치가 쌓일수록 브리프가 두터워지는 폐루프·다른 connectivity 회수·다른 심의의 등록부 읽기·Claude Code L2 보충 회차

## P6 학습 루프 (§9.7) — 전부 앱 리포
- [ ] `rr_labels/rr_patterns/rr_rules/rr_metrics/rr_curation_queue` 쓰기 경로 · 라벨 동기 잡(`sync_loop` 확장 — RA incident·test_run 게이트웨이 읽기·DynaForge 러너 자격·VOC·수동) · 조건 DSL·백테스트 · 지표 대시보드(TargetPage '품질' 카드)·'루프 작동' 배지 · `risk_pattern_card` doc_type(`bootstrap_adh.py`) · `visibility` 정책(§10 11) · RA typed 템플릿 절차서
- [ ] 통과 8항 — incident 동기 auto confirmed 는 match 1.0 만 / 라벨 20건 지표·n<5 표기 / 합성 30타깃 candidate 정확·거짓 0 / 승격 API 백테스트 게이트 422 / rule_hits 결정론 / taxonomy_version·재매핑 dry-run 0 / S2 게이트 전 예측기 코드 0줄 / org 토글 읽기·쓰기 0
- [ ] 결정(§10 11·12·21)
얻는 것 — 검증된 선례·규칙과 루프 작동 여부의 계측(앱 DB 누적, `GET /api/meta/metrics`)

## P7 ODB 실연동·예측기 승격(조건부) (§9.8)
- [ ] 앱 `adapters/ecad.py`(계약 4도구, `registry.py` 도구명 발견) · ir_version 1.1(`MIGRATIONS` v2) · refdes↔파트 사전 UI · `ecad.*` 이벤트 · SedInput 어댑터 · 예측기 HEAX 앱 계획서(별도 리포·매니페스트, 라벨 원천 `GET /api/export`)
- [ ] 통과 4항 — 계약·상한 테스트 / component↔mcad ≥0.9·deferred 재생성 / predict_sed out_of_range 강등 / 예측기 활성화 게이트(n_labeled ≥50·project ≥15)
- [ ] 선행(§10 9·14a): ODB hub 계약 합의, 명명 규칙

## cae00 이관(단계 아님 — §8.4.4 6, §10 21·22 결정 후, P3 통과 뒤)
- [ ] dev `build-all-to-drive.sh`(SIF·app-data → Drive) → cae00 `update.sh` 또는 `deploy-all-from-drive.sh`(`dist-from-drive.sh` 가 `var/sifs/hwax-risk.sif` 배치, 매니페스트는 HEAXHub git pull, `appdata-merge-from-drive.sh` 첫 배포 시드) → reconcile 기동 → cae00 에서 서비스 PAT·heax PAT·AIDH 키 재발급 → cae00 `secrets.env` → `redeploy-app.sh hwax-risk` → SettingsPage/TargetPage '재동기'. 이후 dev→cae00 은 `GET /api/export` → `POST /api/import` 만. dev 에서 `deploy-all` 류 금지

## 반영 절차(운영, 각 단계 후 — §8.4.4 1~5)
- [ ] 1 엔진: agent-server 재기동 → `sync-workflows.sh` → erag 재색인 → `check_chair_parity.py` exit 0
- [ ] 2 포털 창: `systems.yaml` 타일 → `POST /systems/reload` → 프론트 빌드·배포 → 포털 백엔드 재기동(`ConvCreate.kind`). 포털 `.env` 변경 없음
- [ ] 3 앱 등록·빌드(dev): `integrations/hwax-risk/.portal/manifest.yaml` 커밋 → 스캔 → `sif_build_hwax-risk.log` → reconcile 기동 → `integration_hwax_risk.log` → Caddy `/apps/hwax_risk/` 401 → 로그인 후 `/api/health` 200
- [ ] 4 app-data: `var/app_data/hwax_risk/` 확인 → `secrets.env`(0600) → `redeploy-app.sh hwax-risk` → `origin.json.hostname` 확인 → `bootstrap_ra_ontology.py --base <RA> --apply`(env `RA_ADMIN_PAT`) · `bootstrap_adh.py` → dev crontab `appdata-to-drive.sh` 일 1회
- [ ] 5 게이트웨이 자동 흡수 확인만(재시작 없음, 안 되면 매니페스트 status/mcp.expose → state 파일 → `heax_registry.token` 가시성 순으로 점검, restart 시 `-sTCP:LISTEN` 주의)
