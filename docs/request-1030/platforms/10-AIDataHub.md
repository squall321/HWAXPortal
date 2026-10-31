# 10 AIDataHub — 10-30 요청에서 할 일

- **받는 곳** — 살아 있는 AIDataHub 세션이 없다. 처음에는 사람이 이 시트를 그대로 넘기거나, 사용자가 정하면 포털 세션이 맡는 것으로 두었다. 사용자가 10-30 에 정했다(판단 [C-7](../context-notes.md)) — 코드 행은 HWAX 포털 세션 `hwaxportal-a5` 가 맡고, 박스의 데이터를 만지는 단계는 사용자 OK 뒤 사람 몫이다. 사람이나 새 AIDataHub 세션에 넘길 때도 이 시트를 그대로 쓴다.
- **어떻게 갔나** — 세션으로 보내지 않았다. [`../outbound.md`](../outbound.md) 2절 'AIDataHub — 살아 있는 세션이 없다' 가 행 목록과 덧붙일 셋을 적었고, 이 시트는 그 셋을 해당 행의 '우리 쪽 맞물림' 에 그대로 옮겼다. 그 뒤 판단 C-7 이 코드 행을 포털 세션에 맡겼다([체크리스트](../checklist.md) 3b). 이 시트를 쓸 때 AIDataHub 에는 형제 워크트리 가지 다섯(`wt1030/ad-agents` · `wt1030/ad-asof` · `wt1030/ad-drm` · `wt1030/ad-flat` · `wt1030/ad-rec`)이 있었고, 다섯 모두 `ac42bc6` 그대로라 커밋이 없었다. 행과의 짝은 가지 이름으로 짐작한 것이다.
- **요청서 정본** — [`../../request_261030.md`](../../request_261030.md) 끝 절 '이전 회차에서 남은 챗 · 디지털 워커 요청 (10-30 대조)' › 'AIDataHub(`ac42bc6` — 10-18 뒤 커밋 0)' 표다. 표는 8줄이고 행 번호는 9개다(AD-05 · AD-06(다시)는 한 줄). 맞물린 행은 1절 HA-31, 5절 OB-87 · OB-89, 끝 절 포털 HP-21(다시) · HP-53 · HP-54, 에이전트 서버 HA-11(10-27 행)이다.
- **cae00 기준 판** — AIDataHub `ac42bc6`(2026-10-18 21:37 UTC 커밋). 행이 가리키는 다른 리포의 자리는 에이전트 서버 `969e723` · 포털 `aec8e29` 기준이다.
- **이 박스(dev)에서 대조한 판** — AIDataHub main `ac42bc6`(`origin/main` 과 같다). 기준 판 뒤 커밋이 0이라 정본의 줄 번호가 그대로 맞고, 조금 어긋난 두 곳(AD-21 · AD-04)은 행 안에 적었다. 작업 트리에 남의 미커밋 변경이 2건 있어 열지 않았고, 대조는 커밋된 트리(`git show HEAD:…` · `git grep … HEAD`)로만 했다. 함께 읽은 판은 에이전트 서버 `969e723`(cae00) · main `7ca3a2e`, 포털 `aec8e29`(cae00) · main `bf5cd94`, MXWhitePaper `f242254` 다. 대조 시각은 2026-10-30 18:01 KST 다. 읽기만 했다(시험 · 재기동 · 데이터 · 고침 없음).
- **10-27 회차** — 코드 대조 [`../../request-1027/review-10-AIDataHub.md`](../../request-1027/review-10-AIDataHub.md)(그때 HEAD 도 `ac42bc6` 라 그 문서의 `파일:줄` 이 지금도 맞는다) · 요청서 [`../../request-1027/10-AIDataHub.md`](../../request-1027/10-AIDataHub.md).

## 할 일

먼저 행마다 코드인지 박스 데이터인지를 적는다. 박스 데이터를 만지는 단계는 사용자 OK 뒤다(판단 C-7).

| 행 | 갈래 | 누가 · 언제 |
|---|---|---|
| AD-01(다시) | 코드(하위 절 평탄화 · 박스별 다시 짓기 명령) + 박스 데이터(박스마다 다시 짓기 실행) | 코드는 포털 세션(C-7) · 실행은 사람 — dev 먼저, cae00 은 그 박스 병합 뒤, 사용자 OK 뒤 |
| AD-19 | 코드 | 포털 세션(C-7) |
| AD-21 | 코드 | 포털 세션(C-7) |
| AD-03(다시) | 코드 | 포털 세션(C-7) |
| AD-04(다시) | 측정(dev DB 사본의 `EXPLAIN ANALYZE`) + 덧붙임 1(응답에 스위치 상태 칸 — 코드) | 측정은 사람, 사용자 OK 뒤 · 덧붙임 1 은 C-7 의 '맡는 것' 에 들지 않았다 |
| AD-05 · AD-06(다시) | 박스 데이터(dev 원본에서 지우기 → 덤프 → cae00 은 OB-87) | 사람, 사용자 OK 뒤 |
| AD-07(다시) | 코드 | 포털 세션(C-7), 그 뒤 에이전트 HA-11 |
| AD-20 | 코드(합치는 길이 이행이면 박스 데이터도 바뀐다 — 추정) | 포털 세션(C-7) |

### AD-01(다시) · 중간 — MX 백서 카드의 1번 절이 빈다(하위 절 평탄화)

- **무엇이** — (중간) MX 백서 분석가 카드 154장의 1번 절이 비어, 챗 · 심의 근거에서 그 글이 빠진다.
- **근거** — `api_server/src/api/ingest/db_writer.py:201-202`(children 만 내려간다) — 이 파일에 subsections 는 0건이다(HEAD 대조). MX 백서 개발 답(reflection-1028/09 MW-07)이 '본문 빈 154장은 AIDataHub 평탄화 탓' 이라고 했다.
- **할 일** — 평탄화가 subsections 도 내려가게 하고, 박스마다 색인을 다시 짓는 명령을 둔다. 일정을 알려 달라.
- **출처** — 10-AIDataHub AD-01 · AD-14 · TODO-20261029 R-03

#### 지금 판에서의 자리

- HEAD `ac42bc6` 이고 `git log ac42bc6..HEAD -- api_server/src/api/ingest/db_writer.py` 는 0줄이다. 인용한 `:201-202` 가 그대로다 — `_flatten_sections`(`:69`) 안의 `walk` 가 `node.get("children")` 만 내려간다. 이 파일의 `subsections` 는 0건이다.
- `api_server/src` 에서 MXWP 의 `subsections` 를 읽는 곳은 요약을 본문에서 채우는 `services/sync_svc.py:200-201` 하나다(`ppt_converter/core.py` 의 `_extract_body_subsections` 는 이름만 비슷한 pptx 변환 함수다).
- 블록 글을 모으는 `_blocks_to_text`(`db_writer.py:209-248`)는 paragraph · heading · list · code · table 만 읽는다. 10-27 검토 N1 이 짚은 MXWP 블록(quote · callout · math · columns · tabs 등)이 빠지는 것도 그대로다.
- 박스마다 색인을 다시 짓는 명령은 HEAD 에 없다. 절을 다시 넣는 길은 적재 안의 `_resync_sections`(`db_writer.py:623`, 부르는 곳 `:486` · `:538`)뿐이고, 적재는 본문 해시 · 제목 · 요약이 같으면 건너뛴다(`:424-428`). 그래서 재동기화로는 절이 다시 지어지지 않는다(10-27 검토 AD-01 '권하는 길' 3).
- 다시 지을 때 updated_at 을 올리지 않는 스위치(`SET LOCAL aidh.keep_updated_at = 'on'`)는 이미 있다. 이행 0032 트리거(`alembic/versions/0032_embedding_m3_slot.py:56`)가 그 값을 보고, 임베딩 백필(`services/embed_backfill.py:362`)이 쓴다. updated_at 이 오르면 병합 우선순위가 뒤집힌다.
- 병합은 `record_sections` 를 updated_at 비교 없이 같은 (record_id, section_id) 면 dev 값으로 쓴다(`deploy/apptainer/merge-from-drive.sh:155`). 그래서 cae00 은 그 박스 병합 뒤에 다시 짓기를 따로 돌려야 남은 절이 걷힌다(10-27 검토 AD-01 '권하는 길' 4).
- MX 백서 쪽 꼴은 MXWhitePaper `f242254` `apps/api/app/schemas/document.py:2590`(`subsections: list[Section] | None`)으로 확인했다.
- 원인 (A) 병합 섞임과 (B) 평탄화 누락을 가르는 읽기 질의는 10-27 검토 AD-01 절에 있다. 박스 DB 에서 도는 것이라 이 시트는 돌리지 않았다(대조 못 함).

#### 우리 쪽 맞물림

- 코드(평탄화 · 다시 짓기 명령)는 판단 C-7 로 포털 세션이 고치는 중이다(`wt1030/ad-flat` 으로 보인다 — 아직 커밋 없음). 다시 짓기를 박스에서 실제로 돌리는 것은 사용자 OK 뒤 사람 몫이다(체크리스트 3b '실행은 사람 · OK 뒤').
- MX 백서 쪽은 원문 확인(MW-07)까지였고, 그 답이 원인을 AIDataHub 평탄화로 돌렸다(정본 근거 칸).
- 이번 회차의 HA- · HG- · HP- 행 가운데 이 행을 바꾸는 것은 없다.

### AD-19 · 중간 — 추천 점수가 요청 낱말에도 점수를 준다

- **무엇이** — (중간) 추천 점수의 낱말 겹침 항이 '전문가 · 에이전트 · 추천 · 기록' 같은 요청 낱말에도 점수를 줘, 데이터 없는 무관한 전문가가 추천 상위에 오른다(코드 대조 추정).
- **근거** — `api_server/src/api/services/recommend_svc.py:54`(`_DESC_WEIGHT` 2.0) · `:65-76`(`_STOPWORDS` 에 '알려' 는 있고 전문가 · 에이전트 · 추천 · 근거 · 기록은 없다) · `:289-307`(전체 전문가를 질의 낱말 겹침으로 가점한다). 에이전트 `969e723` `app.py:2618` 은 질문 전체를 q 로 넘긴다. DW-13 에서 추천 10명 중 절반이 무관했다.
- **할 일** — 낱말 겹침 항에서 요청 낱말(전문가 · 에이전트 · 추천 · 근거 · 기록 · 찾아)을 빼고, 기록 · 표본 신호가 0 인 전문가는 겹침만으로 상위에 오르지 않게 한다. HA-31 끝의 '추천 순위 까닭' 몫은 이 행이 받는다.
- **출처** — QA-DIGITAL-WORKER-20261030 DW-13 · 이 요청서 HA-31 · 포털 `docs/request-1029` context-notes 0절

#### 지금 판에서의 자리

- `git log ac42bc6..HEAD -- api_server/src/api/services/recommend_svc.py` 는 0줄이고, 인용한 세 자리가 그대로다.
  - `:54` — `_DESC_WEIGHT = float(os.environ.get("AGENT_DESC_WEIGHT", "2.0"))` 다.
  - `:65-76` — `_STOPWORDS` 다. HEAD 에서 낱말마다 세면 '알려' 는 1이고 전문가 · 에이전트 · 추천 · 근거 · 기록 · 찾아 는 0이다. 이 집합은 `_query_terms`(`:112`, 거르는 줄 `:117`)가 쓴다.
  - `:289-307` — `select(Agent)`(`:292`)로 전체 전문가를 읽어, 이름 · 설명 · 태그 · data_types 에 질의 토큰이 부분 일치하는 비율 `frac` 만큼 `agent_score += _DESC_WEIGHT * frac`(`:307`)을 더한다. 기록 · 표본 점수가 0 인 전문가도 이 항만으로 순위에 오른다.
- 신호가 0 인지 가를 값은 이미 응답에 있다. `matched_records` · `matched_sections` · `matched_samples`(`:346-348`), `why` 의 '역할/설명 어휘 매칭'(`:336-337`)과 '(no direct evidence)'(`:349`), `low_confidence`(`:366`, 기준 `_LOW_CONF_DESC` 0.40 — `:57`)다.
- 에이전트 쪽 인용(`969e723` `app.py:2618` — `_call(tools, "recommend_agents", {"q": query, "top_k": 10})`)도 그대로다. 에이전트 main `7ca3a2e` 에서는 `:2712` 로 옮겨졌다. 가로챈 질문에서 떼는 것은 빗금 트리거뿐이다(`strip_agent_trigger`, `969e723` `app.py:2594-2599`).

#### 우리 쪽 맞물림

- [`../outbound.md`](../outbound.md) 2절의 덧붙임 2(그대로 옮김).

  > **AD-19 와 에이전트 HA-31 의 나눔.** 에이전트는 '추천 근거 · 기록 수' 처럼 다른 물음이 든 질문을 가로채지 않게 고친다. 추천 점수의 낱말 겹침 항(요청 낱말 · 신호 0 전문가)은 AIDataHub 몫이다.

- 에이전트 서버 HA-31 은 고치는 중이다(가지 `wt1030/ha31`, main 에는 아직 없다). 정본 HA-31 의 할 일대로 빗금 트리거('/전문가' 등)만 늘 목록으로 답하고, 자연어는 다른 물음(수 · 근거 · 비교 · 조건)이 없을 때만 가로채며, 전문가를 고른 대화에서는 가로채지 않는다. 그래도 가로챈 질문은 빗금만 떼고 통째로 q 로 가므로(위 `strip_agent_trigger`), 요청 낱말을 거르는 일은 이 행에 남는다.
- 코드는 판단 C-7 로 포털 세션이 고치는 중이다(AD-20 과 한 가지 — `wt1030/ad-rec` 으로 보인다, 아직 커밋 없음).

### AD-21 · 중간 — 전문가를 만들거나 고치면 저장 뒤 500

- **무엇이** — (중간) 전문가를 만들거나 고치면 저장은 되는데 500 을 돌려줘, 운영자 정의 동기화가 첫 건에서 멈춘다.
- **근거** — `api_server/src/api/routes/agents.py:185` · `:206`(저장 뒤 `AgentOut.model_validate`). 500(ValidationError)은 10-28 운영자 동기화 실측이고, 까닭 줄은 다시 재지 않았다. 운영자 정의를 바꾸는 HP-53 · HP-54 가 이 동기화를 탄다.
- **할 일** — POST · PATCH `/api/agents` 가 저장 뒤 500 을 내지 않게 한다. 응답 모델이 저장한 값을 받게 하거나, 받을 수 없는 값은 저장 전에 거절한다.
- **출처** — TODO-20261029 R-02

#### 지금 판에서의 자리

- `git log ac42bc6..HEAD -- api_server/src/api/routes/agents.py` 는 0줄이다.
- POST `create_agent` 의 `return AgentOut.model_validate(agent)` 는 인용대로 `routes/agents.py:185` 다. PATCH `patch_agent` 의 같은 줄은 `:205` 다 — 정본의 `:206` 은 그 아래 빈 줄이라 한 줄 어긋났다.
- 저장은 그 앞에서 끝난다. `services/agent_svc.py` 의 `create_agent` 는 `:95`, `update_agent` 는 `:134` 에서 commit 하고 refresh 한 뒤 행을 돌려준다. 그래서 응답 검증이 깨지면 저장은 남고 500 이 된다(코드 흐름 대조).
- 응답 모델 `AgentOut` 은 `routes/_schemas.py:92-112` 이고, 공통 바탕이 `from_attributes=True`(`:17`)다.
- 500 의 까닭 줄은 대조 못 함 — 이 시트는 서비스를 부르지 않았고, 정본도 '까닭 줄은 다시 재지 않았다' 고 적었다.

#### 우리 쪽 맞물림

- [`../outbound.md`](../outbound.md) 2절의 덧붙임 3(그대로 옮김).

  > **AD-21 과 포털 동기화.** 운영자 정의 동기화(`infra/scripts/sync-he-personas.py`)가 저장 뒤 500 에 첫 건에서 멈춘다. 포털은 저장 여부를 다시 읽어 확인하고 이어 가게 고치는 중이다(작으면 — HP-53 묶음). 근본 고침(저장 뒤 500 을 내지 않기)은 AIDataHub 몫 그대로다.

- 포털 main `bf5cd94` 의 `infra/scripts/sync-he-personas.py` 는 아직 POST 실패(`:215-217`) · PATCH 실패(`:230-232`)에서 `return 1` 로 멈춘다. 포털 쪽 고침(저장 여부를 다시 읽고 이어 가기)은 HP-53 묶음으로 고치는 중이다.
- 이 동기화를 타는 포털 행은 HP-53(운영자 `writes` · `confirm` 채움 — 고치는 중)과 HP-54(조건부 — OB-92 결정 뒤, 판단 C-4)다. 판단 C-8 의 DocForge 운영자 고침 셋도 DocForge 0.3.1 이 cae00 게이트웨이에 실린 뒤 같은 동기화를 탄다.
- 코드는 판단 C-7 로 포털 세션이 고치는 중이다(`wt1030/ad-agents` 로 보인다 — 아직 커밋 없음).

### AD-03(다시) · 낮음 — 변환이 NASCA DRM 파일을 '손상' 으로 안내한다

- **무엇이** — (낮음) '이 대화에서 분석' 의 변환이 NASCA DRM 파일을 알아보지 못하고 '파일이 손상됐을 수 있다' 고 안내한다.
- **근거** — `api_server/src/api/services/mcp_write_svc.py:474-478`(convert_failed · 일반 안내). `api_server/src` 에 NASCA · DRM_PROTECTED 가 0건이다. 포털 첨부 판정(HP-14 `frontend/src/components/chat/docAttach.ts:34`)은 들어와 있다.
- **할 일** — `convert_file` 앞에서 DRM 머리를 보고 `DRM_PROTECTED` 로 따로 알린다(포털 `docAttach.ts` 의 머리 표와 같게).
- **출처** — 10-AIDataHub AD-03 · TODO-20261029 R-03

#### 지금 판에서의 자리

- `git log ac42bc6..HEAD -- api_server/src/api/services/mcp_write_svc.py` 는 0줄이고 `:474-478` 이 그대로다. `convert_file` 를 스레드로 부르고(`:474`), 모든 예외를 `convert_failed` 와 '파일이 손상됐거나 변환기가 처리 못하는 구조일 수 있습니다.' 로 돌린다(`:475-478`).
- `api_server/src` 에 NASCA · DRM_PROTECTED 는 0건이다(대소문자를 가리지 않고 'drm' 으로 찾아도 0건).
- 판정을 넣을 자리(10-27 검토 AD-03)는 `services/converter_dispatch.py` 의 `convert_file`(`:152`) 안, `output_dir = req.resolved_output_dir()`(`:165`) 앞이다. 거기서 `APIError` 를 올리면 REST 로는 그대로 나가고(`:263-264`), 나머지 예외는 `ConversionFailedError` 로 감싸인다(`:267-272`).
- 맞출 머리 표는 포털 `aec8e29` `frontend/src/components/chat/docAttach.ts:34`(`DRM_HEAD` — `3C 23 23 20 4E 41 53 43 41`)와 같은 파일의 `isEncryptedOffice`(`:36-48`)다. PK 는 평문, `D0 CF 11 E0` 은 암호화, NASCA 머리는 암호화, `%PDF` 는 평문, 나머지는 모름으로 가른다. 포털 main 에서도 이 파일은 `aec8e29` 뒤 바뀌지 않았다.

#### 우리 쪽 맞물림

- 이번 회차의 HA- · HG- · HP- 행 가운데 이 행을 바꾸는 것은 없다. 포털 첨부 판정(HP-14)은 이미 들어와 있다(정본 근거 칸).
- 사람 손 시험은 5절 OB-60 · OB-61 · OB-62(챗 업로드 — 목적지 · 큰 파일 · DRM 파일, M-1 ~ M-6)다. 10-27 요청서 7절의 M-6 은 NASCA 로 암호화된 .pptx 를 넣어 DRM 문서라는 별도 문구가 나오는지 본다.
- 코드는 판단 C-7 로 포털 세션이 고치는 중이다(`wt1030/ad-drm` 으로 보인다 — 아직 커밋 없음).

### AD-04(다시) · 낮음 — 본문 검색 스위치의 속도를 재야 켤 수 있다

- **무엇이** — (낮음) 지식카드 본문 검색 스위치의 속도를 아직 재지 않아, 챗 카드 검색이 제목 · 요약만 본다.
- **근거** — `api_server/src/api/config.py:37-38`(`AIDH_RECORDS_Q_BODY_SEARCH`, 기본 끔). 잰 값이 오지 않았다(TODO-20261029 W-06).
- **할 일** — dev DB 사본에서 `EXPLAIN ANALYZE` 로 본문 검색 속도를 재서 알려 달라.
- **출처** — 10-AIDataHub AD-04 · 90-OURS OB-89

#### 지금 판에서의 자리

- `git log ac42bc6..HEAD -- api_server/src/api/config.py` 는 0줄이다. 정본의 `config.py:37-38` 은 스위치 설명 주석의 첫 두 줄이고(env 이름 `AIDH_RECORDS_Q_BODY_SEARCH` 는 `:38`), 설정 칸 `aidh_records_q_body_search: bool = False` 는 `:42` 다(10-27 요청서 · 검토도 `:42`). 기본 끔이 그대로다.
- 스위치를 읽는 곳은 `services/record_query_svc.py:91`(`body = settings.aidh_records_q_body_search and bool(agents)` — 전문가 거름이 있을 때만 본문)이다.
- 스위치 상태는 지금 설명문에만 드러난다. MCP `list_records` 설명(`mcp_runtime.py:934`)과 REST 목록의 q 설명(`routes/records.py:111`)이다. `list_records` 응답(`mcp_runtime.py:965-970`)은 `{total, count, offset, items}` 라 상태 칸이 없다.
- trgm 색인은 HEAD 에 0건이다(`trgm` 은 `config.py:40` 주석과 `deploy/apptainer/.env.example:219-220` 에만 나온다). FTS GIN 표현식 색인은 이행 0031 이고, PG 기반 이미지는 `deploy/apptainer/postgres.def:6`(`pgvector/pgvector:pg16`)이다.
- 재는 법은 10-27 검토 AD-04 에 있다. `EXPLAIN (ANALYZE, BUFFERS)` 를 건수 질의와 쪽 질의 둘 다에 걸고(`services/sql_compat.py:351-355` 에서 따로 돈다), 2글자 낱말과 3글자 이상 낱말로 나눠 잰다. 기준 전문가는 material-twin-analyst(2,729장 — `config.py:39-40` 주석)다.
- 잰 값은 대조 못 함 — dev DB 사본을 만들거나 읽지 않았다(데이터 단계, 사용자 OK 뒤).

#### 우리 쪽 맞물림

- [`../outbound.md`](../outbound.md) 2절의 덧붙임 1(그대로 옮김).

  > **AD-04(다시)에 덧붙임 — 스위치 상태 칸.** 본문 검색 스위치(`AIDH_RECORDS_Q_BODY_SEARCH`)를 켤 때 기록 목록 · 검색 응답에 그 스위치 상태를 싣는다. 포털 HP-21(다시)이 그 칸을 보고 검색칸 문구를 바꾼다(포털 판단 C-3).

- 포털 HP-21(다시)은 조건부다(판단 C-3 — 이 칸이 생긴 뒤). 검색칸 문구는 포털 main 에서도 `frontend/src/components/chat/AgentDeepView.tsx:323`(placeholder '제목·요약에서 낱말로 찾기') 그대로다.
- 포털 심층 보기는 AIDataHub 를 바로 부르지 않는다. 포털 `backend/app/agent/routes.py:976-991` 이 에이전트 서버 `/catalog/agent/records` 로 넘기고, 에이전트 서버 `catalog_agent_records`(main `7ca3a2e` `app.py:6673-6691`)가 `list_records` 를 불러 `{total, offset, limit, items}` 만 새로 짜서 돌려준다. 그래서 상태 칸이 생기면 에이전트 서버도 그 칸을 넘겨야 화면에 닿는다. 이번 회차의 HA 행에는 그 일이 없다.
- 스위치를 cae00 에서 켤지는 5절 OB-89(우리 몫 — 'AD-04(다시)의 잰 값 대기')다. 측정은 체크리스트 3b 에서 '데이터 단계, 사용자 OK 뒤' 로 남겼다.

### AD-05 · AD-06(다시) · 낮음 — 빈 전문가 · 데모 전문가가 목록과 추천 후보에 남았다

- **무엇이** — (낮음) 빈 전문가(dynaforge-report)와 데모 전문가(kooremapper-modelmeta)가 전문가 목록 · 추천 후보에 남아 있다.
- **근거** — 10-30 포털 nginx 경유 `GET /ai-data-hub/api/agents/<키>` 가 둘 다 200 · 설명 0자 · data_types [] 다. 지우는 순서는 dev 먼저, cae00 나중이다(AD-13 답).
- **할 일** — dev 원본에서 두 전문가와 데모 카드 3장을 먼저 지워 달라(다음 덤프로 퍼진다). 일정을 알려 달라. cae00 몫은 OB-87 이다.
- **출처** — 10-AIDataHub AD-05 · AD-06 · AD-13 · 90-OURS OB-87

#### 지금 판에서의 자리

- 박스 데이터 행이라 정본 근거에 `파일:줄` 이 없다. 두 전문가가 dev · cae00 에 아직 있는지는 대조 못 함 — 이 시트는 DB 와 API 를 부르지 않았다(레코드 단건 GET 은 read_count · updated_at 을 바꾼다 — 10-27 검토 AD-01; 10-31 덧붙임 — AIDataHub `fccb0e5` 부터 조회는 read_count · last_accessed_at 만 올린다, 사용자 결정 10-31).
- 지우는 길은 HEAD 에 그대로다. 전문가는 `DELETE /api/agents/{agent_type}`(`routes/agents.py:208-216`)가 `agent_svc.delete_agent`(`services/agent_svc.py:201-224`)를 불러, 같은 트랜잭션에서 `records.agents` 배열의 키를 빼고(`:218-221`) 행을 지운다. `agent_records` 는 FK CASCADE 로 따라 지워진다(`db/models.py:484`). 이 경로에는 API 키 검사(`require_api_key`)가 없다(10-27 검토 N5 그대로).
- 레코드 소프트 삭제는 `DELETE /api/records/{record_id}`(`routes/records.py:244`)다. 병합으로 퍼지는 삭제는 이것뿐이다(10-27 검토 AD-06 · AD-13).
- 빈 전문가가 생긴 길은 적재의 stub 만들기(`ingest/db_writer.py:853-864`)이고, 지금은 엄격 검증을 끈 때만 생긴다(주석 `:840-841`). 빈 설명은 추천 맥락에서 'Help the user with: (no description)' 이 된다(`services/recommend_svc.py:843` · `:849`).
- 지우는 순서(10-27 검토 AD-13 답)는 dev 레코드 소프트 삭제 → dev 전문가 삭제 → 새 덤프 → cae00 병합 → cae00 전문가 삭제(OB-87) → 다음 병합 뒤 확인이다. 병합은 `agents` 를 updated_at 이 더 새 쪽으로(`deploy/apptainer/merge-from-drive.sh:150`), `agent_records` 는 키가 같으면 dev 쪽으로(`:153`) 쓰고, cae00 에 없는 키는 그냥 넣는다(`:133`). 그래서 cae00 에서만 지우면 다음 병합에 다시 들어온다.
- dynaforge-report 에 묶인 레코드를 sim-drop-impact 로 다시 묶을지는 지우기 전에 정한다(10-27 검토 AD-05 — 그냥 지우면 배열에서 키가 빠져 그 레코드는 어느 좌석에도 걸리지 않는다).

#### 우리 쪽 맞물림

- cae00 몫은 5절 OB-87(우리 몫 — '끝 절 AD-05 · AD-06(다시) 뒤')이다. dev 원본에서 지우는 것이 먼저다.
- dev 지우기는 체크리스트 3b 에서 '데이터 단계, 사용자 OK 뒤' 로 남겼다(판단 C-7).
- dev 지우기는 덤프를 타고 cae00 에 간다. cae00 은 update-all 3) 'AIDataHub 데이터 동기화'(포털 `infra/scripts/update-all.sh:1119-1190`)에서 병합하고, 병합이 rc 3 으로 끝나면 표식을 적지 않아 다음 update-all 이 다시 병합한다(`:1169`).
- 이번 회차의 HA- · HG- · HP- 행 가운데 이 행을 바꾸는 것은 없다.

### AD-07(다시) · 낮음 · 심의 — agent_search 가 as_of 를 받지 않는다

- **무엇이** — (낮음 · 심의) agent_search 가 as_of 를 받지 않아, 심의가 그 시점 뒤에 생긴 카드까지 근거로 쓸 수 있다. 챗에서 시작한 소급 심의도 같다.
- **근거** — `api_server/src/api/mcp_runtime.py` 에 as_of · valid_from 이 0건이다(HEAD 대조). 믿을 날짜 칸 records.valid_from 은 이미 있다(reflection-1028/10 AD-07).
- **할 일** — agent_search 가 as_of 를 받아 `valid_from <= as_of` 로 거른다. 에이전트 서버 HA-11 이 이것을 기다린다.
- **출처** — 10-AIDataHub AD-07 · 03-HWAXAgentServer HA-11 · TODO-20261029 R-03

#### 지금 판에서의 자리

- `git log ac42bc6..HEAD -- api_server/src/api/mcp_runtime.py` 는 0줄이다. 이 파일의 `as_of` · `valid_from` 은 0건이고, `api_server/src` 전체에서도 `as_of` 는 0건이다.
- `agent_search` 는 `mcp_runtime.py:457` 이다. 좌석 범위를 `:519-525`(`Record.agents @> [agent_type]`, 폴백 `:526-534`)에서 정하고, 범위가 비면 거절한다(`:541-544`). 날짜 조건을 걸 자리가 여기다(10-27 검토 AD-07 — 그때 `:518-545`).
- 믿을 날짜 칸 `records.valid_from` 은 `db/models.py:250`(Date, 빈 값 허용)이고, 동기화가 원천 날짜로 채운다(`services/sync_svc.py:351-356`).
- 에이전트 서버는 `969e723` 과 main `7ca3a2e` 모두 `deliberation.py` · `app.py` 에 `as_of` 가 0건이다. HA-11 은 아직이다.

#### 우리 쪽 맞물림

- 코드는 판단 C-7 로 포털 세션이 고치는 중이다(`wt1030/ad-asof` 로 보인다 — 아직 커밋 없음). 그 뒤 에이전트 서버 HA-11(10-27 행 — 엔진이 `as_of` 를 함께 보낸다)을 잇는다(체크리스트 3b). 10-27 체크리스트의 HA-11 은 '[~] HA-11 as_of — AIDataHub AD-07 뒤' 다.
- 날짜 없는 카드를 어떻게 다룰지는 엔진 쪽이 정한다(10-27 검토 AD-07).
- 이번 회차 1 ~ 4절의 행 가운데 이 행에 걸린 것은 없다.

### AD-20 · 낮음 — 카드와 전문가를 잇는 저장소가 둘이다

- **무엇이** — (낮음) 카드와 전문가를 잇는 저장소가 둘(records.agents · agent_records)이라, 추천의 근거 기록 수와 전문가 기록 목록이 어긋날 수 있다.
- **근거** — `recommend_svc.py:253-255`(records.agents 로 센다) · `api_server/src/api/services/agent_svc.py:338-340`(agent_records 로 목록을 낸다).
- **할 일** — 두 저장소를 하나로 합치거나 한쪽을 정본으로 맞춘다. 추천의 기록 수와 전문가 기록 목록이 같아야 한다.
- **출처** — 포털 `docs/request-1029` PLAN 2.4 E-5 · context-notes 0절

#### 지금 판에서의 자리

- 두 파일 모두 `git log ac42bc6..HEAD` 가 0줄이고, 인용한 줄이 그대로다.
  - `services/recommend_svc.py:253-255` — 의미검색에 걸린 레코드(`:235-241`)의 `records.agents` 로 센다. 그 수가 응답의 `matched_records`(`:346`)다.
  - `services/agent_svc.py:338-340` — `records_for_agent`(`:334-343`)가 `agent_records` 와 join 한다. 부르는 곳은 REST `GET /api/agents/{agent_type}/records`(`routes/agents.py:82-95`)와 `services/preview_svc.py:69` 다.
- `records.agents` 로 정하는 곳이 둘 더 있다. MCP `list_records` 의 전문가 거름(`services/record_query_svc.py:78-79` — 포털 심층 보기 목록이 이 길이다)과 `agent_search` 좌석 범위(`mcp_runtime.py:519-525`)다.
- `agent_records` 는 적재 때 `_resync_agents`(`ingest/db_writer.py:830-872`)가 `records.agents` 로 다시 짓는다. `records.agents` 가 FK 없는 text[] 라는 것은 `delete_agent` 주석(`services/agent_svc.py:212-217`)에 있다. 실제로 어긋난 행 수는 대조 못 함 — DB 를 읽지 않았다.
- 저장소 하나를 걷으면 병합 목록(`deploy/apptainer/merge-from-drive.sh:153` `try_merge agent_records`)도 함께 바뀐다. 이행(alembic)으로 합치면 cae00 은 다음 기동 때 `alembic upgrade head` 가 uvicorn 보다 먼저 돈다(`deploy/apptainer/start_api.sh:169`).

#### 우리 쪽 맞물림

- 포털 `docs/request-1029` PLAN 2.4 E-5(페르소나 연결)가 이 일을 AI 데이터 허브 요청서로 보낸다고 적었고, 그 context-notes 0절이 '저장소가 둘이다 — 어긋날 수 있다' 를 근거로 둔다.
- 코드는 판단 C-7 로 포털 세션이 고치는 중이다(AD-19 와 한 가지 — `wt1030/ad-rec` 으로 보인다, 아직 커밋 없음).
- 이번 회차의 HA- · HG- · HP- 행 가운데 이 행을 바꾸는 것은 없다.

## 끝나면

- **알릴 곳** — HWAX 포털 세션 `hwaxportal-a5` 다. 포털 세션이 맡은 코드 행은 체크리스트 3b 를 채운다. 다른 손(사람 · 새로 연 AIDataHub 세션)이 맡은 일은 `hwaxportal-a5` 에 알려 [`../outbound.md`](../outbound.md) 2절에 답으로 옮긴다. cae00 에서 사람이 할 일은 `docs/request-1030/server-setup.md` 에 옮긴다(계획이 적은 문서이고, 이 시트를 쓸 때는 아직 없었다).

### 코드 행 — AD-01(코드) · AD-19 · AD-20 · AD-21 · AD-03(다시) · AD-07(다시)

- **알릴 것** — 행마다 AIDataHub main 커밋 sha, origin main 에 올렸는지, 더한 시험과 그 결과, 이행(alembic) 번호가 생겼으면 그 번호.
- **배포 산출물** — 없다. AIDataHub API 는 리포의 venv 로 돈다(`deploy/apptainer/start_api.sh:2`). SIF · Drive 빌드가 없고, cae00 은 update-all 2) 의 `deploy-all-from-drive.sh` aidh 단계가 `git_update` 뒤 `boot.sh --force` 로 다시 띄운다(포털 `infra/scripts/deploy-all-from-drive.sh:405-423`). 따로 다시 띄울 때도 `restart.sh --api` 가 아니라 포털 `deploy-all-from-drive.sh aidh` 다(AIDataHub `99cae7b`).
- **cae00 사람 몫** — update-all 뒤 aidh 헬스(`/api/system/health`)와, 이행이 들었으면 그 이행이 끝났는지 본다. AD-21 이 들어가면 운영자 동기화(포털 `infra/scripts/sync-he-personas.py --apply`)가 저장 뒤 500 없이 끝까지 가는지 본다.

### 데이터 단계 — 사용자 OK 뒤(판단 C-7)

- **AD-05 · AD-06(다시)** — dev 원본에서 지운 키 · 레코드 id 와 시각, 그 뒤 Drive `AIDataHub/db-dumps` 에 올린 덤프 이름(`deploy/apptainer/backup-to-drive.sh`)을 알린다. cae00 은 update-all 3) 병합 뒤 OB-87 로 전문가 행을 지운다.
- **AD-01(다시)** — 다시 짓기 명령을 dev 에서 먼저 돌리고, cae00 은 그 박스 병합 뒤에 돌린다. 돌리기 전과 뒤의 '1번 절이 빈 카드' 수를 알린다.
- **AD-04(다시)** — dev DB 사본에서 잰 `EXPLAIN (ANALYZE, BUFFERS)` 값(건수 · 쪽 질의, 2글자 · 3글자 이상 낱말)을 알린다. cae00 에서 켤지는 OB-89(사람)다.

### 다시 볼 시험

- 10-30 정본 7절에는 AIDataHub 행에 걸린 시험이 없다. 가장 가까운 DW-13(HA-31 뒤)의 볼 것은 「질문이 챗 에이전트로 가고 '기록 수' 를 답한다.」 이고, 추천 순위(AD-19)는 그 볼 것에 들지 않는다.
- 10-27 요청서 7절에서 이어지는 확인(cae00, 사람 몫)은 다섯이다.
  - K6-4 확인(AD-01) — 목록 조회로 속 빈 카드를 다시 센다.
  - K6-1 · K6-2 확인(AD-05 · AD-06) — `GET /api/agents/` 에서 이름=키 전문가가 빠지고, `?agent=kooremapper-modelmeta` 의 total 이 3 → 0 이다.
  - K5 확인(AD-04) — 스위치를 켜고 5분 지나서(게이트웨이 `list_*` 캐시 300초) 본문 낱말로 찾는다.
  - M-6(AD-03) — NASCA 로 암호화된 .pptx 를 넣어 DRM 문서라는 별도 문구가 나온다.
  - 전수 점검(AD-01 · AD-04 · AD-05 · AD-06) — cae00 `~/kc-check/kc_sweep.py`(읽기만)를 다시 돌린다. 확인에는 목록 조회만 쓴다(단건 조회는 read_count 를 바꾼다 — updated_at 은 AIDataHub `fccb0e5`(10-31) 부터 그대로).
