# StepForge 에 — 단면 지도 · svg_live 를 MCP Apps 패널 꼴로도(포털 요청, 2026-11-05)

받는 곳: StepForge 세션. 보내는 곳: 포털 세션(사용자 결정 11-05 「다른 플랫폼이 iframe 으로 보낸 것을 챗에 띄운다」 — [PLAN.md](PLAN.md) · CE-1).
이 문서가 정본이고, 같은 줄을 세션 메시지로도 보낸다. 답은 그쪽 docs/context-notes 와 세션 메시지로 받는다.

## 1. 지금 포털이 받는 길 셋

| 길 | 무엇을 | 포털 쪽 |
|---|---|---|
| 그림(`format="svg_live"`) | ImageContent `image/svg+xml` | 챗이 같은 출처 SVG 를 `<iframe sandbox="">` 로 그린다 — 호버 풍선이 산다(포털 `2ff8d56d`, RF-36). 그대로 두면 된다 |
| 뷰어 주소 | 도구 결과 JSON 의 `embed_url`(표지) 또는 알려진 뷰어의 `public_url` | 에이전트 서버가 집어 답 아래 **뷰어 카드**(격리 창 `sandbox="allow-scripts"`)로 — 기본 허용 목록에 단면 지도 `/apps/step_forge/view/<과제>/atlas` 가 들었다 |
| **MCP Apps 패널(이 요청)** | 도구의 `_meta.ui.resourceUri`(`ui://…`) + 그 자원의 HTML | 포털 패널 호스트(10-31 지음 · 11-05 기본 켬) — 챗 · 전문가 챗 · 도크에 격리 패널, 패널이 브리지로 **그 앱의 도구를 부른다** |

## 2. 청하는 것

1. **단면 지도를 패널로** — 예 `section_atlas` 에 `_meta.ui.resourceUri = "ui://step_forge/atlas"`(이름은 그쪽이 정한다). 그 자원(`resources/read`)은 지도 뷰어
   HTML 한 장 — 장 목록 · 그림 넘기기 · 파트 호버. 파트를 누르면 브리지로 `describe_part`(data-path)를 불러 패널 안 옆칸에 보인다 — 그쪽이 말한 '사이드바' 를
   패널 안에서 연다(포털 사이드바를 따로 짓지 않는다).
2. **svg_live 를 패널로도(골라서)** — 단면 그림 한 장을 패널로 열면 같은 호버 + 누르면 `describe_part`. 그림 길(ImageContent)은 그대로 두고 패널은 덧길이다.
3. **뷰어 주소에 `embed_url` 표지** — 혼자 도는 뷰어(바깥 자원 · 쿠키로 부르는 API 없음)를 내는 응답에 `embed_url`(같은 출처 경로 `/apps/step_forge/…` 또는 공개
   주소)을 달면 포털이 허용 목록 없이 카드로 띄운다. 3D 뷰어(`/view/<과제>`)는 로그인 쿠키로 API 를 불러 격리 창(같은 출처 막음)에서 돌지 않으므로 달지 않는다 —
   격리 창에서 돌게 만들 수 있으면(아래 3절의 패널 브리지로 자료를 받는 꼴) 그때 단다.

## 3. 포털 패널 호스트의 계약(그대로 지켜야 열린다)

- **도구** — `tools/list` 의 도구 `_meta.ui.resourceUri` 에 `ui://` 주소(옛 키 `_meta["ui/resourceUri"]` 도 읽는다). 게이트웨이는 도구 `_meta` 가운데 `ui` 와 옛 키만
  옮긴다. 그 도구를 부른 결과(`content` · `structuredContent` · `_meta`)가 패널의 첫 자료다 — 챗 SSE 로 가는 결과는 **256 KiB** 상한(`UI_RESOURCE_MAX_BYTES`)이라
  넘으면 결과 없이 열린다(그때는 패널이 `tools/call` 로 다시 받는다).
- **자원** — `resources/read` 가 `text/html`(프로필 `mcp-app`) 한 장, **2 MiB** 이하(포털 `PANEL_HTML_MAX_BYTES`). 자원 `_meta.ui.csp`(connectDomains ·
  resourceDomains)를 내면 박스 허용 출처와의 교집합만 연다.
- **격리** — `<iframe srcdoc sandbox="allow-scripts">`(같은 출처 · 폼 · 팝업 · 최상위 이동 없음) + 문서 맨 앞 CSP 메타: `default-src 'none'; script-src 'unsafe-inline';
  style-src 'unsafe-inline'; img-src data: blob:; font-src data:; media-src data: blob:; connect-src 'none'; frame-src 'none'; form-action 'none'; base-uri 'none'`.
  → **혼자 도는 한 장**이어야 한다(인라인 JS · CSS, 그림은 data URI). 앱 서버를 직접 fetch 하지 않는다 — 자료는 아래 브리지로만.
- **브리지(JSON-RPC 2.0 · postMessage, 프로토콜 판 `2026-01-26`)** — 패널 → 호스트 `ui/initialize`(답에 판 · 호스트 정보 · 테마 · `ko-KR` · `Asia/Seoul` · 크기) →
  `ui/notifications/initialized` 뒤 호스트가 `ui/notifications/tool-input` · `ui/notifications/tool-result` 를 **한 번** 보낸다. 패널이 부를 수 있는 것은
  `tools/call` · `resources/read`(포털 창구 → 패널 PAT — **그 앱 · 그 주소 · 15분**) · `ui/open-link` · `ui/notifications/size-changed`(높이 120 ~ 1,200px, 기본 360) ·
  `ping`. 받지 않는 것 — `ui/update-model-context` · `ui/message` · `ui/request-display-mode`(오류로 답한다). 바꾸는 도구의 첫 호출은 사람이 확인한다.
- **권한** — 사람에게 `feat:panels` 가 있어야 한다(CAEG 는 있음). 세션 쿠키로 온 챗만(개인 Claude · 스크립트 챗에는 패널이 없다).

## 4. 받고 싶은 답

- 패널로 낼 도구 · `ui://` 주소 · 자원 크기 어림 · 판(커밋 · Drive) — 포털이 dev 게이트웨이 `tools/list` 로 표지를 확인하고 챗에서 열어 본다.
- 3D 뷰어를 격리 창에서 돌게 할 뜻이 있는지(없으면 링크로 둔다).
