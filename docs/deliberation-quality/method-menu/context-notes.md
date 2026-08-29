<!-- 심의 방법 메뉴 구현 — 결정과 근거(계속 갱신) -->
# 심의 방법 메뉴 — 컨텍스트 노트

작업 중 내린 결정과 이유. 다음 세션이 재유도 없이 이어가도록 계속 덧붙인다.

## 그라운드 트루스 (착수 시점 확인)
- **현존 chairTemplate 5종** (JS `infra/pipeline/hwax-deliberate.js` CHAIR_ITEMS · PY `HWAXAgentServer/deliberation.py` _CHAIR_ITEMS):
  `default` · `mechanism` · `sim-plan` · `test-plan` · `build-plan`.
- **산출 heading 맵** (JS hwax-deliberate.js:337 · PY deliberation.py:2151): sim-plan→해석 계획서,
  test-plan→시험 계획서, build-plan→구축 계획서, 그 외→의사결정문.
- **계약 결함**: `routes.py` DelibOpts(58)에 `chair_template` 필드가 없다. 포워딩은
  `delib_opts.model_dump(exclude_none=True)`(routes.py:396)라 Pydantic v2 기본(extra=ignore)에서
  **chair_template 이 조용히 버려진다**. MCP 경로(워크플로 args)만 동작, 웹 경로는 무효였다.
- **프론트 이미 존재**: `HandoffBrief.tsx`(Screen A, 평면 select 4종)·`pages/DeliberatePage.tsx`
  (`/deliberate`, Screen B, 현재 topic→experts 단계만).

## 결정

### D1. 원인 규명 = 신규 `diagnosis`, `mechanism` 과 분리
- `mechanism` 은 "해석 전 인과사슬·지배방정식 후보·미지 파라미터"를 확정해 **sim-plan 의 입력**이
  되는 전반부다(sim-deliberate 가 mechanism→sim-plan 으로 이미 연쇄). 산출이 sim 지향.
- 목업의 **원인 규명(FTA↔FMEA)**은 "원인 불명·특정 로트/조건만 → cut set·미지영역·8D"의
  **불량 진단**이다. 산출 성격이 다르다.
- 따라서 원인 규명은 별도 `diagnosis` chairTemplate 로 만들고, `mechanism` 은 해석 설계의
  전반부로 그대로 둔다(목업 6카드에서 mechanism 은 top-level 이 아님).

### D2. 신규 엔진 3종 (③)
- `diagnosis` (원인 규명) — 결함 사슬(FTA)↔양식(FMEA)·is/is-not(KT)·가설 가중(ACH)·cut set·지배원인·미지영역.
- `option-select` (안 선택) — Pugh 2라운드(기준·가중·채점→재설계)·Flip(무엇이 바뀌면 결론이 뒤집히나)·하이브리드안.
- `credibility` (신뢰 판정) — NASA-STD-7009 신뢰도 축(입력·검증·불확실·성숙도) 채점 + red-team/severe test·go/no-go.
- 셋 다 기존 템플릿 톤(번호 항목·"비우면 실패" 강제)과 맞춘다. 두 엔진 동일 키·동일 항목.

### D3. Modifiers(2층) = 프롬프트 주입 오버레이, chairTemplate 무관 합성
- 계약: `delib_opts.modifiers: list[str]` (화이트리스트, cap 5). 각 값이 정의된 지시 블록을
  BASE(또는 좌석 라운드 프롬프트)에 덧붙인다 — evidence 주입과 같은 방식.
- 5종: `voi`(교착 정산·Value of Information) · `premortem`(사전부검) · `toulmin`(논증 엄밀·warrant 강제)
  · `eliminative`(완결 기준·defeater 유형→언제 끝) · `anon1r`(익명 1R·독립 추정 먼저, IDEA/Delphi 유용부분).
- Job 이 "무엇을 산출하나"라면 Modifier 는 "어떻게 더 엄밀하게/안전하게 굴리나". 직교.

### D4. 계약 수정 (A)
- routes.py DelibOpts 에 `chair_template`(유실 수정)·`modifiers` 선언 추가.
- deliberation.py `_resolve_opts` 에 `modifiers` 화이트리스트 파싱 추가(chair_template 은 이미 파싱).

### D5. 카피 규칙 (사용자 지적: 불분명한 메시지가 최대 혼동원)
- 상황=헤드라인 / 산출=결과 문서 / 애매동사 금지. checklist.md 하단 참조. decision-table.md 에 절로 못박음.

## 진행 (2026-08-29)
- **A·B 완료·커밋.** 계약(routes.py DelibOpts chair_template·modifiers) + 엔진 두 곳.
  - HWAXAgentServer c510300 (deliberation.py), HWAXPortal daf3628 (hwax-deliberate.js·routes.py).
- **build-plan PY 부재 발견.** 착수 시 PY `_CHAIR_ITEMS` 는 4종(default·mechanism·sim-plan·test-plan)뿐,
  build-plan 이 없어 heading 맵만 build-plan 을 참조하던 선존 불일치. JS 텍스트를 충실 미러해 8종으로 맞춤.
- **파리티 검증.** diagnosis/option-select/credibility 3종이 JS↔PY 정규화 후 바이트 일치(706/624/678).
  modifier 필터(중복제거·화이트리스트·cap5)·`_modifier_note`(헤더·드롭·빈값) 실코드 고립 실행 통과.
- **검증 로그.** py_compile(deliberation·routes) OK · node --check(3 JS) OK · AST 키수 8+5 OK.

## 깊이 보강 (2026-08-29, 후속)
- **지정 좌석(좌석 레벨 강제).** 신규 3 Job 에 합성 반대/반증 좌석 자동 주입 — credibility=red-team
  (delib-redteam)·diagnosis=반증(delib-disconfirm)·option-select=반대(delib-contrarian). 프롬프트 지시만으론
  그 역할석이 발굴 안 되면 아무도 안 맡던 문제를 좌석 구조로 못박음. 좌석 시스템 프롬프트가 role 을 쓰므로
  (deliberation.py:862/1278, JS role(k)) 합성 role 이 그대로 반영. RAG 는 합성 키에 빈값(try/except 안전).
  두 엔진 역할 바이트 정합(167/144/130). 커밋 HWAXAgentServer 5386f2d · HWAXPortal 43a5ef7.
- **anon1r 구조화.** 1R 은 좌석 간 이미 병렬 독립(서로 못 봄)이라, 남은 구조적 레버는 이어하기에서 기존
  좌석도 1R 엔 이전 결론을 가리는 것. PY `_has_blind`·prompt_fn, JS `baseFor` 에 ANON1R 추가. fresh 심의는
  프롬프트 지시가 이미 하는 일을 강화만.
- **미결(정직).** ExpertAgents 다운·WIP 카드로 도메인 고정 좌석(rel-fa 등 실 레지스트리 키)은 미배선 —
  지정 좌석은 역할 정의 합성석만. 라이브 e2e 는 vLLM 복구 후.

## UX 그룹화 + 배선 정리 (2026-08-29, 후속)
- **Job 그룹화.** 7개 평면 그리드가 산만하다는 피드백 → 산출물 성격으로 3·3·1 묶음(판단=규명/선택/판정,
  계획=해석/시험/구축, 자유 전폭). group·JOB_GROUPS·jobsByGroup 을 delibTaxonomy 에. 두 화면 동일 적용.
- **하드코딩 제거·통일.** JOB_ROUTING·note·placeholder 를 컴포넌트에서 택소노미로 이관.
- **sim/test 라우팅 통일(품질 결함 수정).** 브리프도 sim/test 를 다단 트리거(/시뮬심의·/시험계획)로 보내
  고정 좌석·2단 파이프라인을 타게 함(run_sim_deliberation/run_test_plan 이 _resolve_opts→_deliberation_stream
  경유라 evidence·modifiers 승계). 종전 단발 sim-plan 품질 저하 제거. startHandoff 에 trigger 추가.
- **디테일.** job별 예시(판단 그룹)·placeholder·note 힌트, 브리프 시작 버튼에 방법·얹을 층 수 표시.
- 커밋 a68a2c2(그룹·라우팅)·9ee1921(폴리시).

## 열린 질문 / 유보
- diagnosis 의 대표 좌석 로스터(rel-fa·품질·공정·SW)와 option-select/credibility 좌석 힌트는
  decision-table.md 에 초안, 실제 recommend_agents 연동은 후속.
- Modifier 주입 위치(BASE 전역 vs 좌석별)는 엔진 구현 때 확정 — 우선 BASE 전역 프리픽스로.
