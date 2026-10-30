# 01 HWAX 포털 — 10-30 요청에서 할 일

- **받는 곳** — 이 세션, HWAX 포털 세션 `hwaxportal-a5`. 우리 리포 행이라 다른 세션에 보내지 않는다.
- **어떻게 갔나** — 이 세션이 고친다. 형제 워크트리 가지 `wt1030/ops` · `wt1030/seed` · `wt1030/ua` · `wt1030/vocab` 에서 구현 · 반대 검토 중이고, 조건부 셋(HP-42(다시) · HP-21(다시) · HP-54)은 판단 C-2 · C-3 · C-4([`../context-notes.md`](../context-notes.md)) 대로 조건을 기다린다. 대조 시각에 가지 셋에 커밋이 있었다 — `wt1030/seed` `9801e02`(HP-52) · `wt1030/ua` `961ec16`(HP-55) · `wt1030/vocab` `f780255`(HP-56). `wt1030/ops` 는 갈라진 자리(`ce41b8f`) 그대로라 커밋이 없다. 모두 main 에 합치기 전이다(가지 커밋은 본 리포에서 `git show` 로 머리글 · 고친 파일 목록 · 일부 변경분만 읽었고, 작업 트리는 보지 않았다).
- **요청서 정본** — [`../../request_261030.md`](../../request_261030.md) 3절 '포털'(HP-51)과 끝 절 '이전 회차에서 남은 챗 · 디지털 워커 요청' 의 '포털' 표(HP-52 · HP-53 · HP-54 · HP-55 · HP-56 · HP-42(다시) · HP-21(다시)). 맞물린 우리 몫은 5절(OB-26 · OB-89 · OB-92 · OB-93), 다시 볼 시험은 7절이다. 같은 요청의 계획 · 판단 · 체크리스트 · 보낸 것은 [`../PLAN.md`](../PLAN.md) · [`../context-notes.md`](../context-notes.md) · [`../checklist.md`](../checklist.md) · [`../outbound.md`](../outbound.md) 다.
- **cae00 기준 판** — 포털 `aec8e29`(요청서의 포털 줄 번호가 이 판의 것이다). 다른 리포를 가리키는 근거는 에이전트 서버 `969e723` · 게이트웨이 `44f4b8d` · KooRemapper `46e4283` 판이다.
- **이 박스(dev)에서 대조한 판** — 포털 main `bf5cd94`(`aec8e29` 가 조상이고 그 뒤 42커밋) · 에이전트 서버 `7ca3a2e` · 게이트웨이 `67d8d00` · KooRemapper `e0451ad` · AIDataHub `ac42bc6` · StepForge `ff308d1` · HWAXRisk `ecad8c8`. 대조 시각 2026-10-30 18:04 KST. 줄 번호가 옮겨진 곳은 함수 · 상수 이름으로 다시 찾았다(판단 C-6).

## 할 일

### HP-51 · 중간 — 운영자 앱이 이 게이트웨이에 없다는 것을 미리 보이기

- **무엇이** — 운영자 정의가 가리키는 앱이 그 박스 게이트웨이에 없는지 미리 알 길이 없다.
- **근거** — DW-12 — he-sim-smarttwin 의 앱(smart-twin-mcp · smart-twin-cluster)이 cae00 게이트웨이에 없다. 챗을 보낸 뒤에야 화면 주의가 뜬다.
- **할 일** — update-all 의 운영자 페르소나 미리보기(`infra/scripts/sync-he-personas.py` — `update-all.sh:1176`)나 '새 앱 점검'(`infra/scripts/app-checks.py` — `:3150`)에 '운영자 앱이 이 게이트웨이에 없다' 줄을 더한다. 전문가 고르기 화면에도 그 운영자에 작은 표지를 단다.
- **다시 볼 시험** — DW-12.

#### 지금 판에서의 자리

포털 main `bf5cd94` 기준이다. 이 행에 닿은 커밋은 main 에 아직 없다.

- **`update-all.sh:1176` — 그대로다.** 기준 판 뒤 이 파일을 바꾼 커밋은 `5969dcb` 하나이고, 기준 판 3500줄 뒤에 17줄을 더했을 뿐이라(`git diff -U0 aec8e29 HEAD` 의 고친 덩이 `@@ -3500,0 +3501,17 @@` 하나) 이 줄은 옮겨지지 않았다. 미리보기는 로그 머리 '3) AIDataHub 데이터(에이전트·레코드) 동기화'(`:1128`)의 AIDH merge 뒤에 돌고(`:1175-1187`), 덤프가 지난번과 같아 'merge 생략' 인 실행(`:1157-1158`)에서는 돌지 않는다.
- **`infra/scripts/sync-he-personas.py` — 기준 판 뒤 커밋 0.** 앱이 없는 운영자는 이미 `· 건너뜀 <키>: 이 게이트웨이에 앱이 없다(…) — 붙어 있는 박스에서 돌리면 생긴다` 줄(앞에 빈칸 둘)로 찍는다(`:132-135` · `:189-190`). 그러나 update-all 은 미리보기 출력에서 `+` · `~` 줄(`update-all.sh:1177`)과 `✗` 줄(`:1180`)만 골라 보이므로 이 줄은 update-all 로그에 나오지 않는다. 선택 앱을 빼고 만든 '· 일부' 줄(`:191-192`)도 같다.
- **`infra/scripts/app-checks.py` — 기준 판 뒤 커밋 0.** 요청서의 `:3150` 은 '새 앱 점검' 절의 머리 주석이고 부르는 줄은 `:3157` 이다(기준 판도 같다, 로그 머리 '6) 헬스게이트' `:2463` 안). 이 스크립트는 게이트웨이 `/tools-map` · 포털 권한 정책 · 기록 파일만 받고 운영자 정의는 읽지 않는다(`he-team` · `persona` 0건).
- **화면 — 표지를 달 값이 목록에 없다.** 챗을 보낸 뒤의 주의는 에이전트 서버가 턴 중에 내는 SSE `warning` `operator_app_missing` 이다(기준 `969e723` `app.py:4902` → 이 박스 `7ca3a2e` `:5004`). 고르기 목록의 카드(`frontend/src/components/chat/PersonaBrowser.tsx:14` `AgentCard`)가 받는 `PoolExpert` 는 key · name · tags 뿐이다(`frontend/src/api/chat.api.ts:146-150` — 기준 판 `:141-145`, `e3d0a48` 이 줄만 옮겼다). 앱이 붙었는지는 누른 뒤 받는 `AgentDetail.apps[].connected`(`chat.api.ts:375-377`)에만 있고, 상세 칸의 `OperatorApps`(`frontend/src/components/chat/AgentFacts.tsx:32`)가 '이 서버에 연결 안 됨'(`:46`)으로 보인다(쓰는 곳 `PersonaBrowser.tsx:265` · `SeatBrowser.tsx:202` · `AgentDeepView.tsx:277`).

#### 우리 쪽 맞물림

- **이 세션이 형제 워크트리에서 고치는 중이다.** 대조 시각에 이 행의 가지 커밋은 보이지 않았다(`wt1030/ops` 는 커밋 0, `wt1030/ua` 의 `961ec16` 은 HP-55 다). 어느 가지가 맡는지는 대조 못 함.
- **OB-92(5절 — 사람)** — SmartTwin MCP 를 cae00 게이트웨이에 잇거나 he-sim-smarttwin 정의를 연결된 클러스터 앱으로 바꾼다. 이 행은 그 어긋남을 챗 전에 보이게 하는 몫이고, 정의를 바꾸는 둘째 길의 정본 고침은 HP-54 다. 잇는 길은 끝 절 PA-16 · PA-19(다시)가 먼저다(`smarttwinmcp-4c` 에 보냄 — 답 기다림, `outbound.md` 1절).
- **HG-22(게이트웨이 — 고치는 중)** — 같은 DW-12 의 클러스터 잡 제출자 메일 · 컨트롤러 사설 IP 가림이다. 7절은 DW-12 를 HG-21 · HG-22 뒤에 다시 본다.

### HP-52 · 중간 — 씨앗 둘이 find_reports 봉투의 items 에서 고르게

- **무엇이** — (중간) 씨앗 절차 둘이 KooRemapper `find_reports` 의 봉투 응답을 목록으로 읽어, 첫 단계에서 `select:no_field` 로 멈춘다. 0건이어도 `on_none` 이 아니라 같은 오류다.
- **근거** — `docs/procedures/fixtures/fullangle-drop-part-report.yaml:40` · `docs/procedures/fixtures/partial-impact-part-report.yaml:43`(`select: {from: "$", …}`). 실행기는 객체 하나를 `[객체]` 로 감싸고(`backend/app/procedures/runner.py:518-521`), 그 객체에 `id` 칸이 없어 `:538-543` 에서 멈춘다. KooRemapper `46e4283` `platform/mcp_server/server.py:1224-1228` 은 `{items, total, reason, truncated}` 를 돌려준다.
- **할 일** — 두 씨앗의 `select` 를 `from: items` 로 고친다(0건이면 `on_none` 이 걸린다). 이미 들인 사용자는 씨앗을 다시 들이면 판본이 오른다(`backend/app/procedures/routes.py:347-359` import_seed). 아니면 실행기가 `items` 배열 하나뿐인 봉투를 목록으로 풀어 준다.
- **출처** — TODO-20261029 R-05 · reflection-1028/04 3절 ① · reflection-1028/00-SUMMARY 4절

#### 지금 판에서의 자리

- **씨앗 두 줄 — 그대로다.** `docs/procedures/fixtures/fullangle-drop-part-report.yaml:40` · `docs/procedures/fixtures/partial-impact-part-report.yaml:43` 이 지금도 `select: {from: "$", …}` 다(두 파일 모두 기준 판 뒤 커밋 0).
- **실행기 — 줄만 두 줄 옮겼다.** `backend/app/procedures/runner.py:518-521` → `:520-523`(`cand = template.extract(v.parsed, sel.from_)` 와 객체 하나를 `[cand]` 로 감싸는 줄), `:538-543` → `:540-545`(`stage="select:no_field"`). 둘 다 `_pick`(`:511`) 안이다. 기준 판 뒤 이 파일 커밋은 `b7c0166`(절차 W-102 — 위쪽 `:192` 에 두 줄을 더함) 하나이고 이 자리의 글은 같다.
- **`backend/app/procedures/routes.py:347-359` — 그대로다**(기준 판 뒤 커밋 0). `import_seed` 는 `:347-365` 이고, 이미 들인 씨앗이면 `add_version` 으로 판본을 올린다(`:358-361`).
- **KooRemapper 봉투 — 꼴은 같고 줄만 옮겼다.** 이 박스 KooRemapper `e0451ad`(기준 `46e4283` 이 조상)에서 `{items, total, reason, truncated}` 를 돌려주는 줄은 `platform/mcp_server/server.py:1286-1290` 이다. `find_reports` 함수 본문은 기준 판과 글자까지 같다(그 뒤 이 파일 커밋 `85ba2f0` · `aa63e2a` 는 다른 도구다).

#### 우리 쪽 맞물림

- **가지 `wt1030/seed` 에서 고치는 중이다.** 가지 커밋 `9801e02`(main 에 합치기 · 반대 검토 전)의 머리글로는 첫째 길을 골랐다. 두 씨앗의 `select` 를 `from: items` 로 바꾸고, 실행기는 봉투를 몰래 벗기지 않는다. 옛 판본(`from: "$"` 인데 결과가 `items` 목록을 가진 객체)이면 `select:no_field` 오류에 '`from: items` 로 고친다 · 정본 예제에서 다시 받는다' 안내를 붙인다. 시험 고정물도 진짜 봉투 꼴로 바꿨다.
- **KooRemapper(`kooremapper-4a`)** — 'HP-52 가 find_reports 의 `items` 를 읽는다' 를 덧붙여 보냈다(답 기다림, `outbound.md` 1절). 봉투 칸 이름이 바뀌면 고친 씨앗이 다시 멈춘다.

### HP-53 · 중간 — 운영자 writes · confirm 채우기

- **무엇이** — (중간) 운영자 정의의 `writes` · `confirm` 이 비었거나 모자라다. 그래서 '요청했을 때만 부른다' · '확인을 받은 뒤 부른다' 안내가 여러 잡 · 쓰기 도구에 붙지 않고, HA-29 의 코드 관문이 읽을 목록도 빈다.
- **근거** — `infra/personas/he-team.json:84-87`(he-cad-odbhub — todo 그대로, key_tools · writes · confirm 빈칸) · `:402-405`(he-data-arp 같음) · `:449-450`(he-data-coreontology writes · confirm 빈칸) · `:825`(he-expert-risk writes 빈칸) · `:51`(he-cad-stepforge writes 에 run_recipe · save_recipe · set_revision · set_admin 없음) · `:166`(he-sim-dynaforge writes 에 recipe_* 없음). `infra/scripts/sync-he-personas.py:71-77` 이 두 목록을 프롬프트의 두 줄로 만든다. DW-03 은 run_job 이 writes 에 있는데도 확인 없이 걸었으니, 근본 고침은 HA-29 이고 이 행은 그 관문이 읽을 목록을 채우는 짝이다.
- **할 일** — 10-30 cae00 `/tools-map` 과 대조한 목록 밖 도구를 각 운영자의 `writes`(잡 · 쓰기)와 `confirm`(지우기 · 권한 · 되돌리기 어려운 것)에 넣는다 — ODB run_checklist · run_analysis · run_compare · run_curvature · create_modified_odb · import_modified_odb, ARP arp_upload_create · arp_upload_stage · arp_upload_register · arp_upload_discard, 코어 허브 object_create · object_update · objects_delete · object_merge · datasource_sync · bundle_import · job_apply, 리스크 앱 risk_start_job · risk_create_project · risk_create_diff, StepForge run_recipe · save_recipe · set_revision · set_admin(confirm), DynaForge recipe_propose · recipe_register · recipe_run(KR-23). ODB · ARP 운영자는 todo · key_tools 도 채운다. ARP 운영자 함정에 '낙하 높이 칸은 단위가 없다 — 시험 조건은 cm' 한 줄을 넣는다(AR-9 전까지). `sync-he-personas.py` 미리보기(`:147-153` 검사 옆)는 운영자 앱의 쓰기 꼴 도구 가운데 두 목록에 없는 것을 알린다. ODB 몫은 OB-26 이 '둔다' 일 때다.
- **출처** — QA-DIGITAL-WORKER-20261030 DW-03 · DW-02 후속 · 이 요청서 HA-29 · TODO-20261029 R-09 · 90-OURS OB-26

#### 지금 판에서의 자리

- **`infra/personas/he-team.json` — 인용 줄이 모두 그대로다**(기준 판 뒤 커밋 0). `:84-87` he-cad-odbhub(todo 한 줄, key_tools · writes · confirm 모두 `[]`), `:402-405` he-data-arp(같음 — 함정은 `:398-400` 의 한 줄뿐이고 낙하 높이 단위 줄은 없다), `:449-450` he-data-coreontology(writes · confirm `[]`), `:825` he-expert-risk(writes `[]` — confirm 은 `:826` 에 risk_submit_panel_result · risk_add_finding 이 있다), `:51` he-cad-stepforge(run_job 은 있고 run_recipe · save_recipe · set_revision · set_admin 은 없다), `:166` he-sim-dynaforge(recipe_* 없음).
- **`infra/scripts/sync-he-personas.py:71-77` · `:147-153` — 그대로다**(기준 판 뒤 커밋 0).
- **목록이 가는 길.** 동기화가 AIDataHub 에 싣는 구조 칸은 `response_config` 의 persona_kind · mcp_apps · key_tools · managed_by 뿐이고(`:169-171`), writes · confirm 은 system_prompt 의 두 줄(`:71-77`)로만 간다. 에이전트 서버 `7ca3a2e` `app.py` 에 `writes` 를 읽는 곳은 0건이다.
- **이름 검사와 멈춤.** `:147-150` 은 그 박스 게이트웨이가 받는 이름(노출 이름 · 접두 별칭 — `:145-146`)만 통과시키고, 오류가 하나라도 있으면 아무 운영자도 올리지 않고 끝난다(`:193-196`). 앱이 없는 운영자는 검사 전에 건너뛰므로(`:132-135`) arp · odb-hub 가 붙지 않은 박스(머리말 `:16` — dev)에서는 ODB · ARP 도구 이름이 cae00 에서야 검사된다.
- **저장 실패에서 멈춤.** 만들기 · 고치기가 2xx 가 아니면 그 자리에서 끝난다(`:214-217` · `:229-232`). AD-21 의 '저장 뒤 500' 이 첫 건에서 멈추게 하는 자리다. update-all 은 미리보기만 하고(`update-all.sh:1175-1187`) `--apply` 는 사람이 한다.
- **더할 도구 이름 — 이 박스 원천에 있다.** StepForge `ff308d1` `app/mcp_server.py` — run_recipe `:32568` · save_recipe `:32453` · set_revision `:31468` · set_admin `:31737`. KooRemapper `e0451ad` `platform/mcp_server/server.py` — recipe_run `:1632` · recipe_propose `:1662` · recipe_register `:1686`. HWAXRisk `ecad8c8` `backend/app/mcp_server.py` — risk_create_project `:597` · risk_create_diff `:659` · risk_start_job `:676`. ODB · ARP · 코어 허브는 이 박스에 리포가 없어 대조 못 함. 요청서가 대조한 10-30 cae00 `/tools-map` 도 이 박스에서 볼 수 없어 대조 못 함.
- **'쓰기 꼴 도구' 알림이 기댈 칸.** 게이트웨이 `/tools-map` 의 `write`(쓰기로 가른 노출 이름 목록)는 `67d8d00` 에서 생겼다(`gateway.py:6472`, origin/master 에 있다). cae00 기준 판 `44f4b8d` 에는 0건이라, cae00 이 그 뒤 게이트웨이를 받기 전에는 이 칸이 없다.

#### 우리 쪽 맞물림

- **가지 `wt1030/ops` 에서 고치는 중이다**(대조 시각 커밋 0). 판단 C-5 대로 ODB 의 writes · confirm 은 지금 채우고, todo · key_tools 는 OB-26(ODB 운영자를 둘지 — 사람 결정) 뒤에 쓴다.
- **HA-29(에이전트 — 고치는 중)** — 잡 시작 · 쓰기 도구를 이번 턴 사람 발화가 시키지 않았으면 코드 단에서 확인 카드로 멈춘다. 그 관문이 읽는 목록을 이 행이 채운다. 관문이 목록을 어디서 읽는지(운영자 글 · 구조 칸 · 정본 파일)는 이 박스 main 에 아직 없어 대조 못 함.
- **AD-21(AIDataHub — 저장 뒤 500)** — 이 행이 타는 동기화(`--apply`)를 첫 건에서 멈춘다. 판단 C-7 로 AD-21 코드도 이 세션이 맡아 고치는 중이다(AIDataHub 가지 `wt1030/ad-agents` — 대조 시각 커밋 0). 포털 동기화는 저장 여부를 다시 읽어(GET) 확인하고 이어 가게 고치는 중이다(`outbound.md` 2절 3 — 작으면 HP-53 묶음).
- **KR-23(KooRemapper — 답 기다림)** — 레시피 등록을 사람 승인으로 묶을지는 KooRemapper 의 답이다. 그와 별개로 이 행이 DynaForge 운영자 writes 에 recipe_* 를 넣어 HA-29 카드에 걸리게 한다(KR-23 의 '포털 몫은 HP-53').
- **AR-9(ARP — 사람이 보냄)** — 낙하 높이 단위가 원천에서 고쳐질 때까지 이 행의 ARP 함정 줄이 메운다(`outbound.md` 2절).
- **판단 C-8** — 같은 동기화를 타는 DocForge 운영자 고침 셋은 DocForge 0.3.1 이 cae00 게이트웨이에 실린 뒤에 커밋한다. 게이트웨이에 없는 도구 이름이 하나라도 있으면 동기화가 통째로 멈추므로, 이 행이 더하는 이름도 cae00 게이트웨이에 실린 것이어야 한다.

### HP-54 · 낮음 · 조건부 — SmartTwin 운영자에 ste 선택 몫

- **무엇이** — (낮음 · 조건부) SmartTwin 운영자 정본에 이 박스에 붙은 클러스터 앱(ste)이 없다. OB-92 에서 '정의를 바꾸는' 길을 고르면, 박스 손질은 다음 git 받기 · 병합에 사라진다.
- **근거** — `infra/personas/he-team.json:94-127`(he-sim-smarttwin — apps 는 smart-twin-mcp, 선택 몫은 smart-twin-cluster 뿐) · `infra/scripts/sync-he-personas.py:133-135`(앱이 없으면 건너뛴다). 10-30 `/tools-map` 의 ste 도구(cluster_info · submit_job · set_job_sync · ste_cancel_job 등)를 묶는 운영자가 0명이다.
- **할 일** — OB-92 에서 둘째 길을 고르면 두 가지를 청한다. he-sim-smarttwin 에 ste 선택 몫(cluster_info 는 조회, submit_job · set_job_sync 는 writes, ste_cancel_job 은 confirm)을 둔다. 기본 앱이 없어도 선택 앱만으로 운영자를 만드는 규칙을 둔다.
- **출처** — QA-DIGITAL-WORKER-20261030 DW-12 · 이 요청서 OB-92

#### 지금 판에서의 자리

- **`infra/personas/he-team.json:94-127` — 그대로다**(기준 판 뒤 커밋 0). he-sim-smarttwin 의 apps 는 `smart-twin-mcp`(`:95`) 하나이고, 선택 몫은 `smart-twin-cluster`(`:118-128`) 하나다. 이 파일에 `ste` 앱 · cluster_info · set_job_sync · ste_cancel_job 은 0건이다.
- **`infra/scripts/sync-he-personas.py:133-135` — 그대로다**(기준 판 뒤 커밋 0). 기본 앱이 하나라도 없으면 선택 몫을 보기 전에 건너뛴다(`_with_optional` 은 `:136` 에서야 부른다). 선택 앱만으로 운영자를 만드는 규칙은 지금 없다.
- he-sim-smarttwin writes(`:116`)의 낙하 제출 도구(fullangle_drop_simulation · single_drop_simulation)는 끝 절 PA-16 · PA-19(다시)가 짚은 자리다.
- 10-30 cae00 `/tools-map` 의 ste 도구 목록은 이 박스에서 볼 수 없어 대조 못 함.

#### 우리 쪽 맞물림

- **지금 고치는 곳은 없다.** 판단 C-4 — OB-92 에서 사람이 둘째 길(정의를 바꾸는 길)을 고르기 전에는 넣지 않는다.
- **OB-92 의 첫째 길(잇기)** 은 PA-16 · PA-19(다시)가 끝난 뒤다(5절 OB-34 · OB-25, `smarttwinmcp-4c` 에 보냄 — 답 기다림). 어느 길이든 HP-51(고치는 중)의 미리보기 줄 · 고르기 표지가 그 어긋남을 챗 전에 보인다.
- **PA-20 · HG-22** — ste 의 cluster_info 를 이 운영자에 묶으면 그 출력의 가림이 함께 걸린다. PA-20 은 SmartTwinExplorer 가 10-30 끝냈다고 답했다(`4f5e0e0`, cae00 반영은 사람 몫 — `outbound.md` 1절). 게이트웨이 HG-22 는 고치는 중이다.

### HP-55 · 낮음 — update-all 의 챗 도구 문구

- **무엇이** — (낮음) update-all 의 챗 도구 문구가 cae00 실제와 다르다. §1 은 TOOL_MAX=0 인 박스에 '미설정 → 기본 200' 이라 적고, §7 은 '챗 창의 45% 안이면 전부 바인딩' 이라 적는다. OB-93 예산 견주기 때 틀린 말이 된다.
- **근거** — `infra/scripts/update-all.sh:1385-1386`(TOOL_MAX 가 0 이어도 '미설정 → 기본 200') · `:3461-3462`('대형 컨텍스트 GLM 이라 전부 실림') · `:3474`('챗 창의 45% 안이면 전부 바인딩') · `:3480-3481`('챗 창의 45%' 고정 · '챗 서버 창을 넓힌다'). 10-29 update-all 로그가 이 문구를 냈다. 10-30 에이전트 `/health` 는 tool_max 0 · tool_cut 1,379 → 209(budget 88,473)다. 에이전트 `969e723` `app.py:2296` 은 `CHAT_TOOL_SCHEMA_BUDGET` 이 있으면 그 값을 예산으로 쓴다.
- **할 일** — §1 은 박스 값이 0 이면 'TOOL_MAX=0 그대로(무캡)' 로 적는다. §7 챗 도구 줄은 `/health` tool_cut 의 budget 값과 그 출처(`CHAT_TOOL_SCHEMA_BUDGET` 이면 그 값, 없으면 창의 45%)로 바꾸고, '전부 바인딩' 과 GLM 권고 문구를 걷는다.
- **출처** — 01-HWAXPortal HP-07 남은 문구 · 포털 `docs/request-1029` W-2 · 이 요청서 OB-93

#### 지금 판에서의 자리

- **인용 줄 넷이 모두 그대로다** — `infra/scripts/update-all.sh:1385-1386` · `:3461-3462` · `:3474` · `:3480-3481`. 이 파일의 기준 판 뒤 변경은 `5969dcb` 의 3500줄 뒤 17줄뿐이다.
- **'§1' 의 자리.** `:1385-1386` 은 로그 머리 '3.5) agent-server .env 보정'(`:1262`) 안이다. 요청서의 '§1' 은 절 번호와 맞지 않으나 줄 번호로 자리는 분명하다. 이 줄은 원격 LLM 갈래(`:1375`)가 아닐 때만 닿는다. 원격 갈래는 박스 값이 있으면 이미 'TOOL_MAX=$TM 그대로(박스 값 …)'(`:1380`)라 적는다. 그러니 10-29 cae00 로그의 '미설정 → 기본 200' 은 그 실행이 LLM 주소를 로컬로 읽었다는 뜻이다. 왜 로컬로 읽었는지는 이 박스에서 대조 못 함.
- **§7 의 자리.** `:3461-3485` 는 로그 머리 '7) 챗 스모크'(`:3425`) 안이다.
- **에이전트 쪽.** `969e723` `app.py:2296` → 이 박스 `7ca3a2e` `:2390` 이고 식은 같다(`CHAT_TOOL_SCHEMA_BUDGET` 이 0 보다 크면 그 값, 아니면 `max(4000, 창 × 0.45)`, 정의 `:2115`). `/health` 의 `tool_cut` 은 잘렸을 때만 채워지고(`_fit_schema`(`:2305`)의 `:2320-2327`) 칸은 at · before · after · budget · est_tokens · dropped_apps 다. 예산의 출처 칸은 없다.

#### 우리 쪽 맞물림

- **가지 `wt1030/ua` 에서 고치는 중이다.** 가지 커밋 `961ec16`(main 에 합치기 · 반대 검토 전)의 머리글은 '§1 은 박스 값 0 을 TOOL_MAX=0 그대로(무캡)로 — 로컬로 읽힌 박스가 맨 끝 가지로 떨어져 …' 로 시작한다. 고친 파일은 `infra/scripts/update-all.sh` 와 시험 둘(`backend/tests/test_update_all_tool_cut.py` · `backend/tests/test_llm_pool_update_all.py`)이다.
- **OB-93(5절 — 사람)** — `CHAT_TOOL_SCHEMA_BUDGET` 40000 → 30000 견주기가 이 문구를 읽는다. 요청서대로, 고치기 전 문구는 그때 틀린 말이 된다.

### HP-56 · 낮음 · 선택 — '전작' · '후속' 을 코어 규칙 발동 낱말에

- **무엇이** — (낮음 · 선택) '전작' · '후속' 이 어휘표 `search` 에는 있는데 코어 규칙 발동 낱말(`rule_words`)에는 없다.
- **근거** — `backend/config/core_vocab.json:9-12`(rule_words 15개에 없다) · `:23`(search 에는 있다). 10-30 OT-05 는 그래도 코어로 갔다.
- **할 일** — rule_words 에 둘을 더할지 본다. 심의 낱말을 가로채지 않는지 게이트웨이 검색 평가와 함께 본다.
- **출처** — QA-CHAT-QWEN-20261030 5.2 #4

#### 지금 판에서의 자리

- **`backend/config/core_vocab.json:9-12` · `:23` — 그대로다**(기준 판 뒤 커밋 0). rule_words 는 15개이고, '전작' · '후속' 은 `search` 의 둘째 묶음(`:22-25`, 도구 graph_neighbors)에만 있다.
- **읽는 곳.** rule_words 는 에이전트 서버의 코어 규칙 글(`_core_rules_text`, `7ca3a2e` `app.py:286` — 낱말 줄 `:295`)과 `/health` 의 낱말 수(`:324`)가 쓴다. 게이트웨이는 `search` 낱말 · 정본 · 앱 역할만 읽는다(`67d8d00` `gateway.py:3075-3087` `_core_vocab_parse`). 두 서비스 모두 파일의 바뀐 시각을 보고 다시 읽으므로(게이트웨이 `_core_vocab` `:3090`, 에이전트 `_core_vocab` `:309`) 재기동이 필요 없다.
- **박스 덧씌우기.** `core_vocab.local.json` 은 merge patch 라 목록을 통째로 바꾼다(`gateway.py:2959-2969` `_merge_patch`). cae00 의 덧씌우기가 rule_words 를 적었다면 정본에 더한 낱말은 그 박스에 닿지 않는다. cae00 파일이라 대조 못 함.
- 포털 시험 `backend/tests/test_core_vocab.py:49` 가 '메커니즘' 이 검색 낱말이 되지 않게 지킨다(심의 '메커니즘 규명' 가로채기 — R-5).

#### 우리 쪽 맞물림

- **가지 `wt1030/vocab` 에서 HA-32 와 함께 고치는 중이다.** 포털 가지 커밋 `f780255`(main 에 합치기 · 반대 검토 전)의 머리글로는 '전작' 과 '후속 모델' 을 더하고 맨 '후속' 은 넣지 않는다. '후속 심의' 같은 심의 · 일반 말을 규칙이 가로채기 때문이라고 적었고, 게이트웨이는 rule_words 를 읽지 않아 검색 순위가 글자까지 같다(평가셋 150쌍 · cae00 꼴 탐침 15개)고 적었다.
- **HA-32(에이전트 — 고치는 중)** — 같은 파일에 낱말 → 타입 이름 대응 칸 `types` 를 더해 코어 규칙 ① 끝 한 줄로 싣는다. 에이전트 가지 `wt1030/vocab` 의 커밋 `ac2aec0`(합치기 전) 머리글로는 칸이 없으면 규칙 글이 종전과 같다. 포털 쪽 `types` 칸은 대조 시각의 포털 가지 커밋(`f780255`)에 아직 없다.
- **update-all §7** 이 게이트웨이 · 에이전트의 어휘표 지문을 견준다(`update-all.sh:3510-3517`, `5969dcb`). 두 행이 들어간 뒤 cae00 에서 두 지문이 같은지가 반영 확인이다.

### HP-42(다시) · 낮음 · 조건부 — 웹 챗의 MCP Apps 패널 호스트

- **무엇이** — (낮음 · 조건부) 포털 웹 챗에 MCP Apps 패널 호스트가 없어, 파일이 끼는 워크플로우는 웹으로 돌아가야 한다. 에이전트 HA-20(2단계)이 먼저다.
- **근거** — 에이전트 `969e723` `app.py` 와 포털 `backend/app` · `frontend/src` 에 `ui_resource` 가 0건이다(HA-20 미반영). 게이트웨이 중계(HG-07)는 들어왔다(`44f4b8d` `gateway.py:4821` `_ui_meta`).
- **할 일** — 2단계로 남긴다. 에이전트 HA-20(ui_resource SSE)이 들어오면 포털 패널 호스트를 다시 청한다. 지금은 답이 필요 없다.
- **출처** — 01-HWAXPortal HP-42 · reflection-1028/01 보류 · 개발 checklist(request-1027) '[~] HP-42'

#### 지금 판에서의 자리

- 포털 `bf5cd94` 의 `backend/app` · `frontend/src` 에 `ui_resource` 0건이다(기준 판 `aec8e29` 도 0건).
- 에이전트 서버 `7ca3a2e` 의 파이썬 파일 전체에 `ui_resource` 0건이다(기준 `969e723` `app.py` 도 0건).
- 게이트웨이 `_ui_meta` 는 그대로 있다 — 기준 `44f4b8d` `gateway.py:4821` → 이 박스 `67d8d00` `:5856`.

#### 우리 쪽 맞물림

- **지금 고치는 곳은 없다.** 판단 C-2 — 손대지 않는다. 먼저인 에이전트 HA-20(10-27 회차 행)은 이번 회차 에이전트 행 목록(`PLAN.md`)에 없다.

### HP-21(다시) · 낮음 · 조건부 — 카드 본문 검색을 켰을 때의 검색칸 문구

- **무엇이** — (낮음 · 조건부) 전문가 카드 본문 검색 스위치를 켜도 검색칸 문구가 '제목·요약에서 낱말로 찾기' 그대로다. 스위치(OB-89)가 꺼진 지금은 문구가 맞다.
- **근거** — `frontend/src/components/chat/AgentDeepView.tsx:323`. 개발 checklist(request-1027)는 '[~] 화면이 AIDataHub 스위치를 볼 길이 없다' 이다.
- **할 일** — 본문 검색을 켤 때(AD-04(다시) · OB-89) AIDataHub 응답에 스위치 상태를 싣게 하고, 포털 문구를 그 칸에 맞춘다.
- **출처** — 01-HWAXPortal HP-21 · 90-OURS OB-89

#### 지금 판에서의 자리

- **`frontend/src/components/chat/AgentDeepView.tsx:323` — 그대로다**(기준 판 뒤 커밋 0). placeholder 가 '제목·요약에서 낱말로 찾기' 다.
- **AIDataHub `ac42bc6`**(이 박스 HEAD 가 cae00 기준과 같다) — 스위치는 `api_server/src/api/config.py:42` `aidh_records_q_body_search`(기본 `False`, 설명 `:37-41`)다. 스위치 상태를 응답 칸으로 싣는 곳은 찾지 못했다. grep 에 걸린 것은 설명 글 두 곳, REST `q` 인자 설명(`api_server/src/api/routes/records.py:111`)과 MCP 도구 설명(`api_server/src/api/mcp_runtime.py:934`)뿐이다.

#### 우리 쪽 맞물림

- **지금 고치는 곳은 없다.** 판단 C-3 — AIDataHub 응답에 스위치 상태 칸이 생긴 뒤에 고친다. 그 칸은 `outbound.md` 2절 1 로 AD-04(다시)에 덧붙여 청하기로 했고, 판단 C-7 의 '맡는 것'(이 세션이 맡은 AIDataHub 코드 행)에는 들어 있지 않다. AD-04(다시)의 속도 측정은 데이터 단계라 사용자 OK 뒤다(C-7).

## 끝나면

포털 행은 이 세션 몫이라 보고는 형제 워크트리에서 포털 세션 `hwaxportal-a5` 로 모인다.

1. **보고** — 가지마다 커밋 번호 · 돌린 시험 파일 · 남긴 것을 `hwaxportal-a5` 에 알린다. 이 세션이 가지를 main 에 합치고, 리포 전체 회귀(백엔드 · 프론트 tsc · lint · build — 한 번에 하나)와 반대 검토 · 변이 시험을 거쳐 push 한다(`PLAN.md` 4 ~ 6 · `checklist.md` 4절).
2. **배포물** — 포털 코드는 git 으로 간다(cae00 update-all 의 git 받기). 화면을 고친 행(HP-51 의 고르기 표지)이 있으면 dev 에서 `cd frontend && pnpm build` 뒤 Drive 에 올린다. HP-56 · HA-32 의 어휘표는 게이트웨이 · 에이전트가 바뀐 시각을 보고 다시 읽어 재기동이 없다.
3. **기록** — `checklist.md` 3절 체크 · 업데이트 이력(KST) · `server-setup.md`(cae00 사람 몫) · CLAUDE.md 문서 표 · cae00 배포 가이드.
4. **cae00 사람 몫(`server-setup.md` 에 옮길 것)**
   - HP-53 — update-all 은 운영자 미리보기만 한다. 받은 뒤 `python3 infra/scripts/sync-he-personas.py` 로 미리 보고 `--apply` 로 올린다. AD-21 이 cae00 에 들어가기 전이면 첫 건에서 멈출 수 있으니, 포털 쪽 다시 읽기 확인(고치는 중)이 든 판인지 먼저 본다.
   - HP-52 — 두 씨앗을 이미 들인 사용자는 씨앗을 다시 들여 판본을 올린다. 누가 들였는지는 이 박스에서 대조 못 함.
   - HP-55 — 다음 update-all 로그의 3.5) TOOL_MAX 줄과 7) 챗 도구 줄을 OB-93 견주기 전에 본다.
   - HP-56 — 7) 의 '코어 어휘표 지문' 줄이 게이트웨이 · 에이전트 같은지, cae00 `core_vocab.local.json` 이 rule_words 를 덮는지 본다.
   - HP-51 — OB-92 가 정해지기 전이라면, 다음 update-all 에서 he-sim-smarttwin 이 '운영자 앱이 이 게이트웨이에 없다' 로 찍히는지 본다.
5. **7절 다시 볼 시험 가운데 포털 몫** — 7절에 포털 행 이름으로 걸린 줄은 없다. 맞물리는 둘은 아래다.
   - DW-12 — HP-51 의 다시 볼 시험(3절 표)이다. 7절에서는 'DW-07 · DW-03 · 06 · 12 · 22 — HG-21 · HG-22 뒤' 줄에 들어 있으니, 같은 재시험에서 고르기 표지 · 미리보기 줄도 본다.
   - DW-02 후속 · DW-03(후속 포함) — 'HA-28 · HA-29 뒤' 줄이다. 확인 카드 관문이 HP-53 의 목록을 읽으므로 HP-53 이 cae00 에 반영된 뒤에 본다.
6. **조건부 셋** — HP-54 는 OB-92 결정, HP-21(다시)는 AIDataHub 스위치 칸 · AD-04(다시) · OB-89, HP-42(다시)는 에이전트 HA-20 이 들어오면 다시 연다.
