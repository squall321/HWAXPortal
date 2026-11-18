# 레디쉬 — StepForge → STE 연계 시험 결과 · 개발 요청 통합본 (2026-11-17)

StepForge 과제의 CAD에서 디스플레이 파트를 골라 면을 뽑고, 그 형상으로 레디쉬 해석을 돌리는 과정을 디지털워커가 HWAX MCP 도구만으로 해 보았다. 이 문서는 그 시험의 기록, 도출한 함수, 받을 곳별 요청서 초안을 한 파일로 묶은 것이다. 과제는 "과제 A", 파트는 "디스플레이 파트(창 유리)"로만 적는다.

## 요약

1. **돌았나**: 레디쉬 1건이 54 s에 돌았다(V1 통과, V2 37.79 mm · 판정 null). 다만 형상은 StepForge 수치를 사람이 둥근 사각형으로 옮긴 것이고, 적층·화학·경계·UV 창은 템플릿 값이다.
2. **막힌 곳**: 파트 하나의 외곽 다각형을 주는 도구가 없다. 파트 하나 STEP 반출이 없다(과제 전체 129.7 MB > MCP 1 MB, 파트는 57 KB). 레지스트리 fetch가 운영 StepForge에 닿지 않는다.
3. **우회도 막힘**: 파트 STEP을 사람이 꺼내 올렸더니, STE outline이 0.45 mm 판에서 외곽을 못 찾았다. 그런데 잡은 COMPLETED · exit 0이었다.
4. **판정 없음**: 휴대폰 크기 패널은 반폭이 3δ보다 작아 V2가 늘 null이고, 레디쉬 합격 기준 칸이 없다.
5. **도출 함수 20개**: P0 4개(`export_part_step`, `part_outline_2d`, 레지스트리 fetch 연결, outline 얇은 판 수정), P1 9개, P2 7개.

## 받을 곳별 요청 한눈에

| 받을 곳 | P0 | P1 | P2 | 장 |
|---|---|---|---|---|
| StepForge | `export_part_step` · `part_outline_2d` | `part_stack` · `uv_mask_from_region` | 역할 `display_panel` · 산출물 목록 요약 | 3장 |
| 브리지 | fetch 연결 · 파트로 받기 · outline 얇은 판 수정 | `outline_source=stepforge` | — | 4장 |
| STE | 잡에 StepForge 주소·토큰 주입 | 단계 실패 = 잡 실패 · `ste_job_summary` · 판정 기준 · `reddish_case_build` · 경계 h 기본표 | 요청서 스키마 · 결과 숫자 칸 · 잡 소유자 · 환경 절 | 5장 |
| HWAX 포탈·게이트웨이 | — | `material_gas_transport` · 시험 조건 → 환경 값 | 운영본 표시 · 잡 목록 소유자 | 6장 |

## 차례

- 1. 시험 기록 (RUNLOG)
- 2. 필요한 함수 (FUNCTIONS)
- 3. 요청서 — StepForge
- 4. 요청서 — 브리지
- 5. 요청서 — STE
- 6. 요청서 — HWAX 포탈·게이트웨이

---

## 1. 시험 기록 (RUNLOG)

표시: ✋ 사람(셸·수작업)이 끼어든 곳 · ⛔ MCP 자동화가 막힌 곳 · D 결함. 셸은 관찰·확인과, 막힌 곳을 돌아가는 데에만 썼다. 과제는 "과제 A", 파트는 "디스플레이 파트(창 유리)"로만 적는다. 시각은 KST.

### 0. 시작 (18:02)

| 시각 | 도구(인자 요약) | 결과 요약 | 시간 |
|---|---|---|---|
| 18:02 | `list_tool_apps` | `heax-step_forge` 193 도구 · ok | 1 s |
| 18:02 | `invoke_tool("stepforgeprod_list_projects")` | `unknown tool` | 1 s |
| 18:03 | `heaxstep_forge_system_status` · `system_capabilities` | 과제 33 · 실행 잡 2 · 대기 1 · build 27b2132 · 193 도구 → **맨이름 = 운영본** | 2 s |

- ⛔-0 (경미) CONTEXT.md의 `stepforgeprod_` 접두사는 11-12 전환 이전 사실이다. 어느 이름이 운영본인지는 도구 목록만으로 알 수 없었다. `system_capabilities`로 판(build)을 보고서야 확정했다.

### 1. 과제·파트 고르기 (18:03 ~ 18:05)

| 시각 | 도구(인자 요약) | 결과 요약 | 시간 |
|---|---|---|---|
| 18:03 | `list_projects(fields=[name,stage,parts], limit=60)` | 33과제 · 전부 세트 조립(300 ~ 6천 파트) | 1 s |
| 18:04 | `identify_parts` × 3과제 | 디스플레이/윈도우 분류 6 ~ 11개씩 · 역할 `glass` | 1 s |
| 18:04 | `find_parts(과제 A, role=glass)` | 9건 · 창 유리 1건이 75.856 × 161.368 × 0.45 mm | 2 s |
| 18:04 | `find_parts(과제 A, name=*disp* / *octa* / *panel* / *lcd*)` | 전부 0건 → **표시 패널·적층 파트 자체가 과제에 없다** | 1 s ×4 |
| 18:04 | `describe_part(과제 A, 창 유리, features)` | 판 · 두께 0.45 · 부피 5,487 mm³ · 프레임과 tied(접촉 3,936 mm²) · 재질 STEP 없음 / 사람이 넣은 유리 재질 1건 | 5 s |

- **과제 A** = 창 유리 크기가 휴대폰 화면 크기이고 저장값이 남아 있는 과제(647 파트, 검출까지 됨). 정의 647개 전부 옛 식 저장값(`backfill` 권고)이다. 레디쉬에 쓰는 폭·높이·두께에는 영향이 없다.
- ✋-1 "디스플레이 파트"를 고른 것은 사람 판단이다. 과제에 표시 패널·편광판·OCA 같은 적층 파트가 없다. 그래서 창 유리 외곽을 디스플레이 외곽 대용으로 썼다. 역할 축에는 `glass`만 있고 표시 패널 역할이 없다.

### 2. 디스플레이 파트 확정 (18:05)

| 시각 | 도구(인자 요약) | 결과 요약 | 시간 |
|---|---|---|---|
| 18:05 | `part_plane_frame(과제 A, 창 유리)` | 평면 +z · 면 1 · 넓이 12,193.7 mm² · **외곽 루프 1 · 점 658** · box_uv 75.856 × 161.368 → 구멍 0. **다각형 좌표는 안 준다** | 1 s |
| 18:05 | `list_planar_regions(과제 A)` | 0건. 평면 영역은 사람이 그림+대응점으로 정한 입력이다(`align_image_to_geometry`) | 1 s |
| 18:05 | `thickness_report(과제 A, 창 유리)` | 최소 두께 0.45 mm(면 24) | 2 s |
| 18:05 | `search_tools("파트 하나 평면 외곽 다각형 … polygon")` | `shape_op` · `section_view` · `dimension_view` 등. 다각형을 돌려주는 읽기 도구는 없다 | 1 s |
| 18:05 | `describe_part(… faces="+z")` | 면 요약뿐, 좌표 없음 | 3 s |

- ⛔-1 **파트 하나의 평면 외곽 다각형(바깥 + 구멍, 평면 mm 좌표)을 돌려주는 도구가 없다.** `part_plane_frame`은 루프 수·점 수·상자만 준다. 코너 반경·변 이름(좌/우/상/하)·변별 이웃 파트도 없다.

### 3. 경로 A — part-study-registry (18:05 ~ 18:11)

| 시각 | 도구(인자 요약) | 결과 요약 | 시간 |
|---|---|---|---|
| 18:05 | `get_app_schema(part-study-registry)` · `(reddish)` | registry: `*.json` + project/solid/source/plane/… · reddish: `*.yaml` + total_days/output_days/post/fields | 2 s |
| 18:05 ~ 18:08 | 셸(STE 헤드) 실행기 `part-study-registry/ste-run.sh` 읽기 | 요청서 키가 폼 인자를 덮는다. `part`는 보고서 이름일 뿐이고 파트를 고르지 않는다 | — |
| 18:08 | `ste_list_jobs(limit=10)` | 다른 사용자 잡까지 보인다(lsdyna 128코어 등) | 1 s |
| 18:11 | `submit_job(part-study-registry, files=[request.json])` — project=과제 A · source raw · cond 0 · post min · ncpu 2 · total_days 2 | 잡 **301e2c766da6** | 1 s |
| 18:11 | `get_job_status(301e2c766da6)` | 3 s 만에 COMPLETED/exit 0. `[fetch] 실패 — POST /api/projects/…/export-step → [Errno 111] Connection refused` → outline·stl·reddish 전부 skip | 1 s |

- ✋-7 실행기·요청서 키는 셸로 읽어서 알았다. `get_app_schema`에는 request.json 키 목록이 없다.
- ⛔-3 **레지스트리 fetch가 운영 StepForge에 닿지 않는다.** fetch는 기본 주소(잡 노드 localhost)로 갔다. 실행기 두 벌에 STEPFORGE_BASE 설정이 없다(셸 grep 0줄). 운영 StepForge는 노드 로컬에서만 열려 있고, 포털 경로로는 인증이 필요하다. 닿더라도 과제 전체 STEP을 받는다. 그다음 `solid` 번호로 골라야 하지만, StepForge 파트 ↔ STEP solid 번호 대응표는 없다.
- D-1 fetch가 실패해도 잡 상태는 **COMPLETED · exit 0**이다. 디지털워커가 "성공"으로 읽는다.

### 4. 경로 B — 파트 STEP · 공유 경로 · 레디쉬 실행 (18:11 ~ 18:36)

| 시각 | 도구(인자 요약) | 결과 요약 | 시간 |
|---|---|---|---|
| 18:11 | `search_tools("파트 하나만 STEP 으로 반출")` | 없음(`match_parts_across` · `compare_part_view` …). `export_step`은 과제 전체 | 1 s |
| 18:12 | `list_artifacts(과제 A)` | worked_step 1 · stl 644 · glb 647 · kfile 1 | 1 s |
| 18:12 | `download_artifact(과제 A, worked_step)` | 129,727,944 B · **too_large**(MCP 상한 1,000,000 B). 조각 받기만 가능 | 1 s |
| 18:12 | `list_artifacts(과제 A, kind=stl)` | 응답 59,813자 → 챗 한도 초과로 파일에 저장 · 창 유리 파트 STL 47,257,365 B | 1 s |
| 18:11 ~ 18:19 | 셸(STE 헤드) 공유 경로 확인(읽기) | STE 헤드 `/home` = 로컬 ext4. 운영 StepForge 데이터 폴더 **없음**. 공유는 `/data`(NFS 950T)뿐 | — |
| 18:13 | `get_job_file(스모크 335cce92f7b8, case.yaml / results.json)` | 템플릿 확보 · 스모크 V1 true · V2 35.49 mm(기준 34.97, null) | 2 s |
| 18:15 | **B1** `submit_job(reddish, files=[case.yaml], post=min, fields=0)` — 둥근 사각형 75.856 × 161.368 · r 8.5 · 구멍 0 · total_days 10 · 나머지 템플릿 | 잡 **db7bbee75f4f** | 1 s |
| 18:16 | `get_job_status(db7bbee75f4f)` | COMPLETED/exit 0 · 메시 셀 342,168 · 절점 172,007 · 변별 경계 bottom/right/top/left 태그 11 ~ 14 · 해석 48.4 s | 54 s |
| 18:21 | `get_job_file(db7bbee75f4f, results.json, tail 45)` | **V1 pass true**(상대오차 0) · **V2 37.79 mm / 기준 34.97 mm · pass null** — 짧은 축 반폭 37.9 mm < 3δ(δ = 27.57 mm) · V3·V4 참고 | 1 s |
| 18:31 | 셸(게이트웨이 서버 → 운영 노드) 원본 파트 STEP 복사 → 게이트웨이 서버 /tmp | 56,973 B · solid 1 · ADVANCED_FACE 24 · AP214 | — |
| 18:32 | `ste_prepare_upload` | 업로드 티켓(24 h) — 값은 어디에도 남기지 않음 | 1 s |
| 18:33 | 셸 `curl -K -`(설정은 stdin으로만) | http 200 · 56,973 B | — |
| 18:35 | **B2** `submit_job(part-study, upload_id, plane auto · cond 0 · post min · ncpu 2 · total_days 2)` | 잡 **3fa9415132b7** | 1 s |
| 18:35 | `get_job_status` · `get_job_file(bridge/outline.json, stage.json)` | 13 s 만에 COMPLETED/exit 0. **outline fail "닫힌 외곽을 찾지 못했다"**(투영면 xy · 두께 0.494 · 종횡 153.7). stl ok(면 24 · 삼각형 420 · 열린 모서리 0). reddish skip | 1 s |
| 18:36 | 셸 게이트웨이 서버 `/tmp/reddish-b2` 삭제 | 없음 확인 | — |

- ⛔-2 **파트 하나 STEP 반출 도구가 없다.** 과제 전체 STEP은 129.7 MB라 MCP로 못 나른다. 정작 이 파트의 원본 STEP은 **57 KB**다(2,277배 차이). 파트별 STL은 있지만 47 MB라 조각으로 받아야 하고, STE 업로드로 넘기는 길도 없다.
- ⛔-4 운영 StepForge 데이터는 노드 로컬 디스크에 있어 STE 계산 노드에서 보이지 않는다. 공유 경로로 넘기는 길은 없다.
- ✋-6 B2 우회 전 과정이 셸이었다. 노드에서 파트 STEP 꺼내기 → 게이트웨이 서버 /tmp → `curl -K -` 업로드 → /tmp 삭제.
- ⛔-5 STE outline 단계가 **두께 0.45 mm · 면 24개짜리 단순 판**에서 닫힌 외곽을 못 찾았다. 같은 파트를 StepForge `part_plane_frame`은 루프 1개 · 점 658개로 읽었다. outline이 실패하니 레디쉬도 skip됐다. 변 태그가 붙는지는 확인하지 못했다.
- D-1(재발) outline이 실패해도 잡은 COMPLETED · exit 0이다.
- ✋-2 레디쉬 case 템플릿은 스모크 잡을 손으로 골라 복사했다(STE에 "앱 기본 case 받기" 도구가 없다).
- ✋-3 외곽 수치는 손으로 옮겼다. 폭·높이는 `describe_part` 치수, 구멍 0은 루프 수, 코너 r 8.5는 **추정**이다(코너 반경을 주는 도구가 없다).
- ✋-4 UV 창(사각 41 × 75 mm)은 손으로 외곽 가운데로 옮겼다(x 17.4 ~ 58.4, y 43.2 ~ 118.2).
- ✋-5 적층 5층(두께 · D · S) · 화학(초기 농도 · 반응 속도) · 변별 h는 템플릿의 `[PLACEHOLDER]` 값 그대로다.
- 외곽 검산: B1 형상 75.856 × 161.368은 `part_plane_frame` box_uv와 같다(손 입력이라 같을 수밖에 없다). STE outline(B2)이 낸 bbox는 75.900 × 161.412 × 0.494로, OCC 상자 여유 0.022 mm씩이 붙었다.

### 5. 결과 읽기 (18:21)

- ✋-8 `results.json`(15.7 KB)은 앞쪽이 설정 메아리다. `tail_lines`로 끝을 잘라 읽어야 `validation`이 나온다. V2 · V3은 `value_html` **문자열**("37.79 mm")뿐이고 숫자 칸이 없다. 디지털워커가 문자열에서 숫자를 뽑아야 한다.
- ⛔-8 **판정이 없다.** V1은 수치 보존(해석기 점검)이지 레디쉬 합격 여부가 아니다. V2는 반폭 < 3δ면 null이다. 휴대폰 크기 패널(반폭 35 ~ 38 mm, 3δ ≈ 83 mm)은 **늘 null**이다(스모크 · B1 둘 다). B1 침투 37.79 mm는 반폭 37.9 mm와 같다. 즉 양쪽에서 들어온 산소가 가운데서 만났다. 조사 창 안 붉어짐 면적 · P 최댓값 같은 합격 기준 칸이 case에도 결과에도 없다.
- D-2 `results.json` 정규화 설정의 `time.total_days`가 1,728,000(= 20일을 **초**로 적은 값)이다. `output_interval_days`도 43,200이다. 칸 이름과 단위가 다르다.
- 보고서 `report.html`은 결과 폴더에 있다. MCP에는 열어 볼 주소가 없다(`get_job_result`는 목록만 주고, 전체 파일은 ste-sync로 받아야 한다).

### 6. StepForge가 못 주는 레디쉬 입력 (18:38)

| 입력 | 이번 값 | StepForge | 다른 출처 후보(확인 결과) |
|---|---|---|---|
| 외곽 다각형 · 구멍 | 상자 수치 손입력 · 구멍 0 | **부분** — 루프 수 · 상자만. 다각형 · 코너 r 없음(⛔-1) | 없음 |
| 변 이름 · 변별 이웃 | 템플릿 좌/우/상/하 | **부분** — 파트 단위 이웃(프레임 tied 3,936 mm²)은 있고 변 단위는 없다 | 없음 |
| 적층(층 · 두께) | 템플릿 5층 | **없음** — 과제에 적층 파트가 없다. 유리 두께 0.45만 있다 | 없음(⛔-6) |
| 층 재료 D · S | 템플릿 | 없음 — 재질 칸은 사람이 넣은 유리 1건뿐 | 재료 카탈로그 앱: 산소투과도 105종 · 확산계수 59종 · 헨리 용해도 19종 등록(`catalog_property_distribution`). 층 → 재료 id 대응이 있어야 쓴다 |
| 화학(초기 농도 · 반응 속도) | 템플릿 | 없음 | 없음(물성팀) |
| 환경(온도 · 습도 · 기간 · 조도) | total_days 10 · 500 klx | 없음 | 신뢰성 시험 앱 `list_reliability_tests` — **내 개인 토큰이 등록되지 않아 막힘**(⛔-7). reddish case에는 온도 · 습도 칸 자체가 없다 |
| UV 마스크 영역 | 템플릿 사각을 재중심 | **부분** — 평면 영역 장부는 있지만 0건(사람이 그림을 맞춰 넣어야 한다) | 인쇄 · 차광층 파트가 있으면 그 외곽 |
| 변별 경계 h | 템플릿 1e-8 ~ 5e-8 m/s | 없음 | 관계(tied · 접착 · 간극 · 노출) → h 기본표가 필요하다 |

### 7. 디지털워커가 V1 · V2 · 판정을 깔끔히 받으려면

1. 잡 상태가 단계 실패를 그대로 드러내야 한다(D-1).
2. 결과 요약 도구 하나가 숫자로 줘야 한다. 단계별 ok/fail, V1 ~ V4 `{value, reference, unit, pass, reason_code}`, 최종 침투 · 반폭 · 3δ, 판정 `{pass, 기준, 값, 한계}`, 보고서 주소, case 지문.
3. case에 합격 기준(예: N일 뒤 조사 창 안 P 평균 상한, 붉어짐 면적비 상한)을 넣을 칸과, 그 기준으로 낸 판정이 있어야 한다(⛔-8).
4. V2가 null일 때 `reason_code`(예: `half_width_lt_3delta`)를 주어, 디지털워커가 "판정 불가 사유"를 그대로 옮길 수 있어야 한다.

### 잡 목록

| 잡 | 앱 | 결과 | 걸린 시간 |
|---|---|---|---|
| 301e2c766da6 | part-study-registry | fetch fail → 전부 skip · COMPLETED/0 | 3 s |
| db7bbee75f4f | reddish | V1 true · V2 37.79 mm(null) | 54 s |
| 3fa9415132b7 | part-study | outline fail · stl ok · reddish skip · COMPLETED/0 | 13 s |

---

## 2. 필요한 함수 (FUNCTIONS)

"왜" 칸의 기호는 1장의 ✋ · ⛔ · D 번호다. 받을 곳은 STE / HWAX 포탈·게이트웨이 / StepForge / 브리지(STE ↔ StepForge 연계 컨테이너: fetch · outline · stl)로 나눈다.

### P0 — 없으면 MCP만으로 못 돈다

| # | 이름 | 받을 곳 | 입력 → 출력 | 왜 | 우선 |
|---|---|---|---|---|---|
| 1 | `export_part_step` | StepForge | `project_id`, `part`(이름 · 경로), `source`(raw/worked) → 단일 파트 STEP 산출물 `{ref, filename, bytes, sha256, rest_path}`. 선택 `to_ste_upload=true`면 STE 업로드 스테이징에 바로 넣고 `upload_id`를 돌려준다(바이트가 모델을 지나지 않는다) | ⛔-2(과제 전체 129.7 MB > MCP 1 MB, 파트는 57 KB) · ✋-6(셸로 노드에서 꺼냄) | P0 |
| 2 | `part_outline_2d` | StepForge | `project_id`, `part`, `plane`(auto · 인덱스), `deflection` → `{frame, units:"mm", thickness, outer:[[u,v]…], holes:[[[u,v]…]…], corner_radii:[…], edges:[{id, side:left/right/top/bottom, from, to, length, neighbors:[{part, relation, contact_mm2}]}]}`. 선택 `format`: `polygon`(기본) · `reddish_geometry`(case.yaml `geometry` 절, 둥근 사각형 근사 또는 .msh/GeoJSON) | ⛔-1(루프 수 · 상자만 줌) · ✋-3(수치 손입력, 코너 r 추정) · ⛔-5 우회(이것이 있으면 STE가 STEP에서 다시 뽑지 않아도 된다) | P0 |
| 3 | 레지스트리 fetch 연결 | 브리지 + STE | 잡 환경에 `STEPFORGE_BASE` + 잡 한정 서비스 토큰(STE가 주입). `fetch_part.py`가 요청서의 `part`로 #1을 불러 그 파트만 받는다. 실패하면 단계 fail + 원인(연결 · 인증 · 파트 없음) | ⛔-3(Connection refused, 설정 없음) · ⛔-4(공유 경로 없음) · `part`가 이름일 뿐인 문제 | P0 |
| 4 | outline 얇은 판 수정 | 브리지 | 두께 0.45 mm · 면 24개 판에서 "닫힌 외곽을 찾지 못했다"가 나지 않게 고친다. 재현 잡 3fa9415132b7(입력 STEP이 잡 폴더에 있음). 함께 `outline_source=stepforge`(#2 출력 JSON을 그대로 받기)도 연다 | ⛔-5 | P0 |

### P1 — 사람 손을 없앤다

| # | 이름 | 받을 곳 | 입력 → 출력 | 왜 | 우선 |
|---|---|---|---|---|---|
| 5 | 단계 실패 = 잡 실패 | STE | part-study · registry에서 fetch · outline · reddish 중 요청한 단계가 fail이면 잡 `FAILED` + `failed_stage`. skip은 사유 코드로 | D-1(2건 모두 COMPLETED/0) | P1 |
| 6 | `ste_job_summary` | STE | `job_id` → `{app, state, failed_stage, stages:[{stage, status, note}], validation:{V1…V4:{value, reference, unit, pass, reason_code}}, metrics:{penetration_final_mm, half_width_mm, delta_mm, …}, verdict, report_url, case_digest}`. 결로도 같은 꼴(앱별 metrics만 다름) | ✋-8(results.json 꼬리 자르기 · 문자열에서 숫자 뽑기) · 보고서 주소 없음 | P1 |
| 7 | 레디쉬 판정 기준 · 판정 | STE | case.yaml `criteria`(예: N일 뒤 조사 창 안 P 평균 상한, 붉어짐 면적비 상한) → results.json `verdict {pass, metric, value, limit}`. V2 null이면 `reason_code: half_width_lt_3delta` | ⛔-8(휴대폰 크기 패널은 V2가 늘 null, 합격 기준 칸 없음) | P1 |
| 8 | `reddish_case_build` | STE | `{geometry(#2 출력) 또는 part 참조, stack(#9), chemistry 프리셋, environment, uv_mask(#12), edge_h(#11)}` → 검사를 거친 case.yaml + `placeholders:[…]`(아직 템플릿 값인 칸 목록). 검사: 광원 창이 외곽 안인지, 구멍과 겹치는지, 필수 칸 | ✋-2(스모크 잡에서 템플릿 복사) · ✋-4(UV 창 손 이동) · ✋-5 | P1 |
| 9 | `part_stack` (get/set) | StepForge | 디스플레이 파트 → 층 `[{name, thickness_um, material_id}]`(위→아래). 쓰기는 사람 확인 뒤 | ⛔-6(적층 파트 · 정보가 어디에도 없음) · ✋-1(창 유리 대용) | P1 |
| 10 | `material_gas_transport` | HWAX 포탈·게이트웨이 | `material_ids`, `temperature_K`, `species=O2` → 층별 `{D_m2_s, S_mol_m3_Pa, P_O2, source, quality_tier}`. 재료 카탈로그 앱 물성 키(확산계수 · 헨리 용해도 · 산소투과도)를 묶어 부른다 | ✋-5(D · S 템플릿) — 카탈로그에 산소투과도 105 · 확산계수 59 · 용해도 19종 있음 | P1 |
| 11 | 변별 경계 h 기본표 | STE | 관계(tied · 접착 · 간극 · 노출) + 실링 종류 → `h_m_s` 기본값. #2 `edges[].neighbors`와 합쳐 `edge_groups` 생성 | ✋-5(h 템플릿) | P1 |
| 12 | `uv_mask_from_region` | StepForge | 평면 영역(장부) 또는 인쇄 · 차광층 파트 → 외곽 좌표계의 사각 목록 또는 마스크 PNG(`mask_file`) | ✋-4 · `list_planar_regions` 0건 | P1 |
| 13 | 시험 조건 → 환경 값 | HWAX 포탈·게이트웨이 | 신뢰성 시험 id → `{temperature_C, rh, lux, days}`. 개인 토큰이 없으면 등록 안내와 함께 "공용 프리셋"으로 대신 받을지 묻는다 | ⛔-7(신뢰성 시험 앱: 개인 토큰 미등록) | P1 |

### P2 — 품질

| # | 이름 | 받을 곳 | 입력 → 출력 | 왜 | 우선 |
|---|---|---|---|---|---|
| 14 | request.json 스키마 노출 | STE | `get_app_schema(part-study-registry)`에 요청서 키 · 뜻 · `part`가 이름일 뿐이라는 점 | ✋-7(셸로 실행기를 읽어서 앎) | P2 |
| 15 | 결과 수치 칸 · 단위 | STE | V2 · V3에 `value_mm` · `reference_mm` 숫자 칸. 정규화 설정의 `total_days` 칸에 초 단위가 들어가는 문제 수정 | ✋-8 · D-2 | P2 |
| 16 | 잡 목록 소유자 표시 | STE · HWAX 포탈·게이트웨이 | `ste_list_jobs`에 `mine`(기본 true) · `owner` 칸. 관리자 시야면 응답에 그렇다고 적기 | 다른 사용자 잡이 섞여 보임 | P2 |
| 17 | 운영본 표시 | HWAX 포탈·게이트웨이 | `list_tool_apps` 줄에 `instance`(운영/동결) · build | ⛔-0 | P2 |
| 18 | 표시 패널 역할 | StepForge | 역할 축에 `display_panel` · 적층 필름류를 `glass`와 나눠 둔다 | ✋-1 | P2 |
| 19 | 산출물 목록 요약 | StepForge | `list_artifacts(kind=stl)` 기본은 개수 · 합계 · `part` 필터. 전체 줄은 `full=true` | 응답 59,813자로 챗 한도 초과 | P2 |
| 20 | 환경 절 | STE | reddish case에 `environment {temperature_C, rh}`와 D · S 온도 의존 | 1장 6절 표 — 온도 · 습도 칸이 없음 | P2 |

### 받을 곳별 묶음 → 요청서 초안

| 받을 곳 | 항목 | 요청서 |
|---|---|---|
| StepForge | 1 · 2 · 9 · 12 · 18 · 19 | 3장 |
| 브리지 | 3(fetch 쪽) · 4 | 4장 |
| STE | 3(환경 주입) · 5 · 6 · 7 · 8 · 11 · 14 · 15 · 16 · 20 | 5장 |
| HWAX 포탈·게이트웨이 | 10 · 13 · 16 · 17 | 6장 |

---

## 3. 요청서 — StepForge

- 작성 2026-11-17 · 받을 곳: StepForge 개발 · 상태: **초안(보내지 않음)**
- 근거: 디지털워커가 MCP 도구만으로 "StepForge 과제 → 디스플레이 파트 → 2D 외곽 → 레디쉬 해석"을 해 본 시험(과제 A).

### 배경

레디쉬 해석은 디스플레이 파트의 평면 외곽(바깥선 + 구멍)과 변별 경계조건이 있어야 돈다. 시험에서 StepForge 읽기 도구로 받을 수 있었던 것은 아래뿐이다.

- `part_plane_frame`: 평면 · 루프 수(1) · 점 수(658) · 상자(75.856 × 161.368 mm).
- `describe_part`: 두께 0.45 mm, 이웃 파트와의 관계(프레임과 tied, 접촉 3,936 mm²).

**외곽 다각형 좌표 · 코너 반경 · 변 이름은 받을 수 없었다.** 그래서 수치를 사람이 둥근 사각형으로 옮겼고, 코너 반경은 추정했다.

STEP도 마찬가지였다. 과제 전체 STEP(129.7 MB)만 반출할 수 있고, MCP 내려받기 상한(1 MB)을 넘는다. 이 파트 하나의 원본 STEP은 57 KB다. 결국 사람이 셸로 노드 파일을 꺼내 해석 서버에 올렸다.

### 요청

#### SF-R1 `export_part_step` (P0)
- 입력: `project_id`, `part`(이름 또는 경로), `source`(raw/worked).
- 출력: 단일 파트 STEP 산출물 `{ref, filename, bytes, sha256, rest_path}`.
- 선택: `to_ste_upload=true`면 STE 업로드 스테이징에 서버끼리 바로 넣고 `upload_id`를 돌려준다. 바이트가 모델이나 사용자 PC를 지나지 않게 하려는 것이다.
- 수용 기준: 과제 A 디스플레이 파트로 부르면 수십 KB 단위의 STEP이 나온다. 그 파일을 STE part-study에 넣으면 stl 단계가 ok다.
- 결로 연계 세션도 같은 이름을 쓴다(외피 파트 반출).

#### SF-R2 `part_outline_2d` (P0)
- 입력: `project_id`, `part`, `plane`(auto 또는 `part_plane_frame` 후보 인덱스), `deflection`.
- 출력:
  - `frame`, `units: "mm"`, `thickness`
  - `outer: [[u,v]…]`, `holes: [[[u,v]…]…]`
  - `corner_radii: […]`
  - `edges: [{id, side, from, to, length, neighbors: [{part, relation, contact_mm2}]}]`. `side`는 프레임 기준 left/right/top/bottom이다.
- 선택 `format`:
  - `polygon`(기본)
  - `reddish_geometry`: 레디쉬 case.yaml의 `geometry` 절. 둥근 사각형으로 근사할 수 있으면 builtin, 아니면 GeoJSON 또는 .msh.
- 수용 기준:
  - 과제 A 디스플레이 파트에서 바깥 루프 1개 · 구멍 0개 · 상자 75.856 × 161.368이 나온다.
  - 변 4묶음에 프레임 이웃이 붙는다.

#### SF-R3 `part_stack` get/set (P1)
- 디스플레이 파트 → 층 목록 `[{name, thickness_um, material_id}]`(위 → 아래).
- 과제에 적층 필름이 파트로 없을 때를 위한 장부다. 쓰기는 사람 확인 뒤에 한다.
- 이유: 레디쉬 적층(5층 두께 · 재료)을 줄 곳이 어디에도 없다.

#### SF-R4 `uv_mask_from_region` (P1)
- 평면 영역 장부 또는 인쇄 · 차광층 파트 → 외곽 좌표계의 사각 목록 또는 마스크 PNG.
- 이유: UV 조사 창을 사람이 손으로 옮겼다. 평면 영역 장부는 0건이었다.

#### SF-R5 역할 축 `display_panel` (P2)
- 표시 패널 · 적층 필름류를 `glass`와 나눈다.
- 이유: 지금은 창 유리와 표시 패널이 같은 역할로 묶여, "디스플레이 파트"를 이름 글롭으로 골라야 한다.

#### SF-R6 `list_artifacts(kind=stl)` 요약 기본값 (P2)
- 기본 응답은 개수 · 합계 · `part` 필터로 한다.
- 이유: 파트 644개 목록이 59,813자로 챗 한도를 넘었다.

### 재현 · 참고
- 시험 과제: 과제 A(647 파트, 검출까지). 디스플레이 파트 = 창 유리(0.45 mm 판, 면 24).
- 같은 파트를 STE outline으로 뽑으면 실패한다(잡 3fa9415132b7, 브리지 요청서 참고). SF-R2가 있으면 STE가 STEP에서 외곽을 다시 뽑지 않아도 된다.

---

## 4. 요청서 — 브리지

- 작성 2026-11-17 · 받을 곳: STE ↔ StepForge 브리지(fetch · outline · stl 컨테이너) · 상태: **초안(보내지 않음)**
- 근거: 디지털워커가 MCP 도구만으로 StepForge 과제 → 레디쉬 해석을 해 본 시험(과제 A).

### 배경

part-study-registry에 request.json 한 장(project = 과제 A, source raw, cond 0, post min, ncpu 2, total_days 2)을 넣었다. 결과는 아래와 같았다.

- fetch: `POST /api/projects/<id>/export-step → [Errno 111] Connection refused`. 기본 주소(잡 노드 자신)로 갔다.
- 그 뒤 단계는 모두 skip됐다. 잡 301e2c766da6, 3 s.

우회로 파트 하나의 STEP(57 KB, solid 1, 면 24)을 업로드해 part-study를 돌렸다.

- outline: `닫힌 외곽을 찾지 못했다`. 투영면 xy, 두께 0.494, 종횡 153.7.
- stl은 ok였다(삼각형 420, 열린 모서리 0). 잡 3fa9415132b7, 13 s.
- 같은 파트를 StepForge `part_plane_frame`은 루프 1개 · 점 658개로 읽는다.

### 요청

#### BR-R1 fetch가 운영 StepForge에 닿게 (P0)
- `fetch_part.py`가 잡 환경의 `STEPFORGE_BASE`와 잡 한정 토큰(헤더)을 쓴다. 값은 STE가 주입한다(STE 요청서 ST-R1).
- 실패하면 원인을 나눠 적는다: 연결 · 인증 · 과제 없음 · 파트 없음.

#### BR-R2 요청서 `part`로 그 파트만 받기 (P0)
- 지금 `part`는 보고서 이름일 뿐이다. 과제 전체 STEP을 받은 뒤 `solid` 번호로 골라야 하는데, StepForge 파트 ↔ STEP solid 번호 대응표는 없다.
- StepForge `export_part_step`(StepForge 요청서 SF-R1)이 생기면 그것을 부른다. 생기기 전에는 `part` 이름 ↔ solid 대응을 STEP 제품 트리에서 찾아 쓴다.

#### BR-R3 outline 얇은 판 수정 (P0)
- 재현: 잡 3fa9415132b7. 입력 STEP이 잡 결과 폴더에 있다.
- 수용 기준:
  - 이 파트에서 바깥 루프 1 · 구멍 0이 나온다.
  - 상자 약 75.86 × 161.37 mm.
  - 변 태그(left/right/top/bottom)가 붙은 메시가 나와 레디쉬 단계로 넘어간다.

#### BR-R4 `outline_source=stepforge` (P1)
- StepForge `part_outline_2d`(SF-R2) 출력 JSON을 그대로 받아 메시를 만드는 길을 연다.
- STEP에서 외곽을 다시 뽑는 일과, 그 실패 위험을 피한다.

### 참고
- 두 잡 모두 단계가 실패했는데도 잡 상태는 COMPLETED · exit 0이었다. 이 부분은 STE 요청서 ST-R2에 적었다.

---

## 5. 요청서 — STE

- 작성 2026-11-17 · 받을 곳: STE 개발 · 상태: **초안(보내지 않음)**
- 근거: 디지털워커가 MCP 도구만으로 StepForge 과제 → 레디쉬 해석을 해 본 시험(과제 A). 잡 3건.

| 잡 | 앱 | 결과 |
|---|---|---|
| 301e2c766da6 | part-study-registry | fetch 실패 → 전부 skip, 그런데 COMPLETED/0 |
| db7bbee75f4f | reddish | 54 s · V1 true · V2 37.79 mm(기준 34.97, pass null) |
| 3fa9415132b7 | part-study | outline 실패 → reddish skip, 그런데 COMPLETED/0 |

### 요청

#### ST-R1 잡에 StepForge 주소 · 토큰 주입 (P0, 브리지 BR-R1과 짝)
- part-study · part-study-registry 잡 환경에 `STEPFORGE_BASE`와 잡 한정 서비스 토큰을 넣는다.
- 지금은 실행기 두 벌 어디에도 설정이 없다. 그래서 fetch가 잡 노드 자신으로 간다.
- StepForge 데이터는 해석 노드와 공유되는 경로에 없다. 그러니 파일 공유 대신 API로 받아야 한다.

#### ST-R2 단계 실패 = 잡 실패 (P1)
- 요청한 단계(fetch · outline · reddish · condensation) 중 fail이 있으면 잡 `FAILED`, `failed_stage`를 채운다.
- skip은 사유 코드로 남긴다.
- 지금은 두 잡 모두 COMPLETED · exit 0이라 디지털워커가 성공으로 읽는다.

#### ST-R3 `ste_job_summary(job_id)` (P1)
- 출력:
  - `{app, state, failed_stage, stages:[{stage, status, note}]}`
  - `validation: {V1…V4: {value, reference, unit, pass, reason_code}}`
  - `metrics: {penetration_final_mm, half_width_mm, delta_mm, …}`
  - `verdict`, `report_url`, `case_digest`
- 결로도 같은 꼴로 하고 `metrics`만 앱별로 다르게 한다. 결로 연계 세션도 같은 이름을 쓴다.
- 이유:
  - 지금은 `results.json`(15.7 KB, 앞쪽이 설정 메아리)을 꼬리로 잘라 읽어야 한다.
  - V2 · V3은 `value_html` 문자열("37.79 mm")뿐이다.
  - `report.html`을 열 주소가 MCP에 없다.

#### ST-R4 레디쉬 판정 기준 · 판정 (P1)
- case.yaml에 `criteria` 절을 둔다. 예: N일 뒤 조사 창 안 P 평균 상한, 붉어짐 면적비 상한.
- results.json에 `verdict {pass, metric, value, limit}`을 낸다.
- V2가 null이면 `reason_code: half_width_lt_3delta`를 낸다.
- 이유:
  - 휴대폰 크기 패널(반폭 35 ~ 38 mm)은 3δ(≈ 83 mm)보다 작아 V2가 늘 null이다. 스모크 · 이번 잡 모두 그랬다.
  - V1은 수치 보존 점검이라 합격 판정이 아니다.
  - 지금은 디지털워커가 "합격/불합격"을 낼 근거가 결과에 없다.

#### ST-R5 `reddish_case_build` (P1)
- 입력:
  - geometry: StepForge `part_outline_2d` 출력 또는 파트 참조
  - stack: 층 · 두께 · 재료 id
  - chemistry 프리셋, environment, uv_mask
  - edge_h: 아래 ST-R6
- 출력: 검사를 거친 case.yaml과 `placeholders: [아직 템플릿 값인 칸]`.
- 검사: 광원 창이 외곽 안에 있는가, 구멍과 겹치는가, 필수 칸이 있는가.
- 함께 앱 기본 case를 받는 길이 필요하다. 지금은 남의 스모크 잡에서 case.yaml을 복사해 썼다.

#### ST-R6 변별 경계 h 기본표 (P1)
- 관계(tied · 접착 · 간극 · 노출) + 실링 종류 → `h_m_s` 기본값.
- StepForge 외곽의 변별 이웃 정보와 합쳐 `edge_groups`를 만든다.

#### ST-R7 request.json 스키마 노출 (P2)
- `get_app_schema(part-study-registry)`에 요청서 키 · 뜻을 싣는다. `part`가 이름일 뿐이라는 점도 적는다.
- 지금은 실행기 스크립트를 읽어야 안다.

#### ST-R8 결과 숫자 칸 · 단위 (P2)
- V2 · V3에 `value_mm` · `reference_mm` 숫자 칸을 둔다.
- 정규화 설정 메아리의 `time.total_days`에 초 단위 값(1,728,000 = 20일)이 들어간다. `output_interval_days`도 같다. 칸 이름과 단위를 맞춘다.

#### ST-R9 잡 목록 소유자 (P2)
- `ste_list_jobs`에 `mine`(기본 true) · `owner` 칸을 둔다.
- 지금은 다른 사용자 잡이 섞여 보여 디지털워커가 혼동할 수 있다.

#### ST-R10 레디쉬 환경 절 (P2)
- case에 `environment {temperature_C, rh}`와 D · S의 온도 의존을 둔다.
- 신뢰성 시험 조건(고온고습 등)을 그대로 넣을 칸이 지금은 없다.

### 참고 수치(잡 db7bbee75f4f)
- 형상: 둥근 사각형 75.856 × 161.368 mm, r 8.5, 구멍 0. 메시 셀 342,168 · 절점 172,007.
- 해석 48.4 s. 변별 경계 태그 bottom 11 · right 12 · top 13 · left 14.
- V1 상대오차 0(pass). V2 37.79 mm / 34.97 mm(null, 반폭 37.9 mm < 3δ, δ = 27.57 mm).

---

## 6. 요청서 — HWAX 포탈·게이트웨이

- 작성 2026-11-17 · 받을 곳: HWAX 포탈·게이트웨이 개발 · 상태: **초안(보내지 않음)**
- 근거: 디지털워커가 MCP 도구만으로 StepForge 과제 → 레디쉬 해석을 해 본 시험(과제 A).

### 배경

레디쉬 case에는 층별 산소 확산계수(D) · 용해도(S), 환경(온도 · 습도 · 조도 · 기간)이 들어간다. 시험에서는 모두 템플릿 값을 그대로 썼다.

- 재료 카탈로그 앱에는 해당 물성 키가 있고 값도 등록돼 있다. 산소투과도 105종, 확산계수 59종, 헨리 용해도 19종(`catalog_property_distribution`으로 확인).
- 그런데 디지털워커가 "이 층의 D · S"를 한 번에 받을 길이 없다.
- 신뢰성 시험 조건은 개인 토큰이 등록되지 않은 사용자에게는 조회가 막힌다.

### 요청

#### PT-R1 `material_gas_transport` (P1)
- 입력: `material_ids`, `temperature_K`, `species`(기본 O2).
- 출력: 재료별 `{D_m2_s, S_mol_m3_Pa, P_O2, source, quality_tier, conditions}`. 값이 없는 칸은 null + 사유.
- 재료 카탈로그 앱의 물성 키(확산계수 · 헨리 용해도 · 산소투과도)를 묶어 부르는 게이트웨이 도구다. D · S 중 하나가 없고 투과도가 있으면 P = D · S로 나머지를 추정하되, 추정임을 표시한다.

#### PT-R2 시험 조건 → 해석 환경 값 (P1)
- 입력: 신뢰성 시험 id → 출력 `{temperature_C, rh, lux, days}`.
- 개인 토큰이 없을 때는 지금처럼 막되, 응답에 "등록 방법"과 "공용 프리셋 조건으로 대신 받을지"를 함께 준다. 디지털워커가 사용자에게 바로 물을 수 있게 하려는 것이다.

#### PT-R3 운영본 표시 (P2)
- `list_tool_apps` 줄에 `instance`(운영/동결)와 build를 싣는다.
- 이유: 전환 뒤 옛 접두사 도구가 사라졌다. 디지털워커는 어느 이름이 운영본인지 도구 목록만으로 알 수 없어서, `system_capabilities`를 따로 불러 확인했다.

#### PT-R4 STE 잡 목록 소유자 표시 (P2, STE ST-R9와 짝)
- 게이트웨이를 거친 `ste_list_jobs` 응답에, 호출자 잡만인지 전체(관리자 시야)인지 적는다.

### 참고
- 재료 이름 ↔ 층 대응(어떤 층이 어떤 재료 id인가)은 StepForge `part_stack`(StepForge 요청서 SF-R3)에서 온다고 가정한다.
