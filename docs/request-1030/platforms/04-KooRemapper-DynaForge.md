# 04 KooRemapper · DynaForge — 10-30 요청에서 할 일

| 항목 | 내용 |
|---|---|
| 받는 곳 | 세션 `kooremapper-4a`(KooRemapper · DynaForge 리포) |
| 어떻게 갔나 | 10-30 KST 에 포털 세션 `hwaxportal-a5` 가 세 행을 정본 글 그대로 보냈다. 덧붙인 것은 'HP-53 이 레시피 도구를 DynaForge 운영자 writes 에, HP-52 가 find_reports 의 `items` 를 읽는다' 다. 답은 아직 없다(기다림 — [`../outbound.md`](../outbound.md) 1절). |
| 요청서 정본 | [`../../request_261030.md`](../../request_261030.md) 끝 절 '이전 회차에서 남은 챗 · 디지털 워커 요청 (10-30 대조)' 의 'KooRemapper · DynaForge(`46e4283`)' 표 — KR-23 · KR-01(다시) · KR-16(다시). 1 ~ 4절과 7절 '다시 볼 시험' 에는 이 플랫폼 행이 없다. |
| cae00 기준 판 | KooRemapper `46e4283`(요청서 끝 절 머리의 cae00 HEAD) |
| 이 박스(dev)에서 대조한 판 | KooRemapper main `e0451ad`(기준 판 뒤 22커밋) · 포털 main `bf5cd94` · 에이전트 서버 main `7ca3a2e` · 게이트웨이 master `67d8d00` — 2026-10-30 18:00 KST |

세 행이 인용한 백엔드 파일 넷(`recipes/routes.py` · `ontology/routes.py` · `runner/sp_core.py` · `worker/plm_sync.py`)은 기준 판과 HEAD 가 같은 blob 이고 작업 트리 변경도 없다. 그래서 백엔드 줄 번호는 요청서 그대로 맞는다. 줄이 옮겨진 것은 `SKILL.md` 하나다(+4줄).

## 할 일

### KR-23 · 중간 — 레시피 등록을 사람 승인으로 묶을지(결정)

- **무엇이**: (중간) 챗 에이전트가 `recipe_propose` · `recipe_register` 로 올린 파이썬 레시피가 사람 검토 없이 모두에게 등록된다. 운영자 정의의 writes 에도 레시피 도구가 없어 HA-29 의 확인 카드에 걸리지 않는다(포털 몫은 HP-53).
- **근거**: `platform/backend/app/modules/recipes/routes.py:48-51`(propose — 로그인만 본다) · `:144-155`(register — 자동 관문을 통과하면 등록) · `platform/mcp_server/skill/kooremapper/SKILL.md:247-250`('효과를 봤으면 recipe_propose'). 10-30 게이트웨이 `/tools-map` 에 recipe_propose · recipe_register · recipe_run 이 있다.
- **할 일**: 레시피 등록(recipe_register)을 사람 승인이나 관리자 권한으로 묶을지 답해 달라. 묶는다면 MCP 설명에 '등록은 사람이 승인한다' 를 싣는다.
- **출처**: TODO-20261029 R-09 · reflection-1028/04 3절 ⑤

#### 지금 판에서의 자리

- `platform/backend/app/modules/recipes/routes.py` 는 `46e4283..HEAD` 커밋이 0건이고 blob 이 같다(`45ef0ef`). 마지막으로 바뀐 것은 `4c96bbe`(10-27, 레시피 배선)다.
- `routes.py:48-51` 그대로다. `propose_recipe` 가 받는 의존성은 `get_current_user` 하나다.
- `routes.py:144-155` 그대로다. `register_recipe` 도 `get_current_user` 하나이고, 서비스 `register`(`services.py:446-505`)는 정적 검사 · 자기 시험 · 앞 판 호환 · 이 판의 성공 실행 1건 이상 · `useful=true` 평가(글 20자 이상, `_MIN_NOTE` `:33`) 1건 이상만 본다. 사람 승인 · 관리자 검사는 없다. 레시피 모듈의 `is_system_admin` 은 실행 기록 보기(`routes.py:84`) · 평가(`services.py:436`) · 내리기(`:513`) 세 곳뿐이다.
- 평가는 그 실행을 한 계정(또는 관리자)이 남긴다(`services.py:436`). 그래서 한 계정이 제안 → 실행 → 평가 → 등록을 혼자 끝낼 수 있다.
- 등록된 판은 누구나 검색 · 실행한다(`services.py:154-171` `get_version_code` — '등록 판은 누구나, 초안·후보는 올린 사람만' · `search` `:86-129`). 등록하면 `platform/recipes/<이름>/` 로 파일을 쓰지만 git 커밋 · 푸시는 하지 않는다(`:495-505` — `tools/recipes_publish.sh` 는 사람이 돌린다).
- 이 자동 등록은 KooRemapper 계획서에 사용자가 고른 것으로 적혀 있다(`docs/01-plan/features/recipes-1026.plan.md:7` — '등록 문턱 — **LLM 자동 + 자동 관문** … 사람은 내리거나 지울 수 있다'). 그래서 이 행의 답은 그 결정을 바꿀지다.
- `SKILL.md` 는 기준 판 뒤 `85ba2f0` · `aa63e2a` 가 185줄 근처에 4줄을 더해, 요청서의 `:247-250` 이 HEAD 에서는 `:251-254` 다. 레시피 절의 글은 그대로다.
- MCP 의 `recipe_run`(HEAD `platform/mcp_server/server.py:1632`) · `recipe_propose`(`:1662`) · `recipe_register`(`:1686` — 설명 '자동 관문(자기 시험 + 성공 실행 ≥1 + 쓸모 평가 ≥1)을 통과하면 누구나 쓰게 된다')는 기준 판(`:1570` · `:1600` · `:1624`)과 글이 같다. 기준 판 뒤 MCP 에 더해진 도구는 `attach_render`(`85ba2f0`) · `attach_cad`(`aa63e2a`) 둘이다(80 → 82개).
- 10-30 cae00 게이트웨이 `/tools-map` 은 이 박스에서 볼 수 없어 대조 못 함.

#### 우리 쪽 맞물림

- HP-53(포털, 고치는 중) — DynaForge 운영자(`he-sim-dynaforge`)의 `writes` 에 recipe_propose · recipe_register · recipe_run 을 넣는다. 포털 main `bf5cd94` 의 `infra/personas/he-team.json:166` 에는 아직 없다(기준 판 `aec8e29` 와 같은 줄).
- HA-29(에이전트 서버, 고치는 중) — 잡을 시작하는 도구와 운영자 정의의 `writes` 는, 이번 턴 사람 발화가 그 일을 분명히 시키지 않았으면 코드 단에서 확인 카드로 멈춘다. HP-53 과 함께 들어가면 웹 챗에서 시키지 않은 레시피 제안 · 등록 · 실행이 확인 카드에 걸린다.
- 판단 재료 — HA-29 는 에이전트 서버(웹 챗) 쪽 관문이다. 게이트웨이에 PAT 로 바로 붙은 MCP 손님(개인 Claude 등)이 부르는 recipe_register 는 그 관문을 지나지 않는다. 모든 길에서 사람 승인을 받게 하려면 KooRemapper 서버 쪽에서 묶어야 한다.
- 참고(요청서 밖) — HP-53 의 목록은 10-30 cae00 `/tools-map`(기준 판, 도구 80개)과 대조한 것이라 기준 판 뒤의 쓰기 도구 attach_render · attach_cad 는 들어 있지 않다. 운영자 동기화는 게이트웨이에 없는 도구 이름에서 멈추므로([`../context-notes.md`](../context-notes.md) C-8), 이 둘을 `writes` 에 넣는 일은 KooRemapper 새 판이 cae00 게이트웨이에 실린 뒤라야 한다.

### KR-01(다시) · 낮음 — 과제 검색이 허브 행의 별칭을 대조하지 않는다

- **무엇이**: (낮음) DynaForge 과제 검색이 허브 행의 별칭을 대조하지 않는다.
- **근거**: `platform/backend/app/modules/ontology/routes.py:65-67`(key · label · task_code 만 ilike 로 본다). 받기 코드 `platform/backend/app/runner/sp_core.py` · `platform/backend/app/worker/plm_sync.py` 에 alias 가 0건이라(HEAD 대조) 별칭을 담지도 않는다.
- **할 일**: 받기가 허브 행의 aliases 를 보관하고, list_tasks 와 resolve 가 그것도 대조해 matched_by 에 alias 를 싣는다.
- **출처**: 04-KooRemapper-DynaForge KR-01 · reflection-1028/04 KR-01②(일부) · TODO-20261029 R-09

#### 지금 판에서의 자리

- `platform/backend/app/modules/ontology/routes.py` 는 `46e4283..HEAD` 커밋이 0건이고 blob 이 같다(`61254dd`). 마지막 변경은 `54304cd`(10-27)이고, 10-27 회차 KR-01 고침 `ca47363`(과제코드 매칭)은 기준 판 안에 있다.
- `routes.py:65-67` 그대로다. `q` 가 있으면 key · label · `properties.task_code` 셋만 ilike 로 본다. 사람이 붙인 별칭 표(`onto_aliases`, 마이그레이션 `0013`)도 list_tasks 는 보지 않는다. `_matched_by`(`:78-89`)가 내는 값은 task_name · task_code · label 셋뿐이다.
- resolve — `resolve_task`(`services.py:331-362`)는 과제명 같음(`exact`) · 과제코드 같음(`task_code`) · 사람이 붙인 별칭(`alias` — `onto_aliases`, `:357-361`)만 푼다. 그러니 how 값 `alias` 는 이미 '사람이 붙인 별칭' 을 뜻한다. 후보 `task_candidates`(`:365-398`)도 과제코드 · 과제명 · label 만 본다. 부르는 곳은 `report_revision` 응답(`routes.py:182` · `:191-192`)과 `plan_task_links`(`services.py:429` · `:443`)이고, MCP 에 'resolve' 라는 이름의 도구는 따로 없다.
- 받기 — `runner/sp_core.py` · `worker/plm_sync.py` 의 alias 0건은 기준 판 · HEAD 모두 맞다(두 파일 blob 이 같다 — `114a1e8` · `3cb27c6`). 다만 `save_rows` 는 행의 `properties` 를 해석 없이 그대로 담는다(`sp_core.py:205-207`).
- 허브 쪽 — 이 리포가 서브모듈로 고정한 허브 사본(`external/StandardPlatform` `f7485c0`, 10-13 — 기준 판과 HEAD 의 gitlink 가 같다)의 코어 API 는 aliases 를 행 최상위 칸이 아니라 `properties` 안에 싣는다(`backend/app/modules/coreapi/services.py:458-461` — `_properties_out(...) | _aliases_of(...)`, `:835-838` — 별칭이 없으면 키를 만들지 않는다). 고정 봉투 `CoreRowOut`(`schemas.py:128`)에는 aliases 칸이 없다.
- 그래서 cae00 허브가 이 꼴 그대로면 별칭은 이미 `onto_objects.properties["aliases"]` 로 들어와 있고 대조만 안 하는 것일 수 있다. 요청서의 '별칭을 담지도 않는다' 와 갈리는 곳이다. cae00 허브의 판과 받은 행은 이 박스에서 대조 못 함. 받은 과제 행 하나의 `properties` 에 `aliases` 가 있는지 보면 가려진다.
- 시험 자리 — `platform/backend/tests/test_ontology_kr0127.py` · `test_task_matching.py` 가 10-27 의 KR-01 · matched_by 를 잠근다.

#### 우리 쪽 맞물림

- 이 요청서의 HWAX 행(HA- · HG- · HP-) 가운데 DynaForge 과제 검색을 고치는 것은 없다. [`../outbound.md`](../outbound.md) 가 이 세션에 덧붙인 것도 HP-53 · HP-52 둘이다.
- 웹 챗은 list_tasks · task_revisions · compare_task_revisions 를 상시 핵심 도구로 묶는다(에이전트 서버 main `7ca3a2e` `app.py:2294-2300` `_ONTO_CORE`). 별칭 대조가 들어가면 챗의 과제 찾기에 바로 닿는다.
- HWAX 세 리포(본 리포 main)의 코드에는 list_tasks 응답의 `matched_by` 를 읽는 곳이 없다(문서에만 나온다). 에이전트 서버는 결과 글에 '[이 결과는 DynaForge 앱의 list_tasks 이다]' 머리를 붙여 모델에 넘긴다(`tests/test_request_1029.py:137-145`). matched_by 에 새 값을 더해도 우리 쪽에서 깨질 코드는 없다.

### KR-16(다시) · 낮음 — list_tasks 가 key 순으로 먼저 자른 창 안에서만 순위를 매긴다

- **무엇이**: (낮음) list_tasks 가 key 순으로 먼저 자른 창 안에서만 순위를 매겨, 짧은 질의의 앞부분 일치가 창 밖으로 밀릴 수 있다. 행마다 match_kind 도 없다.
- **근거**: `routes.py:69-70`(fetch = min(1000, limit×5) 를 key 순으로 자른다) · `:91`(`_rank`) · `:105`(정렬 · 절단). 응답 항목에는 matched_by 만 있다(`:110`).
- **할 일**: 앞부분 일치를 먼저 받거나 순위를 매긴 뒤 자르고, 행마다 match_kind(앞부분 · 낱말 경계 · 부분)를 싣는다.
- **출처**: 04-KooRemapper-DynaForge KR-16 · reflection-1028/04 KR-16(일부)

#### 지금 판에서의 자리

- 같은 `platform/backend/app/modules/ontology/routes.py` 다(기준 판 뒤 커밋 0건, blob `61254dd`). `:69-70` 그대로다 — `fetch = min(1000, max(limit, limit * 5)) if q else limit` 만큼 `order_by(OntoObject.key).limit(fetch)` 로 받는다. 기본 `limit` 100(`:49`, MCP `list_tasks` 도 100 — HEAD `server.py:1494`)이면 key 순 앞 500행이다.
- `_rank`(`:91-102`)는 0 앞부분(key · task_code) · 1 낱말 경계 · 2 부분 문자열이고, `:104-105` 가 그 창 안에서만 정렬 · 절단한다. 그래서 창 밖(key 순 501번째부터)의 앞부분 일치는 순위에 들지 못한다.
- `:107-111` 응답 항목에는 `matched_by`(`:110`)만 있다. `match_kind` 는 리포의 `platform/` 전체에 0건이다.
- 10-27 회차 첫 고침은 `e2075f4`(순위 · project 거르개, 기준 판 안)이고, 시험은 `platform/backend/tests/test_ontology_kr0127.py:160` 의 'KR-16' 절이다.

#### 우리 쪽 맞물림

- 이 요청서의 HWAX 행 가운데 list_tasks 의 순위 · 칸을 바꾸는 것은 없다.
- HWAX 코드에 `match_kind` · `matched_by` 를 읽는 곳은 없다(KR-01 과 같은 대조). 행마다 match_kind 를 더해도 우리 쪽에서 고칠 코드는 없다. list_tasks 는 웹 챗이 상시로 묶는 도구라(KR-01 의 `_ONTO_CORE`) 짧은 질의의 순위 고침은 챗 답에 바로 닿는다.

## 끝나면

- **알릴 곳** — HWAX 포털 세션 `hwaxportal-a5`. 포털은 받은 답을 [`../outbound.md`](../outbound.md) 1절 '답' 칸과 `server-setup.md`(cae00 에서 사람이 할 일)에 옮긴다.
- **알릴 것**
  1. KR-23 — 묶는지 아닌지, 묶으면 어느 쪽(사람 승인 · 관리자 권한)인지. 묶었으면 그 커밋과, MCP 설명에 '등록은 사람이 승인한다' 를 실은 커밋.
  2. KR-01(다시) · KR-16(다시) — 커밋. 별칭을 어디에 담았는지(이미 오는 `properties.aliases` 를 읽는지, 새 칸인지), matched_by 의 새 값 이름(사람이 붙인 별칭 `alias` 와 가르는지), match_kind 의 값 이름 셋.
  3. 배포 — 파이썬만 바뀌면 cae00 은 update-all 의 git 받기로 가져간다(KooRemapper 10-27 보고 `docs/04-report/hwax-request-1027.report.md` — '코드 … origin/main. prod 는 update-all 이 가져간다' · '바이너리 안 바뀜 → 이 묶음은 Drive 불필요'). 화면이나 바이너리가 바뀌면 Drive 판 이름(`dist-…`)을, 마이그레이션이 생기면 그 번호를 함께 적는다.
  4. cae00 사람 몫 — 별칭을 새로 담는다면 이미 받은 행을 채우려고 전체 다시 받기(`sync_type(..., full=True)` — `sp_core.py:296-300`)가 필요한지, 재기동이 필요한지.
- **지켜 줄 것** — HP-52(포털, 고치는 중)는 씨앗 절차 둘(포털 `docs/procedures/fixtures/fullangle-drop-part-report.yaml:40` · `docs/procedures/fixtures/partial-impact-part-report.yaml:43`)의 `select` 를 `from: items` 로 고쳐, find_reports 봉투 `{items, total, reason, truncated}`(HEAD `platform/mcp_server/server.py:1286-1290`, 기준 판 `:1224-1228`)를 읽게 한다. 이 봉투의 칸 이름을 바꾸게 되면 먼저 알려 달라.
- **다시 볼 시험** — 요청서 7절에는 이 플랫폼 행이 없고, 끝 절 표에는 다시 볼 시험 칸이 없다. 7절의 DW-03(HA-29 뒤)은 StepForge run_job 시험이다.
