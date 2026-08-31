<!-- 설계 리스크 심사 — 단계별 실행 체크리스트(plan.md §9 에서 도출, 진행하며 체크) -->
# 설계 리스크 심사 — 체크리스트

정본은 `plan.md`(§9 단계 계획·§10 열린 질문). 이 문서는 실행 순서와 완료 판정만 요약한다. 항목 뒤 괄호는 plan.md 절.

## 착수 전 — 사용자 결정 (§10, P0 착수 전 답이 필요한 것)
- [ ] (1) RA 시스템관리자 PAT 를 포털 secrets(`ra_admin_pat`)에 서비스 계정으로 보관 — 승인/미승인(미승인이면 P0(2) 보류, `external_sync.ra=unavailable`)
- [ ] (2) 게이트웨이 `gateway_config.json` `rest.heax`·`portal.audience_ok` 설정 변경 권한(불가 시 어댑터 `mcp_degraded`)
- [ ] (3) 배치 러너의 사용자 PAT 대리 발급(`issue_user_pat`, 60분·읽기 전용·`consent:true`) 승인(미승인이면 §8.2.4 브라우저 세션 폴백)
- [ ] (10) AIDataHub doc_type 3종·의사 에이전트 `risk-review-memory` 생성 승인
- [ ] (8) 성격 통제 어휘 v1·택소노미 v1 초안 확정 주체 지정(초안 그대로 시작 가능)

## P0 부트스트랩 — 계약·엔진 손잡이·저장소 준비 (§9.1)
산출물
- [ ] 문서 6종 JSON: `taxonomy.v1.json` · `character-vocab.v1.json` · `character-seed-rules.v1.json` · `adjacency.v1.json` · `rules-seed.v1.json` · `seat-contract.v1.json` + `odb-adapter-contract.md`
- [ ] 스키마 `backend/app/risk/schemas/{rr_ir, rr_state, rr_diff, risk_spec, seat_opinion}.v1.json` + 유효/무효 픽스처 각 ≥2
- [ ] `backend/app/risk/narrative.py` v0 = `parse_risk_spec`(parseSimSpec 복제) · `taxonomy.py` · `__init__.py register()` · `routes.py` 골격 · `risk_store.py` 빈 스토어 · Settings 14 필드
- [ ] `backend/scripts/bootstrap_ra_ontology.py`(6축·12관계, dry-run 기본, 멱등) · `bootstrap_adh.py`
- [ ] `deliberation.py`: `_CHAIR_ITEMS['risk-review']` · `_CHAIR_ADVERSARY['risk-review']`(delib-baseline-defender) · doc_title · `_RISK_SEAT_CONTRACT`(+:2044 직후 role 접미 3줄) · `_RISK_READ_TOOLS` · `_RISK_KEEP_TOOLS`(+`_g` 조립식 조건 ≈3줄 :1897 + `_amap` 상향 + `_narrow` keep or 1줄 :1916) · `_resolve_opts` origin 통과 1줄
- [ ] `hwax-deliberate.js`: `CHAIR_ITEMS` · `CHAIR_ADVERSARY` · 제목 삼항 · `RISK_SEAT_CONTRACT` · whenToUse(순수 리터럴)
- [ ] `HWAXPortal/scripts/check_chair_parity.py`(PY/JS/JSON 바이트 동일)
- [ ] `routes.py` ConvCreate kind 값 · `delibTaxonomy.ts`(JobId·JOBS 8행째·JOB_ROUTING) · `conversations.api.ts` ConvKind · `App.tsx` 라우트 4 + `RiskHomePage` 플레이스홀더 · `AppHeader` NavLink(플래그 조건부)
- [ ] 게이트웨이 `gateway_config.json` `rest.heax`·`audience_ok`
- [ ] `backend/tests/risk/` 신설(스키마 라운드트립·파서·parity·`_g`/`_narrow` 단위·플래그 스모크)
- [ ] `delib_metrics.py` 에 risk_spec 파싱 성공률 1종
통과 기준 (12)
- [ ] (1) `check_chair_parity.py` exit 0 — 결정문·반대석·좌석 계약 16 문자열·제목 바이트 동일
- [ ] (2) RA `list_object_types` 에 6축·12관계, 재실행 생성 0·기존 15축 17관계 무변경
- [ ] (3) AIDataHub doc_type 3종·`risk-review-memory` 존재, 재실행 생성 0
- [ ] (4) `issue_user_pat(aud='heax')` 로 게이트웨이 rest_proxy StepForge tree GET 200 · POST 405 · 타 aud 401
- [ ] (5) 기존 8 chair e2e 결정문 형식 불변 + `_g`/`_narrow` 단위 테스트(apps 유무·chair 유무 조합, `get_agent_session` 항상 부재)
- [ ] (6) `/심의`+risk-review 단발 3회 — 파싱 ≥2/3 · 반대석 origin=adversary 3/3 · personas origin 보존 3/3 · `extra_seats==∅` 3/3
- [ ] (7) `_persona_round` sysmsg 덤프에서 `[리스크 심사 좌석 계약]`+`[<dom>]` 5/5석 검출, chair=default 에서 0/6
- [ ] (8) apps 지정 상태에서 rel 좌석 `search_objects`(keep) · sim 좌석 `report_part_risk`(app+read) 실호출 SSE ≥1
- [ ] (9) PAT 실측 3항(루프백 chat 200 / DynaForge per_user_sso / rest_proxy aud) → context-notes 기록, (a) 실패 시 §8.2.4 폴백 확정
- [ ] (10) pytest 스키마 라운드트립 5종·무효 픽스처 거부 ≥10
- [ ] (11) `tsc -b && vite build` + playwright: `/deliberate` Job 카드 8·기존 7 텍스트 불변·`/risk-review` 플래그 off 안내
- [ ] (12) `risk_review_enabled=false` 에서 `/api/risk/*` 404, `/api/agent/conversations` 응답 동일
얻는 것 — 핸드오프 카드·MCP `chairTemplate:'risk-review'` 로 evidence 기반 단발 심사(결정문 8항목+risk_spec+기준선 옹호 지정석)

## P1 단일 과제 IR 스냅샷·상태 평가·게이트·규칙(MCAD) (§9.2)
- [ ] `risk_store.py` P1 표 11종 · `adapters/{base,registry,mcad,ecad_stub}.py` · `ir_builder.py` · `sameas.py` v0 · `state.py` · `render.py`(판단어 린터) · `routes.py`(projects/sources/snapshots/dims/refs/rule_hits) · rules 시드 6종 · `RiskHomePage/ProjectPage/SnapshotPage` · `prior_evidence` v0(E0·E1·E9) · `ra_client` v0 · 골든 `sif-e2e.ir.json`
- [ ] 통과 11항 — sif-e2e 노드3·엣지2 일치·ir_hash 결정론 / StepForge sqlite mtime 불변 / world_center ±0.01mm / G1~G7 픽스처 5 / 500파트 누락0·≤10s / 린터 판단어 0 / rule_hits 6종·payload_hash 동일 / rr_snapshot_calls gzip / ckey 결정론 / prior_evidence 라인 ≤CAP·드롭 0 / ruff·pytest·`/deliberate` 스모크
- [ ] 선행(§10 15): 기존 StepForge 프로젝트 재파싱·재검출은 사용자 실행, 골든 프로젝트 준비
얻는 것 — 과제 등록·스냅샷 현황판·게이트·성격 씨앗·규칙 히트·단발 심사 브리프

## P2 Dyna 어댑터·same-as·원장·3층 diff·summary_text (§9.3)
- [ ] `adapters/dyna.py` · `sameas.py`(사다리 7단·헝가리안·원장 재적용·ckey 자동 승계) · `diff.py`(3층·임계·comparability·의미 이벤트) · `rr_diffs/rr_diff_events` · `SameAsResolver/GateBanner/DiffView/ComparePage` · `prior_evidence` v1(E2~E4) · 합성 픽스처 6종 · `ra_client` design_diff
- [ ] 통과 11항 — 합성 6종 이벤트 정확·self-diff 0 / 브리지 same-as 100% / 교란 30쌍 정밀 ≥0.95·재현 ≥0.9 / 원장 manual_ledger 복원 / tol·result parity 제외 / summary ≤2000·린터 0 / 500·2000 diff <5s / 서비스 계정 private 세션 미개방 / energy_flow src/dst 확정 / G2 fail 시 semantic.blocked_by / ckey·subject_key 일치 ≥0.95 + §4.9 픽스처 승계
- [ ] 선행: P0(9) PAT 결과, DynaForge 세션·K파일·리포트 각 1건(§10 15·15a)
얻는 것 — 두 과제 비교 화면(3층 diff·결론 없는 요약)과 pair 단발 심사(E0~E4)

## P3 risk-review 패널 e2e·서술 저장 (§9.4)
- [ ] `narrative.py` 완성(cites·dangling·evidence_grade·seat_opinion·E0c·E0~E4+E9) · `runner.py` 단일 패널(루프백·issue_user_pat·SSE 캡처·사전 예산·커버리지) · `registry.py` · `character.py` · `ra_client`/`adh_client` · 표 7종 · `TargetPage` 최소 · SSE 픽스처 3종
- [ ] 통과 12항 — 파싱 성공·findings ≥3·gains ≥1·facet 8·dangling 0 / 도구 사용률 ≥80%·IR 인용 ≥50%·contested ≥1 / personas 집합==seats∪adversary·extra_seats==∅·human_note 부재 / SSE 귀속 ≥95%(events[] 경로 포함) / kind='risk-review'·`/deliberate` 0건 / UPSERT 중복 0·agents 실전문가 0 / 70분 뒤 PAT 재발급 / 사전 예산 ≤120·≤20분·over_budget 재실행 0 / MCP complete evidence_only / header_mismatch 픽스처 / 회귀 0 / 병합 멱등
얻는 것 — 등록부·성격 서술·좌석 의견이 3층에 저장되는 완결 심사 1건 + MCP 결과 원장 반영

## P4 커버리지 원장·편성·배치 러너·완결 판정·통합 보고서 (§9.5)
- [ ] `planner.py`(Tier A/B/C·라운드로빈·인접·deferred·carried·결정론) · `rr_roster/rr_coverage`(부분 유니크 `rr_cov_active`)·`rr_jobs` · runner 배치 모드 · C1~C3 · 통합 보고서 v1/v2/v3 · `TargetPage` 완성(히트맵·미착석 배지·verdict 확정) · 지표 6종 · 불변식 테스트
- [ ] 통과 12항 — C1 도달(RA 미가용에서도) / 원장 불변식 / 편성 결정론·동시 편성 이중 착석 0 / 실패 주입 재시도→skipped / ecad deferred ≈105석 / carried 조건·되돌리기 / Tier B ≤6h·슬롯 ≤2·일일 24 / done_weak→C2 strong / 미착석 배지 N 일치 / close_level C2/C3 동작 / 수확 체감 정지 / 재기동 복구
- [ ] 결정(§10 5·6·7·6a·6b): 로스터 도메인 15·ECAD 6·xd 전원 / 기본 마감 C2 vs C3 / carried 90일 / 패널 LLM 상한 120 / 야간 창·concurrency
얻는 것 — "전체 HW/XD 전문가 한 번씩" 회계(C3 문자적 충족, C2 비용 타협)와 레벨별 리스크 심사 보고서

## P5 재사용 루프 (§9.6)
- [ ] `prior_evidence` 완성(E5~E8·별칭·kNN·hybrid·agent_search 예산표) · `rr_delta_priors/rr_iface_alias` · `rr_part_keys` merge/rename UI · `mcp_server.py`(hwax-risk 5도구)+게이트웨이 항목 · `hwax-risk-review.js`+sync · 성격 승격 UI · `RecallPreview` · `/precedents` · `/similar`
- [ ] 통과 9항 — E5~E8 실림·드롭 0(최대 길이 픽스처) / kNN top1 / agent_search 재현 ≥0.8·E7 슬롯 규칙 / narr:/reg: 인용 ≥1·없는 인용 dangling / **계보 없는 과제 회수 ≥1** / sim-plan 좌석의 `risk_get_registry` 자유조회·도구 수 +5 / MCP 패널 원장 done·tier A 422 / 판단어 0·부정 증거 항목 / hwax-risk 호출자 신원
- [ ] 결정(§10 8a·13·13a·13b·16)
얻는 것 — 배치가 쌓일수록 브리프가 두터워지는 폐루프와 다른 connectivity 회수

## P6 학습 루프 (§9.7)
- [ ] `rr_labels/rr_patterns/rr_rules/rr_metrics/rr_curation_queue` · 라벨 동기 잡(RA incident·test_run·DynaForge·VOC·수동) · 조건 DSL·백테스트 · 지표 대시보드·'루프 작동' 배지 · `risk_pattern_card` doc_type · `visibility` 정책 · RA typed 템플릿 절차서
- [ ] 통과 8항 — incident 동기 auto confirmed 는 match 1.0 만 / 라벨 20건 지표·n<5 표기 / 합성 30타깃 candidate 정확·거짓 0 / 승격 API 백테스트 게이트 422 / rule_hits 결정론 / taxonomy_version·재매핑 dry-run 0 / S2 게이트 전 예측기 코드 0줄 / org 토글 읽기·쓰기 0
- [ ] 결정(§10 11·12·12a)
얻는 것 — 검증된 선례·규칙과 루프 작동 여부의 계측

## P7 ODB 실연동·예측기 승격(조건부) (§9.8)
- [ ] `adapters/ecad.py`(계약 4도구) · ir_version 1.1 · refdes↔파트 사전 UI · `ecad.*` 이벤트 · SedInput 어댑터 · 예측기 앱 계획서
- [ ] 통과 4항 — 계약·상한 테스트 / component↔mcad ≥0.9·deferred 재생성 / predict_sed out_of_range 강등 / 예측기 활성화 게이트(n_labeled ≥50·project ≥15)
- [ ] 선행(§10 9·14a): ODB hub 계약 합의, 명명 규칙

## 반영 절차(운영, 각 단계 후 — §8.4.4)
- [ ] agent-server 재기동 → `sync-workflows.sh` → erag 재색인 → 포털 `.env`(`RISK_REVIEW_ENABLED`·secrets)·재기동 → 게이트웨이 설정·재기동(`-sTCP:LISTEN` 주의) → `bootstrap_ra_ontology.py --apply` → `bootstrap_adh.py` → (P5) `hwax-risk` 게이트웨이 항목. dev 에서 `deploy-all` 류 금지.
