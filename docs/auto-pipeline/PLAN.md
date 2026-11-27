# 자동 파이프라인 — 과제·차수에 새 입력이 오면 정해 둔 해석 · 보고서를 저절로(계획, 2026-11-27)

> 체크리스트는 [checklist.md](checklist.md), 결정 기록은 [context-notes.md](context-notes.md).

## 1. 요청(사용자 11-26 · 11-27)

- 정해진 프로세스를 특정 과제 · 특정 차수에 대해 자동으로 진행하는 항목이 있으면 좋겠다.
- CAD(StepForge) · DynaForge 에 파일이 올라가면 자동으로 처리한다. 예를 들면 업데이트가 되면 열충격 해석과 전각도 낙하 해석을 하고, 그 파생 보고서도
  모두 자동으로 만든다.
- 어떤 시뮬레이션을 할지는 포털이 모른다. 포털에서 해석을 셋업하는 것이 아니다. 세팅을 해 두면 모든 과제에 그 프로세스가 적용된다.
- 연결된 MCP 와 보고서 도출까지 규격화해 두고, 그것을 부르면 프로세스가 적용된다.

## 2. 사용자 결정(11-27 — 다섯 다 권장안)

| # | 무엇 | 결정 |
|---|---|---|
| AP-D1 | 누구 이름으로 도나 | **서비스 신원** — 포털 서비스 PAT `system:auto-pipeline`(core-link 11-09). 결과에는 규칙을 켠 사람 · 과제 담당을 함께 적는다 |
| AP-D2 | 해석 제출을 어디까지 자동으로 | **단계적** — 그림자(계획만 기록) → 사람이 한 번 눌러 제출 → 완전 자동. 규칙마다 지금 단계를 고른다 |
| AP-D3 | 보고서 게시 | **자동 보고서 전용 게시판에 확인 없이** — RA 시스템 계정 · 시스템 양식(수신 게시판). 11-21 게시 관문은 이 길에만 푼다. 사람 심의 보고서는 그대로 확인 뒤 게시 |
| AP-D4 | 적용 범위 | **모든 과제 + 제외 목록** |
| AP-D5 | 새 차수가 오면 앞 차수 실행 | **도는 것만 끝까지** — 클러스터에서 도는 해석은 끝까지, 아직 내지 않은 단계는 취소. 끝난 결과는 「대체됨」 표지로 보고서에 남는다 |

## 3. 지금 있는 것 — 새로 짓지 않고 쓴다

| 부품 | 어디 | 이 일에서 맡는 몫 |
|---|---|---|
| 절차(결정적 재생) | `backend/app/procedures/` — `runner.py` · `store.py` · `dispatch.py` | 고정 도구 · 고정 인자 재생, 단계 성공을 코드가 판정(PLAN 5-6), 사람 자리(`run_gate_acks`) — AP-D2 의 「한 번 눌러 제출」 |
| 분석 루틴 | `procedures/routines.py` · `routine_store.py` · 에이전트 `routine.py` | 단계 봉투 · 원장 · 보고서 렌더 · RA 블록 나눔(AR-D7) · 심의 단계 |
| 서비스 신원 | core-link — 포털 `POST /auth/pat/service` · 게이트웨이 `service_tools.local.json` | AP-D1. 게이트웨이는 신원을 넘기는 백엔드(RA · TestScope)를 서비스 신원에 막는다 |
| 박스 훅 | `infra/hooks/post-update.d/*.local.sh` | (선택) 박스별 감지기 설정 |
| 과제 열쇠 | project-insight-graph — (과제 = SP `plm_task` key, 차수 = 개발 단계 코드) | 실행의 주제 열쇠. 이 키가 앱마다 다르면 A → Z 가 끊긴다(절차 PLAN 5-3 · `docs/procedures/app-project-keys.md`) |
| 그림 보관 | 게이트웨이 `GATEWAY_FIG_STORE` · `figure_get` | 결과 봉투의 그림 참조 |
| RA 시스템 연계 3종 | RA v0.180 — 문서 `docs/[참고] 시스템이_올리는_보고서_형식등록.md` §6 | 시스템 양식 `sys.<시스템>.<종류>`(수신 게시판 `format.destination.boards` · `/from-format`) · 시스템 계정 `svc.<시스템>@system.invalid`(`rat_` 토큰, 만료 없음 가능) · 시스템 공간 `sys-<시스템>`(조직 grant — **`edit` 이어야 게시**) · 시스템 공간 대시보드(양식별 수신 · 연계 건강도) |
| RA 형식 등록 | `infra/scripts/ra-register-format.py`(11-21 · 11-26) | 보고서 종류마다 시스템 양식 등록 |
| StepForge 웹훅 장치 | StepForge `app/webhooks.py`(D-706) | 지금은 잡 끝 · 실패 알림뿐. 「과제 등록 · 파싱 끝」 알림으로 넓히기 좋은 자리(허용 주소 · HMAC 서명 · 재전송 · 누락 0) |
| SP 코어 변경 목록 | KooRemapper `runner/sp_core.py` 가 `since` · `next` 꼴로 받는다 | 두 앱이 차수를 허브 객체로 올리면 하나의 감지 원천 |
| 해석 앱 | 게이트웨이 `heax-thermal_shock_mcp`(12) · `heax-kooremapper_mcp`(DynaForge 120 — 후처리 예약 · 캠페인 반입) · ste 전각도(`docs/ste-fullangle`) · SmartTwinMCP(stcx) | 계약(§4.3)을 받을 곳 |

## 4. 설계

```
StepForge · DynaForge 새 차수 ─▶ ① 감지 ─▶ ② 규칙 고르기(모든 과제 − 제외 목록)
                                              │ 단계 연결도
                       ┌──────────────────────┴──────────────────────┐
                       ▼                                             ▼
               ③ 열충격(계약)                                  ③ 전각도 낙하(계약)
                       └──────────────────────┬──────────────────────┘
                                              ▼
                     ④ 원장 — (과제, 차수, 규칙 판, 입력 지문) 한 실행
                                              ▼
                ⑤ 보고서 — 해석별 · 종합 · 이전 차수 대비 → RA 시스템 공간(자동)
```

### 4.1 감지 — 새 차수를 알아챈다

- **v1 은 포털이 묻는다.** 감지기가 몇 분마다(기본 5분) StepForge 과제 목록 · DynaForge 세션을 읽고, 앱마다 커서(마지막으로 본 시각 · 지문)를
  원장에 둔다. 앱을 고치지 않아도 된다.
- **조용해진 뒤 판정한다.** 업로드는 몰려 온다. 같은 과제 · 차수에 새 입력이 `quiet_s`(기본 1800초) 동안 없을 때 한 번 판정한다.
- **준비 판정은 규칙이 정하고, 입력이 갖춰졌는지는 앱이 말한다.** 규칙은 「무엇이 서야 시작하나」(예 — CAD 파싱 끝 + DynaForge 모델 등록)를 적고,
  해석마다 `auto_check` 가 빠진 입력을 돌려준다(§4.3).
- **입력 지문.** 그 차수의 입력(앱이 준 파일 sha · 판 id)을 정렬해 해시한다. 지문이 같으면 다시 돌리지 않는다.
- **나중에는 앱이 알린다.** StepForge 웹훅을 과제 이벤트로 넓히거나, SP 코어 허브 변경 목록 하나를 본다. 묻기는 그대로 두되 주기를 늘린다(알림이
  빠져도 묻기가 잡는다).

### 4.2 규칙(레시피) — 한 번 정하면 모든 과제에

```yaml
id: drop-thermal-default        # 규칙 id
version: 3                      # 불변 판 — 실행은 판을 적는다
stage: shadow | approve | auto  # AP-D2 — 지금 단계
scope:
  all_projects: true            # AP-D4
  exclude: [<과제 key>, …]      # 제외 목록
trigger:
  ready_when: [stepforge.parsed, dynaforge.model_registered]
  quiet_s: 1800
steps:                          # 단계 연결도(DAG)
  - id: thermal
    app: thermal_shock          # 계약을 갖춘 앱
    profile: default            # 앱이 auto_profiles 로 내보인 이름
  - id: drop
    app: fullangle_drop
    profile: 26dir
  - id: report_summary
    kind: report                # 결과 봉투로 코드가 쓰는 보고서
    needs: [thermal, drop]
  - id: report_revdiff
    kind: report_revdiff        # 이전 차수 대비
    needs: [thermal, drop]
  - id: escalate                # (선택) 판정이 기준을 넘으면 심의 · 리스크 심사
    kind: deliberation
    when: any_fail
reports: [thermal, drop, summary, revdiff]
limits: {max_concurrent: 2, night_only: [drop], per_project_per_day: 1}
```

- **단계는 정해진 도구 · 정해진 인자로 돈다.** 인자에는 `${subject.project}` · `${subject.revision}` · 감지가 준 앱 쪽 id 만 들어간다. LLM 이
  도구를 고르지 않는다 — 자동은 매번 같은 결과여야 한다(분석 루틴 AR-D1 과 같은 까닭으로 절차 쪽 보증을 쓴다).
- LLM 은 보고서 서술(근거 id 를 인용해야 한다 — AR-D7)과 선택적인 심의 단계에만 쓴다.
- 규칙은 절차 저장소(`procedures.sqlite`)의 새 표에 둔다. 판은 불변, YAML 내보내기는 절차 · 루틴과 같은 꼴이다.

### 4.3 해석 앱 계약 — 포털은 해석을 모르고 계약만 부른다

해석 앱마다 아래 다섯 도구를 같은 이름 꼴 · 같은 응답 꼴로 갖춘다. 해석 셋업 지식은 앱의 profile 안에 있다.

| 도구 | 입력 | 답 |
|---|---|---|
| `auto_profiles` | — | 자동으로 할 수 있는 해석 목록. profile 마다 이름 · 설명 · 필요한 입력 종류 · 대략의 자원(코어 · 시간) · 판정 기준의 출처 |
| `auto_check` | subject, profile | `{ready: bool, missing: [{kind, why}], inputs: [{kind, ref, sha}]}` — 입력 지문의 재료가 된다 |
| `auto_submit` | subject, profile, `idem_key` | `{run_ref, state}` — 같은 `idem_key` 로 다시 부르면 새로 내지 않고 같은 실행을 돌려준다 |
| `auto_status` | run_ref | `{state, progress?, detail?}` — 상태 낱말은 `queued` · `running` · `done` · `failed` · `cancelled` 다섯만 |
| `auto_result` | run_ref | **결과 봉투**(아래) |

- **subject 는 `{project: <SP plm_task key>, revision: <차수 코드>, refs: {<앱>: <앱 쪽 id>}}`** 다. SP key 가 없는 앱은 받지 않는다(A13 —
  ThermalShock 은 아직 SP key 를 안 받는다). 과제 key 는 짐작하지 않는다(project-insight-graph A13 과 같은 규칙).
- **결과 봉투** — `verdict`(`pass` · `fail` · `marginal` · `unknown`) · `metrics[]`(이름 · 단위 · 값 · 기준 · 기준 출처) · `figures[]`(게이트웨이 그림
  ref) · `artifacts[]`(원자료 위치) · `app_version` · `profile` · `inputs`(auto_check 의 inputs 그대로) · `notes`. 빈 결과는 사유를 싣는다(「없다」와
  「이 박스에 없다」를 가른다 — AR-D2).
- **취소** — AP-D5 때문에 `auto_cancel(run_ref)` 가 있으면 좋지만, v1 은 아직 내지 않은 단계만 포털이 취소하므로 필수가 아니다.
- **이름** — 게이트웨이 로컬 도구가 아니라 앱 도구라 접두가 붙는다. 그래도 심의 좌석 자유 조회 접두(`_FREE_ALLOW`)와 겹치지 않는지 계약을 굳힐 때
  본다(D-18 의 교훈).
- 선례 — 리스크 앱이 ODB 허브에 「계약 4도구」를 청한 것(`docs/design-risk-review/ecad-1031/`)과 같은 방식이다.

### 4.4 실행 원장

- 표 — `auto_rules` · `auto_rule_versions` · `auto_cursors`(감지 커서) · `auto_subjects`(본 과제 · 차수와 지문) · `auto_runs` · `auto_run_steps`.
  모두 절차 저장소에 둔다(설정 · 백업 · 기동에 이미 등록된 파일 — 루틴과 같은 까닭).
- **한 실행 = (과제, 차수, 규칙 판, 입력 지문).** 같으면 다시 만들지 않는다. 앱에 내는 `idem_key` 는 이 넷의 해시다.
- 상태 — 실행은 `planned`(그림자) · `awaiting_approval` · `running` · `done` · `partial` · `failed` · `superseded`. 단계는 계약 상태 다섯 + `skipped` ·
  `blocked`(입력 없음 · 권한 없음 · 이 박스에 없음).
- **AP-D5 — 새 차수가 오면** 앞 차수 실행의 `running` 단계는 끝까지 두고, 아직 내지 않은 단계는 `cancelled`, 실행은 `superseded`. 끝난 단계의 보고서는
  「대체됨 — 차수 N 이 뒤에 왔다」 표지를 달고 남긴다.
- **AP-D2 — 단계(stage)**
  - `shadow` — 감지 · 판정 · `auto_check` 까지만 하고 「이 차수면 이것을 냈을 것」을 원장에 적는다. 제출하지 않는다.
  - `approve` — 실행이 `awaiting_approval` 로 서고 사람이 현황판에서 한 번 누르면 낸다(절차의 사람 자리 `run_gate_acks` 를 쓴다).
  - `auto` — 준비되면 낸다.
- **재기동을 넘는다.** 상태가 원장에 있고 신원이 서비스 PAT 라, 포털이 다시 떠도 `running` 단계의 `auto_status` 를 다시 묻고 이어 간다(분석 루틴은
  사람 PAT 를 잃어 멈추지만 이것은 아니다).
- **보호 장치** — 규칙의 `limits`(동시 수 · 야간 창 · 과제당 하루 상한) · 박스 전체 상한 · 끄기 스위치 하나(`AUTO_PIPELINE_ENABLED`, 기본 꺼짐).
  update-all 은 도는 실행이 있으면 심의처럼 기다린다(해석 잡은 앱 쪽에서 계속 돌므로 기다림은 포털 단계만).

### 4.5 보고서

- 종류 — 해석별(열충격 · 전각도 낙하) · 종합 · **이전 차수 대비**(같은 과제의 바로 앞 `done` 실행과 metrics 를 맞대 바뀐 값 · 판정 변화) · 근거 부록
  (원장의 호출 · 결과 id · 앱 판 · 입력 지문).
- **코드가 결과 봉투로 쓴다.** 수치 · 판정 · 그림은 봉투 그대로, 서술만 LLM(근거 id 인용 필수 · 출처 없는 수치 표지 — AR-D7).
- **AP-D3 — RA 시스템 계정이 시스템 양식으로 올린다.**
  - 보고서 종류마다 시스템 양식 `sys.<시스템>.<종류>` 를 등록하고 수신 게시판을 자동 보고서 전용 시스템 공간으로 둔다.
  - 포털이 박스 비밀 파일의 시스템 계정 토큰으로 RA 를 직접 부른다. 게이트웨이의 `create_report_from_format` 막기(11-21 L21-4 B1)는 사람 · Claude
    길이라 그대로 둔다 — 이 길은 게이트웨이를 거치지 않는다.
  - 시스템 이름은 심의 공간(`sys-hwax`)과 따로 둔다(권고). 그래야 RA 시스템 공간 대시보드의 「양식별 수신 · 연계 건강도」가 자동 보고서만 센다.
  - RA 쪽 문서의 함정 둘을 운영 절차에 적는다 — 서비스 계정도 개인 워크스페이스가 있어야 한다(없으면 첫 보고서에서 FK 위반) · 조직 grant 는 `edit`
    이어야 게시된다.
- **과제 보기** — project-insight-graph 의 (과제, 차수) 보기에 실행 · 보고서를 붙인다(M2 인사이트 원장이 서면).

### 4.6 신원 — AP-D1

- 해석 앱 호출은 서비스 PAT `system:auto-pipeline`(청중 `mcp-gateway-service`)로 게이트웨이를 거친다. 게이트웨이 서비스 허용 목록에 계약 도구만 연다.
- 앱이 서비스 신원의 제출을 받는지는 앱마다 다르다. 클러스터 제출은 서비스 계정 sbatch(KooSlurm SM-01 계열)와 이어진다 — 앱 세션 · 운영 확인이 필요하다.
- 결과 · 보고서에는 「자동 — 규칙 <id> v<판>, 켠 사람 <이름>, 과제 담당 <이름>」을 적는다. 사람 이름은 서명이 아니라 연락처다.
- 서비스 PAT 수명은 1 ~ 365일이다. 만료 30일 전부터 현황판 · 알림으로 보인다(조용히 죽지 않게 — 무음 결함 교훈).

### 4.7 화면

- 절차 탭에 **「자동 파이프라인」** — 규칙 목록 · 편집(범위 · 트리거 · 단계 · 보고서 · 한도 · 단계 stage) · 켜기/끄기 · 판 이력.
- **과제 · 차수 현황판** — 행은 과제 · 차수, 열은 규칙의 단계. 칸은 상태와 판정(합 · 부 · 경계 · 모름), 누르면 단계 결과 · 보고서. `approve` 단계는
  여기서 「제출」 한 번.
- 실행 상세 — 단계별 호출 · 결과 봉투 · 입력 지문 · 대체 사슬.
- 권한 — 규칙 편집은 새 `feat:auto-pipeline`(관리자 그룹), 현황판 보기는 과제 시야 규칙을 따른다.

## 5. 누가 무엇을

| 곳 | 몫 |
|---|---|
| **포털(이 리포)** | 규칙 · 원장 · 감지기 · 실행기 · 현황판 · 보고서 렌더 · RA 시스템 계정 게시 · 서비스 PAT 연결 · update-all 기다림 |
| 게이트웨이 | 서비스 허용 목록에 계약 도구 · 감사에 `via=service:auto-pipeline` |
| StepForge | 과제 · 차수 감지 창구(목록의 갱신 시각 또는 웹훅 확장) · subject 에 SP key · 차수 |
| DynaForge(KooRemapper) | 같은 감지 창구 · 전각도 낙하 계약(후처리 예약 · 캠페인 반입 위에) |
| ThermalShock | 계약 다섯 · SP key 받기(A13) |
| ste · SmartTwinMCP · KooSlurm | 전각도 실행 경로의 서비스 계정 제출 |
| RA(운영 관리자 — 리포는 hands-off) | 시스템 계정 · 시스템 공간 · 조직 `edit` grant · 시스템 양식 등록 |

## 6. 단계(마일스톤)

- **M0 계약 굳히기** — 계약 v1 문서(`contract.md`) · 결과 봉투 JSON Schema · 각 앱 요청서 · cae00 받은 편지함 물음(§9).
- **M1 포털 뼈대(dev)** — 표 · 규칙 저장 · 감지기(묻기) · 그림자 실행 · 현황판 · 끄기 스위치. 앱은 계약 꼴의 가짜(진짜 꼴 그대로 — 가짜는 진짜 꼴로).
- **M2 첫 해석 하나 끝까지(cae00)** — 앱 하나(먼저 계약을 갖춘 쪽)로 그림자 → approve → 결과 봉투 → 해석별 보고서 → RA 시스템 공간.
- **M3 두 번째 해석 · 종합 · 이전 차수 대비** — DAG · 대체 사슬 · AP-D5.
- **M4 auto 단계 · 알림 감지** — 검증된 규칙만 auto, StepForge 웹훅 또는 SP 변경 목록.
- **M5 확대** — 심의 · 리스크 심사 단계(판정 넘침), 과제 인사이트 보기.

## 7. 위험

- **과제 key 정합** — 앱마다 과제 번호가 다르다. 계약에서 SP key · 차수를 필수로 하고, 못 풀면 그 단계는 `blocked`(짐작하지 않는다).
- **실패가 성공처럼 보이는 응답** — 단계 성공은 결과 봉투로 코드가 판정한다(절차 PLAN 5-6 — 실패 다섯 모양 중 셋은 `isError=false`).
- **클러스터 비용** — 그림자로 먼저 「무엇을 얼마나 냈을지」를 재고 나서 approve · auto 로 올린다. 야간 창 · 상한.
- **여러 리포의 계약 채택** — 한 해석으로 끝까지 통과시킨 뒤 넓힌다.
- **자동 게시의 되돌리기** — RA 게시는 작성자가 직접 못 내린다. 전용 게시판에만 올리고, 규칙 판 · 입력 지문을 보고서에 실어 잘못 올라간 것을 찾을 수
  있게 한다.
- **서비스 PAT 만료 · 회수** — 만료 전 표시, 회수되면 실행은 `blocked` 로 서고 알린다.

## 8. 하지 않는 것

- 포털이 해석 조건을 정하지 않는다 — 앱의 profile 이 정한다.
- LLM 이 단계의 도구 · 인자를 고르지 않는다.
- 사람 심의 보고서의 게시 관문은 바꾸지 않는다(AP-D3 은 자동 파이프라인의 시스템 계정 길에만).
- ReportArchive 리포에 커밋하지 않는다 — 시스템 계정 · 공간 · 양식은 운영 관리자가 화면 · 창구로.
- dev 에서 실제 해석 결과를 판정하지 않는다 — 꼴만 본다(AR-D10).

## 9. 밖에 물을 것(받은 편지함 · 앱 세션)

- 운영 — RA 시스템 이름 · 계정 · 공간을 누가 만들고 어디에 둘지, 자동 보고서를 볼 조직(grant `edit` 대상).
- 운영 — 전각도 낙하 · 열충격을 서비스 계정으로 낼 수 있는가(KooSlurm · stcx 서비스 계정 sbatch, ODB 허브 서비스 토큰).
- 앱 세션 — 과제 · 차수 감지 창구를 무엇으로 줄 수 있나(목록 갱신 시각 · 웹훅 · SP 변경 목록), 계약 다섯을 언제 갖출 수 있나.
- 운영 — 「CAD 파싱 끝 + DynaForge 모델 등록」 말고 실제로 해석을 시작해도 되는 신호가 무엇인가(입력 준비의 운영 정의).
