# E-5 전문가 고르기 검토 — 화면 ⇄ 포털 ⇄ 에이전트 서버 계약(`seat-review/1` · `seat-questions/1`)

> 2026-10-31(KST) 세움. 설계는 [design-e5.md](design-e5.md) 2.2 H · 2.4 · 4절 E5-2 이고, 까닭은 [context-notes.md](context-notes.md) C-41 ~ C-47 이다.
> 에이전트 서버 쪽 정본은 HWAXAgentServer `seat_questions.py` 와 그 README 'Seat-choice baseline' 절이다(같은 날 에이전트 서버 E-5 작업 — 이 문서를 쓸 때 아직
> 합치지 않은 작업 트리였다). 포털 쪽은 `backend/app/auth/routes/seat_review.py` · `backend/app/agent/seat_review_harvest.py` · 화면 `/admin/seat-review` 다.
> 칸을 바꾸면 두 리포를 같이 고치고 이 문서의 4절에 적는다 — 포털 시험 `test_seat_review.py` 맨 끝이 형제 리포의 진짜 모듈로 한 바퀴 돈다(합치기 전의 작업 트리는 `HWAX_AGENT_SERVER_ROOT` 로 준다).

## 0. 한눈에

- 실사용 질문(H)의 후보와 사람의 정답 표시는 **에이전트 서버의 박스 파일**(`<seat-eval>/questions/` — 잡 원장의 형제, 리포 밖 · 0600)에만 있다.
  포털은 저장하지 않는다 — 관리자 세션 + CSRF 로 받아 에이전트 서버 창구(공유 비밀)에 넘긴다(도구 검색 검토 E-9 와 같은 꼴). B0 러너(`tools/seat_eval.py`)가
  그 박스 파일을 읽는다.
- 모으는 길은 둘이다. ① 켠 뒤의 발화 — 에이전트 서버가 챗 턴 · MCP `deliberate_start` 를 받을 때 바로 남긴다(출처 넷). ② 켜기 전의 날들 — 포털이 제 대화 저장소에서
  출처 셋(지목 전문가 챗 · 띵킹 · '/전문가')을 떼어 `ingest` 로 민다(화면의 '지난 날 모으기'). 사람이 고른 심의 좌석은 포털 저장소에 없어 ② 에 없다.
- 스위치는 **하나**다 — 에이전트 서버 env `SEAT_QUESTIONS_COLLECT=1`(기본 꺼짐 · 사용자 결정 D-E5-2 (가) — 도구 검색 질의 모으기처럼 허락을 받은 박스에서만).
  꺼져 있으면 에이전트 서버는 아무것도 적지 않고 `ingest` 도 거절하며, 포털은 대화 저장소를 **읽지도 않는다**. 창(일)은 `SEAT_QUESTIONS_DAYS`(60) 하나를 같이 쓴다.
- 화면에는 질문 글 · 날짜 · 출처 · 전문가 이름 · 설명 · 내 표시 · 다른 사람 표시의 **수**만 간다. **순위 · 점수 · 지금 좌석(사람이 고른 전문가 · 답한 좌석) ·
  표본 질문은 어느 화면 답에도 없다**(누설 규칙 L6 · L1). 포털은 에이전트 서버 답을 허용 목록으로 다시 걸러 낸다 — 그쪽이 칸을 더 실어 보내도 화면에 닿지 않는다.
- 다는 사람은 사람이 정한다 — 에이전트 서버 env `SEAT_QUESTIONS_LABELERS`(쉼표, 비면 누구나). 포털이 넘기는 표시자 이름(`by`)은 그 관리자의 메일(소문자)이다.

## 1. 포털 ⇄ 에이전트 서버 — `seat-questions/1`

### 1.1 공통

- **공유 비밀** — 포털은 `Authorization: Bearer <GATEWAY_SHARED_TOKEN>` 을 싣고, 에이전트 서버는 제 MCP_CONFIG 게이트웨이 연결의 `Authorization` 값과 상수 시간으로
  견준다(`seat_probe.authorized`). 세 값(포털 `GATEWAY_SHARED_TOKEN` · 게이트웨이 `_gateway.token` · 에이전트 서버 MCP_CONFIG bearer)은 박스마다 이미 같다 —
  새 비밀이 없다. 다르면 `401 {"error": "unauthorized"}`, 견줄 값이 없으면 `503 {"error": "공유 비밀이 없다 — …"}`.
- **판** — 포털은 요청마다 `X-Seat-Contract: seat-questions/1` 머리를 싣는다(그쪽은 아직 보지 않는다). 그쪽 200 답에 `contract` 칸이 **있으면** `seat-questions/1`
  이어야 하고, 없으면 이 판으로 본다 — 대신 꼴을 본다(아래 '꼭 있는 칸'). 다르면 포털은 502 '꼴 · 판이 다르다'. 그쪽 본문은 선언하지 않은 칸을 422 로 거절하므로
  판을 본문에 싣지 않는다. 칸을 더하는 것은 같은 판이다(포털은 허용 목록이라 화면에 안 닿는다). 뜻을 바꾸거나 빼면 `seat-questions/2` 로 올리고 두 리포를 같이 받는다.
  — **권하는 것**(에이전트 서버): 네 답에 `"contract": "seat-questions/1"` 을 더한다. 더하기만이라 지금 포털과 맞는다.
- **오류 본문** — `{"error": "…"}`. 포털이 옮기는 법 — 400 · 404(사유 있음) · 409 · 422 는 그 상태 · 사유 그대로, 401 → 502(공유 비밀이 다르다), 사유 없는
  404 · 405 → 502(에이전트 서버가 이 판보다 낡았다 — 창구 없음), 닿지 못함 · 그 밖 → 502.

### 1.2 창구

| 창구 | 본문 · 질의 | 200 답 — 꼭 있는 칸 | 그 밖 |
|---|---|---|---|
| `GET /seat-questions?src=&by=&limit=&offset=` | `src` ∈ `persona` · `thinking` · `delib` · `expert_cmd`(비면 전부), `by` 표시자 이름, `limit` 1 ~ 500 | `items` — 그리고 `collect` · `days` · `total` · `counts` · `filtered` · `labeled{mine, any}` · `labelers` | 422(모르는 src) |
| `POST /seat-questions/label` | `{qid, by, primary(1 ~ 3) \| none(core_data · out_of_pool) \| unsure, also(0 ~ 5 — primary 가 있을 때만), via{key: tree\|search}, memo(300자), remove?}` | `ok` — 그리고 `qid` · `by` · `removed` | 422(꼴 · `SEAT_QUESTIONS_LABELERS` 밖) · 404(박스에 없는 qid) |
| `POST /seat-questions/ingest` | `{items: [{src, text, ts?, picked?}]}` 1 ~ 1,000건 — 사람 · 대화를 가리키는 칸은 거절 | `added` — 그리고 `dup` · `old` · `short` | 409(모으기 꺼짐) · 422 |
| `POST /deliberate/experts`(종전 창구) | `{message, groups, light: true}` — 조직도 명부만(추천을 돌리지 않는다) | `pool[{key, name, tags}]` | — |
| `POST /catalog/agent`(종전 창구) | `{key, groups}` | `name` · `role`(설명) — 그 밖의 `samples` · `prompt` · `records` · `tags` 는 포털이 버린다 | `error` 칸 |

`GET /seat-questions` 의 질문 한 줄은 `{qid("H-" + 12자), d(날짜 — 시각은 없다), src, text, mine(이 by 의 표시 — {primary, also, none, unsure, via, memo, t} · 없으면 null),
others(다른 사람 표시의 수)}` 다. 차례는 출처를 번갈아, 출처 안은 qid 의 해시 순이다 — 시스템 점수가 아니다. 8자 아래 · 홀로 서지 않는 발화 · 3글자 조각 자카드
0.8 이상의 겹침은 빼고 `filtered` 에 수만 싣는다. `picked`(사람이 고른 전문가)는 박스 파일에만 있고 이 답에는 없다 — 표시를 끝낸 뒤 러너가 맞대기에 쓴다(design-e5 2.4).

## 2. 화면 ⇄ 포털 — `seat-review/1`

관리자(`portal-admin`)만 부른다. POST 는 CSRF(double-submit)를 요구한다. 모든 답에 `"contract": "seat-review/1"`.

| 창구 | 하는 일 | 답 |
|---|---|---|
| `GET /auth/admin/seat-review/items?src=&offset=&limit=` | `/seat-questions` 를 `by=<내 메일>` 로 | `{total, counts{src: n}, filtered, labeled{mine, any}, collect{on, days}, labelers_set, me{by, can_label}, items[{qid, d, src, text, mine, others}]}` |
| `GET /auth/admin/seat-review/catalog` | 조직도 명부(light) — 운영자(`he-`)를 빼고 키 순 | `{experts[{key, name}]}` — 조직도 라벨은 화면이 정본 `orgTaxonomy.json` 으로 붙인다 |
| `GET /auth/admin/seat-review/expert?key=` | 전문가 카드 | `{key, name, desc(설명 앞 400자), error}` — 표본 질문은 싣지 않는다(L1) |
| `POST /auth/admin/seat-review/label` | 내 표시 — 포털도 그쪽 규칙으로 먼저 거르고(운영자는 고를 수 없다), `by` 를 붙여 넘긴다. `remove` 면 `{qid, by, remove}` 만 | `{ok, qid, removed}` |
| `POST /auth/admin/seat-review/collect` | 지난 날 모으기 — 그쪽 스위치를 먼저 묻고(꺼져 있으면 409 · 저장소를 안 읽는다), 대화 저장소를 읽기 전용으로 떼어 1,000건씩 민다. 한 번에 하나 | `{harvest{days, seen, sent, skipped, scrubbed}, agent{added, dup, old, short}}` — 수만 |

`me.can_label` 은 `by` 가 있고(메일이 그쪽 꼴 — 영문 · 숫자 · `._@-` 40자 — 이 아니면 메일 앞부분, 그래도 아니면 빈 값) `labelers` 가 비었거나 그 안에 있을 때다 —
그쪽이 같은 규칙으로 거절한다(글자 그대로 견준다 — `SEAT_QUESTIONS_LABELERS` 에는 메일을 소문자로 적는다).

## 3. 지난 날 모으기 — 포털이 떼어 내는 규칙

창은 그쪽 `days`(=`SEAT_QUESTIONS_DAYS`)다. 출처를 가르는 규칙은 에이전트 서버 `app._seat_q_source` 와 같게 둔다(다르면 같은 발화가 두 길에서 다른 출처로 든다).

| 출처 | 대화 저장소에서 |
|---|---|
| `persona` | 대화의 첫 사람 발화이고 그 발화 meta 에 고른 전문가(`pinned_agent` · `pinned_agents`)가 있다 — 앞선 사람 발화가 없다. `picked` 에 그 전문가(목록이 있으면 목록 — 그쪽 `_persona_keys`) |
| `thinking` | `## Thinking —` 로 시작하는 답 바로 앞의 사람 발화 — 빗금 트리거(`/띵킹` · `/생각` · `/thinking` · `/think`)는 뗀다 |
| `expert_cmd` | `/전문가` · `/에이전트` · `/agents` · `/agent` 로 시작하는 사람 발화의 나머지 글(그쪽 `strip_agent_trigger` 의 빗금 갈래) |

- 한 발화는 한 출처에만 — `expert_cmd` > `thinking` > `persona`. 그 밖의 빗금 명령(`/심의` · `/보고서` · 글 없는 `/띵킹`)은 넣지 않는다.
- 떼는 것 — 대화 · 메시지 id 와 주인을 싣지 않는다. 메일 주소는 `[메일]`, 포털 원장의 사람 이름(한글 2자 이상 · 영문 3자 이상 — 괄호 앞 머리도) · 메일 앞부분(점 ·
  밑줄 · 붙임표 · 숫자가 든 3자 이상)은 `[이름]`. 그쪽이 받을 때 메일 · uuid · 긴 16진 id · 전화를 한 번 더 지우고 날짜만 남긴다 — 발화 시각(`ts`)은 그 날짜와 창 밖
  거름에만 쓰인다. 원장에 없는 사람의 이름까지 가리지는 못한다 — 화면은 cae00 관리자에게만 간다(design-e5 9절).
- 짧은 글 · 홀로 서지 않는 글 · 겹침은 그쪽이 센다 — 포털은 거르지 않는다(한 곳에서 센다). 같은 글은 그쪽이 qid 로 거르므로 다시 눌러도 겹치지 않는다.
- 저장소는 읽기 전용 연결(`mode=ro`)로 연다 — WAL 이라 저장을 막지 않는다(백업과 같은 방식).

## 4. 바꾼 적

| 판 | 날 | 바뀐 것 |
|---|---|---|
| `seat-review/1` · `seat-questions/1` | 2026-10-31 | 처음 — 포털이 처음 짠 안(창구 이름 `/seat-review/*` · 포털 쪽 스위치 · 자리 a · b)을 걷고 에이전트 서버가 먼저 지은 `/seat-questions*` 에 맞췄다(C-42) |
