# 리스크 심사 앱 · ODB 허브 — 심사에 ECAD(ODB 보드) 싣기 요청 (2026-10-31 · cae00 운영 기준)

요청 HWAX Portal 운영(cae00) · 대상 저장소 ① HWAXRisk(리스크 심사 앱 — cae00 런타임 `heax_app_hwax_risk` :9116, 소스 사본 `HEAXHub/var/integration_workspaces/hwax-risk/upstream/`) ② ODB 허브(게이트웨이 백엔드 `odb-hub`, 박스 밖) · 기준 판 리스크 앱 작업 사본 HEAD `ecad8c8`(10-21, 지금 깔린 SIF 의 `/app` 과 같은 판, 파일:줄은 `backend/app/` 기준) · 게이트웨이 `/tools-map` 10-31(백엔드 `odb-hub` 도구 39개) · 대조 10-31 — 표본 보드 둘(보드 1 · 보드 2)에 odb-hub 읽기 도구를 실제로 불러 계약 필드마다 맞춰 보고, 따로 다시 불러 반박해 본 결과만 적었다(쓰기 · 잡 시작 호출은 하지 않았다) · update-all 로 받는 플랫폼: 리스크 앱은 예(HEAXHub 앱 SIF), ODB 허브는 아니오.

항목 번호 가운데 제품 코드처럼 읽힐 수 있는 것(S · A · M · X · P 로 시작하는 짧은 번호)은 원문 번호에 '-' 를 넣어 적었다(예 계획 단계 P-7).

**한 줄**

- 리스크 심사는 ECAD 를 한 번도 싣지 못했다. ECAD 어댑터가 계약 도구 4개(`odb_get_board` · `odb_list_components` · `odb_list_nets` · `odb_get_stackup`)를 기다리는 스텁이고, 그 이름의 도구는 어디에도 없다. 그래서 스냅숏은 늘 `missing.ecad_absent=true` 다. 권한 문제가 아니다.
- 심의는 게이트웨이의 odb-hub 도구 39개를 이름 그대로 부르므로 같은 보드를 읽는다. 리스크 앱만 못 읽는다.
- 계약 문서가 전제한 「ODB 허브는 게이트웨이 백엔드가 없다」는 이제 사실이 아니다. 게이트웨이에 백엔드 `odb-hub` 로 39개가 붙어 있다.
- 지금 도구로 적층 · 보드 요약 · 분류된 부품 목록은 보드 하나에 열 번 남짓으로 채운다(1단계, 리스크 앱 몫). 부품 좌표와 넷은 부품 · 넷마다 한 번씩 불러야 하고, 넷 목록은 200건에서 말없이 잘린다. 이것은 ODB 허브가 묶음 읽기를 내야 풀린다(2단계).

**건수**

| 대상 | 높음 | 중간 | 낮음 · 선택 | 질문 | 결정 필요 |
|---|---|---|---|---|---|
| HWAXRisk | 3 | 3 | 0 | 0 | 0 |
| ODB 허브 | 2 | 2 | 1 | 0 | 0 |
| **합계** | **5** | **5** | **1** | **0** | **1** |

결정 필요 1건은 사용자 몫이다(5절).

## 1. 지금 상태(실측)

| 항목 | 값 |
|---|---|
| 어댑터 | `adapters/ecad_stub.py` 가 전부다. `REQUIRED_TOOLS = ("odb_get_board", "odb_list_components", "odb_list_nets", "odb_get_stackup")` 이고, `capture` 는 어떤 도구도 부르지 않고 빈 결과와 `degraded: ['ecad_absent']` 를 낸다. `adapters/ecad.py` 는 없다. |
| 발견 | `adapters/registry.py:40` 이 위 4개 이름 집합으로 찾고, `:32` 이 ecad 를 `status="contract_only"` 로 둔다. `:70-73` 은 도구가 다 보여도 `contract_only` 라고 적는다. |
| 대상 | 과제 대상에 ECAD 보드를 담는 칸이 없다. 캡처는 ecad 에 빈 ref 를 넘긴다(`registry.py:287-288` `adapter_for("ecad").capture({}, …)`). |
| 계약 문서 | `docs/odb-adapter-contract.md`(정본은 포털 `docs/design-risk-review/plan.md` §2.5.3 · §2.13.5). 「ODB hub 는 HEAXHub 에 `external_link` 앱으로만 있고 게이트웨이 백엔드가 없다」 고 적혀 있다. |
| 게이트웨이의 odb-hub | 백엔드 `odb-hub` 39개다. 다른 앱과 이름이 겹친 둘만 접두가 붙는다 — `odbhub_list_jobs` · `odbhub_list_parts`. 나머지(`find_job` · `get_board_layers` · `check_job_stackup` · `get_stackup` · `get_part_detail` · `get_parts_summary` · `find_nets` · `get_net` · `get_volume_result` · `get_odb_download` 등)는 이름 그대로다. |
| 심의 | 좌석이 위 도구를 이름으로 부른다. 그래서 「심의는 되는데 리스크 심사는 안 된다」 로 보인다. |

## 2. HWAXRisk — 할 일

| # | 등급 | 무엇이 | 근거 | 할 일 |
|---|---|---|---|---|
| ER-01 | 높음 | 과제 대상에 ECAD 보드를 붙일 길이 없다. | `registry.py:287-288` 이 빈 ref 를 넘긴다. 계약의 `job_ref` 는 ODB 허브가 발급한 불투명 문자열이고, 지금 그것은 odb-hub 의 `job_id`(16자리 16진)다. `find_job(query)` 가 과제 · 모델 · 파일 이름이나 `job_id` 로 보드를 찾아 준다(10개까지, `truncated` 표지). 같은 모델의 다른 판이 함께 나올 수 있다. | 과제 대상에 ECAD 보드(`job_id`)를 담는 칸을 둔다. 고를 때는 `find_job` 결과를 사람에게 보여 고르게 한다(모델 이름만으로 정하지 않는다). |
| ER-02 | 높음 | 발견 조건이 없는 이름 4개다. | 1절. 게이트웨이 이름은 다른 앱이 같은 이름을 들이면 접두가 붙어 바뀐다(지금 `list_jobs` · `list_parts` 가 그렇다). | 이름 대신 `/tools-map` 의 `map`(도구 → 백엔드)에서 백엔드 `odb-hub` 와 원래 이름으로 찾는다. 1단계에 필요한 것은 `find_job` · `get_board_layers` · `check_job_stackup` · `get_volume_result` · `get_odb_download` · `list_parts`(게이트웨이 이름 `odbhub_list_parts`)다. 다 있으면 `status` 를 `contract_only` 에서 실제 상태로 바꾼다. |
| ER-03 | 높음 | `adapters/ecad.py` 가 없다. | 계약 §2.13.5 는 P-7 에서 스텁을 대체한다고 적었다. 부록 A 대로 지금 도구로 채울 수 있는 칸이 많다. | 1단계 어댑터를 만든다. 보드 1장에 `find_job` 1 · `get_board_layers` 1 · `check_job_stackup` 1 · `get_volume_result` 1 · `get_odb_download` 1 · `odbhub_list_parts` 100행씩(보드 1 은 8쪽)으로 board · layer · component(좌표 · 넷 없이) 노드를 만든다. 넷 노드와 component→net 엣지는 2단계다. |
| ER-04 | 중간 | 지금 도구로 못 채우는 칸이 있다. | 부록 A 의 「없음」 · 「일부」 행. | 지어내지 않고 `degraded` 로 남긴다. 제안 표지는 `ecad_nets_deferred` · `component_xy_deferred` · `components_unclassified_omitted` · `outline_origin_unknown` · `stackup_material_unmatched` · `copper_weight_absent` · `plane_type_unknown` · `odb_version_absent` · `component_value_absent` · `component_height_partial` 이다. 단위는 허브가 mm 로 맞춰 주므로 `unit_converted_mil` 은 나오지 않는다. |
| ER-05 | 중간 | 계약 문서와 정본 계획이 지금과 다르다. | 1절 계약 문서 행. | `docs/odb-adapter-contract.md` 의 「P-0 에서의 상태」 와 포털 `plan.md` §2.5.3 · §2.13.5 를 지금 도구 이름 · 발견 방식 · 두 단계로 고친다. ECAD 의존 도메인 6(`pcb · pwr · rf · soc · passive · mem`)을 1단계 뒤 어디까지 `deferred` 에서 풀지도 적는다. |
| ER-06 | 중간 | 좌표 · 넷을 지금 도구로 다 채우면 호출이 너무 많다. | 부품 좌표는 `get_part_detail` 을 부품마다 한 번 불러야 한다(보드 1 약 760번, 보드 2 약 535번). 넷은 `find_nets` 가 200건에서 잘리고 핀 수는 넷마다 `get_net` 한 번이다(부록 B). | 2단계는 ODB 허브의 OH-01 · OH-02 가 들어온 뒤에 한다. 그 전에 꼭 필요하면 핀 수 상위 부품만 `get_part_detail` 로 읽고(호출 상한을 둔다), `component_xy_partial` 을 남긴다. |

## 3. ODB 허브 — 할 일

| # | 등급 | 무엇이 | 근거(10-31 실측) | 할 일 |
|---|---|---|---|---|
| OH-01 | 높음 | `find_nets` 가 200건에서 말없이 자른다. | `find_nets(q='', limit=20000)` 이 두 보드 모두 `count=200` 이다. 응답은 `{job_id, nets[], count}` 뿐이고 total · offset · has_more 가 없다. 잘린 끝에서도 feature_count 가 줄어드는 중이라 두 보드 모두 200 넘게 넷이 있다. 정렬이 (feature_count 내림, 이름 오름)이라 동점 묶음 가운데서 잘린다. 심의 좌석도 같은 도구를 부르므로 같은 일을 겪는다. | offset · total · has_more 를 낸다. 자를 때는 `truncated: true` 와 상한을 적는다. 넷마다 핀 수(`pin_count`)를 목록에 함께 싣는다(지금은 `get_net` 을 넷마다 불러야 한다). |
| OH-02 | 높음 | 부품을 한 번에 읽는 길이 없다. | `list_parts` 는 page_size 를 5000 으로 줘도 100 으로 줄이고, 좌표 · 회전 · 넷이 없다. 분류되지 않은 부품(저항 · 테스트 포인트 등, category `Unknown`)을 빼고 그 범주로 거를 수도 없다(`category='Unknown'` 은 오류). 보드 1 은 목록 748개, 실제 배치 924개다(`get_volume_result` 의 counted). 보드 2 는 528개와 702개다. | `list_parts` 에 분류 안 된 부품 포함 선택지 · x · y · rotation · mirror · 넷 이름(넷당 1개) 칸을 두고, page_size 를 2000 까지 받는다. |
| OH-03 | 중간 | 넷이 200개 넘는 부품은 넷을 다 얻지 못한다. | `get_part_detail.nets` 는 200개에서 자르고(`nets_truncated`), `find_nets(refdes=…)` 도 200 이다. 둘의 정렬이 달라(앞은 ASCII 순, 뒤는 feature_count 순) 넷 203개짜리 부품은 앞의 결과가 소문자 그라운드 넷을 빼먹었다. 넷 450개짜리 부품은 둘을 합쳐도 다 못 얻는다. | 부품 하나의 넷 전체를 내거나 offset 을 받는다. |
| OH-04 | 중간 | 보드 외곽을 부품 좌표와 같은 기준으로 내지 않는다. | `get_volume_result.board` 는 폭 · 높이 · 면적만 준다. 부품 · 구멍 좌표는 ODB step 기준이라 보드마다 원점이 다르다(보드 1 은 음수 좌표, 보드 2 는 한쪽으로 치우친 좌표). | 외곽 bbox(min · max, 부품 좌표와 같은 기준)를 낸다. |
| OH-05 | 낮음 · 선택 | 보드 단위로 있으면 좋은 값이 없다. | 넷 총수(OH-01 이 풀면 됨) · ODB++ 형식 판 · 넷 분류 · 동박층의 plane 구분(두 보드 모두 동박층이 다 `SIGNAL`) · 원판 동박 무게(지금은 도금을 포함한 완성 두께뿐) · 부품 높이 전체(지금은 `get_volume_result` 의 큰 부품 10개씩)를 어느 도구도 내지 않는다. | ODB 에 있는 것만이라도 낸다. 없으면 없다고 문서에 적는다. |

## 4. 두 단계

| 단계 | 누가 | 무엇이 들어오나 | 보드 1장 호출 수 |
|---|---|---|---|
| 1단계 | HWAXRisk(ER-01~ER-05) | board 1건, layer(5종으로 거른 행), component(분류된 부품, 좌표 · 넷 없이). `ecad_absent` 가 사라지고 빠진 칸은 표지로 남는다. | 약 13번(보드 1 기준) |
| 2단계 | ODB 허브(OH-01 · OH-02, 가능하면 OH-03 · OH-04) 다음 HWAXRisk(ER-06) | component 좌표 · 넷, net 노드, component→net 엣지, 분류 안 된 부품. | 묶음 읽기 몇 번 |

## 5. 결정 필요 (사용자)

| # | 정할 것 | 안 | 권장 |
|---|---|---|---|
| D-1 | 2단계를 어느 쪽으로 할지. | (가) ODB 허브가 지금 도구에 묶음 읽기를 더한다(OH-01~OH-04). 리스크 앱은 부록 A 대로 맞춘다. (나) ODB 허브가 계약 4도구를 새로 낸다. 리스크 앱 계약이 그대로 맞는다. | (가). 200건에서 말없이 잘리는 일은 심의 · 챗도 같이 겪으므로 지금 도구를 고치는 쪽이 모두에게 낫다. 도구 수도 늘지 않는다. |

## 6. 다시 볼 시험

| 시험 | 언제 | 통과 기준 |
|---|---|---|
| 1단계 캡처 | ER-01~ER-03 이 든 SIF 를 받은 뒤. | ECAD 보드를 붙인 과제를 캡처했을 때 `missing.ecad_absent` 가 없고, component 노드 수가 `odbhub_list_parts` 의 total 과 같고, layer 노드가 `get_board_layers` 를 5종으로 거른 행 수와 같다. 빠진 칸은 ER-04 표지로 남는다. |
| 넷 목록 | OH-01 이 들어온 뒤. | `find_nets` 를 offset 으로 끝까지 읽었을 때 total 과 받은 수가 같고, 잘렸으면 표지가 있다. |
| 부품 묶음 | OH-02 가 들어온 뒤. | 분류 안 된 부품을 포함한 목록 수가 `get_volume_result` 의 배치 수와 같다. |

## 부록 A. 계약 필드 → 지금 도구(10-31 실측 · 반박 확인)

상태: 그대로 = 값을 옮기면 된다 · 유도 = 바꾸거나 계산해야 한다 · 일부 = 일부만 있거나 뜻이 조금 다르다 · 없음 = 어느 읽기 도구에도 없다. 도구 이름은 게이트웨이 이름이다.

### `odb_get_board`

| 필드 | 상태 | 도구 · 경로 | 변환 · 주의 |
|---|---|---|---|
| board_id | 그대로 | `find_job` · `odbhub_list_jobs` 의 `job_id` | 그대로 쓴다. |
| name | 유도 | `find_job(query=<job_id>)` 의 project · model · board_type · revision | 엮어 만든다. `job_name` · `step_name` 은 쓰지 않는다(최근 100건 가운데 37건 · 58건이 같은 기본값이다). |
| units | 유도 | `get_net.units`, 모든 기하 키가 `_mm` · `_um` | 늘 mm 다. 허브가 인치 ODB 도 mm 로 바꾼다. |
| outline_bbox | 일부 | `get_volume_result.board.x_mm` · `y_mm` · `outline_area_mm2` | 폭 · 높이뿐이고 원점이 없다(OH-04). |
| thickness | 그대로 | `get_board_layers.total_thickness_mm`(+ `check_job_stackup.verdict`) | 도구 설명이 ODB 두께가 자주 틀린다고 적으므로 verdict 를 함께 싣는다. |
| layer_count | 그대로 | `get_board_layers.signal_layer_count` 또는 `check_job_stackup.layer_count` | `get_board_layers.layer_count` 는 쓰지 않는다. 부품 · 실크 · 페이스트 · 드릴 · 문서 층까지 센다(보드 1 은 35, 동박층은 10). |
| n_components | 유도 | `get_volume_result` 의 top · bottom count, 또는 `odbhub_list_parts.total` | 두 값이 약 30% 다르다(분류 안 된 부품). 어느 쪽인지 정해 적는다. |
| n_nets | 없음 | `find_nets.count` 는 200 을 넘지 못한다 | 아래 한도만 안다(OH-01). |
| odb_version | 없음 | — | `revision` 은 설계 판이고 형식 판이 아니다. |
| source_hash | 그대로 | `get_odb_download.sha256`(+ `size_bytes`) | 두 보드 모두 `job_id` 가 sha256 앞 16자리와 같다. 한 번 더 부른다. |

### `odb_list_components`

| 필드 | 상태 | 도구 · 경로 | 변환 · 주의 |
|---|---|---|---|
| side(거르기) | 그대로 | `odbhub_list_parts(side='top'\|'bottom')` | 비우면 양면이다. |
| offset · limit | 유도 | `odbhub_list_parts(page, page_size)` | 한 쪽 100행으로 줄어든다. offset 을 쪽 번호로 바꾸고 남는 것은 앱이 자른다. |
| items(목록) | 일부 | `odbhub_list_parts.rows[]` | 분류된 부품만 나온다(OH-02). |
| refdes | 그대로 | `rows[].refdes` | — |
| part_number | 그대로 | `rows[].part_name` | ODB 의 부품 이름이다(자재 코드이거나 라이브러리 이름). |
| footprint | 그대로 | `rows[].pkg_name`(= `get_part_detail.footprint_name`) | — |
| side | 그대로 | `rows[].side` | 이미 `top` · `bottom` 이다. |
| x · y | 일부 | `get_part_detail.x` · `y` | 부품마다 한 번 부른다. mm, ODB step 기준이라 보드 원점 기준이 아니다(OH-04). |
| rot | 유도 | `get_part_detail.rotation`(+ `mirror`) | 부호 있는 도(-0.0 · -90 · -180 꼴)라 [0,360) 으로 맞춘다. |
| pin_count | 그대로 | `rows[].pin_count` | — |
| nets[] | 일부 | `get_part_detail.nets`(+ `net_count` · `nets_truncated`) | 넷 200개 넘는 부품은 다 못 얻는다(OH-03). |
| height | 일부 | `get_volume_result.{top,bottom}.largest_items[].height_mean_mm` | 면마다 큰 부품 10개만 나온다. 서버에는 다 있다(`missing_height=0`). |
| value | 없음 | — | `part_name` 은 자재 코드라 값으로 바꾸려면 밖의 부품 자료가 필요하다. |
| total | 일부 | `odbhub_list_parts.total` | 분류된 부품 수다. |
| next_offset | 유도 | `has_more` · `page` · `returned` | — |
| component→net 엣지 | 일부 | `get_part_detail.nets` | 넷당 1건이다. nets[] 와 같은 한도다. |

### `odb_list_nets`

| 필드 | 상태 | 도구 · 경로 | 변환 · 주의 |
|---|---|---|---|
| net_name | 일부 | `find_nets.nets[].name` | 200건에서 잘린다. 지금은 q(대소문자 무시 부분 일치)로 나눠 여러 번 부르고 합치는 수밖에 없다(OH-01). 자리표시 넷 `$NONE$` 은 뺀다. |
| pin_count | 그대로 | `get_net.pin_count` | 넷마다 한 번 부른다. `find_nets.feature_count` 는 핀 수가 아니다(층 수 × 패드 수). |
| layers[] | 유도 | `find_nets.nets[].layers[]` 를 `get_board_layers` 의 층 타입으로 거른다 | 마스크 · 페이스트 · 드릴 구간까지 섞여 온다. 실제 배선 층은 `get_net.layers[].segments > 0` 이다. |
| net_class | 없음 | — | 이름으로 짐작하는 것은 ODB 자료가 아니므로 넣지 않는다. |
| total · next_offset | 일부 | — | `find_nets` 에 offset · total 이 없다(OH-01). |

### `odb_get_stackup`

| 필드 | 상태 | 도구 · 경로 | 변환 · 주의 |
|---|---|---|---|
| idx | 유도 | `get_board_layers.layers[]` 의 순서 | 위에서 아래로 물리 순서다. 5종으로 거른 뒤 번호를 매긴다(보드 1 은 23행, 보드 2 는 19행). |
| name | 그대로 | `get_board_layers.layers[].name` | 표준 적층 이름(L1 · L1-L2 꼴)은 `check_job_stackup` 에 있다. |
| type | 유도 | `get_board_layers.layers[].type` | SIGNAL→signal · POWER_GROUND→plane · DIELECTRIC→dielectric · SOLDER_MASK→soldermask · SILK_SCREEN→silkscreen, 나머지는 뺀다. 두 보드 모두 동박층이 다 SIGNAL 이라 plane 이 나오지 않는다. |
| thickness | 그대로 | `layers[].thickness_um` | µm 다. 실크 층은 null 이다. |
| material | 일부 | `check_job_stackup.layers[].material`(또는 `get_stackup`) | 표준 적층과 맞을 때만 있다. 보드 2(`non_standard`)는 비어 있다. 값은 보드 ODB 가 아니라 맞춘 표준 적층에서 온다. |
| copper_weight | 일부 | 동박층 `thickness_um` | 무게 칸은 없다. 바깥층은 도금을 포함한 두께라 원판 동박 무게가 아니다. |
| ecad_stackup_total | 유도 | 5종 행 두께 합 = `total_thickness_mm` × 1000 | 두 보드 모두 같았다. `check_job_stackup.verdict` 를 함께 싣는다. |

## 부록 B. 이렇게 확인했다

- 10-31 에 표본 보드 둘(최근 올라온 보드 가운데 추출 · 체크리스트가 끝난 것 하나와 적층이 표준과 다른 것 하나)에 odb-hub 읽기 도구만 불렀다. 계약 도구 하나마다 한 명이 맞춰 보고, 다른 한 명이 같은 도구를 다시 불러 반박했다. 반박으로 바뀐 것은 넷 목록 상한(한 번에 다 받을 수 있다 → 200 에서 잘림), 부품 넷(그대로 → 일부), 부품 높이(없음 → 일부), 원본 해시(없음 → 그대로), 동박 무게(유도 → 일부), 보드 이름에 `step_name` 을 쓰지 않기다.
- 상한은 이렇게 쟀다. `find_nets` 는 limit 5001 · 20000 에서 count 200 이었다. `odbhub_list_parts` 는 page_size 5000 이 100 으로 돌아왔다. `get_part_detail.nets` 는 넷 203개 부품에서 200 이었다.
- 어느 값도 쓰거나 바꾸지 않았다.
