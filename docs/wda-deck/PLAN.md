# 발표자료로 — 포털이 만든 RA 보고서를 WebDesignAgents 로 PPT · PDF 만들기 — 계획 (2026-11-01)

> 체크리스트 [checklist.md](checklist.md) · 결정과 까닭 [context-notes.md](context-notes.md) · WDA 세션에 그대로 보낼 요청서 [wda-request.md](wda-request.md).
> 설계는 11-01 오전에 끝났고, 같은 날 사용자가 §13 의 다섯을 모두 정했다(권장안 그대로 — U-2 는 사용자가 손으로 push).
> M1(포털 · 에이전트 서버 한 칸)은 이 가지에서 짓는다. WDA 쪽 계약(W-1 ~ W-12)은 아직 없으니 단추는 스위치와 능력 탐침에 막혀 보이지 않는다.
> 줄 번호는 2026-11-01 판 기준이다 — 포털 `7aef6141` · WDA `9dabf86` · 게이트웨이 `63fbc4f` · HEAXHub `7b9a8ed` · 에이전트 서버 `63ad54b`.

## 1. 무엇을 · 왜

WDA(WebDesignAgents) 세션이 포털에 '발표자료' 행선지를 청했다 — 포털 심의 → Report Archive(RA) 보고서 → WDA → 영상 · PPT · 문서 → 다시 포털 챗.
사용자 결정(2026-11-01) 둘로 꼴이 정해졌다.

1. **포털이 맡고 알린다.** 포털이 만든 RA 보고서 옆에 '발표자료로' 단추를 둔다. 포털이 그 보고서를 **그 사람 명의로** 읽어 본문을 WDA 에
   넘기고(요청 R2 (나)), 잡 기록(누가 맡겼나)을 남기고, 화면이 진행을 보이고, 끝나면 그 대화에 받기 링크가 든 알림을 남긴다. DocForge 배달
   (`backend/app/agent/docforge_delivery.py` 와 그 라우트)과 같은 꼴이다. 챗 LLM 은 잡을 폴링하지 않는다(HA-28, `docs/request_261030.md:33`).
2. **기본 출력은 PPT + PDF**(`pptx_mode` hybrid). 영상 · HTML · Word 는 단추에서 고를 수 있다.

이 설계가 더한 것 셋 — ① **WDA 에는 주인이 없다**(§2.4) — 남의 보고서 본문이 새지 않게 WDA 의 주인 기능을 단추를 켜는 전제로 둔다(§13 U-1).
② **포털이 모든 것을 중계한다** — 브라우저는 WDA 의 run_id · job_id · 주소를 보지 않는다. ③ 상태 낱말을 하나로 정한다(§7.2).

## 2. 조사로 확인한 사실

### 2.1 따라 할 꼴 — DocForge 배달

- 잡 기록은 스테이징 아래 `#docforge-jobs/<잡>.json` 이다(0600 · 임시 파일을 바꿔 끼운다) — `backend/app/agent/docforge_delivery.py:33,46-58,61-66`.
  스테이징 청소(6시간)에서 빠지고 `docforge_job_days`(7) 뒤에 지운다 — `backend/app/agent/upload.py:262-272`, `backend/app/config.py:299`.
- **주인만** — 남의 것과 없는 것을 같은 404 로 답한다(있는지도 알리지 않는다) — `docforge_delivery.py:69-78`. 진행 · 배달 · 글 · 취소 · 숨기기
  라우트가 모두 이것을 먼저 부른다 — `backend/app/agent/routes.py:2013,2036,2086,2113,2162`.
- **세션 + CSRF 또는 PAT** — `principal_pat_or_session` 은 Bearer PAT 이면 검증하고, 쿠키면 GET 밖의 요청에 이중 제출 CSRF 를 건다 —
  `backend/app/deps.py:106-118,121-150`. 화면의 `apiFetch` 가 GET 밖의 요청에 `X-CSRF-Token` 을 싣는다 — `frontend/src/api/client.ts:39-44`.
- **한 번만** — 잡마다 `asyncio.Lock`(`docforge_delivery.py:36,108-109`) 안에서 기록을 다시 읽고 `delivered` 가 있으면 그것을 돌려준다 —
  `routes.py:2041-2044`. 넣은 뒤 기록에 남긴다 — `routes.py:2070`.
- **화면이 몬다** — 1.5초마다 진행을 보고(`frontend/src/components/chat/DocDispatchPanel.tsx:46,82-139`) 끝나면 deliver 를 부른다
  (`DocDispatchPanel.tsx:105-113`). 포털 뒤에서 기다리는 일감은 없다(DF-D17 ③, `docs/doc-to-ra/context-notes.md:85-97`). 창을 닫은 잡은
  입력창 위 '끝나지 않은 정밀 변환' 줄로 다시 연다 — `routes.py:2123-2151`, `frontend/src/components/chat/DocforgeResume.tsx:24-64`(DF-D23).
- **보낸 결과를 대화에 남기기**(PP-D3, `docs/chat-ppt/context-notes.md:23-34`) — 화면이 글 + 활동 하나(`origin: 'upload'`)를 지어
  (`frontend/src/components/chat/uploadNotice.ts:84-105`) `addUploadNotice` 로 **지금 대화**에 붙이고 서버 사본에 `meta {activity, upload: true}` 로
  덧붙인다 — `frontend/src/state/ChatContext.tsx:678-722`(711). 다음 턴 이력은 그 활동을 `kind: 'upload'` 근거로 싣는다 —
  `frontend/src/components/chat/history.ts:43`, 포털 모델 `routes.py:91-100`.
- 관찰(고치지 않음) — 포털 주석은 'DocForge 쪽 주인 검사도 한 번 더 걸린다' 라 적었지만(`routes.py:1997-1999`), 게이트웨이 경유 호출은 허브
  서비스 토큰의 주인으로 접혀 DocForge 에 닿는다 — DocForge 스스로 'MCP 길은 기본이 서비스 계정 명의' 라 적었다(DocForge
  `docforge/identity.py:5-8,40-48`). 사람별로 실제로 막는 것은 포털 기록뿐이다(코드 읽기로 낸 판단이다 — 실측은 하지 않았다).

### 2.2 포털이 만든 RA 보고서가 화면에 나오는 자리

| 자리 | 보고서 번호가 어디 있나 | 새로고침 뒤에도 남나 |
|---|---|---|
| 심의 결과 카드 | SSE `delib` kind=outcome 의 `report_id` → `delib.outcome`(`ChatContext.tsx:268-275`) → `DelibView.tsx:284-299` 의 Report Archive 카드 | **아니다.** 중계가 outcome 을 서버 사본에 남기지 않는다(`routes.py:2854-2895` 는 turn · decision · cancelled · evidence 만) — 화면도 그렇다고 적었다(`DelibView.tsx:43,48`) |
| `/보고서` · `/보고서 정리` 저장 답 | 에이전트 서버가 **글로만** 낸다 — `📄 Report Archive 보고서 #{rid} 로 저장했습니다`(HWAXAgentServer `deliberation.py:7904,7913-7914`, 갈래 `app.py:7788-7791`) | 글은 남지만 구조화된 번호가 없다 — 글을 파싱하지 않는다(§5) |
| RA 보내기 알림(PPT 가져오기 · 정밀 변환) | 알림 활동의 `result_full` JSON 에 `report_id`(`uploadNotice.ts:68-105`) | 남는다 — `meta.activity` 로 서버 사본에 있다 |
| 분석 루틴의 RA 초안 | `routine.report.ra_report_id`(`frontend/src/types/chat.ts:243`) | 남는다 — M2 |

- 심의 · `/보고서` 의 RA 저장은 에이전트 서버가 그 사람의 챗 PAT 로 게이트웨이 `create_report_draft` 를 부른다 — 게이트웨이는 RA 를 사람별 자격으로만
  부른다(`HWAXMcpGateway gateway.py:6777-6790`, 등록 연결 · 위임). 그래서 그 보고서는 그 사람의 것이다.
- 관찰(고치지 않음) — 심의 결과 카드의 링크가 `/report-archive/w/dev/reports/{id}` 로 공간 이름을 박았다(`DelibView.tsx:292`). 다른 공간의 보고서는
  RA 가 다른 곳으로 보낼 수 있다.

### 2.3 포털이 RA 를 그 사람 명의로 읽는 길

- `_ra_user_token` — RA 위임(ste 방식, `RA_SSO_SECRET`)이 있으면 그 자리에서 받고, 없으면 '외부 연결' 에 등록한 그 사람의 토큰. 둘 다 없으면
  고칠 곳을 말한다 — `routes.py:1557-1578`. 위임 토큰이 401 이면 한 번만 새로 받는다(`backend/app/auth/ra_sso.py` · `routes.py:2054-2058`).
  서비스 계정으로 내려가는 길은 없다 — RA 글이 남의 개인함으로 가던 사고(2026-09-29, 게이트웨이 `gateway.py:6777-6783` 주석)의 교훈이다.
- 읽기는 RA `GET /api/reports/{id}` 이다 — `can_read_report` 가 아니면 403 'Out of workspace scope'(ReportArchive
  `backend/app/modules/reports/routes.py:1893-1904`). 가시성은 그 사람 기준으로 다시 본다 — 어느 `X-Workspace-Slug` 를 보내도 그 사람이 볼 수 있는
  보고서만 읽힌다(ReportArchive `backend/app/modules/reports/services.py:317-333`). 그래서 포털은 '포털이 만든 보고서인가' 를 따로 검사하지 않는다 —
  단추의 자리는 화면의 일이고, 막는 것은 RA 의 읽기 권한이다.
- WDA 는 RA REST 응답(`{success, data}` 봉투 또는 `GET /api/reports/{id}` 의 ReportRead)을 그대로 받는다 — WDA `src/wdpipeline/ingest.py:9-25`.

### 2.4 WDA 의 지금 상태

- **주인이 없다.** 웹 실행 원장 `data/web_runs/{run_id}.json` 에 주인 칸이 없고(WDA `src/wdweb/runs.py:155-169`), `GET /api/runs` 는 전부를
  돌려준다(`src/wdweb/app.py:170-172`, `runs.py:114-122`). 실행 · 산출물 · 내려받기 · 미리보기 라우트는 id 만 보고 경로 탈출만 막는다 —
  `app.py:175-177,408-434,437-444,464-492`. MCP 의 run_id 와 웹 run_id 는 같은 `pipeline/` 아래라 MCP 도구도 웹 실행에 닿는다
  (`src/wdmcp/server.py:202-207`).
- **익명으로 닿는다.** 허브 매니페스트가 `status: stable` · `visibility: company` 이고 `launch.portal_auth` 가 없다(HEAXHub
  `integrations/web-design-agents/.portal/manifest.yaml:9,46-50,75-76`). 허브 게이트는 company + stable 이고 portal_auth 가 아닌 앱을 **토큰 없이**
  통과시킨다(HEAXHub `backend/app/api/v1/authz.py:83-99,138-146`). dev 실측(11-01) — 포털 nginx 를 거친 `/apps/web_design_agents/api/health` 와
  `/api/runs` 가 로그인 없이 200 이었다(배치된 인스턴스의 실행은 0건이었다). 포털 nginx 는 `/apps/` 를 허브 Caddy 로 넘긴다 —
  `backend/config/routes.env:41`, `infra/scripts/gen-nginx-conf.sh:22-26`. 곧 **WDA 에 넣은 보고서는 지금 그대로라면 사내 누구나 받는다.**
- **신원.** MCP 는 `x-hwax-user` 머리를 세션 칸 나누기에만 쓴다(권한 판정 아님) — `src/wdmcp/session.py:159-191`. 그런데 게이트웨이는 WDA 에
  그 머리를 싣지 않는다 — 호출마다 신원을 싣는 것은 `IDENTITY_FWD_BACKENDS`(기본 `hwax-deliberation` 하나, 떠 있는 dev 게이트웨이 환경에도 따로
  없다)와 `per_user_sso`(dev 는 hwax_risk · kooremapper_mcp · mx-white-paper · ste)뿐이다 — `HWAXMcpGateway gateway.py:6336-6343,6856-6870,361`.
  나머지 허브 앱은 상주 세션 하나로 허브 서비스 토큰을 실어 Caddy 를 지난다(`gateway.py:1446-1448,1474`) — Caddy 는 `X-Heax-User-Email` 을 그 토큰의
  주인(허브 첫 관리자)으로 싣는다(`gateway.py:273-278`, HWAXRisk `backend/app/routes.py:444-449`). 또 Caddy 가 지우는 위조 머리는
  `X-Heax-User-Email` · `X-Heax-User-Name` 둘뿐이라(HEAXHub `backend/app/services/proxy_manager.py:45,70-94`, 게이트웨이 경고 `gateway.py:259-262`)
  `x-hwax-user` 는 자기 PAT 로 `/apps/web_design_agents/mcp` 에 직접 붙은 누구나 적어 보낼 수 있다. 웹 REST 는 신원을 아예 읽지 않는다.
- **배치가 낡았다.** 허브가 띄우는 SIF 는 GitHub 에서 짓는다(manifest `source` `:70-73`). 허브의 `web-design-agents.sif` 는 2026-08-19 판이고
  WDA 로컬 main 은 origin/main 보다 68 커밋 앞선다(11-01 실측 — 계속 는다). push 는 GitHub 이 거절했다 — 역사에 `.github/workflows/ci.yml` 을 만드는
  커밋(08-28 `e4dc40e` · 10-24 `8d5a453`)이 있는데 dev 토큰에 workflow 범위가 없다(WDA 세션 전언). origin/main 의 렌더 출력은 `("video", "pptx")`
  뿐이고 `pdf` · `doc_style` · `pptx_mode` · `resume` 이 없다(`git show origin/main:src/wdweb/runs.py:19`). **사용자 결정 2(PPT + PDF)는 지금 배치에서
  돌지 않는다.**
- **게이트웨이에 실린 도구는 16개다**(dev `/tools-map` 실측 — meeting_* 6 · report_ingest · report_fragmentize · scenario_build · scenario_patch ·
  render_submit · render_status · qa_run · scene_list · scene_html · scene_still). 소스의 23개와 다르다 — 도구는 소스가 아니라 게이트웨이로 대조한다
  (`docs/gotchas.md` 7).
- **본문을 문자열로 받는 MCP 도구가 없다.** `report_ingest(file)` 은 서버 파일 경로만 받는다(`Path(file).is_file()` — `server.py:776-792`).
  본문을 받는 것은 웹 REST `POST /api/runs {report_json, slug}`(JSON 또는 multipart 파일)뿐이다 — `app.py:133-167`. WDA 세션이 R2 (나)로 이 길을
  받아들였다.
- **PDF 는 슬라이드 PDF 가 아니다.** WDA 의 pdf · html · docx 는 같은 심의에서 나온 '읽는 문서'(본문 = 내레이션, 삽화 = 장면 스틸)를 조판한 것이고
  꼴은 `doc_style` report · brief · memo 다 — `src/wdrender/exporter_doc.py:1`, `src/wdpipeline/document.py:520-533`, `src/wdmcp/schemas.py:365-367`.
- **요청한 출력을 조용히 뺀다.** 장면 꼴(wide-16x9 의 outputs 는 `[video, pptx]` — `formats/wide-16x9/format.yaml:18`)이 내지 않는 출력은 말없이
  거른다 — `runs.py:366-367`.
- **취소가 없고, 재기동에 끊긴 실행은 running 으로 남는다.** 파이프라인 · 렌더가 데몬 스레드라(`runs.py:172-176,283-288`) 재기동하면 원장은
  running 인 채이고, 재개는 running 을 거절한다(`runs.py:303-304`).
- **그림.** RA 보고서의 file_id 그림은 WDA 가 `WDA_RA_*` **서비스 자격**이 있을 때만 받는다(`src/wdpipeline/assets.py:92-121`). 사람 명의 원칙과
  맞지 않으니 포털 길에서는 쓰지 않는다(§10 · M2).

- **WDA 세션의 답(11-01)** — W-1 ~ W-12 는 지금 하나도 없다(사용자가 직접 시킬 때만 짓는다 — 포털은 요청서의 계약대로 짓고 시험의 가짜 WDA 가
  그것을 따른다). 심의(`deliberation` 템플릿) 보고서는 장면이 제품 소개 뼈대로 눌려 결정문 · 액션아이템이 사라진다 — 심의 꼴을 다음 일로 짓고
  `format:deliberation` 으로 알린다(W-21). wide-16x9 에서 pptx · pdf 가 둘 다 나온다. 시간은 파이프라인 0.5초 + 렌더(pptx + pdf) 5.0초 = 5.5초,
  크기는 pptx 1,200 KB · pdf 1,926 KB. **보존이 없고(실행 60건에 372 MB) 동시 상한이 없다(요청마다 스레드)** — W-13 · W-14 를 강하게 권했다.
- 템플릿 — 심의 결과 카드와 `/보고서` 저장 답의 보고서는 `deliberation` 템플릿이고(에이전트 서버 `deliberation.py:7631,7892`), RA 보내기 알림의 보고서는
  `__import_blank__` 다. `deliberation` 보고서는 블록 정의를 보고서에 싣지 않는다(타입은 RA 템플릿 스키마 — ReportArchive
  `modules/reports/routes.py:677-722`) — WDA 의 지금 ingest 는 정의 없는 content 키를 건너뛴다(`ingest.py:407-442`).

### 2.5 단추를 막을 권한 키

`plat:webdesign` 이 이미 있다 — 플랫폼 `webdesign` · 게이트웨이 `heax-web_design_agents`(`backend/config/access.yaml:147-149`). RA 읽기는
`plat:reportarchive`(`access.yaml:76-79`). 백엔드는 `ensure` 로 다시 본다(`deps.py:86-93`). 새 키는 만들지 않는다.

## 3. 흐름

1. 사람이 RA 보고서 옆 '발표자료로' 를 누른다 — 작은 창에서 출력(PPT ✓ · PDF ✓ · Word · HTML · 영상)과 문서 꼴(정식 보고서 · 요약 2~3쪽 · 1쪽 메모 —
   PDF · Word · HTML 을 고를 때만)을 고르고 '만들기'.
2. 화면 → 포털 `POST /agent/deck/jobs {report_id, conversation_id, targets, doc_style}`(세션 + CSRF).
3. 포털이 막는다 — 권한 둘 · 박스 스위치 · WDA 능력(주인 기능) · 그 대화가 그 사람 것인가 · 같은 보고서 같은 옵션의 잡이 이미 도는가(그 잡을 준다) ·
   사람당 동시 상한.
4. 포털이 RA `GET /api/reports/{id}` 를 그 사람 토큰으로 읽는다(위임 401 이면 한 번 새로). 403 · 404 면 WDA 를 부르지 않고 실패로 말한다. 본문이 상한(16MB)을
   넘어도 부르지 않는다. 보고서의 그림(file_id) 수를 센다(M1 은 싣지 않는다 — 알림에 말한다).
5. 포털이 그 사람 이름으로 짧은 포털 PAT(청중 `heax-hub`, 10분)을 찍어 **허브 Caddy 를 거쳐** WDA `POST /api/runs` 를 부른다 — 본문 · slug ·
   출처 · 렌더 옵션(WDA 가 빌드 뒤 이어서 렌더 — 요청 W-8). 허브 게이트가 PAT 를 검증해 허브 사용자로 잇고(HEAXHub `authz.py:61-74,148-168`),
   Caddy 가 `X-Heax-User-Email` 을 그 사람으로 싣는다(`proxy_manager.py:70-94,162`). WDA 는 그 값을 run 의 주인으로 적는다(W-1).
6. 포털이 잡 기록을 남긴다(주인 · 대화 · 보고서 · 옵션 · WDA run_id — run_id 는 서버에만) → 화면에 포털 잡 id 만 준다.
7. 화면이 3초마다 `GET /agent/deck/jobs/{job}` — 포털이 그 사람 이름으로 WDA `GET /api/runs/{run_id}` 를 보고 하나의 낱말로 옮긴다(§7.2). 창을 닫아도
   WDA 는 돈다. 다시 오면 입력창 위 '끝나지 않은 발표자료 N건' 줄이 이어 본다.
8. WDA 가 끝(done · failed)을 말하면 화면이 `POST …/advance` 를 부른다 — 포털이 잡 잠금 안에서 산출물을 확인하고(요청한 것 ⊆ 만든 것, 크기) **단추를 누른 그
   대화**의 서버 사본에 알림 한 건을 남긴다(한 번만). 화면은 받은 알림을 그 대화의 화면 사본에만 붙인다. (WDA 가 이어서 렌더하지 않는 판이면 빌드 끝에
   `advance` 가 렌더를 한 번 맡긴다.)
9. 사람이 알림의 링크를 누르면 `GET /agent/deck/jobs/{job}/files/{kind}` — 포털이 기록의 주인을 보고 그 사람 이름으로 WDA 에서 받아 그대로 흘린다
   (attachment). 다음 턴 이력은 알림의 근거(`kind: upload`)로 '발표자료를 만들었다' 를 안다.

## 4. 포털이 부를 계약(요약 — 정본은 [wda-request.md](wda-request.md) §4)

| 무엇 | WDA(허브 Caddy 경유, 그 사람의 짧은 포털 PAT) | 주인 |
|---|---|---|
| 만들기 | `POST /api/runs {report_json, slug, source, render{targets, doc_style, pptx_mode, narration:false}}` → 202 `{run_id}` | 만든 사람(`X-Heax-User-Email`) |
| 진행 | `GET /api/runs/{run_id}` → `status` · `stages[]` · `render{status, requested, outputs, skipped, error}` | 주인만, 아니면 404 |
| 렌더(이어서 렌더가 없는 판) | `POST /api/runs/{run_id}/render {targets, doc_style, pptx_mode}` → 202 · 409 | 주인만 |
| 크기 | `GET /api/runs/{run_id}/artifacts` | 주인만 |
| 받기 | `GET /api/runs/{run_id}/download/{kind}`(kind pptx · pdf · docx · html · mp4) → 파일 | 주인만, attachment |
| 능력 | `GET /api/health` → `{status, version, features[]}` — `owner` 가 있어야 단추를 켠다 | 누구나 |

포털 쪽 라우트(`/agent/deck/…`) — `GET status` · `POST jobs` · `GET jobs` · `GET jobs/{job}` · `POST jobs/{job}/advance` · `GET jobs/{job}/files/{kind}` ·
`POST jobs/{job}/dismiss`. 모두 `principal_pat_or_session`(POST 는 CSRF) · 잡은 주인만(아니면 404).

## 5. 화면 자리

- **심의 결과 카드**(`DelibView.tsx:284-299`) — Report Archive 카드 옆에 '발표자료로'. 새로고침 뒤에도 살게 중계가 outcome 의 `report_id` · `title` 을
  답 meta `delib_outcome` 으로 남기고(`routes.py:2854-2895,3030-3039` 곁), `serverMessagesToLocal`(`frontend/src/api/conversations.api.ts:95-`)이
  `delib.outcome` 으로 되살린다. 지금은 새로고침하면 보고서 단계와 카드가 사라진다(`DelibView.tsx:43,48`) — 이 고침이 그것도 바로잡는다.
- **`/보고서` 저장 답** — 에이전트 서버 `run_report_save` 의 `result` 사건에 `ra_report: {id, title}` 칸을 더하고(HWAXAgentServer `deliberation.py:7913-7914`),
  중계가 답 meta `ra_report` 로 남긴다(`routes.py:2850-2851` 곁). 화면은 그 meta 가 있는 답의 행동 줄(복사 · 위키 옆, `MessageList.tsx:61-96`)에 단추를 둔다.
  글을 파싱하지 않는다 — 글은 바뀐다.
- **RA 보내기 알림** — 활동이 `origin: 'upload'` 이고 도구가 `create_report_draft` · `docforge_convert` 인 알림의 `result_full.report_id`.
- 단추 하나를 셋이 같이 쓴다(`DeckButton` — 보고서 번호 · 제목 · 그 대화의 서버 id). 진행은 그 메시지 아래 작은 칸에, 창을 닫은 잡은 입력창 위 줄
  (`DocforgeResume` 꼴)에 보인다.
- **넣지 않는 자리** — `DocActions`(붙인 문서에 지시문을 채우는 선택지, `DocActions.tsx:27-38,155-209`)와 `destApps.ts`(그 선택지의 '지금 전문가' 순서표,
  `destApps.ts:1-26`). 까닭은 context-notes WD-D13.

## 6. 권한과 켜기 조건

- 단추 · 라우트 둘 다 `plat:webdesign` **와** `plat:reportarchive`. 화면 숨김은 편의이고 백엔드가 `ensure` 로 다시 본다.
- **박스 스위치** `wda_deck_enabled`(기본 꺼짐) — WDA 의 주인 기능이 배치된 박스에서 사람이 켠다.
- **능력 탐침** — `GET /agent/deck/status` 가 WDA `/api/health` 의 `features` 에 `owner` 가 있는지 본다(60초 붙잡음). 없거나 **모르면 숨긴다** —
  모르는 채로 보이면 주인 없는 WDA(옛 SIF 로 되돌린 박스)에 본문을 넘기게 된다. DocForge 목적지의 '모르면 숨기지 않는다'(DF-D21 ②)와 반대인 까닭은
  위험의 종류가 다르기 때문이다(그쪽은 실패, 이쪽은 누출).
- **템플릿 문(W-21)** — RA 보고서의 템플릿 가운데 하나라도 `deliberation` 이면 `owner` 에 더해 `format:deliberation` 이 있어야 한다. 화면은 자리마다
  템플릿을 안다(심의 결과 카드 · `/보고서` = deliberation, RA 보내기 알림 = 그 밖) — `status` 가 `formats.deliberation` 을 알려 주고, 만들기는 RA 에서 읽은
  실제 템플릿으로 다시 본다(아니면 409 와 까닭). 사용자에게 '심의 결과 카드 단추를 W-21 전까지 둘지' 를 묻는 중이다(U-6) — 문은 어느 쪽이든 짓는다.
- 허브 계정 — 허브 게이트는 포털 PAT 의 이메일로 허브 사용자를 찾고, 없으면 403 '허브 계정이 없다 — 포털에서 HEAX Hub 타일을 한 번 눌러…' 를 낸다
  (HEAXHub `authz.py:61-74`). 포털은 그 글을 그대로 보인다. 허브 타일이 보이는 사람은 화면이 미리 로그인해 계정이 생긴다
  (`frontend/src/components/layout/SsoPrimer.tsx:7`, `backend/app/auth/routes/launch.py:24`).

## 7. 잡 기록과 수명

### 7.1 기록

`<upload_staging_dir>/#deck-jobs/<job_id>.json`(0600 · 바꿔 끼우기 · 스테이징 청소에서 빼고 `wda_deck_job_days`(7) 뒤 지움 — DocForge 와 같은 자리 · 같은 규칙).
job_id 는 포털이 짓는 32자 16진 무작위다. 칸 — `owner_sub` · `owner_email` · `conversation_id` · `report{id, title}` · `options{targets, doc_style, pptx_mode}` ·
`wda{run_id, slug}`(화면에 주지 않는다) · `state` · `step` · `created_at` · `updated_at` · `render_submitted_at` · `images_not_sent` ·
`finished{state, files[{kind, bytes}], skipped[], error, at}` · `dismissed`. 보고서 본문 · 파일 바이트는 남기지 않는다.

### 7.2 상태 낱말 하나(화면에 보이는 것)

`queued`(줄 서는 중) · `preparing`(보고서 읽기 → 조각 나누기 → 장면 구성 → 화면 굽기) · `rendering`(파일 만드는 중) · `done` · `failed`.
`step` 은 지금 단계의 이름, `progress` 는 **단계 기준**(시간 아님)의 대강 값이다.

| WDA run.status | 단계(running) | render.status | 포털 state · step | progress |
|---|---|---|---|---|
| queued | — | — | queued | 0 |
| running | ingest | — | preparing · 보고서 읽기 | 10 |
| running | fragmentize | — | preparing · 조각 나누기 | 25 |
| running | scenario | — | preparing · 장면 구성 | 40 |
| running | build | — | preparing · 화면 굽기 | 55 |
| done | — | 없음(이어서 렌더가 없는 판) | preparing · 렌더 맡기기(`advance`) | 60 |
| done | — | queued | rendering · 차례 기다림 | 65 |
| done | — | building(MCP 잡에만 있다) | rendering · 준비 | 70 |
| done | — | rendering | rendering · 만드는 중 | 80 |
| done | — | done | done(요청한 것과 만든 것을 견준 뒤) | 100 |
| done | — | failed | failed · 파일 만들기 | — |
| failed | 실패한 단계 | — | failed · 그 단계 | — |
| (404 · 410) | — | — | failed · 'WDA 가 이 실행을 모른다(지웠거나 다른 박스)' | — |

### 7.3 한 번만 · 늦음 · 끝

- 같은 사람 · 같은 보고서 · 같은 옵션의 잡이 돌면 새로 만들지 않고 그 잡을 준다. 끝난 지 보존 기한 안이면 그것을 주고 '다시 만들기'(`again`)만 새로 만든다.
- 사람당 동시 상한 `wda_deck_inflight_max`(2) · 박스 전체 동시 상한 `wda_deck_inflight_box_max`(4) — 넘으면 429 와 까닭. WDA 에 동시 상한이 없어서다(W-14).
- `advance` 는 잡 잠금 안에서 기록을 다시 읽는다 — 렌더 맡기기는 `render_submitted_at` 이 비었을 때만, 알림은 `finished` 가 비었을 때만. 두 번 눌러도
  알림은 하나다.
- 늦음 — WDA 실측이 5.5초(11-01)라 문턱을 넉넉히 낮췄다. 준비 5분 · 렌더 15분 · 영상이 있으면 60분을 넘으면 상태에 `late: true` 를 싣고 화면이
  '오래 걸린다' 를 말한다(잡은 그대로). 6시간이 지나도 끝나지 않으면 포털이 실패로 닫는다(`wda_deck_give_up_s`) — WDA 는 재기동에 끊긴 실행을
  running 으로 남긴다(W-12 전까지 이 그물이 유일하다).
- 끝(done · failed)을 본 화면은 저절로 `advance` 를 부른다 — 패널이든 입력창 위 줄이든. 알림은 그 사람의 대화에만 쓰므로 사람에게 다시 묻지 않는다
  (WD-D10). 단추를 누른 대화가 답을 받는 중이면 끝날 때까지 기다렸다 부른다(PP-D3 ⑤의 순서).
- 취소는 M1 에 없다 — WDA 에 취소가 없다. '숨기기' 는 목록에서만 뺀다(WDA 는 끝까지 돈다).

## 8. 보안

- **주인 없는 run 은 비공개가 아니다.** 신원 없이 만든 run(CLI · 신원 없는 MCP · 직결)은 WDA 의 주인 기능이 들어간 뒤에도 영영 지금처럼 열려 있다.
  포털은 늘 신원을 싣는다(허브 Caddy 경유 — 직결하지 않는다).
- 신원의 정본은 허브 Caddy 가 실은 `X-Heax-User-Email` 하나다(REST 에서만). `x-hwax-user` 는 쓰지 않는다 — Caddy 가 지우지 않아 누구나 적어 보낼 수
  있고 게이트웨이도 WDA 에는 싣지 않는다(§2.4). `/mcp` 의 `X-Heax-User-Email` 은 허브 관리자로 접히므로 MCP 는 주인을 정하지도, 주인 있는 run 을
  열지도 않는다(W-4).
- 두 겹 — 포털 잡 기록의 주인(아니면 404)과 WDA run 의 주인(아니면 404). 포털은 늘 **요청한 사람의** 이름으로 WDA 를 부르므로 포털 쪽 실수가 있어도
  남의 run 은 WDA 가 404 로 막는다.
- 브라우저는 WDA 의 run_id · job_id · 주소 · 서버 경로를 보지 않는다 — 포털 응답 · 알림 · 링크는 포털 잡 id 와 포털 경로뿐이다. 내려받기는 포털이 서버에서
  받아 흘린다. 서명 URL 은 쓰지 않는다 — 서버 쪽 가져오기가 이미 그 사람으로 인증되고, 들고 다니는 URL 은 로그로 샐 수 있는 열쇠다.
- 내려받기 응답 — `Content-Disposition: attachment` · `X-Content-Type-Options: nosniff` · `Cache-Control: private, no-store` · HTML 은 덧붙여
  `Content-Security-Policy: sandbox`. HTML 을 화면에 끼우지 않는다(M1) — 허브 앱은 포털과 같은 오리진(`/apps/`)이라 그 HTML 의 스크립트가 포털 쿠키 ·
  CSRF 값에 닿을 수 있다. 끼운다면 `sandbox="allow-scripts"`(allow-same-origin 없이) iframe 으로만(WD-D14).
- 짧은 PAT — 청중 `heax-hub` 하나 · 10분 · 무작위 jti · 저장하지 않는다 · 로그에 남기지 않는다. 이 청중의 첫 포털 쪽 쓰임이라 `config.py:243-245` 의
  '소비처가 없다' 주석을 함께 고친다.
- 남는 위험 — ① WDA 의 루프백 포트에 직접 붙으면 `X-Heax-User-Email` 을 꾸밀 수 있다(같은 박스 안 — StepForge · DocForge 의 브라우저 길과 같은
  신뢰 경계). ② 허브 서비스 토큰을 쥔 쪽은 허브 관리자로 보인다. ③ RA 에서 보고서를 지워도 WDA 사본은 WDA 보존 기한까지 남는다(W-13 · M2 지우기).
  닫는 길은 WDA 의 사람별 위임(per_user_sso, HWAXRisk 꼴)이고 2단계로 둔다(WD-D19).
- 감사 — `deck_create` · `deck_render` · `deck_finish` · `deck_download` 를 사람 단위로 남긴다(잡 id · 보고서 번호 · 출력 · 바이트 수 — 본문 · 제목 전문은
  남기지 않는다).

## 9. 실패와 사람이 보는 것

| 어디서 | 무엇 | 사람이 보는 것 |
|---|---|---|
| 권한 | `plat:webdesign` · `plat:reportarchive` 없음 | 단추가 없다(직접 부르면 403 '권한이 없습니다(…) — 내 권한 페이지에서 요청') |
| 켜기 | 스위치 꺼짐 · WDA 에 주인 기능 없음 · 탐침 실패 | 단추가 없다(직접 부르면 409 와 까닭) |
| RA | 연결 · 위임 없음 / 403 / 404 | '보고서를 읽을 수 없습니다 — RA 연결(외부 연결) · 권한을 확인하세요' — WDA 는 부르지 않는다 |
| 크기 | 본문 > 16MB | '보고서가 커서(…MB) 발표자료로 만들 수 없습니다' — WDA 는 부르지 않는다 |
| 허브 | 401 · 403(계정 없음 · 앱 권한) | 허브가 준 까닭 그대로 |
| WDA 접수 | 연결 실패 · 5xx · 413 · 422 | 'WDA 가 받지 않았습니다(…)' · 잡은 실패로 닫고 알림 |
| WDA 진행 | 단계 실패 | 'N단계 「장면 구성」 에서 멈췄습니다 — 까닭' · 알림 · '다시 만들기' |
| WDA 렌더 | 실패 · 일부만 | 실패는 까닭, 일부만이면 만든 것은 받기 링크 · 빠진 것은 이름과 까닭(WDA 의 skipped) |
| 시간 | 문턱 넘음 / 24시간 | '오래 걸립니다(N분)' / 실패로 닫고 알림 |
| WDA 가 모름 | 404 · 410 | 'WDA 가 이 실행을 모릅니다(지웠거나 다른 박스)' |
| 받기 | 보존 기한 뒤 | '파일이 지워졌습니다 — 다시 만드세요' |
| 사람 | 남의 잡 id | 404 — 있는지도 알리지 않는다 |

## 10. 범위 밖(이번에 하지 않는 것)

- 영상 기본 — 고를 수는 있다(오래 걸린다고 적는다). 내레이션은 끈다.
- HTML 끼워 보기 · PDF 미리보기 — 내려받기만(WD-D14).
- 리스크 심사 · 결정 매트릭스 같은 새 장르 · 장면 꼴(`short-9x16` 등) 고르기 — WDA 의 기본 꼴(wide-16x9) 그대로.
- RA 보고서의 그림 싣기 — M2(포털이 그 사람 명의로 RA 파일을 받아 함께 넘기는 WDA 계약이 먼저다). M1 은 그림 수를 알림에 말한다.
- 분석 루틴 RA 초안 자리 · 다시 시도(WDA resume) · WDA 쪽 지우기 · MCP 로 내 발표자료 보기(per_user_sso) — M2.
- 챗 LLM 이 WDA 도구로 발표자료를 만드는 길(운영자 페르소나) — 막지 않되 단추로 안내하도록 페르소나 글만 고친다(WD-D20).

## 11. 시험

먼저 실패하는 시험부터 쓴다(지금 코드에서 빨간 것).

- `test_중계는_심의_결과의_보고서_번호를_서버_사본에_남긴다` — 지금 중계는 outcome 을 버린다(`routes.py:2854-2895`).
- `test_서버_사본에서_심의_보고서_번호를_되살린다`(node 순수 함수, `test_docforge_front.py` 의 길) — 지금 `serverMessagesToLocal` 은 outcome 이 없다.
- `test_중계는_보고서_저장_답의_ra_report_를_남긴다` — 에이전트 서버의 새 칸과 짝.

백엔드(가짜 RA · 가짜 WDA 는 `httpx.MockTransport`, `test_docforge_delivery.py` 의 꼴).

- 만들기는 그 사람 RA 토큰으로 읽고 본문을 넘긴다 — WDA 에 간 Authorization 은 포털이 서명한 PAT(청중 heax-hub · 그 사람 이메일)이고 포털은
  `X-Heax-User-Email` 을 싣지 않는다.
- 남의 잡은 상태 · advance · 파일 · 숨기기 모두 404 · 권한 둘 중 하나가 없으면 403 · 스위치 꺼짐 / 능력 없음이면 만들지 않고 status 가 enabled false.
- RA 403 · 404 · 본문 상한이면 WDA 를 부르지 않는다 · 허브 403(계정 없음)이면 그 까닭을 그대로.
- 상태 낱말 표(§7.2) 전부 · 404 → gone.
- `advance` 를 동시에 두 번 → 알림 하나(`conv_store.append` 한 번) · 실패도 알림 하나 · 요청한 출력이 빠지면 알림에 이름과 까닭 · 알림 · 응답에 WDA 주소 ·
  run_id 가 없다.
- 파일은 주인에게만 흘리고 머리(attachment · nosniff · no-store · HTML 은 CSP sandbox)를 단다.
- 같은 보고서 · 같은 옵션은 하나로 · `again` 은 새로 · 사람당 동시 상한 429 · 잡 기록은 스테이징 청소에서 빠지고 기한 뒤 지운다 · 감사에 본문이 없다.
- 이력 — 알림의 근거가 `kind: upload` 로 다음 턴에 실린다.

브라우저(헤드리스, `backend/tests/test_chat_ppt_in_browser.py` 의 꼴 — 가짜 fetch · 가짜 시계).

- 심의 결과 카드의 '발표자료로' → 진행(queued → 장면 구성 → 만드는 중) → 끝나면 **단추를 누른 대화**에 알림과 받기 링크(다른 대화를 보고 있어도 그 대화에).
- 권한 · 능력이 없으면 단추가 없다 · 새로고침 뒤에도 단추와 '끝나지 않은 발표자료' 줄이 산다 · 답을 받는 중인 대화면 끝난 뒤에 알림을 남긴다.

계약 탐침(dev, WDA 가 닿을 때만 — 읽기만) — `/api/health` 의 features · 신원 없는 `GET /api/runs` 에 주인 있는 run 이 안 보인다.

## 12. 단계

| 단계 | 무엇 | 누가 |
|---|---|---|
| **M0 전제** | §13 결정 · WDA push(방법은 사용자 결정) → 허브 SIF 재빌드(dev) · WDA 요청 W-1 ~ W-12 · 능력 `owner` 확인 · (결정되면) 매니페스트 `portal_auth` | 사람 · WDA 세션 · HEAXHub 세션 |
| **M1 포털(dev)** | 모듈 `wda_deck.py` · 라우트 · 설정 · 단추 셋 · 서버 사본 보존(delib_outcome · ra_report) · 입력창 위 줄 · 시험 · 에이전트 서버 `ra_report` 칸 · 페르소나 글 · 변경 이력 | 포털 세션(+ 에이전트 서버 한 칸) |
| **M2** | 루틴 RA 초안 자리 · RA 그림 함께 보내기 · 다시 시도(resume) · WDA 지우기 · PDF 미리보기(sandbox) · MCP 쪽 주인(per_user_sso) | 포털 · WDA |
| **M3 cae00** | 박스 스위치 · WDA SIF · 허브 계정 · 확인(server-setup 은 M1 끝에 쓴다) | 사람 |

M1 은 스위치를 꺼 둔 채 올린다 — M0 이 끝나지 않은 박스에서는 아무 일도 일어나지 않는다.

## 13. 사람이 정한 것(2026-11-01)

| # | 물음 | 결정 |
|---|---|---|
| U-1 | WDA 의 주인 기능(W-1 ~ W-6)을 단추를 켜는 **전제**로 할까 | **예.** 지금 WDA 는 로그인 없이 목록 · 내려받기가 된다(§2.4 실측). 깨지 않는 꼴(W-1 ~ W-6)이 들어오고 `/api/health` 가 `owner` 를 말해야 단추가 보인다(WD-D24) |
| U-2 | WDA 를 GitHub 에 어떻게 올릴까 | **사용자가 손으로 push 한다.** 다른 누구도 push 하거나 역사를 다시 쓰지 않는다. 11-01 에 코디네이터가 다시 해 본 push 도 같은 workflow 범위 거절이었다(WD-D25) |
| U-3 | 허브 매니페스트에 `launch.portal_auth: true` 를 켤까 | **켠다.** HEAXHub 변경과 dev 반영은 다른 에이전트가 한다 — 이 가지는 HEAXHub 를 건드리지 않는다(WD-D26) |
| U-4 | 'PDF' 는 무엇인가 | **WDA 의 정식 보고서 문서(`doc_style=report`)가 기본, 요약(brief) · 메모(memo)는 고를 수 있게.** 슬라이드 PDF(W-19)는 지금 청하지 않는다(WD-D27) |
| U-5 | M1 의 단추 자리 | **셋 모두** — 심의 결과 카드 · `/보고서` 저장 답 · RA 보내기 알림. 분석 루틴 RA 초안은 M2(WD-D28) |
| U-6 | (묻는 중) 심의 결과 카드 단추를 W-21(`format:deliberation`) 전까지 둘까 | 코디네이터가 사용자에게 묻고 있다. 문은 어느 쪽이든 짓는다 — W-21 이 없으면 `deliberation` 보고서의 단추는 서지 않는다(WD-D29) |
