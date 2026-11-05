# 다른 플랫폼의 화면을 챗 안에 — 결정 기록

계획은 [PLAN.md](PLAN.md), 할 일은 [checklist.md](checklist.md)다. 날짜는 KST.

**CE-1 사용자 결정(11-05) — 셋 다.** 조사 — iframe 으로 띄우라고 오는 것은 지금 두 갈래다. ① 도구가 주는 뷰어 주소(StepForge `section_atlas(viewer=true)` 의
`viewer.public_url` · `view_3d` 의 `viewer_url` · `public_url`) — 챗은 모델이 링크를 적어야 새 탭으로만 열었다. ② MCP Apps 패널 — 포털 · 에이전트 · 게이트웨이에 받는
부품이 있으나(10-31, HA-20) 포털 `MCP_APPS_HOST` 기본 꺼짐이고 dev 앱에는 `ui://` 를 내는 곳이 없다(cae00 SimFlow 후보). 사용자가 ① 뷰어 주소를 챗 안 창으로 ②
패널 켜기 ③ StepForge 에 패널 꼴 요청을 골랐다.

**CE-2 뷰어 카드는 '같은 출처 /apps/ 경로 · 격리 창 · 구조화 사건' 으로.** 허브 앱은 포털과 같은 출처라 격리에 같은 출처를 주면 앱 스크립트가 포털 쿠키에 닿는다 —
`sandbox="allow-scripts"` 하나. 그 격리 안에서는 앱이 쿠키로 부르는 API 가 막혀(불투명 출처) 혼자 도는 페이지만 제대로 뜬다 — 그래서 아무 뷰어 주소나 띄우지 않고
플랫폼의 명시 표지(`embed_url`)와 알려진 혼자 도는 뷰어(기본 StepForge 단면 지도)만. 첫 탐색(창 열기)은 같은 사이트라 Lax 쿠키가 실려 Caddy 로그인 확인을 지난다.
주소는 모델이 쓴 글이 아니라 도구 결과에서 에이전트가 집는다(지어낸 주소를 띄우지 않게) — 세 층이 같은 규칙으로 거른다. 공개 주소는 경로만 쓴다(정문이 같은 `/apps/`).

**CE-3 실물 확인(dev StepForge a81) — 기본 허용 목록이 맞고 뷰어는 격리 창에서 돈다.** `section_atlas(viewer=true)` 의 응답은 `viewer: {route: "/view/<과제>/atlas",
public_url: "<정문 오리진>/apps/step_forge/view/<과제>/atlas", file, file_in_data, bytes, slices}` — 공개 주소의 경로가 기본 허용 목록 `^/apps/step_forge/view/[^/?#]+/atlas$`
와 맞는다(공개 주소의 오리진은 dev 박스 주소라 추적 파일에 적지 않는다). 뷰어 페이지 응답 머리의 CSP 는 `default-src 'none'; script-src 'sha256-…'; style-src
'unsafe-inline'; img-src data:; … frame-ancestors 'self'` — 바깥 연결이 없어 격리(불투명 출처)에서도 그대로 돌고, frame-ancestors 'self' 는 포털 페이지(같은 출처)를 받는다.
3D 뷰어(`/view/<과제>`)는 목록에 없다 — 쿠키로 API 를 불러 격리 창에서 깨진다(링크로 남는다).

**CE-4 MCP Apps 패널 기본 켬 — 권한은 그대로.** `MCP_APPS_HOST` 기본을 True 로(설정 주석에 결정). 켜도 화면은 `feat:panels`(CAEG 는 `"*"`)인 사람만 표지를 싣고,
세션 쿠키 챗만이며, 앱이 `_meta.ui.resourceUri` 를 낸 도구만 패널이 된다 — 지금 dev 앱에는 없어 보이는 변화는 없다(cae00 SimFlow 가 내면 그때 뜬다). 끄기는 박스
`backend/.env` 의 `MCP_APPS_HOST=0`. 패널 시험은 손잡이를 직접 넘겨 기본값과 무관하고, 기본값은 새 시험이 지킨다.

**CE-5 StepForge 요청 — 패널 꼴 · embed_url 표지.** 요청서 [stepforge-request.md](stepforge-request.md)를 세션 메시지로 보냈다(11-05). 패널이면 브리지로 그 앱의
도구(`describe_part`)를 부를 수 있어 그쪽이 말한 '사이드바' 가 패널 안에 선다 — 포털 사이드바를 따로 짓지 않는다. 답(도구 · `ui://` 주소 · 판)이 오면 dev 게이트웨이
`tools/list` 로 표지를 확인하고 챗에서 연다.

**CE-6 에이전트 서버 구현에서 정한 것(af17496 — 하위 에이전트가 짓고 검토해 합침).** 그릇(문맥 변수)은 `embeds.py` 에 둔다(시험이 app 을 다시 읽어도 같은
변수 — ui_panels 와 같은 까닭). 주소 규칙은 포털 것을 그대로 옮기고 질의 몫의 `..` · `//` 까지 버려 조금 좁다 — 내는 쪽이 좁으면 어긋나도 카드가 빠질 뿐이고, 넓으면
화면이 버린 카드를 서버 사본만 쥔다. 결과 글은 앞의 JSON 값 하나만 읽는다(래퍼가 뒤에 붙인 그림 주소 안내가 카드를 가리지 않게). 오류로 끝나는 길(error)은 카드를
내지 않는다 — 계약이 'result 앞' 이다(패널은 error 앞에도 낸다). StepForge 는 `STEPFORGE_PUBLIC_BASE` 가 있을 때만 `viewer.public_url` 을 채운다 — 없는 박스는 null 이라
카드가 없다(그래서 그쪽에 `/apps/…` 경로의 `embed_url` 표지를 청했다 — stepforge-request 2절 3). 실제 StepForge 응답(dev)에 대어 단면 지도 주소를 집는 것을 봤다.

