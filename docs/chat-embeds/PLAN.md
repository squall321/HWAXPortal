# 다른 플랫폼의 화면을 챗 안에 — 뷰어 카드 · MCP Apps 패널 켜기

사용자 요청 11-05 「다른 플랫폼에서 iframe 으로 오게끔 온 것들이 chat 에서도 떴으면 해」 → 조사(지금 그런 것은 둘 — 도구가 주는 **뷰어 주소**(StepForge 단면
지도 뷰어 등)와 **MCP Apps 패널**(`ui://` 화면 — 포털 받는 부품은 10-31 에 지었으나 꺼짐)) → 사용자 결정(11-05) 셋 — ① 뷰어 주소를 챗 안 창으로 ② MCP Apps 패널
켜기 ③ StepForge 에 패널 꼴로도 내 달라고 요청. 판단 기록은 [context-notes.md](context-notes.md), 할 일은 [checklist.md](checklist.md). 날짜는 KST.
앞선 같은 갈래 — 같은 출처 SVG 그림은 격리 iframe(`docs/report-figures` RF-36, 포털 `2ff8d56d`).

## 1. 뷰어 카드

도구 결과에 뷰어 주소가 있으면 그 답 아래에 **격리 창 카드**(머리 — 앱 · 제목 · 새 탭 · 접기)를 단다. 지금은 모델이 링크를 적어야만 새 탭으로 열렸다.

- **무엇을 띄우나** — 같은 출처 `/apps/<앱>/…` 경로만(허브 앱 — 포털 정문의 nginx → 허브 Caddy, 로그인 쿠키 확인). 두 길로 고른다.
  - **명시 표지** — 도구 결과 JSON 의 `embed_url`(경로 또는 공개 주소). 다른 플랫폼에 주는 일반 약속이다 — '바깥 자원 · 쿠키로 부르는 API 없이 혼자 도는 페이지' 만 단다.
  - **기본 허용 목록** — 표지가 없어도 알려진 혼자 도는 뷰어의 `public_url` · `viewer_url`(에이전트 서버 `CHAT_EMBED_PATHS`, 정규식 · 쉼표 — 기본은 StepForge 단면
    지도 `/apps/step_forge/view/<과제>/atlas`). StepForge 3D 뷰어(`/view/<과제>`)는 로그인 쿠키로 API 를 불러 격리 창에서 깨지므로 넣지 않는다(링크 그대로).
  - 공개 주소(`http(s)://…/apps/…`)는 경로만 쓴다 — 포털 정문이 같은 `/apps/` 를 내주므로 같은 출처가 된다(dev `STEPFORGE_PUBLIC_BASE` 의 포트가 달라도).
- **격리** — `<iframe sandbox="allow-scripts">`(같은 출처 · 창 열기 · 폼 · 최상위 이동 막음) · `referrerpolicy="no-referrer"` · `loading="lazy"`. 허브 앱은 포털과 같은
  출처라 `allow-same-origin` 을 주면 앱 스크립트가 포털 쿠키 · 저장소에 닿는다 — 절대 주지 않는다. 페이지 CSP `frame-src 'self'` 그대로(넓히지 않는다).
- **계약(세 층이 같은 꼴)** — 에이전트 서버가 챗 턴 동안 모아 답 끝(`result` 앞)에 SSE `embeds` 한 번: `{"items": [{"app", "tool", "url", "title"}]}` — 턴마다 4개,
  `url` 은 `^/apps/[a-z0-9][a-z0-9_-]{0,63}/` 로 여는 안전한 경로(따옴표 · 공백 · 역슬래시 · `..` · `//` 없음, 2,048자). 포털 중계가 같은 규칙으로 다시 거르고 답
  `meta.embeds` 에 남긴다(새로고침 · 다른 기기). 화면도 다시 거른다. 모델이 쓰는 글을 파싱하지 않는다(지어낸 주소를 띄우지 않게).
- **화면** — 이 탭에서 받은 답이면 연 채로, 기록에서 온 카드는 접힌 채('열기') — 옛 대화를 열 때 창 여럿을 한꺼번에 띄우지 않는다. 높이 520px · 넓게 보기.
- **로그인** — 허브 앱 로그인(SSO)이 덜 된 채면 창이 빈칸(401)일 수 있다 — 카드 머리의 '새 탭' 이 늘 있다.

## 2. MCP Apps 패널 켜기

포털 `MCP_APPS_HOST` 기본을 켬으로(권한 `feat:panels` — CAEG 는 `"*"` 로 이미 있음, 세션 쿠키 요청만 · 에이전트 `CHAT_UI_HOST` 는 이미 1). 앱이 `_meta.ui.resourceUri`
(`ui://`) 를 단 도구를 내면 챗 · 전문가 챗 · 도크에 격리 패널(srcdoc · sandbox=allow-scripts · CSP 메타 · 브리지 · 첫 쓰기 확인 · 감사)로 뜬다(10-31 HA-20). 지금 dev 앱
에는 보내는 곳이 없다 — cae00 SimFlow 가 후보(프로토콜 물음 Q-S1 ~ S9 는 그쪽 답 대기). 끄기는 박스 `backend/.env` 의 `MCP_APPS_HOST=0`.

## 3. StepForge 에 패널 꼴 요청

단면 지도 뷰어 · svg_live 를 MCP Apps(`ui://` 자원 + 도구의 `_meta.ui.resourceUri`)로도 내 달라고 한다 — 패널 길은 브리지 · CSP · 감사가 이미 있고 챗 · 전문가 챗 ·
도크를 다 덮는다. 요청서 [stepforge-request.md](stepforge-request.md).

## 4. 시험

에이전트 서버 — 모으기(표지 · 허용 목록 · 공개 주소 → 경로 · 위험한 주소 버림 · 턴마다 4 · 같은 주소 하나) · 챗 스트림이 `result` 앞에 `embeds` 를 내고 자기검증
감싸개를 지난다. 포털 — 중계가 거르고 `meta.embeds` 에 남김 · `MCP_APPS_HOST` 기본. 화면 — 경로 판정(node) · 카드 iframe 은 `sandbox="allow-scripts"` 하나(소스 단언) ·
저장 · 되살리기.
