# 레디쉬 · 결로 연계 — 포털 · 게이트웨이 몫 계획

> 원문은 `reddish-request.md` 6장(PT-R1 ~ R4)과 `condensation-request.md` 3장(P-1 ~ P-3)이다. 결정과 까닭은 `context-notes.md`, 할 일 상자는 `checklist.md` 에 둔다.
> 사용자 결정(11-18) — 포털 · 게이트웨이 몫을 전부 시작한다.

## 무엇을 왜

디지털워커가 MCP 도구만으로 StepForge 형상을 ste 해석에 넣으려다, 사람이 셸로 끼어든 곳이 셋 있었다. 이 계획은 그 셋을 게이트웨이 도구로 메운다.

1. 파일을 StepForge 에서 ste 로 옮기기. MCP 받기 상한이 1 MB 이고 공유 경로가 없었다.
2. 층 재료의 가스 투과 물성. 카탈로그에 값은 있는데 한 번에 받을 길이 없었다.
3. 신뢰성 시험 조건을 해석 환경 값으로 바꾸기.

## 항목

### P-1 — `artifact_to_ste_upload` (P0, 게이트웨이 로컬 도구 — 지음 `ec91b62`)

- 입력: `project_id` · `kind` · `ref`(선택 — 비우면 그 kind 의 가장 최근 것, StepForge `download_artifact` 와 같은 규칙) · `filename`(선택) · `upload_id`(선택 — 같은 업로드에 파일을 더 넣을 때).
- 흐름(모두 **부르는 사람 명의**)
  1. StepForge `download_artifact(content="base64", offset=0)` 을 그 사람 명의로 부른다. 파일 이름 · 크기 · `file_sha256` 이 온다.
  2. `upload_id` 가 없으면 ste `POST /api/uploads` 를 그 사람의 위임 PAT 로 부른다(게이트웨이 `rest.ste` 의 per_user 길).
  3. ste `PUT /api/uploads/{id}/{filename}` 을 **같은 위임 PAT**(업로드 주인 계정)로 연다. 본문은 StepForge 조각을 `offset` 차례로 받아 풀어 흘려 보낸다. ste 의 티켓은 받지도 쓰지도 않는다.
  4. 조각마다 `file_sha256` 이 처음과 같은지 본다. 마지막 조각 뒤에는 흘려 보내며 잰 sha256 과 맞댄다. 다르면 본문 생성기가 예외를 던져 PUT 을 끊는다. 그러면 ste 가 `.part` 를 지워 반쯤 올라간 파일이 남지 않는다.
  5. 답: `{upload_id, filename, bytes, sha256, expires_at, source:{project_id, kind, ref}, next}`. `next` 는 `ste_submit_job(app, upload_id)` 안내 한 줄이다.
- 권한: 그 사람이 StepForge 와 ste 둘 다 쓸 수 있어야 한다(게이트웨이 접근 판정 그대로). 서비스 PAT 로는 부르지 않는다(ste 업로드 주인 = 제출자).
- 바이트는 모델 · 인자 · 로그에 남지 않는다. 감사에는 크기 · sha256 · 출처만 남긴다.
- SF-R1(파트 하나 STEP)이 생기기 전에도 쓸 수 있다. 지금 있는 산출물(stl · worked_step · 공동 STEP 등)이면 된다.

### PT-R1 — `gas_transport_lookup` (P1, 게이트웨이 로컬 읽기 도구 — 지음 `6dcef62`)

- 요청서의 이름은 `material_gas_transport` 이다. 그런데 `material_` 은 심의 좌석 자유 조회가 여는 접두(에이전트 `_FREE_ALLOW`)라, 그 이름이면 리스크 심사 · 심의 좌석에 새 길이 열린다(D-18). 그래서 이름을 바꿨다(SS-5).
- MaterialTwin(`heax-materialtwin_web`) `get_material_properties(material_id, domain="physical")` 를 재료마다 부르는 사람 그대로 부른다.
  키 셋은 `physical.diffusion_coefficient`(m^2/s) · `physical.gas_solubility`(mol/(m^3*Pa)) · `physical.gas_permeability_o2`(mol/(m*s*Pa))이다.
  `conditions.species` 로 거른다. 카탈로그의 대표값 도구는 기체를 가리지 않아 확산계수 대표값이 물일 수 있다.
- 한 재료 안에도 시료가 다른 행이 있다(`grade_scope` — '상한으로만 써라' · '평균 내지 마라'). 그래서 고른 값과 `alternatives`(다른 후보 다섯까지)를 함께 싣고, 경고 칸은 그대로 넘긴다.
- 고르기: `temperature_K` 를 주면 가까운 온도가 먼저이고 그다음이 등급이다. 안 주면 등급이 먼저이고 그다음이 23 °C 에 가까운 것이다. 외삽하지 않는다.
- P = D·S 는 고른 D · S 가 같은 시료(`grade_scope` 같음)이고 온도가 1 K 안일 때만 셈해 `derived` 로 표시한다. 단위가 다른 행은 환산하지 않고 센다(permeance · OTR 은 다른 양).

### PT-R2 · P-2 — `reliability_test_conditions` (P1, 게이트웨이 로컬 읽기 도구 — 지음 `dd304eb`)

- TestScope 에는 온도 · 습도 · 기간 전용 칸이 없다. 값 행(`attributes[]`)에는 키도 없다. 그래서 셋을 그 사람 토큰으로 불러 잇는다.
  `get_reliability_test`(값 — `definition_id`) → `list_attribute_definitions(target=reliability_test)`(정의 → `condition_key_id`) → `list_conditions`(→ `temperature` · `humidity` · `duration` · `cycles`).
- 단계(`set_label` · `step_order`)마다 `temperature_C` · `rh_pct` · `duration_h` · `cycles` 를 목록으로 준다. 값 하나이거나 min · max 이고, 원문 표시 `display` 를 함께 싣는다.
  - 아는 단위만 바꾼다. 모르는 단위는 `other_attributes` 로 그대로 보인다.
  - 초안은 `draft` 로 표시하고, 지난 판은 뺀다.
- 조도(lux)는 TestScope 조건 어휘에 없어 늘 null 이다.
- 토큰이 없으면 `needs_connect` 와 등록 안내, 그리고 "사람에게 묻는다" 를 답한다. 요청서의 "공용 프리셋" 은 정의된 것이 없어 만들지 않았다(SS-6).
- dev 게이트웨이에는 TestScope 가 붙어 있지 않다. 소스의 꼴로 짓고 시험했다 — 실물 확인은 cae00 이다.

### PT-R3 · P-3 — 운영본 표시 (P2)

- GW-05(게이트웨이 `fd1f52d`, 11-17 07:34)가 이미 `list_tool_apps` 줄마다 `env`(dev · prod) · `canonical` · `aliases`를 싣는다. 옛 접두 이름(`stepforgeprod_…`)을 부르면 새 이름을 안내한다. 11-17 시험 때 cae00 게이트웨이가 이 판 이전이었다(`unknown tool` 만 받음).
- 남은 것은 `build` 하나다. 허브 서버 목록(`/api/v1/mcp/servers`)에 앱 커밋이 없다. HEAXHub 에 칸을 청하고, 생기면 게이트웨이가 그대로 싣는다.

### PT-R4 — ste 잡 목록의 '내 잡' (P2)

- 게이트웨이는 ste 를 그 사람 명의로 부른다. ste ST-R9 가 항목마다 `mine` 을 실으면 게이트웨이가 바꿀 것은 없다. ste 판이 나오면 확인만 한다. `owner` 는 싣지 않는다(ste PA-20).

## 차례

1. P-1 · PT-R1 · PT-R2 — 게이트웨이에 지음(시험 1,100 통과). 남은 것은 dev 실호출과 올리기다.
2. PT-R3 `build` — HEAXHub 답 뒤. PT-R4 — ste 판 뒤 확인.

## 11-21 재시험 뒤 남은 것 — `retest-1121-request.md`

> 운영 박스의 디지털워커가 StepForge D-707 판으로 같은 사슬을 다시 돌린 결과다(사용자가 11-22 에 붙여 넣음 — 「적합한 세션에서 처리하게」). 파트 STEP 반출과
> 산출물 경로 표시는 풀렸고, part-study 가 얇은 판 둘에서 outline 에 멈추는 것 · 공동을 못 만드는 것 · 레디쉬 입력이 템플릿 값인 것이 남았다.

### 받을 곳

| 받을 곳 | 세션 | 항목 |
|---|---|---|
| StepForge | `stepforge-d4` | SF-1 ~ SF-12(P0 는 SF-1 `build_cavity` 파트 목록 · 접수 검사, SF-2 `part_outline_2d` 의 deflection 의존, SF-3 실제 공동에서 개구부 · 찬 면) |
| ste | `smarttwinexplorer-06` | ST-1 ~ ST-17 가운데 ste 코어 몫(잡 상태 · MCP 도구 · 스키마 · 잡 환경에 주소와 토큰 넣기 — ST-3 · ST-4 · ST-5 · ST-12 · ST-14 · ST-16 으로 어림) |
| 브리지 · 앱 래퍼 | `koosolvercontainer-da` | BG-1 · BG-2 · BG-6 과 ST 가운데 앱 래퍼 · 해석기 스크립트 몫(ST-1 · ST-2 · ST-6 ~ ST-11 · ST-13 · ST-15 · ST-17 로 어림) |
| 게이트웨이 · 포털 | 이 리포 세션 | BG-3 · BG-4 · BG-5 · PT-1 · PT-2(아래) |

ST 의 가름은 어림이다 — 11-18 에 ste 06 이 코드와 맞대 다시 갈랐다(SS-1). 이번에도 두 세션이 서로 맞춰 정한다. SF-5(둥근 사각형 ↔ 레디쉬 geometry 규약)와
ST-7(`reddish_case_build`)은 요청서가 「한 곳으로 정해 달라」 고 한 것이라 StepForge 와 브리지가 정한다.

### 게이트웨이 · 포털 몫

| ID | 급 | 지금 | 할 것 |
|---|---|---|---|
| BG-3 | P0 확인 | `artifact_to_ste_upload` 는 part_step 둘(155,360 B · 240,542 B)을 sha256 이 맞게 옮겼다. 100 MB 급과 cavity_step 은 못 봤고, 같은 업로드에 scenario.json 을 더할 길이 없다 | 큰 파일 · cavity_step 은 dev 에서 한 번 확인(조각 길 그대로인지). 작은 텍스트 파일을 업로드에 더하는 길은 ST-10 과 한 묶음이다 — ste 가 `submit_job` 에서 files 와 upload_id 를 함께 받을지, 게이트웨이가 「업로드에 텍스트 더하기」 를 둘지 ste 답을 보고 정한다 |
| BG-4 | P1 | `gas_transport_lookup` 은 S 가 없으면 비워 둔다(P · D 가 있어도 셈하지 않는다). 층 → 재료 id 연결이 없다 | S = P/D 추정(같은 시료 · 온도 1 K 안일 때만, `derived` 표지 — 지금 P = D·S 와 같은 규칙) · 요청 온도와의 차이 칸 확인. 층별 조회는 SF-4(`part_stack` 의 material_id)가 나온 뒤 재료 id 목록을 받는 지금 꼴로 된다 |
| BG-5 · PT-1 | P1 | `reliability_test_conditions` 는 있다. 개인 토큰이 없으면 `needs_connect` 로 막힌다 | 막을 때의 답에 등록 방법이 실리는지 운영 박스의 실제 답으로 확인하고 모자라면 고친다. 「공용 프리셋」 은 11-18 에 만들지 않기로 했다(SS-6) — 요청이 다시 왔으므로 사용자에게 묻는다 |
| PT-2 | P2 | `list_tool_apps` 의 StepForge 줄에 build 가 없다 | 11-18 에 받는 쪽은 지었다(`629f32c`). 떠 있는 인스턴스보다 디스크 SIF 가 새로우면 일부러 비운다 — 운영 박스에서 왜 비는지(허브 판 · 인스턴스와 SIF 의 어긋남) 받은 편지함으로 묻는다. `instance`(운영 / 동결) 칸은 허브가 주는 값이 있어야 한다 |

차례 — 통합 가지(과제 인사이트 · 절차)를 올리고 dev 를 재기동한 뒤에 한다(`../leftovers-1121/` L21-17). 게이트웨이를 여러 가지가 함께 고치는 중이다.
