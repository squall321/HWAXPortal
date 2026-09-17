# 챗·심의 액션 바 — 체크리스트

## 구현
- [x] `chatActions.ts` — 매니페스트 검증(schema·kind·label≤24·prompt≤2000·중복 id·출처당 8·총 12)·`safeUrl`·`scopeOf`·`fillText`
- [x] `ChatActionBar.tsx` — 타일 게이트 → fetch(1.5초·content-type·schema) → scope·need 선별 → 없으면 null
- [x] `ExportBar.tsx` — import 1줄 + 툴바 첫 자식 1줄, 기존 버튼·핸들러 무변경
- [x] `systems.yaml` — `knox-bridge` 타일(proxy, url 없음, 문구가 '메일' 을 약속하지 않게)
- [x] `access.yaml` — 플랫폼 `knoxbridge`
- [x] `routes.local.env.example` — 켜는 법 주석

## 검증
- [x] 백엔드 — 킬 스위치 테스트 6건(되돌림 검사: 타일에 url 을 박으면 2건 실패)
- [x] 백엔드 — 전체 497 통과(`test_access_control.py` 타일·플랫폼 대조 포함)
- [x] 프론트 순수 규칙 16건(되돌림 검사: 역슬래시 방어를 빼면 실패) — 목록은 context-notes A-10
- [x] 프론트 컴포넌트 jsdom 8건(되돌림 둘: 캐시 키 고정 → 사용자 전환 실패, 옛 대답 술어 → 발굴 실패 실패)
- [x] 레이아웃 폭 쓸기 — 빌드 CSS 로 360~1400px × 구성 12가지 실패 0(새 규칙 뺀 대조판 202)
- [x] 프론트 — 변경 파일 eslint 0 · `pnpm build`(tsc -b) 통과. 전체 lint 의 12건은 기존 파일의 것
- [x] 반박 검토 1라운드(킬 스위치·보안·회귀·요청서/권한, 지적 39 → 확인된 것 반영, 기각 6) — A-9
- [x] 반박 검토 2라운드(1라운드 수정분, 지적 13 전부 확인 → 반영, 범위 밖은 A-11) — A-9-2
- [ ] dev 실측 — 카탈로그 재적재 뒤 타일 coming_soon, `/knox-bridge/ui/actions.json` 요청이 안 나간다

## 반영(사내) — 순서를 지킨다
- [ ] 커밋·push
- [ ] **사이드카가 먼저** — `/knox-bridge/ui/actions.json` 이 `application/json` 으로 나오는지 사이드카 포트에서 확인
- [ ] **게이트웨이 키가 먼저** — 사이드카 bridge MCP 를 게이트웨이에 붙이기 전(또는 같은 변경)에 그 백엔드 키를
      `access.yaml` `knoxbridge.gateway` 에 넣고, `feat:chat` 만 있는 계정의 `tools/list` 에 bridge 도구가 없는지 본다
- [ ] cae00 — `git pull` → `cd frontend && pnpm build`
- [ ] `routes.local.env` 에 `knox-bridge=` → `gen-nginx-conf.sh` → nginx reload → `POST /systems/reload`(또는 포털 재기동)
- [ ] CAEG 계정으로 챗·심의 툴바 버튼 확인, 비CAEG 계정으로 매니페스트 요청 0 확인
- [ ] 개통 확인 뒤 `changelog.yaml` 에 "Knox 개통 환경에서" 한정 문구로 항목 추가(모든 박스가 같은 팝업을 본다)

## 사용자 결정
- [x] Knox 미개통 박스에서는 **숨긴다**(2026-09-17) — 타일·권한 표 행·권한 요청. 테스트 4 더함(되돌림 셋 확인), A-12
- [ ] dev 포털 반영 — 백엔드 코드라 포털 인스턴스 재기동이 필요하다(사용자 승인)
