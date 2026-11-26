# 리스크 앱 화면 요청 — 종합 보고서를 RA 시스템 공간에 올리는 단추(2026-11-26)

> 받는 곳: 리스크 앱(HWAXRisk) 화면을 맡은 세션. 배경은 [PLAN.md](PLAN.md).

## 무엇

리스크 종합 보고서를 RA 초안으로 만든 뒤(지금 있는 길), 같은 자리에 「시스템 공간에 올리기」 단추를 둔다. 포털 심의 결과 카드와 같은 흐름이다.

1. 화면에 처음 그릴 때 `GET /agent/ra/post-target` 을 한 번 부른다. `board` 가 null 이면 단추를 그리지 않는다. 운영 박스가 게시판을 정하지
   않은 것이다.
2. 단추를 누르면 `GET /agent/ra/reports/{report_id}/post-preview` 를 부른다. 답은 `{board, targets:[{slug, name, audience, already_mounted, blocked}],
   ok}` 다.
   - `already_mounted` 면 「이미 게시돼 있습니다」를 보인다.
   - `blocked` 이거나 `ok` 가 false 면 그 까닭을 보인다.
   - 그 밖에는 「「{name}」 게시판 — {audience}명이 보게 됩니다. 게시한 뒤에는 작성자가 직접 내릴 수 없고 게시판 매니저의 승인이 필요합니다.」와
     [게시] [취소] 를 보인다.
3. [게시] 를 누르면 `POST /agent/ra/reports/{report_id}/post` 를 부른다. 세션 + CSRF 다(포털 화면의 `apiFetch` 와 같다). 답은
   `{board, name, mounted, already}` 다.

## 지켜야 할 것

- **게시판을 화면이 고르지 않는다.** 포털이 박스 파일에서만 정한다. 보내도 쓰지 않는다.
- **확인 없이 부르지 않는다.** 사용자 결정 11-26 · 11-21 게시 관문이다.
- 오류 답은 `{detail, code}` 다. code 는 `no_board` · `no_ra_connection` · `ra_token_rejected` · `forbidden_by_ra` · `not_found` · `ra_rejected` ·
  `blocked` · `ra_outcome_unknown` · `ra_error` 가운데 하나다. `detail` 을 그대로 보이면 된다.
- 포털 구현은 `backend/app/agent/ra_post.py` · `routes.py` 의 `ra_post_*` 이고, 화면 참고는 `frontend/src/components/chat/RaPostCard.tsx` 다.
