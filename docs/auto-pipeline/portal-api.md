# 자동 파이프라인 — 포털 안 설계 · 창구(M1 ~ M3 를 미리 짓는 기준, 2026-11-27)

> 계획 [PLAN.md](PLAN.md) · 앱 계약 [contract.md](contract.md). 이 문서는 포털 백엔드 · 화면이 같이 보는 기준이다.

## 1. 자리

- 백엔드 모듈 `backend/app/autopipe/`(절차와 같은 격리 모듈 — 챗 · 심의 파일 0줄). 저장은 절차 저장소 `procedures.sqlite` 의 새 표(루틴과 같은 까닭 —
  설정 · 백업 · 기동에 이미 등록된 파일).
- API 접두 `/autopipe-api`(SPA 경로와 겹치지 않게 — 새로고침이 JSON 을 받는 사고). 화면은 절차 페이지의 새 탭 `/procedures/auto`.
- 스위치 `AUTO_PIPELINE_ENABLED`(기본 꺼짐). 꺼지면 엔진이 돌지 않고, 창구는 읽기 · 규칙 편집 · 검증만 된다(`/health` 가 꺼짐과 켜는 법을 말한다).
- 권한 `feat:auto-pipeline` — **grant_only**(전 과제 · 클러스터에 영향이 커서 「전부」 · 관리자 전권에 딸려 오지 않는다). 편집 · 보기 모두 이 키.
  서비스 신원은 모든 과제를 보므로 현황판도 이 키를 가진 사람만 본다.

## 2. 규칙 스펙(JSON, 저장 때 검증)

```json
{
  "title": "낙하 · 열충격 기본",
  "stage": "shadow",
  "scope": {"all_projects": true, "exclude": ["<과제 key>"]},
  "trigger": {"ready_when": ["step_forge.parsed"], "quiet_s": 1800},
  "steps": [
    {"id": "thermal", "kind": "analysis", "app": "thermal_shock", "profile": "default"},
    {"id": "drop", "kind": "analysis", "app": "kooremapper", "profile": "fullangle-26", "needs": []},
    {"id": "summary", "kind": "report", "report": "summary", "needs": ["thermal", "drop"]},
    {"id": "revdiff", "kind": "report", "report": "revdiff", "needs": ["thermal", "drop"]}
  ],
  "limits": {"max_concurrent": 2, "per_project_per_day": 1, "night_only": ["drop"]}
}
```

- `stage` — `shadow` · `approve` · `auto`(AP-D2).
- `steps[].kind` — `analysis`(계약 앱) · `report`(`per_analysis` · `summary` · `revdiff`). `deliberation` 은 M5 — v1 검증은 「아직 없음」으로 거절한다.
- `app` 은 게이트웨이 백엔드 키(앱 id)다. 도구는 `/tools-map` 의 `orig` 로 (백엔드, 원래 이름 `auto_*`) → 노출 이름을 찾는다.
- analysis 가 다른 analysis 를 `needs` 로 가리킬 수 있다(예 ODB 추출 → 열충격). 그때 포털은 앞 단계 결과 봉투를 `upstream` 으로 넘긴다(계약 v1.1 §2).
- 검증 — id 꼴(`^[a-z0-9][a-z0-9_-]{0,39}$`) · 겹침 · `needs` 가 있는 단계를 가리킴 · 순환 없음 · report 의 needs 는 analysis · `quiet_s` 60 ~ 86400 ·
  한도 양수 · `night_only` 는 analysis 단계 · 단계 수 ≤ 12.
- 판은 불변. 고치면 새 판. 규칙은 켜기/끄기(`enabled`)가 판과 따로 있다.

## 3. 표

| 표 | 칸(요지) |
|---|---|
| `auto_rules` | id · title · enabled · latest_version · created_by · created_at · updated_at · archived |
| `auto_rule_versions` | version_id · rule_id · version_no · spec_json · author · created_at |
| `auto_cursors` | source(앱 id) · cursor · last_ok_at · last_error · last_error_at |
| `auto_subjects` | project · revision · refs_json · inputs_json · fingerprint · ready_json · first_seen · last_change · state(`waiting_quiet` · `ready` · `blocked`) · block_reason |
| `auto_runs` | id · rule_id · version_no · project · revision · fingerprint · stage · state · superseded_by · created_at · updated_at · ended_at · reason |
| `auto_run_steps` | run_id · step_id · kind · state · idem_key · run_ref · check_json · result_json · verdict · report_md · ra_report_id · error · started_at · ended_at · polled_at |
| `auto_events` | id · run_id(없을 수 있음) · at · kind · detail_json — 덧붙이기만 한다(감사) |

- 실행의 유일 열쇠 — (rule_id, version_no, project, revision, fingerprint). 같으면 새로 만들지 않는다.
- 실행 상태 — `planned`(그림자 — 계획만) · `awaiting_approval` · `running` · `done` · `partial` · `failed` · `superseded` · `cancelled`.
- 단계 상태 — `pending` · `ready`(입력 갖춤) · `blocked` · `queued` · `running` · `done` · `failed` · `cancelled` · `skipped`.

## 4. 엔진 한 박자(`tick`, 기본 60초)

1. **감지** — 원천 앱마다 `auto_changes(since=커서)`. 받은 항목으로 `auto_subjects` 를 넣거나 고친다(지문이 바뀌면 `last_change` 갱신). 커서는 끝까지
   받았을 때만 나아간다. 실패는 `auto_cursors.last_error` 에 남기고 다음 원천으로.
2. **판정** — `last_change + quiet_s` 가 지났고 `ready_when` 이 다 서면 `ready`. `project` 가 null 이면 `blocked: project_key`, `revision` 이 null 이면 `blocked: revision`.
3. **실행 만들기** — 켜진 규칙마다 범위(전 과제 − 제외)에 드는 `ready` 주제에 실행을 만든다(유일 열쇠로 멱등).
   - 같은 규칙 · 같은 과제의 앞 차수 실행이 끝나지 않았으면 AP-D5 — 앞 실행의 `queued` · `running` 단계는 그대로, `pending` · `ready` 단계는
     `cancelled`, 실행은 `superseded`(superseded_by = 새 실행).
4. **단계 나아가기** — 실행마다 의존이 끝난 단계를.
   - analysis · `pending` → `auto_check`(앞 analysis 가 있으면 그 결과 봉투를 `upstream` 으로). 준비 안 됨이면 `blocked`(missing 을 그대로 남김 — 낱말
     `project_key` · `revision` · `input` · `human_input` · `infra` · `permission`, 모르는 낱말도 그대로). 앞 analysis 가 failed · skipped 면 `skipped`(upstream_failed).
   - `shadow` 실행은 check 까지 하고 실행을 `planned` 로 둔다(제출 없음 · 「냈을 것」 기록 — profile 의 cost 를 함께).
   - `approve` 실행은 모든 analysis 가 check 를 지나면 `awaiting_approval`. 사람이 승인하면 `auto` 처럼 나아간다.
   - `auto` · 승인된 실행 — 한도 안에서 `auto_submit(idem_key)` → `queued`. 응답을 잃으면 다음 박자에 같은 idem_key 로 다시 부른다. 제출 답이 곧바로
     `done` 이면(동기 앱) 상태를 묻지 않고 `auto_result` 로 간다.
   - `queued` · `running` → `auto_status`(단계마다 `polled_at` 으로 너무 자주 묻지 않게, 기본 120초). `done` 이면 `auto_result` 를 받아 봉투 검증 →
     `done` · verdict. 봉투가 꼴에 안 맞으면 `failed`(까닭: envelope_invalid) — 성공처럼 보이는 실패를 막는다.
   - report — needs 가 모두 끝(done · failed · skipped)이면 보고서를 쓴다(§5). needs 가운데 done 이 하나도 없으면 `skipped`.
5. **실행 끝** — 모든 단계가 끝나면 `done`(실패 없음) · `partial`(일부 실패 · 건너뜀) · `failed`(analysis 가 다 실패).

- 재기동을 넘는다 — 상태가 원장에 있어 다음 박자가 이어 간다. 박자는 한 번에 하나만 돈다(같은 프로세스 잠금 + 원장의 잠금 행).
- 한도 — 박스 전체 동시 제출(`AUTO_PIPELINE_MAX_CONCURRENT`, 기본 2) · 규칙 `limits` · 야간 창(`AUTO_PIPELINE_NIGHT`, 기본 `20-07` KST).

## 5. 보고서 · RA

- 보고서는 결과 봉투에서 **코드가 쓴다**(서술 LLM 은 M5 — v1 은 정해진 문장). 머리에 「자동 — 규칙 <title> v<판> · 입력 지문 · 앱 판」, 대체된 실행이면
  「대체됨 — 차수 <새 차수> 가 뒤에 왔다」.
  - `per_analysis` — 판정 · 수치 표(이름 · 값 · 단위 · 기준 · 판정) · 그림 · 원자료 위치 · notes.
  - `summary` — 해석마다 한 줄 판정 + 수치 표 묶음 + 실패 · 건너뜀(숨기지 않는다).
  - `revdiff` — 같은 규칙 · 같은 과제의 바로 앞 차수 `done` 실행과 metrics 를 이름으로 맞대 값 · 판정 변화. 앞 차수가 없으면 「첫 차수」.
- **RA 게시(AP-D3)** — 박스 파일 `infra/ra-formats.local.json` 의 `auto_pipeline` 줄이 있을 때만:
  ```json
  {"auto_pipeline": {"board": "sys-<시스템>", "token_file": "infra/secrets/ra-auto-pipeline.token",
                     "formats": {"summary": {"template_id": "…", "template_version": 1}}}}
  ```
  - 시스템 계정 토큰은 0600 파일(경로는 리포 루트 기준 상대 — 박스마다 경로가 다르다). 포털 프로세스만 읽고 로그 · 응답에 찍지 않는다.
  - 길 — RA `POST /api/reports/ai-draft`(그 형식의 블록 꼴 — 포털 `_ra_blocks` 와 같은 나눔) → `POST /api/mounts`(게시판 = 박스 파일의 board).
    시스템 계정은 관리자가 그 게시판을 미리 연결해 둔 것이 사전 승인이라 확인 토큰 없이 게시된다(RA 문서 §6.4). 게이트웨이를 거치지 않는다.
  - 줄이 없으면 보고서는 포털 원장에만 있고 현황판에서 읽는다(꺼진 것이 아니라 「RA 미설정」으로 보인다).

## 6. 창구(`/autopipe-api`, 모두 `feat:auto-pipeline`)

| 창구 | 하는 일 |
|---|---|
| `GET /health` | `{enabled, how_to_enable, engine: {running, last_tick, last_error}, sources: [{app, cursor_at, last_error}], ra: {configured, board}, counts}` |
| `GET /rules` · `POST /rules`(CSRF) · `GET /rules/{id}` · `POST /rules/{id}/versions`(CSRF) | 규칙 목록 · 만들기 · 읽기 · 새 판 |
| `POST /rules/{id}/enabled`(CSRF) `{enabled}` | 켜기 · 끄기 |
| `POST /validate` `{spec}` | `{ok, errors[], warnings[]}` — 저장하지 않는다 |
| `GET /subjects?project=&state=&limit=` | 감지한 과제 · 차수 |
| `GET /board?rule=&limit=` | 현황판 — 행 `{project, revision, run_id, run_state, superseded_by, steps: {<step_id>: {state, verdict}}}` · 열 = 규칙 단계 |
| `GET /runs?rule=&project=&state=&limit=` · `GET /runs/{id}` | 실행 목록 · 상세(단계 · check · 결과 봉투 · 이벤트) |
| `POST /runs/{id}/approve`(CSRF) | `awaiting_approval` → 나아감(승인한 사람을 이벤트에) |
| `POST /runs/{id}/cancel`(CSRF) | 안 낸 단계 취소(도는 단계는 앱에 `auto_cancel` 이 있으면 부르고, 없으면 끝까지 둔다고 알린다) |
| `GET /runs/{id}/report?step=` | 그 report 단계의 마크다운 |
| `POST /tick`(CSRF) | 한 박자 바로(관리 · 시험용 — 꺼져 있으면 409) |

## 7. 신원

- 해석 · 원천 앱 호출은 포털이 **호출마다 찍는 짧은 서비스 토큰**으로 한다(절차 PAT 와 같은 체계 — 수명 15분 · 실행 · 단계에 묶인 jti).
  클레임은 core-link 의 서비스 PAT 꼴(청중 `mcp-gateway-service` · `sub` `system:auto-pipeline` · `scopes` `["service"]` · `purpose` `service`)이고, 포털
  `auth/service_pat.py` 의 `service_claims` 로 만든다. **jti 는 `svc-` 로 시작해야 게이트웨이가 받는다** — `svc-ap-<run>-<step>`.
- 길게 사는 서비스 PAT 를 저장하지 않는다 — 만료 관리 · 유출 표면이 없다. 무엇을 부를 수 있는지는 게이트웨이 박스 파일 `service_tools.local.json` 이
  정한다(포털이 정하지 않는다).
- 이 결정은 PLAN §4.6 의 「1 ~ 365일 서비스 PAT · 만료 표시」를 바꾼다(context-notes AP-8).
