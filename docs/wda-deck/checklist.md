# 발표자료로(RA 보고서 → WebDesignAgents) — 체크리스트

> 계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md) · WDA 요청서 [wda-request.md](wda-request.md).
> 설계 11-01 오전 · 사람 결정 11-01 오후(다섯 모두 — PLAN §13). M1 은 이 가지에서 짓는다 — WDA 계약(W-1 ~ W-12)이 들어오기 전에는 단추가 보이지 않는다.

## 설계(11-01)

- [x] DocForge 배달 꼴 조사(잡 기록 · 주인만 404 · 세션 + CSRF · 한 번만 · 화면이 몬다 · 다시 열기 · 알림) — PLAN §2.1
- [x] 포털이 만든 RA 보고서의 화면 자리 조사(심의 outcome 은 서버 사본에 없다 · `/보고서` 는 글뿐) — PLAN §2.2
- [x] WDA 신원 · 주인 · 익명 접근 · 배치 판 조사(익명 200 실측 · 게이트웨이가 신원을 안 싣는다 · origin/main 에 pdf 없음) — PLAN §2.4
- [x] 문서 넷(PLAN · checklist · context-notes · wda-request) · CLAUDE.md 문서 표 한 줄

## M0 — 사람 결정

- [x] U-1 WDA 주인 기능을 단추를 켜는 전제로 — **예**(WD-D24)
- [x] U-2 WDA push 방법 — **사용자가 손으로**, 누구도 대신 push · 역사 다시 쓰기 하지 않는다(WD-D25) → 11-01 밤 뒤집힘 — 사용자가 WDA 세션에 직접 맡겼고 그 세션이 SSH 로 올렸다(`6d6abb6..df446ae`, 역사 그대로 · WD-D85)
- [x] U-3 허브 매니페스트 `launch.portal_auth: true` — **켠다**, HEAXHub 변경 · dev 반영은 다른 에이전트(WD-D26)
- [x] U-4 'PDF' 의 뜻 — **정식 보고서 문서(report) 기본, brief · memo 선택**, 슬라이드 PDF(W-19)는 청하지 않는다(WD-D27)
- [x] U-5 M1 단추 자리 — **셋 모두**(심의 결과 · `/보고서` · RA 보내기 알림), 루틴 RA 초안은 M2(WD-D28)
- [x] U-6 심의(deliberation 템플릿) 보고서의 단추 — **심의 형식(W-21 `format:deliberation`)이 설 때까지 숨긴다**(WD-D32). `/보고서` 도 deliberation 템플릿이라 같은 문에 걸린다
      — 11-01 저녁 표지 이름은 WDA 의 `format:delib-16x9` 로(WD-D39)
- [x] U-7 심의 꼴이 `draft` 여도 단추를 보일까 — **아니다, active 일 때만 연다 · draft 는 숨김 · 손잡이 없음**(사용자 결정 11-01, WD-D42 —
      `format_ready` 하나 · 시험은 없음 · draft · active 셋)

## M0 — WDA 세션(요청서 §11)

- [x] 요청서를 받고 답했다(11-01, 요청서 §10) — W-1 ~ W-12 는 지금 하나도 없고 **사용자가 직접 시킬 때** 짓는다. 포털은 그 계약대로 지었다(가짜 WDA 로 시험)
      — **11-21 코드 대조**(L21-8 (나) · WDA `wt1121/deck` 의 `src/wdweb/app.py` · `runs.py` · `src/wdmcp/server.py` · `tests/test_portal_contract.py` 를 읽고
      그 시험을 돌려 맞췄다 — 아래 W-1 ~ W-15 의 근거 커밋은 WDA `d1f144b`(계약 본체) · `dcca8ab`(프록시 접두 뒤의 주인 검사))
- [x] W-1 REST 만들기에 `X-Heax-User-Email` 로 owner(본문의 owner 는 믿지 않는다 · `/mcp` 는 정하지 않는다) — WDA `d1f144b`(`create_run` 의
      `owner=identity(request)` · 202 에 owner · 시험 `test_owner_comes_from_the_header_only`)
- [x] W-2 주인 있는 run 의 run 단위 REST 전부 주인만(다른 사람 · 신원 없음 = 404) — WDA `d1f144b`(미들웨어 `_ownership_guard` 한 곳) · `dcca8ab`
      (`--root-path` 뒤에서 통째로 무력하던 것 — `app_path` · 진짜 uvicorn 두 조건 시험)
- [x] W-3 `GET /api/runs` = 내 것 + 주인 없는 것 — WDA `d1f144b`(`get_runs` · `visible_to`)
- [x] W-4 MCP 의 run_id · job_id · 경로 도구와 렌더 잡 내려받기는 주인 있는 run 에 닿지 않는다 — WDA `d1f144b`(`_block_owned` 도구 아홉 ·
      `download_render_job`). 계약 목록 밖의 길(11-21 탐침 — `meeting_start(run_id)` · `report_ingest(file · run_id)` · 주인 없는 회의)은
      **11-22 사용자 결정으로 닫았다**(WDA `4c25b08` · `1da9733` — 웹 길이 신원을 넘기고 회의에 주인 칸, WD-D97)
- [x] W-5 주인 있는 새 run id 128비트 무작위 · run_id 꼴 검사 — WDA `d1f144b`(`new_run_id(owned=True)` · `RUN_ID_RE`)
- [x] W-6 `/api/health` 에 version · features(`owner` · `render_chain` · `doc_formats` · `skipped_report` · `interrupted`) — WDA `d1f144b`(+ `idempotency` ·
      `error_codes` · 꼴마다 `format:<id>`) · 11-21 `delete`(W-17) · 비밀이 있는 박스에만 `mcp_owner`(W-18)
- [x] W-7 본문 16MB(넘으면 413 TOO_LARGE) — WDA `d1f144b`(`MAX_BODY_BYTES`)
- [x] W-8 만들기의 `render` 칸 — 빌드 뒤 이어서 렌더 — WDA `d1f144b`(`render_request` · 재개에도 이어진다)
- [x] W-9 `render.requested` · `render.skipped[{target, reason}]` — WDA `d1f144b`
- [x] W-10 오류 봉투에 `code` — WDA `d1f144b`(`ERROR_CODES` 여섯 · 상태별 기본)
- [x] W-11 내려받기 머리(attachment · Content-Length · nosniff · HTML 은 `Content-Security-Policy: sandbox`) · 생성 HTML 의 보고서 글 이스케이프 —
      WDA `d1f144b`(`download_headers` — 렌더 잡 경로에도). 이스케이프는 `src/wdrender/exporter_doc.py` 의 `_html.escape`(제목 · 본문 · 표 · 출처 —
      코드 읽기로 본 것이고 넣는 자리를 전수로 감사하지는 않았다)
- [x] W-12 재기동에 끊긴 실행 · 렌더를 `failed`(interrupted)로 — WDA `d1f144b`(`mark_interrupted` — 기동 때)
- [x] (강하게 권장 — 지금 보존 · 동시 상한이 없다) W-13 보존 기한 · W-14 렌더 동시 상한 · (선택) W-15 Idempotency-Key — WDA `d1f144b`
      (W-13 은 지었으나 **끈 채**(`WDA_RETENTION_DAYS` 0 — 사용자 결정 11-01) · W-14 `WDA_RENDER_CONCURRENCY` 2 · W-15 같은 키 + 같은 주인이면 같은 run)
- [x] W-21 심의 보고서 꼴 `delib-16x9` 를 지었다(11-01 저녁 — WDA 로컬 판) — features 의 `format:delib-16x9` · `formats` 의 상태 · 만들기의 `format` 칸 · 모르는 꼴 400
- [ ] `delib-16x9` 가 active 가 된다(지금 draft — 포털은 active 만, U-7 결정) · 허브 SIF 에 들어온다(P-1 뒤) · 실물 심의 보고서(템플릿 블록이 `content` 키뿐)로 확인 · 쟁점 장면(WDA 의 다음 일)
      — **11-21 대조** active 는 됐다(WDA `3b7b5d2` · 골든 교체 `3707509`) · 허브 SIF 에 들어왔다(아래 11-07 대조) · 쟁점 장면도 섰다(WDA O-1 — 뼈대 6장면).
      **남은 하나가 붉다 — 실물 꼴의 심의 보고서를 WDA 가 받지 못한다.** RA `GET /api/reports/{id}` 의 템플릿 보고서는 쪽의 `content` 에 템플릿 블록 id 만
      있고 `extra_blocks` 가 비어 있는데(ReportArchive `modules/reports/schemas.py` — 블록 정의는 템플릿 스키마에), WDA ingest 는 정의 없는 `content` 키를
      건너뛰어 `ValueError: 텍스트를 가진 블록이 없다 (블록 0개, 텍스트 0개)` 로 '보고서 읽기' 단계에서 실패한다(11-21 WDA `wt1121/deck` 에서
      `normalize_report` 에 이 리포 시험의 `DELIB` 꼴을 직접 넣어 재현 — 봉투째도 같다). 심의 결과 카드 · `/보고서` · 분석 루틴 초안 셋이 다 이 꼴이다 —
      단추가 서도 발표자료는 실패한다(WD-D94 ① — WDA 의 결정 대기, 요청서 4.6-2 의 그 물음)
      — **11-22 사용자 결정 (나)로 닫았다** — 포털이 그 사람 명의로 RA 템플릿 스키마를 읽어 `template_schemas` 로 싣고(포털 `547b98fc`) WDA 가 그것으로
      블록을 푼다(WDA `56bb9e9`). 실물 꼴(dev RA 의 심의 보고서 70건 — 읽기 전용)로 시험했고 세 출처가 `delib-16x9` 빌드까지 간다(WD-D96).
      남은 것은 배치본에서 실물 보고서 하나로 보는 일이다(아래 M3 — cae00)
- [x] 요청서 §10 의 다섯 물음에 답했다(11-01 — W-1 ~ W-12 없음 · 심의 꼴 안 맞음 · pptx + pdf 나옴 · 5.5초 · 보존 · 동시 상한 없음)
- [x] 주인 있는 run 은 `WDA_RA_*` 서비스 자격으로 RA 그림을 받지 않는다 — **11-21 지음**(WDA `wt1121/deck` `bca5988` · `66a606c`). 받기를 통째로
      건너뛰고(로그인도 없다) 원장 `run.assets{service_fetch, total, resolved, skipped[], skipped_count}` · `run.warnings` 에 드러낸다. 주인은 원장에서
      읽는다(재개도). 주인 없는 run 은 호출 글자까지 종전 그대로(WD-D93)
- [x] P-1 사용자가 손으로 main push(U-2) → 허브 SIF 재빌드(dev) — WDA 세션은 커밋까지만, push 하지 않는다 → 11-01 밤 뒤집힘 — 사용자가 WDA 세션에 직접 맡겼고 그 세션이 SSH 로 올렸다(`6d6abb6..df446ae`, 역사 그대로 · WD-D85) · 허브 SIF 재빌드 진행(11-01 밤)
- [x] dev 확인 — `/api/health` features 에 `owner` · 신원 없는 `GET /api/runs` 에 주인 있는 run 이 없다 · 게이트웨이 `tools/list` 로 도구 판을 대조한다
      — **11-07 KST 포털 쪽 대조**(WDA `073d205` — O-2 장면 고침 `3e52773` · SIF 14:35 KST · 직결 9521, 허브 Caddy 도 9521) — health `owner` · `delib-16x9` active ·
      신원 없는 목록 0 · 허브 경유 익명 `/api/health` · `/api/runs` 401 · 게이트웨이 WDA 도구 24 = WDA `tools/list` 24(이름까지)

## M0 — HEAXHub(다른 에이전트 — 이 가지는 건드리지 않는다)

- [x] P-2 (U-3 결정) `integrations/web-design-agents/.portal/manifest.yaml` 에 `launch.portal_auth: true` · dev 반영 · 익명 `/apps/web_design_agents/…`(health · runs · mcp · 내려받기) 401 확인 — HEAXHub `385783f`(올림, 11-01). 허브 세션 · 유효한 PAT 은 200, 게이트웨이 WDA 도구 16개 그대로

## M1 — 포털(dev)

백엔드
- [x] 먼저 실패하는 시험 셋 — 중계가 심의 outcome 의 보고서 번호를 남긴다 · 서버 사본이 그것을 되살린다(node) · 중계가 `/보고서` 답의 `ra_report` 를 남긴다
- [x] 설정 — `wda_deck_enabled`(기본 False) · `wda_base_url`(빈 값이면 routes.env 의 `apps` + `web_design_agents`) · `wda_hub_audience`(heax-hub) ·
      `wda_deck_job_days`(7) · `wda_deck_report_max_mb`(16) · `wda_deck_inflight_max`(2) · `wda_deck_inflight_box_max`(4) · 늦음 문턱 셋(300 · 900 · 3600) · `wda_deck_give_up_s`(21600) — 경로 설정이 없어 시험 격리는 따로 없다 · `.env.example` 에는 넣지 않는다(박스 스위치는
      `backend/.env` — 다른 박스 손잡이와 같다, server-setup.md)
- [x] `backend/app/agent/wda_deck.py` — 잡 기록(`#deck-jobs` · 0600 · 바꿔 끼우기 · 주인만 404 · 목록 · 숨기기 · 잠금) · 상태 낱말 접기(PLAN §7.2) · 알림 글 · 활동 짓기
- [x] 짧은 허브 PAT 찍기(청중 heax-hub · scope api · 10분 · 무작위 jti · 로그인 그룹만) — 저장 · 로그 없음 · `config.py:243-245` 주석 고치기
- [x] RA 읽기 — `_ra_user_token`(위임 401 은 한 번 새로) · 403 · 404 · 상한이면 WDA 를 부르지 않는다 · 그림(file_id) 수 세기
- [x] WDA 부르기 — 만들기(render 칸) · 진행 · 렌더(대체 길) · artifacts · 내려받기 흘리기 · health 능력 탐침(60초 붙잡음, 모르면 숨김)
- [x] 라우트 — `GET /agent/deck/status` · `POST /agent/deck/jobs` · `GET /agent/deck/jobs` · `GET /agent/deck/jobs/{job}` · `POST …/advance` · `GET …/files/{kind}` ·
      `POST …/dismiss` — 모두 `principal_pat_or_session`(POST 는 CSRF) · `ensure(plat:webdesign, plat:reportarchive)` · 대화 주인 검사
- [x] 한 번만 — 같은 보고서 · 같은 옵션은 하나로 · `again` · 사람당 동시 상한 · 박스 전체 동시 상한(429) · `advance` 잠금 안에서 렌더 맡기기 · 알림(서버 사본에 직접 — `conv_store.append`, 스레드에서)
- [x] 템플릿 문 — RA 보고서의 템플릿에 `deliberation` 이 있으면 `format:deliberation` 이 있어야 만든다(409) · status 가 `formats.deliberation` 을 알린다
- [x] (11-01 저녁 — WD-D39) 템플릿 문을 WDA 의 꼴로 — `format:delib-16x9` 와 `formats` 의 active(정책 함수 `format_ready` 하나) · 만들기에 `"format": "delib-16x9"`
      (그 밖의 템플릿은 칸 없음) · 모르는 꼴 400 은 까닭을 보이고 잡을 남기지 않는다(기본 꼴로 다시 보내지 않는다) · 가짜 WDA 를 꼴 등록부 · `format` 칸 · 400 으로
- [x] (WD-D40) `block_sections` 는 싣지 않는다 — RA 블록 id 에서 단락이 하나로 정해지지 않는다 · 우리 보고서의 실제 낱말을 요청서 4.6-2 에
- [x] (11-01 저녁 — WD-D43) WDA health 의 `version`(패키지 판 = 허브 매니페스트 판)을 잡 기록 `wda.version` · 감사에 남긴다(막지 않는다) · 가짜도 `0.1.0`
- [x] (11-01 저녁 — WD-D41) 스스로 다시 읽고 고친 셋 — 목록이 WDA 를 못 물은 잡을 남긴다 · 줄이 목록을 못 읽어도 다음 차례에 다시 묻는다 ·
      숨기기는 기록을 확인한 뒤 잠근다 · 오류 글 조사('만들기 요청을')
- [x] 내려받기 머리 — attachment(보고서 제목으로 이름, RFC 5987) · nosniff · `Cache-Control: private, no-store` · HTML 은 CSP sandbox · 응답에 WDA 주소 · id 없음
- [x] 스테이징 청소에서 `#deck-jobs` 빼고 기한 뒤 지우기(`upload.py` sweep)
- [x] 감사 — `deck_create` · `deck_render` · `deck_finish` · `deck_download`(본문 · 제목 전문 없음)
- [x] 중계 — 심의 outcome → 답 meta `delib_outcome` · `result` 의 `ra_report` → 답 meta `ra_report`

에이전트 서버(한 칸)
- [x] `run_report_save` 의 `result` 사건에 `ra_report: {id, title}`(HWAXAgentServer `deliberation.py:7913-7914`) · 시험 — 재기동은 확인 뒤(남의 미반영 커밋을 같이 켠다)

화면
- [x] `api/deck.api.ts` · `DeckButton`(출력 · 문서 꼴 고르기 · 진행 칸 · 실패 까닭 · 다시 만들기) · 입력창 위 '끝나지 않은 발표자료' 줄(끝난 잡은 저절로 `advance`)
- [x] 자리 셋 — `DelibView` 결과 카드 · `/보고서` 답(meta `ra_report`) · RA 보내기 알림(활동 report_id) · 권한 둘과 status enabled 일 때만
- [x] `serverMessagesToLocal` 이 `delib_outcome` 을 `delib.outcome` 으로 · live `result` 의 `ra_report` 를 메시지에
- [x] 알림은 응답을 그 대화(서버 id)의 화면 사본에만 붙인다(서버에 다시 쓰지 않는다) · 그 대화가 답을 받는 중이면 끝난 뒤 `advance`
- [x] `cd frontend && pnpm build`(컨테이너는 dist 를 낸다)

시험
- [x] 백엔드(가짜 RA · 가짜 WDA — PLAN §11 목록 전부) · node 순수 함수 · 브라우저(결과 카드 → 진행 → 그 대화에 알림 · 권한 없으면 단추 없음 · 새로고침 뒤에도 산다 · 답 받는 중이면 뒤에)
- [x] 회귀 — `backend` 전체 pytest(파이프로 rc 를 가리지 않는다) · 프론트 타입 검사 · 빌드 · 린트. 결과(11-01, KST 저녁) —
      포털 전체(`91af8992`) 4,228 통과 · 29 건너뜀 · 실패 2 — 둘 다 작업 트리에만 없는 박스 파일 탓(`test_ste_doctor_and_drive` 의 이 박스 배치 상태 ·
      `test_tlscert` 의 `infra/tls` 폴더)이고 이 가지와 무관하다. 그 뒤 커밋(요청서 낱말 · U-7 시험 나눔 · WDA 판 기록)은 발표자료 시험 넷 · md 링크 · 이력 ·
      클러스터 이름 106 통과. 에이전트 서버 전체(`291bbb9`) 4,109 통과 · 2 건너뜀. 화면 빌드 rc 0(타입 검사 포함) · 린트는 손대지 않은 파일의 경고 7(그대로).
      한 줄 변이 36 중 35 가 붉었다(놓친 하나는 WD-D37 의 같은 동작 변이). 새 시험은 모두 고치기 전 코드에서 붉었다

문서 · 기타
- [x] 운영자 페르소나 `he-doc-webdesign` 글 — 포털 보고서는 '발표자료로' 단추로 · `render_status` 되풀이 금지(동기화 시험)
- [x] 변경 이력(`backend/config/changelog.yaml` 11-01 — 연결 · 기술 · 수정) · 이 체크리스트 · context-notes 덧붙이기 · server-setup.md
- [ ] dev 실주행 — WDA 가 W-1 ~ W-12 를 배치한 뒤(지금은 owner 가 없어 단추가 숨는다). 스위치를 켜고 RA 보내기 알림 하나로 PPT + PDF ·
      남의 계정으로 404 · 익명으로 WDA 목록에 안 보이는지(server-setup.md §2) — **11-07 KST** 스위치는 11-02 05:03 KST 부터 켜져 있다 ·
      포털 로그에 만들기(`POST /agent/deck/jobs`) 0건 — 사람 클릭 대기(11-02 에 부탁하고 다시 챙기지 않은 포털 쪽 누락, WD-D86) · 남은 것은 사용자의 화면 걸음 ·
      누를 때 떠 있을 판은 WDA `073d205` · 그 SIF 의 Drive 는 11-07 음성 녹음기 세션이 사용자 확인으로 2절 전에 올렸다(되돌리기 판 `dist-20261107-053917Z` ·
      latest 목록 30줄 · SIF 와 `.hash` 의 원격 sha256 일치 · drive-drift heax 의 web-design-agents 일치 — 그쪽 알림, WD-D87 — 포털은 보내지 않았다)
      — **11-08 업데이트 라운드** WDA 가 `c5fe4c6`(O-4 · dur_plan 결함 — wide-16x9 90 → 78초)으로 다시 올렸고 그 SIF 를 포털이 Drive 에 올렸다
      (되돌리기 판 `dist-20261107-235303Z`) · 2절은 이 판으로 돈다
- [x] 에이전트 서버 재기동(`ra_report`) — 사람 확인 뒤(남의 미반영 커밋을 같이 켠다) · 포털 재기동 · 화면 빌드 반영 — 이 가지는 하지 않는다
      — **11-07 확인** 다른 일의 재기동으로 다 섰다(에이전트 서버 11-06 06:02 KST 판에 `291bbb9` · `d590d0b` · 포털 11-06 06:10 KST · 화면 빌드 11-05)
- [x] 같은 오리진 절대경로 링크 고침(md.ts — 알림의 받기 링크가 글로 보이던 것, db0c364a 의 뜻을 마저)

## 적대 검토 두 차례 뒤(11-01 밤 — 포털 `6a1f4ce7` · 에이전트 `291bbb9` 에 대한 검토, High 없음)

고친 것마다 고치기 전 코드에서 붉은 시험(검토의 재현을 옮긴 것) · 스크래치 사본의 한 줄 변이 · WD-D 하나 · 커밋 하나.

- [x] WD-D44 `/\host` 링크도 글(md.ts — 고르기 · 검사 두 겹, 주소 안의 `\` 안 받음) · 이력 · 시험 머리 문구
- [x] WD-D45 보고서 번호는 ASCII 숫자만(`_report_id_of` — '²' 에서 중계가 터졌다)
- [x] WD-D46 he-doc-webdesign — 단추가 보일 때만 안내, 안 보이면 '아직 켜지지 않았다'
- [x] WD-D47 허브가 포털 토큰을 WDA 까지 넘긴다 — PLAN §8 알려진 허브 쪽 위험 · 허브 고침 제안(HEAXHub 는 손대지 않음) · 요청서 §6 시간
- [x] WD-D48 가짜를 진짜만큼 엄하게(WDA 4xx `{"detail"}` · code 없음 · 'Type: msg' 글, 허브 몸 없는 401 · 볼 수 없음 403 · JWKS 503 · 읽기 전용 403)
- [x] WD-D49 알림 · LLM 근거의 남의 글은 마크다운이 되지 않게(전각) · WDA · RA 거절은 정해진 글(원문은 로그) · 409 는 '이미 맡겼다'
- [x] WD-D50 권한 둘을 목록 · 진행 · advance · 받기 · 숨기기에서도
- [x] WD-D51 맡기기 · advance · 숨기기는 세션(CSRF)이나 write 범위 PAT 만 · 진짜 인증 길 시험(세션 · PAT 넷)
- [x] WD-D52 run_id '.' · '..' 거절
- [x] WD-D53 RA 본문은 흘려 받으며 상한에서 멈춤 · 받기 실패의 몸은 앞 64 KB 만
- [x] WD-D54 알림은 잡마다 정해진 메시지 id 로 한 번(`conv_store.append(msg_id=)`)
- [x] WD-D55 6시간 그물은 WDA 에 묻지 못해도(목록 · 진행 · advance)
- [x] WD-D56 만들기 잠금은 기록만 — 예약(run_id 없는 잡)으로 자리를 잡고 네트워크는 밖 · 실패하면 예약을 놓음 · 허브 토큰은 쓰기 바로 앞에서
- [x] WD-D57 만들기는 health 를 늘 새로 · 202 의 owner 가 맡긴 사람이 아니면 따라가지 않고 실패로 남김
- [x] WD-D58 만들기의 답을 잃으면 '결과 모름'(504) · 다시 누르면 같은 잡 id(Idempotency-Key) · 연결 실패만 '연결하지 못했다'
- [x] WD-D59 만들기 앞에서 끝나지 않은 잡을 그 주인 이름으로 정리(step) · 숨긴 잡도 줄이 한 걸음씩(끝 알림을 남긴다)
- [x] WD-D60 잠금은 다 쓰면 지운다
- [x] WD-D61 바뀌지 않은 잡 기록은 다시 읽지 않는다(mtime · 크기)
- [x] WD-D62 끝난 잡에도 '다시 만들기' · 지워진 파일(404 · 410)은 링크 대신 다시 만들기 · 다른 대화의 잡이면 그 대화를 말함
- [x] WD-D63 자리표시자 대화에는 화면 알림을 붙이지 않음(열 때 서버 사본)
- [x] WD-D64 두 챗 제공자 사이에 알림 신호(`hwax:deck-notice`)
- [x] WD-D65 숨은 탭은 열 배 천천히 · 창구 404 면 다시 열 때까지 묻지 않음
- [x] WD-D66 질문이 도는 대화에는 알림을 미룸(중계가 도는 턴을 센다 · 6시간 지난 턴은 세지 않음)
- [x] WD-D67 심의 결과 카드의 RA 링크 — 포털 길 `/agent/ra/reports/{번호}/open` 이 그 보고서의 공간으로 302
- [x] WD-D68 되살린 심의의 이어붙이기 실패가 결정문에 보임(에이전트 서버 `d010346`)
- [x] 요청서 §12(WDA 에 닿는 바뀐 것) · W-15 권장으로 · W-22(Authorization 을 쓰지도 남기지도 않기)
- [x] 회귀 — 포털 전체(`b23e440e`) 4,315 통과 · 29 건너뜀 · 실패 2(작업 트리에 없는 박스 파일 — ste doctor 배치 상태 · `infra/tls`, 이 가지와
      무관) · 에이전트 전체(`d010346`) 4,112 통과 · 2 건너뜀 · 화면 빌드 rc 0 · 린트 오류 0 · 경고 7(손대지 않은 파일, 그대로). 이번 판의 한 줄 변이
      69 중 65 가 붉었다 — 놓친 넷은 두 겹의 한쪽(md 링크 둘 · 뺀 출력 · 자리표시자, 둘을 함께 빼면 붉다). 생성기 전 예외 갈래(WD-D66)는 시험이 없다

## 2차 적대 검토 뒤(11-01 밤 — 위 고침에 대한 검토 · 사용자 결정 둘)

고친 것마다 고치기 전 코드에서 붉은 시험(검토의 재현을 옮긴 것) · 스크래치 사본의 한 줄 변이 · WD-D 하나 · 커밋 하나.

- [x] WD-D69 보고서 번호 글은 18자리까지(`[0-9]{1,18}` — int() 자릿수 상한)
- [x] WD-D70 `md_plain` 은 보이지 않는 글자를 범주로(Cc · Cf — U+061C · U+2060 등)
- [x] WD-D71 he-doc-webdesign — 늘 '발표자료로' 단추로(WDA 도구를 직접 몰지 않음 · 견본도 단추 안내로)
- [x] WD-D72 만들기의 잠금 밖 실패는 무엇이든 예약을 정리(RA 연결 없음 · 취소 포함)
- [x] WD-D73 결과 모름은 6시간까지 같은 키로 · 허브의 관문 502 · 503 · 504 는 결과 모름
- [x] WD-D74 만들기 앞의 정리는 내 잡만 내 토큰으로 · 박스 상한은 남의 잡을 어림(갓 맡김 15분 · 주인이 본 지 5분) · 요청 W-23
- [x] WD-D75 질문이 도는 대화에서도 끝(파일 · 링크 · 상한)은 곧바로 적고 대화 알림만 미룸(`notice_pending` — 칸은 멈추고 줄이 남긴다)
- [x] WD-D76 도는 턴은 사용자 발화를 남기기 전에 셈 · 남기지 못하면 곧바로 뺌 · 낡은 턴은 걷음
- [x] WD-D77 받기는 WDA 가 낸 답만 — 지워짐은 WDA 봉투(W-10)의 404 · 410 만, 흘리기 전에 꼴(media type)과 앞 바이트(zip PK · %PDF · mp4 ftyp ·
      html 은 attachment 머리)를 봄
- [x] WD-D78 심의 결과 카드는 RA 가 준 주소로 바로(에이전트 `d590d0b` 가 outcome 에 url) · 옛 카드는 화면이 apiFetch 로 물어서 · `/open` 은 JSON · 앞 64 KB
- [x] WD-D79 상류가 끝난 직후 브라우저가 떠나도 답을 남김(중계의 finishing 표지 — 있던 결함, 사용자 결정 11-01)
- [x] WD-D80 같은 오리진의 세션 쿠키가 WDA 까지 가는 것 — PLAN §8 에 기록만(사용자 결정 11-01)
- [x] WDA 의 셋째 답(11-01 밤 — W-1 ~ W-15 · W-22 로컬 판 · 렌더 building · 보존은 끈 채로, 사용자 결정) — 요청서 §10 · §11 · §12, 가짜 WDA 를 맞춤
- [x] 회귀 — 포털 전체(`ab7edbf3`) 4,375 통과 · 29 건너뜀 · 실패 2(작업 트리에 없는 박스 파일 — ste doctor 배치 상태 · `infra/tls`, 앞 판과 같은 둘) ·
      에이전트 전체(`d590d0b`) 4,126 통과 · 2 건너뜀 · 화면 빌드 rc 0 · 린트 오류 0 · 경고 7(손대지 않은 파일, 그대로) · 중계 · 챗 시험 묶음과 멈춤 ·
      끊김 브라우저 시험 486 통과(WD-D79). 2차 고침의 한 줄 변이 56 중 55 가 붉었다(포털 51 중 50 · 에이전트 5 중 5) — 놓친 하나는 두 겹의 한쪽
      (WD-D74 정리의 '내 잡만' — `step` 이 기록의 주인을 다시 본다)

## 3차 적대 검토 뒤(11-01 밤 — main `e24f510f` · 에이전트 `9f08507` 에 들어간 판, 낮음 넷)

고친 것마다 고치기 전 코드에서 붉은 시험 · 스크래치 사본의 한 줄 변이 · WD-D 하나 · 커밋 하나. 가지를 main 으로 빨리 감은 뒤 이어서 고쳤다.

- [x] WD-D81 끝맺는 pump 를 기다리는 데 상한 120초(`_wait_pump` — 넘기면 크게 남기고 응답을 닫되 저장은 뒤에서 끝까지 · 늦게 끝난 것도 남김)
- [x] WD-D82 남의 대화는 주인부터 보고(`owner_state`) 도는 턴으로 세지 않음 · 내 대화만 턴을 센 뒤 발화를 남김
- [x] WD-D83 루틴 턴의 상한 로그는 실제로 끊을 때만(끝맺는 중이면 남기지 않음)
- [x] WD-D84 팝업이 막히면 옛 카드는 링크대로 RA 첫 화면(진짜 링크 · 빈 탭을 열었을 때만 기본 이동을 막음)
- [x] 회귀 — 중계 · 챗 묶음과 멈춤 · 끊김 브라우저 시험 660 통과 · 포털 전체(`0db3c47c`) 4,440 통과 · 29 건너뜀 · 실패 2(작업 트리에 없는
      박스 파일 — ste doctor · `infra/tls`, 앞 판과 같은 둘) · 화면 빌드 rc 0 · 린트 오류 0 · 경고 7 그대로(에이전트는 바뀌지 않아 돌리지 않았다).
      한 줄 변이 14 중 14 가 붉었다(D81 다섯 · D82 셋 · D83 둘 · D84 넷). 중간에 WD-D82 의 긴 주석이 고른 전문가 시험(소스 거리 단언)을
      붉혀 주석을 줄였다(`0db3c47c`)

## M2

- [x] 분석 루틴 RA 초안 자리(`routine.report.ra_report_id`) — **11-21 지음**(포털 `wt1121/deck` `8c7eb85d` · `8deb28a3`). `deckReportOf` 가 그 칸을 읽고
      루틴 칸(RoutineView)의 RA 초안 줄 아래에 원장과 맞댄 초안 번호로 단추가 선다(끼움 자리 `raExtra` — 루틴 칸은 발표자료 모듈을 끌어오지 않는다) ·
      심의 보고서와 같은 문(심의 꼴이 active 일 때만 — WD-D89)
- [ ] RA 그림 함께 보내기(WDA W-16 뒤 — 포털이 그 사람 명의로 `GET /api/files/{id}`) — W-16(파일을 같이 받는 꼴)이 아직 정해지지 않았다
- [x] 다시 시도(WDA resume) · WDA 지우기(W-17) · PDF 미리보기(CSP sandbox) · MCP 쪽 주인(W-18 · 게이트웨이 `per_user_sso.web_design_agents`)
      — **11-21 지음**(가지 `wt1121/deck` — 올리지 않음). 갈래마다 아래.
  - [x] 다시 시도 — 포털 `27aac38d`(`POST /agent/deck/jobs/{job}/retry` — 같은 WDA 실행 · 새 포털 잡) · 화면 `400edfb5` · WDA `19dc123`(재개는 받은
        자리에서 running). WD-D90
  - [x] 지우기 — WDA `7664a70`(`DELETE /api/runs/{id}` — 주인만 · 묘비 · 도는 중 409) · 포털 `27aac38d`(`DELETE /agent/deck/jobs/{job}`) · 화면
        `400edfb5`. WD-D92
  - [x] PDF 미리보기 — 포털 `27aac38d`(`GET /agent/deck/jobs/{job}/preview` — inline · `Content-Security-Policy: sandbox; frame-ancestors 'self'`) ·
        화면 `400edfb5`(틀에 sandbox 속성 없음 — Chromium 148 실측). WD-D91
  - [x] MCP 쪽 주인의 WDA 쪽 — WDA `28d7c69`(`POST /api/auth/sso` · 단언 `wdsso_` · 확인된 주인에게만) · 게이트웨이 설정 예시 · 차례는 문서만
        (HWAXMcpGateway `a1b6e08` — 코드 변경 없음). WD-D93
  - [ ] MCP 쪽 주인 켜기 — **사람**(박스의 `secrets.env` · `gateway_config.json` · 게이트웨이 재기동 — server-setup.md 4절). 기본 꺼짐
- [ ] 화면의 진짜 브라우저 확인 — PDF 미리보기가 Chrome · Edge · Firefox 에서 서는지(이 박스의 Chromium 148 새 헤드리스에서만 재 봤다 — WD-D91)

### M2 를 지으며(11-21 — 포털 `wt1121/deck` · WDA `wt1121/deck` · 게이트웨이 `wt1121/deck`)

- [x] 먼저 실패하는 시험 — 루틴 자리(node 순수 함수) · 포털 창구 열일곱(가짜 WDA 에 재개 · 지우기를 진짜 꼴로) · WDA 그림 넷 · 지우기 열여덟 · 위임 열여섯.
      브라우저 시나리오 다섯(루틴 칸 · 끝난 잡의 도구 · 지우기 없는 판과 거절 · 다시 시도 · 알림 아래)은 지은 뒤에 쓰고 변이로 붉어지는지 봤다
- [x] 변이 — WDA 서비스 자격 건너뛰기 둘 · 지우기 여섯(주인 두 겹은 한 겹씩 빼면 한쪽이 막는다 · 둘 다 빼면 실기동 시험까지 붉다) · 위임 열 ·
      포털 창구 열하나(주인 · 스위치 · 권한 · 쓰기 범위 · 머리 · 거절을 삼킴 · 꺼진 박스의 status 꼴) · 화면 일곱(루틴 문 셋 · 스위치 · sandbox 속성 ·
      지우기 능력 · 미리보기 물음). 서른여섯 가운데 서른다섯이 붉었다(남은 하나는 두 겹의 한쪽)
- [x] 회귀 — WDA 2 실패 · 2,949 통과(기준선의 같은 둘 · 새 실패 0) · 게이트웨이 1,112 통과 · 포털 5 실패 · 5,132 통과(종전의 셋 + 이 가지와 무관한 둘 —
      부하 탓의 시간 초과 하나 · 형제 에이전트 서버 본 가지가 회귀 도중 앞으로 나간 계약 시험 하나, 병합하면 사라진다). 까닭과 수치는 context-notes WD-D95.
      첫 전체 회귀가 루틴 화면 시험 열넷을 붉혔다(루틴 칸이 발표자료 모듈을 끌어왔다) — `8deb28a3` 로 엮임을 풀고 다시 돌렸다
- [ ] dev 실주행 — 하지 않았다(dev 에는 RA 가 없다 — WD-D88). cae00 에서 server-setup.md 4절

### 11-22 사용자 결정 둘(같은 가지 `wt1121/deck` — 포털 · WDA, 올리지 않음)

- [x] ① 실물 꼴의 심의 보고서 — 포털이 그 사람 명의로 RA 템플릿 스키마를 읽어 `template_schemas` 로 싣는다(선택지 (나)) — 포털 `547b98fc`
      (`templates_needed` · `read_template_schemas` · WDA 판 문 · status 의 심의 자리) · WDA `56bb9e9`(스키마로 블록 풀기 · 긴 글 items 꼴 · 라벨 단락 ·
      저장과 재개). 못 읽으면 정해진 글(권한 403 · 없음 409 · 불통 502) · 서비스 자격 없음 · WDA 를 부르지 않는다. WD-D96
- [x] ② WDA 회의 · ingest 도구의 주인 — 웹 길이 신원을 넘기고 회의에 주인 칸(선택지 (나)) — WDA `4c25b08` · `1da9733`. 11-21 탐침이 막힌다 ·
      주인이 자기 실행으로 회의를 여는 길이 열린다 · 실기동(`--root-path` 두 조건). WD-D97
- [x] ③ 내 실행 목록 도구(짓지 않음) · ④ PDF 미리보기 격리(지금대로 + '받기' 안내) — 닫힌 기본값 그대로
- [x] 시험 먼저 · 변이 — 포털 여덟 · WDA 열다섯(두 살아 하나는 시험을 강화해 붉혔고 하나는 같은 동작의 변이) · 회귀 수치는 WD-D98
- [ ] 배치본 확인(사람 — server-setup.md 5절) — 실물 심의 보고서 하나가 '보고서 읽기' 를 지나는지 · WDA 콘솔에서 주인 있는 실행으로 회의를 열 수 있는지

## M3 — cae00(사람 몫 — server-setup 은 M1 끝에 쓴다)

- [ ] WDA SIF 가 W-1 ~ W-12 판인지(`/api/health` features) · (U-3 이면) 익명 401
- [ ] 박스 스위치 `wda_deck_enabled` 켜기 · 포털 재기동 — 11-08 사용자 결정으로 cae00 에서 2절까지(받은 편지함 2026-11-08 Q4, WD-D88 — dev 에는 RA 가 없어 못 한다)
- [ ] 쓸 사람의 허브 계정(허브 타일 한 번) · 실제 보고서 하나로 확인
- [ ] (11-22 M3 판을 받은 뒤) WDA SIF 가 `template_schemas` 판인지(health features) · 심의 결과 카드 · `/보고서` · 루틴 초안의 '발표자료로' 가 끝까지
      가는지 — server-setup.md 5절
- [ ] (11-21 M2 판을 받은 뒤) WDA SIF 가 M2 판인지(`/api/health` features 에 `delete`) · 끝난 잡에서 PDF 미리보기 · 사본 지우기 · 실패한 잡에서 다시 시도 —
      server-setup.md 4절
- [ ] (선택) MCP 쪽 주인 켜기 — WDA `secrets.env` 의 `WDA_GATEWAY_SECRET` · 게이트웨이 `per_user_sso.web_design_agents` · 게이트웨이 재기동
