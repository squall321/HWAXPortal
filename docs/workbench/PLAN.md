# 워크벤치 — 업무 절차 인벤토리

한 번 해낸 일을 **절차로 굳혀 두었다가, 대상만 바꿔 다시 돌린다.**

목표 사례 — ODB++ 를 가져와 열충격 SED 를 계산하고 보고서를 만들어 Report Archive 에
남기는 일이, 과제가 바뀌면 입력만 갈아 끼워 같은 절차로 돌아가는 것.

## 사용자가 말한 것 (2026-09-14)

① 한 번 해낸 일을 절차로 굳혀 두었다가 대상만 바꿔 다시 돌린다 — **챗으로 한 일을 기억했다가
재생**하는 것까지 포함해서.
② 챗·심의에 지장 없는 **독립 구성**.
③ (개정 2 에서 결정) ODB 는 cae00 `odb-hub` 로 간다 — 로컬 ODB 엔진은 쓰지 않는다.

> ① 의 후반(챗 기록 → 재생)은 조사 결과 선택 단계 S7 로 내렸다 — 이유는
> [context-notes W-1·W-11](context-notes.md).

| 문서 | |
|---|---|
| [recipes.md](recipes.md) | **정본 예제 레시피 넷** — 무엇을 하는 물건인지는 이것이 정한다 |
| [checklist.md](checklist.md) | 실행 항목 |
| [context-notes.md](context-notes.md) | **왜 그렇게 했는지** — 판단을 바꾼 자리 포함 |
| [odb-request.md](odb-request.md) | cae00 에서 받아 올 것(사용자 30분) |

이 계획은 2026-09-14 실물 조사 위에 세웠다 — 게이트웨이 465종 전수 스키마, 대화 저장소
실데이터, 감사 원장 12,393줄, 페르소나 796명 전수. 같은 날 **개정 3** 에서 다중 에이전트
반박을 거쳤다 — 주장 20건 검증(7건 정정), 발견 111건 → 클러스터 31개 반박 → 65건 반영,
20건 병합, 완결성 결손 8건 추가. 방법과 탈락 이유는 context-notes W-14.

---

## 1. 어떻게 쓰는 물건인가

워크벤치에서 **도구를 한 단계씩 돌린다.** 워크벤치가 그 과정을 전부 기록한다. 끝나면
**"레시피로 저장"** 을 누르고, 어떤 값이 과제마다 바뀌는지 표시한다. 다음 과제에서는 그 값만
채우면 **한 번에 재생**된다. 레시피는 서버에 쌓이고 남과 공유된다.

**진입점은 빈 런이다** — 레시피 목록이 아니다. 레시피가 하나도 없어도 도구를 한 단계씩
돌리는 것부터 시작한다.

핵심은 **워크벤치가 자기 관측자**라는 것이다. 챗 기록을 해석해 절차를 복원하려 들면 지금
기록으로는 안 된다(§5-5). 워크벤치 안에서 한 일은 **기록이 곧 절차**라 해석이 필요 없다.

---

## 2. 만들 것

### 레시피

```yaml
id: thermal-shock-sed
version: 1
title: 열충격 SED 판정
vars:                                   # 과제마다 바뀌는 값
  - {key: odb_job,  label: "ODB 잡 ID", type: string, required: true}
  - {key: pkg_type, label: "패키지 분류", type: enum, values: [WLP, FX, DIG],
     required: true, why: "형상 데이터로 유도할 수 없습니다"}
steps:
  - backend: odb-hub                    # 앱 키 + 원본 이름 — 노출 이름은 뒤집힌다(§5-8)
    tool: odb_list_components
    args: {job_id: "{{odb_job}}"}
    save: {ap_cx: "ap.x", ap_cy: "ap.y"}          # 결과에서 뽑아 다음 단계로
  - backend: heax-thermal_shock_mcp
    tool: predict_sed
    args: {sample: {ap_cx: "{{ap_cx}}", pkg_type: "{{pkg_type}}"}}   # 10개는 sample 안에
  - backend: reportarchive
    tool: create_report_draft
    gate: human                         # 사람 확인 자리 — 이 도구는 실행기가 강제한다(§5-4)
    args: {…}
```

기계장치는 **둘뿐이다** — 변수 치환 `{{var}}` 과 결과 추출 `save`.
조건 분기·반복·병렬·대기는 v1 에 넣지 않는다(§4). 두 장치의 의미는 v1 에서 **고정**한다 —
레시피는 공유 자산이라 뒤에 바꾸면 기존 레시피의 뜻이 바뀐다.

| 장치 | 규칙 |
|---|---|
| `{{var}}` | 인자 값이 정확히 `"{{var}}"` 하나면 저장된 JSON 값을 **형 그대로** 넣는다(숫자·객체·배열 유지). 문자열 안에 섞이면 문자열 치환. 치환은 파싱된 JSON 의 문자열 리프에서만 하고 문서 전체를 문자열 템플릿으로 다루지 않는다. 변수 값은 스키마 타입으로 검증한다. 예약 변수 `{{me.email}}`·`{{me.sub}}`(실행자 principal)·`{{run_id}}` |
| `save` | 입력은 결과 `content[]` 의 text 항목을 이어붙여 `json.loads` 한 값이다(`structuredContent` 는 앱마다 있고 없고 모양이 달라 기대지 않는다). 다중 text 항목은 각각 파싱해 리스트로, 이미지 등 비텍스트 항목은 런 기록의 별도 필드로. 경로는 `a.b[0].c` 꼴 점·인덱스 표기로 제한하고 **20줄 안팎으로 직접 푼다**(jsonpath 의존성 없음). 추출은 저장·절단 **전에** 원문에서 한다. 풀린 값이 null·빈 문자열·빈 배열이면 그 단계에서 **정지**한다(RA 는 0행 표를 조용히 만든다). SmartTwin 류 이중 포장(`stdout` 문자열 안 JSON)은 단계 옵션 `unwrap: stdout` 하나로 받거나 v1 첫 레시피 밖으로 둔다 |

변수 `type` 은 `string`·`enum`·`number`·`boolean`·`json` 다섯이다.
인자 입력은 **2단**이다 — 스키마에 `properties` 가 있으면 타입별 폼, 속성 없는 `object`·`array`
(465종 중 44종 — `predict_sed` 의 `sample`, `create_report_draft` 의 `blocks`)는 원문 JSON
textarea 에 도구 설명을 접이식으로 곁들인다.

### 런

레시피를 한 번 실행한 기록이다. 단계마다 **백엔드·도구·전문 인자(+sha256)·전문 결과·시각·
소요·성공 여부·모드·명의 메모·`notes`** 를 남긴다. 이 기록에서 레시피를 되뽑을 수 있으므로
**"하고 나서 저장" 이 성립한다.**

- **성공 여부는 코드가 §5-6 규칙으로 판정한다** — `isError` 만 보면 실패 다섯 모양 중 셋이
  성공으로 기록된다.
- 상태 어휘 — 런 `queued`·`running`·`gated`·`done`·`failed`·`cancelled`·`unknown`,
  단계 `pending`·`running`·`done`·`failed`·`unknown`·`skipped`. 단계는 도구를 부르기 **전에**
  `running` 을 먼저 저장한다. 포털 기동 시 `running` 이던 단계는 `unknown(stage=restart)`,
  그 런은 `failed(stage=restart)` 로 마감한다(쓰기가 뒤늦게 완료됐을 수 있어 `failed` 가 아니라
  `unknown` 이다).
- 결과 저장 — `result_gz`(gzip BLOB) + `result_bytes` + `result_sha256`. 원문 2MB 초과는 본문을
  안 넣고 해시·크기·앞 4KB 프리뷰만 `truncated=1` 로. 이미지(`ImageContent`)는 sqlite 가
  아니라 `workbench-artifacts/<run>/<step>-<n>.<ext>` 파일로. 본문은 **90일 뒤 비우고** 인자·
  해시·크기·메타·성공 여부는 영구 보존한다. 런 삭제는 소유자가 명시적으로 부를 때만.
  실측 근거 — `list_agents` 결과 916,756자, `plot_ashby` base64 72,396자, 워크벤치는
  agent-server 의 절단·이미지 강등을 안 타고 게이트웨이는 content 를 그대로 통과시킨다.
- `notes`(JSON, 4KB) — 도구가 결과 속에 넣어 준 경고·모델 출처·버전을 어댑터가 뽑아 올리는 칸.
  §5-4 의 "경고를 반드시 싣는다" 를 받는 자리이고, S5 비교표가 열로 보인다.
- **워크벤치 런 기록이 감사 정본이다** — 게이트웨이 원장은 MCP 경로에서 호출자를 안 적는다
  (§3). 수정·삭제 API 없이 append-only.
- 런은 `inputs_json`(그 실행에 넣은 변수 값 전부)·`origin`(`manual` 한 단계씩 / `replay`
  재생)·`run_by`·`owner_sub`·`mode`(`plan`|`live`) 를 갖는다 — §6-1 판정에 필요하고 사후에
  복원할 수 없다.

### 저장 모델 — 표 다섯

```
recipes         (id, owner_sub, visibility, title, created_by, latest_version)
recipe_versions (version_id PK, recipe_id, version_no, spec_json 불변, author_sub, created_at,
                 derived_from_run NULL 허용)
runs            (id, owner_sub, run_by, recipe_version_id NULL 허용, inputs_json, origin, mode,
                 state, started_at, ended_at, cancelled_by, cancelled_at)
run_steps       (run_id, ix, backend, tool, schema_fp, expect, args_json, args_sha256,
                 result_gz, result_bytes, result_sha256, truncated, notes,
                 state, ok, error, started_at, duration_ms, mode, identity_note, reused_from_run_id)
run_gate_acks   (run_id, step_ix, ack_by, ack_at, args_sha256, args_override_json)
```

런은 판본 행 id(`recipe_version_id`)를 들고 재생은 항상 그 id 로 한다(HEAXHub
`jobs.app_version_id` FK 방식, `(recipe_id, version)` 복합키가 아니다). 새 판본은 `spec_json`
(vars·steps)이 바뀔 때만 만들고 제목·설명 수정은 `recipes` 행 메타 갱신으로 끝낸다. 워크벤치에서
한 단계씩 돌린 뒤 "레시피로 저장" 한 런은 `recipe_version_id` 가 NULL 이고 새 판본이
`derived_from_run` 으로 그 런을 가리킨다. 게이트 승인은 별도 행으로 남겨 승인자와 실행자가
달라도 감사가 된다(HWAXRisk `rr_gate_acks` 선례). 재개 시 재사용한 단계는 `reused_from_run_id`.

### 2-1. 정본 — 어디에 살고 무엇으로 검증하나

| 정본 | 위치·방식 |
|---|---|
| 레시피·런 모델 | `backend/app/workbench/models.py` — pydantic v2(포털 관례. `jsonschema` 의존성이 없다). 위 YAML 은 예시이고 이 파일이 정본이다. 저장 시 검증 = pydantic 파싱 + must-gate·비밀 키·미지 인자 검사(§5-4·§5-6) |
| API | prefix **`/workbench-api`** — SPA 경로 `/workbench/*` 와 겹치지 않게(`App.tsx` 가 `/changelog` API 와 `/updates` SPA 를 가른 것과 같은 이유). `vite.config.ts` 프록시 1줄과 `include_router` 가 같은 값을 쓴다. SSE 없음, 진행은 GET 폴링 |
| 화면 흐름 | 워크벤치(빈 런에서 도구 한 단계씩) → "레시피로 저장"(변수 표시) → 레시피 목록 → 상세(판본·런 이력) → 실행(변수 폼 → 계획 모드 확인 → 진행 → 게이트 확인) → 런 상세 |

```
GET  /workbench-api/tools                      사용자 PAT tools/list + /tools-map 라벨(§3)
GET  /workbench-api/recipes · POST             GET /recipes/{id}(판본·내 런 이력)
POST /workbench-api/recipes/{id}/versions      GET /recipes/{id}/export · POST /recipes/import  (YAML)
POST /workbench-api/runs                       body {recipe_id?, version?, vars, mode=plan} → 202
                                               recipe_id 없으면 빈 런 = 한 단계씩 돌리는 워크벤치
POST /workbench-api/runs/{id}/steps            빈 런에 단계 하나 {backend, tool, args} → 202, running 이면 409
GET  /workbench-api/runs · /runs/{id}          폴링. 목록은 내 것만, 확인 대기가 맨 위
POST /workbench-api/runs/{id}/steps/{ix}/ack   gate: human 확인(소유자만, 인자 sha256 귀속)
POST /workbench-api/runs/{id}/resume           실패·unknown 단계부터 재개(소유자만)
POST /workbench-api/runs/{id}/cancel           단계 경계에서 반영(소유자·portal-admin)
POST /workbench-api/runs/{id}/save-as-recipe   어느 인자가 변수인지
GET  /workbench-api/health(무인증) · GET /workbench-api/stats(portal-admin, §6-1)
```

---

## 3. 어디에 만드나 — 포털 안의 격리 모듈

독립성은 **별도 프로세스가 아니라 공유 자원을 안 건드리는 것**으로 얻는다.

| 자원 | 워크벤치가 | 안 그러면 |
|---|---|---|
| `agent_semaphore`(64) | 자기 것을 만든다(크기 `workbench_concurrency`, 기본 2) | 넘치면 큐 없이 **429** — 챗이 막힌다 |
| `agent_client`(풀 64) | 자기 것을 만든다 | read 타임아웃이 없어 풀을 먹으면 챗이 **조용히 멈춘다** |
| `conv_store` | 자기 sqlite(WAL·스레드별 연결·busy_timeout) | 연결 1개 + Lock · WAL 없음(디스크 실측 `journal_mode=delete` ×4) · async 안 동기 호출 |
| agent-server | **안 쓴다** | 인증 0 · 전역 가변 상태 12개 이상 · 아티팩트 정리에 네임스페이스 없음 |
| 게이트웨이 백엔드 영속 세션 | **공유 — 피할 수 없다** | 호출이 120초(`gateway.py:57`)를 넘거나 예외가 나면 게이트웨이가 그 백엔드 세션을 재연결하고, 그 순간 같은 백엔드에 걸려 있던 챗·심의 호출이 끊긴다(원장 실측 reconnected 40건). 그래서 **120초를 넘길 수 있는 동기 도구는 레시피에 안 넣는다** |
| 게이트웨이 `verify_answer` 증거칸 | 공유 — 알려진 한계 | 같은 사용자 PAT 로 부르면 그 사람의 최근 도구 출력 20건 칸에 쌓여, 개인 Claude 로 심의 중이면 배치 몇 건에 실제 근거가 밀린다. v1 밖 |

`TOOL_MAX` 는 agent-server 바인딩 캡이라 워크벤치 실행기와 **무관**하다.

### 사용자 명의 — 정확히 어디까지인가

포털은 이미 사용자 명의로 게이트웨이를 부를 수 있다 — `_chat_user_pat`
(`backend/app/agent/routes.py:223`) 이 단명 PAT 를 찍고 게이트웨이가 포털 JWKS 로 검증한다.
그러나 그것이 참인 범위는 **게이트웨이의 인가·읽기 캐시 키·거절까지**다. 백엔드까지 신원이
닿는 것은 라이브 백엔드 16개 중 **4개**뿐이다.

| 갈래 | 백엔드 | 백엔드에 닿는 신원 |
|---|---|---|
| per-user SSO | `heax-hwax_risk` · `heax-kooremapper_mcp` | 실행자 |
| 포털 연결 토큰 | `reportarchive` | **RA 토큰을 포털에 등록한 사용자만**. 미등록이면 게이트웨이가 **조용히 서비스 계정으로 폴백**한다(`gateway.py:1882-1890·1929-1931`, 결과에 표식 없음) |
| 신원 헤더 | `hwax-deliberation` | 실행자 |
| 나머지 12개 | `heax-step_forge`·`heax-thermal_shock_mcp`·`odb-hub`·… | **서비스 계정**(영속 세션) — 감사행에 caller 도 없다 |

→ 목표 사례의 `predict_sed` 와 첫 레시피의 StepForge 단계는 백엔드에서 서비스 계정 소유가
된다. 실행기는 예약 변수 `{{me.email}}`·`{{me.sub}}` 로 소유 인자(`intake` 의 `owner` 처럼)를
실행자로 박을 수 있게 한다. RA 단계가 있으면 **실행 전에 연결 등록을 확인**하고 없으면 시작을
거절한다(`/upload/dispatch` 와 같은 400 문구). odb-hub 는 서비스 토큰 하나로 붙어 있어
"신원 위임 배선이 필요 없다" 는 말이 **해당하지 않는다** — S0 에서 시야를 확인한다.

**레시피는 실행자 명의·권한으로 돈다. 작성자 권한을 물려받지 않는다.** 런 시작 전에 실행자
PAT 로 `tools/list` 를 받아 레시피 단계의 도구가 하나라도 없으면 한 단계도 실행하지 않고
거절한다 — 안 그러면 권한 밖 도구가 N번째 단계에서야 `forbidden` 으로 멈추고 앞 단계
부수효과는 이미 나 있다.

### 감사 — 런 기록이 정본이다

"`invoke_tool` 이 감사를 그대로 탄다" 는 과장이었다. 게이트웨이 `audit.jsonl` 은 MCP 경로에서
호출자를 안 적고(`gateway.py:227-233` — caller 는 REST 프록시만 넘김), 신원은 위 세 갈래에서만
note 로 남으며, cache-hit 과 그 밖의 백엔드는 신원이 없다(실측 최근 400행 caller 0건·신원 8건).
PAT 는 30분 창 결정적이라 단계별 식별자도 못 싣는다. 그래서 워크벤치 런 기록이 감사 정본이고
게이트웨이 원장과는 시각·도구·백엔드로 근사 대조만 한다. 게이트웨이 쪽에 호출자를 남길지는
§7 결정이다.

### 접점 — 챗·심의 파일 0줄

```
backend/app/workbench/{__init__,models,routes,store,runner}.py   신규
backend/app/main.py            import + include_router(prefix /workbench-api) 를 :156
                               `if settings.serve_frontend:` 블록보다 위에. try/except 로 감싸
                               실패하면 라우터를 빼고 포털(챗 릴레이)은 뜬다
frontend/src/pages/workbench/*.tsx            신규
frontend/src/state/WorkbenchContext.tsx       /workbench/* 라우트 요소 안에서만 Provider. useChat 안 씀
frontend/src/App.tsx           라우트 1개 — path "/workbench/*" 에 자식 recipes/:id · runs/:id
frontend/src/components/layout/AppHeader.tsx  메뉴 1개
backend/config/access.yaml     features: workbench (선언) — 라우트마다 ensure(principal, "feat:workbench") 1줄
frontend/vite.config.ts        dev 프록시 1줄 ('/workbench-api')
infra/services.yaml · start.sh · backup-local.sh(3줄) · config.py    새 sqlite 등록(4곳)
infra/services.yaml            workbench-artifacts blob 클래스 1줄
```

`feat:workbench` 는 "코드 0" 이 아니다 — `features` 키는 타일·게이트웨이 백엔드만 자동으로
묶고, 기능 권한은 각 라우트가 `ensure` 를 불러야 걸린다. "재기동 0" 은 맞다.

### 3-1. 배포·재기동

| 변경 | 반영 |
|---|---|
| `access.yaml` `feat:workbench` | 저장 즉시(mtime 재로드) |
| `backend/app/workbench/*`·`main.py` | 포털 재기동 — dev `apptainer instance stop hwax_portal && ./infra/scripts/start.sh`, cae00 `update-forges.sh chat` |
| 프론트 | dev `cd frontend && pnpm build && ./infra/scripts/images-to-drive.sh`(dist 를 Drive `latest/` 로) → git push. cae00 은 `chat` 갱신에 포함 |
| `requirements.txt`·`package.json` | **바꾸지 않는다** — 아래 |

⚠ 포털 재기동은 진행 중인 챗·심의 SSE 를 끊는다(`/agent/` 릴레이가 포털을 지난다).
`update-forges.sh chat` 은 게이트웨이·agent-server 도 함께 재기동한다. 사용 적은 시간에 한다.

**새 pip 의존성 0.** 코드는 바인드 마운트라 pull 로 가지만 파이썬 패키지는 SIF 에 구워진다
(`infra/apptainer/portal.def`). cae00 은 pip 을 못 쓰고 Drive 의 `portal.sif` 를 덮어쓰므로
`requirements.txt` 한 줄이 곧 dev 리빌드·Drive 왕복이고, 빼먹으면 cae00 포털과 챗 릴레이가
ImportError 로 같이 죽는다. 게이트웨이 호출은 `mcp` 패키지 없이 httpx JSON-RPC(`upload.py:282`
`mcp_call` 의 방식)로 한다. **새 npm 의존성도 0** — 의존성 5개뿐이고 cae00 은 오프라인 pnpm 이다.
트리·편집기·폼 라이브러리를 들이지 않는다.

### 3-2. 멈추는 손잡이와 상한

런은 **소유자가 멈출 수 있어야 한다** — `POST …/runs/{id}/cancel`. 진행 중 도구 호출은 끝까지
가고 다음 단계 경계에서 `cancelled` 가 되며 누가 언제 멈췄는지 남긴다. portal-admin 은 남의 런도
멈출 수 있다. 취소가 없으면 폭주 런을 세우는 길이 포털 재기동뿐이고 그 순간 챗이 끊긴다 —
"챗에 지장 없음" 이 실패 경로에서 깨진다.

상한은 Settings 둘 — `workbench_concurrency`(기본 2, 심의 `DELIB_JOB_MAX_RUNNING`·HWAXRisk
`risk_concurrency` 와 같다. `gate: human` 대기 런은 슬롯을 쥐지 않는다) ·
`workbench_max_steps`(저장 시점 거절). 상한에 걸리면 429 가 아니라 큐에서 기다린다. 사용자별
상한·관리자 목록 화면은 v1 에 없다(스택 어디에도 선례가 없다).

### 3-3. 접을 때

위 접점 표를 거꾸로 밟는다. 순서 하나만 지킨다 — `access.yaml` 에서 `workbench` 를 빼기
**전에** 개별 허가로 `feat:workbench` 를 받은 사용자 행부터 지운다(빼고 나면 `AccessAdmin`
저장이 그 키를 되돌려보내 422). sqlite 파일은 남기고 사람이 지운다(D7). 런이 외부 앱에 만든
것은 런 기록의 전문 결과에 ID 가 있다 — 별도 색인은 두지 않는다.

저장소는 독립 sqlite 로 둔다 — 쓸모가 증명되면(§6-1) **언제든 별도 앱으로 떼어낼 수 있게.**

---

## 4. v1 에 **안** 넣는 것

현실성의 절반은 안 만드는 목록이다.

| 안 넣는 것 | 왜 |
|---|---|
| 조건 분기·반복·병렬·**대기(`wait`·폴링)** | 목표 사례가 **직선**이다. 넣으면 미니 언어를 만들게 된다. 잡을 거는 도구(`intake`·`run_job` 류)는 레시피 **밖**에 두고 결과 ID 를 변수로 받는다 |
| 파일 변수·파일 보관소 | 파일을 나르는 단계는 레시피 밖이다. 포털 스테이징은 6시간 뒤 지워지고 호스트 경로 전제라 레시피가 들고 다닐 수 없다 |
| 능력 기반 재바인딩(`accepts`/`produces`) | 계약은 있는데 **데이터가 비었다** — `describe_data_capability("CAD")` 의 `capability_tools` 가 0건 |
| 앱 간 잡 규격 정규화(8종) | 목표 사례가 닿는 건 1~2개다 |
| 레시피 MCP 표면·`evidence.json` 류 외부 표면 | 있으면 좋지만 v1 가치에 필수가 아니다 |
| 스케줄 실행(cron) | 쌓인 레시피가 있어야 의미가 있다 |
| 알림 채널(헤더 배지·메일) | 포털에 사용자 대상 알림 표면이 없다. 게이트 대기 런의 표면은 **런 목록**이다 |
| 사용자별 실행 상한·관리자 런 목록 화면 | 스택 전부 전역 상한이고 HWAXRisk 잡 조작도 소유자 전용이다 |
| 심의 파이프라인 흡수·대체 | `infra/pipeline/*.js` 1,801줄은 심의 전용이고 그대로 둔다 |
| 게이트웨이에 순서 개념·캐시 우회·호출자 기록 추가 | 게이트웨이는 순수 프록시로 둔다. 호출자 기록은 §7 결정 |

---

## 5. 제약 — 계획이 이미 흡수한 것들

### 5-1. 공급자가 없으면 실패하지 않는다. 사람에게 묻는다

`predict_sed` 의 인자는 `sample`(object) **하나**가 필수이고, 그 안에 10개가 필수다
(`board_type`·`ap_cx`·`ap_cy`·`pkg_cx`·`pkg_cy`·`pkg_type`·`pkg_x`·`pkg_y`·`ball_size`·
`pad_size`), 선택 5개(`ap_x`·`ap_y`·`ap_type`·`project`·`pkg`), 그 외 키는 서버
`extra="forbid"` 로 통째 거부(E100). 10개를 최상위에 평탄하게 넘기면 "sample Field required" 다.

| 입력 | 나오는 곳 |
|---|---|
| `ap_c*` · `pkg_c*` | ODB 좌표 + **부품 선별**(사내 규칙 또는 `ap_refdes`·`pkg_refdes` 변수) — 부품 목록은 수천 개를 주지 "이 보드의 AP" 를 주지 않는다 |
| `board_type` · `ball_size` · `pad_size` | **ODB 만** — 단, `board_type` 어휘 대응과 HALF/FULL 판정 규칙은 S0 확인 사항 |
| `pkg_x` · `pkg_y` | ODB bbox 또는 STEP `part_info` |
| **`pkg_type`** | **어디서도 안 나온다** — 패키지 기술 분류 |

그리고 465종 중 **SedInput 을 만들어 주는 어댑터가 0개다.**

→ 공급자 없는 값은 레시피의 **변수**로 내려간다. 레시피는 그대로 돌고 사람이 채우는 칸만
늘어난다. 도구가 나중에 붙으면 **같은 레시피가 손대지 않고** 무인으로 돈다.

### 5-2. ODB 는 cae00 전용 — dev 에서 시험할 수 없다

dev 게이트웨이에 odb 도구 **0/465**, REST 차단, 소스 없음, **도구 이름조차 모른다.**

→ **고정물(fixture) 기반 개발.** cae00 에서 받은 도구 목록·응답 표본을 리포에 넣고 어댑터를
만든다. 실주행 검증은 cae00 에서 한다. 받아 올 것은 [odb-request.md](odb-request.md) 에 있다.
dev 에서 만든 레시피는 sqlite `sync: mirror` 라 동기화로는 cae00 에 안 간다 — **YAML
export/import** 로 옮기고 `docs/workbench/fixtures/` 에 커밋한다(레시피가 이미 YAML 이라 새 형식은
없다).

### 5-3. A→Z 가 끊기는 진짜 이유는 과제 키다

```
StepForge     project_id  23-hex(시간접두 13 + uuid 10)
DynaForge     session_id  ULID 26자 · 소유자 + 전사/부서/팀 공개 범위
ThermalShock  project     문자열 메타(기본 "unknown")
ReportArchive project     list_analysis_runs 의 project_name 부분일치 필터(KG '과제' 축은 dev 에서 비어 있음)
HWAXRisk      target_key  kind:ref_id + 자체 project_id
```

포털 전역으로 다섯을 묶는 것이 **없다.** 단 HWAXRisk 의 `rr_sources`(kind mcad/dyna/ecad,
`ref_json` 에 `stepforge_project_id`·`session_id`)와 `rr_projects.ra_entity_id` 가 이미
StepForge·DynaForge·RA 를 HWAXRisk `project_id` 아래 **부분적으로** 묶고 있다 — S6 은 0 에서
만들지 말고 이것을 확장·재사용할지 먼저 정한다(§7). 여전히 안 묶이는 것은 ThermalShock
`project` 와 RA 해석 런 `project` 문자열이다. v1 은 레시피 `vars` 에 앱별 키를 명시하고 런
기록에 그대로 남기는 것까지다.

### 5-4. 사람 자리 넷 — 그리고 게이트는 실행기가 강제한다

전부 **의도된 설계**다.

1. `publish_report` 는 `preview_publish` 가 발급한 `confirm_token`(수명 600초,
   `ReportArchive/backend/app/modules/mounts/confirm.py:28`)을 요구한다 — 2단 확인.
2. `risk_add_finding` 은 `cites` 0건이면 REST 422 `cites_required`, MCP 는
   `{"error": "cites_required"}`(isError=false — §5-6 ④ 모양). `claim` 은 2000자 이하 산문,
   `warrant` 는 생략 가능. `severity`·`judgement`·`direction` 만 422 검증이고 `mechanism`·`domain` 은 **검증
   없이 어떤 문자열이든 저장**된다 — 그래서 어휘 대조는 코드가 `risk_taxonomy` 로 한다.
3. `pcb_warpage_surrogate` 가 스스로 경고한다 — *"합성 데이터로 학습한 데모. 절대값을
   판정·양산 의사결정 근거로 쓰지 마라."*
4. **태그 확정** — `suggest_report_tags` 는 후보만 돌려주고 **저장하지 않는다**. 검색에 걸리게
   하는 것은 `add_report_tags` 이고 그 독스트링이 "혼자 정하지 마라 — 사용자에게 보여주고
   확인받아라" 다. 안 달면 태그 기반 온톨로지 조회에서 빠진다(텍스트 검색으로는 찾힌다).

→ **`gate: human` 은 작성자 선택이 아니라 실행기가 강제한다.**

- **must-gate 목록** — `publish_report`·`request_unpublish`·`trash_report`·`restore_version`·
  `job_stop`·`risk_add_finding`·`add_report_tags` 가 든 단계에 `gate: human` 이 없으면 **저장
  시점에 거절**한다(작성자가 끌 수 없다). `submit_*`·`run_job`·`register_*`·`upload_*`·
  `ingest_*`·`train_model` 은 must-gate 가 아니라 저장 시 **경고 등급**으로 두어 S5 일괄 재생을
  살린다.
- 게이트웨이 `_INVOKE_DENY`(`gateway.py:1100-1101`, 접두 5·접미 2)는 **백스톱일 뿐** 워크벤치의
  안전 목록이 아니다 — `trash_report`·`job_stop`·`request_unpublish`·`restore_version` 이 그
  목록을 통과하고, `odb_delete_job` 같은 앱 접두 이름은 하나도 안 걸린다. `_CACHEABLE`
  접두사도 허용 목록으로 못 쓴다(`report_` 가 `report_ingest` 같은 쓰기를 연다).
- `save` 로 `confirm_token`·`*_token` 키를 뽑아 다음 단계 인자로 쓰는 레시피는 저장 시점에
  거절한다(RA 2단 확인 우회 차단).
- `publish_report` 앞 게이트 — 실행기가 `preview_publish` 를 불러 게시판·audience 수를 게이트
  카드에 놓고 사람 확인을 받은 뒤, `preview_publish` 를 **다시** 불러 그때 발급된 토큰으로
  곧바로 게시한다(두 호출 사이에 사람 대기를 두지 않아 600초에 안 걸린다). 두 번째 preview 의
  대상이 사람이 본 것과 다르면 게시하지 않고 다시 멈춘다. preview 는 게시하지 않는 호출이라
  두 번 불러도 무해하다.
- 화면 — 재생 시작 전 "되돌리기 어려운 단계 N개, 각 단계에서 멈춥니다" 와 그 목록을 먼저
  보여 준다. 게이트 카드에는 치환이 끝난 **실제 인자**와 직전 단계 결과를 놓는다. 게이트
  확인은 런 소유자만 할 수 있고 (run_id, step, sha256(치환 인자)) 에 묶인 1회용 값이라 확인 뒤
  인자가 바뀌면 무효다. 런 목록에서 "확인 대기" 런을 맨 위에 띄운다(탭을 닫아도 서버에 멈춰
  있다).
- 보고서 경로 — `create_report_draft(gate)` → `suggest_report_tags`(후보) → gate(사람이 고름)
  → `add_report_tags`. `create_report_from_run` 은 적재된 AnalysisRun(`status=ready`) 전용이라
  계산기 출력은 이 길로 못 간다.

런 기록에 **모델 출처·경고를 반드시 싣는다**(`notes`). "A to Z" 의 Z 는 게시가 아니라
**사람 앞에 놓는 것**이다.

### 5-5. 챗 기록으로는 절차를 복원할 수 없다

포털이 남기는 도구 활동은 문자열 다섯 개뿐이고 **호출과 결과를 짝지을 식별자가 없다.**

> 실증 — 한 메시지에서 `predict_sed` 가 `ap_cx=50.1 … 50.5` 로 다섯 번 병렬 호출됐는데
> **결과 다섯의 프리뷰가 전부 같다.**

→ §1 처럼 워크벤치가 자기 관측자면 이 문제를 **우회한다.** 관측 개선은 여전히 값어치가
있지만 **핵심 기능의 선행 조건은 아니다** — S7 의 전제일 뿐이다.

### 5-6. 단계 성공은 코드가 판정한다 — 실패 다섯 모양 중 셋은 `isError=false` 다

게이트웨이는 `@_low.call_tool(validate_input=False)`(`gateway.py:1766`) 라 **인자를 검증하지
않고**, 백엔드 pydantic 은 모르는 인자를 조용히 버린다(실측 `limitt` 오타 → 정상 응답).

| 실패 모양 | `isError` | 예 |
|---|---|---|
| ① 게이트웨이 평문 | true | `unknown tool:`·`forbidden:`·`backend … unavailable:` 접두 |
| ② pydantic 평문 | true | `Error executing tool …` |
| ③ 앱 봉투 | **false** | `{ok:false, data:null, errors:[…]}` — ThermalShockMCP `_guarded` |
| ④ `{error: …}` | **false** | ReportArchive `preview_publish` 검증 실패·HWAXRisk `cites_required` |
| ⑤ 빈 본문 | **false** | DynaForge `list_sessions` |

**실행 전** — `tools/list` 의 `inputSchema` 최상위 `required`·`properties` 로 인자를 직접 대조
한다(의존성 없이 키 대조). 스키마에 없는 최상위 키를 보내는 단계는 저장 시점에 거절한다.
`additionalProperties:true` 인 중첩 객체(`sample`) 안은 못 보므로 실행 후 판정에 맡긴다.

**실행 후** — 성공 = `isError=false` AND text 를 이어붙여 JSON 파싱이 되고(안 되면 그 단계가
`raw: true` 를 선언하지 않는 한 실패) AND 최상위 `ok===false`·최상위 `error` 키·비어 있지 않은
`errors[]`·`refused:true` 가 없음 AND `save` 경로가 전부 값으로 풀림. 하나라도 깨지면 그
단계에서 정지하고 빈 값을 다음 단계에 치환하지 않는다. 런 기록에는 세 층(MCP `isError`·파싱
가능·앱 봉투)과 게이트웨이 접두 분류를 따로 남긴다 — 권한·부재·불통은 재시도 판단이 다르다.

리포의 유일한 게이트웨이 호출 선례 `upload.mcp_call`(`upload.py:310-318`)은 JSON-RPC `error`
만 보고 `isError` 를 버려 `unknown tool` 이 `{"raw": …}` 로 **성공 반환**된다. 그 함수를
베끼지 않는다(§3 접점의 `runner.py`).

### 5-7. `dry_run` 은 두 뜻이다

① **계획 모드**(실행기 수준, 기본값) — 게이트웨이를 부르지 않는다. 치환·`required` 충족·
must-gate·deny 만 검사해 "부를 호출 목록" 을 보여 주고, 앞 단계 `save` 에 의존하는 인자는
'미검증' 으로 표시한다. 재생(S5 포함)은 이 모드로 시작해 사람이 끄고, 단계별 실행은 끈 채
시작한다.
② **도구 `dry_run`** — 그 도구의 스키마에 `dry_run` 이 있을 때만(465종 중 **16종**) 폼에
노출하고 실행기는 주입하지 않는다. 기본값도 도구마다 다르다(`slurm_submit_job` true,
`create_report_draft` false). **스키마에 없는 도구의 `args` 에 `dry_run` 이 적혀 있으면 저장
시점에 거절**한다 — 게이트웨이에 dry_run 처리가 없고 백엔드가 모르는 인자를 버리므로, 그대로
보내면 사용자는 시험이라 믿는데 과제·잡·보고서가 실제로 만들어진다.
런 기록의 단계마다 `mode: plan|dry|live` 를 남긴다.

### 5-8. 도구에는 판본이 없다 — 변화를 잡아 멈추는 것까지다

게이트웨이 노출 이름은 다른 앱의 가동 여부로 **뒤집힌다**(겹칠 때만 접두어를 붙인다,
`gateway.py:347-351`. StepForge 4개 도구 실측). `tools/list` 에 버전 필드가 없고 백엔드는 영속
세션 하나라 옛 판본을 다시 띄울 수 없다(16개 중 heax-* 9개만 HEAXHub 판본 개념이 있다).

→ 단계는 `backend`(앱 키)와 `tool`(원본 이름)을 따로 저장하고, 실행기는 항상 호출되는 별칭
`<백엔드키 하이픈 제거>_<원본>` 으로 부른다(`:339`·`:1814`. 파괴 도구 차단은 원본 이름 기준이라
우회 없음). 저장 시 `schema_fp = sha1(description + "\x00" + json.dumps(inputSchema,
sort_keys=True))[:16]`(게이트웨이 내부 `_tools_fp` 와 같은 식)을 박고, 실행 전 대조해 다르면
정지하고 diff 를 사람 앞에 놓는다 — 자동 진행 금지. `predict_sed` 처럼 `sample: dict` 인
도구는 지문이 내부 키를 못 잡으므로 런 기록과 `gate: human` 이 그 몫이다.

### 5-9. 게이트웨이 읽기 캐시 300초 — 0건도 캐시된다

원본 도구명이 `list_`·`get_`·`find_`·`search_`… 접두사면 게이트웨이가 (백엔드·도구·인자·
사용자) 키로 300초 캐시하고 **빈 결과도 캐시한다**(`gateway.py:140-152`, 우회 인자·헤더 없음).
같은 인자로 5분 안에 같은 단계를 다시 돌리면 캐시가 오고 응답에 표식이 없다. 비우는 유일한
길은 같은 백엔드의 비캐시 도구 호출이다(`:1839-1841`). 잡 상태 조회를 이 접두 도구로 만들면
낡은 '진행 중' 이 정상 응답처럼 온다 — 상태 조회 단계는 캐시 접두 이름을 저장 시점에
거절한다. `get_job`·`get_job_details` 를 `_CACHE_DENY` 에 넣는 것은 게이트웨이 쪽 별개
결손으로 기록만 한다.

### 5-10. 오래 걸리는 도구를 상정한다 — 상한은 120초이고 실측이 그 위에 있다

게이트웨이 호출 상한은 **120초**이고(`gateway.py:57`, infra 어디에도 override 가 없다) 넘기면
그 백엔드 **영속 세션이 재연결**되면서 같은 백엔드에 걸려 있던 챗·심의 호출까지 끊긴다. 게다가
게이트웨이는 재연결 뒤 **같은 인자로 한 번 더** 부른다 — 비멱등 쓰기가 두 번 난다.

실측이 이미 상한 위에 있다.

| 도구 | 실측 | 성격 |
|---|---|---|
| `search_catalog_property`·`search_by_property` | **120.3초** (세션 첫 호출, 3회 재현) · 이후 0.1초 | 콜드스타트 — **첫 호출이 잘린다** |
| `agent_search`(hybrid) | 102~221초 | 상시 |
| `list_materials` | 120초 | 상시 |
| 감사 원장 전체 | ≥60초 호출 **71건** | — |
| 적층 도구 · `thickness_report` · `mesh_size_advice` | 0.0~3.2초 | 빠름 |

→ 실행기가 넷을 한다.

1. **단계가 `expect` 를 선언한다** — `fast`(<5초) · `slow`(5~110초) · `job`(120초를 넘길 수
   있다). `job` 인 단계는 **저장 시점에 거절**하고 제출·회수 두 레시피로 가르게 한다(§4).
   선언은 사람이 하지만 **런 기록의 `duration_ms` 가 쌓이면 실측 p95 를 옆에 보여 준다** —
   워크벤치가 자기 관측자라는 §1 원칙이 여기에도 적용된다. 선언과 실측이 어긋나면 화면이 말한다.
2. **`warmup: true` 단계를 둔다** — 그 도구를 한 번 먼저 부르고 결과를 버린다. 타임아웃이 나도
   실패로 치지 않는다. 콜드스타트가 상한을 넘기는 도구(카탈로그 검색)를 정확히 푸는 자리다.
3. **실행기 httpx 타임아웃은 ≥260초** — 게이트웨이 120초 + 재연결 재시도 한 번을 덮는다.
   실행기가 먼저 포기하면 쓰기는 그 뒤 완료되고 런에는 `unknown` 만 남는다(§2 런).
4. **`slow` 단계가 도는 동안 같은 백엔드에 다른 단계를 걸지 않는다** — S5 일괄 재생의 동시
   상한이 "같은 백엔드에 동시 N" 인 이유다. 재연결이 나면 그 백엔드의 다른 런까지 끊긴다.

화면은 단계를 시작하기 전에 **"이 단계는 보통 N초 걸립니다"** 를 보인다(런 기록에서 계산).
사람이 기다릴지 나중에 볼지를 정할 수 있어야 폴링 화면이 고장으로 안 보인다.

읽기 캐시(§5-9)가 여기서는 유일하게 도움이 된다 — 느린 읽기 도구가 한 번 성공하면 300초 동안
같은 인자에 즉답이다. 재개·재실행이 그만큼 싸다.

---

---

## 6. 단계

각 단계는 **그 단계만으로 값어치가 있어야** 한다. 뒤가 취소돼도 앞이 쓸모없어지지 않게.

단계는 **[정본 예제 레시피 넷](recipes.md)** 위에 걸려 있다. S2~S4 는 각각 예제 하나를 세우고,
그때마다 **처음 증명되는 것**이 다르다.

| 단계 | 무엇 | 세우는 예제 | 크기 | 선행 |
|---|---|---|---|---|
| **S0** | cae00 API 수집 — [odb-request.md](odb-request.md) | (R3 선행) | 사용자 30분 | — |
| **S1** | 레시피 저장소 + 실행기 + 최소 화면 | 첫 레시피(3단계) | **가장 큼** | 없음 |
| **S2** | 적층 굴곡 수명 — **dev 완주 첫 실전** | **R1** | 작다 | S1 |
| **S3** | 낙하·충격 — 제출/회수 두 레시피 | **R2a·R2b** | 중간 | S1 |
| **S4** | ODB 어댑터 + 열충격 SED | **R3** | 중간 | **S0**, S1 |
| **S5** | 일괄 재생(변수 N개 + 비교표) | R1·R2 가 재료 | 작다 | S2~S4 **중 하나** |
| **S6** | 과제 키 레지스트리 | — | 중간 | S5 |
| **S7** | 챗 → 레시피 제안 *(선택)* | — | 불확실 | 관측 개선 |
| **S8** | 리스크 패턴화 | R2b 가 재료 | 중간 | S5 |

**S0 과 S1 은 병렬이다.** S1 의 첫 레시피는 실행기를 검증하는 **가장 단순한 것**으로 잡는다 —
파싱된 과제 `project_id` 를 변수로 → `list_parts` → `create_report_draft`(gate). 예제 넷이
아니라 시험용이다. 잡을 거는 도구(`intake`)는 레시피 밖이다(§4).

**S2~S4 는 서로 독립이다** — 셋 다 S1 만 있으면 되고, 무엇을 먼저 할지는 선행 조건이 가른다.

| 단계 | 처음 증명하는 것 | 어디서 도나 |
|---|---|---|
| **S2 (R1)** | 판단 단계 없이 **직선 체인이 끝까지** 간다. `save` 한 줄이 도구 넷을 잇는다 | **dev 완주** — 선행 0 |
| **S3 (R2)** | 잡 제출을 사람 확인 아래 두고, **제출과 회수를 가른다**(walltime 167시간) | dev 는 `dry_run` 까지 · 회수는 cae00 |
| **S4 (R3)** | 공급자 없는 값이 **사람이 채우는 칸**으로 내려간다(§5-1) | **cae00 전용** · S0 선행 |

→ **S2 를 먼저 권한다.** 선행이 없고 dev 에서 끝까지 돌아 실행기의 판정 규칙·단위 검증·경고
수집을 한 번에 시험한다. S3 는 cae00 없이 절반까지, S4 는 S0 을 기다린다.

**S5** — 배치는 첫 `gate: human` 직전까지 돌고 비교표를 만든다. 게이트 이후 단계는 표에서
골라 개별 재개한다(초안 N개 자동 생성 금지). 동시 상한은 "같은 백엔드에 동시 N" 이다.
첫 실사용례가 이미 둘 있다 — **R1 의 굽힘반경 스윕**(R_min·R_max 유불리)과 **R2 의 각도 프리셋
비교**. 조건 분기가 필요해 보이던 자리가 사실 "같은 레시피 × 변수 N개" 였다.

**S6 은 뒤로 뺐다** — 작지 않고(앱마다 시야가 다르다) 예제 넷의 임계 경로에 있지도 않다
(context-notes W-22).

### 심의는 잡을 걸지 않는다 — 이미 있는 결과를 읽는다

**심의 좌석에 주는 낙하·충격 도구는 읽기 전용 판독 도구뿐이다** — `report_summary`·
`report_worst_cases`·`report_directional`·`report_part_risk`·`report_findings`·`report_query`·
`report_case`·`report_angle_stats`·`report_scatter`·`report_energy_flow`·`report_part_series`·
`compare_reports`. 제출 계열(`smarttwin_submit`·`slurm_submit_job`·`run_job`·`submit_lsdyna_job`)은
**좌석 도구에서 뺀다.**

근거 셋.

1. **시간이 안 맞는다.** 드라이버 잡 walltime 이 167시간인데 심의 라운드는 몇 분이다. 심의 중에
   잡을 걸면 그 심의는 결과 없이 끝나고 **의도만 남은 근거**가 된다.
2. **집계가 좌석의 일이 아니다.** 전각도 낙하는 자식 잡을 26~10000개 만들고 그것을 하나로
   모으는 것이 `sphere_report`·`impact_report` 의 일이다. 좌석이 라운드 중간에 그걸 모을 수
   없고, 모으려 들면 부분 결과로 결론을 낸다.
3. **판독 도구가 이미 집계된 슬라이스를 준다.** `report_worst_cases` 는 최악 랭킹을,
   `report_directional` 은 방향 범주별 롤업을, `report_query` 는 서버가 필터한 조각만 준다.
   좌석이 받아야 할 모양 그대로다.

→ **순서가 정해진다.** 워크벤치가 먼저 돌고(R2a 제출 → 잡 → R2b 회수·반입), 심의는 그 뒤에
`report_id` 를 받아 읽는다. 이것이 앞서 말한 "레시피를 도구로 등록해 심의가 부른다" 의 정확한
형태다 — 심의에 주는 것은 **R2b(회수·판독)** 쪽이지 R2a(제출)가 아니다.

`compare_reports`(리비전·조건 간 파트별 최악 응력 비교)와 `report_corpus`(반복되는 findings =
설계 규칙 후보)가 S8 리스크 패턴화의 재료다.

**S8 첫 항목은 런 → 심의 다리다.** 런 상세에 "심의로 넘기기" 를 두고 단계 기록을
`[{source: "<레시피>#<단계>", tool, args, result}]` 로 바꿔 챗 핸드오프와 **같은 통로**
(`POST /agent/chat` + `delib_opts.evidence`, `chair_template: "risk-review"`)로 싣는다. HWAXRisk
가 이미 이 길로 간다. 상한은 그 통로의 것 — 40건, 항목 150,000자·**인자 1,200자**. 결론은
넣지 않는다(헌법 P1). 챗·심의 파일은 0줄이다. **선행 결손 둘** — 웹에서 리스크 심의를 고를 수
없고(`delibTaxonomy.ts` `JobId` 에 `risk-review` 만 빠짐), `ConvKind` 에도 없어 앱이 만든
대화가 웹 목록에서 조용히 걸러진다. 둘 다 워크벤치와 별개의 기존 결손이고 이 다리가 만든
대화를 웹에서 보기 위한 선행이다.

### 6-1. 쓸모를 어떻게 아나

§3 의 "쓸모가 증명되면 떼어낸다" 는 무엇을 세는지 정해 두지 않으면 영영 판정되지 않는다.
지표 표를 따로 두지 않고 런·레시피 표에서 계산한다 — 그래서 `created_by`·`run_by`·`origin` 이
S1 모델에 있다. 읽는 수는 넷 — 저장된 레시피 수 · 재생(`origin=replay`) 런 수 ·
`created_by ≠ run_by` 인 재생 수 · 재생 완주율. `GET /workbench-api/stats`(portal-admin) 한 줄로
낸다.

판정은 S1 완료 4주 뒤 한 번 — 레시피 ≥3 · 타인 재생 ≥5 · 재생 완주율 ≥70% 면 계속하고 §3 의
승격을 검토한다. 못 미치면 접거나 S5 이후를 보류한다. 세 수치는 근거 있는 값이 아니라
**초기값**이며, 판정 시점에 왜 그 값이었는지와 함께 context-notes 에 적는다.

---

## 7. 남은 결정

| # | 결정 | 메모 |
|---|---|---|
| 1 | ~~ODB 를 어디에~~ | **정해짐 — cae00 `odb-hub`** |
| 2 | S0 을 언제 하나 | 이를수록 S4 설계가 빨라진다. S1~S3 은 안 기다려도 된다 |
| 3 | ~~S1 의 첫 레시피를 무엇으로~~ | **정해짐** — 시험용 3단계(§6). 실전 예제는 [recipes.md](recipes.md) 넷 |
| 4 | 일괄 재생 상한 | S5 때, 같은 백엔드 기준 |
| 5 | 쓸모 판정 시점·임계 | §6-1 초기값. S1 완료 시 확정 |
| 6 | 레시피 공유 범위·편집 정책 | v1 은 `feat:workbench` 전원 공개 · 새 판본은 소유자·portal-admin 만, 남의 것은 포크. 팀 단위 가시성은 access.yaml 에 팀이 없어 보류 |
| 7 | 게이트웨이 원장에 호출자를 남길지 | `_call_tool` 감사에 `_request_user()` 를 caller 로 — 한 줄이지만 §4 '순수 프록시' 와 별개 리포 수정. v1 은 런 기록만으로 간다 |
| 8 | S6 을 HWAXRisk `rr_sources` 확장으로 할지 신규로 할지 | §5-3. S5 뒤에 |
| 9 | odb-hub 사용자 위임 편입 | S0 에서 사용자별 스코프로 확인되면 PER_USER_SSO 편입 또는 IDENTITY_FWD 수용 — v1 밖 별도 결정 |

---

## 8. 확인 못 한 것

- **cae00 `odb-hub` 의 도구 목록·스키마·응답 모양·인증 스코프** — S0 로 받는다. 그전까지
  ODB 관련 설계는 전부 가정이다.
- **브라우저 실물** — 이 세션은 로그인 자격이 없어 포털 화면을 한 번도 보지 못했다.
- 로컬 ODB 엔진(`../ODB`)은 **쓰지 않기로 했다**(사용자 결정). 다만 그 리포의 447줄 MCP
  규격서는 odb-hub 어댑터를 설계할 때 **어휘 참고물**로만 쓴다 — 특히 §2.2 *"지오메트리를
  도구 결과로 반환하지 않는다"* 는 어느 구현이든 지켜야 할 규칙이다. 허브가 그 규격서를
  따랐는지는 모른다.
