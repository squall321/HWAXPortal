# [요청] 결로 자동화 — StepForge 형상 → STE 결로 해석 (통합본, 초안 · 미발송)

- 날짜: 2026-11-17
- 받을 곳: STE(결로 실행기 · 후처리) · StepForge · HWAX 포탈·게이트웨이 · 브리지(STE ↔ StepForge 연계 컨테이너)
- 배경: 디지털워커가 HWAX MCP 도구만으로 "StepForge 과제 → 공기 공동 → 개구부 → 결로 해석 → 결과 읽기" 를 돌려 보았다. 결로 1건(잡 `3aeefbd78706`, 휴대폰 크기 공기 상자)은 30 s 에 돌았다. 그러나 공동 형상은 StepForge 에서 받지 못했고, 개구부 · 환경 값 · STE 이동 · 결과 수치 · 판정은 사람이 정하거나 셸로 돌아가야 했다.
- 근거: `condensation/RUNLOG.md`(시험 기록), `condensation/FUNCTIONS.md`(함수 목록). 항목 끝 괄호의 #번호는 FUNCTIONS.md 번호다.
- 이 파일이 앞서 나눠 쓴 요청서 4건(STE · STEPFORGE · PORTAL · BRIDGE)을 모두 담는다.

## 한눈에

| 우선 | 번호 | 받을 곳 | 요청 |
|---|---|---|---|
| **P0** | F-1 | StepForge | `cavity_openings` — 공동의 개구부(중심 · 넓이 · 법선 · 바깥과 이어지나) + 공기 안 점 |
| **P0** | F-2 · P-1 | StepForge + 포탈 | `artifact_to_ste_upload` — 산출물을 STE 업로드 스테이징으로 바로 옮긴다 |
| **P0** | S-1 | STE | 개구부를 "구멍 영역" 패치로 만든다 |
| **P0** | S-2 | STE | 개구부 미매칭이면 결로 단계 실패 · 잡 실패 |
| P1 | S-3 | STE | `ste_job_summary` — 정리된 수치 |
| P1 | S-4 | STE | 후처리 단위 · 자릿수 |
| P1 | S-5 | STE | `condensation_scenario_build` — 검사를 거친 시나리오 |
| P1 | S-6 · B-1 | STE + 브리지 | part-study 단계 고르기 · STL m 출력 |
| P1 | S-7 | STE | 결로 판정 기준 · 판정 |
| P1 | F-3 | StepForge | `cold_surface_from_parts` — 차가운 면 |
| P1 | F-4 | StepForge | `enclosure_candidates` — 외피 후보 |
| P1 | F-8 | StepForge | `leak_report` 제안값과 `build_cavity` 검출 범위 맞추기 · 제출 때 검사 |
| P1 | P-2 | 포탈 | 시험 조건 → 환경 값 |
| P2 | S-8 | STE | `get_job_file` 앞부분 · 범위 |
| P2 | S-9 | STE | 장시간 결로 모드 |
| P2 | F-5 | StepForge | 잡 대기 정보 · 짧은 잡 줄 |
| P2 | F-6 | StepForge | `leak_report` 넓은 창 |
| P2 | F-7 | StepForge | 산출물 경로 표시 |
| P2 | P-3 | 포탈 | 운영본 표시 |
| 선택 | B-2 | 브리지 | 공동 솔리드 STL 확인 |

확인 순서 제안: S-2 → S-1(실패를 먼저 드러낸 뒤 매칭을 고친다) · F-1 · F-2/P-1(사람 손이 가장 많이 든 곳) · S-4 단위 확인(맞으면 바로 수정) · S-3(레디쉬 요청과 함께) · F-8.

---

## 1. STE — 결로 실행 · 개구부 패치 · 실패 판정 · 결과 요약

### S-1. 개구부를 "구멍 영역" 패치로 만든다 (P0 · #3)
- 지금: `auto_patch_stl.py` 가 STL 면을 **법선 방향만으로**(30°) 묶고, 개구부 `center` 에서 반경 안의 가장 가까운 묶음 중심을 그 역할로 준다. 그래서 개구부가 "그 방향을 보는 면 전체" 가 된다.
- 재현: 잡 `3aeefbd78706`. 반경 4 mm(약 50 mm²)로 준 입구가 **408 mm²**(아래 면 전체) 패치가 됐다(`postProcessing/fluxes_at_openings/0/surfaceFieldValue.dat` 머리: Faces 235, Area 4.08e-4).
- 바라는 것: `openings[{center, radius 또는 area_m2, normal?}]` 이면, 그 원(또는 F-1 이 넘긴 영역) 안의 면만 잘라 새 패치로 만든다. 위치와 연결성으로 고른다. 만든 패치의 넓이 · 면 수를 결과에 남긴다.

### S-2. 개구부 미매칭이면 결로 단계 실패, 잡 실패 (P0 · #4)
- 지금: 맞는 묶음이 없으면 아무 말 없이 wall 로 남고, 잡은 COMPLETED/exit 0 이다. 11-17 스모크 1차는 개구부 0개가 붙었는데도 보고서에 "결로 O" 가 찍혔다.
- 바라는 것: 개구부가 하나라도 안 붙거나 입구 / 출구 중 하나가 없거나 입출 유량 차가 한계(예: 5 %)를 넘으면, 결로 단계 `fail` + 잡 `FAILED` + `failed_stage:"condensation"` + `reason_code`(`opening_unmatched` · `no_outlet` · `flux_imbalance`).
- 레디쉬 쪽 요청 "단계 실패 = 잡 실패" 와 같은 규칙으로 묶어 주면 좋다.

### S-3. `ste_job_summary` (P1 · #5)
- `job_id` → `{app, state, failed_stage, stages[], openings:[{id, patch, distance_m, area_m2, faces, flow_L_s}], metrics:{flow_in_L_s, flow_out_L_s, mass_in_g_s, flux_balance_pct, ach_per_h, y_h2o_in, y_h2o_out, removal_pct, t_avg_C, dew_avg_C, condensed_mg, rate_mg_s, onset_s, patch_area_pct}, verdict, report_url, case_digest}`.
- 레디쉬 요청과 **같은 이름 · 같은 꼴**(앱별 metrics 만 다름).
- 지금은 한글 보고서(`report.txt`) 문자열에서 숫자를 뽑아야 하고, 패치 넓이는 `.dat` 머리 주석에만 있다. 어떤 개구부가 어떤 패치에 붙었는지(거리 포함)는 어디에도 없다.

### S-4. 후처리 단위 · 자릿수 (P1 · #6)
- 유량 단위(확인 요청): 잡 `3aeefbd78706` 에서 입구 sum(phi) = 2.3157e-4, 유속 × 넓이 = 0.5 × 4.08e-4 = 2.04e-4 m³/s. 비가 **1.135**(공기 밀도와 같음)라 phi 가 질량유량(kg/s)으로 보인다. 그런데 보고서는 이를 "부피유량 0.232 L/s" 로 찍고, "질량유량" 은 밀도 1.2 를 또 곱해 0.278 g/s 로 찍는다. 스모크(`bee9c9d167ad`)도 같은 비(272.4 L/s ÷ 240 L/s)다. 맞다면 부피유량 +13.5 %, 질량유량 +20 %, ACH 도 같이 부풀려진다.
- 작은 값: 휴대폰 크기에서 "Volume : 0.000 m³"(실제 5.96e-5), "누적 응축량 0.000 g"(응축률 0.27 mg/s × 0.5 s ≈ 0.14 mg)로 찍힌다. cm³ · mg 로도 찍어 주면 좋다.
- 로그의 메시 셀 수가 "cells: unknown" 이다(snappyHexMesh 로그에는 23,500).

### S-5. `condensation_scenario_build` (P1 · #7)
- 입력: 공동 STL(또는 산출물 참조), 개구부 목록, 차가운 파트 또는 `cold_zone`, 환경 값, 해석 시간.
- 출력: 검사를 거친 scenario.json + `placeholders:[…]`(예제 값으로 남은 칸).
- 검사: 개구부 좌표가 m 이고 STL 상자 안인지 · `location_in_mesh` 가 공기 안인지(지금 기본값은 STL 상자 중심이라 고체 안일 수 있다) · `cold_zone` 이 패치 하나 이상에 걸리는지. 스모크 시나리오 주석은 "두 면" 인데 실제로는 한 면만 cold_wall 이 됐다.

### S-6. part-study 단계 고르기 (P1 · #8)
- `stages=["stl","condensation"]` 로 outline · reddish 를 건너뛰게 한다. 공기 공동 솔리드에는 레디쉬가 뜻이 없다.
- 개구부 좌표는 m 로 넣고 STL 은 mm 로 만든 뒤 줄이는 지금 방식은 단위가 섞인다. 4장 B-1(STL m 출력)과 함께 본다.

### S-7. 결로 판정 기준 · 판정 (P1 · #11)
- 시나리오 `criteria`(예: 누적 응축량 상한 mg, 지정 파트 면의 결로 면적 % 상한) → 결과 `verdict {pass, metric, value, limit, reason_code}`.
- 지금은 "결로 발생 조건" 문장과 면적 % 만 있다(잡 `3aeefbd78706`: 차가운 벽 100 %).

### S-8. `get_job_file` 앞부분 · 범위 (P2 · #16)
- `head_lines` 또는 `offset`. 지금은 꼬리만 줘서 `system/controlDict` 앞쪽(시간 · Courant 설정)을 MCP 로 못 읽었다.

### S-9. 장시간 결로 모드 (P2 · #18)
- 결로 시험은 시간 ~ 일 단위인데 지금 해석은 초 단위 비정상 흐름이다. 준정상 또는 들숨날숨(온도 변화로 공기가 드나듦) 모드가 있으면 시험 조건과 바로 견줄 수 있다.

---

## 2. StepForge — 공동 개구부 · 산출물 STE 이동 · 차가운 면

### F-1. `cavity_openings` (P0 · #1)
- 입력: `project_id`, 공동 산출물 `ref`(또는 `container`).
- 출력: `openings:[{id, center_mm, normal, area_mm2, kind: hole/gap, via:{part 또는 [part_a, part_b]}, connects_outside: bool}]`, `inside_point_mm`(공기 안 점), `units:"mm"`.
- 지금:
  - `leak_report` 는 `{a, b, a_path, b_path, gap}` 만 준다. 위치 · 넓이 · 법선이 없고, 그 틈이 바깥 공기와 이어지는지도 모른다. 과제 B(598 파트 세트) 상위 틈은 대부분 안쪽 틈(부품 ↔ 프레임, 접착층 ↔ 표시부)이었다.
  - `describe_part(프레임, features=true)` 는 구멍 0 · 슬롯 끝 30 · 필렛 1,395 · 모따기 1,517 이다. 단자 · 스피커 · 마이크 구멍이 구멍 피처로 잡히지 않는다.
- 결로 해석은 개구부 좌표 · 넓이 · 역할이 없으면 시작할 수 없다. 공기 안 점도 함께 주면 메시 시작점 문제(해석기 기본값 = 상자 중심)가 같이 풀린다.

### F-2. `artifact_to_ste_upload` — 산출물 쪽 (P0 · #2)
- 입력: `project_id`, 산출물 `ref`(cavity_step · stl · worked_step …).
- 출력: STE 업로드 스테이징의 `upload_id` + `{filename, bytes, sha256}`. 바이트가 모델을 지나지 않는다.
- 지금: MCP 받기(`download_artifact`)는 약 1 MB 상한이다. 운영 StepForge 데이터는 노드 로컬 디스크라 STE 계산 노드에서 보이지 않는다. 남는 길은 셸로 노드에서 꺼내 중계 서버를 거쳐 올리는 것뿐이다.
- 레디쉬 쪽 `export_part_step(to_ste_upload=true)` 와 **같은 함수**로 묶어 주면 좋다. 스테이징 쪽은 3장 P-1.

### F-3. `cold_surface_from_parts` (P1 · #9)
- 입력: `project_id`, 공동 `ref`, 파트(이름 · 역할, 예: 후면 유리).
- 출력: 그 파트와 닿은 공동 면 목록 · 상자(결로 시나리오 `cold_zone` 에 그대로 쓸 수 있는 꼴).
- 지금: 차가운 벽을 "뒷면 전체" 로 손으로 정했다. 파트의 상자는 있지만 역할이 비어 있고(`role` null), 공동 면 ↔ 파트 대응이 없다.

### F-4. `enclosure_candidates` (P1 · #12)
- 입력: `project_id` → 공기를 가두는 외피 후보 파트(프레임 · 앞뒤 유리 · 커버)와 닫힘 추정 · 내부 부피 어림.
- 지금: 33과제가 모두 세트 조립이라, 외피 파트를 이름 글롭과 부피로 사람이 골랐다.

### F-8. `leak_report` 제안값과 `build_cavity` 검출 범위 맞추기 · 제출 때 검사 (P1 · #19)
- 지금: 과제 B 에서 `leak_report(max_gap=0.5)` 가 `suggested_seal_gaps` **0.525** 를 줬다(가장 큰 틈 0.5 가 창 상한에 닿음). 그 값으로 낸 `build_cavity(hull, seal_gaps=0.525)` 는 **113.8 분 대기 뒤 시작해 155 s 만에 실패**했다 — `GapScanStop`: 검출 표가 0.5 mm 까지만 담아 캐시를 버리고 직접 쟀고, 후보 4,113쌍 · 면쌍 1.59 억(예산 30만의 528.7 배)이었다.
- 바라는 것:
  - 제안값이 검출 표 범위를 넘으면 그 사실과 "범위 안 값(0.5)" 또는 "재검출 필요" 를 함께 준다.
  - `build_cavity` 가 **제출할 때** 같은 조건(seal_gaps > 검출 범위이고 직접 재기 예산 초과)을 미리 가려 바로 돌려준다. 지금은 줄을 다 선 뒤에야 실패를 안다.

### F-5. 잡 대기 정보 · 짧은 잡 줄 (P2 · #13)
- `job_status` 에 대기 순번 · 앞 잡 수 · 예상 시작을 실어 준다.
- 산출물만 만드는 짧은 잡(`build_cavity` · `export_step`)과 긴 검출 잡의 줄을 나눈다. 이번 시험에서 공동 잡은 동시 잡 2 개 한도에 막혀 113.8 분을 기다렸다(그동안 응답에 순번 · 예상 시작이 없었다).

### F-6. `leak_report` 넓은 창 (P2 · #14)
- 0.5 mm 를 넘는 틈을 재검출 없이 예산 안에서 잰다(예: 후보를 외피 파트로 좁히는 `parts=`).
- 지금: 2 mm 창은 면쌍 1.79 억(예산 30만의 598 배)으로 멈췄고, 검출 표는 0.5 mm 까지만 있다.

### F-7. 산출물 경로 표시 (P2 · #17)
- `list_artifacts` 의 `path` 에 "노드 로컬" 을 표시하거나 뺀다. `/data/…` 꼴이라 STE 공유 폴더로 착각하기 쉽다.

---

## 3. HWAX 포탈·게이트웨이 — 산출물 스테이징 · 시험 조건 · 운영본 표시

### P-1. `artifact_to_ste_upload` — 스테이징 쪽 (P0 · #2)
- StepForge 산출물을 게이트웨이 안에서 STE 업로드 스테이징으로 바로 옮기고 `upload_id` 만 돌려준다. 바이트와 업로드 티켓이 모델 · 인자 · 파일에 남지 않게 한다.
- 지금: MCP 받기는 약 1 MB 상한이고, 공유 경로가 없다. 남는 길은 셸 우회(노드 → 중계 서버 → `curl -K -`)뿐이다.
- 2장 F-2 와 레디쉬 쪽 `export_part_step(to_ste_upload=true)` 가 같은 길을 쓴다.

### P-2. 시험 조건 → 환경 값 (P1 · #10)
- 신뢰성 시험 id → `{outdoor_T_C, outdoor_rh, indoor_T_C, indoor_rh, cold_wall_T_C, hours}`.
- 레디쉬 요청의 같은 함수에 결로 칸(차가운 벽 온도 · 실내 초기 값)을 더한 꼴이다.
- 개인 토큰이 없으면 등록 안내와 함께 "공용 프리셋으로 대신 받을지" 를 묻는다(레디쉬 시험에서 개인 토큰 미등록으로 막힘).
- 지금: 결로 환경 값은 모두 스모크 예제 값(외기 25 °C · 80 %, 실내 15 °C · 30 %, 차가운 벽 8 °C)이다.

### P-3. 운영본 표시 (P2 · #15)
- `list_tool_apps` 줄에 `instance`(운영 / 동결) · build 를 싣는다.
- 지금: 어느 도구 이름이 운영본인지 목록만으로 알 수 없어 `system_capabilities` 를 따로 불러 확인했다. 레디쉬 요청과 같다.

---

## 4. 브리지 — 결로용 STL 단위

### B-1. `stl --units m` 선택 (P1 · #8)
- part-study 의 stl 단계는 STL 을 mm 로 만들고 결로 단계에서 m 로 줄인다. 그런데 결로 시나리오의 개구부 · 차가운 영역 좌표는 처음부터 m 로 넣어야 한다. 디지털워커가 StepForge 좌표(mm)를 옮길 때 단위가 섞인다.
- STL 을 m 로 바로 내는 선택을 연다. `stl.json` 에 `units` 칸을 싣는다.
- 1장 S-6(`stages=["stl","condensation"]`)과 함께 쓰면, 공동 STEP 하나로 결로만 돌릴 수 있다.

### B-2. 공동 솔리드 STL 확인 (선택)
- `build_cavity` 가 내는 공동 솔리드는 면 수가 많고 얇은 틈이 있다. 지금 `--max-open-edges` 기본 200 으로 통과하는지 확인을 부탁한다.
