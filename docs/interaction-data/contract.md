# 상호작용 데이터 — 리포 사이 계약(M0 · M1 ~ M3)

> 계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md)(IX-1 ~ IX-10). 이 문서가 정본이다 — 포털 · 게이트웨이 작업자가 같이 읽는다. 바꿔야 하면 바꾸지 말고
> '계약 변경 제안' 으로 알린다.

## 1. 스위치(모두 기본 꺼짐 — 끄면 지금과 바이트까지 같다)

| 자리 | 키 | 하는 일 |
|---|---|---|
| 포털 `infra/.env` | `INTERACTIONS_ENABLED=1` | 수집기(가져오기 · 옮기기) · 공유 창구 · 내 기록 · 분석가 화면. 꺼지면 창구 404 · 수집기 안 돎 |
| 게이트웨이(환경 또는 곁 `provision.env` — TS-9 와 같은 읽기) | `GATEWAY_INTERACTION_CAPTURE=1` | 도구 호출 원문을 수집 창고(spool)에 덧붙임 · 내부 가져가기 창구 · `share_conversation` 도구 |

update-all 끝 요약 「있는데 안 켠 것」 에 둘이 ○ 로 뜬다(켜는 법 붙여).

## 2. 저장소 — 포털 `interactions.sqlite`(IX-10 — IX-7 의 PostgreSQL 을 뒤집음)

- 자리는 데이터 레지스트리로(대화 저장소 `conversations.sqlite` 와 같은 꼴), WAL. 백업은 `backup-local.sh` 의 portal 대상에 더한다. Drive · 조각 동기화에 싣지 않는다.
- 표
  - `events` — 한 줄 = 한 사건. 칸 `id`(ULID) · `ts`(초) · `surface`(`web_chat` · `web_delib` · `think` · `routine` · `procedure` · `mcp_call` · `tool_search` ·
    `shared_claude` — M4 에 `delib_job` · `risk`) · `actor`(이메일, 소문자) · `affiliation` · `client`(브라우저 · Claude Code · Claude Desktop · 앱 이름 · 판) · `conv_id` ·
    `turn_id` · `corr`(게이트웨이 연결 ID) · `rid` · `via`(`pat` · `panel` · `procedure` · `routine` · `agent` · `service`) · `app`(백엔드 키) · `tool` · `model` ·
    `status`(`ok` · `error`) · `ms` · `tokens_in` · `tokens_out` · `input`(글) · `output`(글 — 한 줄 상한 1 MB, 넘으면 앞부분) · `output_chars`(원문 크기) ·
    `output_sha256` · `meta`(JSON) · `source`(옮겨 온 저장소 이름) · `source_ref`(그 저장소의 id — `UNIQUE(source, source_ref)` 로 한 번만).
  - `shared_sessions` — 공유한 Claude 대화. `id` · `owner` · `session_id`(같은 세션은 덮어씀 — `UNIQUE(owner, session_id)`) · `title` · `client` · `created` ·
    `updated` · `messages`(JSON 압축 — zlib) · `chars` · `kind`(`tool` — 도구로 받은 것 · `transcript` — 기록 파일 원문).
  - `ingest_cursors` — 가져오기 자리(`source` → `cursor`).
  - `view_audit` — 원문 열람 감사(`ts` · `viewer` · `owner` · `event_id` 또는 `shared_id` · `action`).
- 지우기 — 본인 청구는 그 사람의 `events` · `shared_sessions` 를 지운다(M5 가공층 · 임베딩도 같은 id 로 — M5 몫).

## 3. 게이트웨이 수집 창고(spool)와 가져가기

- **덧붙이는 자리** — SDK 바깥 처리기(`_call_tool_entry`)에서 호출이 끝난 뒤 한 줄(JSONL). 칸 `ts` · `corr` · `rid` · `actor` · `via` · `client`(initialize 의
  clientInfo name · version) · `tool`(노출 이름) · `backend` · `orig`(원래 이름) · `args`(가림 뒤) · `result`(content 글을 이은 것 + structuredContent JSON — 가림 뒤,
  1 MB 상한) · `result_chars` · `result_sha256` · `is_error` · `ms`. 실패한 덧붙이기는 호출을 막지 않는다(로그 · 셈만).
- 자리 `GATEWAY_INTERACTION_SPOOL_DIR`(기본 게이트웨이 곁 `interaction_spool/` — gitignore) · 조각 64 MB 회전 · 전체 상한 `GATEWAY_INTERACTION_SPOOL_MAX_MB`(기본 2048 —
  넘으면 오래된 조각부터 버리고 `dropped` 를 센다).
- **가져가기**(서비스 자격만 — `Authorization: Bearer <GW_TOKEN>` 정확히 한 번, `X-Forwarded-*` 가 실리면 받지 않음 — 결과 손잡이 내부 창구와 같은 막기)
  - `GET /internal/interactions?cursor=<글>&max=500` → `{events: [...], next_cursor, more}` — cursor 가 비면 가장 오래된 것부터.
  - `POST /internal/interactions/ack` `{cursor}` → 그 자리까지 다 읽힌 조각을 지운다.
- `/health` 에 `interactions: {enabled, spool_bytes, segments, dropped, oldest_ts}`.
- 포털 nginx 는 `/mcp-gw/internal` 을 이미 막는다(TS-9 의 nginx 줄).

## 4. 비밀 가림(두 리포가 같은 규칙 — 같은 시험 벡터)

- 칸 이름(대소문자 무시)이 `authorization` · `token` · `access_token` · `refresh_token` · `api_key` · `apikey` · `x-api-key` · `secret` · `client_secret` · `password` ·
  `passwd` · `cookie` · `set-cookie` · `session` · `private_key` 이거나 그 말로 끝나면 값을 `<가림:칸>` 으로.
- 글 안의 꼴 — `Bearer <글>` → `Bearer <가림:bearer>` · JWT(`eyJ` 로 시작하는 세 마디 점 이음) → `<가림:jwt>` · PEM 비밀 키 덩어리 → `<가림:pem>` ·
  `-----BEGIN … PRIVATE KEY-----` 사이 전부.
- 시험 벡터 — 이 문서 끝 부록의 다섯 줄을 두 리포 시험이 그대로 쓴다.

## 5. 공유 길(M2)

- **게이트웨이 로컬 도구 `share_conversation`**(캡처 스위치가 켜졌을 때만 등록) — 설명 「사람이 '이 대화를 공유해' 라고 청한 때만 부른다」.
  인자 `title` · `messages: [{role: user|assistant, content}]` · `session_id?` · `client?`. 호출자 PAT 를 포털 `POST /interactions/share` 로 그대로 넘긴다
  (`save_conversation` 과 같은 길 — 주인 = PAT sub).
- **포털 `POST /interactions/share`**(PAT 또는 세션 + CSRF · `INTERACTIONS_ENABLED`) — 본문 `{session_id?, title?, client?, messages?: [...], transcript?: <Claude Code
  기록 JSONL 글>}`(둘 중 하나 · 50 MB 상한). 같은 `session_id` 는 덮어쓴다. 서버도 가림을 한 번 더.
- **PC 킷** — 토큰 화면 설정 배치의 선택 칸 「내 Claude 대화를 포털에 공유」(기본 끔). 켜면 ① Claude Code 사용자 명령 `/hwax-share`(지금 세션의 기록 파일을 올리는
  작은 PowerShell 을 부른다 — 없으면 `share_conversation` 으로) ② 선택 — 세션 끝 자동 올리기(`SessionEnd` 훅). 끄고 다시 돌리면 걷는다(토큰 절감 E 와 같은 표지 꼴).

## 6. 열람 · 지우기(M3)

- `GET /interactions/me?q=&surface=&before=` · `GET /interactions/me/{id}` · `DELETE /interactions/me`(전부 지우기 청구 — 확인 글) — 본인만.
- 권한 `feat:interaction-analyst`(`grant_only` — 「전부」 · 관리자 전권에 딸려 오지 않는다). `GET /interactions/admin/search` · `GET /interactions/admin/{id}` —
  원문 열기마다 `view_audit` 한 줄.
- 화면 — 「내 기록」(모든 사용자) · 관리 › 「상호작용 기록」(분석가만). 꺼진 박스에서는 메뉴가 없다.

## 7. 알림 문구(초안 — 사람이 확정)

「이 포털을 거친 대화와 도구 호출은 기록되어 품질 개선과 지식 정리에 쓰입니다. 원문은 본인과 지정 분석가만 보며, 언제든 지우기를 청할 수 있습니다.」 — 토큰 화면 ·
웹 챗 첫 화면 · 게이트웨이 initialize instructions · `share_conversation` 설명에 싣는다(켜졌을 때만).

## 부록 — 가림 시험 벡터

| 들어감 | 나옴 |
|---|---|
| `{"Authorization": "Bearer abc.def"}` | `{"Authorization": "<가림:authorization>"}` |
| `{"args": {"api_key": "k-123", "q": "응력"}}` | `{"args": {"api_key": "<가림:api_key>", "q": "응력"}}` |
| `curl -H 'Authorization: Bearer x1y2z3'` | `curl -H 'Authorization: Bearer <가림:bearer>'` |
| `토큰 eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ4In0.c2ln 끝` | `토큰 <가림:jwt> 끝` |
| `{"user_password": "p@ss", "count": 3}` | `{"user_password": "<가림:user_password>", "count": 3}` |

## 8. 짓고 나서 정한 꼴 — 게이트웨이(`wt1124/interactions` `f28ae6c`, 11-24)

- **자리** — 창고 기본 자리는 게이트웨이 곁이 아니라 결과 손잡이 · 그림 보관과 같은 체크아웃 밖 규칙(데이터 루트의 `interaction_spool`, 원장이 리포 안이면 리포
  옆 `<리포>-interaction_spool`, `GATEWAY_INTERACTION_SPOOL_DIR` 이 덮음). 조각 `ix-<첫 줄 ms>.jsonl` · 0600 · 폴더 0700.
- **호출을 늦추지 않는 법** — 처리기는 칸만 대기열에 넣고 돌아가고, 가림 · 쓰기는 일꾼 스레드 하나(대기열이 차면 버리고 `dropped`).
- **`args`** — 1 MB 를 넘으면 앞부분 글이 되고 `args_chars` 칸이 붙는다(객체가 아닐 수 있다). **`result_chars` · `result_sha256`** 은 가린 원문 전체 기준(가리기
  전 지문은 짧은 비밀을 맞혀 보는 길이 된다). 글 블록이 하나뿐이고 structuredContent 와 같은 JSON 이면 한 번만 싣는다.
- **가림 차례** — PEM → Bearer → JWT(Bearer 먼저면 `Bearer -----BEGIN…` 덩어리가 남는다). '끝나면' 은 글자 그대로의 끝 · Bearer 뒤 구분은 빈칸 · 탭 · 결과 글이
  JSON 이면 칸 이름까지 가린다. 포털도 같은 차례.
- **가져가기** — `max` 1 ~ 2000(기본 500) · 한 번에 ≤16 MB · 적어도 한 줄 · cursor 는 불투명 글(지금 꼴 `v1.<조각 ms>.<바이트 자리>` — 포털은 읽지 않는다) ·
  ack 답 `{ok, deleted, segments, spool_bytes}` · 내준 적 없는 자리 400. 내부 창구 막기는 `x-forwarded-` 로 시작하는 머리 전부로 넓혔다(결과 손잡이와 같은 함수).
- **`/health`** — `interactions: {enabled, spool_bytes, segments, dropped, errors, oldest_ts}`.
- **모든 자격을 적는다** — pat · chat · procedure · mcp-app · gw-token · service 를 다 적고 `via` 로 가른다(IX-1). 웹 챗과 겹치는 줄은 포털이 corr 로 거른다.
- **`share_conversation`** — 제목 · session_id · client 200자에서 자름 · 포털 200 · 201 둘 다 성공 · 50 MB 넘으면 보내지 않음 · 포털 404 면 「포털에서 수집이 꺼져
  있다」 · 그 호출 자체도 수집 줄로 남으니 포털 수집기는 `share_conversation` 줄을 건너뛴다(shared_sessions 와 겹치지 않게).
- **§7 알림** — 게이트웨이 지침이 가장 길 때 이미 2,031자라 계약 문구를 넣으면 2,048자를 넘는다. 들어가면 문구 그대로, 넘으면 「호출은 기록된다.」 한 줄을 싣는다
  (전체 문구는 `share_conversation` 설명에) — 이 세션 판단(권장안), 문구는 사람이 확정할 때 함께 다시 본다.
