# 자동 파이프라인 계약 v1.1 — 원천 앱 · 해석 앱이 갖출 도구와 꼴(2026-11-27)

> 계획은 [PLAN.md](PLAN.md). 이 문서가 앱 세션에 보내는 정본이다. 바꾸면 판을 올리고 맨 아래 「판 이력」에 적는다.

포털은 해석을 모른다. 앱이 아래 도구를 갖추면 포털이 그 앱을 자동 파이프라인의 단계로 쓸 수 있다. 도구는 모두 MCP 도구이고 게이트웨이를 거친다.
게이트웨이가 붙이는 접두는 상관없다 — 포털은 게이트웨이 `/tools-map` 의 원래 이름(`orig`)으로 찾는다.

## 0. 공통

### 0.1 subject — 무엇에 대한 일인가

```json
{"project": "<SP 허브 plm_task key>", "revision": "<개발 단계 코드>", "refs": {"<앱 id>": "<그 앱 쪽 id>"}}
```

- **`project` 는 SP 허브 `plm_task` 객체의 key(= 과제명)다.** 과제코드(`properties.task_code`)가 아니다. StepForge 는 `get_project_meta.plm_task.key`
  · `find_plm_task` 로, DynaForge 는 `list_tasks` · `task_revisions` 의 과제명으로 얻는다.
- **`revision` 은 개발 단계 코드다** — 낱말은 DynaForge `dev_rev` 와 같다(`pre` · `dv1` … `dvr` · `pv1` … `pvr` · `pra` · `mp`).
- 둘 다 모르면 짐작하지 않고 **null** 로 싣는다. 포털은 `project` null → `blocked: project_key`, `revision` null → `blocked: revision` 으로 세운다.
- `refs` 는 앱 쪽 id 다(StepForge 과제 id · DynaForge 세션 id 등). 원천 앱이 준 것을 포털이 해석 앱에 그대로 넘긴다.
- StepForge 는 새 CAD 개정이 새 과제 행이다. 같은 개발 단계 안의 새 CAD 개정은 `refs` · 입력 지문이 달라 포털에서 새 실행이 된다(같은 과제의 앞
  실행은 대체된다).

### 0.2 신원

- 포털은 서비스 신원으로 부른다 — 게이트웨이 청중 `mcp-gateway-service`, `sub` `system:auto-pipeline`. 사람 이메일 · 그룹 칸이 없다.
- 게이트웨이는 박스 파일 `service_tools.local.json` 의 `jobs.auto-pipeline.tools`(`"<백엔드 키>:<원래 이름>"`)에 적힌 도구만 서비스 신원에 연다.
  RA · TestScope · 신원 전달 백엔드는 서비스 신원에 늘 막힌다.
- **사람별 위임 앱(DynaForge · ste 등)은 서비스 신원으로 부르면 게이트웨이 서비스 계정 명의로 닿는다**(사람 이메일이 없어서). 그래서 앱은
  - `auto_*` 도구에 한해 그 서비스 계정이 **모든 과제를 읽을 수 있게** 시야를 열고(감지 · 확인 · 결과),
  - 제출은 앱이 정한 서비스 계정으로 낸다(클러스터 제출은 KooSlurm 위임 · 서비스 계정 sbatch — 운영이 계정을 정한다).
- 서비스 신원을 아직 못 받는 앱은 `auto_profiles` 의 `service_identity: false` 로 알린다. 포털은 그 앱 단계를 `blocked` 로 세운다.

### 0.3 답의 꼴

- 모든 답은 JSON 객체다. 실패는 MCP `isError: true` 와 `{"error": "<낱말>", "detail": "<사람 글>"}` 이다. **`isError: false` 로 오류를 싣지 않는다** —
  포털은 `isError` 와 아래 칸으로 성공을 판정한다(포털 절차 PLAN 5-6 — 실패 다섯 모양 중 셋이 `isError=false` 였다).
- 시각은 ISO 8601 UTC(`2026-11-27T01:02:03Z`). 앱 판은 `app_version`(SIF 안 BUILD_INFO 의 커밋 앞 8자리 등).
- **상태 · 판정 낱말은 앱이 바꿔 싣는다.** 예 — DynaForge `succeeded` → `done` · `canceled` → `cancelled`, Slurm `COMPLETED` → `done`, 열충격
  `OK` · `WARNING` · `FAIL` → `pass` · `marginal` · `fail`.

## 1. 원천 앱 — 새 차수를 알린다(StepForge · DynaForge)

### `auto_changes(since: str | null, limit: int = 200)`

마지막으로 본 뒤 바뀐 과제 · 차수를 준다.

```json
{
  "items": [
    {
      "subject": {"project": "…", "revision": "dv1", "refs": {"step_forge": "p-123"}},
      "inputs": [{"kind": "cad_assembly", "ref": "…", "sha256": "…", "at": "2026-11-27T01:02:03Z"}],
      "ready": {"parsed": true},
      "updated_at": "2026-11-27T01:02:03Z"
    }
  ],
  "next_since": "<불투명 커서>",
  "complete": true
}
```

- `since` 가 null 이면 처음부터다. `next_since` 를 다음 호출에 그대로 준다. 커서는 앱이 정하는 불투명 글이다. **쪽을 끝까지 넘길 수 있어야 한다**
  (지금 DynaForge `list_sessions` 처럼 200 에서 잘리면 안 된다).
- `inputs[].sha256` 은 그 입력의 내용 해시다(없으면 앱 쪽 판 id). 포털은 이것으로 입력 지문을 만든다 — 같은 지문이면 다시 돌리지 않는다.
- `ready` 는 원천 쪽 준비 신호다. 규칙의 `trigger.ready_when` 이 `<앱 id>.<키>` 로 본다(예 `step_forge.parsed`). StepForge 의 파싱 끝은 마지막 parse
  잡의 `status` 가 끝난 상태일 때만 참이다.
- `complete: false` 면 아직 더 있다(같은 `next_since` 로 다시 부른다).
- 서비스 신원으로 불러도 모든 과제가 보여야 한다(§0.2).

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
      "inputs": [{"kind": "ecad_board", "required": true}, {"kind": "pkg_type", "required": true, "human": true}],
      "cost": {"cores": 64, "minutes": 240, "cluster": "stcx"},
      "sync": false,
      "criteria_source": "<판정 기준의 출처 — 규격 · 사내 기준 이름>",
      "outputs": ["verdict", "metrics", "figures"]
    }
  ]
}
```

- 해석 조건은 profile 안에 있다. 포털은 profile id 만 고른다.
- `cost` 는 대략치다 — 포털 그림자 모드가 「무엇을 얼마나 냈을지」를 세는 데 쓴다. 잡이 없는 앱은 `sync: true` · `cost` 를 비운다.
- `inputs[].human: true` 는 사람이 줄 값이다(예 열충격의 패키지 종류 · 볼 크기). 앱은 과제마다 그 값을 보관하고, 사람이 넣는 길(화면 · 도구)을
  스스로 갖춘다. 값이 없으면 `auto_check` 가 `missing: [{kind: "human_input", …}]` 로 답한다.

### `auto_check(subject, profile, upstream?)`

```json
{"ready": false, "missing": [{"kind": "human_input", "name": "pkg_type", "why": "이 과제의 패키지 종류를 사람이 정하지 않았다"}],
 "inputs": [{"kind": "cad_assembly", "ref": "…", "sha256": "…"}]}
```

- 제출하지 않는다. 읽기만 한다.
- `missing[].kind` 의 정해진 낱말 — `project_key` · `revision` · `input` · `human_input` · `infra`(클러스터 · 공유 저장소 등 박스 문제) · `permission`.
  `input` 은 `name` 에 앱이 정한 입력 종류를 싣는다.
- `ready: true` 면 `inputs` 가 이번 제출에 쓸 입력이다(포털이 입력 지문에 넣는다). `inputs[].ref` 는 앱 쪽 id 나 클러스터 경로여도 된다.
- **`upstream`(선택)** — 규칙에서 이 단계가 앞 해석 단계를 `needs` 로 가리키면, 포털이 앞 단계의 결과 봉투를 `{"<단계 id>": <결과 봉투>}` 로 넘긴다.
  예 — ODB 추출 단계의 `artifacts` 를 열충격 단계가 입력으로 쓴다. 앱은 쓰지 않으면 무시한다.

### `auto_submit(subject, profile, idem_key, upstream?)`

```json
{"run_ref": "<앱 쪽 실행 id>", "state": "queued", "created": true}
```

- **같은 `idem_key` 로 다시 부르면 새로 내지 않고 같은 `run_ref` 를 `created: false` 로 돌려준다.** 포털이 응답을 잃고 다시 부를 때 두 번 내지 않게
  하는 장치다.
- `idem_key` 는 포털이 (과제, 차수, 규칙 판, 입력 지문, 단계 id)의 sha256 으로 만든다. 64자 소문자 16진수.
- 입력이 안 갖춰졌으면 제출하지 않고 `isError: true` · `error: "not_ready"` 와 `missing` 을 싣는다.
- **잡이 없는 앱(`sync: true`)은 곧바로 `state: "done"` 을 준다.** 포털은 상태를 묻지 않고 바로 `auto_result` 로 간다.

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

- `verdict` 는 `pass` · `fail` · `marginal` · `unknown` 넷이다. **기준이 없으면 `unknown` 이고 지어내지 않는다.** 「전 각도가 끝났다」 같은 완료 판정은
  공학적 합부가 아니다 — 그것만 있으면 `unknown` 이고 완료 여부는 `notes` 에.
- `metrics[].value` 는 숫자다. 단위는 꼭 싣는다.
- `state` 가 `done` 이 아니면 `isError: true` · `error: "not_done"` 이다.
- 빈 결과는 `notes` 에 사유를 싣는다 — 「값이 없다」와 「이 박스에 없다」를 가른다.

### (선택) `auto_cancel(run_ref)`

- v1 의 포털은 아직 내지 않은 단계만 취소하므로 필수가 아니다. 있으면 포털이 사람의 취소 단추에서 부른다.

## 3. 이름과 표지

- 도구 이름은 위 그대로(`auto_changes` · `auto_profiles` · `auto_check` · `auto_submit` · `auto_status` · `auto_result` · `auto_cancel`)로 한다.
- `auto_submit` · `auto_cancel` 은 `readOnlyHint` 를 달지 않는다(`destructiveHint: false`). 나머지는 `readOnlyHint: true`.
- 심의 좌석 자유 조회 접두(에이전트 서버 `_FREE_ALLOW`)에 `auto_` 는 없다(11-27 확인). 좌석이 해석을 내면 안 되므로 앞으로도 넣지 않는다.

## 4. 앱이 시험으로 보일 것

1. `auto_submit` 을 같은 `idem_key` 로 두 번 부르면 실행이 하나다.
2. `auto_check` 는 아무것도 바꾸지 않는다(DB · 큐 · 파일).
3. `isError: false` 응답에 `error` 칸이 없다.
4. `auto_result` 의 `metrics[].unit` 이 비지 않는다.
5. SP key · 개발 단계를 모르는 과제를 지어낸 값으로 싣지 않는다(null).
6. 서비스 신원(게이트웨이 서비스 계정)으로 불러도 `auto_changes` 가 모든 과제를 준다.

## 5. 누가 무엇을 갖추나(11-27 조사 기준)

| 앱 | 갖출 것 | 지금 있는 것 · 빈 곳 |
|---|---|---|
| StepForge | `auto_changes` | `list_projects` 에 갱신 시각 · 개발 단계 칸이 없다(과제 = CAD 개정 하나 · `rev_label` 은 자유 이름). 허브 key 는 `get_project_meta.plm_task.key`. 서비스 신원 읽기 시야는 이미 전체 |
| DynaForge(KooRemapper) | `auto_changes` · **전각도 낙하 해석 다섯** | 세션에 과제 · 개발 단계 칸이 없고 `linked_cad` 만 있다 · `list_sessions` 200 에서 잘림 · 서비스 계정 시야가 좁다 · 캠페인은 만든 사람만. 공학 수치는 stcx 잡 → 후처리 예약 → sphere 리포트 사슬에서 나와 **낙하 계약의 주인은 DynaForge** 다 |
| ThermalShock | 해석 다섯(`sync: true`) | 잡 없는 동기 예측 · 입력 원천은 ODB++(ODB 허브) · 패키지 종류 · 볼 크기는 늘 사람 값 · `project` 는 자유 글(SP key 아님) |
| SmartTwinMCP · KooSlurm | (DynaForge 낙하 사슬의 제출 길) 서비스 계정 제출 | 제출 도구는 `fullangle_drop_simulation` · `catalog_run`(입력은 클러스터 절대 경로) · 신원은 MCP 프로세스의 OS 계정. **공유 폴더 SH-01 · 02 가 풀려야 업로드 입력 잡이 돈다** |
| ODB 허브(cae00 전용) | (열충격 입력) 원천 또는 추출 단계 | 사람이 요청서를 보낸다 — dev 세션 없음 |
| ste 전각도 | 쓰지 않음(v1) | 결과가 완료 판정뿐이라 공학 합부를 못 준다 |

## 판 이력

- v1(2026-11-27) — 처음.
- v1.1(2026-11-27) — 앱 코드 조사 반영: `project` 는 허브 key(과제명) · `revision` 은 개발 단계 코드(DynaForge 낱말) · 둘 다 모르면 null · 사람별 위임 앱의
  서비스 계정 시야 · 상태 · 판정 낱말 바꾸기는 앱 몫 · `human_input` · `revision` 막힘 낱말 · `sync` 앱은 제출이 곧 done · `upstream`(앞 단계 결과 넘기기) ·
  완료 판정은 합부가 아님 · 쪽을 끝까지 · §5 누가 무엇을.
