# 환원 도구 셋 ↔ §10-7 칸 대조표(2026-10-31)

| 항목 | 내용 |
|---|---|
| 무엇 | 절차 [PLAN](PLAN.md) §10-7 '환원 도구의 공통 계약' 의 칸을 지금 있는 환원 도구 셋의 실제 응답 키와 맞댄 표다. 셋 다 맞아 §10-7 을 제안에서 규약으로 올렸다(판단 기록 [context-notes](context-notes.md) W-103). |
| 근거 | [체크리스트](checklist.md) S9 '② 두 번째 환원 도구가 `bend_profile` 과 같은 모양인지 보고 규약으로 올린다' 줄 · [triage-1031](../leftovers-1017/triage-1031.md) 표 B 의 B4 |
| 대조한 판 | StepForge main `51c8788` · ThermalShockMCP main `6e6a6db`. 아래 `파일:줄` 은 이 판이다(다른 리포는 읽기만 했다). 응답 꼴은 이 리포의 실물 고정물(dev 게이트웨이 실호출 09-14 · 09-16)과 StepForge 회귀로 한 번 더 봤다. |

## 1. 칸마다

도구의 자리 — `bend_profile` 은 StepForge `app/mcp_server.py:24791`(계산은 `core/bending.py:590` `describe`), `stackup_profile` 은 StepForge
`app/mcp_server.py:17900`(계산은 `core/profile.py:1995` `stackup`), `sed_sample_from_odb` 는 ThermalShockMCP `app/mcp_server.py:187`(계산은
`app/reduce_odb.py:159`)이다.

| §10-7 칸 | `bend_profile`(StepForge) | `stackup_profile`(StepForge) | `sed_sample_from_odb`(ThermalShockMCP) |
|---|---|---|---|
| `<대상>` — 무엇을 읽었나 | `parts[]` — 형상 정의마다 한 행(같은 정의의 인스턴스를 묶는다 — `app/mcp_server.py:24875` · `:24898`), 행 안의 `bends[]` 가 굽힘마다(`core/bending.py:597`) | `layers[]` — 고른 파트가 층마다 한 행(part · order · thickness · material · range · area — `core/profile.py:2393-2398`) | `parts.ap` · `parts.pkg` — 부르는 쪽이 지목한 두 역할(refdes · rotation · 크기 · 핀 수 — `app/reduce_odb.py:250-252`) |
| `primary` — 대표값 | **있다** — 굽힘이 여럿이면 호 면적(중립면 호 길이 × 폭)이 가장 큰 것(정렬 `core/bending.py:489` · `:608-609`). 고른 규칙은 응답이 아니라 도구 설명에 있다(`app/mcp_server.py:24819`) | 없다 — 묶음 하나가 대상이라 고를 대표가 없다(반환 `core/profile.py:2387-2411` 에 그 칸이 없다) | 없다 — 대상은 부르는 쪽이 지목한다(`app/reduce_odb.py:159-162`) |
| `basis` — 어떻게 읽었나 | 굽힘마다 — `primary.basis` · `bends[].basis`(`analytic_cylinder_pair` · `fitted_cylinder_pair` · `sampled_curvature_pair` — `core/bending.py:107` · `:123`)와 각도를 낸 식 `angle_basis`(`:111`) | 맨 위 글 하나 — 적층축을 무엇으로 정했나(`given` · `contact_normal_area_weighted` · `overlap_normal_area_weighted`, 둘이면 `+` — `core/profile.py:2391` · `:2061` · `:264-265` · `:1176`) | 맨 위 사전 — 칸 → 읽은 길(`app/reduce_odb.py:246`, 채우는 자리 `:173` · `:127` · `:149`). 사람 값이 유도값과 같은지 다른지까지 적는다(`:203-211`) |
| `notes` — 못 읽은 것 · 의심 | 굽힘마다 `bends[].notes`(`core/bending.py:112`) + 정의 단위 `notes`(두께 대조가 어긋날 때만 — `:617-620`) + 응답 머리 `note`(글 하나 — `app/mcp_server.py:24908`) | 맨 위 `notes[]`(`core/profile.py:2402`, 채우는 자리 `:2342-2344`) | 맨 위 `notes[]`(`app/reduce_odb.py:247`) — 봉투의 `warnings` 에도 같은 것(`app/mcp_server.py:201`) |
| `<x>_check` — 교차 검증 | `thickness_check{bend, min_wall, agree}` — 굽힘부 두께 ↔ 최소 벽 두께. 최소 벽을 못 재면 칸이 없다(`core/bending.py:610-616`, 부르는 자리 `app/mcp_server.py:24883-24884`) | `thickness_check{sum_layers, bbox_along_axis, agree}` — 층 두께 합 ↔ 묶음 전체 두께(`core/profile.py:1326-1335` · `:2401`) | `center_check{ap, pkg}` — 역할마다 부품 원점 ↔ 핀 외접 사각형 중심. 핀이 모자라면 `checked: false` + `why` 이고 `agree` 가 없다(`app/reduce_odb.py:93-105` · `:248-249`) |
| `for_<해석>_analysis` — 해석이 그대로 먹는 칸 | `for_bending_analysis{thickness_mm, bend_radius_mm, bend_radius_inner_mm, width_mm, bend_angle_deg, curvature_1_per_mm}` — 대표 굽힘의 값(`core/bending.py:622-629`) | `for_laminate_analysis{unit_system, laminae[{thickness, material_name}], total_thickness_mm, panel}` — 물성은 비어 있다(재질 이름만 — `core/profile.py:2403-2410`). 적층이 아니면 내지 않는다(`:2290-2333`) | `for_sed_analysis` — `SedInput` 의 키만(`app/reduce_odb.py:242`, 키 목록 `:26`). 받는 쪽 스키마가 `extra="forbid"` 다(`app/schemas.py:17`) |
| (§10-2 규율 1) 못 읽으면 | 통째 — `is_bent_plate: false` + `reason`, 그때는 `primary` · `for_bending_analysis` 가 없다(`core/bending.py:597` · `:604-606`, 까닭 글 `:408` · `:487`). 응답 머리에 `not_bent_reasons[]`(`app/mcp_server.py:24899`) | 통째 — `is_stack: false` + `reason`(`core/profile.py:2050` · `:2290-2333`) | 칸 단위 — `needs_human{칸: {why, candidates?}}` · `complete` · `missing`(`app/reduce_odb.py:243-245` · `:234-239`) |

## 2. 판정 — 규약으로 올린다

- **맞은 칸** — `basis` · `notes` · `<x>_check`(`agree`) · `for_<해석>_analysis` 는 셋 다 낸다. `<대상>` 도 셋 다 있다(이름이 정의 · 층 · 역할로
  다르다). 못 읽은 것을 값으로 지어내지 않는 것(§10-2 규율 1)도 셋 다다. §10-7 이 건 조건('두 번째 환원 도구가 같은 모양이면')을 둘이 넘었다.
- **다른 칸 셋** — 도구의 대상이 달라서 생겼다. 규율을 어긴 것이 아니라 규약을 그 꼴까지 넓혔다(PLAN §10-7).
  ① `primary` 는 고를 것이 여럿인 도구만 낸다. ② `basis` 는 글 하나이거나 칸 → 글 사전이다. ③ `<x>_check` 는 역할마다 갈릴 수 있고,
  대조할 수 없으면 `agree` 를 지어내지 않는다(`checked: false` + `why`, 또는 칸이 없다). 못 읽었을 때의 신호도 통째형과 칸 단위형 둘이다.
- **도구에 고쳐 달라고 할 것은 없다.** 새 환원 도구가 생기면 이 표에 열을 하나 더하고 시험의 `REDUCERS` 에 이름을 넣는다.

## 3. 자리는 앱마다 다르다 — 씨앗의 `save` 경로

규약은 칸 이름과 뜻을 정한다. 응답 안의 자리는 앱마다 달라서 `save` 경로는 꼬리(`for_<해석>_analysis.<칸>`)만 같다.

| 씨앗 | 단계 | 실제 응답(고정물) | `save` 경로 |
|---|---|---|---|
| R1 굽힘 수명 | `bend_profile` | 봉투가 없고 정의마다 `parts[i]`(`backend/tests/fixtures/procedures/laminate_responses.json:1209`) | `parts[0].for_bending_analysis.bend_radius_mm` 외 둘(`docs/procedures/fixtures/laminate-bend-life.yaml:102-104`) — 해석 단계가 `"{{r_designed}}"` 로 받는다(`:118`) |
| R3 열충격 SED | `sed_sample_from_odb` | 봉투 `{ok, data, errors, warnings}` 아래(`backend/tests/fixtures/procedures/thermal_shock_responses.json:93`, ThermalShockMCP `app/errors.py:38-50`) | `data.for_sed_analysis`(`docs/procedures/fixtures/thermal-shock-sed.yaml:78`) — `predict_sed` 가 `"{{sample}}"` 로 받는다(`:83`) |
| (아직 없다) | `stackup_profile` | 봉투가 없고 맨 위(StepForge 회귀 `tests/test_profile.py:146-168`) | 쓰면 `for_laminate_analysis.laminae` 다 — 물성은 사람이나 다른 앱이 채운다(결손 [`gaps/lamina-strength-fatigue.yaml`](gaps/lamina-strength-fatigue.yaml)) |

보고서 근거로만 남기는 칸(`parts[0].primary.basis` — `laminate-bend-life.yaml:105` · `data.needs_human` — `thermal-shock-sed.yaml:78`)은 해석에
넘기지 않아 `for_*_analysis` 밖이어도 된다. 해석 단계로 통째 넘기는 환원 값이 `for_*_analysis` 에서 오는지는
`backend/tests/test_procedures_reduction_contract.py` 가 본다.
