# 11-11 cae00 결과 보고 — 결정 · 까닭

> 원문 [request.md](request.md) · 계획 [PLAN.md](PLAN.md).

## R11-1 보고서의 기준 판은 core-link 병합 전이다

cae00 이 11-11 에 돌린 판(포털 `9f1b3ddc` 등)은 core-link 를 main 에 올리기 전이다. 보류(core-link CK-7)가 지켜졌다. 그래서 보고서의 HP-53 수 · 미리 보기는
게이트웨이 쓰기 낱말 link · edit · sync(SRC-14)가 들어가기 전 판으로 센 것이다. 다음 update-all 뒤에는 목록 밖 쓰기가 더 짚힌다. HP-53 은 dev 의 지금 판
(SRC-14 포함)으로 다시 센다.

## R11-2 PA-21 — 해석기 SIF 는 공유 `/data/SmartTwinSolutions/<해석기>/`

KooSolverContainer 가 코드로 답했다. `/opt/apps/sif` · `/opt/apps/sif-web` 은 헤드 로컬이고, 백엔드 preflight 는 헤드를 계산 노드로 쓰지 않는다. 지금 ste 에서
도는 앱(koo-sph · koo-openlb · condensation 대체 경로)이 모두 공유 자리를 쓴다. 새 앱 넷의 `app.yaml` · 래퍼가 `/opt/apps/sif` 를 박아 두었다. 그래서 고치는 판은
06 이 D-23 과 한 묶음으로 짓는다. 셋째 물음(앱 스크립트를 노드가 어떻게 읽나)은 condensation 잡의 성공 기록 하나로 갈리므로 운영에 되물었다(받은 편지함
2026-11-11 Q1).

## R11-3 HP-53 — dev 에도 있는 앱의 목록 밖 쓰기를 가르고, RA 도구는 도구마다 선택 칸으로

- dev 의 지금 판(SRC-14 포함)으로 다시 셌다. 넣은 것은 DynaForge writes 일곱 · confirm 셋, AIDataHub `draft_agent`, MX 백서 `upload_image_bytes`,
  WDA `approval_record`(WDA 세션이 쓰기라고 확인), SmartTwin writes 셋, StepForge `link_plm_tasks` 다. 마지막은 SRC-03 의 새 도구로, `dry_run` 이
  기본이고 MCP 로도 적용하므로 writes 다(StepForge `app/mcp_server.py` 의 `@register(mcp, MODIFY)`).
- 지우기 · 끊기 · 폐기 · 합치기 · 옮기기 · 타입 대응은 되돌리기 어렵다고 보고 confirm 에 넣었다. 나머지는 writes 다.
- 이름은 쓰기 꼴인데 읽기인 둘은 게이트웨이 읽기 목록에 넣었다. RA `run_saved_search` 와 리스크 `risk_propose_board_transform` 이다(게이트웨이 `38ac79f`).
- RA 는 dev 게이트웨이에 없어 이름을 dev 에서 맞대 볼 수 없다. 필수 목록(writes · confirm)에 그 박스에 없는 이름이 하나라도 있으면 동기화가 통째로
  멈춘다. 그래서 RA 쓰기 열여덟(writes 열하나 · confirm 일곱)은 도구마다 `needs_tool` 선택 칸으로 넣었다(SP 0.4.72 와 같은 꼴). 이름은 RA 최신판
  (origin/main `b552f09` — 받기만 하고 그 리포에는 쓰지 않았다)의 데코레이터 도구와 견줘 48개 모두 있음을 확인했다.
- DocForge 운영자의 RA 선택 앱도 같은 꼴로 RA 운영자의 쓰기 · 확인 전부(40)를 도구마다 칸으로 넣었다.
- 앱이 통째로 없으면 동기화 알림이 칸마다 같은 앱 이름을 적었다(`reportarchive, reportarchive, … 외 33개`). 한 번만 적게 고쳤다
  (`sync-he-personas.py` `_with_optional`).
- dev 대조(게이트웨이를 새 읽기 목록으로 다시 띄운 뒤)에 남은 알림은 둘이다. StepForge onto_* 셋은 C-30 그대로다 — MCP 로는 미리 보기만 되고 적용은
  챗의 REST 다리 확인 카드다. Laminate 둘은 Laminate 0.29.0(도구 43개 모두에 표지)이 Drive 에 오르면 사라진다.

## R11-4 SignalForge cae00 알림 · 벡터 — 사용자 결정 넷, 모두 권장안(11-11)

SignalForge 세션이 켜는 길을 제안했다(알림 ① dev 계산 → 병합 · 벡터 ② cae00 cron, ③ cae00 Redis · beat 는 권하지 않음). 사용자가 정할 넷을 선택지로
물었고 넷 다 권장안을 골랐다.

| 물음 | 고른 것 | 버린 것 |
|---|---|---|
| cae00 화면에 dev 운영 알림 넷(수집 상태 · 운영 상태 위반 · 운영 감시 · 백업 실패) | **가린다 — 결함 급등만** | 보인다(dev 수집이 멈추면 cae00 도 안다) |
| 지표 규칙 다섯(dev 에서도 평가가 안 걸려 0건) | **지금은 안 켠다** | dev 에서 켠다(병합으로 cae00 에도) |
| 바깥 웹훅 | **dev 에서만**(cae00 은 웹훅 주소를 비운다 · 보낸 표시가 병합으로 따라간다) | cae00 에서만 · 보내지 않는다 |
| cae00 ollama + bge-m3 | **둔다 — cae00 cron 증분**(2시간마다 600초) | 지금은 안 둔다(낱말 검색만) |

- 가리는 자리(병합에서 빼기 · 화면에서 거르기)는 SignalForge 판단에 맡겼다. 다만 cae00 이 그 알림을 다시 보내거나 세지 않게 했다.
- ollama 설치 · cron 한 줄은 cae00 사람 몫이다. SignalForge 착지 알림을 받으면 받은 편지함에 싣는다.

## R11-5 HP-64 — 병합 뒤 운영자 되돌리기를 update-all §3 이 저절로(병합 `c0f454ba`)

cae00 요청 (나)를 그대로 지었다. 새 모드 `sync-he-personas.py --backup <폴더>` 와 §3 끝의 차례(미리보기 → 백업 · 개수 확인 → `--apply` → 다시 미리보기)다.
요청서와 다르게 정한 것이 셋이다.

- **미리보기가 먼저다.** 어긋남이 있을 때만 백업 · 반영한다. 어긋남이 없는 실행은 백업도 남기지 않는다(✓ 한 줄).
- **정본에 없는 he-* 는 세지 않는다.** 백업에는 넣는다. 11-11 cae00 은 행 21 · git 운영자 19 였다. 남는 둘이 정본에 없는 행이면 글자 그대로의 '개수가
  같아야 한다' 는 실행마다 막힌다. 그래서 '합친 정의의 운영자가 다 들었나' 로 센다.
- **덧씌우기가 깨졌으면 반영하지 않는다.** 깨진 덧씌우기는 버려지고 기본 정의로 돈다. 그대로 `--apply` 하면 박스의 덧씌우기 고침을 기본 판으로 덮는다.

알고 받을 것.
- 저절로는 운영자를 새로 만들지 않는다. 새 운영자(미리보기 `+`)가 있으면 ⚠ 로 멈추고 사람이 `--apply` 한다.
- 어느 박스에도 행이 생길 수 없는 운영자가 정의에 있으면 실행마다 멈춘다. 그 박스 덧씌우기에서 `null` 로 뺀다. 지금은 없다 — dev 가 만든 행은 병합으로
  cae00 에 오고, cae00 에만 있는 앱의 운영자는 cae00 이 만든다.
- 되돌리는 명령은 따로 없다. 백업 파일의 칸을 PATCH 한다. 백업은 `daily/` 밖이라 세대 정리가 지우지 않는다(한 벌에 100KB 안팎).
- AIDataHub 를 못 읽으면 모름으로 다루고(rc 2) 반영하지 않는다. 0건 백업(11-09 의 다른 칸 거르기)도 여기서 막힌다(rc 1).
- 시험은 새 단위 8 · 구역 12(진짜 스크립트를 가짜 게이트웨이 · AIDataHub 와 임시 백업 자리에 돌린다)이고, 사본에서 코드를 13가지로 일부러 깨 모두 잡혔다.
  전체 회귀는 4,628 통과 · 실패 2(ste_doctor · tlscert — 앞선 기준 판에도 있던 것)다.

## R11-6 넘긴 것의 답 — KR-24(KooRemapper 중간 소식, 11-11)

- `git describe --dirty` 가 늘 `-dirty` 였던 것은 추적되는 툴 상태 폴더 `.bkit/` 때문이다. 고친 판은 `.bkit/` 를 뺀 소스 변경이 있을 때만 `-dirty` 를 붙이고,
  worktree 줄을 '깨끗함 · 툴 상태(빌드와 무관) · 추적 안 하는 파일(빌드에 안 든다)' 로 갈라 적는다(KooRemapper 가지 `corelink-src08-11` `ba34e8b` — 다음 dist 에 든다).
- 보고서의 `platform/infra` 차이는 빌드에 들지 않았다. 추적 안 하는 SIF 백업 두 개(`api.sif.bak-…` · `mcp.sif.bak-…`)다. 바이너리는 debian:12 빌더에서
  추적 소스로 짓고 cli.sif 도 그 백업을 쓰지 않는다. 백업은 사람 것이라 지우지 않았다.
- 같은 소식에 SRC-08(지음 · 적대 검토 중) · SRC-09 ~ 11(지음)과 그쪽 사용자 결정(11-11)으로 더 짓는 하나(사람이 손으로 끊은 과제 잇기는 자동 잇기가
  건너뛰고 결과 줄에 그 수를 붙인다)가 있었다. 끝 알림은 검토 · 배포 뒤에 따로 온다.
- 2026-11-09 Q3(stcx Post v51) · Q5(전처리 v135 SIF)를 누가 깔지는 그쪽이 사용자에게 묻는다.

## R11-7 StepForge 착지(여섯째 묶음 D-684 + core-link D-685, 11-11) · ST-13 답 · 단언 길 대조

- 판 — Drive `dist-20261111-164231Z/` + `latest/`. `step_forge.sif` 의 **파일 sha256** `00c86554b970…`(dev 허브 사본으로 다시 셈 — 같다), **허브 `.sif.hash`(빌드
  캐시 열쇠)** `4d981c04f134…`. main 끝 `d2d716cb`(코드 `50b96304`, 뒤는 문서 하나) · SP 서브모듈 `7744159`(0.4.83). 전체 회귀 7345 실패 0. Drive 드리프트 ✓.
- dev 게이트웨이 `/tools-map` 에 `link_plm_tasks` 가 쓰기로 보인다(StepForge 도구 193). 운영자 writes 에는 HP-53 에서 넣었다(R11-3).
- 단언 길을 두 리포 코드로 맞대 봤다. 발급 `POST /api/auth/sso` · 머리 `X-Heax-Gateway-Secret` · 주체 머리 `X-Hwax-Delegate-Email` / `X-Hwax-Delegate-Service`
  (작업 이름 꼴 `^[a-z0-9][a-z0-9-]{0,39}$` — 게이트웨이도 같은 꼴로 받는다) · 답 `{token: sfsso_…, expires_in}` · 쓰기 머리 `X-Heax-Sso-Assertion` 이 맞는다.
  dev 는 양쪽에 비밀 줄이 없어 발급이 404 다(StepForge 라이브 확인) — 실제 단언 쓰기는 cae00 에서 비밀을 넣은 뒤 처음 돈다.
- 맞대다 찾은 것 — 게이트웨이 안내 네 곳(거절 글 · provision 의 ○ 줄 · 주석 둘)이 '비밀은 StepForge 의 `STEPFORGE_GATEWAY_SECRET` 과 같은 값' 이라고 옛
  설계를 적고 있었다. 맞출 값은 StepForge `secrets.env` 의 `STEPFORGE_SSO_SECRET`(발급 비밀이자 HMAC 키 — 포털 신원 검증의 `STEPFORGE_GATEWAY_SECRET` 과
  따로)이다. 포털 update-all 주석과 server-setup 은 맞게 적혀 있었다. 고치고 시험 둘로 묶었다(게이트웨이 `4c56486` · 전체 1,036 통과 · dev 재기동).
- 알고 받을 것(받은 편지함에 싣는다).
  - StepForge 가 193 도구 전부의 입력 스키마에서 pydantic `title` 을 빼고 92 도구의 설명을 줄였다. 그래서 **사람이 기록한 절차 가운데 StepForge 단계가 든
    것은 다음 실행에서 '스키마가 바뀌었다 — 자동 진행하지 않는다' 로 멈춘다.** 그 단계를 다시 기록해 저장한다. 씨앗에서 들인 절차는 지문이 없어 멈추지
    않는다(dev 는 StepForge 단계가 든 절차 둘이 다 씨앗이라 0).
  - 앱 안 자동 실행이 생겼다 — 규칙 단 과제 잇기 · 앞 판 match · 채우기 잡(증명만). 끄기는 StepForge 배포 설정 `STEPFORGE_CORE_LINK=off`.
  - 서비스 허용은 셋이다(`/api/plm-sync` — `full` 까지 · 규칙 단 `/api/onto-link` · 증명 규칙 `/api/onto-fill`). 서비스 link 줄은 `state: auto|candidate` 가 있어야 한다.
  - `whoami.access` 에 `sso_person` · `sso_service` · `sso_decided_at`, 잡 행에 `job_status.actor`(이메일 · `system:<작업>`)가 생겼다.
  - 온톨로지 쓰기 셋(`onto_define` · `onto_put` · `onto_link`)은 여전히 MCP 적용을 받지 않는다(C-30 그대로 — 적용은 REST 다리의 사람 단언).
- ST-13 답 — 공개 표가 덮지 않은 여덟은 일부러 뺀 것이 아니라 아직 덮지 않은 그림 · 보고 도구다(`carryover_report` · `dimension_chart` · `dimension_view` ·
  `section_atlas` · `section_batch` · `section_batch_result` · `section_pair_view` · `stackup_figure`). 짐작한 `onto_*` · `list_fill_rules` · `save_fill_rule` 은 이미
  덮였다(185 / 193). 다음 판에 `system_capabilities.disclosure` 에 빠진 이름 칸을 더하고 여덟을 덮는다.
- ST-14 — 판마다 DB 이행을 셋 경우로 따로 보낸다(오늘 안). 그 답 전에는 **운영 사본을 옛 판으로 되돌리지 않는다.**

## R11-8 SignalForge 착지(알림 · 벡터, 11-11) · 지표 규칙도 가린다(사용자 결정)

- main `7137816`(SIF · Drive 없음 — cae00 은 update-all 로 받는다). 병합이 결함 급등 알림만 싣고(`SF_MERGE_ALERT_RULES` 기본 `defect_anomaly` · 규칙은 이름으로 ·
  보낸 표시 `merged`), 발송기가 `merged` 를 건너뛰며(다시 보내지 않기 둘째 겹 — 첫 겹은 cae00 웹훅 비우기), 백엔드 `ALERT_HIDDEN_RULES` 로 목록 · 최근 알림 ·
  운영 모니터링에서 뺀다(행은 지우지 않는다). 벡터는 `scripts/embed-new.sh`(cron 증분 · 처음 채우기 · `--status`). cae00 문서는 그쪽
  `docs/DEPLOY_CAE00_2026-11-11-alerts-vectors.md` 다.
- 시험 — 병합 통합 14/14 · 발송기 실제 SQL · crawler 2015(실패 4 는 전부터) · MCP 189/189 · dev 실측(화면 그대로 · 증분 85행 4.3초 · 맞춰 보기 12/12).
- 그쪽이 사용자 몫으로 남긴 하나를 물었다. cae00 운영 모니터링에 꺼 둔 지표 규칙 다섯이 'silent' 로 남는다 — **가린다(결함 급등만)** 를 골랐다(권장안).
  `ALERT_HIDDEN_RULES` 에 운영 알림 넷과 지표 규칙 다섯을 함께 둔다. 나중에 dev 에서 지표 규칙을 켜면 cae00 에서는 그 목록에서 빼야 보인다.
  그쪽이 문서에 넣었다(`0a8b5ce`) — `ALERT_HIDDEN_RULES=collection_health,ops_status_violation,operations_monitor,backup_fail,anomaly_z_high,negative_rate_spike,new_term_spike,platforms_negative_share,platforms_negative_share_watch`. 앞서 넷만 넣은 박스도 그 줄을 지우고 다시 쓴다.
  검증은 규칙 목록 · 운영 모니터링 모두 `defect_anomaly` 하나(첫 병합 전이면 비어 있다)다. 그 알림까지 cae00 에 실으려면 `SF_MERGE_ALERT_RULES` 에도 더한다.
- cae00 사람 몫(받은 편지함에 싣는다) — ollama · bge-m3 확인(`/api/tags` 에 `bge-m3:latest` · 임베딩 길이 1024 · `ollama ps` 의 GPU/CPU), 처음 채우기 한 번
  (GPU 면 약 1.5시간, CPU 면 `embed-new.sh 300` 으로 건/초를 재어 셈한다), cron 한 줄(2시간마다), 끝났는지 `--status` 의 `remaining: 0`.

## R11-9 ST-14 답 — 운영 사본을 되돌려야 하면 판만 되돌린다(DB 백업으로 되돌리지 않는다)

- 셋 경우(f1d9932 DB 에 2f5e903 · d2d716cb DB 에 f1d9932 · d2d716cb DB 에 2f5e903) 모두 옛 판이 옮긴 DB 로 뜬다. 이행은 더하기만 하고 옛 칸 값은 안 바뀌며
  옛 판이 DB 판을 보고 거절하는 자리는 없다(`user_version` 0). 백업 DB 로 되돌리면 그 사이 데이터를 잃는다. StepForge 가 빈 DB 를 새 판으로 옮긴 뒤 옛 판으로
  띄워 실측했다(운영 크기 DB · 허브 실서버로는 안 돌렸다).
- 함정의 뿌리는 이행 표식이 한 번만 붙어, 되돌린 판이 쓴 행에는 새 표식이 없다는 것이다. 그래서 지킬 것이 있다 — 되돌리기 전(도는 잡을 끝내고 대기 잡을
  비운다 · `fold` · `variant` 인자를 실은 대기 잡은 옛 판이 그 인자를 버린다), 되돌린 동안(대응 기록을 새로 남기지 않는다 · 자체 저장소 선이 걸린 과제를
  지우지 않는다 · 규칙이 이은 과제에 개정을 손대지 않는다 등), 다시 올린 뒤(첫 기동은 `STEPFORGE_CORE_LINK=off` · `link_plm_tasks(dry_run=true)` 로 먼저 본다 ·
  규칙 줄에 남은 개정을 다시 정한다 · 그 기간의 대응 기록에 match 를 다시 건다).
- 정본은 StepForge 리포 문서로 두기를 청했다(다음 판에서 행에 판 표시를 지으면 지킬 것이 준다 — 한 곳만 고치게). 받은 편지함에는 요약과 그 링크를 싣는다.
- 정본이 섰다 — StepForge `docs/OPS-ROLLBACK.md`(`94eaa05b`). 처음 답과 달라진 것이 넷이다. 규칙 줄을 찾는 SQL 이 넓어졌고(`decided_at IS NOT NULL` —
  개정 이름뿐 아니라 앞 판 · 상태 · 메모만 고친 줄도 잡는다), 고치는 호출이 `set_revision(project_id=…, note=<지금과 다른 글>)` 로 못 박혔고, 대응 기록은 유닉스
  초로 견주며(날짜 글로 견주면 0줄 — 되돌릴 때 `date +%s` 를 적어 둔다), `STEPFORGE_CORE_LINK=off` 는 앱 환경 변수라 켜고 끌 때마다 앱을 다시 띄운다.
  운영이 칠 명령은 받은 편지함에 옮기지 않고 그 문서를 가리킨다.
- 이 문서 커밋으로 StepForge main 이 `d2d716cb` → `94eaa05b` 가 되어 SIF 빌드 캐시 열쇠가 바뀐다(코드는 같은 `50b96304`). 허브가 다시 짓고 사용자 승인으로 Drive 를
  다시 올린 뒤에 받은 편지함 글을 쓴다 — 그 전에 cae00 이 update-all 하면 허브가 열쇠가 다른 SIF 를 띄우지 않는다.
- 다시 올렸다(사용자 승인) — Drive `dist-20261111-204655Z/` + `latest/` · main `94eaa05b`. **파일 sha256** `319eab5c127f…` · **허브 `.sif.hash`(빌드 캐시 열쇠)**
  `ac1b702c6c1f…` — dev 허브 사본으로 둘 다 다시 셈, 같다. 드리프트에서 step_forge 는 풀렸다. StepForge 는 cae00 이 이 판을 받을 때까지 main 에 올리지 않는다.

## R11-10 HH-17 답 — `root_host` 가 null 인 것은 의도다(DocForge 0.3.2 가 안내 한 줄을 붙인다)

- cae00 이 DocForge 에 물은 낮은 물음이다(`docforge_list_inputs` 가 컨테이너 안 경로만 주고 `root_host` 는 null — 그 경로로 convert 는 잘 된다). 사람 결정이 아니다.
- DocForge 가 답하고 고쳤다(`15d9bfe` · 판 0.3.2 `ae3ca51`). `root_host` 는 박스 값 `DOCFORGE_HOST_DATA_DIR` 이 없으면 null 이 맞고, 목록 응답에 'path 를 그대로
  convert 에 넘긴다' 는 note 를 붙였다.
- 0.3.2 는 DocForge main 에 있고 배치(release)는 그쪽 사용자 승인 뒤다(origin/release 는 0.3.1 `bd79e79`). 이번 라운드에 실을지는 사용자가 DocForge 세션에서 정한다 —
  안 실어도 cae00 은 0.3.1 로 변환이 된다.

