# Report Archive 에 청하는 것 — 쓰기 경합 막기 · 태그 하나 떼기(2026-11-22)

> 보내는 쪽 HWAX 포털. 받는 쪽 Report Archive 담당. 포털은 RA 리포에 쓰지 않으므로 이 글을 사용자가 전한다.
> 대조한 판은 RA v0.186.3(`b552f09`)이다. 아래의 파일 · 함수 이름은 그 판의 것이다.

포털과 에이전트 서버는 사람 명의로 RA 보고서에 쓴다. 두 군데서 RA 쪽 창구가 없어 포털만으로는 닫지 못하는 일이 생겼다. 청하는 것은 넷이다.
앞의 셋은 같은 일(쓰기 경합)이고, 넷째는 따로다. 넷 다 기존 호출의 동작을 바꾸지 않는 덧붙임으로 지을 수 있다.

## 1. 쓰기 경합 — 남의 쓰기가 방금 붙인 칸을 지운다

**일어나는 일.** 포털은 그림 칸을 붙일 때 `GET /api/reports/{id}/outline` 으로 쪽 구성을 읽고 `PATCH /api/reports/{id}/ai-draft` 의 `extra_blocks` 로
붙인다. RA 의 ai-draft 쓰기는 보고서 행을 읽고 합치고 쓴다(`routes._apply_ai_draft` → `services.update_report(expected_revision=None,
require_lock=False)`). 같은 보고서에 다른 ai-draft 쓰기가 겹치면(예: 개인 Claude 가 MCP `update_report_draft` 로 같은 쪽을 고침) 한쪽이 읽은 뒤 · 쓰기
전에 다른 쪽이 쓰고, 나중 쓰기가 먼저 쓰기의 칸을 지운다. 포털은 이미 「붙였다」 고 답한 뒤라 사람은 칸이 사라진 것을 모른다.

포털은 포털을 지나는 쓰기끼리는 보고서마다 줄을 세운다. 포털 밖의 쓰기(게이트웨이를 거친 RA MCP 도구)와의 경합은 RA 만 닫을 수 있다.

> **11-24 덧붙임.** HWAX 게이트웨이가 자기를 지나는 본문 쓰기(그림 넣기 · `update_report_draft` · `append_rows` · `patch_cells` · `remove_rows` ·
> `restore_version`)를 보고서마다 한 줄로 세우게 지었다(다음 배포에 실린다). 그래서 게이트웨이를 지나는 쓰기끼리는 RA 의 덧붙임 없이도 닫힌다.
> 남는 것은 게이트웨이를 지나지 않는 쓰기다 — RA 화면의 「Local LLM 작성」, 다른 길로 RA MCP 에 바로 붙은 클라이언트. 이 방향은 3 의 행 잠금으로만
> 닫힌다. 그래서 이제 가장 바라는 것은 3 이고, 1 · 2 는 있으면 좋은 것이다.

**청하는 것.**

1. **`GET /api/reports/{id}/outline` 답에 `revision`.** 지금은 `GET /api/reports/{id}` 와 쓰기 답(`data.report.revision`)에만 있다. 포털은 쪽 구성을
   outline 으로 읽으므로 같은 답에서 판을 받아야 그 판에 맞춰 쓸 수 있다.
2. **`PATCH /api/reports/{id}/ai-draft` 본문(`AiDraftUpdate`)에 `expected_revision: Optional[int]`.** `_apply_ai_draft` 가 그 값을
   `update_report(expected_revision=…)` 에 넘기면 된다. 어긋나면 다른 창구(`PATCH /ai-draft/rows` · `PATCH /{id}`)와 같은 409
   `{success: false, message, errors: [{code: "revision_mismatch"}]}` 를 내 주면 좋다. 비어 있으면 지금과 같다. MCP `update_report_draft` 에도 같은 인자가
   있으면 개인 Claude 와 에이전트 서버의 심의 이어붙이기(쪽 수를 읽고 다음 쪽에 쓴다)도 같은 확인을 할 수 있다.
3. **본문을 통째로 다시 쓰는 창구 셋의 행 잠금** — `PATCH /ai-draft`, `PATCH /ai-draft/rows`(칸 하나만 고쳐도 `ReportUpdate(pages=kept)` 로
   모든 쪽을 다시 쓴다), `POST /versions/{vid}/restore`. 셋 다 `services.update_report` 로 가고, 지금 판 검사는 요청 처음에 읽은 행과 견주는 파이썬
   비교(`report.revision != expected_revision`)다. 두 요청이 같은 행을 읽은 뒤 차례로 쓰면 둘 다 통과한다. `update_report` 에서 행을
   `SELECT … FOR UPDATE` 로 읽거나 `UPDATE … WHERE id = :id AND revision = :읽은 판` 으로 쓰면 세 창구가 한꺼번에 닫힌다.
   **1 · 2 만으로는 경합이 닫히지 않는다.** 포털이 싣는 판은 포털 자신의 쓰기만 막고, 남의 쓰기가 포털의 칸을 덮는 방향은 3 이 있어야 막힌다.

**포털 쪽은 이미 지어 두었다.** outline 답에 `revision` 이 오면 진짜 PATCH 에 `expected_revision` 으로 싣고, 409 `revision_mismatch` 면 다시 읽어
다시 붙인다(세 번까지). 다시 읽은 쪽에 같은 칸이 이미 있으면 붙이지 않는다. 지금 판의 RA 에는 싣지 않으므로 요청 · 동작이 종전과 같다 — RA 가 1 · 2 를
올리면 포털 재배치 없이 저절로 켜진다.

## 2. 보고서에서 태그 하나 떼기

**일어나는 일.** 포털의 과제 인사이트는 사람이 누르면 그 카드의 RA 보고서에 SP 과제 객체(code = SP 키)를 태그로 단다
(`POST /api/reports/{id}/entities/add` — 합집합만 더하고 편집 잠금을 요구하지 않는 창구). 주인이 카드를 거두면 그 태그를 떼고 싶은데, 사람 권한으로
태그를 바꾸는 길은 보고서 `PATCH`(·`ai-draft`)의 `entity_ids` **통째 교체**뿐이다. 읽고 · 빼고 · 쓰는 사이에 다른 사람이 단 태그를 지울 수 있고,
누가 편집 화면을 열어 두면 잠금에 걸린다. 그래서 지금은 떼지 않고 「RA 보고서 편집 화면에서 손으로 뗀다」 고 알린다.

**청하는 것.**

4. **`POST /api/reports/{id}/entities/remove` `{entity_ids: [...]}`** — `entities/add` 의 짝. 준 id 만 빼고(차집합) 나머지는 그대로 둔다. 권한 · 잠금
   규칙은 `entities/add` 와 같게(`can_read_report` · `can_edit`, 편집 잠금 없음). 답도 같은 꼴 `{report_id, entity_ids(적용 후 전체), removed(뺀 수)}`
   이면 포털이 그대로 읽는다. 붙어 있지 않은 id 는 오류 없이 `removed: 0` 이면 다시 보내도 안전하다. MCP 에도 짝 도구가 있으면 좋다(필수는 아니다).

**포털 쪽.** 창구가 생기면 카드를 거둘 때 그 사람 명의로 이 창구를 불러 포털이 단 태그 하나만 떼게 바꾼다. 그 전까지는 지금처럼 남겨 두고 알린다.

## 3. 받는 쪽 확인 — 답을 받으면 포털이 하는 일

| 청 | RA 가 올리면 | 포털 |
|---|---|---|
| 1 · 2 | outline `revision` · ai-draft `expected_revision` | 재배치 없이 저절로 켜진다. 같은 판의 시험을 실물로 다시 본다 |
| 3 | 행 잠금 | 할 일 없다. 경합 재현 시험을 실물로 다시 본다 |
| 4 | `entities/remove` | 거두기에 태그 떼기를 붙인다(포털 한 커밋 · 포털 재기동) |

판 번호를 알려 주면 포털이 그 판으로 다시 대조한다.
