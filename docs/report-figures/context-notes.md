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
