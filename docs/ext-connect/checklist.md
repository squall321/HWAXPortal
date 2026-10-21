# 외부 연결을 설정만으로 — 체크리스트

> 계획 [PLAN.md](PLAN.md) · 요청서 [request.md](request.md) · 결정 [context-notes.md](context-notes.md).

## E1 포털 백엔드
- [x] PB1 `ConnectSpec`(frozen) · `Item.connect`
- [x] PB2 `load_raw` — 추적 권한표의 `connect` 를 떼고 알린다(박스 파일에서만)
- [x] PB3 `_parse_connect` — 칸 표대로 검사, 틀리면 그 블록만 버리고 알린다(모르는 칸도 — EC-D3)
- [x] PB4 `Policy.connections()` · `gateway_connections()`
- [x] PB5 `/internal/access/policy` 에 `connections`(한 파싱 · 한 응답)
- [x] PB6 `BUILTIN` · `_registry(request)`
- [x] PB7 `GET /auth/connections/ext` — platforms · orphans(주소 · verify_url · list_auth 를 내지 않는다)
- [x] PB8 `PUT · DELETE /auth/connections/ext/{service}` — 세션 + CSRF 만, ⓪~⑩
- [x] PB9 `_verify_ext` — `trust_env=False`, none · mcp · url, owner_field fail-closed
- [x] PB10 `/internal/connections/{service}` 가 선언 키를 받는다
- [x] PB11 `connection_services(email)`
- [x] PB12 합성 권한 `feat:connect`
- [x] PB13 추적 권한표 주석(matnexus · fmea · 머리)
- [~] PB14(선택) — 하지 않는다(EC-D5)
- [x] 시험 — 파싱 · 오버레이 · 재기동 없는 반영 · 내부 정책 불변식 · ext 목록 · PUT · DELETE · 합성 권한 · 호환(`test_ext_connections.py` 68)
- [x] 포털 전체 시험 — 3,202 통과 · 2 실패(HEAD 에서도 같다, EC-D6)

## E2 게이트웨이
- [ ] GW1 `_BUILTIN_CONN` · `_CONN_REG` · `_CONN_ACTIVE` · `_CONN_STATUS`
- [ ] GW2 `_Backend(list_headers, list_only)` · `list_fp`
- [ ] GW3 정책 갱신이 `connections` 를 읽고 `_conn_validate`(collision · no-policy-row · invalid) · 캐시 파일 0600
- [ ] GW4 `_load_conn_registry_cache`
- [ ] GW5 `_conn_reconcile` — 붙이기 · 갈아 끼우기 · 떼기
- [ ] GW6 `_REVIVE_LOCK`
- [ ] GW7 `_deny_reason` — 선언 백엔드는 행 · 선언이 없으면 닫힌다
- [ ] GW8 기동 — 첫 카탈로그에 선언 백엔드
- [ ] GW9 읽기 도구 힌트 · 노출 사본 readOnlyHint
- [ ] GW10 캐시는 선언 백엔드의 읽기 도구만
- [ ] GW11 `_call_shared` 는 목록 전용 세션이면 isError
- [ ] GW12 선언 백엔드의 신원 없는 호출 거절
- [ ] GW13 Authorization 한 번 더 떼기
- [ ] GW14 감사 `tok:` 지문
- [ ] GW15 `/health` `conn_platforms` · `/refresh` 가 정책을 먼저
- [ ] GW16(선택) 로그에서 선언 접두 토큰 가리기
- [ ] GW17 `.gitignore`
- [ ] GW18 provision-config 문구 둘
- [ ] GW19 이름 겹침은 선언 쪽만 접두
- [ ] GW20 README
- [ ] 시험 · 게이트웨이 전체 시험(RA · TestScope 묶음 회귀)

## E3 포털 화면
- [ ] PF1 `ExternalConnectionCards.tsx`
- [ ] PF2 · PF3 TokenPage 에 붙이기 · PAT 없는 화면 설명
- [ ] PF4 `/tokens` 문 · 메뉴에 `feat:connect`
- [ ] PF5 eslint 인라인 스타일 목록
- [ ] tsc · build · 화면 시험 · 캡처

## E4 운영 스크립트
- [ ] PX1 mcp-smoke 가 `conn_platforms` 키를 뺀다 · health gate 시험
- [ ] PX2 update-all 다운 백엔드 알림

## E5 문서 · 올리기
- [ ] D1 sso-delegation server-setup C · D(1-7 절차로, 타일 파일은 systems.cae00.yaml)
- [ ] D2 sso-delegation PLAN · checklist · context-notes · CLAUDE.md · 이력에 10-21 덧붙임
- [ ] D3 fmea-request 를 (나) 개인 토큰 채택안으로
- [ ] D4 = GW20
- [ ] D5 · D6 — 초안 정정은 context-notes 에 적는다(초안은 리포에 없다)
- [ ] 업데이트 이력 · CLAUDE.md 행 · 기억
- [ ] push(포털 · 게이트웨이) · 화면 빌드 → Drive
