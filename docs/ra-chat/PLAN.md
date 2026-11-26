# 챗 안의 Report Archive — 내 부서 시작 카드 · 보고서 링크 접두(2026-11-26)

> 체크리스트는 [checklist.md](checklist.md), 결정과 까닭은 [context-notes.md](context-notes.md).

## 요청(사용자, 2026-11-26)

1. **보고서 링크:** 챗에서 RA 를 조회하면 참조 링크가 나온다. 그런데 `/report-archive/w/<공간>/reports/<번호>` 여야 할 링크에서
   `/report-archive` 가 빠진다.
2. **내 부서 시작 카드:** 포털 첫 화면에 나의 Report Archive 조직(파트 · 그룹)을 표기하고, 처음부터 「내 부서의 최근 이슈를 조회해 볼까요」
   제시어가 나오면 좋겠다.

## 1. 링크 접두 — 원인과 고침

- RA 도구의 보고서 주소는 RA 루트 기준 상대 경로 `"url": "/w/<공간>/reports/<번호>"` 다. RA 의 `reports/routes.py` 등이 이렇게 만들고,
  dev 대화 저장소의 도구 결과에서도 이 꼴을 확인했다.
- 챗 LLM 은 이 경로를 그대로 마크다운 링크로 옮긴다.
- 화면 [TextBlock.tsx](../../frontend/src/components/chat/renderers/TextBlock.tsx) 는 `/` 로 시작하는 링크 앞에 `config.apiBase` 만
  붙인다. 그래서 포털 주소에 `/w/…` 가 바로 붙는다. 포털에는 `/w/` 경로가 없다.
- 이 바꿈은 [raLink.ts](../../frontend/src/components/chat/raLink.ts) 에 이미 있지만 심의 결과 카드 · 업로드 알림에서만 쓰인다.

**고침:** 챗 본문 링크가 RA 화면 경로(`/w/<공간>` 와 그 아래)이면 앞에 `/report-archive` 를 붙인다. 화면에서만 바꾸므로 지난 대화도 다시 그릴 때
함께 고쳐진다. LLM 이 보는 글은 바뀌지 않는다.

## 2. 내 부서 시작 카드

**재료(RA 판 `04a147e` 에서 확인).**

- 내 부서: RA `GET /api/me` 의 `home_workspace_slug`. RA 가 「권위 있는 소속 신호」라고 적은 칸이다. 부서 머리 없이 부를 수 있다.
- 위 단계: RA `GET /api/workspaces` 의 `parent_slug` 로 위로 올라간다. 개인 공간은 그 주인에게만 보인다.
- 조회: RA 도구 `list_reports(board=<게시판>, last_days=N)`. RA 는 「조직 단위는 어느 게시판에 게시됐는지로만 정해진다」고 적는다(`list_boards`
  설명).

**포털 서버.** `GET /agent/ra/home` 은 그 사람 명의(위임 먼저 · 등록 토큰 다음, 서비스 계정 없음)로 위 두 창구를 부른다. 답은
`{home, chain}` 이다. `chain` 은 위에서 아래로 놓은 부서 사슬이고 끝이 홈 부서다. RA 연결이 없거나, 홈 부서가 없거나, RA 가 실패하면
`{home: null, reason}` 을 200 으로 돌려준다. 이 경우 첫 화면은 카드 없이 그대로 뜬다.

**화면.** `plat:reportarchive` 가 있는 사람에게만 묻고, 한 탭에 한 번만 묻는다. 첫 화면 인사 아래에 「Report Archive · 그룹 › 파트」를
표기한다. 시작 카드 맨 앞에 「○○파트 최근 이슈」를 둔다. 누르면 입력창에 「Report Archive 의 ○○파트 게시판(slug)에 최근 2주 동안
올라온 보고서를 찾아 주요 이슈를 정리해줘」가 들어간다. 보내기는 사람이 누른다.

## 범위 밖

- 개인 Claude 가 MCP 로 RA 를 부를 때도 같은 상대 경로를 받는다. 그쪽은 호스트까지 붙여야 해서 따로 다룬다.
- RA 리포는 고치지 않는다(커밋 · push 금지).

## 반영

화면만 바꾼 것은 `cd frontend && pnpm build` 를 하면 반영되고, 서버 창구는 포털을 재기동해야 반영된다. cae00 에는 다음 update-all 로 들어간다.
