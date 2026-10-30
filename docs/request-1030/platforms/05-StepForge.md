# 05 StepForge — 10-30 요청에서 할 일

- **받는 곳** — StepForge 세션 `stepforge-d4`.
- **어떻게 갔나** — 10-30 KST 포털 세션 `hwaxportal-a5` 가 SendMessage 로 행을 정본 글 그대로 보냈다(덧붙인 것 — HA-29 카드에 실을 시작 전 작업량을 셀 길이 있는지, HA-28 이 읽을 상태 칸). 답을 받았다(아래 인용 — [`../outbound.md`](../outbound.md) 1절 표의 '답' 칸 그대로).
- **요청서 정본** — [`../../request_261030.md`](../../request_261030.md) 4절 '박스 밖 플랫폼' 의 ST-12 행. 이 행에 닿는 7절 '다시 볼 시험' 줄은 끝의 '끝나면' 에 옮겼다. 같은 요청의 계획 · 판단 · 체크리스트는 [`../PLAN.md`](../PLAN.md) · [`../context-notes.md`](../context-notes.md) · [`../checklist.md`](../checklist.md) 다.
- **cae00 기준 판** — 요청서에 없다(머리의 기준 판과 끝 절의 cae00 HEAD 목록 어디에도 StepForge 가 없다). 그래서 이 박스 HEAD 와 대조했다. 요청서 근거로 짐작하면 cae00 판은 drop_check 를 잡으로 거는 길(D-632 `aa387d9`, 10-28 07:41 KST)이 든 판이다 — DW-03 이 그 잡을 걸었고, 그 앞 판 `aa387d9^` 의 측정 잡 도구 목록에는 drop_check 가 없다. 5절 OB-59 는 프로젝트 이름 · 마케팅명 길(D-647 `c65c92a`)이 개발 main 에만 있다고 적었으니 그 앞 판이다. 정확한 sha 는 대조 못 함(이 세션은 cae00 에 닿지 않는다).
- **이 박스(dev)에서 대조한 판** — StepForge `ff308d1`(main · 커밋 10-30 12:39 KST · main 작업 트리에 고친 파일 0) · 대조 시각 2026-10-30 17:58 KST.

> 받은 답(`outbound.md` 그대로) — 10-30 받음 — ① 시작 전 작업량은 이미 있는 읽기 도구 `estimate_cost(project_id, job, args)`(형상을 읽지 않고 DB 값만, 칸 `expected_s` · `cost_basis` · `gateway_verdict`(over · may_exceed · under · no_basis) · `basis_note` · `advice`) — ST-12 (2)가 판 전체 작업량 칸을 여기와 run_job 시작 응답에 더한다(칸 이름은 짓고 알림). ② `job_status(job_id)` 의 `status` 는 queued · running(도는 중) / done · failed · cancelled(끝), `progress` 0 ~ 100, `error` · `ended` · `result`, 판 전체 측정은 수십 분 — 상한을 넉넉히. ③ ST-12 (1) 합치기 진행률은 OCC 한 호출이라 묶음 합치기를 실물 큰 판에서 재 보고 정함, (3) owner 는 원천에서 가림. 지금 다른 묶음(온톨로지 그래프 도구) 착지 중이라 ST-12 는 그 뒤 판

## 할 일

### ST-12 · 중간 — 판 전체 drop_check 잡의 진행률 · 예상 작업량 · 담당자 칸

- **무엇이** — 판 전체 drop_check 잡이 진행률 10% 에 30분 머물렀다. 한 호출 관문의 예상(60초)은 하한이었다.
- **근거** — DW-03 — 3,658형상 부울 합치기 단계에서 진행이 오르지 않았고 단일 러너를 잡았다.
- **할 일** — 합치기 단계에도 진행률을 올리고, 잡 시작 응답에 '예상 작업량(형상 수 · 하한 초)' 과 '러너를 오래 잡을 수 있다' 를 싣는다. list_projects 의 담당자 칸은 MCP 출력에서 가린다.

#### 지금 판에서의 자리

줄 번호는 StepForge `ff308d1` 의 것이다. 행이 `파일:줄` 을 들지 않아, 행이 이름 댄 것(잡 진행률 · 합치기 · 한 호출 관문 · 잡 시작 응답 · list_projects 담당자 칸)을 코드에서 찾았다. '`aa387d9` 뒤' 는 위에서 짐작한 cae00 판의 하한부터 HEAD 까지다.

- **ST-12 에 닿은 커밋은 아직 없다.** `git grep "ST-12"` 가 0건이고, 작업 가지 `work/a63` · `work/a64` · `work/a65` 도 main 위 커밋이 0이다(그 작업 트리의 고친 파일은 보지 않았다). 답 끝 줄대로 온톨로지 그래프 도구 묶음 뒤의 판이다.
- **(1) 진행률 — 그대로 있다.** 측정 잡 `run_measure`(`core/job_worker.py:5361`)는 `emit(10)`(`:5374`) 뒤 `M.measure_unbounded(...)`(`:5387`)가 돌아올 때까지 진행을 내지 않고 `emit(95)`(`:5388`)로 건너뛴다. `measure_unbounded`(`app/mcp_server.py:9670`)는 그 도구의 본체를 `budget_s=0` 으로 부르고(`:9677`), drop_check 본체 `_drop_check_calc`(`:17583`)가 형상 적재 · 합치기 `oc.fuse_many(shapes)`(`:17619`) · 방향별 계산을 그 사이에 다 한다 — 10% 에 머문 것과 맞는다. 합치기는 `BRepAlgoAPI_Fuse` 한 호출이다(`core/occ_compat.py:2518` · `:2526`) — 답 ③의 'OCC 한 호출' 과 같다. 진행 줄은 워커 stdout 의 `PROGRESS n`(`core/job_worker.py:215` `emit`)을 러너가 읽어 잡 행에 쓴다(`app/jobs.py:42` · `:955`). `aa387d9` 뒤로 `run_measure` · `_drop_check_calc` 를 바꾼 커밋은 없다(`git log -L`).
- **'예상(60초)은 하한' — 관문이 그렇게 생겼다.** 한 호출 상한은 `PAIR_MEASURE_BUDGET_S = 60.0`(`core/measure.py:104`)이다. 합치기 관문 `sweep_fuse_gate`(`core/profile.py:1547`)는 `fuse_parts(…, stop_s=budget_s)`(`:1555`)로 세다가 상한을 넘으면 거기서 그친다(`:1542-1543`). 그래서 멈춘 도구 응답의 `estimated_s` 는 60초를 갓 넘긴 하한이고, 사유 글도 '이상(… 하한 …)' 으로 말한다(`_drop_stopped`, `app/mcp_server.py:17665-17667`). 형상 수 · 하한 초는 그 멈춘 응답의 `skipped_work`(`parts` · `box_pairs` · `estimated_s` · `at_least` · `bound` — `core/profile.py:514-516`)에만 있다. 잡 길(`budget_s=0`)은 `paced_budget` 이 0 을 그대로 돌려줘(`core/measure.py:393`) 합치기 작업량을 아예 세지 않는다(`app/mcp_server.py:17613-17618`).
- **(2) 잡 시작 응답 — 그 칸이 없다.** `run_job`(`app/mcp_server.py:1249`)은 `job_id` · `kind` · `status`(`"pending"`) · `params_accepted` · `note` 와 조건부 `runner_note` 만 낸다(`:1305-1317`). 잡의 안전망은 기본 6시간이다(`app/config.py:177` `STEPFORGE_JOB_TIMEOUT` — 그 전에는 사람의 취소만 끊는다, `core/job_worker.py:5367`). 동시 잡 수의 기본값은 2다(`app/jobs.py:43` `STEPFORGE_MAX_JOBS`). cae00 의 그 값은 대조 못 함(그 박스 설정이다).
- **답 ① `estimate_cost` — 있다. 다만 잡 견적의 판정 값이 답과 다르다.** 도구는 `app/mcp_server.py:31143` 이고 칸 `expected_s` · `low_s` · `high_s` · `cost_basis` · `basis_note`(`app/cost_estimate.py:1084`) · `gateway_verdict`(`:1133`) · `advice`(`:1149-1191`)가 있다. `job=` 으로 물으면 `gateway_verdict` 는 `async_job`(`:1089`)이고 `advice` 는 null 이다 — over · may_exceed · under · no_basis 는 `tool=` 견적의 값이다. 잡 견적에는 도는 · 기다리는 잡 수와 `max_concurrent` 를 담은 `queue` 가 붙는다(`:960-968`). `measure` 잡은 크기 단위가 없고(`JOB_UNITS`, `:112`) 인자가 비용을 정하는 잡(`ARG_JOBS`, `:123`)이라, 근거는 이 과제에서 같은 인자로 끝난 잡뿐이다(코드 읽기 — 돌려 보지는 않았다). 그래서 처음 거는 판 전체 drop_check 잡이면 `expected_s` 가 null 일 수 있다. `tool="drop_check"` 에 `first_contact` 를 준 견적은 최악 단가(리프 인스턴스당 0.9초 — `app/mcp_server.py:129` · `app/cost_estimate.py:157` · `:734-741`)를 `high_s` 로만 쓴다(`expected_s` 는 null — `:1003-1005`). 판 전체 작업량 칸은 아직 없다(답 ①이 ST-12 (2)로 더한다고 했다).
- **답 ② `job_status` — 대기 값의 글자가 다르다.** `job_status`(`app/mcp_server.py:1624`)는 잡 행의 `status` · `progress` · `error`(`app/db.py:95-96`) · `result` 와 `ended`(`app/mcp_server.py:1686`)를 낸다. 대기 값은 이 판 코드에서 `pending` 이다(넣기 `app/jobs.py:47-51` · 집기 `:736` · `run_job` 응답 `app/mcp_server.py:1305`). 답 ②의 'queued' 라는 값은 이 판에 없다.
- **(3) 담당자 칸 — 그대로 실린다.** `list_projects`(`app/mcp_server.py:549`)가 `p.owner` 를 읽어(`:582`) 줄마다 싣고, 짧은 꼴의 칸 목록에도 `owner` 가 있다(`:1893`). 거르개 `_project_filter`(`:621`)는 담당자로도 찾는다(`:626`). 담당자 값은 REST 로 과제를 만들 때 허브가 넘긴 이름이나 메일로 채운다(`app/rest.py:103` · `:258`) — DW-03 의 '메일' 과 맞는다. REST `GET /projects` · `GET /list-projects`(`app/rest.py:288` · `:1734`)는 같은 MCP 본체를 부른다 — 본체에서 가리면 웹 목록에서도 빠진다. 요청서 행은 list_projects 만 짚었지만 같은 칸이 `get_project_meta`(`app/mcp_server.py:727` · `:766`)에도 실리고, 허브 과제 보기(`find_plm_task` · `get_project_meta.plm_task` 가 함께 쓰는 `task_view`)는 허브 행의 `properties` 를 통째로 싣는다(`core/sp_core.py:1217`). 그 `properties` 에 사람 칸이 있는지, DW-22 의 '담당 계정' 이 어느 도구 출력이었는지는 대조 못 함(요청서에 도구 이름이 없고, 이 박스에서 허브 데이터는 열지 않았다). `aa387d9` 뒤 `list_projects` 를 바꾼 커밋은 `8a653a7`(D-638 — 짧은 꼴 · 쪽) 하나이고 담당자 칸은 그대로다.

#### 우리 쪽 맞물림

이 요청의 우리 리포 행은 포털 세션 `hwaxportal-a5` 가 지금 고치는 중이다. 아래는 계획이고 아직 들어가지 않았다.

- **HG-22(게이트웨이)** — 칸 이름 목록에 owner · partOwner · submitter · user · email · assignee 꼴을 더하고, 메일 꼴 · 사내 계정 꼴 · 사설 IP 꼴은 칸 이름과 상관없이 가리고, REST 다리 출력도 같은 가림을 거치게 고치는 중이다(6절 — TODO-20261029 R-08 과 한 번에). 들어가면 위의 `owner` 는 게이트웨이를 지나며 가려진다. 요청서 HG-22 가 '원천 쪽 요청은 4절' 이라 했고 ST-12 (3)이 그 원천 몫이다. 답 ③ 이 원천에서 가린다고 받았으니 두 겹이 된다.
- **HA-28(에이전트)** — 상태 조회 도구(요청서 목록에 heaxstep_forge_job_status 가 있다)는 에이전트가 코드로 기다렸다가 끝났거나 상한에 닿은 결과만 LLM 에 넘기고, 기다리는 동안 화면에 진행률을 흘리게 고치는 중이다. 읽는 칸은 답 ②의 `status` · `progress` 다. ST-12 (1)이 들어가기 전에는 그 진행률이 측정 잡 내내 10 에 머문다. 이 판의 대기 값은 `pending` 이다(위). 답 ②는 '판 전체 측정은 수십 분 — 상한을 넉넉히' 라 했고, 요청서 HA-28 의 예(상한 10분)는 DW-03 의 1,812초보다 짧다.
- **HA-29(에이전트)** — run_job 을 포함한 잡 시작 도구는 이번 턴 사람 발화가 시키지 않았으면 코드 단에서 확인 카드로 멈추고, 도구가 '예상 작업량' 을 주면 확인 문구에 싣게 고치는 중이다. 시작 전 작업량은 run_job 앞에서 답 ①의 `estimate_cost` 로 읽는다. 이 판에서 잡 견적은 `gateway_verdict` 가 `async_job` 이고 처음 거는 측정 잡은 `expected_s` 가 빌 수 있다(위). 답 ①대로 ST-12 (2)가 판 전체 작업량 칸을 견적에 더하면 그 자리가 찬다. run_job 시작 응답의 칸은 잡을 건 **뒤**에 오므로 카드에는 견적 쪽이 쓰인다.
- **HP-53(포털)** — 운영자 정의의 `writes` · `confirm` 에 'StepForge run_recipe · save_recipe · set_revision · set_admin(confirm)' 을 넣는 중이다(판단 C-5 — 목록은 지금 채운다). 포털 main(`bf5cd94`)의 he-cad-stepforge `writes` 에 run_job 은 이미 있고 그 넷은 없다. HA-29 의 관문이 이 목록을 읽는다.
- **OB-101(우리 몫 — 보내지 않음, cae00 사람)** — 'StepForge 코어 받기 cron 에 주 1회 `--full` 을 더한다. 허브에서 빠진 과제가 find_plm_task 결과에 남지 않게 한다.' 남았다(TODO-20261029 T-17). StepForge 쪽 받침은 이미 있다 — `scripts/plm_sync.py` 의 `--full`(`:31`)이고, 그 파일 머리가 바깥 cron · systemd 타이머로 '매일 증분 · 주 1회 `--full`' 을 권한다(`:16`). StepForge 세션이 할 일은 없다.
- **OB-59(우리 몫)** — 요청서는 D-647(`c65c92a`)의 프로젝트 이름 · 마케팅명 길을 '개발 SIF 대기' 로 적었다. 그러나 포털 [`../../request-1029/server-setup.md`](../../request-1029/server-setup.md) 1절 표의 StepForge 줄(커밋 `5ba7a33`, 10-30 12:59 KST)은 그 길이 든 `ff308d1` 의 SIF(`dist-20261030-034158Z`)를 Drive 에 올렸다고 적었다. 남은 것은 cae00 에서 `infra/scripts/drive-drift.sh heax` 로 대조하고 update-all 로 받는 일이다([`90-OURS.md`](90-OURS.md) OB-59). ST-12 가 든 SIF 는 그 뒤 판으로 같은 길을 탄다('끝나면' 5번).

## 끝나면

StepForge 세션이 ST-12 를 끝내면 포털 세션 `hwaxportal-a5` 에 아래를 알린다.

1. **커밋** — sha 와 결정 번호(D-…). ST-12 의 세 몫((1) 합치기 진행률 · (2) 시작 응답과 견적의 작업량 칸 · (3) 담당자 칸 가림)이 각각 어느 커밋인지.
2. **새 칸 이름과 뜻** — 답 ①이 '칸 이름은 짓고 알림' 이라 했다. HA-29 의 확인 카드와 HA-28 의 진행 표시가 그 이름을 읽는다. (1)을 실물 큰 판에서 재 보고(답 ③) 진행률을 못 올리기로 했으면 그 까닭과 대신 낸 것.
3. **가림의 범위** — list_projects 만인지, `get_project_meta` 와 허브 과제 보기의 `properties` 도인지, REST · 웹 목록에서도 빠지는지(같은 본체다).
4. **대기 값 한 줄** — 답 ②의 'queued' 와 이 판 코드의 `pending` 가운데 MCP 출력이 실제로 무엇인지. HA-28 의 판정이 그 글자를 본다.
5. **배포물** — HEAX Hub SIF 를 Drive 에 올린 판(이름 · 판 sha). StepForge 는 cae00 이 update-all 로 받는 플랫폼이다(요청서 머리). D-647(`c65c92a`)이 든 SIF 는 이미 올렸다고 적혀 있어 OB-59 는 이 SIF 를 기다리지 않는다. 새 SIF 도 포털이 `infra/scripts/drive-drift.sh heax` 로 대조한다.

받은 뒤 포털 몫은 답을 [`../outbound.md`](../outbound.md) 표의 '답' 칸과 `server-setup.md`(아직 없다 — 체크리스트 4절에서 쓴다)에 옮기는 것이다. cae00 사람 몫은 update-all 로 새 SIF 를 받은 뒤 아래 시험을 다시 보는 것이다(두 QA 는 SSO 로 로그인한 웹 화면으로 돌렸다).

### 7절에서 이 플랫폼에 닿는 다시 볼 시험(정본 그대로)

| 시험 | 언제 | 볼 것 |
|---|---|---|
| DW-02 후속 · DW-03(후속 포함) | HA-28 · HA-29 뒤 | 상태 조회가 LLM 왕복 없이 기다린다. 잡은 확인 뒤에만 건다. |
| DW-07 · DW-03 · 06 · 12 · 22 | HG-21 · HG-22 뒤 | 숫자가 그대로 나오고, 사람 이름 · 메일 · 사설 IP 가 가려진다. |

4절 표에는 '다시 볼 시험' 칸이 없고, 7절에도 ST-12 만의 줄은 없다. DW-03 은 StepForge run_job(판 전체 drop_check)과 `owner`(메일), DW-22 는 StepForge 담당 계정이 걸린 시험이다(요청서 HA-29 · HG-22 근거). 덧붙여 볼 것(이 시트의 제안 — 요청서에 없다)은 ST-12 가 든 판에서 DW-03 을 다시 돌릴 때 측정 잡의 진행률이 10 에 머물지 않는지와 시작 응답에 작업량 칸이 있는지다.
