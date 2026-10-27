# 10-AIDataHub 요청 검토 — AIDataHub 코드 대조

> 주 세션이 따로 다시 본 것(2026-10-28 KST): N1(`_flatten_sections` 는 `children` 만 내려가고 MXWP 는 `subsections` 를 쓴다) · AD-12 의 전제(`records.updated_at` NOT NULL · 기본값 now()) · N4(포털 env-sync 는 리포 루트 · `infra` · `platform` 만 본다) · AD-16(포털 `docs/embedder-bge-m3/checklist.md` B6 미체크 — 반영했다). 나머지는 검토 에이전트의 대조 그대로다.

대상은 `docs/request-1027/10-AIDataHub.md`(AD-01 ~ AD-18)다. 파일과 `git log/show` 만 읽었다. DB · 서비스 · HTTP 는 건드리지 않았다.

**기준 판.** AIDataHub HEAD 는 `ac42bc6`(10-18 21:37 UTC)이고, 요청서가 말한 10-27 cae00 판과 같다. `b401f88`(40 커밋 앞)와 `57a5a4b`(10 커밋 앞)는 둘 다 HEAD 의 조상이다. 요청서가 `b401f88` 기준으로 적은 줄 가운데 일곱 곳이 옮겨졌다(§6). 아래 `파일:줄` 은 모두 HEAD 기준이다. `api_server/src/api/` 는 `api/` 로 줄여 적는다.

## 0. 총평

**대체로 유효하다.** 18건 가운데 그대로 맞는 것이 11건이다. 고쳐 읽어야 할 것이 4건이다(AD-01 원인, AD-07 인용, AD-08 범위, AD-12 전제). 이미 된 것 1건(AD-09), 포털 문서 몫 1건(AD-16), 선택 1건(AD-10)이다.

| # | 판정 | 한 줄 |
|---|---|---|
| AD-01 | 유효 · 원인 보완 | 상세 조회 실패로 덮인 것만으로는 이 모양이 나오지 않는다. 병합 섞임 또는 MXWP 하위 절 평탄화 누락이다. 질의 하나로 가린다. |
| AD-02 | 유효 | MCP `run_convert` 만 임시 폴더를 지우지 않는다. REST 길은 이미 지운다. |
| AD-03 | 유효 | NASCA 판정 0건이다. 지금 문구는 '손상' 계열이다(추정). |
| AD-04 | 유효(측정) | 측정은 dev DB 로 충분하다. trgm 은 2글자 낱말에는 효과가 없다. |
| AD-05 · 06 | 유효 | 지우기는 양쪽 박스에서 해야 한다(AD-13). 05 는 레코드를 다시 묶는 일이 빠졌다. |
| AD-07 | 유효 · 인용 틀림 | 범위를 정하는 곳은 `mcp_runtime.py` 다. 믿을 날짜 칸 `valid_from` 이 이미 있다. |
| AD-08 | 범위 고침 | AIDataHub 는 부른 사람을 모른다. 포털 쪽이 먼저다. |
| AD-09 | 이미 됨 | `a7a2ee4` · `722d7a0` 으로 해결됐다. 박스에서 다시 세기만 하면 된다. |
| AD-10 | 선택 | 등록만으로는 효과가 없다. |
| AD-11 ~ 15 | 답(§4) | AD-12 는 전제가 틀렸다. AD-15 는 `SF_API_KEY` 가 빠졌다. |
| AD-16 | 포털 몫 | `docs/embedder-bge-m3/checklist.md:18` 이 아직 미체크다. |
| AD-17 · 18 | 결정(§5) | 검토자 권고는 (나) · (나)다. |

**요청서의 틀린 점.**
1. 줄 일곱 곳이 옮겨졌다(§6). `_resync_sections` 는 `api/ingest/db_writer.py:623-679` 에 있다.
2. AD-07 의 `recommend_svc.py:450` 은 맥락 묶음 `build_context_bundle` 이다. `agent_search` 의 좌석 범위는 `api/mcp_runtime.py:518-545` 에서 정한다.
3. AD-12 의 전제(cae00 updated_at 이 빈 행)는 생길 수 없다. `records.updated_at` 과 `agents.updated_at` 은 NOT NULL 이고 기본값이 now() 다(`api/db/models.py:282-287` · `:454-459`, `alembic/versions/0030_agents_updated_at.py:35-42`).
4. AD-09 의 '레코드 시그니처 0건' 은 `a7a2ee4` · `722d7a0`(10-17 14:38 · 14:46 UTC)보다 앞선 병합의 결과다.
5. AD-15 는 `SF_API_KEY`(`config/sync_sources.yml:26`)를 빠뜨렸다.
6. AD-17 의 '10-01 부터' 는 로그를 본 기간일 뿐이다. 코드 주석은 07-18 부터라고 적는다(`api/services/sync_svc.py:688-689`). 막힌 시도는 `sync_runs` 행을 만들지 않는다. 가드(`:686-703`)가 행을 만드는 곳(`:748`)보다 먼저 예외를 내기 때문이다. 그래서 이력 API 에는 보이지 않고 로그와 `last_status='blocked'` 에만 남는다.
7. §6 표의 'AD-17 에 MXWP 쪽 할 일 없음' 은 (가)를 고르면 맞지 않는다. MXWP 목록의 기본 범위는 `audience=mine` 이고, AIDataHub 몫은 `?audience=org` 로 정해져 있다(MXWhitePaper `apps/api/app/routers/documents.py:69-73`, `docs/llm-wiki/checklist.md:41`). 상세 응답에서 어떤 블록을 가릴지는 키의 역할이 정한다(`documents.py:130`).

**요청서에 없는 발견.**
- **N1.** `_flatten_sections` 는 `children` 만 내려간다(`api/ingest/db_writer.py:201-202`). 그런데 MXWP 는 하위 절을 `subsections` 에 둔다(MXWhitePaper `apps/api/app/schemas/document.py:2561-2592`). 그래서 MXWP 하위 절 본문은 `record_sections` 에 들어가지 않는다. '빠진 절' 경고에도 잡히지 않는다(`:148-154` 는 방문한 노드만 센다). `_blocks_to_text`(`:219-248`)도 paragraph · heading · list · code · 참조 table 만 읽는다. 그래서 MXWP 의 heading-4(`title` 칸) · quote · callout · math · 인라인 table · columns · tabs 의 글이 빠진다. AIDataHub 도 이 차이를 알고 있었지만, 요약을 본문에서 채울 때만 반영했다(`api/services/sync_svc.py:200-201`).
- **N2.** 병합은 행을 지우지 않는다. 또 `records` 와 `record_sections` 를 서로 따로 판정한다(`deploy/apptainer/merge-from-drive.sh:102` · `:133` · `:152` · `:155`). 레코드 행은 updated_at 이 더 새 쪽을 고른다. 절은 같은 (record_id, section_id) 가 있으면 늘 dev 것을 쓰고, 운영에만 있는 절은 그대로 남는다. 그래서 한 카드가 두 박스 판의 조합이 될 수 있다.
- **N3.** 레코드 ID 는 박스마다 `MAX(seq)+1` 로 정한다(`api/services/seq.py:8` · `:17`, '단일 작성자 가정'). 두 박스가 같은 소스를 각자 받으면 ID 가 겹친다. 그러면 `external_id_map` 병합(dev 우선, `merge-from-drive.sh:158`)이 매핑을 dev ID 로 돌리고, 운영 쪽 레코드는 매핑 없는 중복으로 남는다.
- **N4.** `deploy/apptainer/.env.example:178` 은 `AIDH_SYNC_ALLOW_INTERNAL=true` 를 켠 채 두고 있다. `.env` 가 없으면 이 예시 파일이 그대로 복사된다(`deploy/apptainer/_common.sh:86-97`). 포털 env-sync 는 `deploy/apptainer` 를 보지 않는다(HWAXPortal `infra/scripts/env-sync.sh:77`).
- **N5(참고).** `DELETE /api/agents/{agent_type}` 는 키 없이 열려 있다(`api/routes/agents.py:208-216` — `require_api_key` 가 없고 AUTH_REQUIRED=false).

## 1. 높음

### AD-01 — mx-whitepaper-analyst 154장의 빈 1번 절

**확인.**
- **사실.** 동기화 폴백은 `section_id "1"` · 제목 「본문」 · 빈 글로 된 절 하나를 만든다(`sync_svc.py:281-296`). `84f4ffc` 이전에는 상세 조회가 실패해도 목록 메타로 이 폴백을 적재했다. 지금은 그 문서를 건너뛰고 failed 로 센다(`:866-873`). `84f4ffc` 커밋 메시지는 154장을 이 결함 탓으로 돌린다.
- **사실.** 그런데 적재할 때는 그 레코드의 절을 모두 지우고 새 트리만 넣는다(`db_writer.py:486` · `:631-635`). 그러니 덮어쓰기만으로는 빈 「본문」 옆에 글이 있는 「개요」 · 「응용」 이 남을 수 없다. 요청서가 '맞지 않는다' 고 본 것이 옳다.
- **추정.** 이 모양을 만들 수 있는 길은 둘이다.
  - **(A) 병합 섞임.** 한 박스는 폴백으로 덮인 판을, 다른 박스는 온전한 판을 가진 경우다. N2 대로라면 dev 의 빈 "1" 이 운영의 "1" 을 덮는다(`merge-from-drive.sh:103` — 절 표는 비교 없이 dev 값을 쓴다). 운영의 "2" · "4" 는 남는다. 요약과 content 를 담은 레코드 행은 updated_at 에 따라 따로 정해진다.
  - **(B) 원천의 1번 절이 MXWP 자신의 「본문」 래퍼인 경우.** MXWP docx 가져오기는 첫 제목 앞의 글이나 빠진 1단계 부모를 「본문」(number "1")으로 만든다(MXWhitePaper `apps/api/app/services/docx_import.py:1241` · `:1270`, pdf 는 `pdf_import.py:153`). 그 절의 글이 하위 절 · 표 · callout 에만 있으면 N1 때문에 허브에서 빈 절이 된다. 1단계 절의 paragraph 는 남는다. 이 길은 한 박스 안에서도 생긴다.
- (B)라면 동기화를 다시 돌려도 고쳐지지 않는다. 같은 트리를 같은 평탄화로 다시 넣을 뿐이다.

**두 원인을 가르는 질의.** 읽기만 한다. 단건 GET 은 read_count 와 updated_at 을 바꾸므로 쓰지 않는다. dev 와 cae00 양쪽에서 돌린다.

```sql
SELECT r.id, jsonb_array_length(r.content->'sections') AS top_n,
       r.content->'sections'->0->>'title' AS s1_title,
       (r.content->'sections'->0) ? 'content_text' AS s1_fallback,
       jsonb_array_length(COALESCE(r.content->'sections'->0->'subsections','[]')) AS s1_subs,
       (SELECT count(*) FROM record_sections s WHERE s.record_id = r.id) AS rows_n
  FROM records r
 WHERE r.agents @> ARRAY['mx-whitepaper-analyst'] AND r.deleted_at IS NULL
   AND EXISTS (SELECT 1 FROM record_sections s WHERE s.record_id = r.id
               AND s.section_id = '1' AND COALESCE(s.content_text,'') = '');
```

`s1_fallback` 이 참이고 `top_n` 이 1 인데 `rows_n` 이 1 보다 크면 (A)다. `s1_fallback` 이 거짓이고 `s1_subs` 가 0 보다 크거나 1번 절 블록이 paragraph 가 아니면 (B)다. 요청서의 '`…0109` 상세 조회가 200 인가' 는 (A)를 볼 때만 쓰는 보조 확인이다.

**몫.** 질의는 AIDataHub 담당이나 박스 운영자가 돌린다. 코드 수정은 AIDataHub 몫이다. MXWP 는 원문 확인(MW-07)만 한다.

**권하는 길.**
1. 위 질의로 (A)와 (B)를 가린다. 10분이면 된다.
2. (B)이면 AIDataHub 코드를 고친다. `_flatten_sections` 가 `subsections` 도 내려가게 하고, `_blocks_to_text` 가 MXWP 블록 종류를 읽게 한다. 방문하지 못한 노드도 `dropped` 에 센다. 30~50줄과 시험이 든다.
3. 색인을 다시 짓는 CLI 를 둔다. records.content 에서 절만 다시 짓는다. 적재는 본문 해시 · 제목 · 요약이 같으면 건너뛰므로(`db_writer.py:424-428`) 재동기화로는 절이 다시 지어지지 않는다. 이때 레코드 행은 건드리지 않거나, `SET LOCAL aidh.keep_updated_at='on'` 으로 쓴다(`alembic/versions/0032_embedding_m3_slot.py:54-59`). updated_at 이 오르면 병합 우선순위가 뒤집히기 때문이다. 60줄 안팎이다.
4. (A)이고 content 가 폴백이면 원천을 다시 받아야 한다. dev 에서 동기화한 뒤 병합하고, cae00 에서 3을 한 번 돌려 남은 절을 걷어 낸다. 병합은 행을 지우지 않기 때문이다.
5. 마지막으로 다시 센다. 그래도 남는 '어디에도 글 없음' 카드만 AD-18 로 넘긴다.

## 2. 중간

### AD-02 — /tmp 에 남는 변환 그림
**확인.** 사실이다. `run_convert` 는 `output_dir` 없이 요청을 만들고(`api/services/mcp_write_svc.py:468-472`), 그러면 디스패처가 `mkdtemp` 로 폴더를 만든다(`converter_dispatch.py:109-113`). 그 폴더를 지우는 곳이 없다. 같은 변환의 REST 길은 작업 폴더를 넘기고 `finally` 에서 지운다(`api/routes/convert.py:302-326`). 포털은 자기가 만든 inbox 사본만 지운다(HWAXPortal `backend/app/agent/routes.py:1499-1503`).
**몫.** AIDataHub 코드다. 이미 남은 폴더 두 개는 운영 몫(OB-36)이다.
**권하는 길.** `run_convert` 를 `tempfile.TemporaryDirectory(prefix="ai_data_convert_")` 로 감싸고 `output_dir=Path(td)/"out"` 을 넘긴다. 변환 결과는 메모리에 있고 그림은 상대 경로로만 실린다(`ppt_converter/core.py:582`). 그래서 뒤 단계(`import_record`)가 읽을 파일은 없다. 10줄과 시험 1건이다.

### AD-03 — DRM(NASCA) 판정
**확인.** `api_server/src` 에 NASCA · DRM 판정은 0건이다(사실). pptx 는 `Presentation(path)` 로 연다(`ppt_converter/core.py:211`). 추정(라이브러리 동작, 실행 안 함)으로는 python-pptx 가 'Package not found at …' 을 낸다. 이것이 'pptx 변환 실패 …' → 'conversion failed' 와 '파일이 손상됐거나…' 안내로 돌아온다(`converter_dispatch.py:267-272`, `mcp_write_svc.py:475-478`). 이 문구에 서버 inbox 경로가 섞인다. 포털 챗은 이 결과를 '읽을 내용을 찾지 못했습니다' 로 바꿔 보여 준다(포털 `routes.py:1504-1507`).
**몫.** AIDataHub 코드다. 포털 HP-14 와 RA RP-03 은 같은 판정 표를 쓴다.
**권하는 길.** `convert_file` 의 `:165` 앞에서 OOXML 확장자 파일의 앞 바이트를 본다. 요청서 실측값 `3C 23 23 20 4E 41 53 43 41` 로 시작하면 DRM 이다. `D0 CF 11 E0` 이면 암호화(또는 구형 바이너리)다. `50 4B` 로 시작하지 않으면 형식 오류다. 새 `APIError`(예 422 `DRM_PROTECTED`)를 올리면 REST 는 그대로 통과한다(`:263-264`). `run_convert` 는 `code: drm_protected` 와 안내문을 낸다. 30줄과 시험 3건이다. 세 리포는 언어가 달라 코드를 나눠 쓸 수 없으니 판정 표를 문서 한 장으로 맞춘다.

### AD-04 — 본문 낱말 검색 스위치
**확인.** 맞다(`api/config.py:42`, `api/services/record_query_svc.py:91`, `alembic/versions/0031_fts_gin_index.py:11-14`, trgm 0건). 덧붙이면 두 가지다. 본문은 전문가 필터가 있을 때만 본다(`:91`). 건수와 쪽을 따로 질의하므로 조건이 두 번 돈다(`api/services/sql_compat.py:351-355`).
**몫.** 측정은 AIDataHub 가 한다. dev DB 로 충분하다(덤프의 원본이라 카드가 같다). 스위치 켜기는 운영(OB-89), 화면 문구는 포털(HP-21) 몫이다.
**권하는 길.** `EXPLAIN (ANALYZE, BUFFERS)` 를 건수 질의와 쪽 질의 둘 다에 걸고, 2글자 낱말과 3글자 이상 낱말로 나눠 잰다. pg_trgm 은 3글자 미만에는 색인을 쓰지 못한다. 그래서 '낙하' · '충격' 같은 2글자 낱말은 여전히 전체를 훑는다. trgm 을 달 때는 0031 처럼 CONCURRENTLY 로 단다. 기반 이미지가 `pgvector:pg16` 이라 contrib 가 들어 있을 것이다(`deploy/apptainer/postgres.def:6`, 추정).

### AD-05 — 빈 전문가 dynaforge-report
**확인.** 빈 행을 만든 것은 `_resync_agents` 다(`db_writer.py:853-864`). 지금은 엄격 검증이 이런 적재를 422 로 막는다(`:330-350`, `config.py:82`, `6b0d06c`). 다만 이미 생긴 행은 남아 있다. 'Help the user with: (no description)' 은 `recommend_svc.py:843-849` 다. `data_types` 는 `agent_search` 의 기본 거름이다(`mcp_runtime.py:511-513`). 그래서 SIM 이 없으면 sim-drop-impact 좌석에서 SIM 카드가 빠진다. 전문가 삭제는 하드 삭제다. `agent_records` 는 FK cascade 로 지워지고(`models.py:484`), 레코드의 `agents` 배열에서도 키를 뺀다(`api/services/agent_svc.py:212-222`).
**몫.** 운영의 데이터 작업이다. 코드는 없다.
**권하는 길.** 지우기 전에, 그 2행에 묶인 레코드를 sim-drop-impact 로 다시 묶을지 먼저 정한다. 그냥 지우면 배열에서 키가 빠져 그 레코드는 어느 좌석에도 걸리지 않는다. 지우는 순서는 AD-13 을 따른다.

### AD-06 — kooremapper-modelmeta 데모 3장
**확인.** `status` 기본값이 draft 인 것은 맞다(`api/ingest/normalizer.py:501`). 소프트 삭제는 `routes/records.py:244` 다(요청서는 `:239`). `deleted_at` 만 적지만(`:280-296`) 트리거가 updated_at 도 올린다. 하드 삭제는 부트스트랩 키가 필요하고 `external_id_map` 까지 지운다(`models.py:831-834`).
**몫.** 운영이다.
**권하는 길.** 레코드는 소프트 삭제한다. 병합으로 퍼질 수 있는 삭제는 이것뿐이다. 레코드 다음에 전문가를 지운다. 순서는 AD-13 을 따른다.

### AD-07 — agent_search 날짜 컷오프
**확인.** 날짜 거름이 0건인 것은 맞다. 다만 범위를 정하는 곳은 `mcp_runtime.py:518-545` 다. `created_at` 은 적재한 시각이고(`models.py:277-281`), 병합하면 dev 값이 그대로 옮겨진다. updated_at 은 단건 조회만 해도 오른다(`routes/records.py:53-73` · `:173`, 트리거 `alembic/versions/0002_record_updated_at_onupdate.py:32-46`).
**믿을 날짜 칸은 이미 있다.** `records.valid_from`(Date, `models.py:250`)이다. 동기화는 이 칸을 원천 날짜로 채운다(`sync_svc.py:351-358`). SignalForge 는 processed_at, MXWP 와 MaterialTwin 은 created_at 을 쓴다(`sync_sources.yml:59` · `:126` · `:199`). 업로드 카드는 올린 사람이 날짜를 줄 때만 채워진다. MXWP 의 created_at 은 문서가 MXWP 에 들어온 날이라 원문 날짜와 다를 수 있다.
**몫.** AIDataHub 코드와 에이전트서버(HA-11)다. 날짜 없는 카드를 어떻게 다룰지는 엔진 담당이 정한다.
**권하는 길.** `agent_search` 가 `as_of` 를 받아 좌석 범위 질의(`:520-523`)에 `valid_from <= as_of` 를 건다. 엄격 모드에서는 날짜 없는 카드를 빼고, 뺀 수를 `applied_config` 에 싣는다. 스키마 작업 없이 20줄과 시험이다. 먼저 카드 종류별로 `valid_from` 이 얼마나 채워졌는지 읽기 질의로 센다.

## 3. 낮음 · 선택

### AD-08 — list_inbox
**확인.** inbox 는 박스에 하나뿐이다(`mcp_write_svc.py:395-401`). 파일 이름 앞에는 올린 사람의 계정이 붙는다(포털 `routes.py:1498` · `:1522`). 그런데 AIDataHub MCP 는 API 키의 주인만 알고 실제 사람은 모른다(`mcp_write_svc.py:245-253`). 그래서 '부른 사람의 파일만' 골라 보여 줄 수 없고, 다 보여 주면 남의 파일 이름이 샌다. 같은 이름의 도구는 게이트웨이 카탈로그 사본에 없다. 비슷한 것은 `inbox_status` 하나다(HWAXMcpGateway `tool_search_eval/catalog.local.json:6493`, 사본 기준).
**몫.** 포털이 먼저다. 포털은 이미 `inbox_name` 을 돌려주고 있으니(`routes.py:1528-1529`) 그것을 대화 맥락에 실으면 된다.
**권하는 길.** AIDataHub 도구는 게이트웨이가 믿을 만한 사용자 표지를 넘겨줄 수 있을 때만 둔다. 지금은 미룬다.

### AD-09 — 병합의 레코드 m3 시그니처
**확인.** 이미 됐다. `a7a2ee4` 는 운영 값이 비어 있으면 채우고, `722d7a0` 은 제목과 본문 해시가 같을 때만 채우게 했다(`merge-from-drive.sh:105-119` · `:152`). 덤프가 같으면 포털이 병합을 건너뛴다(HWAXPortal `infra/scripts/update-all.sh:1152-1154`). 게다가 cae00 스케줄러가 1분마다 레코드 500건씩 시그니처를 채운다(`api/main.py:192-201`).
**몫.** 운영이 다시 세기만 하면 된다.
**권하는 길.** `SELECT count(*) FILTER (WHERE signature_embedding_m3 IS NULL) FROM records WHERE deleted_at IS NULL;` 로 센다. 0 이 아닐 때만 원인을 본다.

### AD-10 — delib-baseline-defender 등록
**확인.** 등록만으로는 효과가 없다. 엔진은 `DELIB_KNOWLEDGE_SYNTHETIC_SEATS` 에 적힌 좌석에만 지식카드를 묻는다(HWAXAgentServer `deliberation.py:3043-3050`). 레코드가 0건인 좌석은 `agent_search` 가 거절한다(`mcp_runtime.py:541-544`).
**몫.** 먼저 카드 묶음을 정하는 쪽(엔진 · 포털)이 정한다. 그다음 AIDataHub 등록(데이터 작업), 마지막으로 엔진 env 한 줄이다.
**권하는 길.** 근거로 삼을 카드(예: 지난 기각 선례)를 정한 뒤 dev 에 등록하고 레코드를 묶는다. 병합으로 cae00 에 보내고 엔진 env 를 고친다. 그 전에는 두지 않는다.

## 4. 질문

**AD-11 — materialtwin 동기화가 이미 있는 content 를 덮어쓰나.** 덮어쓴다. 목록 항목을 바로 변환하고(`sync_svc.py:875-906`, 상세 조회 없음) `external_id_map` 으로 기존 ID 를 찾는다(`routes/records.py:689-725`). 본문 해시 · 제목 · 요약 가운데 하나라도 다르면 content 를 포함한 모든 칸을 바꾸고(`db_writer.py:422-447`), 절을 모두 다시 넣는다(`:486`). 단, 조건이 셋 있다. 첫째, 동기화가 도는 박스에서만 그렇다. cae00 은 지금 가드에 막혀 있다. 둘째, 매핑된 레코드가 소프트 삭제돼 있으면 덮지 않고 실패로 센다(`records.py:707-718`). 셋째, 절을 여러 개로 받는 것은 MaterialTwinWeb 이 `sections` 를 내보낼 때뿐이다. 없으면 6만 자에서 잘린 body 를 받는다(`sync_svc.py:281-291`, HH-01).

**AD-12 — cae00 updated_at 이 비면 dev 가 이기나.** 조건식은 그렇게 쓰여 있지만 그런 행은 없다. 조건식은 `t.updated_at IS NULL OR EXCLUDED.updated_at > t.updated_at` 다(`merge-from-drive.sh:102`). b401f88 판에서는 `>=` 였는데 `a7a2ee4` 가 `>` 로 바꿨다. 실제로 덮이는 길은 셋이다.
1. dev 쪽 행이 더 늦게 고쳐졌을 때다. he-* 는 박스마다 `sync-he-personas.py --apply` 가 그 박스 게이트웨이의 앱으로 만든다(HWAXPortal `infra/scripts/sync-he-personas.py:16-17`). 그래서 dev 에서 나중에 돌리면 다음 병합이 cae00 판을 dev 판으로 바꾼다.
2. updated_at 칸이 없는 표는 키가 같으면 늘 dev 가 이긴다(`:147-159`). agent_records · record_sections · record_attachments · agent_sample_embeddings · external_id_map · doc_types · org_* · mcp_upstreams 가 그렇다.
3. 병합은 행을 지우지 않는다.

권하는 길은 포털 HP-35 를 한 걸음 더 나가는 것이다. 병합 뒤 cae00 에서 `--apply` 를 다시 돌리면 바뀐 칸만 PATCH 하므로 cae00 쪽이 다시 앞선다.

**AD-13 — 지우기를 어디서 하나.** 양쪽 다 지운다. dev 먼저, cae00 다음이다.
- **cae00 에서만 지우면.** 전문가 행은 다음 병합 때 다시 들어온다(`:133` — 충돌이 없으니 INSERT 된다). agent_records 도 돌아온다(`:153`). 소프트 삭제한 레코드는 잠시 남는다. 하지만 dev 쪽 행이 한 번이라도 바뀌면 삭제 안 된 dev 판으로 되살아난다. dev 쪽 updated_at 은 단건 GET 이나 dev 에서 전문가를 지울 때의 `array_remove`(`agent_svc.py:218-221`)로도 오른다.
- **dev 에서만 지우면.** 레코드의 소프트 삭제는 퍼진다. 전문가 행과 agent_records 는 cae00 에 그대로 남는다.
- **하드 삭제는** 어느 쪽에서 해도 퍼지지 않는다.

**순서.**
1. dev 에서 레코드를 소프트 삭제한다.
2. dev 에서 전문가를 지운다.
3. 새 덤프를 만든다.
4. cae00 에서 병합한다.
5. cae00 에서 전문가를 지운다.
6. 다음 병합 뒤에 §7 시험으로 확인한다.

병합이 3 으로 끝나면 표식이 남지 않아 옛 덤프가 다시 들어간다(`update-all.sh:1162-1167`). 그러니 표식을 꼭 본다.

**AD-14 — 동기화를 켜지 않으면 154장은 어떻게 고치나, 왜 1번 절만 비었나.** 까닭은 AD-01 의 (A)와 (B)다. 코드로는 이 둘만 남고, 질의 하나로 가린다. (B)이면 동기화 없이 평탄화를 고치고 색인 CLI 를 돌려 각 박스에서 고친다. (A)이고 content 가 폴백이면 dev 동기화와 병합으로 레코드 행을 바로잡고, cae00 에서 색인을 다시 지어 남은 절을 걷어 낸다. 정기 동기화는 꺼 둔 채 한 번만 받는 길도 있다. 수동 실행은 `enabled=false` 여도 돈다(`sync_svc.py:682-683`). 다만 가드는 그대로 걸린다(`:686`).

**AD-15 — env 는 어느 파일에 두나.** `deploy/apptainer/.env` 가 맞다. `start_api.sh:7` 의 `load_env` 가 이 파일을 `set -a` 로 읽어 내보내고(`_common.sh:86-97`), uvicorn 이 그 환경을 물려받는다(`start_api.sh:215-219`). watchdog · boot · restart 도 모두 `start_api.sh` 를 거친다. `api_server/.env` 는 기동할 때마다 다시 써진다(`start_api.sh:17-44`). 게다가 가드와 키 읽기는 pydantic 설정이 아니라 `os.environ` 을 본다(`url_safety.py:110`, `sync_bootstrap.py:66`). 덧붙일 것은 넷이다.
1. `SF_API_KEY` 도 같은 파일에 넣는다.
2. 키는 기동 때 DB `sync_sources.api_key` 에 평문으로 들어간다(`sync_bootstrap.py:148-152`). env 를 지워도 DB 값은 남는다. 병합 전 스냅샷에도 실린다(`merge-from-drive.sh:46-49`).
3. 넣은 뒤에는 API 를 다시 띄운다(`99cae7b`).
4. env-sync 가 채워 주지 않으니(N4) 사람이 직접 넣는다.

**AD-16 — BGE-M3 전환 알림.** 체크리스트는 포털 리포의 `docs/embedder-bge-m3/checklist.md:18`(B6, 아직 `[ ]`)이다. 포털 세션이 날짜와 함께 고친다. AIDataHub 몫은 없다.

## 5. 결정

### AD-17 — 정기 동기화 셋을 다시 켤지

**지금 상태.** cae00 은 사실상 이미 (나)다. 가드가 막고 있고(`url_safety.py:117-123`), 원장에는 `blocked` 로 남는다(`sync_svc.py:686-703`).

**(가) cae00 에서 다시 켠다.**
- **좋아지는 것.** cae00 에서 생긴 원천 글이 dev 를 거치지 않고 들어온다. 빈 요약 채우기(`5ca5c45` · `13ae431`)와 재료 카드 절 나누기(`57397d9`)가 cae00 에 바로 반영된다. AD-01 의 (A)는 다시 받으면 해결된다.
- **위험.**
  1. 두 박스가 함께 쓰게 된다. N3 대로 ID 가 겹치고 중복 카드가 생긴다. 그래서 한 소스는 한 박스에서만 받아야 한다.
  2. MXWP 목록은 `audience=org` 를 줘야 한다. 이것은 `list_filter` 설정으로 넣는다. 키의 역할은 MXWP 담당이 확인한다.
  3. 원인이 (B)라면 AD-01 은 그대로 남는다.
- **보안.** env 로 `AIDH_SYNC_ALLOW_INTERNAL=true` 를 켜면 소스 셋만 열리는 게 아니다. 모든 동기화 URL 에 대해 루프백 · 사설 IP · 모든 포트가 열린다(`url_safety.py:117-123` · `:136-139` · `:163-167`). 메타데이터 주소만 계속 막힌다(`:125-127`). 소스 등록 · 수정 API 도 같은 가드를 쓰는데(`routes/sync.py:162-165` · `:216-220`), 익명만 아니면 어떤 키로든 부를 수 있다(`api/auth/dependencies.py:102-108`). 포털 SSO 가 발급한 키도 마찬가지다. 그러면 대시보드 사용자 누구나 박스 내부의 아무 포트로 GET 을 보내는 소스를 등록할 수 있다. 코드 허용 목록(정확한 `scheme://host:port` 셋)으로 바꾸면 그 셋만 열린다. httpx 는 기본으로 리다이렉트를 따르지 않으므로(`sync_svc.py:784`) 허용 목록을 우회할 길도 없다. 25줄과 시험이다.

**(나) 켜지 않는다 — 덤프 병합을 정본으로 둔다.**
- **좋아지는 것.** 쓰는 박스가 하나뿐이라 ID 가 겹칠 일이 없다. SSRF 문도 지금처럼 닫혀 있다.
- **남는 것.** cae00 에서만 생긴 원천 글은 들어오지 않는다. 여러 개선은 dev 동기화가 실제로 돌 때만 cae00 에 온다. 그러니 dev 원장의 `last_status` 를 먼저 확인한다.
- **할 일.** `.env.example:178` 을 주석으로 바꾼다(N4). 소음을 끄려고 API 로 PATCH 해도 소용없다. 부팅할 때마다 yaml 의 `enabled: true` 가 다시 써지기 때문이다(`sync_bootstrap.py:169-182`). 박스별로 끄는 env 손잡이(10줄)를 새로 두거나, `blocked` 상태로 그냥 둔다.

**판단 기준.** 소스마다 '새 글이 어느 박스에서 생기는가' 를 묻는다.

**권고(검토자 의견).** (나)를 기본으로 한다. AD-01 의 질의와 평탄화 수정은 어느 쪽을 고르든 먼저 한다. cae00 에서만 생기는 원천이 확인된 소스만 (가)로 옮긴다. 그때도 env 로 넓게 열지 않고 코드 허용 목록을 쓴다. dev 에서는 그 소스를 끄고, MXWP 는 `audience=org` 로 받는다.

### AD-18 — 글이 없는 MX 백서 카드를 내릴지

**사실.** '글 없음' 가운데 일부는 (B)의 평탄화 누락일 수 있다. 내리는 방식에 따라 뒷일이 다르다. 소프트 삭제한 카드는 동기화가 그 문서를 다시 받을 때마다 실패로 센다(`records.py:707-718`). 하드 삭제는 매핑까지 지우므로(`models.py:831-834`) 동기화가 새 ID 로 다시 만든다. 병합으로 퍼지는 것은 소프트 삭제뿐이다.
- **(가) 내린다.** 목록이 깨끗해진다. 하지만 원문이 살아 있다면 고칠 수 있었던 카드를 잃는다.
- **(나) 둔다.** 제목만 있는 카드가 남는다. 대신 되돌릴 일이 생기지 않는다.

**권고(검토자 의견).** 지금은 (나)다. 색인을 다시 지은 뒤 다시 센다. 그래도 비어 있고 MXWP 원문도 비었다고(MW-07) 확인된 카드만 내린다. 내릴 때는 MXWP 에서 보관(archive) 처리하고, AIDataHub 에서는 dev 에서 소프트 삭제해 병합으로 퍼뜨린다.

## 6. 줄 번호 대응표(요청서 → HEAD `ac42bc6`)

| 요청서 | 요청서 기준 판 | HEAD |
|---|---|---|
| `_resync_sections :602-614` | b401f88 | `api/ingest/db_writer.py:623-679`(지우기 `:631-635`) |
| `recommend_svc.py:833-839` | b401f88 | `:843-849` |
| `recommend_svc.py:450` | b401f88 | `build_context_bundle` 안(`:453-`). agent_search 범위는 `mcp_runtime.py:518-545` |
| `routes/records.py:239` | b401f88 | `:244` |
| `records.py:52-68` | b401f88 | `:53-73` |
| `models.py:242` | b401f88 | `:282-287`(+ 트리거 `0002:32-46`) |
| `merge-from-drive.sh:119` | b401f88 | 조건식 `:102`(`>=`→`>`) · agents `:150` |
| 옮겨지지 않음 | — | `url_safety.py:110-122` · `:18-20`, `routes/sync.py:309`, `routes/agents.py:208`, `normalizer.py:501`, `config.py:42`, `record_query_svc.py:91`, `converter_dispatch.py:109-113`, `0031:12-14`, `sync_sources.yml:138-139` · `:172` |
