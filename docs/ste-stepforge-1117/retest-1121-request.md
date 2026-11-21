<!-- 사용자가 2026-11-22(KST) dev 포털 세션에 붙여 넣은 요청 초안을 그대로 옮겼다(줄 사이에 낀 빈 줄만 걷었다). 운영 박스의 디지털워커가 11-21 에 다시 돌려 본 결과다. 받을 곳별 몫과 전달은 PLAN.md 「11-21 재시험」 절 · checklist.md 「전달 (11-22)」 · context-notes.md SS-9 에 있다. -->

# [요청 초안] StepForge → STE 레디쉬 · 결로 연계 — 11-21 재시험 뒤 남은 것

- 작성 2026-11-21 · 상태: **초안(보내지 않음)**
- 받을 곳: StepForge · STE · 브리지·게이트웨이(STE ↔ StepForge 연계 컨테이너와 HWAX 게이트웨이 도구) · 포털
- 배경: 디지털워커가 HWAX MCP 도구만으로 "StepForge(D-707 판) 과제 → STE 해석"을 다시 돌려 보았다. 과제 A 는 레디쉬(창 유리 판), 과제 B 는 결로(후면 유리 · 프레임)다.
  - 된 것: 파트 STEP 반출(`export_part_step`) → STE 업로드(`artifact_to_ste_upload`) → part-study 제출 → 결과 읽기. 셸 없이 끝까지 이어졌다.
  - 안 된 것: part-study 가 두 얇은 판 모두 outline 에서 멈췄다. 결로는 공동을 만들지 못했다. 레디쉬 입력(적층 · 확산 물성 · 경계 · UV 창)은 여전히 템플릿 값이다.
- 11-17 요청 가운데 파트 STEP 반출과 산출물 경로 표시는 풀렸다. 이 문서는 그 밖에 남은 항목과 새로 찾은 결함만 담는다.

## 이번 잡

| 잡 | 어디 | 무엇 | 끝 상태 |
|---|---|---|---|
| da723f9ba623 | STE part-study | 과제 A 창 유리 STEP(155,360 B) 업로드, cond 0 | COMPLETED/0 · outline fail · reddish skip |
| 608a24a0c924 | STE reddish | 템플릿 case 에 둥근 사각형 75.856×161.368 mm · r 5.835 · 구멍 0 | COMPLETED/0 · 61 s · V1 true · V2 37.76 / 34.97 mm pass null |
| 007f6a2250e4 | STE part-study | 과제 B 후면 유리 STEP(240,542 B) 업로드, cond 1 | COMPLETED/0 · outline fail · reddish skip · condensation skip |
| 1ddbdd7cd769 | STE condensation | 손으로 쓴 상자 STL, 입구 반경 4 mm, 출구는 일부러 24 mm 빗나가게 | COMPLETED/0 · 출구 없음 · 60.8 °C · 6.59 mg/s |
| 001a1fb692180c77bd53ee1 | StepForge build_cavity | 과제 B, container=후면 유리, scope region(21 파트), seal_gaps 2.0 | failed · GapScanStop(예산 180.2배) |

## 한눈에

| 우선 | 번호 | 받을 곳 | 요청 |
|---|---|---|---|
| **P0** | SF-1 | StepForge | `build_cavity` 파트 목록 인자 · 접수 때 검사 |
| **P0** | SF-2 | StepForge | `part_outline_2d` 코너가 deflection 에 따라 바뀜 · 복합 코너 · 접촉 넓이 0 |
| **P0** | SF-3 | StepForge | `cavity_openings` · `cold_surface_from_parts` 실제 공동에서 확인 · 바깥 셸 구멍 |
| **P0** | ST-1 | STE | 개구부를 구멍 영역 패치로 |
| **P0** | ST-2 | STE | 개구부 미매칭 · 출구 없음이면 잡 실패 |
| **P0** | ST-3 · BG-1 | STE + 브리지 | 레지스트리 잡이 운영 StepForge 에서 파트를 받게 |
| **P0** | BG-2 | 브리지 | outline 얇은 판 · `outline_source=stepforge` |
| **P0** | BG-3 | 게이트웨이 | `artifact_to_ste_upload` 남은 확인(큰 파일 · 공동 산출물 · 시나리오 더하기) |
| P1 | SF-4 | StepForge | `part_stack` 층 정보 출처 |
| P1 | SF-5 | StepForge (또는 STE ST-7) | 둥근 사각형 출력 ↔ 레디쉬 geometry 규약 |
| P1 | SF-6 | StepForge | `uv_mask_from_region` 실제 UV 창 출처 |
| P1 | SF-7 | StepForge | `enclosure_candidates` 앞뒤 유리 빠짐 |
| P1 | ST-4 ~ ST-11 | STE | 단계 실패 = 잡 실패 · 결과 요약 · 판정 · case/시나리오 조립 · h 기본표 · 후처리 단위 · 단계 고르기 |
| P1 | BG-4 · BG-5 · BG-6 | 게이트웨이 · 브리지 | 확산 물성 조회 보강 · 시험 조건 → 환경 값 · STL 단위 m |
| P1 | PT-1 | 포털 | 개인 토큰이 없을 때의 안내 |
| P2 | SF-8 ~ SF-12 | StepForge | 산출물 part 필터 · 응답 접기 · 역할 축 · `leak_report` 외피 3파트 · 확인만 |
| P2 | ST-12 ~ ST-17 | STE | 스키마 노출 · 수치 칸 단위 · 잡 목록 소유자 · 환경 절 · 파일 앞부분 · 장시간 모드 |
| P2 | PT-2 | 포털 | 운영본 표시 |

확인 순서 제안
1. SF-1 → SF-3: 공동이 나와야 결로 사슬이 시작된다.
2. ST-2 → ST-1: 실패를 먼저 드러낸 뒤 매칭을 고친다.
3. BG-2 · SF-2: 얇은 판에서도 형상이 넘어가게 한다.
4. ST-3 · BG-1: 레지스트리 경로를 연다.
5. ST-5 · ST-6: 숫자와 판정을 받는다.

---

## 1. StepForge

### SF-1. `build_cavity` — 파트 목록 인자 · 접수 때 검사 (P0)
- **지금**
  - 인자는 container · keep · margin · region · scope · seal_gaps 뿐이다. `job_params_guide(cavity)` 도 같다.
  - 그래서 "프레임 + 앞뒤 유리" 같은 최소 외피로 공동을 걸 수 없다. scope=region 으로 하면 후면 유리 상자와 겹치는 21 파트가 모두 들어간다.
  - 과제 B 에서 seal_gaps 2.0 으로 냈다. 검출 표는 0.5 mm 까지다. 그런데 거절되지 않고 잡 `001a1fb692180c77bd53ee1` 이 생겼다.
  - 그 잡은 대기 0.68 s + 실행 98.9 s 뒤 GapScanStop 으로 끝났다. 후보 167쌍, 면쌍 54,056,610 이다(예산 180.2배). 로그에는 '검출 캐시를 쓰지 않는다 — 표는 0.5mm 까지'가 남았다.
  - `leak_report` 는 같은 셈을 1 s 에 한다. 줄이 붐비면 이 실패를 몇 시간 기다린 뒤에야 안다(11-17 첫 공동 잡 대기 113.8 분).
- **바라는 동작**
  1. `parts=[…]`(또는 역할)로 외피 파트만 골라 공동을 만든다.
  2. 접수 때 검사한다. seal_gaps 가 검출 표 밖이고 직접 재기 예산을 넘으면 잡을 만들지 않는다. 대신 사유 · 표 범위 안 값 · 예산 배수를 바로 돌려준다.
  3. 합치기 중에는 `log_last` 에 살아 있음과 경과 시간을 싣는다. 실패하면 깨진 파트 이름을 준다.
  4. 캐시 길에서도 마개는 container 범위 안 간극으로만 고른다.
- **확인 방법**
  - 과제 B, seal_gaps 2.0 → 잡 id 없이 거절되고 사유가 나온다.
  - 과제 B, parts=[프레임, 전면 유리, 후면 유리], seal_gaps 0.5 → cavity_step 산출물 1개가 나온다.
  - 11-17 에 합치기 실패한 판 전체 조건으로 내면 → 진행 표시가 갱신되고, 실패할 때는 파트 이름이 나온다.

### SF-2. `part_outline_2d` — 코너가 deflection 에 따라 바뀜 · 복합 코너 · 접촉 넓이 0 (P0)
- **지금** (과제 A 창 유리)
  - deflection 0.1 이면 코너 R 5.835 ×4, rounded_rect r 5.835, max_dev 0.310, 변 22 가 나온다.
  - deflection 0.5 · 2.0 이면 corner_radii [] · r_mm 0 · corners 0 · max_dev 1.008 이 나온다. 원호 변도 corner 가 아니라 top/left/bottom/right 로 분류된다. 도구 설명은 "코너 반경은 원 모서리에서 읽는다"인데, 실제로는 이산화 인자에 따라 결과가 바뀐다.
  - 코너는 단일 원호가 아니다. 전이 곡선(5.15 mm) + 30° 원호(r 5.835) + 전이 곡선으로 이어지고, 접선 끝까지 8.11 mm 다. 그래서 r 하나(5.835)로 줄이면 45° 지점에서 0.31 이 어긋난다. 45° 지점 기준 등가 r 은 약 6.6 이다.
  - 변별 neighbors · partners 의 contact_mm2 · front/back_mm2 가 모두 0 이다. `part_relations` 도 프레임 접촉을 0(수동 행)으로 준다.
- **바라는 동작**
  1. 코너 · 변 분류를 deflection 과 상관없이 B-rep 모서리에서 정한다.
  2. 복합 코너는 구간 목록(종류 · 길이 · 반경)으로 준다. 둥근 사각형 근사에 쓸 등가 r 과 그 기준(45° 지점 · 접선 끝 등)은 칸으로 밝힌다.
  3. contact_mm2 를 실제 접촉 넓이로 채운다.
- **확인 방법**
  - 같은 파트를 deflection 0.1 · 0.5 · 2.0 으로 부른다. corner_radii · 변 수 · side 가 같아야 한다.
  - 코너 4곳마다 구간 목록과 등가 r 기준이 나온다.
  - 프레임과 tied 인 변의 contact_mm2 가 0 보다 크다.

### SF-3. `cavity_openings` · `cold_surface_from_parts` — 실제 공동에서 확인 · 바깥 셸 구멍 (P0 · P1)
- **지금**
  - 과제 B 에 공동이 없어서, 두 도구 모두 "공동이 없다 — build_cavity 먼저"만 돌려준다. 실제 출력은 한 번도 보지 못했다.
  - `cavity_openings` 의 holes_why 는 "한 파트 관통 구멍(kind hole)은 안 찾는다"다. 단자 · 스피커 · 마이크 같은 바깥 셸 구멍을 다루지 않는다는 뜻이다.
- **바라는 동작**
  - `cavity_openings` 는 kind gap 과 kind hole 을 둘 다 낸다. 개구부마다 center · normal · area · connects_outside 를 싣고, 공기 안 점(inside_point_mm)도 준다.
  - `cold_surface_from_parts` 는 지정한 파트와 닿은 공동 면 목록과 cold_zone 상자를 준다.
- **확인 방법**
  - SF-1 로 만든 과제 B 공동에서 개구부가 1개 이상 나오고, 줄마다 넓이 · 법선 · connects_outside 가 있다.
  - parts=[후면 유리]를 넣으면 면 목록과 cold_zone 이 나온다.

### SF-4. `part_stack` — 층 정보의 출처 (P1)
- **지금**: `part_stack`(과제 A, 창 유리)은 layers null · editions [] · "이 파트에 저장한 층 장부가 없다"를 준다. 장부는 사람이 `save_part_stack` 으로 써 넣는 것뿐이라, 과제 데이터에서 층을 얻을 길이 없다. 레디쉬 잡 608a24a0c924 도 템플릿 5층을 썼다.
- **바라는 동작**: 층마다 `{name, thickness_um, material_id}` 를 위에서 아래 순서로 준다. 장부가 비었을 때는 비었다는 사실과 함께 채우는 길을 알려 준다(쓰기는 사람 확인 뒤). material_id 는 BG-4 확산 물성 조회에 그대로 들어가야 한다.
- **확인 방법**: 사람 확인 뒤 한 번 써 넣는다. 그 뒤 `part_stack` 이 층과 material_id 를 돌려주고, 그 id 로 BG-4 조회가 된다.

### SF-5. 둥근 사각형 출력 ↔ 레디쉬 geometry 규약 (P1, STE ST-7 과 둘 중 한 곳)
- **지금**
  - `part_outline_2d` 의 rounded_rect 는 width_mm 161.368(긴 변) · axis_uv [0,1] · 중심 원점이다.
  - 레디쉬 geometry 는 width = x · 모서리 원점 · 변 4묶음이다. 잡 608a24a0c924 의 메시 상자는 [0,0,0.0759,0.1614](m, x = 짧은 변)이고, 사람이 축을 바꿔 넣은 결과다.
  - side=corner 변 묶음은 레디쉬 edge_groups 4묶음에 대응하지 않는다. UV 창 좌표도 사람이 옮겨야 한다.
- **바라는 동작**: `format=reddish_geometry` 로 레디쉬 case 의 geometry 절(축 · 원점 · 변 4묶음)을 바로 낸다. `uv_mask_from_region` 결과도 같은 규약으로 옮긴다. STE `reddish_case_build`(ST-7)가 맡아도 되지만, 한 곳으로 정해 달라.
- **확인 방법**: 과제 A 창 유리로 낸 geometry 를 손대지 않고 레디쉬에 넣는다. 메시 상자가 x = 짧은 변, 모서리 원점으로 나와야 한다.

### SF-6. `uv_mask_from_region` — 실제 UV 창의 출처 (P1)
- **지금**: 기능은 돈다. 창 유리 + 장식 유리로 부르면 고리 1 · 넓이 2,343.8 mm² · 구멍 3 이 나오고, 창 유리 + 카메라 창 파트로 부르면 rect 12.3×26.5 mm · 292.8 mm² 가 나온다. 그러나 과제 A 에는 인쇄 · 차광층 파트가 없고 `list_planar_regions` 도 0건이다. 그래서 실제 UV 조사 창 값은 얻지 못했다.
- **바라는 동작**: 인쇄 · 차광층이 파트로 없을 때 쓸 출처(평면 영역 장부 등)를 정한다. 출처가 없으면 그 사유를 응답에 준다.
- **확인 방법**: 과제 A 창 유리에서 UV 창 사각 목록이 외곽 좌표계(SF-5 규약)로 나온다.

### SF-7. `enclosure_candidates` — 앞뒤 유리가 빠짐 (P1)
- **지금**
  - 과제 B 결과는 5줄이다. 프레임(cumulative_share 0.941 · +z 1.0 · −z 0.903), 아래 장식 1, 카메라 장식 3. 전면 · 후면 유리가 없다.
  - 상자로 어림하기 때문에 고리 모양 프레임 상자가 ±z 를 다 덮는다. 응답 note 도 "고리 모양 프레임은 가운데 구멍까지 덮는다"고 적는다.
  - 닫힘 추정 칸이 없다. air_upper_mm3 48,610 은 위끝뿐이다.
  - 그래서 앞뒤 유리는 사람이 `find_parts` 이름 · 부피로 골랐다.
- **바라는 동작**: 상자가 아니라 실제 면 가림으로 몫을 셈해 앞뒤 유리를 후보에 넣는다. 닫힘 추정(닫혔나 · 남은 틈) 칸을 둔다.
- **확인 방법**: 과제 B 에서 프레임 · 전면 유리 · 후면 유리가 함께 후보로 나온다.

### SF-8. `list_artifacts` part 필터가 0행 (P2)
- **지금**: part=창 유리(이름 · 경로 둘 다, include_renders true/false 둘 다)로 부르면 parts_matched 1 · artifacts 0 이다. kind=part_step 으로는 그 파트의 줄이 1행 나온다.
- **바라는 동작**: part 로 맞힌 파트의 part_step · stl · glb 를 낸다.
- **확인 방법**: 같은 호출이 1행 이상을 낸다.

### SF-9. `uv_mask_from_region` 응답 접기 (P2)
- **지금**: 응답이 265,308자다. 점 1,152 짜리 고리 하나만 나와도 92,525자다. chat_fold · full 인자가 없다.
- **바라는 동작**: 기본은 요약(고리 수 · 상자 · 넓이 · 구멍 수)만 준다. 점열은 full=true 나 산출물 파일로 준다.
- **확인 방법**: 같은 호출의 기본 응답이 챗 한도 안에 든다.

### SF-10. 역할 축 — 창 접착 테이프가 glass 로 분류됨 (P2)
- **지금**: role=glass 9건 가운데 3건이 접착 폴더 아래 창 테이프다. 역할 축에는 cushion_adhesive 가 있다. display_panel 역할은 축에 들어왔다(과제 A 는 해당 파트 0건).
- **바라는 동작**: 테이프 · 필름류를 glass 와 나눈다.
- **확인 방법**: 과제 A 에서 role=glass 에 접착 폴더 파트가 없다.

### SF-11. `leak_report` — 외피 3파트가 예산 1.1배로 멈춤 (P2)
- **지금**
  - 도구 설명은 "외피 파트(프레임 · 앞뒤 유리 · 커버)로 좁히면 넓은 창도 예산 안에서 잰다"다.
  - 그런데 parts=[프레임, 전면 유리, 후면 유리]는 max_gap 1 · 2 모두 재기 전에 멈춘다. 후보 2쌍 · 면쌍 316,731 / 300,000(1.1배) · worst_pair 209,667 이다.
  - 2파트씩 부르면 된다(measured 0.039226 · 0.039417).
  - 맨이름 `leak_report` 서명에는 parts 가 없어서 invoke_tool 로만 넘길 수 있다.
- **바라는 동작**: 외피 3파트를 쌍별로 나눠 예산 안에서 잰다. 멈출 때는 나눠 부를 길을 응답에 준다. 서명에 parts 를 싣는다.
- **확인 방법**: 같은 3파트 호출이 measured 로 끝난다.

### SF-12. 확인만 부탁 (P2)
- **지금**: 아래 기능은 이번에 볼 기회가 없었다.
  - `export_part_step` 의 source(raw/worked) · to_ste_upload=true. 게이트웨이 `artifact_to_ste_upload` 로 대신했다.
  - `job_status.queue`. 잡이 대기 없이 바로 시작했다.
  - `list_artifacts(kind=stl)` 의 limit 없는 기본 요약 · full=true.
- **바라는 동작**: to_ste_upload=true 가 `artifact_to_ste_upload` 와 같은 함수를 부르는지 알려 달라. 나머지 둘은 기대한 대로 동작하는지 알려 달라.
- **확인 방법**: 각 옵션을 한 번씩 불러 응답 꼴을 맞춰 본다.

---

## 2. STE

### ST-1. 개구부를 구멍 영역 패치로 (P0)
- **지금**: 잡 1ddbdd7cd769 에서 입구를 반경 4 mm(약 50 mm²)로 줬다. fluxes_at_openings 머리에는 patch inlet · Faces 235 · Area 4.08e-4 m² 가 찍혔다. 아래 면 전체(408 mm²)가 입구가 된 것이고, 11-17 과 같다.
- **바라는 동작**: `openings[{center, radius 또는 area_m2, normal?}]` 이면 그 원(또는 StepForge `cavity_openings` 영역) 안의 면만 잘라 새 패치로 만든다. 위치와 연결성으로 고른다. 패치 넓이 · 면 수를 결과에 남긴다.
- **확인 방법**: 같은 입력에서 inlet 넓이가 약 50 mm² 이고, 결과에 넓이 · 면 수가 있다.

### ST-2. 개구부 미매칭 · 출구 없음이면 잡 실패 (P0)
- **지금**
  - 같은 잡에서 출구를 일부러 24 mm 빗나가게 했다. auto_mapping 은 cold_wall · wall · inlet · wall_1~3 뿐이고 outlet 이 없다. 로그에는 아무 말이 없고 잡은 COMPLETED/0 이다.
  - 출구 원의 중심은 위 면 위에 있었다. 매칭이 면 위 위치가 아니라 묶음 중심 거리로 된다는 뜻이다(ST-1 과 같은 원인).
  - 출구가 없으니 닫힌 상자를 미는 해석이 됐다. 입구 sum(phi)가 −2.3157e-4 에서 −5.4695e-4 로 136 % 커졌다(가압 판단은 phi 로 추정했고, p 필드는 보지 않았다).
  - 그런데도 보고서는 내부 15 → 60.8 °C 를 "ΔT +45.84 K 잠열"로, 응축률 6.59 mg/s(11-17 기준 잡 0.27 mg/s 의 24배)를 정상 결과로 냈다.
- **바라는 동작**: 다음 가운데 하나라도 맞으면 결로 단계 fail + 잡 FAILED + failed_stage "condensation" + reason_code 를 낸다.
  - 개구부가 하나라도 패치에 안 붙음 → `opening_unmatched`
  - 입구 · 출구 중 하나가 없음 → `no_outlet`
  - 입출 유량 차가 한계를 넘음 → `flux_imbalance`
- **확인 방법**: 1ddbdd7cd769 와 같은 입력이 FAILED · no_outlet(또는 opening_unmatched)으로 끝난다.

### ST-3. 레지스트리 잡에 StepForge 주소 · 잡 한정 토큰 넣기 (P0, BG-1 과 짝)
- **지금**: part-study · part-study-registry 실행기 두 벌의 파일 시각이 11-17 15:14 그대로다. StepForge 주소 설정은 0줄, 토큰(Authorization) 설정도 0줄이다(11-21 읽기). 11-17 레지스트리 잡 301e2c766da6 은 Connection refused 로 끝났다. 이번에는 제출 상한 때문에 레지스트리 잡을 내지 않았다.
- **바라는 동작**: 잡 환경에 운영 StepForge 주소와 잡 한정 서비스 토큰을 넣는다.
- **확인 방법**: 과제 A · part=창 유리로 레지스트리 잡을 낸다. fetch 가 ok 이고, 받은 파일이 그 파트 하나(솔리드 1)다.

### ST-4. 단계 실패 = 잡 실패 (P1)
- **지금**: da723f9ba623(outline fail · reddish skip)과 007f6a2250e4(outline fail · cond=1 인데 condensation skip)가 둘 다 COMPLETED · exit 0, "성공 2 · 실패 1 · 건너뜀 3" 이다.
- **바라는 동작**: 요청한 단계 가운데 fail 이 있으면 잡 FAILED + failed_stage 를 낸다. skip 은 사유 코드로 남긴다.
- **확인 방법**: 두 잡과 같은 입력이 FAILED · failed_stage "outline" 으로 끝난다.

### ST-5. `ste_job_summary` (P1)
- **지금**: STE 앱 도구 12개 가운데 정리된 수치를 주는 도구가 없다. 레디쉬는 results.json 의 V2 · V3 가 value_html 문자열("37.76 mm")뿐이다. 결로는 report.txt 문자열과 .dat 머리 주석에서 뽑아야 한다.
- **바라는 동작**: `job_id` → `{app, state, failed_stage, stages[], validation 또는 openings, metrics(앱별), verdict, report_url, case_digest}`. 11-17 요청의 꼴 그대로이고, 레디쉬 · 결로가 같은 이름을 쓴다.
- **확인 방법**
  - 608a24a0c924 → V2 value 37.76 · reference 34.97 · unit mm · pass null · reason_code.
  - 1ddbdd7cd769 → 입구 패치 넓이 · 유량 · 응축률이 숫자 칸으로 나온다.

### ST-6. 판정 기준 · 판정 (P1)
- **지금**
  - 레디쉬 608a24a0c924: V1 true · V2 pass null(짧은 축 반폭 37.9 < 3δ, δ 27.57). verdict · reason_code · criteria 칸이 없다.
  - 결로: report.txt 에 "국소 결로 판정" 면적 표와 "→ 결로 발생 조건" 문장만 있다. 출구 없는 잘못된 해석에도 같은 문장이 나온다.
- **바라는 동작**: case.yaml · scenario.json 에 `criteria` 를 두고, 결과에 `verdict {pass, metric, value, limit, reason_code}` 를 낸다. V2 가 null 이면 `half_width_lt_3delta` 를 낸다.
- **확인 방법**: criteria 를 넣은 레디쉬 · 결로 잡에서 verdict 가 나온다.

### ST-7. `reddish_case_build` (P1)
- **지금**: 도구가 없다. case 템플릿은 11-17 잡 db7bbee75f4f 에서 손으로 받았다. 608a24a0c924 는 형상만 바꾸고 나머지는 템플릿 그대로다(적층 5층 · 화학 · h · UV 창 17.4~58.4 × 43.2~118.2). 축 배정 · 원점 옮김도 사람이 했다.
- **바라는 동작**: 입력은 geometry(StepForge `part_outline_2d` 출력 또는 파트 참조) · stack · chemistry 프리셋 · environment · uv_mask · edge_h 다. 출력은 검사를 거친 case.yaml 과 `placeholders`(아직 템플릿 값인 칸)다. SF-5 규약 변환을 여기서 맡아도 된다.
- **확인 방법**: `part_outline_2d` 출력을 그대로 넣어 case.yaml 이 나오고, placeholders 에 남은 템플릿 칸이 적힌다.

### ST-8. 변별 경계 h 기본표 (P1)
- **지금**: 도구가 없다. StepForge 변별 이웃 정보(관계 tied · clearance · gap)는 생겼지만 접촉 넓이가 0 이다(SF-2). corner 변 묶음을 left/right/top/bottom 에 넣는 규칙도 없다.
- **바라는 동작**: 관계 + 실링 종류 → h 기본값을 정하고, StepForge 변별 정보와 합쳐 edge_groups 를 만든다.
- **확인 방법**: 과제 A 창 유리 외곽으로 edge_groups 4묶음과 h 값이 나온다.

### ST-9. 결로 후처리 단위 · 자릿수 (P1)
- **지금**: 1ddbdd7cd769 보고서의 "부피유량 입구 0.547 L/s" 는 sum(phi) 5.4695e-4(질량유량)와 같은 값이다. "Volume : 0.000 m³", "누적 응축량 0.001 g" 으로 찍힌다. 로그에는 "OK (cells: unknown)" 이 남는데, 보고서 안에는 "과포화 셀 0/23500" 이 있다.
- **바라는 동작**: phi 를 질량유량으로 읽고, 부피유량은 해석 밀도로 나눈다. 부피는 cm³, 응축량은 mg 로도 찍는다. 로그에 셀 수를 남긴다.
- **확인 방법**: 같은 잡을 다시 처리하면 부피유량이 sum(phi) 와 다르고, 부피 · 응축량이 0 이 아닌 자릿수로 나온다.

### ST-10. `condensation_scenario_build` · 업로드에 시나리오 넣기 (P1)
- **지금**: 007f6a2250e4 의 condensation 단계는 "scenario.json 을 올리지 않아 건너뜀" 으로 skip 됐다. `artifact_to_ste_upload` 는 StepForge 산출물만 옮긴다. `submit_job` 설명에는 "files 는 upload_id 와 같이 줄 수 없다" 고 돼 있다. 그래서 StepForge STEP 업로드와 시나리오를 한 잡에 줄 MCP 길이 없다.
- **바라는 동작**: 검사를 거친 scenario.json + placeholders 를 낸다. upload_id 를 주면 그 업로드에 scenario.json 을 더한다(또는 `submit_job` 이 files 와 upload_id 를 함께 받는다).
- **확인 방법**: part-study(cond 1)를 업로드 + 시나리오로 내면 condensation 단계가 skip 되지 않는다.

### ST-11. part-study 단계 고르기 (P1, BG-6 과 짝)
- **지금**: `get_app_schema(part-study)` 인자 13개(plane ~ ncpu)에 단계 칸이 없다. 결로만 보려 해도 outline · reddish 가 같이 돈다.
- **바라는 동작**: `stages=[…]` 로 돌릴 단계를 고른다.
- **확인 방법**: stages=["stl","condensation"] 으로 낸 잡의 stage.json 에 outline · reddish 가 "요청 안 함"으로 남는다.

### ST-12. request.json 스키마 노출 (P2)
- **지금**: `get_app_schema(part-study-registry)` 는 params 13 · inputs *.json 만 준다. request.json 키와 part 의 뜻(보고서 이름일 뿐)이 없다.
- **바라는 동작**: 요청서 키 · 뜻 · part 설명을 스키마에 싣는다.
- **확인 방법**: 스키마만 보고 request.json 을 쓸 수 있다.

### ST-13. 결과 수치 칸 · 단위 (P2)
- **지금**: 608a24a0c924 results.json(15,759 B)의 설정 메아리에서 다음이 보인다.
  - config.time.total_days 864000.0 · output_interval_days 43200.0. 일 칸에 초 값이 들어 있다.
  - geometry width_mm 0.0759 · corner_radius_mm 0.005835 · stackup thickness_um 7.5e-05. mm/µm 이름 칸에 m 값이 들어 있다.
  - V2 · V3 는 문자열뿐이다.
- **바라는 동작**: 칸 이름과 단위를 맞춘다. V2 · V3 에 value_mm · reference_mm 숫자 칸을 둔다.
- **확인 방법**: 같은 case 로 다시 내면 total_days 10, width_mm 75.856 꼴로 나온다.

### ST-14. 잡 목록 소유자 · 시야 (P2)
- **지금**: `ste_list_jobs` 에 owner · mine 칸이 없다. total 944 · RUNNING 7 로, 전체(관리자 시야)가 보이는지 호출자 잡만 보이는지 응답에 적혀 있지 않다.
- **바라는 동작**: owner · mine(기본 true) 칸을 두고, 시야를 응답에 적는다.
- **확인 방법**: 기본 호출에 내 잡만 나오고, 시야 표기가 있다.

### ST-15. 레디쉬 환경 절 (P2)
- **지금**: 608a24a0c924 config 에 environment 키가 없다. 온도 · 습도를 넣을 칸이 없어 시험하지 못했다.
- **바라는 동작**: case 에 `environment {temperature_C, rh}` 와 D · S 의 온도 의존을 둔다.
- **확인 방법**: environment 를 바꾼 두 잡의 결과가 달라지고, 결과 메아리에 그 값이 남는다.

### ST-16. `get_job_file` 앞부분 · 범위 (P2)
- **지금**: 인자는 job_id · path · tail_lines · max_bytes 뿐이라 꼬리만 읽힌다.
- **바라는 동작**: head_lines 또는 offset 을 둔다.
- **확인 방법**: 결로 잡의 controlDict 앞쪽을 읽을 수 있다.

### ST-17. 장시간 결로 모드 (P2)
- **지금**: `get_app_schema(condensation)` 인자는 ncpu · end_time · resolution 뿐이다(11-17 과 같다).
- **바라는 동작**: 시간 ~ 일 단위 시험에 맞는 준정상 · 들숨날숨 모드를 둔다.
- **확인 방법**: 시간 단위 end_time 의 잡이 한도 안에 끝난다.

---

## 3. 브리지·게이트웨이

### BG-1. 레지스트리 fetch 가 운영 StepForge 에서 파트를 받게 (P0, ST-3 과 짝)
- **지금**: fetch_part.py 가 기본 주소(잡 노드 자신)로 간다. 11-17 잡 301e2c766da6 은 Connection refused 였다. 요청서 part 는 보고서 이름일 뿐이라 과제 전체를 받는다. 실행기에도 주소 · 토큰 설정이 없다(11-21 읽기).
- **바라는 동작**
  - 잡 환경에 주입된 주소 · 토큰을 쓴다.
  - 요청서 part 로 StepForge `export_part_step`(이번에 생겼다)을 불러 그 파트만 받는다.
  - 실패하면 원인을 연결 · 인증 · 과제 없음 · 파트 없음으로 나눠 적는다.
- **확인 방법**: ST-3 과 같은 잡으로 확인한다. 일부러 없는 파트 이름을 넣으면 fetch fail 과 "파트 없음"이 나와야 한다.

### BG-2. outline 얇은 판 · `outline_source=stepforge` (P0)
- **지금**
  - da723f9ba623(과제 A 창 유리 STEP 155,360 B, 0.45 mm 판): "닫힌 외곽을 찾지 못했다" · 투영면 xy · 두께 0.4938 · 종횡 153.7. stl 은 ok 였다.
  - 007f6a2250e4(과제 B 후면 유리 STEP 240,542 B, 0.63 mm 판): "외곽이 bbox 단면의 6.7 % — 하한 25 %" · 윤곽 2(외곽 1 + 구멍 1).
  - StepForge `part_outline_2d` 는 같은 창 유리를 외곽 1 · 구멍 0 · 75.856×161.368 mm 로 읽는다(deflection 0.1).
  - part-study 에 outline_source 인자가 없다.
- **바라는 동작**: 두 판 모두 outline 을 통과시킨다. `outline_source=stepforge` 로 `part_outline_2d` JSON 을 그대로 받아 메시를 만드는 길도 연다.
- **확인 방법**: 두 잡을 같은 입력으로 다시 낸다. outline ok · 창 유리 상자 약 75.86 × 161.37 mm · 구멍 0 · 후면 유리 외곽 1 + 구멍 1 이 나오고, 다음 단계로 넘어가야 한다.

### BG-3. `artifact_to_ste_upload` 남은 확인 (P0 확인)
- **지금**
  - part_step 155,360 B 와 240,542 B 는 sha256 이 맞게 올라갔다. 그 업로드로 part-study 가 돌았다(da723f9ba623 · 007f6a2250e4). 응답에 티켓 · URL 이 없어서 좋다.
  - 큰 파일(11-17 과제 전체 STEP 은 129.7 MB)과 cavity_step 종류는 보지 못했다.
  - 같은 업로드에 scenario.json 을 더할 길이 없다(ST-10).
- **바라는 동작**: 100 MB 급과 cavity_step 도 같은 꼴로 옮긴다. 업로드에 작은 텍스트 파일을 더할 수 있게 한다.
- **확인 방법**
  - 과제 전체 worked_step(100 MB 급)을 옮기면 sha256 이 맞다.
  - cavity_step + scenario.json 을 한 업로드에 넣어 condensation 을 제출할 수 있다.

### BG-4. 확산 물성 조회 보강 (P1)
- **지금**
  - `gas_transport_lookup`([75, 141, 2675], 298.15 K, O2)에서 D · S · P 를 다 주는 것은 2675 뿐이다. 2675 의 D 2.4e-13 은 303.15 K 값(Δ5)이다.
  - 75 · 141 은 "gas_solubility 에 O2 값이 없다"로 S 가 비어 있다. P/D 로 S 를 셈하지도 않는다.
  - 2675 는 실링 에폭시 계열이고, grade_scope 에 주의 문구가 있다.
  - 레디쉬 층 재료와 이어지지 않아, 잡 608a24a0c924 는 모든 층에 S 4.7e-05(템플릿)를 썼다.
- **바라는 동작**
  - S 가 없고 P · D 가 있으면 S = P/D 로 추정하고, 추정임을 표시한다.
  - 층 → material_id(SF-4)로 층별 D · S 를 준다.
  - 요청 온도와 데이터 온도의 차이(Δ)는 칸으로 준다.
- **확인 방법**: P · D 가 있는 재료에서 S(추정)가 나온다. `part_stack` 층 id 를 넣으면 층별 D · S 표가 나온다.

### BG-5. 시험 조건 → 해석 환경 값 (P1, 포털 PT-1 과 같은 일)
- **지금**: 결로 잡 1ddbdd7cd769 의 환경은 11-17 예제 값(indoor 288.15 K · RH 0.3 등)을 그대로 넣었다. 신뢰성 시험 조건을 해석 환경으로 바꾸는 도구가 없다. 신뢰성 시험 앱은 개인 토큰 미등록 상태(needs_connect)다.
- **바라는 동작**: 시험 id 하나로 결로용 `{outdoor_T_C, outdoor_rh, indoor_T_C, indoor_rh, cold_wall_T_C, hours}` 와 레디쉬용 `{temperature_C, rh, lux, days}` 를 준다.
- **확인 방법**: 개인 토큰을 등록한 사용자로 시험 id 1건을 넣으면 두 꼴이 다 나온다.

### BG-6. STL 단위 m 출력 (P1, ST-11 과 짝)
- **지금**: part-study 인자표에 STL 단위 칸이 없다. 브리지 STL 은 mm 이고 결로 쪽에서 줄인다. 그래서 시나리오 개구부 좌표(m)와 단위가 어긋나기 쉽다.
- **바라는 동작**: STL 을 m 로 내는 선택(`--units m`)을 연다.
- **확인 방법**: 단위 m 로 낸 잡의 STL 상자가 m 값이다.

---

## 4. 포털

### PT-1. 개인 토큰이 없을 때의 안내 (P1)
- **지금**: 신뢰성 시험 조회(`list_reliability_tests`)가 개인 토큰 미등록으로 막힌다. 도구 앱 목록에서도 status 가 needs_connect 다. 막힐 때 "등록 방법"과 "공용 프리셋 조건으로 대신 받을지"를 응답에 주는 경로는 확인하지 못했다.
- **바라는 동작**: 막을 때 등록 방법과 공용 프리셋 대안을 함께 준다. 그래야 디지털워커가 사용자에게 바로 물을 수 있다.
- **확인 방법**: 토큰이 없는 사용자로 부르면 두 안내가 응답에 있다.

### PT-2. 운영본 표시 (P2)
- **지금**: 도구 앱 목록의 StepForge 줄에는 env prod · canonical true · 별칭이 있다. 하지만 build · instance 칸이 없다. 다른 앱 줄 일부(리스크 · 적층 등)에는 build 가 있다. build 3404c449 는 StepForge system_status 를 따로 불러야 보인다.
- **바라는 동작**: StepForge 줄에도 build 와 instance(운영 / 동결)를 싣는다.
- **확인 방법**: 목록 한 번으로 build 3404c449 와 운영본 여부가 보인다.

---

## 참고 — 이번 판에서 풀린 것 (요청 아님)
- `export_part_step`: 과제 A 창 유리 part_step 155,360 B 를 동기로 냈다. 되읽기 check same true(솔리드 1 · 부피 5,487.263996 mm³)다. 그대로 STE 까지 셸 없이 갔다.
- `list_artifacts` 의 path_note(노드 안 경로임을 밝히고 받는 길 셋을 안내)와 쪽 넘기기(page_note · more_after)가 된다. `download_artifact` seek(60 B 조각 · sha 일치)도 된다.
- `part_outline_2d` 가 외곽 다각형 · 구멍 · 변별 이웃을 준다(deflection 0.1). SF-2 의 deflection 의존만 남았다.
- `leak_report` 의 seal_gaps 제안 노트(suggested 0.525 · table_covers_mm 0.5)가 나온다. 접수 검사는 SF-1 에 남았다.
