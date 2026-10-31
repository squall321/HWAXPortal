# 10-30 요청 — 다른 플랫폼에 보낸 것 · 사람이 보낼 것

요청서 정본 [`../request_261030.md`](../request_261030.md). 행의 글(무엇이 · 근거 · 할 일)은 정본에 있고, 보낼 때도 그 글을 그대로 붙였다.
답이 오면 이 표의 '답' 칸과 [`server-setup.md`](server-setup.md)(cae00 에서 사람이 할 일)에 옮겨 적는다.

## 1. 세션으로 보낸 것(10-30 KST, 포털 세션 hwaxportal-a5)

| 받는 곳 | 행 | 덧붙인 것 | 답 |
|---|---|---|---|
| SignalForge `signalforge-c6` | SG-04(다시) · SG-19 | HA-33 이 `{results, notes}` 를 펼친다 — 칸 이름을 지켜 달라. 세션이 둘이라 c6 에만 보냄 | 10-30 끝 — SignalForge main `0e2ac46`(SG-19) · `ec40075`(SG-04 주의 칸) · `f004cd0`(cae00 적용 문서 `docs/DEPLOY_CAE00_2026-10-30.md`). SG-19 — 요청서의 두 추정(시맨틱 적재 · 매처 사전)은 아니었고 시간은 거의 SQL 이었다(한국어 동의어 경로가 voc_records 전체를 경로마다 ILIKE 로 훑음). 한국어 원문 경로를 한 번에 미리 훑고(상한 6초 · 동의어 묶음 10분 캐시) 본 SQL 에 행 id 를 넘김, resolve 키워드 건수는 2.5초 상한(넘기면 5% 표본 어림 — `keyword_hits_exact` false), 결과는 예전과 같음(A/B 총수 · 상위 10). dev 실측 search_voc 2 ~ 3초 · resolve 0.4 ~ 1.4초. 더 줄이려면 한국어 글만 담은 좁은 표 · 색인(스키마 변경 — **사용자 결정**). SG-04 — 풀이(제품 코드)는 그대로, `resolve_product_keyword` 에 `plm_caution{products, named_projects, foreign_projects, note}` 와 note 끝 '주의 — …', search_voc · semantic_search 는 notes 에 '주의 — …' 한 줄, 거울 색인이 별칭을 `properties.aliases` 에서도 읽음. 데이터 결정(안 A · B · C)은 **사용자 몫** — 안 A 의 다시 태깅 범위 SQL 이 문서 3절. 봉투 칸 이름은 그대로(HA-33). **cae00 사람 몫** — update-all 로 받은 뒤 sf-mcp · sf-backend 를 워치독 락을 쥐고 하나씩 재기동(문서 1절 명령, 'sf-mcp semantic import ok' 확인) → 문서 2절 확인(시간 · plm_caution, 실제 이름은 cae00 `~/ontology-test/`) |
| DocForge `docforge-f6` | HH-14 | HA-28 이 읽을 docforge_status 의 끝 · 도는 중 칸, 새 목록 도구에 readOnlyHint | 10-30 끝 — DocForge main `e72cbe5`(도구) · `ab5547e`(판 0.3.1), **배치(release · HEAXHub 등록 사본 · SIF · Drive)는 그 세션의 사용자 승인 대기**(cae00 release 는 아직 `3ba0f6f` 0.3.0). ① 새 도구 `docforge_list_inputs()`(인자 없음 · readOnlyHint) — 운영자 입력 상자(SIF `/data/inbox`, 호스트 `~/Projects/HEAXHub/var/app_data/doc_forge/inbox/`)와 바로 밑 폴더, 응답 `{root, root_host, total, truncated, files:[{path, name, folder, bytes, format, modified}]}` 새것부터 200개, `files[].path` 를 convert 에 그대로. 업로드 스테이징은 나열하지 않음(남의 파일 이름이 보여서 — 요청과 다른 점, 근거 DocForge R-D47). ② docforge_status — `status` queued · running / done · failed · cancelled, `progress` 0 ~ 100, `stage` S0 ~ S7, `error`; **도구 오류는 `{ok:false, error, status:403}` 처럼 `status` 가 숫자 — 숫자면 기다리기를 끝낸다**, 잡은 한 번에 하나라 queued 는 앞 잡 대기. ③ readOnlyHint 는 읽기 넷(capabilities · list_inputs · status · package)에만. ④ 페르소나 `he-doc-docforge` 고침 셋(key_tools 에 list_inputs · can 의 맡기기 줄 · pitfalls 의 path 줄)은 **0.3.1 이 cae00 게이트웨이에 실린 뒤**(동기화가 없는 도구 이름에서 멈춘다 — 판단 C-8). ⑤ cae00 사람 몫 — 새 박스 값 없음, 0.3.1 받은 뒤 `/apps/doc_forge/api/v1/capabilities` version 0.3.1 · 게이트웨이 `/refresh` 뒤 `docforge_*` 여섯, OB-94 시험 파일은 위 상자에 평문 pptx 하나, dev 상자는 비워 둔다(build-all 이 dev 앱 데이터를 cae00 에 심는다) |
| StepForge `stepforge-d4` | ST-12 | HA-29 카드에 실을 시작 전 작업량을 셀 길이 있는지, HA-28 이 읽을 상태 칸 | 10-30 받음 — ① 시작 전 작업량은 이미 있는 읽기 도구 `estimate_cost(project_id, job, args)`(형상을 읽지 않고 DB 값만, 칸 `expected_s` · `cost_basis` · `gateway_verdict`(over · may_exceed · under · no_basis) · `basis_note` · `advice`) — ST-12 (2)가 판 전체 작업량 칸을 여기와 run_job 시작 응답에 더한다(칸 이름은 짓고 알림). ② `job_status(job_id)` 의 `status` 는 다섯 값뿐 — pending · running(도는 중) / done · failed · cancelled(끝)(처음 답의 queued 는 틀렸다고 10-30 정정 — `ff308d1` app/jobs.py · app/mcp_server.py 상태 글자 전수 · 운영 DB jobs 행 근거, 취소 요청은 상태가 아니라 따로 칸 `cancel_requested` 이고 그동안 running 그대로, 모르는 값은 '도는 중' 이 아니라 '모름' 으로 받기를 권함), `progress` 0 ~ 100, `error` · `ended` · `result`, 판 전체 측정은 수십 분 — 상한을 넉넉히. ③ ST-12 (1) 합치기 진행률은 OCC 한 호출이라 묶음 합치기를 실물 큰 판에서 재 보고 정함, (3) owner 는 원천에서 가림. 지금 다른 묶음(온톨로지 그래프 도구) 착지 중이라 ST-12 는 그 뒤 판 · **10-30 끝 — StepForge main `b2c70f1`(D-650), Drive `dist-20261030-135126Z`**(온톨로지 그래프 도구 일곱 D-649 도 같은 판). (1) 합치기는 GIL 을 쥐어 안쪽을 못 세므로 곁 프로세스가 경과 시간으로 10 → 90(90 에는 닿지 않음) · 1분마다 '[합치기] 살아 있음' 로그 · `job_status` 에 `log_last`(묶음 합치기는 RC 211형상에서 RSS 29.7GB OOM 이라 버림). (2) `run_job` 응답과 `estimate_cost(job="measure", args={tool, args})` 에 `work_outlook`(stage · tool · shapes · box_pairs · model_s · model_note · model_why · seen_s{n, median_s, max_s} · holds_runner · runner_slots · progress · note) — **하한 초는 정직하게 낼 수 없어 싣지 않음(모형 값은 하한도 상한도 아니다, 실제/모형 0.1 ~ 1.2) — HA-29 카드에는 `model_s` 를 '예상 시간' 이 아니라 '모형 값' 으로, 가장 나은 근거는 `seen_s`**. (3) MCP `list_projects` · `get_project_meta` · REST `/api/projects` · `/api/list-projects` 의 owner 는 가림(웹 과제 상세는 사람 화면이라 그대로). cae00 사람 몫 — `dist-from-drive.sh` 로 step_forge 교체(교체 전 도는 잡이 없는지 — 정지는 도는 잡을 worker restarted 로 끝낸다) |
| KooRemapper `kooremapper-4a` | KR-23(결정) · KR-01(다시) · KR-16(다시) | HP-53 이 레시피 도구를 DynaForge 운영자 writes 에, HP-52 가 find_reports 의 `items` 를 읽는다 | 10-30 답 — **KR-23 은 사용자 결정 그대로**(10-26 'LLM 자동 + 자동 관문', 게이트웨이에 바로 붙은 MCP 손님은 확인 카드를 지나지 않는다는 것을 듣고 정함). 관문을 MCP 설명 · TOOLS.md · SKILL.md 에 코드대로 적음(KooRemapper `0c1113f` — 정적 검사 · 자기 시험 · 앞 판 호환 · 이 판의 실데이터 실행 성공 1회 · '쓸모 있었다' 평가 1회, 코드는 격리 샌드박스에서만, 잘못 올라간 것은 사람이 `recipe_deprecate` 로 내림 — 지우는 길은 없다고 정정). cae00 사람 몫은 update-all 하나(MCP 도 다시 뜬다). KR-01 · KR-16 도 끝 — `f36270f`(백엔드) · `a3eff43`(MCP 설명): list_tasks 가 허브 별칭과 DynaForge 별칭 표를 함께 대조(matched_by alias · matched_alias · alias_source), resolve 에 previous_key · hub_alias 길, 걸린 것을 전부 받아 순위를 매긴 뒤 자르고 행마다 match_kind(prefix · word · substring) · 응답에 total · truncated. 같은 커밋에 SP 받는 쪽 규격 맞춤 (MCP 도구 82 → 85, 읽기 셋). cae00 은 update-all 의 git 갱신으로 받고 재기동 때 이관 0018 이 돈다. 화면은 다음 Drive 게시 — 그쪽 cae00 점검 문서에 확인 줄을 더해 다시 알린다. `items` 칸은 그대로 |
| MX 백서 `mxwhitepaper-26` | MW-01(다시) · MW-12 | HA-08 이 '…열리지 않았습니다' 도 받는다 — 문구는 그대로 둬도 된다 | 10-30 끝 — MXWhitePaper main `bb0a6a1`(MW-12) · `bd2e79b`(MW-01), 새 이미지(Drive) 없음 · update-all 의 git 받기로 간다. MW-01 은 `_wiki_switch` 가 켜짐 · 꺼짐 · 모름 셋 — http 모드는 모름이면 `wiki_*` 를 싣지 않고 10초마다 다시 봐 켜짐일 때 14개를 싣는다('부를 때 목록 바꾸기' 는 고르지 않음). 꺼짐 문구 '…열리지 않았습니다' 는 그대로(HA-08 이 받는다). MW-12 는 세 설명에서 upload_image 를 빼고 시험이 지킨다. cae00 사람 몫 없음 — 다만 f242254 뒤 W7 이 들어 있어 update-all 의 migrate.sh 가 이관 0059 · 0060(위키 표 · 알림 종류만 더함)을 돈다. 확인 — mxwp-mcp tools/list 의 `wiki_*` 0개(위키 꺼짐), MCP 가 API 보다 먼저 떴으면 로그에 '위키 도구를 미루고 다시 본다' 한 줄이 있고 '미뤄 둔 위키 도구 N개를 실었다' 는 없어야 맞다. dev 는 08:54 UTC 새 코드로 떴다(도구 40 · wiki 14) |
| SmartTwinExplorer `smarttwinexplorer-06` | PA-20 | cluster_info 가 이 리포에 있다. 게이트웨이 HG-22 도 메일 · 사설 IP 를 가린다 | 10-30 끝 — SmartTwinExplorer main `4f5e0e0`(GitHub 올림). 원천은 셋이었다 — cluster_info.controller 에 scontrol 의 `SlurmctldHost` 주소가 그대로 · 메일은 cluster_info 가 아니라 list_jobs · get_job_status 잡 행의 `submitted_by` · `source_ip` · 적대 검토가 찾은 get_job_status 로그 꼬리의 라이선스 서버 주소. 고침 — controller 는 호스트 이름만(이름 자리에 주소면 비움, 웹 · REST · MCP 모두), MCP `_scrub` 이 잡 · 결과 · 파일 꼬리 · 동기화 설정을 내는 도구 여덟에서 `submitted_by` · `source_ip` · `owner_id` · `sync_dir` 를 빼고 글 속 사설 IPv4 · 메일 꼴을 `[사설IP]` · `[메일]` 로 가림. 일부러 남긴 것 — REST `/api/jobs` 의 `submitted_by` · `source_ip`(웹 관리자 감사용, 비관리자는 자기 잡만) — 게이트웨이 HG-22 의 REST 다리 가림이 한 번 더 건다. 시험 173 통과 · dev 스테이징 VM 실측 0건. **cae00 사람 몫** — Drive `ApptainerImages:SmartTwinExplorer/staging` 번들(4f5e0e0)을 `infra/scripts/deploy-ste.sh` 로 반영(MCP `ste-mcp.service` 도 같이 재기동), 그 뒤 DW-12 다시 보기 |
| SmartTwinMCP `smarttwinmcp-4c` | PA-16 · PA-19(다시) | OB-92 · OB-34 · OB-25 가 이 둘을 기다린다 — PA-19 코드 몫만이라도 먼저 | 기다림 |

## 2. 사람이 보낼 것(이 세션이 닿지 않는다)

### AIDataHub — 살아 있는 세션이 없다

행 AD-01(다시) · AD-19 · AD-21 · AD-03(다시) · AD-04(다시) · AD-05 · AD-06(다시) · AD-07(다시) · AD-20 은 정본 끝 절 'AIDataHub' 표 그대로다.
AIDataHub 세션을 열 때 그 표와 아래 셋을 함께 준다. 10-27 회차의 코드 대조는 [`../request-1027/review-10-AIDataHub.md`](../request-1027/review-10-AIDataHub.md) 다.

1. **AD-04(다시)에 덧붙임 — 스위치 상태 칸.** 본문 검색 스위치(`AIDH_RECORDS_Q_BODY_SEARCH`)를 켤 때 기록 목록 · 검색 응답에 그 스위치 상태를 싣는다. 포털 HP-21(다시)이 그 칸을 보고 검색칸 문구를 바꾼다(포털 판단 C-3).
2. **AD-19 와 에이전트 HA-31 의 나눔.** 에이전트는 '추천 근거 · 기록 수' 처럼 다른 물음이 든 질문을 가로채지 않게 고친다. 추천 점수의 낱말 겹침 항(요청 낱말 · 신호 0 전문가)은 AIDataHub 몫이다.
3. **AD-21 과 포털 동기화.** 운영자 정의 동기화(`infra/scripts/sync-he-personas.py`)가 저장 뒤 500 에 첫 건에서 멈춘다. 포털은 저장 여부를 다시 읽어 확인하고 이어 가게 고치는 중이다(작으면 — HP-53 묶음). 근본 고침(저장 뒤 500 을 내지 않기)은 AIDataHub 몫 그대로다.

10-31 — 이 표의 코드 행은 이 세션이 맡아 끝냈다(판단 C-7 — `df7d45b`, 병합 고침 `6f496fa`). 1번(스위치 상태 칸)은 OB-89 를 끈 채로 두어 켜기 전까지 필요 없다(C-16). 3번의 cae00 원인 후보(병합이 표본 순번을 덮음)는 `6f496fa` 로 고쳤다(C-18). 데이터 단계는 [`server-setup.md`](server-setup.md) 5 · 8절이다.

### Datahub 플랫폼(허브 셋 — hwax-batch) · ARP · 사내 파트너

- DP-14 · DP-15(4절)와 DP-01 · DP-02 · DP-04 · DP-05 · DP-06 · DP-07 · DP-08 · DP-09(끝 절) — cae00 의 Datahub 요청서(12-Datahub-platform)와 같은 묶음으로 사람이 보낸다.
- AR-9 · AR-10(4절)과 AR-1 ~ AR-4(다시) — 요청서 6절대로 cae00 의 16-ARP-ODBHub-core-ontology.md 에 이어 붙여 사람이 보낸다. 보내기 전에 사람이 16 문서를 한 번 읽는다(O-9).
- 포털 쪽 짝 — 게이트웨이 HG-22 가 사람 칸 이름 · 메일 · 사설 IP 를 가린다. 글 속 이름(DP-08 의 검출자 · 작업자)은 게이트웨이가 꼴로 가르지 못해 원천 몫 그대로다. ARP 낙하 높이 단위(AR-9)는 고쳐지기 전까지 포털 HP-53 이 ARP 운영자 함정 줄('낙하 높이 칸은 단위가 없다 — 시험 조건은 cm')로 메운다.
- 10-31 — 위 두 묶음과 ODB 허브 요청([`../design-risk-review/ecad-1031/odb-hub-request.md`](../design-risk-review/ecad-1031/odb-hub-request.md))은 cae00 받은 편지함 [`../cae00-inbox/2026-10-31.md`](../cae00-inbox/2026-10-31.md) Q6 · Q7 로도 실었다. 보내는 것은 여전히 사람이다.

## 3. 10-31 — 보낸 것 · 받은 답(포털 세션)

### 3-1. 다른 플랫폼

| 받는 곳 | 무엇 | 답 · 상태 |
|---|---|---|
| SignalForge | 10-30 답의 뒤 — 공개 이력 · SP 킷 | **사용자 결정 10-31** — `ec40075` 가 든 공개 이력은 그대로 둔다(강제 push 없음, 판단 C-19). 이름을 걷는 정리 커밋 둘(`e8df7e3` · `d34f891`)은 그 세션이 올렸다. SP 킷은 3-2 |
| SignalForge | 그쪽 10-31 cae00 문서 | 올라왔다(`404fe42`) — cae00 차례는 [`server-setup.md`](server-setup.md) 3절, 읽기 결과는 받은 편지함 Q9 |
| MaterialTwinWeb | HEAXHub 요청의 HH-13 · HH-01 · HH-10 · HH-11 | 10-31 답 — **HH-13** 그쪽 main `a3563b6` 은 cae00 사본 `6e45b40` 보다 61 커밋 앞이다. **HH-01** `a3563b6` 에서 고쳤다(긴 재료 카드를 절 하나 크기 한도 이하의 절 여럿으로 — 그쪽 실 DB 에서 153장이 나뉘고, 6만 자 절 한도를 넘는 절 0 · 바뀐 글 0). 답할 때는 커밋 하나의 공개 범위를 사용자가 정할 때까지 push 를 기다린다고 했다 — 이 표를 쓰는 때(10-31 아침 KST) GitHub main 은 `a3563b6` 이다(ls-remote). **HH-10** 그 id 들은 그쪽 DB 에 없다(id 는 박스마다 다르다) — 자연 키를 cae00 에서 받는다(받은 편지함 Q1). **HH-11** 지금은 필요 없다 |
| DocForge | HEAXHub 요청의 HH-03 · SP 킷 | 10-31 보냄 — 답 기다림. 0.3.1 배치도 아직이다(GitHub release 는 `3ba0f6f` 0.3.0 그대로 — 10-31 ls-remote, C-8) |
| StepForge | SP 킷 | 10-31 보냄(3-2) — 답 기다림 |
| KooRemapper | SP 0.4.67 | 10-31 답 — 이미 최신이고 0.4.67 의 영향이 없다 |
| ReportArchive | SP 킷 | 10-31 보냄 — 자체 SP 어댑터가 있어 킷과 견주기를 청했다. 답 기다림(RA 리포는 그쪽 세션 몫이다 — 포털은 커밋하지 않는다) |
| SmartTwinMCP | PA-16 · PA-19(다시) | 10-31 다시 청했다 — 답 기다림. OB-92 · OB-34 · OB-25 가 이 둘을 기다린다 |
| SceneForge | (그쪽이 물어 옴) stcx CPU 렌더 파티션 | dev 박스에서는 모른다 — cae00 받은 편지함 Q2 로 넘겼다 |
| HEAXHub | 10-27 행 · 10-31 행 | 10-27 행 HH-02 · HH-04 ~ HH-09 · HH-12 는 이미 HEAXHub main 에 있다(`1dab32a` ~ `42d3b94`). 10-31 행 HH-14(운영 노드 터널로 가는 매니페스트 — 전환 창에서만 합친다) · HH-15(dev 박스도 그 매니페스트 넷을 쓴다 — 박스별 매니페스트 덧씌우기가 먼저) · HH-16 은 다른 워크플로가 짓는 중이다(번호는 10-30 요청서의 HH-14 와 다른 행 — 판단 C-23). ⟪자리 — 결과(커밋 · 판 · cae00 몫)가 오면 이 칸과 server-setup 9절 · 받은 편지함 Q8 에 옮긴다⟫ |

### 3-2. SP(StandardPlatform) 받는 쪽 킷 맞추기

- SP 최신은 `778db2f`(0.4.67 · 킷 2026-10-21)다(읽기 전용 사본으로 대조).
- StepForge · DocForge · SignalForge 는 10-14 킷(`f7485c0`)으로 받는다 — 올리기와 '작업을 시작할 때 SP 최신을 본다' 는 상시 규칙을 청했다.
- KooRemapper 는 이미 최신이고 0.4.67 의 영향이 없다고 답했다. ReportArchive 는 자체 어댑터라 킷과 견주기를 청했다.
- 세션은 다른 세션의 청으로 제 CLAUDE.md 를 고치지 않는다. 상시 규칙을 둘지는 **사용자가 세션마다 정한다**(판단 C-22).

### 3-3. cae00 에서 물을 것 · 사람이 보낼 것

받은 편지함 [`../cae00-inbox/2026-10-31.md`](../cae00-inbox/2026-10-31.md) 에 실었다(판단 C-20). 답은 사용자를 거쳐 이 표 · [`server-setup.md`](server-setup.md) 에 옮긴다.

- 이 박스에서 읽어 답할 것 — Q1(MaterialTwin 자연 키) · Q2(stcx CPU 렌더 파티션 — 노드 함께 쓰기는 stcx 운영에 넘김) · Q3(SG-04 안 A 범위 — 사용자에게만) · Q4(ODB 허브 입구 도구 노출 꼴) · Q5(자기검증 수치) · Q9(SignalForge 10-31 cae00 문서의 읽기 결과 — 사용자에게만).
- 사람이 보낼 것 — Q6(ODB 허브 묶음 읽기 요청) · Q7(Datahub 플랫폼 · ARP 행 — 위 2절).
- 자리 — Q8(HEAXHub 10-31 전환).
