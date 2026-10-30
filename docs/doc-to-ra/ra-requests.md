# Report Archive 에 드리는 요청 — 문서 정밀 변환(DocForge) 배달 (2026-10-27)

> 읽는 사람 — Report Archive(RA) 관리자 · 개발자. 보내는 쪽 — HWAX 포털 doc-to-ra(DocForge). 계획 [PLAN.md](PLAN.md) §12-2 · §12-10, 결정 [context-notes.md](context-notes.md)
> DF-D17 · DF-D23, 조사 근거 [research.md](research.md).
> RA 사실은 RA `v0.167.0`(`3ece194`) 코드를 **읽어서** 확인했다(고치지 않았다). 줄 번호는 그 판 기준이다.
> 지금도 배달은 돈다 — 아래는 없으면 멈추는 것이 아니라, 있으면 실패 · 남는 파일 · 손 작업이 줄어드는 것이다.
> 10-31 — R3 를 실제 SP 공개(과제의 key 는 과제명 · 과제코드는 `properties.task_code`)에 맞춰 고쳤다(DocForge R-D48).

## 0. 지금 배달 길

1. DocForge 가 패키지를 만든다 — `report.json`(편집기 JSON 가져오기 꼴 `report_archive_draft_v1` · 위젯은 전부 `extra_blocks` · 리소스는 `res://<이름>` 자리표) +
   `resources/`(그림 · 원본 파일).
2. 포털이 **사용자 명의**(RA SSO 위임 또는 사람마다 '외부 연결' 토큰)로 리소스마다 `POST /api/files` → 받은 id 로 자리표를 바꾼다.
3. `POST /api/reports` 엄격 생성 — template `__import_blank__`@1 · `pages[].extra_blocks · content · blocks_order`. 25MB 를 넘는 리소스는 올리지 않고 그 칸을
   비운 뒤 사람에게 알린다. `entity_ids` 는 보내지 않는다.

## 1. 요청 한눈에

| # | 요청 | 왜 | 급함 |
|---|---|---|---|
| R1 | `__import_blank__` 템플릿을 늘 있게(이관 시드 또는 확인 창구) | 새 RA 에서 첫 배달이 400 으로 실패한다 | 높음 |
| R2 | 엄격 생성의 **검증만**(dry_run) — 길게는 패키지 한 번에 넣기 | 생성이 거절되면 먼저 올린 파일이 고아로 남는다 | 중간 |
| R3 | SP 과제코드 · 모델명을 RA 엔티티의 `code`(또는 별칭)로 — 축 정하기 | RA 자동 태깅이 DocForge 의 '연결된 과제 · 모델' 칸으로 엔티티를 저절로 잇는다 | 중간 |
| R4 | 원본 첨부(Office · PDF)의 상한 | 25MB 넘는 원본 · 그림은 못 싣는다 | 낮음 |
| R5 | 운영 확인 두 가지 · 결함 하나 | 고아 파일 청소 타이머 · 자동 태깅 켬 · `entity_ids` 가 틀리면 반쯤 만들어짐 | 확인 |

## R1. `__import_blank__` 템플릿을 늘 있게

**지금.** 템플릿은 `POST /api/imports/pptx` 가 처음 불릴 때 `ensure_import_template()` 이 만든다(`backend/app/modules/imports/routes.py:30-50` · 부르는 곳은
`:97` 하나). 이관 · 기동 시드는 없다. 없으면 엄격 생성이 `_validate_page` 에서 "Template not found: __import_blank__@1" 로 **400**(`reports/services.py:1106-1110`)
— 넣기 전에 걸러 아무것도 저장되지 않는다. 바깥에서 만들 길도 없다 — `POST /api/templates` 의 `template_id` 는 `^[a-z0-9][a-z0-9-]*$` 라 이 이름을
받지 않는다(`templates/schemas.py:66`).

**겪는 일.** 새로 깐 RA(또는 아직 아무도 PPTX 가져오기를 안 쓴 RA)에서 정밀 변환의 첫 배달이 실패한다.

**바라는 것.** 둘 중 하나 — ① 이관에서 `__import_blank__`@1 을 시드한다(`ensure_import_template` 과 같은 값 — 전사 공개 · 게시 · 빈 블록). ② 로그인한
사용자가 부를 수 있는 '가져오기 템플릿 확인' 창구(멱등 — 있으면 그대로).

**그동안 우리 쪽.** 배달 실패 문구가 'RA 웹 가져오기를 한 번 쓰면 생긴다' 고 안내한다(server-setup §7). RA 가 동의하면, 템플릿 없음으로 실패했을 때 포털이
빈 PPTX 하나로 `/api/imports/pptx` 를 불러 템플릿을 만들고 한 번 다시 넣을 수도 있다 — RA 의 부수 효과에 기대는 길이라 동의 없이는 하지 않는다.

## R2. 엄격 생성의 검증만 — 길게는 패키지 한 번에

**지금.** 보고서와 파일을 한 번에 만드는 창구는 없다 — `/api/imports/pptx` 는 초안만 돌려주고(`imports/routes.py:149-158`), `report_archive_draft_v1` 은
화면(편집기)에서만 읽는다(`frontend/src/modules/reports/ReportDetailPage.jsx:10293-10302`). 그래서 파일 N 개를 먼저 올리고 보고서를 만든다. 생성이 거절되면
(위젯 검증 · 템플릿 없음) 올린 파일은 어디에도 안 걸린 채 남고, 밤마다 도는 고아 청소(`backend/app/modules/files/orphans.py` · 48시간 유예 ·
`deploy/reportarchive-orphan-cleanup.timer.template`)가 그 타이머가 깔린 박스에서만 지운다. `POST /api/reports` 에는 `dry_run` 이 없다(`ai-draft` 에는 있다 —
`reports/routes.py:890`).

**겪는 일.** 거절된 배달마다 파일이 남는다. 포털은 '앞서 올린 리소스 N개는 RA 에 남았다' 고 알릴 뿐 지울 길이 없다.

**바라는 것.** ① `POST /api/reports` 에 검증만 하는 갈래(`dry_run` — 템플릿 · 위젯 · 배치 검증을 하고 저장하지 않는다). 파일 id 자리는 아직 없으니 자리표
(`res://…`)를 파일 칸으로 받아 주거나 파일 칸 검증을 건너뛰면 된다. 포털은 이것을 먼저 불러 통과할 때만 파일을 올린다. ② 길게는(§12-2) **패키지
가져오기** — zip(report.json + resources/)을 사용자 토큰으로 한 번에 올리면 RA 가 파일과 보고서를 한 트랜잭션으로 만든다. 그러면 어느 클라이언트든
같은 패키지를 넣을 수 있다.

**그동안 우리 쪽.** DocForge 시험이 RA 자신의 위젯 검증(`validate_template_schema` · `validate_report_content`)을 하위 프로세스로 불러 패키지를 미리
대조한다(DocForge `tests/test_ra_contract.py`). 그래서 위젯 검증 거절은 드물고, 남는 경우는 주로 템플릿 없음(R1)이다.

## R3. SP 과제코드 · 모델명을 RA 엔티티의 code 로 — 축 정하기

**지금.** RA 는 **저장할 때마다**(API 로 만든 보고서 포함 — after_commit 훅, `reports/models.py:465-527` · `autotag_on_save` 기본 켬 `config.py:227`) 본문에
엔티티의 값 · 코드 · 별칭이 글자 그대로(대소문자 무시 · 영숫자 경계) 나오면 그 엔티티를 붙인다(`entities/autotag.py:91` 이하 — 결정적 매칭은 바로 적용).
본문 추출은 쪽마다 content 의 글을 모두 훑으므로 key_value 칸도 본다(`widgets/text_extraction.py`). 엔티티에는 외부 키 칸이 없고(`entities/models.py:190-249` —
`code` 는 64자 · 유일하지 않음), `GET /api/entities?q=` 는 별칭을 보지 않으며, 별칭까지 보는 판별은 `GET /api/ai/resolve`(MCP `resolve`)다.
key_value 항목의 `meta.is_entity_id` · `linked_entity_type` 는 스키마에만 있고 읽는 잡이 없다(`widgets/validation.py:80-85`).

**DocForge 가 하는 것(E14 · HH-03).** SP 허브 거울(과제 · 개발모델)의 식별자가 원문에 글자 그대로 나오면 첫 쪽 맨 위에 key_value 「연결된 과제 ·
모델」(블록 `df_1_0` — 값은 과제 '과제코드 과제명' · 모델 '모델명 이름')과 자유 태그(과제코드 · 모델명)를 단다. 실제 공개의 과제는 key 가 과제명이고
과제코드는 `properties.task_code` 다 — 어느 쪽으로 적혀도 잇고, 같은 과제코드가 과제 둘에 걸리면 잇지 않는다. 옛 · 합쳐진 식별자로 적혀 있으면 SP 의
개명 · 합침 기록으로 **지금 것**으로 풀어 적는다.
`entity_ids` 는 보내지 않는다(DocForge 는 RA 엔티티 id 를 지어내지 않는다).

**바라는 것.** RA 가 SP 의 과제 · 개발모델을 엔티티로 둘 때(또는 이미 둔 것에) **과제는 과제코드(SP `properties.task_code`), 개발모델은 모델명(SP
key)을 `code` 나 별칭으로** 둔다(과제명은 엔티티 값으로 — 과제의 SP key 는 과제명이라 `code` 64자를 넘을 수 있다). 그러면 따로 연동하지 않아도 RA
자동 태깅이 그 칸으로 엔티티를 잇는다 — 원문에 옛 식별자가 적혀 있어도 칸에는 지금 것이 있다. 정해 주실 것 — ① SP 과제(plm_task) · 개발모델
(plm_model)을 어느 축에 두나(`project` · `model` 이 맞는지). ② 같은 축 안에서 `code` 의 유일성을 지킬지(지금 `code` 는 유일하지 않다 — SP 에서도 같은 과제코드가 과제 둘에 걸릴 수 있다). ③ 더 확실히 하려면
엔티티에 출처 · 외부 키(`source` · `external_id`)와 그것으로 찾는 창구.

**그동안 우리 쪽.** 칸 · 태그만 단다. RA key_value 의 `multi`(값 여러 개 — 화면은 ', ' 로 잇는다, `KeyValue.jsx:645-651`)는 확인했으나 아직 글 하나로 낸다.

## R4. 원본 첨부의 상한

**지금.** 파일 상한은 확장자로만 갈린다 — 일반 25MB(`upload_max_bytes`) · CAD 200MB · 영상 1GB(`files/routes.py:65-84` · `config.py:121-135`). 넘으면 413
"파일이 너무 큽니다. 최대 N MB.". 이어 올리기(분할 · 재개)는 없다. Office · PDF 는 일반(25MB)이다.

**겪는 일.** 그림이 많은 덱 · 큰 Excel 의 **원본 첨부**와 큰 그림은 싣지 못하고 칸을 비운 채 알린다(사람이 RA 에서 직접 붙인다).

**바라는 것.** Office(.pptx · .docx · .xlsx) · PDF 에 CAD 처럼 따로 둔 상한(예 200MB) — 또는 보고서 첨부 칸에 한해 큰 상한. RA 가 정한 값으로
포털 설정(`docforge_ra_file_max_mb`)을 맞춘다.

## R5. 운영 확인 두 가지 · 결함 하나

1. **고아 파일 청소 타이머** — `reportarchive-orphan-cleanup.timer` 가 cae00 RA 에 깔렸는지(없으면 R2 의 남는 파일이 쌓인다).
2. **자동 태깅** — cae00 RA 에서 `autotag_on_save` 가 켜져 있는지(R3 의 길이 이것에 기댄다).
3. **결함** — `create_report` 는 보고서와 첫 버전을 커밋한 **뒤에** `entity_ids` 를 검증한다(`reports/services.py:1381-1401`). 없는 id 가 섞이면 400 을 돌려주지만
   보고서는 이미 있다. 우리는 `entity_ids` 를 보내지 않아 겪지 않지만, 넣기 전에 검증하면 다른 클라이언트도 안전하다.

## 우리가 지키는 것

- RA 리포는 고치지 않고 import 하지 않는다 — RA 형식은 DocForge `docforge/ra/widgets.py` 에 우리 쪽 계약으로 옮겨 적고, RA 를 받을 때마다 계약 시험이 먼저 깨진다.
- RA 에 넣는 것은 포털이 사용자 명의로 하는 엄격 생성뿐이다. DocForge 는 RA 자격을 쥐지 않는다.
- 문서 글은 기록에 남기지 않는다(건수 · 글자 수 · 시간만).
