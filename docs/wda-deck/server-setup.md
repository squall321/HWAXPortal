# 발표자료로 — 박스에서 켜기 · 확인(사람 몫, cae00 · dev 공통)

> 계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md) · WDA 요청서 [wda-request.md](wda-request.md).
> 포털은 박스 스위치를 꺼 둔 채 올라간다(`wda_deck_enabled` 기본 False). 아래 0 이 끝나기 전에는 스위치를 켜도 단추가 서지 않는다 — WDA 가
> 주인 기능(`owner`)을 알리지 않으면 포털이 숨긴다(WD-D23 · D24).

## 0. 먼저 — WDA 쪽

1. WDA 가 요청서 W-1 ~ W-12 를 main 에 커밋하고 GitHub 에 push 한다 — WDA 세션이 맡는다(11-01 밤 뒤집힘 — 사용자가 WDA 세션에 직접 맡겼고 그 세션이 SSH 로 올렸다(`6d6abb6..df446ae`, 역사 그대로 · WD-D85)). 허브가 앱 커밋이 바뀐 것을 보고 SIF 를 저절로 새로 짓는다. **짓기만으로는 떠 있는 인스턴스가 바뀌지 않는다** — dev 는 `cd ../HEAXHub && bash deploy/apptainer/redeploy-app.sh web-design-agents` 로 바꾸고, cae00 은 Drive 판을 `dist-from-drive.sh` 로 받은 뒤 같은 `redeploy-app.sh web-design-agents` 로 바꾼다(WDA 세션 실측 11-01 — 새 SIF 가 서도 10-10 에 뜬 인스턴스가 그대로 돌았다).
2. 허브 매니페스트 `launch.portal_auth: true`(HEAXHub `385783f`)가 이 박스에 들어와 있다 — 포털 주소로 익명
   `/apps/web_design_agents/api/health` 를 부르면 401 이다.
3. 심의 결과 카드 · `/보고서` 저장 답의 단추는 WDA 의 심의 꼴이 준비된 뒤에만 선다(U-6 — 심의 형식이 설 때까지 숨긴다) — `/api/health` 의 features 에
   `format:delib-16x9` 가 있고 `formats` 에서 그 꼴이 `active` 여야 한다(W-21 · WD-D39 — 11-01 저녁 WDA 로컬 판은 draft, draft 는 숨긴다 — 사용자 결정 WD-D42 · 손잡이 없음). 그 전에는 RA 보내기 알림 자리에서만 선다.

## 1. 포털 켜기

- `backend/.env` 에 `WDA_DECK_ENABLED=true` 를 적고 포털만 다시 띄운다 — `apptainer instance stop hwax_portal && ./infra/scripts/start.sh`.
  (화면을 고친 판이면 `cd frontend && pnpm build` 가 먼저다.)
- WDA 주소는 `backend/config/routes.env`(+ `routes.local.env`)의 `apps`(허브 Caddy) 뒤에 `web_design_agents` 를 붙여 정한다. 다르면
  `WDA_BASE_URL` 로 준다 — 허브 Caddy 의 `/apps/web_design_agents` 여야 한다(루프백 포트 직결 금지 — 신원 머리를 Caddy 가 싣는다).
- 허브의 `PORTAL_AUDIENCE` 가 `heax-hub` 가 아니면 `WDA_HUB_AUDIENCE` 를 같은 값으로 적는다.
- 한도 손잡이 — `WDA_DECK_INFLIGHT_MAX`(사람당 2) · `WDA_DECK_INFLIGHT_BOX_MAX`(박스 전체 4) · `WDA_DECK_REPORT_MAX_MB`(16) ·
  `WDA_DECK_JOB_DAYS`(7) · 늦음 문턱 `WDA_DECK_LATE_PREPARE_S`(300) · `WDA_DECK_LATE_RENDER_S`(900) · `WDA_DECK_LATE_VIDEO_S`(3600) ·
  `WDA_DECK_GIVE_UP_S`(21600). 기본값이면 적지 않는다.
- `/보고서` 저장 답의 단추는 에이전트 서버도 이 판(`result` 의 `ra_report`)으로 다시 떠 있어야 선다 — `cd ../HWAXAgentServer && ./start.sh -d`
  (심의가 돌면 update-all 이 미룬다 — `docs/delib-ops/` 의 절차를 따른다).

## 2. 확인

1. 로그인한 화면에서 `GET /agent/deck/status` — `enabled: true` 여야 한다. 아니면 `reason` 이 까닭이다 — `off`(스위치) · `permission`
   (`plat:webdesign` · `plat:reportarchive`) · `no_base`(WDA 주소) · `unknown`(허브 · WDA 가 답하지 않음 — 그 사람의 허브 계정 · `PORTAL_AUDIENCE`) ·
   `no_owner`(WDA 판이 낡았다 — 0 의 1). `formats.deliberation` 은 WDA 의 `delib-16x9` 가 active 일 때 참이 된다(W-21).
2. RA 보내기 알림 하나에서 '발표자료로' → 기본(PPT · PDF · 정식 보고서)으로 만들기 — 몇 초 뒤 그 대화에 받기 링크 알림이 남고, 링크로 PPT · PDF 가
   내려받아진다.
3. 다른 계정으로 그 받기 링크를 열면 404 다(포털 기록의 주인 · WDA 의 주인 두 겹).
4. 익명으로 WDA 의 `/api/runs` 를 열면 401(허브) — 로그인한 다른 사람에게는 그 run 이 목록에 없다(W-3).

## 3. 끄기

`WDA_DECK_ENABLED` 를 지우고 포털을 다시 띄운다 — 창구가 404 가 되고 단추가 사라진다. 잡 기록(스테이징 `#deck-jobs`)은 7일 뒤 청소된다.
