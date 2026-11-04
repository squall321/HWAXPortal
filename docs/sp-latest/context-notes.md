# SP 최신판 따라가기 — 결정 기록

계획은 [PLAN.md](PLAN.md), 할 일은 [checklist.md](checklist.md)다. 날짜는 KST.

**SL-1 0.4.72 를 읽고 게이트웨이부터(11-03).** SP `ab41cff`(0.4.72 · 키트 2026-11-03)를 0.4.67 과 견줬다. 새 MCP 도구 일곱 가운데 `lineage_repin` 은 설명에
'옮긴 고정은 이 도구로 되돌릴 길이 없다' 고 적혀 있는데, SP 의 `@tool()` 은 표지(`readOnlyHint` · `destructiveHint`)를 달지 않고 이 도구는 MCP 관리자 전용 목록
(`DESTRUCTIVE_TOOLS`)에도 없다. 게이트웨이는 표지가 없으면 이름 낱말로 쓰기를 가리는데 repin 이 낱말에 없어 읽기로 읽혔다 — 쓰기 낱말에 `repin` 을 더했다(게이트웨이
`a3ae08b2`, 시험은 새 도구 일곱의 판정 — 쓰기 셋 · 읽기 넷 · 모두 루틴 울타리 밖). 같은 병합에 검색 열쇠 '단면 비교' 의 owner · source_fix 를 비웠다.

**SL-2 사용자 결정 11-04 — 허브 쓰기는 규칙대로 전부.** 0.4.72 허브의 바꿀 수 있는 도구는 49개인데 운영자 목록(10-30 HP-53)에는 일곱뿐이었다 — 나머지는 cae00
미리보기를 보고 사람이 정하기로 남겨 둔 자리다(docs/request-1030 C-15 ④). 웹 챗 확인 관문은 이 목록만 보므로 허브가 새 판이면 `relation_remove` · `bulk_edit` ·
`ontology_delete` 가 카드 없이 나간다. 사용자가 고른 규칙 —
- confirm(27) — 되돌릴 길이 없거나(`lineage_repin` · `relation_remove` · `jobs_purge`) · 사람이 판단하거나(`relation_proposal_decide` · `review_decide` · 별칭 둘) ·
  일괄이거나(`bulk_edit` · 가져오기 둘 · 되돌리기 묶음) · 정의를 바꾸거나(`ontology_*` 여섯) · 모두에게 미치는 설정(`platform_profile_update` · `datasource_save` ·
  `config_delete` · `metric_define` · `slide_template_save`). `object_restore` · `attachment_remove` · `job_cancel` 도 여기 — SP 가 관리자 전용으로 둔 것이고
  리스크 잡 멈추기(`risk_job_action`)와 같은 자리다.
- writes(15) — 하나씩 잇기 · 고치기(`relation_add` · `relation_propose` · `relation_update`) · 저장(`view_save` · `metric_alert_save` · 장표 둘) · 잡 시작
  (`metric_recompute` · `export_start` · `filestore_gc`) · 그 밖(`object_years` · `object_watch` · `metric_home` · `insight_manage` · `attachment_upload_prepare`).
  `filestore_gc` 는 SP 가 위험 도구로 두지만 이 호출은 세기만 하고 지우기는 `job_apply`(confirm)를 거친다.
- 넣지 않음 — `extension_call`. 읽기(GET)에도 쓰여 넣으면 확장 조회마다 카드가 선다.
- 칸 — 도구마다 `{"app": "rootdesigndatahub", "needs_tool": <도구>, "confirm"|"writes": ["rootdesigndatahub_<도구>"]}` 한 줄. 칸 하나에 여럿을 묶으면 `needs_tool`
  은 있는데 다른 이름이 없는 판(판 사이)에서 '이 앱에 없는 도구' 로 멈춘다. 관문(에이전트 서버 `_confirm_lists`)은 `needs_tool` 과 상관없이 선택 칸 목록을 늘 읽고
  접두를 뗀 꼴로 꼬리를 맞추므로, 형제 허브(failuretrace_ · caegroupdatahub_)의 같은 도구도 걸린다 — 에이전트 서버 시험 243 통과(이 정의를 짝 배치로 읽어),
  실제 관문으로 `failuretrace_lineage_repin` → confirm · `failuretrace_relation_add` → write · 새 읽기 넷 · `extension_call` → 목록 밖을 확인했다.
- 판 — 포털 `1dd1bd71`(병합 — `4ce5eb71`). dev 에이전트 서버가 재기동 없이 읽었다(`/health` `confirm_gate.lists` 쓰기 161 · 확인 114).
- 크기 — 허브 셋이 0.4.72 인 꼴에서 운영자 프롬프트 3,742자(상한 8,000). 10-30 판 허브면 빠진 도구 마흔둘이 알림 한 줄에 들어가 1,600자가 되어 앞 여덟만 적고
  '외 N개' 로 줄였다(목록 밖 쓰기 줄과 같은 `LOOSE_SHOW`).

**SL-3 미리보기의 '목록 밖 쓰기' 는 관문과 같은 셈으로(11-04).** 미리보기는 운영자 앱의 쓰기 꼴 도구가 노출 이름이나 접두 별칭으로 적혀 있는지만 봤다. 관문은 이름
그대로이거나 '_<이름>' 으로 끝나면 건다(접두를 뗀 꼴 포함). 그래서 정본 허브 접두로 적은 이름이 꼬리로 거는 형제 허브의 같은 도구를 미리보기는 '목록 밖' 으로 알렸다 —
허브 셋이 0.4.72 인 꼴에서 99개 가운데 70개가 거짓이었고, update-all §7 의 '운영자 앱에 writes · confirm 어디에도 없는 쓰기 도구' 줄이 늘 섰을 것이다. 대조를
`_gate_names`(거꾸로 점검이 이미 쓰는 것)로 바꿨다 — 이름 그대로이거나 그 꼬리면 적힌 것이다. 어느 목록의 꼬리도 아닌 쓰기는 형제 허브 것이어도 그대로 알린다(시험).

**SL-4 사용자 결정 11-04 — SP 에 표지를 달아 달라고 한다.** 게이트웨이 이름 낱말로는 바꾸는 도구 14개(`ontology_retype` · `ontology_promote` · `aliases_review` ·
`bulk_edit` · `bulk_edit_undo` · `bundle_undo` · `filestore_gc` · `datasource_sync` · `insight_manage` · `metric_define` · `metric_home` · `object_watch` ·
`object_years` · `review_undo`)가 읽기로 읽힌다. 막는 데는 쓰이지 않는다 — 루틴 울타리는 읽기로 확인된 것만 열고, 확인 관문은 SL-2 의 목록을 본다. 흔들리는 것은 검색
순위(쓰기 도구 내리기)와 미리보기 알림뿐이다. 게이트웨이 낱말(edit · undo · retype …)을 더하면 다른 앱 도구의 순위도 함께 바뀌어 평가 147쌍을 다시 돌려야 하므로
고르지 않았다. 요청서는 [sp-annotations-request.md](sp-annotations-request.md) — 표지는 SP 의 `DESTRUCTIVE_TOOLS` 에 `lineage_repin` 을 더한 것을 destructive
로 제안하고, `lineage_repin` 이 관리자 전용 밖인 것이 의도인지 묻는다. 건네는 것은 사용자다. 게이트웨이는 표지를 먼저 읽으므로 SP 가 달면 고침 없이 바로잡힌다.
- 표지가 달리면 함께 바뀌는 것 — 루틴 단계 · 심의 좌석의 읽기 울타리(`_routine_read`)도 표지를 먼저 본다. 지금 SP 읽기 60개 가운데 루틴이 쓸 수 있는 것은 이름의
  읽기 낱말로 열린 23개뿐이고(`object_resolve` · `graph_path` · 새 넷은 닫혀 있다 — 모르면 막기), 표지가 오면 60개가 저절로 열린다. 그것이 울타리의 설계(읽기로
  확인된 것만)대로라 막지 않는다 — 그 판이 오면 루틴 · 좌석에서 새로 열린 도구를 한 번 본다.

**SL-5 소비처(11-04).** DocForge 가 끝냈다 — main `ab0861d`(push), 배치 불요. `sp_core.KIT_VERSION = "2026-11-03"`, 층 1 은 판 표시만 다르고 새 칸(관계 종류의
effectivity · quantity_key · lineage_source)은 카탈로그째 담긴다. 선을 플랫폼 표에 넣는 곳이 없어 §6.2 · §9 는 걸리는 코드가 없고 규칙만 `sp_core.py` 머리에 적었다.
§2-3(관계 종류마다의 매핑)은 그 세션이 사용자에게 묻는 중이다(지금 받는 타입에 선이 없어 답이 와도 코드는 그대로). 시험장 8단계는 자동 모드가 GitHub 에서 받은 키트
코드(fake_sp.py · compare.py) 실행을 막아 돌리지 못했다 — 사람이 DocForge 리포에서
`DOCFORGE_SP_KIT_DIR=<SP ab41cff 의 backend/app/modules/coreapi/kit> .venv/bin/python -m pytest -q tests/test_sp_testbed.py` 로 돌린다(거울 57 · 전체 283 통과,
시험장 둘은 건너뜀).
- SignalForge 가 끝냈다(11-04) — main `07b3f1a`. 「관계 매핑」(§2-3 — 받는 관계 `plm_derived_from` 을 쓸지)은 사용자가 맡은 탭(7f)을 못 찾아 다른 탭(c6)에서 답했다 —
  '지금대로 안 쓴다'(선은 사본에 받아만 두고 색인에 안 쓴다 · 키트 판만 올린다). 7f 가 작업 트리에 넣어 둔 키트 파일을 c6 이 그대로 써서 마쳤다. 키트 `crawler/sp_core_kit` =
  SP `ab41cff` 의 `coreapi/kit`(diff 없음), 판 표시 2026-11-03, §6.2 · §9 는 선을 넣는 코드가 없어 해당 없음(쓰게 되면 §2 물음부터). 시험장 8단계 통과(새 가짜 SP —
  선에 유효 기간 · effectivity · quantity_key · lineage_source), crawler 1898 · MCP 189 통과(옛 실패 4 그대로). cae00 은 받기 코드가 그대로라 사람 몫이 없다 —
  update-all 로 받으면 다음 plm-sync 가 새 키트 파일로 돈다.
- 소비처 넷이 모두 키트 2026-11-03 이다(11-04) — DocForge `ab0861d` · KooRemapper `225da1b` · StepForge `ec721ef` · SignalForge `07b3f1a`.
- StepForge 가 끝냈다(a78, 11-04) — main `b9db3d0`(D-661 키트 — 받기 규칙 그대로 · 시험장 8/8 · 「절반 넘게 안 옴」 까닭 글을 §5.5 새 말로 · §8.1 선 확인표 자동 시험) ·
  `ec721ef`(D-662 그래프 — 새 읽기 셋 `onto_reach` · `onto_explode` · `onto_lineage`, `onto_neighbors` 의 `direction` · 선 `properties`, `onto_walk` rollup 셋, `onto_query` 선 칸 주소 ·
  `edge` 묶음 · `fields` 상한 10 · 값 20) · `ce478ca`(문서), Drive `dist-20261103-234515Z`(a77 까지 품는다), dev 라이브 도구 183. 그쪽 사용자 결정 넷 — 카탈로그 뜻대로 ·
  기간 저장 안 함 · 새 도구 셋 · 허브 관계는 전부 방향 있음. 포털 · 에이전트 · 게이트웨이 · 리스크 앱에는 `onto_*` 를 직접 부르는 코드가 없어(모델만 부른다) 상한이 깨는 곳이
  없다. dev 게이트웨이에 셋 다 읽기(`routine_read`)로 보인다. cae00 확인은 받은 편지함 2026-11-04 Q3.
- KooRemapper 가 끝냈다(11-03) — main `225da1b`, 서브모듈 `778db2f` → `ab41cff`, 층 1 `KIT_VERSION = "2026-11-03"`(받기 규칙은 10-21 판과 같아 코드는 그대로).
  선 반영 대조(§6.2 · §9 — 그쪽 `docs/01-plan/features/sp-receive-1103.plan.md`): 끝은 도착 타입으로 찾고 · SP 에서 온 연결만 끊고(사람이 이은 것은 그대로) ·
  선의 칸은 통째로 바꾸고 · 수량 칸 이름은 박지 않는다. 다른 점 하나 — 그쪽 개정 열쇠와 `revision_of` 선이 SP 과제 key 를 품는다(§9 「연결에 SP key 복사」 꼴,
  식별자가 바뀌면 같은 줄을 새 key 로 옮기고 시험 15항이 지킨다). §2 는 그쪽 사용자 결정(11-03 권장안) — 관계는 보이기만(읽기 전용) · 선의 뜻은 지금처럼 안 보임 ·
  개정 열쇠 설계는 그대로. 시험장 8/8 · §8.1 선 확인표(일부러 틀린 단정을 잡는 것 확인) · 백엔드 829 통과, dev API 재기동. Drive 판은 그대로(파이썬 · 시험 · 주석만)이고
  cae00 은 update-all 2단계(`deploy-all-from-drive.sh` — kooremapper 코드 받기 · 기동)로 들어간다. 실제 SP 연결 점검(그쪽 완료 조건 6)은 허브 주소 · `core:read`
  토큰이 생긴 뒤다.

**SL-6 SP main `d3b5aa1` — 맞출 것 없음(11-04).** 0.4.72(`ab41cff`) 뒤 한 커밋 — 자주검증 입력(svinput) 확장(ADR 0051 — 허브의 온톨로지 타입 위에 얹는 문제점 중심 입력 ·
열람 화면, 26 파일). MCP 도구는 그대로 110 이고(GUIDE.md 36줄 더함) 키트 `KIT_VERSION` 도 그대로다 — 소비처 · 게이트웨이 · 운영자 목록에 맞출 것이 없다. StepForge 는 a79 에서
서브모듈을 이 판으로 올렸다(키트 판 그대로 · 시험장 통과). 확장의 자리는 `extension_call` 로 닿는데, 그 도구는 읽기에도 써서 확인 목록에 넣지 않았다(SL-2) — 확장의 쓰기는
SP 가 관리자 전용으로 막는다(`DESTRUCTIVE_TOOLS`). cae00 허브를 이 판으로 올릴지는 그 화면이 필요할 때 허브 쪽이 정한다.
