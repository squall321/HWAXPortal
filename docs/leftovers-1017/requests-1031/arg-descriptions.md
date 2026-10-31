# 도구 인자 설명 — 절차 씨앗이 부르는 도구부터(요청 · 2026-10-31)

| 항목 | 내용 |
|---|---|
| 받는 곳 | 네 리포의 세션 — LaminateAnalyzerMCP(2-1) · StepForge(2-2) · KooRemapper(DynaForge MCP, 2-3) · ThermalShockMCP(2-4). 절마다 떼어 보내도 읽히게 썼다. **ThermalShockMCP 는 지금 도는 세션이 없다** — 2-4 는 사용자가 그 리포 세션을 열 때 넘긴다. |
| 근거 | [triage-1031](../triage-1031.md) 표 B 의 B37 · 절차 [체크리스트](../../procedures/checklist.md) '전 앱이 인자 `description` 을 채운다' 줄 · 결손 장부 [`hub-arg-descriptions.yaml`](../../procedures/gaps/hub-arg-descriptions.yaml) · [improvement-1015](../../improvement-1015/PLAN.md) §6(점수판) |
| 대조한 판 | LaminateAnalyzerMCP main `2d35565` · StepForge main `51c8788` · KooRemapper main `d3d777c` · ThermalShockMCP main `6e6a6db` · 게이트웨이 master `5f4ba5f` · 리스크 앱 `ae4af1d`. 아래 `파일:줄` 은 이 판이다(다른 리포는 읽기만 했다). dev 게이트웨이 `/tools-map` 은 2026-10-31 15:00 KST 에 읽었다(인증 없이 읽히는 창이다). |

## 1. 왜

**지금** — 네 앱 도구의 인자에 설명이 하나도 없다. dev 게이트웨이 점수판(`/tools-map` 의 `arg_scores`)은 도구 579 · 인자 2,053 가운데 설명 있는 인자를
230(11.2%)으로 센다. 설명이 찬 곳은 게이트웨이 자체(53/57) · 리스크 앱(137/137) · 심의 엔진(40/40)이다.

| 앱(게이트웨이 키) | 도구 | 인자 | 설명 있는 인자 |
|---|---|---|---|
| LaminateAnalyzerMCP(`heax-laminate_analyzer_mcp`) | 38 | 136 | 0 |
| StepForge(`heax-step_forge`) | 176 | 827 | 0 |
| KooRemapper(`heax-kooremapper_mcp`) | 85 | 248 | 0 |
| ThermalShockMCP(`heax-thermal_shock_mcp`) | 12 | 20 | 0 |

**그래서** — 챗 · 심의 좌석 · 개인 Claude 는 인자를 고를 때 도구 설명 산문을 읽고 짐작한다. 포털 절차 화면은 변수의 뜻을 도구 산문에서 인용해
채운다(결손 장부 `hub-arg-descriptions.yaml` 의 대처 — 요청을 대신하지 않는다). 설명이 스키마에 있으면 둘 다 그것을 그대로 쓴다.

**게이트웨이가 세는 법**(`gateway.py:1134-1146` 머리말 · `_arg_counts` `:1181-1194`) — 인자는 `inputSchema.properties` 의 맨 위 키다. 객체 안으로는
내려가지 않는다. 설명은 그 키의 `description` 이 공백 아닌 글일 때만 센다(pydantic 이 이름으로 만드는 `title` 은 설명이 아니다). 단위 · 범위
칸(`unit_or_range`)은 설명에 단위 · 범위 낱말이 있거나 스키마가 `enum` · 숫자 경계를 가질 때 오른다. 이 요청의 기준은 설명이다 — 값에 단위가 있으면
단위를, 허용값이 정해져 있으면 허용값을 함께 적는다.

**범위** — 포털 절차 씨앗(`docs/procedures/fixtures/`)이 실제로 부르는 도구 17개 · 인자 84개만 청한다. 앱 전체로 넓힐지는 그쪽이 정한다(요청이 아니다).

## 2. 무엇을 — 도구와 지금 인자

모두 설명이 0 이다. 인자는 서명 그대로 `이름: 형 = 기본값` 이다(`ctx: Context` 는 FastMCP 가 스키마에서 빼므로 적지 않았다). '뜻이 적힌 곳' 은 지금
그 값의 뜻 · 단위 · 허용값을 적어 둔 자리다 — 설명은 거기서 옮기되 상한 · 허용값은 코드의 상수에서 읽는다(3절).

### 2-1. LaminateAnalyzerMCP — `app/mcp_server.py`(4 도구 · 22 인자)

| 도구 | 자리 | 인자 | 뜻이 적힌 곳 |
|---|---|---|---|
| `analyze_laminate` | :41 | `laminate: dict`(필수) · `include: list[str] \| None = None` · `neutral_axis_mode: str = "clt_weighted"` · `include_abd_6x6: bool = False` · `include_debug: bool = False` | 도구 설명 :44-51 · 서버 안내 :12-17 |
| `recover_ply_stresses` | :191 | `laminate: dict`(필수) · `loads: dict \| None = None` · `delta_T: float \| None = None` · `detail: str = "auto"` · `panel: dict \| None = None` | :194-206 |
| `estimate_fatigue_life` | :292 | `laminate: dict`(필수) · `loads_max: dict`(필수) · `loads_min: dict \| None = None` · `detail: str = "auto"` · `delta_T: float \| None = None` | :294-303 |
| `solve_prescribed_curvature` | :471 | `laminate: dict`(필수) · `kappa: list \| None = None` · `bend_radius: float \| None = None` · `bend_axis: str = "x"` · `width: str = "free"` · `epsilon0: list \| None = None` · `loads: dict \| None = None` | :475-487 |

이 앱의 pydantic 모델(`app/schemas.py` — 머리 주석 '필드 description이 곧 에이전트용 문서', 예 `Strength` :17-24 · `FatigueSN` :27-36)은 칸마다
설명과 단위가 있다. 그런데 도구가 `laminate: dict` 로 받아 그 설명이 inputSchema 에 닿지 않는다 — 게이트웨이는 0 으로 센다. 맨 위 인자에 한 줄
설명을 단다(`laminate` 라면 단위계 · ply 순서 · 꼴을 어디서 보나 정도).

### 2-2. StepForge — `app/mcp_server.py`(3 도구 · 20 인자)

| 도구 | 자리 | 인자 | 뜻이 적힌 곳 |
|---|---|---|---|
| `find_parts` | :2103 | `project_id: str`(필수) · `name: str = ""` · `material: str = ""` · `min_volume: float \| None = None` · `max_volume: float \| None = None` · `has_mesh: bool \| None = None` · `tag: str = ""` · `role: str = ""` · `limit: int = 100` · `offset: int = 0` · `fields: list[str] \| None = None` | :2107-2133(`name` 은 글롭 · `tag` 는 정확히 같은 것 · 한 쪽 1~500행) |
| `stackup_profile` | :17900 | `project_id: str`(필수) · `parts: list \| None = None` · `name: str = ""` · `axis: str = ""` · `full: bool = False` · `nonadjacent_in_budget: bool = False` | :17902-17959 |
| `bend_profile` | :24791 | `project_id: str`(필수) · `part: str \| None = None` · `limit: int = 10` | :24793-24825 |

도구는 `register`(`app/catalog.py:57-77`)가 여러 겹으로 감싸 등록한다(이력 · 과제 이름으로 부르기 · 응답 고리 — :76). 감싼 뒤에도 설명이
inputSchema 에 남는지를 `mcp.list_tools()` 로 보는 시험을 먼저 둔다(3절의 리스크 앱 시험 `_schemas()` 꼴). `project_id` 는 id 만이 아니라 과제
이름 · 코드도 받는다(`register` 머리말 D-211) — 설명에 그 사실을 적는다.

### 2-3. KooRemapper(DynaForge MCP) — `platform/mcp_server/server.py`(8 도구 · 36 인자)

| 도구 | 자리 | 인자 | 뜻이 적힌 곳 |
|---|---|---|---|
| `create_session` | :127 | `name: str`(필수) · `description: str \| None = None` | :128-129 |
| `run_operation` | :237 | `session_id: str` · `operation: str` · `args: dict`(셋 다 필수) | :238-240(`args` 의 꼴은 `describe_operation` 의 `args_schema`) |
| `report_summary` | :1185 | `report_id: str`(필수) | :1186-1187 |
| `report_part_risk` | :1209 | `report_id: str`(필수) · `part_id: int \| None = None` | :1210-1211 |
| `report_directional` | :1224 | `report_id: str`(필수) · `part_id: int \| None = None` | :1225-1226 |
| `find_reports` | :1240 | `kind` · `project` · `dev_rev` · `variation` · `doe` · `focus` · `doe_strategy` · `scenario_type` · `severity` · `has_part` · `q` · `since` · `until` · `session_id`(모두 `str \| None = None`) · `drop_height` · `min_worst_stress` · `min_worst_g`(모두 `float \| None = None`) · `kfile_id: int \| None = None` · `sort: str = "created_at"` · `order: str = "desc"` · `limit: int = 100` | :1264-1274 |
| `report_part_series` | :1413 | `report_id: str` · `case_key: str` · `part_id: int`(셋 다 필수) | :1414 |
| `report_findings` | :1419 | `report_id: str`(필수) · `severity: str \| None = None` | :1420-1421 |

`find_reports` 의 21 인자는 게이트웨이 점수판에서 이 앱의 가장 나쁜 도구다(`worst` 첫 줄). 축의 뜻 · 정렬 값 · 기간 꼴은 도구 설명(:1264-1274)에
있다. 물리량 칸(`drop_height` · `min_worst_stress` · `min_worst_g`)은 단위를 적는다(리포트의 단위 관례는 `platform/backend/app/modules/analysis/ndjson.py:21`
주석). id 는 어디서 얻는지를 적는다(`report_id` — `find_reports` 의 `items`, `case_key` — `report_worst_cases` 의 `case_key`).

### 2-4. ThermalShockMCP — `app/mcp_server.py`(2 도구 · 6 인자) — 지금 도는 세션 없음

| 도구 | 자리 | 인자 | 뜻이 적힌 곳 |
|---|---|---|---|
| `predict_sed` | :163 | `sample: dict`(필수) | :164-171 · 칸의 뜻과 단위는 `app/schemas.py:14-39` `SedInput` |
| `sed_sample_from_odb` | :187 | `ap_part: dict` · `pkg_part: dict`(둘 다 필수) · `interposer: dict \| None = None` · `job: dict \| None = None` · `human: dict \| None = None` | :189-198 |

`SedInput`(`app/schemas.py:14-39`)은 칸마다 설명과 단위가 있고 :24 주석은 '이 설명은 MCP 도구 스키마로 LLM 에게 그대로 간다' 고 적었다. 그런데
도구가 `sample: dict` 로 받아 그 설명이 inputSchema 에 닿지 않는다 — 게이트웨이 셈은 0/20 이다. `sed_sample_from_odb` 의 dict 넷은 어느 도구의
응답을 그대로 넣는지(odb-hub `get_part_detail` · `get_interposer_result` · `list_jobs` · `find_job` 의 항목 · 사람이 정한 칸)를 적으면 된다.

## 3. 따라 할 꼴 — 리스크 앱 `ae4af1d`

리스크 앱(HWAXRisk)이 같은 일을 했다 — 도구 31종의 인자 134개에 설명을 달아 게이트웨이 셈이 0 → 134/134(단위 · 범위 0 → 33)가 됐다. 형 · 기본값 ·
필수 · 순서는 그대로 두었다. 한 쌍만 옮긴다(`backend/app/mcp_server.py`).

전(`ae4af1d^`)

```python
def risk_similar_projects(project_id: str, k: int = 5) -> dict:
    ...
        routes.get_store(), pid, max(1, min(20, int(k))), owner_sub=owner_sub,
```

뒤(`ae4af1d`)

```python
# 유사 과제 k 의 상한 — risk_similar_projects 가 1 과 이 값 사이로 죈다(인자 설명도 이 값을 읽는다).
SIMILAR_K_MAX = 20
_A_PROJECT_ID = "과제 id(risk_list_projects 의 projects[].id · risk_create_project 응답의 id)."
_A_SIMILAR_K = f"과제 수 — 벡터 · 서술 경로와 합친 목록(merged)에 건다(계보 · subject 경로는 아니다). 1~{SIMILAR_K_MAX} 사이로 죈다."

def risk_similar_projects(project_id: Annotated[str, Field(description=_A_PROJECT_ID)],
                          k: Annotated[int, Field(description=_A_SIMILAR_K)] = 5) -> dict:
    ...
        routes.get_store(), pid, max(1, min(SIMILAR_K_MAX, int(k))), owner_sub=owner_sub,
```

읽을 것 셋.
- **값의 종류 · 어디서 얻나 · 범위를 한 줄에** — id 는 어느 도구의 어느 칸에서 오는지, 수는 범위와 단위를 적는다.
- **수를 손으로 옮기지 않는다** — 상한 20 을 상수 `SIMILAR_K_MAX` 로 올리고 설명과 코드가 같은 상수를 읽는다. 허용값도 코드의 목록 · `Literal` 에서 만든다.
- **시험이 지킨다** — `backend/tests/test_mcp_arg_descriptions.py`(설명 빠짐 0 · 설명의 상한이 상수에서 · 허용값이 코드와 같음)와
  `backend/tests/fixtures/mcp_arg_contract.json`(설명을 달기 전 main 에서 뜬 인자 계약 — 형 · 기본값 · 필수 · 순서가 그대로인지).

## 4. 받아들임

1. **그 리포의 시험** — 이 요청의 도구마다 FastMCP 목록(`mcp.list_tools()`)으로 본 inputSchema 의 맨 위 인자 전부에 공백 아닌 `description` 이 있다.
   인자 계약(형 · 기본값 · 필수 · 순서)은 바꾸기 전과 같다.
2. **dev 게이트웨이** — 그 앱의 새 판이 dev 에 뜬 뒤(HEAX 앱은 SIF 를 갈고, KooRemapper 는 그 리포의 재기동 길로 MCP 인스턴스를 다시 띄운다)
   게이트웨이 재집계(60초 주기) 한두 번 뒤 `/tools-map` 의 `arg_scores` 에서 이 도구들의 described == args 다. 점수판은 앱마다 합계와 '설명이 빠진
   도구' 다섯만 싣는다 — 그래서 이렇게 읽는다. 그 앱의 `described` 가 이 요청의 인자 수 이상 오르고(LaminateAnalyzerMCP ≥ 22 · StepForge ≥ 20 ·
   KooRemapper ≥ 36 · ThermalShockMCP ≥ 6), 이 도구들이 그 앱의 `worst` 에 없다. 도구 하나하나의 확인은 1 의 시험이 한다.

   ```bash
   curl -s --noproxy '*' http://127.0.0.1:9110/tools-map | python3 -c '
   import json, sys
   rows = json.load(sys.stdin)["arg_scores"]["apps"]
   for r in rows:
       if r["app"] in ("heax-laminate_analyzer_mcp", "heax-step_forge", "heax-kooremapper_mcp", "heax-thermal_shock_mcp"):
           print(r["app"], r["described"], "/", r["args"], [w["tool"] for w in r["worst"]])'
   ```
3. (가능하면) 단위가 있는 값은 설명에 단위를, 허용값이 정해진 값은 허용값을 적어 `unit_or_range` 도 오른다. 필수는 아니다.

## 5. 하지 않을 것

- 형 · 기본값 · 필수 · 매개변수 순서를 바꾸지 않는다 — 설명만 단다. 특히 `dict` 인자를 pydantic 모델로 바꾸지 않는다. 검증이 도구 앞(FastMCP)으로
  옮겨 가 지금의 오류 봉투(LaminateAnalyzerMCP `_guarded` 의 E 코드 · ThermalShockMCP `envelope`)가 MCP 검증 오류로 바뀐다. 바꾸고 싶으면 따로 정한다.
- 상한 · 허용값을 설명에 손으로 옮겨 적지 않는다 — 코드의 상수 · 목록에서 읽는다(낡지 않게).
- 긴 규칙을 인자 설명에 복사하지 않는다 — 한 줄로 쓰고 자세한 것은 도구 설명을 가리킨다.
- `title` 에 적지 않는다 — 게이트웨이는 `description` 만 센다.
- 포털 · 게이트웨이는 고치지 않는다 — 점수판은 세기만 한다(막지도 숨기지도 않는다).

## 6. 누가 답하나

| 절 | 받는 곳 | 끝나면 알려 줄 것 |
|---|---|---|
| 2-1 | LaminateAnalyzerMCP 세션 | 커밋 · dev 에 SIF 를 간 시각 |
| 2-2 | StepForge 세션 | 같다(전체 회귀는 그쪽 몫) |
| 2-3 | KooRemapper 세션 | 커밋 · MCP 인스턴스를 다시 띄운 시각 |
| 2-4 | ThermalShockMCP — **도는 세션 없음** | 사용자가 그 세션을 열 때 이 절을 넘긴다 |

답은 포털 메인 세션이 받아 [triage-1031](../triage-1031.md) B37 과 절차 체크리스트의 그 줄에 적는다.
