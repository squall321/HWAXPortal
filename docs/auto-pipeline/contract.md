# 자동 파이프라인 계약 v1 — 원천 앱 · 해석 앱이 갖출 도구와 꼴(2026-11-27)

> 계획은 [PLAN.md](PLAN.md). 이 문서가 앱 세션에 보내는 정본이다. 바꾸면 판을 올리고 맨 아래 「판 이력」에 적는다.

포털은 해석을 모른다. 앱이 아래 도구를 갖추면 포털이 그 앱을 자동 파이프라인의 단계로 쓸 수 있다. 도구는 모두 MCP 도구이고 게이트웨이를 거친다.
게이트웨이가 붙이는 접두는 상관없다 — 포털은 게이트웨이 `/tools-map` 의 원래 이름(`orig`)으로 찾는다.

## 0. 공통

### 0.1 subject — 무엇에 대한 일인가

```json
{"project": "<SP plm_task key>", "revision": "<차수 코드>", "refs": {"<앱 id>": "<그 앱 쪽 id>"}}
```

- `project` · `revision` 은 **필수**다. 과제 열쇠는 SP 과제 key, 차수는 개발 단계 코드다(포털 docs/project-insight-graph 와 같은 열쇠).
- 앱이 SP key 를 모르면 짐작하지 않는다. 그 과제는 `auto_changes` 에 싣지 않거나, `auto_check` 에서 `missing: [{kind: "project_key"}]` 로 답한다.
- `refs` 는 앱 쪽 id(StepForge 과제 id · DynaForge 세션 id 등)다. 원천 앱이 준 것을 포털이 해석 앱에 그대로 넘긴다.

### 0.2 신원

- 포털은 서비스 신원으로 부른다 — 게이트웨이 청중 `mcp-gateway-service`, `sub` `system:auto-pipeline`. 사람 이메일 · 그룹 칸이 없다.
- 게이트웨이는 박스 파일 `service_tools.local.json` 에 적힌 도구만 서비스 신원에 연다. 앱은 서비스 신원이 들어오면 **모든 과제를 읽기 시야로** 보되,
  쓰기(제출)는 이 계약의 `auto_submit` 하나로만 받기를 권한다.
- 서비스 신원을 받지 못하는 앱은 「아직 못 받음」을 `auto_profiles` 의 `service_identity: false` 로 알린다. 포털은 그 앱 단계를 `blocked` 로 세운다.

### 0.3 답의 꼴

- 모든 답은 JSON 객체다. 실패는 MCP `isError: true` 와 `{"error": "<낱말>", "detail": "<사람 글>"}` 이다. **`isError: false` 로 오류를 싣지 않는다** —
  포털은 `isError` 와 아래 칸으로 성공을 판정한다(포털 절차 PLAN 5-6 — 실패 다섯 모양 중 셋이 `isError=false` 였다).
- 시각은 ISO 8601 UTC(`2026-11-27T01:02:03Z`).
- 앱 판은 `app_version`(SIF 안 BUILD_INFO 의 커밋 앞 8자리 등)으로 싣는다.

## 1. 원천 앱 — 새 차수를 알린다(StepForge · DynaForge)

### `auto_changes(since: str | null, limit: int = 200)`

마지막으로 본 뒤 바뀐 과제 · 차수를 준다.

```json
{
  "items": [
    {
      "subject": {"project": "…", "revision": "…", "refs": {"step_forge": "p-123"}},
      "inputs": [{"kind": "cad_assembly", "ref": "…", "sha256": "…", "at": "2026-11-27T01:02:03Z"}],
      "ready": {"parsed": true},
      "updated_at": "2026-11-27T01:02:03Z"
    }
  ],
  "next_since": "<불투명 커서>",
  "complete": true
}
```

- `since` 가 null 이면 처음부터다. `next_since` 를 다음 호출에 그대로 준다. 커서는 앱이 정하는 불투명 글이다.
- `inputs[].sha256` 은 그 입력의 내용 해시다(없으면 앱 쪽 판 id). 포털은 이것으로 입력 지문을 만든다 — 같은 지문이면 다시 돌리지 않는다.
- `ready` 는 원천 쪽 준비 신호다. 규칙의 `trigger.ready_when` 이 이 키를 본다(예 `step_forge.parsed` · `kooremapper.model_registered`).
- `complete: false` 면 아직 더 있다(같은 `next_since` 로 다시 부른다).
- SP key 를 모르는 과제는 싣지 않거나 `subject.project` 를 null 로 싣는다(포털은 null 을 `blocked: project_key` 로 센다 — 짐작하지 않는다).

## 2. 해석 앱 — 해석을 낸다(열충격 · 전각도 낙하 · …)

### `auto_profiles()`

```json
{
  "app_version": "…",
  "service_identity": true,
  "profiles": [
    {
      "id": "default",
      "title": "열충격 기본 조건",
      "inputs": [{"kind": "ecad_board", "required": true}, {"kind": "cad_assembly", "required": false}],
      "cost": {"cores": 64, "minutes": 240, "cluster": "stcx"},
      "criteria_source": "<판정 기준의 출처 — 규격 · 사내 기준 이름>",
      "outputs": ["verdict", "metrics", "figures"]
    }
  ]
}
```

- 해석 조건은 profile 안에 있다. 포털은 profile id 만 고른다.
- `cost` 는 대략치다 — 포털 그림자 모드가 「무엇을 얼마나 냈을지」를 세는 데 쓴다.

### `auto_check(subject, profile)`

```json
{"ready": false, "missing": [{"kind": "ecad_board", "why": "이 차수에 보드 파일이 없다"}],
 "inputs": [{"kind": "cad_assembly", "ref": "…", "sha256": "…"}]}
```

- 제출하지 않는다. 읽기만 한다.
- `missing[].kind` 의 정해진 낱말 — `project_key` · `input`(+ 앱이 정한 입력 종류) · `infra`(클러스터 · 공유 저장소 등 박스 문제) · `permission`.
- `ready: true` 면 `inputs` 가 이번 제출에 쓸 입력이다(포털이 입력 지문에 넣는다).

### `auto_submit(subject, profile, idem_key)`

```json
{"run_ref": "<앱 쪽 실행 id>", "state": "queued", "created": true}
```

- **같은 `idem_key` 로 다시 부르면 새로 내지 않고 같은 `run_ref` 를 `created: false` 로 돌려준다.** 포털이 응답을 잃고 다시 부를 때 두 번 내지 않게
  하는 장치다.
- `idem_key` 는 포털이 (과제, 차수, 규칙 판, 입력 지문, 단계 id)의 sha256 으로 만든다. 64자 소문자 16진수.
- 입력이 안 갖춰졌으면 제출하지 않고 `isError: true` · `error: "not_ready"` 와 `missing` 을 싣는다.

### `auto_status(run_ref)`

```json
{"state": "running", "progress": 0.42, "detail": "26방향 중 11 끝", "updated_at": "…"}
```

- `state` 는 다섯 낱말뿐이다 — `queued` · `running` · `done` · `failed` · `cancelled`.
- `failed` 면 `detail` 에 사람이 읽을 까닭을 싣는다.

### `auto_result(run_ref)` — 결과 봉투

```json
{
  "run_ref": "…",
  "subject": {"project": "…", "revision": "…", "refs": {}},
  "profile": "default",
  "app_version": "…",
  "verdict": "pass",
  "metrics": [
    {"name": "solder_sed_max", "label": "솔더 SED 최대", "unit": "MJ/m3", "value": 0.82,
     "limit": 1.0, "limit_source": "<기준 출처>", "verdict": "pass"}
  ],
  "figures": [{"ref": "<게이트웨이 그림 보관 ref 또는 앱 주소>", "caption": "…"}],
  "artifacts": [{"kind": "d3plot", "location": "<원자료 위치>"}],
  "inputs": [{"kind": "…", "ref": "…", "sha256": "…"}],
  "notes": ["…"],
  "finished_at": "…"
}
```

- `verdict` 는 `pass` · `fail` · `marginal` · `unknown` 넷이다. 기준이 없으면 `unknown` 이고 지어내지 않는다.
- `metrics[].value` 는 숫자다. 단위는 꼭 싣는다.
- `state` 가 `done` 이 아니면 `isError: true` · `error: "not_done"` 이다.
- 빈 결과는 `notes` 에 사유를 싣는다 — 「값이 없다」와 「이 박스에 없다」를 가른다.

### (선택) `auto_cancel(run_ref)`

- v1 의 포털은 아직 내지 않은 단계만 취소하므로 필수가 아니다. 있으면 포털이 사람의 취소 단추에서 부른다.

## 3. 이름과 표지

- 도구 이름은 위 그대로(`auto_changes` · `auto_profiles` · `auto_check` · `auto_submit` · `auto_status` · `auto_result` · `auto_cancel`)로 한다.
- `auto_submit` · `auto_cancel` 은 `destructiveHint: false` · `readOnlyHint: false` 표지를 단다. 나머지는 `readOnlyHint: true`.
- 심의 좌석 자유 조회는 이 이름들을 열지 않는다(좌석이 해석을 내면 안 된다). 포털 · 에이전트 서버가 `auto_` 를 좌석 접두에 넣지 않는다.

## 4. 앱이 시험으로 보일 것

1. `auto_submit` 을 같은 `idem_key` 로 두 번 부르면 실행이 하나다.
2. `auto_check` 는 아무것도 바꾸지 않는다(DB · 큐 · 파일).
3. `isError: false` 응답에 `error` 칸이 없다.
4. `auto_result` 의 `metrics[].unit` 이 비지 않는다.
5. SP key 를 모르는 과제를 `auto_changes` 에 지어낸 key 로 싣지 않는다.

## 판 이력

- v1(2026-11-27) — 처음.
