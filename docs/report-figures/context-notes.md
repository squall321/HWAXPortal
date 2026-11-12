# 보고서에 도구 그림 싣기 — 결정 기록

> 계획 [PLAN.md](PLAN.md) · 체크리스트 [checklist.md](checklist.md). 대조 시점 — 포털 main `c33c511a` · 에이전트 서버 main `e13e3e3b` ·
> RA 참고 원본 `/home/koopark/claude/ReportArchive`(09-23 dev 사본, 읽기만 — 배포된 RA 는 더 새것이다). 줄 번호 대신 함수 이름으로 적는다.

## RF-1 창구 둘 — 게이트웨이 계약 하나 · 에이전트 서버용 올리기 하나

- `POST /agent/figures/to-report`(게이트웨이 계약) — multipart `meta`(JSON — report_id · caption · page? · tool · mime · sha256 · filename · ref) +
  `file`. 그 사람 명의로 RA `POST /api/files` → 그 보고서 `page` 쪽(없으면 마지막 쪽) 끝에 그림 칸 하나(`PATCH /api/reports/{id}/ai-draft` 의
  `extra_blocks`). 답 `{ok, report_id, file_id, page, block_index, url, block_id, replaced}` — 계약에 없는 칸은 `block_id` · `replaced` 둘을 더했다
  (덧붙임이라 받는 쪽을 깨지 않는다). `block_index` 는 RA 답의 그 쪽 `blocks_order` 안에서 0부터 센 자리, `url` 은 RA 가 준 `/w/<공간>/reports/<번호>`
  (DocForge 배달과 같은 꼴 — 포털의 RA 공개 길 `/report-archive` 는 붙이지 않는다). 실패는 `{ok:false, error, detail}` 와 맞는 HTTP 상태.
- `POST /agent/figures/upload` — 같은 검사 · 같은 올리기, 보고서는 건드리지 않는다. 답 `{ok, file_id}`.
- 왜 둘인가 — `/보고서` · 심의 보고서에서 그림이 있던 **그 자리**에 '올리지 못함' 까닭을 남기려면 보고서를 만들기 **전에** 올린 결과를 알아야
  한다. 만든 뒤 그림마다 to-report 로 붙이면 실패한 그림의 까닭을 본문 그 자리에 쓸 수 없다(본문은 이미 나갔다). 그래서 에이전트 서버는 먼저
  올리고, 보고서를 만드는 한 번의 호출(`create_report_draft` · `update_report_draft`)에 그림 칸을 함께 싣는다. 보고서 쓰기가 한 번이라 반쯤
  붙은 보고서가 없다. 값 — 보고서 저장이 실패하면 올린 그림 파일은 RA 에 남는다(주인은 그 사람, DocForge 배달과 같다).

## RF-2 자격 — 대화 저장과 같은 의존성, 사람 PAT 만

- 게이트웨이의 포털 경유 도구(`save_conversation` → `/agent/conversations`)가 쓰는 `principal_pat_or_session` 을 그대로 쓴다 — 사람 PAT(청중
  `pat_chat_audience`) 또는 세션 + CSRF. 게이트웨이는 공유 비밀(GW_TOKEN)을 포털로 넘기지 않는다(`_caller_bearer`) — 공유 비밀 + 사용자 머리로
  받는 길은 만들지 않았다.
- 쓰기라 읽기 전용 PAT 는 403(`read_only_token`). 판정은 게이트웨이 `rest_proxy.is_read_only` · 루틴 창구 `routine_routes._read_only_pat` 와
  같다(scopes 에 read 가 있고 write 가 없을 때만). 챗 PAT(`["chat"]`)은 쓴다 — 웹 챗 `/보고서` 의 에이전트 서버가 그 토큰으로 부른다. 루틴의
  함수를 import 하지 않은 것은 절차 라우터 등록이 실패해도 포털이 뜨게 둔 자리(main.py try)라서다 — 같은 판정인지는 시험이 표로 견준다.
- `plat:reportarchive` 가 없으면 403(RA 를 여는 `/agent/ra/reports/{id}/open` 과 같다).
- RA 토큰은 `routes._ra_user_token`(위임 먼저 · 등록 토큰 다음) — 서비스 계정으로 내려가는 길은 없다. 위임 토큰을 RA 가 401 로 거절하면 한 번만
  새로 받는다(DocForge · 발표자료와 같은 규칙).

## RF-3 RA 에 올리는 코드는 하나 — `RaSession`

- DocForge `deliver` 안의 `post` 닫힘(토큰 · `X-Workspace-Slug` · 401 이면 한 번 새 토큰 · 올린 스트림 되감기)을 `docforge_delivery.RaSession`
  으로 떼었다. `deliver` 와 그림 창구가 같이 쓴다. `deliver` 의 동작(주소 · 머리 · 오류 문구 · 다시 받기)은 바꾸지 않았다 — 기존 시험이 그대로
  통과한다.

## RF-4 그림 검사 — 꼴 · 크기 · sha256

- 선언한 mime 은 `image/png` · `image/jpeg`(`image/jpg` 도) · `image/gif` · `image/webp` 만. SVG 는 415 와 까닭(스크립트를 품을 수 있는 꼴 —
  RA 가 자기 주소에서 그대로 내면 그 주소에서 돈다). 그 밖도 415.
- 내용도 본다(머리 바이트 — 에이전트 서버 `vision.sniff` 와 같은 넷). 내용이 그림이 아니면 415. 선언과 내용이 다른 두 그림 꼴이면(예 png 라
  했는데 jpeg) 내용의 꼴로 올린다 — 에이전트 서버 그림 읽기와 같은 원칙(이름 · 선언이 아니라 내용).
- 크기는 `docforge_ra_file_max_mb`(RA `/api/files` 상한 25MB 를 이 박스가 적는 손잡이 — 같은 RA 상한이라 같은 값을 쓴다). 본문을 읽기 전에
  `Content-Length` 로 먼저 막는다(없으면 411 · 넘으면 413 — PC 도우미 창구와 같은 꼴), 읽을 때도 상한 + 1 바이트까지만 읽는다.
- sha256 은 64자리 16진이어야 하고 받은 바이트와 같아야 한다(400 `sha256_mismatch`).

## RF-5 그림 칸의 꼴

- `{"id": "fig_<sha256 앞 16자>", "type": "image", "props": {"max_count": 1}, "content": {"files": [{"file_id", "caption", "alt"}]}}`.
- id 는 RA 블록 id 규칙(`^[a-z][a-z0-9_]{0,63}$` — widgets/validation.py)에 맞춘다. 하이픈을 쓰면 보고서 저장 전체가 거절된다.
- 캡션은 `files[].caption`(그림 아래 figcaption, 상한 500자 — `_image_content`), 넘으면 499자 + '…'. alt 는 상한 200자. RA image 위젯의
  content 는 `additionalProperties: false` 라 `filename` 같은 칸을 넣으면 저장 전체가 거절된다 — 넣지 않는다.
- 같은 그림(sha256)을 같은 쪽에 다시 넣으면 같은 id 라 RA 가 그 칸을 갈아 끼운다(병합 규칙 '같은 id 는 교체') — 다시 보내기가 칸을 늘리지
  않는다. 답의 `replaced` 가 그 경우를 말한다.

## RF-6 쪽 · 동시 호출

- `page` 가 없으면 마지막 쪽. 쪽 수는 RA `GET /api/reports/{id}/outline` 의 `page_count`(본문 전체를 읽지 않는다). 있는 쪽만 — `page` 가 쪽 수를
  넘으면 400(`bad_page`, RA 의 '끝 다음 쪽 = 새 쪽 추가' 규칙을 이 창구로는 쓰지 않는다).
- RA 의 ai-draft PATCH 는 읽고 · 합치고 · 쓴다. 같은 보고서에 그림 여러 장을 한꺼번에 보내면(개인 Claude 의 병렬 도구 호출) 앞 쓰기를 뒤 쓰기가
  덮어 칸이 사라질 수 있다. 포털은 uvicorn 프로세스 하나라 보고서마다 asyncio 잠금 하나로 줄 세운다(DocForge 잡 잠금과 같은 꼴).
- ⚠ 이 잠금은 **포털을 지나는 to-report 끼리만** 줄 세운다(반대 검토 F3 — 가짜 RA 로 재현). 같은 보고서에 게이트웨이의 `update_report_draft` 같은 다른
  쓰기가 겹치면(포털의 PATCH 가 읽은 뒤 · 쓰기 전에 그쪽이 읽고, 포털 뒤에 쓰면) 포털이 이미 ok 를 돌려준 그림 칸을 그 쓰기가 지운다. RA 의 ai-draft
  PATCH 는 revision 검사 · 행 잠금이 없다(`update_report(expected_revision=None, require_lock=False)`). 포털만으로는 닫지 못한다 — 게이트웨이가
  보고서마다 RA 쓰기 도구와 그림 넣기를 줄 세우거나, RA 가 ai-draft 에 expected_revision 을 받아야 한다(게이트웨이 · RA 몫).
- 편집 권한은 RA 가 정한다 — 포털은 권한 규칙을 다시 짓지 않는다. 올리기 **전에** 같은 PATCH 를 `dry_run` 으로 물어(RA 는 권한 · 발행 · 편집 잠금
  가드를 지난 뒤에만 미리보기를 내고 아무것도 바꾸지 않는다) 거절이면 파일을 올리지 않는다(반대 검토 F7 — 고아 파일). 거절은 403(`not_editable`),
  편집 화면이 열려 있으면 409(`report_locked`). 가드 뒤의 거절(검증 400 · 그 사이 잠금 409)만 '올린 파일이 RA 에 남았다' 고 말한다.

## RF-7 RA 가 칸을 버렸으면 실패다

- RA 는 형식이 틀린 extra 블록을 경고만 남기고 **조용히 버린다**(만들기는 된다). PATCH 답의 그 쪽 `blocks_order` 에 우리 id 가 없으면 502
  (`ra_dropped_block`)와 RA 경고를 돌려준다 — 올린 파일은 RA 에 남았다고 말한다.

## RF-8 RA 오류를 옮기는 표

| RA 답 | 포털 답 |
|---|---|
| outline 404 | 404 `report_not_found` |
| outline · PATCH(dry_run · 진짜) 403 | 403 `not_editable`(RA 의 까닭을 붙인다) |
| 올리기 403 | 403 `forbidden_by_ra` |
| PATCH 409 | 409 `report_locked` |
| 401(다시 받은 뒤에도) | 502 `ra_token_rejected` — 부른 쪽의 포털 자격이 아니라 그 사람의 RA 토큰 문제다 |
| 413 · 415 | 413 `too_large` · 415 `unsupported_media_type` |
| 그 밖 4xx | 422 `ra_rejected` |
| 5xx · 답 꼴이 틀림(객체가 아닌 JSON 포함) | 502 `ra_error` |
| 연결 실패 · 시간 초과 | 502 `ra_unreachable` |
| RA 연결 없음(`_ra_user_token`) | 그 함수의 상태(400 · 502) `no_ra_connection` |

## RF-9 에이전트 서버 — 보고서 글의 그림을 올려 그림 칸으로(`report_figures.py`)

- 찾는 것 — 블록 글의 마크다운 그림 `![설명](/agent/artifacts/<이름>)` 과 맨 주소 `/agent/artifacts/<이름>`(도구 결과의 '[생성된 이미지 URL …]'
  줄 · `captured.images[].url` 이 이 꼴이다 — 에이전트가 저장한 그림 블록). 확장자는 png · jpg · jpeg · gif · webp · svg. 처음 나온 차례, 같은
  그림은 한 번(이름 · 내용 해시 둘 다로 묶는다).
- 올리기 — `ARTIFACT_DIR` 의 바이트를 읽어 포털 `POST /agent/figures/upload` 에 **그 사람의 PAT**(`user_pat` — 웹 챗 · 웹 심의는 포털이 준 챗
  PAT)로. 게이트웨이 공유 비밀(GW_TOKEN)은 쓰지 않는다. 포털 주소는 `PORTAL_HTTP_BASE`(기본 `http://127.0.0.1:8723` — 모든 박스의 포털 자리,
  infra `_common.sh` PORTAL_PORT).
- 자리 — 올린 그림은 `[그림 N — 설명]`(설명이 없으면 `[그림 N]`, N 은 올린 것만 1부터), 못 올린 그림은 `[그림 — 올리지 못함: 까닭]`(설명이 있으면
  `… 까닭 · 설명]` — 어느 그림이었는지 읽는 사람이 안다). 설명은 그 그림의 처음 설명 하나라 같은 그림은 어디서나 같은 표지이고, 그림 칸의 캡션
  `그림 N — 설명` 과 짝지어진다. 칸은 RA 가 템플릿 칸 뒤에 차례대로 놓는다.
- 셈 — `/보고서` 는 result 사건의 `figures`({found, attached, failed, reasons — 다른 까닭만 앞 다섯, failed_refs — 못 들어간 그림의 주소 앞
  스물}), 심의는 outcome 사건의 `figures` 와 결정문 끝 안내. 이름만 다른 같은 바이트는 한 장으로 센다. 잡 원장은
  outcome 의 `figures` 를 `report_figures` 로 접고 `deliberate_result` 가 그 칸을 낸다(MCP 잡의 결과). 그림이 없으면 호출 인자 · 사건 · 잡 결과가
  지금과 바이트까지 같다(`extra_blocks` · `figures` · `report_figures` 칸을 싣지 않는다).
- 멈춤 — 포털 답이 그림 하나만의 문제(꼴 · 크기 · 해시 · RA 가 그 파일만 거절 — `too_large` · `unsupported_media_type` · `sha256_mismatch` ·
  `empty_file` · `bad_meta` · `ra_rejected`)면 다음 그림을 올린다. 그 밖(자격 · 연결 · RA 오류 · 토큰 거절)은 남은 그림도 같은 까닭이므로 더 부르지
  않고 같은 까닭을 그 자리에 남긴다 — 포털이 막히면 장마다 시간 한도(330초)를 기다려 `/보고서` 가 수십 분 걸리는 일을 막는다.
- RA 가 우리 칸을 경고로 버렸으면(경고 글에 칸 id) 그 그림을 '못 들어감' 으로 세고 안내에 까닭을 붙인다 — 본문 표지는 이미 나갔지만 결과 · 안내가
  말한다(RF-7 의 에이전트 서버 쪽).

## RF-10 사람 토큰이 없는 심의(MCP 로 연 잡)

- `deliberate_start` 등 MCP 입구의 잡은 사람 토큰이 없다(`delib_jobs.start` — "MCP 잡은 애초에 토큰이 없다"). 그 보고서는 게이트웨이가 서비스
  자격 + 사용자 머리로 RA 에 쓴다. 그림을 같은 서비스 자격으로 올리면 '그 사람 명의' 가 아니므로 올리지 않는다 — 글에 있던 그림은 그 자리마다
  `[그림 — 올리지 못함: 그 사람의 토큰이 없는 길(MCP 로 연 심의 등) …]` 를 남기고, 본문 밖 그림(RF-16)은 한 줄로 장수와 까닭만 적는다(반대 검토
  F2 — 같은 줄이 그림마다 늘어섰다). 잡 결과(`report_figures`)의 `failed_refs` 가 그 그림들의 주소다. 개인 Claude 가 게이트웨이의 그림 넣기
  (to-report)로 자기 PAT 로 넣을 수 있는 것은 그 바이트를 손에 쥔 그림뿐이다 — 에이전트 서버에 저장된 이 그림들을 개인 Claude 가 받아 올 길은 아직
  없다.

## RF-11 한 보고서의 그림 수

- 40장까지(RA 한 쪽 블록 상한 200 — `AI_MAX_BLOCKS_PER_PAGE` — 에 템플릿 칸을 두고 넉넉히). 넘는 그림은 그 자리에 까닭을 남긴다.

## RF-12 시간 제한

- 에이전트 서버 → 포털 한 장 330초, 포털 → RA 300초(DocForge 배달과 같은 값) — 안쪽이 먼저 걸려 까닭이 온다(시간 제한은 층이다).

## RF-13 하지 않은 것

- `/ai-data-hub/attachments/…` 그림(AIDataHub 첨부 — 브라우저는 nginx 길로 본다)은 아직 보고서 그림 칸으로 바꾸지 않는다. 글에 주소 그대로 남는다.
- 분석 루틴의 RA 초안(`routine_report_submit` → 포털 루틴 창구 → 게이트웨이 `create_report_draft`)은 이 길을 타지 않는다 — 루틴 보고서의 그림은
  그대로다.
- 챗에 사람이 올린 그림(이력의 `images` 칸)은 글에 주소가 없어 `/보고서` 가 보지 않는다(도구 그림만).
- 에이전트 서버 `vision.IMG_URL_RE`(챗 그림 읽기)도 이름 끝이 `\b` 라 '…png에' 를 놓친다(반대 검토 F1 의 같은 꼴) — 이 작업 밖이라 고치지 않았다.

## RF-14 아티팩트 주소의 보안 메모(넓히지 않음)

- 포털 `GET /agent/artifacts/{name}`(routes.py `get_artifact`)은 로그인한 누구에게나 이름을 아는 파일을 준다 — 이름은 sha256 앞 20자(80비트)라
  짐작은 못 하지만, 주소가 실린 글(공유한 대화 · 인사이트 카드 · RA 보고서)을 본 사람은 연다. 사람별 주인을 세는 장부가 없어 간단히 고칠 수
  없다 — 이 작업은 길을 넓히지 않았고, 보고서에서는 오히려 주소가 빠진다(그림 칸 · 표지로 바뀐다).
- 같은 길은 에이전트 서버의 `Content-Type` 을 그대로 실어 `.svg` 를 `image/svg+xml` 로 포털 주소에서 낸다 — 새 탭으로 직접 열면 그 SVG 의 스크립트가
  포털 주소에서 돈다. 이 작업이 RA 로 SVG 를 보내지 않는 까닭(RF-4)과 같다. 고치는 길(그 답에 `Content-Security-Policy: sandbox` ·
  `X-Content-Type-Options: nosniff`)은 따로 결정한다.

## RF-15 계약을 두 쪽에서 고정

- 포털 시험이 형제 리포 HWAXAgentServer 의 `report_figures.attach` 를 진짜 포털 앱(ASGI)에 물려 부른다 — meta 칸 이름 · 챗 PAT 자격 · 답의 꼴 ·
  그림 칸의 꼴(포털 `block()` 과 같다)이 어긋나면 거기서 걸린다. 형제 리포가 없으면 건너뛴다(다른 형제 리포 시험과 같은 꼴).

## RF-16 심의 중 도구가 낸 그림 — 본문에 주소가 없어도

- 좌석은 조회로 받은 그림을 발언에 주소로 적지 않는다(발언은 JSON 칸의 글이다). 본문의 그림 줄만 찾으면 StepForge · DynaForge 그림 대부분이 심의
  보고서에 길이 없다. 그래서 심의 단이 `app._turn_images` 에 그 단의 자루를 건다(`_turn_ids` 와 같은 자리 · 같은 꼴 — 선주입 · 지정 도구 · 좌석
  조회 태스크가 이 문맥을 물려받는다). 도구 래퍼(`_cap_tool` → `_stash_image_items`)가 저장한 MCP 이미지 블록이 담긴다.
- 보고서 단계에서 자루의 그림 중 블록 글에 주소가 없는 것을 근거 칸(background) 끝에 한 항목으로 더한다 — '심의 중 도구가 낸 그림(본문에 주소가
  없던 것)' 아래 그림 줄마다 그 그림을 받은 좌석 · 도구(공용 조회 풀에서 찾는다, 못 찾으면 '심의 중 도구 그림'). 그 뒤는 RF-9 와 같은 길이다.
- 재기동 뒤 제자리로 이은 심의는 끊기기 전 라운드의 자루를 되살리지 않는다 — 그 그림은 글에 주소가 있을 때만 실린다(재개 자료에 그림 주소를
  적지 않았다).
- `/보고서` 는 대화 글만 본다 — 챗 턴은 모델이 인용하지 않은 도구 그림을 코드가 답 끝에 `![생성된 그래프](…)` 로 붙이므로 글에 이미 있다.

## RF-17 반대 검토(11-02) — 재현한 것만 고침

- F1 — 맨 주소 바로 뒤의 한글 조사('…png에')를 `\b` 가 막아 그림이 표지 · 셈 없이 포털 상대 주소로 RA 에 갔다 → 이름 끝은 `(?![A-Za-z0-9_])`.
- F2 — 사람 토큰 없는 심의의 본문 밖 그림이 똑같은 '올리지 못함' 줄로 늘어서고, 셈에 주소가 없었다 → 한 줄로 장수와 까닭 · `failed_refs` ·
  다른 까닭만 · 못 올린 표지에 설명(RF-9 · RF-10).
- F4 — 객체가 아닌 JSON 오류 본문이 `_ra_error` 에서 새어 포털 500 → 본문 그대로(DocForge 배달도 함께).
- F5 — 꺾쇠 · 제목이 붙은 마크다운 그림이 깨지고, 같은 그림의 표지와 캡션이 어긋나고, 이름만 다른 같은 바이트가 셈을 어긋냈다 → 정규식 · 설명
  하나 · 한 장으로 셈.
- F6 — 매개변수가 붙은 mime(`image/png; charset=binary`)을 415 → 매개변수를 뗀다.
- F7 — 거절될 PATCH 앞에 그림 파일을 올려 고아로 남겼다 → dry_run 으로 먼저 묻는다(RF-6).
- F3 — 포털 잠금 밖의 RA 쓰기가 그림 칸을 지운다 → 포털만으로 못 닫는다(RF-6 고쳐 적음, 게이트웨이 · RA 몫).
- 재현마다 고치기 전에 실패하는 시험을 먼저 두었다(포털 넷 · 에이전트 서버 여섯). 검토자의 재현 시험은 고친 판에서 F1 · F2 · F4 · F5 · F6 이 모두
  실패한다(버그가 없어졌다) — F3 하나만 그대로다.

## RF-18 RA 병합의 곁효과(의심 — RA 담당 확인 필요)

- RA `_merge_ai_page` 는 칸을 하나라도 더하면 그 쪽의 `blocks_order` 를 템플릿 칸 + 추가 칸으로 다시 짓고 `auto_layout` 을 다시 돌린다 — 사람이
  손으로 배치한 쪽은 배치를 잃는다. 이것은 개인 Claude 가 `update_report_draft(extra_blocks=…)` 를 부를 때와 같은 RA 의 규칙이다.
- 그 템플릿은 보고서 머리의 템플릿(`report.template_id`)이라, 쪽마다 템플릿이 다른 보고서의 다른 템플릿 쪽에 칸을 더하면 그 쪽의 템플릿 칸이
  순서에서 빠질 수 있다(검토자가 RA 원본에서 읽음 · 재현 안 함). to-report 는 쪽을 주지 않으면 마지막 쪽에 넣는다 — 사람이 쓴 여러 템플릿 보고서에
  넣을 때 RA 담당에게 확인한다.

## RF-19 표 칸 그림 — 현장 변환기 대신 PC 키트 변환기(긴급 11-02 '표칸그림 필요해')

- 사용자 PC 의 현장 변환기(`md2docx_z.py` — 우리 리포 밖)는 줄 하나에 홀로 선 그림 표기(`^!\[(.*?)\]\((.+?)\)\s*$`)만 그림으로 넣는다. 표 칸 · 문단
  안의 그림은 글자로 남고, 없는 파일은 '[그림 없음]' 으로 넘어가며, 몇 장이 들어갔는지 대조하지 않는다. 우리 보고서는 GFM 표에 그림을 이름으로
  늘어놓는다 — 표 칸 그림이 없으면 그 표가 통째로 글자다.
- 현장 것을 고치지 않고 우리 리포에 새로 둔다 — `infra/pc-kit/hwax-md2docx.py`(PC 에서 혼자 도는 한 파일, Python 3.9+ · python-docx 하나). webp 는
  Pillow, svg 는 cairosvg 가 있어야 png 로 바꿔 넣고, 없으면 그렇게 말하고 실패한다(Windows 의 cairosvg 는 Cairo DLL 이 없으면 import 에서 OSError —
  그것도 '없음' 으로 본다). 형식은 이름이 아니라 바이트로 가린다(게이트웨이 `_fig_sniff` 와 같은 넷 + bmp).
- 그림 자리 셋 — 홀로 선 줄은 본문 폭(A4 · 네 변 2 cm 라 17 cm, `--max-width-cm` 기본 16 이 막는다) 그림과 그 아래 Caption 문단. 문단 · 목록 ·
  제목 · 인용 안은 줄 안 그림(제 크기 — 96 dpi 픽셀, 남은 폭까지). 표 칸 안은 그 열 몫의 폭(칸 여백 0.4 cm 를 뺀다)에 같은 칸 안의 캡션 문단 —
  칸의 앞뒤 글은 제 문단으로 남고 한 칸에 여럿은 차례대로 쌓는다. 모두 비율을 지키고 높이는 쪽 높이의 8할(20.56 cm)에서 막는다(세로로 긴
  그림이 쪽을 넘지 않게). '줄' 기준이다 — 문단 중간 줄에 그림 하나만 있어도 홀로 선 그림으로 끊는다(CommonMark 는 문단 안 그림으로 읽는다).
- 열 몫 — 그림이 든 열은 무게 32(긴 글 열만큼), 글 열은 가장 긴 칸 글의 너비 + 2(한글 한 자 2)를 6 ~ 32 로. '항목 | 그림 | 설명' 꼴에서 그림 열이
  넓고 짧은 이름 열이 좁다. 표는 고정 배치(`tblLayout fixed`)로 열 폭(`gridCol` · `tcW`)을 둘 다 적는다 — Word · LibreOffice 가 그림 때문에 열을
  다시 넓히지 않는다.
- GFM 과 다른 점(빠짐을 막으려고) — 칸이 머리보다 많은 줄의 넘는 칸을 버리지 않고 열을 늘린다(GFM 은 버린다 — 그 칸의 그림이 말없이 사라진다).
  `_` 강조는 읽지 않는다(`fig_…` · 파일 이름의 밑줄). 그림 주소의 역슬래시는 escape 가 아니라 글자다(Windows 경로).

## RF-20 그림 주소와 ref 찾기 — 토큰은 그 사람의 것, 어디에도 찍지 않는다

- 주소 꼴 — md 기준 상대 경로 · POSIX 절대 · `H:/a.png` · `H:\a.png` · UNC(`\\서버\공유\…` · `//서버/공유/…`) · `<빈칸 든 경로>` · 빈칸 든 경로를 그대로
  (따옴표 제목이 없으면 짝 맞는 닫는 괄호까지) · `%20` 꼴 · 제목(`"…"` · `'…'` · `(…)`). 꼴 가르기와 경로 짓기는 순수 함수(`classify_src` ·
  `src_path(windows=…)`)라 리눅스 시험이 Windows 꼴을 본다. 리눅스에서 드라이브 · UNC 경로는 '이 컴퓨터에서 열 수 없다' 로 실패한다.
- ref — `fig_` + 22자(게이트웨이와 같은 꼴), `fig:fig_…` 도. 찾는 차례 (1) md 폴더 → `--fig-dir` 폴더마다 이름에 ref 가 든 파일(`figure_get` 의 curl
  이름 `<도구>-<ref>.<확장자>` — 그림 확장자 먼저 · 이름 차례), (2) 없고 `HWAX_GATEWAY_PAT` · `HWAX_PORTAL_BASE` 가 둘 다 있으면 `{base}/mcp-gw/fig/<ref>`
  를 `Authorization: Bearer` 로 받아 md 옆에 `<ref>.<형식>` 으로 둔다(다음엔 (1) 에서 찾는다 — 못 써도 이번 변환은 된다), (3) 둘 다 아니면 'figure_get 을
  먼저' 를 말한다. 경로로 적었는데 파일이 없고 이름 끝에 ref 가 있으면 ref 로 다시 찾는다(`render_3d-fig_….png` 를 받기 전에 적은 md).
- 받기의 넘김(30x)은 따라가지 않는다 — urllib 은 넘김에도 Authorization 을 실어 다른 호스트로 토큰을 보낸다. 실패 글에는 상태 · 까닭만 싣고 주소 ·
  머리 · 본문은 싣지 않는다(토큰이 어떤 출력에도 없다 — 시험이 가짜 게이트웨이로 성공 · 404 · 302 셋의 출력에서 토큰을 찾는다). 한 장 64 MB 상한.

## RF-21 빠진 그림은 docx 를 쓰지 않는다 · 저장 뒤 수 대조

- 넣기 전에 모든 그림을 먼저 찾는다. 하나라도 없거나 · 못 읽거나(깨짐 · 모르는 꼴 · 의존성 없음) · 표기가 깨졌으면(`![` 뒤에 `](…)` 가 없다) 줄마다
  `줄 N: 주소 - 까닭` 을 모두 알리고 docx 를 쓰지 않는다(종료 2 — 있던 docx 는 그대로다, 그렇다고 말한다). `--allow-missing` 이면 그 자리에 빨간
  `[그림 없음: 주소]`(굵게 · FF0000)를 두고 쓰되 같은 목록을 알리고 끝 줄에 `· 그림 없음 K` 를 붙인다(종료 0 — 사람이 고른 것이다).
- 저장은 `.part` 에 쓰고 바꿔 끼운다(Word 가 열고 있으면 저장 실패를 말하고 종료 1). 저장한 docx 를 zip 으로 다시 열어 `word/document.xml` 의
  `<w:drawing>` 수와 그 가운데 `<w:tc>` 안의 수를 세고 `그림 표기 N · docx 그림 N · 표 칸 안 M` 을 찍는다. md 의 표기 수는 블록 해석과 **따로**
  센다(울타리 코드 · 줄 안 코드 · 역슬래시 escape 밖 — 인용 안의 울타리도) — 렌더러가 어떤 블록에서 그림을 놓치면 이 대조가 잡는다(종료 3 · 놓친 줄).
  표기 = 넣은 것 + 자리표, docx = 넣은 것, docx 표 칸 안 = 표 칸에 넣은 것.
- 종료 코드 — 0 됨 · 1 인자 · 입력 · 환경(argparse 의 2 를 1 로 바꿨다 — 2 는 '그림이 없다' 다) · 2 그림 · 3 수 어긋남.

## RF-22 게이트웨이가 내려준다 — kit_get · GET /kit/<이름>

- `kit_get(name="hwax-md2docx.py")`(읽기) → `{name, bytes, sha256, url, curl, usage}`. url 은 `figure_get` 과 같은 길(`X-Forwarded-Host` · `Proto`)로
  지은 `…/mcp-gw/kit/<이름>?t=…`(1시간), curl 은 `curl -fsS -o hwax-md2docx.py "<url>"`, usage 는 넷(받기 · 그림 · 쓰기 · 돌리기). 박스 안 서비스 ·
  신원 없음 · 공유 비밀 없음이면 url null 과 까닭. 서버 지침에는 넣지 않았다(2,048자 상한까지 16자 — 시험이 지킨다).
- 받기 `GET /kit/<이름>`(게이트웨이 `_bearer_gate` 안 `/fig/` 옆, nginx 고침 없음) — 그 이름의 서명한 표 또는 MCP 청중 PAT 누구나(주인과 무관 —
  파일이 사람 것이 아니다). 패널 PAT · 공유 비밀은 아니다. 표는 `v1.<끝>.<주인 base64url>.<HMAC(v1|kit:이름|주인|끝)>` — 그림 표는 주인을 그림의 곁
  JSON 에서 다시 읽지만 키트 파일에는 주인이 없어 표에 싣는다(감사에 누가 받았나 · 로그는 `t` 값째 가린다). 열쇠는 그림 표와 다른 용도 이름
  (`hwax-mcp-gateway/kit-ticket/v1`)이라 그림 표로 키트를 받지 못한다. 자격 없음 · 검증 못 함은 401, 모르는 이름 · 경로 넘기 · 틀린 · 끝난 · 다른
  이름의 표 · 패널 PAT · 파일 없음(링크 · 폴더 · 2 MiB 넘음)은 같은 404 — 허용 목록 `{"hwax-md2docx.py"}` 의 글자와 같아야 연다.
- 파일 자리는 게이트웨이 파일 자리에서 유도한 형제 리포 `<게이트웨이>/../HWAXPortal/infra/pc-kit`(박스마다 리포 루트가 다르다 — dev `~/claude` ·
  cae00 `~/Projects`), `GATEWAY_KIT_DIR` 이 덮는다. 그래서 변환기를 고치면 포털 리포를 받는 것만으로 다음 받기부터 새 판이다(게이트웨이 재기동 없음).
  반대로 kit_get 은 게이트웨이 새 판이 떠야 생긴다.

## RF-23 검색 어휘 — 'docx' · '변환기' · '표 칸 그림' · 'md2docx'

- 손 동의어 `docx` · `변환기` · `표 칸` → `kit_get`(게이트웨이 search_tuning.json, 74 → 77). `md2docx` 는 `docx` 열쇠를 담아 따라온다.
- '표 칸 그림' 은 한 글자 낱말('표' · '칸')이 질의에서 버려져 '그림' 하나만 남는다 — 그 낱말로는 dev 의 그리는 도구 열한 개(이름에 plot · render ·
  figure)를 kit_get(설명으로만 맞는다)이 넘지 못한다. 게이트웨이가 띄어 쓴 열쇠를 빈칸을 뺀 질의로 맞추게 했다(그 꼴을 낱말 하나로 더하고, 담은
  낱말 '표칸그림' 에도 잇는다). '그림' 에 kit_get 을 잇는 길은 버렸다 — '보고서에 그림' 이 figure_to_report 보다 kit_get 을 앞세운다(시험이 있다).
- 곁효과 — 띄어 쓴 열쇠는 지금까지 말없이 안 먹었다. 박스 덧씌우기에 띄어 쓴 열쇠(request-1029 server-setup 7.3 의 예 '메인 PBA')가 있으면 그 질의의
  순위가 이 판부터 바뀐다(적은 사람의 뜻대로). 그 꼴이 없는 질의의 순위는 바이트까지 같다(기준본 대조 시험 그대로).

## RF-24 반대 검토(11-02, 사본 — 포털 `6dd91bf1` · 게이트웨이 `4c48abf`) — 재현한 것만 고침

- 변환기 확인 열하나(K1 ~ K11) · 게이트웨이 `/kit/` 확인 0건 · 의심 넷(S1 ~ S4). 표 칸 배치 자체(그림이 `w:tc` 안 · 열 몫 − 0.4 cm · 비율 · 같은
  칸의 캡션 · 앞뒤 글 차례 · `tcPr` 다음 `w:p` 로 끝남 · `docPr` id 겹침 없음)는 생성한 docx 53개에서 맞았다. Windows 경로는 말없이 실패하는 꼴이 없었다.
- **말없이 빠짐(종료 0)** — K2(높음) 세기가 표의 다른 줄끼리 ` 를 짝지어 그림을 가리고, 렌더러는 캡션의 `|` 로 칸을 갈라 그림을 잃어 셈이 맞비겼다.
  세기의 줄 안 코드는 줄 · 이스케이프 안 한 `|` 를 넘지 않게 했다 — 세기는 렌더러보다 **덜** 가려야 한다(더 세면 보이는 종료 3, 덜 세면 렌더러가 놓친
  그림과 맞비긴다). 표 줄 가르기는 그림 표기를 통째로 한 칸에 둔다(GFM 은 가른다 — 쓴 사람의 뜻은 그림이다). K1 HTML `<img>` 는 종료 2 로 알린다(넣지
  않는다). K4 python-docx 는 jpeg · gif · bmp 의 머리만 읽어 끊긴 파일을 넣었다 — 끝까지 있는지 본다(jpeg 은 표지를 길이로 건너 SOS 뒤 EOI, EXIF 안
  작은 그림 · 뒤에 붙은 모션 사진 영상에 속지 않는다), 받기는 Content-Length 보다 짧으면 실패하고 md 옆에 두지 않는다. K11 setext 제목을 제목으로 읽는다.
- **거짓 경보** — K3 종료 3(강조가 그림 · 링크 · 줄 안 코드 안의 `*` 로 닫힘 → 건너뛰는 강조 읽기 / 울타리 안 `> ```` 가 울타리를 닫음 → 닫는 줄은
  여는 줄의 인용 깊이만 뗀다). K8 종료 2(`좋다![1]` · `것![^1]` → 그림을 뜻한 꼴만 거절 — 정의된 이름의 참조 꼴 · 대괄호 뒤 `(` · 그림 경로, HTML 주석 →
  코드 밖에서 뺀다 — docx 에 글로 실렸고 주석 안 예시가 '파일이 없다' 로 막았다).
- **꼴 · 견고** — K5 목록 밑에 들여 쓴 표가 목록 글로 이어졌다 → 표로 읽는다. K7 붙은 두 표 사이에 빈 문단(Word 가 한 표로 합친다). K9 XML 에 못
  싣는 제어 문자가 lxml traceback → 빼고 알린다. K6 http.client 오류(끊긴 조각 · 머리 100개 넘음 · 깨진 상태 줄)가 traceback 이었고, 받은 Authorization 을
  되비춘 상태 줄은 토큰을 찍었다 → 그 그림 하나의 실패, 까닭은 꼴 이름과 OS 글만(서버가 보낸 글은 싣지 않는다).
- **RF-19 를 고쳐 적는다** — K10 16 px 아이콘이 칸 폭으로 33배 커졌다. 홀로 선 줄 · 표 칸 그림은 제 크기(96 dpi)의 **두 배까지만** 키운다(보통의
  도구 그림 — 300 px 넘음 — 은 그대로 본문 · 열 폭이다). 줄 안 그림은 종전대로 제 크기까지.
- 의심 — S1 Windows PowerShell 5.1 의 `curl` 은 Invoke-WebRequest 별칭이다 → `kit_get` usage 받기 줄에 `curl.exe` 를 싣는다(`figure_get` 의 curl 한
  줄도 같은 꼴 — 게이트웨이 그림 저장 쪽 몫으로 남긴다). S3 `http://` 주소로 받으면 토큰이 평문이다 → 막지 않고 알린다(dev · 사내 http 박스가 있다).
  S4 띄어 쓴 열쇠가 '목표 칸' 의 '표 칸' 에도 맞았다 → 낱말 머리에서 시작할 때만. S2(Word 가 붙은 표를 합치나)는 K7 로 함께 닫았다.
- 고치지 않은 것 — 들여 쓴(4칸) 코드 블록은 읽지 않는다(쓰는 법 밖 — 그 안의 예시 그림 표기는 종료 2 로 보인다, 울타리 코드를 쓴다). 렌더 확인은
  못 했다(이 박스의 LibreOffice 가 깨졌다 — `libreglo.so` 없음) — XML 로만 봤다.
- 검토 전에 스스로 잡아 같이 고친 것 — 받기의 http.client 오류 · Content-Length 짧음 · 참조 꼴과 HTML `<img>` 의 까닭 글. 확인 — 포털 시험 30(3.9.25 ·
  3.10 · 3.13), 고침마다 변이 하나씩 열여섯이 모두 빨강, 게이트웨이 전체 855.

**RF-25 MX 백서 문서에 그림 — 게이트웨이 `figure_to_doc`(11-02, 게이트웨이 `6e005a87` · MX 백서 `9842648`).** 보관한 그림을 그 사람의 위임 토큰으로만 MX 백서의
`upload_image_bytes`(http 전용 · png/jpeg/gif/webp · SVG 거절 · API 상한 20 MB · 편집자 · 쓰기 범위)로 올리고 `insert_image_block` 으로 넣는다 — 바이트는
게이트웨이와 MX 백서 사이만 지나고 모델을 거치지 않는다. 위임 설정이 없거나(`PER_USER_SSO_APPS mx-white-paper:MXWP`) `token_header` 로 다른 머리에 싣는
설정이면 서비스 계정으로 쓰게 되므로 부르지 않고 거절한다. 편집 충돌은 한 번만 다시, 결과를 모르면 '넣었는지 모른다' 와 image_id 를 준다(중복 블록을
부르지 않게). 같은 날 게이트웨이가 MX 백서의 `인증 실패 (401): …` 꼴도 토큰 거절로 알게 했다 — 철회된 위임을 12시간 계속 쓰던 것, 401 이면 쓰인 것이
없어 새 토큰으로 한 번만 다시 부른다.

**RF-26 남긴 것 — 일회성 세션의 결과 뒤 도구 목록 묻기(후속).** 사람별 위임의 일회성 세션은 MCP 클라이언트가 호출 성공 뒤 출력 스키마를 보려고
`tools/list` 를 한 번 더 부른다. 그 짧은 틈에 401 을 받으면 다시 받기 고리가 쓰기 도구를 한 번 더 돌릴 수 있다(블록이 두 번 들어갈 위험). 토큰이 호출마다
새로 발급돼 드물고, 고치려면 모든 사람별 위임 호출이 지나는 공용 길(`send_request` 로 CallToolRequest 를 보내 클라이언트 쪽 출력 검증을 건너뛰기)을
바꿔야 해서 따로 검토할 후속으로 둔다.

**RF-27 F1 짝 단면 받음 · F2 → F1 넘김 고침 · 검색 낱말(11-03 KST).** StepForge 세션(a72 · D-655)이 F1 을 올렸다 — main `5979a26`(문서 끝 `8a06681`) · Drive(HEAXHub) `dist-20261103-004526Z` · 도구 `section_pair_view` · `section_batch_result`(둘 다 readOnlyHint) · 잡 종류 `section_batch`. 게이트웨이 tools/list 에 맨 이름으로 둘 다 보인다(dev 는 겹침이 없어 접두가 붙지 않는다 — `heaxstep_forge_*` 는 호출 별칭). 게이트웨이 경유 실호출(postdeploy 시험 과제 둘 · 점 [40, 37.5, 4] · y · 창 24 · jpg) 0.37 초 · JPEG 111 KB · '그림 저장 — fig_…' 표지 — figure_get · figure_to_report · figure_to_doc 이 그대로 쓴다.
- F2 → F1 의 틈 — 리스크 앱 답의 `f1` 은 도구 설명 · note 가 'F1 에 그대로 넘길 꼴 · planes 의 항목은 그대로' 라 했지만 F1 의 마지막 인자와 셋이 달랐다. 실호출로 확인 — `f1.point` 사전({x, y, z, unit})은 F1 의 목록 검사에서 거절, `planes` 의 offset 에 window_mm 를 더하면 '창은 자리 둘레' 로 거절, offset 만이면 창 없는 온 평면(자리에서 먼 60 부품). 우리 쪽(F2) 결함이라 리스크 앱에서 고쳤다 — 평면마다 그대로 부를 인자 `f1.calls`(projects = 이 과제의 CAD 하나 · point [x, y, z] 목록 · axis · window_mm · unit · 몸체는 highlight — offset 없음, CAD 과제를 모르면 projects 빈 목록과 note 한 줄) · note · 도구 설명 · `section_planes` 문서(`fc384f4b`(병합 — 코드 `8c4a6d1` · 문서 `742c4d3`)). 기존 칸은 그대로라 화면 세션 영향 없음. 시험 셋은 옛 코드에서 붉다.
- F2 → F1 실호출 — `located` 를 시험 과제의 PLATE_2 세계 bbox(`part_info.world_bbox` — `bbox` 는 제 좌표라 쓰지 않는다)로 짓고 `f1.calls` 두 줄을 견줄 판 하나만 더해 게이트웨이로 보냈다. 두 평면 다 그림 한 장(JPEG 165 KB · 보관) · 평면 = 그 점(법선 Y · X 의 5.0) · 창 30 mm 가운데 [5.0, 1.5] · 강조는 R1 의 경로를 주었는데 두 판에서 맞았다(F1 이 과제 뿌리를 떼고 견준다 — `highlight.unmatched` 빈 목록). 리스크 앱 저장 · 권한 · ODB 길은 그 앱의 시험과 cae00 몫이다(dev 에는 ODB 허브가 없다).
- 검색 — 질의 기록을 끈 카탈로그 평가(`tool_search_eval/run.py eval` — dev 스냅샷)에서 '짝 단면' 8위 · '이전 판과 단면 비교 그림' 10위였다. '짝' 은 한 글자라 질의에서 버려져 '단면' 만 남고 단면 도구 여섯이 같은 점수다(설명에는 '짝 단면' 이 있다). 띄어 쓴 열쇠 '짝 단면' · '단면 비교' → section_pair_view (게이트웨이 `1c933629`)로 1위 · 2위, 추적 147쌍 순위는 바이트까지 그대로. '단면 두 장 나란히 비교'(12위) · '단면 묶음 잡 결과 그림'(20위 밖)은 그대로 뒀다 — 아홉 쌍에 맞춰 손잡이를 고르면 그 아홉에 맞춘 값이 된다(검색 고리는 cae00 에서 닫는다). '단면 비교' 는 owner heax-step_forge · source_fix (설명에 '비교' — 지금은 '견줄 때' 뿐)라 플랫폼 피드백 보고서에 오른다.
- 리스크 앱 전체 시험의 오류 넷은 스크래치 짝 폴더 탓이다 — `test_parity.py` 가 곁의 `../HWAXPortal`(스크래치의 옛 `portal-clone` 링크)을 찾고 그 곁의 에이전트 서버가 없어 실패한다. `HWAX_PORTAL_REPO` 를 진짜 포털로 주면 넷 다 통과.

**RF-28 F3 짝 단면 묶음 받음(11-03 KST).** StepForge 세션(a73 · D-656)이 `section_batch(rows)` 를 올렸다 — main `ed0ca60` · 문서 끝 `20b72a7` · Drive(HEAXHub) `dist-20261103-025507Z`(F1 의 `004526Z` 를 덮는다) · readOnlyHint. 줄은 `section_pair_view` 의 인자 그대로라 리스크 앱 `f1.calls` 줄에 견줄 판 id 를 더한 꼴이 그대로 들어간다.
- dev 게이트웨이 경유 — RF-27 의 PLATE_2 calls 두 줄 → 내기 0.03 초 · 같은 줄 다시 → 같은 잡(`reused: true`) · 잡 4.1 초 done · `section_batch_result` 두 줄 다 그림 한 장(JPEG 163 · 164 KB) · 게이트웨이 그림 보관 표지 · 평면 = 그 점(법선 Y · X 의 5.0) · 창 30 · 강조 두 판에서 맞음.
- 틈 하나 — 내기 답의 `status` 가 `job_status(job_id=…)` 를 부르라고 하지만 게이트웨이에는 맨 `job_status` 가 없다(StepForge 와 SmartTwinMCP 가 겹쳐 둘 다 접두 — `heaxstep_forge_job_status`, cae00 도 같은 겹침이다). 맨 이름을 부르면 'unknown tool: job_status' 다. `section_batch_result` 가 끝나기 전에는 `ready: false` 와 진행을 주므로 길은 막히지 않는다 — StepForge 세션에 안내 글을 `section_batch_result` 로 바꾸기를 청했다. 겹친 이름 전반(job_status · list_jobs · cancel_job 등)을 게이트웨이가 '이 이름은 여럿이다 — 후보' 로 답하게 하는 것은 따로 할 일로 남긴다(지금은 'unknown tool').
- 검색 — 새 스냅샷(설명에 '비교')에서 F1 질의 아홉 가운데 여덟이 1위('단면 두 장 나란히 비교' 12위 → 1위). '단면 비교' 열쇠를 빼고 재면 '이전 판과 단면 비교 그림' 이 1위 → 3위라 열쇠는 남긴다 — 그쪽이 '비교' 를 넣었으니 다음 게이트웨이 판에서 그 열쇠의 owner · source_fix 를 비운다(지금 플랫폼 피드백 보고서에는 StepForge 의 할 일로 남아 있다). F3 질의 다섯 — '단면 여러 장 한꺼번에' · 'section batch' 1위, '여러 자리 짝 단면 묶어서' 2위, '단면 그림 여러 개 일괄' 3위, '단면 묶음 잡' 20위 밖(설명에 '묶음' 이 없다 — 그쪽에 청했다, 두 글자라 우리 열쇠로 메우지 않는다). 추적 147쌍 그대로.

**RF-29 사용자 결정 11-03 — F6 적층 비교 그림의 잡 시작은 F1 꼴(읽기 토큰도).** StepForge 세션이 물었다 — `compare_stackup` 을 그림 잡으로 할 때 측정 잡(`run_job(kind="measure")`)을 누가 띄우나. 지금은 `job_call` 을 돌려주고 쓰기 PAT 가 띄운다. 이 세션에서 선택지로 물었고 사용자가 권장안을 골랐다 — 두 과제가 파싱돼 있고 바로 길이 예산에서 멈추면 `compare_stackup` · `stackup_figure`(`project_id` + `other_project_id` 길)가 그 측정 잡을 스스로 넣고 `job` 을 준다(StepForge 읽기 울타리의 좁은 예외 `jobs:insert` 가 도구 둘 → 적층 짝까지). `job_call` 은 옛 호출자를 위해 그대로, 파싱 안 된 과제는 `job_call` 만(파싱은 쓰기). 까닭 — 루틴 · 심의 좌석 · 읽기 토큰은 `job_call` 에서 멈춰 적층 그림을 보고서에 싣지 못한다(F1 짝 단면과 같은 꼴로 맞춘다). 버린 것 — 그대로 두고 `stackup_figure(job_id)` 만(울타리는 그대로지만 쓰기 PAT 를 가진 개인 Claude 만 그림까지 간다). StepForge 는 a74 를 안전한 기본(스스로 넣지 않음)으로 먼저 올리고 이 결정을 작은 후속으로 붙인다 — 오면 dev 에서 읽기 토큰으로 적층 그림 잡 → 게이트웨이 그림 보관까지 본다.

**RF-30 F6 받음 · 적층 측정 잡 스스로(11-03 KST).** StepForge 세션(a74 · a75 — D-657 · D-658)이 올렸다 — main `5366950` · `dc7b447` · 문서 끝 `cce849c` · Drive(HEAXHub) `dist-20261103-073959Z`(F1 · F3 의 판을 덮는다).
- 게이트웨이 tools/list — `stackup_figure` 맨 이름 · readOnlyHint, `section_pair_view` 에 `fold`, `section_batch` 설명 머리 '짝 단면 묶음', `compare_stackup` readOnlyHint.
- `fold` — 시험 판 둘(쌓은 판 셋)에서 PLATE_3 을 (10, 0, 2) 지나는 +y 축으로 90° → 0.44 초 · 판마다 1 파트(`fold.moved` R1 · R2 1) · 그림 보관 129 KB. 아무 파트도 안 가리키는 글롭은 거절('돌리지 않은 채 닫힌 상태라 하지 않는다'). `section_batch` 의 새 안내 — `status` 는 `section_batch_result(...)`, `job_status` 는 `heaxstep_forge_job_status(...)`(RF-28 의 틈이 닫혔다).
- `stackup_figure` 바로 길 — 0.42 초 · 그림 보관 94 KB(예산 안이라 잡 없음).
- 측정 잡 스스로(사용자 결정 RF-29) — dev 에서 가장 큰 보드(211 파트)와 45 · 37 파트 보드의 짝이 예산에서 멈춰 `compare_stackup` 이 측정 잡을 넣고 `job` 을 줬다(`job_call` 그대로). 같은 짝으로 `stackup_figure` 바로 길을 부르면 같은 잡(`reused: true`)이다. 게이트웨이 `/tools-map` 의 `routine_read` 에 compare_stackup · stackup_figure · section_pair_view · section_batch · section_batch_result 가 다 든다 — 읽기 전용 PAT · 루틴 · 심의 좌석이 부를 수 있다. 측정 잡은 한 번에 하나씩 돈다(첫 잡 running · 뒤 잡 pending — runner 하나), 211 파트 짝은 dev 에서 오래 걸린다. 그 잡의 그림(`stackup_figure(job_id)`)은 dev 에서 아직 못 봤다 — 첫 잡이 33분째 진행 10% 에 머물렀다(바로 길이 낸 까닭은 '재지 않았다 — 211 파트 묶음의 작업량 어림 61초 이상(하한)이 한 호출 상한 60초를 넘는다' 라 `comparable: false` 는 잠정이다). StepForge 세션에 알렸고, run_job 으로 넣은 측정 잡 → `stackup_figure(job_id)` 그림은 그쪽이 작은 보드로 확인했다. 실제 보드 짝으로 끝까지 보는 것은 그쪽 답 뒤다.
- 자격 — 게이트웨이를 거친 부름이 StepForge 에 싣는 것은 게이트웨이의 앱 토큰이다. StepForge 의 읽기 예외(`jobs:insert`)는 읽기 범위 토큰이 StepForge 를 바로 부를 때(리스크 앱의 portal PAT 등) 걸리고, 게이트웨이 쪽 읽기 전용 PAT 는 게이트웨이의 읽기 분류로 거른다(이 넷은 읽기).
- 검색 — 질의 기록을 끈 카탈로그 평가에서 '접힌 상태 단면' · '적층 비교 그림' · 'stackup figure' 1위, '적층 두께 비교 그림으로' 2위, '두 보드 적층 그림' 3위, '폴더블 닫힌 상태로 단면' 12위 · '힌지 접어서 단면 보기' 8위 — 설명에 '폴더블' · '힌지' · '닫힌' 이 없다(그쪽에 청함 — 두 글자 이상이라 우리 열쇠로 메우지 않는다). RF-28 의 '단면 묶음 잡' 은 그쪽 낱말로 다섯 안에 들었다. 추적 147쌍 그대로.
- (11-03 덧붙임) StepForge 세션 답 — 잡은 멈춘 게 아니라 계산 중이었다(워커 R 상태 · CPU 35분 · RSS 1.28 GB · 한 스레드). RC p9(211 파트)는 쌓임이 아니라 `nonadjacent_in_budget` 의 끝없는 `stackup_profile` 이 모든 겹친 쌍을 잰다 — 바로 길의 61.1초는 하한이었다. 진행 칸(D-650 의 시간 진행)은 보드 전체 퓨즈 안에서만 돌아 이 단계에서는 끝까지 10 이다(그쪽 틈). 러너가 하나라 뒤 잡이 다 줄을 선다 — dev 공용 러너라 시험 잡 둘을 멈췄다(첫 잡 2,162.6초 · 10% 에서 SIGTERM · 둘째는 집히기 전에). 그쪽 고침 — 쌓임 잴 때의 진행 칸, 쌓임이 아닌 쪽이 있으면 스스로 넣지 않고 `job_not_queued` 로 까닭(청함). 오면 쌓인 보드 짝으로 잡 → 그림 보관을 다시 본다.

**RF-31 cae00 실제 데이터 점검 — 한 명령으로 끝까지, 그림은 사람이 본다(11-03, 사용자 요청).** 걸음마다 dev 에서 확인했지만 실제 리스크 항목 → 위치 → 그림 → 보고서를 한 번에 돈 적이 없다 — ODB 허브 · RA · 실제 개정 CAD 가 cae00 에만 있어서다. `infra/scripts/cad-figure-check.py`(`bf528ef4`)가 그 차례를 그 사람의 PAT 로 부른다 — `risk_locate_for_section` → 평면마다 `f1.calls` 줄에 견줄 판을 더한 `section_pair_view`(`--fold` 면 접힌 상태) → `section_batch` · `section_batch_result` → (고르면) `stackup_figure` 바로 길 · 스스로 넣은 잡 → `figure_get` 주소로 받아 크기 · sha256 대조 → (`--ra-report` · `--mxwp-doc` 를 줄 때만) `figure_to_report` · `figure_to_doc`.
- 읽기 목록 밖은 부르기 전에 거절하고 쓰기 둘은 그 인자를 줄 때만 열린다. 변환 등록(`risk_set_board_transform`)은 스크립트가 하지 않는다 — 위치를 못 정하면 까닭 · 고칠 곳을 찍고 멈춘다(사람이 제안을 보고 정한다).
- 그림 받기는 개인 Claude 가 PC 로 받는 길과 같게 `figure_get` 의 주소로 받는다 — 게이트웨이는 박스 안 서비스(게이트웨이 토큰)가 부른 것에는 주소를 주지 않고(`url: null` · 까닭 note), 사람 PAT 로 바로 붙은 부름에는 그 Host 로 서명 주소를 준다(`_fig_public_base`). 그래서 이 점검은 PAT 로만 돈다.
- 요약은 상태 · 수 · 초만 — 과제 · 파트 이름 · id 는 `report.json` 과 받은 그림 폴더(`infra/.state/cad-figure-check/`)에만. 그림이 맞는지(자리 · 강조 · 간극 치수 · 접힌 자리)는 사람이 열어 본다 — 받은 편지함 Q4.
- 기다림 — 묶음 결과는 5초, 적층 측정 잡은 15초마다 다시 묻고 잡 하나에 기본 900초까지. 적층 잡은 StepForge a76(쌓임 축을 모르면 스스로 넣지 않고 `job_not_queued`) 뒤에 축을 주어 부른다.

**RF-32 StepForge a76 받음 · 저절로 넣은 잡의 그림까지(11-03 KST).** a76(D-659) — main `164c99c` · 문서 끝 `01bb4a0` · Drive(HEAXHub) `dist-20261103-104015Z`(F1 · F3 · F6 판을 덮는다). 36분 잡의 까닭은 쌓임이 아닌 보드의 쌓임 축 어림(표본의 87%)이었다 — 쌓임 축을 정하기 전에 멈추면 이제 잡을 넣지 않고 `job_not_queued` 로 까닭 · 할 일(축 주기 · 파트 좁히기 · 쓰기 토큰의 `job_call`)을 준다. 측정 잡 진행은 계산 내내 10 ~ 90 으로 움직인다.
- dev 게이트웨이 — 축 없이 211 파트 짝(RC p9 · 쉴드 캔) 5.0초 · 잡 없음 · `job_not_queued`. 축 z 로 `stackup_figure` 바로 길 1.8초 — '층마다 단면' 어림 60.2초 이상이 한 호출 상한 60초를 넘어 잡이 저절로(axis_from_stop null — 축을 우리가 주었다) → 진행 26 · 54 · 100(2분) → `stackup_figure(job_id)` 그림 한 장 · 게이트웨이 그림 보관. 사용자 결정 RF-29 의 길(큰 보드도 그림까지)이 끝까지 섰다.
- 그림 크기 — 211 줄을 한 장에 그려 1500 × 5743 · 583 KB(jpg 품질 35)로 256 KB 상한을 넘었고 `figure.over_cap: true` 로 스스로 말한다. 보관 · 받기 · 보고서 넣기에는 문제가 없지만(바이트는 모델을 거치지 않는다) 챗에 실리면 무겁다 — 줄이 많으면 나눠 그리기를 그쪽에 청했다.
- 검색 — 그쪽이 짝 단면 설명에 '폴더블' · '힌지' · '닫힌 상태' 를 넣어 '폴더블 닫힌 상태로 단면' 12위 → 2위 · '힌지 접어서 단면 보기' 8위 → 1위, F6 질의 일곱이 다 다섯 안. 추적 147쌍 그대로.

**RF-33 적층 그림 쪽 나눔(StepForge a77 · 11-03 KST).** RF-32 의 청(211 줄 한 장 583 KB · over_cap)을 그쪽이 쪽으로 받았다 — main `143dd42` · `969e7fb` · 문서 끝 `9c8946e` · Drive(HEAXHub) `dist-20261103-130959Z`(a76 까지의 판을 덮는다). `stackup_figure` 의 `page`(1부터) — 쪽마다 60 줄 · 줄 번호와 색은 전체 결과 그대로 · 답의 `page{page, pages, rows, next}` — `next` 는 다음 쪽을 부르는 글(사전이 아니다)이고 끝 쪽은 null, 60 줄 이하면 `page` 칸이 없다. 그쪽이 실주행에서 찾아 고친 것 — 짧은 꼴의 `totals.layers.only_a` · `only_b` 가 한쪽 층 이름 160여 개(5,496자)로 챗 컷 5,000자를 혼자 채워 쪽마다 1 줄만 남던 것을 수로 바꿨다(이름은 `full=true` · `files.json`).
- dev 게이트웨이 — 211 줄 결과(job `…6749bc80`)를 쪽 1 ~ 4 로(1–60 · 61–120 · 121–180 · 181–211) · 쪽마다 0.5 ~ 1.0초 · 1500 × 1076 ~ 1955 · 244,911 ~ 261,927 바이트(모두 256 KB 안 · over_cap 없음) · 쪽마다 게이트웨이 그림 보관 표지 · 끝 쪽 next null. 챗에 보이는 줄(rows_shown)은 dev 챗 컷에서 16 ~ 19 — 그림에는 그 쪽 줄이 다 있다.
- 포털 점검 스크립트(`cad-figure-check.py`)가 답에 `page` 가 있으면 같은 인자에 page 만 바꿔 끝 쪽까지 부르고 쪽마다 그림을 받는다(`next` 글을 읽지 않고 수로 — 바로 길은 그 인자 · 잡 길은 job_id). 한쪽 층 칸을 읽지 않아 그쪽의 꼴 바뀜(목록 → 수)에 걸리지 않는다.

**RF-34 단면 지도 · 타겟 파트 강조 색(StepForge a79 · 11-04 KST, 그쪽 사용자 제안 · D-663).** main `064ec41`(SP 서브모듈 `d3b5aa1` — 키트 판 그대로) · `e4d7bd8` ·
`d0126cd`, Drive `dist-20261104-135504Z`(a78 까지 품는다), dev 라이브 도구 184. 파싱 뒤 작업량 어림 위쪽이 900초 안이면 읽기 전용 그림 잡 `section_atlas` 를 스스로 건다 —
축마다 판 외곽을 고르게 나눈 12칸 가운데와 그 간격에 안 걸린 얇은 파트 가운데를 잘라 장마다 png · 정의 JSON(걸린 파트 · 간극 행 · 한 줄 요약) · 곡선을 남긴다. 새 읽기 도구
`section_atlas` 는 인자 없으면 상태 · 장 목록, `axis` + `position` 은 가장 가까운 장, `part` 는 그 파트를 지나는 장을 그 파트만 자홍 · 이웃 회색으로 다시 그린다(한 호출에 한 장).
`section_view` 에 `highlight`(`through` 와 함께만, 기본 꺼짐). dev 게이트웨이에서 `section_atlas` 는 읽기(루틴 · 좌석 읽기로 열림)다. RC 버기(211 파트) 실측 65장 · 249.8초 ·
17.2 MB · 장마다 치수 8초 상한(27장이 상한에서 멈춰 `skipped_work`) · 한 장 60 파트 상한 · 월드 축만. 포털 점검 스크립트(`cad-figure-check.py`)는 아직 지도를 부르지 않는다 —
짝 단면 · 묶음 · 접힘 · 적층으로 충분해 걸음을 더하지 않았다(필요해지면 '지도 상태 → 그 부품을 지나는 장' 한 걸음). cae00 확인은 받은 편지함 2026-11-04 Q4.

**RF-35 단면 그림을 CAD 단면도 꼴로 · svg_live 예고(StepForge a80 · 11-05 KST, 그쪽 사용자 11-04 · D-664).** main `562e8de`(SP 서브모듈을 `ab41cff` 로 — SP main 이
되돌려졌다, `docs/sp-latest` SL-7) · `8e711c4` · `7c71d7a`, Drive `dist-20261105-015533Z`, 라이브 도구 184. 그림만 바뀐다 — 흰 바탕에 그 평면의 재료 면(OCC 교집합 면)을
파트 색조로 채우고 해칭, 구멍 · 빈 곳은 흰색, 강조 그림은 타겟만 자홍 · 이웃 회색. 3D 뷰 · 적층 그림 · 치수 차트는 어두운 톤 그대로. 짝 단면은 해칭 한 겹으로 256 KB 안(실측
135 KB). 옛 단면 지도는 status stale(「그림 꼴이 바뀌었다」) · rebuild 호출문. 단면 한 장 시간이 는다(RC 55파트 3.2 → 8.6초 · 지도 65장 249.8 → 399.2초). 포털 점검
스크립트(`cad-figure-check.py`)는 바꿀 것이 없다(jpg 를 청하고 응답 꼴이 그대로다). a81 예고 — 상호작용 SVG `format="svg_live"`(파트마다 `<g class="part" data-path …>` ·
마우스를 올린 파트 위에 이름 · 경로 풍선(CSS `:has()` — Chromium 105+), 스크립트 없음, MCP ImageContent `image/svg+xml`). 포털의 답(11-05) — 지금 화면은 그림을
`<img>` 로 그려 호버가 안 된다(게이트웨이 → 에이전트 서버 `/agent/artifacts/<sha>.svg` → 포털 중계(CSP sandbox) → 마크다운 `<img>`). 1단계는 `*.svg` 를
`<iframe sandbox="">` 로(페이지 CSP `frame-src 'self'` 가 허용), 2단계(data-path 로 사이드바)는 소독한 인라인 삽입(DOMPurify) — 화면 규칙과 부딪혀 따로. **화면을
고칠지는 사용자 결정**. `format="svg"` 를 청하는 곳은 포털 · 에이전트 서버 · 게이트웨이 · 리스크 앱에 없다. 보고서(RA) · MX 백서는 SVG 를 받지 않는다(415) — 보고서
그림은 png · jpg 그대로.


**RF-36 사용자 결정(11-05) — 같은 출처 SVG 그림은 격리 iframe 으로 그린다(호버가 산다).** StepForge a81(D-665 — main `e13bd08` · `d776e71`, Drive
`dist-20261105-045500Z`)의 `format="svg_live"` 는 파트 위 이름 · 경로 풍선과 간극 치수를 CSS(`:has()`)만으로 띄운다. 챗은 그림을 `<img>` 로 그려 호버가 죽었다.
이제 `/agent/artifacts/*.svg` 처럼 같은 출처의 `.svg` 는 `<iframe sandbox="">`(스크립트 · 같은 출처 모두 막음 — 따로 출처) 로 그린다. 페이지 CSP 가 `frame-src 'self'`
라 허용되고, 포털 중계는 이미 CSP sandbox · nosniff · inline 이다. SVG 문서는 자기 width · height 로 그려져 칸에 맞춰 줄지 않는다 — 원래 크기(같은 주소를 그림으로 한 번
읽어 안다)의 iframe 을 CSS 변형으로 줄인다(호버 판정은 변형을 따른다). 칼럼보다 1.5배 넘게 넓으면 줄이지 않고 가로 스크롤(그림과 같은 규칙). iframe 안의 누름은
바깥으로 오지 않아 확대는 모서리 아이콘으로 연다. 확대 화면도 같은 iframe(맞춤은 배율로). 바깥 출처 SVG 는 그대로 `<img>`. 인라인 삽입(사이드바 연동)은 하지
않는다. 덧막이 — 에이전트 서버의 도구 그림 저장(`_stash_image_items`)이 내용으로 꼴을 보고(래스터는 `vision.sniff`, SVG 는 `<svg` 머리) 8 MiB(`VISION_MAX_BYTES`)를
넘거나 꼴이 아니면 저장하지 않는다(전에는 선언된 `image/*` 면 무엇이든 저장했다).

**RF-37 StepForge a81 받음 — 상호작용 SVG · 지도 HTML 뷰어(11-05 KST, 그쪽 D-665).** main `e13bd08` · `d776e71`, Drive `dist-20261105-045500Z`, 라이브 도구 184(수 그대로).
`format="svg_live"` 를 section_view(한 장 · 연속 · 강조 · 치수) · section_atlas(남긴 곡선에서 바로) · section_pair_view · section_batch(칸마다 data-project, 폭 · 바이트
맞춤 없이)가 받고, 응답은 글 블록 하나 + ImageContent(image/svg+xml). 풍선은 맨 위층에 미리 그려 두고 CSS `:has()` 로 띄운다(Chromium 105+ · Firefox 121+ · Safari
15.4+), 접근성 이름은 묶음의 aria-label, 규칙은 `svg.stepforge-section` 아래. section_atlas 에 `format`(png | svg_live) · `viewer`(true 면 지도 HTML 을 짓고 viewer.route ·
public_url) — 앱 주소 `GET /view/{project_id}/atlas`(text/html · 뷰어 스크립트 sha256 하나만 허용하는 CSP, 지도나 뷰어가 없으면 404 → `section_atlas(viewer=true)`).
REST `GET /api/projects/{id}/section-atlas` 에 format · viewer, svg_live 는 image_base64. 기본은 png 그대로 — 보고서 · 판독은 지금처럼. 포털 챗은 RF-36 으로 그 SVG 를
격리 iframe 으로 그린다(호버가 산다). cae00 확인(그쪽 청) — 받은 편지함 2026-11-05 Q4 · Q5.

**RF-38 StepForge 단면 계산을 여러 코어로(11-06 KST, 그쪽 D-667 — main `6f246e8` · `3f2780f`, Drive `dist-20261105-162025Z`, 라이브 9514).** 도구 계약 그대로 — 부르는 쪽(포털
점검 스크립트 · 챗 · 패널)이 바꿀 것은 없다. section_batch 잡은 줄마다 fork 워커(검출 잡과 같은 워커 예산 · 줄 차례 · 바이트 상한 · 줄의 실패 규칙 그대로, 결과는 직렬과
그림 바이트까지 같다), 단면 지도 잡은 장마다(운영 RC 211파트 65장 399.2 → 56.1초 — RF-35 의 a80 에서 늘었던 시간이 줄었다), section_view · section_pair_view 한 장은
파트마다 교선 · 채움을 워커에서(치수 끔 3.8 ~ 4.5배 · 켬 1.0 ~ 1.4배 — 치수는 아직 한 코어). 이 판이 패널 둘(CE-7)을 품는다.

**RF-39 사용자 결정 11-08 KST — RF-29 를 유지한다: StepForge 가 단면 · 적층 잡 도구 넷의 readOnlyHint 를 떼어도 포털은 읽기로 다룬다.** StepForge 운영 감사(그쪽 D-677 S7, 11-07 — main `e96e68d`)가 `section_pair_view` · `section_batch` · `compare_stackup` · `stackup_figure` 의 readOnlyHint 를 뗐다(장부는 안 바꾸지만 잡과 파일을 남긴다 · `allow_job` 기본 true). 게이트웨이는 읽기 전용 PAT 을 '읽기 목록에 있거나 앱 표지가 읽기' 로만 열고, 루틴 울타리는 앱 표지가 '읽기 아님' 이면 목록보다 먼저 닫는다 — 그래서 넷이 읽기 토큰 · 루틴에서 거절됐다. RF-29(측정 잡은 읽기 토큰 · 루틴으로도 스스로)와 RF-30 · RF-32 의 전제를 뒤집은 것이라 선택지로 물었고 사용자가 권장안을 골랐다 — StepForge 표지는 그대로 두고 게이트웨이 `read_tools.json` 에 **override** 칸(앱이 readOnlyHint=False 를 적었어도 포털이 읽기로 다루는 도구 — 사용자 결정으로만)을 두어 넷을 적는다. 읽기 전용 PAT 판정 · 루틴 단계 · 패널 읽기 · 쓰기 분류(tools-map `write` · 검색 감점 · 운영자 알림)가 앱 표지보다 먼저 보고, destructiveHint 와 닫기 목록(deny)은 그대로 이긴다. 클라이언트가 보는 tools/list 표지는 앱이 적은 그대로다(개인 Claude 가 읽기 도구로 오해해 묻지 않고 부르지 않게). 기존 읽기 목록(`tools`)의 뜻은 바꾸지 않았다 — 선언 백엔드의 박스 목록이 앱의 False 를 못 이기는 원칙(ext-connect GW9)도 그대로다. 버린 것 — '잡 없을 때만 읽기'(allow_job=false 일 때만, RF-29 의 '멈추지 않는다' 를 뒤집는다) · '새 분류 그대로'(읽기 토큰 · 루틴이 넷을 아예 못 부른다). 게이트웨이 `290f324`(병합 `2d0ec28`) · 참조 고침 `c47e883` — 앞 둘의 메시지는 번호를 RF-33 으로, 날짜를 dev 박스 UTC 로(11-07) 잘못 적었다(강제 푸시 없이 그대로 둔다). 시험 하나 더 · 사본의 변이 셋이 모두 붉었다 · 전체 940 통과. dev 재기동 뒤 `/tools-map` 에서 넷이 `routine_read` · `panel_read` 에 있고 `write` 에 없다. 영향 조사(읽기 전용 에이전트)에서 바뀌지 않는 것 — 챗 확인 관문(HA-29 — 운영자 목록과 잡 목록만 본다) · 심의 좌석 조회(이름 머리 목록) · 지정 도구 · 리스크 앱(넷을 부르지 않고 `f1.calls` 인자만 짓는다). 남은 틈(옛것) — 리스크 패널 좌석이 `compare_stackup` 으로 측정 잡을 걸 수 있다(`compare_` 머리 · `allow_job` 기본 true — StepForge `QUEUES_JOB` 와 어긋남, 바꾸지 않았다). 같은 날의 다른 변화 — 짝 단면 그림 상한 256KB → 8MiB(StepForge D-675)는 게이트웨이 그림 보관 · 에이전트 판독 8 MiB · RA 25MB 와 맞아 고칠 것이 없다(사람당 보관 1 GiB 라 큰 그림이 쌓이면 오래된 것부터 지워진다).

**RF-40 사용자 결정 11-13 KST — 챗의 단면은 기본으로 호버되는 SVG 로 보이게 한다. StepForge 가 PNG 와 SVG 를 짝으로 돌려주고, 화면은 SVG · 모델 판독 · 보고서는 PNG.**
사용자가 "기본이 svg 면 안 되겠니" 라고 물었다. 지금은 StepForge 단면 도구 넷(section_view · section_pair_view · section_batch · section_atlas)의 `format` 기본값이
`png` 이고, `svg_live` 는 모델이 골라야만 온다 — StepForge 운영자 안내문에 svg_live 이야기가 없어 챗에서는 거의 오지 않았다. 챗 화면은 SVG 를 받을 준비가 돼 있다
(에이전트 서버가 내용으로 `.svg` 를 저장하고 화면이 격리 iframe 으로 그려 호버가 산다 — RF-36). StepForge 기본값만 SVG 로 바꾸면 셋이 깨진다 — 챗 모델은 SVG 를
못 읽고(그림 판독은 래스터만 — 에이전트 `vision.IMG_URL_RE` 가 png · jpg · gif · webp 만 집는다), 심의 · 리스크 좌석의 판독과 리스크 앱 `f1.calls`, RA 그림 블록 ·
워드 변환은 래스터를 전제로 한다. 선택지 셋(PNG + SVG 함께 · 챗에서만 SVG 기본 · 그대로) 가운데 사용자가 권장안 **PNG + SVG 함께** 를 골랐다.
- StepForge — 네 도구에 `format="png+svg_live"` 를 더한다. 한 번 그려 글 블록 + ImageContent(PNG) + ImageContent(SVG)를 짝으로 낸다(여러 장이면 짝마다 차례대로 ·
  짝을 알아볼 표지). 기본값은 `png` 그대로 — 다른 호출자(심의 · 리스크 · 절차 · 보고서)는 바뀌지 않는다.
- 에이전트 서버 — 챗 길에서만 인자 기본값(`_CHAT_ARG_DEFAULTS`)으로 `format="png+svg_live"` 를 채운다(모델이 정했으면 그대로). 짝은 같은 줄기 이름으로 저장하고
  모델에게는 SVG 주소를 답에 넣으라고, PNG 는 판독용(답에 넣지 않는다)이라고 적는다 — 판독은 PNG 를 저절로 집는다. `/보고서` 는 SVG 주소를 짝 PNG 로 바꿔 싣는다.
- 포털 화면 — 같은 출처 `.svg` 는 이미 호버 iframe 이다(바꿀 것 없음 — SVG 를 못 읽으면 짝 PNG 로 물러서기는 선택).
- 순서 — StepForge 가 새 값을 지원하기 전에 챗 기본값을 켜면 옛 판이 모르는 값을 받아 실패한다. 그래서 StepForge 착지(일곱째 묶음 뒤 — 판 고정 해제 뒤) → 에이전트
  서버 기본값 · 짝 처리 → dev 실호출 확인 차례다. 게이트웨이 그림 보관(`figure_to_report`)이 짝을 받으면 PNG 를 고르는지도 그때 본다.

