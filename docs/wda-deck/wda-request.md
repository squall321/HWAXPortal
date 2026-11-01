# WebDesignAgents 에 드리는 요청 — 포털 '발표자료로' 단추가 부를 계약 · 신원과 주인 · 내려받기 · 한도

> 대상 — WebDesignAgents(WDA) 세션 · 2026-11-01 · 보낸 쪽 — HWAX 포털(`docs/wda-deck/`, 계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md)).
> 이 글만으로 읽히게 썼다. 줄 번호는 WDA `9dabf86` · HEAXHub `7b9a8ed` · 게이트웨이 `63fbc4f` 판이다.
> 요약 — 포털은 **허브 Caddy 를 거쳐 WDA 웹 REST** 를 그 사람 이름으로 부른다(MCP 는 부르지 않는다). WDA 가 할 일은 넷이다 —
> ① 허브가 실어 주는 `X-Heax-User-Email` 로 **주인을 정하고 주인만 보게** 하기(깨지 않는 꼴) ② 빌드 뒤 **이어서 렌더**하고 뺀 출력을 말하기
> ③ 능력 · 오류 · 재기동 처리를 기계가 읽게 하기 ④ 심의 보고서 꼴 `delib-16x9` 를 `format:delib-16x9` 와 `formats` 의 상태로 알리기(W-21 — 11-01 저녁
> WDA 가 지었다, 지금 draft). 그리고 **main 을 GitHub 에 올려 허브 SIF 를 다시 짓는 것**이 먼저다 — **사용자가 손으로 push 한다**(11-01 결정,
> WDA 세션은 push 하지 않는다).

## 1. 배경 — 사용자 결정(2026-11-01)

1. **포털이 맡고 알린다.** 포털이 만든 RA 보고서 옆 '발표자료로' 단추. 포털이 그 보고서를 **그 사람 명의로** 읽어 본문을 WDA 에 넘기고(요청 R2 (나)),
   잡 기록(누가 맡겼나)을 남기고, 화면이 진행을 보이고, 끝나면 그 대화에 받기 링크 알림을 남긴다. 챗 LLM 은 잡을 폴링하지 않는다.
2. **기본 출력은 PPT + PDF**(`pptx_mode` hybrid). 영상 · HTML · Word 는 단추에서 고를 수 있다.

같은 날 오후 사용자가 포털 계획의 물음 다섯을 정했다 — ① WDA 의 주인 기능(W-1 ~ W-6)이 단추를 보이는 **전제**다. ② WDA 는 **사용자가 손으로 push** 한다
(누구도 대신 push 하거나 역사를 다시 쓰지 않는다). ③ 허브 매니페스트 `launch.portal_auth: true` 를 **켠다** — 반영됐다(HEAXHub `385783f`, 7 P-2).
④ 기본 PDF 는 WDA 의 **정식 보고서 문서**(`doc_style=report`), 요약(brief) · 메모(memo)는 고를 수 있다 — 슬라이드 PDF 는 청하지 않는다. ⑤ 단추 자리는
심의 결과 카드 · `/보고서` 저장 답 · RA 보내기 알림 셋이다.

## 2. 포털이 하는 일(흐름)

1. 사람이 단추를 누른다 → 포털이 RA `GET /api/reports/{id}` 를 그 사람의 RA 토큰으로 읽는다(서비스 계정 없음).
2. 포털이 그 사람 이름으로 짧은 포털 PAT(RS256 · 청중 `heax-hub` · scope `api` · 10분 · 무작위 jti)을 찍어 `{WDA}/api/runs` 를 부른다.
   `{WDA}` 는 허브 Caddy 의 `/apps/web_design_agents` 다 — 루프백 포트에 직결하지 않는다.
3. 허브 게이트(forward_auth)가 그 PAT 를 검증해 허브 사용자로 잇고 앱 권한을 본 뒤(HEAXHub `backend/app/api/v1/authz.py:61-74,148-168`),
   Caddy 가 **클라이언트가 보낸 `X-Heax-User-Email` · `X-Heax-User-Name` 을 지우고** 확인한 값으로 다시 싣는다(HEAXHub
   `backend/app/services/proxy_manager.py:45,70-94` · 내부 앱 라우트 `:162`). 포털은 그 머리를 싣지 않는다.
4. 포털이 3초마다 `GET {WDA}/api/runs/{run_id}` 로 진행을 묻고(늘 **요청한 사람의** 이름으로), 끝나면 산출물을 확인해 그 대화에 알림을 남긴다.
5. 사람이 받기를 누르면 포털이 `GET {WDA}/api/runs/{run_id}/download/{kind}` 를 서버에서 받아 흘린다. **브라우저는 WDA 의 run_id · 주소를 보지
   않는다.** 서명 URL 은 필요 없다 — 가져오기 자체가 그 사람으로 인증된다.

## 3. 신원과 주인 — 깨지 않는 꼴

### 3.1 왜 `X-Heax-User-Email` 인가(그리고 왜 `x-hwax-user` 가 아닌가)

- `x-hwax-user` 는 주인 판정에 쓸 수 없다. ① 게이트웨이는 WDA 에 이 머리를 싣지 않는다 — 호출마다 신원을 싣는 것은 `IDENTITY_FWD_BACKENDS`(기본
  `hwax-deliberation` 하나)와 `per_user_sso`(WDA 없음)뿐이고, 나머지 허브 앱은 상주 세션 하나로 허브 서비스 토큰을 싣는다(게이트웨이
  `gateway.py:6336-6343,6856-6870,1446-1448`). 그래서 지금 WDA 의 MCP 세션 칸(`src/wdmcp/session.py:159-191`)은 게이트웨이 사용자 전원이 한 칸이다.
  ② Caddy 는 `x-hwax-user` 를 지우지 않는다 — 자기 PAT 로 `/apps/web_design_agents/mcp` 에 직접 붙은 누구나 남의 이메일을 적어 보낼 수 있다(게이트웨이도
  같은 까닭으로 소속 머리에 서명을 붙인다 — `gateway.py:259-262`).
- `/mcp` 로 오는 `X-Heax-User-Email` 은 게이트웨이 서비스 토큰의 주인(허브 첫 관리자)으로 **접힌다**(`gateway.py:273-278`, HWAXRisk 가 같은 까닭으로
  위임 머리를 따로 둔다 — HWAXRisk `backend/app/routes.py:444-449`). 그래서 **REST 의 `X-Heax-User-Email` 만** 주인으로 쓴다.
- 남는 위험 하나 — 같은 박스에서 WDA 루프백 포트에 직접 붙으면 그 머리를 꾸밀 수 있다. StepForge · DocForge 의 브라우저 길과 같은 신뢰 경계로 받아들인다.
  닫는 길은 2단계 사람별 위임(W-18)이다.

### 3.2 규칙(필수 — 단추를 켜는 전제)

- **W-1 만들 때 주인을 정한다.** REST `POST /api/runs` 에 `X-Heax-User-Email` 이 있으면 run 에 `owner`(소문자 이메일)를 적는다. 본문의 어떤 owner 칸도 믿지 않는다.
  `/mcp` 와 그 밖의 길은 주인을 정하지 않는다.
- **W-2 주인 있는 run 은 주인만 본다.** run 단위 REST 전부 — `GET /api/runs/{id}` · `/artifacts` · `/download/{kind}` · `/preview/{path}` · `/scenes` ·
  `/scenes/{name}/html` · `/scenes/{name}/still.png` · `PATCH /scenario` · `/render` · `/resume` · `/qa` · `/chat`(GET · POST) · `/revise` — 는 요청의
  `X-Heax-User-Email` 이 주인과 같을 때만 연다. 다른 사람이거나 **신원이 없으면 없는 것과 같은 404** 다(있는지도 알리지 않는다).
- **W-3 목록을 거른다.** `GET /api/runs` 는 내 run 과 주인 없는 run 만 준다. 신원이 없으면 주인 없는 run 만.
- **주인 없는 run 은 비공개가 아니다.** 신원 없이 만든 run(옛 것 · CLI · 신원 없는 MCP · 직결)은 이 기능이 들어간 뒤에도 영영 지금처럼 열려 있다. 그래서
  포털은 **늘** 허브 Caddy 를 거쳐 신원을 싣는다. (지금 WDA 는 허브 매니페스트가 company + stable 이고 `launch.portal_auth` 가 없어 **로그인 없이**
  닿는다 — 2026-11-01 dev 실측, 포털 nginx 를 거친 `/apps/web_design_agents/api/runs` 가 익명 200. HEAXHub `authz.py:83-99,138-146`. 사용자 결정으로
  `launch.portal_auth: true` 를 켰다(7 P-2 — 익명은 이제 401). 그래도 **주인 없는 run 은 로그인한 누구에게나 여전히 열린다.**)
- **W-4 MCP 는 주인 있는 run 에 닿지 않는다.** MCP 의 신원은 확인할 수 없으므로(3.1), run_id · job_id · 서버 경로를 받는 도구 — `report_fragmentize` ·
  `scenario_build` · `scenario_patch` · `scenario_revise` · `scene_list` · `scene_html` · `scene_still` · `render_submit`(scenario_path · build_dir · run_dir) ·
  `render_status` · `qa_run`(build_path) — 는 대상이 주인 있는 run(그 `pipeline/<run_id>` · `build/<slug>` · `renders/<slug>` 아래)이면 `NOT_FOUND` 로
  답한다. `/api/render_jobs/{job_id}/download/{kind}` 도 그 잡의 입력 · 출력이 주인 있는 run 아래면 404. MCP 와 웹 run 은 같은 `pipeline/` 을 쓴다
  (`src/wdmcp/server.py:202-207`).
- **W-5 id 를 추측할 수 없게 · id 꼴을 검사한다.** 주인 있는 새 run 의 id 는 128비트 이상 무작위를 담는다(지금은 초 단위 시각 + 16진 4자 —
  `src/wdweb/runs.py:47-48`). run_id 를 받는 곳은 모두 꼴을 검사해 경로 탈출을 막는다(`_run_dir(run_id)` 는 그대로 이어 붙인다 — `server.py:202-203`).

## 4. 포털이 부를 계약

모든 요청은 `{WDA} = <허브 Caddy 오리진>/apps/web_design_agents` 로 간다. `Authorization: Bearer <포털 PAT>` 는 허브 게이트가 보고, WDA 는 읽지 않아도 된다.
WDA 가 보는 신원은 `X-Heax-User-Email` 하나다. 응답은 지금의 봉투 그대로 `{success, data, message}`(`src/wdweb/app.py:64-95`)에 W-10 의 `code` 를 더한다.

### 4.1 만들기 — `POST {WDA}/api/runs`

```json
{
  "report_json": { "…": "RA GET /api/reports/{id} 의 data(ReportRead) — 봉투째여도 된다(ingest 의 FORM_REST)" },
  "slug": "ra-123",
  "source": { "system": "report-archive", "report_id": 123, "client": "hwax-portal" },
  "render": { "targets": ["pptx", "pdf"], "doc_style": "report", "pptx_mode": "hybrid", "narration": false }
}
```

- `source` 는 표시 · 감사용이다(믿지 않아도 된다). `render` 는 **새 선택 칸(W-8)** — 있으면 빌드가 끝난 뒤 그 옵션으로 렌더를 저절로 맡는다. 없으면 지금과 같다.
- `format` — WDA 가 11-01 저녁에 낸 칸(W-21). 포털은 **심의(`deliberation` 템플릿) 보고서에만** `"format": "delib-16x9"` 를 싣고, 그 밖의 보고서에는 칸을
  싣지 않는다(없으면 `wide-16x9` — 지금과 같다). 모르는 꼴이면 WDA 가 곧바로 400 이다(봉투 · 쓸 수 있는 꼴을 `message` 에 — 실행을 만들지 않는다). 포털은
  그 까닭을 그대로 보이고 **기본 꼴로 다시 보내지 않는다**(심의 보고서를 wide-16x9 로 넣으면 결정문 · 액션아이템이 빠진다 — 4.6-2).
- 응답 — `202 {success: true, data: {run_id, slug, owner}}`. 오류 — 400 `INVALID`(꼴 · 모르는 format) · 413 `TOO_LARGE`(본문 상한, W-7) · 422 `INVALID` · 503 `BUSY`(선택).
- 포털은 응답의 run_id 를 서버 기록에만 둔다.

### 4.2 진행 — `GET {WDA}/api/runs/{run_id}`(주인만)

지금 응답(`runs.py:155-169` 의 원장)에 칸 셋을 더한다 — `owner` · `render.requested` · `render.skipped`(W-9).

```json
{
  "run_id": "…", "owner": "user@corp.example", "status": "queued | running | done | failed",
  "stages": [ { "stage": "ingest | fragmentize | scenario | build", "status": "pending | running | done | failed", "error": null } ],
  "render": null,
  "error": null, "created_at": "…", "updated_at": "…"
}
```

`render` 가 있으면 `{status: "queued | rendering | done | failed", targets, requested, outputs: {kind: …}, skipped: [{target, reason}], doc_style, pptx_mode,
error, started_at, finished_at}`. **낱말은 지금 것 그대로 두어 달라** — 포털이 아래 표로 화면 낱말 하나에 접는다(WDA 가 고칠 것은 없다).

| WDA run.status | 단계(running) | render.status | 포털 화면 |
|---|---|---|---|
| queued | — | — | queued(줄 서는 중) |
| running | ingest · fragmentize · scenario · build | — | preparing(보고서 읽기 · 조각 나누기 · 장면 구성 · 화면 굽기) |
| done | — | 없음(이어서 렌더가 없는 판) | preparing(포털이 4.3 을 한 번 부른다) |
| done | — | queued · building · rendering | rendering(차례 기다림 · 준비 · 만드는 중) |
| done | — | done | done(requested 와 outputs 를 견준 뒤) |
| done | — | failed | failed(파일 만들기) |
| failed | 실패한 단계 | — | failed(그 단계) |
| 404 · 410 | — | — | failed('WDA 가 이 실행을 모른다') |

### 4.3 렌더 — `POST {WDA}/api/runs/{run_id}/render`(주인만, W-8 이 없는 판의 대체 길)

`{targets, doc_style, pptx_mode, narration: false}` → 202. 409 `NOT_BUILT`(빌드 전) · 409 `BUSY`(이미 렌더 중 — 포털은 이것을 '이미 맡겼다' 로 읽는다) · 400 `INVALID`.

### 4.4 크기 — `GET {WDA}/api/runs/{run_id}/artifacts`(주인만)

지금 그대로(`app.py:408-411`) — 포털은 `exists` · `size` 만 쓴다.

### 4.5 받기 — `GET {WDA}/api/runs/{run_id}/download/{kind}`(주인만, W-11)

kind ∈ `pptx · pdf · docx · html · mp4`(지금 `_DOWNLOAD_META` — `app.py:414-434`). 포털은 화면의 `video` 를 `mp4` 로 부른다.

### 4.6 능력 — `GET {WDA}/api/health`(W-6)

`{"status": "ok", "version": "x.y.z", "features": ["owner", "render_chain", "doc_formats", "skipped_report", "interrupted", "format:wide-16x9", "format:delib-16x9", …],
"formats": {"wide-16x9": "active", "delib-16x9": "draft", …}}` — 허브 health_check 는 `status` 만 보니 칸을 더해도 깨지지 않는다(`app.py:124-127`).
`format:<id>` 와 `formats` 는 WDA 가 11-01 저녁에 꼴 등록부에서 만들어 낸다(아래 4.6-2). **포털은 `owner` 가 없거나 이 응답을 못 읽으면 단추를 숨긴다**
(옛 SIF 로 되돌린 박스에 본문을 넘기지 않게). 포털은 이것도 그 사람의 포털 PAT 로 부른다 — `portal_auth` 가 켜지면 허브 게이트가 익명을 막는다.

### 4.6-2 심의 보고서 꼴 — W-21 `format:delib-16x9`(심의 자리의 단추를 세우는 표지)

WDA 답(11-01, Q2) — `deliberation` 템플릿 보고서(화두 · 라운드 요지 · 의사결정문 · 액션아이템)를 넣으면 조각은 바르게 뽑히지만 장면이 제품 소개 뼈대
(opening → problem → concept → process → differentiators → evidence → closing)로 눌려 결정문이 `problem` 장면에 한 번 묻히고 액션아이템 · 라운드 요지가
사라지며 '보고서 참조' 같은 채움 글이 영상에 나간다. **사용자 결정(11-01, U-6) — '심의 형식이 설 때까지 숨긴다'.**

WDA 둘째 답(11-01 저녁) — 심의 꼴 `delib-16x9` 를 지었다(WDA 로컬 판 · 허브 SIF 에는 아직 없다). 뼈대는 화두 → 라운드 → 결정 → 액션 → 요약이고 지어내지
않는다(담당이 없으면 '미지정', 때가 없으면 '후속'). 쟁점 장면은 아직 없다(WDA 의 다음 일). 계약은 이렇다.

- **W-21** `/api/health` 의 `features` 에 꼴마다 `format:<id>` 가 실리고(꼴 등록부에서 만들어 낸다), `formats` 가 꼴마다 상태(`draft` · `active` …)를 준다.
  심의 꼴의 표지는 **`format:delib-16x9`** 다(첫 요청의 이름 `format:deliberation` 대신 WDA 의 이름을 쓴다). 지금 상태는 `draft` 이고 `owner` 는 아직 없다
  (W-1 ~ W-12 는 사용자가 직접 시킬 때 짓는다).
- `GET /api/formats` — 꼴마다 id · 이름 · 상태 · 뼈대 · 템플릿 · 출력 · 무대 크기(MCP `format_list` 와 같은 원천). 포털은 부르지 않는다(health 로 충분하다).
- 만들기 — `POST /api/runs` 의 `format` 칸(4.1). 없으면 `wide-16x9`(지금과 같다), 모르는 꼴이면 곧바로 400(봉투 · 쓸 수 있는 꼴을 `message` 에).
- **포털의 문(정책 함수 하나)** — RA 보고서의 템플릿(최상위 `template_id` 와 페이지마다의 `template_id`) 가운데 하나라도 `deliberation` 이면 `owner` 에 더해
  `features` 에 `format:delib-16x9` 가 있고 **`formats["delib-16x9"]` 가 `active`** 여야 단추를 보이고 만들기를 받으며, 만들기에 `"format": "delib-16x9"` 를
  싣는다. `draft` 는 숨긴다 — 받아도 될지 사용자에게 묻는 중이고, 답이 오기 전까지는 `active` 만이다. 그 밖의 템플릿(지금 단추 자리에서는 RA 보내기
  알림의 `__import_blank__`)은 `owner` 만 보고 `format` 을 싣지 않는다. 포털의 세 자리 가운데 심의 결과 카드와 `/보고서` 저장 답이 `deliberation`
  템플릿이고(에이전트 서버 `deliberation.py:7631,7892`), RA 보내기 알림이 `__import_blank__` 다. 그래서 `delib-16x9` 가 active 가 되기 전에는 RA 보내기 알림
  자리에서만 단추가 선다.
- **`block_sections` 는 포털이 만들어 싣지 않는다(M1).** WDA 는 머리글 추론을 덮어쓰는 `block_sections`(RA 단락 낱말 — `decision` · `action_item` ·
  `alternatives` · `recommendation`, 심의 전용 `topic` · `round`)를 받는다. 그러나 RA 블록 id 에서 단락이 하나로 정해지지 않는다. ① 같은 `deliberation`
  템플릿(블록 `background` · `results` · `recommendation` · `minutes`)을 세 곳이 다른 뜻으로 채운다. 심의 결과의 `recommendation` 은 결정문 전체(핵심 요약 ·
  결정사항 · 쟁점 · 미해결 쟁점과 담당 · 다음 액션 · 쉬운 설명)이고, `/보고서` 의 `recommendation` 은 사람의 결론과 마지막 답 문단이며, 분석 루틴 초안은
  `results` 에 절마다 · `recommendation` 에 인사이트 · `minutes` 에 근거 부록을 싣는다. ② 결정과 액션이 **한 블록 안에** 문단으로 섞여 있다 —
  `recommendation` 에 `decision` 을 붙이면 액션이 근거로 잘려 나간다. ③ RA 자체의 `pages[].block_sections`(블록 id → RA 단락 코드)는 이 보고서들에 비어
  있다(만드는 쪽이 싣지 않는다). 사람이 RA 에서 단락을 단 보고서는 그 칸이 ReportRead 에 실려 바뀌지 않고 그대로 간다 — WDA 가 거기서 읽으면 된다.
  그래서 지금은 WDA 의 머리글 추론에 맡긴다. 블록마다 단락이 하나로 정해지게 하려면 만드는 쪽(에이전트 서버)이 결정 · 액션을 다른 블록으로 나누고
  RA `block_sections` 를 실어야 한다 — 그때 다시 본다.
- 머리글 추론을 위한 사실(코드 읽기 — 우리 심의 보고서에 실제로 있는 낱말). WDA 가 보는 낱말(화두 · 라운드 요지 · 의사결정문 · 액션아이템 · 쟁점 · 대안 ·
  권고) 가운데 '화두' · '라운드 요지' · '액션아이템' · '대안' · '권고' 는 그대로는 없다.
  - `background` — 첫 항목이 `심의 주제: …`(= 화두). 뒤에 VOC 환기 · 정량 근거 선주입이 붙을 수 있다.
  - `results` — 마지막 심화 라운드의 좌석별 발언(`• ` 로 시작하는 항목마다 한 좌석, = 라운드 요지).
  - `recommendation` — 결정문. 맨 앞 `■ 핵심 요약`(불릿 3~5줄), 표지 줄(`■ 기준일` · `■ 봉인 실행` · `■ 외부 응답자 실행` — 있을 때만), 의장이 쓴 본문
    (`## 의사결정문` 머리 아래 번호 항목 `(0)` 커버리지 · `(1) 상황 판단` · `(2) 결정사항` · `(3) 결정 간 관계` · `(4) 쟁점의 축과 소수의견` ·
    `(5) 뒤집히는 조건` · `(6) 미해결 쟁점 + 담당·다음 액션` · `(7) 신뢰도·전제` · `(8) 수렴 경과` — 항목 이름은 모델이 쓰므로 글자가 조금 다를 수 있다),
    끝에 `■ 쉬운 설명`(`### 한마디로` · `### 왜 그런가` · `### 당장 할 일 / 다음에 할 일 / 하지 말 것`). 액션은 `(6)` 과 `당장 할 일` 에 있다.
  - `minutes` — `참여: …` · `N라운드 심의(…)` 줄 뒤에 라운드 머리(`— 1라운드 — 도메인별 초기 입장 —` · `— k라운드 — 상호 반박·심화 —` ·
    `— N라운드 — 수렴·최종 입장 —`)와 `[좌석] 발언` 줄.
  - 항목 하나는 2,000자 아래로 나뉘어 있다(에이전트 서버 `_ra_blocks`) — 한 문단이 두 항목으로 이어질 수 있다.
- 알아 둘 사실(코드 읽기) — RA 의 `deliberation` 보고서는 블록 정의를 보고서에 싣지 않는다. 페이지의 `content` 에 템플릿 블록 id(background · results ·
  recommendation · minutes) 만 있고 타입은 RA 템플릿 스키마에 있다(ReportArchive `modules/reports/routes.py:677-722` — 템플릿 블록은 `content` 로,
  `extra_blocks` 는 빈 채). 지금 `_page_blocks`(`src/wdpipeline/ingest.py:407-442`)는 정의 없는 `content` 키를 건너뛰므로 실물 심의 보고서는 블록 0개가
  될 것이다 — 심의 꼴이 이것을 다루는지 실물 하나로 확인해 달라. 타입을 RA 템플릿 스키마(`GET /api/templates/{id}/versions/{version}`)로 알아야 한다면,
  포털이 그 사람 명의로 읽어 만들기 본문에 `template_schemas: {"<id>@<version>": <schema>}` 로 함께 넘길 수 있다 — 필요하면 칸 이름 · 꼴을 정해 달라.

### 4.7 오류 꼴(W-10)

`{"success": false, "data": null, "message": "<사람이 읽을 까닭>", "code": "NOT_FOUND | TOO_LARGE | NOT_BUILT | BUSY | INVALID | INTERNAL"}` 와 맞는 HTTP 상태.
포털은 `message` 를 사람에게 그대로 보이고 판정은 `code` 와 상태로 한다(글을 파싱하지 않는다). 허브 게이트의 401 · 403(`detail`)은 WDA 에 닿기 전이다.

## 5. 내려받기 요구(W-11)

- 주인만(W-2) · `Content-Disposition: attachment`(지금 웹 경로는 이미 attachment 다 — `app.py:425-434`) · `Content-Length` · `X-Content-Type-Options: nosniff`.
- HTML(`report.html` · 장면 HTML)은 `Content-Security-Policy: sandbox` 를 더한다(allow-same-origin 없이). 허브 앱은 포털과 같은 오리진(`/apps/`)이라 그 HTML 의
  스크립트가 포털 쿠키 · CSRF 값에 닿을 수 있다. 렌더 잡 경로가 html · pdf 를 inline 으로 내는 것(`app.py:455-461`)도 같은 까닭으로 본다.
- 생성 HTML 에 들어가는 보고서 글은 이스케이프한다(보고서는 RA 에서 여러 사람이 쓴 글일 수 있다).
- 포털은 WDA 의 주소를 사람에게 주지 않는다 — WDA 가 주는 URL(`render_status` 의 `urls` — `server.py:1045-1058`)은 포털 길에서는 쓰지 않는다.

## 6. 한도와 수명

- **W-7 본문 16MB 를 받는다** — 넘으면 413 `TOO_LARGE`. 심의 보고서는 블록 상한이 회의록 400 · 결과 · 권고 각 200 항목 × 1,900자라 수 MB 다. 포털은 미리 재서
  넘으면 부르지 않는다.
- **W-12 재기동에 끊긴 실행** — 파이프라인 · 렌더는 데몬 스레드라(`runs.py:172-176,283-288`) 재기동하면 원장이 running 인 채로 남고 재개도 running 을 거절한다
  (`runs.py:303-304`). 기동 때 running · queued(파이프라인) · queued · rendering(렌더)으로 남은 것을 `failed`(error `interrupted`)로 적어 달라.
- **W-13 보존 — 강하게 권한다.** WDA 답(11-01) — 지금은 **아무것도 지우지 않는다**(실행 60건에 372 MB). 남의 보고서 본문이 든 실행 · 산출물이 끝없이 쌓인다.
  보존 기한을 정해 지우고, 지운 산출물은 404 또는 410 으로 답해 달라. 포털은 잡 기록을 7일 두고, 그 뒤 받기는 '지워졌다' 로 말한다.
- **W-14 렌더 줄 — 강하게 권한다.** WDA 답 — 지금은 **동시 상한이 없다**(요청마다 스레드). 렌더(chromium)를 동시에 몇 개까지 돌릴지 정하고 넘치면
  `queued` 로 기다리게 해 달라. 포털은 사람당 동시 2 · 박스 전체 동시 4 로 막지만, WDA 콘솔 · MCP 로 들어오는 일은 포털이 막지 못한다.
- **W-15 같은 키 두 번(선택)** — `Idempotency-Key` 머리(포털 잡 id)가 같은 두 번째 만들기에 같은 run 을 돌려주면 시간 초과 뒤 다시 보낸 요청이 run 을 둘 만들지 않는다.
- 시간 — 보통 보고서로 PPT + PDF 가 몇 분인지, 영상을 더하면 몇 분인지 실측을 알려 달라. 포털 화면은 준비 30분 · 렌더 60분 · 영상 180분을 넘으면 '오래 걸린다'
  만 말하고(잡은 그대로), 24시간이 지나도 running 이면 포털이 실패로 닫는다.
- **뺀 출력(W-9)** — 지금은 장면 꼴이 내지 않는 출력을 말없이 거른다(`runs.py:366-367`). `render.requested` 와 `render.skipped[{target, reason}]` 로 돌려 달라 —
  포털은 알림에 '요청한 영상은 만들지 않았다(까닭)' 를 적는다.
- **그림** — 주인 있는 run 은 `WDA_RA_*` **서비스 자격**으로 RA 그림을 받지 않는다(`src/wdpipeline/assets.py:92-121`) — 사람 대신 서비스 계정이 RA 를 읽는 길이다.
  못 받은 그림은 지금처럼 `assets_meta` 에 까닭을 남긴다. 포털이 그 사람 명의로 그림을 받아 함께 넘기는 꼴은 M2(W-16)다.

## 7. 먼저 풀어야 할 것(전제)

- **P-1 main 을 GitHub 에 올리고 허브 SIF 를 다시 짓는다 — 사용자가 손으로 push 한다(11-01 결정).** 허브는 GitHub 에서 SIF 를 짓는다(HEAXHub
  `integrations/web-design-agents/.portal/manifest.yaml:70-73`). 허브의 `web-design-agents.sif` 는 2026-08-19 판이고 WDA main 은 origin/main 보다 68 커밋 앞선다
  (11-01). origin/main 의 렌더 출력은 `("video", "pptx")` 뿐이고 `pdf` · `doc_style` · `pptx_mode` · `resume` 이 없다 — **기본 PPT + PDF 가 지금 배치에서 돌지
  않는다.** 10-30 의 거절은 `refusing to allow a Personal Access Token to create or update workflow .github/workflows/ci.yml without workflow scope` 였고, 역사의
  `e4dc40e`(08-28) · `8d5a453`(10-24)가 그 파일을 만든다. `git push --dry-run` 은 서버 쪽 검사에 닿지 않으니 통과해도 풀린 것이 아니다. 11-01 에 다시 해 본
  실제 push 도 같은 거절이었다. **결정 — 사용자가 손으로 올린다. WDA 세션 · 포털 세션 · 코디네이터 누구도 push 하거나 역사를 다시 쓰지 않는다**(해시가 바뀌면
  문서가 인용한 커밋이 사라진다). WDA 세션은 W-1 ~ W-12 를 main 에 커밋해 두면 된다 — 올리는 것은 사용자다. 그 뒤 허브 SIF 재빌드는 HEAXHub 반영 순서를 따른다.
- **P-2 허브 매니페스트 `launch.portal_auth: true` — 반영됐다(HEAXHub `385783f`, 11-01).** dev 에서 익명 요청은 health · runs · mcp · 내려받기 모두 401, 허브 세션 · 유효한 PAT 은 200 이다.
  WDA 세션이 할 일은 없다. 켜지면 주인 없는 옛 run 과 WDA 콘솔까지 익명이 닫힌다(게이트가 익명에 401 — `authz.py:138-146`). 포털 길은 그 사람의 PAT 로
  지나므로 바뀌지 않는다.
- 포털 단추는 박스 스위치(기본 꺼짐)와 W-6 의 `owner` 능력이 **둘 다** 있어야 보인다. W-1 ~ W-12 가 배치된 뒤에 사람이 켠다.

## 8. R1 ~ R4 에 대한 답

- **R1 `destApps.ts` 의 `deck` 줄 — 넣지 않는다.** 발표자료는 RA 보고서 옆의 전용 단추이고 `DocActions`(붙인 문서에 LLM 지시문을 채우는 선택지)가 아니다.
  `destApps.ts` 는 그 선택지 · 업로드 목적지의 '지금 전문가' 순서표라 소비처 없는 줄은 아무 일도 하지 않는다. 거기 두면 LLM 이 `report_ingest`(서버 경로) ·
  `render_status` 되풀이로 WDA 를 몰게 된다(포털 결함 HA-28 의 꼴). 나중에 '붙인 문서 → 발표자료' 목적지를 만들면 그때 더한다.
- **R2 (나) 본문 전달 — 받는다.** 포털이 RA 를 그 사람 명의로 읽어 `POST /api/runs {report_json}` 로 넘긴다(4.1). (가) WDA 가 RA 를 끌어오기는 하지 않는다 —
  WDA 에 RA 자격을 주면 서비스 계정이 사람 대신 RA 를 읽는다.
- **R3 돌아오는 길 — 포털이 묻고, 알리고, 중계한다.** 포털이 3초마다 4.2 를 묻고(챗 LLM 은 묻지 않는다), 끝나면 포털이 그 대화에 알림을 남기고, 받기는 포털
  라우트가 4.5 를 서버에서 받아 흘린다. HTML 끼워 보기는 M1 에 하지 않는다(5 — 같은 오리진). 장면 HTML 은 쓰지 않는다.
- **R4 기본 출력 — `targets=["pptx","pdf"]` · `pptx_mode="hybrid"` · `doc_style="report"` · `narration=false`.** 영상 · html · docx 는 사람이 고를 때만.
  WDA 의 pdf 는 슬라이드 PDF 가 아니라 '읽는 문서' 다(`src/wdrender/exporter_doc.py:1`). **사용자 결정(11-01) — 기본 PDF 는 정식 보고서 문서(`doc_style=report`),
  요약(brief) · 메모(memo)는 단추에서 고른다.** 슬라이드 PDF(W-19)는 지금 청하지 않는다.

## 9. 나중(M2 — 단추를 켜는 데는 필요 없다)

- **W-16 그림 함께 받기** — 만들기에 파일을 같이 받는 꼴(예 multipart 의 `report` JSON + `asset:<file_id>` 파일들, 파일당 · 합계 상한)을 정해 달라. 포털이 그 사람
  명의로 RA `GET /api/files/{id}` 를 받아 넘긴다. WDA 는 그 파일만 쓰고 `WDA_RA_*` 로 RA 를 부르지 않는다.
- **W-17 지우기** — `DELETE /api/runs/{id}`(주인만) — RA 에서 보고서를 지운 사람이 사본도 지울 수 있게.
- **W-18 MCP 사람별 위임** — 개인 Claude 로 내 발표자료를 보려면 MCP 신원이 확인돼야 한다. HWAXRisk 꼴 — WDA 에 `/auth/sso`(공유 비밀 `X-Heax-Gateway-Secret` +
  게이트웨이가 실은 `X-Hwax-Delegate-Email` → 그 사람의 단기 단언, HWAXRisk `backend/app/routes.py:437-477`)와 단언 검증(`token_header`)을 두고, 게이트웨이
  `per_user_sso.web_design_agents` 를 켠다. 들어오면 W-4 를 '확인된 주인이면 연다' 로 넓힌다.
- **W-19 슬라이드 PDF** — 지금은 청하지 않는다(사용자 결정 11-01). **W-20 취소**(지금 웹 · MCP 둘 다 없다).

## 10. WDA 세션의 답(11-01)

1. **W-1 ~ W-12 는 지금 하나도 없다** — `src/wdweb/` 어디서도 신원을 읽지 않고, health 는 `{"status": "ok"}` 뿐이고, 본문 상한 · 오류 `code` 가 없고,
   run_id 는 `wr-{UTC 시각}-{16진 4자}`(무작위 16비트)다. 사용자가 직접 시킬 때만 짓겠다고 했다 — 포털은 이 요청서의 계약대로 짓고 시험의 가짜 WDA 가
   그 계약을 따른다(봉투 `{success, data, message, code}` · 상태 낱말 · 남과 신원 없음에 404 · 아래 블록 글자 규칙). 단추는 W-6 의 `owner` 가 보일 때까지
   어디에도 서지 않는다.
2. **심의 보고서는 꼴이 맞지 않는다** — 4.6-2 · W-21. 둘째 답(11-01 저녁) — 심의 꼴 `delib-16x9` 를 지었다(로컬 판 · 허브 SIF 전 · 상태 draft).
   features 는 꼴 등록부에서 만들어 내므로 표지 이름은 `format:delib-16x9` 이고, 만들기의 `format` 칸 · 모르는 꼴 400 · `block_sections` 는 4.1 · 4.6-2.
3. wide-16x9 에서 pptx · pdf 가 둘 다 나온다 — 문서 출력은 장면 꼴 거르기에서 빠진다(허용 docx · html · pdf · pptx · video).
4. 시간 · 크기 — 파이프라인 0.5초 + 렌더(pptx + pdf) 5.0초 = 5.5초, pptx 1,200 KB · pdf 1,926 KB. **보존 없음 · 동시 상한 없음** — W-13 · W-14.
5. 장면의 새 칸 `camera` · `transition` 은 기본값이 있어 계약에 영향이 없다.

블록 글자 규칙(WDA 가 알려 준 것 — 포털 시험의 가짜 WDA 가 그대로 따른다) — `rich_text` 의 글은 `content.markdown`, `heading` 은 `content.text` 다.
heading 의 `props.default_text` 는 대신 쓰지 않는다. `content` 에 항목이 없는 블록은 글자 0 이다. 모든 블록의 글자가 0 이면 거절한다(지금 문구
`ValueError: 텍스트를 가진 블록이 없다 (블록 8개, 텍스트 0개)` — W-10 이 들어오면 `INVALID` 로). 포털은 RA 의 ReportRead 를 **바꾸지 않고** 넘긴다.

## 11. WDA 체크리스트

| # | 무엇 | 언제 |
|---|---|---|
| W-1 | REST 만들기에 `X-Heax-User-Email` 로 owner | M0 필수 |
| W-2 | 주인 있는 run 의 run 단위 REST 전부 주인만(아니면 404) | M0 필수 |
| W-3 | 목록 = 내 것 + 주인 없는 것 | M0 필수 |
| W-4 | MCP(run_id · job_id · 경로 도구 전부) · 렌더 잡 내려받기는 주인 있는 run 에 닿지 않는다 | M0 필수 |
| W-5 | 주인 있는 새 run id 128비트 무작위 · id 꼴 검사 | M0 필수 |
| W-6 | `/api/health` 에 version · features(owner …) | M0 필수 |
| W-7 | 본문 16MB · 넘으면 413 TOO_LARGE | M0 필수 |
| W-8 | 만들기의 `render` 칸 — 빌드 뒤 이어서 렌더 | M0 필수(없으면 포털이 4.3 으로 대신하지만 화면이 열려 있어야 한다) |
| W-9 | `render.requested` · `render.skipped` | M0 필수 |
| W-10 | 오류 봉투에 `code` | M0 필수 |
| W-11 | 내려받기 머리(attachment · Content-Length · nosniff · HTML 은 CSP sandbox) | M0 필수 |
| W-12 | 재기동에 끊긴 실행 · 렌더를 failed(interrupted) | M0 필수 |
| W-13 | 보존 기한 · 지운 뒤 404/410 — 지금 아무것도 지우지 않는다 | **강하게 권장** |
| W-14 | 렌더 동시 상한(줄) — 지금 상한 없음 | **강하게 권장** |
| W-15 | Idempotency-Key | 선택 |
| W-21 | 심의 보고서 꼴 `delib-16x9` — features 의 `format:delib-16x9` · `formats` 의 상태 · 만들기의 `format` 칸 · 모르는 꼴 400(11-01 저녁 지음 · draft · 허브 SIF 전) | 심의 자리 단추의 전제 — 포털은 `active` 만 받는다(draft 는 사용자에게 묻는 중) |
| W-16 ~ W-18 · W-20 | 그림 · 지우기 · MCP 위임 · 취소 | M2 |
| W-19 | 슬라이드 PDF | 청하지 않는다(사용자 결정 11-01) |
| P-1 | main push → 허브 SIF 재빌드 | **사용자가 손으로 push**(결정 11-01) — WDA 세션은 커밋까지, push 하지 않는다 |
| P-2 | 매니페스트 `launch.portal_auth: true` | 반영됨 — HEAXHub `385783f`(WDA 할 일 없음) |
