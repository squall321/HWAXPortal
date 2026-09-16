# 챗·심의 액션 바 — 사내 연계 앱이 툴바에 버튼을 낸다(메일 보내기)

요청: 사내 Knox 연계 사이드카(knox-bridge) 쪽의 2차 변경 요청서(2026-09-17, 원문은 사이드카 리포에 있다 —
사내 주소·계정·서버 실측이 들어 있어 이 공개 리포에는 옮기지 않는다) + 사용자 조건 둘.

1. **메일 보내기가 챗·심의 화면에 버튼으로 있어야 한다.**
2. **Knox 연결 설정이 없는 환경에서는 그냥 꺼져야 한다** — 에러·빈 버튼·콘솔 소음 없이.

## 무엇을 만드나

챗(`/`)·심의(`/deliberate`)가 함께 쓰는 대화 툴바 `ExportBar` 맨 앞에 `ChatActionBar` 를 붙인다. 툴바가
그렇듯 **대화에 메시지가 하나라도 있을 때** 뜬다(새 챗·빈 심의 화면에는 없다).
버튼 목록의 정본은 **포털 밖** — knox-bridge 가 서비스하는 매니페스트 `/knox-bridge/ui/actions.json` 이다.
버튼을 더하고 고치고 지우는 일은 그 JSON 편집 + 새로고침이고 포털 빌드가 필요 없다.

```json
{ "schema": "hwax.chat-actions/1",
  "actions": [
    { "id": "mail-conv", "label": "✉ 메일로 보내기", "kind": "prompt", "mode": "fill",
      "prompt": "지금까지의 대화를 정리해 메일 초안을 만들어 줘. …" },
    { "id": "mail-delib", "label": "✉ 결정문 메일", "kind": "prompt", "mode": "send", "scope": "deliberate",
      "prompt": "이 심의 결정문을 메일 초안으로 만들어 줘. …" },
    { "id": "mailbox", "label": "📬 발송 이력", "kind": "link", "url": "/knox-bridge/mail" }
  ] }
```

| 필드 | 뜻 |
|---|---|
| `kind: prompt` | 누르면 `prompt` 를 입력창에 채운다(`mode: fill`, 기본) 또는 바로 보낸다(`mode: send`) |
| `kind: link` | `url` 을 새 탭으로 연다 — `http(s)://` 또는 같은 오리진 절대경로만 |
| `scope` | `chat` · `deliberate` · `both`(기본) |
| `need` | 이 권한 키(`feat:`·`plat:`)가 있어야 보인다(선택) |

버튼 동작의 안전장치.

- 채우기는 입력창에 쓰던 글을 지우지 않고 뒤에 덧붙인다.
- 바로 보내기는 대화에 대답이 있을 때만 켜지고(챗은 오류 없는 본문, 심의는 **결정문**), 스트리밍 중에는 꺼진다
  (이유를 title 로 보인다). 입력창에 쓰던 글이 있으면 보내지 않고 채우기로 바뀐다.
- **매니페스트 작성 규칙** — `mode: send` 는 지금 대화의 대답을 재료로 쓰는 요청에만 쓴다. 대화와 무관한 요청(메일함
  요약 등)은 `fill` 로 둔다 — send 는 첫 턴이 실패했거나 응답 중이면 꺼진다.
- 매니페스트의 모르는 값(종류·범위·스킴·길이 초과)은 그 항목을 버린다.

실제 발송의 관문은 사이드카의 확인 화면(`/knox-bridge/confirm/{draft_id}`)이다. 버튼은 LLM 에게
**초안 도구를 부르라고 말하는 것**까지이고, 메일은 사람이 확인 화면에서 확정해야 나간다.

## 킬 스위치 — 환경에 Knox 연결이 없으면 요청조차 안 나간다

```
routes.local.env 의 knox-bridge=  ──→ nginx 라우트(gen-nginx-conf.sh) + 타일 available   ← 실제 배선
SYS_KNOX_BRIDGE_URL 환경변수       ──→ 타일 available 만(nginx 라우트 없음 → 매니페스트가 SPA html → 버튼 0)
둘 다 없음                         ──→ 타일 coming_soon

ChatActionBar: /systems 에서 knox-bridge 가 available·proxy 인가?
   아니오 → 매니페스트 fetch 없음, 렌더 null (DOM 0, 콘솔 0)
   예     → /knox-bridge/ui/actions.json (1.5초, JSON·schema 검사) → 실패는 전부 버튼 0
```

새 환경변수를 만들지 않는다. 포털이 이미 쓰는 목적지 규약(routes 파일 한 줄, 또는 `SYS_<ID>_URL`)이 곧
"Knox 연결 설정" 이다. **끄는 법은 그 줄·변수를 지우는 것**이다 — 값이 비어 있지 않으면 `off` 같은 값도 켠다.
끈 뒤 열려 있는 탭은 새로고침해야 버튼이 사라진다.

라우트는 살아 있는데 사이드카가 매니페스트를 안 내면(404) 버튼 0 에 콘솔 네트워크 에러 **사용자당 1건**(확정이라
캐시한다). 죽어 있으면(502·타임아웃) 회복을 위해 캐시하지 않으므로 툴바가 다시 뜰 때마다(대화 전환·챗↔심의 이동)
`/systems`·매니페스트를 다시 부르고 502 는 그때마다 1건 남긴다. 페이지 코드로 막을 수 없다. 그래서 개통은
**사이드카 매니페스트가 먼저**다.

## 권한 — 가리는 것과 막는 것

| 무엇 | 무엇으로 |
|---|---|
| 타일·툴바 버튼·매니페스트 요청 | `/systems` 의 `filter_tiles` — `plat:knoxbridge` 가 없으면 타일이 안 내려온다 |
| **bridge 도구 호출(챗에서 말로·PAT·MCP)** | 게이트웨이 — `access.yaml` `knoxbridge.gateway` 에 **그 백엔드 키가 있어야** 막힌다. 비어 있으면 누구나 쓴다(context-notes A-8) |

## 바꾸는 파일

| 파일 | 무엇 |
|---|---|
| `frontend/src/components/chat/chatActions.ts` (신규) | 순수 규칙 — 매니페스트 검증·링크 안전 판정·출처 병합·화면별 선별·초안 보존 채우기 |
| `frontend/src/components/chat/ChatActionBar.tsx` (신규) | 게이트·fetch·사용자별 캐시·렌더 |
| `frontend/src/components/chat/ExportBar.tsx` | import 1줄 + 툴바 첫 자식 `<ChatActionBar />` 1줄 |
| `frontend/src/styles/chatpage.css` | `.cx-export` 폭 제한·줄바꿈, 사이드바 접힘 때 좌상단 컨트롤 자리 비우기 |
| `backend/config/systems.yaml` | `knox-bridge` 타일(proxy, url 없음 → 목적지 없으면 coming_soon) |
| `backend/config/access.yaml` | 플랫폼 `knoxbridge` — 타일 `knox-bridge` |
| `backend/config/routes.local.env.example` | 켜는 법 주석 |
| `backend/tests/test_chat_actions_killswitch.py` (신규) | 목적지 없으면 coming_soon, 환경변수·routes 로 available, 추적 routes 파일에 목적지 없음 |

포털 백엔드 **코드**는 바꾸지 않는다(설정 데이터만). CSS 는 툴바 두 규칙만 — 버튼이 늘면 좁은 폭에서 좌상단
'사이드바 열기'·'새 대화' 를 덮거나 화면 밖으로 밀렸다(context-notes A-9-2).

## 보이는 변화

| 박스 | 무엇이 달라지나 |
|---|---|
| Knox 개통 박스(routes 줄 + 사이드카 매니페스트) | `plat:knoxbridge` 가진 사람의 챗·심의 툴바에 버튼, `/apps` 에 Knox Bridge 타일 |
| 모든 박스 | 좁은 폭에서 대화 툴바가 좌상단 컨트롤을 덮지 않고 **줄을 바꾼다**(원래 약 430px 미만에서 덮었다). 360~1400px 에서 가림·화면 밖 0 |
| 그 밖(dev 등) | `/apps` 에 (`plat:knoxbridge` 보유자에게) **'Knox Bridge — 곧 공개' 카드**, '내 권한'·관리 화면에 **'Knox 연계' 플랫폼 행** |

## 범위 밖 — 사이드카가 한다

메일함·발송 이력 화면, 매니페스트 서비스, Knox 어댑터 배선, 보낸 메일 보관 정책, 확인 화면의 인증·권한.
전부 knox-bridge 리포의 일이다.
