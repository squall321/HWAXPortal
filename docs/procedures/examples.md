# 정본 예제 절차 넷

절차 기능이 무엇을 하는 물건인지는 이 넷이 정한다. 계획은 [PLAN.md](PLAN.md), 단계는
[checklist.md](checklist.md).

| # | 절차 | 어디서 도나 | 무엇을 처음 증명하나 |
|---|---|---|---|
| **R1** | [적층 굴곡 수명](#r1) | **dev 완주** | 직선 체인이 끝까지 가고, **형상이 변수를 채운다** |
| **R2a** | [전각도 낙하 · 제출](#r2) | dev 는 `dry_run` 까지 | 잡 제출을 사람 확인 아래 둔다 |
| **R2b** | [낙하·충격 · 회수](#r2b) | cae00 | 제출과 회수가 **다른 절차**다 |
| **R3** | [열충격 SED](#r3) | **cae00 전용** | 공급자 없는 값이 사람이 채우는 칸으로 내려간다 |

R2 는 `sim_type` 만 바꾸면 **전위치 부분충격**이 된다 — 같은 절차 두 판본이다.

> 2026-09-14 게이트웨이 465종 실측과 소스 대조로 썼다. 확인 못 한 자리는 그 자리에
> **⚠ 미확인** 으로 적었다. 반환 모양을 안 본 도구는 `save` 경로가 가정이다.

---

<a id="r1"></a>
## R1 — 적층 굴곡 수명 (dev 완주)

부품을 고르면 그 두께·소재로 적층을 세우고, **굽힘반경을 지정해** 층별 응력과 피로 수명을
내고, 유불리를 판정한다.

### 왜 이것이 첫 실전 예제인가

`solve_prescribed_curvature` 도구 설명이 직접 말한다.

> *"다른 도구는 전부 힘 제어(N/M)라 **에이전트가 M = D·κ 지름길을 쓰게 되는데, 비대칭 스택에서
> 실측 +244.8% 과대**다. 이 도구는 K[ε⁰;κ]=[N;M] 를 지정/미지 자유도로 분할해 정확히 푼다."*

LLM 이 스스로 엮으면 2.4배 틀린다. **절차로 굳히면 안 틀린다.** 절차 기능의 존재 이유가 이
한 문장에 있다.

### 절차

정본 씨앗은 [`fixtures/laminate-bend-life.yaml`](fixtures/laminate-bend-life.yaml) 이고,
`backend/tests/test_procedures_r1.py` 가 그 파일을 읽어 검증한다 — **`save` 경로가 실제
게이트웨이 응답에서 풀리는지까지** 본다(고정물은 2026-09-14 실호출 응답이다).

```yaml
vars:  project_id · part · r_unfold · bend_axis · width_mode · laminate
steps:
  ① bend_profile            [heax-step_forge]           ← ★형상이 R·두께·폭을 준다
       save: r_designed = parts[0].for_bending_analysis.bend_radius_mm
             t_part      = …thickness_mm      w_part = …width_mm
             bend_basis  = parts[0].primary.basis
  ② analyze_laminate        [heax-laminate_analyzer_mcp]
  ③ solve_prescribed_curvature  bend_radius = {{r_designed}}   ← 설계된 굽힘
       save: loads_bent = data.equivalent_loads
  ④ solve_prescribed_curvature  bend_radius = {{r_unfold}}     ← 펼친 상태
       save: loads_flat = data.equivalent_loads
  ⑤ recover_ply_stresses    loads = {{loads_bent}}
       save: tsai_wu_r = data.first_ply_failure.tsai_wu_R
  ⑥ estimate_fatigue_life   loads_max = {{loads_bent}}, loads_min = {{loads_flat}}
       save: life_cycles = data.life_cycles
  ⑦ create_report_draft     [reportarchive]  gate: human
```

### ⚠ 응답은 봉투다 — `save` 경로가 `data.` 아래다

적층 해석기는 `{status, data, errors, warnings, assumptions, metadata}` 로 답한다(실측).
**이 문서의 앞 판은 경로를 전부 최상위로 적어 놨고, 그대로 짰으면 첫 실행에서 죽었다.**
회귀가 그것을 잡았다.

| 값 | 틀린 경로(앞 판) | 실물 |
|---|---|---|
| 등가하중 | `equivalent_loads` | **`data.equivalent_loads`** |
| 파손 여유 | `min_tsai_wu_R` | **`data.first_ply_failure.tsai_wu_R`** |
| 수명 | `life_cycles` | **`data.life_cycles`** |
| 경고 | — | **최상위 `warnings[]`**(`data` 밖이다) |

실패도 `{status:"error", data:null, errors:[{code:"E102"…}]}` 로 오고 **`isError` 는 false** 다
— §5-6 판정이 `errors` 와 `status` 로 잡는다.

### 굽힘반경이 사람이 채우는 칸이 아니게 됐다

앞 판은 `r_min`·`r_max` 를 둘 다 사람에게 물었다. **형상이 답을 갖고 있었다** —
굽힘부 안팎 곡면의 반경 차이가 두께이고 평균이 중립면 반경이다(StepForge D-287).
해석 원통이 없어도 **주곡률 방향이 축을, 곡률 중심이 짝짓기를** 해 준다(D-288) —
변환기를 거친 실무 STEP 이 그 경우다.

U자 판(t 1.2 · R 6.0 · 폭 40 · 180°)으로 두 경로 다 실측했다 — 오차 0, NURBS 변환본도 같다.

### 끊기는 자리 — 사람이 채운다

| 자리 | 왜 — 전부 실호출로 확인했다 |
|---|---|
| ~~R_min~~ | **해결됐다** — `bend_profile` 이 형상에서 준다(D-287·D-288). 남은 것은 `r_unfold`(얼마나 펴지는가)뿐이고 그건 쓰임새가 정하지 형상에 없다 |
| **`width_mode`** | 실제 지그가 자유 폭인지 구속 폭인지는 형상에 없다. 답이 9.6% 갈리고 도구가 W130 으로 경고한다 |
| **`laminate` 전체** | `material_lookup("CFRP")` 실호출 → `{RHO:2e-9, E:69000, PR:0.33}` + `*MAT_ELASTIC` — **등방**이다. E1/E2/G12/nu12 도 강도도 없고 값 자체도 라미나로 못 쓴다. `resolve_materials` 는 파트↔재질 **이름** 매핑만 본다. **자동 변환기가 없다** |
| **`strength` · `fatigue`** | `derive_lamina_from_constituents` 는 **강성만** 낸다(`{type,E1,E2,G12,nu12,rho}`). `strength{Xt,Xc,Yt,Yc,S}`·`fatigue{model_type,k\|b}` 는 **어느 도구도 안 준다** |

→ 넷 다 §5-1 대로 **변수로 내려간다.** 절차는 그대로 돌고 사람이 채우는 칸만 있다.

### 함정

- **`estimate_fatigue_life` 는 물성 없는 ply 를 조용히 제외한다.** 설명 원문 — *"strength/fatigue
  없는 ply는 제외되며 **W120으로 알린다(임계 ply가 빠지면 과대평가)**"*. 결과는 정상으로 오고
  경고만 뜬다. **W120 을 실행 기록 `notes` 로 반드시 올린다**(PLAN §2 실행).
- ⚠ **MaterialTwin 의 피로 지수를 그대로 옮기면 틀린다.** `mechanical.fatigue_strength_exponent`
  는 128건 있지만 basis 가 *"MAXIMUM applied stress vs cycles Nf (NOT amplitude, NOT reversals)"*
  이고, 적층 쪽 basquin 은 `r_ar = N^(−b)` 로 **교번(진폭) 강도비** 기준이다. 규약이 다른데
  숫자는 둘 다 그럴듯하게 들어간다 — **조용한 오답**이다.
- **이름 함정** — `list_composites`·`get_composite` 는 적층 재료와 **무관하다.** ReportArchive 의
  **종합보고**(주간·월간 보고서 묶음)다. 적층 재료를 카탈로그에서 고르는 경로는 **없고**
  `laminae[].material` 에 직접 넣는다.
- `laminate` 는 스키마가 `additionalProperties: true` 인 빈 object 다 — 465종 중 44종의 그 부류다.
  **필수 필드가 스키마가 아니라 description 산문에 있다.** 인자 화면은 원문 JSON 2단(PLAN §2).
- `unit_system` 은 `"SI"` 또는 `"SI_mm"` 다. 섞으면 조용히 틀린다. `bend_radius` 의 길이 단위가
  거기 묶인다.
- ⚠ **`mesh_size_advice` 는 `store: true` 가 기본**이라 파트 메타·규칙 YAML 을 쓴다. 조회로 쓰려면
  반드시 `store: false` — 절차에 넣는다면 저장 시점에 그것을 강제한다.
- ⚠ **MaterialTwin 카탈로그 검색이 세션 첫 호출에 120.3초 걸린다**(3회 재현, 두 번째부터 0.1초).
  게이트웨이 상한이 120초라 **첫 호출이 잘린다.** 이 절차는 그 도구를 쓰지 않지만, 쓰는
  절차는 워밍업 한 번을 앞에 두거나 상한을 올려야 한다.
- 적층 백엔드는 `gateway_config.json` 정적 목록이 아니라 **HEAXHub 레지스트리 자동발견**이다 —
  레지스트리가 떠 있어야 도구가 보인다.

### R 스윕은 반복이 아니라 S5 다

R_min 과 R_max 의 유불리 비교는 조건 분기가 아니라 **같은 절차 × `bend_radius` N개 = 비교표**
다. v1 에 반복이 없는 것이 제약이 아니라, 일괄 재생(S5)의 **첫 실사용례**다.

---

<a id="r2"></a>
## R2a — 전각도 낙하 · 제출 (dev 는 `dry_run` 까지)

### 먼저 — 사용자 전제 한 곳을 정정한다

**DynaForge 는 scenario.json 을 만들지 않는다.** `list_operations` 47개를 전수로 확인했고
scenario·drop·impact 계열 오퍼레이션이 없다(analysis·bc·core·deform·inspect·material·mesh 뿐).
실제 흐름은 이렇다.

```
DynaForge   세션에서 모델(.k) 준비·전처리 → save_result_to_path 로 공유 FS 에 내린다
   ↓
클러스터    smarttwin_submit 이 /data/scenario/<preset>/scenario.json 을 base 로
            scenario_overrides 를 deep-merge 해 scenario.json 을 **조립**하고 제출한다
   ↓
DynaForge   결과 리포트 + attach_report_scenario 로 scenario.json 이 **되돌아온다**
```

조립 주체만 다르고 사용자가 원한 그림은 그대로 선다.

### scenario.json 은 두 종류다 — 이게 사고의 근원

| | 전각도 낙하 | 전위치 부분충격 |
|---|---|---|
| 디스패치 | `mode` 키 **없음** | `"mode": "drop_weight_impact"` (최상위) |
| DOE | `scenarios[0].angle_source.source_type` | `simulation_params.locations.mode` |
| 모델 지정 | `scenarios[0].template` = `"%INPUTFILE%"` | `model_file` (최상위) |
| 배열 | `scenarios[]` 있음 | **없음 — 평탄** |

파서(`KooChainRun cmd_prepare`)는 최상위 `.get("mode")` **한 줄로 디스패치하고 스키마 검증이
없다.** 전각도 scenario 에 `mode` 가 섞이면 **조용히 부분충격으로 오실행된다** — 템플릿 주석에
실제 사고번호 `799` 가 적혀 있고 그 잡 디렉터리가 아직 남아 있다.

### 절차

```yaml
id: fullangle-drop-submit
version: 1
title: 전각도 낙하 — 제출
vars:
  - {key: session_id,  label: "DynaForge 세션 ID", type: string, required: true}
  - {key: file_id,     label: "모델 파일 ID(세션 안)", type: string, required: true}
  - {key: model_path,  label: "공유 FS 절대경로(.k)", type: string, required: true,
     why: "클러스터 헤드노드가 보는 경로다. 클라이언트 로컬 경로는 거부된다"}
  - {key: job_name,    label: "잡 이름", type: string, required: true,
     why: "결과 폴더명에 들어간다 — /data/single/<사용자>/<잡이름>_<잡ID>/"}
  - {key: angle_preset, label: "각도 프리셋", type: enum, required: true,
     values: [26direction, 6face, fibonacci-100, fibonacci-1000, fibonacci-10000]}
  - {key: drop_height_mm, label: "낙하 높이 (mm)", type: number, required: true}
  - {key: dry_run,     label: "미리보기만", type: boolean, required: true,
     why: "true 면 최종 scenario.json 과 스크립트만 본다. 실제 제출은 false 를 명시해야 한다"}
steps:
  - backend: heax-kooremapper_mcp       # ① 세션 산출물을 공유 FS 로
    tool: save_result_to_path
    gate: human
    args: {session_id: "{{session_id}}", file_id: "{{file_id}}", dest_path: "{{model_path}}"}
  - backend: smart-twin-cluster         # ② 옵션 카탈로그 — 단위계·프리셋 확인
    tool: smarttwin_scenario_options
    args: {sim_type: "fullangle_drop"}
    raw: true                           # 반환이 JSON 이 아니라 텍스트 카탈로그다
  - backend: smart-twin-cluster         # ③ ★제출 — must-gate
    tool: smarttwin_submit
    gate: human
    args: {sim_type: "fullangle_drop", model_path: "{{model_path}}",
           job_name: "{{job_name}}", angle_preset: "{{angle_preset}}",
           scenario_overrides: {simulation_params: {height: "{{drop_height_mm}}"}},
           dry_run: "{{dry_run}}"}
    save: {job_id: "job_id"}            # ⚠ 미확인 — 제출계라 부르지 않았다
```

**부분충격은 `sim_type: "partial_impact"` 로 바꾼 판본이다.** 다만 `angle_preset` 대신
`scenario_overrides.simulation_params.locations`(`grid`·`list`·`lhs`·`part_center`)와
`impactor`(`Sphere`·`Cylinder`, `radius`, `height`=낙하높이)를 준다.

### 함정 — 전부 실측·소스 확인

| 함정 | 무슨 일이 나나 |
|---|---|
| **단위계가 실제로 섞여 있다** | 카탈로그는 tonne·mm·s·MPa 가 표준이라는데 **프리셋 `26direction` 은 SI**(density 7850, youngs 2e11)이고 부분충격 실제 잡은 tonne-mm(7.85e-9, 2.0e5)이다. `scenario_overrides` 로 물성을 주면 **무변환 기입**된다 — base 가 어느 단위계인지 사람이 본다 |
| **`generation_mode` 오타** | 조용히 기본값(`DampingSpring`) 처리. 다른 해석이 돌고 에러가 없다 |
| **`mode` 키 오배선** | 사고 `799`. 템플릿이 지금은 역방향 가드로 막지만 scenario 를 손으로 만들면 여전하다 |
| **도구 설명문이 낡았다** | `fullangle_drop_simulation` 이 `slurm_job_ids` N개를 준다고 적혀 있는데 레지스트리 실측은 **1개**(드라이버)다. v1.0.0 때 동작이고 지금은 backend 경유다 — `schema_fp` 드리프트 검사가 필요한 이유 |
| **이름 함정 둘** | `scenario_build`·`scenario_patch`·`report_ingest` 는 전부 **발표자료 생성 앱**(`heax-web_design_agents`) 것이고 이 체인과 무관하다. 단계에 `backend` 를 같이 저장하는 이유 |

### 두 제출 갈래

| | `smarttwin_submit` [smart-twin-cluster] | `fullangle_drop_simulation` [smart-twin-mcp] |
|---|---|---|
| scenario | 프리셋 base + deep-merge | `scenario_builder` 가 자동 조립 |
| 필수 | `sim_type`, `model_path` | `work_dir`, **`lstc_license_ip`** |
| 부분충격 | **된다** | 안 된다(빌더가 없다) |

→ **절차는 `smarttwin_submit` 만 쓴다.** 두 sim_type 을 한 모양으로 덮고 라이선스 IP 를
사람에게 묻지 않는다.

---

<a id="r2b"></a>
## R2b — 낙하·충격 · 회수 (cae00)

### 왜 제출과 회수가 다른 절차인가

드라이버 잡 walltime 이 **167시간(7일)** 이다. 한 절차에 둘 수 없다. §4 의 "폴링·대기 없음,
잡을 거는 도구는 절차 밖" 결정이 여기서 값을 한다 — 제약이 아니라 **옳은 모양**이었다.

### 리포트 반입은 REST 다 — 절차 밖

```
POST <포탈오리진>/apps/kooremapper_api/api/v1/reports/intake
폼: file(필수)·kfile·scenario·kind(deep|sphere|impact)·project·dev_rev·variation·doe·focus·session_id
Bearer $KR_PAT      전송 상한 512MB(압축) / 해제 2048MB
```

`sphere_report.html` 실물이 **9.8 MB**, `impact_report.html` 이 **7.9 MB** 다. MCP
`ingest_report` 는 본문을 문자열로 나르므로 **작은 것 전용**이고 도구 설명이 직접 그렇게 말한다.
→ 절차는 `report_id` 를 **변수로 받는다.**

### 절차

```yaml
id: drop-impact-collect
version: 1
title: 낙하·충격 — 회수와 판독
vars:
  - {key: slurm_job_id, label: "Slurm 잡 ID", type: string, required: true}
  - {key: report_id,    label: "DynaForge 리포트 ID", type: string, required: true,
     why: "리포트 HTML 은 512MB 까지 REST intake 로 올린다 — MCP 로 못 나른다"}
steps:
  - backend: smart-twin-cluster       # ① 잡이 정상 종료됐나
    tool: slurm_job_results
    args: {job_id: "{{slurm_job_id}}"}
    save: {state: "state", exit_code: "exit_code"}
  - backend: heax-kooremapper_mcp     # ② 리포트 요약 — kind 가 sphere 인지 impact 인지
    tool: report_summary
    args: {report_id: "{{report_id}}"}
    save: {kind: "kind", worst: "worst"}
  - backend: heax-kooremapper_mcp     # ③ 최악 케이스 (sphere=방향 / impact=위치)
    tool: report_worst_cases
    args: {report_id: "{{report_id}}"}
    save: {worst_cases: "cases"}
  - backend: heax-kooremapper_mcp     # ④ 방향 취약도 (sphere=면/엣지/코너 / impact=F1~F6)
    tool: report_directional
    args: {report_id: "{{report_id}}"}
  - backend: heax-kooremapper_mcp     # ⑤ 파트별 최악값 + 최소 안전율
    tool: report_part_risk
    args: {report_id: "{{report_id}}"}
    save: {part_risk: "parts"}
  - backend: heax-kooremapper_mcp     # ⑥ 위험 소견
    tool: report_findings
    args: {report_id: "{{report_id}}"}
    save: {findings: "findings"}
  - backend: reportarchive            # ⑦ 보고서 초안
    tool: create_report_draft
    gate: human
    args: {…}
```

### `sphere` 와 `impact` 는 리포트 `kind` 다

`ingest_report` 가 **deep/sphere/impact 를 자동 판별**하고, 판독 도구들이 그 축으로 갈린다 —
`report_directional`(*"sphere: 면/엣지/코너, impact: F1~F6"*), `report_worst_cases`(*"sphere=최악
낙하 방향, impact=최악 충격 위치"*), `report_scatter`(**sphere 전용**). `sim_type` 과 정확히
짝이다.

| `sim_type` | 산출 | 리포트 `kind` |
|---|---|---|
| `fullangle_drop` | `output/sphere_report.html` + `.json` | `sphere` |
| `partial_impact` | `output/impact_report.html` + `.json` | `impact` |

### 함정

- **부분충격 scenario 는 리포트에 못 붙인다.** `attach_report_scenario`·intake 의 `scenario`
  필드가 `scenarios` 배열을 요구하는데 부분충격 scenario.json 은 평탄 구조다 →
  `ScenarioParseError` 로 **인제스트 전체가 실패**한다. 절차는 **impact 일 때 scenario 첨부를
  생략**한다(또는 파서를 고친다 — DynaForge 쪽 별개 일감).
- **리포트 라우팅 오배선이 실제로 났다** — 사고 `806`. DWI runner_config 에 `scenario.steps` 가
  없어 DROP 으로 흘러 sphere 로 갔다. 지금은 최상위 `mode` 검사로 막는다.
- **구버전 SIF 는 조용히 넘어간다** — `impact_report.sh` 가 `import koo_impact_report` 실패 시
  경고하고 **`exit 0`** 한다. 산출이 없는데 성공으로 보인다. 이 리포의 무음 실패 그 모양이다.
- `sphere_report.sh` 는 반대다 — 정상 종료 실행이 0이면 **`exit 1`** 로 죽는다.
- 임계 응력 키가 다르다 — sphere 는 `yield_stress_mpa`, impact 는 `postprocess.impact_yield_stress`.
  **일부러 안 겹치게 했다**(충격 덱은 단위계가 다르다).
- 과제 메타(`project`·`dev_rev`·`variation`·`doe`·`focus`)를 안 넣으면 `find_reports`·
  `report_facets` 로 **다시 못 찾는다.**

### 이 묶음이 심의 좌석에 주는 도구다

R2b 의 판독 도구가 그대로 **심의 좌석 도구 목록**이다 — 여기에 `report_query`·`report_case`·
`report_angle_stats`·`report_scatter`·`report_energy_flow`·`report_part_series`·`compare_reports`
를 더한다. 제출 계열은 좌석에서 **뺀다**(PLAN §6 심의 경계).

순서가 정해진다 — **절차 기능이 먼저 돌고(R2a → 잡 → R2b), 심의는 그 뒤에 `report_id` 를 읽는다.**
심의 중에 잡을 걸면 walltime 167시간 뒤에나 결과가 나오고 그 심의는 의도만 남은 근거가 된다.
전각도 자식 잡 26~10000개를 라운드 중간에 좌석이 모을 수도 없다.

### ⚠ dev 에서 검증 불가

`report_corpus` → `{"reports": 0, "cases": 0, "note": "해석 결과 리포트가 아직 없다."}`,
`report_facets` → 전 축 빈 배열. **②~⑥ 은 계약만 확인했고 실동작은 cae00 에서만 본다.**

---

<a id="r3"></a>
## R3 — 열충격 SED (cae00 전용)

ODB++ 에서 좌표·치수를 뽑아 SED 를 판정하고 보고서로 남긴다. ODB 쪽 계약은 S0 수집 결과를
받아야 확정된다 — [odb-request.md](odb-request.md).

```yaml
id: thermal-shock-sed
version: 1
title: 열충격 SED 판정
vars:
  - {key: odb_job,  label: "ODB 잡 ID", type: string, required: true}
  - {key: pkg_type, label: "패키지 분류", type: enum, values: [WLP, FX, DIG], required: true,
     why: "형상 데이터로 유도할 수 없는 기술 분류다"}
  - {key: ap_refdes, label: "AP refdes", type: string, required: true,
     why: "부품 목록은 수천 개를 주지 '이 보드의 AP' 를 주지 않는다. 사내 규칙이 있으면 그때 상수로 내린다"}
steps:
  - backend: odb-hub                    # ⚠ 전부 S0 수집 뒤 확정
    tool: "<S0 에서 받은 부품 목록 도구>"
    args: {job_id: "{{odb_job}}"}
    save: {ap_cx: "…", ap_cy: "…"}
  - backend: heax-thermal_shock_mcp
    tool: predict_sed
    args: {sample: {board_type: "…", ap_cx: "{{ap_cx}}", …, pkg_type: "{{pkg_type}}"}}
    save: {sed: "data.sed_pred"}
  - backend: reportarchive
    tool: create_report_draft
    gate: human
    args: {…}
  - backend: reportarchive
    tool: suggest_report_tags           # 후보만 — 저장하지 않는다
    args: {report_id: "{{report_id}}"}
  - backend: reportarchive
    tool: add_report_tags               # ★실제 저장 — must-gate
    gate: human
    args: {report_id: "{{report_id}}", entity_ids: "{{chosen_tags}}"}
```

### 함정

- `predict_sed` 의 최상위 필수 인자는 **`sample` 하나**다. 10개는 그 안이고, 평탄하게 넘기면
  `sample Field required` 로 실패한다.
- 서버가 `extra="forbid"` 다 — ODB 에서 딸려 온 키가 하나라도 섞이면 **E100 으로 통째 거부**.
  게이트웨이 스키마의 `additionalProperties: true` 는 허상이다.
- `predict_sed_batch` 는 S5 일괄 재생에 쓰지 않는다 — 검증이 전부-아니면-전무라 한 건만 틀려도
  결과 0건이고 과제별 건너뛰기가 안 된다.

---

## 넷을 가로지르는 규칙

| 규칙 | 근거 |
|---|---|
| 단계는 `backend` + `tool`(원본 이름) + `schema_fp` 로 저장한다 | 이름 함정 둘(§R2a)과 낡은 설명문 |
| enum·단위는 **저장 시점**에 검증한다 | `generation_mode` 오타·`unit_system`·단위계 혼재 — 전부 조용히 통과한다 |
| 경고는 `notes` 로 올린다 | W120(ply 제외) · 합성 데이터 경고 · `out_of_domain` |
| 잡을 거는 도구는 제출·회수 **두 절차**로 가른다 | 드라이버 walltime 167시간 |
| 파일을 나르는 단계는 절차 밖이다 | `model_path` 는 공유 FS 절대경로, 리포트는 512MB REST |
| 되돌리기 어려운 단계는 실행기가 멈춘다 | `smarttwin_submit(dry_run=false)` · `add_report_tags` · `publish_report` |
| 단계마다 `expect`(`fast`/`slow`/`job`)를 선언하고 `job` 은 저장 거절 | 게이트웨이 상한 120초 · 실측 `search_catalog_property` **120.3초**(세션 첫 호출)·`agent_search` 102~221초 |
| 콜드스타트가 상한을 넘기는 도구 앞에 `warmup: true` 단계를 둔다 | 두 번째 호출부터 0.1초다 — 한 번 버리는 호출이 제일 싼 해법 |
| **심의는 잡을 걸지 않는다** — 좌석에는 `report_*` 판독 도구만 준다 | walltime 167시간 · 자식 잡 26~10000개의 집계는 `sphere_report` 의 일이다 |
