# odb-hub → 열충격 SED 입력 대조표 (S0 §4)

원천은 [reference.md](reference.md)(odb-hub 쪽 정리, 2026-09-16). 그 문서 §5 를 **이쪽 실물과 대조해 고친 판**이다.
대조에 쓴 것 — ThermalShockMCP `app/schemas.py`(`SedInput`, `extra="forbid"`) · `app/ml.py`(`build_features`) ·
`data/dataset.json`(학습 294건) · HWAXRisk `docs/odb-adapter-contract.md`.

> dev 는 odb-hub 에 닿지 않는다. 아래 "확인" 칸은 **cae00 에서만** 닫힌다.

## 결론

- 필수 10개 중 **refdes 두 개만 사람이 주면** 6개(`ap_cx`·`ap_cy`·`pkg_cx`·`pkg_cy`·`pkg_x`·`pkg_y`)는 odb-hub 가 준다.
  `pad_size` 는 유력(확인 1건 남음).
- **사람이 채우는 칸** — AP refdes · PKG refdes · `pkg_type` · `ball_size` · `board_type`(검증 전).
- 원문 §5 의 두 추정은 틀렸다 — `pkg_type` 을 `pkg_name` 접두사로 유도할 수 없고, `board_type` 의 보드 전체
  top/bottom 규칙은 실데이터와 충돌한다.

## 모델이 입력을 어떻게 쓰나 — 대조의 기준

`build_features` 가 실제로 쓰는 것만 중요하다(`app/ml.py`).

| 입력 | 모델 안에서 | 그래서 |
|---|---|---|
| `ap_cx`·`ap_cy`·`pkg_cx`·`pkg_cy` | `abs_dx=|pkg_cx-ap_cx|`, `abs_dy`, `dist` **만** | 원점은 무관. **두 부품이 같은 좌표계(같은 잡)** 여야 한다. X/Y 축은 구분된다 |
| `pkg_x`·`pkg_y` | 각각 + `pkg_area` + `pkg_diag` | 축이 구분된다 — **회전된 부품은 X/Y 가 뒤바뀔 수 있다** |
| `ball_size` | `"147/250"` → `ball_d`·`ball_pitch` 로 분해 | 형식이 틀리면 스키마(`^\d{2,3}/\d{2,3}$`)가 막는다 |
| `pad_size` | 수치 그대로 | 학습 범위 **180~240** |
| `board_type`·`pkg_type`·`ap_type` | 원핫(`handle_unknown="ignore"`) | 학습에 없던 값은 **조용히 0벡터**가 된다 |

학습 데이터 분포(294건) — `board_type` FULL 192·INT 54·HALF 48 / `pkg_type` WLP 160·DIG 99·FX 35 /
`ap_type` **POP 294(전부)** / `ball_size` 5종(`147/250` 113 등) / `pad_size` 180·190·200·210·220·225·230·240 /
`pkg_x` 2.35~6.4 · `pkg_y` 2.4~6.05 / `|dx|` 0.01~12.24.

## 입력 15개

| 입력 | 필수 | odb-hub | 판정 | 근거·주의 |
|---|---|---|---|---|
| `board_type` | ✓ | `get_interposer_result` · `get_parts_summary` | **사람(검증 전)** | 원문 규칙(top/bottom 둘 다 >0 → FULL)을 보드 전체에 걸면 폰 보드는 거의 다 FULL 이다. 그런데 학습 데이터엔 HALF 가 48건·34과제다. 뜻이 "보드 전체 단면/양면" 이 아닐 가능성이 크다(예: PKG 자리의 반대면 실장). INT(인터포저 count>0)는 그럴듯하나 역시 미검증. 아래 **검증 계획** |
| `ap_cx`·`ap_cy` | ✓ | `get_part_detail(AP).x/.y` | **odb-hub**(refdes 는 사람) | AP 와 PKG 가 **같은 잡**일 때만 뜻이 있다. 인터포저 보드는 AP 와 PKG 가 서로 다른 잡에 있을 수 있다 → 그러면 거절 |
| `pkg_cx`·`pkg_cy` | ✓ | `get_part_detail(PKG).x/.y` | **odb-hub**(refdes 는 사람) | 위와 같다 |
| `pkg_type` | ✓ | — | **사람** | 어휘가 `WLP`/`FX`/`DIG` 다. `pkg_name` 접두사(`bga`·`qfn`·`dfn`·`wlp`·`fowlp`)와 대응이 없다(FX·DIG 에 해당하는 접두사가 없다). 영구 변수 |
| `pkg_x`·`pkg_y` | ✓ | `get_part_detail(PKG).pkg_width/pkg_length` | **odb-hub**(회전 확인 1건) | 학습 데이터가 "보드 축 기준" 인지 "패키지 자체 기준" 인지 모른다. `rotation` 이 ±90 이면 뒤바뀔 수 있다. 정사각(원문 표본 2.35×2.35)은 차이가 없어 표본으로는 안 드러난다 |
| `ball_size` | ✓ | — | **사람** | PKG 볼(지름/피치 µm). ODB++ 에는 PCB 랜드만 있고 패키지 볼은 없다 |
| `pad_size` | ✓ | `get_part_detail(PKG).pins[].pad` | **유력** | `r190`(원형 190) → **190** 이 학습 값 집합에 그대로 있다. 규칙: 모양이 `^r(\d+)$` 이고, PKG 핀들의 최빈값이며, 180~240 안일 때만 채운다. 아니면 사람. cae00 에서 AP/PKG 하나로 확인 |
| `project` | | 잡 `project` | odb-hub | 메타데이터(모델 입력 아님) |
| `pkg` | | `part_name` 또는 `pkg_name` | odb-hub | 메타데이터 |
| `ap_x`·`ap_y` | | `get_part_detail(AP).pkg_width/pkg_length` | odb-hub(회전 확인) | 결측 허용 — 모델이 `ap_size_known` 으로 안다 |
| `ap_type` | | — | **상수 `POP`** | 학습 294건이 전부 POP 다. `FO` 를 넣으면 원핫이 **조용히 0벡터**가 된다 — 모델이 모르는 값이다 |

## 사람이 채우는 칸 → 절차 변수

| 변수 | `why`(화면에 보일 말) | 후보 좁히기(선택 규칙 — 사람이 확정) |
|---|---|---|
| `ap_refdes` | odb-hub 는 부품 역할을 모른다(`part_name` 불투명, `device_type` 근거 부족) | `list_parts(category="IC")` 중 패키지 면적 최대 — **AP 가 가장 큰 IC 라는 가정은 미검증** |
| `pkg_refdes` | 같다 | `list_parts(category="IC")` 중 `pkg_width`·`pkg_length` 가 학습 범위(2.35~6.4 × 2.4~6.05) 안 |
| `pkg_type` | SED 어휘(WLP/FX/DIG)가 ODB 에 없다 | — |
| `ball_size` | 패키지 볼 치수는 ODB 에 없다 | 학습 5종을 선택지로 준다(형식 오류를 원천 차단) |
| `board_type` | 판정 규칙 미검증 | (검증되면 유도로 바꾼다) |

## board_type 검증 계획 (cae00)

라벨이 있는 데이터가 **이미 있다** — 학습 294건에 `project`·`board_type` 이 있다. odb-hub 에는 잡 108개에 `project` 가 있다.

1. 294건의 `project` 로 `find_job(query=…)` → 잡을 찾는다(정확일치만 채택)
2. 찾은 잡마다 원문 규칙을 건다 — 인터포저 count>0 → INT, top/bottom 둘 다 >0 → FULL, 아니면 HALF
3. 라벨과 **혼동행렬**을 낸다. 규칙이 라벨을 재현하면 유도로, 못 하면 사람 칸으로 확정한다

⚠ 과제명은 결과에 남기지 않는다(공개 리포). 혼동행렬 숫자만 커밋한다.

## 워피지 입력 5개 (`pcb_warpage_surrogate`)

| 입력 | 필수 | odb-hub | 판정 |
|---|---|---|---|
| `board_thickness_mm` | ✓ | `check_job_stackup.thickness_mm` | **odb-hub** — 단 `verdict` 가 `standard` 가 아니면 원문 말대로 "ODB 두께가 틀렸다는 신호" 다. `notes` 에 올리고 `suggestions` 를 보인다 |
| `copper_imbalance_pct` | ✓ | `run_analysis(copper)` → `get_task` → `get_copper_result` | **산식 미정** — 성공 응답 표본이 없다(원문엔 미실행 봉투만 있다). 표본 1건 필요 |
| `stackup_asymmetry` | ✓ | `check_job_stackup.layers[]` | **산식 미정** — 데이터는 있다(층별 두께·자재) |
| `diagonal_mm` | | `get_volume_result.board.x_mm`·`y_mm` | odb-hub — `hypot`. 체적 분석이 안 된 잡이면 봉투형 오류일 것(미확인) |
| `peak_temp_c` | | — | 사람(공정 조건) |

## HWAXRisk 어댑터 계약 4도구 대조

계약(`HWAXRisk/docs/odb-adapter-contract.md`)이 가정한 이름은 **하나도 없다.** 계약 개정은 HWAXRisk 쪽 일감이다.

| 계약 | odb-hub 실제 | 차이 |
|---|---|---|
| `odb_get_board` | 없음 — `list_jobs`/`find_job` 메타 + `get_board_layers` + `get_volume_result.board` 조합 | 계약의 `units: mm\|mil` 선언은 필요 없다(항상 mm). `n_nets`·`source_hash` 는 없다 |
| `odb_list_components` | `list_parts` | **`x`·`y`·`rot`·`nets[]` 가 없다** — 좌표는 부품마다 `get_part_detail` 을 따로 불러야 한다. `height`·`value` 없음. 페이지 방식도 `page` 다(계약은 `offset`) |
| `odb_list_nets` | **없음** | 넷은 `get_part_detail.pins[].net` 으로만 보인다. 보드 전체 넷 목록 도구가 없다 |
| `odb_get_stackup` | `get_board_layers` / `check_job_stackup` | 층 타입 어휘가 다르다 — 계약 5종(`signal`·`plane`·…) vs odb-hub 9종(`SIGNAL`·`POWER_GROUND`·…). `copper_weight` 없음 |

## 쓰기·부수효과 도구 (절차 저장 시점 판정의 odb 쪽 정본)

| 도구 | 성격 | 절차에서 |
|---|---|---|
| `run_checklist`·`run_analysis`·`run_compare` | 비동기 · 결과 **덮어쓰기**(파괴 아님) · `task_id` 반환 | `get_task` 폴링이 뒤따른다. 수십 초~수 분 → 제출·회수를 가르거나 폴링 단계를 둔다 |
| `get_managed_parts` | 이름은 읽기인데 **결과를 저장한다**(원문 §4.16 `created_by: mcp`) | 파괴가 아니라 게이트는 필요 없다. 원장에는 부수효과로 적는다 |
| 업로드·삭제 | MCP 에 **없다** | 절차 밖(웹 UI) |

## 우리 쪽에 걸리는 것

| 무엇 | 상태 |
|---|---|
| 게이트웨이가 `get_` 접두를 300초 캐시 → `get_task` 폴링이 옛 상태를 본다. 이미 붙은 앱의 잡 조회 7개도 같았다 | **고쳤다**(HWAXMcpGateway) — 상태·잡 조회는 캐시하지 않는다 |
| 봉투형 오류(200 + `error`)는 `isError` 가 아니라 캐시에 들어갔다 — 일시적 실패가 5분간 굳는다 | **고쳤다**(같은 커밋) |
| 포털의 캐시 규칙 사본이 7개 접두뿐(게이트웨이 27개) · 대조 검사가 한 방향만 봐서 통과했다 | **고쳤다**(HWAXPortal) |
| `get_violation_map` 빈 배열 = "위반 없음" 또는 "미실행" | 어댑터가 `list_results` 로 먼저 가른다 |
| 봉투형 오류 판정 | 포털 판정기가 원문 §4.13 을 실패로 잡는다(`ok=False, layer=envelope, kind=error_key`) — 확인함 |
| odb-hub 는 서비스 토큰 하나로 붙는다(`uploaded_by: anonymous`) | 호출자 구분은 **우리 게이트웨이 감사에만** 남는다. 접근 통제는 게이트웨이 `plat:odbhub` 하나다 |

## 아직 없는 것 (S0 체크리스트 대비)

- `tools.json` 의 **정확한 `args_schema`** — 원문은 파라미터·기본값을 표로만 준다. 절차는 실행 때 게이트웨이의 실제 스키마로 검증하므로 설계는 막히지 않는다
- **사용자 PAT 시야** 한 줄(`list_tool_apps(app=odb-hub)`) — cae00 실주행 전에 필요
- `get_copper_result` **성공** 표본 — 워피지 산식에 필요
