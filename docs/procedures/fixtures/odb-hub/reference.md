# ODB++ 자동화 허브 (odb-hub) — 연계 개발 레퍼런스

> **출처** — S0([odb-request.md](../../odb-request.md))을 odb-hub 쪽에 맡겨 정리받은 문서(2026-09-16 실측).
> 원문을 살렸고 **공개 리포라 더 지운 것**만 있다: 서버 내부 IP → `<odb-hub>`, 잡 ID → `<JOB_n>`,
> 관리계정 이름 → `<공용 관리계정>`(접속되던 노드 수도 뺐다), 체크리스트 규칙 **정의 문구**(§4.3) → 생략. 좌표·치수·층 구조·응답 모양은 원문 그대로다.
> 원문 작성자가 이미 가린 것(토큰·과제명·모델명·부품코드)은 그대로 가려져 있다.

## ⚠ dev 대조 결과 — 이 문서를 믿기 전에 읽을 것

dev 는 odb-hub 에 닿지 않아(`health=000`) **서버에 다시 물어 확인하지는 못했다.** 대신 이쪽에 있는 것 —
ThermalShockMCP 의 `SedInput` 스키마·학습 데이터 294건·`build_features`, HWAXRisk 어댑터 계약,
우리 게이트웨이·판정기 소스 — 와 대조했다. 상세·근거는 [sed-mapping.md](sed-mapping.md).

| # | 원문 위치 | 대조 결과 |
|---|---|---|
| 1 | §5 `pkg_type` "접두사로 부분 가능" | **틀림.** SED 어휘는 `WLP`/`FX`/`DIG` 다. `bga`·`qfn`·`dfn` 접두사와 대응이 없다 → **사람이 채운다** |
| 2 | §3·§5 `board_type` 을 단면/양면으로 판정 | **뜻부터 틀렸다.** INT=인터포저 보드·HALF=인터포저 없는 모바일·FULL=태블릿 등 큰 보드(사용자 확인). 단면/양면이 아닌 근거 — 학습 HALF 46건 중 19건은 PKG 가 AP 면적 안에 통째로 들어간다(반대면 실장). 원천인 ThermalShockMCP 스키마 설명이 틀려 있었다 — 고쳤다 |
| 3 | §5 패드 "환산 정의 못 찾음" | **유력.** 핀 `pad` `r190` → 190 이 SED `pad_size` 실데이터 값 집합(180~240, 10 단위)에 그대로 있다. cae00 에서 한 번 확인 |
| 4 | §3 좌표 원점 우려 | **무관.** SED 모델은 `|dx|`·`|dy|`·`dist` 만 쓴다. 대신 **AP 와 PKG 가 같은 잡(같은 좌표계)** 이어야 한다 — 인터포저 보드 주의 |
| 5 | §2 "읽기 전용(21개)" | 표에는 **24개**다(24+3=27 로 전체 수와 맞는다). 제목 숫자 오기 |
| 6 | §2 `get_managed_parts` 를 읽기로 분류 | §4.16 `list_results` 에 **조사 시각에 `managed_parts`(created_by `mcp`) 결과가 생겼다** — 결과를 저장하는 도구다(파괴는 아님) |
| 7 | §1 "서버 검증(zod 로 추정)" | 서버는 FastAPI(파이썬)라 zod 를 쓰지 않는다. 그 오류는 조사에 쓴 **클라이언트** 쪽일 가능성이 크다. 기본값을 명시해 보내는 건 무해하니 따르되 원인은 미확인 |
| 8 | §3 `get_violation_map` "미실행이면 빈 배열" | 빈 배열이 **"위반 없음" 과 똑같이 생겼다.** `list_results` 로 체크리스트 실행 여부를 먼저 본다 |
| 9 | §3 비동기 `run_*` → `get_task` 폴링 | **우리 게이트웨이 결함이 걸린다** — `get_` 접두 도구를 300초 캐시해 폴링이 옛 상태를 봤다. HWAXMcpGateway 에서 고쳤다(상태·잡 조회는 캐시 안 함) |
| 10 | §4.13 봉투형 오류 | 포털 판정기가 실패로 잡는 것을 원문 그대로 넣어 확인했다(`ok=False, layer=envelope, kind=error_key`) |

---

> 이 문서 하나로 odb-hub를 몰라도 연계 기능(어댑터·자동화 스크립트)을 개발할 수 있도록,
> 서버 위치·전체 도구 스키마·실제 응답 표본·용어 사전·알려진 갭을 한 곳에 모았습니다.
> 작성일 2026-09-16. **사내망 밖으로 반출될 수 있는 문서라 인증 토큰 값과 미공개
> 과제명·모델명은 마스킹했습니다** — 실제 값은 사내 담당자에게 별도 요청하세요.
> (좌표·치수·층 구조·규칙 문구 등 기술 데이터는 실측 그대로 남겼습니다.)

## 0. 한눈에 보기

| 항목 | 내용 |
|---|---|
| 무엇인가 | ODB++ PCB 설계 데이터(.tgz)를 업로드받아 설계 체크리스트(38개 규칙) 자동 검사, 부품 추출, 체적/인터포저/동박율 분석, 리비전 비교, 표준 스택업 대조를 제공하는 사내 웹 서비스 + MCP 서버 |
| 실행 서버 | 사내망 전용 `<odb-hub>:8000` (사내 별칭: **ai02**). FastAPI(uvicorn) 단일 프로세스가 Web UI + REST(`/api/...`) + MCP(`/mcp`)를 함께 서빙 |
| 소스 코드 | **사내 개발 포털(HWAXPortal 등)의 어떤 리포에도 없음.** 모든 곳에서 "외부 링크"로만 등록되어 있고, 실제 소스가 있는 서버(ai02) 자체는 별도 계정 없이는 들어갈 수 없었음(§1 참고). 연계 개발은 이 문서의 API 계약만으로 진행 가능 |
| 데이터 규모(실측) | 저장된 보드(job) 108개, 표준 스택업 라이브러리 53종(0.35T~1.0T, 4~12층, 가이드 버전 4.7) |
| 인증 | MCP: URL 쿼리 토큰(`?token=<REDACTED>`), streamable_http 전송. REST 웹 UI 인증 방식은 미확인(웹 로그인 화면 존재, 별도 조사 필요) |

## 1. 연결 정보

```
Base URL      : http://<odb-hub>:8000/
Health        : GET /health           → 200
                GET /api/health       → {"status":"ok"}
OpenAPI       : GET /openapi.json     → {"openapi":"3.1.0","info":{"title":"ODB++ 자동화 허브 API","version":"0.1.0"}, ...}
API 문서(Swagger) : GET /docs         → 200 (브라우저로 열람)
MCP 엔드포인트 : POST /mcp?token=<REDACTED>   (transport: streamable_http)
뷰어(웹)      : GET /viewer?job=<job_id>
보드 업로드   : POST /api/jobs (multipart, .tgz) — MCP 도구로는 노출 안 됨(§6 참고), 웹/REST 전용으로 추정
리포트 다운로드: GET /api/jobs/{job_id}/report/{checklist|volume|...}
```

- 서버 확인: `server: uvicorn` 헤더, `GET /mcp` (토큰 없이) → `401`.
- **사내 게이트웨이(HWAXMcpGateway)를 통해서도 붙어 있음** — 그 설정엔 `"odb-hub": {"url": "http://<odb-hub>:8000/mcp?token=<REDACTED>", "transport": "streamable_http"}` 형태로 저장되어 있고, 이 백엔드는 **개인 계정이 아니라 서비스 토큰 하나로 통째로 인증**됩니다(호출자별 구분 없음 — 감사 로그에 caller가 안 남는 유형).
- **직접 붙을 때 반드시 확인할 구현상의 함정**: 이 서버의 MCP 도구 스키마는 optional 필드에 기본값이 있어도 클라이언트가 "생략"하면 서버 쪽 검증(zod로 추정)이 `invalid_type: expected nonoptional, received undefined`로 거부합니다. **모든 파라미터를 스키마에 나온 기본값이라도 명시적으로 채워 보내세요.** *(대조 #7 — 원인 미확인)*

## 2. 전체 MCP 도구 (27개) — 이름·설명·파라미터

이름에 `odb_` 같은 접두어가 없는 **bare 이름**입니다(사내 게이트웨이를 거치면 다른 백엔드와 이름이 겹칠 때만 접두어가 붙습니다 — 직접 붙는다면 아래 이름 그대로 씁니다).

### 읽기 전용(21개) — 상태를 바꾸지 않음 *(대조 #5 — 실제 24개, #6 — `get_managed_parts` 는 결과를 저장한다)*

| 도구 | 파라미터 | 설명 |
|---|---|---|
| `ping` | (없음) | 연결 확인. `{"status","server","jobs"}` — jobs는 등록된 보드 총수 |
| `list_jobs` | `limit`(기본20·최대100), `offset`(기본0) | 보드 목록, 업로드 최신순. 각 항목에 `analyses_done` 배열 |
| `find_job` | `query`(string) | 과제명으로 검색 — 정확일치→부분일치→모델명/파일명 순 |
| `list_rules` | `category`("" =전체) | 38개 설계 체크리스트 규칙 정의 목록 |
| `get_rule_detail` | `job_id`, `rule_id`, `page`(기본1), `page_size`(기본0=서버기본20,최대100) | 특정 규칙의 위반 상세 행. 표가 2개인 규칙(CKL-03-015)은 `tables[]`로 두 번째 표도 옴 |
| `get_checklist_result` | `job_id` | 최신 체크리스트 결과 요약(pass/fail 수, 규칙별 violation_count+메시지, 리포트 URL) |
| `get_violation_map` | `job_id`, `rule_id`("" =전체) | 위반 부품의 보드 좌표(x,y) — 뷰어 오버레이용. 체크리스트 미실행이면 빈 배열 *(대조 #8)* |
| `list_parts` | `job_id`, `category`(""), `side`(""), `sort`(""), `page`(1), `page_size`(20) | 분류된 부품 목록(refdes·part_name·pkg_name·pkg_width/length mm·side·pin_count) |
| `get_part_detail` | `job_id`, `refdes` | 부품 1개 상세 — 패키지 치수, x/y/rotation/mirror, `device_type`, 핀별 net+좌표(최대 200핀) |
| `get_parts_summary` | `job_id` | 카테고리별(IC/Connector/Capacitor/Inductor/Interposer/Shield Can/SIM_Socket) top/bottom 집계 |
| `get_managed_parts` | `job_id`, `include_unused`(false) | 관리부품(캐패시터 10종/41종, 인덕터 2S) 사용 현황 |
| `get_board_layers` | `job_id` | 레이어 구성(이름·타입·순서), 스택업 있으면 층별 두께(μm)+총두께(mm), `stackup_verdict` |
| `list_stackups` | `layer_count`(0), `nominal_thickness`(""), `include_inactive`(false) | 표준 스택업 목록(요약, 층 구조 제외) |
| `get_stackup` | `stackup_id` | 표준 스택업 1건의 전체 층 구조(이름/구분/두께um/자재) |
| `check_job_stackup` | `job_id` | 보드 두께가 표준에 실존하는지 판정: `standard`/`ambiguous`/`non_standard`/`unknown` |
| `match_stackup` | `total_thickness`(필수), `layer_count`(0), `tolerance_um`(5), `include_inactive`(false) | 총두께(+층수)로 표준 스택업 역조회. `match_type`: exact/near/none |
| `get_mounting_holes` | `job_id`, `page`(1), `page_size`(0) | 고정홀·컷아웃 목록(지름mm·좌표·도금여부·신뢰도) |
| `get_volume_result` | `job_id` | 부품/보드 체적(mm³), 질량(g/kg), unit/array(판넬) 스코프별 수치, 체적 상위 10개 |
| `get_interposer_result` | `job_id` | top/bottom 인터포저 개수·면적(mm²)·면적비(%)·refdes 목록. 캐시만 있으면 실행 없이 즉석 계산 |
| `get_copper_result` | `job_id` | 층별/구간별 동박율. **미실행 시 봉투형 에러**(§4 예시 참고) — 예외가 아니라 200 응답의 error 필드 |
| `list_results` | `job_id` | 그 보드에 대해 이미 수행된 분석 이력(종류·완료시각·리포트URL) |
| `get_compare_result` | `job_id`(NEW 리비전 기준) | 저장된 리비전 비교 요약(체크리스트 전이 집계, 부품 이동/추가/삭제, 관리부품 변경) |
| `get_compare_table` | `job_id`, `sheet`(""), `page`(1), `page_size`(0) | 비교 결과의 상세 표(페이지 단위) |
| `get_task` | `task_id` | 백그라운드 작업(run_*) 진행 상태 폴링. `status`가 `error`일 때만 실패로 판정 — 진행이 더뎌 보여도 `heartbeat_seconds_ago`가 작으면 살아있는 것 |

### 상태 변경(3개) — 백그라운드로 새 분석 결과를 만듦(덮어쓰기, 파괴 아님)

| 도구 | 파라미터 | 설명 |
|---|---|---|
| `run_checklist` | `job_id`, `rule_ids`(null=전체38개), `solutions`(false) | 체크리스트 실행. `solutions=true`면 (Beta) 수정 제안까지 생성(30초쯤 더 걸림). `task_id` 반환 → `get_task`로 폴링 |
| `run_analysis` | `job_id`, `analysis`("copper"/"interposer"/"volume"/"extract"), `options`(null, 예: `{"method":"vector","n_rows":5,"n_cols":5}` 또는 `{"categories":["IC"]}`) | 지정 분석 실행. `task_id` 반환 |
| `run_compare` | `new_job_id`, `old_job_id` | 두 리비전 비교 실행. 결과는 `get_compare_result(new_job_id)`로 조회 |

**주의**: 이 3개 외에는 업로드(`ingest`)·삭제 도구가 MCP에 전혀 노출되어 있지 않습니다(웹 UI 전용으로 추정). 즉 MCP로 잡을 새로 만들거나 지울 수는 없고, 이미 있는 108개 잡을 읽거나 그 잡에 대한 분석을 (재)실행하는 것만 가능합니다.

## 3. 핵심 개념 · 용어 사전 (실측 기반)

- **`job_id`**: 16자리 hex 문자열(예 `<JOB_1>`). 파일 내용 기반(content-addressed)으로 보이며, 같은 파일을 다시 올리면 같은 ID가 재사용됩니다(`status: ready`).
- **잡 메타 필드**: `project`(과제명) · `model`(모델명) · `board_type`(아래 참고) · `revision` · `job_name` · `original_filename` · `uploaded_at` · `uploaded_by`(관측값 전부 `"anonymous"` — 사용자 구분 없음, 서비스 토큰 계정) · `cache_ready` · `analyses_done`(예: `["checklist","volume"]`).
- **`board_type` 값 어휘 — 중요한 함정**: 실측 값은 `Main` / `Sub` / `S_AP` / `IF Sub` / `M_RF` 등, **휴대폰 하위보드 역할 분류명**입니다. 만약 다른 시스템(예: 열충격 SED 예측 모델)의 `board_type: INT(인터포저)/HALF(단면실장)/FULL(양면실장)` 같은 어휘와 매핑하려 한다면 **이 필드를 그대로 쓰면 안 됩니다** — 일대일 대응이 아닙니다. 대신: *(대조 #2)*
  - 인터포저 여부는 `get_interposer_result`의 `top.count`/`bottom.count` > 0 으로 판정하세요(실측: `board_type="S_AP"`인 잡에서 top 인터포저 1개, 면적비 27.52% 확인).
  - 단면/양면 실장 여부는 `get_parts_summary`의 카테고리별 `top`/`bottom` 개수가 둘 다 0보다 큰지로 판정하세요.
- **좌표·치수 단위**: 부품 위치(x,y)·패키지 폭/길이(pkg_width/pkg_length)·고정홀 지름·체적 계산의 board 치수는 전부 **mm**. 층 두께(`thickness_um`)는 **μm**. 좌표는 보드 자체 좌표계(원점은 과제마다 다를 수 있음 — 절대좌표보다 부품 간 상대거리를 쓰는 것이 안전). *(대조 #4)*
- **스택업(적층) 판정 어휘** (`check_job_stackup.verdict`, `get_board_layers.stackup_verdict`):
  - `standard` = 사내 표준 스택업 라이브러리(53종, 가이드 4.7)에 두께+층수가 실존
  - `ambiguous` = 두께는 같은데 subtype만 다른 후보가 여럿
  - `non_standard` = 표준에 없음 — **ODB 안의 두께 값이 틀렸다는 신호일 수 있음**(문서 자체가 "ODB 내부 두께는 틀린 경우가 잦다"고 명시)
  - `unknown` = ODB에 두께 정보 자체가 없음
  - `standard`가 아니면 `suggestions`에 같은 층수의 최근접 표준 후보가 담깁니다.
- **레이어 타입 어휘**(`get_board_layers.layers[].type`): `SIGNAL` · `POWER_GROUND` · `SOLDER_MASK` · `SOLDER_PASTE` · `SILK_SCREEN` · `DIELECTRIC` · `DRILL` · `DOCUMENT` · `COMPONENT`(부품층은 `comp_+_top`/`comp_+_bot`으로 명명).
- **표준 스택업 층 구분**(`get_stackup.layers[].kind`): `Signal` / `Dielectric` / `SolderResist`, 자재(`material`): `CU`(구리) / `PPG`/`CCL`/`RCC`(유전체) / `SR`(솔더레지스트).
- **에러 응답 모양 — 봉투형(envelope), 예외 아님**: 예를 들어 `get_copper_result`를 아직 실행 안 한 보드에 부르면 HTTP 200 + `{"error": "동박율 결과가 없습니다", "hint": "run_analysis(...) 로 계산 실행 후 재조회"}` 가 돌아옵니다. MCP 프로토콜 레벨의 `isError` 예외가 아니라 **정상 응답 안의 error 필드**이므로, 연계 코드는 `try/except`가 아니라 **응답 JSON에 `error` 키가 있는지**로 실패를 판정해야 합니다. *(대조 #10)*
- **페이지네이션 공통 패턴**: `list_parts`·`get_mounting_holes`·`get_rule_detail`·`get_compare_table`·`list_jobs` 모두 `{page, page_size, returned, total, has_more}` 형태를 씁니다. `has_more=true`면 다음 페이지를 요청하세요(offset류는 `list_jobs`만 `offset` 파라미터, 나머지는 `page` 파라미터).
- **비동기 작업 패턴**: `run_checklist`/`run_analysis`/`run_compare`는 즉시 `task_id`를 반환하고, `get_task(task_id)`로 10~15초 간격 폴링합니다. `status=="error"`일 때만 실패로 판정하세요(대형 보드는 수 분 걸릴 수 있고, 진행률이 한동안 같아 보여도 `heartbeat_seconds_ago`가 작으면 정상 진행 중). *(대조 #9)*
- **관리부품 카테고리**(`get_managed_parts`): "Capacitors 10-type"(10종) / "Capacitors 41-type"(41종) / "Inductors 2S"(54종 중 사용분) — 각 `part_name`·`size`(패키지 사이즈 코드, 예 "603"·"1005"·"2012")·top/bottom/total 개수.
- **체크리스트 규칙 카테고리**: `Placement`(배치) / `Spacing`(이격) / `Clearance`(여백) — 총 38개, 규칙ID 형식 `CKL-XX-NNN`.

## 4. 실제 응답 표본 (2026-09-16 실측, 과제명/모델명 마스킹)

아래는 실제로 살아있는 서버에 호출해서 받은 응답입니다(형태·수치는 그대로, 사업적으로 민감한 과제명/모델명만 `<PROJECT_A>` 식으로 치환).

### 4.1 `ping()`

```json
{"status": "ok", "server": "odb-hub", "jobs": 108}
```

### 4.2 `list_jobs(limit=3, offset=0)` (마스킹)

```json
{
  "jobs": [
    {
      "job_id": "<JOB_2>",
      "project": "<PROJECT_A>", "model": "<MODEL_A>",
      "board_type": "Main", "revision": "0.7",
      "job_name": "designodb",
      "original_filename": "<REDACTED>.tgz",
      "uploaded_at": "2026-09-16T04:42:06.954204+00:00",
      "uploaded_by": "anonymous",
      "cache_ready": true,
      "analyses_done": ["volume"]
    },
    {
      "job_id": "<JOB_3>",
      "project": "<PROJECT_B>", "model": "<MODEL_B>",
      "board_type": "S_AP", "revision": "0.2",
      "job_name": "designodb", "original_filename": "<REDACTED>.tgz",
      "uploaded_at": "2026-09-11T06:13:34.168617+00:00",
      "uploaded_by": "anonymous", "cache_ready": true, "analyses_done": []
    }
  ],
  "total": 108, "returned": 3, "offset": 0, "has_more": true
}
```

관측된 `board_type` 값 전체(상위 10개 잡 기준): `Main`, `S_AP`, `IF Sub`, `M_RF`, `Sub`.

### 4.3 `list_rules()` — 38개 중 3개 예시 *(규칙 정의 문구는 공개 리포라 생략)*

```json
{
  "rules": [
    {"rule_id": "CKL-01-001", "category": "Placement", "description": "<규칙 문구>"},
    {"rule_id": "CKL-01-010", "category": "Placement", "description": "<규칙 문구>"},
    {"rule_id": "CKL-03-015", "category": "Clearance", "description": "<규칙 문구>"}
  ],
  "total": 38
}
```

### 4.4 `get_parts_summary(job_id="<JOB_1>")`

```json
{
  "job_id": "<JOB_1>",
  "categories": [
    {"category": "Capacitor", "top": 821, "bottom": 196, "total": 1017},
    {"category": "Inductor",  "top": 344, "bottom": 57,  "total": 401},
    {"category": "IC",        "top": 49,  "bottom": 22,  "total": 71},
    {"category": "Connector", "top": 3,   "bottom": 13,  "total": 16},
    {"category": "Shield Can","top": 8,   "bottom": 3,   "total": 11},
    {"category": "Receptacle","top": 5,   "bottom": 0,   "total": 5},
    {"category": "SIM_Socket","top": 0,   "bottom": 1,   "total": 1}
  ],
  "total_parts": 1522,
  "note": "미분류(Unknown) 부품은 웹 추출 탭과 동일하게 제외됩니다"
}
```

### 4.5 `list_parts(job_id="<JOB_1>", category="IC")` — 1행 예시

```json
{
  "refdes": "U1005", "part_name": "<PART_CODE>",
  "pkg_name": "bga41f_W235L235_SB019_1_LT",
  "pkg_width": 2.35, "pkg_length": 2.35,
  "side": "top", "pin_count": 41, "category": "IC"
}
```

`part_name`은 사내 부품코드(불투명 숫자)이며, **이름 자체로 AP/PKG 여부를 구분할 수 있는 명명 규칙은 관측되지 않았습니다**(§6 갭 참고).

### 4.6 `get_part_detail(job_id="<JOB_1>", refdes="U1005")` (일부)

```json
{
  "refdes": "U1005", "pkg_name": "bga41f_W235L235_SB019_1_LT",
  "pkg_width": 2.35, "pkg_length": 2.35,
  "x": 17.27, "y": -53.815, "rotation": -90.0, "mirror": false,
  "device_type": "Filter", "type": "IC", "pin_count": 41,
  "pins": [
    {"pin_num": 0, "name": "A1", "net": "PRX_LNA_IN_B40_GBL", "pad": "r190", "x": 18.26, "y": -52.825}
  ],
  "pins_truncated": false, "net_count": 29
}
```

`pad`(예 `"r190"`)는 패드 심볼 코드로 보이나, 정확한 치수 환산 규칙은 이 서버 응답만으로는 확인되지 않았습니다. *(대조 #3)*

### 4.7 `get_board_layers(job_id="<JOB_1>")` (요약)

```json
{
  "layer_count": 39, "signal_layer_count": 8, "total_thickness_mm": 0.65,
  "thickness_source": "odb",
  "layers": [
    {"name": "smt", "type": "SOLDER_MASK", "thickness_um": 20.0},
    {"name": "signal_1", "type": "SIGNAL", "thickness_um": 25.0},
    {"name": "dielectric_3", "type": "DIELECTRIC", "thickness_um": 50.0}
  ],
  "viewer_url": "http://<odb-hub>:8000/viewer?job=<JOB_1>",
  "stackup_verdict": "standard"
}
```

### 4.8 `check_job_stackup(job_id="<JOB_1>")` (요약)

```json
{
  "verdict": "standard",
  "message": "표준 스택업 확인 — 0.65mm / 8L (가이드 4.7)",
  "thickness_mm": 0.65,
  "thickness_source": "misc/attrlist .board_thickness (finished)",
  "layer_count": 8,
  "chosen_id": "SU47-0.65T-8L-030",
  "chosen_by_user": false,
  "layers": [
    {"name": "SR", "kind": "SolderResist", "thickness_um": 20.0, "material": "SR"},
    {"name": "L1", "kind": "Signal", "thickness_um": 25.0, "material": "CU"},
    {"name": "L1-L2", "kind": "Dielectric", "thickness_um": 50.0, "material": "PPG"}
  ]
}
```

### 4.9 `get_managed_parts(job_id="<JOB_1>")` (요약)

```json
{
  "categories": [
    {"category": "Capacitors 10-type", "types": 10, "types_used": 1,
     "top": 1, "bottom": 0, "total_components": 1,
     "parts": [{"part_name": "<CODE>", "size": "3216", "top": 1, "bottom": 0, "total": 1}]},
    {"category": "Capacitors 41-type", "types": 41, "types_used": 22,
     "top": 370, "bottom": 86, "total_components": 456}
  ]
}
```

### 4.10 `get_mounting_holes(job_id="<JOB_1>")`

```json
{
  "hole_count": 1, "cutout_count": 1,
  "summary": "고정홀 1개 (관통 1 / 직경 1.60mm)",
  "holes": [
    {"x": 4.949966, "y": -53.456923, "diameter_mm": 1.6, "nominal_mm": 1.6,
     "kind": "BOTH", "plating": "PLATED", "mount_attr": true, "confidence": "HIGH"}
  ]
}
```

### 4.11 `get_volume_result(job_id="<JOB_1>")` (요약)

```json
{
  "grand_total_mm3": 3007.9131, "pkg_mass_kg": 0.011730907,
  "board": {
    "outline_area_mm2": 6065.3397, "x_mm": 107.18, "y_mm": 72.9693,
    "thickness_mm": 0.65, "signal_layers": 8, "volume_mm3": 3942.4708,
    "stackup_verdict": "standard", "stackup_id": "SU47-0.65T-8L-030"
  },
  "total_with_board_mm3": 6950.3839,
  "scopes": [
    {"key": "unit", "n_units": 1, "total_mm3": 6950.3839, "mass_g": 29.8663, "basis": "보드 외곽 면적 × 두께"},
    {"key": "array", "label": "Array (×2)", "n_units": 2, "total_mm3": 15902.372, "mass_g": 68.9399, "basis": "판넬 재질 면적 × Z"}
  ],
  "report_url": "http://<odb-hub>:8000/api/jobs/<JOB_1>/report/volume"
}
```

### 4.12 `get_interposer_result` — 인터포저 없는 잡 vs 있는 잡

```json
// job A (board_type="Main") — 인터포저 없음
{"top": {"count": 0, "ratio_pct": 0.0}, "bottom": {"count": 0, "ratio_pct": 0.0}}

// job B (board_type="S_AP") — 인터포저 있음
{
  "top": {"count": 1, "pcb_area_mm2": 1287.6553, "interposer_area_mm2": 354.3813,
          "ratio_pct": 27.52, "items": [{"refdes": "INP100", "area_mm2": 354.3813}]},
  "bottom": {"count": 0, "ratio_pct": 0.0}
}
```

### 4.13 `get_copper_result` — 미실행 시 봉투형 에러

```json
{
  "error": "동박율 결과가 없습니다",
  "hint": "run_analysis(job_id, analysis=\"copper\") 로 계산을 실행하고 get_task 로 완료를 확인한 뒤 다시 조회하세요"
}
```

### 4.14 `get_checklist_result(job_id="<JOB_1>")` (요약)

```json
{
  "total": 38, "passed": 32, "failed": 6,
  "failed_rules": [
    {"rule_id": "CKL-01-001", "category": "Placement", "violation_count": 6,
     "message": "반대면 부품과의 패드 중첩 또는 리셉타클 이격 위반이 6건 발견되었습니다."},
    {"rule_id": "CKL-03-015", "category": "Clearance", "violation_count": 63,
     "violation_breakdown": {"main": 6, "signal": 57},
     "message": "PCB 외곽선으로부터 0.65mm 이내에 패드가 있는 부품이 6건, 배선(net)이 57건 발견되었습니다."}
  ],
  "report_url": "http://<odb-hub>:8000/api/jobs/<JOB_1>/report/checklist"
}
```

### 4.15 `get_violation_map(job_id, rule_id="CKL-01-001")`

```json
{
  "rule_count": 1, "total_components": 6,
  "rules": [{
    "rule_id": "CKL-01-001", "verdict": "fail", "affected": 6,
    "comps": [
      {"refdes": "F2005", "side": "top", "x": 92.68, "y": -67.17},
      {"refdes": "PAM1001", "side": "bottom", "x": 13.89, "y": -59.0}
    ]
  }]
}
```

### 4.16 `list_results(job_id="<JOB_1>")`

```json
{
  "results": [
    {"kind": "checklist", "completed_at": "2026-09-16T00:28:17Z", "created_by": "anonymous",
     "report_url": "http://<odb-hub>:8000/api/jobs/<JOB_1>/report/checklist"},
    {"kind": "volume", "completed_at": "2026-09-16T01:59:04Z", "created_by": "anonymous",
     "report_url": "http://<odb-hub>:8000/api/jobs/<JOB_1>/report/volume"},
    {"kind": "managed_parts", "completed_at": "2026-09-16T13:49:51Z", "created_by": "mcp", "report_url": null}
  ]
}
```

*(대조 #6 — 세 번째 줄이 조사 중 `get_managed_parts` 호출로 생긴 것이다)*

### 4.17 `list_stackups()` — 53종 중 일부

```json
{
  "guide_version": "4.7", "count": 53,
  "stackups": [
    {"stackup_id": "SU47-0.65T-8L-030", "nominal_thickness": "0.65T", "total_um": 650.0,
     "layer_count": "8L", "subtype": "2D", "apply_type": "Main", "status": "active"},
    {"stackup_id": "SU47-1.0T-10L-058", "nominal_thickness": "1.0T", "total_um": 1012.0,
     "layer_count": "10L", "subtype": "3D", "apply_type": "Main", "status": "active"}
  ]
}
```

## 5. 다른 시스템과 연계 시 필드 매핑 현황 (사례: 열충격 SED 예측 모델)

> ⚠ **이 절은 대조에서 둘이 틀렸다**(#1 `pkg_type`, #2 `board_type`). 쓸 때는 [sed-mapping.md](sed-mapping.md) 를 본다.

사내 열충격 파손예측 모델(`predict_sed`)이 필요로 하는 입력 15개(필수10+선택5)를 odb-hub가 무엇으로
채울 수 있는지 실측으로 대조한 표입니다. 다른 시스템과 연계할 때도 "이 서버가 좌표·치수·구조는
주지만 상위 개념(공정 파라미터, 판정 카테고리)은 안 준다"는 패턴을 참고하세요.

| 입력 | odb-hub가 주는가 | 근거 |
|---|---|---|
| 보드 구분(예: 인터포저/단면/양면) | **간접 가능** — `board_type` 필드 직접 대응은 아님(§3 참고). `get_interposer_result`(count>0) + `get_parts_summary`(top/bottom 둘다>0)로 유도 | 실측: `board_type="S_AP"` 잡에서 인터포저 27.52% 확인 |
| 부품 중심좌표(x,y) | **가능** | `get_part_detail(refdes).x/.y` (mm, 보드좌표계) |
| 패키지 폭/길이 | **가능** | `list_parts`/`get_part_detail`의 `pkg_width`/`pkg_length` (mm) |
| 볼 피치/직경 문자열, 패드 사이즈 | **불명 — 직접 필드 없음** | 핀 목록의 `pad` 심볼(예 `"r190"`)에서 유도 가능성 있으나 환산 정의를 못 찾음. 사람 확인 필요 |
| 패키지 기술 분류(WLP 등) | **부분 가능(추정)** | `pkg_name` 접두사로 문자열 매칭 가능해 보임(`wlp*`·`qfn*`·`dfn*`·`bga*`·`fowlp*` 관측) — 매핑 표는 검증 안 됨 |
| AP/메모리 등 "어느 부품이 그 역할인지" | **불가 — 선별 규칙 없음** | `part_name`은 불투명 사내코드, `device_type`은 관측값이 "Filter"뿐이라 역할 분류 근거 부족. **부품 역할은 사람이 refdes를 지정해줘야 함** |
| 두께·층수 | **가능, 신뢰도까지 제공** | `get_board_layers`, `check_job_stackup`(표준 대조 verdict 포함) |
| 동박율/대칭도 | **분석을 먼저 실행해야 함** | `run_analysis(analysis="copper")` 후 `get_copper_result` |

**일반화된 교훈**: odb-hub는 "형상 데이터(좌표·치수·층·개수)"는 정확하고 풍부하게 주지만,
"그 형상이 무엇을 의미하는지(역할·공정 분류)"는 대부분 호출하는 쪽에서 사람이 정의해야
합니다. 연계 어댑터를 설계할 때 이 경계를 먼저 정하세요.

## 6. 알려진 갭 / 확인 필요 항목

- **AP/PKG(또는 임의의 "역할이 있는 부품") 선별 규칙 없음** — refdes·part_name 명명 규칙으로
  자동 판별 불가. 도구 응답만으로는 "이 부품이 무슨 역할인지" 알 수 없습니다.
- **ball_size/pad_size류 정밀 치수 필드 없음** — 핀의 `pad` 심볼(`r190` 등)이 유일한 단서.
- **pkg_type 어휘 매핑 미검증** — `pkg_name` 접두사 매칭이 그럴듯해 보이지만 검증되지 않음.
- **업로드(ingest)/삭제 도구가 MCP에 없음** — 새 보드를 올리거나 지우려면 웹 UI(REST
  `POST /api/jobs`로 추정)를 써야 하며, 그 인증 방식은 이번 조사에서 확인하지 못했습니다.
- **REST 웹 UI 자체 인증 방식 미확인** — MCP 토큰과는 별개로 보이며, 로그인 화면이 있는지/
  SSO를 쓰는지 조사 필요.
- **소스 코드 자체에 접근 불가** — ai02 서버 자체에 SSH로 들어가 소스 경로를
  확인하려 했으나, 사내 공용 관리계정(`<공용 관리계정>`)으로는 인증이 거부되었습니다
  (그 계정으로 다른 AI 노드는 정상 접속됨 — ai02만 별도 관리 대상). ai02 고유 계정이
  있어야 소스 위치·배포 방식(어떤 프레임워크로 짜였는지, git 이력 등)을 알 수 있습니다.
- **run_checklist/run_analysis/run_compare의 실제 소요시간 미측정** — 이번 조사는 읽기
  전용 도구만 호출했고, 이 3개(상태 변경)는 문서상 "수십초~수분"이라는 것만 확인됨.

## 7. (참고, 내부 인원용) 관련 사내 문서

외부로 이 문서만 들고 나가는 경우엔 아래는 무시해도 됩니다. 사내에서 더 깊이 파려면:

- `HWAXPortal/backend/config/systems.yaml` — 포털 타일 등록(`odb-hub` 항목)
- `HWAXPortal/docs/procedures/odb-request.md` — 이 조사의 출발점이 된 원본 수집 절차서
- `HWAXPortal/docs/procedures/{PLAN.md,checklist.md,context-notes.md}` — 설계 배경/의사결정 이력
- `HEAXHub/integrations/odb-hub/.portal/manifest.yaml` — external_link 등록(소스 없음의 근거)
- `HWAXMcpGateway/gateway_config.json` — 실제 MCP 토큰(값은 이 문서에서 마스킹)
- `HEAXHub/var/integration_workspaces/hwax-risk/upstream/docs/odb-adapter-contract.md` — 다른 팀(HWAXRisk)이 예전에 가정했던 4개 도구명(`odb_get_board` 등) — **실제 이름과 다름, 개정 필요**
