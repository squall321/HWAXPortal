# 화면 요청서 — 리스크 앱 ECAD 보드 고르기 · 스냅샷 · 비교의 ECAD(HWAXRisk `frontend/` 세션에)

보내는 쪽: 백엔드 세션(포털 리포 `docs/design-risk-review/ecad-1031/`) · 2026-10-31 · 요청서 정본 [request.md](request.md) ER-01 · ER-04 · ER-05. 대조한 코드는 HWAXRisk 가지 `wt1031/ecad` `76fe9a8`(main `ecad8c8` 위, push · main 합침 전)이고, 계약 정본은 같은 가지의 `docs/odb-adapter-contract.md` 다. 아래의 경로 · 칸 · 코드는 그 커밋의 코드에서 확인했다. 사용자 결정 셋(10-31, [context-notes.md](context-notes.md) E-3)은 그 커밋 뒤에 났다 — 그 결정으로 바뀌는 곳은 '결정' 으로 적었고, 백엔드가 반영한 커밋은 끝의 '반영' 에 적는다.

## 0. 먼저 — 모든 화면에 걸리는 것

- **무엇이 바뀌었나.** ECAD 는 지금까지 늘 '연결 대기(스텁)' 이고 스냅샷은 늘 `missing.ecad_absent` 였다. 이제 과제마다 ODB 허브 보드 한 장을 사람이 골라 붙이면 스냅샷이 보드 · 적층 · 분류된 부품을 싣는다(1단계). 부품 좌표 · 넷 · 분류 안 된 부품은 2단계다(ODB 허브 OH-01 ~ OH-04 뒤 ER-06).
- **고르는 것은 사람이다.** 찾기는 후보를 보일 뿐이고 붙이기는 사람이 고른 `job_id` 하나만 받는다. 같은 모델의 다른 판(revision · 올린 시각)이 함께 나오므로 화면도 이름으로 고르거나 첫 행을 미리 고르지 않는다 — 후보가 하나여도 사람이 그 행을 눌러야 붙는다.
- **자격(결정 1).** 찾기 · 붙이기 · 캡처의 ECAD 는 **그 사람의 등록된 포털 PAT 만** 쓴다. 박스 읽기 PAT 로 내려가지 않는다 — 내려가면 게이트웨이의 `plat:odbhub` 문을 서비스 계정으로 지나 ODB 허브 권한이 없는 사람도 보드를 본다. 그 사람의 PAT 가 없으면(없음 · 폐기 · 풀리지 않음 · 곧 끝남) 찾기 · 붙이기는 게이트웨이를 부르기 전에 409 `ecad_pat_absent` 다. 웹으로 들어온 사람은 앱이 PAT 를 저절로 등록하므로(포털 [`../../risk-credentials/frontend-request.md`](../../risk-credentials/frontend-request.md) 1절) 보통은 막히지 않는다.
- **오류 본문.** `{error: {code, message}, …detail}` 이다(detail 칸은 최상위에 펼쳐진다). `message` 는 고칠 곳까지 말하는 한국어라 그대로 보이면 된다.
- **남의 것.** 과제 주인이 아니면 붙이기 · 떼기는 '없는 것' 과 같은 404 다. 찾기(`GET /api/ecad/boards`)는 과제에 묶이지 않는다.
- 경로는 지금처럼 상대 `api/…` 다(앱 `/apps/hwax_risk/` 아래). 아래에서는 `/api/…` 로 적는다.

## 1. ECAD 카드 — 붙은 보드 보이기

**왜.** 지금 `ProjectPage.tsx` 의 `SourceCard` 는 ECAD 에도 일반 연결 폼(어댑터 · 참조 입력)을 그리고, 어댑터가 없으면 '연결 대기(스텁)' 라고 쓴다. 서버는 이제 일반 연결로 ECAD 를 받지 않는다(`POST /api/projects/{id}/sources` 의 kind `ecad` 는 422 `ecad_board_route`, detail `fix` 가 아래 길을 가리킨다).

**백엔드가 주는 것.**

- `GET /api/meta/adapters` 의 `apps[]` 가운데 kind `ecad` 한 줄 — `{kind, app_key: "odb-hub", status, tools_ok, tools_missing[], gateway_error, warnings[], choices: []}`. `status` 는 `ready`(1단계 도구 여섯이 다 보인다) · `unavailable`(빠진 원래 이름이 `tools_missing`) · `planned`(게이트웨이 도구 지도를 못 읽었다)다. `contract_only` 는 더 나오지 않는다.
- `GET /api/projects/{id}` 의 `sources[]` 가운데 kind `ecad` 한 행(과제마다 많아야 한 장).

```text
{ id, kind: "ecad", app_key: "odb-hub", ref: {odb_job_id},          // 16자리 16진(허브 job_id)
  probe: { reachable, status: "linked" | "unreachable", detail, capture_mode: "mcp",
           board: {job_id, name, project, model, board_type, revision, original_filename, uploaded_at} },
  probe_at, status, bridge_declared: false }
```

- `probe.detail` 은 붙였을 때 `find_job_ok app_key=odb-hub`, 캡처 뒤에는 어댑터 결과로 다시 잰 값이다 — 보드를 실었으면 `capture_ok calls=N app_key=…`, 일부만이면 `capture_partial calls=N …`(실패한 호출이 뒤에 붙는다), 못 읽었으면 `status: "unreachable"` · `capture_failed <경고 code> — <글>` 이다. kinds 에서 ecad 를 뺀 캡처는 카드를 건드리지 않는다. `probe.board` 는 캡처 뒤에도 남는다.

**할 일**

- ECAD 카드에서 일반 연결 폼과 '연결 대기(스텁)' 문구를 뺀다. 대신 `meta/adapters` 의 ecad `status` 로 길을 가른다 — `ready` 면 2절의 찾기 칸, `unavailable` 이면 'ODB 허브 도구가 게이트웨이에 없다 — `tools_missing`'(운영자 몫), `planned` 면 '게이트웨이 도구 지도를 못 읽었다 — 잠시 뒤 다시'.
- 붙은 보드가 있으면 카드에 보드 정체를 보인다 — `probe.board.name`(과제 · 모델 · 보드 종류 · 판을 ` / ` 로 엮은 것, 넷 다 비면 null) · `revision` · `original_filename` · `uploaded_at` · `job_id`(고정폭). 그 아래 `status` 배지와 `probe.detail` 을 지금처럼 보인다. 없으면 '보드 없음' 과 찾기 칸이다.
- 바꾸기(3절) · 떼기(4절) 단추를 카드에 둔다. 과제 주인에게만 보인다.

## 2. 찾기 — 검색 칸 → 후보 표

**백엔드가 주는 것.** `GET /api/ecad/boards?q=<과제 · 모델 · 파일 이름 또는 job_id>`(1 ~ 200자) — ODB 허브 `find_job` 한 번을 감싼다.

```text
200 { query, app_key: "odb-hub", tool,
      candidates: [ {job_id, name, project, model, board_type, revision, original_filename, uploaded_at} ],   // 많아야 10
      truncated: bool,
      hub_message?: string }        // 허브가 '찾는 것이 없다' 를 봉투형 오류로 답했을 때 — 그때 candidates 는 []
```

**할 일**

- 검색 칸 하나와 '찾기' 단추를 둔다. 빈 값 · 200자 넘는 값은 화면이 먼저 막는다(서버는 422 `E100`). `job_id` 를 그대로 넣어도 된다 — 그래도 결과는 후보 표이고 사람이 그 행을 고른다.
- 후보를 표로 보인다 — 이름 · 판(`revision`) · 원본 파일 이름 · 올린 시각 · `job_id`. 같은 모델의 다른 판이 줄줄이 나오므로 판과 올린 시각을 앞쪽 열에 둔다. 미리 고른 행은 없다.
- `truncated` 면 표 아래에 '후보가 더 있다 — 검색어를 좁힌다' 를 보인다(서버는 10개까지만 준다).
- 후보가 비고 `hub_message` 가 있으면 그 글을 그대로 보인다. 둘 다 없으면 '찾은 보드가 없다' 다.
- 오류는 5절의 표다.

## 3. 붙이기 · 바꾸기

**백엔드가 주는 것.** `PUT /api/projects/{id}/ecad-board {odb_job_id}`(과제 주인만). 서버는 그 `job_id` 로 `find_job` 을 다시 불러 **같은 job_id 의 행이 있을 때만** 적는다.

```text
200 { ok: true, project_id, ecad_board: <그 후보 한 줄>, source: <1절의 ecad 카드 행>,
      previous_odb_job_id: string | null, changed: bool }
```

- 카드는 과제마다 한 장이라 다른 보드를 주면 같은 카드를 바꾼다. 바뀌면 감사 `project.ecad_board` 한 줄이 남고 `changed: true` 다. 같은 보드를 다시 주면 `changed: false` 다(카드의 보드 정보만 새로 적는다).
- 이미 동결된 스냅샷은 그대로이고 다음 캡처부터 새 보드를 읽는다.

**할 일**

- 후보 표에서 사람이 고른 행의 `job_id` 로만 보낸다. 이름 · 모델로 찾아 보내는 길을 두지 않는다.
- 이미 붙은 보드가 있으면 보내기 전에 '앞 보드 이름(판) → 새 보드 이름(판)' 확인을 받는다. 확인 글에 '동결된 스냅샷은 그대로이고 다음 캡처부터 새 보드를 읽는다' 를 적는다.
- 성공하면 답의 `source` 로 카드를 다시 그린다(과제를 다시 받아도 된다). `changed: false` 면 '이미 붙은 보드다' 로 알린다.
- 422 `ecad_board_not_found` 면 그사이 허브에서 사라졌거나 다른 판이 걸린 것이다 — 본문의 `candidates` 를 후보 표로 다시 보이고(자동으로 고르지 않는다) `hub_message` 가 있으면 함께 보인다.

## 4. 떼기

**백엔드가 주는 것.** `DELETE /api/projects/{id}/ecad-board` → `200 {ok: true, project_id, removed, previous_odb_job_id}`. 붙은 것이 없으면 `removed: 0` 이다(같은 요청을 되풀이해도 된다).

**할 일**

- 확인을 받는다 — '이미 동결된 스냅샷은 그대로이고 다음 캡처부터 ECAD 가 빠진다(스냅샷의 ECAD 는 결측 `ecad_absent`)'.
- 성공하면 카드를 '보드 없음' 으로 되돌린다.

## 5. 오류 상태

| code | HTTP | 언제 | 화면 |
|---|---|---|---|
| `ecad_pat_absent` | 409 | **결정 1** — 그 사람의 등록된 포털 PAT 가 없다 · 폐기됐다 · 풀리지 않는다 · 곧 끝난다. 찾기 · 붙이기 모두다. | '내 포털 PAT 가 없어 ODB 허브를 부르지 않았다' 와 설정 화면으로 가는 길(자동 등록 스위치 · 「포털에서 발급해 등록」). |
| `ecad_credential_absent` | — | `9bd5f48` 부터 없다(지웠다) — 옛 판(`76fe9a8` 이전)에서만 나온다. | 옛 판이 도는 박스에서 받으면 `ecad_pat_absent` 와 같은 안내. |
| `ecad_gateway_unreadable` | 409 | 게이트웨이 도구 지도(`/tools-map`)를 못 읽었다. 못 읽은 지도는 캐시하지 않는다. | '게이트웨이를 못 읽었다 — 잠시 뒤 다시 찾는다'. 다시 찾기 단추. |
| `ecad_unavailable` | 409 | 게이트웨이의 `odb-hub` 백엔드에 `find_job` 이 없다(detail `tools_missing`). | 'ODB 허브가 게이트웨이에 붙어 있지 않다 — 운영자 몫'. |
| `ecad_unreachable` | 409 | `find_job` 호출이 실패했다(detail `tool`). | `message` 그대로와 다시 찾기 단추. |
| `ecad_schema_drift` | 409 | `find_job` 답에서 잡 목록을 못 읽었다(알려진 열쇠가 없다). | `message` 그대로 — 운영자 몫(허브 답의 꼴이 바뀌었다). |
| `ecad_board_not_found` | 422 | 붙이기 — `find_job` 후보에 그 `job_id` 가 없다(detail `candidates` · `hub_message`). | 3절 — 후보를 다시 보이고 사람이 다시 고른다. |
| `E100` | 422 | 찾을 말이 비었거나 200자를 넘는다 · `odb_job_id` 가 16자리 16진이 아니다(이때 허브를 부르지 않는다). | 화면이 먼저 막는다. |
| `ecad_board_route` | 422 | 일반 연결(`POST …/sources`)에 kind `ecad` 를 보냈다. | 화면이 그 길을 부르지 않는다(1절). |
| (404) | 404 | 내 과제가 아니다. | '없음'. |

## 6. 캡처 — 기본 kinds · 못 읽은 보드 · 모델 크기(결정 3)

**백엔드가 주는 것.** `POST /api/projects/{id}/snapshots {label?, kinds, report_ids?, detect_result_file_id?, allow_large?}`.

- kinds 가 비었거나 `ecad` 를 담았을 때만 붙은 보드를 읽는다. kinds 에서 ecad 를 빼면 보드를 읽지 않고 결측 행만 남긴다(ECAD 없는 앞 스냅샷과 견줄 캡처를 사람이 고를 수 있다).
- 붙은 카드가 있는데 kinds 가 그 종류를 다 뺐으면 409 `source_unreachable` 이고 detail 이 `{kinds, attached}` 다 — '연결하라' 가 아니라 kinds 를 고칠 일이다.
- 이번 캡처가 읽은 카드가 ECAD 하나뿐인데 그 보드를 못 읽었으면 스냅샷을 만들지 않는다 — 409 `source_unreachable`, detail `{kind: "ecad", reason: <경고 code>}`(예 `ecad_pat_absent` · `ecad_board_not_found`). 잡은 `failed` 이고 호출 원문은 스냅샷 없이 남는다.
- **결정 3 — 모델 크기 상한(`risk_max_leaf` 1,500)이 ECAD 부품도 센다**(계획 §2.11.3 — 심사 비용을 막는 상한이다). MCAD 리프와 ECAD 부품을 합쳐 넘으면 409 `model_too_large`, detail `{leaf, interfaces, max_leaf, max_interfaces, budget_s}` 이고 `allow_large: true` 로 다시 보내면 동결한다(그때 예산 600 s). 표본 보드의 분류된 부품은 748 · 528 개라 MCAD 와 함께 캡처하면 상한에 닿기 쉽다. detail 에 ECAD 부품 수를 따로 싣는지는 결정 반영 커밋이 정한다('반영' 에 적는다).

**할 일**

- 과제에 ECAD 카드가 붙어 있으면 동결 폼의 기본 kinds 에 `ecad` 를 넣는다(지금 기본은 `["mcad"]` 라 보드를 붙여도 읽지 않는다).
- 409 `source_unreachable` 의 `message` 를 그대로 보이고, detail `kinds` · `attached` 가 있으면 kinds 체크를 그 종류로 바꾸는 단추를 둔다.
- 409 `model_too_large` 면 detail 의 리프 · 계면 수와 상한을 보이고, '그래도 동결' 확인 뒤 같은 요청에 `allow_large: true` 를 실어 다시 보낸다(지금 `SnapshotCreate` 타입 · 폼에는 `allow_large` 가 없다). 무엇이 상한을 넘겼는지(ECAD 부품이 들었는지) 한 줄로 적는다.

## 7. 스냅샷 화면 — board 노드 · ECAD 소스 · 표지

**백엔드가 주는 것.** `GET /api/snapshots/{id}`(part `ir`) 의 봉투. `ir_version` 은 `1.1` 이다.

- **board 노드 1건** — `nodes[]` 의 `domain: "ecad"` · `kind: "board"` · `canon_key: "ecad:board"` · `label: "board"`(판이 바뀌어도 같은 값 — 쌍 비교가 두 판의 보드를 이 이름으로 맞춘다) · `local_key` = job_id. `attrs` 는 아래다(길이는 mm, 없는 값은 null — 0 이 아니다). 노드 표 경로(part `nodes`)는 같은 노드를 `kind` · `source_kind` · `name` 칸으로 주고 `attrs` 는 싣지 않는다.

```text
attrs: { board_id, name, revision, units: "mm",
         thickness, stackup_verdict, stackup_id, ecad_stackup_total,   // 보드 두께 · 적층 판정 · 표준 적층 id · 5종 층 두께 합(mm)
         layer_count,                                                  // 동박층 수
         n_components,                                                 // 분류된 부품 수(= component 노드의 원천)
         n_components_placed,                                          // 배치 수(분류 안 된 부품 포함)
         outline: {x_mm, y_mm, area_mm2}, outline_bbox: null,          // 원점이 없다(OH-04)
         n_nets: null, odb_version: null, source_hash }
```

- **layer 노드** — `kind: "layer"` · `canon_key: "ecad:layer:<idx>"`(위에서 아래로 1부터) · `label` = 층 이름 · `attrs.thickness`(mm, 실크는 null) · `attrs.material`(판정이 standard 이고 표준 적층과 층 구분이 하나하나 맞을 때만, 아니면 null) · `attrs.copper_weight`(늘 null).
- **component 노드** — `kind: "component"` · `canon_key: "ecad:<refdes>"` · `label` = refdes · `group` = 면 · `attrs.{refdes, part_number, footprint, side, pin_count, height}`. `x · y · rot · nets · value` 는 null(2단계). 높이는 면마다 큰 부품 10개에만 있다.
- **ECAD 소스** — `sources[]` 의 kind `ecad` 한 줄. `ref` 는 `{board_id, name}`, `adapter_version` 은 보드를 실었으면 `1.0` · 결측이면 `0.0-stub`, `stats` 는 `thickness_mm · stackup_verdict · stackup_id · stackup_total_mm · layer_count · outline · n_components · n_components_basis("classified") · n_components_placed · n_nets(null) · odb_version(null) · layer_rows · layer_rows_all · source_size_bytes`, `degraded[]` 는 아래 표지다.
- **결측** — `missing` 은 bool 사전이다. ECAD 의 두 열쇠는 `ecad_absent`(보드 없음 · 읽지 않음 · 못 읽음) · `ecad_capture_failed`(붙은 보드를 `find_job` 단계에서 못 읽었다 — '회로가 없다' 가 아니다)다. 호출 없이 끝난 실패(`ecad_pat_absent` · `ecad_gateway_unreadable` · `ecad_tools_missing`)는 `ecad_absent` + 경고다.

**할 일**

- 스냅샷 개요 아래에 '보드' 묶음을 둔다 — board 노드의 `attrs` 를 사람 말 라벨로(보드 이름 · 판 · 두께 · 적층 판정 · 동박층 수 · 분류된 부품 수 · 배치 수 · 외곽 폭 × 높이 · 면적). null 칸은 '없음' 으로 보이고, `n_nets` · `odb_version` · `outline_bbox` 옆에는 '2단계' 를 붙인다. 보드가 없으면 이 묶음을 그리지 않는다.
- 노드 표는 `kind` 로 거를 수 있게 한다(board · layer · component · part …) — 보드 한 장에 노드가 수백 개에서 2,000 개까지 더해진다(부품 상한 2,000, 넘으면 `components_truncated`).
- `FLAG_LABEL` 에 ECAD 표지 열둘과 결측 하나를 더한다. 사전에 없는 코드는 지금처럼 서버 문자열 그대로다.

| 코드 | 사람 말 |
|---|---|
| `ecad_nets_deferred` | 회로 넷 없음(2단계) |
| `component_xy_deferred` | 부품 좌표 · 회전 없음(2단계) |
| `components_unclassified_omitted` | 분류 안 된 부품 빠짐(저항 · 테스트 포인트 등) |
| `outline_origin_unknown` | 외곽 원점 모름(폭 · 높이 · 면적만) |
| `stackup_material_unmatched` | 적층 재료를 표준 적층과 못 맞춤 |
| `copper_weight_absent` | 동박 무게 없음(두께만) |
| `plane_type_unknown` | plane 구분 없음(없다는 뜻이 아니다) |
| `odb_version_absent` | ODB 형식 판 없음 |
| `component_value_absent` | 부품 값 없음 |
| `component_height_partial` | 부품 높이 일부만(면마다 큰 부품 10개) |
| `components_unavailable` | 부품 목록을 못 읽음(부품 노드가 통째로 없다 — 부품 수는 미측정) |
| `layers_unavailable` | 층 목록을 못 읽음(층 노드가 통째로 없다) |
| `ecad_capture_failed` | 붙은 ECAD 보드를 못 읽음 |

- 경고(`warnings[]`)는 지금처럼 `message` 를 그대로 보인다. ECAD 경고 code 목록(`ecad_pat_absent` · `odb_error_body` · `components_incomplete` · `odb_paging_capped` · `placed_below_classified` · `duplicate_refdes` · `refdes_reserved` 등)과 뜻은 계약 문서의 '못 읽었을 때' · '1단계 사상' 이다.

## 8. 비교 화면 — `comparability.ecad` 와 ECAD 항목

**백엔드가 주는 것.** diff 의 `comparability` 에 `ecad` 가 생겼다.

```text
comparability.ecad: { base: "present" | "absent" | "failed",
                      target: "present" | "absent" | "failed",
                      excluded_reason: "capture_partial" | "partial_scope" | null,
                      adapter_parity: bool }
```

- 쪽마다 `present`(보드를 온전히 실었다) · `absent`(보드 없음 · 읽지 않음) · `failed`(못 읽었거나 `capture_partial` · `components_unavailable` · `layers_unavailable`)다.
- 한쪽이라도 `failed` 면 ECAD 항목(ECAD 노드의 구조 변화 · ECAD 만의 파라메트릭 항목)에 `excluded_reason: "capture_partial"`, 한쪽에만 보드가 실렸으면(첫 보드를 붙인 캡처 · kinds 에서 ecad 를 뺀 캡처) `"partial_scope"` 다. 그 항목은 남지만 의미 이벤트(`part.added` · `part.removed`)를 만들지 않는다. MCAD · dyna 의 항목 · 이벤트는 그대로다.
- 두 쪽 다 실렸는데 ECAD 어댑터 세대가 다르면 `adapter_parity: false` 이고 ECAD 항목 · 이벤트에만 `caveat: "parser_differs"` 와 등급 한 단계 낮춤이다.
- 1단계 비교는 ECAD 노드를 refdes · 층 이름으로 맞춰 **추가 · 삭제만** 본다. 층 두께 · 재료 · 품번 · 패키지 · 핀 수 · 높이의 칸 변화는 싣지 않는다.

**할 일**

- 비교 가능성 묶음에 'ECAD' 한 줄을 둔다 — 두 쪽의 상태와 `excluded_reason`. `partial_scope` 면 '한쪽 스냅샷에만 보드가 있다 — ECAD 는 견주지 않았다. 앞 리비전에도 보드를 붙여 다시 캡처하면 견준다', `capture_partial` 이면 '한쪽 보드를 온전히 읽지 못했다 — ECAD 는 견주지 않았다' 다.
- `EXCLUDED_LABEL` 에 `capture_partial`(한쪽 캡처가 부분 · 실패)을 더한다. 지금 `partial_scope` 의 말('부분 검출 범위 밖')은 ECAD 항목에는 맞지 않는다 — 항목이 ECAD 면 '한쪽에만 보드' 로 보인다.
- 두 쪽 다 `present` 면 비교 머리에 '1단계 비교는 ECAD 부품 · 층의 추가 · 삭제만 본다(칸 변화 없음)' 를 한 줄 둔다.

## 9. 대상 화면 — ECAD 의존 도메인(결정 2)

- ECAD 의존 도메인은 여섯이다(`pcb · pwr · rf · soc · passive · mem`). 보드를 실은 **스냅샷 대상**에서는 `pcb · soc · passive · mem` 이 deferred 에서 풀린다. **결정 2 — `pwr · rf` 는 2단계(넷 · 배치)까지 deferred 로 남는다** — 1단계에는 좌표 · 넷이 없어 그 판단이 undetermined 로만 나온다.
- **diff 대상**에서는 1단계 동안 여섯 다 ECAD 부재로 본다(영역 1순위가 아닌 좌석은 deferred · 입력 결손 `ecad_absent`). 두 리비전 모두 보드가 실렸어도 1단계 비교에 ECAD 칸 변화가 없어서다.
- **할 일** — 대상 화면의 좌석 표(`TargetPage.tsx` 의 status · reason)는 지금처럼 서버의 `reason` code 를 보이되 사람 말을 붙인다. `ecad_absent` 는 스냅샷 대상이면 '보드 없음', diff 대상이면 '1단계 비교는 ECAD 칸 변화를 보지 않는다' 다. pwr · rf 를 미루는 까닭 code 는 결정 반영 커밋이 정한다('반영' 에 적는다) — 그 code 에는 '넷 · 배치가 필요해 ECAD 2단계까지 미룸' 을 붙인다.

## 10. 지금 있는 어긋남(이번 일과 함께 보면 좋은 것)

ECAD 칸을 그리다 보면 닿는 자리라 함께 적는다. 둘 다 `ecad8c8` 의 화면에도 있다.

- `types.ts` 의 `SnapshotIr.missing` 은 `string[]` 인데 백엔드 봉투의 `missing` 은 bool 사전(`{mcad_absent, ecad_absent, ecad_capture_failed, …}`)이다. `FlagList` 는 참인 열쇠를 보이면 된다.
- `types.ts` 의 `Comparability` 는 `{ok, excluded_reason, note}` 인데 백엔드의 `comparability` 에는 그 셋이 없다 — `tol_parity · unit_parity · result_parity · scope_parity · coordinate_ok · ir_version_parity · app_version_parity · adapter_parity · source_schema_parity · capture_parity · primary_source_parity · ecad · G7 · base_blocked · target_blocked` 등이다. 지금 비교 화면의 '비교 가능' 배지는 늘 'no' 로 읽힐 수 있다.

## 반영

- 백엔드 칸이 들어간 커밋 — HWAXRisk main `9bd5f48`(2026-10-31 push, 가지 `wt1031/ecad` 를 앞으로 당겨 합침).
  - `bba3492` 1단계 어댑터(`adapters/ecad.py`) · 발견(백엔드 `odb-hub` + 원래 이름) · 표지 열 · `meta/adapters` 의 ecad 상태.
  - `5a06231` 보드 고르기 — `GET /api/ecad/boards` · `PUT · DELETE /api/projects/{id}/ecad-board` · MCP `risk_find_ecad_boards` · `risk_set_ecad_board` · 일반 연결의 422 `ecad_board_route`.
  - `444c8c5` same-as — ECAD 노드가 실려도 쌍 비교의 지문 단계는 MCAD · dyna 끼리 돈다.
  - `cc0539f` 반대 검토 고침 — board 노드 · `comparability.ecad` · `components_unavailable` · `layers_unavailable` · 호출 없이 끝난 실패는 결측 + 경고 · 409 `ecad_gateway_unreadable` · ECAD 하나뿐인 캡처의 409 `source_unreachable` · ECAD 카드를 어댑터 결과로 · diff 대상의 ECAD 도메인 대기.
  - `76fe9a8` 계약 문서 · 판단 기록 · 작업 대장.
- 사용자 결정 셋(10-31)을 반영한 커밋(같은 main) — `8a205f9`(결정 1) · `7d28b8c`(결정 2) · `b7ead6d`(결정 3) · `05b64f3` · `5c8d4be` · `9bd5f48`(시험 · 기록). 바뀐 칸은 이렇다.
  - **결정 1(그 사람 PAT 만)** — `GET /api/ecad/boards` · `PUT /api/projects/{id}/ecad-board` · MCP 찾기 · 붙이기가 그 사람 PAT 가 없거나 쓸 수 없으면(폐기 · 풀리지 않음 ·
    1800초 안에 끝남) 게이트웨이를 부르기 전에 409 `ecad_pat_absent`(detail `app_key: "odb-hub"` · `fix: "portal_pat"`)다. 박스 PAT 가 있어도 같다.
    떼기(DELETE)는 PAT 없이도 된다. 캡처 — 보드만 실은 과제는 409 `source_unreachable`(detail `kind: "ecad"` · `reason: "ecad_pat_absent"`, 잡 `failed`, 카드는
    '못 읽음'), MCAD 와 섞인 과제는 스냅샷이 서고 `credentials.mcp: "service"` · `missing.ecad_absent: true` · `ecad_capture_failed: false` · 경고 `ecad_pat_absent` 다
    (MCAD · dyna 는 지금처럼 박스 PAT 로 내려간다).
  - **결정 2(pwr · rf 는 2단계까지)** — 1단계 보드를 실은 스냅샷 대상에서 pwr · rf 는 ECAD 부재와 같은 꼴이다 — 영역 1순위 좌석은 앉고 2순위부터 `deferred` 다.
    좌석 coverage 의 `reason` 은 `ecad_nets_deferred`, 리뷰 순서의 `input_gaps` 는 pwr · rf 좌석 모두 `["ecad_nets_deferred"]` 다. 2단계 스위치는 백엔드 한 곳이다.
  - **결정 3(상한에 ECAD 부품)** — 409 `model_too_large` 의 detail 에 `leaf_mcad` · `leaf_ecad` 가 붙고 `leaf` 는 그 합이다. 메시지는 '리프 N/상한(MCAD 리프 m · ECAD 부품 e)'
    이고 잡 오류에도 같은 글이 남는다. 분류된 부품이 1,500 을 넘는 보드는 그것만으로 `allow_large=true` 가 든다.
