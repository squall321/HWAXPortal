# 앱별 과제 키 · 행의 주인 · 시야 · SP 과제 키(2026-10-31)

| 항목 | 내용 |
|---|---|
| 무엇 | 앱마다 과제 키의 꼴, 행의 주인과 게이트웨이가 부르는 자격, 누가 무엇을 보나, ODB 잡 메타의 과제 칸, SP 과제 키를 받나를 한 자리에 모은 표다. 절차 S6 의 '매핑 표' · '시야 제약' 두 줄의 답이고, 사용자 결정 10-31 A13 (A) 'SP 과제 키를 앱 사이 정본으로' 의 결정 표로 쓴다. |
| 근거 | [체크리스트](checklist.md) S6 · [PLAN](PLAN.md) §5-3 · §7 #8 · [triage-1031](../leftovers-1017/triage-1031.md) 표 A 의 A13 · 표 B 의 B6 |
| 대조한 판 | StepForge main `51c8788`(SP 사본 `external/StandardPlatform` `778db2f`) · KooRemapper main `d3d777c`(DynaForge — 백엔드 파일은 `platform/backend/` 아래) · ThermalShockMCP main `6e6a6db` · HWAXRisk main `9bd5f48`(파일은 `backend/` 아래) · 게이트웨이 master `5f4ba5f` · Report Archive 는 이 박스의 로컬 사본 `3ece194`(09-27 — 그 뒤 판은 모른다). odb-hub 는 소스가 우리 쪽에 없어 이 리포의 [reference.md](fixtures/odb-hub/reference.md)(09-16 실측)로 적었다. 아래 `파일:줄` 은 이 판이다(다른 리포는 읽기만 했다). |

## 1. 앱마다

'조직 단위 모아 보기' 칸의 **관리자 자격** · **별도 원장** 표시가 조직 전체를 한 번에 보려면 따로 갖춰야 하는 것이다.

| 앱(게이트웨이 키) | 과제 키 꼴 | 행의 주인 · 게이트웨이가 부르는 자격 | 시야(읽기) · 쓰기 | SP 과제 키 | 조직 단위 모아 보기 |
|---|---|---|---|---|---|
| StepForge(`heax-step_forge`) | `project_id` 16진 23자(밀리초 시각 13 + uuid 10 — `app/db.py:418-420`). 사람이 적는 과제번호 `code` · 담당자 `owner` · 부서 칸이 함께 있다(`app/db.py:20-25`). 도구는 id 대신 이름 · 코드로도 부른다(`app/mcp_server.py:566-567`) | 게이트웨이는 허브 서비스 토큰(관리자 PAT `hwax-gateway-mcp` — 게이트웨이 `provision-config.sh:303-318` · `:681-688`)으로 부르고, MCP 길은 부른 사람을 모른다(`app/admins.py:5-9`). `owner` 는 웹 · REST 길에서 포털 신원으로 채우는 기록 칸이지 접근 제어가 아니다(`app/rest.py:89-103` · `:255-258`) | 누구나 전부 — `list_projects` 는 이름 · 코드 · 목적으로만 거른다(`app/mcp_server.py:559` · `:633-640`), 담당자 칸은 가린다(`:563-564`). 쓰기도 막지 않는다(`app/admins.py:3-4`) | **받는다** — 허브 코어 API 거울(`core/sp_core.py:45-62`, 주소 `STEPFORGE_SP_CORE_URL` · `core:read` 토큰 파일). CAD 개정 줄의 `task_code` 가 허브 과제를 가리키고(`app/db.py:229-237`), 사람이 적은 글을 허브 과제로 푸는 한 판정은 `match_task`(key · 과제코드 · 별칭 · 과제명 — `core/sp_core.py:1159-1182`). 거울에도 권한 · 부서 규칙이 없다(`core/onto_graph.py:25`) | 필요 없음 — 누구나 전부 본다 |
| DynaForge(`heax-kooremapper_mcp`) | 세션 `session_id` ULID 26자(`app/models.py:76` · `app/modules/sessions/services.py:25`). 리포트 id 도 ULID(`app/models.py:131`). 리포트의 과제는 사람이 적는 글 `eng_meta.project`(`app/models.py:169-171`)나 리포트에 박힌 `project_name`(`:190`)이다. 후처리 예약으로 들인 리포트에는 `external_job_key` `stcx:<slurm id>`(`:175-177`) | 사람별 위임 — 게이트웨이 `per_user_sso.kooremapper_mcp`(`KOORM_SSO_SECRET` 이 있을 때 — 게이트웨이 `provision-config.sh:697-701`), 없으면 서비스 `kr_` PAT(`app_tokens.kooremapper_mcp` — `:683-684`). MCP 서버는 받은 `Authorization` 과 소속 헤더를 그대로 REST 로 넘긴다(`platform/mcp_server/server.py:33-46`). 행의 주인은 `user_id`(`app/models.py:77` · `:135`) | 세션 — 소유분 + 공개 범위(private 기본 · team · department · company — `app/shared/visibility.py:34-58` · `app/models.py:84-88`). 리포트 — 소유분 + 같은 소속 공유분(반입 때 얼린 `shared_affiliation` 을 게이트웨이 서명 소속과 맞댄다 — `app/modules/reports/services.py:833-843` · `app/modules/reports/routes.py:397-404`, MCP 설명 `platform/mcp_server/server.py:1264` · `:1235`). 공유분은 읽기만이고 고치기 · 지우기는 소유자만(`app/modules/sessions/services.py:58-65` · `app/modules/reports/routes.py:105-111`). ⚠ MCP `list_sessions` 설명은 아직 'user_id 스코프'(`platform/mcp_server/server.py:120-123`)인데 백엔드는 공개 범위로 바뀌었다(`app/modules/sessions/services.py:40-55`) | **받는다** — 사본 표(`alembic/versions/0018_sp_receive.py`)와 `core:read` 토큰 칸 `sp_core_token`(비면 받지 않는다 — `app/config.py:141`, cae00 은 토큰이 아직 없어 꺼져 있다 — 이 리포 `docs/cae00-deploy-guide.md:893-897`). 리포트는 반입 때 `eng_meta.project` 로 허브 과제의 개정에 잇고(옛 key 는 지금 key 로, 거울에 없으면 '확인 못 함' — `app/modules/ontology/services.py:238-249` · `:166-171`, 부르는 자리 `app/modules/reports/services.py:1243-1252`), 과제코드 · 별칭으로 푸는 한 판정은 `resolve_task`(`app/modules/ontology/services.py:366-410`) | 리포트는 **관리자 자격**(`is_system_admin` 이면 전사 — `app/modules/reports/services.py:874-875`). 세션은 관리자 우회도 없어 **별도 원장**이 있어야 한다(`app/shared/visibility.py:34-58`, 관리자 창구는 사용자 목록뿐 — `app/modules/admin/routes.py:64`). 전사 수만은 `corpus_summary`(`platform/mcp_server/server.py:697-700`) |
| ThermalShock(`heax-thermal_shock_mcp`) | `project` 글 하나 — 기본 `"unknown"` · 과제 이름 메타 · 모델 입력 아님(`app/schemas.py:19`). 학습 레코드 id 는 내용 해시(sha256 앞 12자 — `app/schemas.py:58-59`) | 허브 서비스 토큰(게이트웨이 `provision-config.sh:681-688`). 사람 개념이 없다 — 레코드에는 출처 `initial` · `user` 만 남는다(`app/schemas.py:54`) | 누구나 전부 — 데이터셋 파일 하나(`app/config.py:22`)이고 `get_training_data(project)` 는 정확 일치 거르기일 뿐이다(`app/mcp_server.py:331-333`). 더하기 · 지우기도 누구나(`:279` · `:356`) | **안 받는다** — 과제 칸은 위의 글 하나이고 SP 를 읽는 코드가 없다(`app/` 전체 검색 0건) — A13 요청 대상 | 필요 없음 — 데이터셋 하나 |
| HWAXRisk(`heax-hwax_risk`) | 과제 id uuid4 16진 32자(`backend/app/common.py:141-143` · `backend/app/routes.py:868`) + 사람이 적는 `code`(소유자 안에서만 유일 — `backend/app/risk_store.py:30` · `:49`). 심사 대상 `target_key` 는 `<kind>:<ref_id>`(`backend/app/routes.py:2840`, `snap:` · `diff:` — `backend/app/entry.py:768` · `:806`)라 과제 키가 아니다. RA 잇기 `ra_entity_id`(`backend/app/risk_store.py:33`) · ODB 보드 `job_id`(`backend/app/mcp_server.py:318-319`) | 사람별 위임 — 게이트웨이 `per_user_sso.hwax_risk`(단언은 `X-Heax-Sso-Assertion` — 게이트웨이 `provision-config.sh:702-713`). 신원이 풀리면 user, 아니면 service 다(`backend/app/routes.py:780-786`). 행의 주인 `owner_sub`(`backend/app/risk_store.py:29`) | MCP — 사람은 소유 ∪ 멤버(owner · editor · viewer — `backend/app/risk_store.py:70-75`) ∪ `mcp_visibility='org'`, 서비스는 org 만(`backend/app/routes.py:788-798` · 칸 `backend/app/risk_store.py:41`). 웹 목록은 소유분만(`backend/app/routes.py:927-929` · `:948-949`). 쓰기는 역할로 가른다(`backend/app/routes.py:1045-1047`) — org 공개분은 읽기만 | **안 받는다** — 과제 칸은 `code` · `ra_entity_id` · `product_code` 뿐이다(`backend/app/risk_store.py:28-49`) — A13 요청 대상 | **별도 원장**(또는 새 관리자 목록) — 웹 관리자 역할은 아무 과제나 열 수 있어도(`backend/app/routes.py:1255-1257`) 목록은 소유분뿐이고(`:927-929`) MCP 길에는 관리자 우회가 없다(`:773-777`) |
| odb-hub(`odb-hub` — 박스 밖, 소스 없음) | 보드 `job_id` 16진 16자(파일 내용 기반 — `fixtures/odb-hub/reference.md:108`). 잡 메타 `project`(과제명 — 올릴 때 적는 글) · `model` · `revision`(`:109`) — 2절 | **서비스 토큰 하나** — 게이트웨이 `ODB_HUB_TOKEN`(Bearer — `provision-config.sh:511-515` · `:614-631`). 호출자를 가르지 않고 `uploaded_by` 는 전부 `"anonymous"` 다(`fixtures/odb-hub/reference.md:60` · `:109`) | 토큰 하나가 잡 전부를 본다(`reference.md:60`). MCP 로는 잡을 만들거나 지울 수 없고 분석을 다시 돌리기만 한다(`:104`) | 모른다 — 소스가 우리 쪽 어디에도 없다(`reference.md:41`) | 이미 전부 보인다 — 대신 사람별 주인이 없다 |
| Report Archive(`reportarchive` — 우리 몫 아님) | 기준정보 축 `project`(데이터로 만드는 축 — `backend/app/modules/entities/models.py:556`)의 값 `value`(255자 — 유일성은 이 칸) + 선택 `code`(64자 — `models.py:208-212`). 보고서 ↔ 값 잇기는 `report_entities`(`models.py:289-312`). dev 는 축만 있고 값이 0건이다(W-99) | 사람별 — ste 방식 위임(`RA_SSO_SECRET` — 게이트웨이 `provision-config.sh:745-756`)이나 포털에 등록한 본인 토큰. 신원이 있는 호출은 본인 토큰으로만 가고 서비스 계정은 신원 없는 내부 호출과 도구 목록에만 쓴다(게이트웨이 `gateway.py:6663-6667`). 행의 주인 `owner_user_id`(`backend/app/modules/reports/services.py:327-329`) | grant 통합 판정 — 소유 · 시스템 관리자 · 전사 공개(all_org) · 사람 grant · 부서 grant(하위 상속) · 게시판 · 폴더 grant(`backend/app/modules/reports/services.py:317-334` · `:607-614`). 지우기는 소유자 · 시스템 관리자 · 게시판 매니저만(`:354`) | 카탈로그까지만 — 행 받기는 미구현이다(`backend/app/modules/connectors/sp_core.py:1-23`) | **관리자 자격**(시스템 관리자나 전사 공개 grant — `backend/app/modules/reports/services.py:317-334`) |

## 2. ODB 잡 메타의 과제 칸

S6 줄이 'S0 에서 있으면' 이라 적은 칸이다 — 있다.

| 어디서 | 무엇 | 파일:줄 |
|---|---|---|
| odb-hub 잡 메타 | `project`(과제명 — 사람이 올릴 때 적은 글) · `model` · `revision`. 표본은 마스킹(`<PROJECT_A>`)이다 | `docs/procedures/fixtures/odb-hub/reference.md:109` · `:145` |
| 찾기 | `find_job(query)` — 과제명 정확 일치 → 부분 일치 → 모델 · 파일명 차례 | `reference.md:73` |
| ThermalShockMCP 환원 | `sed_sample_from_odb(job=…)` 가 잡 메타 `project` 를 `for_sed_analysis.project` 로 싣는다(모델 입력 아님) | ThermalShockMCP `app/reduce_odb.py:193-195` |
| 포털 R3 씨앗 | `job` 을 넘기지 않는다 — R3 실행의 SED 입력 `project` 는 빠지고 모델 기본값 `"unknown"` 이 된다 | `docs/procedures/fixtures/thermal-shock-sed.yaml:72-78` · ThermalShockMCP `app/schemas.py:19` |
| 리스크 앱 | 과제에 보드 `job_id` 를 붙인다 — 잡 메타의 과제 칸은 읽지 않는다 | HWAXRisk `backend/app/mcp_server.py:318-319` · `:909` · `:915` |
| 경계값 대조(계획) | 학습 294건의 `project` 와 odb-hub 잡의 `project` 를 라벨로 맞대 `board_type` 경계를 정한다(cae00, 과제명은 결과에 남기지 않는다) | `docs/procedures/fixtures/odb-hub/sed-mapping.md:81-88` |

## 3. SP 과제 키 — 무엇이 정본인가

- **SP 의 정의** — 과제 `plm_task` 의 식별자는 과제코드다(SP `mcp_server/guide/GUIDE.md:934`, 원천 표 예시는 key 과제코드(대문자) · label 과제명 —
  `pipeline/AGENTS.md:215`). PLM 기준정보는 허브가 내려 주고 받는 쪽은 받기만 한다(`GUIDE.md:925-929`).
- **받는 쪽 둘이 운영 허브에서 본 것** — `plm_task.key` 는 과제명이고 과제코드는 `properties.task_code` 칸이다(KooRemapper
  `platform/backend/app/modules/ontology/services.py:375-376` · StepForge `core/onto_graph.py:22`, D-637). 그래서 둘 다 사람이 적은 글(과제코드 ·
  별칭 · 과제명)을 허브 key 로 푸는 한 판정을 둔다(StepForge `core/sp_core.py:1159-1182` · KooRemapper `ontology/services.py:366-410`).
- **받는 길** — `GET /core/{type}` 에 `core:read` 토큰(KooRemapper `platform/backend/app/runner/sp_core.py:8-13`). 허브가 key 를 바꾸면 옛 key → 새 key
  짝을 남겨 푼다(KooRemapper `alembic/versions/0018_sp_receive.py:4` · StepForge `app/db.py:195` 의 `previous_keys`).
- **그래서 A13 의 'SP 과제 키' 는 허브가 내는 `plm_task` key 다.** 앱이 저장할 것은 그 key 이고, 사람이 적는 과제코드 · 과제명은 받는 쪽이 한
  판정으로 푼다 — 받는 두 앱이 이미 그 꼴이다. key 가 과제명인지 과제코드인지는 허브 설치가 정한다(SP 안내와 운영 허브가 다르다) — 받는 쪽은
  key 의 꼴을 가정하지 않는다.

## 4. A13 로 읽으면

- **이미 받는 앱 둘** — StepForge · DynaForge. 코드는 있고 `core:read` 토큰을 줘야 켜진다(1절).
- **안 받는 앱 둘** — HWAXRisk · ThermalShock. A13 (A) 의 요청 대상이다. 요청은 A13 의 '먼저 볼 것'(받은 편지함 `2026-10-31-backlog.md` Q17 —
  §6-1 쓸모 판정) 뒤에 이 표를 근거로 낸다. 받는 꼴은 3절이다 — 허브 key 를 저장하고 사람 글은 한 판정으로 푼다.
- **odb-hub** — 박스 밖 서버라 update-all 로 받지 않는다(`docs/design-risk-review/ecad-1031/request.md:3`). 잡 메타 `project` 는 사람이 적는
  과제명이라 SP 키로 이으려면 그쪽이 SP 를 받거나, 그 칸을 읽는 쪽이 과제명 → 허브 key 로 풀어야 한다. 지금 그 칸을 읽는 곳은 ThermalShockMCP
  환원 하나다(2절).
- **Report Archive** — 우리 몫 아님(10-31 지시). 적기만 하고 요청하지 않는다.
- **조직 단위 모아 보기** — 관리자 자격이 필요한 곳은 DynaForge 리포트 · Report Archive, 별도 원장이 필요한 곳은 DynaForge 세션 · HWAXRisk 다.
  StepForge · ThermalShock 은 누구나 전부 보고, odb-hub 는 토큰 하나가 전부를 보는 대신 사람별 주인이 없다.
- **본 것, 고치지 않음** — DynaForge MCP `list_sessions` 의 설명이 옛 글이다(1절 ⚠). 고칠 자리는 KooRemapper 다.
