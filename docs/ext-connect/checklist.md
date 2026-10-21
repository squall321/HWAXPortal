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
- [x] GW1 `_BUILTIN_CONN` · `_CONN_REG` · `_CONN_ACTIVE` · `_CONN_STATUS`
- [x] GW2 `_Backend(list_headers, list_only)` · `list_fp`
- [x] GW3 정책 갱신이 `connections` 를 읽고 `_conn_validate`(collision · no-policy-row · invalid) · 캐시 파일 0600
- [x] GW4 `_load_conn_registry_cache`
- [x] GW5 `_conn_reconcile` — 붙이기 · 갈아 끼우기 · 떼기
- [x] GW6 `_REVIVE_LOCK`
- [x] GW7 `_deny_reason` — 선언 백엔드는 행 · 선언이 없으면 닫힌다
- [x] GW8 기동 — 첫 카탈로그에 선언 백엔드
- [x] GW9 읽기 도구 힌트 · 노출 사본 readOnlyHint
- [x] GW10 캐시는 선언 백엔드의 읽기 도구만
- [x] GW11 `_call_shared` 는 목록 전용 세션이면 isError
- [x] GW12 선언 백엔드의 신원 없는 호출 거절
- [x] GW13 Authorization 한 번 더 떼기
- [x] GW14 감사 `tok:` 지문
- [x] GW15 `/health` `conn_platforms` · `/refresh` 가 정책을 먼저
- [x] GW16(선택) 로그에서 선언 접두 토큰 가리기(숫자가 든 8자 이상만 — EC-D11)
- [x] GW17 `.gitignore`
- [x] GW18 provision-config 문구 둘
- [x] GW19 이름 겹침은 선언 쪽만 접두
- [x] GW20 README
- [x] 시험 · 게이트웨이 전체 시험(RA · TestScope 묶음 회귀) — 533 통과, 변이 29 중 27 잡힘 + 잠금 시험을 고쳐 잡힘(0600 하나는 chmod 가 겹친 동등 변이)

## E3 포털 화면
- [x] PF1 `ExternalConnectionCards.tsx`
- [x] PF2 · PF3 TokenPage 에 붙이기 · PAT 없는 화면 설명
- [x] PF4 `/tokens` 문 · 메뉴에 `feat:connect`
- [x] PF5 eslint 인라인 스타일 목록
- [x] tsc · build · 화면 시험 · 캡처 — 임시 포털 27개 확인(EC-D16)

## E4 운영 스크립트
- [x] PX1 mcp-smoke 가 `conn_platforms` 키를 뺀다 · health gate 시험(붙어 있는 것만 — EC-D13, 변이 5 잡힘)
- [x] PX2 update-all 다운 백엔드 알림

## E5 문서 · 올리기
- [x] D1 sso-delegation server-setup C · D(1-7 절차로, 타일 파일은 systems.cae00.yaml)
- [x] D2 sso-delegation PLAN · checklist · context-notes · CLAUDE.md · 이력에 10-21 덧붙임
- [x] D3 fmea-request 를 (나) 개인 토큰 채택안으로
- [x] D4 = GW20
- [x] D5 · D6 — 초안 정정은 context-notes 에 적는다(초안은 리포에 없다)
- [x] 업데이트 이력 · CLAUDE.md 행 · 기억
- [x] push(포털 · 게이트웨이) · 화면 빌드 → Drive(포털 `latest/` 일치) · 포털 전체 시험 3,204 통과 · 2 실패(EC-D6 과 같은 둘)

## 남은 것 — 사람 몫 · 결정
- [ ] cae00 반영 — 요청서 4절 순서(포털 update-all → 게이트웨이 리포를 새 판으로 · 재기동(한가할 때) → 박스 권한표 `connect:` → 권한 → 사람이 토큰 등록). 절차는 [sso-delegation server-setup](../sso-delegation/server-setup.md) C · D
- [ ] FMEA 목록 계정 — 목록 전용 FMEA 로컬 계정 + 그 토큰을 등록할 포털 계정(`list_auth`) 정하기(server-setup D)
- [ ] 요청서 1-9 남은 질문 — 기본값으로 구현했다(EC-D2). 특히 ③ 평문 토큰(cae00 `users.sqlite` 0644)은 사람이 정한다
- [ ] dev 게이트웨이 · 포털 백엔드가 새 코드로 다시 뜨는 것 — 확인 뒤(재기동은 사용자 몫)
