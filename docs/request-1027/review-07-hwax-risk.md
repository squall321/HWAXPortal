# 07-hwax-risk 요청 검토 — HWAXRisk 코드 대조

검토 2026-10-27 · 기준 HWAXRisk `main` HEAD `ecad8c8`(10-21) · 파일은 읽기만 했다(시험 · 빌드 · 서비스 호출 · 상태를 바꾸는 git 명령은 쓰지 않았다).

## 0. 총평

**대조 기준.** dev 리포 `/home/koopark/claude/HWAXRisk` 의 HEAD 가 `ecad8c8` 이다. 허브가 받아 둔 사본(`HEAXHub/var/integration_workspaces/hwax-risk/upstream`)도 같은 `ecad8c8` 이라 요청서가 말한 cae00 작업 사본과 같은 판이다. `c3f46ba` 는 HEAD 보다 402커밋 앞선 조상이고 커밋 날짜는 10-11 이다(요청서의 10-14 는 SIF 빌드 날짜로 보인다). 요청서 8절의 커밋 아홉(`491895c` · `5d47690` · `0e65f3a` · `9ee4776` · `2c551b5` · `0966b41` · `8d672c7` · `158f89e` · `cdc5dbd`)은 모두 HEAD 에 들어 있다.

| # | 판정 | 몫 | 크기 |
|---|---|---|---|
| RK-01 | RA 로 아무것도 나가지 않는 것은 사실이다. 그러나 까닭과 처방이 틀렸고 사용자 결정이 필요하다 | 사용자 결정 → 앱 백엔드(M4 보내는 쪽). 사람 이름으로 쓰기로 하면 게이트웨이 · 포털 · RA 에도 일이 생긴다 | 큼 |
| RK-02 | 사실이다. 백엔드 · 게이트웨이 · 포털은 이미 되어 있고 화면의 상수만 남았다 | 앱 프론트(다른 세션) | 작음 |
| RK-03 | 사실이다. 백엔드 칸은 되어 있고 화면 몫만 남았다. 갱신 기준은 요청서와 다르다 | 앱 프론트(꼬리는 앱 백엔드 안내 글) | 중간 |
| RK-04 | 사실이다. 백엔드는 되어 있고 화면 몫이다. 지금 화면은 깨질 수 있다(추론) | 앱 프론트 | 작음~중간 |
| RK-05 | 백엔드는 되어 있고 화면 몫이다. cae00 은 10-16 이후 해당하지 않는다(추론) | 앱 프론트 · 박스(남은 `cred.key`) | 작음 |
| RK-06 | 백엔드는 되어 있고 화면 몫이다. 요청서의 근거 줄은 낡았다 | 앱 프론트 | 작음 |
| RK-07 | 10-17 결정 2 로 이미 정했다. 박스 몫이다 | 박스(운영자) | 코드 없음 |
| RK-08 | 두 값은 서로 다른 것을 센다. 맞출 까닭이 없다 | 사용자 결정(측정 뒤) · 포털 주석 | 작음 |
| RK-09 | 필수는 `HWAXRISK_CRED_KEY` 하나다 | 답만 | — |

**요청서가 틀린 것.**
1. RK-01 의 까닭이 틀렸다. "서비스 쓰기 키 하나에만 묶여 있어 키가 없으면 pending" 이 아니라, 보내는 쪽이 아예 없다. `ra_client_from_settings` 를 부르는 런타임 코드가 없다(정의는 ra_client.py:356 하나뿐이고 나머지는 시험이다). 러너도 전송기 없이 만들어진다(main.py:202-203 이 `external_sync_send` 를 넘기지 않는다 → runner.py:2638 에서 None → nightly.py:412-413 이 `skipped: "sender 미배선"` 을 낸다). 그래서 키를 넣어도 한 건도 나가지 않는다. 요청서 RK-04 가 스스로 `sender_unwired` 를 적은 것과도 맞지 않는다.
2. RK-01 의 처방이 지금 앱에는 맞지 않는다. "게이트웨이를 거쳐 그 사람 이름으로 부르는 길이 이미 있다" 고 했지만, 앱이 쥔 사람 PAT 는 읽기 전용이다(identity.py:298-315). 게이트웨이는 읽기 전용 PAT 로 부르는 쓰기 도구를 거절한다(gateway.py:4305-4311 · 3627-3643, read_tools.json 에 reportarchive 항목이 없다). RA 의 객체 쓰기는 시스템 관리자만 할 수 있다(dev 의 RA 사본 `3ece194` 기준 mcp_server/server.py:1820-1826 · backend/app/modules/ai/routes.py:725-742). 정본 설계도 KG 쓰기를 서비스 계정으로 정했다(docs/design-risk-review/plan.md:2976 · 3608 · 4263, 원칙 10 은 :2262). 그러므로 "결정 필요 0" 이 아니다.
3. RK-06 · RK-09 의 근거(main.py:119 · config.py:29-31, 키 다섯 개)는 c3f46ba 판이다. 요청서 8절이 반영됐다고 적은 `8d672c7` 이 필수 키를 하나로 줄였다(config.py:64).
4. RK-07 의 "운영 박스에 둘지는 아직 정하지 않았다" 도 틀렸다. 10-17 결정 2 가 "암호화해 매일" 로 정했고 cae00 절차도 있다(docs/followups-1017/PLAN.md:14 · server-setup.md:81-153).
5. RK-03 의 갱신 기준 "남은 수명 < credential_margin_s" 가 코드와 다르다. 코드는 갱신 문턱 `HWAXRISK_PAT_RENEW_BEFORE_S`(기본 7일)를 쓴다(routes.py:158-159 · config.py:196). 그 문턱이 여유보다 커야 기동한다(main.py:69-75).
6. 6절의 "게이트웨이 할 일 없음" 은 RK-01 을 사람 이름으로 하면 성립하지 않는다. 게이트웨이(읽기 전용 문)와 RA(관리자 전용 쓰기)에 일이 생긴다.

**요청서 밖에서 본 것(고치지 않았다).**
- 화면이 `external_sync` 객체를 글자로 그린다. `ExternalSyncBadge` 는 `RA {sync.ra}` 를 그대로 그린다(frontend/src/components/Badge.tsx:129-141). 그런데 백엔드는 10-13 `0966b41` 부터 이 칸을 객체로 준다(routes.py:992-994). 과제 화면은 기본 탭에서 그 표를 그린다(ProjectPage.tsx:963 · 1033 · 1240-1247). 그래서 타깃이 하나라도 있는 과제 화면은 React 오류("Objects are not valid as a React child")로 깨질 것으로 본다(추론이고 실행해 보지는 않았다). 프론트는 10-07(`3e01d13`) 뒤로 바뀐 적이 없다. 프론트 세션이 가장 먼저 확인할 일이다.
- 지금 웹 버튼이 Claude 길의 등록과 서로를 갈아 끼운다(추론). 버튼은 청중을 `mcp-gateway` 하나로 발급하고 `source` 없이 등록한다(portalPat.ts:24-29 · risk.api.ts:242-243 → `manual` 로 적힌다, routes.py:590). 앞선 등록이 `gateway-exchange` 면 백엔드가 그 PAT 를 포털에서 폐기한다(routes.py:73-74 · 296-305). 새 등록에는 step-forge 가 없으니 `due_reason=audience` 가 되고(routes.py:147-161), 다음 Claude 호출이 다시 교환한다. 그때 앞의 `manual` PAT 는 폐기되지 않고 남는다.
- 야간 잡이 돌지 않는다. 러너 루프에 `nightly_loop` 를 처리하는 갈래가 없고(runner.py:27 · 2654-2687), `run_nightly`(nightly.py:508)를 부르는 런타임 코드도 없다. RK 항목과는 따로 볼 일이다.

## 1. 줄 번호 대응

| 요청서가 적은 줄 | HEAD(`ecad8c8`) |
|---|---|
| ra_client.py:327-339(c3f46ba) · :353-366(ecad8c8) | ra_client.py:352-365(한 줄 밀렸다) |
| main.py:119 `secrets_valid = box_match and all(…SECRET_KEYS)` | main.py:192-195 `config.box_assessment`. 판정식 자체가 바뀌었다 |
| config.py:29-31 `SECRET_KEYS` 다섯 | config.py:64(하나) · 70-73(선택 키 여섯) |
| portalPat.ts:26 · SettingsPage.tsx:271 · routes.py:69 | 그대로다(routes.py:69-70) |
| PLAN.md:180 | docs/risk-review-redesign/PLAN.md:180(종합 보고서의 RA 저장은 M4) |
| 포털 config.py:212 | 그대로다(211-215) |

## 2. 항목별

### RK-01 — RA 쓰기

**확인.**
- RA 로 나가는 것이 없다는 것은 사실이다. 근거는 0절 1 에 적었다. `sync_summary` 도 그 사실을 이미 말한다(ra_client.py:499-514, `reason` 은 늘 `sender_unwired` 이다).
- 쌓이는 op 는 두 종류뿐이고 둘 다 사람이 한 일에서 나온다. 하나는 라벨 기록의 상태 병합과 verified_by|refuted_by 연결이다(metrics.py:227-252 · 409). 다른 하나는 X태그 승격의 design_trait 과 exhibits 다(character.py:349-414, 큐레이션 routes.py:5619). op 는 앱 안에서만 쓰는 꼴(`merge_object` · `link`)이다. 이것을 RA 도구 호출로 옮기는 번역기가 없다. finding 의 RA 객체를 만드는 op 도 없다. `rr_id_map`(risk_store.py:525)을 채우는 곳도 없고, nightly.py:432-454 가 읽기만 한다.
- 패널 보고서는 이미 사람 이름으로 RA 에 들어간다. 패널은 사람 PAT 로 포털 `/agent/chat` 을 부른다(engine_client.py:286-319 · 457). 포털은 그 사람의 챗 PAT(`scopes ['chat']`)를 새로 찍어 에이전트 서버에 넘긴다(포털 backend/app/agent/routes.py:379-418, deps.py:121-145). 에이전트 서버는 그 PAT 로 게이트웨이에 붙어 `create_report_draft` 를 부른다(HWAXAgentServer app.py:240-270). 이 길은 사용자 결정 FU-D17 로 그대로 둔 것이다(identity.py:303-305 주석). 쟁점 패널은 보고서를 저장하지 않는다(runner.py:866 · 901). 종합 보고서의 RA 저장은 M4 몫이다(risk-review-redesign/PLAN.md:180, context-notes.md:78 의 '비공개 과제는 RA 에 올리지 않는다').
- 게이트웨이의 사람별 위임 `per_user_sso.reportarchive` 는 infra/.env 에 `RA_SSO_SECRET` 이 있을 때 생기고, 서비스 부서 헤더를 뺀다(provision-config.sh:738-749). 호출자 이메일이 있으면 그 사람의 RA 자격으로 부른다(gateway.py:4357-4420). dev 의 gateway_config.json 에는 이 항목이 없다. cae00 에서 켜져 있다는 것과 RA `/api/auth/sso` 가 정상이라는 것은 요청서의 말이고 여기서는 확인하지 못했다.
- 사람 이름으로 쓰는 길은 세 곳에서 막힌다.
  ① 앱이 쥔 사람 PAT 는 `scopes ['read']` 만 받는다(identity.py:298-315 · config.py:384, 게이트웨이 교환 등록 routes.py:316-321, 게이트웨이 교환 명세 provision-config.sh:716).
  ② 게이트웨이는 읽기 전용 PAT 에 `x-hwax-readonly` 를 싣고(gateway.py:4841-4842 · rest_proxy.py:68-75), 허용 목록 밖의 도구를 거절한다(gateway.py:4305-4311).
  ③ RA 의 `create_object · update_object · add_object_alias · link_objects` 는 `/api/ai/ontology/write` 로 가고 `require_system_admin` 이 걸려 있다(dev RA 사본 기준이고 운영 RA 판은 보지 못했다). 그래서 일반 사람 이름으로 부르면 403 이 날 것이다(추론).
- 정본 설계는 그 반대로 정했다. "(b) 패널이라도 KG 쓰기는 항상 서비스 쓰기 키로 하고, RA 소유자는 서비스 계정이며, 사용자 귀속은 앱 DB owner_sub 가 맡는다" 는 것이다(plan.md:2976). 정적 시험이 그 경계를 지킨다(backend/tests/test_no_write_tools.py). 다만 정본은 "게이트웨이의 서비스 `rat_` 이 대신한다" 를 전제로 썼는데, RA 위임이 켜진 박스에서는 이메일이 실린 PAT 가 사람별 길로 간다. 이 전제는 10-03 뒤로 낡았다.

**몫.** 사용자 결정이 먼저다(3절 D-1). 그 뒤의 일은 앱 백엔드 몫이고, 보내는 쪽(M4)을 만든다. 사람 이름으로 쓰기로 하면 게이트웨이와 포털(쓰기 자격의 범위), RA(관리자 전용 쓰기 풀기 — 요청서로 보낸다) 몫이 생긴다. 박스는 운영 RA 에 온톨로지 부트스트랩(backend/scripts/bootstrap_ra_ontology.py, 실행자 `RA_ADMIN_PAT`)이 되어 있는지 먼저 본다.

**권하는 길.**
1. KG 인스턴스를 누구 이름으로 쓸지 하나를 정한다.
   - (가) 정본대로 서비스 계정으로 쓴다. 박스가 `HWAXRISK_PORTAL_PAT_RW` 를 둔다(OB-18). cae00 은 RA 위임이 켜져 있으니 그 PAT 주인의 이메일로 RA 에 닿는다. 그래서 그 계정이 RA 시스템 관리자여야 한다(추론이며 확인이 필요하다). "서비스 키 없이" 라는 목표와는 어긋나지만, RA 가 기준정보 쓰기를 관리자 전용으로 둔 것과는 맞는다.
   - (나) 사람 이름으로 쓴다. 사람마다 쓰기 PAT 를 하나 더 받아 둔다(교환의 scopes 는 원 PAT 의 부분집합이어야 한다, 포털 auth/routes/pat.py:218-224). 이 길은 원칙 10 을 뒤집는다. 앱 DB 와 키가 새면 90일 동안 모든 게이트웨이 쓰기 도구를 그 사람 이름으로 쓸 수 있게 된다. 범위를 좁히려면 포털과 게이트웨이에 'RA 쓰기만' 이라는 새 범위가 필요하고, RA 도 관리자 전용 쓰기를 풀어야 한다. 누구 이름인지도 따로 정해야 한다. op 는 라벨을 단 사람이나 승격한 큐레이터가 낸 것이고, X태그 승격은 주인이 서로 다른 여러 과제에 걸친다. 사람 이름으로 쓴 보고서가 개인함에 쌓일 수 있다는 점(RP-01)도 걸린다.
   - 권고는 KG 인스턴스는 (가)로 하고, 사람의 문서인 보고서(종합 보고서, M4)만 사람 이름으로 하는 것이다. 보고서는 이미 포털 챗 PAT 길로 사람 이름으로 쓰고 있다(FU-D17). 앱이 그 길로 보고서를 내려면 포털이나 에이전트 서버에 'PAT 주인 이름으로 RA 보고서 저장' 문이 하나 있어야 한다.
2. 어느 쪽을 고르든 보내는 쪽은 앱 백엔드가 만든다.
   - `ra_client` 에 op 를 도구 호출로 옮기는 번역을 넣는다. `merge_object` 는 get_object 뒤 update_object 병합(`upsert_props`, ra_client.py:311-322)으로, 객체가 없으면 code 로 create_object 한다. `link` 는 link_objects 로 보낸다. 이때 id 를 풀고 `rr_id_map` 에 적는다.
   - 전송기는 main.py:202-203 에서 `RiskRunner(external_sync_send=…)` 로 꽂는다. 비공개 과제의 `withheld` 는 그대로 둔다(routes.py:1083 · 1173-1185).
   - 사람이 없는 배경 잡의 자격도 정해야 한다. (가)는 박스 키 하나라 문제가 없다. (나)는 그 사람의 저장된 쓰기 PAT 만 쓴다. PAT 가 없거나, 폐기됐거나, 풀리지 않거나, 수명이 모자라면 서비스로 내려가지 않는다(U-3 과 같은 규칙).
3. 조용히 pending 으로 남지 않게 한다.
   - `sync_summary` 의 `reason` 을 상수(ra_client.py:511)에서 실제 상태로 바꾼다. 갈래는 `credential_missing:<누구>` · `read_only` · `forbidden`(403) · `transient` · `withheld` 이다.
   - 자격 없음 · 401/403 · 읽기 전용 거절은 재시도하지 않고 곧바로 `unavailable` 로 옮기며 사유를 남긴다(`mark_unavailable`, ra_client.py:426-428). 전송 실패 · 5xx · 기한 초과만 지수 백오프로 다시 보낸다(`note_sync_failure`, ra_client.py:467-480 — 8회 뒤 unavailable).
   - 사람이 자격을 고친 뒤에는 '재동기'(ra_client.py:483-493)로 되살린다. `risk_next_step` 은 이미 그 요약을 싣는다(entry.py:803-804).
   - 기동 로그에 '보내는 쪽 배선 여부 · 자격 출처' 한 줄을 남긴다.

**크기.** 크다. 번역기 · id 사상 · 전송기 · 시험이 들고, 결정에 따라 다른 리포 셋이 더해진다. 7절 'RA 반영' 시험의 통과 기준("그 사람 이름으로")도 결정 뒤에 다시 쓴다.

### RK-02 — 발급 청중 step-forge

**확인.** 사실이다. 웹 버튼은 `audiences: ["mcp-gateway"]` 로 발급한다(frontend/src/api/portalPat.ts:23-29). 안내 글은 SettingsPage.tsx:270-271 이고, 274 의 '직접 발급할 때의 조건' 도 mcp-gateway 만 말한다. 백엔드가 바라는 청중은 이미 둘이고(routes.py:69-70), 하나가 모자라면 `due_reason: audience` 를 낸다(routes.py:140-161). 게이트웨이 교환 명세도 이미 둘이다(provision-config.sh:714-716). REST 다리는 aud 에 사이트 이름이 있어야 받는다(rest_proxy.py:201-206). 포털 `/auth/pat` 은 step-forge 를 받으므로 포털은 바꿀 것이 없다(포털 config.py:238-239 · auth/routes/pat.py:138-139). 이 일은 10-14 화면 요청서에 이미 있다(docs/risk-credentials/frontend-request.md:30 · 34).

**몫.** 앱 프론트(다른 세션)다. 백엔드는 할 일이 없다(아래 선택 하나만 있다).

**권하는 길.** `MINT_BODY.audiences` 를 `["mcp-gateway","step-forge"]` 로 바꾼다. 버튼으로 하는 등록에 `source: "web"` 을 싣는다(frontend-request.md:34 — 싣지 않으면 `manual` 로 적혀 갈아 끼울 때 폐기되지 않는다). 안내 두 줄도 고친다. 선택 사항으로, 백엔드가 `GET /api/me` 의 `portal_pat.auto` 에 바라는 명세(`PORTAL_PAT_WANTED`)를 실어 주면 화면이 상수를 따로 들고 있지 않아도 된다. 그러면 이번 같은 어긋남이 다시 생기지 않는다(작음). 7절의 Claude 캡처 시험은 이 고침을 기다리지 않아도 된다. 그 사람의 등록이 게이트웨이 교환으로 되어 있고 Claude 에 넣은 PAT 에 step-forge 가 있으면 된다(포털 토큰 화면의 기본 청중에 들어 있다, 포털 config.py:231-239). 그 뒤에 웹 버튼을 누르면 다시 깨진다(0절).

**크기.** 작음.

### RK-03 — 웹 자동 등록

**확인.** 백엔드 칸은 되어 있다. `GET /api/me` 의 `portal_pat.auto`(routes.py:163-176 · 554), 끄기 `PUT /api/me/portal-pat-auto`(routes.py:598-605), 등록의 `source` 받기(routes.py:573-595)가 있다. 화면에는 아무것도 없다(types.ts 에 `auto` 칸이 없고, SettingsPage 에 스위치가 없다). 갱신 기준은 0절 5 에 적은 대로 요청서가 틀렸다. 화면은 기준을 스스로 셈하지 말고 `auto.enabled && auto.due` 만 보면 된다.

**몫.** 앱 프론트다. 꼬리로 앱 백엔드 몫이 하나 있다. 스위치가 화면에 나가면 `AUTO_STOP_HINT` 와 `pat_unavailable_guidance` 에서 '곧 생긴다 — 그때까지는 운영자가 DB 에서' 꼬리를 뗀다(runner.py:378-381 · 384~, frontend-request.md:36).

**권하는 길.** frontend-request.md:28-36 그대로 한다. RK-02 와 한 묶음으로 낸다. 청중이 하나인 채로 자동 등록을 켜면 `due=audience` 가 풀리지 않아 화면을 열 때마다 발급한다. 웹에서 난 실패는 백엔드가 모른다(실패 뒤 쉼은 게이트웨이 길에만 있다, routes.py:202-209). 그러니 화면이 한 세션 안에서 되풀이하지 않게 막는다.

**크기.** 중간(화면).

### RK-04 — 'RA 반영 안 됨' 표시

**확인.** 백엔드는 되어 있다. 과제 화면의 타깃(routes.py:992-994), 타깃 목록(routes.py:2398), 진행판(routes.py:3254-3255), `risk_next_step`(entry.py:803-804)에 요약이 실린다. 화면은 옛 꼴 그대로다. 타입은 문자열이고(types.ts:44-45), 배지는 객체를 글자로 그린다(Badge.tsx:129-141). 타깃 화면의 부제는 "레벨이 오를 때마다 … ReportArchive 에 쌓입니다" 라고 하는데(TargetPage.tsx:752) 지금은 사실이 아니다. 0절의 화면 깨짐 추론이 이 자리다. 10-14 요청서 3절에 이미 있다(frontend-request.md:58-62).

**몫.** 앱 프론트.

**권하는 길.** 타입을 `{state, pending_ops, reason, message}` 로 바꾸고, `message` 를 재동기를 누르기 전에도 보인다. 재동기 응답(`ResyncQueued`, types.ts:797)은 꼴이 또 다르니(`{state, attempts, next_at, last_error, done_at, pending_ops[]}`) 따로 받는다. 부제도 고친다. 과제 화면이 정말 깨지는 것이라면 결함이니 우선순위를 '중간' 보다 높게 본다.

**크기.** 작음~중간.

### RK-05 — `cred.key` 폴백 알림

**확인.** 백엔드는 되어 있다. 키 출처 판정이 있다(config.py:609-624, 순서는 secrets → env → path → dev_fallback). 까닭 `cred_key_dev_fallback` 과 값을 옮기는 한 줄 명령이 있고(config.py:640-658 · 712-719), 이 까닭은 `secrets_valid` 를 거짓으로 만든다(config.py:734). 기동 로그에도 남는다(main.py:155-165 · config.py:787). cae00 은 10-16 에 같은 값을 secrets.env 로 옮겼으므로 출처가 `secrets` 이고 이 까닭은 뜨지 않을 것이다(추론 — 박스 응답은 보지 못했다). 남아 있는 `cred.key` 파일 자체는 판정이 말하지 않는다. 다만 리스크 백업 tar 에서는 빠진다(backend/scripts/backup-to-drive.sh:63). 화면은 present/absent 만 보인다(SettingsPage.tsx:373-381).

**몫.** 앱 프론트(`cred_key_source` 와 reasons 보이기)다. 남은 파일을 치우는 것은 박스 몫이다(followups-1017/server-setup.md:150-153).

**권하는 길.** 화면 일은 RK-06 과 같은 일이다. 선택 사항으로, 출처가 secrets 인데 `cred.key` 가 남아 있으면 막지는 않는 정보 수준의 까닭(`cred_key_leftover`)을 백엔드에 더할 수 있다(작음). 요청이 없으면 하지 않는다.

**크기.** 작음.

### RK-06 — 박스 자격의 까닭을 나눠 보이기

**확인.** 요청서의 근거는 c3f46ba 판이다(1절). HEAD 는 까닭을 code · keys · message · fix 로 나눠 낸다. ⓐ 는 `host_mismatch`, ⓑ 는 `missing_required` 와 `missing_optional`(키 이름만 싣는다), ⓒ 는 `cred_key_dev_fallback` 이다. 그 밖에 `cred_key_invalid` 와 `cred_key_path_missing` 도 있다(config.py:661-734). 로그인한 사람에게는 글까지 주고, 익명에게는 code 만 준다(routes.py:565-569). 화면은 고정 문구다(SettingsPage.tsx:360-365 · RiskHomePage.tsx:206-211). HEAD 의 판정이라면 cae00 은 키를 옮긴 뒤 `secrets_valid` 가 참이어야 하니, 그 문구는 이제 뜨지 않을 것이다(추론). 빠진 선택 키는 지금 화면 어디에도 보이지 않는다.

**몫.** 앱 프론트(frontend-request.md:38-56).

**권하는 길.** 고정 문구 대신 `reasons` 의 message 와 fix 를 보인다. `missing_optional` 은 정보로 보이고, fix 의 셸 한 줄은 코드 모양으로 보인다. 백엔드는 할 일이 없다.

**크기.** 작음.

### RK-07 — `backup_unencrypted`

**확인.** 이 경고는 키가 없으면 늘 뜨고, 끄는 손잡이는 없다(main.py:253-263). `backup_key` 는 요청마다 secrets.env 와 env 를 다시 읽으므로, 키를 넣으면 재기동 없이 경고가 사라진다(config.py:589-593). 키가 없으면 백업이 평문 DB 와 exports 를 Drive 로 올린다(backup-to-drive.sh:47-50 · 71-73). 운영 전제도 이미 정해져 있다. 10-17 결정 2 가 '리스크 앱 DB 백업은 암호화해 매일' 로 정했다(followups-1017/PLAN.md:14). cae00 절차도 있다(같은 폴더 server-setup.md:81-153 — 공개키는 dev 와 같은 것을 쓰고 개인키는 사용자가 지닌다). 업데이트 이력(backend/config/changelog.yaml:462)과 키 표(config.py:82 · docs/risk-review-redesign/server-setup-m1.md:98)에도 적혀 있다.

**몫.** 박스(운영자, OB-17)다. 앱 코드는 할 일이 없다.

**권하는 길.** 끄는 손잡이는 만들지 않는다. 이 경고가 말하는 것은 '설계 원문이 평문으로 나간다' 는 사실이고, 의도로 비워 둔 박스라도 백업이 돌면 여전히 참이다. 그래서 답은 "운영의 기본 전제는 키가 있는 것이고, 알림을 없애는 길은 공개키를 넣는 것 하나다" 이다. 박스가 이 앱의 백업을 정말 돌리지 않는다면 그 사실을 박스 기록에 적고, 경고는 그대로 둔다.

**크기.** 코드 없음.

### RK-08 — `risk_concurrency` 2 와 심의 한도 6

**답(코드).**
- `risk_concurrency` 는 리스크 앱이 한 번에 돌리는 패널 일꾼 수다. 환경변수는 `HWAXRISK_CONCURRENCY` 이고 기본값은 2 다(config.py:363). 러너 세마포어가 이 값을 쓰고(runner.py:2639-2640 · 2714-2745), 잡 하나의 동시 패널 수도 이 값 밑으로 죈다(runner.py:1110 · mcp_server.py:265). Tier 패널과 쟁점 패널이 함께 센다. 카드 대조는 따로 센다(`HWAXRISK_REVIEW_CONCURRENCY` 8, config.py:175).
- '심의 한도 6' 은 에이전트 서버의 `DELIB_JOB_MAX_RUNNING` 이다. 코드 기본값은 2 이고(HWAXAgentServer delib_jobs.py:62), 6 은 cae00 박스 .env 의 값이다(docs/delib-ops/request.md:60). 이 한도는 MCP 심의 잡만 센다. 리스크 패널은 포털 `/agent/chat` 에서 열리는 분리 스트림이라 이 한도에 들지 않는다(app.py:965-982, delib-ops/PLAN.md:17 · context-notes.md:8-9 · 127-128 · server-setup.md:68).
- 그러니 두 값은 같은 GLM 을 나눠 쓰는 별개의 문이다. 리스크 쪽을 6 으로 맞추면, 리스크 패널 6개(한 패널이 단계마다 좌석 수만큼 LLM 을 한꺼번에 부른다) 위에 MCP 심의 6개와 카드 대조 관문이 더해진다.
- 바꾸는 자리도 문제다. 이 값은 knobs.env 손잡이가 아니라(config.py:214) 매니페스트 launch.env 로만 닿는다(config.py:109 — SIF 가 cleanenv 다). 지금 매니페스트에는 적혀 있지 않다(.portal/manifest.yaml launch.env). 그래서 박스 하나만 따로 올릴 수 없다.

**권고.** 지금은 2 로 둔다. 올리려면 LLM 용량 측정(docs/llm-pool/capacity.md)을 한 뒤 사용자가 값을 정한다. 그 전에 앱 백엔드에서 `HWAXRISK_CONCURRENCY` 를 knobs.env 손잡이로 옮겨 박스마다 정할 수 있게 하는 것을 권한다(작음 — BOX_KNOBS 에 넣으면 /api/meta/runtime 이 출처를 보인다). 포털 주석(포털 backend/app/config.py:212)의 "같은 2" 는 "서로 다른 문이고 코드 기본값만 2" 로 고친다(포털 HP-45 몫).

### RK-09 — 필수 비밀 키

**답(코드, HEAD).** 필수 키는 `HWAXRISK_CRED_KEY` 하나다(config.py:60-64). secrets.env, 환경변수 `HWAXRISK_CRED_KEY`, `HWAXRISK_CRED_KEY_PATH` 가 가리키는 파일 가운데 어느 하나에 있으면 있는 것으로 센다(config.py:609-624). 앱이 만든 `cred.key` 폴백은 동작은 하지만 `secrets_valid` 를 거짓으로 만든다(config.py:712-719 · 734). 선택 키는 여섯이고, 없을 때 무엇이 닫히는지 코드에 적혀 있다(config.py:70-85).

| 선택 키 | 없으면 |
|---|---|
| `HWAXRISK_PORTAL_PAT` | 사람 자격이 없을 때의 짧은 조회(전문가 명단 · 현장 VOC · 문헌 E10 · 캡처의 MCP 폴백)가 닫힌다. 패널 잡은 이 키를 쓰지 않는다 |
| `HWAXRISK_PORTAL_PAT_RW` | 지금은 달라지는 것이 없다(보내는 쪽이 미배선, M4) |
| `HWAXRISK_HEAX_SERVICE_PAT` | StepForge REST 의 마지막 폴백이 없어진다. 웹 토큰도 사람 PAT 다리도 없는 캡처는 G6 `unit_unknown` 이 된다 |
| `HWAXRISK_AIDH_API_KEY` | 지금은 달라지는 것이 없다(M4) |
| `HWAXRISK_BACKUP_KEY` | 백업이 평문이 되고 `backup_unencrypted` 가 뜬다(env 로도 읽는다) |
| `HWAXRISK_HEAX_GATEWAY_SECRET` | `/api/auth/sso` 와 `/api/auth/portal-pat` 가 404 가 된다. Claude 길의 위임과 PAT 자동 등록이 없어진다(env 로도 읽는다) |

**권고.** 목록은 그대로 둔다. 다만 요청서의 목표(SSO 자격이 저절로 이어지는 것)에는 `HWAXRISK_HEAX_GATEWAY_SECRET` 이 사실상 필수다. `HWAXRISK_BACKUP_KEY` 도 10-17 결정 2 에 따라 운영의 전제다. OB-18(박스 서비스 키)은 위 표의 '없으면' 칸을 보고 정하면 된다. RA 쓰기 키와 AIDataHub 키는 M4 전까지 넣어도 효과가 없다. RK-06 화면의 '빠진 키 이름' 은 `missing_required.keys` 와 `missing_optional.keys` 가 그대로 준다(config.py:686 · 720-728).

## 3. 결정이 필요한 것(요청서는 0 이라고 했다)

| # | 무엇 | 언제 |
|---|---|---|
| D-1 | RK-01 — KG 인스턴스를 서비스 계정과 사람 가운데 누구 이름으로 쓸지. 사람이면 누구인지(과제 주인 · 라벨을 단 사람 · 큐레이터) | 보내는 쪽(M4)을 짓기 전 |
| D-2 | RK-08 — 리스크 패널의 동시 수(지금 2) | LLM 용량 측정 뒤 |

## 4. 7절 시험 보정

- 'Claude 캡처' 는 RK-02 를 기다리지 않아도 된다. 시험 전에 `GET /api/me` 로 그 사람의 등록 출처가 `gateway-exchange` 이고 aud 에 step-forge 가 있는지 본다.
- 'RA 반영' 은 D-1 과 M4 뒤로 미룬다. 통과 기준의 '그 사람 이름으로' 는 D-1 의 결과에 따라 바뀐다.
- '박스 반영' 은 그대로 둔다.
- '백업 알림' 은 공개키를 넣은 뒤 `warnings` 에 `backup_unencrypted` 가 없으면 통과다(재기동은 필요 없다).
