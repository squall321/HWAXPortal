# 14 파트너 앱(ste 클러스터 조회 · stcx SmartTwinMCP) — 10-30 요청에서 할 일

| 항목 | 내용 |
|---|---|
| 받는 곳 | PA-20 은 세션 `smarttwinexplorer-06` 이다(cluster_info 가 SmartTwinExplorer `backend/mcp_server/server.py` 에 있다). PA-16 · PA-19(다시)는 세션 `smarttwinmcp-4c` 이다. PA-16 은 stcx 쪽 운영 배포라 사람(stcx 운영) 일정이 걸린다. |
| 어떻게 갔나 | 10-30 KST 포털 세션 hwaxportal-a5 가 세션으로 보냈다([`../outbound.md`](../outbound.md) 1절). PA-20 은 '10-30 끝' 답이 왔다(SmartTwinExplorer main `4f5e0e0` — 포털 `bf5cd94` 가 답 칸에 옮겼다). PA-16 · PA-19(다시)는 '기다림' 이다. |
| 요청서 정본 | [`../../request_261030.md`](../../request_261030.md) — PA-20 은 4절 '박스 밖 플랫폼' 표, PA-16 · PA-19(다시)는 끝 절 '이전 회차에서 남은 챗 · 디지털 워커 요청' 의 '클러스터 · SmartTwin(stcx)' 표다. |
| cae00 기준 판 | 요청서에 이 플랫폼들의 판이 없다 — 이 박스 HEAD 와 대조했다. PA-16 · PA-19 근거의 포털 줄만 포털 `aec8e29` 기준이다. |
| 이 박스(dev)에서 대조한 판 | SmartTwinExplorer `b059413`(main, 이 박스의 origin/main 추적 참조와 같다) · SmartTwinMCP `97c0e0b`(가지 `feat/cuboid-scatter-drop`, main 은 `a98b9a7`) · KooSlurmInstallAutomationRefactory `a4734e7a`(main, origin/main 추적 참조와 같다 — :5013 에서 도는 정본) · 포털 `bf5cd94` · 게이트웨이 `67d8d00`. |
| 대조한 시각 | 2026-10-30 18:02 KST. |
| 이름 | ste 는 24대 클러스터와 그 위의 SmartTwinExplorer 웹이다. stcx 는 356대 클러스터이고 SmartTwinMCP 가 상대한다. 요청서의 'Ste(클러스터 조회 앱)' 는 ste 다. 'stc' 는 ssh 접속 별칭으로만 쓴다. |
| 이 박스에 없는 문서 | 10-27 의 `14-Partner-apps.md`, `TODO-20261029`, QA 보고서(`QA-DIGITAL-WORKER-20261030.md`)는 cae00 문서라 이 박스에 없다 — 그 원문은 대조 못 함. |
| 한 줄 | PA-20 은 원천에서 고쳐 올렸고 cae00 반영(사람)과 DW-12 다시 보기만 남았다. PA-16 · PA-19 는 답을 기다린다 — 잠금 코드는 :5013 정본(KooSlurm)에 10-14 부터 있고, stcx 운영에 떠 있는지는 이 박스에서 대조 못 함. |

## 할 일

### PA-20 · 중간 — cluster_info 의 컨트롤러 사설 IP · 잡 제출자 메일

- **대상** — Ste(클러스터 조회 앱)
- **무엇이** — cluster_info 가 컨트롤러 사설 IP 와 잡 제출자 메일을 준다.
- **근거** — DW-12.
- **할 일** — 챗 · MCP 출력에서는 호스트 이름만 싣고 IP · 메일은 뺀다.

4절 표에는 '다시 볼 시험' 칸이 없다. 7절의 DW-12 줄은 아래 '끝나면' 에 적었다.

#### 지금 판에서의 자리

- 근거 칸은 'DW-12.' 뿐이라 파일:줄이 없다. 받는 곳 메모(cluster_info 가 SmartTwinExplorer `backend/mcp_server/server.py` 에 있다)를 따라 SmartTwinExplorer 를 대조했다.
- **이미 고쳤다 — `4f5e0e0`(10-30 17:54 KST, 'fix(mcp): 챗 출력에서 사설 IP·메일을 뺀다 — PA-20(10-30 디지털 워커 QA DW-12)').** 뒤이어 `b059413`(17:55 KST, 체크리스트)이 있다. 둘 다 이 박스의 origin/main 추적 참조에 들어 있다. `git log c588bb0..HEAD -- backend/mcp_server/server.py backend/src/ste/slurm.py` 는 `4f5e0e0` 하나다.
- 컨트롤러 사설 IP — 고치기 전 판 `c588bb0` 에서는 `backend/src/ste/slurm.py:83` `cluster_info()` 가 `scontrol show config` 의 `SlurmctldHost[0]` 를 `"controller"`(`:93`)로 그대로 냈다. MCP `cluster_info`(`backend/mcp_server/server.py:75-78`)는 REST `/api/cluster`(`backend/src/ste/routes/cluster.py:11-16`)를 그대로 넘긴다. 지금 판은 `slurm.py:91-97` 이 괄호 앞 호스트 이름만 남기고, 이름 자리에 주소만 있으면 비운다(`"controller": ctl`, `:100`). 원천에서 고쳤으므로 웹 · REST · MCP 가 함께 바뀐다. MCP `cluster_info`(지금 `server.py:96-99`)는 `_scrub` 을 거치지 않는다.
- 잡 제출자 메일 — `cluster_info` 응답에는 잡 행이 없다. 메일은 잡 행의 `submitted_by` 칸에서 나온다. 잡을 낼 때 `request.state.token_name = user["email"]`(`backend/src/ste/auth.py:93`)이 `jobs.submitted_by`(`backend/src/ste/db.py:22`)에 들어가고, 잡 목록 · 상세(`backend/src/ste/routes/jobs.py:37-45` · `:147-154`)가 행을 통째로(`db.row_to_job`, `db.py:238`) 낸다. 제출 PC 주소 `source_ip`(`db.py:24`)도 같은 길로 나갔다. outbound.md 의 답도 '메일은 cluster_info 가 아니라 list_jobs · get_job_status 잡 행' 이라 적었다.
- 지금 판의 가림 — `server.py:80-93` 의 `_PII_KEYS`(`submitted_by` · `source_ip` · `owner_id` · `sync_dir`)와 `_scrub()` 이 그 칸을 빼고, 글 속 사설 IPv4 · 메일 꼴을 `[사설IP]` · `[메일]` 로 바꾼다. 잡 · 결과 · 파일 · 동기화 설정을 내는 여덟 도구(submit_job · get_job_status · list_jobs · get_job_result · get_job_file · cancel_job · get_sync_settings · set_job_sync)의 반환이 모두 `_scrub` 을 거친다(`server.py:168` · `:175` · `:182` · `:190` · `:211` · `:222` · `:229` · `:239`).
- 일부러 남긴 것 — REST `/api/jobs` 는 `submitted_by` · `source_ip` 를 그대로 낸다(웹 관리자 감사용, 비관리자는 자기 잡만 — outbound.md 의 답).
- 시험 — `backend/tests/test_slurm_topology.py` · `backend/tests/test_mcp_server_contract.py` 에 PA-20 시험이 더해졌다(`4f5e0e0`). 세션은 '시험 173 통과 · dev 스테이징 VM 실측 0건' 이라 답했다. 이 시트는 시험을 돌리지 않았다.
- cae00 이 붙는 ste 헤드노드에 들어갔는지는 이 박스에서 대조 못 함 — 에어갭(teleport) 배포는 사람이 불러야 돈다(포털 `infra/scripts/update-all.sh:1193-1227` 2c).

#### 우리 쪽 맞물림

- 게이트웨이 HG-22(고치는 중 — [`../checklist.md`](../checklist.md) 2절)는 사람 칸 이름(owner · partOwner · submitter · user · email · assignee 꼴)을 더하고, 메일 꼴 · 사내 계정 꼴 · 사설 IP 꼴은 칸 이름과 상관없이 가리고, REST 다리 출력도 같은 가림을 거치게 한다(요청서 2절, 6절 R-08 과 한 번에). 게이트웨이를 거치는 출구는 HG-22 로도 가려지지만, PA-20 은 원천에 청한 것이다 — 웹 · REST 와 게이트웨이를 거치지 않는 MCP 호출에는 HG-22 가 닿지 않는다.
- 지금 게이트웨이 main(`67d8d00`)의 칸 이름 목록(`gateway.py:613-620`)에는 `submitted_by` · `source_ip` · `controller` 가 없고, 메일 · 사설 IP 꼴 가림도 없다. cae00 판 `44f4b8d` 의 목록(`:612-620`)도 같다. 그래서 cae00 에서는 PA-20 반영과 HG-22 가운데 먼저 들어가는 쪽이 DW-12 의 노출을 막는다.
- PA-20 이 남긴 REST `/api/jobs` 의 두 칸은 게이트웨이 REST 다리를 지날 때 HG-22(R-08 몫)가 한 번 더 건다고 outbound.md 의 답이 적었다. 그 몫은 HG-22 와 함께 고치는 중이다.
- 원천 표지는 `[사설IP]` · `[메일]`(SmartTwinExplorer `server.py:92`)이고, 게이트웨이 가림 표지는 `[가림:<종류>]` 꼴(`gateway.py:654` · `:667` 등)이다. DW-12 를 다시 볼 때 어느 쪽이 가렸는지 가를 수 있다.
- HP-54(조건부 — [`../context-notes.md`](../context-notes.md) C-4)는 he-sim-smarttwin 에 ste 선택 몫(cluster_info 는 조회, submit_job · set_job_sync 는 writes, ste_cancel_job 은 confirm)을 두자는 행이다. OB-92 에서 둘째 길을 고르면 SmartTwin 운영자가 cluster_info 를 부르게 되므로 PA-20 의 cae00 반영과 함께 본다. 지금은 OB-92 결정 전이라 손대지 않는다.

### PA-16 · PA-19(다시) · 중간 — stcx SmartTwinMCP 운영 배포 · environment 덮어쓰기 잠금

- **무엇이** — (중간) stcx SmartTwinMCP 운영 배포와 `extra_scenario_overrides` 의 environment 덮어쓰기 잠금이 아직이다. OB-92 의 '잇기' 길을 지금 열면, 운영자 writes 의 낙하 도구로 컴퓨트 노드에서 임의 명령이 돌 수 있다.
- **근거** — 14-Partner-apps PA-16 · PA-19(10-27, 답 없음 — TODO-20261029 W-02 대기) · 포털 `aec8e29` `infra/personas/he-team.json:116`(he-sim-smarttwin writes 에 fullangle_drop_simulation · single_drop_simulation). 이 요청서 OB-92 에 이 선행 조건이 적혀 있지 않다.
- **할 일** — PA-16(:5013 운영 배포)과 PA-19(environment 잠금)를 다시 묻는다. OB-92 의 잇기 길은 둘이 끝난 뒤에 연다(5절 OB-34 · OB-25).
- **출처** — 14-Partner-apps PA-16 · PA-19 · 이 요청서 OB-92

#### 지금 판에서의 자리

- **고칠 자리부터 — :5013 에서 도는 코드는 SmartTwinMCP 리포가 아니다.** SmartTwinMCP 리포의 `CLAUDE.md`(`97c0e0b`, 09-22)가 ':5013 에서 실제로 도는 것은 `KooSlurmInstallAutomationRefactory/dashboard/smarttwin_mcp` 다 … 여기를 고치면 시험은 통과하는데 도는 것은 안 바뀐다' 고 적었다. 이 박스의 dev :5013 도 지금 그 정본에서 돈다(`--tools-root` 도 그쪽, 10-27 09:13 KST 기동 — 프로세스 실측). 그래서 두 리포를 다 대조했다.
- **PA-19(environment 잠금) — 정본에는 들어 있다.** KooSlurm `05240273`(10-14 07:36 KST, 'extra_scenario_overrides 의 environment 등 잠금 — 컴퓨트 노드 RCE 차단') · `b6bb79dc`(10-14 08:03 KST, 덮어쓰기 문자열을 안전 토큰으로 — postprocess 경유 셸 · #SBATCH 주입 차단) · `5aa61b67`(10-14 11:36 KST, 개통 전 접근 통제 — job_* 는 PAT 호출자의 잡만, 낙하 도구는 허용 루트 안만)이다. 셋 다 이 박스의 origin/main 추적 참조에 있다. 지금 판(`a4734e7a`) `dashboard/smarttwin_mcp/tools/_shared/scenario_builder.py` 의 자리는 아래와 같다.
  - `LOCKED_SCENARIO_KEYS`(`:93` — environment · mode · model_file · output_dir · project_name), `SAFE_ENVIRONMENT_KEYS`(`:96`, 시간 상한 셋만 통과), 후처리 SIF 경로 제한(`:101`), `sanitize_strings`(`:128`), `strip_locked_overrides`(`:168`).
  - 합치는 세 자리가 모두 걷어 낸 뒤 합친다 — `deep_merge(scenario, strip_locked_overrides(…))`(`:271` · `:346`)와 `build_mode_scenario` 안(`:416`).
  - 두 낙하 도구의 latest 는 1.1.2(`tools/fullangle_drop_simulation/latest` · `tools/single_drop_simulation/latest`)이고, 시험은 `dashboard/smarttwin_mcp/tests/test_scenario_lock.py`(`test_` 함수 13개)다.
  - 정본 작업 트리의 `scenario_builder.py` 는 HEAD 와 같다. `dashboard/smarttwin_mcp` 아래에 커밋 전 변경 다섯 파일(커버리지 문서 · 도구 명세 · 충격 도구 둘)이 있지만 잠금 자리와 무관하다.
- **SmartTwinMCP 리포(`97c0e0b`)에는 잠금이 없다.** `tools/_shared/scenario_builder.py:79-91` 의 `deep_merge` 가 덮어쓰기를 그대로 합치고(부르는 곳 `:146` · `:217` · `:306`), 두 낙하 도구의 latest 는 1.1.0 이다. 이 리포의 어느 가지에도 잠금 키가 없다(`git log --all -S LOCKED_SCENARIO_KEYS` 0건).
- 잠금 코드는 10-27 요청보다 먼저 들어갔다. 그래서 '잠금이 아직이다' 가 (가) 운영 stcx :5013 이 그 판으로 떠 있지 않다는 뜻인지, (나) SmartTwinMCP 리포를 본 판정인지는 가르지 못했다 — 10-27 원문(`14-Partner-apps.md`)이 이 박스에 없어 대조 못 함.
- **PA-16(:5013 운영 배포) — 이 박스에서 대조 못 함.** stcx 운영 박스에 닿지 않는다. KooSlurm 쪽 기록으로는 10-14 회신(`dashboard/smarttwin_mcp/deploy/STCX_DYNAFORGE_REPLY.md:6-9`)이 §2 잠금 · §3 유닛 예시는 코드에 반영했고 §1 운영 배포는 운영 측 절차로 부탁했다. 그 회신 §0(`:13-27`)은 운영 리포에 `5aa61b67` 이 들었는지 보라고 적었다. 정본 체크리스트 `dashboard/smarttwin_mcp/docs/smarttwin_coverage/checklist.md:53`('운영 유닛 drop-in STMC_WORK_ROOTS — 운영 측')과 `:58`('운영 SmartTwinMCP 에 bffd4e50 이상이 반영되면 …')은 아직 열려 있다.
- 회신 §5(`STCX_DYNAFORGE_REPLY.md:170-172`)는 'MCP `/mcp` 엔드포인트 자체는 PAT 를 검사하지 않습니다 … 1차 관문은 게이트웨이(Teleport 터널)입니다' 라 적었다. OB-25 의 터널을 정할 때 함께 볼 줄이다.
- 포털 근거 줄 — `infra/personas/he-team.json:116` 은 `aec8e29` 와 지금 포털 `bf5cd94` 에서 같다(`git log aec8e29..HEAD -- infra/personas/he-team.json` 0건, 작업 트리도 같다). he-sim-smarttwin(`:94-127`)의 `writes` 에 fullangle_drop_simulation · single_drop_simulation 이 그대로 있다.
- `TODO-20261029 W-02` 는 cae00 문서라 대조 못 함.

#### 우리 쪽 맞물림

- OB-92(우리 몫 — 남았다)는 두 길이다. 첫째 길(cae00 게이트웨이에 SmartTwin MCP 를 잇는다)은 OB-34 · OB-25 이고, 요청서 5절은 '선행은 끝 절의 PA-16 · PA-19(다시)다' 라 적었다. 둘째 길(he-sim-smarttwin 정의를 연결된 클러스터 앱으로 바꾼다)은 HP-54 로 이어진다.
- OB-34 는 :5013 이 뜨면 게이트웨이 `provision.env` 로 SmartTwinMCP 를 등록하는 일이다. 포털 update-all 은 `provision.env` 에 `SMARTTWIN_MCP_URL` 이 없으면 게이트웨이가 smart-twin-mcp 를 등재하지 않는다고 보고 건너뛴다(포털 `infra/scripts/update-all.sh:1602-1621`). OB-25 는 둘째 터널을 정하는 일이다. 둘 다 이 행의 답(운영에 뜬 판 · 닿을 길)을 기다린다.
- 요청서가 'OB-92 에 이 선행 조건이 적혀 있지 않다' 고 짚었다. OB-92 를 cae00 안내(`server-setup.md`, 아직 없다)로 옮길 때 'PA-16 · PA-19 가 끝난 뒤' 를 함께 적어야 한다.
- HP-54(조건부 — C-4)는 OB-92 에서 둘째 길을 고를 때만 연다. 지금은 손대지 않는다([`../checklist.md`](../checklist.md) 3절 '[-]').
- HP-51(고치는 중)은 운영자 정의가 가리키는 앱이 그 박스 게이트웨이에 없음을 update-all 미리보기와 전문가 고르기 화면에 미리 알린다. 잇기 전까지는 he-sim-smarttwin(앱 smart-twin-mcp)이 그 표지를 받는 운영자다(HP-51 근거 DW-12).
- HA-29(고치는 중)는 잡을 시작하는 도구와 운영자 `writes` 를 이번 턴 사람이 시키지 않았으면 확인 카드로 멈춘다. he-sim-smarttwin 의 `writes`(`he-team.json:116`)에 든 낙하 도구도 그 목록이다. 다만 HA-29 의 할 일은 멈춰 묻는 것이고 인자(`extra_scenario_overrides`) 검사는 그 안에 없다 — 사람이 시킨 호출은 지나가므로 잠금(PA-19)을 대신하지 않는다.
- HP-53(고치는 중)이 `writes` · `confirm` 을 채우는 운영자 목록에 he-sim-smarttwin 은 없다(요청서 HP-53 근거).

## 끝나면

### SmartTwinExplorer(세션 `smarttwinexplorer-06`) — PA-20

- 세션 쪽 보고는 끝났다. 커밋 `4f5e0e0`(고침) · `b059413`(체크리스트)을 GitHub 에 올렸고, Drive 스테이징 `SmartTwinExplorer/staging` 번들(4f5e0e0)을 올렸고, 포털 세션 hwaxportal-a5 에 회신했다(outbound.md 답 칸 — 포털 `bf5cd94`). Drive 번들은 세션 답 기준이며 이 박스에서 Drive 를 열어 보지는 않았다.
- cae00 사람 몫 — Drive 번들(4f5e0e0)을 포털 `infra/scripts/deploy-ste.sh` 로 ste 헤드노드에 반영한다. 요청서 머리는 'update-all 로 받는 플랫폼' 에서 클러스터 앱(STE · stcx)을 '아니오' 로 적었고, 실제로 update-all 2c 는 teleport 박스에서 사람 호출(대화형 터미널 · `--with-ste` · `STE_DEPLOY=1`) · 신선도 · Teleport 세션이 다 맞을 때만 돈다(`update-all.sh:1193-1227`). 확실한 길은 Teleport 세션을 연 뒤 `STE_DEPLOY=1 infra/scripts/deploy-ste.sh` 다(update-all §6 힌트, `update-all.sh:2756-2757`). 반영은 ste 의 `deploy/refresh-code.sh` 가 `deploy/deploy-backend.sh` 를 불러 `ste-backend` · `ste-mcp` 를 다시 띄운다.
- 확인 — 세션이 스테이징에서 본 것과 같게, REST `/api/cluster` 와 MCP `cluster_info` 의 `controller` 가 호스트 이름뿐이고 `list_jobs` · `get_job_status` 에 메일 · 사설 IP 가 없는지 본다(남았으면 `[메일]` · `[사설IP]` 로 가려져 있어야 한다).
- 포털 세션 몫 — 이 절차를 `server-setup.md` 로 옮긴다([`../checklist.md`](../checklist.md) 0절 '받은 답을 `outbound.md` · `server-setup.md` 에 옮김').
- 7절 다시 볼 시험 — 'DW-07 · DW-03 · 06 · 12 · 22' 줄(언제 'HG-21 · HG-22 뒤', 볼 것 '숫자가 그대로 나오고, 사람 이름 · 메일 · 사설 IP 가 가려진다.')의 DW-12 가 이 플랫폼 몫이다. PA-20 반영과 HG-22 가 다 들어간 뒤 한 번에 보면 되고, 표지로 원천 · 게이트웨이 가운데 누가 가렸는지 가른다.

### SmartTwinMCP(세션 `smarttwinmcp-4c`) — PA-16 · PA-19(다시)

- hwaxportal-a5 에 보낼 것은 셋이다.
  1. PA-19 — 잠금이 든 리포와 커밋. 이 박스 대조로는 KooSlurm 정본 `05240273` · `b6bb79dc` · `5aa61b67` 이다. SmartTwinMCP 리포만 고쳤다면 :5013 에는 닿지 않는다는 점(그 리포 `CLAUDE.md`)을 함께 적는다.
  2. PA-16 — stcx :5013 이 `5aa61b67` 이 든 판으로 떠 있는지, 아니면 운영 배포 날짜. 운영 배포는 stcx 운영(사람) 일정이고, 순서는 회신 §1(운영 리포 받기 · `install_offline.sh --install-service` · drop-in `STMC_WORK_ROOTS` · `/api/v1/health` 확인)이다.
  3. 언제 뜨는지와 cae00 에서 닿을 길 — OB-34(`SMARTTWIN_MCP_URL`) · OB-25(둘째 터널)는 우리가 정하지만 그 재료는 stcx 쪽에 있다.
- 배포물 — SIF · Drive 판이 아니라 KooSlurm 리포의 코드와 오프라인 휠이다(`dashboard/smarttwin_mcp/deploy/RUNBOOK.md` · 회신 §1). update-all 은 이것을 받지 않는다(요청서 머리).
- 받은 뒤 우리 몫 — 답을 outbound.md 의 답 칸과 `server-setup.md` 에 옮기고, OB-34 · OB-25 를 거쳐 OB-92 첫째 길을 연다.
- 7절에는 이 행의 줄이 없다. 잇기 뒤에는 HP-51 의 다시 볼 시험(3절 DW-12)으로 smart-twin-mcp 가 cae00 게이트웨이에 실렸는지 본다.
